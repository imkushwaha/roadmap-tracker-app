/**
 * @module routes/roadmaps
 * Express Router for the user's roadmaps: list, create (custom or restore the
 * built-in one), delete, and read/write each roadmap's progress. HTTP concerns
 * only — SQL lives in roadmaps/repository, input rules in roadmaps/validators.
 *
 * Progress saves use optimistic concurrency (compare-and-swap on `version`),
 * implemented atomically in the repository, to prevent lost updates across
 * devices.
 */
"use strict";

const express = require("express");
const { validateProgress } = require("../../js/progress-schema");
const { BUILTIN_AI_ENGINEER } = require("../roadmaps/builtin");
const { createRoadmapRepository } = require("../roadmaps/repository");
const { emptyProgress } = require("../roadmaps/progress");
const {
  CUSTOM_SOURCE,
  MAX_ROADMAPS_PER_USER,
  validateRoadmapInput,
} = require("../roadmaps/validators");

/**
 * @typedef {object} RoadmapsRouterOptions
 * @property {import('@libsql/client').Client} db
 * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 */

/**
 * Parse a `:id` route param into a non-negative integer, or `null`.
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
  const repo = createRoadmapRepository(db);
  router.use(requireAuth);

  async function findOwnedFromParams(req) {
    const id = parseId(req.params.id);
    return id === null ? undefined : repo.findOwned(req.user.id, id);
  }

  async function restoreBuiltin(req, res) {
    if (await repo.hasSource(req.user.id, BUILTIN_AI_ENGINEER.source)) {
      return res.status(409).json({ error: "You already have this roadmap." });
    }
    const id = await repo.insert(req.user.id, BUILTIN_AI_ENGINEER);
    res.status(201).json({ roadmap: await repo.findOwned(req.user.id, id) });
  }

  async function createCustom(req, res) {
    const input = validateRoadmapInput(req.body);
    if (!input.valid) return res.status(400).json({ error: input.error });
    if (await repo.countForUser(req.user.id) >= MAX_ROADMAPS_PER_USER) {
      return res.status(409).json({ error: `You can have at most ${MAX_ROADMAPS_PER_USER} roadmaps.` });
    }
    const { name, description, startMonth } = input.value;
    const progress = startMonth ? emptyProgress(startMonth) : null;
    const id = await repo.insert(req.user.id, { name, description, source: CUSTOM_SOURCE }, progress);
    res.status(201).json({ roadmap: await repo.findOwned(req.user.id, id) });
  }

  router.get("/", async (req, res) => {
    res.json({ roadmaps: await repo.listForUser(req.user.id) });
  });

  router.post("/", async (req, res) => {
    const source = req.body?.source;
    if (source === BUILTIN_AI_ENGINEER.source) return restoreBuiltin(req, res);
    if (source !== undefined && source !== CUSTOM_SOURCE) {
      return res.status(400).json({ error: "Unknown roadmap source." });
    }
    return createCustom(req, res);
  });

  router.delete("/:id", async (req, res) => {
    const id = parseId(req.params.id);
    const removed = id !== null && await repo.remove(req.user.id, id);
    if (!removed) return res.status(404).json({ error: "Roadmap not found" });
    res.status(204).end();
  });

  router.get("/:id/progress", async (req, res) => {
    const roadmap = await findOwnedFromParams(req);
    if (!roadmap) return res.status(404).json({ error: "Roadmap not found" });

    const row = await repo.getProgress(roadmap.id);
    if (!row) return res.json({ roadmap, data: null, version: 0 });
    res.json({
      roadmap,
      data: JSON.parse(row.data),
      version: row.version,
      updatedAt: row.updated_at,
    });
  });

  router.put("/:id/progress", async (req, res) => {
    const roadmap = await findOwnedFromParams(req);
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
    const result = await repo.saveProgress(roadmap.id, JSON.stringify(data), version);
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
