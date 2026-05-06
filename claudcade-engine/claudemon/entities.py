"""Claudémon instance and trainer classes."""
from __future__ import annotations

import random
from .data import CLAUDEMON, MOVES, effectiveness

def _calc_stat(base: int, level: int, is_hp: bool = False) -> int:
    if is_hp:
        return int((2 * base * level / 100) + level + 10)
    return int((2 * base * level / 100) + 5)

class ClaudemonInstance:
    def __init__(self, name: str, level: int = 5):
        d = CLAUDEMON[name]
        self.name     = name
        self.level    = level
        self.type1    = d['type1']
        self.type2    = d.get('type2')
        self.max_hp   = _calc_stat(d['hp'], level, is_hp=True)
        self.hp       = self.max_hp
        self.atk      = _calc_stat(d['atk'], level)
        self.defense  = _calc_stat(d['def'], level)
        self.spatk    = _calc_stat(d['spatk'], level)
        self.spdef    = _calc_stat(d['spdef'], level)
        self.spd      = _calc_stat(d['spd'], level)
        self.exp      = 0
        self.status   = None  # 'par','slp','psn',None
        self.stat_mods= {'atk':0,'def':0,'spatk':0,'spdef':0,'spd':0}
        # Build moveset from learnset
        ls = d['learnset']
        learned = [m for lv, m in sorted(ls.items()) if lv <= level]
        self.moves = list(dict.fromkeys(learned))[-4:]  # last 4 unique
        self.pp    = {m: MOVES[m]['pp'] for m in self.moves}

    @property
    def alive(self): return self.hp > 0

    @property
    def art(self): return CLAUDEMON[self.name]['art']

    @property
    def data(self): return CLAUDEMON[self.name]

    def _stat_mult(self, stage: int) -> float:
        if stage >= 0: return (2 + stage) / 2
        return 2 / (2 - stage)

    def eff_atk(self)   -> int: return int(self.atk   * self._stat_mult(self.stat_mods['atk']))
    def eff_def(self)   -> int: return int(self.defense* self._stat_mult(self.stat_mods['def']))
    def eff_spatk(self) -> int: return int(self.spatk  * self._stat_mult(self.stat_mods['spatk']))
    def eff_spdef(self) -> int: return int(self.spdef  * self._stat_mult(self.stat_mods['spdef']))
    def eff_spd(self)   -> int: return int(self.spd    * self._stat_mult(self.stat_mods['spd']))

    def deal_damage(self, move_name: str, target: 'ClaudemonInstance') -> tuple[int, float]:
        """Returns (damage, type_mult)."""
        mv = MOVES[move_name]
        if mv.get('power', 0) == 0:
            return 0, 1.0
        # Type effectiveness
        mult  = effectiveness(mv['type'], target.type1)
        if target.type2:
            mult *= effectiveness(mv['type'], target.type2)
        # STAB
        stab = 1.5 if mv['type'] in (self.type1, self.type2) else 1.0
        # Stat selection
        if mv['cat'] == 'physical':
            a, d = self.eff_atk(), target.eff_def()
        else:
            a, d = self.eff_spatk(), target.eff_spdef()
        # Damage formula (gen 1 inspired)
        base = int(((2 * self.level / 5 + 2) * mv['power'] * a / d) / 50 + 2)
        rand = random.uniform(0.85, 1.0)
        dmg  = max(1, int(base * stab * mult * rand))
        target.hp = max(0, target.hp - dmg)
        return dmg, mult

    def apply_stat_move(self, move_name: str, target: 'ClaudemonInstance') -> str:
        mv = MOVES[move_name]
        if 'stat' not in mv:
            return ''
        stat, delta = mv['stat']
        tgt_obj = target if mv.get('target') == 'foe' else self
        tgt_obj.stat_mods[stat] = max(-6, min(6, tgt_obj.stat_mods[stat] + delta))
        direction = 'fell' if delta < 0 else 'rose'
        return f"{tgt_obj.name}'s {stat} {direction}!"

    def gain_exp(self, base_exp: int, foe_level: int) -> list[str]:
        gained = int(base_exp * foe_level / 7)
        self.exp += gained
        msgs = [f'{self.name} gained {gained} EXP!']
        # Level up check
        while self.exp >= self._exp_to_next():
            self.exp -= self._exp_to_next()
            self.level += 1
            old_max = self.max_hp
            d = CLAUDEMON[self.name]
            self.max_hp  = _calc_stat(d['hp'], self.level, True)
            self.atk     = _calc_stat(d['atk'], self.level)
            self.defense = _calc_stat(d['def'], self.level)
            self.spatk   = _calc_stat(d['spatk'], self.level)
            self.spdef   = _calc_stat(d['spdef'], self.level)
            self.spd     = _calc_stat(d['spd'], self.level)
            self.hp     += self.max_hp - old_max
            msgs.append(f'{self.name} reached Lv.{self.level}!')
            # Learn new moves
            ls = d['learnset']
            if self.level in ls:
                mv = ls[self.level]
                if mv not in self.moves:
                    if len(self.moves) < 4:
                        self.moves.append(mv)
                        self.pp[mv] = MOVES[mv]['pp']
                        msgs.append(f'{self.name} learned {mv}!')
                    else:
                        msgs.append(f'{self.name} wants to learn {mv}!')
            # Check evolution
            evo = d.get('evolves_into')
            if evo and d.get('evolves_at') == self.level:
                msgs.append(f'WHAT?! {self.name} is evolving!')
                msgs.append(f'*** {self.name} evolved into {evo}! ***')
                self._evolve(evo)
        return msgs

    def _evolve(self, new_name: str):
        old_name = self.name
        self.name = new_name
        d = CLAUDEMON[new_name]
        self.type1   = d['type1']
        self.type2   = d.get('type2')
        old_max      = self.max_hp
        self.max_hp  = _calc_stat(d['hp'], self.level, True)
        self.atk     = _calc_stat(d['atk'], self.level)
        self.defense = _calc_stat(d['def'], self.level)
        self.spatk   = _calc_stat(d['spatk'], self.level)
        self.spdef   = _calc_stat(d['spdef'], self.level)
        self.spd     = _calc_stat(d['spd'], self.level)
        self.hp      = min(self.hp + (self.max_hp - old_max), self.max_hp)
        # Inherit learnset moves for new species
        ls = d['learnset']
        for lv, mv in sorted(ls.items()):
            if lv <= self.level and mv not in self.moves:
                if len(self.moves) < 4:
                    self.moves.append(mv)
                    self.pp[mv] = MOVES[mv]['pp']

    def _exp_to_next(self) -> int:
        return int(4 * self.level ** 3 / 5)

    def catch_chance(self, ball_mult: float) -> float:
        d   = CLAUDEMON[self.name]
        cr  = d['catch_rate']
        hp_fraction = self.hp / self.max_hp
        chance = (cr / 255) * ball_mult * (1 - hp_fraction * 0.7)
        return min(0.97, max(0.02, chance))

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + amount)

    def full_restore(self):
        self.hp = self.max_hp
        self.status = None

    def save_dict(self) -> dict[str, object]:
        return {
            'name': self.name, 'level': self.level, 'exp': self.exp,
            'hp': self.hp, 'moves': self.moves, 'pp': self.pp,
            'stat_mods': self.stat_mods,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> 'ClaudemonInstance':
        obj       = cls.__new__(cls)
        obj.name  = d['name']
        obj.level = d['level']
        obj.exp   = d['exp']
        obj.hp    = d['hp']
        obj.moves = d['moves']
        obj.pp    = d['pp']
        obj.stat_mods = d.get('stat_mods', {'atk':0,'def':0,'spatk':0,'spdef':0,'spd':0})
        obj.status    = None
        data      = CLAUDEMON[obj.name]
        obj.type1 = data['type1']; obj.type2 = data.get('type2')
        obj.max_hp  = _calc_stat(data['hp'],    obj.level, True)
        obj.atk     = _calc_stat(data['atk'],   obj.level)
        obj.defense = _calc_stat(data['def'],   obj.level)
        obj.spatk   = _calc_stat(data['spatk'], obj.level)
        obj.spdef   = _calc_stat(data['spdef'], obj.level)
        obj.spd     = _calc_stat(data['spd'],   obj.level)
        return obj


class Trainer:
    def __init__(self, name: str, party: list[ClaudemonInstance], reward: int = 0):
        self.name    = name
        self.party   = party
        self.reward  = reward
        self.defeated = False

    @property
    def active(self) -> ClaudemonInstance | None:
        for c in self.party:
            if c.alive: return c
        return None
