"""World map, town, and dungeon exploration."""
import curses, random
from .data    import (WORLD_MAP, MAP_H, MAP_W, WALKABLE, ENCOUNTER_CHANCE,
                      TILE_TOWNS, TILE_DUNGEONS, TOWNS, DUNGEONS, SHOPS,
                      INN_PRICES, ENCOUNTER_GROUPS)
from .entities import Party
from .ui       import safe_add, center

TILE_COLOR = {
    '~': 8, '^': 5, '.': 3, 'T': 3, 'A': 4, 'E': 4, 'C': 4,
    '1': 2, '2': 2, '3': 2,
}
# Single quiet glyph per tile — high contrast between walkable space (blank-ish)
# and walls (solid). Landmarks pop because everything around them is calm.
TILE_CHAR  = {
    '~': '~',   # water, quiet wave
    '^': '^',   # mountain wall
    '.': ' ',   # walkable grass — blank for breathing room
    'T': 't',   # forest — lowercase t reads as foliage, dim color
    'A': 'A', 'E': 'E', 'C': 'C',
    '1': '1', '2': '2', '3': '3',
}

def _tile_glyph(tile: str, x: int, y: int, tick: int) -> str:
    """Return the single glyph for a tile. No variants — keeps the map calm."""
    return TILE_CHAR.get(tile, tile)

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

        # Reserve top/bottom rows for header and HUD; center the viewport
        # block horizontally inside the available terminal width.
        hud_h = 3                      # divider + 2 lines of party info
        vh    = max(6, H - hud_h - 3)  # map area height
        vw    = min(MAP_W, W - 4)      # map area width, capped to actual map
        vx0   = max(0, min(MAP_W - vw, self.x - vw // 2))
        vy0   = max(0, min(MAP_H - vh, self.y - vh // 2))
        off_x = max(0, (W - vw) // 2)  # horizontal centering of the viewport

        # Header — single line, no heavy borders
        title = 'WORLD MAP'
        center(scr, 0, title, W, P(6)|curses.A_BOLD)
        gx = f'Gold: {self.party.gold}'
        safe_add(scr, 0, W - len(gx) - 2, gx, P(4)|curses.A_BOLD)
        safe_add(scr, 1, 0, '─' * W, P(5)|curses.A_DIM)

        for vy in range(vh):
            for vx in range(vw):
                mx, my = vx0 + vx, vy0 + vy
                tile   = self._tile(mx, my)
                ch     = _tile_glyph(tile, mx, my, tick)
                cp_n   = TILE_COLOR.get(tile, 5)
                attr   = curses.color_pair(cp_n)
                # Mountains bold (hard wall), water dim (visual rest),
                # forests dim (softer than landmarks), landmarks bold+reverse.
                if tile == '^': attr |= curses.A_BOLD
                elif tile == '~': attr |= curses.A_DIM
                elif tile == 'T': attr |= curses.A_DIM
                elif tile in TILE_TOWNS or tile in TILE_DUNGEONS:
                    attr |= curses.A_BOLD | curses.A_REVERSE
                if mx == self.x and my == self.y:
                    attr = P(1)|curses.A_BOLD; ch = '@'
                safe_add(scr, 2 + vy, off_x + vx, ch, attr)

        # HUD — single divider, party in three centered columns
        hud_y = H - hud_h - 1
        safe_add(scr, hud_y, 0, '─' * W, P(5)|curses.A_DIM)
        col_w = W // 3
        for i, m in enumerate(self.party.members):
            label = f'{m.name} Lv{m.level}'
            hp    = f'HP {m.hp:>3}/{m.max_hp:<3}   MP {m.mp:>3}/{m.max_mp:<3}'
            alive_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)|curses.A_DIM
            cx_label = i * col_w + max(0, (col_w - len(label)) // 2)
            cx_stat  = i * col_w + max(0, (col_w - len(hp)) // 2)
            safe_add(scr, hud_y + 1, cx_label, label, alive_attr)
            safe_add(scr, hud_y + 2, cx_stat,  hp,    P(3))

        ctrl = 'WASD: Move    M: Menu    Q/ESC: Title'
        center(scr, H - 1, ctrl, W, P(5)|curses.A_DIM)
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

        # Header — name centered on top line, single divider below
        center(scr, 0, self.name.upper(), W, P(4)|curses.A_BOLD)
        safe_add(scr, 1, 0, '─' * W, P(5)|curses.A_DIM)

        # Description (or transient message)
        if self._msg_timer > 0:
            self._msg_timer -= 1
            center(scr, 2, self._msg[:W-4], W, P(4)|curses.A_BOLD)
        else:
            center(scr, 2, self.data['desc'], W, P(5))

        if self._state == 'MAIN':
            self._draw_main(scr, H, W)
        elif self._state == 'NPC':
            self._draw_npc(scr, H, W)
        elif self._state == 'SHOP':
            self._draw_shop(scr, H, W)

        # Party HUD — single divider, three centered columns
        status_y = H - 4
        safe_add(scr, status_y, 0, '─' * W, P(5)|curses.A_DIM)
        col_w = W // 3
        for i, m in enumerate(self.party.members):
            label = f'{m.name} Lv{m.level}'
            stat  = f'HP {m.hp:>3}/{m.max_hp}   MP {m.mp:>3}/{m.max_mp}'
            cx_label = i * col_w + max(0, (col_w - len(label)) // 2)
            cx_stat  = i * col_w + max(0, (col_w - len(stat)) // 2)
            safe_add(scr, status_y+1, cx_label, label, P(m.color)|curses.A_BOLD)
            safe_add(scr, status_y+2, cx_stat,  stat,  P(3))
        # Gold sits at the top-right, not on the divider line
        gx = f'Gold: {self.party.gold}'
        safe_add(scr, 0, W - len(gx) - 2, gx, P(4)|curses.A_BOLD)
        scr.refresh()

    def _draw_main(self, scr, H, W):
        P = curses.color_pair
        # Centered menu list
        list_h = len(self.MAIN_OPTS)
        start_y = max(5, (H - list_h - 8) // 2)
        for i, opt in enumerate(self.MAIN_OPTS):
            prefix = '> ' if i == self._cursor else '  '
            label = f'{prefix}{opt}'
            cp = P(7)|curses.A_BOLD if i == self._cursor else P(5)
            center(scr, start_y + i, label, W, cp)

    def _draw_npc(self, scr, H, W):
        P = curses.color_pair
        npcs  = self.data['npcs']
        npc   = npcs[self._npc_idx]
        lines = npc['lines']
        center(scr, 4, f'-- {npc["name"]} --', W, P(1)|curses.A_BOLD)
        line = lines[min(self._npc_line, len(lines)-1)]
        center(scr, 6, line[:W-4], W, P(5))
        center(scr, H-6, '[SPACE] next  /  [Q] back', W, P(5)|curses.A_DIM)

    def _draw_shop(self, scr, H, W):
        P = curses.color_pair
        # Categories on the left column
        cat_x = max(2, W // 4 - 12)
        center(scr, 4, 'SHOP', W, P(4)|curses.A_BOLD)
        gx = f'Gold: {self.party.gold}'
        safe_add(scr, 4, W - len(gx) - 2, gx, P(4)|curses.A_BOLD)

        for i, cat in enumerate(self._shop_cats):
            active = (i == self._shop_cat and self._shop_state == 'CATEGORY')
            prefix = '> ' if active else '  '
            label = f'{prefix}{cat}'
            cp = P(7)|curses.A_BOLD if active else P(4)
            safe_add(scr, 6+i, cat_x, label, cp)

        # Items area on the right
        list_x = max(cat_x + 16, W // 2 - 10)
        if self._shop_state == 'BUY' and self._shop_items:
            from .data import ITEMS, EQUIPMENT
            safe_add(scr, 6, list_x, 'BUY', P(4)|curses.A_BOLD)
            for i, item in enumerate(self._shop_items[:H-14]):
                d = ITEMS.get(item) or EQUIPMENT.get(item, {})
                price = d.get('price', 0)
                desc  = d.get('desc', '')
                prefix = '> ' if i == self._shop_cursor else '  '
                label = f'{prefix}{item:<18} {price:>5}g  {desc}'
                cp = P(7)|curses.A_BOLD if i == self._shop_cursor else P(5)
                safe_add(scr, 7+i, list_x, label[:W-list_x-2], cp)

        elif self._shop_state == 'SELL':
            inv = [(n,c) for n,c in self.party.items.items()]
            safe_add(scr, 6, list_x, 'SELL (half price)', P(4)|curses.A_BOLD)
            from .data import ITEMS
            for i, (name, cnt) in enumerate(inv[:H-14]):
                d    = ITEMS.get(name, {})
                sell = d.get('price', 10) // 2
                prefix = '> ' if i == self._shop_cursor else '  '
                label = f'{prefix}{name:<18} x{cnt:<3}  sell:{sell}g'
                cp = P(7)|curses.A_BOLD if i == self._shop_cursor else P(4)
                safe_add(scr, 7+i, list_x, label[:W-list_x-2], cp)


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

        # Header — name centered, single divider
        center(scr, 0, self.dname.upper(), W, P(2)|curses.A_BOLD)
        safe_add(scr, 1, 0, '─' * W, P(5)|curses.A_DIM)

        dh = len(self.dmap)
        dw = len(self.dmap[0]) if dh else 0
        scale = 2   # each tile is 2 chars wide
        map_h = H - 7    # leave room for log + party HUD + footer
        off_x = max(1, (W  - dw * scale) // 2)
        off_y = max(2, (map_h - dh) // 2 + 2)

        for r, row in enumerate(self.dmap):
            for c, ch in enumerate(row):
                sx = off_x + c * scale
                sy = off_y + r
                if sy >= H-5 or sx >= W-1: continue
                if c == self.px and r == self.py:
                    safe_add(scr, sy, sx, '@ ', P(1)|curses.A_BOLD)
                    continue
                pos = (c, r)
                if ch == '#':
                    safe_add(scr, sy, sx, '##', P(5)|curses.A_DIM)
                elif ch == '.':
                    safe_add(scr, sy, sx, '  ', 0)
                elif ch == 'S':
                    safe_add(scr, sy, sx, '. ', P(3)|curses.A_DIM)
                elif ch == 'B':
                    safe_add(scr, sy, sx, 'B ', P(2)|curses.A_BOLD)
                elif ch == 'C':
                    if pos in self.chests_opened:
                        safe_add(scr, sy, sx, '. ', P(5)|curses.A_DIM)
                    else:
                        safe_add(scr, sy, sx, '$ ', P(4)|curses.A_BOLD)

        # Log line — single line at the bottom area
        log_y = H - 4
        safe_add(scr, log_y, 0, '─' * W, P(5)|curses.A_DIM)
        if self.log:
            center(scr, log_y - 1, self.log[-1][:W-4], W, P(5))

        # Party HUD — single row of three centered HP readouts
        col_w = W // 3
        for i, m in enumerate(self.party.members):
            label = f'{m.name}  HP {m.hp:>3}/{m.max_hp}'
            alive_attr = P(m.color)|curses.A_BOLD if m.alive else P(5)|curses.A_DIM
            cx = i * col_w + max(0, (col_w - len(label)) // 2)
            safe_add(scr, log_y + 1, cx, label, alive_attr)

        ctrl = 'WASD: Move    Q/ESC: Exit    $=Chest    B=Boss'
        center(scr, H - 1, ctrl, W, P(5)|curses.A_DIM)
        scr.refresh()


# ── Party menu ─────────────────────────────────────────────────────────────────
class PartyMenu:
    TABS: list[str] = ['Status','Equipment','Items','Save','Close']

    def __init__(self, party: Party) -> None:
        self.party   = party
        self.result: str | None = None   # None | 'close'
        self._tab    = 0
        self._cursor = 0
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
        import json
        from . import SAVE_PATH
        try:
            with open(SAVE_PATH, 'w') as f:
                json.dump(self.party.save_dict(), f, indent=2)
            self._msg = f'Saved to {SAVE_PATH}'
        except OSError as e:
            self._msg = f'Save failed: {e}'
        self._msg_t = 90

    def draw(self, scr, H, W, tick):
        P = curses.color_pair
        scr.erase()

        # Header — centered title, gold on the right
        center(scr, 0, 'MENU', W, P(5)|curses.A_BOLD)
        gx = f'Gold: {self.party.gold}'
        safe_add(scr, 0, W - len(gx) - 2, gx, P(4)|curses.A_BOLD)
        safe_add(scr, 1, 0, '─' * W, P(5)|curses.A_DIM)

        # Tabs centered as a single row
        tab_labels = [f'[ {t} ]' for t in self.TABS]
        total = sum(len(t) for t in tab_labels) + 2 * (len(tab_labels) - 1)
        tx = max(0, (W - total) // 2)
        for i, lbl in enumerate(tab_labels):
            attr = P(7)|curses.A_BOLD|curses.A_REVERSE if i == self._tab else P(6)
            safe_add(scr, 2, tx, lbl, attr)
            tx += len(lbl) + 2

        if self._msg_t > 0:
            self._msg_t -= 1
            center(scr, 3, self._msg[:W-4], W, P(4)|curses.A_BOLD)

        safe_add(scr, 4, 0, '─' * W, P(5)|curses.A_DIM)

        tab = self.TABS[self._tab]
        if tab == 'Status':
            self._draw_status(scr, H, W)
        elif tab == 'Equipment':
            self._draw_equip(scr, H, W)
        elif tab == 'Items':
            self._draw_items(scr, H, W)
        elif tab == 'Save':
            center(scr, H//2, 'Press ENTER to save game', W, P(4)|curses.A_BOLD)
        scr.refresh()

    def _draw_status(self, scr, H, W):
        P = curses.color_pair
        m = self.party.members[self._cursor]
        # Left column — character list
        lx = max(2, W // 4 - 10)
        safe_add(scr, 6, lx, 'PARTY', P(5)|curses.A_BOLD)
        for i, mm in enumerate(self.party.members):
            attr = P(7)|curses.A_BOLD if i == self._cursor else P(mm.color)
            prefix = '> ' if i == self._cursor else '  '
            safe_add(scr, 8+i, lx, f'{prefix}{mm.name}', attr)
        # Right column — stat block
        bx = max(lx + 14, W // 2 - 6)
        safe_add(scr, 6,  bx, f'{m.name} the {m.cls}', P(m.color)|curses.A_BOLD)
        safe_add(scr, 7,  bx, f'Level {m.level}   EXP {m.exp}/{m.exp_to_next()}', P(5))
        safe_add(scr, 8,  bx, f'HP  {m.hp:>4}/{m.max_hp:<4}', P(3)|curses.A_BOLD)
        safe_add(scr, 9,  bx, f'MP  {m.mp:>4}/{m.max_mp:<4}', P(8)|curses.A_BOLD)
        safe_add(scr, 10, bx, f'ATK {m.atk:<3}  DEF {m.defense:<3}', P(5))
        safe_add(scr, 11, bx, f'MAG {m.mag:<3}  SPD {m.spd:<3}', P(5))
        safe_add(scr, 13, bx, f'Weapon    {m.weapon or "-"}', P(5))
        safe_add(scr, 14, bx, f'Armor     {m.armor  or "-"}', P(5))
        safe_add(scr, 15, bx, f'Accessory {m.acc    or "-"}', P(5))
        spells_str = ', '.join(m.spells) if m.spells else '-'
        safe_add(scr, 17, bx, f'Spells: {spells_str[:W-bx-4]}', P(6)|curses.A_BOLD)

    def _draw_equip(self, scr, H, W):
        P = curses.color_pair
        from .data import EQUIPMENT
        chars = self.party.members

        # Three columns: CHARACTER, SLOT, EQUIPMENT. Fixed widths keep them
        # from running into each other regardless of terminal size.
        lx = 4
        sx = lx + 16
        ix = sx + 14

        safe_add(scr, 6, lx, 'CHARACTER', P(5)|curses.A_BOLD)
        for i, m in enumerate(chars):
            attr = P(7)|curses.A_BOLD if i == self._equip_char and self._equip_state != 'CHAR' else P(m.color)
            prefix = '> ' if i == self._equip_char else '  '
            safe_add(scr, 8+i, lx, f'{prefix}{m.name:<10}', attr)

        if self._equip_state in ('EQUIP_CHOOSE','ITEM_LIST'):
            slots = ['Weapon','Armor','Accessory']
            safe_add(scr, 6, sx, 'SLOT', P(5)|curses.A_BOLD)
            for i, sl in enumerate(slots):
                prefix = '> ' if i == self._equip_slot else '  '
                attr = P(7)|curses.A_BOLD if i == self._equip_slot else P(5)
                safe_add(scr, 8+i, sx, f'{prefix}{sl:<10}', attr)

        if self._equip_state == 'ITEM_LIST':
            items = getattr(self, '_equip_items', [])
            char  = chars[self._equip_char]
            safe_add(scr, 6, ix, 'EQUIPMENT', P(5)|curses.A_BOLD)
            for i, nm in enumerate(items[:H-12]):
                d = EQUIPMENT.get(nm, {})
                prefix = '> ' if i == self._cursor else '  '
                if nm == '[Remove]':
                    label = f'{prefix}[Remove current]'
                else:
                    delta = char.stat_preview(nm)
                    parts = [f'{k}:{("+" if v>=0 else "")}{v}' for k,v in delta.items() if v != 0]
                    label = f'{prefix}{nm:<18} {d.get("price",0):>5}g  {" ".join(parts)}'
                attr = P(7)|curses.A_BOLD if i == self._cursor else P(5)
                safe_add(scr, 8+i, ix, label[:W-ix-2], attr)

    def _draw_items(self, scr, H, W):
        P = curses.color_pair
        from .data import ITEMS
        avail = [(n,c) for n,c in self.party.items.items()]
        # Layout: items list takes left ~55% when target column is showing,
        # full width otherwise. Truncate item labels so they never spill
        # into the target column.
        targeting = self._item_state == 'TARGET'
        lx        = max(2, W // 8)
        list_end  = (W // 2 + 4) if targeting else (W - 4)
        list_w    = max(20, list_end - lx - 2)

        safe_add(scr, 6, lx, 'ITEMS', P(4)|curses.A_BOLD)
        for i, (name, cnt) in enumerate(avail[:H-10]):
            d     = ITEMS.get(name, {})
            prefix = '> ' if i == self._item_cursor else '  '
            label = f'{prefix}{name:<14} x{cnt:<3}  {d.get("desc","")}'
            attr  = P(7)|curses.A_BOLD if i == self._item_cursor else P(4)
            safe_add(scr, 8+i, lx, label[:list_w], attr)

        if targeting:
            tx = list_end + 2
            safe_add(scr, 6, tx, 'USE ON', P(5)|curses.A_BOLD)
            for i, m in enumerate(self.party.members):
                prefix = '> ' if i == self._item_target else '  '
                attr = P(7)|curses.A_BOLD if i == self._item_target else P(m.color)
                safe_add(scr, 8+i, tx, f'{prefix}{m.name}  HP {m.hp}'[:W-tx-1], attr)
