/**
 * @module index
 * Application entry point. Loads configuration, opens the database, starts
 * the HTTP server, and registers graceful-shutdown handlers.
 */
"use strict";

require("dotenv").config();
const { loadConfig } = require("./config");
const { openDb } = require("./db");
const { createApp } = require("./app");

const cfg = loadConfig(process.env);
const db = openDb(cfg.dbPath);
const app = createApp({
  db,
  sessionSecret: cfg.sessionSecret,
  cookieSecure: cfg.cookieSecure,
  trustProxy: cfg.trustProxy,
});

const server = app.listen(cfg.port, () => {
  const mode = cfg.isProduction ? "production" : "development";
  console.log(
    `Roadmap dashboard on http://localhost:${cfg.port}  (db: ${cfg.dbPath}, ${mode})`
  );
});

attachShutdownHandlers(server, db);

/**
 * Register SIGINT and SIGTERM handlers that gracefully stop the HTTP server
 * and close the database connection before exiting.
 * @param {import('http').Server} server
 * @param {import('better-sqlite3').Database} db
 * @returns {void}
 */
function attachShutdownHandlers(server, db) {
  function shutdown() {
    server.close(() => { db.close(); process.exit(0); });
  }
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}
