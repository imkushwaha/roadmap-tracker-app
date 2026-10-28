/**
 * @module routes/data
 * Express Router for user progress data endpoints: GET and PUT /api/data.
 * Uses optimistic concurrency (compare-and-swap on `version`) via single
 * atomic statements to prevent lost updates across devices.
 */
"use strict";

const express = require("express");
const { validateProgress } = require("../../js/progress-schema");

/**
 * @typedef {object} DataRouterOptions
 * @property {import('@libsql/client').Client} db
 * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 */

/**
 * Build and return an Express Router for user-data endpoints.
 * @param {DataRouterOptions} options
 * @returns {import('express').Router}
 */
function createDataRouter({ db, requireAuth }) {
  const router = express.Router();

  async function getRow(userId) {
    const result = await db.execute({
      sql: "SELECT data, version, updated_at FROM user_data WHERE user_id = ?",
      args: [userId],
    });
    const row = result.rows[0];
    return row
      ? { data: String(row.data), version: Number(row.version), updated_at: String(row.updated_at) }
      : undefined;
  }

  // Compare-and-swap in a single atomic statement: the write only lands if the
  // stored version still equals the client's. Version 0 means "no row yet".
  async function saveData(userId, dataText, clientVersion) {
    const now = new Date().toISOString();
    const result = clientVersion === 0
      ? await db.execute({
          sql: `INSERT INTO user_data (user_id, data, version, updated_at) VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id) DO NOTHING`,
          args: [userId, dataText, now],
        })
      : await db.execute({
          sql: `UPDATE user_data SET data = ?, version = version + 1, updated_at = ?
                WHERE user_id = ? AND version = ?`,
          args: [dataText, now, userId, clientVersion],
        });
    if (result.rowsAffected === 1) {
      return { conflict: false, version: clientVersion + 1, updatedAt: now };
    }
    return { conflict: true, row: await getRow(userId) };
  }

  router.get("/", requireAuth, async (req, res) => {
    const row = await getRow(req.user.id);
    if (!row) return res.json({ data: null, version: 0 });
    res.json({
      data: JSON.parse(row.data),
      version: row.version,
      updatedAt: row.updated_at,
    });
  });

  router.put("/", requireAuth, async (req, res) => {
    const { data, version } = req.body || {};
    if (!Number.isInteger(version) || version < 0) {
      return res.status(400).json({ error: '"version" must be a non-negative integer.' });
    }
    const check = validateProgress(data);
    if (!check.ok) {
      return res.status(400).json({
        error: "Data doesn't match the progress schema.",
        details: check.errors,
      });
    }
    const result = await saveData(req.user.id, JSON.stringify(data), version);
    if (result.conflict) {
      const server = result.row
        ? {
            data: JSON.parse(result.row.data),
            version: result.row.version,
            updatedAt: result.row.updated_at,
          }
        : { data: null, version: 0 };
      return res.status(409).json({ error: "Version conflict", server });
    }
    res.json({ version: result.version, updatedAt: result.updatedAt });
  });

  return router;
}

module.exports = { createDataRouter };
