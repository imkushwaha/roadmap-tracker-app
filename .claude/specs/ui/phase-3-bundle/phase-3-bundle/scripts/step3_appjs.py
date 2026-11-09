"""Phase 3 / js/app.js: Home toolbar, list view, right rail, New roadmap dialog, typed-name delete,
modal focus handling. Run from the repo root: python3 step3_appjs.py"""
P = "js/app.js"
s = open(P, encoding="utf-8").read()


def swap_block(start, end, new):
    """Replace everything from `start` up to (not including) `end`."""
    global s
    assert s.count(start) == 1, "start marker not unique/found: " + start[:70]
    a = s.index(start)
    assert end in s[a:], "end marker not found after start: " + end[:70]
    b = s.index(end, a)
    s = s[:a] + new + s[b:]


def once(old, new):
    global s
    assert s.count(old) == 1, f"expected exactly one match ({s.count(old)} found): {old[:80]}"
    s = s.replace(old, new)


# 1. Home: preferences, filter/sort, cards, table, toolbar, right rail, renderDashboard
NEW_HOME = r'''  // ----- Home: saved preferences, filter, sort -----
  const HOME_PREFS_KEY = "roadmap-dashboard:home";
  const GETTING_STARTED_KEY = "roadmap-dashboard:getting-started";
  const SORT_DEFAULT_DIR = { recent: "desc", name: "asc", progress: "desc" };
  const STATUS_FILTERS = [["all", "All"], ["in_progress", "In progress"], ["not_started", "Not started"], ["completed", "Completed"]];
  // View and sort are remembered; filter and search are not.
  const homeState = { view: "grid", sortKey: "recent", sortDir: "desc", filter: "all", search: "" };

  function loadHomePrefs() {
    try {
      const saved = JSON.parse(localStorage.getItem(HOME_PREFS_KEY) || "null");
      if (!saved) return;
      if (saved.view === "grid" || saved.view === "list") homeState.view = saved.view;
      if (SORT_DEFAULT_DIR[saved.sortKey]) {
        homeState.sortKey = saved.sortKey;
        homeState.sortDir = saved.sortDir === "asc" || saved.sortDir === "desc" ? saved.sortDir : SORT_DEFAULT_DIR[saved.sortKey];
      }
    } catch { /* storage blocked or unreadable: keep the defaults */ }
  }
  function saveHomePrefs() {
    try {
      localStorage.setItem(HOME_PREFS_KEY, JSON.stringify({ view: homeState.view, sortKey: homeState.sortKey, sortDir: homeState.sortDir }));
    } catch { /* storage blocked: preferences last for this visit only */ }
  }

  // not_started | in_progress | completed, from the server-side stats.
  function roadmapState(r) {
    const s = r.stats;
    if (!s || !s.total) return "not_started";
    if (s.completed === s.total) return "completed";
    return s.completed + s.inProgress + s.blocked > 0 ? "in_progress" : "not_started";
  }
  // Does deleting this roadmap throw away real work? (Notes or dates on an otherwise untouched roadmap do not count.)
  function roadmapHasProgress(r) {
    const s = r.stats;
    if (!s) return false;
    return s.completed + s.inProgress + s.blocked > 0 || (r.source !== BUILTIN_SOURCE && s.total > 0);
  }

  function sortRoadmaps(list) {
    const dir = homeState.sortDir === "asc" ? 1 : -1;
    const time = (r) => (r.lastActivityAt ? Date.parse(r.lastActivityAt) : -Infinity);
    const compare = {
      recent: (a, b) => {
        const ta = time(a);
        const tb = time(b);
        if (ta === tb) return a.id - b.id;
        return ta < tb ? -1 : 1;
      },
      name: (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }) || a.id - b.id,
      progress: (a, b) => (pctOf(a.stats) - pctOf(b.stats))
        || ((a.stats ? a.stats.completed : 0) - (b.stats ? b.stats.completed : 0)) || a.id - b.id,
    }[homeState.sortKey];
    return list.slice().sort((a, b) => dir * compare(a, b));
  }

  function visibleRoadmaps() {
    const q = homeState.search.trim().toLowerCase();
    return sortRoadmaps(dashboardRoadmaps.filter((r) => (
      (homeState.filter === "all" || roadmapState(r) === homeState.filter)
      && (!q || r.name.toLowerCase().includes(q) || (r.description || "").toLowerCase().includes(q))
    )));
  }

  // ----- Home: cards and table -----
  function roadmapMenu(r) {
    return `
      <div class="rc-menu">
        <button type="button" class="btn btn-ghost btn-icon btn-sm" data-menu-trigger aria-expanded="false"
                aria-label="More actions for ${esc(r.name)}">${window.Icons.svg("more-horizontal", { size: 18 })}</button>
        <div class="rc-menu-panel hidden" role="group" aria-label="Actions for ${esc(r.name)}">
          <button type="button" class="profile-action-btn danger" data-action="delete-roadmap" data-id="${r.id}">Delete roadmap…</button>
        </div>
      </div>`;
  }

  function roadmapCard(r, animate) {
    const s = r.stats;
    const builtin = r.source === BUILTIN_SOURCE;
    const progressBlock = !s ? "" : `
      <div class="rc-progress">
        ${window.MonthStrip.html(stripMonths(s), { size: "md", animate })}
        <p class="rc-meta">
          <span>${s.total ? `<strong>${pctOf(s)}%</strong> complete · ${s.completed} of ${s.total} tasks` : "No months yet. Add one to start."}</span>
          <span>${esc(monthPosition(s))}</span>
        </p>
      </div>`;
    return `
      <article class="roadmap-card" data-id="${r.id}">
        <div class="rc-head">
          <h2 class="rc-title">${esc(r.name)}</h2>
          <span class="badge rc-badge">${builtin ? "Built-in" : "Custom"}</span>
          ${roadmapMenu(r)}
        </div>
        ${r.description ? `<p class="roadmap-card-desc">${esc(r.description)}</p>` : `<p class="roadmap-card-desc"></p>`}
        ${progressBlock}
        <div class="rc-foot">
          <p class="roadmap-card-meta">${esc(describeActivity(r.lastActivityAt))}</p>
          <button type="button" class="btn btn-primary" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
        </div>
      </article>`;
  }

  function activityShort(iso) {
    if (!iso) return "Not started yet";
    const days = daysBetween(new Date(iso), new Date());
    if (days <= 0) return "Today";
    if (days === 1) return "Yesterday";
    return days + " days ago";
  }

  function sortHeader(key, label) {
    const active = homeState.sortKey === key;
    const aria = active ? (homeState.sortDir === "asc" ? "ascending" : "descending") : "none";
    const arrow = active
      ? `<span class="th-arrow${homeState.sortDir === "asc" ? " is-asc" : ""}">${window.Icons.svg("chevron-down", { size: 14 })}</span>` : "";
    return `<th scope="col" aria-sort="${aria}"><button type="button" class="th-btn" data-action="sort-by" data-value="${key}">${label}${arrow}</button></th>`;
  }

  function roadmapTable(list) {
    const rows = list.map((r) => {
      const s = r.stats;
      return `
        <tr class="rt-row" data-id="${r.id}">
          <td class="rt-name-cell">
            <div class="rt-name">${esc(r.name)}</div>
            ${r.description ? `<div class="rt-desc">${esc(r.description)}</div>` : ""}
          </td>
          <td class="col-type"><span class="badge rc-badge">${r.source === BUILTIN_SOURCE ? "Built-in" : "Custom"}</span></td>
          <td class="rt-progress">
            ${s ? `${window.MonthStrip.html(stripMonths(s), { size: "sm" })}<span class="rt-pct">${s.total ? pctOf(s) + "%" : "No months"}</span>` : ""}
          </td>
          <td class="col-month">${esc(monthPosition(s)) || "—"}</td>
          <td class="col-activity">${esc(activityShort(r.lastActivityAt))}</td>
          <td class="rt-actions">
            <button type="button" class="btn btn-primary btn-sm" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
            ${roadmapMenu(r)}
          </td>
        </tr>`;
    }).join("");
    return `
      <div class="table-wrap">
        <table class="rtable">
          <thead><tr>
            ${sortHeader("name", "Roadmap")}
            <th scope="col" class="col-type">Type</th>
            ${sortHeader("progress", "Progress")}
            <th scope="col" class="col-month">Current month</th>
            ${sortHeader("recent", "Last activity")}
            <th scope="col"><span class="sr-only">Actions</span></th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function summaryBar(roadmaps) {
    const all = roadmaps.map((r) => r.stats).filter(Boolean);
    const sum = (key) => all.reduce((n, s) => n + s[key], 0);
    const total = sum("total");
    const done = sum("completed");
    const pct = total ? Math.round((done / total) * 100) : 0;
    return `
      <section class="summary-bar" aria-label="Summary">
        <div class="summary-item"><p class="summary-label">Roadmaps</p><p class="summary-value">${roadmaps.length}</p></div>
        <div class="summary-item"><p class="summary-label">Tasks done</p><p class="summary-value">${done} <small>/ ${total}</small></p></div>
        <div class="summary-item"><p class="summary-label">Overall progress</p><p class="summary-value">${pct}%</p></div>
        <div class="summary-item"><p class="summary-label">Done this week</p><p class="summary-value">${sum("completedLast7Days")}</p></div>
      </section>`;
  }

  // ----- Home: toolbar, view toggle -----
  function viewToggle() {
    const button = (value, icon, label) => `
      <button type="button" class="view-btn" data-action="set-view" data-value="${value}" aria-pressed="false"
              aria-label="${label}" title="${label}">${window.Icons.svg(icon, { size: 16 })}</button>`;
    return `<div class="view-toggle" role="group" aria-label="Layout">${button("grid", "layout-grid", "Grid view")}${button("list", "list", "List view")}</div>`;
  }

  function homeToolbar() {
    return `
      <div class="home-toolbar">
        <div class="home-search">
          ${window.Icons.svg("search", { size: 16 })}
          <input type="search" id="homeSearch" placeholder="Search roadmaps" aria-label="Search roadmaps" autocomplete="off" value="${esc(homeState.search)}" />
        </div>
        <div id="homeFilters" class="filter-bar" role="group" aria-label="Filter by status"></div>
        <div class="home-sort">
          <label for="homeSort">Sort by</label>
          <select id="homeSort" class="select-filter">
            <option value="recent">Recent activity</option>
            <option value="name">Name</option>
            <option value="progress">Progress</option>
          </select>
        </div>
      </div>`;
  }

  // Redraws only what filtering/sorting changes, so the search box keeps focus while typing.
  function renderHomeResults(animate) {
    const host = $("homeResults");
    if (!host) return;
    const multi = dashboardRoadmaps.length >= 2;
    const list = multi ? visibleRoadmaps() : dashboardRoadmaps.slice();
    const view = multi ? homeState.view : "grid";

    document.querySelectorAll(".view-btn").forEach((btn) => {
      const on = btn.dataset.value === view;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", String(on));
    });
    const filters = $("homeFilters");
    if (filters) {
      const counts = { all: dashboardRoadmaps.length, in_progress: 0, not_started: 0, completed: 0 };
      dashboardRoadmaps.forEach((r) => { counts[roadmapState(r)] += 1; });
      filters.innerHTML = STATUS_FILTERS.map(([value, label]) => `
        <button type="button" class="chip-filter${homeState.filter === value ? " active" : ""}" data-action="filter-status"
                data-value="${value}" aria-pressed="${homeState.filter === value}">${label} <span class="chip-count">${counts[value]}</span></button>`).join("");
    }
    if ($("homeSort")) $("homeSort").value = homeState.sortKey;

    if (!list.length) {
      const q = homeState.search.trim();
      host.innerHTML = `
        <div class="empty-panel empty-panel-sm">
          <h2>${q ? `No roadmaps match “${esc(q)}”.` : "No roadmaps in this view."}</h2>
          <button type="button" class="btn" data-action="clear-filters">${q && homeState.filter === "all" ? "Clear search" : "Clear filters"}</button>
        </div>`;
    } else if (view === "list") {
      host.innerHTML = roadmapTable(list);
    } else {
      host.innerHTML = `<div class="roadmap-grid">${list.map((r) => roadmapCard(r, animate)).join("")}</div>`;
    }
    const count = $("homeResultCount");
    if (count) count.textContent = `${list.length} ${list.length === 1 ? "roadmap" : "roadmaps"} shown`;
  }

  // ----- Home: right-hand rail (Current focus, Getting started) -----
  function focusRoadmap() {
    const withMonths = dashboardRoadmaps.filter((r) => r.stats && r.stats.months.length);
    if (!withMonths.length) return null;
    const active = withMonths.filter((r) => r.lastActivityAt)
      .sort((a, b) => Date.parse(b.lastActivityAt) - Date.parse(a.lastActivityAt));
    return active[0] || withMonths[0];
  }

  // The built-in roadmap's weekly sections follow 7-day blocks from the start of each month (days 1-28).
  function builtinWeekFocus(monthIndex) {
    const week = Math.floor((TODAY.getDate() - 1) / 7);
    const phase = BUILTIN_DATA.phases[monthIndex];
    if (week > 3 || !phase) return "";
    const section = phase.sections.find((s) => s.type === "week" && s.weekNumber && (s.weekNumber - 1) % 4 === week);
    return section ? section.title : "";
  }

  function focusCard() {
    const r = focusRoadmap();
    if (!r) return "";
    const s = r.stats;
    const idx = currentMonthIndex(s.startMonth, s.months.length);
    let main;
    let week = "";
    if (idx >= 0) {
      main = `Month ${s.months[idx].number}: ${s.months[idx].title || "Untitled"}`;
      if (r.source === BUILTIN_SOURCE) week = builtinWeekFocus(idx);
    } else {
      const start = monthKeyOffset(s.startMonth, 0);
      main = TODAY < start
        ? `Starts ${start.toLocaleDateString(undefined, { month: "long", year: "numeric" })}`
        : "The planned months have passed.";
    }
    return `
      <section class="rail-card" aria-labelledby="focusHeading">
        <h2 class="rail-title" id="focusHeading">Current focus</h2>
        <p class="rail-sub">${esc(r.name)}</p>
        <p class="rail-main">${esc(main)}</p>
        ${week ? `<p class="rail-week">${esc(week)}</p>` : ""}
        <button type="button" class="btn btn-primary btn-sm" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
      </section>`;
  }

  function gettingStartedItems() {
    const custom = dashboardRoadmaps.filter((r) => r.source !== BUILTIN_SOURCE);
    return [
      ["Complete your first task", dashboardRoadmaps.some((r) => r.stats && r.stats.completed > 0)],
      ["Create a custom roadmap", custom.length > 0],
      ["Add a month to your roadmap", custom.some((r) => r.stats && r.stats.months.length > 0)],
      ["Choose an appearance", window.Theme.isSaved()],
    ];
  }

  function gettingStartedCard() {
    let dismissed = false;
    try { dismissed = localStorage.getItem(GETTING_STARTED_KEY) === "dismissed"; } catch { /* storage blocked */ }
    const items = gettingStartedItems();
    const done = items.filter(([, ok]) => ok).length;
    if (dismissed || done === items.length) return "";
    return `
      <section class="rail-card" aria-labelledby="startedHeading">
        <h2 class="rail-title" id="startedHeading">Getting started</h2>
        <p class="rail-sub">${done} of ${items.length} done</p>
        <ul class="rail-list">
          ${items.map(([label, ok]) => `<li class="${ok ? "is-done" : ""}">${ok ? window.Icons.svg("check-circle", { size: 16 }) : '<span class="rail-dot" aria-hidden="true"></span>'}<span>${esc(label)}${ok ? '<span class="sr-only"> (done)</span>' : ""}</span></li>`).join("")}
        </ul>
        <button type="button" class="btn btn-ghost btn-sm" data-action="dismiss-getting-started">Dismiss</button>
      </section>`;
  }

  function homeRailHtml() {
    return focusCard() + gettingStartedCard();
  }

  function renderDashboard(roadmaps) {
    dashboardRoadmaps = roadmaps;
    renderSidebarRoadmaps();
    if (roadmaps.length < 2) { homeState.filter = "all"; homeState.search = ""; }
    const hasBuiltin = roadmaps.some((r) => r.source === BUILTIN_SOURCE);
    const atLimit = roadmaps.length >= MAX_ROADMAPS;
    const newBtn = `
      <button type="button" class="btn btn-primary" data-action="create-roadmap" ${atLimit ? `disabled title="You've reached the limit of ${MAX_ROADMAPS} roadmaps."` : ""}>
        ${window.Icons.svg("plus", { size: 16 })} New roadmap
      </button>`;

    if (roadmaps.length === 0) {
      $("dashboardContent").innerHTML = `
        <div class="page-head"><div><h1 class="page-title">Roadmaps</h1></div></div>
        <div class="empty-panel">
          <h2>No roadmaps yet</h2>
          <p>Start with the AI Engineer roadmap or build your own plan.</p>
          <div class="page-actions">
            <button type="button" class="btn btn-primary" data-action="restore-builtin">Restore AI Engineer roadmap</button>
            <button type="button" class="btn" data-action="create-roadmap">Blank roadmap</button>
          </div>
        </div>`;
      return;
    }

    const restore = hasBuiltin ? "" : `
      <div class="notice-row">
        <span>The AI Engineer roadmap isn't in your account. You can bring it back with fresh progress.</span>
        <button type="button" class="btn btn-sm" data-action="restore-builtin">Restore AI Engineer roadmap</button>
      </div>`;
    const animate = !stripsAnimated;
    stripsAnimated = true;
    const multi = roadmaps.length >= 2;
    const rail = homeRailHtml();

    $("dashboardContent").innerHTML = `
      <div class="page-head">
        <div>
          <h1 class="page-title">Roadmaps</h1>
          <p class="page-lead">Track progress across your plans.</p>
        </div>
        <div class="page-actions">${multi ? viewToggle() : ""}${newBtn}</div>
      </div>
      ${restore}
      <div class="home-layout${rail ? " has-rail" : ""}" id="homeLayout">
        <div class="home-main">
          ${summaryBar(roadmaps)}
          ${multi ? homeToolbar() : ""}
          <p id="homeResultCount" class="sr-only" role="status"></p>
          <div id="homeResults"></div>
        </div>
        <aside class="home-rail" id="homeRail" aria-label="Focus and tips">${rail}</aside>
      </div>`;
    renderHomeResults(animate);
  }

'''
swap_block("  function roadmapCard(r, animate) {", "  // Sidebar quick-switcher (Home only)", NEW_HOME)

# 2. Click / input / change handling for Home
NEW_CLICK = r'''  function onDashboardClick(e) {
    const trigger = e.target.closest("[data-menu-trigger]");
    if (trigger) { e.stopPropagation(); toggleCardMenu(trigger); return; }
    const el = e.target.closest("[data-action]");
    if (!el) {
      // A click on the card or table row itself (not on one of its buttons) opens it.
      const row = e.target.closest(".roadmap-card[data-id], .rt-row[data-id]");
      if (row && !e.target.closest("button, a, .rc-menu")) openRoadmap(Number(row.dataset.id));
      return;
    }
    closeCardMenus();
    switch (el.dataset.action) {
      case "open-roadmap": openRoadmap(Number(el.dataset.id)); break;
      case "delete-roadmap": confirmDeleteRoadmap(el.dataset.id); break;
      case "restore-builtin": restoreBuiltinRoadmap(); break;
      case "create-roadmap": openCreateRoadmapModal(); break;
      case "retry-dashboard": showDashboard(); break;
      case "filter-status":
        homeState.filter = el.dataset.value;
        renderHomeResults(false);
        break;
      case "set-view":
        homeState.view = el.dataset.value;
        saveHomePrefs();
        renderHomeResults(false);
        break;
      case "sort-by": {
        const key = el.dataset.value;
        homeState.sortDir = homeState.sortKey === key
          ? (homeState.sortDir === "asc" ? "desc" : "asc") : SORT_DEFAULT_DIR[key];
        homeState.sortKey = key;
        saveHomePrefs();
        renderHomeResults(false);
        break;
      }
      case "clear-filters":
        homeState.filter = "all";
        homeState.search = "";
        if ($("homeSearch")) $("homeSearch").value = "";
        renderHomeResults(false);
        break;
      case "dismiss-getting-started":
        try { localStorage.setItem(GETTING_STARTED_KEY, "dismissed"); } catch { /* storage blocked */ }
        $("homeRail").innerHTML = homeRailHtml();
        if (!$("homeRail").innerHTML.trim()) $("homeLayout").classList.remove("has-rail");
        break;
      default: break;
    }
  }

  function onDashboardInput(e) {
    if (e.target.id !== "homeSearch") return;
    homeState.search = e.target.value;
    renderHomeResults(false);
  }
  function onDashboardChange(e) {
    if (e.target.id !== "homeSort") return;
    homeState.sortKey = e.target.value;
    homeState.sortDir = SORT_DEFAULT_DIR[e.target.value];
    saveHomePrefs();
    renderHomeResults(false);
  }

'''
swap_block("  function onDashboardClick(e) {", "  function handleSessionExpired() {", NEW_CLICK)

# 3. New roadmap dialog, create submit, delete confirmation (typed name when there is progress)
NEW_DIALOGS = r'''  function openCreateRoadmapModal() {
    const thisMonth = currentMonthKey();
    const hasBuiltin = dashboardRoadmaps.some((r) => r.source === BUILTIN_SOURCE);
    $("modalHost").querySelector(".modal").innerHTML = `
      <h2>New roadmap</h2>
      <form id="createRoadmapForm" novalidate>
        <div class="option-list" role="radiogroup" aria-label="How do you want to start?">
          <label class="option-row is-selected">
            <input type="radio" name="newRoadmapKind" value="blank" checked />
            <span class="option-body">
              <span class="option-title">Blank roadmap</span>
              <span class="option-desc">Build your own plan with months, sections, topics and tasks.</span>
            </span>
          </label>
          <label class="option-row${hasBuiltin ? " is-disabled" : ""}">
            <input type="radio" name="newRoadmapKind" value="builtin" ${hasBuiltin ? "disabled" : ""} />
            <span class="option-body">
              <span class="option-title">AI Engineer roadmap</span>
              <span class="option-desc">${hasBuiltin ? "You already have this roadmap." : "The 10-month Production AI Engineer plan, restored with fresh progress."}</span>
            </span>
          </label>
          <label class="option-row is-disabled" title="Coming soon: describe a goal and let AI draft the plan.">
            <input type="radio" name="newRoadmapKind" value="ai" disabled />
            <span class="option-body">
              <span class="option-title">Describe a goal (AI) <span class="badge badge-soon">Soon</span></span>
              <span class="option-desc">Describe a goal and let AI draft the plan.</span>
            </span>
          </label>
        </div>

        <div id="newBlankFields">
          <div class="field">
            <label for="newRoadmapName">Roadmap name</label>
            <input type="text" id="newRoadmapName" maxlength="80" autocomplete="off" placeholder="e.g. Learn Rust in 12 weeks" />
          </div>
          <div class="field">
            <label for="newRoadmapDesc">Description (optional)</label>
            <textarea id="newRoadmapDesc" maxlength="300" placeholder="What is this plan for?" aria-describedby="newRoadmapCount"></textarea>
            <p class="field-hint" id="newRoadmapCount">0 / 300</p>
          </div>
          <div class="field">
            <label for="newRoadmapStart">Month 1 starts in</label>
            <input type="month" id="newRoadmapStart" value="${esc(thisMonth)}" min="${esc(thisMonth)}" />
          </div>
        </div>
        <p id="createRoadmapError" class="auth-error" role="alert"></p>
        <div class="modal-actions">
          <button type="button" class="btn" data-action="close-modal">Cancel</button>
          <button type="submit" class="btn btn-primary" id="createRoadmapSubmit">Create roadmap</button>
        </div>
      </form>`;
    showModal();
    $("newRoadmapName").focus();
  }

  // Show the blank-roadmap fields only for "Blank roadmap"; relabel the button for "AI Engineer roadmap".
  function syncCreateKind() {
    const checked = document.querySelector('input[name="newRoadmapKind"]:checked');
    const kind = checked ? checked.value : "blank";
    document.querySelectorAll(".option-row").forEach((row) => {
      row.classList.toggle("is-selected", !!row.querySelector("input:checked"));
    });
    $("newBlankFields").classList.toggle("hidden", kind !== "blank");
    $("createRoadmapSubmit").textContent = kind === "builtin" ? "Restore roadmap" : "Create roadmap";
    $("createRoadmapError").textContent = "";
  }

  async function submitCreateRoadmap() {
    const checked = document.querySelector('input[name="newRoadmapKind"]:checked');
    if (checked && checked.value === "builtin") { closeModal(); restoreBuiltinRoadmap(); return; }
    const error = $("createRoadmapError");
    const name = $("newRoadmapName").value.trim();
    const startMonth = $("newRoadmapStart").value;
    error.textContent = "";
    if (!name) { error.textContent = "Give your roadmap a name."; $("newRoadmapName").focus(); return; }
    if (startMonth && startMonth < currentMonthKey()) {
      error.textContent = "Start month can't be before the current month.";
      return;
    }
    const submit = $("createRoadmapSubmit");
    submit.disabled = true;
    try {
      const res = await window.RoadmapApi.create({
        name,
        description: $("newRoadmapDesc").value.trim(),
        startMonth: startMonth || undefined,
      });
      closeModal();
      openRoadmap(res.roadmap.id);
    } catch (e) {
      if (e.status === 401) { handleSessionExpired(); return; }
      error.textContent = e.message;
      submit.disabled = false;
    }
  }

  function confirmDeleteRoadmap(id) {
    const roadmap = dashboardRoadmaps.find((r) => String(r.id) === String(id));
    if (!roadmap) return;
    const needsName = roadmapHasProgress(roadmap);
    const s = roadmap.stats;
    const trigger = document.querySelector(
      `.roadmap-card[data-id="${roadmap.id}"] [data-menu-trigger], .rt-row[data-id="${roadmap.id}"] [data-menu-trigger]`,
    );
    $("modalHost").querySelector(".modal").innerHTML = `
      <h2>Delete “${esc(roadmap.name)}”?</h2>
      <form id="deleteRoadmapForm" novalidate>
        <p class="dialog-text">
          This permanently deletes the roadmap and all of its progress: statuses, notes, links, due dates
          and anything you added. This can't be undone.${s && s.completed > 0 ? ` You have completed ${s.completed} of ${s.total} tasks.` : ""}
        </p>
        ${needsName ? `
          <div class="field">
            <label for="deleteConfirmName">Type the roadmap name to confirm</label>
            <input type="text" id="deleteConfirmName" autocomplete="off" spellcheck="false" data-name="${esc(roadmap.name)}" />
            <p class="field-hint">Type exactly: <strong>${esc(roadmap.name)}</strong></p>
          </div>` : ""}
        <div class="modal-actions">
          <button type="button" class="btn" data-action="close-modal" id="deleteCancelBtn">Cancel</button>
          <button type="button" class="btn btn-danger" data-action="confirm-delete-roadmap" data-id="${roadmap.id}"
                  id="deleteConfirmBtn" ${needsName ? "disabled" : ""}>Delete roadmap</button>
        </div>
      </form>`;
    showModal(trigger);
    $("deleteCancelBtn").focus();
  }

'''
swap_block("  function openCreateRoadmapModal() {", "  async function deleteRoadmap(id) {", NEW_DIALOGS)

# 4. Shared modal behaviour: remember where focus was, give the dialog its title as its name,
#    restore focus on close; (Escape and the Tab trap are wired below)
once("""  function closeModal() {
    document.getElementById("modalHost").classList.add("hidden");
  }""", """  // Dialogs opened with showModal() return focus to what opened them when they close.
  let modalReturnFocus = null;
  function showModal(returnFocus) {
    const host = document.getElementById("modalHost");
    const modal = host.querySelector(".modal");
    modalReturnFocus = returnFocus || document.activeElement;
    const title = modal.querySelector("h2");
    if (title) { title.id = "modalTitle"; modal.setAttribute("aria-labelledby", "modalTitle"); }
    else modal.removeAttribute("aria-labelledby");
    host.classList.remove("hidden");
  }
  function closeModal() {
    const host = document.getElementById("modalHost");
    if (host.classList.contains("hidden")) return;
    host.classList.add("hidden");
    const back = modalReturnFocus;
    modalReturnFocus = null;
    if (back && back !== document.body && document.contains(back) && typeof back.focus === "function") back.focus();
  }
  // Keep Tab / Shift+Tab inside the open dialog.
  function trapModalFocus(e) {
    const focusable = [...document.querySelectorAll("#modalHost .modal a[href], #modalHost .modal button, #modalHost .modal input, #modalHost .modal select, #modalHost .modal textarea, #modalHost .modal [tabindex]")]
      .filter((el) => !el.disabled && el.tabIndex >= 0 && el.offsetParent !== null);
    if (!focusable.length) { e.preventDefault(); return; }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && (document.activeElement === first || !document.querySelector("#modalHost .modal").contains(document.activeElement))) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  }""")
once("""    host.classList.remove("hidden");
    $("aboutCloseBtn").focus();""", """    showModal();
    $("aboutCloseBtn").focus();""")

# 5. Event wiring
once("""    $("modalHost").addEventListener("submit", (e) => {
      if (e.target.id !== "createRoadmapForm") return;
      e.preventDefault();
      submitCreateRoadmap();
    });""", """    $("modalHost").addEventListener("submit", (e) => {
      if (e.target.id === "createRoadmapForm") { e.preventDefault(); submitCreateRoadmap(); }
      if (e.target.id === "deleteRoadmapForm") { // Enter in the name box
        e.preventDefault();
        const confirmBtn = $("deleteConfirmBtn");
        if (!confirmBtn.disabled) deleteRoadmap(Number(confirmBtn.dataset.id));
      }
    });
    $("modalHost").addEventListener("input", (e) => {
      if (e.target.id === "newRoadmapDesc") $("newRoadmapCount").textContent = `${e.target.value.length} / 300`;
      if (e.target.id === "deleteConfirmName") $("deleteConfirmBtn").disabled = e.target.value.trim() !== e.target.dataset.name;
    });
    $("modalHost").addEventListener("change", (e) => {
      if (e.target.name === "newRoadmapKind") syncCreateKind();
    });
    // Escape closes the open dialog; Tab stays inside it.
    document.addEventListener("keydown", (e) => {
      if ($("modalHost").classList.contains("hidden")) return;
      if (e.key === "Escape") { e.preventDefault(); closeModal(); }
      else if (e.key === "Tab") trapModalFocus(e);
    });""")
once("""    $("dashboardContent").addEventListener("click", onDashboardClick);""",
     """    $("dashboardContent").addEventListener("click", onDashboardClick);
    $("dashboardContent").addEventListener("input", onDashboardInput);
    $("dashboardContent").addEventListener("change", onDashboardChange);""")
once("    initSidebar();\n", "    initSidebar();\n    loadHomePrefs();\n")

open(P, "w", encoding="utf-8").write(s)
for required in ("function loadHomePrefs", "function visibleRoadmaps", "function roadmapTable", "function renderHomeResults",
                 "function homeRailHtml", "function showModal", "function syncCreateKind", "function onDashboardInput"):
    assert s.count(required) == 1, f"{required}: expected exactly one definition, found {s.count(required)}"
assert s.count("function roadmapCard") == 1 and s.count("function summaryBar") == 1 and s.count("function renderDashboard") == 1
print("js/app.js updated")
