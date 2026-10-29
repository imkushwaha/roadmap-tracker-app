# Generic Tracker App — Implementation Plan

**Session:** from-ai-roadmap-to-generic-roadmap  
**Date:** 2026-10-29  
**Status:** Phase 1 done · Phase 2 done (**built differently from this plan — see the note below**) · Phase 3 not started

> **Phase 2 deviation (read this first).** Sections 4.4, 6.5, 6.6, 7 and 8 and the original Phase 2 list below
> describe a separate up-front roadmap builder, a `roadmaps.definition` column, a
> `RoadmapDefinition` schema validator and `js/roadmap-builder.js`. **None of that was built.** While
> implementing, it turned out the app already had complete in-roadmap editors (add/delete month →
> section → topic → tasks) storing user content in `progress.custom`. A custom roadmap is therefore an
> **empty curriculum** (`BLANK_DATA`) whose whole structure lives in `progress.custom`, built with those
> existing editors. Reasons: reuses proven UI and storage; editing after creation comes for free; no
> schema change; no orphaned progress keys; plan and progress save and conflict-resolve together. See
> "Phase 2 — as built" below and `documentation/multi-roadmap.md`. A creation wizard that pre-fills
> `progress.custom`, templates, or a stored definition remain options for a later phase.

---

## 1. Goal

Transform the single-roadmap "AI Engineer Roadmap" tracker into a **generic multi-roadmap tracker
app**. After login, the user lands on a **Roadmap Dashboard** showing all their roadmaps. The AI
Engineer Roadmap is pre-seeded for every new account. Users can create, open, and delete additional
roadmaps. Each roadmap has its own independent progress data.

---

## 2. User-Facing Changes Summary

| Screen | Before | After |
|---|---|---|
| After login / boot | Directly opens AI Engineer Roadmap | Shows Roadmap Dashboard |
| Roadmap Dashboard | Does not exist | Grid of roadmap cards + Create / Create with AI buttons |
| Roadmap card | — | Name, description, progress %, last updated, Open + Delete |
| Delete | — | Opens confirmation modal before deleting |
| Create new roadmap | — | Opens a form/wizard (name, description, structure builder) |
| Create with AI | — | "Coming Soon" placeholder card / button |
| Inside a roadmap | All 7 views (Overview, Timeline, …) | Same 7 views; Back button to Dashboard |

---

## 3. Architecture Changes

### 3.1 What stays the same
- Express 5 backend structure (`createApp` factory, middleware, auth module)
- Authentication system (JWT cookies, register/login/logout/me) — no change
- All 7 views inside a roadmap (overview, timeline, kanban, checklist, thisweek, mastery, reference)
- ProgressStore shape + `validateProgress` — unchanged
- `data/roadmap.js` → `window.ROADMAP_DATA` — still the AI Engineer roadmap source
- Zero-build frontend philosophy (no bundler)

### 3.2 What changes
- `user_data` table → replaced by `roadmaps` + `roadmap_progress` tables
- `/api/data` → replaced by `/api/roadmaps/*` routes
- `app.js` flow: post-login goes to Roadmap Dashboard, not directly to roadmap views
- `DATA` (currently `const DATA = window.ROADMAP_DATA`) becomes dynamic — set at roadmap open time
- New Roadmap Dashboard screen
- New Roadmap Creation form

---

## 4. Database Design

### 4.1 New tables

```sql
-- One row per roadmap per user.
-- source = 'builtin_ai_engineer' uses window.ROADMAP_DATA (no definition stored).
-- source = 'custom' stores the full definition JSON.
CREATE TABLE IF NOT EXISTS roadmaps (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT    NOT NULL,
  description TEXT    NOT NULL DEFAULT '',
  source      TEXT    NOT NULL DEFAULT 'custom',    -- 'builtin_ai_engineer' | 'custom'
  definition  TEXT,                                 -- NULL for builtin; RoadmapDefinition JSON for custom
  created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Per-roadmap progress. Same shape as the old user_data.
CREATE TABLE IF NOT EXISTS roadmap_progress (
  roadmap_id  INTEGER PRIMARY KEY REFERENCES roadmaps(id) ON DELETE CASCADE,
  data        TEXT    NOT NULL,
  version     INTEGER NOT NULL,
  updated_at  TEXT    NOT NULL
);
```

### 4.2 Migration strategy for existing `user_data` rows

Existing users already have progress in `user_data`. On startup (`server/db.js`), after applying
the new schema, run these migration statements (idempotent — safe to run every boot):

```sql
-- Step 1: For every user who has user_data but no roadmaps row yet, create the builtin roadmap row.
INSERT INTO roadmaps (user_id, name, source)
  SELECT ud.user_id, 'AI Engineer Roadmap', 'builtin_ai_engineer'
  FROM user_data ud
  WHERE NOT EXISTS (
    SELECT 1 FROM roadmaps r WHERE r.user_id = ud.user_id
  );

-- Step 2: Copy their progress into roadmap_progress.
INSERT INTO roadmap_progress (roadmap_id, data, version, updated_at)
  SELECT r.id, ud.data, ud.version, ud.updated_at
  FROM roadmaps r
  JOIN user_data ud ON r.user_id = ud.user_id
  WHERE r.source = 'builtin_ai_engineer'
    AND NOT EXISTS (
      SELECT 1 FROM roadmap_progress rp WHERE rp.roadmap_id = r.id
    );
```

The old `user_data` table is kept alive during the transition period (backward compatibility) and
can be dropped in a later cleanup migration once the new schema is confirmed stable.

### 4.3 Register route — seed AI Engineer Roadmap

When a new user registers (`POST /api/auth/register`), immediately insert a `roadmaps` row:

```sql
INSERT INTO roadmaps (user_id, name, source)
VALUES (?, 'AI Engineer Roadmap', 'builtin_ai_engineer');
```

### 4.4 RoadmapDefinition JSON shape (for custom roadmaps)

The `definition` column stores a JSON object that mirrors `window.ROADMAP_DATA`:

```typescript
type RoadmapDefinition = {
  meta?: {
    horizonStart?: string;  // "YYYY-MM-DD" — used by defaultStartMonth()
  };
  phases: Phase[];          // same Phase[] type as ROADMAP_DATA.phases
};
```

For custom roadmaps, phases/sections/topics/subtasks are user-defined. IDs are client-generated
UUIDs (e.g. `"custom-phase-<uuid>"`). IDs must be stable once saved — ProgressStore keys off them.

---

## 5. API Design

### 5.1 New routes (to be added to `server/routes/roadmaps.js`)

All routes require `requireAuth`.

```
GET    /api/roadmaps                   List all roadmaps for the current user
POST   /api/roadmaps                   Create a new custom roadmap
DELETE /api/roadmaps/:id               Delete a roadmap (cascades progress)

GET    /api/roadmaps/:id/progress      Get progress data for a roadmap
PUT    /api/roadmaps/:id/progress      Save progress data (optimistic CAS, same as /api/data)
```

#### `GET /api/roadmaps`
Returns roadmap metadata (no definition, no progress data — keeps payload small).

```json
{
  "roadmaps": [
    {
      "id": 1,
      "name": "AI Engineer Roadmap",
      "description": "",
      "source": "builtin_ai_engineer",
      "createdAt": "2026-10-01T...",
      "updatedAt": "2026-10-29T..."
    },
    {
      "id": 2,
      "name": "My Custom Roadmap",
      "description": "Learning Rust in 3 months",
      "source": "custom",
      "createdAt": "2026-10-20T...",
      "updatedAt": "2026-10-25T..."
    }
  ]
}
```

#### `POST /api/roadmaps`
```json
// Request
{
  "name": "My Custom Roadmap",
  "description": "Optional description",
  "definition": { "meta": {}, "phases": [] }   // can be empty phases initially
}
// Response 201
{ "id": 3, "name": "...", "source": "custom", "createdAt": "..." }
```

Validation: `name` required (1–128 chars). `definition` validated against `RoadmapDefinitionSchema`
(new validator, similar to `validateProgress`).

#### `DELETE /api/roadmaps/:id`
- Returns 404 if roadmap not found or doesn't belong to user.
- Returns 403 if attempting to delete the `builtin_ai_engineer` roadmap (cannot delete default). ← *design decision: or allow it?*
- On success: 204. DB cascade deletes `roadmap_progress` row.

#### `GET /api/roadmaps/:id/progress`
Same shape as old `GET /api/data` response.
```json
{ "data": null, "version": 0 }                // new roadmap
{ "data": { ...ProgressStore }, "version": 4, "updatedAt": "..." }
```
For `builtin_ai_engineer` roadmaps: same response; definition not included (frontend loads from
`window.ROADMAP_DATA`). For custom roadmaps: also returns the definition:
```json
{
  "definition": { "meta": {}, "phases": [...] },
  "data": { ...ProgressStore },
  "version": 2,
  "updatedAt": "..."
}
```

#### `PUT /api/roadmaps/:id/progress`
Identical to old `PUT /api/data` logic (compare-and-swap on version). Same request/response shape.

### 5.2 Old `/api/data` endpoints

Keep `/api/data` temporarily as a legacy shim pointing to the user's first `builtin_ai_engineer`
roadmap. This ensures any in-flight client code or tests don't break during development. Remove in
a cleanup pass once all code is migrated.

---

## 6. Frontend Changes

### 6.1 New application flow

```
boot()
  │ GET /api/auth/me
  ↓ 401 → showAuth()
  ↓ 200
showRoadmapDashboard(username, firstName, lastName)
  │ GET /api/roadmaps
  ↓
renderDashboard(roadmaps[])
  • Cards: Open | Delete
  • "Create new roadmap" button
  • "Create with AI" (Coming Soon)
  ↓ user clicks "Open"
openRoadmap(roadmap)
  │ GET /api/roadmaps/:id/progress
  ↓
loadRoadmapData(roadmap, progressRes)
  • sets DATA = builtin ? window.ROADMAP_DATA : progressRes.definition
  • sets session.roadmapId = roadmap.id
  • rebuilds INDEX
  • hides Dashboard, shows main app views
  • same rerender() as before
  ↓ user clicks "← Roadmaps" (back button in header)
showRoadmapDashboard()   ← flush save first if dirty
```

### 6.2 `js/app.js` changes

**State changes:**
```js
// Add to session object:
session.roadmapId    = null;   // integer | null
session.roadmapName  = "";
session.roadmapSource = "";    // 'builtin_ai_engineer' | 'custom'

// DATA becomes mutable:
let DATA = null;               // was: const DATA = window.ROADMAP_DATA
```

**New functions:**
- `showRoadmapDashboard(username, firstName, lastName)` — shows the Dashboard screen
- `renderDashboard(roadmaps)` — renders roadmap cards into the dashboard container
- `openRoadmap(roadmap)` — fetches progress, sets DATA, calls `loadRoadmapData`
- `loadRoadmapData(roadmap, progressRes)` — replaces `loadUserData` inner logic
- `confirmDeleteRoadmap(roadmap)` — opens a confirmation modal before calling delete API
- `backToDashboard()` — flushes save if dirty, then shows roadmap dashboard

**Changed functions:**
- `boot()` — after `me()`, calls `showRoadmapDashboard()` instead of `loadUserData()`
- `submitAuth()` — after successful auth, calls `showRoadmapDashboard()` instead of `loadUserData()`
- `loadUserData()` → replaced/split; `loadRoadmapData()` takes over the roadmap-specific part
- `doSave()` / `DataApi.putData()` → use `/api/roadmaps/${session.roadmapId}/progress`
- `defaultStartMonth()` — falls back to `DATA?.meta?.horizonStart` if present, else today
- All `window.Api.getData()` / `window.Api.putData()` calls → use new `RoadmapApi` namespace

**Header changes:**
- Add "← Roadmaps" back button next to the brand in `<header>` (visible only when inside a roadmap)
- Profile trigger area stays the same

**Tab/view changes:**
- `mastery` tab: show only if roadmap has topics with `depth` annotations. For custom roadmaps
  without depth data, hide this tab.
- `reference` tab: show only if `DATA.phases` has a phase/section of type `"reference"` or if
  `DATA.reference` exists. Custom roadmaps likely won't have this.
- `thisweek` tab: works generically already (uses `weekNumber` from sections) — degrade gracefully
  if no sections have `weekNumber`.

### 6.3 New Roadmap Dashboard HTML block

Add to `index.html` (alongside `#authScreen`):

```html
<div id="dashboardScreen" class="dashboard-screen hidden">
  <header class="dashboard-header">
    <div class="brand">
      <span class="brand-icon">🗺</span>
      <h1>My Roadmaps</h1>
    </div>
    <div class="profile-anchor" id="dashProfileAnchor"><!-- same profile trigger --></div>
  </header>
  <main class="dashboard-main">
    <div id="dashboardGrid" class="dashboard-grid"></div>
    <div class="dashboard-actions">
      <button id="createRoadmapBtn" class="btn btn-primary">+ New Roadmap</button>
      <button id="createWithAiBtn" class="btn btn-secondary" disabled title="Coming soon">
        ✦ Create with AI  <span class="coming-soon-badge">Coming Soon</span>
      </button>
    </div>
  </main>
</div>
```

Roadmap card template (rendered by JS):
```html
<div class="roadmap-card" data-id="1">
  <div class="roadmap-card-body">
    <h3 class="roadmap-card-name">AI Engineer Roadmap</h3>
    <p class="roadmap-card-desc">10-Month Execution Tracker</p>
    <div class="roadmap-card-meta">
      <span class="roadmap-card-progress">42% complete</span>
      <span class="roadmap-card-updated">Updated 3 days ago</span>
    </div>
  </div>
  <div class="roadmap-card-actions">
    <button class="btn btn-primary" data-action="open-roadmap" data-id="1">Open</button>
    <button class="btn btn-ghost btn-danger" data-action="delete-roadmap" data-id="1">Delete</button>
  </div>
</div>
```

### 6.4 New API namespace `RoadmapApi` in `js/api.js`

```js
const RoadmapApi = {
  list:           ()           => call("GET",    "/api/roadmaps"),
  create:         (body)       => call("POST",   "/api/roadmaps", body),
  del:            (id)         => call("DELETE", `/api/roadmaps/${id}`),
  getProgress:    (id)         => call("GET",    `/api/roadmaps/${id}/progress`),
  putProgress:    (id, data, version) => call("PUT", `/api/roadmaps/${id}/progress`, { data, version }),
};
window.RoadmapApi = RoadmapApi;
```

### 6.5 Roadmap creation form

A modal or full-screen form for creating a custom roadmap.

**Step 1 — Basics:**
- Roadmap name (required)
- Description (optional)
- Start month (optional, defaults to today)

**Step 2 — Structure builder (Phase → Section → Topic → Task):**
- Add months (phases): title, objective
- Per phase: add sections (either "Week 1–4" shortcuts or free-form theme sections)
- Per section: add topics (title, optional depth tag)
- Per topic: add tasks (each with a title → becomes a subtask in ProgressStore)

This is the most complex UI piece. For the initial implementation, a simple sequential form is
acceptable. A drag-and-drop tree editor is a future enhancement.

**IDs:** Generated client-side as `"cp-" + crypto.randomUUID()` (phase), `"cs-" + ...` (section),
`"ct-" + ...` (topic), `"ck-" + ...` (subtask). These are stable once saved.

### 6.6 New file: `js/roadmap-builder.js`

Given `app.js` is already 1961 lines, the roadmap creation/editing form logic should live in a
separate file. It exports `window.RoadmapBuilder`:

```js
window.RoadmapBuilder = {
  open(onSave)    { /* opens the creation modal */ },
  close()         { /* closes */ },
};
```

The `app.js` calls `window.RoadmapBuilder.open((definition) => { ... })` when the user clicks
"New Roadmap".

Add `<script src="js/roadmap-builder.js"></script>` to `index.html` before `app.js`.

---

## 7. Validation — New `RoadmapDefinitionSchema`

Add `js/roadmap-definition-schema.js` (UMD, like `progress-schema.js`):

```js
function validateRoadmapDefinition(def) { ... }
// Returns { ok: boolean, errors: string[] }
```

Validates:
- `phases` is an array
- Each phase: `id` (string), `title` (string), `sections` (array)
- Each section: `id`, `title`, `type` ("week"|"theme"), optional `weekNumber` (1-4)
- Each topic: `id`, `title`, `groups` array
- Each group: `subtasks` array, each with `id` + `title`
- All IDs are unique within the definition

Used in `server/routes/roadmaps.js` on `POST /api/roadmaps` (and `PUT` if we add editing).

---

## 8. New Server File: `server/routes/roadmaps.js`

```js
function createRoadmapsRouter({ db, requireAuth }) {
  const router = express.Router();
  // GET /               → list roadmaps
  // POST /              → create roadmap
  // DELETE /:id         → delete roadmap
  // GET /:id/progress   → get progress
  // PUT /:id/progress   → save progress (CAS)
  return router;
}
```

Mounted in `server/app.js` as:
```js
app.use("/api/roadmaps", createRoadmapsRouter({ db, requireAuth }));
```

---

## 9. Implementation Phases

### Phase 1 — Infrastructure (backend + wiring, no custom creation yet) — ✅ DONE

*(Checkboxes below were left as written; as built, the `/api/data` shim was dropped rather than kept, and
the dashboard also offers "Restore AI Engineer Roadmap" via `POST /api/roadmaps { source }`.)*

**Goal:** Users see a Roadmap Dashboard after login. They can open the AI Engineer Roadmap,
which works exactly as before. They can delete roadmaps (with confirmation). No custom creation yet.

**Backend:**
- [ ] `server/db.js` — add `roadmaps` + `roadmap_progress` tables; migration statements; seed on register
- [ ] `server/routes/roadmaps.js` — `GET /`, `DELETE /:id`, `GET /:id/progress`, `PUT /:id/progress`
- [ ] `server/app.js` — mount new router; keep `/api/data` shim alive
- [ ] `server/routes/auth.js` — seed roadmap row on register

**Frontend:**
- [ ] `js/api.js` — add `RoadmapApi` namespace
- [ ] `index.html` — add `#dashboardScreen` HTML skeleton + "back" button in app header
- [ ] `js/app.js`:
  - `showRoadmapDashboard()`, `renderDashboard()`, `openRoadmap()`, `loadRoadmapData()`
  - `confirmDeleteRoadmap()` modal
  - `backToDashboard()` + save flush
  - `DATA` becomes `let`; set in `loadRoadmapData()`
  - Update `doSave()` to use `RoadmapApi.putProgress()`
  - Boot flow: `showRoadmapDashboard()` instead of `loadUserData()` directly
- [ ] `css/styles.css` — dashboard screen, roadmap cards

**Tests:**
- [ ] `test/roadmaps.test.js` — CRUD, progress CAS, auth isolation, cascade delete

---

### Phase 2 — Custom Roadmap Creation — ✅ DONE (as built, not as originally planned)

**Original goal:** Users can create a custom roadmap through a form/wizard. It is loadable and functions
like the AI Engineer Roadmap.

**Original task list — superseded, not built:**

- ~~`js/roadmap-definition-schema.js` — `validateRoadmapDefinition()`~~
- ~~`js/roadmap-builder.js` — creation form UI~~
- ~~`index.html` — add `<script src="js/roadmap-definition-schema.js">` and `roadmap-builder.js`~~
- ~~`js/app.js` — wire "New Roadmap" button to `RoadmapBuilder.open()`; `DATA = progressRes.definition`~~
- ~~CSS — roadmap builder modal styles~~

#### Phase 2 — as built

A custom roadmap = `BLANK_DATA` (no phases, counters, skills checklist or reference) + the user's
`progress.custom`, edited with the existing Month → Section (week or theme) → Topic → Tasks editors.

**Backend**
- [x] `server/roadmaps/repository.js` — `createRoadmapRepository(db)`: all roadmap/progress SQL moved out of the router
- [x] `server/roadmaps/validators.js` — `validateRoadmapInput` (name 1–80 single line, description ≤ 300, optional `YYYY-MM` start month), `CUSTOM_SOURCE`, `MAX_ROADMAPS_PER_USER` = 20
- [x] `server/roadmaps/progress.js` — `emptyProgress(startMonth)`
- [x] `server/routes/roadmaps.js` — HTTP-only; `POST /` now has two modes: create custom (`source` omitted/`"custom"`; 201, 400, 409 at the cap) and restore built-in (`source: "builtin_ai_engineer"`; 201/409); unknown `source` → 400. A start month seeds a `roadmap_progress` row at version 1 in the same transaction
- [x] No schema change, no migration

**Frontend**
- [x] `js/api.js` — `RoadmapApi.create(body)`
- [x] `js/app.js` — `BUILTIN_DATA` / `BLANK_DATA` and `let DATA` set in `openRoadmap` by `source`; create dialog (`openCreateRoadmapModal`, `submitCreateRoadmap`); `resetViewState()`, `syncTabs()` (hides Skills Checklist and Reference), `renderBlankRoadmap()` onboarding card; empty-state handling in Timeline/Kanban/Checklist; Kanban no longer assumes `DATA.phases[0]`; `horizonEnd()` clamps to ≥ 1 month; start-month dialog wording adapts to custom roadmaps
- [x] `css/styles.css` — month input styling, blank-roadmap card

**Tests**
- [x] `test/roadmaps.test.js` — "custom roadmaps" block (create, start-month seeding, per-roadmap content isolation, validation, markup stored verbatim, 20-roadmap cap, cross-user access, delete); 59 tests total

**Docs**
- [x] README, `documentation/*.md` (incl. `multi-roadmap.md`) and `.claude/PROJECT_WALKTHROUGH.md` updated

---

### Phase 3 — Polish & "Create with AI" Placeholder

- [ ] "Create with AI" button — shows a modal: "This feature is coming soon. You'll be able to
  describe your learning goal and have an AI generate a structured roadmap for you."
- [ ] Roadmap card progress bar (requires fetching all progress on dashboard — consider lazy loading
  or a lightweight stats endpoint)
- [ ] Edit roadmap name/description
- [ ] Export/import roadmap definition (share a roadmap template)

---

## 10. Key Challenges & Risks

### 10.1 `DATA` is currently a module-level `const`
**Risk:** `app.js` captures `const DATA = window.ROADMAP_DATA` once. Every function uses it.
Changing to a dynamic `let DATA` requires verifying all 30+ references to `DATA` update correctly
when a new roadmap is opened. Missing references silently show stale data.

**Mitigation:** Change to `let DATA = null;` and add an assertion at top of `rebuildIndex()` that
throws if `DATA` is null. This surfaces any missed initialization quickly.

### 10.2 `app.js` is already 1961 lines
**Risk:** Adding the dashboard screen, roadmap cards, delete confirmation, and builder wiring into
the same file pushes it past 2500+ lines. Harder to maintain.

**Mitigation:** Split roadmap creation into `js/roadmap-builder.js`. Keep the dashboard render
logic in `app.js` but it stays lean (card rendering is HTML templating). Do not split `app.js`
itself — that would require a build step or significant refactor.

### 10.3 Migration of existing `user_data`
**Risk:** The migration SQL runs every boot. If it partially fails, users lose data.

**Mitigation:** The migration is INSERT-based and idempotent (uses `NOT EXISTS` guards). Run it
inside a try/catch — if it fails, log and continue (the old `user_data` table still exists as
fallback). Only drop `user_data` after migration is confirmed over a period.

### 10.4 Session expiry while on Dashboard
**Risk:** User is on the Dashboard with no roadmap open. A 401 is returned on an API call.
`handleSessionExpired()` currently offers to "download unsaved changes" — but there are none
(no roadmap is open). The flow needs to handle the 401 gracefully from the dashboard context.

**Mitigation:** Check `session.roadmapId !== null` before offering the download option.

### 10.5 `mastery` and `reference` tabs on custom roadmaps
**Risk:** These views are specific to the AI Engineer roadmap's structure. Custom roadmaps won't
have depth annotations or reference sections. Showing empty/broken views degrades UX.

**Mitigation:**
- Hide `mastery` tab when `DATA.phases` has no topics with `depth` annotations.
- Hide `reference` tab when there are no reference-type sections.
- Add `hasDepthData()` and `hasReferenceSection()` predicates called during tab render.

### 10.6 ID collision between builtin and custom roadmaps
**Risk:** The AI Engineer roadmap uses string IDs like `"month-1-week-1-subtask-abc"`. A custom
roadmap using UUID-based IDs (`"ck-<uuid>"`) has no collision risk. But the ProgressStore is
scoped per roadmap — each `roadmap_progress` row is independent — so there is no cross-roadmap
collision in practice.

**Mitigation:** No special handling needed. Document that IDs are roadmap-scoped.

### 10.7 `progress.custom` semantics for custom roadmaps
**Risk:** `progress.custom.phases` and `progress.custom.topics` in ProgressStore currently let
users add extra content to the AI Engineer roadmap. For a fully user-defined custom roadmap, the
entire structure is in `roadmaps.definition`. Should `custom` still work for custom roadmaps?

**Decision:** Yes, keep it. It allows users to add extra topics/phases on top of any roadmap
(builtin or custom). No code changes needed — the existing `topicsOf()` / `buildCustomPhases()`
logic already merges `custom` on top of `DATA.phases`.

### 10.8 Deleting the builtin AI Engineer Roadmap
**Risk:** Users might delete the default roadmap and then have zero roadmaps, leaving them stuck.

**Decision:** Allow deleting it — do not special-case it. If all roadmaps are deleted, the
Dashboard shows an empty state with "Create your first roadmap" and a "Restore AI Engineer Roadmap"
option (calls `POST /api/roadmaps` with `source: 'builtin_ai_engineer'`).

### 10.9 Dashboard progress bar (requires extra fetches)
**Risk:** To show "42% complete" on each roadmap card, the dashboard would need to fetch progress
for every roadmap. With 10 roadmaps that's 10 round trips.

**Mitigation:** For Phase 1, skip the progress bar on cards — just show name/description/updated.
In Phase 3, add a `GET /api/roadmaps/:id/stats` endpoint that returns a lightweight
`{ total, completed }` without the full data blob.

---

## 11. File-by-File Change Summary

### New files
| File | Purpose |
|---|---|
| `server/routes/roadmaps.js` | Roadmap CRUD + progress endpoints |
| `js/roadmap-builder.js` | Custom roadmap creation form UI |
| `js/roadmap-definition-schema.js` | UMD validator for RoadmapDefinition JSON |
| `test/roadmaps.test.js` | Integration tests for new routes |

### Modified files
| File | Changes |
|---|---|
| `server/db.js` | Add `roadmaps` + `roadmap_progress` tables; migration statements |
| `server/app.js` | Mount `createRoadmapsRouter`; keep `/api/data` shim |
| `server/routes/auth.js` | Seed roadmap row in `POST /register` |
| `js/api.js` | Add `RoadmapApi` namespace; expose as `window.RoadmapApi` |
| `js/app.js` | `DATA` → `let`; boot → dashboard flow; new dashboard functions; update `doSave()`; tab visibility guards |
| `index.html` | Add `#dashboardScreen` HTML; back button in `<header>`; new `<script>` tags |
| `css/styles.css` | Dashboard screen, roadmap cards, coming-soon badge |

### Unchanged files
| File | Reason |
|---|---|
| `js/progress-schema.js` | ProgressStore shape unchanged |
| `server/auth/service.js` | Auth unchanged |
| `server/auth/validators.js` | Validators unchanged (may add roadmap name validation) |
| `server/config.js` | Config unchanged |
| `data/roadmap.md` + `roadmap.js` | AI Engineer content unchanged |
| `scripts/md_to_json.py` | Unchanged |

---

## 12. Open Design Questions

1. **Can users rename a roadmap after creation?**  
   Not in Phase 1. Add `PUT /api/roadmaps/:id` (name + description only) in Phase 3.

2. **Can users edit a custom roadmap's structure after creation (add/remove phases)?**  
   **Yes (resolved in Phase 2).** Because the structure lives in `progress.custom` and is edited with the
   existing add/delete editors for months, sections, topics and tasks, it is editable at any time; deleting
   an item also removes its saved progress, so nothing is orphaned. (Renaming or editing an existing item's
   title is not offered yet, and neither is renaming the roadmap itself — Phase 3.)

3. **Should roadmap cards show a progress percentage?**  
   No in Phase 1. Requires extra progress fetches. Add in Phase 3 with a stats endpoint.

4. **Should "Restore AI Engineer Roadmap" be available when zero roadmaps exist?**  
   Yes — add as empty-state CTA. Simple to implement: `POST /api/roadmaps` with known source.

5. **Export/import of a full roadmap (definition + progress)?**  
   Current export is ProgressStore only. For Phase 3, add a combined export format:
   `{ version: "1.0", definition: {...}, progress: {...} }`.
