const { pool } = require('./_db');

// Types: RegisterResponse, ErrorResponse — see _db.js

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json',
  };

  if (event.httpMethod === 'OPTIONS') return { statusCode: 200, headers, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers, body: '' };

  try {
    const result = await pool.query(
      'INSERT INTO players DEFAULT VALUES RETURNING id'
    );
    const player_id = result.rows[0].id;
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ player_id }),
    };
  } catch (err) {
    console.error(err);
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'DB error' }) };
  }
};
