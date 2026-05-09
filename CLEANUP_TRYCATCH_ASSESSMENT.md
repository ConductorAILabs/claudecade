# Try/Except Cleanup Assessment

Scope: `claudcade_engine.py`, `claudcade_mcp.py`, `ctype.py`, `claudtra.py`, `fight.py`,
`finalclaudesy/*.py`, plus JS Netlify functions under `claudcade-site/netlify/functions/`.
Excluded per instructions: `claudcade.py`, `launch_claudcade.sh`, plus build/test/site
mirror code (the public mirror is byte-identical to the engine).

## Summary by file

### claudcade_engine.py

| Line | Catches | Purpose | Classification | Confidence to remove |
|---|---|---|---|---|
| 239 | `curses.error` | `curses.getmouse()` can raise on partial mouse seq | LEGITIMATE | DO NOT REMOVE |
| 263 | `curses.error` | `at_safe()` — bounds-safe addstr wrapper, REQUIRED per instructions | LEGITIMATE | DO NOT REMOVE |
| 299 | `curses.error` | `Renderer.text()` addstr edge guard | LEGITIMATE | DO NOT REMOVE |
| 493/500/507/518/526 | `curses.error` | `pause_overlay` addstr edge guards | LEGITIMATE | DO NOT REMOVE |
| 681 | `Exception as exc` | Top-level crash handler — restores terminal, prints traceback | LEGITIMATE | DO NOT REMOVE |
| 684 | `curses.error` | `endwin()` cleanup during crash unwind | LEGITIMATE | DO NOT REMOVE |
| 744/803/821 | `curses.error` | resize-guard / fade-overlay addstr edge guards | LEGITIMATE | DO NOT REMOVE |
| 1126/1135 | `curses.error` | `curses.beep()` / `curses.flash()` may fail on TERM=dumb | LEGITIMATE | DO NOT REMOVE |
| 1148 | `OSError` | `subprocess.Popen([afplay,...])` — guards missing audio binary | LEGITIMATE | DO NOT REMOVE |
| 1181 | `OSError, json.JSONDecodeError` | `GameSave.load()` corrupt save file | LEGITIMATE | DO NOT REMOVE |
| 1292 | `curses.error` | `curses.mousemask()` not always supported | LEGITIMATE | DO NOT REMOVE |
| 1308 | `curses.error` | `_put` addstr edge guard | LEGITIMATE | DO NOT REMOVE |
| 1365 | `Exception as e` | `run_game` shared crash handler | LEGITIMATE | DO NOT REMOVE |
| 1368 | `curses.error` | `endwin()` cleanup | LEGITIMATE | DO NOT REMOVE |

### claudcade_mcp.py

| Line | Catches | Purpose | Classification | Confidence to remove |
|---|---|---|---|---|
| 157 | `Exception` | HTTP GET to leaderboard — network errors | LEGITIMATE | DO NOT REMOVE |
| 189 | `ValueError, TypeError` | `int(score)` external input validation | LEGITIMATE | DO NOT REMOVE |
| 193 | `Exception` | HTTP POST to leaderboard | LEGITIMATE | DO NOT REMOVE |
| 380 | `Exception` | Tool dispatch — JSON-RPC contract requires error in result | LEGITIMATE | DO NOT REMOVE |
| 421 | `json.JSONDecodeError` | stdin JSON-RPC frame decode | LEGITIMATE | DO NOT REMOVE |

### finalclaudesy/ui.py

| Line | Catches | Purpose | Classification | Confidence to remove |
|---|---|---|---|---|
| 9 | `curses.error` | `safe_add()` bounds-safe addstr — REQUIRED per instructions | LEGITIMATE | DO NOT REMOVE |

### finalclaudesy/main.py

| Line | Catches | Purpose | Classification | Confidence to remove |
|---|---|---|---|---|
| 153 | `OSError, json.JSONDecodeError, KeyError, ValueError` | Read save file for NewGame+ flag | LEGITIMATE | DO NOT REMOVE |
| 167 | same | Load save on title-screen `[L]` | LEGITIMATE | DO NOT REMOVE |
| 176 | same | Load save for NewGame+ start | LEGITIMATE | DO NOT REMOVE |
| 290 | `OSError` | Persist NewGame+ unlock | LEGITIMATE | DO NOT REMOVE |

### fight.py

| Line | Catches | Purpose | Classification | Confidence to remove |
|---|---|---|---|---|
| 459 | `curses.error` | `make_put` bounds-safe addstr — REQUIRED per instructions | LEGITIMATE | DO NOT REMOVE |

### ctype.py / claudtra.py

No try/except blocks present. Both rely on the engine's `at_safe()` / `_p()` helpers.

### JS Netlify functions

| File | Line | Catches | Purpose | Classification |
|---|---|---|---|---|
| leaderboard.js | 48 | DB error | pg pool query — must return HTTP 500 | LEGITIMATE |
| mcp.js | 353 | tool call | JSON-RPC error contract | LEGITIMATE |
| mcp.js | 386 | JSON parse | Invalid wire body → 400 | LEGITIMATE |
| register.js | 15 | DB error | pg pool insert → 500 | LEGITIMATE |
| rebuild.js | 26 | execFile error | python3 build script may fail | LEGITIMATE |
| submit-score.js | 24 | JSON parse | Invalid body → 400 | LEGITIMATE |
| submit-score.js | 48 | DB error | pg insert + rate-limit query → 500 | LEGITIMATE |

## Conclusion

Every try/except (and try/catch) in the in-scope files handles a real, documented
external failure: curses terminal-edge writes, file/save I/O, JSON wire decode, HTTP /
network failures, child process spawn, or top-level crash recovery. There are no
defensive `except Exception: pass` blocks swallowing arbitrary bugs, and no
redundant blocks guarding against impossible upstream conditions.

No removals to implement.
