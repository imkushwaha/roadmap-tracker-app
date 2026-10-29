/**
 * @module roadmaps/repository
 * All SQL for roadmaps and their progress. Every lookup that starts from a
 * request is scoped by `user_id`, so one account can never reach another's
 * roadmap.
 */
"use strict";

/**
 * @typedef {object} RoadmapRow
 * @property {number} id
 * @property {string} name
 * @property {string} description
 * @property {string} source
 * @property {string} createdAt
 * @property {string | null} [lastActivityAt]
 */

/**
 * @param {Record<string, unknown>} row
 * @returns {RoadmapRow}
 */
function toRoadmap(row) {
  return {
    id: Number(row.id),
    name: String(row.name),
    description: String(row.description),
    source: String(row.source),
    createdAt: String(row.created_at),
  };
}

/**
 * Create the roadmap repository bound to a database client.
 * @param {import('@libsql/client').Client} db
 */
function createRoadmapRepository(db) {
  /** @returns {Promise<RoadmapRow[]>} */
  async function listForUser(userId) {
    const result = await db.execute({
      sql: `SELECT r.id, r.name, r.description, r.source, r.created_at, p.updated_at AS last_activity_at
            FROM roadmaps r LEFT JOIN roadmap_progress p ON p.roadmap_id = r.id
            WHERE r.user_id = ?
            ORDER BY r.created_at, r.id`,
      args: [userId],
    });
    return result.rows.map((row) => ({
      ...toRoadmap(row),
      lastActivityAt: row.last_activity_at == null ? null : String(row.last_activity_at),
    }));
  }

  /** @returns {Promise<RoadmapRow | undefined>} */
  async function findOwned(userId, roadmapId) {
    const result = await db.execute({
      sql: "SELECT id, name, description, source, created_at FROM roadmaps WHERE id = ? AND user_id = ?",
      args: [roadmapId, userId],
    });
    return result.rows[0] ? toRoadmap(result.rows[0]) : undefined;
  }

  async function countForUser(userId) {
    const result = await db.execute({
      sql: "SELECT COUNT(*) AS n FROM roadmaps WHERE user_id = ?",
      args: [userId],
    });
    return Number(result.rows[0].n);
  }

  async function hasSource(userId, source) {
    const result = await db.execute({
      sql: "SELECT 1 FROM roadmaps WHERE user_id = ? AND source = ?",
      args: [userId, source],
    });
    return result.rows.length > 0;
  }

  /**
   * Insert a roadmap, optionally with its first progress row (version 1), in
   * one transaction.
   * @param {number} userId
   * @param {{ name: string, description: string, source: string }} roadmap
   * @param {object | null} [initialProgress]
   * @returns {Promise<number>} the new roadmap id
   */
  async function insert(userId, { name, description, source }, initialProgress = null) {
    const statements = [{
      sql: "INSERT INTO roadmaps (user_id, name, description, source) VALUES (?, ?, ?, ?)",
      args: [userId, name, description, source],
    }];
    if (initialProgress) {
      statements.push({
        sql: "INSERT INTO roadmap_progress (roadmap_id, data, version, updated_at) VALUES (last_insert_rowid(), ?, 1, ?)",
        args: [JSON.stringify(initialProgress), new Date().toISOString()],
      });
    }
    const results = await db.batch(statements, "write");
    return Number(results[0].lastInsertRowid);
  }

  /** @returns {Promise<boolean>} whether a roadmap was deleted */
  async function remove(userId, roadmapId) {
    const result = await db.execute({
      sql: "DELETE FROM roadmaps WHERE id = ? AND user_id = ?",
      args: [roadmapId, userId],
    });
    return result.rowsAffected > 0;
  }

  async function getProgress(roadmapId) {
    const result = await db.execute({
      sql: "SELECT data, version, updated_at FROM roadmap_progress WHERE roadmap_id = ?",
      args: [roadmapId],
    });
    const row = result.rows[0];
    return row
      ? { data: String(row.data), version: Number(row.version), updated_at: String(row.updated_at) }
      : undefined;
  }

  // Compare-and-swap in a single atomic statement: the write only lands if the
  // stored version still equals the client's. Version 0 means "no row yet".
  async function saveProgress(roadmapId, dataText, clientVersion) {
    const now = new Date().toISOString();
    const result = clientVersion === 0
      ? await db.execute({
          sql: `INSERT INTO roadmap_progress (roadmap_id, data, version, updated_at) VALUES (?, ?, 1, ?)
                ON CONFLICT(roadmap_id) DO NOTHING`,
          args: [roadmapId, dataText, now],
        })
      : await db.execute({
          sql: `UPDATE roadmap_progress SET data = ?, version = version + 1, updated_at = ?
                WHERE roadmap_id = ? AND version = ?`,
          args: [dataText, now, roadmapId, clientVersion],
        });
    if (result.rowsAffected === 1) {
      return { conflict: false, version: clientVersion + 1, updatedAt: now };
    }
    return { conflict: true, row: await getProgress(roadmapId) };
  }

  return {
    listForUser, findOwned, countForUser, hasSource, insert, remove, getProgress, saveProgress,
  };
}

module.exports = { createRoadmapRepository };
