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
  `CREATE TABLE IF NOT EXISTS user_data (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    data       TEXT NOT NULL,
    version    INTEGER NOT NULL,
    updated_at TEXT NOT NULL
  )`,
];

// Safe migrations for databases created before first_name/last_name were added.
const MIGRATION_STATEMENTS = [
  `ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL DEFAULT ''`,
  `ALTER TABLE users ADD COLUMN last_name  TEXT NOT NULL DEFAULT ''`,
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
  // Run column additions one-by-one; ignore "duplicate column" errors from existing DBs.
  for (const sql of MIGRATION_STATEMENTS) {
    try {
      await client.execute(sql);
    } catch (e) {
      if (!/duplicate column|already exists/i.test(e?.message ?? "")) throw e;
    }
  }
  return client;
}

module.exports = { openDb };
