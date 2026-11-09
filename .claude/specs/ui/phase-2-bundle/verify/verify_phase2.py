"""Phase 2 verification. Usage:
    python3 verify_phase2.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Needs the demo server from the Phase 0 spec (serve-demo.js) running; the demo user is imkushwaha / demo-pass-123.
Exit code 0 only if every check passes."""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots-p2"
os.makedirs(SHOTS, exist_ok=True)
RUN = int(time.time()) % 1000000
results, AXE_SOURCE = [], None


def check(ok, message):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + message)


def audit(page, label):
    global AXE_SOURCE
    if AXE_SOURCE is None:
        AXE_SOURCE = open(AXE, encoding="utf-8").read()
    page.evaluate(AXE_SOURCE)  # DevTools evaluation works under the app's CSP; <script> injection does not
    v = page.evaluate("""async () => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] } });
      return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0] && v.nodes[0].target.join(' ')));
    }""")
    check(not v, f"axe 0 violations: {label}" + ("" if not v else "  -> " + "; ".join(v)))


def new_context(browser, width=1440, height=900, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
    page = ctx.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: page.problems.append(m.text) if m.type == "error" and "401" not in m.text and "404" not in m.text else None)
    return ctx, page


def fresh_user(ctx, tag):
    name = f"p2{tag}_{RUN}"
    r = ctx.request.post(BASE + "/api/auth/register", data={"firstName": "Rita", "lastName": "Route", "username": name, "password": "longenough1"})
    assert r.status == 201, r.status
    return name


def login_demo(ctx):
    r = ctx.request.post(BASE + "/api/auth/login", data={"username": "imkushwaha", "password": "demo-pass-123"})
    assert r.status == 200, r.status


def home(page):
    page.goto(BASE)
    page.wait_for_selector(".summary-bar", timeout=10000)


def visible(page, selector):
    return page.locator(selector).first.is_visible()


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ============ A. API contract ============
    ctx, page = new_context(browser)
    login_demo(ctx)
    data = ctx.request.get(BASE + "/api/roadmaps").json()
    r0 = data["roadmaps"][0]
    s = r0.get("stats") or {}
    check(s.get("total") == 849 and len(s.get("months", [])) == 10 and s.get("startMonth") == "2026-10", "API: built-in roadmap stats = 849 items, 10 months, startMonth 2026-10")
    check(all(k in s for k in ("completed", "inProgress", "blocked", "completedLast7Days")), "API: stats has status counts and completedLast7Days")
    check(s["completed"] > 0 and s["months"][0]["completed"] > 0, "API: demo progress is reflected in stats")
    check(not any(k in r0 for k in ("progressData", "progressVersion", "data")), "API: raw progress is never in the list response")
    check(ctx.request.get(BASE + "/api/roadmaps").headers.get("cache-control", "").find("no-store") >= 0, "API: list is not cacheable")
    DEMO_DONE = s["completed"]; DEMO_TOTAL = s["total"]; DEMO_WEEK = s["completedLast7Days"]
    ctx.close()

    # ============ B. Home (desktop, new user) ============
    ctx, page = new_context(browser)
    uname = fresh_user(ctx, "a")
    home(page)
    check(page.get_attribute("#appShell", "data-context") == "home", "Home: shell context is 'home'")
    check(page.inner_text("h1.page-title") == "Roadmaps", "Home: one H1 'Roadmaps'")
    check(not page.locator("body.locked").count(), "Home: app is unlocked")
    check(visible(page, "#sidebar") and visible(page, "#sidebarHome") and not visible(page, "#sidebarRoadmap"), "Home: sidebar shows the roadmap switcher, not the views")
    for sel in ("#roadmapSearch", "#panelSaveStatus", "#roadmapMenuTrigger"):
        check(not visible(page, sel), f"Home: roadmap-only control hidden: {sel}")
    check(visible(page, "#profileTrigger") and page.inner_text("#profileAvatar") == "RR", "Home: account menu with initials avatar RR")
    summary = " ".join(page.inner_text(".summary-bar").split())
    check("Roadmaps 1" in summary and "0 / 849" in summary and "0%" in summary, "Home: summary bar for a new account: " + summary)
    card = page.locator("article.roadmap-card").first
    check(card.locator(".rc-title").inner_text() == "AI Engineer Roadmap" and card.locator(".rc-badge").inner_text() == "Built-in", "Home: card title and Built-in badge")
    check(card.locator(".btn-primary").inner_text() == "Start", "Home: new roadmap's primary action is Start")
    check(card.locator(".strip-col").count() == 10, "Home: card strip has 10 months")
    expected_idx = page.evaluate("(() => { const n = new Date(); return (n.getFullYear() - 2026) * 12 + (n.getMonth() - 9); })()")
    pos = card.locator(".rc-meta span").nth(1).inner_text()
    exp = f"Month {expected_idx + 1} of 10" if 0 <= expected_idx < 10 else ("Starts Oct 2026" if expected_idx < 0 else "10 months")
    check(pos == exp, f"Home: month position text '{pos}' == expected '{exp}'")
    check((card.locator(".strip-col.is-current").count() == 1) == (0 <= expected_idx < 10), "Home: current month marker present exactly when today is inside the roadmap")
    check(card.locator(".rc-menu-panel").is_hidden() and page.get_attribute("article.roadmap-card [data-menu-trigger]", "aria-label").startswith("More actions for"), "Home: card menu closed and labelled")
    check(page.locator("#sidebarRoadmapList .nav-roadmap").count() == 1, "Home: sidebar switcher lists the roadmap")
    page.wait_for_timeout(900)  # let the strip animation finish
    page.screenshot(path=f"{SHOTS}/home-desktop-light.png")
    audit(page, "Home (desktop, light)")

    # ---- card menu, About, collapse
    trigger = page.locator("article.roadmap-card [data-menu-trigger]")
    trigger.click()
    check(page.locator(".rc-menu-panel").first.is_visible() and trigger.get_attribute("aria-expanded") == "true", "card menu opens")
    audit(page, "Home with card menu open")
    page.keyboard.press("Escape")
    check(page.locator(".rc-menu-panel").first.is_hidden() and trigger.get_attribute("aria-expanded") == "false", "Escape closes the card menu")
    page.click("#sidebar [data-action=about]"); page.wait_for_selector("#modalHost:not(.hidden)")
    check("Claude" in page.inner_text("#modalHost") and "github.com/imkushwaha" in page.inner_html("#modalHost") and page.evaluate("document.activeElement.id") == "aboutCloseBtn", "About dialog: credits, links, focus on Close")
    audit(page, "About dialog")
    page.click("#aboutCloseBtn")
    page.click("#profileTrigger"); page.locator("#profilePanel [data-action=about]").click(); page.wait_for_selector("#modalHost:not(.hidden)")
    check(True, "About also reachable from the account menu"); page.click("#aboutCloseBtn")
    page.click("#sidebarCollapseBtn")
    check(page.evaluate("document.getElementById('appShell').classList.contains('is-collapsed')") and page.evaluate("document.getElementById('sidebar').getBoundingClientRect().width") <= 70, "sidebar collapses to ~64px")
    check(page.get_attribute("#sidebarCollapseBtn", "aria-pressed") == "true", "collapse button has aria-pressed")
    audit(page, "Home with collapsed sidebar")
    page.reload(); page.wait_for_selector(".summary-bar")
    check(page.evaluate("document.getElementById('appShell').classList.contains('is-collapsed')"), "collapse is remembered after reload")
    page.click("#sidebarCollapseBtn")

    # ============ C. Open a roadmap, routing, live strip ============
    page.click("article.roadmap-card .btn-primary"); page.wait_for_selector(".stat-tile")
    hsh = page.evaluate("location.hash"); rid = hsh.split("/")[2]
    check(hsh == f"#/r/{rid}/overview", "opening pushes #/r/<id>/overview: " + hsh)
    check(page.get_attribute("#appShell", "data-context") == "roadmap" and visible(page, "#sidebarRoadmap") and not visible(page, "#sidebarHome"), "roadmap context: sidebar shows the views")
    for sel in ("#roadmapSearch", "#panelSaveStatus", "#roadmapMenuTrigger"):
        check(visible(page, sel), f"roadmap context: control visible: {sel}")
    check(page.inner_text("#crumbRoadmapName") == "AI Engineer Roadmap" and page.inner_text("#roadmapH1") == "AI Engineer Roadmap", "breadcrumb and hidden H1 carry the roadmap name")
    check(page.locator("#tabs .tab:visible").count() == 7, "7 view buttons visible for the built-in roadmap")
    check(page.get_attribute('.tab[data-view="overview"]', "aria-current") == "page", "active view has aria-current=page")
    page.click('.tab[data-view="kanban"]'); page.wait_for_selector(".kanban-board")
    check(page.evaluate("location.hash") == f"#/r/{rid}/kanban", "view change replaces the URL (kanban)")
    page.reload(); page.wait_for_selector(".kanban-board", timeout=10000)
    check(page.evaluate("location.hash") == f"#/r/{rid}/kanban" and visible(page, "#sidebarRoadmap"), "reload restores roadmap and view")
    page.go_back(); page.wait_for_selector(".summary-bar", timeout=10000)
    check(page.evaluate("location.hash") == "#/" and visible(page, "#sidebarHome"), "Back returns to Home (#/)")
    page.go_forward(); page.wait_for_selector(".kanban-board", timeout=10000)
    check(page.evaluate("location.hash") == f"#/r/{rid}/kanban", "Forward returns to the roadmap view")
    page.click('.tab[data-view="checklist"]'); page.wait_for_selector(".subtask-checkbox")
    before = page.get_attribute("#sidebarStrip .strip", "aria-label")
    page.locator(".subtask-checkbox").first.click()
    page.locator("#panelSaveStatus", has_text="Saved").wait_for(timeout=8000)
    after = page.get_attribute("#sidebarStrip .strip", "aria-label")
    check(before.startswith("0 of 849") and after.startswith("1 of 849"), f"sidebar strip updates live: '{before}' -> '{after}'")
    check("saved" in page.get_attribute("#panelSaveStatus", "class"), "save-status chip shows Saved")
    page.go_back(); page.wait_for_selector(".summary-bar", timeout=10000)
    page.locator("article.roadmap-card .btn-primary").click(); page.wait_for_selector(".stat-tile")
    page.click('.tab[data-view="checklist"]'); page.wait_for_selector(".subtask-checkbox")
    check(page.locator(".subtask-checkbox").first.is_checked(), "a change made just before pressing Back was saved")
    page.screenshot(path=f"{SHOTS}/roadmap-checklist-desktop-light.png")
    # ---- Roadmap settings menu (every item keeps working in its new place)
    page.click("#roadmapMenuTrigger")
    check(page.locator("#roadmapMenuPanel").is_visible() and page.inner_text("#roadmapMenuName") == "AI Engineer Roadmap", "roadmap settings menu opens and shows the roadmap name")
    audit(page, "roadmap settings menu open")
    with page.expect_download() as dl:
        page.click("#exportBtn")
    check(dl.value.suggested_filename.endswith(".json"), "Export progress downloads a .json file: " + dl.value.suggested_filename)
    page.click("#roadmapMenuTrigger"); page.click("#startMonthBtn"); page.wait_for_selector("#modalHost:not(.hidden)")
    check(page.locator("#modalHost input[type=month]").count() == 1, "Set start month opens a dialog with a month picker")
    page.click("#modalHost [data-action=close-modal]"); page.wait_for_selector("#modalHost.hidden", state="attached")
    page.click("#roadmapMenuTrigger"); page.click("#resetBtn"); page.wait_for_selector("#modalHost:not(.hidden)")
    check("reset" in page.inner_text("#modalHost").lower() and page.locator("#modalHost [data-action=confirm-reset]").count() == 1, "Reset progress asks for confirmation")
    page.click("#modalHost [data-action=close-modal]")
    check(page.locator("#importFile").count() == 1 and page.locator("#importBtn").count() == 1, "Import progress control exists")
    page.click("#roadmapMenuTrigger"); check(page.locator("#legacyImportBtn").is_hidden(), "legacy import is hidden when the browser has no old data"); page.keyboard.press("Escape")
    # breadcrumb link
    page.click("#crumbHome .crumb-link"); page.wait_for_selector(".summary-bar")
    check(page.evaluate("location.hash") == "#/", "breadcrumb 'Roadmaps' link goes Home")
    # unknown roadmap
    page.evaluate("location.hash='#/r/999999/overview'"); page.reload()
    page.wait_for_selector("#authBlock:not(.hidden)", timeout=10000)
    check("load" in page.inner_text("#authBlockTitle").lower(), "unknown roadmap id shows an error panel")
    page.click("#authBlockActions button >> nth=1"); page.wait_for_selector(".summary-bar", timeout=10000)
    check(page.evaluate("location.hash") == "#/", "'Back to roadmaps' lands on Home")

    # ============ D. Custom roadmap, delete, empty state, restore ============
    page.click("[data-action=create-roadmap]"); page.fill("#newRoadmapName", "Temp Plan"); page.click("#createRoadmapSubmit")
    page.wait_for_selector("#roadmapTitle")
    check(page.inner_text("#crumbRoadmapName") == "Temp Plan" and page.evaluate("location.hash").endswith("/overview"), "created custom roadmap opens with its URL")
    check(page.locator("#tabs .tab:visible").count() == 5, "custom roadmap shows 5 views (Skills and Reference hidden)")
    page.click("#backToDashboardBtn"); page.wait_for_selector(".summary-bar")
    card = page.locator("article.roadmap-card", has_text="Temp Plan")
    check("No months yet" in card.inner_text() and card.locator(".btn-primary").inner_text() == "Build plan", "empty custom card: 'No months yet' and 'Build plan'")
    check(card.locator(".strip.is-empty").count() == 1, "empty custom card shows the dashed empty strip")
    card.locator("[data-menu-trigger]").click(); card.locator("[data-action=delete-roadmap]").click()
    check("permanently deletes" in page.inner_text("#modalHost") or "delete" in page.inner_text("#modalHost").lower(), "delete asks for confirmation")
    page.click("[data-action=confirm-delete-roadmap]"); page.locator("article.roadmap-card", has_text="Temp Plan").wait_for(state="detached", timeout=8000)
    check(True, "delete from the card menu works")
    ai = page.locator("article.roadmap-card", has_text="AI Engineer")
    ai.locator("[data-menu-trigger]").click(); ai.locator("[data-action=delete-roadmap]").click()
    page.click("[data-action=confirm-delete-roadmap]"); page.wait_for_selector(".empty-panel", timeout=8000)
    check("No roadmaps yet" in page.inner_text(".empty-panel"), "deleting the last roadmap shows the empty state")
    audit(page, "empty state")
    page.click(".empty-panel [data-action=restore-builtin]"); page.wait_for_selector("article.roadmap-card", timeout=8000)
    check(page.locator("article.roadmap-card").count() == 1, "restore from the empty state works")
    page.click("[data-action=create-roadmap]"); page.fill("#newRoadmapName", "Second"); page.click("#createRoadmapSubmit"); page.wait_for_selector("#roadmapTitle")
    page.click("#backToDashboardBtn"); page.wait_for_selector(".summary-bar")
    ai = page.locator("article.roadmap-card", has_text="AI Engineer")
    ai.locator("[data-menu-trigger]").click(); ai.locator("[data-action=delete-roadmap]").click(); page.click("[data-action=confirm-delete-roadmap]")
    page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(state="detached", timeout=8000)
    page.wait_for_selector(".notice-row [data-action=restore-builtin]", timeout=8000)
    check(page.locator(".notice-row [data-action=restore-builtin]").count() == 1, "with other roadmaps left, a notice offers 'Restore AI Engineer roadmap'")
    page.click(".notice-row [data-action=restore-builtin]"); page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(timeout=8000)
    check(page.locator(".notice-row").count() == 0, "notice disappears after restoring")

    # ============ E. Logout clears the URL ============
    page.locator("article.roadmap-card", has_text="AI Engineer").locator(".btn-primary").click(); page.wait_for_selector(".stat-tile")
    page.click("#profileTrigger"); page.click("#logoutBtn"); page.wait_for_selector("#authForm", state="visible")
    check(page.evaluate("location.hash") == "", "logout clears the roadmap URL")
    check(not page.problems, "no page errors or CSP/console errors (desktop flows)" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # ============ F. 20-roadmap limit ============
    ctx, page = new_context(browser)
    fresh_user(ctx, "b")
    for i in range(19):
        r = ctx.request.post(BASE + "/api/roadmaps", data={"name": f"Plan {i + 1}"})
        assert r.status == 201, r.status
    home(page)
    btn = page.locator("[data-action=create-roadmap]").first
    check(btn.is_disabled() and "limit of 20" in (btn.get_attribute("title") or ""), "New roadmap is disabled at 20 roadmaps with an explanatory title")
    check(page.locator("article.roadmap-card").count() == 20, "20 cards render")
    ctx.close()

    # ============ G. Skeleton while loading ============
    ctx, page = new_context(browser)
    fresh_user(ctx, "c")
    def slow(route):
        time.sleep(1.2); route.continue_()
    page.route("**/api/roadmaps", slow)
    page.goto(BASE)
    page.wait_for_selector(".roadmap-card.is-skeleton", timeout=5000)
    check(page.locator(".roadmap-card.is-skeleton").count() == 3 and "Loading your roadmaps" in page.inner_text("#dashboardContent"), "Home shows 3 skeleton cards while loading")
    page.wait_for_selector(".summary-bar", timeout=10000)
    check(page.locator(".is-skeleton").count() == 0, "skeletons are replaced by real content")
    page.unroute("**/api/roadmaps")
    ctx.close()

    # ============ H. Phone and tablet: drawer ============
    for name, (w, h) in (("phone", (390, 844)), ("tablet", (820, 1000))):
        ctx, page = new_context(browser, w, h)
        fresh_user(ctx, name[:1] + "d")
        home(page)
        check(not page.locator("#sidebar").evaluate("el => el.getBoundingClientRect().right > 0 && el.getBoundingClientRect().left >= 0"), f"{name}: sidebar is off-canvas by default")
        check(page.locator("#sidebarOpenBtn").is_visible(), f"{name}: menu button visible")
        check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"{name}: no horizontal scrolling on Home")
        page.click("#sidebarOpenBtn"); page.wait_for_timeout(300)
        check(page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "true" and page.locator("#sidebarScrim").is_visible(), f"{name}: drawer opens with a scrim")
        page.screenshot(path=f"{SHOTS}/drawer-{name}.png")
        audit(page, f"drawer open ({name})")
        page.keyboard.press("Escape"); page.wait_for_timeout(250)
        check(page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "false" and page.evaluate("document.activeElement.id") == "sidebarOpenBtn", f"{name}: Escape closes the drawer and returns focus to the menu button")
        page.click("#sidebarOpenBtn"); page.click("#sidebar .nav-roadmap"); page.wait_for_selector(".stat-tile")
        check(page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "false", f"{name}: choosing a roadmap closes the drawer")
        page.click("#sidebarOpenBtn"); page.click('.tab[data-view="timeline"]'); page.wait_for_timeout(250)
        check(page.evaluate("location.hash").endswith("/timeline") and page.get_attribute("#sidebarOpenBtn", "aria-expanded") == "false", f"{name}: choosing a view closes the drawer and updates the URL")
        check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"{name}: no horizontal scrolling in a roadmap")
        page.screenshot(path=f"{SHOTS}/roadmap-{name}.png")
        audit(page, f"roadmap ({name})")
        ctx.close()

    # ============ I. Accessibility across views, both themes (demo user with progress) ============
    for scheme in ("light", "dark"):
        ctx, page = new_context(browser, 1440, 900, scheme)
        login_demo(ctx); home(page)
        summary = " ".join(page.inner_text(".summary-bar").split())
        check(f"{DEMO_DONE} / {DEMO_TOTAL}" in summary and str(DEMO_WEEK) in summary, f"Home ({scheme}): summary matches the API ({DEMO_DONE} / {DEMO_TOTAL}, {DEMO_WEEK} this week)")
        page.wait_for_timeout(900)  # let the one-time strip animation (0.6s) finish before the screenshot
        page.screenshot(path=f"{SHOTS}/home-{scheme}-progress.png")
        audit(page, f"Home with progress ({scheme})")
        page.click("article.roadmap-card .btn-primary"); page.wait_for_selector(".stat-tile")
        for view in ("overview", "timeline", "kanban", "checklist", "thisweek", "mastery", "reference"):
            page.click(f'.tab[data-view="{view}"]'); page.wait_for_timeout(250)
            if view in ("overview", "kanban") or scheme == "dark":
                page.screenshot(path=f"{SHOTS}/roadmap-{view}-{scheme}.png")
            audit(page, f"{view} ({scheme})")
        check(not page.problems, f"no page errors or CSP/console errors ({scheme} audit run)" + ("" if not page.problems else ": " + str(page.problems[:3])))
        ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
