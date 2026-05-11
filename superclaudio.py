#!/usr/bin/env python3
"""Super Claudio — Side-Scrolling Platformer · ESC to pause"""
from __future__ import annotations

import curses

from claudcade_engine import (
    Camera,
    Engine,
    Particles,
    Renderer,
    Scene,
    at_safe,
    clamp,
)
from claudcade_engine import draw_how_to_play as _engine_how_to_play
from claudcade_scores import player_label, submit_async

# ── Tuning constants ─────────────────────────────────────────────────────────
FPS         = 30
GRAV        = 0.55      # downward acceleration (cells / frame^2)
JUMP_V      = 3.6       # initial jump velocity (cells / frame)
JUMP_HOLD   = 0.32      # extra lift per frame while jump held (variable jump)
JUMP_FRAMES = 10        # max frames the jump-hold lift applies
MAX_FALL    = 2.6
WALK        = 0.55
RUN         = 0.95
AIR_CTRL    = 0.85
START_LIVES = 3
COIN_PTS    = 100
STOMP_PTS   = 200
FLAG_PTS    = 1000
TIME_LIMIT  = 300       # seconds for level — counts down

# Title art (block font)
TITLE_ART = [
    r" ███████╗██╗   ██╗██████╗ ███████╗██████╗ ",
    r" ██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗",
    r" ███████╗██║   ██║██████╔╝█████╗  ██████╔╝",
    r" ╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗",
    r" ███████║╚██████╔╝██║     ███████╗██║  ██║",
    r" ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝",
    r"     ██████╗██╗      █████╗ ██╗   ██╗██████╗ ██╗ ██████╗ ",
    r"    ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗",
    r"    ██║     ██║     ███████║██║   ██║██║  ██║██║██║   ██║",
    r"    ██║     ██║     ██╔══██║██║   ██║██║  ██║██║██║   ██║",
    r"    ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝",
    r"     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ ",
]

CONTROLS = [
    'A / D / Arrows   Move left / right',
    'SPACE / W / Up   Jump (hold for higher)',
    'SHIFT or J       Run (faster)',
    'ESC              Pause / Resume',
    'R                Resume from pause',
    'Q                Quit',
]

# ── Level map ────────────────────────────────────────────────────────────────
# Each row is one terrain row. The BOTTOM row of LEVEL is the ground line.
# Glyph legend:
#   '#'  solid ground / underground block
#   '='  floating platform (solid top, walk-through from below)
#   'B'  brick (solid)
#   '?'  question block (solid, gives a coin)
#   'c'  collectible coin (pickup)
#   'E'  enemy spawn (walker)
#   'F'  flagpole (win)
#   '.'  pit hint (visual only — not used at runtime)
#   ' '  empty sky
#
# The level is 240 columns wide and 12 rows tall.  Row 0 is the SKY,
# row 11 is the GROUND tile row.  Coordinates inside the game treat
# world_x in columns and world_y in rows from the top.

LEVEL = [
    # 0         1         2         3         4         5         6         7         8         9        10        11        12        13        14        15        16        17        18        19        20        21        22        23
    # 0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
    "                                                                                                                                                                                                                                                ",  # 0  sky
    "                                                                                                                                                                                                                                                ",  # 1
    "                                                                                                                                                                                                                                                ",  # 2
    "                                                                                                                                                                                                                                                ",  # 3
    "                                                                                                                                                                                                                                              c ",  # 4
    "                              ccc                                                                                  ccc                                                                                                                  cccccc F",  # 5
    "                ccc          =====            cc                          cc          c c          c                                cccc            ccc                                       cc                            ccc        ====== F",  # 6
    "                            B?B?B           =====                B?B?B   ====        =====        ====                ?B?B?       ======          =====            c c c c                  =====                        =======================",  # 7
    "        cc                                                                                                                                                       ========                                  c c c c                              F",  # 8
    "       ====                                          E                                  E                                       E                                                  E E                  =======         E E                    F",  # 9
    "                       E                E                              E       E                          E                            E                  E                                                                E                   F",  # 10
    "##########  ##########  ###################  ###############   ##################  #####################  ###################  ################# #####################  ###############################  ##############################   #######",  # 11
]

LEVEL_W = max(len(r) for r in LEVEL)
LEVEL_H = len(LEVEL)
GROUND_ROW = LEVEL_H - 1   # the row treated as ground tiles
FLAG_COL = None  # detected from map

# Build solid lookups and collectible sets from the map.
def _build_world():
    solids = set()          # (col, row) of solid tiles (ground, brick, ?-block, platform)
    coins  = set()          # (col, row) of pickup coins
    enemies_init = []        # list of (col, row) where E appears
    flag_col = None
    flag_top = None
    for row, line in enumerate(LEVEL):
        for col, ch in enumerate(line):
            if ch in ('#', 'B', '?', '='):
                solids.add((col, row))
            elif ch == 'c':
                coins.add((col, row))
            elif ch == 'E':
                # spawn on top of nearest solid below
                gr = row + 1
                while gr < LEVEL_H and (col, gr) not in solids and LEVEL[gr][col] != '#':
                    gr += 1
                # enemy stands on row gr-1 (so its feet are at gr-1)
                enemies_init.append((col, gr - 1))
            elif ch == 'F':
                if flag_col is None:
                    flag_col = col
                    flag_top = row
    return solids, coins, enemies_init, flag_col, flag_top


SOLIDS, COIN_CELLS_INIT, ENEMY_SPAWNS, FLAG_COL, FLAG_TOP = _build_world()


# ── Helpers ──────────────────────────────────────────────────────────────────

def is_solid(col: int, row: int) -> bool:
    if row >= LEVEL_H or row < 0:
        return False
    if col < 0:
        return True   # walls on left edge block player
    if col >= LEVEL_W:
        return False
    return (col, row) in SOLIDS


# ── Player ───────────────────────────────────────────────────────────────────

class Player:
    """Box-collider platformer body. Position is float in world cells."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.w = 1.0      # 1-cell-wide collider
        self.h = 2.0      # 2 rows tall (head + body)
        self.facing = 1
        self.on_ground = False
        self.jump_held = 0   # frames the jump button has been held since takeoff
        self.alive = True
        self.dying = 0       # frames into death animation
        self.invuln = 0      # post-respawn iframes
        self.anim = 0
        self.coyote = 0      # frames since left ground (forgiving jump)

    # rectangle helpers
    def bottom(self) -> float: return self.y + self.h
    def top(self) -> float:    return self.y
    def left(self) -> float:   return self.x
    def right(self) -> float:  return self.x + self.w

    def _hits_solid(self, x: float, y: float) -> bool:
        # Check the cells the AABB overlaps
        lo_col = int(x)
        hi_col = int(x + self.w - 0.001)
        lo_row = int(y)
        hi_row = int(y + self.h - 0.001)
        for c in range(lo_col, hi_col + 1):
            for r in range(lo_row, hi_row + 1):
                if is_solid(c, r):
                    return True
        return False

    def update(self, inp, world) -> None:
        if not self.alive:
            self.dying += 1
            # death arc: fall off-screen
            self.vy += GRAV * 0.6
            self.y += self.vy
            return

        if self.invuln > 0:
            self.invuln -= 1

        running = inp.pressed(ord('j'), ord('J')) or inp.pressed(curses.KEY_SLEFT) or 1 in inp.mouse_pressed
        # Also: shift modifiers come through curses as KEY_SLEFT/SRIGHT or via uppercase letters
        speed = RUN if running else WALK

        ctrl = 1.0 if self.on_ground else AIR_CTRL
        dvx = 0.0
        if inp.left:
            dvx -= speed
            self.facing = -1
        if inp.right:
            dvx += speed
            self.facing = 1

        # Smooth horizontal velocity
        target = dvx
        # Snappy controls — blend toward target
        self.vx = self.vx * (1.0 - 0.6 * ctrl) + target * (0.6 * ctrl)
        if abs(self.vx) < 0.04 and dvx == 0:
            self.vx = 0.0

        # Jump: variable-height. Initiate when jump just-pressed and grounded
        # (or within coyote window).
        jump_btn_now = inp.pressed(ord(' '), ord('w'), ord('W'), curses.KEY_UP)
        jump_just = inp.just_pressed(ord(' '), ord('w'), ord('W'), curses.KEY_UP)

        if jump_just and (self.on_ground or self.coyote > 0):
            self.vy = -JUMP_V
            self.on_ground = False
            self.jump_held = 1
            self.coyote = 0
            world.particles.spawn(
                (self.x + 0.5), (self.y + self.h),
                vx=-self.vx * 0.3, vy=0.4, char='.', color=5, life=6,
            )
        elif jump_btn_now and self.jump_held > 0 and self.jump_held < JUMP_FRAMES and self.vy < 0:
            self.vy -= JUMP_HOLD
            self.jump_held += 1
        else:
            # release cancels variable hold
            if not jump_btn_now:
                self.jump_held = 0

        # Gravity
        self.vy += GRAV
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        # ── Horizontal collision ──
        new_x = self.x + self.vx
        if self._hits_solid(new_x, self.y):
            # step pixel-by-pixel toward target until blocked
            step = 0.1 if self.vx > 0 else -0.1
            test = self.x
            while abs(test - new_x) > 0.001:
                next_test = test + step
                if self._hits_solid(next_test, self.y):
                    break
                test = next_test
                if (step > 0 and test >= new_x) or (step < 0 and test <= new_x):
                    test = new_x
                    break
            new_x = test
            self.vx = 0.0
        # left wall: cannot leave the world
        if new_x < 0:
            new_x = 0
            self.vx = 0.0
        self.x = new_x

        # ── Vertical collision ──
        prev_bottom = self.bottom()
        new_y = self.y + self.vy
        was_on_ground = self.on_ground
        self.on_ground = False

        if self.vy > 0:
            # falling — check feet
            if self._hits_solid(self.x, new_y):
                # find the floor row just below previous bottom
                floor_row = int(prev_bottom)
                # snap so bottom == floor_row
                snap_y = float(floor_row) - self.h
                self.y = snap_y
                self.vy = 0.0
                self.on_ground = True
            else:
                self.y = new_y
        elif self.vy < 0:
            # rising — check head
            if self._hits_solid(self.x, new_y):
                # find ceiling — snap top to row below the ceiling
                ceil_row = int(new_y)
                # ascending bump: place top right below the solid cell
                self.y = float(ceil_row + 1)
                self.vy = 0.0
                # If we hit a question/brick directly above, pop a coin out.
                head_col = int(self.x + self.w / 2)
                head_row = ceil_row
                world.try_bonk(head_col, head_row)
            else:
                self.y = new_y
        else:
            self.y = new_y

        # Coyote: if just walked off a ledge, give a brief jump grace.
        if was_on_ground and not self.on_ground and self.vy >= 0:
            self.coyote = 5
        elif self.coyote > 0:
            self.coyote -= 1

        # Pit death — fell past the world floor.
        if self.y > LEVEL_H + 2:
            self.alive = False
            self.dying = 30  # already in pit; short delay before respawn

        self.anim += 1


# ── Enemy (walker) ───────────────────────────────────────────────────────────

class Walker:
    """Paces left/right on its current row until blocked or about to fall."""

    def __init__(self, col: int, row: int) -> None:
        self.x = float(col)
        self.y = float(row - 1)   # top of 1-tall sprite (feet on `row`)
        self.h = 1.0
        self.w = 1.0
        self.vx = -0.35
        self.alive = True
        self.dying = 0
        self.anim = 0

    def update(self) -> None:
        if not self.alive:
            self.dying += 1
            return
        self.anim += 1
        nx = self.x + self.vx
        feet_row = int(self.y + self.h)
        # Solid wall in front?
        front_col = int(nx + (self.w if self.vx > 0 else 0))
        wall = is_solid(front_col, int(self.y))
        if wall:
            self.vx = -self.vx
            return
        # About to walk off a ledge? (only if currently on solid ground)
        ahead_below_col = int(nx + (self.w / 2) + (0.6 if self.vx > 0 else -0.6))
        if not is_solid(ahead_below_col, feet_row):
            # Reverse rather than falling, for predictable Goomba pacing
            self.vx = -self.vx
            return
        self.x = nx


def aabb(ax, ay, aw, ah, bx, by, bw, bh) -> bool:
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


# ── World / level state ──────────────────────────────────────────────────────

class World:
    def __init__(self) -> None:
        self.player = Player(2.0, float(GROUND_ROW - 2))
        self.coins  = set(COIN_CELLS_INIT)  # mutable copy
        self.bonked: dict[tuple[int, int], int] = {}  # (col,row) -> frames showing pop
        self.enemies = [Walker(c, r) for (c, r) in ENEMY_SPAWNS]
        self.particles = Particles()
        self.popups = []   # list of {x,y,txt,ttl}
        self.score = 0
        self.coins_collected = 0
        self.lives = START_LIVES
        self.level_won = False
        self.death_overlay = 0   # frames remaining to show death banner
        self.win_timer = 0
        self.time_left = float(TIME_LIMIT)
        self.checkpoint_x = 2.0
        self.bumped_blocks: set[tuple[int, int]] = set()  # ?-blocks already used

    def respawn(self) -> bool:
        """Returns True if player has lives left and should keep playing."""
        self.lives -= 1
        if self.lives < 0:
            return False
        self.player = Player(self.checkpoint_x, float(GROUND_ROW - 2))
        self.player.invuln = 60
        return True

    def try_bonk(self, col: int, row: int) -> None:
        """Player's head hit a tile from below. Handle ?-block coin pops."""
        if row < 0 or row >= LEVEL_H or col < 0 or col >= LEVEL_W:
            return
        ch = LEVEL[row][col]
        if ch == '?' and (col, row) not in self.bumped_blocks:
            self.bumped_blocks.add((col, row))
            self.score += COIN_PTS
            self.coins_collected += 1
            self.bonked[(col, row)] = 14
            self.popups.append({
                'x': col + 0.5, 'y': row - 0.5,
                'txt': f'+{COIN_PTS}', 'ttl': 22,
            })
            self.particles.explode(int(col), int(row - 1), count=6, color=4)

    def update(self, inp) -> None:
        # Tick time
        if not self.level_won and self.player.alive:
            self.time_left -= 1.0 / FPS
            if self.time_left <= 0:
                self.time_left = 0
                self.player.alive = False
                self.player.dying = 30

        self.player.update(inp, self)
        for e in self.enemies:
            e.update()

        # Coin pickup
        if self.player.alive:
            px = self.player.x
            py = self.player.y
            pw = self.player.w
            ph = self.player.h
            collected = []
            for (c, r) in self.coins:
                if aabb(px, py, pw, ph, c + 0.1, r + 0.1, 0.8, 0.8):
                    collected.append((c, r))
            for cell in collected:
                self.coins.discard(cell)
                self.score += COIN_PTS
                self.coins_collected += 1
                self.popups.append({
                    'x': cell[0] + 0.5, 'y': cell[1] - 0.3,
                    'txt': f'+{COIN_PTS}', 'ttl': 22,
                })
                self.particles.spawn(cell[0] + 0.5, float(cell[1]),
                                     vx=0, vy=-0.4, char='*', color=4, life=10)

        # Enemy interactions
        if self.player.alive and self.player.invuln == 0:
            px = self.player.x
            py = self.player.y
            pw = self.player.w
            ph = self.player.h
            for e in self.enemies:
                if not e.alive:
                    continue
                if aabb(px, py, pw, ph, e.x, e.y, e.w, e.h):
                    # Stomp if player is falling and feet near top of enemy.
                    feet = py + ph
                    if self.player.vy > 0 and feet - e.y < 0.9:
                        e.alive = False
                        e.dying = 8
                        self.score += STOMP_PTS
                        self.player.vy = -JUMP_V * 0.7   # bounce
                        self.player.jump_held = 1
                        self.popups.append({
                            'x': e.x + 0.5, 'y': e.y - 0.3,
                            'txt': f'+{STOMP_PTS}', 'ttl': 22,
                        })
                        self.particles.explode(int(e.x), int(e.y), count=8, color=2)
                    else:
                        self.player.alive = False
                        self.player.dying = 1
                        self.player.vy = -2.5
                        self.particles.explode(int(px), int(py), count=14, color=2)
                        break

        # Flag detection — win condition
        if (self.player.alive and not self.level_won and
                FLAG_COL is not None and self.player.x >= FLAG_COL - 0.5):
            self.level_won = True
            self.score += FLAG_PTS
            # bonus per second left
            bonus = int(self.time_left) * 10
            self.score += bonus
            self.popups.append({
                'x': FLAG_COL + 0.5, 'y': max(2, FLAG_TOP or 5),
                'txt': f'FLAG +{FLAG_PTS + bonus}', 'ttl': 60,
            })
            self.win_timer = 90

        # Update fx
        for b in list(self.bonked):
            self.bonked[b] -= 1
            if self.bonked[b] <= 0:
                del self.bonked[b]

        for pop in self.popups:
            pop['y'] -= 0.06
            pop['ttl'] -= 1
        self.popups = [p for p in self.popups if p['ttl'] > 0]

        self.particles.update()

        # Cull dead enemies
        self.enemies = [e for e in self.enemies
                        if e.alive or e.dying < 14]


# ── Drawing ──────────────────────────────────────────────────────────────────

_p = at_safe


def _color_at(ch: str) -> tuple[int, str]:
    """Map level glyph to (color_pair, render_char)."""
    if ch == '#': return (3, '▓')     # green ground
    if ch == 'B': return (4, '▒')     # gold brick
    if ch == '?': return (4, '?')     # gold ?-block
    if ch == '=': return (3, '=')     # green platform
    return (5, ' ')


def draw_game(scr, world: World, cam: Camera, H: int, W: int, tick: int) -> None:
    P = curses.color_pair
    scr.erase()
    def p(r, c, s, a=0): _p(scr, H, W, r, c, s, a)

    # World→screen mapping. We use a 1:1 mapping in columns and rows but
    # offset by cam.x for horizontal scrolling. We carve out:
    #   rows 0–2   : HUD
    #   rows 3..H-5: play area (12 level rows compressed/expanded to fit)
    #   rows H-3..H-2: footer
    TOP = 3
    BOT = H - 4
    play_h = BOT - TOP
    # Compute vertical offset so the bottom level row maps to BOT-1.
    # We want LEVEL row -> screen row: r_screen = (row - row_offset) + TOP
    # where row_offset places GROUND_ROW at BOT-1.
    row_off = GROUND_ROW - (BOT - 1 - TOP)
    # If the level is taller than play area, clip from the top (sky).
    if row_off < 0:
        row_off = 0

    cam_col = int(cam.x)

    def world_to_screen(col: float, row: float) -> tuple[int, int]:
        sc = int(col) - cam_col + 1
        sr = int(row) - row_off + TOP
        return sr, sc

    # ── HUD ──────────────────────────────────────────────────────────────
    p(0, 0, '╔' + '═' * (W - 2) + '╗', P(5) | curses.A_BOLD)
    p(1, 0, '║', P(5) | curses.A_BOLD)
    p(1, W - 1, '║', P(5) | curses.A_BOLD)
    p(2, 0, '╠' + '═' * (W - 2) + '╣', P(5) | curses.A_BOLD)

    # Lives (left)
    lives_str = f'  LIVES  {"♥" * max(0, world.lives)}{"·" * max(0, START_LIVES - world.lives)}'
    p(1, 1, lives_str, P(2) | curses.A_BOLD)

    # World name (center)
    world_str = '★ SUPER CLAUDIO  ·  WORLD 1-1 ★'
    p(1, max(1, (W - len(world_str)) // 2), world_str, P(4) | curses.A_BOLD)

    # Score + coins + time (right)
    time_int = int(max(0, world.time_left))
    right_str = f'COINS:{world.coins_collected:02d}  TIME:{time_int:03d}  SCORE:{world.score:06d}  '
    p(1, max(1, W - len(right_str) - 2), right_str, P(3) | curses.A_BOLD)

    # ── Sky gradient ─────────────────────────────────────────────────────
    # Top half: pale blue (cyan dim); bottom near ground: darker
    for r in range(TOP, BOT):
        # subtle clouds drifting slowly
        pass
    # Cloud drift — sparse glyphs that scroll a bit slower than world
    cloud_off = (tick // 6) % 80
    cloud_rows = [TOP + 1, TOP + 3]
    cloud_x_seeds = [4, 22, 38, 55, 71, 90, 108, 124, 145, 160, 178, 195, 212]
    for cr in cloud_rows:
        for sx in cloud_x_seeds:
            col_screen = (sx - cam_col // 2 - cloud_off) % (W - 4) + 1
            if 1 < col_screen < W - 6:
                p(cr, col_screen, '⌒⌒⌒', P(5) | curses.A_DIM)

    # Far hills (parallax) — drawn a few rows above ground
    hill_row = BOT - 2
    if hill_row >= TOP:
        hill_off = int(cam.x * 0.4) % (W * 2)
        pattern = '   ▁▂▃▄▃▂▁     ▁▂▃▄▅▄▃▂▁    ▁▂▃▂▁      ▁▂▃▄▃▂▁     '
        long_pat = pattern * (W // len(pattern) + 4)
        seg = long_pat[hill_off: hill_off + W - 2]
        p(hill_row - 1, 1, seg, P(3) | curses.A_DIM)

    # ── Tiles ────────────────────────────────────────────────────────────
    first_col = max(0, cam_col - 1)
    last_col  = min(LEVEL_W, cam_col + W + 2)
    for row in range(row_off, min(LEVEL_H, row_off + play_h + 1)):
        line = LEVEL[row]
        for col in range(first_col, last_col):
            if col >= len(line):
                continue
            ch = line[col]
            if ch in (' ', '.', 'c', 'E', 'F'):
                continue
            sr, sc = world_to_screen(col, row)
            if not (TOP <= sr < BOT and 0 < sc < W - 1):
                continue
            if ch == '#':
                # ground/underground — checker pattern
                glyph = '▓' if ((col + row) % 2 == 0) else '▒'
                p(sr, sc, glyph, P(3) | curses.A_BOLD)
            elif ch == '=':
                # platform — single row of bricks
                p(sr, sc, '═', P(3) | curses.A_BOLD)
            elif ch == 'B':
                p(sr, sc, '▒', P(4) | curses.A_BOLD)
            elif ch == '?':
                if (col, row) in world.bumped_blocks:
                    p(sr, sc, '▒', P(5) | curses.A_DIM)
                else:
                    glyph = '?' if (tick // 8) % 4 != 0 else '◆'
                    p(sr, sc, glyph, P(4) | curses.A_BOLD)

    # ── Flagpole ─────────────────────────────────────────────────────────
    if FLAG_COL is not None:
        for row in range(0, LEVEL_H):
            line = LEVEL[row]
            if FLAG_COL < len(line) and line[FLAG_COL] == 'F':
                sr, sc = world_to_screen(FLAG_COL, row)
                if TOP <= sr < BOT and 0 < sc < W - 1:
                    p(sr, sc, '│', P(5) | curses.A_BOLD)
        # Flag itself at top
        if FLAG_TOP is not None:
            sr, sc = world_to_screen(FLAG_COL, FLAG_TOP)
            if TOP <= sr < BOT and 0 < sc < W - 2:
                if world.level_won:
                    sr2, sc2 = world_to_screen(FLAG_COL, FLAG_TOP + 1)
                    p(sr,  sc, '▼', P(2) | curses.A_BOLD)
                    if TOP <= sr2 < BOT:
                        p(sr2, sc, '═══', P(2) | curses.A_BOLD)
                else:
                    p(sr, sc, '▶═', P(2) | curses.A_BOLD)
                    p(sr + 1 if sr + 1 < BOT else sr, sc, '│', P(5) | curses.A_BOLD)

    # ── Coins ────────────────────────────────────────────────────────────
    spin = (tick // 4) % 4
    coin_glyph = ['◉', '○', '◎', '○'][spin]
    for (c, r) in world.coins:
        if c < cam_col - 1 or c > cam_col + W + 1:
            continue
        sr, sc = world_to_screen(c, r)
        if TOP <= sr < BOT and 0 < sc < W - 1:
            p(sr, sc, coin_glyph, P(4) | curses.A_BOLD)

    # ── Enemies ──────────────────────────────────────────────────────────
    for e in world.enemies:
        if e.x < cam_col - 2 or e.x > cam_col + W + 1:
            continue
        sr, sc = world_to_screen(e.x, e.y)
        if not (TOP <= sr < BOT and 0 < sc < W - 1):
            continue
        if not e.alive:
            # squish frame
            p(sr, sc, '▁▁', P(2) | curses.A_DIM)
        else:
            walk_frame = (e.anim // 5) % 2
            faces = '◣◤' if e.vx < 0 else '◥◢'
            top_face = ['◉◉', '◉•'][walk_frame]
            p(sr - 1 if sr - 1 >= TOP else sr, sc, top_face, P(2) | curses.A_BOLD)
            p(sr, sc, faces, P(2) | curses.A_BOLD)

    # ── Player ───────────────────────────────────────────────────────────
    pl = world.player
    sr, sc = world_to_screen(pl.x, pl.y)
    blink_skip = pl.invuln > 0 and (tick // 3) % 2 == 0
    if not blink_skip:
        if pl.alive:
            head = '◯'
            if pl.on_ground:
                if abs(pl.vx) > 0.05:
                    body = '╫' if (pl.anim // 4) % 2 == 0 else '╪'
                    feet = '╱╲' if (pl.anim // 4) % 2 == 0 else '╲╱'
                else:
                    body = '║'
                    feet = '╨'
            else:
                body = '╪'
                feet = '╱ ' if pl.facing > 0 else ' ╲'
            color = curses.A_BOLD | P(1)
            if 0 < sc < W - 2:
                if TOP <= sr < BOT:     p(sr,     sc, head, color)
                if TOP <= sr + 1 < BOT: p(sr + 1, sc, body, color)
                if TOP <= sr + 2 < BOT: p(sr + 2, sc, feet, color)
        else:
            # death sprite — X eyes
            if TOP <= sr < BOT:     p(sr,     sc, '✕', P(2) | curses.A_BOLD)
            if TOP <= sr + 1 < BOT: p(sr + 1, sc, '│', P(2) | curses.A_BOLD)
            if TOP <= sr + 2 < BOT: p(sr + 2, sc, '╳', P(2) | curses.A_BOLD)

    # ── Particles & popups ──────────────────────────────────────────────
    # Adjust particle positions through camera before drawing.
    # Particles store screen-like cols already (we pass world cells), so
    # we re-render manually using the same world_to_screen helper.
    for part in world.particles._active:
        sr2, sc2 = world_to_screen(part['x'], part['y'])
        if TOP <= sr2 < BOT and 0 < sc2 < W - 1:
            fade = part['life'] / max(1, part['max_life'])
            attr = curses.A_BOLD if fade > 0.4 else curses.A_DIM
            p(sr2, sc2, part['char'], P(part['color']) | attr)
    for pop in world.popups:
        sr2, sc2 = world_to_screen(pop['x'], pop['y'])
        if TOP <= sr2 < BOT and 0 < sc2 < W - len(pop['txt']) - 1:
            attr = curses.A_BOLD if pop['ttl'] > 10 else curses.A_DIM
            p(sr2, sc2, pop['txt'], P(4) | attr)

    # ── Death / Win overlays ─────────────────────────────────────────────
    if not pl.alive and pl.dying > 8:
        mr = (TOP + BOT) // 2 - 1
        if world.lives > 0:
            box = ['  ╔═══════════════╗  ',
                   '  ║   OOPS!   :(  ║  ',
                   '  ╚═══════════════╝  ']
            clr = P(4) | curses.A_BOLD
        else:
            box = ['  ╔═══════════════╗  ',
                   '  ║   GAME OVER   ║  ',
                   '  ╚═══════════════╝  ']
            clr = P(2) | curses.A_BOLD
        for di, ln in enumerate(box):
            p(mr + di, max(1, (W - len(ln)) // 2), ln, clr)

    if world.level_won and world.win_timer > 0:
        mr = (TOP + BOT) // 2 - 1
        box = ['  ╔════════════════════╗  ',
               '  ║   COURSE  CLEAR!   ║  ',
               '  ╚════════════════════╝  ']
        for di, ln in enumerate(box):
            p(mr + di, max(1, (W - len(ln)) // 2), ln, P(3) | curses.A_BOLD)

    # ── Footer ───────────────────────────────────────────────────────────
    p(H - 3, 0, '╠' + '═' * (W - 2) + '╣', P(5) | curses.A_BOLD)
    p(H - 2, 0, '║', P(5) | curses.A_BOLD)
    p(H - 2, W - 1, '║', P(5) | curses.A_BOLD)
    hint = '[ A/D: Move ]  [ SPACE: Jump ]  [ J: Run ]  [ ESC: Pause ]'
    p(H - 2, max(1, (W - len(hint)) // 2), hint, P(5) | curses.A_DIM)
    p(H - 1, 0, '╚' + '═' * (W - 2) + '╝', P(5) | curses.A_BOLD)


def draw_intro(scr, H, W, tick) -> None:
    P = curses.color_pair
    scr.erase()
    def p(r, c, s, a=0): _p(scr, H, W, r, c, s, a)

    # Border
    p(0, 0, '╔' + '═' * (W - 2) + '╗', P(5) | curses.A_BOLD)
    p(H - 1, 0, '╚' + '═' * (W - 2) + '╝', P(5) | curses.A_BOLD)
    for r in range(1, H - 1):
        p(r, 0,     '║', P(5) | curses.A_BOLD)
        p(r, W - 1, '║', P(5) | curses.A_BOLD)

    # Sky pattern — drifting clouds
    cloud_off = (tick // 5) % 60
    cloud_rows = [2, 4, 6]
    seeds = [4, 18, 32, 50, 64, 80, 96, 110]
    for cr in cloud_rows:
        for sx in seeds:
            col = (sx + cloud_off) % (W - 4) + 1
            if 1 < col < W - 6:
                p(cr, col, '⌒⌒⌒', P(5) | curses.A_DIM)

    # Title block
    ta = TITLE_ART
    # narrow fallback
    if W < max(len(line) for line in ta) + 4:
        ta = [
            r" ███████╗ ██╗   ██╗ ██████╗ ",
            r" ██╔════╝ ██║   ██║ ██╔══██╗",
            r" ███████╗ ██║   ██║ ██████╔╝",
            r" ╚════██║ ██║   ██║ ██╔═══╝ ",
            r" ███████║ ╚██████╔╝ ██║     ",
            r" ╚══════╝  ╚═════╝  ╚═╝     ",
            r"  C L A U D I O             ",
        ]
    sr = max(2, (H - len(ta) - 10) // 2)
    palette = [P(2) | curses.A_BOLD, P(4) | curses.A_BOLD,
               P(3) | curses.A_BOLD, P(1) | curses.A_BOLD,
               P(6) | curses.A_BOLD, P(4) | curses.A_BOLD]
    for i, line in enumerate(ta):
        cx = max(1, (W - len(line)) // 2)
        p(sr + i, cx, line, palette[i % len(palette)])

    sub = '◄══  SIDE-SCROLLING  PLATFORMER  ══►'
    p(sr + len(ta) + 1, max(1, (W - len(sub)) // 2), sub, P(5) | curses.A_BOLD)

    # Sample sprite + flag preview (animated)
    ty = H - 9
    walk = (tick // 6) % 2
    body = '╫' if walk == 0 else '╪'
    feet = '╱╲' if walk == 0 else '╲╱'
    p(ty,     6, '◯',  P(1) | curses.A_BOLD)
    p(ty + 1, 6, body, P(1) | curses.A_BOLD)
    p(ty + 2, 6, feet, P(1) | curses.A_BOLD)
    # walker
    coin_g = ['◉', '○', '◎', '○'][(tick // 4) % 4]
    p(ty,     W - 14, '◉◉',   P(2) | curses.A_BOLD)
    p(ty + 1, W - 14, '◣◤',   P(2) | curses.A_BOLD)
    p(ty,     W - 22, coin_g, P(4) | curses.A_BOLD)
    # flag
    p(ty - 2, W - 8, '▶═', P(2) | curses.A_BOLD)
    for r in range(ty - 1, ty + 3):
        p(r, W - 8, '│', P(5) | curses.A_BOLD)
    # ground line under demos
    p(ty + 3, 2, '▓' * (W - 4), P(3) | curses.A_DIM)

    if (tick // 18) % 2 == 0:
        msg = '◄  PRESS SPACE TO START  ►'
        p(H - 4, max(1, (W - len(msg)) // 2), msg, P(4) | curses.A_BOLD)
    hint = '[ SPACE: Start ]   [ ESC: Quit ]'
    p(H - 2, max(1, (W - len(hint)) // 2), hint, P(5) | curses.A_DIM)


def draw_endscreen(scr, H, W, score, tick, sub_result, *, victory: bool) -> None:
    P = curses.color_pair
    scr.erase()
    def p(r, c, s, a=0): _p(scr, H, W, r, c, s, a)

    p(0, 0, '╔' + '═' * (W - 2) + '╗', P(5) | curses.A_BOLD)
    p(H - 1, 0, '╚' + '═' * (W - 2) + '╝', P(5) | curses.A_BOLD)
    for r in range(1, H - 1):
        p(r, 0,     '║', P(5) | curses.A_BOLD)
        p(r, W - 1, '║', P(5) | curses.A_BOLD)

    if victory:
        header = [
            r"  ██╗   ██╗██╗ ██████╗████████╗ ██████╗ ██████╗ ██╗   ██╗",
            r"  ██║   ██║██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝",
            r"  ██║   ██║██║██║        ██║   ██║   ██║██████╔╝ ╚████╔╝ ",
            r"  ╚██╗ ██╔╝██║██║        ██║   ██║   ██║██╔══██╗  ╚██╔╝  ",
            r"   ╚████╔╝ ██║╚██████╗   ██║   ╚██████╔╝██║  ██║   ██║   ",
            r"    ╚═══╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ",
        ]
        clr = P(3) | curses.A_BOLD
    else:
        header = [
            r"  ██████╗  █████╗ ███╗   ███╗███████╗     ██████╗ ██╗   ██╗███████╗██████╗ ",
            r" ██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔═══██╗██║   ██║██╔════╝██╔══██╗",
            r" ██║  ███╗███████║██╔████╔██║█████╗      ██║   ██║██║   ██║█████╗  ██████╔╝",
            r" ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗",
            r" ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║",
            r"  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝     ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝",
        ]
        clr = P(2) | curses.A_BOLD

    # fallback narrow header
    if W < max(len(line) for line in header) + 4:
        if victory:
            header = ['V I C T O R Y']
        else:
            header = ['G A M E   O V E R']

    mr = max(2, (H - len(header) - 10) // 2)
    for i, line in enumerate(header):
        p(mr + i, max(1, (W - len(line)) // 2), line, clr)

    mr2 = mr + len(header) + 2
    sc_lines = [
        '╔════════════════════════════╗',
        f'║  FINAL SCORE:  {score:07d}   ║',
        '╚════════════════════════════╝',
    ]
    for i, ln in enumerate(sc_lines):
        cc = P(4) | curses.A_BOLD if i == 1 else P(5) | curses.A_BOLD
        p(mr2 + i, max(1, (W - len(ln)) // 2), ln, cc)

    pl = player_label()
    p(mr2 + 4, max(1, (W - len(pl) - 4) // 2), f'◄  {pl}  ►', P(1) | curses.A_BOLD)

    if sub_result and sub_result[0]:
        rank = sub_result[0].get('rank')
        if rank:
            if rank <= 10:
                badge = '★ ELITE ★'
                badge_color = P(3) | curses.A_BOLD
            elif rank <= 50:
                badge = '▲ TOP 50 ▲'
                badge_color = P(4) | curses.A_BOLD
            else:
                badge = '◆ RANKED ◆'
                badge_color = P(6) | curses.A_BOLD
            rm = f'  {badge}  Global rank: #{rank}  '
            p(mr2 + 5, max(1, (W - len(rm)) // 2), rm, badge_color)
        elif sub_result[0].get('is_new_pb'):
            msg = '  NEW PERSONAL BEST  '
            p(mr2 + 5, max(1, (W - len(msg)) // 2), msg, P(3) | curses.A_BOLD)
    elif sub_result and sub_result[0] is None:
        p(mr2 + 5, max(1, (W - 26) // 2), '  Submitting score...  ', P(5) | curses.A_DIM)

    if (tick // 18) % 2 == 0:
        msg = '▸ SPACE = Play Again  │  ESC = Quit ◂'
        p(H - 3, max(1, (W - len(msg)) // 2), msg, P(4) | curses.A_BOLD)


def draw_pause(scr, H, W) -> None:
    Renderer(scr, H, W).pause_overlay('Super Claudio', CONTROLS)


def draw_howto(scr, H, W, tick) -> None:
    _engine_how_to_play(
        scr, H, W, tick,
        goal=[
            'Run and jump through World 1-1, collect coins, stomp enemies,',
            'and reach the flagpole at the end of the level.',
        ],
        controls=[
            'A / D / Arrows    Move left / right',
            'SPACE / W / Up    Jump  (hold for higher jump)',
            'J or Shift        Run (faster movement)',
            'ESC               Pause',
        ],
        tips=[
            '• Jump on top of enemies to stomp them (+200 pts).',
            '• Touching enemies from the side is fatal.',
            '• ?-blocks pop a coin when you bonk them from below.',
            '• Time limit: 300 seconds. Bonus points for leftover time.',
            '• Falling in a pit costs you a life.',
        ],
    )


# ── Scenes ───────────────────────────────────────────────────────────────────

class IntroScene(Scene):
    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')): return 'howto'
        if inp.just_pressed(27, ord('q'), ord('Q')): return 'quit'

    def draw(self, r, tick):
        draw_intro(r._scr, self.engine.H, self.engine.W, tick)


class HowToScene(Scene):
    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' '), ord('\n'), 10, 13): return 'play'
        if inp.just_pressed(27, ord('q'), ord('Q')):       return 'quit'

    def draw(self, r, tick):
        draw_howto(r._scr, self.engine.H, self.engine.W, tick)


class PlayScene(Scene):
    def on_enter(self):
        self.world = World()
        self.cam   = Camera()
        self.cam.set_bounds(0, max(0, LEVEL_W - 20))
        self.cam.x = 0.0
        self.paused = False

    def update(self, inp, tick, dt):
        if inp.just_pressed(27):
            self.paused = not self.paused
            return None
        if self.paused:
            if inp.just_pressed(ord('r'), ord('R')): self.paused = False
            if inp.just_pressed(ord('q'), ord('Q')): return 'quit'
            return None

        self.world.update(inp)

        # camera follows player horizontally
        target_x = clamp(self.world.player.x - self.engine.W * 0.35,
                         0.0, max(0.0, LEVEL_W - self.engine.W))
        self.cam.follow(target_x, 0, lerp=0.18)

        pl = self.world.player

        # Win path
        if self.world.level_won:
            self.world.win_timer -= 1
            if self.world.win_timer <= 0:
                sub: list = [None]
                extra = f'Win coins={self.world.coins_collected}'
                submit_async('superclaudio', self.world.score, extra, sub)
                return ('win', (self.world.score, sub))

        # Death path
        if not pl.alive:
            pl.dying += 0   # already incremented in player.update; no double-count
            if pl.dying > 45:
                if self.world.respawn():
                    return None
                # out of lives
                sub2: list = [None]
                extra2 = f'Loss coins={self.world.coins_collected}'
                submit_async('superclaudio', self.world.score, extra2, sub2)
                return ('gameover', (self.world.score, sub2))

    def draw(self, r, tick):
        draw_game(r._scr, self.world, self.cam,
                  self.engine.H, self.engine.W, tick)
        if self.paused:
            draw_pause(r._scr, self.engine.H, self.engine.W)


class GameOverScene(Scene):
    def on_enter(self):
        if isinstance(self.payload, tuple) and len(self.payload) == 2:
            self.score, self.sub = self.payload
        else:
            self.score, self.sub = 0, [None]

    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' '), ord('\n'), 10, 13): return 'play'
        if inp.just_pressed(27, ord('q'), ord('Q')):       return 'quit'

    def draw(self, r, tick):
        draw_endscreen(r._scr, self.engine.H, self.engine.W,
                       self.score, tick, self.sub, victory=False)


class WinScene(Scene):
    def on_enter(self):
        if isinstance(self.payload, tuple) and len(self.payload) == 2:
            self.score, self.sub = self.payload
        else:
            self.score, self.sub = 0, [None]

    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' '), ord('\n'), 10, 13): return 'play'
        if inp.just_pressed(27, ord('q'), ord('Q')):       return 'quit'

    def draw(self, r, tick):
        draw_endscreen(r._scr, self.engine.H, self.engine.W,
                       self.score, tick, self.sub, victory=True)


def main() -> None:
    Engine('Super Claudio', fps=FPS) \
        .scene('intro',    IntroScene()) \
        .scene('howto',    HowToScene()) \
        .scene('play',     PlayScene()) \
        .scene('gameover', GameOverScene()) \
        .scene('win',      WinScene()) \
        .run('intro')


if __name__ == '__main__':
    main()
