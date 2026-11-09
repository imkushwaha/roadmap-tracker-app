"""Phase 2 / backend wiring: repository + list route. Run from the repo root: python3 step2_server.py
(New files js/roadmap-stats.js, server/roadmaps/stats.js and test/stats.test.js are created separately.)"""


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        assert s.count(old) == 1, f"{path}: expected exactly one match ({s.count(old)} found) for: {old[:80]}"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)


patch("server/roadmaps/repository.js", [
    ("""  /** @returns {Promise<RoadmapRow | undefined>} */
  async function findOwned(""",
     """  /**
   * Like listForUser, plus each roadmap's stored progress (raw JSON text and
   * version) so the caller can summarise it. Callers must not expose the raw
   * progress to clients.
   * @returns {Promise<Array<RoadmapRow & { progressData: string | null, progressVersion: number | null }>>}
   */
  async function listWithProgress(userId) {
    const result = await db.execute({
      sql: `SELECT r.id, r.name, r.description, r.source, r.created_at,
                   p.updated_at AS last_activity_at, p.data AS progress_data, p.version AS progress_version
            FROM roadmaps r LEFT JOIN roadmap_progress p ON p.roadmap_id = r.id
            WHERE r.user_id = ?
            ORDER BY r.created_at, r.id`,
      args: [userId],
    });
    return result.rows.map((row) => ({
      ...toRoadmap(row),
      lastActivityAt: row.last_activity_at == null ? null : String(row.last_activity_at),
      progressData: row.progress_data == null ? null : String(row.progress_data),
      progressVersion: row.progress_version == null ? null : Number(row.progress_version),
    }));
  }

  /** @returns {Promise<RoadmapRow | undefined>} */
  async function findOwned("""),
    ("    listForUser, findOwned, countForUser,", "    listForUser, listWithProgress, findOwned, countForUser,"),
])

patch("server/routes/roadmaps.js", [
    ('const { emptyProgress } = require("../roadmaps/progress");',
     'const { emptyProgress } = require("../roadmaps/progress");\nconst { createStatsService } = require("../roadmaps/stats");'),
    (""" * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 */""",
     """ * @property {import('express').RequestHandler} requireAuth - Middleware that sets `req.user`.
 * @property {object} [builtinData] - Parsed data/roadmap.json (defaults to the bundled file).
 */"""),
    ("""function createRoadmapsRouter({ db, requireAuth }) {
  const router = express.Router();
  const repo = createRoadmapRepository(db);""",
     """function createRoadmapsRouter({ db, requireAuth, builtinData = require("../../data/roadmap.json") }) {
  const router = express.Router();
  const repo = createRoadmapRepository(db);
  const stats = createStatsService({ builtinData });"""),
    ("""  router.get("/", async (req, res) => {
    res.json({ roadmaps: await repo.listForUser(req.user.id) });
  });""",
     """  // Each roadmap carries `stats` (totals and a per-month breakdown) so the Home
  // screen can show progress without loading every roadmap's full progress.
  // The raw progress JSON is never included.
  router.get("/", async (req, res) => {
    const rows = await repo.listWithProgress(req.user.id);
    const roadmaps = rows.map(({ progressData, progressVersion, ...roadmap }) => ({
      ...roadmap,
      stats: stats.forRoadmap({
        id: roadmap.id, source: roadmap.source, progressData, progressVersion,
      }),
    }));
    res.json({ roadmaps });
  });"""),
])
print("server/roadmaps/repository.js and server/routes/roadmaps.js updated")
