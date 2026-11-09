"""Phase 0 / index.html. Run from the repo root: python3 step_index.py"""
P = "index.html"
s = open(P, encoding="utf-8").read()


def replace(old, new, count=1):
    global s
    assert old in s, "pattern not found: " + old[:80]
    s = s.replace(old, new, count) if count else s.replace(old, new)


# 1. <head>: SVG favicon, theme script (blocking, external), font preloads, split stylesheets
replace('''<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🧭</text></svg>" />
<link rel="stylesheet" href="css/styles.css" />''',
'''<link rel="icon" type="image/svg+xml" href="img/favicon.svg" />
<meta name="color-scheme" content="light dark" />
<script src="js/theme-boot.js"></script>
<link rel="preload" href="fonts/ibm-plex-sans-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin />
<link rel="preload" href="fonts/ibm-plex-sans-latin-500-normal.woff2" as="font" type="font/woff2" crossorigin />
<link rel="stylesheet" href="css/tokens.css" />
<link rel="stylesheet" href="css/base.css" />
<link rel="stylesheet" href="css/components.css" />
<link rel="stylesheet" href="css/styles.css" />''')

# 2. Brand marks replace the compass emoji (2 on auth cards, 2 in headers)
replace('<div class="auth-brand"><span aria-hidden="true">🧭</span> Roadmap Tracker</div>',
        '<div class="auth-brand"><img class="brand-mark" src="img/logo.svg" alt="" width="24" height="24" /> Roadmap Tracker</div>', 0)
replace('<span class="brand-icon" aria-hidden="true">🧭</span>',
        '<img class="brand-mark" src="img/logo.svg" alt="" width="28" height="28" />', 0)

# 3. Account menu: "Theme" -> "Appearance" and a System option
replace('<span class="profile-panel-label">Theme</span>', '<span class="profile-panel-label">Appearance</span>')
replace('''                <button class="profile-theme-btn" id="themeDarkBtn" data-theme="dark">Dark</button>''',
        '''                <button class="profile-theme-btn" id="themeDarkBtn" data-theme="dark">Dark</button>
                <button class="profile-theme-btn" id="themeSystemBtn" data-theme="system">System</button>''')

# 4. Menu panels are labelled groups, not role="menu" (they hold mixed controls)
replace('id="profileTrigger" aria-haspopup="true" aria-expanded="false" aria-label="Account menu"',
        'id="profileTrigger" aria-expanded="false" aria-controls="profilePanel" aria-label="Account menu"')
replace('id="profilePanel" role="menu"', 'id="profilePanel" role="group" aria-label="Account"')
replace('id="roadmapMenuTrigger" aria-haspopup="true" aria-expanded="false" aria-label="Roadmap settings"',
        'id="roadmapMenuTrigger" aria-expanded="false" aria-controls="roadmapMenuPanel" aria-label="Roadmap settings"')
replace('id="roadmapMenuPanel" role="menu"', 'id="roadmapMenuPanel" role="group" aria-label="Roadmap settings"')

# 5. Icon script before the data script
replace('<script src="data/roadmap.js"></script>', '<script src="js/icons.js"></script>\n<script src="data/roadmap.js"></script>')

open(P, "w", encoding="utf-8").write(s)
assert "🧭" not in s, "an emoji brand mark is still present"
print("index.html updated")
