"""Shared curses drawing helpers."""
import curses
from claudcade_engine import setup_colors


def safe_add(scr, y, x, text, attr=0):
    H, W = scr.getmaxyx()
    if y < 0 or y >= H - 1 or x < 0 or x >= W: return
    try:
        scr.addstr(y, x, text[:max(0, W - x)], attr)
    except curses.error:
        pass


def box(scr, y, x, h, w, title='', cp=5):
    P = curses.color_pair(cp)
    safe_add(scr, y,     x,     '╔' + '═'*(w-2) + '╗', P)
    safe_add(scr, y+h-1, x,     '╚' + '═'*(w-2) + '╝', P)
    for r in range(1, h-1):
        safe_add(scr, y+r, x,     '║', P)
        safe_add(scr, y+r, x+w-1, '║', P)
    if title:
        t = f' {title} '
        safe_add(scr, y, x + (w - len(t)) // 2, t, P | curses.A_BOLD)


def bar(scr, y, x, current, maximum, width, cp_fill=3, cp_empty=5):
    if maximum <= 0: ratio = 0.0
    else: ratio = max(0.0, min(1.0, current / maximum))
    filled = int(width * ratio)
    safe_add(scr, y, x, '█' * filled,          curses.color_pair(cp_fill) | curses.A_BOLD)
    safe_add(scr, y, x + filled, '░' * (width - filled), curses.color_pair(cp_empty))


def center(scr, y, text, W=None, attr=0):
    if W is None: _, W = scr.getmaxyx()
    x = max(0, (W - len(text)) // 2)
    safe_add(scr, y, x, text, attr)


def menu_list(scr, y, x, options, cursor, cp_sel=7, cp_norm=0, width=20):
    for i, opt in enumerate(options):
        label = f'> {opt}' if i == cursor else f'  {opt}'
        label = label.ljust(width)[:width]
        attr = curses.color_pair(cp_sel) | curses.A_BOLD if i == cursor else curses.color_pair(cp_norm)
        safe_add(scr, y + i, x, label, attr)

