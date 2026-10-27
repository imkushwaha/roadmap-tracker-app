/**
 * @module progress-schema
 * Validates the progress JSON blob saved and loaded by the dashboard.
 *
 * Loaded in both the browser (via <script>) and Node.js (via require()), so
 * the module format is UMD. Deliberately tolerant: unknown top-level keys and
 * missing optional sections are accepted without error. Only known fields with
 * the wrong type are rejected, as they would otherwise break the UI.
 *
 * Adding validation for a new top-level key requires only a new per-section
 * function plus one call in validateProgress — existing validators are unchanged.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ProgressSchema = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const STATUSES = ["not_started", "in_progress", "completed", "blocked"];
  const START_MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;
  const MAX_ERRORS = 8;

  // ---------------------------------------------------------------------------
  // Type guards
  // ---------------------------------------------------------------------------

  const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
  const isStr = (v) => typeof v === "string";
  const isStrOrNull = (v) => v === null || typeof v === "string";

  // ---------------------------------------------------------------------------
  // Per-section validators — each pushes onto the shared errors array.
  // Short-circuiting (errors.length < MAX_ERRORS) happens in validateProgress.
  // ---------------------------------------------------------------------------

  /**
   * Validate the `items` map.
   * @param {unknown} items
   * @param {string[]} errors
   */
  function validateItems(items, errors) {
    if (!isObj(items)) { errors.push('"items" must be an object.'); return; }
    for (const id of Object.keys(items)) {
      if (id === "__proto__") { errors.push('items: key "__proto__" is not allowed.'); continue; }
      const it = items[id];
      if (!isObj(it)) { errors.push(`items.${id} must be an object.`); continue; }
      if (it.status !== undefined && !STATUSES.includes(it.status)) {
        errors.push(`items.${id}.status must be one of ${STATUSES.join(", ")}.`);
      }
      if (it.notes !== undefined && !isStr(it.notes)) errors.push(`items.${id}.notes must be a string.`);
      if (it.link !== undefined && !isStr(it.link)) errors.push(`items.${id}.link must be a string.`);
      if (it.dueDate !== undefined && !isStrOrNull(it.dueDate)) errors.push(`items.${id}.dueDate must be a string or null.`);
      if (it.completedAt !== undefined && !isStrOrNull(it.completedAt)) errors.push(`items.${id}.completedAt must be a string or null.`);
    }
  }

  /**
   * Validate the `counters` map.
   * @param {unknown} counters
   * @param {string[]} errors
   */
  function validateCounters(counters, errors) {
    if (!isObj(counters)) { errors.push('"counters" must be an object.'); return; }
    for (const id of Object.keys(counters)) {
      if (id === "__proto__") { errors.push('counters: key "__proto__" is not allowed.'); continue; }
      const v = counters[id];
      if (typeof v !== "number" || !isFinite(v) || v < 0) {
        errors.push(`counters.${id} must be a non-negative number.`);
      }
    }
  }

  /**
   * Validate the `celebratedPhases` array.
   * @param {unknown} phases
   * @param {string[]} errors
   */
  function validateCelebratedPhases(phases, errors) {
    if (!Array.isArray(phases) || !phases.every(isStr)) {
      errors.push('"celebratedPhases" must be an array of strings.');
    }
  }

  /**
   * Validate the `settings` object.
   * @param {unknown} settings
   * @param {string[]} errors
   */
  function validateSettings(settings, errors) {
    if (!isObj(settings)) { errors.push('"settings" must be an object.'); return; }
    if (
      settings.startMonth !== undefined &&
      !(isStr(settings.startMonth) && START_MONTH_RE.test(settings.startMonth))
    ) {
      errors.push('settings.startMonth must look like "YYYY-MM".');
    }
  }

  /**
   * Validate the `custom` extension block (topics and phases).
   * @param {unknown} custom
   * @param {string[]} errors
   */
  function validateCustom(custom, errors) {
    if (!isObj(custom)) { errors.push('"custom" must be an object.'); return; }
    if (custom.topics !== undefined) _validateCustomTopics(custom.topics, errors);
    if (custom.phases !== undefined) _validateCustomPhases(custom.phases, errors);
  }

  /**
   * Validate the custom topics array.
   * @param {unknown} topics
   * @param {string[]} errors
   */
  function _validateCustomTopics(topics, errors) {
    if (!Array.isArray(topics)) { errors.push('custom.topics must be an array.'); return; }
    topics.forEach((t, i) => {
      if (!isObj(t)) { errors.push(`custom.topics[${i}] must be an object.`); return; }
      if (!isStr(t.id) || !t.id) errors.push(`custom.topics[${i}].id must be a non-empty string.`);
      if (!isStr(t.sectionId)) errors.push(`custom.topics[${i}].sectionId must be a string.`);
      if (!isStr(t.title)) errors.push(`custom.topics[${i}].title must be a string.`);
      if (t.depth !== undefined && !isStrOrNull(t.depth)) errors.push(`custom.topics[${i}].depth must be a string or null.`);
      if (!Array.isArray(t.tasks)) {
        errors.push(`custom.topics[${i}].tasks must be an array.`);
      } else {
        t.tasks.forEach((k, j) => {
          if (!isObj(k) || !isStr(k.id) || !k.id || !isStr(k.title)) {
            errors.push(`custom.topics[${i}].tasks[${j}] needs string "id" and "title".`);
          }
        });
      }
    });
  }

  /**
   * Validate the custom phases array.
   * @param {unknown} phases
   * @param {string[]} errors
   */
  function _validateCustomPhases(phases, errors) {
    if (!Array.isArray(phases)) { errors.push('custom.phases must be an array.'); return; }
    phases.forEach((p, i) => {
      if (!isObj(p)) { errors.push(`custom.phases[${i}] must be an object.`); return; }
      if (!isStr(p.id) || !p.id) errors.push(`custom.phases[${i}].id must be a non-empty string.`);
      if (!isStr(p.title)) errors.push(`custom.phases[${i}].title must be a string.`);
      if (p.objective !== undefined && !isStr(p.objective)) errors.push(`custom.phases[${i}].objective must be a string.`);
      if (!Array.isArray(p.sections)) {
        errors.push(`custom.phases[${i}].sections must be an array.`);
      } else {
        p.sections.forEach((sec, j) => {
          const weekOk = sec && (
            sec.weekNumber === undefined || sec.weekNumber === null ||
            (Number.isInteger(sec.weekNumber) && sec.weekNumber >= 1 && sec.weekNumber <= 4)
          );
          if (!isObj(sec) || !isStr(sec.id) || !sec.id || !isStr(sec.title) || !weekOk) {
            errors.push(
              `custom.phases[${i}].sections[${j}] needs string "id" and "title", and weekNumber null or 1-4.`
            );
          }
        });
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Main validator
  // ---------------------------------------------------------------------------

  /**
   * Validate a progress data object against the schema.
   *
   * Tolerant of unknown top-level keys and absent optional sections.
   * Returns at most MAX_ERRORS messages to keep the payload bounded.
   *
   * @param {unknown} data
   * @returns {{ ok: boolean, errors: string[] }}
   */
  function validateProgress(data) {
    if (!isObj(data)) {
      return { ok: false, errors: ["Progress data must be a JSON object."] };
    }
    const errors = [];
    const within = () => errors.length < MAX_ERRORS;

    validateItems(data.items, errors);
    if (within() && data.counters !== undefined) validateCounters(data.counters, errors);
    if (within() && data.celebratedPhases !== undefined) validateCelebratedPhases(data.celebratedPhases, errors);
    if (within() && data.settings !== undefined) validateSettings(data.settings, errors);
    if (within() && data.custom !== undefined) validateCustom(data.custom, errors);

    return { ok: errors.length === 0, errors: errors.slice(0, MAX_ERRORS) };
  }

  return { validateProgress, STATUSES };
});
