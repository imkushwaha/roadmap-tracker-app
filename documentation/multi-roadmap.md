# Multi-Roadmap Tracker — Feature Guide

The app started as a single "AI Engineer Roadmap" tracker. It is now a **roadmap tracker**: each account owns a list of roadmaps — the built-in AI Engineer one plus any number of its own (up to 20) — each with its own independent progress. This guide covers the user flow, how it is built, how custom roadmaps work, and how existing data was migrated. Endpoint and table details live in `api-design.md` and `database-design.md`.

**Status:** Phase 1 (infrastructure + dashboard) and Phase 2 (custom roadmaps) are implemented. Phase 3 (polish, "Create with AI") is planned in `.claude/specs/generic-tracker-plan.md`.

---

## 1. User Flow

```
Login / register
      │
      ▼
Roadmap dashboard  ──── "Log out"
  • one card per roadmap (name, description, last activity)
  • Open · Delete (asks for confirmation)
  • "Create new roadmap" card  → dialog: name, description, start month
  • "Restore AI Engineer Roadmap" card when the account no longer has it
  • "Create roadmap with AI" — shown, disabled, "Coming soon"
      │ Open / Create
      ▼
Roadmap views (Overview · Timeline · Kanban · Checklist · This Week · Skills · Reference)
  • header shows the roadmap's name and description
  • "←" button returns to the dashboard (unsaved edits are flushed first)
  • Skills and Reference tabs appear only for the AI Engineer roadmap
```

- Every new account is seeded with the **AI Engineer Roadmap**.
- **Create** makes an empty custom roadmap and opens it straight away (section 3).
- **Delete** removes the roadmap and its progress permanently. The confirmation modal names the roadmap and warns it cannot be undone.
- **Restore** re-creates the AI Engineer roadmap with fresh progress. It is refused (409) if the account already has one.

---

## 2. Data Model

| Table | Purpose |
|---|---|
| `roadmaps` | One row per roadmap per user: `name`, `description`, `source`, `created_at`. |
| `roadmap_progress` | At most one row per roadmap: the progress JSON blob, `version`, `updated_at`. |

`source = 'builtin_ai_engineer'` marks the starter roadmap. Its curriculum is the static `data/roadmap.js` bundle, so only metadata is stored per user. The name and description are defined once in `server/roadmaps/builtin.js`.

`source = 'custom'` marks a user-built roadmap. It has **no stored curriculum or definition column** — see the next section.

The progress blob is unchanged (`items`, `counters`, `celebratedPhases`, `settings`, `custom`) and is still validated by `js/progress-schema.js` on every write.

---

## 3. Custom Roadmaps

### How they work

A custom roadmap is an **empty curriculum** (`BLANK_DATA` in `js/app.js`: no phases, counters, skills checklist or reference) whose entire structure lives in its progress blob, under `progress.custom`:

```
Month   (custom.phases[])          — title, objective
 └─ Section (phases[].sections[])  — a week (1–4) or a theme (no dates)
     └─ Topic (custom.topics[])    — title, optional depth
         └─ Tasks (topics[].tasks[]) — the checkable steps
```

The user builds it **inside the roadmap** with the editors the app already had for adding to the AI Engineer roadmap: "Add month", "Add section to this month", "Add topic", "＋ task", and the matching delete buttons. Everything the AI Engineer roadmap offers on top of that — status, notes, links, due dates, Overview / Timeline / Kanban / Checklist / This Week, autosave, export/import — works unchanged, because those features only read the combined curriculum + `progress.custom` index.

### Creating one

The create dialog collects:

| Field | Rule |
|---|---|
| Name | Required, 1–80 characters, single line |
| Description | Optional, up to 300 characters; shown as the subtitle |
| Month 1 starts in | `YYYY-MM`; defaults to the current month and cannot be earlier |

`POST /api/roadmaps` validates the same rules on the server. When a start month is given it is saved at creation as version 1 of an empty progress blob (`settings.startMonth`), in the same transaction as the roadmap; otherwise Month 1 defaults to the current month. The start month can be changed later from the profile menu ("Set start month…").

### What the user sees

- **Empty roadmap:** Overview shows an onboarding card ("Let's build your roadmap") that explains Month → Section → Topic → Tasks and offers "Add your first month". Timeline shows a "No months yet" hint; Kanban and Checklist show empty-state messages until there are tasks.
- **Tabs:** Skills Checklist and Reference are hidden (they need a curriculum that provides that content); the "Interview & career counters" block is omitted when there are no counters.
- **Isolation:** switching roadmaps resets the Kanban month, Checklist filters and expanded months/sections, so nothing from one roadmap leaks into the next. Custom content in one roadmap never appears in another.

### Design decision — why there is no separate builder

The first plan (`.claude/specs/generic-tracker-plan.md`) proposed an up-front roadmap builder and a `roadmaps.definition` column holding the structure. **That was not built.** The app already had complete add/delete editing for months, sections, topics and tasks, stored in `progress.custom`. Starting a custom roadmap empty and reusing that gives:

- the proven UI and storage, with nothing new to maintain;
- editing after creation for free (a stored definition would have needed its own editing UI and a plan for progress keys orphaned by changes);
- no schema change, so existing databases and the migration are unaffected;
- plan and progress saved, versioned and conflict-resolved together.

Options left for a later phase if wanted: a creation wizard that pre-fills `progress.custom` with months/sections/topics, ready-made roadmap templates, or a stored definition (which would be a new column added by migration).

---

## 4. Backend

- **`server/routes/roadmaps.js`** — router mounted at `/api/roadmaps`, **HTTP-only**: it parses ids and bodies, validates, chooses status codes and delegates all SQL. `requireAuth` is applied to the whole router. Every query includes `user_id`, so ids belonging to other accounts return `404`, the same as unknown ids.
- **`server/roadmaps/repository.js`** — `createRoadmapRepository(db)`: list, ownership lookup, count, insert, delete, get/save progress. Moving the SQL here (out of the router) follows the project rule that DB access lives in `db.js` or repository modules.
- **`server/roadmaps/validators.js`** — `validateRoadmapInput` and the limits (`NAME_MAX` 80, `DESCRIPTION_MAX` 300, `MAX_ROADMAPS_PER_USER` 20, `CUSTOM_SOURCE`).
- **`server/roadmaps/progress.js`** — `emptyProgress(startMonth)`.
- **Saving progress** — same optimistic concurrency as before: a single atomic compare-and-swap on `version` (`INSERT … ON CONFLICT DO NOTHING` for `version: 0`, otherwise `UPDATE … WHERE version = ?`). A stale version returns `409` with the server copy.
- **Registration** — `routes/auth.js` inserts the user and the starter roadmap in one `db.batch` transaction, so an account never exists without a roadmap and a rejected duplicate username leaves no orphan.
- **Creating roadmaps** — `POST /api/roadmaps` has two modes: create a custom roadmap (`source` omitted or `"custom"`; 400 invalid, 409 at the 20-roadmap cap) or restore the built-in one (`source: "builtin_ai_engineer"`; 409 if it exists). Any other `source` is a 400.

---

## 5. Frontend

| Piece | Where |
|---|---|
| API client | `js/api.js` — `AuthApi` and `RoadmapApi` (`list`, `create`, `restoreBuiltin`, `remove`, `getProgress`, `putProgress`) |
| Dashboard markup | `index.html` — `#dashboardScreen`; the create dialog is rendered into the shared `#modalHost` |
| Flow | `js/app.js` — `boot` → `enterDashboard` → `showDashboard` / `renderDashboard` → (`openCreateRoadmapModal` → `submitCreateRoadmap`) → `openRoadmap` → `backToDashboard` |
| Per-roadmap curriculum | `BUILTIN_DATA`, `BLANK_DATA`, and `let DATA` switched in `openRoadmap` by `source` |
| Per-roadmap UI state | `resetViewState()` and `syncTabs()`; `renderBlankRoadmap()` for the empty onboarding card |
| Styles | `css/styles.css` — "Roadmap dashboard" and "Custom roadmaps" sections |

Session state: `session.roadmapId` is `null` on the dashboard and the open roadmap's id otherwise. Autosave only runs while a roadmap is open. `settleUnsavedChanges` is shared by "back to dashboard" and "log out": it flushes pending edits and asks before discarding anything that could not be saved.

Z-order: roadmap app (50) < dashboard (350) < modal (400) < toasts (450) < auth screen (500).

---

## 6. Migration from the Single-Roadmap Schema

On startup `openDb` runs `migrateLegacyUserData`:

1. If a `user_data` table exists, one transaction gives every account without a roadmap the AI Engineer roadmap row, copies each `user_data` row into `roadmap_progress` (data, version, updated_at preserved), and renames `user_data` to `user_data_legacy`.
2. On later boots `user_data` no longer exists, so nothing runs. A roadmap the user deleted is **never re-seeded**.

The legacy table is renamed rather than dropped so the original data stays recoverable. Drop it manually once the new schema has been verified in production.

**Rollout note:** an older server instance still running against the same database will fail once `user_data` is renamed. Switch all instances over together. Phase 2 itself needs no schema change or migration.

---

## 7. Tests

`test/roadmaps.test.js` covers seeding, list/progress responses, authentication, cross-user isolation, malformed ids, delete (including progress removal), restore rules, atomic registration, the migration (including no re-seed after delete), and — for custom roadmaps — creation, start-month seeding (version 1), input validation, markup in names stored verbatim, the 20-roadmap cap, cross-user access and delete. `test/api.test.js` exercises the shared auth and progress behaviour through the per-roadmap endpoints. The whole suite has 59 tests.

---

## 8. Known Limits

- Roadmap name and description cannot be edited after creation.
- Dashboard cards do not show a completion percentage (it would need every roadmap's progress; planned as a lightweight stats endpoint). "Last activity" is the last progress save, and for a roadmap created with a start month that includes its creation.
- The UI labels the middle levels **Section** and **Topic**, not "module" / "sub-module".
- Topic depth choices (D1–D3) are the AI Engineer roadmap's vocabulary; they are optional.
- A custom roadmap has no Skills Checklist, Reference or counters.
- "Create with AI" is a disabled *Coming soon* placeholder.
- A creation wizard, templates and sharing/exporting a roadmap's structure are not built.
