#!/usr/bin/env python3
"""
Convert data/roadmap.md into data/roadmap.json for the Roadmap Dashboard.

Parsing conventions (confirmed against the version in this repo):
  - Every major section is an H1 of the form "# <n>. <Title>".
  - A month phase starts at an H1 matching "MONTH <n> — <CALENDAR LABEL>",
    immediately followed by an unnumbered H1 with the phase theme.
  - Inside a month phase: "## Month Objective" (paragraph), "## Exit Criteria"
    (list), "## Week <n> — <title>" (H2, repeatable) and a trailing H3
    "### Month <n> deliverables" (checklist).
  - Inside a week: H3 headings are Topics. A topic title may end in
    "— D1" / "— D2/D3" etc, which is parsed out as `depth`.
  - "### Build" / "### Benchmark" H3s are topics with kind=build/benchmark.
  - Checklist items ("- [ ] ...") are subtasks. A plain line ending in ":"
    immediately before checklist items is a group label (e.g. "Study:").

Months 9 and 10 do not use "## Week N" sections — their numbered H1
sub-sections are routed to a phase via SECTION_ROUTING as "theme" sections.
Sections not listed in SECTION_ROUTING fall into the `reference` bucket.

Re-run whenever roadmap.md is edited:

    python3 scripts/md_to_json.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Literal, Optional, TypedDict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "roadmap.md"
OUT = ROOT / "data" / "roadmap.json"

MONTH_NAMES: dict[str, int] = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}

# Routing for numbered H1 sections that belong to Month 9 / Month 10 thematically
# but are not nested as "## Week N" headings.
# Values: phase number (9|10), "reference", "counters", "mastery", or None (skip).
SECTION_ROUTING: dict[int, int | str | None] = {
    0: "reference",   # Roadmap Goal
    1: "reference",   # Core Strategy
    2: "reference",   # Time Commitment
    3: "reference",   # Depth Model
    4: "reference",   # Global Priority Matrix
    5: "reference",   # Master Learning Loop
    6: "reference",   # Monthly Outcome Map
    15: 9, 16: 9, 17: 9, 18: 9, 19: 9, 20: 9, 21: 9, 22: 9, 23: 9,
    24: 10, 25: "reference", 26: 10, 27: 10,
    28: "mastery",
    29: "reference", 30: "reference", 31: "reference", 32: "reference",
    33: "reference",
    34: "reference", 35: "reference", 36: "reference", 37: "reference",
    38: "reference", 39: "reference", 40: "reference", 41: "reference",
    42: None, 43: None,  # describe this tool's own design; not user content
    44: "reference", 45: "reference", 46: "reference",
    47: "counters",
}

# Compiled regular expressions
CHECKBOX_RE = re.compile(r"^-\s*\[( |x|X)\]\s*(.+)$")
H1_RE = re.compile(r"^#\s+(.+)$")
H2_RE = re.compile(r"^##\s+(.+)$")
H3_RE = re.compile(r"^###\s+(.+)$")
NUMBERED_H1_RE = re.compile(r"^(\d+)\.\s+(.+)$")
MONTH_HEADER_RE = re.compile(r"^MONTH\s+(\d+)\s*[—-]\s*(.+)$", re.IGNORECASE)
WEEK_HEADER_RE = re.compile(r"^Week\s+(\d+)\s*[—-]\s*(.+)$", re.IGNORECASE)
DEPTH_SUFFIX_RE = re.compile(r"^(.*?)\s*[—-]\s*(D[0-3](?:/D[0-3])?(?:\s+\w+)*)$")
MONTH_DELIVERABLES_RE = re.compile(r"^Month\s+(\d+)\s+deliverables$", re.IGNORECASE)
TOPIC_HEADING_RE = re.compile(r"^#{3,4}\s+(.+)$")
COUNTER_RE = re.compile(r"^([A-Za-z /]+):\s*(\d+)\s*/\s*(\d+)\s*$")
CALENDAR_LABEL_RE = re.compile(r"([A-Z]+)\s+(\d{4})")


# ---------------------------------------------------------------------------
# TypedDicts — fixed shapes for every data dict the parser produces
# ---------------------------------------------------------------------------

class Subtask(TypedDict):
    """A single trackable checklist task."""

    id: str
    title: str
    status: Literal["not_started"]
    notes: str
    link: str
    dueDate: None


class ChecklistGroup(TypedDict):
    """A named (or anonymous) group of subtasks within a topic."""

    label: Optional[str]
    subtasks: list[Subtask]


class Topic(TypedDict):
    """A learning topic within a week or theme section."""

    id: str
    title: str
    depth: Optional[str]
    kind: Literal["study", "build", "benchmark"]
    groups: list[ChecklistGroup]


class Section(TypedDict):
    """A week or theme section within a phase."""

    id: str
    title: str
    type: Literal["week", "theme"]
    weekNumber: Optional[int]
    startDate: Optional[str]
    endDate: Optional[str]
    topics: list[Topic]


class NoteBlock(TypedDict):
    """A read-only narrative note attached to a phase."""

    id: str
    title: str
    blocks: list[str]


class Phase(TypedDict):
    """One calendar month of the roadmap."""

    id: str
    number: int
    title: str
    calendarLabel: str
    startDate: Optional[str]
    endDate: Optional[str]
    objective: str
    exitCriteria: list[str]
    sections: list[Section]
    deliverables: list[Subtask]
    notes: list[NoteBlock]


class Counter(TypedDict):
    """A numeric progress counter (e.g. DSA problems solved)."""

    id: str
    label: str
    target: int
    current: int


class MasterySkill(TypedDict):
    """An individual skill entry in the mastery checklist."""

    id: str
    title: str
    depth: Optional[str]
    status: Literal["not_started"]


class MasteryCategory(TypedDict):
    """A category grouping related mastery skills."""

    id: str
    title: str
    skills: list[MasterySkill]


class ReferenceSection(TypedDict):
    """A read-only reference section shown alongside the roadmap."""

    id: str
    title: str
    blocks: list[str]


# ---------------------------------------------------------------------------
# SlugRegistry — replaces the old global slug_counter mutable state
# ---------------------------------------------------------------------------

class SlugRegistry:
    """Track slug usage counts to de-duplicate generated IDs within one parse run."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def slugify(self, text: str, prefix: str = "") -> str:
        """Return a unique kebab-case slug for *text*, optionally prefixed.

        Repeated calls with the same text produce "base", "base-2", "base-3", …
        """
        base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        if prefix:
            base = f"{prefix}{base}"
        n = self._counts.get(base, 0)
        self._counts[base] = n + 1
        return base if n == 0 else f"{base}-{n + 1}"


# ---------------------------------------------------------------------------
# Pure date helpers
# ---------------------------------------------------------------------------

def _month_add(d: date, months: int) -> date:
    """Return the first day of the month *months* after *d*."""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)


def _month_last_day(d: date) -> date:
    """Return the last calendar day of the month containing *d*."""
    return _month_add(d, 1) - timedelta(days=1)


# ---------------------------------------------------------------------------
# Heading predicate helpers
# ---------------------------------------------------------------------------

def _is_h1(line: str) -> bool:
    s = line.strip()
    return bool(H1_RE.match(s)) if s.startswith("# ") else False


def _is_h2(line: str) -> bool:
    return line.strip().startswith("## ")


def _is_h3(line: str) -> bool:
    return line.strip().startswith("### ")


def _is_topic_heading(line: str) -> bool:
    # Topics are normally H3, but one spot in the source nests the real
    # topic title one level deeper — treat H3 *and* H4 as topic boundaries.
    s = line.strip()
    return s.startswith("### ") or s.startswith("#### ")


# ---------------------------------------------------------------------------
# Pure content helpers
# ---------------------------------------------------------------------------

def _parse_depth(title: str) -> tuple[str, Optional[str]]:
    """Split a topic title into (clean_title, depth_suffix or None)."""
    m = DEPTH_SUFFIX_RE.match(title.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return title.strip(), None


# ---------------------------------------------------------------------------
# I/O helpers — separated from parsing so the parser is testable in isolation
# ---------------------------------------------------------------------------

def load_lines(path: Path) -> list[str]:
    """Read *path* and return its lines without trailing newlines."""
    return path.read_text(encoding="utf-8").splitlines()


def write_output(data: dict, json_path: Path, js_path: Path) -> None:
    """Serialise *data* to *json_path* and wrap it as a JS assignment for *js_path*."""
    json_text = json.dumps(data, indent=2)
    json_path.write_text(json_text, encoding="utf-8")
    js_path.write_text(
        "// Auto-generated by scripts/md_to_json.py — do not edit by hand.\n"
        f"window.ROADMAP_DATA = {json_text};\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# RoadmapParser — all parsing logic encapsulated in one class
# ---------------------------------------------------------------------------

class RoadmapParser:
    """Parse a structured Markdown roadmap file into a JSON-serialisable dict.

    Args:
        lines: Source lines returned by :func:`load_lines`.
        slug_registry: Shared slug registry. A fresh instance is created when
            omitted, keeping each parser run isolated.
    """

    # Human-readable labels for counter keys found in the source document.
    _COUNTER_LABELS: dict[str, str] = {
        "DSA": "DSA Problems Solved",
        "System Designs": "System Designs Completed",
        "ML Questions": "ML Interview Questions",
        "GenAI Questions": "GenAI Interview Questions",
        "Debugging Questions": "Production Debugging Questions",
        "Behavioral Stories": "Behavioral Stories Prepared",
        "Technical Posts": "Technical Posts Published",
        "Open Source Contributions": "Open Source Contributions",
    }

    def __init__(
        self,
        lines: list[str],
        slug_registry: Optional[SlugRegistry] = None,
    ) -> None:
        self._lines = lines
        self._slugs = slug_registry or SlugRegistry()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def parse(self) -> dict:
        """Run the full parse and return the roadmap data dict."""
        lines = self._lines
        n = len(lines)

        numbered: list[tuple[int, int, str]] = []
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("# "):
                m = NUMBERED_H1_RE.match(s[2:].strip())
                if m:
                    numbered.append((i, int(m.group(1)), m.group(2).strip()))

        phases: dict[int, Phase] = {}
        reference: list[ReferenceSection] = []
        counters: list[Counter] = []
        mastery: list[MasteryCategory] = []

        for idx, (line_idx, sec_num, title) in enumerate(numbered):
            block_end = numbered[idx + 1][0] if idx + 1 < len(numbered) else n
            content_start = line_idx + 1

            mm = MONTH_HEADER_RE.match(title)
            if mm:
                phase_num = int(mm.group(1))
                calendar_label = mm.group(2).strip()
                theme, content_start = self._extract_theme(content_start, block_end)
                phase = self._parse_phase(
                    content_start, block_end, phase_num, calendar_label, theme
                )
                phases[phase_num] = phase
                continue

            route = SECTION_ROUTING.get(sec_num, "reference")
            if route is None:
                continue
            if route == "reference":
                reference.append(self._build_reference(content_start, block_end, title))
            elif route == "counters":
                counters = self._build_counters(content_start, block_end)
            elif route == "mastery":
                mastery = self._build_mastery(content_start, block_end)
            elif isinstance(route, int):
                target_phase = phases.get(route)
                if target_phase is not None:
                    self._attach_routed_section(target_phase, title, content_start, block_end)

        ordered_phases = [phases[k] for k in sorted(phases.keys())]
        return {
            "meta": self._build_meta(ordered_phases),
            "phases": ordered_phases,
            "counters": counters,
            "masteryChecklist": mastery,
            "reference": reference,
        }

    # ------------------------------------------------------------------
    # Phase parsing
    # ------------------------------------------------------------------

    def _extract_theme(self, content_start: int, block_end: int) -> tuple[str, int]:
        """Find the unnumbered H1 theme line and return (theme, new_content_start)."""
        lines = self._lines
        j = content_start
        while j < block_end:
            s = lines[j].strip()
            if s.startswith("# ") and not NUMBERED_H1_RE.match(s[2:].strip()):
                return s[2:].strip(), j + 1
            if s:
                break
            j += 1
        return "", content_start

    def _parse_phase(
        self,
        h1_start: int,
        h1_end: int,
        phase_num: int,
        calendar_label: str,
        theme: str,
    ) -> Phase:
        """Parse one month phase and return its data dict."""
        lines = self._lines
        phase_start_date = self._parse_calendar_date(calendar_label)
        phase_id = f"month-{phase_num}"

        objective = ""
        exit_criteria: list[str] = []
        sections: list[Section] = []
        notes: list[NoteBlock] = []
        deliverables = self._extract_deliverables(h1_start, h1_end, phase_id)

        h2_positions = [j for j in range(h1_start, h1_end) if _is_h2(lines[j])]
        h2_positions.append(h1_end)

        for idx in range(len(h2_positions) - 1):
            h2_title = H2_RE.match(lines[h2_positions[idx]].strip()).group(1).strip()
            body_start = h2_positions[idx] + 1
            body_end = h2_positions[idx + 1]

            if h2_title.lower() == "month objective":
                objective = self._extract_paragraph(body_start, body_end)
                continue
            if h2_title.lower() == "exit criteria":
                exit_criteria = self._extract_list(body_start, body_end)
                continue

            wm = WEEK_HEADER_RE.match(h2_title)
            if wm:
                section = self._build_week_section(
                    body_start, body_end, phase_id, phase_num,
                    int(wm.group(1)), wm.group(2).strip(), phase_start_date
                )
                sections.append(section)
            else:
                sec_id = self._slugs.slugify(f"{phase_id}-{h2_title}", "")
                topics = self._parse_week_section(
                    body_start, body_end, h2_title, sec_id
                )
                if topics:
                    sections.append({
                        "id": sec_id,
                        "title": h2_title,
                        "type": "theme",
                        "weekNumber": None,
                        "startDate": None,
                        "endDate": None,
                        "topics": topics,
                    })
                else:
                    blocks = self._extract_blocks(body_start, body_end)
                    if blocks:
                        notes.append({"id": sec_id, "title": h2_title, "blocks": blocks})

        return {
            "id": phase_id,
            "number": phase_num,
            "title": theme,
            "calendarLabel": calendar_label,
            "startDate": phase_start_date.isoformat() if phase_start_date else None,
            "endDate": _month_last_day(phase_start_date).isoformat() if phase_start_date else None,
            "objective": objective,
            "exitCriteria": exit_criteria,
            "sections": sections,
            "deliverables": deliverables,
            "notes": notes,
        }

    def _parse_calendar_date(self, calendar_label: str) -> Optional[date]:
        """Parse a calendar label like "OCTOBER 2026" into a :class:`date`."""
        m = CALENDAR_LABEL_RE.match(calendar_label.upper())
        if m and m.group(1) in MONTH_NAMES:
            return date(int(m.group(2)), MONTH_NAMES[m.group(1)], 1)
        return None

    def _build_week_section(
        self,
        body_start: int,
        body_end: int,
        phase_id: str,
        phase_num: int,
        week_num: int,
        week_label: str,
        phase_start_date: Optional[date],
    ) -> Section:
        """Build one week section dict."""
        sec_id = self._slugs.slugify(f"{phase_id}-week-{week_num}", "")
        week_start = week_end = None
        if phase_start_date:
            offset = (week_num - 1) % 4
            week_start = phase_start_date + timedelta(days=7 * offset)
            week_end = week_start + timedelta(days=6)
        topics = self._parse_week_section(body_start, body_end, week_label, sec_id)
        return {
            "id": sec_id,
            "title": f"Week {week_num} — {week_label}",
            "type": "week",
            "weekNumber": week_num,
            "startDate": week_start.isoformat() if week_start else None,
            "endDate": week_end.isoformat() if week_end else None,
            "topics": topics,
        }

    def _attach_routed_section(
        self,
        phase: Phase,
        title: str,
        content_start: int,
        block_end: int,
    ) -> None:
        """Attach a routed H1 section (or its H2 sub-sections) to *phase*."""
        lines = self._lines
        h2_positions = [j for j in range(content_start, block_end) if _is_h2(lines[j])]
        if not h2_positions:
            self._attach_theme_section(phase, title, content_start, block_end)
            return

        h2_positions.append(block_end)
        if h2_positions[0] > content_start:
            self._attach_theme_section(phase, title, content_start, h2_positions[0])
        for k in range(len(h2_positions) - 1):
            sub_title = H2_RE.match(lines[h2_positions[k]].strip()).group(1).strip()
            self._attach_theme_section(
                phase,
                f"{title} — {sub_title}",
                h2_positions[k] + 1,
                h2_positions[k + 1],
            )

    def _attach_theme_section(
        self,
        phase: Phase,
        title: str,
        start: int,
        end: int,
    ) -> bool:
        """Append a theme section to *phase*; return True if topics were found."""
        sec_id = self._slugs.slugify(f"{phase['id']}-{title}", "")
        topics = self._parse_week_section(start, end, title, sec_id)
        if topics:
            phase["sections"].append({
                "id": sec_id,
                "title": title,
                "type": "theme",
                "weekNumber": None,
                "startDate": None,
                "endDate": None,
                "topics": topics,
            })
            return True
        blocks = self._extract_blocks(start, end)
        if blocks:
            phase.setdefault("notes", []).append(
                {"id": sec_id, "title": title, "blocks": blocks}
            )
        return False

    # ------------------------------------------------------------------
    # Week / topic parsing
    # ------------------------------------------------------------------

    def _parse_week_section(
        self,
        start: int,
        end: int,
        week_title: str,
        section_id: str,
    ) -> list[Topic]:
        """Return the topic list for one week or theme section."""
        lines = self._lines
        topics: list[Topic] = []

        h3_positions = [j for j in range(start, end) if _is_topic_heading(lines[j])]
        first_h3 = h3_positions[0] if h3_positions else end

        # Content before the first H3 (if any) becomes an implicit overview topic.
        if first_h3 > start:
            leading_groups = self._collect_checklist_groups(
                start, first_h3, f"{section_id}-overview"
            )
            if leading_groups:
                topics.append({
                    "id": self._slugs.slugify(f"{section_id}-overview", "topic-"),
                    "title": week_title,
                    "depth": None,
                    "kind": "study",
                    "groups": leading_groups,
                })

        h3_positions.append(end)
        for idx in range(len(h3_positions) - 1):
            h3_line = lines[h3_positions[idx]].strip()
            title_raw = TOPIC_HEADING_RE.match(h3_line).group(1).strip()
            body_start = h3_positions[idx] + 1
            body_end = h3_positions[idx + 1]

            if MONTH_DELIVERABLES_RE.match(title_raw):
                continue  # handled separately by _extract_deliverables

            title, depth = _parse_depth(title_raw)
            kind: Literal["study", "build", "benchmark"] = "study"
            low = title.lower()
            if low == "build":
                kind = "build"
            elif low == "benchmark":
                kind = "benchmark"

            topic_id = self._slugs.slugify(f"{section_id}-{title}", "topic-")
            groups = self._collect_checklist_groups(body_start, body_end, topic_id)
            if not groups:
                continue
            topics.append({
                "id": topic_id,
                "title": title,
                "depth": depth,
                "kind": kind,
                "groups": groups,
            })

        return topics

    def _collect_checklist_groups(
        self,
        start: int,
        end: int,
        id_prefix: str,
    ) -> list[ChecklistGroup]:
        """Parse lines[start:end] into grouped checklist subtasks.

        A non-checkbox line ending in ':' opens a new named group. Prose
        lines (paragraphs, code fences, tables) are intentionally skipped.
        """
        lines = self._lines
        groups: list[ChecklistGroup] = []
        current: ChecklistGroup = {"label": None, "subtasks": []}

        for i in range(start, end):
            line = lines[i].strip()
            if not line:
                continue
            cb = CHECKBOX_RE.match(line)
            if cb:
                current["subtasks"].append(self._new_subtask(cb.group(2), id_prefix))
            elif line.endswith(":") and not line.startswith("#") and not line.startswith("|"):
                if current["subtasks"] or current["label"]:
                    groups.append(current)
                current = {"label": line[:-1].strip(), "subtasks": []}

        if current["subtasks"] or current["label"]:
            groups.append(current)
        return [g for g in groups if g["subtasks"]]

    def _new_subtask(self, title: str, id_prefix: str) -> Subtask:
        """Create a subtask dict with a unique slug ID."""
        return {
            "id": self._slugs.slugify(title, id_prefix + "-"),
            "title": title.strip(),
            "status": "not_started",
            "notes": "",
            "link": "",
            "dueDate": None,
        }

    # ------------------------------------------------------------------
    # Deliverables, paragraphs, lists, blocks
    # ------------------------------------------------------------------

    def _extract_deliverables(
        self, start: int, end: int, phase_id: str
    ) -> list[Subtask]:
        """Find and parse the "Month N deliverables" H3 checklist, if present."""
        lines = self._lines
        for j in range(start, end):
            if not _is_h3(lines[j]):
                continue
            title_raw = H3_RE.match(lines[j].strip()).group(1).strip()
            if not MONTH_DELIVERABLES_RE.match(title_raw):
                continue
            body_end = end
            for k in range(j + 1, end):
                if _is_h3(lines[k]) or _is_h2(lines[k]) or _is_h1(lines[k]):
                    body_end = k
                    break
            groups = self._collect_checklist_groups(
                j + 1, body_end, f"{phase_id}-deliverable"
            )
            return [st for g in groups for st in g["subtasks"]]
        return []

    def _extract_paragraph(self, start: int, end: int) -> str:
        """Return the first non-empty paragraph text in lines[start:end]."""
        lines = self._lines
        buf: list[str] = []
        for j in range(start, end):
            line = lines[j].strip()
            if not line or line == "---":
                if buf:
                    break
                continue
            if line.startswith("#") or line.startswith("- ["):
                break
            buf.append(line)
        return " ".join(buf).strip()

    def _extract_list(self, start: int, end: int) -> list[str]:
        """Collect bullet / checkbox item text from lines[start:end]."""
        lines = self._lines
        items: list[str] = []
        for j in range(start, end):
            line = lines[j].strip()
            cb = CHECKBOX_RE.match(line)
            if cb:
                items.append(cb.group(2).strip())
            elif line.startswith("- "):
                items.append(line[2:].strip())
        return items

    def _extract_blocks(self, start: int, end: int) -> list[str]:
        """Split lines[start:end] into non-empty paragraph blocks."""
        lines = self._lines
        blocks: list[str] = []
        buf: list[str] = []
        for j in range(start, end):
            line = lines[j].rstrip()
            if line.strip() == "---":
                continue
            if not line.strip():
                if buf:
                    blocks.append("\n".join(buf))
                    buf = []
                continue
            buf.append(line)
        if buf:
            blocks.append("\n".join(buf))
        return blocks

    # ------------------------------------------------------------------
    # Counters, mastery, reference
    # ------------------------------------------------------------------

    def _build_counters(self, start: int, end: int) -> list[Counter]:
        """Parse the Quick Progress Snapshot counter block."""
        lines = self._lines
        counters: list[Counter] = []
        for j in range(start, end):
            m = COUNTER_RE.match(lines[j].strip())
            if m:
                key = m.group(1).strip()
                label = self._COUNTER_LABELS.get(key, key)
                counters.append({
                    "id": self._slugs.slugify(key, "counter-"),
                    "label": label,
                    "target": int(m.group(3)),
                    "current": 0,
                })
        return counters

    def _build_mastery(self, start: int, end: int) -> list[MasteryCategory]:
        """Parse the flat mastery checklist into categorised skill lists."""
        lines = self._lines
        categories: list[MasteryCategory] = []
        h2_positions = [j for j in range(start, end) if _is_h2(lines[j])]
        h2_positions.append(end)
        for idx in range(len(h2_positions) - 1):
            cat_title = H2_RE.match(lines[h2_positions[idx]].strip()).group(1).strip()
            body_start = h2_positions[idx] + 1
            body_end = h2_positions[idx + 1]
            skills: list[MasterySkill] = []
            for j in range(body_start, body_end):
                cb = CHECKBOX_RE.match(lines[j].strip())
                if cb:
                    title, depth = _parse_depth(cb.group(2))
                    skills.append({
                        "id": self._slugs.slugify(f"{cat_title}-{title}", "skill-"),
                        "title": title,
                        "depth": depth,
                        "status": "not_started",
                    })
            if skills:
                categories.append({
                    "id": self._slugs.slugify(cat_title, "cat-"),
                    "title": cat_title,
                    "skills": skills,
                })
        return categories

    def _build_reference(
        self, start: int, end: int, title: str
    ) -> ReferenceSection:
        """Wrap a read-only narrative section."""
        return {
            "id": self._slugs.slugify(title, "ref-"),
            "title": title,
            "blocks": self._extract_blocks(start, end),
        }

    # ------------------------------------------------------------------
    # Static metadata builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_meta(ordered_phases: list[Phase]) -> dict:
        """Build the top-level metadata block."""
        return {
            "title": "AI Engineer — Tier-1 Career Roadmap",
            "subtitle": "Personalized 10-Month Execution Plan for a 4.5-Year AI/ML Engineer",
            "horizonStart": ordered_phases[0]["startDate"] if ordered_phases else None,
            "horizonEnd": ordered_phases[-1]["endDate"] if ordered_phases else None,
            "weeklyHours": {"min": 14, "max": 17},
            "weeklyAllocation": [
                {
                    "track": "DSA / coding",
                    "hoursMin": 3.5, "hoursMax": 4.0, "priority": "Critical",
                },
                {
                    "track": "System design / distributed systems",
                    "hoursMin": 2.0, "hoursMax": 2.5, "priority": "Critical",
                },
                {
                    "track": "AI engineering learning",
                    "hoursMin": 2.5, "hoursMax": 3.0, "priority": "Critical",
                },
                {
                    "track": "Project development",
                    "hoursMin": 4.0, "hoursMax": 5.0, "priority": "Critical",
                },
                {
                    "track": "Career / LinkedIn / networking",
                    "hoursMin": 0.5, "hoursMax": 1.0, "priority": "High",
                },
                {
                    "track": "Weekly review",
                    "hoursMin": 0.5, "hoursMax": 1.0, "priority": "High",
                },
            ],
            "depthLevels": [
                {"code": "D3", "label": "Deep / Mastery"},
                {"code": "D2", "label": "Working Proficiency"},
                {"code": "D1", "label": "Awareness"},
                {"code": "LOW", "label": "Low Priority / Skip"},
            ],
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse roadmap.md and write roadmap.json + roadmap.js."""
    lines = load_lines(SRC)
    data = RoadmapParser(lines).parse()

    js_out = ROOT / "data" / "roadmap.js"
    write_output(data, OUT, js_out)

    ordered_phases: list[Phase] = data["phases"]
    total_subtasks = sum(
        len(g["subtasks"])
        for p in ordered_phases
        for s in p["sections"]
        for t in s["topics"]
        for g in t["groups"]
    ) + sum(len(p["deliverables"]) for p in ordered_phases)

    print(
        f"Wrote {OUT} — {len(ordered_phases)} phases, {total_subtasks} subtasks, "
        f"{len(data['counters'])} counters, "
        f"{len(data['masteryChecklist'])} mastery categories, "
        f"{len(data['reference'])} reference sections."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
