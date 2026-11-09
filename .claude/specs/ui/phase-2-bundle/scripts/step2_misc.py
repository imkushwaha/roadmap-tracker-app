"""Phase 2 / small additions to Phase 0 files: five more icons and the .sr-only utility.
Run from the repo root: python3 step2_misc.py"""

ICONS = r'''    columns: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>',
    "list-checks": '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    award: '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    "book-open": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
'''

P = "js/icons.js"
s = open(P, encoding="utf-8").read()
marker = "    help: '<circle"
assert s.count(marker) == 1, "icon marker not found"
assert "columns:" not in s, "icons already added"
s = s.replace(marker, ICONS + marker)
open(P, "w", encoding="utf-8").write(s)

P = "css/base.css"
s = open(P, encoding="utf-8").read()
old = ".hidden { display: none !important; }"
assert s.count(old) == 1 and ".sr-only" not in s
s = s.replace(old, old + """
.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}""")
open(P, "w", encoding="utf-8").write(s)
print("js/icons.js and css/base.css updated")
