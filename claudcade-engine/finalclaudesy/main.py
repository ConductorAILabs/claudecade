"""Main game loop and state machine for Final Claudesy."""
import curses, time, json, os, random

from .data     import STORY
from .entities import Party
from .battle   import Battle
from .explore  import WorldMap, TownScreen, DungeonScreen, PartyMenu
from .ui       import safe_add, box, center
from claudcade_engine import setup_colors, run_game
from claudcade_engine import draw_how_to_play as _engine_how_to_play
try:
    from claudcade_scores import submit_async as _submit_async
except ImportError:
    def _submit_async(*a, **kw): pass

FPS      = 30
SAVE_PATH = os.path.expanduser('~/finalclaudesy_save.json')
TITLE_ART = [
    r"  ╔══════════════════════════════════════════════════════════════════════╗",
    r"  ║  ███████╗██╗███╗   ██╗ █████╗ ██╗      ██████╗██╗      █████╗  ██╗ ║",
    r"  ║  ██╔════╝██║████╗  ██║██╔══██╗██║     ██╔════╝██║     ██╔══██╗ ██║ ║",
    r"  ║  █████╗  ██║██╔██╗ ██║███████║██║     ██║     ██║     ███████║ ██║ ║",
    r"  ║  ██╔══╝  ██║██║╚██╗██║██╔══██║██║     ██║     ██║     ██╔══██║ ╚═╝ ║",
    r"  ║  ██║     ██║██║ ╚████║██║  ██║███████╗╚██████╗███████╗██║  ██║ ██╗ ║",
    r"  ║  ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═╝ ║",
    r"  ║              ✦  C L A U D E S Y  ✦   A  T E R M I N A L  J R P G  ✦ ║",
    r"  ╚══════════════════════════════════════════════════════════════════════╝",
]

def draw_title(scr, H, W, tick, has_save):
    P = curses.color_pair
    scr.erase()
    box(scr, 0, 0, H, W, '', 5)

    # Animated starfield
    random.seed(42)
    stars = [(random.randint(1, H-2), random.randint(1, W-2), random.choice(['·', '✦', '*', '°', '+'])) for _ in range(80)]
    random.seed()
    for r, c, ch in stars:
        if (tick // 8 + r * 3 + c * 7) % 6 == 0:
            safe_add(scr, r, c, ch, P(6)|curses.A_BOLD)
        elif (tick // 12 + r + c) % 4 == 0:
            safe_add(scr, r, c, ch, P(5)|curses.A_DIM)

    # Title art — centered block
    tr = max(2, H//2 - len(TITLE_ART)//2 - 2)
    for i, line in enumerate(TITLE_ART):
        col = max(1, (W - len(line)) // 2)
        if i == 0 or i == len(TITLE_ART)-1:
            attr = P(5)|curses.A_BOLD
        elif i == len(TITLE_ART)-2:
            attr = P(6)|curses.A_BOLD
        elif i % 2 == 0:
            attr = P(4)|curses.A_BOLD
        else:
            attr = P(1)|curses.A_BOLD
        safe_add(scr, tr+i, col, line, attr)

    # Blinking prompts
    prompt_y = tr + len(TITLE_ART) + 2
    if (tick // 20) % 2 == 0:
        center(scr, prompt_y,   '╔══════════════════╗', W, P(4)|curses.A_BOLD)
        center(scr, prompt_y+1, '║  [ SPACE ]  New Game  ║', W, P(4)|curses.A_BOLD)
        center(scr, prompt_y+2, '╚══════════════════╝', W, P(4)|curses.A_BOLD)
        if has_save:
            center(scr, prompt_y+4, '[ L ]  Continue', W, P(3)|curses.A_BOLD)
    center(scr, H-3, 'WASD/Arrows: Move   Space: Confirm   Q/ESC: Quit   M: Menu', W, P(5)|curses.A_DIM)
    scr.refresh()


def draw_how_to_play(scr, H, W, tick):
    _engine_how_to_play(
        scr, H, W, tick,
        goal=[
            'Lead Claude, Haiku, and Opus across three regions to defeat SYNTHOS.',
            'Explore towns, conquer dungeons, defeat bosses.',
        ],
        controls=[
            'WASD / Arrows    Move',
            'SPACE / Enter    Confirm',
            'Q / ESC          Back',
            'M                Party menu',
        ],
        tips=[
            '• Rest at inns to restore HP/MP',
            '• Save often',
            "• Haiku's magic exploits enemy weaknesses · Opus heals",
        ],
    )


def draw_story(scr, H, W, lines, tick):
    P = curses.color_pair
    scr.erase()

    # Starfield backdrop
    random.seed(99)
    for _ in range(50):
        r = random.randint(1, H-2)
        c = random.randint(1, W-2)
        if (tick // 15 + r + c) % 7 == 0:
            safe_add(scr, r, c, '·', P(5)|curses.A_DIM)
    random.seed()

    # Decorative border with corners
    box(scr, 0, 0, H, W, '', 5)
    # Inner accent lines
    safe_add(scr, 2,    0, '╠' + '─'*(W-2) + '╣', P(5)|curses.A_DIM)
    safe_add(scr, H-3,  0, '╠' + '─'*(W-2) + '╣', P(5)|curses.A_DIM)

    # Text block
    story_lines = [l for l in lines if l != '[ Press SPACE ]']
    start = max(3, H//2 - len(story_lines)//2)
    for i, line in enumerate(story_lines):
        # Speaker lines get color treatment
        if line.startswith('Claude:') or line.startswith('  CLAUDE'):
            attr = P(1)|curses.A_BOLD
        elif line.startswith('Haiku:') or line.startswith('  HAIKU'):
            attr = P(6)|curses.A_BOLD
        elif line.startswith('Opus:') or line.startswith('  OPUS'):
            attr = P(3)|curses.A_BOLD
        elif line.startswith('SYNTHOS:') or line.startswith('  > '):
            attr = P(2)|curses.A_BOLD
        elif line.startswith('S Y N T H O S') or line.startswith('F I N A L') or line.startswith('T H E'):
            attr = P(4)|curses.A_BOLD
        else:
            attr = P(5)
        center(scr, start+i, line, W, attr)

    # Flashing prompt
    if (tick // 15) % 2 == 0:
        center(scr, H-2, '✦ [ Press SPACE ] ✦', W, P(6)|curses.A_BOLD)
    scr.refresh()
def main(scr):
    curses.cbreak(); curses.noecho(); scr.keypad(True)
    scr.nodelay(True); curses.curs_set(0)
    setup_colors()

    state      = 'TITLE'
    prev_state = 'WORLD'   # tracks state before entering MENU
    party      = None
    world      = None
    town       = None
    dungeon    = None
    battle     = None
    menu       = None
    story_key  = None
    story_lines= []
    after_story= None
    battle_msgs= []
    result_timer = 0
    tick       = 0
    nxt        = time.perf_counter()

    has_save = os.path.exists(SAVE_PATH)

    while True:
        now = time.perf_counter()
        if now < nxt:
            time.sleep(max(0, nxt - now - 0.001))
            continue
        nxt += 1 / FPS
        tick += 1

        H, W = scr.getmaxyx()
        keys = set()
        while True:
            k = scr.getch()
            if k == -1: break
            keys.add(k)

        if 27 in keys and state not in ('BATTLE','BATTLE_RESULT','STORY','TITLE'):
            if state in ('TOWN','DUNGEON','WORLD'):
                menu       = PartyMenu(party)
                prev_state = state
                state      = 'MENU'
        if state == 'TITLE':
            draw_title(scr, H, W, tick, has_save)
            if ord(' ') in keys:
                state = 'HOW_TO_PLAY'
                tick  = 0
            elif ord('l') in keys and has_save:
                with open(SAVE_PATH) as f:
                    party = Party.from_dict(json.load(f))
                world = WorldMap(party)
                state = 'WORLD'

        elif state == 'HOW_TO_PLAY':
            draw_how_to_play(scr, H, W, tick)
            if ord(' ') in keys:
                party       = Party()
                world       = WorldMap(party)
                story_lines = STORY['intro']
                after_story = 'WORLD'
                state       = 'STORY'
                tick        = 0

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
                menu       = PartyMenu(party)
                prev_state = 'WORLD'
                state      = 'MENU'
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
                    _submit_async('finalclaudesy', total_lv * 1000 + party.gold,
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
                    # Survive wipe: leader revives at 25% HP, rest at 1
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
                state = prev_state

        # ESC from anywhere goes to title only if on title
        if 27 in keys and state == 'TITLE':
            break


def run():
    run_game(main, 'Final Claudesy')


if __name__ == '__main__':
    run()
