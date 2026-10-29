# High Level Design — Roadmap Dashboard

## 1. System Overview

The Roadmap Dashboard (branded **Roadmap Tracker**) is a multi-roadmap progress tracker. After logging in, a user lands on a **roadmap dashboard** listing their roadmaps and can open one, delete one (after confirmation), or restore the built-in one. Every account starts with the **AI Engineer Roadmap** — a 10-month curriculum (phases → sections → topics → subtasks) — where the user records progress, adds custom content, and visualises completion across multiple views. Progress is stored on the server **per roadmap**, tied to the authenticated user account, with optimistic concurrency control to handle multi-tab edits. Creating custom roadmaps ("Create new roadmap", "Create with AI") is shown as *coming soon* and is planned for later phases.

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
│  server/db.js            (libSQL client + schema +          │
│                           legacy migration)                 │
│  ├── server/auth/                                           │
│  │   ├── service.js      (bcrypt + JWT helpers, requireAuth)│
│  │   └── validators.js   (username/password/name rules)     │
│  ├── server/roadmaps/                                       │
│  │   └── builtin.js      (built-in roadmap identity)        │
│  └── server/routes/                                         │
│      ├── auth.js         (/api/auth/*)                      │
│      └── roadmaps.js     (/api/roadmaps/*)                  │
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
| `js/api.js` | `AuthApi` (register/login/logout/me/checkUsername) and `RoadmapApi` (list/restoreBuiltin/remove/getProgress/putProgress) using `fetch` |
| `js/progress-schema.js` | UMD validator shared with server; validates `ProgressStore` shape |
| `data/roadmap.js` | Static content — `window.ROADMAP_DATA`; generated from `data/roadmap.md` |
| `css/styles.css` | All application styles (light/dark theme support) |

### 3.2 Backend (Express 5)

| Module | Purpose |
|--------|---------|
| `server/index.js` | Entry point — calls `createApp`, binds port, sets up graceful shutdown |
| `server/app.js` | `createApp(db, sessionSecret, opts)` — pure factory, fully testable |
| `server/config.js` | `loadConfig()` — reads env vars, validates required keys, returns config object |
| `server/db.js` | `openDb(url, authToken)` (async) — creates the libSQL client, applies the schema via `batch`, adds missing columns, and runs the one-time `user_data` → `roadmaps` migration |
| `server/auth/service.js` | `hashPassword`, `verifyPassword`, `signToken`, `verifyToken`, cookie options, `getCurrentUser`, `createRequireAuth` |
| `server/auth/validators.js` | `validateUsername`, `validatePassword`, `validateName` — return `{ valid, error }` |
| `server/roadmaps/builtin.js` | `BUILTIN_AI_ENGINEER` — name, description and `source` of the roadmap every account starts with |
| `server/routes/auth.js` | Handles `/api/auth/register` (user + starter roadmap in one transaction), `/login`, `/logout`, `/me`, `/check-username` |
| `server/routes/roadmaps.js` | Handles `/api/roadmaps`: list, restore built-in, delete, and `GET`/`PUT /:id/progress` with optimistic concurrency; all queries scoped to the session user |

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
  │                Create new roadmap / Create with AI (disabled, "Coming soon")
  │
  ├─ Delete → confirmation modal → DELETE /api/roadmaps/:id → refresh list
  ├─ Restore → POST /api/roadmaps { source } → refresh list
  └─ Open → openRoadmap(id)            GET /api/roadmaps/:id/progress
        sets session.roadmapId, session.version; loads progress; rebuilds INDEX;
        header title/subtitle come from the roadmap; starts on the Overview tab
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

The browser loads `data/roadmap.js` as a `<script>` tag. `app.js` reads `window.ROADMAP_DATA` to build its flat `INDEX` of all phases/sections/topics/subtasks.

---

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No frontend framework | Zero build complexity; pure HTML+JS loads instantly, no toolchain required for contributors |
| One progress row per roadmap (`roadmap_progress`) | Each roadmap saves, versions and conflicts independently; deleting a roadmap cascades to exactly its own progress |
| Built-in roadmap stored as metadata only (`source = 'builtin_ai_engineer'`) | The curriculum stays a single static bundle shared by all users; the database holds only name, description and per-user progress. A `source` column (no CHECK constraint) leaves room for future roadmap kinds |
| Starter roadmap seeded in the registration transaction | An account never exists without a roadmap; a failed registration leaves no orphan rows |
| Legacy `user_data` migrated once, renamed not dropped | Preserves every user's progress and version; the old table stays as a safety net (`user_data_legacy`) and its absence makes later boots skip the migration, so a deleted roadmap is never re-seeded |
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
