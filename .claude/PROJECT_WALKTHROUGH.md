# Project Walkthrough — Roadmap Dashboard

**Session context:** Written before the refactor from a single hardcoded "AI Engineer Roadmap" to a
generic multi-roadmap tracker, and updated after **Phase 1** (multi-roadmap infrastructure: roadmap
dashboard, per-roadmap progress, open/delete/restore). Still to come: Phase 2 (custom roadmap
builder) and Phase 3 (polish, "Create with AI"). See `.claude/specs/generic-tracker-plan.md`.

---

## 1. What the App Is

A **multi-user, multi-roadmap progress tracker** (branded "Roadmap Tracker"). After login a user
lands on a **roadmap dashboard** listing their roadmaps; every account starts with the built-in
10-month AI Engineer roadmap (Oct 2026 → Jul 2027), which can be opened, deleted (with confirmation)
and restored. Opening a roadmap shows the familiar views, and progress is stored server-side **per
roadmap**, tied to the authenticated account. Creating custom roadmaps is shown as "Coming soon".

**Key characteristics:**
- Zero-build frontend: plain HTML + CSS + vanilla ES2022 JS, no bundler, no framework
- Express 5 server backed by Turso (hosted libSQL / SQLite-compatible)
- JWT in httpOnly cookies — no localStorage for auth state
- Optimistic concurrency on progress saves (compare-and-swap on `version`)
- Deployable to Render with no persistent disk needed (Turso handles data)

---

## 2. Repository Layout

```
roadmap-dashboard/
├── index.html                  SPA shell — auth screen, roadmap dashboard, and views rendered into <main id="main">
├── css/styles.css              All styles; light/dark theme via CSS vars
│
├── js/
│   ├── app.js                  ~2.2k-line IIFE — dashboard, views, auth UI, sync
│   ├── api.js                  Thin fetch wrappers → AuthApi / RoadmapApi
│   └── progress-schema.js      UMD validator (browser + Node); validates ProgressStore shape
│
├── data/
│   ├── roadmap.md              ★ Human-edited Markdown source of truth for curriculum
│   ├── roadmap.json            Generated structured JSON (tooling / debug)
│   ├── roadmap.js              Generated window.ROADMAP_DATA script served to browser
│   ├── schema.md               TypeScript-style type docs for roadmap.json + ProgressStore
│   └── app.db / .db-shm / .db-wal   Local SQLite dev database (git-ignored)
│
├── server/
│   ├── index.js                Entry point — boot, port bind, graceful shutdown
│   ├── app.js                  createApp() factory — composes everything, fully testable
│   ├── config.js               loadConfig() — reads + validates env vars
│   ├── db.js                   openDb() — libSQL client + schema + column migrations + legacy user_data migration
│   ├── auth/
│   │   ├── service.js          Pure helpers: bcrypt, JWT, cookie options, requireAuth MW
│   │   └── validators.js       validateUsername / validatePassword / validateName
│   ├── roadmaps/
│   │   └── builtin.js          BUILTIN_AI_ENGINEER (source, name, description of the starter roadmap)
│   └── routes/
│       ├── auth.js             /api/auth/* (register, login, logout, me, check-username)
│       └── roadmaps.js         /api/roadmaps: list, restore, delete, GET|PUT /:id/progress (CAS)
│
├── scripts/
│   └── md_to_json.py           Python 3 parser: roadmap.md → roadmap.json + roadmap.js
│
├── test/
│   ├── api.test.js             Integration tests (auth flow, progress CRUD, concurrency, isolation)
│   ├── roadmaps.test.js        Roadmap list/restore/delete, ownership, atomic register, migration
│   ├── config.test.js          Unit tests for loadConfig()
│   ├── schema.test.js          Unit tests for validateProgress()
│   └── helpers.js              Test harness: startServer(), client(), creds(), sampleData
│
├── documentation/
│   ├── high-level-design.md    Architecture overview + key design decisions
│   ├── low-level-design.md     Detailed module breakdown
│   ├── api-design.md           Full REST API reference
│   ├── database-design.md      Schema, ER diagram, query patterns, security notes
│   └── engineering-foundations.md  Coding patterns and conventions
│
├── .claude/
│   ├── PROJECT_WALKTHROUGH.md  ← this file
│   └── specs/                  Implementation plans for past/current features
│
├── .env.example                Required env vars documented
├── render.yaml                 Render.com deployment config
└── package.json                Node >=22, scripts: dev / start / test
```

---

## 3. Architecture at a Glance

```
Browser (index.html)
  ├── data/roadmap.js  →  window.ROADMAP_DATA  (static curriculum)
  ├── js/progress-schema.js  →  window.ProgressSchema
  ├── js/api.js        →  window.AuthApi, window.RoadmapApi
  └── js/app.js        →  IIFE with all state + rendering
         │  fetch (credentials: same-origin, Cookie: rd_session=<JWT>)
Express 5 server (:3000)
  ├── /api/auth/*   → server/routes/auth.js
  ├── /api/roadmaps → server/routes/roadmaps.js
  └── static        → index.html, css/, js/, data/roadmap.js  (allowlist only)
         │  @libsql/client (async)
Turso (hosted libSQL)
  ├── users            (id, username, password_hash, first_name, last_name, created_at)
  ├── roadmaps         (id, user_id FK, name, description, source, created_at)
  └── roadmap_progress (roadmap_id FK, data TEXT, version INT, updated_at)
```

### Static file security
The server NEVER serves its project root wholesale. An explicit allowlist in `server/app.js:_applyStaticRoutes` exposes only: `index.html`, `css/*`, `js/*`, `data/roadmap.js`. The local `data/app.db`, `.env`, `server/`, and `node_modules/` are unreachable.

---

## 4. Server — Module by Module

### `server/index.js`
Entry point. Calls `loadConfig()`, `openDb()`, `createApp()`, then binds the port. Registers
SIGINT/SIGTERM handlers for graceful shutdown (closes HTTP server then DB client).

### `server/config.js` — `loadConfig(env)`
Reads env vars; returns a typed `AppConfig` object. Throws in production if:
- `SESSION_SECRET` is absent or < 32 chars
- `TURSO_DATABASE_URL` is absent
- A remote libSQL URL is given without `TURSO_AUTH_TOKEN`

In development, generates a random `SESSION_SECRET` (logins reset on restart) and defaults the DB
to `./data/app.db`.

### `server/db.js` — `openDb(url, authToken)`
Creates a `@libsql/client` instance, runs `SCHEMA_STATEMENTS` as a batch (`CREATE TABLE IF NOT
EXISTS` so startup is idempotent), runs `MIGRATION_STATEMENTS` one-by-one (adds `first_name` /
`last_name` columns to existing databases, silently ignoring duplicate-column errors), then calls
`migrateLegacyUserData`.

**Schema — three tables:**
```
users             id(PK) | username(UNIQUE NOCASE) | password_hash | first_name | last_name | created_at
roadmaps          id(PK) | user_id(FK→users.id CASCADE, indexed) | name | description | source | created_at
roadmap_progress  roadmap_id(PK, FK→roadmaps.id CASCADE) | data(JSON text) | version(INT) | updated_at
```
`source = "builtin_ai_engineer"` rows are metadata only — the curriculum is the static `data/roadmap.js`.

**Legacy migration:** if a `user_data` table exists (the old one-roadmap-per-user schema), one
transaction gives every user the built-in roadmap, copies each `user_data` row into
`roadmap_progress` (keeping version + updated_at) and renames the table to `user_data_legacy`.
No `user_data` table → no-op, so a deleted roadmap is never re-seeded on a later boot.

### `server/app.js` — `createApp(options)`
Pure factory. No global state. Testable by injecting an in-memory DB and ephemeral port.
- Applies Helmet (CSP with `upgrade-insecure-requests: null` for HTTP-ok deployments)
- Mounts `/api/auth` and `/api/roadmaps` routers
- Sets `Cache-Control: no-store` on all API responses
- Applies static allowlist
- Catches `entity.too.large` (413) and `entity.parse.failed` (400) as structured JSON

### `server/auth/service.js`
Pure helpers, no Express dependency:
- `hashPassword(pass, cost)` — bcrypt hash
- `verifyPassword(pass, hash)` — bcrypt compare
- `computeDummyHash(cost)` — pre-computed hash used for constant-time comparison against unknown
  usernames (prevents timing-based user enumeration)
- `signToken(user, secret, days)` — JWT `{ sub: id, un: username }`, HS256, 7-day expiry
- `verifyToken(token, secret)` — returns payload or `null`
- `buildCookieOptions(secure, days)` — httpOnly, SameSite=Lax, configurable Secure flag
- `getCurrentUser(req, db, secret)` — reads cookie → verifies JWT → DB lookup → returns user or null
- `createRequireAuth(db, secret)` — returns an Express middleware that sets `req.user` or 401s

### `server/auth/validators.js`
Validation functions returning `{ valid: true }` or `{ valid: false, error: string }`:
- `validateUsername(u)` — `/^[A-Za-z0-9_-]{3,32}$/`
- `validatePassword(p)` — min 8 chars, max 72 bytes (bcrypt limit)
- `validateName(v, field)` — `/^[A-Za-zÀ-ÿ' -]{1,64}$/` for first/last name

### `server/routes/auth.js`
Rate-limited router (`express-rate-limit`):
| Endpoint | Rate limit | Notes |
|---|---|---|
| `POST /register` | 10 req / 15 min | All requests count |
| `POST /login` | 10 req / 15 min | Successful logins exempt (`skipSuccessfulRequests`) |
| `GET /check-username` | 30 req / 15 min | Lighter limit |
| `POST /logout` | — | No rate limit |
| `GET /me` | — | No rate limit; issues rolling session (refreshes TTL) |

Register inserts the user **and the starter AI Engineer roadmap row in one `db.batch` transaction** (so a duplicate username leaves nothing behind), sets the cookie, and returns `{ user: { username, firstName, lastName } }` (201).

Login uses `dummyHash` when the username is not found to ensure identical response time for wrong-password vs. unknown-user.

### `server/roadmaps/builtin.js`
`BUILTIN_AI_ENGINEER` — the frozen `{ source, name, description }` of the starter roadmap, shared by
registration, the legacy migration and the restore endpoint.

### `server/routes/roadmaps.js`
`router.use(requireAuth)`; every query is scoped to `req.user.id` (`WHERE id = ? AND user_id = ?`), and a
malformed, unknown or foreign `:id` is a 404.
- `GET /api/roadmaps` — the user's roadmaps with `lastActivityAt` (the progress row's `updated_at`, or `null`)
- `POST /api/roadmaps` — only `{ source: "builtin_ai_engineer" }` is accepted (restore): 201, 409 if the user already has it, 400 otherwise
- `DELETE /api/roadmaps/:id` — 204; `roadmap_progress` cascades
- `GET /api/roadmaps/:id/progress` — `{ roadmap, data, version, updatedAt }` or `{ roadmap, data: null, version: 0 }`
- `PUT /api/roadmaps/:id/progress` — validates via `validateProgress`, then a **compare-and-swap**:
  - `version === 0` → `INSERT ... ON CONFLICT DO NOTHING`
  - `version > 0` → `UPDATE ... WHERE roadmap_id = ? AND version = ?`
  - If `rowsAffected !== 1` → re-read row and return **409 Conflict** with server's copy

---

## 5. Frontend — Module by Module

### `data/roadmap.js` — `window.ROADMAP_DATA`
Generated by `scripts/md_to_json.py` from `data/roadmap.md`. Structure:
```
{
  phases: [
    {
      id, number, title, objective, exitCriteria, notes, deliverables,
      sections: [
        { id, title, type: "week"|"theme", weekNumber, topics: [
            { id, title, depth, kind: "study"|"build"|"benchmark",
              groups: [{ label, subtasks: [{ id, title }] }] }
          ]
        }
      ]
    }
  ]
}
```

### `js/progress-schema.js` — `window.ProgressSchema`
UMD module (works in both browser via `<script>` and Node via `require()`). Exports
`validateProgress(data) → { ok, errors[] }`. Validates the `ProgressStore` shape:
- `items` — map of subtask ID → `{ status, notes, link, dueDate, completedAt }`
- `counters` — map of counter ID → non-negative number
- `celebratedPhases` — string[]
- `settings` — `{ startMonth?: "YYYY-MM" }`
- `custom` — `{ phases: [...], topics: [...] }` for user-created content

Tolerates unknown top-level keys (import/export compatibility). Stops after 8 errors.

### `js/api.js` — `window.AuthApi`, `window.RoadmapApi`
Thin wrappers around `fetch`. Single `call(method, path, body)` helper normalises:
- Network errors → `err.network = true`
- HTTP errors → `err.status`, `err.body`

Exports:
- `AuthApi.me()`, `.login()`, `.register(firstName, lastName, username, password)`,
  `.checkUsername(username)`, `.logout()`
- `RoadmapApi.list()`, `.restoreBuiltin()`, `.remove(id)`, `.getProgress(id)`, `.putProgress(id, data, version)`
- There is no combined `window.Api` shim any more; `app.js` calls `AuthApi` / `RoadmapApi` directly

### `js/app.js` — the SPA (~2.2k lines, single IIFE)
All application logic in one file. Key sections:

**Navigation flow** — `boot()` → `AuthApi.me()` → `enterDashboard(user)` (also called after login/register)
→ `showDashboard()` / `renderDashboard(roadmaps)` (`GET /api/roadmaps`) → user opens a card →
`openRoadmap(id)` (`GET /api/roadmaps/:id/progress`) → roadmap views. The header "←" button runs
`backToDashboard()`, which first flushes unsaved edits (`settleUnsavedChanges`, shared with `logout()`).

**Roadmap dashboard** — `#dashboardScreen` in `index.html`: one card per roadmap (name, description,
last activity, **Open** / **Delete**), a "Restore AI Engineer Roadmap" card when the account has none, and
disabled "Create new roadmap" / "Create roadmap with AI" cards marked *Coming soon*. One delegated click
handler (`onDashboardClick`). **Delete** opens the shared modal (`confirmDeleteRoadmap`) and only the
modal's "Delete roadmap" button calls `RoadmapApi.remove`.

**Progress store** — in-memory `progress` object. Every mutation calls `persist()` which debounces
a server save. `normalizeProgress(parsed)` ensures the store always has all required keys.

**Flat INDEX** — `rebuildIndex()` flattens all phases → sections → topics → subtasks into a single
array used by all views for search, filtering, and stats.

**Views** rendered into `<main id="main">`:
| Tab | View key | What it shows |
|---|---|---|
| Overview | `overview` | Phase cards with progress bars + stat tiles |
| Timeline | `timeline` | Months/weeks with expandable topic rows |
| Kanban | `kanban` | 4 columns (Not started / In progress / Completed / Blocked) |
| Checklist | `checklist` | Flat filterable list of all subtasks |
| This Week | `thisweek` | Current week's tasks based on `startMonth` setting |
| Skills Checklist | `mastery` | Topic-level depth tracking |
| Reference | `reference` | Static reference material from roadmap |

**Auth UI** — `setAuthMode(mode)` toggles login/register form. `submitAuth()` calls the API,
stores session info, then calls `enterDashboard()`. The session object holds:
`{ username, firstName, lastName, roadmapId, version, dirty, saving, conflict, ... }`; `roadmapId` is `null`
on the dashboard, and `persist()` / `flushSave()` do nothing without it. `openRoadmap()` sets the header title and
subtitle (`#roadmapTitle`, `#roadmapSubtitle`) from the roadmap.

**Server sync** — `persist()` sets `session.dirty = true` and calls `scheduleSave(1500ms)`.
`flushSave()` calls `RoadmapApi.putProgress(session.roadmapId, progress, session.version)`. On 409, opens a conflict modal.

**Profile panel** — dropdown from header trigger. Contains: full name + username display, search,
theme toggle (light/dark), start-month setting, export/import JSON, legacy localStorage import,
reset, logout.

**Custom content** — users can add custom topics (attached to a section) and custom phases
(months 11+). These are stored in `progress.custom` and merged into `ALL_PHASES` / `INDEX` on
rebuild so they appear in every view.

---

## 6. Curriculum Content Pipeline

```
data/roadmap.md          (human edits here)
        ↓
python3 scripts/md_to_json.py
        ↓
data/roadmap.json        (structured JSON, for tooling)
data/roadmap.js          (window.ROADMAP_DATA = {...}; committed to repo)
```

The generated `roadmap.js` is committed so Python is not needed at runtime. The parser
(`scripts/md_to_json.py`) understands a specific Markdown convention:
- H1 `MONTH N — CALENDAR LABEL` starts a phase
- H2 `## Week N — Title` starts a week section
- H3 headings are topics (may carry depth suffix `— D1` / `— D2/D3` etc.)
- `- [ ] ...` checklist items are subtasks; a preceding plain line ending in `:` is a group label
- Months 9 and 10 use theme sections instead of weekly sections (handled by `SECTION_ROUTING`)

---

## 7. Authentication & Session Flow

1. User submits register/login form
2. Server validates input, bcrypt-hashes password on register, verifies on login
3. Server signs JWT `{ sub: userId, un: username }` (HS256, 7d)
4. Sets `Set-Cookie: rd_session=<JWT>; HttpOnly; SameSite=Lax; [Secure]`
5. Browser sends cookie automatically on every `fetch` with `credentials: "same-origin"`
6. `requireAuth` middleware (applied to every `/api/roadmaps` route) verifies JWT + DB-confirms user exists → sets `req.user`
7. `GET /api/auth/me` acts as rolling session — reissues cookie on each call

---

## 8. Data Sync & Concurrency Control

```
User action → in-memory progress update → persist() → debounce 1500ms
        → RoadmapApi.putProgress(session.roadmapId, progress, session.version)
        → PUT /api/roadmaps/:id/progress { data, version: N }
        → server: UPDATE roadmap_progress ... WHERE roadmap_id = ? AND version = N
        → rowsAffected = 1 → 200 { version: N+1 }  → session.version++
        → rowsAffected = 0 → 409 { error, server: { data, version } }
                           → conflict modal → user picks server or local
```

Version 0 means "no row yet" — triggers `INSERT ... ON CONFLICT DO NOTHING` (safe first-save).

---

## 9. Environment Variables

| Variable | Dev default | Prod required | Description |
|---|---|---|---|
| `SESSION_SECRET` | random (logins reset on restart) | ✅ ≥32 chars | JWT signing key |
| `TURSO_DATABASE_URL` | `file:./data/app.db` | ✅ | libSQL target URL |
| `TURSO_AUTH_TOKEN` | empty | ✅ for remote URLs | Turso auth token |
| `PORT` | 3000 | optional | HTTP port |
| `NODE_ENV` | — | `production` | Enables strict checks |
| `TRUST_PROXY` | false | typically `1` on Render | Proxy hop count |
| `COOKIE_SECURE` | false (dev) / true (prod) | optional | Force-override Secure flag |

---

## 10. Testing

Tests run with Node's built-in test runner: `npm test` → `node --test "test/*.test.js"`.

| File | What it tests |
|---|---|
| `test/api.test.js` | Full integration: auth flow, progress CRUD via `/api/roadmaps/:id/progress`, optimistic concurrency, cross-user isolation, cascade delete |
| `test/roadmaps.test.js` | Starter-roadmap seeding, list/restore/delete, ownership (404s), atomic registration, one-time `user_data` migration |
| `test/config.test.js` | `loadConfig()` validation, error cases, env var parsing |
| `test/schema.test.js` | `validateProgress()` acceptance and rejection cases |
| `test/helpers.js` | `startServer()` (in-memory DB, ephemeral port), HTTP `client()` with cookie jar, `creds()` (includes first/last name), `dp(client)` (progress path of the first roadmap), `sampleData()` |

---

## 11. Deployment (Render)

`render.yaml` defines a Node web service:
- `buildCommand: npm install`
- `startCommand: npm start` (`cross-env NODE_ENV=production node server/index.js`)
- `SESSION_SECRET` auto-generated by Render
- `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` set manually in Render dashboard
- `TRUST_PROXY=1` for Render's reverse proxy

No persistent disk needed — all data lives in Turso.

**Phase 1 rollout:** on first boot the new code migrates `user_data` → `roadmaps` + `roadmap_progress` and renames the old table to `user_data_legacy`. Stop any older instance before the new one boots, since the old code can no longer find `user_data`.

---

## 12. Hardcoded "AI Engineer" References (Refactor Status)

Status after **Phase 1** (multi-roadmap infrastructure):

| Location | Hardcoded content | Status |
|---|---|---|
| `index.html` `<title>` | "AI Engineer Roadmap — Progress Dashboard" | **Done** — now "Roadmap Tracker"; `openRoadmap()` sets `document.title` to "<roadmap name> — Roadmap Tracker" and the dashboard resets it |
| `index.html` `.brand` (roadmap header) | "AI Engineer Roadmap" + subtitle "Tier-1 Production AI Engineer — 10-Month Execution Tracker" | **Done** — `#roadmapTitle` / `#roadmapSubtitle` are filled from the opened roadmap's `name` / `description` |
| `index.html` auth brand (login form and loading block) | "🧭 AI Engineer Roadmap" in `.auth-brand` | **Done** — now "Roadmap Tracker" |
| `index.html` footer | "AI Engineer Roadmap. All rights reserved." in `.auth-footer-copy` | **Done** — now "Roadmap Tracker. All rights reserved." |
| `server/roadmaps/builtin.js` | Name/description of the starter roadmap | By design — the only place the built-in roadmap's identity lives |
| `data/roadmap.md` | The entire 10-month AI Engineer curriculum content | Unchanged — still the built-in roadmap's content |
| `data/roadmap.js` | Generated from roadmap.md; contains `window.ROADMAP_DATA` | Unchanged — `const DATA = window.ROADMAP_DATA` in `js/app.js` is still static; Phase 2 must make it per-roadmap |
| `package.json` `.description` | "AI Engineer roadmap progress dashboard…" | Not yet changed |
| `js/app.js` `STORAGE_KEY` | `"roadmap-dashboard:progress:v1"` (generic, OK) | No change needed; legacy browser-data import is offered only for the built-in roadmap |
| `documentation/` | Docs describe the single-roadmap app | **Done** for Phase 1 — API, database, HLD, LLD and engineering-foundations now describe roadmaps, `roadmap_progress` and the dashboard flow |

Still hardcoded in views (Phase 2 targets): `DATA.counters`, `DATA.masteryChecklist`, `DATA.reference` and `DATA.meta.horizonStart` are read directly, so a custom roadmap without them would need those tabs/fields guarded.

The roadmap data itself (`window.ROADMAP_DATA`) is consumed generically by `app.js` — the
phase/section/topic/subtask structure is data-driven. The views don't know the content is about AI.
