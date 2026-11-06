"""Phase 2 / index.html: replace the old dashboard overlay, app header and <main> with the app shell.
Run from the repo root: python3 step2_index.py"""
P = "index.html"
s = open(P, encoding="utf-8").read()

NEW_SHELL = r'''<div id="appShell" class="app-shell" data-context="home">
  <aside id="sidebar" class="sidebar" aria-label="Sidebar">
    <div class="sidebar-head">
      <img class="brand-mark" src="img/logo.svg" alt="" width="28" height="28" />
      <span class="sidebar-brand-text">Roadmap Tracker</span>
    </div>

    <nav class="sidebar-nav" aria-label="Primary">
      <!-- Home: switcher between roadmaps -->
      <div id="sidebarHome" class="sidebar-section">
        <button type="button" class="nav-item active" data-nav="home" aria-current="page" title="Roadmaps">
          <span class="nav-icon" data-icon="map"></span><span class="nav-label">Roadmaps</span>
        </button>
        <p class="nav-heading">Your roadmaps</p>
        <div id="sidebarRoadmapList" class="nav-list"></div>
      </div>

      <!-- Inside a roadmap: back link, roadmap card, views -->
      <div id="sidebarRoadmap" class="sidebar-section hidden">
        <button type="button" id="backToDashboardBtn" class="nav-item" title="All roadmaps">
          <span class="nav-icon" data-icon="arrow-left"></span><span class="nav-label">All roadmaps</span>
        </button>
        <div class="sidebar-roadmap-card">
          <p id="roadmapTitle" class="sidebar-roadmap-name">Roadmap</p>
          <p id="roadmapSubtitle" class="sidebar-roadmap-desc"></p>
          <div id="sidebarStrip" class="sidebar-strip"></div>
        </div>
        <p class="nav-heading">Views</p>
        <div id="tabs" class="nav-list">
          <button type="button" class="tab nav-item active" data-view="overview" title="Overview"><span class="nav-icon" data-icon="layout-grid"></span><span class="nav-label">Overview</span></button>
          <button type="button" class="tab nav-item" data-view="timeline" title="Timeline"><span class="nav-icon" data-icon="calendar"></span><span class="nav-label">Timeline</span></button>
          <button type="button" class="tab nav-item" data-view="kanban" title="Kanban"><span class="nav-icon" data-icon="columns"></span><span class="nav-label">Kanban</span></button>
          <button type="button" class="tab nav-item" data-view="checklist" title="Checklist"><span class="nav-icon" data-icon="list-checks"></span><span class="nav-label">Checklist</span></button>
          <button type="button" class="tab nav-item" data-view="thisweek" title="This week"><span class="nav-icon" data-icon="clock"></span><span class="nav-label">This week</span></button>
          <button type="button" class="tab nav-item" data-view="mastery" title="Skills checklist"><span class="nav-icon" data-icon="award"></span><span class="nav-label">Skills checklist</span></button>
          <button type="button" class="tab nav-item" data-view="reference" title="Reference"><span class="nav-icon" data-icon="book-open"></span><span class="nav-label">Reference</span></button>
        </div>
      </div>
    </nav>

    <div class="sidebar-foot">
      <button type="button" class="nav-item" data-action="about" title="About Roadmap Tracker">
        <span class="nav-icon" data-icon="help"></span><span class="nav-label">About</span>
      </button>
      <button type="button" id="sidebarCollapseBtn" class="nav-item sidebar-collapse-btn" aria-pressed="false" title="Collapse sidebar">
        <span class="nav-icon" data-icon="panel-left"></span><span class="nav-label">Collapse</span>
      </button>
    </div>
  </aside>
  <div id="sidebarScrim" class="sidebar-scrim" hidden></div>

  <div class="app-body">
    <header class="topbar">
      <button type="button" id="sidebarOpenBtn" class="btn btn-ghost btn-icon topbar-menu-btn" aria-label="Open navigation" aria-expanded="false" aria-controls="sidebar"></button>
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li id="crumbHome"><span class="crumb-current">Roadmaps</span></li>
          <li id="crumbRoadmap" class="hidden"><span id="crumbRoadmapName" class="crumb-current" aria-current="page"></span></li>
        </ol>
      </nav>
      <div class="topbar-actions">
        <input type="search" id="roadmapSearch" class="roadmap-search roadmap-only" placeholder="Search topics, tasks, notes…" aria-label="Search tasks" autocomplete="off" />
        <button type="button" id="panelSaveStatus" class="save-status roadmap-only" aria-live="polite"></button>
        <div class="profile-anchor roadmap-only">
          <button class="profile-trigger" id="roadmapMenuTrigger" aria-expanded="false" aria-controls="roadmapMenuPanel" aria-label="Roadmap settings">
            <span class="nav-icon" data-icon="settings"></span>
            <span class="roadmap-trigger-label">Roadmap</span>
            <span class="profile-trigger-caret" data-icon="chevron-down" aria-hidden="true"></span>
          </button>
          <div class="profile-panel hidden" id="roadmapMenuPanel" role="group" aria-label="Roadmap settings">
            <div class="profile-panel-header">
              <span class="profile-panel-fullname" id="roadmapMenuName">—</span>
              <span class="profile-panel-username">Roadmap settings</span>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn" id="startMonthBtn">Set start month…</button>
              <button class="profile-action-btn" id="exportBtn">Export progress (JSON)</button>
              <button class="profile-action-btn" id="importBtn">Import progress (JSON)</button>
              <input type="file" id="importFile" accept="application/json" class="hidden" />
              <button id="legacyImportBtn" class="profile-action-btn hidden">Import old data from this browser…</button>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn danger" id="resetBtn">Reset progress…</button>
            </div>
          </div>
        </div>
        <div class="profile-anchor" id="profileAnchor">
          <button class="profile-trigger" id="profileTrigger" aria-expanded="false" aria-controls="profilePanel" aria-label="Account menu">
            <span class="avatar" id="profileAvatar" aria-hidden="true">?</span>
            <span class="profile-trigger-name" id="profileName">—</span>
            <span class="profile-trigger-caret" data-icon="chevron-down" aria-hidden="true"></span>
          </button>
          <div class="profile-panel hidden" id="profilePanel" role="group" aria-label="Account">
            <div class="profile-panel-header">
              <span class="profile-panel-fullname" id="panelFullName">—</span>
              <span class="profile-panel-username" id="panelUsername">—</span>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <span class="profile-panel-label">Appearance</span>
              <div class="profile-theme-btns">
                <button class="profile-theme-btn" id="themeLightBtn" data-theme="light">Light</button>
                <button class="profile-theme-btn" id="themeDarkBtn" data-theme="dark">Dark</button>
                <button class="profile-theme-btn" id="themeSystemBtn" data-theme="system">System</button>
              </div>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn" data-action="about">About Roadmap Tracker</button>
            </div>
            <div class="profile-panel-sep"></div>
            <div class="profile-panel-section">
              <button class="profile-action-btn profile-logout" id="logoutBtn">Log out</button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <div id="dashboardScreen" class="page hidden">
      <div class="page-inner" id="dashboardContent" aria-live="polite"></div>
    </div>
    <div id="roadmapScreen" class="page hidden">
      <h1 class="sr-only" id="roadmapH1">Roadmap</h1>
      <main id="main" class="page-inner"></main>
    </div>
  </div>
</div>
'''

start = '<div id="dashboardScreen"'
end = '<div id="toastHost"'
assert s.count(start) == 1 and s.count(end) == 1, "dashboardScreen/toastHost markers not found"
a, b = s.index(start), s.index(end)
removed = s[a:b]
for gone in ('id="roadmapTitle"', 'id="tabs"', 'id="roadmapSearch"', 'id="panelSaveStatus"', 'id="profileAnchor"', 'id="main"'):
    assert gone in removed, "expected to replace an element that is not there: " + gone
s = s[:a] + NEW_SHELL.rstrip("\n") + "\n\n" + s[b:]

old = '<link rel="stylesheet" href="css/auth.css" />'
assert s.count(old) == 1
s = s.replace(old, old + '\n<link rel="stylesheet" href="css/shell.css" />\n<link rel="stylesheet" href="css/home.css" />')

open(P, "w", encoding="utf-8").write(s)
for required in ('id="appShell"', 'id="sidebar"', 'id="sidebarHome"', 'id="sidebarRoadmap"', 'id="sidebarRoadmapList"', 'id="sidebarStrip"',
                 'id="backToDashboardBtn"', 'id="tabs"', 'id="crumbHome"', 'id="crumbRoadmapName"', 'id="roadmapSearch"',
                 'id="panelSaveStatus"', 'id="roadmapMenuTrigger"', 'id="profileAnchor"', 'id="profileAvatar"', 'id="themeSystemBtn"',
                 'id="dashboardScreen"', 'id="dashboardContent"', 'id="roadmapScreen"', 'id="roadmapH1"', 'id="main"',
                 'id="sidebarCollapseBtn"', 'id="sidebarOpenBtn"', 'id="sidebarScrim"'):
    assert required in s, "missing " + required
assert s.count('data-view="') == 7, "expected 7 view buttons"
print("index.html updated")
