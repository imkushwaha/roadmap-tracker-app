# Multi-Roadmap Tracker — Feature Guide

The app started as a single "AI Engineer Roadmap" tracker. It is now a **roadmap tracker**: each account owns a list of roadmaps, each with its own independent progress. This guide covers the user flow, how it is built, and how existing data was migrated. Endpoint and table details live in `api-design.md` and `database-design.md`.

**Status:** Phase 1 (infrastructure + dashboard) is implemented. Phase 2 (custom roadmap builder) and Phase 3 (polish) are planned in `.claude/specs/generic-tracker-plan.md`.

---

## 1. User Flow

```
Login / register
      │
      ▼
Roadmap dashboard  ──── "Log out"
  • one card per roadmap (name, description, last activity)
  • Open · Delete (asks for confirmation)
  • "Restore AI Engineer Roadmap" card when the account no longer has it
  • "Create new roadmap" and "Create roadmap with AI" — shown, disabled, "Coming soon"
      │ Open
      ▼
Roadmap views (Overview · Timeline · Kanban · Checklist · This Week · Skills · Reference)
  • header shows the roadmap's name and description
  • "←" button returns to the dashboard (unsaved edits are flushed first)
```

- Every new account is seeded with the **AI Engineer Roadmap**.
- **Delete** removes the roadmap and its progress permanently. The confirmation modal names the roadmap and warns it cannot be undone.
- **Restore** re-creates the AI Engineer roadmap with fresh progress. It is refused (409) if the account already has one.

---

## 2. Data Model

| Table | Purpose |
|---|---|
| `roadmaps` | One row per roadmap per user: `name`, `description`, `source`, `created_at`. |
| `roadmap_progress` | At most one row per roadmap: the progress JSON blob, `version`, `updated_at`. |

`source = 'builtin_ai_engineer'` marks the starter roadmap. Its curriculum is the static `data/roadmap.js` bundle, so only metadata is stored per user. The name and description are defined once in `server/roadmaps/builtin.js`.

The progress blob is unchanged (`items`, `counters`, `celebratedPhases`, `settings`, `custom`) and is still validated by `js/progress-schema.js` on every write.

---

## 3. Backend

- **`server/routes/roadmaps.js`** — router mounted at `/api/roadmaps`. `requireAuth` is applied to the whole router. Every query includes `user_id`, so ids belonging to other accounts return `404`, the same as unknown ids.
- **Saving progress** — same optimistic concurrency as before: a single atomic compare-and-swap on `version` (`INSERT … ON CONFLICT DO NOTHING` for `version: 0`, otherwise `UPDATE … WHERE version = ?`). A stale version returns `409` with the server copy.
- **Registration** — `routes/auth.js` inserts the user and the starter roadmap in one `db.batch` transaction, so an account never exists without a roadmap and a rejected duplicate username leaves no orphan.
- **Creating roadmaps** — `POST /api/roadmaps` currently only accepts `{ "source": "builtin_ai_engineer" }` (restore). Phase 2 extends it to custom definitions.

---

## 4. Frontend

| Piece | Where |
|---|---|
| API client | `js/api.js` — `AuthApi` and `RoadmapApi` (`list`, `restoreBuiltin`, `remove`, `getProgress`, `putProgress`) |
| Dashboard markup | `index.html` — `#dashboardScreen` |
| Flow | `js/app.js` — `boot` → `enterDashboard` → `showDashboard` / `renderDashboard` → `openRoadmap` → `backToDashboard` |
| Styles | `css/styles.css` — "Roadmap dashboard" section |

Session state: `session.roadmapId` is `null` on the dashboard and the open roadmap's id otherwise. Autosave only runs while a roadmap is open. `settleUnsavedChanges` is shared by "back to dashboard" and "log out": it flushes pending edits and asks before discarding anything that could not be saved.

Z-order: roadmap app (50) < dashboard (350) < modal (400) < toasts (450) < auth screen (500).

---

## 5. Migration from the Single-Roadmap Schema

On startup `openDb` runs `migrateLegacyUserData`:

1. If a `user_data` table exists, one transaction gives every account without a roadmap the AI Engineer roadmap row, copies each `user_data` row into `roadmap_progress` (data, version, updated_at preserved), and renames `user_data` to `user_data_legacy`.
2. On later boots `user_data` no longer exists, so nothing runs. A roadmap the user deleted is **never re-seeded**.

The legacy table is renamed rather than dropped so the original data stays recoverable. Drop it manually once the new schema has been verified in production.

**Rollout note:** an older server instance still running against the same database will fail once `user_data` is renamed. Switch all instances over together.

---

## 6. Tests

`test/roadmaps.test.js` covers seeding, list/progress responses, authentication, cross-user isolation, malformed ids, delete (including progress removal), restore rules, atomic registration, and the migration (including no re-seed after delete). `test/api.test.js` exercises the shared auth and progress behaviour through the per-roadmap endpoints.

---

## 7. Known Limits (Phase 1)

- Only the AI Engineer roadmap exists; custom creation arrives in Phase 2.
- Dashboard cards do not show a completion percentage (it would need every roadmap's progress; planned as a lightweight stats endpoint).
- Roadmaps cannot be renamed.
- `data/roadmap.js` and `DATA` in `app.js` are still the single static bundle; Phase 2 makes `DATA` per-roadmap.
