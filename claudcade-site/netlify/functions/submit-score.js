const {
  pool, VALID_GAMES, MAX_SCORES,
  RATE_LIMIT_MAX, ROLLING_WINDOW_MIN,
} = require('./_db');

// Types: GameId, SubmitBody, SubmitOkResponse, ErrorResponse — see _db.js

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON' }) };
  }

  const { game, player_name, score, extra = '' } = body;

  if (!game || !VALID_GAMES.includes(game)) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid game' }) };
  }
  if (typeof score !== 'number' || score < 0 || !Number.isFinite(score)) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid score' }) };
  }

  // Cheat guard: reject scores beyond any plausible envelope for this game.
  const cap = MAX_SCORES[game];
  if (cap !== undefined && score > cap) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Score exceeds plausible maximum for this game' }) };
  }

  const name = (player_name || 'Anonymous').slice(0, 24).replace(/[^a-zA-Z0-9 _\-\.]/g, '');
  const safeName = name || 'Anonymous';

  try {
    // Rate limit: how many submissions has this player made in the rolling window?
    const recent = await pool.query(
      `SELECT COUNT(*) AS n FROM scores
        WHERE player_name = $1
          AND created_at > NOW() - INTERVAL '${ROLLING_WINDOW_MIN} minutes'`,
      [safeName]
    );
    if (parseInt(recent.rows[0].n) >= RATE_LIMIT_MAX) {
      return {
        statusCode: 429,
        headers,
        body: JSON.stringify({
          error: `Rate limit exceeded — max ${RATE_LIMIT_MAX} submissions per ${ROLLING_WINDOW_MIN} minutes`,
        }),
      };
    }

    const result = await pool.query(
      `INSERT INTO scores (game, player_name, score, extra)
       VALUES ($1, $2, $3, $4)
       RETURNING id, score`,
      [game, safeName, score, String(extra).slice(0, 64)]
    );

    const rank = await pool.query(
      `SELECT COUNT(*) + 1 AS rank FROM scores WHERE game = $1 AND score > $2`,
      [game, score]
    );

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        id: result.rows[0].id,
        rank: parseInt(rank.rows[0].rank),
      }),
    };
  } catch (err) {
    console.error(err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'Database error' }) };
  }
};
