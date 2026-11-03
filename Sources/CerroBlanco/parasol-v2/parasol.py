"""Cerro Blanco's courtyard parasol v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python parasol.py -- <work dir> <project root> <build|bake|export> ...

A square cafe parasol in place of four flat triangles on a bar: an ecru acrylic canopy in eight gores, sagging a little between its ribs and pulled in along its hem, with piped edges, a valance on each
side and a wind vent over the top on its own spindle and finial. Under it, eight anthracite aluminium ribs pivot in a turned hub, held up by stretchers from a runner that a cord pulls up the pole: the
cord comes out of the pole onto a cleat, with its tail coiled on it. The pole drops through a grommet in the table into a socket tube that stands in a cast base under the table, clamped by a T-knob, so
the old table's centre post is hidden inside it. A tie strap hangs from one gore. No maker's names.

Inches. Z is up, the canopy's sides face +-X and +-Y, and the origin is on the ground at the pole. The table top is at 28.5 to 29.5. The old parasol's rib tips were at 84 and its peak at 100.
"""
import hashlib
import json
import math
import os
import sys

sys.dont_write_bytecode = True
import bmesh
import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, tube  # noqa: E402

CANVAS, POWDER, CAST, NYLON, STEEL, ROPE, BINDING = 0, 1, 2, 3, 4, 5, 6
FOLDER = "models/maps/cerroblanco/parasol_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "parasol_v2")
BLEND = os.path.join(WORK, "parasol_build.blend")
NAME = "parasol"
W, H = 2048, 4096
POS_RANGE = 230.0  # The position bake spans this many inches, centred on the origin.

HALF = 44.0  # The canopy's half width at its rib tips, as the old one's.
PIVOT_R, PIVOT_Z = 1.6, 96.8
TIP_Z = {True: 84.0, False: 84.5}  # Corner ribs, side ribs.
BOW = 1.35  # Ribs arch up under the cloth's pull.
SAG = 0.85  # The cloth between ribs, at the hem.
SCALLOP = 1.05  # How far the hem pulls in between rib tips.
THICK = 0.025  # Half the cloth's thickness.
VENT_IN = 4.6  # The main canopy's opening under the vent.
VENT_HALF, VENT_RIM, VENT_TOP, VENT_DROP = 7.0, 98.9, 101.1, 1.3
VALANCE = 8.0
POLE_R, POLE_TOP = 0.95, 95.6
RUN_Z = 71.5
STRETCH_AT = 0.42
TABLE_Z0, TABLE_Z1 = 28.5, 29.5
SOCKET_R = 1.32
BASE_R = 10.5
CLEAT_Z = 44.5
rng = np.random.default_rng(2611)
edge_lines = []
NO_EDGE = ("rope", "strap", "canvas", "valance", "vent", "pocket", "piping")


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def rib_angle(k):
    return math.radians(45.0 * k)


def is_corner(k):
    return k % 2 == 1


def rib_length(k):
    return HALF * math.sqrt(2.0) if is_corner(k) else HALF


def rib_top(k, s):
    """The top of rib k, where the cloth lies on it, at s from its pivot (0) to its tip (1)."""
    a = rib_angle(k)
    rho = PIVOT_R + s * (rib_length(k) - PIVOT_R)
    z = PIVOT_Z + (TIP_Z[is_corner(k)] - PIVOT_Z) * s + BOW * math.sin(math.pi * s) - 0.35 * max(0.0, (s - 0.88) / 0.12) ** 2
    return Vector((rho * math.cos(a), rho * math.sin(a), z))


def s_inner(k):
    return (VENT_IN - PIVOT_R) / (rib_length(k) - PIVOT_R)


def gore_mid(k, t, v):
    """The middle of the cloth in the gore from rib k to rib k + 1: t from the vent (0) to the hem (1), v across from rib k (0) to rib k + 1 (1)."""
    k1 = (k + 1) % 8
    a = rib_top(k, s_inner(k) + t * (1 - s_inner(k)))
    b = rib_top(k1, s_inner(k1) + t * (1 - s_inner(k1)))
    p = a.lerp(b, v)
    across = math.sin(math.pi * v)
    p.z += THICK - SAG * across * t ** 1.6
    flat = Vector((p.x, p.y, 0.0))
    pull = SCALLOP * across * t ** 8
    if flat.length > 1e-6:
        p -= flat.normalized() * pull
    return p


T_STEPS, V_STEPS = 22, 8


def gore_t(i):
    return (i / T_STEPS) ** 0.92


def canopy_grid():
    """All eight gores as one sheet, round from rib 0, so the cloth is one piece in the atlas."""
    return [[gore_mid(k, gore_t(i), j / V_STEPS) for k in range(8) for j in range(V_STEPS)] for i in range(T_STEPS + 1)]


def sheet(part, grid, offset, upward, wrap=False, uv=None):
    """Faces over a grid of points, moved off it by offset along its normal, facing up (or down) the way upward says. wrap joins the last column to the first. uv is how the build lays it in the atlas
    instead of Blender's projection: "plan" from above, or a direction to lay it along, as a valance."""
    bm = part.bm
    part.uv_mode = uv
    rows, cols = len(grid), len(grid[0])
    normals = []
    for i in range(rows):
        line = []
        for j in range(cols):
            du = grid[min(i + 1, rows - 1)][j] - grid[max(i - 1, 0)][j]
            if wrap:
                dv = grid[i][(j + 1) % cols] - grid[i][j - 1]
            else:
                dv = grid[i][min(j + 1, cols - 1)] - grid[i][max(j - 1, 0)]
            n = du.cross(dv).normalized()
            if n.z < 0 if upward is None else (n.dot(upward(grid[i][j])) < 0):
                n = -n
            line.append(n)
        normals.append(line)
    verts = [[bm.verts.new(grid[i][j] + normals[i][j] * offset) for j in range(cols)] for i in range(rows)]
    flip = offset < 0
    for i in range(rows - 1):
        for j in range(cols if wrap else cols - 1):
            j1 = (j + 1) % cols
            quad = [verts[i][j], verts[i + 1][j], verts[i + 1][j1], verts[i][j1]]
            f = bm.faces.new(quad)
            f.normal_update()
            want = normals[i][j] * (-1 if flip else 1)
            if f.normal.dot(want) < 0:
                f.normal_flip()
    return normals


def bar(part, path, w, h):
    """A rectangular section, w across and h up, swept along points that run mostly level."""
    bm = part.bm
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * sx * w / 2 + up * sz * h / 2) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a, b in zip(rings, rings[1:]):
        for c in range(4):
            bm.faces.new((a[c], a[(c + 1) % 4], b[(c + 1) % 4], b[c]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def canopy():
    grid = canopy_grid()
    sheet(piece(CANVAS, 3, name="canvas"), grid, THICK, None, wrap=True, uv="plan")
    sheet(piece(CANVAS, 3, name="canvas"), grid, -THICK, None, wrap=True, uv="plan")
    for k in range(8):
        # The hem's piping, round the edge between the two tips.
        edge = [gore_mid(k, 1.0, j / 16) - Vector((0, 0, 0.1)) for j in range(17)]
        tube(piece(BINDING, 1, name="piping"), edge, 0.14, 6, caps=False)
    # The opening under the vent is bound too.
    ring = []
    for k in range(8):
        for j in range(4):
            ring.append(gore_mid(k, 0.0, j / 4) - Vector((0, 0, 0.04)))
    tube(piece(BINDING, 1, name="piping"), ring, 0.1, 5, closed=True)


def valances():
    """A valance down each side, sewn under the hem's piping: still at the top, with soft folds that grow toward its bound foot."""
    for side in range(4):
        first_gore, second_gore = (2 * side - 1) % 8, 2 * side
        top = []
        for k in (first_gore, second_gore):
            for j in range(12):
                v = j / 12
                top.append(gore_mid(k, 1.0, v))
        top.append(gore_mid(second_gore, 1.0, 1.0))
        # Stop just short of each corner, so the two valances there don't meet in one line.
        first, last = top[0], top[-1]
        top[0] = first.lerp(top[1], 0.22)
        top[-1] = last.lerp(top[-2], 0.22)
        along = 0.0
        lengths = [0.0]
        for a, b in zip(top, top[1:]):
            along += (b - a).length
            lengths.append(along)
        out_dir = Vector((math.cos(math.radians(90 * side)), math.sin(math.radians(90 * side)), 0.0))
        phase = side * 1.7
        rows = 6
        grid = []
        for r in range(rows + 1):
            depth = VALANCE * r / rows
            line = []
            for q, u in zip(top, lengths):
                ripple = (0.06 + 0.3 * (depth / VALANCE) ** 1.5) * math.sin(2 * math.pi * u / 9.5 + phase) + 0.08 * (depth / VALANCE) * math.sin(2 * math.pi * u / 3.7 + phase * 2)
                flare = 0.3 * (depth / VALANCE) ** 2
                line.append(q - Vector((0, 0, depth + 0.12)) + out_dir * (ripple + flare - 0.02))
            grid.append(line)
        outward = lambda p, o=out_dir: o  # noqa: E731
        along_dir = Vector((-out_dir.y, out_dir.x, 0.0))
        sheet(piece(CANVAS, 3, name="valance"), grid, THICK, outward, uv=along_dir)
        sheet(piece(CANVAS, 3, name="valance"), grid, -THICK, outward, uv=along_dir)


def vent():
    """The wind vent: a small square cap on four struts from the spindle, over the canopy's opening, with a short drop of its own."""
    def cap(t, v, k):
        a, b = rib_angle(k), rib_angle(k + 1)
        ra = VENT_HALF * (math.sqrt(2.0) if is_corner(k) else 1.0)
        rb = VENT_HALF * (math.sqrt(2.0) if is_corner(k + 1) else 1.0)
        pa = Vector((ra * t * math.cos(a), ra * t * math.sin(a), VENT_TOP + (VENT_RIM - VENT_TOP) * t))
        pb = Vector((rb * t * math.cos(b), rb * t * math.sin(b), VENT_TOP + (VENT_RIM - VENT_TOP) * t))
        p = pa.lerp(pb, v)
        p.z -= 0.18 * math.sin(math.pi * v) * t
        return p

    grid = [[cap(0.12 + 0.88 * i / 6, j / 4, k) for k in range(8) for j in range(4)] for i in range(7)]
    sheet(piece(CANVAS, 3, name="vent"), grid, THICK, None, wrap=True, uv="plan")
    sheet(piece(CANVAS, 3, name="vent"), grid, -THICK, None, wrap=True, uv="plan")
    for side in range(4):
        out_dir = Vector((math.cos(math.radians(90 * side)), math.sin(math.radians(90 * side)), 0.0))
        top = [cap(1.0, j / 6, (2 * side - 1) % 8) for j in range(6)] + [cap(1.0, j / 6, (2 * side) % 8) for j in range(7)]
        grid = [[q - Vector((0, 0, VENT_DROP * r / 2)) + out_dir * 0.05 * r for q in top] for r in range(3)]
        outward = lambda p, o=out_dir: o  # noqa: E731
        along_dir = Vector((-out_dir.y, out_dir.x, 0.0))
        sheet(piece(CANVAS, 2, name="vent"), grid, THICK, outward, uv=along_dir)
        sheet(piece(CANVAS, 2, name="vent"), grid, -THICK, outward, uv=along_dir)
    kit.lathe(piece(POWDER, 2, name="spindle"), [(0.42, 98.3), (0.42, VENT_TOP - 0.1), (0, VENT_TOP - 0.1)], 12)
    for k in (1, 3, 5, 7):
        a = rib_angle(k)
        tip = Vector((VENT_HALF * 1.38 * math.cos(a), VENT_HALF * 1.38 * math.sin(a), VENT_RIM - 0.12))
        tube(piece(POWDER, 1, name="vent strut"), [Vector((0.3 * math.cos(a), 0.3 * math.sin(a), VENT_TOP - 0.45)), tip], 0.13, 6)
    # The finial, turned, screwed down on the spindle.
    kit.lathe(piece(POWDER, 2, bevel=0.0, name="finial"), [(0.0, VENT_TOP + 0.05), (0.95, VENT_TOP + 0.05), (1.05, VENT_TOP + 0.3), (0.62, VENT_TOP + 0.9), (0.48, VENT_TOP + 1.25), (0.62, VENT_TOP + 1.55), (0.66, VENT_TOP + 1.9), (0.5, VENT_TOP + 2.25), (0.22, VENT_TOP + 2.42), (0, VENT_TOP + 2.46)], 18)


def frame():
    """Hub, ribs, stretchers, runner and pole, in anthracite powder coat."""
    kit.lathe(piece(POWDER, 3, bevel=0.0, name="hub"), [(POLE_R, 95.0), (1.7, 95.2), (1.95, 95.6), (1.98, 96.0), (1.98, 97.6), (1.78, 98.1), (1.1, 98.4), (0.5, 98.45), (0, 98.45)], 24)
    tube(piece(STEEL, 0, name="hub wire"), kit.ring_path(1.99, 32, kit.frame((0, 0, PIVOT_Z))), 0.06, 4, closed=True)
    for k in range(8):
        path = [rib_top(k, s) - Vector((0, 0, 0.36)) for s in np.linspace(0.0, 1.0, 14)]
        path[0] = Vector((1.2 * math.cos(rib_angle(k)), 1.2 * math.sin(rib_angle(k)), path[0].z))
        bar(piece(POWDER, 2, bevel=0.06, angle=40, name="rib"), path, 0.46, 0.72)
        a = rib_angle(k)
        out = Vector((math.cos(a), math.sin(a), 0))
        tip = rib_top(k, 1.0) - Vector((0, 0, 0.36))
        # The pocket sewn over the rib's end, on the underside.
        pocket = [rib_top(k, 1.0 - d / rib_length(k)) - Vector((0, 0, 0.36)) for d in (3.4, 2.5, 1.5, 0.6, 0.0)] + [tip + out * 0.3]
        tube(piece(CANVAS, 1, name="pocket"), pocket, [0.3, 0.4, 0.44, 0.45, 0.42, 0.24], 7, flatten=0.72)
        # Stretcher from the runner up to the rib, with a clevis at each end.
        joint = rib_top(k, STRETCH_AT) - Vector((0, 0, 0.72))
        foot = Vector((1.95 * math.cos(a), 1.95 * math.sin(a), RUN_Z + 1.6))
        bar(piece(POWDER, 2, bevel=0.045, angle=40, name="stretcher"), [foot, joint], 0.38, 0.5)
        kit.box(piece(POWDER, 1, bevel=0.06, angle=40, name="clevis"), (-0.55, -0.34, -0.55), (0.55, 0.34, 0.4), kit.frame(joint + Vector((0, 0, 0.12)), (0, 0, 1), (math.cos(a), math.sin(a), 0)))
        side = Vector((-math.sin(a), math.cos(a), 0))
        for sign in (-1, 1):
            kit.lathe(piece(STEEL, 0, name="pin"), [(0.11, 0.0), (0.11, 0.05), (0, 0.06)], 8, kit.frame(joint + side * sign * 0.34, side * sign))
        kit.box(piece(POWDER, 1, bevel=0.05, angle=40, name="lug"), (-0.5, -0.32, -0.45), (0.5, 0.32, 0.45), kit.frame(Vector((1.85 * math.cos(a), 1.85 * math.sin(a), RUN_Z + 1.6)), (0, 0, 1), (math.cos(a), math.sin(a), 0)))
    # The runner, which the cord pulls up the pole.
    kit.lathe(piece(POWDER, 3, name="runner"), [(POLE_R + 0.03, RUN_Z - 2.4), (1.4, RUN_Z - 2.4), (1.62, RUN_Z - 2.1), (1.68, RUN_Z - 1.0), (1.68, RUN_Z + 2.2), (1.5, RUN_Z + 2.5), (POLE_R + 0.03, RUN_Z + 2.5)], 24)
    kit.lathe(piece(NYLON, 1, name="runner bush"), [(POLE_R + 0.01, RUN_Z - 2.62), (1.25, RUN_Z - 2.62), (1.3, RUN_Z - 2.4), (POLE_R + 0.01, RUN_Z - 2.4)], 20)
    # The pole, from inside the socket to inside the hub.
    profile = [(POLE_R, z) for z in np.linspace(18.0, POLE_TOP, 9)]
    kit.lathe(piece(POWDER, 3, name="pole"), [(0, 18.0)] + profile + [(0, POLE_TOP)], 24)


def cord():
    """The cord comes out of a grommet in the pole onto a cleat, round it in figure eights, its tail coiled and hung on the top horn."""
    kit.lathe(piece(STEEL, 0, name="cord grommet"), [(0.32, 0.0), (0.32, 0.06), (0.24, 0.1), (0, 0.1)], 10, kit.frame((POLE_R - 0.02, 0, CLEAT_Z + 6.5), (1, 0, 0)))
    x0 = POLE_R
    cleat = piece(NYLON, 1, bevel=0.06, angle=35, name="cleat")
    for z in (CLEAT_Z - 1.2, CLEAT_Z + 1.2):
        kit.box(cleat, (x0 - 0.1, -0.32, z - 0.35), (x0 + 0.62, 0.32, z + 0.35))
    horn = kit.spline([(x0 + 0.62, 0, CLEAT_Z - 2.75), (x0 + 0.78, 0, CLEAT_Z - 1.6), (x0 + 0.8, 0, CLEAT_Z), (x0 + 0.78, 0, CLEAT_Z + 1.6), (x0 + 0.62, 0, CLEAT_Z + 2.75)], 5)
    tube(piece(NYLON, 1, name="cleat"), horn, [0.12] + [0.24] * (len(horn) - 2) + [0.12], 8, flatten=0.8)
    for z in (CLEAT_Z - 0.3, CLEAT_Z + 0.3):
        kit.lathe(piece(STEEL, 0, name="cleat screw"), [(0.13, 0.0), (0.13, 0.04), (0, 0.07)], 8, kit.frame((x0 + 0.62, 0, z + (0.9 if z > CLEAT_Z else -0.9)), (1, 0, 0)))
    r = 0.13
    xf, xm, xbk = x0 + 1.2, x0 + 0.78, x0 + 0.22  # In front of the horns, beside them, and behind them against the pole.
    Z = CLEAT_Z
    rope = [Vector((x0 + 0.05, 0, Z + 6.5)), Vector((x0 + 0.2, 0.1, Z + 5.0)), Vector((x0 + 0.4, 0.45, Z + 3.0)), Vector((x0 + 0.6, 0.5, Z + 0.2)), Vector((xm, 0.46, Z - 1.9))]
    # Under the bottom horn first, then figure eights: across the front, round behind the top horn, back across, round behind the bottom one, and a locking hitch on top.
    for turn in range(3):
        d = turn * 0.13
        rope += [
            Vector((xbk, 0.0, Z - 2.15 + d)),
            Vector((xm, -0.44, Z - 2.0 + d)),
            Vector((xf, -0.3, Z - 1.35 + d)),
            Vector((xf + 0.05, 0.0, Z + d * 0.5)),
            Vector((xf, 0.3, Z + 1.35 - d)),
            Vector((xm, 0.44, Z + 2.0 - d)),
            Vector((xbk, 0.0, Z + 2.15 - d)),
            Vector((xm, -0.44, Z + 2.0 - d)),
            Vector((xf, -0.3, Z + 1.35 - d)),
            Vector((xf + 0.05, 0.0, Z - d * 0.5)),
            Vector((xf, 0.3, Z - 1.35 + d)),
            Vector((xm, 0.44, Z - 2.0 + d)),
        ]
    rope += [Vector((xbk, 0.0, Z - 1.8)), Vector((xm, -0.44, Z - 1.7)), Vector((xf + 0.1, -0.15, Z - 1.2)), Vector((xf + 0.2, 0.6, Z - 1.6)), Vector((xf + 0.25, 0.9, Z - 2.4))]
    tube(piece(ROPE, 1, name="rope"), kit.spline(rope, 4), r, 6)
    # The tail, coiled and hung on the top horn: each loop goes behind the horn and hangs in front of the cleat.
    for n, (depth, wide) in enumerate(((8.8, 1.35), (9.6, 1.6), (8.3, 1.5))):
        top = Z + 2.35 - 0.12 * n
        x = xf + 0.32 + 0.14 * n
        loop = [
            Vector((xbk + 0.02, -0.45, top)), Vector((xbk + 0.02, 0.45, top + 0.02)), Vector((xm + 0.05, 0.62, top)),
            Vector((x - 0.15, 0.85 + 0.1 * n, top - 1.2)), Vector((x, wide, top - depth * 0.55)), Vector((x + 0.05, wide * 0.6, top - depth * 0.92)),
            Vector((x + 0.06, 0.0, top - depth)), Vector((x + 0.05, -wide * 0.6, top - depth * 0.92)), Vector((x, -wide, top - depth * 0.55)),
            Vector((x - 0.15, -0.85 - 0.1 * n, top - 1.2)), Vector((xm + 0.05, -0.62, top)),
        ]
        tube(piece(ROPE, 1, name="rope"), kit.spline(loop + loop[:1], 3)[:-1], r, 6, closed=True)
    start = Vector((xf + 0.25, 0.9, Z - 2.4))
    tail = [start, start + Vector((0.25, 0.15, -2.2)), start + Vector((0.3, 0.05, -5.6)), start + Vector((0.2, -0.1, -8.4))]
    tube(piece(ROPE, 1, name="rope"), kit.spline(tail, 4), r, 6)
    # The end, whipped in black.
    kit.lathe(piece(BINDING, 0, name="rope"), [(0, -0.05), (0.155, 0.0), (0.155, 0.6), (0, 0.66)], 8, kit.frame(tail[-1] - Vector((0, 0, 0.55))))


def base():
    """A cast base under the table, with a socket tube up to a flange under the top and a T-knob clamping the pole."""
    kit.lathe(
        piece(CAST, 3, name="base"),
        [(0, 0.35), (BASE_R - 0.3, 0.35), (BASE_R, 0.6), (BASE_R, 1.25), (BASE_R - 0.25, 1.6), (9.4, 1.85), (6.2, 2.45), (3.4, 2.95), (2.6, 3.15), (2.35, 3.5), (2.05, 5.3), (1.85, 5.55), (SOCKET_R + 0.02, 5.6), (0, 5.6)],
        48,
    )
    for k in range(4):
        a = math.radians(45 + 90 * k)
        kit.lathe(piece(NYLON, 0, name="foot"), [(0, 0.0), (0.75, 0.0), (0.85, 0.12), (0.85, 0.36), (0, 0.36)], 12, kit.frame((8.4 * math.cos(a), 8.4 * math.sin(a), 0)))
    kit.lathe(piece(CAST, 3, name="socket"), [(0, 5.4), (SOCKET_R, 5.4)] + [(SOCKET_R, z) for z in np.linspace(5.6, 27.7, 5)] + [(SOCKET_R, 27.75), (0, 27.75)], 20)
    kit.lathe(piece(CAST, 2, bevel=0.0, name="flange"), [(0, 27.7), (2.9, 27.7), (3.0, 27.82), (3.0, 28.4), (0, 28.4)], 32)
    for k in range(4):
        a = math.radians(90 * k)
        kit.lathe(piece(STEEL, 0, name="flange screw"), [(0.2, 0.0), (0.2, 0.06), (0.12, 0.12), (0, 0.13)], 10, kit.frame((2.3 * math.cos(a), 2.3 * math.sin(a), 27.7), (0, 0, -1)))
    # The T-knob on its stud.
    kit.lathe(piece(STEEL, 0, name="stud"), [(0.2, 0.0), (0.2, 0.75), (0, 0.75)], 10, kit.frame((SOCKET_R - 0.05, 0, 24.0), (1, 0, 0)))
    kit.lathe(piece(CAST, 1, name="boss"), [(0.42, 0.0), (0.42, 0.28), (0.3, 0.36), (0, 0.36)], 14, kit.frame((SOCKET_R - 0.12, 0, 24.0), (1, 0, 0)))
    grip = kit.spline([(SOCKET_R + 0.85, -1.25, 24.0), (SOCKET_R + 0.95, -0.6, 24.0), (SOCKET_R + 1.0, 0, 24.0), (SOCKET_R + 0.95, 0.6, 24.0), (SOCKET_R + 0.85, 1.25, 24.0)], 4)
    tube(piece(NYLON, 1, name="knob"), grip, [0.2] + [0.27] * (len(grip) - 2) + [0.2], 10, flatten=0.8)
    kit.lathe(piece(NYLON, 1, name="knob"), [(0, 0.0), (0.36, 0.0), (0.36, 0.25), (0.32, 0.32), (0, 0.32)], 12, kit.frame((SOCKET_R + 0.62, 0, 24.0), (1, 0, 0)))
    # The grommet in the table top, round the pole.
    kit.lathe(piece(STEEL, 2, name="grommet"), [(POLE_R + 0.03, TABLE_Z1 - 0.02), (1.62, TABLE_Z1 - 0.02), (1.66, TABLE_Z1 + 0.06), (1.52, TABLE_Z1 + 0.2), (POLE_R + 0.03, TABLE_Z1 + 0.22)], 24)


def strap():
    """A tie strap hanging from one gore's underside near the hem, with a ring at its end for tying the canopy shut."""
    k = 2
    top = gore_mid(k, 0.9, 0.5) - Vector((0, 0, 0.12))
    a = math.radians(45 * k + 22.5)
    out = Vector((math.cos(a), math.sin(a), 0))
    side = Vector((-math.sin(a), math.cos(a), 0))
    path = [top, top - Vector((0, 0, 1.6)) + out * 0.1, top - Vector((0, 0, 4.0)) + out * 0.35 + side * 0.15, top - Vector((0, 0, 6.6)) + out * 0.28 + side * 0.25, top - Vector((0, 0, 8.6)) + out * 0.1 + side * 0.2]
    pts = kit.spline(path, 4)
    bm_part = piece(CANVAS, 1, name="strap")
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        across = side - t * side.dot(t)
        across.normalize()
        face = t.cross(across).normalized()
        rings.append([bm_part.bm.verts.new(p + across * sx * 0.5 + face * sz * 0.03) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a_, b_ in zip(rings, rings[1:]):
        for c in range(4):
            bm_part.bm.faces.new((a_[c], a_[(c + 1) % 4], b_[(c + 1) % 4], b_[c]))
    bm_part.bm.faces.new(list(reversed(rings[0])))
    bm_part.bm.faces.new(list(rings[-1]))
    end = pts[-1] - Vector((0, 0, 0.55))
    tube(piece(STEEL, 0, name="ring"), kit.ring_path(0.55, 16, kit.frame(end, side)), 0.07, 5, closed=True)


def geometry():
    canopy()
    valances()
    vent()
    frame()
    cord()
    base()
    strap()


def harden_all():
    seen = set()
    for p in kit.parts:
        bm = p.bm
        if p.name not in ("canvas", "valance", "vent"):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in (POWDER, CAST) and p.name not in NO_EDGE:
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.08))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        while True:
            p.rand = float(kit.rng.uniform(0, 1))
            if round(p.rand, 4) not in seen:
                seen.add(round(p.rand, 4))
                break


def share(finish, normal, centre):
    """How much texture an island gets, against the canopy's underside at 1."""
    flat = Vector((centre.x, centre.y, 0))
    if finish in (CANVAS, BINDING):
        if centre.z > 75.0 and abs(normal.z) > 0.35 and flat.length < 50:
            return 1.0 if normal.z < 0 else 0.58
        if abs(normal.z) < 0.5 and flat.length > 30:
            return 0.95 if normal.dot(flat.normalized()) > 0 else 0.5
        return 1.1
    if finish == CAST:
        if normal.z < -0.7:
            return 0.03
        return 0.85
    if finish == ROPE:
        return 1.1
    return 1.08


def pack(mesh, pad_px=4):
    """The toolkit's real-scale shelf packing, with a share of the atlas for each island, which is kept in the facts' third channel."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    layer = bm.loops.layers.uv.active
    facts = bm.loops.layers.float_color["facts"]
    bm.faces.ensure_lookup_table()
    seen = set()
    islands = []
    for seed in bm.faces:
        if seed.index in seen:
            continue
        seen.add(seed.index)
        stack, faces = [seed], []
        while stack:
            f = stack.pop()
            faces.append(f)
            for l in f.loops:
                a, b = l[layer].uv, l.link_loop_next[layer].uv
                for other in l.link_loops:
                    g = other.face
                    if g.index in seen:
                        continue
                    c, d = other[layer].uv, other.link_loop_next[layer].uv
                    if ((a - d).length < 1e-5 and (b - c).length < 1e-5) or ((a - c).length < 1e-5 and (b - d).length < 1e-5):
                        seen.add(g.index)
                        stack.append(g)
        islands.append(faces)

    rects = []
    for n, faces in enumerate(islands):
        area3 = sum(f.calc_area() for f in faces)
        pts = np.array([tuple(l[layer].uv) for f in faces for l in f.loops])
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
        weighted = Vector((0, 0, 0))
        middle = Vector((0, 0, 0))
        for f in faces:
            weighted += f.normal * f.calc_area()
            middle += f.calc_center_median() * f.calc_area()
        weight = share(int(round(faces[0].loops[0][facts][0] * 16)), weighted.normalized(), middle / max(area3, 1e-9))
        scale = math.sqrt(area3 / max(areauv, 1e-12)) * weight
        centre = pts.mean(0)
        inches = (pts - centre) * scale
        best = None
        for deg in np.linspace(0, 90, 19):
            r = math.radians(deg)
            rot = np.array(((math.cos(r), -math.sin(r)), (math.sin(r), math.cos(r))))
            q = inches @ rot.T
            w, h = np.ptp(q, axis=0)
            if best is None or w * h < best[0]:
                best = (w * h, rot, w, h)
        _, rot, w, h = best
        q = inches @ rot.T
        if h > w:
            rot = np.array(((0.0, 1.0), (-1.0, 0.0))) @ rot
            q = inches @ rot.T
            w, h = h, w
        rects.append((w, h, n, centre, scale, rot, q.min(0), weight))

    def attempt(px_per_in):
        pad = pad_px / px_per_in
        limit_x, limit_y = W / px_per_in, H / px_per_in
        x = y = pad
        row = 0.0
        places = {}
        for w, h, n, *_ in sorted(rects, key=lambda r: (-round(r[1], 1), -r[0])):
            if x + w + pad > limit_x:
                x = pad
                y += row + pad
                row = 0.0
            if y + h + pad > limit_y:
                return None
            places[n] = (x, y)
            x += w + pad
            row = max(row, h)
        return places

    lo, hi = 2.0, 400.0
    places = None
    for _ in range(30):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            places, lo = got, mid
        else:
            hi = mid
    first = lo
    # The shelves waste half the atlas on so many small islands, so lay them out on the shelves first, in a space as tall as the atlas, and let Blender nest them inside that box.
    for w, h, n, centre, scale, rot, low, weight in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px) * first / H, (q[1] + py) * first / H)
                l[facts][2] = weight
    # Two pinned specks at the box's corners make Blender pack into the whole of it, not the shelves' outline.
    for corner, toward in (((0.0, 0.0), (1, 1)), ((W / H, 1.0), (-1, -1))):
        tri = [bm.verts.new((9000.0 + k, 0.0, -9000.0)) for k in range(3)]
        f = bm.faces.new(tri)
        for l, (du, dv) in zip(f.loops, ((0, 0), (1, 0), (0, 1))):
            l[layer].uv = (corner[0] + toward[0] * du * 1e-5, corner[1] + toward[1] * dv * 1e-5)
            l[layer].pin_uv = True
            l[facts][0], l[facts][1], l[facts][2] = 0.0, -1.0, 1.0
    bm.to_mesh(mesh)
    bm.free()
    ob = next(o for o in bpy.data.objects if o.data is mesh)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="ORIGINAL_AABB", rotate=True, rotate_method="ANY", scale=True, merge_overlap=False, margin_method="ADD", margin=pad_px / H, pin=True, pin_method="LOCKED", shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(False)
    specks = bmesh.new()
    specks.from_mesh(mesh)
    bmesh.ops.delete(specks, geom=[v for v in specks.verts if v.co.x > 8000.0], context="VERTS")
    specks.to_mesh(mesh)
    specks.free()
    uv = np.empty(len(mesh.loops) * 2, np.float64)
    mesh.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    low_uv = uv.min(0)
    # The space is as tall as the atlas, W / H of it wide: fill it, then stretch across to the atlas.
    fit = min((W / H) / np.ptp(uv[:, 0]), 1.0 / np.ptp(uv[:, 1])) * (1 - 1e-4)
    uv = (uv - low_uv) * fit
    uv[:, 0] *= H / W
    mesh.uv_layers.active.data.foreach_set("uv", uv.reshape(-1))
    # Blender scaled the islands too, so measure the density from the result: texels per weighted square inch.
    check = bmesh.new()
    check.from_mesh(mesh)
    lay = check.loops.layers.uv.active
    fl = check.loops.layers.float_color["facts"]
    texels = weighted = 0.0
    for f in check.faces:
        c = [Vector((l[lay].uv.x * W, l[lay].uv.y * H)) for l in f.loops]
        for i in range(1, len(c) - 1):
            texels += abs((c[i] - c[0]).cross(c[i + 1] - c[0])) / 2
        weighted += f.calc_area() * f.loops[0][fl][2] ** 2
    check.free()
    density = math.sqrt(texels / weighted)
    print("islands", len(rects), "shelves px/in %.1f" % first, "nested px/in %.1f" % density, flush=True)
    return density


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "parasol_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    lookup = {round(p.rand, 4): p for p in kit.parts}
    # The cloth's sheets are laid flat from above, or along their side, so each is one rectangle in the atlas rather than many triangles.
    bm = bmesh.new()
    bm.from_mesh(hw.data)
    layer = bm.loops.layers.uv.active
    facts = bm.loops.layers.float_color["facts"]
    areas = {}
    for f in bm.faces:
        p = lookup[round(f.loops[0][facts][1], 4)]
        areas[p.name] = areas.get(p.name, 0.0) + f.calc_area()
        mode = getattr(p, "uv_mode", None)
        if mode is None:
            continue
        for l in f.loops:
            co = l.vert.co
            l[layer].uv = (co.x / 100.0, co.y / 100.0) if mode == "plan" else (co.dot(mode) / 100.0, co.z / 100.0)
    bm.to_mesh(hw.data)
    bm.free()
    print("areas", {k: round(v) for k, v in sorted(areas.items(), key=lambda kv: -kv[1])}, flush=True)
    density = pack(hw.data, 4)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), "px/in %.1f" % density, flush=True)

    def lod(number, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = f"parasol_lod{number}"
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        facts = bm.loops.layers.float_color["facts"]
        drop = [f for f in bm.faces if lookup[round(f.loops[0][facts][1], 4)].lod < keep]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(copy.data)
        bm.free()
        bpy.context.view_layer.objects.active = copy
        copy.select_set(True)
        mod = copy.modifiers.new("collapse", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        mod.delimit = {"UV", "SEAM"}
        bpy.ops.object.modifier_apply(modifier=mod.name)
        copy.select_set(False)
        copy.data.calc_loop_triangles()
        print(copy.name, "tris", len(copy.data.loop_triangles), flush=True)

    lod(1, 1, 0.6)
    lod(2, 3, 0.45)
    np.save(os.path.join(WORK, "parasol_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "parasol_parts.json"), "w") as h:
        json.dump([[p.rand, p.name, p.finish] for p in kit.parts], h)
    with open(os.path.join(WORK, "parasol.json"), "w") as h:
        json.dump(
            dict(density=density, range=POS_RANGE, half=HALF, pivot=(PIVOT_R, PIVOT_Z), tip_z=(TIP_Z[True], TIP_Z[False]), vent_in=VENT_IN, vent=(VENT_HALF, VENT_RIM, VENT_TOP), valance=VALANCE, pole=(POLE_R, POLE_TOP), run_z=RUN_Z, table=(TABLE_Z0, TABLE_Z1), socket=SOCKET_R, base_r=BASE_R, cleat_z=CLEAT_Z),
            h,
        )
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved build", flush=True)


def uv_hash(ob):
    data = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers["UVMap"].data.foreach_get("uv", data)
    return hashlib.sha1(data.tobytes()).hexdigest()


def bake_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.max_bounces = 2
    hw = bpy.data.objects["parasol_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 3.0
    with open(os.path.join(WORK, "parasol_baked_uv_hash.txt"), "w") as h:
        h.write(uv_hash(hw))

    def source(kind):
        def setup(nt, emit):
            if kind == "facts":
                attr = nt.nodes.new("ShaderNodeVertexColor")
                attr.layer_name = "facts"
                nt.links.new(attr.outputs[0], emit.inputs[0])
                return
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            mapped = nt.nodes.new("ShaderNodeVectorMath")
            mapped.operation = "MULTIPLY_ADD"
            scale = 1 / POS_RANGE if kind == "pos" else 0.5
            mapped.inputs[1].default_value = (scale, scale, scale)
            mapped.inputs[2].default_value = (0.5, 0.5, 0.5)
            nt.links.new(geo.outputs["Position" if kind == "pos" else "Normal"], mapped.inputs[0])
            nt.links.new(mapped.outputs[0], emit.inputs[0])

        return setup

    def bake_one(w, h, kind, setup, samples, out):
        img = bpy.data.images.new(out, w, h, alpha=True, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        mat = bpy.data.materials.new(out)
        mat.use_nodes = True
        nt = mat.node_tree
        if setup:
            nt.nodes.clear()
            o = nt.nodes.new("ShaderNodeOutputMaterial")
            e = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(e.outputs[0], o.inputs[0])
            setup(nt, e)
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.nodes.active = tex
        tex.select = True
        hw.data.materials.clear()
        hw.data.materials.append(mat)
        scene.cycles.samples = samples
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = hw
        hw.select_set(True)
        bpy.ops.object.bake(type=kind, margin=0, use_clear=True, target="IMAGE_TEXTURES")
        data = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(h, w, 4))
        print("baked", out, flush=True)

    bake_one(W, H, "EMIT", source("pos"), 1, "bake_ps_pos")
    bake_one(W, H, "EMIT", source("nor"), 1, "bake_ps_nor")
    bake_one(W, H, "EMIT", source("facts"), 1, "bake_ps_facts")
    bake_one(W // 2, H // 2, "AO", None, 40, "bake_ps_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["parasol_lod0"]) != open(os.path.join(WORK, "parasol_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"parasol_lod{number}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(62))
        mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
        mod.mode = "FACE_AREA"
        mod.weight = 100
        mod.keep_sharp = True
        mod.thresh = 0.01
        dg = bpy.context.evaluated_depsgraph_get()
        e = ob.evaluated_get(dg)
        em = e.to_mesh()
        em.calc_loop_triangles()
        n_loops, n_tris = len(em.loops), len(em.loop_triangles)
        loops = np.empty(n_tris * 3, np.int32)
        em.loop_triangles.foreach_get("loops", loops)
        verts = np.empty(n_loops, np.int32)
        em.loops.foreach_get("vertex_index", verts)
        co = np.empty(len(em.vertices) * 3)
        em.vertices.foreach_get("co", co)
        uv = np.empty(n_loops * 2)
        em.uv_layers["UVMap"].data.foreach_get("uv", uv)
        nn = np.empty(n_loops * 3)
        em.corner_normals.foreach_get("vector", nn)
        p = co.reshape(-1, 3)[verts[loops]][:, [1, 2, 0]]
        t = uv.reshape(-1, 2)[loops]
        n = nn.reshape(-1, 3)[loops][:, [1, 2, 0]]
        e.to_mesh_clear()
        tables = ({}, {}, {})
        lines = ([], [], [])
        faces = []
        for k in range(n_tris):
            tri = []
            for c in range(3):
                i = k * 3 + c
                idx = []
                for table, store, prefix, vec, digits in zip(tables, lines, ("v ", "vt ", "vn "), (p[i], t[i], n[i]), (5, 6, 5)):
                    key = tuple(np.round(vec, digits))
                    got = table.get(key)
                    if got is None:
                        got = len(table) + 1
                        table[key] = got
                        store.append(prefix + " ".join(f"{x:.{digits}f}" for x in key) + "\n")
                    idx.append(got)
                tri.append("%d/%d/%d" % tuple(idx))
            faces.append("f " + " ".join(tri) + "\n")
        with open(os.path.join(OUT, f"{NAME}_lod{number}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/CerroBlanco/parasol-v2/parasol.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {NAME}\n")
            h.writelines(faces)
        counts[number] = n_tris
        print("lod", number, "tris", n_tris, flush=True)
    with open(os.path.join(OUT, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{FOLDER}/{NAME}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 40.0, 110.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/CerroBlanco/parasol-v2/parasol.py
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{{ from = "{NAME}.vmat" to = "{FOLDER}/{NAME}.vmat" }}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
{meshes}
				]
			}},
			{{
				_class = "LODGroupList"
				children =
				[
{groups}
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
"""
    with open(os.path.join(OUT, f"{NAME}.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/CerroBlanco/parasol-v2/parasol.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{FOLDER}/{NAME}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{FOLDER}/{NAME}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{FOLDER}/{NAME}_metal.png"

	//---- Normal ----
	TextureNormal "{FOLDER}/{NAME}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{FOLDER}/{NAME}_rough.png"
}}
"""
    with open(os.path.join(OUT, f"{NAME}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("parasol stages done", flush=True)
