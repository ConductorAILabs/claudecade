
/**
 * Site landing-page script: animated cover-art frames and a small embedded
 * leaderboard widget that hits /api/leaderboard.
 *
 * @typedef {'ctype'|'claudtra'|'fight'|'finalclaudesy'|'superclaudio'|'claudemon'|'claudturismo'} GameId
 *
 * @typedef {{
 *   game?:        GameId,
 *   player_name:  string,
 *   score:        number,
 *   extra:        string,
 *   created_at?:  string
 * }} ScoreRow
 *
 * @typedef {{ game: GameId, entries: string, top_score: string }} StatRow
 * @typedef {{ scores: ScoreRow[], stats?: StatRow[] }} LeaderboardResponse
 */

/** @type {Record<string, string[]>} */
const ART_FRAMES = {
  'art-ctype': [
    ' ·  ★   ·    *   ·   ★  ·\n    ◁══◁   ·   ◁══◁\n ·    ·  ·   ·    ·  ·\n         ◁══◁   ◁══◁\n ·   ·    ·   ·    ·   ·\n══════════════════════════\n▷════════════════●●●●●●●●\n══════════════════════════\n ·   ·    ·   ·    ·   ·\n    ◁══◁   ·   ◁══◁\n ·  ★   ·    *   ·   ★  ·',
    ' ·  ·   ·    *   ·   ★  ·\n  ◁══◁     ·  ◁══◁\n ·    ·  ·   ·    ·  ·\n       ◁══◁     ◁══◁\n ·   ·    ·   ·    ·   ·\n══════════════════════════\n▷════════════════●●●●●●●●\n══════════════════════════\n ·   ·    ·   ·    ·   ·\n  ◁══◁     ·  ◁══◁\n ·  ·   ·    *   ·   ★  ·',
    ' ·  ★   ·    *   ·   ·  ·\n      ◁══◁ ·   ◁══◁\n ·    ·  ·   ·    ·  ·\n          ◁══◁  ◁══◁\n ·   ·    ·   ·    ·   ·\n══════════════════════════\n▷════════════════●●●●●●●●\n══════════════════════════\n ·   ·    ·   ·    ·   ·\n      ◁══◁ ·   ◁══◁\n ·  ★   ·    *   ·   ·  ·',
  ],
  'art-claudtra': [
    '  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n        ×          ×\n  ▷@──▷    ×\n  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n          ████ ████\n  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁\n  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n  ███████████████████████',
    '  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n        ×          ×\n  ▷ @──▷   ×\n  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n          ████ ████\n  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁\n  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n  ███████████████████████',
    '  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n        ×          ×\n  ▷  @──▷  ×\n  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n          ████ ████\n  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁\n  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n  ███████████████████████',
  ],
  'art-fight': [
    '  HP ████████░░  P1\n  HP ░░████████  P2\n  ─────────────────────\n  ╔══════╗     ╔══════╗\n  ║ ▲ ▲  ║     ║ ● ●  ║\n  ║  ▽   ║ ×── ║  ○   ║\n  ╚═══╦══╝     ╚═══╦══╝\n      ║               ║\n  ─────────────────────\n  ████████████████████',
    '  HP ████████░░  P1\n  HP ░░████████  P2\n  ─────────────────────\n  ╔══════╗     ╔══════╗\n  ║ ▲ ▲  ║     ║ ◉ ◉  ║\n  ║  ▽   ║ ──× ║  ○   ║\n  ╚═══╦══╝     ╚═══╦══╝\n      ║               ║\n  ─────────────────────\n  ████████████████████',
    '  HP ███████░░░  P1\n  HP ░░████████  P2\n  ─────────────────────\n  ╔══════╗     ╔══════╗\n  ║ ▲ ▲  ║     ║ ● ●  ║\n  ║  ▽   ║  ×  ║  ○   ║\n  ╚═══╦══╝     ╚═══╦══╝\n      ║               ║\n  ─────────────────────\n  ████████████████████',
  ],
  'art-superclaudio': [
    '       [?]        [?]\n  ◆               ◆\n      ████\n  (☿)       [C]\n  ═══════════════════\n  ████████    ███████\n  ████████    ███████',
    '       [?]        [?]\n  ◆               ◆\n      ████\n   (☿)      [C]\n  ═══════════════════\n  ████████    ███████\n  ████████    ███████',
    '       [?]  ◆     [?]\n               ◆\n      ████\n  (☿)       [C]\n  ═══════════════════\n  ████████    ███████\n  ████████    ███████',
  ],
  'art-claudturismo': [
    '  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n   ──────────────────\n    ════════════════\n      ════════════\n        ════════\n          ═════\n           ═▷═▷\n             ▷\n  ████████████████████',
    '  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n   ──────────────────\n    ════════════════\n      ════════════\n        ════════\n          ══▷══\n           ═▷═▷\n             ▷\n  ████████████████████',
    '  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n   ──────────────────\n    ════════════════\n      ════════════\n        ═══▷════\n          ═════\n           ═▷═▷\n             ▷\n  ████████████████████',
  ],
  'art-claudemon': [
    '  WILD   LV 8      AQUUX\n  .·*·.  HP ████░░░░\n  (◎◎)\n  /▐W▐\\\n  ─────────────────────\n  CLAUDPYRE   LV 12\n  HP ██████░░\n  .·*·.   > BATTLE\n  (●●)\n  /▐C▐\\',
    '  WILD   LV 8      AQUUX\n  .·*·.  HP ████░░░░\n  (◎◎)\n  /▐W▐\\\n  ─────────────────────\n  CLAUDPYRE   LV 12\n  HP ██████░░\n  .·*·.   > THROW\n  (●●)\n  /▐C▐\\',
    '  WILD   LV 8      AQUUX\n  .·*·.  HP ███░░░░░\n  (◉◉)\n  /▐W▐\\\n  ─────────────────────\n  CLAUDPYRE   LV 12\n  HP ██████░░\n  .·*·.   > ABILITY\n  (●●)\n  /▐C▐\\',
  ],
  'art-finalclaudesy': [
    '┌───────────────────────┐\n│ CLAUDE  HP ██████░░ │\n│ HAIKU   HP ███░░░░░ │\n│ OPUS    HP ███████░ │\n├───────────────────────┤\n│ ▸ Attack    Magic   │\n│   Item      Defend  │\n└───────────────────────┘',
    '┌───────────────────────┐\n│ CLAUDE  HP ██████░░ │\n│ HAIKU   HP ███░░░░░ │\n│ OPUS    HP ███████░ │\n├───────────────────────┤\n│   Attack    Magic   │\n│ ▸ Item      Defend  │\n└───────────────────────┘',
    '┌───────────────────────┐\n│ CLAUDE  HP ██████░░ │\n│ HAIKU   HP ███░░░░░ │\n│ OPUS    HP ███████░ │\n├───────────────────────┤\n│   Attack  ▸ Magic   │\n│   Item      Defend  │\n└───────────────────────┘',
  ],
};

/** @type {Record<string, number>} */
const artTimers = {};

document.querySelectorAll('.game-cover').forEach(card => {
  const artEl = card.querySelector('.cover-art-pre');
  if (!artEl) return;
  const artId = artEl.id;
  const frames = ART_FRAMES[artId];
  if (!frames) return;

  card.addEventListener('mouseenter', () => {
    let frame = 1;
    artTimers[artId] = setInterval(() => {
      artEl.textContent = frames[frame % frames.length];
      frame++;
    }, 400);
  });

  card.addEventListener('mouseleave', () => {
    if (artTimers[artId]) {
      clearInterval(artTimers[artId]);
      delete artTimers[artId];
    }
    artEl.textContent = frames[0];
  });
});


/** @type {Record<string, string>} */
const GAME_LABELS = {
  ctype:         'C-TYPE',
  claudtra:      'Claudtra',
  fight:         'Claude Fighter',
  superclaudio:  'Super Claudio',
  claudturismo:  'Claude Turismo',
  claudemon:     'Claudémon',
  finalclaudesy: 'Final Claudesy',
};

let currentGame = '';

/**
 * @param {ScoreRow[]} scores
 * @returns {HTMLPreElement}
 */
function buildAsciiTable(scores) {
  const pre = document.createElement('pre');
  pre.className = 'lb-ascii-table';

  const allGames = !currentGame;
  const RW = 4, PW = 18, GW = 14, SW = 12, EW = 14;

  function pad(v, w, right) {
    const s = String(v ?? '').slice(0, w);
    return right ? s.padStart(w) : s.padEnd(w);
  }

  function hline(l, j, m, r, widths) {
    return l + widths.map(w => j.repeat(w + 2)).join(m) + r;
  }

  function row(cells) {
    return '│' + cells.map(c => ' ' + c + ' ').join('│') + '│';
  }

  const widths = allGames ? [RW, PW, GW, SW] : [RW, PW, SW, EW];
  const top = hline('┌', '─', '┬', '┐', widths);
  const mid = hline('├', '─', '┼', '┤', widths);
  const bot = hline('└', '─', '┴', '┘', widths);

  const hdr = allGames
    ? [pad('#', RW, true), pad('PLAYER', PW), pad('GAME', GW), pad('SCORE', SW, true)]
    : [pad('#', RW, true), pad('PLAYER', PW), pad('SCORE', SW, true), pad('DETAIL', EW)];

  const lines = [top, row(hdr), mid];
  const medals = ['▸', '·', '·'];

  scores.forEach((s, i) => {
    const mark   = medals[i] ?? ' ';
    const rankS  = pad(mark + String(i + 1).padStart(2), RW, true);
    const cells  = allGames
      ? [rankS, pad(s.player_name, PW), pad(GAME_LABELS[s.game] || s.game, GW), pad(Number(s.score).toLocaleString(), SW, true)]
      : [rankS, pad(s.player_name, PW), pad(Number(s.score).toLocaleString(), SW, true), pad(s.extra || '', EW)];
    lines.push(row(cells));
  });

  lines.push(bot);
  pre.textContent = lines.join('\n');
  return pre;
}

/**
 * @param {string} game  game id, or '' for combined leaderboard
 * @returns {Promise<void>}
 */
async function loadLeaderboard(game) {
  const el = document.getElementById('lb-main');
  if (!el) return;
  el.textContent = '';

  const loading = document.createElement('p');
  loading.className = 'loading';
  loading.textContent = 'LOADING';
  el.appendChild(loading);

  const url = game
    ? `/api/leaderboard?game=${encodeURIComponent(game)}&limit=20`
    : '/api/leaderboard?limit=20';

  try {
    const res  = await fetch(url);
    if (!res.ok) throw new Error();
    const data = await res.json();
    const scores = Array.isArray(data.scores) ? data.scores : [];

    const stats = Array.isArray(data.stats) ? data.stats : [];
    const total = stats.reduce((n, r) => n + parseInt(r.entries || 0), 0);
    const totalEl = document.getElementById('lb-total');
    if (totalEl && total) totalEl.textContent = total + ' SCORES';

    el.textContent = '';

    if (!scores.length) {
      const p = document.createElement('p');
      p.className = 'loading';
      p.textContent = 'NO SCORES YET';
      el.appendChild(p);
    } else {
      el.appendChild(buildAsciiTable(scores));
    }
  } catch {
    el.textContent = '';
    const p = document.createElement('p');
    p.className = 'loading';
    p.textContent = 'UNAVAILABLE';
    el.appendChild(p);
  }
}

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    currentGame = btn.dataset.game || '';
    loadLeaderboard(currentGame);
  });
});

loadLeaderboard('');
setInterval(() => loadLeaderboard(currentGame), 30000);
