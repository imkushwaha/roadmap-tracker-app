// =============================================================
// AI Engineer Roadmap — Progress Dashboard
// Vanilla JS, no build step. Per-user data is stored on the server
// (SQLite, via /api); see js/api.js and the sync section below.
// =============================================================
(function () {
  "use strict";

  const DATA = window.ROADMAP_DATA;
  const STORAGE_KEY = "roadmap-dashboard:progress:v1";
  const THEME_KEY = "roadmap-dashboard:theme";

  const STATUS = ["not_started", "in_progress", "completed", "blocked"];
  const STATUS_LABEL = {
    not_started: "Not started",
    in_progress: "In progress",
    completed: "Completed",
    blocked: "Blocked",
  };

  // ---------------------------------------------------------
  // Progress store (in memory; synced to the server below)
  // ---------------------------------------------------------
  function normalizeProgress(parsed) {
    parsed = parsed || {};
    const customTopics = parsed.custom && Array.isArray(parsed.custom.topics) ? parsed.custom.topics : [];
    const customPhases = parsed.custom && Array.isArray(parsed.custom.phases) ? parsed.custom.phases : [];
    return {
      items: parsed.items || {},
      counters: parsed.counters || {},
      celebratedPhases: parsed.celebratedPhases || [],
      settings: parsed.settings || {},
      // User-added topics: [{ id, sectionId, title, depth, tasks: [{ id, title }] }]
      // User-added months: [{ id, title, objective, sections: [{ id, title, weekNumber }] }]
      custom: { topics: customTopics, phases: customPhases },
    };
  }

  // Browser storage is no longer the source of truth. The old localStorage
  // copy is only ever *read*, once, so it can be offered for import into the
  // account (see readLegacyLocalData). The app never deletes it.
  function readLegacyLocalData() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!window.ProgressSchema.validateProgress(parsed).ok) return null;
      const p = normalizeProgress(parsed);
      const meaningful = Object.keys(p.items).length > 0 ||
        Object.values(p.counters).some((v) => v > 0) ||
        p.custom.topics.length > 0 || !!p.settings.startMonth;
      return meaningful ? p : null;
    } catch (e) {
      return null;
    }
  }

  let progress = normalizeProgress(null);

  // Every mutation calls persist(); it now just flags the data as changed and
  // schedules a debounced save to the server (see "Server sync" below).
  function persist() {
    if (!session.username || session.roadmapId == null) return;
    session.dirty = true;
    if (session.conflict) return;
    if (session.saving) { setSaveStatus("saving"); return; }
    scheduleSave(SAVE_DEBOUNCE_MS);
  }

  function getItem(id) {
    const d = progress.items[id];
    return {
      status: (d && d.status) || "not_started",
      notes: (d && d.notes) || "",
      link: (d && d.link) || "",
      dueDate: (d && d.dueDate) || null,
      completedAt: (d && d.completedAt) || null,
    };
  }

  function setItemFields(id, fields) {
    const current = getItem(id);
    const next = Object.assign({}, current, fields);
    if (fields.status && fields.status === "completed" && current.status !== "completed") {
      next.completedAt = new Date().toISOString();
    }
    if (fields.status && fields.status !== "completed") {
      next.completedAt = null;
    }
    progress.items[id] = next;
    persist();
  }

  function getCounter(id, fallback) {
    return progress.counters[id] != null ? progress.counters[id] : fallback;
  }
  function setCounter(id, value) {
    progress.counters[id] = Math.max(0, value | 0);
    persist();
  }

  // ---------------------------------------------------------
  // Flatten roadmap into a searchable/filterable index
  // ---------------------------------------------------------
  // The static roadmap plus any topics the user has added themselves.
  // Every view reads from INDEX / topicsOf(), so a custom topic shows up
  // everywhere (Timeline, Checklist, Kanban, This Week, stats) at once.
  function topicsOf(section) {
    const extra = progress.custom.topics
      .filter((t) => t.sectionId === section.id)
      .map((t) => ({
        id: t.id,
        title: t.title,
        depth: t.depth || null,
        kind: "study",
        custom: true,
        groups: [{ label: null, subtasks: t.tasks.map((k) => ({ id: k.id, title: k.title })) }],
      }));
    return section.topics.concat(extra);
  }

  // Built-in months plus any months the user added. Custom months continue
  // the numbering (Month 11, 12, …) so their dates follow the start month.
  function buildCustomPhases() {
    return progress.custom.phases.map((p, i) => ({
      id: p.id,
      number: DATA.phases.length + i + 1,
      title: p.title,
      objective: p.objective || "",
      exitCriteria: [],
      notes: [],
      deliverables: [],
      custom: true,
      sections: p.sections.map((sec) => ({
        id: sec.id,
        title: sec.title,
        type: sec.weekNumber ? "week" : "theme",
        weekNumber: sec.weekNumber || null,
        topics: [],
        custom: true,
      })),
    }));
  }
  let ALL_PHASES = DATA.phases;
  function allPhases() { return ALL_PHASES; }

  const INDEX = [];
  function rebuildIndex() {
    ALL_PHASES = DATA.phases.concat(buildCustomPhases());
    INDEX.length = 0;
    ALL_PHASES.forEach((phase) => {
      phase.sections.forEach((section) => {
        topicsOf(section).forEach((topic) => {
          topic.groups.forEach((group) => {
            group.subtasks.forEach((st) => {
              INDEX.push({
                id: st.id,
                title: st.title,
                kind: "subtask",
                custom: !!topic.custom,
                phaseId: phase.id,
                phaseNumber: phase.number,
                phaseTitle: phase.title,
                sectionId: section.id,
                sectionTitle: section.title,
                sectionType: section.type,
                weekNumber: section.weekNumber || null,
                topicId: topic.id,
                topicTitle: topic.title,
                topicDepth: topic.depth,
                topicKind: topic.kind,
                groupLabel: group.label,
              });
            });
          });
        });
      });
      phase.deliverables.forEach((st) => {
        INDEX.push({
          id: st.id,
          title: st.title,
          kind: "deliverable",
          custom: false,
          phaseId: phase.id,
          phaseNumber: phase.number,
          phaseTitle: phase.title,
          sectionId: null,
          sectionTitle: "Month Deliverables",
          sectionType: "deliverables",
          weekNumber: null,
          topicId: null,
          topicTitle: "Deliverables",
          topicDepth: null,
          topicKind: "deliverable",
          groupLabel: null,
        });
      });
    });
  }
  rebuildIndex();

  function phaseSubtaskIds(phaseId) {
    return INDEX.filter((e) => e.phaseId === phaseId).map((e) => e.id);
  }

  // ---------------------------------------------------------
  // Date utilities
  // ---------------------------------------------------------
  function parseDate(iso) {
    if (!iso) return null;
    const d = new Date(iso + "T00:00:00");
    return isNaN(d.getTime()) ? null : d;
  }
  function today() {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }
  function daysBetween(a, b) {
    return Math.round((b - a) / 86400000);
  }
  function fmtDate(d) {
    if (!d) return "";
    if (typeof d === "string") d = parseDate(d);
    if (!d) return "";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }
  function fmtDateShort(d) {
    if (!d) return "";
    if (typeof d === "string") d = parseDate(d);
    if (!d) return "";
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
  function isoWeekKey(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    const weekNo = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
    return d.getUTCFullYear() + "-W" + String(weekNo).padStart(2, "0");
  }

  const TODAY = today();

  // ---------------------------------------------------------
  // Configurable start month
  //
  // The roadmap source bakes in calendar dates (e.g. "Month 1 = October
  // 2026"), but you may actually start a different month. Rather than
  // trusting those baked-in dates, every phase/week date used anywhere in
  // the app is computed from a single, user-editable "Month 1 starts on"
  // setting (stored with the rest of your account data). Change it
  // any time from the data menu and the whole timeline shifts to match.
  // ---------------------------------------------------------
  function defaultStartMonth() {
    // Fall back to whatever the source roadmap was authored against.
    const d = parseDate(DATA.meta.horizonStart) || new Date();
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
  }
  function currentMonthKey() {
    return TODAY.getFullYear() + "-" + String(TODAY.getMonth() + 1).padStart(2, "0");
  }
  function getStartMonth() {
    return (progress.settings && progress.settings.startMonth) || defaultStartMonth();
  }
  function setStartMonth(yyyyMm) {
    progress.settings = progress.settings || {};
    progress.settings.startMonth = yyyyMm;
    persist();
  }
  function roadmapStartDate() {
    const [y, m] = getStartMonth().split("-").map(Number);
    return new Date(y, m - 1, 1);
  }
  function addMonths(date, n) {
    return new Date(date.getFullYear(), date.getMonth() + n, 1);
  }
  function lastDayOfMonth(date) {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0);
  }
  function phaseStartDate(phaseNumber) {
    return addMonths(roadmapStartDate(), phaseNumber - 1);
  }
  function phaseEndDate(phaseNumber) {
    return lastDayOfMonth(phaseStartDate(phaseNumber));
  }
  function phaseCalendarLabel(phaseNumber) {
    return phaseStartDate(phaseNumber)
      .toLocaleDateString(undefined, { month: "long", year: "numeric" })
      .toUpperCase();
  }
  // Weeks are approximated as sequential 7-day blocks from the start of
  // their phase's month (the source gives month labels, not explicit week
  // dates) — same approximation the data generator uses, just computed
  // live so it follows whatever start month you've set.
  function weekStartDate(phaseNumber, weekNumber) {
    const offset = (weekNumber - 1) % 4;
    const d = new Date(phaseStartDate(phaseNumber));
    d.setDate(d.getDate() + 7 * offset);
    return d;
  }
  function weekEndDate(phaseNumber, weekNumber) {
    const d = new Date(weekStartDate(phaseNumber, weekNumber));
    d.setDate(d.getDate() + 6);
    return d;
  }
  function sectionDates(phaseNumber, section) {
    if (!section || section.type !== "week" || !section.weekNumber) return { start: null, end: null };
    return { start: weekStartDate(phaseNumber, section.weekNumber), end: weekEndDate(phaseNumber, section.weekNumber) };
  }
  function entryDates(entry) {
    if (!entry.weekNumber) return { start: null, end: null };
    return { start: weekStartDate(entry.phaseNumber, entry.weekNumber), end: weekEndDate(entry.phaseNumber, entry.weekNumber) };
  }
  function horizonStart() {
    return phaseStartDate(1);
  }
  function horizonEnd() {
    return phaseEndDate(allPhases().length);
  }

  function currentPhase() {
    return allPhases().find((p) => {
      const s = phaseStartDate(p.number), e = phaseEndDate(p.number);
      return TODAY >= s && TODAY <= e;
    });
  }
  function currentSection(phase) {
    if (!phase) return null;
    return phase.sections.find((s) => {
      const { start, end } = sectionDates(phase.number, s);
      return start && end && TODAY >= start && TODAY <= end;
    });
  }

  // ---------------------------------------------------------
  // Stats
  // ---------------------------------------------------------
  function statsFor(ids) {
    let total = ids.length, completed = 0, inProgress = 0, blocked = 0;
    ids.forEach((id) => {
      const s = getItem(id).status;
      if (s === "completed") completed++;
      else if (s === "in_progress") inProgress++;
      else if (s === "blocked") blocked++;
    });
    return {
      total, completed, inProgress, blocked,
      notStarted: total - completed - inProgress - blocked,
      pct: total ? Math.round((completed / total) * 100) : 0,
    };
  }
  function phaseStats(phaseId) {
    return statsFor(phaseSubtaskIds(phaseId));
  }
  function overallStats() {
    return statsFor(INDEX.map((e) => e.id));
  }
  function sectionStats(sectionId) {
    return statsFor(INDEX.filter((e) => e.sectionId === sectionId).map((e) => e.id));
  }
  function topicStats(topicId) {
    return statsFor(INDEX.filter((e) => e.topicId === topicId).map((e) => e.id));
  }

  function momentumThisWeek() {
    const weekAgo = new Date(TODAY.getTime() - 7 * 86400000);
    let n = 0;
    Object.values(progress.items).forEach((it) => {
      if (it.completedAt && new Date(it.completedAt) >= weekAgo) n++;
    });
    return n;
  }

  function weeklyCompletionSeries(weeks) {
    const buckets = {};
    Object.values(progress.items).forEach((it) => {
      if (!it.completedAt) return;
      const key = isoWeekKey(new Date(it.completedAt));
      buckets[key] = (buckets[key] || 0) + 1;
    });
    const out = [];
    for (let i = weeks - 1; i >= 0; i--) {
      const d = new Date(TODAY.getTime() - i * 7 * 86400000);
      const key = isoWeekKey(d);
      out.push({ key, label: "W" + key.split("-W")[1], count: buckets[key] || 0 });
    }
    return out;
  }

  function estimatedCompletion(overall) {
    const completedWithDates = Object.values(progress.items).filter((it) => it.completedAt);
    if (completedWithDates.length < 3) return null;
    const earliest = completedWithDates.reduce(
      (min, it) => Math.min(min, new Date(it.completedAt).getTime()),
      Date.now()
    );
    const daysSince = Math.max(1, daysBetween(new Date(earliest), new Date()));
    const rate = completedWithDates.length / daysSince; // tasks/day
    if (rate <= 0) return null;
    const remaining = overall.total - overall.completed;
    const daysNeeded = Math.ceil(remaining / rate);
    const projected = new Date(TODAY.getTime() + daysNeeded * 86400000);
    return { projected, rate };
  }

  // ---------------------------------------------------------
  // Small render helpers
  // ---------------------------------------------------------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function progressBar(pct) {
    return `<div class="progress-row">
      <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="progress-pct">${pct}%</div>
    </div>`;
  }

  function statusChip(status) {
    return `<span class="status-chip status-${status}">${STATUS_LABEL[status]}</span>`;
  }

  function statusSelect(id, status) {
    return `<select class="status-select" data-action="set-status" data-id="${id}">
      ${STATUS.map((s) => `<option value="${s}" ${s === status ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}
    </select>`;
  }

  function depthBadge(depth) {
    if (!depth) return "";
    const code = depth.split("/")[0].trim();
    const cls = code.startsWith("D3") ? "badge-depth-D3" : code.startsWith("D2") ? "badge-depth-D2" : "badge-depth-D1";
    return `<span class="badge ${cls}">${esc(depth)}</span>`;
  }

  function dueTag(dueDate, status) {
    if (!dueDate) return "";
    const d = parseDate(dueDate);
    const overdue = d && d < TODAY && status !== "completed";
    return `<span class="due-tag ${overdue ? "overdue" : ""}">${overdue ? "Overdue · " : "Due "}${fmtDateShort(d)}</span>`;
  }

  function matchesSearch(entry, q) {
    if (!q) return true;
    const hay = (entry.title + " " + entry.topicTitle + " " + entry.phaseTitle + " " + (getItem(entry.id).notes || "")).toLowerCase();
    return hay.includes(q);
  }

  // ---------------------------------------------------------
  // Subtask row (shared by Checklist / This Week / Timeline)
  // ---------------------------------------------------------
  function subtaskRow(entry, opts) {
    opts = opts || {};
    const item = getItem(entry.id);
    const checked = item.status === "completed";
    const overdueCls = item.dueDate && parseDate(item.dueDate) < TODAY && !checked ? "overdue" : "";
    return `<div class="subtask-row ${overdueCls}" data-row-id="${entry.id}">
      <input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${entry.id}" ${checked ? "checked" : ""} aria-label="Mark complete" />
      <div class="subtask-main">
        <div class="subtask-title ${checked ? "done" : ""}">${esc(entry.title)}</div>
        ${opts.showCrumbs ? `<div class="topic-crumbs">Month ${entry.phaseNumber} · ${esc(entry.sectionTitle)} ${entry.topicTitle && entry.topicTitle !== "Deliverables" ? "· " + esc(entry.topicTitle) : ""}</div>` : ""}
        <div class="subtask-meta">
          ${statusSelect(entry.id, item.status)}
          ${dueTag(item.dueDate, item.status)}
          ${item.link ? `<a class="subtask-link" href="${esc(item.link)}" target="_blank" rel="noopener">🔗 link</a>` : ""}
          <button class="mini-btn" data-action="open-edit" data-id="${entry.id}">✎ details</button>
          ${entry.custom ? `<button class="mini-btn" data-action="delete-task" data-id="${entry.id}" title="Remove this task">✕</button>` : ""}
          ${item.notes ? `<span class="subtask-note-preview">"${esc(item.notes.slice(0, 48))}${item.notes.length > 48 ? "…" : ""}"</span>` : ""}
        </div>
      </div>
    </div>`;
  }

  // ---------------------------------------------------------
  // VIEW: Overview
  // ---------------------------------------------------------
  function renderOverview(container) {
    const overall = overallStats();
    const cur = currentPhase();
    const curSection = currentSection(cur);
    const hStart = horizonStart(), hEnd = horizonEnd();
    const elapsed = Math.max(0, daysBetween(hStart, TODAY));
    const totalDays = Math.max(1, daysBetween(hStart, hEnd));
    const remaining = Math.max(0, daysBetween(TODAY, hEnd));
    const momentum = momentumThisWeek();
    const est = estimatedCompletion(overall);
    const series = weeklyCompletionSeries(8);
    const maxBar = Math.max(1, ...series.map((s) => s.count));

    container.innerHTML = `
      <div class="section-title">Dashboard</div>
      <div class="grid grid-stats">
        <div class="stat-tile">
          <div class="stat-label">Overall progress</div>
          <div class="stat-value">${overall.pct}%</div>
          <div class="stat-sub">${overall.completed} / ${overall.total} tasks done</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Current month</div>
          <div class="stat-value">${cur ? "M" + cur.number : "—"}</div>
          <div class="stat-sub">${cur ? esc(cur.title) : "Outside planned horizon"}</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Timeline</div>
          <div class="stat-value">${elapsed}d <span style="color:var(--text-faint); font-size:15px;">/ ${totalDays}d</span></div>
          <div class="stat-sub">${remaining >= 0 ? remaining + " days remaining" : "Target date passed"}</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">This week's momentum</div>
          <div class="stat-value">${momentum}</div>
          <div class="stat-sub">tasks completed in last 7 days</div>
        </div>
      </div>

      <div class="grid grid-2col" style="margin-top:18px;">
        <div class="card">
          <div class="section-title" style="margin-top:0;">Progress by month</div>
          ${allPhases().map((p) => {
            const st = phaseStats(p.id);
            const isCurrent = cur && cur.id === p.id;
            const isDone = st.pct === 100;
            return `<div style="margin-bottom:12px;">
              <div style="display:flex; justify-content:space-between; font-size:12.5px; margin-bottom:4px;">
                <span style="font-weight:700;">M${p.number} — ${esc(p.title)} ${isCurrent ? '<span class="badge badge-here">YOU ARE HERE</span>' : ""} ${isDone ? '<span class="badge" style="background:var(--status-completed-bg); color:var(--status-completed);">✓ done</span>' : ""}</span>
                <span style="color:var(--text-faint);">${fmtDateShort(phaseStartDate(p.number))}–${fmtDateShort(phaseEndDate(p.number))}</span>
              </div>
              ${progressBar(st.pct)}
            </div>`;
          }).join("")}
        </div>

        <div class="card">
          <div class="section-title" style="margin-top:0;">Pace</div>
          ${est ? `
            <p style="font-size:13px; margin:0 0 4px;">At your current pace, you'll finish around</p>
            <p style="font-size:20px; font-weight:800; margin:0 0 4px;">${fmtDate(est.projected)}</p>
            <p style="font-size:12px; color:var(--text-faint); margin:0;">Planned target: ${fmtDate(hEnd)} · ~${est.rate.toFixed(2)} tasks/day</p>
          ` : `<p style="font-size:13px; color:var(--text-faint);">Complete a few tasks to unlock a pace estimate.</p>`}

          <div class="section-title">This week</div>
          ${curSection ? `<p style="font-size:13px; margin:0;">Focus: <strong>${esc(curSection.title)}</strong></p>` : `<p style="font-size:13px; color:var(--text-faint);">No active week in range.</p>`}

          <div class="section-title">Tasks completed / week</div>
          <div class="bar-chart">
            ${series.map((s) => `<div class="bar-col"><div class="bar" style="height:${Math.round((s.count / maxBar) * 70) || 2}px" title="${s.count} completed"></div><div class="bar-label">${s.label}</div></div>`).join("")}
          </div>
        </div>
      </div>

      <div class="section-title">Status breakdown</div>
      <div class="grid grid-stats">
        <div class="stat-tile"><div class="stat-label">${statusChip("completed")}</div><div class="stat-value">${overall.completed}</div></div>
        <div class="stat-tile"><div class="stat-label">${statusChip("in_progress")}</div><div class="stat-value">${overall.inProgress}</div></div>
        <div class="stat-tile"><div class="stat-label">${statusChip("blocked")}</div><div class="stat-value">${overall.blocked}</div></div>
        <div class="stat-tile"><div class="stat-label">${statusChip("not_started")}</div><div class="stat-value">${overall.notStarted}</div></div>
      </div>

      <div class="section-title">Interview & career counters</div>
      <div class="grid grid-stats">
        ${DATA.counters.map((c) => {
          const val = getCounter(c.id, c.current);
          const pct = c.target ? Math.min(100, Math.round((val / c.target) * 100)) : 0;
          return `<div class="stat-tile">
            <div class="stat-label">${esc(c.label)}</div>
            <div class="stat-value">${val}<span style="color:var(--text-faint); font-size:14px;"> / ${c.target}</span></div>
            <div style="margin-top:8px;">${progressBar(pct)}</div>
            <div style="display:flex; gap:6px; margin-top:8px;">
              <button class="mini-btn" data-action="counter-dec" data-id="${c.id}">−</button>
              <button class="mini-btn" data-action="counter-inc" data-id="${c.id}">+</button>
            </div>
          </div>`;
        }).join("")}
      </div>
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Timeline
  // ---------------------------------------------------------
  const timelineOpenState = {}; // sectionId -> bool

  function renderTimeline(container) {
    const cur = currentPhase();
    container.innerHTML = `
      <div class="section-title">Roadmap Timeline</div>
      <div class="timeline">
        ${allPhases().map((p) => {
          const st = phaseStats(p.id);
          const isCurrent = cur && cur.id === p.id;
          const isDone = st.pct === 100;
          return `<div class="timeline-item ${isCurrent ? "is-current" : ""} ${isDone ? "is-done" : ""}">
            <div class="timeline-dot">${isDone ? "✓" : isCurrent ? "●" : ""}</div>
            <div class="phase-card ${isCurrent ? "is-current" : ""}">
              <div class="phase-card-head">
                <div>
                  <div class="phase-num">Month ${p.number} · ${esc(phaseCalendarLabel(p.number))}</div>
                  <div class="phase-title">${esc(p.title)} ${isCurrent ? '<span class="badge badge-here">YOU ARE HERE</span>' : ""}${p.custom ? ' <span class="badge badge-custom">Custom</span>' : ""}</div>
                  <div class="phase-dates">${fmtDate(phaseStartDate(p.number))} – ${fmtDate(phaseEndDate(p.number))}${p.custom ? ` <button class="mini-btn" data-action="delete-month" data-id="${p.id}" title="Delete this month and everything in it">🗑 Delete month</button>` : ""}</div>
                </div>
                <button class="phase-expand-btn" data-action="toggle-phase" data-id="${p.id}">${expandedPhases[p.id] ? "Collapse" : "Expand"}</button>
              </div>
              ${progressBar(st.pct)}
              ${p.objective ? `<p style="font-size:12.5px; color:var(--text-muted); margin:10px 0 0;">${esc(p.objective)}</p>` : ""}
              ${expandedPhases[p.id] ? renderPhaseBody(p) : ""}
            </div>
          </div>`;
        }).join("")}
      </div>
      <button class="add-topic-btn add-month-btn" data-action="add-month">＋ Add month (Month ${allPhases().length + 1} · ${esc(phaseCalendarLabel(allPhases().length + 1))})</button>
    `;
  }

  const expandedPhases = {};

  function renderPhaseBody(phase) {
    const exitCriteria = phase.exitCriteria && phase.exitCriteria.length
      ? `<div class="group-label" style="margin-top:14px;">Exit criteria</div>
         <ul style="margin:0; padding-left:18px; font-size:12.5px; color:var(--text-muted);">
           ${phase.exitCriteria.map((c) => `<li>${esc(c)}</li>`).join("")}
         </ul>` : "";

    const sections = phase.sections.map((s) => {
      const st = sectionStats(s.id);
      const open = sectionOpenState[s.id] !== false; // default open
      const { start: wStart, end: wEnd } = sectionDates(phase.number, s);
      return `<div class="week-block">
        <div class="week-head ${open ? "open" : ""}" data-action="toggle-section" data-id="${s.id}">
          <h4><span class="caret">▸</span> ${esc(s.title)}</h4>
          <div class="week-meta">${wStart ? fmtDateShort(wStart) + "–" + fmtDateShort(wEnd) + " · " : ""}${st.completed}/${st.total}${s.custom ? ` <button class="mini-btn" data-action="delete-section" data-id="${s.id}" title="Delete this section and its topics">🗑</button>` : ""}</div>
        </div>
        ${open ? renderTopics(topicsOf(s)) + `<button class="add-topic-btn" data-action="add-topic" data-section-id="${s.id}">＋ Add topic to this ${s.type === "week" ? "week" : "section"}</button>` : ""}
      </div>`;
    }).join("");

    const notes = (phase.notes || []).map((n) => `
      <div class="ref-block" style="background:var(--bg-sunken); padding:10px 12px; border-radius:8px; margin-top:10px;">
        <strong style="font-size:12.5px;">${esc(n.title)}</strong>
        <div style="margin-top:4px;">${n.blocks.map((b) => esc(b)).join("\n\n")}</div>
      </div>`).join("");

    const deliverables = phase.deliverables && phase.deliverables.length ? `
      <div class="week-block">
        <div class="week-head open"><h4><span class="caret">▸</span> Month ${phase.number} Deliverables</h4></div>
        <div class="topic-block">
          ${phase.deliverables.map((d) => subtaskRow(indexEntry(d.id))).join("")}
        </div>
      </div>` : "";

    const addSection = phase.custom
      ? (phase.sections.length ? "" : `<p class="empty-hint">This month has no sections yet. Add one, then add topics and tasks inside it.</p>`) +
        `<button class="add-topic-btn" data-action="add-section" data-phase-id="${phase.id}">＋ Add section to this month</button>`
      : "";

    return exitCriteria + sections + addSection + deliverables + (notes ? `<div class="group-label" style="margin-top:14px;">Context & notes</div>${notes}` : "");
  }

  const sectionOpenState = {};

  function renderTopics(topics) {
    return topics.map((t) => {
      const st = topicStats(t.id);
      return `<div class="topic-block">
        <div class="topic-head">
          <span class="topic-title">${esc(t.title)}</span>
          ${depthBadge(t.depth)}
          ${t.custom ? `<span class="badge badge-custom">Custom</span>
            <button class="mini-btn" data-action="add-task" data-topic-id="${t.id}">＋ task</button>
            <button class="mini-btn" data-action="delete-topic" data-topic-id="${t.id}" title="Delete this topic and its tasks">🗑</button>` : ""}
          <span class="topic-progress">${st.completed}/${st.total}</span>
        </div>
        ${t.groups.map((g) => `
          ${g.label ? `<div class="group-label">${esc(g.label)}</div>` : ""}
          ${g.subtasks.map((s) => subtaskRow(indexEntry(s.id))).join("")}
        `).join("")}
      </div>`;
    }).join("");
  }

  function indexEntry(id) {
    return INDEX.find((e) => e.id === id) || { id, title: id, phaseNumber: "", sectionTitle: "", topicTitle: "" };
  }

  // ---------------------------------------------------------
  // VIEW: Checklist
  // ---------------------------------------------------------
  const checklistFilters = { status: "all", phase: "all" };

  function renderChecklist(container) {
    const q = state.search.trim().toLowerCase();
    let entries = INDEX.filter((e) => matchesSearch(e, q));
    if (checklistFilters.status !== "all") entries = entries.filter((e) => getItem(e.id).status === checklistFilters.status);
    if (checklistFilters.phase !== "all") entries = entries.filter((e) => e.phaseId === checklistFilters.phase);

    // group by phase > section > topic
    const byPhase = {};
    entries.forEach((e) => {
      byPhase[e.phaseId] = byPhase[e.phaseId] || { title: e.phaseTitle, number: e.phaseNumber, sections: {} };
      const sec = byPhase[e.phaseId].sections;
      sec[e.sectionId || "deliverables"] = sec[e.sectionId || "deliverables"] || { title: e.sectionTitle, topics: {} };
      const top = sec[e.sectionId || "deliverables"].topics;
      const tKey = e.topicId || "deliverables";
      top[tKey] = top[tKey] || { title: e.topicTitle, depth: e.topicDepth, custom: e.custom, items: [] };
      top[tKey].items.push(e);
    });

    const phaseIds = Object.keys(byPhase).sort((a, b) => byPhase[a].number - byPhase[b].number);

    container.innerHTML = `
      <div class="section-title">Checklist</div>
      <div class="filter-bar">
        ${["all", ...STATUS].map((s) => `<button class="chip-filter ${checklistFilters.status === s ? "active" : ""}" data-action="filter-status" data-value="${s}">${s === "all" ? "All" : STATUS_LABEL[s]}</button>`).join("")}
        <select class="select-filter" data-action="filter-phase">
          <option value="all">All months</option>
          ${allPhases().map((p) => `<option value="${p.id}" ${checklistFilters.phase === p.id ? "selected" : ""}>Month ${p.number} — ${esc(p.title)}</option>`).join("")}
        </select>
        <span style="font-size:12px; color:var(--text-faint); margin-left:auto;">${entries.length} task${entries.length === 1 ? "" : "s"}</span>
      </div>
      <div id="checklistBody">
        ${phaseIds.length === 0 ? emptyState("No tasks match your filters.") : phaseIds.map((pid) => {
          const phase = byPhase[pid];
          return `<div class="phase-section-group">
            <div class="psg-head">Month ${phase.number} — ${esc(phase.title)}</div>
            ${Object.keys(phase.sections).map((sid) => {
              const section = phase.sections[sid];
              return `<div style="margin:8px 0 10px 10px;">
                <div style="font-size:12.5px; font-weight:700; color:var(--text-muted); margin-bottom:4px;">${esc(section.title)}</div>
                ${Object.keys(section.topics).map((tid) => {
                  const topic = section.topics[tid];
                  return `<div class="topic-block">
                    <div class="topic-head">
                      <span class="topic-title">${esc(topic.title)}</span>
                      ${depthBadge(topic.depth)}
                      ${topic.custom ? '<span class="badge badge-custom">Custom</span>' : ""}
                    </div>
                    ${topic.items.map((e) => subtaskRow(e)).join("")}
                  </div>`;
                }).join("")}
              </div>`;
            }).join("")}
          </div>`;
        }).join("")}
      </div>
    `;
  }

  function emptyState(msg) {
    return `<div class="empty-state"><span class="emoji">🗒️</span>${esc(msg)}</div>`;
  }

  // ---------------------------------------------------------
  // VIEW: This Week
  // ---------------------------------------------------------
  function renderThisWeek(container) {
    const weekAhead = new Date(TODAY.getTime() + 7 * 86400000);
    const active = INDEX.filter((e) => {
      const item = getItem(e.id);
      if (item.status === "completed") return false;
      const { start: secStart, end: secEnd } = entryDates(e);
      const inActiveSection = secStart && secEnd && TODAY >= secStart && TODAY <= secEnd;
      const due = parseDate(item.dueDate);
      const dueSoon = due && due <= weekAhead;
      return inActiveSection || dueSoon;
    });
    const overdue = active.filter((e) => {
      const d = parseDate(getItem(e.id).dueDate);
      return d && d < TODAY;
    });
    const rest = active.filter((e) => overdue.indexOf(e) === -1);

    const cur = currentPhase();
    const curSec = currentSection(cur);

    container.innerHTML = `
      <div class="section-title">This Week</div>
      <div class="card" style="margin-bottom:16px;">
        ${cur ? `<p style="margin:0; font-size:13.5px;">Month ${cur.number} — <strong>${esc(cur.title)}</strong>${curSec ? " · " + esc(curSec.title) : ""}</p>` : `<p style="margin:0; color:var(--text-faint); font-size:13.5px;">Today isn't inside a planned month — showing anything with a near-term due date.</p>`}
      </div>
      ${overdue.length ? `<div class="section-title" style="color:var(--status-blocked);">Overdue (${overdue.length})</div>${overdue.map((e) => subtaskRow(e, { showCrumbs: true })).join("")}` : ""}
      <div class="section-title">Active now (${rest.length})</div>
      ${rest.length ? rest.map((e) => subtaskRow(e, { showCrumbs: true })).join("") : emptyState("Nothing active right now — check the Checklist view or get ahead on next week.")}
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Kanban
  // ---------------------------------------------------------
  const kanbanState = { phase: null };

  function renderKanban(container) {
    if (!kanbanState.phase) {
      const cur = currentPhase();
      kanbanState.phase = cur ? cur.id : DATA.phases[0].id;
    }
    const q = state.search.trim().toLowerCase();
    const entries = INDEX.filter((e) => e.phaseId === kanbanState.phase && matchesSearch(e, q));
    const cols = { not_started: [], in_progress: [], blocked: [], completed: [] };
    entries.forEach((e) => cols[getItem(e.id).status].push(e));

    const colMeta = [
      { key: "not_started", label: "To Do" },
      { key: "in_progress", label: "In Progress" },
      { key: "blocked", label: "Blocked" },
      { key: "completed", label: "Done" },
    ];

    container.innerHTML = `
      <div class="section-title">Kanban</div>
      <div class="kanban-toolbar">
        <select class="select-filter" data-action="kanban-phase">
          ${allPhases().map((p) => `<option value="${p.id}" ${kanbanState.phase === p.id ? "selected" : ""}>Month ${p.number} — ${esc(p.title)}</option>`).join("")}
        </select>
        <span style="font-size:12px; color:var(--text-faint);">Drag cards between columns, or use the ⋯ menu on a card.</span>
      </div>
      <div class="kanban-board">
        ${colMeta.map((c) => `
          <div class="kanban-col" data-action="kanban-dropzone" data-status="${c.key}">
            <div class="kanban-col-head"><span>${c.label}</span><span>${cols[c.key].length}</span></div>
            ${cols[c.key].map((e) => `
              <div class="kanban-card" draggable="true" data-id="${e.id}" data-action="kanban-card">
                <div class="k-title">${esc(e.title)}</div>
                <div class="k-path">${esc(e.sectionTitle)}${e.topicTitle && e.topicTitle !== "Deliverables" ? " · " + esc(e.topicTitle) : ""}${e.custom ? " · ★ custom" : ""}</div>
                <div style="margin-top:6px; display:flex; gap:6px;">
                  <button class="mini-btn" data-action="open-edit" data-id="${e.id}">✎</button>
                </div>
              </div>
            `).join("")}
          </div>
        `).join("")}
      </div>
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Mastery checklist
  // ---------------------------------------------------------
  function renderMastery(container) {
    const q = state.search.trim().toLowerCase();
    container.innerHTML = `
      <div class="section-title">Skills Mastery Checklist</div>
      <p style="font-size:12.5px; color:var(--text-faint); margin-top:-6px;">A flat, non-date-bound reference checklist of the roadmap's full skill list (source: "AI Engineering Mastery Checklist"). Track these independently of the month-by-month timeline.</p>
      <div class="mastery-grid">
        ${DATA.masteryChecklist.map((cat) => {
          const skills = cat.skills.filter((sk) => !q || sk.title.toLowerCase().includes(q));
          if (!skills.length) return "";
          const done = cat.skills.filter((sk) => getItem(sk.id).status === "completed").length;
          return `<div class="mastery-cat">
            <h3>${esc(cat.title)} <span style="color:var(--text-faint); font-weight:600; font-size:11.5px;">(${done}/${cat.skills.length})</span></h3>
            ${skills.map((sk) => `
              <div class="mastery-skill-row">
                <input type="checkbox" class="subtask-checkbox" data-action="toggle-complete" data-id="${sk.id}" ${getItem(sk.id).status === "completed" ? "checked" : ""} />
                <span class="skill-title ${getItem(sk.id).status === "completed" ? "done" : ""}" style="${getItem(sk.id).status === "completed" ? "text-decoration:line-through; color:var(--text-faint);" : ""}">${esc(sk.title)}</span>
                ${depthBadge(sk.depth)}
              </div>
            `).join("")}
          </div>`;
        }).join("")}
      </div>
    `;
  }

  // ---------------------------------------------------------
  // VIEW: Reference
  // ---------------------------------------------------------
  function renderBlockAsHtml(block) {
    const lines = block.split("\n");
    const isTableBlock = lines.filter((l) => l.trim().startsWith("|")).length >= 2;
    if (isTableBlock) {
      const rows = lines.filter((l) => l.trim().startsWith("|")).map((l) =>
        l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim())
      );
      const header = rows[0];
      const body = rows.slice(1).filter((r) => !r.every((c) => /^:?-+:?$/.test(c)));
      return `<table><thead><tr>${header.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
        <tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }
    return esc(block).replace(/^#{1,4}\s*(.+)$/gm, "<strong>$1</strong>").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function renderReference(container) {
    const q = state.search.trim().toLowerCase();
    container.innerHTML = `
      <div class="section-title">Reference & Strategy</div>
      <p style="font-size:12.5px; color:var(--text-faint); margin-top:-6px;">Background and strategic context from the roadmap that isn't itself a checklist item — preserved here so nothing is lost.</p>
      ${DATA.reference.map((r) => {
        const hay = (r.title + " " + r.blocks.join(" ")).toLowerCase();
        const match = !q || hay.includes(q);
        return `<div class="card ref-card ${match ? "" : "ref-search-hidden"}">
          <h3>${esc(r.title)}</h3>
          ${r.blocks.map((b) => `<div class="ref-block">${renderBlockAsHtml(b)}</div>`).join("")}
        </div>`;
      }).join("")}
    `;
  }

  // ---------------------------------------------------------
  // Toasts & Confetti
  // ---------------------------------------------------------
  function toast(msg, kind) {
    const host = document.getElementById("toastHost");
    const el = document.createElement("div");
    el.className = "toast " + (kind || "");
    el.textContent = msg;
    host.appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  function celebrate(phaseTitle) {
    toast(`🎉 Month complete: ${phaseTitle}!`, "celebrate");
    const canvas = document.getElementById("confettiCanvas");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const ctx = canvas.getContext("2d");
    const colors = ["#4f46e5", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4"];
    const particles = Array.from({ length: 140 }, () => ({
      x: Math.random() * canvas.width,
      y: -20 - Math.random() * canvas.height * 0.3,
      vx: (Math.random() - 0.5) * 4,
      vy: 2 + Math.random() * 4,
      size: 4 + Math.random() * 5,
      color: colors[(Math.random() * colors.length) | 0],
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.3,
    }));
    let frame = 0;
    function step() {
      frame++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        p.x += p.vx; p.y += p.vy; p.vy += 0.03; p.rot += p.vr;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        ctx.restore();
      });
      if (frame < 140) requestAnimationFrame(step);
      else ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    requestAnimationFrame(step);
  }

  function checkMilestones() {
    allPhases().forEach((p) => {
      const st = phaseStats(p.id);
      if (st.total > 0 && st.pct === 100 && progress.celebratedPhases.indexOf(p.id) === -1) {
        progress.celebratedPhases.push(p.id);
        persist();
        celebrate(p.title);
      }
    });
  }

  // ---------------------------------------------------------
  // Task detail modal
  // ---------------------------------------------------------
  function openEditModal(id) {
    const entry = indexEntry(id);
    const item = getItem(id);
    const host = document.getElementById("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>${esc(entry.title)}</h2>
      <p style="font-size:12px; color:var(--text-faint); margin-top:-10px;">Month ${entry.phaseNumber} · ${esc(entry.sectionTitle || "")} ${entry.topicTitle ? "· " + esc(entry.topicTitle) : ""}</p>
      <div class="field">
        <label>Status</label>
        <select id="modalStatus">${STATUS.map((s) => `<option value="${s}" ${s === item.status ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}</select>
      </div>
      <div class="field">
        <label>Due date / target week</label>
        <input type="date" id="modalDue" value="${item.dueDate || ""}" />
      </div>
      <div class="field">
        <label>Resource link (course, doc, repo)</label>
        <input type="url" id="modalLink" placeholder="https://…" value="${esc(item.link)}" />
      </div>
      <div class="field">
        <label>Notes</label>
        <textarea id="modalNotes" placeholder="e.g. revisit this, found a great resource…">${esc(item.notes)}</textarea>
      </div>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-primary" data-action="save-modal" data-id="${id}">Save</button>
      </div>
    `;
    host.classList.remove("hidden");
  }
  function closeModal() {
    document.getElementById("modalHost").classList.add("hidden");
  }
  function saveModal(id) {
    const status = document.getElementById("modalStatus").value;
    const dueDate = document.getElementById("modalDue").value || null;
    const link = document.getElementById("modalLink").value.trim();
    const notes = document.getElementById("modalNotes").value;
    setItemFields(id, { status, dueDate, link, notes });
    closeModal();
    rerender();
    checkMilestones();
  }

  // ---------------------------------------------------------
  // App state & main render switch
  // ---------------------------------------------------------
  const state = { view: "overview", search: "" };

  const VIEW_RENDERERS = {
    overview: renderOverview,
    timeline: renderTimeline,
    kanban: renderKanban,
    checklist: renderChecklist,
    thisweek: renderThisWeek,
    mastery: renderMastery,
    reference: renderReference,
  };

  function rerender() {
    const main = document.getElementById("main");
    VIEW_RENDERERS[state.view](main);
  }

  function setView(view) {
    state.view = view;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
    rerender();
  }

  // ---------------------------------------------------------
  // Theme
  // ---------------------------------------------------------
  function applyTheme(theme) {
    if (theme === "dark" || theme === "light") {
      document.documentElement.setAttribute("data-theme", theme);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    const isDark = theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const lightBtn = document.getElementById("themeLightBtn");
    const darkBtn = document.getElementById("themeDarkBtn");
    if (lightBtn) lightBtn.classList.toggle("active", !isDark);
    if (darkBtn) darkBtn.classList.toggle("active", isDark);
  }
  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    applyTheme(saved);
  }

  // ---------------------------------------------------------
  // Export / Import / Reset
  // ---------------------------------------------------------
  function exportProgress() {
    const payload = Object.assign({ exportedAt: new Date().toISOString(), version: 1 }, progress);
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `roadmap-progress-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("Progress exported.", "success");
  }

  function importProgress(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        const check = window.ProgressSchema.validateProgress(parsed);
        if (!check.ok) {
          throw new Error("File doesn't look like a progress export. " + check.errors.slice(0, 3).join(" "));
        }
        progress = normalizeProgress(parsed);
        persist();
        rebuildIndex();
        rerender();
        toast("Progress imported.", "success");
      } catch (e) {
        toast("Import failed: " + e.message, "error");
      }
    };
    reader.readAsText(file);
  }

  function confirmReset() {
    const host = document.getElementById("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Reset all progress?</h2>
      <p style="font-size:13px; color:var(--text-muted);">This clears every status, note, link, due date and counter you've set. The roadmap structure, your start month and any topics you've added are kept (their tasks go back to "Not started"). This can't be undone — export a backup first if you're not sure.</p>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-danger" data-action="confirm-reset">Reset everything</button>
      </div>
    `;
    host.classList.remove("hidden");
  }
  function doReset() {
    progress = Object.assign(normalizeProgress(null), { settings: progress.settings, custom: progress.custom });
    persist();
    closeModal();
    rerender();
    toast("Progress reset.", "success");
  }

  // ---------------------------------------------------------
  // User-added topics & tasks
  // ---------------------------------------------------------
  function uid(prefix) {
    return prefix + "-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }
  function findSection(sectionId) {
    for (const phase of allPhases()) {
      const section = phase.sections.find((s) => s.id === sectionId);
      if (section) return { phase, section };
    }
    return null;
  }
  function parseTaskLines(text) {
    return String(text || "")
      .split("\n")
      .map((l) => l.trim().replace(/^[-*•]\s*(\[[ xX]\]\s*)?/, "").trim())
      .filter(Boolean);
  }
  function afterCustomChange() {
    persist();
    rebuildIndex();
    rerender();
  }

  function openTopicModal(sectionId) {
    const found = findSection(sectionId);
    if (!found) return;
    const host = document.getElementById("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Add a topic</h2>
      <p style="font-size:12px; color:var(--text-faint); margin-top:-10px;">Month ${found.phase.number} · ${esc(found.section.title)}</p>
      <div class="field">
        <label>Topic title</label>
        <input type="text" id="topicTitleInput" placeholder="e.g. Pydantic v2 validators" maxlength="200" />
      </div>
      <div class="field">
        <label>Target depth (optional)</label>
        <select id="topicDepthInput">
          <option value="">—</option>
          <option value="D3">D3 — Deep / mastery</option>
          <option value="D2/D3">D2/D3</option>
          <option value="D2">D2 — Working proficiency</option>
          <option value="D1">D1 — Awareness</option>
        </select>
      </div>
      <div class="field">
        <label>Tasks — one per line (optional)</label>
        <textarea id="topicTasksInput" placeholder="Read the migration guide&#10;Rewrite one model&#10;Write tests for validators"></textarea>
        <div style="font-size:11.5px; color:var(--text-faint); margin-top:4px;">Leave blank to create a single task named after the topic. You can add more later.</div>
      </div>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-primary" data-action="save-topic" data-section-id="${esc(sectionId)}">Add topic</button>
      </div>
    `;
    host.classList.remove("hidden");
    document.getElementById("topicTitleInput").focus();
  }
  function saveTopic(sectionId) {
    const title = document.getElementById("topicTitleInput").value.trim();
    if (!title) {
      toast("Give the topic a title first.", "error");
      document.getElementById("topicTitleInput").focus();
      return;
    }
    const depth = document.getElementById("topicDepthInput").value || null;
    const lines = parseTaskLines(document.getElementById("topicTasksInput").value);
    const tasks = (lines.length ? lines : [title]).map((t) => ({ id: uid("custom-task"), title: t }));
    progress.custom.topics.push({ id: uid("custom-topic"), sectionId, title, depth, tasks });
    closeModal();
    afterCustomChange();
    toast(`Added "${title}" with ${tasks.length} task${tasks.length === 1 ? "" : "s"}.`, "success");
  }

  function openTasksModal(topicId) {
    const topic = progress.custom.topics.find((t) => t.id === topicId);
    if (!topic) return;
    const host = document.getElementById("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Add tasks to "${esc(topic.title)}"</h2>
      <div class="field">
        <label>Tasks — one per line</label>
        <textarea id="moreTasksInput" placeholder="Add one task per line"></textarea>
      </div>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-primary" data-action="save-tasks" data-topic-id="${esc(topicId)}">Add</button>
      </div>
    `;
    host.classList.remove("hidden");
    document.getElementById("moreTasksInput").focus();
  }
  function saveTasks(topicId) {
    const topic = progress.custom.topics.find((t) => t.id === topicId);
    const lines = parseTaskLines(document.getElementById("moreTasksInput").value);
    if (!topic || !lines.length) { closeModal(); return; }
    lines.forEach((t) => topic.tasks.push({ id: uid("custom-task"), title: t }));
    closeModal();
    afterCustomChange();
    toast(`Added ${lines.length} task${lines.length === 1 ? "" : "s"}.`, "success");
  }

  function deleteTopic(topicId) {
    const topic = progress.custom.topics.find((t) => t.id === topicId);
    if (!topic) return;
    if (!window.confirm(`Delete the topic "${topic.title}" and its ${topic.tasks.length} task(s), including any notes you saved on them?`)) return;
    topic.tasks.forEach((k) => delete progress.items[k.id]);
    progress.custom.topics = progress.custom.topics.filter((t) => t.id !== topicId);
    afterCustomChange();
    toast("Topic deleted.", "success");
  }
  function deleteTask(taskId) {
    const topic = progress.custom.topics.find((t) => t.tasks.some((k) => k.id === taskId));
    if (!topic) return;
    if (!window.confirm("Remove this task?")) return;
    topic.tasks = topic.tasks.filter((k) => k.id !== taskId);
    delete progress.items[taskId];
    afterCustomChange();
  }

  // ---------------------------------------------------------
  // User-added months and sections
  // ---------------------------------------------------------
  function openMonthModal() {
    const n = allPhases().length + 1;
    const host = document.getElementById("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Add a month</h2>
      <p style="font-size:12px; color:var(--text-faint); margin-top:-10px;">
        It becomes <strong>Month ${n}</strong> (${esc(phaseCalendarLabel(n))}), right after your last month.
      </p>
      <div class="field">
        <label>Month title</label>
        <input type="text" id="monthTitleInput" placeholder="e.g. Rust for AI Infrastructure" maxlength="200" />
      </div>
      <div class="field">
        <label>Objective (optional)</label>
        <textarea id="monthObjectiveInput" placeholder="What should be true by the end of this month?"></textarea>
      </div>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-primary" data-action="save-month">Add month</button>
      </div>
    `;
    host.classList.remove("hidden");
    document.getElementById("monthTitleInput").focus();
  }
  function saveMonth() {
    const title = document.getElementById("monthTitleInput").value.trim();
    if (!title) {
      toast("Give the month a title first.", "error");
      document.getElementById("monthTitleInput").focus();
      return;
    }
    const objective = document.getElementById("monthObjectiveInput").value.trim();
    const id = uid("custom-month");
    progress.custom.phases.push({ id, title, objective, sections: [] });
    expandedPhases[id] = true;
    closeModal();
    afterCustomChange();
    toast(`Added "${title}". Add a section to start filling it in.`, "success");
  }

  function openSectionModal(phaseId) {
    const phase = progress.custom.phases.find((p) => p.id === phaseId);
    if (!phase) return;
    const used = phase.sections.map((sec) => sec.weekNumber).filter(Boolean);
    const next = [1, 2, 3, 4].find((w) => used.indexOf(w) === -1) || "";
    const host = document.getElementById("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Add a section</h2>
      <p style="font-size:12px; color:var(--text-faint); margin-top:-10px;">In "${esc(phase.title)}"</p>
      <div class="field">
        <label>Section title</label>
        <input type="text" id="sectionTitleInput" placeholder="e.g. Ownership and borrowing" maxlength="200" />
      </div>
      <div class="field">
        <label>When</label>
        <select id="sectionWeekInput">
          ${[1, 2, 3, 4].map((w) => `<option value="${w}" ${next === w ? "selected" : ""}>Week ${w}${used.indexOf(w) !== -1 ? " (already used)" : ""}</option>`).join("")}
          <option value="" ${next === "" ? "selected" : ""}>Not tied to a week (no dates)</option>
        </select>
        <div style="font-size:11.5px; color:var(--text-faint); margin-top:4px;">
          Weeks are 7-day blocks from the 1st of the month. A dated section shows up in <em>This Week</em> while it's current.
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-primary" data-action="save-section" data-phase-id="${esc(phaseId)}">Add section</button>
      </div>
    `;
    host.classList.remove("hidden");
    document.getElementById("sectionTitleInput").focus();
  }
  function saveSection(phaseId) {
    const phase = progress.custom.phases.find((p) => p.id === phaseId);
    const title = document.getElementById("sectionTitleInput").value.trim();
    if (!phase) { closeModal(); return; }
    if (!title) {
      toast("Give the section a title first.", "error");
      document.getElementById("sectionTitleInput").focus();
      return;
    }
    const week = document.getElementById("sectionWeekInput").value;
    phase.sections.push({ id: uid("custom-section"), title, weekNumber: week ? Number(week) : null });
    closeModal();
    afterCustomChange();
    toast(`Added "${title}". Use "Add topic" inside it.`, "success");
  }

  // Removes the custom topics (and the saved status/notes of their tasks)
  // that live in the given sections. Returns {topics, tasks} removed.
  function removeTopicsInSections(sectionIds) {
    const gone = progress.custom.topics.filter((t) => sectionIds.indexOf(t.sectionId) !== -1);
    let tasks = 0;
    gone.forEach((t) => t.tasks.forEach((k) => { delete progress.items[k.id]; tasks++; }));
    progress.custom.topics = progress.custom.topics.filter((t) => sectionIds.indexOf(t.sectionId) === -1);
    return { topics: gone.length, tasks };
  }
  function countTopicsInSections(sectionIds) {
    const topics = progress.custom.topics.filter((t) => sectionIds.indexOf(t.sectionId) !== -1);
    return { topics: topics.length, tasks: topics.reduce((n, t) => n + t.tasks.length, 0) };
  }

  function deleteMonth(phaseId) {
    const phase = progress.custom.phases.find((p) => p.id === phaseId);
    if (!phase) return;
    const ids = phase.sections.map((sec) => sec.id);
    const c = countTopicsInSections(ids);
    if (!window.confirm(`Delete the month "${phase.title}" with its ${ids.length} section(s), ${c.topics} topic(s) and ${c.tasks} task(s), including any notes you saved on them?`)) return;
    removeTopicsInSections(ids);
    progress.custom.phases = progress.custom.phases.filter((p) => p.id !== phaseId);
    progress.celebratedPhases = progress.celebratedPhases.filter((id) => id !== phaseId);
    delete expandedPhases[phaseId];
    if (kanbanState.phase === phaseId) kanbanState.phase = null;
    if (checklistFilters.phase === phaseId) checklistFilters.phase = "all";
    afterCustomChange();
    toast("Month deleted.", "success");
  }
  function deleteSection(sectionId) {
    const phase = progress.custom.phases.find((p) => p.sections.some((sec) => sec.id === sectionId));
    if (!phase) return;
    const sec = phase.sections.find((x) => x.id === sectionId);
    const c = countTopicsInSections([sectionId]);
    if (!window.confirm(`Delete the section "${sec.title}" with its ${c.topics} topic(s) and ${c.tasks} task(s), including any notes you saved on them?`)) return;
    removeTopicsInSections([sectionId]);
    phase.sections = phase.sections.filter((x) => x.id !== sectionId);
    afterCustomChange();
    toast("Section deleted.", "success");
  }

  function openStartMonthModal() {
    const host = document.getElementById("modalHost");
    const current = getStartMonth();
    host.querySelector(".modal").innerHTML = `
      <h2>When does Month 1 start?</h2>
      <p style="font-size:13px; color:var(--text-muted);">
        The roadmap was written assuming Month 1 = ${esc(phaseCalendarLabelFor(defaultStartMonth()))}.
        Set your real start month and every phase, week and "you are here"
        marker shifts to match — nothing else about your progress changes.
      </p>
      <div class="field">
        <label>Month 1 starts on</label>
        <input type="month" id="startMonthInput" value="${esc(current)}" min="${esc(currentMonthKey())}" />
      </div>
      <p style="font-size:12px; color:var(--text-faint); margin-top:-6px;">
        Only the current month or later can be picked — past months are disabled.
      </p>
      <p style="font-size:12px; color:var(--text-faint); margin-top:-6px;">
        Example: if you pick ${esc(phaseCalendarLabelFor(nextMonthKey(current)))}, Month 2 will fall on ${esc(phaseCalendarLabelFor(nextMonthKey(nextMonthKey(current))))}.
      </p>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-primary" data-action="save-start-month">Save</button>
      </div>
    `;
    host.classList.remove("hidden");
  }
  function phaseCalendarLabelFor(yyyyMm) {
    const [y, m] = yyyyMm.split("-").map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" }).toUpperCase();
  }
  function nextMonthKey(yyyyMm) {
    const [y, m] = yyyyMm.split("-").map(Number);
    const d = addMonths(new Date(y, m - 1, 1), 1);
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
  }
  function saveStartMonth() {
    const val = document.getElementById("startMonthInput").value;
    if (!val) { closeModal(); return; }
    if (val < currentMonthKey()) {
      toast("Start month can't be before the current month.", "error");
      return;
    }
    setStartMonth(val);
    closeModal();
    rerender();
    checkMilestones();
    toast(`Month 1 is now set to ${phaseCalendarLabelFor(val)}.`, "success");
  }

  // ---------------------------------------------------------
  // Event wiring (delegated)
  // ---------------------------------------------------------
  function wireEvents() {
    document.getElementById("tabs").addEventListener("click", (e) => {
      const btn = e.target.closest(".tab");
      if (btn) setView(btn.dataset.view);
    });

    // Profile panel toggle
    const profileTrigger = document.getElementById("profileTrigger");
    const profilePanel = document.getElementById("profilePanel");
    const closePanel = () => {
      profilePanel.classList.add("hidden");
      profileTrigger.setAttribute("aria-expanded", "false");
    };

    profileTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const opening = profilePanel.classList.contains("hidden");
      if (opening) {
        document.getElementById("legacyImportBtn").classList.toggle("hidden", !readLegacyLocalData());
      }
      profilePanel.classList.toggle("hidden", !opening);
      profileTrigger.setAttribute("aria-expanded", String(opening));
    });
    document.addEventListener("click", (e) => {
      if (!profilePanel.classList.contains("hidden") &&
          !document.getElementById("profileAnchor").contains(e.target)) {
        closePanel();
      }
    });

    // Theme
    document.getElementById("themeLightBtn").addEventListener("click", () => {
      localStorage.setItem(THEME_KEY, "light");
      applyTheme("light");
    });
    document.getElementById("themeDarkBtn").addEventListener("click", () => {
      localStorage.setItem(THEME_KEY, "dark");
      applyTheme("dark");
    });

    // Search (always visible inside profile panel)
    const panelSearch = document.getElementById("panelSearch");
    panelSearch.addEventListener("input", () => {
      state.search = panelSearch.value;
      rerender();
    });

    // Data actions
    document.getElementById("legacyImportBtn").addEventListener("click", () => {
      closePanel();
      openLegacyModal(session.version > 0);
    });
    document.getElementById("exportBtn").addEventListener("click", () => {
      exportProgress();
      closePanel();
    });
    document.getElementById("importBtn").addEventListener("click", () => {
      document.getElementById("importFile").click();
      closePanel();
    });
    document.getElementById("importFile").addEventListener("change", (e) => {
      if (e.target.files[0]) importProgress(e.target.files[0]);
      e.target.value = "";
    });
    document.getElementById("resetBtn").addEventListener("click", () => {
      confirmReset();
      closePanel();
    });
    document.getElementById("startMonthBtn").addEventListener("click", () => {
      openStartMonthModal();
      closePanel();
    });

    document.getElementById("modalHost").addEventListener("click", (e) => {
      if (e.target.classList.contains("modal-backdrop")) closeModal();
    });

    // Main delegated handler for all view content
    document.getElementById("main").addEventListener("click", onMainClick);
    document.getElementById("main").addEventListener("change", onMainChange);
    document.getElementById("modalHost").addEventListener("click", onModalClick);

    // Kanban drag & drop (delegated)
    document.getElementById("main").addEventListener("dragstart", (e) => {
      const card = e.target.closest(".kanban-card");
      if (card) {
        e.dataTransfer.setData("text/plain", card.dataset.id);
        card.classList.add("drag-ghost");
      }
    });
    document.getElementById("main").addEventListener("dragend", (e) => {
      const card = e.target.closest(".kanban-card");
      if (card) card.classList.remove("drag-ghost");
    });
    document.getElementById("main").addEventListener("dragover", (e) => {
      const col = e.target.closest(".kanban-col");
      if (col) { e.preventDefault(); col.classList.add("drag-over"); }
    });
    document.getElementById("main").addEventListener("dragleave", (e) => {
      const col = e.target.closest(".kanban-col");
      if (col) col.classList.remove("drag-over");
    });
    document.getElementById("main").addEventListener("drop", (e) => {
      const col = e.target.closest(".kanban-col");
      if (!col) return;
      e.preventDefault();
      col.classList.remove("drag-over");
      const id = e.dataTransfer.getData("text/plain");
      if (id) {
        setItemFields(id, { status: col.dataset.status });
        rerender();
        checkMilestones();
      }
    });
  }

  function onModalClick(e) {
    const action = e.target.dataset.action;
    if (action === "close-modal") closeModal();
    if (action === "save-modal") saveModal(e.target.dataset.id);
    if (action === "confirm-reset") doReset();
    if (action === "confirm-delete-roadmap") deleteRoadmap(Number(e.target.dataset.id));
    if (action === "save-start-month") saveStartMonth();
    if (action === "conflict-load") resolveConflictLoadServer();
    if (action === "conflict-overwrite") resolveConflictOverwrite();
    if (action === "legacy-import") importLegacyData();
    if (action === "save-month") saveMonth();
    if (action === "save-section") saveSection(e.target.dataset.phaseId);
    if (action === "save-topic") saveTopic(e.target.dataset.sectionId);
    if (action === "save-tasks") saveTasks(e.target.dataset.topicId);
  }

  function onMainClick(e) {
    const t = e.target;
    const action = t.dataset.action;
    if (!action) return;

    switch (action) {
      case "toggle-phase":
        expandedPhases[t.dataset.id] = !expandedPhases[t.dataset.id];
        rerender();
        break;
      case "toggle-section":
        sectionOpenState[t.dataset.id] = sectionOpenState[t.dataset.id] === false ? true : false;
        rerender();
        break;
      case "open-edit":
        openEditModal(t.dataset.id);
        break;
      case "add-month":
        openMonthModal();
        break;
      case "add-section":
        openSectionModal(t.dataset.phaseId);
        break;
      case "delete-month":
        deleteMonth(t.dataset.id);
        break;
      case "delete-section":
        deleteSection(t.dataset.id);
        break;
      case "add-topic":
        openTopicModal(t.dataset.sectionId);
        break;
      case "add-task":
        openTasksModal(t.dataset.topicId);
        break;
      case "delete-topic":
        deleteTopic(t.dataset.topicId);
        break;
      case "delete-task":
        deleteTask(t.dataset.id);
        break;
      case "filter-status":
        checklistFilters.status = t.dataset.value;
        rerender();
        break;
      case "counter-inc":
        setCounter(t.dataset.id, getCounter(t.dataset.id, 0) + 1);
        rerender();
        break;
      case "counter-dec":
        setCounter(t.dataset.id, getCounter(t.dataset.id, 0) - 1);
        rerender();
        break;
      default:
        break;
    }
  }

  function onMainChange(e) {
    const t = e.target;
    const action = t.dataset.action;
    if (action === "toggle-complete") {
      const id = t.dataset.id;
      setItemFields(id, { status: t.checked ? "completed" : "not_started" });
      rerender();
      checkMilestones();
      return;
    }
    if (action === "set-status") {
      setItemFields(t.dataset.id, { status: t.value });
      rerender();
      checkMilestones();
      return;
    }
    if (action === "filter-phase") {
      checklistFilters.phase = t.value;
      rerender();
      return;
    }
    if (action === "kanban-phase") {
      kanbanState.phase = t.value;
      rerender();
      return;
    }
  }

  // ---------------------------------------------------------
  // Server sync (debounced autosave with optimistic versioning)
  // ---------------------------------------------------------
  const SAVE_DEBOUNCE_MS = 1500;
  const RETRY_DELAYS_MS = [2000, 5000, 15000];

  const session = {
    username: null,     // set while authenticated; persist() is a no-op without it
    roadmapId: null,    // the open roadmap; null while on the dashboard
    version: 0,         // server version our copy is based on
    dirty: false,       // local changes not yet confirmed saved
    saving: false,      // a PUT is in flight
    conflict: false,    // server has a newer copy; autosave paused until resolved
    conflictServer: null,
    retries: 0,
    timer: null,
    expiredFor: null,
  };

  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const SAVE_LABELS = {
    idle: "", saving: "Saving…", saved: "Saved",
    error: "Save failed — click to retry", conflict: "Conflict — click to resolve",
  };
  function setSaveStatus(kind, detail) {
    const el = $("panelSaveStatus");
    el.className = "profile-panel-save " + kind;
    el.textContent = SAVE_LABELS[kind];
    el.title = detail || "";
    el.dataset.kind = kind;
  }

  function scheduleSave(delay) {
    clearTimeout(session.timer);
    if (session.conflict) return;
    setSaveStatus("saving");
    session.timer = setTimeout(flushSave, delay);
  }

  async function flushSave() {
    if (session.saving || !session.dirty || session.conflict || !session.username || session.roadmapId == null) return;
    clearTimeout(session.timer);
    session.saving = true;
    session.dirty = false;
    setSaveStatus("saving");
    const snapshot = JSON.parse(JSON.stringify(progress));
    try {
      const r = await window.RoadmapApi.putProgress(session.roadmapId, snapshot, session.version);
      session.version = r.version;
      session.retries = 0;
      session.saving = false;
      if (session.dirty) scheduleSave(SAVE_DEBOUNCE_MS); // edited while the request was in flight
      else setSaveStatus("saved", "Last saved " + new Date(r.updatedAt).toLocaleTimeString());
    } catch (e) {
      session.saving = false;
      session.dirty = true;
      if (e.status === 409) {
        session.conflict = true;
        session.conflictServer = e.body && e.body.server;
        setSaveStatus("conflict");
        openConflictModal();
      } else if (e.status === 401) {
        handleSessionExpired();
      } else if (e.status === 400 || e.status === 413) {
        setSaveStatus("error", e.message);
        toast("Couldn't save: " + e.message, "error");
      } else if (session.retries < RETRY_DELAYS_MS.length) {
        setSaveStatus("saving", "Retrying…");
        session.timer = setTimeout(flushSave, RETRY_DELAYS_MS[session.retries++]);
      } else {
        setSaveStatus("error", e.message);
        toast("Couldn't save your changes: " + e.message, "error");
      }
    }
  }

  async function flushNow() {
    clearTimeout(session.timer);
    while (session.saving) await sleep(50);
    await flushSave();
    while (session.saving) await sleep(50);
  }

  function openConflictModal() {
    const srv = session.conflictServer;
    const when = srv && srv.updatedAt ? new Date(srv.updatedAt).toLocaleString() : "earlier";
    const host = $("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Your data changed somewhere else</h2>
      <p style="font-size:13px; color:var(--text-muted); line-height:1.5;">
        The copy saved on the server (last updated ${esc(when)}) is newer than the one this
        page started from — probably from another device or browser tab. Autosave is paused until you choose:
      </p>
      <ul style="font-size:13px; color:var(--text-muted); line-height:1.5; padding-left:18px;">
        <li><strong>Load server version</strong> — replaces what's on this screen; your unsaved changes here are discarded.</li>
        <li><strong>Overwrite with mine</strong> — saves this screen's data over the server copy.</li>
      </ul>
      <div class="modal-actions">
        <button class="btn" data-action="conflict-load">Load server version</button>
        <button class="btn btn-danger" data-action="conflict-overwrite">Overwrite with mine</button>
      </div>
    `;
    host.classList.remove("hidden");
  }
  function resolveConflictLoadServer() {
    const srv = session.conflictServer || { data: null, version: 0 };
    progress = normalizeProgress(srv.data);
    session.version = srv.version || 0;
    session.dirty = false;
    session.conflict = false;
    session.conflictServer = null;
    closeModal();
    rebuildIndex();
    rerender();
    setSaveStatus("saved");
    toast("Loaded the server version.", "success");
  }
  function resolveConflictOverwrite() {
    const srv = session.conflictServer || { version: 0 };
    session.version = srv.version || 0;
    session.conflict = false;
    session.conflictServer = null;
    session.dirty = true;
    closeModal();
    flushSave();
  }

  // ---------------------------------------------------------
  // Login / register / session
  // ---------------------------------------------------------
  let authMode = "login";

  function lockApp() { document.body.classList.add("locked"); }
  function unlockApp() { document.body.classList.remove("locked"); }

  function setAuthMode(mode) {
    authMode = mode;
    const reg = mode === "register";
    $("authTitle").textContent = reg ? "Create your account" : "Log in";
    $("authSubmit").textContent = reg ? "Create account" : "Log in";
    $("authToggleText").textContent = reg ? "Already have an account?" : "New here?";
    $("authToggle").textContent = reg ? "Log in" : "Create an account";
    $("authHint").classList.toggle("hidden", !reg);
    $("authPassword").autocomplete = reg ? "new-password" : "current-password";
    $("authError").textContent = "";
    $("authRegisterFields").classList.toggle("hidden", !reg);
    $("authConfirmPasswordField").classList.toggle("hidden", !reg);
    $("authUsernameLabel").textContent = reg ? "User ID" : "Username";
    $("authUsernameStatus").textContent = "";
    $("authUsernameStatus").className = "auth-field-hint";
    $("authPasswordMatch").textContent = "";
    $("authPasswordMatch").className = "auth-field-hint";
    if (!reg) {
      $("authFirstName").value = "";
      $("authLastName").value = "";
      $("authConfirmPassword").value = "";
    }
  }

  function showAuth(mode, notice, opts) {
    opts = opts || {};
    lockApp();
    hideDashboard();
    setAuthMode(mode || "login");
    const n = $("authNotice");
    n.textContent = notice || "";
    n.classList.toggle("hidden", !notice);
    $("authDownload").classList.toggle("hidden", !opts.offerDownload);
    $("authPassword").value = "";
    $("authBlock").classList.add("hidden");
    $("authForm").classList.remove("hidden");
    $("authScreen").classList.remove("hidden");
    $("authUsername").focus();
  }
  function hideAuth() { $("authScreen").classList.add("hidden"); }

  // buttons: [[label, handler], ...]
  function showBlock(title, text, buttons) {
    lockApp();
    $("authBlockTitle").textContent = title;
    $("authBlockText").textContent = text || "";
    $("authBlockText").classList.toggle("hidden", !text);
    const box = $("authBlockActions");
    box.innerHTML = "";
    (buttons || []).forEach(([label, fn], i) => {
      const b = document.createElement("button");
      b.className = "btn" + (i === 0 ? " btn-primary" : "");
      b.type = "button";
      b.textContent = label;
      b.addEventListener("click", fn);
      box.appendChild(b);
    });
    $("authForm").classList.add("hidden");
    $("authBlock").classList.remove("hidden");
    $("authScreen").classList.remove("hidden");
  }

  async function submitAuth(ev) {
    ev.preventDefault();
    const username = $("authUsername").value.trim();
    const password = $("authPassword").value;
    const err = $("authError");
    err.textContent = "";
    if (!username || !password) { err.textContent = "Enter a username and password."; return; }
    if (authMode === "register") {
      const firstName = $("authFirstName").value.trim();
      const lastName  = $("authLastName").value.trim();
      const confirmPassword = $("authConfirmPassword").value;
      if (!firstName) { err.textContent = "Please enter your first name."; return; }
      if (!lastName)  { err.textContent = "Please enter your last name."; return; }
      if (!/^[A-Za-z0-9_-]{3,32}$/.test(username)) { err.textContent = "User ID must be 3–32 characters: letters, numbers, _ or -."; return; }
      if (password.length < 8) { err.textContent = "Password must be at least 8 characters."; return; }
      if (password !== confirmPassword) { err.textContent = "Passwords do not match."; return; }
    }
    const btn = $("authSubmit");
    btn.disabled = true;
    try {
      let res;
      if (authMode === "register") {
        const firstName = $("authFirstName").value.trim();
        const lastName  = $("authLastName").value.trim();
        res = await window.AuthApi.register(firstName, lastName, username, password);
      } else {
        res = await window.AuthApi.login(username, password);
      }
      $("authPassword").value = "";
      $("authConfirmPassword").value = "";
      session.expiredFor = null;
      enterDashboard(res.user);
    } catch (e) {
      err.textContent = e.message;
    } finally {
      btn.disabled = false;
    }
  }

  async function boot() {
    showBlock("Loading…", "");
    let me;
    try {
      me = await window.AuthApi.me();
    } catch (e) {
      if (e.status === 401) { showAuth("login"); return; }
      showBlock("Can't reach the server", e.message, [["Retry", boot]]);
      return;
    }
    enterDashboard(me.user);
  }

  // Reset every piece of per-roadmap sync state; the account fields are kept.
  function resetRoadmapSession(roadmapId, version) {
    clearTimeout(session.timer);
    Object.assign(session, { roadmapId, version, dirty: false, saving: false,
      conflict: false, conflictServer: null, retries: 0, expiredFor: null });
  }

  // Called once the user is authenticated: lands them on the roadmap dashboard.
  function enterDashboard(user) {
    const firstName = user.firstName || "";
    const lastName = user.lastName || "";
    Object.assign(session, { username: user.username, firstName, lastName });
    resetRoadmapSession(null, 0);
    progress = normalizeProgress(null);
    const fullName = [firstName, lastName].filter(Boolean).join(" ") || user.username;
    $("profileName").textContent = fullName;
    $("panelFullName").textContent = fullName;
    $("panelUsername").textContent = "@" + user.username;
    $("dashboardGreeting").textContent = "Signed in as " + fullName;
    hideAuth();
    showDashboard();
  }

  // ---------------------------------------------------------
  // Roadmap dashboard (post-login landing page)
  // ---------------------------------------------------------
  let dashboardRoadmaps = [];

  function hideDashboard() { $("dashboardScreen").classList.add("hidden"); }

  async function showDashboard() {
    lockApp();
    document.title = "Roadmap Tracker";
    $("dashboardScreen").classList.remove("hidden");
    $("dashboardContent").innerHTML = `<p class="dashboard-status">Loading your roadmaps…</p>`;
    let res;
    try {
      res = await window.RoadmapApi.list();
    } catch (e) {
      if (e.status === 401) { handleSessionExpired(); return; }
      $("dashboardContent").innerHTML = `
        <div class="dashboard-status">
          <p>Couldn't load your roadmaps: ${esc(e.message)}</p>
          <button type="button" class="btn btn-primary" data-action="retry-dashboard">Retry</button>
        </div>`;
      return;
    }
    renderDashboard(res.roadmaps);
  }

  function describeActivity(iso) {
    if (!iso) return "Not started yet";
    const days = daysBetween(new Date(iso), new Date());
    if (days <= 0) return "Last activity today";
    if (days === 1) return "Last activity yesterday";
    return "Last activity " + days + " days ago";
  }

  function renderDashboard(roadmaps) {
    const cards = roadmaps.map((r) => `
      <article class="roadmap-card">
        <div>
          <h3>${esc(r.name)}</h3>
          ${r.description ? `<p class="roadmap-card-desc">${esc(r.description)}</p>` : ""}
          <p class="roadmap-card-meta">${esc(describeActivity(r.lastActivityAt))}</p>
        </div>
        <div class="roadmap-card-actions">
          <button type="button" class="btn btn-primary btn-open" data-action="open-roadmap" data-id="${r.id}">Open</button>
          <button type="button" class="btn btn-ghost-danger" data-action="delete-roadmap" data-id="${r.id}"
                  aria-label="Delete ${esc(r.name)}">Delete</button>
        </div>
      </article>`);

    // Offer the starter roadmap back whenever the account no longer has it.
    const restore = roadmaps.some((r) => r.source === "builtin_ai_engineer") ? "" : `
      <button type="button" class="roadmap-card action" data-action="restore-builtin">
        <span class="action-title">↺ Restore AI Engineer Roadmap</span>
        <span class="action-desc">Bring back the 10-month starter roadmap with fresh progress.</span>
      </button>`;

    $("dashboardContent").innerHTML = `
      <h2>Your roadmaps</h2>
      <p class="dashboard-lead">${roadmaps.length
        ? "Pick up where you left off."
        : "You don't have any roadmaps yet."}</p>
      <div class="roadmap-grid">
        ${cards.join("")}
        ${restore}
        <button type="button" class="roadmap-card action" disabled>
          <span class="action-title">+ Create new roadmap <span class="coming-soon-badge">Coming soon</span></span>
          <span class="action-desc">Build your own plan: months, modules and tasks.</span>
        </button>
        <button type="button" class="roadmap-card action" disabled>
          <span class="action-title">✦ Create roadmap with AI <span class="coming-soon-badge">Coming soon</span></span>
          <span class="action-desc">Describe a goal and let AI draft the plan.</span>
        </button>
      </div>`;
    dashboardRoadmaps = roadmaps;
  }

  async function restoreBuiltinRoadmap() {
    try {
      await window.RoadmapApi.restoreBuiltin();
      toast("AI Engineer Roadmap restored.", "success");
    } catch (e) {
      if (e.status === 401) { handleSessionExpired(); return; }
      if (e.status !== 409) { toast("Couldn't restore the roadmap: " + e.message, "error"); return; }
    }
    showDashboard();
  }

  function confirmDeleteRoadmap(id) {
    const roadmap = dashboardRoadmaps.find((r) => String(r.id) === String(id));
    if (!roadmap) return;
    const host = $("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Delete “${esc(roadmap.name)}”?</h2>
      <p style="font-size:13px; color:var(--text-muted); line-height:1.5;">
        This permanently deletes the roadmap and all of its progress — statuses, notes, links, due dates
        and anything you added. This can't be undone.
      </p>
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">Cancel</button>
        <button class="btn btn-danger" data-action="confirm-delete-roadmap" data-id="${roadmap.id}">Delete roadmap</button>
      </div>`;
    host.classList.remove("hidden");
  }

  async function deleteRoadmap(id) {
    closeModal();
    try {
      await window.RoadmapApi.remove(id);
      toast("Roadmap deleted.", "success");
    } catch (e) {
      if (e.status === 401) { handleSessionExpired(); return; }
      if (e.status !== 404) { toast("Couldn't delete the roadmap: " + e.message, "error"); return; }
    }
    showDashboard();
  }

  async function openRoadmap(id) {
    hideDashboard();
    showBlock("Loading roadmap…", "");
    let res;
    try {
      res = await window.RoadmapApi.getProgress(id);
    } catch (e) {
      if (e.status === 401) { showAuth("login"); return; }
      // Never fall through to an empty editable state: saving it would overwrite real data.
      showBlock("Couldn't load this roadmap", e.message, [
        ["Retry", () => openRoadmap(id)],
        ["Back to roadmaps", () => { hideAuth(); showDashboard(); }],
      ]);
      return;
    }
    resetRoadmapSession(res.roadmap.id, res.version || 0);
    progress = normalizeProgress(res.data);
    rebuildIndex();
    hideAuth();
    unlockApp();
    $("roadmapTitle").textContent = res.roadmap.name;
    $("roadmapSubtitle").textContent = res.roadmap.description;
    document.title = res.roadmap.name + " — Roadmap Tracker";
    state.search = "";
    $("panelSearch").value = "";
    setSaveStatus("saved");
    setView("overview");
    checkMilestones();
    if (res.data === null && res.roadmap.source === "builtin_ai_engineer" && readLegacyLocalData()) {
      openLegacyModal(false);
    }
  }

  // Flush pending edits before leaving the open roadmap; false if the user chose to stay.
  async function settleUnsavedChanges(verb) {
    if (session.username && session.roadmapId != null && (session.dirty || session.saving)) {
      await flushNow();
      if (session.dirty && !window.confirm(`Some changes haven't been saved yet. ${verb} anyway and lose them?`)) return false;
    }
    return true;
  }

  async function backToDashboard() {
    if (!(await settleUnsavedChanges("Leave"))) return;
    resetRoadmapSession(null, 0);
    progress = normalizeProgress(null);
    closeModal();
    showDashboard();
  }

  function onDashboardClick(e) {
    const el = e.target.closest("[data-action]");
    if (!el) return;
    switch (el.dataset.action) {
      case "open-roadmap": openRoadmap(Number(el.dataset.id)); break;
      case "delete-roadmap": confirmDeleteRoadmap(el.dataset.id); break;
      case "restore-builtin": restoreBuiltinRoadmap(); break;
      case "retry-dashboard": showDashboard(); break;
      default: break;
    }
  }

  function handleSessionExpired() {
    const hadRoadmap = session.roadmapId != null;
    clearTimeout(session.timer);
    session.expiredFor = session.username;
    session.username = null;
    setSaveStatus("idle");
    closeModal();
    showAuth("login",
      hadRoadmap
        ? "Your session expired, so your latest changes couldn't be saved. Log in again to keep working. " +
          "If you made changes you want to keep, download them first."
        : "Your session expired. Log in again to continue.",
      { offerDownload: hadRoadmap });
  }

  async function logout() {
    if (!(await settleUnsavedChanges("Log out"))) return;
    try { await window.AuthApi.logout(); } catch (e) { /* cookie may already be gone */ }
    // A full reload drops every piece of in-memory, user-specific state.
    window.location.reload();
  }

  // ---------------------------------------------------------
  // One-time migration of old browser-stored data
  // ---------------------------------------------------------
  function openLegacyModal(replacing) {
    const legacy = readLegacyLocalData();
    if (!legacy) return;
    const tasks = Object.keys(legacy.items).length;
    const topics = legacy.custom.topics.length;
    const summary = `${tasks} task${tasks === 1 ? "" : "s"} with saved status or notes` +
      (topics ? `, ${topics} custom topic${topics === 1 ? "" : "s"}` : "");
    const host = $("modalHost");
    host.querySelector(".modal").innerHTML = `
      <h2>Import existing local data into your account?</h2>
      <p style="font-size:13px; color:var(--text-muted); line-height:1.5;">
        This browser still has progress saved from before accounts existed (${esc(summary)}).
        Importing uploads it to your account so you can reach it from any computer.
        Your browser's copy is <strong>not deleted</strong>.
      </p>
      ${replacing ? `<p style="font-size:13px; color:var(--status-blocked); line-height:1.5;">
        Your account already has saved data — importing will <strong>replace</strong> it with the old browser data.</p>` : ""}
      <div class="modal-actions">
        <button class="btn" data-action="close-modal">${replacing ? "Cancel" : "Not now"}</button>
        <button class="btn btn-primary" data-action="legacy-import">Import into my account</button>
      </div>
    `;
    host.classList.remove("hidden");
  }
  function importLegacyData() {
    const legacy = readLegacyLocalData();
    closeModal();
    if (!legacy) { toast("No usable local data found.", "error"); return; }
    progress = legacy;
    rebuildIndex();
    rerender();
    persist();
    toast("Imported your local data — saving to your account…", "success");
  }

  function debounce(fn, delay) {
    let t;
    return function (...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay); };
  }

  function wireSyncEvents() {
    $("authForm").addEventListener("submit", submitAuth);
    $("authToggle").addEventListener("click", () => setAuthMode(authMode === "login" ? "register" : "login"));
    $("authDownload").addEventListener("click", exportProgress);

    // Live username availability check (register mode only)
    $("authUsername").addEventListener("input", debounce(async () => {
      if (authMode !== "register") return;
      const val = $("authUsername").value.trim();
      const el = $("authUsernameStatus");
      if (val.length < 3 || !/^[A-Za-z0-9_-]{1,32}$/.test(val)) {
        el.textContent = "";
        el.className = "auth-field-hint";
        return;
      }
      el.textContent = "Checking…";
      el.className = "auth-field-hint checking";
      try {
        const r = await window.AuthApi.checkUsername(val);
        if ($("authUsername").value.trim() !== val) return; // stale
        el.textContent = r.available ? "✓ Available" : "✗ Already taken";
        el.className = "auth-field-hint " + (r.available ? "available" : "taken");
      } catch { el.textContent = ""; el.className = "auth-field-hint"; }
    }, 400));

    // Live password match indicator
    function updatePasswordMatch() {
      if (authMode !== "register") return;
      const pw  = $("authPassword").value;
      const cpw = $("authConfirmPassword").value;
      const el  = $("authPasswordMatch");
      if (!pw || !cpw) { el.textContent = ""; el.className = "auth-field-hint"; return; }
      const match = pw === cpw;
      el.textContent = match ? "✓ Passwords match" : "✗ Passwords do not match";
      el.className = "auth-field-hint " + (match ? "match" : "mismatch");
    }
    $("authPassword").addEventListener("input", updatePasswordMatch);
    $("authConfirmPassword").addEventListener("input", updatePasswordMatch);
    $("logoutBtn").addEventListener("click", logout);
    $("dashboardLogoutBtn").addEventListener("click", logout);
    $("backToDashboardBtn").addEventListener("click", backToDashboard);
    $("dashboardContent").addEventListener("click", onDashboardClick);
    $("panelSaveStatus").addEventListener("click", () => {
      const kind = $("panelSaveStatus").dataset.kind;
      if (kind === "error") { session.retries = 0; flushSave(); }
      if (kind === "conflict") openConflictModal();
    });
    window.addEventListener("beforeunload", (e) => {
      if (session.dirty || session.saving) { e.preventDefault(); e.returnValue = ""; }
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden" && session.dirty) flushSave();
    });
    window.addEventListener("online", () => {
      if (session.dirty && !session.conflict) { session.retries = 0; flushSave(); }
    });
  }

  // ---------------------------------------------------------
  // Init
  // ---------------------------------------------------------
  function init() {
    if (!DATA) {
      document.getElementById("main").innerHTML = emptyState("Could not load roadmap data (data/roadmap.js missing).");
      return;
    }
    const footerYear = document.getElementById("authFooterYear");
    if (footerYear) footerYear.textContent = new Date().getFullYear();
    initTheme();
    wireEvents();
    wireSyncEvents();
    boot();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
