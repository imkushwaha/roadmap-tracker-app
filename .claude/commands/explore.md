# /explore — Session Project Walkthrough

Run this at the start of any new session **before making code changes**. It orients you on the current project state so that every suggestion and edit is grounded in what's actually there — not what was there in a previous session.

## Steps

1. **Read key config files**
   - `package.json` — dependencies, scripts, Node version
   - `.env.example` or `.env` (if present, never log actual secrets) — understand env vars
   - `CLAUDE.md` — refresh the active rules

2. **Survey the server**
   - Read `server/app.js` — middleware stack, router mounts
   - Read `server/db.js` — DB client setup, any schema helpers
   - List `server/routes/` and read each route file — understand endpoints, auth middleware, and response shapes
   - List `server/auth/` if it exists — auth strategy and JWT handling

3. **Survey the frontend**
   - Read `index.html` — page structure, script/style includes
   - List `js/` and read each file — understand app bootstrap, API client, and UI modules
   - List `css/` — note any theme or layout files

4. **Survey tests**
   - List `test/` — note which modules are covered
   - Briefly read `test/helpers.js` if present — understand test DB setup and fixtures

5. **Check documentation**
   - List `documentation/` — note which docs exist
   - Read `README.md` — current feature list, setup steps, known gaps

6. **Summarise findings**
   - Current tech stack and versions
   - Data flow: request → route → DB → response
   - Auth mechanism (JWT shape, cookie vs header)
   - Any in-progress work visible from git status or unfinished TODOs in code
   - Which documentation files map to which features

After completing this walkthrough, state what you found in 6–10 bullet points, then ask the user what they'd like to change or build.
