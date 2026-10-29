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
  const c = loadConfig({ NODE_ENV: "production", SESSION_SECRET: "x".repeat(40), TURSO_DATABASE_URL: "file:./x.db" });
  assert.equal(c.cookieSecure, true);
  assert.equal(c.port, 3000);
});
test("production refuses to start without TURSO_DATABASE_URL", () => {
  assert.throws(
    () => loadConfig({ NODE_ENV: "production", SESSION_SECRET: "x".repeat(40) }),
    /TURSO_DATABASE_URL is required/
  );
});
test("production refuses a remote Turso URL without an auth token", () => {
  assert.throws(
    () => loadConfig({ NODE_ENV: "production", SESSION_SECRET: "x".repeat(40), TURSO_DATABASE_URL: "libsql://db.turso.io" }),
    /TURSO_AUTH_TOKEN is required/
  );
});
test("development defaults to a local SQLite file", () => {
  const warn = console.warn; console.warn = () => {};
  try {
    assert.match(loadConfig({}).dbUrl, /^file:.*data[\\/]app\.db$/);
  } finally { console.warn = warn; }
});
test("development falls back to an ephemeral secret and non-secure cookies", () => {
  const warn = console.warn; console.warn = () => {};
  try {
    const c = loadConfig({});
    assert.ok(c.sessionSecret.length >= 32);
    assert.equal(c.cookieSecure, false);
  } finally { console.warn = warn; }
});
test("TURSO_*, PORT, COOKIE_SECURE and TRUST_PROXY are honoured", () => {
  const c = loadConfig({ NODE_ENV: "production", SESSION_SECRET: "x".repeat(40), TURSO_DATABASE_URL: "libsql://db.turso.io", TURSO_AUTH_TOKEN: "tok", PORT: "8080", COOKIE_SECURE: "false", TRUST_PROXY: "1" });
  assert.equal(c.dbUrl, "libsql://db.turso.io");
  assert.equal(c.dbAuthToken, "tok");
  assert.equal(c.port, 8080);
  assert.equal(c.cookieSecure, false);
  assert.equal(c.trustProxy, 1);
});
