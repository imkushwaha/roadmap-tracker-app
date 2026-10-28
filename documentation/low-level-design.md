# Low Level Design — Roadmap Dashboard

## 1. Module Map

```
roadmap-dashboard/
├── index.html                     ← SPA shell (all script/style tags)
├── css/
│   └── styles.css                 ← All UI styles (light + dark theme)
├── js/
│   ├── progress-schema.js         ← UMD validator (browser + Node)
│   ├── api.js                     ← AuthApi + DataApi (fetch wrappers)
│   └── app.js                     ← Entire frontend app (~1961 lines)
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
│   ├── db.js                      ← openDb + DDL
│   ├── auth/
│   │   ├── service.js             ← Pure auth helpers
│   │   └── validators.js          ← Input validation
│   └── routes/
│       ├── auth.js                ← /api/auth/* handlers
│       └── data.js                ← /api/data handlers
└── test/
    ├── helpers.js                 ← startServer, client, fixtures
    ├── api.test.js                ← Integration tests
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
express-rate-limit(config)      — global rate limiting (10 req / 15 min / IP)
cookie-parser(sessionSecret)    — parse rd_session cookie
express.json({ limit: '5mb' }) — parse JSON body (5 MB max)
/api/auth/*  → authRouter       — public auth routes (no requireAuth)
/api/data/*  → dataRouter       — protected (requireAuth applied inside)
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
  await client.batch(SCHEMA_STATEMENTS, 'write')   // CREATE TABLE IF NOT EXISTS users / user_data
  return client
}
```

All callers receive the same `@libsql/client` `Client`. Queries are async and parameterised: `await db.execute({ sql, args })` returns `{ rows, rowsAffected, lastInsertRowid }`; numeric columns arrive as JS numbers, `lastInsertRowid` as a `BigInt`. There are no prepared statements, and no `PRAGMA` calls — libSQL enforces foreign keys by default (covered by the `ON DELETE CASCADE` test). Each query is a network round trip to Turso (for `libsql://` URLs), so handlers avoid redundant queries; the data write is a single statement for that reason.

---

### 2.5 `server/auth/service.js` — Auth Service

**Exports:** crypto/JWT helpers, plus the session-lookup helpers `getCurrentUser` and `createRequireAuth`, which are the only functions here that touch the DB (async, via `db.execute`).

| Function | Signature | Notes |
|----------|-----------|-------|
| `getCurrentUser` | `async (req, db, secret) → { id, username } \| null` | Verifies the cookie JWT, then `SELECT id, username FROM users WHERE id = ?` |
| `createRequireAuth` | `(db, secret) → async middleware` | Sets `req.user`, or responds 401; DB errors are passed to `next(err)` |
| `hashPassword` | `(password) → Promise<hash>` | `bcrypt.hash(password, ROUNDS)` |
| `verifyPassword` | `(password, hash) → Promise<bool>` | `bcrypt.compare(...)` |
| `signToken` | `(payload, secret) → string` | `jwt.sign({ sub, un }, secret, { expiresIn: '7d' })` |
| `verifyToken` | `(token, secret) → payload` | `jwt.verify(...)` — throws on invalid/expired |
| `cookieOptions` | `(secure) → object` | Returns `{ httpOnly, sameSite, path, maxAge, secure }` |
| `DUMMY_HASH` | constant | Pre-computed bcrypt hash used in anti-enumeration login path |

---

### 2.6 `server/auth/validators.js` — Input Validators

**Exports:** returns an error string on failure, `null` on success.

```js
validateUsername(username)
  // Checks: typeof string, length 3–32, /^[A-Za-z0-9_-]+$/ pattern
  // Returns: null | "Username must be 3–32 characters and contain only letters, numbers, _ or -"

validatePassword(password)
  // Checks: typeof string, byteLength 8–72 (Buffer.byteLength)
  // Returns: null | "Password must be 8–72 characters"
```

---

### 2.7 `server/routes/auth.js` — Auth Router

**Express Router** mounted at `/api/auth`.

#### POST `/register`

```
1. validateUsername(body.username)  → 400 if error
2. validatePassword(body.password)  → 400 if error
3. hashPassword(password) → hash
4. await db.execute({ sql: 'INSERT INTO users (username, password_hash) VALUES (?, ?)', args: [username, hash] })
   → id = result.lastInsertRowid
   If isUniqueViolation(err) (code SQLITE_CONSTRAINT_UNIQUE or message "UNIQUE constraint failed")
   → 409 "That username is already taken."   (username is UNIQUE COLLATE NOCASE; any other error is rethrown)
5. signToken({ sub: Number(id), un: username }, sessionSecret)
6. res.cookie('rd_session', token, cookieOptions(secure))
7. 201 { user: { username } }
```

#### POST `/login`

```
1. await db.execute({ sql: 'SELECT id, username, password_hash FROM users WHERE username = ?', args: [username] })
   → row = result.rows[0]
   If not found:
     verifyPassword(password, DUMMY_HASH)  // anti-timing
     → 401 "Invalid credentials"
2. verifyPassword(password, row.password_hash)
   If false → 401 "Invalid credentials"
3. signToken({ sub: Number(row.id), un: row.username }, sessionSecret)
4. res.cookie('rd_session', token, cookieOptions(secure))
5. 200 { user: { username } }
```

#### POST `/logout`

```
1. res.clearCookie('rd_session', { path: '/' })
2. 204
```

#### GET `/me`

```
1. requireAuth middleware:
     verifyToken(req.cookies.rd_session, sessionSecret) → { sub, un }
     await db.execute({ sql: 'SELECT id, username FROM users WHERE id = ?', args: [Number(sub)] })
     If not found → 401
     req.user = { id, username: un }
2. signToken({ sub: req.user.id, un: req.user.username }, sessionSecret)  // rolling session
3. res.cookie('rd_session', newToken, cookieOptions(secure))
4. 200 { user: { username } }
```

---

### 2.8 `server/routes/data.js` — Data Router

**Express Router** mounted at `/api/data`. Both routes use `requireAuth` middleware.

#### GET `/`

```
1. requireAuth(req, res, next)
2. row = await getRow(req.user.id)
   // SELECT data, version, updated_at FROM user_data WHERE user_id = ?
3. If no row: return 200 { data: null, version: 0 }
4. JSON.parse(row.data) → parsedData
5. 200 { data: parsedData, version: row.version, updatedAt: row.updated_at }
```

#### PUT `/`

```
1. requireAuth(req, res, next)
2. Validate body.version is non-negative integer → 400 if not
3. validateProgress(body.data) → { valid, errors }
   If !valid → 400 { error: 'Invalid progress data', details: errors }
4. serialised = JSON.stringify(body.data)
5. now = new Date().toISOString()

result = await saveData(userId, serialised, body.version)   // single-statement compare-and-swap:

  if body.version === 0:
    INSERT INTO user_data (user_id, data, version, updated_at) VALUES (?, ?, 1, ?)
    ON CONFLICT(user_id) DO NOTHING
  else:
    UPDATE user_data SET data = ?, version = version + 1, updated_at = ?
     WHERE user_id = ? AND version = ?

  if rowsAffected === 1:
    → { conflict: false, version: body.version + 1, updatedAt: now }
  else:
    row = await getRow(userId)        // re-read the server copy
    → { conflict: true, row }

if result.conflict:
  return 409 { error: 'Version conflict',
               server: row ? { data: JSON.parse(row.data), version: row.version, updatedAt: row.updated_at }
                           : { data: null, version: 0 } }

6. 200 { version: result.version, updatedAt: result.updatedAt }
```

---

## 3. Frontend — Detailed Module Design

### 3.1 `js/api.js` — API Client

Uses the browser `fetch` API with `credentials: "same-origin"` (sends cookies automatically).

**AuthApi** — returned as `window.AuthApi`

| Method | HTTP call | Returns |
|--------|-----------|---------|
| `me()` | `GET /api/auth/me` | `{ user }` or throws |
| `login(u, p)` | `POST /api/auth/login` | `{ user }` or throws |
| `register(u, p)` | `POST /api/auth/register` | `{ user }` or throws |
| `logout()` | `POST /api/auth/logout` | void |

**DataApi** — returned as `window.DataApi`

| Method | HTTP call | Returns |
|--------|-----------|---------|
| `getData()` | `GET /api/data` | `{ data, version, updatedAt }` |
| `putData(data, version)` | `PUT /api/data` | `{ version, updatedAt }` or throws |

`window.Api` provides a merged shim for backward-compat access.

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

### 3.3 `js/app.js` — Application Core (~1961 lines)

Structured as a self-invoking function expression (IIFE) to avoid global namespace pollution.

#### Key Internal Objects

| Name | Purpose |
|------|---------|
| `progress` | In-memory `ProgressStore` object; mutated by all user interactions |
| `session` | `{ username, version, dirty, saving, conflict, conflictServer, retries }` |
| `ROADMAP` | `window.ROADMAP_DATA` — the full static curriculum |
| `INDEX` | Flat array of all subtasks built from `ROADMAP` for fast search/filter |

#### State Mutation Pattern

Every user interaction that changes progress follows the same pattern:
```js
progress.items[subtaskId].status = newStatus;
if (newStatus === 'completed') progress.items[subtaskId].completedAt = new Date().toISOString();
renderCurrentView();   // re-render the active view
persist();             // schedule debounced autosave
```

#### `persist()` — Autosave

```js
persist() {
  session.dirty = true;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, 1500);     // debounced 1500ms
}

async save() {
  if (session.saving) return;             // skip if already in flight
  session.saving = true;
  try {
    const result = await DataApi.putData(progress, session.version);
    session.version = result.version;
    session.dirty = false;
    session.retries = 0;
  } catch (err) {
    if (err.status === 409) {
      session.conflict = true;
      session.conflictServer = err.body.server;
      showConflictModal();
    } else {
      // Exponential backoff: 2s, 5s, 15s
      const delay = [2000, 5000, 15000][Math.min(session.retries, 2)];
      session.retries++;
      setTimeout(save, delay);
    }
  } finally {
    session.saving = false;
  }
}
```

Additional save triggers: `visibilitychange` (tab hidden), `online` event (reconnect), `beforeunload` warning if dirty.

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
| `overview` | Progress stats, phase progress bars, velocity chart, counters |
| `timeline` | Expandable month → section → topic → subtask drill-down tree |
| `kanban` | Per-month board with 4 columns (To Do / In Progress / Blocked / Done); drag-and-drop |
| `checklist` | Flat task list; filter by status and phase |
| `thisweek` | Tasks in current calendar week or due within 7 days |
| `mastery` | Skills checklist (not calendar-bound) |
| `reference` | Read-only strategy/background content from ROADMAP |

---

## 4. Data Flow Diagrams

### 4.1 App Bootstrap

```
Browser loads index.html
  → <script> loads progress-schema.js, api.js, roadmap.js, app.js (in order)
  → app.js IIFE runs:
      ROADMAP = window.ROADMAP_DATA
      INDEX = buildIndex(ROADMAP)        // flat subtask list
      progress = initialProgressStore()  // empty state
      AuthApi.me()
        → 401: show login/register form
        → 200: session.username = user.username
               DataApi.getData()
                 → { data: null } → keep empty progress
                 → { data, version } → progress = data; session.version = version
               renderView('overview')
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
startServer(opts) → { url, close }
  // Creates in-memory DB, calls createApp(db, secret, opts), binds port 0, returns URL

client(baseUrl) → { get, post, put, fetch }
  // Wraps fetch with cookie jar (manual Set-Cookie / Cookie header tracking)
  // Enables multi-request auth session in tests
```

### Test Coverage

| File | Scope |
|------|-------|
| `test/api.test.js` | Full HTTP integration: register, login, logout, me, data CRUD, conflict, cross-user isolation, static serving, 404 for sensitive paths, rate limit |
| `test/config.test.js` | `loadConfig()` with various env var combinations; production secret validation |
| `test/schema.test.js` | `validateProgress()`: valid stores, each invalid field type, nested violations, extra top-level keys |

Run: `npm test` → `node --test "test/*.test.js"`
