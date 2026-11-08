"""Boxyard perimeter wall v1: geometry of the wall panel and pier models (boxyard-model session, 2026-11-06).

Model space is the engine's, in inches: x along the wall (left to right as seen from inside the yard), y OUT of the yard
(the yard face of a panel is y = 0, its back is y = +8), z up. A panel's origin is the centre of its left pier on the yard
face; it runs to x = pitch. A pier's origin is its centre on the yard face. The instance rotation is a yaw only
(East 180, West 0, North -90, South +90).

The OBJ files are written the way Tools/map_kit.py writes them: a vertex (x, y, z) becomes `v y z x`.
"""
import math
import random
import zlib
from collections import OrderedDict
from pathlib import Path

import numpy as np

TILE = 48.0                      # inches per tile of the reused concrete_wall_009 scan (2048 px, about 42.7 px/in)
T, H = 8.0, 128.0                # wall thickness and height (same as the old wall)
PLINTH_Z, PLINTH_Y, PLINTH_CH = 8.0, -1.2, 1.2
BASE_TOP = 24.0                  # the dirty base zone (plinth and first course) ends here
COURSE, NCOURSE = 16.0, 6        # field courses between the base zone and the coping
COPING_Z0 = BASE_TOP + COURSE * NCOURSE        # 120
GROOVE_HALF, GROOVE_DEEP = 0.6, 0.5
PIER_W, PIER_D, PIER_Y0 = 12.0, 12.0, -2.0     # the old posts' footprint: 12 deep, 2 in proud of the yard face
PIER_CH = 1.0
BASE_MAT, FIELD_MAT, STEEL_MAT = "pw_base", "pw_concrete", "bx_galv"


def norm(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


class Mesh:
    """ Flat-shaded polygons by material. Every polygon is given with the direction it faces, and wound to match. """

    def __init__(self):
        self.polys = []          # ( material, [ points ], [ uvs ], normal )

    def poly(self, mat, pts, uvs, towards):
        pts = [np.asarray(p, float) for p in pts]
        uvs = [tuple(map(float, uv)) for uv in uvs]
        normal = np.zeros(3)
        for k in range(1, len(pts) - 1):
            normal += np.cross(pts[k] - pts[0], pts[k + 1] - pts[0])
        if np.linalg.norm(normal) < 1e-9:
            return
        if np.dot(normal, towards) < 0:
            pts = pts[:1] + pts[:0:-1]
            uvs = uvs[:1] + uvs[:0:-1]
            normal = -normal
        self.polys.append((mat, pts, uvs, norm(normal)))

    def triangles(self, mat=None):
        return sum(len(p) - 2 for m, p, _, _ in self.polys if mat is None or m == mat)

    def bounds(self):
        pts = np.array([q for _, p, _, _ in self.polys for q in p])
        return pts.min(0), pts.max(0)


# ---------------------------------------------------------------------------------------------------------------------
# Texture windows. The scan is 3 board rows high (16 in each) and 48 in wide; its left and right edges are darkened, so a
# face takes a window that stays 3 % in from them.

def windows(length, rnd, max_w=45.0):
    n = max(1, math.ceil(length / max_w))
    w = length / n
    out = []
    for i in range(n):
        wf = w / TILE
        out.append(dict(x0=i * w, x1=(i + 1) * w, u0=rnd.uniform(0.03, 0.97 - wf), flip=rnd.random() < 0.5, wf=wf))
    return out


def field_u(win, x, back=False):
    t = ((win["x1"] - x) if back else (x - win["x0"])) / TILE
    if win["flip"]:
        t = win["wf"] - t
    return win["u0"] + t


# ---------------------------------------------------------------------------------------------------------------------
# Small solids

def box_quads(mesh, mat, lo, hi, uvf, skip=()):
    """ An axis-aligned box. uvf(point, face) -> (u, v). """
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    faces = {
        "+x": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
        "-x": ([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], (-1, 0, 0)),
        "+y": ([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], (0, 1, 0)),
        "-y": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
        "+z": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
        "-z": ([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], (0, 0, -1)),
    }
    for name, (pts, towards) in faces.items():
        if name in skip:
            continue
        mesh.poly(mat, pts, [uvf(p, name) for p in pts], towards)


def beam(mesh, mat, p0, p1, w, h, up=(0, 0, 1), uv_scale=24.0):
    """ A square-ended bar from p0 to p1, w across and h the other way (the h side faces up where it can). """
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = norm(p1 - p0)
    side = np.cross(up, ax)
    if np.linalg.norm(side) < 1e-6:
        side = np.cross((1.0, 0.0, 0.0), ax)
    side = norm(side)
    top = np.cross(ax, side)
    L = float(np.linalg.norm(p1 - p0))
    c = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ring0 = [p0 + side * sx * w / 2 + top * sz * h / 2 for sx, sz in c]
    ring1 = [p1 + side * sx * w / 2 + top * sz * h / 2 for sx, sz in c]
    for k in range(4):
        a, b = k, (k + 1) % 4
        mid = (ring0[a] + ring0[b] + ring1[a] + ring1[b]) / 4 - (p0 + p1) / 2
        mesh.poly(mat, [ring0[a], ring0[b], ring1[b], ring1[a]],
                  [(0, k * 0.25), (0, k * 0.25 + 0.25), (L / uv_scale, k * 0.25 + 0.25), (L / uv_scale, k * 0.25)], mid)
    mesh.poly(mat, ring0[::-1], [(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1)], -ax)
    mesh.poly(mat, ring1, [(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1)], ax)


def tube(mesh, mat, pts, radius, sides=4, uv_scale=24.0, cap=False):
    """ A thin round (or diamond, sides=4) bar along a polyline. """
    pts = [np.asarray(p, float) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = norm(b - a)
        s = np.cross(t, (0.0, 0.0, 1.0))
        if np.linalg.norm(s) < 1e-6:
            s = np.cross(t, (0.0, 1.0, 0.0))
        s = norm(s)
        u = np.cross(s, t)
        rings.append([p + radius * (math.cos(2 * math.pi * k / sides) * s + math.sin(2 * math.pi * k / sides) * u)
                      for k in range(sides)])
    run = 0.0
    for i in range(len(pts) - 1):
        seg = float(np.linalg.norm(pts[i + 1] - pts[i]))
        for k in range(sides):
            a, b = k, (k + 1) % sides
            mid = (rings[i][a] + rings[i][b] + rings[i + 1][a] + rings[i + 1][b]) / 4 - (pts[i] + pts[i + 1]) / 2
            mesh.poly(mat, [rings[i][a], rings[i][b], rings[i + 1][b], rings[i + 1][a]],
                      [(run / uv_scale, k / sides), (run / uv_scale, (k + 1) / sides),
                       ((run + seg) / uv_scale, (k + 1) / sides), ((run + seg) / uv_scale, k / sides)], mid)
        run += seg


def barb(mesh, mat, p, tangent, direction, length=0.9, span=0.5):
    """ A little three-sided spike standing out of a wire at p. """
    p = np.asarray(p, float)
    t = norm(tangent)
    d = norm(direction)
    s = norm(np.cross(t, d))
    base = [p - t * span / 2 + s * 0.18, p + t * span / 2 + s * 0.18, p - s * 0.28]
    tip = p + d * length
    for k in range(3):
        a, b = base[k], base[(k + 1) % 3]
        mid = (a + b + tip) / 3 - p
        mesh.poly(mat, [a, b, tip], [(0, 0), (0.2, 0), (0.1, 0.4)], mid)


# ---------------------------------------------------------------------------------------------------------------------
# The panel

def sag_points(x0, x1, y, z, sag, n):
    return [(x0 + (x1 - x0) * i / n, y, z - sag * 4 * (i / n) * (1 - i / n)) for i in range(n + 1)]


def panel(P, seed, lod):
    m = Mesh()
    rnd = random.Random(seed)
    segs = windows(P, rnd)
    off = rnd.random()                         # the base strip's u start
    cont = dict(x0=0.0, x1=P, u0=0.03, flip=False, wf=P / TILE)      # one window over the whole length (the far LODs)

    def base_strip(y0, z0, y1, z1, towards):
        u0, u1 = off, off + P / TILE
        m.poly(BASE_MAT, [(0, y0, z0), (P, y0, z0), (P, y1, z1), (0, y1, z1)],
               [(u0, z0 / BASE_TOP), (u1, z0 / BASE_TOP), (u1, z1 / BASE_TOP), (u0, z1 / BASE_TOP)], towards)

    # Yard face, base zone: the plinth, its weathering chamfer and the first course.
    base_strip(PLINTH_Y, 0.0, PLINTH_Y, PLINTH_Z, (0, -1, 0))
    base_strip(PLINTH_Y, PLINTH_Z, 0.0, PLINTH_Z + PLINTH_CH, (0, -1, 1))
    top_of_base = BASE_TOP - (GROOVE_HALF if lod == 0 else 0.0)
    base_strip(0.0, PLINTH_Z + PLINTH_CH, 0.0, top_of_base, (0, -1, 0))
    # The plinth's top edge returns to the wall: it is hidden by the chamfer. Its ends are inside the piers.

    # Reveal grooves: V notches, shaded by two sloped strips; the scan's own joint line is under them.
    def groove(zb):
        v0 = 1.0 / 3.0
        for (ya, za, yb, zb2, towards, va, vb) in (
                (0.0, zb - GROOVE_HALF, GROOVE_DEEP, zb, (0, -1, 1), v0 - 0.003, v0),
                (GROOVE_DEEP, zb, 0.0, zb + GROOVE_HALF, (0, -1, -1), v0, v0 + 0.003)):
            m.poly(FIELD_MAT, [(0, ya, za), (P, ya, za), (P, yb, zb2), (0, yb, zb2)],
                   [(0.03, va), (0.03 + P / TILE, va), (0.03 + P / TILE, vb), (0.03, vb)], towards)

    # Field courses: each takes one board row of the scan, in windows.
    for k in range(NCOURSE):
        z0 = BASE_TOP + COURSE * k + (GROOVE_HALF if lod == 0 else 0.0)
        z1 = BASE_TOP + COURSE * (k + 1) - (GROOVE_HALF if (lod == 0 and k < NCOURSE - 1) else 0.0)
        if lod == 0:
            for si, w in enumerate(segs):
                row = rnd.randrange(3)
                vv = lambda z: row / 3.0 + 0.012 + (z - z0) / TILE
                m.poly(FIELD_MAT, [(w["x0"], 0, z0), (w["x1"], 0, z0), (w["x1"], 0, z1), (w["x0"], 0, z1)],
                       [(field_u(w, w["x0"]), vv(z0)), (field_u(w, w["x1"]), vv(z0)),
                        (field_u(w, w["x1"]), vv(z1)), (field_u(w, w["x0"]), vv(z1))], (0, -1, 0))
        else:
            row = k % 3
            vv = lambda z: row / 3.0 + 0.012 + (z - z0) / TILE
            m.poly(FIELD_MAT, [(0, 0, z0), (P, 0, z0), (P, 0, z1), (0, 0, z1)],
                   [(0.03, vv(z0)), (0.03 + P / TILE, vv(z0)), (0.03 + P / TILE, vv(z1)), (0.03, vv(z1))], (0, -1, 0))
    if lod == 0:
        for k in range(NCOURSE):
            groove(BASE_TOP + COURSE * k)

    # Coping: a 8 in slab with a chamfered top and a 1.5 in overhang on both faces.
    prof = [(-1.5, COPING_Z0, "bottom"), (T + 1.5, COPING_Z0, "bottom_back"), (T + 1.5, COPING_Z0 + 4.5, "back_up"),
            (T, H, "back_chamfer"), (0.0, H, "top"), (-1.5, COPING_Z0 + 4.5, "front_chamfer")]
    # faces: (from, to, name, v window start); a closed loop, the last returns to the first.
    loop = [(-1.5, COPING_Z0), (T + 1.5, COPING_Z0), (T + 1.5, COPING_Z0 + 4.5), (T, H), (0.0, H), (-1.5, COPING_Z0 + 4.5)]
    centre = np.array((T / 2, COPING_Z0 + 4.0))
    wins = segs if lod == 0 else [cont]
    for w in wins:
        vcur = 0.36
        for i in range(len(loop)):
            a, b = loop[i], loop[(i + 1) % len(loop)]
            ln = math.hypot(b[0] - a[0], b[1] - a[1])
            mid = np.array(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
            out2 = norm(np.array((b[1] - a[1], -(b[0] - a[0]))))        # the loop runs front-bottom, back-bottom, ...
            if np.dot(out2, mid - centre) < 0:
                out2 = -out2
            va, vb = vcur, vcur + ln / TILE
            vcur = vb + 0.01
            if vcur > 0.62:
                vcur = 0.36
            ua, ub = field_u(w, w["x0"]), field_u(w, w["x1"])
            m.poly(FIELD_MAT, [(w["x0"], a[0], a[1]), (w["x1"], a[0], a[1]), (w["x1"], b[0], b[1]), (w["x0"], b[0], b[1])],
                   [(ua, va), (ub, va), (ub, vb), (ua, vb)], (0, out2[0], out2[1]))

    # Back face: one board-formed sheet.
    row = 1
    wins = segs if lod <= 1 else [cont]
    for w in wins:
        vv = lambda z: row / 3.0 + 0.012 + (z - BASE_TOP) / TILE
        m.poly(FIELD_MAT, [(w["x1"], T, 0.0), (w["x0"], T, 0.0), (w["x0"], T, COPING_Z0), (w["x1"], T, COPING_Z0)],
               [(field_u(w, w["x1"], True), vv(0.0)), (field_u(w, w["x0"], True), vv(0.0)),
                (field_u(w, w["x0"], True), vv(COPING_Z0)), (field_u(w, w["x1"], True), vv(COPING_Z0))], (0, 1, 0))

    # Wire: two strands strung between the pier brackets' arm tips.
    tip_in, tip_out, tip_z = PIER_Y0 + PIER_D / 2 - 12.0, PIER_Y0 + PIER_D / 2 + 12.0, 160.0
    if lod <= 1:
        n = 8 if lod == 0 else 2
        for ty in (tip_in, tip_out):
            pts = sag_points(0.0, P, ty, tip_z, 2.5, n)
            tube(m, STEEL_MAT, pts, 0.22 if lod == 0 else 0.3, 4)
            if lod == 0:
                # barbs every 10 in, turning round the wire
                dirs = [(0, 0, 1), (0, 1, 0), (0, 0, -1), (0, -1, 0)]
                count = int(P // 10.0)
                for k in range(1, count):
                    x = k * P / count
                    z = tip_z - 2.5 * 4 * (x / P) * (1 - x / P)
                    slope = -2.5 * 4 * (1 - 2 * x / P) / P
                    barb(m, STEEL_MAT, (x, ty, z), (1, 0, slope), dirs[k % 4])
    return m


# ---------------------------------------------------------------------------------------------------------------------
# The pier

def pier(seed, lod):
    m = Mesh()
    rnd = random.Random(seed)
    cx, cy = 0.0, PIER_Y0 + PIER_D / 2             # the pier's centre in plan
    hw, hd = PIER_W / 2, PIER_D / 2
    c = PIER_CH
    # Chamfered shaft outline, anticlockwise from above.
    oct_pts = [(cx - hw + c, cy - hd), (cx + hw - c, cy - hd), (cx + hw, cy - hd + c), (cx + hw, cy + hd - c),
               (cx + hw - c, cy + hd), (cx - hw + c, cy + hd), (cx - hw, cy + hd - c), (cx - hw, cy - hd + c)]
    base_off = rnd.random()
    zb, zt = 8.0, 134.0                            # the shaft
    u_edge = [rnd.uniform(0.03, 0.80) for _ in oct_pts]

    # Base block: a square 8 in plinth below the shaft, weathered like the panels' base zone.
    def base_uv(p, face):
        along = p[0] if face in ("-y", "+y") else p[1]
        return (along / TILE + base_off, p[2] / BASE_TOP)
    box_quads(m, BASE_MAT, (cx - hw, cy - hd, 0.0), (cx + hw, cy + hd, zb), base_uv, skip=("+z", "-z"))
    # The tops of the base block's four corners, left square where the shaft is chamfered.
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        corner = (cx + sx * hw, cy + sy * hd)
        a = (cx + sx * (hw - c), cy + sy * hd)
        b = (cx + sx * hw, cy + sy * (hd - c))
        m.poly(BASE_MAT, [(corner[0], corner[1], zb), (a[0], a[1], zb), (b[0], b[1], zb)],
               [(0.1, 0.33), (0.12, 0.33), (0.11, 0.35)], (0, 0, 1))

    # Shaft: base zone (dirty) up to z = 24, then the field scan.
    for i in range(8 if lod == 0 else 4):
        if lod == 0:
            a, b = oct_pts[i], oct_pts[(i + 1) % 8]
        else:
            quad = [(cx - hw, cy - hd), (cx + hw, cy - hd), (cx + hw, cy + hd), (cx - hw, cy + hd)]
            a, b = quad[i], quad[(i + 1) % 4]
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        out = norm((b[1] - a[1], -(b[0] - a[0]), 0.0))
        if np.dot(out[:2], (np.array(a) + np.array(b)) / 2 - (cx, cy)) < 0:
            out = -out
        u0 = u_edge[i % 8]
        for (za, zb2, mat) in ((zb, BASE_TOP, BASE_MAT), (BASE_TOP, zt, FIELD_MAT)):
            if mat == BASE_MAT:
                uv = [(base_off + i * 0.11, za / BASE_TOP), (base_off + i * 0.11 + ln / TILE, za / BASE_TOP),
                      (base_off + i * 0.11 + ln / TILE, zb2 / BASE_TOP), (base_off + i * 0.11, zb2 / BASE_TOP)]
            else:
                va = ((za - BASE_TOP) / TILE) + 0.012
                vb = ((zb2 - BASE_TOP) / TILE) + 0.012
                uv = [(u0, va), (u0 + ln / TILE, va), (u0 + ln / TILE, vb), (u0, vb)]
            m.poly(mat, [(a[0], a[1], za), (b[0], b[1], za), (b[0], b[1], zb2), (a[0], a[1], zb2)], uv, (out[0], out[1], 0))

    # Cap: a 0.8 in overhang with chamfered top edges, and its underside.
    ov = 0.8
    ox0, ox1, oy0, oy1 = cx - hw - ov, cx + hw + ov, cy - hd - ov, cy + hd + ov
    zc0, zc1, zc2 = zt, zt + 5.0, zt + 6.0
    ix0, ix1, iy0, iy1 = ox0 + 0.9, ox1 - 0.9, oy0 + 0.9, oy1 - 0.9

    def cap_uv(face, a_len, v0):
        u0 = rnd.uniform(0.03, 0.75)
        return [(u0, v0), (u0 + a_len / TILE, v0), (u0 + a_len / TILE, v0 + 0.1), (u0, v0 + 0.1)]
    sides = [((ox0, oy0), (ox1, oy0), (0, -1, 0)), ((ox1, oy0), (ox1, oy1), (1, 0, 0)),
             ((ox1, oy1), (ox0, oy1), (0, 1, 0)), ((ox0, oy1), (ox0, oy0), (-1, 0, 0))]
    inner = [((ix0, iy0), (ix1, iy0)), ((ix1, iy0), (ix1, iy1)), ((ix1, iy1), (ix0, iy1)), ((ix0, iy1), (ix0, iy0))]
    for (a, b, out), (ia, ib) in zip(sides, inner):
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        m.poly(FIELD_MAT, [(a[0], a[1], zc0), (b[0], b[1], zc0), (b[0], b[1], zc1), (a[0], a[1], zc1)], cap_uv("side", ln, 0.4), out)
        m.poly(FIELD_MAT, [(a[0], a[1], zc1), (b[0], b[1], zc1), (ib[0], ib[1], zc2), (ia[0], ia[1], zc2)],
               cap_uv("chamfer", ln, 0.2), (out[0], out[1], 1))
        # the underside overhang: a trapezoid from the cap's edge to the shaft's face
        sa = (np.clip(a[0], cx - hw, cx + hw), np.clip(a[1], cy - hd, cy + hd))
        sb = (np.clip(b[0], cx - hw, cx + hw), np.clip(b[1], cy - hd, cy + hd))
        m.poly(FIELD_MAT, [(a[0], a[1], zc0), (b[0], b[1], zc0), (sb[0], sb[1], zc0), (sa[0], sa[1], zc0)],
               cap_uv("under", ln, 0.6), (0, 0, -1))
    m.poly(FIELD_MAT, [(ix0, iy0, zc2), (ix1, iy0, zc2), (ix1, iy1, zc2), (ix0, iy1, zc2)],
           [(0.1, 0.4), (0.3, 0.4), (0.3, 0.6), (0.1, 0.6)], (0, 0, 1))

    # Bracket: a base plate, a short stem and a V of two arms (the arms' tips carry the two wire strands).
    pz = zc2
    uvs = lambda p, f: (p[0] / 24.0, p[2] / 24.0)
    if lod <= 1:
        box_quads(m, STEEL_MAT, (cx - 3.0, cy - 3.0, pz), (cx + 3.0, cy + 3.0, pz + 0.5), uvs, skip=("-z",))
        box_quads(m, STEEL_MAT, (cx - 1.0, cy - 1.0, pz + 0.5), (cx + 1.0, cy + 1.0, pz + 7.5), uvs, skip=("-z", "+z"))
        stem_top = np.array((cx, cy, pz + 7.0))
        for sign in (-1, 1):
            tip = np.array((cx, cy + sign * 12.0, 160.0))
            beam(m, STEEL_MAT, stem_top, tip, 1.6, 1.6, up=(1, 0, 0))
        if lod == 0:
            # four bolt heads on the plate
            for sx, sy in ((-2.2, -2.2), (2.2, -2.2), (2.2, 2.2), (-2.2, 2.2)):
                box_quads(m, STEEL_MAT, (cx + sx - 0.5, cy + sy - 0.5, pz + 0.5), (cx + sx + 0.5, cy + sy + 0.5, pz + 1.0), uvs,
                          skip=("-z",))
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def obj_text(mesh, name, mtl):
    lines = ["# Sources/Boxyard/perimeter-wall-v1/pw_geom.py (boxyard-model session, 2026-11-06)", f"mtllib {mtl}", f"o {name}"]
    verts, uvs, normals, faces = [], [], [], []
    by_mat = OrderedDict()
    for mat, pts, uv, n in mesh.polys:
        by_mat.setdefault(mat, []).append((pts, uv, n))
    for mat, items in by_mat.items():
        faces.append(f"usemtl {mat}")
        for pts, uv, n in items:
            base = len(verts)
            normals.append(f"vn {n[1]:.5f} {n[2]:.5f} {n[0]:.5f}")
            ni = len(normals)
            for p, (u, v) in zip(pts, uv):
                verts.append(f"v {p[1]:.4f} {p[2]:.4f} {p[0]:.4f}")
                uvs.append(f"vt {u:.5f} {v:.5f}")
            for k in range(1, len(pts) - 1):
                a, b, c = base + 1, base + k + 1, base + k + 2
                faces.append(f"f {a}/{a}/{ni} {b}/{b}/{ni} {c}/{c}/{ni}")
    return "\n".join(lines + verts + uvs + normals + faces) + "\n"


def mtl_text(mats):
    return "".join(f"newmtl {m}\nKd 1 1 1\nd 1\n" for m in mats)


REMAP = {
    FIELD_MAT: "materials/boxyard/perimeter_wall_v1/pw_concrete.vmat",
    BASE_MAT: "materials/boxyard/perimeter_wall_v1/pw_base.vmat",
    STEEL_MAT: "materials/boxyard/bx_galv.vmat",
}


def vmdl_text(model_dir, stem, mats, thresholds):
    remaps = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{m}.vmat" to = "{REMAP[m]}" }}' for m in sorted(mats))
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{model_dir}/{stem}_lod{i}.obj" import_translation = [ 0.0, 0.0, 0.0 ] '
        f'import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" '
        f'align_origin_z_type = "None" parent_bone = "" import_filter = {{ exclude_by_default = false exception_list = [ ] }} }}'
        for i in range(len(thresholds)))
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{i}" ] }}'
                        for i, t in enumerate(thresholds))
    return ('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
            "// Generated by Sources/Boxyard/perimeter-wall-v1/build.py (boxyard-model session, 2026-11-06). No collision: the yard model keeps the wall's four boxes.\n"
            "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
            "\t\t\t{\n\t\t\t\t_class = \"MaterialGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n\t\t\t\t\t{\n"
            "\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n"
            f"{remaps}\n"
            "\t\t\t\t\t\t]\n\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n\t\t\t\t\t},\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n"
            f"{meshes}\n"
            "\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n"
            f"{groups}\n"
            "\t\t\t\t]\n\t\t\t},\n"
            "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n")
