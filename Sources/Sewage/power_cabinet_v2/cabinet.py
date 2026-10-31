"""Sewage's power cabinet v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python cabinet.py -- <work dir> <project root> <build|bake|export> ...

The old one is a flat box with eight bars stuck on it. This is a motor control cabinet as a waterworks would have it: a
bolted frame on a hazard-striped plinth, two hinged doors with pressed louvres (eight slats a bank, like the old bars), an
instrument panel with meters and pilot lamps, a red main switch, a lock rod with a padlock, and three conduits rising out
of the floor, clamped up its side and over into the roof. A green status lamp stands on its header.

Inches, engine axes. Local +X is out of the doors, origin on the floor at the old box's centre. The carcass fills the old
box (X +-18, Y +-38, Z 0..115) exactly, so the old collision hull still fits it.
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

from build import Part, add, box, frame, hex_bolt, lathe, prism, ring_path, spline, tube, weld_line  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST = range(9)
HAZARD, LOUVRE, DIAL, LENS_G, LENS_A, LENS_R, RED = range(9, 16)

NAME = "power_cabinet"
MODEL = "models/maps/sewage/power_cabinet_v2"
MATS = "materials/maps/sewage/power_cabinet_v2"
BLEND = os.path.join(WORK, "cabinet_build.blend")
RES = 2048

FRONT, HALF_W, TOP = 18.0, 38.0, 115.0
SKIN = 18.5  # The doors' outer face.
LEAF_LOW, LEAF_HIGH = 8.0, 107.5
GAUGES = [(-25.0, 94.2), (-12.0, 94.2)]
GAUGE_R = 4.1
LAMP_AT = (18.5, -24.0, 110.8)


def part(finish, lod=3, bevel=0.0, segs=1, angle=40.0, name="", dense=1.0):
    p = add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))
    p.dense = dense
    return p


def drop(p, *directions):
    """Faces that can never be seen take no texture space."""
    p.bm.normal_update()
    wanted = [Vector(d) for d in directions]
    bmesh.ops.delete(p.bm, geom=[f for f in p.bm.faces if any(f.normal.dot(d) > 0.9 for d in wanted)], context="FACES")
    return p


def along_y(profile, y0, y1, p):
    """A profile of (x, z), extruded from y0 to y1."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(profile, profile[1:] + profile[:1]))
    pts = profile if area < 0 else list(reversed(profile))
    prism(p, [(x, -z) for x, z in pts], y0, y1, frame((0, 0, 0), (0, 1, 0), (1, 0, 0)))


def face_frame(y, z, x=SKIN):
    """Local z out of the doors, at a point on them."""
    return frame((x, y, z), (1, 0, 0), (0, 1, 0))


def button_head(y, z, x=SKIN, size=0.42, finish=OXIDE, lod=0):
    lathe(part(finish, lod, name="bolt", dense=0.6), [(size, 0.0), (size, 0.1), (size * 0.72, 0.2), (0.0, 0.26)], 6, face_frame(y, z, x))


def carcass():
    # The plinth, standing on a foot flange with ears for its floor anchors.
    p = part(HAZARD, 3, bevel=0.06, name="plinth")
    box(p, (-17.7, -37.7, 0.45), (FRONT, HALF_W, 5.0))
    drop(p, (0, 0, 1), (0, 0, -1))
    p = part(OXIDE, 3, bevel=0.03, name="foot flange", dense=0.5)
    box(p, (-18.2, -38.2, 0.0), (18.4, 38.2, 0.45))
    drop(p, (0, 0, -1))
    for sy in (-1, 1):
        for x in (-11.0, 11.0):
            box(part(OXIDE, 2, bevel=0.04, name="foot ear"), (x - 2.4, sy * 38.2 - 2.4 if sy > 0 else sy * 38.2 - 2.1, 0.0), (x + 2.4, sy * 38.2 + 2.1 if sy > 0 else sy * 38.2 + 2.4, 0.42))
            hex_bolt((x, sy * 39.4, 0.42), (0, 0, 1), 0.95, lod=1, finish=OXIDE, stud=0.5)

    # A plain block behind everything, so door gaps and vents have something dark to look into.
    p = part(RUBBER, 3, name="carcass", dense=0.1)
    box(p, (-17.6, -37.6, 5.0), (17.3, 37.6, 114.0))
    drop(p, (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

    # Corner posts, rails and the front frame round the doors.
    for sy in (-1, 1):
        lo, hi = (35.5, HALF_W) if sy > 0 else (-HALF_W, -35.5)
        for x0, x1 in ((15.5, FRONT), (-FRONT, -15.5)):
            box(part(PAINT, 3, bevel=0.1, segs=2, name="post", dense=0.7), (x0, lo, 5.0), (x1, hi, 114.0))
        for z0, z1 in ((5.0, 8.0), (107.8, 111.0)):
            box(part(PAINT, 3, bevel=0.08, name="side rail", dense=0.55), (-15.5, lo, z0), (15.5, hi, z1))
    p = part(PAINT, 3, bevel=0.09, segs=2, name="sill")
    box(p, (15.5, -35.5, 5.0), (FRONT, 35.5, LEAF_LOW - 0.3))
    drop(p, (-1, 0, 0), (0, 0, -1))
    p = part(PAINT, 3, bevel=0.09, segs=2, name="header")
    box(p, (15.5, -35.5, LEAF_HIGH + 0.3), (FRONT, 35.5, 114.0))
    drop(p, (-1, 0, 0), (0, 0, 1))

    # Roof with a drip edge all round, and the back and side sheets.
    outline = [(-19.0, -39.0), (19.8, -39.0), (19.8, 39.0), (-19.0, 39.0)]
    prism(part(PAINT, 3, bevel=0.12, segs=2, name="roof", dense=0.32), outline, 113.8, TOP - 0.4)
    p = part(PAINT, 3, bevel=0.2, segs=2, name="roof crown", dense=0.32)
    prism(p, [(-17.5, -37.5), (18.2, -37.5), (18.2, 37.5), (-17.5, 37.5)], TOP - 0.4, TOP)
    drop(p, (0, 0, -1))
    p = part(PAINT, 3, name="back sheet", dense=0.22)
    box(p, (-18.0, -35.5, 8.0), (-17.6, 35.5, 107.8))
    drop(p, (1, 0, 0))
    for z in (36.0, 58.0, 80.0):
        box(part(PAINT, 2, bevel=0.05, name="back rib", dense=0.22), (-18.5, -35.0, z), (-18.0, 35.0, z + 2.6))
    for sy in (-1, 1):
        lo, hi = (37.6, 38.0) if sy > 0 else (-38.0, -37.6)
        p = part(PAINT, 3, name="side sheet", dense=0.62)
        box(p, (-15.5, lo, 8.0), (15.5, hi, 107.8))
        drop(p, (0, -sy, 0))
        for z in (58.0, 84.0):
            lo2, hi2 = (38.0, 38.5) if sy > 0 else (-38.5, -38.0)
            box(part(PAINT, 2, bevel=0.05, name="side rib", dense=0.62), (-14.8, lo2, z), (14.8, hi2, z + 2.6))
            for x in (-12.0, -4.0, 4.0, 12.0):
                at = Vector((x, sy * 38.5, z + 1.3))
                lathe(part(OXIDE, 0, name="bolt", dense=0.6), [(0.4, 0.0), (0.4, 0.1), (0.28, 0.2), (0.0, 0.25)], 6, frame(at, (0, sy, 0), (1, 0, 0)))
        # A side vent low down: its slats face the same way as the doors'.
        side_vent(sy)

    # Bolts along the header and the posts.
    for y in np.arange(-33.0, 33.1, 11.0):
        button_head(float(y), 111.6, FRONT, 0.46)
    for y in (-37.0, 37.0):
        for z in np.arange(12.0, 106.0, 15.5):
            button_head(y, float(z), FRONT, 0.36)
    # Lifting eyes on the roof.
    for x, y in ((-15.0, -35.0), (-15.0, 35.0), (15.0, 35.0), (15.0, -35.0)):
        lathe(part(OXIDE, 1, name="eye boss"), [(1.15, 0.0), (1.15, 0.28), (0.72, 0.5), (0.72, 0.8)], 12, frame((x, y, TOP)))
        tube(part(OXIDE, 1, name="lifting eye"), ring_path(1.15, 16, frame((x, y, TOP + 1.95), (0, 1, 0))), 0.34, 8, closed=True)


def side_vent(sy):
    y = sy * 38.0
    lo = (-10.5, min(y, y + sy * 0.3), 16.0)
    hi = (10.5, max(y, y + sy * 0.3), 40.0)
    box(part(RUBBER, 2, name="vent back", dense=0.4), lo, hi)
    for z0, z1, x0, x1 in ((39.0, 41.0, -11.5, 11.5), (15.0, 17.0, -11.5, 11.5)):
        box(part(LOUVRE, 2, bevel=0.05, name="vent frame", dense=0.6), (x0, min(y, y + sy * 0.55), z0), (x1, max(y, y + sy * 0.55), z1))
    for x0, x1 in ((-11.5, -9.8), (9.8, 11.5)):
        box(part(LOUVRE, 2, bevel=0.05, name="vent frame", dense=0.6), (x0, min(y, y + sy * 0.55), 17.0), (x1, max(y, y + sy * 0.55), 39.0))
    for k in range(5):
        z = 18.2 + k * 4.2
        m = frame((0, y, z), (1, 0, 0), (0, sy, 0))
        p = part(LOUVRE, 2, bevel=0.03, name="side slat", dense=0.6)
        prism(p, [(0.0, -0.2), (0.15, -0.2), (0.95, 2.6), (0.8, 2.6)], -9.8, 9.8, m)


def louvre_bank(y0, y1, z0, count=8, pitch=3.9):
    """A pressed vent: a raised frame, a dark mesh behind, and rain-shedding slats, the lowest edge furthest out."""
    z1 = z0 + count * pitch + 0.5
    p = part(RUBBER, 2, name="vent back", dense=0.5)
    box(p, (SKIN - 0.05, y0, z0), (SKIN + 0.04, y1, z1))
    drop(p, (-1, 0, 0))
    f = dict(bevel=0.07, segs=2, name="vent frame")
    box(part(LOUVRE, 3, **f), (SKIN - 0.05, y0 - 1.3, z1), (SKIN + 0.55, y1 + 1.3, z1 + 1.3))
    box(part(LOUVRE, 3, **f), (SKIN - 0.05, y0 - 1.3, z0 - 1.3), (SKIN + 0.55, y1 + 1.3, z0))
    box(part(LOUVRE, 3, **f), (SKIN - 0.05, y0 - 1.3, z0), (SKIN + 0.55, y0, z1))
    box(part(LOUVRE, 3, **f), (SKIN - 0.05, y1, z0), (SKIN + 0.55, y1 + 1.3, z1))
    for k in range(count):
        z = z0 + 0.35 + k * pitch
        profile = [(SKIN + 0.05, z + pitch - 0.1), (SKIN + 0.05, z + pitch - 0.55), (SKIN + 1.0, z), (SKIN + 1.0, z + 0.34)]
        along_y(profile, y0, y1, part(LOUVRE, 2, bevel=0.03, angle=30, name="slat"))
    for z in (z0 - 0.65, z1 + 0.65):
        for y in (y0 - 0.65, y1 + 0.65):
            button_head(y, z, SKIN + 0.55, 0.3)


def leaf(s):
    y0, y1 = (0.22, 36.3) if s > 0 else (-36.3, -0.22)
    # One sheet: the pressed pan in its middle is in the normal map, as a mesh of its own doubled the door's texture.
    p = part(PAINT, 3, bevel=0.14, segs=2, angle=30, name="door", dense=1.2)
    box(p, (17.3, y0, LEAF_LOW), (SKIN, y1, LEAF_HIGH))
    drop(p, (-1, 0, 0))
    # Three strap hinges on the outside edge.
    edge = s * 36.3
    for z in (23.0, 58.0, 93.0):
        lathe(part(OXIDE, 2, name="hinge pin"), [(0.0, -2.5), (0.34, -2.5), (0.55, -2.3), (0.55, 2.3), (0.34, 2.5), (0.0, 2.5)], 12, frame((SKIN + 0.2, s * 37.3, z)))
        strap = [edge - s * 6.4, s * 37.0]
        box(part(OXIDE, 2, bevel=0.03, name="hinge strap"), (SKIN, min(strap), z - 1.15), (SKIN + 0.3, max(strap), z + 1.15))
        for off in (2.0, 4.8):
            button_head(edge - s * off, z, SKIN + 0.3, 0.32)
    louvre_bank(y0 + (7.0 if s > 0 else 4.0), y1 - 4.0, 34.0)


def instruments():
    """The left door's panel: two meters, three pilot lamps, two push buttons and a selector."""
    y0, y1, z0, z1 = -31.0, -6.0, 76.0, 102.0
    p = part(PLATE, 2, bevel=0.08, segs=2, angle=30, name="panel")
    box(p, (SKIN, y0, z0), (SKIN + 0.5, y1, z1))
    drop(p, (-1, 0, 0))
    for y in (y0 + 1.0, y1 - 1.0):
        for z in (z0 + 1.0, z1 - 1.0):
            button_head(y, z, SKIN + 0.5, 0.3, ZINC)
    x = SKIN + 0.5
    for y, z in GAUGES:
        m = face_frame(y, z, x)
        lathe(part(OXIDE, 2, bevel=0.0, name="meter bezel", dense=1.5), [(GAUGE_R + 0.75, 0.0), (GAUGE_R + 0.75, 0.55), (GAUGE_R + 0.5, 0.86), (GAUGE_R + 0.04, 0.86), (GAUGE_R + 0.04, 0.3)], 28, m)
        p = part(DIAL, 2, name="meter dial", dense=2.2)
        lathe(p, [(0.0, 0.32), (GAUGE_R + 0.06, 0.32)][::-1], 28, m)
        drop(p, (-1, 0, 0))
        lathe(part(RUBBER, 1, name="meter boss", dense=1.5), [(0.34, 0.3), (0.34, 0.5), (0.0, 0.58)], 8, m)
        for a in (45, 135, 225, 315):
            r = math.radians(a)
            button_head(y + (GAUGE_R + 1.35) * math.cos(r), z + (GAUGE_R + 1.35) * math.sin(r), x, 0.22, ZINC)
    # Pilot lamps.
    for y, finish in ((-25.5, LENS_G), (-18.5, LENS_A), (-11.5, LENS_R)):
        m = face_frame(y, 84.0, x)
        lathe(part(ZINC, 1, name="lamp ring", dense=1.5), [(1.15, 0.0), (1.15, 0.22), (0.92, 0.32), (0.86, 0.3)], 16, m)
        lathe(part(finish, 1, name="lamp lens", dense=1.5), [(0.88, 0.28), (0.8, 0.52), (0.5, 0.74), (0.0, 0.82)], 16, m)
    # Push buttons and a selector switch.
    for y, finish in ((-26.0, LENS_G), (-19.0, RED)):
        m = face_frame(y, 79.2, x)
        lathe(part(OXIDE, 1, name="button collar"), [(1.0, 0.0), (1.0, 0.3), (0.76, 0.34)], 14, m)
        lathe(part(RED if finish == RED else GALV, 1, name="button"), [(0.72, 0.3), (0.72, 0.62), (0.56, 0.74), (0.0, 0.78)], 14, m)
    m = face_frame(-11.0, 79.2, x)
    lathe(part(OXIDE, 1, name="selector collar"), [(1.05, 0.0), (1.05, 0.26), (0.84, 0.3)], 14, m)
    lathe(part(RUBBER, 1, name="selector"), [(0.82, 0.28), (0.82, 0.5), (0.0, 0.5)], 14, m)
    box(part(RUBBER, 1, bevel=0.04, name="selector key"), (x + 0.5, -11.2, 78.3), (x + 1.05, -10.8, 80.1))


def main_switch():
    """The right door's main switch: a backing plate with a heavy red lever, thrown on."""
    y, z = 19.0, 89.0
    x = SKIN
    m = face_frame(y, z, x)
    p = part(PLATE, 2, bevel=0.05, name="switch plate")
    box(p, (x, y - 8.2, z - 10.5), (x + 0.3, y + 8.2, z + 10.5))
    drop(p, (-1, 0, 0))
    for dy in (-7.2, 7.2):
        for dz in (-9.5, 9.5):
            button_head(y + dy, z + dz, x + 0.3, 0.32, ZINC)
    x += 0.3
    m = face_frame(y, z, x)
    lathe(part(OXIDE, 3, bevel=0.03, angle=30, name="switch body"), [(5.0, 0.0), (5.0, 0.9), (4.5, 1.25), (2.6, 1.45), (2.2, 2.2), (1.7, 2.3)], 28, m)
    lathe(part(ZINC, 2, name="switch boss"), [(1.75, 2.2), (1.75, 2.8), (1.2, 3.0), (0.0, 3.0)], 14, m)
    # The lever, rising to the right, thrown to ON.
    a = math.radians(38)
    d = Vector((0.0, math.cos(a), math.sin(a)))
    start = Vector((x + 2.75, y, z))
    path = [start - d * 1.2, start, start + d * 3.5, start + d * 7.4 + Vector((0.5, 0, 0)), start + d * 10.6 + Vector((1.15, 0, 0))]
    tube(part(RED, 3, name="switch lever", dense=1.3), spline(path, 4), [0.72, 0.82, 0.68, 0.72, 0.84, 0.92, 0.94, 0.96, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.7][:len(spline(path, 4))], 12, flatten=0.82)


def lock_rod():
    """An exposed lock rod up the right door, with a T handle and a padlocked hasp."""
    y = 4.6
    x = SKIN
    r0, r1 = 12.0, 104.0
    lathe(part(ZINC, 3, name="lock rod"), [(0.0, r0 - 0.4), (0.36, r0 - 0.28), (0.36, r1 + 0.28), (0.0, r1 + 0.4)], 10, frame((x + 0.82, y, 0)))
    for z in (r0 + 1.2, 33.0, 58.0, 84.0, r1 - 1.2):
        strap = [(x, z - 0.8), (x + 1.28, z - 0.8), (x + 1.28, z + 0.8), (x, z + 0.8)]
        along_y(strap, y - 0.7, y - 0.5, part(OXIDE, 2, name="rod guide"))
        along_y(strap, y + 0.5, y + 0.7, part(OXIDE, 2, name="rod guide"))
        along_y([(x + 1.25, z - 0.8), (x + 1.45, z - 0.8), (x + 1.45, z + 0.8), (x + 1.25, z + 0.8)], y - 0.7, y + 0.7, part(OXIDE, 2, name="rod guide"))
        box(part(OXIDE, 1, bevel=0.03, name="guide foot"), (x, y - 1.6, z - 0.9), (x + 0.16, y + 1.6, z + 0.9))
    # Keeps top and bottom, where the rod shoots into the frame.
    for z, z2 in ((r0 - 1.5, r0 + 0.2), (r1 - 0.2, r1 + 1.5)):
        box(part(OXIDE, 2, bevel=0.06, name="rod keep"), (FRONT, y - 1.1, z), (x + 1.45, y + 1.1, z2))
    # The T handle, on a boss, and the hasp beneath it.
    h = 75.5
    lathe(part(OXIDE, 2, name="handle boss"), [(1.2, 0.0), (1.2, 0.36), (0.72, 0.62), (0.5, 1.5), (0.34, 1.7)], 14, face_frame(y, h, x))
    lathe(part(RED, 2, bevel=0.03, angle=30, name="t handle", dense=1.3), [(0.0, -3.5), (0.6, -3.36), (0.68, -3.0), (0.54, 3.0), (0.66, 3.36), (0.0, 3.5)], 10, frame((x + 1.9, y, h), (0, 1, 0)))
    z = 69.8
    box(part(OXIDE, 2, bevel=0.04, name="hasp"), (x, y - 1.2, z - 1.5), (x + 0.26, y + 5.0, z + 1.5))
    lathe(part(OXIDE, 1, name="staple"), [(0.0, 0.0), (0.46, 0.0), (0.46, 0.6), (0.0, 0.6)], 8, frame((x + 0.26, y + 3.9, z), (1, 0, 0)))
    # The padlock, hanging from the staple by its shackle.
    sx = x + 1.0
    arch = spline([(sx, y + 3.9 - 0.82, z - 1.4), (sx, y + 3.9 - 0.82, z + 0.1), (sx, y + 3.9, z + 0.9), (sx, y + 3.9 + 0.82, z + 0.1), (sx, y + 3.9 + 0.82, z - 1.4)], 4)
    tube(part(ZINC, 1, name="shackle", dense=1.4), arch, 0.2, 8)
    outline = [(-0.42, -1.25), (0.42, -1.25), (0.42, 1.25), (-0.42, 1.25)]
    prism(part(BRASS, 2, bevel=0.1, segs=2, angle=30, name="padlock", dense=1.4), outline, z - 3.5, z - 1.4, frame((0, 0, 0)) @ Matrix.Translation((sx, y + 3.9, 0)))


def plates():
    """A yellow danger plate, and the supply plate low on the right door."""
    p = part(PLATE, 2, bevel=0.04, name="danger plate", dense=1.6)
    box(p, (SKIN, -31.0, 19.0), (SKIN + 0.12, -6.0, 31.0))
    drop(p, (-1, 0, 0))
    for y in (-30.2, -6.8):
        for z in (19.8, 30.2):
            button_head(y, z, SKIN + 0.12, 0.22, ZINC)
    p = part(PLATE, 2, bevel=0.04, name="supply plate", dense=1.6)
    box(p, (SKIN, 10.0, 18.0), (SKIN + 0.12, 31.0, 28.5))
    drop(p, (-1, 0, 0))
    for y in (10.8, 30.2):
        for z in (18.8, 27.7):
            button_head(y, z, SKIN + 0.12, 0.22, ZINC)


def conduits():
    """Three rigid conduits up from the floor, clamped to a channel on the side, over into glands in the roof."""
    for k, x in enumerate((-10.0, 0.0, 10.0)):
        y = -41.6
        turn = TOP + 3.6 + k * 0.0
        path = spline([(x, y, 0.0), (x, y, 60.0), (x, y, turn - 3.0), (x, y + 0.6, turn - 0.2), (x, y + 2.8, turn + 2.0), (x, y + 6.8, turn + 2.2), (x, y + 8.6, turn + 0.6), (x, y + 9.2, TOP + 0.6)], 5)
        tube(part(GALV, 3, name="conduit", dense=0.55), path, 1.18, 12)
        lathe(part(OXIDE, 2, bevel=0.03, angle=30, name="floor flange"), [(2.3, 0.0), (2.3, 0.3), (1.45, 0.5), (1.45, 2.2), (1.25, 2.4)], 14, frame((x, y, 0.0)))
        for z in (34.0 + k * 3.0, 74.0 - k * 2.0):
            lathe(part(GALV, 2, bevel=0.03, angle=30, name="coupling"), [(1.18, -1.15), (1.48, -1.05), (1.48, 1.05), (1.18, 1.15)], 12, frame((x, y, z)))
        lathe(part(OXIDE, 2, name="gland"), [(2.2, 0.0), (2.2, 0.24), (1.75, 0.3), (1.75, 1.0), (1.3, 1.25)], 6, frame((x, y + 9.2, TOP)))
    for z in (26.0, 62.0, 98.0):
        box(part(GALV, 3, bevel=0.05, name="strut", dense=0.8), (-14.5, -40.0, z - 0.8), (14.5, -38.0, z + 0.8))
        for x in (-13.2, 13.2):
            lathe(part(OXIDE, 0, name="bolt", dense=0.6), [(0.42, 0.0), (0.42, 0.1), (0.3, 0.2), (0.0, 0.25)], 6, frame((x, -40.0, z), (0, -1, 0), (1, 0, 0)))
        for x in (-10.0, 0.0, 10.0):
            arc = [Vector((x + 1.36 * math.cos(a), -41.6 + 1.36 * math.sin(a), z)) for a in np.linspace(0.0, -math.pi, 9)]
            arc = [Vector((x + 1.9, -40.0, z))] + arc + [Vector((x - 1.9, -40.0, z))]
            tube(part(ZINC, 1, name="pipe strap", dense=0.8), arc, 0.2, 5, flatten=2.2)


def status_lamp():
    """A caged well-glass lamp on a bracket from the header."""
    x, y, z = LAMP_AT
    box(part(OXIDE, 3, bevel=0.05, name="lamp bracket"), (FRONT, y - 1.6, z - 1.5), (FRONT + 0.3, y + 1.6, z + 1.5))
    lathe(part(OXIDE, 3, name="lamp arm"), [(0.0, 0.0), (0.72, 0.0), (0.72, 3.5), (0.0, 3.5)], 10, frame((FRONT + 0.2, y, z), (1, 0, 0)))
    at = (FRONT + 4.2, y, z)
    lathe(part(OXIDE, 3, bevel=0.03, angle=30, name="lamp body", dense=1.3), [(1.9, -0.35), (2.2, -0.35), (2.55, 0.0), (2.5, 0.9), (1.1, 1.5), (0.0, 1.5)], 16, frame(at))
    lathe(part(LENS_G, 3, name="well glass", dense=1.3), [(1.9, -0.3), (2.05, -1.5), (1.95, -3.3), (1.3, -4.5), (0.0, -4.9)][::-1], 16, frame(at))
    lathe(part(ZINC, 2, name="lamp guard ring", dense=1.1), [(2.42, -3.05), (2.5, -2.92), (2.42, -2.8), (2.34, -2.92)], 14, frame(at))
    for a in np.linspace(0.0, 2 * math.pi, 4, endpoint=False):
        c, s = math.cos(a), math.sin(a)
        wire = [Vector(at) + Vector((c * r, s * r, h)) for r, h in ((2.4, -0.2), (2.48, -1.6), (2.42, -2.9), (2.02, -4.3), (0.9, -5.4), (0.0, -5.6))]
        tube(part(ZINC, 2, name="lamp guard", dense=1.1), spline(wire, 2), 0.09, 5)


def geometry():
    carcass()
    leaf(-1)
    leaf(1)
    instruments()
    main_switch()
    lock_rod()
    plates()
    conduits()
    status_lamp()
    # Welds where the frame's rails meet the posts, on what shows.
    for z in (LEAF_LOW - 0.3, LEAF_HIGH + 0.3):
        for y in (-35.5, 35.5):
            weld_line((FRONT + 0.02, y, z - 1.2), (FRONT + 0.02, y, z + 1.2), 0.1, lod=0)


def window_max(a, k):
    """The largest of each k neighbours, by prefix and suffix maxima over blocks of k. Blender has no scipy."""
    n = len(a)
    if k == 1:
        return a.copy()
    blocks = np.concatenate((a, np.zeros(-n % k, a.dtype))).reshape(-1, k)
    prefix = np.maximum.accumulate(blocks, axis=1).ravel()[:n]
    suffix = np.maximum.accumulate(blocks[:, ::-1], axis=1)[:, ::-1].ravel()[:n]
    return np.maximum(suffix[: n - k + 1], prefix[k - 1 :])


def pack_weighted(mesh, weights, names, res=RES, pad_px=4):
    """The toolkit's real-scale layout with two changes: each island's scale is weighted by its parts' density, and it goes on
    a skyline rather than shelves, which fills far more of the sheet."""
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

    def measure(faces):
        dense = max(weights[round(f.loops[0][facts][1], 4)] for f in faces)
        area3 = sum(f.calc_area() for f in faces)
        pts = np.array([tuple(l[layer].uv) for f in faces for l in f.loops])
        tris = np.array([[tuple(l[layer].uv) for l in f.loops[:3]] for f in faces])
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
        scale = math.sqrt(area3 / max(areauv, 1e-12)) * dense
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
        return w, h, centre, scale, rot, q.min(0), area3 * dense * dense

    def pairs(faces):
        """Thin L-shaped bevel strips waste nearly all of their rectangle, so they go on the sheet two triangles at a time."""
        left = {f.index for f in faces}
        groups = []
        for f in faces:
            if f.index not in left:
                continue
            left.discard(f.index)
            mate = None
            for l in sorted(f.loops, key=lambda l: -l.edge.calc_length()):
                mate = next((g for g in l.edge.link_faces if g.index in left), None)
                if mate:
                    break
            if mate:
                left.discard(mate.index)
            groups.append([f, mate] if mate else [f])
        return groups

    kept = []
    for faces in islands:
        m = measure(faces)
        if len(faces) > 2 and m[0] * m[1] > 2.2 * m[6]:
            kept.extend(pairs(faces))
        else:
            kept.append(faces)
    islands = kept
    rects = []
    for n, faces in enumerate(islands):
        w, h, centre, scale, rot, low, _ = measure(faces)
        rects.append((w, h, n, centre, scale, rot, low))
    order = sorted(rects, key=lambda r: (-round(r[1], 1), -r[0]))
    for w, h, n, *_ in sorted(rects, key=lambda r: -r[0] * r[1])[:14]:
        f = islands[n][0]
        print("  island %.0f x %.0f, %d faces, part %s" % (w, h, len(islands[n]), names.get(round(f.loops[0][facts][1], 4))), flush=True)
    print("  total weighted area", round(sum(r[0] * r[1] for r in rects)), flush=True)

    def attempt(px):
        heights = np.zeros(res, np.int32)
        places = {}
        for w, h, n, *_ in order:
            iw, ih = int(math.ceil(w * px)) + pad_px, int(math.ceil(h * px)) + pad_px
            if iw >= res:
                return None
            mx = window_max(heights, iw)
            i = int(np.argmin(mx))
            top = int(mx[i]) + ih
            if top >= res:
                return None
            heights[i : i + iw] = top
            places[n] = ((i + pad_px / 2) / px, (top - ih + pad_px / 2) / px)
        return places

    lo, hi = 2.0, 120.0
    places = None
    for _ in range(18):
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
    fill = sum(r[0] * r[1] for r in rects) * density * density / res / res
    print("islands", len(rects), "px per weighted inch %.1f" % density, "fill %.2f" % fill, flush=True)
    return density


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    order = kit.rng.permutation(len(kit.parts))
    for p, k in zip(kit.parts, order):
        kit.harden(p)
        p.done = p.bm
        # Faces are traced back to their parts by this, rounded to four places, so no two may share one.
        p.rand = (float(k) + 0.5) / len(kit.parts)
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "cabinet_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    lookup = {round(p.rand, 4): p for p in kit.parts}
    weights = {k: getattr(p, "dense", 1.0) for k, p in lookup.items()}
    density = pack_weighted(hw.data, weights, {k: p.name for k, p in lookup.items()})

    # Each texel's density goes in the facts' third channel, since the normal map's strength depends on it.
    colour = hw.data.color_attributes["facts"]
    data = np.zeros(len(hw.data.loops) * 4, np.float32)
    colour.data.foreach_get("color", data)
    data = data.reshape(-1, 4)
    data[:, 2] = [weights[round(float(r), 4)] / 4.0 for r in data[:, 1]]
    colour.data.foreach_set("color", data.ravel())

    def lod(name, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = name
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
        print(name, "tris", len(copy.data.loop_triangles), flush=True)

    hw.data.calc_loop_triangles()
    print("cabinet_lod0 tris", len(hw.data.loop_triangles), flush=True)
    lod("cabinet_lod1", 1, 0.6)
    lod("cabinet_lod2", 2, 0.4)
    lod("cabinet_lod3", 3, 0.3)
    with open(os.path.join(WORK, "cabinet.json"), "w") as h:
        json.dump(dict(density=density, gauges=GAUGES, gauge_r=GAUGE_R, skin=SKIN, lamp=LAMP_AT), h)
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
    hw = bpy.data.objects["cabinet_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 8.0
    with open(os.path.join(WORK, "baked_uv_hash.txt"), "w") as h:
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
            scale = 1 / 400.0 if kind == "pos" else 0.5
            mapped.inputs[1].default_value = (scale, scale, scale)
            mapped.inputs[2].default_value = (0.5, 0.5, 0.5)
            nt.links.new(geo.outputs["Position" if kind == "pos" else "Normal"], mapped.inputs[0])
            nt.links.new(mapped.outputs[0], emit.inputs[0])

        return setup

    def bake_one(size, kind, setup, samples, out):
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_cabinet_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_cabinet_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_cabinet_facts")
    bake_one(1024, "AO", None, 24, "bake_cabinet_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["cabinet_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2, 3):
        ob = bpy.data.objects[f"cabinet_lod{lod}"]
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
                for table, store, prefix, vec in zip(tables, lines, ("v ", "vt ", "vn "), (p[i], t[i], n[i])):
                    key = tuple(np.round(vec, 5))
                    got = table.get(key)
                    if got is None:
                        got = len(table) + 1
                        table[key] = got
                        store.append(prefix + " ".join(f"{x:.5f}" for x in key) + "\n")
                    idx.append(got)
                tri.append("%d/%d/%d" % tuple(idx))
            faces.append("f " + " ".join(tri) + "\n")
        with open(os.path.join(out, f"{NAME}_lod{lod}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/Sewage/power_cabinet_v2/cabinet.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {NAME}\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/{NAME}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 80.0, 180.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Sewage/power_cabinet_v2/cabinet.py
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
							{{ from = "{NAME}.vmat" to = "{MATS}/{NAME}.vmat" }}
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
    with open(os.path.join(out, f"{NAME}.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Sewage/power_cabinet_v2/cabinet.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1
	F_SELF_ILLUM 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/{NAME}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/{NAME}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/{NAME}_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/{NAME}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/{NAME}_rough.png"

	//---- Self Illum ----
	TextureSelfIllumMask "{MATS}/{NAME}_glow.png"
	g_flSelfIllumBrightness "2.600"
	g_flSelfIllumAlbedoFactor "1.000"
	g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"
}}
"""
    with open(os.path.join(mats, f"{NAME}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("cabinet stages done", flush=True)
