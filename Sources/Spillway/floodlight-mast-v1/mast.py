"""Spillway's yard floodlight mast v1: build, bake and export. Uses the capture flag's mesh toolkit, as the pallet does.

blender -b --factory-startup -t 4 --python mast.py -- <work dir> <project root> <build|bake|export> ...

A 26 ft hot-dip galvanised lighting mast as a plant yard really has one: a poured pier and grout pad, a 12 in base plate on four
anchor bolts with ribs and a fillet weld, a tapered round pole whose lowest 66 in is painted safety yellow, a hand-hole with its
cover and earth lug, a slip-joint sleeve, a welded hub with a cross-arm through it, two braces back to the pole, and two LED
floodlights on yokes (cast body with cooling fins, hinged bezel and gasket, glass, visor, trunnion bolts, U-bolt clamps, a cable
from each to the pole). Inches, engine axes: the lamps face +X, +Y is to the left of that, Z up, origin on the floor at the pier.

The model it replaces (Tools/spillway_map.py cargo_yard) was a 6 in untapered rod on a box with a bare crossbar and two wall-pack
boxes, 528 triangles. Every light in the scene is left where it was (17.5 in out from the pole, 35 in each side, 300 in up).
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
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, frame, lathe, prism, tube  # noqa: E402

GALV, ZINC, BRASS, RUBBER, WELD, PLATE, RUST = kit.GALV, kit.ZINC, kit.BRASS, kit.RUBBER, kit.WELD, kit.PLATE, kit.RUST
HOUSING, OXIDE = kit.PAINT, kit.OXIDE
YELLOW, PIER, LENS = 9, 13, 14

NAME = "mast"
MODEL_FOLDER = "models/props/spillway/floodlight_mast_v1"
MAT_FOLDER = "materials/spillway/floodlight_mast_v1"
OUT_MODEL = os.path.join(ROOT, "Assets", "models", "props", "spillway", "floodlight_mast_v1")
OUT_MAT = os.path.join(ROOT, "Assets", "materials", "spillway", "floodlight_mast_v1")
BLEND = os.path.join(WORK, "mast_build.blend")
RES = 2048
POS_RANGE = 700.0  # The position bake spans this many inches; the mast is 311 in tall.
LOD_SWITCH = (0.0, 38.0, 105.0)  # About 19 in per unit: LOD1 from 19 m, LOD2 from 52 m.

# ---- Dimensions, inches. ----
PIER_HALF, PIER_TOP = 11.0, 11.5
GROUT_TOP, PLATE_TOP, PLATE_HALF = 12.25, 13.25, 6.0
Z0 = PLATE_TOP
R0, R1, ZTOP = 3.45, 1.9, 299.2  # Pole radius at the plate and at the top.
SIDES = 24
Z_ARM, R_ARM, ARM_HALF = 294.5, 1.5, 47.0
HEAD_Y = 35.0  # Where the scene's lights are: 35 in each side of the pole.
XP, PZ, TILT = 8.0, 296.0 + 8.9, 28.0  # Pivot of the lamp bodies (out from the pole, up), their tilt down.
HANDHOLE_AT = 205.0  # Degrees round from +X; the way the close view from the north-west looks.
PLATE_AT = 232.0
SEGMENTS = [(Z0, 66.0, YELLOW, 3.0), (66.0, 130.0, GALV, 1.8), (130.0, 210.0, GALV, 1.2), (210.0, ZTOP, GALV, 1.0)]

CTX = {"group": "main", "weight": 1.0}


def radius(z):
    return R0 + (R1 - R0) * (z - Z0) / (ZTOP - Z0)


def piece(finish, lod=3, bevel=0.0, segs=1, angle=40.0, name="", weight=None, group=None):
    p = Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name)
    p.weight = CTX["weight"] if weight is None else weight
    p.group = CTX["group"] if group is None else group
    p.drop = None
    p.drop_dir = None
    kit.parts.append(p)
    return p


class ctx:
    """The toolkit's own helpers add parts that carry none of this; tag whatever a block adds."""

    def __init__(self, group=None, weight=None):
        self.group, self.weight = group, weight

    def __enter__(self):
        self.n0 = len(kit.parts)
        self.old = dict(CTX)
        if self.group is not None:
            CTX["group"] = self.group
        if self.weight is not None:
            CTX["weight"] = self.weight

    def __exit__(self, *a):
        for p in kit.parts[self.n0 :]:
            if not hasattr(p, "group"):
                p.group = CTX["group"]
            if not hasattr(p, "weight"):
                p.weight = CTX["weight"]
            if not hasattr(p, "drop"):
                p.drop = None
            if not hasattr(p, "drop_dir"):
                p.drop_dir = None
        CTX.clear()
        CTX.update(self.old)


def bolt(at, axis, size, lod=1, washer=True, finish=ZINC, stud=0.0, weight=None):
    """A hex nut or bolt head on a round washer, sitting on `at` and facing along `axis`; the faces on the work are dropped.

    The toolkit's own hex_bolt bevels everything and spends about 120 triangles on a washer; this keeps the washer to a 10-sided
    disc and the head to a chamfered hexagon, and any stud to a 6-sided pin."""
    m = frame(at, axis)
    d = Vector(axis).normalized()
    z = 0.0
    if washer:
        w = piece(finish, lod, name="washer", weight=weight)
        lathe(w, [(size * 0.92, 0), (size * 0.92, size * 0.09), (0.0, size * 0.09)], 10, m)
        w.drop_dir = d
        z = size * 0.09
    b = piece(finish, lod, name="nut", weight=weight)
    lathe(b, [(size * 0.66, z), (size * 0.66, z + size * 0.5), (size * 0.5, z + size * 0.56)], 6, m)
    b.drop_dir = d
    if stud:
        s = piece(finish, 0, name="stud", weight=weight)
        lathe(s, [(size * 0.3, z + size * 0.5), (size * 0.3, z + size * 0.56 + stud), (size * 0.2, z + size * 0.6 + stud), (0.0, z + size * 0.6 + stud)], 6, m)
        s.drop_dir = d


YZX = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # local x -> Y, y -> Z, z -> X: an outline in YZ extruded along X.
XZ = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # local x -> X, y -> Z, z -> -Y: an outline in XZ extruded along Y.


def plate_xz(part, outline, y0, y1, m=Matrix.Identity(4)):
    """A counter-clockwise outline in (X, Z), thick from Y = y0 to y1."""
    prism(part, outline, -y1, -y0, m @ XZ)


def rrect(w, h, r, segs):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ring_prism(part, outer, inner, z0, z1, m=Matrix.Identity(4)):
    """A frame: counter-clockwise outer and inner outlines with the same number of points, extruded along local Z."""
    bm = part.bm
    n = len(outer)
    lo_o = [bm.verts.new(m @ Vector((x, y, z0))) for x, y in outer]
    hi_o = [bm.verts.new(m @ Vector((x, y, z1))) for x, y in outer]
    lo_i = [bm.verts.new(m @ Vector((x, y, z0))) for x, y in inner]
    hi_i = [bm.verts.new(m @ Vector((x, y, z1))) for x, y in inner]
    for k in range(n):
        j = (k + 1) % n
        bm.faces.new((lo_o[k], lo_o[j], hi_o[j], hi_o[k]))
        bm.faces.new((lo_i[j], lo_i[k], hi_i[k], hi_i[j]))
        bm.faces.new((hi_o[k], hi_o[j], hi_i[j], hi_i[k]))
        bm.faces.new((lo_o[j], lo_o[k], lo_i[k], lo_i[j]))


def wrap_plate(part, theta_deg, zc, w, h, lift, rows=4, cols=8):
    """A w x h plate laid on the pole's skin, `lift` proud of it: a grid on the cone, with a skirt down into the pole."""
    bm = part.bm
    th0 = math.radians(theta_deg)
    zs = [zc - h / 2 + h * j / rows for j in range(rows + 1)]

    def at(i, j, r_off):
        z = zs[j]
        rs = radius(z)
        th = th0 + (-w / 2 + w * i / cols) / rs
        r = rs + r_off
        return bm.verts.new((r * math.cos(th), r * math.sin(th), z))

    o = [[at(i, j, lift) for j in range(rows + 1)] for i in range(cols + 1)]
    n = {}
    for i in range(cols + 1):
        for j in range(rows + 1):
            if i in (0, cols) or j in (0, rows):
                n[(i, j)] = at(i, j, -0.08)
    for i in range(cols):
        for j in range(rows):
            bm.faces.new((o[i][j], o[i + 1][j], o[i + 1][j + 1], o[i][j + 1]))
    for j in range(rows):
        bm.faces.new((o[0][j], o[0][j + 1], n[(0, j + 1)], n[(0, j)]))
        bm.faces.new((o[cols][j + 1], o[cols][j], n[(cols, j)], n[(cols, j + 1)]))
    for i in range(cols):
        bm.faces.new((o[i + 1][0], o[i][0], n[(i, 0)], n[(i + 1, 0)]))
        bm.faces.new((o[i][rows], o[i + 1][rows], n[(i + 1, rows)], n[(i, rows)]))


def pole_point(theta_deg, z, lift=0.0):
    t = math.radians(theta_deg)
    r = radius(z) + lift
    return Vector((r * math.cos(t), r * math.sin(t), z)), Vector((math.cos(t), math.sin(t), 0.0))


# ---------------------------------------------------------------- the pier and base
def pier():
    with ctx(group="pier", weight=1.0):
        c = 1.1
        h = PIER_HALF
        octa = [(-h + c, -h), (h - c, -h), (h, -h + c), (h, h - c), (h - c, h), (-h + c, h), (-h, h - c), (-h, -h + c)]
        prism(piece(PIER, 3, bevel=0.9, segs=2, angle=60, name="pier"), octa, -1.5, PIER_TOP)
        g = 7.6
        c2 = 1.2
        gr = [(-g + c2, -g), (g - c2, -g), (g, -g + c2), (g, g - c2), (g - c2, g), (-g + c2, g), (-g, g - c2), (-g, -g + c2)]
        prism(piece(PIER, 3, bevel=0.3, segs=2, angle=60, name="grout"), gr, PIER_TOP - 0.2, GROUT_TOP)


def base():
    with ctx(weight=1.0):
        c = 1.1
        h = PLATE_HALF
        outline = [(-h + c, -h), (h - c, -h), (h, -h + c), (h, h - c), (h - c, h), (-h + c, h), (-h, h - c), (-h, -h + c)]
        plate = piece(GALV, 3, bevel=0.14, segs=2, angle=40, name="base plate", weight=2.5)
        prism(plate, outline, GROUT_TOP, PLATE_TOP)
        plate.drop = lambda f: f.normal.z < -0.9
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            bolt((sx * 4.4, sy * 4.4, PLATE_TOP), (0, 0, 1), 1.5, lod=1, washer=True, finish=ZINC, stud=0.9, weight=2.5)
        # The fillet weld round the pole's foot, and four ribs standing on the plate.
        fillet = piece(WELD, 2, angle=30, name="foot weld", weight=2.5)
        lathe(fillet, [(R0 + 0.9, Z0), (R0 + 0.25, Z0 + 0.5), (R0 - 0.03, Z0 + 1.7)], SIDES)
        fillet.drop = lambda f: abs(f.normal.z) > 0.99
        for a in (0, 90, 180, 270):
            rib = piece(YELLOW, 2, bevel=0.05, segs=1, name="rib", weight=3.0)
            outline = [(R0 - 0.3, Z0), (R0 + 3.7, Z0), (R0 + 3.7, Z0 + 0.8), (R0 + 0.45, Z0 + 7.6), (R0 - 0.3, Z0 + 7.6)]
            m = Matrix.Rotation(math.radians(a), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X")
            prism(rib, outline, -0.19, 0.19, m)
            rib.drop = lambda f: f.normal.z < -0.9


# ---------------------------------------------------------------- the pole
def pole():
    for z0, z1, fin, w in SEGMENTS:
        p = piece(fin, 3, bevel=0.0, angle=89, name="pole", weight=w)
        lathe(p, [(radius(z0), z0), (radius(z1), z1)], SIDES)
        p.drop = lambda f: abs(f.normal.z) > 0.99
    cap = piece(GALV, 3, name="pole cap", weight=1.0)
    lathe(cap, [(R1, ZTOP), (2.12, ZTOP + 0.15), (2.12, ZTOP + 0.7), (1.2, ZTOP + 1.7), (0.0, ZTOP + 2.15)], 16)
    cap.drop = lambda f: f.normal.z < -0.99
    # The slip-joint sleeve where the two lengths of the pole overlap, with its set screws.
    zj = 150.0
    r = radius(zj)
    sleeve = piece(GALV, 2, bevel=0.04, angle=30, name="sleeve", weight=1.2)
    lathe(sleeve, [(r + 0.02, zj), (r + 0.4, zj + 0.7), (r + 0.4, zj + 5.3), (r + 0.02, zj + 6.0)], SIDES)
    sleeve.drop = lambda f: abs(f.normal.z) > 0.99
    for a in (20, 140, 260):
        p, n = pole_point(a, zj + 3.0, 0.4)
        bolt(p, n, 0.55, lod=0, washer=False, finish=ZINC)
    # The stay collar the braces hang from.
    collar = piece(GALV, 3, bevel=0.04, angle=30, name="brace collar", weight=1.1)
    lathe(collar, [(2.1, 246.5), (2.56, 246.9), (2.56, 252.1), (2.1, 252.5)], SIDES)
    collar.drop = lambda f: abs(f.normal.z) > 0.99


def handhole():
    """A reinforced hand-hole with its cover plate, two screws and the brass earth lug beside it, and a riveted data plate."""
    with ctx(weight=3.0):
        zc = 36.0
        wrap_plate(piece(GALV, 2, name="handhole frame", weight=3.0), HANDHOLE_AT, zc, 5.6, 8.4, 0.34)
        wrap_plate(piece(GALV, 2, name="handhole cover", weight=3.0), HANDHOLE_AT, zc, 4.6, 7.2, 0.66)
        for dz in (-2.9, 2.9):
            p, n = pole_point(HANDHOLE_AT, zc + dz, 0.66)
            bolt(p, n, 0.7, lod=1, washer=True, finish=ZINC, weight=2.5)
        # The earth lug: a brass tab with a stud and a nut, beside the frame.
        p, n = pole_point(HANDHOLE_AT + 17.0, zc - 3.0, 0.0)
        tab = piece(BRASS, 1, bevel=0.05, name="earth lug", weight=3.0)
        kit.box(tab, (-0.7, -0.5, -0.1), (0.7, 0.5, 0.32), frame(p, n, (0, 0, 1)))
        bolt(p + n * 0.32, n, 0.5, lod=0, washer=True, finish=BRASS, stud=0.6, weight=2.5)
        # The data plate, riveted at the corners.
        zp = 64.0
        wrap_plate(piece(PLATE, 1, name="data plate", weight=3.0), PLATE_AT, zp, 4.2, 2.8, 0.1, rows=2, cols=6)
        for da, dz in ((-1.8, -1.1), (-1.8, 1.1), (1.8, -1.1), (1.8, 1.1)):
            p, n = pole_point(PLATE_AT + math.degrees(da / radius(zp)), zp + dz, 0.1)
            r = piece(PLATE, 0, name="rivet", weight=2.5)
            lathe(r, [(0.12, 0.0), (0.11, 0.03), (0.05, 0.06), (0.0, 0.065)], 8, frame(p, n))
            r.drop_dir = n


# ---------------------------------------------------------------- the top: hub, arm, braces
def top():
    with ctx(weight=1.0):
        hub = piece(GALV, 3, bevel=0.05, angle=30, name="hub", weight=1.2)
        lathe(hub, [(1.97, 290.6), (2.5, 291.5), (2.8, 292.3), (2.8, 296.7), (2.5, 297.5), (1.93, 298.4)], 20)
        hub.drop = lambda f: abs(f.normal.z) > 0.99
        arm = piece(GALV, 3, bevel=0.0, angle=89, name="arm", weight=1.2)
        lathe(arm, [(0.0, -ARM_HALF), (1.28, -ARM_HALF), (R_ARM, -ARM_HALF + 0.35), (R_ARM, ARM_HALF - 0.35), (1.28, ARM_HALF), (0.0, ARM_HALF)], 16, frame((0, 0, Z_ARM), (0, 1, 0)))
        for s in (1, -1):
            # A band clamped round the arm where the brace ends.
            band = piece(GALV, 3, bevel=0.03, angle=30, name="arm band", weight=1.0)
            lathe(band, [(R_ARM, -0.9), (1.76, -0.9), (1.76, 0.9), (R_ARM, 0.9)], 16, frame((0, s * 27.0, Z_ARM), (0, 1, 0)))
            band.drop = lambda f: all(math.hypot(v.co.x, v.co.z - Z_ARM) < 1.52 for v in f.verts)
            # The brace's clevis on the collar: two ears with the pin through them.
            for e in (1, -1):
                ear = [(2.4, 247.6), (5.0, 247.6), (5.9, 248.8), (5.9, 250.4), (5.0, 251.6), (2.4, 251.6)]
                if s < 0:
                    ear = [(-y, z) for y, z in ear][::-1]
                x0, x1 = (0.7, 1.0) if e > 0 else (-1.0, -0.7)
                prism(piece(GALV, 3, bevel=0.03, name="brace ear", weight=1.0), ear, x0, x1, YZX)
                bolt(Vector((e * 1.0, s * 4.6, 249.6)), (e, 0, 0), 0.8, lod=1, washer=True, finish=ZINC)
            tube(piece(GALV, 3, name="brace", weight=0.9), [Vector((0, s * 4.6, 249.6)), Vector((0, s * 27.0, Z_ARM - 1.4))], 0.62, 10)
            bolt(Vector((0.0, s * 27.0, Z_ARM - 1.76)), (0, 0, -1), 0.7, lod=1, washer=True, finish=ZINC)


# ---------------------------------------------------------------- a floodlight head
def make_head(group, y0):
    H = Matrix.Translation((XP, y0, PZ)) @ Matrix.Rotation(math.radians(TILT), 4, "Y")
    Y_ = Matrix.Translation((XP, y0, PZ))
    forward = (H.to_3x3() @ Vector((1, 0, 0))).normalized()
    with ctx(group=group, weight=1.0):
        # Cast body and its cooling fins.
        body = piece(HOUSING, 3, bevel=0.32, segs=2, angle=40, name="head body", weight=1.1)
        kit.box(body, (-1.5, -10.2, -5.3), (2.6, 10.2, 5.3), H)
        for k in range(14):
            yk = -9.1 + 1.4 * k
            fin = piece(HOUSING, 0, name="fin", weight=0.7)
            prism(fin, [(-1.5, 0.13), (-3.7, 0.07), (-3.7, -0.07), (-1.5, -0.13)], -5.1, 5.1, H @ Matrix.Translation((0, yk, 0)))
        # A cast rib across the fins, so they read as one casting.
        kit.box(piece(HOUSING, 1, bevel=0.06, name="fin rib", weight=0.8), (-3.0, -9.4, -0.35), (-1.5, 9.4, 0.35), H)
        # Hinged bezel, its gasket and its screws.
        ring_prism(piece(HOUSING, 3, bevel=0.07, name="bezel", weight=1.2), rrect(21.4, 12.0, 0.9, 3), rrect(18.6, 9.4, 0.5, 3), 2.6, 3.5, H @ YZX)
        ring_prism(piece(RUBBER, 2, name="gasket", weight=0.8), rrect(18.9, 9.7, 0.45, 3), rrect(18.25, 9.05, 0.4, 3), 3.0, 3.4, H @ YZX)
        for yy in (-7.5, -2.5, 2.5, 7.5):
            for zz in (-5.35, 5.35):
                s = piece(ZINC, 0, name="bezel screw", weight=1.0)
                lathe(s, [(0.3, 0.0), (0.3, 0.09), (0.0, 0.17)], 6, H @ Matrix.Translation((3.5, yy, zz)) @ frame((0, 0, 0), (1, 0, 0)))
                s.drop_dir = forward
        for yy in (-7.2, 7.2):
            k = piece(OXIDE, 1, name="hinge knuckle", weight=1.0)
            lathe(k, [(0.0, -1.3), (0.5, -1.3), (0.5, 1.3), (0.0, 1.3)], 8, H @ Matrix.Translation((2.95, yy, 6.15)) @ frame((0, 0, 0), (0, 1, 0)))
        for yy in (-6.0, 6.0):
            kit.box(piece(OXIDE, 1, bevel=0.05, name="latch", weight=1.0), (2.9, yy - 0.9, -6.5), (3.8, yy + 0.9, -5.7), H)
        # The visor: a folded sheet with its front lip and two wings.
        V = H @ Matrix.Translation((2.7, 0, 6.2)) @ Matrix.Rotation(math.radians(10), 4, "Y")
        prism(piece(HOUSING, 2, bevel=0.03, name="visor", weight=1.0), [(0.0, -10.9), (5.3, -10.9), (5.3, 10.9), (0.0, 10.9)], 0.0, 0.14, V)
        kit.box(piece(HOUSING, 2, bevel=0.03, name="visor lip", weight=1.0), (5.1, -10.9, -1.0), (5.3, 10.9, 0.14), V)
        for sy in (-1, 1):
            y0w, y1w = (10.76, 10.9) if sy > 0 else (-10.9, -10.76)
            plate_xz(piece(HOUSING, 2, bevel=0.03, name="visor wing", weight=1.0), [(0.0, 0.14), (0.0, -5.0), (5.3, -0.7), (5.3, 0.14)], y0w, y1w, V)
        # Trunnion bosses on the body and the pivot bolts through the yoke.
        for sy in (-1, 1):
            boss = piece(HOUSING, 2, name="trunnion boss", weight=1.0)
            lathe(boss, [(1.25, 0.0), (1.25, 0.8)], 10, H @ Matrix.Translation((0.0, sy * 10.2, 0.0)) @ frame((0, 0, 0), (0, sy, 0)))
            boss.drop_dir = (H.to_3x3() @ Vector((0, sy, 0))).normalized()
            bolt(Y_ @ Vector((0.0, sy * 11.25, 0.0)), (0, sy, 0), 1.0, lod=1, washer=True, finish=ZINC)
        # The cable gland under the body.
        gl = piece(OXIDE, 1, name="gland", weight=1.0)
        lathe(gl, [(0.8, 0.0), (0.8, 0.6), (0.55, 0.64), (0.55, 1.25), (0.0, 1.3)], 8, H @ Matrix.Translation((-0.2, 0.0, -5.3)) @ frame((0, 0, 0), (0, 0, -1)))
        gl.drop_dir = (H.to_3x3() @ Vector((0, 0, -1))).normalized()
        # Yoke: two side plates and the base they stand on, clamped to the arm by two U-bolts.
        outline = [(-4.0, -8.9), (5.2, -8.9), (4.4, -3.4)]
        for a in range(-35, 216, 25):
            t = math.radians(a)
            outline.append((3.3 * math.cos(t), 3.3 * math.sin(t)))
        outline.append((-2.9, -3.6))
        for sy in (-1, 1):
            y0p, y1p = (10.95, 11.25) if sy > 0 else (-11.25, -10.95)
            plate_xz(piece(GALV, 2, name="yoke plate", weight=1.0), outline, y0p, y1p, Y_)
        tee = [(-10.5, -6.5), (-4.0, -6.5), (-4.0, -10.95), (5.2, -10.95), (5.2, 10.95), (-4.0, 10.95), (-4.0, 6.5), (-10.5, 6.5)]
        prism(piece(GALV, 2, name="yoke base", weight=0.9), tee, -8.9, -8.6, Y_)
        for off in (-5.0, 5.0):
            ys = y0 + off
            path = [(-1.82, ys, Z_ARM + R_ARM + 1.5), (-1.82, ys, Z_ARM)]
            for a in (190, 230, 270, 310, 350):
                t = math.radians(a)
                path.append((1.82 * math.cos(t), ys, Z_ARM + 1.82 * math.sin(t)))
            path += [(1.82, ys, Z_ARM), (1.82, ys, Z_ARM + R_ARM + 1.5)]
            tube(piece(ZINC, 1, name="u-bolt", weight=0.9), [Vector(p) for p in path], 0.3, 6)
            for lx in (-1.82, 1.82):
                bolt(Vector((lx, ys, Z_ARM + R_ARM + 0.3)), (0, 0, 1), 0.95, lod=1, washer=True, finish=ZINC, weight=0.9)


def gland_tip():
    H = Matrix.Translation((XP, 0.0, PZ)) @ Matrix.Rotation(math.radians(TILT), 4, "Y")
    return H @ Vector((-0.2, 0.0, -6.7))


def cables():
    """Each head's cable: out of the gland, over the yoke plate, down behind the arm and along it to the hub."""
    with ctx(weight=0.6):
        g = gland_tip()
        for s in (1, -1):
            y = s * HEAD_Y
            path = [
                (g.x, y, g.z),
                (g.x - 0.55, y, g.z - 1.1),
                (3.0, y, 297.15),
                (0.5, y, 296.85),
                (-1.8, y, 296.85),
                (-3.2, y, 296.2),
                (-3.7, y - s * 1.5, 295.0),
                (-2.6, y - s * 3.5, 294.3),
                (-2.05, y - s * 8.0, 294.2),
                (-2.05, y - s * 18.0, 294.2),
                (-2.05, y - s * 30.0, 294.2),
                (-1.3, s * 2.2, 294.2),
            ]
            tube(piece(RUBBER, 1, name="cable", weight=0.6), kit.spline(path, 2), 0.3, 6)


def lens_grid(part, y0, cols=6, rows=3):
    H = Matrix.Translation((XP, y0, PZ)) @ Matrix.Rotation(math.radians(TILT), 4, "Y")
    bm = part.bm
    v = []
    for i in range(cols + 1):
        col = []
        for j in range(rows + 1):
            y = -9.1 + 18.2 * i / cols
            z = -4.5 + 9.0 * j / rows
            x = 3.2 + 0.28 * (1 - (y / 9.1) ** 2) * (1 - (z / 4.5) ** 2)
            col.append(bm.verts.new(H @ Vector((x, y, z))))
        v.append(col)
    for i in range(cols):
        for j in range(rows):
            bm.faces.new((v[i][j], v[i + 1][j], v[i + 1][j + 1], v[i][j + 1]))


def lenses():
    with ctx(group="lens", weight=1.0):
        for y0 in (HEAD_Y, -HEAD_Y):
            lens_grid(piece(LENS, 3, name="lens"), y0)


def geometry():
    pier()
    base()
    pole()
    handhole()
    top()
    cables()
    lenses()
    make_head("head_a", HEAD_Y)  # head B is this one moved along the arm, copied after the parts are hardened


# ---------------------------------------------------------------- build stage
edge_lines = []


def harden_all():
    rng = np.random.default_rng(3107)
    count = len(kit.parts)
    perm = rng.permutation(count)
    for index, p in enumerate(kit.parts):
        bm = p.bm
        bm.normal_update()
        if all(len(e.link_faces) == 2 for e in bm.edges):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.normal_update()
        if p.group in ("main", "head_a") and p.finish not in (PIER, LENS):
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    n = max(1, int((b - a).length / 0.2))
                    for k in range(n + 1):
                        edge_lines.append(tuple(a.lerp(b, k / n)))
        kit.harden(p)
        bm.normal_update()
        doomed = []
        for f in bm.faces:
            if p.drop is not None and p.drop(f):
                doomed.append(f)
            elif p.drop_dir is not None and f.normal.dot(p.drop_dir) < -0.97:
                doomed.append(f)
        if doomed:
            bmesh.ops.delete(bm, geom=doomed, context="FACES")
        p.done = bm
        p.rand = float((perm[index] + 0.5) / count)  # Unique, so a face finds its part from it.
        p.key = round(float(np.float32(p.rand)), 4)
    keys = [p.key for p in kit.parts]
    if len(set(keys)) != len(keys):
        raise SystemExit("two parts share a rounded key")


def join(parts, name):
    verts, faces, fin, rnd, wgt = [], [], [], [], []
    offset = 0
    for part in parts:
        bm = part.done
        verts.extend(tuple(v.co) for v in bm.verts)
        bm.verts.index_update()
        for f in bm.faces:
            faces.append(tuple(v.index + offset for v in f.verts))
            fin.append(part.finish)
            rnd.append(part.rand)
            wgt.append(part.weight)
        offset += len(bm.verts)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    colour = mesh.color_attributes.new("facts", "FLOAT_COLOR", "CORNER")
    per_face = np.stack([np.array(fin, np.float32) / 16.0, np.array(rnd, np.float32), np.array(wgt, np.float32) / 8.0, np.ones(len(fin), np.float32)], -1)
    colour.data.foreach_set("color", np.repeat(per_face, 3, axis=0).reshape(-1))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def pack_weighted(mesh, res=2048, pad_px=5):
    """The toolkit's real-scale packer, with a density weight per island read from the facts colour's blue channel."""
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
        weights = {round(f.loops[0][facts][2] * 8.0, 3) for f in faces}
        if len(weights) > 1:
            print("island with mixed weights", weights, flush=True)
        weight = max(weights)
        area3 = sum(f.calc_area() for f in faces)
        pts = np.array([tuple(l[layer].uv) for f in faces for l in f.loops])
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
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
        low = q.min(0)
        if h > w:
            rot = np.array(((0.0, 1.0), (-1.0, 0.0))) @ rot
            q = inches @ rot.T
            low = q.min(0)
            w, h = h, w
        rects.append((w, h, n, centre, scale, rot, low))

    def attempt(density):
        """First-fit decreasing height shelves: an island goes on the first shelf with room, so the ends of rows fill up."""
        pad = pad_px / density
        limit = res / density
        shelves = []  # [y, height, x used]
        top = pad
        places = {}
        for w, h, n, *_ in sorted(rects, key=lambda r: (-round(r[1], 1), -r[0])):
            if w + 2 * pad > limit:
                return None
            for shelf in shelves:
                if h <= shelf[1] and shelf[2] + w + pad <= limit:
                    places[n] = (shelf[2], shelf[0])
                    shelf[2] += w + pad
                    break
            else:
                if top + h + pad > limit:
                    return None
                shelves.append([top, h, pad + w + pad])
                places[n] = (pad, top)
                top += h + pad
        return places

    lo, hi = 1.0, 200.0
    places = None
    for _ in range(30):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            places, lo = got, mid
        else:
            hi = mid
    density = lo
    for w, h, n, centre, scale, rot, low in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px) * density / res, (q[1] + py) * density / res)
    bm.to_mesh(mesh)
    bm.free()
    print("islands", len(rects), "density px/in at weight 1: %.2f" % density, flush=True)
    return density


def planar_uv(mesh):
    """The pier is the map's concrete: its UVs are the old plinth's, planar at 1/128 per inch."""
    layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        n = poly.normal
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            if abs(n.z) >= abs(n.x) and abs(n.z) >= abs(n.y):
                uv = (co.y / 128.0, co.x / 128.0)
            elif abs(n.x) >= abs(n.y):
                uv = (co.y / 128.0, co.z / 128.0)
            else:
                uv = (co.x / 128.0, co.z / 128.0)
            layer.data[li].uv = uv


def lens_uv(mesh):
    layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = (0.5, 0.5)


def combine(pairs, name, mats):
    """Several meshes in one, each with its material slot."""
    bm = bmesh.new()
    for mesh, slot in pairs:
        before = len(bm.faces)
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[before:]:
            f.material_index = slot
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    for m in mats:
        out.materials.append(m)
    out.polygons.foreach_set("use_smooth", np.ones(len(out.polygons), bool))
    ob = bpy.data.objects.new(name, out)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def drop_small(mesh, keep):
    """A copy without the parts whose lod is below keep."""
    out = mesh.copy()
    bm = bmesh.new()
    bm.from_mesh(out)
    facts = bm.loops.layers.float_color["facts"]
    drop = [f for f in bm.faces if LOOKUP[round(f.loops[0][facts][1], 4)].lod < keep]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(out)
    bm.free()
    return out


def decimated(mesh, ratio, delimit=("UV", "SEAM")):
    tmp = bpy.data.objects.new("tmp", mesh.copy())
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.objects.active = tmp
    tmp.select_set(True)
    mod = tmp.modifiers.new("collapse", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    mod.delimit = set(delimit)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    tmp.select_set(False)
    out = tmp.data
    bpy.data.objects.remove(tmp)
    return out


LOOKUP = {}


def count_tris(mesh):
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    harden_all()
    LOOKUP.update({p.key: p for p in kit.parts})
    print("parts", len(kit.parts), "tris", sum(len(p.done.faces) for p in kit.parts), flush=True)
    by = lambda g: [p for p in kit.parts if p.group == g]
    tally = {}
    for p in kit.parts:
        t = tally.setdefault((p.group if p.group != "head_b" else "head_a", p.name), [0, 0])
        t[0] += len(p.done.faces)
        t[1] += 1
    for (g, n), (t, c) in sorted(tally.items(), key=lambda kv: -kv[1][0])[:30]:
        print("  tris %5d  x%-3d %s / %s" % (t, c, g, n), flush=True)

    core = by("main") + by("head_a")
    hw = join(core, "mast_bake")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    density = pack_weighted(hw.data, RES, 5)
    mesh = hw.data

    # Texel density by part.
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    facts = np.empty(len(mesh.loops) * 4, np.float32)
    mesh.color_attributes["facts"].data.foreach_get("color", facts)
    facts = facts.reshape(-1, 4)
    mesh.calc_loop_triangles()
    names = {}
    for tri in mesh.loop_triangles:
        a, b, c = co[list(tri.vertices)]
        area3 = 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        p, q, r = uv[list(tri.loops)]
        uva = 0.5 * abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]))
        part = LOOKUP[round(float(facts[tri.loops[0]][1]), 4)]
        t = names.setdefault(part.name, [0.0, 0.0])
        t[0] += area3
        t[1] += uva
    print("atlas fill %.3f" % sum(v[1] for v in names.values()), "surface in2 %.0f" % sum(v[0] for v in names.values()), flush=True)
    for name, (a3, ua) in sorted(names.items(), key=lambda kv: -kv[1][0]):
        print("  %-18s %7.1f in2  %5.1f px/in" % (name, a3, RES * math.sqrt(ua / a3)), flush=True)

    # Head B: head A's finished parts moved along the arm (copied, so the topology is the same), with head A's UVs.
    twins = []
    for p in by("head_a"):
        q = Part(p.finish, p.lod, name=p.name)
        q.weight, q.group, q.rand, q.key = p.weight, "head_b", p.rand, p.key
        q.done = p.done.copy()
        bmesh.ops.translate(q.done, verts=q.done.verts, vec=(0.0, -2 * HEAD_Y, 0.0))
        twins.append(q)
    head_b = join(twins, "mast_head_b")
    mesh_b = head_b.data
    mesh_b.uv_layers.new(name="UVMap")
    n_a = sum(len(p.done.faces) for p in by("head_a"))
    first = sum(len(p.done.faces) for p in by("main"))
    if n_a != len(mesh_b.polygons):
        raise SystemExit(f"Head B has {len(mesh_b.polygons)} faces, head A {n_a}")
    loops_all = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", loops_all)
    loops_a = loops_all.reshape(-1, 2)[3 * first : 3 * (first + n_a)]
    co_b = np.empty(len(mesh_b.vertices) * 3)
    mesh_b.vertices.foreach_get("co", co_b)
    co_b = co_b.reshape(-1, 3)
    vi_b = np.empty(len(mesh_b.loops), np.int32)
    mesh_b.loops.foreach_get("vertex_index", vi_b)
    vi_a = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get("vertex_index", vi_a)
    vi_a = vi_a[3 * first : 3 * (first + n_a)]
    err = np.abs(co[vi_a] - (co_b[vi_b] + np.array((0.0, 2 * HEAD_Y, 0.0)))).max()
    print("head B is head A moved along the arm, worst %.5f in" % err, flush=True)
    if err > 1e-3:
        raise SystemExit("Head B is not head A moved along the arm")
    mesh_b.uv_layers["UVMap"].data.foreach_set("uv", loops_a.reshape(-1))

    pier_ob = join(by("pier"), "mast_pier")
    planar_uv(pier_ob.data)
    lens_ob = join(by("lens"), "mast_lens")
    lens_uv(lens_ob.data)

    mats = [bpy.data.materials.new(n) for n in ("mast_hw", "mast_pier", "mast_lens")]
    full = combine([(hw.data, 0), (mesh_b, 0)], "mast_hwfull", mats[:1])

    lod0 = combine([(hw.data, 0), (mesh_b, 0), (pier_ob.data, 1), (lens_ob.data, 2)], "mast_lod0", mats)
    hw1 = decimated(drop_small(full.data, 1), 0.5)
    lod1 = combine([(hw1, 0), (decimated(pier_ob.data, 0.6, ()), 1), (lens_ob.data, 2)], "mast_lod1", mats)
    hw2 = decimated(drop_small(full.data, 3), 0.32)
    lod2 = combine([(hw2, 0), (decimated(pier_ob.data, 0.35, ()), 1), (decimated(lens_ob.data, 0.5, ()), 2)], "mast_lod2", mats)
    for ob in (lod0, lod1, lod2):
        print(ob.name, "tris", count_tris(ob.data), flush=True)
    bpy.data.objects.remove(full)
    bpy.data.objects.remove(head_b)
    bpy.data.objects.remove(lens_ob)

    np.save(os.path.join(WORK, "mast_edges.npy"), np.array(edge_lines, np.float32))
    meta = dict(density=density, res=RES, range=POS_RANGE, ztop=ZTOP, r0=R0, r1=R1, z0=Z0, z_arm=Z_ARM, arm_half=ARM_HALF, head_y=HEAD_Y,
                handhole_at=HANDHOLE_AT, plate_at=PLATE_AT, xp=XP, pz=PZ, tilt=TILT,
                parts={str(p.key): dict(name=p.name, finish=p.finish, weight=p.weight, lod=p.lod, group=p.group) for p in kit.parts})
    with open(os.path.join(WORK, "mast.json"), "w") as h:
        json.dump(meta, h)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved build", flush=True)


def uv_hash(ob):
    data = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers["UVMap"].data.foreach_get("uv", data)
    return hashlib.sha1(data.tobytes()).hexdigest()


# ---------------------------------------------------------------- bake stage
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
    hw = bpy.data.objects["mast_bake"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    # The floor it stands on and the pier, for the AO bake only.
    floor = bpy.data.meshes.new("floor")
    floor.from_pydata([(-300, -300, 0), (300, -300, 0), (300, 300, 0), (-300, 300, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("floor", floor)
    scene.collection.objects.link(ground)
    pier_ob = bpy.data.objects["mast_pier"]
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 9.0
    with open(os.path.join(WORK, "mast_baked_uv_hash.txt"), "w") as h:
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

    def bake_one(size, kind, setup, samples, out):
        ground.hide_render = kind != "AO"
        pier_ob.hide_render = kind != "AO"
        img = bpy.data.images.new(out, size, size, alpha=True, float_buffer=True)
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
        data = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(size, size, 4))
        print("baked", out, flush=True)

    bake_one(RES, "EMIT", source("pos"), 1, "bake_mast_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_mast_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_mast_facts")
    bake_one(1024, "AO", None, 64, "bake_mast_ao")


# ---------------------------------------------------------------- export stage
def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT_MODEL, exist_ok=True)
    os.makedirs(OUT_MAT, exist_ok=True)
    if uv_hash(bpy.data.objects["mast_bake"]) != open(os.path.join(WORK, "mast_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    materials = ["mast_hw", "mast_pier", "mast_lens"]
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"mast_lod{number}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(50))
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
        poly_of = np.empty(n_tris, np.int32)
        em.loop_triangles.foreach_get("polygon_index", poly_of)
        slot_of_poly = np.empty(len(em.polygons), np.int32)
        em.polygons.foreach_get("material_index", slot_of_poly)
        slots = slot_of_poly[poly_of]
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
        faces = {0: [], 1: [], 2: []}
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
            faces[int(slots[k])].append("f " + " ".join(tri) + "\n")
        with open(os.path.join(OUT_MODEL, f"mast_lod{number}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Spillway/floodlight-mast-v1/mast.py\nmtllib mast.mtl\n")
            for block in lines:
                h.writelines(block)
            for slot, name in enumerate(materials):
                if faces[slot]:
                    h.write(f"usemtl {name}\n")
                    h.writelines(faces[slot])
        counts[number] = {m: len(faces[s]) for s, m in enumerate(materials)}
        print("lod", number, "tris", n_tris, counts[number], flush=True)
    with open(os.path.join(OUT_MODEL, "mast.mtl"), "w", newline="\n") as h:
        for name in materials:
            h.write(f"newmtl {name}\nKd 1 1 1\nd 1\n\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL_FOLDER}/mast_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, LOD_SWITCH))
    remaps = [
        ("mast_hw.vmat", f"{MAT_FOLDER}/mast_hw.vmat"),
        ("mast_pier.vmat", "materials/spillway/sw_trim_v2.vmat"),
        ("mast_lens.vmat", "materials/riverdale/rv_lamp_warm.vmat"),
    ]
    remap_text = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{a}" to = "{b}" }}' for a, b in remaps)
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Spillway/floodlight-mast-v1/mast.py
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
{remap_text}
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
    with open(os.path.join(OUT_MODEL, "mast.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Spillway/floodlight-mast-v1/mast.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MAT_FOLDER}/mast_hw_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MAT_FOLDER}/mast_hw_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MAT_FOLDER}/mast_hw_metal.png"

	//---- Normal ----
	TextureNormal "{MAT_FOLDER}/mast_hw_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MAT_FOLDER}/mast_hw_rough.png"
}}
"""
    with open(os.path.join(OUT_MAT, "mast_hw.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    # Size of the model, to put in the README.
    mesh = bpy.data.objects["mast_lod0"].data
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    print("extent in (x y z) min", np.round(co.min(0), 2), "max", np.round(co.max(0), 2), flush=True)
    print("exported", {k: sum(v.values()) for k, v in counts.items()}, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("mast stages done", flush=True)
