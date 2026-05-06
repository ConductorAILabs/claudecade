"""Claudémon overworld exploration."""
from __future__ import annotations

import curses, random
from .data    import WORLD_MAPS, ENCOUNTERS, CLAUDEMON
from .entities import ClaudemonInstance

def _p(scr: curses.window, H: int, W: int, r: int, c: int, s: str, a: int = 0) -> None:
    try:
        if 0 <= r < H-1 and 0 <= c < W:
            scr.addstr(r, c, s[:max(0, W-c)], a)
    except curses.error:
        pass

TILE_COLORS = {
    '#': (5, False),  # wall — white dim
    '▲': (3, False),  # tree — green dim
    '.': (5, False),  # path
    '·': (5, False),  # path dot
    'G': (3, True),   # grass — green bold
    '~': (8, True),   # water — cyan
    '≈': (8, True),   # water wave — cyan
    '≋': (8, True),   # water strong — cyan
    'T': (7, True),   # town building — white bold
    'N': (4, True),   # NPC — yellow
    'P': (1, True),   # player start
    '═': (5, False),  # path connector
    ' ': (5, False),
}

TILE_CHARS = {
    '#': '▓', '.': '·', '·': '·', 'G': '░', '~': '≈',
    '≈': '≈', '≋': '≋', 'T': '▓', 'N': '◉', 'P': '·',
    '▲': '▲', '═': '─', ' ': ' ',
}

class Overworld:
    def __init__(self, party: list[ClaudemonInstance], items: dict[str, int],
                 area: str = 'startup', px: int = 5, py: int = 8) -> None:
        self.party   = party
        self.items   = items
        self.area    = area
        self.px, self.py = px, py
        self.result: tuple[str, object] | None = None  # None | ('battle', enemy) | ('npc', data)
        self.msg     = ''
        self.msg_timer = 0
        self.steps   = 0

    def _map(self) -> list[str]:
        return WORLD_MAPS[self.area]['map']

    def _tile(self, x: int, y: int) -> str:
        m = self._map()
        if 0 <= y < len(m) and 0 <= x < len(m[y]):
            return m[y][x]
        return '#'

    def _walkable(self, t: str) -> bool:
        return t not in ('#', '~')

    def handle_key(self, key: int) -> None:
        dx, dy = 0, 0
        if key in (curses.KEY_UP,    ord('w')): dy = -1
        if key in (curses.KEY_DOWN,  ord('s')): dy =  1
        if key in (curses.KEY_LEFT,  ord('a')): dx = -1
        if key in (curses.KEY_RIGHT, ord('d')): dx =  1
        if dx == 0 and dy == 0: return

        nx, ny = self.px + dx, self.py + dy
        tile   = self._tile(nx, ny)

        # Area transition exits
        area_data = WORLD_MAPS[self.area]
        exit_map  = area_data.get('exits', {})
        if (nx, ny) in exit_map:
            dest = exit_map[(nx, ny)]
            if dest in WORLD_MAPS:
                conn = area_data.get('connections', {})
                for direction, (dest_area, dest_x, dest_y) in conn.items():
                    if dest_area == dest:
                        self.area = dest
                        self.px, self.py = dest_x, dest_y
                        self.msg = f'Entering {WORLD_MAPS[dest]["name"]}!'
                        self.msg_timer = 60
                        return
            return

        if not self._walkable(tile): return

        # NPC interaction
        npcs = area_data.get('npcs', {})
        if (nx, ny) in npcs:
            npc = npcs[(nx, ny)]
            self.result = ('npc', npc)
            return

        self.px, self.py = nx, ny
        self.steps += 1

        # Encounter check on grass
        if tile == 'G':
            enc_table = area_data.get('encounter_table')
            if enc_table and random.random() < 0.12:
                table  = ENCOUNTERS.get(enc_table, [])
                if table:
                    name, lv_min, lv_max = random.choice(table)
                    lv    = random.randint(lv_min, lv_max)
                    enemy = ClaudemonInstance(name, lv)
                    self.result = ('battle', enemy)

    def draw(self, scr: curses.window, H: int, W: int, tick: int) -> None:
        P = curses.color_pair
        scr.erase()

        MAP_ROWS = H - 7
        MAP_COLS = W - 2
        m  = self._map()
        mh = len(m)
        mw = len(m[0]) if mh else 0

        # Viewport: try to centre on player
        vx0 = max(0, min(mw - MAP_COLS, self.px - MAP_COLS // 2))
        vy0 = max(0, min(mh - MAP_ROWS, self.py - MAP_ROWS // 2))

        _p(scr, H, W, 0, 0, '╔'+'═'*(W-2)+'╗', P(5)|curses.A_BOLD)
        _p(scr, H, W, H-1, 0, '╚'+'═'*(W-2)+'╝', P(5)|curses.A_BOLD)
        for r in range(1, H-1):
            _p(scr, H, W, r, 0, '║', P(5))
            _p(scr, H, W, r, W-1, '║', P(5))

        _p(scr, H, W, 1, 1, '▓▒░'+'░'*(W-8)+'░▒▓', P(5)|curses.A_DIM)
        aname = WORLD_MAPS[self.area]['name']
        _p(scr, H, W, 1, 5, f'★ CLAUDÉMON ★  {aname}', P(6)|curses.A_BOLD)
        _p(scr, H, W, 2, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)

        for vy in range(MAP_ROWS):
            for vx in range(MAP_COLS):
                mx, my = vx0 + vx, vy0 + vy
                if mx >= mw or my >= mh: continue
                tile = m[my][mx]
                ch   = TILE_CHARS.get(tile, tile)
                col, bold = TILE_COLORS.get(tile, (5, False))
                attr = P(col) | (curses.A_BOLD if bold else curses.A_DIM)
                # Animate grass tiles slightly
                if tile == 'G' and (tick // 15 + mx + my) % 8 == 0:
                    ch = '▒'
                # Animate water tiles
                if tile in ('~', '≈', '≋') and (tick // 20 + mx) % 4 == 0:
                    ch = '≋'
                if mx == self.px and my == self.py:
                    ch   = '♟'
                    attr = P(6) | curses.A_BOLD
                _p(scr, H, W, 3 + vy, 1 + vx, ch, attr)

        status_y = H - 4
        _p(scr, H, W, status_y, 0, '╠'+'═'*(W-2)+'╣', P(5)|curses.A_BOLD)
        slot_w = max(10, (W - 2) // max(1, len(self.party[:6])))
        for i, c in enumerate(self.party[:6]):
            col_x = 2 + i * slot_w
            if col_x + slot_w > W - 2: break
            hp_f  = c.hp / c.max_hp if c.max_hp else 0
            hp_cp = P(3) if hp_f > 0.5 else (P(4) if hp_f > 0.25 else P(2))
            bar_w = min(8, slot_w - 6)
            filled = max(0, int(bar_w * hp_f))
            bar = '█' * filled + '░' * (bar_w - filled)
            name_attr = P(1)|curses.A_BOLD if c.alive else P(5)|curses.A_DIM
            _p(scr, H, W, status_y+1, col_x, c.name[:slot_w-1], name_attr)
            if c.alive:
                _p(scr, H, W, status_y+2, col_x, bar, hp_cp|curses.A_BOLD)
            else:
                _p(scr, H, W, status_y+2, col_x, '✗ FAINT', P(2)|curses.A_DIM)

        # Message overlay
        if self.msg_timer > 0:
            self.msg_timer -= 1
            mw2 = len(self.msg) + 4
            mr = H // 2
            mc = (W - mw2) // 2
            try:
                scr.addstr(mr, mc, '╔'+'═'*(mw2-2)+'╗', P(5)|curses.A_BOLD)
                scr.addstr(mr+1, mc, '║ '+self.msg+' ║', P(5)|curses.A_BOLD)
                scr.addstr(mr+2, mc, '╚'+'═'*(mw2-2)+'╝', P(5)|curses.A_BOLD)
            except curses.error:
                pass

        # Controls hint
        _p(scr, H, W, H-2, 2, 'WASD:Move   SPACE:Interact   M:Menu   ESC:Pause', P(5)|curses.A_DIM)
        scr.refresh()
