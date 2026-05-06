"""Turn-based battle system."""
from __future__ import annotations

import curses, random, math
from .data    import SPELLS, ITEMS, ENEMIES as ENEMY_DATA, STATUS_ICONS, SPELL_FX
from .entities import EnemyInstance, Character, Party
from .ui       import safe_add, box, bar, menu_list, center

def _phys(attacker_atk: int, defender_def: int, variance: float = 0.15) -> int:
    # Defense reduces damage but never below 15% of attacker's raw ATK
    base = max(attacker_atk * 0.15, attacker_atk - defender_def * 0.4)
    return max(1, int(base * random.uniform(1 - variance, 1 + variance)))

def _magic(power: int, caster_mag: int, defender: 'Character | EnemyInstance',
           spell_type: str | None, variance: float = 0.10) -> int:
    base = power * (caster_mag / 45.0)
    mult = 1.5 if (spell_type and getattr(defender, 'weakness', None) == spell_type) else 1.0
    return max(1, int(base * mult * random.uniform(1 - variance, 1 + variance)))

def _heal(power: int, caster_mag: int) -> int:
    return max(1, int(power * (caster_mag / 40.0) * random.uniform(0.9, 1.1)))

def resolve_enemy_action(enemy: EnemyInstance, action: str, targets: list[Character], party: Party) -> list[str]:
    msgs = []
    living_party = [m for m in party.members if m.alive]
    if not living_party: return msgs
    one = random.choice(living_party)

    if action == 'Attack':
        d = _phys(enemy.atk_eff, one.defense)
        one.hp -= d
        msgs.append(f'{enemy.name} attacks {one.name} for {d} damage!')

    elif action in ('Stab', 'Dark Slash'):
        d = int(_phys(enemy.atk_eff, one.defense) * 1.4)
        one.hp -= d
        msgs.append(f'{enemy.name} uses {action} on {one.name} for {d} damage!')
        if action == 'Dark Slash' and random.random() < 0.4:
            if one.apply_status('blind'): msgs.append(f'{one.name} is blinded!')

    elif action == 'Bite':
        d = _phys(enemy.atk_eff, one.defense)
        one.hp -= d
        msgs.append(f'{enemy.name} bites {one.name} for {d} damage!')
        if random.random() < 0.35:
            if one.apply_status('blind'): msgs.append(f'{one.name} is blinded!')

    elif action in ('Spore', 'Poison Spore'):
        msgs.append(f'{enemy.name} releases {action}!')
        for m in living_party:
            if random.random() < 0.4:
                if m.apply_status('poison', 3): msgs.append(f'{m.name} is poisoned!')

    elif action == 'Vine':
        msgs.append(f'{enemy.name} tangles {one.name}!')
        d = _phys(int(enemy.atk_eff * 0.7), one.defense)
        one.hp -= d
        if random.random() < 0.5:
            if one.apply_status('sleep', 2): msgs.append(f'{one.name} falls asleep!')

    elif action in ('Ember', 'Fire Breath', 'Flame Burst'):
        power = 35 if action == 'Ember' else (55 if action == 'Flame Burst' else 45)
        tgts = living_party if action in ('Fire Breath',) else [one]
        for t in tgts:
            d = _magic(power, enemy.mag_eff, t, 'fire')
            t.hp -= d
            msgs.append(f'{enemy.name} uses {action} on {t.name} for {d} fire damage!')

    elif action == 'Rock Slam':
        d = int(_phys(enemy.atk_eff, one.defense) * 1.6)
        one.hp -= d
        msgs.append(f'{enemy.name} SLAMS {one.name} for {d} damage!')
        if random.random() < 0.3:
            if one.apply_status('stun', 1): msgs.append(f'{one.name} is stunned!')

    elif action == 'Blind':
        if one.apply_status('blind', 3): msgs.append(f'{enemy.name} blinds {one.name}!')
        else: msgs.append(f'{enemy.name}\'s blind fails!')

    elif action == 'Tail Swipe':
        msgs.append(f'{enemy.name} tail swipes!')
        for t in living_party:
            d = _phys(int(enemy.atk_eff * 0.8), t.defense)
            t.hp -= d
            msgs.append(f'  {t.name} takes {d} damage!')

    elif action == 'Vine Whip':
        d = int(_phys(enemy.atk_eff, one.defense) * 1.2)
        one.hp -= d
        msgs.append(f'{enemy.name} whips {one.name} for {d} damage!')
        if random.random() < 0.4:
            if one.apply_status('slow', 3): msgs.append(f'{one.name} is slowed!')

    elif action == 'Entangle':
        msgs.append(f'{enemy.name} entangles the party!')
        for t in living_party:
            if random.random() < 0.35:
                if t.apply_status('sleep', 2): msgs.append(f'  {t.name} falls asleep!')

    elif action in ('Inferno', 'Magma Wave'):
        msgs.append(f'{enemy.name} unleashes {action}!')
        for t in living_party:
            d = _magic(80 if action == 'Inferno' else 65, enemy.mag_eff, t, 'fire')
            t.hp -= d
            msgs.append(f'  {t.name} takes {d} fire damage!')

    elif action == 'Enrage':
        enemy.buffs['atk'] = enemy.buffs.get('atk', 1.0) * 1.35
        msgs.append(f'{enemy.name} ENRAGES! Attack surges!')

    elif action == 'Crystal Slam':
        d = int(_phys(enemy.atk_eff, one.defense) * 1.5)
        one.hp -= d
        msgs.append(f'{enemy.name} crystal slams {one.name} for {d} damage!')

    elif action == 'Reflect':
        enemy.buffs['def'] = enemy.buffs.get('def', 1.0) * 1.4
        msgs.append(f'{enemy.name} hardens its crystal shell!')

    elif action == 'Dark Wave':
        msgs.append(f'{enemy.name} unleashes Dark Wave!')
        for t in living_party:
            d = _magic(55, enemy.mag_eff, t, 'dark')
            t.hp -= d
            msgs.append(f'  {t.name} takes {d} dark damage!')

    elif action == 'Drain':
        d = _magic(50, enemy.mag_eff, one, None)
        one.hp -= d
        enemy.hp = min(enemy.max_hp, enemy.hp + d // 2)
        msgs.append(f'{enemy.name} drains {d} HP from {one.name}!')

    elif action == 'Silence':
        if one.apply_status('silence', 3): msgs.append(f'{enemy.name} silences {one.name}!')
        else: msgs.append(f'{enemy.name}\'s silence fails!')

    elif action == 'Laser':
        d = _phys(int(enemy.atk_eff * 1.3), one.defense)
        one.hp -= d
        msgs.append(f'{enemy.name} fires a laser at {one.name} for {d} damage!')

    elif action == 'System Shock':
        msgs.append(f'{enemy.name} fires System Shock!')
        for t in living_party:
            if random.random() < 0.55:
                if t.apply_status('silence', 2): msgs.append(f'  {t.name} is silenced!')

    elif action == 'Berserk':
        enemy.buffs['atk'] = enemy.buffs.get('atk', 1.0) * 1.5
        enemy.buffs['def'] = enemy.buffs.get('def', 1.0) * 0.7
        msgs.append(f'{enemy.name} goes BERSERK!')

    elif action == 'Laser Array':
        msgs.append('SYNTHOS fires Laser Array!')
        for t in living_party:
            d = _magic(70, enemy.mag_eff, t, None)
            t.hp -= d
            msgs.append(f'  {t.name} takes {d} damage!')

    elif action == 'System Crush':
        d = int(_phys(enemy.atk_eff * 1.8, one.defense))
        one.hp -= d
        msgs.append(f'SYNTHOS crushes {one.name} for {d} damage!')

    elif action == 'Void Pulse':
        msgs.append('SYNTHOS emits Void Pulse!')
        for t in living_party:
            if random.random() < 0.45:
                t.apply_status('silence', 2); msgs.append(f'  {t.name} silenced!')
            if random.random() < 0.25:
                t.apply_status('stun', 1);    msgs.append(f'  {t.name} stunned!')

    elif action == 'Assimilation':
        msgs.append('SYNTHOS initiates Assimilation!')
        for t in living_party:
            d = int(t.max_hp * 0.18)
            t.hp -= d; enemy.hp = min(enemy.max_hp, enemy.hp + d // 3)
            msgs.append(f'  Drains {d} HP from {t.name}!')

    elif action == 'Overload':
        msgs.append('⚡ SYNTHOS OVERLOADS ⚡')
        for t in living_party:
            d = _magic(150, enemy.mag_eff, t, None)
            t.hp -= d
            msgs.append(f'  {t.name} takes {d} MASSIVE damage!')

    return msgs


class Battle:
    """
    State machine:
      ROUND_START → ACTOR_TURN (loop) → ROUND_END → WIN / LOSE
      ACTOR_TURN sub-states (player): ACT_MENU, ACT_SPELL, ACT_ITEM, ACT_TARGET
      ACTOR_TURN sub-states (enemy): auto-resolve
    """

    def __init__(self, party: Party, enemy_names: list[str], is_boss=False):
        self.party   = party
        self.enemies = [EnemyInstance(n) for n in enemy_names]
        self.is_boss = is_boss
        self.result  = None   # 'win' | 'lose' | 'escaped'

        # Turn state
        self._turn_order: list[tuple[str, Character | EnemyInstance]] = []
        self._turn_idx   = 0
        self._state      = 'ROUND_START'

        # Player input
        self._act_state  = 'ACT_MENU'
        self._act_cursor = 0
        self._spell_cursor = 0
        self._item_cursor  = 0
        self._target_cursor = 0
        self._pending_spell = None
        self._pending_item  = None
        self._act_mode      = None   # 'spell'|'item'|'target'

        # Message log
        self.log: list[str] = []
        self._anim_timer    = 0
        self._phase_msg     = ''
        self._phase_timer   = 0
        self._spell_fx_name = ''
        self._spell_fx_timer = 0

        self._build_turn_order()

    def _build_turn_order(self) -> None:
        actors: list[tuple[str, Character | EnemyInstance]] = []
        for m in self.party.members:
            if m.alive: actors.append(('player', m))
        for e in self.enemies:
            if e.alive: actors.append(('enemy', e))
        # Party members get a small speed advantage to act first on ties
        def sort_key(a: tuple[str, Character | EnemyInstance]) -> int:
            kind, actor = a
            spd = actor.spd if hasattr(actor, 'spd') else 0
            bonus = 2 if kind == 'player' else 0
            return spd + bonus
        actors.sort(key=sort_key, reverse=True)
        self._turn_order = actors
        self._turn_idx   = 0
        self._state      = 'ACTOR_TURN'
        self._prep_next_actor()

    def _prep_next_actor(self):
        while self._turn_idx < len(self._turn_order):
            kind, actor = self._turn_order[self._turn_idx]
            if not actor.alive:
                self._turn_idx += 1; continue
            # tick status
            _, msgs = actor.tick_status()
            self.log.extend(msgs)
            if not actor.alive:
                self.log.append(f'{actor.name} succumbed to poison!')
                self._turn_idx += 1; continue
            # skip if sleeping/stunned
            if 'sleep' in actor.status or 'stun' in actor.status:
                self.log.append(f'{actor.name} cannot act!')
                self._turn_idx += 1; continue
            # ready
            if kind == 'enemy':
                self._do_enemy_turn(actor)
                self._turn_idx += 1
                self._prep_next_actor()
            else:
                # player turn — wait for input
                self._act_state  = 'ACT_MENU'
                self._act_cursor = 0
                actor.defending  = False
                return
            return
        # all actors done → new round
        self._check_phase()
        self._state = 'ROUND_CHECK'

    def _do_enemy_turn(self, enemy: EnemyInstance):
        action = enemy.choose_action()
        msgs = resolve_enemy_action(enemy, action, self.party.members, self.party)
        self.log.extend(msgs)

    def _current_actor(self):
        if self._turn_idx >= len(self._turn_order): return None, None
        return self._turn_order[self._turn_idx]

    def _living_enemies(self): return [e for e in self.enemies if e.alive]
    def _living_party(self):   return [m for m in self.party.members if m.alive]

    def _check_phase(self):
        for e in self.enemies:
            if e.boss and e.check_phase():
                self._phase_msg   = f'★ {e.name} PHASE 2! ★'
                self._phase_timer = 60

    def _items_available(self):
        # Only show consumables (not equipment pieces that ended up in inventory)
        return [(n, c) for n, c in self.party.items.items()
                if c > 0 and n in ITEMS]

    def handle_key(self, key):
        if self.result: return
        kind, actor = self._current_actor()

        # round check — auto advance
        if self._state == 'ROUND_CHECK':
            if not self._living_enemies():
                self.result = 'win'; return
            if not self._living_party():
                self.result = 'lose'; return
            self._build_turn_order()
            return

        if kind != 'player': return   # waiting on enemy auto-resolve

        UP   = key in (curses.KEY_UP,   ord('w'), ord('k'))
        DOWN = key in (curses.KEY_DOWN,  ord('s'), ord('j'))
        OK   = key in (ord('\n'), ord(' '), ord('l'))
        BACK = key in (27, ord('q'), curses.KEY_BACKSPACE, ord('h'))

        if self._act_state == 'ACT_MENU':
            opts = self._menu_options(actor)
            if UP:   self._act_cursor = (self._act_cursor - 1) % len(opts)
            if DOWN: self._act_cursor = (self._act_cursor + 1) % len(opts)
            if OK:
                choice = opts[self._act_cursor]
                if choice == 'Attack':
                    self._act_mode = 'attack_target'
                    self._act_state = 'ACT_TARGET'
                    self._target_cursor = 0
                elif choice == 'Magic':
                    self._act_state  = 'ACT_SPELL'
                    self._spell_cursor = 0
                elif choice == 'Item':
                    self._act_state = 'ACT_ITEM'
                    self._item_cursor = 0
                elif choice == 'Defend':
                    actor.defending = True
                    self.log.append(f'{actor.name} defends!')
                    self._advance_turn()
                elif choice == 'Run':
                    self._try_run()

        elif self._act_state == 'ACT_SPELL':
            spells = actor.spells
            if not spells:
                self._act_state = 'ACT_MENU'; return
            if UP:   self._spell_cursor = (self._spell_cursor - 1) % len(spells)
            if DOWN: self._spell_cursor = (self._spell_cursor + 1) % len(spells)
            if BACK: self._act_state = 'ACT_MENU'; return
            if OK:
                sp_name = spells[self._spell_cursor]
                sp      = SPELLS.get(sp_name, {})
                if actor.mp < sp.get('mp', 0):
                    self.log.append('Not enough MP!'); return
                self._pending_spell = sp_name
                tgt = sp.get('target', 'one')
                stype = sp.get('type', '')
                if tgt == 'all' or stype in ('heal','raise','esuna','buff_def','buff_mdef','buff_spd') or stype.startswith('buff'):
                    self._act_mode = 'spell_all'
                    self._cast_spell(actor, sp_name, None)
                else:
                    self._act_mode  = 'spell_target'
                    self._act_state = 'ACT_TARGET'
                    self._target_cursor = 0

        elif self._act_state == 'ACT_ITEM':
            avail = self._items_available()
            if not avail:
                self._act_state = 'ACT_MENU'; return
            if UP:   self._item_cursor = (self._item_cursor - 1) % len(avail)
            if DOWN: self._item_cursor = (self._item_cursor + 1) % len(avail)
            if BACK: self._act_state = 'ACT_MENU'; return
            if OK:
                self._pending_item = avail[self._item_cursor][0]
                it = ITEMS.get(self._pending_item, {})
                if it.get('target') == 'all' or it.get('type') == 'dmg':
                    self._use_item(actor, self._pending_item, None)
                else:
                    self._act_mode  = 'item_target'
                    self._act_state = 'ACT_TARGET'
                    self._target_cursor = 0

        elif self._act_state == 'ACT_TARGET':
            if self._act_mode in ('attack_target', 'spell_target'):
                targets = self._living_enemies()
            else:
                targets = self.party.members
            if not targets: return
            if UP:   self._target_cursor = (self._target_cursor - 1) % len(targets)
            if DOWN: self._target_cursor = (self._target_cursor + 1) % len(targets)
            if BACK:
                if self._act_mode == 'spell_target': self._act_state = 'ACT_SPELL'
                elif self._act_mode == 'item_target': self._act_state = 'ACT_ITEM'
                else: self._act_state = 'ACT_MENU'
                return
            if OK:
                t = targets[min(self._target_cursor, len(targets)-1)]
                if self._act_mode == 'attack_target':
                    self._do_attack(actor, t)
                elif self._act_mode == 'spell_target':
                    self._cast_spell(actor, self._pending_spell, t)
                elif self._act_mode == 'item_target':
                    self._use_item(actor, self._pending_item, t)

    def _menu_options(self, actor):
        opts = ['Attack']
        if actor.spells: opts.append('Magic')
        opts.append('Item')
        opts.append('Defend')
        if not self.is_boss: opts.append('Run')
        return opts

    def _do_attack(self, actor: Character, target: EnemyInstance):
        miss = 'blind' in actor.status and random.random() < 0.4
        if miss:
            self.log.append(f'{actor.name} attacks but misses!')
        else:
            d = _phys(actor.atk, target.defense_eff)
            target.hp -= d
            self.log.append(f'{actor.name} attacks {target.name} for {d} damage!')
            if not target.alive:
                self.log.append(f'{target.name} is defeated!')
        self._advance_turn()

    def _cast_spell(self, actor: Character, sp_name: str, target):
        sp   = SPELLS[sp_name]
        cost = sp['mp']
        if actor.mp < cost:
            self.log.append('Not enough MP!'); return
        actor.mp -= cost
        self.log.append(f'{actor.name}: {sp["msg"]}')
        # Trigger spell FX animation
        if sp_name in SPELL_FX:
            self._spell_fx_name  = sp_name
            self._spell_fx_timer = len(SPELL_FX[sp_name]) * 8
        stype  = sp['type']
        power  = sp.get('power', 0)
        tgt_all = sp.get('target') == 'all'

        # Silence check
        if 'silence' in actor.status:
            actor.mp += cost
            self.log.append(f'{actor.name} is silenced!'); return

        if stype in ('fire','ice','lightning','holy','none','physical','dark'):
            tgts = self._living_enemies() if tgt_all else [target]
            for t in tgts:
                d = _magic(power, actor.mag, t, stype)
                t.hp -= d
                self.log.append(f'  {t.name} takes {d} damage!')
                if not t.alive: self.log.append(f'  {t.name} is defeated!')
        elif stype == 'heal':
            if tgt_all:
                tgts = self._living_party()
            else:
                # Only heal living targets; dead members require Raise/Phoenix Down
                if target and isinstance(target, Character) and target.alive:
                    tgts = [target]
                else:
                    self.log.append('  Cannot heal the fallen! Use Raise or Phoenix Down.')
                    tgts = []
            for t in tgts:
                amt = _heal(power, actor.mag)
                t.hp += amt
                self.log.append(f'  {t.name} recovers {amt} HP!')
        elif stype == 'raise':
            if target and isinstance(target, Character):
                if target.alive:
                    self.log.append(f'{target.name} is conscious!')
                else:
                    target.hp = target.max_hp // 4
                    self.log.append(f'{target.name} is revived!')
        elif stype == 'esuna':
            tgts = self._living_party() if tgt_all else ([target] if target else [])
            for t in tgts:
                t.status.clear()
                self.log.append(f'  {t.name} is cleansed!')
        elif stype in ('buff_def', 'buff_mdef'):
            tgts = self._living_party() if tgt_all else ([target] if target else [])
            for t in tgts:
                t.apply_buff('def', 1.5)
                self.log.append(f'  {t.name}\'s defense rises!')
        elif stype == 'buff_spd':
            tgts = self._living_party() if tgt_all else ([target] if target else [])
            for t in tgts:
                t.apply_buff('spd', 1.4)
                self.log.append(f'  {t.name}\'s speed rises!')
        elif stype == 'poison':
            if target and isinstance(target, EnemyInstance):
                if target.apply_status('poison', 4): self.log.append(f'  {target.name} is poisoned!')
                else: self.log.append(f'  {target.name} resists poison!')
        elif stype == 'sleep':
            if target and isinstance(target, EnemyInstance):
                if target.apply_status('sleep', 3): self.log.append(f'  {target.name} falls asleep!')
                else: self.log.append(f'  {target.name} resists sleep!')
        elif stype == 'silence':
            if target and isinstance(target, EnemyInstance):
                if target.apply_status('silence', 3): self.log.append(f'  {target.name} is silenced!')
                else: self.log.append(f'  {target.name} resists silence!')
        elif stype == 'slow':
            tgts = [target] if target else []
            for t in tgts:
                if isinstance(t, EnemyInstance):
                    t.apply_status('slow', 3); t.buffs['spd'] = 0.6
                    self.log.append(f'  {t.name} is slowed!')

        self._advance_turn()

    def _use_item(self, actor: Character, item_name: str, target):
        it = ITEMS.get(item_name, {})
        if it.get('target') == 'all' or it.get('type') == 'dmg':
            # AoE
            if it.get('type') == 'dmg':
                self.party.remove_item(item_name)
                self.log.append(f'{actor.name} throws a Grenade!')
                for e in self._living_enemies():
                    d = it['power']
                    e.hp -= d
                    self.log.append(f'  {e.name} takes {d} damage!')
                    if not e.alive: self.log.append(f'  {e.name} defeated!')
            elif it.get('type') == 'heal':
                self.party.remove_item(item_name)
                self.log.append(f'{actor.name} uses {item_name}!')
                for m in self._living_party():
                    m.hp += it['power']
                    self.log.append(f'  {m.name} recovers {it["power"]} HP!')
            self._advance_turn()
        else:
            msg = self.party.use_item(item_name, target)
            self.log.append(msg)
            self._advance_turn()

    def _try_run(self):
        avg_spd = sum(m.spd for m in self._living_party()) / max(1, len(self._living_party()))
        e_spd   = sum(e.spd for e in self._living_enemies()) / max(1, len(self._living_enemies()))
        chance  = 0.75 + 0.2 * (avg_spd - e_spd) / max(1, avg_spd + e_spd)
        if random.random() < chance:
            self.result = 'escaped'
        else:
            self.log.append('Couldn\'t escape!')
            self._advance_turn()

    def _advance_turn(self):
        self._act_state = 'ACT_MENU'
        self._turn_idx += 1
        if not self._living_enemies():
            self.result = 'win'; return
        if not self._living_party():
            self.result = 'lose'; return
        self._prep_next_actor()

    def battle_end_rewards(self) -> list[str]:
        msgs = []
        if self.result != 'win': return msgs
        total_exp  = sum(e.exp  for e in self.enemies)
        total_gold = sum(e.gold for e in self.enemies)
        self.party.gold += total_gold
        msgs.append(f'Gained {total_gold} gold!')
        for m in self.party.alive_members:
            lmsgs = m.gain_exp(total_exp)
            msgs.extend(lmsgs)
        # drops
        for e in self.enemies:
            for item, chance in e.drops:
                if random.random() < chance:
                    self.party.add_item(item)
                    msgs.append(f'Found {item}!')
        return msgs

    def _status_tag(self, status_dict: dict) -> str:
        """Build a compact status tag string using icons."""
        parts = []
        for k in status_dict:
            icon = STATUS_ICONS.get(k, k[:3].upper())
            parts.append(icon)
        return ' '.join(parts) if parts else ''

    def _hp_color(self, cur, mx):
        if mx <= 0: return 2
        ratio = cur / mx
        if ratio > 0.5: return 3
        if ratio > 0.25: return 4
        return 2

    def draw(self, scr, H, W, tick):
        P = curses.color_pair
        scr.erase()

        # Phase message overlay (full screen)
        if self._phase_timer > 0:
            self._phase_timer -= 1
            box(scr, 0, 0, H, W, '', 5)
            center(scr, H//2-1, '╔══════════════════════╗', W, P(2)|curses.A_BOLD)
            center(scr, H//2,   f'  {self._phase_msg}  ',  W, P(2)|curses.A_BOLD)
            center(scr, H//2+1, '╚══════════════════════╝', W, P(2)|curses.A_BOLD)
            scr.refresh(); return

        # ── LAYOUT ────────────────────────────────────────────
        # Top: enemies on RIGHT half, party stats on LEFT half, divider │
        # Below divider: action menu LEFT, battle log RIGHT
        # ──────────────────────────────────────────────────────

        DIVIDER_COL = W // 2         # vertical divider between party/enemy areas
        PARTY_PANEL_H = 3 + len(self.party.members) * 4 + 1   # rows for party stats
        TOP_H = max(PARTY_PANEL_H, 14)    # height of top combat area
        TOP_H = min(TOP_H, H - 10)

        # Outer border
        box(scr, 0, 0, H, W, '', 5)

        # Header
        is_boss = any(e.boss for e in self.enemies)
        header_txt = '  ⚔  B A T T L E  ⚔  ' if not is_boss else '  ★  B O S S  B A T T L E  ★  '
        header_cp  = P(4)|curses.A_BOLD if not is_boss else P(2)|curses.A_BOLD
        safe_add(scr, 1, (W - len(header_txt)) // 2, header_txt, header_cp)

        # Horizontal separator after header
        safe_add(scr, 2, 0, '╠' + '═'*(W-2) + '╣', P(5))

        # Vertical divider in combat area
        for vy in range(3, TOP_H + 3):
            safe_add(scr, vy, DIVIDER_COL, '║', P(5))

        # ── LEFT: PARTY PANEL ─────────────────────────────────
        party_x = 1
        party_label_y = 3
        safe_add(scr, party_label_y, party_x,
                 '┌─  P A R T Y  ─────────────────┐'[:DIVIDER_COL-2],
                 P(1)|curses.A_BOLD)

        for mi, m in enumerate(self.party.members):
            base_y = party_label_y + 1 + mi * 4
            is_cur = (self._state == 'ACTOR_TURN' and
                      self._turn_idx < len(self._turn_order) and
                      self._turn_order[self._turn_idx][1] is m)

            # Name row
            turn_arrow = '▶' if is_cur else ' '
            ko_tag     = '  ✝KO✝' if not m.alive else ''
            name_attr  = (P(m.color)|curses.A_BOLD|curses.A_REVERSE) if is_cur else (P(m.color)|curses.A_BOLD if m.alive else P(5)|curses.A_DIM)
            name_str   = f'{turn_arrow} {m.name:<7} {m.cls:<7} Lv{m.level:>2}{ko_tag}'
            safe_add(scr, base_y, party_x, name_str[:DIVIDER_COL-2], name_attr)

            if not m.alive:
                safe_add(scr, base_y+1, party_x+2, '── Fallen ──', P(5)|curses.A_DIM)
                continue

            # HP bar row
            hp_w  = min(16, DIVIDER_COL - 24)
            hp_cp = self._hp_color(m.hp, m.max_hp)
            safe_add(scr, base_y+1, party_x+2, 'HP', P(hp_cp)|curses.A_BOLD)
            bar(scr, base_y+1, party_x+5, m.hp, m.max_hp, hp_w, hp_cp)
            hp_str = f'{m.hp:>4}/{m.max_hp}'
            safe_add(scr, base_y+1, party_x+5+hp_w+1, hp_str, P(5))

            # MP bar row
            mp_w  = min(16, DIVIDER_COL - 24)
            safe_add(scr, base_y+2, party_x+2, 'MP', P(8)|curses.A_BOLD)
            bar(scr, base_y+2, party_x+5, m.mp, m.max_mp, mp_w, 8)
            mp_str = f'{m.mp:>4}/{m.max_mp}'
            safe_add(scr, base_y+2, party_x+5+mp_w+1, mp_str, P(5))

            # Status row
            if m.status:
                stag = self._status_tag(m.status)
                safe_add(scr, base_y+3, party_x+2, stag[:DIVIDER_COL-4], P(6)|curses.A_BOLD)
            else:
                safe_add(scr, base_y+3, party_x+2, '· · ·', P(5)|curses.A_DIM)

        # ── RIGHT: ENEMY PANEL ────────────────────────────────
        enemy_x0  = DIVIDER_COL + 2
        enemy_area_w = W - DIVIDER_COL - 3
        enemies = self.enemies
        n_enemies = max(1, len(enemies))
        e_slot_w  = max(12, enemy_area_w // n_enemies)

        safe_add(scr, 3, enemy_x0,
                 '┌─  E N E M I E S  ─────────────┐'[:enemy_area_w],
                 P(2)|curses.A_BOLD)

        # Spell FX overlay
        if self._spell_fx_timer > 0:
            self._spell_fx_timer -= 1
            fx_frames = SPELL_FX.get(self._spell_fx_name, [])
            if fx_frames:
                frame_idx = min(len(fx_frames)-1,
                                (len(fx_frames) * 8 - self._spell_fx_timer) // 8)
                fx_str = fx_frames[frame_idx]
                fx_y = 4 + (TOP_H // 2)
                center_x = DIVIDER_COL + 2 + (enemy_area_w - len(fx_str)) // 2
                safe_add(scr, fx_y,   max(DIVIDER_COL+2, center_x-2),
                         '·' * min(enemy_area_w, len(fx_str)+4), P(6)|curses.A_DIM)
                safe_add(scr, fx_y+1, max(DIVIDER_COL+2, center_x),
                         fx_str[:enemy_area_w], P(2)|curses.A_BOLD)
                safe_add(scr, fx_y+2, max(DIVIDER_COL+2, center_x-2),
                         '·' * min(enemy_area_w, len(fx_str)+4), P(6)|curses.A_DIM)

        for i, e in enumerate(enemies):
            ex = enemy_x0 + i * e_slot_w
            ey = 4

            if not e.alive:
                ko_y = ey + 2
                safe_add(scr, ko_y,   ex, '  ╔══════╗  '[:e_slot_w], P(5)|curses.A_DIM)
                safe_add(scr, ko_y+1, ex, '  ║ ✝KO✝ ║  '[:e_slot_w], P(2)|curses.A_BOLD)
                safe_add(scr, ko_y+2, ex, '  ╚══════╝  '[:e_slot_w], P(5)|curses.A_DIM)
                continue

            cp = P(e.color) | curses.A_BOLD
            # Boss sprite flashes on phase change
            if e.boss and e.phase == 1 and (tick // 6) % 2 == 0:
                cp = P(2) | curses.A_BOLD

            for si, row in enumerate(e.sprite):
                if ey + si >= TOP_H + 3: break
                safe_add(scr, ey + si, ex, row[:e_slot_w], cp)

            ny = ey + len(e.sprite) + 1
            if ny < TOP_H + 3:
                safe_add(scr, ny, ex, e.name[:e_slot_w-2], P(5)|curses.A_BOLD)
            if ny+1 < TOP_H + 3:
                hp_w2 = min(e_slot_w - 4, 14)
                hp_cp = self._hp_color(e.hp, e.max_hp)
                bar(scr, ny+1, ex, e.hp, e.max_hp, hp_w2, hp_cp)
                safe_add(scr, ny+1, ex+hp_w2+1, f'{e.hp}/{e.max_hp}', P(5))
            if ny+2 < TOP_H + 3 and e.status:
                stag = self._status_tag(e.status)
                safe_add(scr, ny+2, ex, stag[:e_slot_w-2], P(6)|curses.A_BOLD)

        # ── MIDDLE DIVIDER ────────────────────────────────────
        div_y = TOP_H + 3
        safe_add(scr, div_y, 0, '╠' + '═'*(W-2) + '╣', P(5))
        # sub-vertical divider for action/log
        act_log_split = DIVIDER_COL
        for vy in range(div_y+1, H-1):
            safe_add(scr, vy, act_log_split, '│', P(5)|curses.A_DIM)

        # ── BOTTOM LEFT: ACTION MENU ──────────────────────────
        kind, actor = self._current_actor()
        act_y = div_y + 1
        menu_w = act_log_split - 2

        if self._state != 'ROUND_CHECK' and not self.result:
            if kind == 'player' and self._act_state == 'ACT_MENU':
                opts = self._menu_options(actor)
                # Actor indicator
                actor_label = f'  ▶ {actor.name}\'s Turn'
                safe_add(scr, act_y, 1, actor_label, P(actor.color)|curses.A_BOLD)
                # Command box
                box(scr, act_y+1, 1, len(opts)+2, menu_w, '', 4)
                for ci, opt in enumerate(opts):
                    sel = ci == self._act_cursor
                    icon = {'Attack': '⚔', 'Magic': '✦', 'Item': '◈', 'Defend': '◇', 'Run': '→'}.get(opt, ' ')
                    label = f' {icon} {opt}'
                    attr  = P(7)|curses.A_BOLD if sel else P(4)
                    safe_add(scr, act_y+2+ci, 3, label.ljust(menu_w-4)[:menu_w-4], attr)

            elif kind == 'player' and self._act_state == 'ACT_SPELL':
                spells = actor.spells
                safe_add(scr, act_y, 1, f'  ✦ {actor.name} — MAGIC', P(6)|curses.A_BOLD)
                visible_spells = spells[:min(8, H - act_y - 4)]
                box(scr, act_y+1, 1, len(visible_spells)+2, menu_w, '', 6)
                for i, sp_name in enumerate(visible_spells):
                    sp   = SPELLS.get(sp_name, {})
                    sel  = i == self._spell_cursor
                    mp   = sp.get('mp', 0)
                    stype = sp.get('type','')
                    type_icon = {'fire':'✦','ice':'❄','lightning':'⚡','heal':'♥','raise':'†','esuna':'◌','holy':'★'}.get(stype,'·')
                    can  = actor.mp >= mp
                    label = f' {type_icon} {sp_name:<13} {mp:>3}MP'
                    attr  = (P(7)|curses.A_BOLD) if sel else (P(6) if can else P(5)|curses.A_DIM)
                    safe_add(scr, act_y+2+i, 3, label[:menu_w-4], attr)

            elif kind == 'player' and self._act_state == 'ACT_ITEM':
                avail = self._items_available()
                safe_add(scr, act_y, 1, '  ◈ ITEMS', P(4)|curses.A_BOLD)
                visible_items = avail[:min(8, H - act_y - 4)]
                box(scr, act_y+1, 1, len(visible_items)+2, menu_w, '', 4)
                for i, (name, cnt) in enumerate(visible_items):
                    sel   = i == self._item_cursor
                    label = f' ◈ {name:<18} ×{cnt}'
                    attr  = P(7)|curses.A_BOLD if sel else P(4)
                    safe_add(scr, act_y+2+i, 3, label[:menu_w-4], attr)

            elif kind == 'player' and self._act_state == 'ACT_TARGET':
                if self._act_mode in ('attack_target', 'spell_target'):
                    tgts = self._living_enemies()
                    safe_add(scr, act_y, 1, '  ▶ Select Enemy Target', P(2)|curses.A_BOLD)
                    tcp = 2
                else:
                    tgts = self.party.members
                    safe_add(scr, act_y, 1, '  ▶ Select Ally Target', P(1)|curses.A_BOLD)
                    tcp = 1
                box(scr, act_y+1, 1, len(tgts)+2, menu_w, '', tcp)
                for i, t in enumerate(tgts[:6]):
                    sel   = i == self._target_cursor
                    arrow = '▶' if sel else ' '
                    hp_info = f'HP:{t.hp}/{t.max_hp}' if hasattr(t,'max_hp') else ''
                    label = f' {arrow} {t.name:<12} {hp_info}'
                    attr  = P(7)|curses.A_BOLD if sel else P(tcp)
                    safe_add(scr, act_y+2+i, 3, label[:menu_w-4], attr)

        # ── BOTTOM RIGHT: BATTLE LOG ──────────────────────────
        log_x  = act_log_split + 1
        log_y  = act_y
        log_w  = W - log_x - 2
        log_h  = H - log_y - 2
        safe_add(scr, log_y, log_x,
                 '┤ B A T T L E   L O G ├'[:log_w], P(5)|curses.A_BOLD)
        visible = self.log[-(log_h):] if len(self.log) > log_h else self.log
        for i, line in enumerate(visible):
            # Colour-code log lines
            if 'damage' in line.lower() or 'attacks' in line.lower():
                lattr = P(2)
            elif 'recover' in line.lower() or 'heals' in line.lower() or 'revived' in line.lower():
                lattr = P(3)
            elif 'defeated' in line.lower() or 'KO' in line or 'succumbed' in line.lower():
                lattr = P(2)|curses.A_BOLD
            elif 'PHASE' in line or 'OVERLOAD' in line or 'SYNTHOS' in line:
                lattr = P(6)|curses.A_BOLD
            elif any(s in line.lower() for s in ('poisoned','silenced','asleep','blinded','slowed','stunned')):
                lattr = P(6)
            else:
                lattr = P(5)
            safe_add(scr, log_y+1+i, log_x+1, line[:log_w-2], lattr)

        scr.refresh()

    def draw_result(self, scr, H, W, msgs, cursor):
        """Draw win/lose/escaped result screen."""
        P = curses.color_pair
        scr.erase()
        box(scr, 0, 0, H, W, '', 5)

        if self.result == 'win':
            banner = [
                '╔══════════════════════════════╗',
                '║   ★  V I C T O R Y  ★       ║',
                '╚══════════════════════════════╝',
            ]
            bcp = P(4)|curses.A_BOLD
        elif self.result == 'lose':
            banner = [
                '╔══════════════════════════════╗',
                '║  ✖  D E F E A T E D  ✖      ║',
                '╚══════════════════════════════╝',
            ]
            bcp = P(2)|curses.A_BOLD
        else:
            banner = [
                '╔══════════════════════════════╗',
                '║    →  E S C A P E D  →       ║',
                '╚══════════════════════════════╝',
            ]
            bcp = P(6)|curses.A_BOLD

        banner_y = max(2, H//2 - len(msgs)//2 - 4)
        for i, bl in enumerate(banner):
            center(scr, banner_y + i, bl, W, bcp)

        text_y = banner_y + len(banner) + 1
        for i, m in enumerate(msgs):
            if m.startswith('★') or m.startswith('S Y N T H O S') or m.startswith('F I N A L'):
                attr = P(4)|curses.A_BOLD
            elif 'level' in m.lower() or 'learned' in m.lower():
                attr = P(6)|curses.A_BOLD
            elif 'gold' in m.lower() or 'found' in m.lower():
                attr = P(3)|curses.A_BOLD
            elif 'game over' in m.lower() or 'defeated' in m.lower():
                attr = P(2)|curses.A_BOLD
            else:
                attr = P(5)
            center(scr, text_y + i, m, W, attr)

        center(scr, H-3, '✦ [ Press SPACE ] ✦', W, P(5)|curses.A_BOLD)
        scr.refresh()
