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
