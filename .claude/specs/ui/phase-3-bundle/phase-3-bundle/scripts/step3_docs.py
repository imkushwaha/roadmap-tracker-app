"""Phase 3 / documentation. Run from the repo root: python3 step3_docs.py"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match ({s.count(old)} found) for: {old[:80]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("README.md", [
    ("- **Delete** a roadmap (and its progress) from the card's **⋯** menu — always behind a confirmation dialog",
     "- **Delete** a roadmap (and its progress) from the card's **⋯** menu — always behind a confirmation dialog; a roadmap that has progress also asks you to **type its name**"),
    ("- **Create roadmap with AI** is shown as *Coming soon*\n",
     "- **New roadmap** dialog — choose *Blank roadmap* (name, description with a character counter, start month), restore the *AI Engineer roadmap* when you no longer have it, or see the disabled *Describe a goal (AI)* option marked **Soon**\n"
     "- **Find your roadmaps** — with two or more roadmaps, Home adds search (name and description), status filters with counts (All, In progress, Not started, Completed) and sorting (Recent activity, Name, Progress); switch between a **grid** and a **list** view (columns sort; your view and sort are remembered)\n"
     "- **Right-hand panel** — *Current focus* (the current month, and this week's section for the built-in roadmap, of your most recently used roadmap) and a dismissible *Getting started* checklist\n"),
])

patch("documentation/multi-roadmap.md", [
    ("and leaving a roadmap with unsaved edits asks first |",
     "and leaving a roadmap with unsaved edits asks first |\n"
     "| Home controls | `homeState` (view, sort, filter, search) in `js/app.js`; `renderHomeResults()` redraws only the results, so typing in search keeps focus. View and sort persist under `roadmap-dashboard:home`; the dismissed *Getting started* card under `roadmap-dashboard:getting-started` |\n"
     "| Dialogs | `openCreateRoadmapModal` (Blank / AI Engineer / AI soon), `confirmDeleteRoadmap` (typed name when `roadmapHasProgress`), shared `showModal` / `closeModal` (focus returns to the opener; Escape closes; Tab stays inside) |"),
])

patch("documentation/design-system.md", [
    ('Theme.set("dark");  // save + apply + notify',
     'Theme.set("dark");  // save + apply + notify\nTheme.isSaved();    // true once the user has explicitly chosen (used by "Getting started")'),
    ("| 3 | Home flows (New roadmap dialog, filters, list view) | Not started |",
     "| 3 | Home flows (New roadmap dialog, filters, list view, right rail, typed-name delete) | Done |"),
    ("## Motion and accessibility rules",
     """## Home flows (Phase 3)

- **Option rows** (`.option-row`, in the New roadmap dialog): a bordered radio card; `.is-selected` (accent border and soft fill) and `.is-disabled` (sunken background, muted text, no opacity so contrast holds). A `.badge-soon` marks features that are not available yet.
- **Dialog behaviour** (all dialogs): `role="dialog"`, named by the first `<h2>` (`#modalTitle`); Escape closes; Tab/Shift+Tab stay inside; dialogs opened with `showModal()` return focus to what opened them.
- **Typed confirmation** for destructive actions on real work: the confirm button stays disabled until the exact name is typed (case-sensitive); focus starts on Cancel.
- **Responsive tables** use container queries on `.home-main`, so columns hide according to the space next to the rail rather than the window width; below 560px a row becomes a small card.
- **Filter chips** reuse `.chip-filter` with `aria-pressed` and a `.chip-count`; the view toggle uses `.view-toggle`/`.view-btn`.

## Motion and accessibility rules"""),
])
print("docs updated")
