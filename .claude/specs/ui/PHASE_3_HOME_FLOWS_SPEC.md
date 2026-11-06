# Phase 3 — Home Flows: Implementation Spec

> **Audience:** an AI coding agent (or developer) implementing this phase in the *Roadmap Tracker* repository.
> **Status of this spec:** every step below was executed on a copy of the repository with Phases 0–2 applied, and verified: `npm test` 79/79, Phase 3 UI harness **88/88**, and the earlier harnesses still pass (Phase 0: 61/61, Phase 1: 67/67, Phase 2: 114/114 after the small harness patch in Task 5). If you follow it exactly you will get the same result.

| | |
|---|---|
| **Phase** | 3 of 5 — Home flows |
| **Depends on** | **Phases 0, 1 and 2 completed and verified** (Section 2) |
| **Branch** | continue on `feature/ui-redesign` |
| **Effort** | about 1.5 working days by hand; under an hour of agent time because every script is supplied |
| **Visible result** | Home gains search, status filters with counts, sorting, a Grid/List toggle, a table view, and a right-hand panel (**Current focus**, **Getting started**). The New roadmap dialog offers Blank / AI Engineer / AI (soon). Deleting a roadmap that has progress requires typing its name. All dialogs close on Escape, keep Tab inside, and give focus back |
| **Backend change** | **None.** Everything is derived from the `stats` added in Phase 2 |
| **Risk** | Low–medium. Home rendering and the create/delete dialogs are rewritten; the roadmap views are untouched |
| **Next phase** | Phase 4 — the seven roadmap views (separate spec) |

---

## 0. Rules for the implementing agent (read first)

1. **Do exactly what this document says. Do not redesign.** Names, copy, sizes and behaviour are decided.
2. **Phases 0–2 must already be applied.** If `css/home.css`, `js/roadmap-stats.js`, `renderDashboard`, `roadmapCard` or `window.MonthStrip` are missing, stop and report.
3. **No new npm dependencies, no build step, no server or database change.** Do not edit anything under `server/`.
4. **Do not change** the roadmap views, save/conflict logic, auth logic, routing, `js/api.js`, or the existing API. Phase 3 only changes Home and the shared dialog behaviour.
5. **Keep all existing element IDs and `data-action` names** listed in Section 5 (the Phase 2 harness and the app depend on them).
6. **Security rules** (`CLAUDE.md`): roadmap names and descriptions are user text — always pass them through `esc()` when building HTML (the supplied code does); no inline scripts or `eval` (strict CSP); only preferences are stored in `localStorage` (never tokens or personal data).
7. **If a script in this spec fails an `assert`**, the repository has drifted. Do not force it. Read that script's "Intent" list, apply the equivalent edit by hand, and record the difference in your hand-off.
8. **Run the verification (Section 7) before declaring done.** Commit in task order.

---

## 1. Goal and scope

### 1.1 Problems this phase fixes

| # | Problem after Phase 2 | Fix |
|---|---|---|
| 1 | With many roadmaps there is no way to find one | Search (name + description), status filters with counts, sort |
| 2 | Only a card grid | Grid/List toggle; sortable table; compact cards on phones |
| 3 | The right side of Home is empty | Right-hand panel: **Current focus** and **Getting started** |
| 4 | "New roadmap" opens the old plain form; restoring the built-in roadmap is a separate notice; no hint of AI | New dialog with three options (Blank, AI Engineer, AI soon) |
| 5 | Deleting a roadmap with months of progress needs one click | Type the roadmap's name to confirm (only when real work would be lost) |
| 6 | Dialogs trap nobody: Tab escapes behind them, Escape does nothing, focus is lost | Escape closes, Tab stays inside, focus returns to the opener, dialogs are named for screen readers |

### 1.2 Deliverables

| # | Deliverable | Files |
|---|---|---|
| 1 | Home logic: preferences, filter, sort, cards, table, toolbar, rail, `renderDashboard` | `js/app.js` |
| 2 | New roadmap dialog + typed-name delete dialog | `js/app.js` |
| 3 | Shared dialog behaviour (`showModal`, `closeModal`, Escape, Tab trap) | `js/app.js` |
| 4 | `Theme.isSaved()` | `js/theme-boot.js` |
| 5 | Home Phase 3 styles (toolbar, table with container queries, rail, option rows) | `css/home.css` |
| 6 | Documentation | `README.md`, `documentation/multi-roadmap.md`, `documentation/design-system.md` |
| 7 | Patch that keeps the Phase 2 harness runnable | Appendix B4 |

### 1.3 Out of scope (do NOT do these here)

- Rename roadmap, duplicate, undo delete, "Account settings" (need backend work).
- The AI roadmap generator itself (the option is disabled and marked **Soon**).
- Restyling the seven roadmap views or their dialogs (Phase 4). The existing task-details, start-month, reset, import, conflict and legacy dialogs keep their own markup and only gain Escape + Tab trap from the shared behaviour.
- Any server, API or database change.

---

## 2. Preconditions

```bash
git status                                  # on feature/ui-redesign, clean
npm test                                    # expect: tests 79, pass 79, fail 0
ls css/home.css css/shell.css js/roadmap-stats.js js/month-strip.js js/theme-boot.js
grep -c "function renderDashboard" js/app.js     # expect 1
grep -c "function roadmapCard" js/app.js         # expect 1
grep -c "function openCreateRoadmapModal" js/app.js   # expect 1
```

Optionally run the Phase 0, 1 and 2 harnesses first so you know the baseline is green.

### 2.1 What exists after Phase 2 (facts you must respect)

- `renderDashboard(roadmaps)` builds Home: page head (**New roadmap** button), restore notice, summary bar, a card grid, using `roadmapCard(r, animate)` and `summaryBar(roadmaps)`. `dashboardRoadmaps` holds the list; each item has `id`, `name`, `description`, `source` (`"builtin_ai_engineer"` or `"custom"`), `createdAt`, `lastActivityAt` and `stats` (Phase 2 contract: `total`, `completed`, `inProgress`, `blocked`, `completedLast7Days`, `startMonth`, `months[]`).
- Helpers: `stripMonths(stats)`, `pctOf(stats)`, `cardAction(stats)` (Start / Continue / Review / Build plan / Open), `monthPosition(stats)`, `currentMonthIndex(startMonth, count)`, `monthKeyOffset(startMonth, offset)`, `describeActivity(iso)`, `daysBetween`, `TODAY`, `MAX_ROADMAPS = 20`, `BUILTIN_SOURCE`, `BUILTIN_DATA`.
- `onDashboardClick(e)` is the delegated click handler for `#dashboardContent` (and the sidebar). It handles `open-roadmap`, `delete-roadmap`, `restore-builtin`, `create-roadmap`, `retry-dashboard`, card menus, and clicks on a card body.
- The shared dialog host is `#modalHost` (`.modal-backdrop` + `.modal[role=dialog][aria-modal]`). Each dialog writes its HTML into `.modal` and removes `hidden`. `closeModal()` just adds `hidden`; clicking the backdrop already closes (existing handler); `onModalClick` handles `data-action` buttons (`close-modal`, `confirm-delete-roadmap`, …).
- `openCreateRoadmapModal`, `submitCreateRoadmap`, `confirmDeleteRoadmap`, `deleteRoadmap`, `restoreBuiltinRoadmap` exist (Phase 2 left them as in the original app).
- `openAboutModal` (Phase 2) opens the About dialog.

---

## 3. Design specification

### 3.1 Home layout

```
Roadmaps                                              [▦|☰]  [+ New roadmap]
Track progress across your plans.

┌ Roadmaps ┬ Tasks done ┬ Overall ┬ This week ┐                 ┌ Current focus ───────┐
│ 4        │ 137 / 871  │ 16%     │ 63        │                 │ Data Engineering     │
└──────────┴────────────┴─────────┴───────────┘                 │ Month 1: Focus month │
[🔍 Search roadmaps…                       ]   Sort by [Recent ▾]│ [Review]             │
(All 4) (In progress 2) (Not started 1) (Completed 1)           └──────────────────────┘
┌─────────────┐ ┌─────────────┐                                 ┌ Getting started ─────┐
│ card        │ │ card        │                                 │ 3 of 4 done          │
└─────────────┘ └─────────────┘                                 │ ✓ Complete first task│
                                                                │ ✓ Create custom …    │
                                                                │ ○ Choose appearance  │
                                                                │ Dismiss              │
                                                                └──────────────────────┘
```

| Item | Spec |
|---|---|
| `.home-layout` | Single column by default. At ≥ 1280px **and** when a rail exists (`.has-rail`): two columns `minmax(0,1fr) 320px`, gap 24px. Below 1280px the rail simply follows the list (it does **not** become a banner) |
| `.home-main` | The list column. It is a **size container** (`container-type: inline-size; container-name: homemain`) so tables and the toolbar adapt to *its* width |
| `.home-rail#homeRail` | Holds the rail cards; empty → `display: none` and `.has-rail` is removed |
| Page head actions | When there are **2 or more** roadmaps: the Grid/List toggle (`.view-toggle`) then **New roadmap**. With one roadmap only **New roadmap** |
| Toolbar | Shown only with **2 or more** roadmaps. With fewer, `homeState.filter` and `homeState.search` are reset to `"all"` and `""` and the grid is used regardless of the saved view |
| One roadmap | No toolbar, no toggle; summary bar, one card, and the rail |
| Zero roadmaps | Unchanged empty state (Phase 2) |

### 3.2 Toolbar

| Control | Spec |
|---|---|
| Search `#homeSearch` | `type="search"`, `aria-label="Search roadmaps"`, placeholder "Search roadmaps", leading search icon, 36px high, max 360px. Matches `name` **or** `description`, case-insensitive substring. Updates results on every keystroke **without redrawing the input** (focus stays) |
| Status chips `#homeFilters` | `role="group" aria-label="Filter by status"`; four buttons `.chip-filter` with `data-action="filter-status"`, `data-value` ∈ `all`, `in_progress`, `not_started`, `completed`, `aria-pressed`, and a count `<span class="chip-count">` computed over **all** roadmaps (not the filtered list). Labels: **All**, **In progress**, **Not started**, **Completed** |
| Sort `#homeSort` | `<select class="select-filter">` with a visible label "Sort by": `recent` (Recent activity), `name` (Name), `progress` (Progress) |
| Result count `#homeResultCount` | `class="sr-only" role="status"`: "`N roadmap(s) shown`" after every change |

Toolbar layout: a grid with named areas. Container width < 860px: row 1 = search + sort, row 2 = chips. ≥ 860px: one row = search (200–300px) · chips · sort.

### 3.3 Filter, sort and persistence rules

**Status of a roadmap** (`roadmapState`):

| Condition | State |
|---|---|
| no `stats`, or `stats.total === 0` | `not_started` |
| `completed === total` | `completed` |
| `completed + inProgress + blocked > 0` | `in_progress` |
| otherwise | `not_started` |

**Sort** (`sortRoadmaps`): each key has a default direction, `SORT_DEFAULT_DIR = { recent: "desc", name: "asc", progress: "desc" }`.

| Key | Order | Ties |
|---|---|---|
| `recent` | `lastActivityAt` (roadmaps never saved sort as oldest) | lower `id` first |
| `name` | `localeCompare` with `sensitivity: "base"` (so "AI Engineer Roadmap" sorts before "Alpha") | `id` |
| `progress` | `pctOf(stats)`, then `completed` count | `id` |

Direction `asc`/`desc` multiplies the comparison. Choosing a key from the **select** sets that key's default direction. Clicking a **table header** on the active key flips the direction; on another key it selects that key with its default direction.

**Persistence:** `localStorage["roadmap-dashboard:home"]` = `{ "view": "grid"|"list", "sortKey": …, "sortDir": … }`, written on every view/sort change and read once at start-up (`loadHomePrefs`, invalid or blocked storage → defaults). **Filter and search are never persisted.**

### 3.4 No-result states

Inside `#homeResults`, an `.empty-panel.empty-panel-sm` with an `h2` and one button (`data-action="clear-filters"`, which resets both filter and search):

| Situation | Heading | Button |
|---|---|---|
| search text present | `No roadmaps match “<text>”.` (curly quotes, text escaped) | **Clear search** if the filter is "All", otherwise **Clear filters** |
| filter only | `No roadmaps in this view.` | **Clear filters** |

### 3.5 List view

A table in `.table-wrap` (`1px` border, `--radius-md`). Columns:

| Column | Content | Sortable (header button, `aria-sort`) |
|---|---|---|
| Roadmap | name (600 weight, ellipsis) and description (13px muted, ellipsis) | yes (`name`) |
| Type | badge **Built-in** / **Custom** (`.col-type`) | no |
| Progress | **sm** Month Strip and the percent (or "No months" when total is 0) | yes (`progress`) |
| Current month | `monthPosition(stats)` or "—" (`.col-month`) | no |
| Last activity | **Today** / **Yesterday** / **N days ago** / **Not started yet** (`.col-activity`; `activityShort`) | yes (`recent`) |
| (actions) | header `sr-only` "Actions"; primary button (`cardAction`, `btn-sm`) + the ⋯ menu | no |

- Header cells: `scope="col"`, `aria-sort` = `ascending` / `descending` on the active sort column, `none` on the other sortable ones. The header button shows a chevron (rotated for ascending).
- A row (`tr.rt-row[data-id]`) is clickable like a card (clicking text opens the roadmap; buttons keep their own action). Hover = `--bg-sunken`.
- The name column absorbs spare width and truncates (`width:100%; max-width:0` on the cell).
- **Column hiding follows the container, not the window:**

| `.home-main` width | Hidden |
|---|---|
| ≤ 899px | Current month |
| ≤ 679px | + Type |
| ≤ 559px | The table becomes **stacked cards**: header hidden; each row is a grid (name + progress on the left, action on the right); Type, Current month, Last activity and descriptions hidden. Sorting then uses the "Sort by" select |

- The overflow menu and its Delete action are identical to the card's (`roadmapMenu(r)`).
- The table must not overflow its container (checked by the harness) and must never overlap the rail.

### 3.6 Right rail

**Current focus** (`focusCard`) — shown when at least one roadmap has months:

| Part | Rule |
|---|---|
| Which roadmap | Among roadmaps with `stats.months.length > 0`: the one with the **latest `lastActivityAt`**; if none has activity, the first |
| Heading / sub | `h2` "Current focus"; sub = roadmap name |
| Main line | If today falls inside the roadmap's months: `Month N: <title or "Untitled">`. Before the start: `Starts <Month YYYY>` (long month name). After the end: `The planned months have passed.` |
| Week line (built-in only) | The built-in roadmap's week sections cover days 1–28 of each month in 7-day blocks: `week = floor((dayOfMonth − 1) / 7)`; if `week > 3` or the month has no such section → no line. Otherwise the section of that month's `sections` with `type === "week"` and `(weekNumber − 1) % 4 === week`; show its `title` (e.g. "Week 5 — Distributed Systems Fundamentals — D3"). Months 9–10 use "theme" sections, so they show no week line |
| Button | primary small, `data-action="open-roadmap"`, label from `cardAction(stats)` |

**Getting started** (`gettingStartedCard`) — a checklist of four items, each done/not done:

| # | Label | Done when |
|---|---|---|
| 1 | Complete your first task | any roadmap has `stats.completed > 0` |
| 2 | Create a custom roadmap | any roadmap with `source !== "builtin_ai_engineer"` |
| 3 | Add a month to your roadmap | any custom roadmap has `stats.months.length > 0` |
| 4 | Choose an appearance | `Theme.isSaved()` (the user explicitly picked Light, Dark or System) |

Heading "Getting started", sub "`n of 4 done`", list (done items: check-circle icon in green, muted text, visually-hidden " (done)"; open items: a hollow circle `.rail-dot`), and a ghost **Dismiss** button (`data-action="dismiss-getting-started"`). The card is **not rendered** when dismissed (`localStorage["roadmap-dashboard:getting-started"] === "dismissed"`) or when all four are done. Dismiss re-renders the rail only and removes `.has-rail` when the rail ends up empty.

Both cards are `<section aria-labelledby>`; the rail is `<aside aria-label="Focus and tips">`.

### 3.7 New roadmap dialog

Opened by any `data-action="create-roadmap"` (page head button, empty state "Blank roadmap"). Width 560px (`.modal:has(#createRoadmapForm)`). Title `h2` **New roadmap**.

| Part | Spec |
|---|---|
| Options | `div.option-list[role=radiogroup][aria-label="How do you want to start?"]` of three `label.option-row` with radio `name="newRoadmapKind"` |
| 1 · **Blank roadmap** (`value="blank"`, checked) | "Build your own plan with months, sections, topics and tasks." |
| 2 · **AI Engineer roadmap** (`value="builtin"`) | Enabled only if the account has no built-in roadmap. Enabled text: "The 10-month Production AI Engineer plan, restored with fresh progress." Disabled (`.is-disabled`, `disabled`): "You already have this roadmap." |
| 3 · **Describe a goal (AI)** (`value="ai"`, always disabled) | Title + `<span class="badge badge-soon">Soon</span>`; text "Describe a goal and let AI draft the plan."; `title="Coming soon: describe a goal and let AI draft the plan."` |
| Blank fields `#newBlankFields` | Roadmap name `#newRoadmapName` (max 80, placeholder "e.g. Learn Rust in 12 weeks"); Description `#newRoadmapDesc` (optional, max 300) with live counter `#newRoadmapCount` "`n / 300`"; "Month 1 starts in" `#newRoadmapStart` (`type=month`, default and minimum = the current month) |
| Error `#createRoadmapError` | `role="alert"`, same banner style as auth; messages unchanged: "Give your roadmap a name.", "Start month can't be before the current month.", or the server's message |
| Buttons | **Cancel** (`data-action="close-modal"`) and submit `#createRoadmapSubmit` — label **Create roadmap**, or **Restore roadmap** while option 2 is selected |
| Selecting an option | `syncCreateKind()`: toggles `.is-selected`, hides `#newBlankFields` unless Blank is selected, relabels the submit button, clears the error |
| Submit (Blank) | Same validation and API call as before (`RoadmapApi.create`), then `closeModal()` and `openRoadmap(id)` |
| Submit (AI Engineer) | `closeModal()` then the existing `restoreBuiltinRoadmap()` (toast "AI Engineer Roadmap restored.") |
| Initial focus | the name field |

The Phase 2 limit rule stays: at 20 roadmaps the page-head button is disabled, so the dialog cannot be opened from it.

### 3.8 Delete dialog

Opened by the card/row menu's **Delete roadmap…** (`confirmDeleteRoadmap(id)`), width 440px (`.modal:has(#deleteRoadmapForm)`).

| Part | Spec |
|---|---|
| Title | `Delete “<name>”?` (curly quotes, escaped) |
| Text | "This permanently deletes the roadmap and all of its progress: statuses, notes, links, due dates and anything you added. This can't be undone." followed, when `stats.completed > 0`, by " You have completed X of Y tasks." |
| **Needs typed name?** | `roadmapHasProgress(r)`: `stats` exists **and** (`completed + inProgress + blocked > 0` **or** (the roadmap is custom **and** `stats.total > 0`)). So an untouched built-in roadmap, or an empty custom one, is deleted with a plain confirmation. (Notes or due dates alone on an otherwise untouched roadmap do not count.) |
| Name field | Only when needed: label "Type the roadmap name to confirm", input `#deleteConfirmName` (`autocomplete="off"`, `spellcheck="false"`, `data-name` = the exact name), hint "Type exactly: **<name>**" |
| Buttons | **Cancel** (`#deleteCancelBtn`, `close-modal`) and danger **Delete roadmap** (`#deleteConfirmBtn`, `data-action="confirm-delete-roadmap"`, `data-id`); the danger button is `disabled` until `input.value.trim() === data-name` (exact, case-sensitive) |
| Keyboard | **Initial focus on Cancel.** Enter inside the name field submits only when the name matches (`#deleteRoadmapForm` submit) |
| After deleting | existing behaviour: toast "Roadmap deleted.", Home reloads |
| On Cancel / Escape | focus returns to that roadmap's ⋯ button |

### 3.9 Shared dialog behaviour (applies to every dialog)

| Behaviour | Spec |
|---|---|
| Name | `showModal()` gives the dialog `aria-labelledby="modalTitle"` (the first `h2` receives `id="modalTitle"`); if there is no `h2` the attribute is removed |
| Escape | closes the open dialog (any dialog, including conflict/reset/import ones — the backdrop could already close them) |
| Tab trap | Tab and Shift+Tab cycle through the dialog's enabled, visible, tabbable controls; if there are none, Tab is swallowed |
| Return focus | Dialogs opened through `showModal(returnFocus?)` — **About, New roadmap, Delete** — return focus to `returnFocus` (default: the element focused when it opened) when closed. Other dialogs keep their old markup and do **not** restore focus yet (Phase 4) |
| `closeModal()` | no-op when already hidden; clears the remembered element |

### 3.10 Storage keys added

`roadmap-dashboard:home` (view and sort), `roadmap-dashboard:getting-started` (`"dismissed"`). Both wrapped in try/catch.

### 3.11 Accessibility requirements

- Filter chips are buttons with `aria-pressed`; the toggle buttons have `aria-label` and `aria-pressed`; the sort select and search input have labels; results announce their count.
- Table headers: `scope="col"`, `aria-sort`; sort headers are real `<button>`s.
- Option rows are real radios inside labels with a visible focus ring (`:focus-within`); disabled options keep readable text (no opacity trick).
- Dialogs: role, name, Escape, Tab trap, focus return (3.9). The delete confirm button is disabled until the name matches (not hidden).
- axe-core WCAG 2.2 A/AA: 0 violations on Home (one roadmap; grid; list; no-result), the New roadmap dialog, the Delete dialog (light and dark), and the phone layouts.

---

## 4. Tasks (do them in this order)

> Run every `python3 step3_*.py` from the **repository root**. Keep scripts outside the repo (or delete them afterwards); **do not commit them.**

### Task 1 — Baseline
Confirm Section 2 passes (79/79).

### Task 2 — `Theme.isSaved()` and the Phase 3 styles
Run **Appendix B1** (`step3_misc.py`).
**Intent:** (a) `js/theme-boot.js`: add `isSaved()` to `window.Theme` returning whether `localStorage["roadmap-dashboard:theme"]` holds `light`, `dark` or `system` (false when storage is blocked); (b) append the Phase 3 block to `css/home.css` (home layout and rail, view toggle, toolbar, list table with container queries, rail cards, option rows, dialog sizes).
**Acceptance:** prints `js/theme-boot.js and css/home.css updated`.

### Task 3 — Home, dialogs and shared dialog behaviour in `js/app.js`
Run **Appendix B2** (`step3_appjs.py`).
**Intent:** (a) replace the block from `roadmapCard` up to the comment `// Sidebar quick-switcher (Home only)` with the Phase 3 Home code (preferences, filters, sort, `roadmapMenu`, `roadmapCard`, table, `summaryBar`, view toggle, toolbar, `renderHomeResults`, rail, `renderDashboard`); (b) replace `onDashboardClick` and add `onDashboardInput` / `onDashboardChange`; (c) replace the create/submit/delete-confirmation functions with the new dialogs and add `syncCreateKind`; (d) replace `closeModal` with `showModal` / `closeModal` / `trapModalFocus`, and make `openAboutModal` use `showModal()`; (e) in `wireSyncEvents`: extend the `#modalHost` submit handler (create + delete forms), add `input` and `change` handlers for the dialogs, add the document-level Escape/Tab handler, add `input` and `change` listeners on `#dashboardContent`; (f) call `loadHomePrefs()` in `init()` after `initSidebar()`.
**Acceptance:** prints `js/app.js updated`; `node --check js/app.js` passes.

### Task 4 — Documentation (required by `CLAUDE.md`)
Run **Appendix B3** (`step3_docs.py`). Also copy this spec to `.claude/specs/ui-redesign-phase-3.md` (recommended).
**Acceptance:** prints `docs updated`.

### Task 5 — Keep the Phase 2 harness runnable
Phase 3 requires typing the name before deleting a roadmap that has progress, so the Phase 2 harness must do the same. Run **Appendix B4** once against your copy of `verify_phase2.py`:
```bash
python3 patch_phase2_harness.py /tmp/ui-verify/verify_phase2.py     # prints: patched 3 delete confirmations in …
```

### Task 6 — Verify
Follow Section 7.

---

## 5. Contracts

### 5.1 Preserved (must still exist and behave the same)

`#createRoadmapForm`, `#newRoadmapName`, `#newRoadmapDesc`, `#newRoadmapStart`, `#createRoadmapError`, `#createRoadmapSubmit`; `data-action` values `open-roadmap`, `delete-roadmap`, `restore-builtin`, `create-roadmap`, `retry-dashboard`, `close-modal`, `confirm-delete-roadmap`, `about`, `go-home`; `data-menu-trigger`; `.roadmap-card[data-id]`; the Phase 2 Home structure (`.page-head`, `.page-actions`, `.summary-bar`, `.notice-row`, `.empty-panel`, `.roadmap-grid`, `.rc-menu`).

### 5.2 New element IDs

`homeSearch`, `homeSort`, `homeFilters`, `homeResults`, `homeResultCount`, `homeLayout`, `homeRail`, `focusHeading`, `startedHeading`, `newBlankFields`, `newRoadmapCount`, `deleteRoadmapForm`, `deleteConfirmName`, `deleteConfirmBtn`, `deleteCancelBtn`, `modalTitle` (set on the open dialog's `h2`).

New `data-action` values: `filter-status` (`data-value`), `set-view` (`data-value` = `grid`\|`list`), `sort-by` (`data-value` = `name`\|`progress`\|`recent`), `clear-filters`, `dismiss-getting-started`.

### 5.3 New functions in `js/app.js` (names Phase 4 may rely on)

`loadHomePrefs`, `saveHomePrefs`, `roadmapState`, `roadmapHasProgress`, `sortRoadmaps`, `visibleRoadmaps`, `roadmapMenu`, `activityShort`, `sortHeader`, `roadmapTable`, `viewToggle`, `homeToolbar`, `renderHomeResults`, `focusRoadmap`, `builtinWeekFocus`, `focusCard`, `gettingStartedItems`, `gettingStartedCard`, `homeRailHtml`, `onDashboardInput`, `onDashboardChange`, `syncCreateKind`, `showModal`, `closeModal`, `trapModalFocus`. State: `homeState`, `modalReturnFocus`; constants `HOME_PREFS_KEY`, `GETTING_STARTED_KEY`, `SORT_DEFAULT_DIR`, `STATUS_FILTERS`.

### 5.4 New CSS classes

`.home-layout` (`.has-rail`), `.home-main`, `.home-rail`, `.view-toggle`, `.view-btn`, `.home-toolbar`, `.home-search`, `.home-sort`, `.chip-count`, `.table-wrap`, `.rtable`, `.th-btn`, `.th-arrow`, `.rt-row`, `.rt-name-cell`, `.rt-name`, `.rt-desc`, `.rt-progress`, `.rt-pct`, `.rt-actions`, `.col-type`, `.col-month`, `.col-activity`, `.empty-panel-sm`, `.rail-card`, `.rail-title`, `.rail-sub`, `.rail-main`, `.rail-week`, `.rail-list`, `.rail-dot`, `.option-list`, `.option-row` (`.is-selected`, `.is-disabled`), `.option-body`, `.option-title`, `.option-desc`, `.badge-soon`, `.dialog-text`.

---

## 6. Acceptance criteria (checklist)

**Home**
- [ ] One roadmap: no toolbar or toggle; the summary bar, the card and the rail show. Zero roadmaps: the Phase 2 empty state.
- [ ] Two or more roadmaps: search, status chips with correct counts, sort select and the Grid/List toggle appear.
- [ ] Filters produce exactly the sets in 3.3; search matches names **and** descriptions; typing keeps focus in the box; the result count is announced.
- [ ] No-match states show the right heading and button (3.4); the button restores everything.
- [ ] Sort by Name is A–Z with case-insensitive, accent-tolerant comparison; Progress is high-first; Recent puts never-saved roadmaps last.
- [ ] List view: table with the columns in 3.5, correct `aria-sort`, header clicks change/flip the sort, rows open roadmaps, the table never overlaps the rail, the "Current month" column hides in the narrow column and appears on wide screens (1920px), and rows become stacked cards on phones.
- [ ] View and sort survive a reload; filter and search do not.
- [ ] Rail: Current focus names the right roadmap/month (and the week for the built-in roadmap); Getting started counts items correctly, **Dismiss** is remembered, and the card disappears when all four are done. Below 1280px the rail sits under the list.

**Dialogs**
- [ ] New roadmap: three options as in 3.7; Blank is preselected and the name field has focus; the AI option is disabled with **Soon**; the built-in option is disabled when you already have that roadmap and enabled when you do not (choosing it hides the blank fields and relabels the button **Restore roadmap**); the description counter updates; validation messages unchanged; creating opens the new roadmap.
- [ ] Delete: typed name required **only** when the roadmap has progress (3.8); exact (case-sensitive) match enables Delete; Enter submits only on a match; focus starts on Cancel; Escape cancels and returns focus to the ⋯ button; the toast "Roadmap deleted." appears.
- [ ] All dialogs: Escape closes, Tab stays inside, About/New/Delete return focus to their opener.

**Quality**
- [ ] axe-core 0 violations (3.11), no console/CSP errors, no horizontal scrolling at 390px.
- [ ] `npm test` still 79/79; **no change under `server/`**.
- [ ] Phase 0 (61/61), Phase 1 (67/67) and patched Phase 2 (114/114) harnesses pass.
- [ ] The static ID check from the Phase 2 spec (Section 7.2) still reports no missing IDs.
- [ ] Docs updated.

---

## 7. Verification

### 7.1 Automated
```bash
npm test      # expect: tests 79, pass 79, fail 0
```

### 7.2 Static ID check
Re-run the check from the Phase 2 spec (Section 7.2); expect `missing ids: []`.

### 7.3 UI harnesses

Keep these **outside the repo** in one folder (e.g. `/tmp/ui-verify/`): `serve-demo.js` + `verify_phase0.py` (Phase 0 spec), `verify_phase1.py` (Phase 1 spec), `verify_phase2.py` (Phase 2 spec, then patched by Task 5) and this phase's `verify_phase3.py` (Appendix C1).

```bash
npm install --prefix /tmp/ui-verify axe-core
node /tmp/ui-verify/serve-demo.js "$(pwd)" 3111 &                 # keep running
AXE=/tmp/ui-verify/node_modules/axe-core/axe.min.js; U=http://127.0.0.1:3111
python3 /tmp/ui-verify/verify_phase3.py $U $AXE      # expect: RESULT 88/88
python3 /tmp/ui-verify/verify_phase2.py $U $AXE      # regression (patched): RESULT 114/114
python3 /tmp/ui-verify/verify_phase1.py $U $AXE      # regression: RESULT 67/67
python3 /tmp/ui-verify/verify_phase0.py $U $AXE      # regression: RESULT 61/61
```

The Phase 3 harness registers fresh users, creates roadmaps through the API (custom ones with real tasks, so "In progress" and "Completed" exist), then exercises the dialogs, filters, search, sorting, list view (at 1440px, 1920px and on a phone), the rail, typed-name delete, restore through the dialog, focus return and the Tab trap, and runs axe in light and dark. Screenshots go to `/tmp/ui-verify/shots-p3`. It adapts to today's date when checking the week line.

### 7.4 Visual checklist

| Screenshot | What you should see |
|---|---|
| `home-one-roadmap.png` | Summary bar, one card, and the rail at the right: **Current focus** (roadmap name, "Month N: …", a week line if applicable, blue **Start**) and **Getting started** ("0 of 4 done", four hollow circles, **Dismiss**) |
| `dialog-new.png` | 560px dialog "New roadmap": three bordered option rows (Blank selected with blue border and light-blue fill; AI Engineer greyed with "You already have this roadmap."; "Describe a goal (AI)" greyed with a blue **Soon** pill), then name, description with "5 / 300", start month, Cancel / **Create roadmap** |
| `home-no-match.png` | Toolbar with "zzz" typed and a panel "No roadmaps match “zzz”." with **Clear search** |
| `home-list.png` | Table (Roadmap, Type, Progress with a small strip and %, Last activity with a chevron, action buttons + ⋯) beside the rail; the **Current month** column is hidden at this width |
| `dialog-delete.png` | 440px dialog "Delete “Gamma”?" with the progress sentence, a name field and hint "Type exactly: **Gamma**", Cancel and a **faded red** Delete button (disabled) |
| `home-list-phone.png` | Rows as small cards: name and strip on the left, **Continue/Start** and ⋯ on the right; no horizontal scroll; rail cards stacked under the list |
| `home-dark.png` | Same layout in the dark theme |

### 7.5 Known and acceptable

- The rail never turns into a banner on phones; it stacks below the list (simpler and keeps the content visible).
- "Getting started" has four items; "set your start month" was dropped because the list API does not say whether the user chose one.
- Only About / New roadmap / Delete restore focus to their opener; the older dialogs get Escape and the Tab trap but not focus return (Phase 4 finishes that).
- Escape also closes the conflict dialog (the backdrop already could); the save chip lets the user reopen it.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Typing in search loses focus | Results are being redrawn by `renderDashboard` instead of `renderHomeResults`; the input must live outside `#homeResults` |
| List view overlaps the rail | `.home-main` is missing `container-type: inline-size`, or the columns are hidden with media queries instead of `@container homemain` |
| List view columns never hide | Container queries need the `container-name: homemain` on `.home-main`; check the Phase 3 CSS was appended to `css/home.css` |
| Delete button is never enabled | `data-name` differs from what was typed (curly quotes, trailing spaces); the comparison is `value.trim() === dataset.name` |
| Focus does not return after closing | The dialog was opened without `showModal()`; About, New and Delete must call it |
| Escape does nothing in a dialog | The document-level keydown handler was not added in `wireSyncEvents` |
| "Choose an appearance" never completes | `Theme.isSaved` missing (Task 2); or storage is blocked |
| Phase 2 harness fails at a delete step | Task 5 patch not applied |
| `npm test` fails | Phase 3 must not touch `server/`; check you did not edit it |
| A `step3_*.py` assertion fails | Repo drifted; apply the Intent list manually |

---

## 9. Hand-off

Report: commits, `npm test`, all four harness result lines, the static ID check, and any manual deviations.

**Phase 4 assumes** these exist and are unchanged: `showModal` / `closeModal` / `trapModalFocus` and the document-level Escape handler (Phase 4 converts the remaining dialogs — task details, start month, reset, import, conflict, legacy, add month/section/topic/tasks — to `showModal()` and removes their duplicated markup styles), the option-row and dialog classes, `.rail-*`, `Theme.isSaved`, the container-query pattern on `.home-main`, and the view-button contract `#tabs .tab[data-view]`.

**Rollback:** revert the Phase 3 commits. No server, API, database or data change was made.

---

# Appendices


## Appendix B1 — `step3_misc.py` (Task 2)

Run from the repo root: `python3 step3_misc.py`. The Phase 3 CSS is embedded in this script.

```python
"""Phase 3 / small additions to earlier files: Theme.isSaved() and the Phase 3 styles.
Run from the repo root: python3 step3_misc.py"""

# 1. js/theme-boot.js: report whether the user has chosen an appearance (used by "Getting started")
P = "js/theme-boot.js"
s = open(P, encoding="utf-8").read()
old = "    get: read,\n"
assert s.count(old) == 1 and "isSaved" not in s, "theme-boot.js is not in the expected state"
s = s.replace(old, old + """    isSaved() {
      try { return MODES.includes(localStorage.getItem(KEY)); } catch { return false; }
    },
""")
open(P, "w", encoding="utf-8").write(s)

# 2. css/home.css: append the Phase 3 styles
P = "css/home.css"
s = open(P, encoding="utf-8").read()
assert ".home-layout" not in s, "Phase 3 styles already present"
BLOCK = r'''
/* ===========================================================
   Phase 3: Home flows — toolbar, list view, right rail, dialogs
   =========================================================== */

/* Layout: list + optional right rail (rail drops below the list under 1280px) */
.home-layout { display: grid; gap: 24px; grid-template-columns: minmax(0, 1fr); align-items: start; }
@media (min-width: 1280px) { .home-layout.has-rail { grid-template-columns: minmax(0, 1fr) 320px; } }
.home-rail { display: flex; flex-direction: column; gap: 16px; }
.home-rail:empty { display: none; }

/* Grid / list toggle */
.view-toggle { display: inline-flex; gap: 2px; padding: 3px; background: var(--bg-sunken); border-radius: var(--radius-sm); }
.view-btn {
  width: 34px; height: 30px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid transparent; border-radius: 4px; background: transparent; color: var(--text-muted);
}
.view-btn:hover { color: var(--text); }
.view-btn.active { background: var(--bg-elevated); color: var(--text); border-color: var(--border-strong); }

/* The main column is a size container: tables and the toolbar adapt to the space actually available
   next to the right rail, not to the window width. */
.home-main { min-width: 0; container-type: inline-size; container-name: homemain; }

/* Toolbar: search + sort on the first row, status chips below; one row when there is room */
.home-toolbar {
  display: grid; align-items: center; gap: 12px 16px; margin-bottom: 16px;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas: "search sort" "filters filters";
}
@container homemain (min-width: 860px) {
  .home-toolbar { grid-template-columns: minmax(200px, 300px) 1fr auto; grid-template-areas: "search filters sort"; }
}
.home-search { grid-area: search; position: relative; max-width: 360px; }
.home-search .icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-faint); pointer-events: none; }
.home-search input {
  width: 100%; min-height: 36px; padding: 0 12px 0 32px;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
  background: var(--bg-elevated); color: var(--text); font-size: 14px;
}
.home-search input:focus { border-color: var(--accent); }
.home-toolbar .filter-bar { grid-area: filters; margin: 0; }
.home-toolbar .chip-filter { min-height: 32px; }
.chip-count { margin-left: 2px; font-variant-numeric: tabular-nums; opacity: 0.8; }
.home-sort { grid-area: sort; display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); }
.home-sort .select-filter { min-height: 36px; border-radius: var(--radius-sm); border-color: var(--border-strong); }

/* List view */
.table-wrap { background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.rtable { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; }
.rtable th {
  height: 40px; padding: 0 16px; text-align: left; white-space: nowrap;
  font-size: 13px; font-weight: 500; color: var(--text-muted); background: var(--bg-sunken);
}
.rtable thead th:first-child { border-top-left-radius: calc(var(--radius-md) - 1px); }
.rtable thead th:last-child { border-top-right-radius: calc(var(--radius-md) - 1px); }
.rtable td { padding: 12px 16px; border-top: 1px solid var(--border); vertical-align: middle; }
.rt-row { cursor: pointer; }
.rt-row:hover { background: var(--bg-sunken); }
.th-btn { display: inline-flex; align-items: center; gap: 4px; min-height: 28px; padding: 0; border: 0; background: none; font: inherit; color: inherit; cursor: pointer; }
.th-btn:hover { color: var(--text); }
.th-arrow { display: inline-flex; }
.th-arrow.is-asc { transform: rotate(180deg); }
.rt-name-cell { width: 100%; max-width: 0; }   /* lets the name column absorb leftover width and truncate */
.rt-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.rt-desc { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-muted); }
.rt-progress { min-width: 160px; }
.rt-progress .strip { margin-bottom: 4px; }
.rt-pct { font-size: 12px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.col-month, .col-activity { white-space: nowrap; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.rt-actions { white-space: nowrap; text-align: right; }
.rt-actions > * { display: inline-flex; vertical-align: middle; }
.rt-actions .rc-menu { margin: 0 0 0 4px; }
@container homemain (max-width: 899px) { .col-month { display: none; } }
@container homemain (max-width: 679px) { .col-type { display: none; } }
/* Narrow column (phones): each row becomes a small card — name and progress on the left, action on the right.
   Sorting then uses the "Sort by" control above, since the header row is hidden. */
@container homemain (max-width: 559px) {
  .rtable, .rtable tbody { display: block; }
  .rtable thead { display: none; }
  .rtable .rt-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px 12px; padding: 14px 16px; border-top: 1px solid var(--border); }
  .rtable .rt-row:first-child { border-top: 0; }
  .rtable td { display: block; padding: 0; border: 0; }
  .rtable .rt-name-cell { grid-column: 1; width: auto; max-width: none; }
  .rtable .rt-progress { grid-column: 1; min-width: 0; }
  .rtable .rt-actions { grid-column: 2; grid-row: 1 / span 2; align-self: center; }
  .rtable .col-type, .rtable .col-month, .rtable .col-activity, .rt-desc { display: none; }
}

.empty-panel-sm { margin: 24px auto; padding: 24px; }

/* Right rail */
.rail-card { padding: 20px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.rail-title { margin: 0 0 4px; font-size: 15px; line-height: 22px; }
.rail-sub { margin: 0 0 12px; font-size: 13px; color: var(--text-muted); overflow-wrap: anywhere; }
.rail-main { margin: 0 0 4px; font-weight: 600; overflow-wrap: anywhere; }
.rail-week { margin: 0 0 16px; font-size: 13px; color: var(--text-muted); }
.rail-card .btn { margin-top: 4px; }
.rail-list { list-style: none; margin: 0 0 12px; padding: 0; display: flex; flex-direction: column; gap: 10px; font-size: 14px; }
.rail-list li { display: flex; align-items: center; gap: 10px; color: var(--text); }
.rail-list li.is-done { color: var(--text-muted); }
.rail-list li.is-done .icon { color: var(--status-completed); }
.rail-dot { flex-shrink: 0; width: 14px; height: 14px; margin: 1px; border: 1.5px solid var(--text-faint); border-radius: 50%; }

/* New roadmap and delete dialogs */
.modal:has(#createRoadmapForm) { max-width: 560px; }
.modal:has(#deleteRoadmapForm) { max-width: 440px; }
.option-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
.option-row {
  display: flex; align-items: flex-start; gap: 12px; padding: 12px 14px; cursor: pointer;
  border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--bg-elevated);
}
.option-row:hover { border-color: var(--text-faint); }
.option-row.is-selected { border-color: var(--accent); background: var(--accent-soft); }
.option-row.is-disabled { cursor: not-allowed; background: var(--bg-sunken); }
.option-row.is-disabled .option-title { color: var(--text-muted); }
.option-row:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
.option-row input { margin-top: 3px; accent-color: var(--accent); }
.option-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.option-title { font-weight: 600; }
.option-desc { font-size: 13px; color: var(--text-muted); }
.option-row.is-disabled .option-desc { color: var(--text-faint); }
.badge-soon { margin-left: 6px; background: var(--accent-soft); color: var(--accent); }
.dialog-text { margin: 0 0 16px; color: var(--text-muted); line-height: 1.5; }
'''
open(P, "w", encoding="utf-8").write(s.rstrip("\n") + "\n" + BLOCK)
print("js/theme-boot.js and css/home.css updated")
```

## Appendix B2 — `step3_appjs.py` (Task 3)

Run from the repo root: `python3 step3_appjs.py`. The new JavaScript is embedded in this script.

```python
"""Phase 3 / js/app.js: Home toolbar, list view, right rail, New roadmap dialog, typed-name delete,
modal focus handling. Run from the repo root: python3 step3_appjs.py"""
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


# 1. Home: preferences, filter/sort, cards, table, toolbar, right rail, renderDashboard
NEW_HOME = r'''  // ----- Home: saved preferences, filter, sort -----
  const HOME_PREFS_KEY = "roadmap-dashboard:home";
  const GETTING_STARTED_KEY = "roadmap-dashboard:getting-started";
  const SORT_DEFAULT_DIR = { recent: "desc", name: "asc", progress: "desc" };
  const STATUS_FILTERS = [["all", "All"], ["in_progress", "In progress"], ["not_started", "Not started"], ["completed", "Completed"]];
  // View and sort are remembered; filter and search are not.
  const homeState = { view: "grid", sortKey: "recent", sortDir: "desc", filter: "all", search: "" };

  function loadHomePrefs() {
    try {
      const saved = JSON.parse(localStorage.getItem(HOME_PREFS_KEY) || "null");
      if (!saved) return;
      if (saved.view === "grid" || saved.view === "list") homeState.view = saved.view;
      if (SORT_DEFAULT_DIR[saved.sortKey]) {
        homeState.sortKey = saved.sortKey;
        homeState.sortDir = saved.sortDir === "asc" || saved.sortDir === "desc" ? saved.sortDir : SORT_DEFAULT_DIR[saved.sortKey];
      }
    } catch { /* storage blocked or unreadable: keep the defaults */ }
  }
  function saveHomePrefs() {
    try {
      localStorage.setItem(HOME_PREFS_KEY, JSON.stringify({ view: homeState.view, sortKey: homeState.sortKey, sortDir: homeState.sortDir }));
    } catch { /* storage blocked: preferences last for this visit only */ }
  }

  // not_started | in_progress | completed, from the server-side stats.
  function roadmapState(r) {
    const s = r.stats;
    if (!s || !s.total) return "not_started";
    if (s.completed === s.total) return "completed";
    return s.completed + s.inProgress + s.blocked > 0 ? "in_progress" : "not_started";
  }
  // Does deleting this roadmap throw away real work? (Notes or dates on an otherwise untouched roadmap do not count.)
  function roadmapHasProgress(r) {
    const s = r.stats;
    if (!s) return false;
    return s.completed + s.inProgress + s.blocked > 0 || (r.source !== BUILTIN_SOURCE && s.total > 0);
  }

  function sortRoadmaps(list) {
    const dir = homeState.sortDir === "asc" ? 1 : -1;
    const time = (r) => (r.lastActivityAt ? Date.parse(r.lastActivityAt) : -Infinity);
    const compare = {
      recent: (a, b) => {
        const ta = time(a);
        const tb = time(b);
        if (ta === tb) return a.id - b.id;
        return ta < tb ? -1 : 1;
      },
      name: (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }) || a.id - b.id,
      progress: (a, b) => (pctOf(a.stats) - pctOf(b.stats))
        || ((a.stats ? a.stats.completed : 0) - (b.stats ? b.stats.completed : 0)) || a.id - b.id,
    }[homeState.sortKey];
    return list.slice().sort((a, b) => dir * compare(a, b));
  }

  function visibleRoadmaps() {
    const q = homeState.search.trim().toLowerCase();
    return sortRoadmaps(dashboardRoadmaps.filter((r) => (
      (homeState.filter === "all" || roadmapState(r) === homeState.filter)
      && (!q || r.name.toLowerCase().includes(q) || (r.description || "").toLowerCase().includes(q))
    )));
  }

  // ----- Home: cards and table -----
  function roadmapMenu(r) {
    return `
      <div class="rc-menu">
        <button type="button" class="btn btn-ghost btn-icon btn-sm" data-menu-trigger aria-expanded="false"
                aria-label="More actions for ${esc(r.name)}">${window.Icons.svg("more-horizontal", { size: 18 })}</button>
        <div class="rc-menu-panel hidden" role="group" aria-label="Actions for ${esc(r.name)}">
          <button type="button" class="profile-action-btn danger" data-action="delete-roadmap" data-id="${r.id}">Delete roadmap…</button>
        </div>
      </div>`;
  }

  function roadmapCard(r, animate) {
    const s = r.stats;
    const builtin = r.source === BUILTIN_SOURCE;
    const progressBlock = !s ? "" : `
      <div class="rc-progress">
        ${window.MonthStrip.html(stripMonths(s), { size: "md", animate })}
        <p class="rc-meta">
          <span>${s.total ? `<strong>${pctOf(s)}%</strong> complete · ${s.completed} of ${s.total} tasks` : "No months yet. Add one to start."}</span>
          <span>${esc(monthPosition(s))}</span>
        </p>
      </div>`;
    return `
      <article class="roadmap-card" data-id="${r.id}">
        <div class="rc-head">
          <h2 class="rc-title">${esc(r.name)}</h2>
          <span class="badge rc-badge">${builtin ? "Built-in" : "Custom"}</span>
          ${roadmapMenu(r)}
        </div>
        ${r.description ? `<p class="roadmap-card-desc">${esc(r.description)}</p>` : `<p class="roadmap-card-desc"></p>`}
        ${progressBlock}
        <div class="rc-foot">
          <p class="roadmap-card-meta">${esc(describeActivity(r.lastActivityAt))}</p>
          <button type="button" class="btn btn-primary" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
        </div>
      </article>`;
  }

  function activityShort(iso) {
    if (!iso) return "Not started yet";
    const days = daysBetween(new Date(iso), new Date());
    if (days <= 0) return "Today";
    if (days === 1) return "Yesterday";
    return days + " days ago";
  }

  function sortHeader(key, label) {
    const active = homeState.sortKey === key;
    const aria = active ? (homeState.sortDir === "asc" ? "ascending" : "descending") : "none";
    const arrow = active
      ? `<span class="th-arrow${homeState.sortDir === "asc" ? " is-asc" : ""}">${window.Icons.svg("chevron-down", { size: 14 })}</span>` : "";
    return `<th scope="col" aria-sort="${aria}"><button type="button" class="th-btn" data-action="sort-by" data-value="${key}">${label}${arrow}</button></th>`;
  }

  function roadmapTable(list) {
    const rows = list.map((r) => {
      const s = r.stats;
      return `
        <tr class="rt-row" data-id="${r.id}">
          <td class="rt-name-cell">
            <div class="rt-name">${esc(r.name)}</div>
            ${r.description ? `<div class="rt-desc">${esc(r.description)}</div>` : ""}
          </td>
          <td class="col-type"><span class="badge rc-badge">${r.source === BUILTIN_SOURCE ? "Built-in" : "Custom"}</span></td>
          <td class="rt-progress">
            ${s ? `${window.MonthStrip.html(stripMonths(s), { size: "sm" })}<span class="rt-pct">${s.total ? pctOf(s) + "%" : "No months"}</span>` : ""}
          </td>
          <td class="col-month">${esc(monthPosition(s)) || "—"}</td>
          <td class="col-activity">${esc(activityShort(r.lastActivityAt))}</td>
          <td class="rt-actions">
            <button type="button" class="btn btn-primary btn-sm" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
            ${roadmapMenu(r)}
          </td>
        </tr>`;
    }).join("");
    return `
      <div class="table-wrap">
        <table class="rtable">
          <thead><tr>
            ${sortHeader("name", "Roadmap")}
            <th scope="col" class="col-type">Type</th>
            ${sortHeader("progress", "Progress")}
            <th scope="col" class="col-month">Current month</th>
            ${sortHeader("recent", "Last activity")}
            <th scope="col"><span class="sr-only">Actions</span></th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function summaryBar(roadmaps) {
    const all = roadmaps.map((r) => r.stats).filter(Boolean);
    const sum = (key) => all.reduce((n, s) => n + s[key], 0);
    const total = sum("total");
    const done = sum("completed");
    const pct = total ? Math.round((done / total) * 100) : 0;
    return `
      <section class="summary-bar" aria-label="Summary">
        <div class="summary-item"><p class="summary-label">Roadmaps</p><p class="summary-value">${roadmaps.length}</p></div>
        <div class="summary-item"><p class="summary-label">Tasks done</p><p class="summary-value">${done} <small>/ ${total}</small></p></div>
        <div class="summary-item"><p class="summary-label">Overall progress</p><p class="summary-value">${pct}%</p></div>
        <div class="summary-item"><p class="summary-label">Done this week</p><p class="summary-value">${sum("completedLast7Days")}</p></div>
      </section>`;
  }

  // ----- Home: toolbar, view toggle -----
  function viewToggle() {
    const button = (value, icon, label) => `
      <button type="button" class="view-btn" data-action="set-view" data-value="${value}" aria-pressed="false"
              aria-label="${label}" title="${label}">${window.Icons.svg(icon, { size: 16 })}</button>`;
    return `<div class="view-toggle" role="group" aria-label="Layout">${button("grid", "layout-grid", "Grid view")}${button("list", "list", "List view")}</div>`;
  }

  function homeToolbar() {
    return `
      <div class="home-toolbar">
        <div class="home-search">
          ${window.Icons.svg("search", { size: 16 })}
          <input type="search" id="homeSearch" placeholder="Search roadmaps" aria-label="Search roadmaps" autocomplete="off" value="${esc(homeState.search)}" />
        </div>
        <div id="homeFilters" class="filter-bar" role="group" aria-label="Filter by status"></div>
        <div class="home-sort">
          <label for="homeSort">Sort by</label>
          <select id="homeSort" class="select-filter">
            <option value="recent">Recent activity</option>
            <option value="name">Name</option>
            <option value="progress">Progress</option>
          </select>
        </div>
      </div>`;
  }

  // Redraws only what filtering/sorting changes, so the search box keeps focus while typing.
  function renderHomeResults(animate) {
    const host = $("homeResults");
    if (!host) return;
    const multi = dashboardRoadmaps.length >= 2;
    const list = multi ? visibleRoadmaps() : dashboardRoadmaps.slice();
    const view = multi ? homeState.view : "grid";

    document.querySelectorAll(".view-btn").forEach((btn) => {
      const on = btn.dataset.value === view;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    });
    const filters = $("homeFilters");
    if (filters) {
      const counts = { all: dashboardRoadmaps.length, in_progress: 0, not_started: 0, completed: 0 };
      dashboardRoadmaps.forEach((r) => { counts[roadmapState(r)] += 1; });
      filters.innerHTML = STATUS_FILTERS.map(([value, label]) => `
        <button type="button" class="chip-filter${homeState.filter === value ? " active" : ""}" data-action="filter-status"
                data-value="${value}" aria-pressed="${homeState.filter === value}">${label} <span class="chip-count">${counts[value]}</span></button>`).join("");
    }
    if ($("homeSort")) $("homeSort").value = homeState.sortKey;

    if (!list.length) {
      const q = homeState.search.trim();
      host.innerHTML = `
        <div class="empty-panel empty-panel-sm">
          <h2>${q ? `No roadmaps match “${esc(q)}”.` : "No roadmaps in this view."}</h2>
          <button type="button" class="btn" data-action="clear-filters">${q && homeState.filter === "all" ? "Clear search" : "Clear filters"}</button>
        </div>`;
    } else if (view === "list") {
      host.innerHTML = roadmapTable(list);
    } else {
      host.innerHTML = `<div class="roadmap-grid">${list.map((r) => roadmapCard(r, animate)).join("")}</div>`;
    }
    const count = $("homeResultCount");
    if (count) count.textContent = `${list.length} ${list.length === 1 ? "roadmap" : "roadmaps"} shown`;
  }

  // ----- Home: right-hand rail (Current focus, Getting started) -----
  function focusRoadmap() {
    const withMonths = dashboardRoadmaps.filter((r) => r.stats && r.stats.months.length);
    if (!withMonths.length) return null;
    const active = withMonths.filter((r) => r.lastActivityAt)
      .sort((a, b) => Date.parse(b.lastActivityAt) - Date.parse(a.lastActivityAt));
    return active[0] || withMonths[0];
  }

  // The built-in roadmap's weekly sections follow 7-day blocks from the start of each month (days 1-28).
  function builtinWeekFocus(monthIndex) {
    const week = Math.floor((TODAY.getDate() - 1) / 7);
    const phase = BUILTIN_DATA.phases[monthIndex];
    if (week > 3 || !phase) return "";
    const section = phase.sections.find((s) => s.type === "week" && s.weekNumber && (s.weekNumber - 1) % 4 === week);
    return section ? section.title : "";
  }

  function focusCard() {
    const r = focusRoadmap();
    if (!r) return "";
    const s = r.stats;
    const idx = currentMonthIndex(s.startMonth, s.months.length);
    let main;
    let week = "";
    if (idx >= 0) {
      main = `Month ${s.months[idx].number}: ${s.months[idx].title || "Untitled"}`;
      if (r.source === BUILTIN_SOURCE) week = builtinWeekFocus(idx);
    } else {
      const start = monthKeyOffset(s.startMonth, 0);
      main = TODAY < start
        ? `Starts ${start.toLocaleDateString(undefined, { month: "long", year: "numeric" })}`
        : "The planned months have passed.";
    }
    return `
      <section class="rail-card" aria-labelledby="focusHeading">
        <h2 class="rail-title" id="focusHeading">Current focus</h2>
        <p class="rail-sub">${esc(r.name)}</p>
        <p class="rail-main">${esc(main)}</p>
        ${week ? `<p class="rail-week">${esc(week)}</p>` : ""}
        <button type="button" class="btn btn-primary btn-sm" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
      </section>`;
  }

  function gettingStartedItems() {
    const custom = dashboardRoadmaps.filter((r) => r.source !== BUILTIN_SOURCE);
    return [
      ["Complete your first task", dashboardRoadmaps.some((r) => r.stats && r.stats.completed > 0)],
      ["Create a custom roadmap", custom.length > 0],
      ["Add a month to your roadmap", custom.some((r) => r.stats && r.stats.months.length > 0)],
      ["Choose an appearance", window.Theme.isSaved()],
    ];
  }

  function gettingStartedCard() {
    let dismissed = false;
    try { dismissed = localStorage.getItem(GETTING_STARTED_KEY) === "dismissed"; } catch { /* storage blocked */ }
    const items = gettingStartedItems();
    const done = items.filter(([, ok]) => ok).length;
    if (dismissed || done === items.length) return "";
    return `
      <section class="rail-card" aria-labelledby="startedHeading">
        <h2 class="rail-title" id="startedHeading">Getting started</h2>
        <p class="rail-sub">${done} of ${items.length} done</p>
        <ul class="rail-list">
          ${items.map(([label, ok]) => `<li class="${ok ? "is-done" : ""}">${ok ? window.Icons.svg("check-circle", { size: 16 }) : '<span class="rail-dot" aria-hidden="true"></span>'}<span>${esc(label)}${ok ? '<span class="sr-only"> (done)</span>' : ""}</span></li>`).join("")}
        </ul>
        <button type="button" class="btn btn-ghost btn-sm" data-action="dismiss-getting-started">Dismiss</button>
      </section>`;
  }

  function homeRailHtml() {
    return focusCard() + gettingStartedCard();
  }

  function renderDashboard(roadmaps) {
    dashboardRoadmaps = roadmaps;
    renderSidebarRoadmaps();
    if (roadmaps.length < 2) { homeState.filter = "all"; homeState.search = ""; }
    const hasBuiltin = roadmaps.some((r) => r.source === BUILTIN_SOURCE);
    const atLimit = roadmaps.length >= MAX_ROADMAPS;
    const newBtn = `
      <button type="button" class="btn btn-primary" data-action="create-roadmap" ${atLimit ? `disabled title="You've reached the limit of ${MAX_ROADMAPS} roadmaps."` : ""}>
        ${window.Icons.svg("plus", { size: 16 })} New roadmap
      </button>`;

    if (roadmaps.length === 0) {
      $("dashboardContent").innerHTML = `
        <div class="page-head"><div><h1 class="page-title">Roadmaps</h1></div></div>
        <div class="empty-panel">
          <h2>No roadmaps yet</h2>
          <p>Start with the AI Engineer roadmap or build your own plan.</p>
          <div class="page-actions">
            <button type="button" class="btn btn-primary" data-action="restore-builtin">Restore AI Engineer roadmap</button>
            <button type="button" class="btn" data-action="create-roadmap">Blank roadmap</button>
          </div>
        </div>`;
      return;
    }

    const restore = hasBuiltin ? "" : `
      <div class="notice-row">
        <span>The AI Engineer roadmap isn't in your account. You can bring it back with fresh progress.</span>
        <button type="button" class="btn btn-sm" data-action="restore-builtin">Restore AI Engineer roadmap</button>
      </div>`;
    const animate = !stripsAnimated;
    stripsAnimated = true;
    const multi = roadmaps.length >= 2;
    const rail = homeRailHtml();

    $("dashboardContent").innerHTML = `
      <div class="page-head">
        <div>
          <h1 class="page-title">Roadmaps</h1>
          <p class="page-lead">Track progress across your plans.</p>
        </div>
        <div class="page-actions">${multi ? viewToggle() : ""}${newBtn}</div>
      </div>
      ${restore}
      <div class="home-layout${rail ? " has-rail" : ""}" id="homeLayout">
        <div class="home-main">
          ${summaryBar(roadmaps)}
          ${multi ? homeToolbar() : ""}
          <p id="homeResultCount" class="sr-only" role="status"></p>
          <div id="homeResults"></div>
        </div>
        <aside class="home-rail" id="homeRail" aria-label="Focus and tips">${rail}</aside>
      </div>`;
    renderHomeResults(animate);
  }

'''
swap_block("  function roadmapCard(r, animate) {", "  // Sidebar quick-switcher (Home only)", NEW_HOME)

# 2. Click / input / change handling for Home
NEW_CLICK = r'''  function onDashboardClick(e) {
    const trigger = e.target.closest("[data-menu-trigger]");
    if (trigger) { e.stopPropagation(); toggleCardMenu(trigger); return; }
    const el = e.target.closest("[data-action]");
    if (!el) {
      // A click on the card or table row itself (not on one of its buttons) opens it.
      const row = e.target.closest(".roadmap-card[data-id], .rt-row[data-id]");
      if (row && !e.target.closest("button, a, .rc-menu")) openRoadmap(Number(row.dataset.id));
      return;
    }
    closeCardMenus();
    switch (el.dataset.action) {
      case "open-roadmap": openRoadmap(Number(el.dataset.id)); break;
      case "delete-roadmap": confirmDeleteRoadmap(el.dataset.id); break;
      case "restore-builtin": restoreBuiltinRoadmap(); break;
      case "create-roadmap": openCreateRoadmapModal(); break;
      case "retry-dashboard": showDashboard(); break;
      case "filter-status":
        homeState.filter = el.dataset.value;
        renderHomeResults(false);
        break;
      case "set-view":
        homeState.view = el.dataset.value;
        saveHomePrefs();
        renderHomeResults(false);
        break;
      case "sort-by": {
        const key = el.dataset.value;
        homeState.sortDir = homeState.sortKey === key
          ? (homeState.sortDir === "asc" ? "desc" : "asc") : SORT_DEFAULT_DIR[key];
        homeState.sortKey = key;
        saveHomePrefs();
        renderHomeResults(false);
        break;
      }
      case "clear-filters":
        homeState.filter = "all";
        homeState.search = "";
        if ($("homeSearch")) $("homeSearch").value = "";
        renderHomeResults(false);
        break;
      case "dismiss-getting-started":
        try { localStorage.setItem(GETTING_STARTED_KEY, "dismissed"); } catch { /* storage blocked */ }
        $("homeRail").innerHTML = homeRailHtml();
        if (!$("homeRail").innerHTML.trim()) $("homeLayout").classList.remove("has-rail");
        break;
      default: break;
    }
  }

  function onDashboardInput(e) {
    if (e.target.id !== "homeSearch") return;
    homeState.search = e.target.value;
    renderHomeResults(false);
  }
  function onDashboardChange(e) {
    if (e.target.id !== "homeSort") return;
    homeState.sortKey = e.target.value;
    homeState.sortDir = SORT_DEFAULT_DIR[e.target.value];
    saveHomePrefs();
    renderHomeResults(false);
  }

'''
swap_block("  function onDashboardClick(e) {", "  function handleSessionExpired() {", NEW_CLICK)

# 3. New roadmap dialog, create submit, delete confirmation (typed name when there is progress)
NEW_DIALOGS = r'''  function openCreateRoadmapModal() {
    const thisMonth = currentMonthKey();
    const hasBuiltin = dashboardRoadmaps.some((r) => r.source === BUILTIN_SOURCE);
    $("modalHost").querySelector(".modal").innerHTML = `
      <h2>New roadmap</h2>
      <form id="createRoadmapForm" novalidate>
        <div class="option-list" role="radiogroup" aria-label="How do you want to start?">
          <label class="option-row is-selected">
            <input type="radio" name="newRoadmapKind" value="blank" checked />
            <span class="option-body">
              <span class="option-title">Blank roadmap</span>
              <span class="option-desc">Build your own plan with months, sections, topics and tasks.</span>
            </span>
          </label>
          <label class="option-row${hasBuiltin ? " is-disabled" : ""}">
            <input type="radio" name="newRoadmapKind" value="builtin" ${hasBuiltin ? "disabled" : ""} />
            <span class="option-body">
              <span class="option-title">AI Engineer roadmap</span>
              <span class="option-desc">${hasBuiltin ? "You already have this roadmap." : "The 10-month Production AI Engineer plan, restored with fresh progress."}</span>
            </span>
          </label>
          <label class="option-row is-disabled" title="Coming soon: describe a goal and let AI draft the plan.">
            <input type="radio" name="newRoadmapKind" value="ai" disabled />
            <span class="option-body">
              <span class="option-title">Describe a goal (AI) <span class="badge badge-soon">Soon</span></span>
              <span class="option-desc">Describe a goal and let AI draft the plan.</span>
            </span>
          </label>
        </div>

        <div id="newBlankFields">
          <div class="field">
            <label for="newRoadmapName">Roadmap name</label>
            <input type="text" id="newRoadmapName" maxlength="80" autocomplete="off" placeholder="e.g. Learn Rust in 12 weeks" />
          </div>
          <div class="field">
            <label for="newRoadmapDesc">Description (optional)</label>
            <textarea id="newRoadmapDesc" maxlength="300" placeholder="What is this plan for?" aria-describedby="newRoadmapCount"></textarea>
            <p class="field-hint" id="newRoadmapCount">0 / 300</p>
          </div>
          <div class="field">
            <label for="newRoadmapStart">Month 1 starts in</label>
            <input type="month" id="newRoadmapStart" value="${esc(thisMonth)}" min="${esc(thisMonth)}" />
          </div>
        </div>
        <p id="createRoadmapError" class="auth-error" role="alert"></p>
        <div class="modal-actions">
          <button type="button" class="btn" data-action="close-modal">Cancel</button>
          <button type="submit" class="btn btn-primary" id="createRoadmapSubmit">Create roadmap</button>
        </div>
      </form>`;
    showModal();
    $("newRoadmapName").focus();
  }

  // Show the blank-roadmap fields only for "Blank roadmap"; relabel the button for "AI Engineer roadmap".
  function syncCreateKind() {
    const checked = document.querySelector('input[name="newRoadmapKind"]:checked');
    const kind = checked ? checked.value : "blank";
    document.querySelectorAll(".option-row").forEach((row) => {
      row.classList.toggle("is-selected", !!row.querySelector("input:checked"));
    });
    $("newBlankFields").classList.toggle("hidden", kind !== "blank");
    $("createRoadmapSubmit").textContent = kind === "builtin" ? "Restore roadmap" : "Create roadmap";
    $("createRoadmapError").textContent = "";
  }

  async function submitCreateRoadmap() {
    const checked = document.querySelector('input[name="newRoadmapKind"]:checked');
    if (checked && checked.value === "builtin") { closeModal(); restoreBuiltinRoadmap(); return; }
    const error = $("createRoadmapError");
    const name = $("newRoadmapName").value.trim();
    const startMonth = $("newRoadmapStart").value;
    error.textContent = "";
    if (!name) { error.textContent = "Give your roadmap a name."; $("newRoadmapName").focus(); return; }
    if (startMonth && startMonth < currentMonthKey()) {
      error.textContent = "Start month can't be before the current month.";
      return;
    }
    const submit = $("createRoadmapSubmit");
    submit.disabled = true;
    try {
      const res = await window.RoadmapApi.create({
        name,
        description: $("newRoadmapDesc").value.trim(),
        startMonth: startMonth || undefined,
      });
      closeModal();
      openRoadmap(res.roadmap.id);
    } catch (e) {
      if (e.status === 401) { handleSessionExpired(); return; }
      error.textContent = e.message;
      submit.disabled = false;
    }
  }

  function confirmDeleteRoadmap(id) {
    const roadmap = dashboardRoadmaps.find((r) => String(r.id) === String(id));
    if (!roadmap) return;
    const needsName = roadmapHasProgress(roadmap);
    const s = roadmap.stats;
    const trigger = document.querySelector(
      `.roadmap-card[data-id="${roadmap.id}"] [data-menu-trigger], .rt-row[data-id="${roadmap.id}"] [data-menu-trigger]`,
    );
    $("modalHost").querySelector(".modal").innerHTML = `
      <h2>Delete “${esc(roadmap.name)}”?</h2>
      <form id="deleteRoadmapForm" novalidate>
        <p class="dialog-text">
          This permanently deletes the roadmap and all of its progress: statuses, notes, links, due dates
          and anything you added. This can't be undone.${s && s.completed > 0 ? ` You have completed ${s.completed} of ${s.total} tasks.` : ""}
        </p>
        ${needsName ? `
          <div class="field">
            <label for="deleteConfirmName">Type the roadmap name to confirm</label>
            <input type="text" id="deleteConfirmName" autocomplete="off" spellcheck="false" data-name="${esc(roadmap.name)}" />
            <p class="field-hint">Type exactly: <strong>${esc(roadmap.name)}</strong></p>
          </div>` : ""}
        <div class="modal-actions">
          <button type="button" class="btn" data-action="close-modal" id="deleteCancelBtn">Cancel</button>
          <button type="button" class="btn btn-danger" data-action="confirm-delete-roadmap" data-id="${roadmap.id}"
                  id="deleteConfirmBtn" ${needsName ? "disabled" : ""}>Delete roadmap</button>
        </div>
      </form>`;
    showModal(trigger);
    $("deleteCancelBtn").focus();
  }

'''
swap_block("  function openCreateRoadmapModal() {", "  async function deleteRoadmap(id) {", NEW_DIALOGS)

# 4. Shared modal behaviour: remember where focus was, give the dialog its title as its name,
#    restore focus on close; (Escape and the Tab trap are wired below)
once("""  function closeModal() {
    document.getElementById("modalHost").classList.add("hidden");
  }""", """  // Dialogs opened with showModal() return focus to what opened them when they close.
  let modalReturnFocus = null;
  function showModal(returnFocus) {
    const host = document.getElementById("modalHost");
    const modal = host.querySelector(".modal");
    modalReturnFocus = returnFocus || document.activeElement;
    const title = modal.querySelector("h2");
    if (title) { title.id = "modalTitle"; modal.setAttribute("aria-labelledby", "modalTitle"); }
    else modal.removeAttribute("aria-labelledby");
    host.classList.remove("hidden");
  }
  function closeModal() {
    const host = document.getElementById("modalHost");
    if (host.classList.contains("hidden")) return;
    host.classList.add("hidden");
    const back = modalReturnFocus;
    modalReturnFocus = null;
    if (back && back !== document.body && document.contains(back) && typeof back.focus === "function") back.focus();
  }
  // Keep Tab / Shift+Tab inside the open dialog.
  function trapModalFocus(e) {
    const focusable = [...document.querySelectorAll("#modalHost .modal a[href], #modalHost .modal button, #modalHost .modal input, #modalHost .modal select, #modalHost .modal textarea, #modalHost .modal [tabindex]")]
      .filter((el) => !el.disabled && el.tabIndex >= 0 && el.offsetParent !== null);
    if (!focusable.length) { e.preventDefault(); return; }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && (document.activeElement === first || !document.querySelector("#modalHost .modal").contains(document.activeElement))) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  }""")
once("""    host.classList.remove("hidden");
    $("aboutCloseBtn").focus();""", """    showModal();
    $("aboutCloseBtn").focus();""")

# 5. Event wiring
once("""    $("modalHost").addEventListener("submit", (e) => {
      if (e.target.id !== "createRoadmapForm") return;
      e.preventDefault();
      submitCreateRoadmap();
    });""", """    $("modalHost").addEventListener("submit", (e) => {
      if (e.target.id === "createRoadmapForm") { e.preventDefault(); submitCreateRoadmap(); }
      if (e.target.id === "deleteRoadmapForm") { // Enter in the name box
        e.preventDefault();
        const confirmBtn = $("deleteConfirmBtn");
        if (!confirmBtn.disabled) deleteRoadmap(Number(confirmBtn.dataset.id));
      }
    });
    $("modalHost").addEventListener("input", (e) => {
      if (e.target.id === "newRoadmapDesc") $("newRoadmapCount").textContent = `${e.target.value.length} / 300`;
      if (e.target.id === "deleteConfirmName") $("deleteConfirmBtn").disabled = e.target.value.trim() !== e.target.dataset.name;
    });
    $("modalHost").addEventListener("change", (e) => {
      if (e.target.name === "newRoadmapKind") syncCreateKind();
    });
    // Escape closes the open dialog; Tab stays inside it.
    document.addEventListener("keydown", (e) => {
      if ($("modalHost").classList.contains("hidden")) return;
      if (e.key === "Escape") { e.preventDefault(); closeModal(); }
      else if (e.key === "Tab") trapModalFocus(e);
    });""")
once("""    $("dashboardContent").addEventListener("click", onDashboardClick);""",
     """    $("dashboardContent").addEventListener("click", onDashboardClick);
    $("dashboardContent").addEventListener("input", onDashboardInput);
    $("dashboardContent").addEventListener("change", onDashboardChange);""")
once("    initSidebar();\n", "    initSidebar();\n    loadHomePrefs();\n")

open(P, "w", encoding="utf-8").write(s)
for required in ("function loadHomePrefs", "function visibleRoadmaps", "function roadmapTable", "function renderHomeResults",
                 "function homeRailHtml", "function showModal", "function syncCreateKind", "function onDashboardInput"):
    assert s.count(required) == 1, f"{required}: expected exactly one definition, found {s.count(required)}"
assert s.count("function roadmapCard") == 1 and s.count("function summaryBar") == 1 and s.count("function renderDashboard") == 1
print("js/app.js updated")
```

## Appendix B3 — `step3_docs.py` (Task 4)

Run from the repo root: `python3 step3_docs.py`.

```python
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
```

## Appendix B4 — `patch_phase2_harness.py` (Task 5)

Run once against your copy of `verify_phase2.py` (kept outside the repo).

```python
"""Phase 3 / keep the Phase 2 harness runnable.
Phase 3 requires typing a roadmap's name before deleting one that has progress, so the Phase 2 harness must
type it too. Run once, next to verify_phase2.py:  python3 patch_phase2_harness.py /tmp/ui-verify/verify_phase2.py"""
import sys

path = sys.argv[1]
s = open(path, encoding="utf-8").read()
assert "def confirm_delete" not in s, "already patched"

HELPER = '''def confirm_delete(page):
    """Phase 3: roadmaps with progress need their name typed before Delete is enabled."""
    field = page.locator("#deleteConfirmName")
    if field.count():
        field.fill(field.get_attribute("data-name"))
    page.click("[data-action=confirm-delete-roadmap]")


'''
marker = "def home(page):"
assert s.count(marker) == 1
s = s.replace(marker, HELPER + marker)

old = 'page.click("[data-action=confirm-delete-roadmap]")'
n = s.count(old) - 1          # the helper itself contains one occurrence
assert n >= 3, f"expected at least 3 delete confirmations to patch, found {n}"
head, tail = s.split(HELPER, 1)
tail_head, rest = tail.split("def home(page):", 1)
rest = rest.replace(old, "confirm_delete(page)")
s = head + HELPER + tail_head + "def home(page):" + rest
open(path, "w", encoding="utf-8").write(s)
print(f"patched {n} delete confirmations in {path}")
```

## Appendix C1 — `verify_phase3.py` (verification harness; keep outside the repo)

Uses `serve-demo.js` from the Phase 0 spec (Appendix C1).

```python
"""Phase 3 verification. Usage:
    python3 verify_phase3.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Needs the demo server from the Phase 0 spec (serve-demo.js) running. Exit code 0 only if every check passes."""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots-p3"
os.makedirs(SHOTS, exist_ok=True)
RUN = int(time.time()) % 1000000
results, AXE_SOURCE = [], None


def check(ok, message):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + message)


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
    name = f"p3{tag}_{RUN}"
    r = ctx.request.post(BASE + "/api/auth/register", data={"firstName": "Rita", "lastName": "Route", "username": name, "password": "longenough1"})
    assert r.status == 201, r.status


def make_custom(ctx, name, description, done, total):
    """Create a custom roadmap with one month and `total` tasks, `done` of them completed."""
    rid = ctx.request.post(BASE + "/api/roadmaps", data={"name": name, "description": description}).json()["roadmap"]["id"]
    if total:
        tasks = [{"id": f"t{rid}-{i}", "title": f"Task {i}"} for i in range(total)]
        data = {"items": {t["id"]: {"status": "completed", "completedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} for t in tasks[:done]},
                "counters": {}, "celebratedPhases": [], "settings": {},
                "custom": {"topics": [{"id": f"tp{rid}", "sectionId": f"s{rid}", "title": "Topic", "depth": "D2", "tasks": tasks}],
                           "phases": [{"id": f"p{rid}", "title": "Focus month", "sections": [{"id": f"s{rid}", "title": "Week", "type": "week", "weekNumber": 1}]}]}}
        ver = ctx.request.get(BASE + f"/api/roadmaps/{rid}/progress").json()["version"]
        r = ctx.request.put(BASE + f"/api/roadmaps/{rid}/progress", data={"version": ver, "data": data})
        assert r.status == 200, r.status
    return rid


def home(page):
    page.goto(BASE)
    page.wait_for_selector(".summary-bar", timeout=10000)


def titles(page):
    return [t.strip() for t in page.locator("#homeResults .rc-title, #homeResults .rt-name").all_inner_texts()]


def chip_text(page, value):
    return " ".join(page.locator(f'.chip-filter[data-value="{value}"]').inner_text().split())


with sync_playwright() as p:
    browser = p.chromium.launch()

    # =============== A. One roadmap: no toolbar, rail present ===============
    ctx, page = new_context(browser)
    register(ctx, "a")
    home(page)
    check(page.locator("#homeSearch").count() == 0 and page.locator(".view-toggle").count() == 0, "one roadmap: no toolbar and no view toggle")
    check(page.locator(".home-rail .rail-card").count() == 2, "one roadmap: rail shows Current focus and Getting started")
    check(page.locator("#homeLayout.has-rail").count() == 1, "layout has the rail column")
    main_box = page.evaluate("(() => { const m = document.querySelector('.home-main').getBoundingClientRect(), r = document.querySelector('.home-rail').getBoundingClientRect(); return {mr: m.right, rl: r.left, rw: r.width, rt: r.top, mt: m.top}; })()")
    check(abs(main_box["rw"] - 320) <= 1 and main_box["rl"] >= main_box["mr"], f"desktop: rail is 320px wide, beside the list ({main_box['rw']:.0f}px)")
    gs = " ".join(page.locator("#startedHeading").locator("xpath=..").inner_text().split())
    check("0 of 4 done" in gs, "Getting started: new account shows 0 of 4 done")
    focus = " ".join(page.locator("#focusHeading").locator("xpath=..").inner_text().split())
    check("AI Engineer Roadmap" in focus and "Month" in focus or "Starts" in focus, "Current focus names the roadmap: " + focus[:80])
    page.set_viewport_size({"width": 1100, "height": 900}); page.wait_for_timeout(200)
    below = page.evaluate("(() => { const m = document.querySelector('.home-main').getBoundingClientRect(), r = document.querySelector('.home-rail').getBoundingClientRect(); return r.top >= m.bottom - 1; })()")
    check(below, "below 1280px the rail drops under the list")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(path=f"{SHOTS}/home-one-roadmap.png")
    audit(page, "Home with one roadmap and rail")

    # =============== B. New roadmap dialog ===============
    btn = page.locator("[data-action=create-roadmap]").first
    btn.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    modal = page.locator("#modalHost .modal")
    check(modal.get_attribute("role") == "dialog" and modal.get_attribute("aria-modal") == "true", "dialog has role=dialog and aria-modal")
    check(page.inner_text("#modalTitle") == "New roadmap" and modal.get_attribute("aria-labelledby") == "modalTitle", "dialog is named by its heading")
    radios = page.locator('input[name="newRoadmapKind"]')
    check(radios.count() == 3 and radios.nth(0).is_checked(), "three start options; Blank roadmap preselected")
    check(radios.nth(1).is_disabled() and "already have this roadmap" in page.inner_text("#modalHost .option-row >> nth=1"), "AI Engineer option disabled with 'You already have this roadmap.'")
    check(radios.nth(2).is_disabled() and page.locator(".badge-soon").inner_text() == "Soon", "AI option disabled and marked Soon")
    check(page.evaluate("document.activeElement.id") == "newRoadmapName", "focus starts in the name field")
    page.fill("#newRoadmapDesc", "hello")
    check(page.inner_text("#newRoadmapCount") == "5 / 300", "description counter updates: " + page.inner_text("#newRoadmapCount"))
    page.screenshot(path=f"{SHOTS}/dialog-new.png")
    audit(page, "New roadmap dialog")
    for _ in range(14):
        page.keyboard.press("Tab")
    inside = page.evaluate("document.getElementById('modalHost').querySelector('.modal').contains(document.activeElement)")
    check(inside, "Tab cycles inside the dialog (focus trap)")
    page.keyboard.press("Shift+Tab")
    check(page.evaluate("document.getElementById('modalHost').querySelector('.modal').contains(document.activeElement)"), "Shift+Tab stays inside too")
    page.fill("#newRoadmapName", ""); page.click("#createRoadmapSubmit")
    check(page.inner_text("#createRoadmapError") == "Give your roadmap a name." and page.locator("#modalHost.hidden").count() == 0, "empty name: error shown, dialog stays open")
    page.keyboard.press("Escape")
    check(page.locator("#modalHost.hidden").count() == 1, "Escape closes the dialog")
    check(page.evaluate("document.activeElement.getAttribute('data-action')") == "create-roadmap", "focus returns to the 'New roadmap' button")
    # create a real one (blank)
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    page.fill("#newRoadmapName", "Alpha"); page.fill("#newRoadmapDesc", "Alpha description"); page.click("#createRoadmapSubmit")
    page.wait_for_selector("#roadmapTitle"); page.locator("#crumbRoadmapName", has_text="Alpha").wait_for(timeout=8000)
    check(page.evaluate("location.hash").endswith("/overview"), "creating a blank roadmap opens it")
    page.click("#backToDashboardBtn"); page.wait_for_selector(".summary-bar")

    # =============== C. Several roadmaps: toolbar, filter, search, sort ===============
    make_custom(ctx, "Beta Plan", "Notes about a quokka diet", 2, 4)      # in progress, 50%
    make_custom(ctx, "Gamma", "All done here", 3, 3)                       # completed, 100%
    home(page)
    check(page.locator("#homeSearch").is_visible() and page.locator(".view-toggle").is_visible(), "2+ roadmaps: search, filters, sort and view toggle appear")
    check(chip_text(page, "all") == "All 4" and chip_text(page, "in_progress") == "In progress 1"
          and chip_text(page, "not_started") == "Not started 2" and chip_text(page, "completed") == "Completed 1", "filter chips show counts: " + " | ".join(chip_text(page, v) for v in ("all", "in_progress", "not_started", "completed")))
    check(page.locator("article.roadmap-card").count() == 4 and "4 roadmaps shown" in page.inner_text("#homeResultCount"), "all 4 cards shown; live count announced")
    page.click('.chip-filter[data-value="in_progress"]')
    check(titles(page) == ["Beta Plan"] and page.get_attribute('.chip-filter[data-value="in_progress"]', "aria-pressed") == "true", "filter In progress -> Beta Plan only")
    page.click('.chip-filter[data-value="completed"]'); check(titles(page) == ["Gamma"], "filter Completed -> Gamma only")
    page.click('.chip-filter[data-value="not_started"]'); check(sorted(titles(page)) == ["AI Engineer Roadmap", "Alpha"], "filter Not started -> AI Engineer + Alpha")
    page.click('.chip-filter[data-value="all"]')
    page.fill("#homeSearch", "gam"); check(titles(page) == ["Gamma"], "search by name ('gam')")
    check(page.evaluate("document.activeElement.id") == "homeSearch", "typing in search keeps focus in the box")
    page.fill("#homeSearch", "quokka"); check(titles(page) == ["Beta Plan"], "search also matches descriptions ('quokka')")
    page.fill("#homeSearch", "zzz")
    check("No roadmaps match" in page.inner_text("#homeResults") and "zzz" in page.inner_text("#homeResults"), "no match: message with the search text")
    page.screenshot(path=f"{SHOTS}/home-no-match.png")
    audit(page, "Home: no results state")
    page.click('[data-action="clear-filters"]')
    check(page.input_value("#homeSearch") == "" and len(titles(page)) == 4, "Clear search restores all roadmaps")
    page.click('.chip-filter[data-value="completed"]'); page.fill("#homeSearch", "beta")
    check("Clear filters" in page.inner_text("#homeResults"), "filter + search with no match offers 'Clear filters'")
    page.click('[data-action="clear-filters"]')
    page.select_option("#homeSort", "name")
    check(titles(page) == ["AI Engineer Roadmap", "Alpha", "Beta Plan", "Gamma"], "sort Name (A-Z): " + str(titles(page)))
    page.select_option("#homeSort", "progress")
    check(titles(page)[0] == "Gamma" and titles(page)[1] == "Beta Plan", "sort Progress (high first): " + str(titles(page)))

    # =============== D. List view ===============
    page.click('[data-action=set-view][data-value=list]')
    check(page.locator("table.rtable").count() == 1 and page.locator("tr.rt-row").count() == 4, "list view: table with 4 rows")
    check(page.get_attribute('[data-action=set-view][data-value=list]', "aria-pressed") == "true", "list toggle is pressed")
    ths = {t.inner_text().strip(): t.get_attribute("aria-sort") for t in page.locator("table.rtable thead th").all() if t.inner_text().strip()}
    check(ths.get("Progress") == "descending" and ths.get("Roadmap") == "none", "aria-sort reflects the active sort: " + str(ths))
    tbl = page.evaluate("(() => { const t = document.querySelector('.rtable').getBoundingClientRect(), w = document.querySelector('.table-wrap').getBoundingClientRect(), r = document.querySelector('.home-rail').getBoundingClientRect(); return {tr: t.right, wr: w.right, rl: r.left}; })()")
    check(tbl["tr"] <= tbl["wr"] + 1 and tbl["wr"] <= tbl["rl"], "list view fits beside the rail (no overlap)")
    check(not page.locator("th.col-month").is_visible(), "narrow column: 'Current month' column is hidden")
    page.screenshot(path=f"{SHOTS}/home-list.png")
    audit(page, "Home list view")
    page.click('th button[data-value="name"]')
    check(page.locator("th", has_text="Roadmap").get_attribute("aria-sort") == "ascending" and titles(page)[0] == "AI Engineer Roadmap", "click 'Roadmap' header: ascending (Name defaults A-Z)")
    page.click('th button[data-value="name"]')
    check(page.locator("th", has_text="Roadmap").get_attribute("aria-sort") == "descending" and titles(page)[0] == "Gamma", "click again: descending")
    page.reload(); page.wait_for_selector(".summary-bar")
    check(page.locator("table.rtable").count() == 1 and page.input_value("#homeSort") == "name", "view and sort are remembered after reload")
    check(page.locator("th", has_text="Roadmap").get_attribute("aria-sort") == "descending", "sort direction is remembered too")
    row = page.locator("tr.rt-row", has_text="Gamma")
    row.locator(".rt-name").click(); page.wait_for_selector(".stat-tile, #main", timeout=8000)
    check("/r/" in page.evaluate("location.hash"), "clicking a list row opens the roadmap")
    page.go_back(); page.wait_for_selector(".summary-bar")
    ctx2, page2 = new_context(browser, 1920, 1000)
    ctx2.add_cookies(ctx.cookies()); page2.goto(BASE); page2.wait_for_selector(".summary-bar")
    if page2.locator("table.rtable").count() == 0:
        page2.click('[data-action=set-view][data-value=list]')
    check(page2.locator("th.col-month").is_visible(), "wide screen (1920px): 'Current month' column appears")
    ctx2.close()
    page.click('[data-action=set-view][data-value=grid]'); page.select_option("#homeSort", "recent")

    # =============== E. Delete: typed name when there is progress ===============
    def open_delete(title):
        card = page.locator("article.roadmap-card", has_text=title)
        card.locator("[data-menu-trigger]").click(); card.locator("[data-action=delete-roadmap]").click()
        page.wait_for_selector("#modalHost:not(.hidden)")
        return card

    open_delete("Gamma")
    check(page.inner_text("#modalTitle") == "Delete “Gamma”?", "delete dialog title uses the roadmap name")
    check("You have completed 3 of 3 tasks." in page.inner_text("#modalHost"), "dialog states how much progress will be lost")
    check(page.locator("#deleteConfirmName").count() == 1 and page.locator("#deleteConfirmBtn").is_disabled(), "roadmap with progress: name field present, Delete disabled")
    check(page.evaluate("document.activeElement.id") == "deleteCancelBtn", "focus starts on Cancel")
    page.fill("#deleteConfirmName", "gamma")
    check(page.locator("#deleteConfirmBtn").is_disabled(), "wrong case keeps Delete disabled")
    page.screenshot(path=f"{SHOTS}/dialog-delete.png")
    audit(page, "Delete dialog with typed name")
    page.keyboard.press("Escape")
    check(page.locator("#modalHost.hidden").count() == 1 and page.locator("article.roadmap-card", has_text="Gamma").count() == 1, "Escape cancels; the roadmap still exists")
    check(page.evaluate("document.activeElement.hasAttribute('data-menu-trigger')"), "focus returns to the card's ⋯ button")
    open_delete("Gamma"); page.fill("#deleteConfirmName", "Gamma")
    check(not page.locator("#deleteConfirmBtn").is_disabled(), "exact name enables Delete")
    page.keyboard.press("Enter")
    page.locator("article.roadmap-card", has_text="Gamma").wait_for(state="detached", timeout=8000)
    check(page.locator(".toast.success", has_text="Roadmap deleted.").count() >= 1, "Enter in the name box deletes; toast 'Roadmap deleted.'")
    open_delete("Alpha")
    check(page.locator("#deleteConfirmName").count() == 0 and not page.locator("#deleteConfirmBtn").is_disabled(), "roadmap without progress: no name field, Delete enabled")
    page.click("#deleteConfirmBtn"); page.locator("article.roadmap-card", has_text="Alpha").wait_for(state="detached", timeout=8000)
    check(True, "plain confirmation deletes an untouched roadmap")
    # built-in untouched? Beta has progress; delete the built-in (no progress) then restore via the dialog
    open_delete("AI Engineer"); check(page.locator("#deleteConfirmName").count() == 0, "untouched built-in roadmap needs no typed name")
    page.click("#deleteConfirmBtn"); page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(state="detached", timeout=8000)
    page.wait_for_selector(".notice-row")
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    check(not page.locator('input[value="builtin"]').is_disabled(), "AI Engineer option is enabled when the account no longer has it")
    page.locator('input[value="builtin"]').check()
    check(page.locator("#newBlankFields").is_hidden() and page.inner_text("#createRoadmapSubmit") == "Restore roadmap", "choosing it hides the blank fields and relabels the button")
    page.click("#createRoadmapSubmit")
    page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(timeout=8000)
    check(page.locator(".toast.success", has_text="AI Engineer Roadmap restored.").count() >= 1, "restore through the dialog works")

    # =============== F. Right rail logic ===============
    page.reload(); page.wait_for_selector(".summary-bar")
    gs = " ".join(page.locator("#startedHeading").locator("xpath=..").inner_text().split())
    check("done" in gs and "Choose an appearance" in gs, "Getting started still visible while items remain")
    # Beta has a custom roadmap with a month and 2 completed tasks: items 1-3 done
    check(page.locator(".rail-list li.is-done").count() == 3 and "3 of 4 done" in gs, "Getting started: 3 of 4 done (task, custom roadmap, month)")
    page.click("#profileTrigger"); page.click("#themeLightBtn"); page.keyboard.press("Escape"); page.reload(); page.wait_for_selector(".summary-bar")
    check(page.locator("#startedHeading").count() == 0, "choosing an appearance completes the last item and hides the card")
    # Dismiss on a fresh account
    ctx3, page3 = new_context(browser); register(ctx3, "f"); home(page3)
    page3.click('[data-action="dismiss-getting-started"]')
    check(page3.locator("#startedHeading").count() == 0 and page3.locator("#focusHeading").count() == 1, "Dismiss removes only Getting started")
    page3.reload(); page3.wait_for_selector(".summary-bar")
    check(page3.locator("#startedHeading").count() == 0, "dismissal is remembered after reload")
    expect = page3.evaluate("""(() => { const d = window.ROADMAP_DATA, n = new Date(), idx = (n.getFullYear() - 2026) * 12 + (n.getMonth() - 9);
      if (idx < 0 || idx > 9) return null; const w = Math.floor((n.getDate() - 1) / 7); if (w > 3) return ''; const s = d.phases[idx].sections.find(s => s.type === 'week' && s.weekNumber && (s.weekNumber - 1) % 4 === w); return s ? s.title : ''; })()""")
    shown = page3.locator(".rail-week").inner_text() if page3.locator(".rail-week").count() else ""
    check((expect is None) or shown == expect, f"Current focus week line matches the roadmap data (expected '{expect}', shown '{shown}')")
    check(page3.locator(".home-rail [data-action=open-roadmap]").inner_text() == "Start", "Current focus button for an untouched roadmap says Start")
    ctx3.close()

    # =============== G. Other dialogs get Escape, focus return and trap ===============
    page.click("#sidebar [data-action=about]"); page.wait_for_selector("#modalHost:not(.hidden)")
    page.keyboard.press("Tab"); check(page.evaluate("document.activeElement.id") == "aboutCloseBtn" or page.evaluate("document.getElementById('modalHost').querySelector('.modal').contains(document.activeElement)"), "About: focus stays inside on Tab")
    page.keyboard.press("Escape")
    check(page.locator("#modalHost.hidden").count() == 1 and page.evaluate("document.activeElement.getAttribute('data-action')") == "about", "About: Escape closes it and focus returns to the About button")
    page.locator("article.roadmap-card", has_text="Beta").locator(".btn-primary").click(); page.wait_for_selector("#main")
    page.click('.tab[data-view="checklist"]'); page.wait_for_selector(".subtask-row, #main .empty-state, #main .section-title")
    if page.locator("[data-action=edit]").count() or page.locator(".mini-btn", has_text="details").count():
        page.locator(".mini-btn", has_text="details").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
        page.keyboard.press("Escape")
        check(page.locator("#modalHost.hidden").count() == 1, "task-details dialog also closes on Escape")
    else:
        check(True, "task-details dialog check skipped (no task rows in this roadmap)")
    page.go_back(); page.wait_for_selector(".summary-bar")
    check(not page.problems, "no page errors or CSP/console errors" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # =============== H. Phone and dark theme ===============
    ctx, page = new_context(browser, 390, 900)
    register(ctx, "h"); make_custom(ctx, "Beta Plan", "x", 1, 2); home(page)
    check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "phone: Home with toolbar has no horizontal scrolling")
    check(page.locator("#homeSearch").is_visible() and page.locator("#homeSort").is_visible(), "phone: search and sort are usable")
    page.click('[data-action=set-view][data-value=list]')
    check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "phone: list view has no horizontal scrolling")
    check(not page.locator("th.col-type").is_visible() and not page.locator("th.col-activity").is_visible(), "phone: list drops Type and Last activity columns")
    page.screenshot(path=f"{SHOTS}/home-list-phone.png", full_page=True)
    audit(page, "Home list view (phone)")
    page.click('[data-action=set-view][data-value=grid]'); audit(page, "Home grid with toolbar (phone)")
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    check(page.evaluate("(() => { const r = document.querySelector('#modalHost .modal').getBoundingClientRect(); return r.right <= window.innerWidth && r.left >= 0; })()"), "phone: New roadmap dialog fits the screen")
    audit(page, "New roadmap dialog (phone)")
    ctx.close()

    ctx, page = new_context(browser, 1440, 1000, "dark")
    register(ctx, "i"); make_custom(ctx, "Beta Plan", "dark theme", 2, 4); make_custom(ctx, "Gamma", "done", 3, 3); home(page)
    page.wait_for_timeout(900)
    page.screenshot(path=f"{SHOTS}/home-dark.png")
    audit(page, "Home grid + rail (dark)")
    page.click('[data-action=set-view][data-value=list]'); audit(page, "Home list (dark)")
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)"); audit(page, "New roadmap dialog (dark)"); page.keyboard.press("Escape")
    card = page.locator("tr.rt-row", has_text="Gamma"); card.locator("[data-menu-trigger]").click(); card.locator("[data-action=delete-roadmap]").click()
    page.wait_for_selector("#modalHost:not(.hidden)"); audit(page, "Delete dialog (dark)")
    ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
```

---

*End of Phase 3 spec. Phase 4 (the seven roadmap views) is specified separately.*
