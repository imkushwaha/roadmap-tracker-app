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
const { validateUsername, validatePassword } = require("../auth/validators");

const SESSION_DAYS = 7;
const RATE_LIMIT_MESSAGE = {
  error: "Too many attempts. Please wait a few minutes and try again.",
};

/**
 * @typedef {object} AuthRouterOptions
 * @property {import('better-sqlite3').Database} db
 * @property {import('better-sqlite3').Statement} userByIdStmt - Shared prepared statement.
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
  userByIdStmt,
  secret,
  cookieSecure = false,
  bcryptCost = 12,
  rateLimitConfig = { windowMs: 15 * 60 * 1000, max: 10 },
}) {
  const router = express.Router();

  const q = {
    userByName: db.prepare("SELECT id, username, password_hash FROM users WHERE username = ?"),
    insertUser: db.prepare("INSERT INTO users (username, password_hash) VALUES (?, ?)"),
  };

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

  router.post("/register", registerLimiter, async (req, res) => {
    const { username, password } = req.body || {};

    const uCheck = validateUsername(username);
    if (!uCheck.valid) return res.status(400).json({ error: uCheck.error });

    const pCheck = validatePassword(password);
    if (!pCheck.valid) return res.status(400).json({ error: pCheck.error });

    const hash = await hashPassword(password, bcryptCost);
    let id;
    try {
      id = q.insertUser.run(username, hash).lastInsertRowid;
    } catch (e) {
      if (e?.code === "SQLITE_CONSTRAINT_UNIQUE") {
        return res.status(409).json({ error: "That username is already taken." });
      }
      throw e;
    }
    const user = { id: Number(id), username };
    issueSession(res, user);
    res.status(201).json({ user: { username } });
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
    const row = q.userByName.get(username);
    const ok = await verifyPassword(password, row ? row.password_hash : dummyHash);
    if (!row || !ok) return invalid();
    issueSession(res, row);
    res.json({ user: { username: row.username } });
  });

  router.post("/logout", (_req, res) => {
    const { maxAge, ...clearOpts } = opts(); // eslint-disable-line no-unused-vars
    res.clearCookie(COOKIE_NAME, clearOpts);
    res.status(204).end();
  });

  router.get("/me", (req, res) => {
    const user = getCurrentUser(req, userByIdStmt, secret);
    if (!user) return res.status(401).json({ error: "Not authenticated" });
    issueSession(res, user); // rolling session: active users stay logged in
    res.json({ user: { username: user.username } });
  });

  return router;
}

module.exports = { createAuthRouter, SESSION_DAYS };
