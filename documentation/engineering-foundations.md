# Engineering Foundations — Roadmap Dashboard

## 1. Tech Stack

| Layer | Technology | Version | Why Chosen |
|-------|-----------|---------|------------|
| **Runtime** | Node.js | ≥ 22 | Built-in `node:test` module; modern ESM; stable LTS |
| **Web framework** | Express | 5.x | Minimal, well-understood; v5 is async-error-friendly |
| **Database** | Turso (hosted libSQL) via `@libsql/client` | — | SQLite-compatible SQL; data persists across redeploys on ephemeral hosts (Render) with no paid disk; async API fits Express 5 |
| **Auth** | `jsonwebtoken` + `bcryptjs` | — | Industry-standard JWT + constant-time password hashing |
| **Security** | `helmet` + `express-rate-limit` | — | CSP headers + brute-force protection out of the box |
| **Frontend** | Vanilla JS (ES2022), HTML5, CSS3 | — | No build step; loads instantly; anyone can contribute |
| **Roadmap parser** | Python 3.10+ | — | Rich text parsing ecosystem; output committed so not a runtime dep |
| **Testing** | `node:test` (built-in) | — | No extra test runner; zero dependency; fast startup |
| **Config** | `dotenv` | — | Standard `.env` file support |

---

## 2. Project Structure Conventions

### Directory Layout

```
roadmap-dashboard/
├── css/            ← All styles in one file (styles.css)
├── data/           ← Static roadmap content (+ local dev SQLite file, git-ignored)
├── js/             ← Frontend scripts loaded by index.html
├── scripts/        ← Developer tooling (Python parser — not a runtime dep)
├── server/         ← All backend code
│   ├── auth/       ← Auth-specific helpers (pure functions, no routes)
│   └── routes/     ← Express routers (auth + data)
└── test/           ← All tests + helpers
```

### File Naming

- `snake_case` for Python scripts
- `camelCase.js` for Node.js modules
- Routers named by resource: `auth.js`, `data.js`
- Helpers named by concern: `service.js`, `validators.js`

### Module Exports

- Server modules use CommonJS (`require`/`module.exports`) — consistent with `@libsql/client` and `jsonwebtoken`
- Frontend JS is plain script files (no `import`/`export`) loaded via `<script>` tags in order
- `js/progress-schema.js` uses a UMD wrapper to work in both environments

---

## 3. Development Environment Setup

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | ≥ 22 | Check with `node --version` |
| npm | ≥ 10 | Bundled with Node 22 |
| Python | ≥ 3.10 | Only needed to regenerate roadmap content |

### First Run

```bash
# 1. Install dependencies
npm install

# 2. Copy environment template
cp .env.example .env
# Edit .env and set SESSION_SECRET (any string for dev; 32+ chars for prod)

# 3. Start server
npm start
# Server starts on http://localhost:3000
# With TURSO_DATABASE_URL unset, a local SQLite DB is created at data/app.db on first start.
# To develop against Turso instead, set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env.

# 4. Run tests
npm test
```

### Environment Variables

| Variable | Dev Default | Prod Required | Description |
|----------|-------------|---------------|-------------|
| `SESSION_SECRET` | random (auto-generated) | Yes (≥ 32 chars) | JWT signing key |
| `TURSO_DATABASE_URL` | local file `./data/app.db` | **Yes** | Turso `libsql://…` URL (`turso db show <name> --url`); tests use `:memory:` |
| `TURSO_AUTH_TOKEN` | empty | Yes, for a remote `libsql://` URL | Turso auth token (`turso db tokens create <name>`); keep secret |
| `PORT` | `3000` | No | HTTP listen port |
| `NODE_ENV` | — | `production` | Enables production safety checks |
| `TRUST_PROXY` | `false` | No | Number of reverse-proxy hops (for rate-limit real-IP) |
| `COOKIE_SECURE` | `true` in prod | No | Set `false` for plain-HTTP production environments |

### Regenerating Roadmap Content

Edit `data/roadmap.md`, then run:

```bash
python scripts/md_to_json.py
```

This overwrites `data/roadmap.json` and `data/roadmap.js`. Commit both generated files — Python is not required at runtime.

---

## 4. Security Model

### Authentication

- Passwords hashed with **bcrypt**, cost factor 12 (≈ 250ms per hash at server startup time).
- Sessions are **JWT tokens** signed with HS256, embedded in `httpOnly; SameSite=Lax` cookies. JavaScript cannot access the token value.
- Tokens expire after **7 days**; `GET /api/auth/me` issues a fresh token to extend active sessions.
- **Anti-enumeration**: the login route calls `verifyPassword(password, DUMMY_HASH)` for unknown usernames so the response time is indistinguishable from a real password check.

### Transport

- `helmet` sets HTTP security headers including a strict **Content Security Policy**.
- `SameSite=Lax` prevents the session cookie from being sent on cross-origin `POST` (CSRF protection).
- `Secure` cookie flag is on by default in production (`COOKIE_SECURE=false` opt-out).

### Rate Limiting

- Global: 10 requests per 15-minute window per IP.
- Login sub-limit: tracks failed attempts specifically to slow brute-force attacks.
- `TRUST_PROXY` config correctly extracts client IP when behind a reverse proxy.

### Input Validation

- `validateUsername` / `validatePassword` validate auth inputs before any DB touch.
- `validateProgress` (shared UMD) validates the full `ProgressStore` shape before every `PUT /api/data` write. Invalid data is rejected with a descriptive 400 before it can reach the database.
- Body size limit of **5 MB** on `PUT /api/data` prevents DoS via large payloads.

### File Serving Allowlist

The server explicitly maps only four path groups:
1. `index.html`
2. `css/`
3. `js/`
4. `data/roadmap.js`

All other paths return 404 — `data/app.db`, `.env`, `server/`, `node_modules/`, and `package.json` are never accidentally served.

---

## 5. Data Integrity & Reliability

### Optimistic Concurrency Control

`PUT /api/data` performs a single-statement compare-and-swap: `UPDATE … WHERE user_id = ? AND version = ?` (or `INSERT … ON CONFLICT DO NOTHING` for a first save). The write only lands if the stored `version` still matches the client's; otherwise zero rows are affected and the route re-reads the server copy and returns 409 (e.g. another browser tab saved first). This prevents silent data loss without pessimistic locking or a multi-statement transaction (one network round trip to Turso).

### Autosave Resilience

- 1500ms debounce prevents write storms during rapid UI interaction.
- Retry backoff: 2s → 5s → 15s for transient network errors.
- `visibilitychange` and `online` events flush pending saves immediately on tab visibility or reconnect.
- `beforeunload` warns the user if there are unsaved changes.

### Database

- **Durable hosted storage**: data lives in Turso, not on the web server's disk, so redeploys and restarts on Render do not wipe users or progress.
- **Foreign keys enforced** (libSQL default; verified by the cascade test) ensures `user_data.user_id` always references a real `users.id`.
- **`ON DELETE CASCADE`** means deleting a user cleans up their data row atomically.

---

## 6. Testing Strategy

### Philosophy

Tests are **integration-first**: most of the test suite exercises real HTTP requests against a real Express app backed by an in-memory libSQL database (`:memory:`, no Turso credentials needed). This catches the full request → middleware → route → DB → response cycle without mocking.

Unit tests target the two pure, stateless modules: `loadConfig` and `validateProgress`.

### Test Structure

```
test/helpers.js     — shared: startServer(), client (cookie-jar fetch), fixtures
test/api.test.js    — HTTP integration (auth flow, data CRUD, conflict, isolation, security)
test/config.test.js — loadConfig() unit tests
test/schema.test.js — validateProgress() unit tests
```

### Key Integration Test Scenarios

| Scenario | What It Verifies |
|----------|-----------------|
| Register → login → me → logout | Full auth lifecycle |
| PUT then GET | Data round-trips correctly |
| Two-tab conflict (PUT twice with same version) | 409 returned with server's copy |
| User A cannot read User B's data | Per-user isolation |
| GET `/data/app.db` returns 404 | File serving allowlist |
| GET `/css/styles.css` returns 200 | Static files work |
| Rapid login attempts | Rate limiting kicks in |

### Running Tests

```bash
npm test
# → node --test "test/*.test.js"
# Uses in-memory DB (:memory:) + ephemeral port (0)
# No fixtures to clean up; each test run is isolated
```

---

## 7. Coding Patterns

### Server-Side

- **No ORM**: raw SQL via `@libsql/client`'s `db.execute({ sql, args })`. Parameterised `args` prevent SQL injection; the API is async, so route handlers `await` queries (Express 5 forwards rejected promises to the error handler).
- **No global state**: `db` and `sessionSecret` flow through `createApp` and into route handlers via closure — no module-level singletons.
- **Explicit error handling**: every route has a try/catch that returns a structured `{ error }` JSON response.

### Frontend-Side

- **No framework, no bundler**: `js/app.js` is a plain ES2022 IIFE. DOM updates happen by setting `innerHTML` on the `<main>` container — simple full re-renders rather than virtual DOM diffing.
- **Event delegation**: all interactive elements are handled by `document.addEventListener` or `main.addEventListener` — never per-element. This avoids listener leaks across view re-renders.
- **Single source of truth**: `progress` (in-memory `ProgressStore`) is mutated directly; every mutation calls `renderCurrentView()` + `persist()`. No secondary copies or derived state caches.

---

## 8. Known Limitations & Future Considerations

| Limitation | Impact | Possible Improvement |
|------------|--------|----------------------|
| Turso free tier + network hop | Each query is a network round trip; depends on an external service and its credentials; free-tier usage limits apply (ample for ~10–20 users) | Co-locate the Render region with the Turso region; move to a paid Turso plan or PostgreSQL if usage grows |
| JWT in cookie (no blacklist) | Logout clears cookie but issued token remains valid until expiry if intercepted | Add a token revocation table or use short-lived tokens |
| No pagination on data read | `user_data.data` JSON blob grows with roadmap size | Already bounded by 5 MB limit; current roadmap is well under |
| `js/app.js` is a monolith (~1961 lines) | Harder to navigate; no tree-shaking | Split into view modules (refactor plan drafted in `.claude/code-refactor-plan.md`) |
| Python parser as manual step | Roadmap content updates require a developer with Python | Could become a CI step or a small Node script |
| No HTTPS in development | Cookies with `Secure` flag off | Use `mkcert` or a local reverse proxy for HTTPS dev |
| Single user per account | No team/shared progress | Would require multi-tenancy or shared roadmap features |
