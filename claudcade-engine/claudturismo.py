#!/usr/bin/env python3
"""Claude Turismo — Pseudo-3D Terminal Racing · ESC to pause"""
import curses, time, random, math, sys
from claudcade_engine import setup_colors, Renderer, run_game
INTRO, HOW_TO_PLAY, PLAY, PAUSE, FINISH = range(5)
FPS          = 30
LAPS         = 3
MAX_SPEED    = 260.0    # world units / second at full throttle
ACCEL        = 130.0    # units/s² when holding accelerate
BRAKE_RATE   = 260.0    # units/s² when braking
FRICTION     = 65.0     # natural deceleration per second
OFFROAD_SLOW = 140.0    # extra drag off-road
STEER_SPEED  = 1800.0   # lateral units/s at full steer
CENTRIFUGAL  = 0.0035   # fraction of speed pushed outward per curve unit
SEG_LEN      = 180      # world units per track segment
ROAD_HALF_W  = 1600     # half-width of road in world units
LAP_SEGS     = 160      # track segments per lap

TITLE = [
    r" ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗",
    r"██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝",
    r"██║     ██║     ███████║██║   ██║██║  ██║█████╗  ",
    r"██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  ",
    r"╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗",
    r" ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝",
    r"",
    r"  ████████╗██╗   ██╗██████╗ ██╗███████╗███╗   ███╗ ██████╗ ",
    r"  ╚══██╔══╝██║   ██║██╔══██╗██║██╔════╝████╗ ████║██╔═══██╗",
    r"     ██║   ██║   ██║██████╔╝██║███████╗██╔████╔██║██║   ██║",
    r"     ██║   ██║   ██║██╔══██╗██║╚════██║██║╚██╔╝██║██║   ██║",
    r"     ██║   ╚██████╔╝██║  ██║██║███████║██║ ╚═╝ ██║╚██████╔╝",
    r"     ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ",
]

# (curve, length)  curve: negative=left  positive=right  abs max ≈ 1.5
LAYOUT = [
    ( 0.00, 22),  # start straight
    ( 0.70, 18),  # gentle right
    ( 0.00, 12),  # straight
    (-0.90, 16),  # left hairpin
    ( 0.00, 10),  # straight
    ( 1.20, 12),  # right sweeper
    (-1.20, 12),  # left sweeper (chicane)
    ( 0.00, 18),  # back straight
    (-0.60, 14),  # gentle left
    ( 1.40, 10),  # sharp right
    ( 0.00, 16),  # finish straight
]

def _build_track():
    segs = []
    for curve, length in LAYOUT:
        segs.extend([float(curve)] * length)
    while len(segs) < LAP_SEGS:
        segs.append(0.0)
    return segs[:LAP_SEGS]

TRACK = _build_track()

# ─────────────────────────────────────────────────────────────
#  PLAYER CAR SPRITES  (viewed from above/behind)
#  3 variants: straight, left lean, right lean
# ─────────────────────────────────────────────────────────────
#  C = center, L = steering left, R = steering right
_CAR_C = [
    "  ╔════╗  ",
    " ▐██████▌ ",
    " ▐█▐══▌█▌ ",
    " ▐██████▌ ",
    "  ╚════╝  ",
]
_CAR_L = [
    " ╔════╗   ",
    "▐██████▌  ",
    "▐█▐══▌█▌  ",
    "▐██████▌  ",
    " ╚════╝   ",
]
_CAR_R = [
    "   ╔════╗ ",
    "  ▐██████▌",
    "  ▐█▐══▌█▌",
    "  ▐██████▌",
    "   ╚════╝ ",
]

# ─────────────────────────────────────────────────────────────
#  OPPONENT CAR SPRITES  — clearly distinct (wedge/angular look)
#  Different sizes by distance
# ─────────────────────────────────────────────────────────────
_OPP_XL = [
    " ┌──────┐ ",
    " │▓▓▓▓▓▓│ ",
    "═╡◈    ◈╞═",
    " │▓▓▓▓▓▓│ ",
    " └──────┘ ",
]
_OPP_LG = [
    " ┌────┐ ",
    "═╡◈  ◈╞═",
    " └────┘ ",
]
_OPP_MD = [
    "┌────┐",
    "│◈  ◈│",
    "└────┘",
]
_OPP_SM = [
    "╓──╖",
    "◈  ◈",
]
_OPP_XS = ["▪▪"]

def _opp_sprite(dist):
    if dist < 800:   return _OPP_XL, 1   # color pair 1 = RED
    if dist < 1600:  return _OPP_LG, 4   # YELLOW
    if dist < 3000:  return _OPP_MD, 4
    if dist < 6000:  return _OPP_SM, 5
    return _OPP_XS, 5

# ─────────────────────────────────────────────────────────────
#  ROADSIDE SCENERY  — parallax trees / barriers / billboards
# ─────────────────────────────────────────────────────────────
# Each entry: (z_period, x_side, sprite_lines)
# x_side: +1 = right of road, -1 = left of road
_TREE_L  = ["♣", "│"]
_TREE_R  = ["♣", "│"]
_BARRIER = ["═══"]
_SIGN    = ["▓▓▓", "▐ ▌", "▐ ▌"]

# Scenery placement: (seg_offset, side, type)  side: L/R
SCENERY_DEFS = [
    (0,  'L', 'tree'), (3,  'R', 'tree'), (6,  'L', 'tree'),
    (9,  'R', 'tree'), (12, 'L', 'tree'), (15, 'R', 'tree'),
    (18, 'L', 'tree'), (20, 'R', 'sign'), (22, 'L', 'tree'),
    (25, 'R', 'tree'), (28, 'L', 'sign'), (30, 'R', 'tree'),
    (33, 'L', 'tree'), (36, 'R', 'tree'), (40, 'L', 'tree'),
    (43, 'R', 'tree'), (46, 'L', 'tree'), (50, 'R', 'sign'),
    (53, 'L', 'tree'), (56, 'R', 'tree'), (60, 'L', 'tree'),
    (63, 'R', 'tree'), (66, 'L', 'sign'), (70, 'R', 'tree'),
    (73, 'L', 'tree'), (76, 'R', 'tree'), (80, 'L', 'tree'),
    (83, 'R', 'tree'), (86, 'L', 'tree'), (90, 'R', 'sign'),
]

def _p(scr, H, W, r, c, s, a=0):
    try:
        if 0 <= r < H-1 and 0 <= c < W:
            scr.addstr(r, c, s[:max(0, W-c)], a)
    except curses.error:
        pass

def _fmt_time(secs):
    m = int(secs) // 60
    s = secs % 60
    return f"{m}:{s:05.2f}"

def _ordinal(n):
    suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
    return f"{n}{suffixes.get(n, 'th')}"

class Racer:
    def __init__(self, z, x, speed, is_player=False):
        self.z         = float(z)
        self.x         = float(x)
        self.speed     = float(speed)
        self.lap       = 0
        self.lap_times = []
        self.lap_start = 0.0
        self.finished  = False
        self.is_player = is_player
        self.steer_dir = 0

class Race:
    def __init__(self):
        self.player    = Racer(0, 0, 0, is_player=True)
        lap_offset     = LAP_SEGS * SEG_LEN
        self.opps      = [
            Racer(-SEG_LEN * 3,                         random.uniform(-400, 400),  90),
            Racer(-SEG_LEN * 7  + lap_offset // 4,      random.uniform(-600, 600), 110),
            Racer(-SEG_LEN * 12 + lap_offset // 3,      random.uniform(-200, 200),  80),
        ]
        self.racers       = [self.player] + self.opps
        self.start_time   = time.time()
        self.race_time    = 0.0
        self.finished     = False
        self.finish_place = 0
        self.best_lap     = None
        # Countdown: 3 seconds before race starts (90 ticks at 30fps)
        self.countdown    = 90

    def position(self):
        """Player's current race position (1-based)."""
        p_dist = self.player.z + self.player.lap * LAP_SEGS * SEG_LEN
        ahead  = sum(
            1 for o in self.opps
            if not o.finished and (o.z + o.lap * LAP_SEGS * SEG_LEN) > p_dist
        )
        # finished opponents who finished before player count too
        ahead += sum(1 for o in self.opps if o.finished and not self.player.finished)
        return min(ahead + 1, 4)

    def seg_at(self, z):
        idx = int(z / SEG_LEN) % LAP_SEGS
        return TRACK[idx]

    def update(self, keys, mouse_click, dt):
        # Countdown phase — no player input yet
        if self.countdown > 0:
            self.countdown -= 1
            # AI still frozen during countdown
            return

        p = self.player
        if p.finished:
            return
        accel = curses.KEY_UP   in keys or ord('w') in keys
        decel = curses.KEY_DOWN in keys or ord('s') in keys
        left  = curses.KEY_LEFT in keys or ord('a') in keys
        right = curses.KEY_RIGHT in keys or ord('d') in keys

        if accel:
            p.speed = min(MAX_SPEED, p.speed + ACCEL * dt)
        elif decel:
            p.speed = max(0.0, p.speed - BRAKE_RATE * dt)
        else:
            p.speed = max(0.0, p.speed - FRICTION * dt)

        steer = (-1 if left else 0) + (1 if right else 0)
        p.steer_dir = steer
        p.x += steer * STEER_SPEED * dt

        curve = self.seg_at(p.z)
        p.x += curve * p.speed * CENTRIFUGAL * dt * SEG_LEN

        if abs(p.x) > ROAD_HALF_W:
            p.speed = max(0.0, p.speed - OFFROAD_SLOW * dt)
            p.x = max(-ROAD_HALF_W * 1.8, min(ROAD_HALF_W * 1.8, p.x))

        p.z += p.speed * dt

        lap_len = LAP_SEGS * SEG_LEN
        while p.z >= lap_len * (p.lap + 1):
            now = time.time() - self.start_time
            lt  = now - (p.lap_start if p.lap > 0 else 0) - sum(p.lap_times)
            p.lap_times.append(lt)
            if self.best_lap is None or lt < self.best_lap:
                self.best_lap = lt
            p.lap += 1
            if p.lap >= LAPS:
                p.finished        = True
                self.finished     = True
                self.finish_place = 1 + sum(1 for o in self.opps if o.finished)

        for opp in self.opps:
            if opp.finished: continue
            gap    = p.z - opp.z
            target = min(MAX_SPEED * 0.85, MAX_SPEED * 0.6 + gap * 0.02)
            if opp.speed < target:
                opp.speed = min(target, opp.speed + ACCEL * 0.6 * dt)
            else:
                opp.speed = max(target, opp.speed - FRICTION * dt)
            opp.z += opp.speed * dt
            opp.x *= (1 - dt * 0.8)
            opp.x += self.seg_at(opp.z) * opp.speed * CENTRIFUGAL * 0.5 * dt * SEG_LEN
            while opp.z >= LAP_SEGS * SEG_LEN * (opp.lap + 1):
                opp.lap += 1
                if opp.lap >= LAPS: opp.finished = True

        self.race_time = time.time() - self.start_time


# ═══════════════════════════════════════════════════════════════
#  ROAD RENDERER
# ═══════════════════════════════════════════════════════════════
def draw_road(scr, H, W, race, tick):
    P = curses.color_pair
    p = race.player

    HUD_H       = 3        # rows used by HUD at top
    CAR_H       = len(_CAR_C)
    CAR_ROW_GAP = 1        # gap between road bottom and car
    ROAD_TOP    = HUD_H
    ROAD_BOTTOM = H - CAR_H - CAR_ROW_GAP - 2
    ROAD_ROWS   = max(2, ROAD_BOTTOM - ROAD_TOP)

    # ── Perspective curve accumulation ──────────────────────
    curve_acc      = 0.0
    curve_per_row  = []
    for i in range(ROAD_ROWS):
        depth_factor = (ROAD_ROWS - i) / ROAD_ROWS
        look_ahead   = depth_factor * (p.speed / MAX_SPEED) * 20
        seg_idx      = int((p.z / SEG_LEN) + look_ahead) % LAP_SEGS
        curve_acc   += TRACK[seg_idx] * depth_factor * 0.8
        curve_per_row.append(curve_acc)

    player_x_offset = int(p.x / ROAD_HALF_W * (W // 4))
    max_hw          = W // 2 - 3

    # ── Sky / horizon gradient ───────────────────────────────
    for y in range(ROAD_TOP):
        _p(scr, H, W, y, 1, ' ' * (W - 2), P(8) | curses.A_DIM)

    # ── Road rows ────────────────────────────────────────────
    for i in range(ROAD_ROWS):
        screen_y = ROAD_TOP + i
        scale    = (i + 1) / ROAD_ROWS        # 0 (horizon) → 1 (near)
        half_w   = max(1, int(scale * max_hw))
        road_cx  = W // 2 - int(curve_per_row[i] * scale * 12) - player_x_offset

        # Scrolling stripe phase — faster at higher speed
        stripe_speed = max(1, int(p.speed / 6))
        alt = (i + (tick * stripe_speed // FPS)) % 8 < 4

        # ── Grass ────────────────────────────────────────────
        # Alternate between two grass chars for depth shimmering
        if scale < 0.25:
            g = '·' if alt else ' '           # far grass: subtle dots
        elif scale < 0.55:
            g = '░' if alt else '·'
        else:
            g = '▒' if alt else '░'           # near grass: chunky

        grass_attr  = P(3) | (curses.A_BOLD if alt else curses.A_DIM)

        # ── Road surface ─────────────────────────────────────
        # Alternate road color for depth bands (rumble-strip effect on edges)
        road_attr   = P(5) | curses.A_DIM

        # ── Kerb / edge: checkerboard rumble strips ──────────
        # Every 2 rows the kerb color flips RED/WHITE to give kerb feel
        kerb_alt    = ((i // 2) + (tick * stripe_speed // (FPS * 2))) % 2 == 0
        edge_attr   = (P(1) | curses.A_BOLD) if kerb_alt else (P(5) | curses.A_BOLD)

        rl = road_cx - half_w
        rr = road_cx + half_w

        try:
            # Left grass
            if rl > 1:
                scr.addstr(screen_y, 1, g * min(rl - 1, W - 2), grass_attr)
            # Left kerb strip (2 chars wide where space allows)
            if half_w >= 3:
                lk = max(1, rl)
                scr.addstr(screen_y, lk, '▐▌'[:max(0, W - lk)], edge_attr)
            elif rl >= 1:
                scr.addstr(screen_y, max(1, rl), '▌', edge_attr)

            # Road surface
            inner_l = max(1, rl + (2 if half_w >= 3 else 1))
            inner_r = min(W - 2, rr - (2 if half_w >= 3 else 1))
            if inner_l < inner_r:
                scr.addstr(screen_y, inner_l, ' ' * (inner_r - inner_l), road_attr)

            # Center dashes — scale width & spacing with perspective
            if scale > 0.08 and 0 < road_cx < W - 1:
                dash_phase = int(p.z / 30 + i * 1.2) % 10
                if scale > 0.5:
                    # Near rows: wide dash block
                    if dash_phase < 5:
                        dash_char = '━━'
                        _p(scr, H, W, screen_y, road_cx - 1, dash_char,
                           P(4) | curses.A_BOLD)
                elif scale > 0.25:
                    # Mid rows: single dash
                    if dash_phase < 4:
                        _p(scr, H, W, screen_y, road_cx, '─',
                           P(4) | curses.A_BOLD)
                else:
                    # Far rows: single dot
                    if dash_phase < 3:
                        _p(scr, H, W, screen_y, road_cx, '·',
                           P(4) | curses.A_DIM)

            # Right kerb strip
            if half_w >= 3:
                rk = min(rr, W - 3)
                scr.addstr(screen_y, rk, '▐▌'[:max(0, W - rk)], edge_attr)
            elif rr >= 1 and rr < W - 1:
                scr.addstr(screen_y, min(rr, W - 2), '▐', edge_attr)

            # Right grass
            if rr + 1 < W - 1:
                scr.addstr(screen_y, rr + 1,
                           g * min(W - rr - 3, W - 2), grass_attr)

        except curses.error:
            pass

        # ── Roadside scenery (parallax) ───────────────────────
        for seg_off, side, stype in SCENERY_DEFS:
            # World z of this scenery object
            seg_world_z = seg_off * SEG_LEN
            # Wrap to same lap
            lap_len     = LAP_SEGS * SEG_LEN
            obj_z       = (seg_world_z - (p.z % lap_len) + lap_len) % lap_len

            # Map obj_z to a render row (same projection as road)
            if obj_z < 50 or obj_z > 14000:
                continue
            row_frac = 1.0 - min(1.0, obj_z / 14000)
            obj_row  = int(row_frac * ROAD_ROWS)
            if obj_row != i:
                continue

            # Lateral screen position — well outside road edges
            edge_offset = int(half_w * 1.6)
            if side == 'L':
                sx = road_cx - edge_offset - 3
            else:
                sx = road_cx + edge_offset + 1

            if stype == 'tree':
                sprite = _TREE_L if side == 'L' else _TREE_R
                for si, srow in enumerate(sprite):
                    _p(scr, H, W, screen_y - len(sprite) + si + 1,
                       sx, srow, P(3) | curses.A_BOLD)
            elif stype == 'sign':
                for si, srow in enumerate(_SIGN):
                    _p(scr, H, W, screen_y - len(_SIGN) + si + 1,
                       sx, srow, P(6) | curses.A_BOLD)

        # ── Opponent cars ─────────────────────────────────────
        for opp in race.opps:
            rel_z = opp.z - p.z
            if 50 < rel_z < 18000:
                row_frac = 1.0 - min(1.0, rel_z / 18000)
                opp_row  = int(row_frac * ROAD_ROWS)
                if opp_row != i: continue

                sprite, col  = _opp_sprite(rel_z)
                half_sp_w    = max(1, len(sprite[0]) // 2)
                opp_lateral  = opp.x - p.x
                opp_screen_x = road_cx + int(opp_lateral / ROAD_HALF_W * half_w) - half_sp_w
                for si, srow in enumerate(sprite):
                    _p(scr, H, W, screen_y - len(sprite) + si + 1,
                       opp_screen_x, srow, P(col) | curses.A_BOLD)

    # ── Player car ────────────────────────────────────────────
    car_row  = ROAD_BOTTOM + CAR_ROW_GAP
    sprite   = _CAR_L if p.steer_dir < 0 else (_CAR_R if p.steer_dir > 0 else _CAR_C)
    car_col  = (W - len(sprite[0])) // 2
    off_road = abs(p.x) > ROAD_HALF_W
    car_attr = P(2) | curses.A_BOLD if off_road else P(1) | curses.A_BOLD
    for si, srow in enumerate(sprite):
        _p(scr, H, W, car_row + si, car_col, srow, car_attr)


# ═══════════════════════════════════════════════════════════════
#  HUD
# ═══════════════════════════════════════════════════════════════
def draw_hud(scr, H, W, race, tick):
    P   = curses.color_pair
    p   = race.player

    DIM  = P(5) | curses.A_DIM
    BLD  = P(5) | curses.A_BOLD
    PNK  = P(6) | curses.A_BOLD
    YLW  = P(4) | curses.A_BOLD
    GRN  = P(3) | curses.A_BOLD
    RED  = P(2) | curses.A_BOLD
    WHT  = P(7) | curses.A_BOLD if 7 <= curses.COLORS else BLD

    # ── Outer frame ───────────────────────────────────────────
    _p(scr, H, W, 0, 0, '╔' + '═' * (W - 2) + '╗', BLD)
    _p(scr, H, W, H - 1, 0, '╚' + '═' * (W - 2) + '╝', BLD)
    for r in range(1, H - 1):
        _p(scr, H, W, r, 0,     '║', P(5))
        _p(scr, H, W, r, W - 1, '║', P(5))

    # ── HUD row 1: LAP │ POS │ SPEED BAR ────────────────────────
    # Left side: lap counter and position
    lap_num  = min(p.lap + 1, LAPS)
    lap_str  = f' LAP {lap_num}/{LAPS} '
    pos      = race.position()
    pos_str  = f' POS: {_ordinal(pos)} '

    col = 1
    _p(scr, H, W, 1, col, lap_str,  YLW);  col += len(lap_str)
    _p(scr, H, W, 1, col, '│',      DIM);  col += 1
    _p(scr, H, W, 1, col, pos_str,  PNK);  col += len(pos_str)
    _p(scr, H, W, 1, col, '│',      DIM)

    # Centre: game title
    title = ' CLAUDE TURISMO '
    _p(scr, H, W, 1, (W - len(title)) // 2, title, PNK)

    # Right side: speed bar + km/h
    spd_frac = p.speed / MAX_SPEED
    bar_w    = 16
    filled   = int(bar_w * spd_frac)
    km_h     = int(p.speed * 1.2)   # cosmetic km/h scale

    if spd_frac < 0.45:
        spd_cp = P(3) | curses.A_BOLD    # green (slow)
    elif spd_frac < 0.75:
        spd_cp = P(4) | curses.A_BOLD    # yellow (mid)
    else:
        spd_cp = P(2) | curses.A_BOLD    # red (fast)

    bar_filled  = '▶' * filled
    bar_empty   = '░' * (bar_w - filled)
    speed_label = f'{km_h:3d} km/h '
    spd_str     = f' ▕{bar_filled}{bar_empty}▏ {speed_label}'
    _p(scr, H, W, 1, W - len(spd_str) - 1, spd_str, spd_cp)

    # ── HUD row 2: TIME │ BEST LAP ───────────────────────────────
    _p(scr, H, W, 2, 0, '╠' + '═' * (W - 2) + '╣', BLD)

    time_str = f' TIME: {_fmt_time(race.race_time)} '
    _p(scr, H, W, 2, 1, time_str, YLW)

    if race.best_lap:
        bl_str = f' BEST LAP: {_fmt_time(race.best_lap)} '
        _p(scr, H, W, 2, 1 + len(time_str), '│', DIM)
        _p(scr, H, W, 2, 2 + len(time_str), bl_str, GRN)

    # Controls row at bottom
    bot = H - 2
    _p(scr, H, W, bot - 1, 0, '╠' + '═' * (W - 2) + '╣', BLD)
    ctrl = '  ↑/W Accel   ↓/S Brake   ←/A Left   →/D Right   ESC Pause  '
    _p(scr, H, W, bot, 2, ctrl, DIM)

    # Off-road warning — flashing
    if abs(p.x) > ROAD_HALF_W:
        if (tick // 5) % 2 == 0:
            warn = '  !! OFF ROAD — SLOWER !!  '
            _p(scr, H, W, H // 2, (W - len(warn)) // 2, warn,
               P(2) | curses.A_BOLD | curses.A_REVERSE)


# ═══════════════════════════════════════════════════════════════
#  COUNTDOWN OVERLAY
# ═══════════════════════════════════════════════════════════════
_COUNT_3 = [
    "╔═════╗",
    "     ║",
    "╔═════╣",
    "╚═════╗",
    "     ║",
    "╔═════╣",
    "╚═════╝",
]
_COUNT_2 = [
    "╔═════╗",
    "      ║",
    "╔═════╣",
    "║      ",
    "╠═════╝",
    "╚══════",
]
_COUNT_1 = [
    "  ╔══╗",
    " ╔╝  ║",
    " ╚╗  ║",
    "  ║  ║",
    "╔═╩══╩═╗",
    "╚═══════╝",
]
_COUNT_GO = [
    "╔═════╗  ╔══╗",
    "║  ╔══╝  ║  ║",
    "║  ╠═══╗ ║  ║",
    "║  ╚══╗║ ║  ║",
    "╚═════╝╚═╩══╝",
]

def draw_countdown(scr, H, W, race):
    P = curses.color_pair
    ticks_left = race.countdown
    # 90 ticks total: 3→60, 2→30, 1→0, GO briefly shown at 0
    if   ticks_left > 60: digit, art, cp = '3', _COUNT_3, P(2) | curses.A_BOLD
    elif ticks_left > 30: digit, art, cp = '2', _COUNT_2, P(4) | curses.A_BOLD
    elif ticks_left > 5:  digit, art, cp = '1', _COUNT_1, P(3) | curses.A_BOLD
    else:                 digit, art, cp = 'GO', _COUNT_GO, P(6) | curses.A_BOLD | curses.A_REVERSE
    bw = max(len(row) for row in art)
    bx = (W - bw) // 2
    by = H // 2 - len(art) // 2 - 2
    # Dim backing box
    for bi in range(len(art) + 4):
        _p(scr, H, W, by - 1 + bi, bx - 2, ' ' * (bw + 4),
           P(5) | curses.A_REVERSE)
    for si, row in enumerate(art):
        _p(scr, H, W, by + si, bx, row, cp)


# ═══════════════════════════════════════════════════════════════
#  INTRO
# ═══════════════════════════════════════════════════════════════
def draw_intro(scr, H, W, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0,     0, '╔' + '═' * (W - 2) + '╗', P(5) | curses.A_BOLD)
    _p(scr, H, W, H - 1, 0, '╚' + '═' * (W - 2) + '╝', P(5) | curses.A_BOLD)
    for r in range(1, H - 1):
        _p(scr, H, W, r, 0,     '║', P(5))
        _p(scr, H, W, r, W - 1, '║', P(5))

    # Title — two-section: CLAUDE in one color, TURISMO in another
    title_top_half    = TITLE[:6]
    title_bottom_half = TITLE[6:]
    top_attrs  = [P(4) | curses.A_BOLD, P(1) | curses.A_BOLD,
                  P(6) | curses.A_BOLD, P(4) | curses.A_BOLD,
                  P(1) | curses.A_BOLD, P(6) | curses.A_BOLD]
    bot_attrs  = [P(5) | curses.A_DIM,
                  P(6) | curses.A_BOLD, P(4) | curses.A_BOLD,
                  P(6) | curses.A_BOLD, P(4) | curses.A_BOLD,
                  P(6) | curses.A_BOLD, P(4) | curses.A_BOLD]

    start_row = 1
    for i, (line, attr) in enumerate(zip(TITLE, top_attrs + bot_attrs)):
        if not line: continue
        tx = max(1, (W - len(line)) // 2)
        _p(scr, H, W, start_row + i, tx, line, attr)

    title_end = start_row + len(TITLE)

    _p(scr, H, W, title_end, 1, '▓' * (W - 2), P(5) | curses.A_DIM)

    sub = '  P S E U D O - 3 D   T E R M I N A L   R A C I N G  '
    pulse = P(6) | curses.A_BOLD if (tick // 12) % 2 == 0 else P(4) | curses.A_BOLD
    _p(scr, H, W, title_end + 1, max(1, (W - len(sub)) // 2), sub, pulse)

    # Animated preview road
    mid = title_end + 3
    for i in range(min(8, H - mid - 5)):
        scale = (i + 1) / 8
        hw    = int(scale * (W // 2 - 6))
        cx    = W // 2 + int(math.sin(tick * 0.04) * 6 * (1 - scale))
        alt   = (i + tick // 3) % 8 < 4
        g     = '▒' if alt else '░'
        grass_a = P(3) | (curses.A_BOLD if alt else curses.A_DIM)
        road_a  = P(5) | curses.A_DIM
        lx = max(1, cx - hw)
        rx = cx + hw
        if cx - hw - 2 > 0:
            try: scr.addstr(mid + i, 1, g * (cx - hw - 2), grass_a)
            except curses.error: pass
        if hw > 0 and lx < W - 1:
            try: scr.addstr(mid + i, lx, ' ' * (hw * 2), road_a)
            except curses.error: pass
        if rx + 1 < W - 2:
            try: scr.addstr(mid + i, rx + 1, g * (W - rx - 3), grass_a)
            except curses.error: pass
        # Center dash
        if (i + tick // 3) % 6 < 3 and 0 < cx < W - 1:
            _p(scr, H, W, mid + i, cx, '│', P(4) | curses.A_BOLD)

    # Preview player car in intro
    car_preview_row = mid + min(8, H - mid - 5)
    if car_preview_row < H - 5:
        car_col = (W - len(_CAR_C[0])) // 2
        for si, srow in enumerate(_CAR_C):
            _p(scr, H, W, car_preview_row + si, car_col, srow,
               P(1) | curses.A_BOLD)

    if (tick // 18) % 2 == 0:
        msg = '[ SPACE ]  START RACE'
        _p(scr, H, W, H - 4, (W - len(msg)) // 2, msg, P(4) | curses.A_BOLD)
    _p(scr, H, W, H - 3, 0, '╠' + '═' * (W - 2) + '╣', P(5) | curses.A_BOLD)
    _p(scr, H, W, H - 2, 2, f'  {LAPS} LAPS  ·  3 AI OPPONENTS  ·  BEAT THE CLOCK  ',
       P(5) | curses.A_DIM)
    scr.refresh()


# ═══════════════════════════════════════════════════════════════
#  HOW TO PLAY
# ═══════════════════════════════════════════════════════════════
def draw_how_to_play(scr, H, W, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0,     0, '╔' + '═' * (W - 2) + '╗', P(5) | curses.A_BOLD)
    _p(scr, H, W, H - 1, 0, '╚' + '═' * (W - 2) + '╝', P(5) | curses.A_BOLD)
    for r in range(1, H - 1):
        _p(scr, H, W, r, 0,     '║', P(5))
        _p(scr, H, W, r, W - 1, '║', P(5))
    _p(scr, H, W, 1, 1, '▓▒░' + '─' * (W - 8) + '░▒▓', P(5) | curses.A_DIM)
    t = '  H O W   T O   R A C E  '
    _p(scr, H, W, 1, (W - len(t)) // 2, t, P(4) | curses.A_BOLD)
    _p(scr, H, W, 2, 0, '╠' + '═' * (W - 2) + '╣', P(5) | curses.A_BOLD)

    lines = [
        ('GOAL', None),
        ('', None),
        ('  Complete 3 laps faster than the AI opponents.', P(5)),
        ('  Stay on the road — grass slows you down!', P(5)),
        ("  Brake before tight corners or you'll spin wide.", P(5)),
        ('', None),
        ('CONTROLS', None),
        ('', None),
        ('  ↑ / W      Accelerate', P(6) | curses.A_BOLD),
        ('  ↓ / S      Brake', P(6) | curses.A_BOLD),
        ('  ← / A      Steer left', P(6) | curses.A_BOLD),
        ('  → / D      Steer right', P(6) | curses.A_BOLD),
        ('  ESC        Pause', P(5) | curses.A_DIM),
        ('', None),
        ('TIPS', None),
        ('', None),
        ('  ▶  Lift off the gas before corners, accelerate out', P(5) | curses.A_DIM),
        ('  ▶  Road curves build at the horizon — read ahead!', P(5) | curses.A_DIM),
        ('  ▶  Rubber-band AI — stay in front at all costs!', P(5) | curses.A_DIM),
        ('  ▶  Red kerb strips mark the road edge — hug them', P(5) | curses.A_DIM),
    ]

    for i, (text, attr) in enumerate(lines):
        y = 4 + i
        if y >= H - 4: break
        if attr is None:
            _p(scr, H, W, y, 4, text, P(4) | curses.A_BOLD)
        else:
            _p(scr, H, W, y, 2, text, attr)

    if (tick // 18) % 2 == 0:
        msg = '[ SPACE ]  READY — GO!'
        _p(scr, H, W, H - 3, (W - len(msg)) // 2, msg, P(2) | curses.A_BOLD)
    _p(scr, H, W, H - 2, 0, '╠' + '═' * (W - 2) + '╣', P(5) | curses.A_BOLD)
    scr.refresh()


# ═══════════════════════════════════════════════════════════════
#  PAUSE
# ═══════════════════════════════════════════════════════════════
def draw_pause(scr, H, W):
    Renderer(scr, H, W).pause_overlay('CLAUDE TURISMO', CONTROLS)


# ═══════════════════════════════════════════════════════════════
#  FINISH / PODIUM
# ═══════════════════════════════════════════════════════════════
_PODIUM_1 = [
    "  ╔═══════╗  ",
    "  ║  1st  ║  ",
    "  ║  WIN  ║  ",
    "══╩═══════╩══",
]
_PODIUM_2 = [
    "╔═══════╗    ",
    "║  2nd  ║    ",
    "╩═══════╩    ",
]
_PODIUM_3 = [
    "    ╔═══════╗",
    "    ║  3rd  ║",
    "    ╩═══════╝",
]

_CHEQUERED = "▐█░█░█░█░█░█▌"

def draw_finish(scr, H, W, race, tick):
    P  = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0,     0, '╔' + '═' * (W - 2) + '╗', P(5) | curses.A_BOLD)
    _p(scr, H, W, H - 1, 0, '╚' + '═' * (W - 2) + '╝', P(5) | curses.A_BOLD)
    for r in range(1, H - 1):
        _p(scr, H, W, r, 0,     '║', P(5))
        _p(scr, H, W, r, W - 1, '║', P(5))

    # Scrolling chequered flag banner
    flag_offset = (tick // 2) % len(_CHEQUERED)
    flag_banner = (_CHEQUERED * ((W // len(_CHEQUERED)) + 2))[flag_offset:flag_offset + W - 2]
    _p(scr, H, W, 1, 1, flag_banner, P(5) | curses.A_BOLD)
    _p(scr, H, W, 2, 0, '╠' + '═' * (W - 2) + '╣', P(5) | curses.A_BOLD)

    # Heading
    hdg = '  C H E C K E R E D   F L A G  '
    pulse = P(4) | curses.A_BOLD if (tick // 15) % 2 == 0 else P(6) | curses.A_BOLD
    _p(scr, H, W, 3, (W - len(hdg)) // 2, hdg, pulse)

    # Position display
    fp   = race.finish_place
    pos_labels = {
        1: ('  *** RACE WINNER ***  ', P(4) | curses.A_BOLD),
        2: ('  2nd Place            ', P(6) | curses.A_BOLD),
        3: ('  3rd Place            ', P(5) | curses.A_BOLD),
        4: ('  4th Place            ', P(5) | curses.A_DIM),
    }
    pos_txt, pos_attr = pos_labels.get(fp, (f'  P{fp}  ', P(5) | curses.A_DIM))
    _p(scr, H, W, 4, (W - len(pos_txt)) // 2, pos_txt, pos_attr)

    # Podium art for top 3
    mr = 5
    if fp == 1 and mr + len(_PODIUM_1) < H - 6:
        for si, row in enumerate(_PODIUM_1):
            _p(scr, H, W, mr + si, (W - len(row)) // 2, row, P(4) | curses.A_BOLD)
        mr += len(_PODIUM_1) + 1
    elif fp == 2 and mr + len(_PODIUM_2) < H - 6:
        for si, row in enumerate(_PODIUM_2):
            _p(scr, H, W, mr + si, (W - len(row)) // 2, row, P(6) | curses.A_BOLD)
        mr += len(_PODIUM_2) + 1
    elif fp == 3 and mr + len(_PODIUM_3) < H - 6:
        for si, row in enumerate(_PODIUM_3):
            _p(scr, H, W, mr + si, (W - len(row)) // 2, row, P(5) | curses.A_BOLD)
        mr += len(_PODIUM_3) + 1
    else:
        mr += 1

    # Race stats
    _p(scr, H, W, mr, 3,
       f'  RACE TIME  {_fmt_time(race.race_time)}  ', P(5) | curses.A_BOLD)
    if race.best_lap:
        bl = f'  BEST LAP   {_fmt_time(race.best_lap)}  '
        _p(scr, H, W, mr + 1, 3, bl, P(3) | curses.A_BOLD)

    _p(scr, H, W, mr + 3, 3, '  LAP TIMES:', P(5) | curses.A_BOLD)
    for i, lt in enumerate(race.player.lap_times[:LAPS]):
        _p(scr, H, W, mr + 4 + i, 5,
           f'  Lap {i + 1}:  {_fmt_time(lt)}', P(5))

    # Prompt
    if (tick // 18) % 2 == 0:
        msg = '  [ SPACE ] Race Again     [ Q ] Quit  '
        _p(scr, H, W, H - 3, (W - len(msg)) // 2, msg,
           P(5) | curses.A_REVERSE)
    scr.refresh()


# ═══════════════════════════════════════════════════════════════
#  CONTROLS LIST  (used by pause overlay)
# ═══════════════════════════════════════════════════════════════
CONTROLS = [
    '↑ / W        Accelerate',
    '↓ / S        Brake',
    '← / A        Steer left',
    '→ / D        Steer right',
    'ESC          Pause / Resume',
    'Q            Quit to Claudcade',
]


# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════
def main(scr):
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()
    try: curses.mousemask(0)
    except curses.error: pass

    state = INTRO
    race  = None
    tick  = 0
    nxt   = time.perf_counter()

    while True:
        now = time.perf_counter()
        if now < nxt:
            time.sleep(max(0.0, nxt - now - 0.001))
            continue
        dt  = min(1 / FPS * 2, now - (nxt - 1 / FPS))
        nxt += 1 / FPS
        tick += 1

        H, W = scr.getmaxyx()
        keys = set()
        while True:
            k = scr.getch()
            if k == -1: break
            keys.add(k)

        if 27 in keys:
            if   state == PLAY:  state = PAUSE
            elif state == PAUSE: state = PLAY
            else: break

        if state == INTRO:
            draw_intro(scr, H, W, tick)
            if ord(' ') in keys:
                state = HOW_TO_PLAY; tick = 0

        elif state == HOW_TO_PLAY:
            draw_how_to_play(scr, H, W, tick)
            if ord(' ') in keys:
                race = Race(); state = PLAY; tick = 0

        elif state == PLAY:
            race.update(keys, False, dt)
            scr.erase()
            draw_road(scr, H, W, race, tick)
            draw_hud(scr, H, W, race, tick)
            # Show countdown overlay while race hasn't started
            if race.countdown > 0:
                draw_countdown(scr, H, W, race)
            scr.refresh()
            if race.finished:
                state = FINISH; tick = 0

        elif state == PAUSE:
            draw_road(scr, H, W, race, tick)
            draw_hud(scr, H, W, race, tick)
            draw_pause(scr, H, W)
            if ord('r') in keys or ord('R') in keys: state = PLAY
            if ord('q') in keys or ord('Q') in keys: break

        elif state == FINISH:
            draw_finish(scr, H, W, race, tick)
            if ord(' ') in keys:
                race = Race(); state = HOW_TO_PLAY; tick = 0
            if ord('q') in keys or ord('Q') in keys: break

if __name__ == '__main__':
    run_game(main, 'Claude Turismo')
