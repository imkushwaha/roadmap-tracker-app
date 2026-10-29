# Profile Section — Implementation Spec

**Branch:** `feature/profile-section`  
**Status:** Draft  
**Date:** 2026-10-28

---

## Overview

Consolidate all user-account controls (currently scattered across the top header) into a single **profile panel** anchored to the **top-right** of the application. The main header is stripped down to just the app brand and tab navigation.

---

## Current State

All controls live in `.header-actions` (right side of `.header-inner`):

| Element | ID | Purpose |
|---|---|---|
| Save status indicator | `#saveStatus` | Shows saving / saved / error state |
| User chip | `#userChip` | Displays 👤 + username |
| Logout button | `#logoutBtn` | Ends session |
| Search toggle | `#searchToggle` | Shows/hides search bar |
| Theme toggle | `#themeToggle` | Cycles 🌙/☀️ icon |
| Three-dot menu trigger | `#dataMenuToggle` | Opens dropdown |
| Three-dot dropdown | `#dataMenu` | Set Start Month, Export/Import JSON, Reset Progress |

---

## Target State

### Layout

```
┌─────────────────────────────────────────────────────────┐
│   Roadmap Dashboard                  [👤 Username ▾]    │
│   brand (left)                        ↑ profile trigger │
├─────────────────────────────────────────────────────────┤
│  [Overview] [Timeline] [Kanban] [Checklist] … (tabs)    │
└─────────────────────────────────────────────────────────┘
```

When the profile trigger is clicked, a panel drops down from it (top-right):

```
┌──────────────────────┐
│ 👤 username          │
│ ● Saved              │  ← save status (read-only text, updates dynamically)
├──────────────────────┤
│ 🔎  Search           │  ← inline search input (visible inside panel)
├──────────────────────┤
│ Theme                │
│ [Light]  [Dark]      │  ← two text buttons, active one is highlighted
├──────────────────────┤
│ 📅 Set start month…  │
│ ⬇ Export progress    │
│ ⬆ Import progress    │
│ ⟲ Reset progress…    │
├──────────────────────┤
│ Log out              │
└──────────────────────┘
```

- The panel is a positioned dropdown (absolute, z-index above header) that closes on outside click.
- The existing collapsible `#searchBar` under the header is **removed**; search moves inside the panel.
- The existing `#dataMenu` dropdown is **removed**; its items are absorbed into the profile panel.
- The existing `#themeToggle` icon button is **removed**; replaced by text buttons inside the panel.

---

## HTML Changes (`index.html`)

### Remove from `.header-actions`

Remove all of:
- `#saveStatus`
- `#userChip`
- `#logoutBtn`
- `#searchToggle`
- `#themeToggle`
- `#dataMenuToggle`
- `#dataMenu` (entire dropdown div including children)

### Remove from header

Remove:
- `#searchBar` div (the collapsible search bar below `.header-inner`)

### Add to `.header-inner` — before `.brand`

```html
<div class="profile-anchor" id="profileAnchor">
  <button class="profile-trigger" id="profileTrigger" aria-haspopup="true" aria-expanded="false">
    <span class="profile-trigger-avatar">👤</span>
    <span class="profile-trigger-name" id="profileName">—</span>
    <span class="profile-trigger-caret">▾</span>
  </button>

  <div class="profile-panel hidden" id="profilePanel" role="menu">

    <!-- Identity + save status -->
    <div class="profile-panel-header">
      <span class="profile-panel-username" id="panelUsername">—</span>
      <span class="profile-panel-save" id="panelSaveStatus">Saved</span>
    </div>

    <div class="profile-panel-sep"></div>

    <!-- Search -->
    <div class="profile-panel-section">
      <label class="profile-panel-label" for="panelSearch">Search</label>
      <input type="search" id="panelSearch" class="profile-panel-search" placeholder="Search topics…" autocomplete="off" />
    </div>

    <div class="profile-panel-sep"></div>

    <!-- Theme -->
    <div class="profile-panel-section profile-panel-theme">
      <span class="profile-panel-label">Theme</span>
      <div class="profile-theme-btns">
        <button class="profile-theme-btn" id="themeLightBtn" data-theme="light">Light</button>
        <button class="profile-theme-btn" id="themeDarkBtn" data-theme="dark">Dark</button>
      </div>
    </div>

    <div class="profile-panel-sep"></div>

    <!-- Data actions (formerly three-dot menu) -->
    <div class="profile-panel-section profile-panel-actions">
      <button class="profile-action-btn" id="startMonthBtn">📅 Set start month…</button>
      <button class="profile-action-btn" id="exportBtn">⬇ Export progress (JSON)</button>
      <button class="profile-action-btn" id="importBtn">⬆ Import progress (JSON)</button>
      <input type="file" id="importFile" accept=".json" class="hidden" />
      <button id="legacyImportBtn" class="profile-action-btn hidden">⬆ Import legacy data</button>
      <button class="profile-action-btn danger" id="resetBtn">⟲ Reset progress…</button>
    </div>

    <div class="profile-panel-sep"></div>

    <!-- Logout -->
    <div class="profile-panel-section">
      <button class="profile-action-btn profile-logout" id="logoutBtn">Log out</button>
    </div>

  </div>
</div>
```

> **Note:** `id` values for `startMonthBtn`, `exportBtn`, `importBtn`, `importFile`, `legacyImportBtn`, `resetBtn`, `logoutBtn` are **kept identical** so JS event bindings in `app.js` require no change.

---

## CSS Changes (`css/styles.css`)

### Remove

- `.icon-btn` styles that were exclusively for `#searchToggle`, `#themeToggle`, `#dataMenuToggle` (keep the class if it's shared elsewhere, otherwise remove).
- `.user-chip` styles.
- `.btn-sm` styles (logout button style — replaced by profile panel style).
- `.search-bar` styles (the full collapsible search bar).
- `.dropdown-menu` styles (the three-dot dropdown).
- `.dropdown-sep` styles.

### Add

```css
/* ── Profile Anchor ─────────────────────────────────────── */
.profile-anchor {
  position: relative;
  flex-shrink: 0;
}

.profile-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-1);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.profile-trigger:hover {
  background: var(--surface-3);
}
.profile-trigger[aria-expanded="true"] {
  background: var(--surface-3);
}
.profile-trigger-caret {
  font-size: 0.7rem;
  opacity: 0.6;
}

/* ── Profile Panel ──────────────────────────────────────── */
.profile-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 240px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  z-index: 200;
  padding: 4px 0;
  display: flex;
  flex-direction: column;
}
.profile-panel.hidden {
  display: none;
}

.profile-panel-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 16px 10px;
}
.profile-panel-username {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-1);
}
.profile-panel-save {
  font-size: 0.75rem;
  color: var(--text-2);
}
/* Mirror existing save-status states via class */
.profile-panel-save.saving { color: var(--accent); }
.profile-panel-save.saved  { color: var(--success, #22c55e); }
.profile-panel-save.error  { color: var(--danger, #ef4444); }

.profile-panel-sep {
  height: 1px;
  background: var(--border);
  margin: 2px 0;
}

.profile-panel-section {
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.profile-panel-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-2);
}

/* Search input inside panel */
.profile-panel-search {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 0.875rem;
  box-sizing: border-box;
}
.profile-panel-search:focus {
  outline: none;
  border-color: var(--accent);
}

/* Theme buttons */
.profile-theme-btns {
  display: flex;
  gap: 6px;
}
.profile-theme-btn {
  flex: 1;
  padding: 5px 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.profile-theme-btn:hover {
  background: var(--surface-3);
}
.profile-theme-btn.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

/* Action buttons (formerly three-dot items + logout) */
.profile-action-btn {
  width: 100%;
  text-align: left;
  padding: 7px 0;
  background: none;
  border: none;
  color: var(--text-1);
  font-size: 0.875rem;
  cursor: pointer;
  border-radius: 4px;
  transition: color 0.15s;
}
.profile-action-btn:hover {
  color: var(--accent);
}
.profile-action-btn.danger {
  color: var(--danger, #ef4444);
}
.profile-action-btn.danger:hover {
  color: var(--danger-dark, #b91c1c);
}
.profile-logout {
  font-weight: 500;
}
```

---

## JS Changes (`js/app.js`)

### 1. Remove / update old element bindings

**Lines 1424–1466 region (event wiring block in `init()`):**

- **Remove** `themeToggle` click handler (line 1424) → replaced by `#themeLightBtn` / `#themeDarkBtn`.
- **Remove** `searchToggle` click handler (lines 1429–1432) → search is now always visible inside the panel.
- **Remove** `searchClose` click handler (lines 1433–1438) → no longer needed.
- **Update** `searchInput` handler: change `$("searchInput")` reference to `$("panelSearch")`.
- **Remove** `dataMenuToggle` click (lines 1444–1450) → panel has its own toggle.
- **Keep** `exportBtn`, `importBtn`, `importFile`, `resetBtn`, `startMonthBtn`, `logoutBtn` handlers **unchanged** — IDs are preserved.

### 2. Add profile panel toggle logic

Insert after existing init wiring:

```js
// Profile panel open/close
const profileTrigger = $("profileTrigger");
const profilePanel   = $("profilePanel");

profileTrigger.addEventListener("click", (e) => {
  e.stopPropagation();
  const open = !profilePanel.classList.contains("hidden");
  profilePanel.classList.toggle("hidden", open);
  profileTrigger.setAttribute("aria-expanded", String(!open));
});

document.addEventListener("click", (e) => {
  if (!profilePanel.classList.contains("hidden") &&
      !$("profileAnchor").contains(e.target)) {
    profilePanel.classList.add("hidden");
    profileTrigger.setAttribute("aria-expanded", "false");
  }
});
```

### 3. Update theme toggle

Replace the single `themeToggle` click handler with:

```js
function applyTheme(dark) {
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  $("themeLightBtn").classList.toggle("active", !dark);
  $("themeDarkBtn").classList.toggle("active", dark);
  localStorage.setItem("theme", dark ? "dark" : "light");
}

$("themeLightBtn").addEventListener("click", () => applyTheme(false));
$("themeDarkBtn").addEventListener("click", () => applyTheme(true));
```

Wherever the existing theme-init code runs (e.g., reading `localStorage.getItem("theme")`), call `applyTheme(isDark)` to set the `.active` class on the correct button.

### 4. Update search wiring

Everywhere the code references `$("searchInput")` in the search handler, change the reference to `$("panelSearch")`. The search bar visibility toggle logic (`#searchBar.hidden`) is fully removed.

### 5. Update save-status display

The existing `saveStatus` button (which updated its own class + text) is removed. Replace any calls that touch `$("saveStatus")` to instead update `$("panelSaveStatus")`:

```js
// Old pattern:
// $("saveStatus").textContent = "Saved";
// $("saveStatus").className = "save-status saved";

// New pattern:
$("panelSaveStatus").textContent = "Saved";
$("panelSaveStatus").className = "profile-panel-save saved";
```

All four states — `saving`, `saved`, `error`, `conflict` — need equivalent class mappings defined in CSS (see CSS section above).

### 6. Update `loadUserData()` (lines ~1855–1857)

Replace the userChip/logoutBtn visibility logic:

```js
// Old:
$("userName").textContent = username;
$("userChip").title = "Signed in as " + username;
["userChip", "logoutBtn"].forEach((id) => $(id).classList.remove("hidden"));

// New:
$("profileName").textContent = username;
$("panelUsername").textContent = username;
// logoutBtn is always in the DOM (inside profile panel), no toggle needed
```

---

## Files Modified

| File | Change Summary |
|---|---|
| `index.html` | Remove header controls; add `.profile-anchor` + `.profile-panel` block before `.brand` |
| `css/styles.css` | Remove old control styles; add profile panel + theme button styles |
| `js/app.js` | Rewire search, theme, save-status, user-chip references; add panel toggle logic |

---

## Out of Scope

- No change to auth screen, tab navigation, view renderers, or backend.
- No new files needed; all changes are in the three existing files above.
- Responsive/mobile layout is not specified here; handle in a follow-up if needed.

---

## Acceptance Criteria

1. Header shows only brand + tab bar after profile trigger (no search bar, no icon buttons, no three-dot menu).
2. Profile trigger in top-right shows the logged-in username.
3. Clicking the trigger opens the profile panel; clicking outside closes it.
4. Save status text updates correctly for all four states inside the panel.
5. Search input inside the panel filters roadmap items in real-time (same behaviour as before).
6. "Light" and "Dark" text buttons switch theme; the active theme's button is visually highlighted.
7. Set Start Month, Export, Import, Reset all function identically to before.
8. Logout works identically to before.
9. No regressions in tab navigation, view rendering, or data sync.
