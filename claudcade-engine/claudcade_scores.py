"""Claudcade score submission helper — shared by all games."""
from __future__ import annotations

import os, json, sys, urllib.request, threading

SITE    = "https://starlit-macaron-113a83.netlify.app"
ID_FILE = os.path.expanduser("~/.claudcade_id")

_player_id  = None   # cached after first load
_id_lock    = threading.Lock()
def get_player_id() -> int | None:
    global _player_id
    with _id_lock:
        if _player_id is not None:
            return _player_id
        if os.path.exists(ID_FILE):
            try:
                _player_id = int(open(ID_FILE).read().strip())
                return _player_id
            except Exception as e:
                print(f"[claudcade_scores] Could not read player ID from {ID_FILE}: {e}", file=sys.stderr)
        try:
            req = urllib.request.Request(
                SITE + "/api/register",
                data=b"{}",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                pid = json.loads(r.read())["player_id"]
            with open(ID_FILE, "w") as f:
                f.write(str(pid))
            _player_id = pid
            return _player_id
        except Exception as e:
            print(f"[claudcade_scores] Registration failed: {e}", file=sys.stderr)
            return None

def player_label() -> str:
    pid = get_player_id()
    return f"Player #{pid}" if pid else "Anonymous"
def submit_score(game: str, score: int, extra: str = "") -> dict[str, object] | None:
    pid = get_player_id()
    name = f"Player #{pid}" if pid else "Anonymous"
    try:
        body = json.dumps({
            "game": game, "player_name": name,
            "score": score, "extra": extra,
        }).encode()
        req = urllib.request.Request(
            SITE + "/api/submit-score",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[claudcade_scores] Score submission failed ({game}): {e}", file=sys.stderr)
        return None

def submit_async(game: str, score: int, extra: str,
                 result_box: list[dict[str, object] | None]) -> threading.Thread:
    """Fire-and-forget submission. Puts result dict (or None on failure) into result_box[0]."""
    def _run():
        result_box[0] = submit_score(game, score, extra)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
