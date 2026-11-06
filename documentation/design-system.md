# Design System

The visual language of Roadmap Tracker: design tokens, typography, components, theming and the rules that keep screens consistent. The full redesign rationale and phase plan live in `.claude/specs/ui-redesign-spec.md`.

**Principles:** progress is the hero; color carries meaning (status), never decoration; borders over shadows; dense but breathable; keyboard and screen-reader friendly by default.

## File map (no build step)

| File | Role |
|---|---|
| `css/tokens.css` | **Single source** of color, radius, spacing, type tokens. Light on `:root`, dark on `:root[data-theme="dark"]` |
| `css/base.css` | `@font-face` (self-hosted IBM Plex Sans), reset, body type, focus ring, reduced-motion rules |
| `css/components.css` | Buttons, form fields, progress bar, badges, status chips, modal, toasts, skeleton, avatar, mini button, **Month Strip** |
| `css/auth.css` | Log in / create-account screens (split layout, brand panel, field hints, footer) |
| `css/shell.css` | App shell: sidebar (expanded, collapsed, drawer), top bar, breadcrumb, save-status chip, About dialog bits |
| `css/home.css` | Home: page header, summary bar, roadmap cards, per-card menu, empty state, skeleton |
| `css/styles.css` | Layout and per-view rules not yet moved (shrinks each phase; see "Redesign status") |
| `js/theme-boot.js` | Applies Light / Dark / System **before first paint**; exposes `window.Theme` |
| `js/icons.js` | Inline SVG icon set, `Icons.svg(name, { size, label })` (Lucide, ISC licence) |
| `js/month-strip.js` | `MonthStrip.html(months, { size, labels, animate })` |
| `js/roadmap-stats.js` | Shared (UMD) progress summaries; used by the server for `stats` on the roadmap list |
| `fonts/` | IBM Plex Sans 400 / 500 / 600, Latin subset, plus the SIL OFL licence |
| `img/` | `logo.svg` (brand mark) and `favicon.svg` |

Load order in `index.html`: `theme-boot.js` (blocking, in `<head>`) → `tokens.css` → `base.css` → `components.css` → `auth.css` → `shell.css` → `home.css` → `styles.css`; scripts at the end: `icons.js`, `month-strip.js`, `data/roadmap.js`, `progress-schema.js`, `api.js`, `app.js`.

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

## Month Strip

One segment per month; each segment is a stacked bar of that month's tasks (completed, in progress, blocked, remaining). The current month gets an accent marker. More than 12 months collapses to one continuous bar; zero months shows a dashed empty strip. Output is escaped HTML with `role="img"` and a text summary (for example "152 of 849 tasks complete across 10 months"). Sizes: `"sm"` (4px), `"md"` (8px), `"lg"` (14px, optionally with month labels). `animate: true` plays the single entrance animation (segments fill left to right over 600ms; disabled by reduced motion).

```js
MonthStrip.html([
  { label: "Oct", title: "Month 1: Foundations", total: 100, completed: 60, inProgress: 10, blocked: 0, current: true },
], { size: "md", labels: false, animate: false });
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

## App shell

`#appShell` holds the sidebar and the page. `data-context="home|roadmap"` switches what is shown: Home shows the roadmap switcher; a roadmap shows "All roadmaps", the roadmap card with a live Month Strip, and the seven views (buttons with `data-view`, so the existing view switching is unchanged). Roadmap-only controls (search, save status, roadmap settings) carry the `roadmap-only` class and are hidden on Home. The account menu is a single element in the top bar. Below 1024px the sidebar is a drawer (menu button, scrim, Escape to close); on desktop it can be collapsed to an icon rail, remembered under `roadmap-dashboard:sidebar`.

## Redesign status

| Phase | Scope | Status |
|---|---|---|
| 0 | Tokens, fonts, theme (incl. System), icons, base components, reduced motion | Done |
| 1 | Log in and create-account screens | Done |
| 2 | App shell, Home, `stats` API, hash routes | Done |
| 3 | Home flows (New roadmap dialog, filters, list view) | Not started |
| 4 | Roadmap views | Not started |
| 5 | Hardening, remove legacy CSS | Not started |
