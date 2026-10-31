"""Railhead luggage trolley v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python trolley.py -- <work dir> <project root> <build|bake|export> ...

A station baggage cart as a fabricator would make it: rolled channels and bolted boards on leaf springs, a steering bolster
with a forked drawbar, steel disc wheels on ribbed tyres. The load is separate, believable things: two framed and strapped
crates, a fibre trunk, an aluminium flight case, a pair of hard suitcases, a polymer case and a canvas roll. Every load item
fills the old model's collision box for it, so the old physics still fits and the four placements don't change.
Inches, engine axes: +X towards the drawbar, Y across, Z up, origin on the ground under the deck's centre.
"""
import hashlib
import json
import math
import os
import re
import shutil
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

from build import Part, add, box, frame, lathe, prism, spline, tube  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, CASE, ROPE, BOARD, GRAIN_X, GRAIN_Y, GRAIN_Z, CANVAS, STRAP, LABEL, LINER, AMBER, BRACE = range(19)
MODEL = "models/props/railhead/luggage_trolley_v2"
MATS = "materials/railhead/luggage_trolley_v2"
OLD_DIR = "models/props/railhead/luggage"
NAME = "luggage_trolley"
BLEND = os.path.join(WORK, "trolley_build.blend")
ATLAS = 4096

HL, HW, DECK = 49.2, 23.6, 24.0
WEB = HW + 0.55
ALONG_X = frame((0, 0, 0), (1, 0, 0), (0, 1, 0))  # Local x to +Y, local y to +Z, local z to +X.
rivets = []  # Fasteners too small to be worth triangles: painted from these, (x, y, z, radius).
nails = []
grains = {}  # Part rand: the way a brace's grain runs, filled in once parts have their rands.
rng = np.random.default_rng(3101)


def bx(finish, lod, lo, hi, bevel=0.06, name="", m=Matrix.Identity(4), segs=1, angle=40, texel=1.0):
    p = add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))
    box(p, lo, hi, m)
    p.texel = texel
    return p


def drop_down(p, limit=-0.9):
    """Remove faces pointing at the deck they rest on: never seen, and they'd only cost texture."""
    p.bm.normal_update()
    bmesh.ops.delete(p.bm, geom=[f for f in p.bm.faces if f.normal.z < limit], context="FACES")
    return p


def ring_sweep(part, profile, sides, m=Matrix.Identity(4)):
    """A closed profile of (radius, z) spun about local Z: a hollow ring with no end caps, as a tyre is."""
    bm = part.bm
    rings = [[bm.verts.new(m @ Vector((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z))) for k in range(sides)] for r, z in profile]
    for i, a in enumerate(rings):
        b = rings[(i + 1) % len(rings)]
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))


def ribbon(part, path, w, h, up=(0, 0, 1)):
    """A flat bar along a path, with a rectangular section: spring leaves and the like."""
    bm = part.bm
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        s = t.cross(Vector(up)).normalized()
        u = s.cross(t).normalized()
        rings.append([bm.verts.new(p + s * sa * w / 2 + u * ua * h / 2) for sa, ua in ((-1, -1), (-1, 1), (1, 1), (1, -1))])
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def sy(s, a, b):
    return min(s * a, s * b), max(s * a, s * b)


def bolt(at, axis, size=0.36, lod=1, finish=ZINC):
    kit.hex_bolt(at, axis, size, lod, washer=False, finish=finish)


def dome(finish, lod, at, axis, r, sides=8):
    lathe(add(Part(finish, lod, name="dome")), [(r, 0), (r, r * 0.3), (r * 0.7, r * 0.75), (0, r * 0.95)], sides, frame(at, axis))


def chassis():
    for s in (-1, 1):
        pts = [(WEB - 2.6, 18.9), (WEB, 18.9), (WEB, 22.9), (WEB - 2.6, 22.9), (WEB - 2.6, 22.62), (WEB - 0.28, 22.62), (WEB - 0.28, 19.18), (WEB - 2.6, 19.18)]
        outline = [(s * a, b) for a, b in pts]
        if s < 0:
            outline.reverse()
        p = add(Part(PAINT, 3, bevel=0.05, angle=30, name="side channel"))
        prism(p, outline, -HL, HL, ALONG_X)
        p.texel = 1.5  # Carries the fleet stencils.
        a, b = sy(s, WEB, HW + 1.0)
        bx(PAINT, 2, (-HL, a, 22.0), (HL, b, 23.2), 0.08, "rub rail")
        for sx in (-1, 1):
            # Fish plate where channel meets end member, bolted through.
            a, b = sy(s, WEB, WEB + 0.14)
            bx(PAINT, 1, (sx * (HL - 2) - 1.8, a, 18.5), (sx * (HL - 2) + 1.8, b, 21.95), 0.03, "fish plate", angle=30)
            for dz in (19.3, 21.2):
                for dx in (-1.1, 1.1):
                    bolt((sx * (HL - 2) + dx, s * (WEB + 0.14), dz), (0, s, 0), 0.3, 0)
            # Amber reflector on a bracket.
            a, b = sy(s, WEB, WEB + 0.1)
            bx(OXIDE, 1, (sx * 40 - 2.1, a, 19.45), (sx * 40 + 2.1, b, 21.75), 0.02, "reflector back", angle=30)
            a, b = sy(s, WEB + 0.1, WEB + 0.2)
            bx(AMBER, 1, (sx * 40 - 1.75, a, 19.75), (sx * 40 + 1.75, b, 21.45), 0.03, "reflector", angle=30, texel=1.6)
    for x in (-HL, HL):
        bx(PAINT, 3, (x - 0.8, -HW, 19.3), (x + 0.8, HW, 22.75), 0.1, "end member")
    for x in (-34, -8, 18, 34):
        bx(PAINT, 2, (x - 0.8, -HW + 0.28, 19.3), (x + 0.8, HW - 0.28, 22.6), 0.08, "cross member", texel=0.5)
    # Twelve deck boards, gaps showing. Their undersides go: one dark plate closes them and costs almost no texture.
    bx(LINER, 2, (-HL + 0.5, -HW + 0.3, 22.48), (HL - 0.5, HW - 0.3, 22.6), 0.0, "under deck", texel=0.2)
    width = HL * 2 / 12
    for i in range(12):
        x0 = -HL + i * width + 0.075
        x1 = -HL + (i + 1) * width - 0.075
        top = DECK - float(rng.uniform(0, 0.05))
        drop_down(bx(BOARD, 3, (x0, -HW + 0.5, 22.7), (x1, HW - 0.5, top), 0.08, "deck board"))
        for y in (-HW + 2.0, HW - 2.0, -11.4, 11.4):
            for dx in (-2.2, 2.2):
                rivets.append(((x0 + x1) / 2 + dx, y, top, 0.34))
    # Skid strips the crates are dragged along.
    for y in (-12.2, 12.2):
        bx(OXIDE, 2, (-47.5, y - 1.1, 23.98), (47.5, y + 1.1, 24.1), 0.02, "skid strip", angle=30)
        for x in np.arange(-44, 46, 8.2):
            rivets.append((float(x), y, 24.1, 0.26))
    # Sockets the end gates drop into.
    for sx in (-1, 1):
        for s in (-1, 1):
            x, y = sx * 48.2, s * 22.6
            bx(PAINT, 2, (x - 1.75, y - 1.65, 20.4), (x + 1.75, y + 1.65, 27.3), 0.12, "gate socket")
            for z in (21.8, 25.8):
                bolt((x + sx * 1.75, y, z), (sx, 0, 0), 0.34, 1)
            kit.weld_line((x - sx * 1.75, y - 1.65, 24.05), (x - sx * 1.75, y + 1.65, 24.05), 0.1, 0, 6)


def gate(x):
    y, z, r = 22.6, 43.4, 2.6
    path = [(x, -y, 22.6), (x, -y, z - r)]
    path += [(x, -y + r - r * math.cos(a), z - r + r * math.sin(a)) for a in np.linspace(0.2, math.pi / 2, 6)]
    path += [(x, y - r + r * math.sin(a), z - r + r * math.cos(a)) for a in np.linspace(0.0, math.pi / 2 - 0.2, 6)]
    path += [(x, y, z - r), (x, y, 22.6)]
    tube(add(Part(PAINT, 3, name="gate tube")), path, 0.9, 12)
    lathe(add(Part(PAINT, 3, name="gate rail")), [(0.65, -y), (0.65, y)], 10, frame((x, 0, 32.5), (0, 1, 0)))
    for s in (-1, 1):
        kit.weld_ring(0.68, frame((x, s * (y - 0.82), 32.5), (0, 1, 0)), 0.1, 12, 0)
    # The fleet plate hung from the rail, on both gates.
    sign = 1 if x > 0 else -1
    a, b = sorted((x + sign * 0.72, x + sign * 0.85))
    bx(PAINT, 2, (a, -5.5, 33.3), (b, 5.5, 39.3), 0.03, "fleet plate", angle=30, texel=1.5)
    for y2 in (-4, 4):
        bx(OXIDE, 1, (x - 0.9, y2 - 0.5, 32.3), (x + 0.95, y2 + 0.5, 33.6), 0.06, "plate clip")
        rivets.append((x + sign * 0.85, y2, 34.0, 0.24))
        rivets.append((x + sign * 0.85, y2, 38.6, 0.24))


def spring_pack(x, y):
    for i, half in enumerate((12.0, 9.6, 7.2, 4.8)):
        zc = 11.2 - i * 0.3
        path = [(x + q, y, zc + (q / 12.0) ** 2 * 3.2) for q in np.linspace(-half, half, 9)]
        ribbon(add(Part(OXIDE, 1 if i else 2, name="leaf")), path, 2.0, 0.26)
    # U-bolt over the axle, with a plate and nuts.
    bx(OXIDE, 1, (x - 1.4, y - 1.2, 9.05), (x + 1.4, y + 1.2, 10.05), 0.08, "spring seat")
    for dx in (-0.95, 0.95):
        path = [(x + dx, y - 1.5, 9.4), (x + dx, y - 1.5, 11.9), (x + dx, y - 1.1, 12.2), (x + dx, y + 1.1, 12.2), (x + dx, y + 1.5, 11.9), (x + dx, y + 1.5, 9.4)]
        tube(add(Part(ZINC, 0, name="u-bolt")), path, 0.15, 6)
    for dx in (-12.0, 12.0):
        lathe(add(Part(OXIDE, 1, name="spring eye")), [(0.55, -1.1), (0.55, 1.1)], 8, frame((x + dx, y - 1.1, 14.4), (0, 1, 0)))
        lathe(add(Part(ZINC, 0, name="shackle pin")), [(0.2, -1.5), (0.2, 3.7)], 6, frame((x + dx, y - 1.1, 14.4), (0, 1, 0)))
        bx(PAINT, 2, (x + dx - 0.75, y - 1.45, 14.0), (x + dx + 0.75, y - 1.15, 18.95), 0.03, "hanger", angle=30)
        bx(PAINT, 2, (x + dx - 0.75, y + 1.15, 14.0), (x + dx + 0.75, y + 1.45, 18.95), 0.03, "hanger", angle=30)


def wheel(x, s):
    m = frame((x, s * 19.8, 8.05), (0, s, 0))
    tyre = [(5.6, -1.6), (5.75, -1.8), (6.4, -1.85), (7.2, -1.65), (7.7, -1.3), (7.95, -1.0), (8.05, -0.92), (8.05, -0.58), (7.86, -0.52), (7.86, -0.22), (8.05, -0.17), (8.05, 0.17), (7.86, 0.22), (7.86, 0.52), (8.05, 0.58), (8.05, 0.92), (7.95, 1.0), (7.7, 1.3), (7.2, 1.65), (6.4, 1.85), (5.75, 1.8), (5.6, 1.6)]
    p = add(Part(RUBBER, 3, name="tyre"))
    ring_sweep(p, tyre, 28, m)
    p.texel = 1.2
    disc = [(0, -1.0), (1.6, -1.0), (2.4, -0.85), (4.4, -0.6), (5.0, -1.0), (5.25, -1.85), (5.7, -2.05), (5.98, -1.98), (5.98, -1.75), (5.62, -1.6), (5.62, 1.6), (5.98, 1.75), (5.98, 1.98), (5.9, 2.06), (5.62, 2.06), (5.38, 1.9), (5.12, 1.05), (5.0, 0.82), (4.75, 0.66), (3.5, 0.66), (3.25, 0.78), (2.95, 1.15), (2.85, 1.24), (2.0, 1.28), (1.3, 1.28), (0, 1.28)]
    p = add(Part(PAINT, 3, name="wheel disc"))
    lathe(p, disc, 24, m)
    p.texel = 1.3
    lathe(add(Part(OXIDE, 2, name="hub cap")), [(1.15, 1.25), (1.15, 1.7), (1.05, 1.85), (0.85, 2.1), (0.75, 2.35), (0.6, 2.42), (0, 2.45)], 12, m)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        at = m @ Vector((2.45 * math.cos(a), 2.45 * math.sin(a), 1.28))
        bolt(at, (0, s, 0), 0.4, 1)


def running_gear():
    for x in (-37.0, 33.0):
        lathe(add(Part(OXIDE, 3, name="axle")), [(1.12, -21.4), (1.12, 21.4)], 10, frame((x, 0, 8.05), (0, 1, 0)))
        for y in (-16.5, 16.5):
            spring_pack(x, y)
        for s in (-1, 1):
            wheel(x, s)
    # The steering bolster and turntable under the front.
    bx(PAINT, 2, (31.1, -18, 15.0), (34.9, 18, 17.9), 0.14, "bolster")
    ring_sweep(add(Part(OXIDE, 2, name="turntable")), [(6.4, 17.9), (6.4, 18.5), (5.9, 18.9), (1.5, 18.9), (1.5, 17.9)], 24, frame((33, 0, 0)))
    bx(PAINT, 1, (31, -6.2, 17.5), (42.4, 6.2, 18.1), 0.05, "fork plate", angle=30)
    # A forked drawbar on a pivot, drawn up to the frame by a return spring.
    for s in (-1, 1):
        for dy in (-0.95, 0.95):
            a, b = sy(1, s * 5 + dy - 0.17, s * 5 + dy + 0.17)
            bx(PAINT, 2, (38.5, a, 13), (41.8, b, 17.6), 0.03, "pivot ear", angle=30)
        lathe(add(Part(ZINC, 1, name="pivot pin")), [(0.42, -1.7), (0.42, 1.7)], 8, frame((40.1, s * 5, 15.1), (0, 1, 0)))
        bolt((40.1, s * 5 + 1.7, 15.1), (0, 1, 0), 0.5, 1)
        path = spline([(40, s * 5, 15.1), (58, s * 3, 9.5), (73, s * 1.7, 7.2)], 3)
        tube(add(Part(PAINT, 3, name="drawbar arm")), path, 0.74, 10, flatten=0.86)
    eye = [(76 + 3.2 * math.cos(a), 2.2 * math.sin(a), 7.1) for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)]
    tube(add(Part(OXIDE, 3, name="towing eye")), eye, 0.65, 8, closed=True)
    lathe(add(Part(PAINT, 2, name="drawbar tie")), [(0.6, -2.3), (0.6, 2.3)], 8, frame((70, 0, 7.55), (0, 1, 0)))
    lathe(add(Part(PAINT, 2, name="spring bar")), [(0.5, -3.3), (0.5, 3.3)], 8, frame((55, 0, 10.45), (0, 1, 0)))
    a, b = Vector((55, 0, 10.95)), Vector((49.3, 0, 19.2))
    u, v = Vector((0, 1, 0)), (b - a).normalized().cross(Vector((0, 1, 0)))
    coil = [a.lerp(b, k / 52.0) + (u * math.cos(k * math.tau / 7) + v * math.sin(k * math.tau / 7)) * 0.42 for k in range(53)]
    tube(add(Part(OXIDE, 0, name="return spring")), coil, 0.085, 4)


def face_frame(origin, n):
    n = Vector(n)
    return frame(origin, n, Vector((0, 0, 1)).cross(n))


def crate_face(origin, n, W, H, grain, seed, rail_grain=None):
    """A framed crate side. Local x across the face, local y up, local z out of the face; the frame's face is z = 0."""
    m = face_frame(origin, n)
    rail_grain = rail_grain if rail_grain is not None else grain
    B, R = 2.8, 2.6
    for u0, u1 in ((-W / 2, -W / 2 + B), (W / 2 - B, W / 2)):
        bx(GRAIN_Z, 3, (u0, 0, -0.7), (u1, H, 0), 0.08, "crate post", m)
    for v0, v1 in ((0, R), (H - R, H)):
        bx(rail_grain, 3, (-W / 2 + B, v0, -0.7), (W / 2 - B, v1, 0), 0.08, "crate rail", m)
    # Boards behind the frame, gaps uneven, as sawn stock is.
    rows = 4
    widths = rng.uniform(0.85, 1.15, rows)
    span = H - 2 * R
    v = R
    for w in widths * span / widths.sum():
        bx(grain, 3, (-W / 2 + B - 0.3, v + 0.13, -0.95), (W / 2 - B + 0.3, v + w - 0.13, -0.42), 0.05, "crate board", m)
        for u in (-W / 2 + B / 2, W / 2 - B / 2):
            for dv in (w * 0.28, w * 0.72):
                nails.append(tuple(m @ Vector((u, v + dv, 0.0))))
        v += w
    for v0 in (R / 2, H - R / 2):
        for u in np.linspace(-W / 2 + B + 1.4, W / 2 - B - 1.4, max(2, int(W / 7))):
            nails.append(tuple(m @ Vector((float(u), v0, 0.0))))
    # A diagonal brace, buried at its ends in the frame.
    a, b = Vector((-W / 2 + B, R)), Vector((W / 2 - B, H - R))
    if seed % 2:
        a.x, b.x = b.x, a.x
    length = (b - a).length
    turn = Matrix.Rotation(math.atan2(b.y - a.y, b.x - a.x), 4, "Z")
    mid = (a + b) / 2
    bm = m @ Matrix.Translation((mid.x, mid.y, 0)) @ turn
    p = bx(BRACE, 2, (-length / 2 - 0.5, -1.15, -0.62), (length / 2 + 0.5, 1.15, -0.14), 0.05, "crate brace", bm)
    p.grain = tuple((m.to_3x3() @ turn.to_3x3() @ Vector((1, 0, 0))))
    for t in (-0.32, 0.0, 0.32):
        nails.append(tuple(bm @ Vector((t * length, 0.0, -0.14))))


def rope_handle(m, H):
    path = spline([(-3.0, H - 4.2, -0.5), (-2.7, H - 5.3, 0.65), (0, H - 6.1, 1.0), (2.7, H - 5.3, 0.65), (3.0, H - 4.2, -0.5)], 3)
    tube(add(Part(ROPE, 1, name="rope handle")), [m @ p for p in path], 0.24, 6)
    for u in (-3.0, 3.0):
        rivets.append((*(m @ Vector((u, H - 4.2, 0.0))), 0.5))


def crate(lo, hi, seed, bands, holder=None):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    H = z1 - z0
    drop_down(bx(LINER, 3, (x0 + 0.85, y0 + 0.85, z0), (x1 - 0.85, y1 - 0.85, z1 - 0.7), 0.0, "crate liner", texel=0.25))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # X faces take the posts' full width; Y faces butt between them.
    crate_face((x0, cy, z0), (-1, 0, 0), y1 - y0, H, GRAIN_Y, seed)
    crate_face((x1, cy, z0), (1, 0, 0), y1 - y0, H, GRAIN_Y, seed + 1)
    crate_face((cx, y0, z0), (0, -1, 0), x1 - x0 - 1.4, H, GRAIN_X, seed + 1)
    crate_face((cx, y1, z0), (0, 1, 0), x1 - x0 - 1.4, H, GRAIN_X, seed)
    # Lid boards and two cleats.
    y = y0 + 0.7
    widths = rng.uniform(0.85, 1.15, 5)
    for w in widths * (y1 - y0 - 1.4) / widths.sum():
        bx(GRAIN_X, 3, (x0 + 0.7, y + 0.1, z1 - 0.62), (x1 - 0.7, y + w - 0.1, z1 - 0.16), 0.05, "lid board")
        y += w
    for x in (x0 + (x1 - x0) * 0.2, x0 + (x1 - x0) * 0.8):
        bx(GRAIN_Y, 2, (x - 1.2, y0 + 0.7, z1 - 0.16), (x + 1.2, y1 - 0.7, z1), 0.04, "lid cleat")
        for y2 in np.linspace(y0 + 2.2, y1 - 2.2, 5):
            nails.append((x, float(y2), z1))
    # Steel strapping, right round, with a crimped seal on top.
    for x in bands:
        bx(ZINC, 1, (x - 0.4, y0, z1), (x + 0.4, y1, z1 + 0.03), 0.0, "strapping", texel=0.7)
        bx(ZINC, 1, (x - 0.4, y0 - 0.03, z0 + 0.4), (x + 0.4, y0, z1 + 0.03), 0.0, "strapping", texel=0.7)
        bx(ZINC, 1, (x - 0.4, y1, z0 + 0.4), (x + 0.4, y1 + 0.03, z1 + 0.03), 0.0, "strapping", texel=0.7)
        bx(ZINC, 0, (x - 0.55, cy - 0.5, z1 + 0.03), (x + 0.55, cy + 0.5, z1 + 0.11), 0.015, "seal", angle=30)
    for n, at in (((-1, 0, 0), (x0, cy, z0)), ((1, 0, 0), (x1, cy, z0))):
        m = face_frame(at, n)
        rope_handle(m, H)
    if holder:
        # A tin holder with a paper waybill in it, on the boards.
        at, n = holder
        m = face_frame(at, n)
        bx(ZINC, 1, (-3.6, -2.6, -0.5), (3.6, 2.6, -0.34), 0.02, "waybill holder", m, angle=30)
        bx(LABEL, 1, (-3.25, -2.25, -0.34), (3.25, 2.25, -0.31), 0.0, "waybill", m, texel=2.6)


def rbox(finish, lod, lo, hi, r, segs=2, name=""):
    return bx(finish, lod, lo, hi, r, name, segs=segs)


def corners(lo, hi, size, finish, r=0.24, proud=0.04, lod=1, bottom=True):
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            for z in (lo[2], hi[2]) if bottom else (hi[2],):
                a = [x - proud if x == lo[0] else x - size, y - proud if y == lo[1] else y - size, z - proud if z == lo[2] else z - size]
                b = [x + size if x == lo[0] else x + proud, y + size if y == lo[1] else y + proud, z + size if z == lo[2] else z + proud]
                bx(finish, lod, a, b, r, "corner cap")
                sx, sy_ = (1 if x == lo[0] else -1), (1 if y == lo[1] else -1)
                rivets.append((x + sx * size * 0.55, y - sy_ * proud, z + (1 if z == lo[2] else -1) * size * 0.55, 0.13))
                rivets.append((x - sx * proud, y + sy_ * size * 0.55, z + (1 if z == lo[2] else -1) * size * 0.55, 0.13))


def catch(x, y, z, s, finish=BRASS, lod=1):
    """A draw latch across a lid seam, on a face looking along s in Y."""
    a, b = sy(s, y, y + 0.1)
    bx(finish, lod, (x - 0.6, a, z - 1.25), (x + 0.6, b, z + 0.95), 0.03, "latch plate", angle=30)
    a, b = sy(s, y + 0.1, y + 0.26)
    bx(finish, lod, (x - 0.38, a, z - 0.75), (x + 0.38, b, z + 0.45), 0.05, "latch lever")
    lathe(add(Part(finish, 0, name="latch pin")), [(0.14, -0.5), (0.14, 0.5)], 6, frame((x, y + s * 0.26, z - 0.7), (1, 0, 0)))
    for dz in (-1.0, 0.75):
        for dx in (-0.4, 0.4):
            rivets.append((x + dx, y + s * 0.1, z + dz, 0.09))


def trunk():
    """The fibre trunk on top: oxblood, bound in dark steel, strapped in leather."""
    x0, y0, z0, x1, y1, z1 = -45.8, 7.9, 38.55, -19.2, 21.5, 47.4
    seam = 45.0
    drop_down(rbox(CASE, 3, (x0 + 0.06, y0 + 0.06, z0), (x1 - 0.06, y1 - 0.06, seam - 0.06), 0.4, 2, "trunk body"))
    rbox(CASE, 3, (x0 + 0.06, y0 + 0.06, seam + 0.06), (x1 - 0.06, y1 - 0.06, z1 - 0.02), 0.75, 2, "trunk lid")
    bx(LINER, 2, (x0 + 0.3, y0 + 0.3, seam - 0.07), (x1 - 0.3, y1 - 0.3, seam + 0.07), 0.0, "trunk gasket", texel=0.3)
    bx(OXIDE, 2, (x0, y0, seam - 0.8), (x1, y1, seam - 0.1), 0.36, "trunk binding")
    bx(OXIDE, 2, (x0, y0, seam + 0.1), (x1, y1, seam + 0.8), 0.36, "trunk binding")
    bx(OXIDE, 2, (x0 + 0.02, y0 + 0.02, z0 + 0.1), (x1 - 0.02, y1 - 0.02, z0 + 0.72), 0.2, "trunk binding")
    corners((x0, y0, z0 + 0.1), (x1, y1, z1), 1.7, OXIDE, 0.3, 0.03)
    for x in np.linspace(x0 + 3, x1 - 3, 9):
        rivets.append((float(x), y1, seam - 0.45, 0.13))
        rivets.append((float(x), y1, seam + 0.45, 0.13))
    for x in (x0 + 6.2, x1 - 6.2):
        bx(STRAP, 1, (x - 0.85, y0 - 0.04, z1 - 0.03), (x + 0.85, y1 + 0.04, z1 + 0.06), 0.03, "trunk strap", angle=30)
        bx(STRAP, 1, (x - 0.85, y1 - 0.02, z0 + 0.4), (x + 0.85, y1 + 0.07, z1 + 0.05), 0.03, "trunk strap", angle=30)
        bx(STRAP, 1, (x - 0.85, y0 - 0.07, z0 + 0.4), (x + 0.85, y0 + 0.02, z1 + 0.05), 0.03, "trunk strap", angle=30)
        # A square buckle, on the strap's front run.
        for lo, hi in (((x - 1.1, 0, 41.6), (x - 0.86, 0, 43.9)), ((x + 0.86, 0, 41.6), (x + 1.1, 0, 43.9)), ((x - 1.1, 0, 41.36), (x + 1.1, 0, 41.6)), ((x - 1.1, 0, 43.9), (x + 1.1, 0, 44.14))):
            bx(BRASS, 1, (lo[0], y1 + 0.03, lo[2]), (hi[0], y1 + 0.22, hi[2]), 0.04, "buckle")
    # Lock plate and two latches on the front.
    bx(BRASS, 2, (-34.4, y1 - 0.02, seam - 1.7), (-30.6, y1 + 0.12, seam + 1.2), 0.05, "lock plate", angle=30)
    lathe(add(Part(BRASS, 0, name="lock boss")), [(0.55, 0), (0.55, 0.1), (0.35, 0.2), (0, 0.22)], 10, frame((-32.5, y1 + 0.12, seam - 0.15), (0, 1, 0)))
    for x in (x0 + 11.2, x1 - 11.2):
        catch(x, y1, seam, 1)
    # A leather handle on the near end.
    m = frame((x1, 14.7, 42.0), (1, 0, 0), (0, 1, 0))
    for dy in (-2.7, 2.7):
        bx(BRASS, 1, (dy - 0.55, -0.55, -0.03), (dy + 0.55, 0.55, 0.14), 0.04, "handle loop", m)
    path = spline([(-2.7, 0, 0.16), (-2.2, -0.2, 0.75), (0, -0.55, 1.05), (2.2, -0.2, 0.75), (2.7, 0, 0.16)], 3)
    tube(add(Part(STRAP, 1, name="trunk handle")), [m @ Vector(p) for p in path], 0.3, 6, flatten=0.6)


def flight_case():
    """An aluminium flight case: ribbed panels in extrusions, ball corners, butterfly latches."""
    x0, y0, z0, x1, y1, z1 = -46.0, 7.9, 24.0, -19.0, 21.5, 38.3
    seam = 33.7
    drop_down(bx(GALV, 3, (x0 + 0.35, y0 + 0.35, z0), (x1 - 0.35, y1 - 0.35, seam - 0.1), 0.03, "case panel"))
    bx(GALV, 3, (x0 + 0.35, y0 + 0.35, seam + 0.1), (x1 - 0.35, y1 - 0.35, z1 - 0.12), 0.03, "case panel")
    bx(LINER, 2, (x0 + 0.5, y0 + 0.5, seam - 0.12), (x1 - 0.5, y1 - 0.5, seam + 0.12), 0.0, "case gasket", texel=0.3)
    for a, b in ((z0, z0 + 1.1), (seam - 1.1, seam - 0.08), (seam + 0.08, seam + 1.1), (z1 - 1.1, z1)):
        bx(OXIDE, 3, (x0 + 0.12, y0 + 0.12, a), (x1 - 0.12, y1 - 0.12, b), 0.1, "extrusion")
    for x in (x0, x1 - 1.5):
        for y in (y0, y1 - 1.5):
            bx(OXIDE, 2, (x, y, z0 + 0.6), (x + 1.5, y + 1.5, z1 - 0.6), 0.22, "corner extrusion")
    for x in (x0 + 0.5, x1 - 0.5):
        for y in (y0 + 0.5, y1 - 0.5):
            for z in (z0 + 0.85, z1 - 0.85):
                lathe(add(Part(ZINC, 1, name="ball corner")), [(0, -0.85), (0.6, -0.6), (0.85, 0), (0.6, 0.6), (0, 0.85)], 8, frame((x, y, z)))
    for x in (x0 + 5.2, x1 - 5.2):
        catch(x, y1 - 0.12, seam, 1, ZINC)
    # Dish handles on the ends, and one on the long side.
    for x, s in ((x1 - 0.35, 1), (x0 + 0.35, -1)):
        a, b = sorted((x, x + s * 0.12))
        bx(OXIDE, 2, (a, 12.2, 27.4), (b, 17.2, 30.6), 0.04, "dish plate", angle=30)
        path = spline([(x + s * 0.12, 12.9, 29.3), (x + s * 0.7, 13.5, 29.0), (x + s * 0.95, 14.7, 28.9), (x + s * 0.7, 15.9, 29.0), (x + s * 0.12, 16.5, 29.3)], 2)
        tube(add(Part(ZINC, 1, name="case handle")), path, 0.2, 6)
    for x in np.linspace(x0 + 2.5, x1 - 2.5, 11):
        for z in (z0 + 0.55, seam - 0.6, seam + 0.6, z1 - 0.55):
            rivets.append((float(x), y1 - 0.12, z, 0.09))


def hard_case(x0, y0, z0, x1, y1, z1, tag=False):
    """A hard suitcase stood on end: two moulded shells on an aluminium seam, handle up."""
    ym = (y0 + y1) / 2
    drop_down(rbox(CASE, 3, (x0, y0, z0 + 0.3), (x1, ym - 0.14, z1), 1.0, 3, "shell")).texel = 1.3
    drop_down(rbox(CASE, 3, (x0, ym + 0.14, z0 + 0.3), (x1, y1, z1), 1.0, 3, "shell")).texel = 1.3
    bx(GALV, 2, (x0 + 0.05, ym - 0.22, z0 + 0.34), (x1 - 0.05, ym + 0.22, z1 - 0.05), 0.5, "seam frame", segs=2)
    for x in (x0 + 1.0, x1 - 3.0):
        drop_down(bx(RUBBER, 1, (x, y0 + 1.1, z0), (x + 2.0, y1 - 1.1, z0 + 0.42), 0.08, "foot"))
    # Moulded bumpers on the four bottom corners.
    for x in (x0 - 0.02, x1 - 2.1):
        for y in (y0 - 0.02, y1 - 1.9):
            bx(OXIDE, 1, (x, y, z0 + 0.3), (x + 2.12, y + 1.92, z0 + 2.3), 0.4, "bumper", segs=1)
    cx = (x0 + x1) / 2
    bx(OXIDE, 2, (cx - 3.6, ym - 1.25, z1 - 0.02), (cx + 3.6, ym + 1.25, z1 + 0.12), 0.05, "handle plate", angle=30)
    for dx in (-2.7, 2.7):
        bx(ZINC, 1, (cx + dx - 0.34, ym - 0.42, z1 + 0.1), (cx + dx + 0.34, ym + 0.42, z1 + 0.75), 0.08, "handle bracket")
    path = spline([(cx - 2.7, ym, z1 + 0.6), (cx - 2.3, ym, z1 + 1.6), (cx - 1.1, ym, z1 + 1.86), (cx + 1.1, ym, z1 + 1.86), (cx + 2.3, ym, z1 + 1.6), (cx + 2.7, ym, z1 + 0.6)], 3)
    tube(add(Part(STRAP, 2, name="case handle")), path, 0.27, 8, flatten=0.7)
    for dx in (-4.6, 4.6):
        bx(ZINC, 1, (cx + dx - 0.5, ym - 0.7, z1 - 0.03), (cx + dx + 0.5, ym + 0.7, z1 + 0.09), 0.03, "case lock", angle=30)
    if tag:
        # A luggage label on a string from the handle, hanging down the case's near end.
        tx, ty = x1 + 0.05, ym + 0.5
        path = spline([(cx + 1.8, ym, z1 + 1.72), (cx + 4.5, ym + 0.2, z1 + 1.0), (tx + 0.1, ty, z1 - 0.6), (tx + 0.12, ty, z1 - 3.1)], 3)
        tube(add(Part(ROPE, 0, name="tag string")), path, 0.035, 4)
        bx(LABEL, 1, (tx + 0.08, ty - 0.95, z1 - 6.2), (tx + 0.11, ty + 0.95, z1 - 3.0), 0.0, "luggage tag", texel=2.6)


def polymer_case():
    """A black moulded case with ribs in the lid and two latches on its long side."""
    x0, y0, z0, x1, y1, z1 = 7.9, -20.8, 24.0, 33.4, -7.0, 34.2
    seam = 30.2
    drop_down(rbox(CASE, 3, (x0, y0 + 0.2, z0), (x1, y1, seam - 0.05), 0.55, 2, "case tub"))
    rbox(CASE, 3, (x0, y0 + 0.2, seam + 0.05), (x1, y1, z1 - 0.2), 0.7, 2, "case lid")
    bx(LINER, 2, (x0 + 0.3, y0 + 0.5, seam - 0.06), (x1 - 0.3, y1 - 0.3, seam + 0.06), 0.0, "case gasket", texel=0.3)
    for y in (y0 + 3.3, (y0 + y1) / 2, y1 - 3.1):
        bx(CASE, 2, (x0 + 2.2, y - 0.9, z1 - 0.22), (x1 - 2.2, y + 0.9, z1), 0.1, "lid rib")
    for x in (x0 + 2.0, x1 - 3.4):
        bx(CASE, 2, (x, y0, z0 + 0.8), (x + 1.4, y0 + 0.22, z1 - 0.8), 0.07, "side rib")
    for x in (x0 + 6.2, x1 - 6.2):
        catch(x, y0 + 0.2, seam, -1, OXIDE)
    # A folding handle in the middle of the long side.
    cx = (x0 + x1) / 2
    for dx in (-3.4, 3.4):
        bx(CASE, 1, (cx + dx - 0.45, y0, 26.1), (cx + dx + 0.45, y0 + 0.2, 28.6), 0.05, "handle lug")
    path = [(cx - 3.4, y0, 27.2), (cx - 2.9, y0 - 0.46, 27.05), (cx + 2.9, y0 - 0.46, 27.05), (cx + 3.4, y0, 27.2)]
    tube(add(Part(RUBBER, 1, name="fold handle")), path, 0.27, 6, flatten=0.75)
    # A pressure valve in the end.
    lathe(add(Part(OXIDE, 0, name="valve")), [(0.55, 0), (0.55, 0.14), (0.3, 0.2), (0, 0.22)], 10, frame((x1, -13.9, 27.4), (1, 0, 0)))


ROLL = dict(y0=-20.1, y1=17.4, x=40.4, z=29.1, r=5.05, straps=(-9.8, 8.8))


def roll_point(y, a, dr=0.0, wrinkle=True):
    R = ROLL
    squeeze = sum(math.exp(-(((y - s) / 1.05) ** 2)) for s in R["straps"])
    fold = 0.0
    if wrinkle:
        fold = (0.13 * math.cos(a * 7 + y * 0.31) + 0.09 * math.sin(a * 11 - y * 0.47) + 0.06 * math.sin(a * 3 + y * 0.9)) * max(0.0, 1 - squeeze * 1.3)
    t = (y - R["y0"]) / (R["y1"] - R["y0"])
    end = 0.28 * min(1.0, min(t, 1 - t) / 0.03)
    r = R["r"] - 0.3 * squeeze + fold + end - 0.28 + dr
    x = R["x"] + math.sin(a) * r
    z = R["z"] + math.cos(a) * r * 0.97
    return Vector((x, y, max(z, 24.04)))


def canvas_roll():
    R = ROLL
    sides = 28
    ys = list(np.linspace(R["y0"], R["y1"], 44))
    p = add(Part(CANVAS, 3, name="canvas roll"))
    bm = p.bm
    rings = [[bm.verts.new(roll_point(y, 2 * math.pi * k / sides)) for k in range(sides)] for y in ys]
    # The rolled ends are set in a little, as cloth is when it's been rolled tight.
    rings.insert(0, [bm.verts.new(roll_point(R["y0"] + 0.22, 2 * math.pi * k / sides, -0.42, False)) for k in range(sides)])
    rings.append([bm.verts.new(roll_point(R["y1"] - 0.22, 2 * math.pi * k / sides, -0.42, False)) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))
    for s in R["straps"]:
        q = add(Part(STRAP, 2, name="roll strap"))
        bm = q.bm
        loops = [[bm.verts.new(roll_point(s + dy, 2 * math.pi * k / sides, dr, False)) for k in range(sides)] for dy, dr in ((-0.62, -0.15), (-0.58, 0.08), (0.58, 0.08), (0.62, -0.15))]
        for i, a in enumerate(loops):
            b = loops[(i + 1) % 4]
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
        top = R["z"] + (R["r"] - 0.3 - 0.28 + 0.28 + 0.08) * 0.97
        bx(OXIDE, 1, (R["x"] - 0.8, s - 0.86, top - 0.1), (R["x"] - 0.56, s + 0.86, top + 0.18), 0.03, "buckle")
        bx(OXIDE, 1, (R["x"] + 0.56, s - 0.86, top - 0.1), (R["x"] + 0.8, s + 0.86, top + 0.18), 0.03, "buckle")
        for dy in (-0.86, 0.68):
            bx(OXIDE, 1, (R["x"] - 0.8, s + dy, top - 0.1), (R["x"] + 0.8, s + dy + 0.18, top + 0.18), 0.03, "buckle")
        bx(STRAP, 1, (R["x"] - 0.1, s - 0.56, top + 0.02), (R["x"] + 2.5, s + 0.56, top + 0.12), 0.02, "strap tail", angle=30)


def geometry():
    chassis()
    gate(-48.2)
    gate(48.2)
    running_gear()
    # Each item fills its old collision box. Red and aluminium behind the far crate, the blue pair in the middle.
    crate((-45.5, -21.0, DECK), (-18.5, 7.2, 43.9), 0, (-39.0, -25.0), ((-32.0, -21.0, DECK + 8.8), (0, -1, 0)))
    flight_case()
    trunk()
    hard_case(-15.2, -19.1, DECK, -0.6, -10.0, 52.1, tag=True)
    hard_case(-13.6, -7.5, DECK, 1.0, 1.7, 50.3)
    crate((9.6, -3.7, DECK), (34.0, 20.0, 42.5), 2, (15.2, 28.4), ((21.8, 20.0, DECK + 8.2), (0, 1, 0)))
    polymer_case()
    canvas_roll()


def skyline(rects, limit):
    """Bottom-left placement of (w, h, key) in a limit-sized square. Returns key: (x, y), or None if they don't fit."""
    line = [[0.0, 0.0, limit]]  # x, y, width
    places = {}
    for w, h, key in rects:
        best, best_y = None, None
        for i, (x, _, _) in enumerate(line):
            if x + w > limit + 1e-6:
                break
            y, covered, j = 0.0, 0.0, i
            while covered < w:
                y = max(y, line[j][1])
                covered += line[j][2]
                j += 1
            if best_y is None or y < best_y:
                best, best_y = i, y
        if best is None or best_y + h > limit:
            return None
        x = line[best][0]
        places[key] = (x, best_y)
        rest, j = w, best
        while rest > 1e-9:
            if line[j][2] <= rest:
                rest -= line[j][2]
                del line[j]
            else:
                line[j][0] += rest
                line[j][2] -= rest
                rest = 0
        line.insert(best, [x, best_y + h, w])
        i = max(best - 1, 0)
        while i < len(line) - 1:
            if abs(line[i][1] - line[i + 1][1]) < 1e-9:
                line[i][2] += line[i + 1][2]
                del line[i + 1]
            else:
                i += 1
    return places


def pack_atlas(mesh, lookup, res, pad_px):
    """Real-scale islands, skyline packed. A part's texel scale and faces nobody can see set how much atlas each island gets."""
    from mathutils.bvhtree import BVHTree

    facts = mesh.color_attributes["facts"].data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    layer = bm.loops.layers.uv.active
    tree = BVHTree.FromBMesh(bm)
    weight = {}
    for f in bm.faces:
        centre = f.calc_center_median()
        hit = tree.ray_cast(centre + f.normal * 0.012, f.normal, 0.75)
        hidden = hit[0] is not None
        weight[f.index] = (getattr(lookup[round(facts[f.loops[0].index].color[1], 4)], "texel", 1.0), hidden)
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
    low_islands = 0
    for n, faces in enumerate(islands):
        area3 = sum(f.calc_area() for f in faces)
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        pts = tris.reshape(-1, 2)
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
        texel = weight[faces[0].index][0]
        if all(weight[f.index][1] for f in faces):
            texel = min(texel, 0.2)
            low_islands += 1
        scale = math.sqrt(area3 / max(areauv, 1e-12)) * texel
        centre = pts.mean(0)
        inches = (pts - centre) * scale
        best = None
        for deg in np.linspace(0, 90, 13):
            r = math.radians(deg)
            rot = np.array(((math.cos(r), -math.sin(r)), (math.sin(r), math.cos(r))))
            q = inches @ rot.T
            w, h = np.ptp(q, axis=0)
            if best is None or w * h < best[0]:
                best = (w * h, rot, w, h)
        _, rot, w, h = best
        if h > w:
            rot = np.array(((0.0, 1.0), (-1.0, 0.0))) @ rot
            w, h = h, w
        q = inches @ rot.T
        rects.append((w, h, n, centre, scale, rot, q.min(0)))
    order = sorted(rects, key=lambda r: (-round(r[1], 1), -r[0]))

    def attempt(px_per_in):
        pad = pad_px / px_per_in
        return skyline([(r[0] + pad, r[1] + pad, r[2]) for r in order], res / px_per_in)

    lo, hi = 2.0, 60.0
    places = None
    for _ in range(11):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            places, lo = got, mid
        else:
            hi = mid
    density = lo
    half = pad_px / density / 2
    for w, h, n, centre, scale, rot, low in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px + half) * density / res, (q[1] + py + half) * density / res)
    bm.to_mesh(mesh)
    bm.free()
    print("islands", len(rects), "low-texel", low_islands, "density px/in %.1f" % density, flush=True)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    count = len(kit.parts)
    order = np.random.default_rng(77).permutation(count)
    for i, p in enumerate(kit.parts):
        kit.harden(p)
        if max(v.co.z for v in p.bm.verts) < 19.0 and p.finish != RUBBER and p.name not in ("wheel disc", "hub cap", "drawbar arm", "towing eye", "bolt"):
            p.texel = min(getattr(p, "texel", 1.0), 0.55)
        p.done = p.bm
        p.rand = (float(order[i]) + 0.5) / count  # Unique per part: the LODs and braces look parts up by it.
        if hasattr(p, "grain"):
            grains[f"{p.rand:.5f}"] = list(p.grain)
    print("parts", count, flush=True)
    hw = kit.join_parts(kit.parts, "trolley_lod0")
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
    mesh = hw.data
    pack_atlas(mesh, lookup, ATLAS, 3)
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    mesh.calc_loop_triangles()
    area3 = uva = 0.0
    for tri in mesh.loop_triangles:
        a, b, c = co[list(tri.vertices)]
        area3 += 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        p, q, r = uv[list(tri.loops)]
        uva += 0.5 * abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]))
    density = ATLAS * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)

    def lod(name, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = name
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        layer = bm.loops.layers.float_color["facts"]
        drop = [f for f in bm.faces if lookup[round(f.loops[0][layer][1], 4)].lod < keep]
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

    lod("trolley_lod1", 1, 0.6)
    lod("trolley_lod2", 2, 0.35)
    lod("trolley_lod3", 3, 0.16)
    with open(os.path.join(WORK, "trolley.json"), "w") as h:
        json.dump(dict(density=density, rivets=rivets, nails=[list(n) for n in nails], grains=grains), h)
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
    hw = bpy.data.objects["trolley_lod0"]
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

    bake_one(ATLAS, "EMIT", source("pos"), 1, "bake_trolley_pos")
    bake_one(ATLAS, "EMIT", source("nor"), 1, "bake_trolley_nor")
    bake_one(ATLAS, "EMIT", source("facts"), 1, "bake_trolley_facts")
    bake_one(2048, "AO", None, 24, "bake_trolley_ao")


def old_physics():
    """The old model's collision, word for word, with its hull files copied into this folder."""
    text = open(os.path.join(ROOT, "Assets", OLD_DIR, f"{NAME}.vmdl"), encoding="utf-8").read()
    start = text.index('_class = "PhysicsShapeList"')
    open_at = text.rindex("{", 0, start)
    depth = 0
    for i in range(open_at, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            block = text[open_at : i + 1]
            break
    out = os.path.join(ROOT, "Assets", MODEL)
    for name in re.findall(r'filename = "([^"]+)"', block):
        shutil.copyfile(os.path.join(ROOT, "Assets", name), os.path.join(out, os.path.basename(name)))
    return block.replace(OLD_DIR + "/", MODEL + "/")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["trolley_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in range(4):
        ob = bpy.data.objects[f"trolley_lod{lod}"]
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
            h.write(f"# Generated by Sources/Railhead/props/luggage_trolley_v2/trolley.py\nmtllib {NAME}.mtl\n")
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
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 15.0, 40.0, 90.0)))
    physics = old_physics()
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Railhead/props/luggage_trolley_v2/trolley.py
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
			{physics},
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
    vmat = f"""// Generated by Sources/Railhead/props/luggage_trolley_v2/trolley.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

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
}}
"""
    os.makedirs(mats, exist_ok=True)
    with open(os.path.join(mats, f"{NAME}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("trolley stages done", flush=True)
