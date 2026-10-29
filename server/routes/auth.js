/**
 * @module routes/auth
 * Express Router for authentication endpoints: register, login, logout, me.
 * Depends on auth/service for crypto operations and auth/validators for input
 * validation, keeping this module free of library-specific details.
 */
"use strict";

const express = require("express");
const expressRateLimit = require("express-rate-limit");
const {
  COOKIE_NAME,
  hashPassword,
  verifyPassword,
  computeDummyHash,
  signToken,
  getCurrentUser,
  buildCookieOptions,
} = require("../auth/service");
const { validateName, validateUsername, validatePassword } = require("../auth/validators");
const { BUILTIN_AI_ENGINEER } = require("../roadmaps/builtin");

const SESSION_DAYS = 7;
const RATE_LIMIT_MESSAGE = {
  error: "Too many attempts. Please wait a few minutes and try again.",
};

/**
 * Whether *err* is a SQLite unique-constraint violation (local or Turso).
 * @param {unknown} err
 * @returns {boolean}
 */
function isUniqueViolation(err) {
  return (
    err?.code === "SQLITE_CONSTRAINT_UNIQUE" ||
    /UNIQUE constraint failed/i.test(err?.message ?? "")
  );
}

/**
 * @typedef {object} AuthRouterOptions
 * @property {import('@libsql/client').Client} db
 * @property {string} secret - JWT signing secret.
 * @property {boolean} [cookieSecure] - Whether to set the `Secure` cookie flag.
 * @property {number} [bcryptCost] - bcrypt cost factor.
 * @property {{ windowMs: number, max: number }} [rateLimitConfig] - Rate limit settings.
 */

/**
 * Build and return an Express Router for authentication endpoints.
 * @param {AuthRouterOptions} options
 * @returns {import('express').Router}
 */
function createAuthRouter({
  db,
  secret,
  cookieSecure = false,
  bcryptCost = 12,
  rateLimitConfig = { windowMs: 15 * 60 * 1000, max: 10 },
}) {
  const router = express.Router();

  const dummyHash = computeDummyHash(bcryptCost);
  const opts = () => buildCookieOptions(cookieSecure, SESSION_DAYS);

  function issueSession(res, user) {
    res.cookie(COOKIE_NAME, signToken(user, secret, SESSION_DAYS), opts());
  }

  const rateLimitBase = {
    windowMs: rateLimitConfig.windowMs,
    limit: rateLimitConfig.max,
    standardHeaders: "draft-7",
    legacyHeaders: false,
    message: RATE_LIMIT_MESSAGE,
  };

  // Only failed logins count toward the login limit so normal use never locks out.
  const registerLimiter = expressRateLimit({ ...rateLimitBase });
  const loginLimiter = expressRateLimit({ ...rateLimitBase, skipSuccessfulRequests: true });
  const checkUsernameLimiter = expressRateLimit({
    ...rateLimitBase,
    limit: 30,
    message: RATE_LIMIT_MESSAGE,
  });

  router.get("/check-username", checkUsernameLimiter, async (req, res) => {
    const { username } = req.query;
    const uCheck = validateUsername(username);
    if (!uCheck.valid) return res.status(400).json({ error: uCheck.error });
    const found = await db.execute({
      sql: "SELECT 1 FROM users WHERE username = ?",
      args: [username],
    });
    res.json({ available: found.rows.length === 0 });
  });

  router.post("/register", registerLimiter, async (req, res) => {
    const { firstName, lastName, username, password } = req.body || {};

    const fnCheck = validateName(firstName, "First name");
    if (!fnCheck.valid) return res.status(400).json({ error: fnCheck.error });

    const lnCheck = validateName(lastName, "Last name");
    if (!lnCheck.valid) return res.status(400).json({ error: lnCheck.error });

    const uCheck = validateUsername(username);
    if (!uCheck.valid) return res.status(400).json({ error: uCheck.error });

    const pCheck = validatePassword(password);
    if (!pCheck.valid) return res.status(400).json({ error: pCheck.error });

    const hash = await hashPassword(password, bcryptCost);
    const fn = firstName.trim();
    const ln = lastName.trim();
    let id;
    try {
      // One transaction: an account never exists without its starter roadmap.
      const [created] = await db.batch([
        {
          sql: "INSERT INTO users (username, password_hash, first_name, last_name) VALUES (?, ?, ?, ?)",
          args: [username, hash, fn, ln],
        },
        {
          sql: "INSERT INTO roadmaps (user_id, name, description, source) VALUES (last_insert_rowid(), ?, ?, ?)",
          args: [BUILTIN_AI_ENGINEER.name, BUILTIN_AI_ENGINEER.description, BUILTIN_AI_ENGINEER.source],
        },
      ], "write");
      id = created.lastInsertRowid;
    } catch (e) {
      if (isUniqueViolation(e)) {
        return res.status(409).json({ error: "That username is already taken." });
      }
      throw e;
    }
    const user = { id: Number(id), username, firstName: fn, lastName: ln };
    issueSession(res, user);
    res.status(201).json({ user: { username, firstName: fn, lastName: ln } });
  });

  router.post("/login", loginLimiter, async (req, res) => {
    const { username, password } = req.body || {};
    const invalid = () => res.status(401).json({ error: "Invalid credentials" });
    if (
      typeof username !== "string" || typeof password !== "string" ||
      !username || !password ||
      username.length > 64 || Buffer.byteLength(password, "utf8") > 256
    ) {
      return invalid();
    }
    const found = await db.execute({
      sql: "SELECT id, username, password_hash, first_name, last_name FROM users WHERE username = ?",
      args: [username],
    });
    const row = found.rows[0];
    const ok = await verifyPassword(password, row ? row.password_hash : dummyHash);
    if (!row || !ok) return invalid();
    const u = {
      id: Number(row.id),
      username: String(row.username),
      firstName: String(row.first_name || ""),
      lastName: String(row.last_name || ""),
    };
    issueSession(res, u);
    res.json({ user: { username: u.username, firstName: u.firstName, lastName: u.lastName } });
  });

  router.post("/logout", (_req, res) => {
    const { maxAge, ...clearOpts } = opts(); // eslint-disable-line no-unused-vars
    res.clearCookie(COOKIE_NAME, clearOpts);
    res.status(204).end();
  });

  router.get("/me", async (req, res) => {
    const user = await getCurrentUser(req, db, secret);
    if (!user) return res.status(401).json({ error: "Not authenticated" });
    issueSession(res, user); // rolling session: active users stay logged in
    res.json({ user: { username: user.username, firstName: user.firstName, lastName: user.lastName } });
  });

  return router;
}

module.exports = { createAuthRouter, SESSION_DAYS };
