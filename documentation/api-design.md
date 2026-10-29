# API Design — Roadmap Dashboard

## 1. Overview

The backend exposes a JSON REST API under the `/api` prefix. All responses use `Content-Type: application/json`. The server listens on **port 3000** (configurable via `PORT` env var).

### Base URL
```
http://localhost:3000/api
```

### Authentication Transport
Session token is a **JWT stored in an httpOnly cookie** (`rd_session`). Browsers send it automatically on every same-origin `fetch()` call with `credentials: "same-origin"`. The cookie is never readable by JavaScript, protecting against XSS theft.

### Rate Limiting
The `/api/auth` endpoints `register` and `login` are limited to **10 requests per 15-minute window per IP** (configurable); only **failed** logins count toward the login limit. `GET /api/auth/check-username` has its own, looser limit of 30 per window. Roadmap routes (`/api/roadmaps`) are not rate-limited; they require a valid session.

### Common Error Shape
```json
{
  "error": "Human-readable message"
}
```

---

## 2. Auth Endpoints — `/api/auth`

Auth routes do **not** require a prior session. They set or clear the `rd_session` cookie.

---

### POST `/api/auth/register`

Creates a new user account and starts a session.

**Request body**
```json
{
  "firstName": "Alice",
  "lastName": "Smith",
  "username": "alice",
  "password": "mypassword"
}
```

**Validation rules**

| Field | Rule |
|-------|------|
| `firstName`, `lastName` | 1–64 characters, letters (including accented), space, `'` or `-` |
| `username` | 3–32 characters, pattern `/^[A-Za-z0-9_-]+$/` |
| `password` | 8–72 bytes |

**Success — 201 Created**
```json
{
  "user": { "username": "alice", "firstName": "Alice", "lastName": "Smith" }
}
```
Sets `rd_session` cookie (httpOnly, SameSite=Lax, 7-day TTL).

The user row and the starter **AI Engineer Roadmap** row are inserted in a single transaction (`db.batch`), so an account never exists without its starter roadmap. A rejected duplicate username leaves nothing behind.

**Failure — 400 Bad Request** (validation failure)
```json
{ "error": "Username must be 3-32 characters: letters, numbers, _ or -." }
```

**Failure — 409 Conflict** (username taken)
```json
{ "error": "That username is already taken." }
```

---

### POST `/api/auth/login`

Authenticates an existing user and starts a session.

**Request body**
```json
{
  "username": "alice",
  "password": "mypassword"
}
```

**Success — 200 OK**
```json
{
  "user": { "username": "alice", "firstName": "Alice", "lastName": "Smith" }
}
```
Sets `rd_session` cookie.

**Failure — 401 Unauthorized**
```json
{ "error": "Invalid credentials" }
```

> **Anti-enumeration:** The response time and message are identical whether the username does not exist or the password is wrong. The server runs `verifyPassword(password, dummyHash)` for unknown usernames to neutralise timing attacks.

---

### POST `/api/auth/logout`

Clears the session cookie. No authentication required — clears the cookie regardless.

**Success — 204 No Content** *(empty body)*

Sets `rd_session` cookie to expired (`Max-Age=0`).

---

### GET `/api/auth/me`

Returns the currently authenticated user and issues a **rolling session** (refreshes cookie TTL).

**Requires:** valid `rd_session` cookie.

**Success — 200 OK**
```json
{
  "user": { "username": "alice", "firstName": "Alice", "lastName": "Smith" }
}
```
Sets refreshed `rd_session` cookie.

**Failure — 401 Unauthorized**
```json
{ "error": "Not authenticated" }
```

---

### GET `/api/auth/check-username?username=<value>`

Reports whether a username is free, for live feedback on the registration form. No session required. Rate limit: 30 requests per window per IP.

**Success — 200 OK**
```json
{ "available": true }
```

**Failure — 400 Bad Request** (value fails the username rules)
```json
{ "error": "Username must be 3-32 characters: letters, numbers, _ or -." }
```

---

## 3. Roadmap Endpoints — `/api/roadmaps`

Every account owns zero or more roadmaps. A new account starts with one: the built-in **AI Engineer Roadmap** (`source: "builtin_ai_engineer"`), whose content is the static `data/roadmap.js` bundle; only its metadata and the user's progress are stored per account. Progress data is stored **per roadmap**.

All routes require a valid `rd_session` cookie (`401 {"error":"Not authenticated"}` otherwise) and every query is scoped to the authenticated user. A roadmap that doesn't exist, belongs to someone else, or has a malformed `:id` (`abc`, `0`, `1.5`, `-1`) yields `404 {"error":"Roadmap not found"}` — the API never reveals whether another user's roadmap exists.

The old `/api/data` endpoints no longer exist; their behaviour moved to `/api/roadmaps/:id/progress`.

**Roadmap summary shape**

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | |
| `name` | string | |
| `description` | string | May be empty |
| `source` | string | `"builtin_ai_engineer"` (static AI Engineer curriculum) or `"custom"` (user-built, starts empty) |
| `createdAt` | string | ISO-8601 UTC |
| `lastActivityAt` | string \| null | Only in the list response: when progress was last saved; `null` if never |

---

### GET `/api/roadmaps`

Lists the user's roadmaps, oldest first. Returns metadata only (no progress data).

**Success — 200 OK**
```json
{
  "roadmaps": [
    {
      "id": 2,
      "name": "AI Engineer Roadmap",
      "description": "Tier-1 Production AI Engineer — 10-Month Execution Tracker",
      "source": "builtin_ai_engineer",
      "createdAt": "2026-10-29T10:33:41.960Z",
      "lastActivityAt": null
    }
  ]
}
```
A user who deleted every roadmap gets `{ "roadmaps": [] }`.

---

### POST `/api/roadmaps`

Two modes, chosen by the `source` field.

#### Mode 1 — create a custom roadmap (`source` omitted or `"custom"`)

Creates an **empty** roadmap. It has no curriculum of its own: months, sections, topics and tasks are added afterwards inside the roadmap (stored in its progress data under `custom`), using the same editors as the AI Engineer roadmap.

**Request body**
```json
{
  "name": "Learn Rust",
  "description": "Twelve weeks of systems programming",
  "startMonth": "2026-12"
}
```

| Field | Required | Rule |
|-------|----------|------|
| `name` | Yes | String, trimmed, 1–80 characters, single line (no control characters) |
| `description` | No | String, trimmed, at most 300 characters |
| `startMonth` | No | `"YYYY-MM"`, or `null`/omitted |

With a `startMonth`, the server also writes the roadmap's first progress row at **version 1** (empty progress with `settings.startMonth` set), in the same transaction as the roadmap. Without one there is no progress row (`version: 0`) and the app defaults Month 1 to the current month.

**Success — 201 Created**
```json
{
  "roadmap": {
    "id": 4,
    "name": "Learn Rust",
    "description": "Twelve weeks of systems programming",
    "source": "custom",
    "createdAt": "2026-10-29T11:02:10.512Z"
  }
}
```

**Failure — 400 Bad Request** (validation) — `{ "error": "<message>" }`, for example `"Roadmap name is required."`, `"Roadmap name must be 1–80 characters on a single line."`, `"Description must be at most 300 characters."`, `"Start month must look like \"YYYY-MM\"."`

**Failure — 409 Conflict** (an account may own at most **20** roadmaps)
```json
{ "error": "You can have at most 20 roadmaps." }
```

#### Mode 2 — restore the built-in roadmap (`source: "builtin_ai_engineer"`)

Re-creates the AI Engineer roadmap after it was deleted.

**Request body**
```json
{ "source": "builtin_ai_engineer" }
```

**Success — 201 Created** — a fresh roadmap with no saved progress (`version: 0`)
```json
{
  "roadmap": {
    "id": 3,
    "name": "AI Engineer Roadmap",
    "description": "Tier-1 Production AI Engineer — 10-Month Execution Tracker",
    "source": "builtin_ai_engineer",
    "createdAt": "2026-10-29T10:33:42.947Z"
  }
}
```

**Failure — 409 Conflict** (the user already has one)
```json
{ "error": "You already have this roadmap." }
```

#### Unknown source

Any other `source` value returns **400** `{ "error": "Unknown roadmap source." }`.

---

### DELETE `/api/roadmaps/:id`

Permanently deletes the roadmap. Its `roadmap_progress` row is removed by `ON DELETE CASCADE`. The UI asks for confirmation before calling this; the API itself does not.

**Success — 204 No Content** *(empty body)*

**Failure — 404 Not Found** — unknown id, not the caller's, or already deleted.

---

### GET `/api/roadmaps/:id/progress`

Returns the roadmap's metadata together with the progress saved against it.

**Success — 200 OK** (progress has been saved)
```json
{
  "roadmap": {
    "id": 2,
    "name": "AI Engineer Roadmap",
    "description": "Tier-1 Production AI Engineer — 10-Month Execution Tracker",
    "source": "builtin_ai_engineer",
    "createdAt": "2026-10-29T10:33:41.960Z"
  },
  "data": {
    "items": {
      "subtask-abc": {
        "status": "completed",
        "notes": "Reviewed chapter 3",
        "link": "https://example.com",
        "dueDate": "2024-03-15",
        "completedAt": "2024-03-10T14:30:00.000Z"
      }
    },
    "counters": { "papers-read": 12 },
    "celebratedPhases": ["month-1"],
    "settings": { "startMonth": "2024-01" },
    "custom": { "phases": [], "topics": [] }
  },
  "version": 7,
  "updatedAt": "2024-03-10T14:30:00.000Z"
}
```

**Success — 200 OK** (nothing saved yet) — `data` is `null` and `version` is `0`; `updatedAt` is absent.
```json
{ "roadmap": { ... }, "data": null, "version": 0 }
```

**Failure — 401 / 404** as described above.

---

### PUT `/api/roadmaps/:id/progress`

Saves (creates or replaces) the progress for one roadmap. Uses **optimistic concurrency control**: the client passes the `version` it last read. If the stored version has changed (another tab or device saved in the meantime), the server returns 409 with its current copy so the client can resolve the conflict.

**Request body**
```json
{
  "data": { ...ProgressStore... },
  "version": 6
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `data` | object | Yes | Must pass `validateProgress()` schema check |
| `version` | integer | Yes | Non-negative; must match the stored `version`; use `0` for the first-ever save |

**Body size limit:** 5 MB.

**Success — 200 OK**
```json
{
  "version": 7,
  "updatedAt": "2024-03-10T14:31:00.000Z"
}
```
The client should update its local `session.version` to the returned `version`.

**Failure — 400 Bad Request** (`version` not a non-negative integer, or schema violation)
```json
{ "error": "\"version\" must be a non-negative integer." }
```
```json
{
  "error": "Data doesn't match the progress schema.",
  "details": ["items.subtask-xyz.status must be one of not_started, in_progress, completed, blocked."]
}
```

**Failure — 401 Unauthorized / 404 Not Found** as described above. Ownership is checked first, so a foreign or unknown roadmap is a 404 even when the body is also invalid.

**Failure — 409 Conflict** (version mismatch, including a non-zero `version` for a roadmap with no saved progress)
```json
{
  "error": "Version conflict",
  "server": {
    "data": { ...ProgressStore... },
    "version": 7,
    "updatedAt": "2024-03-10T14:30:45.000Z"
  }
}
```
For a roadmap with no saved progress the `server` object is `{ "data": null, "version": 0 }`. The client presents a conflict dialog (keep server version or overwrite with local).

**Failure — 413 Payload Too Large**
```json
{ "error": "Request body too large (limit 5 MB)." }
```

---

## 4. Static File Routes

These paths serve the application assets. They are an explicit allowlist — all other paths return 404.

| Path | Response | Notes |
|------|----------|-------|
| `GET /` | `index.html` | SPA shell |
| `GET /index.html` | `index.html` | Same file |
| `GET /css/*` | CSS files | All files under `css/` |
| `GET /js/*` | JS files | All files under `js/` |
| `GET /data/roadmap.js` | Static roadmap data | `window.ROADMAP_DATA = {...}` |
| Any other `/api/*` | `404 { "error": "Not found" }` | |
| Everything else | `404` | `data/app.db` (local dev file), `.env`, `server/`, `node_modules/` are never served |

---

## 5. HTTP Status Code Reference

| Code | Meaning | Used When |
|------|---------|-----------|
| 200 | OK | Successful GET or PUT |
| 201 | Created | Successful register; creating a custom roadmap; restoring the AI Engineer roadmap |
| 204 | No Content | Successful logout; successful roadmap delete |
| 400 | Bad Request | Missing fields, validation failure |
| 401 | Unauthorized | Missing or invalid session cookie |
| 404 | Not Found | Roadmap id unknown, malformed, or owned by another user |
| 409 | Conflict | Username taken (register), version mismatch (PUT progress), built-in roadmap already exists (restore), or the 20-roadmap limit reached (create) |
| 413 | Payload Too Large | Request body > 5 MB |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server fault |

---

## 6. Conflict Resolution Protocol

The PUT `/api/roadmaps/:id/progress` endpoint implements a **compare-and-swap** pattern, independently for each roadmap:

```
Client                          Server
  │                               │
  │ PUT { data, version: N }      │
  ├──────────────────────────────►│
  │                               │ single atomic statement:
  │                               │   N = 0: INSERT ... ON CONFLICT DO NOTHING
  │                               │   N > 0: UPDATE ... WHERE version = N
  │                               │ if rowsAffected == 1:
  │◄──────────────────────────────┤   200 { version: N+1, updatedAt }
  │                               │ else (version mismatch):
  │                               │   re-read current row
  │◄──────────────────────────────┤   409 { error, server: { data, version } }
```

On 409, `app.js` opens a modal presenting the user with two options:
- **Keep server version** — discard local changes, adopt server state
- **Overwrite** — re-submit with the server's current version number (forcing the write)

---

## 7. Security Notes

- **Passwords are never returned** in any API response.
- **httpOnly cookie** prevents JavaScript from reading the session token.
- **SameSite=Lax** prevents CSRF on cross-site navigations.
- **Anti-enumeration** on login: identical response for wrong-password and unknown-user.
- **Rate limiting** limits brute-force login attempts.
- **5 MB body limit** on PUT `/api/roadmaps/:id/progress` prevents DoS via large payload.
- **Per-user scoping:** every roadmap query filters on the session user's id, never on request input; another user's roadmap is indistinguishable from a missing one (404).
- **Schema validation** on every write prevents malformed data from reaching the database.
