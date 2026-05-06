#!/usr/bin/env python3
"""Claude & Field — Track and Field arcade game for Claudecade."""
from __future__ import annotations

import curses
import math
import time

from claudcade_engine import run_game, setup_colors
from claudcade_scores import player_label, submit_async

# ── Constants ─────────────────────────────────────────────────────────────────

FPS = 30
SPF = 1.0 / FPS

A_KEYS    = {ord('a'), ord('A')}
D_KEYS    = {ord('d'), ord('D')}
MASH_KEYS = A_KEYS | D_KEYS

EVENTS = [
    dict(id='dash',     name='100m DASH',    unit='s', wr= 9.58, qual=15.0, hi=False),
    dict(id='longjump', name='LONG JUMP',    unit='m', wr= 8.95, qual= 4.5, hi=True),
    dict(id='hurdles',  name='110m HURDLES', unit='s', wr=12.80, qual=18.0, hi=False),
    dict(id='javelin',  name='JAVELIN',      unit='m', wr=98.48, qual=28.0, hi=True),
    dict(id='hammer',   name='HAMMER THROW', unit='m', wr=86.74, qual=22.0, hi=True),
]

# Athlete sprites: (top_line, bot_line)
_R0 = (' ◙ ', '╱ ╲')   # run frame 0
_R1 = (' ◙ ', '╲ ╱')   # run frame 1
_ST = (' ◙ ', '║ ║')   # standing
_JP = (' ◙╱', '╱   ')  # in air
_TH = ('━◙━', '╲ ╱')   # throw wind-up
_KO = (' ✕ ', '─┸─')   # dead/fallen

# ── Utilities ─────────────────────────────────────────────────────────────────

def _p(scr: curses.window, y: int, x: int, s: str, attr: int = 0) -> None:
    try:
        scr.addstr(y, x, s, attr)
    except curses.error:
        pass

def _cx(W: int, s: str) -> int:
    return max(0, (W - len(s)) // 2)

def _bar(frac: float, width: int = 20, fill: str = '█', empty: str = '░') -> str:
    n = max(0, min(width, round(frac * width)))
    return fill * n + empty * (width - n)

def _box(scr: curses.window, y: int, x: int, h: int, w: int, attr: int = 0) -> None:
    _p(scr, y,     x, '┌' + '─' * (w - 2) + '┐', attr)
    for i in range(1, h - 1):
        _p(scr, y + i, x, '│' + ' ' * (w - 2) + '│', attr)
    _p(scr, y + h - 1, x, '└' + '─' * (w - 2) + '┘', attr)

def _sleep(dt: float) -> None:
    if dt > 0:
        time.sleep(dt)

def _wait_space(scr: curses.window) -> bool:
    """Block until SPACE or ESC. Returns False if ESC."""
    scr.nodelay(False)
    while True:
        k = scr.getch()
        if k == ord(' '):
            scr.nodelay(True)
            return True
        if k == 27:
            scr.nodelay(True)
            return False

def _hud(scr: curses.window, H: int, W: int, ev: dict, centre: str = '') -> None:
    left  = f" ◈ {ev['name']}"
    right = f" WR {ev['wr']}{ev['unit']} "
    gap   = W - len(left) - len(right)
    mid   = centre[:gap].center(gap)
    _p(scr, 0, 0, (left + mid + right)[:W], curses.color_pair(3) | curses.A_BOLD)

# ── Mash speed tracker ────────────────────────────────────────────────────────

class Mash:
    """Converts alternating A/D keypresses into a 0–100 speed value."""

    def __init__(self, decay: float = 24.0, gain: float = 16.0, cap: float = 100.0) -> None:
        self.speed = 0.0
        self.decay = decay
        self.gain  = gain
        self.cap   = cap
        self._side: str | None = None
        self._t:    float      = 0.0

    def key(self, k: int) -> bool:
        if k not in MASH_KEYS:
            return False
        side = 'a' if k in A_KEYS else 'd'
        now  = time.time()
        if side != self._side:
            interval = max(0.04, min(0.55, now - self._t)) if self._t else 0.4
            self.speed = min(self.cap, self.speed + self.gain / interval * 0.10)
            self._side = side
        self._t = now
        return True

    def tick(self, dt: float) -> None:
        self.speed = max(0.0, self.speed - self.decay * dt)

    @property
    def frac(self) -> float:
        return self.speed / self.cap

    def bar(self, w: int = 22) -> str:
        return _bar(self.frac, w)

    def bar_colored(self, w: int = 22) -> tuple[str, int]:
        b = self.bar(w)
        if self.frac > 0.75:
            return b, curses.color_pair(2) | curses.A_BOLD
        if self.frac > 0.40:
            return b, curses.color_pair(3)
        return b, curses.color_pair(4)

# ── Event: 100m Dash ──────────────────────────────────────────────────────────

def _dash(scr: curses.window, H: int, W: int, ev: dict) -> float:
    mash = Mash(decay=22, gain=18)
    scr.nodelay(True)

    TY    = H // 2 - 1
    LEFT  = 3
    RIGHT = W - 10
    TL    = RIGHT - LEFT

    cpu_spd = 0.0
    cpu_x   = float(LEFT)
    ply_x   = float(LEFT)
    result  : float | None = None
    tick    = 0

    # Countdown
    for cd in (3, 2, 1, 0):
        scr.erase()
        _hud(scr, H, W, ev, 'A / D  alternate to sprint')
        _p(scr, TY - 1, LEFT, '─' * TL + '╢FINISH')
        _p(scr, TY,     LEFT, '─' * TL + '╢      ')
        _p(scr, TY + 1, LEFT, '─' * TL + '╢      ')
        _p(scr, TY + 3, LEFT, '─' * TL + '╢      ')
        _p(scr, TY + 4, LEFT, '─' * TL + '╢      ')
        _p(scr, TY,     LEFT, _ST[0], curses.color_pair(5) | curses.A_BOLD)
        _p(scr, TY + 1, LEFT, _ST[1], curses.color_pair(5))
        _p(scr, TY + 3, LEFT, _ST[0], curses.color_pair(4))
        _p(scr, TY + 4, LEFT, _ST[1], curses.color_pair(4))
        label = str(cd) if cd else 'GO!'
        bx = _cx(W, '│  GO!  │')
        _p(scr, TY - 4, bx, '┌───────┐')
        c  = curses.color_pair(2 if not cd else 3) | curses.A_BOLD
        _p(scr, TY - 3, bx, f'│ {label:^5} │', c)
        _p(scr, TY - 2, bx, '└───────┘')
        _p(scr, H - 2, 2, 'P1: ◙  CPU: ×', curses.color_pair(1))
        scr.refresh()
        time.sleep(1.0 if cd else 0.25)

    start = time.time()
    last  = start

    while True:
        now = time.time()
        dt  = now - last
        last = now
        k   = scr.getch()
        mash.key(k)
        if k == 27:
            return -1.0

        mash.tick(dt)
        ply_x = min(float(RIGHT), ply_x + mash.frac * 42.0 * dt)
        cpu_spd += (0.60 - cpu_spd) * 1.8 * dt
        cpu_x   = min(float(RIGHT), cpu_x + cpu_spd * 42.0 * dt)

        elapsed = now - start

        if ply_x >= RIGHT and result is None:
            result = elapsed
        if cpu_x >= RIGHT and result is None:
            result = elapsed + 0.8  # CPU won — penalise

        scr.erase()
        _hud(scr, H, W, ev, f'TIME  {elapsed:.2f}s')

        _p(scr, TY - 1, LEFT, '─' * TL + '╢FINISH')
        _p(scr, TY,     LEFT, ' ' * TL + '╢')
        _p(scr, TY + 1, LEFT, '─' * TL + '╢')
        _p(scr, TY + 3, LEFT, ' ' * TL + '╢')
        _p(scr, TY + 4, LEFT, '─' * TL + '╢')

        af = (tick // 4) % 2
        rf = (_R0, _R1)[af]
        px, cpx = int(ply_x), int(cpu_x)
        _p(scr, TY,     px,  rf[0], curses.color_pair(5) | curses.A_BOLD)
        _p(scr, TY + 1, px,  rf[1], curses.color_pair(5))
        _p(scr, TY + 3, cpx, rf[0], curses.color_pair(4))
        _p(scr, TY + 4, cpx, rf[1], curses.color_pair(4))

        bstr, bc = mash.bar_colored(26)
        _p(scr, H - 3, 2, f'SPEED [{bstr}] {int(mash.speed):3d}%', bc)
        _p(scr, H - 2, 2, 'Alternate  A / D  as fast as possible', curses.color_pair(1))

        if result is not None:
            scr.refresh()
            time.sleep(0.6)
            return result

        tick += 1
        scr.refresh()
        _sleep(SPF - (time.time() - now))

# ── Event: Long Jump ──────────────────────────────────────────────────────────

def _longjump(scr: curses.window, H: int, W: int, ev: dict) -> float:
    best = 0.0
    ATTEMPTS = 3

    for attempt in range(1, ATTEMPTS + 1):
        mash  = Mash(decay=18, gain=20)
        scr.nodelay(True)
        TY    = H // 2
        LEFT  = 2
        RIGHT = W - 4
        BOARD = LEFT + (RIGHT - LEFT) * 3 // 4   # takeoff board position
        ply_x = float(LEFT)

        phase  = 'run'   # 'run' → 'air' → 'land'
        air_t  = 0.0
        jump_v = 0.0     # horizontal speed at takeoff
        fault  = False
        dist   = 0.0
        tick   = 0
        last   = time.time()

        while True:
            now = time.time()
            dt  = now - last
            last = now
            k   = scr.getch()
            mash.key(k)
            if k == 27:
                return -1.0

            scr.erase()
            _hud(scr, H, W, ev, f'Attempt {attempt}/{ATTEMPTS}  |  BEST {best:.2f}m')
            _p(scr, H - 2, 2, 'A/D: sprint    SPACE: jump at  ┃  board', curses.color_pair(1))

            if phase == 'run':
                mash.tick(dt)
                ply_x = min(float(BOARD + 3), ply_x + mash.frac * 36.0 * dt)

                if ply_x >= BOARD + 3:
                    # Ran through the board without jumping — foul
                    fault = True
                    phase = 'done'
                elif k == ord(' '):
                    # Jump from wherever the player is — earlier = shorter distance
                    jump_v = mash.frac * min(1.0, ply_x / max(1, BOARD))
                    air_t  = 0.0
                    phase  = 'air'

                # Draw track
                _p(scr, TY + 2, LEFT, '─' * (BOARD - LEFT) + '┃' + '─' * (RIGHT - BOARD))
                _p(scr, TY + 3, LEFT, ' ' * (BOARD - LEFT) + '▲' + ' ' * (RIGHT - BOARD))
                _p(scr, TY + 4, LEFT, ' ' * (BOARD - LEFT) + 'BOARD' )

                # Draw athlete
                af = (tick // 3) % 2
                rf = (_R0, _R1)[af]
                px = int(ply_x)
                _p(scr, TY,     px, rf[0], curses.color_pair(5) | curses.A_BOLD)
                _p(scr, TY + 1, px, rf[1], curses.color_pair(5))

                # Board proximity warning
                dist_to_board = BOARD - ply_x
                if dist_to_board < 0:
                    _p(scr, H - 3, 2, '▶▶ JUMP NOW ◀◀', curses.color_pair(4) | curses.A_BOLD)
                elif dist_to_board < 12:
                    _p(scr, H - 3, 2, f'◀ BOARD IN {int(dist_to_board):2d} ▶', curses.color_pair(2) | curses.A_BOLD)

            elif phase == 'air':
                air_t    += dt
                duration  = 0.6 + jump_v * 0.8
                air_frac  = min(1.0, air_t / duration)   # clamp: never exceed 1.0
                parabola  = 4 * air_frac * (1 - air_frac)
                peak_h    = 4
                air_x     = BOARD + int(jump_v * 50 * air_frac)
                air_y     = max(1, TY + 1 - int(parabola * peak_h))  # clamp above row 1

                _p(scr, TY + 2, LEFT, '─' * (BOARD - LEFT) + '┃' + '─' * (RIGHT - BOARD))

                # Trail of previous arc positions
                for step in range(1, int(air_frac * 14)):
                    t = step / 14.0
                    ax = BOARD + int(jump_v * 50 * t)
                    ay = max(1, TY + 1 - int(4 * t * (1 - t) * peak_h))
                    _p(scr, ay, ax, '·', curses.color_pair(3))

                _p(scr, air_y,     air_x, _JP[0], curses.color_pair(5) | curses.A_BOLD)
                _p(scr, air_y + 1, air_x, _JP[1], curses.color_pair(5))

                if air_frac >= 1.0:
                    dist  = round(jump_v * 8.5, 2)
                    phase = 'land'

            elif phase == 'land':
                land_x = BOARD + int(jump_v * 50)
                _p(scr, TY + 2, LEFT, '─' * (BOARD - LEFT) + '┃' + '─' * (RIGHT - BOARD))
                _p(scr, TY,     land_x, _ST[0], curses.color_pair(5) | curses.A_BOLD)
                _p(scr, TY + 1, land_x, _ST[1], curses.color_pair(5))
                # distance marker
                _p(scr, TY + 2, land_x, '│')
                _p(scr, TY + 3, BOARD,  f'└──── {dist:.2f}m ────')
                _p(scr, H - 3, 2, f'DISTANCE: {dist:.2f}m', curses.color_pair(2) | curses.A_BOLD)
                scr.refresh()
                time.sleep(1.8)
                if dist > best:
                    best = dist
                break

            elif phase == 'done':
                if fault:
                    _p(scr, TY + 2, LEFT, '─' * (BOARD - LEFT) + '┃' + '─' * (RIGHT - BOARD))
                    _p(scr, TY, int(ply_x), _KO[0], curses.color_pair(4) | curses.A_BOLD)
                    _p(scr, TY + 1, int(ply_x), _KO[1], curses.color_pair(4))
                    bx = _cx(W, '│  FOUL!  │')
                    _p(scr, H // 2 - 2, bx, '┌─────────┐', curses.color_pair(4))
                    _p(scr, H // 2 - 1, bx, '│  FOUL!  │', curses.color_pair(4) | curses.A_BOLD)
                    _p(scr, H // 2,     bx, '└─────────┘', curses.color_pair(4))
                    scr.refresh()
                    time.sleep(1.5)
                    break

            bstr, bc = mash.bar_colored(26)
            _p(scr, H - 4, 2, f'SPEED [{bstr}] {int(mash.speed):3d}%', bc)

            tick += 1
            scr.refresh()
            _sleep(SPF - (time.time() - now))

        if attempt < ATTEMPTS:
            time.sleep(0.4)

    return best

# ── Event: 110m Hurdles ───────────────────────────────────────────────────────

def _hurdles(scr: curses.window, H: int, W: int, ev: dict) -> float:
    mash = Mash(decay=20, gain=19)
    scr.nodelay(True)

    TY    = H // 2
    LEFT  = 2
    RIGHT = W - 6
    TL    = RIGHT - LEFT

    N_HURDLES   = 8
    hurdle_xs   = [LEFT + int((i + 1) * TL / (N_HURDLES + 1)) for i in range(N_HURDLES)]
    cleared     = [False] * N_HURDLES
    hit         = [False] * N_HURDLES

    ply_x  = float(LEFT)
    jumped = False
    jump_t = 0.0
    fault  = False
    result : float | None = None
    tick   = 0

    # Countdown
    for cd in (3, 2, 1, 0):
        scr.erase()
        _hud(scr, H, W, ev, 'A/D sprint   SPACE jump each hurdle')
        track = '─' * TL + '╢FINISH'
        _p(scr, TY - 1, LEFT, track)
        _p(scr, TY + 1, LEFT, track)
        for hx in hurdle_xs:
            _p(scr, TY - 1, hx, '┫┃', curses.color_pair(3))
        _p(scr, TY, LEFT, _ST[0], curses.color_pair(5) | curses.A_BOLD)
        label = str(cd) if cd else 'GO!'
        bx = _cx(W, '│  GO!  │')
        _p(scr, TY - 4, bx, '┌───────┐')
        _p(scr, TY - 3, bx, f'│ {label:^5} │', curses.color_pair(2 if not cd else 3) | curses.A_BOLD)
        _p(scr, TY - 2, bx, '└───────┘')
        scr.refresh()
        time.sleep(1.0 if cd else 0.25)

    start = time.time()
    last  = start

    while True:
        now = time.time()
        dt  = now - last
        last = now
        k   = scr.getch()
        mash.key(k)
        if k == 27:
            return -1.0

        mash.tick(dt)

        if jumped:
            jump_t += dt
            # Still advance at 60% speed while airborne — jumping shouldn't kill all momentum
            ply_x = min(float(RIGHT), ply_x + mash.frac * 24.0 * dt)
            if jump_t >= 0.35:
                jumped = False
                jump_t = 0.0
        else:
            ply_x = min(float(RIGHT), ply_x + mash.frac * 40.0 * dt)

        # Check hurdles
        for i, hx in enumerate(hurdle_xs):
            if not cleared[i] and not hit[i]:
                dist = ply_x - hx
                if -2 <= dist <= 3:
                    if k == ord(' ') and not jumped:
                        cleared[i] = True
                        jumped     = True
                        jump_t     = 0.0
                    elif dist > 2 and not jumped:
                        # Clipped hurdle
                        hit[i]     = True
                        mash.speed = max(0, mash.speed - 35)

        elapsed = now - start
        if ply_x >= RIGHT and result is None:
            result = elapsed

        scr.erase()
        _hud(scr, H, W, ev, f'TIME  {elapsed:.2f}s')

        _p(scr, TY - 1, LEFT, '─' * TL + '╢FINISH')
        _p(scr, TY + 1, LEFT, '─' * TL + '╢')

        for i, hx in enumerate(hurdle_xs):
            if hit[i]:
                _p(scr, TY - 1, hx, '╳ ', curses.color_pair(4))
            elif not cleared[i]:
                _p(scr, TY - 1, hx, '┫┃', curses.color_pair(3))

        af  = (tick // 4) % 2
        rf  = (_JP if jumped else (_R0, _R1)[af])
        row = TY - 2 if jumped else TY
        _p(scr, row,     int(ply_x), rf[0], curses.color_pair(5) | curses.A_BOLD)
        _p(scr, row + 1, int(ply_x), rf[1], curses.color_pair(5))

        # Next hurdle indicator
        nxt = next((hx for i, hx in enumerate(hurdle_xs) if not cleared[i] and not hit[i]), None)
        if nxt:
            gap = nxt - ply_x
            _p(scr, H - 3, 2, f'NEXT HURDLE  {int(gap):3d}m  → SPACE', curses.color_pair(3))

        bstr, bc = mash.bar_colored(26)
        _p(scr, H - 4, 2, f'SPEED [{bstr}] {int(mash.speed):3d}%', bc)
        _p(scr, H - 2, 2, 'A/D: sprint   SPACE: jump hurdle', curses.color_pair(1))

        if result is not None:
            scr.refresh()
            time.sleep(0.6)
            return result

        tick += 1
        scr.refresh()
        _sleep(SPF - (time.time() - now))

# ── Event: Javelin Throw ──────────────────────────────────────────────────────

def _javelin(scr: curses.window, H: int, W: int, ev: dict) -> float:
    best = 0.0
    ATTEMPTS = 3

    for attempt in range(1, ATTEMPTS + 1):
        mash  = Mash(decay=15, gain=22)
        scr.nodelay(True)
        TY    = H // 2
        LEFT  = 2
        FOUL  = LEFT + (W - LEFT) // 3       # foul line — must release before
        ply_x       = float(LEFT)
        phase       = 'run'   # → 'thrown' → 'fault'
        thrown_dist = 0.0
        tick        = 0
        last        = time.time()

        while True:
            now = time.time()
            dt  = now - last
            last = now
            k   = scr.getch()
            mash.key(k)
            if k == 27:
                return -1.0

            scr.erase()
            _hud(scr, H, W, ev, f'Attempt {attempt}/{ATTEMPTS}  |  BEST {best:.2f}m')
            _p(scr, H - 2, 2, 'A/D: sprint for power    SPACE: throw', curses.color_pair(1))

            # Foul line
            _p(scr, TY - 2, FOUL, '┃ FOUL')
            _p(scr, TY - 1, FOUL, '┃ LINE')
            _p(scr, TY,     FOUL, '┃')
            _p(scr, TY + 1, FOUL, '┃')
            _p(scr, TY + 2, LEFT, '─' * (W - LEFT - 4))

            if phase == 'run':
                mash.tick(dt)
                ply_x = min(float(FOUL - 2), ply_x + mash.frac * 28.0 * dt)

                if ply_x >= FOUL - 2:
                    # Ran past foul line without throwing — fault
                    phase = 'fault'
                elif k == ord(' '):
                    # Angle is based on how far into the run-up you throw:
                    # start of runway = 15°, optimal zone (80% of runway) = 45°, past optimal = 70°
                    run_frac    = (ply_x - LEFT) / max(1, FOUL - 2 - LEFT)
                    # 0.0→15°, 0.8→45°, 1.0→70° (parabola peaks at 80% of runway)
                    if run_frac <= 0.8:
                        throw_angle = 15.0 + run_frac / 0.8 * 30.0   # 15° → 45°
                    else:
                        throw_angle = 45.0 + (run_frac - 0.8) / 0.2 * 25.0  # 45° → 70°
                    rad         = math.radians(throw_angle)
                    thrown_dist = round(mash.frac * 95.0 * math.sin(2 * rad), 2)
                    phase       = 'thrown'

                af = (tick // 3) % 2
                rf = (_R0, _R1)[af]
                px = int(ply_x)
                _p(scr, TY,     px, rf[0], curses.color_pair(5) | curses.A_BOLD)
                _p(scr, TY + 1, px, '━▷' + rf[1], curses.color_pair(5))

                bstr, bc = mash.bar_colored(26)
                _p(scr, H - 4, 2, f'POWER [{bstr}] {int(mash.speed):3d}%', bc)
                steps_left  = int(FOUL - 2 - ply_x)
                run_pct     = int((ply_x - LEFT) / max(1, FOUL - 2 - LEFT) * 100)
                angle_now   = 15.0 + min(run_pct / 80.0, 1.0) * 30.0
                zone_c      = curses.color_pair(2) | curses.A_BOLD if 70 <= run_pct <= 85 else curses.color_pair(3)
                _p(scr, H - 3, 2, f'ANGLE ~{int(angle_now):2d}°   THROW ZONE IN {steps_left:2d}  (aim 80%)', zone_c)

            elif phase == 'thrown':
                px = int(ply_x)
                _p(scr, TY,     px, _TH[0], curses.color_pair(5) | curses.A_BOLD)
                _p(scr, TY + 1, px, _TH[1], curses.color_pair(5))

                # Visual arc proportional to distance
                land_x = min(W - 4, px + max(4, int(thrown_dist / 95.0 * (W - px - 6))))
                steps  = land_x - px
                for s in range(steps):
                    t_frac = s / max(1, steps)
                    ax     = px + s
                    ay     = TY - int(5 * 4 * t_frac * (1 - t_frac) * power)
                    _p(scr, ay, ax, '─' if t_frac < 0.5 else '·', curses.color_pair(3))
                _p(scr, TY, land_x, '●', curses.color_pair(3) | curses.A_BOLD)

                dist_label = f'{thrown_dist:.2f}m'
                _p(scr, H - 3, 2, f'DISTANCE: {dist_label}', curses.color_pair(2) | curses.A_BOLD)
                scr.refresh()
                time.sleep(1.8)
                if thrown_dist > best:
                    best = thrown_dist
                break

            elif phase == 'fault':
                _p(scr, TY, int(ply_x), _KO[0], curses.color_pair(4) | curses.A_BOLD)
                _p(scr, TY + 1, int(ply_x), _KO[1], curses.color_pair(4))
                bx = _cx(W, '│  FOUL!  │')
                _p(scr, H // 2 - 2, bx, '┌─────────┐', curses.color_pair(4))
                _p(scr, H // 2 - 1, bx, '│  FOUL!  │', curses.color_pair(4) | curses.A_BOLD)
                _p(scr, H // 2,     bx, '└─────────┘', curses.color_pair(4))
                scr.refresh()
                time.sleep(1.5)
                break

            tick += 1
            scr.refresh()
            _sleep(SPF - (time.time() - now))

        if attempt < ATTEMPTS:
            time.sleep(0.3)

    return best

# ── Event: Hammer Throw ───────────────────────────────────────────────────────

def _hammer(scr: curses.window, H: int, W: int, ev: dict) -> float:
    best = 0.0
    ATTEMPTS = 3

    for attempt in range(1, ATTEMPTS + 1):
        mash  = Mash(decay=8, gain=14, cap=100.0)
        scr.nodelay(True)
        angle  = 0.0     # degrees, 0=right, 90=up, 45=optimal
        spins  = 0
        phase  = 'spin'  # → 'released' → 'done'
        dist   = 0.0
        tick   = 0
        last   = time.time()
        CX     = W // 2
        CY     = H // 2
        RADIUS = 4

        while True:
            now = time.time()
            dt  = now - last
            last = now
            k   = scr.getch()
            if k == 27:
                return -1.0

            scr.erase()
            _hud(scr, H, W, ev, f'Attempt {attempt}/{ATTEMPTS}  |  BEST {best:.2f}m')
            _p(scr, H - 2, 2, 'A/D: alternate to spin    SPACE: release at 45°', curses.color_pair(1))

            if phase == 'spin':
                was_mashed = mash.key(k)
                if was_mashed:
                    angle = (angle + 15) % 360
                    if angle < 15:
                        spins += 1
                mash.tick(dt)

                if k == ord(' '):
                    # Release at current angle
                    rad  = math.radians(angle)
                    dist = mash.frac * 82.0 * abs(math.sin(2 * rad))
                    dist = round(max(1.0, dist), 2)
                    phase = 'released'

                # Draw circle of rotation
                for a_deg in range(0, 360, 10):
                    rad_a = math.radians(a_deg)
                    cx    = CX + int(RADIUS * 2 * math.cos(rad_a))
                    cy    = CY + int(RADIUS * math.sin(rad_a))
                    # Green zone around 45 degrees
                    if 35 <= a_deg <= 55 or 215 <= a_deg <= 235:
                        _p(scr, cy, cx, '·', curses.color_pair(2))
                    else:
                        _p(scr, cy, cx, '·', curses.color_pair(1))

                # Hammer ball position
                h_rad = math.radians(angle)
                hx    = CX + int(RADIUS * 2 * math.cos(h_rad))
                hy    = CY + int(RADIUS * math.sin(h_rad))
                _p(scr, CY, CX, '◙', curses.color_pair(5) | curses.A_BOLD)
                _p(scr, hy, hx, '●', curses.color_pair(3) | curses.A_BOLD)

                # Info
                bstr, bc = mash.bar_colored(24)
                _p(scr, H - 5, 2, f'SPIN  [{bstr}]  {int(mash.speed):3d}%', bc)
                _p(scr, H - 4, 2, f'ANGLE {int(angle):3d}°   SPINS {spins}', curses.color_pair(3))
                # Angle quality hint
                in_zone = 38 <= angle <= 52 or 218 <= angle <= 232
                ang_dist = min(abs(angle - 45), abs(angle - 225))
                if in_zone:
                    hint, hc = '★ RELEASE NOW! ★', curses.color_pair(2) | curses.A_BOLD
                elif ang_dist < 30:
                    hint, hc = f'◀ {ang_dist}° from optimal ▶', curses.color_pair(3)
                else:
                    hint, hc = 'keep spinning — green zone = 45°', curses.color_pair(1)
                _p(scr, H - 3, 2, hint, hc)

                if in_zone and (tick // 6) % 2:
                    _p(scr, CY - RADIUS - 2, _cx(W, '▼ SPACE ▼'), '▼ SPACE ▼',
                       curses.color_pair(2) | curses.A_BOLD)

            elif phase == 'released':
                # Show throw arc
                rad     = math.radians(45)   # always draw at ideal 45 visually
                land_x  = CX + int(dist / 82.0 * (W // 2 - 4))
                land_x  = min(W - 4, land_x)
                steps   = land_x - CX
                for s in range(max(0, steps)):
                    t_frac = s / max(1, steps)
                    ax     = CX + s
                    ay     = CY - int(5 * 4 * t_frac * (1 - t_frac))
                    _p(scr, ay, ax, '─' if t_frac < 0.5 else '·', curses.color_pair(3))
                _p(scr, CY, land_x, '●', curses.color_pair(3) | curses.A_BOLD)
                _p(scr, CY, CX, '◙', curses.color_pair(5) | curses.A_BOLD)
                _p(scr, H - 3, 2, f'DISTANCE: {dist:.2f}m', curses.color_pair(2) | curses.A_BOLD)
                scr.refresh()
                time.sleep(1.8)
                if dist > best:
                    best = dist
                break

            tick += 1
            scr.refresh()
            _sleep(SPF - (time.time() - now))

        if attempt < ATTEMPTS:
            time.sleep(0.3)

    return best

# ── Screen wrappers ───────────────────────────────────────────────────────────

def _title(scr: curses.window, H: int, W: int) -> bool:
    scr.nodelay(False)
    scr.erase()
    cy = H // 2 - 7

    title_art = [
        ' ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗',
        '██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝',
        '██║     ██║     ███████║██║   ██║██║  ██║█████╗  ',
        '╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗',
        ' ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝',
        '',
        '  ██████╗      ███████╗██╗███████╗██╗     ██████╗ ',
        ' ██╔═══╝      ██╔════╝██║██╔════╝██║     ██╔══██╗',
        ' ██║           █████╗  ██║█████╗  ██║     ██║  ██║',
        ' ██║           ██╔══╝  ██║██╔══╝  ██║     ██║  ██║',
        ' ╚██████╗      ██║     ██║███████╗███████╗██████╔╝',
        '  ╚═════╝      ╚═╝     ╚═╝╚══════╝╚══════╝╚═════╝ ',
    ]

    for i, line in enumerate(title_art):
        attr = curses.color_pair(3 if i < 5 else 5) | curses.A_BOLD
        _p(scr, cy + i, _cx(W, line), line, attr)

    ey = cy + len(title_art) + 1
    for i, ev in enumerate(EVENTS):
        label = f'  {i+1}. {ev["name"]:<16}  WR: {ev["wr"]}{ev["unit"]}'
        _p(scr, ey + i, _cx(W, label), label, curses.color_pair(1))

    _p(scr, ey + len(EVENTS) + 2,
       _cx(W, 'CONTROLS: A / D alternate to build speed   SPACE for action   ESC quit'),
       'CONTROLS: A / D alternate to build speed   SPACE for action   ESC quit',
       curses.color_pair(1))

    prompt = '◆ PRESS SPACE TO START ◆'
    blink  = True
    last   = time.time()
    while True:
        now = time.time()
        if now - last > 0.5:
            blink = not blink
            last  = now
            _p(scr, ey + len(EVENTS) + 4, _cx(W, prompt), prompt,
               (curses.color_pair(3) | curses.A_BOLD) if blink else curses.color_pair(1))
            scr.refresh()
        k = scr.getch()
        if k == ord(' '):
            scr.nodelay(True)
            return True
        if k == 27:
            scr.nodelay(True)
            return False
        time.sleep(0.05)

def _event_intro(scr: curses.window, H: int, W: int, ev: dict, num: int) -> bool:
    """Returns False if ESC pressed (quit)."""
    scr.nodelay(False)
    scr.erase()
    cy = H // 2 - 5
    _box(scr, cy, _cx(W, '─' * 42), 11, 42, curses.color_pair(5))
    _p(scr, cy + 1, _cx(W, f'EVENT {num} OF {len(EVENTS)}'), f'EVENT {num} OF {len(EVENTS)}',
       curses.color_pair(1))
    _p(scr, cy + 3, _cx(W, ev['name']), ev['name'],
       curses.color_pair(3) | curses.A_BOLD)
    _p(scr, cy + 5, _cx(W, f'WORLD RECORD  {ev["wr"]}{ev["unit"]}'),
       f'WORLD RECORD  {ev["wr"]}{ev["unit"]}', curses.color_pair(2))
    qual_s = f'QUALIFY: {"UNDER" if not ev["hi"] else "OVER"}  {ev["qual"]}{ev["unit"]}'
    _p(scr, cy + 6, _cx(W, qual_s), qual_s, curses.color_pair(1))
    _p(scr, cy + 9, _cx(W, 'SPACE to begin   ESC to quit'), 'SPACE to begin   ESC to quit',
       curses.color_pair(3) | curses.A_BOLD)
    scr.refresh()
    return _wait_space(scr)

def _event_result(
    scr: curses.window, H: int, W: int, ev: dict, result: float
) -> bool:
    """Show result screen. Returns False if ESC (quit)."""
    scr.nodelay(False)
    qualified = (result >= ev['qual']) if ev['hi'] else (result <= ev['qual'])
    wr_beaten = (result > ev['wr']) if ev['hi'] else (result < ev['wr'])
    scr.erase()
    cy = H // 2 - 5
    bw = 44
    bx = _cx(W, '─' * bw)
    _box(scr, cy, bx, 11, bw, curses.color_pair(5))
    _p(scr, cy + 1, _cx(W, ev['name']), ev['name'], curses.color_pair(3) | curses.A_BOLD)
    if wr_beaten:
        _p(scr, cy + 2, _cx(W, '★ WORLD RECORD! ★'), '★ WORLD RECORD! ★',
           curses.color_pair(3) | curses.A_BOLD | curses.A_BLINK)
    _p(scr, cy + 3, _cx(W, f'YOUR RESULT  {result:.2f}{ev["unit"]}'),
       f'YOUR RESULT  {result:.2f}{ev["unit"]}', curses.color_pair(3) | curses.A_BOLD)
    _p(scr, cy + 4, _cx(W, f'WORLD RECORD {ev["wr"]}{ev["unit"]}'),
       f'WORLD RECORD {ev["wr"]}{ev["unit"]}', curses.color_pair(1))
    q_label = '  ★ QUALIFIED ★  ' if qualified else '  ✕ DNQ ✕  '
    q_attr  = curses.color_pair(2) | curses.A_BOLD if qualified else curses.color_pair(4) | curses.A_BOLD
    _p(scr, cy + 6, _cx(W, q_label), q_label, q_attr)
    _p(scr, cy + 9, _cx(W, 'SPACE to continue   ESC to quit'), 'SPACE to continue   ESC to quit',
       curses.color_pair(1))
    scr.refresh()
    return _wait_space(scr)

def _ceremony(scr: curses.window, H: int, W: int, results: list[dict]) -> int:
    """Show final results, return total score."""
    scr.nodelay(False)
    total = 0
    for r in results:
        ev   = r['event']
        val  = r['result']
        if ev['hi']:
            pts = int(min(1000, val / ev['wr'] * 1000)) if val > 0 else 0
        else:
            pts = int(min(1000, ev['wr'] / val * 1000)) if val > 0 else 0
        r['pts'] = pts
        total   += pts

    scr.erase()
    cy = max(1, H // 2 - 1 - len(results))
    _p(scr, cy, _cx(W, '══ FINAL RESULTS ══'), '══ FINAL RESULTS ══',
       curses.color_pair(3) | curses.A_BOLD)
    cy += 2
    header = f'  {"EVENT":<18} {"RESULT":>10}  {"PTS":>6}'
    _p(scr, cy, _cx(W, header), header, curses.color_pair(1))
    cy += 1
    _p(scr, cy, _cx(W, '─' * len(header)), '─' * len(header), curses.color_pair(1))
    cy += 1
    for r in results:
        ev   = r['event']
        val  = r['result']
        pts  = r['pts']
        line = f'  {ev["name"]:<18} {val:>8.2f}{ev["unit"]}  {pts:>6}'
        c    = curses.color_pair(2) if pts > 800 else curses.color_pair(3) if pts > 500 else curses.color_pair(4)
        _p(scr, cy, _cx(W, line), line, c)
        cy += 1
    cy += 1
    _p(scr, cy, _cx(W, '─' * len(header)), '─' * len(header), curses.color_pair(1))
    cy += 1
    total_line = f'  {"TOTAL":<18} {"":>10}  {total:>6}'
    _p(scr, cy, _cx(W, total_line), total_line, curses.color_pair(3) | curses.A_BOLD)
    cy += 2

    if total >= 4000:
        medal, mc = '★ GOLD MEDAL ★', curses.color_pair(3) | curses.A_BOLD
    elif total >= 2500:
        medal, mc = '● SILVER MEDAL ●', curses.color_pair(5) | curses.A_BOLD
    elif total >= 1000:
        medal, mc = '▲ BRONZE MEDAL ▲', curses.color_pair(4) | curses.A_BOLD
    else:
        medal, mc = 'NO MEDAL', curses.color_pair(1)
    _p(scr, cy, _cx(W, medal), medal, mc)
    cy += 2
    _p(scr, cy, _cx(W, 'SPACE to submit score   ESC to skip'), 'SPACE to submit score   ESC to skip',
       curses.color_pair(1))
    scr.refresh()
    # ESC skips submission; SPACE submits. Either way return total.
    _wait_space(scr)
    return total

# ── Main ──────────────────────────────────────────────────────────────────────

EVENT_FNS = {
    'dash':     _dash,
    'longjump': _longjump,
    'hurdles':  _hurdles,
    'javelin':  _javelin,
    'hammer':   _hammer,
}

def main(scr: curses.window) -> None:
    setup_colors()
    curses.curs_set(0)
    H, W = scr.getmaxyx()
    scr.nodelay(True)

    if not _title(scr, H, W):
        return

    results: list[dict] = []

    for num, ev in enumerate(EVENTS, 1):
        if not _event_intro(scr, H, W, ev, num):
            return
        fn     = EVENT_FNS[ev['id']]
        result = fn(scr, H, W, ev)
        if result < 0:
            return
        if not _event_result(scr, H, W, ev, result):
            # ESC on result screen — still record and continue
            results.append(dict(event=ev, result=result, qualified=False))
            return
        qualified = (result >= ev['qual']) if ev['hi'] else (result <= ev['qual'])
        results.append(dict(event=ev, result=result, qualified=qualified))

    total = _ceremony(scr, H, W, results)
    plabel = player_label()
    result_box: list[object] = []
    submit_async('claudefield', total, f'{total}pts', result_box)

    scr.nodelay(False)
    scr.erase()
    _p(scr, H // 2 - 1, _cx(W, f'Score {total} submitted for {plabel}'),
       f'Score {total} submitted for {plabel}', curses.color_pair(2) | curses.A_BOLD)
    _p(scr, H // 2 + 1, _cx(W, 'SPACE to exit'), 'SPACE to exit', curses.color_pair(1))
    scr.refresh()
    _wait_space(scr)


if __name__ == '__main__':
    run_game(main, 'Claude & Field')
