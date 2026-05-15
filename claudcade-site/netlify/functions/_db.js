/**
 * Shared database pool, game constants, and JSDoc types for all Netlify functions.
 * Import with: const { pool, VALID_GAMES, GAME_LABELS } = require('./_db');
 *
 * @typedef {'ctype'|'claudtra'|'fight'|'finalclaudesy'|'superclaudio'|'claudturismo'|'claudemon'} GameId
 *
 * @typedef {{ error: string }} ErrorResponse
 *
 * @typedef {{
 *   game?: GameId,
 *   player_name: string,
 *   score: number,
 *   extra: string,
 *   created_at: string
 * }} ScoreRow
 *
 * @typedef {{ game: GameId, entries: string, top_score: string }} StatRow
 *
 * @typedef {{
 *   scores: ScoreRow[],
 *   stats:  StatRow[],
 *   range:  'today'|'week'|'month'|'all',
 *   total:  number,
 *   limit:  number,
 *   offset: number
 * }} LeaderboardResponse
 *
 * @typedef {{ success: true, id: number, rank: number }} SubmitOkResponse
 * @typedef {{ game: GameId, player_name?: string, score: number, extra?: string }} SubmitBody
 *
 * @typedef {{ player_id: number }} RegisterResponse
 */
'use strict';

const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.NEON_DATABASE_URL,
  ssl: { rejectUnauthorized: false },
  max: 5,
});

const VALID_GAMES = [
  'ctype', 'claudtra', 'fight', 'finalclaudesy',
  'superclaudio', 'claudturismo', 'claudemon',
];

const GAME_LABELS = {
  ctype:         'C-TYPE (Space Shooter)',
  claudtra:      'Claudtra (Action Platformer)',
  fight:         'Claude Fighter (Fighting)',
  finalclaudesy: 'Final Claudesy (JRPG)',
  superclaudio:  'Super Claudio (Platformer)',
  claudturismo:  'Claude Turismo (Racing)',
  claudemon:     'Claudemon (Creature RPG)',
};

// Per-game maximum plausible score. Anything above is rejected as cheated.
// Rough envelope: deepest plausible run × score-per-action × generous slack.
const MAX_SCORES = {
  ctype:         10_000_000,
  claudtra:       5_000_000,
  fight:                500,   // p1w * 100, NEED=2 → max ~200; small slack
  finalclaudesy:    999_999,
  superclaudio:   5_000_000,   // platformer collectible scoring envelope
  claudturismo:   1_000_000,   // racing — typically low integer scoring
  claudemon:        999_999,   // RPG-style total like finalclaudesy
};

// Per-player rate limit: max submissions per ROLLING_WINDOW_MIN minutes.
const RATE_LIMIT_MAX     = 30;
const ROLLING_WINDOW_MIN = 60;

module.exports = {
  pool,
  VALID_GAMES,
  GAME_LABELS,
  MAX_SCORES,
  RATE_LIMIT_MAX,
  ROLLING_WINDOW_MIN,
};
