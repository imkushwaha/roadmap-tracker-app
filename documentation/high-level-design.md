# High Level Design — Roadmap Dashboard

## 1. System Overview

The Roadmap Dashboard is a **10-month AI Engineer learning roadmap tracker**. It lets a registered user work through a structured curriculum (phases → sections → topics → subtasks), record their progress, add custom content, and visualise completion across multiple views. All progress data is stored on the server, tied to the authenticated user account, with optimistic concurrency control to handle multi-tab edits.

The application is a **zero-build web app**: the frontend is plain HTML, CSS, and ES2022 JavaScript loaded directly by the browser. There is no compilation step, no bundler, and no frontend framework. The backend is an Express 5 server backed by a SQLite database.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                                                             │
│  index.html                                                 │
│  ├── css/styles.css          (all styles)                   │
│  ├── js/progress-schema.js   (UMD validator, shared)        │
│  ├── js/api.js               (fetch wrappers: AuthApi/DataApi)│
│  ├── data/roadmap.js         (static roadmap content)       │
│  └── js/app.js               (entire SPA logic, ~1961 lines) │
│                                                             │
│  Views rendered into <main id="main">:                      │
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
│  server/db.js            (SQLite init)                      │
│  ├── server/auth/                                           │
│  │   ├── service.js      (bcrypt + JWT helpers)             │
│  │   └── validators.js   (username/password rules)          │
│  └── server/routes/                                         │
│      ├── auth.js         (/api/auth/*)                      │
│      └── data.js         (/api/data GET + PUT)              │
│                                                             │
│  Static serving:                                            │
│  index.html · css/ · js/ · data/roadmap.js  (allowlist)    │
└──────────────────┬──────────────────────────────────────────┘
                   │ better-sqlite3 (sync)
┌──────────────────▼──────────────────────────────────────────┐
│              SQLite — data/app.db                            │
│  users        (id, username, password_hash, created_at)     │
│  user_data    (user_id FK, data JSON, version, updated_at)  │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Topology

| Environment | Server | Database | Notes |
|-------------|--------|----------|-------|
| Development | `node server/index.js` :3000 | `data/app.db` | Random `SESSION_SECRET` on restart |
| Production | Same Express process | Same SQLite file | `SESSION_SECRET` required; `COOKIE_SECURE=true` |

---

## 3. Key Components

### 3.1 Frontend (Vanilla JS SPA)

| File | Purpose |
|------|---------|
| `index.html` | SPA shell; loads all JS/CSS; hosts `<main id="main">` render target |
| `js/app.js` | ~1961-line IIFE: all view rendering, state, sync, auth UI, event handling |
| `js/api.js` | `AuthApi` (register/login/logout/me) and `DataApi` (getData/putData) using `fetch` |
| `js/progress-schema.js` | UMD validator shared with server; validates `ProgressStore` shape |
| `data/roadmap.js` | Static content — `window.ROADMAP_DATA`; generated from `data/roadmap.md` |
| `css/styles.css` | All application styles (light/dark theme support) |

### 3.2 Backend (Express 5)

| Module | Purpose |
|--------|---------|
| `server/index.js` | Entry point — calls `createApp`, binds port, sets up graceful shutdown |
| `server/app.js` | `createApp(db, sessionSecret, opts)` — pure factory, fully testable |
| `server/config.js` | `loadConfig()` — reads env vars, validates required keys, returns config object |
| `server/db.js` | Opens/initialises SQLite (WAL mode, FK on), runs DDL |
| `server/auth/service.js` | `hashPassword`, `verifyPassword`, `signToken`, `verifyToken`, cookie options |
| `server/auth/validators.js` | `validateUsername`, `validatePassword` — returns error strings or null |
| `server/routes/auth.js` | Handles `/api/auth/register`, `/login`, `/logout`, `/me` |
| `server/routes/data.js` | Handles `GET /api/data`, `PUT /api/data` with optimistic concurrency |

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
requireAuth middleware (server/routes/data.js)
  jwt.verify(req.cookies.rd_session) → { id, username }
  db lookup confirms user exists
  sets req.user = { id, username }
        │
        ▼
Route handler processes request
```

`GET /api/auth/me` acts as a **rolling session** — it refreshes the cookie TTL on every call, keeping active users logged in across the 7-day expiry.

---

## 5. Data Flow — Saving Progress

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
DataApi.putData(progress, session.version)
  PUT /api/data { data: ProgressStore, version: N }
        │
  ┌─────┴──────────┐
  │                │
Match            Mismatch
(version OK)     (409 conflict)
  │                │
  ▼                ▼
UPDATE user_data   Return { error, server: { data, version } }
SET version = N+1  Conflict modal → user chooses server or local
  │
  ▼
200 { version: N+1, updatedAt }
session.version = N+1
```

---

## 6. Static Content Flow — Roadmap Data

The roadmap curriculum itself is **static** — it is not stored in the database and cannot be edited through the UI:

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

## 7. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No frontend framework | Zero build complexity; pure HTML+JS loads instantly, no toolchain required for contributors |
| JWT in httpOnly cookies | Immune to XSS-based token theft; rolling sessions keep UX seamless |
| JSON blob for progress data | Schema flexibility; user additions (custom phases/topics) fit naturally; avoids N+1 DB rows |
| Optimistic concurrency (compare-and-swap) | Safe multi-tab editing without locking; conflict surfaced transparently to user |
| SQLite over PostgreSQL | Single-user app (one user's data); zero infrastructure; file is portable |
| `createApp` factory pattern | Enables unit-testable Express app; tests inject in-memory DB and ephemeral port |
| Shared UMD validator | Server validates before writing; browser validates on import — single source of truth for the ProgressStore shape |
| Static file allowlist | Server never accidentally leaks `.env`, `server/`, `data/app.db` or `node_modules/` |
| Python parser for roadmap | Keeps curriculum authoring in familiar Markdown; generated JS committed so Python not needed at runtime |
