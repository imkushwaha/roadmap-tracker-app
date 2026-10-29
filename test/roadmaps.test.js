const { test, describe, before, after } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { createClient } = require("@libsql/client");
const { openDb } = require("../server/db");
const { startServer, client, creds, sampleData, dp } = require("./helpers");

let srv;
before(async () => { srv = await startServer(); });
after(async () => { await srv.close(); srv.db.close(); });

async function register(name) {
  const c = client(srv.base);
  assert.equal((await c.post("/api/auth/register", creds(name))).status, 201);
  return c;
}

describe("starter roadmap", () => {
  test("every new account is seeded with the AI Engineer roadmap", async () => {
    const c = await register("seeded");
    const list = await c.get("/api/roadmaps");
    assert.equal(list.status, 200);
    assert.equal(list.body.roadmaps.length, 1);
    const [r] = list.body.roadmaps;
    assert.equal(r.name, "AI Engineer Roadmap");
    assert.equal(r.source, "builtin_ai_engineer");
    assert.equal(r.lastActivityAt, null);
    assert.ok(r.id > 0 && r.createdAt);
  });

  test("progress response carries the roadmap metadata; lastActivityAt appears after a save", async () => {
    const c = await register("withmeta");
    const path = await dp(c);
    const empty = await c.get(path);
    assert.equal(empty.body.roadmap.source, "builtin_ai_engineer");
    assert.equal(empty.body.data, null);
    assert.equal(empty.body.version, 0);

    assert.equal((await c.put(path, { data: sampleData(), version: 0 })).status, 200);
    const [r] = (await c.get("/api/roadmaps")).body.roadmaps;
    assert.ok(r.lastActivityAt);
  });
});

describe("authentication & isolation", () => {
  test("every roadmap route requires a session", async () => {
    const c = client(srv.base);
    assert.equal((await c.get("/api/roadmaps")).status, 401);
    assert.equal((await c.post("/api/roadmaps", { source: "builtin_ai_engineer" })).status, 401);
    assert.equal((await c.request("DELETE", "/api/roadmaps/1")).status, 401);
    assert.equal((await c.get("/api/roadmaps/1/progress")).status, 401);
    assert.equal((await c.put("/api/roadmaps/1/progress", { data: sampleData(), version: 0 })).status, 401);
  });

  test("a user cannot read, write or delete another user's roadmap", async () => {
    const a = await register("owner_a");
    const b = await register("owner_b");
    const aPath = await dp(a);
    assert.equal((await a.put(aPath, { data: sampleData(), version: 0 })).status, 200);

    assert.equal((await b.get(aPath)).status, 404);
    assert.equal((await b.put(aPath, { data: sampleData(), version: 1 })).status, 404);
    assert.equal((await b.request("DELETE", aPath.replace("/progress", ""))).status, 404);

    // A's data is untouched and still listed
    assert.equal((await a.get(aPath)).body.version, 1);
    assert.equal((await a.get("/api/roadmaps")).body.roadmaps.length, 1);
  });

  test("malformed or unknown ids are a clean 404", async () => {
    const c = await register("badids");
    for (const id of ["abc", "0", "999999", "1.5", "-1"]) {
      assert.equal((await c.get(`/api/roadmaps/${id}/progress`)).status, 404, id);
      assert.equal((await c.request("DELETE", `/api/roadmaps/${id}`)).status, 404, id);
    }
  });
});

describe("delete & restore", () => {
  test("deleting a roadmap removes it and its progress", async () => {
    const c = await register("deleter");
    const progressPath = await dp(c);
    const roadmapPath = progressPath.replace("/progress", "");
    const id = Number(roadmapPath.split("/").pop());
    await c.put(progressPath, { data: sampleData(), version: 0 });

    assert.equal((await c.request("DELETE", roadmapPath)).status, 204);
    assert.deepEqual((await c.get("/api/roadmaps")).body.roadmaps, []);
    assert.equal((await c.get(progressPath)).status, 404);
    assert.equal((await c.request("DELETE", roadmapPath)).status, 404); // already gone

    const left = await srv.db.execute({ sql: "SELECT COUNT(*) n FROM roadmap_progress WHERE roadmap_id = ?", args: [id] });
    assert.equal(left.rows[0].n, 0);
  });

  test("the AI Engineer roadmap can be restored once, and starts fresh", async () => {
    const c = await register("restorer");
    const progressPath = await dp(c);
    await c.put(progressPath, { data: sampleData(), version: 0 });

    const dup = await c.post("/api/roadmaps", { source: "builtin_ai_engineer" });
    assert.equal(dup.status, 409);

    await c.request("DELETE", progressPath.replace("/progress", ""));
    const restored = await c.post("/api/roadmaps", { source: "builtin_ai_engineer" });
    assert.equal(restored.status, 201);
    assert.equal(restored.body.roadmap.name, "AI Engineer Roadmap");

    const fresh = await c.get(await dp(c));
    assert.equal(fresh.body.data, null);
    assert.equal(fresh.body.version, 0);
  });

  test("unknown sources and nameless bodies are rejected", async () => {
    const c = await register("othersource");
    for (const body of [{}, { source: "custom" }, { source: 5 }, { source: "enterprise", name: "x" }]) {
      assert.equal((await c.post("/api/roadmaps", body)).status, 400, JSON.stringify(body));
    }
    assert.equal((await c.get("/api/roadmaps")).body.roadmaps.length, 1);
  });
});

describe("custom roadmaps", () => {
  test("creating one lists it alongside the starter and starts empty", async () => {
    const c = await register("creator");
    const res = await c.post("/api/roadmaps", { name: "  Learn Rust  ", description: "12 weeks of systems work" });
    assert.equal(res.status, 201);
    const { roadmap } = res.body;
    assert.equal(roadmap.name, "Learn Rust"); // trimmed
    assert.equal(roadmap.description, "12 weeks of systems work");
    assert.equal(roadmap.source, "custom");

    const list = (await c.get("/api/roadmaps")).body.roadmaps;
    assert.deepEqual(list.map((r) => r.source), ["builtin_ai_engineer", "custom"]);

    const fresh = await c.get(`/api/roadmaps/${roadmap.id}/progress`);
    assert.equal(fresh.status, 200);
    assert.equal(fresh.body.roadmap.source, "custom");
    assert.equal(fresh.body.data, null);
    assert.equal(fresh.body.version, 0);
  });

  test("a chosen start month is saved as version 1 of valid progress", async () => {
    const c = await register("monthpicker");
    const { roadmap } = (await c.post("/api/roadmaps", { name: "Plan", startMonth: "2027-02" })).body;
    const got = await c.get(`/api/roadmaps/${roadmap.id}/progress`);
    assert.equal(got.body.version, 1);
    assert.equal(got.body.data.settings.startMonth, "2027-02");
    assert.deepEqual(got.body.data.custom, { topics: [], phases: [] });
    // the next autosave continues from version 1
    const put = await c.put(`/api/roadmaps/${roadmap.id}/progress`, { data: got.body.data, version: 1 });
    assert.equal(put.body.version, 2);
  });

  test("custom content saved in a roadmap stays separate from other roadmaps", async () => {
    const c = await register("twoplans");
    const a = (await c.post("/api/roadmaps", { name: "A" })).body.roadmap;
    const b = (await c.post("/api/roadmaps", { name: "B" })).body.roadmap;
    const custom = {
      phases: [{ id: "custom-month-1", title: "Basics", objective: "", sections: [{ id: "custom-section-1", title: "Week", weekNumber: 1 }] }],
      topics: [{ id: "custom-topic-1", sectionId: "custom-section-1", title: "Syntax", depth: null, tasks: [{ id: "custom-task-1", title: "Read" }] }],
    };
    assert.equal((await c.put(`/api/roadmaps/${a.id}/progress`, { data: sampleData({ custom }), version: 0 })).status, 200);
    assert.equal((await c.get(`/api/roadmaps/${b.id}/progress`)).body.data, null);
    assert.deepEqual((await c.get(`/api/roadmaps/${a.id}/progress`)).body.data.custom, custom);
  });

  test("invalid input is rejected and creates nothing", async () => {
    const c = await register("badinput");
    const bad = [
      { name: "" },
      { name: "   " },
      { name: 42 },
      { name: "x".repeat(81) },
      { name: "two\nlines" },
      { name: "ok", description: 7 },
      { name: "ok", description: "d".repeat(301) },
      { name: "ok", startMonth: "October" },
      { name: "ok", startMonth: "2027-13" },
      { name: "ok", startMonth: 202702 },
    ];
    for (const body of bad) {
      assert.equal((await c.post("/api/roadmaps", body)).status, 400, JSON.stringify(body).slice(0, 60));
    }
    assert.equal((await c.get("/api/roadmaps")).body.roadmaps.length, 1);
  });

  test("markup in names is stored verbatim (escaped on render, never executed)", async () => {
    const c = await register("markup");
    const res = await c.post("/api/roadmaps", { name: "<img src=x onerror=alert(1)>" });
    assert.equal(res.status, 201);
    assert.equal(res.body.roadmap.name, "<img src=x onerror=alert(1)>");
  });

  test("an account is capped at 20 roadmaps", async () => {
    const c = await register("collector");
    for (let i = 1; i < 20; i++) assert.equal((await c.post("/api/roadmaps", { name: `Plan ${i}` })).status, 201);
    const over = await c.post("/api/roadmaps", { name: "One too many" });
    assert.equal(over.status, 409);
    assert.match(over.body.error, /at most 20/);
    // deleting frees a slot
    const [first] = (await c.get("/api/roadmaps")).body.roadmaps;
    await c.request("DELETE", `/api/roadmaps/${first.id}`);
    assert.equal((await c.post("/api/roadmaps", { name: "Fits now" })).status, 201);
  });

  test("another user cannot open or delete a custom roadmap", async () => {
    const owner = await register("plan_owner");
    const other = await register("plan_other");
    const { roadmap } = (await owner.post("/api/roadmaps", { name: "Private" })).body;
    assert.equal((await other.get(`/api/roadmaps/${roadmap.id}/progress`)).status, 404);
    assert.equal((await other.request("DELETE", `/api/roadmaps/${roadmap.id}`)).status, 404);
    assert.equal((await owner.get(`/api/roadmaps/${roadmap.id}/progress`)).status, 200);
  });

  test("deleting a custom roadmap removes its progress too", async () => {
    const c = await register("customdeleter");
    const { roadmap } = (await c.post("/api/roadmaps", { name: "Temp", startMonth: "2027-01" })).body;
    assert.equal((await c.request("DELETE", `/api/roadmaps/${roadmap.id}`)).status, 204);
    const left = await srv.db.execute({ sql: "SELECT COUNT(*) n FROM roadmap_progress WHERE roadmap_id = ?", args: [roadmap.id] });
    assert.equal(left.rows[0].n, 0);
  });
});

describe("registration is atomic with the starter roadmap", () => {
  test("a rejected duplicate username leaves no orphan roadmap", async () => {
    await register("dupe_user");
    const before = (await srv.db.execute("SELECT COUNT(*) n FROM roadmaps")).rows[0].n;
    const dup = await client(srv.base).post("/api/auth/register", creds("DUPE_USER"));
    assert.equal(dup.status, 409);
    const after = (await srv.db.execute("SELECT COUNT(*) n FROM roadmaps")).rows[0].n;
    assert.equal(after, before);
  });
});

describe("legacy user_data migration", () => {
  const LEGACY_SCHEMA = [
    `CREATE TABLE users (
       id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
       password_hash TEXT NOT NULL, first_name TEXT NOT NULL DEFAULT '', last_name TEXT NOT NULL DEFAULT '',
       created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))`,
    `CREATE TABLE user_data (
       user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
       data TEXT NOT NULL, version INTEGER NOT NULL, updated_at TEXT NOT NULL)`,
  ];

  test("copies saved progress into the built-in roadmap exactly once", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "roadmap-migrate-"));
    const url = "file:" + path.join(dir, "legacy.db");
    try {
      const legacy = createClient({ url });
      await legacy.batch(LEGACY_SCHEMA, "write");
      await legacy.batch([
        "INSERT INTO users (username, password_hash) VALUES ('saved', 'x'), ('never_saved', 'x')",
        { sql: "INSERT INTO user_data (user_id, data, version, updated_at) VALUES (1, ?, 7, '2026-10-01T00:00:00.000Z')",
          args: [JSON.stringify(sampleData())] },
      ], "write");
      legacy.close();

      const db = await openDb(url);
      const rows = (await db.execute(
        `SELECT u.username, r.source, p.data, p.version, p.updated_at
         FROM roadmaps r JOIN users u ON u.id = r.user_id
         LEFT JOIN roadmap_progress p ON p.roadmap_id = r.id ORDER BY u.id`)).rows;
      assert.equal(rows.length, 2);
      assert.equal(rows[0].source, "builtin_ai_engineer");
      assert.deepEqual(JSON.parse(rows[0].data), sampleData());
      assert.equal(rows[0].version, 7);
      assert.equal(rows[0].updated_at, "2026-10-01T00:00:00.000Z");
      assert.equal(rows[1].data, null); // an account that never saved still gets its roadmap

      const tables = (await db.execute("SELECT name FROM sqlite_master WHERE type='table'")).rows.map((r) => r.name);
      assert.ok(tables.includes("user_data_legacy"));
      assert.ok(!tables.includes("user_data"));

      // A deleted roadmap must not be re-seeded on the next boot.
      await db.execute("DELETE FROM roadmaps WHERE user_id = 1");
      db.close();
      const again = await openDb(url);
      const count = (await again.execute("SELECT COUNT(*) n FROM roadmaps")).rows[0].n;
      assert.equal(count, 1);
      again.close();
    } finally {
      // Windows may still hold the SQLite file open; a leftover temp dir is harmless.
      try { fs.rmSync(dir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }); } catch { /* ignore */ }
    }
  });
});
