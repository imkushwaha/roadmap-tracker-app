# Turso Migration Plan

> ## Implementation status (2026-10-28): code DONE, Turso account + deploy PENDING
>
> All code steps below are implemented; `npm test` passes (41/41) and a real-entrypoint
> smoke test (register, save, restart, login, data still present) passed against a local
> `file:` database. Not yet done: create the Turso DB, run the dev server against it, and
> deploy to Render.
>
> **Deviations from the plan as written:**
> - **Tests did need changes** (the plan said they wouldn't): `test/helpers.js` awaits `openDb`,
>   `test/api.test.js` replaced 4 direct `db.prepare()` calls with `db.execute()`, and
>   `test/config.test.js` now asserts `dbUrl`/`dbAuthToken` and adds Turso-config cases.
> - **Config:** fields are `dbUrl` / `dbAuthToken` (not `tursoUrl`). Dev without
>   `TURSO_DATABASE_URL` falls back to a local file `./data/app.db` (not `:memory:`), so dev
>   data survives restarts. Production requires the URL, and the token for remote URLs.
> - **`data.js`:** uses single-statement compare-and-swap (`UPDATE ... WHERE version = ?`,
>   `INSERT ... ON CONFLICT DO NOTHING`) instead of an interactive transaction. Same
>   semantics, one network round trip instead of four.
> - **Dependency:** `@libsql/client ^0.18.0` (plan said `^0.14.0`).
> - **Not covered by the plan:** README and `documentation/*.md` still describe
>   `better-sqlite3` / `DB_PATH` and need a docs pass.

Migrate `roadmap-dashboard` from a local `better-sqlite3` file-backed database to
[Turso](https://turso.tech) (hosted libSQL) so data persists across Render redeployments
without a paid persistent disk.

**Scope:** server-side only — no frontend, no SQL schema, no test data changes.  
**Effort:** ~1–2 hours.

---

## Prerequisites

### 1. Turso account + database

```bash
# Install Turso CLI (macOS/Linux)
curl -sSfL https://get.tur.so/install.sh | bash

# Windows (PowerShell)
winget install turso

# Authenticate
turso auth login

# Create the database
turso db create roadmap-dashboard

# Get the libsql:// URL
turso db show roadmap-dashboard

# Generate an auth token (keep this secret — treat it like a password)
turso db tokens create roadmap-dashboard
```

Save both values — you will need them in `.env` and in Render's dashboard.

### 2. Local `.env` update

```
# Remove this line:
DB_PATH=./data/app.db

# Add these two:
TURSO_DATABASE_URL=libsql://<your-db-name>.turso.io
TURSO_AUTH_TOKEN=<token from above>
```

---

## Implementation

Work through the files in this order — each step is self-contained and testable.

### Step 1 — Swap the dependency (`package.json`)

```diff
- "better-sqlite3": "^13.0.3",
+ "@libsql/client": "^0.14.0",
```

Run `npm install` after editing.

---

### Step 2 — Update config (`server/config.js`)

Remove `_resolveDbPath` and its `DB_PATH` env var.  
Add two new private helpers and expose them in the returned config object.

**Changes:**
- Remove `_resolveDbPath(env)` helper function entirely.
- Add `_resolveTursoUrl(env, isProduction)` — throws in production if missing.
- Add `_resolveTursoAuthToken(env, isProduction)` — throws in production if missing.
- Update `loadConfig` return object: replace `dbPath` with `tursoUrl` + `tursoAuthToken`.
- Update the `AppConfig` typedef accordingly.

```js
// New helpers to add:
function _resolveTursoUrl(env, isProduction) {
  const url = env.TURSO_DATABASE_URL;
  if (!url && isProduction) throw new Error("TURSO_DATABASE_URL is required in production.");
  return url || ":memory:";  // falls back to in-memory for local dev without Turso
}

function _resolveTursoAuthToken(env, isProduction) {
  const token = env.TURSO_AUTH_TOKEN;
  if (!token && isProduction) throw new Error("TURSO_AUTH_TOKEN is required in production.");
  return token || "";
}
```

> **Note on the `:memory:` fallback:** If `TURSO_DATABASE_URL` is absent in dev,
> `@libsql/client` accepts `":memory:"` and runs an in-process SQLite. This keeps
> `npm run dev` working without Turso credentials. Data resets on restart in that mode.

---

### Step 3 — Rewrite the database module (`server/db.js`)

Full rewrite. The new file is ~30 lines.

**Key differences from `better-sqlite3`:**
- `createClient({ url, authToken })` from `@libsql/client` replaces `new Database(dbPath)`.
- No pragmas — Turso manages WAL and foreign keys in its hosted environment.
  For the `:memory:` fallback, pragmas can be run via `client.execute()` if needed.
- `db.exec(SCHEMA_SQL)` → `await client.batch([stmt1, stmt2], "write")`.
  `batch()` runs multiple statements atomically; each statement is `{ sql: "..." }`.
- `openDb` becomes `async` and returns a `client`.

```js
// Skeleton of the new db.js
const { createClient } = require("@libsql/client");

const SCHEMA_STMTS = [
  { sql: `CREATE TABLE IF NOT EXISTS users (...)` },
  { sql: `CREATE TABLE IF NOT EXISTS user_data (...)` },
];

async function openDb(url, authToken) {
  const client = createClient({ url, authToken });
  await client.batch(SCHEMA_STMTS, "write");
  return client;
}

module.exports = { openDb };
```

---

### Step 4 — Async startup (`server/index.js`)

`openDb` is now async, so startup must await it.  
Wrap the top-level code in an async IIFE.

```js
// Before:
const db = openDb(cfg.dbPath);
const app = createApp({ db, ... });
const server = app.listen(...);

// After:
(async () => {
  const client = await openDb(cfg.tursoUrl, cfg.tursoAuthToken);
  const app = createApp({ db: client, ... });
  const server = app.listen(...);
  attachShutdownHandlers(server, client);
})();
```

The `attachShutdownHandlers` function: `db.close()` → `client.close()` (libsql has the same method).

---

### Step 5 — Remove prepared statement from app factory (`server/app.js`)

`db.prepare()` does not exist on the libsql client.  
The shared `userByIdStmt` at line 55 is removed.

```diff
- const userByIdStmt = db.prepare("SELECT id, username FROM users WHERE id = ?");
- const requireAuth = createRequireAuth(userByIdStmt, sessionSecret);
+ const requireAuth = createRequireAuth(db, sessionSecret);
```

Pass `db` (the client) directly to `createRequireAuth` and `createAuthRouter` instead of `userByIdStmt`.  
Update the `AppOptions` typedef: replace `db: import('better-sqlite3').Database` with
`db: import('@libsql/client').Client`.

---

### Step 6 — Async auth service (`server/auth/service.js`)

`getCurrentUser` calls `userByIdStmt.get()` synchronously.  
This becomes an async DB call.

**Changes:**
- Signature: `getCurrentUser(req, userByIdStmt, secret)` → `getCurrentUser(req, client, secret)`
- Make `getCurrentUser` async; replace `.get()` with `await client.execute(...)`.
- `createRequireAuth` receives `client`; its inner `requireAuth` middleware becomes async.

```js
// Before:
function getCurrentUser(req, userByIdStmt, secret) {
  ...
  return userByIdStmt.get(Number(payload.sub)) || null;
}

function createRequireAuth(userByIdStmt, secret) {
  return function requireAuth(req, res, next) {
    const user = getCurrentUser(req, userByIdStmt, secret);
    if (!user) return res.status(401).json({ error: "Not authenticated" });
    req.user = user;
    next();
  };
}

// After:
async function getCurrentUser(req, client, secret) {
  ...
  const result = await client.execute({
    sql: "SELECT id, username FROM users WHERE id = ?",
    args: [Number(payload.sub)],
  });
  return result.rows[0] || null;
}

function createRequireAuth(client, secret) {
  return async function requireAuth(req, res, next) {
    const user = await getCurrentUser(req, client, secret);
    if (!user) return res.status(401).json({ error: "Not authenticated" });
    req.user = user;
    next();
  };
}
```

Update JSDoc typedefs in this file: `Statement` → `Client`.

---

### Step 7 — Async auth routes (`server/routes/auth.js`)

Remove `db.prepare()` calls at lines 53–55. Run queries inline.

**Two queries to migrate:**

```js
// userByName — was: q.userByName.get(username)
const result = await client.execute({
  sql: "SELECT id, username, password_hash FROM users WHERE username = ?",
  args: [username],
});
const row = result.rows[0];

// insertUser — was: q.insertUser.run(username, hash).lastInsertRowid
const ins = await client.execute({
  sql: "INSERT INTO users (username, password_hash) VALUES (?, ?)",
  args: [username, hash],
});
const id = Number(ins.lastInsertRowid);
```

**Error code change** — libsql surfaces the SQLite error message differently:

```diff
- if (e?.code === "SQLITE_CONSTRAINT_UNIQUE")
+ if (e?.message?.includes("UNIQUE constraint failed"))
```

Update the `AuthRouterOptions` typedef: replace `userByIdStmt` and `db` with `client`.

---

### Step 8 — Async data routes with transaction rewrite (`server/routes/data.js`)

This is the most significant change. The synchronous `db.transaction()` CAS block must be
rewritten using libsql's interactive async transaction API.

**Before (better-sqlite3):**
```js
const saveData = db.transaction((userId, dataText, clientVersion) => {
  const row = q.getData.get(userId);
  ...
  return { conflict, version, updatedAt };
});
// called as:
saveData.immediate(req.user.id, ...)
```

**After (libsql):**
```js
async function saveData(client, userId, dataText, clientVersion) {
  const tx = await client.transaction("write");
  try {
    const res = await tx.execute({
      sql: "SELECT data, version, updated_at FROM user_data WHERE user_id = ?",
      args: [userId],
    });
    const row = res.rows[0];
    const serverVersion = row ? Number(row.version) : 0;
    if (serverVersion !== clientVersion) {
      await tx.rollback();
      return { conflict: true, row };
    }
    const now = new Date().toISOString();
    if (row) {
      await tx.execute({
        sql: "UPDATE user_data SET data = ?, version = version + 1, updated_at = ? WHERE user_id = ?",
        args: [dataText, now, userId],
      });
    } else {
      await tx.execute({
        sql: "INSERT INTO user_data (user_id, data, version, updated_at) VALUES (?, ?, 1, ?)",
        args: [userId, dataText, now],
      });
    }
    await tx.commit();
    return { conflict: false, version: serverVersion + 1, updatedAt: now };
  } catch (e) {
    await tx.rollback();
    throw e;
  }
}
```

Route handlers: both `GET /` and `PUT /` become `async`.  
`saveData.immediate(...)` → `await saveData(client, ...)`.

Remove all `db.prepare()` calls and the `q` object at lines 26–34.

---

### Step 9 — Update config files

**`.env.example`:**
```diff
- DB_PATH=./data/app.db
+ TURSO_DATABASE_URL=   # libsql://<db-name>.turso.io — from: turso db show <name>
+ TURSO_AUTH_TOKEN=     # from: turso db tokens create <name>
```

**`render.yaml`:**
```diff
     envVars:
-      - key: DB_PATH
-        value: /data/app.db
+      - key: TURSO_DATABASE_URL
+        sync: false
+      - key: TURSO_AUTH_TOKEN
+        sync: false
-    disk:
-      name: sqlite-data
-      mountPath: /data
-      sizeGB: 1
```

---

## Local Testing

### Run unit tests
```bash
npm test
```
Tests use `:memory:` SQLite. After migration they will run against libsql's in-memory mode
(same engine, same SQL). All 38 tests should continue to pass.

> If `TURSO_DATABASE_URL` is absent and `NODE_ENV` is not `production`,
> `config.js` falls back to `":memory:"` — tests work without Turso credentials.

### Run the dev server against real Turso
```bash
# Make sure .env has TURSO_DATABASE_URL and TURSO_AUTH_TOKEN set
npm run dev
```
Manual smoke test checklist:
- [ ] App loads at `http://localhost:3000`
- [ ] Register a new user
- [ ] Log in with that user
- [ ] Save progress (tick a checkbox or update any field)
- [ ] Stop the server (`Ctrl+C`)
- [ ] Restart the server (`npm run dev`)
- [ ] Log in again — data should still be there (persistent in Turso)
- [ ] Open Turso dashboard → Tables → confirm rows in `users` and `user_data`

### Verify the version conflict path
- Open the app in two browser tabs, logged in as the same user
- Make a change in tab 1 and save
- Make a different change in tab 2 and save — should get a 409 conflict response

---

## Deployment to Render

1. Push code to GitHub (triggers auto-deploy on Render)
2. In Render dashboard → your service → **Environment**:
   - Add `TURSO_DATABASE_URL` = your `libsql://...` URL
   - Add `TURSO_AUTH_TOKEN` = your auth token
3. Remove the `DB_PATH` env var if it still exists
4. In **Disks** tab: the disk is no longer needed (leave it if it exists — it just won't be used)
5. Trigger a manual deploy if Render didn't auto-deploy

After deploy: smoke test with the same checklist above against the live URL.

---

## Rollback Plan

If anything goes wrong after deployment:

1. Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` back to empty in Render env vars
2. Add `DB_PATH=/data/app.db` back
3. Re-attach the persistent disk (if you removed it)
4. Revert the git commits
5. Push → Render redeploys the old version

Since you're migrating from a wiped-on-every-deploy state anyway, there is no user data to
lose during the migration window.

---

## File Change Summary

| File | Type of change |
|---|---|
| `package.json` | Swap `better-sqlite3` → `@libsql/client` |
| `server/db.js` | Full rewrite — async `createClient` + `batch` schema |
| `server/config.js` | Replace `dbPath` with `tursoUrl` + `tursoAuthToken` |
| `server/index.js` | Async IIFE startup; `db.close()` → `client.close()` |
| `server/app.js` | Remove `db.prepare()`; pass `client` to routers |
| `server/auth/service.js` | `getCurrentUser` + `createRequireAuth` → async |
| `server/routes/auth.js` | Inline async queries; fix unique-constraint error check |
| `server/routes/data.js` | Remove `db.transaction()`; async interactive transaction |
| `.env.example` | Replace `DB_PATH` with `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` |
| `render.yaml` | Remove disk block; add Turso env vars |

**Files with zero changes:** `server/auth/validators.js`, `js/`, `css/`, `index.html`, `data/`.
(`test/` did change; see the status note at the top.)
