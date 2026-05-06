#!/usr/bin/env python3
"""CLAUDE FIGHTER — ESC to quit back to Claude"""
import curses, time, random
from claudcade_engine import Renderer, setup_colors
from claudcade_engine import draw_how_to_play as _engine_how_to_play, run_game
try:
    from claudcade_scores import submit_async
except ImportError:
    def submit_async(*a, **kw): pass
INTRO, SELECT, COUNTDOWN, FIGHT, PAUSE, HOW_TO_PLAY = range(6)

CONTROLS = [
    'A / D           Move left / right',
    'SPACE           Jump',
    'S               Crouch',
    'J / Click       Punch',
    'K               Kick',
    'L               Block',
    'ESC             Pause / Resume',
    'Q               Quit to Claudcade',
]

def draw_pause(scr, H, W):
    Renderer(scr, H, W).pause_overlay('CLAUDE FIGHTER', CONTROLS)

def _fight_put(scr, H, W, r, c, s, a=0):
    try:
        if 0 <= r < H-1 and 0 <= c < W: scr.addstr(r, c, s[:W-c], a)
    except curses.error: pass

def draw_how_to_play(scr, H, W, tick):
    _engine_how_to_play(
        scr, H, W, tick,
        goal=[
            'Defeat the AI opponent in a best of 3 rounds. Each round ends when',
            'one fighter reaches 0 HP.',
        ],
        controls=[
            'A / D            Move left / right',
            'SPACE            Jump',
            'J                Punch',
            'K                Kick',
            'L                Block',
            'ESC              Pause',
        ],
        tips=[
            '• Block reduces damage',
            '• A landed punch or kick stuns the opponent',
            '• Stay mobile',
        ],
    )
FPS      = 30
ARENA_W  = 68
SW, SH   = 9, 6
WALK     = 1.4
JV0      = 6.0
GRAV     = 0.8
MINSEP   = SW + 1
PR, KR   = 13, 16
PD, KD   = 6, 8
BM       = 0.08
MHP      = 100
STUN_DUR = 18
NEED     = 2
ADUR     = {'idle':14,'walk':7,'punch':11,'kick':11,'block':1,
            'hurt':8,'crouch':1,'jump':1,'ko':1,'victory':16}
TITLE_ART = [
    r"  ____ _       _  _   _ ____  ___ ",
    r" / ___| |     / \| | | |  _ \| __|",
    r"| |   | |    / _ \ | | | | | | _| ",
    r"| |___| |___/ ___ \ |_| | |_| | |___",
    r" \____|_____/_/   \_\___/|____/|____|",
    r"",
    r" _____ ___ ____ _  _ _____ ___ ____  ",
    r"|  ___|_ _/ ___| || |_   _| __| __ \ ",
    r"| |_   | | |  _| || | | | | _||  __/ ",
    r"|  _|  | | |_| |__   _|| | | |_| |   ",
    r"|_|   |___\____|  |_|  |_| |___|_|   ",
]
CHARS = [
    {
        'name': 'WARRIOR', 'title': 'Iron Fist',
        'desc': 'Heavy power, tough defense',
        'cp': 1, 'power': 1.3, 'speed': 0.85, 'defense': 1.2,
        'portrait': [
            " ╔═╦═╗  ",
            " ║█▀█║  ",
            " ╚═╩═╝  ",
            "╔╩═══╩╗ ",
            "║█████║ ",
            "╠══╦══╣ ",
            "║  ║  ║ ",
            "╚══╩══╝ ",
        ],
        'stats': [('PWR','████████░░'),('SPD','█████░░░░░'),('DEF','████████░░')],
    },
    {
        'name': 'NINJA', 'title': 'Shadow Step',
        'desc': 'Lightning fast, elusive',
        'cp': 2, 'power': 0.85, 'speed': 1.5, 'defense': 0.8,
        'portrait': [
            "  ╭───╮  ",
            "  │·_·│  ",
            "  ╰━━━╯  ",
            "  ─╫───  ",
            " ╱ ║   ╲ ",
            "╱  ║    ╲",
            "  ┄║┄    ",
            " ╱ ║ ╲   ",
        ],
        'stats': [('PWR','█████░░░░░'),('SPD','██████████'),('DEF','████░░░░░░')],
    },
    {
        'name': 'SAMURAI', 'title': 'Steel Blade',
        'desc': 'Long reach, disciplined',
        'cp': 4, 'power': 1.1, 'speed': 0.95, 'defense': 1.05,
        'portrait': [
            " ╔╦═╦╗  ",
            " ║▀█▀║  ",
            " ╚╩═╩╝  ",
            "  ═╪═   ",
            " ─═╪══► ",
            "  ╱╪    ",
            " ╱ ╪    ",
            "╱  ╪    ",
        ],
        'stats': [('PWR','███████░░░'),('SPD','██████░░░░'),('DEF','███████░░░')],
    },
    {
        'name': 'MONK', 'title': 'Stone Palm',
        'desc': 'Balanced, deadly counters',
        'cp': 3, 'power': 1.0, 'speed': 1.1, 'defense': 1.1,
        'portrait': [
            "  ≋≋≋≋  ",
            "  (^‿^)  ",
            " ╔╝ ╔╝  ",
            " ╚╦═╩╗  ",
            "  ║░░║  ",
            " ╱║  ║╲ ",
            "╱ ║  ║ ╲",
            "  ╙──╜  ",
        ],
        'stats': [('PWR','██████░░░░'),('SPD','███████░░░'),('DEF','███████░░░')],
    },
]
def frm(*rows, w=SW, h=SH):
    out = [(r + ' '*w)[:w] for r in rows]
    while len(out) < h: out.append(' '*w)
    return out[:h]

def _mirror(frames):
    t={'(':')',')':'(','/':'\\','\\':'/','>':'<','<':'>','[':']',']':'[',
       '╔':'╗','╗':'╔','╚':'╝','╝':'╚','╠':'╣','╣':'╠','╭':'╮','╮':'╭',
       '◄':'►','►':'◄','╱':'╲','╲':'╱'}
    return [[''.join(t.get(c,c) for c in reversed(row)) for row in fr] for fr in frames]

# ── WARRIOR sprites ── stocky, heavy, armoured ──────────────────────────────
_WAR1 = {
    'idle':   [frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ '),
               frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║▓▓▓║ ',' ╠═╦═╣ ',' ╙─╨─╜ ')],
    'walk':   [frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ','╱╙─╨─╜  '),
               frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ','  ╙─╨─╜╲')],
    'punch':  [frm(' ╔═╦═╗ ',' ║◘▀◘╠═','  ╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ '),
               frm(' ╔═╦═╗ ',' ║◘▀◘╠══►',' ╠═╩═╣',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ '),
               frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ ')],
    'kick':   [frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║███╠ ',' ╠═╦═╣ ',' ╙─╨   '),
               frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║███╠══►',' ╠═╦═╣',' ╙─╨   '),
               frm(' ╔═╦═╗ ',' ║◘▀◘║ ',' ╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ ')],
    'block':  [frm(' ╔═╦═╗ ','╔║◘▀◘║ ','╚╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ ')],
    'hurt':   [frm(' ╔═╦═╗ ',' ║✕▀✕║ ',' ╠═╩═╣ ',' ║▓▒▓║ ',' ╠═╦═╣ ',' ╙─╨─╜ '),
               frm(' ╔═╦═╗ ',' ║×▀×║ ',' ╠═╩═╣ ',' ║▒░▒║ ',' ╠═╦═╣ ',' ╙─╨─╜ ')],
    'crouch': [frm('       ',' ╔═╦═╗ ',' ║◘▀◘║ ','═╩╠═╩╣ ',' ╙─╨─╜ ','       ')],
    'jump':   [frm(' ╔═╦═╗ ',' ║◘▀◘║ ','╱╠═╩═╣╲','  ║███  ',' ╙   ╜ ','       ')],
    'ko':     [frm('       ','       ',' ╔═╦═╗ ',' ║×▀×║ ','═╩╩═╩╩═','▓▓▓▓▓▓▓')],
    'victory':[frm(' ╔═╦═╗ ',' ║◘▀◘║ ','╱╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ '),
               frm(' ╔═╦═╗ ',' ║◘▀◘║╲',' ╠═╩═╣ ',' ║███║ ',' ╠═╦═╣ ',' ╙─╨─╜ ')],
}

# ── NINJA sprites ── thin, fast, wraith-like ─────────────────────────────────
_NIN1 = {
    'idle':   [frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','   ╫   ','  ╱ ╲  ','       '),
               frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','   ╫   ','  ╲ ╱  ','       ')],
    'walk':   [frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','  ─╫   ','  ╱╲   ','╱      '),
               frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','   ╫─  ','   ╱╲  ','     ╲ ')],
    'punch':  [frm('  ╭─╮  ','  │·│  ','  ╰─╯─ ','   ╫   ','  ╱ ╲  ','       '),
               frm('  ╭─╮  ','  │·│─►','  ╰─╯  ','   ╫   ','  ╱ ╲  ','       '),
               frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','   ╫   ','  ╱ ╲  ','       ')],
    'kick':   [frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','   ╫   ','  ╱╱   ','  ╱    '),
               frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','   ╫╱  ','  ╱ ╱══►','       '),
               frm('  ╭─╮  ','  │·│  ','  ╰─╯  ','   ╫   ','  ╱ ╲  ','       ')],
    'block':  [frm('  ╭─╮  ','  │·│  ','╔─╰─╯  ','╚══╫   ','   ╲   ','       ')],
    'hurt':   [frm('  ╭─╮  ','  │×│  ','  ╰─╯  ','  ~╫~  ',' ╲ ╱ ╱ ','       '),
               frm('  ╭─╮  ','  │✕│  ','  ╰─╯  ','  ~╫~  ',' ╱ ╲ ╲ ','       ')],
    'crouch': [frm('       ','  ╭─╮  ','  │·│  ','──╰╫╯──','  ╱ ╲  ','       ')],
    'jump':   [frm('  ╭─╮  ','╲ │·│ ╱','  ╰─╯  ','   ╫   ','  ╱╲   ','       ')],
    'ko':     [frm('       ','       ','  ╭─╮  ','  │×│  ','~~╰─╯~~','▒░░░░▒▒')],
    'victory':[frm('  ╭─╮  ','╲ │·│  ','  ╰─╯╱ ','   ╫   ','  ╱ ╲  ','       '),
               frm('  ╭─╮  ','  │·│╱ ','  ╰─╯  ','   ╫   ','  ╱ ╲  ','       ')],
}

# ── SAMURAI sprites ── upright, sword extended ───────────────────────────────
_SAM1 = {
    'idle':   [frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝   ','  ╪═══ ','  ║    ','  ╨    '),
               frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝   ','  ╪══  ','  ║    ','  ╨    ')],
    'walk':   [frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝   ','  ╪═══ ','  ╱    ','╱      '),
               frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝   ','  ╪═══ ','  ║╲   ','    ╲  ')],
    'punch':  [frm(' ╔╦╗   ',' ║▀║─  ',' ╚╩╝   ','  ╪════','  ║    ','  ╨    '),
               frm(' ╔╦╗   ',' ║▀║══►',' ╚╩╝   ','  ╪════','  ║    ','  ╨    '),
               frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝   ','  ╪═══ ','  ║    ','  ╨    ')],
    'kick':   [frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝╱  ','  ╪    ','  ║╱   ','       '),
               frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝   ','  ╪╱═══►','  ║    ','       '),
               frm(' ╔╦╗   ',' ║▀║   ',' ╚╩╝   ','  ╪═══ ','  ║    ','  ╨    ')],
    'block':  [frm(' ╔╦╗   ',' ║▀║   ','╔╚╩╝   ','║ ╪════','╚╗║    ','  ╨    ')],
    'hurt':   [frm(' ╔╦╗   ',' ║×║   ',' ╚╩╝   ','~ ╪ ~  ',' ╱╲    ','       '),
               frm(' ╔╦╗   ',' ║✕║   ',' ╚╩╝   ','~~╪~~  ',' ╲╱    ','       ')],
    'crouch': [frm('       ',' ╔╦╗   ',' ║▀║   ','═╚╩╝══ ','  ╪═══ ','       ')],
    'jump':   [frm(' ╔╦╗   ','╱║▀║   ',' ╚╩╝╲  ','  ╪═══ ','       ','       ')],
    'ko':     [frm('       ','       ',' ╔╦╗   ',' ║×║   ','═╩╩╩══ ','▒▓▒▓▒▓▒')],
    'victory':[frm(' ╔╦╗   ','╱║▀║   ',' ╚╩╝   ','  ╪════','  ║    ','  ╨    '),
               frm(' ╔╦╗╱  ',' ║▀║   ',' ╚╩╝   ','  ╪════','  ║    ','  ╨    ')],
}

# ── MONK sprites ── wide stance, open palms ──────────────────────────────────
_MON1 = {
    'idle':   [frm('  ≈≈≈  ','  (^‿^)','  )│(  ','─(│ │)─','  │ │  ','  ╙ ╜  '),
               frm('  ≈≈≈  ','  (‿^‿)','  )│(  ','─(│ │)─','  │ │  ','  ╙ ╜  ')],
    'walk':   [frm('  ≈≈≈  ','  (^‿^)','  )│(  ','─(│ │)─','  │╱   ','╱      '),
               frm('  ≈≈≈  ','  (^‿^)','  )│(  ','─(│ │)─','   ╲│  ','     ╲ ')],
    'punch':  [frm('  ≈≈≈  ','  (^‿^)','  )│══ ','─(│ │)─','  │ │  ','  ╙ ╜  '),
               frm('  ≈≈≈  ','  (^‿^)','  )│═══►','(│ │)─','  │ │  ','  ╙ ╜  '),
               frm('  ≈≈≈  ','  (^‿^)','  )│(  ','─(│ │)─','  │ │  ','  ╙ ╜  ')],
    'kick':   [frm('  ≈≈≈  ','  (^‿^)','  )│(  ','─(│ │╱ ','  │╱   ','       '),
               frm('  ≈≈≈  ','  (^‿^)','  )│(  ','─(│ │═══►','  │    ','       '),
               frm('  ≈≈≈  ','  (^‿^)','  )│(  ','─(│ │)─','  │ │  ','  ╙ ╜  ')],
    'block':  [frm('  ≈≈≈  ','  (^‿^)','╔═)│(  ','╚═(│ │)─','  │ │  ','  ╙ ╜  ')],
    'hurt':   [frm('  ≈≈≈  ','  (×‿×)','~ )│( ~','─(│ │)─','  ╲ ╱  ','       '),
               frm('  ≈≈≈  ','  (✕‿✕)','~~)│(~~','─(│ │)─','  ╱ ╲  ','       ')],
    'crouch': [frm('       ','  ≈≈≈  ','  (^‿^)','═)╞═╡(═','  ╙ ╜  ','       ')],
    'jump':   [frm('  ≈≈≈  ','╲ (^‿^)╱','  )│(  ','  │ │  ','       ','       ')],
    'ko':     [frm('       ','       ','  ≈≈≈  ','  (×‿×)','~~)═(~~','▒░▒░▒░▒')],
    'victory':[frm('  ≈≈≈  ','╲ (^‿^)','  )│(  ','─(│ │)─','  │ │  ','  ╙ ╜  '),
               frm('  ≈≈≈  ','  (^‿^)╱','  )│(  ','─(│ │)─','  │ │  ','  ╙ ╜  ')],
}

# Per-character sprite lookup (P1 facing right)
CHAR_SPRITES_P1 = [_WAR1, _NIN1, _SAM1, _MON1]

# Mirror for P2 (facing left)
CHAR_SPRITES_P2 = [
    {k: _mirror(v) for k, v in sp.items()}
    for sp in CHAR_SPRITES_P1
]

# Fallback generic sprites still used if index out of range
SP1 = _WAR1
SP2 = {k: _mirror(v) for k, v in SP1.items()}
class Fighter:
    def __init__(self, name, x, cp, char_def, char_idx=0, is_p2=False, is_ai=False):
        self.name=name; self.x=float(x); self.y=0.0; self.vy=0.0
        self.cp=cp; self.is_p2=is_p2; self.is_ai=is_ai
        # Use per-character sprite tables; fall back to generic if index missing
        idx = char_idx % len(CHAR_SPRITES_P1)
        self.sp = CHAR_SPRITES_P2[idx] if is_p2 else CHAR_SPRITES_P1[idx]
        self.power=char_def['power']; self.speed=char_def['speed']
        self.defense=char_def['defense']
        self.hp=MHP; self.velx=0.0; self.grounded=True
        self.state='idle'; self.af=0; self.at=0
        self.stun=0; self.hit_dealt=False; self.ai_cd=0

    def set(self,s):
        if self.state==s: return
        self.state=s; self.af=0; self.at=0; self.hit_dealt=False

    def tick_anim(self):
        spd=ADUR.get(self.state,6)
        self.at+=1
        if self.at>=spd:
            self.at=0
            frames=self.sp.get(self.state,self.sp['idle'])
            self.af=(self.af+1)%len(frames)
            if self.state in ('punch','kick') and self.af==0: return True
        return False

    def frame(self):
        frames=self.sp.get(self.state,self.sp['idle'])
        return frames[self.af%len(frames)]

    def hit_active(self): return self.state in ('punch','kick') and self.af==1
    def alive(self): return self.hp>0

    def can_be_hit_by(self, atk_state):
        """Crouch dodges punches. Jump (high enough) dodges kicks."""
        if atk_state=='punch' and self.state=='crouch':
            return False
        if atk_state=='kick' and self.y>3.5:
            return False
        return True

    def take_hit(self, dmg):
        if not self.alive() or self.state=='ko': return 0
        m=BM if self.state=='block' else 1.0
        actual=max(1,int(dmg*m*self.defense))
        self.hp=max(0,self.hp-actual)
        if self.hp==0:            self.set('ko');   self.stun=9999
        elif self.state!='block': self.set('hurt'); self.stun=STUN_DUR
        return actual

    def physics(self, other):
        if not self.grounded:
            self.vy-=GRAV; self.y+=self.vy
            if self.y<=0:
                self.y=0.0; self.vy=0.0; self.grounded=True
                if self.state=='jump': self.set('idle')
        self.x+=self.velx
        self.x=max(0.0,min(ARENA_W,self.x))
        dx=other.x-self.x
        if abs(dx)<MINSEP:
            push=(MINSEP-abs(dx))/2
            if dx>=0: self.x-=push; other.x+=push
            else:     self.x+=push; other.x-=push
        self.x=max(0.0,min(ARENA_W,self.x))
        other.x=max(0.0,min(ARENA_W,other.x))

    def player_input(self, keys, mouse_punch=False, mouse_kick=False):
        if self.state in ('punch','kick'): return
        ws=WALK*self.speed
        self.velx=0.0; moving=False
        if ord('a') in keys: self.velx=-ws; moving=True
        if ord('d') in keys: self.velx= ws; moving=True
        jump=ord('w') in keys or ord(' ') in keys
        if jump and self.grounded:
            self.vy=JV0; self.grounded=False; self.set('jump')
        if ord('s') in keys and self.grounded: self.set('crouch'); moving=True
        if   ord('j') in keys or mouse_punch: self.set('punch')
        elif ord('k') in keys or mouse_kick:  self.set('kick')
        elif ord('l') in keys: self.set('block')
        elif moving and self.grounded and self.state not in ('crouch',): self.set('walk')
        elif not moving and self.grounded and self.state not in \
             ('punch','kick','block','jump','crouch','hurt','ko'): self.set('idle')

    def ai_input(self, opp):
        self.ai_cd-=1
        dx=opp.x-self.x; dist=abs(dx)
        ws=WALK*self.speed; self.velx=0.0
        if self.state not in ('punch','kick','block'):
            if   dist>KR+4: self.velx=ws*0.65*(1 if dx>0 else -1); self.set('walk') if self.grounded else None
            elif dist>PR+3: self.velx=ws*0.3*(1 if dx>0 else -1)
        if self.ai_cd<=0:
            # Slower reaction: 18-32 frames (0.6–1.1 s) between decisions
            self.ai_cd=random.randint(18,32)
            if self.state in ('punch','kick'): return
            r=random.random()
            if dist<=PR:
                # punch 22%, kick 18%, block 15%, idle the rest
                if   r<0.22: self.set('punch'); self.velx=0
                elif r<0.40: self.set('kick');  self.velx=0
                elif r<0.55: self.set('block')
                else:        self.set('idle')
            elif dist<=KR+3:
                # Only kick or jump 25% of the time at medium range
                if r<0.18: self.set('kick'); self.velx=0
                elif r<0.25 and self.grounded:
                    self.vy=JV0; self.grounded=False; self.set('jump')

    def update(self, other, keys=None, mp=False, mk=False):
        if self.stun>0:
            self.stun-=1
            if self.stun==0 and self.state=='hurt': self.set('idle')
        self.velx=0.0
        frozen=self.state in ('ko','hurt') and self.stun>0
        if not frozen:
            if self.is_ai:         self.ai_input(other)
            elif keys is not None: self.player_input(keys,mp,mk)
        if self.state in ('punch','kick'):
            if self.tick_anim(): self.set('idle')
        else: self.tick_anim()
        self.physics(other)
class Game:
    def __init__(self, p1_char, p2_char):
        self.p1_char=p1_char; self.p2_char=p2_char
        self.p1w=0; self.p2w=0; self.rnd=1
        self.msg=''; self.msg_t=0; self.flash=0; self.sparks=[]
        self.over=False
        self._new()

    def _new(self):
        c1=CHARS[self.p1_char]; c2=CHARS[self.p2_char]
        self.p1=Fighter(c1['name'],14,c1['cp'],c1,char_idx=self.p1_char,is_p2=False,is_ai=False)
        self.p2=Fighter(c2['name'],54,c2['cp'],c2,char_idx=self.p2_char,is_p2=True, is_ai=True)
        self.over=False; self.sparks=[]

    def show(self,m,d=120): self.msg=m; self.msg_t=d

    def _hits(self):
        for a,d in [(self.p1,self.p2),(self.p2,self.p1)]:
            if a.hit_active() and not a.hit_dealt:
                rng=KR if a.state=='kick' else PR
                if abs(d.x-a.x)<=rng and d.can_be_hit_by(a.state):
                    dmg=KD if a.state=='kick' else PD
                    actual=d.take_hit(int(dmg*a.power))
                    a.hit_dealt=True; self.flash=5
                    if actual:
                        cx=1+int(d.x/ARENA_W*60); cy=8
                        spark_pool = list('✦✧★✸✺✻◈⊛*·×+◆◇▪▫')
                        # central impact flash
                        self.sparks.append([cx, cy, 0, 0, '✸', 4])
                        for _ in range(9):
                            self.sparks.append([cx+(random.random()-.5)*8,
                                                cy+(random.random()-.5)*4,
                                                (random.random()-.5)*2.2,
                                                -(random.random()*1.6),
                                                random.choice(spark_pool), 9])

    def update(self, keys, mp=False, mk=False):
        if self.over: return
        self.p1.update(self.p2,keys,mp,mk)
        self.p2.update(self.p1)
        self._hits()
        self.sparks=[s for s in self.sparks if s[5]>0]
        for s in self.sparks: s[0]+=s[2]; s[1]+=s[3]; s[3]+=.15; s[5]-=1
        if self.msg_t>0: self.msg_t-=1
        if self.flash>0: self.flash-=1
        p1_ko = not self.p1.alive()
        p2_ko = not self.p2.alive()
        if (p1_ko or p2_ko) and not self.over:
            self.over = True
            if p1_ko and p2_ko:
                # Simultaneous KO: tiebreak in favour of p2
                self.p2w += 1; self.p2.set('victory')
                self.show(f'  {self.p2.name} WINS!  ')
            elif p1_ko:
                self.p2w += 1; self.p2.set('victory')
                self.show(f'  {self.p2.name} WINS!  ')
            else:
                self.p1w += 1; self.p1.set('victory')
                self.show(f'  {self.p1.name} WINS!  ')

    def next_round(self):
        if self.p1w>=NEED or self.p2w>=NEED: return False
        self.rnd+=1; self._new(); self.show(f'  ROUND {self.rnd}  ',90); return True
def make_put(scr, H, W):
    def put(r,c,s,a=0):
        try:
            if 0<=r<H-1 and 0<=c<W: scr.addstr(r,c,s[:W-c],a)
        except curses.error: pass
    return put
def draw_intro(scr, H, W, tick):
    put=make_put(scr,H,W)
    scr.erase()
    P=curses.color_pair

    put(0,0,'╔'+'═'*(W-2)+'╗',P(5))
    put(H-1,0,'╚'+'═'*(W-2)+'╝',P(5))
    for r in range(1,H-1):
        put(r,0,'║',P(5)); put(r,W-1,'║',P(5))

    start_row=max(1,(H-len(TITLE_ART))//2-1)
    for i,line in enumerate(TITLE_ART):
        col=max(1,(W-len(line))//2)
        attr=P(1)|curses.A_BOLD if i<4 else P(4)|curses.A_BOLD
        put(start_row+i,col,line,attr)

    fr_idx=(tick//14)%2
    p1fr=CHAR_SPRITES_P1[0]['idle'][fr_idx]
    p2fr=CHAR_SPRITES_P2[2]['idle'][fr_idx]
    fy=H-8
    for i,row in enumerate(p1fr):
        put(fy+i,3,row,P(1)|curses.A_BOLD)
    for i,row in enumerate(p2fr):
        put(fy+i,W-SW-3,row,P(2)|curses.A_BOLD)

    if (tick//15)%2==0:
        msg='  ★  PRESS SPACE TO START  ★  '
        put(H-3,(W-len(msg))//2,msg,P(4)|curses.A_BOLD)

    put(H-2,(W-30)//2,'  A Claude Code Production · 2025  ',P(5))
    scr.refresh()
def draw_select(scr, H, W, sel, tick):
    put=make_put(scr,H,W)
    P=curses.color_pair
    scr.erase()

    # outer frame
    put(0,0,'╔'+'═'*(W-2)+'╗',P(5)|curses.A_BOLD)
    put(H-1,0,'╚'+'═'*(W-2)+'╝',P(5)|curses.A_BOLD)
    for r in range(1,H-1):
        put(r,0,'║',P(5)); put(r,W-1,'║',P(5))

    # title
    title=' ★  CHOOSE YOUR FIGHTER  ★ '
    put(0,(W-len(title))//2,title,P(4)|curses.A_BOLD)
    put(2,0,'╠'+'═'*(W-2)+'╣',P(5)|curses.A_BOLD)
    put(1,(W-len(title))//2,title,P(4)|curses.A_BOLD)

    PW=14   # inner portrait width (chars inside box)
    BW=PW+2 # box width including side borders
    GAP=2
    total=len(CHARS)*BW+(len(CHARS)-1)*GAP
    start_col=max(1,(W-total)//2)

    for i,ch in enumerate(CHARS):
        cx=start_col+i*(BW+GAP)
        selected=(i==sel)
        blink=(tick//8)%2==0
        if selected:
            bc=P(ch['cp'])|curses.A_BOLD
            hc=P(ch['cp'])|curses.A_BOLD|(curses.A_REVERSE if blink else 0)
        else:
            bc=P(5)
            hc=P(5)

        box_top=3

        # portrait box
        TL,TR,BL,BR,SI,TOP,BOT = ('╔','╗','╚','╝','║','═','═') if selected else ('┌','┐','└','┘','│','─','─')
        put(box_top,   cx, TL+TOP*PW+TR, bc)
        for r in range(8):
            row_str=ch['portrait'][r] if r<len(ch['portrait']) else ''
            inner=row_str.center(PW)[:PW]
            put(box_top+1+r, cx, SI+inner+SI, P(ch['cp'])|curses.A_BOLD if selected else P(5))
        put(box_top+9, cx, BL+BOT*PW+BR, bc)

        # name + title beneath box
        put(box_top+10, cx, ('▶' if selected else ' ')+ch['name'].center(PW)+('◀' if selected else ' '), hc)
        put(box_top+11, cx+1, ch['title'].center(PW), P(ch['cp']) if selected else P(5))
        put(box_top+12, cx+1, ch['desc'][:PW].center(PW), P(5)|curses.A_DIM)

        # stat bars
        put(box_top+14, cx+1, '─'*PW, P(5)|curses.A_DIM)
        for si,(stat,bar) in enumerate(ch['stats']):
            bar_display=bar[:10]
            put(box_top+15+si, cx+1, f'{stat}:{bar_display}', P(3)|curses.A_BOLD if selected else P(5))

    ctrl=' ◄ ► to select    SPACE to confirm '
    put(H-2,(W-len(ctrl))//2,ctrl,P(4)|curses.A_BOLD)
    scr.refresh()
_BIG = {
    '3': ['╔══╗','  ═╣','╔══╣','╚══╝'],
    '2': ['╔══╗','╔══╝','║   ','╚══╝'],
    '1': ['  ╗ ','  ║ ','  ║ ','  ╩ '],
    'F': ['╔══╗','║╔═╣','║╚═╗','╩ ╩ '],
    'I': ['╔╦╗','  ║ ','  ║ ','═╩═ '],
    'G': ['╔══╗','║ ╔╗','║ ╚╣','╚══╝'],
    'H': ['║  ║','╠══╣','║  ║','╩  ╩'],
    'T': ['╦══╦','  ╬  ','  ║  ','  ╩  '],
    '!': [' ║ ',' ║ ','   ',' ● '],
    'R': ['╔═╗ ','╠╦╝ ','║╚╗ ','╩ ╚╗'],
    'O': ['╔══╗','║  ║','║  ║','╚══╝'],
    'U': ['║  ║','║  ║','║  ║','╚══╝'],
    'N': ['╔╗║ ','║╠╣ ','║╚╣ ','╩ ╚╗'],
    'D': ['╔══╗','║  ║','║  ║','╚══╝'],
    ' ': ['    ','    ','    ','    '],
}

def _big_text(text):
    """Render text using 4-row tall big characters. Returns list of 4 strings."""
    chars = [_BIG.get(c, _BIG[' ']) for c in text.upper()]
    w = max((len(r) for ch in chars for r in ch), default=4)
    rows = []
    for line_i in range(4):
        row = '  '.join(ch[line_i] if line_i < len(ch) else ' '*4 for ch in chars)
        rows.append(row)
    return rows

def draw_countdown(scr, H, W, phase):
    # phase: 3=show 3, 2=show 2, 1=show 1, 0=FIGHT!
    put=make_put(scr,H,W)
    P=curses.color_pair
    scr.erase()

    # background border
    put(0,0,'╔'+'═'*(W-2)+'╗',P(5))
    put(H-1,0,'╚'+'═'*(W-2)+'╝',P(5))
    for r in range(1,H-1):
        put(r,0,'║',P(5)); put(r,W-1,'║',P(5))

    if phase>0:
        text=str(phase)
        color=[P(2),P(4),P(3)][phase-1]|curses.A_BOLD
    else:
        text='FIGHT!'
        color=P(1)|curses.A_BOLD

    lines = _big_text(text)
    art_h = len(lines) + 4   # 2 padding rows top/bottom
    art_w = max(len(l) for l in lines) + 6
    mr = H//2 - art_h//2
    mc = (W - art_w) // 2

    put(mr,   mc,'╔'+'═'*(art_w-2)+'╗',P(5)|curses.A_BOLD)
    put(mr+1, mc,'║'+'░'*(art_w-2)+'║',P(5))
    for i, line in enumerate(lines):
        put(mr+2+i, mc,'║  '+line.center(art_w-6)+'  ║', color)
    put(mr+2+len(lines), mc,'║'+'░'*(art_w-2)+'║',P(5))
    put(mr+3+len(lines), mc,'╚'+'═'*(art_w-2)+'╝',P(5)|curses.A_BOLD)

    scr.refresh()
AT=5   # arena top row (rows 0-4 = HUD)
def _hbar(hp, maxhp, w, fill='█', empty='░'):
    """Return a health bar string of width w."""
    filled = max(0, round(w * hp / maxhp))
    return fill * filled + empty * (w - filled)

def draw_fight(scr, g, W, H):
    put=make_put(scr,H,W)
    P=curses.color_pair
    GR=H-5; AH=GR-AT   # arena rows AT..GR-1
    scr.erase()

    # ── outer frame ──────────────────────────────────────────────────────────
    put(0,0,'╔'+'═'*(W-2)+'╗',P(5)|curses.A_BOLD)
    put(4,0,'╠'+'═'*(W-2)+'╣',P(5)|curses.A_BOLD)
    for r in range(AT,GR):
        put(r,0,'║',P(5))
        put(r,W-1,'║',P(5))
    put(H-5,0,'╠'+'═'*(W-2)+'╣',P(5)|curses.A_BOLD)
    put(H-4,0,'╠'+'─'*(W-2)+'╣',P(5)|curses.A_DIM)
    put(H-3,0,'║',P(5)); put(H-3,W-1,'║',P(5))
    put(H-2,0,'╚'+'═'*(W-2)+'╝',P(5))

    # ── HUD row 0: title bar ─────────────────────────────────────────────────
    title_bar = '║' + '▓▒░' + ' ★ CLAUDE FIGHTER ★ '.center(W-8) + '░▒▓' + '║'
    put(0,0,title_bar,P(2)|curses.A_BOLD)

    # ── HUD row 1: health bars ────────────────────────────────────────────────
    # Layout: ║ NAME ████████░░ HP:NNN ▐VS▌ NNN:HP ░░████████ NAME ║
    MARGIN = 2
    center_label = '╠ VS ╣'
    cl = len(center_label)
    bar_space = (W - 2 - 2*MARGIN - cl) // 2  # space each side for name+bar+number
    name_w = 8
    num_w  = 7  # " HP:NNN"
    bar_w  = max(4, bar_space - name_w - num_w)

    cp1 = 3 if g.p1.hp/MHP > 0.3 else 4
    cp2 = 3 if g.p2.hp/MHP > 0.3 else 4

    left_col  = 1 + MARGIN
    center_col = W // 2 - cl // 2

    # P1 name + bar (grows right)
    p1_name = g.p1.name[:name_w].ljust(name_w)
    p1_bar  = _hbar(g.p1.hp, MHP, bar_w)
    p1_num  = f' {g.p1.hp:3d}HP'
    put(1, left_col, p1_name, P(g.p1.cp)|curses.A_BOLD)
    put(1, left_col+name_w, p1_bar, P(cp1)|curses.A_BOLD)
    put(1, left_col+name_w+bar_w, p1_num, P(cp1))

    # Center VS marker
    put(1, center_col, center_label, P(7)|curses.A_BOLD)

    # P2 name + bar (grows left, mirrored)
    p2_name = g.p2.name[:name_w].rjust(name_w)
    p2_bar  = _hbar(g.p2.hp, MHP, bar_w, fill='█', empty='░')
    p2_num  = f'HP:{g.p2.hp:3d} '
    p2_bar_start = center_col + cl
    put(1, p2_bar_start, p2_num, P(cp2))
    put(1, p2_bar_start + len(p2_num), p2_bar, P(cp2)|curses.A_BOLD)
    put(1, p2_bar_start + len(p2_num) + bar_w, p2_name, P(g.p2.cp)|curses.A_BOLD)

    put(1, 0, '║', P(5)|curses.A_BOLD)
    put(1, W-1, '║', P(5)|curses.A_BOLD)

    # ── HUD row 2: thin decorative bar ───────────────────────────────────────
    put(2, 0, '║', P(5)); put(2, W-1, '║', P(5))
    wins = f'  ROUND {g.rnd}   {"▣"*g.p1w}{"□"*(NEED-g.p1w)} P1  ·  P2 {"□"*(NEED-g.p2w)}{"▣"*g.p2w}  '
    put(2, (W-len(wins))//2, wins, P(5)|curses.A_BOLD)

    # ── HUD row 3: HP numbers + stage name ───────────────────────────────────
    put(3, 0, '║', P(5)); put(3, W-1, '║', P(5))
    put(3, 2, f'HP:{g.p1.hp:3d}', P(cp1)|curses.A_BOLD)
    stage = '── DOJO OF FATE ──'
    put(3, (W-len(stage))//2, stage, P(5)|curses.A_DIM)
    put(3, W-9, f'HP:{g.p2.hp:3d}', P(cp2)|curses.A_BOLD)

    # ── arena floor — textured ───────────────────────────────────────────────
    floor_chars = '▓▒░▒'
    floor_line  = ''.join(floor_chars[i%4] for i in range(W-2))
    put(GR,   0, '╠', P(5)|curses.A_BOLD); put(GR,   W-1, '╣', P(5)|curses.A_BOLD)
    put(GR,   1, floor_line, P(5)|curses.A_DIM)
    if GR+1 < H-5:
        put(GR+1, 0, '║', P(5)); put(GR+1, W-1, '║', P(5))
        shadow = '░' * (W-2)
        put(GR+1, 1, shadow, P(5)|curses.A_DIM)

    # ── fighters ─────────────────────────────────────────────────────────────
    peak=JV0*JV0/(2*GRAV)
    for f in (g.p1,g.p2):
        fr=f.frame()
        col=1+round(f.x/ARENA_W*max(1,W-2-SW)); col=max(1,min(W-1-SW,col))
        joff=0 if f.grounded else min(round(f.y/peak*(AH-SH-1)),AH-SH-1)
        top=GR-SH-joff
        cp=P(f.cp)|curses.A_BOLD
        if f.state=='ko': cp=P(5)|curses.A_DIM
        if g.flash>0 and f.state in ('hurt','ko') and f.state!='ko':
            cp=P(6)|curses.A_BOLD|curses.A_REVERSE
        for i,row in enumerate(fr):
            r=top+i
            if AT<=r<GR: put(r,col,row,cp)

    # ── spark hit effects ─────────────────────────────────────────────────────
    spark_chars = ['✦','✧','★','✸','✺','✻','◈','⊛']
    for s in g.sparks:
        r,c=round(s[1]),round(s[0])
        if AT<=r<GR and 0<c<W-1:
            put(r,c,s[4],P(4)|curses.A_BOLD)

    # ── round/ko message overlay ──────────────────────────────────────────────
    if g.msg_t>0:
        m=g.msg.strip()
        # Build a larger, more dramatic box for major announcements
        is_big = any(x in m for x in ('WINS','KO','FIGHT','ROUND'))
        mr=AT+AH//2
        if is_big:
            pad=4
            mw=len(m)+pad*2
            mc=W//2-mw//2
            put(mr-2,mc,'╔'+'═'*mw+'╗',P(7)|curses.A_BOLD)
            put(mr-1,mc,'║'+'░'*mw+'║',P(7))
            put(mr,  mc,'║'+'  '*pad+m+'  '*pad+'║',P(7)|curses.A_BOLD)
            put(mr+1,mc,'║'+'░'*mw+'║',P(7))
            put(mr+2,mc,'╚'+'═'*mw+'╝',P(7)|curses.A_BOLD)
            if g.over:
                hint='  [ ENTER = next round   ESC = quit ]  '
                put(mr+4,(W-len(hint))//2,hint,P(5))
        else:
            mw=len(m)+4; mc=W//2-mw//2
            put(mr-1,mc,'╔'+'═'*(mw-2)+'╗',P(7))
            put(mr,  mc,'║ '+m+' ║',P(7)|curses.A_BOLD)
            put(mr+1,mc,'╚'+'═'*(mw-2)+'╝',P(7))

    # ── control bar ──────────────────────────────────────────────────────────
    ctrl='A/D:Move  SPC:Jump  S:Crouch  J:Punch  K:Kick  L:Block  ESC:Pause  Q:Quit'
    put(H-3,1,ctrl[:W-2].center(W-2),P(5)|curses.A_DIM)
    scr.refresh()
def main(scr):
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()

    try: curses.mousemask(curses.ALL_MOUSE_EVENTS|curses.REPORT_MOUSE_POSITION)
    except curses.error: pass

    state=INTRO; sel=0; p1_char=0; _sub=[None]
    countdown_phase=3; countdown_timer=0
    game=None; tick=0
    nxt=time.perf_counter()

    while True:
        now=time.perf_counter()
        if now<nxt: time.sleep(max(0,nxt-now-.001)); continue
        nxt+=1/FPS; tick+=1

        H,W=scr.getmaxyx()
        keys=set(); mp=False; mk=False
        while True:
            k=scr.getch()
            if k==-1: break
            if k==curses.KEY_MOUSE:
                try:
                    _,_,_,_,bst=curses.getmouse()
                    if bst&curses.BUTTON1_PRESSED: mp=True
                    if bst&curses.BUTTON3_PRESSED: mk=True
                except curses.error: pass
            else: keys.add(k)

        if 27 in keys:
            if   state==FIGHT: state=PAUSE
            elif state==PAUSE: state=FIGHT
            else: break

        if state==INTRO:
            draw_intro(scr,H,W,tick)
            if ord(' ') in keys: state=SELECT

        elif state==SELECT:
            draw_select(scr,H,W,sel,tick)
            if curses.KEY_LEFT  in keys: sel=(sel-1)%len(CHARS)
            if curses.KEY_RIGHT in keys: sel=(sel+1)%len(CHARS)
            if ord(' ') in keys:
                p1_char=sel
                # AI picks random different character
                p2_choices=[i for i in range(len(CHARS)) if i!=p1_char]
                p2_char=random.choice(p2_choices)
                state=HOW_TO_PLAY; tick=0

        elif state==HOW_TO_PLAY:
            draw_how_to_play(scr,H,W,tick)
            if ord(' ') in keys:
                countdown_phase=3; countdown_timer=FPS
                state=COUNTDOWN

        elif state==COUNTDOWN:
            draw_countdown(scr,H,W,countdown_phase)
            countdown_timer-=1
            if countdown_timer<=0:
                if countdown_phase>0:
                    countdown_phase-=1
                    countdown_timer=FPS if countdown_phase>0 else FPS
                else:
                    game=Game(p1_char,p2_char)
                    game.show(f'  ROUND {game.rnd}  ',75)
                    state=FIGHT

        elif state==FIGHT:
            if game:
                game.update(keys,mp,mk)
                draw_fight(scr,game,W,H)
                if game.over and (10 in keys or 13 in keys):
                    if not game.next_round():
                        # Match over — submit score (rounds won as score)
                        _sub=[None]
                        extra=f'{"Win" if game.p1w>=NEED else "Loss"} {game.p1w}-{game.p2w}'
                        submit_async('fight', game.p1w*100, extra, _sub)
                        state=SELECT; sel=p1_char
                    else:
                        countdown_phase=3; countdown_timer=FPS
                        state=COUNTDOWN

        elif state==PAUSE:
            if game: draw_fight(scr,game,W,H)
            draw_pause(scr,H,W)
            if ord('r') in keys or ord('R') in keys: state=FIGHT
            if ord('q') in keys or ord('Q') in keys: break

if __name__ == '__main__':
    run_game(main, 'Claude Fighter')
