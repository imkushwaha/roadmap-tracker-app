/**
 * @module api
 * Thin HTTP wrappers around the backend REST API.
 *
 * Exposes two focused namespaces — AuthApi and RoadmapApi.
 * No application state lives here; callers are responsible for state management.
 */
(function () {
  "use strict";

  /**
   * @typedef {{ username: string }} UserInfo
   * @typedef {{ user: UserInfo }} AuthResponse
   * @typedef {{ id: number, name: string, description: string, source: string, createdAt: string, lastActivityAt?: string|null }} RoadmapSummary
   * @typedef {{ roadmap: RoadmapSummary, data: object|null, version: number, updatedAt?: string }} ProgressResponse
   * @typedef {{ version: number, updatedAt: string }} SaveResponse
   */

  /**
   * Low-level HTTP fetch wrapper — single point of error normalisation.
   *
   * Network errors set `err.network = true` on the thrown Error.
   * HTTP error responses set `err.status` and `err.body`.
   *
   * @param {'GET'|'POST'|'PUT'|'DELETE'} method
   * @param {string} path
   * @param {object} [body]
   * @returns {Promise<object|null>}
   */
  async function call(method, path, body) {
    let res;
    try {
      res = await fetch(path, {
        method,
        credentials: "same-origin",
        headers: body !== undefined ? { "content-type": "application/json" } : {},
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch {
      const err = new Error(
        "Can't reach the server. Check your connection and that the server is running."
      );
      err.network = true;
      throw err;
    }
    let json = null;
    try { json = await res.json(); } catch { /* 204 or non-JSON body */ }
    if (!res.ok) {
      const err = new Error((json && json.error) || `Request failed (${res.status})`);
      err.status = res.status;
      err.body = json;
      throw err;
    }
    return json;
  }

  /**
   * Authentication API — session management, registration, and login.
   * @namespace
   */
  const AuthApi = {
    /**
     * Return the currently authenticated user, or reject with 401.
     * @returns {Promise<AuthResponse>}
     */
    me: () => call("GET", "/api/auth/me"),

    /**
     * Authenticate an existing user and start a session.
     * @param {string} username
     * @param {string} password
     * @returns {Promise<AuthResponse>}
     */
    login: (username, password) =>
      call("POST", "/api/auth/login", { username, password }),

    /**
     * Create a new user account and start a session.
     * @param {string} firstName
     * @param {string} lastName
     * @param {string} username
     * @param {string} password
     * @returns {Promise<AuthResponse>}
     */
    register: (firstName, lastName, username, password) =>
      call("POST", "/api/auth/register", { firstName, lastName, username, password }),

    /**
     * Check whether a username is available (not yet taken).
     * @param {string} username
     * @returns {Promise<{ available: boolean }>}
     */
    checkUsername: (username) =>
      call("GET", "/api/auth/check-username?username=" + encodeURIComponent(username)),

    /**
     * End the current session.
     * @returns {Promise<null>}
     */
    logout: () => call("POST", "/api/auth/logout"),
  };

  /**
   * Roadmap API — list, restore and delete roadmaps, and load/persist the
   * progress stored against each one.
   * @namespace
   */
  const RoadmapApi = {
    /**
     * List the signed-in user's roadmaps.
     * @returns {Promise<{ roadmaps: RoadmapSummary[] }>}
     */
    list: () => call("GET", "/api/roadmaps"),

    /**
     * Create an empty custom roadmap.
     * @param {{ name: string, description?: string, startMonth?: string }} body - startMonth is "YYYY-MM".
     * @returns {Promise<{ roadmap: RoadmapSummary }>}
     */
    create: (body) => call("POST", "/api/roadmaps", body),

    /**
     * Re-create the built-in AI Engineer roadmap after it was deleted.
     * @returns {Promise<{ roadmap: RoadmapSummary }>}
     */
    restoreBuiltin: () => call("POST", "/api/roadmaps", { source: "builtin_ai_engineer" }),

    /**
     * Permanently delete a roadmap and its progress.
     * @param {number} id
     * @returns {Promise<null>}
     */
    remove: (id) => call("DELETE", `/api/roadmaps/${id}`),

    /**
     * Fetch a roadmap's metadata, progress data and server version.
     * @param {number} id
     * @returns {Promise<ProgressResponse>}
     */
    getProgress: (id) => call("GET", `/api/roadmaps/${id}/progress`),

    /**
     * Persist progress data. Requires the current server version for
     * optimistic concurrency; a 409 response carries the server's copy.
     * @param {number} id
     * @param {object} data
     * @param {number} version
     * @returns {Promise<SaveResponse>}
     */
    putProgress: (id, data, version) =>
      call("PUT", `/api/roadmaps/${id}/progress`, { data, version }),
  };

  window.AuthApi = AuthApi;
  window.RoadmapApi = RoadmapApi;
})();
