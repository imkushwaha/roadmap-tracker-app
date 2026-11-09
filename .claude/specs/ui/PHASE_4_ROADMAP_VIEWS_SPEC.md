# Phase 4 — The Seven Roadmap Views: Implementation Spec

> **Audience:** an AI coding agent (or developer) implementing this phase in the *Roadmap Tracker* repository.
> **Status of this spec:** every step below was executed on a copy of the repository with Phases 0–3 applied, and verified: `npm test` 79/79, Phase 4 UI harness **121/121**, and the earlier harnesses still pass (Phase 0: 61/61, Phase 1: 67/67, Phase 2: 114/114 (patched), Phase 3: 88/88). If you follow it exactly you will get the same result.

| | |
|---|---|
| **Phase** | 4 of 5 — Roadmap views |
| **Depends on** | **Phases 0–3 completed and verified** (Section 2) |
| **Branch** | continue on `feature/ui-redesign` |
| **Effort** | about 5 working days by hand; under an hour of agent time because every file and script is supplied |
| **Visible result** | Overview, Timeline, Checklist, This week, Kanban, Skills checklist and Reference are redesigned and consistent; the blank-roadmap state is a guided empty state; every dialog behaves the same (named, Escape, Tab trap, focus return, labelled fields); emoji icons and inline styles are gone |
| **Backend change** | **None** |
| **Risk** | Medium. About 600 lines of rendering code are replaced. Mitigations: the data logic (statuses, saving, counters, search, drag-and-drop handlers) is untouched; the class names earlier harnesses wait on are kept; a 121-check harness covers every view |
| **Next phase** | Phase 5 — Hardening: remove the last legacy CSS file, cross-browser and responsive pass, final accessibility audit, documentation (separate spec) |

---

## 0. Rules for the implementing agent (read first)

1. **Do exactly what this document says. Do not redesign.** Names, copy, structure and behaviour are decided.
2. **Phases 0–3 must already be applied.** If `css/home.css`, `showModal()` in `js/app.js`, or `window.MonthStrip` are missing, stop and report.
3. **No new npm dependencies, no build step, no server, API or database change.** Do not edit anything under `server/` or `test/`.
4. **Do not change data logic**: statuses and `setItemFields`, saving/conflict handling, counters (`getCounter`/`setCounter`), search state, `phaseStats`/`overallStats`/…, drag-and-drop handlers, routing, auth. Only markup, classes, labels, icons and the small handler changes in Task 3.
5. **Keep these class names** (earlier harnesses wait on them): `.stat-tile`, `.kanban-board`, `.subtask-checkbox`, `.subtask-row`, `.mini-btn`, `.tab`, `.section-title` may disappear but `h2.view-title` replaces it.
6. **Icons, not glyphs.** Use `icon(name, size)` (wraps `Icons.svg`). The only emoji allowed in the whole app is the celebration toast "🎉 Month complete…".
7. **Handlers must use `event.target.closest("[data-action]")`.** A click can land on an SVG inside a button; code that reads `event.target.dataset` silently stops working (this is why Task 3 exists).
8. **Security rules** (`CLAUDE.md`): every piece of user text (task titles, notes, links, roadmap names) goes through `esc()`; no inline scripts or `eval`; no new storage.
9. **If a script in this spec fails an `assert`**, the repository has drifted. Do not force it. Read that script's "Intent" list, apply the equivalent edit by hand, and record the difference in your hand-off.
10. **Run the verification (Section 7) before declaring done.** Commit in task order.

---

## 1. Goal and scope

### 1.1 Problems this phase fixes

| # | Problem after Phase 3 | Fix |
|---|---|---|
| 1 | Overview: eight near-identical stat tiles, many inline styles | One header band (headline %, Month Strip, three metrics), status bar with legend, month list, compact counters |
| 2 | Every view has a different heading style (`.section-title` div) | `h2.view-title` via `viewHead()`; text-heavy views use a reading width |
| 3 | Emoji used as icons (🔗 ✎ ✕ 🗑 ＋ ▸ ✓ ●) | SVG icons everywhere |
| 4 | Clicking an icon inside a button would do nothing (handler read `e.target.dataset`) | `closest("[data-action]")` |
| 5 | Timeline: sections toggled by clicking a `div` (not keyboard reachable); all months collapsed | Real buttons inside headings; current month opens by itself; sticky month header |
| 6 | Checklist: filters scroll away, no counts, rows cramped (controls under the title) | Sticky filter bar with counts; one-line 40px task rows |
| 7 | Kanban: no keyboard way to change status; text mentions a "⋯ menu" that does not exist | Status dropdown on every card; four coloured columns; sideways scroll on phones |
| 8 | Skills: no per-group progress; inline-styled strike-through | Group progress bars; class-based styling |
| 9 | Reference: one long scroll of 23 cards | Two panes: sticky document list + 760px reading column ("Jump to" select on small screens) |
| 10 | Blank roadmap: a paragraph and a list | Guided empty state with three steps |
| 11 | Dialogs: inline-styled text, unlabelled fields, no focus return, mixed behaviour | One behaviour (named, Escape, Tab trap, focus in and back), `for`-linked labels, text classes |
| 12 | All-caps month labels ("OCTOBER 2026") | Sentence case |
| 13 | About 60 inline `style=` attributes in `js/app.js` | 3 left, all genuinely dynamic |

### 1.2 Deliverables

| # | Deliverable | Files |
|---|---|---|
| 1 | Seven redesigned views + blank-roadmap state + render helpers | `js/app.js` |
| 2 | Click/change handler changes (`closest`, new actions) | `js/app.js` |
| 3 | Dialog clean-up and shared behaviour improvements | `js/app.js` |
| 4 | New stylesheet for all views | `css/roadmap.css` (new); `css/styles.css` reduced to the account-menu rules |
| 5 | Three more icons (`link`, `pencil`, `inbox`) | `js/icons.js` |
| 6 | Stylesheet link | `index.html` |
| 7 | Documentation | `README.md`, `documentation/design-system.md` |

### 1.3 Out of scope (do NOT do these here)

- Removing `css/styles.css` entirely, cross-browser testing, the final audit (Phase 5).
- New features: drag-and-drop for lists, task reordering, bulk edit, a right-hand detail drawer, command palette.
- Any change to the roadmap data (`data/roadmap.json`, `data/roadmap.js`) or its wording.
- Restyling the Home screen or the app shell (done in Phases 2–3).

---

## 2. Preconditions

```bash
git status                                         # on feature/ui-redesign, clean
npm test                                           # expect: tests 79, pass 79, fail 0
ls css/roadmap.css 2>/dev/null; echo "(roadmap.css must NOT exist yet)"
grep -c "function showModal" js/app.js             # expect 1  (Phase 3)
grep -c "function renderOverview" js/app.js        # expect 1
grep -c "const kanbanState" js/app.js              # expect 1
```

Optionally run the Phase 0–3 harnesses first to confirm a green baseline.

### 2.1 How the views work today (facts you must respect)

- `rerender()` calls `VIEW_RENDERERS[state.view](document.getElementById("main"))`; each renderer writes `container.innerHTML`. State lives in module variables: `expandedPhases`, `sectionOpenState`, `checklistFilters`, `kanbanState`, `state.search`. `resetViewState()` clears them when a roadmap opens.
- Rendering helpers: `progressBar`, `statusChip`, `statusSelect`, `depthBadge`, `dueTag`, `matchesSearch`, `subtaskRow`, `indexEntry`, `emptyState`. Data helpers: `allPhases`, `phaseStats`, `sectionStats`, `topicStats`, `overallStats`, `currentPhase`, `currentSection`, `momentumThisWeek`, `weeklyCompletionSeries`, `estimatedCompletion`, `getItem`, `getCounter`, `setCounter`, `INDEX`, `DATA`, `STATUS`, `STATUS_LABEL`.
- **Event handling:** `onMainClick` (delegated on `#main`) reads `e.target.dataset.action` — it must become `closest()`. `onMainChange` handles `toggle-complete`, `set-status`, `filter-phase`, `kanban-phase`. `onModalClick` handles dialog buttons by `e.target.dataset.action`.
- **Dialogs** each build HTML into `#modalHost .modal` and (before this phase) remove `hidden` directly. Phase 3 added `showModal(returnFocus)` / `closeModal()` / `trapModalFocus` and the document Escape handler; New roadmap, Delete and About use them, the rest do not yet.
- **The Overview** is expected to contain `.stat-tile` elements (several harnesses wait for one to know the roadmap has loaded); **Kanban** contains `.kanban-board`.
- Month labels come from `phaseCalendarLabel(n)` / `phaseCalendarLabelFor(yyyy-mm)`, which upper-case the text.

---

## 3. Design specification

### 3.1 Common to all views

| Aspect | Spec |
|---|---|
| Heading | `viewHead(title, sub?)` → `<header class="view-head"><h2 class="view-title">…</h2><p class="view-sub">…</p></header>`. Titles: **Overview**, **Timeline**, **Checklist**, **This week**, **Kanban**, **Skills checklist**, **Reference & strategy**, and **Let's build your roadmap** for the blank state. The screen's single `h1` stays the hidden `#roadmapH1` |
| Width | Content fills `.page-inner` (max 1600px). `.view-narrow` caps This week and the blank-roadmap guide at **880px**; the Reference reading column is **760px** |
| Cards | `.card`: 20px padding, 1px border, `--radius-md`, no shadow; `.card-title` 15px |
| Icons | `const icon = (name, size) => Icons.svg(name, {size})`. Needed icons: `plus`, `minus`, `check`, `x`, `trash`, `chevron-right`, `link`, `pencil`, `inbox` |
| Status | Always `statusChip`/`statusSelect` with the four status tokens (green completed, amber in progress, red blocked, grey not started). Labels: **Not started, In progress, Blocked, Completed** (Kanban now uses these too, not "To Do/Done") |
| Depth badge | `depthBadge` keeps its classes and gains `title="D3: Deep / Mastery"` (built from `DATA.meta.depthLevels`; for "D2/D3" both are listed with " · ") |
| Empty state | `emptyState(msg)` → icon `inbox` (32px) + message (no emoji) |
| Dates | Month labels in sentence case: "October 2026" (remove `.toUpperCase()` from `phaseCalendarLabel` and `phaseCalendarLabelFor`) |
| Inline styles | None, except dynamic `width:%` (progress fill), `height:px` (chart bar), `flex-grow:n` (status-bar segment) — and `flex-basis:%` inside `js/month-strip.js` |

### 3.2 Overview

```
Overview
┌──────────────────────────────────────────────────────────────────────────┐
│ 15% complete            [Oct][Nov][Dec][Jan][Feb][Mar][Apr][May][Jun][Jul]│
│ 124 of 849 tasks done     (large Month Strip with labels; click = Timeline)│
│ ──────────────────────────────────────────────────────────────────────── │
│ Current month   Timeline          Momentum                                │
│ M2 System…      36d / 303d        56                                      │
└──────────────────────────────────────────────────────────────────────────┘
┌ Progress by month ──────────────────┐ ┌ Status ───────────────────────────┐
│ M1 — Software…  Oct 1–Oct 31        │ │ ▓▓▓▓░░░░░░░ (stacked bar)         │
│ ████████░░░░ 64%   116 of 180 tasks │ │ ●Completed 124  ●In progress 16   │
│ M2 — System…  [Current]  …          │ │ ●Blocked 8      ●Not started 701  │
│ …                                   │ ├ Pace ─────────────────────────────┤
└─────────────────────────────────────┘ │ At your current pace… Feb 26, 2027 │
┌ Interview & career counters ────────┐ │ This week / Tasks completed per wk │
│ DSA Problems Solved   0 / 180 [−][+]│ └───────────────────────────────────┘
└─────────────────────────────────────┘
```

| Part | Spec |
|---|---|
| Band `.overview-band` | Card with two columns: left `.band-main` (headline `<span class="band-pct-num">{pct}%</span> complete` 40px/600, and "`{completed} of {total} tasks done`"); right `.band-strip` with `MonthStrip.html(months, {size: "lg", labels: true})`. Below, a divider and `.band-metrics`: three `.stat-tile` (**Current month** `M{n}`/`—` + title; **Timeline** `{elapsed}d / {total}d` + "`{n} days remaining`"; **Momentum** count + "tasks completed in the last 7 days"). Under 760px the band is one column |
| Strip data | One month object per phase: `label` = short month name of the phase's start date; `title` = "`Month N: Title (c of t tasks complete). Click to open in the Timeline.`"; counts from `phaseStats`; `current` for the current phase |
| Strip click | A click on a segment (`.band-strip .strip-col`) opens that month in the Timeline (`goToMonth`): marks it expanded, switches view, scrolls the card to the top. Ignored when the strip is collapsed (more than 12 months) |
| Progress by month `<section class="card">` | `ul.month-list`; each `li.month-row` has: a button `.month-link` ("`M{n} — {title}`", `data-action="goto-month"`), a **Current** badge, a green **Done** badge with a check icon at 100%, the date range (right, muted), a progress bar, and "`{c} of {t} tasks`" |
| Status `<section class="card">` | `.status-bar[role="img"]` with `aria-label` "`{c} completed, {i} in progress, {b} blocked, {n} not started`" containing one `span.sb.sb-{status}` per non-zero status (`style="flex-grow:{n}"`); `ul.status-legend` (2×2) of status chip + bold count |
| Pace `<section class="card">` | The old content in classes: lead text, `.pace-date` (20px/600), note; sub-headings "This week" (focus section) and "Tasks completed per week" with the 8-week bar chart (`.bar-chart`) |
| Counters `<section class="card counters-card">` | Only when the roadmap has counters. `ul.counter-list` (auto-fill columns, min 360px or 100%); each `li.counter-row`: label, "`value / target`", progress bar, and `[−] [+]` icon buttons with `aria-label` "Decrease/Increase `<label>`". The existing `counter-dec`/`counter-inc` actions are reused |
| Layout | `.overview-grid`: two columns 3fr/2fr (month list left; Status above Pace on the right); one column under 1100px |
| Empty roadmap | A roadmap with no months shows the blank-roadmap guide instead (3.10) |

### 3.3 Timeline

| Part | Spec |
|---|---|
| Structure | `.timeline` (vertical line + dots). Each month is `div.timeline-item` > `.timeline-dot` (`aria-hidden`; a check icon when done) + `article.phase-card[data-phase-id]` (`.is-current`, `.is-open`) |
| Card header | `header.phase-card-head`: left `.phase-num` ("Month N · October 2026") / `h3.phase-title` (+ **Current**/**Custom** badges) / `.phase-dates` (+ a "Delete month" mini button with trash icon for custom months); right `.phase-head-side`: "`c/t tasks`" and the expand button `.phase-expand-btn` (`data-action="toggle-phase"`, chevron icon that rotates, text Expand/Collapse, `aria-expanded`, `aria-controls="phase-body-<id>"`) |
| Body | Progress bar, objective, and — when open — `div.phase-body#phase-body-<id>` with exit criteria, sections, deliverables, notes (classes `.exit-list`, `.note-block`) |
| Default open state | `timelineState.seeded` (reset in `resetViewState`): the first time the Timeline renders for a roadmap, the **current** month is added to `expandedPhases`; afterwards the user's choices are respected. If today is outside the roadmap nothing opens |
| Sticky header | `.phase-card.is-open > .phase-card-head` is `position: sticky; top: 57px` on screens ≥ 1024px (static below), with an elevated background and a bottom border |
| Sections | `div.week-head` > `h4.week-heading` > `button.week-toggle[data-action="toggle-section"][aria-expanded]` (chevron + title) and `.week-meta` (dates, `done/total`, trash button for custom sections). The deliverables block uses a static `h4` |
| Add buttons | `.add-topic-btn` with a plus icon: "Add month (Month N · <Month YYYY>)", "Add section to this month", "Add topic to this week/section"; `.mini-btn` "Task" (plus icon) and trash icon (with `aria-label`) on custom topics |

### 3.4 Task rows (`subtaskRow`, used by Timeline, Checklist, This week)

`div.subtask-row[data-row-id]` is a 3-column grid (`checkbox | main | controls`), min-height 40px:

| Part | Spec |
|---|---|
| Checkbox | `.subtask-checkbox` (`data-action="toggle-complete"`), `aria-label` = the task title |
| Main | `.subtask-title` (strike-through when done), optional `.topic-crumbs` ("Month N · Section · Topic", only where `showCrumbs`), optional `.subtask-note-preview` (“first 80 characters…”) |
| Controls `.subtask-meta` | due tag (red "Overdue · …" when late), link (`a.subtask-link` with link icon + "Link", `aria-label` "Link for: <title>"), the status select (`aria-label` "Status: <title>"), **Details** (`.mini-btn`, pencil icon + text, `aria-label` "Details: <title>"), and for custom tasks a danger icon button (x, `aria-label` "Remove task: <title>") |
| Overdue | `.overdue` adds a 3px red inset edge |
| Narrow | Under 720px the controls drop under the title (single column grid) |

### 3.5 Checklist

| Part | Spec |
|---|---|
| Filter bar | `.filter-bar.is-sticky` (sticky at `top: 57px` from 1024px up, with page background and a bottom border): five chips **All, Not started, In progress, Blocked, Completed**, each `aria-pressed` with a `.chip-count`; a "Filter by month" select (max-width 100% so it never overflows); right-aligned `.filter-count` `role="status"` "`N tasks`" |
| Counts | Chip counts respect the **search** and the **month** filter but not the status filter itself (so you can see how many each chip would show). `All` = number of matching tasks |
| Body | `#checklistBody` > `section.phase-section-group` > `h3.psg-head` ("Month N — Title") > `.cl-section` > `h4.cl-section-title` > `.topic-block` (title, depth badge, Custom badge) > task rows |
| Empty | "No tasks match your filters." or, for a roadmap without tasks, "This roadmap has no tasks yet. Add months, topics and tasks from the Timeline." |

### 3.6 This week

`div.view-narrow`: `viewHead("This week")`; `section.card.focus-card` with "Month N — **Title** · Section" (or, outside a month, "Today isn't inside a planned month — showing anything with a near-term due date."); optional `h3.list-heading.list-heading-danger` "Overdue (n)" + rows; `h3.list-heading` "Active now (n)" + rows (with crumbs) or the empty state "Nothing active right now — check the Checklist view or get ahead on next week."

### 3.7 Kanban

| Part | Spec |
|---|---|
| Toolbar | Month select (`data-action="kanban-phase"`, `aria-label="Month"`) and the hint "Drag cards between columns, or change a card's status with its dropdown." |
| Board | `.kanban-board`: 4 equal columns ≥ 1001px. **At or below 1000px** it becomes a horizontally scrolling strip (`grid-auto-flow: column`, columns `min(300px, 86%)`, `scroll-snap-type: x mandatory`) that scrolls **inside itself** — the page never scrolls sideways |
| Column | `section.kanban-col[data-action="kanban-dropzone"][data-status][aria-label]`, 3px coloured top edge (grey / amber / red / green), header with the label and a count pill `.kanban-count`. Order: Not started, In progress, Blocked, Completed |
| Card | `.kanban-card[draggable][data-id][data-action="kanban-card"]`: title, path ("Section · Topic[ · Custom]"), and `.k-actions` with the status select (the keyboard alternative to dragging) and a pencil icon button (`aria-label` "Details: <title>") opening the details dialog |
| Behaviour | Drag-and-drop handlers are unchanged; drop zones get `.drag-over`; changing the select moves the card (re-render) and saves |
| Empty | No months → heading + `emptyState("Add a month with some tasks from the Timeline to use the board.")` |

### 3.8 Skills checklist

`viewHead("Skills checklist", "A flat, non-date-bound reference checklist … Track these independently of the month-by-month timeline.")`; `.mastery-grid` (auto-fill, min 320px); each group `section.mastery-cat`: `h3` (title + `.mastery-count` "done/total"), a progress bar, and rows (`.mastery-skill-row`: checkbox labelled by the skill, `.skill-title` (`.done` strikes it through via CSS), depth badge). Groups with no search match are hidden.

### 3.9 Reference

| Part | Spec |
|---|---|
| Layout | `.ref-layout`: from 1024px, two columns `260px | minmax(0, 760px)`; below, one column |
| List | `nav.ref-nav[aria-label="Reference documents"]` (sticky, `top: 73px`, scrolls if long) with one `.ref-nav-btn` per **matching** document (`data-action="ref-jump"`, `data-id="ref-doc-<i>"`) |
| Small screens | The list is hidden and a `select#refJump.ref-select` ("Jump to a document…" + the matching documents, preceded by a visually hidden label) is shown; choosing an option scrolls to it and resets the select |
| Documents | `article.card.ref-card#ref-doc-<i>` (`scroll-margin-top: 73px`) with `h3` and the blocks (`.ref-block`, 14px/1.65, tables supported and scrollable). Non-matching documents get `.ref-search-hidden` |
| Search | The existing top-bar search filters documents (title + text) |

### 3.10 Blank roadmap (`renderBlankRoadmap`)

`div.view-narrow`: `viewHead("Let's build your roadmap", "This roadmap is empty. Lay it out the way the AI Engineer roadmap is organised.")`; `ol.build-steps` of three `li.build-step` (numbered circle `.step-num[aria-hidden]` + bold title + one line): **Add a month** — "A block of time with an objective."; **Add sections** — "A week, or a theme, inside the month."; **Add topics and tasks** — "Subjects to cover, and the checkable steps inside them. You can add these from the Timeline at any time."; then a large primary button `data-action="add-month"` "**+ Add first month**" (plus icon).

### 3.11 Dialogs (all of them)

1. Every dialog is shown with `showModal()` (the nine sites that removed `hidden` directly are converted): task details, reset, add topic, add tasks, add month, add section, start month, conflict, legacy import, and the Phase 3 ones.
2. `showModal` additionally: (a) if the opener sits inside a menu panel (`.profile-panel`), focus returns to that menu's **trigger button** (the item itself is hidden once the menu closes); (b) if nothing inside the dialog has focus after opening, the **first enabled control** receives it.
3. `trapModalFocus` also pulls focus back inside when it is outside the dialog (Tab → first control, Shift+Tab → last).
4. Every `<label>` followed by an input/select/textarea gets `for="<id>"` (13 labels).
5. Inline-styled text becomes classes: `.dialog-sub` (small muted line under the title), `.dialog-text`, `.dialog-hint`, `.dialog-list`, `.dialog-warn`, `.field-hint`, `.modal-note`.
6. `onModalClick` uses `closest("[data-action]")`.

### 3.12 Responsive behaviour

| Width | Behaviour |
|---|---|
| ≥ 1100 | Overview: month list + side column. ≥ 1024: sticky month headers, sticky checklist filters, Reference two-pane |
| < 1100 | Overview single column |
| < 1024 | Sticky headers/filters off; Reference list becomes the "Jump to" select |
| ≤ 1000 | Kanban scrolls inside itself with snap points |
| < 760 | Overview band single column |
| < 720 | Task controls wrap under the title |

No page-level horizontal scrolling at 320–1600px. The month and status dropdowns have `max-width: 100%`; the counter grid uses `minmax(min(360px, 100%), 1fr)`.

### 3.13 Accessibility requirements

- Heading order: `h1` (hidden) → `h2.view-title` → `h3` cards/groups → `h4` sections.
- All icon-only buttons have `aria-label`; decorative icons are `aria-hidden`; the strips and status bar are `role="img"` with a text summary; the Overview strip click has a keyboard equivalent (the month links).
- Section and month toggles are buttons with `aria-expanded`; filter chips have `aria-pressed`; `.filter-count` is a status region.
- Dialog behaviour as in 3.11. Focus ring unchanged (Phase 0).
- axe-core WCAG 2.2 A/AA: 0 violations on all seven views in light and dark, the blank roadmap, the details/reset/start-month/add-month dialogs, and phone and tablet layouts.

---

## 4. Tasks (do them in this order)

> Run every `python3 step4_*.py` from the **repository root**. Keep scripts outside the repo (or delete them afterwards); **do not commit them.**

### Task 1 — Baseline
Confirm Section 2 passes (79/79).

### Task 2 — `css/roadmap.css`
Create from **Appendix A1** verbatim.
**Acceptance:** file exists (300 lines).

### Task 3 — Views, helpers, handlers and dialogs in `js/app.js`
Run **Appendix B2** (`step4_appjs.py`).
**Intent (manual fallback):**
(a) replace the block from `progressBar` up to the `// VIEW: Overview` banner with the new render helpers (`progressBar`, `statusChip`, `statusSelect`, `depthBadge` with tooltip, `dueTag`, `matchesSearch`, `icon`, `viewHead`, `emptyState`, `subtaskRow`);
(b) replace the block from `renderBlankRoadmap` up to the `// Toasts & Confetti` banner with the redesigned views (`renderBlankRoadmap`, `goToMonth`, `renderOverview`, `timelineState`, `renderTimeline`, `renderPhaseBody`, `renderTopics`, `indexEntry`, `renderChecklist`, `renderThisWeek`, `renderKanban`, `renderMastery`, `renderBlockAsHtml`, `jumpToReference`, `renderReference`);
(c) `onMainClick`: handle the Overview strip, use `closest("[data-action]")`, add `goto-month` and `ref-jump`; `onMainChange`: add `ref-jump-select`; `resetViewState`: add `timelineState.seeded = false`;
(d) replace `onModalClick` with the `closest()` version;
(e) in `showModal`: menu-opener rule and default focus (3.11); in `trapModalFocus`: pull focus inside; convert every direct `host.classList.remove("hidden")` to `showModal()`; add `for=` to labels;
(f) replace inline styles with the classes in 3.11 and the skeleton classes (`sk-*`); update the confetti colours; remove `.toUpperCase()` from the two month-label helpers.
**Acceptance:** prints `js/app.js updated (13 dialog labels linked to their controls)`; `node --check js/app.js` passes. (The script's own final check fails if any non-dynamic inline style is left.)

### Task 4 — Icons, stylesheet link, legacy CSS
Run **Appendix B1** (`step4_misc.py`).
**Intent:** add `link`, `pencil`, `inbox` to `js/icons.js`; link `css/roadmap.css` after `css/home.css` in `index.html` (`styles.css` stays last); cut `css/styles.css` back to the account-menu rules (everything from `/* ---------------- Generic card / grid` to the end moves to `roadmap.css`).
**Acceptance:** prints `js/icons.js, index.html and css/styles.css updated`.

### Task 5 — Documentation (required by `CLAUDE.md`)
Run **Appendix B3** (`step4_docs.py`). Also copy this spec to `.claude/specs/ui-redesign-phase-4.md` (recommended).
**Acceptance:** prints `docs updated`.

### Task 6 — Verify
Follow Section 7.

---

## 5. Contracts

### 5.1 Preserved

`#main`, `#tabs .tab[data-view]`, `data-action` values `toggle-complete`, `set-status`, `open-edit`, `delete-task`, `toggle-phase`, `toggle-section`, `add-month`, `add-section`, `add-topic`, `add-task`, `delete-month`, `delete-section`, `delete-topic`, `filter-status`, `filter-phase`, `kanban-phase`, `kanban-card`, `kanban-dropzone`, `counter-inc`, `counter-dec`; `.subtask-row`, `.subtask-checkbox`, `.mini-btn`, `.stat-tile`, `.kanban-board`, `.kanban-card`, `.kanban-col`, `.chip-filter`, `.select-filter`, `.badge-*`, `.status-chip`; dialog field IDs (`modalStatus`, `modalDue`, `modalLink`, `modalNotes`, `topicTitleInput`, …).

### 5.2 New `data-action` values and IDs

`goto-month` (`data-id` = phase id), `ref-jump` (`data-id` = `ref-doc-<i>`), `ref-jump-select`; IDs `refJump`, `phase-body-<phaseId>`, `ref-doc-<i>`, `ovMonths`, `ovStatus`, `ovPace`, `ovCounters`.

### 5.3 New functions and state in `js/app.js`

`icon`, `viewHead`, `goToMonth`, `jumpToReference`, `timelineState`. (Changed: `depthBadge`, `subtaskRow`, `emptyState`, all `render*` views, `onMainClick`, `onMainChange`, `onModalClick`, `showModal`, `trapModalFocus`, `resetViewState`.)

### 5.4 New CSS classes (`css/roadmap.css`)

Shared: `.view-head`, `.view-title`, `.view-sub`, `.view-narrow`, `.card-title`, `.card-subtitle`, `.stat-unit`, `.mini-btn-danger`, `.filter-count`. Overview: `.overview-band`, `.band-main`, `.band-pct(-num)`, `.band-sub`, `.band-strip`, `.band-metrics`, `.overview-grid`, `.overview-side`, `.month-list`, `.month-row(-head)`, `.month-link`, `.month-dates`, `.month-count`, `.status-bar`, `.sb(-status)`, `.status-legend`, `.pace-*`, `.counter-*`, `.counters-card`. Timeline: `.phase-head-text`, `.phase-head-side`, `.phase-count`, `.phase-body`, `.phase-objective`, `.week-heading`, `.week-toggle`, `.exit-list`, `.note-block`. Kanban: `.kanban-hint`, `.kanban-count`, `.k-actions`. Others: `.focus-card`, `.focus-line`, `.list-heading`, `.cl-section(-title)`, `.mastery-count`, `.ref-layout`, `.ref-nav(-btn)`, `.ref-select`, `.ref-content`, `.build-steps`, `.build-step`, `.step-num`, `.sk-*`, `.dialog-sub|hint|list|warn`, `.modal-note`.

---

## 6. Acceptance criteria (checklist)

**Overview**
- [ ] Headline % and "x of y tasks done" match the data; the strip has one labelled segment per month with the current month marked; three `.stat-tile` metrics.
- [ ] Status bar `aria-label` and legend counts equal the status totals; month list shows one row per month with correct counts; the **Current**/**Done** badges appear correctly.
- [ ] A month link and a strip segment both open that month, expanded, in the Timeline.
- [ ] Counter +/− work (also when the click lands on the icon), are named per counter, and save.

**Timeline / Checklist / This week**
- [ ] On a fresh visit only the current month is open; Expand/Collapse toggles `aria-expanded`; open months have a sticky header on desktop; section titles are headings containing a keyboard-operable button.
- [ ] Task rows are ≥ 40px high; the checkbox is named by the task title; Details opens the dialog.
- [ ] Checklist chip counts are correct; the Blocked filter shows exactly the blocked tasks; the filter bar stays pinned under the top bar; month filter and top-bar search narrow the list.
- [ ] This week is at most 880px wide with a focus card and an "Active now" list.

**Kanban / Skills / Reference**
- [ ] Four columns in order with distinct top colours; counts add up to the month's tasks; the dropdown moves a card and saves; drag-and-drop still works; the pencil opens the details dialog.
- [ ] Skills: 13 groups each with a progress bar; ticking a skill updates the group's count; finished skills are struck through by class.
- [ ] Reference: every document appears in the list and the page; choosing one scrolls it to the top; the reading column is ≤ 760px; search hides non-matching documents in both places; below 1024px a "Jump to" select replaces the list.

**Blank roadmap and dialogs**
- [ ] The blank roadmap shows the 3-step guide and **Add first month**.
- [ ] Every dialog: named (`role=dialog`, `aria-labelledby`), labels tied to fields, Escape closes, Tab stays inside, focus returns to the opener (to the **Roadmap** menu button when opened from that menu).

**Cleanliness and quality**
- [ ] No emoji or glyph icons anywhere except the 🎉 in the celebration toast (source scan in 7.3).
- [ ] `grep -c 'style="' js/app.js` → **3**, all dynamic (progress width, status-bar `flex-grow`, chart bar height).
- [ ] axe-core 0 violations (3.13); no console/CSP errors; no horizontal page scrolling at 390px and 820px; the Kanban board scrolls inside itself on phones.
- [ ] `npm test` 79/79; **no change under `server/` or `test/`**.
- [ ] Phase 0–3 harnesses pass; the static ID check reports nothing missing.
- [ ] Docs updated.

---

## 7. Verification

### 7.1 Automated
```bash
npm test      # expect: tests 79, pass 79, fail 0
```

### 7.2 Static checks
```bash
# (a) no element ID used by app.js is missing  — the check from the Phase 2 spec, section 7.2. Expect: missing ids: []
# (b) inline styles left in app.js: exactly the three dynamic ones
grep -c 'style="' js/app.js          # expect: 3
grep -n 'style="' js/app.js | sed 's/.*\(style="[^"]*"\).*/\1/'
# expect: style="width:${pct}%" / style="flex-grow:${n}" / style="height:${Math.round((s.count / maxBar) * 70) || 2}px"
```

### 7.3 Source scan for emoji and glyph icons
```bash
python3 - <<'EOF'
import re
s = open("js/app.js", encoding="utf-8").read()
pat = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFF0B\u25A0-\u25FF\u2190-\u21FF\u2713\u2715\u270E]")
hits = [(i, m.group()) for i, line in enumerate(s.split("\n"), 1) for m in pat.finditer(line)]
print(hits)                       # expect exactly one hit: the 🎉 in the celebration toast
EOF
```

### 7.4 UI harnesses

Keep these **outside the repo** in one folder (e.g. `/tmp/ui-verify/`): `serve-demo.js` + `verify_phase0.py` (Phase 0 spec), `verify_phase1.py` (Phase 1 spec), `verify_phase2.py` (Phase 2 spec, patched by the Phase 3 spec's Task 5), `verify_phase3.py` (Phase 3 spec) and this phase's `verify_phase4.py` (Appendix C1).

```bash
npm install --prefix /tmp/ui-verify axe-core
node /tmp/ui-verify/serve-demo.js "$(pwd)" 3111 &                 # keep running
AXE=/tmp/ui-verify/node_modules/axe-core/axe.min.js; U=http://127.0.0.1:3111
python3 /tmp/ui-verify/verify_phase4.py $U $AXE      # expect: RESULT 121/121
python3 /tmp/ui-verify/verify_phase3.py $U $AXE      # regression: RESULT 88/88
python3 /tmp/ui-verify/verify_phase2.py $U $AXE      # regression (patched): RESULT 114/114
python3 /tmp/ui-verify/verify_phase1.py $U $AXE      # regression: RESULT 67/67
python3 /tmp/ui-verify/verify_phase0.py $U $AXE      # regression: RESULT 61/61
```

The Phase 4 harness registers fresh users, seeds the built-in roadmap with known progress (35 completed, 6 in progress, 4 blocked) through the API, then checks every view's content against that data (including the status bar summary and chip counts), keyboard behaviour, drag-and-drop, sticky positions, the dialogs, a blank custom roadmap, dark theme, and phone/tablet layouts; it runs axe on each. It adapts to today's date for the "current month" checks. Screenshots go to `/tmp/ui-verify/shots-p4`.

### 7.5 Visual checklist

| Screenshot | What you should see |
|---|---|
| `overview-light.png` | A white band: big "15% complete" at the left, a 10-segment strip with month labels (Oct first, current month underlined in blue) at the right, and three metrics underneath. Below: "Progress by month" list on the left; "Status" (stacked bar + legend) and "Pace" on the right; "Interview & career counters" as compact rows with − / + buttons |
| `timeline-light.png` | Page title "Timeline"; month cards on a vertical line; the current month open with a blue outline, a sticky header (month label, title, "Current" badge, dates, "n/m tasks", **Collapse**), a progress bar, week sections with chevrons, and task rows: checkbox, title, status dropdown, **Details** button |
| `checklist-light.png` | Sticky chip bar "All 849 · Not started · In progress · Completed · Blocked" with counts, a month dropdown, "849 tasks"; dense rows with the status dropdown and **Details** at the right |
| `kanban-light.png` | Four columns with grey / amber / red / green top edges and count pills; compact cards each with a status dropdown and a pencil button |
| `mastery-light.png` | Cards in a grid, each with a title, "done/total", a progress bar and checkbox rows |
| `reference-light.png` | A left list of document titles and a white reading column with the first document |
| `blank-roadmap.png` | Title "Let's build your roadmap", three numbered step cards, a large blue "+ Add first month" button |
| `checklist-phone.png`, `reference-phone.png` | Task controls wrap under the title; Reference shows a "Jump to a document…" dropdown instead of the side list |
| `*-dark.png` | The same layouts in the dark theme |

### 7.6 Known and acceptable

- The 🎉 in the month-completion toast is intentional.
- Kanban card paths can repeat a section and topic name that are nearly identical in the roadmap data; this is the data, not the layout.
- Month and status colours in the Month Strip depend on today's date (which month is "current").
- The Overview strip segments are mouse-clickable only; the keyboard route is the month links beside them.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Buttons with icons do nothing | A handler still reads `e.target.dataset` — use `closest("[data-action]")` (Task 3c, d) |
| Overview never "loads" in tests | The Overview has no `.stat-tile`; keep the three metrics as `.stat-tile` |
| Timeline starts fully collapsed | `timelineState.seeded` not defined/reset, or `expandedPhases` seeded on every render |
| Sticky header overlaps the top bar | The offset is 57px (top bar height); check the top bar still has `min-height: 56px` + 1px border |
| Page scrolls sideways on phones | A grid with a fixed 360px minimum, or an unconstrained `<select>`; use `min(360px, 100%)` and `max-width: 100%` |
| Reference jump does nothing | `data-id` must be the card's `id` (`ref-doc-<i>`); the select uses `data-action="ref-jump-select"` handled in `onMainChange` |
| Dialog does not return focus | It still removes `hidden` directly instead of calling `showModal()` |
| Reset dialog: focus escapes with Tab | Missing the two `showModal`/`trapModalFocus` changes (Task 3e) |
| axe: "form elements must have labels" in a dialog | A `<label>` without `for` (Task 3e adds them) |
| A harness fails at a delete step | Apply the Phase 2 harness patch from the Phase 3 spec |
| A `step4_*.py` assertion fails | Repo drifted; apply the Intent list manually |

---

## 9. Hand-off

Report: commits, `npm test`, all five harness result lines, the static checks (7.2–7.3) and any manual deviations.

**Phase 5 assumes** these exist and are unchanged: `css/roadmap.css` (all view styles) and `css/styles.css` containing **only** the account-menu rules (`.profile-anchor`, `.profile-trigger`, `.profile-panel*`, `.profile-theme-btn*`, `.profile-action-btn`, `.profile-logout`, `.profile-trigger-caret`) so that Phase 5 can move them into `shell.css` and delete the file; the shared dialog helpers; the icon set; and the harnesses.

**Rollback:** revert the Phase 4 commits. No data, API or server change was made.

---

# Appendices


## Appendix A1 — `css/roadmap.css`

```css
/* ===========================================================
   Roadmap views: shared building blocks, Overview, Timeline, Checklist,
   This week, Kanban, Skills checklist, Reference, blank roadmap, and the
   small text styles used inside dialogs.
   =========================================================== */

/* ---------------- Shared ---------------- */
.view-head { margin-bottom: 20px; }
.view-title { margin: 0; font-size: 24px; line-height: 32px; letter-spacing: -0.01em; }
.view-sub { margin: 4px 0 0; max-width: 70ch; color: var(--text-muted); font-size: 14px; }
.view-narrow { max-width: 880px; }

.card { padding: 20px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.card-title { margin: 0 0 12px; font-size: 15px; line-height: 22px; }
.card-subtitle { margin: 20px 0 8px; font-size: 13px; font-weight: 600; color: var(--text-muted); }
.grid { display: grid; gap: 16px; }
.grid-stats { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }

.stat-tile { padding: 14px 16px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.stat-label { font-size: 13px; color: var(--text-muted); }
.stat-value { margin-top: 4px; font-size: 22px; line-height: 28px; font-weight: 600; letter-spacing: -0.01em; font-variant-numeric: tabular-nums; }
.stat-unit { font-size: 14px; font-weight: 400; color: var(--text-faint); }
.stat-sub { margin-top: 2px; font-size: 13px; color: var(--text-faint); }

.empty-state { padding: 56px 20px; text-align: center; color: var(--text-muted); }
.empty-state .icon { display: block; margin: 0 auto 12px; color: var(--text-faint); }
.empty-state p { margin: 0; }
.empty-hint { margin: 12px 0 0; font-size: 13px; color: var(--text-faint); }

.mini-btn .icon { flex-shrink: 0; }
.mini-btn { gap: 4px; }
.mini-btn-danger { color: var(--danger); }
.mini-btn-danger:hover { background: var(--danger-soft); border-color: var(--danger); }

.filter-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 16px; }
.chip-filter {
  display: inline-flex; align-items: center; gap: 4px; min-height: 32px; padding: 0 12px;
  border: 1px solid var(--border-strong); border-radius: 99px; background: var(--bg-elevated);
  color: var(--text-muted); font-size: 13px; font-weight: 500;
}
.chip-filter:hover { background: var(--bg-sunken); }
.chip-filter.active { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.select-filter {
  min-height: 32px; max-width: 100%; padding: 0 10px; border: 1px solid var(--border-strong); border-radius: 99px;
  background: var(--bg-elevated); color: var(--text); font-size: 13px;
}
.filter-count { margin-left: auto; font-size: 13px; color: var(--text-faint); font-variant-numeric: tabular-nums; }

/* ---------------- Overview ---------------- */
.overview-band {
  display: grid; gap: 20px 32px; margin-bottom: 16px; padding: 24px;
  grid-template-columns: minmax(150px, 220px) minmax(0, 1fr);
  grid-template-areas: "main strip" "metrics metrics";
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md);
}
.band-main { grid-area: main; }
.band-pct { margin: 0; color: var(--text-muted); }
.band-pct-num { font-size: 40px; line-height: 44px; font-weight: 600; letter-spacing: -0.02em; color: var(--text); font-variant-numeric: tabular-nums; }
.band-sub { margin: 4px 0 0; font-size: 13px; color: var(--text-muted); }
.band-strip { grid-area: strip; align-self: center; }
.band-strip .strip-col { cursor: pointer; }
.band-strip .strip-col:hover .strip-seg { box-shadow: inset 0 0 0 1px var(--accent); }
.band-metrics {
  grid-area: metrics; display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 16px;
  padding-top: 18px; border-top: 1px solid var(--border);
}
.band-metrics .stat-tile { padding: 0; border: 0; background: none; }
@media (max-width: 760px) {
  .overview-band { padding: 18px; grid-template-columns: minmax(0, 1fr); grid-template-areas: "main" "strip" "metrics"; }
}

.overview-grid { display: grid; gap: 16px; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); align-items: start; margin-bottom: 16px; }
.overview-side { display: flex; flex-direction: column; gap: 16px; }
@media (max-width: 1100px) { .overview-grid { grid-template-columns: minmax(0, 1fr); } }

.month-list { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 16px; }
.month-row-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 6px; }
.month-link { padding: 0; border: 0; background: none; font: inherit; font-weight: 600; color: var(--text); text-align: left; }
.month-link:hover { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }
.month-dates { margin-left: auto; font-size: 13px; color: var(--text-faint); white-space: nowrap; }
.month-count { margin-top: 2px; font-size: 12px; color: var(--text-faint); font-variant-numeric: tabular-nums; }

.status-bar { display: flex; height: 14px; overflow: hidden; border-radius: 99px; background: var(--bg-sunken); }
.sb { display: block; flex-basis: 0; min-width: 4px; }
.sb-completed { background: var(--status-completed); }
.sb-in_progress { background: var(--status-in-progress); }
.sb-blocked { background: var(--status-blocked); }
.sb-not_started { background: var(--border-strong); }
.status-legend { margin: 14px 0 0; padding: 0; list-style: none; display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; }
.status-legend li { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.status-legend strong { font-variant-numeric: tabular-nums; }

.pace-lead { margin: 0 0 4px; font-size: 14px; }
.pace-date { margin: 0 0 4px; font-size: 20px; font-weight: 600; }
.pace-note { margin: 0; font-size: 13px; color: var(--text-faint); }

.bar-chart { display: flex; align-items: flex-end; gap: 6px; height: 90px; padding-top: 10px; }
.bar-chart .bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.bar-chart .bar { width: 100%; min-height: 2px; background: var(--accent); border-radius: 4px 4px 0 0; }
.bar-chart .bar-label { font-size: 11px; color: var(--text-faint); }

.counter-list { margin: 0; padding: 0; list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(360px, 100%), 1fr)); gap: 4px 32px; }
.counter-row {
  display: grid; align-items: center; gap: 4px 12px; padding: 10px 0; border-top: 1px solid var(--border);
  grid-template-columns: minmax(0, 1fr) auto auto; grid-template-areas: "label value steps" "bar bar bar";
}
.counter-label { grid-area: label; font-weight: 500; }
.counter-value { grid-area: value; font-variant-numeric: tabular-nums; font-weight: 600; }
.counter-bar { grid-area: bar; }
.counter-steps { grid-area: steps; display: inline-flex; gap: 6px; }
.counters-card { margin-bottom: 16px; }

/* ---------------- Timeline ---------------- */
.timeline { position: relative; padding-left: 28px; }
.timeline::before { content: ""; position: absolute; left: 9px; top: 6px; bottom: 6px; width: 2px; background: var(--border); }
.timeline-item { position: relative; margin-bottom: 14px; }
.timeline-dot {
  position: absolute; left: -28px; top: 20px; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;
  border: 2px solid var(--border-strong); border-radius: 50%; background: var(--bg);
}
.timeline-item.is-current .timeline-dot { border-color: var(--accent); background: var(--accent-soft); }
.timeline-item.is-done .timeline-dot { border-color: var(--status-completed); background: var(--status-completed-bg); color: var(--status-completed); }

.phase-card { position: relative; padding: 16px 18px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.phase-card.is-current { border-color: var(--accent); }
.phase-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.phase-card.is-open > .phase-card-head {
  position: sticky; top: 57px; z-index: 5; margin: -16px -18px 12px; padding: 14px 18px 10px;
  background: var(--bg-elevated); border-bottom: 1px solid var(--border); border-radius: var(--radius-md) var(--radius-md) 0 0;
}
@media (max-width: 1023px) { .phase-card.is-open > .phase-card-head { position: static; } }
.phase-num { font-size: 12px; font-weight: 600; color: var(--text-faint); }
.phase-title { margin: 2px 0 0; font-size: 16px; line-height: 24px; }
.phase-dates { margin-top: 2px; font-size: 13px; color: var(--text-faint); }
.phase-dates .mini-btn { margin-left: 8px; }
.phase-head-side { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.phase-count { font-size: 13px; color: var(--text-muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
.phase-expand-btn {
  display: inline-flex; align-items: center; gap: 4px; min-height: 32px; padding: 0 10px;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm); background: var(--bg-elevated);
  color: var(--text); font-size: 13px; font-weight: 500;
}
.phase-expand-btn:hover { background: var(--bg-sunken); }
.phase-expand-btn .caret { display: inline-flex; transition: transform 0.12s ease; }
.phase-card.is-open .phase-expand-btn .caret { transform: rotate(90deg); }
.phase-objective { margin: 10px 0 0; font-size: 13px; color: var(--text-muted); }
.timeline-empty { margin-left: 0; }

.week-block { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--border); }
.week-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.week-heading { margin: 0; font-size: 14px; }
.week-heading-static { padding: 4px 0; }
.week-toggle { display: inline-flex; align-items: center; gap: 6px; padding: 4px 0; border: 0; background: none; font: inherit; font-weight: 600; color: var(--text); text-align: left; }
.week-toggle:hover { color: var(--accent); }
.week-toggle .caret { display: inline-flex; color: var(--text-faint); transition: transform 0.12s ease; }
.week-toggle.open .caret { transform: rotate(90deg); }
.week-meta { font-size: 12px; color: var(--text-faint); white-space: nowrap; font-variant-numeric: tabular-nums; }
.week-meta .mini-btn { margin-left: 8px; }

.topic-block { margin: 10px 0 0; padding: 10px 12px; border-radius: var(--radius-md); background: var(--bg-sunken); }
.topic-head { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 6px; }
.topic-title { font-weight: 600; font-size: 14px; }
.topic-progress { margin-left: auto; font-size: 12px; font-weight: 600; color: var(--text-faint); font-variant-numeric: tabular-nums; }
.group-label { margin: 8px 0 4px; font-size: 12px; font-weight: 600; color: var(--text-muted); }
.group-label-spaced { margin-top: 14px; }
.exit-list { margin: 0; padding-left: 18px; font-size: 13px; color: var(--text-muted); }
.note-block { margin-top: 10px; padding: 10px 12px; border-radius: var(--radius-sm); background: var(--bg-sunken); font-size: 13px; }
.note-text { margin-top: 4px; white-space: pre-wrap; color: var(--text-muted); }

.add-topic-btn {
  display: inline-flex; align-items: center; gap: 6px; margin: 10px 0 0; padding: 7px 12px;
  border: 1px dashed var(--border-strong); border-radius: var(--radius-sm); background: transparent;
  color: var(--text-muted); font-size: 13px; font-weight: 500;
}
.add-topic-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
.add-month-btn { margin: 6px 0 0; padding: 10px 16px; }

/* ---------------- Task rows (Timeline, Checklist, This week) ---------------- */
.subtask-row {
  display: grid; align-items: center; gap: 4px 10px; min-height: 40px; padding: 6px 8px; border-radius: var(--radius-sm);
  grid-template-columns: auto minmax(0, 1fr) auto;
}
.subtask-row:hover { background: var(--bg-elevated); }
.subtask-row.overdue { box-shadow: inset 3px 0 0 var(--status-blocked); }
.subtask-checkbox { width: 18px; height: 18px; margin: 0; accent-color: var(--status-completed); flex-shrink: 0; }
.subtask-main { min-width: 0; }
.subtask-title { font-size: 14px; line-height: 1.4; }
.subtask-title.done { text-decoration: line-through; color: var(--text-faint); }
.topic-crumbs { margin-top: 2px; font-size: 12px; color: var(--text-faint); }
.subtask-note-preview { margin-top: 2px; font-size: 12px; font-style: italic; color: var(--text-faint); }
.subtask-meta { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px 8px; }
.subtask-meta .mini-btn { padding: 0 8px; background: transparent; color: var(--text-muted); }
.subtask-meta .mini-btn:hover { background: var(--bg-sunken); color: var(--text); }
.subtask-meta .mini-btn-danger { color: var(--danger); }
.subtask-link { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: var(--accent); text-decoration: none; }
.subtask-link:hover { text-decoration: underline; }
.due-tag { padding: 2px 8px; border-radius: 99px; background: var(--bg-sunken); color: var(--text-muted); font-size: 12px; font-weight: 500; white-space: nowrap; }
.due-tag.overdue { background: var(--status-blocked-bg); color: var(--status-blocked); }
@media (max-width: 720px) {
  .subtask-row { grid-template-columns: auto minmax(0, 1fr); }
  .subtask-meta { grid-column: 2; justify-content: flex-start; }
}

/* ---------------- Checklist ---------------- */
.filter-bar.is-sticky { position: sticky; top: 57px; z-index: 6; margin-bottom: 8px; padding: 10px 0; background: var(--bg); border-bottom: 1px solid var(--border); }
@media (max-width: 1023px) { .filter-bar.is-sticky { position: static; } }
.phase-section-group { margin-bottom: 20px; }
.psg-head { margin: 16px 0 6px; font-size: 16px; }
.cl-section { margin: 8px 0 12px 8px; }
.cl-section-title { margin: 0 0 4px; font-size: 13px; font-weight: 600; color: var(--text-muted); }

/* ---------------- This week ---------------- */
.focus-card { margin-bottom: 16px; }
.focus-line { margin: 0; font-size: 14px; }
.focus-line-muted { color: var(--text-faint); }
.list-heading { margin: 24px 0 8px; font-size: 14px; font-weight: 600; color: var(--text-muted); }
.list-heading-danger { color: var(--status-blocked); }

/* ---------------- Kanban ---------------- */
.kanban-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; margin-bottom: 14px; }
.kanban-hint { font-size: 13px; color: var(--text-faint); }
.kanban-board { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; align-items: start; }
.kanban-col {
  min-height: 120px; padding: 10px; border-top: 3px solid var(--border-strong);
  background: var(--bg-sunken); border-radius: var(--radius-md);
}
.kanban-col[data-status="in_progress"] { border-top-color: var(--status-in-progress); }
.kanban-col[data-status="blocked"] { border-top-color: var(--status-blocked); }
.kanban-col[data-status="completed"] { border-top-color: var(--status-completed); }
.kanban-col.drag-over { outline: 2px dashed var(--accent); outline-offset: -4px; }
.kanban-col-head { display: flex; align-items: center; justify-content: space-between; padding: 4px 6px 10px; font-size: 13px; font-weight: 600; color: var(--text-muted); }
.kanban-count { min-width: 22px; padding: 1px 8px; border-radius: 99px; background: var(--bg-elevated); border: 1px solid var(--border); text-align: center; font-variant-numeric: tabular-nums; }
.kanban-card { margin-bottom: 8px; padding: 10px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-elevated); cursor: grab; }
.kanban-card:active { cursor: grabbing; }
.kanban-card.drag-ghost { opacity: 0.4; }
.k-title { margin-bottom: 4px; font-size: 13px; font-weight: 600; line-height: 1.35; }
.k-path { font-size: 12px; color: var(--text-faint); }
.k-actions { display: flex; align-items: center; gap: 6px; margin-top: 8px; }
.k-actions .status-select { flex: 1; min-width: 0; }
@media (max-width: 1000px) {
  .kanban-board {
    grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: min(300px, 86%);
    overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: 8px;
  }
  .kanban-col { scroll-snap-align: start; }
}

/* ---------------- Skills checklist ---------------- */
.mastery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; align-items: start; }
.mastery-cat { padding: 16px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.mastery-cat h3 { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin: 0 0 8px; font-size: 14px; }
.mastery-count { font-size: 13px; font-weight: 400; color: var(--text-faint); font-variant-numeric: tabular-nums; }
.mastery-skill-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 14px; }
.mastery-skill-row .skill-title { flex: 1; min-width: 0; }
.skill-title.done { text-decoration: line-through; color: var(--text-faint); }

/* ---------------- Reference ---------------- */
.ref-layout { display: grid; grid-template-columns: 260px minmax(0, 760px); gap: 32px; align-items: start; }
.ref-nav { position: sticky; top: 73px; max-height: calc(100vh - 96px); overflow-y: auto; }
.ref-nav ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 2px; }
.ref-nav-btn { width: 100%; min-height: 32px; padding: 6px 10px; border: 0; border-radius: var(--radius-sm); background: none; color: var(--text-muted); font-size: 13px; text-align: left; }
.ref-nav-btn:hover { background: var(--bg-sunken); color: var(--text); }
.ref-select { display: none; width: 100%; margin-bottom: 12px; border-radius: var(--radius-sm); min-height: 36px; }
.ref-card { margin-bottom: 16px; scroll-margin-top: 73px; }
.ref-card h3 { margin: 0 0 8px; font-size: 16px; }
.ref-block { margin-bottom: 8px; overflow-x: auto; font-size: 14px; line-height: 1.65; color: var(--text-muted); white-space: pre-wrap; }
.ref-block table { width: 100%; margin: 6px 0; border-collapse: collapse; font-size: 13px; white-space: normal; }
.ref-block th, .ref-block td { padding: 6px 8px; border: 1px solid var(--border); text-align: left; }
.ref-block th { background: var(--bg-sunken); }
.ref-search-hidden { display: none !important; }
@media (max-width: 1023px) {
  .ref-layout { grid-template-columns: minmax(0, 1fr); }
  .ref-nav { display: none; }
  .ref-select { display: block; }
}

/* ---------------- Blank roadmap ---------------- */
.build-steps { margin: 0 0 24px; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 12px; }
.build-step { display: flex; align-items: flex-start; gap: 14px; padding: 14px 16px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.build-step p { margin: 2px 0 0; font-size: 13px; color: var(--text-muted); }
.step-num { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; flex-shrink: 0; border-radius: 50%; background: var(--accent-soft); color: var(--accent); font-weight: 600; }

/* ---------------- Loading skeleton blocks ---------------- */
.sk-title { height: 22px; width: 60%; }
.sk-text { height: 36px; }
.sk-bar { height: 8px; }
.sk-action { height: 36px; margin-top: auto; }
.sk-heading { height: 28px; width: 220px; margin-bottom: 20px; }
.sk-tile { height: 92px; }
.sk-panel { height: 320px; margin-top: 20px; }
.roadmap-card.is-skeleton .sk-title + .sk-text { margin-top: 10px; }

/* ---------------- Text inside dialogs ---------------- */
.dialog-sub { margin: -10px 0 16px; font-size: 13px; color: var(--text-faint); }
.dialog-hint { margin: 0 0 12px; font-size: 13px; color: var(--text-faint); }
.dialog-list { margin: 0 0 12px; padding-left: 18px; font-size: 13px; line-height: 1.5; color: var(--text-muted); }
.dialog-warn { margin: 0 0 12px; font-size: 13px; line-height: 1.5; color: var(--status-blocked); }
.modal-note { margin: 12px 0 0; font-size: 13px; color: var(--text-muted); }

#confettiCanvas { position: fixed; inset: 0; z-index: 300; width: 100%; height: 100%; pointer-events: none; }
```

## Appendix B1 — `step4_misc.py` (Task 4)

Run from the repo root: `python3 step4_misc.py` (after creating `css/roadmap.css`).

```python
"""Phase 4 / small additions to earlier files: three icons, the roadmap.css link, and removal of the
old view rules from css/styles.css (they now live in css/roadmap.css).
Run from the repo root: python3 step4_misc.py   (create css/roadmap.css first)"""
import os

assert os.path.exists("css/roadmap.css"), "create css/roadmap.css first (Appendix A1)"

# 1. js/icons.js: link, pencil, inbox
P = "js/icons.js"
s = open(P, encoding="utf-8").read()
ICONS = r'''    link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    pencil: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
    inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
'''
marker = "    help: '<circle"
assert s.count(marker) == 1 and "pencil:" not in s, "icons.js is not in the expected state"
s = s.replace(marker, ICONS + marker)
open(P, "w", encoding="utf-8").write(s)

# 2. index.html: load roadmap.css after home.css (styles.css stays last)
P = "index.html"
s = open(P, encoding="utf-8").read()
old = '<link rel="stylesheet" href="css/home.css" />'
assert s.count(old) == 1 and "roadmap.css" not in s
s = s.replace(old, old + '\n<link rel="stylesheet" href="css/roadmap.css" />')
open(P, "w", encoding="utf-8").write(s)

# 3. css/styles.css: drop everything from the generic card/grid block to the end; only the account-menu rules stay
P = "css/styles.css"
s = open(P, encoding="utf-8").read()
marker = "/* ---------------- Generic card / grid ---------------- */"
assert s.count(marker) == 1, "generic card marker not found"
s = s[:s.index(marker)].rstrip("\n") + "\n"
assert ".profile-panel" in s and ".kanban" not in s and ".subtask-row" not in s
open(P, "w", encoding="utf-8").write(s)
print("js/icons.js, index.html and css/styles.css updated")
```

## Appendix B2 — `step4_appjs.py` (Task 3)

Run from the repo root: `python3 step4_appjs.py`. The new JavaScript is embedded in this script.

```python
"""Phase 4 / js/app.js: the seven views, their helpers, dialogs and inline-style clean-up.
Run from the repo root: python3 step4_appjs.py"""
import re

P = "js/app.js"
s = open(P, encoding="utf-8").read()


def swap_block(start, end, new):
    """Replace everything from `start` up to (not including) `end`."""
    global s
    assert s.count(start) == 1, "start marker not unique/found: " + start[:70]
    a = s.index(start)
    assert end in s[a:], "end marker not found after start: " + end[:70]
    b = s.index(end, a)
    s = s[:a] + new + s[b:]


def once(old, new):
    global s
    assert s.count(old) == 1, f"expected exactly one match ({s.count(old)} found): {old[:80]}"
    s = s.replace(old, new)


# 1. Render helpers (progress bar, chips, depth badge with tooltip, task rows with SVG icons)
NEW_HELPERS = r'''  function progressBar(pct) {
    return `<div class="progress-row">
      <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="progress-pct">${pct}%</div>
    </div>`;
  }

  function statusChip(status) {
    return `<span class="status-chip status-${status}">${STATUS_LABEL[status]}</span>`;
  }

  function statusSelect(id, status) {
    const entry = indexEntry(id);
    const label = entry ? `Status: ${entry.title}` : "Status";
    return `<select class="status-select" data-action="set-status" data-id="${id}" aria-label="${esc(label)}">
      ${STATUS.map((s) => `<option value="${s}" ${s === status ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}
    </select>`;
  }

  // Depth badge; the tooltip spells out what each code means (D3: Deep / Mastery, …).
  function depthBadge(depth) {
    if (!depth) return "";
    const code = depth.split("/")[0].trim();
    const cls = code.startsWith("D3") ? "badge-depth-D3" : code.startsWith("D2") ? "badge-depth-D2" : "badge-depth-D1";
    const levels = (DATA.meta && DATA.meta.depthLevels) || (BUILTIN_DATA.meta && BUILTIN_DATA.meta.depthLevels) || [];
    const tip = depth.split("/").map((c) => {
      const level = levels.find((l) => l.code === c.trim());
      return level ? `${level.code}: ${level.label}` : "";
    }).filter(Boolean).join(" · ");
    return `<span class="badge ${cls}"${tip ? ` title="${esc(tip)}"` : ""}>${esc(depth)}</span>`;
  }

  function dueTag(dueDate, status) {
    if (!dueDate) return "";
    const d = parseDate(dueDate);
    const overdue = d && d < TODAY && status !== "completed";
    return `<span class="due-tag ${overdue ? "overdue" : ""}">${overdue ? "Overdue · " : "Due "}${fmtDateShort(d)}</span>`;
  }

  function matchesSearch(entry, q) {
    if (!q) return true;
    const hay = (entry.title + " " + entry.topicTitle + " " + entry.phaseTitle + " " + (getItem(entry.id).notes || "")).toLowerCase();
    return hay.includes(q);
  }

  // Small building blocks shared by the views
  const icon = (name, size) => window.Icons.svg(name, { size: size || 16 });

  function viewHead(title, sub) {
    return `<header class="view-head"><h2 class="view-title">${esc(title)}</h2>${sub ? `<p class="view-sub">${esc(sub)}</p>` : ""}</header>`;
  }

  function emptyState(msg) {
    return `<div class="empty-state">${icon("inbox", 32)}<p>${esc(msg)}</p></div>`;
  }

  // ---------------------------------------------------------
  // Subtask row (shared by Checklist / This Week / Timeline)
  // ---------------------------------------------------------
  function subtaskRow(entry, opts) {
    opts = opts || {};
    const item = getItem(entry.id);
    const checked = item.status === "completed";
    const overdueCls = item.dueDate && parseDate(item.dueDate) < TODAY && !checked ? "overdue" : "";
    const title = esc(entry.title);
    return `<div class="subtask-row ${overdueCls}" data-row-id="${entry.id}">
      <input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${entry.id}" ${checked ? "checked" : ""} aria-label="${title}" />
      <div class="subtask-main">
        <div class="subtask-title ${checked ? "done" : ""}">${title}</div>
        ${opts.showCrumbs ? `<div class="topic-crumbs">Month ${entry.phaseNumber} · ${esc(entry.sectionTitle)} ${entry.topicTitle && entry.topicTitle !== "Deliverables" ? "· " + esc(entry.topicTitle) : ""}</div>` : ""}
        ${item.notes ? `<div class="subtask-note-preview">“${esc(item.notes.slice(0, 80))}${item.notes.length > 80 ? "…" : ""}”</div>` : ""}
      </div>
      <div class="subtask-meta">
        ${dueTag(item.dueDate, item.status)}
        ${item.link ? `<a class="subtask-link" href="${esc(item.link)}" target="_blank" rel="noopener" aria-label="Link for: ${title}">${icon("link", 14)}<span>Link</span></a>` : ""}
        ${statusSelect(entry.id, item.status)}
        <button type="button" class="mini-btn" data-action="open-edit" data-id="${entry.id}" aria-label="Details: ${title}">${icon("pencil", 14)}<span>Details</span></button>
        ${entry.custom ? `<button type="button" class="mini-btn mini-btn-danger" data-action="delete-task" data-id="${entry.id}" aria-label="Remove task: ${title}" title="Remove this task">${icon("x", 14)}</button>` : ""}
      </div>
    </div>`;
  }

'''
swap_block("  function progressBar(pct) {",
           "  // ---------------------------------------------------------\n  // VIEW: Overview", NEW_HELPERS)

# 2. The seven views + the blank-roadmap state
NEW_VIEWS = r'''  function renderBlankRoadmap(container) {
    container.innerHTML = `
      <div class="view-narrow">
        ${viewHead("Let's build your roadmap", "This roadmap is empty. Lay it out the way the AI Engineer roadmap is organised.")}
        <ol class="build-steps">
          <li class="build-step"><span class="step-num" aria-hidden="true">1</span><div><strong>Add a month</strong><p>A block of time with an objective.</p></div></li>
          <li class="build-step"><span class="step-num" aria-hidden="true">2</span><div><strong>Add sections</strong><p>A week, or a theme, inside the month.</p></div></li>
          <li class="build-step"><span class="step-num" aria-hidden="true">3</span><div><strong>Add topics and tasks</strong><p>Subjects to cover, and the checkable steps inside them. You can add these from the Timeline at any time.</p></div></li>
        </ol>
        <button type="button" class="btn btn-primary btn-lg" data-action="add-month">${icon("plus")} Add first month</button>
      </div>`;
  }

  function goToMonth(phaseId) {
    expandedPhases[phaseId] = true;
    setView("timeline");
    const card = document.querySelector(`.phase-card[data-phase-id="${CSS.escape(phaseId)}"]`);
    if (card) card.scrollIntoView({ block: "start" });
  }

  function renderOverview(container) {
    if (allPhases().length === 0) { renderBlankRoadmap(container); return; }
    const overall = overallStats();
    const cur = currentPhase();
    const curSection = currentSection(cur);
    const hStart = horizonStart();
    const hEnd = horizonEnd();
    const elapsed = Math.max(0, daysBetween(hStart, TODAY));
    const totalDays = Math.max(1, daysBetween(hStart, hEnd));
    const remaining = Math.max(0, daysBetween(TODAY, hEnd));
    const momentum = momentumThisWeek();
    const est = estimatedCompletion(overall);
    const series = weeklyCompletionSeries(8);
    const maxBar = Math.max(1, ...series.map((s) => s.count));
    const phases = allPhases();

    const stripMonthsData = phases.map((p) => {
      const st = phaseStats(p.id);
      return {
        label: phaseStartDate(p.number).toLocaleDateString(undefined, { month: "short" }),
        title: `Month ${p.number}: ${p.title} (${st.completed} of ${st.total} tasks complete). Click to open in the Timeline.`,
        total: st.total, completed: st.completed, inProgress: st.inProgress, blocked: st.blocked,
        current: !!cur && cur.id === p.id,
      };
    });

    const statusSegments = [["completed", overall.completed], ["in_progress", overall.inProgress], ["blocked", overall.blocked], ["not_started", overall.notStarted]];
    const statusSummary = `${overall.completed} completed, ${overall.inProgress} in progress, ${overall.blocked} blocked, ${overall.notStarted} not started`;

    const monthRows = phases.map((p) => {
      const st = phaseStats(p.id);
      const isCurrent = cur && cur.id === p.id;
      return `<li class="month-row${isCurrent ? " is-current" : ""}">
        <div class="month-row-head">
          <button type="button" class="month-link" data-action="goto-month" data-id="${esc(p.id)}">M${p.number} — ${esc(p.title)}</button>
          ${isCurrent ? '<span class="badge badge-here">Current</span>' : ""}
          ${st.pct === 100 ? `<span class="badge badge-success">${icon("check", 12)} Done</span>` : ""}
          <span class="month-dates">${fmtDateShort(phaseStartDate(p.number))}–${fmtDateShort(phaseEndDate(p.number))}</span>
        </div>
        ${progressBar(st.pct)}
        <div class="month-count">${st.completed} of ${st.total} tasks</div>
      </li>`;
    }).join("");

    container.innerHTML = `
      ${viewHead("Overview")}
      <section class="overview-band" aria-label="Roadmap progress">
        <div class="band-main">
          <p class="band-pct"><span class="band-pct-num">${overall.pct}%</span> complete</p>
          <p class="band-sub">${overall.completed} of ${overall.total} tasks done</p>
        </div>
        <div class="band-strip">${window.MonthStrip.html(stripMonthsData, { size: "lg", labels: true })}</div>
        <div class="band-metrics">
          <div class="stat-tile">
            <div class="stat-label">Current month</div>
            <div class="stat-value">${cur ? "M" + cur.number : "—"}</div>
            <div class="stat-sub">${cur ? esc(cur.title) : "Outside planned horizon"}</div>
          </div>
          <div class="stat-tile">
            <div class="stat-label">Timeline</div>
            <div class="stat-value">${elapsed}d <span class="stat-unit">/ ${totalDays}d</span></div>
            <div class="stat-sub">${remaining} days remaining</div>
          </div>
          <div class="stat-tile">
            <div class="stat-label">Momentum</div>
            <div class="stat-value">${momentum}</div>
            <div class="stat-sub">tasks completed in the last 7 days</div>
          </div>
        </div>
      </section>

      <div class="overview-grid">
        <section class="card" aria-labelledby="ovMonths">
          <h3 class="card-title" id="ovMonths">Progress by month</h3>
          <ul class="month-list">${monthRows}</ul>
        </section>

        <div class="overview-side">
          <section class="card" aria-labelledby="ovStatus">
            <h3 class="card-title" id="ovStatus">Status</h3>
            <div class="status-bar" role="img" aria-label="${esc(statusSummary)}">
              ${statusSegments.filter(([, n]) => n > 0).map(([key, n]) => `<span class="sb sb-${key}" style="flex-grow:${n}"></span>`).join("")}
            </div>
            <ul class="status-legend">
              ${statusSegments.map(([key, n]) => `<li>${statusChip(key)}<strong>${n}</strong></li>`).join("")}
            </ul>
          </section>

          <section class="card" aria-labelledby="ovPace">
            <h3 class="card-title" id="ovPace">Pace</h3>
            ${est ? `
              <p class="pace-lead">At your current pace, you'll finish around</p>
              <p class="pace-date">${fmtDate(est.projected)}</p>
              <p class="pace-note">Planned target: ${fmtDate(hEnd)} · ~${est.rate.toFixed(2)} tasks/day</p>
            ` : `<p class="pace-note">Complete a few tasks to unlock a pace estimate.</p>`}
            <h4 class="card-subtitle">This week</h4>
            ${curSection ? `<p class="pace-lead">Focus: <strong>${esc(curSection.title)}</strong></p>` : `<p class="pace-note">No active week in range.</p>`}
            <h4 class="card-subtitle">Tasks completed per week</h4>
            <div class="bar-chart">
              ${series.map((s) => `<div class="bar-col"><div class="bar" style="height:${Math.round((s.count / maxBar) * 70) || 2}px" title="${s.count} completed"></div><div class="bar-label">${s.label}</div></div>`).join("")}
            </div>
          </section>
        </div>
      </div>

      ${DATA.counters.length ? `
        <section class="card counters-card" aria-labelledby="ovCounters">
          <h3 class="card-title" id="ovCounters">Interview & career counters</h3>
          <ul class="counter-list">
            ${DATA.counters.map((c) => {
              const val = getCounter(c.id, c.current);
              const pct = c.target ? Math.min(100, Math.round((val / c.target) * 100)) : 0;
              return `<li class="counter-row">
                <span class="counter-label">${esc(c.label)}</span>
                <span class="counter-value">${val}<span class="stat-unit"> / ${c.target}</span></span>
                <span class="counter-bar">${progressBar(pct)}</span>
                <span class="counter-steps">
                  <button type="button" class="mini-btn" data-action="counter-dec" data-id="${c.id}" aria-label="Decrease ${esc(c.label)}">${icon("minus", 14)}</button>
                  <button type="button" class="mini-btn" data-action="counter-inc" data-id="${c.id}" aria-label="Increase ${esc(c.label)}">${icon("plus", 14)}</button>
                </span>
              </li>`;
            }).join("")}
          </ul>
        </section>` : ""}
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Timeline
  // ---------------------------------------------------------
  const timelineState = { seeded: false }; // the current month opens by itself, once per roadmap

  function renderTimeline(container) {
    const cur = currentPhase();
    if (!timelineState.seeded) {
      if (cur) expandedPhases[cur.id] = true;
      timelineState.seeded = true;
    }
    container.innerHTML = `
      ${viewHead("Timeline")}
      <div class="timeline">
        ${allPhases().map((p) => {
          const st = phaseStats(p.id);
          const isCurrent = cur && cur.id === p.id;
          const isDone = st.pct === 100;
          const open = !!expandedPhases[p.id];
          return `<div class="timeline-item ${isCurrent ? "is-current" : ""} ${isDone ? "is-done" : ""}">
            <div class="timeline-dot" aria-hidden="true">${isDone ? icon("check", 11) : ""}</div>
            <article class="phase-card ${isCurrent ? "is-current" : ""} ${open ? "is-open" : ""}" data-phase-id="${esc(p.id)}">
              <header class="phase-card-head">
                <div class="phase-head-text">
                  <div class="phase-num">Month ${p.number} · ${esc(phaseCalendarLabel(p.number))}</div>
                  <h3 class="phase-title">${esc(p.title)} ${isCurrent ? '<span class="badge badge-here">Current</span>' : ""}${p.custom ? ' <span class="badge badge-custom">Custom</span>' : ""}</h3>
                  <div class="phase-dates">${fmtDate(phaseStartDate(p.number))} – ${fmtDate(phaseEndDate(p.number))}${p.custom ? ` <button type="button" class="mini-btn mini-btn-danger" data-action="delete-month" data-id="${esc(p.id)}" title="Delete this month and everything in it">${icon("trash", 14)}<span>Delete month</span></button>` : ""}</div>
                </div>
                <div class="phase-head-side">
                  <span class="phase-count">${st.completed}/${st.total} tasks</span>
                  <button type="button" class="phase-expand-btn" data-action="toggle-phase" data-id="${esc(p.id)}" aria-expanded="${open}" aria-controls="phase-body-${esc(p.id)}">
                    <span class="caret">${icon("chevron-right", 14)}</span><span>${open ? "Collapse" : "Expand"}</span>
                  </button>
                </div>
              </header>
              ${progressBar(st.pct)}
              ${p.objective ? `<p class="phase-objective">${esc(p.objective)}</p>` : ""}
              ${open ? `<div class="phase-body" id="phase-body-${esc(p.id)}">${renderPhaseBody(p)}</div>` : ""}
            </article>
          </div>`;
        }).join("")}
      </div>
      ${allPhases().length === 0 ? `<p class="empty-hint timeline-empty">No months yet — add your first one below.</p>` : ""}
      <button type="button" class="add-topic-btn add-month-btn" data-action="add-month">${icon("plus", 14)} Add month (Month ${allPhases().length + 1} · ${esc(phaseCalendarLabel(allPhases().length + 1))})</button>
    `;
  }

  const expandedPhases = {};

  function renderPhaseBody(phase) {
    const exitCriteria = phase.exitCriteria && phase.exitCriteria.length
      ? `<div class="group-label group-label-spaced">Exit criteria</div>
         <ul class="exit-list">
           ${phase.exitCriteria.map((c) => `<li>${esc(c)}</li>`).join("")}
         </ul>` : "";

    const sections = phase.sections.map((s) => {
      const st = sectionStats(s.id);
      const open = sectionOpenState[s.id] !== false; // default open
      const { start: wStart, end: wEnd } = sectionDates(phase.number, s);
      return `<div class="week-block">
        <div class="week-head">
          <h4 class="week-heading"><button type="button" class="week-toggle${open ? " open" : ""}" data-action="toggle-section" data-id="${esc(s.id)}" aria-expanded="${open}">
            <span class="caret">${icon("chevron-right", 14)}</span><span>${esc(s.title)}</span>
          </button></h4>
          <div class="week-meta">${wStart ? fmtDateShort(wStart) + "–" + fmtDateShort(wEnd) + " · " : ""}${st.completed}/${st.total}${s.custom ? ` <button type="button" class="mini-btn mini-btn-danger" data-action="delete-section" data-id="${esc(s.id)}" aria-label="Delete section: ${esc(s.title)}" title="Delete this section and its topics">${icon("trash", 14)}</button>` : ""}</div>
        </div>
        ${open ? renderTopics(topicsOf(s)) + `<button type="button" class="add-topic-btn" data-action="add-topic" data-section-id="${esc(s.id)}">${icon("plus", 14)} Add topic to this ${s.type === "week" ? "week" : "section"}</button>` : ""}
      </div>`;
    }).join("");

    const notes = (phase.notes || []).map((n) => `
      <div class="note-block">
        <strong>${esc(n.title)}</strong>
        <div class="note-text">${n.blocks.map((b) => esc(b)).join("\n\n")}</div>
      </div>`).join("");

    const deliverables = phase.deliverables && phase.deliverables.length ? `
      <div class="week-block">
        <div class="week-head"><h4 class="week-heading week-heading-static">Month ${phase.number} Deliverables</h4></div>
        <div class="topic-block">
          ${phase.deliverables.map((d) => subtaskRow(indexEntry(d.id))).join("")}
        </div>
      </div>` : "";

    const addSection = phase.custom
      ? (phase.sections.length ? "" : `<p class="empty-hint">This month has no sections yet. Add one, then add topics and tasks inside it.</p>`) +
        `<button type="button" class="add-topic-btn" data-action="add-section" data-phase-id="${esc(phase.id)}">${icon("plus", 14)} Add section to this month</button>`
      : "";

    return exitCriteria + sections + addSection + deliverables + (notes ? `<div class="group-label group-label-spaced">Context & notes</div>${notes}` : "");
  }

  const sectionOpenState = {};

  function renderTopics(topics) {
    return topics.map((t) => {
      const st = topicStats(t.id);
      return `<div class="topic-block">
        <div class="topic-head">
          <span class="topic-title">${esc(t.title)}</span>
          ${depthBadge(t.depth)}
          ${t.custom ? `<span class="badge badge-custom">Custom</span>
            <button type="button" class="mini-btn" data-action="add-task" data-topic-id="${esc(t.id)}">${icon("plus", 14)}<span>Task</span></button>
            <button type="button" class="mini-btn mini-btn-danger" data-action="delete-topic" data-topic-id="${esc(t.id)}" aria-label="Delete topic: ${esc(t.title)}" title="Delete this topic and its tasks">${icon("trash", 14)}</button>` : ""}
          <span class="topic-progress">${st.completed}/${st.total}</span>
        </div>
        ${t.groups.map((g) => `
          ${g.label ? `<div class="group-label">${esc(g.label)}</div>` : ""}
          ${g.subtasks.map((s) => subtaskRow(indexEntry(s.id))).join("")}
        `).join("")}
      </div>`;
    }).join("");
  }

  function indexEntry(id) {
    return INDEX.find((e) => e.id === id) || { id, title: id, phaseNumber: "", sectionTitle: "", topicTitle: "" };
  }

  // ---------------------------------------------------------
  // VIEW: Checklist
  // ---------------------------------------------------------
  const checklistFilters = { status: "all", phase: "all" };

  function renderChecklist(container) {
    const q = state.search.trim().toLowerCase();
    // Counts on the chips ignore the status filter itself, but respect search and month.
    const base = INDEX.filter((e) => matchesSearch(e, q) && (checklistFilters.phase === "all" || e.phaseId === checklistFilters.phase));
    const counts = { all: base.length };
    STATUS.forEach((s) => { counts[s] = base.filter((e) => getItem(e.id).status === s).length; });
    const entries = checklistFilters.status === "all" ? base : base.filter((e) => getItem(e.id).status === checklistFilters.status);

    // group by phase > section > topic
    const byPhase = {};
    entries.forEach((e) => {
      byPhase[e.phaseId] = byPhase[e.phaseId] || { title: e.phaseTitle, number: e.phaseNumber, sections: {} };
      const sec = byPhase[e.phaseId].sections;
      sec[e.sectionId || "deliverables"] = sec[e.sectionId || "deliverables"] || { title: e.sectionTitle, topics: {} };
      const top = sec[e.sectionId || "deliverables"].topics;
      const tKey = e.topicId || "deliverables";
      top[tKey] = top[tKey] || { title: e.topicTitle, depth: e.topicDepth, custom: e.custom, items: [] };
      top[tKey].items.push(e);
    });

    const phaseIds = Object.keys(byPhase).sort((a, b) => byPhase[a].number - byPhase[b].number);

    container.innerHTML = `
      ${viewHead("Checklist")}
      <div class="filter-bar is-sticky">
        ${["all", ...STATUS].map((s) => `<button type="button" class="chip-filter ${checklistFilters.status === s ? "active" : ""}" data-action="filter-status" data-value="${s}" aria-pressed="${checklistFilters.status === s}">${s === "all" ? "All" : STATUS_LABEL[s]} <span class="chip-count">${counts[s]}</span></button>`).join("")}
        <select class="select-filter" data-action="filter-phase" aria-label="Filter by month">
          <option value="all">All months</option>
          ${allPhases().map((p) => `<option value="${p.id}" ${checklistFilters.phase === p.id ? "selected" : ""}>Month ${p.number} — ${esc(p.title)}</option>`).join("")}
        </select>
        <span class="filter-count" role="status">${entries.length} task${entries.length === 1 ? "" : "s"}</span>
      </div>
      <div id="checklistBody">
        ${phaseIds.length === 0 ? emptyState(INDEX.length
          ? "No tasks match your filters."
          : "This roadmap has no tasks yet. Add months, topics and tasks from the Timeline.") : phaseIds.map((pid) => {
          const phase = byPhase[pid];
          return `<section class="phase-section-group">
            <h3 class="psg-head">Month ${phase.number} — ${esc(phase.title)}</h3>
            ${Object.keys(phase.sections).map((sid) => {
              const section = phase.sections[sid];
              return `<div class="cl-section">
                <h4 class="cl-section-title">${esc(section.title)}</h4>
                ${Object.keys(section.topics).map((tid) => {
                  const topic = section.topics[tid];
                  return `<div class="topic-block">
                    <div class="topic-head">
                      <span class="topic-title">${esc(topic.title)}</span>
                      ${depthBadge(topic.depth)}
                      ${topic.custom ? '<span class="badge badge-custom">Custom</span>' : ""}
                    </div>
                    ${topic.items.map((e) => subtaskRow(e)).join("")}
                  </div>`;
                }).join("")}
              </div>`;
            }).join("")}
          </section>`;
        }).join("")}
      </div>
    `;
  }

  // ---------------------------------------------------------
  // VIEW: This Week
  // ---------------------------------------------------------
  function renderThisWeek(container) {
    const weekAhead = new Date(TODAY.getTime() + 7 * 86400000);
    const active = INDEX.filter((e) => {
      const item = getItem(e.id);
      if (item.status === "completed") return false;
      const { start: secStart, end: secEnd } = entryDates(e);
      const inActiveSection = secStart && secEnd && TODAY >= secStart && TODAY <= secEnd;
      const due = parseDate(item.dueDate);
      const dueSoon = due && due <= weekAhead;
      return inActiveSection || dueSoon;
    });
    const overdue = active.filter((e) => {
      const d = parseDate(getItem(e.id).dueDate);
      return d && d < TODAY;
    });
    const rest = active.filter((e) => overdue.indexOf(e) === -1);

    const cur = currentPhase();
    const curSec = currentSection(cur);

    container.innerHTML = `
      <div class="view-narrow">
        ${viewHead("This week")}
        <section class="card focus-card" aria-label="Current focus">
          ${cur
            ? `<p class="focus-line">Month ${cur.number} — <strong>${esc(cur.title)}</strong>${curSec ? " · " + esc(curSec.title) : ""}</p>`
            : `<p class="focus-line focus-line-muted">Today isn't inside a planned month — showing anything with a near-term due date.</p>`}
        </section>
        ${overdue.length ? `<h3 class="list-heading list-heading-danger">Overdue (${overdue.length})</h3>${overdue.map((e) => subtaskRow(e, { showCrumbs: true })).join("")}` : ""}
        <h3 class="list-heading">Active now (${rest.length})</h3>
        ${rest.length ? rest.map((e) => subtaskRow(e, { showCrumbs: true })).join("") : emptyState("Nothing active right now — check the Checklist view or get ahead on next week.")}
      </div>
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Kanban
  // ---------------------------------------------------------
  const kanbanState = { phase: null };

  function renderKanban(container) {
    if (allPhases().length === 0) {
      container.innerHTML = viewHead("Kanban") +
        emptyState("Add a month with some tasks from the Timeline to use the board.");
      return;
    }
    if (!allPhases().some((p) => p.id === kanbanState.phase)) {
      const cur = currentPhase();
      kanbanState.phase = cur ? cur.id : allPhases()[0].id;
    }
    const q = state.search.trim().toLowerCase();
    const entries = INDEX.filter((e) => e.phaseId === kanbanState.phase && matchesSearch(e, q));
    const cols = { not_started: [], in_progress: [], blocked: [], completed: [] };
    entries.forEach((e) => cols[getItem(e.id).status].push(e));

    container.innerHTML = `
      ${viewHead("Kanban")}
      <div class="kanban-toolbar">
        <select class="select-filter" data-action="kanban-phase" aria-label="Month">
          ${allPhases().map((p) => `<option value="${p.id}" ${kanbanState.phase === p.id ? "selected" : ""}>Month ${p.number} — ${esc(p.title)}</option>`).join("")}
        </select>
        <span class="kanban-hint">Drag cards between columns, or change a card's status with its dropdown.</span>
      </div>
      <div class="kanban-board">
        ${["not_started", "in_progress", "blocked", "completed"].map((key) => `
          <section class="kanban-col" data-action="kanban-dropzone" data-status="${key}" aria-label="${STATUS_LABEL[key]}">
            <div class="kanban-col-head"><span>${STATUS_LABEL[key]}</span><span class="kanban-count">${cols[key].length}</span></div>
            ${cols[key].map((e) => `
              <div class="kanban-card" draggable="true" data-id="${e.id}" data-action="kanban-card">
                <div class="k-title">${esc(e.title)}</div>
                <div class="k-path">${esc(e.sectionTitle)}${e.topicTitle && e.topicTitle !== "Deliverables" ? " · " + esc(e.topicTitle) : ""}${e.custom ? " · Custom" : ""}</div>
                <div class="k-actions">
                  ${statusSelect(e.id, key)}
                  <button type="button" class="mini-btn" data-action="open-edit" data-id="${e.id}" aria-label="Details: ${esc(e.title)}">${icon("pencil", 14)}</button>
                </div>
              </div>
            `).join("")}
          </section>
        `).join("")}
      </div>
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Mastery checklist
  // ---------------------------------------------------------
  function renderMastery(container) {
    const q = state.search.trim().toLowerCase();
    container.innerHTML = `
      ${viewHead("Skills checklist", "A flat, non-date-bound reference checklist of the roadmap's full skill list (source: “AI Engineering Mastery Checklist”). Track these independently of the month-by-month timeline.")}
      <div class="mastery-grid">
        ${DATA.masteryChecklist.map((cat) => {
          const skills = cat.skills.filter((sk) => !q || sk.title.toLowerCase().includes(q));
          if (!skills.length) return "";
          const done = cat.skills.filter((sk) => getItem(sk.id).status === "completed").length;
          const pct = cat.skills.length ? Math.round((done / cat.skills.length) * 100) : 0;
          return `<section class="mastery-cat">
            <h3>${esc(cat.title)} <span class="mastery-count">${done}/${cat.skills.length}</span></h3>
            ${progressBar(pct)}
            ${skills.map((sk) => `
              <div class="mastery-skill-row">
                <input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${sk.id}" aria-label="${esc(sk.title)}" ${getItem(sk.id).status === "completed" ? "checked" : ""} />
                <span class="skill-title ${getItem(sk.id).status === "completed" ? "done" : ""}">${esc(sk.title)}</span>
                ${depthBadge(sk.depth)}
              </div>
            `).join("")}
          </section>`;
        }).join("")}
      </div>
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Reference
  // ---------------------------------------------------------
  function renderBlockAsHtml(block) {
    const lines = block.split("\n");
    const isTableBlock = lines.filter((l) => l.trim().startsWith("|")).length >= 2;
    if (isTableBlock) {
      const rows = lines.filter((l) => l.trim().startsWith("|")).map((l) =>
        l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim())
      );
      const header = rows[0];
      const body = rows.slice(1).filter((r) => !r.every((c) => /^:?-+:?$/.test(c)));
      return `<table><thead><tr>${header.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
        <tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }
    return esc(block).replace(/^#{1,4}\s*(.+)$/gm, "<strong>$1</strong>").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function jumpToReference(id) {
    const card = document.getElementById(id);
    if (card) card.scrollIntoView({ block: "start" });
  }

  function renderReference(container) {
    const q = state.search.trim().toLowerCase();
    const docs = DATA.reference.map((r, i) => {
      const hay = (r.title + " " + r.blocks.join(" ")).toLowerCase();
      return { r, id: `ref-doc-${i}`, match: !q || hay.includes(q) };
    });
    container.innerHTML = `
      ${viewHead("Reference & strategy", "Background and strategic context from the roadmap that isn't itself a checklist item — preserved here so nothing is lost.")}
      <div class="ref-layout">
        <nav class="ref-nav" aria-label="Reference documents">
          <ul>
            ${docs.filter((d) => d.match).map((d) => `<li><button type="button" class="ref-nav-btn" data-action="ref-jump" data-id="${d.id}">${esc(d.r.title)}</button></li>`).join("")}
          </ul>
        </nav>
        <div class="ref-content">
          <label class="sr-only" for="refJump">Jump to document</label>
          <select id="refJump" class="select-filter ref-select" data-action="ref-jump-select">
            <option value="">Jump to a document…</option>
            ${docs.filter((d) => d.match).map((d) => `<option value="${d.id}">${esc(d.r.title)}</option>`).join("")}
          </select>
          ${docs.map((d) => `
            <article class="card ref-card ${d.match ? "" : "ref-search-hidden"}" id="${d.id}">
              <h3>${esc(d.r.title)}</h3>
              ${d.r.blocks.map((b) => `<div class="ref-block">${renderBlockAsHtml(b)}</div>`).join("")}
            </article>
          `).join("")}
        </div>
      </div>
    `;
  }

'''
swap_block("  function renderBlankRoadmap(container) {",
           "  // ---------------------------------------------------------\n  // Toasts & Confetti", NEW_VIEWS)

# 3. Clicks inside the views: use closest() so buttons that contain an SVG icon still work;
#    add the Overview month strip / month links and the Reference jump list
once("""  function onMainClick(e) {
    const t = e.target;
    const action = t.dataset.action;
    if (!action) return;
""", """  function onMainClick(e) {
    // Overview: clicking a segment of the month strip opens that month in the Timeline.
    const segment = e.target.closest(".band-strip .strip-col");
    if (segment) {
      const cols = [...segment.parentElement.children];
      const phase = allPhases()[cols.indexOf(segment)];
      if (phase && cols.length === allPhases().length) goToMonth(phase.id);
      return;
    }
    const t = e.target.closest("[data-action]");
    if (!t || !document.getElementById("main").contains(t)) return;
    const action = t.dataset.action;
""")
once("""      case "counter-dec":
        setCounter(t.dataset.id, getCounter(t.dataset.id, 0) - 1);
        rerender();
        break;
""", """      case "counter-dec":
        setCounter(t.dataset.id, getCounter(t.dataset.id, 0) - 1);
        rerender();
        break;
      case "goto-month":
        goToMonth(t.dataset.id);
        break;
      case "ref-jump":
        jumpToReference(t.dataset.id);
        break;
""")
once("""    if (action === "kanban-phase") {
      kanbanState.phase = t.value;
      rerender();
      return;
    }
  }""", """    if (action === "kanban-phase") {
      kanbanState.phase = t.value;
      rerender();
      return;
    }
    if (action === "ref-jump-select") {
      if (t.value) jumpToReference(t.value);
      t.value = "";
    }
  }""")
once("    kanbanState.phase = null;\n", "    kanbanState.phase = null;\n    timelineState.seeded = false;\n")

# 4. Dialog clicks: closest() as well
a = s.index("  function onModalClick(e) {")
b = s.index("\n  }\n", a) + len("\n  }\n")
s = s[:a] + r'''  function onModalClick(e) {
    const el = e.target.closest("[data-action]");
    if (!el) return;
    const action = el.dataset.action;
    if (action === "close-modal") closeModal();
    if (action === "save-modal") saveModal(el.dataset.id);
    if (action === "confirm-reset") doReset();
    if (action === "confirm-delete-roadmap") deleteRoadmap(Number(el.dataset.id));
    if (action === "save-start-month") saveStartMonth();
    if (action === "conflict-load") resolveConflictLoadServer();
    if (action === "conflict-overwrite") resolveConflictOverwrite();
    if (action === "legacy-import") importLegacyData();
    if (action === "save-month") saveMonth();
    if (action === "save-section") saveSection(el.dataset.phaseId);
    if (action === "save-topic") saveTopic(el.dataset.sectionId);
    if (action === "save-tasks") saveTasks(el.dataset.topicId);
  }
''' + s[b:]

# 5. Every dialog uses the shared showModal() (focus return, Escape, name). Dialogs opened from a
#    menu item return focus to that menu's button, because the item itself is hidden when the menu closes.
once("    modalReturnFocus = returnFocus || document.activeElement;",
     """    let opener = returnFocus || document.activeElement;
    const menu = opener && opener.closest ? opener.closest(".profile-panel") : null;
    if (menu) opener = menu.parentElement.querySelector(".profile-trigger");
    modalReturnFocus = opener;""")
a = s.index("  function showModal(")
b = s.index("  function closeModal(")
head, show, tail = s[:a], s[a:b], s[b:]
reveal = 'host.classList.remove("hidden");'
before = head.count(reveal) + tail.count(reveal)
head, tail = head.replace(reveal, "showModal();"), tail.replace(reveal, "showModal();")
s = head + show + tail
assert before == 9, f"expected to convert exactly 9 dialogs, found {before}"

# 6. Every dialog field label is tied to its control
s, n_labels = re.subn(r'<label>([^<]*)</label>(\s*)<(input|select|textarea)([^>]*?)\bid="([^"]+)"',
                      r'<label for="\5">\1</label>\2<\3\4id="\5"', s)

# 7. Inline styles -> classes (anything left must be a genuinely dynamic width/height)
SKELETONS = [
    ('<span class="skeleton" style="height:22px;width:60%"></span>', '<span class="skeleton sk-title"></span>'),
    ('<span class="skeleton" style="height:36px"></span>', '<span class="skeleton sk-text"></span>'),
    ('<span class="skeleton" style="height:8px"></span>', '<span class="skeleton sk-bar"></span>'),
    ('<span class="skeleton" style="height:36px;margin-top:auto"></span>', '<span class="skeleton sk-action"></span>'),
    ('<span class="skeleton" style="height:28px;width:220px;margin-bottom:20px"></span>', '<span class="skeleton sk-heading"></span>'),
    ('<span class="skeleton" style="height:320px;margin-top:20px"></span>', '<span class="skeleton sk-panel"></span>'),
    (r'''"<span class=\"skeleton\" style=\"height:92px\"></span>".repeat(4)''', r'''"<span class=\"skeleton sk-tile\"></span>".repeat(4)'''),
]
for old, new in SKELETONS:
    once(old, new)

DIALOG_STYLES = {
    "font-size:12px; color:var(--text-faint); margin-top:-10px;": "dialog-sub",
    "font-size:13px; color:var(--text-muted);": "dialog-text",
    "font-size:13px; color:var(--text-muted); line-height:1.5;": "dialog-text",
    "font-size:11.5px; color:var(--text-faint); margin-top:4px;": "field-hint",
    "font-size:13px; color:var(--text-faint);": "dialog-hint",
    "font-size:12px; color:var(--text-faint); margin-top:-6px;": "dialog-hint",
    "font-size:13px; color:var(--text-muted); line-height:1.5; padding-left:18px;": "dialog-list",
    "font-size:13px; color:var(--status-blocked); line-height:1.5;": "dialog-warn",
    "font-size:12px; color:var(--text-faint);": "dialog-hint",
    "margin-top:4px;": "modal-note",
}
for css, cls in DIALOG_STYLES.items():
    pattern = re.compile(r'<(\w+)((?:\s[^<>]*?)?)\sstyle="' + re.escape(css) + r'"([^<>]*)>')
    def fix(m, cls=cls):
        attrs = m.group(2) + m.group(3)
        if "class=" in attrs:
            attrs = re.sub(r'class="([^"]*)"', lambda c: 'class="' + c.group(1) + " " + cls + '"', attrs, count=1)
            return "<" + m.group(1) + attrs + ">"
        return "<" + m.group(1) + m.group(2) + ' class="' + cls + '"' + m.group(3) + ">"
    s = pattern.sub(fix, s)

# 8. Confetti in the brand palette
once('const colors = ["#4f46e5", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4"];',
     'const colors = ["#2b50d8", "#3dbe84", "#e0a33a", "#f0716a", "#6c8cff"];')

# 9. Month labels in sentence case ("October 2026"), not ALL CAPS
once("""    return phaseStartDate(phaseNumber)
      .toLocaleDateString(undefined, { month: "long", year: "numeric" })
      .toUpperCase();""", """    return phaseStartDate(phaseNumber)
      .toLocaleDateString(undefined, { month: "long", year: "numeric" });""")
once("""return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" }).toUpperCase();""",
     """return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });""")

# 10. Dialogs always take focus; the Tab trap also pulls stray focus back inside
once("""    else modal.removeAttribute("aria-labelledby");
    host.classList.remove("hidden");
  }""", """    else modal.removeAttribute("aria-labelledby");
    host.classList.remove("hidden");
    // Dialogs that do not focus a control themselves get focus on their first control.
    if (!modal.contains(document.activeElement)) {
      const first = [...modal.querySelectorAll("input:not([type=hidden]), select, textarea, button, a[href]")]
        .find((el) => !el.disabled && el.offsetParent !== null);
      if (first) first.focus();
    }
  }""")
once("""    const first = focusable[0];
    const last = focusable[focusable.length - 1];
""", """    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!document.querySelector("#modalHost .modal").contains(document.activeElement)) {
      e.preventDefault();
      (e.shiftKey ? last : first).focus();
      return;
    }
""")

open(P, "w", encoding="utf-8").write(s)

# Checks
DYNAMIC = [r'style="width:\$\{pct\}%"', r'style="height:\$\{Math\.round\(\(s\.count / maxBar\) \* 70\) \|\| 2\}px"', r'style="flex-grow:\$\{n\}"']
leftover = [m for m in re.findall(r'style=\\?"[^"]*\\?"', s) if not any(re.fullmatch(d, m) for d in DYNAMIC)]
assert not leftover, "non-dynamic inline styles remain: " + "; ".join(leftover)
for required in ("function goToMonth", "function viewHead", "function jumpToReference", "const timelineState"):
    assert s.count(required) == 1, f"{required}: expected exactly one definition, found {s.count(required)}"
assert s.count("function emptyState") == 1 and s.count("function subtaskRow") == 1 and s.count("function renderOverview") == 1
print(f"js/app.js updated ({n_labels} dialog labels linked to their controls)")
```

## Appendix B3 — `step4_docs.py` (Task 5)

Run from the repo root: `python3 step4_docs.py`.

```python
"""Phase 4 / documentation. Run from the repo root: python3 step4_docs.py"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match ({s.count(old)} found) for: {old[:80]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("README.md", [
    ("| **Overview** | Overall completion %, per-month progress bars, pace projection, weekly momentum chart, interview/career counters |",
     "| **Overview** | Headline completion % with a clickable Month Strip (opens that month in the Timeline), current month / timeline / momentum, a status bar with legend, per-month progress, pace projection and weekly chart, compact interview/career counters |"),
    ("| **Timeline** | Month → Week → Topic → Task drill-down; exit criteria, deliverables, read-only background notes |",
     "| **Timeline** | Month → Week → Topic → Task drill-down with sticky month headers; the current month opens by itself; exit criteria, deliverables, read-only background notes |"),
    ("| **Kanban** | Per-month drag-and-drop board across To Do / In Progress / Blocked / Done |",
     "| **Kanban** | Per-month board across Not started / In progress / Blocked / Completed: drag cards, or change a card's status with its dropdown (keyboard friendly); scrolls sideways on phones |"),
    ("| **Checklist** | Full flat task list with status/phase filters, search, and a per-task details modal (notes, link, due date) |",
     "| **Checklist** | Full flat task list with a sticky filter bar (status chips with counts, month), search, and a per-task details dialog (notes, link, due date) |"),
    ("| **Skills Checklist** | Flat mastery checklist trackable independently of the calendar (AI Engineer roadmap only — hidden on custom roadmaps) |",
     "| **Skills Checklist** | Flat mastery checklist, grouped with a progress bar per group, trackable independently of the calendar (AI Engineer roadmap only — hidden on custom roadmaps) |"),
    ("| **Reference** | All strategic/background roadmap content, searchable (AI Engineer roadmap only — hidden on custom roadmaps) |",
     "| **Reference** | All strategic/background roadmap content in a comfortable reading column with a sticky document list (a \"Jump to\" menu on small screens), searchable (AI Engineer roadmap only — hidden on custom roadmaps) |"),
    ("│   ├── home.css                  Home (roadmap list): summary bar, cards\n│   └── styles.css                Layout + per-view rules (shrinking during the redesign)",
     "│   ├── home.css                  Home (roadmap list): summary bar, cards\n│   ├── roadmap.css               The seven roadmap views, task rows, dialog text\n│   └── styles.css                Account-menu rules (the last legacy file; removed in Phase 5)"),
])

patch("documentation/design-system.md", [
    ("| `css/styles.css` | Layout and per-view rules not yet moved (shrinks each phase; see \"Redesign status\") |",
     "| `css/roadmap.css` | The seven roadmap views (Overview, Timeline, Checklist, This week, Kanban, Skills, Reference), task rows, the blank-roadmap guide, skeleton blocks and the small text styles used inside dialogs |\n"
     "| `css/styles.css` | Only the account-menu rules remain (removed in Phase 5) |"),
    ("→ `shell.css` → `home.css` → `styles.css`;", "→ `shell.css` → `home.css` → `roadmap.css` → `styles.css`;"),
    ("| 4 | Roadmap views | Not started |", "| 4 | Roadmap views | Done |"),
    ("## Motion and accessibility rules",
     """## Roadmap views (Phase 4)

- **Page structure:** every view starts with `viewHead(title, sub)` (an `h2.view-title`); the one `h1` of the screen is the visually hidden `#roadmapH1`. Text-heavy views (This week, blank roadmap) sit in `.view-narrow` (max 880px).
- **Icons, not glyphs:** buttons use `Icons.svg()` (`icon()` helper in the views). Because a click can land on the SVG, delegated handlers use `event.target.closest("[data-action]")` — never `event.target.dataset`.
- **Overview:** a header band (`.overview-band`) holds the headline %, the large Month Strip (segments open that month in the Timeline) and three metrics (`.stat-tile`); then a month list, a stacked status bar with legend, pace, and compact counter rows with +/− steppers.
- **Timeline:** month cards with a sticky header when open; sections are real buttons inside headings (`aria-expanded`); the current month opens once per roadmap.
- **Kanban:** four status columns, each with a coloured top edge and a count; every card has a status dropdown (the keyboard alternative to dragging). Below 1000px the board scrolls sideways inside itself with snap points.
- **Task rows** (`.subtask-row`): checkbox named by the task title, status select, due tag, link, Details button; the controls wrap under the title below 720px.
- **Dialogs:** all of them go through `showModal()`; every field label is tied to its control (`for`); text inside dialogs uses `.dialog-sub`, `.dialog-text`, `.dialog-hint`, `.dialog-list`, `.dialog-warn`. A dialog opened from a menu item returns focus to that menu's button.
- **No inline styles** except genuinely dynamic widths and heights (progress fills, chart bars, status-bar segments).

## Motion and accessibility rules"""),
])
print("docs updated")
```

## Appendix C1 — `verify_phase4.py` (verification harness; keep outside the repo)

Uses `serve-demo.js` from the Phase 0 spec (Appendix C1).

```python
"""Phase 4 verification. Usage:
    python3 verify_phase4.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Needs the demo server from the Phase 0 spec (serve-demo.js) running. Exit code 0 only if every check passes."""
import os
import re
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots-p4"
os.makedirs(SHOTS, exist_ok=True)
RUN = int(time.time()) % 1000000
results, AXE_SOURCE = [], None
LAST_BAD = []
VIEWS = ["overview", "timeline", "kanban", "checklist", "thisweek", "mastery", "reference"]
DYNAMIC_STYLE = re.compile(r"^(width|height|flex-grow|flex-basis):\s*[\d.]+(px|%)?;?$")


def check(ok, message):
    global LAST_BAD
    results.append(bool(ok))
    extra = "" if ok or not LAST_BAD else "  -> offending styles: " + "; ".join(LAST_BAD[:4])
    print(("PASS " if ok else "FAIL ") + message + extra)
    LAST_BAD = []


def audit(page, label):
    global AXE_SOURCE
    if AXE_SOURCE is None:
        AXE_SOURCE = open(AXE, encoding="utf-8").read()
    page.evaluate(AXE_SOURCE)  # DevTools evaluation works under the app's CSP; <script> injection does not
    v = page.evaluate("""async () => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] } });
      return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0] && v.nodes[0].target.join(' ')));
    }""")
    check(not v, f"axe 0 violations: {label}" + ("" if not v else "  -> " + "; ".join(v)))


def new_context(browser, width=1440, height=1000, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
    page = ctx.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: page.problems.append(m.text) if m.type == "error" and "401" not in m.text and "404" not in m.text else None)
    return ctx, page


def register(ctx, tag):
    r = ctx.request.post(BASE + "/api/auth/register", data={"firstName": "Vera", "lastName": "View", "username": f"p4{tag}_{RUN}", "password": "longenough1"})
    assert r.status == 201, r.status


def seed_progress(ctx, page):
    """Give the built-in roadmap real, varied progress through the API; returns the list stats."""
    page.goto(BASE); page.wait_for_load_state("load")   # signed in already, so this lands on Home
    ids = page.evaluate("""() => window.ROADMAP_DATA.phases.map(p => p.sections.flatMap(s => s.topics.flatMap(t => t.groups.flatMap(g => g.subtasks.map(x => x.id)))))""")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    items = {}
    for i, tid in enumerate(ids[0][:30]): items[tid] = {"status": "completed", "completedAt": now}
    for tid in ids[0][30:34]: items[tid] = {"status": "in_progress"}
    for tid in ids[0][34:37]: items[tid] = {"status": "blocked"}
    for tid in ids[1][:5]: items[tid] = {"status": "completed", "completedAt": now}
    for tid in ids[1][5:7]: items[tid] = {"status": "in_progress"}
    items[ids[1][7]] = {"status": "blocked"}
    rid = ctx.request.get(BASE + "/api/roadmaps").json()["roadmaps"][0]["id"]
    r = ctx.request.put(BASE + f"/api/roadmaps/{rid}/progress", data={"version": 0, "data": {"items": items, "counters": {}, "celebratedPhases": [], "settings": {}, "custom": {"topics": [], "phases": []}}})
    assert r.status == 200, r.status
    return ctx.request.get(BASE + "/api/roadmaps").json()["roadmaps"][0]["stats"]


def open_roadmap(page, view="overview", index=0):
    page.goto(BASE); page.wait_for_selector(".summary-bar", timeout=10000)
    page.locator("article.roadmap-card .btn-primary").nth(index).click()
    page.wait_for_selector(".tab.active", timeout=10000)
    go(page, view)


def go(page, view):
    if page.locator("#sidebarOpenBtn").is_visible():      # phones and tablets: the views are inside the drawer
        page.click("#sidebarOpenBtn"); page.wait_for_timeout(200)
    page.click(f'.tab[data-view="{view}"]'); page.wait_for_selector("#main > *", timeout=8000); page.wait_for_timeout(250)




def styles_ok(page):
    """True when every inline style in the view/dialog is a dynamic width/height (kept for charts and bars)."""
    global LAST_BAD
    LAST_BAD = [x for x in bad_styles(page) if not DYNAMIC_STYLE.match(x)]
    return not LAST_BAD


def bad_styles(page):
    # (an empty style="" left behind by the browser is not an inline style)
    return page.evaluate("""() => [...document.querySelectorAll('#main [style], #modalHost [style]')].map(e => (e.getAttribute('style') || '').trim()).filter(Boolean)""")


def pictographs(page):
    return page.evaluate(r"""() => { const t = document.getElementById('main').innerText + ' ' + document.getElementById('modalHost').innerText;
      return (t.match(/\p{Extended_Pictographic}|[✎✓✕▸＋●🔗🗑]/gu) || []).join(''); }""")


def month_expectation(page):
    return page.evaluate("(() => { const n = new Date(); return (n.getFullYear() - 2026) * 12 + (n.getMonth() - 9); })()")


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ======================= Data setup =======================
    ctx, page = new_context(browser)
    register(ctx, "a")
    stats = seed_progress(ctx, page)
    total, done, inprog, blocked = stats["total"], stats["completed"], stats["inProgress"], stats["blocked"]
    notstarted = total - done - inprog - blocked
    check(done == 35 and inprog == 6 and blocked == 4 and total == 849, f"seeded progress: {done} done, {inprog} in progress, {blocked} blocked of {total}")

    # ======================= A. Overview =======================
    open_roadmap(page, "overview")
    check(page.inner_text("h2.view-title") == "Overview", "Overview: heading")
    pct = round(done / total * 100)
    check(f"{pct}%" in page.inner_text(".band-pct") and f"{done} of {total} tasks done" in page.inner_text(".band-sub"), f"Overview: headline {pct}% and '{done} of {total} tasks done'")
    cols = page.locator(".band-strip .strip-col")
    check(cols.count() == 10 and [t.strip() for t in page.locator(".band-strip .strip-label").all_inner_texts()] == ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"], "Overview: 10-month strip with labels Oct..Jul")
    idx = month_expectation(page)
    check(page.locator(".band-strip .strip-col.is-current").count() == (1 if 0 <= idx < 10 else 0), "Overview: current month marked exactly when today is inside the roadmap")
    check(page.locator(".band-metrics .stat-tile").count() == 3, "Overview: three metrics in the header band")
    label = page.get_attribute(".status-bar", "aria-label")
    check(label == f"{done} completed, {inprog} in progress, {blocked} blocked, {notstarted} not started", "Overview: status bar summary matches the data: " + label)
    check(page.locator(".status-legend li").count() == 4 and page.locator(".status-legend strong").all_inner_texts() == [str(done), str(inprog), str(blocked), str(notstarted)], "Overview: legend counts")
    check(page.locator(".month-row").count() == 10 and f"{stats['months'][0]['completed']} of {stats['months'][0]['total']} tasks" in page.inner_text(".month-row >> nth=0"), "Overview: 10 month rows with per-month counts")
    check(page.locator(".counter-row").count() == 8, "Overview: 8 counters as compact rows")
    page.screenshot(path=f"{SHOTS}/overview-light.png", full_page=True)
    check(styles_ok(page), "Overview: only dynamic width/height inline styles remain")
    check(pictographs(page) == "", "Overview: no emoji or glyph icons in the text")
    audit(page, "Overview (light)")
    # counters: click on the svg inside the button must work
    first_value = lambda: page.inner_text(".counter-row >> nth=0 >> .counter-value").split("/")[0].strip()
    page.locator('.counter-row >> nth=0 >> [data-action="counter-inc"] svg').click()
    check(first_value() == "1", "Overview: clicking the icon inside '+' increments the counter")
    check(page.get_attribute('.counter-row >> nth=0 >> [data-action="counter-inc"]', "aria-label") == "Increase DSA Problems Solved", "Overview: counter buttons have descriptive names")
    page.click('.counter-row >> nth=0 >> [data-action="counter-dec"]'); check(first_value() == "0", "Overview: '−' decrements")
    # month link and strip segment open the Timeline on that month
    page.click('.month-link >> nth=2')
    page.wait_for_selector(".phase-card.is-open")
    third = page.locator(".phase-card").nth(2)
    check(page.evaluate("location.hash").endswith("/timeline") and third.get_attribute("class").find("is-open") >= 0, "Overview: a month link opens that month in the Timeline")
    go(page, "overview"); page.locator(".band-strip .strip-col").nth(4).click(); page.wait_for_selector(".phase-card.is-open")
    check(page.evaluate("location.hash").endswith("/timeline") and page.locator(".phase-card").nth(4).get_attribute("class").find("is-open") >= 0, "Overview: clicking a strip segment opens that month in the Timeline")

    # ======================= B. Timeline =======================
    go(page, "timeline")
    check(page.inner_text("h2.view-title") == "Timeline" and page.locator("h3.phase-title").count() == 10, "Timeline: heading and 10 month cards (h3)")
    open_cards = page.locator(".phase-card.is-open").count()
    check(open_cards >= 1, f"Timeline: expanded month(s) stay open ({open_cards})")
    page.reload(); page.wait_for_selector(".phase-card")
    expected_open = 1 if 0 <= idx < 10 else 0
    check(page.locator(".phase-card.is-open").count() == expected_open, f"Timeline: on a fresh visit only the current month is open ({expected_open})")
    check("OCTOBER" not in page.inner_text(".phase-num >> nth=0") and "October" in page.inner_text(".phase-num >> nth=0"), "Timeline: month label is sentence case: " + page.inner_text(".phase-num >> nth=0"))
    btn = page.locator('[data-action="toggle-phase"]').first
    before = btn.get_attribute("aria-expanded"); btn.click()
    check(page.locator('[data-action="toggle-phase"]').first.get_attribute("aria-expanded") != before, "Timeline: Expand/Collapse toggles aria-expanded")
    page.locator('[data-action="toggle-phase"]').first.click()
    if expected_open:
        head = page.locator(".phase-card.is-open > .phase-card-head").first
        check(head.evaluate("e => getComputedStyle(e).position") == "sticky", "Timeline: an open month's header is sticky on desktop")
        wk = page.locator(".phase-card.is-open .week-toggle").first
        wk.focus(); page.keyboard.press("Enter")
        check(page.locator(".phase-card.is-open .week-toggle").first.get_attribute("aria-expanded") == "false", "Timeline: sections toggle with the keyboard (real buttons)")
        page.locator(".phase-card.is-open .week-toggle").first.click()
        check(page.locator(".phase-card.is-open h4.week-heading > button").count() >= 1, "Timeline: section titles are headings that contain a button")
        row = page.locator(".phase-card.is-open .subtask-row").first
        check(row.locator('input[type="checkbox"]').get_attribute("aria-label") == row.locator(".subtask-title").inner_text().strip(), "Timeline: each task checkbox is named by its title")
        check(row.bounding_box()["height"] >= 38, f"Timeline: task rows are at least 40px high ({row.bounding_box()['height']:.0f}px)")
    check(pictographs(page) == "", "Timeline: no emoji or glyph icons")
    check(styles_ok(page), "Timeline: only dynamic inline styles")
    page.screenshot(path=f"{SHOTS}/timeline-light.png")
    audit(page, "Timeline (light)")

    # ======================= C. Checklist =======================
    go(page, "checklist")
    chip = lambda v: " ".join(page.locator(f'.chip-filter[data-value="{v}"]').inner_text().split())
    check(chip("all") == f"All {total}" and chip("completed") == f"Completed {done}" and chip("blocked") == f"Blocked {blocked}"
          and chip("in_progress") == f"In progress {inprog}" and chip("not_started") == f"Not started {notstarted}", "Checklist: chips show counts: " + " | ".join(chip(v) for v in ("all", "not_started", "in_progress", "blocked", "completed")))
    page.click('.chip-filter[data-value="blocked"]')
    check(page.inner_text(".filter-count") == f"{blocked} tasks" and page.get_attribute('.chip-filter[data-value="blocked"]', "aria-pressed") == "true", "Checklist: Blocked filter shows exactly the blocked tasks")
    vals = page.evaluate("[...document.querySelectorAll('.status-select')].map(s => s.value)")
    check(vals and set(vals) == {"blocked"}, "Checklist: every visible task is blocked")
    page.click('.chip-filter[data-value="all"]')
    check(page.locator(".filter-bar.is-sticky").evaluate("e => getComputedStyle(e).position") == "sticky", "Checklist: filter bar is sticky on desktop")
    page.evaluate("window.scrollTo(0, 900)"); page.wait_for_timeout(200)
    top = page.locator(".filter-bar.is-sticky").bounding_box()["y"]
    check(50 <= top <= 70, f"Checklist: the filter bar stays pinned under the top bar while scrolling ({top:.0f}px)")
    page.evaluate("window.scrollTo(0, 0)")
    page.select_option('[data-action="filter-phase"]', index=1)
    check(page.inner_text(".filter-count").startswith(str(stats["months"][0]["total"])), "Checklist: month filter narrows the list to that month")
    page.select_option('[data-action="filter-phase"]', index=0)
    page.fill("#roadmapSearch", "scalab"); page.wait_for_timeout(300)
    n = int(page.inner_text(".filter-count").split()[0])
    check(0 < n < total, f"Checklist: top-bar search filters the list ({n} tasks)")
    page.fill("#roadmapSearch", ""); page.wait_for_timeout(200)
    check(page.locator(".subtask-row").first.locator(".mini-btn", has_text="Details").count() == 1, "Checklist: each row has a Details button with an icon and text")
    check(pictographs(page) == "", "Checklist: no emoji or glyph icons")
    page.screenshot(path=f"{SHOTS}/checklist-light.png")
    audit(page, "Checklist (light)")
    # details dialog: name, labels, Escape, focus return
    details = page.locator(".subtask-row").first.locator(".mini-btn", has_text="Details")
    details.focus(); details.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    modal = page.locator("#modalHost .modal")
    check(modal.get_attribute("role") == "dialog" and modal.get_attribute("aria-labelledby") == "modalTitle", "Details dialog: role and accessible name")
    check(page.locator("label[for=modalStatus]").count() == 1 and page.locator("label[for=modalDue]").count() == 1 and page.locator("label[for=modalNotes]").count() == 1, "Details dialog: every field label is tied to its control")
    check(styles_ok(page), "Details dialog: no inline styles")
    audit(page, "Details dialog")
    page.keyboard.press("Escape")
    check(page.locator("#modalHost.hidden").count() == 1 and page.evaluate("document.activeElement.getAttribute('data-action')") == "open-edit", "Details dialog: Escape closes it and focus returns to the Details button")

    # ======================= D. This week =======================
    go(page, "thisweek")
    check(page.inner_text("h2.view-title") == "This week" and page.locator(".view-narrow").bounding_box()["width"] <= 881, "This week: heading and a reading width of 880px or less")
    check(page.locator(".focus-card").count() == 1 and page.locator(".list-heading", has_text="Active now").count() == 1, "This week: current focus card and 'Active now' list")
    check(pictographs(page) == "", "This week: no emoji or glyph icons")
    audit(page, "This week (light)")

    # ======================= E. Kanban =======================
    go(page, "kanban")
    check([t.strip() for t in page.locator(".kanban-col-head > span:first-child").all_inner_texts()] == ["Not started", "In progress", "Blocked", "Completed"], "Kanban: four columns in order")
    cnt = lambda s: int(page.inner_text(f'.kanban-col[data-status="{s}"] .kanban-count'))
    counts = {s: cnt(s) for s in ("not_started", "in_progress", "blocked", "completed")}
    month_total = stats["months"][idx if 0 <= idx < 10 else 0]["total"]
    check(sum(counts.values()) == month_total, f"Kanban: column counts add up to the month's {month_total} tasks: {counts}")
    colors = page.evaluate("[...document.querySelectorAll('.kanban-col')].map(c => getComputedStyle(c).borderTopColor)")
    check(len(set(colors)) == 4, "Kanban: each column has its own top-border colour")
    card = page.locator('.kanban-col[data-status="not_started"] .kanban-card').first
    card.locator("select").select_option("blocked")
    check(cnt("blocked") == counts["blocked"] + 1 and cnt("not_started") == counts["not_started"] - 1, "Kanban: a card's status dropdown moves it between columns (keyboard alternative to dragging)")
    page.locator("#panelSaveStatus", has_text="Saved").wait_for(timeout=8000)
    src = page.locator('.kanban-col[data-status="not_started"] .kanban-card').first
    src.drag_to(page.locator('.kanban-col[data-status="completed"]'))
    page.wait_for_timeout(300)
    check(cnt("completed") == counts["completed"] + 1, "Kanban: drag and drop between columns still works")
    page.locator(".kanban-card").first.locator(".mini-btn").click(); page.wait_for_selector("#modalHost:not(.hidden)")
    check(page.inner_text("#modalTitle") != "", "Kanban: the pencil button opens the details dialog"); page.keyboard.press("Escape")
    check(pictographs(page) == "", "Kanban: no emoji or glyph icons")
    page.screenshot(path=f"{SHOTS}/kanban-light.png")
    audit(page, "Kanban (light)")

    # ======================= F. Skills checklist =======================
    go(page, "mastery")
    check(page.locator(".mastery-cat").count() == 13 and page.locator(".mastery-cat .progress-track").count() == 13, "Skills: 13 groups, each with its own progress bar")
    head = lambda: " ".join(page.locator(".mastery-cat >> nth=0 >> h3").inner_text().split())
    before = head()
    page.locator(".mastery-cat >> nth=0 >> .subtask-checkbox").first.click(); page.wait_for_timeout(200)
    after = head()
    check(before != after, f"Skills: ticking a skill updates the group's count: '{before}' -> '{after}'")
    check("line-through" in page.locator(".mastery-cat >> nth=0 >> .skill-title.done").first.evaluate("e => getComputedStyle(e).textDecorationLine"), "Skills: a finished skill is struck through (by class, not inline style)")
    check(pictographs(page) == "" and styles_ok(page), "Skills: no emoji, only dynamic inline styles")
    page.screenshot(path=f"{SHOTS}/mastery-light.png")
    audit(page, "Skills checklist (light)")

    # ======================= G. Reference =======================
    go(page, "reference")
    docs = page.evaluate("window.ROADMAP_DATA.reference.length")
    check(page.locator(".ref-card").count() == docs and page.locator(".ref-nav-btn").count() == docs, f"Reference: {docs} documents, each in the jump list")
    check(page.locator(".ref-content").bounding_box()["width"] <= 761, "Reference: reading column is at most 760px")
    page.locator(".ref-nav-btn").nth(6).click(); page.wait_for_timeout(300)
    y = page.locator(".ref-card").nth(6).bounding_box()["y"]
    check(55 <= y <= 130, f"Reference: choosing a document scrolls it to the top ({y:.0f}px)")
    check(page.locator(".ref-nav").evaluate("e => getComputedStyle(e).position") == "sticky", "Reference: the jump list is sticky")
    page.fill("#roadmapSearch", "Resource Strategy"); page.wait_for_timeout(300)
    visible_cards = page.locator(".ref-card:visible").count(); visible_nav = page.locator(".ref-nav-btn:visible").count()
    check(visible_cards == visible_nav and 0 < visible_cards < docs, f"Reference: search hides non-matching documents in both the list and the page ({visible_cards})")
    page.fill("#roadmapSearch", "")
    check(pictographs(page) == "", "Reference: no emoji or glyph icons")
    page.screenshot(path=f"{SHOTS}/reference-light.png")
    audit(page, "Reference (light)")
    # ======================= H. Roadmap settings menu dialogs: focus returns to the menu button =======================
    page.click("#roadmapMenuTrigger"); page.click("#resetBtn"); page.wait_for_selector("#modalHost:not(.hidden)")
    check(page.inner_text("#modalTitle") == "Reset all progress?" and styles_ok(page), "Reset dialog: named, and free of inline styles")
    audit(page, "Reset dialog")
    for _ in range(8): page.keyboard.press("Tab")
    check(page.evaluate("document.querySelector('#modalHost .modal').contains(document.activeElement)"), "Reset dialog: Tab stays inside")
    page.keyboard.press("Escape")
    check(page.evaluate("document.activeElement.id") == "roadmapMenuTrigger", "Reset dialog: Escape returns focus to the Roadmap menu button")
    page.click("#roadmapMenuTrigger"); page.click("#startMonthBtn"); page.wait_for_selector("#modalHost:not(.hidden)")
    audit(page, "Start month dialog"); page.keyboard.press("Escape")
    check(page.evaluate("document.activeElement.id") == "roadmapMenuTrigger", "Start month dialog: focus returns to the Roadmap menu button")
    check(not page.problems, "no page errors or CSP/console errors (desktop run)" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # ======================= I. Blank custom roadmap =======================
    ctx, page = new_context(browser)
    register(ctx, "b")
    ctx.request.post(BASE + "/api/roadmaps", data={"name": "Blank Plan", "description": "empty"})
    page.goto(BASE); page.wait_for_selector(".summary-bar")
    page.locator("article.roadmap-card", has_text="Blank Plan").locator(".btn-primary").click(); page.wait_for_selector(".build-step")
    check(page.locator(".build-step").count() == 3 and page.inner_text("h2.view-title") == "Let's build your roadmap", "Blank roadmap: heading and a three-step guide")
    check(page.locator(".step-num").first.get_attribute("aria-hidden") == "true" and pictographs(page) == "", "Blank roadmap: decorative numbers hidden from assistive tech; no emoji")
    audit(page, "Blank roadmap")
    page.screenshot(path=f"{SHOTS}/blank-roadmap.png")
    page.locator('[data-action="add-month"]').first.focus(); page.click('[data-action="add-month"]'); page.wait_for_selector("#modalHost:not(.hidden)")
    check(page.locator("#modalHost label[for]").count() >= 1 and page.inner_text("#modalTitle") != "", "Add month dialog: named, labels tied to fields")
    audit(page, "Add month dialog")
    page.keyboard.press("Escape")
    check(page.evaluate("document.activeElement.getAttribute('data-action')") == "add-month", "Add month dialog: focus returns to 'Add first month'")
    for v in ("timeline", "kanban", "checklist", "thisweek"):
        go(page, v)
        check(page.inner_text("#main").strip() != "" and pictographs(page) == "", f"Blank roadmap: {v} view renders without emoji")
    go(page, "timeline"); audit(page, "Blank roadmap: Timeline")
    check(not page.problems, "no page errors (blank roadmap)" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # ======================= J. Dark theme =======================
    ctx, page = new_context(browser, 1440, 1000, "dark")
    register(ctx, "d"); seed_progress(ctx, page)
    open_roadmap(page, "overview")
    for v in VIEWS:
        go(page, v)
        if v in ("overview", "kanban", "timeline"): page.screenshot(path=f"{SHOTS}/{v}-dark.png")
        audit(page, f"{v} (dark)")
    ctx.close()

    # ======================= K. Phone and tablet =======================
    for name, (w, h) in (("phone", (390, 900)), ("tablet", (820, 1000))):
        ctx, page = new_context(browser, w, h)
        register(ctx, name[:1] + "p"); seed_progress(ctx, page)
        open_roadmap(page, "overview")
        for v in ("overview", "timeline", "checklist", "thisweek", "mastery", "reference"):
            go(page, v)
            fits = page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            check(fits, f"{name}: {v} has no horizontal page scrolling")
        go(page, "kanban")
        check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"{name}: kanban does not scroll the page sideways")
        scroll = page.locator(".kanban-board").evaluate("e => ({sw: e.scrollWidth, cw: e.clientWidth, ox: getComputedStyle(e).overflowX})")
        check(scroll["ox"] in ("auto", "scroll") and scroll["sw"] > scroll["cw"], f"{name}: kanban board scrolls inside itself ({scroll['sw']} > {scroll['cw']})")
        if name == "phone":
            go(page, "checklist")
            row = page.locator(".subtask-row").first
            check(row.locator(".subtask-meta").bounding_box()["y"] > row.locator(".subtask-title").bounding_box()["y"], "phone: task controls wrap under the title")
            page.screenshot(path=f"{SHOTS}/checklist-phone.png")
            go(page, "reference")
            check(page.locator("#refJump").is_visible() and not page.locator(".ref-nav").is_visible(), "phone: Reference shows a 'Jump to' select instead of the side list")
            page.select_option("#refJump", index=5); page.wait_for_timeout(300)
            check(page.locator(".ref-card").nth(4).bounding_box()["y"] < 400, "phone: choosing a document in the select scrolls to it")
            page.screenshot(path=f"{SHOTS}/reference-phone.png")
        for v in ("overview", "checklist", "kanban"):
            go(page, v); audit(page, f"{v} ({name})")
        ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
```

---

*End of Phase 4 spec. Phase 5 (hardening) is specified separately.*
