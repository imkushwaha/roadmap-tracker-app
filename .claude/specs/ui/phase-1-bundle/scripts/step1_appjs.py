"""Phase 1 / js/app.js: auth form behaviour. Run from the repo root: python3 step1_appjs.py"""
P = "js/app.js"
s = open(P, encoding="utf-8").read()


def swap_block(start, end, new):
    """Replace everything from `start` up to (not including) `end`."""
    global s
    assert s.count(start) == 1, "start marker not unique/found: " + start[:60]
    a = s.index(start)
    b = s.index(end, a)
    s = s[:a] + new + s[b:]


def once(old, new):
    global s
    assert s.count(old) == 1, f"expected exactly one match ({s.count(old)} found): {old[:80]}"
    s = s.replace(old, new)


# 1. setAuthMode + helpers (username/password rules, show/hide password, invalid-field handling)
NEW_MODE = r'''  function setAuthMode(mode) {
    authMode = mode;
    const reg = mode === "register";
    $("authTitle").textContent = reg ? "Create your account" : "Log in";
    $("authSubtitle").textContent = reg
      ? "Start with the 10-month AI Engineer roadmap, or build your own."
      : "Welcome back. Pick up where you left off.";
    $("authSubmit").textContent = reg ? "Create account" : "Log in";
    $("authToggleText").textContent = reg ? "Already have an account?" : "New here?";
    $("authToggle").textContent = reg ? "Log in" : "Create an account";
    $("authUsernameRule").classList.toggle("hidden", !reg);
    $("authPwRules").classList.toggle("hidden", !reg);
    $("authPassword").autocomplete = reg ? "new-password" : "current-password";
    $("authError").textContent = "";
    $("authRegisterFields").classList.toggle("hidden", !reg);
    $("authConfirmPasswordField").classList.toggle("hidden", !reg);
    $("authUsernameStatus").textContent = "";
    $("authUsernameStatus").className = "auth-field-hint";
    $("authPasswordMatch").textContent = "";
    $("authPasswordMatch").className = "auth-field-hint";
    setPasswordVisible(false);
    clearInvalid();
    updatePasswordRules();
    if (!reg) {
      $("authFirstName").value = "";
      $("authLastName").value = "";
      $("authConfirmPassword").value = "";
    }
  }

  // ----- Auth form helpers -----
  const AUTH_FIELDS = ["authFirstName", "authLastName", "authUsername", "authPassword", "authConfirmPassword"];

  function clearInvalid() {
    AUTH_FIELDS.forEach((id) => $(id).removeAttribute("aria-invalid"));
  }

  // Show a message in the error banner, mark the field and move focus to it.
  function failAuth(message, fieldId) {
    $("authError").textContent = message;
    if (!fieldId) return;
    $(fieldId).setAttribute("aria-invalid", "true");
    $(fieldId).focus();
  }

  function setPasswordVisible(visible) {
    ["authPassword", "authConfirmPassword"].forEach((id) => { $(id).type = visible ? "text" : "password"; });
    const btn = $("authPasswordToggle");
    btn.setAttribute("aria-pressed", String(visible));
    btn.setAttribute("aria-label", visible ? "Hide password" : "Show password");
    btn.innerHTML = window.Icons.svg(visible ? "eye-off" : "eye", { size: 18 });
  }

  function updatePasswordRules() {
    $("authRuleLength").classList.toggle("met", $("authPassword").value.length >= 8);
  }

'''
swap_block("  function setAuthMode(mode) {", "  function showAuth(mode, notice, opts) {", NEW_MODE)

# 2. submitAuth: validation messages, focus handling, loading button, success toast
NEW_SUBMIT = r'''  async function submitAuth(ev) {
    ev.preventDefault();
    const username = $("authUsername").value.trim();
    const password = $("authPassword").value;
    $("authError").textContent = "";
    clearInvalid();
    const register = authMode === "register";
    const firstName = $("authFirstName").value.trim();
    const lastName = $("authLastName").value.trim();

    if (register && !firstName) { failAuth("Enter your first name.", "authFirstName"); return; }
    if (register && !lastName) { failAuth("Enter your last name.", "authLastName"); return; }
    if (!username) { failAuth(register ? "Choose a username." : "Enter your username.", "authUsername"); return; }
    if (register && !/^[A-Za-z0-9_-]{3,32}$/.test(username)) {
      failAuth("Username must be 3 to 32 characters: letters, numbers, _ or -.", "authUsername"); return;
    }
    if (!password) { failAuth(register ? "Choose a password." : "Enter your password.", "authPassword"); return; }
    if (register && password.length < 8) { failAuth("Password must be at least 8 characters.", "authPassword"); return; }
    if (register && password !== $("authConfirmPassword").value) {
      failAuth("Passwords don't match.", "authConfirmPassword"); return;
    }

    const btn = $("authSubmit");
    btn.disabled = true;
    btn.classList.add("is-loading");
    try {
      const res = register
        ? await window.AuthApi.register(firstName, lastName, username, password)
        : await window.AuthApi.login(username, password);
      $("authPassword").value = "";
      $("authConfirmPassword").value = "";
      session.expiredFor = null;
      enterDashboard(res.user);
      if (register) toast("Account created. Your AI Engineer roadmap is ready.", "success");
    } catch (e) {
      $("authError").textContent = e.message;
    } finally {
      btn.disabled = false;
      btn.classList.remove("is-loading");
    }
  }

'''
swap_block("  async function submitAuth(ev) {", "  async function boot() {", NEW_SUBMIT)

# 3. Field hints: plain-language text (icons come from CSS)
once('el.textContent = r.available ? "✓ Available" : "✗ Already taken";',
     'el.textContent = r.available ? "Username is available." : "That username is taken.";')
once('el.textContent = match ? "✓ Passwords match" : "✗ Passwords do not match";',
     'el.textContent = match ? "Passwords match." : "Passwords don\'t match.";')
once('el.textContent = "Checking…";', 'el.textContent = "Checking availability…";')

# 4. Password field: live rules, show/hide toggle, Caps Lock hint
once('    $("authPassword").addEventListener("input", updatePasswordMatch);',
     '''    $("authPassword").addEventListener("input", () => { updatePasswordMatch(); updatePasswordRules(); });
    $("authPasswordToggle").addEventListener("click", () => {
      setPasswordVisible($("authPassword").type === "password");
    });
    // Caps Lock hint on the password fields
    ["authPassword", "authConfirmPassword"].forEach((id) => {
      const field = $(id);
      const check = (e) => {
        if (typeof e.getModifierState !== "function") return;
        $("authCapsHint").classList.toggle("hidden", !e.getModifierState("CapsLock"));
      };
      field.addEventListener("keydown", check);
      field.addEventListener("keyup", check);
      field.addEventListener("blur", () => $("authCapsHint").classList.add("hidden"));
    });''')

# 5. Decorative sample strip on the brand panel
NEW_PANEL = r'''  // Decorative sample on the login brand panel (no real data).
  function renderAuthPanelStrip() {
    const sample = [
      [100, 0, 0], [100, 0, 0], [62, 14, 0], [24, 10, 0], [0, 0, 0],
      [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
    ];
    const labels = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
    const months = sample.map(([completed, inProgress, blocked], i) => ({
      label: labels[i], title: `Month ${i + 1}`, total: 100, completed, inProgress, blocked, current: i === 2,
    }));
    $("authPanelStrip").innerHTML = window.MonthStrip.html(months, { size: "lg", labels: true });
  }

'''
once("  function wireSyncEvents() {", NEW_PANEL + "  function wireSyncEvents() {")
once("    initTheme();\n    wireEvents();", "    initTheme();\n    renderAuthPanelStrip();\n    wireEvents();")

open(P, "w", encoding="utf-8").write(s)
for required in ("function setPasswordVisible", "function updatePasswordRules", "function failAuth", "function renderAuthPanelStrip"):
    assert required in s, "missing " + required
assert "User ID" not in s, "old 'User ID' wording is still present"
assert "authHint" not in s, "reference to the removed #authHint element remains"
print("js/app.js updated")
