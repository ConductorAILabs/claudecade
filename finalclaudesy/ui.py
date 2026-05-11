"""Shared curses drawing helpers."""
import curses
from claudcade_engine import setup_colors, at_safe


def safe_add(scr, y, x, text, attr=0):
    # Thin shim around the engine's at_safe — reads (H, W) from the screen so
    # call sites don't have to thread them through every helper.
    H, W = scr.getmaxyx()
    at_safe(scr, H, W, y, x, text, attr)


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


