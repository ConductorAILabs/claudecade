#!/usr/bin/env python3
"""Claudtra — Side-Scrolling Action · ESC to quit"""
from __future__ import annotations

import curses, random
from claudcade_engine import Engine, Renderer, Scene, at_safe
from claudcade_engine import draw_how_to_play as _engine_how_to_play
from claudcade_engine import BulletDict, PlatformDict
from claudcade_scores import player_label, submit_async

CONTROLS = [
    'A / D           Move left / right',
    'SPACE           Jump',
    'J / Click       Shoot',
    'S               Crouch',
    'ESC             Pause / Resume',
    'Q               Quit to Claudcade',
]

def draw_pause(scr, H, W):
    Renderer(scr, H, W).pause_overlay('Claudtra', CONTROLS)

def draw_how_to_play(scr, H, W, tick):
    _engine_how_to_play(
        scr, H, W, tick,
        goal=[
            'Run, jump, and shoot your way through endless waves of grunts and',
            'heavies. Survive as long as possible.',
        ],
        controls=[
            'A / D            Move left / right',
            'SPACE            Jump',
            'J / Click        Shoot',
            'S                Crouch',
            'ESC              Pause',
        ],
        tips=[
            '• Crouch to dodge enemy fire',
            '• Jump over fast enemies',
            '• Heavy enemies take multiple hits',
        ],
    )
FPS       = 30
SW, SH    = 7, 5
WALK      = 1.3
JV0       = 6.0
GRAV      = 0.8
B_SPD     = 4.0
EB_SPD    = 1.6
E_SPD     = 0.35
SHOOT_CD  = 10
LIVES     = 3
INVULN    = 90
GUN_ROW   = 3.0   # world-y height of gun (used for bullet spawning)
TITLE_ART = [
    r" ██████╗██╗      █████╗ ██╗   ██╗██████╗ ████████╗██████╗  █████╗ ",
    r"██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗",
    r"██║     ██║     ███████║██║   ██║██║  ██║   ██║   ██████╔╝███████║",
    r"██║     ██║     ██╔══██║██║   ██║██║  ██║   ██║   ██╔══██╗██╔══██║",
    r"╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝   ██║   ██║  ██║██║  ██║",
    r" ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝",
]
def frm(*rows, w=SW, h=SH):
    out = [(r + ' '*w)[:w] for r in rows]
    while len(out) < h: out.append(' '*w)
    return out[:h]

PSP = {  # player faces right  (SW=7 wide, SH=5 tall)
    'run':   [frm(' ╓──╖ ',' ▶╫─►','  ║   ',' ╱ ╲  ','╱     '),
              frm(' ╓──╖ ',' ▶╫─►','  ║   ','╱   ╲ ','  ╲   ')],
    'jump':  [frm(' ╓──╖ ',' ▶╫─►',' /║   ',' ╱    ','      ')],
    'shoot': [frm(' ╓──╖ ',' ▶╫━━►','  ║   ',' ╱ ╲  ','      ')],
    'crouch':[frm('      ',' ╓──╖►','▶╫══╗ ','      ','      ')],
    'hurt':  [frm(' ╳──╳ ',' ╱║╲  ','  ║   ',' ╲ ╱  ','      ')],
    'dead':  [frm('      ','      ','╔╗x╔╗ ','╚╩═╩╝ ','▓▓▓▓▓ ')],
    'idle':  [frm(' ╓──╖ ',' ▶╫   ','  ║   ',' ╱ ╲  ','      '),
              frm(' ╓──╖ ',' ▶╫   ','  ║   ',' ╲ ╱  ','      ')],
}
def _flip(frames):
    t = {'/':'\\','\\':'/','>':'<','<':'>','(':')',')':'('}
    return [[''.join(t.get(c,c) for c in reversed(r)) for r in fr] for fr in frames]
PSP_L = {k: _flip(v) for k,v in PSP.items()}

GRUNT = {
    'walk': [frm(' ◉    ','◄╟─   ','  ╎   ',' ╱╎   ','      '),
             frm(' ◉    ','◄╟─   ','  ╎   ','  ╎╲  ','      ')],
    'shoot':[frm(' ◉    ','◄━━╟─ ','  ╎   ',' ╱╎   ','      ')],
    'hurt': [frm(' ╳    ','╲╟╱   ','  ╎   ',' ╲╎╱  ','      ')],
    'dead': [frm('      ','  ╳   ','╔╗x╔╗ ','╚╩═╩╝ ','▓▓▓▓▓ ')],
}
HEAVY = {
    'idle': [frm(' ◉◉   ','◄╠══╗ ','  ║║  ','▓╱  ╲ ','      '),
             frm(' ◉◉   ','◄╠══╗ ','  ║║  ','▓╱  ╲ ','  ╷   ')],
    'shoot':[frm(' ◉◉   ','◄━━╠══╗','  ║║  ','▓╱  ╲ ','      ')],
    'hurt': [frm(' ╳╳   ','╲╠══╱ ','  ║║  ','▓╲  ╱ ','      ')],
    'dead': [frm('      ','  ╳╳  ','╔╬══╬╗','╚╬══╬╝','▓▓▓▓▓ ')],
}

def get_frame(sp, state, af):
    frames = sp.get(state, sp.get('idle', list(sp.values())[0]))
    return frames[af % len(frames)]
class Player:
    def __init__(self):
        self.wx = 5.0; self.y = 0.0; self.vy = 0.0
        self.grounded = True; self.facing = 1
        self.state = 'idle'; self.af = 0; self.at = 0
        self.lives = LIVES; self.invuln = 0
        self.shoot_cd = 0; self.dead_timer = 0

    def set(self, s):
        if self.state == s: return
        self.state = s; self.af = 0; self.at = 0

    def tick_anim(self):
        self.at += 1
        spd = 5 if self.state == 'run' else 7
        if self.at >= spd:
            self.at = 0
            sp = PSP if self.facing==1 else PSP_L
            frames = sp.get(self.state, sp['idle'])
            self.af = (self.af+1) % len(frames)

    def frame(self):
        sp = PSP if self.facing==1 else PSP_L
        return get_frame(sp, self.state, self.af)

    def get_hit(self):
        if self.invuln > 0: return False
        self.lives -= 1; self.invuln = INVULN
        if self.lives <= 0: self.set('dead'); self.dead_timer = 80
        else:               self.set('hurt')
        return True

    def update(self, keys, mshoot, world):
        if self.state == 'dead':
            self.dead_timer -= 1; self.tick_anim(); return
        if self.invuln > 0: self.invuln -= 1
        if self.state == 'hurt' and self.invuln < INVULN-12: self.set('idle')
        if self.shoot_cd > 0: self.shoot_cd -= 1

        vx = 0
        if ord('a') in keys or curses.KEY_LEFT  in keys: vx = -WALK; self.facing = -1
        if ord('d') in keys or curses.KEY_RIGHT in keys: vx =  WALK; self.facing =  1
        if self.state not in ('hurt',):
            self.wx = max(0, self.wx + vx)

        if not self.grounded:
            self.vy -= GRAV

        new_y = self.y + self.vy

        # platforms first (so fast falls don't skip through them to ground)
        if self.vy <= 0:
            for pl in world.platforms:
                if pl['x'] - 1 <= self.wx <= pl['x'] + pl['w'] + 1:
                    if self.y >= pl['y'] >= new_y:
                        new_y = pl['y']; self.vy = 0; self.grounded = True
                        if self.state == 'jump': self.set('idle')
                        break

        # ground
        if new_y <= 0:
            new_y = 0; self.vy = 0; self.grounded = True
            if self.state == 'jump': self.set('idle')

        self.y = new_y

        # platform edge: still supported?
        if self.grounded and self.y > 0:
            on_pl = any(pl['x'] - 0.5 <= self.wx <= pl['x']+pl['w']+0.5
                        and abs(pl['y']-self.y) < 0.5
                        for pl in world.platforms)
            if not on_pl: self.grounded = False

        if (ord('w') in keys or ord(' ') in keys or curses.KEY_UP in keys) and self.grounded:
            self.vy = JV0; self.grounded = False

        crouch = (ord('s') in keys or curses.KEY_DOWN in keys) and self.grounded
        shoot  = (ord('j') in keys or ord('f') in keys or mshoot) and self.shoot_cd == 0
        if shoot and self.state not in ('hurt',):
            bx = self.wx + (4 if self.facing==1 else -2)
            by = self.y + GUN_ROW
            world.bullets.append({'wx': bx, 'y': by,
                                   'vx': B_SPD * self.facing, 'owner': 'player'})
            world.muzzle(bx, by, self.facing)
            self.shoot_cd = SHOOT_CD
            if self.grounded: self.set('shoot')

        if self.state not in ('hurt', 'shoot', 'dead'):
            if not self.grounded:        self.set('jump')
            elif crouch:                 self.set('crouch')
            elif vx != 0:                self.set('run')
            else:                        self.set('idle')
        if self.state == 'shoot' and self.shoot_cd == 0: self.set('idle')

        self.tick_anim()
class Enemy:
    def __init__(self, wx, etype='grunt'):
        self.wx = float(wx); self.y = 0.0
        self.etype = etype
        self.hp = 1 if etype == 'grunt' else 4
        self.state = 'walk' if etype == 'grunt' else 'idle'
        self.af = 0; self.at = 0
        self.shoot_cd = random.randint(60, 140) if etype == 'heavy' else random.randint(40, 100)
        self.alive = True

    def frame(self):
        sp = GRUNT if self.etype == 'grunt' else HEAVY
        return get_frame(sp, self.state, self.af)

    def tick_anim(self):
        self.at += 1
        if self.at >= 6:
            self.at = 0
            sp = GRUNT if self.etype == 'grunt' else HEAVY
            frames = sp.get(self.state, list(sp.values())[0])
            self.af = (self.af + 1) % len(frames)

    def take_hit(self):
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False; self.state = 'dead'; return True
        self.state = 'hurt'; self.af = 0; self.at = 0
        return False

    def update(self, player, world):
        if not self.alive: return
        if self.state == 'dead': return
        if self.state == 'hurt':
            self.tick_anim()
            if self.at == 0 and self.af >= 1:
                self.state = 'walk' if self.etype == 'grunt' else 'idle'
            return

        dx = player.wx - self.wx
        self.shoot_cd -= 1

        if self.etype == 'grunt':
            if abs(dx) > 5:
                self.wx += E_SPD * (1 if dx > 0 else -1)
            if self.shoot_cd <= 0 and abs(dx) < 55:
                self.shoot_cd = random.randint(50, 110)
                vx = EB_SPD * (1 if dx > 0 else -1)
                world.bullets.append({'wx': self.wx, 'y': self.y + GUN_ROW,
                                       'vx': vx, 'owner': 'enemy'})
                world.muzzle(self.wx, self.y + GUN_ROW, 1 if vx > 0 else -1)
                self.state = 'shoot'
            elif self.state == 'shoot': self.state = 'walk'
        else:  # heavy
            if self.shoot_cd <= 0 and abs(dx) < 60:
                self.shoot_cd = random.randint(70, 130)
                vx = EB_SPD * 1.4 * (1 if dx > 0 else -1)
                world.bullets.append({'wx': self.wx, 'y': self.y + GUN_ROW,
                                       'vx': vx, 'owner': 'enemy'})
                world.muzzle(self.wx, self.y + GUN_ROW, 1 if vx > 0 else -1)
                self.state = 'shoot'
            elif self.state == 'shoot': self.state = 'idle'

        self.tick_anim()
# Biome thresholds in world-x units. Each biome has a name + color pair index
# used by the renderer for accent foliage / ground tone.
BIOMES = [
    (   0, 'FOREST',  3),   # green
    ( 800, 'FACTORY', 5),   # white
    (1800, 'ORBIT',   1),   # cyan
]

# Checkpoints at biome boundaries — death respawns at the most recent one.
CHECKPOINT_XS = [b[0] for b in BIOMES]


def biome_for(wx: float) -> tuple[int, str, int]:
    """Return (start_x, name, color_pair) for the biome containing world-x."""
    chosen = BIOMES[0]
    for entry in BIOMES:
        if wx >= entry[0]:
            chosen = entry
    return chosen


class World:
    def __init__(self):
        self.cam_x = 0.0
        self.player = Player()
        self.enemies = []
        self.bullets:   list[BulletDict]   = []
        self.platforms: list[PlatformDict] = []
        # Short-lived FX:
        # flashes  = muzzle-flash sprites: {'wx','y','dir','ttl'}
        # particles= death dust + hit sparks: {'wx','y','vx','vy','ttl','ch'}
        self.flashes   = []
        self.particles = []
        self.score = 0; self.wave = 1; self._gen_to = 0
        # Most-recently-passed checkpoint; player respawns here on death.
        self.checkpoint_x = 0.0
        # Last biome name announced — for "ENTERING X" toast.
        self.biome_name   = BIOMES[0][1]
        self.biome_msg    = ''; self.biome_msg_t = 0
        self._generate(0, 250)

    def muzzle(self, wx, y, direction):
        self.flashes.append({'wx': wx, 'y': y, 'dir': direction, 'ttl': 3})

    def burst(self, wx, y, n=6):
        for _ in range(n):
            self.particles.append({
                'wx': wx + random.uniform(-0.5, 0.5),
                'y':  y  + random.uniform(0.0, 1.5),
                'vx': random.uniform(-1.2, 1.2),
                'vy': random.uniform(0.4, 1.4),
                'ttl': random.randint(5, 10),
                'ch': random.choice(['·','∙','*','▓']),
            })

    def _generate(self, start, end):
        x = max(start, self._gen_to, 90)  # no enemies in first 90 units
        while x < end:
            if random.random() < 0.3:
                w = random.randint(7, 16)
                y = float(random.randint(3, 8))
                self.platforms.append({'x': float(x), 'y': y, 'w': float(w)})
                x += w + random.randint(6, 16)
            else:
                x += random.randint(10, 20)
            if x > 90 and random.random() < 0.45:
                et = 'heavy' if random.random() < 0.2 else 'grunt'
                self.enemies.append(Enemy(float(x + random.randint(5, 28)), et))
        self._gen_to = end

    def _check_hits(self):
        p = self.player
        for b in self.bullets:
            if b.get('dead'): continue
            if b['owner'] == 'player':
                for e in self.enemies:
                    if not e.alive or e.state == 'dead': continue
                    if abs(b['wx'] - e.wx - 3) < 6 and abs(b['y'] - (e.y + GUN_ROW)) < 4:
                        b['dead'] = True
                        if e.take_hit():
                            self.score += 300 if e.etype == 'heavy' else 100
                            self.burst(e.wx + 3, e.y, n=10 if e.etype == 'heavy' else 6)
                        else:
                            self.burst(b['wx'], b['y'], n=2)
                        break
            else:  # enemy bullet
                if p.invuln > 0 or p.state == 'dead': continue
                if abs(b['wx'] - p.wx - 3) < 5 and abs(b['y'] - (p.y + GUN_ROW)) < 4:
                    b['dead'] = True; p.get_hit()
        # contact damage
        if p.invuln == 0 and p.state not in ('dead', 'hurt'):
            for e in self.enemies:
                if e.alive and e.etype == 'grunt':
                    if abs(e.wx - p.wx) < 5 and abs(e.y - p.y) < 3:
                        p.get_hit(); break

    def update(self, keys, mshoot):
        p = self.player
        p.update(keys, mshoot, self)
        self.cam_x = max(0.0, p.wx - 22)

        if self.cam_x + 180 > self._gen_to:
            self._generate(self._gen_to, int(self.cam_x + 260))

        for e in self.enemies: e.update(p, self)
        for b in self.bullets:  b['wx'] += b['vx']
        for f in self.flashes:  f['ttl'] -= 1
        for pt in self.particles:
            pt['wx'] += pt['vx']; pt['y'] += pt['vy']
            pt['vy'] *= 0.85; pt['vx'] *= 0.92
            pt['ttl'] -= 1

        lo, hi = self.cam_x - 10, self.cam_x + 95
        self.bullets   = [b for b in self.bullets   if not b.get('dead') and lo < b['wx'] < hi]
        self.enemies   = [e for e in self.enemies   if e.wx > self.cam_x - 15]
        self.platforms = [pl for pl in self.platforms if pl['x'] + pl['w'] > self.cam_x - 10]
        self.flashes   = [f for f in self.flashes   if f['ttl'] > 0]
        self.particles = [pt for pt in self.particles if pt['ttl'] > 0 and lo < pt['wx'] < hi]
        self._check_hits()
        self.wave = 1 + int(p.wx) // 200

        # Update checkpoint when crossing a boundary.
        for cx in CHECKPOINT_XS:
            if p.wx >= cx > self.checkpoint_x:
                self.checkpoint_x = float(cx)
        # Toast on biome change.
        cur_name = biome_for(p.wx)[1]
        if cur_name != self.biome_name:
            self.biome_name  = cur_name
            self.biome_msg   = f'  ENTERING {cur_name}  '
            self.biome_msg_t = 60
        if self.biome_msg_t > 0:
            self.biome_msg_t -= 1
_p = at_safe

def draw_intro(scr, H, W, tick):
    P = curses.color_pair; scr.erase()
    p = lambda r,c,s,a=0: _p(scr,H,W,r,c,s,a)

    # Outer border
    p(0,   0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    p(H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        p(r, 0,   '║', P(5)|curses.A_BOLD)
        p(r, W-1, '║', P(5)|curses.A_BOLD)

    # Scrolling starfield background
    stars = ['·', '·', '·', '·', '∙', '∘', '○']
    rng = random.Random(tick // 6)
    for r in range(2, H-3):
        for c in range(2, W-2, 7):
            s = stars[rng.randint(0, len(stars)-1)]
            p(r, (c + (tick//4)) % (W-4) + 2, s, P(5)|curses.A_DIM)

    # Title art — centred, colour-banded
    ta = TITLE_ART
    # Fall back to short title if terminal too narrow
    if W < len(ta[0]) + 4:
        ta = [
            r"  ██████╗██╗      █████╗ ██╗   ██╗",
            r" ██╔════╝██║     ██╔══██╗██║   ██║",
            r" ██║     ██║     ███████║██║   ██║",
            r" ╚██████╗███████╗██║  ██║╚██████╔╝",
            r"  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ",
        ]
    sr = max(1, (H - len(ta) - 10) // 2)
    color_cycle = [P(1)|curses.A_BOLD, P(4)|curses.A_BOLD,
                   P(3)|curses.A_BOLD, P(1)|curses.A_BOLD,
                   P(6)|curses.A_BOLD, P(5)|curses.A_BOLD]
    for i, line in enumerate(ta):
        cx = max(1, (W - len(line)) // 2)
        p(sr+i, cx, line, color_cycle[i % len(color_cycle)])

    # Sub-title divider
    div_y = sr + len(ta) + 1
    sub = '◄══  SIDE-SCROLLING RUN & GUN  ══►'
    p(div_y, (W-len(sub))//2, sub, P(5)|curses.A_BOLD)

    # Animated demo sprites: player left, grunt right
    ty = H - 10
    pframe = (tick // 10) % 2
    gframe = (tick // 10) % 2
    for i, row in enumerate(PSP['run'][pframe]):
        p(ty+i, 4, row, P(1)|curses.A_BOLD)
    # Bullet in middle when tick phase right
    if (tick // 8) % 5 == 0:
        bullet_col = 4 + SW + 1 + (tick % 8)
        p(ty + 2, min(bullet_col, W-8), '━►', P(4)|curses.A_BOLD)
    for i, row in enumerate(GRUNT['walk'][gframe]):
        p(ty+i, W-SW-5, row, P(2)|curses.A_BOLD)

    # Ground line under demo sprites
    p(ty + SH, 2, '▓' * (W-4), P(5)|curses.A_DIM)

    # Blinking start prompt
    if (tick // 18) % 2 == 0:
        msg = '◄  PRESS SPACE TO START  ►'
        p(H-4, (W-len(msg))//2, msg, P(4)|curses.A_BOLD)

    # Controls hint
    hint = '[ A/D: Move ]  [ SPACE: Jump ]  [ J / Click: Shoot ]  [ S: Crouch ]'
    p(H-2, max(1,(W-len(hint))//2), hint, P(5)|curses.A_DIM)

    scr.refresh()

def draw_game(scr, world, H, W, tick):
    P = curses.color_pair; scr.erase()
    p = lambda r,c,s,a=0: _p(scr,H,W,r,c,s,a)
    pl  = world.player
    cam = world.cam_x
    AT  = 3        # top of play area (row index)
    GR  = H - 5   # ground row — adapts to terminal height

    def spr(world_y):      # sprite TOP row for entity at world_y
        return GR - SH - int(world_y)

    def sc(world_x):       # screen col
        return int(world_x - cam) + 1

    def brow(bullet_y):    # screen row for bullet
        return GR - int(bullet_y) - 1

    # ── HUD top bar ────────────────────────────────────────────────────────
    p(0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    p(1, 0, '║', P(5)|curses.A_BOLD); p(1, W-1, '║', P(5)|curses.A_BOLD)
    p(2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

    # HUD section 1: LIVES (left)
    hp_filled = pl.lives
    hp_empty  = LIVES - hp_filled
    hp_bar = '█'*hp_filled + '░'*hp_empty
    lives_str = f'  LIVES: [{hp_bar}]'
    p(1, 1, lives_str, P(2)|curses.A_BOLD)

    # HUD section 2: SCORE (center)
    sc_str = f'◄ SCORE: {world.score:07d} ►'
    score_col = (W - len(sc_str)) // 2
    p(1, score_col, sc_str, P(4)|curses.A_BOLD)

    # HUD section 3: WAVE & DISTANCE (right)
    dist_m = int(pl.wx * 2)
    bcp    = biome_for(pl.wx)[2]
    wd = f'WAVE:{world.wave:2d}  DIST:{dist_m:05d}m  '
    wave_col = W - len(wd) - 2
    p(1, wave_col, wd, P(bcp)|curses.A_BOLD)

    # Vertical dividers between sections
    div1_col = score_col - 2
    div2_col = wave_col - 1
    if div1_col > len(lives_str) + 1:
        p(1, div1_col, '║', P(5)|curses.A_BOLD)
    if div2_col > score_col + len(sc_str) + 1:
        p(1, div2_col, '║', P(5)|curses.A_BOLD)

    # Biome-entry: bright full-width band for the first ~6 frames, then blink toast
    if world.biome_msg_t > 54:
        band_y = H // 2 - 1
        band   = '>>>' + world.biome_msg.strip().rjust(20).ljust(28) + '<<<'
        p(band_y, max(1, (W - len(band)) // 2), band[:W-2], P(bcp)|curses.A_BOLD|curses.A_REVERSE)
    elif world.biome_msg_t > 0 and (tick // 6) % 2 == 0:
        bx = (W - len(world.biome_msg)) // 2
        p(H // 2 - 1, bx, world.biome_msg, P(bcp)|curses.A_BOLD|curses.A_REVERSE)

    # ── Side borders (play area) ───────────────────────────────────────────
    for r in range(AT, GR):
        p(r, 0,   '║', P(5))
        p(r, W-1, '║', P(5))

    # ── Background layer 1: far stars (░) slow scroll ─────────────────────
    far_stars = [(2,11),(3,27),(4,45),(5,61),(6,9),(7,38),(8,55),(9,22),
                 (5,72),(3,83),(7,14),(4,68),(6,51),(8,35),(9,77)]
    far_off = int(cam * 0.04)
    for (br_, bc_) in far_stars:
        c_ = (bc_ - far_off) % (W-4) + 2
        if AT <= br_ < GR-8 and 1 < c_ < W-1:
            p(br_, c_, '░', P(5)|curses.A_DIM)

    # ── Background layer 2: mid mountains (▒) medium scroll ───────────────
    mid_off = int(cam * 0.18) % (W-2)
    mountain_pat = '  ▒  ▒▒▒ ▒▒▒▒▒  ▒▒▒▒▒▒▒  ▒▒▒  ▒▒▒▒▒▒▒▒▒  ▒▒▒  '
    mrow = GR - 8
    if AT < mrow < GR:
        full = (mountain_pat * ((W // len(mountain_pat)) + 3))
        seg  = full[mid_off: mid_off + W - 2]
        p(mrow, 1, seg, P(5)|curses.A_DIM)

    # ── Background layer 3: near hills (▒▓) faster scroll ─────────────────
    near_off = int(cam * 0.40) % (W-2)
    hill_pat = '▒▒▓▓▓▒▒  ▒▒▒▓▓▓▓▓▒▒  ▒▒▒▒▓▓▓▒▒  ▒▓▓▓▓▓▒▒  '
    hrow = GR - 5
    if AT < hrow < GR:
        full = (hill_pat * ((W // len(hill_pat)) + 3))
        seg  = full[near_off: near_off + W - 2]
        p(hrow, 1, seg, P(5)|curses.A_DIM)

    # ── Ground ─────────────────────────────────────────────────────────────
    p(GR, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    gnd_off = int(cam * 1.0) % 8
    gnd_pat = '▓▓▓▒▓▓▓▓'
    if GR+1 < H-1:
        full = (gnd_pat * ((W // len(gnd_pat)) + 2))
        seg  = full[gnd_off: gnd_off + W - 2]
        p(GR+1, 0, '║'+seg+'║', P(5)|curses.A_BOLD)

    # ── Platforms ──────────────────────────────────────────────────────────
    for pl_ in world.platforms:
        c0 = sc(pl_['x']); pr = GR - int(pl_['y'])
        pw = int(pl_['w'])
        if -pw < c0 < W and AT < pr < GR:
            # Top surface — double-line caps
            top_seg  = '╔' + '═'*pw + '╗'
            vis      = top_seg[max(0, 1-c0):]
            p(pr,   max(1,c0), vis[:W-max(1,c0)], P(3)|curses.A_BOLD)
            # Under-surface — hatched fill
            bot_seg  = '║' + '▓'*(pw//2) + '≡'*(pw - pw//2) + '║'
            vis2     = bot_seg[max(0, 1-c0):]
            p(pr+1, max(1,c0), vis2[:W-max(1,c0)], P(5)|curses.A_DIM)

    # ── Enemies ────────────────────────────────────────────────────────────
    for e in world.enemies:
        c0 = sc(e.wx)
        if -SW < c0 < W:
            fr  = e.frame()
            top = spr(e.y)
            if   e.state == 'hurt': cp = P(6)|curses.A_BOLD|curses.A_REVERSE
            elif e.state == 'dead': cp = P(5)|curses.A_DIM
            elif e.etype == 'heavy': cp = P(3)|curses.A_BOLD   # gold/orange heavies
            else:                    cp = P(2)|curses.A_BOLD   # green grunts
            for i, row in enumerate(fr):
                r = top+i
                if AT <= r < GR: p(r, max(1,c0), row, cp)

    # ── Player ─────────────────────────────────────────────────────────────
    blink = pl.invuln > 0 and (tick//3) % 2 == 0
    if not blink:
        c0  = sc(pl.wx)
        top = spr(pl.y)
        fr  = pl.frame()
        if   pl.state == 'dead': cp = P(5)|curses.A_DIM
        elif pl.state == 'hurt': cp = P(6)|curses.A_BOLD|curses.A_REVERSE
        else:                    cp = P(1)|curses.A_BOLD
        for i, row in enumerate(fr):
            r = top+i
            if AT <= r < GR: p(r, max(1,c0), row, cp)

    # ── Bullets ────────────────────────────────────────────────────────────
    for b in world.bullets:
        c0 = sc(b['wx']); br = brow(b['y'])
        if 1 <= c0 < W-2 and AT <= br < GR:
            if b['owner'] == 'player':
                sprite = '━►'
                cp = P(4)|curses.A_BOLD
            else:
                sprite = '◄━'
                cp = P(2)|curses.A_BOLD
            p(br, c0, sprite, cp)

    # ── Muzzle flashes (1–2 frames at gun position before bullet flies) ────
    for f in world.flashes:
        c0 = sc(f['wx']); br = brow(f['y'])
        if 1 <= c0 < W-2 and AT <= br < GR:
            ch = '╪' if f['ttl'] >= 2 else '+'
            p(br, c0, ch, P(4)|curses.A_BOLD)

    # ── Death-burst particles ─────────────────────────────────────────────
    for pt in world.particles:
        c0 = sc(pt['wx']); br = brow(pt['y'])
        if 1 <= c0 < W-1 and AT <= br < GR:
            attr = curses.A_BOLD if pt['ttl'] > 4 else curses.A_DIM
            p(br, c0, pt['ch'], P(2)|attr)

    # ── In-game overlay (death / respawn) ──────────────────────────────────
    if pl.state == 'dead' and pl.dead_timer > 35:
        if pl.lives <= 0:
            lines = ['  ╔═══════════════╗  ',
                     '  ║  GAME  OVER   ║  ',
                     '  ╚═══════════════╝  ']
            clr = P(2)|curses.A_BOLD
        else:
            lines = ['  ╔═══════════════╗  ',
                     '  ║  GET  READY!  ║  ',
                     '  ╚═══════════════╝  ']
            clr = P(3)|curses.A_BOLD
        mr = AT + (GR-AT)//2 - 1
        for di, ln in enumerate(lines):
            p(mr+di, (W-len(ln))//2, ln, clr)

    # ── Bottom status bar ──────────────────────────────────────────────────
    p(H-4, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    p(H-3, 0, '║', P(5)); p(H-3, W-1, '║', P(5))
    ctrl = '[ A/D:Move ]  [ SPC:Jump ]  [ J/Click:Shoot ]  [ S:Crouch ]  [ ESC:Pause ]'
    p(H-3, 1, ctrl.center(W-2), P(5)|curses.A_DIM)
    p(H-2, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    scr.refresh()

def draw_gameover(scr, H, W, score, tick, sub_result=None):
    P = curses.color_pair; scr.erase()
    p = lambda r,c,s,a=0: _p(scr,H,W,r,c,s,a)

    # Outer border
    p(0,   0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    p(H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        p(r, 0,   '║', P(5)|curses.A_BOLD)
        p(r, W-1, '║', P(5)|curses.A_BOLD)

    # Scrolling starfield background (similar to intro)
    stars = ['·', '·', '·', '·', '∙', '∘', '○']
    rng = random.Random(tick // 6)
    for r in range(2, H-4):
        for c in range(2, W-2, 7):
            s = stars[rng.randint(0, len(stars)-1)]
            p(r, (c + (tick//4)) % (W-4) + 2, s, P(5)|curses.A_DIM)

    color_band = [P(1)|curses.A_BOLD, P(4)|curses.A_BOLD,
                  P(3)|curses.A_BOLD, P(6)|curses.A_BOLD]
    for bi in range(2):
        band_row = 2 + bi
        if band_row < H - 4:
            p(band_row, 1, '═'*(W-2), color_band[bi % len(color_band)])

    # "GAME OVER" header in block-font style
    mr = H//2 - 5
    go_header = [
        r'  ██████╗  █████╗ ███╗   ███╗███████╗    ██████╗ ██╗   ██╗███████╗██████╗ ',
        r' ██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗',
        r' ██║  ███╗███████║██╔████╔██║█████╗      ██║  ██║ ╚████╔╝ █████╗  ██████╔╝',
        r' ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██║  ██║  ╚██╔╝  ██╔══╝  ██╔══██╗',
        r' ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ██████╔╝   ██║   ███████╗██║  ██║',
        r'  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝    ╚═════╝    ╚═╝   ╚══════╝╚═╝  ╚═╝',
    ]
    # Fall back to shorter header if terminal too narrow
    if W < 80:
        go_header = [
            r' ██████╗  █████╗ ███╗   ███╗███████╗',
            r'██╔════╝ ██╔══██╗████╗ ████║██╔════╝',
            r'██║  ███╗███████║██╔████╔██║█████╗  ',
            r'██║   ██║██╔══██║██║╚██╔╝██║██╔══╝  ',
            r'╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗',
            r' ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝',
        ]
    header_colors = [P(6)|curses.A_BOLD, P(1)|curses.A_BOLD,
                     P(4)|curses.A_BOLD, P(6)|curses.A_BOLD,
                     P(1)|curses.A_BOLD, P(4)|curses.A_BOLD]
    for i, line in enumerate(go_header):
        if mr + i < H - 6:
            cx = max(1, (W - len(line)) // 2)
            p(mr + i, cx, line[:W-2], header_colors[i % len(header_colors)])

    mr = mr + len(go_header) + 1

    sc_lines = [
        '╔════════════════════════════╗',
        f'║  FINAL SCORE:  {score:07d}   ║',
        '╚════════════════════════════╝',
    ]
    for i, ln in enumerate(sc_lines):
        color = P(1)|curses.A_BOLD if i == 1 else P(5)|curses.A_BOLD
        p(mr+i, (W-len(ln))//2, ln, color)

    pl = player_label()
    p(mr+4, (W-len(pl)-4)//2, f'◄  {pl}  ►', P(4)|curses.A_BOLD)

    if sub_result and sub_result[0]:
        rank = sub_result[0].get('rank')
        if rank:
            # Award visual based on rank
            if rank <= 10:
                badge = '★ ELITE ★'
                badge_color = P(3)|curses.A_BOLD
            elif rank <= 50:
                badge = '▲ TOP 50 ▲'
                badge_color = P(4)|curses.A_BOLD
            else:
                badge = '◆ RANKED ◆'
                badge_color = P(6)|curses.A_BOLD
            rm = f'  {badge}  Global rank: #{rank}  '
            p(mr+5, (W-len(rm))//2, rm, badge_color)
    elif sub_result and sub_result[0] is None:
        p(mr+5, (W-26)//2, '  Submitting score...  ', P(5)|curses.A_DIM)

    for bi in range(2):
        band_row = H - 5 + bi
        if band_row < H - 1:
            p(band_row, 1, '═'*(W-2), color_band[(3-bi) % len(color_band)])

    if (tick//18) % 2 == 0:
        msg = '▸ SPACE = Play Again  │  ESC = Quit ◂'
        p(H-3, (W-len(msg))//2, msg, P(4)|curses.A_BOLD)

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
        self.world  = World()
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
        self.world.update(inp.keys, mshoot)
        p = self.world.player
        if p.state == 'dead' and p.dead_timer <= 0:
            if p.lives <= 0:
                sub: list = [None]
                submit_async('claudtra', self.world.score, f'Dist {int(p.wx)}', sub)
                return ('gameover', (self.world.score, sub))
            # Respawn at next checkpoint (or +12 forward if no checkpoint set yet)
            cp = getattr(self.world, 'checkpoint_x', None)
            p.wx = cp if cp is not None else (p.wx + 12)
            p.y = 0; p.vy = 0
            p.grounded = True; p.invuln = INVULN * 2; p.state = 'idle'

    def draw(self, r, tick):
        draw_game(r._scr, self.world, self.engine.H, self.engine.W, tick)
        if self.paused:
            draw_pause(r._scr, self.engine.H, self.engine.W)


class GameOverScene(Scene):
    def on_enter(self):
        if isinstance(self.payload, tuple) and len(self.payload) == 2:
            self.score, self.sub = self.payload
        else:
            self.score, self.sub = 0, [None]

    def update(self, inp, tick, dt):
        if inp.just_pressed(ord(' ')): return 'play'
        if inp.just_pressed(27):       return 'quit'

    def draw(self, r, tick):
        draw_gameover(r._scr, self.engine.H, self.engine.W,
                      self.score, tick, self.sub)


def main():
    Engine('Claudtra', fps=FPS) \
        .scene('intro',    IntroScene()) \
        .scene('howto',    HowToPlayScene()) \
        .scene('play',     PlayScene()) \
        .scene('gameover', GameOverScene()) \
        .run('intro')


if __name__ == '__main__':
    main()
