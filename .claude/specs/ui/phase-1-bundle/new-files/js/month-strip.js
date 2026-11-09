/**
 * @module month-strip
 * The Month Strip: one segment per month of a roadmap, each a tiny stacked bar
 * of that month's tasks (completed · in progress · blocked · remaining).
 *
 *   MonthStrip.html(months, { size: "sm" | "md" | "lg", labels: false, animate: false })
 *
 * `months` is an array of
 *   { label: "Oct", title: "Month 1: Software Engineering Upgrade",
 *     total, completed, inProgress, blocked, current?: boolean }
 *
 * Returns an HTML string that is safe to insert with innerHTML: every text value
 * is escaped here. Styling lives in css/components.css (.strip*).
 * More than 12 months collapses into one continuous bar; no months renders a
 * dashed empty strip.
 */
(function () {
  "use strict";

  const MAX_SEGMENTS = 12;

  function esc(value) {
    return String(value).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  const num = (v) => (Number.isFinite(Number(v)) && Number(v) > 0 ? Number(v) : 0);

  function parts(m) {
    const total = num(m.total);
    if (!total) return "";
    const pct = (n) => Math.min(100, (num(n) / total) * 100).toFixed(2);
    return [
      ["is-done", m.completed],
      ["is-progress", m.inProgress],
      ["is-blocked", m.blocked],
    ].filter(([, n]) => num(n) > 0)
      .map(([cls, n]) => `<i class="strip-part ${cls}" style="flex-basis:${pct(n)}%"></i>`)
      .join("");
  }

  function summary(months) {
    const total = months.reduce((s, m) => s + num(m.total), 0);
    const done = months.reduce((s, m) => s + num(m.completed), 0);
    return `${done} of ${total} tasks complete across ${months.length} ${months.length === 1 ? "month" : "months"}`;
  }

  function collapse(months) {
    const sum = (key) => months.reduce((s, m) => s + num(m[key]), 0);
    return [{
      label: "", title: "All months", total: sum("total"), completed: sum("completed"),
      inProgress: sum("inProgress"), blocked: sum("blocked"), current: false,
    }];
  }

  function html(months, options) {
    const o = options || {};
    const size = ["sm", "md", "lg"].includes(o.size) ? o.size : "md";
    const list = Array.isArray(months) ? months : [];
    const cls = `strip strip-${size}${o.animate ? " is-animated" : ""}`;

    if (list.length === 0) {
      return `<div class="${cls} is-empty" role="img" aria-label="No months yet"></div>`;
    }
    const shown = list.length > MAX_SEGMENTS ? collapse(list) : list;
    const showLabels = o.labels && shown === list;
    const cols = shown.map((m) => `
      <div class="strip-col${m.current ? " is-current" : ""}">
        <div class="strip-seg" title="${esc(m.title || m.label || "")}">${parts(m)}</div>
        ${showLabels ? `<span class="strip-label">${esc(m.label || "")}</span>` : ""}
      </div>`).join("");
    return `<div class="${cls}" role="img" aria-label="${esc(summary(list))}">${cols}</div>`;
  }

  window.MonthStrip = { html };
})();
