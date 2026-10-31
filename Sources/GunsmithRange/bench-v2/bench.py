"""The firing range's shooting bench v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python bench.py -- <work dir> <project root> <build|bake|export> ...

A range bench in place of a flat board on four square posts, on the same 170 x 30 footprint and the same 34 high top: a laminated oak top on
a welded steel frame of three trestles, aprons, a stretcher and diagonal braces, bolted down through foot plates. On it, what a firing point
collects: a ribbed rubber mat, two canvas rests, a steel tray and spent brass. Under it a slatted shelf with ammo cans and a spare bag, and
ear defenders on a hook. Its length is along Y, the shooter stands on -X and +X is downrange, standing on the ground about its origin. It goes
at world (-19, lane y, 0), yaw 0. Inches, engine axes (Z up).

One atlas, 4096 x 2048, so a stave's whole 170 inches fits at about 24 px/in. Islands get a share of it by what the player sees (`share`).
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

from build import Part, add, tube  # noqa: E402

FRAME, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE = kit.PAINT, kit.OXIDE, kit.ZINC, kit.BRASS, kit.RUBBER, kit.WELD, kit.PLATE
CARTON, OAK, MAT, CANVAS, OLIVE, ORANGE = 9, 11, 12, 13, 14, 15
FOLDER = "models/gunsmith_range/shooting_bench_v2"
OUT = os.path.join(ROOT, "Assets", "models", "gunsmith_range", "shooting_bench_v2")
BLEND = os.path.join(WORK, "bench_build.blend")
NAME = "bench"
W, H = 4096, 2048
POS_RANGE = 256.0  # The position bake spans this many inches.
HL, HD, TOP = 85.0, 15.0, 34.0
BOTTOM = 30.4
STAVES, GAP = 6, 0.025
STAVE = (2 * HD - (STAVES - 1) * GAP) / STAVES
TRESTLES = (-76.0, 0.0, 76.0)
LEG_X = 10.0
rng = np.random.default_rng(1919)
edge_lines = []
cans, plates, bags = [], [], []


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def tubing(lo, hi, lod=3, bevel=0.2, name="box section"):
    kit.box(piece(FRAME, lod, bevel=bevel, segs=2, angle=40, name=name), lo, hi)


def xz_plate(part, outline, y0, y1):
    """An outline in (x, z), extruded along y."""
    swap = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    kit.prism(part, outline, y0, y1, swap)


def laminated_top():
    for k in range(STAVES):
        x0 = -HD + k * (STAVE + GAP)
        grow = float(rng.uniform(-0.05, 0.03))
        drop = float(rng.uniform(0.0, 0.025))
        kit.box(piece(OAK, 3, bevel=0.07, segs=2, angle=40, name="stave"), (x0, -HL - grow, BOTTOM), (x0 + STAVE, HL + grow, TOP - drop))
    # The rods that tie the staves together, nutted on the outer staves.
    for y in (-72.0, -24.0, 24.0, 72.0):
        for side in (-1, 1):
            kit.hex_bolt((side * HD, y, 32.2), (side, 0, 0), size=0.72, lod=0, finish=ZINC)


def trestle(y):
    for x in (-LEG_X, LEG_X):
        tubing((x - 1.75, y - 1.75, 0.5), (x + 1.75, y + 1.75, 27.0), name="leg")
        kit.box(piece(FRAME, 2, bevel=0.06, angle=40, name="foot plate"), (x - 3.7, y - 3.7, 0.0), (x + 3.7, y + 3.7, 0.5))
        for dx in (-2.8, 2.8):
            for dy in (-2.8, 2.8):
                kit.hex_bolt((x + dx, y + dy, 0.5), (0, 0, 1), size=0.62, lod=0, finish=ZINC)
        for dy, (ax, bx) in ((-1.78, (x - 1.7, x + 1.7)), (1.78, (x - 1.7, x + 1.7))):
            kit.weld_line((ax, y + dy, 0.56), (bx, y + dy, 0.56), r=0.12, lod=0, count=5)
        for dx in (-1.78, 1.78):
            kit.weld_line((x + dx, y - 1.7, 0.56), (x + dx, y + 1.7, 0.56), r=0.12, lod=0, count=5)
        # A knee plate either side of the leg's head, inside the frame.
        out = 1 if x > 0 else -1
        knee = piece(FRAME, 1, bevel=0.03, angle=40, name="knee")
        xz_plate(knee, [(x - out * 1.7, 27.0), (x - out * 7.5, 27.0), (x - out * 1.7, 20.5)], y - 0.16, y + 0.16)
    tubing((-12.4, y - 1.0, 27.0), (12.4, y + 1.0, 30.2), name="cross rail")
    tubing((-LEG_X, y - 0.9, 9.0), (LEG_X, y + 0.9, 10.8), name="low rail")


def long_rails():
    for x0, x1 in ((-13.25, -10.75), (10.75, 13.25)):
        tubing((x0, -83.0, 26.6), (x1, 83.0, 30.2), name="apron")
    tubing((-1.25, -76.0, 10.8), (1.25, 76.0, 13.2), name="stretcher")
    # Diagonals, from low on the end trestles up to the aprons.
    for side in (-1, 1):
        for x in (-LEG_X, LEG_X):
            a = Vector((x, side * 74.2, 11.5))
            b = Vector((x, side * 31.0, 26.6))
            tube(piece(FRAME, 2, name="diagonal"), [a, b], 0.68, 8)
            kit.weld_line(a + Vector((0.72, side * -0.1, 0)), a + Vector((-0.72, side * -0.1, 0)), r=0.11, lod=0, count=4)
            kit.weld_line(b + Vector((0.72, 0, -0.1)), b + Vector((-0.72, 0, -0.1)), r=0.11, lod=0, count=4)
    for y in (-60.0, -30.0, 30.0, 60.0):
        kit.hex_bolt((-13.25, y, 28.4), (-1, 0, 0), size=0.58, lod=0, finish=ZINC)
        kit.hex_bolt((13.25, y, 28.4), (1, 0, 0), size=0.58, lod=0, finish=ZINC)


def shelf():
    """Slats on two angle rails, in the bay on the shooter's left."""
    for x0, x1 in ((-9.4, -7.6), (7.6, 9.4)):
        kit.box(piece(FRAME, 2, bevel=0.08, angle=40, name="shelf rail"), (x0, 1.0, 10.8), (x1, 75.0, 12.2))
    y = 2.6
    while y < 72.0:
        kit.box(piece(FRAME, 2, bevel=0.1, angle=40, name="slat"), (-9.8, y, 12.2), (9.8, y + 3.5, 12.65))
        y += 4.72


def ammo_can(x, y, z, text):
    hx, hy = 2.75, 5.5
    kit.box(piece(OLIVE, 2, bevel=0.07, angle=40, name="can"), (x - hx, y - hy, z), (x + hx, y + hy, z + 6.2))
    kit.box(piece(OLIVE, 2, bevel=0.1, segs=2, angle=40, name="lid"), (x - hx - 0.18, y - hy - 0.18, z + 6.2), (x + hx + 0.18, y + hy + 0.18, z + 7.4))
    for dy in (-3.6, 3.6):
        kit.box(piece(OLIVE, 1, bevel=0.04, angle=40, name="rib"), (x - hx - 0.06, y + dy - 0.45, z + 0.3), (x + hx + 0.06, y + dy + 0.45, z + 5.9))
    kit.box(piece(OXIDE, 1, bevel=0.03, angle=40, name="latch"), (x - 1.0, y + hy + 0.16, z + 4.7), (x + 1.0, y + hy + 0.42, z + 7.0))
    tube(piece(OXIDE, 1, name="handle"), [(x, y - 3.2, z + 7.4), (x, y - 2.9, z + 8.0), (x, y + 2.9, z + 8.0), (x, y + 3.2, z + 7.4)], 0.14, 6)
    cans.append(dict(x=x, y=y, z=z, hx=hx, hy=hy, text=text))


def pillow(cx, cy, z0, lx, ly, h, dent=0.0, lod=2, rows=14, cols=30):
    """A filled canvas bag: two panels sewn at a piped seam low on its side, sat flat, with a little sag and, for a rest, a dent to lay a gun in."""
    part = piece(CANVAS, lod, name="bag")
    bm = part.bm
    phase = rng.uniform(0.0, 6.28, 4)
    low, high = 0.2 * h, 0.8 * h

    def signed(v, e):
        return math.copysign(abs(v) ** e, v)

    def point(phi, theta):
        cp, sp = math.cos(phi), math.sin(phi)
        wave = 1.0 + 0.022 * math.sin(theta * 3 + phase[2]) + 0.016 * math.sin(theta * 7 + phase[3])
        px = lx / 2 * signed(cp, 0.62) * signed(math.cos(theta), 0.42) * wave
        py = ly / 2 * signed(cp, 0.62) * signed(math.sin(theta), 0.42) * wave
        pz = high * abs(sp) ** 0.82 if sp > 0 else -low * abs(sp) ** 0.7
        up = max(pz / high, 0.0)
        along = py / (ly / 2)
        pz -= dent * math.exp(-(along * 1.9) ** 2) * math.exp(-(px / (lx / 2) * 1.4) ** 2) * up
        pz += 0.05 * h * math.sin(px * 0.9 + phase[0]) * math.cos(py * 0.55 + phase[1]) * up
        return Vector((cx + px, cy + py, z0 + low + pz))

    rings = []
    for i in range(1, rows):
        phi = -math.pi / 2 + math.pi * i / rows
        rings.append([bm.verts.new(point(phi, 2 * math.pi * j / cols)) for j in range(cols)])
    south = bm.verts.new(point(-math.pi / 2 + 1e-4, 0.0))
    north = bm.verts.new(point(math.pi / 2 - 1e-4, 0.0))
    for a, b in zip(rings, rings[1:]):
        for j in range(cols):
            bm.faces.new((a[j], a[(j + 1) % cols], b[(j + 1) % cols], b[j]))
    for j in range(cols):
        bm.faces.new((south, rings[0][(j + 1) % cols], rings[0][j]))
        bm.faces.new((north, rings[-1][j], rings[-1][(j + 1) % cols]))
    tube(piece(CANVAS, max(lod - 1, 0), name="piping"), [point(0.0, 2 * math.pi * j / 60) for j in range(60)], 0.13, 5, closed=True)
    bags.append(dict(x=cx, y=cy, z=z0 + low, lx=lx, ly=ly))


def casing(x, y, z, turn):
    """A spent 5.56 case lying on its side."""
    axis = (math.cos(turn), math.sin(turn), 0.0)
    m = kit.frame((x, y, z + 0.185), axis)
    kit.lathe(
        piece(BRASS, 0, name="casing"),
        [(0, 0.0), (0.17, 0.0), (0.19, 0.03), (0.19, 0.07), (0.155, 0.1), (0.185, 0.15), (0.185, 1.22), (0.125, 1.4), (0.125, 1.75), (0.08, 1.75), (0.08, 1.6), (0, 1.6)],
        8,
        m,
    )


def magazine(x0, y0, z0):
    """A curved rifle magazine lying on its side, long along X."""
    count = 8
    low = [(7.0 * k / count, 0.32 * math.sin(math.pi * k / count)) for k in range(count + 1)]
    high = [(x, y + 2.3) for x, y in reversed(low)]
    shift = Matrix.Translation((x0, y0, 0))
    kit.prism(piece(OXIDE, 1, bevel=0.03, angle=40, name="magazine"), low + high, z0, z0 + 0.86, shift)
    inset = [(x * 0.82 + 0.6, y * 0.72 + 0.32) for x, y in low + high]
    kit.prism(piece(OXIDE, 0, bevel=0.015, angle=40, name="magazine rib"), inset, z0 + 0.86, z0 + 0.93, shift)
    kit.box(piece(OXIDE, 0, bevel=0.02, angle=40, name="floor plate"), (x0 - 0.22, y0 - 0.1, z0 - 0.03), (x0 + 0.04, y0 + 2.4, z0 + 0.89))


def on_the_top():
    kit.box(piece(MAT, 3, bevel=0.05, segs=1, angle=40, name="mat"), (-13.2, -28.0, TOP), (5.2, 28.0, TOP + 0.24))
    for x in (-12.2, 4.2):
        for y in (-27.0, 27.0):
            kit.hex_bolt((x, y, TOP + 0.24), (0, 0, 1), size=0.42, lod=0, finish=ZINC)
    pillow(8.8, 0.0, TOP, 7.4, 20.0, 4.3, dent=1.3)
    pillow(-8.2, 0.0, TOP + 0.24, 5.8, 10.5, 2.9, dent=0.45)

    # A steel tray of three bays, bolted down.
    x0, x1, y0, y1 = -11.0, -0.5, -55.0, -37.0
    tray = dict(lod=1, bevel=0.022, angle=40, name="tray")
    kit.box(piece(OXIDE, **tray), (x0, y0, TOP), (x1, y1, TOP + 0.1))
    for lo, hi in (
        ((x0, y0, TOP), (x0 + 0.1, y1, TOP + 1.5)),
        ((x1 - 0.1, y0, TOP), (x1, y1, TOP + 1.5)),
        ((x0 + 0.1, y0, TOP), (x1 - 0.1, y0 + 0.1, TOP + 1.5)),
        ((x0 + 0.1, y1 - 0.1, TOP), (x1 - 0.1, y1, TOP + 1.5)),
        ((x0 + 0.1, -49.0, TOP), (x1 - 0.1, -48.9, TOP + 1.2)),
        ((x0 + 0.1, -43.0, TOP), (x1 - 0.1, -42.9, TOP + 1.2)),
    ):
        kit.box(piece(OXIDE, **tray), lo, hi)
    for _ in range(9):
        casing(float(rng.uniform(x0 + 0.8, x1 - 2.2)), float(rng.uniform(-54.4, -49.6)), TOP + 0.1, float(rng.uniform(0, 6.28)))

    # Two magazines and a carton in the other bays.
    for y in (-48.6, -45.85):
        magazine(-10.2, y, TOP + 0.1)
    kit.box(piece(CARTON, 1, bevel=0.035, angle=40, name="carton"), (-9.6, -41.6, TOP + 0.1), (-2.2, -38.4, TOP + 1.42))

    # Brass that nobody swept up.
    for x, y, turn in ((1.6, -19.0, 0.6), (-3.4, -22.5, 2.3), (-10.0, 17.5, 4.0), (2.8, 20.5, 1.2)):
        casing(x, y, TOP + 0.24, turn)
    for x, y, turn in ((10.9, -31.0, 1.0), (-5.5, 33.0, 5.1), (6.8, 38.0, 2.7), (12.6, 52.0, 0.2), (-12.0, -32.0, 3.3)):
        casing(x, y, TOP, turn)


def sign():
    y0, y1, z0, z1 = -15.0, 15.0, 26.9, 29.9
    kit.box(piece(PLATE, 2, bevel=0.02, angle=40, name="plate"), (-13.37, y0, z0), (-13.25, y1, z1))
    plates.append(dict(y0=y0, y1=y1, z0=z0, z1=z1))
    for y in (y0 + 0.6, y1 - 0.6):
        for z in (z0 + 0.45, z1 - 0.45):
            kit.hex_bolt((-13.37, y, z), (-1, 0, 0), size=0.26, lod=0, washer=False, finish=ZINC)


def ear_defenders(x, y):
    """Hung off a hook under the apron, in the safety orange the firing line is painted."""
    tube(piece(OXIDE, 1, name="hook"), kit.spline([(-13.25, y, 28.2), (x + 0.2, y, 28.2), (x - 0.25, y, 27.4), (x, y, 26.75)], 3), 0.11, 6)
    half = 3.05
    path = []
    for k in range(13):
        a = math.pi * k / 12
        path.append((x, y + half * math.cos(a), 22.9 + 3.75 * math.sin(a) ** 0.8))
    tube(piece(RUBBER, 1, name="headband"), path, 0.3, 8, flatten=0.42)
    for side in (-1, 1):
        at = (x, y + side * half, 21.4)
        kit.lathe(piece(ORANGE, 1, name="cup"), [(1.72, 0.0), (1.88, 0.35), (1.8, 0.95), (1.3, 1.42), (0.5, 1.56), (0, 1.56)], 16, kit.frame(at, (0, side, 0)))
        kit.lathe(piece(RUBBER, 1, name="cushion"), [(0, -0.72), (1.1, -0.72), (1.55, -0.66), (1.82, -0.32), (1.8, 0.0)], 16, kit.frame(at, (0, side, 0)))
        tube(piece(OXIDE, 0, name="yoke"), [(x, y + side * half, 23.2), (x, y + side * (half + 0.1), 22.6)], 0.14, 6)


def geometry():
    laminated_top()
    for y in TRESTLES:
        trestle(y)
    long_rails()
    shelf()
    ammo_can(-2.8, 15.5, 12.65, ("5.56 MM", "840 CTG"))
    ammo_can(-2.6, 28.5, 12.65, ("9 MM", "1000 CTG"))
    pillow(0.0, 54.0, 12.65, 9.0, 16.0, 5.6)
    on_the_top()
    sign()
    ear_defenders(-14.6, 40.0)


def harden_all():
    seen = set()
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        # A round tube's facets aren't edges, and it isn't worn along them.
        if p.finish in (OAK, FRAME, OXIDE, PLATE, OLIVE, CARTON) and p.name not in ("diagonal", "hook", "handle", "yoke"):
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.25))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        # A part is looked up by this at four digits when the LODs are cut, so no two can share one.
        while True:
            p.rand = float(kit.rng.uniform(0, 1))
            if round(p.rand, 4) not in seen:
                seen.add(round(p.rand, 4))
                break


def share(finish, normal, centre):
    """How much texture an island gets, against a stave's top at 1."""
    if finish == OAK:
        if normal.z > 0.7:
            return 1.0
        if normal.z < -0.7:
            return 0.22
        if abs(normal.y) > 0.7:
            return 0.8
        return 0.8 if abs(centre.x) > HD - 0.5 else 0.1
    if finish == MAT:
        return 1.0 if normal.z > 0.5 else 0.06
    if finish == FRAME:
        return 0.55
    if finish in (PLATE, OLIVE, CARTON):
        return 0.9
    if finish in (OXIDE, ORANGE, BRASS):
        return 0.75
    if finish == CANVAS:
        return 0.9
    return 0.45


def pack(mesh, pad_px=5):
    """The toolkit's real-scale shelf packing, for a wide atlas and with a share of it for each island, which is kept in the facts' third channel."""
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
    for w, h, n, centre, scale, rot, low, weight in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px) * density / W, (q[1] + py) * density / H)
                l[facts][2] = weight
    bm.to_mesh(mesh)
    bm.free()
    print("islands", len(rects), "density px/in %.1f" % density, flush=True)
    return density


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "bench_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    density = pack(hw.data, 5)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def lod(number, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = f"bench_lod{number}"
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
    np.save(os.path.join(WORK, "bench_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "bench.json"), "w") as h:
        json.dump(dict(density=density, range=POS_RANGE, half_length=HL, half_depth=HD, top=TOP, bottom=BOTTOM, staves=STAVES, stave=STAVE, gap=GAP, cans=cans, plates=plates, bags=bags), h)
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
    hw = bpy.data.objects["bench_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 8.0
    with open(os.path.join(WORK, "bench_baked_uv_hash.txt"), "w") as h:
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

    bake_one(W, H, "EMIT", source("pos"), 1, "bake_rb_pos")
    bake_one(W, H, "EMIT", source("nor"), 1, "bake_rb_nor")
    bake_one(W, H, "EMIT", source("facts"), 1, "bake_rb_facts")
    bake_one(W // 2, H // 2, "AO", None, 32, "bake_rb_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["bench_lod0"]) != open(os.path.join(WORK, "bench_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"bench_lod{number}"]
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
            h.write(f"# Generated by Sources/GunsmithRange/bench-v2/bench.py\nmtllib {NAME}.mtl\n")
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
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 80.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/GunsmithRange/bench-v2/bench.py
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
    vmat = f"""// Generated by Sources/GunsmithRange/bench-v2/bench.py

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
print("bench stages done", flush=True)
