# Low Level Design — Roadmap Dashboard

## 1. Module Map

```
roadmap-dashboard/
├── index.html                     ← SPA shell (all script/style tags)
├── css/
│   └── styles.css                 ← All UI styles (light + dark theme)
├── js/
│   ├── progress-schema.js         ← UMD validator (browser + Node)
│   ├── api.js                     ← AuthApi + RoadmapApi (fetch wrappers)
│   └── app.js                     ← Entire frontend app (dashboard + roadmap views)
├── data/
│   ├── roadmap.md                 ← Human-edited curriculum source
│   ├── roadmap.json               ← Generated structured JSON
│   └── roadmap.js                 ← Generated window.ROADMAP_DATA
├── scripts/
│   └── md_to_json.py              ← Python parser: md → json + js
├── server/
│   ├── index.js                   ← Boot + graceful shutdown
│   ├── app.js                     ← createApp factory
│   ├── config.js                  ← loadConfig (env vars)
│   ├── db.js                      ← openDb + DDL + legacy user_data migration
│   ├── auth/
│   │   ├── service.js             ← Pure auth helpers
│   │   └── validators.js          ← Input validation
│   ├── roadmaps/
│   │   ├── builtin.js             ← BUILTIN_AI_ENGINEER identity constant
│   │   ├── validators.js          ← validateRoadmapInput, CUSTOM_SOURCE, limits
│   │   ├── progress.js            ← emptyProgress(startMonth)
│   │   └── repository.js          ← createRoadmapRepository(db): all roadmap SQL
│   └── routes/
│       ├── auth.js                ← /api/auth/* handlers
│       └── roadmaps.js            ← /api/roadmaps/* handlers
└── test/
    ├── helpers.js                 ← startServer, client, creds, dp, fixtures
    ├── api.test.js                ← Integration tests (auth, progress, conflicts, isolation)
    ├── roadmaps.test.js           ← Roadmap list/create/delete/restore, ownership, limits, migration
    ├── config.test.js             ← Config unit tests
    └── schema.test.js             ← Schema validator unit tests
```

---

## 2. Server — Detailed Module Design

### 2.1 `server/index.js` — Entry Point

**Responsibilities:**
1. Call `loadConfig()` to read and validate env vars
2. `await openDb(config.dbUrl, config.dbAuthToken)` to connect to Turso and apply the schema (startup runs inside an async `main()`; a startup failure logs the error and exits with code 1)
3. Call `createApp(db, config.sessionSecret, opts)` to build the Express app
4. `app.listen(port)` — bind HTTP server
5. Register `SIGTERM`/`SIGINT` handlers for graceful shutdown (stop HTTP server, then `db.close()`)

---

### 2.2 `server/app.js` — App Factory

**Export:** `createApp(db, sessionSecret, opts) → Express app`

**Middleware stack applied in order:**

```
helmet(cspOptions)              — security headers + Content Security Policy
cookie-parser()                 — parse rd_session cookie
Cache-Control: no-store         — on every /api response
express.json({ limit: '5mb' }) — parse JSON body (5 MB max)
/api/auth/*     → authRouter     — auth routes (rate-limited; /me checks the session itself)
/api/roadmaps/* → roadmapsRouter — protected (router.use(requireAuth) inside)
Static allowlist                — index.html, css/, js/, data/roadmap.js
404 handler                     — all other paths return { error: 'Not found' }
```

**Why factory pattern:** Tests inject `db` as an in-memory libSQL client (`openDb(":memory:")`) and bind to port 0 (ephemeral). No global singletons.

---

### 2.3 `server/config.js` — Config Loader

**Export:** `loadConfig() → Config`

```js
Config {
  port: number,
  dbUrl: string,          // libsql://… | file:… | :memory:
  dbAuthToken: string,    // Turso token ('' for local targets)
  sessionSecret: string,
  cookieSecure: boolean,
  trustProxy: number | boolean,
  bcryptRounds: number
}
```

In production (`NODE_ENV=production`), throws if `SESSION_SECRET` is missing or shorter than 32 characters, if `TURSO_DATABASE_URL` is missing, or if the URL is remote (`libsql:`, `wss:`, `https:` …) and `TURSO_AUTH_TOKEN` is missing. In development, generates a random secret (sessions reset on restart) and, when `TURSO_DATABASE_URL` is unset, falls back to a local file `file:<project>/data/app.db`.

---

### 2.4 `server/db.js` — Database Module

**Export:** `openDb(url, authToken) → Promise<Client>`

```js
async openDb(url, authToken) {
  client = createClient({ url, authToken: authToken || undefined })   // @libsql/client
  await client.batch(SCHEMA_STATEMENTS, 'write')   // CREATE TABLE/INDEX IF NOT EXISTS: users, roadmaps, idx_roadmaps_user, roadmap_progress
  for (sql of MIGRATION_STATEMENTS) ...            // ALTER TABLE users ADD COLUMN first_name / last_name; "duplicate column" errors ignored
  await migrateLegacyUserData(client)              // one-time user_data -> roadmaps/roadmap_progress
  return client
}
```

`migrateLegacyUserData(client)` returns immediately unless a table named `user_data` exists in `sqlite_master`. Otherwise it runs one `client.batch([...], 'write')` transaction that (1) inserts the built-in roadmap row for every user that has no roadmap, (2) copies each `user_data` row into `roadmap_progress` (keeping `data`, `version`, `updated_at`), and (3) runs `ALTER TABLE user_data RENAME TO user_data_legacy`. Since the old table is gone afterwards, later boots skip it. See `database-design.md` §9.

All callers receive the same `@libsql/client` `Client`. Queries are async and parameterised: `await db.execute({ sql, args })` returns `{ rows, rowsAffected, lastInsertRowid }`; numeric columns arrive as JS numbers, `lastInsertRowid` as a `BigInt`. There are no prepared statements, and no `PRAGMA` calls — libSQL enforces foreign keys by default (covered by the `ON DELETE CASCADE` test). Each query is a network round trip to Turso (for `libsql://` URLs), so handlers avoid redundant queries; the data write is a single statement for that reason.

---

### 2.5 `server/auth/service.js` — Auth Service

**Exports:** crypto/JWT helpers, plus the session-lookup helpers `getCurrentUser` and `createRequireAuth`, which are the only functions here that touch the DB (async, via `db.execute`).

| Function | Signature | Notes |
|----------|-----------|-------|
| `getCurrentUser` | `async (req, db, secret) → { id, username, firstName, lastName } \| null` | Verifies the cookie JWT, then `SELECT id, username, first_name, last_name FROM users WHERE id = ?` |
| `createRequireAuth` | `(db, secret) → async middleware` | Sets `req.user`, or responds 401; DB errors are passed to `next(err)` |
| `hashPassword` | `(password) → Promise<hash>` | `bcrypt.hash(password, ROUNDS)` |
| `verifyPassword` | `(password, hash) → Promise<bool>` | `bcrypt.compare(...)` |
| `signToken` | `(payload, secret) → string` | `jwt.sign({ sub, un }, secret, { expiresIn: '7d' })` |
| `verifyToken` | `(token, secret) → payload` | `jwt.verify(...)` — throws on invalid/expired |
| `cookieOptions` | `(secure) → object` | Returns `{ httpOnly, sameSite, path, maxAge, secure }` |
| `DUMMY_HASH` | constant | Pre-computed bcrypt hash used in anti-enumeration login path |

---

### 2.6 `server/auth/validators.js` — Input Validators

**Exports:** `validateName`, `validateUsername`, `validatePassword` (plus `MIN_PASSWORD`, `MAX_PASSWORD_BYTES`). Each returns `{ valid: true }` or `{ valid: false, error: string }`.

```js
validateName(value, field)
  // typeof string, trimmed value matches /^[A-Za-zÀ-ÿ' -]{1,64}$/
  // error: "<field> must be 1–64 letters."

validateUsername(username)
  // typeof string, /^[A-Za-z0-9_-]{3,32}$/
  // error: "Username must be 3-32 characters: letters, numbers, _ or -."

validatePassword(password)
  // typeof string, length >= 8, Buffer.byteLength(password, "utf8") <= 72 (bcrypt limit)
  // errors: "Password must be at least 8 characters." / "Password must be at most 72 bytes."
```

---

### 2.7 `server/routes/auth.js` — Auth Router

**Express Router** mounted at `/api/auth`. `register` and `login` are rate-limited (10 per 15 min per IP; only failed logins count toward the login limit); `check-username` has its own 30-per-window limit.

#### POST `/register`

```
1. validateName(firstName, "First name"), validateName(lastName, "Last name"),
   validateUsername(username), validatePassword(password)  → 400 with the first error
2. hashPassword(password, bcryptCost) → hash
3. await db.batch([
     INSERT INTO users (username, password_hash, first_name, last_name) VALUES (?, ?, ?, ?),
     INSERT INTO roadmaps (user_id, name, description, source) VALUES (last_insert_rowid(), ?, ?, ?)
   ], "write")                       // args for the 2nd statement come from BUILTIN_AI_ENGINEER
   → id = first result's lastInsertRowid
   If isUniqueViolation(err) (code SQLITE_CONSTRAINT_UNIQUE or message "UNIQUE constraint failed")
   → 409 "That username is already taken." (whole transaction rolled back; any other error is rethrown)
4. issueSession → res.cookie('rd_session', signToken(user, secret, 7), cookieOptions)
5. 201 { user: { username, firstName, lastName } }
```

#### POST `/login`

```
1. If username/password are not non-empty strings, or username > 64 chars, or password > 256 bytes → 401 "Invalid credentials"
2. await db.execute({ sql: 'SELECT id, username, password_hash, first_name, last_name FROM users WHERE username = ?', args: [username] })
3. ok = await verifyPassword(password, row ? row.password_hash : dummyHash)   // anti-timing; dummyHash computed once per router
   If !row || !ok → 401 "Invalid credentials"
4. issueSession(res, user)
5. 200 { user: { username, firstName, lastName } }
```

#### POST `/logout`

```
1. res.clearCookie('rd_session', <cookie options without maxAge>)
2. 204
```

#### GET `/me`

```
1. user = await getCurrentUser(req, db, secret)   // verifies the JWT, then loads the user row
   If null → 401 "Not authenticated"
2. issueSession(res, user)                         // rolling session
3. 200 { user: { username, firstName, lastName } }
```

#### GET `/check-username?username=…`

```
1. validateUsername(req.query.username) → 400 if invalid
2. SELECT 1 FROM users WHERE username = ?          // column is COLLATE NOCASE
3. 200 { available: rows.length === 0 }
```

---

### 2.8 `server/roadmaps/builtin.js` — Built-in Roadmap Identity

```js
BUILTIN_AI_ENGINEER = Object.freeze({
  source: "builtin_ai_engineer",
  name: "AI Engineer Roadmap",
  description: "Tier-1 Production AI Engineer — 10-Month Execution Tracker",
});
```

Shared by registration (`routes/auth.js`), the legacy migration (`db.js`) and the restore endpoint (`routes/roadmaps.js`), so the three can never drift apart.

---

### 2.9 Roadmap support modules — `server/roadmaps/`

| Module | Exports | Role |
|--------|---------|------|
| `validators.js` | `validateRoadmapInput(body)`, `CUSTOM_SOURCE` (`"custom"`), `NAME_MAX` (80), `DESCRIPTION_MAX` (300), `MAX_ROADMAPS_PER_USER` (20) | Pure input rules for creating a custom roadmap. Returns `{ valid: true, value: { name, description, startMonth } }` (name and description trimmed, `startMonth` or `null`) or `{ valid: false, error }`. Rejects a missing/blank name, a name over 80 chars or containing control characters (e.g. a newline), a non-string description, a description over 300 chars, and a `startMonth` that is not `YYYY-MM` |
| `progress.js` | `emptyProgress(startMonth)` | Builds `{ items: {}, counters: {}, celebratedPhases: [], settings: startMonth ? { startMonth } : {}, custom: { topics: [], phases: [] } }` — valid input for `validateProgress` |
| `repository.js` | `createRoadmapRepository(db)` | All SQL for roadmaps and progress (below) |

`createRoadmapRepository(db)` returns:

| Method | Statement(s) | Returns |
|--------|--------------|---------|
| `listForUser(userId)` | `SELECT r.id, r.name, r.description, r.source, r.created_at, p.updated_at AS last_activity_at FROM roadmaps r LEFT JOIN roadmap_progress p ON p.roadmap_id = r.id WHERE r.user_id = ? ORDER BY r.created_at, r.id` | `RoadmapRow[]`, each with `lastActivityAt: string \| null` |
| `findOwned(userId, roadmapId)` | `SELECT … FROM roadmaps WHERE id = ? AND user_id = ?` | `RoadmapRow` or `undefined` |
| `countForUser(userId)` | `SELECT COUNT(*) AS n FROM roadmaps WHERE user_id = ?` | number |
| `hasSource(userId, source)` | `SELECT 1 FROM roadmaps WHERE user_id = ? AND source = ?` | boolean |
| `insert(userId, { name, description, source }, initialProgress = null)` | One `db.batch`: `INSERT INTO roadmaps …`; when `initialProgress` is given, also `INSERT INTO roadmap_progress … VALUES (last_insert_rowid(), ?, 1, ?)` | new roadmap id |
| `remove(userId, roadmapId)` | `DELETE FROM roadmaps WHERE id = ? AND user_id = ?` (progress cascades) | boolean (a row was deleted) |
| `getProgress(roadmapId)` | `SELECT data, version, updated_at FROM roadmap_progress WHERE roadmap_id = ?` | `{ data, version, updated_at }` or `undefined` |
| `saveProgress(roadmapId, dataText, clientVersion)` | Compare-and-swap, one statement: version 0 → `INSERT … ON CONFLICT(roadmap_id) DO NOTHING`; else `UPDATE … WHERE roadmap_id = ? AND version = ?` | `{ conflict: false, version, updatedAt }` or `{ conflict: true, row }` (row re-read) |

---

### 2.10 `server/routes/roadmaps.js` — Roadmaps Router

**Export:** `createRoadmapsRouter({ db, requireAuth })` — an Express Router mounted at `/api/roadmaps`. `router.use(requireAuth)` guards every route. The router is **HTTP-only**: it parses ids and bodies, validates, picks status codes and delegates every query to `createRoadmapRepository(db)`.

Internal helpers: `parseId(raw)` (digits-only string → number, else `null`) and `findOwnedFromParams(req)` (`parseId` + `repo.findOwned(req.user.id, id)`, so a malformed id and a foreign id both yield `undefined`).

#### GET `/`

```
1. repo.listForUser(req.user.id)
2. 200 { roadmaps: [ { id, name, description, source, createdAt, lastActivityAt } ] }
```

#### POST `/`

Dispatches on `req.body?.source`:

```
source === BUILTIN_AI_ENGINEER.source  → restoreBuiltin
source !== undefined && source !== CUSTOM_SOURCE → 400 { error: "Unknown roadmap source." }
otherwise (undefined or "custom")      → createCustom

restoreBuiltin:
  1. repo.hasSource(userId, "builtin_ai_engineer") → 409 "You already have this roadmap."
  2. repo.insert(userId, BUILTIN_AI_ENGINEER)                       // no progress row: version 0
  3. 201 { roadmap }

createCustom:
  1. validateRoadmapInput(req.body) → 400 { error } when invalid
  2. repo.countForUser(userId) >= 20 → 409 "You can have at most 20 roadmaps."
  3. progress = startMonth ? emptyProgress(startMonth) : null
  4. repo.insert(userId, { name, description, source: "custom" }, progress)
       // with a start month: roadmap + roadmap_progress(version 1) in one transaction
  5. 201 { roadmap }
```

Examples of bodies that return 400: `{}` and `{ "source": "custom" }` (no name), `{ "source": 5 }`, `{ "source": "enterprise", "name": "x" }`, a name over 80 chars or with a newline, `description` as a number, `startMonth` of `"October"` or `"2027-13"`.

#### DELETE `/:id`

```
1. id = parseId(req.params.id); a malformed id is treated as "not found"
2. repo.remove(userId, id)                                    // roadmap_progress cascades
3. nothing removed → 404 { error: 'Roadmap not found' }; otherwise 204
```

#### GET `/:id/progress`

```
1. roadmap = await findOwnedFromParams(req)  → 404 if none (unknown, foreign or malformed id)
2. row = await repo.getProgress(roadmap.id)
3. No row → 200 { roadmap, data: null, version: 0 }
   Else   → 200 { roadmap, data: JSON.parse(row.data), version, updatedAt }
```

#### PUT `/:id/progress`

```
1. roadmap = await findOwnedFromParams(req)  → 404 (ownership is checked before the body)
2. body.version must be a non-negative integer → 400 '"version" must be a non-negative integer.'
3. validateProgress(body.data) → { ok, errors }
   If !ok → 400 { error: "Data doesn't match the progress schema.", details: errors }
4. result = await repo.saveProgress(roadmap.id, JSON.stringify(body.data), body.version)
     rowsAffected === 1 → { conflict: false, version: body.version + 1, updatedAt: now }
     else               → { conflict: true, row: await getProgress(roadmap.id) }

5. conflict → 409 { error: 'Version conflict',
                    server: row ? { data: JSON.parse(row.data), version, updatedAt } : { data: null, version: 0 } }
   else     → 200 { version, updatedAt }
```

---

## 3. Frontend — Detailed Module Design

### 3.1 `js/api.js` — API Client

Uses the browser `fetch` API with `credentials: "same-origin"` (sends cookies automatically). A single `call(method, path, body)` helper normalises errors: network failures throw with `err.network = true`; HTTP errors throw with `err.status` and `err.body`. No state lives here.

**AuthApi** — published as `window.AuthApi`

| Method | HTTP call | Returns |
|--------|-----------|---------|
| `me()` | `GET /api/auth/me` | `{ user }` or throws |
| `login(username, password)` | `POST /api/auth/login` | `{ user }` or throws |
| `register(firstName, lastName, username, password)` | `POST /api/auth/register` | `{ user }` or throws |
| `checkUsername(username)` | `GET /api/auth/check-username?username=…` | `{ available }` |
| `logout()` | `POST /api/auth/logout` | `null` |

**RoadmapApi** — published as `window.RoadmapApi`

| Method | HTTP call | Returns |
|--------|-----------|---------|
| `list()` | `GET /api/roadmaps` | `{ roadmaps }` |
| `create({ name, description?, startMonth? })` | `POST /api/roadmaps` | `{ roadmap }` (`source: "custom"`) or throws (400 validation, 409 at the 20-roadmap limit) |
| `restoreBuiltin()` | `POST /api/roadmaps` with `{ source: "builtin_ai_engineer" }` | `{ roadmap }` |
| `remove(id)` | `DELETE /api/roadmaps/:id` | `null` |
| `getProgress(id)` | `GET /api/roadmaps/:id/progress` | `{ roadmap, data, version, updatedAt? }` |
| `putProgress(id, data, version)` | `PUT /api/roadmaps/:id/progress` | `{ version, updatedAt }` or throws (409 carries `body.server`) |

There is no combined `window.Api` shim; callers use `AuthApi` or `RoadmapApi` directly.

---

### 3.2 `js/progress-schema.js` — Shared Validator

**UMD module** — works as a browser `<script>` (sets `window.validateProgress`) and as a Node.js `require()` (exports `validateProgress`).

```js
validateProgress(data) → { valid: boolean, errors: string[] }
```

Checks:
- `data` is an object
- `data.items` is an object; each value has a valid `status` enum
- `data.counters` is an object of non-negative numbers
- `data.celebratedPhases` is an array of strings
- `data.settings` is an object (optional fields)
- `data.custom` is an object with optional `phases` and `topics` arrays
- Custom phase/topic ids match required prefixes
- Extra top-level keys are tolerated (non-strict)

---

### 3.3 `js/app.js` — Application Core

Structured as a self-invoking function expression (IIFE) to avoid global namespace pollution.

#### Key Internal Objects

| Name | Purpose |
|------|---------|
| `progress` | In-memory `ProgressStore` of the **open roadmap**; mutated by all user interactions (an empty store while on the dashboard) |
| `session` | `{ username, firstName, lastName, roadmapId, version, dirty, saving, conflict, conflictServer, retries, timer, expiredFor }`. `roadmapId` is `null` on the dashboard; `persist()` and `flushSave()` do nothing unless both `username` and `roadmapId` are set |
| `dashboardRoadmaps` | The roadmap list last rendered on the dashboard (used to look up a name for the delete confirmation) |
| `BUILTIN_DATA` / `BLANK_DATA` | `BUILTIN_DATA` is `window.ROADMAP_DATA`, the static AI Engineer curriculum. `BLANK_DATA` is a frozen empty curriculum `{ meta: { horizonStart: null }, phases: [], counters: [], masteryChecklist: [], reference: [] }` used for custom roadmaps |
| `DATA` | `let` — the curriculum of the **open roadmap**: `BUILTIN_DATA` initially, then set by `openRoadmap` to `BUILTIN_DATA` for a `builtin_ai_engineer` roadmap and `BLANK_DATA` for any other source |
| `INDEX` | Flat array of all subtasks built from `DATA` plus the roadmap's custom content (`progress.custom`), for fast search/filter |

#### Screens and Navigation

| Function | Role |
|----------|------|
| `boot()` | `AuthApi.me()`; 401 → `showAuth("login")`, otherwise `enterDashboard(user)` |
| `submitAuth()` | After a successful login/register calls `enterDashboard(res.user)` |
| `enterDashboard(user)` | Stores the account fields, resets per-roadmap sync state via `resetRoadmapSession(null, 0)`, clears `progress`, fills the profile name fields, hides the auth screen and calls `showDashboard()` |
| `showDashboard()` | Locks the roadmap UI, shows `#dashboardScreen`, calls `RoadmapApi.list()`, then `renderDashboard()`; a 401 goes to `handleSessionExpired()`, other errors render a Retry state |
| `renderDashboard(roadmaps)` | Renders one card per roadmap (name, description, last activity, **Open** / **Delete**), a "Restore AI Engineer Roadmap" card when the account has no `builtin_ai_engineer` roadmap, an enabled "Create new roadmap" card (`create-roadmap`), and a disabled "Create roadmap with AI" card marked *Coming soon*. Names and descriptions are inserted through `esc()` |
| `onDashboardClick(e)` | One delegated handler on `#dashboardContent` for `open-roadmap`, `delete-roadmap`, `restore-builtin`, `create-roadmap`, `retry-dashboard` |
| `openCreateRoadmapModal()` | Opens the shared modal with a `<form id="createRoadmapForm">`: name (max 80), description (max 300), and a `type="month"` start month defaulting to, and not earlier than, the current month; Cancel is `type="button"` so only Enter / "Create roadmap" submits |
| `submitCreateRoadmap()` | Called from a delegated `submit` listener on `#modalHost`. Checks a name is present and the start month is not in the past (inline error in `#createRoadmapError`), disables the submit button, calls `RoadmapApi.create`, closes the modal and calls `openRoadmap(newId)`. A 401 goes to `handleSessionExpired()`; any other error is shown inline and the button is re-enabled |
| `confirmDeleteRoadmap(id)` | Opens the shared modal asking for confirmation (names the roadmap, warns it is permanent); the modal's `confirm-delete-roadmap` action calls `deleteRoadmap(id)` → `RoadmapApi.remove` → refresh |
| `restoreBuiltinRoadmap()` | `RoadmapApi.restoreBuiltin()`, then refreshes; a 409 ("already have it") just refreshes |
| `openRoadmap(id)` | Shows a loading block, `RoadmapApi.getProgress(id)`; on failure shows Retry / "Back to roadmaps" (never an empty editable state). On success: `resetRoadmapSession(id, version)`, **`DATA = source === "builtin_ai_engineer" ? BUILTIN_DATA : BLANK_DATA`**, `progress = normalizeProgress(data)`, `resetViewState()`, `rebuildIndex()`, `syncTabs()`, sets `#roadmapTitle` / `#roadmapSubtitle` from the roadmap, clears search, `setView("overview")`. The one-time legacy browser-storage import is offered only for a `builtin_ai_engineer` roadmap with no saved data |
| `resetViewState()` | Clears per-roadmap UI state so nothing leaks between roadmaps: `kanbanState.phase = null`, Checklist status/month filters back to "all", and the `expandedPhases` / `sectionOpenState` maps emptied |
| `syncTabs()` | Hides the **Skills Checklist** and **Reference** tabs when `DATA.masteryChecklist` / `DATA.reference` are empty (always the case for a custom roadmap) and shows them otherwise |
| `backToDashboard()` | `settleUnsavedChanges("Leave")`, then `resetRoadmapSession(null, 0)`, clears `progress`, closes any modal and calls `showDashboard()` |
| `settleUnsavedChanges(verb)` | If edits are pending, awaits `flushNow()`; if they still can't be saved, asks the user whether to discard them. Shared by `backToDashboard()` and `logout()` |
| `handleSessionExpired()` | Clears the save timer and `session.username`, then shows the login form; mentions unsaved changes and offers the JSON download only if a roadmap was open |

#### State Mutation Pattern

Every user interaction that changes progress follows the same pattern:
```js
setItemFields(id, { status: newStatus });   // updates progress.items[id] (+ completedAt) and calls persist()
rerender();                                 // re-render the active view
checkMilestones();
```

#### Autosave

```js
persist() {
  if (!session.username || session.roadmapId == null) return;   // nothing open, nothing to save
  session.dirty = true;
  if (session.conflict) return;
  if (session.saving) { setSaveStatus("saving"); return; }
  scheduleSave(1500);                                           // debounced 1500 ms
}

async flushSave() {
  if (session.saving || !session.dirty || session.conflict || !session.username || session.roadmapId == null) return;
  session.saving = true; session.dirty = false;
  try {
    const r = await RoadmapApi.putProgress(session.roadmapId, snapshot, session.version);
    session.version = r.version; session.retries = 0;
    // edited while in flight -> schedule another save
  } catch (e) {
    // 409 -> session.conflict = true; conflict modal (load server / overwrite)
    // 401 -> handleSessionExpired()
    // 400 / 413 -> "Save failed" status + error toast
    // anything else -> retry after 2s, 5s, 15s, then show an error
  } finally { session.saving = false; }
}
```

Additional save triggers: `visibilitychange` (tab hidden), `online` event (reconnect), `beforeunload` warning if dirty or saving.

#### View Rendering

```js
function renderView(viewName) {
  currentView = viewName;
  const main = document.getElementById('main');
  main.innerHTML = '';
  switch (viewName) {
    case 'overview':   renderOverview(main); break;
    case 'timeline':   renderTimeline(main); break;
    case 'kanban':     renderKanban(main);   break;
    case 'checklist':  renderChecklist(main);break;
    case 'thisweek':   renderThisWeek(main); break;
    case 'mastery':    renderMastery(main);  break;
    case 'reference':  renderReference(main);break;
  }
}
```

All event handling uses **event delegation** on `document` or `main` — no per-element listeners that could leak on re-render.

#### View Responsibilities

| View | What it renders |
|------|----------------|
| `overview` | Progress stats, phase progress bars, velocity chart, counters (the counters block is omitted when `DATA.counters` is empty). With **no months at all** it renders `renderBlankRoadmap()` instead: an onboarding card explaining Month → Section → Topic → Tasks with an "Add your first month" button (`add-month`) |
| `timeline` | Expandable month → section → topic → subtask drill-down tree; with no months it adds a "No months yet" hint above the add-month button |
| `kanban` | Per-month board with 4 columns (To Do / In Progress / Blocked / Done); drag-and-drop. Uses `allPhases()[0]` when the remembered month no longer exists; with no months it shows an empty-state message |
| `checklist` | Flat task list; filter by status and phase. With no tasks at all it says the roadmap has no tasks yet and points at the Timeline |
| `thisweek` | Tasks in current calendar week or due within 7 days |
| `mastery` | Skills checklist (not calendar-bound) — AI Engineer roadmap only (tab hidden by `syncTabs`) |
| `reference` | Read-only strategy/background content from ROADMAP — AI Engineer roadmap only (tab hidden by `syncTabs`) |

The Overview "Timeline" tile uses `horizonEnd()`, which clamps to at least one month so an empty roadmap never computes a date from month 0.

---

## 4. Data Flow Diagrams

### 4.1 App Bootstrap

```
Browser loads index.html
  → <script> loads data/roadmap.js, progress-schema.js, api.js, app.js (in order)
  → app.js IIFE runs init() → boot():
      AuthApi.me()
        → 401: show login/register form (submitAuth → enterDashboard on success)
        → 200: enterDashboard(user)
               session.username = user.username; session.roadmapId = null
               showDashboard() → RoadmapApi.list() → renderDashboard(roadmaps)
      user clicks "Open" on a card → openRoadmap(id)
               RoadmapApi.getProgress(id)
                 → { data: null, version: 0 } → progress = empty store
                 → { data, version }          → progress = normalizeProgress(data); session.version = version
               session.roadmapId = id
               DATA = builtin_ai_engineer ? BUILTIN_DATA : BLANK_DATA
               resetViewState(); INDEX = buildIndex(DATA + custom content); syncTabs()
               setView('overview')
      user clicks "Create new roadmap" → modal form → RoadmapApi.create(...) → openRoadmap(newId)
      "←" button → backToDashboard() (flushes pending saves first)
```

### 4.2 Conflict Resolution Flow

```
tab-A: save() → PUT { data: A, version: 5 } → 200 { version: 6 }
tab-B: save() → PUT { data: B, version: 5 } → 409 { server: { data: A, version: 6 } }

tab-B app.js:
  session.conflict = true
  session.conflictServer = { data: A, version: 6 }
  showConflictModal():
    Option 1 "Use server version":
      progress = session.conflictServer.data
      session.version = session.conflictServer.version
      session.conflict = false
      renderCurrentView()
    Option 2 "Keep my changes":
      session.version = session.conflictServer.version   // adopt server version number
      save()                                              // re-attempt with updated version
```

### 4.3 Roadmap Content Update (Developer Flow)

```
Edit data/roadmap.md
  ↓
python scripts/md_to_json.py
  ↓
data/roadmap.json (updated)
data/roadmap.js   (updated — window.ROADMAP_DATA = {...})
  ↓
git commit data/roadmap.json data/roadmap.js
  ↓
Server restart / browser refresh
  → app.js reads updated window.ROADMAP_DATA
  → Existing user progress preserved (subtask IDs are stable)
```

---

## 5. Test Architecture

### `test/helpers.js`

```js
startServer(opts) → { db, base, close }
  // Creates in-memory DB, calls createApp(...), binds port 0, returns base URL

client(baseUrl) → { jar, request, get, post, put }
  // Wraps fetch with cookie jar (manual Set-Cookie / Cookie header tracking)
  // Enables multi-request auth session in tests; DELETE goes through request("DELETE", path)

creds(username, password?) → { firstName, lastName, username, password }   // registration payload
dp(client) → "/api/roadmaps/<id>/progress"
  // progress path of the logged-in client's first (seeded) roadmap; looked up fresh on each call
sampleData(overrides?) → valid ProgressStore fixture
```

### Test Coverage

| File | Scope |
|------|-------|
| `test/api.test.js` | Full HTTP integration: register, login, logout, me, progress save/load via `/api/roadmaps/:id/progress`, conflict, cross-user isolation, static serving, 404 for sensitive paths, rate limit |
| `test/roadmaps.test.js` | Starter-roadmap seeding, list/restore/delete, ownership (another user's or malformed id → 404), atomic registration, the one-time `user_data` migration (copies progress and version, renames to `user_data_legacy`, never re-seeds a deleted roadmap), and the **custom roadmaps** block: create (trimmed name, listed after the starter, empty progress), start month seeded as version 1 and saveable, custom content staying separate per roadmap, input validation (blank/over-long/multi-line name, bad description or `startMonth`), markup in names stored verbatim, the 20-roadmap cap (and deleting frees a slot), cross-user isolation, and progress removed on delete |

The suite has 59 tests (`npm test`).
| `test/config.test.js` | `loadConfig()` with various env var combinations; production secret validation |
| `test/schema.test.js` | `validateProgress()`: valid stores, each invalid field type, nested violations, extra top-level keys |

Run: `npm test` → `node --test "test/*.test.js"`
