"""Character, EnemyInstance, and Party classes."""
from __future__ import annotations

import random
from .data import EQUIPMENT, SPELLS, PARTY_DEFS, ENEMIES as ENEMY_DATA, ITEMS


class Character:
    def __init__(self, name: str) -> None:
        d = PARTY_DEFS[name]
        self.name   = name
        self.cls    = d['cls']
        self.sprite = d['sprite']
        self.color  = d['color']
        b, g        = d['base'], d['growth']
        self.base   = dict(b)
        self.growth = dict(g)
        self.level  = 1
        self.exp    = 0
        self.weapon = d['weapon']
        self.armor  = d['armor']
        self.acc    = d['acc']
        self.spells = list(d['spells'])
        self.learn  = dict(d['learn'])
        self._hp    = self.max_hp
        self._mp    = self.max_mp
        self.status : dict[str,int] = {}
        self.buffs  : dict[str,float] = {}
        self.defending = False

    def _equip(self, stat: str) -> int:
        t = 0
        for slot in (self.weapon, self.armor, self.acc):
            if slot and slot in EQUIPMENT:
                t += EQUIPMENT[slot].get(stat, 0)
        return t

    @property
    def max_hp(self) -> int: return self.base['hp'] + self.growth['hp'] * (self.level - 1)
    @property
    def max_mp(self) -> int: return self.base['mp'] + self.growth['mp'] * (self.level - 1)
    @property
    def atk(self) -> int:    return int((self.base['atk'] + self.growth['atk']*(self.level-1) + self._equip('atk')) * self.buffs.get('atk', 1.0))
    @property
    def defense(self) -> int:
        v = (self.base['def'] + self.growth['def']*(self.level-1) + self._equip('def')) * self.buffs.get('def', 1.0)
        return int(v * 1.5 if self.defending else v)
    @property
    def mag(self) -> int:    return int((self.base['mag'] + self.growth['mag']*(self.level-1) + self._equip('mag')) * self.buffs.get('mag', 1.0))
    @property
    def spd(self) -> int:    return int((self.base['spd'] + self.growth['spd']*(self.level-1) + self._equip('spd')) * self.buffs.get('spd', 1.0))

    @property
    def hp(self) -> int: return self._hp
    @hp.setter
    def hp(self, v: int) -> None: self._hp = max(0, min(self.max_hp, v))

    @property
    def mp(self) -> int: return self._mp
    @mp.setter
    def mp(self, v: int) -> None: self._mp = max(0, min(self.max_mp, v))

    @property
    def alive(self) -> bool: return self._hp > 0

    def tick_status(self) -> tuple[int, list[str]]:
        dmg, msgs = 0, []
        for s in list(self.status):
            if s == 'poison':
                d = max(1, int(self.max_hp * 0.05))
                self.hp -= d; dmg += d
                msgs.append(f'{self.name} takes {d} poison damage!')
            self.status[s] -= 1
            if self.status[s] <= 0:
                del self.status[s]
                msgs.append(f"{self.name}'s {s} wore off.")
        return dmg, msgs

    def apply_status(self, status: str, turns: int = 3) -> bool:
        if status not in self.status:
            self.status[status] = turns
            return True
        return False

    def apply_buff(self, stat: str, mult: float) -> None:
        self.buffs[stat] = mult

    def clear_buffs(self) -> None:
        self.buffs.clear()
        self.defending = False

    def restore(self) -> None:
        self.hp = self.max_hp
        self.mp = self.max_mp
        self.status.clear()
        self.clear_buffs()

    def exp_to_next(self) -> int:
        return int(40 * (self.level ** 1.4))

    def gain_exp(self, amount: int) -> list[str]:
        self.exp += amount
        msgs = []
        while self.exp >= self.exp_to_next():
            self.exp -= self.exp_to_next()
            self.level += 1
            self.hp = min(self._hp + self.growth['hp'], self.max_hp)
            self.mp = min(self._mp + self.growth['mp'], self.max_mp)
            msgs.append(f'{self.name} reached level {self.level}!')
            if self.level in self.learn:
                sp = self.learn[self.level]
                if sp not in self.spells:
                    self.spells.append(sp)
                    msgs.append(f'{self.name} learned {sp}!')
        return msgs

    def slot_for(self, item: str) -> str | None:
        if item not in EQUIPMENT: return None
        return EQUIPMENT[item]['slot']

    def can_equip(self, item: str) -> bool:
        if item not in EQUIPMENT: return False
        f = EQUIPMENT[item].get('for', 'all')
        if f == 'all': return True
        return f == self.cls.lower()

    def equip(self, item: str) -> bool:
        if not self.can_equip(item): return False
        slot = self.slot_for(item)
        if slot == 'weapon': self.weapon = item
        elif slot == 'armor': self.armor  = item
        elif slot == 'acc':   self.acc    = item
        return True

    def stat_preview(self, item: str) -> dict[str, int]:
        """Returns dict of stat deltas if item were equipped."""
        old_weapon, old_armor, old_acc = self.weapon, self.armor, self.acc
        tmp = Character.__new__(Character)
        tmp.__dict__.update(self.__dict__)
        tmp.weapon, tmp.armor, tmp.acc = old_weapon, old_armor, old_acc
        before = {'atk': self.atk, 'def': self.defense, 'mag': self.mag, 'spd': self.spd}
        # simulate equip
        slot = self.slot_for(item)
        if slot == 'weapon': self.weapon = item
        elif slot == 'armor': self.armor  = item
        elif slot == 'acc':   self.acc    = item
        after = {'atk': self.atk, 'def': self.defense, 'mag': self.mag, 'spd': self.spd}
        self.weapon, self.armor, self.acc = old_weapon, old_armor, old_acc
        return {k: after[k] - before[k] for k in before}

    def save_dict(self) -> dict[str, object]:
        return {
            'name': self.name, 'level': self.level, 'exp': self.exp,
            'hp': self._hp, 'mp': self._mp,
            'weapon': self.weapon, 'armor': self.armor, 'acc': self.acc,
            'spells': self.spells,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> 'Character':
        c = cls(d['name'])
        c.level  = d['level'];  c.exp   = d['exp']
        c._hp    = d['hp'];     c._mp   = d['mp']
        c.weapon = d['weapon']; c.armor = d['armor']; c.acc = d['acc']
        c.spells = d['spells']
        return c


class EnemyInstance:
    def __init__(self, name: str, scale: float = 1.0) -> None:
        d = ENEMY_DATA[name]
        self.name    = name
        self.sprite  = d['sprite']
        self.color   = d.get('color', 5)
        self.max_hp  = int(d['hp'] * scale)
        self._hp     = self.max_hp
        self.mp      = d.get('mp', 0)
        self.atk     = int(d['atk'] * scale)
        self.defense = int(d['def'] * scale)
        self.mag     = int(d.get('mag', 0) * scale)
        self.spd     = d['spd']
        self.exp     = d['exp']
        self.gold    = d['gold']
        self.drops   = d.get('drops', [])
        self._actions = d['actions']
        self.boss    = d.get('boss', False)
        self.phases  = d.get('phases', 1)
        self.phase   = 0
        self.weakness = d.get('weakness')
        self.status  : dict[str,int] = {}
        self.buffs   : dict[str,float] = {}
        self.defending = False

    @property
    def hp(self) -> int: return self._hp
    @hp.setter
    def hp(self, v: int) -> None: self._hp = max(0, min(self.max_hp, v))

    @property
    def alive(self) -> bool: return self._hp > 0

    @property
    def defense_eff(self) -> int:
        v = self.defense * self.buffs.get('def', 1.0)
        return int(v * 1.5 if self.defending else v)

    @property
    def atk_eff(self) -> int:  return int(self.atk * self.buffs.get('atk', 1.0))
    @property
    def mag_eff(self) -> int:  return int(self.mag  * self.buffs.get('mag', 1.0))

    def choose_action(self) -> str:
        r = random.random(); cum = 0.0
        if self.phase == 1 and self.phases > 1:
            # phase 2: weight toward damage actions
            actions = [(a, p*1.4 if i < len(self._actions)//2 else p*0.6)
                       for i,(a,p) in enumerate(self._actions)]
        else:
            actions = self._actions
        for a, p in actions:
            cum += p
            if r <= cum: return a
        return self._actions[0][0]

    def check_phase(self) -> bool:
        if self.phases > 1 and self.phase == 0 and self._hp <= self.max_hp // 2:
            self.phase = 1; return True
        return False

    def tick_status(self) -> tuple[int, list[str]]:
        dmg, msgs = 0, []
        for s in list(self.status):
            if s == 'poison':
                d = max(1, int(self.max_hp * 0.06))
                self.hp -= d; dmg += d
                msgs.append(f'{self.name} takes {d} poison damage!')
            self.status[s] -= 1
            if self.status[s] <= 0:
                del self.status[s]
        return dmg, msgs

    def apply_status(self, status: str, turns: int = 3) -> bool:
        if status not in self.status:
            self.status[status] = turns; return True
        return False


class Party:
    def __init__(self):
        self.members   = [Character(n) for n in ('Claude','Haiku','Opus')]
        self.gold      = 400
        self.items     : dict[str,int] = {'Potion': 8, 'Hi-Potion': 3, 'Antidote': 3, 'Phoenix Down': 2}
        self.story_flags: set[str]     = set()
        self.dungeon_done: set[str]    = set()
        self.map_x     = 13
        self.map_y     = 7

    @property
    def alive_members(self): return [m for m in self.members if m.alive]

    def inn_rest(self) -> None:
        for m in self.members: m.restore()

    def add_item(self, name: str, n: int = 1) -> None:
        self.items[name] = self.items.get(name, 0) + n

    def remove_item(self, name: str, n: int = 1) -> None:
        self.items[name] = self.items.get(name, 0) - n
        if self.items[name] <= 0: del self.items[name]

    def use_item(self, item_name: str, target: 'Character | EnemyInstance') -> str:
        if self.items.get(item_name, 0) <= 0: return 'No items left!'
        d = ITEMS.get(item_name)
        if d is None:
            # Equipment piece found in chest — auto-equip rather than consume
            return f'{item_name} is equipment, equip it via the Equipment menu.'
        self.remove_item(item_name)
        t = d['type']
        if t == 'heal':
            if isinstance(target, Character) and not target.alive:
                self.add_item(item_name); return f'{target.name} is KO!'
            amt = d['power']; target.hp += amt
            return f'{target.name} recovers {amt} HP!'
        if t == 'mp':
            amt = d['power']; target.mp += amt
            return f'{target.name} recovers {amt} MP!'
        if t == 'elixir':
            target.hp = target.max_hp; target.mp = target.max_mp
            return f'{target.name} fully restored!'
        if t == 'raise':
            if isinstance(target, Character) and target.alive:
                self.add_item(item_name); return f'{target.name} is conscious!'
            target.hp = target.max_hp // 4
            return f'{target.name} is revived!'
        if t == 'esuna':
            cures = d.get('cures')
            if cures: target.status.pop(cures, None)
            else: target.status.clear()
            return f"{target.name}'s ailments cured!"
        if t == 'dmg':
            return f'Grenade! {d["power"]} damage!'
        return 'Nothing happened.'

    def save_dict(self):
        return {
            'members':  [m.save_dict() for m in self.members],
            'gold':     self.gold,
            'items':    self.items,
            'flags':    list(self.story_flags),
            'dungeons': list(self.dungeon_done),
            'map_x':    self.map_x,
            'map_y':    self.map_y,
        }

    @classmethod
    def from_dict(cls, d):
        p = cls.__new__(cls)
        p.members     = [Character.from_dict(m) for m in d['members']]
        p.gold        = d['gold']
        p.items       = d['items']
        p.story_flags = set(d.get('flags', []))
        p.dungeon_done= set(d.get('dungeons', []))
        p.map_x       = d.get('map_x', 13)
        p.map_y       = d.get('map_y', 7)
        return p
