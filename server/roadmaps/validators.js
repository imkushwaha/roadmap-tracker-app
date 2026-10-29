/**
 * @module roadmaps/validators
 * Input validation and policy limits for creating roadmaps. Validators return
 * a discriminated union so callers can respond without inspecting exceptions.
 */
"use strict";

const CUSTOM_SOURCE = "custom";
const NAME_MAX = 80;
const DESCRIPTION_MAX = 300;
const MAX_ROADMAPS_PER_USER = 20;

const START_MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;
// eslint-disable-next-line no-control-regex
const CONTROL_CHARS_RE = /[\u0000-\u001f\u007f]/;

/**
 * @typedef {{ name: string, description: string, startMonth: string | null }} RoadmapInput
 * @typedef {{ valid: true, value: RoadmapInput } | { valid: false, error: string }} RoadmapInputResult
 */

/**
 * Validate and normalise the body of a "create custom roadmap" request.
 * @param {unknown} body
 * @returns {RoadmapInputResult}
 */
function validateRoadmapInput(body) {
  const { name, description, startMonth } = body && typeof body === "object" ? body : {};

  if (typeof name !== "string" || !name.trim()) {
    return { valid: false, error: "Roadmap name is required." };
  }
  const cleanName = name.trim();
  if (cleanName.length > NAME_MAX || CONTROL_CHARS_RE.test(cleanName)) {
    return { valid: false, error: `Roadmap name must be 1–${NAME_MAX} characters on a single line.` };
  }

  if (description !== undefined && typeof description !== "string") {
    return { valid: false, error: "Description must be text." };
  }
  const cleanDescription = (description || "").trim();
  if (cleanDescription.length > DESCRIPTION_MAX) {
    return { valid: false, error: `Description must be at most ${DESCRIPTION_MAX} characters.` };
  }

  if (startMonth !== undefined && startMonth !== null &&
      !(typeof startMonth === "string" && START_MONTH_RE.test(startMonth))) {
    return { valid: false, error: 'Start month must look like "YYYY-MM".' };
  }

  return {
    valid: true,
    value: { name: cleanName, description: cleanDescription, startMonth: startMonth || null },
  };
}

module.exports = {
  CUSTOM_SOURCE,
  NAME_MAX,
  DESCRIPTION_MAX,
  MAX_ROADMAPS_PER_USER,
  validateRoadmapInput,
};
