"""Phase 0 verification. Usage:
    python3 verify_phase0.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Requires: python3 -m pip install playwright && python3 -m playwright install chromium
          npm install --prefix /tmp/ui-verify axe-core      (provides AXE_JS_PATH)
Exit code 0 only if every check passes. Screenshots are written for human review."""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots"
os.makedirs(SHOTS, exist_ok=True)

results = []


def check(ok, message):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + message)


AXE_SOURCE = None


def axe_violations(page):
    # The app's Content Security Policy blocks <script> injection, but evaluating the
    # source through the DevTools protocol is allowed - and keeps CSP errors detectable.
    global AXE_SOURCE
    if AXE_SOURCE is None:
        AXE_SOURCE = open(AXE, encoding="utf-8").read()
    page.evaluate(AXE_SOURCE)
    return page.evaluate("""async () => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] } });
      return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0] && v.nodes[0].target.join(' ')));
    }""")


def audit(page, label):
    v = axe_violations(page)
    check(not v, f"axe 0 violations: {label}" + ("" if not v else "  -> " + "; ".join(v)))


def login(page):
    page.goto(BASE)
    page.wait_for_selector("#authForm", state="visible")
    page.fill("#authUsername", "imkushwaha")
    page.fill("#authPassword", "demo-pass-123")
    page.click("#authSubmit")
    page.wait_for_selector(".roadmap-card", timeout=10000)


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---- A. Assets, tokens, fonts, theme (light OS) ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="light")
    page = ctx.new_page()
    problems = []
    page.on("pageerror", lambda e: problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" and "401" not in m.text else None)
    page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{window.__earlyTheme=document.documentElement.getAttribute('data-theme')})")

    for path in ("/css/tokens.css", "/css/base.css", "/css/components.css", "/js/theme-boot.js", "/js/icons.js",
                 "/img/logo.svg", "/img/favicon.svg",
                 "/fonts/ibm-plex-sans-latin-400-normal.woff2", "/fonts/ibm-plex-sans-latin-500-normal.woff2",
                 "/fonts/ibm-plex-sans-latin-600-normal.woff2"):
        check(page.request.get(BASE + path).status == 200, f"asset served: {path}")
    for path in ("/.env", "/data/app.db", "/server/app.js", "/fonts/", "/package.json"):
        check(page.request.get(BASE + path).status == 404, f"not served (404): {path}")

    page.goto(BASE)
    page.wait_for_selector("#authForm", state="visible")
    page.wait_for_timeout(400)
    page.screenshot(path=f"{SHOTS}/login-light.png")
    root_style = lambda name: page.evaluate(f"getComputedStyle(document.documentElement).getPropertyValue('{name}').trim().toLowerCase()")
    check(root_style("--accent") == "#2b50d8", "token --accent is #2b50d8 in light theme")
    check(root_style("--text-faint") == "#5f6a7d", "token --text-faint is #5f6a7d")
    check(page.evaluate("document.fonts.check('14px \"IBM Plex Sans\"')"), "IBM Plex Sans is loaded")
    check("IBM Plex Sans" in page.evaluate("getComputedStyle(document.body).fontFamily"), "body uses IBM Plex Sans")
    check(page.evaluate("document.documentElement.getAttribute('data-theme')") == "light", "default System + light OS => data-theme=light")
    check(page.evaluate("localStorage.getItem('roadmap-dashboard:theme')") is None, "nothing stored until the user chooses")
    check(page.evaluate("document.querySelectorAll('script:not([src])').length") == 0, "no inline <script> in the page (CSP)")
    check("🧭" not in page.inner_text("body"), "no compass emoji left in visible text")
    check(page.locator("img.brand-mark").count() >= 1, "SVG brand mark present")

    login(page)
    page.screenshot(path=f"{SHOTS}/home-light.png")
    audit(page, "home (light)")
    page.click("#profileTrigger")
    check(page.locator("#themeSystemBtn").is_visible() and "Appearance" in page.inner_text("#profilePanel"), "account menu has Appearance with a System option")
    page.screenshot(path=f"{SHOTS}/menu-light.png")
    audit(page, "account menu (light)")

    # theme behaviour
    theme = lambda: page.evaluate("document.documentElement.getAttribute('data-theme')")
    page.click("#themeDarkBtn")
    check(theme() == "dark" and page.evaluate("localStorage.getItem('roadmap-dashboard:theme')") == "dark", "Dark: applied and remembered")
    check(page.evaluate("document.querySelector('.profile-theme-btn.active').id") == "themeDarkBtn", "active theme button follows the choice")
    page.reload(); page.wait_for_selector(".roadmap-card", timeout=10000)
    check(page.evaluate("window.__earlyTheme") == "dark", "after reload the theme was applied BEFORE app scripts ran (no flash)")
    page.click("#profileTrigger"); page.click("#themeSystemBtn")
    check(theme() == "light", "System with light OS => light")
    page.emulate_media(color_scheme="dark"); page.wait_for_timeout(250)
    check(theme() == "dark", "System follows the OS live (OS -> dark)")
    page.click("#themeLightBtn"); page.emulate_media(color_scheme="dark"); page.wait_for_timeout(100)
    check(theme() == "light", "explicit Light ignores the OS")
    page.click("#themeSystemBtn"); page.keyboard.press("Escape")
    page.emulate_media(color_scheme="light")

    # open roadmap + every view, light
    page.click("[data-action=open-roadmap]"); page.wait_for_selector(".stat-tile", timeout=10000)
    for view in ("overview", "timeline", "kanban", "checklist", "thisweek", "mastery", "reference"):
        page.click(f'.tab[data-view="{view}"]'); page.wait_for_timeout(250)
        check(page.inner_text("#main").strip() != "", f"view renders: {view}")
        page.screenshot(path=f"{SHOTS}/{view}-light.png")
        audit(page, f"{view} (light)")
    check(not problems, "no page errors or CSP/console errors" + ("" if not problems else ": " + str(problems[:3])))
    ctx.close()

    # ---- B. Dark theme audit of the same screens ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
    page = ctx.new_page()
    page.goto(BASE); page.wait_for_selector("#authForm", state="visible")
    check(page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark", "dark OS => data-theme=dark on first load")
    check(root_style("--accent") == "#6c8cff", "token --accent is #6c8cff in dark theme")
    page.screenshot(path=f"{SHOTS}/login-dark.png")
    audit(page, "login (dark)")
    login(page); audit(page, "home (dark)")
    page.click("[data-action=open-roadmap]"); page.wait_for_selector(".stat-tile", timeout=10000)
    for view in ("overview", "timeline", "kanban", "checklist", "thisweek", "mastery", "reference"):
        page.click(f'.tab[data-view="{view}"]'); page.wait_for_timeout(250)
        if view in ("overview", "kanban", "checklist"):
            page.screenshot(path=f"{SHOTS}/{view}-dark.png")
        audit(page, f"{view} (dark)")
    ctx.close()

    # ---- C. Reduced motion ----
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page(); page.goto(BASE); page.wait_for_selector("#authForm", state="visible")
    check(page.evaluate("getComputedStyle(document.getElementById('confettiCanvas')).display") == "none", "reduced motion hides the confetti canvas")
    check(page.evaluate("parseFloat(getComputedStyle(document.getElementById('authSubmit')).transitionDuration) < 0.01"), "reduced motion removes transitions")
    ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
