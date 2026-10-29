/**
 * @module roadmaps/builtin
 * Identity of the built-in roadmap every account starts with. Its content is
 * the static `data/roadmap.js` bundle, so only metadata is stored per user.
 */
"use strict";

const BUILTIN_AI_ENGINEER = Object.freeze({
  source: "builtin_ai_engineer",
  name: "AI Engineer Roadmap",
  description: "Tier-1 Production AI Engineer — 10-Month Execution Tracker",
});

module.exports = { BUILTIN_AI_ENGINEER };
