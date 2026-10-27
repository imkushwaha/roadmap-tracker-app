const { test } = require("node:test");
const assert = require("node:assert/strict");
const { loadConfig } = require("../server/config");

test("production refuses to start without SESSION_SECRET", () => {
  assert.throws(() => loadConfig({ NODE_ENV: "production" }), /SESSION_SECRET is required/);
});
test("production refuses a short SESSION_SECRET", () => {
  assert.throws(() => loadConfig({ NODE_ENV: "production", SESSION_SECRET: "short" }), /at least 32/);
});
test("production accepts a long secret, defaults, and secure cookies", () => {
  const c = loadConfig({ NODE_ENV: "production", SESSION_SECRET: "x".repeat(40) });
  assert.equal(c.cookieSecure, true);
  assert.equal(c.port, 3000);
  assert.match(c.dbPath, /data[\\/]app\.db$/);
});
test("development falls back to an ephemeral secret and non-secure cookies", () => {
  const warn = console.warn; console.warn = () => {};
  try {
    const c = loadConfig({});
    assert.ok(c.sessionSecret.length >= 32);
    assert.equal(c.cookieSecure, false);
  } finally { console.warn = warn; }
});
test("DB_PATH, PORT, COOKIE_SECURE and TRUST_PROXY are honoured", () => {
  const c = loadConfig({ NODE_ENV: "production", SESSION_SECRET: "x".repeat(40), DB_PATH: ":memory:", PORT: "8080", COOKIE_SECURE: "false", TRUST_PROXY: "1" });
  assert.equal(c.dbPath, ":memory:");
  assert.equal(c.port, 8080);
  assert.equal(c.cookieSecure, false);
  assert.equal(c.trustProxy, 1);
});
