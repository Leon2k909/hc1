"""Reference double-decker: sliding doors, glazed saloons and authored PBR trim.

The train stays part of Railhead's static dressing. All sizes are in the car's
local (across, depth, height) frame; the visible saloons are decorative, while
the existing platform-side vestibules retain their playable collision.

    rtk python Tools/railhead_train.py       # deterministic materials only
"""
import io
import math
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Assets/materials/railhead"
SIZE = 2048
DETAIL = "rw_emu_details"
METAL = "rw_emu_metal"
INSIDE = "rw_emu_interior"
DECAL = "rw_emu_decals"
LIT = "rw_emu_lit"
GLASS = "rw_emu_glass"
RED = "rw_emu_red"
BLUE = "rw_emu_blue"
PAINTS = (DETAIL, METAL, INSIDE, DECAL, LIT, GLASS, RED, BLUE)
RECTS = {
    "metal": (16, 16, 496, 1008),
    "wall": (512, 16, 992, 1008),
    "seat": (1008, 16, 1504, 752),
    "head": (1520, 16, 2032, 504),
    "dark": (1520, 520, 2032, 1008),
    "door_markings": (16, 1040, 208, 1856),
    "access": (224, 1040, 448, 1760),
    "db": (464, 1040, 688, 1200),
    "destination": (704, 1040, 1488, 1216),
    "number": (464, 1232, 1488, 1296),
    "poster": (1520, 1040, 1712, 1360),
    "map": (1728, 1040, 2032, 1360),
    "floor": (464, 1312, 992, 1840),
    "lamp": (1008, 1312, 1488, 1376),
    "button": (1008, 1392, 1120, 1504),
    "threshold": (1136, 1392, 1488, 1456),
    "emergency": (1136, 1472, 1312, 1680),
    "class": (1328, 1472, 1488, 1680),
}


def uv(entry, u, v):
    a, b, c, d = RECTS[entry]
    return (a + u * (c - a)) / SIZE, 1 - (d - v * (d - b)) / SIZE


def _poly(car, paint, pts, normal, entry=None, coords=None, normals=None):
    import railhead_props as P
    tex = None if entry is None else [uv(entry, *p) for p in (coords or ((0, 0), (1, 0), (1, 1), (0, 1)))]
    P.outward(car.model, paint, [car.p(*p) for p in pts], P._world(car.F, car.local(normal)), uv=tex,
              normals=None if normals is None else [P._world(car.F, car.local(n)) for n in normals])


def box(car, bounds, entry="wall", paint=INSIDE, skip=()):
    x0, x1, d0, d1, z0, z1 = bounds
    faces = (
        ("-x", (-1, 0, 0), ((x0, d0, z0), (x0, d1, z0), (x0, d1, z1), (x0, d0, z1))),
        ("+x", (1, 0, 0), ((x1, d0, z0), (x1, d1, z0), (x1, d1, z1), (x1, d0, z1))),
        ("-d", (0, -1, 0), ((x0, d0, z0), (x1, d0, z0), (x1, d0, z1), (x0, d0, z1))),
        ("+d", (0, 1, 0), ((x0, d1, z0), (x1, d1, z0), (x1, d1, z1), (x0, d1, z1))),
        ("-z", (0, 0, -1), ((x0, d0, z0), (x1, d0, z0), (x1, d1, z0), (x0, d1, z0))),
        ("+z", (0, 0, 1), ((x0, d0, z1), (x1, d0, z1), (x1, d1, z1), (x0, d1, z1))),
    )
    for key, normal, pts in faces:
        if key not in skip:
            _poly(car, paint, pts, normal, entry)


def outline(a, b, lo, hi, radius, steps=6):
    """A counter-clockwise rounded rectangle, including tangent vertices."""
    from railhead_card_reader import _outline
    return _outline(a, b, lo, hi, min(radius, (b - a) / 2, (hi - lo) / 2), steps=steps)


def _face(car, xs, x, d0, d1, z0, z1, entry, paint=DETAIL, radius=0):
    pts = outline(d0, d1, z0, z1, radius)[0] if radius else ((d0, z0), (d1, z0), (d1, z1), (d0, z1))
    sd = xs * car.s
    coords = [(((d - d0) / (d1 - d0)) if sd > 0 else ((d1 - d) / (d1 - d0)),
               (z - z0) / (z1 - z0)) for d, z in pts]
    _poly(car, paint, [(x, d, z) for d, z in pts], (xs, 0, 0), entry, coords)


def _rim(car, xs, rings, paint=DETAIL, entry="dark", smooth=False):
    """Rings are (across, depth min/max, height min/max, corner radius)."""
    for a, b in zip(rings, rings[1:]):
        xa, da, db, za, zb, ra = a
        xb, dc, dd, zc, zd, rb = b
        pa, na = outline(da, db, za, zb, ra)
        pb, nb = outline(dc, dd, zc, zd, rb)
        for k in range(len(pa)):
            j = (k + 1) % len(pa)
            pts = [(xa, *pa[k]), (xa, *pa[j]), (xb, *pb[j]), (xb, *pb[k])]
            centre = np.mean(pts, axis=0)
            # Across-facing bevels; the deep inner reveal faces into the opening.
            normal = np.array((xs, 0, 0))
            if abs(da - dc) < .001 and abs(za - zc) < .001:
                normal = np.array((0, (da + db) / 2 - centre[1], (za + zb) / 2 - centre[2]))
            ns = None
            if smooth:
                width = max(abs(dc - da), abs(zc - za), .01)
                rise = abs(xb - xa)
                ns = [(xs * width, n[0] * rise, n[1] * rise)
                      for n in (na[k], na[j], nb[j], nb[k])]
                ns = [tuple(np.asarray(n) / np.linalg.norm(n)) for n in ns]
            _poly(car, paint, pts, normal, entry, normals=ns)


def _corner_fill(car, xs, x, bounds, radius, body):
    """Keep the shell outside each rounded aperture, without a rectangle behind its glass."""
    d0, d1, z0, z1 = bounds
    pts, _ = outline(d0, d1, z0, z1, radius)
    count = len(pts) // 4
    corners = ((d1, z0), (d1, z1), (d0, z1), (d0, z0))
    # _outline starts at bottom-right, traversing right/top/left/bottom.
    for k, corner in enumerate(corners):
        arc = pts[k * count:(k + 1) * count]
        _poly(car, body, [(x, *corner), *[(x, *p) for p in arc]], (xs, 0, 0))


def window(car, xs, d0, d1, z0, z1, body):
    import railhead_props as P
    W = P.EMU_W
    outside = (d0 - 1.7, d1 + 1.7, z0 - 1.7, z1 + 1.7)
    _corner_fill(car, xs, xs * W, outside, 4.7, body)
    _rim(car, xs, ((xs * W, *outside, 4.7),
                   (xs * (W + .48), d0 - .95, d1 + .95, z0 - .95, z1 + .95, 4.0),
                   (xs * (W + .38), d0, d1, z0, z1, 3.5),
                   (xs * (W - 1.85), d0, d1, z0, z1, 3.5)))
    # A glossy black frame band just inside the gasket, 60 mm, then the glass 40 mm back from the body's skin.
    _rim(car, xs, ((xs * (W + .40), d0 + .15, d1 - .15, z0 + .15, z1 - .15, 3.4),
                   (xs * (W - 1.5), d0 + 2.0, d1 - 2.0, z0 + 2.0, z1 - 2.0, 2.0)), METAL, "dark")
    # Separate no-shadow glazing model: the saloon really exists behind it.
    _face(car, xs, xs * (W - 1.6), d0 + 1.9, d1 - 1.9, z0 + 1.9, z1 - 1.9, "dark", GLASS, radius=2.0)
    # Thin interior gasket visible on oblique views.
    _rim(car, -xs, ((xs * (W - 1.95), d0 - .45, d1 + .45, z0 - .45, z1 + .45, 3.9),
                    (xs * (W - 2.0), d0, d1, z0, z1, 3.5)))


def rounded_solid(car, bounds, axis="d", radius=1.2, bevel=.35, entry="seat", paint=INSIDE):
    """Soft bevels on seat cushions, seat backs, headrests and door hardware."""
    x0, x1, d0, d1, z0, z1 = bounds
    # Map a rounded section (u,v) and its extrusion coordinate t to car space.
    if axis == "d":
        a, b, lo, hi, t0, t1 = x0, x1, z0, z1, d0, d1
        point = lambda u, t, v: (u, t, v)
        vec = lambda u, t, v: (u, t, v)
    elif axis == "x":
        a, b, lo, hi, t0, t1 = d0, d1, z0, z1, x0, x1
        point = lambda u, t, v: (t, u, v)
        vec = lambda u, t, v: (t, u, v)
    else:
        a, b, lo, hi, t0, t1 = x0, x1, d0, d1, z0, z1
        point = lambda u, t, v: (u, v, t)
        vec = lambda u, t, v: (u, v, t)
    radius = min(radius, (b - a) / 2, (hi - lo) / 2)
    bevel = min(bevel, radius * .6, (t1 - t0) / 2)
    rings = []
    for t, inset in ((t0, bevel), (t0 + bevel, 0), (t1 - bevel, 0), (t1, bevel)):
        ps, ns = outline(a + inset, b - inset, lo + inset, hi - inset, radius - inset, steps=3)
        rings.append((t, inset, ps, ns))
    for ra, rb in zip(rings, rings[1:]):
        ta, ia, pa, na = ra
        tb, ib, pb, nb = rb
        dt, di = tb - ta, ia - ib
        length = math.hypot(dt, di)
        if length < 1e-8:
            continue
        for k in range(len(pa)):
            j = (k + 1) % len(pa)
            ns = [vec(n[0] * dt / length, -di / length, n[1] * dt / length)
                  for n in (na[k], na[j], nb[j], nb[k])]
            ps = [point(*p) for p in ((pa[k][0], ta, pa[k][1]), (pa[j][0], ta, pa[j][1]),
                                     (pb[j][0], tb, pb[j][1]), (pb[k][0], tb, pb[k][1]))]
            _poly(car, paint, ps, np.sum(ns, axis=0), entry, normals=ns)
    for ring, sign in ((rings[0], -1), (rings[-1], 1)):
        t, _, ps, _ = ring
        _poly(car, paint, [point(u, t, v) for u, v in ps], vec(0, sign, 0), entry,
              [((u - a) / (b - a), (v - lo) / (hi - lo)) for u, v in ps])


def seat(car, x, d, floor, forward):
    # Individual upholstery, inset headrest and separate plastic shell/support.
    back = d - forward * 7.8
    rounded_solid(car, (x - 8.8, x + 8.8, d - 8, d + 8, floor + 15, floor + 18.4),
                  axis="z", radius=2.1, bevel=.7)
    rounded_solid(car, (x - 8.6, x + 8.6, back - 1.5, back + 1.5, floor + 16, floor + 43.5),
                  radius=2.7, bevel=.55, entry="head")
    front = back + forward * 1.7
    lo, hi = sorted((front, front + forward * .9))
    rounded_solid(car, (x - 7.85, x + 7.85, lo, hi, floor + 19, floor + 40.7),
                  radius=2.4, bevel=.35)
    rounded_solid(car, (x - 7.2, x + 7.2, back - 2.4, back + 2.4, floor + 39.5, floor + 48),
                  radius=2.4, bevel=.6, entry="head")
    box(car, (x - 2.6, x + 2.6, d - 4, d + 4, floor, floor + 15), "dark", DETAIL, skip=("-z", "+z"))
    for side in (-1, 1):
        rounded_solid(car, (x + side * 8.3 - .8, x + side * 8.3 + .8,
                            d - 4.5, d + 6.5, floor + 23.5, floor + 25.2),
                      axis="z", radius=.7, bevel=.35, entry="head")


def saloon(car, d0, d1, floor, ceiling, rows):
    # Sealed decorative saloons do not change collision or expose playable voids.
    box(car, (-55.3, 55.3, d0, d1, floor - 1, floor), "floor", INSIDE, skip=("-z",))
    box(car, (-55.3, 55.3, d0, d1, ceiling, ceiling + 1), "wall", INSIDE, skip=("+z",))
    for d in (d0, d1):
        box(car, (-55.3, 55.3, d - .3, d + .3, floor, ceiling), "wall", INSIDE)
    for index, d in enumerate(rows):
        for x in (-38, -19, 19, 38):
            seat(car, x, d, floor, 1 if index < len(rows) / 2 else -1)
    # Visible strip luminaires and overhead luggage shelves.
    for xs in (-1, 1):
        a, b = sorted((xs * 36, xs * 48))
        box(car, (a, b, d0 + 3, d1 - 3, ceiling - 10.0, ceiling - 9.5), "metal", METAL)
        a, b = sorted((xs * 13, xs * 14.4))
        box(car, (a, b, d0 + 3, d1 - 3, ceiling - 4.5, ceiling - 4.0), "lamp", LIT)


def interior(car):
    saloon(car, 315, 535, 23, 94, (342, 375, 408, 442, 475, 508))
    saloon(car, 315, 535, 99, 168, (342, 375, 408, 442, 475, 508))
    saloon(car, 624, 758, 49, 124, (640, 674, 708, 742))
    saloon(car, 116, 215, 49, 124, (137, 170, 201))


def underframe(car):
    """What shows round each bogie in its cut-out: a dark bulkhead between the wheels (so the gap doesn't show the far
    side), the body's sole bar along the cut-out's top, and a cable tray and brake pipe along under it. The bogie
    itself (railhead_running_gear) stands in the open in front of the bulkhead."""
    import railhead_props as P
    portals = [(d - 1, d + 65) for d in P.EMU_DOORS]
    def clipped_box(bounds, entry="dark", paint=DETAIL):
        x0, x1, d0, d1, z0, z1 = bounds
        for lo, hi in P._subtract((d0, d1), portals):
            box(car, (x0, x1, lo, hi, z0, z1), entry, paint)
    for centre in P.EMU_BOGIES:
        for xs in (-1, 1):
            # The bulkhead in the bogie's dust tone (not black), so the side frame's fish belly shows against it.
            a, b = sorted((xs * 19.0, xs * 20.0))
            clipped_box((a, b, centre - 66, centre + 66, 8, P.EMU_CUT), "metal", "rw_bogie_dust")
            a, b = sorted((xs * (P.EMU_W - 14), xs * (P.EMU_W - 9)))
            clipped_box((a, b, centre - 62, centre + 62, 37, P.EMU_CUT))
            # The cable tray and the brake pipe running along under the sole bar.
            a, b = sorted((xs * (P.EMU_W - 18), xs * (P.EMU_W - 15)))
            clipped_box((a, b, centre - 62, centre + 62, 33.5, 36.5), "metal", METAL)
            car.rod((xs * (P.EMU_W - 20.5), centre - 62, 35.0), (xs * (P.EMU_W - 20.5), centre + 62, 35.0), .55,
                    "rw_steel_dark", 6)


def _door_leaf(car, xs, d0, d1, right):
    import railhead_props as P
    W = P.EMU_W
    x0, x1 = sorted((xs * (W + .13), xs * (W + 1.65)))
    # Folded panel edges and real black rebate around the narrow glass insert.
    box(car, (x0, x1, d0, d1, 30.3, 129.4), "metal", METAL)
    x = xs * (W + 1.68)
    a, b, lo, hi = d0 + 6.2, d1 - 6.2, 64.2, 118.8
    _rim(car, xs, ((x, a - .8, b + .8, lo - .8, hi + .8, 1.9),
                   (x + xs * .15, a, b, lo, hi, 1.3)))
    _face(car, xs, x + xs * .12, a, b, lo, hi,
          "door_markings" if right else "dark", DETAIL, radius=1.3)
    # Door opening button on the edge nearest the open portal, with metal surround.
    edge = d0 + 3.0 if right == (xs * car.s > 0) else d1 - 3.0
    for radius, paint, offset in ((1.55, METAL, .13), (1.22, DETAIL, .20)):
        pts = [(edge + radius * math.cos(t), 86.0 + radius * math.sin(t))
               for t in np.linspace(0, math.tau, 25)[:-1]]
        _poly(car, paint, [(x + xs * offset, d, z) for d, z in pts], (xs, 0, 0),
              "metal" if paint == METAL else "dark",
              [((d - edge) / radius / 2 + .5, (z - 86) / radius / 2 + .5) for d, z in pts])
    _face(car, xs, x + xs * .23, edge - .86, edge + .86, 85.14, 86.86, "button", LIT, radius=.85)
    rounded_solid(car, (min(x + xs * .15, x + xs * .85), max(x + xs * .15, x + xs * .85),
                       edge - .5, edge + .5, 71, 82.0), axis="x", radius=.45, bevel=.12,
                  entry="metal", paint=METAL)
    # Recessed grip, lower sliding guide and small fixing screws.
    _face(car, xs, x + xs * .87, edge - .2, edge + .2, 72.1, 81.0, "dark")
    for z in (33.0, 126.4):
        for d in (d0 + 1.2, d1 - 1.2):
            car.disc("rw_steel_grey", (x + xs * .025, d, z), (xs, 0, 0), .20, 8)


def doorway(car, xs, d0, d1, opened=False):
    import railhead_props as P
    W = P.EMU_W
    mid, width = (d0 + d1) / 2, (d1 - d0) / 2
    sd = xs * car.s
    if opened:
        leaves = ((d0 - width, d0), (d1, d1 + width))
    else:
        leaves = ((d0, mid - .14), (mid + .14, d1))
    for lo, hi in leaves:
        right = (lo + hi) / 2 > mid if sd > 0 else (lo + hi) / 2 < mid
        _door_leaf(car, xs, lo, hi, right)
        if opened:
            car.collide(xs * W, xs * (W + 1.65), lo, hi, 30.3, 129.4)
    # Outer door seal and the pocket into which the leaves slide.
    x = xs * (W + .05)
    _rim(car, xs, ((x, d0 - 1.4, d1 + 1.4, 29.4, 131.4, 1.6),
                   (x + xs * .12, d0, d1, 30, 130, .6)))
    # The step plate under the doorway, 40 mm out from the skin, chequered stainless with a yellow nosing line.
    a, b = sorted((xs * (W - .2), xs * (W + 1.75)))
    box(car, (a, b, d0 - 2.0, d1 + 2.0, 28.6, 29.5), "metal", METAL)
    a, b = sorted((xs * (W + 1.55), xs * (W + 1.78)))
    box(car, (a, b, d0 - 2.0, d1 + 2.0, 28.75, 29.35), "threshold", DETAIL, skip=("-z",))
    if not opened:
        # Rubber meeting seals: black lips along both leaves' leading edges, proud of the leaves, and the narrow centre
        # joint behind them, which must not leave a slit through to the opposite side of the train.
        a, b = sorted((xs * (W + 1.2), xs * (W + 1.56)))
        box(car, (a, b, mid - .21, mid + .21, 30.0, 130.0), "dark", DETAIL)
        a, b = sorted((xs * (W + 1.5), xs * (W + 1.95)))
        for lo_, hi_ in ((mid - .95, mid - .14), (mid + .14, mid + .95)):
            box(car, (a, b, lo_, hi_, 30.6, 129.2), "dark", DETAIL, skip=("-z",))
        return
    # The reveal and ceiling point into the open passage, not out through the skin.
    # The back panel matches the existing centre-line collision boundary.
    near, far = xs * (W - .2), 0.0
    a, b = sorted((near, far))
    for d, normal in ((d0 + .25, (0, 1, 0)), (d1 - .25, (0, -1, 0))):
        _poly(car, INSIDE, [(near, d, 30), (far, d, 38), (far, d, 128), (near, d, 130)], normal, "wall")
        # Stainless inner jambs, panel breaks and a dark overhead duct.
        box(car, (min(xs * (W - 3), xs * (W - 1)), max(xs * (W - 3), xs * (W - 1)),
                  d - .45, d + .45, 30.3, 129.5), "metal", METAL)
    box(car, (a, b, d0 + .2, d1 - .2, 128, 130), "wall", INSIDE, skip=("+z",))
    # A shallow two-step vestibule, with metal nosings and a bright safety threshold.
    floor_sections = ((W - 16, W, 30), (W - 29, W - 16, 34), (0, W - 29, 38))
    for f0, f1, top in floor_sections:
        q0, q1 = sorted((xs * f0, xs * f1))
        box(car, (q0, q1, d0 + .4, d1 - .4, 27.5, top), "floor", INSIDE, skip=("-z",))
        nose = xs * f1
        q0, q1 = sorted((nose - xs * .45, nose))
        box(car, (q0, q1, d0 + .5, d1 - .5, top + .02, top + .10), "metal", METAL)
        if f0 >= 0:
            car.collide(xs * f0, xs * f1, d0, d1, 27.5, top)
        else:
            car.collide(0, xs * f1, d0, d1, 27.5, top)
    _poly(car, DETAIL, [(xs * (W + .05), d0, 30.18), (xs * (W + 1.45), d0, 30.18),
                        (xs * (W + 1.45), d1, 30.18), (xs * (W + .05), d1, 30.18)],
          (0, 0, 1), "threshold", ((0, 0), (0, 1), (1, 1), (1, 0)))
    # Opposite internal door: inset silver leaves, a rounded narrow window and seam.
    box(car, (far - .2, far + .2, d0 + .3, d1 - .3, 38, 128), "wall", INSIDE)
    doorx = far + xs * .25
    _face(car, xs, doorx, mid - 22.0, mid + 22.0, 39, 119.8, "dark", radius=.7)
    _face(car, xs, doorx + xs * .08, mid - 21.3, mid + 21.3, 39.6, 119.0, "metal", METAL, radius=.4)
    _face(car, xs, doorx + xs * .13, mid - .12, mid + .12, 39.6, 119.0, "dark")
    _rim(car, xs, ((doorx + xs * .18, mid - 7.5, mid + 7.5, 62.7, 108.0, 2.8),
                   (doorx + xs * .28, mid - 6.9, mid + 6.9, 63.3, 107.4, 2.4)))
    _face(car, xs, doorx + xs * .24, mid - 6.9, mid + 6.9, 63.3, 107.4, "dark", radius=2.4)
    for d, entry, z0, z1, w in ((mid - 26.6, "poster", 83, 104, 6.7),
                               (mid + 26.6, "map", 94, 111, 7.5),
                               (mid + 26.6, "emergency", 83, 92, 6.5)):
        _face(car, xs, doorx + xs * .27, d - w / 2, d + w / 2, z0, z1, entry, INSIDE)
    box(car, (min(doorx, doorx + xs * .8), max(doorx, doorx + xs * .8),
              mid - 12.3, mid - 11.4, 67, 75), "metal", METAL)
    # Four yellow grab poles, rounded collars, and waist-height inward rails.
    for depth, inset in ((W - 5.5, 4.2), (W - 20, 7.0), (6.5, 6.2)):
        for d in (d0 + inset, d1 - inset):
            car.rod((xs * depth, d, 38 if depth < W - 29 else 30),
                    (xs * depth, d, 126.8), .60, "rw_yellow_paint", 16, (True, True))
            for z in (42, 124):
                car.rod((xs * depth, d, z - .45), (xs * depth, d, z + .45), .76, "rw_steel_dark", 12)
            if depth == W - 20:
                car.rod((xs * depth, d, 76), (xs * (depth - 8), d, 76), .57, "rw_yellow_paint", 12)
    # Broad ceiling fitting, light diffuser, and a small smoke detector.
    q0, q1 = sorted((xs * (W - 25), xs * (W - 9)))
    box(car, (q0, q1, d0 + 4, d1 - 4, 126.0, 127.6), "metal", METAL)
    box(car, (q0 + .6, q1 - .6, d0 + 5, d1 - 5, 125.8, 126.0), "lamp", LIT)
    car.rod((xs * 4, mid, 126.9), (xs * 4, mid, 128), 1.7, "rw_train_white", 16, (True, True))
    car.rod((xs * 4, mid, 126.4), (xs * 4, mid, 126.9), .7, "rw_steel_dark", 12, (True, True))


def markings(car, xs, doors):
    import railhead_props as P
    # Layout is measured relative to each portal, so both ends and sides read correctly.
    for index, (d0, d1) in enumerate(doors):
        mid = (d0 + d1) / 2
        # Door leaves are 32 in; the accessibility panel sits immediately to their left.
        end_direction = 1 if index == 1 else -1
        left = mid - end_direction * 74
        _face(car, xs, xs * (P.EMU_W + .13), left - 5.4, left + 5.4,
              75 if index == 1 else 89, 111 if index == 1 else 119, "access", DECAL)
        right = mid + end_direction * (82 if index == 1 else 74)
        # At the first portal, this lies on the double deck rather than the high end saloon.
        logo_z = 113 if index == 1 else 104
        _face(car, xs, xs * (P.EMU_W + .15), right - 9.4, right + 9.4,
              logo_z - 6.7, logo_z + 6.7, "db", DECAL)
        bike = mid + end_direction * (80 if index == 1 else 74)
        P._emu_bicycle(car, xs, bike, 68)
        sign = mid + 121 if index == 1 else 156
        _face(car, xs, xs * (P.EMU_W + .27), sign - 42, sign + 42, 137, 153,
              "destination", LIT, radius=1.3)
        _rim(car, xs, ((xs * (P.EMU_W + .10), sign - 42.6, sign + 42.6, 136.4, 153.6, 1.7),
                       (xs * (P.EMU_W + .28), sign - 42, sign + 42, 137, 153, 1.3)))
        if index == 1:
            num = mid + end_direction * 142
            _face(car, xs, xs * (P.EMU_W + .14), num - 24, num + 24, 36.5, 42, "number", DECAL)
            for centre, size in ((mid + end_direction * 116, 9), (mid + end_direction * 150, 5.6)):
                # Maintenance hatch: red face inside a fine gasket, screw heads in its corners.
                _face(car, xs, xs * (P.EMU_W + .10), centre - size / 2, centre + size / 2,
                      34, 34 + size, "dark", radius=.6)
                _poly(car, car.body, [(xs * (P.EMU_W + .14), centre - size / 2 + .16, 34.16),
                                      (xs * (P.EMU_W + .14), centre + size / 2 - .16, 34.16),
                                      (xs * (P.EMU_W + .14), centre + size / 2 - .16, 34 + size - .16),
                                      (xs * (P.EMU_W + .14), centre - size / 2 + .16, 34 + size - .16)], (xs, 0, 0))
                for dz in (.8, size - .8):
                    for dd in (-size / 2 + .8, size / 2 - .8):
                        car.disc("rw_steel_grey", (xs * (P.EMU_W + .16), centre + dd, 34 + dz), (xs, 0, 0), .20, 8)


def lights(e, n_front, facing, rail_z, platform_side):
    """Local lights stay inside each car, with no additional shadow maps."""
    import railhead_props as P
    F = P.vehicle_frame(e, n_front, facing, rail_z)
    xs = platform_side * F.x[0]
    total = 2 * P.EMU_CAR + P.EMU_GAP
    out = []
    for k, (a0, s) in enumerate(((0, 1), (total, -1))):
        def p(x, d, z):
            return tuple(float(v) for v in F.p(x, -(a0 + s * d), z))
        for j, d in enumerate(P.EMU_DOORS):
            out.append((f"car {k + 1} vestibule {j + 1}", p(xs * 18, d + 32, 116), "0.32,0.285,0.225,1", 112))
        for name, d, z, radius in (("lower saloon", 425, 83, 126), ("upper saloon", 425, 156, 126),
                                   ("end saloon", 690, 112, 98), ("front saloon", 168, 112, 78)):
            out.append((f"car {k + 1} {name}", p(0, d, z), "0.17,0.155,0.13,1", radius))
    return out


def _save(path, image):
    data = io.BytesIO()
    image.save(data, format="PNG", optimize=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(data.getvalue())
    for attempt in range(10):
        try:
            temp.replace(path)
            return
        except PermissionError:
            time.sleep(.25 * (attempt + 1))
    temp.replace(path)


def _font(size, bold=False):
    return ImageFont.truetype(str(ROOT / "Assets/fonts" / ("Dinish-Bold.ttf" if bold else "Dinish-Regular.ttf")), size)


def _label(draw, xy, text, size, fill=(223, 222, 210, 255), bold=False, anchor="mm"):
    draw.text(xy, text, font=_font(size, bold), fill=fill, anchor=anchor)


def _bike(draw, cx, cy, scale, fill, width=3):
    def p(x, y):
        return (cx + x * scale, cy + y * scale)
    for x in (-23, 23):
        draw.ellipse((cx + (x - 15) * scale, cy + (7 - 15) * scale,
                      cx + (x + 15) * scale, cy + (7 + 15) * scale), outline=fill, width=width)
    for points in (((-23, 7), (-7, -16), (15, -16), (23, 7)),
                   ((-23, 7), (0, 7), (15, -16)), ((-10, -25), (0, 7)),
                   ((-16, -25), (-4, -25)), ((12, -27), (19, -27), (20, -15))):
        draw.line([p(*q) for q in points], fill=fill, width=width)


def write(root=None):
    """Draw surfaces and crisp markings from source, rather than baking a reference photograph onto the model. root: a
    folder laid out as Assets (a stage) to write into; Assets with none."""
    out = OUT if root is None else Path(root) / "materials/railhead"
    from scipy.ndimage import gaussian_filter
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(41005)
    color = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
    rough = Image.new("L", (SIZE, SIZE), 170)
    height = np.zeros((SIZE, SIZE), dtype=np.float32)
    emission = Image.new("L", (SIZE, SIZE), 0)
    ambient = Image.new("L", (SIZE, SIZE), 0)
    for entry, base, r in (("metal", (212, 210, 201), 122), ("wall", (143, 141, 132), 166),
                           ("seat", (48, 57, 68), 235), ("head", (72, 73, 70), 211),
                           ("dark", (18, 21, 24), 109), ("floor", (49, 49, 46), 221)):
        a, b, c, d = RECTS[entry]
        h, w = d - b, c - a
        fine = rng.normal(0, 1, (h, w))
        large = gaussian_filter(fine, 18)
        large /= large.std() + 1e-6
        if entry == "metal":
            grain = gaussian_filter(fine, (.4, 8)) * 4.0
            streak = gaussian_filter(rng.normal(0, 1, (h, w)), (100, 2))
            streak /= streak.std() + 1e-6
            variation = grain + large * 1.5 - np.maximum(streak, 0) * 4.0
            relief = gaussian_filter(fine, (.4, 8)) * .0008
        elif entry == "seat":
            variation = fine * 2.0 + large * 1.0
            relief = fine * .0005
        else:
            variation = fine * 1.3 + large * 1.5
            relief = fine * .0002
        arr = np.clip(np.asarray(base)[None, None, :] + variation[..., None], 0, 255).astype(np.uint8)
        color.paste(Image.fromarray(arr).convert("RGBA"), (a, b))
        rr = np.clip(r + fine * 2, 0, 255).astype(np.uint8)
        rough.paste(Image.fromarray(rr), (a, b))
        height[b:d, a:c] = relief
    draw = ImageDraw.Draw(color)
    white = (222, 221, 210, 255)
    # Woven seat fabric with restrained warm-coloured flecks, like the reference.
    a, b, c, d = RECTS["seat"]
    for y in range(b + 5, d - 5, 18):
        for x in range(a + 5, c - 5, 19):
            ox, oy = int(rng.integers(-5, 6)), int(rng.integers(-5, 6))
            tint = ((111, 81, 51, 255), (77, 65, 78, 255), (68, 88, 101, 255))[int(rng.integers(3))]
            draw.line((x + ox, y + oy, x + ox + 3, y + oy + 1), fill=tint, width=2)
    # Right-hand door insert: second class, bicycle and luggage pictograms.
    a, b, c, d = RECTS["door_markings"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(23, 27, 30, 255))
    _label(draw, ((a + c) / 2, b + 170), "2", 176)
    for y in (b + 282, b + 440, b + 598):
        draw.line((a + 28, y, c - 28, y), fill=(126, 125, 114, 255), width=2)
    _bike(draw, (a + c) / 2, b + 354, 1.50, white, 4)
    draw.rounded_rectangle((a + 58, b + 489, c - 58, b + 566), 6, outline=white, width=4)
    draw.arc((a + 74, b + 473, c - 74, b + 504), 180, 360, fill=white, width=4)
    for x in (a + 72, c - 72):
        draw.line((x, b + 493, x, b + 565), fill=white, width=2)
    # Exterior panel on clear background: 2 / wheelchair / pushchair.
    a, b, c, d = RECTS["access"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(0, 0, 0, 0))
    draw.rectangle((a + 12, b + 12, c - 13, d - 13), outline=white, width=3)
    _label(draw, ((a + c) / 2, b + 125), "2", 200)
    for y in (b + 252, b + 465):
        draw.line((a + 14, y, c - 14, y), fill=white, width=3)
    draw.ellipse((a + 90, b + 274, a + 122, b + 306), fill=white)
    draw.line((a + 105, b + 305, a + 100, b + 370, a + 151, b + 370, a + 165, b + 414), fill=white, width=10)
    draw.line((a + 99, b + 337, a + 147, b + 337), fill=white, width=9)
    draw.arc((a + 51, b + 341, a + 142, b + 432), 55, 300, fill=white, width=8)
    draw.pieslice((a + 48, b + 493, a + 173, b + 621), 0, 180, fill=white)
    draw.line((a + 58, b + 590, a + 86, b + 648, a + 139, b + 648, a + 171, b + 579), fill=white, width=7)
    draw.line((a + 47, b + 589, a + 30, b + 565), fill=white, width=7)
    for x in (a + 88, a + 146):
        draw.ellipse((x - 12, b + 646, x + 12, b + 670), fill=white)
    # The (made-up) regional operator's mark and the vehicle number, with transparent surroundings: two white
    # chevrons and "rhv" (Regionalverkehr Hohenwald-Vorland). No real operator's name or logo.
    a, b, c, d = RECTS["db"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(0, 0, 0, 0))
    cy = (b + d) / 2
    for k in range(2):
        x = a + 14 + k * 24
        draw.polygon(((x, b + 40), (x + 16, b + 40), (x + 40, cy), (x + 16, d - 40), (x, d - 40), (x + 24, cy)),
                     fill=white)
    _label(draw, (a + 146, cy - 4), "rhv", 78, bold=True)
    a, b, c, d = RECTS["number"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(0, 0, 0, 0))
    _label(draw, ((a + c) / 2, (b + d) / 2), "94 80 0462 314-8 D-RHV", 49)
    # Amber dot matrix. Text is rasterised through a regular LED grid, no glowing rectangle.
    a, b, c, d = RECTS["destination"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(9, 13, 17, 255))
    mask = Image.new("L", (c - a, d - b), 0)
    md = ImageDraw.Draw(mask)
    md.text((97, 94), "RE5", font=_font(59), fill=255, anchor="mm")
    md.text((281, 24), "Hauptbahnhof", font=_font(49), fill=255)
    md.text((281, 80), "über Westkreuz", font=_font(46), fill=255)
    ma = np.asarray(mask)
    ed = ImageDraw.Draw(emission)
    for y in range(4, d - b - 4, 4):
        for x in range(4, c - a - 4, 4):
            if ma[y:y + 3, x:x + 3].mean() > 90:
                draw.ellipse((a + x, b + y, a + x + 2, b + y + 2), fill=(207, 126, 39, 255))
                ed.ellipse((a + x, b + y, a + x + 2, b + y + 2), fill=255)
    # Interior notices / line map are authored signs, not exterior window photographs.
    for entry in ("poster", "map", "emergency", "class"):
        a, b, c, d = RECTS[entry]
        draw.rectangle((a, b, c - 1, d - 1), fill=(216, 214, 196, 255))
        if entry == "poster":
            draw.rectangle((a + 7, b + 7, c - 8, b + 66), fill=(160, 32, 36, 255))
            _label(draw, ((a + c) / 2, b + 34), "Sicher reisen", 22, bold=True)
            for y in range(b + 90, d - 35, 21):
                draw.line((a + 15, y, c - 16, y), fill=(63, 63, 59, 255), width=3)
            _label(draw, ((a + c) / 2, d - 23), "rhv Regio", 22, (119, 28, 30, 255), True)
        elif entry == "map":
            _label(draw, ((a + c) / 2, b + 24), "Liniennetz", 27, (48, 58, 60, 255), True)
            for row, tint in enumerate(((124, 39, 43, 255), (39, 87, 115, 255), (83, 108, 63, 255))):
                ps = [(a + 25 + i * 40, b + 75 + row * 70 + int(math.sin(i) * 20)) for i in range(7)]
                draw.line(ps, fill=tint, width=4)
                for x, y in ps:
                    draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=white, outline=tint, width=2)
        elif entry == "emergency":
            draw.rectangle((a + 7, b + 7, c - 8, b + 65), fill=(170, 37, 37, 255))
            _label(draw, ((a + c) / 2, b + 36), "NOTBREMSE", 25, bold=True)
            draw.line((a + 35, b + 100, c - 36, b + 100), fill=(178, 31, 30, 255), width=14)
            for y in (b + 145, b + 162, b + 179):
                draw.line((a + 16, y, c - 17, y), fill=(65, 65, 62, 255), width=2)
        else:
            _label(draw, ((a + c) / 2, (b + d) / 2), "2", 167, (68, 68, 61, 255))
    a, b, c, d = RECTS["lamp"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(229, 224, 205, 255))
    ImageDraw.Draw(emission).rectangle((a, b, c - 1, d - 1), fill=255)
    a, b, c, d = RECTS["button"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(0, 0, 0, 0))
    draw.ellipse((a + 6, b + 6, c - 7, d - 7), fill=(36, 46, 29, 255), outline=(138, 175, 73, 255), width=10)
    draw.line((a + 43, b + 36, a + 34, b + 56, a + 43, b + 76), fill=white, width=5)
    draw.line((c - 44, b + 36, c - 35, b + 56, c - 44, b + 76), fill=white, width=5)
    a, b, c, d = RECTS["threshold"]
    draw.rectangle((a, b, c - 1, d - 1), fill=(177, 148, 31, 255))
    for x in range(a - 64, c, 32):
        draw.polygon(((x, b), (x + 14, b), (x + 78, d - 1), (x + 64, d - 1)), fill=(20, 23, 24, 255))
    # Pad each tile into its gutter so mipmaps cannot pull adjacent lettering into a surface.
    for a, b, c, d in RECTS.values():
        for im in (color, rough, emission):
            tile = im.crop((a, b, c, d))
            im.paste(tile.crop((0, 0, 1, tile.height)).resize((8, tile.height)), (a - 8, b))
            im.paste(tile.crop((tile.width - 1, 0, tile.width, tile.height)).resize((8, tile.height)), (c, b))
            im.paste(im.crop((a - 8, b, c + 8, b + 1)).resize((c - a + 16, 8)), (a - 8, b - 8))
            im.paste(im.crop((a - 8, d - 1, c + 8, d)).resize((c - a + 16, 8)), (a - 8, d))
    ad = ImageDraw.Draw(ambient)
    for entry, amount in (("seat", 192), ("head", 192), ("wall", 32), ("floor", 16)):
        a, b, c, d = RECTS[entry]
        ad.rectangle((a - 8, b - 8, c + 7, d + 7), fill=amount)
    from building_textures import gl_normals
    normal = Image.fromarray(np.clip((gl_normals(height, 1) * .5 + .5) * 255, 0, 255).astype(np.uint8), "RGB")
    for suffix, im in (("color", color), ("rough", rough), ("normal", normal), ("emission", emission),
                       ("trans", color.getchannel("A")), ("ambient", ambient)):
        _save(out / f"rw_emu_{suffix}.png", im)
    for paint, metallic, self_illum, alpha in ((DETAIL, 0, 0, False), (METAL, .18, 0, False),
                                             (INSIDE, 0, .32, False), (DECAL, 0, 0, True), (LIT, .05, .8, True)):
        text = ["// Tools/railhead_train.py", '"Layer0"', "{", '    shader "shaders/complex.shader"',
                '    F_SPECULAR "1"', f'    g_flMetalness "{metallic}"',
                '    TextureColor "materials/railhead/rw_emu_color.png"',
                '    TextureNormal "materials/railhead/rw_emu_normal.png"',
                '    TextureRoughness "materials/railhead/rw_emu_rough.png"',
                '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
                '    g_vColorTint "[1 1 1 1]"', '    g_flModelTintAmount "1.0"']
        if self_illum:
            text += ['    F_SELF_ILLUM "1"', f'    g_flSelfIllumBrightness "{self_illum}"',
                     '    g_flSelfIllumAlbedoFactor "1.0"', '    g_vSelfIllumTint "[1 1 1 0]"',
                     '    TextureSelfIllumMask "materials/railhead/rw_emu_emission.png"' if paint == LIT
                     else '    TextureSelfIllumMask "materials/railhead/rw_emu_ambient.png"']
        if alpha:
            text += ['    F_ALPHA_TEST "1"', '    g_flAlphaTestReference "0.45"',
                     '    TextureTranslucency "materials/railhead/rw_emu_trans.png"',
                     '    g_flAntiAliasedEdgeStrength "1"']
        (out / f"{paint}.vmat").write_text("\n".join(text + ["}", ""]), encoding="utf-8")
    # Tinted train glass is clear enough to see seats, with restrained reflections.
    (out / f"{GLASS}.vmat").write_text('''// Tools/railhead_train.py
"Layer0"
{
    shader "shaders/glass.shader"
    F_GLASS_QUALITY "2"
    g_bFogEnabled "1"
    g_flBlurAmount "0"
    g_flRefractionStrength "1.003"
    AlbedoAbsorption "0.68"
    g_flTintColor "[1 1 1 0]"
    TextureColor "[0.42 0.47 0.46 0]"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "[0.075 0.075 0.075 0]"
    TextureMetalness "[0 0 0 0]"
    TextureAmbientOcclusion "[1 1 1 0]"
    TextureBlendMask "materials/default/default_blend.tga"
    TextureTintMask "materials/default/default.tga"
    TextureTranslucency "materials/default/default_trans.tga"
}
''', encoding="utf-8")
    # Separate enamels avoid changing the car/van paints elsewhere in the map.
    n = 1024
    fine = rng.normal(0, 1, (n, n))
    broad = gaussian_filter(fine, 38, mode="wrap")
    broad /= broad.std() + 1e-6
    vertical = gaussian_filter(fine, (65, 3), mode="wrap")
    vertical /= vertical.std() + 1e-6
    dirt = np.maximum(vertical, 0) * .02 + np.maximum(broad, 0) * .03
    streaks = gaussian_filter(rng.normal(0, 1, (n, n)), (120, 6), mode="wrap")
    streaks = np.maximum(streaks / (streaks.std() + 1e-6) - 1.4, 0) * .025
    for paint, base in ((RED, (184, 26, 29)), (BLUE, (19, 54, 126))):
        arr = np.asarray(base)[None, None, :] * (1 - dirt[..., None] - streaks[..., None]) + fine[..., None] * .9
        arr += np.array((22, 20, 17))[None, None, :] * (dirt + streaks)[..., None]       # grey road and brake dust
        _save(out / f"{paint}_color.png", Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB"))
        rough = np.clip(0.30 + 0.05 * broad + 0.5 * (dirt + streaks), 0.22, 0.6)
        _save(out / f"{paint}_rough.png", Image.fromarray(np.clip(rough * 255, 0, 255).astype(np.uint8), "L"))
        (out / f"{paint}.vmat").write_text('''// Tools/railhead_train.py
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "0.06"
    TextureColor "materials/railhead/PAINT_color.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "materials/railhead/PAINT_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
}
'''.replace("PAINT", paint), encoding="utf-8")
    print(f"Wrote reference train PBR atlas, enamels and {len(PAINTS)} materials")


def rebuild_dressing():
    """Targeted rebuild: preserve the station, gameplay objects and all existing lights."""
    import json
    import map_kit as K
    import railhead_map as R
    glass = K.Model()
    for sign, name in ((1, "railhead_dress_east"), (-1, "railhead_dress_west")):
        model = R.dress_side(sign)
        glass.extend(R.split_paints(model, R.GLASS_PAINTS))
        R.configure(model)
        count = K.write_model(R.OUT_DIR, R.RESOURCE_DIR, name, model)
        print(f"{name}: {count} triangles, {len(model.boxes)} collision boxes", flush=True)
    centre = R.dress_centre()
    glass.extend(R.split_paints(centre, R.GLASS_PAINTS))
    R.configure(glass)
    count = K.write_model(R.OUT_DIR, R.RESOURCE_DIR, "railhead_dress_glass", glass)
    print(f"railhead_dress_glass: {count} triangles", flush=True)
    scene = json.loads(R.SCENE_FILE.read_text(encoding="utf-8"))
    group = next(obj for obj in scene["GameObjects"] if obj.get("Name") == "Lights")
    group["Children"] = [obj for obj in group.get("Children", []) if not obj.get("Name", "").startswith("Train ")]
    for name, position, color, radius, shadows in R.lights():
        if not name.startswith("Train "):
            continue
        key = f"light/{name}"
        group["Children"].append(K.game_object(R.ids, name, key, K.to_world(position), tags="light_point,light",
                                  components=[K.component(R.ids, "Sandbox.PointLight", f"{key}/light", Attenuation=1,
                                              FogMode="Disabled", FogStrength=0, LightColor=color, Radius=radius, Shadows=False)]))
    R.SCENE_FILE.write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
    print("Updated visible train interior lights; other scene objects preserved", flush=True)


def missing():
    return any(not (OUT / f"{paint}.vmat").exists() for paint in PAINTS) or not (OUT / "rw_emu_color.png").exists()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="also rebuild just the train-bearing dressing and lights")
    parser.add_argument("--out", metavar="ROOT", help="a root laid out as Assets (a stage); default Assets")
    args = parser.parse_args()
    write(args.out)
    if args.build:
        rebuild_dressing()
