"""Turn-based battle system."""
import curses, random, math
from .data    import SPELLS, ITEMS, ENEMIES as ENEMY_DATA
from .entities import EnemyInstance, Character, Party
from .ui       import safe_add, box, bar, menu_list, center

# ── Damage formulas ────────────────────────────────────────────────────────────
def _phys(attacker_atk, defender_def, variance=0.15):
    # Defense reduces damage but never below 15% of attacker's raw ATK
    base = max(attacker_atk * 0.15, attacker_atk - defender_def * 0.4)
    return max(1, int(base * random.uniform(1 - variance, 1 + variance)))

def _magic(power, caster_mag, defender, spell_type, variance=0.10):
    base = power * (caster_mag / 45.0)
    mult = 1.5 if (spell_type and getattr(defender, 'weakness', None) == spell_type) else 1.0
    return max(1, int(base * mult * random.uniform(1 - variance, 1 + variance)))

def _heal(power, caster_mag):
    return max(1, int(power * (caster_mag / 40.0) * random.uniform(0.9, 1.1)))

# ── Enemy ability resolver ─────────────────────────────────────────────────────
def resolve_enemy_action(enemy: EnemyInstance, action: str, targets: list, party: Party) -> list[str]:
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

    # ── SYNTHOS ────────────────────────────────────────────────────────────────
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


# ── Battle class ───────────────────────────────────────────────────────────────
class Battle:
    """
    State machine:
      ROUND_START → ACTOR_TURN (loop) → ROUND_END → WIN / LOSE
      ACTOR_TURN sub-states (player): ACT_MENU, ACT_SPELL, ACT_ITEM, ACT_TARGET
      ACTOR_TURN sub-states (enemy): auto-resolve
    """

    def __init__(self, party: Party, enemy_names: list[str], is_boss: bool = False) -> None:
        self.party   = party
        self.enemies: list[EnemyInstance] = [EnemyInstance(n) for n in enemy_names]
        self.is_boss = is_boss
        self.result: str | None = None   # 'win' | 'lose' | 'escaped' | None

        # Turn state — entries are ('player', Character) or ('enemy', EnemyInstance)
        self._turn_order: list[tuple[str, Character | EnemyInstance]] = []
        self._turn_idx   = 0
        self._state      = 'ROUND_START'

        # Player input
        self._act_state  = 'ACT_MENU'
        self._act_cursor = 0
        self._spell_cursor = 0
        self._item_cursor  = 0
        self._target_cursor = 0
        self._pending_spell: str | None = None
        self._pending_item:  str | None = None
        self._act_mode:      str | None = None   # 'attack_target'|'spell_target'|'spell_all'|'item_target'

        # Message log
        self.log: list[str] = []
        self._anim_timer    = 0
        self._phase_msg     = ''
        self._phase_timer   = 0

        self._build_turn_order()

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _build_turn_order(self):
        actors = []
        for m in self.party.members:
            if m.alive: actors.append(('player', m))
        for e in self.enemies:
            if e.alive: actors.append(('enemy', e))
        # Party members get a small speed advantage to act first on ties
        def sort_key(a):
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
        return [(n, c) for n, c in self.party.items.items() if c > 0]

    # ── Input handler (call each frame) ───────────────────────────────────────
    def handle_key(self, key: int) -> None:
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

    # ── Action executors ───────────────────────────────────────────────────────
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
            tgts = self._living_party() if tgt_all else [target]
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
        # check win/lose before continuing
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

    # ── Renderer ───────────────────────────────────────────────────────────────
    def draw(self, scr: 'curses.window', H: int, W: int, tick: int) -> None:
        P = curses.color_pair
        scr.erase()

        # Phase message overlay
        if self._phase_timer > 0:
            self._phase_timer -= 1
            center(scr, H//2, self._phase_msg, W, P(2)|curses.A_BOLD)
            scr.refresh(); return

        enemy_area_h = H - 16
        enemy_area_h = max(8, enemy_area_h)

        # ── Top border ──
        box(scr, 0, 0, H, W, '', 5)

        # ── Enemy area ──
        enemies = self.enemies
        ex_each = max(14, W // max(1, len(enemies)))
        for i, e in enumerate(enemies):
            ex = 2 + i * ex_each
            sprite = e.sprite
            ey_off = 2
            # Flash on defeat
            if not e.alive:
                safe_add(scr, ey_off + len(sprite)//2, ex + 2, '  * * K O * *  ', P(2)|curses.A_BOLD)
                continue
            # Boss name flash + idle pulse so the sprite breathes (was static).
            # Per-enemy phase offset so a row of enemies doesn't pulse in lockstep.
            phase  = (tick + i * 11) % 40
            bobble = 1 if phase < 20 else 0
            attr   = curses.A_BOLD if phase < 30 else curses.A_DIM
            cp     = P(e.color) | attr
            for si, row in enumerate(sprite):
                safe_add(scr, ey_off + si, ex + bobble, row, cp)
            # Name + HP bar
            ny = ey_off + len(sprite) + 1
            safe_add(scr, ny, ex, e.name[:ex_each-2], P(5)|curses.A_BOLD)
            hp_w = min(ex_each - 2, 18)
            hp_cp = 3 if e.hp > e.max_hp * 0.5 else (4 if e.hp > e.max_hp * 0.25 else 2)
            bar(scr, ny+1, ex, e.hp, e.max_hp, hp_w, hp_cp)
            safe_add(scr, ny+2, ex, f'{e.hp}/{e.max_hp}', P(5))
            # Status
            if e.status:
                s_str = ' '.join(f'[{k.upper()[:3]}]' for k in e.status)
                safe_add(scr, ny+3, ex, s_str[:ex_each-2], P(6))

        # ── Divider ──
        div_y = enemy_area_h + 2
        safe_add(scr, div_y, 0, '╠' + '═'*(W-2) + '╣', P(5))

        # ── Party status ──
        py = div_y + 1
        for mi, m in enumerate(self.party.members):
            mx = 1
            # Highlight current actor
            is_cur = (self._state == 'ACTOR_TURN' and
                      self._turn_idx < len(self._turn_order) and
                      self._turn_order[self._turn_idx][1] is m)
            name_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)
            if is_cur: name_attr |= curses.A_REVERSE
            label = f'{"▶ " if is_cur else "  "}{m.name:<8} Lv{m.level:<3}'
            safe_add(scr, py + mi, mx, label, name_attr)
            # HP bar
            bx = mx + 22
            hp_cp = 3 if m.hp > m.max_hp * 0.5 else (4 if m.hp > m.max_hp * 0.25 else 2)
            safe_add(scr, py+mi, bx-5, 'HP', P(3))
            bar(scr, py+mi, bx-3, m.hp, m.max_hp, 12, hp_cp)
            safe_add(scr, py+mi, bx+10, f'{m.hp:>4}/{m.max_hp}', P(5))
            # MP bar
            mpx = bx + 22
            safe_add(scr, py+mi, mpx-5, 'MP', P(8))
            bar(scr, py+mi, mpx-3, m.mp, m.max_mp, 10, 8)
            safe_add(scr, py+mi, mpx+8, f'{m.mp:>3}/{m.max_mp}', P(5))
            # Status
            sx = mpx + 18
            if not m.alive:
                safe_add(scr, py+mi, sx, '[KO]', P(2)|curses.A_BOLD)
            elif m.status:
                s_str = ' '.join(f'[{k.upper()[:3]}]' for k in m.status)
                safe_add(scr, py+mi, sx, s_str[:12], P(6))
            else:
                safe_add(scr, py+mi, sx, '[OK] ', P(3))

        # ── Second divider ──
        div2_y = py + 3
        safe_add(scr, div2_y, 0, '╠' + '═'*(W-2) + '╣', P(5))

        # ── Action menu ──
        kind, actor = self._current_actor()
        act_y = div2_y + 1

        if self._state == 'ROUND_CHECK' or self.result:
            pass  # nothing to show
        elif kind == 'player' and self._act_state == 'ACT_MENU':
            opts = self._menu_options(actor)
            safe_add(scr, act_y, 2, f'{actor.name}\'s turn:', P(actor.color)|curses.A_BOLD)
            menu_list(scr, act_y+1, 4, opts, self._act_cursor, width=10)

        elif kind == 'player' and self._act_state == 'ACT_SPELL':
            spells = actor.spells
            safe_add(scr, act_y, 2, 'MAGIC:', P(6)|curses.A_BOLD)
            for i, sp_name in enumerate(spells[:8]):
                sp = SPELLS.get(sp_name, {})
                label = f'{sp_name:<14} {sp.get("mp",0):>3}MP'
                cp = P(7)|curses.A_BOLD if i == self._spell_cursor else P(6)
                safe_add(scr, act_y+1+i, 4, label, cp)

        elif kind == 'player' and self._act_state == 'ACT_ITEM':
            avail = self._items_available()
            safe_add(scr, act_y, 2, 'ITEMS:', P(4)|curses.A_BOLD)
            for i, (name, cnt) in enumerate(avail[:8]):
                label = f'{name:<18} x{cnt}'
                cp = P(7)|curses.A_BOLD if i == self._item_cursor else P(4)
                safe_add(scr, act_y+1+i, 4, label, cp)

        elif kind == 'player' and self._act_state == 'ACT_TARGET':
            if self._act_mode in ('attack_target','spell_target'):
                tgts = self._living_enemies()
                safe_add(scr, act_y, 2, 'TARGET:', P(2)|curses.A_BOLD)
            else:
                tgts = self.party.members
                safe_add(scr, act_y, 2, 'TARGET:', P(1)|curses.A_BOLD)
            for i, t in enumerate(tgts[:6]):
                label = f'{"▶ " if i == self._target_cursor else "  "}{t.name}'
                cp = P(7)|curses.A_BOLD if i == self._target_cursor else P(5)
                safe_add(scr, act_y+1+i, 4, label, cp)

        # ── Message log ──
        log_x   = W // 2
        log_y   = act_y
        log_h   = H - act_y - 2
        safe_add(scr, log_y, log_x, '┤ BATTLE LOG ├', P(5))
        visible = self.log[-log_h:] if len(self.log) > log_h else self.log
        for i, line in enumerate(visible):
            safe_add(scr, log_y+1+i, log_x+1, line[:W-log_x-3], P(5))

        scr.refresh()

    def draw_result(self, scr: 'curses.window', H: int, W: int,
                    msgs: list[str], cursor: int) -> None:
        """Draw win/lose/escaped result screen."""
        P = curses.color_pair
        scr.erase()
        if self.result == 'win':
            title = '★ VICTORY ★'
            tcp = P(4)|curses.A_BOLD
        elif self.result == 'lose':
            title = '✖ DEFEATED ✖'
            tcp = P(2)|curses.A_BOLD
        else:
            title = 'You escaped!'
            tcp = P(5)|curses.A_BOLD
        center(scr, H//2-len(msgs)//2-2, title, W, tcp)
        for i, m in enumerate(msgs):
            center(scr, H//2-len(msgs)//2+i, m, W, P(5))
        center(scr, H//2+len(msgs)//2+2, '[ Press SPACE ]', W, P(5))
        scr.refresh()
