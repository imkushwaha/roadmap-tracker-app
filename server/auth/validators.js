/**
 * @module auth/validators
 * Input validation helpers for authentication endpoints.
 * All validators return a discriminated union so callers can act on the error
 * message without inspecting exception types.
 */
"use strict";

const USERNAME_RE = /^[A-Za-z0-9_-]{3,32}$/;
const NAME_RE = /^[A-Za-zÀ-ÿ' -]{1,64}$/;
const MIN_PASSWORD = 8;
/** bcrypt silently ignores anything past 72 bytes. */
const MAX_PASSWORD_BYTES = 72;

/**
 * @typedef {{ valid: true } | { valid: false, error: string }} ValidationResult
 */

/**
 * Validate a first or last name.
 * @param {unknown} value
 * @param {string} field - Display label used in the error message.
 * @returns {ValidationResult}
 */
function validateName(value, field) {
  if (typeof value !== "string" || !NAME_RE.test(value.trim())) {
    return { valid: false, error: `${field} must be 1–64 letters.` };
  }
  return { valid: true };
}

/**
 * Validate a registration username against the allowed character set and length.
 * @param {unknown} username
 * @returns {ValidationResult}
 */
function validateUsername(username) {
  if (typeof username !== "string" || !USERNAME_RE.test(username)) {
    return { valid: false, error: "Username must be 3-32 characters: letters, numbers, _ or -." };
  }
  return { valid: true };
}

/**
 * Validate a registration password against minimum length and maximum byte size.
 * @param {unknown} password
 * @returns {ValidationResult}
 */
function validatePassword(password) {
  if (typeof password !== "string" || password.length < MIN_PASSWORD) {
    return { valid: false, error: `Password must be at least ${MIN_PASSWORD} characters.` };
  }
  if (Buffer.byteLength(password, "utf8") > MAX_PASSWORD_BYTES) {
    return { valid: false, error: `Password must be at most ${MAX_PASSWORD_BYTES} bytes.` };
  }
  return { valid: true };
}

module.exports = { validateName, validateUsername, validatePassword, MIN_PASSWORD, MAX_PASSWORD_BYTES };
