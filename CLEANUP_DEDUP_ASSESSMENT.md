# Claudcade Codebase Cleanup / Deduplication Assessment

This document lists duplication candidates found in the Claudcade arcade
codebase, where they live, and a confidence rating for whether each can be
consolidated safely without behavioural risk.

Read me first: claudcade_engine.py already contains a rich set of helpers
(at_safe, Renderer, Scene, draw_how_to_play, run_game, etc.). Most duplication
in the games is local helper code reimplementing things the engine
already does, or copy-paste between games.

## HIGH-CONFIDENCE candidates (safe to consolidate)

### 1. `frm()` helper in claudtra.py and fight.py - IDENTICAL
- Locations:
  - claudtra.py:64-67 (uses SW=7, SH=5)
  - fight.py:143-146   (uses SW=9, SH=6)
- Each game uses its own SW/SH module constants as defaults — the bodies are
  byte-identical.
- Status: Both files use `frm()` extensively for sprite tables. Moving it to
  the engine would require passing SW/SH at call sites. NOT WORTH IT — the
  per-file SW/SH defaults make the local definition correct. SKIP.
- Lines saved: 0 (after considering call-site impact). Confidence: HIGH that
  consolidation is NOT worth doing.

### 2. `_p = at_safe; p = lambda r,c,s,a=0: _p(scr,H,W,r,c,s,a)` in ctype + claudtra
- Locations:
  - ctype.py:600 + 604 + 657
  - claudtra.py:393 + 397 + 467 + 657
- Already imports `at_safe` from engine. The local `_p` alias and per-function
  lambda is a thin closure that captures `scr,H,W` for brevity. Removing it
  would touch dozens of call sites with marginal gain.
- Status: SKIP — cosmetic only.

### 3. `IntroScene` and `HowToPlayScene` classes in ctype.py + claudtra.py - IDENTICAL
- Locations:
  - ctype.py:941-954 (IntroScene + HowToPlayScene)
  - claudtra.py:757-770 (IntroScene + HowToPlayScene)
- Both define a Scene that takes a draw function module-attr. The two pairs of
  classes are byte-identical except for which `draw_intro`/`draw_how_to_play`
  they reference.
- Risk: Both files define `draw_intro` and `draw_how_to_play` as module-level
  free functions, so a generic factory can call them. fight.py uses a
  different IntroScene that goes to 'select' instead of 'howto', so it isn't
  fully shared. SKIP — going through claudcade_engine.py risks coupling.
- Lines saved: ~14. Confidence: MEDIUM (small win, mild risk).

### 4. `draw_pause()` wrapper around `Renderer.pause_overlay()` - REPEATED 3x
- Locations:
  - ctype.py:19-20 — `def draw_pause(scr, H, W): Renderer(scr,H,W).pause_overlay('C-TYPE', CONTROLS)`
  - claudtra.py:21-22 — same with 'Claudtra'
  - fight.py:20-21 — same with 'CLAUDE FIGHTER'
- Each game just constructs a Renderer and calls pause_overlay. This is barely
  a wrapper — the call sites already use `draw_pause(scr, H, W)`.
- Status: SKIP — three trivial 1-line wrappers, replacing them with inline
  `Renderer(...).pause_overlay(...)` would not measurably help readability.

### 5. `draw_how_to_play()` per-game wrappers - REPEATED 3x
- Locations:
  - ctype.py:22-42 — calls `_engine_how_to_play` with goal/controls/tips
  - claudtra.py:24-43 — same shape
  - fight.py:23-43 — same shape
- These all just feed game-specific text into the shared engine helper.
  They're already DRY — content is data per game.
- Status: SKIP — already factored.

### 6. Outer-border drawing pattern - REPEATED ~10x
- Pattern:
  ```
  p(0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
  p(H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
  for r in range(1, H-1):
      p(r, 0, '║', P(5)); p(r, W-1, '║', P(5))
  ```
- Locations: ctype.py:606-610, ctype.py:892-894, claudtra.py:399-404,
  claudtra.py:660-664, fight.py several, finalclaudesy/main.py:28-32, etc.
- The engine has `Renderer.outer_border()` but these games use raw curses
  calls inside their draw functions, not Renderer instances.
- Risk: each call site uses its own `p`/`put`/`safe_add` lambda and passes
  custom color attrs (some bold, some not, some color 5/6/2/etc). Replacing
  in place requires careful behavioral preservation.
- Status: MEDIUM — would save ~30 lines but risks subtle visual changes.
  SKIP for safety.

### 7. `_make_ctype_stars` vs `make_stars` (engine) - DUPLICATED FUNCTIONALITY
- Location: ctype.py:561-598 — defines a custom 100-star generator with deep
  background. The engine already has `make_stars(H, W, count, deep)` at
  claudcade_engine.py:1196-1223 which does the same job.
- Risk: ctype's version uses different tier weights, color choices, and char
  glyph mapping. The engine's `make_stars` is simpler and may produce a
  noticeably different starfield. Behavioural change is visible.
- Status: SKIP — visual difference would be observable.

### 8. `make_put()` factory in fight.py - LOCAL PUT HELPER
- Location: fight.py:457-462
  ```
  def make_put(scr, H, W):
      def put(r,c,s,a=0):
          try:
              if 0<=r<H-1 and 0<=c<W: scr.addstr(r,c,s[:W-c],a)
          except curses.error: pass
      return put
  ```
- This is exactly what `at_safe` from the engine does. fight.py doesn't
  import at_safe at all.
- Replacement: import at_safe and replace `put = make_put(scr,H,W)` with a
  closure that calls at_safe.
- Risk: at_safe checks `0 <= row < H - 1`, make_put checks `0<=r<H-1` — same.
  at_safe also slices via `s[:max(0, W-col)]`; make_put does `s[:W-c]` (same
  in practice when c >= 0).
- Lines saved: 6.
- Status: HIGH CONFIDENCE — drop-in replacement.

### 9. `finalclaudesy/ui.py:safe_add` duplicates `claudcade_engine.at_safe`
- Location: finalclaudesy/ui.py:6-12
- Behaviour: identical to at_safe (checks bounds, clips, eats curses.error)
  except `safe_add(scr, y, x, text, attr=0)` reads H,W from scr inside the
  function (at_safe takes them as args).
- Risk: callers already pass (scr, y, x, text, attr) — to switch to at_safe
  callers would need to pass H, W, OR safe_add could become a thin shim
  calling at_safe. The shim is cleaner and avoids touching every call site.
- Lines saved: 6 (function body collapses to a one-liner).
- Status: HIGH CONFIDENCE — make safe_add a thin shim.

### 10. `box()` in finalclaudesy/ui.py duplicates `Renderer.box` semantics
- Location: finalclaudesy/ui.py:15-24
- The engine `Renderer.box(row, col, h, w, color, title)` covers the same job.
  But callers use the standalone function with (scr, y, x, h, w, title, cp).
- Risk: changing call sites is invasive. SKIP.

### 11. `bar()` in finalclaudesy/ui.py duplicates `Renderer.bar`
- Same story as box — different signature, would touch many call sites. SKIP.

### 12. `setup_colors` import-and-call in finalclaudesy
- finalclaudesy/main.py:107-109 — manually does cbreak/noecho/keypad/nodelay/
  curs_set then calls setup_colors. The engine has `_init_curses()` which does
  the same things and also enables mouse. finalclaudesy doesn't use Engine,
  so this is its own loop. Replacement would be invasive.
- Status: SKIP.

### 13. Scoreboard submit_async usage - shared helper already
- All games already use claudcade_scores.submit_async — no duplication.
- Status: ALREADY DRY.

## Summary

After careful review, the only HIGH-confidence consolidations that are
clearly net-positive without behavioural risk are:

1. **fight.py: replace `make_put()` with `at_safe`** — saves 6 lines and
   removes a redundant helper; at_safe is byte-identical in behaviour.

2. **finalclaudesy/ui.py: make `safe_add` a shim around `at_safe`** — saves
   6 lines; safe_add already does what at_safe does.

Both changes are mechanical and verifiable without UI inspection.

Total lines saved: ~12.

## MEDIUM/LOW SKIPPED

- IntroScene/HowToPlayScene shared between ctype + claudtra (small win, mild
  risk of breaking scene-name strings)
- Outer-border pattern (~10 sites, but visual attrs vary subtly per call)
- `_make_ctype_stars` vs engine `make_stars` (visual difference)
