#!/usr/bin/env python3
"""Claudturismo - Top-Down Racing - ESC to pause, Q to quit."""
from __future__ import annotations

import curses
import math
import random

from claudcade_engine import (
    ENEMY,
    GOLD,
    GOOD,
    NEUTRAL,
    PLAYER,
    SELECT,
    SPECIAL,
    WATER,
    Engine,
    Renderer,
    Scene,
    at_safe,
    clamp,
)
from claudcade_engine import draw_how_to_play as _engine_how_to_play
from claudcade_scores import SubmitResult, player_label, submit_async

# ── Tunables ──────────────────────────────────────────────────────────────────
FPS              = 30
LAPS_TO_WIN      = 3
TRACK_LENGTH     = 900.0       # world-units per lap
ROAD_HALF_WIDTH  = 14          # half-width of road in screen columns
MAX_SPEED        = 22.0        # world-units per second
ACCEL            = 12.0
BRAKE            = 28.0
COAST            = 6.0         # passive deceleration when no throttle
OFFROAD_DRAG     = 18.0        # extra decel off-road
COLLIDE_PENALTY  = 0.55        # speed multiplier on collision
STEER_SPEED      = 18.0        # screen cols per second at max steer
RIVAL_COUNT      = 3
OBSTACLE_COUNT   = 6

TITLE_ART = [
    r"  ██████╗██╗      █████╗ ██╗   ██╗██████╗ ████████╗██╗   ██╗██████╗ ███╗   ███╗ ██████╗ ",
    r" ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗╚══██╔══╝██║   ██║██╔══██╗████╗ ████║██╔═══██╗",
    r" ██║     ██║     ███████║██║   ██║██║  ██║   ██║   ██║   ██║██████╔╝██╔████╔██║██║   ██║",
    r" ██║     ██║     ██╔══██║██║   ██║██║  ██║   ██║   ██║   ██║██╔══██╗██║╚██╔╝██║██║   ██║",
    r" ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝   ██║   ╚██████╔╝██║  ██║██║ ╚═╝ ██║╚██████╔╝",
    r"  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ",
]

TITLE_ART_SHORT = [
    r"  ██████╗██╗      █████╗ ██╗   ██╗██████╗ ████████╗██╗   ██╗██████╗ ",
    r" ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗╚══██╔══╝██║   ██║██╔══██╗",
    r" ██║     ██║     ███████║██║   ██║██║  ██║   ██║   ██║   ██║██████╔╝",
    r" ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝   ██║    ╚████╔╝ ██║  ██║",
    r"  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝    ╚═╝     ╚═══╝  ╚═╝  ╚═╝",
]

CAR_SPRITE = [
    " ╱─╲ ",
    "│◉=◉│",
    "│ + │",
    "│◉=◉│",
    " ╲─╱ ",
]

RIVAL_SPRITE = [
    " ┌─┐ ",
    "│o-o│",
    "│ x │",
    "│o-o│",
    " └─┘ ",
]

CAR_W = 5
CAR_H = 5

CONTROLS = [
    'W / UP          Accelerate',
    'S / DOWN        Brake / Reverse',
    'A / D / LEFT/RT Steer left / right',
    'R               Reset / Restart race',
    'ESC             Pause',
    'Q               Quit to terminal',
]


# ── Track shape ───────────────────────────────────────────────────────────────

def track_curve(distance: float) -> float:
    """Return horizontal centerline offset (in screen cols) for the given
    distance into the lap. Produces a winding track with both gentle and
    sharper bends. Periodic with TRACK_LENGTH so laps line up."""
    t = distance / TRACK_LENGTH
    a = math.sin(t * math.tau * 2) * 8.0
    b = math.sin(t * math.tau * 3 + 1.3) * 4.5
    c = math.sin(t * math.tau * 5 + 0.7) * 2.0
    return a + b + c


def fmt_time(seconds: float) -> str:
    """Format seconds into MM:SS.cc."""
    if seconds <= 0 or seconds > 5999.0:
        return ' --:--.--'
    m = int(seconds // 60)
    s = seconds - m * 60
    return f'{m:02d}:{s:05.2f}'


# ── Entities ──────────────────────────────────────────────────────────────────

class Rival:
    """A computer-controlled racer on the same track."""

    def __init__(self, distance: float, lateral: float, speed: float) -> None:
        self.distance = distance          # how far into the lap (world units)
        self.lateral  = lateral           # offset from track center (-ROAD..+ROAD)
        self.base_speed = speed           # personality (e.g. ~0.65 * MAX)
        self.speed   = speed              # current speed after rubberband
        # Slight steering personality: drifts toward this lateral target.
        self._target  = lateral
        self._target_age = 0.0

    def update(self, dt: float, player_distance: float) -> None:
        # Rubberband: nudge speed toward base, biased by gap to player. Trailing
        # rivals push +25%; leading rivals throttle back -20%. Capped so the
        # race stays fair — no warp-speed catch-up.
        gap = self.distance - player_distance
        if gap < 0:
            rb = clamp(1.0 + (-gap) * 0.004, 1.0, 1.25)
        else:
            rb = clamp(1.0 - gap * 0.003, 0.80, 1.0)
        target = self.base_speed * rb
        self.speed += clamp(target - self.speed, -8.0 * dt, 8.0 * dt)

        self.distance += self.speed * dt
        # Periodically pick a new lateral target so rivals weave a little.
        self._target_age += dt
        if self._target_age > 2.5:
            self._target_age = 0.0
            self._target = random.uniform(-ROAD_HALF_WIDTH + 3, ROAD_HALF_WIDTH - 3)
        self.lateral += clamp(self._target - self.lateral, -3.0, 3.0) * dt
        # Far-behind rivals teleport back into view so the road doesn't go
        # quiet. Player can still overtake — they don't get warped forward.
        if gap < -120:
            self.distance = player_distance + random.uniform(50.0, 120.0)
            self.lateral  = random.uniform(-ROAD_HALF_WIDTH + 3, ROAD_HALF_WIDTH - 3)


class Obstacle:
    """A static obstacle (cone / oil slick) at a fixed track position."""

    __slots__ = ('distance', 'lateral', 'kind', 'hit_lap')

    def __init__(self, distance: float, lateral: float, kind: str) -> None:
        self.distance = distance
        self.lateral  = lateral
        self.kind     = kind
        # Track which lap last collided — prevents repeated collisions on
        # subsequent frames inside the same crossing.
        self.hit_lap: int = -1


class Race:
    """All race state. The player's distance is the authoritative race clock —
    when it crosses TRACK_LENGTH * LAPS_TO_WIN the race is over."""

    def __init__(self) -> None:
        self.distance     = 0.0      # total distance traveled along the track
        self.lap_distance = 0.0      # distance into the current lap
        self.lateral      = 0.0      # player offset from road center (cols)
        self.speed        = 0.0      # current forward speed
        self.lap          = 1
        self.lap_time     = 0.0      # time spent on current lap
        self.best_lap     = 0.0      # 0 = no clean lap yet
        self.total_time   = 0.0      # total race time
        self.lap_splits: list[float] = []
        self.finished     = False
        self.collisions   = 0
        self.bump_timer   = 0.0      # screen-shake timer
        self.flash_timer  = 0.0
        self.last_signal  = ''       # toast message like "LAP 2!" or "BEST!"
        self.signal_time  = 0.0

        # Procedural decoration: roadside cones (decorative dashes / markers)
        self.rivals: list[Rival] = []
        self.obstacles: list[Obstacle] = []
        self._seed_rivals()
        self._seed_obstacles()

    # ── Setup ──────────────────────────────────────────────────────────────

    def _seed_rivals(self) -> None:
        # Push the first rival further down the track so the opening straight
        # is clear and the player can settle into the steering before
        # competing for line.
        for i in range(RIVAL_COUNT):
            d = 90.0 + i * 60.0
            lat = random.uniform(-ROAD_HALF_WIDTH + 3, ROAD_HALF_WIDTH - 3)
            spd = random.uniform(MAX_SPEED * 0.55, MAX_SPEED * 0.75)
            self.rivals.append(Rival(d, lat, spd))

    def _seed_obstacles(self) -> None:
        # No cones / oil slicks in the first ~120m of the track for the same
        # reason — give the player a clean opening to learn the curve.
        for _ in range(OBSTACLE_COUNT):
            d = random.uniform(120.0, TRACK_LENGTH - 30.0)
            lat = random.uniform(-ROAD_HALF_WIDTH + 2, ROAD_HALF_WIDTH - 2)
            kind = random.choice(['cone', 'cone', 'cone', 'oil'])
            self.obstacles.append(Obstacle(d, lat, kind))

    # ── Per-frame update ───────────────────────────────────────────────────

    def update(self, inp_up: bool, inp_down: bool,
               inp_left: bool, inp_right: bool, dt: float) -> str | None:
        """Return a flavour string (e.g. 'finish', 'lap', 'best') when an event
        fires, or None otherwise."""
        if self.finished:
            return None

        signal: str | None = None

        # Throttle / brake.
        if inp_up:
            self.speed += ACCEL * dt
        elif inp_down:
            self.speed -= BRAKE * dt
        else:
            # Coast — decay toward 0.
            sign = 1.0 if self.speed > 0 else (-1.0 if self.speed < 0 else 0.0)
            self.speed -= sign * COAST * dt
            if abs(self.speed) < 0.1:
                self.speed = 0.0
        # Off-road extra drag.
        if abs(self.lateral) > ROAD_HALF_WIDTH - 1:
            sign = 1.0 if self.speed > 0 else (-1.0 if self.speed < 0 else 0.0)
            self.speed -= sign * OFFROAD_DRAG * dt
        self.speed = clamp(self.speed, -MAX_SPEED * 0.4, MAX_SPEED)

        # Steering. Steering authority scales mildly with speed so a stopped
        # car can still nudge sideways.
        steer = 0.0
        if inp_left:  steer -= 1.0
        if inp_right: steer += 1.0
        # The track curves underneath the player — we apply the inverse to
        # lateral so going straight on a curving track pushes you off.
        curve_now  = track_curve(self.lap_distance)
        # A small fraction of the local curve also nudges the car (centrifugal
        # feel — the faster you go through a corner, the more it pulls).
        centrifugal = (track_curve(self.lap_distance + 6) - curve_now) * 0.25 \
            * (self.speed / MAX_SPEED)
        self.lateral += (steer * STEER_SPEED * dt) + centrifugal
        # Wide off-road safety — don't let player vanish entirely.
        self.lateral = clamp(self.lateral, -ROAD_HALF_WIDTH - 6, ROAD_HALF_WIDTH + 6)

        # Forward motion.
        prev_lap_distance = self.lap_distance
        forward = self.speed * dt
        self.distance     += forward
        self.lap_distance += forward
        self.lap_time     += dt
        self.total_time   += dt

        # Lap rollover.
        if self.lap_distance >= TRACK_LENGTH:
            self.lap_distance -= TRACK_LENGTH
            lap_finished = self.lap_time
            self.lap_splits.append(lap_finished)
            is_best = self.best_lap == 0.0 or lap_finished < self.best_lap
            if is_best:
                self.best_lap = lap_finished
                signal = 'best'
            else:
                signal = 'lap'
            self.lap += 1
            self.lap_time = 0.0
            if self.lap > LAPS_TO_WIN:
                self.finished = True
                self.lap = LAPS_TO_WIN  # clamp display
                signal = 'finish'

        # Collisions: rivals & obstacles. Use distance window + lateral test.
        if not self.finished:
            self._collide(prev_lap_distance, dt)

        # Decay screen-shake / flash.
        if self.bump_timer > 0:
            self.bump_timer = max(0.0, self.bump_timer - dt)
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        if self.signal_time > 0:
            self.signal_time = max(0.0, self.signal_time - dt)

        # Drive rivals.
        for r in self.rivals:
            r.update(dt, self.distance)

        if signal == 'best':
            self.last_signal = 'BEST LAP!'
            self.signal_time = 2.2
        elif signal == 'lap':
            self.last_signal = f'LAP {self.lap} / {LAPS_TO_WIN}'
            self.signal_time = 2.0
        elif signal == 'finish':
            self.last_signal = 'FINISH!'
            self.signal_time = 3.0
        return signal

    # ── Collisions ─────────────────────────────────────────────────────────

    def _collide(self, prev_lap_distance: float, dt: float) -> None:
        # Don't pile on collisions inside the brief bump-flash window.
        if self.bump_timer > 0.15:
            return
        # Player is at lap_distance, lateral. Compare against rivals + obstacles.
        my_d = self.distance
        for r in self.rivals:
            if abs(r.distance - my_d) < 2.2 and abs(r.lateral - self.lateral) < 3.0:
                self._bump()
                # Push rival sideways + ahead so we don't lock into a stuck collision.
                r.lateral += 3.0 if r.lateral >= self.lateral else -3.0
                r.distance += 3.0
                return
        for ob in self.obstacles:
            # Obstacles are per-lap-position, not per-total-distance, and only
            # fire once per lap to avoid repeated-frame collisions.
            if ob.hit_lap == self.lap:
                continue
            d_lap = ob.distance
            # Detect crossing during this frame (handles fast speeds).
            crossing = False
            if prev_lap_distance <= d_lap <= self.lap_distance:
                crossing = True
            elif (self.lap_distance < prev_lap_distance
                  and (d_lap >= prev_lap_distance or d_lap <= self.lap_distance)):
                crossing = True
            if crossing and abs(ob.lateral - self.lateral) < 2.5:
                ob.hit_lap = self.lap
                if ob.kind == 'oil':
                    # Oil: lose steering for a moment, mild slow.
                    self.speed *= 0.85
                    self.lateral += random.choice((-1.0, 1.0)) * 1.5
                else:
                    self._bump()
                return

    def _bump(self) -> None:
        self.speed *= COLLIDE_PENALTY
        self.bump_timer = 0.35
        self.flash_timer = 0.18
        self.collisions += 1


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _put(scr: curses.window, H: int, W: int, row: int, col: int,
         s: str, attr: int = 0) -> None:
    at_safe(scr, H, W, row, col, s, attr)


def draw_intro(scr: curses.window, H: int, W: int, tick: int) -> None:
    P = curses.color_pair
    scr.erase()

    # Outer frame.
    _put(scr, H, W, 0,   0, '╔' + '═' * (W - 2) + '╗', P(NEUTRAL) | curses.A_BOLD)
    _put(scr, H, W, H-1, 0, '╚' + '═' * (W - 2) + '╝', P(NEUTRAL) | curses.A_BOLD)
    for r in range(1, H - 1):
        _put(scr, H, W, r, 0,     '║', P(NEUTRAL) | curses.A_BOLD)
        _put(scr, H, W, r, W - 1, '║', P(NEUTRAL) | curses.A_BOLD)

    # Title art.
    art = TITLE_ART if W >= len(TITLE_ART[0]) + 4 else TITLE_ART_SHORT
    if W < len(art[0]) + 4:
        art = ['CLAUDTURISMO']  # very narrow fallback
    sr = max(2, (H - len(art) - 12) // 2)
    palette = [GOLD, ENEMY, PLAYER, GOLD, ENEMY, PLAYER]
    for i, line in enumerate(art):
        cx = max(1, (W - len(line)) // 2)
        _put(scr, H, W, sr + i, cx, line, P(palette[i % len(palette)]) | curses.A_BOLD)

    # Sub-title.
    sub_y = sr + len(art) + 1
    sub = f'<<<   TOP-DOWN RACING  -  {LAPS_TO_WIN} LAPS  -  TIME ATTACK   >>>'
    _put(scr, H, W, sub_y, max(1, (W - len(sub)) // 2), sub, P(GOLD) | curses.A_BOLD)

    # Animated road preview.
    road_top  = sub_y + 2
    road_rows = max(3, H - road_top - 6)
    cx = W // 2
    for i in range(road_rows):
        d = i + (tick // 2)
        center_shift = int(math.sin(d * 0.18) * 6)
        left  = cx - ROAD_HALF_WIDTH + center_shift
        right = cx + ROAD_HALF_WIDTH + center_shift
        rrow = road_top + i
        # Grass.
        if 0 < left < W:
            _put(scr, H, W, rrow, max(1, left - 14), '▒' * 14, P(GOOD) | curses.A_DIM)
        if right < W - 1:
            _put(scr, H, W, rrow, right + 1,        '▒' * max(1, W - right - 3),
                 P(GOOD) | curses.A_DIM)
        # Road body.
        if left < right:
            road_w = right - left
            _put(scr, H, W, rrow, max(1, left), ' ' * max(0, road_w),
                 P(NEUTRAL) | curses.A_REVERSE)
        # Center dashes.
        if (i + tick // 1) % 2 == 0:
            _put(scr, H, W, rrow, max(1, left + (right - left) // 2),
                 '|', P(GOLD) | curses.A_BOLD)
        # Road edges.
        _put(scr, H, W, rrow, max(1, left),  '|', P(NEUTRAL) | curses.A_BOLD)
        _put(scr, H, W, rrow, min(W - 2, right), '|', P(NEUTRAL) | curses.A_BOLD)

    # Demo car.
    demo_x = cx - CAR_W // 2 + int(math.sin(tick * 0.08) * 2)
    demo_y = road_top + road_rows - CAR_H - 1
    for i, row in enumerate(CAR_SPRITE):
        _put(scr, H, W, demo_y + i, demo_x, row, P(PLAYER) | curses.A_BOLD)

    # Blinking prompt.
    if (tick // 18) % 2 == 0:
        msg = '<  PRESS SPACE TO START  >'
        _put(scr, H, W, H - 4, (W - len(msg)) // 2, msg, P(GOLD) | curses.A_BOLD)

    hint = '[ W/UP: Gas ]  [ S/DOWN: Brake ]  [ A D LEFT/RT: Steer ]  [ ESC: Pause ]'
    _put(scr, H, W, H - 2, max(1, (W - len(hint)) // 2), hint,
         P(NEUTRAL) | curses.A_DIM)

    scr.refresh()


def draw_race(scr: curses.window, race: Race, H: int, W: int, tick: int) -> None:
    P = curses.color_pair
    scr.erase()

    # Layout.
    HUD_H        = 3
    play_top     = HUD_H
    play_bottom  = H - 2
    play_rows    = play_bottom - play_top
    if play_rows < 6:
        # Terminal too small for a real play area.
        _put(scr, H, W, H // 2, max(0, (W - 18) // 2),
             ' resize terminal ', P(NEUTRAL) | curses.A_BOLD)
        scr.refresh()
        return

    # Camera shake (after a bump).
    shake_x = 0
    if race.bump_timer > 0:
        shake_x = random.choice((-1, 0, 1))

    cx = W // 2 + shake_x

    # ── HUD bar ────────────────────────────────────────────────────────────
    r = Renderer(scr, H, W)
    speed_kph = int(abs(race.speed) * 9.5)  # not literal, just feels racey
    bump_color = ENEMY if race.flash_timer > 0 else NEUTRAL
    r.text(0, 0, '╔' + '═' * (W - 2) + '╗', bump_color, bold=True)
    r.text(1, 0, '║', bump_color, bold=True)
    r.text(1, W - 1, '║', bump_color, bold=True)
    r.text(2, 0, '╠' + '═' * (W - 2) + '╣', bump_color, bold=True)

    # HUD: SPEED + LAP + cur/best.
    hud_lap = f' LAP {min(race.lap, LAPS_TO_WIN)}/{LAPS_TO_WIN} '
    r.text(1, 2, hud_lap, GOLD, bold=True)

    # SPEED bar.
    bar_x = 2 + len(hud_lap) + 2
    bar_w = min(24, max(8, (W - 48) // 2))
    r.text(1, bar_x, 'SPD', NEUTRAL, bold=True)
    r.bar(1, bar_x + 4, abs(race.speed), MAX_SPEED, bar_w,
          fill_color=GOOD if race.speed >= 0 else SPECIAL,
          empty_color=NEUTRAL,
          label=f'{speed_kph:3d}')

    # Times: right-aligned.
    cur_str = f'CUR {fmt_time(race.lap_time)}'
    bst_str = f'BST {fmt_time(race.best_lap)}'
    right_pad = W - 2
    r.text(1, right_pad - len(bst_str) - 1, bst_str, GOLD, bold=True)
    r.text(1, right_pad - len(bst_str) - len(cur_str) - 4, cur_str, PLAYER, bold=True)

    # ── Track render ───────────────────────────────────────────────────────
    # The car is fixed near the bottom of the play area. The track scrolls
    # past it. For each on-screen row we compute its world-distance ahead
    # of the car and look up the centerline curvature there.

    car_row = play_bottom - CAR_H - 1
    # How many "world distance" units one screen row represents. We compress
    # the depth so the player gets a useful look-ahead.
    depth_per_row = 0.55

    for i in range(play_rows):
        rrow = play_top + i
        # rows nearest the car are closest to "now"; rows higher up are ahead.
        depth = (play_rows - 1 - i) * depth_per_row
        lap_d_at_row = race.lap_distance + depth
        # Curve at that distance, relative to curve at the car.
        curve_here = track_curve(lap_d_at_row) - track_curve(race.lap_distance)
        center_col = cx + int(curve_here)
        left  = center_col - ROAD_HALF_WIDTH
        right = center_col + ROAD_HALF_WIDTH

        # Grass fill outside the road.
        if left > 0:
            _put(scr, H, W, rrow, 1, '▒' * (left - 1),
                 P(GOOD) | curses.A_DIM)
        if right < W - 1:
            _put(scr, H, W, rrow, right + 1, '▒' * (W - right - 2),
                 P(GOOD) | curses.A_DIM)

        # Road surface (reverse video for "tarmac").
        if right > left:
            road_w = right - left + 1
            _put(scr, H, W, rrow, max(1, left), ' ' * road_w,
                 P(NEUTRAL) | curses.A_REVERSE)

        # Edge stripes — alternating colors give speed feel.
        edge_phase = (int(race.distance * 2) + i) % 4
        edge_attr  = P(ENEMY) | curses.A_BOLD if edge_phase < 2 else \
                     P(NEUTRAL) | curses.A_BOLD
        _put(scr, H, W, rrow, max(1, left),  '|', edge_attr)
        _put(scr, H, W, rrow, min(W - 2, right), '|', edge_attr)

        # Centerline dashes — scroll with race distance.
        cl_phase = (int(race.distance * 3) + i) % 3
        if cl_phase == 0:
            _put(scr, H, W, rrow, center_col, ':', P(GOLD) | curses.A_BOLD)

    # ── Obstacles ──────────────────────────────────────────────────────────
    for ob in race.obstacles:
        # Compute the depth of this obstacle from the car's lap_distance.
        d_lap = ob.distance
        # Compare modulo TRACK_LENGTH so obstacles wrap each lap.
        depth = d_lap - race.lap_distance
        if depth < -2.0:
            depth += TRACK_LENGTH
        if depth < -1.0 or depth > play_rows * depth_per_row:
            continue
        row = int(play_bottom - 1 - depth / depth_per_row)
        if not (play_top <= row < play_bottom):
            continue
        # The road centerline shifts with depth — match it.
        curve_here = track_curve(d_lap) - track_curve(race.lap_distance)
        col = int(cx + curve_here + ob.lateral)
        if ob.kind == 'cone':
            _put(scr, H, W, row, col, 'A', P(GOLD) | curses.A_BOLD)
        else:  # oil slick
            _put(scr, H, W, row, col, '~', P(SPECIAL) | curses.A_BOLD)

    # ── Rivals ─────────────────────────────────────────────────────────────
    # Render rivals that are within sight ahead of the player.
    for rv in race.rivals:
        gap = rv.distance - race.distance
        # Behind the player by a little — draw at the bottom edge.
        if gap < -1.5:
            continue
        if gap > play_rows * depth_per_row:
            continue
        row = int(play_bottom - 1 - gap / depth_per_row) - CAR_H + 1
        # Match the curving road at that depth so the rival sits on it.
        lap_d = race.lap_distance + max(0.0, gap)
        curve_here = track_curve(lap_d) - track_curve(race.lap_distance)
        col = int(cx + curve_here + rv.lateral - CAR_W // 2)
        for i, srow in enumerate(RIVAL_SPRITE):
            if play_top <= row + i < play_bottom:
                _put(scr, H, W, row + i, col, srow, P(ENEMY) | curses.A_BOLD)

    # ── Player car ─────────────────────────────────────────────────────────
    pcol = int(cx + race.lateral - CAR_W // 2)
    pcolor = PLAYER
    if race.flash_timer > 0 and (tick // 2) % 2 == 0:
        pcolor = ENEMY
    for i, srow in enumerate(CAR_SPRITE):
        if play_top <= car_row + i < play_bottom:
            _put(scr, H, W, car_row + i, pcol, srow,
                 P(pcolor) | curses.A_BOLD)

    # Tire smoke when off-road or braking hard.
    if abs(race.lateral) > ROAD_HALF_WIDTH - 1 and abs(race.speed) > 1.0:
        smoke_row = car_row + CAR_H
        for dx in (0, CAR_W - 1):
            _put(scr, H, W, smoke_row, pcol + dx,
                 random.choice(('*', '.', 'o')),
                 P(NEUTRAL) | curses.A_DIM)

    # ── Signal toast (lap / best / finish) ─────────────────────────────────
    if race.signal_time > 0:
        toast = f'  {race.last_signal}  '
        # blink in the first half.
        bold = (tick // 4) % 2 == 0
        ty = play_top + 2
        attr_color = GOLD if 'BEST' in race.last_signal or 'FINISH' in race.last_signal else PLAYER
        r.text(ty, max(1, (W - len(toast)) // 2), toast,
               attr_color, bold=bold)

    # ── Bottom controls strip ──────────────────────────────────────────────
    r.text(H - 2, 0, '╚' + '═' * (W - 2) + '╝', NEUTRAL, bold=True)
    ctrl = '[W/UP:Gas]  [S/DN:Brake]  [A D LEFT/RT:Steer]  [R:Restart]  [ESC:Pause]'
    r.text(H - 2, max(1, (W - len(ctrl)) // 2), ctrl, NEUTRAL, dim=True)
    scr.refresh()


def draw_finish(scr: curses.window, H: int, W: int, race: Race,
                score: int, tick: int, sub_result: list | None = None) -> None:
    P = curses.color_pair
    scr.erase()

    _put(scr, H, W, 0,   0, '╔' + '═' * (W - 2) + '╗', P(GOLD) | curses.A_BOLD)
    _put(scr, H, W, H-1, 0, '╚' + '═' * (W - 2) + '╝', P(GOLD) | curses.A_BOLD)
    for r in range(1, H - 1):
        _put(scr, H, W, r, 0,     '║', P(GOLD) | curses.A_BOLD)
        _put(scr, H, W, r, W - 1, '║', P(GOLD) | curses.A_BOLD)

    # Checkered band.
    chk = ''.join('█' if (i + tick // 3) % 2 == 0 else ' '
                  for i in range(W - 4))
    _put(scr, H, W, 2, 2, chk, P(NEUTRAL) | curses.A_BOLD)
    _put(scr, H, W, H - 3, 2, chk, P(NEUTRAL) | curses.A_BOLD)

    title = 'R A C E   C O M P L E T E' if race.finished else 'R A C E   A B A N D O N E D'
    mr = H // 2 - 5
    _put(scr, H, W, mr, max(1, (W - len(title)) // 2), title,
         P(GOLD) | curses.A_BOLD)

    # Stats table.
    lines = []
    lines.append(f'TOTAL TIME      {fmt_time(race.total_time)}')
    lines.append(f'BEST LAP        {fmt_time(race.best_lap)}')
    for i, t in enumerate(race.lap_splits):
        lines.append(f'  LAP {i+1:1d} SPLIT   {fmt_time(t)}')
    lines.append('')
    lines.append(f'COLLISIONS      {race.collisions}')
    lines.append(f'SCORE           {score:07d}')

    for i, ln in enumerate(lines):
        _put(scr, H, W, mr + 2 + i, max(2, (W - len(ln)) // 2), ln,
             P(NEUTRAL) | curses.A_BOLD)

    pl = player_label()
    _put(scr, H, W, mr + 3 + len(lines), max(2, (W - len(pl) - 4) // 2),
         f'<  {pl}  >', P(PLAYER) | curses.A_BOLD)

    if sub_result and sub_result[0]:
        rank = sub_result[0].get('rank') if isinstance(sub_result[0], dict) else None
        if rank:
            rm = f'  Global rank: #{rank}  '
            _put(scr, H, W, mr + 4 + len(lines),
                 max(2, (W - len(rm)) // 2), rm, P(GOOD) | curses.A_BOLD)
    elif sub_result and sub_result[0] is None:
        _put(scr, H, W, mr + 4 + len(lines),
             max(2, (W - 24) // 2), '  Submitting score...  ',
             P(NEUTRAL) | curses.A_DIM)

    if (tick // 18) % 2 == 0:
        msg = '>  SPACE = Race again   |   ESC = Quit  <'
        _put(scr, H, W, H - 4, max(2, (W - len(msg)) // 2), msg,
             P(GOLD) | curses.A_BOLD)
    scr.refresh()


# ── Scoring ───────────────────────────────────────────────────────────────────

def race_score(race: Race) -> int:
    """Score formula: faster total time + lower collisions => higher score.
    Returns 0 for unfinished races."""
    if not race.finished or race.total_time <= 0:
        return 0
    # Baseline: 1,000,000 / total_time gives a clean integer-shaped score.
    base = 1_000_000 / race.total_time
    # Penalise collisions by 1.5% each.
    penalty = max(0.4, 1.0 - race.collisions * 0.015)
    return int(base * penalty)


# ── Scenes ────────────────────────────────────────────────────────────────────

class IntroScene(Scene):
    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')):                  return 'howto'
        if inp.just_pressed(27):                        return 'quit'
        if inp.just_pressed(ord('q'), ord('Q')):        return 'quit'

    def draw(self, r, tick):
        draw_intro(r._scr, self.engine.H, self.engine.W, tick)


class HowToPlayScene(Scene):
    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')):           return 'race'
        if inp.just_pressed(27):                 return 'quit'
        if inp.just_pressed(ord('q'), ord('Q')): return 'quit'

    def draw(self, r, tick):
        _engine_how_to_play(
            r._scr, self.engine.H, self.engine.W, tick,
            goal=[
                f'Complete {LAPS_TO_WIN} laps as fast as possible. Fastest total time wins.',
                'Avoid the rival cars and the orange cones. Stay on the road -- the',
                'grass is slow and unforgiving.',
            ],
            controls=[
                'W / UP            Accelerate',
                'S / DOWN          Brake / Reverse',
                'A / LEFT          Steer left',
                'D / RIGHT         Steer right',
                'R                 Restart current race',
                'ESC               Pause',
            ],
            tips=[
                '* Brake before the bends -- you cannot turn well at top speed',
                '* Tap-steer through tight curves rather than holding the key',
                '* Oil slicks (~) shove your car sideways -- aim around them',
                '* Bumping rivals costs speed; clean laps score more',
            ],
        )


class RaceScene(Scene):
    race: Race
    paused: bool
    finished_pending: int

    def on_enter(self):
        self.race = Race()
        self.paused = False
        self.finished_pending = 0   # finish-toast frames before scene switch
        self.submit_box: list[SubmitResult | None] = [None]
        self._submitted = False

    def update(self, inp, tick, dt):
        if inp.just_pressed(27):
            self.paused = not self.paused
            return None

        if self.paused:
            if inp.just_pressed(ord('r'), ord('R')):
                self.paused = False
                return None
            if inp.just_pressed(ord('q'), ord('Q')):
                return 'quit'
            if inp.just_pressed(ord(' ')):
                self.paused = False
                return None
            return None

        if inp.just_pressed(ord('q'), ord('Q')):
            return 'quit'

        # Restart in-race.
        if inp.just_pressed(ord('r'), ord('R')) and not self.race.finished:
            self.race = Race()
            self.finished_pending = 0
            return None

        if self.race.finished:
            # Brief pause so the FINISH toast is visible, then go to summary.
            self.finished_pending += 1
            if not self._submitted:
                score = race_score(self.race)
                submit_async('claudturismo', score,
                             f'time={self.race.total_time:.2f}s best={self.race.best_lap:.2f}s',
                             self.submit_box)
                self._submitted = True
            if self.finished_pending > 60:
                return ('finish', (self.race, race_score(self.race), self.submit_box))
            return None

        up    = inp.up
        down  = inp.down
        left  = inp.left
        right = inp.right
        self.race.update(up, down, left, right, dt)
        return None

    def draw(self, r, tick):
        draw_race(r._scr, self.race, self.engine.H, self.engine.W, tick)
        if self.paused:
            Renderer(r._scr, self.engine.H, self.engine.W).pause_overlay(
                'Claudturismo', CONTROLS,
            )


class FinishScene(Scene):
    def on_enter(self):
        if isinstance(self.payload, tuple) and len(self.payload) == 3:
            self.race, self.score, self.sub = self.payload
        else:
            self.race = Race()
            self.race.finished = True
            self.score = 0
            self.sub = [None]

    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')):                  return 'race'
        if inp.just_pressed(27):                        return 'quit'
        if inp.just_pressed(ord('q'), ord('Q')):        return 'quit'

    def draw(self, r, tick):
        draw_finish(r._scr, self.engine.H, self.engine.W,
                    self.race, self.score, tick, self.sub)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    # Independent RNG seed each run.
    random.seed()
    # Re-export keeps ruff from flagging WATER/SELECT as unused; both are
    # part of the engine palette and used in draw helpers above.
    _ = (WATER, SELECT)
    (
        Engine('Claudturismo', fps=FPS)
        .scene('intro',  IntroScene())
        .scene('howto',  HowToPlayScene())
        .scene('race',   RaceScene())
        .scene('finish', FinishScene())
        .run('intro')
    )


if __name__ == '__main__':
    main()
