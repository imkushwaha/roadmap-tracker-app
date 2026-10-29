/**
 * @module roadmaps/progress
 * Starting progress state for a freshly created roadmap.
 */
"use strict";

/**
 * Build an empty progress blob that passes `validateProgress`.
 * @param {string | null} startMonth - "YYYY-MM" the roadmap's Month 1 starts in, if chosen.
 * @returns {object}
 */
function emptyProgress(startMonth) {
  return {
    items: {},
    counters: {},
    celebratedPhases: [],
    settings: startMonth ? { startMonth } : {},
    custom: { topics: [], phases: [] },
  };
}

module.exports = { emptyProgress };
