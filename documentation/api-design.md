# API Design — Roadmap Dashboard

## 1. Overview

The backend exposes a JSON REST API under the `/api` prefix. All responses use `Content-Type: application/json`. The server listens on **port 3000** (configurable via `PORT` env var).

### Base URL
```
http://localhost:3000/api
```

### Authentication Transport
Session token is a **JWT stored in an httpOnly cookie** (`rd_session`). Browsers send it automatically on every same-origin `fetch()` call with `credentials: "same-origin"`. The cookie is never readable by JavaScript, protecting against XSS theft.

### Global Rate Limiting
All `/api` routes share a rate limit: **10 requests per 15-minute window per IP** (configurable). Failed login attempts have an additional sub-limit to slow brute-force attacks.

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
  "username": "alice",
  "password": "mypassword"
}
```

**Validation rules**

| Field | Rule |
|-------|------|
| `username` | 3–32 characters, pattern `/^[A-Za-z0-9_-]+$/` |
| `password` | 8–72 bytes |

**Success — 201 Created**
```json
{
  "user": { "username": "alice" }
}
```
Sets `rd_session` cookie (httpOnly, SameSite=Lax, 7-day TTL).

**Failure — 400 Bad Request** (validation failure)
```json
{ "error": "Username must be 3–32 characters and contain only letters, numbers, _ or -" }
```

**Failure — 409 Conflict** (username taken)
```json
{ "error": "Username already taken" }
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
  "user": { "username": "alice" }
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
  "user": { "username": "alice" }
}
```
Sets refreshed `rd_session` cookie.

**Failure — 401 Unauthorized**
```json
{ "error": "Not authenticated" }
```

---

## 3. Data Endpoints — `/api/data`

All data endpoints require a valid `rd_session` cookie. Each user's data is isolated — a user can only read and write their own `ProgressStore`.

---

### GET `/api/data`

Returns the authenticated user's stored progress data.

**Requires:** valid `rd_session` cookie.

**Success — 200 OK** (user has saved data)
```json
{
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

**Success — 200 OK** (new user, no data saved yet)
```json
{
  "data": null,
  "version": 0
}
```

**Failure — 401 Unauthorized**
```json
{ "error": "Not authenticated" }
```

---

### PUT `/api/data`

Saves (creates or replaces) the authenticated user's progress data. Uses **optimistic concurrency control**: the client must pass the `version` it last read. If the server's version has changed (another tab or device saved in the meantime), the server returns 409 with its current copy so the client can resolve the conflict.

**Requires:** valid `rd_session` cookie.

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
| `version` | integer | Yes | Must match current server `version`; use `0` for first-ever save |

**Body size limit:** 5 MB.

**Success — 200 OK**
```json
{
  "version": 7,
  "updatedAt": "2024-03-10T14:31:00.000Z"
}
```
The client should update its local `session.version` to the returned `version`.

**Failure — 400 Bad Request** (invalid body or schema violation)
```json
{
  "error": "Invalid progress data",
  "details": ["items.subtask-xyz.status must be one of: not_started, in_progress, completed, blocked"]
}
```

**Failure — 401 Unauthorized**
```json
{ "error": "Not authenticated" }
```

**Failure — 409 Conflict** (version mismatch)
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
The client receives the server's current copy and presents the user with a conflict resolution dialog (keep server version or overwrite with local).

**Failure — 413 Payload Too Large**
```json
{ "error": "Request body too large" }
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
| Everything else | `404` | `data/app.db`, `.env`, `server/`, `node_modules/` are never served |

---

## 5. HTTP Status Code Reference

| Code | Meaning | Used When |
|------|---------|-----------|
| 200 | OK | Successful GET or PUT |
| 201 | Created | Successful register |
| 204 | No Content | Successful logout |
| 400 | Bad Request | Missing fields, validation failure |
| 401 | Unauthorized | Missing or invalid session cookie |
| 409 | Conflict | Username taken (register) or version mismatch (PUT /data) |
| 413 | Payload Too Large | Request body > 5 MB |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server fault |

---

## 6. Conflict Resolution Protocol

The PUT `/api/data` endpoint implements a **compare-and-swap** pattern:

```
Client                          Server
  │                               │
  │ PUT { data, version: N }      │
  ├──────────────────────────────►│
  │                               │ BEGIN IMMEDIATE transaction
  │                               │ SELECT version WHERE user_id = ?
  │                               │ if server.version != N:
  │◄──────────────────────────────┤   409 { error, server: { data, version } }
  │                               │ else:
  │                               │   UPSERT version = N+1
  │◄──────────────────────────────┤   200 { version: N+1, updatedAt }
  │                               │ COMMIT
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
- **5 MB body limit** on PUT `/api/data` prevents DoS via large payload.
- **Schema validation** on every write prevents malformed data from reaching the database.
