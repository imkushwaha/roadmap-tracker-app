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
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
  )`,
  `CREATE TABLE IF NOT EXISTS user_data (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
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
