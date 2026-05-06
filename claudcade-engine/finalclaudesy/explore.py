"""World map, town, and dungeon exploration."""
import curses, random
from .data    import (WORLD_MAP, MAP_H, MAP_W, WALKABLE, ENCOUNTER_CHANCE,
                      TILE_TOWNS, TILE_DUNGEONS, TOWNS, DUNGEONS, SHOPS,
                      INN_PRICES, ENCOUNTER_GROUPS, STORY, ITEMS, EQUIPMENT,
                      TILE_DISPLAY, STATUS_ICONS)
from .entities import Party, EnemyInstance
from .ui       import safe_add, box, bar, center, menu_list

# Legacy fallback color table (used if tile not in TILE_DISPLAY)
TILE_COLOR = {
    '~': 8, '^': 5, '.': 3, 'T': 3, 'A': 4, 'E': 2, 'C': 6,
    '1': 3, '2': 2, '3': 6,
}

# Town/dungeon label overlay (shown near the tile)
TILE_LABELS = {
    'A': 'Anthropia',
    'E': 'Emberia',
    'C': 'Crystal City',
    '1': 'Thornwood',
    '2': 'Magma Forge',
    '3': 'SYNTHOS Core',
}

class WorldMap:
    def __init__(self, party: Party):
        self.party  = party
        self.x      = party.map_x
        self.y      = party.map_y
        self.result = None   # None | ('town', name) | ('dungeon', name, region) | ('battle', [...])

    def _tile(self, x, y):
        if 0 <= y < MAP_H and 0 <= x < MAP_W:
            return WORLD_MAP[y][x]
        return '~'

    def handle_key(self, key):
        dx, dy = 0, 0
        if key in (curses.KEY_UP,    ord('w')): dy = -1
        if key in (curses.KEY_DOWN,  ord('s')): dy =  1
        if key in (curses.KEY_LEFT,  ord('a')): dx = -1
        if key in (curses.KEY_RIGHT, ord('d')): dx =  1
        if dx == 0 and dy == 0: return

        nx, ny = self.x + dx, self.y + dy
        tile = self._tile(nx, ny)
        if tile not in WALKABLE: return

        self.x, self.y = nx, ny
        self.party.map_x, self.party.map_y = nx, ny

        # Town / dungeon entry
        if tile in TILE_TOWNS:
            self.result = ('town', TILE_TOWNS[tile])
            return
        if tile in TILE_DUNGEONS:
            name, region = TILE_DUNGEONS[tile]
            self.result = ('dungeon', name, region)
            return

        # Random encounter
        enc_chance = ENCOUNTER_CHANCE.get(tile, 0)
        if enc_chance and random.random() < enc_chance:
            region = self._region_at(nx, ny)
            group  = random.choice(ENCOUNTER_GROUPS.get(region, [['Slime']]))
            self.result = ('battle', group, region)

    def _region_at(self, x, y):
        tile = self._tile(x, y)
        if tile in TILE_DUNGEONS: return TILE_DUNGEONS[tile][1]
        if x <= 20:  return 1
        if x <= 46:  return 2
        return 3

    def draw(self, scr, H, W, tick):
        P = curses.color_pair
        scr.erase()

        # viewport centered on player
        vw = W - 2
        vh = H - 7
        vx0 = max(0, min(MAP_W - vw, self.x - vw // 2))
        vy0 = max(0, min(MAP_H - vh, self.y - vh // 2))

        # ── Header ──────────────────────────────────────────────
        safe_add(scr, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
        title_txt = ' ★  F I N A L   C L A U D E S Y  ★   W O R L D   M A P '
        safe_add(scr, 1, 2, title_txt, P(6)|curses.A_BOLD)
        gx = f'✦ {self.party.gold}g ✦'
        safe_add(scr, 1, W-len(gx)-3, gx, P(4)|curses.A_BOLD)
        safe_add(scr, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

        # ── Map viewport ─────────────────────────────────────────
        for vy in range(vh):
            for vx in range(vw):
                mx, my = vx0 + vx, vy0 + vy
                tile   = self._tile(mx, my)

                # Player character
                if mx == self.x and my == self.y:
                    # Animate player sprite: alternate between @ and ✦
                    player_ch = '@' if (tick // 15) % 2 == 0 else '✦'
                    safe_add(scr, 3 + vy, 1 + vx, player_ch, P(1)|curses.A_BOLD)
                    continue

                # Rich tile display
                if tile in TILE_DISPLAY:
                    ch, cp, bold = TILE_DISPLAY[tile]
                    attr = P(cp)
                    if bold: attr |= curses.A_BOLD
                    # Animate water tiles
                    if tile == '~' and (tick // 20 + mx + my) % 3 == 0:
                        ch = '~'
                        attr = P(8)|curses.A_DIM
                    # Animate forest tiles
                    elif tile == 'T' and (tick // 30 + mx * 3) % 7 == 0:
                        ch = '❧'
                        attr = P(3)|curses.A_BOLD
                else:
                    ch   = tile
                    attr = P(TILE_COLOR.get(tile, 5))

                safe_add(scr, 3 + vy, 1 + vx, ch, attr)

        # ── Mini-legend ───────────────────────────────────────────
        legend_y = 3
        legend_x = W - 18
        safe_add(scr, legend_y,   legend_x, '┌── LEGEND ───┐', P(5)|curses.A_DIM)
        safe_add(scr, legend_y+1, legend_x, '│ @ You       │', P(1))
        safe_add(scr, legend_y+2, legend_x, '│ ▣ Town      │', P(4))
        safe_add(scr, legend_y+3, legend_x, '│ ╬ Dungeon   │', P(2))
        safe_add(scr, legend_y+4, legend_x, '│ ♣ Forest    │', P(3))
        safe_add(scr, legend_y+5, legend_x, '│ ▲ Mountain  │', P(5))
        safe_add(scr, legend_y+6, legend_x, '│ ≈ Water     │', P(8))
        safe_add(scr, legend_y+7, legend_x, '└─────────────┘', P(5)|curses.A_DIM)

        # ── Party HUD ────────────────────────────────────────────
        hud_y = H - 5
        safe_add(scr, hud_y, 0, '╠' + '═'*(W-2) + '╣', P(5))
        col_w = W // 3
        for i, m in enumerate(self.party.members):
            mx = 2 + i * col_w
            alive_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)|curses.A_DIM
            tag = '✝KO' if not m.alive else ('▶' if i == 0 else ' ')
            safe_add(scr, hud_y+1, mx, f'{tag} {m.name} Lv{m.level} [{m.cls}]', alive_attr)
            # HP bar
            hp_cp = 3 if m.hp > m.max_hp*0.5 else (4 if m.hp > m.max_hp*0.25 else 2)
            safe_add(scr, hud_y+2, mx, 'HP', P(hp_cp)|curses.A_BOLD)
            bar(scr, hud_y+2, mx+3, m.hp, m.max_hp, 10, hp_cp)
            safe_add(scr, hud_y+2, mx+14, f'{m.hp}/{m.max_hp}', P(5))
            # MP bar
            safe_add(scr, hud_y+3, mx, 'MP', P(8)|curses.A_BOLD)
            bar(scr, hud_y+3, mx+3, m.mp, m.max_mp, 10, 8)
            safe_add(scr, hud_y+3, mx+14, f'{m.mp}/{m.max_mp}', P(5))

        safe_add(scr, H-1, 0, '╚' + '═'*(W-2) + '╝', P(5))
        ctrl = 'WASD:Move  ▣:Town  ╬:Dungeon  M:Menu/Save'
        safe_add(scr, H-1, (W-len(ctrl))//2, ctrl, P(5)|curses.A_DIM)
        scr.refresh()


class TownScreen:
    MAIN_OPTS = ['Talk to NPCs', 'Shop', 'Inn', 'Leave']

    def __init__(self, party: Party, town_name: str):
        self.party   = party
        self.name    = town_name
        self.data    = TOWNS[town_name]
        self.result  = None   # None | 'leave' | ('battle', [...], region)
        self._state  = 'MAIN'
        self._cursor = 0
        self._npc_idx= 0
        self._npc_line = 0
        self._shop_state  = 'CATEGORY'
        self._shop_cat    = 0
        self._shop_cursor = 0
        self._shop_cats   = ['Items','Weapons','Armor','Accessories','Sell','Done']
        self._shop_items  : list[str] = []
        self._msg         = ''
        self._msg_timer   = 0

    def handle_key(self, key):
        UP   = key in (curses.KEY_UP,   ord('w'), ord('k'))
        DOWN = key in (curses.KEY_DOWN,  ord('s'), ord('j'))
        OK   = key in (ord('\n'), ord(' '), ord('l'))
        BACK = key in (27, ord('q'), curses.KEY_BACKSPACE)

        if self._state == 'MAIN':
            if UP:   self._cursor = (self._cursor-1) % len(self.MAIN_OPTS)
            if DOWN: self._cursor = (self._cursor+1) % len(self.MAIN_OPTS)
            if OK:
                choice = self.MAIN_OPTS[self._cursor]
                if choice == 'Leave':    self.result = 'leave'
                elif choice == 'Talk to NPCs':
                    self._state   = 'NPC'
                    self._npc_idx = 0; self._npc_line = 0
                elif choice == 'Shop':
                    self._state   = 'SHOP'
                    self._shop_state  = 'CATEGORY'
                    self._shop_cat    = 0
                elif choice == 'Inn':
                    cost = INN_PRICES.get(self.name, 100)
                    if self.party.gold >= cost:
                        self.party.gold -= cost
                        self.party.inn_rest()
                        self._show(f'Rested! -{cost} gold. Party fully healed.')
                    else:
                        self._show(f'Need {cost} gold. (Have {self.party.gold})')
            if BACK: self.result = 'leave'

        elif self._state == 'NPC':
            npcs  = self.data['npcs']
            npc   = npcs[self._npc_idx]
            lines = npc['lines']
            if OK or DOWN:
                self._npc_line += 1
                if self._npc_line >= len(lines):
                    self._npc_idx = (self._npc_idx + 1) % len(npcs)
                    self._npc_line = 0
            if BACK or (UP and self._npc_line == 0):
                self._state = 'MAIN'

        elif self._state == 'SHOP':
            self._handle_shop(key, UP, DOWN, OK, BACK)

    def _handle_shop(self, key, UP, DOWN, OK, BACK):
        shop = SHOPS.get(self.name, {})
        if self._shop_state == 'CATEGORY':
            if UP:   self._shop_cat = (self._shop_cat-1) % len(self._shop_cats)
            if DOWN: self._shop_cat = (self._shop_cat+1) % len(self._shop_cats)
            if BACK: self._state = 'MAIN'; return
            if OK:
                cat = self._shop_cats[self._shop_cat]
                if cat == 'Done': self._state = 'MAIN'
                elif cat == 'Sell':
                    self._shop_state  = 'SELL'
                    self._shop_cursor = 0
                    self._shop_items  = [(n,c) for n,c in self.party.items.items()]
                else:
                    key_map = {'Items':'items','Weapons':'weapons','Armor':'armor','Accessories':'acc'}
                    self._shop_items  = shop.get(key_map[cat], [])
                    self._shop_state  = 'BUY'
                    self._shop_cursor = 0

        elif self._shop_state == 'BUY':
            if UP:   self._shop_cursor = (self._shop_cursor-1) % max(1,len(self._shop_items))
            if DOWN: self._shop_cursor = (self._shop_cursor+1) % max(1,len(self._shop_items))
            if BACK: self._shop_state = 'CATEGORY'; return
            if OK and self._shop_items:
                item = self._shop_items[self._shop_cursor]
                from .data import ITEMS, EQUIPMENT
                d = ITEMS.get(item) or EQUIPMENT.get(item)
                if d:
                    price = d.get('price', 0)
                    if self.party.gold >= price:
                        self.party.gold -= price
                        self.party.add_item(item)
                        self._show(f'Bought {item} for {price}g!')
                    else:
                        self._show(f'Need {price}g. (Have {self.party.gold}g)')

        elif self._shop_state == 'SELL':
            inv = [(n,c) for n,c in self.party.items.items()]
            if UP:   self._shop_cursor = (self._shop_cursor-1) % max(1,len(inv))
            if DOWN: self._shop_cursor = (self._shop_cursor+1) % max(1,len(inv))
            if BACK: self._shop_state = 'CATEGORY'; return
            if OK and inv:
                item, cnt = inv[min(self._shop_cursor, len(inv)-1)]
                from .data import ITEMS
                d = ITEMS.get(item, {})
                sell_price = d.get('price', 10) // 2
                self.party.remove_item(item)
                self.party.gold += sell_price
                self._show(f'Sold {item} for {sell_price}g!')

    def _show(self, msg, duration=90):
        self._msg = msg; self._msg_timer = duration

    def draw(self, scr, H, W, tick):
        P = curses.color_pair
        scr.erase()

        # Town-specific color (Emberia = red, Crystal City = cyan, Anthropia = yellow)
        town_cp = {'Anthropia': 4, 'Emberia': 2, 'Crystal City': 6}.get(self.name, 4)
        box(scr, 0, 0, H, W, '', town_cp)

        # Header banner
        town_icons = {'Anthropia': '▣', 'Emberia': '✦', 'Crystal City': '◈'}
        icon = town_icons.get(self.name, '★')
        header = f'  {icon}  {self.name.upper()}  {icon}  '
        center(scr, 1, header, W, P(town_cp)|curses.A_BOLD)
        safe_add(scr, 2, 2, self.data['desc'], P(5)|curses.A_DIM)
        safe_add(scr, 3, 0, '╠' + '═'*(W-2) + '╣', P(town_cp))

        # Flash message
        if self._msg_timer > 0:
            self._msg_timer -= 1
            msg_box_w = min(len(self._msg)+6, W-4)
            box(scr, 4, (W-msg_box_w)//2, 3, msg_box_w, '', town_cp)
            center(scr, 5, self._msg[:W-4], W, P(town_cp)|curses.A_BOLD)

        if self._state == 'MAIN':
            # Stylish main menu
            menu_y, menu_x, menu_w = 7, 3, 26
            box(scr, menu_y, menu_x, len(self.MAIN_OPTS)+2, menu_w, ' Options ', town_cp)
            opt_icons = {'Talk to NPCs': '>', 'Shop': '◈', 'Inn': '♥', 'Leave': '→'}
            for i, opt in enumerate(self.MAIN_OPTS):
                sel  = i == self._cursor
                icon_ch = opt_icons.get(opt, '·')
                label = f'  {icon_ch} {opt}'
                attr  = P(7)|curses.A_BOLD if sel else P(town_cp)
                safe_add(scr, menu_y+1+i, menu_x+2, label.ljust(menu_w-4)[:menu_w-4], attr)

        elif self._state == 'NPC':
            npcs  = self.data['npcs']
            npc   = npcs[self._npc_idx]
            lines = npc['lines']
            # NPC portrait-style box
            npc_y = 6
            npc_w = W - 6
            box(scr, npc_y, 2, 7, npc_w, '', 1)
            # Name tag
            name_tag = f'┤ {npc["name"]} ├'
            safe_add(scr, npc_y, 4, name_tag, P(1)|curses.A_BOLD)
            # Speaker icon
            safe_add(scr, npc_y+1, 4, '  ╭───╮', P(1)|curses.A_DIM)
            safe_add(scr, npc_y+2, 4, '  │ ◉ │', P(1))
            safe_add(scr, npc_y+3, 4, '  ╰───╯', P(1)|curses.A_DIM)
            # Dialogue line
            line = lines[min(self._npc_line, len(lines)-1)]
            # Word-wrap long lines
            max_line_w = npc_w - 16
            safe_add(scr, npc_y+2, 14, f'"{line[:max_line_w]}"', P(5))
            if len(line) > max_line_w:
                safe_add(scr, npc_y+3, 14, f' {line[max_line_w:max_line_w*2]}"', P(5))
            # Progress indicator
            pg = f'[{self._npc_line+1}/{len(lines)}]  SPACE:next  Q:done'
            safe_add(scr, npc_y+5, 4, pg, P(5)|curses.A_DIM)

        elif self._state == 'SHOP':
            self._draw_shop(scr, H, W)

        # ── Party HUD ────────────────────────────────────────────
        status_y = H - 5
        safe_add(scr, status_y, 0, '╠' + '═'*(W-2) + '╣', P(5))
        col_w = W // 3
        for i, m in enumerate(self.party.members):
            mx2 = 2 + i * col_w
            alive_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)|curses.A_DIM
            safe_add(scr, status_y+1, mx2, f'{m.name} Lv{m.level}', alive_attr)
            hp_cp = 3 if m.hp > m.max_hp*0.5 else (4 if m.hp > m.max_hp*0.25 else 2)
            safe_add(scr, status_y+2, mx2, 'HP', P(hp_cp)|curses.A_BOLD)
            bar(scr, status_y+2, mx2+3, m.hp, m.max_hp, 8, hp_cp)
            safe_add(scr, status_y+3, mx2, 'MP', P(8)|curses.A_BOLD)
            bar(scr, status_y+3, mx2+3, m.mp, m.max_mp, 8, 8)
        gold_str = f'✦ Gold: {self.party.gold}g ✦'
        safe_add(scr, status_y+1, W-len(gold_str)-3, gold_str, P(4)|curses.A_BOLD)
        safe_add(scr, H-1, 0, '╚' + '═'*(W-2) + '╝', P(5))
        scr.refresh()

    def _draw_shop(self, scr, H, W):
        P = curses.color_pair
        shop = SHOPS.get(self.name, {})

        # Shop header
        shop_title = '◈  S H O P  ◈'
        safe_add(scr, 6, 2, shop_title, P(4)|curses.A_BOLD)
        gold_str = f'✦ {self.party.gold}g'
        safe_add(scr, 6, W-len(gold_str)-4, gold_str, P(4)|curses.A_BOLD)

        # Category column
        cat_x, cat_y, cat_w = 2, 7, 20
        box(scr, cat_y, cat_x, len(self._shop_cats)+2, cat_w, ' Category ', 4)
        cat_icons = {'Items':'◈','Weapons':'⚔','Armor':'◇','Accessories':'✦','Sell':'←','Done':'✕'}
        for i, cat in enumerate(self._shop_cats):
            sel  = (self._shop_state == 'CATEGORY') and (i == self._shop_cat)
            icon = cat_icons.get(cat, '·')
            label = f' {icon} {cat}'
            attr  = P(7)|curses.A_BOLD if sel else P(4)
            safe_add(scr, cat_y+1+i, cat_x+2, label.ljust(cat_w-4)[:cat_w-4], attr)

        if self._shop_state == 'BUY' and self._shop_items:
            from .data import ITEMS, EQUIPMENT
            list_y = cat_y
            list_x = cat_x + cat_w + 2
            list_w = W - list_x - 3
            n_show = min(len(self._shop_items), H - list_y - 6)
            box(scr, list_y, list_x, n_show+2, list_w, ' Buy ', 4)
            for i, item in enumerate(self._shop_items[:n_show]):
                d     = ITEMS.get(item) or EQUIPMENT.get(item, {})
                price = d.get('price', 0)
                desc  = d.get('desc', '')
                can   = self.party.gold >= price
                sel   = i == self._shop_cursor
                arrow = '▶' if sel else ' '
                cost_str = f'{price:>5}g'
                label = f' {arrow} {item:<20} {cost_str}  {desc}'
                if sel:
                    attr = P(7)|curses.A_BOLD
                elif not can:
                    attr = P(5)|curses.A_DIM
                else:
                    attr = P(5)
                safe_add(scr, list_y+1+i, list_x+1, label[:list_w-2], attr)

        elif self._shop_state == 'SELL':
            inv    = [(n,c) for n,c in self.party.items.items()]
            list_y = cat_y
            list_x = cat_x + cat_w + 2
            list_w = W - list_x - 3
            n_show = min(len(inv), H - list_y - 6)
            box(scr, list_y, list_x, max(n_show, 1)+2, list_w, ' Sell (half price) ', 4)
            from .data import ITEMS
            for i, (name, cnt) in enumerate(inv[:n_show]):
                d    = ITEMS.get(name, {})
                sell = d.get('price', 10) // 2
                sel  = i == self._shop_cursor
                arrow = '▶' if sel else ' '
                label = f' {arrow} {name:<20} ×{cnt:<3}  → {sell}g'
                attr  = P(7)|curses.A_BOLD if sel else P(4)
                safe_add(scr, list_y+1+i, list_x+1, label[:list_w-2], attr)


class DungeonScreen:
    def __init__(self, party: Party, dungeon_name: str):
        self.party  = party
        self.dname  = dungeon_name
        self.data   = DUNGEONS[dungeon_name]
        self.region = self.data['region']
        self.dmap   = self.data['map']
        self.chests_opened: set = set()
        self.result = None   # None | 'exit' | ('battle', [...], int) | ('boss', str)
        self.log    = [self.data['intro']]
        self._find_start()

    def _find_start(self):
        for r, row in enumerate(self.dmap):
            for c, ch in enumerate(row):
                if ch == 'S': self.px, self.py = c, r; return
        self.px, self.py = 1, 1

    def _tile(self, x, y):
        if 0 <= y < len(self.dmap) and 0 <= x < len(self.dmap[y]):
            return self.dmap[y][x]
        return '#'

    def handle_key(self, key):
        dx, dy = 0, 0
        if key in (curses.KEY_UP,    ord('w')): dy = -1
        if key in (curses.KEY_DOWN,  ord('s')): dy =  1
        if key in (curses.KEY_LEFT,  ord('a')): dx = -1
        if key in (curses.KEY_RIGHT, ord('d')): dx =  1
        if key in (27, ord('q')): self.result = 'exit'; return
        if dx == 0 and dy == 0: return

        nx, ny = self.px + dx, self.py + dy
        tile = self._tile(nx, ny)

        if tile == '#': return
        if tile == 'B':
            if self.dname in self.party.dungeon_done:
                self.log = ['Boss already defeated. Exit to continue.']
                return
            self.result = ('boss', self.data['boss'])
            return

        # Chest
        if tile == 'C':
            pos = (nx, ny)
            if pos not in self.chests_opened:
                self.chests_opened.add(pos)
                chest = self.data['chests'].get(pos)
                if chest:
                    item, qty = chest
                    self.party.add_item(item, qty)
                    self.log = [f'Found a chest! Got {qty}x {item}!']
                else:
                    self.log = ['Empty chest.']
            else:
                self.log = ['Already opened.']

        self.px, self.py = nx, ny

        # Random encounter (dungeon floor tiles)
        if tile in '.CS' and random.random() < 0.08:
            group  = random.choice(ENCOUNTER_GROUPS.get(self.region, [['Slime']]))
            self.result = ('battle', group, self.region)

    def draw(self, scr, H, W, tick):
        P = curses.color_pair
        scr.erase()

        # Dungeon-specific styling
        dun_cp = {'Thornwood Cave': 3, 'Magma Forge': 2, 'SYNTHOS Core': 6}.get(self.dname, 5)
        box(scr, 0, 0, H, W, '', dun_cp)

        # Header
        dun_icons = {'Thornwood Cave': '♣', 'Magma Forge': '✦', 'SYNTHOS Core': '◈'}
        icon = dun_icons.get(self.dname, '╬')
        header = f'  {icon}  {self.dname.upper()}  {icon}  '
        center(scr, 1, header, W, P(dun_cp)|curses.A_BOLD)
        safe_add(scr, 2, 0, '╠' + '═'*(W-2) + '╣', P(dun_cp))

        dh = len(self.dmap)
        dw = len(self.dmap[0]) if dh else 0
        scale = 2   # each tile is 2 chars wide
        map_render_h = H - 10
        map_render_w = W - 4
        off_x = max(2, (W  - dw * scale) // 2)
        off_y = max(3, (map_render_h - dh) // 2 + 3)

        # Viewport clamping for large dungeons
        vx0 = max(0, min(dw - map_render_w // scale, self.px - map_render_w // scale // 2))
        vy0 = max(0, min(dh - map_render_h, self.py - map_render_h // 2))

        for r, row in enumerate(self.dmap):
            for c, ch in enumerate(row):
                vr = r - vy0
                vc = c - vx0
                sx = off_x + vc * scale
                sy = off_y + vr
                if sy < 3 or sy >= H-7 or sx < 2 or sx >= W-2: continue

                if c == self.px and r == self.py:
                    # Animated player
                    player_ch = '@' if (tick // 15) % 2 == 0 else '✦'
                    safe_add(scr, sy, sx, f'{player_ch} ', P(1)|curses.A_BOLD)
                    continue

                pos = (c, r)
                if ch == '#':
                    # Wall style per dungeon
                    wall_chars = {'Thornwood Cave': '██', 'Magma Forge': '▓▓', 'SYNTHOS Core': '╬╬'}
                    wall_str = wall_chars.get(self.dname, '██')
                    safe_add(scr, sy, sx, wall_str, P(dun_cp)|curses.A_DIM)
                elif ch == '.':
                    floor_chars = {'Thornwood Cave': '··', 'Magma Forge': '░░', 'SYNTHOS Core': '──'}
                    floor_str = floor_chars.get(self.dname, '  ')
                    safe_add(scr, sy, sx, floor_str, P(5)|curses.A_DIM)
                elif ch == 'S':
                    safe_add(scr, sy, sx, '▲ ', P(3)|curses.A_BOLD)
                elif ch == 'B':
                    if self.dname in self.party.dungeon_done:
                        safe_add(scr, sy, sx, '╬ ', P(5)|curses.A_DIM)
                    else:
                        attr = P(dun_cp)|curses.A_BOLD
                        boss_ch = ('★ ' if (tick//8)%2==0 else '✦ ')
                        safe_add(scr, sy, sx, boss_ch, attr)
                elif ch == 'C':
                    if pos in self.chests_opened:
                        safe_add(scr, sy, sx, '□ ', P(5)|curses.A_DIM)
                    else:
                        chest_ch = '◈ ' if (tick // 20) % 2 == 0 else '■ '
                        safe_add(scr, sy, sx, chest_ch, P(4)|curses.A_BOLD)

        # ── Event log ─────────────────────────────────────────
        log_y = H - 7
        safe_add(scr, log_y, 0, '╠' + '═'*(W-2) + '╣', P(dun_cp))
        for i, line in enumerate(self.log[-2:]):
            lattr = P(4)|curses.A_BOLD if 'Found' in line or 'chest' in line.lower() else P(5)
            safe_add(scr, log_y+1+i, 2, line[:W-4], lattr)

        # ── Party HUD ─────────────────────────────────────────
        hud_y = H - 4
        safe_add(scr, hud_y, 0, '╠' + '═'*(W-2) + '╣', P(5))
        col_w = W // 3
        for i, m in enumerate(self.party.members):
            mx = 2 + i * col_w
            alive_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)|curses.A_DIM
            ko = ' ✝' if not m.alive else ''
            safe_add(scr, hud_y+1, mx, f'{m.name}{ko} HP:{m.hp}/{m.max_hp}', alive_attr)

        ctrl = 'WASD:Move  ◈=Chest  ★=Boss  Q:Exit dungeon'
        safe_add(scr, H-2, (W-len(ctrl))//2, ctrl, P(5)|curses.A_DIM)
        safe_add(scr, H-1, 0, '╚'+'═'*(W-2)+'╝', P(dun_cp))
        scr.refresh()


class PartyMenu:
    TABS = ['Status','Equipment','Items','Save','Close']

    def __init__(self, party: Party):
        self.party   = party
        self.result  = None   # None | 'close'
        self._tab    = 0
        self._cursor = 0
        self._sub    = 0
        self._msg    = ''
        self._msg_t  = 0
        self._equip_char  = 0
        self._equip_slot  = 0
        self._equip_state = 'CHAR'
        self._item_state  = 'ITEM'
        self._item_cursor = 0
        self._item_target = 0

    def handle_key(self, key):
        UP   = key in (curses.KEY_UP,   ord('w'), ord('k'))
        DOWN = key in (curses.KEY_DOWN,  ord('s'), ord('j'))
        LEFT = key in (curses.KEY_LEFT,  ord('a'))
        RIGHT= key in (curses.KEY_RIGHT, ord('d'))
        OK   = key in (ord('\n'), ord(' '), ord('l'))
        BACK = key in (27, ord('q'), curses.KEY_BACKSPACE)

        if BACK and self._tab_top_level(): self.result = 'close'; return

        # Tab navigation
        if LEFT:  self._tab = (self._tab-1) % len(self.TABS)
        if RIGHT: self._tab = (self._tab+1) % len(self.TABS)

        tab = self.TABS[self._tab]

        if tab == 'Close':
            self.result = 'close'; return

        if tab == 'Status':
            if UP:   self._cursor = (self._cursor-1) % 3
            if DOWN: self._cursor = (self._cursor+1) % 3
            return

        if tab == 'Equipment':
            self._handle_equip(UP, DOWN, OK, BACK)

        if tab == 'Items':
            self._handle_items(UP, DOWN, OK, BACK)

        if tab == 'Save':
            if OK: self._do_save()

    def _tab_top_level(self): return True

    def _handle_equip(self, UP, DOWN, OK, BACK):
        from .data import EQUIPMENT
        chars = self.party.members

        if self._equip_state == 'CHAR':
            if UP:   self._equip_char = (self._equip_char-1) % 3
            if DOWN: self._equip_char = (self._equip_char+1) % 3
            if OK:   self._equip_state = 'EQUIP_CHOOSE'; self._equip_slot = 0
            if BACK: self.result = 'close'

        elif self._equip_state == 'EQUIP_CHOOSE':
            slots = ['Weapon','Armor','Accessory']
            if UP:   self._equip_slot = (self._equip_slot-1) % len(slots)
            if DOWN: self._equip_slot = (self._equip_slot+1) % len(slots)
            if BACK: self._equip_state = 'CHAR'
            if OK:
                self._equip_state  = 'ITEM_LIST'
                self._cursor       = 0
                char = chars[self._equip_char]
                slot_name = ['weapon','armor','acc'][self._equip_slot]
                self._equip_items = [
                    n for n,d in EQUIPMENT.items()
                    if d['slot'] == slot_name and char.can_equip(n)
                ] + ['[Remove]']

        elif self._equip_state == 'ITEM_LIST':
            items = self._equip_items
            if UP:   self._cursor = (self._cursor-1) % len(items)
            if DOWN: self._cursor = (self._cursor+1) % len(items)
            if BACK: self._equip_state = 'EQUIP_CHOOSE'
            if OK:
                char = chars[self._equip_char]
                choice = items[self._cursor]
                if choice == '[Remove]':
                    slot_name = ['weapon','armor','acc'][self._equip_slot]
                    if slot_name == 'weapon': char.weapon = None
                    elif slot_name == 'armor': char.armor = None
                    elif slot_name == 'acc':   char.acc   = None
                    self._msg = 'Unequipped.'; self._msg_t = 60
                else:
                    if char.equip(choice):
                        self._msg = f'Equipped {choice}!'; self._msg_t = 60
                    else:
                        self._msg = f'Cannot equip!'; self._msg_t = 60

    def _handle_items(self, UP, DOWN, OK, BACK):
        avail = [(n,c) for n,c in self.party.items.items()]
        if self._item_state == 'ITEM':
            if UP:   self._item_cursor = (self._item_cursor-1) % max(1,len(avail))
            if DOWN: self._item_cursor = (self._item_cursor+1) % max(1,len(avail))
            if BACK: self.result = 'close'
            if OK and avail:
                self._item_state = 'TARGET'; self._item_target = 0
        elif self._item_state == 'TARGET':
            if UP:   self._item_target = (self._item_target-1) % 3
            if DOWN: self._item_target = (self._item_target+1) % 3
            if BACK: self._item_state = 'ITEM'
            if OK:
                avail = [(n,c) for n,c in self.party.items.items()]
                if avail:
                    item = avail[min(self._item_cursor, len(avail)-1)][0]
                    target = self.party.members[self._item_target]
                    msg = self.party.use_item(item, target)
                    self._msg = msg; self._msg_t = 90
                self._item_state = 'ITEM'

    def _do_save(self):
        import json, os
        path = os.path.expanduser('~/finalclaudesy_save.json')
        with open(path, 'w') as f:
            json.dump(self.party.save_dict(), f, indent=2)
        self._msg = f'Saved to {path}'; self._msg_t = 90

    def draw(self, scr, H, W, tick):
        P = curses.color_pair
        scr.erase()
        box(scr, 0, 0, H, W, '', 5)

        # Title bar
        title = '  ✦  P A R T Y   M E N U  ✦  '
        center(scr, 1, title, W, P(6)|curses.A_BOLD)

        # Tab bar with boxes
        tx = 2
        tab_icons = {'Status': '◈', 'Equipment': '⚔', 'Items': '◈', 'Save': '✦', 'Close': '✕'}
        for i, tab in enumerate(self.TABS):
            icon = tab_icons.get(tab, '·')
            lbl  = f' {icon} {tab} '
            attr = P(7)|curses.A_BOLD if i == self._tab else P(5)
            safe_add(scr, 2, tx, lbl, attr)
            tx += len(lbl) + 1

        safe_add(scr, 3, 0, '╠' + '═'*(W-2) + '╣', P(5))

        if self._msg_t > 0:
            self._msg_t -= 1
            center(scr, 4, f'  {self._msg[:W-6]}  ', W, P(4)|curses.A_BOLD)

        gold_str = f'✦ {self.party.gold}g'
        safe_add(scr, 4, W-len(gold_str)-3, gold_str, P(4)|curses.A_BOLD)

        tab = self.TABS[self._tab]

        if tab == 'Status':
            self._draw_status(scr, H, W)
        elif tab == 'Equipment':
            self._draw_equip(scr, H, W)
        elif tab == 'Items':
            self._draw_items(scr, H, W)
        elif tab == 'Save':
            box(scr, H//2-3, W//4, 6, W//2, '', 4)
            center(scr, H//2-1, '✦  S A V E   G A M E  ✦', W, P(4)|curses.A_BOLD)
            center(scr, H//2,   'Press ENTER to save your progress.', W, P(5))
            center(scr, H//2+1, f'Save file: ~/finalclaudesy_save.json', W, P(5)|curses.A_DIM)

        safe_add(scr, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5))
        scr.refresh()

    def _draw_status(self, scr, H, W):
        P = curses.color_pair
        m = self.party.members[self._cursor]

        # Party selector column
        party_x, party_y = 2, 5
        box(scr, party_y, party_x, len(self.party.members)+2, 22, ' Party ', 5)
        for i, mm in enumerate(self.party.members):
            sel  = i == self._cursor
            attr = P(7)|curses.A_BOLD if sel else P(mm.color)
            arrow = '▶' if sel else ' '
            ko = ' ✝' if not mm.alive else ''
            safe_add(scr, party_y+1+i, party_x+2,
                     f'{arrow} {mm.name:<8} Lv{mm.level:>2}{ko}', attr)

        # Stats panel box
        bx = 26
        sw = W - bx - 3
        box(scr, party_y, bx, H - party_y - 2, sw, '', m.color)

        # Character header
        cls_icons = {'Knight': '⚔', 'Mage': '✦', 'Healer': '†'}
        cls_icon = cls_icons.get(m.cls, '·')
        safe_add(scr, party_y+1, bx+2,
                 f'{cls_icon}  {m.name}  the {m.cls}',
                 P(m.color)|curses.A_BOLD)

        # Level & EXP
        exp_pct = int(100 * m.exp / max(1, m.exp_to_next()))
        safe_add(scr, party_y+2, bx+2,
                 f'Lv {m.level}   EXP {m.exp}/{m.exp_to_next()} ({exp_pct}%)',
                 P(5))

        # HP and MP bars
        bar_w = min(20, sw - 20)
        safe_add(scr, party_y+4, bx+2, 'HP', P(3)|curses.A_BOLD)
        hp_cp = 3 if m.hp > m.max_hp*0.5 else (4 if m.hp > m.max_hp*0.25 else 2)
        bar(scr, party_y+4, bx+5, m.hp, m.max_hp, bar_w, hp_cp)
        safe_add(scr, party_y+4, bx+6+bar_w, f'{m.hp}/{m.max_hp}', P(5))

        safe_add(scr, party_y+5, bx+2, 'MP', P(8)|curses.A_BOLD)
        bar(scr, party_y+5, bx+5, m.mp, m.max_mp, bar_w, 8)
        safe_add(scr, party_y+5, bx+6+bar_w, f'{m.mp}/{m.max_mp}', P(5))

        # Combat stats grid
        safe_add(scr, party_y+7,  bx+2, f'ATK  {m.atk:<6}  DEF  {m.defense:<6}', P(5))
        safe_add(scr, party_y+8,  bx+2, f'MAG  {m.mag:<6}  SPD  {m.spd:<6}', P(5))

        # Equipment
        safe_add(scr, party_y+10, bx+2, f'⚔  Weapon :  {m.weapon or "─ None ─"}', P(5))
        safe_add(scr, party_y+11, bx+2, f'◇  Armor  :  {m.armor  or "─ None ─"}', P(5))
        safe_add(scr, party_y+12, bx+2, f'✦  Acc    :  {m.acc    or "─ None ─"}', P(5))

        # Status effects
        if m.status:
            stags = []
            for k in m.status:
                icon = STATUS_ICONS.get(k, k[:3].upper())
                stags.append(f'{icon} {k}({m.status[k]}t)')
            safe_add(scr, party_y+14, bx+2, 'Status: ' + '  '.join(stags), P(6)|curses.A_BOLD)

        # Spells list
        if m.spells:
            safe_add(scr, party_y+16, bx+2, 'Spells:', P(6)|curses.A_BOLD)
            spell_str = '  '.join(m.spells)
            safe_add(scr, party_y+17, bx+4, spell_str[:sw-6], P(6))

    def _draw_equip(self, scr, H, W):
        P = curses.color_pair
        from .data import EQUIPMENT
        chars = self.party.members

        # Character column
        char_x, char_y = 2, 5
        box(scr, char_y, char_x, len(chars)+2, 22, ' Character ', 5)
        for i, m in enumerate(chars):
            sel  = i == self._equip_char
            attr = P(7)|curses.A_BOLD if sel else P(m.color)
            arrow = '▶' if sel else ' '
            safe_add(scr, char_y+1+i, char_x+2,
                     f'{arrow} {m.name:<10} [{m.cls[:3]}]', attr)

        # Slot column
        if self._equip_state in ('EQUIP_CHOOSE', 'ITEM_LIST'):
            char = chars[self._equip_char]
            slots = ['Weapon','Armor','Accessory']
            slot_x = char_x + 24
            box(scr, char_y, slot_x, len(slots)+2, 20, ' Slot ', 5)
            slot_icons = {'Weapon': '⚔', 'Armor': '◇', 'Accessory': '✦'}
            for i, sl in enumerate(slots):
                sel  = i == self._equip_slot
                attr = P(7)|curses.A_BOLD if sel else P(5)
                icon = slot_icons.get(sl, '·')
                safe_add(scr, char_y+1+i, slot_x+2,
                         f' {icon} {sl}', attr)

            # Currently equipped in each slot
            curr_x = slot_x + 22
            box(scr, char_y, curr_x, len(slots)+2, W-curr_x-3, ' Currently Equipped ', 5)
            curr_items = [char.weapon or '─', char.armor or '─', char.acc or '─']
            for i, ci in enumerate(curr_items):
                safe_add(scr, char_y+1+i, curr_x+2, ci, P(5)|curses.A_DIM)

        # Equipment item list
        if self._equip_state == 'ITEM_LIST':
            items = getattr(self, '_equip_items', [])
            char  = chars[self._equip_char]
            list_y = char_y + len(chars) + 3
            n_show = min(len(items), H - list_y - 4)
            box(scr, list_y, char_x, n_show+2, W-char_x-3, ' Choose Equipment ', 5)
            for i, nm in enumerate(items[:n_show]):
                d   = EQUIPMENT.get(nm, {})
                sel = i == self._cursor
                arrow = '▶' if sel else ' '
                if nm == '[Remove]':
                    label = f' {arrow} [Remove current equipment]'
                    attr  = P(2)|curses.A_BOLD if sel else P(2)
                else:
                    delta = char.stat_preview(nm)
                    parts = []
                    for k, v in delta.items():
                        if v != 0:
                            sign = '+' if v > 0 else ''
                            col  = '↑' if v > 0 else '↓'
                            parts.append(f'{col}{k}:{sign}{v}')
                    delta_str = '  '.join(parts)
                    price_str = f'{d.get("price",0):>5}g'
                    label = f' {arrow} {nm:<22} {price_str}  {delta_str}'
                    if sel:
                        attr = P(7)|curses.A_BOLD
                    else:
                        attr = P(5)
                safe_add(scr, list_y+1+i, char_x+2, label[:W-char_x-7], attr)

    def _draw_items(self, scr, H, W):
        P = curses.color_pair
        from .data import ITEMS
        avail = [(n,c) for n,c in self.party.items.items()]

        # Item list panel
        list_x, list_y = 2, 5
        list_w = W // 2 - 2
        n_show = min(len(avail), H - list_y - 6)
        box(scr, list_y, list_x, max(n_show, 1)+2, list_w, ' Items ', 5)
        type_icons = {'heal': '♥', 'mp': '◌', 'elixir': '★', 'raise': '†',
                      'esuna': '◎', 'dmg': '✦'}
        for i, (name, cnt) in enumerate(avail[:n_show]):
            d     = ITEMS.get(name, {})
            sel   = i == self._item_cursor
            arrow = '▶' if sel else ' '
            itype = d.get('type', '')
            icon  = type_icons.get(itype, '·')
            label = f' {arrow} {icon} {name:<18} ×{cnt:<3}'
            attr  = P(7)|curses.A_BOLD if sel else P(4)
            safe_add(scr, list_y+1+i, list_x+2, label[:list_w-4], attr)

        # Description panel for selected item
        if avail:
            sel_item = avail[min(self._item_cursor, len(avail)-1)]
            d = ITEMS.get(sel_item[0], {})
            desc_x = list_x + list_w + 2
            desc_w = W - desc_x - 3
            box(scr, list_y, desc_x, 5, desc_w, ' Info ', 5)
            safe_add(scr, list_y+1, desc_x+2, sel_item[0], P(4)|curses.A_BOLD)
            safe_add(scr, list_y+2, desc_x+2, d.get('desc', ''), P(5))
            tgt = d.get('target', '')
            safe_add(scr, list_y+3, desc_x+2, f'Target: {tgt}', P(5)|curses.A_DIM)

        # Target selection panel
        if self._item_state == 'TARGET':
            tgt_x = list_x + list_w + 2
            tgt_y = list_y + 6
            tgt_w = W - tgt_x - 3
            box(scr, tgt_y, tgt_x, len(self.party.members)+2, tgt_w, ' Use on... ', 1)
            for i, m in enumerate(self.party.members):
                sel  = i == self._item_target
                attr = P(7)|curses.A_BOLD if sel else P(m.color)
                arrow = '▶' if sel else ' '
                ko = ' ✝' if not m.alive else ''
                label = f' {arrow} {m.name:<10} HP:{m.hp}/{m.max_hp}{ko}'
                safe_add(scr, tgt_y+1+i, tgt_x+2, label[:tgt_w-4], attr)
