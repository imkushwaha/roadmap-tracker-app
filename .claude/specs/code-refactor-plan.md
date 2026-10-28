# Code Refactor Plan — Roadmap Dashboard

**Status:** Draft  
**Scope:** All non-generated source files (`server/`, `js/`, `scripts/`, `test/`)  
**Goals:** Modularisation (FP + OOP), type safety via JSDoc/TypeScript types and Python type hints, PEP 8 compliance, SOLID principles

---

## 1. Audit Summary

| File | LOC | Key Issues |
|---|---|---|
| `server/app.js` | 222 | God-function; mixed auth, routing, middleware, error handling |
| `server/config.js` | 38 | Minor: no JSDoc; validation logic inline in loader |
| `server/db.js` | 27 | Minor: no JSDoc; schema SQL embedded as raw string |
| `server/index.js` | 23 | Acceptable; graceful-shutdown could be a helper |
| `js/api.js` | 39 | IIFE style (pre-ESM); no JSDoc; auth/data concerns mixed |
| `js/progress-schema.js` | 130 | UMD boilerplate; validator function is one large flat function |
| `scripts/md_to_json.py` | 627 | Global mutable state; no type hints; all parsing in module scope |
| `test/helpers.js` | 64 | Minor: no JSDoc; `client` helper has overloaded signature |
| `test/api.test.js` | 341 | Minor: inline fixture construction scattered across tests |

---

## 2. SOLID Violations Identified

### 2.1 Single Responsibility Principle (SRP)

- **`server/app.js` — `createApp`**: One factory function owns middleware wiring, prepared-statement definitions, bcrypt dummy-hash init, session issuance, auth route handlers, data route handlers, static file serving, and error handling. Each of these is a separate concern that should live in its own module.
- **`scripts/md_to_json.py` — `main()`**: Orchestrates file I/O, line parsing, phase construction, section routing, counter parsing, mastery parsing, reference parsing, and JSON/JS file output — all in one function.
- **`js/progress-schema.js` — `validateProgress`**: Validates `items`, `counters`, `celebratedPhases`, `settings`, and `custom` (topics + phases) in a single flat function.

### 2.2 Open/Closed Principle (OCP)

- **Route handlers in `app.js`**: Adding a new API resource requires editing the `createApp` factory. Routers registered by name (e.g., `authRouter`, `dataRouter`) would allow extension without touching the factory.
- **`SECTION_ROUTING` in `md_to_json.py`**: New routing destinations (beyond `"reference"`, `"counters"`, `"mastery"`, `int`) require an `elif` branch in `main()`. A dispatch table or strategy map would make it extensible.

### 2.3 Dependency Inversion Principle (DIP)

- **`server/app.js`**: Directly imports and calls `bcrypt`, `jwt`, `express`, and `cookie-parser`. Route handlers are tightly coupled to these concrete libraries. Wrapping each in a thin interface (e.g., `hashPassword(pw)`, `verifyToken(token)`) would let tests substitute fakes without mocking the entire library.
- **`scripts/md_to_json.py`**: `load_lines()` hardcodes `SRC` (a module-level `Path`). `main()` hardcodes `OUT`. Injecting paths as parameters makes the parser testable with fixture files.

### 2.4 Interface Segregation Principle (ISP)

- **`js/api.js` — `window.Api`**: A single `Api` object exposes both auth methods (`me`, `login`, `register`, `logout`) and data methods (`getData`, `putData`). Client code that only needs data sync is forced to depend on the whole surface.

### 2.5 Liskov Substitution Principle (LSP)

- Not broadly violated; LSP is less common in functional JS, but the `db` argument to `createApp` is assumed to have specific prepared-statement semantics that aren't documented, making it hard to substitute a different store.

---

## 3. Refactor Plan by File

---

### 3.1 `server/app.js` → split into `server/routes/auth.js` + `server/routes/data.js` + `server/middleware/`

**Objective:** Break the 222-line God-function into focused, testable units.

#### 3.1.1 Extract `server/auth/service.js` (SRP + DIP)

Create a pure-function auth service with no Express dependency:

```js
/**
 * @typedef {{ id: number, username: string }} UserRow
 * @typedef {{ ok: true, user: UserRow } | { ok: false, reason: string }} AuthResult
 */

/**
 * Hash a plain-text password.
 * @param {string} password
 * @param {number} cost
 * @returns {Promise<string>}
 */
async function hashPassword(password, cost) { ... }

/**
 * Verify a plain-text password against a stored hash.
 * @param {string} password
 * @param {string} hash
 * @returns {Promise<boolean>}
 */
async function verifyPassword(password, hash) { ... }

/**
 * Sign a session JWT.
 * @param {{ id: number, username: string }} user
 * @param {string} secret
 * @param {number} sessionDays
 * @returns {string}
 */
function signToken(user, secret, sessionDays) { ... }

/**
 * Verify and decode a session JWT.
 * @param {string} token
 * @param {string} secret
 * @returns {{ sub: string, un: string } | null}
 */
function verifyToken(token, secret) { ... }

module.exports = { hashPassword, verifyPassword, signToken, verifyToken };
```

#### 3.1.2 Extract `server/auth/validators.js` (SRP)

```js
/** @typedef {{ valid: true } | { valid: false, error: string }} ValidationResult */

/**
 * Validate a registration username.
 * @param {unknown} username
 * @returns {ValidationResult}
 */
function validateUsername(username) { ... }

/**
 * Validate a registration password (length + byte-length).
 * @param {unknown} password
 * @returns {ValidationResult}
 */
function validatePassword(password) { ... }

module.exports = { validateUsername, validatePassword };
```

#### 3.1.3 Extract `server/routes/auth.js` (SRP)

```js
/**
 * Build and return an Express Router for authentication endpoints.
 *
 * @param {object} options
 * @param {import('better-sqlite3').Database} options.db
 * @param {import('../auth/service')} options.authService
 * @param {import('../auth/validators')} options.validators
 * @param {object} options.sessionConfig - { secret, sessionDays, cookieSecure }
 * @param {object} options.rateLimitConfig - { windowMs, max }
 * @returns {import('express').Router}
 */
function createAuthRouter(options) { ... }

module.exports = { createAuthRouter };
```

#### 3.1.4 Extract `server/routes/data.js` (SRP)

```js
/**
 * Build and return an Express Router for user-data endpoints.
 *
 * @param {object} options
 * @param {import('better-sqlite3').Database} options.db
 * @param {Function} options.requireAuth - Middleware that sets req.user
 * @param {Function} options.validateProgress - Schema validator
 * @returns {import('express').Router}
 */
function createDataRouter(options) { ... }

module.exports = { createDataRouter };
```

#### 3.1.5 Slim down `server/app.js`

The factory becomes a thin compositor:

```js
/**
 * Create and configure the Express application.
 *
 * @param {object} options
 * @param {import('better-sqlite3').Database} options.db
 * @param {string} options.sessionSecret
 * @param {boolean} [options.cookieSecure]
 * @param {boolean|string|number} [options.trustProxy]
 * @param {number} [options.bcryptCost]
 * @param {{ windowMs: number, max: number }} [options.authRateLimit]
 * @param {string} [options.bodyLimit]
 * @param {string} [options.staticRoot]
 * @returns {import('express').Application}
 */
function createApp(options) { ... }
```

---

### 3.2 `server/config.js`

**Issues:** No JSDoc; inline validation logic; `loadConfig` returns a raw object with no named type.

**Refactor:**

```js
/**
 * @typedef {object} AppConfig
 * @property {boolean} isProduction
 * @property {string}  sessionSecret
 * @property {string}  dbPath
 * @property {number}  port
 * @property {boolean} cookieSecure
 * @property {boolean|string|number} trustProxy
 */

/**
 * Load and validate application configuration from environment variables.
 *
 * Throws if `SESSION_SECRET` is absent or too short in production.
 *
 * @param {NodeJS.ProcessEnv} [env] - Defaults to `process.env`.
 * @returns {AppConfig}
 */
function loadConfig(env = process.env) { ... }
```

Extract `parseTrustProxy(raw)` and `resolveDbPath(raw)` as private helpers so `loadConfig` stays readable.

---

### 3.3 `server/db.js`

**Issues:** Schema SQL is an inline string; no JSDoc; no type for the return value.

**Refactor:**

```js
/**
 * Open (or create) the SQLite database and apply the schema.
 *
 * Creates the parent directory automatically for file-backed databases.
 * Uses WAL journal mode and enforces foreign keys.
 *
 * @param {string} dbPath - Absolute path, or `":memory:"` for an in-memory database.
 * @returns {import('better-sqlite3').Database}
 */
function openDb(dbPath) { ... }
```

Move the `CREATE TABLE` DDL to a separate constant `SCHEMA_SQL` at the top of the file so it can be read and reviewed independently of the function body.

---

### 3.4 `server/index.js`

**Issues:** Graceful-shutdown logic is inline; no JSDoc.

**Refactor:** Extract `attachShutdownHandlers(server, db)` as a named helper:

```js
/**
 * Register SIGINT and SIGTERM handlers that gracefully close the HTTP server
 * and the database connection before exiting.
 *
 * @param {import('http').Server} server
 * @param {import('better-sqlite3').Database} db
 * @returns {void}
 */
function attachShutdownHandlers(server, db) { ... }
```

---

### 3.5 `js/api.js` — Browser API client (ISP + JSDoc)

**Issues:** Single global `window.Api` mixes auth and data; IIFE pattern hides the shape from editors; no JSDoc.

**Refactor:** Split into two named exports consumed by a thin `window.Api` shim:

```js
/**
 * @typedef {{ username: string }} UserInfo
 * @typedef {{ user: UserInfo }} AuthResponse
 * @typedef {{ data: object|null, version: number, updatedAt?: string }} DataResponse
 */

/**
 * Low-level HTTP transport — single point of error normalisation.
 *
 * @param {'GET'|'POST'|'PUT'} method
 * @param {string} path
 * @param {object} [body]
 * @returns {Promise<object|null>}
 */
async function call(method, path, body) { ... }

/** Auth API surface. */
const AuthApi = {
  /** @returns {Promise<AuthResponse>} */
  me: () => call('GET', '/api/auth/me'),
  /** @param {string} username @param {string} password @returns {Promise<AuthResponse>} */
  login: (username, password) => call('POST', '/api/auth/login', { username, password }),
  /** @param {string} username @param {string} password @returns {Promise<AuthResponse>} */
  register: (username, password) => call('POST', '/api/auth/register', { username, password }),
  /** @returns {Promise<null>} */
  logout: () => call('POST', '/api/auth/logout'),
};

/** Data sync API surface. */
const DataApi = {
  /** @returns {Promise<DataResponse>} */
  getData: () => call('GET', '/api/data'),
  /** @param {object} data @param {number} version @returns {Promise<{ version: number, updatedAt: string }>} */
  putData: (data, version) => call('PUT', '/api/data', { data, version }),
};

// Backwards-compatible shim
window.Api = { ...AuthApi, ...DataApi };
window.AuthApi = AuthApi;
window.DataApi = DataApi;
```

---

### 3.6 `js/progress-schema.js` — Validator (SRP + OCP)

**Issues:** One 100-line `validateProgress` function validates five independent sections. Adding a new top-level key requires editing that function.

**Refactor:** Compose small per-section validators:

```js
/**
 * @typedef {{ ok: true } | { ok: false, errors: string[] }} ValidationResult
 */

/**
 * Collect validation errors for the `items` map.
 * @param {unknown} items
 * @param {string[]} errors
 */
function validateItems(items, errors) { ... }

/**
 * Collect validation errors for the `counters` map.
 * @param {unknown} counters
 * @param {string[]} errors
 */
function validateCounters(counters, errors) { ... }

/**
 * Collect validation errors for `celebratedPhases`.
 * @param {unknown} phases
 * @param {string[]} errors
 */
function validateCelebratedPhases(phases, errors) { ... }

/**
 * Collect validation errors for `settings`.
 * @param {unknown} settings
 * @param {string[]} errors
 */
function validateSettings(settings, errors) { ... }

/**
 * Collect validation errors for the `custom` extension block.
 * @param {unknown} custom
 * @param {string[]} errors
 */
function validateCustom(custom, errors) { ... }

/**
 * Validate a progress data object against the schema.
 *
 * Deliberately tolerant of unknown top-level keys and missing optional
 * sections; only rejects known fields with the wrong type.
 *
 * @param {unknown} data
 * @returns {ValidationResult}
 */
function validateProgress(data) {
  const errors = [];
  if (!isObj(data)) return { ok: false, errors: ['Progress data must be a JSON object.'] };
  validateItems(data.items, errors);
  if (data.counters !== undefined) validateCounters(data.counters, errors);
  if (data.celebratedPhases !== undefined) validateCelebratedPhases(data.celebratedPhases, errors);
  if (data.settings !== undefined) validateSettings(data.settings, errors);
  if (data.custom !== undefined) validateCustom(data.custom, errors);
  return { ok: errors.length === 0, errors: errors.slice(0, MAX_ERRORS) };
}
```

This makes `validateProgress` open for new sections (add a new validator + one line) without modifying existing ones.

---

### 3.7 `scripts/md_to_json.py` — Parser (SRP + OCP + DIP + type hints)

This is the most complex refactor. The 627-line script has global state, no type hints, and a monolithic `main()`.

#### 3.7.1 Add type hints throughout

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # forward references only

# Replace bare dicts with dataclasses or TypedDicts for all data shapes:
from typing import TypedDict, Literal, Optional


class Subtask(TypedDict):
    id: str
    title: str
    status: Literal["not_started"]
    notes: str
    link: str
    dueDate: None


class ChecklistGroup(TypedDict):
    label: Optional[str]
    subtasks: list[Subtask]


class Topic(TypedDict):
    id: str
    title: str
    depth: Optional[str]
    kind: Literal["study", "build", "benchmark"]
    groups: list[ChecklistGroup]
```

Apply `-> ReturnType` annotations to every function signature.

#### 3.7.2 Eliminate global mutable state — `slug_counter`

`slug_counter` is a module-level dict mutated by `slugify`. This makes the script non-idempotent in the same process (e.g., tests or imports).

```python
class SlugRegistry:
    """Tracks slug usage counts to de-duplicate generated IDs."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def slugify(self, text: str, prefix: str = "") -> str:
        """Return a unique kebab-case slug for *text*, optionally prefixed."""
        base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        if prefix:
            base = f"{prefix}{base}"
        n = self._counts.get(base, 0)
        self._counts[base] = n + 1
        return base if n == 0 else f"{base}-{n + 1}"
```

Pass a `SlugRegistry` instance down the call chain instead of reading a global.

#### 3.7.3 Separate I/O from parsing (DIP)

`load_lines()` and the `OUT.write_text(...)` calls live in the same function as the parsing logic.

```python
def load_lines(path: Path) -> list[str]:
    """Read *path* and return its lines without trailing newlines."""
    return path.read_text(encoding="utf-8").splitlines()


def write_output(data: dict, json_path: Path, js_path: Path) -> None:
    """Serialise *data* to *json_path* and wrap it for *js_path*."""
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    js_path.write_text(
        "// Auto-generated by scripts/md_to_json.py — do not edit by hand.\n"
        f"window.ROADMAP_DATA = {json.dumps(data, indent=2)};\n",
        encoding="utf-8",
    )
```

`main()` wires them together; the parsing functions accept `list[str]` and return `dict`.

#### 3.7.4 Organise parsing into a `RoadmapParser` class (SRP + OCP)

```python
class RoadmapParser:
    """Parse a structured Markdown roadmap file into a JSON-serialisable dict.

    Args:
        lines: Source lines (from :func:`load_lines`).
        slug_registry: Shared slug registry; defaults to a new instance.
    """

    def __init__(
        self,
        lines: list[str],
        slug_registry: SlugRegistry | None = None,
    ) -> None:
        self._lines = lines
        self._slugs = slug_registry or SlugRegistry()

    def parse(self) -> dict:
        """Run the full parse and return the roadmap data dict."""
        ...

    # -- private helpers, one method per structural concern --

    def _parse_phase(
        self,
        h1_start: int,
        h1_end: int,
        phase_num: int,
        calendar_label: str,
        theme: str,
    ) -> dict:
        """Parse one month phase and return its data dict."""
        ...

    def _parse_week_section(
        self,
        start: int,
        end: int,
        phase_num: int,
        week_title: str,
        sec_type: str,
        section_id: str,
    ) -> list[dict]:
        """Return topic list for one week/theme section."""
        ...

    def _collect_checklist_groups(
        self,
        start: int,
        end: int,
        id_prefix: str,
    ) -> list[ChecklistGroup]:
        """Parse lines[start:end] into grouped checklist subtasks."""
        ...

    def _build_counters(self, start: int, end: int) -> list[dict]:
        """Parse the Quick Progress Snapshot counter block."""
        ...

    def _build_mastery(self, start: int, end: int) -> list[dict]:
        """Parse the flat mastery checklist into categories."""
        ...

    def _build_reference(self, start: int, end: int, title: str) -> dict:
        """Wrap a read-only narrative block."""
        ...
```

#### 3.7.5 PEP 8 items

- `SECTION_ROUTING` dict: the inline comments are fine; consistent 4-space indentation already present.
- Function `build_reference` duplicates logic from `extract_blocks`; merge them.
- `new_subtask` → rename `_new_subtask` (private helper) or make it a `RoadmapParser` method.
- `month_add` / `month_last_day` → move to a `date_utils.py` module or keep as module-level pure functions (acceptable; they have no side effects).
- Add a `if __name__ == "__main__":` guard — already present, no change needed.
- Add module-level docstring — already present, update to reflect new class structure.

---

### 3.8 `test/helpers.js`

**Issues:** `client` mixin (`.jar`, `.request`, `.get`, `.post`, `.put`) has no JSDoc; `sampleData` has no type.

**Refactor:**

```js
/**
 * @typedef {object} HttpResponse
 * @property {number} status
 * @property {object|null} body
 * @property {string} text
 * @property {Headers} headers
 * @property {string[]} setCookies
 */

/**
 * @typedef {object} TestClient
 * @property {Map<string,string>} jar - Cookie jar (name → value).
 * @property {(method: string, path: string, body?: unknown, headers?: Record<string,string>) => Promise<HttpResponse>} request
 * @property {(path: string) => Promise<HttpResponse>} get
 * @property {(path: string, body?: unknown) => Promise<HttpResponse>} post
 * @property {(path: string, body: unknown) => Promise<HttpResponse>} put
 */

/**
 * Create a minimal HTTP client with a persistent cookie jar.
 *
 * Each call to `client()` simulates a fresh browser with its own session.
 *
 * @param {string} base - Server base URL (e.g., `"http://127.0.0.1:3001"`).
 * @returns {TestClient}
 */
function client(base) { ... }

/**
 * Return a minimal valid progress data object.
 *
 * @param {Partial<import('../js/progress-schema').ProgressData>} [overrides]
 * @returns {import('../js/progress-schema').ProgressData}
 */
function sampleData(overrides = {}) { ... }
```

---

### 3.9 `test/api.test.js`

**Issues:** Fixture data (`creds`, inline `custom`, inline `bad` arrays) is defined inline per test. Centralise in `helpers.js`.

**Refactor:** Move common fixtures to `helpers.js`:

```js
/** @param {string} username @param {string} [password] */
const creds = (username, password = "correct-horse-1") => ({ username, password });

/** @type {import('../js/progress-schema').CustomData} */
const SAMPLE_CUSTOM = {
  phases: [...],
  topics: [...],
};
```

Import in tests rather than redefining per `describe` block.

---

## 4. Implementation Order

Tasks are sequenced so each step is independently reviewable and tests pass after every step.

| Step | File(s) | Change | Tests affected |
|---|---|---|---|
| 1 | `scripts/md_to_json.py` | Type hints + `SlugRegistry` class + I/O separation | None (script, not imported) |
| 2 | `scripts/md_to_json.py` | `RoadmapParser` class, methods, PEP 8 clean-up | None |
| 3 | `js/progress-schema.js` | Split into per-section validators; keep UMD wrapper | `test/schema.test.js` |
| 4 | `server/auth/service.js` | New file: `hashPassword`, `verifyPassword`, `signToken`, `verifyToken` | New unit tests |
| 5 | `server/auth/validators.js` | New file: `validateUsername`, `validatePassword` | New unit tests |
| 6 | `server/routes/auth.js` | Extract auth routes from `createApp`; use auth service + validators | `test/api.test.js` (auth suites) |
| 7 | `server/routes/data.js` | Extract data routes from `createApp` | `test/api.test.js` (data suites) |
| 8 | `server/app.js` | Slim down to compositor; add JSDoc to `createApp` | Full test suite |
| 9 | `server/config.js` | JSDoc + extract `parseTrustProxy` + `resolveDbPath` helpers | `test/config.test.js` |
| 10 | `server/db.js` | JSDoc + `SCHEMA_SQL` constant | `test/api.test.js` (static serving suite) |
| 11 | `server/index.js` | Extract `attachShutdownHandlers` | Manual / integration |
| 12 | `js/api.js` | Split `AuthApi` / `DataApi`; JSDoc; keep `window.Api` shim | Browser smoke test |
| 13 | `test/helpers.js` | JSDoc + centralise `creds` + `SAMPLE_CUSTOM` | All test suites |
| 14 | `test/api.test.js` | Import fixtures from helpers; no logic change | All test suites |

---

## 5. Coding Standards Checklist

### JavaScript / Node.js
- [ ] Every exported function has a JSDoc block: purpose, `@param` (name + type), `@returns`
- [ ] Every module has a one-line module-level comment stating its responsibility
- [ ] No function longer than ~40 lines; extract named helpers for any block needing a comment
- [ ] No inline `// eslint-disable` unless unavoidable (the existing one in `app.js` is fine)
- [ ] Prefer `const` over `let`; `let` only where rebinding is genuinely needed
- [ ] No bare `catch (e) {}` without at least a `console.error` or a re-throw

### Python
- [ ] Module-level docstring on every `.py` file
- [ ] Type hints on every function signature (parameters + return type)
- [ ] Use `TypedDict` for any dict with a fixed shape
- [ ] No global mutable state
- [ ] Max line length 99 characters (PEP 8 allows 79; this project's lines go to ~90)
- [ ] All functions have a one-line docstring; multi-paragraph only where the algorithm is non-obvious
- [ ] `pathlib.Path` throughout (already in use; keep it)
- [ ] Private helpers prefixed with `_` or scoped as class methods

---

## 6. Files NOT Touched

| File | Reason |
|---|---|
| `data/roadmap.json` | Auto-generated |
| `data/roadmap.js` | Auto-generated |
| `data/roadmap.md` | Source content, not code |
| `data/schema.md` | Documentation |
| `css/styles.css` | Out of scope |
| `index.html` | Out of scope |
| `package.json` | No structural changes needed |
| `.env.example` | Configuration template, not code |
| `node_modules/**` | Third-party |
