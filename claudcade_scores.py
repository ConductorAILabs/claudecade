"""Claudcade score submission helper — shared by all games.

Exposes:
  get_player_id()       Cached integer player id (registers on first call)
  player_label()        "Player #42" or "Anonymous"
  submit_score(...)     Synchronous submit; returns merged dict (rank + local_best)
  submit_async(...)     Fire-and-forget version that fills result_box[0]
"""
from __future__ import annotations

import os, json, urllib.request, urllib.error, threading
from typing import TypedDict


class SubmitResult(TypedDict, total=False):
    """Shape returned by submit_score(). Local fields are always present;
    server fields are only present on a successful network round-trip."""
    local_best: int   # always present
    is_new_pb:  bool  # always present
    rank:       int   # server only
    id:         int   # server only
    success:    bool  # server only


class _PBEntry(TypedDict, total=False):
    """One row inside ~/.claudcade_scores.json keyed by game id."""
    best:  int
    extra: str


SITE        = "https://starlit-macaron-113a83.netlify.app"
ID_FILE     = os.path.expanduser("~/.claudcade_id")
SCORES_FILE = os.path.expanduser("~/.claudcade_scores.json")

_player_id: int | None = None
_id_lock   = threading.Lock()
_pb_lock   = threading.Lock()

# ── Player registration ────────────────────────────────────────────────────────

def get_player_id() -> int | None:
    global _player_id
    with _id_lock:
        if _player_id is not None:
            return _player_id
        if os.path.exists(ID_FILE):
            try:
                _player_id = int(open(ID_FILE).read().strip())
                return _player_id
            except (OSError, ValueError):
                pass  # corrupt or unreadable id file → fall through to re-register
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
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            return None  # offline / server down → caller falls back to "Anonymous"

def player_label() -> str:
    pid = get_player_id()
    return f"Player #{pid}" if pid else "Anonymous"

# ── Local personal-best cache ──────────────────────────────────────────────────

def _load_pb() -> dict[str, _PBEntry]:
    if not os.path.exists(SCORES_FILE):
        return {}
    try:
        with open(SCORES_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}

def _save_pb(data: dict[str, _PBEntry]) -> None:
    try:
        with open(SCORES_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass  # disk full / permissions → in-memory only, will retry next save

def _record_pb(game: str, score: int, extra: str) -> tuple[int, bool]:
    """Update the cached PB if `score` beats it. Returns (new_best, is_new_pb)."""
    with _pb_lock:
        data  = _load_pb()
        entry = data.get(game) or {}
        prev  = int(entry.get("best", 0)) if entry else 0
        if score > prev:
            data[game] = {"best": int(score), "extra": str(extra)[:64]}
            _save_pb(data)
            return score, True
        return prev, False

# ── Score submission ───────────────────────────────────────────────────────────

def submit_score(game: str, score: int, extra: str = "") -> SubmitResult:
    """Submit a score. Returns a dict with at least {local_best, is_new_pb};
    on successful network submit also includes server fields (rank, id, success).
    Never raises — network failures result in a local-only response."""
    new_best, is_new_pb = _record_pb(game, score, extra)
    result: SubmitResult = {"local_best": new_best, "is_new_pb": is_new_pb}

    pid  = get_player_id()
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
            server = json.loads(r.read())
        if isinstance(server, dict):
            # Copy only the documented server fields into the TypedDict, so the
            # type checker can validate them against SubmitResult's schema.
            if "rank"    in server: result["rank"]    = int(server["rank"])
            if "id"      in server: result["id"]      = int(server["id"])
            if "success" in server: result["success"] = bool(server["success"])
    except (urllib.error.URLError, OSError, ValueError):
        pass  # offline / server down → return local-only result
    return result

# A 1-element mutable container used by submit_async() to publish the result
# from the worker thread back to the caller. Shape: [None] before the thread
# completes, [SubmitResult] after. Callers create it as `_sub = [None]` and
# read `_sub[0]` once non-None.
ResultBox = list  # list[SubmitResult | None] — kept loose so existing `[None]` literals type-check

def submit_async(game: str, score: int, extra: str,
                 result_box: list[SubmitResult | None]) -> threading.Thread:
    """Fire-and-forget submission. Puts result dict into result_box[0]."""
    def _run() -> None:
        result_box[0] = submit_score(game, score, extra)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
