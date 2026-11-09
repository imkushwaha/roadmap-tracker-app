# Phase 0 — Foundations: Implementation Spec

> **Audience:** an AI coding agent (or developer) implementing this phase in the *Roadmap Tracker* repository.
> **Status of this spec:** every step below was executed on a pristine copy of the original repository and verified (59/59 tests, 61/61 UI checks). If you follow it exactly, you will get the same result.

| | |
|---|---|
| **Phase** | 0 of 5 — Foundations |
| **Depends on** | Nothing (first phase) |
| **Branch** | `feature/ui-redesign` created from `dev` |
| **Effort** | about 1.5 working days by hand; under an hour of agent time because every file is supplied |
| **Visible result** | The whole app re-skins (new colors, IBM Plex Sans font, logo, account-menu "Appearance" with Light / Dark / **System**). **No layout or behavior change.** |
| **Risk** | Low. CSS tokens keep their old names; JavaScript changes are small and isolated. |
| **Next phase** | Phase 1 — Log in / Create account screens (separate spec) |

---

## 0. Rules for the implementing agent (read first)

1. **Do exactly what this document says. Do not redesign.** Colors, sizes, names and copy are decided. If something seems wrong, finish the phase as written and report it in your hand-off notes.
2. **Do not add npm dependencies.** The project has no build step and must stay that way. (Fonts are copied files; the only package you install is a *temporary* one outside the repo to fetch them.)
3. **Do not change layout, markup structure, element IDs, API behavior, or database code.** Phase 0 is tokens, fonts, theme handling, icons, base components, and small accessibility fixes.
4. **Follow the repository's own rules** (`CLAUDE.md`): Airbnb-style JavaScript, `const` by default, escape all user-supplied text before it enters `innerHTML` (use the existing `esc()`), no tokens or personal data in `localStorage` (only the appearance preference is stored), parameterised SQL (no SQL is touched here), and **update the documentation in the same change** (Task 13).
5. **Content Security Policy is strict** (`helmet()` defaults): scripts only from `'self'`, **no inline `<script>`, no `eval`**. Anything new must be a same-origin file served by the static allowlist. This is *why* the theme script is an external file.
6. **Run the verification (Section 7) before declaring done.** A phase is not finished until every check passes.
7. **If a script in this spec fails an `assert`**, the repository has drifted from the version this spec was written against. Do not force it. Read the script's "Intent" list, apply the equivalent edit by hand, and note the difference in your hand-off.
8. **Commit in the order of the tasks** (one commit per task is ideal) so a reviewer can follow it.

---

## 1. Goal and scope

### 1.1 What this phase delivers

| # | Deliverable | Why |
|---|---|---|
| 1 | **Design tokens** in one file (`css/tokens.css`), light + dark, keeping the existing variable names | One source of truth; the whole app re-colors without touching every rule |
| 2 | **IBM Plex Sans**, self-hosted | Enterprise-grade, legible at 13–14px, no third-party requests (CSP-friendly, works offline) |
| 3 | **Base styles** (`css/base.css`): fonts, reset, focus ring, reduced-motion | Consistent keyboard focus; respects the OS "reduce motion" setting |
| 4 | **Component styles** (`css/components.css`): buttons, fields, progress bar, badges, status chips, modal, toasts, skeleton, avatar, mini button | Shared building blocks for Phases 1–5 |
| 5 | **Theme engine** (`js/theme-boot.js`): Light / Dark / **System**, applied before first paint | No white flash for dark users; System follows the OS live |
| 6 | **Icon set** (`js/icons.js`): inline SVG | Replaces emoji icons over later phases |
| 7 | **Logo + favicon** (`img/logo.svg`, `img/favicon.svg`) | Replaces the compass emoji |
| 8 | **Static allowlist** for `/fonts` and `/img` + tests | The server only serves allow-listed folders |
| 9 | **Accessibility fixes** found by an automated audit | Contrast, unnamed form controls, invalid ARIA roles, link-in-text |
| 10 | **Documentation** (`documentation/design-system.md` + edits) | Required by `CLAUDE.md` |

### 1.2 Out of scope (do NOT do these here)

- Any layout change: sidebar, top bar, split-screen login, new Home page (Phases 1–3).
- Replacing emoji in the UI other than the compass logo (the ⭐ in the login footer, ⚙, 👤, 📅 and others stay until the phase that owns each screen).
- Month Strip, `roadmap-stats`, `stats` API, hash routing (Phase 2).
- Restyling the seven roadmap views beyond what the tokens do automatically (Phase 4).
- Any change to `server/` other than the two static lines in Task 12.

### 1.3 Before and after (what a reviewer should see)

- **Before:** indigo `#4F46E5` accent, system font, emoji compass, "THEME" label with Light/Dark only, all-caps small labels, gradient progress bars, 16px rounded cards with soft shadows.
- **After:** blue `#2B50D8` accent (`#6C8CFF` in dark), IBM Plex Sans, SVG compass logo, "Appearance" with **Light / Dark / System**, sentence-case labels, solid green progress bars, 10px bordered containers (shadows only on floating layers). **Everything is in the same place.**

---

## 2. Preconditions

| Item | Requirement |
|---|---|
| Node | 22.x (`node -v`) |
| Install | `npm install` in the repo root |
| Git | Create `feature/ui-redesign` from `dev` |
| Baseline | `npm test` → **58 tests pass**. Record this; if it is not 58/58 before you start, stop and report |
| Optional but recommended | Python 3 + Playwright (`python3 -m pip install playwright && python3 -m playwright install chromium`) to run the UI verification harness in Section 7 |
| Starting point | The repository exactly as provided: `css/styles.css` (617 lines), `js/app.js` (about 2,380 lines), `index.html` with `#authScreen`, `#dashboardScreen`, `.app-header` |

**Repository facts you must respect**

- Plain static front end served by Express 5 (`server/app.js`). There is **no bundler**. Files are loaded by `<link>`/`<script>` tags in `index.html`.
- Static serving is an **explicit allowlist** in `server/app.js` (`_applyStaticRoutes`): `/`, `/css`, `/js`, `/data/roadmap.js`. Anything else returns 404. Task 12 adds `/fonts` and `/img`.
- `js/app.js` is one large IIFE that builds HTML with template strings and `innerHTML`; user text goes through `esc()`.

---

## 3. Design decisions (so you understand the "why")

### 3.1 Keep the existing CSS variable names

The old `styles.css` already defined `--bg`, `--bg-elevated`, `--bg-sunken`, `--border`, `--text`, `--text-muted`, `--text-faint`, `--accent`, `--accent-ink`, `--accent-soft`, `--status-*`, `--radius-*`. Changing only their **values** re-skins all existing rules (roadmap views included) with almost no markup change. New tokens are added next to them.

### 3.2 Colors

Color carries meaning, never decoration: **blue = action/focus/"current"**, **green = completed**, **amber = in progress**, **red = blocked/destructive**, **grey = not started**.

| Token | Light | Dark |
|---|---|---|
| `--bg` page | `#f6f7f9` | `#0b1220` |
| `--bg-elevated` cards, inputs | `#ffffff` | `#121b2d` |
| `--bg-sunken` hover, tracks | `#eef0f4` | `#1a2538` |
| `--bg-brand` (new) sidebar/brand panel (used from Phase 1) | `#0e1a2f` | `#08111f` |
| `--border` / `--border-strong` (new) | `#dde1e8` / `#b9c0cd` | `#26324a` / `#3a4863` |
| `--text` / `--text-muted` / `--text-faint` | `#141a26` / `#4a5365` / `#5f6a7d` | `#e8ecf4` / `#a9b3c6` / `#8591a8` |
| `--accent` / `--accent-ink` / `--accent-soft` | `#2b50d8` / `#ffffff` / `#eaf0ff` | `#6c8cff` / `#08111f` / `#1b2748` |
| `--status-completed` | `#17794d` | `#3dbe84` |
| `--status-in-progress` | `#9a5b00` | `#e0a33a` |
| `--status-blocked` / `--danger` | `#c0291f` | `#f0716a` |
| `--status-not-started` | `#5f6a7d` | `#8591a8` |

All text/background pairs were checked to meet WCAG 2.2 AA (4.5:1 text, 3:1 UI). **`--text-faint` must be `#5f6a7d` in light theme** — the natural-looking `#667085` measured 4.36:1 on the grey chip background and fails.

### 3.3 Typography

IBM Plex Sans 400/500/600, Latin subset, `font-display: swap`, two weights preloaded. Body is 14px/20px. Sentence case (no ALL-CAPS labels). Numbers in counters use tabular figures. Inputs are 16px below 640px wide (prevents iOS zoom-on-focus).

### 3.4 Shape and depth

Radius tiers by role: controls 6px, containers 10px, overlays 14px. **Borders over shadows**: `--shadow-sm` is `none`; only menus/toasts (`--shadow-md`) and dialogs (`--shadow-lg`) float.

### 3.5 Theme engine

- Saved choice lives in `localStorage["roadmap-dashboard:theme"]` as `light`, `dark` or `system`. **Missing = system.** Old saved values (`light`/`dark`) keep working.
- `js/theme-boot.js` runs **synchronously in `<head>`** and sets `<html data-theme="light|dark">` before the stylesheet paints. It must be an external file (CSP forbids inline scripts).
- System mode follows `prefers-color-scheme` live via `matchMedia`.
- CSS needs **one** dark block: `:root[data-theme="dark"]`. The old duplicated `@media (prefers-color-scheme: dark)` block is deleted.

### 3.6 Accessibility changes included in this phase

| Finding (from an automated axe-core audit) | Fix |
|---|---|
| `--text-faint` below 4.5:1 on grey chips | Darkened to `#5f6a7d` |
| ~850 status `<select>` elements without a name | `aria-label="Status: <task title>"` |
| Month and kanban filter `<select>` without a name | `aria-label` |
| Skills-checklist checkboxes without a name (119) | `aria-label="<skill title>"` |
| `role="menu"` panels with no menu items | `role="group"` + `aria-label`; triggers lose `aria-haspopup`, gain `aria-controls` |
| Login footer links distinguishable only by color | Always underlined |
| Confetti ignores reduced-motion | Skipped when `prefers-reduced-motion: reduce` |

---

## 4. Tasks (do them in this order)

Each task lists **Files**, the **Action**, and an **Acceptance** check. Code for every new file is in the appendices; copy it **verbatim**.

> Run every `python3 step_*.py` command **from the repository root**. Save the scripts from the appendices to a temporary folder outside the repo (e.g. `/tmp/p0/`) and call them with their path, or copy them into the repo root temporarily and delete them afterwards. **Do not commit them.**

### Task 1 — Branch and baseline

```bash
git checkout dev && git pull
git checkout -b feature/ui-redesign
npm install
npm test            # must report: tests 58, pass 58, fail 0
```

**Acceptance:** branch exists; baseline is 58/58.

### Task 2 — Fonts

**Files created:** `fonts/ibm-plex-sans-latin-400-normal.woff2`, `…-500-…`, `…-600-…`, `fonts/LICENSE-OFL.txt`.

```bash
mkdir -p fonts img
mkdir -p /tmp/fontsrc && cd /tmp/fontsrc && npm init -y >/dev/null && npm install @fontsource/ibm-plex-sans --no-audit --no-fund
cd -   # back to the repo root
for w in 400 500 600; do
  cp /tmp/fontsrc/node_modules/@fontsource/ibm-plex-sans/files/ibm-plex-sans-latin-$w-normal.woff2 fonts/
done
cp /tmp/fontsrc/node_modules/@fontsource/ibm-plex-sans/LICENSE fonts/LICENSE-OFL.txt
```

Use **only** the three `latin-{400,500,600}-normal.woff2` files (about 22–24 KB each). Do **not** add `@fontsource` to `package.json`. The font is licensed under the SIL Open Font License; the licence file must ship with it.

**Acceptance:** `ls fonts` shows exactly 3 `.woff2` files and `LICENSE-OFL.txt`; `git diff package.json` is empty.

### Task 3 — `css/tokens.css`

Create the file with the content of **Appendix A1**, verbatim.

**Acceptance:** file exists (121 lines); it defines `:root` and exactly one dark block `:root[data-theme="dark"]`.

### Task 4 — `css/base.css`

Create the file with **Appendix A2**, verbatim. It declares the three `@font-face` rules (paths are `../fonts/...`), the reset, `body` typography, the focus ring, and the reduced-motion rules (which also hide `#confettiCanvas`).

**Acceptance:** file exists (72 lines).

### Task 5 — `css/components.css`

Create the file with **Appendix A3**, verbatim. Class names that already existed (`.btn`, `.btn-primary`, `.btn-danger`, `.btn-ghost-danger`, `.field`, `.modal*`, `.toast*`, `.badge*`, `.status-*`, `.progress-*`, `.link-btn`) are **kept**, with new looks and new variants (`.btn-secondary`, `.btn-ghost`, `.btn-sm`, `.btn-lg`, `.btn-icon`, `.is-loading`, `.field-hint`, `.field-error`, `.skeleton`, `.avatar`, `.mini-btn`).

**Acceptance:** file exists (176 lines).

### Task 6 — Logo and favicon

Create `img/logo.svg` with **Appendix A4**, then copy it: `cp img/logo.svg img/favicon.svg`.

**Acceptance:** both files exist and are identical.

### Task 7 — `js/theme-boot.js`

Create the file with **Appendix A5**, verbatim. It exposes `window.Theme` (`get`, `resolved`, `set`, `onChange`).

**Acceptance:** `node --check js/theme-boot.js` passes.

### Task 8 — `js/icons.js`

Create the file with **Appendix A6**, verbatim. It exposes `window.Icons.svg(name, { size, label })`. (Nothing uses it yet in Phase 0 beyond being loaded; Phase 1 starts using it.)

**Acceptance:** `node --check js/icons.js` passes.

### Task 9 — Migrate `css/styles.css`

Run **Appendix B1** (`step_styles.py`).

**Intent (use this if you must do it by hand):**

1. Delete the file header, the `:root` token block and **both** dark-theme blocks (the `@media (prefers-color-scheme: dark)` one and the `[data-theme="dark"]` one), the `*{box-sizing}` reset, `body`, `.skip-link`, `button`, `.hidden` (all now live in `tokens.css` / `base.css`). Replace the header with a short comment.
2. Delete rules that moved to `components.css`: progress bars, badges, status chips, `select.status-select`, toasts and `@keyframes toast-in`, the modal block (`.modal*`, `.field*`, `.modal-actions`, `.btn*`), `.badge-custom`, `.field input[type=password|month]`, `.field input[type="text"], .field select { font-family }`, `.link-btn`, `.btn-ghost-danger`.
3. Replace every `var(--radius-lg)` with `var(--radius-md)` (containers), **except** the auth card (`--radius-lg`).
4. Remove ALL-CAPS styling (`text-transform: uppercase; letter-spacing`) from `.section-title`, `.phase-num`, `.kanban-col-head`, `.profile-panel-label`; use sentence case, 12–13px, weight 500–600.
5. Restyle the account menu **in place** (it is rebuilt in Phase 2): 280px wide, `--radius-lg`, segmented Light/Dark/System control, action buttons with hover background.
6. `.brand-icon` → `.brand-mark` (28px image); `.auth-brand` becomes a flex row with a 24px mark.
7. Underline `.auth-footer-link` always (links in running text must not rely on color alone).

**Acceptance:** script prints `css/styles.css migrated: 416 lines`; `grep -n "text-transform\|linear-gradient\|prefers-color-scheme" css/styles.css` prints nothing.

### Task 10 — Update `index.html`

Run **Appendix B2** (`step_index.py`).

**Intent:** (a) replace the emoji `data:` favicon with `img/favicon.svg`; (b) add `<meta name="color-scheme">`, then `<script src="js/theme-boot.js">` **before any stylesheet**; (c) preload two font files; (d) load `tokens.css`, `base.css`, `components.css`, then `styles.css` **in that order**; (e) replace the 4 compass emoji with `<img class="brand-mark" src="img/logo.svg" alt="" …>`; (f) menu label "Theme" → "Appearance" and add a **System** button `id="themeSystemBtn"`; (g) panels `role="menu"` → `role="group"` with `aria-label`, triggers drop `aria-haspopup` and gain `aria-controls`; (h) add `<script src="js/icons.js">` before `data/roadmap.js`.

**Acceptance:** script prints `index.html updated`; no `🧭` remains in `index.html`.

### Task 11 — Update `js/app.js`

Run **Appendix B3** (`step_appjs.py`).

**Intent:** (a) remove the `THEME_KEY` constant; (b) replace `applyTheme`/`initTheme` with `syncThemeButtons`/`initTheme` that use `window.Theme`; (c) one click handler per theme button calls `window.Theme.set(...)`; (d) `celebrate()` returns after the toast when `prefers-reduced-motion: reduce`; (e) the badge text "YOU ARE HERE" becomes "Current" (2 places); (f) add `aria-label` to the status `<select>`, the two month `<select>`s and the skills checkbox.

**Acceptance:** script prints `js/app.js updated`; `node --check js/app.js` passes; `grep -n "THEME_KEY\|applyTheme" js/app.js` prints nothing.

### Task 12 — Static allowlist and tests

Run **Appendix B4** (`step_server.py`). It adds, in `server/app.js` right after the `/js` line:

```js
app.use("/fonts", express.static(path.join(staticRoot, "fonts"), { maxAge: "365d", immutable: true }));
app.use("/img", express.static(path.join(staticRoot, "img")));
```

and, in `test/api.test.js`, asserts the new assets return 200, directory/traversal probes return 404, fonts are cacheable for a year, and the page's `script-src` has no `'unsafe-inline'`.

**Acceptance:** `npm test` → **59 tests pass** (58 original + 1 new).

### Task 13 — Documentation (required by `CLAUDE.md`)

1. Create `documentation/design-system.md` with **Appendix A7**, verbatim.
2. Run **Appendix B5** (`step_docs.py`) — updates `README.md`, `documentation/low-level-design.md`, `.claude/PROJECT_WALKTHROUGH.md`.
3. Copy this spec into the repo as `.claude/specs/ui-redesign-phase-0.md` (optional but recommended).

**Acceptance:** script prints `docs updated`; `README.md` says "All 59 tests".

### Task 14 — Verify

Follow Section 7. All checks must pass.

---

## 5. Behavior contract (what later phases rely on)

### 5.1 `window.Theme` (from `js/theme-boot.js`)

| Call | Returns / does |
|---|---|
| `Theme.get()` | `"light"` \| `"dark"` \| `"system"` — the saved choice (default `"system"`) |
| `Theme.resolved()` | `"light"` \| `"dark"` — what is actually applied |
| `Theme.set(mode)` | Saves, applies to `<html data-theme>`, notifies listeners. Ignores invalid values |
| `Theme.onChange(fn)` | `fn(mode, resolved)` on every change, including OS changes while in System mode |

Resolution: `light`/`dark` as saved; `system` → `prefers-color-scheme`. If `localStorage` is blocked, behave as `system` and still apply for the visit.

### 5.2 `window.Icons`

`Icons.svg("check")` → 16px decorative SVG string; `{ size: 20 }` changes size; `{ label: "Info" }` makes it `role="img"` with that label. `Icons.has(name)` tests existence. Unknown names return `""`. Names are fixed identifiers — never user input.

### 5.3 CSS class contract (stable names for Phases 1–5)

| Area | Classes |
|---|---|
| Buttons | `.btn` + one of `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`, `.btn-ghost-danger`; sizes `.btn-sm` (28px), default (36px), `.btn-lg` (44px); `.btn-icon`; loading `.is-loading` (label hidden, spinner, width unchanged) |
| Fields | `.field` wrapper with `label` + `input/select/textarea`; helpers `.field-hint`, `.field-error`; invalid via `aria-invalid="true"` |
| Feedback | `.badge` (+ `-success`, `-warning`, `-danger`, `-depth-*`, `-here`, `-custom`), `.status-chip` + `.status-{not_started,in_progress,completed,blocked}`, `.toast` (+ `.success`, `.error`, `.celebrate`), `.skeleton`, `.avatar` (+ `.avatar-lg`), `.mini-btn` |
| Progress | `.progress-track` > `.progress-fill` (solid green), `.progress-row`, `.progress-pct` |
| Overlays | `.modal-host` > `.modal-backdrop` + `.modal`, `.modal-actions` |
| Utility | `.hidden` (display none, `!important`) |

### 5.4 Focus and motion

- Every interactive element shows a 2px accent outline offset 2px on `:focus-visible` only (inputs use offset 0).
- `prefers-reduced-motion: reduce`: transitions and animations are effectively disabled globally; `#confettiCanvas` is hidden; `celebrate()` shows only the toast.

---

## 6. Acceptance criteria (checklist)

**Functional**
- [ ] App loads; login, sign-up, create/open/delete roadmap, saving a task, and all 7 views behave exactly as before.
- [ ] Account menu shows **Appearance** with **Light / Dark / System**; the active one is highlighted and has `aria-pressed`.
- [ ] Choosing Dark persists across reload and is applied before app scripts run (no white flash).
- [ ] System follows the operating system live; explicit Light/Dark ignores the OS.

**Visual**
- [ ] Font is IBM Plex Sans (verify with the browser inspector: Network shows 2–3 `woff2` requests, all 200).
- [ ] Accent is `#2b50d8` in light and `#6c8cff` in dark.
- [ ] The compass emoji is gone everywhere; a navy rounded-square logo mark appears on the auth card and headers; the browser tab shows the SVG favicon.
- [ ] Progress bars are solid green (no gradient). No ALL-CAPS small labels remain ("Appearance", section titles, "Current").
- [ ] **Layout is unchanged** from before (cards, tabs, header all in the same positions).

**Accessibility and security**
- [ ] axe-core (WCAG 2.2 A/AA) reports **0 violations** on login, Home, account menu, and all 7 roadmap views in light and dark.
- [ ] No console errors (a single `401` from the pre-login `/api/auth/me` check is expected).
- [ ] `document.querySelectorAll('script:not([src])').length === 0`.
- [ ] `/fonts/`, `/.env`, `/data/app.db`, `/server/app.js`, `/package.json` return 404; the new assets return 200.

**Tests and docs**
- [ ] `npm test` → 59/59.
- [ ] `documentation/design-system.md` exists; README, low-level design and walkthrough updated.
- [ ] `package.json` and `package-lock.json` are unchanged.

---

## 7. Verification

### 7.1 Automated

```bash
npm test      # expect: tests 59, pass 59, fail 0
```

### 7.2 UI harness (recommended)

The harness boots the real app on an in-memory database with a demo user, then drives Chromium. Save **Appendix C1** and **C2** into a folder **outside the repo** (e.g. `/tmp/ui-verify/`).

```bash
npm install --prefix /tmp/ui-verify axe-core
node /tmp/ui-verify/serve-demo.js "$(pwd)" 3111 &       # keep running
python3 /tmp/ui-verify/verify_phase0.py http://127.0.0.1:3111 \
        /tmp/ui-verify/node_modules/axe-core/axe.min.js /tmp/ui-verify/shots
# expect the last line:  RESULT 61/61 checks passed
```

Notes: the harness evaluates axe through the DevTools protocol because the app's CSP blocks injected `<script>` tags; it exits non-zero if any check fails. Open the PNGs in `/tmp/ui-verify/shots` for the visual checklist below. Stop the server afterwards.

### 7.3 Visual checklist (human or vision-capable agent)

| Screenshot | What you should see |
|---|---|
| `login-light.png` | Same centered card as before. Navy rounded logo tile before "Roadmap Tracker". Blue "Log in" button. Username field shows a thick blue focus ring. Footer text still has a ⭐ emoji and is now underlined for links |
| `home-light.png` | Same three-tile dashboard. Blue "Open" buttons, red-outlined "Delete", IBM Plex Sans type |
| `menu-light.png` | Account menu 280px wide: name, @username, "Appearance" with a grey segmented control **Light / Dark / System**, "Log out" |
| `overview-light.png` / `-dark.png` | Same Overview layout; green solid progress bars; amber/green/red status chips; dark theme is navy, not black |
| `checklist-*.png`, `kanban-*.png` | Same layouts, new colors and font; status dropdowns restyled |

### 7.4 Known and acceptable

- The ⭐, ⚙, 👤, ✦, ⬇ and other emoji remain in the UI until the phase that rebuilds each screen.
- The login screen still uses the old small centered card (Phase 1 changes it).
- The roadmap header still has the old two-row layout (Phase 2 changes it).

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Font looks like a system font | `fonts/*.woff2` missing or not served: check `GET /fonts/ibm-plex-sans-latin-400-normal.woff2` is 200 and that Task 12 was applied |
| Console: "Refused to execute inline script" | Something added an inline `<script>`. Theme code must stay in `js/theme-boot.js` |
| Dark users see a white flash | `theme-boot.js` is not the **first** thing in `<head>` after the meta tags, or it has `defer`/`async` |
| Theme buttons do nothing | `window.Theme` undefined: `theme-boot.js` not loaded or path wrong |
| `npm test` fails the static test | `fonts/` or `img/` folder/file names differ from the test's expectations |
| A `step_*.py` assertion fails | Repo drifted. Apply the "Intent" list manually (Section 4) and note it |
| axe reports `color-contrast` on grey chips | `--text-faint`/`--status-not-started` is not `#5f6a7d` |
| Harness cannot inject axe | Do not use `add_script_tag`; evaluate the source (as the harness does) |

---

## 9. Hand-off notes (what to tell the reviewer, and what Phase 1 assumes)

Report: the branch name; commit list; `npm test` result; the harness result line; any manual deviations. **Phase 1 assumes** these exist and are unchanged: `Theme`, `Icons.svg`, the CSS class contract in 5.3, token names in 3.2 (plus `--bg-brand`, `--border-strong`), and `#themeSystemBtn`.

**Rollback:** `git revert` the Phase 0 commits (or delete the branch). No database or API change was made, so there is nothing else to undo.

---

# Appendices


## Appendix A1 — `css/tokens.css`

```css
/* ===========================================================
   Design tokens — Roadmap Tracker
   Single source of truth for color, radius, spacing, type.
   Existing variable names are kept so older rules keep working;
   new tokens sit beside them. Dark theme is one block, selected
   by <html data-theme="dark"> (set by js/theme-boot.js).
   See documentation/design-system.md.
   =========================================================== */

:root {
  /* Surfaces */
  --bg: #f6f7f9;
  --bg-elevated: #ffffff;
  --bg-sunken: #eef0f4;
  --bg-brand: #0e1a2f;

  /* Lines */
  --border: #dde1e8;
  --border-strong: #b9c0cd;

  /* Text */
  --text: #141a26;
  --text-muted: #4a5365;
  --text-faint: #5f6a7d;

  /* Accent (actions, focus, "you are here") */
  --accent: #2b50d8;
  --accent-ink: #ffffff;
  --accent-soft: #eaf0ff;
  --accent-hover: #2142b8;
  --accent-pressed: #1b3699;

  /* Status — colour carries meaning, never decoration */
  --status-not-started: #5f6a7d;
  --status-not-started-bg: #eef0f4;
  --status-in-progress: #9a5b00;
  --status-in-progress-bg: #fff4df;
  --status-completed: #17794d;
  --status-completed-bg: #e6f4ec;
  --status-blocked: #c0291f;
  --status-blocked-bg: #fdecea;

  --danger: #c0291f;
  --danger-soft: #fdecea;
  --danger-ink: #ffffff;

  --priority-critical: #c0291f;
  --priority-high: #9a5b00;
  --priority-medium: #2b50d8;

  /* Elevation: borders by default, shadows only for floating layers */
  --shadow-sm: none;
  --shadow-md: 0 4px 16px rgb(14 26 47 / 0.1);
  --shadow-lg: 0 12px 40px rgb(14 26 47 / 0.18);

  /* Radius, tiered by role */
  --radius-sm: 6px;   /* controls */
  --radius-md: 10px;  /* containers */
  --radius-lg: 14px;  /* overlays */

  /* Spacing (4px grid) */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;

  /* Focus ring (keyboard only, see base.css) */
  --focus-ring: 0 0 0 2px var(--bg-elevated), 0 0 0 4px var(--accent);

  /* Type */
  --font: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  color-scheme: light;
}

:root[data-theme="dark"] {
  --bg: #0b1220;
  --bg-elevated: #121b2d;
  --bg-sunken: #1a2538;
  --bg-brand: #08111f;

  --border: #26324a;
  --border-strong: #3a4863;

  --text: #e8ecf4;
  --text-muted: #a9b3c6;
  --text-faint: #8591a8;

  --accent: #6c8cff;
  --accent-ink: #08111f;
  --accent-soft: #1b2748;
  --accent-hover: #8aa3ff;
  --accent-pressed: #a5b8ff;

  --status-not-started: #8591a8;
  --status-not-started-bg: #1f2a3e;
  --status-in-progress: #e0a33a;
  --status-in-progress-bg: #2b2112;
  --status-completed: #3dbe84;
  --status-completed-bg: #12281f;
  --status-blocked: #f0716a;
  --status-blocked-bg: #2e1816;

  --danger: #f0716a;
  --danger-soft: #2e1816;
  --danger-ink: #08111f;

  --priority-critical: #f0716a;
  --priority-high: #e0a33a;
  --priority-medium: #8aa3ff;

  --shadow-md: 0 4px 16px rgb(0 0 0 / 0.4);
  --shadow-lg: 0 16px 40px rgb(0 0 0 / 0.5);

  color-scheme: dark;
}
```

## Appendix A2 — `css/base.css`

```css
/* ===========================================================
   Base — fonts, reset, typography, focus, motion preferences.
   Loaded after tokens.css, before components.css.
   =========================================================== */

/* IBM Plex Sans, self-hosted (SIL Open Font License, see fonts/LICENSE-OFL.txt).
   Latin subset only; the stack in --font falls back to system fonts. */
@font-face {
  font-family: "IBM Plex Sans";
  font-style: normal; font-weight: 400; font-display: swap;
  src: url("../fonts/ibm-plex-sans-latin-400-normal.woff2") format("woff2");
}
@font-face {
  font-family: "IBM Plex Sans";
  font-style: normal; font-weight: 500; font-display: swap;
  src: url("../fonts/ibm-plex-sans-latin-500-normal.woff2") format("woff2");
}
@font-face {
  font-family: "IBM Plex Sans";
  font-style: normal; font-weight: 600; font-display: swap;
  src: url("../fonts/ibm-plex-sans-latin-600-normal.woff2") format("woff2");
}

* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  font-family: var(--font);
  font-size: 14px;
  line-height: 1.43;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

h1, h2, h3, h4 { font-weight: 600; letter-spacing: -0.01em; }
button { font-family: inherit; cursor: pointer; }
input, select, textarea { font-family: inherit; }
.hidden { display: none !important; }

/* Numbers line up in columns (counts, percentages, dates). */
.stat-value, .progress-pct, .topic-progress, .badge, .status-chip, .due-tag,
.roadmap-card-meta, .stat-sub { font-variant-numeric: tabular-nums; }

.skip-link {
  position: absolute; left: -999px; top: 0;
  background: var(--accent); color: var(--accent-ink);
  padding: 8px 14px; border-radius: 0 0 8px 0; z-index: 999;
}
.skip-link:focus { left: 0; }

/* Keyboard focus: one ring, everywhere, never for mouse clicks. */
:focus { outline: none; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.field input:focus-visible, .field textarea:focus-visible, .field select:focus-visible {
  outline-offset: 0;
}

::selection { background: var(--accent-soft); color: var(--text); }

/* Respect the operating-system "reduce motion" setting. The confetti canvas is
   hidden too; celebrate() in app.js shows a toast instead. */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  #confettiCanvas { display: none !important; }
}
```

## Appendix A3 — `css/components.css`

```css
/* ===========================================================
   Components — buttons, fields, chips, badges, progress,
   modal, toast, skeleton, avatar.
   Class names that already existed are kept.
   =========================================================== */

/* ---------------- Buttons ---------------- */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  min-height: 36px; padding: 0 14px;
  border: 1px solid var(--border-strong); background: var(--bg-elevated); color: var(--text);
  border-radius: var(--radius-sm);
  font-size: 14px; font-weight: 500; line-height: 1.2; text-decoration: none;
  transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease;
}
.btn:hover { background: var(--bg-sunken); }
.btn:active { background: var(--bg-sunken); border-color: var(--text-faint); }
.btn[disabled], .btn[aria-disabled="true"] { opacity: 0.55; cursor: not-allowed; }

.btn-primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.btn-primary:active { background: var(--accent-pressed); border-color: var(--accent-pressed); }

.btn-secondary { background: var(--bg-elevated); }
.btn-ghost { background: transparent; border-color: transparent; color: var(--text-muted); }
.btn-ghost:hover { background: var(--bg-sunken); color: var(--text); }

.btn-danger { background: var(--danger); border-color: var(--danger); color: var(--danger-ink); }
.btn-danger:hover { background: var(--danger); filter: brightness(0.92); }
.btn-ghost-danger { background: transparent; color: var(--danger); border-color: var(--border-strong); }
.btn-ghost-danger:hover { background: var(--danger-soft); border-color: var(--danger); }

.btn-sm { min-height: 28px; padding: 0 10px; font-size: 13px; }
.btn-lg { min-height: 44px; padding: 0 18px; }
.btn-icon { width: 36px; padding: 0; }

/* Loading: label hidden, spinner shown, width unchanged. */
.btn.is-loading { position: relative; color: transparent !important; pointer-events: none; }
.btn.is-loading::after {
  content: ""; position: absolute; width: 16px; height: 16px;
  border: 2px solid var(--accent-ink); border-right-color: transparent; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.link-btn {
  background: none; border: none; padding: 0; color: var(--accent);
  font-size: inherit; font-weight: 500; text-decoration: underline; text-underline-offset: 2px;
}
.link-btn:hover { color: var(--accent-hover); }

@media (pointer: coarse) {
  .btn { min-height: 44px; }
  .btn-sm { min-height: 36px; }
}

/* ---------------- Form fields ---------------- */
.field { margin-bottom: 16px; }
.field label { display: block; font-size: 13px; font-weight: 500; color: var(--text); margin-bottom: 6px; }
.field input:not([type="checkbox"]):not([type="radio"]):not([type="file"]),
.field textarea, .field select {
  width: 100%; min-height: 40px; padding: 9px 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border-strong);
  background: var(--bg-elevated); color: var(--text); font-size: 14px; font-family: inherit;
  transition: border-color 0.12s ease;
}
.field input:not([type="checkbox"]):not([type="radio"]):not([type="file"]):hover,
.field textarea:hover, .field select:hover { border-color: var(--text-faint); }
.field input:not([type="checkbox"]):not([type="radio"]):not([type="file"]):focus,
.field textarea:focus, .field select:focus { border-color: var(--accent); }
.field textarea { min-height: 80px; resize: vertical; }
.field input[aria-invalid="true"], .field textarea[aria-invalid="true"] { border-color: var(--danger); }
.field-hint { font-size: 12px; color: var(--text-faint); margin: 6px 0 0; }
.field-error { font-size: 12px; color: var(--danger); margin: 6px 0 0; }

@media (max-width: 640px) {
  .field input:not([type="checkbox"]):not([type="radio"]):not([type="file"]),
  .field textarea, .field select { font-size: 16px; } /* stops iOS zoom-on-focus */
}

/* ---------------- Progress bar ---------------- */
.progress-track {
  height: 8px; border-radius: 99px; background: var(--bg-sunken); overflow: hidden;
}
.progress-fill {
  height: 100%; border-radius: 99px; background: var(--status-completed);
  transition: width 0.3s ease;
}
.progress-row { display: flex; align-items: center; gap: 10px; }
.progress-row .progress-track { flex: 1; }
.progress-pct { font-size: 12.5px; font-weight: 600; color: var(--text-muted); min-width: 36px; text-align: right; }

/* ---------------- Badges and status chips ---------------- */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 99px; font-size: 12px; font-weight: 500;
  white-space: nowrap;
}
.badge-depth-D3 { background: var(--accent-soft); color: var(--accent); }
.badge-depth-D2 { background: var(--bg-sunken); color: var(--text-muted); }
.badge-depth-D1 { background: var(--bg-sunken); color: var(--text-faint); }
.badge-here { background: var(--accent-soft); color: var(--accent); }
.badge-custom { background: var(--accent-soft); color: var(--accent); }
.badge-success { background: var(--status-completed-bg); color: var(--status-completed); }
.badge-warning { background: var(--status-in-progress-bg); color: var(--status-in-progress); }
.badge-danger { background: var(--status-blocked-bg); color: var(--status-blocked); }

.status-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 500;
}
.status-chip::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status-not_started { color: var(--status-not-started); background: var(--status-not-started-bg); }
.status-in_progress { color: var(--status-in-progress); background: var(--status-in-progress-bg); }
.status-completed { color: var(--status-completed); background: var(--status-completed-bg); }
.status-blocked { color: var(--status-blocked); background: var(--status-blocked-bg); }

select.status-select {
  border-radius: var(--radius-sm); border: 1px solid var(--border-strong); background: var(--bg-elevated);
  color: var(--text); font-size: 13px; font-weight: 500; padding: 5px 8px;
}

/* ---------------- Modal ---------------- */
.modal-host { position: fixed; inset: 0; z-index: 400; display: flex; align-items: center; justify-content: center; padding: 16px; }
.modal-backdrop { position: absolute; inset: 0; background: rgb(8 17 31 / 0.55); }
.modal {
  position: relative; background: var(--bg-elevated); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
  width: 100%; max-width: 480px; max-height: 85vh; overflow-y: auto; padding: 24px;
}
.modal h2 { margin: 0 0 16px; font-size: 18px; line-height: 1.4; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }

/* ---------------- Toasts ---------------- */
.toast-host { position: fixed; bottom: 18px; right: 18px; display: flex; flex-direction: column; gap: 8px; z-index: 450; }
.toast {
  background: var(--bg-elevated); border: 1px solid var(--border); box-shadow: var(--shadow-md);
  border-radius: var(--radius-md); padding: 12px 16px; font-size: 14px; max-width: 360px;
  animation: toast-in 0.16s ease;
}
.toast.success { border-left: 3px solid var(--status-completed); }
.toast.error { border-left: 3px solid var(--status-blocked); }
.toast.celebrate { border-left: 3px solid var(--accent); }
@keyframes toast-in { from { transform: translateY(4px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@media (max-width: 640px) {
  .toast-host { left: 12px; right: 12px; bottom: 12px; align-items: stretch; }
  .toast { max-width: none; }
}

/* ---------------- Skeleton (loading placeholder) ---------------- */
.skeleton {
  display: block; border-radius: var(--radius-sm); min-height: 12px;
  background: linear-gradient(90deg, var(--bg-sunken) 25%, var(--border) 50%, var(--bg-sunken) 75%);
  background-size: 200% 100%; animation: skeleton 1.4s ease-in-out infinite;
}
@keyframes skeleton { from { background-position: 200% 0; } to { background-position: -200% 0; } }

/* ---------------- Avatar (initials) ---------------- */
.avatar {
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--accent-soft); color: var(--accent);
  font-size: 12px; font-weight: 600; letter-spacing: 0.02em; user-select: none;
}
.avatar-lg { width: 40px; height: 40px; font-size: 14px; }

/* ---------------- Mini button (steppers, inline actions) ---------------- */
.mini-btn {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 28px; min-height: 28px; padding: 0 8px;
  border: 1px solid var(--border-strong); background: var(--bg-elevated); color: var(--text);
  border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; line-height: 1;
  transition: background 0.12s ease;
}
.mini-btn:hover { background: var(--bg-sunken); }
@media (pointer: coarse) { .mini-btn { min-width: 36px; min-height: 36px; } }
```

## Appendix A4 — `img/logo.svg` (also copy to `img/favicon.svg`)

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" role="img" aria-label="Roadmap Tracker">
  <rect width="32" height="32" rx="8" fill="#0E1A2F"/>
  <circle cx="16" cy="16" r="9.5" fill="none" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="1.6"/>
  <path d="M16 6.5v2.4M16 23.1v2.4M6.5 16h2.4M23.1 16h2.4" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M20.6 11.4l-2.9 6.3-6.3 2.9 2.9-6.3z" fill="#6C8CFF"/>
  <path d="M20.6 11.4l-2.9 6.3-2.9-2.9z" fill="#FFFFFF"/>
</svg>
```

## Appendix A5 — `js/theme-boot.js`

```javascript
/**
 * @module theme-boot
 * Resolves the appearance setting (light / dark / system) and applies it to
 * <html data-theme="…"> before first paint, so dark-theme users never see a
 * white flash. Loaded synchronously from <head> as an external file because
 * the Content Security Policy forbids inline scripts.
 *
 * Exposes `window.Theme` for the account menu:
 *   Theme.get()        → "light" | "dark" | "system"  (the saved choice)
 *   Theme.resolved()   → "light" | "dark"             (what is on screen)
 *   Theme.set(mode)    → saves, applies, notifies listeners
 *   Theme.onChange(fn) → fn(mode, resolved) on every change (incl. OS change)
 *
 * Storage: localStorage key "roadmap-dashboard:theme". A missing or unknown
 * value means "system". Only the appearance preference is stored here — never
 * tokens or personal data.
 */
(function () {
  "use strict";

  const KEY = "roadmap-dashboard:theme";
  const MODES = ["light", "dark", "system"];
  const listeners = [];
  const query = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function read() {
    try {
      const saved = localStorage.getItem(KEY);
      return MODES.includes(saved) ? saved : "system";
    } catch {
      return "system"; // storage blocked (private mode, policy)
    }
  }

  function resolve(mode) {
    if (mode === "light" || mode === "dark") return mode;
    return query && query.matches ? "dark" : "light";
  }

  function apply() {
    const mode = read();
    const resolved = resolve(mode);
    document.documentElement.setAttribute("data-theme", resolved);
    listeners.forEach((fn) => fn(mode, resolved));
  }

  function set(mode) {
    if (!MODES.includes(mode)) return;
    try { localStorage.setItem(KEY, mode); } catch { /* ignore: still applies for this visit */ }
    apply();
  }

  if (query) {
    const onOsChange = () => { if (read() === "system") apply(); };
    if (query.addEventListener) query.addEventListener("change", onOsChange);
    else if (query.addListener) query.addListener(onOsChange);
  }

  window.Theme = {
    get: read,
    resolved: () => resolve(read()),
    set,
    onChange(fn) { listeners.push(fn); },
  };

  apply();
})();
```

## Appendix A6 — `js/icons.js`

```javascript
/**
 * @module icons
 * Inline SVG icon set (outline, 1.5px stroke). Paths are from Lucide
 * (https://lucide.dev, ISC licence). Replaces emoji so icons render the same
 * on every operating system.
 *
 *   Icons.svg("check")                 → '<svg …>…</svg>' (16px, decorative)
 *   Icons.svg("trash", { size: 20 })   → 20px
 *   Icons.svg("info", { label: "Info" })→ adds role="img" and aria-label
 *
 * Icon names are fixed identifiers, never user input, so the returned string
 * is safe to put inside an innerHTML template.
 */
(function () {
  "use strict";

  const PATHS = {
    check: '<path d="M20 6 9 17l-5-5"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    minus: '<path d="M5 12h14"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    menu: '<path d="M4 12h16"/><path d="M4 6h16"/><path d="M4 18h16"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    eye: '<path d="M2.06 12.35a1 1 0 0 1 0-.7 10.75 10.75 0 0 1 19.88 0 1 1 0 0 1 0 .7 10.75 10.75 0 0 1-19.88 0"/><circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c4.5 0 8.3 2.9 9.94 7a10.75 10.75 0 0 1-1.67 2.68"/><path d="M6.61 6.61A10.7 10.7 0 0 0 2.06 12c1.64 4.1 5.44 7 9.94 7a10.4 10.4 0 0 0 5.39-1.61"/><path d="m2 2 20 20"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    "log-out": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    calendar: '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
    archive: '<rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
    "more-horizontal": '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "alert-triangle": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "check-circle": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
    star: '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
    sparkles: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
    "layout-grid": '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    list: '<path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M8 6h13"/>',
    map: '<path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z"/><path d="M15 5.764v15"/><path d="M9 3.236v15"/>',
    "panel-left": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/>',
    help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  };

  function svg(name, opts) {
    const o = opts || {};
    const size = Number(o.size) || 16;
    const body = PATHS[name];
    if (!body) return "";
    const a11y = o.label
      ? `role="img" aria-label="${String(o.label).replace(/[&<>"']/g, "")}"`
      : 'aria-hidden="true" focusable="false"';
    return `<svg class="icon" xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" ${a11y}>${body}</svg>`;
  }

  window.Icons = { svg, has: (name) => Object.prototype.hasOwnProperty.call(PATHS, name) };
})();
```

## Appendix A7 — `documentation/design-system.md`

````markdown
# Design System

The visual language of Roadmap Tracker: design tokens, typography, components, theming and the rules that keep screens consistent. The full redesign rationale and phase plan live in `.claude/specs/ui-redesign-spec.md`.

**Principles:** progress is the hero; color carries meaning (status), never decoration; borders over shadows; dense but breathable; keyboard and screen-reader friendly by default.

## File map (no build step)

| File | Role |
|---|---|
| `css/tokens.css` | **Single source** of color, radius, spacing, type tokens. Light on `:root`, dark on `:root[data-theme="dark"]` |
| `css/base.css` | `@font-face` (self-hosted IBM Plex Sans), reset, body type, focus ring, reduced-motion rules |
| `css/components.css` | Buttons, form fields, progress bar, badges, status chips, modal, toasts, skeleton, avatar, mini button |
| `css/styles.css` | Layout and per-view rules not yet moved (shrinks each phase; see "Redesign status") |
| `js/theme-boot.js` | Applies Light / Dark / System **before first paint**; exposes `window.Theme` |
| `js/icons.js` | Inline SVG icon set, `Icons.svg(name, { size, label })` (Lucide, ISC licence) |
| `fonts/` | IBM Plex Sans 400 / 500 / 600, Latin subset, plus the SIL OFL licence |
| `img/` | `logo.svg` (brand mark) and `favicon.svg` |

Load order in `index.html`: `theme-boot.js` (blocking, in `<head>`) → `tokens.css` → `base.css` → `components.css` → `styles.css`; scripts at the end: `icons.js`, `data/roadmap.js`, `progress-schema.js`, `api.js`, `app.js`.

## Tokens

Existing variable names were kept (`--bg`, `--bg-elevated`, `--bg-sunken`, `--border`, `--text`, `--text-muted`, `--text-faint`, `--accent`, `--accent-ink`, `--accent-soft`, `--status-*`, `--radius-*`) so older rules keep working; new ones sit beside them (`--bg-brand`, `--border-strong`, `--accent-hover`, `--accent-pressed`, `--danger*`, `--space-*`).

| Meaning | Token | Light | Dark |
|---|---|---|---|
| Page | `--bg` | `#f6f7f9` | `#0b1220` |
| Cards, inputs | `--bg-elevated` | `#ffffff` | `#121b2d` |
| Hover, tracks | `--bg-sunken` | `#eef0f4` | `#1a2538` |
| Brand surfaces | `--bg-brand` | `#0e1a2f` | `#08111f` |
| Actions, focus, "current" | `--accent` | `#2b50d8` | `#6c8cff` |
| Completed | `--status-completed` | `#17794d` | `#3dbe84` |
| In progress | `--status-in-progress` | `#9a5b00` | `#e0a33a` |
| Blocked, destructive | `--status-blocked` / `--danger` | `#c0291f` | `#f0716a` |
| Not started | `--status-not-started` | `#5f6a7d` | `#8591a8` |

Contrast was verified with axe-core (WCAG 2.2 AA). `--text-faint` is `#5f6a7d` (4.79:1 on `--bg-sunken`), darker than the original grey, to pass.

**Never hard-code colors in components**; use a token. Radii are tiered by role: `--radius-sm` 6px (controls), `--radius-md` 10px (containers), `--radius-lg` 14px (overlays). Shadows exist only for floating layers (`--shadow-md` menus and toasts, `--shadow-lg` dialogs).

## Typography

IBM Plex Sans, self-hosted (`fonts/`), with a system-font fallback. Body 14px / 20px. Sentence case everywhere (no all-caps labels). Counts and percentages use tabular figures. Inputs are 16px under 640px wide to prevent iOS zoom-on-focus.

## Theme (Light / Dark / System)

`js/theme-boot.js` reads `localStorage["roadmap-dashboard:theme"]` (`light`, `dark` or `system`; missing means `system`), resolves it, and sets `<html data-theme="light|dark">`. In System mode it follows the operating-system setting live. It is an **external** script because the Content Security Policy forbids inline scripts. Only the appearance preference is stored; never tokens or personal data (project rule).

```js
Theme.get();        // "light" | "dark" | "system"  (saved choice)
Theme.resolved();   // "light" | "dark"             (what is on screen)
Theme.set("dark");  // save + apply + notify
Theme.onChange((mode, resolved) => { /* … */ });
```

## Motion and accessibility rules

- Hover and press: color only, 120ms. Menus, dialogs and toasts: 160ms fade plus a 4px shift, only when the user opens them.
- `prefers-reduced-motion: reduce` disables transitions and animations globally and hides the confetti canvas (the toast still appears).
- One focus style: a 2px accent outline, shown for keyboard focus only (`:focus-visible`).
- Every `<select>`, checkbox and icon-only button needs an accessible name (`aria-label` or a label).
- Do not use `role="menu"` for panels that contain mixed controls; use a labelled group with `aria-expanded` on the trigger.
- Icons: use `Icons.svg()`, never emoji, for UI controls.

## Content Security Policy constraints

`helmet()` default CSP applies: scripts from `'self'` only (no inline scripts, no `eval`), styles from `'self'` and inline styles, fonts and images from `'self'`/`data:`. New assets must be same-origin files served by the allowlist in `server/app.js` (`/css`, `/js`, `/fonts`, `/img`, `/data/roadmap.js`).

## Redesign status

| Phase | Scope | Status |
|---|---|---|
| 0 | Tokens, fonts, theme (incl. System), icons, base components, reduced motion | Done |
| 1 | Log in and create-account screens | Not started |
| 2 | App shell, Home, `stats` API | Not started |
| 3 | Home flows (New roadmap dialog, filters, list view) | Not started |
| 4 | Roadmap views | Not started |
| 5 | Hardening, remove legacy CSS | Not started |
````

## Appendix B1 — `step_styles.py` (Task 9)

Run from the repo root: `python3 step_styles.py`.

```python
"""Phase 0 / css/styles.css migration. Run from the repo root: python3 step_styles.py
Fails loudly (assert) if any expected block is missing."""
import re

P = "css/styles.css"
s = open(P, encoding="utf-8").read()


def cut(start_marker, end_marker):
    """Delete from start_marker up to (not including) end_marker."""
    global s
    i = s.index(start_marker)
    j = s.index(end_marker, i + len(start_marker))
    s = s[:i] + s[j:]


def replace(old, new, count=1):
    global s
    assert old in s, "pattern not found: " + old[:70]
    s = s.replace(old, new, count)


# 1. Tokens, dark-theme blocks, reset, skip-link, base button rules move to tokens.css / base.css
cut("/* ===========================================================\n   AI Engineer Roadmap",
    "/* ---------------- Header ---------------- */")
s = ("/* ===========================================================\n"
     "   Roadmap Tracker — screen styles.\n"
     "   Tokens: css/tokens.css · Base: css/base.css · Components: css/components.css\n"
     "   This file holds layout and view-specific rules only; it shrinks as the\n"
     "   redesign phases move screens into their own files (see\n"
     "   documentation/design-system.md).\n"
     "   =========================================================== */\n\n") + s

# 2. Components that moved to components.css
cut("/* ---------------- Progress bars ---------------- */",
    "/* ---------------- Phase cards (Overview + Timeline) ---------------- */")
cut("/* ---------------- Toasts ---------------- */", "#confettiCanvas {")
cut("/* ---------------- Modal ---------------- */", "/* ---------------- Responsive ---------------- */")

# 3. Small leftovers that moved
replace(".badge-custom { background: var(--accent-soft); color: var(--accent); }\n", "")
for pattern in (
    r'\.field input\[type="text"\], \.field select \{ font-family: inherit; \}\n',
    r'\.field input\[type="password"\] \{[^}]*\}\n',
    r'\.field input\[type="month"\] \{[^}]*\}\n',
    r'\.link-btn \{[^}]*\}\n',
    r'\.btn-ghost-danger \{[^}]*\}\n\.btn-ghost-danger:hover \{[^}]*\}\n',
):
    assert re.search(pattern, s), "pattern not found: " + pattern
    s = re.sub(pattern, "", s)

# 4. Radius tiers: containers use md; overlays (auth card, profile panel) keep lg
s = s.replace("var(--radius-lg)", "var(--radius-md)")
replace("max-width: 380px; background: var(--bg-elevated); border: 1px solid var(--border);\n  border-radius: var(--radius-md);",
        "max-width: 380px; background: var(--bg-elevated); border: 1px solid var(--border);\n  border-radius: var(--radius-lg);")

# 5. Sentence case instead of ALL CAPS labels
replace("font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em;\n  color: var(--text-faint); font-weight: 700; margin: 28px 0 12px;",
        "font-size: 13px;\n  color: var(--text-muted); font-weight: 600; margin: 28px 0 12px;")
replace(".phase-num { font-size: 11px; color: var(--text-faint); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }",
        ".phase-num { font-size: 12px; color: var(--text-faint); font-weight: 600; }")
replace("font-size: 12px; font-weight: 700; padding: 4px 6px 10px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); }",
        "font-size: 13px; font-weight: 600; padding: 4px 6px 10px; color: var(--text-muted); }")
replace("  font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;\n  color: var(--text-faint);\n}",
        "  font-size: 12px; font-weight: 500; color: var(--text-faint);\n}")

# 6. Account menu restyled in place (it is rebuilt in Phase 2)
replace("background: var(--bg-sunken); border: 1px solid var(--border); border-radius: 8px;\n  color: var(--text); font-size: 13.5px; font-weight: 500;",
        "background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: var(--radius-sm);\n  color: var(--text); font-size: 14px; font-weight: 500; min-height: 36px;")
replace(".profile-trigger:hover { background: var(--bg-elevated); filter: brightness(0.97); }\n.profile-trigger[aria-expanded=\"true\"] { background: var(--bg-elevated); }",
        ".profile-trigger:hover { background: var(--bg-sunken); }\n.profile-trigger[aria-expanded=\"true\"] { background: var(--bg-sunken); }")
replace("width: 240px;\n  background: var(--bg-elevated); border: 1px solid var(--border);\n  border-radius: 12px; box-shadow: var(--shadow-lg);",
        "width: 280px; max-width: calc(100vw - 24px);\n  background: var(--bg-elevated); border: 1px solid var(--border);\n  border-radius: var(--radius-lg); box-shadow: var(--shadow-md);")
replace(".profile-panel-fullname { font-weight: 700; font-size: 14px;", ".profile-panel-fullname { font-weight: 600; font-size: 14px;")
replace(".profile-panel-section { padding: 8px 16px; display: flex; flex-direction: column; gap: 6px; }",
        ".profile-panel-section { padding: 8px 12px; display: flex; flex-direction: column; gap: 6px; }")
replace(""".profile-theme-btns { display: flex; gap: 6px; }
.profile-theme-btn {
  flex: 1; padding: 5px 0;
  border: 1px solid var(--border); border-radius: 6px;
  background: var(--bg-sunken); color: var(--text); font-size: 12.5px;
  cursor: pointer; transition: background 0.15s, border-color 0.15s;
}
.profile-theme-btn:hover { background: var(--bg-elevated); }
.profile-theme-btn.active { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }""",
""".profile-theme-btns { display: flex; gap: 2px; padding: 3px; background: var(--bg-sunken); border-radius: var(--radius-sm); }
.profile-theme-btn {
  flex: 1; padding: 5px 0; min-height: 28px;
  border: 1px solid transparent; border-radius: 4px;
  background: transparent; color: var(--text-muted); font-size: 13px; font-weight: 500;
  cursor: pointer; transition: background 0.12s, color 0.12s;
}
.profile-theme-btn:hover { color: var(--text); }
.profile-theme-btn.active { background: var(--bg-elevated); color: var(--text); border-color: var(--border-strong); font-weight: 600; }""")
replace("width: 100%; text-align: left; padding: 7px 0;\n  background: none; border: none; color: var(--text); font-size: 13px;\n  cursor: pointer; border-radius: 4px; transition: color 0.15s;\n}\n.profile-action-btn:hover { color: var(--accent); }\n.profile-action-btn.danger { color: var(--status-blocked); }\n.profile-action-btn.danger:hover { opacity: 0.8; }",
        "width: 100%; text-align: left; padding: 8px 10px;\n  background: none; border: none; color: var(--text); font-size: 14px;\n  cursor: pointer; border-radius: var(--radius-sm); transition: background 0.12s;\n}\n.profile-action-btn:hover { background: var(--bg-sunken); }\n.profile-action-btn.danger { color: var(--danger); }\n.profile-action-btn.danger:hover { background: var(--danger-soft); }")

# 7. Brand mark replaces the compass emoji
replace(".brand-icon { font-size: 28px; }",
        ".brand-mark { width: 28px; height: 28px; border-radius: 7px; flex-shrink: 0; display: block; }")
replace(".auth-brand { font-size: 14px; font-weight: 700; color: var(--text-muted); margin-bottom: 14px; }",
        ".auth-brand { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 16px; }\n.auth-brand .brand-mark { width: 24px; height: 24px; border-radius: 6px; }")
replace(".brand h1 { font-size: 17px; margin: 0; font-weight: 700; letter-spacing: -0.01em; }",
        ".brand h1 { font-size: 17px; margin: 0; font-weight: 600; letter-spacing: -0.01em; }")

# 8. Links inside running text must not rely on colour alone (WCAG 1.4.1): underline them
replace(".auth-footer-link { color: var(--accent); text-decoration: none; }\n.auth-footer-link:hover { text-decoration: underline; }",
        ".auth-footer-link { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }\n.auth-footer-link:hover { color: var(--accent-hover); }")

open(P, "w", encoding="utf-8").write(s)

# Sanity checks on the result
assert "text-transform" not in s, "an ALL CAPS rule is still present"
assert "linear-gradient" not in s
assert "prefers-color-scheme" not in s
print("css/styles.css migrated:", len(s.splitlines()), "lines")
```

## Appendix B2 — `step_index.py` (Task 10)

Run from the repo root: `python3 step_index.py`.

```python
"""Phase 0 / index.html. Run from the repo root: python3 step_index.py"""
P = "index.html"
s = open(P, encoding="utf-8").read()


def replace(old, new, count=1):
    global s
    assert old in s, "pattern not found: " + old[:80]
    s = s.replace(old, new, count) if count else s.replace(old, new)


# 1. <head>: SVG favicon, theme script (blocking, external), font preloads, split stylesheets
replace('''<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🧭</text></svg>" />
<link rel="stylesheet" href="css/styles.css" />''',
'''<link rel="icon" type="image/svg+xml" href="img/favicon.svg" />
<meta name="color-scheme" content="light dark" />
<script src="js/theme-boot.js"></script>
<link rel="preload" href="fonts/ibm-plex-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin />
<link rel="preload" href="fonts/ibm-plex-sans-latin-500-normal.woff2" as="font" type="font/woff2" crossorigin />
<link rel="stylesheet" href="css/tokens.css" />
<link rel="stylesheet" href="css/base.css" />
<link rel="stylesheet" href="css/components.css" />
<link rel="stylesheet" href="css/styles.css" />''')

# 2. Brand marks replace the compass emoji (2 on auth cards, 2 in headers)
replace('<div class="auth-brand"><span aria-hidden="true">🧭</span> Roadmap Tracker</div>',
        '<div class="auth-brand"><img class="brand-mark" src="img/logo.svg" alt="" width="24" height="24" /> Roadmap Tracker</div>', 0)
replace('<span class="brand-icon" aria-hidden="true">🧭</span>',
        '<img class="brand-mark" src="img/logo.svg" alt="" width="28" height="28" />', 0)

# 3. Account menu: "Theme" -> "Appearance" and a System option
replace('<span class="profile-panel-label">Theme</span>', '<span class="profile-panel-label">Appearance</span>')
replace('''                <button class="profile-theme-btn" id="themeDarkBtn" data-theme="dark">Dark</button>''',
        '''                <button class="profile-theme-btn" id="themeDarkBtn" data-theme="dark">Dark</button>
                <button class="profile-theme-btn" id="themeSystemBtn" data-theme="system">System</button>''')

# 4. Menu panels are labelled groups, not role="menu" (they hold mixed controls)
replace('id="profileTrigger" aria-haspopup="true" aria-expanded="false" aria-label="Account menu"',
        'id="profileTrigger" aria-expanded="false" aria-controls="profilePanel" aria-label="Account menu"')
replace('id="profilePanel" role="menu"', 'id="profilePanel" role="group" aria-label="Account"')
replace('id="roadmapMenuTrigger" aria-haspopup="true" aria-expanded="false" aria-label="Roadmap settings"',
        'id="roadmapMenuTrigger" aria-expanded="false" aria-controls="roadmapMenuPanel" aria-label="Roadmap settings"')
replace('id="roadmapMenuPanel" role="menu"', 'id="roadmapMenuPanel" role="group" aria-label="Roadmap settings"')

# 5. Icon script before the data script
replace('<script src="data/roadmap.js"></script>', '<script src="js/icons.js"></script>\n<script src="data/roadmap.js"></script>')

open(P, "w", encoding="utf-8").write(s)
assert "🧭" not in s, "an emoji brand mark is still present"
print("index.html updated")
```

## Appendix B3 — `step_appjs.py` (Task 11)

Run from the repo root: `python3 step_appjs.py`.

```python
"""Phase 0 / js/app.js. Run from the repo root: python3 step_appjs.py"""
import re

P = "js/app.js"
s = open(P, encoding="utf-8").read()


def replace(old, new):
    global s
    assert s.count(old) == 1, f"expected exactly one match ({s.count(old)} found): {old[:80]}"
    s = s.replace(old, new)


# 1. The theme key now lives in js/theme-boot.js
m = re.search(r'\n  const THEME_KEY = "roadmap-dashboard:theme";', s)
assert m, "THEME_KEY constant not found"
s = s.replace(m.group(0), "")

# 2. applyTheme/initTheme -> keep the menu buttons in sync with window.Theme
a = s.index("  function applyTheme(theme) {")
b = s.index("  // ---------------------------------------------------------\n  // Export / Import / Reset")
s = s[:a] + '''  // The saved choice (light / dark / system) lives in js/theme-boot.js, which
  // also applies it before first paint. Here we only keep the menu buttons in sync.
  const THEME_BUTTONS = { light: "themeLightBtn", dark: "themeDarkBtn", system: "themeSystemBtn" };

  function syncThemeButtons() {
    const mode = window.Theme.get();
    Object.entries(THEME_BUTTONS).forEach(([value, id]) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.classList.toggle("active", value === mode);
      btn.setAttribute("aria-pressed", String(value === mode));
    });
  }
  function initTheme() {
    window.Theme.onChange(syncThemeButtons);
    syncThemeButtons();
  }

''' + s[b:]

# 3. Button handlers
a = s.index('    $("themeLightBtn").addEventListener("click"')
b = s.index("    // Search (tab bar, roadmap only)")
s = s[:a] + '''    Object.entries(THEME_BUTTONS).forEach(([value, id]) => {
      $(id).addEventListener("click", () => window.Theme.set(value));
    });

''' + s[b:]

# 4. Confetti honours "reduce motion"
replace('''    toast(`🎉 Month complete: ${phaseTitle}!`, "celebrate");
    const canvas''', '''    toast(`🎉 Month complete: ${phaseTitle}!`, "celebrate");
    // Honour the OS "reduce motion" setting: the toast alone is the celebration.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas''')

# 5. "YOU ARE HERE" (all caps) -> "Current" (2 occurrences)
assert s.count("YOU ARE HERE") == 2, "expected 2 occurrences of YOU ARE HERE"
s = s.replace("YOU ARE HERE", "Current")

# 6. Accessible names for form controls that had none
replace('''  function statusSelect(id, status) {
    return `<select class="status-select" data-action="set-status" data-id="${id}">''',
'''  function statusSelect(id, status) {
    const entry = indexEntry(id);
    const label = entry ? `Status: ${entry.title}` : "Status";
    return `<select class="status-select" data-action="set-status" data-id="${id}" aria-label="${esc(label)}">''')
replace('<select class="select-filter" data-action="filter-phase">',
        '<select class="select-filter" data-action="filter-phase" aria-label="Filter by month">')
replace('<select class="select-filter" data-action="kanban-phase">',
        '<select class="select-filter" data-action="kanban-phase" aria-label="Month">')
replace('<input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${sk.id}" ${getItem(sk.id).status === "completed" ? "checked" : ""} />',
        '<input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${sk.id}" aria-label="${esc(sk.title)}" ${getItem(sk.id).status === "completed" ? "checked" : ""} />')

# 7. Initialise theme (unchanged call site: initTheme() already runs in init())
assert "initTheme();" in s

open(P, "w", encoding="utf-8").write(s)
print("js/app.js updated")
```

## Appendix B4 — `step_server.py` (Task 12)

Run from the repo root: `python3 step_server.py`.

```python
"""Phase 0 / server/app.js + test/api.test.js. Run from the repo root: python3 step_server.py"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match for: {old[:70]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("server/app.js", [(
'''  app.use("/js", express.static(path.join(staticRoot, "js")));''',
'''  app.use("/js", express.static(path.join(staticRoot, "js")));
  // Self-hosted fonts and the logo/favicon. Fonts never change for a given file
  // name, so let browsers cache them for a year.
  app.use("/fonts", express.static(path.join(staticRoot, "fonts"), { maxAge: "365d", immutable: true }));
  app.use("/img", express.static(path.join(staticRoot, "img")));''')])

patch("test/api.test.js", [
('''    assert.equal((await c.get("/data/roadmap.js")).status, 200);
    for (const p of ["/data/app.db",''',
'''    assert.equal((await c.get("/data/roadmap.js")).status, 200);
    for (const p of ["/css/tokens.css", "/css/base.css", "/css/components.css", "/js/theme-boot.js", "/js/icons.js",
                     "/img/logo.svg", "/img/favicon.svg", "/fonts/ibm-plex-sans-latin-400-normal.woff2"]) {
      assert.equal((await c.get(p)).status, 200, p);
    }
    for (const p of ["/fonts/", "/fonts/../.env", "/img/../package.json", "/data/app.db",'''),
('''  test("API responses are not cacheable", async () => {''',
'''  test("fonts are cacheable; the page forbids inline scripts", async () => {
    const font = await client(srv.base).get("/fonts/ibm-plex-sans-latin-400-normal.woff2");
    assert.match(font.headers.get("cache-control"), /max-age=31536000/);
    const page = await client(srv.base).get("/");
    const csp = page.headers.get("content-security-policy");
    assert.match(csp, /script-src 'self'/);
    assert.doesNotMatch(csp.split(";").find((d) => d.trim().startsWith("script-src")), /unsafe-inline/);
  });

  test("API responses are not cacheable", async () => {'''),
])
print("server/app.js and test/api.test.js updated")
```

## Appendix B5 — `step_docs.py` (Task 13)

Run from the repo root: `python3 step_docs.py`.

```python
"""Phase 0 / documentation. Run from the repo root: python3 step_docs.py"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match for: {old[:70]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("README.md", [
    ("- **Create roadmap with AI** is shown as *Coming soon*\n",
     "- **Create roadmap with AI** is shown as *Coming soon*\n"
     "- **Appearance** — Light, Dark or **System** (follows your operating system live); the choice is remembered per browser and applied before the page paints, so there is no flash\n"),
    ("├── css/\n│   └── styles.css                All styling (light + dark themes)\n│\n├── js/\n"
     "│   ├── app.js                    UI state, rendering, dashboard, autosave, auth\n",
     "├── css/\n"
     "│   ├── tokens.css                Design tokens: colour, radius, spacing (light + dark)\n"
     "│   ├── base.css                  Fonts, reset, typography, focus ring, reduced motion\n"
     "│   ├── components.css            Buttons, fields, chips, modal, toasts, …\n"
     "│   └── styles.css                Layout + per-view rules (shrinking during the redesign)\n"
     "├── fonts/                        IBM Plex Sans (self-hosted, SIL OFL)\n"
     "├── img/                          logo.svg, favicon.svg\n│\n├── js/\n"
     "│   ├── theme-boot.js             Light / Dark / System, applied before first paint (window.Theme)\n"
     "│   ├── icons.js                  Inline SVG icon set (window.Icons)\n"
     "│   ├── app.js                    UI state, rendering, dashboard, autosave, auth\n"),
    ("All 58 tests cover", "All 59 tests cover"),
    ("`/`, `/index.html`, `/css/*`, `/js/*`, `/data/roadmap.js`\n",
     "`/`, `/index.html`, `/css/*`, `/js/*`, `/fonts/*`, `/img/*`, `/data/roadmap.js`\n"),
    ("| Static allowlist | Only four path patterns serve files; `path.join` + `sendFile` prevent path-traversal. |",
     "| Static allowlist | Only an explicit list of paths serves files (`/`, `/css`, `/js`, `/fonts`, `/img`, `/data/roadmap.js`); `path.join` + `sendFile` prevent path-traversal. |\n"
     "| Content Security Policy | `helmet` default CSP: scripts only from `'self'` (no inline scripts), so the theme script is the external `js/theme-boot.js`. Fonts are self-hosted; no third-party requests. |"),
])
patch("documentation/low-level-design.md", [
    ("├── css/\n│   └── styles.css                 ← All UI styles (light + dark theme)",
     "├── css/\n"
     "│   ├── tokens.css                 ← Design tokens (light + dark) — see design-system.md\n"
     "│   ├── base.css                   ← Fonts, reset, focus ring, reduced motion\n"
     "│   ├── components.css             ← Buttons, fields, chips, modal, toasts\n"
     "│   └── styles.css                 ← Layout + per-view styles (shrinking)\n"
     "├── fonts/  img/                   ← Self-hosted IBM Plex Sans; logo and favicon"),
    ("Static allowlist                — index.html, css/, js/, data/roadmap.js",
     "Static allowlist                — index.html, css/, js/, fonts/, img/, data/roadmap.js"),
])
patch(".claude/PROJECT_WALKTHROUGH.md", [
    ("├── css/styles.css              All styles; light/dark theme via CSS vars",
     "├── css/                        tokens.css (design tokens, light/dark), base.css, components.css,\n"
     "│                               styles.css (layout + views, shrinking). See documentation/design-system.md\n"
     "├── fonts/ img/                 Self-hosted IBM Plex Sans; logo + favicon"),
    ("  └── static        → index.html, css/, js/, data/roadmap.js  (allowlist only)",
     "  └── static        → index.html, css/, js/, fonts/, img/, data/roadmap.js  (allowlist only)"),
    ("`index.html`, `css/*`, `js/*`, `data/roadmap.js`. The local",
     "`index.html`, `css/*`, `js/*`, `fonts/*`, `img/*`, `data/roadmap.js`. The local"),
    ("theme toggle (light/dark), start-month",
     "theme toggle (Light / Dark / System via `window.Theme`, `js/theme-boot.js`), start-month"),
])
print("docs updated")
```

## Appendix C1 — `serve-demo.js` (verification server; keep outside the repo)

```javascript
// Temporary verification server (NOT part of the repo). Usage:
//   node serve-demo.js <repo-root> [port]
// Boots the real app on an in-memory database with one demo user and some progress.
const path = require("node:path");
const root = path.resolve(process.argv[2] || ".");
const port = Number(process.argv[3] || 3111);
const { openDb } = require(path.join(root, "server/db"));
const { createApp } = require(path.join(root, "server/app"));

(async () => {
  const db = await openDb(":memory:");
  const app = createApp({
    db, sessionSecret: "x".repeat(40), bcryptCost: 4,
    authRateLimit: { windowMs: 60000, max: 10000 }, staticRoot: root,
  });
  app.listen(port, "127.0.0.1", async () => {
    const base = `http://127.0.0.1:${port}`;
    const r = await fetch(base + "/api/auth/register", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ username: "imkushwaha", password: "demo-pass-123", firstName: "Upendra", lastName: "Kumar" }),
    });
    const cookie = (r.headers.get("set-cookie") || "").split(";")[0];
    const list = await (await fetch(base + "/api/roadmaps", { headers: { cookie } })).json();
    const id = list.roadmaps[0].id;
    const data = require(path.join(root, "data/roadmap.json"));
    const items = {};
    let n = 0;
    data.phases.slice(0, 1).forEach((p) => p.sections.forEach((s) => s.topics.forEach((t) => t.groups.forEach((g) => g.subtasks.forEach((st) => {
      n += 1;
      if (n % 3 !== 0) items[st.id] = { status: "completed", completedAt: new Date(Date.now() - (n % 20) * 86400000).toISOString() };
      else if (n % 7 === 0) items[st.id] = { status: "in_progress" };
    })))));
    data.phases.slice(1, 2).forEach((p) => p.sections.forEach((s) => s.topics.forEach((t) => t.groups.forEach((g) => g.subtasks.forEach((st, i) => {
      if (i === 0) items[st.id] = { status: "completed", completedAt: new Date().toISOString() };
      else if (i === 1) items[st.id] = { status: "blocked" };
      else if (i === 2) items[st.id] = { status: "in_progress" };
    })))));
    const put = await fetch(`${base}/api/roadmaps/${id}/progress`, {
      method: "PUT", headers: { "content-type": "application/json", cookie },
      body: JSON.stringify({ version: 0, data: { items, counters: {}, celebratedPhases: [], settings: { startMonth: "2026-10" }, custom: { topics: [], phases: [] } } }),
    });
    console.log(`ready on ${base} (seed ${put.status}, ${Object.keys(items).length} items). Login: imkushwaha / demo-pass-123`);
  });
})();
```

## Appendix C2 — `verify_phase0.py` (verification harness; keep outside the repo)

```python
"""Phase 0 verification. Usage:
    python3 verify_phase0.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Requires: python3 -m pip install playwright && python3 -m playwright install chromium
          npm install --prefix /tmp/ui-verify axe-core      (provides AXE_JS_PATH)
Exit code 0 only if every check passes. Screenshots are written for human review."""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots"
os.makedirs(SHOTS, exist_ok=True)

results = []


def check(ok, message):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + message)


AXE_SOURCE = None


def axe_violations(page):
    # The app's Content Security Policy blocks <script> injection, but evaluating the
    # source through the DevTools protocol is allowed - and keeps CSP errors detectable.
    global AXE_SOURCE
    if AXE_SOURCE is None:
        AXE_SOURCE = open(AXE, encoding="utf-8").read()
    page.evaluate(AXE_SOURCE)
    return page.evaluate("""async () => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] } });
      return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0] && v.nodes[0].target.join(' ')));
    }""")


def audit(page, label):
    v = axe_violations(page)
    check(not v, f"axe 0 violations: {label}" + ("" if not v else "  -> " + "; ".join(v)))


def login(page):
    page.goto(BASE)
    page.wait_for_selector("#authForm", state="visible")
    page.fill("#authUsername", "imkushwaha")
    page.fill("#authPassword", "demo-pass-123")
    page.click("#authSubmit")
    page.wait_for_selector(".roadmap-card", timeout=10000)


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---- A. Assets, tokens, fonts, theme (light OS) ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="light")
    page = ctx.new_page()
    problems = []
    page.on("pageerror", lambda e: problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" and "401" not in m.text else None)
    page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{window.__earlyTheme=document.documentElement.getAttribute('data-theme')})")

    for path in ("/css/tokens.css", "/css/base.css", "/css/components.css", "/js/theme-boot.js", "/js/icons.js",
                 "/img/logo.svg", "/img/favicon.svg",
                 "/fonts/ibm-plex-sans-latin-400-normal.woff2", "/fonts/ibm-plex-sans-latin-500-normal.woff2",
                 "/fonts/ibm-plex-sans-latin-600-normal.woff2"):
        check(page.request.get(BASE + path).status == 200, f"asset served: {path}")
    for path in ("/.env", "/data/app.db", "/server/app.js", "/fonts/", "/package.json"):
        check(page.request.get(BASE + path).status == 404, f"not served (404): {path}")

    page.goto(BASE)
    page.wait_for_selector("#authForm", state="visible")
    page.wait_for_timeout(400)
    page.screenshot(path=f"{SHOTS}/login-light.png")
    root_style = lambda name: page.evaluate(f"getComputedStyle(document.documentElement).getPropertyValue('{name}').trim().toLowerCase()")
    check(root_style("--accent") == "#2b50d8", "token --accent is #2b50d8 in light theme")
    check(root_style("--text-faint") == "#5f6a7d", "token --text-faint is #5f6a7d")
    check(page.evaluate("document.fonts.check('14px \"IBM Plex Sans\"')"), "IBM Plex Sans is loaded")
    check("IBM Plex Sans" in page.evaluate("getComputedStyle(document.body).fontFamily"), "body uses IBM Plex Sans")
    check(page.evaluate("document.documentElement.getAttribute('data-theme')") == "light", "default System + light OS => data-theme=light")
    check(page.evaluate("localStorage.getItem('roadmap-dashboard:theme')") is None, "nothing stored until the user chooses")
    check(page.evaluate("document.querySelectorAll('script:not([src])').length") == 0, "no inline <script> in the page (CSP)")
    check("🧭" not in page.inner_text("body"), "no compass emoji left in visible text")
    check(page.locator("img.brand-mark").count() >= 1, "SVG brand mark present")

    login(page)
    page.screenshot(path=f"{SHOTS}/home-light.png")
    audit(page, "home (light)")
    page.click("#profileTrigger")
    check(page.locator("#themeSystemBtn").is_visible() and "Appearance" in page.inner_text("#profilePanel"), "account menu has Appearance with a System option")
    page.screenshot(path=f"{SHOTS}/menu-light.png")
    audit(page, "account menu (light)")

    # theme behaviour
    theme = lambda: page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.click("#themeDarkBtn")
    check(theme() == "dark" and page.evaluate("localStorage.getItem('roadmap-dashboard:theme')") == "dark", "Dark: applied and remembered")
    check(page.evaluate("document.querySelector('.profile-theme-btn.active').id") == "themeDarkBtn", "active theme button follows the choice")
    page.reload(); page.wait_for_selector(".roadmap-card", timeout=10000)
    check(page.evaluate("window.__earlyTheme") == "dark", "after reload the theme was applied BEFORE app scripts ran (no flash)")
    page.click("#profileTrigger"); page.click("#themeSystemBtn")
    check(theme() == "light", "System with light OS => light")
    page.emulate_media(color_scheme="dark"); page.wait_for_timeout(250)
    check(theme() == "dark", "System follows the OS live (OS -> dark)")
    page.click("#themeLightBtn"); page.emulate_media(color_scheme="dark"); page.wait_for_timeout(100)
    check(theme() == "light", "explicit Light ignores the OS")
    page.click("#themeSystemBtn"); page.keyboard.press("Escape")
    page.emulate_media(color_scheme="light")

    # open roadmap + every view, light
    page.click("[data-action=open-roadmap]"); page.wait_for_selector(".stat-tile", timeout=10000)
    for view in ("overview", "timeline", "kanban", "checklist", "thisweek", "mastery", "reference"):
        page.click(f'.tab[data-view="{view}"]'); page.wait_for_timeout(250)
        check(page.inner_text("#main").strip() != "", f"view renders: {view}")
        page.screenshot(path=f"{SHOTS}/{view}-light.png")
        audit(page, f"{view} (light)")
    check(not problems, "no page errors or CSP/console errors" + ("" if not problems else ": " + str(problems[:3])))
    ctx.close()

    # ---- B. Dark theme audit of the same screens ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
    page = ctx.new_page()
    page.goto(BASE); page.wait_for_selector("#authForm", state="visible")
    check(page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark", "dark OS => data-theme=dark on first load")
    check(root_style("--accent") == "#6c8cff", "token --accent is #6c8cff in dark theme")
    page.screenshot(path=f"{SHOTS}/login-dark.png")
    audit(page, "login (dark)")
    login(page); audit(page, "home (dark)")
    page.click("[data-action=open-roadmap]"); page.wait_for_selector(".stat-tile", timeout=10000)
    for view in ("overview", "timeline", "kanban", "checklist", "thisweek", "mastery", "reference"):
        page.click(f'.tab[data-view="{view}"]'); page.wait_for_timeout(250)
        if view in ("overview", "kanban", "checklist"):
            page.screenshot(path=f"{SHOTS}/{view}-dark.png")
        audit(page, f"{view} (dark)")
    ctx.close()

    # ---- C. Reduced motion ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page(); page.goto(BASE); page.wait_for_selector("#authForm", state="visible")
    check(page.evaluate("getComputedStyle(document.getElementById('confettiCanvas')).display") == "none", "reduced motion hides the confetti canvas")
    check(page.evaluate("parseFloat(getComputedStyle(document.getElementById('authSubmit')).transitionDuration) < 0.01"), "reduced motion removes transitions")
    ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
```

---

*End of Phase 0 spec. Phase 1 (Log in / Create account) is specified separately.*
