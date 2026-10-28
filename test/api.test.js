const { test, describe, before, after } = require("node:test");
const assert = require("node:assert/strict");
const jwt = require("jsonwebtoken");
const { startServer, client, creds, sampleData, SECRET } = require("./helpers");

let srv;
before(async () => { srv = await startServer(); });
after(async () => { await srv.close(); srv.db.close(); });

describe("auth flow", () => {
  test("register -> me -> logout -> login", async () => {
    const c = client(srv.base);
    assert.equal((await c.get("/api/auth/me")).status, 401);

    const reg = await c.post("/api/auth/register", creds("alice"));
    assert.equal(reg.status, 201);
    assert.deepEqual(reg.body, { user: { username: "alice" } });

    const me = await c.get("/api/auth/me");
    assert.equal(me.status, 200);
    assert.equal(me.body.user.username, "alice");

    const out = await c.post("/api/auth/logout");
    assert.equal(out.status, 204);
    assert.equal((await c.get("/api/auth/me")).status, 401);
    assert.equal((await c.get("/api/data")).status, 401);

    const login = await c.post("/api/auth/login", creds("alice"));
    assert.equal(login.status, 200);
    assert.equal((await c.get("/api/auth/me")).status, 200);
  });

  test("session cookie is httpOnly + SameSite=Lax; Secure only when configured", async () => {
    const c = client(srv.base);
    const reg = await c.post("/api/auth/register", creds("cookiecheck"));
    const sc = reg.setCookies[0];
    assert.match(sc, /HttpOnly/i);
    assert.match(sc, /SameSite=Lax/i);
    assert.doesNotMatch(sc, /Secure/i);

    const secure = await startServer({ cookieSecure: true });
    try {
      const c2 = client(secure.base);
      const r = await c2.post("/api/auth/register", creds("securecheck"));
      assert.match(r.setCookies[0], /Secure/i);
    } finally { await secure.close(); secure.db.close(); }
  });

  test("passwords are stored hashed, never plaintext", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("hashcheck", "my-secret-pass"));
    const { rows: [row] } = await srv.db.execute({
      sql: "SELECT password_hash FROM users WHERE username = ?",
      args: ["hashcheck"],
    });
    assert.match(row.password_hash, /^\$2[aby]\$/);
    assert.ok(!row.password_hash.includes("my-secret-pass"));
  });

  test("login failures are generic (wrong password == unknown user)", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("bob"));
    const wrongPw = await client(srv.base).post("/api/auth/login", creds("bob", "not-the-password"));
    const noUser = await client(srv.base).post("/api/auth/login", creds("nobody-here"));
    assert.equal(wrongPw.status, 401);
    assert.equal(noUser.status, 401);
    assert.deepEqual(wrongPw.body, noUser.body);
    assert.equal(wrongPw.body.error, "Invalid credentials");
  });

  test("usernames are case-insensitive for uniqueness and login", async () => {
    const c = client(srv.base);
    assert.equal((await c.post("/api/auth/register", creds("CaseUser"))).status, 201);
    assert.equal((await client(srv.base).post("/api/auth/register", creds("caseuser"))).status, 409);
    const login = await client(srv.base).post("/api/auth/login", creds("CASEUSER"));
    assert.equal(login.status, 200);
    assert.equal(login.body.user.username, "CaseUser"); // keeps the registered casing
  });

  test("input validation", async () => {
    const c = client(srv.base);
    const bad = [
      creds("ab"),                       // too short
      creds("x".repeat(33)),             // too long
      creds("has space"),                // bad chars
      creds("emoji😀name"),              // bad chars
      creds("validname", "short"),       // password < 8
      creds("validname", "é".repeat(40)),// > 72 bytes
      { username: 123, password: "whatever123" },
      {},
    ];
    for (const b of bad) {
      const r = await c.post("/api/auth/register", b);
      assert.equal(r.status, 400, JSON.stringify(b).slice(0, 60));
    }
    const ok = await c.post("/api/auth/register", creds("A_b-9"));
    assert.equal(ok.status, 201);
  });

  test("a forged or foreign-signed token is rejected", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("forgeme"));
    const forged = jwt.sign({ un: "forgeme" }, "some-other-secret", { subject: "1", algorithm: "HS256" });
    c.jar.set("rd_session", forged);
    assert.equal((await c.get("/api/auth/me")).status, 401);
    const none = jwt.sign({ un: "x" }, "", { subject: "1", algorithm: "none" });
    c.jar.set("rd_session", none);
    assert.equal((await c.get("/api/data")).status, 401);
  });
});

describe("data save/load", () => {
  test("new user has no data; PUT then GET round-trips and bumps version", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("roundtrip"));

    const empty = await c.get("/api/data");
    assert.equal(empty.status, 200);
    assert.equal(empty.body.data, null);
    assert.equal(empty.body.version, 0);

    const d1 = sampleData();
    const p1 = await c.put("/api/data", { data: d1, version: 0 });
    assert.equal(p1.status, 200);
    assert.equal(p1.body.version, 1);

    const got = await c.get("/api/data");
    assert.deepEqual(got.body.data, d1);
    assert.equal(got.body.version, 1);
    assert.ok(got.body.updatedAt);

    const d2 = sampleData({ counters: { "counter-dsa": 4 } });
    const p2 = await c.put("/api/data", { data: d2, version: 1 });
    assert.equal(p2.body.version, 2);
    assert.deepEqual((await c.get("/api/data")).body.data, d2);
  });

  test("custom months/sections/topics round-trip unchanged and stay per-user", async () => {
    const a = client(srv.base), b = client(srv.base);
    await a.post("/api/auth/register", creds("monthsa"));
    await b.post("/api/auth/register", creds("monthsb"));
    const custom = {
      phases: [{ id: "custom-month-x", title: "Rust", objective: "ship a crate",
                 sections: [{ id: "custom-section-x", title: "Ownership", weekNumber: 3 }] }],
      topics: [{ id: "custom-topic-x", sectionId: "custom-section-x", title: "Borrowing", depth: "D2",
                 tasks: [{ id: "custom-task-x", title: "Read the book chapter" }] }],
    };
    const data = sampleData({ custom });
    assert.equal((await a.put("/api/data", { data, version: 0 })).status, 200);
    assert.deepEqual((await a.get("/api/data")).body.data.custom, custom);
    assert.equal((await b.get("/api/data")).body.data, null);
    const bad = sampleData({ custom: { topics: [], phases: [{ id: "m", title: "x", sections: [{ id: "s", title: "t", weekNumber: 9 }] }] } });
    assert.equal((await a.put("/api/data", { data: bad, version: 1 })).status, 400);
    assert.deepEqual((await a.get("/api/data")).body.data.custom, custom); // rejected save changed nothing
  });

  test("an export file (with exportedAt/version extras) is accepted as-is", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("exportfile"));
    const exported = { exportedAt: "2026-10-14T00:00:00.000Z", version: 1, ...sampleData() };
    assert.equal((await c.put("/api/data", { data: exported, version: 0 })).status, 200);
  });

  test("rejects data that doesn't match the import schema", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("badshape"));
    const cases = [
      null, "string", [], {},
      { items: [] },
      { items: { a: { status: "done-ish" } } },
      { items: {}, counters: { x: -1 } },
      { items: {}, settings: { startMonth: "October" } },
      { items: {}, custom: { topics: [{ id: "t", sectionId: "s", title: "x" }] } },
    ];
    for (const data of cases) {
      const r = await c.put("/api/data", { data, version: 0 });
      assert.equal(r.status, 400, JSON.stringify(data));
    }
    assert.equal((await c.put("/api/data", { data: sampleData(), version: "0" })).status, 400);
    assert.equal((await c.put("/api/data", { data: sampleData(), version: -1 })).status, 400);
    assert.equal((await c.get("/api/data")).body.data, null); // nothing was saved
  });

  test("unauthenticated access to data is refused", async () => {
    const c = client(srv.base);
    assert.equal((await c.get("/api/data")).status, 401);
    assert.equal((await c.put("/api/data", { data: sampleData(), version: 0 })).status, 401);
  });

  test("request bodies over 5 MB are rejected with 413", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("bigbody"));
    const big = sampleData({ items: { "x": { status: "not_started", notes: "a".repeat(5.5 * 1024 * 1024) } } });
    assert.equal((await c.put("/api/data", { data: big, version: 0 })).status, 413);
  });

  test("malformed JSON gets a clean 400", async () => {
    const c = client(srv.base);
    const r = await c.request("POST", "/api/auth/login", "{not json", { "content-type": "application/json" });
    assert.equal(r.status, 400);
  });
});

describe("version conflicts", () => {
  test("stale version -> 409 with the server copy; overwrite works after adopting its version", async () => {
    const c1 = client(srv.base), c2 = client(srv.base); // same user, two devices
    await c1.post("/api/auth/register", creds("twodevices"));
    await c2.post("/api/auth/login", creds("twodevices"));

    const base = sampleData();
    assert.equal((await c1.put("/api/data", { data: base, version: 0 })).body.version, 1);

    const fromLaptop = sampleData({ counters: { "counter-dsa": 10 } });
    assert.equal((await c1.put("/api/data", { data: fromLaptop, version: 1 })).body.version, 2);

    // device 2 still thinks the version is 1
    const stale = await c2.put("/api/data", { data: sampleData({ counters: { "counter-dsa": 99 } }), version: 1 });
    assert.equal(stale.status, 409);
    assert.equal(stale.body.server.version, 2);
    assert.deepEqual(stale.body.server.data, fromLaptop);

    // server copy was not clobbered
    assert.deepEqual((await c1.get("/api/data")).body.data, fromLaptop);

    // user chooses "overwrite": retry using the server's version
    const mine = sampleData({ counters: { "counter-dsa": 99 } });
    const over = await c2.put("/api/data", { data: mine, version: stale.body.server.version });
    assert.equal(over.status, 200);
    assert.equal(over.body.version, 3);
    assert.deepEqual((await c1.get("/api/data")).body.data, mine);
  });

  test("a brand-new account can't be saved with a non-zero version", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("freshconflict"));
    const r = await c.put("/api/data", { data: sampleData(), version: 5 });
    assert.equal(r.status, 409);
    assert.deepEqual(r.body.server, { data: null, version: 0 });
  });
});

describe("cross-user isolation", () => {
  test("user A cannot read or write user B's data", async () => {
    const a = client(srv.base), b = client(srv.base);
    await a.post("/api/auth/register", creds("iso_a"));
    await b.post("/api/auth/register", creds("iso_b"));

    const aData = sampleData({ counters: { "counter-dsa": 111 } });
    const bData = sampleData({ counters: { "counter-dsa": 222 } });
    assert.equal((await a.put("/api/data", { data: aData, version: 0 })).status, 200);

    // B starts with nothing, not A's data
    const bFirst = await b.get("/api/data");
    assert.equal(bFirst.body.data, null);

    // B saving starts at version 0 for B's own row; A's row is untouched
    assert.equal((await b.put("/api/data", { data: bData, version: 0 })).body.version, 1);
    assert.deepEqual((await a.get("/api/data")).body.data, aData);
    assert.deepEqual((await b.get("/api/data")).body.data, bData);

    // The user id can't be smuggled in via query string, body, or headers
    const aId = (await srv.db.execute("SELECT id FROM users WHERE username='iso_a'")).rows[0].id;
    const sneaky = await b.request("PUT", `/api/data?user_id=${aId}&userId=${aId}`,
      { data: sampleData({ counters: { "counter-dsa": 666 } }), version: 1, user_id: aId, userId: aId },
      { "x-user-id": String(aId) });
    assert.equal(sneaky.status, 200);
    assert.deepEqual((await a.get("/api/data")).body.data, aData);
    assert.equal((await b.get("/api/data")).body.data.counters["counter-dsa"], 666);

    // Straight from the DB: exactly one row each, matching their own data
    const { rows } = await srv.db.execute(
      "SELECT u.username, d.data FROM user_data d JOIN users u ON u.id = d.user_id WHERE u.username IN ('iso_a','iso_b') ORDER BY u.username");
    assert.equal(rows.length, 2);
    assert.equal(JSON.parse(rows[0].data).counters["counter-dsa"], 111);
    assert.equal(JSON.parse(rows[1].data).counters["counter-dsa"], 666);
  });

  test("logging out one browser doesn't expose data to a new user in the same browser", async () => {
    const shared = client(srv.base);
    await shared.post("/api/auth/register", creds("shared_one"));
    await shared.put("/api/data", { data: sampleData(), version: 0 });
    await shared.post("/api/auth/logout");
    assert.equal((await shared.get("/api/data")).status, 401);
    await shared.post("/api/auth/register", creds("shared_two"));
    assert.equal((await shared.get("/api/data")).body.data, null);
  });

  test("deleting a user removes their data (FK cascade enabled)", async () => {
    const c = client(srv.base);
    await c.post("/api/auth/register", creds("cascade"));
    await c.put("/api/data", { data: sampleData(), version: 0 });
    const id = (await srv.db.execute("SELECT id FROM users WHERE username='cascade'")).rows[0].id;
    await srv.db.execute({ sql: "DELETE FROM users WHERE id = ?", args: [id] });
    const left = await srv.db.execute({ sql: "SELECT COUNT(*) n FROM user_data WHERE user_id = ?", args: [id] });
    assert.equal(left.rows[0].n, 0);
    assert.equal((await c.get("/api/auth/me")).status, 401); // token for a deleted user is dead
  });
});

describe("rate limiting", () => {
  test("repeated failed logins get 429; register is limited too", async () => {
    const limited = await startServer({ authRateLimit: { windowMs: 60_000, max: 3 } });
    try {
      const c = client(limited.base);
      await c.post("/api/auth/register", creds("ratelimited"));
      const statuses = [];
      for (let i = 0; i < 5; i++) statuses.push((await c.post("/api/auth/login", creds("ratelimited", "wrong-password"))).status);
      assert.deepEqual(statuses, [401, 401, 401, 429, 429]);
      // a correct password is blocked too while locked out (that's the point)
      assert.equal((await c.post("/api/auth/login", creds("ratelimited"))).status, 429);
    } finally { await limited.close(); limited.db.close(); }
  });

  test("successful logins don't count toward the limit", async () => {
    const limited = await startServer({ authRateLimit: { windowMs: 60_000, max: 3 } });
    try {
      const c = client(limited.base);
      await c.post("/api/auth/register", creds("fine_user"));
      for (let i = 0; i < 6; i++) assert.equal((await c.post("/api/auth/login", creds("fine_user"))).status, 200);
    } finally { await limited.close(); limited.db.close(); }
  });
});

describe("static serving", () => {
  test("serves the app but not the database, server code or secrets", async () => {
    const c = client(srv.base);
    assert.equal((await c.get("/")).status, 200);
    assert.equal((await c.get("/css/styles.css")).status, 200);
    assert.equal((await c.get("/js/app.js")).status, 200);
    assert.equal((await c.get("/js/progress-schema.js")).status, 200);
    assert.equal((await c.get("/data/roadmap.js")).status, 200);
    for (const p of ["/data/app.db", "/data/app.db-wal", "/data/roadmap.md", "/server/app.js", "/server/db.js",
                     "/.env", "/.env.example", "/package.json", "/node_modules/express/package.json", "/test/api.test.js"]) {
      assert.equal((await c.get(p)).status, 404, p);
    }
    assert.equal((await c.get("/js/..%2fserver/app.js")).status, 404);
  });

  test("API responses are not cacheable", async () => {
    const r = await client(srv.base).get("/api/auth/me");
    assert.match(r.headers.get("cache-control"), /no-store/);
  });
});
