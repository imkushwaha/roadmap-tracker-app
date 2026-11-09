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
