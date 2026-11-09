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
