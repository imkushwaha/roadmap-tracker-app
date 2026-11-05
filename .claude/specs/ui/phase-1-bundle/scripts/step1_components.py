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
