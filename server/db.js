/**
 * @module db
 * Database initialisation. Connects to Turso (hosted libSQL), or to a local
 * libSQL/SQLite target (`:memory:` or `file:` URL) for development and tests,
 * and applies the schema.
 */
"use strict";

const { createClient } = require("@libsql/client");
const { BUILTIN_AI_ENGINEER } = require("./roadmaps/builtin");

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

// Safe migrations for databases created before first_name/last_name were added.
const MIGRATION_STATEMENTS = [
  `ALTER TABLE users ADD COLUMN first_name TEXT NOT NULL DEFAULT ''`,
  `ALTER TABLE users ADD COLUMN last_name  TEXT NOT NULL DEFAULT ''`,
];

/**
 * One-time move from the single-roadmap `user_data` table to per-roadmap
 * storage: every account gets the built-in roadmap row and its saved progress
 * is copied across. The old table is renamed (not dropped) so nothing is lost,
 * and its absence on later boots makes this a no-op. Runs as one transaction.
 *
 * @param {import('@libsql/client').Client} client
 * @returns {Promise<void>}
 */
async function migrateLegacyUserData(client) {
  const legacy = await client.execute(
    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user_data'"
  );
  if (legacy.rows.length === 0) return;

  const { source, name, description } = BUILTIN_AI_ENGINEER;
  await client.batch([
    {
      sql: `INSERT INTO roadmaps (user_id, name, description, source)
            SELECT u.id, ?, ?, ? FROM users u
            WHERE NOT EXISTS (SELECT 1 FROM roadmaps r WHERE r.user_id = u.id)`,
      args: [name, description, source],
    },
    {
      sql: `INSERT INTO roadmap_progress (roadmap_id, data, version, updated_at)
            SELECT r.id, ud.data, ud.version, ud.updated_at
            FROM roadmaps r JOIN user_data ud ON ud.user_id = r.user_id
            WHERE r.source = ?`,
      args: [source],
    },
    "ALTER TABLE user_data RENAME TO user_data_legacy",
  ], "write");
}

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
  await migrateLegacyUserData(client);
  return client;
}

module.exports = { openDb };
