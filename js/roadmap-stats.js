/**
 * @module roadmap-stats
 * Progress summaries for a roadmap: totals by status and a per-month breakdown
 * (the data behind the Month Strip on the Home screen).
 *
 * Loaded in Node.js (via require()) by the roadmap list endpoint. UMD like
 * progress-schema.js so the browser can reuse it later. Pure functions: no
 * I/O, no clock unless `now` is passed in.
 *
 * Counting rules mirror js/app.js (`rebuildIndex` / `statsFor`):
 *   - every task and every month deliverable of the curriculum counts once;
 *   - user-added topics (progress.custom.topics) count in the month that owns
 *     their section, built-in or custom;
 *   - user-added months (progress.custom.phases) follow the built-in months;
 *   - an id missing from progress.items is "not started".
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.RoadmapStats = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const DAY_MS = 86400000;
  const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

  /**
   * @typedef {object} CurriculumMonth
   * @property {string} id
   * @property {number} number
   * @property {string} title
   * @property {string[]} taskIds     tasks and deliverables of the month
   * @property {string[]} sectionIds  sections that user-added topics can attach to
   *
   * @typedef {object} Curriculum
   * @property {string | null} defaultStartMonth  "YYYY-MM" Month 1 is authored against
   * @property {CurriculumMonth[]} months
   */

  /**
   * Reduce the full roadmap JSON (data/roadmap.json) to the ids that matter for
   * counting. Done once at server start-up.
   * @param {{ meta?: { horizonStart?: string }, phases?: object[] }} data
   * @returns {Curriculum}
   */
  function buildCurriculum(data) {
    const phases = Array.isArray(data && data.phases) ? data.phases : [];
    const horizon = data && data.meta && data.meta.horizonStart;
    return {
      defaultStartMonth: typeof horizon === "string" && /^\d{4}-\d{2}/.test(horizon) ? horizon.slice(0, 7) : null,
      months: phases.map((phase) => ({
        id: phase.id,
        number: phase.number,
        title: phase.title,
        sectionIds: (phase.sections || []).map((s) => s.id),
        taskIds: [].concat(
          ...(phase.sections || []).map((s) => [].concat(
            ...(s.topics || []).map((t) => [].concat(
              ...(t.groups || []).map((g) => (g.subtasks || []).map((st) => st.id))
            ))
          )),
          (phase.deliverables || []).map((d) => d.id)
        ),
      })),
    };
  }

  /** The empty curriculum of a custom roadmap: everything lives in progress.custom. */
  const EMPTY_CURRICULUM = Object.freeze({ defaultStartMonth: null, months: [] });

  function monthsWithTasks(curriculum, custom) {
    const base = curriculum.months.map((m) => ({
      id: m.id, number: m.number, title: m.title, ids: m.taskIds.slice(),
    }));
    const bySection = new Map();
    curriculum.months.forEach((m, i) => m.sectionIds.forEach((id) => bySection.set(id, base[i])));

    const customPhases = custom && Array.isArray(custom.phases) ? custom.phases : [];
    customPhases.forEach((p, i) => {
      const month = { id: p.id, number: base.length + 1, title: p.title || "", ids: [] };
      base.push(month);
      (Array.isArray(p.sections) ? p.sections : []).forEach((s) => bySection.set(s.id, month));
    });

    const customTopics = custom && Array.isArray(custom.topics) ? custom.topics : [];
    customTopics.forEach((topic) => {
      const month = bySection.get(topic.sectionId);
      if (!month) return; // orphaned topic: the app does not show it either
      (Array.isArray(topic.tasks) ? topic.tasks : []).forEach((task) => month.ids.push(task.id));
    });
    return base;
  }

  function tally(ids, items) {
    const out = { total: ids.length, completed: 0, inProgress: 0, blocked: 0 };
    ids.forEach((id) => {
      const item = items[id];
      const status = item && item.status;
      if (status === "completed") out.completed += 1;
      else if (status === "in_progress") out.inProgress += 1;
      else if (status === "blocked") out.blocked += 1;
    });
    return out;
  }

  /**
   * Summarise a roadmap's progress.
   * @param {Curriculum} curriculum
   * @param {object | null} progress  the stored progress blob (or null if none yet)
   * @param {{ now?: Date }} [options]
   * @returns {{
   *   total: number, completed: number, inProgress: number, blocked: number,
   *   completedLast7Days: number, startMonth: string | null,
   *   months: Array<{ number: number, id: string, title: string,
   *                   total: number, completed: number, inProgress: number, blocked: number }>
   * }}
   */
  function summarize(curriculum, progress, options) {
    const now = (options && options.now) || new Date();
    const items = progress && isObj(progress.items) ? progress.items : {};
    const custom = progress && isObj(progress.custom) ? progress.custom : null;
    const settings = progress && isObj(progress.settings) ? progress.settings : {};

    const months = monthsWithTasks(curriculum || EMPTY_CURRICULUM, custom).map((m) => ({
      number: m.number, id: m.id, title: m.title, ...tally(m.ids, items),
    }));

    const totals = months.reduce((acc, m) => ({
      total: acc.total + m.total,
      completed: acc.completed + m.completed,
      inProgress: acc.inProgress + m.inProgress,
      blocked: acc.blocked + m.blocked,
    }), { total: 0, completed: 0, inProgress: 0, blocked: 0 });

    const since = now.getTime() - 7 * DAY_MS;
    const completedLast7Days = Object.values(items).filter((it) => {
      if (!isObj(it) || typeof it.completedAt !== "string") return false;
      const t = Date.parse(it.completedAt);
      return Number.isFinite(t) && t >= since && t <= now.getTime() + DAY_MS;
    }).length;

    return {
      ...totals,
      completedLast7Days,
      startMonth: settings.startMonth || (curriculum && curriculum.defaultStartMonth) || null,
      months,
    };
  }

  return { buildCurriculum, summarize, EMPTY_CURRICULUM };
});
