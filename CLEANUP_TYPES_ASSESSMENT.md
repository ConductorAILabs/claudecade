# Type/Data-shape Consolidation Assessment

Survey of duplicate or duplicate-able type definitions across the Claudcade
codebase. Engine = `claudcade_engine.py`. Games = `ctype.py`, `claudtra.py`,
`fight.py`, `finalclaudesy/*.py`. JS = `claudcade-site/netlify/functions/*.js`.

## Engine TypedDicts already centralized
The engine defines `StarDict`, `_ParticleDict`, `BulletDict` (total=False),
`PlatformDict`, `ParticleDict`, `_FadeState`, plus `Color` (IntEnum). These are
the canonical homes. Tests in `tests/test_engine.py` cover engine types.
JS side: `_db.js` already centralizes `GameId`, `ScoreRow`, `StatRow`,
`LeaderboardResponse`, `SubmitOkResponse`, `SubmitBody`, `RegisterResponse`,
`ErrorResponse`. All other JS functions reference them via comments
(no duplicate `@typedef`s found). No JS work to do.

## Findings

### 1. claudtra bullet dict matches engine `BulletDict` exactly — HIGH CONFIDENCE
Engine `BulletDict` is `{wx, y, vx, owner, dead}` (total=False, dead is
optional). `claudtra.py` World creates bullets at lines 184, 246, 255 and
mutates `b['dead']` at lines 333, 338, 348. The keys match exactly.
Action: import `BulletDict` and annotate `World.bullets: list[BulletDict]`
as a non-invasive type-only consolidation. (Skipped: do NOT add type hints to
function signatures — separate task. Annotating a list field is a pure
cross-file consistency win.)

### 2. claudtra platform dict matches engine `PlatformDict` exactly — HIGH CONFIDENCE
Engine `PlatformDict` is `{x, y, w}`. `claudtra.py` line 321 appends exactly
`{'x': float(x), 'y': y, 'w': float(w)}`. Identical shape.
Action: annotate `World.platforms: list[PlatformDict]`.

### 3. ctype starfield dict matches engine `StarDict` exactly — HIGH CONFIDENCE
Engine `StarDict` is `{x, y, spd, ch, cp}`. `ctype.py::_make_ctype_stars`
returns dicts with exactly those keys (lines 581-587 and the deep-landmark
block). The local generator legitimately differs from `make_stars()` (custom
weight tiers and deep landmarks) so we keep the function but type its return
as `list[StarDict]`. (`claudcade-engine/ctype.py` already does the analogous
import.)
Action: import `StarDict` in `ctype.py` and annotate the helper's return
type / `Game.stars` field.

### 4. ctype `pbullets`/`ebullets` dict shape — MEDIUM CONFIDENCE, SKIPPED
ctype bullets are `{x, y, vx, vy, ...}` plus optional `heavy`, `beam`, `len`.
Engine `BulletDict` uses `wx` (world-x), not `x`, and lacks `vy`. Different
coordinate convention (screen-x in ctype vs world-x in claudtra). Forcing a
shared TypedDict here would require either renaming engine fields or
inventing a second `ScreenBulletDict`, which violates "don't introduce new
abstractions just because you can." Skip.

### 5. ctype hit-spark dict vs engine `_ParticleDict` — MEDIUM CONFIDENCE, SKIPPED
ctype particles use `{x, y, vx, vy, ttl, ch, cp}`. Engine `_ParticleDict`
uses `{x, y, vx, vy, life, max_life, char, color}`. Same conceptual idea,
different field names (`ttl` vs `life/max_life`, `ch/cp` vs `char/color`).
Renaming would be churn and the engine `Particles` class is unused by the
game (it has its own `spark()` method). Skip — cosmetic-only.

### 6. claudtra particle dict (`{wx, y, vx, vy, ttl, ch}`) — LOW CONFIDENCE, SKIPPED
Has `wx` (world-x) and no `cp`. Doesn't match engine `_ParticleDict` or
ctype's particle. Unique to side-scrolling coord system. Skip.

### 7. fight `sparks` (list of lists, not dicts) — LOW CONFIDENCE, SKIPPED
`fight.py` uses `[cx, cy, vx, vy, char, ttl]` — a positional list, not a dict.
Refactoring this to a dict or dataclass would change indexing throughout the
update/draw paths. Out of scope: this isn't a duplicate of an existing type.

### 8. fight `combo` per-side dict (`{n, t, peak}`) — LOW CONFIDENCE, SKIPPED
Local to `fight.py::Game`. No duplicate elsewhere — nothing to consolidate.

### 9. ctype `Game.beam` and `Player.beam` inline shapes — LOW CONFIDENCE, SKIPPED
`{'x','y','ttl','rows','power'}` and `{'x','y','vx','vy','beam','len'}`. Used
in only one file; not duplicated.

### 10. finalclaudesy classes — N/A
`Character`, `EnemyInstance`, `Party`, `Battle`, `WorldMap` etc. are all
domain-specific classes already defined once in `finalclaudesy/entities.py`
or other module files. No duplication. Nothing to consolidate.

### 11. Game intro/scene state IntEnum-style ranges — LOW CONFIDENCE, SKIPPED
Each game declares e.g. `INTRO, PLAY, GAME_OVER, PAUSE, HOW_TO_PLAY = range(5)`
(ctype, claudtra) or `range(6)` for fight. The set of states differs per game;
forcing a common Enum would over-couple the games.

## Plan
Implement findings 1, 2, and 3 (HIGH CONFIDENCE only). Each is a minimal,
purely-additive type annotation referencing types already exported from the
engine — no behavior change, no signature changes, no new abstractions.
