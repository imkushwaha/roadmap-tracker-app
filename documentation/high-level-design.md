# High Level Design — Roadmap Dashboard

## 1. System Overview

The Roadmap Dashboard (branded **Roadmap Tracker**) is a multi-roadmap progress tracker. After logging in, a user lands on a **roadmap dashboard** listing their roadmaps and can open one, create a new one, delete one (after confirmation), or restore the built-in one. Every account starts with the **AI Engineer Roadmap** — a 10-month curriculum (phases → sections → topics → subtasks) — where the user records progress, adds custom content, and visualises completion across multiple views. Users can also create **custom roadmaps**: a custom roadmap starts empty and is built inside the app with the same Month → Section → Topic → Tasks editors, and then offers the same Overview, Timeline, Kanban, Checklist and This Week views. Progress (and, for custom roadmaps, the plan itself) is stored on the server **per roadmap**, tied to the authenticated user account, with optimistic concurrency control to handle multi-tab edits. "Create with AI" is shown as *coming soon* and is planned for a later phase.

The application is a **zero-build web app**: the frontend is plain HTML, CSS, and ES2022 JavaScript loaded directly by the browser. There is no compilation step, no bundler, and no frontend framework. The backend is an Express 5 server backed by a Turso (hosted libSQL, SQLite-compatible) database.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                                                             │
│  index.html                                                 │
│  ├── css/styles.css          (all styles)                   │
│  ├── js/progress-schema.js   (UMD validator, shared)        │
│  ├── js/api.js               (fetch wrappers: AuthApi /     │
│  │                            RoadmapApi)                   │
│  ├── data/roadmap.js         (static AI Engineer content)   │
│  └── js/app.js               (entire SPA logic)             │
│                                                             │
│  Screens: auth · roadmap dashboard · roadmap views          │
│  Roadmap views rendered into <main id="main">:              │
│  overview · timeline · kanban · checklist · thisweek        │
│  mastery · reference                                        │
└──────────────────┬──────────────────────────────────────────┘
                   │ fetch (credentials: same-origin)
                   │ Cookie: rd_session=<JWT>
┌──────────────────▼──────────────────────────────────────────┐
│                Express 5 Server (port 3000)                  │
│                                                             │
│  server/app.js           (createApp factory)                │
│  server/config.js        (env-var loader)                   │
│  server/db.js            (libSQL client + schema)           │
│  ├── server/auth/                                           │
│  │   ├── service.js      (bcrypt + JWT helpers, requireAuth)│
│  │   └── validators.js   (username/password/name rules)     │
│  ├── server/roadmaps/                                       │
│  │   ├── builtin.js      (built-in roadmap identity)        │
│  │   ├── validators.js   (create input rules, limits)       │
│  │   ├── progress.js     (empty starting progress)          │
│  │   └── repository.js   (all roadmap/progress SQL)         │
│  └── server/routes/                                         │
│      ├── auth.js         (/api/auth/*)                      │
│      └── roadmaps.js     (/api/roadmaps/* — HTTP only)      │
│                                                             │
│  Static serving:                                            │
│  index.html · css/ · js/ · data/roadmap.js  (allowlist)    │
└──────────────────┬──────────────────────────────────────────┘
                   │ @libsql/client (async, over the network)
┌──────────────────▼──────────────────────────────────────────┐
│     Turso (hosted libSQL) — TURSO_DATABASE_URL              │
│  users             (id, username, password_hash,            │
│                     first_name, last_name, created_at)      │
│  roadmaps          (id, user_id FK, name, description,      │
│                     source, created_at)                     │
│  roadmap_progress  (roadmap_id FK, data JSON, version,      │
│                     updated_at)                             │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Topology

| Environment | Server | Database | Notes |
|-------------|--------|----------|-------|
| Development | `node server/index.js` :3000 | Local file `data/app.db` (or a Turso URL if `TURSO_DATABASE_URL` is set) | Random `SESSION_SECRET` on restart |
| Test | In-process, ephemeral port | `:memory:` libSQL | Fresh database per server |
| Production (Render) | Express web service (`render.yaml`) | Turso, via `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` | `SESSION_SECRET` required; `COOKIE_SECURE=true`; no persistent disk needed |

---

## 3. Key Components

### 3.1 Frontend (Vanilla JS SPA)

| File | Purpose |
|------|---------|
| `index.html` | SPA shell; loads all JS/CSS; hosts the auth screen, the roadmap dashboard (`#dashboardScreen`) and the `<main id="main">` view render target |
| `js/app.js` | Large IIFE: roadmap dashboard, view rendering, state, sync, auth UI, event handling |
| `js/api.js` | `AuthApi` (register/login/logout/me/checkUsername) and `RoadmapApi` (list/create/restoreBuiltin/remove/getProgress/putProgress) using `fetch` |
| `js/progress-schema.js` | UMD validator shared with server; validates `ProgressStore` shape |
| `data/roadmap.js` | Static content — `window.ROADMAP_DATA`; generated from `data/roadmap.md` |
| `css/styles.css` | All application styles (light/dark theme support) |

### 3.2 Backend (Express 5)

| Module | Purpose |
|--------|---------|
| `server/index.js` | Entry point — calls `createApp`, binds port, sets up graceful shutdown |
| `server/app.js` | `createApp(db, sessionSecret, opts)` — pure factory, fully testable |
| `server/config.js` | `loadConfig()` — reads env vars, validates required keys, returns config object |
| `server/db.js` | `openDb(url, authToken)` (async) — creates the libSQL client and applies the schema via `batch` |
| `server/auth/service.js` | `hashPassword`, `verifyPassword`, `signToken`, `verifyToken`, cookie options, `getCurrentUser`, `createRequireAuth` |
| `server/auth/validators.js` | `validateUsername`, `validatePassword`, `validateName` — return `{ valid, error }` |
| `server/roadmaps/builtin.js` | `BUILTIN_AI_ENGINEER` — name, description and `source` of the roadmap every account starts with |
| `server/roadmaps/validators.js` | `validateRoadmapInput` (name 1–80 single line, description ≤ 300, optional `YYYY-MM` start month), `CUSTOM_SOURCE`, `MAX_ROADMAPS_PER_USER` (20) |
| `server/roadmaps/progress.js` | `emptyProgress(startMonth)` — the starting progress blob of a new custom roadmap |
| `server/roadmaps/repository.js` | `createRoadmapRepository(db)` — every roadmap/progress query (list, ownership lookup, count, insert, delete, get/save progress with compare-and-swap); lookups are scoped by `user_id` |
| `server/routes/auth.js` | Handles `/api/auth/register` (user + starter roadmap in one transaction), `/login`, `/logout`, `/me`, `/check-username` |
| `server/routes/roadmaps.js` | HTTP layer for `/api/roadmaps`: list, create custom, restore built-in, delete, and `GET`/`PUT /:id/progress`; parses/validates requests and delegates all SQL to the repository |

### 3.3 Supporting Tools

| File | Purpose |
|------|---------|
| `scripts/md_to_json.py` | Python 3 parser — converts `data/roadmap.md` → `data/roadmap.json` + `data/roadmap.js` |
| `data/roadmap.md` | Source of truth for the 10-month curriculum (edited by humans) |
| `data/schema.md` | TypeScript-style type documentation for `roadmap.json` and `ProgressStore` |
| `test/` | Integration and unit tests using Node.js built-in `node:test` |

---

## 4. Authentication & Authorisation Flow

```
User submits register/login form
        │
        ▼
POST /api/auth/register or /login
  bcrypt hash/verify password (anti-timing dummy hash for unknown users)
  (register also inserts the starter roadmap in the same transaction)
  jwt.sign({ sub: userId, un: username }, SESSION_SECRET, { expiresIn: '7d' })
        │
        ▼
Set-Cookie: rd_session=<JWT>; HttpOnly; SameSite=Lax; Path=/
(Secure flag on in production)
        │
        ▼
Browser stores cookie (automatic, httpOnly — JS cannot read it)
        │
        ▼
Every subsequent fetch() call with credentials: 'same-origin'
  → Cookie: rd_session=<JWT> sent automatically
        │
        ▼
requireAuth middleware (server/auth/service.js, applied to /api/roadmaps)
  jwt.verify(req.cookies.rd_session) → { id, username }
  db lookup confirms user exists
  sets req.user = { id, username }
        │
        ▼
Route handler processes request
```

`GET /api/auth/me` acts as a **rolling session** — it refreshes the cookie TTL on every call, keeping active users logged in across the 7-day expiry.

---

## 5. Navigation Flow — Dashboard to Roadmap

```
boot()                                 GET /api/auth/me
  │ 401 → auth screen (login / register)
  ▼ 200 (or after a successful login/register)
enterDashboard(user)                   resets per-roadmap sync state; session.roadmapId = null
  ▼
showDashboard() → renderDashboard()    GET /api/roadmaps
  │  cards: Open · Delete
  │  action cards: Restore AI Engineer Roadmap (only if the user has none),
  │                Create new roadmap (opens the create dialog),
  │                Create with AI (disabled, "Coming soon")
  │
  ├─ Delete → confirmation modal → DELETE /api/roadmaps/:id → refresh list
  ├─ Restore → POST /api/roadmaps { source } → refresh list
  ├─ Create → dialog (name, description, start month) → POST /api/roadmaps
  │        → openRoadmap(new id): the user lands in the empty roadmap
  └─ Open → openRoadmap(id)            GET /api/roadmaps/:id/progress
        sets session.roadmapId, session.version; picks the curriculum for the
        roadmap's source (AI Engineer bundle or empty BLANK_DATA); loads progress;
        resets per-roadmap view state (Kanban month, Checklist filters, expanded
        months/sections); rebuilds INDEX; shows only the tabs the curriculum
        supports; header title/subtitle come from the roadmap; starts on Overview
        │
        ▼ "←" back button
backToDashboard()                      flushes unsaved changes first (confirms if they can't be saved)
```

Logging out follows the same "flush first" rule and then reloads the page, dropping all in-memory user state.

---

## 6. Data Flow — Saving Progress

```
User interacts with UI (e.g. marks subtask as completed)
        │
        ▼
app.js: update in-memory progress object
        │
        ▼
persist() → schedules debounced autosave (1500ms)
        │
        ▼ (after debounce)
RoadmapApi.putProgress(session.roadmapId, progress, session.version)
  PUT /api/roadmaps/:id/progress { data: ProgressStore, version: N }
        │
  ┌─────┴──────────┐
  │                │
Match            Mismatch
(version OK)     (409 conflict)
  │                │
  ▼                ▼
UPDATE roadmap_progress   Return { error, server: { data, version } }
SET version = N+1         Conflict modal → user chooses server or local
  │
  ▼
200 { version: N+1, updatedAt }
session.version = N+1
```

---

## 7. Static Content Flow — Roadmap Data

The built-in AI Engineer curriculum is **static** — it is not stored in the database and cannot be edited through the UI (the `roadmaps` row for it holds only metadata; users can still add custom topics/months, stored in their progress):

```
data/roadmap.md          (human-edited Markdown source)
        │
        ▼
python scripts/md_to_json.py
        │
        ├── data/roadmap.json   (structured JSON, for tooling)
        └── data/roadmap.js     (window.ROADMAP_DATA = {...}; served to browser)
```

The browser loads `data/roadmap.js` as a `<script>` tag. `app.js` keeps it as `BUILTIN_DATA` and uses it as the curriculum (`DATA`) whenever a `builtin_ai_engineer` roadmap is open; opening a `custom` roadmap switches `DATA` to `BLANK_DATA`, a frozen empty curriculum (no phases, counters, skills checklist or reference). Either way `app.js` builds its flat `INDEX` of all phases/sections/topics/subtasks from `DATA` plus the roadmap's `progress.custom`.

### Custom roadmaps

A custom roadmap therefore has **no stored definition**: its months, sections, topics and tasks are exactly the user's `progress.custom` entries, edited with the existing Month → Section (a week or a theme) → Topic → Tasks editors, which already support adding and deleting at every level. Because those entries are part of the progress blob, the plan and the progress save, version and conflict-resolve together.

Consequences visible in the UI:
- **Skills Checklist** and **Reference** are curriculum-only features, so their tabs are hidden for a custom roadmap (`syncTabs`); the "Interview & career counters" block is hidden when the curriculum has none.
- An empty roadmap shows an onboarding card on Overview ("Add your first month") instead of the stats dashboard; Kanban and Checklist show an empty-state message until tasks exist.
- Month 1 starts in the start month chosen at creation (or the current month); it can be changed later with "Set start month…".

---

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No frontend framework | Zero build complexity; pure HTML+JS loads instantly, no toolchain required for contributors |
| One progress row per roadmap (`roadmap_progress`) | Each roadmap saves, versions and conflicts independently; deleting a roadmap cascades to exactly its own progress |
| Built-in roadmap stored as metadata only (`source = 'builtin_ai_engineer'`) | The curriculum stays a single static bundle shared by all users; the database holds only name, description and per-user progress. A `source` column (no CHECK constraint) leaves room for future roadmap kinds |
| Custom roadmap = empty curriculum + `progress.custom`; no up-front builder, no `definition` column | The original plan (`.claude/specs/generic-tracker-plan.md`) called for a separate roadmap builder and a stored definition. That was **not built**: the app already lets users add and delete months, sections, topics and tasks and stores them in `progress.custom`, so a new custom roadmap simply starts empty and reuses that proven UI and storage. Editing after creation comes for free, there is no schema change, and no progress keys can be orphaned by a changed definition. A creation wizard that pre-fills `progress.custom`, roadmap templates, or a stored definition remain options for a later phase |
| Roadmap SQL isolated in `server/roadmaps/repository.js` | The router is HTTP-only (parse, validate, respond), as the project rules require DB access in `db.js` or repository modules; ownership scoping and compare-and-swap live in one place |
| Starter roadmap seeded in the registration transaction | An account never exists without a roadmap; a failed registration leaves no orphan rows |
| Ownership enforced in every roadmap query (`WHERE id = ? AND user_id = ?`) | Another user's roadmap is indistinguishable from a missing one (404); the user id never comes from the request |
| Dashboard as the post-login landing screen | A fixed entry point that scales from one roadmap to many without changing the roadmap views themselves |
| JWT in httpOnly cookies | Immune to XSS-based token theft; rolling sessions keep UX seamless |
| JSON blob for progress data | Schema flexibility; user additions (custom phases/topics) fit naturally; avoids N+1 DB rows |
| Optimistic concurrency (compare-and-swap) | Safe multi-tab editing without locking; conflict surfaced transparently to user |
| Turso (hosted libSQL) over a local SQLite file or PostgreSQL | SQLite-compatible SQL, so the schema and queries are unchanged; data survives redeploys on Render's ephemeral filesystem without a paid disk; free tier is ample for ~10–20 users. Trade-offs: a network round trip per query, an external dependency with credentials to manage, and free-tier usage limits |
| `createApp` factory pattern | Enables unit-testable Express app; tests inject an in-memory DB and ephemeral port |
| Shared UMD validator | Server validates before writing; browser validates on import — single source of truth for the ProgressStore shape |
| Static file allowlist | Server never accidentally leaks `.env`, `server/`, the local `data/app.db` or `node_modules/` |
| Python parser for roadmap | Keeps curriculum authoring in familiar Markdown; generated JS committed so Python not needed at runtime |
