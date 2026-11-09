# Phase 1 — Log in and Create account: Implementation Spec

> **Audience:** an AI coding agent (or developer) implementing this phase in the *Roadmap Tracker* repository.
> **Status of this spec:** every step below was executed on a copy of the original repository with Phase 0 applied, and verified (59/59 tests, 67/67 Phase 1 UI checks, 61/61 Phase 0 regression checks). If you follow it exactly you will get the same result.

| | |
|---|---|
| **Phase** | 1 of 5 — Authentication screens |
| **Depends on** | **Phase 0 completed and verified** (see Section 2) |
| **Branch** | continue on `feature/ui-redesign` |
| **Effort** | about 1.5 working days by hand; under an hour of agent time because every file and script is supplied |
| **Visible result** | Log in and Create account become a professional **split-screen**: a navy brand panel with a sample Month Strip on the left, the form on the right. Show/hide password, Caps Lock hint, live username and password checks, clear error banner. On phones and tablets the panel disappears and a compact logo sits above the form |
| **Risk** | Low–medium. Only auth markup, auth CSS and the auth section of `js/app.js` change. **No server, API, or database change.** |
| **Next phase** | Phase 2 — App shell, Home, `stats` API, hash routes (separate spec) |

---

## 0. Rules for the implementing agent (read first)

1. **Do exactly what this document says. Do not redesign.** Layout, copy, sizes and class names are decided.
2. **Phase 0 must already be applied.** If `css/tokens.css`, `js/theme-boot.js` or `js/icons.js` are missing, stop and report; do not recreate them here.
3. **No new npm dependencies, no build step.** Plain HTML, CSS and JavaScript only.
4. **Do not touch `server/`, `js/api.js`, `js/progress-schema.js`, the database, or any test file.** Phase 1 has no server change. The existing username-availability endpoint (`GET /api/auth/check-username`) is **reused**.
5. **Keep every existing element ID** listed in Section 5.1. `js/app.js` looks elements up by ID; renaming one breaks the app silently.
6. **The app has one auth form** (`#authForm`) that switches between log in and create account (`setAuthMode`). Keep it that way — do **not** create two forms or two screens.
7. **Security rules still apply** (`CLAUDE.md`): user-supplied text is escaped (`esc()` / `textContent`); no tokens or personal data in `localStorage`; the Content Security Policy forbids inline scripts, `eval` and remote assets. Never reveal whether a username or password was the wrong one (the server already returns the single message "Invalid credentials" — display it as is).
8. **If a script in this spec fails an `assert`**, the repository has drifted. Do not force it. Read that script's "Intent" list, apply the equivalent edit by hand, and record the difference in your hand-off notes.
9. **Run the verification (Section 7) before declaring done.** Commit in task order, one commit per task.

---

## 1. Goal and scope

### 1.1 Problems this phase fixes

| # | Problem today | Fix |
|---|---|---|
| 1 | A small card floats in a large empty canvas; no product identity | Split-screen layout with a brand panel (desktop) |
| 2 | Uneven vertical spacing; fields have no visible border at rest | 4px spacing scale; bordered 40px inputs with a clear focus ring (Phase 0 tokens) |
| 3 | No show/hide password, no Caps Lock hint | Both added |
| 4 | Sign-up calls the field "User ID" while login says "Username" | **Username** everywhere |
| 5 | Rules appear far below the fields in grey text | Permanent hint under the username; live password checklist |
| 6 | Six stacked fields make sign-up tall | First and last name side by side; fits a 1440×768 laptop screen |
| 7 | Error text is a small coloured line | Banner above the fields (`role="alert"`); focus moves to the first invalid field |
| 8 | A five-credit footer competes with the form | One quiet line; extra credits in an expandable "About this project" |
| 9 | Hint messages use ✓ / ✗ text glyphs | Plain sentences; icons drawn by CSS |

### 1.2 Deliverables

| # | Deliverable | File |
|---|---|---|
| 1 | Month Strip component (first use: the brand-panel illustration) | `js/month-strip.js` (new) + styles appended to `css/components.css` |
| 2 | Auth stylesheet | `css/auth.css` (new) |
| 3 | New auth markup (brand panel + form column + footer) | `index.html` |
| 4 | Old auth CSS removed | `css/styles.css` |
| 5 | Auth behaviour: modes, validation, hints, show/hide, Caps Lock, loading button, success toast | `js/app.js` |
| 6 | Documentation | `README.md`, `documentation/low-level-design.md`, `documentation/design-system.md` |

### 1.3 Out of scope (do NOT do these here)

- The in-app **About dialog**, app shell, Home page, hash routes, `stats` API (Phase 2). The auth footer keeps the Claude and open-source credits in an expandable `<details>` until then.
- **Forgot password / email / social login.** The backend has none; do not add UI for them.
- Changing messages returned by the server, rate limits, or password rules (8+ characters, username 3–32 of letters, numbers, `_`, `-`).
- Replacing emoji outside the auth screen.

---

## 2. Preconditions

**Phase 0 must be in place.** Confirm all of these before starting:

```bash
git status                       # on feature/ui-redesign, clean
npm test                         # expect: tests 59, pass 59, fail 0
ls css/tokens.css css/base.css css/components.css js/theme-boot.js js/icons.js img/logo.svg fonts/*.woff2
grep -c "window.Theme" js/app.js # expect: a number greater than 0
```

Phase 0 supplies what this phase uses: design tokens (`--bg-brand`, `--border-strong`, `--status-*`, `--accent*`), `.btn`, `.btn-primary`, `.btn-lg`, `.link-btn`, `.field`, `.is-loading`, `.hidden`, `.modal-actions`, `window.Icons.svg()`, the static allowlist for `/css` `/js` `/img` `/fonts`.

### 2.1 How the auth screen works today (facts you must respect)

- `index.html` has `#authScreen` (a full-screen overlay) containing **`#authForm`** (log in / create account) and **`#authBlock`** (a status card used for "Loading…", "Can't reach the server", "Couldn't load this roadmap" with buttons). Exactly one of the two is visible; the code toggles the `hidden` class.
- `setAuthMode("login" | "register")` shows or hides the register-only fields (`#authRegisterFields`, `#authConfirmPasswordField`) and changes the texts.
- `showAuth(mode, notice, opts)` shows the screen (optionally with a notice paragraph `#authNotice` and the **"Download my unsaved changes"** link `#authDownload` after a session expiry). `showBlock(title, text, buttons)` shows `#authBlock`.
- `submitAuth` calls `AuthApi.login` / `AuthApi.register`; errors from the server are shown as plain text (`e.message`). `AuthApi.checkUsername(value)` returns `{ available }`.
- Registration: username `^[A-Za-z0-9_-]{3,32}$`, password at least 8 characters, names required. The server already enforces this; the client checks first.
- `document.body.classList` has `locked` while auth/status is showing.

---

## 3. Design specification

### 3.1 Layout

**Desktop (viewport ≥ 1024px): split screen**

```
┌─────────────────────────────────┬──────────────────────────────────────────┐
│  BRAND PANEL  (45%, min 480px)  │  FORM COLUMN  (the rest)                 │
│  background: --bg-brand         │  background: --bg                        │
│                                 │                                          │
│  [logo] Roadmap Tracker         │                                          │
│                                 │              Log in                      │
│  Turn a learning goal into      │              Welcome back. Pick up       │
│  a plan you can finish.         │              where you left off.         │
│                                 │                                          │
│  Every account starts with a    │              Username                    │
│  10-month Production AI         │              [__________________]        │
│  Engineer roadmap. Build your   │              Password                    │
│  own plan whenever you need one.│              [__________________] [eye]  │
│                                 │                                          │
│  ┌───────────────────────────┐  │              [       Log in        ]     │
│  │ AI Engineer Roadmap       │  │                                          │
│  │ [▮][▮][▮][▮][▮] ... month │  │              New here? Create an account │
│  │ Oct Nov Dec Jan ... Jul   │  │                                          │
│  │ Month 3 of 10 · 29%       │  │  © 2026 Roadmap Tracker · Developed by … │
│  └───────────────────────────┘  │       About this project                 │
│  Open source. Contributions     │                                          │
│  welcome.                       │                                          │
└─────────────────────────────────┴──────────────────────────────────────────┘
```

- Form column: vertically centered, **max width 400px**, text left-aligned, footer centered at the bottom (max 640px).
- **Below 1024px** (tablet and phone): the brand panel is removed (`display: none`); a compact logo + "Roadmap Tracker" line (`.auth-brand-compact`) appears above the form. Padding 24px (12–16px on phones).
- Name fields share one row at ≥ 480px and stack below.
- Inputs are 40px tall (16px font under 640px, from Phase 0). The submit button is full width and 44px tall (`.btn.btn-primary.btn-lg.auth-submit`).

### 3.2 Brand panel (decorative)

- The whole `<aside class="auth-panel">` has `aria-hidden="true"`; it contains **no focusable elements**.
- Always dark in both themes (`--bg-brand`); inside it the status colours are pinned to their dark values so the strip stays legible.
- Exact copy:
  - Top: logo (28px) + "Roadmap Tracker"
  - Headline (32px/40px, 600): **Turn a learning goal into a plan you can finish.**
  - Text (15px): **Every account starts with a 10-month Production AI Engineer roadmap. Build your own plan whenever you need one.**
  - Demo card title: **AI Engineer Roadmap**, right label **Sample progress**
  - Caption: **Month 3 of 10 · 29% complete**
  - Bottom: **Open source. Contributions welcome.**
- No fake testimonials, customer logos, or statistics other than the labelled sample.

**Sample data for the illustration** (hard-coded; computed in `renderAuthPanelStrip`; 100 tasks per month, so the numbers are percentages):

| Month | Oct | Nov | Dec | Jan | Feb | Mar | Apr | May | Jun | Jul |
|---|---|---|---|---|---|---|---|---|---|---|
| Completed | 100 | 100 | 62 | 24 | 0 | 0 | 0 | 0 | 0 | 0 |
| In progress | 0 | 0 | 14 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| Current month | | | **yes** | | | | | | | |

The caption's 29% is `(100+100+62+24)/1000`. If you change the sample, change the caption to match.

### 3.3 Month Strip component (first use)

One segment per month; each segment is a stacked bar of that month's tasks.

| Aspect | Spec |
|---|---|
| API | `MonthStrip.html(months, { size: "sm" \| "md" \| "lg", labels: false, animate: false })` → HTML string |
| Month object | `{ label, title, total, completed, inProgress, blocked, current }` (all numbers optional; junk becomes 0) |
| Parts | completed `--status-completed`, in progress `--status-in-progress`, blocked `--status-blocked`, remaining = track colour (`--bg-sunken` with a 1px inset border) |
| Sizes | `sm` 4px (sidebar), `md` 8px (cards), `lg` 14px (this panel, with `labels: true`) |
| Current month | accent underline (3px) and accent, bold label |
| More than 12 months | collapses to **one** continuous bar (labels hidden) |
| No months | dashed empty strip, `aria-label="No months yet"` |
| Accessibility | container `role="img"` with `aria-label` like "5 of 10 tasks complete across 2 months"; each segment has a `title` tooltip |
| Safety | **every text value is HTML-escaped inside the function** (labels, titles) |
| Motion | `animate: true` adds `.is-animated`: segments grow left-to-right once over 0.6s (disabled by reduced motion) |

### 3.4 Form behaviour

**Modes**

| Element | Log in | Create account |
|---|---|---|
| Heading `#authTitle` | Log in | Create your account |
| Subtitle `#authSubtitle` | Welcome back. Pick up where you left off. | Start with the 10-month AI Engineer roadmap, or build your own. |
| Names row `#authRegisterFields` | hidden | visible (First name, Last name) |
| Username label | Username | Username |
| Username rule `#authUsernameRule` | hidden | visible: "3 to 32 characters. Letters, numbers, _ and -" |
| Password requirements `#authPwRules` | hidden | visible: ○ At least 8 characters (turns ✓ green when met) |
| Confirm field `#authConfirmPasswordField` | hidden | visible |
| Submit label | Log in | Create account |
| Toggle text | New here? **Create an account** | Already have an account? **Log in** |
| Password `autocomplete` | `current-password` | `new-password` |

Switching modes: clears the error banner and hint states, resets show/hide to hidden, clears `aria-invalid`, and (when going back to log in) clears the register-only fields.

**Validation on submit** (first failing rule wins; message goes in `#authError`, the offending field gets `aria-invalid="true"` and keyboard focus)

| Order | Condition | Message | Focus |
|---|---|---|---|
| 1 | register, first name empty | Enter your first name. | `#authFirstName` |
| 2 | register, last name empty | Enter your last name. | `#authLastName` |
| 3 | username empty | register: Choose a username. / login: Enter your username. | `#authUsername` |
| 4 | register, not `^[A-Za-z0-9_-]{3,32}$` | Username must be 3 to 32 characters: letters, numbers, _ or -. | `#authUsername` |
| 5 | password empty | register: Choose a password. / login: Enter your password. | `#authPassword` |
| 6 | register, length < 8 | Password must be at least 8 characters. | `#authPassword` |
| 7 | register, confirm differs | Passwords don't match. | `#authConfirmPassword` |

Server errors (wrong credentials, rate limit, username taken, network) are shown **unchanged** in the same banner. **Never** reveal which of username/password was wrong.

**Live hints** (elements keep their IDs; the state is a CSS class on the element)

| Hint element | Text | Class |
|---|---|---|
| `#authUsernameStatus` | Checking availability… | `auth-field-hint checking` |
| | Username is available. | `auth-field-hint available` (green, check icon) |
| | That username is taken. | `auth-field-hint taken` (red, ✕ icon) |
| `#authPasswordMatch` | Passwords match. | `auth-field-hint match` |
| | Passwords don't match. | `auth-field-hint mismatch` |
| `#authRuleLength` (list item) | At least 8 characters | gains class `met` at ≥ 8 characters |

The availability check is debounced (400ms), runs only in register mode for 3+ valid characters, ignores stale responses, and silently shows nothing if the request fails. Icons are drawn by CSS masks (data-URI SVG) so the text stays plain.

**Password field:** a button inside the field (`#authPasswordToggle`, 32px, icon from `Icons.svg("eye" | "eye-off", {size: 18})`) toggles **both** password inputs between `password` and `text`; it carries `aria-pressed` and `aria-label` ("Show password" / "Hide password"). A hint `#authCapsHint` ("Caps Lock is on.") shows while Caps Lock is on (checked on `keydown`/`keyup` via `getModifierState("CapsLock")`) and hides on `blur`.

**Submit:** while sending, the button is disabled and shows the Phase 0 spinner (`.is-loading`); width does not change. On success the form returns to the existing flow (`enterDashboard`); after **registration** a success toast appears: **Account created. Your AI Engineer roadmap is ready.**

### 3.5 Footer

One quiet line (12px, muted): `© <year> Roadmap Tracker · Developed by <email> · GitHub: imkushwaha · If this tool helps you, please star the repo`, links underlined. Below it an expandable `<details class="auth-about"><summary>About this project</summary>` holds: *Built with planning & development assistance from **Claude** (Anthropic AI). Open source — contributions welcome.* `#authFooterYear` is filled by existing code.

### 3.6 Accessibility requirements

- Every input has a real `<label for>`; the heading `h2#authTitle` is the only heading in the form.
- `#authError` has `role="alert"` and **stays in the DOM when empty** (so screen readers announce changes); when empty it takes no space (`:empty` rule).
- `#authUsernameStatus` and `#authPasswordMatch` have `aria-live="polite"`.
- After a failed submit, focus moves to the first invalid field.
- All text/background pairs pass WCAG 2.2 AA in light and dark; touch targets ≥ 44px for the main button, 32px for the inline toggle.
- No horizontal scrolling at 320px width.

---

## 4. Tasks (do them in this order)

> Run every `python3 step1_*.py` from the **repository root**. Save the scripts to a temporary folder outside the repo and call them by path, or copy them to the repo root and delete them afterwards. **Do not commit them.**

### Task 1 — `js/month-strip.js`
Create the file with **Appendix A1** verbatim.
**Acceptance:** `node --check js/month-strip.js` passes.

### Task 2 — Month Strip styles
Run **Appendix B0** (`step1_components.py`). It appends the `.strip*` rules to the end of `css/components.css`.
**Intent (manual fallback):** append the Month Strip block (segments as flex columns; `.strip-seg` 8px with inset 1px border; `sm`/`lg` sizes; part colours from status tokens; current-month underline; dashed `.is-empty`; `.is-animated` keyframes `strip-grow`) to the end of `components.css`.
**Acceptance:** prints `css/components.css: Month Strip styles appended`.

### Task 3 — `css/auth.css`
Create the file with **Appendix A2** verbatim. It contains the layout, brand panel, form column, banner, hints, password toggle, password-rule checklist, icon masks (`--icon-check`, `--icon-x`) and footer.
**Acceptance:** file exists (117 lines).

### Task 4 — Remove the old auth rules from `css/styles.css`
Run **Appendix B1** (`step1_styles.py`).
**Intent:** delete everything between the comments `/* ---------------- Login / sync ---------------- */` and `/* ---------------- Custom months / sections ---------------- */` **except** the single rule `body.locked .app-header, body.locked main { display: none; }` (it must remain).
**Acceptance:** prints `css/styles.css: removed 49 lines of old auth rules`; `grep -n "auth-card\|auth-footer\|auth-field-hint" css/styles.css` prints nothing.

### Task 5 — New auth markup in `index.html`
Run **Appendix B2** (`step1_index.py`). It replaces everything from `<div id="authScreen"` up to (not including) `<div id="dashboardScreen"` with the new markup, adds `<link rel="stylesheet" href="css/auth.css" />` after `components.css`, and adds `<script src="js/month-strip.js"></script>` after `icons.js`.
**Intent:** the new `#authScreen` contains `.auth-layout` → `aside.auth-panel[aria-hidden]` + `section.auth-main` (`.auth-main-inner` with `form#authForm` and `div#authBlock`, then `footer.auth-footer`). All IDs in Section 5.1 must exist; `#authHint` is removed.
**Acceptance:** prints `index.html updated`.

### Task 6 — Auth behaviour in `js/app.js`
Run **Appendix B3** (`step1_appjs.py`).
**Intent:** (a) replace `setAuthMode` and add helpers `clearInvalid`, `failAuth`, `setPasswordVisible`, `updatePasswordRules`; (b) replace `submitAuth` with the validation table of 3.4, the loading button and the success toast; (c) change the hint texts to plain sentences; (d) wire the show/hide button, the live password-rule update and the Caps Lock hint; (e) add `renderAuthPanelStrip()` (sample data from 3.2) and call it from `init()` right after `initTheme()`.
**Acceptance:** prints `js/app.js updated`; `node --check js/app.js` passes; `grep -n "User ID\|authHint" js/app.js` prints nothing.

### Task 7 — Documentation (required by `CLAUDE.md`)
Run **Appendix B4** (`step1_docs.py`). It updates `README.md`, `documentation/low-level-design.md` and `documentation/design-system.md` (adds the Month Strip section and marks Phase 1 done). Also copy this spec to `.claude/specs/ui-redesign-phase-1.md` (recommended).
**Acceptance:** prints `docs updated`.

### Task 8 — Verify
Follow Section 7. Everything must pass.

---

## 5. Contracts

### 5.1 Element IDs on the auth screen

| Status | IDs |
|---|---|
| **Kept (must exist)** | `authScreen`, `authForm`, `authTitle`, `authNotice`, `authRegisterFields`, `authFirstName`, `authLastName`, `authUsernameLabel`, `authUsername`, `authUsernameStatus`, `authPassword`, `authConfirmPasswordField`, `authConfirmPassword`, `authPasswordMatch`, `authError`, `authSubmit`, `authToggleText`, `authToggle`, `authDownload`, `authBlock`, `authBlockTitle`, `authBlockText`, `authBlockActions`, `authFooterYear` |
| **New** | `authSubtitle`, `authUsernameRule`, `authCapsHint`, `authPwRules`, `authRuleLength`, `authPasswordToggle`, `authPanelStrip` |
| **Removed** | `authHint` (its job is done by `authUsernameRule` and `authPwRules`) |

### 5.2 CSS classes introduced

`.auth-layout`, `.auth-panel` (+ `-top`, `-title`, `-text`, `-demo`, `-demo-head`, `-demo-foot`, `-foot`), `.auth-main`, `.auth-main-inner`, `.auth-card`, `.auth-brand`, `.auth-brand-compact`, `.auth-subtitle`, `.auth-notice`, `.auth-error`, `.field-row`, `.auth-submit`, `.auth-toggle`, `.input-affix`, `.input-affix-btn`, `.auth-field-hint` (+ `checking`, `available`, `taken`, `match`, `mismatch`), `.field-hint`, `.rules` (+ `li.met`), `.auth-footer`, `.auth-about`; Month Strip: `.strip`, `.strip-sm|md|lg`, `.strip-col`, `.strip-seg`, `.strip-part` (+ `is-done`, `is-progress`, `is-blocked`), `.strip-label`, `.is-current`, `.is-empty`, `.is-animated`.

### 5.3 `window.MonthStrip`
See 3.3. It is a pure function returning a string; it does not touch the DOM.

---

## 6. Acceptance criteria (checklist)

**Layout**
- [ ] Desktop 1440px: brand panel ≈ 45% wide (580–700px), form column ≤ 400px wide, panel contains a 10-segment strip labelled Oct…Jul with **Dec** marked current and the caption "29% complete".
- [ ] 820px and 390px: no brand panel; compact logo above the form; no horizontal scrolling.
- [ ] 390px: first/last name stack; inputs are 16px.
- [ ] Sign-up with hints visible fits a 1440×768 viewport without scrolling.

**Behaviour**
- [ ] Empty/incorrect submits show the exact messages of 3.4 in a `role="alert"` banner, set `aria-invalid`, and move focus.
- [ ] Wrong password shows "Invalid credentials" (server text); the form does not reveal which field was wrong.
- [ ] Show/hide password works for both password fields and updates `aria-pressed` / `aria-label`.
- [ ] Caps Lock hint appears and disappears correctly.
- [ ] Existing username → "That username is taken."; new username → "Username is available."; password rule turns met at 8 characters; match/mismatch hints correct.
- [ ] Successful sign-up lands on Home and shows "Account created. Your AI Engineer roadmap is ready."; log out and log in again works.
- [ ] The words "User ID" appear nowhere on the auth screen or in `js/app.js`.
- [ ] Session-expiry still shows the notice and the "Download my unsaved changes" link (`#authDownload`); "Loading…" and error panels (`#authBlock`) still work.

**Quality**
- [ ] axe-core WCAG 2.2 A/AA: **0 violations** on log in, log in with error, sign-up with hints (desktop light + dark, tablet, phone).
- [ ] No console errors / CSP violations (a single `401` before login is expected).
- [ ] `npm test` still 59/59; `git diff --stat` shows no changes under `server/` or `test/`, and none to `package.json` / `package-lock.json`, in the Phase 1 commits.
- [ ] Phase 0 harness still passes (61/61).
- [ ] Docs updated.

---

## 7. Verification

### 7.1 Automated

```bash
npm test      # expect: tests 59, pass 59, fail 0
```

### 7.2 UI harnesses (recommended)

Save **Phase 0 Appendix C1** (`serve-demo.js`) and **Phase 0 Appendix C2** (`verify_phase0.py`) plus this phase's **Appendix C1** (`verify_phase1.py`) into one folder **outside the repo** (e.g. `/tmp/ui-verify/`).

```bash
npm install --prefix /tmp/ui-verify axe-core
node /tmp/ui-verify/serve-demo.js "$(pwd)" 3111 &          # keep running
python3 /tmp/ui-verify/verify_phase1.py http://127.0.0.1:3111          # expect: RESULT 67/67
python3 /tmp/ui-verify/verify_phase0.py http://127.0.0.1:3111          # regression: expect RESULT 61/61
```

The harness creates one extra user per run (`p1user_…`) on the in-memory database; stop the server afterwards. PNGs are written to `/tmp/ui-verify/shots-p1`.

### 7.3 Visual checklist

| Screenshot | What you should see |
|---|---|
| `login-desktop-light.png` | Left: navy panel, logo, big headline, paragraph, a dark rounded card with a 10-segment strip (Oct–Jul, first two fully green, Dec partly green with an amber sliver, Jan a little green), blue underline under **Dec**, caption "Month 3 of 10 · 29% complete". Right: heading "Log in", subtitle, Username/Password fields with a thick blue ring on Username, an eye icon inside Password, a full-width blue button, "New here? Create an account", one-line footer and "About this project" |
| `login-error-desktop-light.png` | A red-bordered banner above the fields saying "Invalid credentials" |
| `signup-desktop-light.png` | Names side by side; permanent grey username rule; red ✕ "That username is taken." (if filled with the demo username); an empty circle "At least 8 characters"; red ✕ "Passwords don't match." under Confirm |
| `signup-phone-light.png` | Single column, no panel, compact logo on top, larger inputs |
| `*-dark.png` | Same layout; the form column is dark navy, the panel slightly different navy, blue button with dark text |

### 7.4 Known and acceptable

- A `⭐` may remain in old text elsewhere; none is in the new auth footer.
- On very short windows (< 700px high) the sign-up form scrolls inside the overlay; that is expected.
- The brand panel and the form column are close in colour in dark mode; a 1px border separates them.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| App shows a blank page / console `TypeError: Cannot read properties of null` | An element ID from 5.1 is missing in the new markup — compare against the table |
| Brand panel never shows on desktop | `css/auth.css` not linked, or viewport < 1024px |
| Strip is empty on the panel | `js/month-strip.js` loaded after `app.js`, or `renderAuthPanelStrip()` not called in `init()` |
| Hint icons (✓/✕) missing | `--icon-check` / `--icon-x` custom properties not defined (they live at the bottom of `auth.css`), or the CSP blocks `data:` images (default CSP allows them) |
| "Username is available." never appears | The check needs 3+ valid characters and runs 400ms after typing; ensure the server is reachable |
| Error banner not announced | `#authError` must keep `role="alert"` and must not be `display:none` when empty |
| Harness cannot inject axe | Do not use `add_script_tag`; evaluate the source (as the harness does) |
| A `step1_*.py` assertion fails | Repo drifted; apply the Intent list manually |

---

## 9. Hand-off

Report: commits, `npm test` result, both harness result lines, and any manual deviations.

**Phase 2 assumes** these exist and are unchanged: `window.MonthStrip` and the `.strip*` classes (used for roadmap cards and the sidebar), `.avatar`, `.skeleton`, `.btn*`, `.field*`, the auth element IDs in 5.1, `showAuth` / `showBlock` / `handleSessionExpired`, and `documentation/design-system.md`. Phase 2 moves the Claude/open-source credits into an in-app About dialog and keeps the auth footer as written here.

**Rollback:** revert the Phase 1 commits. No data, API or server change was made.

---

# Appendices


## Appendix A1 — `js/month-strip.js`

```javascript
/**
 * @module month-strip
 * The Month Strip: one segment per month of a roadmap, each a tiny stacked bar
 * of that month's tasks (completed · in progress · blocked · remaining).
 *
 *   MonthStrip.html(months, { size: "sm" | "md" | "lg", labels: false, animate: false })
 *
 * `months` is an array of
 *   { label: "Oct", title: "Month 1: Software Engineering Upgrade",
 *     total, completed, inProgress, blocked, current?: boolean }
 *
 * Returns an HTML string that is safe to insert with innerHTML: every text value
 * is escaped here. Styling lives in css/components.css (.strip*).
 * More than 12 months collapses into one continuous bar; no months renders a
 * dashed empty strip.
 */
(function () {
  "use strict";

  const MAX_SEGMENTS = 12;

  function esc(value) {
    return String(value).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  const num = (v) => (Number.isFinite(Number(v)) && Number(v) > 0 ? Number(v) : 0);

  function parts(m) {
    const total = num(m.total);
    if (!total) return "";
    const pct = (n) => Math.min(100, (num(n) / total) * 100).toFixed(2);
    return [
      ["is-done", m.completed],
      ["is-progress", m.inProgress],
      ["is-blocked", m.blocked],
    ].filter(([, n]) => num(n) > 0)
      .map(([cls, n]) => `<i class="strip-part ${cls}" style="flex-basis:${pct(n)}%"></i>`)
      .join("");
  }

  function summary(months) {
    const total = months.reduce((s, m) => s + num(m.total), 0);
    const done = months.reduce((s, m) => s + num(m.completed), 0);
    return `${done} of ${total} tasks complete across ${months.length} ${months.length === 1 ? "month" : "months"}`;
  }

  function collapse(months) {
    const sum = (key) => months.reduce((s, m) => s + num(m[key]), 0);
    return [{
      label: "", title: "All months", total: sum("total"), completed: sum("completed"),
      inProgress: sum("inProgress"), blocked: sum("blocked"), current: false,
    }];
  }

  function html(months, options) {
    const o = options || {};
    const size = ["sm", "md", "lg"].includes(o.size) ? o.size : "md";
    const list = Array.isArray(months) ? months : [];
    const cls = `strip strip-${size}${o.animate ? " is-animated" : ""}`;

    if (list.length === 0) {
      return `<div class="${cls} is-empty" role="img" aria-label="No months yet"></div>`;
    }
    const shown = list.length > MAX_SEGMENTS ? collapse(list) : list;
    const showLabels = o.labels && shown === list;
    const cols = shown.map((m) => `
      <div class="strip-col${m.current ? " is-current" : ""}">
        <div class="strip-seg" title="${esc(m.title || m.label || "")}">${parts(m)}</div>
        ${showLabels ? `<span class="strip-label">${esc(m.label || "")}</span>` : ""}
      </div>`).join("");
    return `<div class="${cls}" role="img" aria-label="${esc(summary(list))}">${cols}</div>`;
  }

  window.MonthStrip = { html };
})();
```

## Appendix A2 — `css/auth.css`

```css
/* ===========================================================
   Auth screens (log in, create account, status panel).
   Desktop: split screen, brand panel + form. Under 1024px the brand
   panel is dropped and a compact logo sits above the form.
   =========================================================== */

.auth-screen { position: fixed; inset: 0; z-index: 500; background: var(--bg); overflow-y: auto; }
.auth-layout { min-height: 100%; display: grid; grid-template-columns: 1fr; }

/* ---------------- Brand panel (desktop only, decorative) ---------------- */
.auth-panel { display: none; }
@media (min-width: 1024px) {
  .auth-layout { grid-template-columns: minmax(480px, 45%) 1fr; }
  .auth-panel {
    /* The panel is always dark, in both themes: pin the status colours to
       their dark-theme values so the strip stays legible on navy. */
    --status-completed: #3dbe84; --status-in-progress: #e0a33a; --status-blocked: #f0716a;
    display: flex; flex-direction: column; justify-content: space-between; gap: 48px;
    padding: 48px; background: var(--bg-brand); color: #fff;
    border-right: 1px solid rgb(255 255 255 / 0.08);
  }
}
.auth-panel-top { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 600; }
.auth-panel-top .brand-mark { width: 28px; height: 28px; box-shadow: 0 0 0 1px rgb(255 255 255 / 0.18); }
.auth-panel-title { margin: 0 0 16px; font-size: 32px; line-height: 40px; font-weight: 600; letter-spacing: -0.02em; max-width: 16em; }
.auth-panel-text { margin: 0 0 32px; font-size: 15px; line-height: 24px; color: rgb(255 255 255 / 0.74); max-width: 30em; }
.auth-panel-demo {
  padding: 20px; border-radius: var(--radius-md);
  background: rgb(255 255 255 / 0.05); border: 1px solid rgb(255 255 255 / 0.12); max-width: 520px;
}
.auth-panel-demo-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 16px; font-size: 14px; font-weight: 500; }
.auth-panel-demo-head span { font-size: 12px; font-weight: 400; color: rgb(255 255 255 / 0.6); }
.auth-panel-demo .strip-seg { background: rgb(255 255 255 / 0.1); box-shadow: none; }
.auth-panel-demo .strip-label { color: rgb(255 255 255 / 0.6); }
.auth-panel-demo .strip-col.is-current .strip-label { color: #fff; }
.auth-panel-demo .strip-col.is-current::after { background: #6c8cff; }
.auth-panel-demo-foot { margin: 16px 0 0; font-size: 13px; color: rgb(255 255 255 / 0.7); font-variant-numeric: tabular-nums; }
.auth-panel-foot { margin: 0; font-size: 13px; color: rgb(255 255 255 / 0.55); }

/* ---------------- Form column ---------------- */
.auth-main { display: flex; flex-direction: column; min-height: 100vh; padding: 24px 24px 0; }
.auth-main-inner {
  flex: 1; display: flex; flex-direction: column; justify-content: center;
  width: 100%; max-width: 400px; margin: 0 auto; padding: 24px 0;
}
.auth-card { width: 100%; }
.auth-brand { display: flex; align-items: center; gap: 10px; font-size: 15px; font-weight: 600; color: var(--text); margin-bottom: 24px; }
.auth-brand .brand-mark { width: 24px; height: 24px; border-radius: 6px; }
@media (min-width: 1024px) { .auth-brand-compact { display: none; } }

.auth-card h2 { margin: 0 0 4px; font-size: 24px; line-height: 32px; letter-spacing: -0.01em; }
.auth-subtitle { margin: 0 0 24px; font-size: 14px; color: var(--text-muted); }

.auth-notice {
  font-size: 13px; color: var(--text-muted); background: var(--bg-sunken);
  border-radius: var(--radius-sm); padding: 10px 12px; margin: 0 0 16px; line-height: 1.45;
}

/* Error banner stays in the DOM (so assistive tech announces it) but takes no space when empty. */
.auth-error {
  font-size: 13px; line-height: 1.45; color: var(--status-blocked);
  background: var(--status-blocked-bg); border: 1px solid var(--status-blocked);
  border-radius: var(--radius-sm); padding: 10px 12px; margin: 0 0 16px;
}
.auth-error:empty { padding: 0; border: 0; margin: 0; background: none; }

.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 479px) { .field-row { grid-template-columns: 1fr; gap: 0; } }

.auth-submit { width: 100%; margin-top: 8px; }
.auth-toggle { text-align: center; font-size: 14px; color: var(--text-muted); margin: 20px 0 0; }
#authDownload { display: block; margin: 16px auto 0; font-size: 13px; }

/* Show / hide password button sits inside the field */
.input-affix { position: relative; }
.field .input-affix input:not([type="checkbox"]):not([type="radio"]) { padding-right: 44px; }
.input-affix-btn {
  position: absolute; top: 4px; right: 4px; width: 32px; height: 32px;
  display: inline-flex; align-items: center; justify-content: center;
  border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--text-faint);
}
.input-affix-btn:hover { background: var(--bg-sunken); color: var(--text); }

/* Hints under fields. State classes are set from app.js. */
.auth-field-hint, .field-hint { font-size: 12px; line-height: 16px; margin: 6px 0 0; color: var(--text-faint); }
.auth-field-hint:empty { margin: 0; }
.auth-field-hint.checking { font-style: italic; }
.auth-field-hint.available, .auth-field-hint.match { color: var(--status-completed); }
.auth-field-hint.taken, .auth-field-hint.mismatch { color: var(--status-blocked); }
.auth-field-hint.available::before, .auth-field-hint.match::before,
.auth-field-hint.taken::before, .auth-field-hint.mismatch::before,
.rules li::before {
  content: ""; display: inline-block; width: 12px; height: 12px; margin-right: 6px; vertical-align: -1px;
  background: currentColor; -webkit-mask: var(--icon-x) center / contain no-repeat; mask: var(--icon-x) center / contain no-repeat;
}
.auth-field-hint.available::before, .auth-field-hint.match::before, .rules li.met::before {
  -webkit-mask-image: var(--icon-check); mask-image: var(--icon-check);
}
:root {
  --icon-check: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M20 6 9 17l-5-5'/%3E%3C/svg%3E");
  --icon-x: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M18 6 6 18M6 6l12 12'/%3E%3C/svg%3E");
}

/* Live password requirements (sign-up) */
.rules { list-style: none; margin: 8px 0 0; padding: 0; font-size: 12px; line-height: 18px; color: var(--text-faint); }
.rules li.met { color: var(--status-completed); }
.rules li:not(.met)::before { -webkit-mask-image: none; mask-image: none; background: none; border: 1.5px solid currentColor; border-radius: 50%; width: 10px; height: 10px; margin-right: 7px; vertical-align: -1px; }

/* ---------------- Footer: one quiet line ---------------- */
.auth-footer { width: 100%; max-width: 640px; margin: 0 auto; padding: 16px 0 20px; font-size: 12px; line-height: 18px; color: var(--text-faint); text-align: center; }
.auth-footer p { margin: 0; }
.auth-footer a { color: var(--text-muted); text-decoration: underline; text-underline-offset: 2px; }
.auth-footer a:hover { color: var(--accent); }
.auth-about { margin-top: 6px; }
.auth-about summary { display: inline; cursor: pointer; color: var(--text-muted); }
.auth-about summary:hover { color: var(--accent); }
.auth-about p { margin-top: 6px; }
```

## Appendix B0 — `step1_components.py` (Task 2)

Run from the repo root: `python3 step1_components.py`.

```python
"""Phase 1 / css/components.css: append the Month Strip styles.
Run from the repo root: python3 step1_components.py"""
P = "css/components.css"
s = open(P, encoding="utf-8").read()
assert "Month Strip (signature element)" not in s, "Month Strip styles already present"

BLOCK = r'''/* ---------------- Month Strip (signature element) ----------------
   One segment per month; each segment is a stacked bar of its tasks.
   Markup comes from js/month-strip.js. */
.strip { display: flex; gap: 4px; align-items: flex-start; width: 100%; }
.strip-col { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; align-items: stretch; gap: 6px; }
.strip-seg {
  display: flex; height: 8px; border-radius: 3px; overflow: hidden;
  background: var(--bg-sunken); box-shadow: inset 0 0 0 1px var(--border);
}
.strip-sm .strip-seg { height: 4px; border-radius: 2px; }
.strip-lg .strip-seg { height: 14px; border-radius: 4px; }
.strip-part { display: block; flex-grow: 0; flex-shrink: 0; height: 100%; }
.strip-part.is-done { background: var(--status-completed); }
.strip-part.is-progress { background: var(--status-in-progress); }
.strip-part.is-blocked { background: var(--status-blocked); }
.strip-label { font-size: 12px; line-height: 1; color: var(--text-faint); text-align: center; }
.strip-col.is-current .strip-label { color: var(--accent); font-weight: 600; }
.strip-col.is-current::after {
  content: ""; height: 3px; border-radius: 2px; background: var(--accent); margin-top: -2px;
}
.strip.is-empty {
  height: 8px; border-radius: 3px; border: 1px dashed var(--border-strong); background: transparent;
}
.strip-sm.is-empty { height: 4px; }
.strip-lg.is-empty { height: 14px; }

/* The one deliberate motion: segments fill left to right once on first load. */
.strip.is-animated .strip-part { transform-origin: left center; animation: strip-grow 0.6s ease-out both; }
@keyframes strip-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
'''

open(P, "w", encoding="utf-8").write(s.rstrip("\n") + "\n\n" + BLOCK)
assert ".strip-seg" in open(P, encoding="utf-8").read()
print("css/components.css: Month Strip styles appended")
```

## Appendix B1 — `step1_styles.py` (Task 4)

Run from the repo root: `python3 step1_styles.py`.

```python
"""Phase 1 / css/styles.css: remove the old auth rules (they now live in css/auth.css).
Run from the repo root: python3 step1_styles.py"""
P = "css/styles.css"
s = open(P, encoding="utf-8").read()

start = "/* ---------------- Login / sync ---------------- */"
end = "/* ---------------- Custom months / sections ---------------- */"
assert s.count(start) == 1 and s.count(end) == 1, "section markers not found"
a, b = s.index(start), s.index(end)
removed = s[a:b]
# Everything between the markers is auth styling EXCEPT the rule that hides the app while locked.
s = (s[:a]
     + start + "\nbody.locked .app-header, body.locked main { display: none; }\n\n"
     + s[b:])
assert "body.locked .app-header, body.locked main" in s
assert ".auth-card" not in s and ".auth-footer" not in s and ".auth-field-hint" not in s, "auth rules remain"
open(P, "w", encoding="utf-8").write(s)
print("css/styles.css: removed", len(removed.splitlines()), "lines of old auth rules")
```

## Appendix B2 — `step1_index.py` (Task 5)

Run from the repo root: `python3 step1_index.py`. The new auth markup is embedded in this script.

```python
"""Phase 1 / index.html: new split-screen auth markup + stylesheet and script tags.
Run from the repo root: python3 step1_index.py"""
P = "index.html"
s = open(P, encoding="utf-8").read()

NEW_AUTH = r'''<div id="authScreen" class="auth-screen hidden">
  <div class="auth-layout">
    <aside class="auth-panel" aria-hidden="true">
      <div class="auth-panel-top"><img class="brand-mark" src="img/logo.svg" alt="" width="28" height="28" /> Roadmap Tracker</div>
      <div>
        <p class="auth-panel-title">Turn a learning goal into a plan you can finish.</p>
        <p class="auth-panel-text">Every account starts with a 10-month Production AI Engineer roadmap. Build your own plan whenever you need one.</p>
        <div class="auth-panel-demo">
          <div class="auth-panel-demo-head">AI Engineer Roadmap <span>Sample progress</span></div>
          <div id="authPanelStrip"></div>
          <p class="auth-panel-demo-foot">Month 3 of 10 &middot; 29% complete</p>
        </div>
      </div>
      <p class="auth-panel-foot">Open source. Contributions welcome.</p>
    </aside>

    <section class="auth-main">
      <div class="auth-main-inner">
        <form id="authForm" class="auth-card" novalidate>
          <div class="auth-brand auth-brand-compact"><img class="brand-mark" src="img/logo.svg" alt="" width="24" height="24" /> Roadmap Tracker</div>
          <h2 id="authTitle">Log in</h2>
          <p id="authSubtitle" class="auth-subtitle">Welcome back. Pick up where you left off.</p>
          <p id="authNotice" class="auth-notice hidden"></p>
          <p id="authError" class="auth-error" role="alert"></p>

          <!-- Register-only fields (hidden during login) -->
          <div id="authRegisterFields" class="field-row hidden">
            <div class="field">
              <label for="authFirstName">First name</label>
              <input id="authFirstName" type="text" autocomplete="given-name" autocapitalize="words" maxlength="64" />
            </div>
            <div class="field">
              <label for="authLastName">Last name</label>
              <input id="authLastName" type="text" autocomplete="family-name" autocapitalize="words" maxlength="64" />
            </div>
          </div>

          <div class="field">
            <label id="authUsernameLabel" for="authUsername">Username</label>
            <input id="authUsername" type="text" autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="32" aria-describedby="authUsernameRule authUsernameStatus" />
            <p id="authUsernameRule" class="field-hint hidden">3 to 32 characters. Letters, numbers, _ and -</p>
            <p id="authUsernameStatus" class="auth-field-hint" aria-live="polite"></p>
          </div>

          <div class="field">
            <label for="authPassword">Password</label>
            <div class="input-affix">
              <input id="authPassword" type="password" autocomplete="current-password" maxlength="72" aria-describedby="authCapsHint authPwRules" />
              <button type="button" id="authPasswordToggle" class="input-affix-btn" aria-label="Show password" aria-pressed="false"></button>
            </div>
            <p id="authCapsHint" class="field-hint hidden">Caps Lock is on.</p>
            <ul id="authPwRules" class="rules hidden" aria-label="Password requirements">
              <li id="authRuleLength">At least 8 characters</li>
            </ul>
          </div>

          <!-- Confirm password — register only -->
          <div id="authConfirmPasswordField" class="field hidden">
            <label for="authConfirmPassword">Confirm password</label>
            <input id="authConfirmPassword" type="password" autocomplete="new-password" maxlength="72" />
            <p id="authPasswordMatch" class="auth-field-hint" aria-live="polite"></p>
          </div>

          <button id="authSubmit" class="btn btn-primary btn-lg auth-submit" type="submit">Log in</button>
          <p class="auth-toggle"><span id="authToggleText">New here?</span> <button type="button" id="authToggle" class="link-btn">Create an account</button></p>
          <button type="button" id="authDownload" class="link-btn hidden">Download my unsaved changes (JSON)</button>
        </form>
        <div id="authBlock" class="auth-card hidden">
          <div class="auth-brand auth-brand-compact"><img class="brand-mark" src="img/logo.svg" alt="" width="24" height="24" /> Roadmap Tracker</div>
          <h2 id="authBlockTitle"></h2>
          <p id="authBlockText" class="auth-notice"></p>
          <div id="authBlockActions" class="modal-actions"></div>
        </div>
      </div>

      <footer class="auth-footer">
        <p>&copy; <span id="authFooterYear"></span> Roadmap Tracker &middot;
          Developed by <a href="mailto:upendra.kumar48762@gmail.com">upendra.kumar48762@gmail.com</a> &middot;
          <a href="https://github.com/imkushwaha" target="_blank" rel="noopener">GitHub: imkushwaha</a> &middot;
          If this tool helps you, please <a href="https://github.com/imkushwaha" target="_blank" rel="noopener">star the repo</a></p>
        <details class="auth-about">
          <summary>About this project</summary>
          <p>Built with planning &amp; development assistance from <strong>Claude</strong> (Anthropic AI). Open source &mdash; contributions welcome.</p>
        </details>
      </footer>
    </section>
  </div>
</div>
'''

start = '<div id="authScreen"'
end = '<div id="dashboardScreen"'
assert s.count(start) == 1 and s.count(end) == 1, "auth/dashboard markers not found"
a, b = s.index(start), s.index(end)
s = s[:a] + NEW_AUTH.rstrip("\n") + "\n\n" + s[b:]

def once(old, new):
    global s
    assert s.count(old) == 1, "expected exactly one match: " + old[:70]
    s = s.replace(old, new)

once('<link rel="stylesheet" href="css/components.css" />',
     '<link rel="stylesheet" href="css/components.css" />\n<link rel="stylesheet" href="css/auth.css" />')
once('<script src="js/icons.js"></script>',
     '<script src="js/icons.js"></script>\n<script src="js/month-strip.js"></script>')

open(P, "w", encoding="utf-8").write(s)
for required in ('id="authForm"', 'id="authBlock"', 'id="authPasswordToggle"', 'id="authPanelStrip"', 'id="authFooterYear"',
                 'id="authUsernameStatus"', 'id="authPasswordMatch"', 'id="authDownload"'):
    assert required in s, "missing " + required
print("index.html updated")
```

## Appendix B3 — `step1_appjs.py` (Task 6)

Run from the repo root: `python3 step1_appjs.py`. The new JavaScript is embedded in this script.

```python
"""Phase 1 / js/app.js: auth form behaviour. Run from the repo root: python3 step1_appjs.py"""
P = "js/app.js"
s = open(P, encoding="utf-8").read()


def swap_block(start, end, new):
    """Replace everything from `start` up to (not including) `end`."""
    global s
    assert s.count(start) == 1, "start marker not unique/found: " + start[:60]
    a = s.index(start)
    b = s.index(end, a)
    s = s[:a] + new + s[b:]


def once(old, new):
    global s
    assert s.count(old) == 1, f"expected exactly one match ({s.count(old)} found): {old[:80]}"
    s = s.replace(old, new)


# 1. setAuthMode + helpers (username/password rules, show/hide password, invalid-field handling)
NEW_MODE = r'''  function setAuthMode(mode) {
    authMode = mode;
    const reg = mode === "register";
    $("authTitle").textContent = reg ? "Create your account" : "Log in";
    $("authSubtitle").textContent = reg
      ? "Start with the 10-month AI Engineer roadmap, or build your own."
      : "Welcome back. Pick up where you left off.";
    $("authSubmit").textContent = reg ? "Create account" : "Log in";
    $("authToggleText").textContent = reg ? "Already have an account?" : "New here?";
    $("authToggle").textContent = reg ? "Log in" : "Create an account";
    $("authUsernameRule").classList.toggle("hidden", !reg);
    $("authPwRules").classList.toggle("hidden", !reg);
    $("authPassword").autocomplete = reg ? "new-password" : "current-password";
    $("authError").textContent = "";
    $("authRegisterFields").classList.toggle("hidden", !reg);
    $("authConfirmPasswordField").classList.toggle("hidden", !reg);
    $("authUsernameStatus").textContent = "";
    $("authUsernameStatus").className = "auth-field-hint";
    $("authPasswordMatch").textContent = "";
    $("authPasswordMatch").className = "auth-field-hint";
    setPasswordVisible(false);
    clearInvalid();
    updatePasswordRules();
    if (!reg) {
      $("authFirstName").value = "";
      $("authLastName").value = "";
      $("authConfirmPassword").value = "";
    }
  }

  // ----- Auth form helpers -----
  const AUTH_FIELDS = ["authFirstName", "authLastName", "authUsername", "authPassword", "authConfirmPassword"];

  function clearInvalid() {
    AUTH_FIELDS.forEach((id) => $(id).removeAttribute("aria-invalid"));
  }

  // Show a message in the error banner, mark the field and move focus to it.
  function failAuth(message, fieldId) {
    $("authError").textContent = message;
    if (!fieldId) return;
    $(fieldId).setAttribute("aria-invalid", "true");
    $(fieldId).focus();
  }

  function setPasswordVisible(visible) {
    ["authPassword", "authConfirmPassword"].forEach((id) => { $(id).type = visible ? "text" : "password"; });
    const btn = $("authPasswordToggle");
    btn.setAttribute("aria-pressed", String(visible));
    btn.setAttribute("aria-label", visible ? "Hide password" : "Show password");
    btn.innerHTML = window.Icons.svg(visible ? "eye-off" : "eye", { size: 18 });
  }

  function updatePasswordRules() {
    $("authRuleLength").classList.toggle("met", $("authPassword").value.length >= 8);
  }

'''
swap_block("  function setAuthMode(mode) {", "  function showAuth(mode, notice, opts) {", NEW_MODE)

# 2. submitAuth: validation messages, focus handling, loading button, success toast
NEW_SUBMIT = r'''  async function submitAuth(ev) {
    ev.preventDefault();
    const username = $("authUsername").value.trim();
    const password = $("authPassword").value;
    $("authError").textContent = "";
    clearInvalid();
    const register = authMode === "register";
    const firstName = $("authFirstName").value.trim();
    const lastName = $("authLastName").value.trim();

    if (register && !firstName) { failAuth("Enter your first name.", "authFirstName"); return; }
    if (register && !lastName) { failAuth("Enter your last name.", "authLastName"); return; }
    if (!username) { failAuth(register ? "Choose a username." : "Enter your username.", "authUsername"); return; }
    if (register && !/^[A-Za-z0-9_-]{3,32}$/.test(username)) {
      failAuth("Username must be 3 to 32 characters: letters, numbers, _ or -.", "authUsername"); return;
    }
    if (!password) { failAuth(register ? "Choose a password." : "Enter your password.", "authPassword"); return; }
    if (register && password.length < 8) { failAuth("Password must be at least 8 characters.", "authPassword"); return; }
    if (register && password !== $("authConfirmPassword").value) {
      failAuth("Passwords don't match.", "authConfirmPassword"); return;
    }

    const btn = $("authSubmit");
    btn.disabled = true;
    btn.classList.add("is-loading");
    try {
      const res = register
        ? await window.AuthApi.register(firstName, lastName, username, password)
        : await window.AuthApi.login(username, password);
      $("authPassword").value = "";
      $("authConfirmPassword").value = "";
      session.expiredFor = null;
      enterDashboard(res.user);
      if (register) toast("Account created. Your AI Engineer roadmap is ready.", "success");
    } catch (e) {
      $("authError").textContent = e.message;
    } finally {
      btn.disabled = false;
      btn.classList.remove("is-loading");
    }
  }

'''
swap_block("  async function submitAuth(ev) {", "  async function boot() {", NEW_SUBMIT)

# 3. Field hints: plain-language text (icons come from CSS)
once('el.textContent = r.available ? "✓ Available" : "✗ Already taken";',
     'el.textContent = r.available ? "Username is available." : "That username is taken.";')
once('el.textContent = match ? "✓ Passwords match" : "✗ Passwords do not match";',
     'el.textContent = match ? "Passwords match." : "Passwords don\'t match.";')
once('el.textContent = "Checking…";', 'el.textContent = "Checking availability…";')

# 4. Password field: live rules, show/hide toggle, Caps Lock hint
once('    $("authPassword").addEventListener("input", updatePasswordMatch);',
     '''    $("authPassword").addEventListener("input", () => { updatePasswordMatch(); updatePasswordRules(); });
    $("authPasswordToggle").addEventListener("click", () => {
      setPasswordVisible($("authPassword").type === "password");
    });
    // Caps Lock hint on the password fields
    ["authPassword", "authConfirmPassword"].forEach((id) => {
      const field = $(id);
      const check = (e) => {
        if (typeof e.getModifierState !== "function") return;
        $("authCapsHint").classList.toggle("hidden", !e.getModifierState("CapsLock"));
      };
      field.addEventListener("keydown", check);
      field.addEventListener("keyup", check);
      field.addEventListener("blur", () => $("authCapsHint").classList.add("hidden"));
    });''')

# 5. Decorative sample strip on the brand panel
NEW_PANEL = r'''  // Decorative sample on the login brand panel (no real data).
  function renderAuthPanelStrip() {
    const sample = [
      [100, 0, 0], [100, 0, 0], [62, 14, 0], [24, 10, 0], [0, 0, 0],
      [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    ];
    const labels = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
    const months = sample.map(([completed, inProgress, blocked], i) => ({
      label: labels[i], title: `Month ${i + 1}`, total: 100, completed, inProgress, blocked, current: i === 2,
    }));
    $("authPanelStrip").innerHTML = window.MonthStrip.html(months, { size: "lg", labels: true });
  }

'''
once("  function wireSyncEvents() {", NEW_PANEL + "  function wireSyncEvents() {")
once("    initTheme();\n    wireEvents();", "    initTheme();\n    renderAuthPanelStrip();\n    wireEvents();")

open(P, "w", encoding="utf-8").write(s)
for required in ("function setPasswordVisible", "function updatePasswordRules", "function failAuth", "function renderAuthPanelStrip"):
    assert required in s, "missing " + required
assert "User ID" not in s, "old 'User ID' wording is still present"
assert "authHint" not in s, "reference to the removed #authHint element remains"
print("js/app.js updated")
```

## Appendix B4 — `step1_docs.py` (Task 7)

Run from the repo root: `python3 step1_docs.py`.

````python
"""Phase 1 / documentation. Run from the repo root: python3 step1_docs.py"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match for: {old[:70]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("README.md", [
    ("- **Appearance** — Light, Dark or **System**",
     "- **Log in / Create account** — split-screen layout (brand panel plus form), show/hide password, Caps Lock hint, live username-availability and password-requirement checks, errors announced to screen readers\n"
     "- **Appearance** — Light, Dark or **System**"),
    ("│   ├── components.css            Buttons, fields, chips, modal, toasts, …\n",
     "│   ├── components.css            Buttons, fields, chips, modal, toasts, Month Strip, …\n"
     "│   ├── auth.css                  Log in / Create account screens\n"),
    ("│   ├── icons.js                  Inline SVG icon set (window.Icons)\n",
     "│   ├── icons.js                  Inline SVG icon set (window.Icons)\n"
     "│   ├── month-strip.js            Month Strip component (window.MonthStrip)\n"),
])
patch("documentation/low-level-design.md", [
    ("│   ├── components.css             ← Buttons, fields, chips, modal, toasts\n",
     "│   ├── components.css             ← Buttons, fields, chips, modal, toasts, Month Strip\n"
     "│   ├── auth.css                   ← Log in / Create account screens\n"),
])
patch("documentation/design-system.md", [
    ("| `css/components.css` | Buttons, form fields, progress bar, badges, status chips, modal, toasts, skeleton, avatar, mini button |",
     "| `css/components.css` | Buttons, form fields, progress bar, badges, status chips, modal, toasts, skeleton, avatar, mini button, **Month Strip** |\n"
     "| `css/auth.css` | Log in / create-account screens (split layout, brand panel, field hints, footer) |"),
    ("| `js/icons.js` | Inline SVG icon set, `Icons.svg(name, { size, label })` (Lucide, ISC licence) |",
     "| `js/icons.js` | Inline SVG icon set, `Icons.svg(name, { size, label })` (Lucide, ISC licence) |\n"
     "| `js/month-strip.js` | `MonthStrip.html(months, { size, labels, animate })` |"),
    ("→ `components.css` → `styles.css`; scripts at the end: `icons.js`, `data/roadmap.js`",
     "→ `components.css` → `auth.css` → `styles.css`; scripts at the end: `icons.js`, `month-strip.js`, `data/roadmap.js`"),
    ("| 1 | Log in and create-account screens | Not started |", "| 1 | Log in and create-account screens | Done |"),
    ("## Motion and accessibility rules",
     """## Month Strip

One segment per month; each segment is a stacked bar of that month's tasks (completed, in progress, blocked, remaining). The current month gets an accent marker. More than 12 months collapses to one continuous bar; zero months shows a dashed empty strip. Output is escaped HTML with `role="img"` and a text summary (for example "152 of 849 tasks complete across 10 months"). Sizes: `"sm"` (4px), `"md"` (8px), `"lg"` (14px, optionally with month labels). `animate: true` plays the single entrance animation (segments fill left to right over 600ms; disabled by reduced motion).

```js
MonthStrip.html([
  { label: "Oct", title: "Month 1: Foundations", total: 100, completed: 60, inProgress: 10, blocked: 0, current: true },
], { size: "md", labels: false, animate: false });
```

## Motion and accessibility rules"""),
])
print("docs updated")
````

## Appendix C1 — `verify_phase1.py` (verification harness; keep outside the repo)

Uses `serve-demo.js` from Phase 0 (Appendix C1 of the Phase 0 spec).

```python
"""Phase 1 verification. Usage:
    python3 verify_phase1.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Needs the demo server from Phase 0 (serve-demo.js) running: user imkushwaha / demo-pass-123 exists.
Exit code 0 only if every check passes."""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots-p1"
os.makedirs(SHOTS, exist_ok=True)
NEW_USER = "p1user_%d" % (int(time.time()) % 1000000)
results = []
AXE_SOURCE = None


def check(ok, message):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + message)


def audit(page, label):
    global AXE_SOURCE
    if AXE_SOURCE is None:
        AXE_SOURCE = open(AXE, encoding="utf-8").read()
    page.evaluate(AXE_SOURCE)  # evaluating via DevTools works under the app's CSP (script tags do not)
    v = page.evaluate("""async () => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] } });
      return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0] && v.nodes[0].target.join(' ')));
    }""")
    check(not v, f"axe 0 violations: {label}" + ("" if not v else "  -> " + "; ".join(v)))


def new_page(browser, width, height, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
    page = ctx.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: page.problems.append(m.text) if m.type == "error" and "401" not in m.text else None)
    page.goto(BASE)
    page.wait_for_selector("#authForm", state="visible")
    return ctx, page


def box(page, selector):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height,b:r.bottom}; }", selector)


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---------- 1. Assets ----------
    ctx, page = new_page(browser, 1440, 900)
    for path in ("/css/auth.css", "/js/month-strip.js"):
        check(page.request.get(BASE + path).status == 200, f"asset served: {path}")

    # ---------- 2. Desktop layout (>= 1024px) ----------
    check(page.locator(".auth-panel").is_visible(), "desktop: brand panel visible")
    panel, form = box(page, ".auth-panel"), box(page, "#authForm")
    check(580 <= panel["w"] <= 700, f"desktop: brand panel is ~45% wide ({panel['w']:.0f}px of 1440)")
    check(form["w"] <= 401, f"desktop: form column max 400px ({form['w']:.0f}px)")
    check(not page.locator(".auth-brand-compact").first.is_visible(), "desktop: compact logo hidden (panel has the logo)")
    cols = page.locator("#authPanelStrip .strip-col")
    check(cols.count() == 10, "panel strip has 10 month segments")
    labels = [t.strip() for t in page.locator("#authPanelStrip .strip-label").all_inner_texts()]
    check(labels == ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"], f"strip labels Oct..Jul: {labels}")
    check(page.locator("#authPanelStrip .strip-col").nth(2).get_attribute("class").find("is-current") >= 0, "Dec is the marked current month")
    check("29% complete" in page.inner_text(".auth-panel-demo-foot"), "caption matches the sample data (29%)")
    check(page.get_attribute("#authPanelStrip .strip", "aria-label") is not None, "strip has an accessible summary")
    check(page.get_attribute(".auth-panel", "aria-hidden") == "true", "decorative brand panel is aria-hidden")
    check(page.evaluate("document.activeElement.id") == "authUsername", "username field is focused on load")
    check(page.evaluate("getComputedStyle(document.getElementById('authSubmit')).height") in ("44px",), "submit button is 44px high")
    page.screenshot(path=f"{SHOTS}/login-desktop-light.png")
    audit(page, "login (desktop, light)")

    # ---------- 3. Login behaviour ----------
    page.click("#authSubmit")
    check(page.inner_text("#authError") == "Enter your username." and page.get_attribute("#authUsername", "aria-invalid") == "true"
          and page.evaluate("document.activeElement.id") == "authUsername", "empty submit: banner + aria-invalid + focus on username")
    page.fill("#authUsername", "imkushwaha"); page.click("#authSubmit")
    check(page.inner_text("#authError") == "Enter your password." and page.evaluate("document.activeElement.id") == "authPassword", "missing password: banner + focus on password")
    page.fill("#authPassword", "wrong-wrong-1"); page.click("#authSubmit")
    page.locator("#authError", has_text="Invalid").wait_for(timeout=8000)
    check(True, "wrong password shows the server's error in the banner: " + page.inner_text("#authError"))
    check(page.get_attribute("#authError", "role") == "alert", "error banner is role=alert")
    page.screenshot(path=f"{SHOTS}/login-error-desktop-light.png")
    audit(page, "login with error banner (desktop, light)")
    check(page.get_attribute("#authPassword", "type") == "password" and page.get_attribute("#authPasswordToggle", "aria-label") == "Show password", "password hidden by default; toggle says 'Show password'")
    check(page.locator("#authPasswordToggle svg").count() == 1, "toggle shows an SVG icon")
    page.click("#authPasswordToggle")
    check(page.get_attribute("#authPassword", "type") == "text" and page.get_attribute("#authPasswordToggle", "aria-pressed") == "true"
          and page.get_attribute("#authPasswordToggle", "aria-label") == "Hide password", "toggle reveals the password and updates aria")
    page.click("#authPasswordToggle")
    check(page.get_attribute("#authPassword", "type") == "password", "toggle hides it again")
    # Caps Lock hint (simulated modifier state)
    page.evaluate("document.getElementById('authPassword').dispatchEvent(new KeyboardEvent('keydown', {key: 'a', modifierCapsLock: true, bubbles: true}))")
    check(page.locator("#authCapsHint").is_visible(), "Caps Lock hint appears when Caps Lock is on")
    page.evaluate("document.getElementById('authPassword').dispatchEvent(new KeyboardEvent('keyup', {key: 'a', modifierCapsLock: false, bubbles: true}))")
    check(not page.locator("#authCapsHint").is_visible(), "Caps Lock hint disappears when it is off")
    check(page.get_attribute("#authDownload", "class").find("hidden") >= 0, "'Download my unsaved changes' hidden during normal login")

    # ---------- 4. Create-account behaviour ----------
    page.click("#authToggle")
    check(page.inner_text("#authTitle") == "Create your account", "toggle switches the heading")
    check("10-month AI Engineer roadmap" in page.inner_text("#authSubtitle"), "sign-up subtitle")
    check(page.inner_text("#authUsernameLabel") == "Username", "label says 'Username' (not 'User ID')")
    check("User ID" not in page.inner_text("#authScreen"), "the words 'User ID' appear nowhere on the auth screen")
    check(page.locator("#authUsernameRule").is_visible() and "3 to 32 characters" in page.inner_text("#authUsernameRule"), "permanent username rule is visible")
    first, last = box(page, "#authFirstName"), box(page, "#authLastName")
    check(abs(first["y"] - last["y"]) < 2 and last["x"] > first["x"], "first and last name sit side by side")
    check(page.locator("#authError").inner_text() == "", "switching modes clears the error banner")
    check(page.get_attribute("#authPassword", "autocomplete") == "new-password", "password autocomplete = new-password in sign-up")
    page.fill("#authFirstName", "Ada"); page.fill("#authLastName", "Lovelace")
    page.fill("#authUsername", "imkushwaha")
    page.locator("#authUsernameStatus", has_text="taken").wait_for(timeout=5000)
    check("taken" in page.get_attribute("#authUsernameStatus", "class"), "existing username => 'That username is taken.' (state class taken)")
    page.fill("#authUsername", NEW_USER)
    page.locator("#authUsernameStatus", has_text="available").wait_for(timeout=5000)
    check("available" in page.get_attribute("#authUsernameStatus", "class"), "new username => 'Username is available.' (state class available)")
    page.fill("#authPassword", "short")
    check("met" not in page.get_attribute("#authRuleLength", "class"), "password rule not met under 8 characters")
    page.fill("#authPassword", "longenough1")
    check("met" in page.get_attribute("#authRuleLength", "class"), "password rule turns met at 8+ characters")
    page.fill("#authConfirmPassword", "different1")
    check(page.inner_text("#authPasswordMatch") == "Passwords don't match." and "mismatch" in page.get_attribute("#authPasswordMatch", "class"), "mismatch hint")
    page.screenshot(path=f"{SHOTS}/signup-desktop-light.png")
    audit(page, "sign-up with validation hints (desktop, light)")
    page.click("#authSubmit")
    check(page.inner_text("#authError") == "Passwords don't match." and page.evaluate("document.activeElement.id") == "authConfirmPassword"
          and page.get_attribute("#authConfirmPassword", "aria-invalid") == "true", "mismatch on submit: banner + focus + aria-invalid on confirm field")
    page.fill("#authConfirmPassword", "longenough1")
    check("match" in page.get_attribute("#authPasswordMatch", "class") and page.inner_text("#authPasswordMatch") == "Passwords match.", "match hint")

    # ---------- 5. Success: lands on Home with a toast ----------
    page.click("#authSubmit")
    page.wait_for_selector(".roadmap-card", timeout=10000)
    check(page.inner_text("#profileName") == "Ada Lovelace", "account created; signed in as Ada Lovelace")
    check(page.locator(".toast.success", has_text="Account created. Your AI Engineer roadmap is ready.").count() >= 1, "success toast shown")
    page.click("#profileTrigger"); page.click("#logoutBtn"); page.wait_for_selector("#authForm", state="visible")
    page.fill("#authUsername", NEW_USER); page.fill("#authPassword", "longenough1"); page.click("#authSubmit")
    page.wait_for_selector(".roadmap-card", timeout=10000)
    check(True, "log out and log in again with the new account")
    check(not page.problems, "no page errors or CSP/console errors" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # ---------- 6. Sign-up fits a laptop screen ----------
    ctx, page = new_page(browser, 1440, 768)
    page.click("#authToggle")
    page.fill("#authFirstName", "A"); page.fill("#authUsername", "abc"); page.fill("#authPassword", "x"); page.fill("#authConfirmPassword", "y")
    fits = page.evaluate("(() => { const s = document.getElementById('authScreen'); return s.scrollHeight <= s.clientHeight + 1; })()")
    check(fits, "sign-up form (with hints) fits a 1440x768 viewport without scrolling")
    ctx.close()

    # ---------- 7. Tablet and phone ----------
    for name, (w, h) in (("tablet", (820, 1000)), ("phone", (390, 844))):
        ctx, page = new_page(browser, w, h)
        check(not page.locator(".auth-panel").is_visible(), f"{name}: brand panel hidden")
        check(page.locator(".auth-brand-compact").first.is_visible(), f"{name}: compact logo shown above the form")
        overflow = page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        check(overflow, f"{name}: no horizontal scrolling")
        page.click("#authToggle")
        if name == "phone":
            first, last = box(page, "#authFirstName"), box(page, "#authLastName")
            check(last["y"] > first["y"], "phone: first and last name stack")
            inputs_ok = page.evaluate("parseFloat(getComputedStyle(document.getElementById('authUsername')).fontSize) >= 16")
            check(inputs_ok, "phone: inputs are 16px (no iOS zoom)")
        page.fill("#authFirstName", "A"); page.fill("#authUsername", "abc"); page.fill("#authPassword", "x"); page.fill("#authConfirmPassword", "y")
        page.screenshot(path=f"{SHOTS}/signup-{name}-light.png", full_page=True)
        audit(page, f"sign-up ({name}, light)")
        ctx.close()

    # ---------- 8. Dark theme ----------
    ctx, page = new_page(browser, 1440, 900, "dark")
    page.screenshot(path=f"{SHOTS}/login-desktop-dark.png")
    audit(page, "login (desktop, dark)")
    page.click("#authSubmit")
    audit(page, "login with error banner (desktop, dark)")
    page.click("#authToggle"); page.fill("#authUsername", "imkushwaha"); page.wait_for_timeout(700)
    page.fill("#authPassword", "short"); page.fill("#authConfirmPassword", "other")
    page.screenshot(path=f"{SHOTS}/signup-desktop-dark.png")
    audit(page, "sign-up with hints (desktop, dark)")
    ctx.close()

    # ---------- 9. MonthStrip component contract ----------
    ctx, page = new_page(browser, 1440, 900)
    ev = lambda js: page.evaluate(js)
    empty = ev("MonthStrip.html([])")
    check("is-empty" in empty and 'aria-label="No months yet"' in empty, "MonthStrip: empty list renders a dashed empty strip")
    two = ev("MonthStrip.html([{label:'A',total:10,completed:5},{label:'B',total:0,completed:0}], {size:'sm'})")
    check('aria-label="5 of 10 tasks complete across 2 months"' in two and "strip-sm" in two, "MonthStrip: accessible summary and size class")
    many = ev("MonthStrip.html(Array.from({length:13},(_, i)=>({label:'M'+i,total:10,completed:1})))")
    check(many.count("strip-col") == 1, "MonthStrip: more than 12 months collapses into one continuous bar")
    evil = ev("MonthStrip.html([{label:'<img src=x onerror=alert(1)>', title:'\"><script>1</script>', total:1, completed:1}], {labels:true})")
    check("<img" not in evil and "<script" not in evil and "&lt;img" in evil and "&lt;script&gt;" in evil,
          "MonthStrip: labels and titles are HTML-escaped")
    parts = ev("MonthStrip.html([{label:'x',total:10,completed:5,inProgress:3,blocked:2,current:true}])")
    check("is-done" in parts and "is-progress" in parts and "is-blocked" in parts and "is-current" in parts and "flex-basis:50.00%" in parts, "MonthStrip: stacked parts and current marker")
    bad = ev("MonthStrip.html([{label:'x',total:'abc',completed:-4,inProgress:NaN}])")
    check("strip-part" not in bad, "MonthStrip: junk numbers render no parts and do not throw")
    ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
```

---

*End of Phase 1 spec. Phase 2 (App shell, Home, stats API, hash routes) is specified separately.*
