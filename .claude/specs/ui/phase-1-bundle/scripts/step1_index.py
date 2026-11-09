"""Phase 1 / index.html: new split-screen auth markup + stylesheet and script tags.
Run from the repo root: python3 step1_index.py"""
P = "index.html"
s = open(P, encoding="utf-8").read()

NEW_AUTH = r'''<div id="authScreen" class="auth-screen hidden">
  <div class="auth-layout">
    <aside class="auth-panel" aria-hidden="true">
      <div class="auth-panel-top"><img class="brand-mark" src="img/logo.svg" alt="" width="28" height="28" /> Roadmap Tracker</div>
      <div>
        <p class="auth-panel-title">Turn a learning goal into a plan you can finish.</p>
        <p class="auth-panel-text">Every account starts with a 10-month Production AI Engineer roadmap. Build your own plan whenever you need one.</p>
        <div class="auth-panel-demo">
          <div class="auth-panel-demo-head">AI Engineer Roadmap <span>Sample progress</span></div>
          <div id="authPanelStrip"></div>
          <p class="auth-panel-demo-foot">Month 3 of 10 &middot; 29% complete</p>
        </div>
      </div>
      <p class="auth-panel-foot">Open source. Contributions welcome.</p>
    </aside>

    <section class="auth-main">
      <div class="auth-main-inner">
        <form id="authForm" class="auth-card" novalidate>
          <div class="auth-brand auth-brand-compact"><img class="brand-mark" src="img/logo.svg" alt="" width="24" height="24" /> Roadmap Tracker</div>
          <h2 id="authTitle">Log in</h2>
          <p id="authSubtitle" class="auth-subtitle">Welcome back. Pick up where you left off.</p>
          <p id="authNotice" class="auth-notice hidden"></p>
          <p id="authError" class="auth-error" role="alert"></p>

          <!-- Register-only fields (hidden during login) -->
          <div id="authRegisterFields" class="field-row hidden">
            <div class="field">
              <label for="authFirstName">First name</label>
              <input id="authFirstName" type="text" autocomplete="given-name" autocapitalize="words" maxlength="64" />
            </div>
            <div class="field">
              <label for="authLastName">Last name</label>
              <input id="authLastName" type="text" autocomplete="family-name" autocapitalize="words" maxlength="64" />
            </div>
          </div>

          <div class="field">
            <label id="authUsernameLabel" for="authUsername">Username</label>
            <input id="authUsername" type="text" autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="32" aria-describedby="authUsernameRule authUsernameStatus" />
            <p id="authUsernameRule" class="field-hint hidden">3 to 32 characters. Letters, numbers, _ and -</p>
            <p id="authUsernameStatus" class="auth-field-hint" aria-live="polite"></p>
          </div>

          <div class="field">
            <label for="authPassword">Password</label>
            <div class="input-affix">
              <input id="authPassword" type="password" autocomplete="current-password" maxlength="72" aria-describedby="authCapsHint authPwRules" />
              <button type="button" id="authPasswordToggle" class="input-affix-btn" aria-label="Show password" aria-pressed="false"></button>
            </div>
            <p id="authCapsHint" class="field-hint hidden">Caps Lock is on.</p>
            <ul id="authPwRules" class="rules hidden" aria-label="Password requirements">
              <li id="authRuleLength">At least 8 characters</li>
            </ul>
          </div>

          <!-- Confirm password — register only -->
          <div id="authConfirmPasswordField" class="field hidden">
            <label for="authConfirmPassword">Confirm password</label>
            <input id="authConfirmPassword" type="password" autocomplete="new-password" maxlength="72" />
            <p id="authPasswordMatch" class="auth-field-hint" aria-live="polite"></p>
          </div>

          <button id="authSubmit" class="btn btn-primary btn-lg auth-submit" type="submit">Log in</button>
          <p class="auth-toggle"><span id="authToggleText">New here?</span> <button type="button" id="authToggle" class="link-btn">Create an account</button></p>
          <button type="button" id="authDownload" class="link-btn hidden">Download my unsaved changes (JSON)</button>
        </form>
        <div id="authBlock" class="auth-card hidden">
          <div class="auth-brand auth-brand-compact"><img class="brand-mark" src="img/logo.svg" alt="" width="24" height="24" /> Roadmap Tracker</div>
          <h2 id="authBlockTitle"></h2>
          <p id="authBlockText" class="auth-notice"></p>
          <div id="authBlockActions" class="modal-actions"></div>
        </div>
      </div>

      <footer class="auth-footer">
        <p>&copy; <span id="authFooterYear"></span> Roadmap Tracker &middot;
          Developed by <a href="mailto:upendra.kumar48762@gmail.com">upendra.kumar48762@gmail.com</a> &middot;
          <a href="https://github.com/imkushwaha" target="_blank" rel="noopener">GitHub: imkushwaha</a> &middot;
          If this tool helps you, please <a href="https://github.com/imkushwaha" target="_blank" rel="noopener">star the repo</a></p>
        <details class="auth-about">
          <summary>About this project</summary>
          <p>Built with planning &amp; development assistance from <strong>Claude</strong> (Anthropic AI). Open source &mdash; contributions welcome.</p>
        </details>
      </footer>
    </section>
  </div>
</div>
'''

start = '<div id="authScreen"'
end = '<div id="dashboardScreen"'
assert s.count(start) == 1 and s.count(end) == 1, "auth/dashboard markers not found"
a, b = s.index(start), s.index(end)
s = s[:a] + NEW_AUTH.rstrip("\n") + "\n\n" + s[b:]

def once(old, new):
    global s
    assert s.count(old) == 1, "expected exactly one match: " + old[:70]
    s = s.replace(old, new)

once('<link rel="stylesheet" href="css/components.css" />',
     '<link rel="stylesheet" href="css/components.css" />\n<link rel="stylesheet" href="css/auth.css" />')
once('<script src="js/icons.js"></script>',
     '<script src="js/icons.js"></script>\n<script src="js/month-strip.js"></script>')

open(P, "w", encoding="utf-8").write(s)
for required in ('id="authForm"', 'id="authBlock"', 'id="authPasswordToggle"', 'id="authPanelStrip"', 'id="authFooterYear"',
                 'id="authUsernameStatus"', 'id="authPasswordMatch"', 'id="authDownload"'):
    assert required in s, "missing " + required
print("index.html updated")
