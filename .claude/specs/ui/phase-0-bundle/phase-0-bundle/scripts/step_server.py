"""Phase 0 / server/app.js + test/api.test.js. Run from the repo root: python3 step_server.py"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match for: {old[:70]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("server/app.js", [(
'''  app.use("/js", express.static(path.join(staticRoot, "js")));''',
'''  app.use("/js", express.static(path.join(staticRoot, "js")));
  // Self-hosted fonts and the logo/favicon. Fonts never change for a given file
  // name, so let browsers cache them for a year.
  app.use("/fonts", express.static(path.join(staticRoot, "fonts"), { maxAge: "365d", immutable: true }));
  app.use("/img", express.static(path.join(staticRoot, "img")));''')])

patch("test/api.test.js", [
('''    assert.equal((await c.get("/data/roadmap.js")).status, 200);
    for (const p of ["/data/app.db",''',
'''    assert.equal((await c.get("/data/roadmap.js")).status, 200);
    for (const p of ["/css/tokens.css", "/css/base.css", "/css/components.css", "/js/theme-boot.js", "/js/icons.js",
                     "/img/logo.svg", "/img/favicon.svg", "/fonts/ibm-plex-sans-latin-400-normal.woff2"]) {
      assert.equal((await c.get(p)).status, 200, p);
    }
    for (const p of ["/fonts/", "/fonts/../.env", "/img/../package.json", "/data/app.db",'''),
('''  test("API responses are not cacheable", async () => {''',
'''  test("fonts are cacheable; the page forbids inline scripts", async () => {
    const font = await client(srv.base).get("/fonts/ibm-plex-sans-latin-400-normal.woff2");
    assert.match(font.headers.get("cache-control"), /max-age=31536000/);
    const page = await client(srv.base).get("/");
    const csp = page.headers.get("content-security-policy");
    assert.match(csp, /script-src 'self'/);
    assert.doesNotMatch(csp.split(";").find((d) => d.trim().startsWith("script-src")), /unsafe-inline/);
  });

  test("API responses are not cacheable", async () => {'''),
])
print("server/app.js and test/api.test.js updated")
