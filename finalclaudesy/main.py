"""Main game loop and state machine for Final Claudesy."""
import curses, time, json, os, random

from .data     import STORY
from .entities import Party
from .battle   import Battle
from .explore  import WorldMap, TownScreen, DungeonScreen, PartyMenu
from .ui       import safe_add, box, center, setup_colors
from claudcade_scores import submit_async

FPS      = 30
SAVE_PATH = os.path.expanduser('~/finalclaudesy_save.json')

# ── Title screen ───────────────────────────────────────────────────────────────
TITLE_ART = [
    r"  ███████ ██ ███   ███   ███   ███  ███  ██  ██ ██ ███ ███ ███████  ██",
    r" ██      ███  ██  ██ ██ ██ ██ ██    ██ ██ ██ ██ ███ ██████ ██   █████",
    r" ██████ ███   ██ ██   ██ ██ ██ ███  ██ ██ ███  ██ █ ███ ████ █████ ██ ",
    r" ██     ███ █  █ ███ ███  ███  ███ ████  ██  ██  ████████ █████ ██ ",
    r" ███████ ███ █  █ ██   ██ █   ███  ██ ██  █    ██ ██  ████ █████ ██ ",
]

def draw_title(scr, H, W, tick, has_save, ng_plus_available=False):
    P = curses.color_pair
    scr.erase()

    safe_add(scr, 0, 0, '╔' + '═'*(W-2) + '╗', P(5)|curses.A_BOLD)
    safe_add(scr, H-1, 0, '╚' + '═'*(W-2) + '╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        safe_add(scr, r, 0, '║', P(5)|curses.A_BOLD)
        safe_add(scr, r, W-1, '║', P(5)|curses.A_BOLD)

    # Starfield — fewer stars, slower blink
    random.seed(42)
    for _ in range(20):
        r = random.randint(1, H-2)
        c = random.randint(1, W-2)
        ch = random.choice(['·', '+', '*'])
        if (tick // 30 + r + c) % 5 == 0:
            safe_add(scr, r, c, ch, P(5)|curses.A_DIM)
    random.seed()

    tr = max(2, H//2 - 7)
    colors = [4, 1, 6, 4, 1]  # magenta, red, cyan cycle
    for i, line in enumerate(TITLE_ART):
        col = max(1, (W - len(line)) // 2)
        color_idx = (i + tick // 20) % len(colors)
        attr = P(colors[color_idx])|curses.A_BOLD
        safe_add(scr, tr+i, col, line, attr)

    sep = '▓▒░░▒▓'
    sub = f'{sep} A TERMINAL JRPG {sep}'
    center(scr, tr+6, sub, W, P(6)|curses.A_BOLD)

    if (tick // 20) % 2 == 0:
        center(scr, H//2+2, '╔════════════════════╗', W, P(4))
        center(scr, H//2+3, '  [ SPACE ] New Game  ', W, P(4)|curses.A_BOLD)
        center(scr, H//2+4, '╚════════════════════╝', W, P(4))
        if has_save:
            center(scr, H//2+6, '╔════════════════════╗', W, P(3))
            center(scr, H//2+7, '  [ L ] Load Game  ', W, P(3)|curses.A_BOLD)
            center(scr, H//2+8, '╚════════════════════╝', W, P(3))
        if ng_plus_available:
            y_offset = 10 if has_save else 6
            center(scr, H//2+y_offset, '╔═══════════════════════════════╗', W, P(6))
            center(scr, H//2+y_offset+1, '  [ N ] NewGame+ — keep levels  ', W, P(6)|curses.A_BOLD)
            center(scr, H//2+y_offset+2, '╚═══════════════════════════════╝', W, P(6))

    ctrl = '║ WASD:Move  J/Space:Confirm  Q/ESC:Back  M:Menu ║'
    center(scr, H-3, ctrl, W, P(5))
    scr.refresh()


def draw_story(scr, H, W, lines, tick):
    P = curses.color_pair
    scr.erase()

    safe_add(scr, 0, 0, '╔' + '═'*(W-2) + '╗', P(5)|curses.A_BOLD)
    safe_add(scr, H-1, 0, '╚' + '═'*(W-2) + '╝', P(5)|curses.A_BOLD)
    for r in range(1, H-1):
        safe_add(scr, r, 0, '║', P(5)|curses.A_BOLD)
        safe_add(scr, r, W-1, '║', P(5)|curses.A_BOLD)

    header = '▓ STORY ▓'
    center(scr, 1, header, W, P(6)|curses.A_BOLD)
    safe_add(scr, 2, 0, '╠' + '═'*(W-2) + '╣', P(5)|curses.A_BOLD)

    start = max(3, H//2 - len(lines)//2 - 1)
    for i, line in enumerate(lines):
        if line == '[ Press SPACE ]':
            if (tick // 15) % 2 == 0:
                center(scr, H-4, '┤ ' + line + ' ├', W, P(5)|curses.A_BOLD)
        else:
            center(scr, start+i, line, W, P(5))
    scr.refresh()


# ── Main ───────────────────────────────────────────────────────────────────────
def main(scr):
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()

    state      = 'TITLE'
    party      = None
    world      = None
    town       = None
    dungeon    = None
    battle     = None
    menu       = None
    story_lines= []
    after_story= None
    battle_msgs= []
    result_timer = 0
    tick       = 0
    nxt        = time.perf_counter()
    _key_age: dict[int, int] = {}   # sticky-input age tracker

    has_save = os.path.exists(SAVE_PATH)

    while True:
        now = time.perf_counter()
        if now < nxt:
            time.sleep(max(0, nxt - now - 0.001))
            continue
        nxt += 1 / FPS
        tick += 1

        H, W = scr.getmaxyx()
        # Sticky input: a key remains in `keys` for 4 frames after its last
        # actual press. Compensates for unreliable terminal key auto-repeat
        # so single taps produce smooth movement (mirrors claudcade_engine).
        seen_now = set()
        while True:
            k = scr.getch()
            if k == -1: break
            seen_now.add(k)
        _key_age = {k: a + 1 for k, a in _key_age.items() if a + 1 < 4}
        for k in seen_now:
            _key_age[k] = 0
        keys = set(_key_age.keys())

        # ESC or M opens party menu when exploring (M matches documented controls).
        if (27 in keys or ord('m') in keys or ord('M') in keys) and \
           state not in ('BATTLE','BATTLE_RESULT','STORY','TITLE'):
            if state in ('TOWN','DUNGEON','WORLD'):
                menu   = PartyMenu(party)
                state  = 'MENU'

        # ── State logic ────────────────────────────────────────────────────────
        if state == 'TITLE':
            # Detect a finished save to offer NewGame+ on the title screen.
            ng_plus_available = False
            if has_save:
                try:
                    with open(SAVE_PATH) as f:
                        ng_plus_available = bool(json.load(f).get('newgame_plus', False))
                except (OSError, json.JSONDecodeError, KeyError, ValueError):
                    ng_plus_available = False
            draw_title(scr, H, W, tick, has_save, ng_plus_available)
            if ord(' ') in keys:
                party     = Party()
                world     = WorldMap(party)
                story_lines = STORY['intro']
                after_story = 'WORLD'
                state     = 'STORY'
                tick      = 0
            elif ord('l') in keys and has_save:
                try:
                    with open(SAVE_PATH) as f:
                        party = Party.from_dict(json.load(f))
                    world = WorldMap(party)
                    state = 'WORLD'
                except (OSError, json.JSONDecodeError, KeyError, ValueError):
                    pass  # corrupt save → stay on title screen
            elif ord('n') in keys and ng_plus_available:
                # NewGame+: load the existing save and carry levels forward.
                try:
                    with open(SAVE_PATH) as f:
                        party = Party.from_dict(json.load(f)).start_newgame_plus()
                    world = WorldMap(party)
                    story_lines = ['The cycle begins again...', '',
                                   'You retain your strength but the world is harsher.',
                                   '', '[ Press SPACE ]']
                    after_story = 'WORLD'
                    state = 'STORY'
                    tick = 0
                except (OSError, json.JSONDecodeError, KeyError, ValueError):
                    pass

        elif state == 'STORY':
            draw_story(scr, H, W, story_lines, tick)
            if ord(' ') in keys or ord('\n') in keys:
                state = after_story

        elif state == 'WORLD':
            if world is None: world = WorldMap(party)
            world.draw(scr, H, W, tick)

            for k in keys:
                world.handle_key(k)
            if ord('m') in keys:
                menu  = PartyMenu(party)
                state = 'MENU'
                continue

            res = world.result
            world.result = None
            if res:
                if res[0] == 'town':
                    town  = TownScreen(party, res[1])
                    state = 'TOWN'
                elif res[0] == 'dungeon':
                    name, region = res[1], res[2]
                    dungeon = DungeonScreen(party, name)
                    state   = 'DUNGEON'
                elif res[0] == 'battle':
                    _, group, region = res
                    battle = Battle(party, group)
                    state  = 'BATTLE'

        elif state == 'TOWN':
            town.draw(scr, H, W, tick)
            for k in keys: town.handle_key(k)
            if town.result == 'leave':
                town   = None
                state  = 'WORLD'
            elif town.result and town.result[0] == 'battle':
                _, group, region = town.result
                battle = Battle(party, group)
                town.result = None
                state  = 'BATTLE'

        elif state == 'DUNGEON':
            dungeon.draw(scr, H, W, tick)
            for k in keys: dungeon.handle_key(k)
            res = dungeon.result
            dungeon.result = None
            if res:
                if res == 'exit':
                    dungeon = None; state = 'WORLD'
                elif res[0] == 'battle':
                    _, group, region = res
                    battle = Battle(party, group)
                    state  = 'BATTLE'
                elif res[0] == 'boss':
                    boss_name = res[1]
                    # story before final boss
                    if boss_name == 'SYNTHOS' and 'before_final' not in party.story_flags:
                        party.story_flags.add('before_final')
                        story_lines = STORY['before_final']
                        after_story = '_BOSS_' + boss_name
                        state = 'STORY'
                    else:
                        battle = Battle(party, [boss_name], is_boss=True)
                        state  = 'BATTLE'

        elif state.startswith('_BOSS_'):
            boss_name = state[6:]
            battle    = Battle(party, [boss_name], is_boss=True)
            state     = 'BATTLE'

        elif state == 'BATTLE':
            battle.draw(scr, H, W, tick)
            for k in keys: battle.handle_key(k)

            if battle.result:
                if battle.result == 'win':
                    battle_msgs = battle.battle_end_rewards()
                    total_lv = sum(m.level for m in party.members)
                    submit_async('finalclaudesy', total_lv * 1000 + party.gold,
                                 f'Lv {max(m.level for m in party.members)}', [None])
                    boss = next((e for e in battle.enemies if e.boss), None)
                    if boss:
                        bname = boss.name
                        party.dungeon_done.add(dungeon.dname if dungeon else '')
                        if bname == 'Vine Colossus' and 'boss1' not in party.story_flags:
                            party.story_flags.add('boss1')
                            battle_msgs.append('')
                            battle_msgs += STORY['after_boss1']
                        elif bname == 'Pyralith' and 'boss2' not in party.story_flags:
                            party.story_flags.add('boss2')
                            battle_msgs.append('')
                            battle_msgs += STORY['after_boss2']
                        elif bname == 'SYNTHOS':
                            battle_msgs.append('')
                            battle_msgs += STORY['victory']
                            # Persist NewGame+ unlock so the title screen offers it.
                            party.newgame_plus = True
                            try:
                                with open(SAVE_PATH, 'w') as f:
                                    json.dump(party.save_dict(), f)
                            except OSError: pass
                            state = 'BATTLE_RESULT'
                    state = 'BATTLE_RESULT'
                elif battle.result == 'lose':
                    battle_msgs = ['The party was defeated...', '', 'GAME OVER']
                    state = 'BATTLE_RESULT'
                elif battle.result == 'escaped':
                    battle_msgs = ['You escaped!']
                    state = 'BATTLE_RESULT'
                result_timer = 0

        elif state == 'BATTLE_RESULT':
            battle.draw_result(scr, H, W, battle_msgs, 0)
            result_timer += 1
            if ord(' ') in keys and result_timer > 30:
                if battle.result == 'lose':
                    # Return to last town or start
                    party.members[0].hp = max(1, party.members[0].max_hp // 4)
                    for m in party.members[1:]: m.hp = 1
                    state = 'WORLD'
                elif 'SYNTHOS' in [e.name for e in battle.enemies]:
                    state = 'TITLE'
                else:
                    if dungeon:
                        state = 'DUNGEON'
                    elif town:
                        state = 'TOWN'
                    else:
                        state = 'WORLD'
                battle_msgs = []

        elif state == 'MENU':
            menu.draw(scr, H, W, tick)
            for k in keys: menu.handle_key(k)
            if menu.result == 'close':
                menu  = None
                state = 'WORLD'

        elif state == 'GAME_OVER':
            scr.erase()
            box(scr, 0, 0, H, W, '', 2)
            center(scr, H//2-1, 'G A M E   O V E R', W, curses.color_pair(2)|curses.A_BOLD)
            center(scr, H//2+1, '[ SPACE ] Return to title', W, curses.color_pair(5))
            scr.refresh()
            if ord(' ') in keys:
                state = 'TITLE'; party = None

        # ESC at the title screen quits the game.
        if 27 in keys and state == 'TITLE':
            break


def run():
    curses.wrapper(main)
    print('\n  [ Final Claudesy — thanks for playing! ]\n')


if __name__ == '__main__':
    run()
