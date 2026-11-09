const { test, describe, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { buildCurriculum, summarize, EMPTY_CURRICULUM } = require("../js/roadmap-stats");
const { createStatsService } = require("../server/roadmaps/stats");
const { startServer, client, creds, dp } = require("./helpers");
const builtin = require("../data/roadmap.json");

// A tiny curriculum: month 1 has 3 tasks + 1 deliverable, month 2 has 1 task.
const SMALL = {
  meta: { horizonStart: "2026-10-01" },
  phases: [
    {
      id: "m1", number: 1, title: "One",
      sections: [{ id: "m1-s1", topics: [{ groups: [{ subtasks: [{ id: "a" }, { id: "b" }] }, { subtasks: [{ id: "c" }] }] }] }],
      deliverables: [{ id: "d1" }],
    },
    { id: "m2", number: 2, title: "Two", sections: [{ id: "m2-s1", topics: [{ groups: [{ subtasks: [{ id: "e" }] }] }] }], deliverables: [] },
  ],
};
const curriculum = buildCurriculum(SMALL);
const empty = () => ({ items: {}, counters: {}, celebratedPhases: [], settings: {}, custom: { topics: [], phases: [] } });

describe("roadmap-stats: summarize", () => {
  test("counts every task and deliverable once, per month and in total", () => {
    const s = summarize(curriculum, null);
    assert.equal(s.total, 5);
    assert.deepEqual(s.months.map((m) => [m.number, m.total]), [[1, 4], [2, 1]]);
    assert.equal(s.completed + s.inProgress + s.blocked, 0);
    assert.equal(s.startMonth, "2026-10");
  });

  test("counts each status; ids missing from items are not started", () => {
    const p = empty();
    p.items = { a: { status: "completed" }, b: { status: "in_progress" }, d1: { status: "blocked" }, e: { status: "completed" } };
    const s = summarize(curriculum, p);
    assert.deepEqual([s.completed, s.inProgress, s.blocked], [2, 1, 1]);
    assert.deepEqual(s.months[0], { number: 1, id: "m1", title: "One", total: 4, completed: 1, inProgress: 1, blocked: 1 });
    assert.equal(s.months[1].completed, 1);
  });

  test("user-added topics count in the month that owns their section", () => {
    const p = empty();
    p.custom.topics = [{ id: "t1", sectionId: "m2-s1", title: "x", tasks: [{ id: "x1" }, { id: "x2" }] }];
    p.items = { x1: { status: "completed" } };
    const s = summarize(curriculum, p);
    assert.equal(s.total, 7);
    assert.equal(s.months[1].total, 3);
    assert.equal(s.months[1].completed, 1);
  });

  test("user-added months follow the built-in months and own their topics", () => {
    const p = empty();
    p.custom.phases = [{ id: "cm1", title: "Extra", sections: [{ id: "cs1" }] }];
    p.custom.topics = [{ id: "t9", sectionId: "cs1", title: "y", tasks: [{ id: "y1" }] }];
    const s = summarize(curriculum, p);
    assert.equal(s.months.length, 3);
    assert.deepEqual([s.months[2].number, s.months[2].title, s.months[2].total], [3, "Extra", 1]);
  });

  test("a topic whose section no longer exists is ignored (the app does not show it)", () => {
    const p = empty();
    p.custom.topics = [{ id: "t", sectionId: "gone", title: "z", tasks: [{ id: "z1" }] }];
    assert.equal(summarize(curriculum, p).total, 5);
  });

  test("a custom roadmap with no months has no totals and no months", () => {
    const s = summarize(EMPTY_CURRICULUM, empty());
    assert.equal(s.total, 0);
    assert.deepEqual(s.months, []);
    assert.equal(s.startMonth, null);
  });

  test("startMonth: the saved setting wins over the authored default", () => {
    const p = empty();
    p.settings.startMonth = "2027-01";
    assert.equal(summarize(curriculum, p).startMonth, "2027-01");
  });

  test("completedLast7Days counts recent completions only", () => {
    const now = new Date("2026-11-04T12:00:00Z");
    const p = empty();
    p.items = {
      a: { status: "completed", completedAt: "2026-11-03T08:00:00Z" },
      b: { status: "completed", completedAt: "2026-10-20T08:00:00Z" },
      c: { status: "completed", completedAt: "not a date" },
      d1: { status: "completed", completedAt: null },
    };
    assert.equal(summarize(curriculum, p, { now }).completedLast7Days, 1);
  });

  test("malformed progress shapes do not throw", () => {
    assert.doesNotThrow(() => summarize(curriculum, { items: [], custom: { phases: "x", topics: 5 }, settings: null }));
  });

  test("the built-in roadmap has 10 months and 849 trackable items", () => {
    const s = summarize(buildCurriculum(builtin), null);
    assert.equal(s.months.length, 10);
    assert.equal(s.total, 849);
    assert.equal(s.startMonth, "2026-10");
  });
});

describe("stats service cache", () => {
  const row = (extra) => ({ id: 1, source: "builtin_ai_engineer", progressVersion: 1, progressData: JSON.stringify(empty()), ...extra });

  test("reuses a result for the same roadmap and version, recomputes after a new version", () => {
    const svc = createStatsService({ builtinData: builtin });
    const a = svc.forRoadmap(row());
    assert.equal(svc.forRoadmap(row()), a);
    assert.notEqual(svc.forRoadmap(row({ progressVersion: 2 })), a);
    assert.equal(svc.cacheSize(), 2);
  });

  test("expires entries after the TTL", () => {
    let now = 1_000_000;
    const svc = createStatsService({ builtinData: builtin, ttlMs: 1000, clock: () => now });
    const a = svc.forRoadmap(row());
    now += 2000;
    assert.notEqual(svc.forRoadmap(row()), a);
  });

  test("never grows past maxEntries", () => {
    const svc = createStatsService({ builtinData: builtin, maxEntries: 3 });
    for (let i = 1; i <= 10; i++) svc.forRoadmap(row({ id: i }));
    assert.equal(svc.cacheSize(), 3);
  });

  test("a roadmap with no saved progress is summarised without caching", () => {
    const svc = createStatsService({ builtinData: builtin });
    const s = svc.forRoadmap(row({ progressData: null, progressVersion: null }));
    assert.equal(s.total, 849);
    assert.equal(svc.cacheSize(), 0);
  });

  test("corrupt stored JSON gives null instead of throwing", () => {
    const svc = createStatsService({ builtinData: builtin });
    assert.equal(svc.forRoadmap(row({ progressData: "{not json" })), null);
  });

  test("an unknown source is treated as an empty custom roadmap", () => {
    const svc = createStatsService({ builtinData: builtin });
    assert.equal(svc.forRoadmap(row({ source: "custom", progressData: null, progressVersion: null })).total, 0);
  });
});

describe("GET /api/roadmaps includes stats", () => {
  let srv;
  before(async () => { srv = await startServer(); });
  after(async () => { await srv.close(); srv.db.close(); });

  async function register(name) {
    const c = client(srv.base);
    assert.equal((await c.post("/api/auth/register", creds(name))).status, 201);
    return c;
  }

  test("a new account's built-in roadmap reports 849 not-started items over 10 months", async () => {
    const c = await register("stats_new");
    const [r] = (await c.get("/api/roadmaps")).body.roadmaps;
    assert.equal(r.stats.total, 849);
    assert.equal(r.stats.completed, 0);
    assert.equal(r.stats.months.length, 10);
    assert.equal(r.stats.startMonth, "2026-10");
  });

  test("stats follow saved progress and never expose the raw progress blob", async () => {
    const c = await register("stats_saved");
    const path = await dp(c);
    const first = builtin.phases[0].sections[0].topics[0].groups[0].subtasks[0].id;
    const data = empty();
    data.items[first] = { status: "completed", completedAt: new Date().toISOString() };
    data.settings.startMonth = "2027-02";
    assert.equal((await c.put(path, { data, version: 0 })).status, 200);

    const res = await c.get("/api/roadmaps");
    const [r] = res.body.roadmaps;
    assert.equal(r.stats.completed, 1);
    assert.equal(r.stats.months[0].completed, 1);
    assert.equal(r.stats.completedLast7Days, 1);
    assert.equal(r.stats.startMonth, "2027-02");
    assert.equal("progressData" in r || "data" in r || "progressVersion" in r, false);
    assert.doesNotMatch(res.text, /celebratedPhases/);
  });

  test("a custom roadmap with a topic reports that topic's tasks", async () => {
    const c = await register("stats_custom");
    const created = await c.post("/api/roadmaps", { name: "Mine" });
    const id = created.body.roadmap.id;
    const data = empty();
    data.custom.phases = [{ id: "cm1", title: "M1", sections: [{ id: "cs1", title: "S" }] }];
    data.custom.topics = [{ id: "ct1", sectionId: "cs1", title: "T", tasks: [{ id: "k1", title: "a" }, { id: "k2", title: "b" }] }];
    data.items = { k1: { status: "completed" } };
    assert.equal((await c.put(`/api/roadmaps/${id}/progress`, { data, version: 0 })).status, 200);
    const mine = (await c.get("/api/roadmaps")).body.roadmaps.find((r) => r.id === id);
    assert.deepEqual([mine.stats.total, mine.stats.completed, mine.stats.months.length], [2, 1, 1]);
  });

  test("one user's progress never leaks into another user's list", async () => {
    const a = await register("stats_iso_a");
    const b = await register("stats_iso_b");
    const data = empty();
    data.items[builtin.phases[0].deliverables[0].id] = { status: "completed" };
    assert.equal((await a.put(await dp(a), { data, version: 0 })).status, 200);
    assert.equal((await b.get("/api/roadmaps")).body.roadmaps[0].stats.completed, 0);
  });
});
