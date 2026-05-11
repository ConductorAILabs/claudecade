#!/usr/bin/env python3
"""Claudemon - Creature-catching RPG - ESC to pause / quit."""
from __future__ import annotations

import curses
import random
from dataclasses import dataclass, field

from claudcade_engine import (
    ENEMY,
    GOLD,
    GOOD,
    NEUTRAL,
    PLAYER,
    SELECT,
    SPECIAL,
    WATER,
    Engine,
    Input,
    Renderer,
    Scene,
)
from claudcade_engine import draw_how_to_play as _engine_how_to_play
from claudcade_scores import player_label, submit_async

FPS         = 30
MAP_W       = 40
MAP_H       = 20
PARTY_MAX   = 6
ENCOUNTER_RATE  = 0.06   # per step into grass
CATCH_RATE_CAP  = 0.85

CONTROLS_PAUSE = [
    'WASD / Arrows  Move',
    'SPACE / ENTER  Confirm / Interact',
    'M              Open party',
    'ESC            Pause / Resume',
    'Q              Quit to Claudcade',
]

# Type triangle: FIRE > GRASS > WATER > FIRE; NORMAL is neutral.
TYPE_COLOR = {'FIRE': ENEMY, 'WATER': WATER, 'GRASS': GOOD, 'NORMAL': NEUTRAL}
MATCHUP: dict[str, dict[str, float]] = {
    'FIRE':   {'GRASS': 2.0, 'WATER': 0.5, 'FIRE': 1.0, 'NORMAL': 1.0},
    'WATER':  {'FIRE':  2.0, 'GRASS': 0.5, 'WATER': 1.0, 'NORMAL': 1.0},
    'GRASS':  {'WATER': 2.0, 'FIRE':  0.5, 'GRASS': 1.0, 'NORMAL': 1.0},
    'NORMAL': {'FIRE':  1.0, 'WATER': 1.0, 'GRASS': 1.0, 'NORMAL': 1.0},
}


@dataclass(frozen=True)
class Species:
    name:        str
    type:        str
    base_hp:     int
    base_dmg:    int
    catch_bonus: float = 0.0    # added to base catch chance
    sprite:      tuple[str, ...] = ()


SPECIES: tuple[Species, ...] = (
    Species('Embertail', 'FIRE',   22, 5,  0.0,
            ('   /\\_/\\   ', '  ( o.o )  ', '  > ^ <    ', '   ~~~~    ')),
    Species('Cinderpup', 'FIRE',   26, 6, -0.05,
            ('   (\\_/)   ', '  (=^.^=)  ', '   \\=*=/   ', '   ^^ ^^   ')),
    Species('Bubblefin', 'WATER',  24, 5,  0.05,
            ('   ___     ', '  /o  \\>   ', '  \\___/    ', '  ~ ~ ~    ')),
    Species('Drizzlek',  'WATER',  28, 6,  0.0,
            ('   .---.   ', '  ( o o )  ', '   \\_v_/   ', '   . . .   ')),
    Species('Leafling',  'GRASS',  22, 5,  0.05,
            ('    @@@    ', '   /o o\\   ', '   \\ - /   ', '    | |    ')),
    Species('Mossback',  'GRASS',  30, 5, -0.05,
            ('   .---.   ', '  /#####\\  ', '  ( - - )  ', '   \\___/   ')),
    Species('Sparkmite', 'NORMAL', 20, 7,  0.05,
            ('   .---.   ', '  ( O.O )  ', '   /=*=\\   ', '   `   `   ')),
)

BOSS = Species('CLAUDESYNTH', 'NORMAL', 90, 12, -1.0,
               ('   _____   ', '  /\\___/\\  ', ' < X . X > ',
                '  \\\\\\v///  ', '   `---`   '))


# ── Creature instance ─────────────────────────────────────────────────────────

@dataclass
class Creature:
    species: Species
    level:   int = 1
    hp:      int = 0
    max_hp:  int = 0
    xp:      int = 0
    caught:  bool = False    # True if the player owns it

    @classmethod
    def make(cls, sp: Species, level: int = 1, caught: bool = False) -> Creature:
        c = cls(species=sp, level=level, caught=caught)
        c.max_hp = sp.base_hp + (level - 1) * 4
        c.hp     = c.max_hp
        return c

    @property
    def damage(self) -> int:
        return self.species.base_dmg + (self.level - 1) * 2

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def heal_full(self) -> None:
        self.hp = self.max_hp

    def xp_for_next(self) -> int:
        return 8 + self.level * 4

    def gain_xp(self, amount: int) -> list[str]:
        msgs: list[str] = []
        self.xp += amount
        while self.xp >= self.xp_for_next():
            self.xp -= self.xp_for_next()
            self.level += 1
            self.max_hp += 4
            self.hp = self.max_hp
            msgs.append(f'{self.species.name} grew to Lv {self.level}!')
        return msgs


# ── Overworld map ─────────────────────────────────────────────────────────────

TILE_GRASS = '"'
TILE_TREE  = '#'
TILE_PATH  = '.'
TILE_WATER = '~'
TILE_HOME  = 'H'
TILE_BOSS  = 'B'
TILE_WALL  = '+'


def build_map() -> list[list[str]]:
    """Generate a small overworld grid (MAP_W x MAP_H)."""
    g: list[list[str]] = [[TILE_PATH for _ in range(MAP_W)] for _ in range(MAP_H)]

    # outer wall
    for x in range(MAP_W):
        g[0][x] = TILE_WALL
        g[MAP_H - 1][x] = TILE_WALL
    for y in range(MAP_H):
        g[y][0] = TILE_WALL
        g[y][MAP_W - 1] = TILE_WALL

    # tall-grass patches
    patches = [
        (4, 3, 8, 4),
        (20, 3, 7, 5),
        (4, 12, 9, 4),
        (22, 11, 10, 5),
        (15, 7, 6, 3),
    ]
    for (px, py, pw, ph) in patches:
        for y in range(py, py + ph):
            for x in range(px, px + pw):
                if 1 <= x < MAP_W - 1 and 1 <= y < MAP_H - 1:
                    g[y][x] = TILE_GRASS

    # water strip across the middle (with crossings)
    for x in range(1, MAP_W - 1):
        if x not in (9, 18, 28):
            g[10][x] = TILE_WATER

    # trees scattered around
    rng = random.Random(7)
    for _ in range(28):
        x = rng.randint(1, MAP_W - 2)
        y = rng.randint(1, MAP_H - 2)
        if g[y][x] == TILE_PATH:
            g[y][x] = TILE_TREE

    # home base bottom-left
    g[16][6] = TILE_HOME
    g[16][7] = TILE_PATH

    # boss top-right
    g[3][MAP_W - 4] = TILE_BOSS
    g[3][MAP_W - 5] = TILE_PATH
    return g


GRASS_TILES   = {TILE_GRASS}
WALKABLE      = {TILE_PATH, TILE_GRASS, TILE_HOME, TILE_BOSS}


# ── Game state ────────────────────────────────────────────────────────────────

@dataclass
class Game:
    grid:     list[list[str]]                  = field(default_factory=build_map)
    px:       int                              = 7
    py:       int                              = 16
    party:    list[Creature]                   = field(default_factory=list)
    active:   int                              = 0
    caught_species: set[str]                   = field(default_factory=set)
    boss_defeated:  bool                       = False
    boss_present:   bool                       = True
    last_msg: str                              = 'Welcome to Claudemon. Step in tall grass!'
    step_count: int                            = 0
    rng:      random.Random                    = field(default_factory=lambda: random.Random())

    @property
    def at_home(self) -> bool:
        return self.grid[self.py][self.px] == TILE_HOME

    @property
    def at_boss(self) -> bool:
        return self.grid[self.py][self.px] == TILE_BOSS

    @property
    def on_grass(self) -> bool:
        return self.grid[self.py][self.px] == TILE_GRASS

    @property
    def alive_party(self) -> list[Creature]:
        return [c for c in self.party if c.alive]

    @property
    def active_creature(self) -> Creature | None:
        if not self.party:
            return None
        if 0 <= self.active < len(self.party) and self.party[self.active].alive:
            return self.party[self.active]
        for i, c in enumerate(self.party):
            if c.alive:
                self.active = i
                return c
        return None

    def try_move(self, dx: int, dy: int) -> bool:
        nx, ny = self.px + dx, self.py + dy
        if not (0 <= nx < MAP_W and 0 <= ny < MAP_H):
            return False
        tile = self.grid[ny][nx]
        if tile not in WALKABLE:
            return False
        # boss tile is only walkable until boss defeated; afterwards it stays
        # walkable too (player can revisit).
        if tile == TILE_BOSS and not self.boss_present:
            pass
        self.px, self.py = nx, ny
        self.step_count += 1
        return True

    def maybe_encounter(self) -> Species | None:
        if not self.on_grass:
            return None
        if self.rng.random() < ENCOUNTER_RATE:
            return self.rng.choice(SPECIES)
        return None

    def heal_party(self) -> None:
        for c in self.party:
            c.heal_full()

    def add_to_party(self, c: Creature) -> bool:
        if len(self.party) >= PARTY_MAX:
            return False
        c.caught = True
        self.party.append(c)
        self.caught_species.add(c.species.name)
        return True

    def win(self) -> bool:
        all_caught = len(self.caught_species) >= len(SPECIES)
        return self.boss_defeated and all_caught

    def lost(self) -> bool:
        # Lose only if the player has at least one creature but all are KO'd
        return bool(self.party) and not self.alive_party

    def score(self) -> int:
        caught = len(self.caught_species)
        lvls   = sum(c.level for c in self.party)
        boss   = 1000 if self.boss_defeated else 0
        return caught * 100 + lvls * 10 + boss


# ── Battle state ──────────────────────────────────────────────────────────────

BATTLE_ACTIONS = ('ATTACK', 'CATCH', 'SWITCH', 'RUN')


@dataclass
class Battle:
    enemy:      Creature
    is_boss:    bool = False
    cursor:     int  = 0
    log:        list[str] = field(default_factory=list)
    # animation / state machine
    phase:      str  = 'menu'   # menu | submenu | resolve | result
    submenu:    str  = ''       # 'switch' (party select)
    sub_cursor: int  = 0
    result:     str  = ''       # 'win' 'lose' 'caught' 'fled'
    flash:      int  = 0        # frames of damage flash

    def log_push(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > 4:
            del self.log[0]


def calc_damage(attacker: Creature, defender: Creature, rng: random.Random) -> tuple[int, float]:
    mult = MATCHUP[attacker.species.type][defender.species.type]
    base = attacker.damage
    # +/- 15% randomisation
    roll = 0.85 + rng.random() * 0.30
    dmg = max(1, int(base * mult * roll))
    return dmg, mult


def catch_chance(enemy: Creature) -> float:
    """Catch probability based on enemy HP%. Lower HP -> higher chance."""
    hp_frac = enemy.hp / max(1, enemy.max_hp)
    base = 0.85 - 0.65 * hp_frac     # 0.20 at full HP, 0.85 at 0 HP
    base += enemy.species.catch_bonus
    return max(0.05, min(CATCH_RATE_CAP, base))


# ── Scenes ────────────────────────────────────────────────────────────────────

class TitleScene(Scene):
    def update(self, inp: Input, tick: int, dt: float) -> str | None:
        if inp.just_pressed(ord(' '), 10, 13): return 'howto'
        if inp.just_pressed(27): return 'quit'
        return None

    def draw(self, r: Renderer, tick: int) -> None:
        r.outer_border(NEUTRAL)
        h = r.H // 2
        title = [
            ' ██████ ██       █████  ██    ██ ██████  ███████ ███    ███  ██████  ███    ██ ',
            '██      ██      ██   ██ ██    ██ ██   ██ ██      ████  ████ ██    ██ ████   ██ ',
            '██      ██      ███████ ██    ██ ██   ██ █████   ██ ████ ██ ██    ██ ██ ██  ██ ',
            '██      ██      ██   ██ ██    ██ ██   ██ ██      ██  ██  ██ ██    ██ ██  ██ ██ ',
            ' ██████ ███████ ██   ██  ██████  ██████  ███████ ██      ██  ██████  ██   ████ ',
        ]
        # Scale down if narrow
        start = max(2, h - 6)
        for i, line in enumerate(title):
            if len(line) + 2 < r.W:
                r.center(start + i, line, GOLD, bold=True)
            else:
                # fallback: just text
                r.center(start + i, 'CLAUDEMON', GOLD, bold=True)
                break

        r.center(start + 6, 'a tiny terminal creature-catching RPG', SPECIAL, bold=True)
        if (tick // 15) % 2 == 0:
            r.center(h + 3, '[ SPACE ] Begin    [ ESC ] Quit', NEUTRAL, bold=True)
        r.center(r.H - 4, f'  {player_label()}  ', PLAYER)


class HowToScene(Scene):
    def update(self, inp: Input, tick: int, dt: float) -> str | None:
        if inp.just_pressed(ord(' '), 10, 13): return 'play'
        if inp.just_pressed(27): return 'quit'
        return None

    def draw(self, r: Renderer, tick: int) -> None:
        _engine_how_to_play(
            r._scr, self.engine.H, self.engine.W, tick,
            goal=[
                'Wander tall grass to find wild creatures. Battle, weaken,',
                f'and catch all {len(SPECIES)} species, then defeat the boss CLAUDESYNTH.',
            ],
            controls=[
                'WASD / Arrows     Move',
                'SPACE / ENTER     Confirm / Interact',
                'M                 Party menu',
                'ESC               Pause',
            ],
            tips=[
                '* Step on H (home base) to fully heal your party.',
                '* Type triangle: FIRE > GRASS > WATER > FIRE.',
                '* Lower HP = higher catch chance. Bring them low first.',
                '* Boss tile B in the north-east; clear it after catching all.',
            ],
        )


class PlayScene(Scene):
    """Overworld + battle controller."""

    def on_enter(self) -> None:
        # If we're returning from battle, payload may be the prior Game.
        prev = self.payload if isinstance(self.payload, Game) else None
        if prev is not None:
            self.game = prev
        else:
            self.game = Game()
        self.paused: bool = False
        self.battle: Battle | None = None
        self.menu_open: bool = False
        self.menu_cursor: int = 0
        self.last_step_msg: str = ''
        self._move_cd: int = 0   # frames before next allowed step

    # ── Update ──
    def update(self, inp: Input, tick: int, dt: float) -> str | tuple[str, object] | None:
        if inp.just_pressed(27):
            if self.menu_open:
                self.menu_open = False
                return None
            if self.battle is not None:
                # ESC in battle just toggles pause
                self.paused = not self.paused
                return None
            self.paused = not self.paused
            return None

        if self.paused:
            if inp.just_pressed(ord('r'), ord('R')): self.paused = False
            if inp.just_pressed(ord('q'), ord('Q')): return 'quit'
            return None

        # Win/lose checks
        if self.game.win():
            return ('gameover', ('win', self.game))
        if self.game.lost():
            return ('gameover', ('lose', self.game))

        if self.battle is not None:
            self._update_battle(inp)
            return None

        if self.menu_open:
            self._update_menu(inp)
            return None

        # Open party menu
        if inp.just_pressed(ord('m'), ord('M')) and self.game.party:
            self.menu_open = True
            self.menu_cursor = 0
            return None

        # Movement (cooldown-gated so a held key paces nicely)
        if self._move_cd > 0:
            self._move_cd -= 1
        else:
            dx = dy = 0
            if inp.up:    dy = -1
            elif inp.down:  dy = 1
            elif inp.left:  dx = -1
            elif inp.right: dx = 1
            if dx != 0 or dy != 0:
                moved = self.game.try_move(dx, dy)
                self._move_cd = 4
                if moved:
                    sp = self.game.maybe_encounter()
                    if sp is not None and self.game.party:
                        self._start_battle(sp, is_boss=False)
                        return None
                    if sp is not None and not self.game.party:
                        # First encounter ever — give the player this creature
                        # as a starter so they can battle.
                        starter = Creature.make(sp, level=3, caught=True)
                        self.game.add_to_party(starter)
                        self.game.last_msg = (
                            f'A wild {sp.name} appeared and joined you as a starter!'
                        )

        # Confirm / interact
        if inp.just_pressed(ord(' '), 10, 13):
            if self.game.at_home:
                self.game.heal_party()
                self.game.last_msg = 'Your party rests at home base. Fully healed.'
            elif self.game.at_boss and self.game.boss_present:
                if len(self.game.caught_species) < len(SPECIES):
                    self.game.last_msg = (
                        f'CLAUDESYNTH guards this spot. '
                        f'Catch all {len(SPECIES)} species first!'
                    )
                elif not self.game.party:
                    self.game.last_msg = 'You need a creature to challenge the boss.'
                else:
                    boss_creature = Creature.make(BOSS, level=10, caught=False)
                    self._start_battle(boss_creature.species, is_boss=True,
                                        boss_creature=boss_creature)
            else:
                # Tip prompt
                if not self.game.party:
                    self.game.last_msg = 'Step into tall grass " to find a starter.'
        return None

    def _start_battle(self, sp: Species, is_boss: bool = False,
                      boss_creature: Creature | None = None) -> None:
        if is_boss and boss_creature is not None:
            enemy = boss_creature
        else:
            # Wild creature: level scales with party progress
            base = 1 + len(self.game.caught_species)
            lvl  = max(1, base + self.game.rng.randint(-1, 1))
            enemy = Creature.make(sp, level=lvl, caught=False)
        self.battle = Battle(enemy=enemy, is_boss=is_boss)
        self.battle.log_push(f'A wild {sp.name} ({sp.type}) appeared!')

    # ── Battle update ──
    def _update_battle(self, inp: Input) -> None:
        b = self.battle
        if b is None: return
        rng = self.game.rng

        if b.flash > 0:
            b.flash -= 1

        # If a result is set, wait for SPACE to dismiss.
        if b.result:
            if inp.just_pressed(ord(' '), 10, 13):
                self._end_battle()
            return

        active = self.game.active_creature
        # If active is dead but party has alive members, force switch.
        if active is None:
            # All party KO'd — battle is a loss
            b.result = 'lose'
            b.log_push('All your creatures fainted...')
            return

        if b.phase == 'menu':
            if inp.just_pressed(curses.KEY_UP, ord('w'), ord('W')):
                b.cursor = (b.cursor - 1) % len(BATTLE_ACTIONS)
            if inp.just_pressed(curses.KEY_DOWN, ord('s'), ord('S')):
                b.cursor = (b.cursor + 1) % len(BATTLE_ACTIONS)
            if inp.just_pressed(ord(' '), 10, 13):
                action = BATTLE_ACTIONS[b.cursor]
                if action == 'ATTACK':
                    self._do_attack(active)
                elif action == 'CATCH':
                    self._do_catch(active)
                elif action == 'SWITCH':
                    if sum(1 for c in self.game.party if c.alive) <= 1:
                        b.log_push('No one else can fight.')
                    else:
                        b.phase = 'submenu'
                        b.submenu = 'switch'
                        b.sub_cursor = 0
                elif action == 'RUN':
                    self._do_run(active)
            return

        if b.phase == 'submenu' and b.submenu == 'switch':
            party = self.game.party
            if not party:
                b.phase = 'menu'
                return
            if inp.just_pressed(curses.KEY_UP, ord('w'), ord('W')):
                b.sub_cursor = (b.sub_cursor - 1) % len(party)
            if inp.just_pressed(curses.KEY_DOWN, ord('s'), ord('S')):
                b.sub_cursor = (b.sub_cursor + 1) % len(party)
            if inp.just_pressed(ord(' '), 10, 13):
                target = party[b.sub_cursor]
                if not target.alive:
                    b.log_push(f'{target.species.name} has fainted.')
                elif b.sub_cursor == self.game.active:
                    b.log_push(f'{target.species.name} is already out.')
                else:
                    self.game.active = b.sub_cursor
                    b.log_push(f'Go, {target.species.name}!')
                    b.phase = 'menu'
                    # Enemy gets a free turn after switching
                    self._enemy_turn(self.game.party[b.sub_cursor], rng)
            if inp.just_pressed(27, ord('q'), ord('Q')):
                b.phase = 'menu'
            return

    # ── Battle actions ──
    def _do_attack(self, active: Creature) -> None:
        b = self.battle
        if b is None: return
        rng = self.game.rng
        dmg, mult = calc_damage(active, b.enemy, rng)
        b.enemy.hp = max(0, b.enemy.hp - dmg)
        b.flash = 6
        b.log_push(
            f'{active.species.name} hits for {dmg}'
            + (' (super!)' if mult > 1.1 else '')
            + (' (resisted)' if mult < 0.9 else '')
        )
        if not b.enemy.alive:
            xp = 4 + b.enemy.level * 3
            msgs = active.gain_xp(xp)
            b.log_push(f'Enemy {b.enemy.species.name} fainted! +{xp} XP')
            for m in msgs:
                b.log_push(m)
            b.result = 'win'
            return
        self._enemy_turn(active, rng)

    def _do_catch(self, active: Creature) -> None:
        b = self.battle
        if b is None: return
        rng = self.game.rng
        if b.is_boss:
            b.log_push('The boss cannot be caught!')
            self._enemy_turn(active, rng)
            return
        if len(self.game.party) >= PARTY_MAX:
            b.log_push('Party is full!')
            self._enemy_turn(active, rng)
            return
        if b.enemy.species.name in self.game.caught_species:
            b.log_push(f'You already have a {b.enemy.species.name}.')
            self._enemy_turn(active, rng)
            return
        chance = catch_chance(b.enemy)
        pct = int(chance * 100)
        if rng.random() < chance:
            captured = Creature.make(b.enemy.species, level=b.enemy.level, caught=True)
            captured.hp = max(1, b.enemy.hp)
            self.game.add_to_party(captured)
            b.log_push(f'Gotcha! Caught {b.enemy.species.name} ({pct}%).')
            b.result = 'caught'
        else:
            b.log_push(f'{b.enemy.species.name} broke free! ({pct}%)')
            self._enemy_turn(active, rng)

    def _do_run(self, active: Creature) -> None:
        b = self.battle
        if b is None: return
        rng = self.game.rng
        if b.is_boss:
            b.log_push('You cannot flee the boss!')
            self._enemy_turn(active, rng)
            return
        if rng.random() < 0.7:
            b.log_push('Got away safely!')
            b.result = 'fled'
        else:
            b.log_push('Could not escape!')
            self._enemy_turn(active, rng)

    def _enemy_turn(self, active: Creature, rng: random.Random) -> None:
        b = self.battle
        if b is None or not b.enemy.alive: return
        dmg, mult = calc_damage(b.enemy, active, rng)
        active.hp = max(0, active.hp - dmg)
        b.log_push(
            f'{b.enemy.species.name} strikes {active.species.name} for {dmg}'
            + (' (super!)' if mult > 1.1 else '')
            + (' (resisted)' if mult < 0.9 else '')
        )
        if not active.alive:
            b.log_push(f'{active.species.name} fainted!')
            # auto-switch to next alive
            alive = [i for i, c in enumerate(self.game.party) if c.alive]
            if alive:
                self.game.active = alive[0]
                b.log_push(f'Go, {self.game.party[alive[0]].species.name}!')
            else:
                b.result = 'lose'

    def _end_battle(self) -> None:
        b = self.battle
        if b is None: return
        if b.result == 'win' and b.is_boss:
            self.game.boss_defeated = True
            self.game.boss_present  = False
            self.game.last_msg = 'You defeated CLAUDESYNTH! Legendary!'
        elif b.result == 'win':
            self.game.last_msg = f'Defeated wild {b.enemy.species.name}.'
        elif b.result == 'caught':
            self.game.last_msg = f'Caught {b.enemy.species.name}!'
        elif b.result == 'fled':
            self.game.last_msg = 'You fled the battle.'
        elif b.result == 'lose':
            self.game.last_msg = 'Your party was wiped out...'
        self.battle = None

    # ── Party menu ──
    def _update_menu(self, inp: Input) -> None:
        n = len(self.game.party)
        if n == 0:
            self.menu_open = False
            return
        if inp.just_pressed(curses.KEY_UP, ord('w'), ord('W')):
            self.menu_cursor = (self.menu_cursor - 1) % n
        if inp.just_pressed(curses.KEY_DOWN, ord('s'), ord('S')):
            self.menu_cursor = (self.menu_cursor + 1) % n
        if inp.just_pressed(ord(' '), 10, 13):
            if self.game.party[self.menu_cursor].alive:
                self.game.active = self.menu_cursor
                self.game.last_msg = (
                    f'{self.game.party[self.menu_cursor].species.name} is now active.'
                )
                self.menu_open = False
        if inp.just_pressed(ord('m'), ord('M'), ord('q'), ord('Q')):
            self.menu_open = False

    # ── Draw ──
    def draw(self, r: Renderer, tick: int) -> None:
        r.outer_border(NEUTRAL)
        # Header
        caught_str = f'CAUGHT {len(self.game.caught_species)}/{len(SPECIES)}'
        boss_str   = 'BOSS DOWN' if self.game.boss_defeated else 'BOSS LIVE'
        r.header('CLAUDEMON',
                 left=f'PARTY {len(self.game.party)}/{PARTY_MAX}',
                 right=f'{caught_str}  {boss_str}')

        if self.battle is not None:
            self._draw_battle(r, tick)
        else:
            self._draw_overworld(r, tick)

        # Footer
        if self.battle is not None:
            r.footer('W/S Choose   ENTER Confirm   ESC Pause', NEUTRAL)
        elif self.menu_open:
            r.footer('W/S Choose   ENTER Set Active   M Close', NEUTRAL)
        else:
            r.footer('WASD Move   SPACE Interact   M Party   ESC Pause', NEUTRAL)

        if self.menu_open:
            self._draw_menu(r)

        if self.paused:
            r.pause_overlay('Claudemon', CONTROLS_PAUSE)

    # ── Overworld draw ──
    def _draw_overworld(self, r: Renderer, tick: int) -> None:
        # Center the map under the HUD.
        top  = 3
        left = max(2, (r.W - MAP_W) // 2)

        for y in range(MAP_H):
            for x in range(MAP_W):
                ch = self.grid_char(x, y)
                color = self.grid_color(x, y, tick)
                r.text(top + y, left + x, ch, color,
                       bold=(self.grid[y][x] in (TILE_HOME, TILE_BOSS)))
        # player
        r.text(top + self.game.py, left + self.game.px, '@', PLAYER, bold=True)

        # Side panel: party + message
        panel_x = left + MAP_W + 3
        if panel_x + 22 < r.W:
            r.box(top, panel_x, MAP_H, 22, SELECT, title='PARTY')
            if not self.game.party:
                r.text(top + 2, panel_x + 2, '(empty)', NEUTRAL, dim=True)
                r.text(top + 4, panel_x + 2, 'Step into grass', NEUTRAL)
                r.text(top + 5, panel_x + 2, 'to find a starter.', NEUTRAL)
            else:
                for i, c in enumerate(self.game.party):
                    row = top + 1 + i * 3
                    marker = '>' if i == self.game.active else ' '
                    name_color = TYPE_COLOR.get(c.species.type, NEUTRAL)
                    r.text(row, panel_x + 1,
                           f'{marker}{c.species.name[:10]:<10} Lv{c.level}',
                           name_color, bold=(i == self.game.active))
                    bar_w = 14
                    r.bar(row + 1, panel_x + 2, c.hp, c.max_hp, bar_w,
                          fill_color=GOOD if c.hp > c.max_hp // 2 else GOLD,
                          empty_color=NEUTRAL)

        # Status / message bar near the bottom
        msg_row = top + MAP_H + 1
        if msg_row < r.H - 4:
            r.text(msg_row, left, self.game.last_msg[:r.W - left - 2], GOLD, bold=True)

        # Tip about boss
        tip_row = msg_row + 1
        if tip_row < r.H - 4:
            tip = ''
            if self.game.at_home:
                tip = 'You are at HOME. Press SPACE to heal.'
            elif self.game.at_boss and self.game.boss_present:
                tip = 'CLAUDESYNTH lurks here. Press SPACE to challenge.'
            elif self.game.on_grass:
                tip = 'Tall grass rustles around you...'
            if tip:
                r.text(tip_row, left, tip[:r.W - left - 2], SPECIAL)

    def grid_char(self, x: int, y: int) -> str:
        t = self.grid[y][x]
        if t == TILE_BOSS and not self.game.boss_present:
            return '*'
        return t

    def grid_color(self, x: int, y: int, tick: int) -> int:
        t = self.grid[y][x]
        if t == TILE_GRASS:  return GOOD
        if t == TILE_TREE:   return GOOD
        if t == TILE_WATER:  return WATER
        if t == TILE_HOME:   return GOLD
        if t == TILE_BOSS:   return ENEMY
        if t == TILE_WALL:   return NEUTRAL
        return NEUTRAL

    @property
    def grid(self) -> list[list[str]]:
        return self.game.grid

    # ── Battle draw ──
    def _draw_battle(self, r: Renderer, tick: int) -> None:
        b = self.battle
        if b is None: return
        active = self.game.active_creature

        # Frame layout
        pad = 4
        bw  = r.W - 2 * pad
        bh  = r.H - 8
        x0  = pad
        y0  = 3
        r.box(y0, x0, bh, bw, SELECT, title='BATTLE', double=True)

        # Enemy panel — upper right
        ew = min(36, bw // 2 - 2)
        ex = x0 + bw - ew - 2
        ey = y0 + 1
        eh = 7
        r.box(ey, ex, eh, ew, ENEMY if b.is_boss else NEUTRAL,
              title=('BOSS' if b.is_boss else 'WILD'))
        e = b.enemy
        e_color = TYPE_COLOR.get(e.species.type, NEUTRAL)
        r.text(ey + 1, ex + 2, f'{e.species.name}  Lv{e.level}',
               e_color, bold=True)
        r.text(ey + 2, ex + 2, f'TYPE {e.species.type}', e_color)
        r.bar(ey + 3, ex + 2, e.hp, e.max_hp, ew - 6,
              fill_color=GOOD if e.hp > e.max_hp // 2 else GOLD)
        r.text(ey + 4, ex + 2, f'HP {e.hp}/{e.max_hp}', NEUTRAL)
        if b.is_boss:
            r.text(ey + 5, ex + 2, '*** BOSS ENCOUNTER ***',
                   ENEMY, bold=True)

        # Enemy sprite right below enemy panel
        sprite_y = ey + eh + 1
        sprite_x = ex + (ew - 11) // 2
        sprite = e.species.sprite or ('   ???   ',)
        sprite_color = ENEMY if (b.flash > 0) else e_color
        for i, line in enumerate(sprite):
            if sprite_y + i < y0 + bh - 1:
                r.text(sprite_y + i, sprite_x, line, sprite_color, bold=True)

        # Player panel — lower left
        pw = min(36, bw // 2 - 2)
        pxc = x0 + 2
        pyc = y0 + bh - 9
        ph = 7
        if active is not None:
            r.box(pyc, pxc, ph, pw, PLAYER, title='YOUR ACTIVE')
            p_color = TYPE_COLOR.get(active.species.type, NEUTRAL)
            r.text(pyc + 1, pxc + 2,
                   f'{active.species.name}  Lv{active.level}',
                   p_color, bold=True)
            r.text(pyc + 2, pxc + 2, f'TYPE {active.species.type}', p_color)
            r.bar(pyc + 3, pxc + 2, active.hp, active.max_hp, pw - 6,
                  fill_color=GOOD if active.hp > active.max_hp // 2 else GOLD)
            r.text(pyc + 4, pxc + 2,
                   f'HP {active.hp}/{active.max_hp}  XP {active.xp}/{active.xp_for_next()}',
                   NEUTRAL)
            r.text(pyc + 5, pxc + 2,
                   f'DMG ~{active.damage}', NEUTRAL)

        # Action menu — bottom-right
        mw = 22
        mh = 7
        mx = x0 + bw - mw - 2
        my = pyc
        r.box(my, mx, mh, mw, GOLD, title='ACTION')
        if b.phase == 'menu':
            for i, opt in enumerate(BATTLE_ACTIONS):
                row = my + 1 + i
                if i == b.cursor:
                    r.text(row, mx + 2, '> ' + opt, SELECT, bold=True)
                else:
                    r.text(row, mx + 2, '  ' + opt, NEUTRAL)
            # Show catch hint
            if BATTLE_ACTIONS[b.cursor] == 'CATCH':
                c = int(catch_chance(b.enemy) * 100)
                r.text(my + mh - 1, mx + 2, f'catch ~{c}%', GOLD)
        elif b.phase == 'submenu' and b.submenu == 'switch':
            r.text(my + 1, mx + 2, 'SWITCH TO:', GOLD, bold=True)
            for i, c in enumerate(self.game.party[:mh - 2]):
                row = my + 2 + i
                tag = '> ' if i == b.sub_cursor else '  '
                state = '' if c.alive else ' KO'
                line = f'{tag}{c.species.name[:10]:<10} L{c.level}{state}'
                color = SELECT if i == b.sub_cursor else (
                    NEUTRAL if c.alive else ENEMY)
                r.text(row, mx + 2, line[:mw - 3], color,
                       bold=(i == b.sub_cursor))

        # Log panel — bottom of battle frame
        log_y = y0 + bh - 2
        log_lines = b.log[-2:]
        for i, line in enumerate(log_lines):
            r.text(log_y + i, x0 + 2, line[:bw - 4], NEUTRAL, bold=(i == len(log_lines) - 1))

        # If a result is set, show a 'press SPACE' prompt blinking.
        if b.result and (tick // 15) % 2 == 0:
            tag = {
                'win':    'VICTORY!',
                'lose':   'DEFEAT...',
                'caught': 'CAPTURED!',
                'fled':   'ESCAPED',
            }.get(b.result, '')
            r.center(y0 + bh - 4, f' {tag}  [SPACE] continue ',
                     GOLD if b.result != 'lose' else ENEMY, bold=True)

    def _draw_menu(self, r: Renderer) -> None:
        # Floating party menu
        w  = 44
        h  = min(r.H - 4, 5 + len(self.game.party) * 3)
        x0 = (r.W - w) // 2
        y0 = (r.H - h) // 2
        # blank backdrop
        for rr in range(h):
            r.text(y0 + rr, x0, ' ' * w, NEUTRAL)
        r.box(y0, x0, h, w, SELECT, title='PARTY', double=True)
        if not self.game.party:
            r.text(y0 + 2, x0 + 2, '(no creatures yet)', NEUTRAL, dim=True)
            return
        for i, c in enumerate(self.game.party):
            row = y0 + 1 + i * 3
            sel = (i == self.menu_cursor)
            marker = '>' if sel else (' *' if i == self.game.active else '  ')
            name_color = TYPE_COLOR.get(c.species.type, NEUTRAL)
            r.text(row, x0 + 2,
                   f'{marker} {c.species.name[:10]:<10} '
                   f'Lv{c.level:<2} {c.species.type:<6}',
                   SELECT if sel else name_color, bold=sel)
            r.bar(row + 1, x0 + 4, c.hp, c.max_hp, w - 10,
                  fill_color=GOOD if c.hp > c.max_hp // 2 else GOLD)
            r.text(row + 1, x0 + w - 5, f'{c.hp:3d}', NEUTRAL)


class GameOverScene(Scene):
    def on_enter(self) -> None:
        if isinstance(self.payload, tuple) and len(self.payload) == 2:
            self.outcome, self.game = self.payload
        else:
            self.outcome, self.game = 'lose', Game()
        self.score = self.game.score()
        self.sub_box: list = [None]
        extra = (
            f'Caught {len(self.game.caught_species)}/{len(SPECIES)}'
            + (' +Boss' if self.game.boss_defeated else '')
        )
        submit_async('claudemon', self.score, extra, self.sub_box)
        self.entered_tick: int = 0

    def update(self, inp: Input, tick: int, dt: float) -> str | tuple[str, object] | None:
        self.entered_tick += 1
        if self.entered_tick > 20:
            if inp.just_pressed(ord(' '), 10, 13):
                return ('play', None)
            if inp.just_pressed(27, ord('q'), ord('Q')):
                return 'quit'
        return None

    def draw(self, r: Renderer, tick: int) -> None:
        is_win = (self.outcome == 'win')
        title = 'V I C T O R Y !' if is_win else 'G A M E   O V E R'
        title_color = GOOD if is_win else ENEMY
        rank = None
        sub_result = self.sub_box[0]
        if isinstance(sub_result, dict):
            rank = sub_result.get('rank')
        score_line = (
            f'SCORE {self.score}    '
            f'Caught {len(self.game.caught_species)}/{len(SPECIES)}'
            + ('    Boss: defeated' if self.game.boss_defeated else '')
        )
        r.gameover_screen(
            title=title,
            score_line=score_line,
            player_label=player_label(),
            rank=rank,
            tick=tick,
            prompt='[ SPACE ] Play again   [ ESC ] Quit',
            title_color=title_color,
        )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    Engine('Claudemon', fps=FPS) \
        .scene('title',    TitleScene()) \
        .scene('howto',    HowToScene()) \
        .scene('play',     PlayScene()) \
        .scene('gameover', GameOverScene()) \
        .run('title')


if __name__ == '__main__':
    main()
