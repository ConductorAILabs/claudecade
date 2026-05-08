#!/usr/bin/env python3
"""Claudcade — The Claude Terminal Arcade Launcher"""
import curses, time, random, subprocess, os, sys
from claudcade_engine import setup_colors

# ── TITLE ART (CLAUDECADE in block font) ───────────────────────────────────────
TITLE = [
    " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗ ██████╗ █████╗ ██████╗ ███████╗",
    "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝",
    "██║     ██║     ███████║██║   ██║██║  ██║█████╗  ██║     ███████║██║  ██║█████╗  ",
    "██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  ██║     ██╔══██║██║  ██║██╔══╝  ",
    "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗╚██████╗██║  ██║██████╔╝███████╗",
    " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝",
]

# Game block-font titles (for right panel display)
GAME_TITLES = {
    'ctype': [
        " ██████╗       ████████╗██╗   ██╗██████╗ ███████╗",
        "██╔════╝       ╚══██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝",
        "██║     ██████╗   ██║    ╚████╔╝ ██████╔╝█████╗  ",
        "██║     ╚═════╝   ██║     ╚██╔╝  ██╔═══╝ ██╔══╝  ",
        "╚██████╗          ██║      ██║   ██║     ███████╗",
        " ╚═════╝          ╚═╝      ╚═╝   ╚═╝     ╚══════╝",
    ],
    'claudtra': [
        " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ████████╗██████╗  █████╗ ",
        "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗",
        "██║     ██║     ███████║██║   ██║██║  ██║   ██║   ██████╔╝███████║",
        "██║     ██║     ██╔══██║██║   ██║██║  ██║   ██║   ██╔══██╗██╔══██║",
        "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝   ██║   ██║  ██║██║  ██║",
        " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝",
    ],
    'fight': [
        " ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗    ███████╗██╗ ██████╗ ██╗  ██╗████████╗███████╗██████╗ ",
        "██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝    ██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝██╔════╝██╔══██╗",
        "██║     ██║     ███████║██║   ██║██║  ██║█████╗      █████╗  ██║██║  ███╗███████║   ██║   █████╗  ██████╔╝",
        "██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝      ██╔══╝  ██║██║   ██║██╔══██║   ██║   ██╔══╝  ██╔══██╗",
        "╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗    ██║     ██║╚██████╔╝██║  ██║   ██║   ███████╗██║  ██║",
        " ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝",
    ],
    'finalclaudesy': [
        "███████╗██╗███╗   ██╗ █████╗ ██╗          ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗███████╗██╗   ██╗",
        "██╔════╝██║████╗  ██║██╔══██╗██║         ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝",
        "█████╗  ██║██╔██╗ ██║███████║██║         ██║     ██║     ███████║██║   ██║██║  ██║█████╗  ███████╗ ╚████╔╝ ",
        "██╔══╝  ██║██║╚██╗██║██╔══██║██║         ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  ╚════██║  ╚██╔╝  ",
        "██║     ██║██║ ╚████║██║  ██║███████╗    ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗███████║   ██║   ",
        "╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝     ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ",
    ],
}

# ── GAME CATALOGUE ─────────────────────────────────────────────────────────────
GAMES = [
    {
        'name':     'C-TYPE',
        'subtitle': 'SPACE SHOOTER',
        'script':   'ctype.py',
        'genre':    'SHMUP',
        'color':    1,
        'title_key': 'ctype',
        'desc': [
            'Dodge waves · Charge beam · Get power-ups',
            'Boss every 6th wave · Parallax starfield',
            '5 enemy types · Escalating difficulty',
            'Score system with local leaderboard',
        ],
        'controls': [
            'WASD / Arrows  Move',
            'J / SPACE      Fire',
            'Hold J         Charge beam',
            'ESC            Pause / Quit',
        ],
        'art': [
            "    ▲      ",
            "◀═══◆═══▶  ",
            "    ▼      ",
        ],
    },
    {
        'name':     'CLAUDTRA',
        'subtitle': 'RUN & GUN',
        'script':   'claudtra.py',
        'genre':    'ACTION',
        'color':    3,
        'title_key': 'claudtra',
        'desc': [
            'Side-scrolling action platformer',
            'Grunt and heavy enemies · Multi-life system',
            'Jump, crouch, shoot through waves',
            'Score system with local leaderboard',
        ],
        'controls': [
            'A / D          Move left / right',
            'SPACE          Jump',
            'J              Shoot',
            'S              Crouch · ESC  Pause',
        ],
        'art': [
            "  ╭─╮      ",
            "  │·│═══► ",
            "  ╰┬╯     ",
            "  ╱╲      ",
        ],
    },
    {
        'name':     'CLAUDE FIGHTER',
        'subtitle': '1V1 FIGHTING',
        'script':   'fight.py',
        'genre':    'FIGHTING',
        'color':    2,
        'title_key': 'fight',
        'desc': [
            '5 unique fighters with distinct styles',
            'Punch, kick, block, jump mechanics',
            'Best of 3 rounds vs AI opponent',
            'Score system with local leaderboard',
        ],
        'controls': [
            'A / D          Move',
            'SPACE          Jump',
            'J              Punch',
            'K  Kick · L  Block · S  Crouch',
        ],
        'art': [
            "  ╲ ╱    ",
            "   ╳     ",
            "  ╱ ╲    ",
        ],
    },
    {
        'name':     'FINAL CLAUDESY',
        'subtitle': 'EPIC JRPG',
        'script':   'finalclaudesy.py',
        'genre':    'RPG',
        'color':    6,
        'title_key': 'finalclaudesy',
        'desc': [
            '3 heroes · 3 regions · 20+ spells',
            'Turn-based combat · Equipment system',
            'Towns, dungeons, NPCs, full story',
            '~3 hours of content · Multiple endings',
        ],
        'controls': [
            'WASD / Arrows  Move or select',
            'SPACE / Enter  Confirm action',
            'M              Open party menu',
            'Q / ESC        Cancel / Back',
        ],
        'art': [
            "     ▲     ",
            "    ╔╪╗    ",
            "     ║     ",
            "     ║     ",
            "     ▼     ",
        ],
    },
]

# ── DRAWING HELPERS ────────────────────────────────────────────────────────────
def _p(scr, H, W, r, c, s, a=0):
    try:
        if 0 <= r < H-1 and 0 <= c < W:
            scr.addstr(r, c, s[:max(0, W-c)], a)
    except curses.error:
        pass

# ── MAIN SCREEN ────────────────────────────────────────────────────────────────
def draw_main(scr, H, W, tick, cursor):
    P = curses.color_pair
    scr.erase()

    # ── Animated background stars ──────────────────────────────────────────
    random.seed(999)
    for _ in range(40):
        r = random.randint(1, H-2)
        c = random.randint(1, W-2)
        ch = random.choice(['·', '·', '·', '+', '*'])
        if (tick // 8 + r * 3 + c) % 11 == 0:
            _p(scr, H, W, r, c, ch, P(5)|curses.A_DIM)
    random.seed()

    # ── Outer border ────────────────────────────────────────────────────────
    _p(scr, H, W, 0,   0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0,   '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))

    # ── Header block (shaded depth) ─────────────────────────────────────────
    shade_full = '▓▒░' + '░'*(W-8) + '░▒▓'
    _p(scr, H, W, 1, 1, shade_full[:W-2], P(5)|curses.A_DIM)

    # Title art — cycle through 4 colors for flair
    title_colors = [P(4)|curses.A_BOLD, P(1)|curses.A_BOLD,
                    P(6)|curses.A_BOLD, P(4)|curses.A_BOLD]
    for i, line in enumerate(TITLE):
        tx = max(1, (W - len(line)) // 2)
        _p(scr, H, W, 2+i, tx, line, title_colors[i])

    sub = '◈   T H E   C L A U D E   T E R M I N A L   A R C A D E   ◈'
    _p(scr, H, W, 6, max(1, (W-len(sub))//2), sub, P(6)|curses.A_BOLD)

    _p(scr, H, W, 7, 1, shade_full[:W-2], P(5)|curses.A_DIM)

    # ── Section divider ─────────────────────────────────────────────────────
    DIV = 8
    _p(scr, H, W, DIV, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

    # ── Vertical panel split ─────────────────────────────────────────────────
    LIST_W  = 30
    SPLIT   = LIST_W + 1
    DET_X   = SPLIT + 1
    DET_W   = W - DET_X - 1
    PANEL_Y = DIV + 1

    for r in range(PANEL_Y, H-3):
        _p(scr, H, W, r, SPLIT, '║', P(5))
    _p(scr, H, W, DIV,  SPLIT, '╦', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-3,  SPLIT, '╩', P(5)|curses.A_BOLD)

    # ── Game list (left panel) ───────────────────────────────────────────────
    _p(scr, H, W, PANEL_Y,   2, 'GAMES',  P(5)|curses.A_BOLD)
    _p(scr, H, W, PANEL_Y,  22, 'GENRE',  P(5)|curses.A_DIM)
    _p(scr, H, W, PANEL_Y+1, 2, '─'*(LIST_W-2), P(5)|curses.A_DIM)

    for i, g in enumerate(GAMES):
        gy = PANEL_Y + 2 + i * 2
        if gy >= H-4: break
        sel = (i == cursor)
        prefix   = '▶ ' if sel else '  '
        name_a   = (P(g['color'])|curses.A_BOLD|curses.A_REVERSE) if sel else (P(g['color'])|curses.A_BOLD)
        genre_a  = P(7) if sel else (P(5)|curses.A_DIM)
        _p(scr, H, W, gy,   2, prefix + g['name'][:17], name_a)
        _p(scr, H, W, gy,  21, f'[{g["genre"]:7}]',    genre_a)
        if sel:
            _p(scr, H, W, gy+1, 4, '·'*(LIST_W-6), P(g['color'])|curses.A_DIM)

    # ── Game detail (right panel) ────────────────────────────────────────────
    g   = GAMES[cursor]
    gcp = g['color']

    # Block-font game title
    title_key = g.get('title_key', g['name'].lower().replace(' ', ''))
    if title_key in GAME_TITLES:
        ART_Y = PANEL_Y
        for i, line in enumerate(GAME_TITLES[title_key]):
            if ART_Y + i < H - 4:
                trimmed = line[:DET_W-2] if len(line) > DET_W-2 else line
                _p(scr, H, W, ART_Y+i, DET_X+1, trimmed, P(gcp)|curses.A_BOLD)
        ART_Y += len(GAME_TITLES[title_key])
    else:
        ART_Y = PANEL_Y
        gt   = f'★  {g["name"]}  —  {g["subtitle"]}  ★'
        _p(scr, H, W, ART_Y, DET_X+1, gt[:DET_W-2], P(gcp)|curses.A_BOLD)
        ART_Y += 1

    _p(scr, H, W, ART_Y, DET_X+1, '═'*(DET_W-2), P(gcp)|curses.A_DIM)

    # Game sprite (small art preview)
    ART_Y = ART_Y + 2
    ART_X = DET_X + 3
    art   = g['art']
    if art:
        aw    = max(len(l) for l in art) + 2
        ah    = len(art) + 2
        if ART_Y + ah < H - 6:
            _p(scr, H, W, ART_Y,      ART_X-2, '┌'+'─'*aw+'┐', P(5)|curses.A_DIM)
            _p(scr, H, W, ART_Y+ah-1, ART_X-2, '└'+'─'*aw+'┘', P(5)|curses.A_DIM)
            for r in range(1, ah-1):
                _p(scr, H, W, ART_Y+r, ART_X-2, '│', P(5)|curses.A_DIM)
                _p(scr, H, W, ART_Y+r, ART_X-2+aw+1, '│', P(5)|curses.A_DIM)
            for i, line in enumerate(art):
                _p(scr, H, W, ART_Y+1+i, ART_X, line, P(gcp)|curses.A_BOLD)

    # Description
    DESC_X = DET_X + 2
    _p(scr, H, W, ART_Y,   DESC_X, g['subtitle'], P(gcp)|curses.A_BOLD)
    _p(scr, H, W, ART_Y+1, DESC_X, '─'*max(0, DET_W-2), P(5)|curses.A_DIM)
    for i, line in enumerate(g['desc']):
        if ART_Y+2+i < H-5:
            _p(scr, H, W, ART_Y+2+i, DESC_X, f'• {line}', P(5))

    # Controls
    CTRL_Y = ART_Y + len(g['desc']) + 3
    if CTRL_Y < H - 5:
        _p(scr, H, W, CTRL_Y, DET_X+2, 'CONTROLS', P(5)|curses.A_BOLD)
        _p(scr, H, W, CTRL_Y, DET_X+12, '─'*max(0, DET_W-12), P(5)|curses.A_DIM)
        for i, ctrl in enumerate(g['controls']):
            ky, rest = ctrl.split(None, 1) if ' ' in ctrl else (ctrl, '')
            cy = CTRL_Y + 1 + i
            if cy >= H-4: break
            _p(scr, H, W, cy, DET_X+4, ky, P(gcp)|curses.A_BOLD)
            pad = 14 - len(ky)
            _p(scr, H, W, cy, DET_X+4+len(ky)+max(1,pad), rest, P(5))

    # Launch prompt (blinking)
    if (tick // 15) % 2 == 0:
        lp = f'[ ENTER ]  Launch  {g["name"]}'
        lx = DET_X + (DET_W - len(lp)) // 2
        _p(scr, H, W, H-4, lx, lp, P(gcp)|curses.A_BOLD|curses.A_REVERSE)

    # ── Footer ──────────────────────────────────────────────────────────────
    _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    foot = f'  ↑↓  Select     ENTER  Launch     Q  Quit              {len(GAMES)} GAMES  ·  Claudcade v1.0'
    _p(scr, H, W, H-2, 2, foot, P(5))

    scr.refresh()

# ── ARCADE MAIN ────────────────────────────────────────────────────────────────
_launch_script = None

def arcade_main(scr):
    global _launch_script
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()
    try: curses.mousemask(0)  # disable mouse for the launcher
    except curses.error: pass

    cursor = 0
    nxt    = time.perf_counter()
    tick   = 0

    while True:
        now = time.perf_counter()
        if now < nxt: time.sleep(max(0, nxt-now-0.001)); continue
        nxt += 1/30; tick += 1

        H, W = scr.getmaxyx()
        keys = set()
        while True:
            k = scr.getch()
            if k == -1: break
            keys.add(k)

        UP   = curses.KEY_UP   in keys or ord('w') in keys
        DOWN = curses.KEY_DOWN in keys or ord('s') in keys
        OK   = any(k in keys for k in (ord('\n'), 10, 13, ord(' ')))
        QUIT = ord('q') in keys or ord('Q') in keys or 27 in keys

        if UP:   cursor = (cursor-1) % len(GAMES)
        if DOWN: cursor = (cursor+1) % len(GAMES)
        if QUIT: _launch_script = None; break
        if OK:   _launch_script = GAMES[cursor]['script']; break

        draw_main(scr, H, W, tick, cursor)

def run():
    global _launch_script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        curses.wrapper(arcade_main)
        if _launch_script is None:
            print('\n  Thanks for playing — Claudcade\n')
            break
        script = os.path.join(script_dir, _launch_script)
        subprocess.run([sys.executable, script], cwd=script_dir)

if __name__ == '__main__':
    run()
