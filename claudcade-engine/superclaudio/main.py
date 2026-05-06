"""Super Claudio — main game engine and loop."""
import curses, time, random, math, sys

from .levels import LEVELS, TILE_SOLID, TILE_DISPLAY

from claudcade_engine import setup_colors, Renderer, run_game, ParticleDict
TITLE, HOW_TO_PLAY, PLAY, PAUSE, LEVEL_CLEAR, GAME_OVER, WIN = range(7)
FPS        = 30
GRAVITY    = 0.55      # tile units / frame²
JUMP_VX    = -8.5      # initial jump velocity (negative = up)
WALK_SPEED = 0.22      # tile units / frame
RUN_SPEED  = 0.35      # with shift (hold J)
MAX_FALL   = 0.8       # terminal velocity
TILE_W     = 2         # screen columns per tile
TILE_H     = 1         # screen rows per tile
TITLE_ART = [
    r"  ██████  ██    ██ ██████  ███████ ██████      ██████ ██       █████  ██    ██ ██████  ██  ██████  ",
    r" ██       ██    ██ ██   ██ ██      ██   ██    ██      ██      ██   ██ ██    ██ ██   ██ ██ ██    ██ ",
    r" ██████   ██    ██ ██████  █████   ██████     ██      ██      ███████ ██    ██ ██   ██ ██ ██    ██ ",
    r"      ██  ██    ██ ██      ██      ██   ██    ██      ██      ██   ██ ██    ██ ██   ██ ██ ██    ██ ",
    r" ██████    ██████  ██      ███████ ██   ██     ██████ ███████ ██   ██  ██████  ██████  ██  ██████  ",
]

GAME_OVER_ART = [
    r"  ██████   █████  ███    ███ ███████      ██████  ██    ██ ███████ ██████  ",
    r" ██       ██   ██ ████  ████ ██          ██    ██ ██    ██ ██      ██   ██ ",
    r" ██   ███ ███████ ██ ████ ██ █████       ██    ██ ██    ██ █████   ██████  ",
    r" ██    ██ ██   ██ ██  ██  ██ ██          ██    ██  ██  ██  ██      ██   ██ ",
    r"  ██████  ██   ██ ██      ██ ███████      ██████    ████   ███████ ██   ██ ",
]

WIN_ART = [
    r" ██    ██  ██████  ██    ██     ██     ██ ██ ███    ██ ██ ",
    r"  ██  ██  ██    ██ ██    ██     ██     ██ ██ ████   ██ ██ ",
    r"   ████   ██    ██ ██    ██     ██  █  ██ ██ ██ ██  ██ ██ ",
    r"    ██    ██    ██ ██    ██     ██ ███ ██ ██ ██  ██ ██    ",
    r"    ██     ██████   ██████       ███ ███  ██ ██   ████ ██ ",
]

LEVEL_CLEAR_ART = [
    r" ██████  ██      ███████  █████  ██████  ██ ",
    r" ██      ██      ██      ██   ██ ██   ██ ██ ",
    r" ██      ██      █████   ███████ ██████  ██ ",
    r" ██      ██      ██      ██   ██ ██   ██    ",
    r" ██████  ███████ ███████ ██   ██ ██   ██ ██ ",
]
def _p(scr, H, W, r, c, s, a=0):
    try:
        if 0 <= r < H-1 and 0 <= c < W:
            scr.addstr(r, c, s[:max(0, W-c)], a)
    except curses.error:
        pass
class Level:
    def __init__(self, data: dict):
        self.world    = data['world']
        self.name     = data['name']
        self.time_lim = data['time']
        self.rows     = data['data']
        self.height   = len(self.rows)
        self.width    = max(len(r) for r in self.rows)
        self.q_map    = dict(data.get('question_contents', {}))  # (x,y)->content
        self.used_q   = set()
        self.px0, self.py0 = data['player_start']

        # Parse enemies and coins from tile data
        self.init_coins: list[tuple[int,int]]   = []
        self.init_enemies: list[tuple[str,int,int]] = []
        for r, row in enumerate(self.rows):
            for c, ch in enumerate(row):
                if ch == 'c': self.init_coins.append((c, r))
                elif ch in ('g','t','h'): self.init_enemies.append((ch, c, r))

    def tile(self, tx: int, ty: int) -> str:
        if ty < 0 or ty >= self.height: return '='
        row = self.rows[ty]
        if tx < 0 or tx >= len(row): return ' '
        return row[tx]

    def is_solid(self, tx: int, ty: int) -> bool:
        t = self.tile(tx, ty)
        return t in TILE_SOLID

    def hit_block(self, tx: int, ty: int) -> str | None:
        """Player hits block from below. Returns item spawned or None."""
        t = self.tile(tx, ty)
        if (tx, ty) in self.used_q:
            return None
        if t == '?':
            content = self.q_map.get((tx, ty), 'coin')
            self.used_q.add((tx, ty))
            return content
        if t == '#':
            return 'break'
        return None
class Player:
    def __init__(self, tx: float, ty: float):
        self.x       = float(tx)
        self.y       = float(ty)
        self.vx      = 0.0
        self.vy      = 0.0
        self.grounded= False
        self.alive   = True
        self.power   = 0      # 0=small, 1=super, 2=fire
        self.lives   = 3
        self.score   = 0
        self.coins   = 0
        self.dead_timer = 0
        self.invuln  = 0
        self.facing  = 1   # 1=right, -1=left
        self.anim    = 0   # frame counter for walk anim
        self.flag_slide = 0  # >0 = sliding down flag

    def hit(self):
        if self.invuln > 0: return
        if self.power > 0:
            self.power -= 1
            self.invuln = 90
        else:
            self.alive   = False
            self.dead_timer = 90
            self.vy = -6.0

    def add_coin(self):
        self.coins += 1
        self.score += 200
        if self.coins >= 100:
            self.coins -= 100
            self.lives += 1

    @property
    def height(self): return 2 if self.power > 0 else 1

    def sprite(self, tick):
        """Return list of strings (rows, each 3 chars wide)."""
        walk_frame = (tick // 5) % 2
        facing_r = self.facing >= 0
        if self.power == 0:
            # Small Claudio — facing direction shown by cap tilt
            if not self.grounded:
                # Airborne: arms up
                return ['(◙)'] if facing_r else ['(◙)']
            # Walking: alternate feet
            if walk_frame == 0:
                return ['◄◙►'] if facing_r else ['◄◙►']
            else:
                return ['◄◙►'] if facing_r else ['◄◙►']
        elif self.power == 1:
            # Super Claudio — two rows, distinct hat
            top = '(◉)' if facing_r else '(◉)'
            if not self.grounded:
                bot = '└┘ ' if facing_r else ' └┘'
            elif walk_frame == 0:
                bot = '/◉\\' if facing_r else '\\◉/'
            else:
                bot = '|◉|'
            return [top, bot]
        else:
            # Fire Claudio — glowing star hat, fire arms
            top = '[◈]'
            if not self.grounded:
                bot = '✦ ✦' if facing_r else '✦ ✦'
            elif walk_frame == 0:
                bot = '/◈\\' if facing_r else '\\◈/'
            else:
                bot = '|◈|'
            return [top, bot]


class Enemy:
    def __init__(self, etype: str, tx: float, ty: float):
        self.type    = etype   # 'g'=glitchy 't'=tokenoopa 'h'=hallucigator
        self.x       = float(tx)
        self.y       = float(ty)
        self.vx      = -0.12  # start moving left
        self.vy      = 0.0
        self.alive   = True
        self.shell   = False   # tokenoopa stomped into shell
        self.shell_moving = False
        self.dead_timer = 0
        self.anim    = 0

    def sprite(self, tick):
        af = (tick // 6) % 2
        if not self.alive:
            # Stomped/dead — flat
            return ['─✕─']
        if self.type == 'g':
            # Glitchy: angry brow, googly eyes, shuffling feet
            if af == 0:
                return ['▽_▽']   # eyes down menacing
            else:
                return ['×_×']   # X eyes variant
        elif self.type == 't':
            if self.shell:
                # Tokenoopa in shell — spinning if moving
                if self.shell_moving:
                    return ['[»]' if af == 0 else '[«]']
                return ['[■]']
            # Tokenoopa walking — shell on back, beaky face
            if af == 0:
                return ['Ö_Ö']
            else:
                return ['Ö‿Ö']
        elif self.type == 'h':
            # Hallucigator — flying, swooping wings
            if af == 0:
                return ['◁●▷']
            else:
                return ['△●△']
        return ['[?]']

    @property
    def height(self):
        return 1


class Item:
    def __init__(self, itype: str, tx: float, ty: float):
        self.type  = itype  # 'coin','mushroom','flower','fireball'
        self.x     = float(tx)
        self.y     = float(ty)
        self.vx    = 0.12 if itype == 'mushroom' else (0.25 if itype == 'fireball' else 0.0)
        self.vy    = -0.3 if itype in ('mushroom','flower') else -0.2
        self.alive = True
        self.bounces = 0
        self.anim  = 0

    def sprite(self, tick=0):
        af = (tick // 6) % 2
        if self.type == 'coin':
            # Spinning coin — alternate frames
            return ['◆ ' if af == 0 else '○ ']
        if self.type == 'mushroom':
            # Mushroom cap + stem
            return ['(∩)']
        if self.type == 'flower':
            # Fire flower in bloom
            return ['❀ ' if af == 0 else '✿ ']
        if self.type == 'fireball':
            # Bouncing fireball
            return ['✦ ' if af == 0 else '· ']
        return [' ? ']
class Game:
    def __init__(self, level_idx: int = 0, lives: int = 3, score: int = 0, coins: int = 0):
        self.level_idx  = level_idx
        self.level      = Level(LEVELS[level_idx])
        self.timer      = float(self.level.time_lim)
        self.player     = Player(self.level.px0, self.level.py0)
        self.player.lives = lives
        self.player.score = score
        self.player.coins = coins
        self.cam_x      = 0.0
        self.enemies: list[Enemy] = []
        self.items:   list[Item]  = []
        self.coins_set: set[tuple[int,int]] = set()
        self._init_entities()
        self.particles: list[ParticleDict] = []

    def _init_entities(self):
        for (etype, ex, ey) in self.level.init_enemies:
            e = Enemy(etype, ex, ey - 0.01)
            self.enemies.append(e)
        for (cx, cy) in self.level.init_coins:
            self.coins_set.add((cx, cy))

    def tile(self, tx: int, ty: int) -> str:
        t = self.level.tile(tx, ty)
        if t == 'c' and (tx, ty) not in self.coins_set:
            return ' '  # coin collected
        if t == '?' and (tx, ty) in self.level.used_q:
            return 'X'
        return t

    def is_solid(self, tx: int, ty: int) -> bool:
        return self.tile(tx, ty) in TILE_SOLID

    def _resolve_x(self, ent, new_x, width=1.0):
        left  = new_x
        right = new_x + width - 0.05
        ty_top = int(ent.y - ent.height + 0.1)
        ty_bot = int(ent.y - 0.05)
        for ty in range(ty_top, ty_bot + 1):
            if self.is_solid(int(left), ty):
                new_x = int(left) + 1.0
                ent.vx = abs(ent.vx)
                break
            if self.is_solid(int(right), ty):
                new_x = int(right) - width
                ent.vx = -abs(ent.vx)
                break
        return new_x

    def _resolve_y(self, ent, new_y, width=0.9) -> tuple[float, bool, int | None]:
        """Returns (resolved_y, grounded, hit_block_ty)."""
        hit_block = None
        grounded  = False
        left  = ent.x + 0.05
        right = ent.x + width - 0.05
        foot_y = new_y
        head_y = new_y - ent.height + 0.05

        # Ceiling check (moving up)
        if ent.vy < 0:
            head_row = int(head_y)
            for tx in (int(left), int(right)):
                if self.is_solid(tx, head_row):
                    new_y  = head_row + ent.height
                    ent.vy = 0.0
                    hit_block = (tx, head_row)
                    break

        # Floor check (moving down or standing)
        if ent.vy >= 0:
            foot_row = int(foot_y)
            if foot_y - int(foot_y) < 0.15: foot_row = int(foot_y)
            for tx in (int(left), int(right)):
                if self.is_solid(tx, foot_row):
                    new_y    = float(foot_row)
                    ent.vy   = 0.0
                    grounded = True
                    break

        return new_y, grounded, hit_block

    def update(self, keys: set, tick: int) -> str | None:
        """Returns next state or None to stay in PLAY."""
        p = self.player
        dt = 1.0  # frame-based physics
        self.timer -= 1.0 / FPS
        if self.timer <= 0:
            p.hit()
            if not p.alive:
                p.lives -= 1
                return GAME_OVER if p.lives < 0 else None
        if not p.alive:
            p.dead_timer -= 1
            p.y += p.vy * dt
            p.vy += GRAVITY * dt
            if p.dead_timer <= 0:
                p.lives -= 1
                return GAME_OVER if p.lives < 0 else None
            return None

        if p.flag_slide > 0:
            p.flag_slide -= 1
            p.y += 0.15
            if p.flag_slide <= 0:
                p.score += max(0, int(self.timer)) * 50
                return LEVEL_CLEAR
            return None

        if p.invuln > 0: p.invuln -= 1
        p.anim += 1
        left   = curses.KEY_LEFT  in keys or ord('a') in keys
        right  = curses.KEY_RIGHT in keys or ord('d') in keys
        jump   = curses.KEY_UP    in keys or ord('w') in keys or ord(' ') in keys
        run    = ord('j') in keys or ord('f') in keys
        shoot  = ord('j') in keys

        spd = RUN_SPEED if run else WALK_SPEED
        if left:  p.vx = max(p.vx - 0.05, -spd); p.facing = -1
        elif right: p.vx = min(p.vx + 0.05, spd); p.facing = 1
        else:
            # Friction
            if p.vx > 0: p.vx = max(0.0, p.vx - 0.04)
            elif p.vx < 0: p.vx = min(0.0, p.vx + 0.04)

        if jump and p.grounded:
            p.vy = JUMP_VX
            p.grounded = False

        # Fire!
        if p.power == 2 and shoot and tick % 10 == 0:
            fb = Item('fireball', p.x + (1.0 if p.facing > 0 else 0.0), p.y - 0.5)
            fb.vx = 0.4 * p.facing
            fb.vy = 0.0
            self.items.append(fb)
        p.vy = min(p.vy + GRAVITY * dt, MAX_FALL)
        new_x = p.x + p.vx * dt
        new_y = p.y + p.vy * dt

        # Resolve X
        p.x = self._resolve_x(p, new_x, 0.9)

        # Resolve Y
        new_y, p.grounded, hit_blk = self._resolve_y(p, new_y, 0.9)
        p.y = new_y

        if hit_blk:
            tx, ty = hit_blk
            result = self.level.hit_block(tx, ty)
            if result == 'break':
                if p.power > 0:
                    self.particles.append({'x': tx*2, 'y': ty, 'life': 12, 'type': 'break'})
                    p.score += 50
            elif result == 'coin':
                p.add_coin()
                p.score += 200
                self.particles.append({'x': tx*2, 'y': ty-1, 'life': 20, 'type': 'coin'})
            elif result in ('mushroom', 'flower'):
                item = Item(result, float(tx), float(ty - 1))
                self.items.append(item)

        # Collect in-grid coins
        ftx, fty = int(p.x + 0.45), int(p.y - 0.5)
        if (ftx, fty) in self.coins_set:
            self.coins_set.discard((ftx, fty))
            p.add_coin()
            self.particles.append({'x': ftx*2, 'y': fty, 'life': 18, 'type': 'coin'})

        # Fall into pit
        if p.y > self.level.height + 2:
            p.alive = False
            p.dead_timer = 60

        # Clamp to level bounds (don't scroll left past start)
        p.x = max(0.0, min(p.x, self.level.width - 2.0))

        # Camera follows player
        screen_tiles = 38
        target_cam = p.x - screen_tiles // 3
        self.cam_x = max(0.0, min(float(self.level.width - screen_tiles), target_cam))
        for e in self.enemies:
            if not e.alive: continue

            if e.type == 'h':
                # Hallucigator floats left
                e.x += e.vx
                e.y += math.sin(tick * 0.08) * 0.05  # bobbing
                if e.x < -2: e.alive = False
                # Wall bounce
                if self.is_solid(int(e.x), int(e.y)):
                    e.vx *= -1
            else:
                # Apply gravity to non-fliers
                e.vy = min(e.vy + GRAVITY * dt, MAX_FALL)
                new_ex = e.x + e.vx
                new_ey = e.y + e.vy

                # X collision → reverse direction
                ex2 = self._resolve_x(e, new_ex, 0.85)
                e.x = ex2
                new_ey, e_ground, _ = self._resolve_y(e, new_ey, 0.85)
                e.y = new_ey
                if e_ground and not self.is_solid(int(e.x + 0.5), int(e.y + 0.3)):
                    e.vx *= -1  # turn at edges

                # Off level
                if e.y > self.level.height + 2: e.alive = False

            # Enemy vs player collision
            if p.alive and p.invuln == 0:
                px_l, px_r = p.x + 0.05, p.x + 0.85
                py_t       = p.y - p.height + 0.1
                py_b       = p.y - 0.05
                ex_l, ex_r = e.x + 0.05, e.x + 0.85
                ey_t       = e.y - e.height + 0.1
                ey_b       = e.y - 0.05

                if px_l < ex_r and px_r > ex_l and py_t < ey_b and py_b > ey_t:
                    # Player lands on top of enemy?
                    if py_b <= ey_t + 0.35 and p.vy > 0:
                        # Stomp!
                        p.vy = JUMP_VX * 0.45
                        p.score += 100
                        if e.type == 't' and not e.shell:
                            e.shell = True
                            e.vx    = 0.0
                        else:
                            e.alive = False
                            self.particles.append({'x': int(e.x)*2, 'y': int(e.y), 'life': 14, 'type': 'stomp'})
                    else:
                        # Player gets hit
                        if not (e.type == 't' and e.shell and not e.shell_moving):
                            p.hit()
                            if not p.alive:
                                p.dead_timer = 90
                        elif e.type == 't' and e.shell:
                            # Kick shell
                            e.shell_moving = True
                            e.vx = 0.35 if p.x < e.x else -0.35
        for item in self.items:
            if not item.alive: continue
            item.vy = min(item.vy + GRAVITY * dt * 0.5, MAX_FALL)
            new_ix = item.x + item.vx
            new_iy = item.y + item.vy

            if item.type == 'fireball':
                new_iy2, i_ground, _ = self._resolve_y(item, new_iy, 0.4)
                item.y = new_iy2
                item.x += item.vx
                if i_ground:
                    item.vy   = JUMP_VX * 0.3
                    item.bounces += 1
                if item.bounces > 4 or item.x < -1 or item.x > self.level.width + 1:
                    item.alive = False
                # Hit enemy
                for e in self.enemies:
                    if e.alive and abs(e.x - item.x) < 1.0 and abs(e.y - item.y) < 1.5:
                        e.alive = False
                        item.alive = False
                        p.score += 200
                continue

            item.x = self._resolve_x(item, new_ix, 0.8)
            new_iy2, _, _ = self._resolve_y(item, new_iy, 0.8)
            item.y = new_iy2

            # Off screen → remove
            if item.y > self.level.height + 3 or item.x < -2:
                item.alive = False
                continue

            # Player picks up item
            if (abs(item.x - p.x) < 1.2 and abs(item.y - p.y) < 1.5 and
                    item.type in ('mushroom', 'flower')):
                if item.type == 'mushroom' and p.power < 1:
                    p.power = 1
                    p.score += 1000
                elif item.type == 'flower' and p.power < 2:
                    p.power = 2
                    p.score += 1000
                item.alive = False

        # Cull dead enemies and items
        self.enemies = [e for e in self.enemies if e.alive or e.dead_timer > 0]
        self.items   = [i for i in self.items   if i.alive]
        for part in self.particles:
            part['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]
        # Find flagpole ^ position
        for ry, row in enumerate(self.level.rows):
            for rx, ch in enumerate(row):
                if ch in ('^', 'F') and abs(p.x - rx) < 1.5 and p.alive:
                    p.flag_slide = 40
                    p.score += 1000
                    return None

        return None
def draw_game(scr, H, W, game: Game, tick: int):
    P   = curses.color_pair
    scr.erase()

    p   = game.player
    lv  = game.level

    GAME_ROW_START = 3
    GAME_ROWS = H - 7
    cam_x = game.cam_x
    tiles_w = (W - 2) // TILE_W  # visible tiles wide
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))
    # HUD background bar
    _p(scr, H, W, 1, 1, ' '*(W-2), P(5))
    # Lives: hearts
    heart_str = '♥' * max(0, p.lives)
    lives_label = f' ♥×{p.lives} '
    _p(scr, H, W, 1, 2, lives_label, P(2)|curses.A_BOLD)
    # World/level name
    w_str = f'WORLD {lv.world[0]}-{lv.world[1]}  {lv.name}'
    _p(scr, H, W, 1, (W - len(w_str)) // 2, w_str, P(5)|curses.A_BOLD)
    # Coins
    coins_str = f'◆×{p.coins:02d}'
    _p(scr, H, W, 1, W//2 + 16, coins_str, P(4)|curses.A_BOLD)
    # Score
    sc_str = f'★{p.score:07d}'
    _p(scr, H, W, 1, W//2 + 24, sc_str, P(6)|curses.A_BOLD)
    # Timer — flash red when low
    time_val = int(game.timer)
    time_str  = f'T {time_val:03d}'
    time_attr = P(2)|curses.A_BOLD if game.timer < 60 else P(4)|curses.A_BOLD
    _p(scr, H, W, 1, W - 12, time_str, time_attr)
    _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    # Draw sky background with subtle horizon gradient
    for r in range(GAME_ROW_START, H-4):
        _p(scr, H, W, r, 1, ' '*(W-2), P(8)|curses.A_DIM)

    for vis_tx in range(tiles_w + 2):
        world_tx = int(cam_x) + vis_tx
        scr_col  = 1 + (world_tx - int(cam_x)) * TILE_W

        for ty in range(lv.height):
            t    = game.tile(world_tx, ty)
            if t == ' ': continue

            scr_row = GAME_ROW_START + ty
            if scr_row < GAME_ROW_START or scr_row >= H - 4: continue

            td = TILE_DISPLAY.get(t, ('  ', 5, False))
            chars, cp, bold = td
            attr = P(cp) | (curses.A_BOLD if bold else 0)

            if t == '?':
                # Question block: bright gold with pulsing shimmer
                if (tick // 10) % 2 == 0:
                    chars = '?!'
                    attr  = P(4) | curses.A_BOLD | curses.A_REVERSE
                else:
                    chars = '[?'
                    attr  = P(4) | curses.A_BOLD
            elif t == 'X':
                # Used/empty block: faded brick look
                chars = '▒▒'; attr = P(5) | curses.A_DIM
            elif t == 'c':
                # Coin: spinning animation between diamond and circle
                if (tick // 8) % 2 == 0:
                    chars = '◆·'; attr = P(4) | curses.A_BOLD
                else:
                    chars = '○·'; attr = P(4) | curses.A_BOLD
            elif t == '^':
                # Flagpole tip: star flag
                chars = '★ '; attr = P(4) | curses.A_BOLD
            elif t == 'F':
                # Flagpole pole: solid vertical bar
                chars = '│ '; attr = P(3) | curses.A_BOLD
            elif t == '#':
                # Brick block: cross-hatch pattern, flashes when hit nearby
                chars = '▦▦'; attr = P(5) | curses.A_BOLD
            elif t == '=':
                # Solid ground: double-line heavy tiles
                chars = '▓▓'; attr = P(5) | curses.A_BOLD
            elif t == '|':
                # Pipe wall: green double-bar
                chars = '▐▌'; attr = P(3) | curses.A_BOLD
            elif t == 'P':
                # Pipe top: pipe opening
                chars = '╒╕'; attr = P(3) | curses.A_BOLD

            _p(scr, H, W, scr_row, scr_col, chars, attr)
    for e in game.enemies:
        if not e.alive: continue
        ex_scr = 1 + int((e.x - cam_x) * TILE_W)
        ey_scr = GAME_ROW_START + int(e.y - e.height + 1)
        if 1 <= ex_scr < W - 3 and GAME_ROW_START <= ey_scr < H - 4:
            sp = e.sprite(tick)
            cp = P(2)|curses.A_BOLD if e.type == 'g' else (P(4)|curses.A_BOLD if e.type == 't' else P(6)|curses.A_BOLD)
            _p(scr, H, W, ey_scr, ex_scr, sp[0], cp)
    for item in game.items:
        if not item.alive: continue
        ix_scr = 1 + int((item.x - cam_x) * TILE_W)
        iy_scr = GAME_ROW_START + int(item.y)
        if 1 <= ix_scr < W - 3 and GAME_ROW_START <= iy_scr < H - 4:
            sp = item.sprite(tick)
            if item.type == 'coin':
                cp = P(4)|curses.A_BOLD
            elif item.type == 'mushroom':
                cp = P(2)|curses.A_BOLD   # red mushroom
            elif item.type == 'flower':
                cp = P(6)|curses.A_BOLD   # fire flower — magenta/yellow
            elif item.type == 'fireball':
                cp = P(4)|curses.A_BOLD   # bright fireball
            else:
                cp = P(5)|curses.A_BOLD
            _p(scr, H, W, iy_scr, ix_scr, sp[0], cp)
    for part in game.particles:
        px_scr = 1 + int((part['x'] / TILE_W - cam_x) * TILE_W)
        py_scr = GAME_ROW_START + part['y']
        if 1 <= px_scr < W - 2 and GAME_ROW_START <= py_scr < H - 4:
            if part['type'] == 'coin':
                # Coin pop: diamond rises then fades
                ch = '◆' if part['life'] > 10 else '○' if part['life'] > 5 else '·'
                _p(scr, H, W, int(py_scr), px_scr, ch, P(4)|curses.A_BOLD)
            elif part['type'] == 'break':
                # Brick debris: chunky bits scatter
                if part['life'] > 8:
                    ch = '▦'
                elif part['life'] > 4:
                    ch = '▒'
                else:
                    ch = '·'
                _p(scr, H, W, int(py_scr), px_scr, ch+ch, P(5)|curses.A_BOLD)
            elif part['type'] == 'stomp':
                # Stomp star burst
                ch = '✸' if part['life'] > 7 else '✦' if part['life'] > 3 else '·'
                _p(scr, H, W, int(py_scr), px_scr, ch, P(4)|curses.A_BOLD)
    px_scr = 1 + int((p.x - cam_x) * TILE_W)
    py_scr = GAME_ROW_START + int(p.y) - p.height + 1

    if p.alive and (p.invuln == 0 or (tick // 3) % 2 == 0):
        sp = p.sprite(tick)
        if p.power == 2:
            pcp = P(6)|curses.A_BOLD   # Fire Claudio — bright yellow/fire
        elif p.power == 1:
            pcp = P(4)|curses.A_BOLD   # Super Claudio — gold
        else:
            pcp = P(1)|curses.A_BOLD   # Small Claudio — cyan/white
        for si, srow in enumerate(sp):
            row = py_scr + si
            if GAME_ROW_START <= row < H - 4:
                _p(scr, H, W, row, px_scr, srow, pcp)
    elif not p.alive:
        # Death animation — player spins/tumbles up then falls
        spin = ['(×)', '(+)', '(÷)', '(·)']
        frame_ch = spin[(tick // 4) % len(spin)]
        if GAME_ROW_START <= py_scr < H - 4:
            _p(scr, H, W, py_scr, px_scr, frame_ch, P(2)|curses.A_BOLD)
    _p(scr, H, W, H-4, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    ctrl = '← → / A D : Move    W / ↑ / SPC : Jump    J : Shoot    ESC : Pause'
    _p(scr, H, W, H-3, 2, ctrl, P(5)|curses.A_DIM)
    if p.power == 2:
        power_icon = '[◈] FIRE CLAUDIO'
        power_msg  = f'{power_icon}  — ✦ shoot fireballs with J ✦'
        _p(scr, H, W, H-2, 2, power_msg, P(6)|curses.A_BOLD)
    elif p.power == 1:
        power_icon = '(◉) SUPER CLAUDIO'
        power_msg  = f'{power_icon}  — ▦ smash bricks with your head ▦'
        _p(scr, H, W, H-2, 2, power_msg, P(4)|curses.A_BOLD)
    else:
        power_icon = '(◙) CLAUDIO'
        power_msg  = f'{power_icon}  — grab (∩) mushroom to power up!'
        _p(scr, H, W, H-2, 2, power_msg, P(1)|curses.A_DIM)
    scr.refresh()


def draw_title(scr, H, W, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))

    # ── Title art (5 rows, alternating gold / cyan / magenta) ──────────────
    title_colors = [P(4)|curses.A_BOLD, P(1)|curses.A_BOLD, P(6)|curses.A_BOLD,
                    P(4)|curses.A_BOLD, P(3)|curses.A_BOLD]
    for i, line in enumerate(TITLE_ART):
        col = max(1, (W - len(line)) // 2)
        _p(scr, H, W, 2 + i, col, line, title_colors[i % len(title_colors)])

    # ── Decorative separator ────────────────────────────────────────────────
    sep = '·' * (W - 2)
    _p(scr, H, W, 8, 1, sep, P(5)|curses.A_DIM)

    # ── Tagline ─────────────────────────────────────────────────────────────
    tag = '✦  THREE WORLDS  ·  POWER-UPS  ·  SAVE ANTHROPIA  ✦'
    _p(scr, H, W, 9, max(1, (W - len(tag)) // 2), tag, P(6)|curses.A_BOLD)

    # ── Animated demo scene ─────────────────────────────────────────────────
    demo_y = H // 2 + 1
    scene_w = W - 4

    # Sky / clouds
    cloud_x = (tick // 3) % scene_w
    _p(scr, H, W, demo_y - 3, 2 + cloud_x % (scene_w - 10), '☁  ☁', P(1)|curses.A_DIM)
    _p(scr, H, W, demo_y - 3, 2 + (cloud_x + scene_w // 2) % (scene_w - 10), '☁', P(5)|curses.A_DIM)

    # ? blocks and brick as scenery
    block_row = demo_y - 1
    for bx in range(6, W - 6, 12):
        if (tick // 20) % 2 == 0:
            _p(scr, H, W, block_row, bx, '[?', P(4)|curses.A_BOLD)
        else:
            _p(scr, H, W, block_row, bx, '▦▦', P(5)|curses.A_BOLD)

    # Ground
    ground = '▓▓' * ((W - 2) // 2)
    _p(scr, H, W, demo_y + 1, 1, ground[:W-2], P(5)|curses.A_BOLD)
    _p(scr, H, W, demo_y + 2, 1, '▒▒' * ((W - 2) // 2), P(5)|curses.A_DIM)

    # Animated Claudio running right
    px = 4 + (tick * 2) % (scene_w - 10)
    walk_f = (tick // 5) % 2
    claudio_sp = '◄◙►' if walk_f == 0 else '◄◙►'
    _p(scr, H, W, demo_y, px, claudio_sp, P(1)|curses.A_BOLD)

    # Animated Glitchy running left (bounces)
    ex = W - 8 - (tick * 2) % (scene_w - 10)
    glitch_sp = '▽_▽' if (tick // 6) % 2 == 0 else '×_×'
    _p(scr, H, W, demo_y, max(4, ex), glitch_sp, P(2)|curses.A_BOLD)

    # Coin sparkle above ground
    coin_x = 14 + (tick // 4) % (scene_w - 20)
    coin_ch = '◆' if (tick // 8) % 2 == 0 else '○'
    _p(scr, H, W, demo_y - 2, coin_x, coin_ch, P(4)|curses.A_BOLD)

    # ── Flagpole at right edge ───────────────────────────────────────────────
    fp_x = W - 8
    _p(scr, H, W, demo_y - 3, fp_x, '★', P(4)|curses.A_BOLD)
    for fr in range(demo_y - 2, demo_y + 1):
        _p(scr, H, W, fr, fp_x, '│', P(3)|curses.A_BOLD)

    # ── Blinking prompt ─────────────────────────────────────────────────────
    _p(scr, H, W, H-4, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    if (tick // 18) % 2 == 0:
        msg = '▶  PRESS SPACE TO START  ◀       L  TO LOAD LEVEL'
        _p(scr, H, W, H-3, max(1, (W - len(msg)) // 2), msg, P(4)|curses.A_BOLD)
    else:
        msg = '  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·'
        _p(scr, H, W, H-3, max(1, (W - len(msg)) // 2), msg, P(5)|curses.A_DIM)
    features = '(◙) Small  (◉) Super  (◈) Fire  ·  ▽_▽ Glitchy  ·  ◆ Coins  ·  (∩) Mushroom  ·  ❀ Flower'
    _p(scr, H, W, H-2, max(1, (W - len(features)) // 2), features, P(5)|curses.A_DIM)
    scr.refresh()


def draw_how_to_play(scr, H, W, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))
    # Header
    _p(scr, H, W, 1, 1, ' '*(W-2), P(4))
    hdr = '  ✦  H O W   T O   P L A Y  ✦  '
    _p(scr, H, W, 1, max(1, (W - len(hdr)) // 2), hdr, P(4)|curses.A_BOLD)
    _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

    lines = [
        ('── GOAL ─────────────────────────────────────────────────────', P(4)|curses.A_BOLD),
        ('', None),
        ('  Reach the ★ flagpole at the end of each world.', P(5)),
        ('  Stomp enemies from above by landing on their heads.', P(5)),
        ('  Hit [? blocks from below to reveal coins and power-ups.', P(5)),
        ('', None),
        ('── CONTROLS ──────────────────────────────────────────────────', P(4)|curses.A_BOLD),
        ('', None),
        ('  A / ←          Move left',                    P(6)|curses.A_BOLD),
        ('  D / →          Move right',                   P(6)|curses.A_BOLD),
        ('  W / ↑ / SPACE  Jump  (hold for height)',      P(6)|curses.A_BOLD),
        ('  J / F          Run (hold) / Shoot fireballs', P(6)|curses.A_BOLD),
        ('  ESC            Pause / Resume',               P(5)|curses.A_DIM),
        ('', None),
        ('── POWER-UPS ─────────────────────────────────────────────────', P(4)|curses.A_BOLD),
        ('', None),
        ('  (◙)  Small Claudio    — stomp only, avoid enemies',         P(1)|curses.A_BOLD),
        ('  (∩)  Context Mushroom → (◉) Super Claudio  (smash ▦ bricks)', P(2)|curses.A_BOLD),
        ('  ❀    Prompt Flower   → (◈) Fire Claudio   (shoot ✦ fireballs)', P(6)|curses.A_BOLD),
        ('', None),
        ('── ENEMIES ───────────────────────────────────────────────────', P(4)|curses.A_BOLD),
        ('', None),
        ('  ▽_▽  Glitchy     — stomp to defeat, worth 100 pts',        P(2)|curses.A_BOLD),
        ('  Ö_Ö  Tokenoopa   — stomp → [■] shell, kick to clear foes', P(4)|curses.A_BOLD),
        ('  ◁●▷  Hallucigator— flying! dodge or shoot with fireballs',  P(6)|curses.A_BOLD),
    ]

    for i, (text, attr) in enumerate(lines):
        y = 4 + i
        if y >= H - 4: break
        if attr is None:
            _p(scr, H, W, y, 2, '', P(5))
        else:
            _p(scr, H, W, y, 2, text, attr)

    _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    if (tick // 18) % 2 == 0:
        msg = '▶  PRESS SPACE — Let\'s-a go!  ◀'
        _p(scr, H, W, H-2, max(1, (W - len(msg)) // 2), msg, P(3)|curses.A_BOLD)
    scr.refresh()


def draw_level_clear(scr, H, W, game: Game, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))

    lv = game.level
    p  = game.player

    # ── Star field animation ────────────────────────────────────────────────
    stars = ['★', '✦', '✸', '·']
    for sx in range(3, W - 3, 7):
        sy = 2 + (sx * 3 + tick // 4) % (H - 6)
        _p(scr, H, W, sy, sx, stars[(sx + tick // 8) % len(stars)], P(4)|curses.A_DIM)

    # ── "CLEAR!" ASCII banner ───────────────────────────────────────────────
    banner_row = 3
    banner_colors = [P(4)|curses.A_BOLD, P(6)|curses.A_BOLD, P(3)|curses.A_BOLD,
                     P(1)|curses.A_BOLD, P(4)|curses.A_BOLD]
    for i, line in enumerate(LEVEL_CLEAR_ART):
        col = max(1, (W - len(line)) // 2)
        _p(scr, H, W, banner_row + i, col, line, banner_colors[i % len(banner_colors)])

    # ── World complete label ────────────────────────────────────────────────
    mr = banner_row + len(LEVEL_CLEAR_ART) + 2
    world_msg = f'✦  WORLD  {lv.world[0]} - {lv.world[1]}  ·  {lv.name}  ✦'
    _p(scr, H, W, mr, max(1, (W - len(world_msg)) // 2), world_msg, P(6)|curses.A_BOLD)

    # ── Score & time bonus ──────────────────────────────────────────────────
    time_bonus = max(0, int(game.timer)) * 50
    score_msg  = f'SCORE:    {p.score:>9,}'
    bonus_msg  = f'TIME BONUS: {time_bonus:>7,}'
    coins_msg  = f'COINS:    {p.coins:>9}'
    _p(scr, H, W, mr + 2, max(1, (W - len(score_msg) - 4) // 2), f'  {score_msg}  ', P(4)|curses.A_BOLD)
    _p(scr, H, W, mr + 3, max(1, (W - len(bonus_msg) - 4) // 2), f'  {bonus_msg}  ', P(3)|curses.A_BOLD)
    _p(scr, H, W, mr + 4, max(1, (W - len(coins_msg) - 4) // 2), f'  {coins_msg}  ', P(4)|curses.A_BOLD)

    # ── Divider ─────────────────────────────────────────────────────────────
    div = '·' * (W - 6)
    _p(scr, H, W, mr + 5, 3, div, P(5)|curses.A_DIM)

    # ── Blinking next world prompt ──────────────────────────────────────────
    if (tick // 18) % 2 == 0:
        if game.level_idx + 1 < len(LEVELS):
            nxt = LEVELS[game.level_idx + 1]
            msg = f'▶  SPACE  —  Onward to World {nxt["world"][0]}-{nxt["world"][1]}: {nxt["name"]}  ◀'
        else:
            msg = '▶  SPACE  —  YOU WIN!  ◀'
        _p(scr, H, W, mr + 7, max(1, (W - len(msg)) // 2), msg, P(3)|curses.A_BOLD)
    scr.refresh()


def draw_game_over(scr, H, W, score, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))

    # ── Falling debris animation ────────────────────────────────────────────
    debris = ['▦', '▒', '·', '░', '▓']
    for dx in range(2, W - 2, 5):
        dy = (dx * 2 + tick // 2) % (H - 4) + 2
        _p(scr, H, W, dy, dx, debris[(dx + tick // 6) % len(debris)], P(5)|curses.A_DIM)

    # ── Big GAME OVER art ───────────────────────────────────────────────────
    go_row = max(2, H // 2 - len(GAME_OVER_ART) - 2)
    go_colors = [P(2)|curses.A_BOLD, P(2)|curses.A_BOLD, P(2)|curses.A_BOLD,
                 P(2)|curses.A_BOLD, P(2)|curses.A_BOLD]
    for i, line in enumerate(GAME_OVER_ART):
        col = max(1, (W - len(line)) // 2)
        _p(scr, H, W, go_row + i, col, line, go_colors[i])

    # ── Tombstone ───────────────────────────────────────────────────────────
    mr = go_row + len(GAME_OVER_ART) + 2
    tomb = [
        '  ╔═════╗  ',
        '  ║ R·I·P║  ',
        '  ║(×)   ║  ',
        '  ╚═════╝  ',
        '   ▓▓▓▓▓   ',
    ]
    for i, line in enumerate(tomb):
        _p(scr, H, W, mr + i, max(1, (W - len(line)) // 2), line, P(5)|curses.A_BOLD)

    # ── Score ───────────────────────────────────────────────────────────────
    score_msg = f'FINAL SCORE:  {score:,}'
    _p(scr, H, W, mr + len(tomb) + 1, max(1, (W - len(score_msg)) // 2), score_msg, P(4)|curses.A_BOLD)

    # ── Prompt ──────────────────────────────────────────────────────────────
    if (tick // 18) % 2 == 0:
        prompt = '▶  SPACE : Try Again      Q : Quit to Claudcade  ◀'
        _p(scr, H, W, H - 3, max(1, (W - len(prompt)) // 2), prompt, P(3)|curses.A_BOLD)
    scr.refresh()


def draw_win(scr, H, W, score, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))

    # ── Fireworks / confetti animation ──────────────────────────────────────
    fireworks = ['✸', '✦', '★', '◆', '·', '✿']
    fw_colors  = [P(4), P(6), P(3), P(1), P(2), P(4)]
    for i in range(0, W - 4, 9):
        fy = 2 + ((i * 3 + tick // 3) % (H // 2))
        ch = fireworks[(i // 9 + tick // 10) % len(fireworks)]
        cp = fw_colors[(i // 9 + tick // 12) % len(fw_colors)]
        _p(scr, H, W, fy, i + 2, ch, cp|curses.A_BOLD)

    # ── YOU WIN! banner ──────────────────────────────────────────────────────
    win_row = 3
    win_colors = [P(4)|curses.A_BOLD, P(3)|curses.A_BOLD, P(6)|curses.A_BOLD,
                  P(1)|curses.A_BOLD, P(4)|curses.A_BOLD]
    for i, line in enumerate(WIN_ART):
        col = max(1, (W - len(line)) // 2)
        _p(scr, H, W, win_row + i, col, line, win_colors[i % len(win_colors)])

    mr = win_row + len(WIN_ART) + 2

    # ── Saved Anthropia headline ─────────────────────────────────────────────
    headline = '✦ ✦ ✦   YOU SAVED ANTHROPIA!   ✦ ✦ ✦'
    _p(scr, H, W, mr, max(1, (W - len(headline)) // 2), headline, P(4)|curses.A_BOLD)

    # ── Claudio victory pose ────────────────────────────────────────────────
    claudio = [
        r'    \(◈)/    ',
        r'     |◈|     ',
        r'    / ◈ \    ',
    ]
    princess = [
        '♛ ANTHROPIA ♛',
        '  ╔══════╗   ',
        '  ║ ◎‿◎ ║   ',
        '  ╚══════╝   ',
    ]
    pose_row = mr + 2
    for i, line in enumerate(claudio):
        _p(scr, H, W, pose_row + i, max(1, W // 2 - 20), line, P(6)|curses.A_BOLD)
    for i, line in enumerate(princess):
        _p(scr, H, W, pose_row + i, max(1, W // 2 + 4), line, P(3)|curses.A_BOLD)

    # ── Score display ───────────────────────────────────────────────────────
    score_msg = f'FINAL SCORE:  {score:,}'
    _p(scr, H, W, pose_row + 5, max(1, (W - len(score_msg)) // 2), score_msg, P(4)|curses.A_BOLD)

    # ── Flavor text ─────────────────────────────────────────────────────────
    _p(scr, H, W, pose_row + 6, max(1, (W - 40) // 2),
       '"Thank you, Claudio! The prompts are safe!"', P(5)|curses.A_DIM)

    # ── Prompt ──────────────────────────────────────────────────────────────
    if (tick // 18) % 2 == 0:
        prompt = '▶  SPACE : Play Again      Q : Quit  ◀'
        _p(scr, H, W, H - 3, max(1, (W - len(prompt)) // 2), prompt, P(3)|curses.A_BOLD)
    scr.refresh()


PAUSE_CONTROLS = [
    'A / ←          Move left / right',
    'W / ↑ / SPC    Jump',
    'J              Shoot (Fire Claudio)',
    'ESC            Pause / Resume',
    'Q              Quit to Claudcade',
]

def draw_pause(scr, H, W):
    Renderer(scr, H, W).pause_overlay('SUPER CLAUDIO', PAUSE_CONTROLS)
def main(scr):
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()
    try: curses.mousemask(0)
    except curses.error: pass

    state     = TITLE
    game: Game | None = None
    tick      = 0
    nxt       = time.perf_counter()

    def new_game(level_idx=0, lives=3, score=0, coins=0):
        nonlocal game
        game = Game(level_idx, lives, score, coins)

    while True:
        now = time.perf_counter()
        if now < nxt:
            time.sleep(max(0.0, nxt - now - 0.001))
            continue
        nxt += 1/FPS; tick += 1

        H, W = scr.getmaxyx()
        keys = set()
        while True:
            k = scr.getch()
            if k == -1: break
            keys.add(k)

        OK  = any(k in keys for k in (ord(' '), ord('\n'), 10, 13))
        ESC = 27 in keys

        if state == TITLE:
            draw_title(scr, H, W, tick)
            if OK:
                new_game(0)
                state = HOW_TO_PLAY
            elif ord('l') in keys or ord('L') in keys:
                new_game(0)
                state = PLAY

        elif state == HOW_TO_PLAY:
            draw_how_to_play(scr, H, W, tick)
            if OK: state = PLAY

        elif state == PLAY:
            draw_game(scr, H, W, game, tick)
            if ESC: state = PAUSE; continue
            result = game.update(keys, tick)
            if result == LEVEL_CLEAR:
                state = LEVEL_CLEAR
            elif result == GAME_OVER:
                state = GAME_OVER

        elif state == PAUSE:
            draw_game(scr, H, W, game, tick)
            draw_pause(scr, H, W)
            if ord('r') in keys or ord('R') in keys or ESC: state = PLAY
            if ord('q') in keys or ord('Q') in keys: break

        elif state == LEVEL_CLEAR:
            draw_level_clear(scr, H, W, game, tick)
            if OK:
                next_idx = game.level_idx + 1
                if next_idx < len(LEVELS):
                    p = game.player
                    new_game(next_idx, p.lives, p.score, p.coins)
                    state = PLAY
                else:
                    state = WIN

        elif state == GAME_OVER:
            draw_game_over(scr, H, W, game.player.score if game else 0, tick)
            if OK: new_game(0); state = HOW_TO_PLAY
            if ord('q') in keys or ord('Q') in keys: break

        elif state == WIN:
            draw_win(scr, H, W, game.player.score if game else 0, tick)
            if OK: new_game(0); state = TITLE
            if ord('q') in keys: break


def run():
    run_game(main, 'Super Claudio')
