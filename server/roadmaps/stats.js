/**
 * @module roadmaps/stats
 * Computes the per-roadmap progress summary shown on the Home screen.
 *
 * The summary is derived from the stored progress JSON, which can be large, so
 * results are cached by roadmap id and saved version. A new save bumps the
 * version, so a cached entry can never be stale with respect to progress; the
 * short TTL only keeps the "done in the last 7 days" figure fresh.
 */
"use strict";

const { buildCurriculum, summarize, EMPTY_CURRICULUM } = require("../../js/roadmap-stats");
const { BUILTIN_AI_ENGINEER } = require("./builtin");

const DEFAULT_TTL_MS = 10 * 60 * 1000;
const DEFAULT_MAX_ENTRIES = 500;

/**
 * @param {object} options
 * @param {object} options.builtinData - parsed data/roadmap.json
 * @param {number} [options.ttlMs]
 * @param {number} [options.maxEntries]
 * @param {() => number} [options.clock] - ms since epoch (injectable for tests)
 */
function createStatsService({
  builtinData, ttlMs = DEFAULT_TTL_MS, maxEntries = DEFAULT_MAX_ENTRIES, clock = Date.now,
}) {
  const curricula = { [BUILTIN_AI_ENGINEER.source]: buildCurriculum(builtinData) };
  /** @type {Map<string, { at: number, stats: object }>} */
  const cache = new Map();

  function curriculumFor(source) {
    return curricula[source] || EMPTY_CURRICULUM;
  }

  function remember(key, stats) {
    if (cache.size >= maxEntries) cache.delete(cache.keys().next().value); // oldest first
    cache.set(key, { at: clock(), stats });
  }

  /**
   * @param {{ id: number, source: string, progressData: string | null, progressVersion: number | null }} row
   * @returns {object | null} the summary, or null if the stored data cannot be read
   */
  function forRoadmap(row) {
    const curriculum = curriculumFor(row.source);
    const now = new Date(clock());
    if (row.progressData == null) return summarize(curriculum, null, { now });

    const key = `${row.id}:${row.progressVersion}`;
    const hit = cache.get(key);
    if (hit && clock() - hit.at < ttlMs) return hit.stats;

    let progress;
    try {
      progress = JSON.parse(row.progressData);
    } catch {
      return null; // corrupt blob: the roadmap still lists, just without numbers
    }
    const stats = summarize(curriculum, progress, { now });
    remember(key, stats);
    return stats;
  }

  return { forRoadmap, cacheSize: () => cache.size };
}

module.exports = { createStatsService };
