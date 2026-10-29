# Login Page Update — Implementation Plan

**Session:** login-page-update  
**Branch:** feature/profile-section  
**Date:** 2026-10-29

---

## Overview

Three discrete areas of change:

1. **Registration form** — extended fields (first name, last name, user ID availability check, password + confirm-password with live match feedback)
2. **Footer banner** — full-width persistent banner on the login/auth screen covering copyright, attribution, GitHub, and Claude acknowledgement
3. **Profile display** — show full name (first + last) and user ID in the profile panel header

---

## Current State

| File | Relevant section |
|---|---|
| `index.html` | `#authScreen` / `#authForm` — one username + one password field |
| `js/app.js:1760–1841` | `setAuthMode`, `submitAuth` — drives the auth UI |
| `js/api.js:83` | `AuthApi.register(username, password)` — only two params |
| `server/routes/auth.js:81–107` | `POST /api/auth/register` — reads `{ username, password }` |
| `server/auth/validators.js` | `validateUsername`, `validatePassword` |
| `server/db.js:11–24` | `users` table — `id`, `username`, `password_hash`, `created_at` |
| `css/styles.css:481–516` | Auth-screen styles |

---

## Part 1 — Registration Form (extended fields)

### 1a. Database — add `first_name`, `last_name` columns

**File:** `server/db.js`

Add two columns to the `users` table DDL, and an `ALTER TABLE` migration statement that is safe to run on an existing database (no-op if the column already exists via `IF NOT EXISTS` guard or by catching the error).

```sql
ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN last_name  TEXT NOT NULL DEFAULT '';
```

`SCHEMA_STATEMENTS` already runs via `client.batch(…, "write")`. Add a separate `MIGRATION_STATEMENTS` array that runs after the schema and silently ignores "duplicate column" errors from libSQL.

### 1b. Backend — register route

**File:** `server/routes/auth.js`

- Accept `{ firstName, lastName, username, password }` from `req.body`.
- Add `validateName(value)` import from validators (see 1c).
- Insert `first_name`, `last_name` into the `INSERT` statement.
- Return `{ user: { username, firstName, lastName } }` in the 201 response.

**File:** `server/auth/validators.js`

Add:
```js
const NAME_RE = /^[A-Za-zÀ-ÿ '-]{1,64}$/;

function validateName(value, field) {
  if (typeof value !== 'string' || !NAME_RE.test(value.trim())) {
    return { valid: false, error: `${field} must be 1–64 letters.` };
  }
  return { valid: true };
}
```

### 1c. Backend — `/api/auth/me` and `/api/auth/login` responses

**File:** `server/routes/auth.js`

Update the `SELECT` in `getCurrentUser` (via `auth/service.js`) and in the `/login` handler to also return `first_name`, `last_name`, so the front-end can display them after login without a separate request.

`auth/service.js` — `getCurrentUser` currently `SELECT id, username`. Change to:
```sql
SELECT id, username, first_name, last_name FROM users WHERE id = ?
```
Return `{ id, username, firstName, lastName }`.

`routes/auth.js` — update `/login` and `/me` response shape to include `firstName`, `lastName`.

### 1d. Username availability check — new API endpoint

**File:** `server/routes/auth.js`

Add a lightweight, rate-limited endpoint:

```
GET /api/auth/check-username?username=<value>
```

Response:
```json
{ "available": true }   // or false
```

- Uses `SELECT 1 FROM users WHERE username = ? COLLATE NOCASE` (same collation as the UNIQUE constraint).
- Rate-limited with the existing `rateLimitBase` config (max 20/15 min is reasonable).
- Returns 400 if `username` param fails `validateUsername`.

### 1e. Front-end API layer

**File:** `js/api.js`

- Update `register` to accept `(firstName, lastName, username, password)` and POST all four fields.
- Add `checkUsername(username)` → `call("GET", "/api/auth/check-username?username=" + encodeURIComponent(username))`.

### 1f. Front-end HTML — registration fields

**File:** `index.html`

Inside `#authForm`, add four new `<div class="field">` blocks that are shown only in register mode (use a wrapper `<div id="authRegisterFields" class="hidden">`):

```html
<div id="authRegisterFields" class="hidden">
  <!-- First Name -->
  <div class="field">
    <label for="authFirstName">First Name</label>
    <input id="authFirstName" type="text" autocomplete="given-name" maxlength="64" />
  </div>
  <!-- Last Name -->
  <div class="field">
    <label for="authLastName">Last Name</label>
    <input id="authLastName" type="text" autocomplete="family-name" maxlength="64" />
  </div>
</div>
```

The existing `#authUsername` field stays as the **User ID** field (relabel its `<label>` to "User ID" in register mode via JS).

Add a confirm-password field after the password field, also inside `#authRegisterFields`:

```html
<div class="field" id="confirmPasswordField">
  <label for="authConfirmPassword">Confirm Password</label>
  <input id="authConfirmPassword" type="password" autocomplete="new-password" maxlength="72" />
  <p id="authPasswordMatch" class="auth-field-hint"></p>
</div>
```

### 1g. Front-end JS — `setAuthMode` and `submitAuth`

**File:** `js/app.js`

**`setAuthMode`** changes:
- Toggle `#authRegisterFields` hidden/visible.
- Toggle username label: "Username" (login) vs "User ID" (register).
- Clear register-only fields when switching back to login.

**`submitAuth`** changes:
- In register mode, read `firstName`, `lastName`, `confirmPassword` from new fields.
- Validate `firstName` / `lastName` client-side (non-empty, letters only).
- Validate `confirmPassword === password`; show error if mismatch.
- Call `window.AuthApi.register(firstName, lastName, username, password)`.
- After successful register/login, pass `firstName` and `lastName` into `loadUserData`.

**Live username availability check:**
- Add a `debounce`-wrapped `input` listener on `#authUsername` that fires when in register mode and `username.length >= 3`.
- Calls `window.AuthApi.checkUsername(username)`.
- Shows a small inline status element `#authUsernameStatus` below the username field:
  - Green "✓ Available" if `available: true`
  - Red "✗ Already taken" if `available: false`
  - Neutral spinner during the request

**Live password match indicator:**
- `input` listeners on both `#authPassword` and `#authConfirmPassword`.
- Updates `#authPasswordMatch`:
  - Empty when either field is empty
  - Green "Passwords match" when equal
  - Red "Passwords do not match" when unequal

### 1h. CSS — new auth field helpers

**File:** `css/styles.css`

Add styles for:
- `.auth-field-hint` — small text below a field (12px, muted; coloured via modifier classes)
- `.auth-field-hint.match` — green (`var(--status-completed)`)
- `.auth-field-hint.mismatch` — red (`var(--status-blocked)`)
- `#authUsernameStatus` — same pattern, positioned under the User ID input

---

## Part 2 — Footer Banner on the Auth Screen

### 2a. HTML — add banner inside `#authScreen`

**File:** `index.html`

Add a `<footer class="auth-footer">` as the last child of `#authScreen` (after the `#authBlock` div, before the closing `</div>`):

```html
<footer class="auth-footer">
  <div class="auth-footer-inner">
    <span class="auth-footer-copy">&copy; <span id="authFooterYear"></span> AI Engineer Roadmap. All rights reserved.</span>
    <span class="auth-footer-sep">·</span>
    <span>Developed by <a class="auth-footer-link" href="mailto:upendra.kumar48762@gmail.com">upendra.kumar48762@gmail.com</a></span>
    <span class="auth-footer-sep">·</span>
    <span>
      <a class="auth-footer-link" href="https://github.com/imkushwaha" target="_blank" rel="noopener">
        GitHub: imkushwaha
      </a>
      &nbsp;— if this tool helps you, please ⭐ the repo!
    </span>
    <span class="auth-footer-sep">·</span>
    <span>Built with planning &amp; development assistance from <strong>Claude</strong> (Anthropic AI).</span>
    <span class="auth-footer-sep">·</span>
    <span>Open source — contributions welcome.</span>
  </div>
</footer>
```

**Note:** Year is populated at runtime via `document.getElementById("authFooterYear").textContent = new Date().getFullYear()` in `app.js` (add to `boot()` or DOMContentLoaded).

### 2b. CSS — auth footer

**File:** `css/styles.css`

The `#authScreen` is currently `position: fixed; inset: 0; display: flex; align-items: center; justify-content: center`. Change it to a column layout to accommodate the footer:

```css
.auth-screen {
  flex-direction: column;
  justify-content: center;   /* keep card centred vertically when there's room */
  padding-bottom: 0;         /* footer sits flush at the bottom */
}

.auth-footer {
  width: 100%;
  background: var(--bg-sunken);
  border-top: 1px solid var(--border);
  padding: 10px 20px;
  margin-top: auto;          /* pushes footer to the bottom of the flex column */
  flex-shrink: 0;
}

.auth-footer-inner {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
  font-size: 11.5px;
  color: var(--text-faint);
  justify-content: center;
  text-align: center;
}

.auth-footer-link {
  color: var(--accent);
  text-decoration: none;
}
.auth-footer-link:hover { text-decoration: underline; }

.auth-footer-sep { opacity: 0.35; }
```

---

## Part 3 — Profile Panel: Full Name + User ID

### 3a. Backend — carry `firstName`, `lastName` in JWT payload (optional but clean)

The JWT currently stores `{ un: username }`. Adding `fn` (first name) and `ln` (last name) avoids an extra DB hit on every `/me` call. However, because the JWT is already carrying the username, the simplest approach is:

- **Keep the JWT as-is** (only `un` + `sub`).
- **`/me` and `/login` responses** already return `firstName`/`lastName` from the DB (added in 1c above); the front-end stores them in `session`.

### 3b. Front-end — `session` object

**File:** `js/app.js`

Extend the `session` object to hold `firstName` and `lastName`:

```js
Object.assign(session, {
  username,
  firstName: res.user.firstName || "",
  lastName:  res.user.lastName  || "",
  version: ...,
  ...
});
```

### 3c. Profile panel HTML

**File:** `index.html`

The current profile panel header:
```html
<div class="profile-panel-header">
  <span class="profile-panel-username" id="panelUsername">—</span>
  <span class="profile-panel-save" id="panelSaveStatus" aria-live="polite"></span>
</div>
```

Replace with:
```html
<div class="profile-panel-header">
  <span class="profile-panel-fullname" id="panelFullName">—</span>
  <span class="profile-panel-username" id="panelUsername">—</span>
  <span class="profile-panel-save" id="panelSaveStatus" aria-live="polite"></span>
</div>
```

The header trigger in the app header currently shows `#profileName` (just username). Update it to show the full name when available:
```html
<span class="profile-trigger-name" id="profileName">—</span>
```
(no HTML change needed here; JS will populate it differently)

### 3d. Front-end JS — populate full name + user ID

**File:** `js/app.js`

In `loadUserData` (around line 1874):
```js
const fullName = [session.firstName, session.lastName].filter(Boolean).join(" ") || username;
$("profileName").textContent = fullName;          // header trigger
$("panelFullName").textContent = fullName;         // panel full name row
$("panelUsername").textContent = "@" + username;   // user ID row, prefixed with @
```

### 3e. CSS — profile panel full-name style

**File:** `css/styles.css`

Add:
```css
.profile-panel-fullname {
  font-weight: 700;
  font-size: 14px;
  color: var(--text);
}
.profile-panel-username {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}
```

(The existing `.profile-panel-username` rule targets font-weight 600 at 13.5px — update it to the above to differentiate from the full-name line.)

---

## File-by-file Change Summary

| File | Changes |
|---|---|
| `server/db.js` | Add `first_name`, `last_name` columns; run migration |
| `server/auth/validators.js` | Add `validateName()` |
| `server/auth/service.js` | `getCurrentUser` returns `firstName`, `lastName` |
| `server/routes/auth.js` | Accept + store names on register; return names on login/me; add `GET /check-username` |
| `js/api.js` | `register` accepts 4 params; add `checkUsername()` |
| `index.html` | Register-only field group; confirm-password; username status; auth footer |
| `js/app.js` | `setAuthMode` toggles new fields; `submitAuth` validates + calls new API; session stores names; profile panel renders full name + user ID; footer year injection |
| `css/styles.css` | `.auth-field-hint`, `#authUsernameStatus`, `.auth-footer*`, `.profile-panel-fullname` update |

---

## Implementation Order (avoid merge conflicts)

1. `server/db.js` — schema + migration (no front-end deps)
2. `server/auth/validators.js` — add `validateName`
3. `server/auth/service.js` — extend `getCurrentUser`
4. `server/routes/auth.js` — register route + check-username endpoint
5. `js/api.js` — update `register`, add `checkUsername`
6. `css/styles.css` — all new CSS rules
7. `index.html` — new HTML blocks
8. `js/app.js` — logic changes (depends on HTML IDs existing)

---

## Out of Scope

- Allowing users to edit their name after registration (profile settings page — separate task).
- Email-based password reset.
- OAuth / SSO.
