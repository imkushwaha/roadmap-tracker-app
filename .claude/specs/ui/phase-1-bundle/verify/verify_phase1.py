"""Phase 1 verification. Usage:
    python3 verify_phase1.py [BASE_URL] [AXE_JS_PATH] [SHOT_DIR]
Needs the demo server from Phase 0 (serve-demo.js) running: user imkushwaha / demo-pass-123 exists.
Exit code 0 only if every check passes."""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3111"
AXE = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ui-verify/node_modules/axe-core/axe.min.js"
SHOTS = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ui-verify/shots-p1"
os.makedirs(SHOTS, exist_ok=True)
NEW_USER = "p1user_%d" % (int(time.time()) % 1000000)
results = []
AXE_SOURCE = None


def check(ok, message):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + message)


def audit(page, label):
    global AXE_SOURCE
    if AXE_SOURCE is None:
        AXE_SOURCE = open(AXE, encoding="utf-8").read()
    page.evaluate(AXE_SOURCE)  # evaluating via DevTools works under the app's CSP (script tags do not)
    v = page.evaluate("""async () => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] } });
      return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0] && v.nodes[0].target.join(' ')));
    }""")
    check(not v, f"axe 0 violations: {label}" + ("" if not v else "  -> " + "; ".join(v)))


def new_page(browser, width, height, scheme="light"):
    ctx = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
    page = ctx.new_page()
    page.problems = []
    page.on("pageerror", lambda e: page.problems.append("pageerror: " + str(e)))
    page.on("console", lambda m: page.problems.append(m.text) if m.type == "error" and "401" not in m.text else None)
    page.goto(BASE)
    page.wait_for_selector("#authForm", state="visible")
    return ctx, page


def box(page, selector):
    return page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height,b:r.bottom}; }", selector)


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---------- 1. Assets ----------
    ctx, page = new_page(browser, 1440, 900)
    for path in ("/css/auth.css", "/js/month-strip.js"):
        check(page.request.get(BASE + path).status == 200, f"asset served: {path}")

    # ---------- 2. Desktop layout (>= 1024px) ----------
    check(page.locator(".auth-panel").is_visible(), "desktop: brand panel visible")
    panel, form = box(page, ".auth-panel"), box(page, "#authForm")
    check(580 <= panel["w"] <= 700, f"desktop: brand panel is ~45% wide ({panel['w']:.0f}px of 1440)")
    check(form["w"] <= 401, f"desktop: form column max 400px ({form['w']:.0f}px)")
    check(not page.locator(".auth-brand-compact").first.is_visible(), "desktop: compact logo hidden (panel has the logo)")
    cols = page.locator("#authPanelStrip .strip-col")
    check(cols.count() == 10, "panel strip has 10 month segments")
    labels = [t.strip() for t in page.locator("#authPanelStrip .strip-label").all_inner_texts()]
    check(labels == ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"], f"strip labels Oct..Jul: {labels}")
    check(page.locator("#authPanelStrip .strip-col").nth(2).get_attribute("class").find("is-current") >= 0, "Dec is the marked current month")
    check("29% complete" in page.inner_text(".auth-panel-demo-foot"), "caption matches the sample data (29%)")
    check(page.get_attribute("#authPanelStrip .strip", "aria-label") is not None, "strip has an accessible summary")
    check(page.get_attribute(".auth-panel", "aria-hidden") == "true", "decorative brand panel is aria-hidden")
    check(page.evaluate("document.activeElement.id") == "authUsername", "username field is focused on load")
    check(page.evaluate("getComputedStyle(document.getElementById('authSubmit')).height") in ("44px",), "submit button is 44px high")
    page.screenshot(path=f"{SHOTS}/login-desktop-light.png")
    audit(page, "login (desktop, light)")

    # ---------- 3. Login behaviour ----------
    page.click("#authSubmit")
    check(page.inner_text("#authError") == "Enter your username." and page.get_attribute("#authUsername", "aria-invalid") == "true"
          and page.evaluate("document.activeElement.id") == "authUsername", "empty submit: banner + aria-invalid + focus on username")
    page.fill("#authUsername", "imkushwaha"); page.click("#authSubmit")
    check(page.inner_text("#authError") == "Enter your password." and page.evaluate("document.activeElement.id") == "authPassword", "missing password: banner + focus on password")
    page.fill("#authPassword", "wrong-wrong-1"); page.click("#authSubmit")
    page.locator("#authError", has_text="Invalid").wait_for(timeout=8000)
    check(True, "wrong password shows the server's error in the banner: " + page.inner_text("#authError"))
    check(page.get_attribute("#authError", "role") == "alert", "error banner is role=alert")
    page.screenshot(path=f"{SHOTS}/login-error-desktop-light.png")
    audit(page, "login with error banner (desktop, light)")
    check(page.get_attribute("#authPassword", "type") == "password" and page.get_attribute("#authPasswordToggle", "aria-label") == "Show password", "password hidden by default; toggle says 'Show password'")
    check(page.locator("#authPasswordToggle svg").count() == 1, "toggle shows an SVG icon")
    page.click("#authPasswordToggle")
    check(page.get_attribute("#authPassword", "type") == "text" and page.get_attribute("#authPasswordToggle", "aria-pressed") == "true"
          and page.get_attribute("#authPasswordToggle", "aria-label") == "Hide password", "toggle reveals the password and updates aria")
    page.click("#authPasswordToggle")
    check(page.get_attribute("#authPassword", "type") == "password", "toggle hides it again")
    # Caps Lock hint (simulated modifier state)
    page.evaluate("document.getElementById('authPassword').dispatchEvent(new KeyboardEvent('keydown', {key: 'a', modifierCapsLock: true, bubbles: true}))")
    check(page.locator("#authCapsHint").is_visible(), "Caps Lock hint appears when Caps Lock is on")
    page.evaluate("document.getElementById('authPassword').dispatchEvent(new KeyboardEvent('keyup', {key: 'a', modifierCapsLock: false, bubbles: true}))")
    check(not page.locator("#authCapsHint").is_visible(), "Caps Lock hint disappears when it is off")
    check(page.get_attribute("#authDownload", "class").find("hidden") >= 0, "'Download my unsaved changes' hidden during normal login")

    # ---------- 4. Create-account behaviour ----------
    page.click("#authToggle")
    check(page.inner_text("#authTitle") == "Create your account", "toggle switches the heading")
    check("10-month AI Engineer roadmap" in page.inner_text("#authSubtitle"), "sign-up subtitle")
    check(page.inner_text("#authUsernameLabel") == "Username", "label says 'Username' (not 'User ID')")
    check("User ID" not in page.inner_text("#authScreen"), "the words 'User ID' appear nowhere on the auth screen")
    check(page.locator("#authUsernameRule").is_visible() and "3 to 32 characters" in page.inner_text("#authUsernameRule"), "permanent username rule is visible")
    first, last = box(page, "#authFirstName"), box(page, "#authLastName")
    check(abs(first["y"] - last["y"]) < 2 and last["x"] > first["x"], "first and last name sit side by side")
    check(page.locator("#authError").inner_text() == "", "switching modes clears the error banner")
    check(page.get_attribute("#authPassword", "autocomplete") == "new-password", "password autocomplete = new-password in sign-up")
    page.fill("#authFirstName", "Ada"); page.fill("#authLastName", "Lovelace")
    page.fill("#authUsername", "imkushwaha")
    page.locator("#authUsernameStatus", has_text="taken").wait_for(timeout=5000)
    check("taken" in page.get_attribute("#authUsernameStatus", "class"), "existing username => 'That username is taken.' (state class taken)")
    page.fill("#authUsername", NEW_USER)
    page.locator("#authUsernameStatus", has_text="available").wait_for(timeout=5000)
    check("available" in page.get_attribute("#authUsernameStatus", "class"), "new username => 'Username is available.' (state class available)")
    page.fill("#authPassword", "short")
    check("met" not in page.get_attribute("#authRuleLength", "class"), "password rule not met under 8 characters")
    page.fill("#authPassword", "longenough1")
    check("met" in page.get_attribute("#authRuleLength", "class"), "password rule turns met at 8+ characters")
    page.fill("#authConfirmPassword", "different1")
    check(page.inner_text("#authPasswordMatch") == "Passwords don't match." and "mismatch" in page.get_attribute("#authPasswordMatch", "class"), "mismatch hint")
    page.screenshot(path=f"{SHOTS}/signup-desktop-light.png")
    audit(page, "sign-up with validation hints (desktop, light)")
    page.click("#authSubmit")
    check(page.inner_text("#authError") == "Passwords don't match." and page.evaluate("document.activeElement.id") == "authConfirmPassword"
          and page.get_attribute("#authConfirmPassword", "aria-invalid") == "true", "mismatch on submit: banner + focus + aria-invalid on confirm field")
    page.fill("#authConfirmPassword", "longenough1")
    check("match" in page.get_attribute("#authPasswordMatch", "class") and page.inner_text("#authPasswordMatch") == "Passwords match.", "match hint")

    # ---------- 5. Success: lands on Home with a toast ----------
    page.click("#authSubmit")
    page.wait_for_selector(".roadmap-card", timeout=10000)
    check(page.inner_text("#profileName") == "Ada Lovelace", "account created; signed in as Ada Lovelace")
    check(page.locator(".toast.success", has_text="Account created. Your AI Engineer roadmap is ready.").count() >= 1, "success toast shown")
    page.click("#profileTrigger"); page.click("#logoutBtn"); page.wait_for_selector("#authForm", state="visible")
    page.fill("#authUsername", NEW_USER); page.fill("#authPassword", "longenough1"); page.click("#authSubmit")
    page.wait_for_selector(".roadmap-card", timeout=10000)
    check(True, "log out and log in again with the new account")
    check(not page.problems, "no page errors or CSP/console errors" + ("" if not page.problems else ": " + str(page.problems[:3])))
    ctx.close()

    # ---------- 6. Sign-up fits a laptop screen ----------
    ctx, page = new_page(browser, 1440, 768)
    page.click("#authToggle")
    page.fill("#authFirstName", "A"); page.fill("#authUsername", "abc"); page.fill("#authPassword", "x"); page.fill("#authConfirmPassword", "y")
    fits = page.evaluate("(() => { const s = document.getElementById('authScreen'); return s.scrollHeight <= s.clientHeight + 1; })()")
    check(fits, "sign-up form (with hints) fits a 1440x768 viewport without scrolling")
    ctx.close()

    # ---------- 7. Tablet and phone ----------
    for name, (w, h) in (("tablet", (820, 1000)), ("phone", (390, 844))):
        ctx, page = new_page(browser, w, h)
        check(not page.locator(".auth-panel").is_visible(), f"{name}: brand panel hidden")
        check(page.locator(".auth-brand-compact").first.is_visible(), f"{name}: compact logo shown above the form")
        overflow = page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        check(overflow, f"{name}: no horizontal scrolling")
        page.click("#authToggle")
        if name == "phone":
            first, last = box(page, "#authFirstName"), box(page, "#authLastName")
            check(last["y"] > first["y"], "phone: first and last name stack")
            inputs_ok = page.evaluate("parseFloat(getComputedStyle(document.getElementById('authUsername')).fontSize) >= 16")
            check(inputs_ok, "phone: inputs are 16px (no iOS zoom)")
        page.fill("#authFirstName", "A"); page.fill("#authUsername", "abc"); page.fill("#authPassword", "x"); page.fill("#authConfirmPassword", "y")
        page.screenshot(path=f"{SHOTS}/signup-{name}-light.png", full_page=True)
        audit(page, f"sign-up ({name}, light)")
        ctx.close()

    # ---------- 8. Dark theme ----------
    ctx, page = new_page(browser, 1440, 900, "dark")
    page.screenshot(path=f"{SHOTS}/login-desktop-dark.png")
    audit(page, "login (desktop, dark)")
    page.click("#authSubmit")
    audit(page, "login with error banner (desktop, dark)")
    page.click("#authToggle"); page.fill("#authUsername", "imkushwaha"); page.wait_for_timeout(700)
    page.fill("#authPassword", "short"); page.fill("#authConfirmPassword", "other")
    page.screenshot(path=f"{SHOTS}/signup-desktop-dark.png")
    audit(page, "sign-up with hints (desktop, dark)")
    ctx.close()

    # ---------- 9. MonthStrip component contract ----------
    ctx, page = new_page(browser, 1440, 900)
    ev = lambda js: page.evaluate(js)
    empty = ev("MonthStrip.html([])")
    check("is-empty" in empty and 'aria-label="No months yet"' in empty, "MonthStrip: empty list renders a dashed empty strip")
    two = ev("MonthStrip.html([{label:'A',total:10,completed:5},{label:'B',total:0,completed:0}], {size:'sm'})")
    check('aria-label="5 of 10 tasks complete across 2 months"' in two and "strip-sm" in two, "MonthStrip: accessible summary and size class")
    many = ev("MonthStrip.html(Array.from({length:13},(_, i)=>({label:'M'+i,total:10,completed:1})))")
    check(many.count("strip-col") == 1, "MonthStrip: more than 12 months collapses into one continuous bar")
    evil = ev("MonthStrip.html([{label:'<img src=x onerror=alert(1)>', title:'\"><script>1</script>', total:1, completed:1}], {labels:true})")
    check("<img" not in evil and "<script" not in evil and "&lt;img" in evil and "&lt;script&gt;" in evil,
          "MonthStrip: labels and titles are HTML-escaped")
    parts = ev("MonthStrip.html([{label:'x',total:10,completed:5,inProgress:3,blocked:2,current:true}])")
    check("is-done" in parts and "is-progress" in parts and "is-blocked" in parts and "is-current" in parts and "flex-basis:50.00%" in parts, "MonthStrip: stacked parts and current marker")
    bad = ev("MonthStrip.html([{label:'x',total:'abc',completed:-4,inProgress:NaN}])")
    check("strip-part" not in bad, "MonthStrip: junk numbers render no parts and do not throw")
    ctx.close()
    browser.close()

print(f"\nRESULT {sum(results)}/{len(results)} checks passed; screenshots in {SHOTS}")
sys.exit(0 if all(results) else 1)
