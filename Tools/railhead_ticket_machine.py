"""Railhead's reference ticket machine: a recessed portrait LCD and separate payment column.

    rtk python Tools/railhead_ticket_machine.py

The 2048px PBR atlas has explicit UVs, readable DIN lettering, keypad legends,
contactless markings and independently lit screen/sign surfaces. Geometry uses
the existing 850 x 500 x 1800 mm machine footprint and one metal collision box.
"""
import argparse
import io
import math
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Assets/materials/railhead"
SIZE = 2048
BODY = "rw_ticket_machine"
METAL = "rw_ticket_machine_metal"
DISPLAY = "rw_ticket_machine_display"
RECTS = {
    "screen": (24, 24, 792, 1016),
    "header": (824, 24, 2024, 312),
    "body": (824, 344, 1360, 880),
    "metal": (1392, 344, 2024, 1008),
    "bezel": (824, 912, 1360, 1016),
    "tap": (24, 1048, 520, 1464),
    "receipt": (552, 1048, 1304, 1216),
    "qr": (1360, 1048, 1520, 1208),
    "card": (1552, 1048, 1712, 1240),
    "coins": (1744, 1048, 1920, 1224),
    "black": (24, 1496, 536, 2024),
    "lock": (568, 1496, 760, 1720),
    "lamp": (1552, 1296, 1776, 1360),
    "led": (1552, 1392, 1776, 1456),
    "dark_steel": (1552, 1496, 2024, 2024),
}
KEYS = (("1", "2", "3"), ("4", "5", "6"),
        ("7", "8", "9"), ("cancel", "0", "accept"))
for row, names in enumerate(KEYS):
    for col, name in enumerate(names):
        RECTS[name] = (792 + col * 248, 1296 + row * 176,
                       1008 + col * 248, 1440 + row * 176)
for i, (name, a) in enumerate(RECTS.items()):
    for other, b in list(RECTS.items())[i + 1:]:
        assert a[2] + 16 <= b[0] or b[2] + 16 <= a[0] or a[3] + 16 <= b[1] or b[3] + 16 <= a[1], (name, other)


def _uv(name, x, z):
    x0, y0, x1, y1 = RECTS[name]
    return (x0 + x * (x1 - x0)) / SIZE, 1 - (y1 - z * (y1 - y0)) / SIZE


def _face(model, F, bounds, entry="body", paint=BODY, radius=.04, texture_bounds=None):
    import railhead_props as P
    from railhead_card_reader import _outline
    x0, x1, y, z0, z1 = bounds
    points = ((x0, z0), (x1, z0), (x1, z1), (x0, z1)) if radius <= 0 else _outline(x0, x1, z0, z1, radius, steps=3)[0]
    a, b, c, d = texture_bounds or (x0, x1, z0, z1)
    P.outward(model, paint, [F.p(x, y, z) for x, z in points], F.y,
              uv=[_uv(entry, (x - a) / (b - a), (z - c) / (d - c)) for x, z in points])


def _solid(model, F, bounds, entry="body", paint=BODY, radius=.10, bevel=.035, front=True, back=True):
    """Rounded sheet-metal extrusion; the cabinet omits its face for actual recessed openings."""
    import railhead_props as P
    from railhead_card_reader import _outline
    x0, x1, y0, y1, z0, z1 = bounds
    radius = min(radius, (x1 - x0) / 2, (z1 - z0) / 2)
    bevel = min(bevel, radius * .7, (y1 - y0) / 2)
    rings = []
    for y, inset in ((y0, bevel), (y0 + bevel, 0), (y1 - bevel, 0), (y1, bevel)):
        points, normals = _outline(x0 + inset, x1 - inset, z0 + inset, z1 - inset, radius - inset, steps=3)
        rings.append((y, inset, points, normals))
    for a, b in zip(rings, rings[1:]):
        ya, ia, pa, na = a
        yb, ib, pb, nb = b
        dy, dr = yb - ya, ia - ib
        length = math.hypot(dy, dr)
        if length < 1e-9:
            continue
        for i in range(len(pa)):
            j = (i + 1) % len(pa)
            normals = [P._world(F, (ns[k][0] * dy / length, -dr / length, ns[k][1] * dy / length))
                       for ns, k in ((na, i), (na, j), (nb, j), (nb, i))]
            points = [F.p(*p) for p in ((pa[i][0], ya, pa[i][1]), (pa[j][0], ya, pa[j][1]),
                                        (pb[j][0], yb, pb[j][1]), (pb[i][0], yb, pb[i][1]))]
            P.outward(model, paint, points, sum(normals),
                      uv=[_uv(entry, u, v) for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))], normals=normals)
    for ring, direction in ((rings[0], -1), (rings[-1], 1)):
        if (direction == 1 and not front) or (direction == -1 and not back):
            continue
        y, _, points, _ = ring
        P.outward(model, paint, [F.p(x, y, z) for x, z in points], F.y * direction,
                  uv=[_uv(entry, (x - x0) / (x1 - x0), (z - z0) / (z1 - z0)) for x, z in points])


def _recess(model, F, outer, inner, front_y, back_y, entry="body", paint=BODY):
    """Four sloped reveals around a genuinely open rectangular pocket."""
    import railhead_props as P
    a, b, c, d = outer
    e, f, g, h = inner
    front = [(a, front_y, c), (b, front_y, c), (b, front_y, d), (a, front_y, d)]
    back = [(e, back_y, g), (f, back_y, g), (f, back_y, h), (e, back_y, h)]
    centre = F.p((a + b + e + f) / 4, (front_y + back_y) / 2, (c + d + g + h) / 4)
    for k in range(4):
        j = (k + 1) % 4
        pts = [F.p(*p) for p in (front[k], front[j], back[j], back[k])]
        # Inward-facing sides: their normal always looks into the pocket, toward its centre.
        P.outward(model, paint, pts, centre - np.mean(pts, axis=0),
                  uv=[_uv(entry, u, v) for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))])


def _plate_with_hole(model, F, bounds, hole, entry, paint=BODY):
    x0, x1, y, z0, z1 = bounds
    a, b, c, d = hole
    for lo, hi, bottom, top in ((x0, a, z0, z1), (b, x1, z0, z1),
                                (a, b, z0, c), (a, b, d, z1)):
        _face(model, F, (lo, hi, y, bottom, top), entry, paint, radius=0, texture_bounds=(x0, x1, z0, z1))


def _plate_with_holes(model, F, bounds, holes, entry, paint=BODY):
    x0, x1, y, z0, z1 = bounds
    heights = sorted({z0, z1, *(z for hole in holes for z in hole[2:])})
    for bottom, top in zip(heights, heights[1:]):
        active = sorted((a, b) for a, b, c, d in holes if c < (bottom + top) / 2 < d)
        start = x0
        for a, b in active + [(x1, x1)]:
            if a > start:
                _face(model, F, (start, a, y, bottom, top), entry, paint, radius=0, texture_bounds=(x0, x1, z0, z1))
            start = b


def _cap(model, F):
    import railhead_props as P
    profile = [(-11.25, 68), (8.5, 68), (8.5, 69.65), (-9.2, 71), (-11.25, 70.6)]
    for i, (y, z) in enumerate(profile):
        yn, zn = profile[(i + 1) % len(profile)]
        points = [F.p(*p) for p in ((-16.9, y, z), (16.9, y, z), (16.9, yn, zn), (-16.9, yn, zn))]
        P.outward(model, BODY, points, P._world(F, (0, zn - z, y - yn)),
                  uv=[_uv("body", u, v) for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))])
    for side in (-1, 1):
        P.outward(model, BODY, [F.p(side * 16.9, y, z) for y, z in profile], F.x * side,
                  uv=[_uv("body", (y + 11.25) / 19.75, (z - 68) / 3) for y, z in profile])


def build(model, F):
    """Front layout measured from the reference; unchanged footprint and height for the map."""
    for paint in (BODY, METAL, DISPLAY):
        model.material_overrides[paint] = f"materials/railhead/{paint}.vmat"
        model.tile_overrides[paint] = 1.0

    # Anthracite casing, inset kick plate, folded cap and thin front frame.
    _solid(model, F, (-15.7, 15.7, -10.5, 7.9, 0, 5.7), radius=.18, bevel=.08)
    _solid(model, F, (-16.7, 16.7, -11, 7.85, 5.7, 68), radius=.16, bevel=.06, front=False)
    _face(model, F, (-16.3, 16.3, 4.5, 5.8, 67.8), "black")
    for a, b in ((-16.7, -14.55), (15.55, 16.7)):
        _solid(model, F, (a, b, 7.65, 8.03, 5.7, 58), radius=.08)
    _cap(model, F)
    _solid(model, F, (-16.55, 16.55, 7.4, 8.2, 58, 68), radius=.12, bevel=.045)
    _solid(model, F, (-14.67, 14.67, 8.205, 8.28, 60.0, 66.95), "black", radius=.1, bevel=.02)
    _face(model, F, (-14.48, 14.48, 8.285, 60.17, 66.79), "header", DISPLAY, radius=.03)

    # The screen sits deep in a black bay, with a sloping sill and lit top hood.
    _recess(model, F, (-14.55, 7.4, 27.65, 57.95), (-13.1, 6.1, 28.75, 56.75), 8.0, 5.8)
    _face(model, F, (-13.1, 6.1, 5.79, 28.75, 56.75), "body")
    _solid(model, F, (-12.9, 5.9, 5.81, 5.98, 30.0, 54.5), "bezel", radius=.20, bevel=.05)
    _face(model, F, (-12.08, 5.08, 5.99, 31.45, 53.65), "screen", DISPLAY, radius=.015)
    for x in (-8.95, 2.0):
        _solid(model, F, (x - 1.67, x + 1.67, 6.55, 7.65, 57.44, 57.72), "dark_steel", METAL, radius=.08)
        _face(model, F, (x - 1.45, x + 1.45, 7.66, 57.49, 57.65), "lamp", DISPLAY, radius=.025)

    # Separate long payment door, with an inset reader and individual metal keys.
    _solid(model, F, (7.47, 15.53, 7.6, 8.0, 5.7, 57.95), "metal", METAL, radius=.09, bevel=.035, front=False, back=False)
    _plate_with_holes(model, F, (7.47, 15.53, 8.005, 5.7, 57.95),
                      ((9.12, 13.67, 34.15, 35.53), (9.16, 13.65, 26.22, 30.87),
                       (9.52, 13.37, 19.62, 21.03)), "metal", METAL)
    _solid(model, F, (8.17, 14.72, 8.01, 8.18, 36.95, 54.5), "black", radius=.22, bevel=.035)
    _solid(model, F, (8.62, 14.28, 8.19, 8.24, 46.35, 52.03), "bezel", radius=.12, bevel=.015)
    _face(model, F, (8.77, 14.13, 8.25, 46.5, 51.9), "tap", radius=.11)
    _solid(model, F, (10.17, 12.52, 8.19, 8.245, 52.9, 53.05), "led", DISPLAY, radius=.06, bevel=.012)
    for row, names in enumerate(KEYS):
        for col, name in enumerate(names):
            x, z = 9.55 + col * 1.82, 44.75 - row * 1.82
            _solid(model, F, (x - .74, x + .74, 8.18, 8.34, z - .72, z + .72),
                   "dark_steel", METAL, radius=.12, bevel=.03)
            _solid(model, F, (x - .67, x + .67, 8.34, 8.43, z - .64, z + .64),
                   "metal" if name not in ("cancel", "accept") else "body", METAL, radius=.09, bevel=.022)
            _face(model, F, (x - .64, x + .64, 8.437, z - .60, z + .60), name, METAL, radius=.07)

    # Card mouth: sheet-metal frame, bevels, deep black slot and separate guide rails.
    _solid(model, F, (8.65, 14.12, 8.03, 8.18, 33.75, 36.0), "dark_steel", METAL, radius=.23, front=False, back=False)
    _plate_with_hole(model, F, (8.79, 13.98, 8.185, 33.9, 35.85), (9.12, 13.67, 34.15, 35.53), "metal", METAL)
    _recess(model, F, (9.12, 13.67, 34.15, 35.53), (9.35, 13.43, 34.35, 35.30), 8.19, 6.7, "dark_steel", METAL)
    _face(model, F, (9.35, 13.43, 6.71, 34.35, 35.30), "black")
    _solid(model, F, (9.23, 13.55, 7.88, 8.2, 34.17, 34.32), "metal", METAL, radius=.04, bevel=.01)
    _face(model, F, (10.88, 12.10, 8.025, 31.88, 33.35), "card", METAL)

    # Banknote pocket, with four inclined metal faces and a dark throat.
    _solid(model, F, (8.65, 14.12, 8.02, 8.18, 22.93, 31.27), "metal", METAL, radius=.3, front=False, back=False)
    _plate_with_hole(model, F, (8.79, 13.98, 8.185, 23.08, 31.12), (9.16, 13.65, 26.22, 30.87), "metal", METAL)
    _recess(model, F, (9.16, 13.65, 26.22, 30.87), (9.66, 13.10, 26.90, 30.58), 8.19, 5.82, "metal", METAL)
    _face(model, F, (9.66, 13.10, 5.84, 26.90, 30.58), "black")
    _solid(model, F, (10.66, 12.15, 5.92, 6.22, 30.16, 30.44), "black", radius=.1)
    _face(model, F, (10.86, 12.2, 8.19, 23.63, 24.97), "qr", METAL, radius=.01)

    # Coin return below the banknote reader, with a recessed opening and stack pictogram.
    _solid(model, F, (8.93, 13.97, 8.02, 8.17, 17.32, 21.93), "black", radius=.17, front=False, back=False)
    _plate_with_hole(model, F, (9.07, 13.82, 8.185, 17.48, 21.79), (9.52, 13.37, 19.62, 21.03), "bezel")
    _recess(model, F, (9.52, 13.37, 19.62, 21.03), (9.72, 13.17, 19.77, 20.88), 8.19, 6.2, "black")
    _face(model, F, (9.72, 13.17, 6.21, 19.77, 20.88), "black")
    _face(model, F, (10.83, 12.07, 8.19, 17.77, 19.12), "coins", radius=.01)

    # The lower service door surrounds an open ticket dispenser, rather than a painted-on rectangle.
    _plate_with_hole(model, F, (-14.5, 7.35, 8.025, 5.7, 27.50), (-10.72, 5.34, 15.62, 22.85), "metal", METAL)
    _solid(model, F, (-10.8, 5.42, 8.04, 8.20, 15.55, 22.92), "black", radius=.18, front=False, back=False)
    _plate_with_hole(model, F, (-10.66, 5.28, 8.215, 15.7, 22.77), (-9.42, 4.06, 16.2, 19.67), "bezel")
    _face(model, F, (-8.62, 3.70, 8.23, 20.05, 22.21), "receipt", radius=.01)
    _recess(model, F, (-9.42, 4.06, 16.2, 19.67), (-9.14, 3.78, 16.42, 19.52), 8.22, 5.2, "dark_steel", METAL)
    _face(model, F, (-9.14, 3.78, 5.22, 16.42, 19.52), "black")
    _solid(model, F, (-9.24, 3.90, 5.3, 8.23, 16.25, 16.38), "metal", METAL, radius=.04, bevel=.012)
    _solid(model, F, (-9.40, 4.04, 8.18, 9.26, 15.86, 16.35), "dark_steel", METAL, radius=.06, bevel=.025)
    _solid(model, F, (-13.46, -11.48, 8.04, 8.19, 12.75, 15.15), "bezel", radius=.12, bevel=.02)
    _face(model, F, (-13.32, -11.62, 8.20, 12.93, 14.98), "lock", METAL, radius=.07)

    # One smooth metal collision box preserves the existing movement/navmesh footprint.
    F.collide(model, -16.7, 16.7, -11.0, 8.5, 0.0, 71.0, "metal")


def lights(F):
    """The two hood lamps: small local lights, without shadows or fog scattering."""
    return [(F.p(x, 6.95, 57.25), 10.0) for x in (-8.95, 2.0)]


def _font(size, bold=False):
    from PIL import ImageFont
    name = "Dinish-Bold.ttf" if bold else "Dinish-Regular.ttf"
    return ImageFont.truetype(str(ROOT / "Assets/fonts" / name), size)


def _text(draw, at, words, size, color, bold=False, anchor="mm"):
    draw.text(at, words, font=_font(size, bold), fill=color, anchor=anchor)


def _header():
    from PIL import Image, ImageDraw
    w, h = 1200, 288
    yy, xx = np.mgrid[:h, :w]
    glow = np.exp(-((xx - 360) / 750) ** 2 - ((yy - 146) / 200) ** 2)
    rgb = np.array((18, 55, 113)) + glow[..., None] * np.array((10, 30, 48))
    image = Image.fromarray(np.uint8(rgb))
    d = ImageDraw.Draw(image)
    white = (248, 251, 255)
    d.rounded_rectangle((74, 45, 190, 209), radius=27, fill=white)
    d.rounded_rectangle((88, 77, 177, 136), radius=5, fill=(23, 77, 142))
    d.rounded_rectangle((116, 56, 150, 65), radius=3, fill=(23, 77, 142))
    for x in (100, 166):
        d.ellipse((x - 9, 165, x + 9, 183), fill=(23, 77, 142))
    d.polygon(((98, 197), (112, 204), (80, 252), (60, 252)), fill=white)
    d.polygon(((165, 197), (151, 204), (184, 252), (205, 252)), fill=white)
    d.line((89, 229, 177, 229), fill=white, width=10)
    d.line((278, 42, 278, 253), fill=white, width=5)
    _text(d, (350, 112), "Fahrkarten", 175, white, bold=True, anchor="lm")
    _text(d, (355, 232), "Tickets  |  Billets  |  Biglietti", 64, white, anchor="lm")
    return image


def _icon(d, name, cx, cy, size, ink):
    if name == "location":
        d.ellipse((cx - size * .27, cy - size * .48, cx + size * .27, cy + size * .1), fill=ink)
        d.polygon(((cx - size * .23, cy - size * .06), (cx, cy + size * .43), (cx + size * .23, cy - size * .06)), fill=ink)
        d.ellipse((cx - size * .09, cy - size * .30, cx + size * .09, cy - size * .12), fill=(216, 226, 240))
    elif name == "return":
        for sign in (-1, 1):
            y = cy + sign * size * .18
            d.line((cx - size * .37, y, cx + size * .37, y), fill=ink, width=5)
            x = cx + sign * size * .37
            d.polygon(((x, y - size * .14), (x + sign * size * .17, y), (x, y + size * .14)), fill=ink)
    elif name == "clock":
        d.ellipse((cx - size * .42, cy - size * .42, cx + size * .42, cy + size * .42), fill=ink)
        d.line((cx, cy - size * .27, cx, cy, cx + size * .2, cy + size * .12), fill=(233, 240, 250), width=4)
    elif name == "group":
        for x, scale in ((cx - size * .22, .82), (cx + size * .19, 1.0)):
            r = size * .12 * scale
            d.ellipse((x - r, cy - size * .38, x + r, cy - size * .38 + r * 2), fill=ink)
            d.pieslice((x - size * .25 * scale, cy - size * .06, x + size * .25 * scale, cy + size * .55), 180, 360, fill=ink)
    elif name == "card":
        d.rounded_rectangle((cx - size * .44, cy - size * .29, cx + size * .44, cy + size * .29), radius=4, fill=ink)
        d.rectangle((cx - size * .44, cy - size * .15, cx + size * .44, cy - size * .07), fill=(234, 241, 251))
        d.line((cx - size * .30, cy + size * .17, cx - size * .04, cy + size * .17), fill=(234, 241, 251), width=3)
    else:
        for x in (-.28, 0, .28):
            r = size * .09
            d.ellipse((cx + size * x - r, cy - r, cx + size * x + r, cy + r), fill=ink)


def _flag(d, x, y, name):
    w, h = 74, 51
    if name == "de":
        for k, color in enumerate(((22, 24, 26), (193, 28, 34), (238, 186, 42))):
            d.rectangle((x, y + k * 17, x + w, y + (k + 1) * 17), fill=color)
    elif name in ("fr", "it"):
        colors = ((33, 81, 155), (240, 243, 243), (211, 45, 55)) if name == "fr" else ((31, 140, 81), (240, 243, 243), (211, 45, 55))
        for k, color in enumerate(colors):
            d.rectangle((x + k * w / 3, y, x + (k + 1) * w / 3, y + h), fill=color)
    elif name == "es":
        d.rectangle((x, y, x + w, y + h), fill=(189, 32, 44))
        d.rectangle((x, y + 13, x + w, y + 38), fill=(242, 190, 38))
        d.rectangle((x + 18, y + 21, x + 24, y + 31), fill=(159, 36, 54))
        d.line((x + 17, y + 19, x + 25, y + 19), fill=(159, 36, 54), width=2)
    else:
        d.rectangle((x, y, x + w, y + h), fill=(34, 63, 112))
        for a, b in (((x, y), (x + w, y + h)), ((x + w, y), (x, y + h))):
            d.line((*a, *b), fill=(238, 240, 245), width=11)
            d.line((*a, *b), fill=(199, 45, 51), width=4)
        d.rectangle((x + 29, y, x + 45, y + h), fill=(238, 240, 245))
        d.rectangle((x, y + 18, x + w, y + 33), fill=(238, 240, 245))
        d.rectangle((x + 33, y, x + 41, y + h), fill=(199, 45, 51))
        d.rectangle((x, y + 22, x + w, y + 29), fill=(199, 45, 51))


def _screen():
    from PIL import Image, ImageDraw
    w, h = 768, 992
    yy, xx = np.mgrid[:h, :w]
    glow = np.exp(-((xx - 615) / 530) ** 2 - ((yy - 520) / 450) ** 2)
    rgb = np.array((27, 50, 82)) + glow[..., None] * np.array((16, 37, 61))
    image = Image.fromarray(np.uint8(rgb))
    d = ImageDraw.Draw(image)
    # Faint station-roof drawing, behind the controls like the reference welcome page.
    roof = (61, 94, 130)
    for j in range(9):
        d.arc((-950 + j * 112, 99 + j * 32, 850 + j * 75, 1280 - j * 32), 259, 354, fill=roof, width=2)
    for j in range(15):
        d.line((135 + j * 62, 163, 900 - j * 57, 966), fill=roof, width=1)
    for j in range(10):
        d.line((0, 530 + j * 48, 768, 321 + j * 67), fill=roof, width=1)
    d.rectangle((0, 0, w, 107), fill=(30, 56, 92))
    d.rounded_rectangle((40, 29, 117, 86), radius=5, outline=(247, 251, 255), width=4)
    _text(d, (79, 59), "DB", 43, (247, 251, 255), bold=True)
    _text(d, (732, 59), "14:32", 34, (248, 250, 255), anchor="rm")
    _text(d, (40, 190), "Willkommen", 60, (248, 250, 255), bold=True, anchor="lm")
    _text(d, (40, 267), "Wohin soll es gehen?", 35, (244, 248, 253), anchor="lm")
    ink = (6, 20, 42)
    labels = (("location", "Ziel eingeben"), ("return", "Hin- und Rückfahrt"),
              ("clock", "Tageskarte"), ("group", "Gruppenkarte"),
              ("card", "BahnCard"), ("more", "Weitere Optionen"))
    for k, (name, words) in enumerate(labels):
        x, y = 36 + (k % 2) * 370, 342 + (k // 2) * 156
        d.rounded_rectangle((x, y, x + 355, y + 142), radius=9, fill=(188, 203, 224), outline=(221, 231, 245), width=2)
        _icon(d, name, x + 64, y + 70, 64, ink)
        size = 30
        while _font(size, bold=True).getlength(words) > 226:
            size -= 1
        _text(d, (x + 115, y + 71), words, size, ink, bold=True, anchor="lm")
    d.line((0, 848, 768, 848), fill=(148, 175, 203), width=2)
    for i, name in enumerate(("de", "uk", "fr", "it", "es")):
        _flag(d, 94 + i * 125, 896, name)
    return image


def _grain(w, h, entry, rng):
    from PIL import Image, ImageDraw
    yy, xx = np.mgrid[:h, :w]
    noise = rng.normal(0, 1, (h, w))
    metal = entry in ("metal", "dark_steel", "lock", "cancel", "accept") or entry in set("0123456789")
    if metal:
        value = 171 if entry == "metal" else 76 if entry == "dark_steel" else 167
        grain = rng.normal(0, 1.3, (1, w)) + noise * .8
        rgb = np.stack((value + grain, value + grain, value + grain + 1), axis=-1)
        rough = 160 + grain * 2
        height = grain * .015
    else:
        value = 24 if entry in ("body", "tap", "receipt", "coins", "card") else 12
        grain = noise * (1.5 if entry == "body" else .7)
        rgb = np.stack((value + grain, value + grain + 1, value + grain + 2), axis=-1)
        rough = 150 + noise * 4
        height = noise * .055
    tile = Image.fromarray(np.uint8(np.clip(rgb, 0, 255)))
    # Fine coating wear and sparse hairline scratches, without large high-contrast blotches.
    if entry in ("metal", "body", "dark_steel"):
        d = ImageDraw.Draw(tile)
        base = 148 if entry == "metal" else 17 if entry == "body" else 63
        for _ in range(30):
            x, y = rng.integers(0, w), rng.integers(0, h)
            length = rng.integers(3, 25)
            d.line((int(x), int(y), int(x + length * .18), int(y + length)), fill=(base, base + 1, base + 2), width=1)
    gy, gx = np.gradient(height)
    normals = np.stack((-gx, gy, np.ones_like(gx)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    return tile, np.uint8(np.clip(rough, 0, 255)), np.uint8(np.clip((normals * .5 + .5) * 255, 0, 255))


def _markings(tile, name):
    from PIL import ImageDraw
    d = ImageDraw.Draw(tile)
    w, h = tile.size
    white = (224, 230, 233)
    if name in set("0123456789"):
        _text(d, (w / 2, h / 2 + 2), name, 120, (24, 27, 29))
    elif name == "cancel":
        for a, b in (((74, 38), (143, 107)), ((143, 38), (74, 107))):
            d.line((*a, *b), fill=(216, 35, 40), width=16)
    elif name == "accept":
        d.line((62, 76, 96, 105, 155, 37), fill=(45, 174, 79), width=16, joint="curve")
    elif name == "tap":
        d.ellipse((65, 88, 323, 292), outline=white, width=5)
        for r in (24, 42, 60, 78):
            d.arc((157 - r, 190 - r, 157 + r, 190 + r), -45, 45, fill=white, width=10)
        d.rounded_rectangle((300, 159, 356, 207), radius=5, outline=white, width=4)
        d.line((313, 170, 342, 193), fill=white, width=3)
        d.line((385, 288, 361, 267, 347, 242, 315, 225, 313, 214, 321, 209, 346, 222,
                322, 198, 323, 189, 332, 185, 376, 224, 380, 214, 360, 195, 360, 186,
                370, 181, 395, 198, 415, 223, 439, 263), fill=white, width=5, joint="curve")
    elif name == "receipt":
        d.rectangle((39, 53, 137, 103), outline=white, width=4)
        d.line((51, 60, 51, 96), fill=white, width=4)
        d.line((125, 60, 125, 96), fill=white, width=4)
        _text(d, (175, 80), "Tickets & Belege", 59, white, anchor="lm")
    elif name == "card":
        d.rounded_rectangle((39, 23, 121, 170), radius=8, outline=white, width=5)
        d.rectangle((90, 38, 102, 57), outline=white, width=3)
        for x in (48, 110):
            for y in (40, 154):
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=white)
    elif name == "coins":
        for y in (74, 88, 102, 116):
            d.arc((49, y - 18, 128, y + 18), 0, 180, fill=white, width=4)
        d.ellipse((49, 37, 128, 73), outline=white, width=4)
        d.line((49, 55, 49, 116), fill=white, width=4)
        d.line((128, 55, 128, 116), fill=white, width=4)
    elif name == "lock":
        d.ellipse((43, 54, 149, 160), fill=(47, 50, 52), outline=(217, 223, 225), width=6)
        d.ellipse((75, 70, 119, 114), fill=(193, 198, 201))
        d.rectangle((91, 83, 103, 139), fill=(20, 23, 24))
    elif name == "qr":
        d.rectangle((0, 0, w, h), fill=(211, 213, 211))
        rng = np.random.default_rng(74831)
        grid = rng.integers(0, 2, (25, 25))
        for ox, oy in ((0, 0), (18, 0), (0, 18)):
            grid[oy:oy + 7, ox:ox + 7] = 1
            grid[oy + 1:oy + 6, ox + 1:ox + 6] = 0
            grid[oy + 2:oy + 5, ox + 2:ox + 5] = 1
        for y, x in zip(*np.where(grid)):
            d.rectangle((17 + int(x) * 5, 17 + int(y) * 5, 21 + int(x) * 5, 21 + int(y) * 5), fill=(37, 41, 40))


def vmat(metal=False, display=False):
    lines = ['// Tools/railhead_ticket_machine.py', '"Layer0"', '{',
             '    shader "shaders/complex.shader"', f'    F_SPECULAR "{0 if display else 1}"',
             '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{.25 if metal else 0:.2f}"']
    if display:
        lines += ['    F_SELF_ILLUM "1"',
                  '    TextureSelfIllumMask "materials/railhead/rw_ticket_machine_illum.png"',
                  '    g_flSelfIllumBrightness "0.35"', '    g_flSelfIllumAlbedoFactor "1.0"',
                  '    g_vSelfIllumTint "[1 1 1 0]"']
    lines += ['    TextureColor "materials/railhead/rw_ticket_machine_color.png"',
              '    TextureNormal "materials/railhead/rw_ticket_machine_normal.png"',
              '    TextureRoughness "materials/railhead/rw_ticket_machine_rough.png"',
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
              '    g_vColorTint "[1 1 1 1]"', '    g_flModelTintAmount "1.0"', '}']
    return '\n'.join(lines) + '\n'


def missing(out=OUT):
    return any(not (Path(out) / name).is_file() for name in
               ("rw_ticket_machine_color.png", "rw_ticket_machine_normal.png", "rw_ticket_machine_rough.png",
                "rw_ticket_machine_illum.png", "rw_ticket_machine.vmat", "rw_ticket_machine_metal.vmat",
                "rw_ticket_machine_display.vmat"))


def write(out=OUT):
    from PIL import Image
    import map_kit as K
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    color = Image.new("RGB", (SIZE, SIZE), (24, 25, 26))
    normal = Image.new("RGB", (SIZE, SIZE), (128, 128, 255))
    rough = Image.new("L", (SIZE, SIZE), 150)
    illum = Image.new("L", (SIZE, SIZE), 0)
    rng = np.random.default_rng(173911)
    for name, (x0, y0, x1, y1) in RECTS.items():
        w, h = x1 - x0, y1 - y0
        tile, rr, nn = _grain(w, h, name, rng)
        if name in ("screen", "header"):
            tile = _screen() if name == "screen" else _header()
            rr[:] = 45 if name == "screen" else 77
            nn[:] = (128, 128, 255)
            illum.paste(255, (x0, y0, x1, y1))
        elif name in ("lamp", "led"):
            tile = Image.new("RGB", (w, h), (248, 231, 203) if name == "lamp" else (46, 98, 246))
            rr[:] = 45
            nn[:] = (128, 128, 255)
            illum.paste(255, (x0, y0, x1, y1))
        else:
            _markings(tile, name)
        for atlas, patch in ((color, tile), (rough, Image.fromarray(rr)), (normal, Image.fromarray(nn))):
            atlas.paste(patch, (x0, y0))
            atlas.paste(patch.crop((0, 0, 1, h)).resize((8, h)), (x0 - 8, y0))
            atlas.paste(patch.crop((w - 1, 0, w, h)).resize((8, h)), (x1, y0))
            atlas.paste(patch.crop((0, 0, w, 1)).resize((w, 8)), (x0, y0 - 8))
            atlas.paste(patch.crop((0, h - 1, w, h)).resize((w, 8)), (x0, y1))
    for name, atlas in (("color", color), ("normal", normal), ("rough", rough), ("illum", illum)):
        buffer = io.BytesIO()
        atlas.save(buffer, format="PNG", optimize=True)
        data = buffer.getvalue()
        path = out / f"rw_ticket_machine_{name}.png"
        if path.exists() and path.read_bytes() == data:
            continue
        temporary = path.with_name(path.name + ".writing")
        temporary.write_bytes(data)
        for attempt in range(20):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(.5)
    for metal, display, name in ((False, False, BODY), (True, False, METAL), (False, True, DISPLAY)):
        K.write_text(out / f"{name}.vmat", vmat(metal, display))
    print(f"wrote ticket machine: {len(RECTS)} atlas entries, three materials, {SIZE}px")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    write(ap.parse_args().out)


if __name__ == "__main__":
    main()
