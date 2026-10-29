/**
 * @module auth/service
 * Pure authentication helpers — no Express dependency.
 * Wraps bcrypt and jsonwebtoken so route handlers are decoupled from
 * concrete library implementations.
 */
"use strict";

const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");

const COOKIE_NAME = "rd_session";

/**
 * Hash a plain-text password using bcrypt.
 * @param {string} password
 * @param {number} cost - bcrypt cost factor.
 * @returns {Promise<string>}
 */
async function hashPassword(password, cost) {
  return bcrypt.hash(password, cost);
}

/**
 * Verify a plain-text password against a stored bcrypt hash.
 * @param {string} password
 * @param {string} hash
 * @returns {Promise<boolean>}
 */
async function verifyPassword(password, hash) {
  return bcrypt.compare(password, hash);
}

/**
 * Pre-compute a dummy hash for constant-time comparison when a username
 * does not exist, preventing timing-based user enumeration.
 * @param {number} cost - bcrypt cost factor.
 * @returns {string}
 */
function computeDummyHash(cost) {
  return bcrypt.hashSync("not-a-real-password", cost);
}

/**
 * Sign a session JWT for *user*.
 * @param {{ id: number, username: string }} user
 * @param {string} secret
 * @param {number} sessionDays
 * @returns {string}
 */
function signToken(user, secret, sessionDays) {
  return jwt.sign({ un: user.username }, secret, {
    algorithm: "HS256",
    subject: String(user.id),
    expiresIn: `${sessionDays}d`,
  });
}

/**
 * Verify and decode a session JWT. Returns `null` on any verification failure.
 * @param {string} token
 * @param {string} secret
 * @returns {{ sub: string, un: string } | null}
 */
function verifyToken(token, secret) {
  try {
    return jwt.verify(token, secret, { algorithms: ["HS256"] });
  } catch {
    return null;
  }
}

/**
 * Build a session cookie options object.
 * @param {boolean} secure - Whether to set the `Secure` flag.
 * @param {number} sessionDays
 * @returns {import('express').CookieOptions}
 */
function buildCookieOptions(secure, sessionDays) {
  return {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
    maxAge: sessionDays * 24 * 60 * 60 * 1000,
  };
}

/**
 * Extract the authenticated user from the session cookie, or return null.
 * @param {import('express').Request} req
 * @param {import('@libsql/client').Client} db
 * @param {string} secret
 * @returns {Promise<{ id: number, username: string } | null>}
 */
async function getCurrentUser(req, db, secret) {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) return null;
  const payload = verifyToken(token, secret);
  if (!payload) return null;
  const result = await db.execute({
    sql: "SELECT id, username, first_name, last_name FROM users WHERE id = ?",
    args: [Number(payload.sub)],
  });
  const row = result.rows[0];
  return row
    ? {
        id: Number(row.id),
        username: String(row.username),
        firstName: String(row.first_name || ""),
        lastName: String(row.last_name || ""),
      }
    : null;
}

/**
 * Create an Express middleware that resolves the session user and sets
 * `req.user`, or sends a 401 response when no valid session exists.
 * @param {import('@libsql/client').Client} db
 * @param {string} secret
 * @returns {import('express').RequestHandler}
 */
function createRequireAuth(db, secret) {
  return async function requireAuth(req, res, next) {
    try {
      const user = await getCurrentUser(req, db, secret);
      if (!user) return res.status(401).json({ error: "Not authenticated" });
      req.user = user;
      next();
    } catch (err) {
      next(err);
    }
  };
}

module.exports = {
  COOKIE_NAME,
  hashPassword,
  verifyPassword,
  computeDummyHash,
  signToken,
  verifyToken,
  buildCookieOptions,
  getCurrentUser,
  createRequireAuth,
};
