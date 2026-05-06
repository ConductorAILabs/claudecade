"""Claudémon battle system."""
import curses, random
from .data   import MOVES, ITEMS
from .entities import ClaudemonInstance

# States
ACT_MENU, ACT_FIGHT, ACT_CATCH, ACT_ITEM, ACT_RUN, \
ANIMATING, LEVEL_UP, WIN, LOSE, ESCAPED, CAUGHT = range(11)

# Type color map for type badges
TYPE_COLORS = {
    'Neural': 1, 'Logic': 8, 'Data': 4, 'Spark': 4,
    'Flow': 8, 'Void': 5, 'Normal': 5,
}

# Ball throw animation frames (shown in enemy zone)
BALL_FRAMES = [
    ["        ", "   ●    ", "        "],
    ["        ", "     ●  ", "        "],
    ["        ", "       ●", "        "],
    ["        ", "      ● ", "        "],
    ["  ╔═╗  ", "  ║●║  ", "  ╚═╝  "],   # ball hits
    ["  ╔═╗  ", "  ║*║  ", "  ╚═╝  "],
    ["  ╔═╗  ", "  ║·║  ", "  ╚═╝  "],
    ["  ╔═╗  ", "  ║ ║  ", "  ╚═╝  "],   # contained
]

FAINT_ART = [
    "   * * *   ",
    "  F A I N T ",
    "   * * *   ",
]

EVOLVE_ART = [
    " ✦ ✦ ✦ ✦ ✦ ",
    "✦ EVOLVING! ✦",
    " ✦ ✦ ✦ ✦ ✦ ",
]


def _p(scr, H, W, r, c, s, a=0):
    try:
        if 0 <= r < H-1 and 0 <= c < W:
            scr.addstr(r, c, s[:max(0, W-c)], a)
    except curses.error:
        pass


def _hp_bar(cur, mx, w=16):
    """Returns (bar_str, color_pair_num)."""
    frac = cur / mx if mx else 0
    filled = max(0, int(w * frac))
    empty  = w - filled
    bar = '█' * filled + '░' * empty
    if frac > 0.5:
        cp = 3   # green
    elif frac > 0.25:
        cp = 4   # yellow
    else:
        cp = 2   # red/pink
    return bar, cp


def _exp_bar(cur, nxt, w=16):
    frac   = cur / nxt if nxt else 0
    filled = max(0, int(w * frac))
    return '▪' * filled + '·' * (w - filled)


def _type_badge(t):
    if not t: return ''
    short = t[:5]
    return f'[{short}]'


class Battle:
    def __init__(self, player_party: list[ClaudemonInstance],
                 wild: ClaudemonInstance | None = None,
                 trainer: 'Trainer | None' = None,
                 items: dict[str, int] | None = None):
        self.party    = player_party
        self.wild     = wild
        self.trainer  = trainer
        self.items    = items or {}
        self.is_wild  = wild is not None

        # Find first alive party member
        self.p_idx    = next((i for i, c in enumerate(self.party) if c.alive), 0)
        self.player   = self.party[self.p_idx]
        self.enemy    = wild if wild else (trainer.active if trainer else None)

        self.state    = ACT_MENU
        self.cursor   = 0
        self.log: list[str] = []
        self.log_idx  = 0
        self.pending_msgs: list[str] = []
        self.level_up_msgs: list[str] = []
        self.caught_name  = ''
        self.result   = None  # 'win','lose','escaped','caught'

        # Catch animation
        self.catch_anim_frame = -1   # -1 = not animating
        self.catch_success    = False

    @property
    def active_enemy(self) -> ClaudemonInstance | None:
        return self.wild or (self.trainer.active if self.trainer else None)

    def _menu_opts(self) -> list[str]:
        opts = ['FIGHT']
        if self.is_wild: opts.append('CATCH')
        opts.append('ITEM')
        if self.is_wild: opts.append('RUN')
        return opts

    def handle_key(self, key: int) -> None:
        UP    = key in (curses.KEY_UP,   ord('w'), ord('k'))
        DOWN  = key in (curses.KEY_DOWN,  ord('s'), ord('j'))
        LEFT  = key in (curses.KEY_LEFT,  ord('a'))
        RIGHT = key in (curses.KEY_RIGHT, ord('d'))
        OK    = key in (ord('\n'), ord(' '), 10, 13, ord('l'))
        BACK  = key in (27, ord('q'), curses.KEY_BACKSPACE)

        # Drain pending messages first
        if self.state == ANIMATING:
            if OK or DOWN:
                if self.pending_msgs:
                    msg = self.pending_msgs.pop(0)
                    self.log.append(msg)
                    if not self.pending_msgs:
                        self.catch_anim_frame = -1
                        self._after_animation()
            return

        if self.state == LEVEL_UP:
            if OK:
                if self.level_up_msgs:
                    self.log.append(self.level_up_msgs.pop(0))
                if not self.level_up_msgs:
                    self._check_end()
            return

        if self.state == ACT_MENU:
            opts = self._menu_opts()
            if UP:   self.cursor = (self.cursor - 1) % len(opts)
            if DOWN: self.cursor = (self.cursor + 1) % len(opts)
            if OK:
                ch = opts[self.cursor]
                if ch == 'FIGHT':
                    self.state  = ACT_FIGHT
                    self.cursor = 0
                elif ch == 'CATCH':
                    self.state  = ACT_CATCH
                    self.cursor = 0
                elif ch == 'ITEM':
                    self.state  = ACT_ITEM
                    self.cursor = 0
                elif ch == 'RUN':
                    self._try_run()

        elif self.state == ACT_FIGHT:
            moves = self.player.moves
            if UP:   self.cursor = (self.cursor - 1) % max(1, len(moves))
            if DOWN: self.cursor = (self.cursor + 1) % max(1, len(moves))
            if LEFT: self.cursor = (self.cursor - 1) % max(1, len(moves))
            if RIGHT:self.cursor = (self.cursor + 1) % max(1, len(moves))
            if BACK: self.state = ACT_MENU; self.cursor = 0; return
            if OK and moves:
                mv = moves[self.cursor]
                if self.player.pp.get(mv, 0) <= 0:
                    self.log.append(f'No PP left for {mv}!')
                    return
                self._do_player_attack(mv)

        elif self.state == ACT_CATCH:
            balls = [(n, c) for n, c in self.items.items()
                     if c > 0 and ITEMS.get(n, {}).get('type') == 'ball']
            if UP or LEFT: self.cursor = (self.cursor - 1) % max(1, len(balls))
            if DOWN or RIGHT: self.cursor = (self.cursor + 1) % max(1, len(balls))
            if BACK: self.state = ACT_MENU; self.cursor = 0; return
            if OK and balls:
                ball_name, _ = balls[self.cursor]
                self._throw_ball(ball_name)

        elif self.state == ACT_ITEM:
            heals = [(n, c) for n, c in self.items.items()
                     if c > 0 and ITEMS.get(n, {}).get('type') in ('heal', 'revive')]
            if UP or LEFT: self.cursor = (self.cursor - 1) % max(1, len(heals))
            if DOWN or RIGHT: self.cursor = (self.cursor + 1) % max(1, len(heals))
            if BACK: self.state = ACT_MENU; self.cursor = 0; return
            if OK and heals:
                item_name, _ = heals[self.cursor]
                self._use_item(item_name)


    def _do_player_attack(self, move_name: str):
        mv = MOVES[move_name]
        self.player.pp[move_name] -= 1
        enemy = self.active_enemy
        msgs = [f'{self.player.name} used {move_name}!']
        if mv.get('power', 0) > 0:
            dmg, mult = self.player.deal_damage(move_name, enemy)
            msgs.append(f'  Dealt {dmg} damage!')
            if mult >= 2.0:
                msgs.append("  ★ It's SUPER EFFECTIVE! ★")
            elif mult == 0.0:
                msgs.append("  It had no effect...")
            elif mult <= 0.5:
                msgs.append("  Not very effective...")
        else:
            stat_msg = self.player.apply_stat_move(move_name, enemy)
            if stat_msg: msgs.append(f'  {stat_msg}')

        # Enemy turn (if alive)
        if enemy and enemy.alive:
            e_move = random.choice([m for m in enemy.moves if enemy.pp.get(m, 0) > 0] or enemy.moves[:1])
            enemy.pp[e_move] = max(0, enemy.pp.get(e_move, 1) - 1)
            msgs.append(f'Foe {enemy.name} used {e_move}!')
            e_mv = MOVES[e_move]
            if e_mv.get('power', 0) > 0:
                dmg, mult = enemy.deal_damage(e_move, self.player)
                msgs.append(f'  Dealt {dmg} damage to {self.player.name}!')
                if mult >= 2.0:
                    msgs.append("  ★ It's SUPER EFFECTIVE! ★")
                elif mult == 0.0:
                    msgs.append("  It had no effect...")
                elif mult <= 0.5:
                    msgs.append("  Not very effective...")
            else:
                stat_msg = enemy.apply_stat_move(e_move, self.player)
                if stat_msg: msgs.append(f'  {stat_msg}')

        self.pending_msgs = msgs
        self.state = ANIMATING

    def _throw_ball(self, ball_name: str):
        self.items[ball_name] -= 1
        if self.items[ball_name] == 0:
            del self.items[ball_name]
        enemy = self.active_enemy
        d     = ITEMS[ball_name]
        chance = enemy.catch_chance(d['catch_mult'])
        msgs  = [f'You threw a {ball_name}!', '  ...', '  ...', '  ...']

        self.catch_anim_frame = 0
        if random.random() < chance:
            msgs.append(f'  Gotcha! {enemy.name} was caught!')
            msgs.append(f'  {enemy.name} was added to your Claudédex!')
            self.caught_name = enemy.name
            self.catch_success = True
            self.pending_msgs = msgs
            self.result = 'caught'
            self.state  = ANIMATING
        else:
            msgs.append(f'  Oh no! {enemy.name} broke free!')
            self.catch_success = False
            # Enemy attacks back
            if enemy.alive and enemy.moves:
                e_move = random.choice(enemy.moves)
                msgs.append(f'Foe {enemy.name} used {e_move}!')
                e_mv = MOVES[e_move]
                if e_mv.get('power', 0) > 0:
                    dmg, _ = enemy.deal_damage(e_move, self.player)
                    msgs.append(f'  Dealt {dmg} damage!')
            self.pending_msgs = msgs
            self.state = ANIMATING

    def _use_item(self, item_name: str):
        self.items[item_name] -= 1
        if self.items[item_name] == 0:
            del self.items[item_name]
        d  = ITEMS[item_name]
        msgs = [f'Used {item_name}!']
        if d['type'] == 'heal':
            amt = min(d['power'], self.player.max_hp - self.player.hp)
            self.player.heal(d['power'])
            msgs.append(f"  {self.player.name} recovered {amt} HP!")
        elif d['type'] == 'revive':
            fainted = [c for c in self.party if not c.alive]
            if fainted:
                fainted[0].hp = fainted[0].max_hp // 2
                msgs.append(f"  {fainted[0].name} was revived!")
        self.pending_msgs = msgs
        self.state = ANIMATING

    def _try_run(self):
        p_spd = self.player.eff_spd()
        e_spd = self.active_enemy.eff_spd() if self.active_enemy else 0
        odds  = (p_spd * 128 // max(1, e_spd)) + 30
        if random.randint(0, 255) < odds:
            self.pending_msgs = ['Got away safely!']
            self.result = 'escaped'
            self.state  = ANIMATING
        else:
            self.pending_msgs = ["Can't escape!", f'Foe {self.active_enemy.name} blocks the way!']
            self.state = ANIMATING

    def _after_animation(self):
        if self.result:
            return
        # Check if enemy fainted
        enemy = self.active_enemy
        if enemy and not enemy.alive:
            msgs = [f'Foe {enemy.name} fainted!']
            exp_msgs = self.player.gain_exp(enemy.data['base_exp'], enemy.level)
            msgs.extend(exp_msgs)
            # Trainer: send next
            if self.trainer:
                nxt = self.trainer.active
                if nxt:
                    msgs.append(f'{self.trainer.name} sent out {nxt.name}!')
                else:
                    msgs.append(f'{self.trainer.name} is out of Claudémon!')
                    self.result = 'win'
            else:
                self.result = 'win'
            self.level_up_msgs = msgs
            self.state = LEVEL_UP
            return
        # Check if player fainted
        if not self.player.alive:
            nxt = next((c for c in self.party if c.alive and c is not self.player), None)
            if nxt:
                self.player = nxt
                self.pending_msgs = [f'{self.player.name}, go!', f'Come on, {self.player.name}!']
                self.state = ANIMATING
            else:
                self.pending_msgs = ['All your Claudémon fainted...']
                self.result = 'lose'
                self.state  = ANIMATING
            return
        self.state  = ACT_MENU
        self.cursor = 0

    def _check_end(self):
        if self.result:
            return
        if not self.active_enemy or not self.active_enemy.alive:
            self.result = 'win'
        elif not any(c.alive for c in self.party):
            self.result = 'lose'
        else:
            self.state  = ACT_MENU
            self.cursor = 0


    def draw(self, scr, H, W, tick):
        P = curses.color_pair
        scr.erase()

        PINK  = P(6) | curses.A_BOLD
        DIM   = P(5) | curses.A_DIM
        BOLD  = P(5) | curses.A_BOLD
        RED   = P(2) | curses.A_BOLD
        YEL   = P(4) | curses.A_BOLD
        GRN   = P(3) | curses.A_BOLD
        CYAN  = P(8) | curses.A_BOLD

        # ── Outer border ──────────────────────────────────────────────────────
        _p(scr, H, W, 0,   0, '╔'+'═'*(W-2)+'╗', BOLD)
        _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', BOLD)
        for r in range(1, H-1):
            _p(scr, H, W, r, 0,   '║', P(5))
            _p(scr, H, W, r, W-1, '║', P(5))

        # ── Title bar ─────────────────────────────────────────────────────────
        title = '★  C L A U D É M O N  B A T T L E  ★'
        _p(scr, H, W, 1, 1, '░'*(W-2), DIM)
        _p(scr, H, W, 1, max(1, (W-len(title))//2), title, PINK)
        _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', BOLD)

        enemy  = self.active_enemy
        mid    = W // 2
        ARENA_TOP = 3
        ARENA_BOT = H - 8   # bottom of arena area

        # ── Vertical divider ──────────────────────────────────────────────────
        for r in range(ARENA_TOP, ARENA_BOT):
            _p(scr, H, W, r, mid, '│', DIM)

        # ══════════════════════════════════════════════════════════════════════
        # ENEMY (top-right quadrant)
        # ══════════════════════════════════════════════════════════════════════
        if enemy:
            # Name + level
            ename = f'{enemy.name}'
            elevel = f'Lv.{enemy.level}'
            _p(scr, H, W, ARENA_TOP,   mid+2, ename,  BOLD)
            _p(scr, H, W, ARENA_TOP,   mid+2+len(ename)+1, elevel, DIM)

            # Type badge
            t1_badge = _type_badge(enemy.type1)
            t2_badge = _type_badge(enemy.type2) if enemy.type2 else ''
            tc1 = P(TYPE_COLORS.get(enemy.type1, 5)) | curses.A_BOLD
            _p(scr, H, W, ARENA_TOP+1, mid+2, t1_badge, tc1)
            if t2_badge:
                tc2 = P(TYPE_COLORS.get(enemy.type2, 5)) | curses.A_BOLD
                _p(scr, H, W, ARENA_TOP+1, mid+2+len(t1_badge)+1, t2_badge, tc2)

            # HP bar
            hp_bar, hp_cp = _hp_bar(enemy.hp, enemy.max_hp, w=min(18, W//2-8))
            _p(scr, H, W, ARENA_TOP+2, mid+2, 'HP', GRN)
            _p(scr, H, W, ARENA_TOP+2, mid+5, hp_bar, P(hp_cp)|curses.A_BOLD)
            _p(scr, H, W, ARENA_TOP+3, mid+5, f'{enemy.hp:>3}/{enemy.max_hp}', DIM)

            # Enemy art — large, top-right (enemy faces left = shown from back)
            if self.catch_anim_frame >= 0 and self.state == ANIMATING:
                # Show catch ball animation
                frame_idx = min(self.catch_anim_frame, len(BALL_FRAMES)-1)
                anim = BALL_FRAMES[frame_idx]
                art_row = ARENA_TOP + 4
                for i, line in enumerate(anim):
                    acol = mid + max(2, (W//2 - len(line)) // 2)
                    _p(scr, H, W, art_row+i, acol, line, CYAN)
                # Advance frame every 6 ticks
                if tick % 6 == 0:
                    self.catch_anim_frame = min(self.catch_anim_frame+1, len(BALL_FRAMES)-1)
            else:
                art = enemy.art if enemy.alive else FAINT_ART
                art_row = ARENA_TOP + 4
                for i, line in enumerate(art):
                    art_col = mid + max(2, (W//2 - len(line)) // 2)
                    faint_attr = DIM if not enemy.alive else (P(2)|curses.A_BOLD)
                    _p(scr, H, W, art_row+i, art_col, line, faint_attr)

        # ══════════════════════════════════════════════════════════════════════
        # PLAYER (bottom-left quadrant)
        # ══════════════════════════════════════════════════════════════════════
        p = self.player

        # Player art — smaller, shown from front (bottom-left)
        art = p.art if p.alive else FAINT_ART
        art_start = ARENA_BOT - len(art) - 1
        for i, line in enumerate(art):
            _p(scr, H, W, art_start+i, 3, line, P(1)|curses.A_BOLD if p.alive else DIM)

        # Player info (top-left quadrant)
        pname  = f'{p.name}'
        plevel = f'Lv.{p.level}'
        _p(scr, H, W, ARENA_TOP,   2, pname,  BOLD)
        _p(scr, H, W, ARENA_TOP,   2+len(pname)+1, plevel, DIM)

        # Type badge
        pt1_badge = _type_badge(p.type1)
        pt2_badge = _type_badge(p.type2) if p.type2 else ''
        ptc1 = P(TYPE_COLORS.get(p.type1, 5)) | curses.A_BOLD
        _p(scr, H, W, ARENA_TOP+1, 2, pt1_badge, ptc1)
        if pt2_badge:
            ptc2 = P(TYPE_COLORS.get(p.type2, 5)) | curses.A_BOLD
            _p(scr, H, W, ARENA_TOP+1, 2+len(pt1_badge)+1, pt2_badge, ptc2)

        # Player HP bar
        php_bar, php_cp = _hp_bar(p.hp, p.max_hp, w=min(18, mid-8))
        _p(scr, H, W, ARENA_TOP+2, 2, 'HP', GRN)
        _p(scr, H, W, ARENA_TOP+2, 5, php_bar, P(php_cp)|curses.A_BOLD)
        _p(scr, H, W, ARENA_TOP+3, 5, f'{p.hp:>3}/{p.max_hp}', DIM)

        # EXP bar
        exp_bar = _exp_bar(p.exp, max(1, p._exp_to_next()), w=min(18, mid-8))
        _p(scr, H, W, ARENA_TOP+4, 2, 'EX', CYAN)
        _p(scr, H, W, ARENA_TOP+4, 5, exp_bar, P(8)|curses.A_DIM)

        # Status indicator
        if p.status:
            status_str = f' [{p.status.upper()}] '
            _p(scr, H, W, ARENA_TOP+5, 2, status_str, RED)

        # ── Message log divider ───────────────────────────────────────────────
        log_y = H - 8
        _p(scr, H, W, log_y, 0, '╠'+'═'*(W-2)+'╣', BOLD)

        # Show last 2 log lines (scrollback)
        visible = self.log[-2:] if len(self.log) >= 2 else self.log
        for i, line in enumerate(visible):
            _p(scr, H, W, log_y+1+i, 2, line[:W-4], P(5))

        # Pending/animating messages
        if self.state == ANIMATING and self.pending_msgs:
            msg = self.pending_msgs[0]
            # Colour super-effective messages
            if 'SUPER EFFECTIVE' in msg:
                attr = YEL
            elif 'not very effective' in msg.lower():
                attr = DIM
            elif 'no effect' in msg.lower():
                attr = DIM
            elif 'fainted' in msg.lower():
                attr = RED
            else:
                attr = BOLD
            _p(scr, H, W, log_y+1, 2, msg[:W-4], attr)
            if len(self.pending_msgs) > 1:
                if (tick // 10) % 2 == 0:
                    _p(scr, H, W, log_y+2, W-5, '▼', DIM)

        if self.state == LEVEL_UP and self.level_up_msgs:
            msg = self.level_up_msgs[0]
            attr = PINK if 'evolved' in msg.lower() else (YEL if 'level' in msg.lower() else BOLD)
            _p(scr, H, W, log_y+1, 2, msg[:W-4], attr)
            if (tick // 10) % 2 == 0:
                _p(scr, H, W, log_y+2, W-5, '▼', DIM)

        # ── Battle menu ───────────────────────────────────────────────────────
        menu_y = H - 5
        _p(scr, H, W, menu_y, 0, '╠'+'═'*(W-2)+'╣', BOLD)

        if self.state == ACT_MENU:
            opts = self._menu_opts()
            # Draw a clean box for the menu
            box_w  = 18
            box_x  = W - box_w - 2
            _p(scr, H, W, menu_y+1, box_x, '╔'+'═'*(box_w-2)+'╗', BOLD)
            _p(scr, H, W, menu_y+2, box_x, '╚'+'═'*(box_w-2)+'╝', BOLD)
            for r in range(1, 2):
                _p(scr, H, W, menu_y+1+r, box_x, '║', P(5))
                _p(scr, H, W, menu_y+1+r, box_x+box_w-1, '║', P(5))

            # 2x2 grid of menu options
            positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
            for i, opt in enumerate(opts[:4]):
                sel  = (i == self.cursor)
                attr = PINK if sel else DIM
                row, col_off = positions[i]
                x = 4 + col_off * ((W - box_w - 8) // 2)
                prefix = '▸ ' if sel else '  '
                _p(scr, H, W, menu_y+1+row, x, f'{prefix}{opt:<10}', attr)

        elif self.state == ACT_FIGHT:
            # Move menu — 2x2 grid
            moves = p.moves
            _p(scr, H, W, menu_y+1, 2, 'Choose a move:', BOLD)
            for i, mv in enumerate(moves):
                pp_left = p.pp.get(mv, 0)
                pp_max  = MOVES[mv]['pp']
                mv_type = MOVES[mv]['type']
                row = menu_y + 2 + (i // 2)
                col = 2 + (i % 2) * ((W - 4) // 2)
                sel  = (i == self.cursor)
                attr = PINK if sel else DIM
                pp_col = GRN if pp_left > pp_max // 2 else (YEL if pp_left > 0 else RED)
                prefix = '▸' if sel else ' '
                mv_str = f'{prefix} {mv:<14} {mv_type:<6}'
                _p(scr, H, W, row, col, mv_str, attr)
                pp_str = f'{pp_left}/{pp_max}'
                _p(scr, H, W, row, col+len(mv_str), pp_str, pp_col if sel else DIM)

        elif self.state == ACT_CATCH:
            balls = [(n, c) for n, c in self.items.items()
                     if c > 0 and ITEMS.get(n, {}).get('type') == 'ball']
            _p(scr, H, W, menu_y+1, 2, 'Choose a ball:', BOLD)
            if not balls:
                _p(scr, H, W, menu_y+2, 4, 'No balls! Visit a shop.', RED)
            else:
                for i, (bn, cnt) in enumerate(balls[:4]):
                    sel  = (i == self.cursor)
                    attr = PINK if sel else DIM
                    col  = 4 + (i % 2) * ((W-4)//2)
                    row  = menu_y+2 + i//2
                    prefix = '▸ ' if sel else '  '
                    _p(scr, H, W, row, col, f'{prefix}({bn}) ×{cnt}', attr)

        elif self.state == ACT_ITEM:
            heals = [(n, c) for n, c in self.items.items()
                     if c > 0 and ITEMS.get(n, {}).get('type') in ('heal','revive')]
            _p(scr, H, W, menu_y+1, 2, 'Choose an item:', BOLD)
            if not heals:
                _p(scr, H, W, menu_y+2, 4, 'No usable items.', RED)
            else:
                for i, (nm, cnt) in enumerate(heals[:4]):
                    sel  = (i == self.cursor)
                    attr = PINK if sel else DIM
                    col  = 4 + (i % 2) * ((W-4)//2)
                    row  = menu_y+2 + i//2
                    prefix = '▸ ' if sel else '  '
                    _p(scr, H, W, row, col, f'{prefix}{nm} ×{cnt}', attr)

        # Controls hint bottom-right
        hint = 'WASD:Navigate  ENTER:Select  Q:Back'
        _p(scr, H, W, H-2, max(1, W-len(hint)-2), hint, DIM)

        scr.refresh()
