#!/usr/bin/env python3
"""
Claudcade MCP Server
Gives Claude Code tools to query and submit to the Claudcade global leaderboard.

https://github.com/ConductorAILabs/claudcade

Add to ~/.claude/settings.json:
  "mcpServers": {
    "claudcade": {
      "type": "stdio",
      "command": "python3",
      "args": ["/absolute/path/to/claudcade_mcp.py"]
    }
  }
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.parse
import urllib.error
from typing import cast

SITE_URL = "https://starlit-macaron-113a83.netlify.app"

GAMES: dict[str, str] = {
    "ctype":          "C-TYPE (Space Shooter)",
    "claudtra":       "Claudtra (Action Platformer)",
    "fight":          "Claude Fighter (Fighting)",
    "finalclaudesy":  "FINAL CLAUDESY (JRPG)",
}


def send(obj: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def err(id_: object, code: int, msg: str) -> None:
    send({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}})

def ok(id_: object, result: object) -> None:
    send({"jsonrpc": "2.0", "id": id_, "result": result})


def get_json(path: str) -> dict[str, object]:
    url = SITE_URL + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())  # type: ignore[return-value]

def post_json(path: str, data: dict[str, object]) -> dict[str, object]:
    url  = SITE_URL + path
    body = json.dumps(data).encode()
    req  = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())  # type: ignore[return-value]


def tool_list_games() -> str:
    lines = ["Available Claudcade games:\n"]
    for key, label in GAMES.items():
        lines.append(f"  • {key:<18} — {label}")
    return "\n".join(lines)

def tool_get_leaderboard(game: str = "", limit: int = 10) -> str:
    try:
        qs     = f"?game={urllib.parse.quote(game)}&limit={limit}" if game else f"?limit={limit}"
        data   = get_json("/api/leaderboard" + qs)
        scores = cast(list[dict[str, object]], data.get("scores", []))
        stats  = cast(list[dict[str, object]], data.get("stats",  []))
    except Exception as e:
        return f"Error fetching leaderboard: {e}"

    if not scores:
        return "No scores yet." + (" Be the first!" if game else "")

    lines = [f"{'#':<4} {'PLAYER':<20} {'GAME':<18} {'SCORE':>9}", "─" * 54]
    for i, s in enumerate(scores):
        medal      = ["[1]", "[2]", "[3]"][i] if i < 3 else "   "
        game_label = GAMES.get(str(s.get("game", "")), str(s.get("game", "")))[:16]
        lines.append(f"{medal} {i+1:<3} {s['player_name']!s:<20} {game_label:<18} {cast(int, s['score']):>9,}")

    if stats:
        lines.append("\n── Per-game totals ──")
        for s in stats:
            lines.append(f"  {GAMES.get(str(s['game']), str(s['game'])):<28} "
                         f"best: {cast(int, s['top_score']):,}  entries: {s['entries']}")
    return "\n".join(lines)

def tool_submit_score(game: str, player_name: str, score: int | str, extra: str = "") -> str:
    if game not in GAMES:
        return f"Unknown game '{game}'. Valid: {', '.join(GAMES)}"
    try:
        score = int(score)
    except (ValueError, TypeError):
        return "Score must be an integer."
    try:
        res  = post_json("/api/submit-score", {
            "game": game, "player_name": player_name,
            "score": score, "extra": str(extra),
        })
        rank = res.get("rank", "?")
        return (f"Score submitted! {player_name} · {GAMES[game]}\n"
                f"Score: {score:,}  ·  Global rank: #{rank}")
    except Exception as e:
        return f"Submission failed: {e}"


TOOLS: list[dict[str, object]] = [
    {
        "name": "claudcade_list_games",
        "description": "List all games available on Claudcade with their IDs.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "claudcade_leaderboard",
        "description": (
            "Fetch the Claudcade global leaderboard. "
            "Optionally filter by game ID (ctype, claudtra, fight, finalclaudesy)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "game":  {"type": "string", "description": "Game ID to filter by (omit for all games)"},
                "limit": {"type": "integer", "description": "Max rows to return (default 10, max 50)"},
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
                "game":        {"type": "string",  "description": "Game ID (ctype, claudtra, fight, finalclaudesy)"},
                "player_name": {"type": "string",  "description": "Player name (max 24 chars)"},
                "score":       {"type": "integer", "description": "Score value"},
                "extra":       {"type": "string",  "description": "Extra info e.g. 'Wave 12' or 'Lv 20'"},
            },
            "required": ["game", "player_name", "score"],
        },
    },
]


def handle(msg: dict[str, object]) -> None:
    id_    = msg.get("id")
    method = msg.get("method", "")
    params = cast(dict[str, object], msg.get("params") or {})

    if method == "initialize":
        ok(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities":    {"tools": {}},
            "serverInfo":      {"name": "claudcade", "version": "1.0.0"},
        })

    elif method == "tools/list":
        ok(id_, {"tools": TOOLS})

    elif method == "tools/call":
        name = str(params.get("name", ""))
        args = cast(dict[str, object], params.get("arguments") or {})
        try:
            if name == "claudcade_list_games":
                text = tool_list_games()
            elif name == "claudcade_leaderboard":
                text = tool_get_leaderboard(
                    game  = str(args.get("game", "")),
                    limit = cast(int, args.get("limit", 10)),
                )
            elif name == "claudcade_submit_score":
                text = tool_submit_score(
                    game        = str(args.get("game", "")),
                    player_name = str(args.get("player_name", "Anonymous")),
                    score       = args.get("score", 0),  # type: ignore[arg-type]
                    extra       = str(args.get("extra", "")),
                )
            else:
                err(id_, -32601, f"Unknown tool: {name}")
                return
            ok(id_, {"content": [{"type": "text", "text": text}]})
        except Exception as e:
            ok(id_, {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True})

    elif method == "notifications/initialized":
        pass  # no response needed

    else:
        if id_ is not None:
            err(id_, -32601, f"Method not found: {method}")

def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict):
            handle(msg)

if __name__ == "__main__":
    main()
