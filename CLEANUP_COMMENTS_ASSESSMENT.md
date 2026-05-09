# Comment Cleanup Assessment

Codebase scope: Python game files (`ctype.py`, `fight.py`, `claudtra.py`,
`claudcade_engine.py`, `claudcade_mcp.py`, `claudcade_scores.py`,
`finalclaudesy/*.py`) plus Netlify JS functions
(`claudcade-site/netlify/functions/*.js`).

Overall the codebase is in better shape than typical AI-generated code.
Most module-level docstrings, sprite-block labels, and structural section
markers (`# ── Section ──`) are useful and were KEPT. The bulk of the slop
is concentrated in the `finalclaudesy/` UI render methods, which were
clearly produced by an "add visual styling" pass that left a comment for
every block.

## Categories Found

### 1. AI-flavor "with [visual|bold|block|decorative] styling/borders"
Restating the obvious next-line draw call. Highest-volume offender.
Counts (case-sensitive grep, # lines):
- `finalclaudesy/battle.py`:    9
- `finalclaudesy/explore.py`:   13
- `finalclaudesy/main.py`:      3
- `claudtra.py`:                2
- `ctype.py`:                   1
Total: ~28 such comments.

Examples:
- `# Bold border with decorative pattern`        (main.py:27, before `safe_add('╔...╗')`)
- `# Bold decorative header with block styling`  (explore.py:99)
- `# HUD with visual improvements`               (explore.py:120)
- `# Tab bar with visual styling`                (explore.py:622)
- `# Action menu with visual prominence`         (battle.py:661)
- `# HP bar with block fill` / `# MP bar with block fill` (battle.py:635/641)

### 2. Restating-the-obvious comments
- `# Bold border` (battle.py:728) immediately above the border-draw block.
- `# Bold header` / `# Decorative header` (explore.py:261, 99) similar.

### 3. Historical "was X / previously" narration
- `# Unified animation rate (was 8 — felt sluggish vs player's 5/7)` (claudtra.py:214)
- `# smoother burst than the previous four; the second frame eases…`   (ctype.py:149-151)

### 4. Acceptable "previous" references (KEEP)
- `claudcade_engine.py:179` "Input owns its own previous-frame snapshot"
  describes a real invariant, not a refactor history. Kept.
- `fight.py:404` "Combo: increment if last hit was within window" describes
  current behaviour. Kept.
- `fight.py:875` "Payload may be int (legacy: char only)" documents a real
  back-compat path the code branches on. Kept.

### 5. Useful section markers (KEEP)
The `# ── Outer border ──`, `# ── Player ship ──`, `# ── HUD row 1 ──`
patterns in `ctype.py`, `fight.py`, `claudtra.py` chunk long render
functions and aid scanning. These remain.

### 6. Sprite-block labels (KEEP per task instructions)
`# Power 0 — basic fighter`, `# Grunt: fast, dumb, single-line dart`,
`# WARRIOR sprites` etc. These label the ASCII art; they stay.

### 7. JavaScript files
`mcp.js`, `_db.js`, `leaderboard.js`, `submit-score.js`, `register.js`,
`daily.js` are already clean — comments explain non-obvious things
(rate-limit reasoning, deterministic seed, why placeholder game IDs
exist). No changes needed.

## Plan

DELETE the ~28 "with visual/bold styling" decorator comments outright —
the very next line shows the styling, the comment adds nothing.

REPLACE the two historical comments with a one-liner that explains the
*current* invariant (not what changed):
- `claudtra.py:214` → drop the "was 8" history; explain the rate value.
- `ctype.py:149-151` → trim three lines into one explaining the cadence.

KEEP everything else: section markers, sprite labels, module docstrings,
comments documenting non-obvious math, edge cases, or invariants.
