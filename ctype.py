#!/usr/bin/env python3
"""C-TYPE: Space Shooter · ESC to quit"""
from __future__ import annotations

import curses, time, random, math
from claudcade_engine import Engine, Renderer, Scene, setup_colors
from claudcade_engine import draw_how_to_play as _engine_how_to_play
from claudcade_scores import player_label, submit_async
INTRO, PLAY, GAME_OVER, PAUSE, HOW_TO_PLAY = range(5)

CONTROLS = [
    'WASD / Arrows   Move',
    'J / Click       Shoot',
    'Hold J          Charge beam',
    'ESC             Pause / Resume',
    'Q               Quit to Claudcade',
]

def draw_pause(scr, H, W):
    Renderer(scr, H, W).pause_overlay('C-TYPE', CONTROLS)

def draw_how_to_play(scr, H, W, tick):
    _engine_how_to_play(
        scr, H, W, tick,
        goal=[
            'Shoot down every wave of enemies. Survive boss waves every 6 levels.',
            'Earn the highest score.',
        ],
        controls=[
            'WASD / Arrows    Move',
            'J / Click        Shoot',
            'Hold J           Charge beam (release to fire)',
            'B                Bomb (clears the screen)',
            'ESC              Pause',
        ],
        tips=[
            '• Hold J to charge a powerful beam',
            '• Press B to detonate a bomb (2 per life)',
            '• Mini-boss every wave 3, 9, 15',
            '• Boss every 6 waves',
        ],
    )
FPS        = 30
AT         = 3          # arena top row
P_SPD      = 2.0        # player speed (rows/cols per tick)
PB_SPD     = 5.0        # player bullet speed
EB_SPD     = 1.4        # enemy bullet speed
SHOOT_CD   = 7
CHARGE_MAX = 50
LIVES      = 3
INVULN     = 90         # invincibility frames after hit
PSW, PSH   = 7, 3       # player sprite dims
TITLE_ART = [
    r" ██████╗      ████████╗██╗   ██╗██████╗ ███████╗",
    r"██╔════╝         ██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝",
    r"██║      ─────   ██║    ╚████╔╝ ██████╔╝█████╗  ",
    r"██║               ██║    ╚██╔╝  ██╔═══╝ ██╔══╝  ",
    r"╚██████╗          ██║     ██║   ██║     ███████╗",
    r" ╚═════╝          ╚═╝     ╚═╝   ╚═╝     ╚══════╝",
]

# ── Player ship sprites ──────────────────────────────────────────────────────
# Each power level is 3 rows × 7 chars. Left edge is tail, right is nose/gun.
# The ship faces RIGHT: thrust exhaust ≡ on left, needle ▶ on right.
PSHIPS = [
    # Power 0 — basic fighter
    [
        ' ╱‾‾╲  ',
        '╞══▷  ▶',
        ' ╲__╱  ',
    ],
    # Power 1 — upgraded, twin-barrel
    [
        '▗╱═══╲▖',
        '╠══▶═▷▶',
        '▝╲═══╱▘',
    ],
    # Power 2 — heavy assault, triple barrel
    [
        '◢█╱═══╲',
        '◈══▶▶▷▶',
        '◣█╲═══╱',
    ],
]

def get_ship(power, charged):
    sp = PSHIPS[min(power, len(PSHIPS)-1)]
    if charged:
        # Charging glow: replace leading char with ◉ and add ★ to tip
        return ['◉' + s[1:] for s in sp]
    return sp

# ── Enemy sprites ────────────────────────────────────────────────────────────
# Each enemy type has 1–2 rows. They face LEFT (approaching the player).
ESP = {
    # Grunt: fast, dumb, single-line dart
    'grunt':  ['◁━━◆━━▷'],
    # Sine: weaving interceptor — wide swept wings
    'sine':   ['◁≋◆≋▷'],
    # Diver: homing drone — tall body with sensor pod
    'diver':  ['▽◈▽',
               '╞○╡'],
    # Heavy: armored gunship — wide, bracketed hull
    'heavy':  ['◀██▓▓██▶',
               '◁┤░░░░┝▷'],
    # Turret: slow, stationary gun platform — boxy with antenna
    'turret': [' ╻╻╻ ',
               '▐███▌',
               '◁═══▷'],
}

# ── Boss frames ───────────────────────────────────────────────────────────────
# Phase 0 = full HP, Phase 1 = <50% HP (rage mode, faster fire rate).
BOSS_FRAMES = [
    [   # frame A — calm
        '  ╔══◆══╗  ',
        ' ╔╝▓▓█▓▓╚╗ ',
        '◀╣░▒▓★▓▒░╠▶',
        ' ╚╗▓▓█▓▓╔╝ ',
        '  ╚══◆══╝  ',
    ],
    [   # frame B — engines firing
        '  ╔══◈══╗  ',
        ' ╔╝▓▓█▓▓╚╗ ',
        '◀╣▒▓▓●▓▓▒╠▶',
        ' ╚╗▓▓█▓▓╔╝ ',
        '  ╚══◈══╝  ',
    ],
    [   # frame C — phase 2 (rage) — used when phase==1
        '  ╔══✦══╗  ',
        ' ╔╝░▒█▒░╚╗ ',
        '◀╣▓▒▒✦▒▒▓╠▶',
        ' ╚╗░▒█▒░╔╝ ',
        '  ╚══✦══╝  ',
    ],
    [   # frame D — phase 2 firing
        '  ╔══★══╗  ',
        ' ╔╝▒▓█▓▒╚╗ ',
        '◀╣░▓▒★▒▓░╠▶',
        ' ╚╗▒▓█▓▒╔╝ ',
        '  ╚══★══╝  ',
    ],
]

class Explosion:
    # Five-frame decay (peak → settling → mid → fade → ghost) reads as a
    # smoother burst than the previous four; the second frame eases the
    # transition between the bright core and the sparser mid-stage.
    FRAMES = [
        ['▓█▓', '█◉█', '▓█▓'],
        ['▓◈▓', '◈★◈', '▓◈▓'],
        ['▒◈▒', '◈✦◈', '▒◈▒'],
        ['░·░', '·✧·', '░·░'],
        ['   ', ' ∙ ', '   '],
    ]
    def __init__(self, x, y):
        self.x=x; self.y=y; self.f=0; self.t=0
    @property
    def done(self): return self.f >= len(self.FRAMES)
    def tick(self):
        self.t += 1
        if self.t >= 3: self.t=0; self.f+=1
class Powerup:
    TYPES = [('P','power',4),('S','speed',3),('♥','life',2)]
    def __init__(self, x, y):
        w = random.choices(self.TYPES, weights=[4,3,2])[0]
        self.x=float(x); self.y=float(y); self.char=w[0]; self.kind=w[1]
    def update(self): self.x -= 0.8
    @property
    def gone(self): return self.x < 0
BOMBS_PER_LIFE = 2

class Player:
    def __init__(self, H, W):
        self.GR = H-5
        self.W  = W
        self.x  = float(8)
        self.y  = float(self.GR - AT) // 2 + AT
        self.lives   = LIVES
        self.power   = 0
        self.speed   = P_SPD
        self.invuln  = 0
        self.shoot_cd= 0
        self.charge  = 0
        self.beam    = None   # active beam: {'len', 'y', 'ttl'}
        self.shield  = 0
        self.bombs   = BOMBS_PER_LIFE
        self.bomb_cd = 0      # debounce for B key

    def sprites(self): return get_ship(self.power, self.charge >= CHARGE_MAX)

    def get_hit(self):
        if self.invuln > 0 or self.shield > 0:
            if self.shield > 0: self.shield -= 1
            return False
        self.lives = max(0, self.lives - 1); self.invuln = INVULN
        self.power = max(0, min(2, self.power - 1))
        # On respawn, refill bombs to BOMBS_PER_LIFE
        if self.lives > 0:
            self.bombs = BOMBS_PER_LIFE
        return True

    def update(self, keys, game):
        if self.invuln > 0: self.invuln -= 1
        if self.shoot_cd > 0: self.shoot_cd -= 1
        if self.bomb_cd > 0: self.bomb_cd -= 1

        # Bomb: clears every enemy + bullets on screen. 1 use per press.
        if (ord('b') in keys or ord('B') in keys) and self.bombs > 0 and self.bomb_cd == 0:
            self.bombs -= 1
            self.bomb_cd = 12
            game.detonate_bomb()

        spd = self.speed
        if ord('w') in keys or curses.KEY_UP    in keys: self.y -= spd
        if ord('s') in keys or curses.KEY_DOWN  in keys: self.y += spd
        if ord('a') in keys or curses.KEY_LEFT  in keys: self.x -= spd
        if ord('d') in keys or curses.KEY_RIGHT in keys: self.x += spd

        GR = self.GR
        self.x = max(2.0,   min(self.W // 3, self.x))
        self.y = max(float(AT+1), min(float(GR - PSH - 1), self.y))

        fire_key = ord('j') in keys or ord('f') in keys
        if fire_key:
            self.charge = min(self.charge+1, CHARGE_MAX)
            # Rapid-fire while holding; stops when charge fills (switches to beam mode)
            if self.charge < CHARGE_MAX and self.shoot_cd == 0:
                game.pbullets.append({'x': self.x+PSW, 'y': self.y+1, 'vx': PB_SPD, 'vy': 0})
                if self.power >= 1:
                    game.pbullets.append({'x': self.x+PSW, 'y': self.y,   'vx': PB_SPD, 'vy':-0.3})
                    game.pbullets.append({'x': self.x+PSW, 'y': self.y+2, 'vx': PB_SPD, 'vy': 0.3})
                self.shoot_cd = SHOOT_CD
        else:
            if self.charge >= 15:
                # Threshold of 15 — easy to trigger, avoids hair-trigger taps
                self.beam = {'x': self.x+PSW, 'y': int(self.y), 'ttl': 18,
                             'rows': 3, 'power': self.charge}
                beam_len = max(1, self.W - int(self.x) - PSW)
                game.pbullets.append({'x': self.x+PSW, 'y': self.y+1,
                                       'vx': PB_SPD*2, 'vy': 0, 'beam': True,
                                       'len': beam_len})
            self.charge = 0
class Enemy:
    def __init__(self, x, y, etype, speed=1.0):
        self.x  = float(x); self.y_start = float(y); self.y = float(y)
        self.etype = etype
        self.hp = {'grunt':1,'sine':1,'diver':2,'heavy':4,'turret':3}[etype]
        self.age = 0
        self.speed = speed
        self.shoot_cd = random.randint(40, 120)
        self.alive = True
        rows = ESP[etype]; self.h = len(rows); self.w = len(rows[0])

    def sprites(self): return ESP[self.etype]

    def take_hit(self, dmg=1):
        self.hp -= dmg
        if self.hp <= 0: self.alive = False; return True
        return False

    def update(self, player, game):
        if not self.alive: return
        self.age += 1
        spd = self.speed

        if self.etype == 'grunt':
            self.x -= spd
        elif self.etype == 'sine':
            self.x -= spd * 0.75
            self.y = self.y_start + math.sin(self.age * 0.12) * 6
        elif self.etype == 'diver':
            self.x -= spd * 0.6
            dy = player.y - self.y
            self.y += max(-0.8, min(0.8, dy * 0.04))
        elif self.etype == 'heavy':
            self.x -= spd * 0.5
        elif self.etype == 'turret':
            self.x -= spd * 0.3

        self.shoot_cd -= 1
        if self.shoot_cd <= 0 and abs(self.x - player.x) < 65:
            self.shoot_cd = random.randint(50, 130)
            dx = player.x - self.x; dy = player.y - self.y
            dist = max(1, math.hypot(dx, dy))
            vx = EB_SPD * dx / dist; vy = EB_SPD * dy / dist
            game.ebullets.append({'x': self.x-1, 'y': self.y+self.h//2,
                                   'vx': vx, 'vy': vy})
class Boss:
    def __init__(self, H, W):
        self.x   = float(W - 14)
        self.y   = float(H//2 - 2)
        self.hp  = 40; self.max_hp = 40
        self.alive = True; self.age = 0
        self.phase = 0; self.frame = 0; self.ft = 0
        self.shoot_cd = 20; self.H=H; self.W=W; self.h=5; self.w=13

    def sprites(self):
        base = 2 if self.phase == 1 else 0
        return BOSS_FRAMES[base + (self.frame % 2)]

    def take_hit(self, dmg=1):
        self.hp -= dmg
        if self.hp <= 0: self.alive=False; return True
        if self.hp < self.max_hp//2: self.phase=1
        return False

    def update(self, player, game):
        if not self.alive: return
        self.age += 1
        self.ft += 1
        if self.ft >= 12: self.ft=0; self.frame+=1

        self.y = (self.H//2 - 2) + math.sin(self.age * 0.03) * (self.H//6)
        self.y = max(float(AT+1), min(float(self.H-5-self.h), self.y))
        if self.phase == 1:  # phase 2: advance toward center to pressure the player
            self.x = max(float(self.W//2), self.x - 0.3)

        self.shoot_cd -= 1
        if self.shoot_cd <= 0:
            shots = 3 if self.phase==0 else 5
            self.shoot_cd = 28 if self.phase==0 else 18
            cx = self.x; cy = self.y + self.h//2
            for i in range(shots):
                angle = math.pi + (i - shots//2) * 0.25
                vx = EB_SPD * 1.2 * math.cos(angle)
                vy = EB_SPD * 1.2 * math.sin(angle)
                game.ebullets.append({'x':cx,'y':cy,'vx':vx,'vy':vy})
class Game:
    def __init__(self, H, W):
        self.H=H; self.W=W; self.GR=H-5
        self.player    = Player(H, W)
        self.enemies   = []
        self.pbullets  = []
        self.ebullets  = []
        self.explosions= []
        self.powerups  = []
        self.stars     = _make_ctype_stars(H, W)
        self.score     = 0
        self.wave      = 0
        self.wave_cd   = 80   # ticks until first wave
        self.pending   = []   # enemies waiting to spawn: (delay, etype, x, y)
        self.boss      = None
        self.boss_mode = False
        self.msg       = ''; self.msg_t = 0

    def show(self, m, d=90): self.msg=m; self.msg_t=d

    def detonate_bomb(self) -> None:
        """Wipe every enemy + bullet on screen. Each kill triggers an explosion
        and adds half-credit score. Boss takes one tick of damage."""
        for e in self.enemies:
            if e.alive:
                e.alive = False
                self.score += 50
                self.explosions.append(Explosion(int(e.x), int(e.y)))
        self.enemies = []
        # Bomb does heavy damage to a present boss (a quarter of max HP)
        if self.boss and self.boss.alive:
            self.boss.hp = max(0, self.boss.hp - max(1, self.boss.max_hp // 4))
        self.ebullets.clear()
        self.show('  ★ BOMB! ★  ', 25)

    def _spawn_wave(self):
        self.wave += 1
        self.show(f'  WAVE {self.wave}  ', 50)
        W=self.W; H=self.H; GR=self.GR
        cx = W - 2
        arena_h = GR - AT - 2
        center  = AT + 1 + arena_h // 2

        if self.wave % 6 == 0:
            # Boss wave
            self.boss = Boss(H, W)
            self.boss_mode = True
            self.show('  ★ BOSS INCOMING ★  ', 70)
            return

        if self.wave in (3, 9, 15, 21):
            # Mini-boss: a single hardened heavy with extra HP and a turret pair
            self.show('  ◆ MINI-BOSS ◆  ', 60)
            spd_mul = 1.0 + self.wave * 0.04
            mb_y = float(center)
            self.pending.append((0, 'heavy', cx, mb_y, spd_mul * 0.6))
            # Plus 2 turrets above and below for crossfire
            self.pending.append((20, 'turret', cx, float(AT + 2),       spd_mul * 0.5))
            self.pending.append((20, 'turret', cx, float(GR - 3),       spd_mul * 0.5))
            return

        pattern = (self.wave-1) % 5
        count   = 3 + self.wave // 2
        spd_mul = 1.0 + self.wave * 0.04

        if pattern == 0:   # vertical spread, straight fliers
            ys = [AT+1 + arena_h*i//(count+1) for i in range(1, count+1)]
            for i,y in enumerate(ys):
                self.pending.append((i*20, 'grunt', cx, float(y), spd_mul))
        elif pattern == 1:  # sine wave
            for i in range(count):
                y = center + (i-count//2)*3
                self.pending.append((i*15, 'sine', cx, float(y), spd_mul))
        elif pattern == 2:  # divers
            for i in range(min(count, 5)):
                y = AT+2 + arena_h*i//(max(count,1)+1)
                self.pending.append((i*12, 'diver', cx, float(y), spd_mul))
        elif pattern == 3:  # mixed grunt + 1 heavy
            for i in range(count-1):
                y = float(random.randint(AT+2, GR-3))
                self.pending.append((i*18, 'grunt', cx, y, spd_mul))
            self.pending.append((count*18, 'heavy', cx, float(center), spd_mul*0.8))
        elif pattern == 4:  # turrets + grunts
            for i in range(2):
                y = AT+2 + arena_h*(i+1)//3
                self.pending.append((i*25, 'turret', cx, float(y), spd_mul*0.5))
            for i in range(count-2):
                y = float(random.randint(AT+2, GR-3))
                self.pending.append((i*12+10, 'grunt', cx, y, spd_mul))

    def _check_hits(self):
        p = self.player
        W = self.W
        for b in list(self.pbullets):
            if b.get('dead'): continue
            beam = b.get('beam', False)
            dmg  = max(1, int(b.get('len', 1) // 15)) if beam else 1

            targets = ([self.boss] if self.boss and self.boss.alive else []) + self.enemies
            for e in targets:
                ex = e.x; ey = e.y; ew = e.w; eh = e.h
                if beam:
                    hit = (ex <= W and abs(b['y'] - (ey + eh//2)) <= eh//2 + 1)
                else:
                    hit = (ex - 2 <= b['x'] <= ex + ew + 1 and
                           ey - 1 <= b['y'] <= ey + eh + 1)
                if hit:
                    if not beam: b['dead'] = True
                    killed = e.take_hit(dmg if beam else 1)
                    if killed:
                        self.explosions.append(Explosion(int(e.x), int(e.y+eh//2)))
                        sc = {'grunt':100,'sine':150,'diver':200,'heavy':400,'turret':300}
                        if isinstance(e, Boss):
                            self.score += 5000; self.boss_mode=False; self.boss=None
                            self.show('  BOSS DESTROYED!  ', 90)
                        else:
                            self.score += sc.get(e.etype,100)
                            if random.random() < 0.12:
                                self.powerups.append(Powerup(e.x, e.y))
                    if not beam: break

        if p.invuln == 0:
            for b in list(self.ebullets):
                if b.get('dead'): continue
                if (abs(b['x'] - p.x - PSW//2) < 4 and
                    abs(b['y'] - p.y - PSH//2) < 3):
                    b['dead'] = True
                    if p.get_hit(): self.explosions.append(Explosion(int(p.x+2), int(p.y+1)))
            if self.boss and self.boss.alive:
                if (self.boss.x <= p.x+PSW and p.x <= self.boss.x+self.boss.w and
                    self.boss.y <= p.y+PSH and p.y <= self.boss.y+self.boss.h):
                    p.get_hit()

        for pu in list(self.powerups):
            if abs(pu.x - p.x - PSW//2) < 5 and abs(pu.y - p.y - 1) < 3:
                if pu.kind == 'power':  p.power = min(2, p.power+1)
                elif pu.kind == 'speed': p.speed = min(3.5, p.speed+0.5)
                elif pu.kind == 'life':  p.lives += 1
                self.score += 500
                pu.x = -1  # mark collected

    def update(self, keys, mshoot):
        p = self.player
        effective_keys = keys | {ord('j')} if mshoot else keys
        p.update(effective_keys, self)

        for s in self.stars:
            s['x'] -= s['spd']
            if s['x'] < 1: s['x'] = float(self.W-2)

        new_pending = []
        for item in self.pending:
            delay,et,ex,ey,spd = item
            if delay <= 0:
                self.enemies.append(Enemy(ex,ey,et,spd))
            else:
                new_pending.append((delay-1,et,ex,ey,spd))
        self.pending = new_pending

        active = [e for e in self.enemies if e.alive]
        if not self.boss_mode:
            self.wave_cd -= 1
            if self.wave_cd <= 0 and len(active)==0 and len(self.pending)==0:
                self.wave_cd = 120
                self._spawn_wave()

        for e in self.enemies: e.update(p, self)
        if self.boss: self.boss.update(p, self)
        for b in self.pbullets: b['x'] += b['vx']; b['y'] += b.get('vy',0)
        for b in self.ebullets: b['x'] += b['vx']; b['y'] += b.get('vy',0)
        for ex in self.explosions: ex.tick()
        for pu in self.powerups: pu.update()

        self._check_hits()

        if p.beam:
            p.beam['ttl'] -= 1
            if p.beam['ttl'] <= 0: p.beam = None

        self.pbullets  = [b for b in self.pbullets  if not b.get('dead') and b['x'] < self.W]
        self.ebullets  = [b for b in self.ebullets  if not b.get('dead')
                          and 0 < b['x'] < self.W and AT < b['y'] < self.GR]
        self.enemies   = [e for e in self.enemies   if e.alive and e.x > -10]
        self.explosions= [ex for ex in self.explosions if not ex.done]
        self.powerups  = [pu for pu in self.powerups  if not pu.gone]
        if self.msg_t > 0: self.msg_t -= 1
def _make_ctype_stars(H, W, count=100):
    """Parallax starfield with varied depth glyphs for C-TYPE.

    Includes a few slow far-background landmarks (planets, moons) that drift
    almost imperceptibly — gives a strong sense of depth without crowding.
    """
    result = []
    # (speed, char, color_pair) tiers — slowest = smallest/dimmest
    tiers = [
        (0.2, '∙', 5),   # far: tiny dot,  white dim
        (0.4, '·', 5),   # mid-far
        (0.7, '·', 1),   # mid: cyan
        (1.2, '+', 1),   # near: bright cyan
        (1.8, '✦', 4),   # very near: gold sparkle
        (2.4, '★', 4),   # closest: bright gold star
    ]
    weights = [30, 25, 18, 12, 9, 6]
    for _ in range(count):
        tier = random.choices(tiers, weights=weights)[0]
        spd, ch, cp = tier
        result.append({
            'x':   float(random.randint(1, max(1, W - 2))),
            'y':   float(random.randint(1, max(1, H - 5))),
            'spd': spd,
            'ch':  ch,
            'cp':  cp,
        })
    # Deep-background landmarks: rare, very slow, larger glyphs
    deep_glyphs = ['O', 'o', '°', '◯']
    for _ in range(3):
        result.append({
            'x':   float(random.randint(1, max(1, W - 2))),
            'y':   float(random.randint(1, max(1, H - 5))),
            'spd': 0.06,
            'ch':  random.choice(deep_glyphs),
            'cp':  random.choice([6, 5, 8]),  # magenta / white / blue
        })
    return result

def _p(scr, H, W, r, c, s, a=0):
    try:
        if 0 <= r < H-1 and 0 <= c < W: scr.addstr(r, c, s[:W-c], a)
    except curses.error: pass

def draw_intro(scr, H, W, tick):
    P = curses.color_pair; scr.erase()
    p = lambda r,c,s,a=0: _p(scr,H,W,r,c,s,a)

    # ── Outer border ──────────────────────────────────────────────────────────
    p(0,   0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    p(H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        p(r, 0, '║', P(5)); p(r, W-1, '║', P(5))

    # ── Parallax starfield ────────────────────────────────────────────────────
    star_chars = ['∙','·','·','+','✦','★']
    star_colors= [ 5,  5,  1,  1,  4,  4]
    for col in range(2, W-2, 4):
        tier = (col * 7) % len(star_chars)
        r = 2 + (col * 5 + tick // (tier+2)) % max(1, H-6)
        if 2 <= r < H-3:
            p(r, col, star_chars[tier], P(star_colors[tier])|curses.A_DIM)

    # ── Title art ─────────────────────────────────────────────────────────────
    sr = max(1, (H - len(TITLE_ART) - 8) // 2)
    for i, line in enumerate(TITLE_ART):
        color = P(4) if i % 2 == 0 else P(1)
        p(sr+i, max(1,(W-len(line))//2), line, color|curses.A_BOLD)

    # ── Subtitle tagline ──────────────────────────────────────────────────────
    tag = '─── TERMINAL SPACE SHOOTER ───'
    p(sr+len(TITLE_ART)+1, (W-len(tag))//2, tag, P(5)|curses.A_DIM)

    # ── Animated demo ship flying across the screen ───────────────────────────
    ship = PSHIPS[2]   # show max-power ship in intro
    sw   = len(ship[0])
    sy   = sr + len(TITLE_ART) + 3
    sx   = (tick * 2) % max(1, W - sw - 4) + 2
    for i, row in enumerate(ship):
        if 0 <= sy+i < H-1:
            p(sy+i, sx, row, P(1)|curses.A_BOLD)
    # little thruster exhaust behind ship — flickers between chars
    exhaust = ['≡', '≈', '~'][tick % 3]
    if 0 <= sy+1 < H-1 and sx-2 >= 1:
        p(sy+1, sx-2, exhaust, P(4)|curses.A_DIM)

    # ── Blinking start prompt ─────────────────────────────────────────────────
    if (tick // 12) % 2 == 0:
        msg = '◈  PRESS SPACE TO LAUNCH  ◈'
        p(H-4, (W-len(msg))//2, msg, P(4)|curses.A_BOLD)

    # ── Bottom hint bar ───────────────────────────────────────────────────────
    p(H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    hint = 'WASD / ↑↓←→  Move      J / Click  Shoot      Hold J  Charge beam'
    p(H-2, 1, hint.center(W-2)[:W-2], P(5))
    scr.refresh()

def draw_game(scr, game, H, W, tick):
    P = curses.color_pair; scr.erase()
    p = lambda r,c,s,a=0: _p(scr,H,W,r,c,s,a)
    pl = game.player
    GR = game.GR

    # ── Frame borders ─────────────────────────────────────────────────────────
    p(0,   0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    p(2,   0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    for r in range(AT, GR): p(r,0,'║',P(5)); p(r,W-1,'║',P(5))
    p(GR,  0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    p(H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)

    # ── HUD row 1 ─────────────────────────────────────────────────────────────
    p(1, 0, '║', P(5)|curses.A_BOLD); p(1, W-1, '║', P(5)|curses.A_BOLD)
    p(1, 1, '▓▒░', P(5)|curses.A_DIM); p(1, W-4, '░▒▓', P(5)|curses.A_DIM)

    # Game title
    p(1, 5, '◈ C-TYPE ◈', P(4)|curses.A_BOLD)

    # Lives display: ♥ × lives, ♡ × (LIVES - lives)
    lv_s = ('♥ ' * pl.lives + '♡ ' * max(0, LIVES - pl.lives)).rstrip()
    p(1, 18, lv_s, P(2)|curses.A_BOLD)

    # Bombs (B to detonate): ◆ filled, ◇ used
    bomb_s = ('◆ ' * pl.bombs + '◇ ' * max(0, BOMBS_PER_LIFE - pl.bombs)).rstrip()
    p(1, 30, bomb_s, P(4)|curses.A_BOLD)

    # Score centered
    sc_s = f'◆ {game.score:08d} ◆'
    p(1, (W-len(sc_s))//2, sc_s, P(4)|curses.A_BOLD)

    # Power + Wave (right side)
    pwr_pips  = '▰'*(pl.power+1) + '▱'*(2-pl.power)
    wave_s    = f'│ PWR:{pwr_pips} │ WAVE:{game.wave:02d} │'
    if game.boss_mode: wave_s += ' ★BOSS★ │'
    p(1, W-len(wave_s)-4, wave_s, P(3))

    # ── Starfield ─────────────────────────────────────────────────────────────
    for s in game.stars:
        r=int(s['y']); c=int(s['x'])
        if AT<=r<GR and 1<=c<W-1:
            cp = P(s['cp'])
            # fast/bright stars get BOLD; slow/far ones get DIM
            attr = curses.A_BOLD if s['spd'] >= 1.2 else curses.A_DIM
            p(r, c, s['ch'], cp|attr)

    # ── Boss HP bar (replaces the arena top divider when boss is alive) ────────
    if game.boss and game.boss.alive:
        bar_w  = W - 18
        filled = int(bar_w * game.boss.hp / game.boss.max_hp)
        empty  = bar_w - filled
        bar_color = P(2) if game.boss.phase == 0 else P(6)
        p(AT, 1, '┤BOSS HP├', P(2)|curses.A_BOLD)
        p(AT, 10, '█'*filled, bar_color|curses.A_BOLD)
        p(AT, 10+filled, '░'*empty, P(5)|curses.A_DIM)
        hp_pct = f'{100*game.boss.hp//game.boss.max_hp:3d}%'
        p(AT, 10+bar_w+1, hp_pct, bar_color|curses.A_BOLD)

    # ── Power-ups ─────────────────────────────────────────────────────────────
    for pu in game.powerups:
        r=int(pu.y); c=int(pu.x)
        if AT<=r<GR and 1<=c<W-1:
            cp = P(4) if pu.kind=='power' else (P(3) if pu.kind=='speed' else P(2))
            blink = (tick//5)%2==0
            glyph = f'◇{pu.char}◇' if blink else f' {pu.char} '
            p(r, c, glyph, cp|curses.A_BOLD)

    # ── Enemies ───────────────────────────────────────────────────────────────
    for e in game.enemies:
        if not e.alive: continue
        rows = e.sprites()
        er=int(e.y); ec=int(e.x)
        cp_map = {'grunt':P(2), 'sine':P(6), 'diver':P(1), 'heavy':P(3), 'turret':P(4)}
        cp = cp_map.get(e.etype, P(2)) | curses.A_BOLD
        for i,row in enumerate(rows):
            r=er+i
            if AT<=r<GR and ec<W: p(r, max(1,ec), row, cp)

    # ── Boss sprite ───────────────────────────────────────────────────────────
    # Two-tone rendering: hull in the phase color, glowing core in gold/red
    # for visual depth. Core is in the middle row (index 2) at the centre.
    if game.boss and game.boss.alive:
        rows = game.boss.sprites()
        br=int(game.boss.y); bc=int(game.boss.x)
        if game.boss.phase == 0:
            hull_cp = P(2)|curses.A_BOLD
            core_cp = P(4)|curses.A_BOLD     # gold core, calm phase
        else:
            hull_cp = (P(6) if (tick//4)%2==0 else P(2))|curses.A_BOLD
            core_cp = P(4)|curses.A_BOLD|curses.A_REVERSE  # raging core
        for i,row in enumerate(rows):
            r=br+i
            if not (AT<=r<GR and bc<W): continue
            if i == 2 and len(row) >= 7:
                # split into [hull-left | core | hull-right] so the core marker
                # (★/◆/✦/★/●) renders in a different color than the hull
                mid = len(row) // 2
                p(r, max(1,bc),         row[:mid],     hull_cp)
                p(r, max(1,bc)+mid,     row[mid],      core_cp)
                p(r, max(1,bc)+mid+1,   row[mid+1:],   hull_cp)
            else:
                p(r, max(1,bc), row, hull_cp)

    # ── Charge beam (sustained visual while beam TTL active) ─────────────────
    if pl.beam and pl.beam['ttl'] > 0:
        by  = pl.beam['y']
        bx  = int(pl.beam['x'])
        # Core beam: bright yellow double-line; edges: dimmer
        core_cp  = P(4)|curses.A_BOLD
        edge_cp  = P(1)|curses.A_DIM
        for dx in range(0, W - bx - 1):
            cx = bx + dx
            if 1 <= cx < W-1:
                if AT <= by   < GR: p(by,   cx, '═', core_cp)
                if AT <= by-1 < GR: p(by-1, cx, '─', edge_cp)
                if AT <= by+1 < GR: p(by+1, cx, '─', edge_cp)
        # Beam tip / origin burst
        if AT <= by < GR and 1 <= bx < W-1:
            p(by, bx, '◉', P(4)|curses.A_BOLD)

    # ── Player ship ───────────────────────────────────────────────────────────
    blink = pl.invuln > 0 and (tick//3)%2==0
    if not blink:
        rows = pl.sprites()
        pr=int(pl.y); pc=int(pl.x)
        if pl.charge >= CHARGE_MAX:
            cp = P(4)|curses.A_BOLD    # gold when fully charged
        elif pl.charge > CHARGE_MAX // 2:
            cp = P(3)|curses.A_BOLD    # green while mid-charge
        else:
            cp = P(1)|curses.A_BOLD    # cyan normal
        for i,row in enumerate(rows):
            r=pr+i
            if AT<=r<GR: p(r, max(1,pc), row, cp)

    # ── Charge indicator bar (above ship, grows as charge fills) ─────────────
    if pl.charge > 8 and not blink:
        ratio    = pl.charge / CHARGE_MAX
        bar_len  = int((PSW + 2) * ratio)
        bar_str  = '▰' * bar_len
        bar_col  = P(4) if ratio >= 1.0 else (P(3) if ratio > 0.5 else P(1))
        p(int(pl.y)-1, int(pl.x), bar_str, bar_col|curses.A_BOLD)
        if ratio >= 1.0:
            if (tick//5)%2==0:
                p(int(pl.y)-1, int(pl.x)+bar_len, '★', P(4)|curses.A_BOLD)

    # ── Player bullets ────────────────────────────────────────────────────────
    for b in game.pbullets:
        bc=int(b['x']); br=int(b['y'])
        if AT<=br<GR and 1<=bc<W-1:
            if b.get('beam'):
                # Charge beam bullet — thick golden bolt
                blen = b.get('len', 1)
                p(br, bc, '◉', P(4)|curses.A_BOLD)
                for dx in range(1, min(blen, W-bc-1)):
                    p(br, bc+dx, '═', P(4)|curses.A_BOLD)
            else:
                # Normal bullet — slim cyan dart
                p(br, bc, '─▶', P(1)|curses.A_BOLD)

    # ── Enemy bullets ─────────────────────────────────────────────────────────
    for b in game.ebullets:
        bc=int(b['x']); br=int(b['y'])
        if AT<=br<GR and 1<=bc<W-1:
            p(br, bc, '◁·', P(2)|curses.A_BOLD)

    # ── Explosions ────────────────────────────────────────────────────────────
    for ex in game.explosions:
        fr = Explosion.FRAMES[min(ex.f, len(Explosion.FRAMES)-1)]
        for i, row in enumerate(fr):
            r=ex.y-1+i; c=ex.x-1
            if AT<=r<GR and 1<=c<W-2: p(r, c, row, P(4)|curses.A_BOLD)

    # ── Wave/event message box ────────────────────────────────────────────────
    if game.msg_t > 0:
        msg = game.msg
        mw  = len(msg) + 4
        mc  = (W-mw)//2
        mr  = AT + (GR-AT)//2
        p(mr-1, mc, '╔'+'═'*(mw-2)+'╗', P(7)|curses.A_BOLD)
        p(mr,   mc, '║ '+msg+' ║',        P(7)|curses.A_BOLD)
        p(mr+1, mc, '╚'+'═'*(mw-2)+'╝', P(7)|curses.A_BOLD)

    # ── Controls footer ───────────────────────────────────────────────────────
    for r in range(GR+1, H-1): p(r,0,'║',P(5)); p(r,W-1,'║',P(5))
    ctrl = 'WASD/↑↓←→ Move  │  J/Click Shoot  │  Hold J Charge  │  ESC Pause  │  Q Quit'
    p(H-3, 1, ctrl.center(W-2)[:W-2], P(5))
    p(H-2, 0, '╚'+'═'*(W-2)+'╝', P(5))
    scr.refresh()

GAMEOVER_ART = [
    '   ██████╗  █████╗ ███╗   ███╗███████╗ ',
    '  ██╔════╝ ██╔══██╗████╗ ████║██╔════╝ ',
    '  ██║  ███╗███████║██╔████╔██║█████╗   ',
    '  ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝   ',
    '  ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗ ',
    '   ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝ ',
    '      ██████╗ ██╗   ██╗███████╗██████╗ ',
    '     ██╔═══██╗██║   ██║██╔════╝██╔══██╗',
    '     ██║   ██║██║   ██║█████╗  ██████╔╝',
    '     ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗',
    '     ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║',
    '      ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝',
]

def draw_gameover(scr, H, W, score, wave, tick, sub_result=None):
    P=curses.color_pair; scr.erase()
    p=lambda r,c,s,a=0: _p(scr,H,W,r,c,s,a)

    # ── Outer border ──────────────────────────────────────────────────────────
    p(0,   0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    p(H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1): p(r,0,'║',P(5)); p(r,W-1,'║',P(5))

    # ── Flickering starfield ruins ────────────────────────────────────────────
    rng = random.Random(tick // 4)
    for _ in range(30):
        sr = rng.randint(1, H-2); sc = rng.randint(1, W-2)
        p(sr, sc, rng.choice(['·','∙','✧']), P(5)|curses.A_DIM)

    # ── GAME OVER art (centered) ──────────────────────────────────────────────
    art_h  = len(GAMEOVER_ART)
    art_w  = max(len(l) for l in GAMEOVER_ART)
    art_r  = max(1, (H - art_h - 8) // 2)
    for i, line in enumerate(GAMEOVER_ART):
        color = P(2) if i < 6 else P(4)   # top half red, bottom half gold
        blink_off = (i < 6) and (tick//8)%2==0
        if not blink_off:
            p(art_r+i, max(1,(W-art_w)//2), line, color|curses.A_BOLD)

    # ── Score panel ───────────────────────────────────────────────────────────
    mr = art_r + art_h + 1
    panel_w = 38
    panel_x = (W - panel_w) // 2
    p(mr,   panel_x, '╔'+'═'*(panel_w-2)+'╗', P(5)|curses.A_BOLD)
    sc_line = f' SCORE  {score:08d}   WAVE {wave:02d} '
    p(mr+1, panel_x, '║'+sc_line.center(panel_w-2)+'║', P(4)|curses.A_BOLD)
    pl_name = player_label()
    p(mr+2, panel_x, '║'+f' {pl_name} '.center(panel_w-2)+'║', P(1)|curses.A_BOLD)

    # Rank line
    if sub_result and sub_result[0]:
        rank = sub_result[0].get('rank')
        if rank:
            rank_s = f' ◆ Global rank: #{rank} ◆ '
            p(mr+3, panel_x, '║'+rank_s.center(panel_w-2)+'║', P(3)|curses.A_BOLD)
        else:
            p(mr+3, panel_x, '║'+''.center(panel_w-2)+'║', P(5))
    elif sub_result and sub_result[0] is None:
        p(mr+3, panel_x, '║'+' Submitting score... '.center(panel_w-2)+'║', P(5)|curses.A_DIM)
    else:
        p(mr+3, panel_x, '║'+''.center(panel_w-2)+'║', P(5))
    p(mr+4, panel_x, '╚'+'═'*(panel_w-2)+'╝', P(5)|curses.A_BOLD)

    # ── Blinking restart prompt ───────────────────────────────────────────────
    if (tick//12)%2==0:
        msg = '◈  SPACE  Play Again     ESC  Quit  ◈'
        p(mr+6, (W-len(msg))//2, msg, P(5))
    scr.refresh()
class IntroScene(Scene):
    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')): return 'howto'
        if inp.just_pressed(27):       return 'quit'
    def draw(self, r, tick):
        draw_intro(r._scr, self.engine.H, self.engine.W, tick)


class HowToPlayScene(Scene):
    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')): return 'play'
        if inp.just_pressed(27):       return 'quit'
    def draw(self, r, tick):
        draw_how_to_play(r._scr, self.engine.H, self.engine.W, tick)


class PlayScene(Scene):
    def on_enter(self):
        self.game = Game(self.engine.H, self.engine.W)
        self.game.show('  WAVE 1  ', 50)
        self.paused = False

    def update(self, inp, tick, dt):
        if inp.just_pressed(27):
            self.paused = not self.paused
            return None
        if self.paused:
            if inp.just_pressed(ord('r'), ord('R')): self.paused = False
            if inp.just_pressed(ord('q'), ord('Q')): return 'quit'
            return None

        mshoot = 1 in inp.mouse_pressed
        self.game.update(inp.keys, mshoot)
        p = self.game.player
        if p.lives <= 0 and p.invuln == 0:
            sub: list = [None]
            submit_async('ctype', self.game.score, f'Wave {self.game.wave}', sub)
            return ('gameover', (self.game.score, self.game.wave, sub))

    def draw(self, r, tick):
        draw_game(r._scr, self.game, self.engine.H, self.engine.W, tick)
        if self.paused:
            draw_pause(r._scr, self.engine.H, self.engine.W)


class GameOverScene(Scene):
    def on_enter(self):
        if isinstance(self.payload, tuple) and len(self.payload) == 3:
            self.score, self.wave, self.sub = self.payload
        else:
            self.score, self.wave, self.sub = 0, 1, [None]

    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')): return 'play'
        if inp.just_pressed(27):       return 'quit'

    def draw(self, r, tick):
        draw_gameover(r._scr, self.engine.H, self.engine.W,
                      self.score, self.wave, tick, self.sub)


def main():
    Engine('C-TYPE', fps=FPS) \
        .scene('intro',    IntroScene()) \
        .scene('howto',    HowToPlayScene()) \
        .scene('play',     PlayScene()) \
        .scene('gameover', GameOverScene()) \
        .run('intro')


if __name__ == '__main__':
    main()
