// Returns today's daily-challenge seed. The seed is deterministic for a given
// UTC date so every player who runs a daily challenge today gets the same RNG
// sequence — same wave layout, same enemy spawn pattern, etc.
//
// Response shape:
//   { date: 'YYYY-MM-DD', seed: <32-bit int> }

'use strict';

function dailySeed(dateStr) {
  // Deterministic FNV-1a over the date string. Stable across runtimes.
  let hash = 0x811c9dc5;
  for (let i = 0; i < dateStr.length; i++) {
    hash ^= dateStr.charCodeAt(i);
    hash = (hash * 0x01000193) >>> 0;
  }
  return hash;
}

exports.handler = async () => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json',
  };
  const now  = new Date();
  const date = now.toISOString().slice(0, 10);  // YYYY-MM-DD UTC
  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({ date, seed: dailySeed(date) }),
  };
};
