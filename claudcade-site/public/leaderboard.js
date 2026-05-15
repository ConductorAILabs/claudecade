/**
 * Types come from the server's _db.js so this file can never drift from
 * the schema the API actually returns. Editor tooling resolves the
 * `import()` form across the static/server boundary.
 *
 * @typedef {import('../netlify/functions/_db').GameId}                GameId
 * @typedef {import('../netlify/functions/_db').ScoreRow}              ScoreRow
 * @typedef {import('../netlify/functions/_db').StatRow}               StatRow
 * @typedef {import('../netlify/functions/_db').LeaderboardResponse}   LeaderboardResponse
 */

/** @type {Record<string, string>} */
const GAME_LABELS = {
  ctype:         'C-TYPE',
  claudtra:      'Claudtra',
  fight:         'Claude Fighter',
  superclaudio:  'Super Claudio',
  claudemon:     'Claudémon',
  claudturismo:  'Claude Turismo',
  finalclaudesy: 'Final Claudesy',
};

const PAGE_SIZE = 25;

let currentGame  = '';
let currentRange = 'all';
let currentQuery = '';
let currentOffset = 0;

/**
 * @param {ScoreRow[]} scores
 * @returns {HTMLTableElement}
 */
function buildTable(scores) {
  const table = document.createElement('table');
  table.className = 'lb-table';

  const thead = document.createElement('thead');
  const hrow  = document.createElement('tr');
  const cols   = currentGame
    ? ['#', 'PLAYER', 'SCORE', 'DETAIL', 'DATE']
    : ['#', 'PLAYER', 'GAME', 'SCORE', 'DATE'];
  cols.forEach(h => {
    const th = document.createElement('th');
    th.textContent = h;
    if (h === 'SCORE') th.className = 'score';
    hrow.appendChild(th);
  });
  thead.appendChild(hrow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  scores.forEach((s, i) => {
    const tr = document.createElement('tr');
    const rankClass = i === 0 ? 'rank-gold' : i === 1 ? 'rank-silver' : i === 2 ? 'rank-bronze' : '';

    function td(cls, text) {
      const el = document.createElement('td');
      el.className = cls + (cls === 'rank' && rankClass ? ' ' + rankClass : '');
      el.textContent = text;
      return el;
    }

    tr.appendChild(td('rank', String(i + 1)));
    tr.appendChild(td('player', s.player_name));
    if (!currentGame) tr.appendChild(td('game', GAME_LABELS[s.game] || s.game));
    tr.appendChild(td('score', Number(s.score).toLocaleString()));
    if (currentGame && s.extra) tr.appendChild(td('extra', s.extra));
    else if (currentGame)       tr.appendChild(td('extra', ''));

    const date = new Date(s.created_at);
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
    tr.appendChild(td('date', dateStr));

    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

/**
 * Fetch the leaderboard with current filters and render it into #lb-main.
 * Never throws — failures show a fallback.
 *
 * @returns {Promise<void>}
 */
function updatePrompt() {
  const el = document.getElementById('lb-prompt-text');
  if (!el) return;
  const parts = ['claudecade scores'];
  parts.push(currentGame ? `--game ${currentGame}` : '--all');
  if (currentRange !== 'all') parts.push(`--range ${currentRange}`);
  if (currentQuery)           parts.push(`--player "${currentQuery}"`);
  parts.push(`--limit ${PAGE_SIZE}`);
  el.textContent = parts.join(' ');
}

async function loadLeaderboard() {
  const el = document.getElementById('lb-main');
  if (!el) return;
  updatePrompt();

  const loading = document.createElement('p');
  loading.className = 'loading';
  loading.textContent = 'Loading...';
  el.textContent = '';
  el.appendChild(loading);

  const params = new URLSearchParams({
    limit:  String(PAGE_SIZE),
    offset: String(currentOffset),
    range:  currentRange,
  });
  if (currentGame)  params.set('game', currentGame);
  if (currentQuery) params.set('q', currentQuery);

  try {
    const res  = await fetch('/api/leaderboard?' + params.toString());
    if (!res.ok) throw new Error('bad response');
    const data   = await res.json();
    const scores = Array.isArray(data.scores) ? data.scores : [];
    const total  = Number(data.total) || scores.length;

    el.textContent = '';
    if (scores.length === 0) {
      const p = document.createElement('p');
      p.className = 'loading dim';
      p.textContent = currentQuery
        ? `No scores match "${currentQuery}".`
        : 'No scores yet for this filter.';
      el.appendChild(p);
    } else {
      el.appendChild(buildTable(scores));
      el.appendChild(buildPager(total));
    }
  } catch {
    el.textContent = '';
    const p = document.createElement('p');
    p.className = 'loading dim';
    p.textContent = 'Failed to load leaderboard.';
    el.appendChild(p);
  }
}

/**
 * @param {number} total total rows matching the current filter
 * @returns {HTMLDivElement}
 */
function buildPager(total) {
  const div = document.createElement('div');
  div.className = 'lb-pager';
  const page  = Math.floor(currentOffset / PAGE_SIZE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const info  = document.createElement('span');
  info.textContent = `Page ${page} / ${pages}  ·  ${total} total`;
  const prev  = document.createElement('button');
  prev.textContent = '< Prev';
  prev.disabled = currentOffset === 0;
  prev.onclick = () => { currentOffset = Math.max(0, currentOffset - PAGE_SIZE); loadLeaderboard(); };
  const next  = document.createElement('button');
  next.textContent = 'Next >';
  next.disabled = currentOffset + PAGE_SIZE >= total;
  next.onclick = () => { currentOffset += PAGE_SIZE; loadLeaderboard(); };
  div.appendChild(prev); div.appendChild(info); div.appendChild(next);
  return div;
}

// Game tabs
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    currentGame   = btn.dataset.game || '';
    currentOffset = 0;
    loadLeaderboard();
  });
});

// Time-range buttons (set up once at load if the markup provides them)
document.querySelectorAll('.range').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.range').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    currentRange  = btn.dataset.range || 'all';
    currentOffset = 0;
    loadLeaderboard();
  });
});

// Search box (debounced 300ms)
const searchEl = document.getElementById('lb-search');
if (searchEl) {
  let timer;
  searchEl.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      currentQuery  = searchEl.value.trim();
      currentOffset = 0;
      loadLeaderboard();
    }, 300);
  });
}

loadLeaderboard();
setInterval(loadLeaderboard, 30000);
