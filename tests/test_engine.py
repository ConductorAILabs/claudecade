"""Pure-Python tests for claudcade_engine helpers (no curses runtime).

Run with: python3 tests/test_engine.py
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

import claudcade_engine as e


# ── helpers ────────────────────────────────────────────────────────────────────
PASS = 0
FAIL: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS
    if cond:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL.append(f"{name} {detail}")
        print(f"  FAIL  {name}  {detail}")


# ── math helpers ──────────────────────────────────────────────────────────────
check("clamp lo",            e.clamp(-1, 0, 10) == 0)
check("clamp hi",            e.clamp(11, 0, 10) == 10)
check("clamp mid",           e.clamp(5, 0, 10) == 5)
check("lerp 0",              e.lerp(0, 100, 0.0) == 0.0)
check("lerp 1",              e.lerp(0, 100, 1.0) == 100.0)
check("lerp half",           e.lerp(0, 100, 0.5) == 50.0)
check("ease_in 0",           e.ease_in(0) == 0.0)
check("ease_in 1",           e.ease_in(1) == 1.0)
check("ease_out 0",          e.ease_out(0) == 0.0)
check("ease_out 1",          e.ease_out(1) == 1.0)
check("ease_in_out monotone", e.ease_in_out(0.3) < e.ease_in_out(0.7))
check("sign neg",            e.sign(-5) == -1.0)
check("sign zero",           e.sign(0) == 0.0)
check("sign pos",            e.sign(7) == 1.0)
check("distance 3-4-5",      abs(e.distance(0, 0, 3, 4) - 5.0) < 1e-9)


# ── Camera ─────────────────────────────────────────────────────────────────────
cam = e.Camera()
cam.set_bounds(0, 100, 0, 50)
cam.x = cam.y = 0
cam.follow(50, 25, lerp=1.0)
check("camera follow exact",  cam.x == 50 and cam.y == 25)
cam.x = cam.y = 0
cam.follow(50, 25, lerp=0.5)
check("camera lerp half",     cam.x == 25.0 and cam.y == 12.5)
cam.x = 1000; cam.y = 1000
cam.follow(2000, 2000, lerp=1.0)
check("camera respects bounds", cam.x == 100 and cam.y == 50)
row, col = cam.world_to_screen(60, 30, W=80, H=24)
check("world_to_screen sane",  isinstance(row, int) and isinstance(col, int))


# ── Particles ──────────────────────────────────────────────────────────────────
p = e.Particles()
p.spawn(10, 5, vx=1, vy=0, life=3)
check("particle spawned",     p.count == 1)
p.update(); p.update(); p.update()
check("particle expired after life", p.count == 0)

p.explode(20, 10, count=12)
check("explode creates count", p.count == 12)


# ── Timer ──────────────────────────────────────────────────────────────────────
t = e.Timer(1.0)
check("timer not done init", not t.done)
fired = t.tick(0.5)
check("timer not fired half", not fired and not t.done)
fired = t.tick(0.6)
check("timer fires past dur", fired and t.done)
fired_again = t.tick(0.5)
check("timer doesn't refire", not fired_again)
check("timer remaining 0",    t.remaining == 0.0)
t.reset()
check("timer reset clears",   not t.done and t.frac == 0.0)

t2 = e.Timer(1.0, auto_reset=True)
t2.tick(1.5)
check("auto_reset stays not done", not t2.done)


# ── AnimSprite ─────────────────────────────────────────────────────────────────
states = {
    'idle': [['A'], ['B']],
    'run':  [['C'], ['D'], ['E']],
}
sp = e.AnimSprite(states, ticks_per_frame=2)
check("anim initial state",   sp.state == 'idle')
check("anim initial frame",   sp.current() == ['A'])
sp.tick(); sp.tick()
check("anim cycles after ticks_per_frame", sp.current() == ['B'])
sp.tick(); sp.tick()
check("anim wraps to first",  sp.current() == ['A'])

sp.set_state('run')
check("set_state changes",    sp.state == 'run' and sp.current() == ['C'])
sp.set_state('run')  # same state — should not restart
sp.tick()
check("same state doesn't reset timer", sp._timer == 1)
sp.set_state('run', force=True)
check("force=True resets",    sp._frame == 0)


# ── Input ──────────────────────────────────────────────────────────────────────
prev = e.Input()
prev.keys = {ord('a')}
cur = e.Input()
cur.keys = {ord('a'), ord('b')}
cur._prev = prev

check("pressed a",            cur.pressed(ord('a')))
check("pressed b",            cur.pressed(ord('b')))
check("just_pressed b only",  cur.just_pressed(ord('b')))
check("just_pressed not a",   not cur.just_pressed(ord('a')))

next_ = e.Input()
next_._prev = cur
next_.keys = {ord('b')}
check("just_released a",      next_.just_released(ord('a')))
check("just_released not b",  not next_.just_released(ord('b')))

# property aliases
inp = e.Input(); inp.keys = {ord('w')}
check("up alias",  inp.up)
inp.keys = {curses_key_left := 260}  # curses.KEY_LEFT
import curses as _curses
inp.keys = {_curses.KEY_LEFT}
check("left arrow", inp.left)


# ── Renderer.bar / box bounds-safety (no curses; verify the math via mock) ────
# curses.color_pair() requires initscr() — stub it for headless testing.
import curses as _stub_curses
_stub_curses.color_pair = lambda n: 0
for _attr in ("A_BOLD", "A_DIM", "A_REVERSE", "A_BLINK"):
    if not hasattr(_stub_curses, _attr):
        setattr(_stub_curses, _attr, 0)


class _MockScr:
    def __init__(self, H=24, W=80):
        self.H = H; self.W = W
        self.calls: list[tuple[int, int, str]] = []
    def getmaxyx(self): return self.H, self.W
    def addstr(self, r, c, s, attr=0):
        self.calls.append((r, c, s))


scr = _MockScr()
r = e.Renderer(scr, 24, 80)
r.text(5, 10, "hello")
check("text writes once",     len(scr.calls) == 1 and scr.calls[0][2] == "hello")

scr.calls.clear()
r.text(-1, 0, "off-top")
r.text(0, -1, "off-left")
r.text(0, 80, "off-right")
r.text(23, 0, "last-row-skipped")  # Renderer skips H-1 by design
check("off-screen text skipped", len(scr.calls) == 0)

scr.calls.clear()
r.bar(5, 0, value=30, maximum=100, width=10, label="HP")
fills = [c for c in scr.calls if "█" in c[2]]
empty = [c for c in scr.calls if "░" in c[2]]
check("bar 30%: 3 filled",    fills and len(fills[0][2]) == 3)
check("bar 30%: 7 empty",     empty and len(empty[0][2]) == 7)


# ── summary ────────────────────────────────────────────────────────────────────
total = PASS + len(FAIL)
print(f"\n{PASS}/{total} passed.")
if FAIL:
    for f in FAIL:
        print(f"  - {f}")
sys.exit(0 if not FAIL else 1)
