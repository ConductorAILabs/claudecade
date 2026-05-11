#!/usr/bin/env python3
"""
Claudcade MCP Server
Gives Claude Code tools to query and submit to the Claudcade global leaderboard.

Add to ~/.claude/settings.json:
  "mcpServers": {
    "claudcade": {
      "type": "stdio",
      "command": "python3",
      "args": ["/path/to/claudcade_mcp.py"]
    }
  }
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# JSON-RPC payloads carry arbitrary nested JSON; the wire format is the only
# constraint, so Any is genuinely the right shape here.
JsonValue   = Any
JsonObject  = dict[str, JsonValue]

SITE_URL = "https://starlit-macaron-113a83.netlify.app"

GAMES: dict[str, str] = {
    "ctype":          "C-TYPE (Space Shooter)",
    "claudtra":       "Claudtra (Action Platformer)",
    "fight":          "Claude Fighter (Fighting)",
    "finalclaudesy":  "Final Claudesy (JRPG)",
    # Placeholder cards on the site — not yet implemented in Python, but the
    # API accepts these IDs so future builds can submit scores immediately.
    "superclaudio":   "Super Claudio (Platformer)",
    "claudturismo":   "Claude Turismo (Racing)",
    "claudemon":      "Claudemon (Creature RPG)",
}

# ── Static content (mirrors mcp.js so the local stdio server has feature parity)

SLASH_COMMAND_CONTENT = """\
Launch the Claudecade arcade in a new tmux window.

The send-keys pattern is required: `tmux new-window CMD` runs the command in
a non-interactive context where Python's curses fails to initialise.

1. Verify the arcade is installed:
   ```bash
   ls ~/claudecade/claudcade.py 2>/dev/null
   ```
   If missing, download it:
   ```bash
   curl -L https://starlit-macaron-113a83.netlify.app/claudcade.zip -o /tmp/claudcade.zip && unzip -q /tmp/claudcade.zip -d ~/claudecade && rm /tmp/claudcade.zip
   ```

2. Find the user's attached tmux session, create a new window, and send the
   launch command interactively so curses gets a real TTY:
   ```bash
   SESSION=$(tmux list-clients -F '#{session_name}' 2>/dev/null | head -1)
   [ -z "$SESSION" ] && SESSION=$(tmux list-sessions -F '#{session_activity} #{session_name}' 2>/dev/null | sort -rn | head -1 | awk '{print $2}')
   tmux new-window -t "${SESSION}:" -n CLAUDCADE
   tmux send-keys -t "${SESSION}:CLAUDCADE" "clear && cd ~/claudecade && python3 claudcade.py; exit" Enter
   tmux select-window -t "${SESSION}:CLAUDCADE"
   ```

3. Tell the user: "Claudecade is running in the CLAUDCADE tmux window. Arrow keys to pick a game, Enter to launch it full-screen. Switch back here with tmux prefix + p."
"""

SETUP_INSTRUCTIONS = """\
# Claudecade Setup

Execute every step below using your Bash tool. Do not ask the user to type anything.

## 1. Install tmux if missing
```bash
which tmux || brew install tmux 2>/dev/null || sudo apt-get install -y tmux 2>/dev/null
```

## 2. Download and extract Claudcade
```bash
curl -L https://starlit-macaron-113a83.netlify.app/claudcade.zip -o /tmp/claudcade.zip && unzip -q /tmp/claudcade.zip -d ~/claudecade && rm /tmp/claudcade.zip
```

## 3. Install the /claudcade slash command
```bash
mkdir -p ~/.claude/commands && cat > ~/.claude/commands/claudcade.md << 'EOF'
""" + SLASH_COMMAND_CONTENT + """EOF
```

## 4. Confirm setup
Tell the user: "You're all set. Type /claudcade any time inside a tmux session to launch the arcade."

Requirements: Python 3.10+ . tmux . macOS, Linux, or WSL
"""

ENGINE_DOCS = """\
# Claudecade Engine - Quick Reference

Copy claudcade_engine.py into your project. No pip install needed.

```python
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
        r.header("MY GAME", left="hp hp hp", right="SCORE: 000", color=CYAN)
        r.outer_border()
        r.text(int(self.y), int(self.x), '@', YELLOW, bold=True)

Engine("My Game", fps=30).scene("game", GameScene()).run("game")
```

## Key classes
- Engine("title", fps) - manages loop and scenes. Chain .scene(name, Scene()).run(first)
- Scene - override on_enter(), update(inp, tick), draw(r, tick)
- Input - inp.up/down/left/right/fire/jump/confirm/pause, inp.pressed(ord('x'))
- Renderer - r.text, r.center, r.box, r.bar, r.sprite, r.header, r.footer, r.outer_border, r.menu, r.stars, r.pause_overlay, r.gameover_screen
- Entity - base class with x, y, vx, vy, alive, rect(), collides()
- PhysicsEntity - adds gravity, grounded, apply_physics(floor_y)
- AnimSprite - named states with frame cycling
- Camera - follow(tx, ty, lerp), world_to_screen(wx, wy, W, H)
- Particles - explode(col, row), spark(), update(), draw(r)

## Colors: CYAN=1 RED=2 GREEN=3 YELLOW=4 WHITE=5 MAGENTA=6 HIGHLIGHT=7 BLUE=8

Full docs: https://github.com/ConductorAILabs/claudecade
"""

# ── MCP wire protocol (stdio JSON-RPC 2.0) ────────────────────────────────────

def send(obj: JsonObject) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def err(id_: int | str | None, code: int, msg: str) -> None:
    send({"jsonrpc":"2.0","id":id_,"error":{"code":code,"message":msg}})

def ok(id_: int | str | None, result: JsonObject) -> None:
    send({"jsonrpc":"2.0","id":id_,"result":result})

# ── HTTP helpers ───────────────────────────────────────────────────────────────

def get_json(path: str) -> JsonObject:
    url = SITE_URL + path
    req = urllib.request.Request(url, headers={"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        result: JsonObject = json.loads(r.read())
        return result

def post_json(path: str, data: JsonObject) -> JsonObject:
    url   = SITE_URL + path
    body  = json.dumps(data).encode()
    req   = urllib.request.Request(url, data=body,
                                   headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        result: JsonObject = json.loads(r.read())
        return result

# ── Tool implementations ───────────────────────────────────────────────────────

def tool_list_games() -> str:
    lines = ["Available Claudcade games:\n"]
    for key, label in GAMES.items():
        lines.append(f"  • {key:<18} — {label}")
    return "\n".join(lines)

def tool_get_leaderboard(game: str = "", limit: int = 10) -> str:
    try:
        qs  = ""
        if game: qs += f"?game={urllib.parse.quote(game)}&limit={limit}"
        else:    qs += f"?limit={limit}"
        data   = get_json("/api/leaderboard" + qs)
        scores = data.get("scores", [])
        stats  = data.get("stats", [])
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"Error fetching leaderboard: {e}"

    if not scores:
        return "No scores yet." + (" Be the first!" if game else "")

    lines = [f"{'#':<4} {'PLAYER':<20} {'GAME':<18} {'SCORE':>9}",
             "─" * 54]
    for i, s in enumerate(scores):
        medal = ["[1]", "[2]", "[3]"][i] if i < 3 else "   "
        game_label = GAMES.get(s.get("game",""), s.get("game",""))[:16]
        lines.append(
            f"{medal} {i+1:<3} {s['player_name']:<20} {game_label:<18} {s['score']:>9,}"
        )

    if stats:
        lines.append("\n── Per-game totals ──")
        for s in stats:
            lines.append(f"  {GAMES.get(s['game'], s['game']):<28} "
                         f"best: {int(s['top_score']):,}  entries: {s['entries']}")
    return "\n".join(lines)

def tool_submit_score(game: str, player_name: str, score: int, extra: str = "") -> str:
    if game not in GAMES:
        return f"Unknown game '{game}'. Valid: {', '.join(GAMES)}"
    try:
        score = int(score)
    except (ValueError, TypeError):
        return "Score must be an integer."
    try:
        res = post_json("/api/submit-score", {
            "game": game, "player_name": player_name,
            "score": score, "extra": str(extra)
        })
        rank = res.get("rank", "?")
        return (f"Score submitted! {player_name} · {GAMES[game]}\n"
                f"Score: {score:,}  ·  Global rank: #{rank}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"Submission failed: {e}"

def tool_setup() -> str:
    return SETUP_INSTRUCTIONS

def tool_engine_docs() -> str:
    return ENGINE_DOCS

def tool_scaffold(genre: str = "other", title: str = "My Game") -> str:
    """Generate a starter game using the Claudcade Engine."""
    game_id = title.lower().replace(" ", "_")
    TITLE   = title.upper()

    shooter = f'''```python
"""{title} - a Claudcade space shooter"""
import random
from claudcade_engine import Engine, Scene, Entity, Renderer, Input
from claudcade_engine import CYAN, RED, YELLOW, WHITE, make_stars, scroll_stars

class Bullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y); self.vx = 10.0
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
        self.score   = 0
        self.stars   = make_stars(self.engine.H, self.engine.W)

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
        r.header('{TITLE}', right=f'SCORE: {{self.score:06d}}', color=CYAN)
        r.outer_border()
        r.stars(self.stars)
        r.text(int(self.py), int(self.px), '>===)>', CYAN, bold=True)
        for b in self.bullets: b.draw(r)

Engine('{title}', fps=30).scene('game', GameScene()).run('game')
```'''

    platformer = f'''```python
"""{title} - a Claudcade platformer"""
from claudcade_engine import Engine, Scene, PhysicsEntity, Renderer, Input
from claudcade_engine import CYAN, GREEN, YELLOW, WHITE

class Player(PhysicsEntity):
    gravity = 1.5
    def rect(self): return (self.x, self.y, 5.0, 3.0)

class GameScene(Scene):
    def on_enter(self):
        self.player = Player(8.0, 0.0)
        self.score  = 0

    def update(self, inp, tick):
        p = self.player
        H = self.engine.H
        floor_y = H - 6.0
        if inp.left:    p.vx = -2.5
        elif inp.right: p.vx =  2.5
        else:           p.vx =  0
        if inp.jump and p.grounded: p.vy = -9.0
        p.apply_physics(floor_y)
        if inp.pause: return 'pause'

    def draw(self, r: Renderer, tick: int):
        H, W = self.engine.H, self.engine.W
        r.header('{TITLE}', right=f'SCORE: {{self.score:06d}}', color=GREEN)
        r.outer_border()
        r.text(H - 5, 1, '=' * (W - 2), WHITE)
        r.sprite(int(self.player.y), int(self.player.x), [' _O_ ', '/|\\\\', '/ \\\\ '], CYAN)

Engine('{title}', fps=30).scene('game', GameScene()).run('game')
```'''

    template = {"shooter": shooter, "platformer": platformer}.get(genre, shooter)
    return (f"Here is a starter {genre} game using the Claudecade Engine:\n\n"
            f"{template}\n\nSave as {game_id}.py next to claudcade_engine.py and "
            f"run with: python3 {game_id}.py\n\nTag @ConductorAILabs when you ship it!")

# ── Tool schema ────────────────────────────────────────────────────────────────

TOOLS: list[JsonObject] = [
    {
        "name": "claudcade_setup",
        "description": "Get setup instructions to download and run Claudcade games locally. Call this when someone asks how to install, download, or play Claudcade.",
        "inputSchema": {"type":"object","properties":{},"required":[]},
    },
    {
        "name": "claudcade_list_games",
        "description": "List all games available on Claudcade with their IDs.",
        "inputSchema": {"type":"object","properties":{},"required":[]},
    },
    {
        "name": "claudcade_leaderboard",
        "description": (
            "Fetch the Claudcade global leaderboard. "
            "Optionally filter by game ID (ctype, claudtra, fight, finalclaudesy, superclaudio, claudturismo, claudemon)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "game":  {"type":"string","description":"Game ID to filter by (omit for all games)"},
                "limit": {"type":"integer","description":"Max rows to return (default 10, max 50)"},
            },
            "required": [],
        },
    },
    {
        "name": "claudcade_submit_score",
        "description": "Submit a score to the Claudcade global leaderboard.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "game":        {"type":"string","description":"Game ID (ctype, claudtra, fight, finalclaudesy, superclaudio, claudturismo, claudemon)"},
                "player_name": {"type":"string","description":"Player name (max 24 chars)"},
                "score":       {"type":"integer","description":"Score value"},
                "extra":       {"type":"string","description":"Extra info e.g. 'Wave 12' or 'Lv 20'"},
            },
            "required": ["game","player_name","score"],
        },
    },
    {
        "name": "claudcade_engine_docs",
        "description": "Get the Claudecade Engine API reference. Use this to help build terminal games with the engine.",
        "inputSchema": {"type":"object","properties":{},"required":[]},
    },
    {
        "name": "claudcade_scaffold",
        "description": "Generate a starter game file using the Claudecade Engine for a given genre.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "genre": {"type":"string","description":"Game genre: shooter, platformer, puzzle, rpg, or other"},
                "title": {"type":"string","description":"Game title"},
            },
            "required": ["genre","title"],
        },
    },
]

# ── Main loop ──────────────────────────────────────────────────────────────────

def handle(msg: JsonObject) -> None:
    id_:    int | str | None = msg.get("id")
    method: str              = msg.get("method","")
    params: JsonObject       = msg.get("params") or {}

    if method == "initialize":
        ok(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities":    {"tools": {}},
            "serverInfo":      {"name": "claudcade", "version": "1.0.0"},
        })

    elif method == "tools/list":
        ok(id_, {"tools": TOOLS})

    elif method == "tools/call":
        name  = params.get("name","")
        args  = params.get("arguments") or {}
        try:
            if name == "claudcade_setup":
                text = tool_setup()
            elif name == "claudcade_list_games":
                text = tool_list_games()
            elif name == "claudcade_leaderboard":
                text = tool_get_leaderboard(
                    game  = args.get("game",""),
                    limit = int(args.get("limit", 10)),
                )
            elif name == "claudcade_submit_score":
                text = tool_submit_score(
                    game        = args.get("game",""),
                    player_name = args.get("player_name","Anonymous"),
                    score       = args.get("score", 0),
                    extra       = args.get("extra",""),
                )
            elif name == "claudcade_engine_docs":
                text = tool_engine_docs()
            elif name == "claudcade_scaffold":
                text = tool_scaffold(
                    genre = args.get("genre","other"),
                    title = args.get("title","My Game"),
                )
            else:
                err(id_, -32601, f"Unknown tool: {name}"); return
            ok(id_, {"content":[{"type":"text","text":text}]})
        except Exception as e:
            ok(id_, {"content":[{"type":"text","text":f"Error: {e}"}],"isError":True})

    elif method == "notifications/initialized":
        pass  # no response needed

    else:
        if id_ is not None:
            err(id_, -32601, f"Method not found: {method}")

def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        handle(msg)

if __name__ == "__main__":
    main()
