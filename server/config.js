/**
 * @module config
 * Application configuration loader. Validates and normalises environment
 * variables into a typed configuration object. Throws on invalid production
 * config rather than silently starting with unsafe defaults.
 */
"use strict";

const crypto = require("node:crypto");
const path = require("node:path");

const PROJECT_ROOT = path.resolve(__dirname, "..");

/**
 * @typedef {object} AppConfig
 * @property {boolean} isProduction
 * @property {string} sessionSecret
 * @property {string} dbUrl - `libsql://…`, `file:…` or `:memory:`.
 * @property {string} dbAuthToken - Turso auth token (empty for local targets).
 * @property {number} port
 * @property {boolean} cookieSecure
 * @property {boolean|string|number} trustProxy
 */

/**
 * Load and validate application configuration from environment variables.
 *
 * Throws when `SESSION_SECRET` is absent or too short in production.
 *
 * @param {NodeJS.ProcessEnv} [env] - Defaults to `process.env`.
 * @returns {AppConfig}
 */
function loadConfig(env = process.env) {
  const isProduction = env.NODE_ENV === "production";
  return {
    isProduction,
    sessionSecret: _resolveSessionSecret(env, isProduction),
    dbUrl: _resolveDbUrl(env, isProduction),
    dbAuthToken: env.TURSO_AUTH_TOKEN || "",
    port: Number(env.PORT) || 3000,
    cookieSecure: _resolveCookieSecure(env, isProduction),
    trustProxy: _parseTrustProxy(env.TRUST_PROXY),
  };
}

/**
 * Resolve the session secret. Generates a random ephemeral one in development
 * when the env var is absent; throws in production.
 * @param {NodeJS.ProcessEnv} env
 * @param {boolean} isProduction
 * @returns {string}
 */
function _resolveSessionSecret(env, isProduction) {
  const secret = env.SESSION_SECRET;
  if (!secret) {
    if (isProduction) {
      throw new Error(
        "SESSION_SECRET is required when NODE_ENV=production (see .env.example)."
      );
    }
    // Dev convenience: sessions don't survive a restart.
    console.warn("[config] SESSION_SECRET not set — using a random one; logins reset on restart.");
    return crypto.randomBytes(32).toString("hex");
  }
  if (isProduction && secret.length < 32) {
    throw new Error("SESSION_SECRET must be at least 32 characters in production.");
  }
  return secret;
}

/**
 * Resolve the database URL. Production requires `TURSO_DATABASE_URL` (and a
 * token for remote `libsql://` URLs). In development it defaults to a local
 * SQLite file at `./data/app.db` so `npm run dev` works without Turso.
 * @param {NodeJS.ProcessEnv} env
 * @param {boolean} isProduction
 * @returns {string}
 */
function _resolveDbUrl(env, isProduction) {
  const url = env.TURSO_DATABASE_URL;
  if (!url) {
    if (isProduction) {
      throw new Error("TURSO_DATABASE_URL is required when NODE_ENV=production (see .env.example).");
    }
    return "file:" + path.resolve(PROJECT_ROOT, "data", "app.db");
  }
  if (isProduction && /^(libsql|wss?|https?):/.test(url) && !env.TURSO_AUTH_TOKEN) {
    throw new Error("TURSO_AUTH_TOKEN is required for a remote TURSO_DATABASE_URL.");
  }
  return url;
}

/**
 * Resolve whether session cookies carry the `Secure` flag.
 * Defaults to `true` in production; can be overridden with `COOKIE_SECURE=false`
 * for plain-HTTP production setups (e.g. a LAN box behind a hardware proxy).
 * @param {NodeJS.ProcessEnv} env
 * @param {boolean} isProduction
 * @returns {boolean}
 */
function _resolveCookieSecure(env, isProduction) {
  return env.COOKIE_SECURE ? env.COOKIE_SECURE !== "false" : isProduction;
}

/**
 * Parse the `TRUST_PROXY` environment variable into the value Express expects.
 *
 * A numeric string (e.g. `"1"`) becomes a number; any other non-empty string
 * is passed through as-is; absent or empty resolves to `false`.
 *
 * @param {string | undefined} raw
 * @returns {boolean | string | number}
 */
function _parseTrustProxy(raw) {
  if (!raw) return false;
  return /^\d+$/.test(raw) ? Number(raw) : raw;
}

module.exports = { loadConfig, PROJECT_ROOT };
