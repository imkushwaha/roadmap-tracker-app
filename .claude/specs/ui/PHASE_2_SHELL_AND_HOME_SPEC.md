# Phase 2 — App Shell, Home and Progress Stats: Implementation Spec

> **Audience:** an AI coding agent (or developer) implementing this phase in the *Roadmap Tracker* repository.
> **Status of this spec:** every step below was executed on a copy of the original repository with Phases 0 and 1 applied, and verified: `npm test` 79/79 (59 + 20 new), Phase 2 UI harness **114/114**, plus the Phase 0 (61/61) and Phase 1 (67/67) harnesses still passing. If you follow it exactly you will get the same result.

| | |
|---|---|
| **Phase** | 2 of 5 — App shell, Home, `stats` API, hash routes |
| **Depends on** | **Phases 0 and 1 completed and verified** (Section 2) |
| **Branch** | continue on `feature/ui-redesign` |
| **Effort** | about 4.5 working days by hand; roughly an hour of agent time because every file and script is supplied |
| **Visible result** | A left sidebar and top bar replace the old header and the 7-tab row. Home gets a summary bar and roadmap cards with a **Month Strip**, percent complete and current month. Refresh, Back/Forward and bookmarks work through `#/r/<id>/<view>` URLs |
| **Backend change** | **Yes, one small additive change:** `GET /api/roadmaps` now includes a `stats` summary per roadmap (the raw progress is never exposed). 20 new tests |
| **Risk** | Medium. This phase restructures the page frame and the navigation code in `js/app.js`. Mitigation: all view renderers are untouched, every existing element ID is kept or mapped (Section 5), and the harness covers every flow |
| **Next phase** | Phase 3 — Home flows: New roadmap dialog, typed-name delete, filters/sort, list view, right rail (separate spec) |

---

## 0. Rules for the implementing agent (read first)

1. **Do exactly what this document says. Do not redesign.** Names, copy, sizes and behaviour are decided.
2. **Phases 0 and 1 must already be applied.** If `css/tokens.css`, `js/theme-boot.js`, `js/icons.js`, `js/month-strip.js`, `css/auth.css` are missing, stop and report.
3. **No new npm dependencies, no build step.**
4. **Do not change the seven view renderers** (`renderOverview`, `renderTimeline`, `renderKanban`, `renderChecklist`, `renderThisWeek`, `renderMastery`, `renderReference`), the save/conflict logic, the auth logic, `js/api.js`, `js/progress-schema.js`, the database schema, or any existing API behaviour. The **only** server change is the additive `stats` field (Tasks 2–5).
5. **Never send raw progress to the Home list.** The list response carries `stats` only; a test enforces this.
6. **Keep working behaviour:** save status and conflict dialog, export/import/reset/start month, legacy browser import, unsaved-change guards, the 20-roadmap limit, restore of the built-in roadmap, session-expiry handling. Section 5.1 maps every old element to its new home.
7. **Security rules** (`CLAUDE.md`): all user-supplied text (roadmap names and descriptions) goes through `esc()`; no inline scripts, no `eval`, no remote assets (strict CSP); only the appearance and sidebar preferences are stored in `localStorage` — never tokens or personal data; parameterised SQL only.
8. **If a script in this spec fails an `assert`**, the repository has drifted. Do not force it. Read that script's "Intent" list, apply the equivalent edit by hand, and record the difference in your hand-off.
9. **Run the verification (Section 7) before declaring done.** Commit in task order.

---

## 1. Goal and scope

### 1.1 Problems this phase fixes

| # | Problem today | Fix |
|---|---|---|
| 1 | Home is a narrow column at the top left; most of the screen is empty | App shell + summary bar + fluid card grid |
| 2 | Cards show only "Not started yet" — no sense of progress | Month Strip, percent, task counts, current month on every card |
| 3 | "Open" and "Delete" side by side; non-functional "Create with AI" tile looks like content | One **New roadmap** button; Delete moves into a ⋯ menu behind a confirmation |
| 4 | The roadmap header is two crowded rows (brand, title, save status, menus, 7 tabs, search) | Sidebar for navigation; slim top bar for breadcrumb, search, save chip and menus |
| 5 | The account menu is moved between two places in the DOM depending on screen | One account menu in the top bar |
| 6 | Footer credits only on the login screen | **About** dialog reachable everywhere (sidebar, account menu) |
| 7 | No URLs: refresh drops you on Home, Back leaves the app | Hash routes `#/` and `#/r/<id>/<view>` |
| 8 | "Loading…" is a full-screen card that hides the whole app | Skeletons inside the shell |
| 9 | The list API gives no progress numbers | `stats` per roadmap (server-side, cached) |

### 1.2 Deliverables

| # | Deliverable | Files |
|---|---|---|
| 1 | Progress summary module (shared UMD) | `js/roadmap-stats.js` (new) |
| 2 | Stats service with cache | `server/roadmaps/stats.js` (new) |
| 3 | `listWithProgress` + list route returns `stats` | `server/roadmaps/repository.js`, `server/routes/roadmaps.js` |
| 4 | 20 new tests | `test/stats.test.js` (new) |
| 5 | Shell + Home styles | `css/shell.css`, `css/home.css` (new); old header/tabs/dashboard rules removed from `css/styles.css` |
| 6 | Shell markup | `index.html` |
| 7 | Shell, Home, sidebar, routing, About logic | `js/app.js` |
| 8 | Five more icons, `.sr-only` utility | `js/icons.js`, `css/base.css` |
| 9 | Documentation | `README.md`, `documentation/*.md`, `.claude/*` |

### 1.3 Out of scope (do NOT do these here — Phase 3 or later)

- A redesigned **New roadmap** dialog (keep the existing create dialog), the disabled "Describe a goal (AI)" option, typed-name delete confirmation, search/filter/sort on Home, list view, the right-hand rail (Current focus, Getting started), rename roadmap.
- Restyling the seven roadmap views themselves (Phase 4). They simply sit inside the new shell and pick up the Phase 0 tokens.
- A tablet icon-rail (dropped; below 1024px the sidebar is always a drawer).
- Account settings, change password, undo delete (need backend work; later).

---

## 2. Preconditions

```bash
git status                        # on feature/ui-redesign, clean
npm test                          # expect: tests 59, pass 59, fail 0
ls css/tokens.css css/base.css css/components.css css/auth.css js/theme-boot.js js/icons.js js/month-strip.js img/logo.svg fonts/*.woff2
grep -c "renderAuthPanelStrip" js/app.js    # expect > 0 (Phase 1)
grep -c "window.Theme" js/app.js            # expect > 0 (Phase 0)
```

Optionally re-run the Phase 0 and Phase 1 harnesses first so you know the baseline is green.

### 2.1 How the page is organised today (facts you must respect)

- `index.html` has: `#authScreen` (overlay, Phase 1); `#dashboardScreen` (a fixed overlay with its own bar, holding `#dashboardContent`); `<header class="app-header">` (brand, `#roadmapTitle`, `#roadmapSubtitle`, `#backToDashboardBtn`, save status `#panelSaveStatus`, roadmap menu, account menu slot, `#tabs` with seven `.tab` buttons carrying `data-view`, search `#roadmapSearch`); `<main id="main">` (the view renderers write here); toast host, confetti canvas and `#modalHost`.
- `body.locked` hides the app header and `main` while the auth screen or a status panel (`showBlock`) is showing. `lockApp()` / `unlockApp()` toggle it.
- The account menu (`#profileAnchor`) was moved between `#dashboardAccountSlot` and `#roadmapAccountSlot` by `mountAccountMenu()`.
- `showDashboard()` fetches `RoadmapApi.list()` and calls `renderDashboard(roadmaps)`; `openRoadmap(id)` loads progress and renders; `backToDashboard()` flushes unsaved changes (`settleUnsavedChanges`) then shows Home; `setView(view)` / `rerender()` render the current view into `#main`; `syncTabs()` hides the Skills and Reference tabs for roadmaps that lack them.
- Menus use `createMenu(trigger, panel)`, `closeAllMenus()`, `menuRefs`.
- There is **no URL routing** today.
- `session.roadmapId` is `null` on Home and the open roadmap's id otherwise. `session.username` is set after login.

---

## 3. Design specification

### 3.1 Shell layout

```
HOME (data-context="home")                                  ROADMAP (data-context="roadmap")
┌──────────────┬────────────────────────────┐               ┌──────────────┬──────────────────────────────────────┐
│ [logo] Road- │ Roadmaps          (UK) Name▾│               │ [logo] Road- │ Roadmaps / AI Engineer Roadmap       │
│ map Tracker  ├────────────────────────────┤               │ map Tracker  │ [Search…] ●Saved [⚙ Roadmap▾] (UK)▾ │
│              │                            │               │              ├──────────────────────────────────────┤
│ ▣ Roadmaps   │       PAGE CONTENT         │               │ ← All roadmaps│                                      │
│              │                            │               │ ┌──────────┐ │                                      │
│ Your         │                            │               │ │AI Engineer│ │          VIEW CONTENT                │
│ roadmaps     │                            │               │ │desc…     │ │                                      │
│  AI Engineer │                            │               │ │▮▮▯▯▯▯▯▯▯▯ │ │                                      │
│  ▮▮▯▯▯▯▯▯▯▯  │                            │               │ └──────────┘ │                                      │
│              │                            │               │ Views        │                                      │
│              │                            │               │  Overview ◀  │                                      │
│              │                            │               │  Timeline    │                                      │
│ ? About      │                            │               │  Kanban …    │                                      │
│ ▢ Collapse   │                            │               │ ? About      │                                      │
└──────────────┴────────────────────────────┘               └──────────────┴──────────────────────────────────────┘
   248px (64px collapsed)
```

| Item | Spec |
|---|---|
| Grid | `.app-shell` is a 2-column grid: sidebar `248px` (`64px` when `.is-collapsed`) + content `minmax(0, 1fr)`. `body.locked .app-shell { display: none }` |
| Page | `.page-inner` max-width **1600px**, centered, padding 24px 32px 64px (24px / 20px 24px 56px under 1024; 16px 12px 48px under 640) |
| Context | `#appShell[data-context="home"\|"roadmap"]`. Elements with class `roadmap-only` (search, save chip, roadmap menu) are hidden on Home |
| Z-index | top bar 20, sidebar 30, drawer scrim 55, drawer 60, modal 400 (unchanged), toasts 450, auth overlay 500 |

### 3.2 Sidebar

Background `--bg-brand`, text white at 86%; always dark in both themes (it pins a lighter accent `#8aa3ff` and dark-theme status colours for its strips).

| Part | Spec |
|---|---|
| Head (56px) | Logo mark 28px + "Roadmap Tracker" (15px/600, white) |
| Nav item `.nav-item` | min-height 36px, 14px/500, radius 6px, padding 6px 12px; hover `rgb(255 255 255 / .08)`; **active** = `.active` or `aria-current="page"`: background `rgb(255 255 255 / .12)` and a 3px accent bar on the left edge |
| **Home section** (`#sidebarHome`) | Item "Roadmaps" (active), heading "Your roadmaps", then `#sidebarRoadmapList`: one `button.nav-item.nav-roadmap[data-action="open-roadmap"][data-id]` per roadmap showing the name (ellipsis), the percent (when stats exist) and a **sm** Month Strip. Empty: "No roadmaps yet." |
| **Roadmap section** (`#sidebarRoadmap`) | Button "All roadmaps" (`#backToDashboardBtn`, arrow-left icon); a card with the roadmap name (`#roadmapTitle`), description clamped to 2 lines (`#roadmapSubtitle`) and a live **md** Month Strip (`#sidebarStrip`); heading "Views"; seven buttons (`#tabs`, class `tab nav-item`, `data-view`) |
| View buttons | Overview (layout-grid), Timeline (calendar), Kanban (columns), Checklist (list-checks), This week (clock), Skills checklist (award), Reference (book-open). Skills and Reference are hidden by the existing `syncTabs()` when the roadmap lacks them (custom roadmaps) |
| Foot | "About" (help icon, `data-action="about"`), "Collapse" (`#sidebarCollapseBtn`, `aria-pressed`, desktop only) |
| Icon hydration | Elements with `data-icon="name"` receive `Icons.svg(name)` at start-up (`hydrateIcons`): 20px for `.nav-icon`, 14px otherwise |

**Collapsed (desktop only):** 64px; labels, headings, brand text, roadmap card and the roadmap list are hidden; items are centered icons with `title` tooltips. State is stored in `localStorage["roadmap-dashboard:sidebar"]` as `"collapsed"` or `"expanded"` (storage errors are ignored).

**Drawer (below 1024px):** the sidebar is `position: fixed`, 280px wide (max 86vw), off-canvas via `transform: translateX(-100%)`; `.app-shell.nav-open` slides it in; `#sidebarScrim` covers the page. The Collapse button is hidden; the drawer is always expanded. It closes on: scrim click, **Escape** (focus returns to `#sidebarOpenBtn`), choosing a view, choosing a roadmap, opening About.

### 3.3 Top bar

`position: sticky; top: 0; z-index: 20`, min-height 56px, `--bg-elevated`, 1px bottom border, wraps on small screens.

| Part | Spec |
|---|---|
| `#sidebarOpenBtn` | Visible below 1024px only; ghost icon button (menu icon); `aria-expanded`, `aria-controls="sidebar"` |
| Breadcrumb | `<nav aria-label="Breadcrumb"><ol>`: Home → "Roadmaps" as plain current text. Roadmap → **"Roadmaps"** as a link-style button (`data-action="go-home"`) `/` roadmap name (`#crumbRoadmapName`, `aria-current="page"`, ellipsis at 36ch; 18ch on phones) |
| Search `#roadmapSearch` | roadmap only; 260px; on phones it takes its own full-width row |
| Save chip `#panelSaveStatus` | a `<button>`; roadmap only; hidden when empty. Classes `saving` (amber), `saved` (green), `error` / `conflict` (red, clickable). Same `setSaveStatus()` and click handler as before |
| Roadmap menu `#roadmapMenuTrigger` | roadmap only; gear icon + label "Roadmap" (label hidden on phones); panel `#roadmapMenuPanel` |
| Account menu `#profileTrigger` | avatar (`#profileAvatar`, 24px initials) + first/last name (hidden on phones) + caret; panel `#profilePanel` |

### 3.4 Menus

**Account menu** (one element, always in the top bar): header with full name and `@username`; "Appearance" with **Light / Dark / System**; button "About Roadmap Tracker" (`data-action="about"`); "Log out" (`#logoutBtn`).

**Roadmap settings menu:** header with the roadmap name (`#roadmapMenuName`) and "Roadmap settings"; then `#startMonthBtn` "Set start month…", `#exportBtn` "Export progress (JSON)", `#importBtn` "Import progress (JSON)" (+ hidden `#importFile`), `#legacyImportBtn` "Import old data from this browser…" (shown only for the built-in roadmap when old browser data exists), separator, `#resetBtn` "Reset progress…" (red). **Labels are the originals without their emoji prefixes**; IDs and handlers are unchanged.

Both panels are labelled groups (`role="group"` + `aria-label`), not `role="menu"`; triggers have `aria-expanded` and `aria-controls`.

### 3.5 About dialog

Opened by any element with `data-action="about"`; rendered into the shared `#modalHost` (`openAboutModal`). Content, in order: heading "About Roadmap Tracker"; one sentence of description; list: © year Roadmap Tracker. All rights reserved. · Developed by (mailto link) · GitHub: imkushwaha (link) · "If this tool helps you, please star the repo." (link) · "Built with planning & development assistance from **Claude** (Anthropic AI)." · "Open source. Contributions welcome."; a primary **Close** button (`#aboutCloseBtn`) that receives focus. External links use `target="_blank" rel="noopener"`.

### 3.6 Home screen

```
Roadmaps                                         [+ New roadmap]
Track progress across your plans.

┌ Roadmaps ──┬ Tasks done ─┬ Overall progress ┬ Done this week ┐
│ 1          │ 124 / 849   │ 15%              │ 50             │
└────────────┴─────────────┴──────────────────┴────────────────┘
┌──────────────────────────────────────────────┐ ┌─────────────…
│ AI Engineer Roadmap          [Built-in]    ⋯ │ │ next card
│ Tier-1 Production AI Engineer — 10-Month    │
│ Execution Tracker                            │
│ [▮][▮][▮][▮][▮][▮][▮][▮][▮][▮]  (Month Strip)│
│ 15% complete · 124 of 849 tasks   Month 2 of 10
│ ──────────────────────────────────────────── │
│ Last activity today                [Continue]│
└──────────────────────────────────────────────┘
```

| Part | Spec |
|---|---|
| Page head | `h1.page-title` "Roadmaps"; `p.page-lead` "Track progress across your plans."; right: `.page-actions` with **New roadmap** (primary, plus icon, `data-action="create-roadmap"`). It opens the **existing** create dialog. At 20 roadmaps it is `disabled` with `title="You've reached the limit of 20 roadmaps."` |
| Restore notice | When the account has no built-in roadmap but has others: `.notice-row` "The AI Engineer roadmap isn't in your account. You can bring it back with fresh progress." + small button "Restore AI Engineer roadmap" (`data-action="restore-builtin"`) |
| Summary bar | One panel, 4 equal columns separated by 1px dividers (2×2 under 768px). Metrics: **Roadmaps** (count) · **Tasks done** (`completed <small>/ total</small>`, sums over roadmaps that have stats) · **Overall progress** (rounded percent, 0 when total is 0) · **Done this week** (sum of `completedLast7Days`). Values 22px/600, tabular numbers |
| Grid | `repeat(auto-fill, minmax(340px, 1fr))`, gap 16px; single column under 400px |
| Card | `article.roadmap-card[data-id]` (clicking the card body, but not a button, opens it) |
| Card head | `h2.rc-title` (name, escaped), badge `Built-in` (`source === "builtin_ai_engineer"`) or `Custom`, overflow menu (⋯ button `data-menu-trigger`, `aria-label="More actions for <name>"`, `aria-expanded`) whose panel holds **Delete roadmap…** (`data-action="delete-roadmap"`, danger style) |
| Description | 2-line clamp, min-height 36px; empty if none |
| Progress block | Present when `stats` exists: a **md** Month Strip built from `stats.months` + a meta row: left `<strong>{pct}%</strong> complete · {completed} of {total} tasks`, or **"No months yet. Add one to start."** when `total === 0`; right: the month position (below) |
| Footer | Left: `describeActivity()` ("Not started yet" / "Last activity today / yesterday / N days ago"). Right: primary button (below) |
| Primary action label | `stats` missing → **Open**; `total === 0` → **Build plan**; `completed === total` → **Review**; any completed/in-progress/blocked → **Continue**; else **Start**. The button has `data-action="open-roadmap" data-id` |
| Month position | The current calendar month's index within the roadmap, from `stats.startMonth` (if `null`, the current month is Month 1) and the user's **local** date: inside → `Month N of M`; before the start → `Starts Mon YYYY`; after the end → `M months`; no months → empty |
| Animation | Strips animate (`animate: true`) the **first** time Home renders in a page visit only (`stripsAnimated` flag) |
| Loading | `dashboardSkeleton()`: heading, lead "Loading your roadmaps…" and **3** skeleton cards of the final size; replaced by real content |
| Error | "We couldn't load your roadmaps: <message>" + **Try again** (`data-action="retry-dashboard"`); a 401 triggers the existing session-expired flow |
| Empty | `.empty-panel`: heading "No roadmaps yet", text "Start with the AI Engineer roadmap or build your own plan.", buttons **Restore AI Engineer roadmap** (primary, `restore-builtin`) and **Blank roadmap** (`create-roadmap`) |
| Card menu | Opens on click; one open at a time; closes on Escape, outside click, and any action |
| Delete | Unchanged confirmation flow (`confirmDeleteRoadmap` → `deleteRoadmap`). (Phase 3 adds the typed-name rule) |

**Month Strip data from `stats`** (`stripMonths`): label = short month name of `startMonth + index` (local date; `startMonth` null → this month); title = `Month {number}: {title or "Untitled"} ({completed} of {total} tasks complete)`; counts from the month; `current` = the month containing today.

### 3.7 Inside a roadmap

- **Loading:** `openRoadmap` first calls `showRoadmapLoading()`: hide the auth overlay, unlock the app, set context `roadmap`, show `#roadmapScreen` with a skeleton (title bar, 4 tiles, one tall block), set the name placeholders to "Loading…", and add `.is-loading` to `#tabs` (50% opacity, not clickable). On failure it falls back to the existing status panel (`showBlock`) with **Try again** and **Back to roadmaps**; 401 → `showAuth("login")`.
- **After loading:** name goes to `#roadmapTitle`, `#roadmapH1` (a visually hidden `h1.sr-only` — the one H1 of the screen), `#crumbRoadmapName` and `#roadmapMenuName`; description to `#roadmapSubtitle`; `document.title` = `<name> — Roadmap Tracker` (Home: `Roadmap Tracker`); search is cleared; the sidebar strip is drawn.
- **Live strip:** `rerender()` ends with `renderSidebarStrip()`, which builds the md strip from the open roadmap's own data (`allPhases()`, `phaseStats`, `currentPhase()`), so the strip updates as tasks change.
- **Views:** each `.tab` button toggles `active` and `aria-current="page"`; clicking one calls `setView(view)`, closes the drawer and scrolls to top.

### 3.8 Routing

| URL | Meaning |
|---|---|
| `#/` | Home |
| `#/r/<id>/<view>` | Roadmap `<id>` showing `<view>` (`overview`, `timeline`, `kanban`, `checklist`, `thisweek`, `mastery`, `reference`). A missing/unavailable view falls back to `overview` (`validView`). Only plain `#path` URLs; no query strings |

| Event | History action |
|---|---|
| Login success, no route in the URL | `replaceState` to `#/` |
| Login success, route in the URL | open that roadmap (no new entry) |
| Open a roadmap | **push** `#/r/<id>/<view>` |
| Change view | **replace** `#/r/<id>/<view>` (does not grow history) |
| Back to Home (sidebar button, breadcrumb link) | **push** `#/` |
| Browser Back/Forward (`popstate`) | follow the URL; **if leaving a roadmap with unsaved changes, `settleUnsavedChanges("Leave")` runs first; if the user cancels, push the previous hash back and stay** |
| Load error "Back to roadmaps" | replace `#/` |
| Log out | `replaceState` to the bare path (no hash), then reload |
| Session expiry | the hash is kept, so after logging in again the user returns to the same roadmap |

`#/r/999999/overview` (not found / not yours) shows the existing error panel: title "Couldn't load this roadmap", the server's message, buttons **Try again** and **Back to roadmaps**.

### 3.9 `stats` — server contract

`GET /api/roadmaps` adds `stats` to each roadmap (or `null` if its stored data is unreadable):

```json
"stats": {
  "total": 849, "completed": 0, "inProgress": 0, "blocked": 0,
  "completedLast7Days": 0, "startMonth": "2026-10",
  "months": [ { "number": 1, "id": "month-1", "title": "Software Engineering Upgrade",
                "total": 180, "completed": 0, "inProgress": 0, "blocked": 0 } ]
}
```

Counting rules (identical to the client's `rebuildIndex`/`statsFor`):

1. Every **task** and every **month deliverable** of the curriculum counts once (built-in: 793 + 56 = **849**, in **10** months; month 1 has 180).
2. User-added topics (`progress.custom.topics`) count in the month that owns their `sectionId`, built-in or custom. A topic whose section does not exist is ignored.
3. User-added months (`progress.custom.phases`) follow the built-in months and are numbered after them.
4. An id missing from `progress.items` is **not started**.
5. `completedLast7Days` = items whose `completedAt` is a valid date within the last 7 days.
6. `startMonth` = `progress.settings.startMonth`, else the roadmap's authored start (`data/roadmap.json` `meta.horizonStart`, as `YYYY-MM`; built-in = `2026-10`), else `null` (custom roadmap without one).
7. A custom roadmap's curriculum is empty: everything comes from `progress.custom`.

The client works out the **current month** from `startMonth` and its own local date (avoids server time-zone mistakes).

**Cache:** in-memory `Map` keyed `"<roadmapId>:<version>"`, TTL 10 minutes, max 500 entries (oldest evicted). A save bumps `version`, so stale numbers are impossible; the TTL only keeps "last 7 days" fresh. A roadmap with no progress row is summarised without caching. Corrupt JSON gives `stats: null` and never fails the request.

### 3.10 Responsive behaviour

| Width | Behaviour |
|---|---|
| < 640 | Drawer; page padding 12px; search on its own row; roadmap-menu label and account name hidden; summary bar 2×2; toast host full width |
| 640–1023 | Drawer; summary bar 2×2 under 768; padding 24px |
| ≥ 1024 | Sticky sidebar (collapsible) |
| ≥ 1600 | Content capped at 1600px and centered |

No horizontal scrolling at any width ≥ 320px.

### 3.11 Accessibility requirements

- Landmarks: `<aside aria-label="Sidebar">`, `<nav aria-label="Primary">`, `<nav aria-label="Breadcrumb">`, `<main id="main">`; exactly one H1 per screen (Home: `h1.page-title`; roadmap: `h1.sr-only#roadmapH1`).
- Active view and active home item use `aria-current="page"`; icon-only buttons have `aria-label`; the card's ⋯ button is labelled with the roadmap name; decorative icons are `aria-hidden`.
- Strips are `role="img"` with a text summary.
- Focus: visible ring everywhere (white ring inside the dark sidebar); Escape closes menus, card menus and the drawer; About focuses its Close button.
- axe-core WCAG 2.2 A/AA: 0 violations on Home, card menu, About, collapsed sidebar, empty state, the drawer, and all seven views in light and dark.

---

## 4. Tasks (do them in this order)

> Run every `python3 step2_*.py` from the **repository root**. Keep the scripts outside the repo (or delete them afterwards); **do not commit them.**

### Task 1 — Baseline
Confirm Section 2 passes (59/59).

### Task 2 — `js/roadmap-stats.js`
Create from **Appendix A1** verbatim.
**Acceptance:** `node --check js/roadmap-stats.js`; and
```bash
node -e "const S=require('./js/roadmap-stats');const t=S.summarize(S.buildCurriculum(require('./data/roadmap.json')),null);console.log(t.total,t.months.length,t.startMonth,t.months[0].total)"
# expect: 849 10 2026-10 180
```

### Task 3 — `server/roadmaps/stats.js`
Create from **Appendix A2** verbatim (cache + service).

### Task 4 — Wire the repository and route
Run **Appendix B1** (`step2_server.py`).
**Intent:** (a) `repository.js`: add `listWithProgress(userId)` (same join as `listForUser` plus `p.data AS progress_data`, `p.version AS progress_version`) and export it; (b) `routes/roadmaps.js`: require the stats service, accept an injectable `builtinData` (defaults to `require("../../data/roadmap.json")`), and make `GET /` build `stats` per roadmap while **stripping** `progressData`/`progressVersion` from the response.
**Acceptance:** prints `server/roadmaps/repository.js and server/routes/roadmaps.js updated`; `npm test` still 59/59.

### Task 5 — Tests
Create `test/stats.test.js` from **Appendix A3** verbatim.
**Acceptance:** `npm test` → **tests 79, pass 79, fail 0**.

### Task 6 — Icons and `.sr-only`
Run **Appendix B2** (`step2_misc.py`): adds `columns`, `list-checks`, `clock`, `award`, `book-open` to `js/icons.js` and the `.sr-only` utility to `css/base.css`.

### Task 7 — `css/shell.css` and `css/home.css`
Create from **Appendix A4** and **A5** verbatim.

### Task 8 — Remove old header/tab/dashboard rules from `css/styles.css`
Run **Appendix B3** (`step2_styles.py`).
**Intent:** delete the "Header" block (brand, subtitle, `.header-actions`, save-status rules), the tab row (`.tabs-row`, `.tabs`, `.roadmap-search`, `.tab*`) and the bare `main` rule, the whole "Roadmap dashboard" block (cards, bar, grid, action tiles, `.back-btn`, `.coming-soon-badge`) and the old mobile header rules; remove the `body.locked .app-header, body.locked main` rule (`shell.css` replaces it). **Keep** the account-menu rules (`.profile-*`) — they are reused.
**Acceptance:** prints `css/styles.css: 256 lines`.

### Task 9 — Shell markup in `index.html`
Run **Appendix B4** (`step2_index.py`). It replaces everything from `<div id="dashboardScreen"` up to (not including) `<div id="toastHost"` with the shell and adds the `shell.css` and `home.css` links after `auth.css`.
**Acceptance:** prints `index.html updated`.

### Task 10 — Shell, Home, sidebar, routing and About in `js/app.js`
Run **Appendix B5** (`step2_appjs.py`).
**Intent:** (a) replace the block from `enterDashboard` to `renderDashboard` with: `enterDashboard` (avatar initials, route-or-Home), `hydrateIcons`, `setContext`, drawer/collapse helpers, `openAboutModal`, the routing helpers (`parseRoute`, `routeFor`, `navigate`, `replaceRoute`, `validView`, `onPopState`), `dashboardSkeleton`, `showDashboard`, `describeActivity`, Month Strip data helpers, `roadmapCard`, `summaryBar`, `renderDashboard`, `renderSidebarRoadmaps`, `renderSidebarStrip`, card-menu helpers; (b) replace `onDashboardClick`; (c) replace `openRoadmap` and add `showRoadmapLoading`; (d) replace `rerender` and `setView`; (e) delete `mountAccountMenu`; (f) `backToDashboard` pushes `#/`; `logout` clears the hash; (g) wire tab clicks, sidebar, drawer, collapse, `data-action` for About/Home, `popstate`, Escape; (h) in `init()` call `hydrateIcons()` and `initSidebar()`.
**Acceptance:** prints `js/app.js updated`; `node --check js/app.js`.

### Task 11 — Documentation (required by `CLAUDE.md`)
Run **Appendix B6** (`step2_docs.py`). Also copy this spec to `.claude/specs/ui-redesign-phase-2.md` (recommended).
**Acceptance:** prints `docs updated`.

### Task 12 — Verify
Follow Section 7.

---

## 5. Contracts

### 5.1 Where every old element went

| Old | New |
|---|---|
| `#dashboardScreen` (fixed overlay with its own bar) | `#dashboardScreen` is now a normal `.page` inside `#appShell` |
| `#dashboardContent` | unchanged id, same role (Home content) |
| `.app-header`, `.brand`, `#roadmapSubtitle`, `#roadmapTitle` | sidebar roadmap card (`#roadmapTitle`, `#roadmapSubtitle` keep their ids) |
| `#backToDashboardBtn` (arrow button in the header) | sidebar "All roadmaps" button, same id |
| `#tabs` (horizontal row) | `#tabs` in the sidebar (same id, same `.tab[data-view]` buttons) |
| `#roadmapSearch` | top bar, same id |
| `#panelSaveStatus` (text in the header) | top-bar chip (now a `<button>`), same id |
| Roadmap menu trigger/panel | top bar, same ids (`roadmapMenuTrigger`, `roadmapMenuPanel`, `roadmapMenuName`, `startMonthBtn`, `exportBtn`, `importBtn`, `importFile`, `legacyImportBtn`, `resetBtn`) |
| `#profileAnchor`, `#profileTrigger`, `#profilePanel`, `#profileName`, `#panelFullName`, `#panelUsername`, theme buttons, `#logoutBtn` | one instance in the top bar, same ids; new `#profileAvatar`, `#themeSystemBtn` (Phase 0), About item |
| `#dashboardAccountSlot`, `#roadmapAccountSlot`, `mountAccountMenu()` | **removed** |
| `<main id="main">` | `#main` inside `#roadmapScreen` (renderers still write to it) |
| "Create new / Restore / Create with AI" tiles | **New roadmap** button, restore notice / empty-state button; the AI tile is removed for now (Phase 3 re-adds it as a disabled option) |

### 5.2 New element IDs and attributes

`appShell` (`data-context`), `sidebar`, `sidebarHome`, `sidebarRoadmap`, `sidebarRoadmapList`, `sidebarStrip`, `sidebarCollapseBtn`, `sidebarOpenBtn`, `sidebarScrim`, `crumbHome`, `crumbRoadmap`, `crumbRoadmapName`, `roadmapScreen`, `roadmapH1`, `profileAvatar`, `aboutCloseBtn` (created by the dialog). Actions (`data-action`): `open-roadmap`, `delete-roadmap`, `restore-builtin`, `create-roadmap`, `retry-dashboard`, `about`, `go-home`; `data-menu-trigger` on card menus.

### 5.3 New functions in `js/app.js` (names Phase 3 will rely on)

`initialsOf`, `hydrateIcons`, `setContext(ctx)`, `openNav`, `closeNav`, `setSidebarCollapsed`, `initSidebar`, `openAboutModal`, `parseRoute`, `routeFor`, `navigate`, `replaceRoute`, `validView`, `onPopState`, `dashboardSkeleton`, `showDashboard`, `monthKeyOffset`, `currentMonthIndex`, `stripMonths`, `pctOf`, `cardAction`, `monthPosition`, `roadmapCard`, `summaryBar`, `renderDashboard(roadmaps)`, `renderSidebarRoadmaps`, `renderSidebarStrip`, `closeCardMenus`, `toggleCardMenu`, `showRoadmapLoading`, `openRoadmap(id, { view, push })`, `setView(view, { silent })`. Module state: `dashboardRoadmaps`, `stripsAnimated`, `lastHash`, `MAX_ROADMAPS = 20`.

### 5.4 Storage

`roadmap-dashboard:theme` (Phase 0) and `roadmap-dashboard:sidebar` (`"collapsed"` \| `"expanded"`). Nothing else.

---

## 6. Acceptance criteria (checklist)

**Backend**
- [ ] `GET /api/roadmaps` returns `stats` for each roadmap: built-in = 849 items, 10 months, `startMonth` `"2026-10"` on a new account; custom roadmaps count their own months/topics/tasks.
- [ ] The response never contains raw progress (`data`, `progressData`, `progressVersion`, `celebratedPhases`, …).
- [ ] `npm test` → 79/79; no change to existing API behaviour.

**Shell and Home**
- [ ] Desktop: sticky 248px sidebar; collapses to ~64px and remembers it across reloads; top bar with breadcrumb.
- [ ] Home shows the summary bar (numbers equal the API's totals), cards with Month Strip, percent, tasks, month position, last activity and the correct primary action (**Start / Continue / Review / Build plan / Open**).
- [ ] Roadmap-only controls (search, save chip, roadmap menu) are hidden on Home and visible in a roadmap.
- [ ] Card ⋯ menu opens/closes (Escape, outside click); Delete works through the existing confirmation; deleting the last roadmap shows the empty state; restore works from both the empty state and the notice.
- [ ] At 20 roadmaps **New roadmap** is disabled with the explanatory title.
- [ ] Skeleton cards appear while the list loads.
- [ ] About dialog opens from the sidebar and the account menu, focuses Close, shows credits and links.

**Roadmap**
- [ ] The sidebar shows "All roadmaps", the roadmap card with a **live** strip, and the views; the active view has `aria-current="page"`; custom roadmaps show 5 views.
- [ ] Save chip shows Saving/Saved/error/conflict as before; roadmap settings menu items (Export downloads a `.json`, Set start month opens a month picker, Reset asks for confirmation) all work.
- [ ] All seven views render and work as before.

**Routing**
- [ ] Opening a roadmap pushes `#/r/<id>/overview`; changing view replaces the URL; reload restores roadmap and view; Back goes Home (`#/`), Forward returns.
- [ ] A change made just before pressing Back is saved (no data loss); unsaved-change prompt still appears when it cannot be saved.
- [ ] An unknown roadmap id shows the error panel; "Back to roadmaps" lands on `#/`.
- [ ] Log out leaves no hash in the URL.

**Responsive and quality**
- [ ] Below 1024px the sidebar is a drawer: opens from the menu button, closes on Escape (focus returns to the button), scrim, choosing a view or a roadmap.
- [ ] No horizontal scrolling at 390px and 820px.
- [ ] axe-core 0 violations (see 3.11); no console/CSP errors; no inline scripts.
- [ ] Phase 0 harness (61/61) and Phase 1 harness (67/67) still pass.
- [ ] A static check finds **no element ID referenced by `js/app.js` that is missing from `index.html`/templates** (Section 7.2).
- [ ] Docs updated.

---

## 7. Verification

### 7.1 Automated

```bash
npm test      # expect: tests 79, pass 79, fail 0
```

### 7.2 Static ID check (catches silent breakage in markup moves)

```bash
python3 - <<'EOF'
import re
js = open("js/app.js", encoding="utf-8").read(); html = open("index.html", encoding="utf-8").read()
used = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', js)) | set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', js))
defined = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', html)) | set(re.findall(r'\bid=\\?"([A-Za-z0-9_-]+)\\?"', js))
missing = sorted(used - defined)
print("missing ids:", missing); raise SystemExit(1 if missing else 0)
EOF
# expect: missing ids: []
```

### 7.3 UI harnesses

Keep these **outside the repo** in one folder (e.g. `/tmp/ui-verify/`): `serve-demo.js` and `verify_phase0.py` (Phase 0 spec, Appendices C1–C2), `verify_phase1.py` (Phase 1 spec, Appendix C1) and this phase's `verify_phase2.py` (Appendix C1).

```bash
npm install --prefix /tmp/ui-verify axe-core
node /tmp/ui-verify/serve-demo.js "$(pwd)" 3111 &            # keep running
python3 /tmp/ui-verify/verify_phase2.py http://127.0.0.1:3111  # expect: RESULT 114/114
python3 /tmp/ui-verify/verify_phase1.py http://127.0.0.1:3111  # regression: RESULT 67/67
python3 /tmp/ui-verify/verify_phase0.py http://127.0.0.1:3111  # regression: RESULT 61/61
```

The harness uses a fresh user for most flows and the demo user (with progress) for the summary and accessibility checks, creates 19 extra roadmaps for the limit test, delays the list request to observe the skeleton, and writes screenshots to `/tmp/ui-verify/shots-p2`. It evaluates axe through the DevTools protocol (the app's CSP blocks injected `<script>`). It adapts to the current date when checking the "Month N of 10" text.

### 7.4 Visual checklist

| Screenshot | What you should see |
|---|---|
| `home-desktop-light.png` | Left: navy sidebar with logo, active "Roadmaps", "Your roadmaps" with one entry (name, small strip), "About" and "Collapse" at the bottom. Top bar: "Roadmaps", account button with a "RR" avatar. Page: title, lead, blue **+ New roadmap**; a four-column summary panel; one card with a 10-segment strip, "Start", "Month N of 10" |
| `home-light-progress.png` / `-dark-` | Same, with demo progress: green first segments, an amber/red sliver, blue underline under the current month, "Continue" |
| `roadmap-overview-dark.png` | Sidebar now shows "← All roadmaps", a roadmap card with a strip and the seven views (Overview active, left accent bar); top bar: breadcrumb "Roadmaps / AI Engineer Roadmap", search, green "Saved" chip, "Roadmap" menu, account |
| `roadmap-checklist-desktop-light.png` | Same shell around the unchanged checklist |
| `drawer-phone.png` | Dark drawer over a dimmed page, "Roadmaps" and the roadmap entry visible; no Collapse button |
| `roadmap-phone.png` | Top bar wraps: menu button + breadcrumb, then chip/menu/avatar, then a full-width search row; content stacked |

### 7.5 Known and acceptable

- Home has only the summary bar and cards (no right rail yet); with one roadmap the right side of the page is empty by design until Phase 3.
- The roadmap views keep their old internal layouts (Phase 4).
- The strips in the demo screenshots depend on today's date for the "current" marker.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Blank app after login, console `Cannot read properties of null` | An element ID from 5.1/5.2 is missing in the new markup — run the static ID check (7.2) |
| Views never switch | `#tabs` buttons lost `class="tab"` or `data-view`; the click handler uses `.closest(".tab")` |
| Sidebar list empty on Home | `renderSidebarRoadmaps` not called by `renderDashboard`, or `dashboardRoadmaps` not set |
| Cards have no strip | The list response has no `stats` (route not updated, or older server); cards fall back gracefully |
| `stats.total` is 0 for the built-in roadmap | `data/roadmap.json` not loaded: check the default `require("../../data/roadmap.json")` path in the route |
| Back button does nothing | `popstate` listener not registered in `wireEvents`, or `lastHash` not updated by `navigate`/`replaceRoute` |
| Reload shows Home instead of the roadmap | `enterDashboard` is not reading `parseRoute()`; or the hash was cleared by an extra `replaceState` |
| Drawer won't close with Escape | Escape handler must also check `.nav-open` and focus `#sidebarOpenBtn` |
| Strip in the sidebar is stale | `rerender()` must end with `renderSidebarStrip()` |
| axe complains about `role="menu"` | Panels must be `role="group"` (Phase 0) — do not reintroduce `role="menu"` |
| A `step2_*.py` assertion fails | Repo drifted; apply the Intent list manually |

---

## 9. Hand-off

Report: commits, `npm test`, the three harness result lines, the static-ID-check output, and any manual deviations.

**Phase 3 assumes** these exist and are unchanged: the Home structure (`.page-head`, `.page-actions`, `.summary-bar`, `.notice-row`, `.empty-panel`, `.roadmap-grid`, `.roadmap-card`, `.rc-menu`), the functions in 5.3 (especially `renderDashboard`, `roadmapCard`, `onDashboardClick`, `dashboardRoadmaps`), the `stats` shape (3.9), the existing `openCreateRoadmapModal` / `submitCreateRoadmap` / `confirmDeleteRoadmap` / `deleteRoadmap` / `restoreBuiltinRoadmap` flows (Phase 3 replaces the dialog and the delete confirmation), `.btn*`, `.field*`, `.badge`, `.skeleton`, `MonthStrip`, and the hash routes.

**Rollback:** revert the Phase 2 commits. The only persistent change is additive (`stats` in an API response), so no data migration is needed.

---

# Appendices


## Appendix A1 — `js/roadmap-stats.js`

```javascript
/**
 * @module roadmap-stats
 * Progress summaries for a roadmap: totals by status and a per-month breakdown
 * (the data behind the Month Strip on the Home screen).
 *
 * Loaded in Node.js (via require()) by the roadmap list endpoint. UMD like
 * progress-schema.js so the browser can reuse it later. Pure functions: no
 * I/O, no clock unless `now` is passed in.
 *
 * Counting rules mirror js/app.js (`rebuildIndex` / `statsFor`):
 *   - every task and every month deliverable of the curriculum counts once;
 *   - user-added topics (progress.custom.topics) count in the month that owns
 *     their section, built-in or custom;
 *   - user-added months (progress.custom.phases) follow the built-in months;
 *   - an id missing from progress.items is "not started".
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.RoadmapStats = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const DAY_MS = 86400000;
  const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

  /**
   * @typedef {object} CurriculumMonth
   * @property {string} id
   * @property {number} number
   * @property {string} title
   * @property {string[]} taskIds     tasks and deliverables of the month
   * @property {string[]} sectionIds  sections that user-added topics can attach to
   *
   * @typedef {object} Curriculum
   * @property {string | null} defaultStartMonth  "YYYY-MM" Month 1 is authored against
   * @property {CurriculumMonth[]} months
   */

  /**
   * Reduce the full roadmap JSON (data/roadmap.json) to the ids that matter for
   * counting. Done once at server start-up.
   * @param {{ meta?: { horizonStart?: string }, phases?: object[] }} data
   * @returns {Curriculum}
   */
  function buildCurriculum(data) {
    const phases = Array.isArray(data && data.phases) ? data.phases : [];
    const horizon = data && data.meta && data.meta.horizonStart;
    return {
      defaultStartMonth: typeof horizon === "string" && /^\d{4}-\d{2}/.test(horizon) ? horizon.slice(0, 7) : null,
      months: phases.map((phase) => ({
        id: phase.id,
        number: phase.number,
        title: phase.title,
        sectionIds: (phase.sections || []).map((s) => s.id),
        taskIds: [].concat(
          ...(phase.sections || []).map((s) => [].concat(
            ...(s.topics || []).map((t) => [].concat(
              ...(t.groups || []).map((g) => (g.subtasks || []).map((st) => st.id))
            ))
          )),
          (phase.deliverables || []).map((d) => d.id)
        ),
      })),
    };
  }

  /** The empty curriculum of a custom roadmap: everything lives in progress.custom. */
  const EMPTY_CURRICULUM = Object.freeze({ defaultStartMonth: null, months: [] });

  function monthsWithTasks(curriculum, custom) {
    const base = curriculum.months.map((m) => ({
      id: m.id, number: m.number, title: m.title, ids: m.taskIds.slice(),
    }));
    const bySection = new Map();
    curriculum.months.forEach((m, i) => m.sectionIds.forEach((id) => bySection.set(id, base[i])));

    const customPhases = custom && Array.isArray(custom.phases) ? custom.phases : [];
    customPhases.forEach((p, i) => {
      const month = { id: p.id, number: base.length + 1, title: p.title || "", ids: [] };
      base.push(month);
      (Array.isArray(p.sections) ? p.sections : []).forEach((s) => bySection.set(s.id, month));
    });

    const customTopics = custom && Array.isArray(custom.topics) ? custom.topics : [];
    customTopics.forEach((topic) => {
      const month = bySection.get(topic.sectionId);
      if (!month) return; // orphaned topic: the app does not show it either
      (Array.isArray(topic.tasks) ? topic.tasks : []).forEach((task) => month.ids.push(task.id));
    });
    return base;
  }

  function tally(ids, items) {
    const out = { total: ids.length, completed: 0, inProgress: 0, blocked: 0 };
    ids.forEach((id) => {
      const item = items[id];
      const status = item && item.status;
      if (status === "completed") out.completed += 1;
      else if (status === "in_progress") out.inProgress += 1;
      else if (status === "blocked") out.blocked += 1;
    });
    return out;
  }

  /**
   * Summarise a roadmap's progress.
   * @param {Curriculum} curriculum
   * @param {object | null} progress  the stored progress blob (or null if none yet)
   * @param {{ now?: Date }} [options]
   * @returns {{
   *   total: number, completed: number, inProgress: number, blocked: number,
   *   completedLast7Days: number, startMonth: string | null,
   *   months: Array<{ number: number, id: string, title: string,
   *                   total: number, completed: number, inProgress: number, blocked: number }>
   * }}
   */
  function summarize(curriculum, progress, options) {
    const now = (options && options.now) || new Date();
    const items = progress && isObj(progress.items) ? progress.items : {};
    const custom = progress && isObj(progress.custom) ? progress.custom : null;
    const settings = progress && isObj(progress.settings) ? progress.settings : {};

    const months = monthsWithTasks(curriculum || EMPTY_CURRICULUM, custom).map((m) => ({
      number: m.number, id: m.id, title: m.title, ...tally(m.ids, items),
    }));

    const totals = months.reduce((acc, m) => ({
      total: acc.total + m.total,
      completed: acc.completed + m.completed,
      inProgress: acc.inProgress + m.inProgress,
      blocked: acc.blocked + m.blocked,
    }), { total: 0, completed: 0, inProgress: 0, blocked: 0 });

    const since = now.getTime() - 7 * DAY_MS;
    const completedLast7Days = Object.values(items).filter((it) => {
      if (!isObj(it) || typeof it.completedAt !== "string") return false;
      const t = Date.parse(it.completedAt);
      return Number.isFinite(t) && t >= since && t <= now.getTime() + DAY_MS;
    }).length;

    return {
      ...totals,
      completedLast7Days,
      startMonth: settings.startMonth || (curriculum && curriculum.defaultStartMonth) || null,
      months,
    };
  }

  return { buildCurriculum, summarize, EMPTY_CURRICULUM };
});
```

## Appendix A2 — `server/roadmaps/stats.js`

```javascript
/**
 * @module roadmaps/stats
 * Computes the per-roadmap progress summary shown on the Home screen.
 *
 * The summary is derived from the stored progress JSON, which can be large, so
 * results are cached by roadmap id and saved version. A new save bumps the
 * version, so a cached entry can never be stale with respect to progress; the
 * short TTL only keeps the "done in the last 7 days" figure fresh.
 */
"use strict";

const { buildCurriculum, summarize, EMPTY_CURRICULUM } = require("../../js/roadmap-stats");
const { BUILTIN_AI_ENGINEER } = require("./builtin");

const DEFAULT_TTL_MS = 10 * 60 * 1000;
const DEFAULT_MAX_ENTRIES = 500;

/**
 * @param {object} options
 * @param {object} options.builtinData - parsed data/roadmap.json
 * @param {number} [options.ttlMs]
 * @param {number} [options.maxEntries]
 * @param {() => number} [options.clock] - ms since epoch (injectable for tests)
 */
function createStatsService({
  builtinData, ttlMs = DEFAULT_TTL_MS, maxEntries = DEFAULT_MAX_ENTRIES, clock = Date.now,
}) {
  const curricula = { [BUILTIN_AI_ENGINEER.source]: buildCurriculum(builtinData) };
  /** @type {Map<string, { at: number, stats: object }>} */
  const cache = new Map();

  function curriculumFor(source) {
    return curricula[source] || EMPTY_CURRICULUM;
  }

  function remember(key, stats) {
    if (cache.size >= maxEntries) cache.delete(cache.keys().next().value); // oldest first
    cache.set(key, { at: clock(), stats });
  }

  /**
   * @param {{ id: number, source: string, progressData: string | null, progressVersion: number | null }} row
   * @returns {object | null} the summary, or null if the stored data cannot be read
   */
  function forRoadmap(row) {
    const curriculum = curriculumFor(row.source);
    const now = new Date(clock());
    if (row.progressData == null) return summarize(curriculum, null, { now });

    const key = `${row.id}:${row.progressVersion}`;
    const hit = cache.get(key);
    if (hit && clock() - hit.at < ttlMs) return hit.stats;

    let progress;
    try {
      progress = JSON.parse(row.progressData);
    } catch {
      return null; // corrupt blob: the roadmap still lists, just without numbers
    }
    const stats = summarize(curriculum, progress, { now });
    remember(key, stats);
    return stats;
  }

  return { forRoadmap, cacheSize: () => cache.size };
}

module.exports = { createStatsService };
```

## Appendix A3 — `test/stats.test.js`

```javascript
const { test, describe, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { buildCurriculum, summarize, EMPTY_CURRICULUM } = require("../js/roadmap-stats");
const { createStatsService } = require("../server/roadmaps/stats");
const { startServer, client, creds, dp } = require("./helpers");
const builtin = require("../data/roadmap.json");

// A tiny curriculum: month 1 has 3 tasks + 1 deliverable, month 2 has 1 task.
const SMALL = {
  meta: { horizonStart: "2026-10-01" },
  phases: [
    {
      id: "m1", number: 1, title: "One",
      sections: [{ id: "m1-s1", topics: [{ groups: [{ subtasks: [{ id: "a" }, { id: "b" }] }, { subtasks: [{ id: "c" }] }] }] }],
      deliverables: [{ id: "d1" }],
    },
    { id: "m2", number: 2, title: "Two", sections: [{ id: "m2-s1", topics: [{ groups: [{ subtasks: [{ id: "e" }] }] }] }], deliverables: [] },
  ],
};
const curriculum = buildCurriculum(SMALL);
const empty = () => ({ items: {}, counters: {}, celebratedPhases: [], settings: {}, custom: { topics: [], phases: [] } });

describe("roadmap-stats: summarize", () => {
  test("counts every task and deliverable once, per month and in total", () => {
    const s = summarize(curriculum, null);
    assert.equal(s.total, 5);
    assert.deepEqual(s.months.map((m) => [m.number, m.total]), [[1, 4], [2, 1]]);
    assert.equal(s.completed + s.inProgress + s.blocked, 0);
    assert.equal(s.startMonth, "2026-10");
  });

  test("counts each status; ids missing from items are not started", () => {
    const p = empty();
    p.items = { a: { status: "completed" }, b: { status: "in_progress" }, d1: { status: "blocked" }, e: { status: "completed" } };
    const s = summarize(curriculum, p);
    assert.deepEqual([s.completed, s.inProgress, s.blocked], [2, 1, 1]);
    assert.deepEqual(s.months[0], { number: 1, id: "m1", title: "One", total: 4, completed: 1, inProgress: 1, blocked: 1 });
    assert.equal(s.months[1].completed, 1);
  });

  test("user-added topics count in the month that owns their section", () => {
    const p = empty();
    p.custom.topics = [{ id: "t1", sectionId: "m2-s1", title: "x", tasks: [{ id: "x1" }, { id: "x2" }] }];
    p.items = { x1: { status: "completed" } };
    const s = summarize(curriculum, p);
    assert.equal(s.total, 7);
    assert.equal(s.months[1].total, 3);
    assert.equal(s.months[1].completed, 1);
  });

  test("user-added months follow the built-in months and own their topics", () => {
    const p = empty();
    p.custom.phases = [{ id: "cm1", title: "Extra", sections: [{ id: "cs1" }] }];
    p.custom.topics = [{ id: "t9", sectionId: "cs1", title: "y", tasks: [{ id: "y1" }] }];
    const s = summarize(curriculum, p);
    assert.equal(s.months.length, 3);
    assert.deepEqual([s.months[2].number, s.months[2].title, s.months[2].total], [3, "Extra", 1]);
  });

  test("a topic whose section no longer exists is ignored (the app does not show it)", () => {
    const p = empty();
    p.custom.topics = [{ id: "t", sectionId: "gone", title: "z", tasks: [{ id: "z1" }] }];
    assert.equal(summarize(curriculum, p).total, 5);
  });

  test("a custom roadmap with no months has no totals and no months", () => {
    const s = summarize(EMPTY_CURRICULUM, empty());
    assert.equal(s.total, 0);
    assert.deepEqual(s.months, []);
    assert.equal(s.startMonth, null);
  });

  test("startMonth: the saved setting wins over the authored default", () => {
    const p = empty();
    p.settings.startMonth = "2027-01";
    assert.equal(summarize(curriculum, p).startMonth, "2027-01");
  });

  test("completedLast7Days counts recent completions only", () => {
    const now = new Date("2026-11-04T12:00:00Z");
    const p = empty();
    p.items = {
      a: { status: "completed", completedAt: "2026-11-03T08:00:00Z" },
      b: { status: "completed", completedAt: "2026-10-20T08:00:00Z" },
      c: { status: "completed", completedAt: "not a date" },
      d1: { status: "completed", completedAt: null },
    };
    assert.equal(summarize(curriculum, p, { now }).completedLast7Days, 1);
  });

  test("malformed progress shapes do not throw", () => {
    assert.doesNotThrow(() => summarize(curriculum, { items: [], custom: { phases: "x", topics: 5 }, settings: null }));
  });

  test("the built-in roadmap has 10 months and 849 trackable items", () => {
    const s = summarize(buildCurriculum(builtin), null);
    assert.equal(s.months.length, 10);
    assert.equal(s.total, 849);
    assert.equal(s.startMonth, "2026-10");
  });
});

describe("stats service cache", () => {
  const row = (extra) => ({ id: 1, source: "builtin_ai_engineer", progressVersion: 1, progressData: JSON.stringify(empty()), ...extra });

  test("reuses a result for the same roadmap and version, recomputes after a new version", () => {
    const svc = createStatsService({ builtinData: builtin });
    const a = svc.forRoadmap(row());
    assert.equal(svc.forRoadmap(row()), a);
    assert.notEqual(svc.forRoadmap(row({ progressVersion: 2 })), a);
    assert.equal(svc.cacheSize(), 2);
  });

  test("expires entries after the TTL", () => {
    let now = 1_000_000;
    const svc = createStatsService({ builtinData: builtin, ttlMs: 1000, clock: () => now });
    const a = svc.forRoadmap(row());
    now += 2000;
    assert.notEqual(svc.forRoadmap(row()), a);
  });

  test("never grows past maxEntries", () => {
    const svc = createStatsService({ builtinData: builtin, maxEntries: 3 });
    for (let i = 1; i <= 10; i++) svc.forRoadmap(row({ id: i }));
    assert.equal(svc.cacheSize(), 3);
  });

  test("a roadmap with no saved progress is summarised without caching", () => {
    const svc = createStatsService({ builtinData: builtin });
    const s = svc.forRoadmap(row({ progressData: null, progressVersion: null }));
    assert.equal(s.total, 849);
    assert.equal(svc.cacheSize(), 0);
  });

  test("corrupt stored JSON gives null instead of throwing", () => {
    const svc = createStatsService({ builtinData: builtin });
    assert.equal(svc.forRoadmap(row({ progressData: "{not json" })), null);
  });

  test("an unknown source is treated as an empty custom roadmap", () => {
    const svc = createStatsService({ builtinData: builtin });
    assert.equal(svc.forRoadmap(row({ source: "custom", progressData: null, progressVersion: null })).total, 0);
  });
});

describe("GET /api/roadmaps includes stats", () => {
  let srv;
  before(async () => { srv = await startServer(); });
  after(async () => { await srv.close(); srv.db.close(); });

  async function register(name) {
    const c = client(srv.base);
    assert.equal((await c.post("/api/auth/register", creds(name))).status, 201);
    return c;
  }

  test("a new account's built-in roadmap reports 849 not-started items over 10 months", async () => {
    const c = await register("stats_new");
    const [r] = (await c.get("/api/roadmaps")).body.roadmaps;
    assert.equal(r.stats.total, 849);
    assert.equal(r.stats.completed, 0);
    assert.equal(r.stats.months.length, 10);
    assert.equal(r.stats.startMonth, "2026-10");
  });

  test("stats follow saved progress and never expose the raw progress blob", async () => {
    const c = await register("stats_saved");
    const path = await dp(c);
    const first = builtin.phases[0].sections[0].topics[0].groups[0].subtasks[0].id;
    const data = empty();
    data.items[first] = { status: "completed", completedAt: new Date().toISOString() };
    data.settings.startMonth = "2027-02";
    assert.equal((await c.put(path, { data, version: 0 })).status, 200);

    const res = await c.get("/api/roadmaps");
    const [r] = res.body.roadmaps;
    assert.equal(r.stats.completed, 1);
    assert.equal(r.stats.months[0].completed, 1);
    assert.equal(r.stats.completedLast7Days, 1);
    assert.equal(r.stats.startMonth, "2027-02");
    assert.equal("progressData" in r || "data" in r || "progressVersion" in r, false);
    assert.doesNotMatch(res.text, /celebratedPhases/);
  });

  test("a custom roadmap with a topic reports that topic's tasks", async () => {
    const c = await register("stats_custom");
    const created = await c.post("/api/roadmaps", { name: "Mine" });
    const id = created.body.roadmap.id;
    const data = empty();
    data.custom.phases = [{ id: "cm1", title: "M1", sections: [{ id: "cs1", title: "S" }] }];
    data.custom.topics = [{ id: "ct1", sectionId: "cs1", title: "T", tasks: [{ id: "k1", title: "a" }, { id: "k2", title: "b" }] }];
    data.items = { k1: { status: "completed" } };
    assert.equal((await c.put(`/api/roadmaps/${id}/progress`, { data, version: 0 })).status, 200);
    const mine = (await c.get("/api/roadmaps")).body.roadmaps.find((r) => r.id === id);
    assert.deepEqual([mine.stats.total, mine.stats.completed, mine.stats.months.length], [2, 1, 1]);
  });

  test("one user's progress never leaks into another user's list", async () => {
    const a = await register("stats_iso_a");
    const b = await register("stats_iso_b");
    const data = empty();
    data.items[builtin.phases[0].deliverables[0].id] = { status: "completed" };
    assert.equal((await a.put(await dp(a), { data, version: 0 })).status, 200);
    assert.equal((await b.get("/api/roadmaps")).body.roadmaps[0].stats.completed, 0);
  });
});
```

## Appendix A4 — `css/shell.css`

```css
/* ===========================================================
   App shell: sidebar, top bar, page container, menus' anchors.
   Desktop (>=1024px): fixed sidebar, 248px (64px collapsed).
   Below 1024px the sidebar becomes an off-canvas drawer.
   =========================================================== */

.app-shell { display: grid; grid-template-columns: 248px minmax(0, 1fr); min-height: 100vh; }
.app-shell.is-collapsed { grid-template-columns: 64px minmax(0, 1fr); }
body.locked .app-shell { display: none; }

.app-body { min-width: 0; display: flex; flex-direction: column; }
.page { flex: 1; min-width: 0; }
.page-inner { max-width: 1600px; margin: 0 auto; padding: 24px 32px 64px; }

/* Context switching: Home shows one set of controls, a roadmap another. */
.app-shell[data-context="home"] .roadmap-only { display: none !important; }

/* ---------------- Sidebar ---------------- */
.sidebar {
  position: sticky; top: 0; height: 100vh; z-index: 30;
  display: flex; flex-direction: column; overflow: hidden auto;
  background: var(--bg-brand); color: rgb(255 255 255 / 0.86);
  border-right: 1px solid rgb(255 255 255 / 0.06);
  /* Accent tuned for a dark surface in both themes */
  --nav-accent: #8aa3ff;
}
.sidebar-head { display: flex; align-items: center; gap: 10px; height: 56px; padding: 0 16px; flex-shrink: 0; font-size: 15px; font-weight: 600; color: #fff; }
.sidebar-head .brand-mark { box-shadow: 0 0 0 1px rgb(255 255 255 / 0.18); }
.sidebar-nav { flex: 1; padding: 8px 12px; overflow-y: auto; }
.sidebar-section { display: flex; flex-direction: column; gap: 2px; }
.nav-heading { margin: 20px 12px 6px; font-size: 12px; font-weight: 500; color: rgb(255 255 255 / 0.55); }

.nav-list { display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 10px; width: 100%; min-height: 36px; padding: 6px 12px;
  border: 0; border-radius: var(--radius-sm); background: transparent; color: inherit;
  font-size: 14px; font-weight: 500; text-align: left; position: relative;
  transition: background 0.12s ease;
}
.nav-item:hover { background: rgb(255 255 255 / 0.08); color: #fff; }
.nav-item.active, .nav-item[aria-current="page"] { background: rgb(255 255 255 / 0.12); color: #fff; }
.nav-item.active::before, .nav-item[aria-current="page"]::before {
  content: ""; position: absolute; left: -12px; top: 6px; bottom: 6px; width: 3px; border-radius: 0 3px 3px 0; background: var(--nav-accent);
}
.sidebar :focus-visible { outline-color: #fff; }
.nav-icon { display: inline-flex; flex-shrink: 0; width: 20px; height: 20px; align-items: center; justify-content: center; }
.nav-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Roadmap switcher entries on Home */
.nav-roadmap { flex-direction: column; align-items: stretch; gap: 8px; padding: 8px 12px; }
.nav-roadmap-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; min-width: 0; }
.nav-roadmap-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.nav-roadmap-pct { flex-shrink: 0; font-size: 12px; color: rgb(255 255 255 / 0.6); font-variant-numeric: tabular-nums; }
.nav-empty { margin: 4px 12px; font-size: 13px; color: rgb(255 255 255 / 0.55); }

/* Dark surface: strips need their own track and status colours */
.sidebar .strip-seg { background: rgb(255 255 255 / 0.12); box-shadow: none; }
.sidebar { --status-completed: #3dbe84; --status-in-progress: #e0a33a; --status-blocked: #f0716a; }

.sidebar-roadmap-card { margin: 12px 0 0; padding: 12px; border-radius: var(--radius-md); background: rgb(255 255 255 / 0.06); border: 1px solid rgb(255 255 255 / 0.1); }
.sidebar-roadmap-name { margin: 0; font-size: 14px; font-weight: 600; color: #fff; line-height: 20px; overflow-wrap: anywhere; }
.sidebar-roadmap-desc { margin: 4px 0 0; font-size: 12px; line-height: 16px; color: rgb(255 255 255 / 0.62); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.sidebar-roadmap-desc:empty { display: none; }
.sidebar-strip { margin-top: 12px; }

.sidebar-foot { padding: 8px 12px 12px; border-top: 1px solid rgb(255 255 255 / 0.08); flex-shrink: 0; display: flex; flex-direction: column; gap: 2px; }

/* Collapsed (desktop only): icons with tooltips */
.app-shell.is-collapsed .nav-label,
.app-shell.is-collapsed .nav-heading,
.app-shell.is-collapsed .sidebar-brand-text,
.app-shell.is-collapsed .sidebar-roadmap-card,
.app-shell.is-collapsed #sidebarRoadmapList { display: none; }
.app-shell.is-collapsed .sidebar-head { justify-content: center; padding: 0; }
.app-shell.is-collapsed .sidebar-nav { padding: 8px; }
.app-shell.is-collapsed .nav-item { justify-content: center; padding: 6px; }
.app-shell.is-collapsed .nav-item.active::before, .app-shell.is-collapsed .nav-item[aria-current="page"]::before { left: -8px; }
.app-shell.is-collapsed .sidebar-foot { padding: 8px; }
.app-shell.is-collapsed .sidebar-collapse-btn .nav-icon { transform: scaleX(-1); }

/* ---------------- Top bar ---------------- */
.topbar {
  position: sticky; top: 0; z-index: 20; min-height: 56px;
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; padding: 8px 24px;
  background: var(--bg-elevated); border-bottom: 1px solid var(--border);
}
.topbar-menu-btn { display: none; }
.breadcrumb { min-width: 0; }
.breadcrumb ol { display: flex; align-items: center; margin: 0; padding: 0; list-style: none; font-size: 14px; color: var(--text-muted); min-width: 0; }
.breadcrumb li { display: flex; align-items: center; min-width: 0; }
.breadcrumb li + li::before { content: "/"; margin: 0 8px; color: var(--text-faint); }
.crumb-current { font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 36ch; }
.topbar-actions { margin-left: auto; display: flex; align-items: center; gap: 10px; min-width: 0; }

.roadmap-search {
  width: 260px; min-height: 36px; padding: 0 12px;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
  background: var(--bg-elevated); color: var(--text); font-size: 14px;
}
.roadmap-search:focus { border-color: var(--accent); }

/* Save status chip (roadmap only) */
.save-status {
  display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border: 0; border-radius: 99px;
  background: var(--bg-sunken); color: var(--text-muted); font-size: 13px; font-weight: 500; white-space: nowrap;
  cursor: default;
}
.save-status:empty { display: none; }
.save-status::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.save-status.saving { color: var(--status-in-progress); background: var(--status-in-progress-bg); }
.save-status.saved { color: var(--status-completed); background: var(--status-completed-bg); }
.save-status.error, .save-status.conflict { color: var(--status-blocked); background: var(--status-blocked-bg); cursor: pointer; text-decoration: none; }
.save-status.error:hover, .save-status.conflict:hover { text-decoration: underline; }

.profile-trigger .avatar { width: 24px; height: 24px; font-size: 11px; }
.profile-trigger .nav-icon { width: 16px; height: 16px; }

/* ---------------- Drawer (below 1024px) ---------------- */
@media (max-width: 1023px) {
  .app-shell, .app-shell.is-collapsed { grid-template-columns: minmax(0, 1fr); }
  .sidebar {
    position: fixed; inset: 0 auto 0 0; width: 280px; max-width: 86vw; z-index: 60;
    transform: translateX(-100%); transition: transform 0.16s ease; box-shadow: var(--shadow-lg);
  }
  .app-shell.nav-open .sidebar { transform: none; }
  .sidebar-scrim { position: fixed; inset: 0; z-index: 55; background: rgb(8 17 31 / 0.55); }
  .sidebar-scrim[hidden] { display: none; }
  .topbar-menu-btn { display: inline-flex; }
  .sidebar-collapse-btn { display: none; }
  /* The drawer is always expanded */
  .app-shell.is-collapsed .nav-label, .app-shell.is-collapsed .nav-heading, .app-shell.is-collapsed .sidebar-brand-text,
  .app-shell.is-collapsed .sidebar-roadmap-card { display: revert; }
  .app-shell.is-collapsed #sidebarRoadmapList { display: flex; }
  .page-inner { padding: 20px 24px 56px; }
}
@media (max-width: 639px) {
  .topbar { padding: 8px 12px; }
  .page-inner { padding: 16px 12px 48px; }
  .roadmap-search { order: 10; flex: 1 1 100%; width: auto; }
  .topbar-actions { flex-wrap: wrap; justify-content: flex-end; }
  .roadmap-trigger-label, .profile-trigger-name { display: none; }
  .crumb-current { max-width: 18ch; }
}

/* Breadcrumb link back to Home */
.crumb-link {
  padding: 0; border: 0; background: none; font-size: 14px; color: var(--text-muted);
  text-decoration: none; border-radius: 3px;
}
.crumb-link:hover { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }

/* While a roadmap loads, the view list cannot be used yet */
#tabs.is-loading { opacity: 0.5; pointer-events: none; }

/* About dialog */
.about-text { margin: 0 0 12px; color: var(--text-muted); }
.about-list { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; font-size: 14px; }
.about-list a { color: var(--accent); }
```

## Appendix A5 — `css/home.css`

```css
/* ===========================================================
   Home screen: roadmap list.
   =========================================================== */

.page-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 24px; line-height: 32px; letter-spacing: -0.01em; }
.page-lead { margin: 4px 0 0; font-size: 14px; color: var(--text-muted); }
.page-actions { display: flex; align-items: center; gap: 8px; }
.btn .icon { flex-shrink: 0; }

/* Summary: one panel, four inline metrics */
.summary-bar {
  display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md);
  margin-bottom: 24px;
}
.summary-item { padding: 16px 20px; min-width: 0; }
.summary-item + .summary-item { border-left: 1px solid var(--border); }
.summary-label { margin: 0; font-size: 13px; color: var(--text-muted); }
.summary-value { margin: 4px 0 0; font-size: 22px; line-height: 28px; font-weight: 600; letter-spacing: -0.01em; font-variant-numeric: tabular-nums; }
.summary-value small { font-size: 14px; font-weight: 400; color: var(--text-faint); }
@media (max-width: 767px) {
  .summary-bar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-item:nth-child(3) { border-left: 0; }
  .summary-item:nth-child(n + 3) { border-top: 1px solid var(--border); }
}

.notice-row {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  padding: 12px 16px; margin-bottom: 20px; border-radius: var(--radius-md);
  background: var(--accent-soft); border: 1px solid var(--border); font-size: 14px;
}

/* Cards */
.roadmap-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
@media (max-width: 400px) { .roadmap-grid { grid-template-columns: minmax(0, 1fr); } }
.roadmap-card {
  display: flex; flex-direction: column; gap: 14px; padding: 20px; cursor: pointer;
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md);
  transition: border-color 0.12s ease;
}
.roadmap-card:hover { border-color: var(--border-strong); }
.rc-head { display: flex; align-items: flex-start; gap: 8px; }
.rc-title { margin: 0; flex: 1; min-width: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.005em; overflow-wrap: anywhere; }
.rc-badge { flex-shrink: 0; margin-top: 2px; background: var(--bg-sunken); color: var(--text-muted); }
.roadmap-card-desc { margin: -6px 0 0; font-size: 13px; line-height: 18px; color: var(--text-muted); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 36px; }
.rc-progress { display: flex; flex-direction: column; gap: 8px; }
.rc-meta { display: flex; justify-content: space-between; gap: 12px; margin: 0; font-size: 13px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.rc-meta strong { color: var(--text); font-weight: 600; }
.rc-foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: auto; padding-top: 14px; border-top: 1px solid var(--border); }
.roadmap-card-meta { margin: 0; font-size: 13px; color: var(--text-faint); }

/* Per-card overflow menu */
.rc-menu { position: relative; flex-shrink: 0; margin: -4px -8px 0 0; }
.rc-menu-panel {
  position: absolute; top: calc(100% + 4px); right: 0; z-index: 10; min-width: 200px; padding: 4px;
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-md);
}
.rc-menu-panel .profile-action-btn { display: flex; align-items: center; gap: 8px; }

.dashboard-status { font-size: 14px; color: var(--text-muted); padding: 40px 0; text-align: center; }
.dashboard-status .btn { margin-top: 12px; }

.empty-panel {
  max-width: 520px; margin: 48px auto; padding: 32px; text-align: center;
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md);
}
.empty-panel h2 { margin: 0 0 8px; font-size: 18px; }
.empty-panel p { margin: 0 0 20px; color: var(--text-muted); }
.empty-panel .page-actions { justify-content: center; flex-wrap: wrap; }

/* Loading skeleton cards (same footprint as real cards) */
.roadmap-card.is-skeleton { cursor: default; pointer-events: none; }
.roadmap-card.is-skeleton .skeleton + .skeleton { margin-top: 10px; }
```

## Appendix B1 — `step2_server.py` (Task 4)

Run from the repo root: `python3 step2_server.py`.

```python
"""Phase 2 / backend wiring: repository + list route. Run from the repo root: python3 step2_server.py
(New files js/roadmap-stats.js, server/roadmaps/stats.js and test/stats.test.js are created separately.)"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match ({s.count(old)} found) for: {old[:80]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("server/roadmaps/repository.js", [
    ("""  /** @returns {Promise<RoadmapRow | undefined>} */
  async function findOwned(""",
     """  /**
   * Like listForUser, plus each roadmap's stored progress (raw JSON text and
   * version) so the caller can summarise it. Callers must not expose the raw
   * progress to clients.
   * @returns {Promise<Array<RoadmapRow & { progressData: string | null, progressVersion: number | null }>>}
   */
  async function listWithProgress(userId) {
    const result = await db.execute({
      sql: `SELECT r.id, r.name, r.description, r.source, r.created_at,
                   p.updated_at AS last_activity_at, p.data AS progress_data, p.version AS progress_version
            FROM roadmaps r LEFT JOIN roadmap_progress p ON p.roadmap_id = r.id
            WHERE r.user_id = ?
            ORDER BY r.created_at, r.id`,
      args: [userId],
    });
    return result.rows.map((row) => ({
      ...toRoadmap(row),
      lastActivityAt: row.last_activity_at == null ? null : String(row.last_activity_at),
      progressData: row.progress_data == null ? null : String(row.progress_data),
      progressVersion: row.progress_version == null ? null : Number(row.progress_version),
    }));
  }

  /** @returns {Promise<RoadmapRow | undefined>} */
  async function findOwned("""),
    ("    listForUser, findOwned, countForUser,", "    listForUser, listWithProgress, findOwned, countForUser,"),
])

patch("server/routes/roadmaps.js", [
    ('const { emptyProgress } = require("../roadmaps/progress");',
     'const { emptyProgress } = require("../roadmaps/progress");\nconst { createStatsService } = require("../roadmaps/stats");'),
    (""" * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 */""",
     """ * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 * @property {object} [builtinData] - Parsed data/roadmap.json (defaults to the bundled file).
 */"""),
    ("""function createRoadmapsRouter({ db, requireAuth }) {
  const router = express.Router();
  const repo = createRoadmapRepository(db);""",
     """function createRoadmapsRouter({ db, requireAuth, builtinData = require("../../data/roadmap.json") }) {
  const router = express.Router();
  const repo = createRoadmapRepository(db);
  const stats = createStatsService({ builtinData });"""),
    ("""  router.get("/", async (req, res) => {
    res.json({ roadmaps: await repo.listForUser(req.user.id) });
  });""",
     """  // Each roadmap carries `stats` (totals and a per-month breakdown) so the Home
  // screen can show progress without loading every roadmap's full progress.
  // The raw progress JSON is never included.
  router.get("/", async (req, res) => {
    const rows = await repo.listWithProgress(req.user.id);
    const roadmaps = rows.map(({ progressData, progressVersion, ...roadmap }) => ({
      ...roadmap,
      stats: stats.forRoadmap({
        id: roadmap.id, source: roadmap.source, progressData, progressVersion,
      }),
    }));
    res.json({ roadmaps });
  });"""),
])
print("server/roadmaps/repository.js and server/routes/roadmaps.js updated")
```

## Appendix B2 — `step2_misc.py` (Task 6)

Run from the repo root: `python3 step2_misc.py`.

```python
"""Phase 2 / small additions to Phase 0 files: five more icons and the .sr-only utility.
Run from the repo root: python3 step2_misc.py"""

ICONS = r'''    columns: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>',
    "list-checks": '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    award: '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    "book-open": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
'''

P = "js/icons.js"
s = open(P, encoding="utf-8").read()
marker = "    help: '<circle"
assert s.count(marker) == 1, "icon marker not found"
assert "columns:" not in s, "icons already added"
s = s.replace(marker, ICONS + marker)
open(P, "w", encoding="utf-8").write(s)

P = "css/base.css"
s = open(P, encoding="utf-8").read()
old = ".hidden { display: none !important; }"
assert s.count(old) == 1 and ".sr-only" not in s
s = s.replace(old, old + """
.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}""")
open(P, "w", encoding="utf-8").write(s)
print("js/icons.js and css/base.css updated")
```

## Appendix B3 — `step2_styles.py` (Task 8)

Run from the repo root: `python3 step2_styles.py`.

```python
"""Phase 2 / css/styles.css: remove the old header, tabs and roadmap-dashboard rules
(they are replaced by css/shell.css and css/home.css). Run from the repo root: python3 step2_styles.py"""
import re

P = "css/styles.css"
s = open(P, encoding="utf-8").read()


def cut(start, end):
    """Delete from `start` up to (not including) `end`; both markers must exist once."""
    global s
    assert s.count(start) == 1, "start marker not unique/found: " + start[:60]
    a = s.index(start)
    assert end in s[a:], "end marker not found after start: " + end[:60]
    b = s.index(end, a)
    s = s[:a] + s[b:]


# 1. Old header (brand, subtitle, header-actions, save-status)
cut("/* ---------------- Header ---------------- */", "/* ── Profile Anchor")
# 2. Old tab row and the bare `main` rule
cut("\n.tabs-row {\n", "/* ---------------- Generic card / grid ---------------- */")  # (a mobile rule also starts with ".tabs-row {")
# 3. Old roadmap dashboard (cards, bar, grid, action tiles, coming-soon badge)
cut("/* ---------------- Roadmap dashboard ---------------- */", "/* ---------------- Custom roadmaps ---------------- */")

# 4. Leftovers
s = re.sub(r"\.header-actions \{[^}]*\}\n", "", s)
s = re.sub(r"\.save-status \{[^}]*\}\n\.save-status:empty \{[^}]*\}\n(\.save-status\.[^\n]*\n)+", "", s)
old_locked = "body.locked .app-header, body.locked main { display: none; }\n"
assert s.count(old_locked) == 1, "locked rule not found"
s = s.replace(old_locked, "")  # css/shell.css hides the shell while locked
mobile = ("  .tabs-row { flex-wrap: wrap; gap: 0; }\n  .tabs { flex-basis: 100%; }\n"
          "  .roadmap-search { flex: 1 1 100%; margin: 4px 0 8px; }\n  .header-inner { padding: 12px 14px 8px; }\n"
          "  .brand h1 { font-size: 15px; }\n  .brand .subtitle { display: none; }\n  main { padding: 14px 12px 70px; }\n")
assert s.count(mobile) == 1, "old mobile header rules not found"
s = s.replace(mobile, "")

open(P, "w", encoding="utf-8").write(s)
for gone in (".app-header", ".tabs-row", ".dashboard-bar", ".roadmap-grid", ".header-inner", ".back-btn", ".coming-soon-badge"):
    assert gone not in s, "still present: " + gone
print("css/styles.css:", len(s.splitlines()), "lines")
```

## Appendix B4 — `step2_index.py` (Task 9)

Run from the repo root: `python3 step2_index.py`. The shell markup is embedded in this script.

```python
"""Phase 2 / index.html: replace the old dashboard overlay, app header and <main> with the app shell.
Run from the repo root: python3 step2_index.py"""
P = "index.html"
s = open(P, encoding="utf-8").read()

NEW_SHELL = r'''<div id="appShell" class="app-shell" data-context="home">
  <aside id="sidebar" class="sidebar" aria-label="Sidebar">
    <div class="sidebar-head">
      <img class="brand-mark" src="img/logo.svg" alt="" width="28" height="28" />
      <span class="sidebar-brand-text">Roadmap Tracker</span>
    </div>

    <nav class="sidebar-nav" aria-label="Primary">
      <!-- Home: switcher between roadmaps -->
      <div id="sidebarHome" class="sidebar-section">
        <button type="button" class="nav-item active" data-nav="home" aria-current="page" title="Roadmaps">
          <span class="nav-icon" data-icon="map"></span><span class="nav-label">Roadmaps</span>
        </button>
        <p class="nav-heading">Your roadmaps</p>
        <div id="sidebarRoadmapList" class="nav-list"></div>
      </div>

      <!-- Inside a roadmap: back link, roadmap card, views -->
      <div id="sidebarRoadmap" class="sidebar-section hidden">
        <button type="button" id="backToDashboardBtn" class="nav-item" title="All roadmaps">
          <span class="nav-icon" data-icon="arrow-left"></span><span class="nav-label">All roadmaps</span>
        </button>
        <div class="sidebar-roadmap-card">
          <p id="roadmapTitle" class="sidebar-roadmap-name">Roadmap</p>
          <p id="roadmapSubtitle" class="sidebar-roadmap-desc"></p>
          <div id="sidebarStrip" class="sidebar-strip"></div>
        </div>
        <p class="nav-heading">Views</p>
        <div id="tabs" class="nav-list">
          <button type="button" class="tab nav-item active" data-view="overview" title="Overview"><span class="nav-icon" data-icon="layout-grid"></span><span class="nav-label">Overview</span></button>
          <button type="button" class="tab nav-item" data-view="timeline" title="Timeline"><span class="nav-icon" data-icon="calendar"></span><span class="nav-label">Timeline</span></button>
          <button type="button" class="tab nav-item" data-view="kanban" title="Kanban"><span class="nav-icon" data-icon="columns"></span><span class="nav-label">Kanban</span></button>
          <button type="button" class="tab nav-item" data-view="checklist" title="Checklist"><span class="nav-icon" data-icon="list-checks"></span><span class="nav-label">Checklist</span></button>
          <button type="button" class="tab nav-item" data-view="thisweek" title="This week"><span class="nav-icon" data-icon="clock"></span><span class="nav-label">This week</span></button>
          <button type="button" class="tab nav-item" data-view="mastery" title="Skills checklist"><span class="nav-icon" data-icon="award"></span><span class="nav-label">Skills checklist</span></button>
          <button type="button" class="tab nav-item" data-view="reference" title="Reference"><span class="nav-icon" data-icon="book-open"></span><span class="nav-label">Reference</span></button>
        </div>
      </div>
    </nav>

    <div class="sidebar-foot">
      <button type="button" class="nav-item" data-action="about" title="About Roadmap Tracker">
        <span class="nav-icon" data-icon="help"></span><span class="nav-label">About</span>
      </button>
      <button type="button" id="sidebarCollapseBtn" class="nav-item sidebar-collapse-btn" aria-pressed="false" title="Collapse sidebar">
        <span class="nav-icon" data-icon="panel-left"></span><span class="nav-label">Collapse</span>
      </button>
    </div>
  </aside>
  <div id="sidebarScrim" class="sidebar-scrim" hidden></div>

  <div class="app-body">
    <header class="topbar">
      <button type="button" id="sidebarOpenBtn" class="btn btn-ghost btn-icon topbar-menu-btn" aria-label="Open navigation" aria-expanded="false" aria-controls="sidebar"></button>
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li id="crumbHome"><span class="crumb-current">Roadmaps</span></li>
          <li id="crumbRoadmap" class="hidden"><span id="crumbRoadmapName" class="crumb-current" aria-current="page"></span></li>
        </ol>
      </nav>
      <div class="topbar-actions">
        <input type="search" id="roadmapSearch" class="roadmap-search roadmap-only" placeholder="Search topics, tasks, notes…" aria-label="Search tasks" autocomplete="off" />
        <button type="button" id="panelSaveStatus" class="save-status roadmap-only" aria-live="polite"></button>
        <div class="profile-anchor roadmap-only">
          <button class="profile-trigger" id="roadmapMenuTrigger" aria-expanded="false" aria-controls="roadmapMenuPanel" aria-label="Roadmap settings">
            <span class="nav-icon" data-icon="settings"></span>
            <span class="roadmap-trigger-label">Roadmap</span>
            <span class="profile-trigger-caret" data-icon="chevron-down" aria-hidden="true"></span>
          </button>
          <div class="profile-panel hidden" id="roadmapMenuPanel" role="group" aria-label="Roadmap settings">
            <div class="profile-panel-header">
              <span class="profile-panel-fullname" id="roadmapMenuName">—</span>
              <span class="profile-panel-username">Roadmap settings</span>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn" id="startMonthBtn">Set start month…</button>
              <button class="profile-action-btn" id="exportBtn">Export progress (JSON)</button>
              <button class="profile-action-btn" id="importBtn">Import progress (JSON)</button>
              <input type="file" id="importFile" accept="application/json" class="hidden" />
              <button id="legacyImportBtn" class="profile-action-btn hidden">Import old data from this browser…</button>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn danger" id="resetBtn">Reset progress…</button>
            </div>
          </div>
        </div>
        <div class="profile-anchor" id="profileAnchor">
          <button class="profile-trigger" id="profileTrigger" aria-expanded="false" aria-controls="profilePanel" aria-label="Account menu">
            <span class="avatar" id="profileAvatar" aria-hidden="true">?</span>
            <span class="profile-trigger-name" id="profileName">—</span>
            <span class="profile-trigger-caret" data-icon="chevron-down" aria-hidden="true"></span>
          </button>
          <div class="profile-panel hidden" id="profilePanel" role="group" aria-label="Account">
            <div class="profile-panel-header">
              <span class="profile-panel-fullname" id="panelFullName">—</span>
              <span class="profile-panel-username" id="panelUsername">—</span>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <span class="profile-panel-label">Appearance</span>
              <div class="profile-theme-btns">
                <button class="profile-theme-btn" id="themeLightBtn" data-theme="light">Light</button>
                <button class="profile-theme-btn" id="themeDarkBtn" data-theme="dark">Dark</button>
                <button class="profile-theme-btn" id="themeSystemBtn" data-theme="system">System</button>
              </div>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn" data-action="about">About Roadmap Tracker</button>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn profile-logout" id="logoutBtn">Log out</button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <div id="dashboardScreen" class="page hidden">
      <div class="page-inner" id="dashboardContent" aria-live="polite"></div>
    </div>
    <div id="roadmapScreen" class="page hidden">
      <h1 class="sr-only" id="roadmapH1">Roadmap</h1>
      <main id="main" class="page-inner"></main>
    </div>
  </div>
</div>
'''

start = '<div id="dashboardScreen"'
end = '<div id="toastHost"'
assert s.count(start) == 1 and s.count(end) == 1, "dashboardScreen/toastHost markers not found"
a, b = s.index(start), s.index(end)
removed = s[a:b]
for gone in ('id="roadmapTitle"', 'id="tabs"', 'id="roadmapSearch"', 'id="panelSaveStatus"', 'id="profileAnchor"', 'id="main"'):
    assert gone in removed, "expected to replace an element that is not there: " + gone
s = s[:a] + NEW_SHELL.rstrip("\n") + "\n\n" + s[b:]

old = '<link rel="stylesheet" href="css/auth.css" />'
assert s.count(old) == 1
s = s.replace(old, old + '\n<link rel="stylesheet" href="css/shell.css" />\n<link rel="stylesheet" href="css/home.css" />')

open(P, "w", encoding="utf-8").write(s)
for required in ('id="appShell"', 'id="sidebar"', 'id="sidebarHome"', 'id="sidebarRoadmap"', 'id="sidebarRoadmapList"', 'id="sidebarStrip"',
                 'id="backToDashboardBtn"', 'id="tabs"', 'id="crumbHome"', 'id="crumbRoadmapName"', 'id="roadmapSearch"',
                 'id="panelSaveStatus"', 'id="roadmapMenuTrigger"', 'id="profileAnchor"', 'id="profileAvatar"', 'id="themeSystemBtn"',
                 'id="dashboardScreen"', 'id="dashboardContent"', 'id="roadmapScreen"', 'id="roadmapH1"', 'id="main"',
                 'id="sidebarCollapseBtn"', 'id="sidebarOpenBtn"', 'id="sidebarScrim"'):
    assert required in s, "missing " + required
assert s.count('data-view="') == 7, "expected 7 view buttons"
print("index.html updated")
```

## Appendix B5 — `step2_appjs.py` (Task 10)

Run from the repo root: `python3 step2_appjs.py`. The new JavaScript is embedded in this script.

```python
"""Phase 2 / js/app.js: shell, Home, sidebar, routing, About. Run from the repo root: python3 step2_appjs.py"""
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


# 1. enterDashboard -> renderDashboard (everything up to restoreBuiltinRoadmap):
#    login landing, shell helpers, About, routing, Home cards, sidebar switcher, card menus
NEW_ENTER = r'''  // Called once the user is authenticated: lands them on the roadmap named in
  // the URL (#/r/12/overview) or, otherwise, on the roadmap list.
  function enterDashboard(user) {
    const firstName = user.firstName || "";
    const lastName = user.lastName || "";
    Object.assign(session, { username: user.username, firstName, lastName });
    resetRoadmapSession(null, 0);
    progress = normalizeProgress(null);
    const fullName = [firstName, lastName].filter(Boolean).join(" ") || user.username;
    $("profileName").textContent = fullName;
    $("panelFullName").textContent = fullName;
    $("panelUsername").textContent = "@" + user.username;
    $("profileAvatar").textContent = initialsOf(firstName, lastName, user.username);
    hideAuth();
    const route = parseRoute();
    if (route) {
      openRoadmap(route.id, { view: route.view, push: false });
    } else {
      replaceRoute("#/"); // so Back from a roadmap lands on a real Home entry
      showDashboard();
    }
  }

  function initialsOf(firstName, lastName, username) {
    const two = `${(firstName || "").charAt(0)}${(lastName || "").charAt(0)}`;
    return (two.length === 2 ? two : String(username || "?").slice(0, 2)).toUpperCase();
  }

  // ---------------------------------------------------------
  // App shell: sidebar, context (home / roadmap), About
  // ---------------------------------------------------------
  const SIDEBAR_KEY = "roadmap-dashboard:sidebar";

  // Elements marked data-icon="name" get their SVG here (names are fixed identifiers).
  function hydrateIcons() {
    document.querySelectorAll("[data-icon]").forEach((el) => {
      el.innerHTML = window.Icons.svg(el.dataset.icon, { size: el.classList.contains("nav-icon") ? 20 : 14 });
    });
    $("sidebarOpenBtn").innerHTML = window.Icons.svg("menu", { size: 20 });
  }

  function setContext(ctx) {
    const home = ctx === "home";
    $("appShell").dataset.context = ctx;
    $("sidebarHome").classList.toggle("hidden", !home);
    $("sidebarRoadmap").classList.toggle("hidden", home);
    $("crumbRoadmap").classList.toggle("hidden", home);
    $("crumbHome").innerHTML = home
      ? `<span class="crumb-current">Roadmaps</span>`
      : `<button type="button" class="crumb-link" data-action="go-home">Roadmaps</button>`;
    closeNav();
  }

  function openNav() {
    $("appShell").classList.add("nav-open");
    $("sidebarScrim").hidden = false;
    $("sidebarOpenBtn").setAttribute("aria-expanded", "true");
  }
  function closeNav() {
    $("appShell").classList.remove("nav-open");
    $("sidebarScrim").hidden = true;
    $("sidebarOpenBtn").setAttribute("aria-expanded", "false");
  }
  function setSidebarCollapsed(collapsed, remember) {
    $("appShell").classList.toggle("is-collapsed", collapsed);
    const btn = $("sidebarCollapseBtn");
    btn.setAttribute("aria-pressed", String(collapsed));
    btn.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
    if (remember) {
      try { localStorage.setItem(SIDEBAR_KEY, collapsed ? "collapsed" : "expanded"); } catch { /* storage blocked */ }
    }
  }
  function initSidebar() {
    let saved = null;
    try { saved = localStorage.getItem(SIDEBAR_KEY); } catch { /* storage blocked */ }
    setSidebarCollapsed(saved === "collapsed", false);
  }

  function openAboutModal() {
    const host = $("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>About Roadmap Tracker</h2>
      <p class="about-text">Track your progress through structured roadmaps, starting with a 10-month Production AI Engineer plan, or build your own.</p>
      <ul class="about-list">
        <li>&copy; ${new Date().getFullYear()} Roadmap Tracker. All rights reserved.</li>
        <li>Developed by <a href="mailto:upendra.kumar48762@gmail.com">upendra.kumar48762@gmail.com</a></li>
        <li><a href="https://github.com/imkushwaha" target="_blank" rel="noopener">GitHub: imkushwaha</a></li>
        <li>If this tool helps you, please <a href="https://github.com/imkushwaha" target="_blank" rel="noopener">star the repo</a>.</li>
        <li>Built with planning &amp; development assistance from <strong>Claude</strong> (Anthropic AI).</li>
        <li>Open source. Contributions welcome.</li>
      </ul>
      <div class="modal-actions">
        <button type="button" class="btn btn-primary" data-action="close-modal" id="aboutCloseBtn">Close</button>
      </div>`;
    host.classList.remove("hidden");
    $("aboutCloseBtn").focus();
  }

  // ---------------------------------------------------------
  // Routing: plain #hash URLs, no router library.
  //   #/                      roadmap list
  //   #/r/12/overview         roadmap 12, Overview view
  // pushState adds a history entry (Back works); replaceState does not.
  // ---------------------------------------------------------
  let lastHash = window.location.hash;

  function parseRoute() {
    const m = /^#\/r\/(\d+)(?:\/([a-z]+))?$/.exec(window.location.hash);
    return m ? { id: Number(m[1]), view: m[2] || "overview" } : null;
  }
  function routeFor(id, view) { return `#/r/${id}/${view}`; }
  function navigate(hash) {
    if (window.location.hash === hash) return;
    window.history.pushState(null, "", hash);
    lastHash = hash;
  }
  function replaceRoute(hash) {
    if (window.location.hash !== hash) window.history.replaceState(null, "", hash);
    lastHash = hash;
  }
  function validView(view) {
    const tab = document.querySelector(`.tab[data-view="${view}"]`);
    return tab && !tab.classList.contains("hidden") && VIEW_RENDERERS[view] ? view : "overview";
  }

  // Browser Back / Forward.
  async function onPopState() {
    if (!session.username) { lastHash = window.location.hash; return; }
    const route = parseRoute();
    const inRoadmap = session.roadmapId != null;
    if (inRoadmap && !(route && route.id === session.roadmapId)) {
      if (!(await settleUnsavedChanges("Leave"))) { // stay put and restore the URL
        window.history.pushState(null, "", lastHash || "#/");
        return;
      }
    }
    lastHash = window.location.hash;
    if (route && session.roadmapId === route.id) { setView(validView(route.view), { silent: true }); return; }
    if (route) { openRoadmap(route.id, { view: route.view, push: false }); return; }
    if (inRoadmap) {
      resetRoadmapSession(null, 0);
      progress = normalizeProgress(null);
      closeModal();
    }
    showDashboard();
  }

  // ---------------------------------------------------------
  // Roadmap dashboard (post-login landing page)
  // ---------------------------------------------------------
  let dashboardRoadmaps = [];
  let stripsAnimated = false; // the strips fill in once per visit, not on every redraw
  const MAX_ROADMAPS = 20;

  function hideDashboard() { $("dashboardScreen").classList.add("hidden"); }

  function dashboardSkeleton() {
    const card = `
      <article class="roadmap-card is-skeleton" aria-hidden="true">
        <span class="skeleton" style="height:22px;width:60%"></span>
        <span class="skeleton" style="height:36px"></span>
        <span class="skeleton" style="height:8px"></span>
        <span class="skeleton" style="height:36px;margin-top:auto"></span>
      </article>`;
    return `
      <div class="page-head"><div><h1 class="page-title">Roadmaps</h1><p class="page-lead">Loading your roadmaps…</p></div></div>
      <div class="roadmap-grid">${card}${card}${card}</div>`;
  }

  async function showDashboard() {
    closeAllMenus();
    closeCardMenus();
    unlockApp();
    setContext("home");
    document.title = "Roadmap Tracker";
    $("roadmapScreen").classList.add("hidden");
    $("dashboardScreen").classList.remove("hidden");
    $("dashboardContent").innerHTML = dashboardSkeleton();
    let res;
    try {
      res = await window.RoadmapApi.list();
    } catch (e) {
      if (e.status === 401) { handleSessionExpired(); return; }
      $("dashboardContent").innerHTML = `
        <div class="dashboard-status">
          <p>We couldn't load your roadmaps: ${esc(e.message)}</p>
          <button type="button" class="btn btn-primary" data-action="retry-dashboard">Try again</button>
        </div>`;
      return;
    }
    renderDashboard(res.roadmaps);
  }

  function describeActivity(iso) {
    if (!iso) return "Not started yet";
    const days = daysBetween(new Date(iso), new Date());
    if (days <= 0) return "Last activity today";
    if (days === 1) return "Last activity yesterday";
    return "Last activity " + days + " days ago";
  }

  // ----- Month Strip data from a roadmap's server-side stats -----
  function monthKeyOffset(startMonth, offset) {
    const [y, m] = (startMonth || currentMonthKey()).split("-").map(Number);
    return new Date(y, m - 1 + offset, 1);
  }
  // 0-based index of the current calendar month within the roadmap, or -1.
  function currentMonthIndex(startMonth, count) {
    const start = monthKeyOffset(startMonth, 0);
    const idx = (TODAY.getFullYear() - start.getFullYear()) * 12 + (TODAY.getMonth() - start.getMonth());
    return idx >= 0 && idx < count ? idx : -1;
  }
  function stripMonths(stats) {
    const current = currentMonthIndex(stats.startMonth, stats.months.length);
    return stats.months.map((m, i) => ({
      label: monthKeyOffset(stats.startMonth, i).toLocaleDateString(undefined, { month: "short" }),
      title: `Month ${m.number}: ${m.title || "Untitled"} (${m.completed} of ${m.total} tasks complete)`,
      total: m.total, completed: m.completed, inProgress: m.inProgress, blocked: m.blocked,
      current: i === current,
    }));
  }
  const pctOf = (stats) => (stats && stats.total ? Math.round((stats.completed / stats.total) * 100) : 0);

  function cardAction(stats) {
    if (!stats) return "Open";
    if (stats.total === 0) return "Build plan";
    if (stats.completed === stats.total) return "Review";
    return stats.completed + stats.inProgress + stats.blocked > 0 ? "Continue" : "Start";
  }

  function monthPosition(stats) {
    if (!stats || !stats.months.length) return "";
    const idx = currentMonthIndex(stats.startMonth, stats.months.length);
    if (idx >= 0) return `Month ${idx + 1} of ${stats.months.length}`;
    const start = monthKeyOffset(stats.startMonth, 0);
    const before = TODAY < start;
    const label = start.toLocaleDateString(undefined, { month: "short", year: "numeric" });
    return before ? `Starts ${label}` : `${stats.months.length} months`;
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
          <div class="rc-menu">
            <button type="button" class="btn btn-ghost btn-icon btn-sm" data-menu-trigger aria-expanded="false"
                    aria-label="More actions for ${esc(r.name)}">${window.Icons.svg("more-horizontal", { size: 18 })}</button>
            <div class="rc-menu-panel hidden" role="group" aria-label="Actions for ${esc(r.name)}">
              <button type="button" class="profile-action-btn danger" data-action="delete-roadmap" data-id="${r.id}">Delete roadmap…</button>
            </div>
          </div>
        </div>
        ${r.description ? `<p class="roadmap-card-desc">${esc(r.description)}</p>` : `<p class="roadmap-card-desc"></p>`}
        ${progressBlock}
        <div class="rc-foot">
          <p class="roadmap-card-meta">${esc(describeActivity(r.lastActivityAt))}</p>
          <button type="button" class="btn btn-primary" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
        </div>
      </article>`;
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

  function renderDashboard(roadmaps) {
    dashboardRoadmaps = roadmaps;
    renderSidebarRoadmaps();
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

    $("dashboardContent").innerHTML = `
      <div class="page-head">
        <div>
          <h1 class="page-title">Roadmaps</h1>
          <p class="page-lead">Track progress across your plans.</p>
        </div>
        <div class="page-actions">${newBtn}</div>
      </div>
      ${restore}
      ${summaryBar(roadmaps)}
      <div class="roadmap-grid">${roadmaps.map((r) => roadmapCard(r, animate)).join("")}</div>`;
  }

  // Sidebar quick-switcher (Home only)
  function renderSidebarRoadmaps() {
    const host = $("sidebarRoadmapList");
    if (!dashboardRoadmaps.length) { host.innerHTML = `<p class="nav-empty">No roadmaps yet.</p>`; return; }
    host.innerHTML = dashboardRoadmaps.map((r) => `
      <button type="button" class="nav-item nav-roadmap" data-action="open-roadmap" data-id="${r.id}" title="${esc(r.name)}">
        <span class="nav-roadmap-top">
          <span class="nav-roadmap-name">${esc(r.name)}</span>
          ${r.stats ? `<span class="nav-roadmap-pct">${pctOf(r.stats)}%</span>` : ""}
        </span>
        ${r.stats ? window.MonthStrip.html(stripMonths(r.stats), { size: "sm" }) : ""}
      </button>`).join("");
  }

  // Inside a roadmap, the strip is computed live from the open roadmap's data.
  function renderSidebarStrip() {
    const cur = currentPhase();
    const months = allPhases().map((p) => {
      const st = phaseStats(p.id);
      return {
        label: phaseStartDate(p.number).toLocaleDateString(undefined, { month: "short" }),
        title: `Month ${p.number}: ${p.title} (${st.completed} of ${st.total} tasks complete)`,
        total: st.total, completed: st.completed, inProgress: st.inProgress, blocked: st.blocked,
        current: !!cur && cur.id === p.id,
      };
    });
    $("sidebarStrip").innerHTML = window.MonthStrip.html(months, { size: "md" });
  }

  // Per-card overflow menu (Home)
  function closeCardMenus() {
    document.querySelectorAll(".rc-menu-panel").forEach((panel) => {
      if (panel.classList.contains("hidden")) return;
      panel.classList.add("hidden");
      const trigger = panel.parentElement.querySelector("[data-menu-trigger]");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  }
  function toggleCardMenu(trigger) {
    const panel = trigger.parentElement.querySelector(".rc-menu-panel");
    const willOpen = panel.classList.contains("hidden");
    closeCardMenus();
    if (!willOpen) return;
    panel.classList.remove("hidden");
    trigger.setAttribute("aria-expanded", "true");
  }

'''
swap_block("  // Called once the user is authenticated: lands them on the roadmap dashboard.",
           "  async function restoreBuiltinRoadmap() {", NEW_ENTER)

# 2. Click handling for Home and sidebar
NEW_CLICK = r'''  function onDashboardClick(e) {
    const trigger = e.target.closest("[data-menu-trigger]");
    if (trigger) { e.stopPropagation(); toggleCardMenu(trigger); return; }
    const el = e.target.closest("[data-action]");
    if (!el) {
      // A click on the card itself (not on one of its buttons) opens it.
      const card = e.target.closest(".roadmap-card[data-id]");
      if (card && !e.target.closest("button, a, .rc-menu")) openRoadmap(Number(card.dataset.id));
      return;
    }
    closeCardMenus();
    switch (el.dataset.action) {
      case "open-roadmap": openRoadmap(Number(el.dataset.id)); break;
      case "delete-roadmap": confirmDeleteRoadmap(el.dataset.id); break;
      case "restore-builtin": restoreBuiltinRoadmap(); break;
      case "create-roadmap": openCreateRoadmapModal(); break;
      case "retry-dashboard": showDashboard(); break;
      default: break;
    }
  }

'''
swap_block("  function onDashboardClick(e) {", "  function handleSessionExpired() {", NEW_CLICK)

# 3. openRoadmap: loading skeleton, view + URL handling
NEW_OPEN = r'''  // Shell with a skeleton while a roadmap loads (the sidebar and top bar stay put).
  function showRoadmapLoading() {
    hideAuth();
    unlockApp();
    setContext("roadmap");
    $("dashboardScreen").classList.add("hidden");
    $("roadmapScreen").classList.remove("hidden");
    $("roadmapTitle").textContent = "Loading…";
    $("roadmapSubtitle").textContent = "";
    $("crumbRoadmapName").textContent = "Loading…";
    $("sidebarStrip").innerHTML = "";
    $("tabs").classList.add("is-loading");
    $("main").innerHTML = `
      <div aria-busy="true">
        <span class="skeleton" style="height:28px;width:220px;margin-bottom:20px"></span>
        <div class="grid grid-stats">
          ${"<span class=\"skeleton\" style=\"height:92px\"></span>".repeat(4)}
        </div>
        <span class="skeleton" style="height:320px;margin-top:20px"></span>
      </div>`;
  }

  async function openRoadmap(id, opts) {
    const options = opts || {};
    hideDashboard();
    showRoadmapLoading();
    let res;
    try {
      res = await window.RoadmapApi.getProgress(id);
    } catch (e) {
      if (e.status === 401) { showAuth("login"); return; }
      // Never fall through to an empty editable state: saving it would overwrite real data.
      showBlock("Couldn't load this roadmap", e.message, [
        ["Try again", () => openRoadmap(id, options)],
        ["Back to roadmaps", () => { hideAuth(); replaceRoute("#/"); showDashboard(); }],
      ]);
      return;
    }
    resetRoadmapSession(res.roadmap.id, res.version || 0);
    DATA = res.roadmap.source === "builtin_ai_engineer" ? BUILTIN_DATA : BLANK_DATA;
    progress = normalizeProgress(res.data);
    resetViewState();
    rebuildIndex();
    syncTabs();
    hideAuth();
    unlockApp();
    setContext("roadmap");
    $("tabs").classList.remove("is-loading");
    $("roadmapTitle").textContent = res.roadmap.name;
    $("roadmapH1").textContent = res.roadmap.name;
    $("roadmapSubtitle").textContent = res.roadmap.description;
    $("crumbRoadmapName").textContent = res.roadmap.name;
    document.title = res.roadmap.name + " — Roadmap Tracker";
    state.search = "";
    session.roadmapSource = res.roadmap.source;
    $("roadmapMenuName").textContent = res.roadmap.name;
    $("roadmapSearch").value = "";
    closeAllMenus();
    setSaveStatus("saved");
    const view = validView(options.view || "overview");
    setView(view, { silent: true });
    if (options.push === false) replaceRoute(routeFor(res.roadmap.id, view));
    else navigate(routeFor(res.roadmap.id, view));
    window.scrollTo(0, 0);
    checkMilestones();
    if (res.data === null && res.roadmap.source === "builtin_ai_engineer" && readLegacyLocalData()) {
      openLegacyModal(false);
    }
  }

'''
swap_block("  async function openRoadmap(id) {", "  // Per-roadmap UI state must not leak", NEW_OPEN)

# 4. rerender / setView
NEW_RERENDER = r'''  function rerender() {
    const main = document.getElementById("main");
    VIEW_RENDERERS[state.view](main);
    renderSidebarStrip();
  }
  function setView(view, opts) {
    state.view = view;
    document.querySelectorAll(".tab").forEach((t) => {
      const active = t.dataset.view === view;
      t.classList.toggle("active", active);
      if (active) t.setAttribute("aria-current", "page"); else t.removeAttribute("aria-current");
    });
    if (!(opts && opts.silent) && session.roadmapId != null) replaceRoute(routeFor(session.roadmapId, view));
    rerender();
  }

'''
swap_block("  function rerender() {", "  // ---------------------------------------------------------\n  // Theme", NEW_RERENDER)

# 5. The account menu is one element in the top bar now: no more moving it between screens
swap_block("  function mountAccountMenu(slotId) {", "  function wireEvents() {", "")

# 6. Back to Home adds a history entry; logging out forgets the roadmap URL
once("""    progress = normalizeProgress(null);
    closeModal();
    showDashboard();
  }

  function onDashboardClick""", """    progress = normalizeProgress(null);
    closeModal();
    navigate("#/");
    showDashboard();
  }

  function onDashboardClick""")
once("""    // A full reload drops every piece of in-memory, user-specific state.
    window.location.reload();""", """    // Forget the roadmap URL so the next person to log in starts at Home, then
    // reload to drop every piece of in-memory, user-specific state.
    window.history.replaceState(null, "", window.location.pathname);
    window.location.reload();""")

# 7. Event wiring
once("""    document.getElementById("tabs").addEventListener("click", (e) => {
      const btn = e.target.closest(".tab");
      if (btn) setView(btn.dataset.view);
    });
""", """    document.getElementById("tabs").addEventListener("click", (e) => {
      const btn = e.target.closest(".tab");
      if (!btn) return;
      setView(btn.dataset.view);
      closeNav();
      window.scrollTo(0, 0);
    });

    // Sidebar: roadmap switcher, drawer and collapse
    $("sidebar").addEventListener("click", onDashboardClick);
    $("sidebarOpenBtn").addEventListener("click", openNav);
    $("sidebarScrim").addEventListener("click", closeNav);
    $("sidebarCollapseBtn").addEventListener("click", () => {
      setSidebarCollapsed(!$("appShell").classList.contains("is-collapsed"), true);
    });
    // Actions available from several places (menus, sidebar, breadcrumb)
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[data-action]");
      if (!el) { closeCardMenus(); return; }
      if (el.dataset.action === "about") { closeAllMenus(); closeNav(); openAboutModal(); }
      if (el.dataset.action === "go-home") backToDashboard();
      if (!el.closest(".rc-menu")) closeCardMenus();
    });
    window.addEventListener("popstate", onPopState);
""")
once("""      const open = menus.find((m) => m.isOpen());
      if (open) open.close(true);
    });""", """      const open = menus.find((m) => m.isOpen());
      if (open) open.close(true);
      closeCardMenus();
      if ($("appShell").classList.contains("nav-open")) { closeNav(); $("sidebarOpenBtn").focus(); }
    });""")
once("    initTheme();\n    renderAuthPanelStrip();", "    initTheme();\n    hydrateIcons();\n    initSidebar();\n    renderAuthPanelStrip();")

open(P, "w", encoding="utf-8").write(s)
for required in ("function hydrateIcons", "function setContext", "function parseRoute", "function onPopState", "function renderDashboard",
                 "function renderSidebarRoadmaps", "function renderSidebarStrip", "function openAboutModal", "function showRoadmapLoading"):
    assert s.count(required) == 1, f"{required}: expected exactly one definition, found {s.count(required)}"
assert s.count("function describeActivity") == 1, "duplicate describeActivity"
for gone in ("mountAccountMenu", "dashboardAccountSlot", "roadmapAccountSlot", "app-header"):
    assert gone not in s, "leftover reference: " + gone
print("js/app.js updated")
```

## Appendix B6 — `step2_docs.py` (Task 11)

Run from the repo root: `python3 step2_docs.py`.

````python
"""Phase 2 / documentation. Run from the repo root: python3 step2_docs.py"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match ({s.count(old)} found) for: {old[:80]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


STATS_EXAMPLE = '''      "lastActivityAt": null,
      "stats": {
        "total": 849, "completed": 0, "inProgress": 0, "blocked": 0,
        "completedLast7Days": 0, "startMonth": "2026-10",
        "months": [
          { "number": 1, "id": "month-1", "title": "Software Engineering Upgrade",
            "total": 180, "completed": 0, "inProgress": 0, "blocked": 0 }
        ]
      }'''

patch("documentation/api-design.md", [
    ("| `lastActivityAt` | string \\| null | Only in the list response: when progress was last saved; `null` if never |",
     "| `lastActivityAt` | string \\| null | Only in the list response: when progress was last saved; `null` if never |\n"
     "| `stats` | object \\| null | Only in the list response: progress summary (below). `null` only if the stored progress cannot be read |"),
    ("Lists the user's roadmaps, oldest first. Returns metadata only (no progress data).",
     "Lists the user's roadmaps, oldest first. Returns metadata and a progress **summary** (`stats`); the progress data itself is never included."),
    ('      "lastActivityAt": null\n    }\n  ]\n}\n```\nA user who deleted every roadmap gets `{ "roadmaps": [] }`.',
     STATS_EXAMPLE + '\n    }\n  ]\n}\n```\nA user who deleted every roadmap gets `{ "roadmaps": [] }`.\n\n'
     "**`stats` fields** (computed by `js/roadmap-stats.js`):\n\n"
     "| Field | Meaning |\n|---|---|\n"
     "| `total`, `completed`, `inProgress`, `blocked` | Item counts across the whole roadmap. Every task and every month deliverable counts once; user-added topics count in the month that owns their section; an id with no saved status is \"not started\" |\n"
     "| `completedLast7Days` | Items whose stored `completedAt` is within the last 7 days |\n"
     "| `startMonth` | Effective Month 1 (`\"YYYY-MM\"`): the saved `settings.startMonth`, else the roadmap's authored start; `null` for a custom roadmap that has none. The client works out the current month from this in local time |\n"
     "| `months[]` | One entry per month (built-in months, then user-added months) with `number`, `id`, `title` and the same four counts |\n\n"
     "Results are cached in memory by roadmap id and saved `version` (so a save always invalidates), with a 10-minute TTL and a 500-entry cap."),
])

patch("README.md", [
    ("| `GET` | `/api/roadmaps` | — | `200 {roadmaps: [{id, name, description, source, createdAt, lastActivityAt}]}` — `lastActivityAt` is `null` until the first save |",
     "| `GET` | `/api/roadmaps` | — | `200 {roadmaps: [{id, name, description, source, createdAt, lastActivityAt, stats}]}` — `lastActivityAt` is `null` until the first save; `stats` is a progress summary (`total`, `completed`, `inProgress`, `blocked`, `completedLast7Days`, `startMonth`, per-month `months[]`), never the raw progress. See `documentation/api-design.md` |"),
    ("│   └── progress-schema.js        Progress data validator (UMD — browser + server)",
     "│   ├── roadmap-stats.js          Progress summaries for the roadmap list (UMD, used by the server)\n│   └── progress-schema.js        Progress data validator (UMD — browser + server)"),
    ("│   ├── auth.css                  Log in / Create account screens\n",
     "│   ├── auth.css                  Log in / Create account screens\n│   ├── shell.css                 App shell: sidebar, top bar, drawer\n│   ├── home.css                  Home (roadmap list): summary bar, cards\n"),
    ("│   └── schema.test.js            Unit tests for progress-schema validator",
     "│   ├── stats.test.js             Progress summaries: counting rules, cache, list endpoint\n│   └── schema.test.js            Unit tests for progress-schema validator"),
    ("| `test/config.test.js` | Config loader — env vars, production guards, defaults |",
     "| `test/config.test.js` | Config loader — env vars, production guards, defaults |\n| `test/stats.test.js` | `roadmap-stats` counting rules (tasks, deliverables, user-added topics and months, status counts, last 7 days), the stats cache (version key, TTL, size cap), and `GET /api/roadmaps` `stats` (849 items on a new account, follows saves, never exposes raw progress, isolated per user) |"),
    ("All 59 tests cover", "All 79 tests cover"),
    ("- **Delete** a roadmap (and its progress) — always behind a confirmation dialog",
     "- **Delete** a roadmap (and its progress) from the card's **⋯** menu — always behind a confirmation dialog\n"
     "- Each card shows a **Month Strip** (one segment per month, filled by completed / in-progress / blocked tasks, current month marked), percent complete, task counts and the current month; a summary bar totals tasks done across roadmaps\n"
     "- **App shell** — a left sidebar (roadmap switcher on Home; view navigation inside a roadmap; collapsible, and a slide-in drawer on small screens) and a top bar with breadcrumb, search, save status, roadmap settings and the account menu\n"
     "- **Links that work** — `#/` is Home and `#/r/<id>/<view>` is a roadmap view, so refresh, Back/Forward and bookmarks work; leaving a roadmap with unsaved edits still asks first"),
])

patch("documentation/multi-roadmap.md", [
    ("| Dashboard markup | `index.html` — `#dashboardScreen`; the create dialog is rendered into the shared `#modalHost` |",
     "| Dashboard markup | `index.html` — `#dashboardScreen` inside the app shell (`#appShell`: sidebar + top bar); the create dialog is rendered into the shared `#modalHost`. Cards use the list endpoint's `stats` for the Month Strip and totals |"),
    ('| Styles | `css/styles.css` — "Roadmap dashboard" and "Custom roadmaps" sections |',
     '| Styles | `css/home.css` (cards, summary bar), `css/shell.css` (sidebar, top bar), `css/styles.css` ("Custom roadmaps") |\n'
     '| URLs | `parseRoute` / `navigate` / `replaceRoute` / `onPopState` in `js/app.js`: `#/` and `#/r/<id>/<view>`; Back and Forward are handled, and leaving a roadmap with unsaved edits asks first |'),
    ("Z-order: roadmap app (50) < dashboard (350) < modal (400) < toasts (450) < auth screen (500).",
     "Z-order: top bar (20) < sidebar (30) < drawer scrim (55) and drawer (60) < modal (400) < toasts (450) < auth screen (500)."),
])

patch(".claude/PROJECT_WALKTHROUGH.md", [
    ("- `GET /api/roadmaps` — the user's roadmaps with `lastActivityAt` (the progress row's `updated_at`, or `null`)",
     "- `GET /api/roadmaps` — the user's roadmaps with `lastActivityAt` (the progress row's `updated_at`, or `null`) and `stats` (progress summary from `js/roadmap-stats.js`, cached by roadmap id + version in `server/roadmaps/stats.js`)"),
])

patch("documentation/low-level-design.md", [
    ("| `listForUser(userId)` |",
     "| `listWithProgress(userId)` | Same join as `listForUser` plus `p.data` and `p.version`; used only by the list route to build `stats`; the raw data is stripped before responding | `RoadmapRow[]` with `progressData`, `progressVersion` |\n| `listForUser(userId)` |"),
])

patch("documentation/design-system.md", [
    ("| `css/auth.css` | Log in / create-account screens (split layout, brand panel, field hints, footer) |",
     "| `css/auth.css` | Log in / create-account screens (split layout, brand panel, field hints, footer) |\n"
     "| `css/shell.css` | App shell: sidebar (expanded, collapsed, drawer), top bar, breadcrumb, save-status chip, About dialog bits |\n"
     "| `css/home.css` | Home: page header, summary bar, roadmap cards, per-card menu, empty state, skeleton |"),
    ("| `js/month-strip.js` | `MonthStrip.html(months, { size, labels, animate })` |",
     "| `js/month-strip.js` | `MonthStrip.html(months, { size, labels, animate })` |\n"
     "| `js/roadmap-stats.js` | Shared (UMD) progress summaries; used by the server for `stats` on the roadmap list |"),
    ("→ `auth.css` → `styles.css`;", "→ `auth.css` → `shell.css` → `home.css` → `styles.css`;"),
    ("| 2 | App shell, Home, `stats` API | Not started |", "| 2 | App shell, Home, `stats` API, hash routes | Done |"),
    ("## Redesign status",
     """## App shell

`#appShell` holds the sidebar and the page. `data-context="home|roadmap"` switches what is shown: Home shows the roadmap switcher; a roadmap shows "All roadmaps", the roadmap card with a live Month Strip, and the seven views (buttons with `data-view`, so the existing view switching is unchanged). Roadmap-only controls (search, save status, roadmap settings) carry the `roadmap-only` class and are hidden on Home. The account menu is a single element in the top bar. Below 1024px the sidebar is a drawer (menu button, scrim, Escape to close); on desktop it can be collapsed to an icon rail, remembered under `roadmap-dashboard:sidebar`.

## Redesign status"""),
])

patch(".claude/specs/settings-split-plan.md", [
    ("**Status:** Planning — not started", "**Status:** Superseded by ui-redesign-spec.md (Phase 2)"),
])
print("docs updated")
````

## Appendix C1 — `verify_phase2.py` (verification harness; keep outside the repo)

Uses `serve-demo.js` from the Phase 0 spec (Appendix C1).

```python
"""Phase 2 verification. Usage:
    python3 verify_phase2.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Needs the demo server from the Phase 0 spec (serve-demo.js) running; the demo user is imkushwaha / demo-pass-123.
Exit code 0 only if every check passes."""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots-p2"
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


def new_context(browser, width=1440, height=900, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
    page = ctx.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: page.problems.append(m.text) if m.type == "error" and "401" not in m.text and "404" not in m.text else None)
    return ctx, page


def fresh_user(ctx, tag):
    name = f"p2{tag}_{RUN}"
    r = ctx.request.post(BASE + "/api/auth/register", data={"firstName": "Rita", "lastName": "Route", "username": name, "password": "longenough1"})
    assert r.status == 201, r.status
    return name


def login_demo(ctx):
    r = ctx.request.post(BASE + "/api/auth/login", data={"username": "imkushwaha", "password": "demo-pass-123"})
    assert r.status == 200, r.status


def home(page):
    page.goto(BASE)
    page.wait_for_selector(".summary-bar", timeout=10000)


def visible(page, selector):
    return page.locator(selector).first.is_visible()


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ============ A. API contract ============
    ctx, page = new_context(browser)
    login_demo(ctx)
    data = ctx.request.get(BASE + "/api/roadmaps").json()
    r0 = data["roadmaps"][0]
    s = r0.get("stats") or {}
    check(s.get("total") == 849 and len(s.get("months", [])) == 10 and s.get("startMonth") == "2026-10", "API: built-in roadmap stats = 849 items, 10 months, startMonth 2026-10")
    check(all(k in s for k in ("completed", "inProgress", "blocked", "completedLast7Days")), "API: stats has status counts and completedLast7Days")
    check(s["completed"] > 0 and s["months"][0]["completed"] > 0, "API: demo progress is reflected in stats")
    check(not any(k in r0 for k in ("progressData", "progressVersion", "data")), "API: raw progress is never in the list response")
    check(ctx.request.get(BASE + "/api/roadmaps").headers.get("cache-control", "").find("no-store") >= 0, "API: list is not cacheable")
    DEMO_DONE = s["completed"]; DEMO_TOTAL = s["total"]; DEMO_WEEK = s["completedLast7Days"]
    ctx.close()

    # ============ B. Home (desktop, new user) ============
    ctx, page = new_context(browser)
    uname = fresh_user(ctx, "a")
    home(page)
    check(page.get_attribute("#appShell", "data-context") == "home", "Home: shell context is 'home'")
    check(page.inner_text("h1.page-title") == "Roadmaps", "Home: one H1 'Roadmaps'")
    check(not page.locator("body.locked").count(), "Home: app is unlocked")
    check(visible(page, "#sidebar") and visible(page, "#sidebarHome") and not visible(page, "#sidebarRoadmap"), "Home: sidebar shows the roadmap switcher, not the views")
    for sel in ("#roadmapSearch", "#panelSaveStatus", "#roadmapMenuTrigger"):
        check(not visible(page, sel), f"Home: roadmap-only control hidden: {sel}")
    check(visible(page, "#profileTrigger") and page.inner_text("#profileAvatar") == "RR", "Home: account menu with initials avatar RR")
    summary = " ".join(page.inner_text(".summary-bar").split())
    check("Roadmaps 1" in summary and "0 / 849" in summary and "0%" in summary, "Home: summary bar for a new account: " + summary)
    card = page.locator("article.roadmap-card").first
    check(card.locator(".rc-title").inner_text() == "AI Engineer Roadmap" and card.locator(".rc-badge").inner_text() == "Built-in", "Home: card title and Built-in badge")
    check(card.locator(".btn-primary").inner_text() == "Start", "Home: new roadmap's primary action is Start")
    check(card.locator(".strip-col").count() == 10, "Home: card strip has 10 months")
    expected_idx = page.evaluate("(() => { const n = new Date(); return (n.getFullYear() - 2026) * 12 + (n.getMonth() - 9); })()")
    pos = card.locator(".rc-meta span").nth(1).inner_text()
    exp = f"Month {expected_idx + 1} of 10" if 0 <= expected_idx < 10 else ("Starts Oct 2026" if expected_idx < 0 else "10 months")
    check(pos == exp, f"Home: month position text '{pos}' == expected '{exp}'")
    check((card.locator(".strip-col.is-current").count() == 1) == (0 <= expected_idx < 10), "Home: current month marker present exactly when today is inside the roadmap")
    check(card.locator(".rc-menu-panel").is_hidden() and page.get_attribute("article.roadmap-card [data-menu-trigger]", "aria-label").startswith("More actions for"), "Home: card menu closed and labelled")
    check(page.locator("#sidebarRoadmapList .nav-roadmap").count() == 1, "Home: sidebar switcher lists the roadmap")
    page.wait_for_timeout(900)  # let the strip animation finish
    page.screenshot(path=f"{SHOTS}/home-desktop-light.png")
    audit(page, "Home (desktop, light)")

    # ---- card menu, About, collapse
    trigger = page.locator("article.roadmap-card [data-menu-trigger]")
    trigger.click()
    check(page.locator(".rc-menu-panel").first.is_visible() and trigger.get_attribute("aria-expanded") == "true", "card menu opens")
    audit(page, "Home with card menu open")
    page.keyboard.press("Escape")
    check(page.locator(".rc-menu-panel").first.is_hidden() and trigger.get_attribute("aria-expanded") == "false", "Escape closes the card menu")
    page.click("#sidebar [data-action=about]"); page.wait_for_selector("#modalHost:not(.hidden)")
    check("Claude" in page.inner_text("#modalHost") and "github.com/imkushwaha" in page.inner_html("#modalHost") and page.evaluate("document.activeElement.id") == "aboutCloseBtn", "About dialog: credits, links, focus on Close")
    audit(page, "About dialog")
    page.click("#aboutCloseBtn")
    page.click("#profileTrigger"); page.locator("#profilePanel [data-action=about]").click(); page.wait_for_selector("#modalHost:not(.hidden)")
    check(True, "About also reachable from the account menu"); page.click("#aboutCloseBtn")
    page.click("#sidebarCollapseBtn")
    check(page.evaluate("document.getElementById('appShell').classList.contains('is-collapsed')") and page.evaluate("document.getElementById('sidebar').getBoundingClientRect().width") <= 70, "sidebar collapses to ~64px")
    check(page.get_attribute("#sidebarCollapseBtn", "aria-pressed") == "true", "collapse button has aria-pressed")
    audit(page, "Home with collapsed sidebar")
    page.reload(); page.wait_for_selector(".summary-bar")
    check(page.evaluate("document.getElementById('appShell').classList.contains('is-collapsed')"), "collapse is remembered after reload")
    page.click("#sidebarCollapseBtn")

    # ============ C. Open a roadmap, routing, live strip ============
    page.click("article.roadmap-card .btn-primary"); page.wait_for_selector(".stat-tile")
    hsh = page.evaluate("location.hash"); rid = hsh.split("/")[2]
    check(hsh == f"#/r/{rid}/overview", "opening pushes #/r/<id>/overview: " + hsh)
    check(page.get_attribute("#appShell", "data-context") == "roadmap" and visible(page, "#sidebarRoadmap") and not visible(page, "#sidebarHome"), "roadmap context: sidebar shows the views")
    for sel in ("#roadmapSearch", "#panelSaveStatus", "#roadmapMenuTrigger"):
        check(visible(page, sel), f"roadmap context: control visible: {sel}")
    check(page.inner_text("#crumbRoadmapName") == "AI Engineer Roadmap" and page.inner_text("#roadmapH1") == "AI Engineer Roadmap", "breadcrumb and hidden H1 carry the roadmap name")
    check(page.locator("#tabs .tab:visible").count() == 7, "7 view buttons visible for the built-in roadmap")
    check(page.get_attribute('.tab[data-view="overview"]', "aria-current") == "page", "active view has aria-current=page")
    page.click('.tab[data-view="kanban"]'); page.wait_for_selector(".kanban-board")
    check(page.evaluate("location.hash") == f"#/r/{rid}/kanban", "view change replaces the URL (kanban)")
    page.reload(); page.wait_for_selector(".kanban-board", timeout=10000)
    check(page.evaluate("location.hash") == f"#/r/{rid}/kanban" and visible(page, "#sidebarRoadmap"), "reload restores roadmap and view")
    page.go_back(); page.wait_for_selector(".summary-bar", timeout=10000)
    check(page.evaluate("location.hash") == "#/" and visible(page, "#sidebarHome"), "Back returns to Home (#/)")
    page.go_forward(); page.wait_for_selector(".kanban-board", timeout=10000)
    check(page.evaluate("location.hash") == f"#/r/{rid}/kanban", "Forward returns to the roadmap view")
    page.click('.tab[data-view="checklist"]'); page.wait_for_selector(".subtask-checkbox")
    before = page.get_attribute("#sidebarStrip .strip", "aria-label")
    page.locator(".subtask-checkbox").first.click()
    page.locator("#panelSaveStatus", has_text="Saved").wait_for(timeout=8000)
    after = page.get_attribute("#sidebarStrip .strip", "aria-label")
    check(before.startswith("0 of 849") and after.startswith("1 of 849"), f"sidebar strip updates live: '{before}' -> '{after}'")
    check("saved" in page.get_attribute("#panelSaveStatus", "class"), "save-status chip shows Saved")
    page.go_back(); page.wait_for_selector(".summary-bar", timeout=10000)
    page.locator("article.roadmap-card .btn-primary").click(); page.wait_for_selector(".stat-tile")
    page.click('.tab[data-view="checklist"]'); page.wait_for_selector(".subtask-checkbox")
    check(page.locator(".subtask-checkbox").first.is_checked(), "a change made just before pressing Back was saved")
    page.screenshot(path=f"{SHOTS}/roadmap-checklist-desktop-light.png")
    # ---- Roadmap settings menu (every item keeps working in its new place)
    page.click("#roadmapMenuTrigger")
    check(page.locator("#roadmapMenuPanel").is_visible() and page.inner_text("#roadmapMenuName") == "AI Engineer Roadmap", "roadmap settings menu opens and shows the roadmap name")
    audit(page, "roadmap settings menu open")
    with page.expect_download() as dl:
        page.click("#exportBtn")
    check(dl.value.suggested_filename.endswith(".json"), "Export progress downloads a .json file: " + dl.value.suggested_filename)
    page.click("#roadmapMenuTrigger"); page.click("#startMonthBtn"); page.wait_for_selector("#modalHost:not(.hidden)")
    check(page.locator("#modalHost input[type=month]").count() == 1, "Set start month opens a dialog with a month picker")
    page.click("#modalHost [data-action=close-modal]"); page.wait_for_selector("#modalHost.hidden", state="attached")
    page.click("#roadmapMenuTrigger"); page.click("#resetBtn"); page.wait_for_selector("#modalHost:not(.hidden)")
    check("reset" in page.inner_text("#modalHost").lower() and page.locator("#modalHost [data-action=confirm-reset]").count() == 1, "Reset progress asks for confirmation")
    page.click("#modalHost [data-action=close-modal]")
    check(page.locator("#importFile").count() == 1 and page.locator("#importBtn").count() == 1, "Import progress control exists")
    page.click("#roadmapMenuTrigger"); check(page.locator("#legacyImportBtn").is_hidden(), "legacy import is hidden when the browser has no old data"); page.keyboard.press("Escape")
    # breadcrumb link
    page.click("#crumbHome .crumb-link"); page.wait_for_selector(".summary-bar")
    check(page.evaluate("location.hash") == "#/", "breadcrumb 'Roadmaps' link goes Home")
    # unknown roadmap
    page.evaluate("location.hash='#/r/999999/overview'"); page.reload()
    page.wait_for_selector("#authBlock:not(.hidden)", timeout=10000)
    check("load" in page.inner_text("#authBlockTitle").lower(), "unknown roadmap id shows an error panel")
    page.click("#authBlockActions button >> nth=1"); page.wait_for_selector(".summary-bar", timeout=10000)
    check(page.evaluate("location.hash") == "#/", "'Back to roadmaps' lands on Home")

    # ============ D. Custom roadmap, delete, empty state, restore ============
    page.click("[data-action=create-roadmap]"); page.fill("#newRoadmapName", "Temp Plan"); page.click("#createRoadmapSubmit")
    page.wait_for_selector("#roadmapTitle")
    check(page.inner_text("#crumbRoadmapName") == "Temp Plan" and page.evaluate("location.hash").endswith("/overview"), "created custom roadmap opens with its URL")
    check(page.locator("#tabs .tab:visible").count() == 5, "custom roadmap shows 5 views (Skills and Reference hidden)")
    page.click("#backToDashboardBtn"); page.wait_for_selector(".summary-bar")
    card = page.locator("article.roadmap-card", has_text="Temp Plan")
    check("No months yet" in card.inner_text() and card.locator(".btn-primary").inner_text() == "Build plan", "empty custom card: 'No months yet' and 'Build plan'")
    check(card.locator(".strip.is-empty").count() == 1, "empty custom card shows the dashed empty strip")
    card.locator("[data-menu-trigger]").click(); card.locator("[data-action=delete-roadmap]").click()
    check("permanently deletes" in page.inner_text("#modalHost") or "delete" in page.inner_text("#modalHost").lower(), "delete asks for confirmation")
    page.click("[data-action=confirm-delete-roadmap]"); page.locator("article.roadmap-card", has_text="Temp Plan").wait_for(state="detached", timeout=8000)
    check(True, "delete from the card menu works")
    ai = page.locator("article.roadmap-card", has_text="AI Engineer")
    ai.locator("[data-menu-trigger]").click(); ai.locator("[data-action=delete-roadmap]").click()
    page.click("[data-action=confirm-delete-roadmap]"); page.wait_for_selector(".empty-panel", timeout=8000)
    check("No roadmaps yet" in page.inner_text(".empty-panel"), "deleting the last roadmap shows the empty state")
    audit(page, "empty state")
    page.click(".empty-panel [data-action=restore-builtin]"); page.wait_for_selector("article.roadmap-card", timeout=8000)
    check(page.locator("article.roadmap-card").count() == 1, "restore from the empty state works")
    page.click("[data-action=create-roadmap]"); page.fill("#newRoadmapName", "Second"); page.click("#createRoadmapSubmit"); page.wait_for_selector("#roadmapTitle")
    page.click("#backToDashboardBtn"); page.wait_for_selector(".summary-bar")
    ai = page.locator("article.roadmap-card", has_text="AI Engineer")
    ai.locator("[data-menu-trigger]").click(); ai.locator("[data-action=delete-roadmap]").click(); page.click("[data-action=confirm-delete-roadmap]")
    page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(state="detached", timeout=8000)
    page.wait_for_selector(".notice-row [data-action=restore-builtin]", timeout=8000)
    check(page.locator(".notice-row [data-action=restore-builtin]").count() == 1, "with other roadmaps left, a notice offers 'Restore AI Engineer roadmap'")
    page.click(".notice-row [data-action=restore-builtin]"); page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(timeout=8000)
    check(page.locator(".notice-row").count() == 0, "notice disappears after restoring")

    # ============ E. Logout clears the URL ============
    page.locator("article.roadmap-card", has_text="AI Engineer").locator(".btn-primary").click(); page.wait_for_selector(".stat-tile")
    page.click("#profileTrigger"); page.click("#logoutBtn"); page.wait_for_selector("#authForm", state="visible")
    check(page.evaluate("location.hash") == "", "logout clears the roadmap URL")
    check(not page.problems, "no page errors or CSP/console errors (desktop flows)" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # ============ F. 20-roadmap limit ============
    ctx, page = new_context(browser)
    fresh_user(ctx, "b")
    for i in range(19):
        r = ctx.request.post(BASE + "/api/roadmaps", data={"name": f"Plan {i + 1}"})
        assert r.status == 201, r.status
    home(page)
    btn = page.locator("[data-action=create-roadmap]").first
    check(btn.is_disabled() and "limit of 20" in (btn.get_attribute("title") or ""), "New roadmap is disabled at 20 roadmaps with an explanatory title")
    check(page.locator("article.roadmap-card").count() == 20, "20 cards render")
    ctx.close()

    # ============ G. Skeleton while loading ============
    ctx, page = new_context(browser)
    fresh_user(ctx, "c")
    def slow(route):
        time.sleep(1.2); route.continue_()
    page.route("**/api/roadmaps", slow)
    page.goto(BASE)
    page.wait_for_selector(".roadmap-card.is-skeleton", timeout=5000)
    check(page.locator(".roadmap-card.is-skeleton").count() == 3 and "Loading your roadmaps" in page.inner_text("#dashboardContent"), "Home shows 3 skeleton cards while loading")
    page.wait_for_selector(".summary-bar", timeout=10000)
    check(page.locator(".is-skeleton").count() == 0, "skeletons are replaced by real content")
    page.unroute("**/api/roadmaps")
    ctx.close()

    # ============ H. Phone and tablet: drawer ============
    for name, (w, h) in (("phone", (390, 844)), ("tablet", (820, 1000))):
        ctx, page = new_context(browser, w, h)
        fresh_user(ctx, name[:1] + "d")
        home(page)
        check(not page.locator("#sidebar").evaluate("el => el.getBoundingClientRect().right > 0 && el.getBoundingClientRect().left >= 0"), f"{name}: sidebar is off-canvas by default")
        check(page.locator("#sidebarOpenBtn").is_visible(), f"{name}: menu button visible")
        check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"{name}: no horizontal scrolling on Home")
        page.click("#sidebarOpenBtn"); page.wait_for_timeout(300)
        check(page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "true" and page.locator("#sidebarScrim").is_visible(), f"{name}: drawer opens with a scrim")
        page.screenshot(path=f"{SHOTS}/drawer-{name}.png")
        audit(page, f"drawer open ({name})")
        page.keyboard.press("Escape"); page.wait_for_timeout(250)
        check(page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "false" and page.evaluate("document.activeElement.id") == "sidebarOpenBtn", f"{name}: Escape closes the drawer and returns focus to the menu button")
        page.click("#sidebarOpenBtn"); page.click("#sidebar .nav-roadmap"); page.wait_for_selector(".stat-tile")
        check(page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "false", f"{name}: choosing a roadmap closes the drawer")
        page.click("#sidebarOpenBtn"); page.click('.tab[data-view="timeline"]'); page.wait_for_timeout(250)
        check(page.evaluate("location.hash").endswith("/timeline") and page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "false", f"{name}: choosing a view closes the drawer and updates the URL")
        check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"{name}: no horizontal scrolling in a roadmap")
        page.screenshot(path=f"{SHOTS}/roadmap-{name}.png")
        audit(page, f"roadmap ({name})")
        ctx.close()

    # ============ I. Accessibility across views, both themes (demo user with progress) ============
    for scheme in ("light", "dark"):
        ctx, page = new_context(browser, 1440, 900, scheme)
        login_demo(ctx); home(page)
        summary = " ".join(page.inner_text(".summary-bar").split())
        check(f"{DEMO_DONE} / {DEMO_TOTAL}" in summary and str(DEMO_WEEK) in summary, f"Home ({scheme}): summary matches the API ({DEMO_DONE} / {DEMO_TOTAL}, {DEMO_WEEK} this week)")
        page.wait_for_timeout(900)  # let the one-time strip animation (0.6s) finish before the screenshot
        page.screenshot(path=f"{SHOTS}/home-{scheme}-progress.png")
        audit(page, f"Home with progress ({scheme})")
        page.click("article.roadmap-card .btn-primary"); page.wait_for_selector(".stat-tile")
        for view in ("overview", "timeline", "kanban", "checklist", "thisweek", "mastery", "reference"):
            page.click(f'.tab[data-view="{view}"]'); page.wait_for_timeout(250)
            if view in ("overview", "kanban") or scheme == "dark":
                page.screenshot(path=f"{SHOTS}/roadmap-{view}-{scheme}.png")
            audit(page, f"{view} ({scheme})")
        check(not page.problems, f"no page errors or CSP/console errors ({scheme} audit run)" + ("" if not page.problems else ": " + str(page.problems[:3])))
        ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
```

---

*End of Phase 2 spec. Phase 3 (Home flows) is specified separately.*
