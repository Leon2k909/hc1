"""Orion launch-deck control shed v1: build, bake and export. Uses the capture flag's mesh toolkit, as the Spillway mast does.

blender -b --factory-startup -t 4 --python shed.py -- <work dir> <project root> <build|bake|export> ...

A prefabricated steel equipment shelter as a launch deck really has one, 120 x 90 x 110 in on the deck at bomb site A (the footprint
and height of the plain box it replaces): a welded base channel on anchor brackets, four corner posts, trapezoidal corrugated sheet
on the east, west and back walls and the front's side bays, a flat door pilaster with closure channels (the door and lamp that are
already on the front wall belong to the map and stay), a rolled eave cap with a standing-seam roof inside it, a louvred vent, a
rain-hooded electrical cabinet with its conduit, sign plates, flanged boots where the two deck pipes pass through the side walls, a
cable gland box, and on the roof a package air conditioner, a mushroom vent, a hatch, an antenna mast and four lifting lugs.

Inches. Axes are the engine's world axes, origin at the middle of the footprint on the floor: +X is north (the back of the shed),
+Y is west (the left of the front as you face it), Z up. The scene object sits at world (1335, 170, 240) with no rotation.
The door's wall is X = -45. Nothing on the front wall within the door's frame or the lamp's body is touched.

The model it replaces was 12 triangles of one steel box (Tools/orion_map.py launch_deck(), the box -230..-110 / 1290..1380).
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

BODY, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST = kit.PAINT, kit.GALV, kit.OXIDE, kit.ZINC, kit.BRASS, kit.RUBBER, kit.WELD, kit.PLATE, kit.RUST
YELLOW, RED, DARK, LIGHT = 9, 10, 11, 12

NAME = "shed"
MODEL_FOLDER = "models/props/orion/deck_shed_v1"
MAT_FOLDER = "materials/orion/deck_shed_v1"
OUT_MODEL = os.path.join(ROOT, "Assets", "models", "props", "orion", "deck_shed_v1")
OUT_MAT = os.path.join(ROOT, "Assets", "materials", "orion", "deck_shed_v1")
BLEND = os.path.join(WORK, "shed_build.blend")
RES = 2048
POS_RANGE = 300.0  # The position bake spans this many inches round the origin; the shed is about 123 x 93 x 125.
LOD_SWITCH = (0.0, 38.0, 105.0)  # About 19 in per unit: LOD1 from 18 m, LOD2 from 51 m.

# ---- Dimensions, inches. ----
HX, HY = 45.0, 60.0          # the walls' crest planes: the front is X = -45, the east wall is Y = -60
BASE_H = 5.0                  # the base channel
WALL_TOP = 108.2              # the eave cap sits on this
CAP_TOP = 110.0               # the old box's height
DEPTH, SHEET = 1.0, 0.8       # corrugation depth and the sheet's own thickness
POST_IN, POST_OUT = 55.5, 60.8
DOOR_HALF = 24.0              # the flat door pilaster: |Y| < 24
TRIM_OUT = 26.5
BAY_IN = 55.5                 # corrugated bays run between the closure channel and the corner post
SIDE_X = 41.0                 # the side walls' corrugation runs between the corner posts

CTX = {"weight": 1.0}


def piece(finish, lod=3, bevel=0.0, segs=1, angle=40.0, name="", weight=None):
    p = Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name)
    p.weight = CTX["weight"] if weight is None else weight
    p.group = "main"
    p.drop = None
    p.drop_dir = None
    kit.parts.append(p)
    return p


def box_part(finish, lod, lo, hi, bevel=0.2, segs=1, name="", weight=None, drop_dir=None, drop=None, angle=40.0, m=Matrix.Identity(4)):
    """A box. drop_dir points away from whatever the part rests on; the faces looking the other way are never seen, so they go."""
    p = piece(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name, weight=weight)
    kit.box(p, lo, hi, m)
    p.drop_dir = drop_dir
    p.drop = drop
    return p


def bolt(at, axis, size, lod=1, washer=True, finish=ZINC, stud=0.0, weight=None):
    """A hex nut or bolt head on a round washer, sitting on `at` and facing along `axis`; the faces on the work are dropped."""
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
    """An outline in (X, Z), thick from Y = y0 to y1."""
    prism(part, outline, -y1, -y0, m @ XZ)


def rrect(w, h, r, segs):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle(r, n, cx=0.0, cy=0.0):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


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


def grid_strip(part, la, lb, outward):
    """An open sheet between two polylines of 3D points of equal length, its faces turned to look along `outward`."""
    bm = part.bm
    va = [bm.verts.new(p) for p in la]
    vb = [bm.verts.new(p) for p in lb]
    out = Vector(outward)
    for k in range(len(la) - 1):
        a0, a1, b0 = Vector(la[k]), Vector(la[k + 1]), Vector(lb[k])
        if (a1 - a0).cross(b0 - a0).dot(out) >= 0:
            bm.faces.new((va[k], va[k + 1], vb[k + 1], vb[k]))
        else:
            bm.faces.new((va[k], vb[k], vb[k + 1], va[k + 1]))


def wall_xy(wall, t, r):
    """A point on a wall: t along it, r in from its crest plane."""
    if wall == "front":
        return (-HX + r, t)
    if wall == "back":
        return (HX - r, t)
    if wall == "east":
        return (t, -HY + r)
    return (t, HY - r)


OUTWARD = {"front": (-1, 0, 0), "back": (1, 0, 0), "east": (0, -1, 0), "west": (0, 1, 0)}


def corrugated(wall, t0, t1, n, name, weight, z0=BASE_H, z1=WALL_TOP, lod=3):
    """One run of trapezoidal sheet, outer skin only: n ridges between t0 and t1, starting and ending part way up a valley."""
    p = piece(BODY, lod, name=name, weight=weight)
    pitch = (t1 - t0) / n
    prof = [(t0, DEPTH)]
    for k in range(n):
        tc = t0 + (k + 0.5) * pitch
        prof += [(tc - 0.35 * pitch, DEPTH), (tc - 0.15 * pitch, 0.0), (tc + 0.15 * pitch, 0.0), (tc + 0.35 * pitch, DEPTH)]
    prof.append((t1, DEPTH))
    pts = [wall_xy(wall, t, r) for t, r in prof]
    grid_strip(p, [(x, y, z0) for x, y in pts], [(x, y, z1) for x, y in pts], OUTWARD[wall])
    p.planar = wall
    return p


# ---------------------------------------------------------------- the base and the frame
def base_frame():
    members = [
        ((-46.4, DOOR_HALF, 0.0), (-43.0, 61.4, BASE_H), "base front west"),
        ((-46.4, -61.4, 0.0), (-43.0, -DOOR_HALF, BASE_H), "base front east"),
        ((43.0, -61.4, 0.0), (46.4, 61.4, BASE_H), "base back"),
        ((-43.0, 58.0, 0.0), (43.0, 61.4, BASE_H), "base west"),
        ((-43.0, -61.4, 0.0), (43.0, -58.0, BASE_H), "base east"),
    ]
    for lo, hi, name in members:
        side = name.endswith("west") or name.endswith("east")
        long_side = "west" in name.split()[-1:] or "east" in name.split()[-1:]
        weight = 0.9 if "front" in name else (0.6 if name == "base east" else 0.25)
        joined = name in ("base west", "base east")
        box_part(DARK, 3, lo, hi, bevel=0.3, segs=1, name="base channel", weight=weight,
                 drop=(lambda f: abs(f.normal.x) > 0.9 or f.normal.z < -0.9) if joined else (lambda f: f.normal.z < -0.9))
    # Anchor brackets: an angle with a foot flat on the deck and a lug up the channel's outer face, one bolt through the foot.
    # (side, position along the side)
    spots = [("front", 40.0), ("front", -40.0), ("back", 30.0), ("back", -30.0), ("west", 25.0), ("west", -25.0), ("east", 25.0), ("east", -25.0)]
    for side, t in spots:
        w_ = 0.9 if side in ("front", "east") else 0.3
        if side == "front":
            origin, out = (-46.4, t, 0.0), (-1, 0, 0)
        elif side == "back":
            origin, out = (46.4, t, 0.0), (1, 0, 0)
        elif side == "west":
            origin, out = (t, 61.4, 0.0), (0, 1, 0)
        else:
            origin, out = (t, -61.4, 0.0), (0, -1, 0)
        # Local Z is out from the channel, local X is up: the box is (height, along, out).
        m = frame(origin, out, x=(0, 0, 1))
        box_part(GALV, 1, (0.0, -3.0, 0.0), (0.7, 3.0, 4.6), bevel=0.12, name="anchor foot", weight=w_, drop=lambda f: f.normal.z < -0.9, m=m)
        box_part(GALV, 1, (0.7, -3.0, 0.0), (4.2, 3.0, 0.8), bevel=0.1, name="anchor lug", weight=w_,
                 drop=lambda f, o=Vector(out): f.normal.z < -0.9 or f.normal.dot(o) < -0.97, m=m)
        bolt(m @ Vector((0.7, 0.0, 2.9)), (0, 0, 1), 1.3, lod=1, washer=True, finish=ZINC, stud=0.7, weight=w_)


def posts():
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1 = (-45.8, -41.0) if sx < 0 else (41.0, 45.8)
            y0, y1 = (POST_IN, POST_OUT) if sy > 0 else (-POST_OUT, -POST_IN)
            front = sx < 0
            east = sy < 0
            weight = 0.9 if (front and east) else (0.8 if front else (0.5 if east else 0.2))
            box_part(DARK, 3, (x0, y0, BASE_H), (x1, y1, WALL_TOP), bevel=0.35, segs=2, name="corner post", weight=weight,
                     drop=lambda f: f.normal.z < -0.9)


# ---------------------------------------------------------------- the walls
def walls():
    # Front: a flat pilaster for the door and lamp, closure channels, and two corrugated bays.
    # The door and its frame hide the pilaster up to z = 86, so only the strip above is detailed; the slivers either side are plain.
    for name, z0, z1, wgt in (("door pilaster low", 0.0, 86.0, 0.3), ("door pilaster", 86.0, WALL_TOP, 1.0)):
        p = piece(BODY, 3, name=name, weight=wgt)
        grid_strip(p, [(-HX, DOOR_HALF, z0), (-HX, -DOOR_HALF, z0)], [(-HX, DOOR_HALF, z1), (-HX, -DOOR_HALF, z1)], OUTWARD["front"])
        p.planar = "front"
    # Cut-away wall under the door's sill stays: the sheet goes to the floor, the threshold box is the map's.
    for sy in (-1, 1):
        y0, y1 = (DOOR_HALF, TRIM_OUT) if sy > 0 else (-TRIM_OUT, -DOOR_HALF)
        box_part(BODY, 3, (-45.9, y0, BASE_H), (-43.4, y1, WALL_TOP), bevel=0.2, name="closure channel", weight=1.0,
                 drop=lambda f: f.normal.x > 0.9 or f.normal.z < -0.9)
    # One sheet profile all round: about 3.6 in from crest to crest, 1 in deep.
    corrugated("front", TRIM_OUT, BAY_IN, 8, "front bay west", 1.0)
    corrugated("front", -BAY_IN, -TRIM_OUT, 8, "front bay east", 1.0)
    corrugated("back", -BAY_IN, BAY_IN, 31, "back wall", 0.25)
    corrugated("east", -SIDE_X, SIDE_X, 23, "east wall", 0.45)
    corrugated("west", -SIDE_X, SIDE_X, 23, "west wall", 0.25)


# ---------------------------------------------------------------- the eave cap and the roof
def cap_and_roof():
    # The cap is four straight bars round the top, 3 in wide, so each is a plain strip to unwrap (a ring would wrap its islands round
    # the whole shed and cost an atlas of bounding box). The front and back bars run the full depth; the side bars fit between them.
    for lo, hi, wgt in (((-46.5, -61.5, WALL_TOP), (-43.5, 61.5, CAP_TOP), 0.8),      # front
                        ((43.5, -61.5, WALL_TOP), (46.5, 61.5, CAP_TOP), 0.25),       # back
                        ((-43.5, -61.5, WALL_TOP), (43.5, -58.5, CAP_TOP), 0.5),      # east
                        ((-43.5, 58.5, WALL_TOP), (43.5, 61.5, CAP_TOP), 0.25)):      # west
        box_part(BODY, 3, lo, hi, bevel=0.25, segs=1, name="eave cap", weight=wgt)
    # The roof: standing seams every 11.7 in, a trapezoid 1 in high, laid between the cap's inner edges.
    r = piece(GALV, 3, name="roof sheet", weight=0.4)
    y0, y1, n = -58.5, 58.5, 10
    pitch = (y1 - y0) / n
    z_flat, z_seam = 108.8, 109.8
    prof = [(y0, z_flat)]
    for k in range(n + 1):
        yc = y0 + k * pitch
        if 0 < k < n:
            prof += [(yc - 0.9, z_flat), (yc - 0.4, z_seam), (yc + 0.4, z_seam), (yc + 0.9, z_flat)]
    prof.append((y1, z_flat))
    grid_strip(r, [(-43.5, y, z) for y, z in prof], [(43.5, y, z) for y, z in prof], (0, 0, 1))
    r.planar = "roof"
    # Four lifting lugs welded to the cap's corners.
    for sx in (-1, 1):
        for sy in (-1, 1):
            # A plate with an eye, standing on the cap's 3 in top strip along each side wall, near the corner.
            lug = piece(GALV, 2, bevel=0.0, name="lifting lug", weight=0.5)
            zc = CAP_TOP + 3.0
            o = [(sx * 40.0 + px, zc + py) for px, py in rrect(7.0, 6.0, 1.5, 3)]
            i = [(sx * 40.0 + px, zc + 0.6 + py) for px, py in circle(1.35, 16)]
            ring_prism(lug, o, i, -(sy * 60.0 + 0.35), -(sy * 60.0 - 0.35), XZ)


# ---------------------------------------------------------------- the front: louvre, cabinet, conduit, plates
def front_louvre():
    yc, zc = 41.0, 70.0
    w_, h_ = 22.0, 28.0
    wgt = 0.9
    # Frame bars, 2 in wide and 2.2 deep, standing on the corrugation's crests.
    for lo, hi in (
        ((-47.2, yc - w_ / 2, zc - h_ / 2), (-45.0, yc + w_ / 2, zc - h_ / 2 + 2.0)),
        ((-47.2, yc - w_ / 2, zc + h_ / 2 - 2.0), (-45.0, yc + w_ / 2, zc + h_ / 2)),
        ((-47.2, yc - w_ / 2, zc - h_ / 2 + 2.0), (-45.0, yc - w_ / 2 + 2.0, zc + h_ / 2 - 2.0)),
        ((-47.2, yc + w_ / 2 - 2.0, zc - h_ / 2 + 2.0), (-45.0, yc + w_ / 2, zc + h_ / 2 - 2.0)),
    ):
        box_part(LIGHT, 3, lo, hi, bevel=0.2, name="louvre frame", weight=wgt, drop=lambda f: f.normal.x > 0.9)
    # The dark opening behind the blades.
    box_part(OXIDE, 2, (-45.7, yc - w_ / 2 + 2.0, zc - h_ / 2 + 2.0), (-45.5, yc + w_ / 2 - 2.0, zc + h_ / 2 - 2.0), bevel=0.0, name="louvre opening", weight=0.6,
             drop=lambda f: f.normal.x > 0.9 or abs(f.normal.y) > 0.9 or abs(f.normal.z) > 0.9)
    # Seven fixed blades, sloping down and out.
    for k in range(7):
        z = zc - h_ / 2 + 3.6 + 3.4 * k
        blade = piece(GALV, 2, name="louvre blade", weight=0.9)
        plate_xz(blade, [(-45.9, z + 1.55), (-47.4, z - 0.95), (-47.35, z - 1.15), (-45.85, z + 1.35)], yc - w_ / 2 + 2.0, yc + w_ / 2 - 2.0)
    for dy in (-1, 1):
        for dz in (-1, 1):
            bolt((-47.2, yc + dy * (w_ / 2 - 1.0), zc + dz * (h_ / 2 - 1.0)), (-1, 0, 0), 0.7, lod=0, washer=False, finish=ZINC, weight=0.9)
    # A drip hood over the frame, so rain runs off in front of the blades.
    top = zc + h_ / 2
    hood = piece(LIGHT, 2, bevel=0.06, name="louvre hood", weight=0.9)
    plate_xz(hood, [(-45.0, top + 3.0), (-49.0, top + 1.2), (-49.0, top + 0.2), (-45.0, top + 1.8)], yc - w_ / 2 - 1.0, yc + w_ / 2 + 1.0)


def front_cabinet():
    wgt = 1.0
    y_a, y_b = -53.0, -32.0
    z_a, z_b = 30.0, 60.0
    x_back, x_front = -46.2, -53.2
    # Two strut rails it hangs on, wider than the cabinet, standing on the crests.
    for z in (33.0, 56.4):
        box_part(GALV, 2, (-46.3, y_a - 2.0, z), (-45.0, y_b + 2.0, z + 1.7), bevel=0.1, name="strut rail", weight=0.8, drop=lambda f: f.normal.x > 0.9)
        for yy in (y_a - 1.0, y_b + 1.0):
            bolt((-46.3, yy, z + 0.85), (-1, 0, 0), 0.8, lod=0, washer=False, finish=ZINC, weight=0.8)
    box_part(LIGHT, 3, (x_front, y_a, z_a), (x_back, y_b, z_b), bevel=0.45, segs=2, name="cabinet body", weight=wgt, drop=lambda f: f.normal.x > 0.9)
    box_part(LIGHT, 3, (x_front - 0.7, y_a + 1.0, z_a + 1.0), (x_front, y_b - 1.0, z_b - 1.0), bevel=0.2, name="cabinet door", weight=wgt, drop=lambda f: f.normal.x > 0.9)
    # Hinge barrels on the side towards the door, a pull handle and a lock on the other.
    for z in (z_a + 6.0, z_b - 10.0):
        h = piece(OXIDE, 1, name="hinge", weight=0.9)
        lathe(h, [(0.5, 0.0), (0.5, 4.0), (0.0, 4.0)], 8, frame((x_front - 0.5, y_b - 0.3, z), (0, 0, 1)))
    for z in (z_a + 9.0, z_b - 9.0):
        box_part(OXIDE, 1, (x_front - 1.9, y_a + 2.2, z - 0.4), (x_front - 0.7, y_a + 3.0, z + 0.4), bevel=0.05, name="handle post", weight=0.9, drop_dir=(-1, 0, 0))
    bar = piece(OXIDE, 1, name="pull handle", weight=0.9)
    tube(bar, [Vector((x_front - 2.1, y_a + 2.6, z_a + 9.0)), Vector((x_front - 2.1, y_a + 2.6, z_b - 9.0))], 0.4, 6)
    lock = piece(BRASS, 1, name="lock", weight=0.9)
    lathe(lock, [(0.8, 0.0), (0.8, 0.35), (0.55, 0.4), (0.0, 0.4)], 10, frame((x_front - 0.7, y_a + 4.6, 45.0), (-1, 0, 0)))
    lock.drop_dir = Vector((-1, 0, 0))
    # A rain hood over it: a sheet sloping down and out, with cheeks.
    hood = piece(LIGHT, 3, bevel=0.08, name="rain hood", weight=0.9)
    plate_xz(hood, [(-45.0, z_b + 6.0), (-57.5, z_b + 2.0), (-57.5, z_b + 0.9), (-45.0, z_b + 4.9)], y_a - 1.2, y_b + 1.2)
    for yy in (y_a - 1.2, y_b + 1.2 - 0.14):
        cheek = piece(LIGHT, 2, name="hood cheek", weight=0.9)
        plate_xz(cheek, [(-45.0, z_b + 4.9), (-57.5, z_b + 0.9), (-57.5, z_b - 0.4), (-45.0, z_b - 0.4)], yy, yy + 0.14)
    # Conduit: out of the cabinet's side, bending back to the wall, up to the eave and along it to a junction box.
    path = [(-49.7, y_b - 0.2, 48.0), (-49.7, y_b + 1.4, 48.0), (-48.5, -29.8, 49.0), (-47.0, -29.5, 52.0), (-47.0, -29.5, 98.0), (-47.0, -29.5, 102.6), (-47.0, -30.8, 104.4), (-47.0, -33.5, 104.5), (-47.0, -53.0, 104.5)]
    tube(piece(GALV, 2, name="conduit", weight=0.7), kit.spline(path, 3), 0.55, 8)
    for z in (62.0, 78.0, 94.0):
        box_part(ZINC, 1, (-47.5, -30.4, z - 0.3), (-45.0, -28.6, z + 0.3), bevel=0.06, name="conduit clamp", weight=0.7, drop_dir=(-1, 0, 0))
    for yy in (-38.0, -46.0):
        box_part(ZINC, 1, (-47.5, yy - 0.3, 103.6), (-45.0, yy + 0.3, 105.4), bevel=0.06, name="conduit clamp", weight=0.7, drop_dir=(-1, 0, 0))
    box_part(GALV, 2, (-49.0, -56.0, 102.6), (-45.0, -52.4, 106.4), bevel=0.2, name="junction box", weight=0.7, drop_dir=(-1, 0, 0))
    # Plates, 0.16 in thick: a notice above the hood on the sheet's crests, and the shock warning on the cabinet's door.
    # Only the face you read is kept: a 0.16 in edge is not worth an atlas island.
    box_part(PLATE, 2, (-45.16, -54.0, 74.0), (-45.0, -32.0, 83.0), bevel=0.0, name="plate auth", weight=1.8, drop=lambda f: f.normal.x > -0.9)
    box_part(PLATE, 2, (x_front - 0.7 - 0.16, -47.0, 44.5), (x_front - 0.7, -38.0, 53.5), bevel=0.0, name="plate danger", weight=1.8, drop=lambda f: f.normal.x > -0.9)


# ---------------------------------------------------------------- the side walls: boots, gland box
def pipe_boot(x, z, side):
    """A flanged boot where a deck pipe (radius 7) goes through a side wall: ring plate, two rubber collars, eight bolts."""
    s = 1 if side == "west" else -1
    y_wall = s * HY
    # Local Z of the frame points out from the wall, along the Y axis.
    m = frame((x, y_wall, z), (0, s, 0), x=(1, 0, 0))
    n = 24
    ring = piece(GALV, 3, bevel=0.1, name="boot flange", weight=0.7 if side == "east" else 0.2)
    ring_prism(ring, circle(10.6, n), circle(7.4, n), 0.0, 1.3, m)
    c1 = piece(RUBBER, 2, bevel=0.0, name="boot collar", weight=0.7 if side == "east" else 0.2)
    ring_prism(c1, circle(8.8, n), circle(7.15, n), 1.3, 2.6, m)
    c2 = piece(RUBBER, 2, bevel=0.0, name="boot collar", weight=0.7 if side == "east" else 0.2)
    ring_prism(c2, circle(8.0, n), circle(7.1, n), 2.6, 3.7, m)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        p = m @ Vector((9.5 * math.cos(a), 9.5 * math.sin(a), 1.3))
        bolt(p, (0, s, 0), 1.0, lod=1, washer=False, finish=ZINC, weight=0.7 if side == "east" else 0.2)


def side_walls():
    pipe_boot(19.0, 22.0, "east")
    pipe_boot(19.0, 22.0, "west")
    # A cable gland box on the east wall, with the conduit it feeds going up to the eave.
    wgt = 0.6
    box_part(LIGHT, 3, (-32.0, -66.0, 52.0), (-18.0, -60.0, 72.0), bevel=0.4, segs=2, name="gland box", weight=wgt, drop=lambda f: f.normal.y > 0.9)
    box_part(LIGHT, 2, (-31.0, -66.7, 53.0), (-19.0, -66.0, 71.0), bevel=0.15, name="gland box lid", weight=wgt, drop=lambda f: f.normal.y > 0.9)
    for x in (-28.0, -25.0, -22.0):
        g = piece(OXIDE, 1, name="gland", weight=wgt)
        lathe(g, [(0.9, 0.0), (0.9, 0.7), (0.65, 0.75), (0.65, 2.3), (0.0, 2.35)], 8, frame((x, -63.0, 52.0), (0, 0, -1)))
        g.drop_dir = Vector((0, 0, -1))
    for dx in (-1, 1):
        for dz in (-1, 1):
            bolt((-25.0 + dx * 5.2, -66.7, 62.0 + dz * 8.0), (0, -1, 0), 0.7, lod=0, washer=False, finish=ZINC, weight=wgt)
    tube(piece(GALV, 2, name="conduit", weight=wgt), [Vector((-25.0, -61.2, 72.0)), Vector((-25.0, -61.2, 102.5)), Vector((-25.0, -61.2, 104.0))], 0.55, 8)
    for z in (80.0, 92.0):
        box_part(ZINC, 1, (-25.9, -62.0, z - 0.3), (-24.1, -60.0, z + 0.3), bevel=0.06, name="conduit clamp", weight=wgt, drop_dir=(0, -1, 0))
    box_part(GALV, 2, (-27.5, -64.0, 102.0), (-22.5, -60.0, 106.2), bevel=0.15, name="junction box", weight=wgt, drop=lambda f: f.normal.y > 0.9)
    # A name plate under the gland box, 0.16 in thick on the sheet's crests.
    box_part(PLATE, 2, (-31.0, -60.16, 36.0), (-19.0, -60.0, 43.0), bevel=0.0, name="plate side", weight=1.4, drop=lambda f: f.normal.y > -0.9)


# ---------------------------------------------------------------- the roof's equipment
def roof_equipment():
    zr = 109.8
    wgt = 0.5
    # A package air conditioner on a curb: casing, coil grilles, a fan under a guard, a disconnect.
    ax0, ax1, ay0, ay1 = -2.0, 26.0, -38.5, -5.5
    box_part(GALV, 3, (ax0 - 0.5, ay0 - 0.5, zr), (ax1 + 0.5, ay1 + 0.5, zr + 3.2), bevel=0.2, name="ac curb", weight=wgt, drop=lambda f: f.normal.z < -0.9)
    box_part(LIGHT, 3, (ax0, ay0, zr + 3.2), (ax1, ay1, zr + 19.0), bevel=0.55, segs=2, name="ac casing", weight=wgt, drop=lambda f: f.normal.z < -0.9)
    for lo, hi in (((ax0 - 0.35, ay0 + 3.0, zr + 6.5), (ax0 + 0.2, ay1 - 3.0, zr + 16.5)), ((ax0 + 3.0, ay0 - 0.35, zr + 6.5), (ax1 - 3.0, ay0 + 0.2, zr + 16.5))):
        box_part(OXIDE, 2, lo, hi, bevel=0.0, name="ac grille", weight=wgt, drop=lambda f: False)
    cx, cy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
    z_top = zr + 19.0
    shroud = piece(GALV, 2, name="ac fan shroud", weight=wgt)
    lathe(shroud, [(11.6, z_top), (11.6, z_top + 1.6), (10.7, z_top + 1.9), (10.2, z_top + 1.6)], 20, frame((cx, cy, 0.0), (0, 0, 1)))
    shroud.drop = lambda f: f.normal.z < -0.9
    fan = piece(OXIDE, 1, name="ac fan", weight=wgt)
    lathe(fan, [(10.3, z_top + 0.2), (10.3, z_top + 0.5), (1.4, z_top + 0.9), (0.0, z_top + 1.2)], 20, frame((cx, cy, 0.0), (0, 0, 1)))
    for r_ in (4.8, 8.6):
        tube(piece(ZINC, 0, name="ac guard ring", weight=wgt), [Vector((cx + r_ * math.cos(a), cy + r_ * math.sin(a), z_top + 1.7)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)], 0.2, 4, closed=True)
    for k in range(6):
        a = 2 * math.pi * k / 6
        tube(piece(ZINC, 0, name="ac guard spoke", weight=wgt), [Vector((cx + 0.6 * math.cos(a), cy + 0.6 * math.sin(a), z_top + 1.9)), Vector((cx + 10.9 * math.cos(a), cy + 10.9 * math.sin(a), z_top + 1.7))], 0.2, 4)
    box_part(LIGHT, 2, (ax1, ay1 - 12.0, zr + 8.0), (ax1 + 3.6, ay1 - 4.0, zr + 15.0), bevel=0.25, name="ac disconnect", weight=wgt, drop=lambda f: f.normal.x < -0.9)
    for dx in (ax0 + 1.5, ax1 - 1.5):
        for dy in (ay0 + 1.5, ay1 - 1.5):
            bolt((dx, dy, zr + 3.2), (0, 0, 1), 0.9, lod=0, washer=False, finish=ZINC, weight=wgt)
    # A mushroom vent on a collar.
    vc = (20.0, 38.0)
    col = piece(GALV, 3, bevel=0.0, name="vent collar", weight=wgt)
    lathe(col, [(5.2, zr), (5.2, zr + 2.4), (4.7, zr + 2.6), (4.7, zr + 8.0)], 14, frame((vc[0], vc[1], 0.0), (0, 0, 1)))
    col.drop = lambda f: f.normal.z < -0.9
    cap_ = piece(GALV, 3, bevel=0.0, name="vent cowl", weight=wgt)
    lathe(cap_, [(4.2, zr + 8.0), (9.8, zr + 9.6), (9.9, zr + 10.6), (6.4, zr + 13.2), (0.0, zr + 14.0)], 14, frame((vc[0], vc[1], 0.0), (0, 0, 1)))
    for a in (0, 120, 240):
        t = math.radians(a)
        stay = piece(GALV, 1, name="vent stay", weight=wgt)
        tube(stay, [Vector((vc[0] + 4.6 * math.cos(t), vc[1] + 4.6 * math.sin(t), zr + 7.9)), Vector((vc[0] + 8.0 * math.cos(t), vc[1] + 8.0 * math.sin(t), zr + 9.6))], 0.25, 4)
    # A roof hatch: curb, lid, two hinges, a pull and a hasp.
    hx0, hx1, hy0, hy1 = -31.0, -7.0, 19.0, 43.0
    box_part(GALV, 3, (hx0, hy0, zr), (hx1, hy1, zr + 4.0), bevel=0.2, name="hatch curb", weight=wgt, drop=lambda f: f.normal.z < -0.9)
    box_part(LIGHT, 3, (hx0 - 0.9, hy0 - 0.9, zr + 4.0), (hx1 + 0.9, hy1 + 0.9, zr + 5.6), bevel=0.4, segs=2, name="hatch lid", weight=wgt, drop=lambda f: f.normal.z < -0.9)
    for yy in (hy0 + 5.0, hy1 - 5.0):
        box_part(OXIDE, 1, (hx1 + 0.2, yy - 1.8, zr + 3.2), (hx1 + 1.8, yy + 1.8, zr + 6.0), bevel=0.08, name="hatch hinge", weight=wgt, drop=lambda f: f.normal.z < -0.9)
    tube(piece(OXIDE, 1, name="hatch pull", weight=wgt), [Vector((hx0 + 3.0, (hy0 + hy1) / 2 - 4.0, zr + 7.4)), Vector((hx0 + 3.0, (hy0 + hy1) / 2 + 4.0, zr + 7.4))], 0.35, 6)
    for yy in (-4.0, 4.0):
        box_part(OXIDE, 1, (hx0 + 2.6, (hy0 + hy1) / 2 + yy - 0.4, zr + 5.6), (hx0 + 3.4, (hy0 + hy1) / 2 + yy + 0.4, zr + 7.1), bevel=0.04, name="hatch pull post", weight=wgt, drop=lambda f: f.normal.z < -0.9)
    # An antenna on a base plate at the back corner.
    ax, ay = 35.0, -49.0
    box_part(GALV, 2, (ax - 3.5, ay - 3.5, zr), (ax + 3.5, ay + 3.5, zr + 0.6), bevel=0.1, name="antenna plate", weight=0.3, drop=lambda f: f.normal.z < -0.9)
    for dx in (-2.4, 2.4):
        for dy in (-2.4, 2.4):
            bolt((ax + dx, ay + dy, zr + 0.6), (0, 0, 1), 0.8, lod=0, washer=False, finish=ZINC, weight=0.3)
    mast = piece(GALV, 1, name="antenna mast", weight=0.3)
    lathe(mast, [(1.15, zr + 0.6), (1.15, zr + 30.0), (0.62, zr + 30.5), (0.62, zr + 46.0), (0.24, zr + 46.4), (0.24, zr + 62.0), (0.0, zr + 62.4)], 6, frame((ax, ay, 0.0), (0, 0, 1)))
    mast.drop = lambda f: f.normal.z < -0.9
    for z in (zr + 12.0, zr + 24.0):
        clamp = piece(ZINC, 0, name="antenna clamp", weight=0.3)
        lathe(clamp, [(1.15, z), (1.7, z), (1.7, z + 1.2), (1.15, z + 1.2)], 8, frame((ax, ay, 0.0), (0, 0, 1)))


def geometry():
    base_frame()
    posts()
    walls()
    cap_and_roof()
    front_louvre()
    front_cabinet()
    side_walls()
    roof_equipment()


# ---------------------------------------------------------------- build stage
edge_lines = []
PLANAR = {}


def harden_all():
    rng = np.random.default_rng(4121)
    count = len(kit.parts)
    perm = rng.permutation(count)
    for index, p in enumerate(kit.parts):
        bm = p.bm
        bm.normal_update()
        if all(len(e.link_faces) == 2 for e in bm.edges) and len(bm.edges):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                a, b = e.verts[0].co, e.verts[1].co
                n = max(1, int((b - a).length / 0.25))
                for k in range(n + 1):
                    edge_lines.append(tuple(a.lerp(b, k / n)))
        kit.harden(p)
        bm.normal_update()
        doomed = []
        for f in bm.faces:
            if p.drop is not None and p.drop(f):
                doomed.append(f)
            elif p.drop_dir is not None and f.normal.dot(Vector(p.drop_dir)) < -0.97:
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
        part.first_face = len(faces)
        for f in bm.faces:
            faces.append(tuple(v.index + offset for v in f.verts))
            fin.append(part.finish)
            rnd.append(part.rand)
            wgt.append(part.weight)
        part.n_faces = len(faces) - part.first_face
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
    shape_waste = {}
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
        key = round(faces[0].loops[0][facts][1], 4)
        t = shape_waste.setdefault(LOOKUP[key].name, [0.0, 0.0, 0])
        t[0] += area3 * weight * weight
        t[1] += w * h
        t[2] += 1

    def attempt(density, order):
        """Guillotine packing, best area fit: each island goes in the free rectangle it leaves least room in, free to turn a
        quarter, and that rectangle is cut along its shorter leftover side. Much tighter than shelves for islands this mixed."""
        pad = pad_px / density
        limit = res / density
        free = np.array([[0.0, 0.0, limit, limit]])
        places = {}
        for w, h, n, *_ in order:
            bw, bh = w + 2 * pad, h + 2 * pad
            fw, fh = free[:, 2], free[:, 3]
            best = None
            for turned, (rw, rh) in ((False, (bw, bh)), (True, (bh, bw))):
                fits = (fw >= rw - 1e-7) & (fh >= rh - 1e-7)
                if fits.any():
                    waste = np.where(fits, fw * fh - rw * rh, np.inf)
                    i = int(np.argmin(waste))
                    if best is None or waste[i] < best[0]:
                        best = (waste[i], i, turned, rw, rh)
            if best is None:
                return None
            _, i, turned, rw, rh = best
            x, y, fw_i, fh_i = free[i]
            places[n] = (x + pad, y + pad, turned)
            right_w, below_h = fw_i - rw, fh_i - rh
            rest = []
            if right_w <= below_h:
                if right_w > 1e-6:
                    rest.append((x + rw, y, right_w, rh))
                if below_h > 1e-6:
                    rest.append((x, y + rh, fw_i, below_h))
            else:
                if right_w > 1e-6:
                    rest.append((x + rw, y, right_w, fh_i))
                if below_h > 1e-6:
                    rest.append((x, y + rh, rw, below_h))
            free = np.delete(free, i, axis=0)
            if rest:
                free = np.vstack([free, np.array(rest).reshape(-1, 4)])
        return places

    lost = sorted(shape_waste.items(), key=lambda kv: -(kv[1][1] - kv[1][0]))
    print("islands: true area, bounding rectangles (weighted in2, before padding)", round(sum(v[0] for v in shape_waste.values())), round(sum(v[1] for v in shape_waste.values())), flush=True)
    for name, (true_a, rect_a, count) in lost[:14]:
        print("  waste %-18s %3d islands  true %8.0f  rect %8.0f" % (name, count, true_a, rect_a), flush=True)
    orders = {
        "area": sorted(rects, key=lambda r: -(r[0] * r[1])),
        "long side": sorted(rects, key=lambda r: (-max(r[0], r[1]), -(r[0] * r[1]))),
    }
    density, places, how = 0.0, None, ""
    for label, order in orders.items():
        lo, hi = 1.0, 200.0
        got_best = None
        for _ in range(26):
            mid = (lo + hi) / 2
            got = attempt(mid, order)
            if got:
                got_best, lo = got, mid
            else:
                hi = mid
        print("packing by", label, "-> %.2f px/in" % lo, flush=True)
        if got_best and lo > density:
            density, places, how = lo, got_best, label
    quarter = np.array(((0.0, -1.0), (1.0, 0.0)))
    filled = 0.0
    for w, h, n, centre, scale, rot, low in rects:
        px, py, turned = places[n]
        if turned:
            rot = quarter @ rot
            low = np.array((-(low[1] + h), low[0]))
        filled += (w + 2 * pad_px / density) * (h + 2 * pad_px / density)
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px) * density / res, (q[1] + py) * density / res)
    bm.to_mesh(mesh)
    bm.free()
    print("islands", len(rects), "packed by", how, "density px/in at weight 1: %.2f" % density, "padded rectangles fill %.3f" % (filled * density * density / (res * res)), flush=True)
    return density


def apply_planar_uv(mesh, parts):
    """Corrugated sheets, the door pilaster and the roof get one flat projection, facing out, so a wall is a single island."""
    layer = mesh.uv_layers["UVMap"]
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    for part in parts:
        mode = getattr(part, "planar", None)
        if not mode:
            continue
        for pi in range(part.first_face, part.first_face + part.n_faces):
            poly = mesh.polygons[pi]
            for li in poly.loop_indices:
                x, y, z = co[mesh.loops[li].vertex_index]
                if mode == "front":
                    uv = (-y, z)
                elif mode == "back":
                    uv = (y, z)
                elif mode == "east":
                    uv = (x, z)
                elif mode == "west":
                    uv = (-x, z)
                else:  # roof, seen from above with north up
                    uv = (-y, x)
                layer.data[li].uv = uv


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
    tally = {}
    for p in kit.parts:
        t = tally.setdefault(p.name, [0, 0])
        t[0] += len(p.done.faces)
        t[1] += 1
    for n, (t, c) in sorted(tally.items(), key=lambda kv: -kv[1][0])[:40]:
        print("  tris %5d  x%-3d %s" % (t, c, n), flush=True)

    hw = join(kit.parts, "shed_bake")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    apply_planar_uv(hw.data, kit.parts)
    density = pack_weighted(hw.data, RES, 3)
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

    mat = bpy.data.materials.new("shed_body")
    lod0 = combine([(hw.data, 0)], "shed_lod0", [mat])
    lod1 = combine([(decimated(drop_small(hw.data, 1), 0.55), 0)], "shed_lod1", [mat])
    lod2 = combine([(decimated(drop_small(hw.data, 3), 0.28), 0)], "shed_lod2", [mat])
    for ob in (lod0, lod1, lod2):
        print(ob.name, "tris", count_tris(ob.data), flush=True)

    np.save(os.path.join(WORK, "shed_edges.npy"), np.array(edge_lines, np.float32))
    meta = dict(density=density, res=RES, range=POS_RANGE, wall_top=WALL_TOP, cap_top=CAP_TOP, base_h=BASE_H, depth=DEPTH,
                parts={str(p.key): dict(name=p.name, finish=p.finish, weight=p.weight, lod=p.lod) for p in kit.parts})
    with open(os.path.join(WORK, "shed.json"), "w") as h:
        json.dump(meta, h)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved build", flush=True)


def uv_hash(ob):
    data = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers["UVMap"].data.foreach_get("uv", data)
    return hashlib.sha1(data.tobytes()).hexdigest()


# ---------------------------------------------------------------- bake stage
def cylinder(name, p0, p1, r, n=20):
    d = Vector(p1) - Vector(p0)
    m = frame(p0, tuple(d))
    verts = [tuple(m @ Vector((r * math.cos(a), r * math.sin(a), z))) for z in (0.0, d.length) for a in (2 * math.pi * k / n for k in range(n))]
    faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


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
    hw = bpy.data.objects["shed_bake"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    # What stands round it on the deck, for the AO bake only: the floor, the red container 10 in off the west wall, the deck's
    # two pipes (radius 10 on the back wall's plane, radius 7 through the side walls), and the support block at the back corner.
    occluders = []
    floor = bpy.data.meshes.new("floor")
    floor.from_pydata([(-400, -400, 0), (400, -400, 0), (400, 400, 0), (-400, 400, 0)], [], [(0, 1, 2, 3)])
    occluders.append(bpy.data.objects.new("floor", floor))
    scene.collection.objects.link(occluders[-1])

    def block(name, lo, hi):
        v = [(x, y, z) for z in (lo[2], hi[2]) for x, y in ((lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1]))]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(v, [], f)
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        occluders.append(ob)

    block("container", (-93.0, 70.0, 0.0), (3.0, 310.0, 102.0))
    block("support", (31.0, -90.0, 0.0), (55.0, -50.0, 30.0))
    for name, x, r in (("pipe a", 45.0, 10.0), ("pipe b", 19.0, 7.0)):
        occluders.append(cylinder(name, (x, -300.0, 22.0), (x, 300.0, 22.0), r))
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 9.0
    with open(os.path.join(WORK, "shed_baked_uv_hash.txt"), "w") as h:
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
        for ob in occluders:
            ob.hide_render = kind != "AO"
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_shed_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_shed_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_shed_facts")
    bake_one(1024, "AO", None, 64, "bake_shed_ao")


# ---------------------------------------------------------------- export stage
def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT_MODEL, exist_ok=True)
    os.makedirs(OUT_MAT, exist_ok=True)
    if uv_hash(bpy.data.objects["shed_bake"]) != open(os.path.join(WORK, "shed_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    materials = ["shed_body"]
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"shed_lod{number}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(45))
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
        with open(os.path.join(OUT_MODEL, f"shed_lod{number}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Orion/deck-shed-v1/shed.py\nmtllib shed.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {materials[0]}\n")
            h.writelines(faces)
        counts[number] = n_tris
        print("lod", number, "tris", n_tris, flush=True)
    with open(os.path.join(OUT_MODEL, "shed.mtl"), "w", newline="\n") as h:
        for name in materials:
            h.write(f"newmtl {name}\nKd 1 1 1\nd 1\n\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL_FOLDER}/shed_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, LOD_SWITCH))
    remaps = [("shed_body.vmat", f"{MAT_FOLDER}/shed_body.vmat")]
    remap_text = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{a}" to = "{b}" }}' for a, b in remaps)
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Orion/deck-shed-v1/shed.py
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
    with open(os.path.join(OUT_MODEL, "shed.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Orion/deck-shed-v1/shed.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MAT_FOLDER}/shed_body_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MAT_FOLDER}/shed_body_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MAT_FOLDER}/shed_body_metal.png"

	//---- Normal ----
	TextureNormal "{MAT_FOLDER}/shed_body_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MAT_FOLDER}/shed_body_rough.png"
}}
"""
    with open(os.path.join(OUT_MAT, "shed_body.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    mesh = bpy.data.objects["shed_lod0"].data
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    print("extent in (x y z) min", np.round(co.min(0), 2), "max", np.round(co.max(0), 2), flush=True)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("shed stages done", flush=True)
