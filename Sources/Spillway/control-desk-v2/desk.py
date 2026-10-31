"""Spillway control desk v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python desk.py -- <work dir> <project root> <build|bake|export> ...

The old desk is one flat box with a flat blue screen floating above it. This is a hydro plant's operator desk: steel pedestals
with a kneehole, a laminate top with a rubber edge, a sloped hardwired mimic board with pistol-grip switches and lamps, a row of
round meters and a chart recorder, three later screens on a beam, and what an operator leaves out. Same 120 x 70 footprint,
with the worktop's top at 31.5 where the old box's was 34. The operator's side is +X. Inches, engine axes.
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
sys.path.insert(0, os.path.join(ROOT, "Sources", "Spillway", "control-desk-v2"))
import build as kit  # noqa: E402
import layout as L  # noqa: E402

from build import Part, add, box, frame, lathe, prism, spline, tube  # noqa: E402

NAVY, GREY, CHROME, BLACK, RUBBER, LAM, RED, YELLOW, PAPER, ENAMEL, KEY, PLATE, BOARD = range(13)
MODEL = "models/props/spillway/control_desk_v2"
MATS = "materials/spillway/control_desk_v2"
NAME = "control_desk"
BLEND = os.path.join(WORK, "desk_build.blend")
ATLAS = 4096
THRESHOLDS = (0.0, 30.0, 80.0)

# Lamps and screens: one self-lit mesh with its own UVs. Panel: two quads on their own atlas.
glow = {"v": [], "f": [], "uv": [], "lod": []}
panel = {"v": [], "f": [], "uv": []}


def S(u, v, h=0.0):
    """A point on the slope panel, h above it."""
    x = L.SLOPE_LOW[0] + L.SLOPE_DIR[0] * v + L.SLOPE_NORMAL[0] * h
    z = L.SLOPE_LOW[1] + L.SLOPE_DIR[1] * v + L.SLOPE_NORMAL[1] * h
    return Vector((x, u - L.PANEL_W / 2, z))


def U(u, v, h=0.0):
    """A point on the upright panel, h in front of it."""
    return Vector((L.UPRIGHT_X + h, u - L.PANEL_W / 2, L.UPRIGHT_Z + v))


SLOPE_N = (L.SLOPE_NORMAL[0], 0.0, L.SLOPE_NORMAL[1])


def on_slope(u, v, h=0.0, turn=0.0):
    return frame(S(u, v, h), SLOPE_N, (0, 1, 0)) @ Matrix.Rotation(math.radians(turn), 4, "Z")


def on_upright(u, v, h=0.0):
    return frame(U(u, v, h), (1, 0, 0), (0, 1, 0))


def hexa(part, c):
    """Eight corners: one ring, then the ring above it. Normals are put right after the build."""
    bm = part.bm
    v = [bm.verts.new(Vector(p)) for p in c]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])


def slope_box(part, u0, u1, v0, v1, h0, h1):
    hexa(part, [S(u0, v0, h0), S(u1, v0, h0), S(u1, v1, h0), S(u0, v1, h0), S(u0, v0, h1), S(u1, v0, h1), S(u1, v1, h1), S(u0, v1, h1)])


def upright_box(part, u0, u1, v0, v1, h0, h1):
    hexa(part, [U(u0, v0, h0), U(u1, v0, h0), U(u1, v1, h0), U(u0, v1, h0), U(u0, v0, h1), U(u1, v0, h1), U(u1, v1, h1), U(u0, v1, h1)])


def ring_solid(part, loop, sides, m=Matrix.Identity(4)):
    """A closed (radius, z) loop swept about local Z: an open ring with a real hole in it."""
    bm = part.bm
    rings = [
        [bm.verts.new(m @ Vector((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z))) for k in range(sides)]
        for r, z in loop
    ]
    for j in range(len(rings)):
        a, b = rings[j], rings[(j + 1) % len(rings)]
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))


def xz_prism(part, outline, y0, y1):
    """An outline in (x, z), extruded along Y."""
    bm = part.bm
    a = [bm.verts.new((x, y0, z)) for x, z in outline]
    b = [bm.verts.new((x, y1, z)) for x, z in outline]
    n = len(outline)
    for k in range(n):
        bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(list(b))


def screw(at, axis, size=0.26, lod=0, finish=CHROME):
    lathe(add(Part(finish, lod, name="screw")), [(size, 0), (size, size * 0.3), (size * 0.6, size * 0.5), (0, size * 0.52)], 6, frame(at, axis))


def louvre(lo, hi, axis_out, count, depth=0.34, finish=NAVY):
    """Pressed slats in a frame, on a plane facing along +-X (axis_out = +1 or -1, x = lo[0]) over a black back."""
    x, y0, z0 = lo
    y1, z1 = hi
    s = axis_out
    add_box = lambda f, a, b, lod=2, bevel=0.04: box(add(Part(f, lod, bevel=bevel, name="vent")), (min(a[0], b[0]), a[1], a[2]), (max(a[0], b[0]), b[1], b[2]))
    add_box(BLACK, (x, y0, z0), (x + s * 0.08, y1, z1), 3, 0.0)
    w = 0.5
    add_box(finish, (x, y0 - w, z0 - w), (x + s * depth, y1 + w, z0))
    add_box(finish, (x, y0 - w, z1), (x + s * depth, y1 + w, z1 + w))
    add_box(finish, (x, y0 - w, z0), (x + s * depth, y0, z1))
    add_box(finish, (x, y1, z0), (x + s * depth, y1 + w, z1))
    pitch = (z1 - z0) / count
    for k in range(count):
        z = z0 + pitch * k
        low = x + s * 0.05
        high = x + s * depth * 0.95
        slat = add(Part(finish, 1, name="slat"))
        hexa(slat, [(low, y0, z), (low, y1, z), (high, y1, z + pitch * 0.2), (high, y0, z + pitch * 0.2),
                    (low, y0, z + pitch * 0.95), (low, y1, z + pitch * 0.95), (high, y1, z + pitch * 0.72), (high, y0, z + pitch * 0.72)])


def side_vents(y_face, s):
    """Pressed bumps on a pedestal's outer side."""
    for k in range(6):
        z = 15.0 + k * 1.75
        for x0, x1 in ((-24.0, -6.0), (4.0, 22.0)):
            bump = add(Part(NAVY, 1, bevel=0.05, name="pressed vent"))
            y = y_face + s * 0.22
            hexa(bump, [(x0 - 0.4, y_face, z), (x1 + 0.4, y_face, z), (x1 + 0.4, y_face, z + 1.05), (x0 - 0.4, y_face, z + 1.05),
                        (x0, y, z + 0.1), (x1, y, z + 0.1), (x1, y, z + 0.55), (x0, y, z + 0.55)])


def pull(y0, y1, z, x=31.35):
    """A drawer's bar pull on two stand-offs."""
    tube(add(Part(CHROME, 1, name="pull")), [(x + 1.15, y0, z), (x + 1.15, y1, z)], 0.28, 10)
    for y in (y0 + 0.7, y1 - 0.7):
        tube(add(Part(CHROME, 1, name="pull post")), [(x, y, z), (x + 1.15, y, z)], 0.22, 8)
        lathe(add(Part(CHROME, 0, name="pull base")), [(0.42, 0), (0.42, 0.06), (0.26, 0.12)], 10, frame((x, y, z), (1, 0, 0)))


def card_holder(y, z, x=31.35):
    """A chrome frame holding a label card."""
    w, h = 2.6, 0.85
    box(add(Part(PAPER, 1, name="card")), (x, y - w, z - h), (x + 0.05, y + w, z + h))
    f = add(Part(CHROME, 1, bevel=0.015, name="card frame"))
    box(f, (x, y - w - 0.14, z - h - 0.14), (x + 0.12, y + w + 0.14, z - h))
    box(f, (x, y - w - 0.14, z + h), (x + 0.12, y + w + 0.14, z + h + 0.14))
    box(f, (x, y - w - 0.14, z - h), (x + 0.12, y - w, z + h))
    box(f, (x, y + w, z - h), (x + 0.12, y + w + 0.14, z + h))


def pedestals():
    # The body, the kick plate, the modesty panel and the top.
    for y0, y1 in ((-58.0, -24.0), (24.0, 58.0)):
        box(add(Part(NAVY, 3, bevel=0.16, name="pedestal")), (-33.0, y0, 3.0), (31.0, y1, 29.5))
        box(add(Part(RUBBER, 3, bevel=0.06, name="kick")), (-32.0, y0 + 0.6, 0.0), (29.6, y1 - 0.6, 3.0))
    box(add(Part(NAVY, 3, bevel=0.1, name="modesty")), (-33.0, -24.0, 3.0), (-6.0, 24.0, 29.5))
    box(add(Part(LAM, 3, bevel=0.03, angle=60, name="worktop")), (-6.0, -58.8, 29.5), (33.6, 58.8, 31.5))
    edge = add(Part(RUBBER, 3, bevel=0.32, segs=2, name="rubber edge"))
    box(edge, (33.6, -60.0, 29.3), (35.0, 60.0, 31.7))
    for s in (-1, 1):
        side = add(Part(RUBBER, 3, bevel=0.32, segs=2, name="rubber edge"))
        a, b = sorted((s * 58.8, s * 60.0))
        box(side, (-6.0, a, 29.3), (33.6, b, 31.7))

    # Left as the operator sits: one door with a vent and a quarter-turn latch.
    box(add(Part(NAVY, 3, bevel=0.14, name="door")), (31.0, -56.0, 4.8), (31.35, -26.0, 27.8))
    louvre((31.35, -53.0, 7.2), (-29.0, 15.0), 1, 7)
    latch = frame((31.35, -28.6, 21.0), (1, 0, 0))
    lathe(add(Part(CHROME, 1, bevel=0.03, name="latch")), [(0.85, 0), (0.85, 0.12), (0.62, 0.2), (0.5, 0.48), (0.38, 0.62)], 14, latch)
    box(add(Part(CHROME, 1, bevel=0.05, name="latch bar")), (31.9, -28.85, 19.7), (32.25, -28.35, 22.3))
    for z in (8.0, 24.5):
        tube(add(Part(CHROME, 1, name="hinge")), [(31.5, -56.15, z - 1.3), (31.5, -56.15, z + 1.3)], 0.2, 8)
    box(add(Part(PLATE, 1, bevel=0.02, angle=50, name="id plate")), (31.35, -49.0, 20.0), (31.42, -35.0, 24.0))
    for y in (-48.4, -35.6):
        for z in (20.6, 23.4):
            screw((31.42, y, z), (1, 0, 0), 0.14)

    # Right: two drawers, each with a pull and a label.
    for z0, z1 in ((4.8, 15.8), (16.6, 27.8)):
        box(add(Part(NAVY, 3, bevel=0.14, name="drawer")), (31.0, 26.0, z0), (31.35, 56.0, z1))
        mid = (z0 + z1) / 2
        pull(36.0, 46.0, mid - 1.6)
        card_holder(41.0, mid + 2.2)

    # The kneehole's foot rail, on two brackets into the pedestals.
    tube(add(Part(CHROME, 2, name="foot rail")), [(8.0, -24.0, 5.5), (8.0, 24.0, 5.5)], 0.62, 12)
    for s in (-1, 1):
        lathe(add(Part(CHROME, 1, name="rail flange")), [(1.05, 0), (1.05, 0.14), (0.7, 0.26)], 12, frame((8.0, s * 24.0, 5.5), (0, -s, 0)))
    box(add(Part(BLACK, 1, bevel=0.05, name="gland")), (-6.0, 8.0, 21.0), (-5.75, 14.0, 26.0))

    # The back, which nobody sees but the sides do.
    box(add(Part(NAVY, 3, bevel=0.1, name="rear panel")), (-35.0, -58.0, 3.0), (-33.0, 58.0, 57.5))
    for s in (-1, 1):
        side_vents(s * 58.0, s)
        for x, z in ((-31.0, 5.0), (-31.0, 27.5), (29.0, 5.0), (29.0, 27.5)):
            screw((x, s * 58.0, z), (0, s, 0), 0.24)


def instrument_board():
    # Side cheeks carry the slope and the meters.
    outline = [(-35.0, 29.5), (-1.0, 29.5), (-1.0, 33.6), (-18.0, 48.3), (-18.0, 57.5), (-35.0, 57.5)]
    for y0, y1 in ((-58.0, -56.0), (56.0, 58.0)):
        xz_prism(add(Part(NAVY, 3, bevel=0.14, name="cheek")), outline, y0, y1)
    # Under the slope and behind the meters, so nothing shows through from a low angle.
    box(add(Part(BLACK, 3, name="inside")), (-33.0, -56.0, 29.5), (-20.0, 56.0, 33.0))
    box(add(Part(NAVY, 3, bevel=0.06, name="low lip")), (-6.0, -56.0, 31.5), (-1.0, 56.0, 33.2))

    # Frame and bay divides on the slope.
    w, l = L.PANEL_W, L.SLOPE_L
    slope_box(add(Part(GREY, 3, bevel=0.06, name="slope rail")), 0, w, -0.5, 0.55, -0.2, 0.34)
    slope_box(add(Part(GREY, 3, bevel=0.06, name="slope rail")), 0, w, l - 0.55, l + 0.5, -0.2, 0.34)
    for k in range(1, L.BAYS):
        u = k * L.BAY_W
        slope_box(add(Part(GREY, 2, bevel=0.05, name="mullion")), u - 0.36, u + 0.36, 0.5, l - 0.5, -0.1, 0.26)
    for k in range(L.BAYS + 1):
        u = min(max(k * L.BAY_W, 0.8), w - 0.8)
        for v in (0.0, l):
            screw(S(u, v, 0.34), SLOPE_N, 0.2)
        if 0 < k < L.BAYS:
            for v in (5.5, 11.0, 16.5):
                screw(S(u, v, 0.26), SLOPE_N, 0.16)

    # The bays' switchgear.
    angle = 0
    for i in range(L.BAYS):
        left = L.bay_left(i)
        if i != 2:
            for u, v in L.SWITCH_AT:
                pistol(left + u, v, L.SWITCH_ANGLES[angle % len(L.SWITCH_ANGLES)])
                angle += 1
        for u, v, kind in L.lamp_places(i):
            lamp(u, v, kind)
        for u, v, k in L.button_places(i):
            button(u, v, (GREY, BLACK, RED, BLACK, GREY, BLACK)[k])
    # The station bay's emergency stop in its yellow guard, and its small touch screen's frame.
    eu, ev = L.bay_left(2) + L.ESTOP[0], L.ESTOP[1]
    m = on_slope(eu, ev)
    ring_solid(add(Part(YELLOW, 2, name="stop guard")), [(1.25, 0.0), (1.85, 0.0), (1.85, 0.72), (1.6, 0.86), (1.42, 0.86)], 20, m)
    lathe(add(Part(BLACK, 2, name="stop collar")), [(1.25, 0.0), (1.25, 0.3), (0.84, 0.36)], 16, m)
    lathe(add(Part(RED, 2, bevel=0.0, name="stop head")), [(0.72, 0.36), (0.72, 0.62), (1.14, 0.7), (1.2, 0.92), (1.04, 1.18), (0.6, 1.34), (0, 1.38)], 18, m)
    u0, v0, u1, v1 = L.HMI
    u0, u1 = u0 + L.bay_left(2), u1 + L.bay_left(2)
    t = 0.55
    for a, b, c, d in ((u0 - t, u1 + t, v0 - t, v0), (u0 - t, u1 + t, v1, v1 + t), (u0 - t, u0, v0, v1), (u1, u1 + t, v0, v1)):
        slope_box(add(Part(BLACK, 2, bevel=0.05, name="hmi frame")), a, b, c, d, 0.0, 0.3)
    glow_quad([S(u0, v0, 0.06), S(u1, v0, 0.06), S(u1, v1, 0.06), S(u0, v1, 0.06)], "hmi", 2)

    # Meters and the chart recorder.
    upright_box(add(Part(GREY, 3, bevel=0.05, name="upright rail")), 0, w, -0.45, 0.35, -0.25, 0.28)
    upright_box(add(Part(GREY, 3, bevel=0.05, name="upright rail")), 0, w, L.UPRIGHT_H - 0.3, L.UPRIGHT_H + 0.2, -0.2, 0.28)
    for u, needle in zip(L.METER_U, L.METER_NEEDLES):
        m = on_upright(u, L.METER_V)
        r = L.METER_R
        ring_solid(add(Part(BLACK, 2, bevel=0.0, name="meter bezel")), [(r - 0.5, 0.0), (r, 0.0), (r, 0.42), (r - 0.18, 0.56), (r - 0.42, 0.56), (r - 0.5, 0.3)], 24, m)
        # The pointer stands in front of its printed dial.
        a = math.radians(210 - 240 * needle)
        tip = (2.7 * math.cos(a), 2.7 * math.sin(a))
        nm = add(Part(RED, 1, name="needle"))
        side = (-math.sin(a) * 0.05, math.cos(a) * 0.05)
        c = [(-side[0], -side[1]), (tip[0] - side[0], tip[1] - side[1]), (tip[0] + side[0], tip[1] + side[1]), (side[0], side[1])]
        prism(nm, c, 0.12, 0.18, m)
        lathe(add(Part(BLACK, 1, name="needle hub")), [(0.26, 0.04), (0.26, 0.2), (0, 0.24)], 8, m)
    u0, v0, u1, v1 = L.CHART
    t = 0.38
    for a, b, c, d in ((u0 - t, u1 + t, v0 - t, v0), (u0 - t, u1 + t, v1, v1 + t), (u0 - t, u0, v0, v1), (u1, u1 + t, v0, v1)):
        upright_box(add(Part(BLACK, 2, bevel=0.05, name="chart frame")), a, b, c, d, 0.0, 0.5)
    pen = add(Part(CHROME, 1, bevel=0.02, name="chart pen"))
    upright_box(pen, u0 + 7.0, u0 + 7.6, v0 + 0.2, v1 - 0.2, 0.28, 0.42)
    upright_box(add(Part(RED, 0, name="chart nib")), u0 + 7.0, u0 + 7.6, v0 + 4.7, v0 + 5.25, 0.2, 0.5)

    # The hood over the meters, and the conduit up the side.
    box(add(Part(NAVY, 3, bevel=0.14, name="hood")), (-35.0, -58.6, 57.5), (-17.4, 58.6, 59.8))
    path = [(-30.0, 59.1, 0.0), (-30.0, 59.1, 52.0), (-30.0, 59.1, 53.2), (-30.0, 58.5, 54.2), (-30.0, 58.05, 54.6)]
    tube(add(Part(CHROME, 2, name="conduit")), path, 0.55, 10)
    for z in (6.0, 24.0, 44.0):
        clamp = add(Part(CHROME, 1, bevel=0.03, name="conduit strap"))
        box(clamp, (-31.3, 58.0, z - 0.4), (-28.7, 58.3, z + 0.4))
        tube(add(Part(CHROME, 1, name="strap")), [(-30.0 + 0.72 * math.cos(a), 59.1 + 0.72 * math.sin(a), z) for a in np.linspace(-0.3, math.pi + 0.3, 8)], 0.12, 5, flatten=2.2)
    box(add(Part(NAVY, 2, bevel=0.08, name="junction box")), (-32.4, 58.0, 35.0), (-27.6, 60.0, 40.5))


def pistol(u, v, turn):
    m = on_slope(u, v)
    lathe(add(Part(CHROME, 1, name="switch ring")), [(1.2, 0), (1.2, 0.1), (1.0, 0.18), (0.82, 0.2)], 16, m)
    lathe(add(Part(BLACK, 1, name="switch skirt")), [(0.82, 0.2), (0.74, 0.62), (0.52, 0.72)], 14, m)
    g = on_slope(u, v, 0.0, turn)
    outline = [(-0.36, -0.52), (0.36, -0.52), (0.56, 0.05), (0.24, 1.42), (-0.24, 1.42), (-0.56, 0.05)]
    prism(add(Part(BLACK, 2, bevel=0.1, segs=1, angle=30, name="pistol grip")), outline, 0.7, 1.42, g)
    box(add(Part(PLATE, 0, name="index line")), (-0.05, 0.1, 1.42), (0.05, 1.3, 1.43), g)


def lamp(u, v, kind):
    m = on_slope(u, v)
    lathe(add(Part(BLACK, 1, name="lamp bezel")), [(0.56, 0), (0.56, 0.12), (0.46, 0.2)], 10, m)
    glow_dome(m, 0.46, 0.2, 0.42, kind)


def button(u, v, finish):
    m = on_slope(u, v)
    lathe(add(Part(CHROME, 1, name="button collar")), [(0.6, 0), (0.6, 0.12), (0.5, 0.18)], 12, m)
    lathe(add(Part(finish, 1, name="button")), [(0.44, 0.18), (0.44, 0.42), (0.3, 0.5), (0, 0.52)], 10, m)


def glow_quad(corners, screen, lod=2):
    x, y, w, h = L.SCREENS[screen]
    W, H = L.SCREEN_ATLAS
    uv = [(x / W, 1 - (y + h) / H), ((x + w) / W, 1 - (y + h) / H), ((x + w) / W, 1 - y / H), (x / W, 1 - y / H)]
    add_face(glow, corners, uv)
    glow["lod"].append(lod)


def add_face(store, corners, uv):
    base = len(store["v"])
    store["v"].extend(tuple(c) for c in corners)
    store["uv"].extend(uv)
    store["f"].append(tuple(range(base, base + len(corners))))


def glow_dome(m, r, z, height, kind, sides=8):
    W, H = L.SCREEN_ATLAS
    cx, cy = L.SWATCHES[kind], L.SWATCH_Y
    rad = L.SWATCH_R
    rings = [(r, z, 1.0), (r * 0.72, z + height * 0.62, 0.62)]
    base = len(glow["v"])
    for rr, zz, t in rings:
        for k in range(sides):
            a = 2 * math.pi * k / sides
            glow["v"].append(tuple(m @ Vector((rr * math.cos(a), rr * math.sin(a), zz))))
            glow["uv"].append(((cx + rad * t * math.cos(a)) / W, 1 - (cy + rad * t * math.sin(a)) / H))
    glow["v"].append(tuple(m @ Vector((0, 0, z + height))))
    glow["uv"].append((cx / W, 1 - cy / H))
    for k in range(sides):
        n = (k + 1) % sides
        glow["f"].append((base + k, base + n, base + sides + n, base + sides + k))
        glow["lod"].append(1)
        glow["f"].append((base + sides + k, base + sides + n, base + 2 * sides))
        glow["lod"].append(1)


def monitor(centre, normal, width, height, screen, led=True):
    n = Vector(normal).normalized()
    up0 = Vector((0, 0, 1))
    right = up0.cross(n).normalized()
    up = n.cross(right).normalized()
    m = Matrix((right, up, n)).transposed().to_4x4()
    m.translation = Vector(centre)
    a, b = width / 2 + 0.75, height / 2 + 0.75
    c = 0.5
    rounded = [(-a + c, -b - 0.45), (a - c, -b - 0.45), (a, -b + c - 0.45), (a, b - c), (a - c, b), (-a + c, b), (-a, b - c), (-a, -b + c - 0.45)]
    prism(add(Part(BLACK, 3, bevel=0.1, angle=30, name="monitor case")), rounded, -2.4, -0.18, m)
    w2, h2 = width / 2, height / 2
    bez = 0.75
    for lo, hi in (((-w2 - bez, -h2 - bez - 0.45), (w2 + bez, -h2)), ((-w2 - bez, h2), (w2 + bez, h2 + bez)), ((-w2 - bez, -h2), (-w2, h2)), ((w2, -h2), (w2 + bez, h2))):
        box(add(Part(BLACK, 3, bevel=0.05, angle=30, name="bezel")), (lo[0], lo[1], -0.3), (hi[0], hi[1], 0.14), m)
    back = add(Part(BLACK, 2, bevel=0.2, angle=30, name="monitor back"))
    box(back, (-w2 * 0.62, -h2 * 0.62, -3.7), (w2 * 0.62, h2 * 0.62, -2.4), m)
    glow_quad([m @ Vector((-w2, -h2, -0.08)), m @ Vector((w2, -h2, -0.08)), m @ Vector((w2, h2, -0.08)), m @ Vector((-w2, h2, -0.08))], screen, 2)
    for k in range(4):
        box(add(Part(GREY, 0, name="monitor button")), (w2 - 4.6 + k * 1.15, -h2 - 0.95, 0.14), (w2 - 3.95 + k * 1.15, -h2 - 0.6, 0.18), m)
    if led:
        glow_dome(m @ Matrix.Translation((w2 - 0.6, -h2 - 0.78, 0.14)), 0.09, 0.0, 0.03, "G", 6)
    return m


def monitors():
    # Two posts through the hood, a beam across them, each screen on a bracket.
    for y in (-20.0, 20.0):
        box(add(Part(CHROME, 3, bevel=0.05, name="post")), (-30.0, y - 1.1, 59.8), (-27.8, y + 1.1, 66.2))
        lathe(add(Part(BLACK, 1, name="post collar")), [(2.0, 0), (2.0, 0.28), (1.6, 0.36)], 12, frame((-28.9, y, 59.8)))
    box(add(Part(CHROME, 3, bevel=0.05, name="beam")), (-30.2, -52.0, 64.0), (-27.6, 52.0, 66.5))
    tilt = math.radians(5)
    n = (math.cos(tilt), 0, math.sin(tilt))
    monitor((-19.6, 0.0, 73.2), n, 40.0, 23.4, "main")
    for s in (-1, 1):
        yaw = math.radians(22)
        side = (math.cos(yaw) * math.cos(tilt), -s * math.sin(yaw) * math.cos(tilt), math.sin(tilt))
        centre = (-21.4, s * 36.8, 70.2)
        monitor(centre, side, 26.5, 15.2, "trend" if s < 0 else "alarms")
        bracket = add(Part(CHROME, 2, name="bracket"))
        tube(bracket, [(-27.6, s * 36.8, 65.2), (-25.8 - 0.8, s * 36.8, 68.0), (-25.2, s * 36.5, 70.2)], 0.6, 10)
    tube(add(Part(CHROME, 2, name="bracket")), [(-27.6, 0.0, 65.2), (-25.0, 0.0, 71.0)], 0.9, 12)

    # Their cables, gathered and tied, down through a grommet in the hood.
    for k, (y, z) in enumerate(((-34.0, 64.0), (-31.0, 63.0), (-6.0, 62.0), (-3.0, 62.5), (31.0, 63.0), (34.0, 64.0))):
        hole = 10.0 if y > 0 else -10.0
        path = spline([(-24.6 - k * 0.06, y, z + 2.0), (-26.0, y * 0.92, z - 2.4), (-26.2, (y + hole) / 2, 61.3 + k * 0.1), (-26.6, hole + k * 0.05, 60.5), (-26.8, hole + k * 0.05, 59.7)], 5)
        tube(add(Part(RUBBER, 1, name="cable")), path, 0.2, 5)
    for s in (-1, 1):
        ring_solid(add(Part(RUBBER, 1, name="grommet")), [(1.0, 0), (1.45, 0), (1.45, 0.14), (1.0, 0.2)], 12, frame((-26.7, s * 10.0, 59.8)))


def worktop_items():
    z = 31.5
    # Keyboard: a low wedge with its keys.
    kx, ky = 17.0, -2.0
    kw, kd = 9.6, 3.5
    base = add(Part(BLACK, 2, bevel=0.1, angle=30, name="keyboard"))
    hexa(base, [(kx + kd, ky - kw, z), (kx + kd, ky + kw, z), (kx - kd, ky + kw, z), (kx - kd, ky - kw, z),
                (kx + kd, ky - kw, z + 0.42), (kx + kd, ky + kw, z + 0.42), (kx - kd, ky + kw, z + 0.82), (kx - kd, ky - kw, z + 0.82)])
    for row in range(5):
        cols = 14
        x = kx + kd - 1.0 - row * 1.25
        lift = 0.5 + (row * 1.25 / (2 * kd)) * 0.4
        for col in range(cols):
            width = 1.04
            y0 = ky - kw + 0.5 + col * 1.3
            if row == 4 and col in (5, 6, 7, 8):
                if col != 5:
                    continue
                width = 1.04 + 3.9
            box(add(Part(KEY, 0, bevel=0.04, angle=40, name="key")), (x - 0.5, y0, z + lift), (x + 0.5, y0 + width, z + lift + 0.26))
    box(add(Part(BLACK, 1, bevel=0.06, angle=30, name="key slab")), (kx - kd + 0.5, ky - kw + 0.4, z + 0.3), (kx + kd - 0.5, ky + kw - 0.4, z + 0.66))
    # Mouse.
    tube(add(Part(BLACK, 1, name="mouse")), [(kx + 2.0, 13.0, z + 0.5), (kx, 13.0, z + 0.72), (kx - 2.0, 13.0, z + 0.55)], [0.82, 1.02, 0.8], 12, flatten=0.5)
    tube(add(Part(RUBBER, 0, name="mouse lead")), spline([(kx - 2.6, 13.0, z + 0.3), (kx - 5.0, 12.4, z + 0.16), (kx - 9.0, 14.0, z + 0.14), (kx - 16.0, 12.0, z + 0.14), (-1.0, 12.2, z + 0.14)], 5), 0.1, 5)

    # The direct line to the grid control centre: red, and old.
    px, py = 15.0, -38.0

    def top(dx, dy, h=0.0):
        """A point on the phone's sloping face."""
        return (px + dx + h * 0.3, py + dy, z + 1.2 + (3.9 - dx) * 0.316 + h * 0.953)

    phone = add(Part(RED, 2, bevel=0.2, segs=2, angle=20, name="telephone"))
    hexa(phone, [(px + 4.7, py - 3.7, z), (px + 4.7, py + 3.7, z), (px - 4.7, py + 3.7, z), (px - 4.7, py - 3.7, z),
                 (px + 3.9, py - 3.1, z + 1.2), (px + 3.9, py + 3.1, z + 1.2), (px - 2.9, py + 2.9, z + 3.35), (px - 2.9, py - 2.9, z + 3.35)])
    hump = add(Part(RED, 2, bevel=0.2, segs=2, angle=20, name="cradle block"))
    hexa(hump, [(px - 0.6, py - 2.5, z + 2.0), (px - 0.6, py + 2.5, z + 2.0), (px - 4.1, py + 2.8, z + 2.0), (px - 4.1, py - 2.8, z + 2.0),
                (px - 1.2, py - 2.2, z + 3.7), (px - 1.2, py + 2.2, z + 3.7), (px - 3.7, py + 2.2, z + 4.1), (px - 3.7, py - 2.2, z + 4.1)])
    # Two forks that the handset rests in.
    for s in (-1, 1):
        fork = add(Part(RED, 1, bevel=0.08, angle=25, name="fork"))
        for x0, x1 in ((px - 1.5, px - 1.05), (px - 3.65, px - 3.2)):
            box(fork, (x0, py + s * 1.9 - 0.42, z + 3.7), (x1, py + s * 1.9 + 0.42, z + 4.95))
        box(add(Part(BLACK, 0, name="hook switch")), (px - 2.75, py + s * 1.9 - 0.3, z + 3.9), (px - 1.95, py + s * 1.9 + 0.3, z + 4.1))
    # The keypad, on a dark plate let into the slope.
    plate = add(Part(BLACK, 1, name="key plate"))
    hexa(plate, [top(3.1, -1.75), top(3.1, 1.75), top(-0.2, 1.75), top(-0.2, -1.75), top(3.1, -1.75, 0.03), top(3.1, 1.75, 0.03), top(-0.2, 1.75, 0.03), top(-0.2, -1.75, 0.03)])
    for row in range(4):
        for col in range(3):
            a = 2.65 - row * 0.8
            b = -1.05 + col * 1.05
            key = add(Part(PLATE, 0, name="phone key"))
            w, d_ = 0.36, 0.28
            hexa(key, [top(a + d_, b - w, 0.03), top(a + d_, b + w, 0.03), top(a - d_, b + w, 0.03), top(a - d_, b - w, 0.03),
                       top(a + d_, b - w, 0.16), top(a + d_, b + w, 0.16), top(a - d_, b + w, 0.16), top(a - d_, b - w, 0.16)])
    hx = px - 2.35
    hz = z + 5.0
    handset_path = spline([(hx, py - 4.3, hz), (hx, py - 3.0, hz + 0.35), (hx, py, hz + 0.45), (hx, py + 3.0, hz + 0.35), (hx, py + 4.3, hz)], 4)
    tube(add(Part(RED, 2, name="handset")), handset_path, 0.6, 12, flatten=0.82)
    for s in (-1, 1):
        lathe(add(Part(RED, 2, bevel=0.06, angle=25, name="ear cup")), [(1.02, -0.05), (1.24, 0.3), (1.2, 0.7), (0.74, 0.9)], 14, frame((hx, py + s * 4.35, hz - 0.2), (0, 0, -1)))
    # The coiled cord drops from the handset and lies on the desk before running into the phone's back.
    line = spline([(hx - 0.2, py - 5.1, hz - 0.5), (hx - 0.2, py - 5.7, z + 2.4), (hx + 1.2, py - 6.0, z + 0.45), (hx + 4.6, py - 6.5, z + 0.35), (hx + 7.4, py - 5.6, z + 0.35), (hx + 8.0, py - 4.2, z + 0.32)], 8)
    coil = []
    turns = 30
    steps = turns * 5
    centre = np.array([tuple(p) for p in line])
    chords = np.linalg.norm(np.diff(centre, axis=0), axis=1)
    along = np.concatenate(([0.0], np.cumsum(chords)))
    for k in range(steps + 1):
        t = k / steps * along[-1]
        c = np.array([np.interp(t, along, centre[:, j]) for j in range(3)])
        d_ = np.array([np.interp(min(t + 0.05, along[-1]), along, centre[:, j]) for j in range(3)]) - np.array([np.interp(max(t - 0.05, 0), along, centre[:, j]) for j in range(3)])
        d_ = d_ / max(np.linalg.norm(d_), 1e-6)
        u = np.cross(d_, (0.0, 0.0, 1.0))
        if np.linalg.norm(u) < 0.2:
            u = np.cross(d_, (1.0, 0.0, 0.0))
        u = u / np.linalg.norm(u)
        v = np.cross(d_, u)
        a = 2 * math.pi * k / 5
        coil.append(tuple(c + (u * math.cos(a) + v * math.sin(a)) * 0.24))
    tube(add(Part(RED, 0, name="phone cord")), coil, 0.065, 4)

    # Clipboard with the shift log.
    bx, by = 15.0, 30.0
    box(add(Part(BOARD, 2, bevel=0.02, angle=50, name="clipboard")), (bx - 6.2, by - 4.4, z), (bx + 6.2, by + 4.4, z + 0.14))
    box(add(Part(PAPER, 2, name="shift log")), (bx - 5.4, by - 4.0, z + 0.14), (bx + 4.9, by + 4.0, z + 0.26))
    box(add(Part(CHROME, 1, bevel=0.04, name="clip")), (bx - 6.0, by - 1.6, z + 0.26), (bx - 4.6, by + 1.6, z + 0.56))
    tube(add(Part(BLACK, 1, name="pen")), [(bx + 3.2, by + 5.8, z + 0.28), (bx - 2.0, by + 6.6, z + 0.28)], [0.17, 0.17], 8)

    # An enamel mug with a chipped rim.
    mx, my = L.MUG_XY
    m = frame((mx, my, z))
    lathe(add(Part(ENAMEL, 2, bevel=0.0, name="mug")), [(1.42, 0.0), (1.5, 0.08), (1.5, 3.5), (1.46, 3.6), (1.36, 3.6), (1.34, 0.5), (0, 0.5)], 18, m)
    tube(add(Part(ENAMEL, 1, name="mug handle")), spline([(mx, my - 1.45, z + 2.9), (mx, my - 2.4, z + 2.7), (mx, my - 2.5, z + 1.5), (mx, my - 1.45, z + 0.95)], 4), 0.2, 6, flatten=0.55)
    lathe(add(Part(BLACK, 1, name="coffee")), [(1.33, 1.8), (1.33, 2.65), (0, 2.65)], 16, m)


def geometry():
    pedestals()
    instrument_board()
    monitors()
    worktop_items()
    # The panel's two printed faces, on their own atlas.
    W, H = L.PANEL_ATLAS
    ppi = L.PPI

    def uv(row_top, block_h, u, v):
        return (u * ppi / W, 1 - (row_top + (block_h - v) * ppi) / H)

    w, l, h = L.PANEL_W, L.SLOPE_L, L.UPRIGHT_H
    add_face(panel, [S(0, 0), S(w, 0), S(w, l), S(0, l)], [uv(L.SLOPE_ROW, l, 0, 0), uv(L.SLOPE_ROW, l, w, 0), uv(L.SLOPE_ROW, l, w, l), uv(L.SLOPE_ROW, l, 0, l)])
    add_face(panel, [U(0, 0), U(w, 0), U(w, h), U(0, h)], [uv(L.UPRIGHT_ROW, h, 0, 0), uv(L.UPRIGHT_ROW, h, w, 0), uv(L.UPRIGHT_ROW, h, w, h), uv(L.UPRIGHT_ROW, h, 0, h)])


def mesh_from(name, store, keep=None):
    faces = [f for i, f in enumerate(store["f"]) if keep is None or store["lod"][i] >= keep]
    used = sorted({v for f in faces for v in f})
    remap = {v: i for i, v in enumerate(used)}
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([store["v"][v] for v in used], [], [tuple(remap[v] for v in f) for f in faces])
    layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = store["uv"][used[mesh.loops[li].vertex_index]]
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        bmesh.ops.recalc_face_normals(p.bm, faces=p.bm.faces)
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "body_lod0")
    mesh = hw.data
    # What faces the floor is never seen, so it takes no texture.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    drop = [f for f in bm.faces if f.normal.z < -0.9 and f.calc_center_median().z < 3.1]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, ATLAS, 6)
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mesh.calc_loop_triangles()
    area3 = uva = 0.0
    for tri in mesh.loop_triangles:
        a, b, c = co[list(tri.vertices)]
        area3 += 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        p, q, r = uv[list(tri.loops)]
        uva += 0.5 * abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]))
    density = ATLAS * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

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

    lod("body_lod1", 1, 0.7)
    lod("body_lod2", 3, 0.6)
    mesh_from("panel_lod0", panel)
    for level, keep in ((0, None), (1, 1), (2, 2)):
        mesh_from(f"glow_lod{level}", glow, keep)
    with open(os.path.join(WORK, "desk.json"), "w") as h:
        json.dump(dict(density=density), h)
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
    hw = bpy.data.objects["body_lod0"]
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.01))
    ground = bpy.context.object
    ground.name = "ground"
    keep = {hw, ground, bpy.data.objects["panel_lod0"], bpy.data.objects["glow_lod0"]}
    for ob in scene.objects:
        ob.hide_render = ob not in keep
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
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(size, size, 4).astype(np.float32))
        bpy.data.images.remove(img)
        print("baked", out, flush=True)

    bake_one(ATLAS, "EMIT", source("pos"), 1, "bake_desk_pos")
    bake_one(ATLAS, "EMIT", source("nor"), 1, "bake_desk_nor")
    bake_one(ATLAS, "EMIT", source("facts"), 1, "bake_desk_facts")
    bake_one(2048, "AO", None, 24, "bake_desk_ao")


def write_lod(path, sections):
    """sections: [(material, p, t, n)] in engine axes. Engine X, Y, Z become OBJ Z, X, Y, as in the capture flag's export."""
    tables = ({}, {}, {})
    lines = ([], [], [])
    faces = []
    tris = 0
    for material, p, t, n in sections:
        faces.append(f"usemtl {material}\n")
        po, no = p[..., [1, 2, 0]], n[..., [1, 2, 0]]
        for k in range(len(po)):
            tri = []
            for c in range(3):
                idx = []
                for table, store, prefix, vec in zip(tables, lines, ("v ", "vt ", "vn "), (po[k, c], t[k, c], no[k, c])):
                    key = tuple(np.round(vec, 5))
                    got = table.get(key)
                    if got is None:
                        got = len(table) + 1
                        table[key] = got
                        store.append(prefix + " ".join(f"{x:.5f}" for x in key) + "\n")
                    idx.append(got)
                tri.append("%d/%d/%d" % tuple(idx))
            faces.append("f " + " ".join(tri) + "\n")
        tris += len(po)
    with open(path, "w", newline="\n") as h:
        h.write(f"# Generated by Sources/Spillway/control-desk-v2/desk.py\nmtllib {NAME}.mtl\n")
        for block in lines:
            h.writelines(block)
        h.writelines(faces)
    return tris


def triangles(ob, flat_big):
    mesh = ob.data
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    if flat_big:
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
    p = co.reshape(-1, 3)[verts[loops]].reshape(-1, 3, 3)
    t = uv.reshape(-1, 2)[loops].reshape(-1, 3, 2)
    n = nn.reshape(-1, 3)[loops].reshape(-1, 3, 3)
    e.to_mesh_clear()
    if flat_big:
        # Big flat faces stay exactly flat, so the engine draws no shading wedges across them. Tubes turn by more than this limit.
        cross = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        area = np.linalg.norm(cross, axis=1) / 2
        face = cross / np.maximum(area[:, None] * 2, 1e-9)
        agree = (n * face[:, None, :]).sum(-1).min(1)
        pick = (area > 1.5) & (agree > math.cos(math.radians(9)))
        n[pick] = face[pick][:, None, :]
    return p, t, n


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["body_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    bounds = None
    counts = {}
    for lod in (0, 1, 2):
        body = triangles(bpy.data.objects[f"body_lod{lod}"], True)
        pan = triangles(bpy.data.objects["panel_lod0"], False)
        gl = triangles(bpy.data.objects[f"glow_lod{lod}"], False)
        counts[lod] = write_lod(os.path.join(out, f"{NAME}_lod{lod}.obj"), [("cd_body", *body), ("cd_panel", *pan), ("cd_glow", *gl)])
        if lod == 0:
            every = np.concatenate([x[0].reshape(-1, 3) for x in (body, pan, gl)])
            bounds = (every.min(0).tolist(), every.max(0).tolist())
        print("lod", lod, "tris", counts[lod], flush=True)
    with open(os.path.join(out, f"{NAME}.mtl"), "w", newline="\n") as h:
        for m in ("cd_body", "cd_panel", "cd_glow"):
            h.write(f"newmtl {m}\nKd 1 1 1\nd 1\n")
    remaps = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{m}.vmat" to = "{MATS}/{m}.vmat" }}' for m in ("cd_body", "cd_panel", "cd_glow"))
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/{NAME}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, THRESHOLDS))

    def phys(lo, hi):
        o = [(a + b) / 2 for a, b in zip(lo, hi)]
        s = [b - a for a, b in zip(lo, hi)]
        return (
            '\t\t\t\t\t{ _class = "PhysicsShapeBox" parent_bone = "" surface_prop = "metal" collision_tags = "solid" '
            f"origin = [ {o[0]:.3f}, {o[1]:.3f}, {o[2]:.3f} ] angles = [ 0.0, 0.0, 0.0 ] dimensions = [ {s[0]:.3f}, {s[1]:.3f}, {s[2]:.3f} ] }}"
        )

    shapes = ",\n".join(phys(*b) for b in (
        ((-35, -60, 0), (35, 60, 31.7)),  # The worktop and the pedestals, in the old box's footprint.
        ((-35, -58, 31.7), (-1, 58, 40)),  # The slope's lower half.
        ((-35, -58, 40), (-17.4, 58, 59.8)),  # Its upper half and the meters.
        ((-30.2, -52, 59.8), (-18, 52, 85.8)),  # The screens.
    ))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Spillway/control-desk-v2/desk.py
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
{remaps}
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
			{{
				_class = "PhysicsShapeList"
				children =
				[
{shapes}
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

    def pbr(name):
        return f"""// Generated by Sources/Spillway/control-desk-v2/desk.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/{name}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/{name}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/{name}_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/{name}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/{name}_rough.png"
}}
"""

    for name in ("cd_body", "cd_panel"):
        with open(os.path.join(mats, name + ".vmat"), "w", newline="\n") as h:
            h.write(pbr(name))
    # The same settings as the map's own screens, so they read as bright as the old ones did.
    glow_mat = f"""// Generated by Sources/Spillway/control-desk-v2/desk.py

Layer0
{{
	shader "shaders/complex.shader"
	F_SPECULAR 1
	F_SELF_ILLUM 1
	TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"
	g_flSelfIllumBrightness "3.00"
	g_flSelfIllumAlbedoFactor "1.0"
	g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"
	g_flRoughnessScaleFactor "1"
	g_flMetalness "0.00"
	TextureColor "{MATS}/cd_glow_color.png"
	TextureNormal "materials/default/default_normal.tga"
	TextureRoughness "[0.220000 0.220000 0.220000 0.000000]"
	TextureAmbientOcclusion "materials/default/default_ao.tga"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	g_flModelTintAmount "1.0"
}}
"""
    with open(os.path.join(mats, "cd_glow.vmat"), "w", newline="\n") as h:
        h.write(glow_mat)
    with open(os.path.join(WORK, "export.json"), "w") as h:
        json.dump(dict(triangles=counts, bounds=bounds), h)
    print("exported", counts, bounds, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("desk stages done", flush=True)
