"""World map, town, and dungeon exploration."""
import curses, random
from .data    import (WORLD_MAP, MAP_H, MAP_W, WALKABLE, ENCOUNTER_CHANCE,
                      TILE_TOWNS, TILE_DUNGEONS, TOWNS, DUNGEONS, SHOPS,
                      INN_PRICES, ENCOUNTER_GROUPS, STORY)
from .entities import Party, EnemyInstance
from .ui       import safe_add, box, bar, center, menu_list

TILE_COLOR = {
    '~': 8, '^': 5, '.': 3, 'T': 3, 'A': 4, 'E': 4, 'C': 4,
    '1': 2, '2': 2, '3': 2,
}
TILE_CHAR  = {
    '~': '~', '^': '^', '.': '.', 'T': 'T',
    'A': 'A', 'E': 'E', 'C': 'C',
    '1': '1', '2': '2', '3': '3',
}
# Per-tile texture variants — picked deterministically from (x,y) so terrain
# looks varied without flickering. Landmark tiles (towns, dungeons, mountains)
# stay fixed so the player can identify them.
TILE_VARIANTS = {
    '.': '.,\'·░',
    'T': 'T♣Y♠',
    '~': '~≈∽⌒',
}

def _tile_glyph(tile: str, x: int, y: int, tick: int) -> str:
    """Pick a textured glyph for terrain tiles, animated for water."""
    variants = TILE_VARIANTS.get(tile)
    if not variants: return TILE_CHAR.get(tile, tile)
    if tile == '~':
        # Water shimmers — phase shifts every ~30 ticks
        idx = (x * 7 + y * 13 + tick // 30) % len(variants)
    else:
        idx = (x * 31 + y * 17) % len(variants)
    return variants[idx]

# ── World map ──────────────────────────────────────────────────────────────────
class WorldMap:
    def __init__(self, party: Party) -> None:
        self.party  = party
        self.x      = party.map_x
        self.y      = party.map_y
        self.result: tuple | None = None   # None | ('town', name) | ('dungeon', name, region) | ('battle', [...])

    def _tile(self, x: int, y: int) -> str:
        if 0 <= y < MAP_H and 0 <= x < MAP_W:
            return WORLD_MAP[y][x]
        return '~'

    def handle_key(self, key: int) -> None:
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

    def _region_at(self, x: int, y: int) -> int:
        tile = self._tile(x, y)
        if tile in TILE_DUNGEONS: return TILE_DUNGEONS[tile][1]
        if x <= 20:  return 1
        if x <= 46:  return 2
        return 3

    def draw(self, scr: 'curses.window', H: int, W: int, tick: int) -> None:
        P = curses.color_pair
        scr.erase()

        # viewport centered on player
        vw = W - 2
        vh = H - 6
        vx0 = max(0, min(MAP_W - vw, self.x - vw // 2))
        vy0 = max(0, min(MAP_H - vh, self.y - vh // 2))

        # Bold decorative header with block styling
        safe_add(scr, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
        safe_add(scr, 1, 1, '█████ WORLD MAP █████', P(5)|curses.A_BOLD)
        gx = f'Gold: {self.party.gold}g'
        safe_add(scr, 1, W-len(gx)-4, gx, P(4)|curses.A_BOLD)
        safe_add(scr, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

        for vy in range(vh):
            for vx in range(vw):
                mx, my = vx0 + vx, vy0 + vy
                tile   = self._tile(mx, my)
                ch     = _tile_glyph(tile, mx, my, tick)
                cp_n   = TILE_COLOR.get(tile, 5)
                attr   = curses.color_pair(cp_n)
                if tile in ('^', 'T'): attr |= curses.A_BOLD
                # Faint dim on plain grass texture variants for depth
                if tile == '.' and ch in ('░', '·'): attr |= curses.A_DIM
                if mx == self.x and my == self.y:
                    attr = P(1)|curses.A_BOLD; ch = '@'
                safe_add(scr, 1 + vy, 1 + vx, ch, attr)

        # HUD with visual improvements
        p0, p1, p2 = self.party.members
        hud_y = H - 4
        safe_add(scr, hud_y, 0, '╠' + '═'*(W-2) + '╣', P(3)|curses.A_BOLD)
        safe_add(scr, hud_y, 2, '▓ PARTY ▓', P(3)|curses.A_BOLD)
        for i, m in enumerate(self.party.members):
            mx = 2 + i * (W // 3)
            alive_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)
            safe_add(scr, hud_y+1, mx, f'{m.name} Lv{m.level}', alive_attr)
            hp_bar = f'HP:█{m.hp:>3}/{m.max_hp:<3}█'
            mp_bar = f'MP:█{m.mp:>3}/{m.max_mp:<3}█'
            safe_add(scr, hud_y+2, mx, hp_bar, P(3))
            safe_add(scr, hud_y+3, mx, mp_bar, P(8))

        safe_add(scr, H-1, 0, '╚' + '═'*(W-2) + '╝', P(5)|curses.A_BOLD)
        ctrl = '║ WASD:Move  T:Town/Dungeon  M:Menu  S:Save ║'
        safe_add(scr, hud_y+3, (W-len(ctrl))//2, ctrl[:W], P(5)|curses.A_BOLD)
        scr.refresh()


# ── Town ───────────────────────────────────────────────────────────────────────
class TownScreen:
    MAIN_OPTS = ['Talk to NPCs', 'Shop', 'Inn', 'Leave']

    def __init__(self, party: Party, town_name: str) -> None:
        self.party   = party
        self.name    = town_name
        self.data    = TOWNS[town_name]
        self.result: str | tuple | None = None   # None | 'leave' | ('battle', [...], region)
        self._state  = 'MAIN'
        self._cursor = 0
        self._npc_idx= 0
        self._npc_line = 0
        self._shop_state  = 'CATEGORY'
        self._shop_cat    = 0
        self._shop_cursor = 0
        self._shop_cats: list[str] = ['Items','Weapons','Armor','Accessories','Sell','Done']
        self._shop_items: list = []
        self._msg         = ''
        self._msg_timer   = 0

    def handle_key(self, key: int) -> None:
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

    def _show(self, msg: str, duration: int = 90) -> None:
        self._msg = msg; self._msg_timer = duration

    def draw(self, scr: 'curses.window', H: int, W: int, tick: int) -> None:
        P = curses.color_pair
        scr.erase()
        # Bold header
        safe_add(scr, 0, 0, '╔' + '═'*(W-2) + '╗', P(4)|curses.A_BOLD)
        town_header = f'▓ {self.name} ▓'
        safe_add(scr, 0, (W-len(town_header))//2, town_header, P(4)|curses.A_BOLD)
        safe_add(scr, 1, 0, '╠' + '═'*(W-2) + '╣', P(4)|curses.A_BOLD)
        safe_add(scr, 2, 2, self.data['desc'], P(5))

        if self._msg_timer > 0:
            self._msg_timer -= 1
            safe_add(scr, 2, 2, self._msg[:W-4], P(4)|curses.A_BOLD)

        if self._state == 'MAIN':
            # Menu with block styling
            safe_add(scr, 4, 2, '╔════════════════════╗', P(5)|curses.A_BOLD)
            safe_add(scr, 4, 5, '▓ MENU ▓', P(5)|curses.A_BOLD)
            for i, opt in enumerate(self.MAIN_OPTS):
                prefix = '▶' if i == self._cursor else ' '
                label = f'{prefix} {opt}'
                cp = P(7)|curses.A_BOLD if i == self._cursor else P(5)
                safe_add(scr, 5+i, 4, label, cp)
            safe_add(scr, 5+len(self.MAIN_OPTS), 2, '╚════════════════════╝', P(5)|curses.A_BOLD)

        elif self._state == 'NPC':
            npcs  = self.data['npcs']
            npc   = npcs[self._npc_idx]
            lines = npc['lines']
            # NPC dialog box with borders
            safe_add(scr, 4, 2, '╔' + '═'*(W-6) + '╗', P(1)|curses.A_BOLD)
            npc_header = f'█ {npc["name"]} █'
            safe_add(scr, 4, (W-len(npc_header))//2, npc_header, P(1)|curses.A_BOLD)
            safe_add(scr, 5, 2, '╠' + '═'*(W-6) + '╣', P(1)|curses.A_BOLD)
            line = lines[min(self._npc_line, len(lines)-1)]
            safe_add(scr, 6, 4, line, P(5))
            safe_add(scr, 12, 2, '╚' + '═'*(W-6) + '╝', P(1)|curses.A_BOLD)
            safe_add(scr, 13, 4, '▒ [SPACE] next / [Q] back ▒', P(5)|curses.A_BOLD)

        elif self._state == 'SHOP':
            self._draw_shop(scr, H, W)

        # Party quick status with visual styling
        status_y = H - 5
        safe_add(scr, status_y, 0, '╠' + '═'*(W-2) + '╣', P(3)|curses.A_BOLD)
        safe_add(scr, status_y, 2, '▓ PARTY STATUS ▓', P(3)|curses.A_BOLD)
        for i, m in enumerate(self.party.members):
            mx = 2 + i*(W//3)
            safe_add(scr, status_y+1, mx, f'{m.name} Lv{m.level}', P(m.color)|curses.A_BOLD)
            safe_add(scr, status_y+2, mx, f'█HP:{m.hp:>3}/{m.max_hp}█', P(3))
            safe_add(scr, status_y+3, mx, f'█MP:{m.mp:>3}/{m.max_mp}█ G:{self.party.gold}', P(8))
        safe_add(scr, H-1, 0, '╚' + '═'*(W-2) + '╝', P(5)|curses.A_BOLD)
        scr.refresh()

    def _draw_shop(self, scr, H, W):
        P = curses.color_pair
        shop = SHOPS.get(self.name, {})
        # Shop categories with block styling
        safe_add(scr, 4, 2, '╔══════════════════════╗', P(4)|curses.A_BOLD)
        safe_add(scr, 4, 5, '▓ CATEGORIES ▓', P(4)|curses.A_BOLD)
        for i, cat in enumerate(self._shop_cats):
            prefix = '▶' if (i == self._shop_cat and self._shop_state == 'CATEGORY') else ' '
            label = f'{prefix} {cat}'
            cp = P(7)|curses.A_BOLD if (i == self._shop_cat and self._shop_state == 'CATEGORY') else P(4)
            safe_add(scr, 5+i, 4, label, cp)
        safe_add(scr, 5+len(self._shop_cats), 2, '╚══════════════════════╝', P(4)|curses.A_BOLD)

        gold_display = f'█ Gold: {self.party.gold}g █'
        safe_add(scr, 4, 26, gold_display, P(4)|curses.A_BOLD)

        if self._shop_state == 'BUY' and self._shop_items:
            from .data import ITEMS, EQUIPMENT
            # Buy menu with borders
            safe_add(scr, 8, 2, '╔' + '═'*(W-6) + '╗', P(4)|curses.A_BOLD)
            safe_add(scr, 8, (W-10)//2, '▓ BUY ▓', P(4)|curses.A_BOLD)
            safe_add(scr, 9, 2, '╠' + '═'*(W-6) + '╣', P(4)|curses.A_BOLD)
            for i, item in enumerate(self._shop_items[:H-20]):
                d = ITEMS.get(item) or EQUIPMENT.get(item, {})
                price = d.get('price', 0)
                desc  = d.get('desc', '')
                prefix = '▶' if i == self._shop_cursor else ' '
                label = f'{prefix} {item:<20} {price:>5}g  {desc}'
                cp = P(7)|curses.A_BOLD if i == self._shop_cursor else P(5)
                safe_add(scr, 10+i, 4, label[:W-8], cp)

        elif self._shop_state == 'SELL':
            inv = [(n,c) for n,c in self.party.items.items()]
            # Sell menu with borders
            safe_add(scr, 8, 2, '╔' + '═'*(W-6) + '╗', P(4)|curses.A_BOLD)
            safe_add(scr, 8, (W-18)//2, '▓ SELL (half price) ▓', P(4)|curses.A_BOLD)
            safe_add(scr, 9, 2, '╠' + '═'*(W-6) + '╣', P(4)|curses.A_BOLD)
            from .data import ITEMS
            for i, (name, cnt) in enumerate(inv[:H-20]):
                d    = ITEMS.get(name, {})
                sell = d.get('price', 10) // 2
                prefix = '▶' if i == self._shop_cursor else ' '
                label = f'{prefix} {name:<20} x{cnt:<3}  sell:{sell}g'
                cp = P(7)|curses.A_BOLD if i == self._shop_cursor else P(4)
                safe_add(scr, 10+i, 4, label[:W-8], cp)


# ── Dungeon ────────────────────────────────────────────────────────────────────
class DungeonScreen:
    def __init__(self, party: Party, dungeon_name: str) -> None:
        self.party  = party
        self.dname  = dungeon_name
        self.data   = DUNGEONS[dungeon_name]
        self.region = self.data['region']
        self.dmap   = self.data['map']
        self.chests_opened: set[tuple[int, int]] = set()
        self.result: str | tuple | None = None   # None | 'exit' | ('battle', [...], int) | ('boss', str)
        self.log: list[str] = [self.data['intro']]
        self._find_start()

    def _find_start(self) -> None:
        for r, row in enumerate(self.dmap):
            for c, ch in enumerate(row):
                if ch == 'S': self.px, self.py = c, r; return
        self.px, self.py = 1, 1

    def _tile(self, x: int, y: int) -> str:
        if 0 <= y < len(self.dmap) and 0 <= x < len(self.dmap[y]):
            return self.dmap[y][x]
        return '#'

    def handle_key(self, key: int) -> None:
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

    def draw(self, scr: 'curses.window', H: int, W: int, tick: int) -> None:
        P = curses.color_pair
        scr.erase()
        # Dungeon header with bold styling
        safe_add(scr, 0, 0, '╔' + '═'*(W-2) + '╗', P(2)|curses.A_BOLD)
        dungeon_header = f'█ {self.dname} █'
        safe_add(scr, 0, (W-len(dungeon_header))//2, dungeon_header, P(2)|curses.A_BOLD)
        safe_add(scr, 1, 0, '╠' + '═'*(W-2) + '╣', P(2)|curses.A_BOLD)

        dh = len(self.dmap)
        dw = len(self.dmap[0]) if dh else 0
        scale = 2   # each tile is 2 chars wide
        off_x = max(1, (W  - dw * scale) // 2)
        off_y = max(1, (H  - dh   - 8)   // 2 + 1)

        for r, row in enumerate(self.dmap):
            for c, ch in enumerate(row):
                sx = off_x + c * scale
                sy = off_y + r
                if sy >= H-7 or sx >= W-1: continue
                if c == self.px and r == self.py:
                    safe_add(scr, sy, sx, '@ ', P(1)|curses.A_BOLD)
                    continue
                pos = (c, r)
                if ch == '#':
                    safe_add(scr, sy, sx, '██', P(5))
                elif ch == '.':
                    safe_add(scr, sy, sx, '  ', 0)
                elif ch == 'S':
                    safe_add(scr, sy, sx, '▲ ', P(3))
                elif ch == 'B':
                    attr = P(2)|curses.A_BOLD
                    if (tick//8)%2 == 0: attr |= curses.A_BLINK
                    safe_add(scr, sy, sx, '!! ', attr)
                elif ch == 'C':
                    if pos in self.chests_opened:
                        safe_add(scr, sy, sx, '□ ', P(5))
                    else:
                        safe_add(scr, sy, sx, '■ ', P(4)|curses.A_BOLD)

        # Log with decorative styling
        log_y = H - 7
        safe_add(scr, log_y, 0, '╠' + '═'*(W-2) + '╣', P(5)|curses.A_BOLD)
        safe_add(scr, log_y, 2, '▓ LOG ▓', P(5)|curses.A_BOLD)
        for i, line in enumerate(self.log[-2:]):
            safe_add(scr, log_y+1+i, 2, line[:W-4], P(5))

        # Party HUD with visual improvements
        hud_y = H - 4
        safe_add(scr, hud_y, 0, '╠' + '═'*(W-2) + '╣', P(3)|curses.A_BOLD)
        safe_add(scr, hud_y, 2, '▓ PARTY ▓', P(3)|curses.A_BOLD)
        for i, m in enumerate(self.party.members):
            mx = 2 + i*(W//3)
            alive_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)
            safe_add(scr, hud_y+1, mx, f'{m.name} █ {m.hp:>3}/{m.max_hp}',
                     alive_attr)
        safe_add(scr, H-2, 2, '▒ WASD:Move  Q:Exit  ██=Chest  !!=Boss ▒', P(5)|curses.A_BOLD)
        safe_add(scr, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
        scr.refresh()


# ── Party menu ─────────────────────────────────────────────────────────────────
class PartyMenu:
    TABS: list[str] = ['Status','Equipment','Items','Save','Close']

    def __init__(self, party: Party) -> None:
        self.party   = party
        self.result: str | None = None   # None | 'close'
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

    def handle_key(self, key: int) -> None:
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
        # Menu header with bold styling
        safe_add(scr, 0, 0, '╔' + '═'*(W-2) + '╗', P(5)|curses.A_BOLD)
        menu_header = '█ M E N U █'
        safe_add(scr, 0, (W-len(menu_header))//2, menu_header, P(5)|curses.A_BOLD)
        safe_add(scr, 1, 0, '╠' + '═'*(W-2) + '╣', P(5)|curses.A_BOLD)

        # Tab bar with visual styling
        tx = 2
        for i, tab in enumerate(self.TABS):
            attr = P(7)|curses.A_BOLD|curses.A_REVERSE if i == self._tab else P(6)
            tab_str = f'[ {tab} ]'
            safe_add(scr, 2, tx, tab_str, attr)
            tx += len(tab_str) + 2

        if self._msg_t > 0:
            self._msg_t -= 1
            safe_add(scr, 3, 2, self._msg[:W-4], P(4)|curses.A_BOLD)

        safe_add(scr, 3, W-24, f'█ Gold: {self.party.gold}g █', P(4)|curses.A_BOLD)

        tab = self.TABS[self._tab]

        if tab == 'Status':
            self._draw_status(scr, H, W)
        elif tab == 'Equipment':
            self._draw_equip(scr, H, W)
        elif tab == 'Items':
            self._draw_items(scr, H, W)
        elif tab == 'Save':
            save_prompt = '█ Press ENTER to save game █'
            center(scr, H//2, save_prompt, W, P(4)|curses.A_BOLD)

        safe_add(scr, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
        scr.refresh()

    def _draw_status(self, scr, H, W):
        P = curses.color_pair
        m = self.party.members[self._cursor]
        # Party selection box with borders
        safe_add(scr, 3, 2, '╔══════════════════╗', P(5)|curses.A_BOLD)
        safe_add(scr, 3, 5, '▓ PARTY ▓', P(5)|curses.A_BOLD)
        for i, mm in enumerate(self.party.members):
            attr = P(7)|curses.A_BOLD if i == self._cursor else P(mm.color)
            prefix = '▶' if i==self._cursor else ' '
            safe_add(scr, 4+i, 4, f'{prefix} {mm.name}', attr)
        safe_add(scr, 7, 2, '╚══════════════════╝', P(5)|curses.A_BOLD)
        # Stats panel with block styling
        bx = 22
        safe_add(scr, 3,  bx, f'█ {m.name} the {m.cls} █', P(m.color)|curses.A_BOLD)
        safe_add(scr, 4,  bx, f'Level: {m.level}   EXP: {m.exp}/{m.exp_to_next()}', P(5))
        safe_add(scr, 5,  bx, f'█ HP:  {m.hp:>4}/{m.max_hp:<4}█', P(3)|curses.A_BOLD)
        safe_add(scr, 6,  bx, f'█ MP:  {m.mp:>4}/{m.max_mp:<4}█', P(8)|curses.A_BOLD)
        safe_add(scr, 7,  bx, f'ATK: {m.atk}   DEF: {m.defense}', P(5))
        safe_add(scr, 8,  bx, f'MAG: {m.mag}   SPD: {m.spd}', P(5))
        safe_add(scr, 9,  bx, f'Weapon:    {m.weapon or "—"}', P(5))
        safe_add(scr, 10, bx, f'Armor:     {m.armor  or "—"}', P(5))
        safe_add(scr, 11, bx, f'Accessory: {m.acc    or "—"}', P(5))
        spells_str = ', '.join(m.spells) if m.spells else '—'
        safe_add(scr, 12, bx, f'Spells: {spells_str[:W-bx-4]}', P(6)|curses.A_BOLD)

    def _draw_equip(self, scr, H, W):
        P = curses.color_pair
        from .data import EQUIPMENT
        chars = self.party.members
        # Character selection with borders
        safe_add(scr, 3, 2, '╔════════════════════╗', P(5)|curses.A_BOLD)
        safe_add(scr, 3, 5, '▓ CHARACTER ▓', P(5)|curses.A_BOLD)
        for i, m in enumerate(chars):
            attr = P(7)|curses.A_BOLD if i == self._equip_char and self._equip_state != 'CHAR' else P(m.color)
            prefix = '▶' if i == self._equip_char else ' '
            safe_add(scr, 4+i, 4, f'{prefix} {m.name}', attr)
        safe_add(scr, 7, 2, '╚════════════════════╝', P(5)|curses.A_BOLD)

        if self._equip_state in ('EQUIP_CHOOSE','ITEM_LIST'):
            char = chars[self._equip_char]
            slots = ['Weapon','Armor','Accessory']
            # Slot selection with borders
            safe_add(scr, 3, 24, '╔══════════════════╗', P(5)|curses.A_BOLD)
            safe_add(scr, 3, 27, '▓ SLOT ▓', P(5)|curses.A_BOLD)
            for i, sl in enumerate(slots):
                prefix = '▶' if i == self._equip_slot else ' '
                attr = P(7)|curses.A_BOLD if i == self._equip_slot else P(5)
                safe_add(scr, 4+i, 26, f'{prefix} {sl}', attr)
            safe_add(scr, 7, 24, '╚══════════════════╝', P(5)|curses.A_BOLD)
        if self._equip_state == 'ITEM_LIST':
            items = getattr(self, '_equip_items', [])
            char  = chars[self._equip_char]
            # Equipment list with borders
            safe_add(scr, 8, 2, '╔' + '═'*(W-6) + '╗', P(5)|curses.A_BOLD)
            safe_add(scr, 8, (W-16)//2, '▓ EQUIPMENT ▓', P(5)|curses.A_BOLD)
            safe_add(scr, 9, 2, '╠' + '═'*(W-6) + '╣', P(5)|curses.A_BOLD)
            for i, nm in enumerate(items[:H-20]):
                d = EQUIPMENT.get(nm, {})
                prefix = '▶' if i == self._cursor else ' '
                if nm == '[Remove]':
                    label = f'{prefix} [Remove current]'
                else:
                    delta = char.stat_preview(nm)
                    parts = [f'{k}:{("+" if v>=0 else "")}{v}' for k,v in delta.items() if v != 0]
                    label = f'{prefix} {nm:<20} {d.get("price",0):>5}g  {" ".join(parts)}'
                attr = P(7)|curses.A_BOLD if i == self._cursor else P(5)
                safe_add(scr, 10+i, 4, label[:W-8], attr)

    def _draw_items(self, scr, H, W):
        P = curses.color_pair
        from .data import ITEMS
        avail = [(n,c) for n,c in self.party.items.items()]
        # Items list with borders
        safe_add(scr, 3, 2, '╔' + '═'*(W//2-4) + '╗', P(4)|curses.A_BOLD)
        safe_add(scr, 3, W//2-8, '▓ ITEMS ▓', P(4)|curses.A_BOLD)
        safe_add(scr, 4, 2, '╠' + '═'*(W//2-4) + '╣', P(4)|curses.A_BOLD)
        for i, (name, cnt) in enumerate(avail[:H-16]):
            d     = ITEMS.get(name, {})
            prefix = '▶' if i == self._item_cursor else ' '
            label = f'{prefix} {name:<18} x{cnt:<3}  {d.get("desc","")}'
            attr  = P(7)|curses.A_BOLD if i == self._item_cursor else P(4)
            safe_add(scr, 5+i, 4, label[:W//2-4], attr)
        if self._item_state == 'TARGET':
            # Target selection with borders
            safe_add(scr, 3, W//2+2, '╔' + '═'*22 + '╗', P(5)|curses.A_BOLD)
            safe_add(scr, 3, W//2+8, '▓ USE ON ▓', P(5)|curses.A_BOLD)
            safe_add(scr, 4, W//2+2, '╠' + '═'*22 + '╣', P(5)|curses.A_BOLD)
            for i, m in enumerate(self.party.members):
                prefix = '▶' if i == self._item_target else ' '
                attr = P(7)|curses.A_BOLD if i == self._item_target else P(m.color)
                safe_add(scr, 5+i, W//2+4, f'{prefix} {m.name} HP:{m.hp}', attr)
