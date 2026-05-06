#!/usr/bin/env python3
"""Claudcade — The Claude Terminal Arcade Launcher"""
from __future__ import annotations

import curses, time, random, subprocess, os, sys
from claudcade_engine import setup_colors
TITLE = [
    r"  ___  _      _   _   _  ___   ___   _    ___  ___ ",
    r" / __|| |    /_\ | | | ||   \ / __| /_\  |   \| __|",
    r"| (__ | |__ / _ \| |_| || |) | (__ / _ \ | |) | _| ",
    r" \___||____/_/ \_\\___/ |___/ \___/_/ \_\|___/|___|",
]
GAMES = [
    {
        'name':     'C-TYPE',
        'subtitle': 'SPACE SHOOTER',
        'script':   'ctype.py',
        'genre':    'SHMUP',
        'color':    1,
        'desc': [
            '5 enemy types + escalating wave system',
            'Parallax star-field, power-ups',
            'Boss battle every 6th wave',
            'Hold J for charge beam · mouse to fire',
        ],
        'controls': [
            'WASD / Arrows  Move',
            'J / Click      Shoot',
            'Hold J         Charge beam',
            'ESC            Pause',
        ],
        'art': [
            "  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·",
            "      ▷═══▷         ◁══◁       ",
            "  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·",
        ],
    },
    {
        'name':     'Claudtra',
        'subtitle': 'ACTION PLATFORMER',
        'script':   'claudtra.py',
        'genre':    'ACTION',
        'color':    3,
        'desc': [
            'Side-scrolling run-and-gun platformer',
            'Grunt and heavy enemy classes',
            'Multi-life system with respawn',
            'Jump, crouch, shoot through waves',
        ],
        'controls': [
            'A / D          Move left / right',
            'SPACE          Jump',
            'J / Click      Shoot',
            'S              Crouch',
            'ESC            Pause',
        ],
        'art': [
            "▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔",
            "▷ @──▷          ×    ",
            "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓",
        ],
    },
    {
        'name':     'Claude Fighter',
        'subtitle': '1v1 FIGHTING',
        'script':   'fight.py',
        'genre':    'FIGHTING',
        'color':    2,
        'desc': [
            '5 unique fighters with distinct styles',
            'Punch, kick, block, jump, crouch',
            'Best of 3 rounds vs AI opponent',
            'Mouse left/right click to fight',
        ],
        'controls': [
            'A / D          Move',
            'SPACE          Jump',
            'S              Crouch',
            'J / Click      Punch',
            'K              Kick',
            'L              Block',
            'ESC            Pause',
        ],
        'art': [
            " ╔═══╗       ╔═══╗",
            " ║ ▲ ║ ──×   ║ ● ║",
            " ╚═╦═╝       ╚═╦═╝",
            "   ║             ║ ",
        ],
    },
    {
        'name':     'Super Claudio',
        'subtitle': 'PLATFORMER',
        'script':   'superclaudio.py',
        'genre':    'PLATFORM',
        'color':    1,
        'desc': [
            '3 worlds to save Princess Anthropia',
            'Stomp Glitchies, collect Tokens',
            'Power-up: Mushroom → Super, Flower → Fire',
            'Reach the flagpole to clear each world',
        ],
        'controls': [
            'A / ←          Move left / right',
            'W / ↑ / SPC    Jump',
            'J              Shoot (Fire Claudio)',
            'ESC            Pause',
        ],
        'art': [
            "  ══ [?] ══  ",
            "       ◉     ",
            "  (◎)   (ₓ)  ",
            "══════════════",
        ],
    },
    {
        'name':     'Claudémon',
        'subtitle': 'COLLECT & BATTLE RPG',
        'script':   'claudemon.py',
        'genre':    'RPG',
        'color':    3,
        'desc': [
            'Catch all 20 Claudémon across 4 regions',
            '3 starters: Neural, Data, or Logic type',
            'Turn-based battles with type matchups',
            'Save your progress · Evolve your team',
        ],
        'controls': [
            'WASD / Arrows  Move / Navigate',
            'SPACE / Enter  Confirm / Interact',
            'M              Party menu',
            'ESC            Pause',
        ],
        'art': [
            "   .·◉·.   ",
            "   (◕‿◕)   ",
            "   /▌C▐\\   ",
            "    \\___/   ",
        ],
    },
    {
        'name':     'Claude Turismo',
        'subtitle': 'PSEUDO-3D RACING',
        'script':   'claudturismo.py',
        'genre':    'RACING',
        'color':    4,
        'desc': [
            '3-lap pseudo-3D terminal racing',
            'Perspective road with real curves',
            'AI opponents with rubber-band logic',
            'Brake for corners or spin wide',
        ],
        'controls': [
            '↑ / W          Accelerate',
            '↓ / S          Brake',
            '← / A          Steer left',
            '→ / D          Steer right',
            'ESC            Pause',
        ],
        'art': [
            "  · · · · · · · · · ·",
            "       ▷═══▷         ",
            "      /       \\      ",
            "     / ══   ══ \\    ",
            "▐▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▌  ",
        ],
    },
    {
        'name':     'FINAL CLAUDESY',
        'subtitle': 'TERMINAL JRPG',
        'script':   'finalclaudesy.py',
        'genre':    'RPG',
        'color':    6,
        'desc': [
            '3 heroes · 3 regions · final boss',
            'Turn-based combat with 20+ spells',
            'Towns, dungeons, equipment, story',
            'Save system · ~3 hours of content',
        ],
        'controls': [
            'WASD / Arrows  Move / Navigate',
            'SPACE / Enter  Confirm',
            'Q / ESC        Back / Cancel',
            'M              Party menu',
        ],
        'art': [
            "┌─────────────────┐",
            "│  HP ███████░░░ │",
            "│  MP █████░░░░░ │",
            "├─────────────────┤",
            "│  ▸ Attack      │",
            "│    Magic       │",
            "└─────────────────┘",
        ],
    },
    {
        'name':     'Claude & Field',
        'subtitle': 'TRACK & FIELD',
        'script':   'claudefield.py',
        'genre':    'SPORTS',
        'color':    2,
        'desc': [
            '5 events: Dash · Long Jump · Hurdles',
            'Javelin Throw · Hammer Throw',
            'Mash A/D to sprint · SPACE to act',
            'Beat the world record in each event',
        ],
        'controls': [
            'A / D          Alternate rapidly to sprint',
            'SPACE          Jump / Throw / Release',
            'ESC            Quit event',
        ],
        'art': [
            "  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·",
            "   ◙      ◙      ◙      ◙     ",
            "  ╱ ╲    ╲ ╱    ╱ ╲    ╲ ╱   ",
            "══════════════════════════════",
        ],
    },
]
def _p(scr: curses.window, H: int, W: int, r: int, c: int, s: str, a: int = 0) -> None:
    try:
        if 0 <= r < H-1 and 0 <= c < W:
            scr.addstr(r, c, s[:max(0, W-c)], a)
    except curses.error:
        pass
_SPACED_CAPS = {
    'C-TYPE':          'C · T · Y · P · E',
    'Claudtra':        'C L A U D T R A',
    'Claude Fighter':  'C L A U D E  F I G H T E R',
    'Super Claudio':   'S U P E R  C L A U D I O',
    'Claudémon':       'C L A U D É M O N',
    'Claude Turismo':  'C L A U D E  T U R I S M O',
    'FINAL CLAUDESY':  'F I N A L  C L A U D E S Y',
    'Claude & Field':  'C L A U D E  &  F I E L D',
}

def _spaced(name: str) -> str:
    return _SPACED_CAPS.get(name, name.upper())

def draw_main(scr: curses.window, H: int, W: int, tick: int, cursor: int) -> None:
    P    = curses.color_pair
    PINK = P(6) | curses.A_BOLD   # the only accent color
    DIM  = P(5) | curses.A_DIM
    BOLD = P(5) | curses.A_BOLD
    NORM = P(5)

    scr.erase()
    _p(scr, H, W, 0,   0, '╔' + '═'*(W-2) + '╗', BOLD)
    _p(scr, H, W, H-1, 0, '╚' + '═'*(W-2) + '╝', BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0,   '║', NORM)
        _p(scr, H, W, r, W-1, '║', NORM)
    title_attrs = [BOLD, BOLD, NORM, DIM]
    for i, (line, attr) in enumerate(zip(TITLE, title_attrs)):
        tx = max(1, (W - len(line)) // 2)
        _p(scr, H, W, 1+i, tx, line, attr)

    # Fade row: ░ characters soften the transition
    _p(scr, H, W, 5, 1, '░' * (W-2), DIM)
    DIV = 6
    _p(scr, H, W, DIV, 0, '╠' + '═'*(W-2) + '╣', BOLD)
    CARD_Y   = DIV + 1          # row where cards start
    CARD_H   = 7                # height of each cabinet card
    INNER_W  = W - 2            # usable columns inside outer border
    card_w   = INNER_W // 4    # width of each card (equal quarters)
    N        = len(GAMES)

    for i, g in enumerate(GAMES):
        sel  = (i == cursor)
        cx   = 1 + i * card_w  # leftmost column of card
        num  = f'0{i+1}' if i < 9 else str(i+1)
        spaced = _spaced(g['name'])

        inner = card_w - 2
        name_str = spaced[:inner] if len(spaced) > inner else spaced

        if sel:
            tl, tr, bl, br, hz, vt = '╔', '╗', '╚', '╝', '═', '║'
            border_attr  = PINK
            name_attr    = PINK
        else:
            tl, tr, bl, br, hz, vt = '┌', '┐', '└', '┘', '─', '│'
            border_attr  = DIM
            name_attr    = NORM

        _p(scr, H, W, CARD_Y,          cx, tl + hz*(card_w-2) + tr, border_attr)
        _p(scr, H, W, CARD_Y+CARD_H-1, cx, bl + hz*(card_w-2) + br, border_attr)

        for row in range(1, CARD_H-1):
            _p(scr, H, W, CARD_Y+row, cx,           vt, border_attr)
            _p(scr, H, W, CARD_Y+row, cx+card_w-1,  vt, border_attr)
            _p(scr, H, W, CARD_Y+row, cx+1, ' '*inner, NORM)

        # Row 1: game number (top-left of interior)
        _p(scr, H, W, CARD_Y+1, cx+2, num, DIM)

        # Row 3 (middle): spaced-caps game name, centred
        name_col = cx + 1 + max(0, (inner - len(name_str)) // 2)
        _p(scr, H, W, CARD_Y+3, name_col, name_str, name_attr)

        # Row 5: genre tag, centred
        genre = g['genre'][:inner]
        genre_col = cx + 1 + max(0, (inner - len(genre)) // 2)
        _p(scr, H, W, CARD_Y+5, genre_col, genre, DIM)
    DET_DIV = CARD_Y + CARD_H
    _p(scr, H, W, DET_DIV, 0, '╠' + '═'*(W-2) + '╣', BOLD)
    g    = GAMES[cursor]
    DX   = 2          # left margin inside border
    DY   = DET_DIV + 1

    title_str  = g['name'].upper()
    sub_str    = '  —  ' + g['subtitle']
    _p(scr, H, W, DY,   DX, title_str, BOLD)
    _p(scr, H, W, DY,   DX + len(title_str), sub_str, DIM)

    desc_lines = g['desc']
    if len(desc_lines) >= 2:
        desc_str = desc_lines[0] + '  ' + desc_lines[1]
    else:
        desc_str = desc_lines[0] if desc_lines else ''
    _p(scr, H, W, DY+1, DX, desc_str[:W-4], DIM)

    # Keys rendered in PINK, descriptions in DIM, separated by fixed spacing
    ctrl_parts = []
    for ctrl in g['controls'][:5]:
        parts = ctrl.split(None, 1)
        ctrl_parts.append((parts[0], parts[1] if len(parts) > 1 else ''))

    ctrl_col = DX
    ctrl_row = DY + 2
    for key, desc in ctrl_parts:
        if ctrl_col >= W - 2:
            break
        _p(scr, H, W, ctrl_row, ctrl_col, key, PINK)
        ctrl_col += len(key)
        if desc:
            sep = ' '
            _p(scr, H, W, ctrl_row, ctrl_col, sep + desc, DIM)
            ctrl_col += len(sep) + len(desc)
        _p(scr, H, W, ctrl_row, ctrl_col, '   ', NORM)
        ctrl_col += 3
    _p(scr, H, W, H-3, 0, '╠' + '═'*(W-2) + '╣', BOLD)
    _p(scr, H, W, H-2, 2, '←→ SELECT     ENTER LAUNCH     Q QUIT', DIM)

    scr.refresh()
_launch_script = None

def arcade_main(scr: curses.window) -> None:
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

        LEFT  = (curses.KEY_LEFT  in keys or ord('a') in keys or
                 curses.KEY_UP    in keys or ord('w') in keys)
        RIGHT = (curses.KEY_RIGHT in keys or ord('d') in keys or
                 curses.KEY_DOWN  in keys or ord('s') in keys)
        OK   = any(k in keys for k in (ord('\n'), 10, 13, ord(' ')))
        QUIT = ord('q') in keys or ord('Q') in keys or 27 in keys

        if LEFT:  cursor = (cursor-1) % len(GAMES)
        if RIGHT: cursor = (cursor+1) % len(GAMES)
        if QUIT: _launch_script = None; break
        if OK:   _launch_script = GAMES[cursor]['script']; break

        draw_main(scr, H, W, tick, cursor)

def _launch(script: str, script_dir: str):
    """Open the game full-screen in a new tmux window. Falls back to direct run."""
    full_path = os.path.join(script_dir, script)
    window_name = script.replace('.py', '').upper()
    if os.environ.get('TMUX'):
        # New window = full screen. Closes automatically when game exits,
        # returning focus to the arcade window.
        subprocess.run([
            'tmux', 'new-window', '-n', window_name,
            f'cd {script_dir} && {sys.executable} {full_path}'
        ])
    else:
        subprocess.run([sys.executable, full_path], cwd=script_dir)


def run():
    global _launch_script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        curses.wrapper(arcade_main)
        if _launch_script is None:
            print('\n  Thanks for playing — Claudcade\n')
            break
        _launch(_launch_script, script_dir)

if __name__ == '__main__':
    run()
