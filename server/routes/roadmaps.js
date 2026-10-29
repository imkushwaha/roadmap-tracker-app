/**
 * @module routes/roadmaps
 * Express Router for the user's roadmaps: list, restore the built-in one,
 * delete, and read/write each roadmap's progress. Every query is scoped to the
 * authenticated user, so one account can never reach another's roadmap.
 *
 * Progress saves use optimistic concurrency (compare-and-swap on `version`)
 * via single atomic statements to prevent lost updates across devices.
 */
"use strict";

const express = require("express");
const { validateProgress } = require("../../js/progress-schema");
const { BUILTIN_AI_ENGINEER } = require("../roadmaps/builtin");

/**
 * @typedef {object} RoadmapsRouterOptions
 * @property {import('@libsql/client').Client} db
 * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 */

/**
 * Shape a `roadmaps` row for API responses.
 * @param {Record<string, unknown>} row
 * @returns {{ id: number, name: string, description: string, source: string, createdAt: string }}
 */
function toRoadmap(row) {
  return {
    id: Number(row.id),
    name: String(row.name),
    description: String(row.description),
    source: String(row.source),
    createdAt: String(row.created_at),
  };
}

/**
 * Parse a `:id` route param into a positive integer, or `null`.
 * @param {string} raw
 * @returns {number | null}
 */
function parseId(raw) {
  return /^\d+$/.test(raw) ? Number(raw) : null;
}

/**
 * Build and return an Express Router for roadmap endpoints.
 * @param {RoadmapsRouterOptions} options
 * @returns {import('express').Router}
 */
function createRoadmapsRouter({ db, requireAuth }) {
  const router = express.Router();
  router.use(requireAuth);

  async function findOwned(userId, roadmapId) {
    const result = await db.execute({
      sql: "SELECT id, name, description, source, created_at FROM roadmaps WHERE id = ? AND user_id = ?",
      args: [roadmapId, userId],
    });
    return result.rows[0];
  }

  async function getProgressRow(roadmapId) {
    const result = await db.execute({
      sql: "SELECT data, version, updated_at FROM roadmap_progress WHERE roadmap_id = ?",
      args: [roadmapId],
    });
    const row = result.rows[0];
    return row
      ? { data: String(row.data), version: Number(row.version), updated_at: String(row.updated_at) }
      : undefined;
  }

  // Compare-and-swap in a single atomic statement: the write only lands if the
  // stored version still equals the client's. Version 0 means "no row yet".
  async function saveProgress(roadmapId, dataText, clientVersion) {
    const now = new Date().toISOString();
    const result = clientVersion === 0
      ? await db.execute({
          sql: `INSERT INTO roadmap_progress (roadmap_id, data, version, updated_at) VALUES (?, ?, 1, ?)
                ON CONFLICT(roadmap_id) DO NOTHING`,
          args: [roadmapId, dataText, now],
        })
      : await db.execute({
          sql: `UPDATE roadmap_progress SET data = ?, version = version + 1, updated_at = ?
                WHERE roadmap_id = ? AND version = ?`,
          args: [dataText, now, roadmapId, clientVersion],
        });
    if (result.rowsAffected === 1) {
      return { conflict: false, version: clientVersion + 1, updatedAt: now };
    }
    return { conflict: true, row: await getProgressRow(roadmapId) };
  }

  router.get("/", async (req, res) => {
    const result = await db.execute({
      sql: `SELECT r.id, r.name, r.description, r.source, r.created_at, p.updated_at AS last_activity_at
            FROM roadmaps r LEFT JOIN roadmap_progress p ON p.roadmap_id = r.id
            WHERE r.user_id = ?
            ORDER BY r.created_at, r.id`,
      args: [req.user.id],
    });
    res.json({
      roadmaps: result.rows.map((row) => ({
        ...toRoadmap(row),
        lastActivityAt: row.last_activity_at == null ? null : String(row.last_activity_at),
      })),
    });
  });

  // Only restoring the built-in roadmap is supported until custom creation lands.
  router.post("/", async (req, res) => {
    const { source } = req.body || {};
    if (source !== BUILTIN_AI_ENGINEER.source) {
      return res.status(400).json({ error: "Only the AI Engineer roadmap can be created right now." });
    }
    const existing = await db.execute({
      sql: "SELECT 1 FROM roadmaps WHERE user_id = ? AND source = ?",
      args: [req.user.id, source],
    });
    if (existing.rows.length > 0) {
      return res.status(409).json({ error: "You already have this roadmap." });
    }
    const inserted = await db.execute({
      sql: "INSERT INTO roadmaps (user_id, name, description, source) VALUES (?, ?, ?, ?)",
      args: [req.user.id, BUILTIN_AI_ENGINEER.name, BUILTIN_AI_ENGINEER.description, source],
    });
    const row = await findOwned(req.user.id, Number(inserted.lastInsertRowid));
    res.status(201).json({ roadmap: toRoadmap(row) });
  });

  router.delete("/:id", async (req, res) => {
    const id = parseId(req.params.id);
    const result = id === null
      ? { rowsAffected: 0 }
      : await db.execute({
          sql: "DELETE FROM roadmaps WHERE id = ? AND user_id = ?",
          args: [id, req.user.id],
        });
    if (result.rowsAffected === 0) return res.status(404).json({ error: "Roadmap not found" });
    res.status(204).end();
  });

  router.get("/:id/progress", async (req, res) => {
    const id = parseId(req.params.id);
    const roadmap = id === null ? undefined : await findOwned(req.user.id, id);
    if (!roadmap) return res.status(404).json({ error: "Roadmap not found" });

    const row = await getProgressRow(id);
    if (!row) return res.json({ roadmap: toRoadmap(roadmap), data: null, version: 0 });
    res.json({
      roadmap: toRoadmap(roadmap),
      data: JSON.parse(row.data),
      version: row.version,
      updatedAt: row.updated_at,
    });
  });

  router.put("/:id/progress", async (req, res) => {
    const id = parseId(req.params.id);
    const roadmap = id === null ? undefined : await findOwned(req.user.id, id);
    if (!roadmap) return res.status(404).json({ error: "Roadmap not found" });

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
    const result = await saveProgress(id, JSON.stringify(data), version);
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

module.exports = { createRoadmapsRouter };
