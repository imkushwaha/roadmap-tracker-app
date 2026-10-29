# Database Design — Roadmap Dashboard

## 1. Overview

The application uses **[Turso](https://turso.tech)** (hosted libSQL, a SQLite-compatible database) via the `@libsql/client` library. The client API is **async**: every query is `await db.execute({ sql, args })` with parameterised `args` (there are no prepared statements). Because the data lives in Turso rather than on the web server's disk, it survives redeploys on hosts with an ephemeral filesystem such as Render.

**Connection targets** (selected by `TURSO_DATABASE_URL`):
- `libsql://<db>.turso.io` — Turso, used in production (requires `TURSO_AUTH_TOKEN`)
- `file:<path>` — local SQLite file; the development default is `./data/app.db` when no URL is set
- `:memory:` — in-process database used by the test suite

**Startup:** `openDb(url, authToken)` (async) creates the client, applies the schema with `client.batch(SCHEMA_STATEMENTS, "write")`, runs the idempotent column additions (`first_name`/`last_name`), then runs the one-time legacy migration (see [section 9](#9-migration-from-the-single-roadmap-schema)). No `PRAGMA journal_mode` is set by the application (journaling is managed by libSQL/Turso). Foreign-key constraints are enforced by libSQL by default; the test suite verifies this through the `ON DELETE CASCADE` tests.

Schema is created with `CREATE TABLE IF NOT EXISTS` guards, so startup is idempotent. All timestamps are stored as ISO-8601 text (`YYYY-MM-DDTHH:MM:SS.sssZ`).

---

## 2. Entity Relationship Diagram

```
┌───────────────────────────────┐
│             users             │
├───────────────────────────────┤
│ id (PK)                       │
│ username (UNIQUE, NOCASE)     │
│ password_hash                 │
│ first_name, last_name         │
│ created_at                    │
└──────────────┬────────────────┘
               │ 1
               │ ON DELETE CASCADE
               │ N (starts with 1: the AI Engineer roadmap)
┌──────────────▼────────────────┐
│           roadmaps            │
├───────────────────────────────┤
│ id (PK)                       │
│ user_id (FK → users.id)       │
│ name, description             │
│ source                        │
│ created_at                    │
└──────────────┬────────────────┘
               │ 1
               │ ON DELETE CASCADE
               │ 0..1 (created on first save)
┌──────────────▼────────────────┐
│       roadmap_progress        │
├───────────────────────────────┤
│ roadmap_id (PK, FK → id)      │
│ data  (JSON text)             │
│ version (integer)             │
│ updated_at                    │
└───────────────────────────────┘
```

A user owns **N roadmaps** (`users` 1 : N `roadmaps`); a new account is created with exactly one, the built-in AI Engineer roadmap. Each roadmap has **at most one** `roadmap_progress` row, created on its first save (`roadmaps` 1 : 0..1 `roadmap_progress`). Deleting a roadmap cascades to its progress row; deleting a user cascades through both levels.

`roadmaps.source` identifies where a roadmap's *content* comes from. `builtin_ai_engineer` rows are metadata only — the curriculum is the static `data/roadmap.js` bundle, so nothing but name, description and the user's progress is stored per account.

---

## 3. Table Definitions

### 3.1 `users`

```sql
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT    NOT NULL,
  first_name    TEXT    NOT NULL DEFAULT '',
  last_name     TEXT    NOT NULL DEFAULT '',
  created_at    TEXT    NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
```

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | PK, AUTOINCREMENT | Surrogate key; embedded in JWT `sub` claim |
| `username` | TEXT | UNIQUE NOCASE, NOT NULL | Case-insensitive uniqueness — `Alice` and `alice` collide |
| `password_hash` | TEXT | NOT NULL | bcrypt `$2b$12$...` hash; never returned in API responses |
| `first_name`, `last_name` | TEXT | NOT NULL, DEFAULT `''` | Collected at registration; added to older databases by `ALTER TABLE` at startup (duplicate-column errors ignored) |
| `created_at` | TEXT | NOT NULL, DEFAULT | ISO-8601 UTC timestamp; set once at row creation |

---

### 3.2 `roadmaps`

```sql
CREATE TABLE IF NOT EXISTS roadmaps (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT    NOT NULL,
  description TEXT    NOT NULL DEFAULT '',
  source      TEXT    NOT NULL,
  created_at  TEXT    NOT NULL
              DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_roadmaps_user ON roadmaps(user_id);
```

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | PK, AUTOINCREMENT | Used in `/api/roadmaps/:id` URLs; every lookup also filters on `user_id` |
| `user_id` | INTEGER | NOT NULL, FK → `users.id`, CASCADE | Owner |
| `name` | TEXT | NOT NULL | Display name, e.g. `AI Engineer Roadmap` |
| `description` | TEXT | NOT NULL, DEFAULT `''` | Shown as the subtitle inside the roadmap |
| `source` | TEXT | NOT NULL | `builtin_ai_engineer` (static AI Engineer curriculum, metadata-only row) or `custom` (user-built roadmap that starts empty); no CHECK constraint, so future sources need no migration |
| `created_at` | TEXT | NOT NULL, DEFAULT | ISO-8601 UTC timestamp |

The built-in name, description and source live in `server/roadmaps/builtin.js` (`BUILTIN_AI_ENGINEER`) and are shared by registration, the legacy migration and the restore endpoint. The `custom` source constant and the creation limits (name ≤ 80, description ≤ 300, at most 20 roadmaps per user) live in `server/roadmaps/validators.js`.

**There is no definition column.** A `custom` roadmap stores no curriculum of its own — its months, sections, topics and tasks live in its progress blob (`ProgressStore.custom`, section 4). The application treats the curriculum of a `custom` roadmap as empty (`BLANK_DATA`) and layers `custom` on top, exactly as it already does for user additions to the AI Engineer roadmap. This avoids a second source of truth and the problem of progress keys orphaned by a changed definition.

---

### 3.3 `roadmap_progress`

```sql
CREATE TABLE IF NOT EXISTS roadmap_progress (
  roadmap_id INTEGER PRIMARY KEY
             REFERENCES roadmaps(id) ON DELETE CASCADE,
  data       TEXT    NOT NULL,
  version    INTEGER NOT NULL,
  updated_at TEXT    NOT NULL
);
```

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `roadmap_id` | INTEGER | PK, FK → `roadmaps.id`, CASCADE | One row per roadmap; PK doubles as FK |
| `data` | TEXT | NOT NULL | Serialised `ProgressStore` JSON; validated before write |
| `version` | INTEGER | NOT NULL | Monotonically incremented; starts at 1 on first save |
| `updated_at` | TEXT | NOT NULL | ISO-8601 UTC timestamp; set on every write; surfaced as `lastActivityAt` in the roadmap list |

---

## 4. Data Model — ProgressStore (stored in `roadmap_progress.data`)

The `data` column stores the user's entire progress state as a single JSON text value. Its shape is defined and validated by `js/progress-schema.js` (UMD module shared between browser and server).

```typescript
type ProgressStore = {
  items: {
    [subtaskId: string]: {
      status:      "not_started" | "in_progress" | "completed" | "blocked";
      notes:       string;
      link:        string;
      dueDate:     string | null;    // ISO date "YYYY-MM-DD" or null
      completedAt: string | null;    // ISO datetime when status → "completed"
    };
  };
  counters: {
    [counterId: string]: number;     // non-negative integer
  };
  celebratedPhases: string[];        // phase ids where completion confetti shown
  settings: {
    startMonth?: string;             // "YYYY-MM" — start of the user's roadmap
  };
  custom: {
    phases?: Array<{
      id:        string;             // "custom-month-<uuid>"
      title:     string;
      objective?: string;
      sections:  Array<{
        id:         string;          // "custom-section-<uuid>"
        title:      string;
        weekNumber: number | null;   // 1–4 or null
      }>;
    }>;
    topics?: Array<{
      id:        string;             // "custom-topic-<uuid>"
      sectionId: string;
      title:     string;
      depth:     string | null;      // "D1" | "D2" | "D2/D3" | "D3" | null
      tasks:     Array<{ id: string; title: string }>;
    }>;
  };
};
```

**Custom roadmaps.** For a `source = 'custom'` roadmap this blob is the *whole* plan: `custom.phases` are its months (with their sections) and `custom.topics` its topics and tasks, edited in the app with the Month → Section (week or theme) → Topic → Tasks editors. For the AI Engineer roadmap the same `custom` block holds only the user's additions on top of the static curriculum. An empty starting blob is built by `emptyProgress(startMonth)` in `server/roadmaps/progress.js`:

```json
{ "items": {}, "counters": {}, "celebratedPhases": [],
  "settings": { "startMonth": "2026-12" },
  "custom": { "topics": [], "phases": [] } }
```

The router only writes this blob at creation time when a start month was chosen; see "Create a custom roadmap" below.

**Validation rules:**
- Top-level keys not listed above are **tolerated** (import/export compatibility)
- `items[*].status` must be one of the four enum values
- `counters[*]` must be a non-negative number
- `celebratedPhases` must be an array of strings
- `custom.phases[*].id` must start with `"custom-month-"`
- `custom.topics[*].id` must start with `"custom-topic-"`

---

## 5. Indexes

SQLite automatically indexes `PRIMARY KEY` and `UNIQUE` columns. The schema creates:

| Index | Table | Column | Type |
|-------|-------|--------|------|
| (implicit) | `users` | `id` | PK |
| (implicit) | `users` | `username` | UNIQUE |
| `idx_roadmaps_user` | `roadmaps` | `user_id` | Explicit — serves the roadmap list and every ownership check |
| (implicit) | `roadmaps` | `id` | PK |
| (implicit) | `roadmap_progress` | `roadmap_id` | PK |

No further indexes are needed at current scale; all other queries are PK/UNIQUE lookups.

---

## 6. Key Query Patterns

### User lookup on login
```sql
SELECT * FROM users WHERE username = ? COLLATE NOCASE;
```
The `COLLATE NOCASE` on the column definition makes this implicitly case-insensitive.

### Registration — user and starter roadmap in one transaction
`POST /api/auth/register` sends both statements in one `db.batch([...], "write")`, so an account never exists without its starter roadmap, and a rejected duplicate username rolls back both:

```sql
INSERT INTO users (username, password_hash, first_name, last_name) VALUES (?, ?, ?, ?);
INSERT INTO roadmaps (user_id, name, description, source)
VALUES (last_insert_rowid(), ?, ?, ?);   -- the user id from the statement above
```

### List a user's roadmaps
```sql
SELECT r.id, r.name, r.description, r.source, r.created_at,
       p.updated_at AS last_activity_at
FROM roadmaps r LEFT JOIN roadmap_progress p ON p.roadmap_id = r.id
WHERE r.user_id = ?
ORDER BY r.created_at, r.id;
```
`last_activity_at` is `NULL` for a roadmap that has never been saved.

### Ownership check (every `/:id` route)
```sql
SELECT id, name, description, source, created_at
FROM roadmaps WHERE id = ? AND user_id = ?;
```
No row means 404 — whether the id is unknown or belongs to someone else.

### Create a custom roadmap
`POST /api/roadmaps` first enforces the per-user cap, then inserts. When the request carries a `startMonth`, the roadmap and its first progress row go in **one `db.batch` transaction**, so the progress row can never be missing or orphaned:

```sql
SELECT COUNT(*) AS n FROM roadmaps WHERE user_id = ?;                  -- >= 20 -> 409
INSERT INTO roadmaps (user_id, name, description, source) VALUES (?, ?, ?, 'custom');
INSERT INTO roadmap_progress (roadmap_id, data, version, updated_at)
VALUES (last_insert_rowid(), ?, 1, ?);                                 -- only when startMonth was given
```
Without a `startMonth` only the first statement runs: there is no progress row (`version: 0`) until the first autosave.

### Restore the built-in roadmap / delete a roadmap
```sql
SELECT 1 FROM roadmaps WHERE user_id = ? AND source = ?;               -- already have it? -> 409
INSERT INTO roadmaps (user_id, name, description, source) VALUES (?, ?, ?, ?);
DELETE FROM roadmaps WHERE id = ? AND user_id = ?;                     -- rowsAffected 0 -> 404; progress cascades
```

All of these statements live in `server/roadmaps/repository.js` (`createRoadmapRepository(db)`); the router never builds SQL.

### Save roadmap progress (first save vs. update)
The `PUT /api/roadmaps/:id/progress` route performs an atomic compare-and-swap using a **single statement** (no explicit transaction), after the ownership check above. The statement depends on the client's version:

```sql
-- clientVersion = 0: first save (no row yet)
INSERT INTO roadmap_progress (roadmap_id, data, version, updated_at)
VALUES (?, ?, 1, ?)
ON CONFLICT(roadmap_id) DO NOTHING;

-- clientVersion > 0: update only if the stored version still matches
UPDATE roadmap_progress
   SET data = ?, version = version + 1, updated_at = ?
 WHERE roadmap_id = ? AND version = ?;      -- the CAS guard
```

If `rowsAffected === 1` the save succeeded and the new version is `clientVersion + 1`. Otherwise the version didn't match (or a row already exists for a version-0 insert), so the route re-reads the row and returns **409 Conflict** with the server's current copy.

### Fetch roadmap progress
```sql
SELECT data, version, updated_at FROM roadmap_progress WHERE roadmap_id = ?;
```
Returns `null` data for a roadmap that has never been saved (no row yet) — represented as `{ data: null, version: 0 }` in the API response.

---

## 7. Security Notes

- `password_hash` is stored as a bcrypt `$2b$12$...` string (cost factor 12 default). The plain-text password never touches the database.
- The `data` column is validated by `validateProgress()` before every write. Malformed JSON or invalid schema causes a **400** and is never written.
- `ON DELETE CASCADE` ensures no orphaned `roadmaps` or `roadmap_progress` rows if a user or roadmap is removed.
- Roadmap access is always scoped by the session user (`WHERE id = ? AND user_id = ?`); the user id is never taken from the request.
- The local development file (`data/app.db`) is **not served** by the static file allowlist and returns 404 if requested directly.
- `TURSO_AUTH_TOKEN` grants full access to the database. Keep it in `.env` (git-ignored) or the host's secret store; never commit it.
- All queries use parameterised `args`, never string concatenation. Duplicate usernames are detected via `isUniqueViolation` (error code `SQLITE_CONSTRAINT_UNIQUE` or a message containing `UNIQUE constraint failed`) and mapped to 409.

---

## 8. Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `TURSO_DATABASE_URL` | dev: local file `./data/app.db`; **required in production** | `libsql://…` Turso URL (or `file:` / `:memory:`); tests use `:memory:` |
| `TURSO_AUTH_TOKEN` | empty | Turso auth token; required when the URL is remote (`libsql://`) in production |

---

## 9. Migration from the single-roadmap schema

Before multi-roadmap support, each user had one row in a `user_data` table (`user_id` PK, `data`, `version`, `updated_at`). `migrateLegacyUserData` in `server/db.js` moves that data on the first boot of the new code:

1. **Guard.** It runs only if a table named `user_data` exists in `sqlite_master`. A fresh database never has one, and the step below removes it, so later boots skip the migration entirely.
2. **One transaction** (`client.batch([...], "write")`):
   1. `INSERT INTO roadmaps … SELECT … FROM users u WHERE NOT EXISTS (SELECT 1 FROM roadmaps r WHERE r.user_id = u.id)` — gives **every** account, including ones that never saved, the built-in AI Engineer roadmap.
   2. `INSERT INTO roadmap_progress … SELECT r.id, ud.data, ud.version, ud.updated_at FROM roadmaps r JOIN user_data ud ON ud.user_id = r.user_id WHERE r.source = ?` — copies each user's saved progress and **keeps its `version` and `updated_at`**, so open browser tabs and CAS saves keep working.
   3. `ALTER TABLE user_data RENAME TO user_data_legacy`.
3. **Rename, not drop.** The old data stays in `user_data_legacy` as a safety net. Nothing reads it; drop it manually (`DROP TABLE user_data_legacy`) once the new schema is confirmed healthy.

Because the guard is "`user_data` exists", a user who later deletes their AI Engineer roadmap is **not** re-seeded on the next boot.

**Rollout notes**
- Deploy as a single switch. An older server instance still running against the same database would fail once `user_data` is renamed, so stop old instances before (or as) the new one boots.
- The migration was verified against a copy of a real development database (account and progress version preserved) and by `test/roadmaps.test.js`.
- To roll back, stop the new code, then `ALTER TABLE user_data_legacy RENAME TO user_data` (progress saved after the migration lives only in `roadmap_progress` and would be lost on the old code).
