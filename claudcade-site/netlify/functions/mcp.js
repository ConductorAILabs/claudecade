const { pool, VALID_GAMES, GAME_LABELS } = require('./_db');

/**
 * Types: GameId, SubmitBody, SubmitOkResponse, ErrorResponse — see _db.js
 *
 * @typedef {{ game?: import('./_db').GameId, limit?: number }} LeaderboardArgs
 * @typedef {{ genre: string, title: string }} ScaffoldArgs
 */

const ENGINE_DOCS = `
# Claudecade Engine — Quick Reference

Copy claudcade_engine.py into your project. No pip install needed.

\`\`\`python
from claudcade_engine import Engine, Scene, Renderer, Input, CYAN, YELLOW

class GameScene(Scene):
    def on_enter(self):
        self.x, self.y = 10.0, 5.0

    def update(self, inp: Input, tick: int) -> str | None:
        if inp.left:  self.x -= 1
        if inp.right: self.x += 1
        if inp.up:    self.y -= 1
        if inp.down:  self.y += 1
        if inp.pause: return "quit"

    def draw(self, r: Renderer, tick: int):
        r.header("MY GAME", left="♥ ♥ ♥", right="SCORE: 000", color=CYAN)
        r.outer_border()
        r.text(int(self.y), int(self.x), '@', YELLOW, bold=True)

Engine("My Game", fps=30).scene("game", GameScene()).run("game")
\`\`\`

## Key classes
- Engine("title", fps) — manages loop and scenes. Chain .scene(name, Scene()).run(first)
- Scene — override on_enter(), update(inp, tick) → str|None, draw(r, tick)
- Input — inp.up/down/left/right/fire/jump/confirm/pause, inp.pressed(ord('x'))
- Renderer — r.text(row,col,s), r.center(row,s), r.box(), r.bar(), r.sprite(), r.header(), r.footer(), r.outer_border(), r.menu(), r.stars(), r.pause_overlay(), r.gameover_screen()
- Entity — base class with x,y,vx,vy,alive,rect(),collides()
- PhysicsEntity — adds gravity, grounded, apply_physics(floor_y)
- AnimSprite — named states with frame cycling
- Camera — follow(tx,ty,lerp), world_to_screen(wx,wy,W,H)
- Particles — explode(col,row), spark(), update(), draw(r)

## Colors: CYAN=1 RED=2 GREEN=3 YELLOW=4 WHITE=5 MAGENTA=6 HIGHLIGHT=7 BLUE=8

Full docs: https://github.com/ConductorAILabs/claudecade
`.trim();

const SLASH_COMMAND_CONTENT = `\
Launch the Claudecade arcade in a new tmux window.

The send-keys pattern is required: \`tmux new-window CMD\` runs the command in
a non-interactive context where Python's curses fails to initialise.

1. Verify the arcade is installed:
   \`\`\`bash
   ls ~/claudecade/claudcade.py 2>/dev/null
   \`\`\`
   If missing, download it:
   \`\`\`bash
   curl -L https://starlit-macaron-113a83.netlify.app/claudcade.zip -o /tmp/claudcade.zip && unzip -q /tmp/claudcade.zip -d ~/claudecade && rm /tmp/claudcade.zip
   \`\`\`

2. Find the user's attached tmux session, create a new window, and send the
   launch command interactively so curses gets a real TTY:
   \`\`\`bash
   SESSION=$(tmux list-clients -F '#{session_name}' 2>/dev/null | head -1)
   [ -z "$SESSION" ] && SESSION=$(tmux list-sessions -F '#{session_activity} #{session_name}' 2>/dev/null | sort -rn | head -1 | awk '{print $2}')
   tmux new-window -t "${SESSION}:" -n CLAUDCADE
   tmux send-keys -t "${SESSION}:CLAUDCADE" "clear && cd ~/claudecade && python3 claudcade.py; exit" Enter
   tmux select-window -t "${SESSION}:CLAUDCADE"
   \`\`\`

3. Tell the user: "Claudecade is running in the CLAUDCADE tmux window. Arrow keys to pick a game, Enter to launch it full-screen. Switch back here with tmux prefix + p."
`;

const SETUP_INSTRUCTIONS = `
# Claudecade Setup

Execute every step below using your Bash tool. Do not ask the user to type anything.

## 1. Install tmux if missing
\`\`\`bash
which tmux || brew install tmux 2>/dev/null || sudo apt-get install -y tmux 2>/dev/null
\`\`\`

## 2. Download and extract Claudcade
\`\`\`bash
curl -L https://starlit-macaron-113a83.netlify.app/claudcade.zip -o /tmp/claudcade.zip && unzip -q /tmp/claudcade.zip -d ~/claudecade && rm /tmp/claudcade.zip
\`\`\`

## 3. Install the /claudecade slash command
\`\`\`bash
mkdir -p ~/.claude/commands && rm -f ~/.claude/commands/claudcade.md && cat > ~/.claude/commands/claudecade.md << 'EOF'
${SLASH_COMMAND_CONTENT}EOF
\`\`\`

## 4. Confirm setup
Tell the user: "You're all set. Type /claudecade any time inside a tmux session to launch the arcade."

Requirements: Python 3.10+ · tmux · macOS, Linux, or WSL
`.trim();


const TOOLS = [
  {
    name: 'claudcade_setup',
    description: 'Get setup instructions to download and run Claudcade games locally. Call this when someone asks how to install, download, or play Claudcade.',
    inputSchema: { type: 'object', properties: {}, required: [] },
  },
  {
    name: 'claudcade_list_games',
    description: 'List all games available in Claudecade with descriptions.',
    inputSchema: { type: 'object', properties: {}, required: [] },
  },
  {
    name: 'claudcade_leaderboard',
    description: 'Fetch the live global leaderboard. Optionally filter by game.',
    inputSchema: {
      type: 'object',
      properties: {
        game:  { type: 'string', description: 'Game ID: ctype, claudtra, fight, finalclaudesy, superclaudio, claudturismo, or claudemon. Omit for all games.' },
        limit: { type: 'integer', description: 'Max scores to return (default 10)' },
      },
    },
  },
  {
    name: 'claudcade_submit_score',
    description: 'Submit a score to the global leaderboard.',
    inputSchema: {
      type: 'object',
      properties: {
        game:        { type: 'string',  description: 'Game ID: ctype, claudtra, fight, finalclaudesy, superclaudio, claudturismo, or claudemon' },
        player_name: { type: 'string',  description: 'Player name or number (e.g. "Player #42")' },
        score:       { type: 'integer', description: 'Score value' },
        extra:       { type: 'string',  description: 'Extra info e.g. "Wave 12" or "Lv 20"' },
      },
      required: ['game', 'player_name', 'score'],
    },
  },
  {
    name: 'claudcade_engine_docs',
    description: 'Get the Claudecade Engine API reference. Use this to help build terminal games with the engine.',
    inputSchema: { type: 'object', properties: {}, required: [] },
  },
  {
    name: 'claudcade_scaffold',
    description: 'Generate a starter game file using the Claudecade Engine for a given genre.',
    inputSchema: {
      type: 'object',
      properties: {
        genre: { type: 'string', description: 'Game genre: shooter, platformer, puzzle, rpg, or other' },
        title: { type: 'string', description: 'Game title' },
      },
      required: ['genre', 'title'],
    },
  },
];


function handleSetup() {
  return SETUP_INSTRUCTIONS;
}

function handleListGames() {
  return [
    `Claudcade — ${Object.keys(GAME_LABELS).length} games registered:\n`,
    ...Object.entries(GAME_LABELS).map(([id, label]) => `  • ${label}  (id: ${id})`),
    '',
    'Run python3 claudcade.py after cloning to launch the arcade.',
  ].join('\n');
}

/** @param {LeaderboardArgs} args */
async function handleLeaderboard(args) {
  const game  = args.game  || '';
  const limit = Math.min(parseInt(args.limit) || 10, 50);

  if (game && !VALID_GAMES.includes(game)) {
    return `Unknown game "${game}". Valid IDs: ${VALID_GAMES.join(', ')}`;
  }

  const { rows: scores } = game
    ? await pool.query(
        'SELECT player_name, score, extra, created_at FROM scores WHERE game=$1 ORDER BY score DESC, created_at ASC LIMIT $2',
        [game, limit]
      )
    : await pool.query(
        'SELECT game, player_name, score, extra, created_at FROM scores ORDER BY score DESC, created_at ASC LIMIT $1',
        [limit]
      );

  const { rows: stats } = await pool.query(
    'SELECT game, COUNT(*) AS entries, MAX(score) AS top_score FROM scores GROUP BY game ORDER BY game'
  );

  if (!scores.length) return 'No scores yet. Be the first!';

  const header = game
    ? `#   ${'PLAYER'.padEnd(22)} ${'SCORE'.padStart(9)}  DETAIL`
    : `#   ${'PLAYER'.padEnd(22)} ${'GAME'.padEnd(16)} ${'SCORE'.padStart(9)}`;
  const divider = '─'.repeat(header.length);

  const rows = scores.map((s, i) => {
    const medal = ['[1]', '[2]', '[3]'][i] ?? `${i + 1}. `;
    const name  = String(s.player_name).padEnd(22).slice(0, 22);
    const sc    = String(s.score).padStart(9);
    if (game) return `${medal} ${name} ${sc}  ${s.extra || ''}`;
    const g = (GAME_LABELS[s.game] || s.game).padEnd(16).slice(0, 16);
    return `${medal} ${name} ${g} ${sc}`;
  });

  const statLines = stats.map(s =>
    `  ${(GAME_LABELS[s.game] || s.game).padEnd(28)} best: ${Number(s.top_score).toLocaleString()}  entries: ${s.entries}`
  );

  return [header, divider, ...rows, '', '── Stats ──', ...statLines].join('\n');
}

/** @param {import('./_db').SubmitBody} args */
async function handleSubmitScore(args) {
  const { game, player_name, score, extra = '' } = args;
  if (!VALID_GAMES.includes(game)) {
    return `Unknown game "${game}". Valid: ${VALID_GAMES.join(', ')}`;
  }
  const { rows } = await pool.query(
    'INSERT INTO scores (game, player_name, score, extra) VALUES ($1,$2,$3,$4) RETURNING id',
    [game, String(player_name).slice(0, 24), parseInt(score), String(extra).slice(0, 64)]
  );
  const { rows: rank } = await pool.query(
    'SELECT COUNT(*)+1 AS rank FROM scores WHERE game=$1 AND score>$2',
    [game, parseInt(score)]
  );
  return `Score submitted! ${player_name} · ${GAME_LABELS[game]}\nScore: ${Number(score).toLocaleString()} · Global rank: #${rank[0].rank}`;
}

function handleEngineDocs() {
  return ENGINE_DOCS;
}

/** @param {ScaffoldArgs} args */
function handleScaffold(args) {
  const { genre = 'other', title = 'My Game' } = args;
  const gameId = title.toLowerCase().replace(/\s+/g, '_');

  const templates = {
    shooter: `\`\`\`python
"""${title} — a Claudcade space shooter"""
import random
from claudcade_engine import Engine, Scene, Entity, Renderer, Input
from claudcade_engine import CYAN, RED, YELLOW, WHITE, make_stars, scroll_stars

class Bullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx = 10.0
    def rect(self): return (self.x, self.y, 2.0, 1.0)
    def update(self, inp, tick):
        self.x += self.vx
        if self.x > 200: self.alive = False
    def draw(self, r):
        r.text(int(self.y), int(self.x), '=>', YELLOW, bold=True)

class GameScene(Scene):
    def on_enter(self):
        self.px, self.py = 5.0, 12.0
        self.bullets = []
        self.score = 0
        self.stars = make_stars(self.engine.H, self.engine.W)

    def update(self, inp, tick):
        H, W = self.engine.H, self.engine.W
        if inp.up:    self.py = max(3.0, self.py - 2)
        if inp.down:  self.py = min(H - 4.0, self.py + 2)
        if inp.fire and tick % 8 == 0:
            self.bullets.append(Bullet(self.px + 5, self.py))
        for b in self.bullets: b.update(inp, tick)
        self.bullets = [b for b in self.bullets if b.alive]
        scroll_stars(self.stars, W)
        if inp.pause: return 'pause'

    def draw(self, r: Renderer, tick: int):
        r.header('${title.toUpperCase()}', right=f'SCORE: {self.score:06d}', color=CYAN)
        r.outer_border()
        r.stars(self.stars)
        r.text(int(self.py), int(self.px), '>===)>', CYAN, bold=True)
        for b in self.bullets: b.draw(r)

class PauseScene(Scene):
    def update(self, inp, tick):
        if inp.pressed(ord('r'), ord('R')) or inp.pause: return 'game'
        if inp.pressed(ord('q'), ord('Q')): return 'quit'
    def draw(self, r, tick):
        self.engine._scenes['game'].draw(r, tick)
        r.pause_overlay('${title.toUpperCase()}', ['WASD  Move', 'J     Shoot', 'ESC   Pause'])

Engine('${title}', fps=30).scene('game', GameScene()).scene('pause', PauseScene()).run('game')
\`\`\``,

    platformer: `\`\`\`python
"""${title} — a Claudcade platformer"""
from claudcade_engine import Engine, Scene, PhysicsEntity, Renderer, Input
from claudcade_engine import CYAN, GREEN, YELLOW, WHITE

class Player(PhysicsEntity):
    gravity = 1.5
    def rect(self): return (self.x, self.y, 5.0, 3.0)

class GameScene(Scene):
    def on_enter(self):
        self.player = Player(8.0, 0.0)
        self.score  = 0
        self.floor  = 0  # set in draw based on H

    def update(self, inp, tick):
        p = self.player
        H = self.engine.H
        floor_y = H - 6.0
        if inp.left:  p.vx = -2.5
        elif inp.right: p.vx = 2.5
        else: p.vx = 0
        if inp.jump and p.grounded: p.vy = -9.0
        p.apply_physics(floor_y)
        if inp.pause: return 'pause'

    def draw(self, r: Renderer, tick: int):
        H, W = self.engine.H, self.engine.W
        r.header('${title.toUpperCase()}', right=f'SCORE: {self.score:06d}', color=GREEN)
        r.outer_border()
        r.text(H - 5, 1, '═' * (W - 2), WHITE)
        r.sprite(int(self.player.y), int(self.player.x), [' _O_ ', '/|\\->', '/ \\  '], CYAN)

class PauseScene(Scene):
    def update(self, inp, tick):
        if inp.pressed(ord('r'), ord('R')) or inp.pause: return 'game'
        if inp.pressed(ord('q'), ord('Q')): return 'quit'
    def draw(self, r, tick):
        self.engine._scenes['game'].draw(r, tick)
        r.pause_overlay('${title.toUpperCase()}', ['A/D  Move', 'SPC  Jump', 'ESC  Pause'])

Engine('${title}', fps=30).scene('game', GameScene()).scene('pause', PauseScene()).run('game')
\`\`\``,
  };

  const template = templates[genre] || templates.shooter.replace('shooter', genre);
  return `Here is a starter ${genre} game using the Claudecade Engine:\n\n${template}\n\nSave as ${gameId}.py next to claudcade_engine.py and run with: python3 ${gameId}.py\n\nTag @ConductorAILabs when you ship it!`;
}


async function handleMessage(msg) {
  const { id, method, params = {} } = msg;

  const ok  = (result) => ({ jsonrpc: '2.0', id, result });
  const err = (code, message) => ({ jsonrpc: '2.0', id, error: { code, message } });

  if (method === 'initialize') {
    return ok({
      protocolVersion: '2024-11-05',
      capabilities: { tools: {} },
      serverInfo: { name: 'claudcade', version: '1.0.0' },
    });
  }

  if (method === 'tools/list') {
    return ok({ tools: TOOLS });
  }

  if (method === 'tools/call') {
    const name = params.name || '';
    const args = params.arguments || {};
    try {
      let text;
      if (name === 'claudcade_setup')        text = handleSetup();
      else if (name === 'claudcade_list_games') text = handleListGames();
      else if (name === 'claudcade_leaderboard')  text = await handleLeaderboard(args);
      else if (name === 'claudcade_submit_score')  text = await handleSubmitScore(args);
      else if (name === 'claudcade_engine_docs')   text = handleEngineDocs();
      else if (name === 'claudcade_scaffold')      text = handleScaffold(args);
      else return err(-32601, `Unknown tool: ${name}`);
      return ok({ content: [{ type: 'text', text }] });
    } catch (e) {
      return ok({ content: [{ type: 'text', text: `Error: ${e.message}` }], isError: true });
    }
  }

  if (method === 'notifications/initialized') return null;
  if (id != null) return err(-32601, `Method not found: ${method}`);
  return null;
}


exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };

  if (event.httpMethod === 'OPTIONS') return { statusCode: 200, headers, body: '' };
  if (event.httpMethod !== 'POST')    return { statusCode: 405, headers, body: '' };

  let msg;
  try {
    msg = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON' }) };
  }

  const response = await handleMessage(msg);
  if (!response) return { statusCode: 204, headers, body: '' };
  return { statusCode: 200, headers, body: JSON.stringify(response) };
};
