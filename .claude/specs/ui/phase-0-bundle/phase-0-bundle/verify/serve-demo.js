// Temporary verification server (NOT part of the repo). Usage:
//   node serve-demo.js <repo-root> [port]
// Boots the real app on an in-memory database with one demo user and some progress.
const path = require("node:path");
const root = path.resolve(process.argv[2] || ".");
const port = Number(process.argv[3] || 3111);
const { openDb } = require(path.join(root, "server/db"));
const { createApp } = require(path.join(root, "server/app"));

(async () => {
  const db = await openDb(":memory:");
  const app = createApp({
    db, sessionSecret: "x".repeat(40), bcryptCost: 4,
    authRateLimit: { windowMs: 60000, max: 10000 }, staticRoot: root,
  });
  app.listen(port, "127.0.0.1", async () => {
    const base = `http://127.0.0.1:${port}`;
    const r = await fetch(base + "/api/auth/register", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ username: "imkushwaha", password: "demo-pass-123", firstName: "Upendra", lastName: "Kumar" }),
    });
    const cookie = (r.headers.get("set-cookie") || "").split(";")[0];
    const list = await (await fetch(base + "/api/roadmaps", { headers: { cookie } })).json();
    const id = list.roadmaps[0].id;
    const data = require(path.join(root, "data/roadmap.json"));
    const items = {};
    let n = 0;
    data.phases.slice(0, 1).forEach((p) => p.sections.forEach((s) => s.topics.forEach((t) => t.groups.forEach((g) => g.subtasks.forEach((st) => {
      n += 1;
      if (n % 3 !== 0) items[st.id] = { status: "completed", completedAt: new Date(Date.now() - (n % 20) * 86400000).toISOString() };
      else if (n % 7 === 0) items[st.id] = { status: "in_progress" };
    })))));
    data.phases.slice(1, 2).forEach((p) => p.sections.forEach((s) => s.topics.forEach((t) => t.groups.forEach((g) => g.subtasks.forEach((st, i) => {
      if (i === 0) items[st.id] = { status: "completed", completedAt: new Date().toISOString() };
      else if (i === 1) items[st.id] = { status: "blocked" };
      else if (i === 2) items[st.id] = { status: "in_progress" };
    })))));
    const put = await fetch(`${base}/api/roadmaps/${id}/progress`, {
      method: "PUT", headers: { "content-type": "application/json", cookie },
      body: JSON.stringify({ version: 0, data: { items, counters: {}, celebratedPhases: [], settings: { startMonth: "2026-10" }, custom: { topics: [], phases: [] } } }),
    });
    console.log(`ready on ${base} (seed ${put.status}, ${Object.keys(items).length} items). Login: imkushwaha / demo-pass-123`);
  });
})();
