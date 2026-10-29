# Project Rules

## Coding Standards

This project uses **Node.js (≥22) + Express 5 + vanilla JS + Turso (libSQL)**. Apply the following standards on every code change:

### General
- Prefer `const` over `let`; never use `var`
- Use `async/await` — no raw `.then()` chains
- Validate all user input at the Express route boundary; trust nothing from `req.body`, `req.query`, or `req.params`
- Never log secrets, tokens, or full SQL query results
- Keep functions small and single-purpose; extract helpers when a function exceeds ~30 lines

### JavaScript (server & client)
- Follow the Airbnb style guide as the baseline
- Use named exports; avoid default exports except for Express routers
- Prefer early returns over deeply nested `if/else`
- Use template literals for string construction; avoid concatenation
- Handle all async errors with `try/catch` — never let unhandled promise rejections through
- Always include meaningful HTTP status codes in responses (not just 200/500)

### Express / API
- Never expose raw database errors or stack traces to the client
- Return consistent JSON shapes: `{ data, error, message }`
- Rate-limit sensitive endpoints (login, register, password reset)
- Use `helmet()` and validate `Content-Type` on POST/PUT routes
- Parameterise every SQL query — no string interpolation in queries

### Turso / Database
- Always use parameterised queries via `@libsql/client` (`args` array)
- Keep DB access in `server/db.js` or dedicated repository modules — never query directly from route handlers
- Index columns used in `WHERE` clauses for user-facing queries

### Frontend (vanilla JS)
- Escape all user-supplied content before inserting into the DOM (`textContent`, not `innerHTML`, or explicit sanitisation)
- Separate DOM manipulation from fetch/API logic
- Use `fetch` with explicit `Content-Type: application/json` headers on POST/PUT
- Never store JWTs or sensitive data in `localStorage` — use `httpOnly` cookies or memory

---

## Documentation Rule

Whenever you **implement a new feature** or **update an existing feature**, you must:

1. **Update `README.md`** — reflect the change in the relevant section (features list, setup steps, API reference, etc.)
2. **Update the feature's documentation file** in `documentation/` if one exists
3. **Create a new file** in `documentation/` if no file covers the feature yet — name it `<feature-name>.md` using kebab-case (e.g. `documentation/auth-flow.md`)

The documentation update is part of the task — do not mark work complete without it.

Existing docs:
- `documentation/api-design.md`
- `documentation/database-design.md`
- `documentation/high-level-design.md`
- `documentation/low-level-design.md`
- `documentation/engineering-foundations.md`
- `documentation/multi-roadmap.md`
