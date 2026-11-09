"""Phase 0 / js/app.js. Run from the repo root: python3 step_appjs.py"""
import re

P = "js/app.js"
s = open(P, encoding="utf-8").read()


def replace(old, new):
    global s
    assert s.count(old) == 1, f"expected exactly one match ({s.count(old)} found): {old[:80]}"
    s = s.replace(old, new)


# 1. The theme key now lives in js/theme-boot.js
m = re.search(r'\n  const THEME_KEY = "roadmap-dashboard:theme";', s)
assert m, "THEME_KEY constant not found"
s = s.replace(m.group(0), "")

# 2. applyTheme/initTheme -> keep the menu buttons in sync with window.Theme
a = s.index("  function applyTheme(theme) {")
b = s.index("  // ---------------------------------------------------------\n  // Export / Import / Reset")
s = s[:a] + '''  // The saved choice (light / dark / system) lives in js/theme-boot.js, which
  // also applies it before first paint. Here we only keep the menu buttons in sync.
  const THEME_BUTTONS = { light: "themeLightBtn", dark: "themeDarkBtn", system: "themeSystemBtn" };

  function syncThemeButtons() {
    const mode = window.Theme.get();
    Object.entries(THEME_BUTTONS).forEach(([value, id]) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.classList.toggle("active", value === mode);
      btn.setAttribute("aria-pressed", String(value === mode));
    });
  }
  function initTheme() {
    window.Theme.onChange(syncThemeButtons);
    syncThemeButtons();
  }

''' + s[b:]

# 3. Button handlers
a = s.index('    $("themeLightBtn").addEventListener("click"')
b = s.index("    // Search (tab bar, roadmap only)")
s = s[:a] + '''    Object.entries(THEME_BUTTONS).forEach(([value, id]) => {
      $(id).addEventListener("click", () => window.Theme.set(value));
    });

''' + s[b:]

# 4. Confetti honours "reduce motion"
replace('''    toast(`🎉 Month complete: ${phaseTitle}!`, "celebrate");
    const canvas''', '''    toast(`🎉 Month complete: ${phaseTitle}!`, "celebrate");
    // Honour the OS "reduce motion" setting: the toast alone is the celebration.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas''')

# 5. "YOU ARE HERE" (all caps) -> "Current" (2 occurrences)
assert s.count("YOU ARE HERE") == 2, "expected 2 occurrences of YOU ARE HERE"
s = s.replace("YOU ARE HERE", "Current")

# 6. Accessible names for form controls that had none
replace('''  function statusSelect(id, status) {
    return `<select class="status-select" data-action="set-status" data-id="${id}">''',
'''  function statusSelect(id, status) {
    const entry = indexEntry(id);
    const label = entry ? `Status: ${entry.title}` : "Status";
    return `<select class="status-select" data-action="set-status" data-id="${id}" aria-label="${esc(label)}">''')
replace('<select class="select-filter" data-action="filter-phase">',
        '<select class="select-filter" data-action="filter-phase" aria-label="Filter by month">')
replace('<select class="select-filter" data-action="kanban-phase">',
        '<select class="select-filter" data-action="kanban-phase" aria-label="Month">')
replace('<input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${sk.id}" ${getItem(sk.id).status === "completed" ? "checked" : ""} />',
        '<input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${sk.id}" aria-label="${esc(sk.title)}" ${getItem(sk.id).status === "completed" ? "checked" : ""} />')

# 7. Initialise theme (unchanged call site: initTheme() already runs in init())
assert "initTheme();" in s

open(P, "w", encoding="utf-8").write(s)
print("js/app.js updated")
