/**
 * @module app
 * Express application factory. Composes middleware, auth and data routers,
 * static file serving, and error handling into a configured Express instance.
 *
 * Every concern lives in its own module; this file is intentionally thin.
 */
"use strict";

const path = require("node:path");
const express = require("express");
const helmet = require("helmet");
const cookieParser = require("cookie-parser");
const { PROJECT_ROOT } = require("./config");
const { createAuthRouter } = require("./routes/auth");
const { createDataRouter } = require("./routes/data");
const { COOKIE_NAME, createRequireAuth } = require("./auth/service");

/**
 * @typedef {object} AppOptions
 * @property {import('better-sqlite3').Database} db
 * @property {string} sessionSecret
 * @property {boolean} [cookieSecure] - Set the `Secure` flag on session cookies.
 * @property {boolean|string|number} [trustProxy] - Passed to Express `trust proxy`.
 * @property {number} [bcryptCost] - bcrypt cost factor (default 12).
 * @property {{ windowMs: number, max: number }} [authRateLimit] - Rate limit config.
 * @property {string} [bodyLimit] - Maximum JSON body size (default `"5mb"`).
 * @property {string} [staticRoot] - Directory from which to serve static assets.
 */

/**
 * Create and configure the Express application.
 * @param {AppOptions} options
 * @returns {import('express').Application}
 */
function createApp({
  db,
  sessionSecret,
  cookieSecure = false,
  trustProxy = false,
  bcryptCost = 12,
  authRateLimit = { windowMs: 15 * 60 * 1000, max: 10 },
  bodyLimit = "5mb",
  staticRoot = PROJECT_ROOT,
}) {
  if (!db) throw new Error("createApp: db is required");
  if (!sessionSecret) throw new Error("createApp: sessionSecret is required");

  const app = express();
  app.disable("x-powered-by");
  if (trustProxy) app.set("trust proxy", trustProxy);

  // One shared prepared statement used by both the auth router's /me endpoint
  // and the requireAuth middleware passed to the data router.
  const userByIdStmt = db.prepare("SELECT id, username FROM users WHERE id = ?");
  const requireAuth = createRequireAuth(userByIdStmt, sessionSecret);

  _applyMiddleware(app, bodyLimit);

  app.use("/api/auth", createAuthRouter({
    db,
    userByIdStmt,
    secret: sessionSecret,
    cookieSecure,
    bcryptCost,
    rateLimitConfig: authRateLimit,
  }));

  app.use("/api/data", createDataRouter({ db, requireAuth }));

  app.use("/api", (_req, res) => res.status(404).json({ error: "Not found" }));

  _applyStaticRoutes(app, staticRoot);
  _applyErrorHandler(app);

  return app;
}

/**
 * Apply global security and parsing middleware.
 * @param {import('express').Application} app
 * @param {string} bodyLimit
 */
function _applyMiddleware(app, bodyLimit) {
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        // Suppressed to allow plain-http deployments and localhost dev.
        "upgrade-insecure-requests": null,
      },
    },
  }));
  app.use(cookieParser());
  app.use("/api", (_req, res, next) => { res.set("Cache-Control", "no-store"); next(); });
  app.use("/api", express.json({ limit: bodyLimit }));
}

/**
 * Register static file routes using an explicit allowlist.
 *
 * Never serves the project root wholesale — the database, .env, and server
 * source files live alongside the static assets and must not be reachable.
 *
 * @param {import('express').Application} app
 * @param {string} staticRoot
 */
function _applyStaticRoutes(app, staticRoot) {
  const file = (rel) => (_req, res) => res.sendFile(path.join(staticRoot, rel));
  app.get(["/", "/index.html"], file("index.html"));
  app.get("/data/roadmap.js", file("data/roadmap.js"));
  app.use("/css", express.static(path.join(staticRoot, "css")));
  app.use("/js", express.static(path.join(staticRoot, "js")));
}

/**
 * Register the centralised error-handling middleware.
 * @param {import('express').Application} app
 */
function _applyErrorHandler(app) {
  // eslint-disable-next-line no-unused-vars
  app.use((err, _req, res, _next) => {
    if (err?.type === "entity.too.large") {
      return res.status(413).json({ error: "Request body too large (limit 5 MB)." });
    }
    if (err?.type === "entity.parse.failed") {
      return res.status(400).json({ error: "Invalid JSON body." });
    }
    console.error(err);
    res.status(500).json({ error: "Internal server error" });
  });
}

module.exports = { createApp, COOKIE_NAME };
