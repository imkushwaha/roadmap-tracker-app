/**
 * @module routes/data
 * Express Router for user progress data endpoints: GET and PUT /api/data.
 * Uses optimistic concurrency (compare-and-swap on `version`) inside a single
 * immediate SQLite transaction to prevent lost updates across devices.
 */
"use strict";

const express = require("express");
const { validateProgress } = require("../../js/progress-schema");

/**
 * @typedef {object} DataRouterOptions
 * @property {import('better-sqlite3').Database} db
 * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 */

/**
 * Build and return an Express Router for user-data endpoints.
 * @param {DataRouterOptions} options
 * @returns {import('express').Router}
 */
function createDataRouter({ db, requireAuth }) {
  const router = express.Router();

  const q = {
    getData: db.prepare("SELECT data, version, updated_at FROM user_data WHERE user_id = ?"),
    insertData: db.prepare(
      "INSERT INTO user_data (user_id, data, version, updated_at) VALUES (?, ?, 1, ?)"
    ),
    updateData: db.prepare(
      "UPDATE user_data SET data = ?, version = version + 1, updated_at = ? WHERE user_id = ?"
    ),
  };

  // Compare-and-swap: read current version and write atomically in one transaction.
  const saveData = db.transaction((userId, dataText, clientVersion) => {
    const row = q.getData.get(userId);
    const serverVersion = row ? row.version : 0;
    if (serverVersion !== clientVersion) return { conflict: true, row };
    const now = new Date().toISOString();
    if (row) q.updateData.run(dataText, now, userId);
    else q.insertData.run(userId, dataText, now);
    return { conflict: false, version: serverVersion + 1, updatedAt: now };
  });

  router.get("/", requireAuth, (req, res) => {
    const row = q.getData.get(req.user.id);
    if (!row) return res.json({ data: null, version: 0 });
    res.json({
      data: JSON.parse(row.data),
      version: row.version,
      updatedAt: row.updated_at,
    });
  });

  router.put("/", requireAuth, (req, res) => {
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
    const result = saveData.immediate(req.user.id, JSON.stringify(data), version);
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
