#!/usr/bin/env python3
"""
CLAUDECADE Font Builder - ANSI SHADOW STYLE
Converts the ANSI Shadow ASCII art (with box-drawing chars) to TTF/OTF.
Each box-drawing character is rendered as the appropriate sub-pixel shape.
"""

from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

# ============================================================================
# ANSI SHADOW LETTERFORMS (from CLAUDECADE title)
# ============================================================================
GLYPHS = {
    'A': [
        " █████╗ ",
        "██╔══██╗",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    'B': [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔══██╗",
        "██████╔╝",
        "╚═════╝ ",
    ],
    'C': [
        " ██████╗",
        "██╔════╝",
        "██║     ",
        "██║     ",
        "╚██████╗",
        " ╚═════╝",
    ],
    'D': [
        "██████╗ ",
        "██╔══██╗",
        "██║  ██║",
        "██║  ██║",
        "██████╔╝",
        "╚═════╝ ",
    ],
    'E': [
        "███████╗",
        "██╔════╝",
        "█████╗  ",
        "██╔══╝  ",
        "███████╗",
        "╚══════╝",
    ],
    'F': [
        "███████╗",
        "██╔════╝",
        "█████╗  ",
        "██╔══╝  ",
        "██║     ",
        "╚═╝     ",
    ],
    'G': [
        " ██████╗ ",
        "██╔════╝ ",
        "██║  ███╗",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    'H': [
        "██╗  ██╗",
        "██║  ██║",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    'I': [
        "██╗",
        "██║",
        "██║",
        "██║",
        "██║",
        "╚═╝",
    ],
    'J': [
        "     ██╗",
        "     ██║",
        "     ██║",
        "██   ██║",
        "╚█████╔╝",
        " ╚════╝ ",
    ],
    'K': [
        "██╗  ██╗",
        "██║ ██╔╝",
        "█████╔╝ ",
        "██╔═██╗ ",
        "██║  ██╗",
        "╚═╝  ╚═╝",
    ],
    'L': [
        "██╗     ",
        "██║     ",
        "██║     ",
        "██║     ",
        "███████╗",
        "╚══════╝",
    ],
    'M': [
        "███╗   ███╗",
        "████╗ ████║",
        "██╔████╔██║",
        "██║╚██╔╝██║",
        "██║ ╚═╝ ██║",
        "╚═╝     ╚═╝",
    ],
    'N': [
        "███╗   ██╗",
        "████╗  ██║",
        "██╔██╗ ██║",
        "██║╚██╗██║",
        "██║ ╚████║",
        "╚═╝  ╚═══╝",
    ],
    'O': [
        " ██████╗ ",
        "██╔═══██╗",
        "██║   ██║",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    'P': [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔═══╝ ",
        "██║     ",
        "╚═╝     ",
    ],
    'Q': [
        " ██████╗ ",
        "██╔═══██╗",
        "██║   ██║",
        "██║██╗██║",
        "╚█████╔██╗",
        " ╚═══╝ ╚═╝",
    ],
    'R': [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔══██╗",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    'S': [
        "███████╗",
        "██╔════╝",
        "███████╗",
        "╚════██║",
        "███████║",
        "╚══════╝",
    ],
    'T': [
        "████████╗",
        "╚══██╔══╝",
        "   ██║   ",
        "   ██║   ",
        "   ██║   ",
        "   ╚═╝   ",
    ],
    'U': [
        "██╗   ██╗",
        "██║   ██║",
        "██║   ██║",
        "██║   ██║",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    'V': [
        "██╗   ██╗",
        "██║   ██║",
        "██║   ██║",
        "╚██╗ ██╔╝",
        " ╚████╔╝ ",
        "  ╚═══╝  ",
    ],
    'W': [
        "██╗    ██╗",
        "██║    ██║",
        "██║ █╗ ██║",
        "██║███╗██║",
        "╚███╔███╔╝",
        " ╚══╝╚══╝ ",
    ],
    'X': [
        "██╗  ██╗",
        "╚██╗██╔╝",
        " ╚███╔╝ ",
        " ██╔██╗ ",
        "██╔╝ ██╗",
        "╚═╝  ╚═╝",
    ],
    'Y': [
        "██╗   ██╗",
        "╚██╗ ██╔╝",
        " ╚████╔╝ ",
        "  ╚██╔╝  ",
        "   ██║   ",
        "   ╚═╝   ",
    ],
    'Z': [
        "███████╗",
        "╚══███╔╝",
        "  ███╔╝ ",
        " ███╔╝  ",
        "███████╗",
        "╚══════╝",
    ],
    '0': [
        " ██████╗ ",
        "██╔═████╗",
        "██║██╔██║",
        "████╔╝██║",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    '1': [
        " ██╗",
        "███║",
        "╚██║",
        " ██║",
        " ██║",
        " ╚═╝",
    ],
    '2': [
        "██████╗ ",
        "╚════██╗",
        " █████╔╝",
        "██╔═══╝ ",
        "███████╗",
        "╚══════╝",
    ],
    '3': [
        "██████╗ ",
        "╚════██╗",
        " █████╔╝",
        " ╚═══██╗",
        "██████╔╝",
        "╚═════╝ ",
    ],
    '4': [
        "██╗  ██╗",
        "██║  ██║",
        "███████║",
        "╚════██║",
        "     ██║",
        "     ╚═╝",
    ],
    '5': [
        "███████╗",
        "██╔════╝",
        "███████╗",
        "╚════██║",
        "███████║",
        "╚══════╝",
    ],
    '6': [
        " ██████╗ ",
        "██╔════╝ ",
        "███████╗ ",
        "██╔═══██╗",
        "╚██████╔╝",
        " ╚═════╝ ",
    ],
    '7': [
        "███████╗",
        "╚════██║",
        "    ██╔╝",
        "   ██╔╝ ",
        "   ██║  ",
        "   ╚═╝  ",
    ],
    '8': [
        " █████╗ ",
        "██╔══██╗",
        "╚█████╔╝",
        "██╔══██╗",
        "╚█████╔╝",
        " ╚════╝ ",
    ],
    '9': [
        " █████╗ ",
        "██╔══██╗",
        "╚██████║",
        " ╚═══██║",
        " █████╔╝",
        " ╚════╝ ",
    ],
}

# ============================================================================
# SUB-PIXEL RENDERING
# ============================================================================
# Each ASCII character cell becomes a SUB-GRID of sub-pixels.
# Width:Height ratio ~ 0.5 to match monospace cell aspect ratio.
# We use 4 wide x 6 tall so cells are taller than wide (like real monospace).

SUB_W = 4  # Sub-pixels wide per character cell
SUB_H = 6  # Sub-pixels tall per character cell
TX_LO = 1  # thin line lo X (middle band horizontally)
TX_HI = 3  # thin line hi X (exclusive)
TY_LO = 2  # thin line lo Y (middle band vertically)
TY_HI = 4  # thin line hi Y (exclusive)


def char_to_subgrid(ch):
    """Return sub-grid: set of (col, row) sub-pixel positions to fill (row 0 = top)."""
    pixels = set()

    if ch == '█':
        # Full block - all sub-pixels
        for c in range(SUB_W):
            for r in range(SUB_H):
                pixels.add((c, r))
    elif ch == '║':
        # Vertical line through entire cell, middle X-band
        for c in range(TX_LO, TX_HI):
            for r in range(SUB_H):
                pixels.add((c, r))
    elif ch == '═':
        # Horizontal line through entire cell, middle Y-band
        for r in range(TY_LO, TY_HI):
            for c in range(SUB_W):
                pixels.add((c, r))
    elif ch == '╔':
        # Top-left corner: line goes RIGHT and DOWN from corner
        for r in range(TY_LO, TY_HI):
            for c in range(TX_LO, SUB_W):
                pixels.add((c, r))
        for c in range(TX_LO, TX_HI):
            for r in range(TY_LO, SUB_H):
                pixels.add((c, r))
    elif ch == '╗':
        # Top-right corner: line goes LEFT and DOWN
        for r in range(TY_LO, TY_HI):
            for c in range(0, TX_HI):
                pixels.add((c, r))
        for c in range(TX_LO, TX_HI):
            for r in range(TY_LO, SUB_H):
                pixels.add((c, r))
    elif ch == '╚':
        # Bottom-left corner: line goes RIGHT and UP
        for r in range(TY_LO, TY_HI):
            for c in range(TX_LO, SUB_W):
                pixels.add((c, r))
        for c in range(TX_LO, TX_HI):
            for r in range(0, TY_HI):
                pixels.add((c, r))
    elif ch == '╝':
        # Bottom-right corner: line goes LEFT and UP
        for r in range(TY_LO, TY_HI):
            for c in range(0, TX_HI):
                pixels.add((c, r))
        for c in range(TX_LO, TX_HI):
            for r in range(0, TY_HI):
                pixels.add((c, r))
    # Space and unknown chars = empty cell

    return pixels


def render_glyph(lines):
    """
    Convert ASCII art lines into a 2D pixel grid using sub-pixel expansion.
    Returns: (grid_width, grid_height, set of (x, y) filled pixel coords with y=0 at TOP)
    """
    height_chars = len(lines)
    width_chars = max(len(line) for line in lines)

    # Pad lines to uniform width
    lines = [line.ljust(width_chars) for line in lines]

    grid_w = width_chars * SUB_W
    grid_h = height_chars * SUB_H

    filled = set()
    for line_idx, line in enumerate(lines):
        for col_idx, ch in enumerate(line):
            sub_pixels = char_to_subgrid(ch)
            for (sc, sr) in sub_pixels:
                x = col_idx * SUB_W + sc
                y = line_idx * SUB_H + sr
                filled.add((x, y))

    return grid_w, grid_h, filled


# ============================================================================
# TTF FONT BUILDING
# ============================================================================

PIXEL_UNIT = 50  # font units per sub-pixel
GLYPH_HEIGHT_CELLS = 6  # all glyphs are 6 lines tall
GLYPH_HEIGHT = GLYPH_HEIGHT_CELLS * SUB_H * PIXEL_UNIT  # 1800
ASCENT = GLYPH_HEIGHT
DESCENT = 0
UPM = 2048


def find_pixel_runs(filled, grid_w, grid_h):
    """
    Group adjacent filled pixels into horizontal runs per row, then merge
    vertically into rectangles. This reduces contour count.
    Simple greedy approach: per row, find horizontal runs.
    """
    rectangles = []
    for y in range(grid_h):
        x = 0
        while x < grid_w:
            if (x, y) in filled:
                start = x
                while x < grid_w and (x, y) in filled:
                    x += 1
                # Try to extend down: how many rows below also have this exact run filled?
                end = x
                height = 1
                while y + height < grid_h:
                    can_extend = True
                    for cx in range(start, end):
                        if (cx, y + height) not in filled:
                            can_extend = False
                            break
                    if not can_extend:
                        break
                    # Mark that band as consumed for vertical extension below
                    height += 1
                # We won't actually merge vertically here - let's keep it simple
                # and just emit one rect per row run. The visual is identical.
                rectangles.append((start, y, end, y + 1))
            else:
                x += 1
    return rectangles


def build_glyph(filled, grid_w, grid_h):
    """Build a TTF glyph from filled pixels."""
    pen = TTGlyphPen(None)
    rects = find_pixel_runs(filled, grid_w, grid_h)

    for (x0, y0, x1, y1) in rects:
        # Convert grid coords to font units
        # Grid y=0 is TOP; font y=0 is BOTTOM, so flip Y
        fx0 = x0 * PIXEL_UNIT
        fx1 = x1 * PIXEL_UNIT
        fy_top = (grid_h - y0) * PIXEL_UNIT
        fy_bot = (grid_h - y1) * PIXEL_UNIT

        # Draw filled rect CW (for TTF: outer outline clockwise to fill)
        pen.moveTo((fx0, fy_bot))
        pen.lineTo((fx0, fy_top))
        pen.lineTo((fx1, fy_top))
        pen.lineTo((fx1, fy_bot))
        pen.closePath()

    return pen.glyph()


def main():
    glyph_order = ['.notdef', 'space']
    cmap = {}
    glyphs = {}
    advance_widths = {}

    # .notdef
    pen = TTGlyphPen(None)
    pen.moveTo((50, 50))
    pen.lineTo((50, 1750))
    pen.lineTo((1000, 1750))
    pen.lineTo((1000, 50))
    pen.closePath()
    glyphs['.notdef'] = pen.glyph()
    advance_widths['.notdef'] = 1100

    # Space (4 cells wide)
    pen = TTGlyphPen(None)
    glyphs['space'] = pen.glyph()
    space_w = 4 * SUB_W * PIXEL_UNIT
    advance_widths['space'] = space_w
    cmap[ord(' ')] = 'space'

    for ch, lines in GLYPHS.items():
        grid_w, grid_h, filled = render_glyph(lines)
        glyph_name = ch if ch.isalpha() else f'num{ch}'
        if not ch.isalpha():
            glyph_name = {
                '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
                '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
            }[ch]
        glyph_order.append(glyph_name)

        glyphs[glyph_name] = build_glyph(filled, grid_w, grid_h)

        # Advance = grid width + 1 character cell of spacing
        adv = (grid_w + SUB_W) * PIXEL_UNIT
        advance_widths[glyph_name] = adv

        cmap[ord(ch)] = glyph_name
        if ch.isalpha():
            cmap[ord(ch.lower())] = glyph_name

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)

    metrics = {gn: (advance_widths.get(gn, 1000), 0) for gn in glyph_order}
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENT, descent=-DESCENT)

    fb.setupNameTable({
        "familyName": "Claudecade Shadow",
        "styleName": "Regular",
        "uniqueFontIdentifier": "ClaudecadeShadow-Regular-1.0",
        "fullName": "Claudecade Shadow Regular",
        "psName": "ClaudecadeShadow-Regular",
        "version": "Version 1.0",
    })
    fb.setupOS2(sTypoAscender=ASCENT, sTypoDescender=-DESCENT,
                usWinAscent=ASCENT, usWinDescent=DESCENT)
    fb.setupPost()

    out = str(Path(__file__).parent / "ClaudecadeShadow-Regular.ttf")
    fb.font.save(out)
    print(f"Font built: {out}")
    print(f"Glyphs: {len(glyph_order)}")
    print(f"Mapped chars: {len(cmap)}")


if __name__ == "__main__":
    main()
