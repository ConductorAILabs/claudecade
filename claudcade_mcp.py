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

import json, sys, urllib.request, urllib.parse, urllib.error
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
    "finalclaudesy":  "FINAL CLAUDESY (JRPG)",
}

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
        return json.loads(r.read())

def post_json(path: str, data: JsonObject) -> JsonObject:
    url   = SITE_URL + path
    body  = json.dumps(data).encode()
    req   = urllib.request.Request(url, data=body,
                                   headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

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
    except Exception as e:
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
    except Exception as e:
        return f"Submission failed: {e}"

# ── Tool schema ────────────────────────────────────────────────────────────────

TOOLS: list[JsonObject] = [
    {
        "name": "claudcade_list_games",
        "description": "List all games available on Claudcade with their IDs.",
        "inputSchema": {"type":"object","properties":{},"required":[]},
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
                "game":        {"type":"string","description":"Game ID (ctype, claudtra, fight, finalclaudesy)"},
                "player_name": {"type":"string","description":"Player name (max 24 chars)"},
                "score":       {"type":"integer","description":"Score value"},
                "extra":       {"type":"string","description":"Extra info e.g. 'Wave 12' or 'Lv 20'"},
            },
            "required": ["game","player_name","score"],
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
            if name == "claudcade_list_games":
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
