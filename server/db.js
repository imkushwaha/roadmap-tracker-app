/**
 * @module db
 * SQLite database initialisation. Opens (or creates) the database, applies
 * the schema, and returns a ready-to-use connection.
 */
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const Database = require("better-sqlite3");

const SCHEMA_SQL = `
  CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
  );
  CREATE TABLE IF NOT EXISTS user_data (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    data       TEXT NOT NULL,
    version    INTEGER NOT NULL,
    updated_at TEXT NOT NULL
  );
`;

/**
 * Open (or create) the SQLite database at *dbPath* and apply the schema.
 *
 * Uses WAL journal mode and enforces foreign-key constraints. Creates the
 * parent directory automatically for file-backed databases.
 *
 * @param {string} dbPath - Absolute file path, or `":memory:"` for an in-memory database.
 * @returns {import('better-sqlite3').Database}
 */
function openDb(dbPath) {
  if (dbPath !== ":memory:") fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.exec(SCHEMA_SQL);
  return db;
}

module.exports = { openDb };
