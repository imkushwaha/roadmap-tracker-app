/**
 * @module theme-boot
 * Resolves the appearance setting (light / dark / system) and applies it to
 * <html data-theme="…"> before first paint, so dark-theme users never see a
 * white flash. Loaded synchronously from <head> as an external file because
 * the Content Security Policy forbids inline scripts.
 *
 * Exposes `window.Theme` for the account menu:
 *   Theme.get()        → "light" | "dark" | "system"  (the saved choice)
 *   Theme.resolved()   → "light" | "dark"             (what is on screen)
 *   Theme.set(mode)    → saves, applies, notifies listeners
 *   Theme.onChange(fn) → fn(mode, resolved) on every change (incl. OS change)
 *
 * Storage: localStorage key "roadmap-dashboard:theme". A missing or unknown
 * value means "system". Only the appearance preference is stored here — never
 * tokens or personal data.
 */
(function () {
  "use strict";

  const KEY = "roadmap-dashboard:theme";
  const MODES = ["light", "dark", "system"];
  const listeners = [];
  const query = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function read() {
    try {
      const saved = localStorage.getItem(KEY);
      return MODES.includes(saved) ? saved : "system";
    } catch {
      return "system"; // storage blocked (private mode, policy)
    }
  }

  function resolve(mode) {
    if (mode === "light" || mode === "dark") return mode;
    return query && query.matches ? "dark" : "light";
  }

  function apply() {
    const mode = read();
    const resolved = resolve(mode);
    document.documentElement.setAttribute("data-theme", resolved);
    listeners.forEach((fn) => fn(mode, resolved));
  }

  function set(mode) {
    if (!MODES.includes(mode)) return;
    try { localStorage.setItem(KEY, mode); } catch { /* ignore: still applies for this visit */ }
    apply();
  }

  if (query) {
    const onOsChange = () => { if (read() === "system") apply(); };
    if (query.addEventListener) query.addEventListener("change", onOsChange);
    else if (query.addListener) query.addListener(onOsChange);
  }

  window.Theme = {
    get: read,
    resolved: () => resolve(read()),
    set,
    onChange(fn) { listeners.push(fn); },
  };

  apply();
})();
