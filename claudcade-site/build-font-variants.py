#!/usr/bin/env python3
"""Build the Claudecade font family.

Reads the SHADOW GLYPHS dict from build-font.py, then generates 6 derived
variants by transforming the sub-pixel bitmap before TTF emission:

    Outline   — only edge sub-pixels (interior hollow)
    Inline    — solid fill with a thin hollow stripe down the middle
    Striped   — alternating filled rows (CRT scanline)
    Dotted    — checkerboard (halftone)
    Italic    — geometric slant via shear on the outline coordinates
    Mono      — same shapes as Regular but with uniform advance width

Each variant is written to claudcade-site/Claudecade<Name>-Regular.ttf.
"""
import importlib.util, sys, math
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path('/Users/jeffmiddleton/Desktop/claudegames/claudcade-site')

# ── Load the SHADOW GLYPHS + sub-pixel renderer from build-font.py ────────────
spec = importlib.util.spec_from_file_location('build_font', ROOT / 'build-font.py')
bf   = importlib.util.module_from_spec(spec)
sys.modules['build_font'] = bf
spec.loader.exec_module(bf)

GLYPHS      = bf.GLYPHS
SUB_W       = bf.SUB_W
SUB_H       = bf.SUB_H
PIXEL_UNIT  = bf.PIXEL_UNIT
GLYPH_HEIGHT_CELLS = bf.GLYPH_HEIGHT_CELLS
GLYPH_HEIGHT = bf.GLYPH_HEIGHT
ASCENT      = bf.ASCENT
UPM         = bf.UPM
render_glyph = bf.render_glyph

# ── Variant transformations on the filled sub-pixel set ───────────────────────
def neighbors(p):
    x, y = p
    return [(x+dx, y+dy) for dx in (-1,0,1) for dy in (-1,0,1) if (dx,dy) != (0,0)]

def t_outline(filled, w, h):
    out = set()
    for p in filled:
        for n in neighbors(p):
            if n not in filled:
                out.add(p); break
    return out

def t_inline(filled, w, h):
    """Solid fill but with a 1-pixel hollow horizontal stripe at sub-pixel y % 6 == 2."""
    return {p for p in filled if not (p[1] % SUB_H == 2)}

def t_striped(filled, w, h):
    """Drop every other sub-pixel row (within each char cell)."""
    return {p for p in filled if (p[1] % 2) == 0}

def t_dotted(filled, w, h):
    """Checkerboard."""
    return {p for p in filled if ((p[0] + p[1]) % 2) == 0}

def t_identity(filled, w, h):
    return filled

# ── Outline-coordinate transform (for Italic) ─────────────────────────────────
def shear_glyph(filled, w, h, rectangles, shear):
    """Italic builds rectangles AS-IS but applies a shear at draw time."""
    return rectangles  # actual shear happens in build_glyph

# ── Glyph builders ────────────────────────────────────────────────────────────
def find_pixel_runs(filled, grid_w, grid_h):
    rectangles = []
    for y in range(grid_h):
        x = 0
        while x < grid_w:
            if (x, y) in filled:
                start = x
                while x < grid_w and (x, y) in filled:
                    x += 1
                rectangles.append((start, y, x, y + 1))
            else:
                x += 1
    return rectangles

def build_glyph(filled, grid_w, grid_h, shear=0.0):
    pen = TTGlyphPen(None)
    rects = find_pixel_runs(filled, grid_w, grid_h)
    for (x0, y0, x1, y1) in rects:
        fx0 = x0 * PIXEL_UNIT
        fx1 = x1 * PIXEL_UNIT
        fy_top = (grid_h - y0) * PIXEL_UNIT
        fy_bot = (grid_h - y1) * PIXEL_UNIT
        # Shear x by y (italic): x' = x + shear * y
        s = shear
        pen.moveTo((fx0 + s*fy_bot, fy_bot))
        pen.lineTo((fx0 + s*fy_top, fy_top))
        pen.lineTo((fx1 + s*fy_top, fy_top))
        pen.lineTo((fx1 + s*fy_bot, fy_bot))
        pen.closePath()
    return pen.glyph()

# ── Build one variant ─────────────────────────────────────────────────────────
def build_variant(name, transform, *, shear=0.0, mono=False, family='Claudecade'):
    glyph_order = ['.notdef', 'space']
    cmap = {}
    glyphs = {}
    advance_widths = {}

    # .notdef (placeholder square)
    pen = TTGlyphPen(None)
    pen.moveTo((50, 50)); pen.lineTo((50, 1750))
    pen.lineTo((1000, 1750)); pen.lineTo((1000, 50))
    pen.closePath()
    glyphs['.notdef'] = pen.glyph()
    advance_widths['.notdef'] = 1100

    # Space
    pen = TTGlyphPen(None)
    glyphs['space'] = pen.glyph()
    advance_widths['space'] = 4 * SUB_W * PIXEL_UNIT
    cmap[ord(' ')] = 'space'

    NUM_NAMES = {'0':'zero','1':'one','2':'two','3':'three','4':'four',
                 '5':'five','6':'six','7':'seven','8':'eight','9':'nine'}

    # Compute mono advance = max grid width of any glyph + 1 cell of space
    mono_adv = 0
    if mono:
        for ch, lines in GLYPHS.items():
            grid_w, _, _ = render_glyph(lines)
            mono_adv = max(mono_adv, grid_w)
        mono_adv = (mono_adv + SUB_W) * PIXEL_UNIT

    for ch, lines in GLYPHS.items():
        grid_w, grid_h, filled = render_glyph(lines)
        filled = transform(filled, grid_w, grid_h)
        gname  = ch if ch.isalpha() else NUM_NAMES[ch]
        glyph_order.append(gname)
        glyphs[gname] = build_glyph(filled, grid_w, grid_h, shear=shear)
        adv = mono_adv if mono else (grid_w + SUB_W) * PIXEL_UNIT
        advance_widths[gname] = adv
        cmap[ord(ch)] = gname
        if ch.isalpha():
            cmap[ord(ch.lower())] = gname

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    metrics = {gn: (advance_widths.get(gn, 1000), 0) for gn in glyph_order}
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASCENT, descent=0)

    family_full = f'Claudecade {name}'
    ps_name = f'Claudecade{name}-Regular'
    fb.setupNameTable({
        "familyName": family_full,
        "styleName":  "Regular",
        "uniqueFontIdentifier": f"{ps_name}-1.0",
        "fullName": f"{family_full} Regular",
        "psName":   ps_name,
        "version":  "Version 1.0",
    })
    fb.setupOS2(sTypoAscender=ASCENT, sTypoDescender=0,
                usWinAscent=ASCENT, usWinDescent=0)
    fb.setupPost()

    out = ROOT / f'{ps_name}.ttf'
    fb.font.save(out)
    return out

# ── Run them all ──────────────────────────────────────────────────────────────
VARIANTS = [
    ('Outline',  t_outline,  {}),
    ('Inline',   t_inline,   {}),
    ('Striped',  t_striped,  {}),
    ('Dotted',   t_dotted,   {}),
    ('Italic',   t_identity, {'shear': math.tan(math.radians(12))}),
    ('Mono',     t_identity, {'mono': True}),
]

if __name__ == '__main__':
    for name, transform, opts in VARIANTS:
        path = build_variant(name, transform, **opts)
        sz = path.stat().st_size
        print(f'  {path.name:34s}  {sz:>7,d} bytes')
    print('\nDone. 8 variants written to claudcade-site/.')
