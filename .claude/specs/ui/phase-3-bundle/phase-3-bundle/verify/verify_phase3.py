"""Phase 3 verification. Usage:
    python3 verify_phase3.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Needs the demo server from the Phase 0 spec (serve-demo.js) running. Exit code 0 only if every check passes."""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots-p3"
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


def new_context(browser, width=1440, height=1000, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
    page = ctx.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: page.problems.append(m.text) if m.type == "error" and "401" not in m.text and "404" not in m.text else None)
    return ctx, page


def register(ctx, tag):
    name = f"p3{tag}_{RUN}"
    r = ctx.request.post(BASE + "/api/auth/register", data={"firstName": "Rita", "lastName": "Route", "username": name, "password": "longenough1"})
    assert r.status == 201, r.status


def make_custom(ctx, name, description, done, total):
    """Create a custom roadmap with one month and `total` tasks, `done` of them completed."""
    rid = ctx.request.post(BASE + "/api/roadmaps", data={"name": name, "description": description}).json()["roadmap"]["id"]
    if total:
        tasks = [{"id": f"t{rid}-{i}", "title": f"Task {i}"} for i in range(total)]
        data = {"items": {t["id"]: {"status": "completed", "completedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} for t in tasks[:done]},
                "counters": {}, "celebratedPhases": [], "settings": {},
                "custom": {"topics": [{"id": f"tp{rid}", "sectionId": f"s{rid}", "title": "Topic", "depth": "D2", "tasks": tasks}],
                           "phases": [{"id": f"p{rid}", "title": "Focus month", "sections": [{"id": f"s{rid}", "title": "Week", "type": "week", "weekNumber": 1}]}]}}
        ver = ctx.request.get(BASE + f"/api/roadmaps/{rid}/progress").json()["version"]
        r = ctx.request.put(BASE + f"/api/roadmaps/{rid}/progress", data={"version": ver, "data": data})
        assert r.status == 200, r.status
    return rid


def home(page):
    page.goto(BASE)
    page.wait_for_selector(".summary-bar", timeout=10000)


def titles(page):
    return [t.strip() for t in page.locator("#homeResults .rc-title, #homeResults .rt-name").all_inner_texts()]


def chip_text(page, value):
    return " ".join(page.locator(f'.chip-filter[data-value="{value}"]').inner_text().split())


with sync_playwright() as p:
    browser = p.chromium.launch()

    # =============== A. One roadmap: no toolbar, rail present ===============
    ctx, page = new_context(browser)
    register(ctx, "a")
    home(page)
    check(page.locator("#homeSearch").count() == 0 and page.locator(".view-toggle").count() == 0, "one roadmap: no toolbar and no view toggle")
    check(page.locator(".home-rail .rail-card").count() == 2, "one roadmap: rail shows Current focus and Getting started")
    check(page.locator("#homeLayout.has-rail").count() == 1, "layout has the rail column")
    main_box = page.evaluate("(() => { const m = document.querySelector('.home-main').getBoundingClientRect(), r = document.querySelector('.home-rail').getBoundingClientRect(); return {mr: m.right, rl: r.left, rw: r.width, rt: r.top, mt: m.top}; })()")
    check(abs(main_box["rw"] - 320) <= 1 and main_box["rl"] >= main_box["mr"], f"desktop: rail is 320px wide, beside the list ({main_box['rw']:.0f}px)")
    gs = " ".join(page.locator("#startedHeading").locator("xpath=..").inner_text().split())
    check("0 of 4 done" in gs, "Getting started: new account shows 0 of 4 done")
    focus = " ".join(page.locator("#focusHeading").locator("xpath=..").inner_text().split())
    check("AI Engineer Roadmap" in focus and "Month" in focus or "Starts" in focus, "Current focus names the roadmap: " + focus[:80])
    page.set_viewport_size({"width": 1100, "height": 900}); page.wait_for_timeout(200)
    below = page.evaluate("(() => { const m = document.querySelector('.home-main').getBoundingClientRect(), r = document.querySelector('.home-rail').getBoundingClientRect(); return r.top >= m.bottom - 1; })()")
    check(below, "below 1280px the rail drops under the list")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(path=f"{SHOTS}/home-one-roadmap.png")
    audit(page, "Home with one roadmap and rail")

    # =============== B. New roadmap dialog ===============
    btn = page.locator("[data-action=create-roadmap]").first
    btn.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    modal = page.locator("#modalHost .modal")
    check(modal.get_attribute("role") == "dialog" and modal.get_attribute("aria-modal") == "true", "dialog has role=dialog and aria-modal")
    check(page.inner_text("#modalTitle") == "New roadmap" and modal.get_attribute("aria-labelledby") == "modalTitle", "dialog is named by its heading")
    radios = page.locator('input[name="newRoadmapKind"]')
    check(radios.count() == 3 and radios.nth(0).is_checked(), "three start options; Blank roadmap preselected")
    check(radios.nth(1).is_disabled() and "already have this roadmap" in page.inner_text("#modalHost .option-row >> nth=1"), "AI Engineer option disabled with 'You already have this roadmap.'")
    check(radios.nth(2).is_disabled() and page.locator(".badge-soon").inner_text() == "Soon", "AI option disabled and marked Soon")
    check(page.evaluate("document.activeElement.id") == "newRoadmapName", "focus starts in the name field")
    page.fill("#newRoadmapDesc", "hello")
    check(page.inner_text("#newRoadmapCount") == "5 / 300", "description counter updates: " + page.inner_text("#newRoadmapCount"))
    page.screenshot(path=f"{SHOTS}/dialog-new.png")
    audit(page, "New roadmap dialog")
    for _ in range(14):
        page.keyboard.press("Tab")
    inside = page.evaluate("document.getElementById('modalHost').querySelector('.modal').contains(document.activeElement)")
    check(inside, "Tab cycles inside the dialog (focus trap)")
    page.keyboard.press("Shift+Tab")
    check(page.evaluate("document.getElementById('modalHost').querySelector('.modal').contains(document.activeElement)"), "Shift+Tab stays inside too")
    page.fill("#newRoadmapName", ""); page.click("#createRoadmapSubmit")
    check(page.inner_text("#createRoadmapError") == "Give your roadmap a name." and page.locator("#modalHost.hidden").count() == 0, "empty name: error shown, dialog stays open")
    page.keyboard.press("Escape")
    check(page.locator("#modalHost.hidden").count() == 1, "Escape closes the dialog")
    check(page.evaluate("document.activeElement.getAttribute('data-action')") == "create-roadmap", "focus returns to the 'New roadmap' button")
    # create a real one (blank)
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    page.fill("#newRoadmapName", "Alpha"); page.fill("#newRoadmapDesc", "Alpha description"); page.click("#createRoadmapSubmit")
    page.wait_for_selector("#roadmapTitle"); page.locator("#crumbRoadmapName", has_text="Alpha").wait_for(timeout=8000)
    check(page.evaluate("location.hash").endswith("/overview"), "creating a blank roadmap opens it")
    page.click("#backToDashboardBtn"); page.wait_for_selector(".summary-bar")

    # =============== C. Several roadmaps: toolbar, filter, search, sort ===============
    make_custom(ctx, "Beta Plan", "Notes about a quokka diet", 2, 4)      # in progress, 50%
    make_custom(ctx, "Gamma", "All done here", 3, 3)                       # completed, 100%
    home(page)
    check(page.locator("#homeSearch").is_visible() and page.locator(".view-toggle").is_visible(), "2+ roadmaps: search, filters, sort and view toggle appear")
    check(chip_text(page, "all") == "All 4" and chip_text(page, "in_progress") == "In progress 1"
          and chip_text(page, "not_started") == "Not started 2" and chip_text(page, "completed") == "Completed 1", "filter chips show counts: " + " | ".join(chip_text(page, v) for v in ("all", "in_progress", "not_started", "completed")))
    check(page.locator("article.roadmap-card").count() == 4 and "4 roadmaps shown" in page.inner_text("#homeResultCount"), "all 4 cards shown; live count announced")
    page.click('.chip-filter[data-value="in_progress"]')
    check(titles(page) == ["Beta Plan"] and page.get_attribute('.chip-filter[data-value="in_progress"]', "aria-pressed") == "true", "filter In progress -> Beta Plan only")
    page.click('.chip-filter[data-value="completed"]'); check(titles(page) == ["Gamma"], "filter Completed -> Gamma only")
    page.click('.chip-filter[data-value="not_started"]'); check(sorted(titles(page)) == ["AI Engineer Roadmap", "Alpha"], "filter Not started -> AI Engineer + Alpha")
    page.click('.chip-filter[data-value="all"]')
    page.fill("#homeSearch", "gam"); check(titles(page) == ["Gamma"], "search by name ('gam')")
    check(page.evaluate("document.activeElement.id") == "homeSearch", "typing in search keeps focus in the box")
    page.fill("#homeSearch", "quokka"); check(titles(page) == ["Beta Plan"], "search also matches descriptions ('quokka')")
    page.fill("#homeSearch", "zzz")
    check("No roadmaps match" in page.inner_text("#homeResults") and "zzz" in page.inner_text("#homeResults"), "no match: message with the search text")
    page.screenshot(path=f"{SHOTS}/home-no-match.png")
    audit(page, "Home: no results state")
    page.click('[data-action="clear-filters"]')
    check(page.input_value("#homeSearch") == "" and len(titles(page)) == 4, "Clear search restores all roadmaps")
    page.click('.chip-filter[data-value="completed"]'); page.fill("#homeSearch", "beta")
    check("Clear filters" in page.inner_text("#homeResults"), "filter + search with no match offers 'Clear filters'")
    page.click('[data-action="clear-filters"]')
    page.select_option("#homeSort", "name")
    check(titles(page) == ["AI Engineer Roadmap", "Alpha", "Beta Plan", "Gamma"], "sort Name (A-Z): " + str(titles(page)))
    page.select_option("#homeSort", "progress")
    check(titles(page)[0] == "Gamma" and titles(page)[1] == "Beta Plan", "sort Progress (high first): " + str(titles(page)))

    # =============== D. List view ===============
    page.click('[data-action=set-view][data-value=list]')
    check(page.locator("table.rtable").count() == 1 and page.locator("tr.rt-row").count() == 4, "list view: table with 4 rows")
    check(page.get_attribute('[data-action=set-view][data-value=list]', "aria-pressed") == "true", "list toggle is pressed")
    ths = {t.inner_text().strip(): t.get_attribute("aria-sort") for t in page.locator("table.rtable thead th").all() if t.inner_text().strip()}
    check(ths.get("Progress") == "descending" and ths.get("Roadmap") == "none", "aria-sort reflects the active sort: " + str(ths))
    tbl = page.evaluate("(() => { const t = document.querySelector('.rtable').getBoundingClientRect(), w = document.querySelector('.table-wrap').getBoundingClientRect(), r = document.querySelector('.home-rail').getBoundingClientRect(); return {tr: t.right, wr: w.right, rl: r.left}; })()")
    check(tbl["tr"] <= tbl["wr"] + 1 and tbl["wr"] <= tbl["rl"], "list view fits beside the rail (no overlap)")
    check(not page.locator("th.col-month").is_visible(), "narrow column: 'Current month' column is hidden")
    page.screenshot(path=f"{SHOTS}/home-list.png")
    audit(page, "Home list view")
    page.click('th button[data-value="name"]')
    check(page.locator("th", has_text="Roadmap").get_attribute("aria-sort") == "ascending" and titles(page)[0] == "AI Engineer Roadmap", "click 'Roadmap' header: ascending (Name defaults A-Z)")
    page.click('th button[data-value="name"]')
    check(page.locator("th", has_text="Roadmap").get_attribute("aria-sort") == "descending" and titles(page)[0] == "Gamma", "click again: descending")
    page.reload(); page.wait_for_selector(".summary-bar")
    check(page.locator("table.rtable").count() == 1 and page.input_value("#homeSort") == "name", "view and sort are remembered after reload")
    check(page.locator("th", has_text="Roadmap").get_attribute("aria-sort") == "descending", "sort direction is remembered too")
    row = page.locator("tr.rt-row", has_text="Gamma")
    row.locator(".rt-name").click(); page.wait_for_selector(".stat-tile, #main", timeout=8000)
    check("/r/" in page.evaluate("location.hash"), "clicking a list row opens the roadmap")
    page.go_back(); page.wait_for_selector(".summary-bar")
    ctx2, page2 = new_context(browser, 1920, 1000)
    ctx2.add_cookies(ctx.cookies()); page2.goto(BASE); page2.wait_for_selector(".summary-bar")
    if page2.locator("table.rtable").count() == 0:
        page2.click('[data-action=set-view][data-value=list]')
    check(page2.locator("th.col-month").is_visible(), "wide screen (1920px): 'Current month' column appears")
    ctx2.close()
    page.click('[data-action=set-view][data-value=grid]'); page.select_option("#homeSort", "recent")

    # =============== E. Delete: typed name when there is progress ===============
    def open_delete(title):
        card = page.locator("article.roadmap-card", has_text=title)
        card.locator("[data-menu-trigger]").click(); card.locator("[data-action=delete-roadmap]").click()
        page.wait_for_selector("#modalHost:not(.hidden)")
        return card

    open_delete("Gamma")
    check(page.inner_text("#modalTitle") == "Delete “Gamma”?", "delete dialog title uses the roadmap name")
    check("You have completed 3 of 3 tasks." in page.inner_text("#modalHost"), "dialog states how much progress will be lost")
    check(page.locator("#deleteConfirmName").count() == 1 and page.locator("#deleteConfirmBtn").is_disabled(), "roadmap with progress: name field present, Delete disabled")
    check(page.evaluate("document.activeElement.id") == "deleteCancelBtn", "focus starts on Cancel")
    page.fill("#deleteConfirmName", "gamma")
    check(page.locator("#deleteConfirmBtn").is_disabled(), "wrong case keeps Delete disabled")
    page.screenshot(path=f"{SHOTS}/dialog-delete.png")
    audit(page, "Delete dialog with typed name")
    page.keyboard.press("Escape")
    check(page.locator("#modalHost.hidden").count() == 1 and page.locator("article.roadmap-card", has_text="Gamma").count() == 1, "Escape cancels; the roadmap still exists")
    check(page.evaluate("document.activeElement.hasAttribute('data-menu-trigger')"), "focus returns to the card's ⋯ button")
    open_delete("Gamma"); page.fill("#deleteConfirmName", "Gamma")
    check(not page.locator("#deleteConfirmBtn").is_disabled(), "exact name enables Delete")
    page.keyboard.press("Enter")
    page.locator("article.roadmap-card", has_text="Gamma").wait_for(state="detached", timeout=8000)
    check(page.locator(".toast.success", has_text="Roadmap deleted.").count() >= 1, "Enter in the name box deletes; toast 'Roadmap deleted.'")
    open_delete("Alpha")
    check(page.locator("#deleteConfirmName").count() == 0 and not page.locator("#deleteConfirmBtn").is_disabled(), "roadmap without progress: no name field, Delete enabled")
    page.click("#deleteConfirmBtn"); page.locator("article.roadmap-card", has_text="Alpha").wait_for(state="detached", timeout=8000)
    check(True, "plain confirmation deletes an untouched roadmap")
    # built-in untouched? Beta has progress; delete the built-in (no progress) then restore via the dialog
    open_delete("AI Engineer"); check(page.locator("#deleteConfirmName").count() == 0, "untouched built-in roadmap needs no typed name")
    page.click("#deleteConfirmBtn"); page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(state="detached", timeout=8000)
    page.wait_for_selector(".notice-row")
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    check(not page.locator('input[value="builtin"]').is_disabled(), "AI Engineer option is enabled when the account no longer has it")
    page.locator('input[value="builtin"]').check()
    check(page.locator("#newBlankFields").is_hidden() and page.inner_text("#createRoadmapSubmit") == "Restore roadmap", "choosing it hides the blank fields and relabels the button")
    page.click("#createRoadmapSubmit")
    page.locator("article.roadmap-card", has_text="AI Engineer").wait_for(timeout=8000)
    check(page.locator(".toast.success", has_text="AI Engineer Roadmap restored.").count() >= 1, "restore through the dialog works")

    # =============== F. Right rail logic ===============
    page.reload(); page.wait_for_selector(".summary-bar")
    gs = " ".join(page.locator("#startedHeading").locator("xpath=..").inner_text().split())
    check("done" in gs and "Choose an appearance" in gs, "Getting started still visible while items remain")
    # Beta has a custom roadmap with a month and 2 completed tasks: items 1-3 done
    check(page.locator(".rail-list li.is-done").count() == 3 and "3 of 4 done" in gs, "Getting started: 3 of 4 done (task, custom roadmap, month)")
    page.click("#profileTrigger"); page.click("#themeLightBtn"); page.keyboard.press("Escape"); page.reload(); page.wait_for_selector(".summary-bar")
    check(page.locator("#startedHeading").count() == 0, "choosing an appearance completes the last item and hides the card")
    # Dismiss on a fresh account
    ctx3, page3 = new_context(browser); register(ctx3, "f"); home(page3)
    page3.click('[data-action="dismiss-getting-started"]')
    check(page3.locator("#startedHeading").count() == 0 and page3.locator("#focusHeading").count() == 1, "Dismiss removes only Getting started")
    page3.reload(); page3.wait_for_selector(".summary-bar")
    check(page3.locator("#startedHeading").count() == 0, "dismissal is remembered after reload")
    expect = page3.evaluate("""(() => { const d = window.ROADMAP_DATA, n = new Date(), idx = (n.getFullYear() - 2026) * 12 + (n.getMonth() - 9);
      if (idx < 0 || idx > 9) return null; const w = Math.floor((n.getDate() - 1) / 7); if (w > 3) return ''; const s = d.phases[idx].sections.find(s => s.type === 'week' && s.weekNumber && (s.weekNumber - 1) % 4 === w); return s ? s.title : ''; })()""")
    shown = page3.locator(".rail-week").inner_text() if page3.locator(".rail-week").count() else ""
    check((expect is None) or shown == expect, f"Current focus week line matches the roadmap data (expected '{expect}', shown '{shown}')")
    check(page3.locator(".home-rail [data-action=open-roadmap]").inner_text() == "Start", "Current focus button for an untouched roadmap says Start")
    ctx3.close()

    # =============== G. Other dialogs get Escape, focus return and trap ===============
    page.click("#sidebar [data-action=about]"); page.wait_for_selector("#modalHost:not(.hidden)")
    page.keyboard.press("Tab"); check(page.evaluate("document.activeElement.id") == "aboutCloseBtn" or page.evaluate("document.getElementById('modalHost').querySelector('.modal').contains(document.activeElement)"), "About: focus stays inside on Tab")
    page.keyboard.press("Escape")
    check(page.locator("#modalHost.hidden").count() == 1 and page.evaluate("document.activeElement.getAttribute('data-action')") == "about", "About: Escape closes it and focus returns to the About button")
    page.locator("article.roadmap-card", has_text="Beta").locator(".btn-primary").click(); page.wait_for_selector("#main")
    page.click('.tab[data-view="checklist"]'); page.wait_for_selector(".subtask-row, #main .empty-state, #main .section-title")
    if page.locator("[data-action=edit]").count() or page.locator(".mini-btn", has_text="details").count():
        page.locator(".mini-btn", has_text="details").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
        page.keyboard.press("Escape")
        check(page.locator("#modalHost.hidden").count() == 1, "task-details dialog also closes on Escape")
    else:
        check(True, "task-details dialog check skipped (no task rows in this roadmap)")
    page.go_back(); page.wait_for_selector(".summary-bar")
    check(not page.problems, "no page errors or CSP/console errors" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # =============== H. Phone and dark theme ===============
    ctx, page = new_context(browser, 390, 900)
    register(ctx, "h"); make_custom(ctx, "Beta Plan", "x", 1, 2); home(page)
    check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "phone: Home with toolbar has no horizontal scrolling")
    check(page.locator("#homeSearch").is_visible() and page.locator("#homeSort").is_visible(), "phone: search and sort are usable")
    page.click('[data-action=set-view][data-value=list]')
    check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "phone: list view has no horizontal scrolling")
    check(not page.locator("th.col-type").is_visible() and not page.locator("th.col-activity").is_visible(), "phone: list drops Type and Last activity columns")
    page.screenshot(path=f"{SHOTS}/home-list-phone.png", full_page=True)
    audit(page, "Home list view (phone)")
    page.click('[data-action=set-view][data-value=grid]'); audit(page, "Home grid with toolbar (phone)")
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)")
    check(page.evaluate("(() => { const r = document.querySelector('#modalHost .modal').getBoundingClientRect(); return r.right <= window.innerWidth && r.left >= 0; })()"), "phone: New roadmap dialog fits the screen")
    audit(page, "New roadmap dialog (phone)")
    ctx.close()

    ctx, page = new_context(browser, 1440, 1000, "dark")
    register(ctx, "i"); make_custom(ctx, "Beta Plan", "dark theme", 2, 4); make_custom(ctx, "Gamma", "done", 3, 3); home(page)
    page.wait_for_timeout(900)
    page.screenshot(path=f"{SHOTS}/home-dark.png")
    audit(page, "Home grid + rail (dark)")
    page.click('[data-action=set-view][data-value=list]'); audit(page, "Home list (dark)")
    page.locator("[data-action=create-roadmap]").first.click(); page.wait_for_selector("#modalHost:not(.hidden)"); audit(page, "New roadmap dialog (dark)"); page.keyboard.press("Escape")
    card = page.locator("tr.rt-row", has_text="Gamma"); card.locator("[data-menu-trigger]").click(); card.locator("[data-action=delete-roadmap]").click()
    page.wait_for_selector("#modalHost:not(.hidden)"); audit(page, "Delete dialog (dark)")
    ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
