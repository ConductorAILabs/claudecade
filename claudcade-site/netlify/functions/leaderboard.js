const { pool, VALID_GAMES } = require('./_db');

// Types: GameId, ScoreRow, StatRow, LeaderboardResponse — see _db.js
//
// Query params:
//   game     GameId   filter by game (omit for all games)
//   range    today | week | month | all   default 'all'
//   limit    int      default 20, max 100
//   offset   int      pagination cursor, default 0
//   q        string   substring search on player_name

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
    'Cache-Control': 'public, max-age=30',
  };

  const params = event.queryStringParameters || {};
  const { game, q } = params;
  const range  = (params.range  || 'all').toLowerCase();
  const limit  = Math.min(Math.max(parseInt(params.limit) || 20, 1), 100);
  const offset = Math.max(parseInt(params.offset) || 0, 0);

  // Translate range → SQL interval. 'all' means no time filter.
  const RANGE_INTERVALS = {
    today: '1 day',
    week:  '7 days',
    month: '30 days',
  };
  const interval = RANGE_INTERVALS[range] || null;

  // Build WHERE clause + parameter list dynamically.
  const where = [];
  const args  = [];
  if (game && VALID_GAMES.includes(game)) {
    where.push(`game = $${args.length + 1}`); args.push(game);
  }
  if (interval) {
    where.push(`created_at > NOW() - INTERVAL '${interval}'`);
  }
  if (q && typeof q === 'string') {
    where.push(`player_name ILIKE $${args.length + 1}`);
    args.push(`%${q.slice(0, 24)}%`);
  }
  const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

  try {
    args.push(limit);  args.push(offset);
    const sel = game
      ? `SELECT player_name, score, extra, created_at`
      : `SELECT game, player_name, score, extra, created_at`;
    const rows = (await pool.query(
      `${sel} FROM scores ${whereSql}
       ORDER BY score DESC, created_at ASC
       LIMIT $${args.length - 1} OFFSET $${args.length}`,
      args
    )).rows;

    // Total matching rows (for pagination UI). Cheap COUNT(*) reusing where.
    const countArgs = args.slice(0, args.length - 2);
    const total = parseInt((await pool.query(
      `SELECT COUNT(*) AS n FROM scores ${whereSql}`, countArgs
    )).rows[0].n);

    // Per-game stats are useful for the index page; keep them range-scoped too
    // so "today" shows today's totals, not all-time.
    const statsWhere = interval ? `WHERE created_at > NOW() - INTERVAL '${interval}'` : '';
    const stats = (await pool.query(
      `SELECT game, COUNT(*) AS entries, MAX(score) AS top_score
       FROM scores ${statsWhere}
       GROUP BY game ORDER BY game`
    )).rows;

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        scores: rows,
        stats,
        range,
        total,
        limit,
        offset,
      }),
    };
  } catch (err) {
    console.error(err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'Database error' }) };
  }
};
