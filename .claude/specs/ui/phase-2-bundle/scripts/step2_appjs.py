"""Phase 2 / js/app.js: shell, Home, sidebar, routing, About. Run from the repo root: python3 step2_appjs.py"""
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


# 1. enterDashboard -> renderDashboard (everything up to restoreBuiltinRoadmap):
#    login landing, shell helpers, About, routing, Home cards, sidebar switcher, card menus
NEW_ENTER = r'''  // Called once the user is authenticated: lands them on the roadmap named in
  // the URL (#/r/12/overview) or, otherwise, on the roadmap list.
  function enterDashboard(user) {
    const firstName = user.firstName || "";
    const lastName = user.lastName || "";
    Object.assign(session, { username: user.username, firstName, lastName });
    resetRoadmapSession(null, 0);
    progress = normalizeProgress(null);
    const fullName = [firstName, lastName].filter(Boolean).join(" ") || user.username;
    $("profileName").textContent = fullName;
    $("panelFullName").textContent = fullName;
    $("panelUsername").textContent = "@" + user.username;
    $("profileAvatar").textContent = initialsOf(firstName, lastName, user.username);
    hideAuth();
    const route = parseRoute();
    if (route) {
      openRoadmap(route.id, { view: route.view, push: false });
    } else {
      replaceRoute("#/"); // so Back from a roadmap lands on a real Home entry
      showDashboard();
    }
  }

  function initialsOf(firstName, lastName, username) {
    const two = `${(firstName || "").charAt(0)}${(lastName || "").charAt(0)}`;
    return (two.length === 2 ? two : String(username || "?").slice(0, 2)).toUpperCase();
  }

  // ---------------------------------------------------------
  // App shell: sidebar, context (home / roadmap), About
  // ---------------------------------------------------------
  const SIDEBAR_KEY = "roadmap-dashboard:sidebar";

  // Elements marked data-icon="name" get their SVG here (names are fixed identifiers).
  function hydrateIcons() {
    document.querySelectorAll("[data-icon]").forEach((el) => {
      el.innerHTML = window.Icons.svg(el.dataset.icon, { size: el.classList.contains("nav-icon") ? 20 : 14 });
    });
    $("sidebarOpenBtn").innerHTML = window.Icons.svg("menu", { size: 20 });
  }

  function setContext(ctx) {
    const home = ctx === "home";
    $("appShell").dataset.context = ctx;
    $("sidebarHome").classList.toggle("hidden", !home);
    $("sidebarRoadmap").classList.toggle("hidden", home);
    $("crumbRoadmap").classList.toggle("hidden", home);
    $("crumbHome").innerHTML = home
      ? `<span class="crumb-current">Roadmaps</span>`
      : `<button type="button" class="crumb-link" data-action="go-home">Roadmaps</button>`;
    closeNav();
  }

  function openNav() {
    $("appShell").classList.add("nav-open");
    $("sidebarScrim").hidden = false;
    $("sidebarOpenBtn").setAttribute("aria-expanded", "true");
  }
  function closeNav() {
    $("appShell").classList.remove("nav-open");
    $("sidebarScrim").hidden = true;
    $("sidebarOpenBtn").setAttribute("aria-expanded", "false");
  }
  function setSidebarCollapsed(collapsed, remember) {
    $("appShell").classList.toggle("is-collapsed", collapsed);
    const btn = $("sidebarCollapseBtn");
    btn.setAttribute("aria-pressed", String(collapsed));
    btn.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
    if (remember) {
      try { localStorage.setItem(SIDEBAR_KEY, collapsed ? "collapsed" : "expanded"); } catch { /* storage blocked */ }
    }
  }
  function initSidebar() {
    let saved = null;
    try { saved = localStorage.getItem(SIDEBAR_KEY); } catch { /* storage blocked */ }
    setSidebarCollapsed(saved === "collapsed", false);
  }

  function openAboutModal() {
    const host = $("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>About Roadmap Tracker</h2>
      <p class="about-text">Track your progress through structured roadmaps, starting with a 10-month Production AI Engineer plan, or build your own.</p>
      <ul class="about-list">
        <li>&copy; ${new Date().getFullYear()} Roadmap Tracker. All rights reserved.</li>
        <li>Developed by <a href="mailto:upendra.kumar48762@gmail.com">upendra.kumar48762@gmail.com</a></li>
        <li><a href="https://github.com/imkushwaha" target="_blank" rel="noopener">GitHub: imkushwaha</a></li>
        <li>If this tool helps you, please <a href="https://github.com/imkushwaha" target="_blank" rel="noopener">star the repo</a>.</li>
        <li>Built with planning &amp; development assistance from <strong>Claude</strong> (Anthropic AI).</li>
        <li>Open source. Contributions welcome.</li>
      </ul>
      <div class="modal-actions">
        <button type="button" class="btn btn-primary" data-action="close-modal" id="aboutCloseBtn">Close</button>
      </div>`;
    host.classList.remove("hidden");
    $("aboutCloseBtn").focus();
  }

  // ---------------------------------------------------------
  // Routing: plain #hash URLs, no router library.
  //   #/                      roadmap list
  //   #/r/12/overview         roadmap 12, Overview view
  // pushState adds a history entry (Back works); replaceState does not.
  // ---------------------------------------------------------
  let lastHash = window.location.hash;

  function parseRoute() {
    const m = /^#\/r\/(\d+)(?:\/([a-z]+))?$/.exec(window.location.hash);
    return m ? { id: Number(m[1]), view: m[2] || "overview" } : null;
  }
  function routeFor(id, view) { return `#/r/${id}/${view}`; }
  function navigate(hash) {
    if (window.location.hash === hash) return;
    window.history.pushState(null, "", hash);
    lastHash = hash;
  }
  function replaceRoute(hash) {
    if (window.location.hash !== hash) window.history.replaceState(null, "", hash);
    lastHash = hash;
  }
  function validView(view) {
    const tab = document.querySelector(`.tab[data-view="${view}"]`);
    return tab && !tab.classList.contains("hidden") && VIEW_RENDERERS[view] ? view : "overview";
  }

  // Browser Back / Forward.
  async function onPopState() {
    if (!session.username) { lastHash = window.location.hash; return; }
    const route = parseRoute();
    const inRoadmap = session.roadmapId != null;
    if (inRoadmap && !(route && route.id === session.roadmapId)) {
      if (!(await settleUnsavedChanges("Leave"))) { // stay put and restore the URL
        window.history.pushState(null, "", lastHash || "#/");
        return;
      }
    }
    lastHash = window.location.hash;
    if (route && session.roadmapId === route.id) { setView(validView(route.view), { silent: true }); return; }
    if (route) { openRoadmap(route.id, { view: route.view, push: false }); return; }
    if (inRoadmap) {
      resetRoadmapSession(null, 0);
      progress = normalizeProgress(null);
      closeModal();
    }
    showDashboard();
  }

  // ---------------------------------------------------------
  // Roadmap dashboard (post-login landing page)
  // ---------------------------------------------------------
  let dashboardRoadmaps = [];
  let stripsAnimated = false; // the strips fill in once per visit, not on every redraw
  const MAX_ROADMAPS = 20;

  function hideDashboard() { $("dashboardScreen").classList.add("hidden"); }

  function dashboardSkeleton() {
    const card = `
      <article class="roadmap-card is-skeleton" aria-hidden="true">
        <span class="skeleton" style="height:22px;width:60%"></span>
        <span class="skeleton" style="height:36px"></span>
        <span class="skeleton" style="height:8px"></span>
        <span class="skeleton" style="height:36px;margin-top:auto"></span>
      </article>`;
    return `
      <div class="page-head"><div><h1 class="page-title">Roadmaps</h1><p class="page-lead">Loading your roadmaps…</p></div></div>
      <div class="roadmap-grid">${card}${card}${card}</div>`;
  }

  async function showDashboard() {
    closeAllMenus();
    closeCardMenus();
    unlockApp();
    setContext("home");
    document.title = "Roadmap Tracker";
    $("roadmapScreen").classList.add("hidden");
    $("dashboardScreen").classList.remove("hidden");
    $("dashboardContent").innerHTML = dashboardSkeleton();
    let res;
    try {
      res = await window.RoadmapApi.list();
    } catch (e) {
      if (e.status === 401) { handleSessionExpired(); return; }
      $("dashboardContent").innerHTML = `
        <div class="dashboard-status">
          <p>We couldn't load your roadmaps: ${esc(e.message)}</p>
          <button type="button" class="btn btn-primary" data-action="retry-dashboard">Try again</button>
        </div>`;
      return;
    }
    renderDashboard(res.roadmaps);
  }

  function describeActivity(iso) {
    if (!iso) return "Not started yet";
    const days = daysBetween(new Date(iso), new Date());
    if (days <= 0) return "Last activity today";
    if (days === 1) return "Last activity yesterday";
    return "Last activity " + days + " days ago";
  }

  // ----- Month Strip data from a roadmap's server-side stats -----
  function monthKeyOffset(startMonth, offset) {
    const [y, m] = (startMonth || currentMonthKey()).split("-").map(Number);
    return new Date(y, m - 1 + offset, 1);
  }
  // 0-based index of the current calendar month within the roadmap, or -1.
  function currentMonthIndex(startMonth, count) {
    const start = monthKeyOffset(startMonth, 0);
    const idx = (TODAY.getFullYear() - start.getFullYear()) * 12 + (TODAY.getMonth() - start.getMonth());
    return idx >= 0 && idx < count ? idx : -1;
  }
  function stripMonths(stats) {
    const current = currentMonthIndex(stats.startMonth, stats.months.length);
    return stats.months.map((m, i) => ({
      label: monthKeyOffset(stats.startMonth, i).toLocaleDateString(undefined, { month: "short" }),
      title: `Month ${m.number}: ${m.title || "Untitled"} (${m.completed} of ${m.total} tasks complete)`,
      total: m.total, completed: m.completed, inProgress: m.inProgress, blocked: m.blocked,
      current: i === current,
    }));
  }
  const pctOf = (stats) => (stats && stats.total ? Math.round((stats.completed / stats.total) * 100) : 0);

  function cardAction(stats) {
    if (!stats) return "Open";
    if (stats.total === 0) return "Build plan";
    if (stats.completed === stats.total) return "Review";
    return stats.completed + stats.inProgress + stats.blocked > 0 ? "Continue" : "Start";
  }

  function monthPosition(stats) {
    if (!stats || !stats.months.length) return "";
    const idx = currentMonthIndex(stats.startMonth, stats.months.length);
    if (idx >= 0) return `Month ${idx + 1} of ${stats.months.length}`;
    const start = monthKeyOffset(stats.startMonth, 0);
    const before = TODAY < start;
    const label = start.toLocaleDateString(undefined, { month: "short", year: "numeric" });
    return before ? `Starts ${label}` : `${stats.months.length} months`;
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
          <div class="rc-menu">
            <button type="button" class="btn btn-ghost btn-icon btn-sm" data-menu-trigger aria-expanded="false"
                    aria-label="More actions for ${esc(r.name)}">${window.Icons.svg("more-horizontal", { size: 18 })}</button>
            <div class="rc-menu-panel hidden" role="group" aria-label="Actions for ${esc(r.name)}">
              <button type="button" class="profile-action-btn danger" data-action="delete-roadmap" data-id="${r.id}">Delete roadmap…</button>
            </div>
          </div>
        </div>
        ${r.description ? `<p class="roadmap-card-desc">${esc(r.description)}</p>` : `<p class="roadmap-card-desc"></p>`}
        ${progressBlock}
        <div class="rc-foot">
          <p class="roadmap-card-meta">${esc(describeActivity(r.lastActivityAt))}</p>
          <button type="button" class="btn btn-primary" data-action="open-roadmap" data-id="${r.id}">${cardAction(s)}</button>
        </div>
      </article>`;
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

  function renderDashboard(roadmaps) {
    dashboardRoadmaps = roadmaps;
    renderSidebarRoadmaps();
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

    $("dashboardContent").innerHTML = `
      <div class="page-head">
        <div>
          <h1 class="page-title">Roadmaps</h1>
          <p class="page-lead">Track progress across your plans.</p>
        </div>
        <div class="page-actions">${newBtn}</div>
      </div>
      ${restore}
      ${summaryBar(roadmaps)}
      <div class="roadmap-grid">${roadmaps.map((r) => roadmapCard(r, animate)).join("")}</div>`;
  }

  // Sidebar quick-switcher (Home only)
  function renderSidebarRoadmaps() {
    const host = $("sidebarRoadmapList");
    if (!dashboardRoadmaps.length) { host.innerHTML = `<p class="nav-empty">No roadmaps yet.</p>`; return; }
    host.innerHTML = dashboardRoadmaps.map((r) => `
      <button type="button" class="nav-item nav-roadmap" data-action="open-roadmap" data-id="${r.id}" title="${esc(r.name)}">
        <span class="nav-roadmap-top">
          <span class="nav-roadmap-name">${esc(r.name)}</span>
          ${r.stats ? `<span class="nav-roadmap-pct">${pctOf(r.stats)}%</span>` : ""}
        </span>
        ${r.stats ? window.MonthStrip.html(stripMonths(r.stats), { size: "sm" }) : ""}
      </button>`).join("");
  }

  // Inside a roadmap, the strip is computed live from the open roadmap's data.
  function renderSidebarStrip() {
    const cur = currentPhase();
    const months = allPhases().map((p) => {
      const st = phaseStats(p.id);
      return {
        label: phaseStartDate(p.number).toLocaleDateString(undefined, { month: "short" }),
        title: `Month ${p.number}: ${p.title} (${st.completed} of ${st.total} tasks complete)`,
        total: st.total, completed: st.completed, inProgress: st.inProgress, blocked: st.blocked,
        current: !!cur && cur.id === p.id,
      };
    });
    $("sidebarStrip").innerHTML = window.MonthStrip.html(months, { size: "md" });
  }

  // Per-card overflow menu (Home)
  function closeCardMenus() {
    document.querySelectorAll(".rc-menu-panel").forEach((panel) => {
      if (panel.classList.contains("hidden")) return;
      panel.classList.add("hidden");
      const trigger = panel.parentElement.querySelector("[data-menu-trigger]");
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  }
  function toggleCardMenu(trigger) {
    const panel = trigger.parentElement.querySelector(".rc-menu-panel");
    const willOpen = panel.classList.contains("hidden");
    closeCardMenus();
    if (!willOpen) return;
    panel.classList.remove("hidden");
    trigger.setAttribute("aria-expanded", "true");
  }

'''
swap_block("  // Called once the user is authenticated: lands them on the roadmap dashboard.",
           "  async function restoreBuiltinRoadmap() {", NEW_ENTER)

# 2. Click handling for Home and sidebar
NEW_CLICK = r'''  function onDashboardClick(e) {
    const trigger = e.target.closest("[data-menu-trigger]");
    if (trigger) { e.stopPropagation(); toggleCardMenu(trigger); return; }
    const el = e.target.closest("[data-action]");
    if (!el) {
      // A click on the card itself (not on one of its buttons) opens it.
      const card = e.target.closest(".roadmap-card[data-id]");
      if (card && !e.target.closest("button, a, .rc-menu")) openRoadmap(Number(card.dataset.id));
      return;
    }
    closeCardMenus();
    switch (el.dataset.action) {
      case "open-roadmap": openRoadmap(Number(el.dataset.id)); break;
      case "delete-roadmap": confirmDeleteRoadmap(el.dataset.id); break;
      case "restore-builtin": restoreBuiltinRoadmap(); break;
      case "create-roadmap": openCreateRoadmapModal(); break;
      case "retry-dashboard": showDashboard(); break;
      default: break;
    }
  }

'''
swap_block("  function onDashboardClick(e) {", "  function handleSessionExpired() {", NEW_CLICK)

# 3. openRoadmap: loading skeleton, view + URL handling
NEW_OPEN = r'''  // Shell with a skeleton while a roadmap loads (the sidebar and top bar stay put).
  function showRoadmapLoading() {
    hideAuth();
    unlockApp();
    setContext("roadmap");
    $("dashboardScreen").classList.add("hidden");
    $("roadmapScreen").classList.remove("hidden");
    $("roadmapTitle").textContent = "Loading…";
    $("roadmapSubtitle").textContent = "";
    $("crumbRoadmapName").textContent = "Loading…";
    $("sidebarStrip").innerHTML = "";
    $("tabs").classList.add("is-loading");
    $("main").innerHTML = `
      <div aria-busy="true">
        <span class="skeleton" style="height:28px;width:220px;margin-bottom:20px"></span>
        <div class="grid grid-stats">
          ${"<span class=\"skeleton\" style=\"height:92px\"></span>".repeat(4)}
        </div>
        <span class="skeleton" style="height:320px;margin-top:20px"></span>
      </div>`;
  }

  async function openRoadmap(id, opts) {
    const options = opts || {};
    hideDashboard();
    showRoadmapLoading();
    let res;
    try {
      res = await window.RoadmapApi.getProgress(id);
    } catch (e) {
      if (e.status === 401) { showAuth("login"); return; }
      // Never fall through to an empty editable state: saving it would overwrite real data.
      showBlock("Couldn't load this roadmap", e.message, [
        ["Try again", () => openRoadmap(id, options)],
        ["Back to roadmaps", () => { hideAuth(); replaceRoute("#/"); showDashboard(); }],
      ]);
      return;
    }
    resetRoadmapSession(res.roadmap.id, res.version || 0);
    DATA = res.roadmap.source === "builtin_ai_engineer" ? BUILTIN_DATA : BLANK_DATA;
    progress = normalizeProgress(res.data);
    resetViewState();
    rebuildIndex();
    syncTabs();
    hideAuth();
    unlockApp();
    setContext("roadmap");
    $("tabs").classList.remove("is-loading");
    $("roadmapTitle").textContent = res.roadmap.name;
    $("roadmapH1").textContent = res.roadmap.name;
    $("roadmapSubtitle").textContent = res.roadmap.description;
    $("crumbRoadmapName").textContent = res.roadmap.name;
    document.title = res.roadmap.name + " — Roadmap Tracker";
    state.search = "";
    session.roadmapSource = res.roadmap.source;
    $("roadmapMenuName").textContent = res.roadmap.name;
    $("roadmapSearch").value = "";
    closeAllMenus();
    setSaveStatus("saved");
    const view = validView(options.view || "overview");
    setView(view, { silent: true });
    if (options.push === false) replaceRoute(routeFor(res.roadmap.id, view));
    else navigate(routeFor(res.roadmap.id, view));
    window.scrollTo(0, 0);
    checkMilestones();
    if (res.data === null && res.roadmap.source === "builtin_ai_engineer" && readLegacyLocalData()) {
      openLegacyModal(false);
    }
  }

'''
swap_block("  async function openRoadmap(id) {", "  // Per-roadmap UI state must not leak", NEW_OPEN)

# 4. rerender / setView
NEW_RERENDER = r'''  function rerender() {
    const main = document.getElementById("main");
    VIEW_RENDERERS[state.view](main);
    renderSidebarStrip();
  }
  function setView(view, opts) {
    state.view = view;
    document.querySelectorAll(".tab").forEach((t) => {
      const active = t.dataset.view === view;
      t.classList.toggle("active", active);
      if (active) t.setAttribute("aria-current", "page"); else t.removeAttribute("aria-current");
    });
    if (!(opts && opts.silent) && session.roadmapId != null) replaceRoute(routeFor(session.roadmapId, view));
    rerender();
  }

'''
swap_block("  function rerender() {", "  // ---------------------------------------------------------\n  // Theme", NEW_RERENDER)

# 5. The account menu is one element in the top bar now: no more moving it between screens
swap_block("  function mountAccountMenu(slotId) {", "  function wireEvents() {", "")

# 6. Back to Home adds a history entry; logging out forgets the roadmap URL
once("""    progress = normalizeProgress(null);
    closeModal();
    showDashboard();
  }

  function onDashboardClick""", """    progress = normalizeProgress(null);
    closeModal();
    navigate("#/");
    showDashboard();
  }

  function onDashboardClick""")
once("""    // A full reload drops every piece of in-memory, user-specific state.
    window.location.reload();""", """    // Forget the roadmap URL so the next person to log in starts at Home, then
    // reload to drop every piece of in-memory, user-specific state.
    window.history.replaceState(null, "", window.location.pathname);
    window.location.reload();""")

# 7. Event wiring
once("""    document.getElementById("tabs").addEventListener("click", (e) => {
      const btn = e.target.closest(".tab");
      if (btn) setView(btn.dataset.view);
    });
""", """    document.getElementById("tabs").addEventListener("click", (e) => {
      const btn = e.target.closest(".tab");
      if (!btn) return;
      setView(btn.dataset.view);
      closeNav();
      window.scrollTo(0, 0);
    });

    // Sidebar: roadmap switcher, drawer and collapse
    $("sidebar").addEventListener("click", onDashboardClick);
    $("sidebarOpenBtn").addEventListener("click", openNav);
    $("sidebarScrim").addEventListener("click", closeNav);
    $("sidebarCollapseBtn").addEventListener("click", () => {
      setSidebarCollapsed(!$("appShell").classList.contains("is-collapsed"), true);
    });
    // Actions available from several places (menus, sidebar, breadcrumb)
    document.addEventListener("click", (e) => {
      const el = e.target.closest("[data-action]");
      if (!el) { closeCardMenus(); return; }
      if (el.dataset.action === "about") { closeAllMenus(); closeNav(); openAboutModal(); }
      if (el.dataset.action === "go-home") backToDashboard();
      if (!el.closest(".rc-menu")) closeCardMenus();
    });
    window.addEventListener("popstate", onPopState);
""")
once("""      const open = menus.find((m) => m.isOpen());
      if (open) open.close(true);
    });""", """      const open = menus.find((m) => m.isOpen());
      if (open) open.close(true);
      closeCardMenus();
      if ($("appShell").classList.contains("nav-open")) { closeNav(); $("sidebarOpenBtn").focus(); }
    });""")
once("    initTheme();\n    renderAuthPanelStrip();", "    initTheme();\n    hydrateIcons();\n    initSidebar();\n    renderAuthPanelStrip();")

open(P, "w", encoding="utf-8").write(s)
for required in ("function hydrateIcons", "function setContext", "function parseRoute", "function onPopState", "function renderDashboard",
                 "function renderSidebarRoadmaps", "function renderSidebarStrip", "function openAboutModal", "function showRoadmapLoading"):
    assert s.count(required) == 1, f"{required}: expected exactly one definition, found {s.count(required)}"
assert s.count("function describeActivity") == 1, "duplicate describeActivity"
for gone in ("mountAccountMenu", "dashboardAccountSlot", "roadmapAccountSlot", "app-header"):
    assert gone not in s, "leftover reference: " + gone
print("js/app.js updated")
