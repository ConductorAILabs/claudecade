# Cleanup Assessment — Claudcade Codebase

Tools used: vulture, ruff (F401/F811/F841), pyflakes, plus repo-wide grep cross-referencing
across `*.py`, `*.md`, `*.html`, `*.js`, `*.json`, `*.txt`, `*.sh`.

Reference: every "unused" candidate was checked against:
- `claudcade-engine/` (distributed copy / examples, treats engine as public API)
- `claudcade-site/public/` (HTML demos, hosted engine.py mirror)
- `claudcade-site/netlify/functions/` (MCP / leaderboard / score)
- `claudcade_mcp.py` (MCP scaffolds, mention engine symbols by name)
- `tests/` (smoke + pure tests)
- `*.md` skill files

## Public-API surface (DO NOT remove anything below)

`claudcade_engine.py` is a public, ship-as-a-single-file module. Examples in
`claudcade-engine/` import many symbols vulture flags as "unused" (run_game,
make_stars, scroll_stars, ParticleDict, StarDict, distance, ease_in/out,
AnimSprite, Camera, Particles, Timer, Audio, GameSave, sign, Renderer.dialog,
gameover_screen, footer, vbar, Color/Input properties). MCP scaffold in
`claudcade_mcp.py` and mirrored `claudcade-site/netlify/functions/mcp.js` also
mention these by name in generated templates and the `engine_docs` payload.

Skipped: every vulture finding inside `claudcade_engine.py`.

## HIGH confidence — to be removed

| Location | Symbol | Type | Search result |
|---|---|---|---|
| ctype.py:9 | `INTRO, PLAY, GAME_OVER, PAUSE, HOW_TO_PLAY = range(5)` | Dead enum (Scene-based engine, never referenced) | grep across repo: only the definition line |
| claudtra.py:10 | `INTRO, PLAY, GAME_OVER, PAUSE, HOW_TO_PLAY = range(5)` | Same — game uses Scene state machine | only definition line |
| fight.py:7 | `INTRO, SELECT, COUNTDOWN, FIGHT, PAUSE, HOW_TO_PLAY = range(6)` | Same | "FIGHT" / "ROUND" appearances are inside string literals, not the constant |
| ctype.py:5 / claudtra.py:5 / fight.py:3 | `time` import | Unused import | no `time.` references |
| ctype.py:6 / claudtra.py:6 / fight.py:4 | `setup_colors` import | Unused (Engine() does it internally now) | no calls inside file |
| fight.py:578 | local `w = max(...)` | Assigned, never read | only line 578 |
| fight.py:854 | local `cp = ...` (loop body) | Replaced with inline `st['cp'] if sel else 5` | grep within loop: cp not read |
| finalclaudesy/battle.py:2 | `import math` | Unused | no `math.` reference in file |
| finalclaudesy/battle.py:3 | `ENEMIES as ENEMY_DATA` | Unused alias | no ENEMY_DATA reference |
| finalclaudesy/battle.py:5 | `box`, `menu_list` from .ui | Unused imports | no calls |
| finalclaudesy/entities.py:3 | `SPELLS` | Unused import | no reference |
| finalclaudesy/explore.py:5 | `STORY` | Unused import | no reference in file |
| finalclaudesy/explore.py:6 | `EnemyInstance` | Unused import | no reference |
| finalclaudesy/explore.py:7 | `box`, `bar`, `menu_list` | Unused imports | no calls |
| finalclaudesy/explore.py:121 | `p0, p1, p2 = self.party.members` | Tuple unpack never used; loop reuses `self.party.members` | only line 121 |
| finalclaudesy/explore.py:314 | local `shop = SHOPS.get(...)` | Never read | only line 314 |
| finalclaudesy/explore.py:495 | `self._sub = 0` | Instance attr, never accessed | only line 495 |
| finalclaudesy/main.py:4 | `ENCOUNTER_GROUPS` | Unused import | no reference in main.py |
| finalclaudesy/main.py:5 | `EnemyInstance` | Unused import | no reference |
| finalclaudesy/main.py:145 | local `prev = state` | Never read | only line 145 |
| finalclaudesy/battle.py:222 | `self._anim_timer = 0` | Instance attr, never accessed | only line 222 |
| finalclaudesy/ui.py:3 | `from claudcade_engine import setup_colors` | Unused import | no calls in ui.py |

## MEDIUM confidence — intentionally skipped

1. **`menu_list` in finalclaudesy/ui.py** — defined but never called anywhere.
   Removed only from importers; left the function in place. The mirrored
   `claudcade-engine/finalclaudesy/ui.py` defines it too, suggesting it is a
   ui-helpers menu intended to be shipped with the kit. Conservative.
2. **`PLAYER_START` in finalclaudesy/data.py** — local data constant, no reads.
   The mirrored `claudcade-engine/claudemon/main.py` does import a `PLAYER_START`
   from its own package, so the symbol name is meaningful. Could be a forgotten
   spawn position; safer to leave.
3. **`ResultBox` in claudcade_scores.py:135** — defined as `list` alias for
   doc/typing, no external import. Module is a public API used by all games and
   the doc comment block treats it as a documented type. Keep.

## LOW confidence (skipped)

- `claudcade.py:354` `except curses.error as e` — instructions forbid touching claudcade.py.
- All `_ParticleDict`/`BulletDict`/`PlatformDict`/`ParticleDict` in `claudcade_engine.py`
  — public TypedDicts shipped to game authors.
- `Renderer.dialog`, `Renderer.footer`, `Renderer.vbar`, `Renderer.gameover_screen`,
  `Audio.play`, `GameSave.*`, `make_stars`, `scroll_stars`, `Camera`, `Particles`,
  `Timer`, `AnimSprite`, `run_game`, `distance`, `ease_*`, `sign` — all in
  `claudcade-engine/` examples and/or MCP scaffold strings.

## Implementation plan

- Edit `ctype.py`, `claudtra.py`, `fight.py`, `finalclaudesy/{battle,explore,entities,main,ui}.py`.
- Run `python3 -c 'import MOD'` + ruff after each file.
- Do **not** touch `claudcade_engine.py`, `claudcade.py`, or `launch_claudcade.sh`.
- Do **not** touch `claudcade-engine/` mirrored copies (different ship target).
