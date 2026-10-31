"""LPG cylinder v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python lpg.py -- <work dir> <project root> <intact|ruptured|cap> <build|bake|export> ...

A strapped forklift fuel cylinder as one really is: a three-piece welded shell, a foot ring, a valve guard on four welded
legs, a service valve with its handwheel, a relief valve, a bleed screw and a contents gauge, a hose down to the truck,
and two saddles with rubber-lined straps closed by a T-bolt. Inches, engine axes, the bottle along Y, the valve at +Y.

What LpgCanister relies on is kept: the origin at the bottle's centre, the shell profile its leak code works out by hand
(r 6.3 to |y| 13.5, then 5.9 at 15.2, 4.7 at 16.4, 2.3 at 17), the valve inside the scene's 1.5-radius collider at
y = 17.8, the hose's end where it meets the truck, and the cap's 12.6 x 3.5 size with its origin at its centre.
"""
import hashlib
import json
import math
import os
import shutil
import sys

sys.dont_write_bytecode = True
import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT, VARIANT = argv[0], argv[1], argv[2]
STAGES = argv[3:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, box, frame, hex_bolt, lathe, prism, ring_path, spline, tube, weld_line, weld_ring  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST = kit.PAINT, kit.GALV, kit.OXIDE, kit.ZINC, kit.BRASS, kit.RUBBER, kit.WELD, kit.PLATE, kit.RUST
SHELL, GUARD, RED, SOOT, DIAL, TORN = 9, 10, 11, 12, 13, 14

MODEL = "models/props/lowtide/lpg_canister_v2"
MATS = "materials/lowtide/lpg_canister_v2"
RETIRED = os.path.join(ROOT, "output/asset-improvement-20261030/lpg-canister/retired-lpg_canister")
VARIANTS = {
    "intact": dict(name="lpg_canister", mat="lpg_intact", size=2048, ao=1024, lods=((1, 0.5), (2, 0.2)), thresholds=(0.0, 26.0, 75.0), ground=True),
    "ruptured": dict(name="lpg_canister_ruptured", mat="lpg_ruptured", size=2048, ao=1024, lods=((1, 0.42), (2, 0.14)), thresholds=(0.0, 26.0, 75.0), ground=True),
    "cap": dict(name="lpg_canister_cap", mat="lpg_cap", size=1024, ao=512, lods=((1, 0.32),), thresholds=(0.0, 18.0), ground=False),
}
V = VARIANTS[VARIANT]
BLEND = os.path.join(WORK, f"{VARIANT}_build.blend")
AX = frame((0, 0, 0), (0, 1, 0))
THICK = 0.16


def R(a):
    return Vector((math.cos(a), 0.0, math.sin(a)))


def T(a):
    return Vector((-math.sin(a), 0.0, math.cos(a)))


def sweep(part, profile, segs, a0=0.0, a1=2 * math.pi, m=AX):
    """A closed (r, z) outline, counter-clockwise, swept round the axis from angle a0 to a1 (a is atan2(Z, X)): no end discs."""
    bm = part.bm
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    t0, t1 = -a1, -a0
    count = segs if full else segs + 1
    rings = []
    for k in range(count):
        t = t0 + (t1 - t0) * k / segs
        rings.append([bm.verts.new(m @ Vector((r * math.cos(t), r * math.sin(t), z))) for r, z in profile])
    n = len(profile)
    for k in range(segs):
        a, b = rings[k], rings[(k + 1) % count]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], b[i], b[j], a[j]))
    if not full:
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))


def head_points():
    """The dished end of the shell from the weld line to the pole, through the stations the leak code hard-codes."""
    ctrl = [(11.5, 6.3, 0), (13.5, 6.3, 0), (15.2, 5.9, 0), (16.4, 4.7, 0), (16.82, 3.5, 0), (16.97, 2.3, 0), (17.0, 0.0, 0)]
    out = []
    for p in spline(ctrl, 3):
        if p.x >= 13.5 - 1e-6:
            out.append((min(p.x, 17.0), min(max(p.y, 0.0), 6.3)))
    out[-1] = (17.0, 0.0)
    return out


HEAD = head_points()


def shell():
    profile = [(r, -y) for y, r in reversed(HEAD)] + [(r, y) for y, r in HEAD]
    lathe(add(Part(SHELL, 3, name="shell")), profile, 64, AX)
    for y in (-13.5, 13.5):
        weld_ring(6.3, frame((0, y, 0), (0, 1, 0)), 0.12, 56, lod=1)


def foot_ring(m=AX):
    # Stamped from one strip with four drain notches, welded to the end it stands on.
    for k in range(4):
        a0 = math.radians(45 + 90 * k + 6)
        a1 = math.radians(45 + 90 * (k + 1) - 6)
        sweep(add(Part(SHELL, 2, bevel=0.03, angle=40, name="foot ring")), [(5.0, -17.0), (5.3, -17.0), (5.3, -15.72), (5.0, -15.72)], 13, a0, a1, m)


def data_plate():
    a0, a1 = math.radians(122), math.radians(138)
    y0, y1 = -8.8, -5.4
    sweep(add(Part(PLATE, 2, bevel=0.012, angle=40, name="data plate")), [(6.28, y0), (6.345, y0), (6.345, y1), (6.28, y1)], 7, a0, a1)
    for a in (a0 + math.radians(1.6), a1 - math.radians(1.6)):
        for y in (y0 + 0.17, y1 - 0.17):
            axis = R(a)
            lathe(add(Part(PLATE, 0, name="rivet")), [(0.09, 0), (0.085, 0.03), (0.045, 0.05), (0, 0.055)], 8, frame(axis * 6.34 + Vector((0, y, 0)), axis))


def saddle(y):
    """A foot on the truck: base plate, two gussets, a curved flange, a rubber liner and the strap over the top."""
    box(add(Part(GUARD, 3, bevel=0.04, name="base plate")), (-6.5, y - 1.05, -6.7), (6.5, y + 1.05, -6.52))
    arc = lambda x: -math.sqrt(6.5**2 - x**2)
    for dy in (-0.72, 0.72):
        m = Matrix(((1, 0, 0, 0), (0, 0, -1, y + dy), (0, 1, 0, 0), (0, 0, 0, 1)))
        right = [(1.8, -6.52), (5.0, -6.52)] + [(x, arc(x)) for x in np.linspace(5.0, 1.8, 7)]
        left = [(-5.0, -6.52), (-1.8, -6.52)] + [(x, arc(x)) for x in np.linspace(-1.8, -5.0, 7)]
        for outline in (right, left):
            prism(add(Part(GUARD, 2, bevel=0.02, angle=50, name="gusset")), outline, -0.1, 0.1, m)
        side = 1 if dy > 0 else -1
        for x0, x1 in ((1.95, 4.9), (-4.9, -1.95)):
            weld_line((x0, y + dy + side * 0.13, -6.48), (x1, y + dy + side * 0.13, -6.48), 0.07, lod=0)
    a0, a1 = math.radians(-143), math.radians(-37)
    sweep(add(Part(GUARD, 3, bevel=0.03, angle=40, name="saddle flange")), [(6.34, y - 1.05), (6.52, y - 1.05), (6.52, y + 1.05), (6.34, y + 1.05)], 14, a0, a1)
    sweep(add(Part(RUBBER, 2, bevel=0.0, name="liner")), [(6.27, y - 0.76), (6.34, y - 0.76), (6.34, y + 0.76), (6.27, y + 0.76)], 32)
    sweep(add(Part(GUARD, 3, bevel=0.025, angle=40, name="strap")), [(6.34, y - 0.55), (6.44, y - 0.55), (6.44, y + 0.55), (6.34, y + 0.55)], 28, math.radians(-30), math.radians(210))
    # The T-bolt that closes the strap on each side: a tab on the strap, a lug on the flange, a bolt through both.
    for mid, sign in ((math.radians(-33.5), 1), (math.radians(-146.5), -1)):
        radial, along = R(mid), T(mid) * sign
        centre = radial * 6.42 + Vector((0, y, 0))
        for d in (-0.42, 0.42):
            tab = frame(centre + along * d, along, radial)
            box(add(Part(GUARD, 2, bevel=0.025, angle=40, name="tab")), (-0.08, -0.55, -0.09), (1.05, 0.55, 0.09), tab)
        shaft = centre + radial * 0.62
        lathe(add(Part(ZINC, 1, name="t bolt")), [(0, -0.95), (0.14, -0.95), (0.14, 0.95), (0, 0.95)], 8, frame(shaft, along))
        hex_bolt(shaft + along * 0.51, along, 0.46, lod=1, washer=True)
        hex_bolt(shaft - along * 0.51, -along, 0.46, lod=0, washer=True)
    for x in (-5.9, 5.9):
        hex_bolt((x, y, -6.52), (0, 0, 1), 0.62, lod=1, stud=0.1)


def guard():
    """The hoop that takes the knocks instead of the valve, on four flat legs welded to the head."""
    tube(add(Part(SHELL, 3, name="guard hoop")), ring_path(4.6, 48, frame((0, 18.72, 0), (0, 1, 0))), 0.3, 10, closed=True)
    outline = [(0, -0.92), (0.45, -0.92), (1.05, -0.6), (2.52, -0.6), (2.52, 0.6), (1.05, 0.6), (0.45, 0.92), (0, 0.92)]
    for k in range(4):
        a = math.radians(45 + 90 * k)
        radial = R(a)
        foot = radial * 4.6 + Vector((0, 16.1, 0))
        m = frame(foot, radial, (0, 1, 0))
        prism(add(Part(SHELL, 3, bevel=0.035, angle=40, name="guard leg")), outline, -0.11, 0.11, m)
        for r, z in ((4.74, 16.34), (4.47, 16.56)):
            at = radial * r + Vector((0, z, 0))
            weld_line(at - T(a) * 0.88, at + T(a) * 0.88, 0.08, lod=1, count=5)
        for side in (-1, 1):
            at = radial * 4.6 + T(a) * side * 0.62 + Vector((0, 18.2, 0))
            weld_line(at - Vector((0, 0.45, 0)), at + Vector((0, 0.42, 0)), 0.06, lod=0, count=3)


def valves():
    # The boss welded to the crown.
    lathe(add(Part(SHELL, 3, bevel=0.03, angle=30, name="boss")), [(1.62, 16.8), (1.62, 17.16), (1.42, 17.28), (1.2, 17.3)], 24, AX)
    weld_ring(1.62, frame((0, 16.98, 0), (0, 1, 0)), 0.085, 28, lod=1)
    # The service valve's forged body, its wrench flats, the handwheel on top and the outlet.
    lathe(
        add(Part(BRASS, 3, bevel=0.012, angle=30, name="valve body")),
        [(0.88, 17.28), (0.88, 17.42), (0.86, 17.7), (0.8, 17.78), (0.8, 18.08), (0.92, 18.16), (0.92, 18.6), (0.7, 18.72), (0.5, 18.76)],
        20,
        AX,
    )
    lathe(add(Part(BRASS, 2, bevel=0.02, angle=40, name="flats")), [(1.13, 17.42), (1.13, 17.68)], 6, AX)
    bonnet = frame((0, 17.9, 0), (0, 0, 1))
    lathe(add(Part(BRASS, 3, bevel=0.012, angle=30, name="bonnet")), [(0.52, 0.5), (0.52, 1.04), (0.64, 1.1), (0.64, 1.42), (0.46, 1.5), (0.3, 1.52)], 14, bonnet)
    lathe(add(Part(BRASS, 2, bevel=0.018, angle=40, name="packing nut")), [(0.58, 1.48), (0.58, 1.72)], 6, bonnet)
    lathe(add(Part(ZINC, 2, name="stem")), [(0.15, 1.7), (0.15, 2.46), (0, 2.48)], 8, bonnet)
    # A handwheel lies flat over the stem, its rim scalloped for the fingers.
    rim = [Vector((0.9 * math.cos(2 * math.pi * k / 24), 17.9 + 0.9 * math.sin(2 * math.pi * k / 24), 2.22)) for k in range(24)]
    radii = [0.125 + 0.018 * math.cos(5 * 2 * math.pi * k / 24) for k in range(24)]
    tube(add(Part(RED, 3, name="handwheel rim")), rim, radii, 8, closed=True)
    lathe(add(Part(RED, 3, name="handwheel hub")), [(0.27, 2.08), (0.27, 2.32), (0.2, 2.36), (0, 2.37)], 12, frame((0, 17.9, 0), (0, 0, 1)))
    for k in range(5):
        t = 2 * math.pi * (k + 0.5) / 5
        d = Vector((math.cos(t), math.sin(t), 0))
        tube(add(Part(RED, 2, name="handwheel spoke")), [Vector((0, 17.9, 2.22)) + d * 0.2, Vector((0, 17.9, 2.22)) + d * 0.84], 0.075, 6, flatten=0.7)
    hex_bolt((0, 17.9, 2.37), (0, 0, 1), 0.28, lod=0, washer=False)

    lathe(add(Part(BRASS, 2, name="nipple")), [(0.5, 18.74), (0.5, 19.06)], 12, AX)
    lathe(add(Part(BRASS, 3, bevel=0.03, angle=40, name="union nut")), [(0.74, 19.04), (0.74, 19.4)], 6, AX)
    elbow = frame((0, 19.62, 0), (0, 0, -1))
    lathe(add(Part(BRASS, 3, bevel=0.0, name="elbow")), [(0, -0.4), (0.32, -0.36), (0.42, -0.18), (0.42, 0.42), (0.34, 0.56), (0.34, 0.66)], 12, elbow)
    lathe(add(Part(GALV, 3, name="ferrule")), [(0.3, 0.62), (0.37, 0.66), (0.37, 0.86), (0.335, 0.9), (0.335, 0.98), (0.37, 1.02), (0.37, 1.2), (0.335, 1.24), (0.335, 1.32), (0.37, 1.36), (0.37, 1.58), (0.28, 1.64)], 10, elbow)

    # The hose, down to the point the old one reached the truck.
    hose = spline([(0, 19.62, -1.5), (0.6, 19.68, -2.5), (2.5, 19.74, -4.0), (5.0, 18.0, -6.0), (8.2, 17.0, -10.8), (15.2, 15.0, -14.8)], 6)
    tube(add(Part(RUBBER, 3, name="hose")), hose, 0.24, 10)

    # The relief valve under its rubber rain cap, the bleed screw and the contents gauge.
    rel = frame((-1.9, 16.86, 0.6), (0, 1, 0))
    lathe(add(Part(BRASS, 2, bevel=0.012, angle=30, name="relief valve")), [(0.46, 0), (0.46, 0.46), (0.36, 0.54), (0.36, 0.86)], 12, rel)
    lathe(add(Part(RUBBER, 2, name="rain cap")), [(0.48, 0.8), (0.48, 1.22), (0.4, 1.34), (0.22, 1.42), (0, 1.44)], 14, rel)
    bleed = frame((1.86, 16.86, 0.8), (0, 1, 0))
    lathe(add(Part(BRASS, 2, bevel=0.01, angle=30, name="bleed")), [(0.34, 0), (0.34, 0.34), (0.22, 0.42), (0.22, 0.72), (0.3, 0.76), (0.3, 1.0), (0.2, 1.06), (0, 1.07)], 12, bleed)
    dial = frame((-0.2, 16.68, -2.6), (0, 1, 0))
    sweep(add(Part(GALV, 2, bevel=0.012, angle=40, name="gauge bezel")), [(0.72, 0.0), (0.94, 0.0), (0.94, 0.52), (0.86, 0.62), (0.76, 0.62), (0.72, 0.54)], 20, m=dial)
    lathe(add(Part(DIAL, 2, name="gauge dial")), [(0.72, 0.0), (0.72, 0.52), (0, 0.52)], 20, dial)


def shell_noise(seed, count=7, fy=(0.6, 2.2), fa=(1, 6)):
    r = np.random.default_rng(seed)
    terms = [(r.uniform(*fy) * r.choice((-1, 1)), int(r.integers(*fa)), r.uniform(0, 6.28), r.uniform(0.4, 1.0)) for _ in range(count)]
    total = sum(t[3] for t in terms)

    def f(y, a):
        return sum(w * math.sin(k * y + m * a + p) for k, m, p, w in terms) / total

    return f


def wiggle(seed, step, span=(-18.0, 18.0)):
    """Piecewise-straight noise along y, in -1..1: tears run in straight little runs, not sine waves."""
    r = np.random.default_rng(seed)
    xs = np.arange(span[0], span[1] + step, step)
    xs = xs + r.uniform(-0.3, 0.3, len(xs)) * step
    vs = r.uniform(-1, 1, len(xs))
    return lambda y: float(np.interp(y, xs, vs))


def ring_wiggle(seed, step, period=40.0):
    """The same round a rim, in inches, closing on itself."""
    r = np.random.default_rng(seed)
    xs = np.arange(0.0, period, step)
    xs = xs + r.uniform(-0.3, 0.3, len(xs)) * step
    vs = r.uniform(-1, 1, len(xs))
    return lambda x: float(np.interp(x, xs, vs, period=period))


def face(bm, vs):
    out = []
    for v in vs:
        if not out or out[-1] is not v:
            out.append(v)
    while len(out) > 1 and out[0] is out[-1]:
        out.pop()
    if len(out) >= 3 and len(set(out)) == len(out):
        try:
            bm.faces.new(out)
        except ValueError:
            pass


def grid_solid(outer, inner, edge, O, I, closed):
    """Two surfaces of a torn sheet and the raw edge between them. Rows run +Y, columns by rising angle; the last row may be a pole."""
    N, count = O.shape[:2]
    M = count - 1
    pole = np.linalg.norm(O[-1, 0] - O[-1, 1]) < 1e-6

    def verts(part, G):
        rows = []
        for i in range(N):
            if pole and i == N - 1:
                rows.append([part.bm.verts.new(G[i, 0])] * count)
                continue
            row = [part.bm.verts.new(G[i, j]) for j in range(M + (0 if closed[i] else 1))]
            rows.append(row + [row[0]] if closed[i] else row)
        return rows

    a, b = verts(outer, O), verts(inner, I)
    for i in range(N - 1):
        for j in range(M):
            face(outer.bm, (a[i][j], a[i + 1][j], a[i + 1][j + 1], a[i][j + 1]))
            face(inner.bm, (b[i][j + 1], b[i + 1][j + 1], b[i + 1][j], b[i][j]))
    new = edge.bm.verts.new
    for i in range(N - 1):
        if closed[i] and closed[i + 1]:
            continue
        for j, flip in ((M, False), (0, True)):
            q = [new(O[i, j]), new(O[i + 1, j]), new(I[i + 1, j]), new(I[i, j])]
            face(edge.bm, q[::-1] if flip else q)
    for j in range(M):
        face(edge.bm, (new(O[0, j]), new(O[0, j + 1]), new(I[0, j + 1]), new(I[0, j])))


def kit_smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def torn_shell():
    """A fish-mouth split along the rear between the straps, its flaps peeled back with their length kept, and the foot end sheared off."""
    M = 56
    n0 = 6
    body = np.concatenate((np.linspace(-13.2, -9.6, 9, endpoint=False), np.linspace(-9.6, 9.2, 44, endpoint=False), np.linspace(9.2, 13.5, 4)))
    tip = HEAD[2::2] + ([HEAD[-1]] if (len(HEAD) - 3) % 2 else [])
    ys = list(body) + [y for y, _ in tip]
    rs = [6.3] * len(body) + [r for _, r in tip]
    N = len(ys)
    normals = []
    for i in range(N):
        if i < len(body):
            normals.append((0.0, 1.0))
            continue
        y0, r0 = ys[i - 1], rs[i - 1]
        y1, r1 = ys[min(i + 1, N - 1)], rs[min(i + 1, N - 1)]
        d = Vector((y1 - y0, r1 - r0))
        d.normalize()
        normals.append((-d.y, d.x))
    normals[-1] = (1.0, 0.0)

    centre, half = -0.3, 9.0
    tooth_p, tooth_m = wiggle(11, 0.62), wiggle(12, 0.62)
    lobe_p, lobe_m = wiggle(13, 2.6), wiggle(14, 2.6)
    length_p, length_m = wiggle(15, 3.1), wiggle(16, 3.1)
    bump = shell_noise(21)
    bump2 = shell_noise(22, fy=(2.0, 5.0), fa=(3, 14))
    rim = ring_wiggle(23, 1.0)
    rim2 = ring_wiggle(24, 4.0)
    # Where a flap split as it peeled: a tongue of metal either side, the tear running back between them.
    notches_p = ((-4.6, 0.3), (2.0, 0.24), (6.3, 0.3))
    notches_m = ((-2.8, 0.12), (4.0, 0.14))

    def notch(y, notches):
        return sum(depth * math.exp(-(((y - at) / 0.42) ** 2)) for at, depth in notches)

    O = np.zeros((N, M + 1, 3), np.float64)
    I = np.zeros((N, M + 1, 3), np.float64)
    closed = np.zeros(N, bool)
    th = THICK
    for i, (y, r) in enumerate(zip(ys, rs)):
        t = (y - centre) / half
        shape = max(0.0, 1.0 - t * t) ** 0.72
        phi_p = phi_m = hinge_p = hinge_m = 0.0
        if shape > 0.04:
            taper = min(1.0, shape * 3.0)
            # Wider above than below: the lower flap can't fold through the truck under it.
            hinge_p = 1.25 * shape * (1.0 + 0.18 * lobe_p(y))
            hinge_m = 0.55 * shape * (1.0 + 0.18 * lobe_m(y))
            phi_p = max(hinge_p + (0.09 * tooth_p(y) + notch(y, notches_p)) * taper, 0.015)
            phi_m = max(hinge_m + (0.07 * tooth_m(y) + notch(y, notches_m)) * taper, 0.015)
        closed[i] = phi_p == 0.0 and phi_m == 0.0
        ny, nr = normals[i]
        A_p, A_m = math.pi - phi_p, math.pi - phi_m
        for j in range(M + 1):
            x = 2.0 * j / M - 1.0
            g = 0.4 * x + 0.6 * math.sin(x * math.pi / 2)
            a = g * (A_p if g >= 0 else A_m)
            yy = y
            if i < n0:
                # The sheared end. It's a rim that wanders about the old weld line.
                inches = (a + math.pi) * 6.3662
                edge_y = -12.3 + 0.45 * rim(inches) + 1.1 * rim2(inches)
                edge_y = min(max(edge_y, -13.4), -11.1)
                yy = edge_y + (ys[n0] - edge_y) * i / n0
            side = 1.0 if a >= 0 else -1.0
            A = A_p if a >= 0 else A_m
            phi = phi_p if a >= 0 else phi_m
            length = ((3.0 if a >= 0 else 1.9) * shape**0.55 * (1 + 0.3 * (length_p if a >= 0 else length_m)(y))) if phi > 0 else 0.0
            # The hinge follows the opening's broad shape, not its teeth: the sheet is whole, only its edge is torn.
            bend_at = math.pi - (hinge_p if a >= 0 else hinge_m) - length / 6.3
            near = math.exp(-max(A - abs(a), 0.0) * 6.3 / 2.6) if phi > 0 else 0.0
            flare = math.exp(-max(yy + 13.2, 0.0) / 1.9) * 0.34 if yy < -9 else 0.0
            ripple = 0.42 * near * bump(y, a) + 0.16 * near * bump2(y, a) + 0.05 * shape * (1 + math.cos(a)) * 0.5 + 0.09 * flare * (1 + bump2(y, a))
            rr = r + ripple + flare
            if phi > 0 and abs(a) > bend_at:
                # Past the hinge the sheet rolls outward about a centre beyond its outer face.
                rc = 2.55 * (1 + 0.2 * bump(y * 0.7, 0.3))
                l = (abs(a) - bend_at) * 6.3
                ab = bend_at * side
                c = R(ab) * (rr + rc)
                turned = ab - side * l / rc
                n = R(turned)
                p = c - n * rc
                q = c - n * (rc + th)
                # The tallest tongue is folded over rather than left standing above the old model's height.
                settle = max(p.z - 8.4, 0.0) * 0.5
                O[i, j] = (p.x, yy, p.z - settle)
                I[i, j] = (q.x, yy, q.z - settle)
            else:
                ca, sa = math.cos(a), math.sin(a)
                # The valve end's crown is a thick pad here, as the valve and guard are rooted in it and mustn't show inside.
                pad = 0.4 * kit_smooth(14.5, 15.6, y)
                wall = th + pad
                O[i, j] = (rr * ca, yy, rr * sa)
                I[i, j] = ((rr - wall * nr) * ca, yy - wall * ny, (rr - wall * nr) * sa)
    lips = []
    for i in range(N):
        if not closed[i]:
            lips.append(O[i, 0])
            lips.append(O[i, M])
    lips.extend(O[0, ::2])
    np.save(os.path.join(WORK, "lips.npy"), np.array(lips, np.float32))
    print("tear: rows", N, "open", int((~closed).sum()), "bounds", O.min((0, 1)).round(2), O.max((0, 1)).round(2), flush=True)
    grid_solid(add(Part(SHELL, 3, name="shell outer")), add(Part(SOOT, 3, name="shell inner")), add(Part(TORN, 3, name="torn edge")), O, I, closed)
    weld_ring(6.3, frame((0, 13.5, 0), (0, 1, 0)), 0.12, 56, lod=1)
    # The dip tube that drew liquid from the bottom, now in plain view through the hole.
    tube(add(Part(SOOT, 2, name="dip tube")), spline([(0, 16.7, 0), (0, 15.6, -0.4), (0, 12.5, -2.6), (0, 8.5, -5.3)], 4), 0.2, 8)


def torn_cap():
    """The foot-end head as it left the bottle: built at the valve end's position, then turned round and centred."""
    M = 60
    N = 11
    table = [(13.2, 6.3)] + HEAD
    s = [0.0]
    for (y0, r0), (y1, r1) in zip(table, table[1:]):
        s.append(s[-1] + math.hypot(y1 - y0, r1 - r0))
    s = np.array(s)
    ty, tr = np.array([p[0] for p in table]), np.array([p[1] for p in table])
    rim = ring_wiggle(31, 1.0)
    rim2 = ring_wiggle(32, 3.6)
    bump = shell_noise(33, fy=(0.8, 2.5), fa=(2, 8))
    O = np.zeros((N, M + 1, 3), np.float64)
    I = np.zeros((N, M + 1, 3), np.float64)
    for j in range(M + 1):
        a = -math.pi + 2 * math.pi * (j % M) / M
        u = (j % M) / M
        s_rim = 0.3 + 0.95 + 0.5 * rim(u * 40.0) + 0.6 * rim2(u * 40.0)
        s_rim = max(s_rim, 0.3)
        for i in range(N):
            f = i / (N - 1)
            ss = s_rim + (s[-1] - s_rim) * f
            y = float(np.interp(ss, s, ty))
            r = float(np.interp(ss, s, tr))
            near = (1 - f) ** 2
            rr = r - 0.22 * near * (1 + bump(y, a))
            d = 0.05
            y2 = float(np.interp(ss + d, s, ty))
            r2 = float(np.interp(ss + d, s, tr))
            dv = Vector((y2 - y, r2 - r))
            dv.normalize()
            ny, nr = -dv.y, dv.x
            if i == N - 1:
                ny, nr, rr = 1.0, 0.0, 0.0
            ca, sa = math.cos(a), math.sin(a)
            # Turned half round about Z and moved so the head's centre is the model's: y = -Y + 15.25.
            O[i, j] = (-rr * ca, 15.25 - y, rr * sa)
            I[i, j] = (-(rr - THICK * nr) * ca, 15.25 - (y - THICK * ny), (rr - THICK * nr) * sa)
    closed = np.ones(N, bool)
    grid_solid(add(Part(SHELL, 3, name="cap outer")), add(Part(SOOT, 3, name="cap inner")), add(Part(TORN, 3, name="cap edge")), O, I, closed)
    foot_ring(Matrix.Translation((0, 15.25, 0)) @ AX)
    print("cap bounds", O.min((0, 1)).round(2), O.max((0, 1)).round(2), flush=True)


def geometry():
    if VARIANT == "cap":
        torn_cap()
        return
    if VARIANT == "intact":
        shell()
        foot_ring()
        data_plate()
    else:
        torn_shell()
    guard()
    valves()
    for y in (-10.0, 10.0):
        saddle(y)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "lpg_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, V["size"], 5)

    mesh = hw.data
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
    density = V["size"] * math.sqrt(uva / area3)
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
        drop = [f for f in bm.faces if lookup.get(round(f.loops[0][facts][1], 4)) is not None and lookup[round(f.loops[0][facts][1], 4)].lod < keep]
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

    for level, ratio in V["lods"]:
        lod(f"lpg_lod{level}", level, ratio)
    with open(os.path.join(WORK, f"{VARIANT}.json"), "w") as h:
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
    hw = bpy.data.objects["lpg_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    if V["ground"]:
        bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -6.72))
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 6.0
    with open(os.path.join(WORK, f"{VARIANT}_baked_uv_hash.txt"), "w") as h:
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

    size, ao = V["size"], V["ao"]
    bake_one(size, "EMIT", source("pos"), 1, f"bake_{VARIANT}_pos")
    bake_one(size, "EMIT", source("nor"), 1, f"bake_{VARIANT}_nor")
    bake_one(size, "EMIT", source("facts"), 1, f"bake_{VARIANT}_facts")
    bake_one(ao, "AO", None, 48, f"bake_{VARIANT}_ao")


def physics_of_old():
    old_doc = open(os.path.join(RETIRED, "lpg_canister.vmdl"), encoding="utf-8").read()
    start = old_doc.index('_class = "PhysicsShapeList"')
    start = old_doc.rindex("{", 0, start)
    end = old_doc.index("model_archetype")
    end = old_doc.rindex("]", 0, end)
    return old_doc[start:end].rstrip().replace("models/props/lowtide/lpg_canister_hulls_metal.obj", f"{MODEL}/lpg_canister_hulls_metal.obj")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["lpg_lod0"]) != open(os.path.join(WORK, f"{VARIANT}_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    name, mat = V["name"], V["mat"]
    counts = {}
    levels = [0] + [level for level, _ in V["lods"]]
    for lod in levels:
        ob = bpy.data.objects[f"lpg_lod{lod}"]
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
        with open(os.path.join(out, f"{name}_lod{lod}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/Lowtide/lpg_canister_v2/lpg.py\nmtllib {name}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {mat}\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, f"{name}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {mat}\nKd 1 1 1\nd 1\n")

    physics = ""
    if VARIANT == "intact":
        shutil.copyfile(os.path.join(RETIRED, "lpg_canister_hulls_metal.obj"), os.path.join(out, "lpg_canister_hulls_metal.obj"))
        physics = "\t\t\t" + physics_of_old() + "\n"
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/{name}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, V["thresholds"]))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Lowtide/lpg_canister_v2/lpg.py
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
							{{ from = "{mat}.vmat" to = "{MATS}/{mat}.vmat" }}
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
{physics}		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
"""
    with open(os.path.join(out, f"{name}.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Lowtide/lpg_canister_v2/lpg.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/{mat}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/{mat}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/{mat}_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/{mat}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/{mat}_rough.png"
}}
"""
    with open(os.path.join(mats, f"{mat}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("lpg stages done", flush=True)
