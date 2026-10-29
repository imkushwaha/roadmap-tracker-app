/**
 * @module db
 * Database initialisation. Connects to Turso (hosted libSQL), or to a local
 * libSQL/SQLite target (`:memory:` or `file:` URL) for development and tests,
 * and applies the schema.
 */
"use strict";

const { createClient } = require("@libsql/client");

const SCHEMA_STATEMENTS = [
  `CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    first_name    TEXT NOT NULL DEFAULT '',
    last_name     TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
  )`,
  `CREATE TABLE IF NOT EXISTS roadmaps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
  )`,
  `CREATE INDEX IF NOT EXISTS idx_roadmaps_user ON roadmaps(user_id)`,
  `CREATE TABLE IF NOT EXISTS roadmap_progress (
    roadmap_id INTEGER PRIMARY KEY REFERENCES roadmaps(id) ON DELETE CASCADE,
    data       TEXT NOT NULL,
    version    INTEGER NOT NULL,
    updated_at TEXT NOT NULL
  )`,
];

/**
 * Connect to the database at *url* and apply the schema.
 *
 * @param {string} url - `libsql://…` (Turso), `file:…`, or `":memory:"`.
 * @param {string} [authToken] - Turso auth token; not needed for local targets.
 * @returns {Promise<import('@libsql/client').Client>}
 */
async function openDb(url, authToken) {
  const client = createClient({ url, authToken: authToken || undefined });
  await client.batch(SCHEMA_STATEMENTS, "write");
  return client;
}

module.exports = { openDb };
