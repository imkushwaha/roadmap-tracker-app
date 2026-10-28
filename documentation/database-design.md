# Database Design — Roadmap Dashboard

## 1. Overview

The application uses **[Turso](https://turso.tech)** (hosted libSQL, a SQLite-compatible database) via the `@libsql/client` library. The client API is **async**: every query is `await db.execute({ sql, args })` with parameterised `args` (there are no prepared statements). Because the data lives in Turso rather than on the web server's disk, it survives redeploys on hosts with an ephemeral filesystem such as Render.

**Connection targets** (selected by `TURSO_DATABASE_URL`):
- `libsql://<db>.turso.io` — Turso, used in production (requires `TURSO_AUTH_TOKEN`)
- `file:<path>` — local SQLite file; the development default is `./data/app.db` when no URL is set
- `:memory:` — in-process database used by the test suite

**Startup:** `openDb(url, authToken)` (async) creates the client and applies the schema in one call, `client.batch(SCHEMA_STATEMENTS, "write")`. No `PRAGMA journal_mode` is set by the application (journaling is managed by libSQL/Turso). Foreign-key constraints are enforced by libSQL by default; the test suite verifies this through the `ON DELETE CASCADE` test.

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
│ created_at                    │
└──────────────┬────────────────┘
               │ 1
               │ ON DELETE CASCADE
               │ N (max 1 in practice)
┌──────────────▼────────────────┐
│           user_data           │
├───────────────────────────────┤
│ user_id (PK, FK → users.id)  │
│ data  (JSON text)             │
│ version (integer)             │
│ updated_at                    │
└───────────────────────────────┘
```

The relationship is effectively **1 : 0..1**: each user has at most one `user_data` row, created on first save. Deleting a user cascades to delete their data row.

---

## 3. Table Definitions

### 3.1 `users`

```sql
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT    NOT NULL,
  created_at    TEXT    NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
```

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | PK, AUTOINCREMENT | Surrogate key; embedded in JWT `sub` claim |
| `username` | TEXT | UNIQUE NOCASE, NOT NULL | Case-insensitive uniqueness — `Alice` and `alice` collide |
| `password_hash` | TEXT | NOT NULL | bcrypt `$2b$12$...` hash; never returned in API responses |
| `created_at` | TEXT | NOT NULL, DEFAULT | ISO-8601 UTC timestamp; set once at row creation |

---

### 3.2 `user_data`

```sql
CREATE TABLE IF NOT EXISTS user_data (
  user_id    INTEGER PRIMARY KEY
             REFERENCES users(id) ON DELETE CASCADE,
  data       TEXT    NOT NULL,
  version    INTEGER NOT NULL,
  updated_at TEXT    NOT NULL
);
```

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `user_id` | INTEGER | PK, FK → `users.id`, CASCADE | One row per user; PK doubles as FK |
| `data` | TEXT | NOT NULL | Serialised `ProgressStore` JSON; validated before write |
| `version` | INTEGER | NOT NULL | Monotonically incremented; starts at 1 on first save |
| `updated_at` | TEXT | NOT NULL | ISO-8601 UTC timestamp; set on every write |

---

## 4. Data Model — ProgressStore (stored in `user_data.data`)

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
| (implicit) | `user_data` | `user_id` | PK |

No additional indexes are needed at current scale (single-user app; all queries are PK/UNIQUE lookups).

---

## 6. Key Query Patterns

### User lookup on login
```sql
SELECT * FROM users WHERE username = ? COLLATE NOCASE;
```
The `COLLATE NOCASE` on the column definition makes this implicitly case-insensitive.

### Save user data (first save vs. update)
The `PUT /api/data` route performs an atomic compare-and-swap using a **single statement** (no explicit transaction), so it costs one network round trip to Turso. The statement depends on the client's version:

```sql
-- clientVersion = 0: first save (no row yet)
INSERT INTO user_data (user_id, data, version, updated_at)
VALUES (?, ?, 1, ?)
ON CONFLICT(user_id) DO NOTHING;

-- clientVersion > 0: update only if the stored version still matches
UPDATE user_data
   SET data = ?, version = version + 1, updated_at = ?
 WHERE user_id = ? AND version = ?;      -- the CAS guard
```

If `rowsAffected === 1` the save succeeded and the new version is `clientVersion + 1`. Otherwise the version didn't match (or a row already exists for a version-0 insert), so the route re-reads the row and returns **409 Conflict** with the server's current copy.

### Fetch user progress
```sql
SELECT data, version, updated_at FROM user_data WHERE user_id = ?;
```
Returns `null` data for a new user (no row yet) — represented as `{ data: null, version: 0 }` in the API response.

---

## 7. Security Notes

- `password_hash` is stored as a bcrypt `$2b$12$...` string (cost factor 12 default). The plain-text password never touches the database.
- The `data` column is validated by `validateProgress()` before every write. Malformed JSON or invalid schema causes a **400** and is never written.
- `ON DELETE CASCADE` ensures no orphaned `user_data` rows if a user is ever removed.
- The local development file (`data/app.db`) is **not served** by the static file allowlist and returns 404 if requested directly.
- `TURSO_AUTH_TOKEN` grants full access to the database. Keep it in `.env` (git-ignored) or the host's secret store; never commit it.
- All queries use parameterised `args`, never string concatenation. Duplicate usernames are detected via `isUniqueViolation` (error code `SQLITE_CONSTRAINT_UNIQUE` or a message containing `UNIQUE constraint failed`) and mapped to 409.

---

## 8. Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `TURSO_DATABASE_URL` | dev: local file `./data/app.db`; **required in production** | `libsql://…` Turso URL (or `file:` / `:memory:`); tests use `:memory:` |
| `TURSO_AUTH_TOKEN` | empty | Turso auth token; required when the URL is remote (`libsql://`) in production |
