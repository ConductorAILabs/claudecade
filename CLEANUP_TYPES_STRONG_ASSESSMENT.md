# Type-Strengthening Assessment

Survey of weak/loose existing type hints in the Python and JS sources. Most of
this codebase is intentionally untyped Python; only places that already have
weak hints are listed below.

## Python

### claudcade_mcp.py
| Line | Current     | Possible       | Confidence | Notes |
|------|-------------|----------------|------------|-------|
| 22   | `JsonValue = Any` | (keep) | -          | Comment explicitly states Any is correct for nested JSON-RPC payloads. SKIP. |
| 363  | `id_: int | str | None = msg.get("id")` (already strong) | - | - | already specific. |

### claudcade_engine.py
| Line | Current                              | Stronger                | Confidence | Notes |
|------|--------------------------------------|-------------------------|------------|-------|
| 106  | `_FadeState.phase: str  # 'out' or 'in'` | `Literal['out', 'in']` | HIGH    | Assignments only ever use the two literals; comment confirms enum. APPLIED. |
| 589  | `payload: object | None = None`     | (keep)                  | -          | Truly arbitrary scene payload (any value type). SKIP. |
| 649  | `payload: object | None = None` (Engine.switch) | (keep)        | -          | Same as above. SKIP. |
| 768  | `payload: object | None = None` (loop local) | (keep)            | -          | Same. SKIP. |
| 1175 | `def save(self, data: dict) -> None` | `dict[str, object]`    | MED        | JSON-serialisable mapping — `object` keeps it loose but constrains keys to str. Low risk but no real gain over `dict` since JSON values are heterogeneous. |
| 1178 | `def load(self) -> dict | None`     | `dict[str, object] | None` | MED      | Same. |

### finalclaudesy/entities.py
| Line | Current                              | Stronger                | Confidence | Notes |
|------|--------------------------------------|-------------------------|------------|-------|
| 154  | `def save_dict(self) -> dict` (Character) | `dict[str, object]` | MED       | Constraining keys to str is correct, but `object` values force callers (from_dict, etc.) to cast/narrow at every read. Surrounding code is intentionally untyped, so this would add mypy noise without runtime benefit. SKIP. |
| 163  | `def from_dict(cls, d: dict) -> 'Character'` | `dict[str, object]` | MED  | Same — `object` breaks `[ ... for m in d['members']]` style without further cast support. SKIP. |
| 308  | `def save_dict(self) -> dict` (Party) | `dict[str, object]`   | MED        | Same. SKIP. |
| 321  | `def from_dict(cls, d: dict) -> 'Party'` | `dict[str, object]` | MED     | Same. SKIP. |

### claudcade_scores.py
Already strongly typed (`dict[str, _PBEntry]`, `_PBEntry` is a TypedDict). No
weak hints to strengthen.

## JavaScript

`netlify/functions/_db.js` and `mcp.js` already use rich JSDoc typedefs
(`GameId`, `ScoreRow`, `LeaderboardArgs`, etc.). No `any`, `*`, or unknown
JSDoc params anywhere in the Netlify functions. Other Netlify functions
(`leaderboard.js`, `submit-score.js`, `register.js`, `daily.js`, `rebuild.js`)
have no JSDoc at all — out of scope per task constraints (don't add types).

## Skipped (low/medium-confidence) candidates

1. `GameSave.save / load` (`claudcade_engine.py` lines 1175/1178) — strengthening
   `dict` to `dict[str, object]` is correct but adds no real safety since the
   values are inherently heterogeneous JSON. Borderline benefit.
2. All `payload: object | None` in `claudcade_engine.py` — `object` is already
   the strongest accurate type for an arbitrary scene payload. There is no
   stronger union without breaking the API contract.
3. `JsonValue = Any` in `claudcade_mcp.py` — author intentionally chose `Any`
   for genuinely-arbitrary JSON-RPC values; comment confirms intent.
