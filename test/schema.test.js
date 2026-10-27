const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { validateProgress } = require("../js/progress-schema");

const valid = () => ({
  items: { a: { status: "in_progress", notes: "", link: "", dueDate: "2026-10-20", completedAt: null } },
  counters: { c: 2 }, celebratedPhases: ["month-1"],
  settings: { startMonth: "2026-11" },
  custom: { topics: [{ id: "custom-topic-1", sectionId: "month-1-week-1", title: "T", depth: "D2", tasks: [{ id: "custom-task-1", title: "x" }] }] },
});

test("accepts a full, valid progress object", () => assert.deepEqual(validateProgress(valid()), { ok: true, errors: [] }));
test("optional sections may be missing (older exports)", () => assert.ok(validateProgress({ items: {} }).ok));
test("unknown top-level keys are ignored (exportedAt, version)", () => assert.ok(validateProgress({ ...valid(), exportedAt: "x", version: 1, future: {} }).ok));
test("rejects wrong types and bad enums with readable messages", () => {
  const r = validateProgress({ items: { a: { status: "nope" } }, counters: [], settings: { startMonth: "Oct" } });
  assert.equal(r.ok, false);
  assert.ok(r.errors.length >= 3);
  assert.match(r.errors[0], /status must be one of/);
});
test("rejects __proto__ keys", () => {
  assert.equal(validateProgress(JSON.parse('{"items":{"__proto__":{}}}')).ok, false);
});
test("the app's own initial/empty state validates", () => {
  assert.ok(validateProgress({ items: {}, counters: {}, celebratedPhases: [], settings: {}, custom: { topics: [] } }).ok);
});
test("every statuses the UI can produce is accepted", () => {
  for (const status of ["not_started", "in_progress", "completed", "blocked"]) {
    assert.ok(validateProgress({ items: { a: { status } } }).ok, status);
  }
});
test("schema.md documents the same top-level keys the validator knows", () => {
  const doc = fs.readFileSync(path.join(__dirname, "../data/schema.md"), "utf8");
  for (const key of ["items", "counters", "celebratedPhases", "settings", "custom"]) assert.ok(doc.includes(key), key);
});

const withPhases = (phases) => ({ items: {}, custom: { topics: [], phases } });
const goodPhase = () => ({ id: "custom-month-1", title: "Rust", objective: "", sections: [
  { id: "custom-section-1", title: "Ownership", weekNumber: 2 },
  { id: "custom-section-2", title: "Undated", weekNumber: null },
] });

test("custom.phases: accepts months with dated and undated sections", () => {
  assert.ok(validateProgress(withPhases([goodPhase()])).ok);
  assert.ok(validateProgress(withPhases([])).ok);
  assert.ok(validateProgress({ items: {}, custom: { topics: [] } }).ok); // phases stay optional
});
test("custom.phases: rejects malformed months and sections", () => {
  const bad = [
    "nope", [null], [{ title: "x", sections: [] }],                         // not array / null / missing id
    [{ id: "a", title: 5, sections: [] }],
    [{ id: "a", title: "x", sections: "no" }],
    [{ id: "a", title: "x", objective: 3, sections: [] }],
    [{ id: "a", title: "x", sections: [{ id: "s", title: "t", weekNumber: 5 }] }],   // week out of range
    [{ id: "a", title: "x", sections: [{ id: "s", title: "t", weekNumber: 1.5 }] }],
    [{ id: "a", title: "x", sections: [{ title: "t" }] }],
  ];
  for (const phases of bad) assert.equal(validateProgress({ items: {}, custom: { phases } }).ok, false, JSON.stringify(phases));
});
