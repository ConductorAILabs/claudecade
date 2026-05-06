"""Claudémon — main game loop."""
from __future__ import annotations

import curses, time, random, json, os, sys

from .data     import CLAUDEMON, WORLD_MAPS, PLAYER_START, ITEMS
from .entities import ClaudemonInstance
from .battle   import Battle, ANIMATING, LEVEL_UP
from .world    import Overworld

from claudcade_engine import setup_colors, Renderer, run_game

FPS       = 30
SAVE_PATH = os.path.expanduser('~/claudemon_save.json')
TITLE, STARTER_SELECT, HOW_TO_PLAY, OVERWORLD, IN_BATTLE, PARTY_MENU, SHOP, DIALOGUE, PAUSE, GAME_OVER = range(10)

TITLE_ART = [
    r"  ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗███╗   ███╗ ██████╗ ███╗  ██╗",
    r" ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝████╗ ████║██╔═══██╗████╗ ██║",
    r" ██║     ██║     ███████║██║   ██║██║  ██║█████╗  ██╔████╔██║██║   ██║██╔██╗██║",
    r" ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║██║╚████║",
    r" ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝██║ ╚███║",
    r"  ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚══╝",
]

TITLE_ART_SIMPLE = [
    r" ___  _      _   _   _  ___  _  _  ___  _  _",
    r"/ __|| |    /_\ | | | ||   \| \| ||   \| \| |",
    r"\__ \| |__ / _ \| |_| || |) | .  || |) | .  |",
    r"|___/|____/_/ \_\\___/ |___/|_|\_||___/|_|\_|",
]

STARTERS = ['Promptling', 'Dataling', 'Logixlet']

STARTER_DESC = {
    'Promptling': ('Neural', 'A clever Neural-type.\nFast and magic-oriented.\nLearns Prompt early.'),
    'Dataling':   ('Data',   'A sturdy Data-type.\nHigh Attack & Defense.\nLearns Compile early.'),
    'Logixlet':   ('Logic',  'A balanced Logic-type.\nGreat Sp.Def & Speed.\nLearns Analyze early.'),
}

def _p(scr, H, W, r, c, s, a=0):
    try:
        if 0 <= r < H-1 and 0 <= c < W:
            scr.addstr(r, c, s[:max(0, W-c)], a)
    except curses.error:
        pass


def draw_title(scr, H, W, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))

    # Choose art size based on terminal width
    use_art = TITLE_ART if W >= len(TITLE_ART[0])+4 else TITLE_ART_SIMPLE
    title_colors = [P(4)|curses.A_BOLD, P(6)|curses.A_BOLD, P(1)|curses.A_BOLD,
                    P(4)|curses.A_BOLD, P(6)|curses.A_BOLD, P(1)|curses.A_BOLD]
    for i, line in enumerate(use_art):
        attr = title_colors[i % len(title_colors)]
        _p(scr, H, W, 2+i, max(1,(W-len(line))//2), line, attr)

    title_h = 2 + len(use_art)
    _p(scr, H, W, title_h, 1, '░'*(W-2), P(5)|curses.A_DIM)

    sub = '◈  C A T C H  T H E M  A L L  ◈'
    _p(scr, H, W, title_h+1, max(1,(W-len(sub))//2), sub, P(6)|curses.A_BOLD)

    # Three starter previews side by side
    arts = [CLAUDEMON[s]['art'] for s in STARTERS]
    names = STARTERS
    panel_w = (W - 4) // 3
    ay = title_h + 3
    for si, (art, name) in enumerate(zip(arts, names)):
        px = 2 + si * panel_w
        # Cycle-highlight one starter
        highlight = (si == (tick // 40) % 3)
        box_attr  = P(6)|curses.A_BOLD if highlight else P(5)|curses.A_DIM
        _p(scr, H, W, ay-1, px, '┌'+'─'*(panel_w-2)+'┐', box_attr)
        art_lines = art + ['']*(5-len(art))
        for ai, aline in enumerate(art_lines[:5]):
            _p(scr, H, W, ay+ai, px, '│', box_attr)
            _p(scr, H, W, ay+ai, px+panel_w-1, '│', box_attr)
            acol = px + max(1, (panel_w-len(aline))//2)
            line_attr = P(1)|curses.A_BOLD if highlight else P(5)
            _p(scr, H, W, ay+ai, acol, aline, line_attr)
        _p(scr, H, W, ay+5, px, '└'+'─'*(panel_w-2)+'┘', box_attr)
        nattr = P(6)|curses.A_BOLD if highlight else P(5)|curses.A_BOLD
        _p(scr, H, W, ay+6, px + max(0,(panel_w-len(name))//2), name, nattr)

    if (tick // 18) % 2 == 0:
        msg = '[ SPACE ] ▸ NEW GAME        [ L ] ▸ LOAD GAME'
        _p(scr, H, W, H-4, max(1,(W-len(msg))//2), msg, P(4)|curses.A_BOLD)
    _p(scr, H, W, H-2, 2, '20 Claudémon to discover · 4 regions · Catch them all!', P(5)|curses.A_DIM)
    _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    scr.refresh()


def draw_starter_select(scr, H, W, cursor, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))
    _p(scr, H, W, 1, 1, '░'*(W-2), P(5)|curses.A_DIM)
    prompt = '◈  Prof. Claude: Choose your first Claudémon!  ◈'
    _p(scr, H, W, 1, max(1,(W-len(prompt))//2), prompt, P(4)|curses.A_BOLD)
    _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

    card_w = (W - 5) // 3
    card_h = 14
    card_top = 3

    for i, name in enumerate(STARTERS):
        sel  = (i == cursor)
        cx   = 2 + i * (card_w + 1)
        col  = P(6)|curses.A_BOLD if sel else P(5)|curses.A_DIM
        tl, tr, bl, br, hz, vt = ('╔','╗','╚','╝','═','║') if sel else ('┌','┐','└','┘','─','│')
        _p(scr, H, W, card_top, cx, tl+hz*(card_w-2)+tr, col)
        for r in range(1, card_h-1):
            _p(scr, H, W, card_top+r, cx, vt+' '*(card_w-2)+vt, col)
        _p(scr, H, W, card_top+card_h-1, cx, bl+hz*(card_w-2)+br, col)

        # Art — centred in card
        art = CLAUDEMON[name]['art']
        art_start = card_top + 1
        for ai, aline in enumerate(art[:6]):
            ax = cx + max(1, (card_w-len(aline))//2)
            line_attr = P(1)|curses.A_BOLD if sel else P(5)|curses.A_DIM
            _p(scr, H, W, art_start+ai, ax, aline, line_attr)

        # Name + type
        name_row = card_top + 8
        n_attr = P(6)|curses.A_BOLD if sel else P(5)|curses.A_BOLD
        _p(scr, H, W, name_row,   cx+max(1,(card_w-len(name))//2), name, n_attr)
        type_str = f'[ {STARTER_DESC[name][0]} ]'
        t_attr = P(4)|curses.A_BOLD if sel else P(5)|curses.A_DIM
        _p(scr, H, W, name_row+1, cx+max(1,(card_w-len(type_str))//2), type_str, t_attr)

        # Mini stat display
        if sel:
            from .data import CLAUDEMON as CD
            d = CD[name]
            stat_y = name_row + 2
            stats = [('HP', d['hp']), ('ATK', d['spatk']), ('SPD', d['spd'])]
            for si, (sname, sval) in enumerate(stats):
                bar_w = min(8, card_w - 10)
                filled = max(0, int(bar_w * sval / 120))
                sbar = '█'*filled + '░'*(bar_w-filled)
                _p(scr, H, W, stat_y+si, cx+2, f'{sname:<4}{sbar}', P(3)|curses.A_BOLD)

    # Description of selected
    desc_y = card_top + card_h + 1
    sel_name = STARTERS[cursor]
    _, _, desc = STARTER_DESC[sel_name]
    _p(scr, H, W, desc_y, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    for i, line in enumerate(desc.split('\n')):
        _p(scr, H, W, desc_y+1+i, 4, line, P(5)|curses.A_BOLD)

    _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    if (tick // 18) % 2 == 0:
        hint = '[ ← → ]  Browse   [ ENTER ]  Choose this Claudémon!'
        _p(scr, H, W, H-2, max(1,(W-len(hint))//2), hint, P(4)|curses.A_BOLD)
    scr.refresh()


def draw_how_to_play(scr, H, W, tick):
    P = curses.color_pair
    scr.erase()
    _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
    _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        _p(scr, H, W, r, 0, '║', P(5))
        _p(scr, H, W, r, W-1, '║', P(5))
    _p(scr, H, W, 1, 1, '░'*(W-2), P(5)|curses.A_DIM)
    title = '◈  H O W  T O  P L A Y  ◈'
    _p(scr, H, W, 1, max(1,(W-len(title))//2), title, P(4)|curses.A_BOLD)
    _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

    lines = [
        ('── GOAL ──────────────────────────────────', P(4)|curses.A_BOLD),
        ('', None),
        ("  Explore the world and catch all 20 Claudémon!", P(5)),
        ("  Weaken wild Claudémon first, then throw a ball.", P(5)),
        ("  Lower HP = higher catch chance!", P(4)|curses.A_BOLD),
        ('', None),
        ('── OVERWORLD CONTROLS ────────────────────', P(4)|curses.A_BOLD),
        ('', None),
        ('  WASD / Arrows   Move your trainer ♟', P(6)|curses.A_BOLD),
        ('  SPACE / ENTER   Confirm / Talk to NPC', P(6)|curses.A_BOLD),
        ('  M               Open party & items menu', P(6)|curses.A_BOLD),
        ('  ESC             Pause menu', P(5)|curses.A_DIM),
        ('', None),
        ('── IN BATTLE ─────────────────────────────', P(4)|curses.A_BOLD),
        ('', None),
        ('  ▸ FIGHT   Attack with one of your moves', P(5)),
        ('  ▸ CATCH   Throw a ball at a wild Claudémon', P(5)),
        ('  ▸ ITEM    Use a Potion, Hi-Potion, or Revive', P(5)),
        ('  ▸ RUN     Try to escape a wild battle', P(5)),
        ('', None),
        ('── TYPE CHART ────────────────────────────', P(4)|curses.A_BOLD),
        ('  Neural > Logic   Data > Spark   Spark > Neural', P(5)|curses.A_DIM),
    ]
    for i, (text, attr) in enumerate(lines):
        y = 3 + i
        if y >= H - 4: break
        if attr is None:
            pass
        else:
            _p(scr, H, W, y, 2, text[:W-4], attr)

    _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
    if (tick // 18) % 2 == 0:
        msg = '[ SPACE ] ▸ Begin your journey!'
        _p(scr, H, W, H-2, max(1,(W-len(msg))//2), msg, P(2)|curses.A_BOLD)
    scr.refresh()


def draw_pause(scr, H, W):
    P = curses.color_pair
    bw = 46; bh = 12
    by = (H-bh)//2; bx = (W-bw)//2
    try:
        # Shadow
        for r in range(bh+1):
            scr.addstr(by+r+1, bx+2, '▒'*bw, P(5)|curses.A_DIM)
        # Box
        scr.addstr(by,      bx, '╔'+'═'*(bw-2)+'╗', P(7)|curses.A_BOLD)
        for r in range(1, bh-1):
            scr.addstr(by+r, bx, '║'+' '*(bw-2)+'║', P(7))
        scr.addstr(by+bh-1, bx, '╚'+'═'*(bw-2)+'╝', P(7)|curses.A_BOLD)
        # Header
        scr.addstr(by+1, bx+1, '░'*(bw-2), P(7)|curses.A_DIM)
        pause_title = '  ||  C L A U D É M O N  P A U S E D  ||  '
        scr.addstr(by+1, bx+max(0,(bw-len(pause_title))//2), pause_title, P(7)|curses.A_BOLD)
        scr.addstr(by+2, bx+1, '═'*(bw-2), P(7)|curses.A_DIM)
        # Options
        scr.addstr(by+4, bx+6, '▸ [ R ]  Resume game', P(3)|curses.A_BOLD)
        scr.addstr(by+6, bx+6, '▸ [ S ]  Save game', P(4)|curses.A_BOLD)
        scr.addstr(by+8, bx+6, '▸ [ Q ]  Quit to Claudcade', P(2)|curses.A_BOLD)
        scr.addstr(by+10, bx+1, '─'*(bw-2), P(7)|curses.A_DIM)
    except curses.error:
        pass
    scr.refresh()


def save_game(party: list[ClaudemonInstance], items: dict[str, int],
              area: str, px: int, py: int, pokedex: set[str]) -> None:
    data = {
        'party': [c.save_dict() for c in party],
        'items': items,
        'area':  area,
        'px':    px,
        'py':    py,
        'pokedex': list(pokedex),
    }
    with open(SAVE_PATH, 'w') as f:
        json.dump(data, f, indent=2)


def load_game() -> tuple[list[ClaudemonInstance], dict[str, int], str, int, int, set[str]]:
    with open(SAVE_PATH) as f:
        d = json.load(f)
    party   = [ClaudemonInstance.from_dict(c) for c in d['party']]
    items   = d['items']
    area    = d.get('area', 'startup')
    px, py  = d.get('px', 5), d.get('py', 8)
    pokedex = set(d.get('pokedex', []))
    return party, items, area, px, py, pokedex


def main(scr):
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()

    state          = TITLE
    party: list[ClaudemonInstance] = []
    items: dict[str, int]    = {'Claudéball': 5, 'Potion': 3}
    pokedex: set[str]        = set()
    world: Overworld | None = None
    battle: Battle | None   = None
    npc_data       = None
    starter_cursor = 0
    tick           = 0
    nxt            = time.perf_counter()
    has_save       = os.path.exists(SAVE_PATH)
    dialogue_lines : list[str] = []
    dialogue_idx   = 0
    after_dialogue = None

    def start_world(area, px, py):
        nonlocal world
        world = Overworld(party, items, area, px, py)

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

        UP    = any(k in keys for k in (curses.KEY_UP,    ord('w'), ord('k')))
        DOWN  = any(k in keys for k in (curses.KEY_DOWN,  ord('s'), ord('j')))
        LEFT  = any(k in keys for k in (curses.KEY_LEFT,  ord('a')))
        RIGHT = any(k in keys for k in (curses.KEY_RIGHT, ord('d')))
        OK    = any(k in keys for k in (ord('\n'), 10, 13, ord(' '), ord('l')))
        ESC   = 27 in keys
        if state == TITLE:
            draw_title(scr, H, W, tick)
            if ord(' ') in keys:
                state = STARTER_SELECT
            elif ord('l') in keys and has_save:
                party, items, area, px, py, pokedex = load_game()
                start_world(area, px, py)
                state = OVERWORLD
        elif state == STARTER_SELECT:
            draw_starter_select(scr, H, W, starter_cursor, tick)
            if LEFT:  starter_cursor = (starter_cursor - 1) % 3
            if RIGHT: starter_cursor = (starter_cursor + 1) % 3
            if UP:    starter_cursor = (starter_cursor - 1) % 3
            if DOWN:  starter_cursor = (starter_cursor + 1) % 3
            if OK:
                chosen = STARTERS[starter_cursor]
                starter = ClaudemonInstance(chosen, 5)
                party   = [starter]
                pokedex.add(chosen)
                # Intro dialogue
                dialogue_lines = [
                    'Prof. Claude: Welcome, Trainer!',
                    f'You chose {chosen}!',
                    'Your journey begins in Startup Town.',
                    'Catch Claudémon, explore the world.',
                    'Good luck!',
                ]
                dialogue_idx   = 0
                after_dialogue = lambda: start_world(*PLAYER_START) or None
                state = DIALOGUE
        elif state == HOW_TO_PLAY:
            draw_how_to_play(scr, H, W, tick)
            if OK:
                state = OVERWORLD
        elif state == DIALOGUE:
            scr.erase()
            P = curses.color_pair
            _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
            _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
            for r in range(1, H-1):
                _p(scr, H, W, r, 0, '║', P(5))
                _p(scr, H, W, r, W-1, '║', P(5))
            # Decorative top
            _p(scr, H, W, 1, 1, '░'*(W-2), P(5)|curses.A_DIM)
            _p(scr, H, W, 1, max(1,(W-14)//2), '  CLAUDÉMON  ', P(6)|curses.A_BOLD)
            _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
            # Cycling art from starters in middle
            arts = [CLAUDEMON[s]['art'] for s in STARTERS]
            art  = arts[(tick // 40) % len(arts)]
            ay   = 4
            for ai, aline in enumerate(art):
                _p(scr, H, W, ay+ai, max(1,(W-len(aline))//2), aline, P(1)|curses.A_BOLD)
            # Dialogue text box
            box_y = H - 8
            _p(scr, H, W, box_y,   0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
            for br in range(1, 5):
                _p(scr, H, W, box_y+br, 1, ' '*(W-2), 0)
            if dialogue_idx < len(dialogue_lines):
                line = dialogue_lines[dialogue_idx]
                _p(scr, H, W, box_y+2, 3, line[:W-6], P(5)|curses.A_BOLD)
            # Progress dots
            total_d = len(dialogue_lines)
            dots = '  '.join('◉' if i == dialogue_idx else '○' for i in range(total_d))
            _p(scr, H, W, box_y+4, max(1,(W-len(dots))//2), dots, P(5)|curses.A_DIM)
            if (tick // 15) % 2 == 0:
                _p(scr, H, W, box_y+3, W-5, '▼', P(4)|curses.A_BOLD)
            _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
            _p(scr, H, W, H-2, max(1,(W-22)//2), '[ SPACE ] Continue', P(5)|curses.A_DIM)
            scr.refresh()
            if OK:
                dialogue_idx += 1
                if dialogue_idx >= len(dialogue_lines):
                    if after_dialogue:
                        after_dialogue()
                        after_dialogue = None
                    state = HOW_TO_PLAY if not world else OVERWORLD
        elif state == OVERWORLD:
            world.draw(scr, H, W, tick)
            for k in keys:
                world.handle_key(k)
            if ord('m') in keys:
                state = PARTY_MENU

            res = world.result; world.result = None
            if res:
                if res[0] == 'battle':
                    enemy = res[1]
                    pokedex.add(enemy.name)
                    battle = Battle(party, wild=enemy, items=items)
                    state  = IN_BATTLE
                elif res[0] == 'npc':
                    npc = res[1]
                    if npc.get('role') == 'professor':
                        dialogue_lines = [
                            'Prof. Claude: How is your journey?',
                            'This world is full of Claudémon.',
                            'Catch them, train them, become the best!',
                        ]
                        dialogue_idx   = 0
                        after_dialogue = None
                        state = DIALOGUE

            if ESC:
                state = PAUSE
        elif state == IN_BATTLE:
            battle.draw(scr, H, W, tick)
            for k in keys:
                battle.handle_key(k)

            if battle.result and battle.state not in (ANIMATING, LEVEL_UP):
                if battle.result == 'win':
                    world.msg = 'You won!'
                    world.msg_timer = 90
                    state = OVERWORLD
                elif battle.result == 'lose':
                    world.msg = 'You blacked out...'
                    world.msg_timer = 90
                    # Heal lead Claudémon to 1 HP
                    for c in party:
                        if c.alive: c.hp = max(1, c.max_hp // 4)
                    state = OVERWORLD
                elif battle.result == 'escaped':
                    state = OVERWORLD
                elif battle.result == 'caught':
                    caught = battle.caught_name
                    pokedex.add(caught)
                    new_mon = battle.wild
                    if len(party) < 6:
                        party.append(new_mon)
                    world.msg = f'{new_mon.name} was added to your party!'
                    world.msg_timer = 90
                    state = OVERWORLD
        elif state == PARTY_MENU:
            scr.erase()
            P = curses.color_pair
            _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
            _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
            for r in range(1, H-1):
                _p(scr, H, W, r, 0, '║', P(5))
                _p(scr, H, W, r, W-1, '║', P(5))

            # Header bar
            _p(scr, H, W, 1, 1, '░'*(W-2), P(5)|curses.A_DIM)
            title = '★  P A R T Y  M E N U  ★'
            _p(scr, H, W, 1, max(1,(W-len(title))//2), title, P(6)|curses.A_BOLD)
            _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

            # Info bar: dex count + items
            total = len(CLAUDEMON)
            dex_str = f'CLAUDÉDEX: {len(pokedex):>2}/{total}'
            _p(scr, H, W, 3, 2, dex_str, P(4)|curses.A_BOLD)
            _p(scr, H, W, 3, 2+len(dex_str)+2, '│', P(5)|curses.A_DIM)
            ix = 2 + len(dex_str) + 4
            for nm, cnt in items.items():
                item_str = f'{nm} ×{cnt}'
                _p(scr, H, W, 3, ix, item_str, P(5)|curses.A_DIM)
                ix += len(item_str) + 3
            _p(scr, H, W, 4, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

            # Party members — two-column layout
            _p(scr, H, W, 5, 2, 'PARTY:', P(5)|curses.A_BOLD)
            col_w = (W - 4) // 2
            BAR_W = min(16, col_w - 20)
            for i, c in enumerate(party):
                col_x = 2 + (i % 2) * col_w
                row   = 6 + (i // 2) * 5
                alive_attr = P(1)|curses.A_BOLD if c.alive else P(5)|curses.A_DIM

                # Name + level + type
                type_str = f'[{c.type1}]' + (f'[{c.type2}]' if c.type2 else '')
                _p(scr, H, W, row,   col_x, f'{c.name}', alive_attr)
                _p(scr, H, W, row,   col_x+len(c.name)+1, f'Lv.{c.level}', P(5)|curses.A_DIM)
                _p(scr, H, W, row,   col_x+len(c.name)+8, type_str, P(4)|curses.A_DIM)

                # HP bar
                hp_f  = c.hp / c.max_hp if c.max_hp else 0
                hp_cp = P(3) if hp_f > 0.5 else (P(4) if hp_f > 0.25 else P(2))
                filled = max(0, int(BAR_W * hp_f))
                hp_bar = '█' * filled + '░' * (BAR_W - filled)
                if c.alive:
                    _p(scr, H, W, row+1, col_x, 'HP', P(3)|curses.A_BOLD)
                    _p(scr, H, W, row+1, col_x+3, hp_bar, hp_cp|curses.A_BOLD)
                    _p(scr, H, W, row+1, col_x+3+BAR_W+1, f'{c.hp}/{c.max_hp}', P(5)|curses.A_DIM)
                else:
                    _p(scr, H, W, row+1, col_x, '✗ FAINTED', P(2)|curses.A_BOLD)

                # EXP bar
                from .entities import _calc_stat as _cs
                exp_next = int(4 * c.level ** 3 / 5)
                exp_f    = c.exp / max(1, exp_next)
                exp_fill = max(0, int(BAR_W * exp_f))
                exp_bar  = '▪' * exp_fill + '·' * (BAR_W - exp_fill)
                _p(scr, H, W, row+2, col_x, 'EX', P(8)|curses.A_BOLD)
                _p(scr, H, W, row+2, col_x+3, exp_bar, P(8)|curses.A_DIM)

                # Moves
                moves_str = '  '.join(f'{m}' for m in c.moves[:4])
                _p(scr, H, W, row+3, col_x+2, moves_str[:col_w-3], P(5)|curses.A_DIM)

                # Status
                if c.status:
                    _p(scr, H, W, row, col_x+col_w-10, f'[{c.status.upper()}]', P(2)|curses.A_BOLD)

            _p(scr, H, W, H-3, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
            _p(scr, H, W, H-2, 2, 'M / ESC — Close party menu', P(5)|curses.A_DIM)
            scr.refresh()
            if ESC or ord('q') in keys or ord('m') in keys:
                state = OVERWORLD
        elif state == PAUSE:
            if world: world.draw(scr, H, W, tick)
            draw_pause(scr, H, W)
            if ord('r') in keys or ord('R') in keys: state = OVERWORLD
            if ord('s') in keys or ord('S') in keys:
                if world:
                    save_game(party, items, world.area, world.px, world.py, pokedex)
                    has_save = True
            if ord('q') in keys or ord('Q') in keys: break
            if ESC: state = OVERWORLD


def run():
    run_game(main, 'Claudémon')
