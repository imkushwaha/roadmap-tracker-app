/**
 * @module api
 * Thin HTTP wrappers around the backend REST API.
 *
 * Exposes two focused namespaces — AuthApi and DataApi — plus a combined
 * window.Api shim for backwards compatibility with existing app code.
 * No application state lives here; callers are responsible for state management.
 */
(function () {
  "use strict";

  /**
   * @typedef {{ username: string }} UserInfo
   * @typedef {{ user: UserInfo }} AuthResponse
   * @typedef {{ data: object|null, version: number, updatedAt?: string }} DataResponse
   * @typedef {{ version: number, updatedAt: string }} SaveResponse
   */

  /**
   * Low-level HTTP fetch wrapper — single point of error normalisation.
   *
   * Network errors set `err.network = true` on the thrown Error.
   * HTTP error responses set `err.status` and `err.body`.
   *
   * @param {'GET'|'POST'|'PUT'} method
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
     * @param {string} username
     * @param {string} password
     * @returns {Promise<AuthResponse>}
     */
    register: (username, password) =>
      call("POST", "/api/auth/register", { username, password }),

    /**
     * End the current session.
     * @returns {Promise<null>}
     */
    logout: () => call("POST", "/api/auth/logout"),
  };

  /**
   * Data sync API — load and persist the user's progress data.
   * @namespace
   */
  const DataApi = {
    /**
     * Fetch the user's current progress data and its server version.
     * @returns {Promise<DataResponse>}
     */
    getData: () => call("GET", "/api/data"),

    /**
     * Persist progress data. Requires the current server version for
     * optimistic concurrency; a 409 response carries the server's copy.
     * @param {object} data
     * @param {number} version
     * @returns {Promise<SaveResponse>}
     */
    putData: (data, version) => call("PUT", "/api/data", { data, version }),
  };

  // Publish to window — split namespaces for new code, combined shim for existing code
  window.AuthApi = AuthApi;
  window.DataApi = DataApi;
  window.Api = { ...AuthApi, ...DataApi };
})();
