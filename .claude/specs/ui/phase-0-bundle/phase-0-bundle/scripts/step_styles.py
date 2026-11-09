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
