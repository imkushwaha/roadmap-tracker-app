"""Phase 3 / small additions to earlier files: Theme.isSaved() and the Phase 3 styles.
Run from the repo root: python3 step3_misc.py"""

# 1. js/theme-boot.js: report whether the user has chosen an appearance (used by "Getting started")
P = "js/theme-boot.js"
s = open(P, encoding="utf-8").read()
old = "    get: read,\n"
assert s.count(old) == 1 and "isSaved" not in s, "theme-boot.js is not in the expected state"
s = s.replace(old, old + """    isSaved() {
      try { return MODES.includes(localStorage.getItem(KEY)); } catch { return false; }
    },
""")
open(P, "w", encoding="utf-8").write(s)

# 2. css/home.css: append the Phase 3 styles
P = "css/home.css"
s = open(P, encoding="utf-8").read()
assert ".home-layout" not in s, "Phase 3 styles already present"
BLOCK = r'''
/* ===========================================================
   Phase 3: Home flows — toolbar, list view, right rail, dialogs
   =========================================================== */

/* Layout: list + optional right rail (rail drops below the list under 1280px) */
.home-layout { display: grid; gap: 24px; grid-template-columns: minmax(0, 1fr); align-items: start; }
@media (min-width: 1280px) { .home-layout.has-rail { grid-template-columns: minmax(0, 1fr) 320px; } }
.home-rail { display: flex; flex-direction: column; gap: 16px; }
.home-rail:empty { display: none; }

/* Grid / list toggle */
.view-toggle { display: inline-flex; gap: 2px; padding: 3px; background: var(--bg-sunken); border-radius: var(--radius-sm); }
.view-btn {
  width: 34px; height: 30px; display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid transparent; border-radius: 4px; background: transparent; color: var(--text-muted);
}
.view-btn:hover { color: var(--text); }
.view-btn.active { background: var(--bg-elevated); color: var(--text); border-color: var(--border-strong); }

/* The main column is a size container: tables and the toolbar adapt to the space actually available
   next to the right rail, not to the window width. */
.home-main { min-width: 0; container-type: inline-size; container-name: homemain; }

/* Toolbar: search + sort on the first row, status chips below; one row when there is room */
.home-toolbar {
  display: grid; align-items: center; gap: 12px 16px; margin-bottom: 16px;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas: "search sort" "filters filters";
}
@container homemain (min-width: 860px) {
  .home-toolbar { grid-template-columns: minmax(200px, 300px) 1fr auto; grid-template-areas: "search filters sort"; }
}
.home-search { grid-area: search; position: relative; max-width: 360px; }
.home-search .icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-faint); pointer-events: none; }
.home-search input {
  width: 100%; min-height: 36px; padding: 0 12px 0 32px;
  border: 1px solid var(--border-strong); border-radius: var(--radius-sm);
  background: var(--bg-elevated); color: var(--text); font-size: 14px;
}
.home-search input:focus { border-color: var(--accent); }
.home-toolbar .filter-bar { grid-area: filters; margin: 0; }
.home-toolbar .chip-filter { min-height: 32px; }
.chip-count { margin-left: 2px; font-variant-numeric: tabular-nums; opacity: 0.8; }
.home-sort { grid-area: sort; display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); }
.home-sort .select-filter { min-height: 36px; border-radius: var(--radius-sm); border-color: var(--border-strong); }

/* List view */
.table-wrap { background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.rtable { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; }
.rtable th {
  height: 40px; padding: 0 16px; text-align: left; white-space: nowrap;
  font-size: 13px; font-weight: 500; color: var(--text-muted); background: var(--bg-sunken);
}
.rtable thead th:first-child { border-top-left-radius: calc(var(--radius-md) - 1px); }
.rtable thead th:last-child { border-top-right-radius: calc(var(--radius-md) - 1px); }
.rtable td { padding: 12px 16px; border-top: 1px solid var(--border); vertical-align: middle; }
.rt-row { cursor: pointer; }
.rt-row:hover { background: var(--bg-sunken); }
.th-btn { display: inline-flex; align-items: center; gap: 4px; min-height: 28px; padding: 0; border: 0; background: none; font: inherit; color: inherit; cursor: pointer; }
.th-btn:hover { color: var(--text); }
.th-arrow { display: inline-flex; }
.th-arrow.is-asc { transform: rotate(180deg); }
.rt-name-cell { width: 100%; max-width: 0; }   /* lets the name column absorb leftover width and truncate */
.rt-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.rt-desc { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--text-muted); }
.rt-progress { min-width: 160px; }
.rt-progress .strip { margin-bottom: 4px; }
.rt-pct { font-size: 12px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.col-month, .col-activity { white-space: nowrap; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.rt-actions { white-space: nowrap; text-align: right; }
.rt-actions > * { display: inline-flex; vertical-align: middle; }
.rt-actions .rc-menu { margin: 0 0 0 4px; }
@container homemain (max-width: 899px) { .col-month { display: none; } }
@container homemain (max-width: 679px) { .col-type { display: none; } }
/* Narrow column (phones): each row becomes a small card — name and progress on the left, action on the right.
   Sorting then uses the "Sort by" control above, since the header row is hidden. */
@container homemain (max-width: 559px) {
  .rtable, .rtable tbody { display: block; }
  .rtable thead { display: none; }
  .rtable .rt-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px 12px; padding: 14px 16px; border-top: 1px solid var(--border); }
  .rtable .rt-row:first-child { border-top: 0; }
  .rtable td { display: block; padding: 0; border: 0; }
  .rtable .rt-name-cell { grid-column: 1; width: auto; max-width: none; }
  .rtable .rt-progress { grid-column: 1; min-width: 0; }
  .rtable .rt-actions { grid-column: 2; grid-row: 1 / span 2; align-self: center; }
  .rtable .col-type, .rtable .col-month, .rtable .col-activity, .rt-desc { display: none; }
}

.empty-panel-sm { margin: 24px auto; padding: 24px; }

/* Right rail */
.rail-card { padding: 20px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); }
.rail-title { margin: 0 0 4px; font-size: 15px; line-height: 22px; }
.rail-sub { margin: 0 0 12px; font-size: 13px; color: var(--text-muted); overflow-wrap: anywhere; }
.rail-main { margin: 0 0 4px; font-weight: 600; overflow-wrap: anywhere; }
.rail-week { margin: 0 0 16px; font-size: 13px; color: var(--text-muted); }
.rail-card .btn { margin-top: 4px; }
.rail-list { list-style: none; margin: 0 0 12px; padding: 0; display: flex; flex-direction: column; gap: 10px; font-size: 14px; }
.rail-list li { display: flex; align-items: center; gap: 10px; color: var(--text); }
.rail-list li.is-done { color: var(--text-muted); }
.rail-list li.is-done .icon { color: var(--status-completed); }
.rail-dot { flex-shrink: 0; width: 14px; height: 14px; margin: 1px; border: 1.5px solid var(--text-faint); border-radius: 50%; }

/* New roadmap and delete dialogs */
.modal:has(#createRoadmapForm) { max-width: 560px; }
.modal:has(#deleteRoadmapForm) { max-width: 440px; }
.option-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; }
.option-row {
  display: flex; align-items: flex-start; gap: 12px; padding: 12px 14px; cursor: pointer;
  border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--bg-elevated);
}
.option-row:hover { border-color: var(--text-faint); }
.option-row.is-selected { border-color: var(--accent); background: var(--accent-soft); }
.option-row.is-disabled { cursor: not-allowed; background: var(--bg-sunken); }
.option-row.is-disabled .option-title { color: var(--text-muted); }
.option-row:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
.option-row input { margin-top: 3px; accent-color: var(--accent); }
.option-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.option-title { font-weight: 600; }
.option-desc { font-size: 13px; color: var(--text-muted); }
.option-row.is-disabled .option-desc { color: var(--text-faint); }
.badge-soon { margin-left: 6px; background: var(--accent-soft); color: var(--accent); }
.dialog-text { margin: 0 0 16px; color: var(--text-muted); line-height: 1.5; }
'''
open(P, "w", encoding="utf-8").write(s.rstrip("\n") + "\n" + BLOCK)
print("js/theme-boot.js and css/home.css updated")
