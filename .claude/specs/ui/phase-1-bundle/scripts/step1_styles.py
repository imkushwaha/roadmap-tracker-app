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
