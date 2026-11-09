"""Phase 2 / css/styles.css: remove the old header, tabs and roadmap-dashboard rules
(they are replaced by css/shell.css and css/home.css). Run from the repo root: python3 step2_styles.py"""
import re

P = "css/styles.css"
s = open(P, encoding="utf-8").read()


def cut(start, end):
    """Delete from `start` up to (not including) `end`; both markers must exist once."""
    global s
    assert s.count(start) == 1, "start marker not unique/found: " + start[:60]
    a = s.index(start)
    assert end in s[a:], "end marker not found after start: " + end[:60]
    b = s.index(end, a)
    s = s[:a] + s[b:]


# 1. Old header (brand, subtitle, header-actions, save-status)
cut("/* ---------------- Header ---------------- */", "/* ── Profile Anchor")
# 2. Old tab row and the bare `main` rule
cut("\n.tabs-row {\n", "/* ---------------- Generic card / grid ---------------- */")  # (a mobile rule also starts with ".tabs-row {")
# 3. Old roadmap dashboard (cards, bar, grid, action tiles, coming-soon badge)
cut("/* ---------------- Roadmap dashboard ---------------- */", "/* ---------------- Custom roadmaps ---------------- */")

# 4. Leftovers
s = re.sub(r"\.header-actions \{[^}]*\}\n", "", s)
s = re.sub(r"\.save-status \{[^}]*\}\n\.save-status:empty \{[^}]*\}\n(\.save-status\.[^\n]*\n)+", "", s)
old_locked = "body.locked .app-header, body.locked main { display: none; }\n"
assert s.count(old_locked) == 1, "locked rule not found"
s = s.replace(old_locked, "")  # css/shell.css hides the shell while locked
mobile = ("  .tabs-row { flex-wrap: wrap; gap: 0; }\n  .tabs { flex-basis: 100%; }\n"
          "  .roadmap-search { flex: 1 1 100%; margin: 4px 0 8px; }\n  .header-inner { padding: 12px 14px 8px; }\n"
          "  .brand h1 { font-size: 15px; }\n  .brand .subtitle { display: none; }\n  main { padding: 14px 12px 70px; }\n")
assert s.count(mobile) == 1, "old mobile header rules not found"
s = s.replace(mobile, "")

open(P, "w", encoding="utf-8").write(s)
for gone in (".app-header", ".tabs-row", ".dashboard-bar", ".roadmap-grid", ".header-inner", ".back-btn", ".coming-soon-badge"):
    assert gone not in s, "still present: " + gone
print("css/styles.css:", len(s.splitlines()), "lines")
