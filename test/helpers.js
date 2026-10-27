/**
 * @module test/helpers
 * Shared test utilities: in-memory server bootstrap, a minimal cookie-jar
 * HTTP client, shared credentials factory, and common progress data fixture.
 */
"use strict";

const { openDb } = require("../server/db");
const { createApp } = require("../server/app");

const SECRET = "test-secret-test-secret-test-secret-123456";

/**
 * Boot a real HTTP server on an ephemeral port backed by an in-memory database.
 *
 * @param {Partial<import('../server/app').AppOptions>} [overrides]
 * @returns {Promise<{ db: import('better-sqlite3').Database, base: string, close: () => Promise<void> }>}
 */
async function startServer(overrides = {}) {
  const db = overrides.db || openDb(":memory:");
  const app = createApp({
    db,
    sessionSecret: SECRET,
    bcryptCost: 4,
    authRateLimit: { windowMs: 60_000, max: 1000 },
    ...overrides,
  });
  const server = await new Promise((resolve) => {
    const s = app.listen(0, "127.0.0.1", () => resolve(s));
  });
  const base = `http://127.0.0.1:${server.address().port}`;
  return {
    db,
    base,
    close: () => new Promise((r) => server.close(() => r())),
  };
}

/**
 * @typedef {object} HttpResponse
 * @property {number} status
 * @property {object|null} body
 * @property {string} text
 * @property {Headers} headers
 * @property {string[]} setCookies
 */

/**
 * @typedef {object} TestClient
 * @property {Map<string, string>} jar - Cookie jar (name → value).
 * @property {(method: string, path: string, body?: unknown, headers?: Record<string,string>) => Promise<HttpResponse>} request
 * @property {(path: string) => Promise<HttpResponse>} get
 * @property {(path: string, body?: unknown) => Promise<HttpResponse>} post
 * @property {(path: string, body: unknown) => Promise<HttpResponse>} put
 */

/**
 * Create a minimal HTTP client with a persistent cookie jar.
 *
 * Each call to `client()` simulates a distinct browser with its own session.
 *
 * @param {string} base - Server base URL (e.g., `"http://127.0.0.1:3001"`).
 * @returns {TestClient}
 */
function client(base) {
  const jar = new Map();

  async function request(method, path, body, extraHeaders = {}) {
    const headers = { ...extraHeaders };
    if (body !== undefined && typeof body !== "string") headers["content-type"] = "application/json";
    if (jar.size) headers.cookie = [...jar].map(([k, v]) => `${k}=${v}`).join("; ");
    const res = await fetch(base + path, {
      method,
      headers,
      redirect: "manual",
      body: body === undefined
        ? undefined
        : (typeof body === "string" ? body : JSON.stringify(body)),
    });
    const setCookies = res.headers.getSetCookie();
    for (const c of setCookies) {
      const [pair] = c.split(";");
      const eq = pair.indexOf("=");
      const name = pair.slice(0, eq);
      const value = pair.slice(eq + 1);
      if (!value) jar.delete(name); else jar.set(name, value);
    }
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch { /* not JSON */ }
    return { status: res.status, body: json, text, headers: res.headers, setCookies };
  }

  return {
    jar,
    request,
    get: (p) => request("GET", p),
    post: (p, b) => request("POST", p, b === undefined ? {} : b),
    put: (p, b) => request("PUT", p, b),
  };
}

/**
 * Build a registration credentials object.
 * @param {string} username
 * @param {string} [password]
 * @returns {{ username: string, password: string }}
 */
const creds = (username, password = "correct-horse-1") => ({ username, password });

/**
 * Return a minimal valid progress data object, merging any provided overrides.
 * @param {object} [overrides]
 * @returns {object}
 */
function sampleData(overrides = {}) {
  return {
    items: {
      "topic-a-task-1": {
        status: "completed",
        notes: "n",
        link: "",
        dueDate: null,
        completedAt: "2026-10-05T10:00:00.000Z",
      },
    },
    counters: { "counter-dsa": 3 },
    celebratedPhases: [],
    settings: { startMonth: "2026-10" },
    custom: { topics: [] },
    ...overrides,
  };
}

module.exports = { startServer, client, creds, sampleData, SECRET };
