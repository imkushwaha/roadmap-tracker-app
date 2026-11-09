# Settings Split — Account Menu vs Roadmap Settings

**Date:** 2026-11-04
**Status:** Superseded by ui-redesign-spec.md (Phase 2)
**Scope:** Front end only (`index.html`, `js/app.js`, `css/styles.css`) plus docs. No API, database or server change.

---

## 1. Problem

One profile dropdown serves two different jobs. It only exists inside a roadmap, so account-level things (theme, log out, who you are) are missing on the homepage, and roadmap-level things (start month, export, reset) sit in a menu that reads like account settings.

Today the dropdown (`#profilePanel`, in `<header class="app-header">`) holds: name and @username, save status, search, theme, start month, export, import, import old browser data, reset progress, log out. The homepage has only a bare "Log out" button.

## 2. Decisions

| Item | Today | Goes to | Why |
|---|---|---|---|
| Name and @username | roadmap profile menu | **Account menu** (homepage and roadmap) | Who you are is not roadmap-specific |
| Theme (light/dark) | roadmap profile menu | **Account menu** | One preference for the whole app; stored per browser in `localStorage` already |
| Log out | profile menu + homepage button | **Account menu** (homepage button removed) | One place, reachable everywhere |
| Start month | profile menu | **Roadmap settings** | Stored in that roadmap's progress (`settings.startMonth`) |
| Export / Import progress | profile menu | **Roadmap settings** | They read and write one roadmap's progress |
| Reset progress | profile menu | **Roadmap settings** (danger zone, last) | Clears one roadmap |
| Import old browser data | profile menu (shown for any roadmap) | **Roadmap settings, AI Engineer roadmap only** | The legacy data was AI Engineer progress; it should not be offered into a custom roadmap |
| Save status | hidden inside the profile menu | **Visible indicator in the roadmap header** | Users should see "Saving…/Saved/Conflict" without opening a menu; clicking still retries or resolves |
| Search | hidden inside the profile menu | **Search box in the tab bar** (roadmap only) | It is used constantly and only filters the open roadmap |

**Homepage** shows only the account menu (name, @username, theme, log out). Nothing else belongs there yet.

**Roadmap window** shows the account menu **and** a separate "⚙ Roadmap" settings menu. Keeping the account menu inside a roadmap means you can still switch theme or log out without going back.

Deferred (need backend work or a product decision): edit name, change password, delete account, default start month for new roadmaps, theme saved to the account instead of the browser, and rename/delete a roadmap from inside its settings (Phase 3 items).

## 3. Target layout

```
Homepage                                   Roadmap window
┌──────────────────────────────────┐      ┌────────────────────────────────────────────────┐
│ 🧭 Roadmap Tracker   [👤 Ada ▾]  │      │ ← 🧭 Learn Rust   ● Saved   [⚙ Roadmap ▾] [👤 Ada ▾] │
├──────────────────────────────────┤      │ Overview Timeline Kanban …          [🔍 Search…]    │
│ Your roadmaps  (cards)           │      └────────────────────────────────────────────────┘
└──────────────────────────────────┘
Account menu:   Ada Lovelace · @ada · Theme [Light|Dark] · Log out
Roadmap menu:   <roadmap name> · 📅 Start month… · ⬇ Export · ⬆ Import · 🗂 Import old browser data* · ⟲ Reset progress…   (*AI Engineer only, only if legacy data exists)
```

## 4. Implementation

### 4.1 `index.html`
- Split `#profilePanel` into two menus: the account menu (name, username, theme, log out) and a new roadmap menu (`#roadmapMenuTrigger` / `#roadmapMenuPanel`) holding the five roadmap actions.
- Move `#panelSaveStatus` out of the menu into the roadmap header as a standalone chip.
- Move the search input out of the menu into the tab bar row (`#roadmapSearch`).
- Remove `#dashboardLogoutBtn`; the homepage bar gets the account menu instead. Drop the redundant "Signed in as …" greeting.
- Keep the existing element IDs for everything that stays (`themeLightBtn`, `exportBtn`, `importFile`, …) so the handlers keep working.

### 4.2 One account menu, two homes
Build the account menu once and **re-parent** the single `#profileAnchor` node into the active header (homepage bar or roadmap header) when the screen changes. This avoids duplicate IDs and double event listeners. Add `mountAccountMenu(hostEl)` called from `showDashboard()` and `openRoadmap()`.

### 4.3 `js/app.js`
- Generalise menu handling: a small `createMenu(triggerEl, panelEl)` helper used by both menus. Only one menu open at a time; outside click and **Escape** close it; Escape returns focus to the trigger.
- Roadmap menu actions reuse the existing handlers (`openStartMonthModal`, `exportProgress`, `importProgress`, `confirmReset`, `openLegacyModal`). No logic change.
- `legacyImportBtn` visibility: `readLegacyLocalData() && session.roadmapSource === "builtin_ai_engineer"`. Store `roadmapSource` on the session in `openRoadmap`.
- Search: wire `#roadmapSearch` to `state.search` as today; reset it in `openRoadmap` (already done for the old input).
- The roadmap menu header shows the roadmap name so it is clear which roadmap the actions apply to.
- `setSaveStatus` keeps working (same element, new location); its click handler is unchanged.

### 4.4 `css/styles.css`
- New styles for the roadmap header actions, the save-status chip, and the tab-bar search. Reuse the existing `.profile-panel*` / `.profile-action-btn` styles for the roadmap menu.
- Narrow screens: the tab bar already scrolls; let the search box wrap onto its own row under 640px and collapse the roadmap trigger to the "⚙" icon.
- Menus must sit above the homepage content (`z-index` stays under modals at 400, above the sticky bars).

## 5. Edge cases to handle
- Opening a roadmap while the account menu is open (and vice versa): close both on screen change.
- Session expiry while the roadmap menu is open: `handleSessionExpired` closes menus.
- Theme buttons keep their active state when the menu is re-parented (state is read from `data-theme`, not the DOM position).
- The login screen's "Download my unsaved changes" link still uses `exportProgress`; unaffected.
- Keyboard: both triggers keep `aria-haspopup` / `aria-expanded`; menus close on Escape.

## 6. Verification
- Server tests are unaffected (no backend change); `npm test` must stay at 58 passing.
- Re-run the jsdom end-to-end smoke test (it lives in the session scratchpad, not the repo) extended with: account menu present on the homepage and in a roadmap; roadmap menu only in a roadmap; "Import old browser data" absent in a custom roadmap; search filters the checklist; save chip updates after an edit; Escape closes a menu; logout works from the homepage menu.
- Visual check is on you: layout, spacing, dark mode and mobile width. I cannot render the page.

## 7. Docs to update (project rule)
`README.md` (features), `documentation/low-level-design.md` (frontend section), `documentation/multi-roadmap.md` (user flow), `.claude/PROJECT_WALKTHROUGH.md`. No API or database docs change.

## 8. Effort and risk
Small to medium: about one focused session. Main risk is regressions from moving elements that other code looks up by ID (`panelSearch`, `panelSaveStatus`, `profileName`); mitigated by keeping IDs where possible and grepping every `$("…")` and `getElementById` use before moving anything.

## 9. Open questions (defaults in bold)
1. Keep the account menu inside a roadmap too? **Yes.** The alternative is homepage-only, which forces a trip back to log out or change theme.
2. Search as a visible box in the tab bar? **Yes.** The alternative is keeping it inside the roadmap menu, which hides a frequently used control.
3. Theme stays per browser? **Yes.** Saving it to the account needs a backend column and API.
