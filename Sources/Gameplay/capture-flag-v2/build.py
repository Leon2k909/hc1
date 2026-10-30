"""Build the capture flag's meshes and UVs and save them as work/capture_flag_build.blend.

blender -b --factory-startup -t 2 --python build.py -- <work dir>

The asset is a field mast as an army would actually put one up: a weighted stand, a two-part telescoping mast locked by
a cam lever, three turnbuckled stays down to staked foot plates held by sandbags, and a halyard over a sheave with the
flag on two snap hooks. Inches, engine axes (+X the way the flag flies, Z up), origin on the ground at the mast.

Hard surface is mid-poly: real bevels and face-weighted normals, so it keeps its shape with no high-to-low bake, and
the normal map only carries surface detail. Soft goods (bags, flag) come from their simulations, sampled on a grid so
every LOD shares one set of UVs. No third-party meshes or textures.
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

WORK = sys.argv[sys.argv.index("--") + 1]

# Finishes, stored per face and baked to an ID map for the paint stage.
PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST = range(9)

MAST_TOP = 102.6
FLAG_LOW, FLAG_HIGH = 70.0, 97.0
ROPE_X = 2.62
FLAG_X = 3.05
YAWS = (180.0, 60.0, -60.0)
FOOT_RADIUS = 22.0
PILE_SHIFT = 0.6

rng = np.random.default_rng(1944)
parts = []


def frame(origin=(0, 0, 0), z=(0, 0, 1), x=None):
    """Matrix taking local +Z onto z."""
    zv = Vector(z).normalized()
    if x is None:
        x = (1, 0, 0) if abs(zv.x) < 0.9 else (0, 1, 0)
    yv = zv.cross(Vector(x)).normalized()
    xv = yv.cross(zv).normalized()
    m = Matrix((xv, yv, zv)).transposed().to_4x4()
    m.translation = origin
    return m


def yaw(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")


class Part:
    def __init__(self, finish, lod=3, bevel=0.0, segs=1, angle=40.0, name=""):
        self.bm = bmesh.new()
        self.finish, self.lod, self.bevel, self.segs, self.angle, self.name = finish, lod, bevel, segs, angle, name


def lathe(part, profile, sides, m=Matrix.Identity(4)):
    """Rings of (radius, z) about local Z, capped where the profile doesn't reach the axis."""
    bm = part.bm
    rings = []
    for r, z in profile:
        if r < 1e-5:
            rings.append([bm.verts.new(m @ Vector((0, 0, z)))])
        else:
            rings.append(
                [
                    bm.verts.new(m @ Vector((r * math.cos(a), r * math.sin(a), z)))
                    for a in (2 * math.pi * k / sides for k in range(sides))
                ]
            )
    # Faces wind outward for a profile climbing z. Cycles draws both sides, so getting this wrong only shows in the engine.
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            for k in range(sides):
                bm.faces.new((a[0], b[(k + 1) % sides], b[k]))
        elif len(b) == 1:
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[0]))
        else:
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    if len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1:
        bm.faces.new(list(rings[-1]))


def prism(part, outline, z0, z1, m=Matrix.Identity(4)):
    """A counter-clockwise outline in local XY, extruded along local Z."""
    bm = part.bm
    low = [bm.verts.new(m @ Vector((x, y, z0))) for x, y in outline]
    high = [bm.verts.new(m @ Vector((x, y, z1))) for x, y in outline]
    n = len(outline)
    for k in range(n):
        bm.faces.new((low[k], low[(k + 1) % n], high[(k + 1) % n], high[k]))
    bm.faces.new(list(reversed(low)))
    bm.faces.new(list(high))


def box(part, lo, hi, m=Matrix.Identity(4)):
    prism(part, [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])], lo[2], hi[2], m)


def tube(part, path, radius, sides, closed=False, caps=True, flatten=1.0, lumps=None):
    """Sweep a circle along points. radius may be one value or one per point."""
    bm = part.bm
    pts = [Vector(p) for p in path]
    n = len(pts)
    radii = radius if hasattr(radius, "__len__") else [radius] * n
    tangents = []
    for i in range(n):
        if closed:
            t = pts[(i + 1) % n] - pts[i - 1]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    u = tangents[0].cross(ref).normalized()
    rings = []
    for i in range(n):
        if i:
            axis = tangents[i - 1].cross(tangents[i])
            if axis.length > 1e-6:
                u = Matrix.Rotation(tangents[i - 1].angle(tangents[i]), 3, axis.normalized()) @ u
            u = (u - tangents[i] * u.dot(tangents[i])).normalized()
        v = tangents[i].cross(u).normalized()
        r = radii[i]
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            ring.append(bm.verts.new(pts[i] + u * (r * math.cos(a)) + v * (r * flatten * math.sin(a))))
        rings.append(ring)
    last = n if closed else n - 1
    for i in range(last):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    if caps and not closed:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(list(rings[-1]))


def ring_path(R, segs, m=Matrix.Identity(4), start=0.0, end=2 * math.pi):
    return [m @ Vector((R * math.cos(start + (end - start) * k / segs), R * math.sin(start + (end - start) * k / segs), 0)) for k in range(segs)]


def spline(points, per=8):
    """Catmull-Rom through points."""
    p = [Vector(q) for q in points]
    out = []
    for i in range(len(p) - 1):
        a, b, c, d = p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, len(p) - 1)]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * b) + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t * t * t))
    out.append(p[-1])
    return out


def add(part):
    parts.append(part)
    return part


def weld_line(a, b, r=0.11, lod=1, count=None):
    length = (Vector(b) - Vector(a)).length
    count = count or max(4, int(length / 0.45))
    path = [Vector(a).lerp(Vector(b), k / count) for k in range(count + 1)]
    radii = [r * float(rng.uniform(0.82, 1.14)) for _ in path]
    radii[0] = radii[-1] = r * 0.55
    tube(add(Part(WELD, lod, name="weld")), path, radii, 6)


def weld_ring(R, m, r=0.14, segs=64, lod=1):
    path = ring_path(R, segs, m)
    radii = [r * float(rng.uniform(0.84, 1.12)) for _ in path]
    tube(add(Part(WELD, lod, name="weld")), path, radii, 6, closed=True)


def hex_bolt(at, axis, size=0.75, lod=1, washer=True, finish=ZINC, stud=0.0):
    """A hex head on a washer, sitting on at, facing along axis."""
    m = frame(at, axis)
    z = 0.0
    if washer:
        w = add(Part(finish, lod, bevel=0.012, angle=50, name="washer"))
        lathe(w, [(size * 0.42, 0), (size * 0.92, 0), (size * 0.92, size * 0.09), (size * 0.42, size * 0.09)], 14 if size > 0.5 else 10, m)
        z = size * 0.09
    b = add(Part(finish, lod, bevel=size * 0.05, angle=40, name="bolt"))
    lathe(b, [(size * 0.66, z), (size * 0.66, z + size * 0.5), (size * 0.5, z + size * 0.56)], 6, m)
    if stud:
        s = add(Part(finish, 0, bevel=0.01, angle=50, name="stud"))
        lathe(s, [(size * 0.3, z + size * 0.56), (size * 0.3, z + size * 0.56 + stud), (size * 0.2, z + size * 0.56 + stud + 0.04), (0, z + size * 0.56 + stud + 0.04)], 8, m)


def base():
    octagon = [(-6.4, -8), (6.4, -8), (8, -6.4), (8, 6.4), (6.4, 8), (-6.4, 8), (-8, 6.4), (-8, -6.4)]
    prism(add(Part(PAINT, 3, bevel=0.07, segs=2, name="base plate")), octagon, 0.0, 0.62)
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        hex_bolt((sx * 6.2, sy * 6.2, 0.62), (0, 0, 1), 0.85, lod=1, stud=0.32)
    lathe(
        add(Part(PAINT, 3, bevel=0.07, segs=2, angle=30, name="socket")),
        [(2.28, 0.62), (2.28, 10.3), (2.78, 10.5), (2.78, 12.15), (2.65, 12.28), (1.62, 12.28)],
        32,
    )
    weld_ring(2.36, frame((0, 0, 0.72)), 0.17, 72, lod=2)
    weld_ring(2.34, frame((0, 0, 10.32)), 0.1, 56, lod=1)
    gusset = [(2.24, 0.62), (6.7, 0.62), (6.7, 1.45), (2.95, 7.6), (2.24, 7.6)]
    for a in (45, 135, 225, 315):
        m = yaw(a) @ Matrix.Rotation(math.radians(90), 4, "X")
        prism(add(Part(PAINT, 2, bevel=0.05, segs=2, name="gusset")), gusset, -0.21, 0.21, m)
        for side in (-0.24, 0.24):
            rot = yaw(a)
            weld_line(rot @ Vector((2.5, side, 0.74)), rot @ Vector((6.55, side, 0.74)), 0.1, lod=1)
            weld_line(rot @ Vector((2.33, side, 0.78)), rot @ Vector((2.33, side, 7.45)), 0.1, lod=1)
    # The mast is held in the socket by a T-handled screw.
    z = 11.35
    lathe(add(Part(PAINT, 2, bevel=0.03, angle=30, name="boss")), [(0.62, 2.45), (0.62, 3.2), (0.48, 3.3), (0.32, 3.3)], 16, frame((0, 0, z), (0, 1, 0)))
    lathe(add(Part(ZINC, 2, bevel=0.015, angle=30, name="screw")), [(0.3, 3.2), (0.3, 4.5), (0.42, 4.55), (0.42, 4.95), (0.3, 5.0)], 12, frame((0, 0, z), (0, 1, 0)))
    bar = add(Part(OXIDE, 2, bevel=0.02, angle=35, name="t handle"))
    lathe(bar, [(0.24, -1.85), (0.24, 1.85)], 12, frame((0, 4.74, z), (1, 0, 0)))
    for s in (-1, 1):
        lathe(
            add(Part(OXIDE, 1, name="t handle end")),
            [(0.0, -0.36), (0.22, -0.3), (0.34, -0.1), (0.34, 0.1), (0.22, 0.3), (0.0, 0.36)],
            12,
            frame((s * 2.05, 4.74, z), (1, 0, 0)),
        )
    # A riveted data plate on the socket, wrapped to its curve.
    R = 2.31
    plate = add(Part(PLATE, 2, bevel=0.012, angle=40, name="data plate"))
    bm = plate.bm
    cols = 8
    a0, a1 = math.radians(180 - 42), math.radians(180 + 42)
    z0, z1 = 3.1, 5.0
    outer, inner = [], []
    for row, zz in enumerate((z0, z1)):
        o = [bm.verts.new((( R + 0.05) * math.cos(a0 + (a1 - a0) * k / cols), (R + 0.05) * math.sin(a0 + (a1 - a0) * k / cols), zz)) for k in range(cols + 1)]
        i = [bm.verts.new(((R - 0.03) * math.cos(a0 + (a1 - a0) * k / cols), (R - 0.03) * math.sin(a0 + (a1 - a0) * k / cols), zz)) for k in range(cols + 1)]
        outer.append(o)
        inner.append(i)
    for k in range(cols):
        bm.faces.new((outer[0][k], outer[0][k + 1], outer[1][k + 1], outer[1][k]))
        bm.faces.new((outer[0][k], inner[0][k], inner[0][k + 1], outer[0][k + 1]))
        bm.faces.new((outer[1][k], outer[1][k + 1], inner[1][k + 1], inner[1][k]))
    for row in (0, 1):
        pass
    bm.faces.new((outer[0][0], outer[1][0], inner[1][0], inner[0][0]))
    bm.faces.new((outer[0][cols], inner[0][cols], inner[1][cols], outer[1][cols]))
    for a in (a0 + math.radians(5), a1 - math.radians(5)):
        for zz in (z0 + 0.22, z1 - 0.22):
            axis = Vector((math.cos(a), math.sin(a), 0))
            lathe(
                add(Part(PLATE, 0, name="rivet")),
                [(0.11, 0), (0.1, 0.035), (0.05, 0.06), (0, 0.065)],
                8,
                frame(axis * (R + 0.04) + Vector((0, 0, zz)), axis),
            )


def mast():
    lathe(add(Part(PAINT, 3, bevel=0.0, angle=89, name="lower mast")), [(1.6, 12.28), (1.6, 53.5)], 28)
    lathe(add(Part(GALV, 3, angle=89, name="upper mast")), [(1.2, 56.6), (1.2, 99.6)], 24)

    # The stay collar, clamped with two screws and carrying three pairs of lugs.
    lathe(
        add(Part(OXIDE, 3, bevel=0.03, angle=30, name="stay collar")),
        [(1.62, 43.9), (1.98, 43.95), (2.12, 44.15), (2.12, 46.65), (1.98, 46.85), (1.62, 46.9)],
        32,
    )
    for k, deg in enumerate(YAWS):
        rot = yaw(deg)
        for side in (-0.46, 0.46):
            outline = [(1.95, 44.3), (3.1, 44.55), (3.95, 45.3), (3.95, 46.1), (3.5, 46.5), (1.95, 46.5)]
            m = rot @ Matrix.Translation((0, side, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")
            prism(add(Part(OXIDE, 2, bevel=0.03, name="lug")), outline, -0.14, 0.14, m)
        pin = rot @ Matrix.Translation((3.5, 0, 45.65)) @ frame((0, 0, 0), (0, 1, 0))
        lathe(add(Part(ZINC, 2, bevel=0.012, angle=30, name="pin")), [(0.23, -0.78), (0.23, 0.72), (0.34, 0.74), (0.34, 0.86), (0.22, 0.92), (0, 0.92)], 10, pin)
        # A hairpin keeps each pin in; small enough to fall off at the first LOD.
        hairpin = spline(
            [
                rot @ Vector((3.5, -0.84, 45.7)),
                rot @ Vector((3.5, -0.84, 45.25)),
                rot @ Vector((3.56, -0.84, 44.95)),
                rot @ Vector((3.75, -0.84, 45.2)),
                rot @ Vector((3.75, -0.84, 45.6)),
            ],
            3,
        )
        tube(add(Part(ZINC, 0, name="hairpin")), hairpin, 0.035, 5)
    for deg in (0, 120):
        axis = yaw(deg) @ Vector((1, 0, 0))
        hex_bolt(axis * 2.08 + Vector((0, 0, 45.4)), axis, 0.42, lod=0, washer=False, finish=OXIDE)

    # The telescoping joint with its cam lever.
    lathe(
        add(Part(OXIDE, 3, bevel=0.03, angle=30, name="joint collar")),
        [(1.62, 53.3), (1.98, 53.35), (2.15, 53.55), (2.15, 55.45), (1.98, 55.65), (1.9, 55.7), (1.9, 56.25), (1.5, 56.95), (1.22, 57.0)],
        32,
    )
    for side in (-0.42, 0.42):
        box(add(Part(OXIDE, 2, bevel=0.04, name="clamp ear")), (side - 0.2, 1.9, 53.65), (side + 0.2, 3.05, 55.35))
    lathe(add(Part(ZINC, 2, bevel=0.012, angle=30, name="clamp pin")), [(0.2, -0.86), (0.2, 0.86), (0.3, 0.88), (0.3, 1.0), (0, 1.0)], 10, frame((0, 2.62, 54.5), (1, 0, 0)))
    lever = spline([(0, 2.62, 54.5), (0, 2.78, 55.6), (0, 2.72, 57.4), (0, 2.42, 60.0), (0, 2.16, 61.9)], 4)
    tube(add(Part(OXIDE, 2, name="lever")), lever, 0.2, 10, flatten=0.8)
    grip = spline([(0, 2.72, 57.5), (0, 2.42, 60.0), (0, 2.14, 62.1)], 4)
    tube(add(Part(RUBBER, 2, name="lever grip")), grip, [0.3] * 8 + [0.3 * 0.7], 10, flatten=0.85)
    # The index pin and its pull ring.
    m = frame((0, -1.18, 60.0), (0, -1, 0))
    lathe(add(Part(ZINC, 1, bevel=0.01, angle=30, name="index boss")), [(0.46, 0), (0.46, 0.34), (0.3, 0.42), (0.2, 0.42)], 12, m)
    lathe(add(Part(ZINC, 1, name="index pin")), [(0.17, 0.4), (0.17, 0.96), (0.1, 1.02), (0, 1.02)], 8, m)
    tube(add(Part(ZINC, 0, name="pull ring")), ring_path(0.52, 18, frame((0, -2.06, 59.46), (1, 0, 0))), 0.055, 6, closed=True)

    # The truck, its finial and the sheave the halyard runs over.
    lathe(
        add(Part(GALV, 3, bevel=0.02, angle=30, name="truck")),
        [(1.2, 99.5), (1.42, 99.55), (1.52, 99.72), (1.52, 100.9), (1.34, 101.06), (0.84, 101.14)],
        24,
    )
    lathe(
        add(Part(BRASS, 3, name="finial")),
        [(0.44, 101.1), (0.5, 101.3), (0.62, 101.42), (0.74, 101.7), (0.72, 102.0), (0.56, 102.3), (0.28, 102.54), (0, MAST_TOP)],
        20,
    )
    cheek = [(1.15, 99.55), (2.45, 99.62), (2.92, 100.15), (2.92, 100.42), (2.45, 100.9), (1.15, 100.95)]
    for side in (-0.31, 0.31):
        m = Matrix.Translation((0, side, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")
        prism(add(Part(GALV, 2, bevel=0.022, name="cheek")), cheek, -0.06, 0.06, m)
    sheave = frame((2.02, 0, 100.28), (0, 1, 0))
    lathe(
        add(Part(BRASS, 2, angle=30, name="sheave")),
        [(0, -0.25), (0.62, -0.25), (0.66, -0.2), (0.49, -0.02), (0.49, 0.02), (0.66, 0.2), (0.62, 0.25), (0, 0.25)],
        20,
        sheave,
    )
    lathe(add(Part(ZINC, 1, name="axle")), [(0, -0.46), (0.11, -0.46), (0.11, 0.46), (0, 0.46)], 8, sheave)

    # The horn cleat on its band.
    lathe(add(Part(GALV, 2, bevel=0.015, angle=30, name="cleat band")), [(1.61, 39.1), (1.7, 39.14), (1.7, 40.86), (1.61, 40.9)], 28)
    for side in (-1.05, 1.05):
        box(add(Part(GALV, 2, bevel=0.06, segs=2, name="cleat foot")), (1.55, side - 0.42, 39.56), (2.94, side + 0.42, 40.44))
    horn = [(3.02, y, 40.0) for y in np.linspace(-3.25, 3.25, 15)]
    radii = [0.17, 0.27, 0.33, 0.37, 0.41, 0.44, 0.46, 0.47, 0.46, 0.44, 0.41, 0.37, 0.33, 0.27, 0.17]
    tube(add(Part(GALV, 2, bevel=0.0, name="cleat horn")), horn, radii, 12)


def stays():
    for deg in YAWS:
        rot = yaw(deg)
        top = rot @ Vector((3.5, 0, 45.65))
        foot = rot @ Vector((FOOT_RADIUS - 2.8, 0, 2.22))
        axis = (foot - top).normalized()
        length = (foot - top).length
        at = lambda d: top + axis * d

        def seg(finish, lod, d0, d1, r0, r1=None, sides=14):
            r1 = r0 if r1 is None else r1
            lathe(add(Part(finish, lod, name="stay")), [(r0, 0.0), (r1, d1 - d0)], sides, frame(at(d0), axis))

        tang = frame(at(0), axis)
        # Every piece of a stay lasts to the far LOD, or the stays break into floating lengths there.
        box(add(Part(OXIDE, 3, bevel=0.04, name="tang")), (-0.42, -0.26, -0.5), (0.42, 0.26, 1.3), tang)
        seg(OXIDE, 3, 1.3, 2.3, 0.42, 0.5)
        tube_end = length * 0.58
        seg(PAINT, 3, 2.3, tube_end, 0.5, sides=16)
        seg(OXIDE, 3, tube_end, tube_end + 1.0, 0.5, 0.33)
        tb0, tb1 = tube_end + 2.6, tube_end + 8.6
        seg(ZINC, 3, tube_end + 1.0, tb0 + 0.4, 0.29, sides=10)
        for d, name in ((tb0, "boss"), (tb1 - 1.1, "boss")):
            lathe(add(Part(GALV, 3, bevel=0.03, angle=30, name=name)), [(0.3, 0), (0.5, 0.06), (0.52, 0.16), (0.52, 0.94), (0.5, 1.04), (0.3, 1.1)], 12, frame(at(d), axis))
        tb = frame(at(tb0 + 1.0), axis)
        for side in (-0.44, 0.44):
            box(add(Part(GALV, 3, bevel=0.03, name="turnbuckle bar")), (side - 0.09, -0.17, -0.1), (side + 0.09, 0.17, tb1 - tb0 - 1.9), tb)
        seg(ZINC, 3, tb1 - 0.4, tb1 + 2.0, 0.29, sides=10)
        seg(OXIDE, 3, tb1 + 2.0, tb1 + 3.0, 0.33, 0.5)
        seg(PAINT, 3, tb1 + 3.0, length - 2.1, 0.5, sides=16)
        seg(OXIDE, 3, length - 2.1, length - 1.2, 0.5, 0.42)
        box(add(Part(OXIDE, 3, bevel=0.04, name="tang")), (-0.42, -0.26, length - 1.25), (0.42, 0.26, length + 0.5), tang)


def feet():
    for deg in YAWS:
        place = yaw(deg) @ Matrix.Translation((FOOT_RADIUS, 0, 0))
        outline = [(-5.5, -4.1), (-4.6, -5.0), (4.6, -5.0), (5.5, -4.1), (5.5, 4.1), (4.6, 5.0), (-4.6, 5.0), (-5.5, 4.1)]
        prism(add(Part(PAINT, 3, bevel=0.05, segs=2, name="foot plate")), outline, 0.0, 0.45, place)
        ear = [(-4.1, 0.45), (-1.7, 0.45), (-1.7, 1.25), (-2.45, 3.0), (-3.15, 3.0), (-4.1, 1.25)]
        for side in (-0.44, 0.44):
            m = place @ Matrix.Translation((0, side, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")
            prism(add(Part(PAINT, 2, bevel=0.03, name="clevis ear")), ear, -0.15, 0.15, m)
            for off in (-0.2, 0.2):
                weld_line(place @ Vector((-4.0, side + off, 0.52)), place @ Vector((-1.8, side + off, 0.52)), 0.08, lod=0)
        pin = place @ Matrix.Translation((-2.8, 0, 2.22)) @ frame((0, 0, 0), (0, 1, 0))
        lathe(add(Part(ZINC, 2, bevel=0.012, angle=30, name="pin")), [(0.23, -0.8), (0.23, 0.74), (0.34, 0.76), (0.34, 0.88), (0.22, 0.94), (0, 0.94)], 10, pin)
        hairpin = spline(
            [
                place @ Vector((-2.8, -0.86, 2.27)),
                place @ Vector((-2.8, -0.86, 1.8)),
                place @ Vector((-2.72, -0.86, 1.5)),
                place @ Vector((-2.55, -0.86, 1.75)),
                place @ Vector((-2.55, -0.86, 2.15)),
            ],
            3,
        )
        tube(add(Part(ZINC, 0, name="hairpin")), hairpin, 0.035, 5)
        # Two rebar stakes, hammered in and mushroomed by it.
        for side, tall in ((-3.7, 1.25), (3.7, 1.0)):
            at = place @ Vector((-4.2, side, 0.45))
            lathe(add(Part(ZINC, 1, bevel=0.012, angle=30, name="stake washer")), [(0.4, 0), (0.78, 0), (0.78, 0.08), (0.4, 0.08)], 12, frame(at))
            lathe(
                add(Part(RUST, 1, name="stake")),
                [(0.36, 0.0), (0.36, tall), (0.48, tall + 0.1), (0.56, tall + 0.22), (0.5, tall + 0.34), (0.26, tall + 0.42), (0, tall + 0.44)],
                10,
                frame(at),
            )


def fittings():
    """The flag's two brass grommets, the snap hooks through them and the ferrules that hold those on the halyard."""
    grid = np.load(os.path.join(WORK, "flag_shape.npz"))["grid"].astype(np.float64)
    rows, cols = grid.shape[:2]
    for row in (rows - 5, 4):
        p = grid[row, 3] + np.array((FLAG_X, 0, FLAG_LOW))
        along = grid[row, 5] - grid[row, 1]
        up = grid[row + 2, 3] - grid[row - 2, 3]
        normal = Vector(np.cross(along, up)).normalized()
        tube(add(Part(BRASS, 1, name="grommet")), ring_path(0.29, 14, frame(tuple(p), normal)), 0.075, 6, closed=True)
        z = float(p[2])
        rope = Vector((ROPE_X + 0.55 * math.sin(math.pi * (z - FLAG_LOW) / (FLAG_HIGH - FLAG_LOW)), 0.0, z))
        hole = Vector(p)
        axis = (hole - rope).normalized()
        side = axis.cross(Vector((0, 1, 0))).normalized()
        length = (hole - rope).length + 0.26
        oval = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            oval.append(rope + axis * (length * 0.5 + 0.5 * length * math.cos(a)) + side * (0.2 * math.sin(a)) + Vector((0, 0.03 * math.sin(a), 0)))
        tube(add(Part(BRASS, 1, name="snap hook")), oval, 0.058, 6, closed=True)
        lathe(add(Part(BRASS, 1, name="ferrule")), [(0.13, -0.3), (0.2, -0.24), (0.2, 0.24), (0.13, 0.3)], 8, frame(tuple(rope)))


def harden(part):
    bm = part.bm
    bm.normal_update()
    if part.bevel > 0:
        limit = math.radians(part.angle)
        edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > limit]
        if edges:
            bmesh.ops.bevel(bm, geom=edges, offset=part.bevel, segments=part.segs, profile=0.5, affect="EDGES", clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")


def join_parts(chosen, name, finish_attr=True, uv_map=None):
    """One mesh from parts, with finish and a per-part random stored at its corners."""
    verts, faces, face_finish, face_rand = [], [], [], []
    offset = 0
    for index, part in enumerate(chosen):
        bm = part.done
        verts.extend([tuple(v.co) for v in bm.verts])
        bm.verts.index_update()
        for f in bm.faces:
            faces.append(tuple(v.index + offset for v in f.verts))
            face_finish.append(part.finish)
            face_rand.append(part.rand)
        offset += len(bm.verts)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    colour = mesh.color_attributes.new("facts", "FLOAT_COLOR", "CORNER")
    data = np.zeros(len(mesh.loops) * 4, np.float32)
    for poly, fin, rnd in zip(mesh.polygons, face_finish, face_rand):
        for li in poly.loop_indices:
            data[li * 4 : li * 4 + 4] = (fin / 16.0, rnd, 0.0, 1.0)
    colour.data.foreach_set("color", data)
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def rope_paths():
    """The halyard: up the fly side, over the sheave, down the mast side, cleated and coiled."""
    bow = lambda z: 0.55 * math.sin(math.pi * (z - FLAG_LOW) / (FLAG_HIGH - FLAG_LOW))
    front = [(ROPE_X + (0.0 if z < FLAG_LOW else bow(z)) + (0.34 * (FLAG_LOW - z) / (FLAG_LOW - 41.2) if z < FLAG_LOW else 0), 0.0, z) for z in np.linspace(41.2, FLAG_HIGH, 28)]
    over = [(2.02 + 0.6 * math.cos(a), 0.0, 100.28 + 0.6 * math.sin(a)) for a in np.linspace(0.0, math.pi, 10)]
    run = front + [(2.62, 0.0, 98.6)] + over + [(1.42, 0.0, 98.5)]
    back = [(1.42 + 0.06 * math.sin(k * 0.8) + (1.5 * (70 - z) / 30 if z < 70 else 0), 0.04 * math.sin(k * 0.5) - 0.2 * (1 - (z - 41) / 57), z) for k, z in enumerate(np.linspace(96.0, 41.0, 18))]
    # Figure-of-eight round the horns, then the coil hanging off them.
    wrap = [
        (3.42, 0.3, 40.72),
        (3.5, 1.75, 40.42),
        (3.34, 2.72, 40.32),
        (2.86, 2.72, 40.55),
        (2.6, 2.1, 40.25),
        (2.86, 2.25, 39.62),
        (3.45, 1.4, 39.5),
        (3.55, 0.0, 39.98),
        (3.5, -1.4, 40.45),
        (3.32, -2.7, 40.4),
        (2.86, -2.72, 40.5),
        (2.6, -2.1, 40.2),
        (2.86, -2.3, 39.62),
        (3.42, -1.3, 39.5),
        (3.62, 0.1, 40.0),
        (3.58, 1.5, 40.34),
        (3.3, 2.46, 40.36),
    ]
    main = run + back + wrap
    # What's left hangs off the horn in three loops, then the end drops free of them.
    coil = [(3.3, 2.46, 40.36)]
    for k in range(31):
        t = k / 30
        a = math.pi / 2 + 2 * math.pi * 3 * t
        wide = 1.05 + 0.1 * math.sin(t * 17.0)
        tall = 4.5 - 0.5 * t + 0.16 * math.sin(t * 23.0)
        coil.append((3.34 + 0.2 * math.sin(a * 0.5 + 0.6) + 0.16 * t, 1.4 + wide * math.cos(a), 35.0 + tall * math.sin(a)))
    coil += [(3.62, 1.1, 38.2), (3.66, 0.92, 36.2), (3.7, 1.0, 34.2), (3.66, 0.9, 32.9)]
    return dict(main=spline(main, 2), coil=spline(coil, 2))


def build_rope(lod):
    sides = {0: 7, 1: 5, 2: 4}[lod]
    paths = rope_paths()
    verts, uvs, faces = [], [], []
    for name, pts in paths.items():
        if lod >= 2 and name != "main":
            continue
        if lod >= 1 and name == "tail":
            continue
        pts = pts[:: (1 if lod == 0 else 2)]
        pts = [Vector(p) for p in pts]
        along = 0.0
        ref = None
        rings = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            if i:
                along += (p - pts[i - 1]).length
            if ref is None:
                ref = t.cross(Vector((0, 0.3, 1))).normalized()
            ref = (ref - t * ref.dot(t)).normalized()
            bi = t.cross(ref)
            start = len(verts)
            for k in range(sides + 1):
                a = 2 * math.pi * k / sides
                # The rope's free end is whipped to a point rather than left an open tube.
                radius = 0.125 * (0.45 if i == len(pts) - 1 else 1.0)
                verts.append(tuple(p + (ref * math.cos(a) + bi * math.sin(a)) * radius))
                uvs.append((k / sides, along / 0.82))
            rings.append(start)
        for a, b in zip(rings, rings[1:]):
            for k in range(sides):
                faces.append((a + k, a + k + 1, b + k + 1, b + k))
    mesh = bpy.data.meshes.new(f"rope_lod{lod}")
    mesh.from_pydata(verts, [], faces)
    layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[mesh.loops[li].vertex_index]
    ob = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def pack_real_scale(mesh, res=2048, pad_px=5):
    """Lay every UV island at real size, squared up to its long side, on shelves at the highest density that fits."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    layer = bm.loops.layers.uv.active
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
        areauv = 0.5 * np.abs(
            (tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])
        ).sum()
        scale = math.sqrt(area3 / max(areauv, 1e-12))
        centre = pts.mean(0)
        inches = (pts - centre) * scale
        # The tightest of a sweep of turns.
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

    def attempt(px_per_in):
        pad = pad_px / px_per_in
        limit = res / px_per_in
        x = y = pad
        row = 0.0
        places = {}
        for w, h, n, *_ in sorted(rects, key=lambda r: (-round(r[1], 1), -r[0])):
            if x + w + pad > limit:
                x = pad
                y += row + pad
                row = 0.0
            if y + h + pad > limit:
                return None
            places[n] = (x, y)
            x += w + pad
            row = max(row, h)
        return places

    lo, hi = 2.0, 200.0
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
    print("islands", len(rects), "density px/in %.1f" % density, flush=True)


def shelf_pack(rects, margin):
    """Rectangles (w, h, key) in one square. Returns key: (u, v, scale)."""
    order = sorted(rects, key=lambda r: -r[1])

    def attempt(scale):
        x = y = margin
        row = 0.0
        out = {}
        for w, h, key in order:
            ww, hh = w * scale, h * scale
            if x + ww + margin > 1.0:
                x = margin
                y += row + margin
                row = 0.0
            if y + hh + margin > 1.0:
                return None
            out[key] = (x, y, scale)
            x += ww + margin
            row = max(row, hh)
        return out

    lo, hi = 0.0, 1.0
    best = None
    for _ in range(40):
        mid = (lo + hi) / 2
        result = attempt(mid)
        if result:
            best, lo = result, mid
        else:
            hi = mid
    return best


def grid_mesh(name, rows, uv, faces_of):
    """rows: [(points (r, c, 3), uv fn)]; appended with shared UVs."""
    verts, uvs, faces = [], [], []
    for pts, uvf, flip in rows:
        h, w = pts.shape[:2]
        start = len(verts)
        verts.extend(map(tuple, pts.reshape(-1, 3)))
        uvs.extend(uvf(j, i) for j in range(h) for i in range(w))
        for j in range(h - 1):
            for i in range(w - 1):
                a = start + j * w + i
                q = (a, a + 1, a + w + 1, a + w)
                faces.append(tuple(reversed(q)) if flip else q)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[mesh.loops[li].vertex_index]
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def world_of_pile(points, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    out = points.copy()
    px = points[..., 0] + FOOT_RADIUS + PILE_SHIFT
    out[..., 0] = c * px - s * points[..., 1]
    out[..., 1] = s * px + c * points[..., 1]
    return out


def sample(points, rows, cols):
    jj = np.round(np.linspace(0, points.shape[0] - 1, rows + 1)).astype(int)
    ii = np.round(np.linspace(0, points.shape[1] - 1, cols + 1)).astype(int)
    return points[np.ix_(jj, ii)], jj, ii


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    base()
    mast()
    stays()
    feet()
    fittings()
    for p in parts:
        harden(p)
        p.done = p.bm
        p.rand = float(rng.uniform(0, 1))
    print("parts", len(parts), "tris", sum(len(p.done.faces) for p in parts), flush=True)

    # Hardware UVs: flattened from LOD 0, then every LOD is cut from it so all share one atlas.
    hw = join_parts(parts, "hw_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    pack_real_scale(hw.data)

    # Texel density of the atlas.
    mesh = hw.data
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    area3 = uva = 0.0
    mesh.calc_loop_triangles()
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    for tri in mesh.loop_triangles:
        a, b, c = co[list(tri.vertices)]
        area3 += 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        p, q, r = uv[list(tri.loops)]
        uva += 0.5 * abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]))
    px_per_in = 2048 * math.sqrt(uva / area3)
    print("hardware: tris", len(mesh.loop_triangles), "uv fill %.2f" % uva, "px/in %.1f" % px_per_in, flush=True)

    def decimated(source, name, keep_lod, ratio):
        """A LOD: drop the small parts (their faces know their finish and random) then collapse, keeping the UVs."""
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = copy.data.name = name
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        facts = bm.loops.layers.float_color["facts"]
        drop = set()
        by_rand = {p.rand: p for p in parts}
        for f in bm.faces:
            rnd = round(f.loops[0][facts][1], 4)
            part = lookup.get(rnd)
            if part is not None and part.lod < keep_lod:
                drop.add(f)
        bmesh.ops.delete(bm, geom=list(drop), context="FACES")
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
        print(name, "tris", len(copy.data.loop_triangles), flush=True)
        return copy

    lookup = {round(p.rand, 4): p for p in parts}
    decimated(hw, "hw_lod1", 1, 0.62)
    decimated(hw, "hw_lod2", 2, 0.34)
    decimated(hw, "hw_lod3", 3, 0.1)
    for lod in (0, 1, 2):
        build_rope(lod)

    # Soft goods.
    rects = []
    piles = []
    for index, deg in enumerate(YAWS):
        data = np.load(os.path.join(WORK, f"pile_{index}_72.npz"))
        nx, ny = int(data["nx"]), int(data["ny"])
        for k in range(3):
            if f"bag{k}" not in data:
                continue
            pts = data[f"bag{k}"].astype(np.float64)
            top = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
            bottom = np.full_like(top, -1)
            bottom[0, :], bottom[-1, :], bottom[:, 0], bottom[:, -1] = top[0, :], top[-1, :], top[:, 0], top[:, -1]
            bottom[1:-1, 1:-1] = top.size + np.arange((nx - 1) * (ny - 1)).reshape(ny - 1, nx - 1)
            key = f"p{index}b{k}"
            piles.append((key, world_of_pile(pts[top], deg), world_of_pile(pts[bottom], deg), deg))
            rects.append((19.0, 11.0, key + "t"))
            rects.append((9.5, 5.5, key + "b"))
    rects.append((27.2, 1.7, "strip"))
    atlas = shelf_pack(rects, 0.008)
    size = {k: (w, h) for w, h, k in rects}
    print("soft atlas scale px/in %.1f" % (2048 * atlas["strip"][2]), flush=True)

    bag_grids = {}
    for key, top, bottom, deg in piles:
        bag_grids[key + "_top"] = top.astype(np.float32)
        bag_grids[key + "_bottom"] = bottom.astype(np.float32)

    def rect_uv(key, rows, cols):
        u0, v0, s = atlas[key]
        w, h = size[key]
        return lambda j, i: (u0 + s * w * i / cols, v0 + s * h * j / rows)

    flag_shape = np.load(os.path.join(WORK, "flag_shape.npz"))
    grid = flag_shape["grid"].astype(np.float64)
    placed = grid.copy()
    placed[..., 0] += FLAG_X
    placed[..., 2] += FLAG_LOW

    strip_cols = 7
    strip = placed[:, : strip_cols]
    strip_n = np.cross(np.gradient(strip, axis=1), np.gradient(strip, axis=0))
    strip_n /= np.linalg.norm(strip_n, axis=-1, keepdims=True) + 1e-9
    # The strip wraps the hoist, sticking out of the flag on both faces and past its edge.
    front = strip + strip_n * 0.035
    back = strip - strip_n * 0.035

    lods = {0: ((14, 9), (40, 26)), 1: ((8, 5), (20, 13)), 2: ((4, 3), (10, 7)), 3: ((2, 2), (5, 3))}
    for lod, ((bc, br), (fc, fr)) in lods.items():
        rows = []
        for key, top, bottom, deg in piles:
            t, jj, ii = sample(top, br, bc)
            b, _, _ = sample(bottom, br, bc)
            rows.append((t, rect_uv(key + "t", br, bc), False))
            rows.append((b, rect_uv(key + "b", br, bc), True))
        if lod <= 1:
            sr = {0: 12, 1: 6}[lod]
            f, _, _ = sample(front, sr, 1)
            g, _, _ = sample(back, sr, 1)
            rows.append((f, rect_uv("strip", sr, 1), False))
            rows.append((g, rect_uv("strip", sr, 1), True))
        grid_mesh(f"soft_lod{lod}", rows, None, None)
        f, _, _ = sample(placed, fr, fc)
        flagmesh = grid_mesh(f"flag_lod{lod}", [(f, lambda j, i, fr=fr, fc=fc: (i / fc, j / fr), False)], None, None)
        print(f"lod {lod}: flag tris {fr * fc * 2}", flush=True)

    np.savez_compressed(os.path.join(WORK, "soft_grids.npz"), **bag_grids, flag=placed.astype(np.float32))
    with open(os.path.join(WORK, "atlas.json"), "w") as h:
        json.dump(dict(rects={k: list(v) for k, v in atlas.items()}, sizes={k: list(v) for k, v in size.items()}, hw_px_per_in=px_per_in), h, indent=1)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "capture_flag_build.blend"))
    print("saved build", flush=True)


if __name__ == "__main__":
    main()
