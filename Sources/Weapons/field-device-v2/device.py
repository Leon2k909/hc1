"""Field device v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python device.py -- <work dir> <project root> <build|bake|export> ...

The old device's layout, rebuilt: a moulded rubber tray, three padded canvas pouches pulled down by two webbing bands with
cam buckles, a cast housing and a control plate with a recessed keypad and a window. It's a fictional sealed game prop: no
ports, no wiring, nothing that opens. Same origin, axes and bounds as the old model, and every key within 0.03 of where it was.
Inches, engine axes, Z up. The plate reads with +X up the page and -Y to the right, as the old atlas did.
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

from build import Part, add, box, frame, lathe, prism, tube  # noqa: E402

CANVAS, BINDING, WEB, RUBBER, KEY, HOUSING, PLATE, STEEL, GLASS, GASKET, LABEL = range(11)
# These get more of the atlas: the plate is what the player looks at.
HIGH_DENSITY = (KEY, PLATE, GLASS, LABEL)
DENSITY_BOOST = 1.7
MODEL = "weapons/c4/field_device_v2"
BLEND = os.path.join(WORK, "device_build.blend")
BAND_X = 5.2
BAND_W = 1.0
KEY_X = [0.919 - 1.189 * i for i in range(4)]
KEY_Y = [1.335, 0.0, -1.335]
LAMP = (3.74, -2.92)
POUCHES = (-3.65, 0.0, 3.65)


def outline(hx, hy, r, segs=6):
    """A rounded rectangle, counter-clockwise, with the same point count at any size."""
    pts = []
    for sx, sy, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(segs + 1):
            a = math.radians(start + 90 * k / segs)
            pts.append((sx * (hx - r) + r * math.cos(a), sy * (hy - r) + r * math.sin(a)))
    return pts


def stack(part, hx, hy, r, profile, at=(0, 0), segs=6):
    """Rings of a rounded rectangle up a profile of (inset, z), capped at both ends. Faces wind outward."""
    bm = part.bm
    rings = []
    for inset, z in profile:
        ring = outline(hx - inset, hy - inset, max(r - inset, 0.015), segs)
        rings.append([bm.verts.new((at[0] + x, at[1] + y, z)) for x, y in ring])
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def strap(part, path, width, thick, x=0.0, wobble=0.0):
    """A flat strip swept along a path in the YZ plane, width along X. The path runs toward +Y, so its outside is up."""
    bm = part.bm
    pts = [Vector((0, p[0], p[1])) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((0, -t.z, t.y))
        centre = x + wobble * math.sin(i * 0.9)
        rings.append(
            [
                bm.verts.new(Vector((centre - width / 2, p.y, p.z)) - up * (thick / 2)),
                bm.verts.new(Vector((centre + width / 2, p.y, p.z)) - up * (thick / 2)),
                bm.verts.new(Vector((centre + width / 2, p.y, p.z)) + up * (thick / 2)),
                bm.verts.new(Vector((centre - width / 2, p.y, p.z)) + up * (thick / 2)),
            ]
        )
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new((a[k], b[k], b[(k + 1) % 4], a[(k + 1) % 4]))
    bm.faces.new(tuple(rings[0]))
    bm.faces.new(tuple(reversed(rings[-1])))


def socket_screw(at, radius, finish=STEEL, axis=(0, 0, 1), lod=1):
    """A cap head with a real hexagon socket: every ring has 18 points, and the pit's lie on a hexagon."""
    m = frame(at, axis)
    part = add(Part(finish, lod, name="socket screw"))
    bm = part.bm
    hexagon, circle = [], []
    for k in range(18):
        a = 2 * math.pi * k / 18
        sector = (a + math.pi / 6) % (math.pi / 3) - math.pi / 6
        reach = math.cos(math.pi / 6) / math.cos(sector)
        hexagon.append((math.cos(a) * reach, math.sin(a) * reach))
        circle.append((math.cos(a), math.sin(a)))
    h = radius * 0.62
    pit = radius * 0.56
    profile = [(circle, radius, 0.0), (circle, radius, h - radius * 0.12), (circle, radius * 0.88, h), (hexagon, pit, h), (hexagon, pit, h - radius * 0.34)]
    rings = [[bm.verts.new(m @ Vector((x * r, y * r, z))) for x, y in shape] for shape, r, z in profile]
    for a, b in zip(rings, rings[1:]):
        for k in range(18):
            bm.faces.new((a[k], a[(k + 1) % 18], b[(k + 1) % 18], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def rivet(at, axis, radius=0.1, finish=STEEL, lod=0):
    lathe(add(Part(finish, lod, name="rivet")), [(radius, 0), (radius * 0.92, radius * 0.3), (radius * 0.5, radius * 0.56), (0, radius * 0.62)], 10, frame(at, axis))


def lump(x, y):
    """The soft unevenness of a filled pouch, always the same for one place."""
    return (
        0.05 * math.sin(x * 0.83 + y * 1.3 + 0.4)
        + 0.035 * math.sin(x * 1.9 - y * 2.1 + 1.7)
        + 0.022 * math.sin(x * 3.7 + y * 3.1 + 0.2)
        + 0.012 * math.sin(x * 7.1 - y * 5.3 + 2.6)
    )


def pinch(x):
    """How far a band pulls the top down at this x: 1 under a band, fading out over about half an inch."""
    d = abs(abs(x) - BAND_X) - BAND_W / 2
    t = min(max((d + 0.05) / 0.62, 0.0), 1.0)
    return 1 - t * t * (3 - 2 * t)


def pouch_lift(x, y, y0):
    """How far the top of a pouch sits from the old model's 2.9: a low dome, drawn down under the bands."""
    u = (x / 5.9) ** 2
    v = ((y - y0) / 1.75) ** 2
    return -0.04 + 0.12 * (1 - u * 0.6) * (1 - v) + lump(x, y) * 0.8 - 0.14 * pinch(x)


def pouch_point(q, y0, hx=5.9, hy=1.75, hz=1.25, r=0.42):
    """A point of the box lattice q (centred on the pouch) moved onto its padded shape. Returns where, and which way out."""
    inner = (hx - r, hy - r, hz - r)
    c = [max(-i, min(i, v)) for i, v in zip(inner, q)]
    d = Vector((q[0] - c[0], q[1] - c[1], q[2] - c[2]))
    n = d.normalized()
    p = Vector(c) + n * r
    t = (p.z + hz) / (2 * hz)
    up = t * t * (3 - 2 * t)
    bulge = 0.07 * math.sin(math.pi * t) * (1 - 0.7 * pinch(p.x)) + 0.5 * lump(p.x * 1.3 + p.z, y0 + p.z * 2.0)
    world = Vector((p.x + n.x * bulge, p.y + y0 + n.y * bulge, 0.4 + hz + p.z + up * pouch_lift(p.x, p.y + y0, y0)))
    return world, n


def lattice_lines(half, r, cell):
    """Lattice positions along one side: even in the flat, crowding where the shape turns so the turn stays round."""
    inner = half - r
    n = max(1, round(2 * inner / cell))
    mid = [-inner + 2 * inner * k / n for k in range(n + 1)]
    edge = [inner + r * math.tan(math.radians(a)) for a in (15, 30, 45)]
    return [-e for e in reversed(edge)] + mid + edge


def pouch(y0):
    part = add(Part(CANVAS, 3, name="pouch"))
    bm = part.bm
    hx, hy, hz = 5.9, 1.75, 1.25
    xs = lattice_lines(hx, 0.42, 0.4)
    ys = lattice_lines(hy, 0.42, 0.44)
    zs = lattice_lines(hz, 0.42, 0.42)
    nx, ny, nz = len(xs) - 1, len(ys) - 1, len(zs) - 1
    verts = {}

    def v(i, j, k):
        key = (i, j, k)
        if key not in verts:
            verts[key] = bm.verts.new(pouch_point((xs[i], ys[j], zs[k]), y0)[0])
        return verts[key]

    for i in range(nx):
        for j in range(ny):
            bm.faces.new((v(i, j, nz), v(i + 1, j, nz), v(i + 1, j + 1, nz), v(i, j + 1, nz)))
            bm.faces.new((v(i, j + 1, 0), v(i + 1, j + 1, 0), v(i + 1, j, 0), v(i, j, 0)))
    for i in range(nx):
        for k in range(nz):
            bm.faces.new((v(i, 0, k), v(i + 1, 0, k), v(i + 1, 0, k + 1), v(i, 0, k + 1)))
            bm.faces.new((v(i, ny, k + 1), v(i + 1, ny, k + 1), v(i + 1, ny, k), v(i, ny, k)))
    for j in range(ny):
        for k in range(nz):
            bm.faces.new((v(0, j, k + 1), v(0, j + 1, k + 1), v(0, j + 1, k), v(0, j, k)))
            bm.faces.new((v(nx, j, k), v(nx, j + 1, k), v(nx, j + 1, k + 1), v(nx, j, k + 1)))

    # The sewn binding round the top seam, following the shape it's sewn to.
    ring = [(x, -hy) for x in xs[:-1]] + [(hx, y) for y in ys[:-1]] + [(x, hy) for x in reversed(xs[1:])] + [(-hx, y) for y in reversed(ys[1:])]
    path = []
    for x, y in ring:
        p, n = pouch_point((x, y, hz), y0)
        path.append(p + n * 0.012)
    tube(add(Part(BINDING, 0, name="binding")), path, 0.052, 5, closed=True, flatten=0.8)


def tray():
    # The dish: a lip around a floor the pouches sit in.
    stack(
        add(Part(RUBBER, 3, bevel=0.05, segs=2, angle=38, name="tray")),
        6.1,
        5.6,
        0.62,
        [(0.03, 0.0), (0.0, 0.06), (0.0, 0.66), (0.22, 0.7), (0.3, 0.42)],
    )
    # Moulded corner bumpers, which set the old model's outer size along X.
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        part = add(Part(RUBBER, 3, bevel=0.05, segs=2, angle=38, name="bumper"))
        stack(part, 0.84, 0.84, 0.46, [(0.04, 0.0), (0.0, 0.08), (0.0, 0.82), (0.18, 1.02)], at=(sx * (6.2 - 0.84), sy * (5.64 - 0.84)))
    # Grip ribs moulded along the walls, stopping short of the bumpers.
    for y in np.arange(-3.7, 3.71, 0.74):
        for sx in (-1, 1):
            lo, hi = sorted((sx * 6.03, sx * 6.14))
            box(add(Part(RUBBER, 1, bevel=0.018, angle=38, name="rib")), (lo, y - 0.13, 0.12), (hi, y + 0.13, 0.6))
    for x in np.arange(-4.07, 4.08, 0.74):
        for sy in (-1, 1):
            lo, hi = sorted((sy * 5.53, sy * 5.64))
            box(add(Part(RUBBER, 1, bevel=0.018, angle=38, name="rib")), (x - 0.13, lo, 0.12), (x + 0.13, hi, 0.6))


def band_z(x, y):
    """Height of the middle of a band: over the pouch tops, bridging the gaps, with a slight sag over each gap."""
    y0 = min(POUCHES, key=lambda c: abs(c - y))
    gap = math.exp(-(((abs(y) - 1.825) / 0.3) ** 2))
    return 2.9 + pouch_lift(x, y, y0) * (1 - 0.5 * gap) + 0.075


def bands():
    for sx in (-1, 1):
        x = sx * BAND_X
        path = [(-5.62, 0.62), (-5.61, 0.95), (-5.6, 1.4), (-5.59, 1.9), (-5.57, 2.3), (-5.52, 2.55)]
        shoulder = band_z(x, -5.0)
        path += [(-5.42, shoulder - 0.2), (-5.26, shoulder - 0.06)]
        path += [(float(y), band_z(x, float(y))) for y in np.linspace(-5.0, 5.0, 26)]
        shoulder = band_z(x, 5.0)
        path += [(5.26, shoulder - 0.06), (5.42, shoulder - 0.2), (5.52, 2.55), (5.57, 2.3), (5.59, 1.9), (5.6, 1.4), (5.61, 0.95), (5.62, 0.62)]
        strap(add(Part(WEB, 3, bevel=0.012, segs=1, angle=55, name="band")), path, BAND_W, 0.07, x=x, wobble=0.01)

        # Two rivets through the bumper hold each end of the band in the tray.
        for sy in (-1, 1):
            for side in (-0.42, 0.42):
                rivet((x + side, sy * 5.645, 0.5), (0, sy, 0), 0.085, lod=1)

        # The cam buckle, where the old model had its metal block and rubber pad.
        cy = -4.5
        base = band_z(x, cy) + 0.04
        plate = add(Part(STEEL, 2, bevel=0.018, angle=40, name="buckle plate"))
        stack(plate, 0.725, 0.8, 0.12, [(0.0, base), (0.0, base + 0.06)], at=(x, cy), segs=3)
        for side in (-0.64, 0.64):
            box(add(Part(STEEL, 2, bevel=0.018, angle=40, name="buckle rail")), (x + side - 0.07, cy - 0.74, base + 0.05), (x + side + 0.07, cy + 0.74, base + 0.2))
        lathe(add(Part(STEEL, 1, name="buckle pin")), [(0, -0.74), (0.05, -0.74), (0.05, 0.74), (0, 0.74)], 8, frame((x, cy + 0.42, base + 0.15), (1, 0, 0)))
        # The cam, a rocker across the strap on the pin through the rails.
        cam = add(Part(STEEL, 2, bevel=0.03, segs=2, angle=38, name="cam"))
        profile = [(cy + 0.58, base + 0.08), (cy + 0.58, base + 0.2), (cy + 0.34, base + 0.27), (cy - 0.5, base + 0.2), (cy - 0.66, base + 0.13), (cy - 0.62, base + 0.09)]
        side_on = Matrix(((0, 0, 1, x), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
        prism(cam, profile, -0.54, 0.54, side_on)
        pad = add(Part(GASKET, 2, bevel=0.022, segs=1, angle=38, name="cam pad"))
        stack(pad, 0.34, 0.45, 0.09, [(0.0, base + 0.2), (0.0, base + 0.31), (0.05, base + 0.345)], at=(x, cy - 0.06), segs=3)
        for side in (-0.64, 0.64):
            for along in (-0.5, 0.5):
                rivet((x + side, cy + along, base + 0.2), (0, 0, 1), 0.06, lod=0)
        # The band's free end comes out of the buckle and lies along it, held by an elastic keeper.
        tail = [(-3.95, base + 0.1), (-3.72, base + 0.06)] + [(y, band_z(x, y) + 0.06) for y in (-3.45, -3.2, -2.95, -2.7, -2.45)]
        strap(add(Part(WEB, 1, bevel=0.01, angle=55, name="tail")), tail, BAND_W * 0.94, 0.05, x=x)
        at = Matrix.Translation((x, -2.95, band_z(x, -2.95) + 0.03)) @ Matrix.Rotation(math.radians(90), 4, "X")
        prism(add(Part(GASKET, 1, bevel=0.012, angle=38, name="elastic keeper")), outline(0.56, 0.095, 0.05, 2), -0.17, 0.17, at)
    # Grab loops on the two outer pouches, sewn down at both ends.
    for sy in (-1, 1):
        y = sy * 4.62
        loop = [(float(t) * 1.65, 2.93 + 0.24 * (1 - float(t) ** 2) + 0.012 * math.sin(float(t) * 5.0)) for t in np.linspace(-1, 1, 15)]
        part = add(Part(WEB, 1, bevel=0.01, angle=55, name="grab loop"))
        strap(part, loop, 0.72, 0.055)
        part.bm.transform(Matrix(((0, 1, 0, 0), (-1, 0, 0, y), (0, 0, 1, 0), (0, 0, 0, 1))))


def housing():
    # Cast housing: a foot, a drafted body and a shoulder the plate sits on.
    stack(
        add(Part(HOUSING, 3, bevel=0.028, segs=2, angle=35, name="housing")),
        4.65,
        3.8,
        0.5,
        [(0.0, 2.725), (0.0, 2.92), (0.1, 2.98), (0.13, 3.62), (0.18, 3.7)],
    )
    # Cast ribs along the long sides.
    for sy in (-1, 1):
        lo, hi = sorted((sy * 3.6, sy * 3.75))
        for x in np.arange(-3.2, 3.21, 0.8):
            box(add(Part(HOUSING, 1, bevel=0.018, angle=35, name="cast rib")), (x - 0.09, lo, 2.92), (x + 0.09, hi, 3.48))
    # The short sides carry a plain raised pad each, and the operator's side has the data plate on its pad.
    for sx in (-1, 1):
        lo, hi = sorted((sx * 4.46, sx * 4.56))
        box(add(Part(HOUSING, 2, bevel=0.022, angle=35, name="side pad")), (lo, -2.5, 3.0), (hi, 2.5, 3.6))
    box(add(Part(LABEL, 2, bevel=0.008, angle=40, name="data plate")), (-4.585, -2.2, 3.06), (-4.555, 2.2, 3.54))
    for y in (-2.05, 2.05):
        for z in (3.15, 3.45):
            rivet((-4.585, y, z), (-1, 0, 0), 0.048, lod=0)
    # A soft gasket line between the casting and the plate.
    stack(add(Part(GASKET, 2, name="gasket")), 4.46, 3.63, 0.34, [(0.0, 3.68), (0.0, 3.735), (0.05, 3.75)])


def control_plate():
    """A plate with a real window recess and a real keypad well, cut from a grid so the walls stay clean."""
    part = add(Part(PLATE, 3, name="control plate"))
    bm = part.bm
    xs = [-4.45, -3.3, 1.57, 1.86, 3.12, 4.45]
    ys = [-3.625, -2.25, -2.05, 2.05, 2.25, 3.625]
    z0, z1 = 3.72, 3.92
    top = {(i, j): bm.verts.new((xs[i], ys[j], z1)) for i in range(6) for j in range(6)}
    faces = {}
    for i in range(5):
        for j in range(5):
            faces[(i, j)] = bm.faces.new((top[(i, j)], top[(i + 1, j)], top[(i + 1, j + 1)], top[(i, j + 1)]))
    ring = [(i, 0) for i in range(6)] + [(5, j) for j in range(1, 6)] + [(i, 5) for i in range(4, -1, -1)] + [(0, j) for j in range(4, 0, -1)]
    low = [bm.verts.new((xs[i], ys[j], z0)) for i, j in ring]
    high = [top[k] for k in ring]
    n = len(ring)
    for k in range(n):
        bm.faces.new((low[k], low[(k + 1) % n], high[(k + 1) % n], high[k]))
    bm.faces.new(list(reversed(low)))
    # The keypad well and the window, sunk.
    for chosen in ([faces[(1, 2)]], [faces[(3, j)] for j in (1, 2, 3)]):
        made = bmesh.ops.extrude_face_region(bm, geom=chosen)
        for v in made["geom"]:
            if isinstance(v, bmesh.types.BMVert):
                v.co.z = 3.8
        # The extrude leaves the faces it started from, which would be a lid over the well.
        bmesh.ops.delete(bm, geom=chosen, context="FACES_ONLY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Round the outer corners, and let harden soften every other hard edge.
    bm.normal_update()
    corners = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1 and all(abs(abs(v.co.x) - 4.45) < 1e-4 and abs(abs(v.co.y) - 3.625) < 1e-4 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=corners, offset=0.3, segments=5, profile=0.5, affect="EDGES", clamp_overlap=False)
    part.bevel, part.segs, part.angle = 0.022, 2, 40

    # Glass and its rubber seat, down in the window.
    stack(add(Part(GASKET, 2, name="window seat")), 0.63, 2.25, 0.04, [(0.0, 3.8), (0.0, 3.86), (0.07, 3.86), (0.07, 3.83)], at=(2.49, 0.0), segs=2)
    box(add(Part(GLASS, 3, bevel=0.012, angle=40, name="window")), (2.49 - 0.57, -2.19, 3.8), (2.49 + 0.57, 2.19, 3.845))
    # Raised guards beside the keypad, so nothing leans on the keys.
    for sy in (-1, 1):
        lo, hi = sorted((sy * 2.47, sy * 2.72))
        box(add(Part(PLATE, 2, bevel=0.022, segs=2, angle=40, name="key guard")), (-3.2, lo, 3.9), (1.4, hi, 4.0))
    # Keys, at the old keys' centres and sizes. Their tops are the old model's 4.17.
    for x in KEY_X:
        for y in KEY_Y:
            stack(
                add(Part(KEY, 2, name="key")),
                0.455,
                0.51,
                0.16,
                [(-0.04, 3.8), (-0.04, 3.845), (0.0, 3.87), (0.018, 4.08), (0.06, 4.145), (0.12, 4.17), (0.2, 4.158), (0.3, 4.152)],
                at=(x, y),
                segs=3,
            )
    # Plate screws, where the old fasteners were.
    for x in (-4.13, 4.13):
        for y in (-3.28, 3.28):
            socket_screw((x, y, 3.92), 0.2, lod=2)
    # The status lamp, in a small bezel.
    place = Matrix.Translation((LAMP[0], LAMP[1], 0))
    lathe(add(Part(STEEL, 1, name="lamp bezel")), [(0.17, 3.92), (0.17, 3.955), (0.13, 3.975), (0.105, 3.965), (0.105, 3.95)], 16, place)
    lathe(add(Part(GLASS, 1, name="lamp")), [(0.105, 3.95), (0.1, 3.975), (0.06, 3.995), (0, 4.0)], 12, place)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    tray()
    for y0 in POUCHES:
        pouch(y0)
    bands()
    housing()
    control_plate()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    dev = kit.join_parts(kit.parts, "fd_lod0")
    dev.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = dev
    dev.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    dev.select_set(False)

    mesh = dev.data
    polys = len(mesh.polygons)
    facts = np.empty(len(mesh.loops) * 4, np.float32)
    mesh.color_attributes["facts"].data.foreach_get("color", facts)
    facts = facts.reshape(-1, 4)
    loop_finish = np.rint(facts[:, 0] * 16).astype(np.int32)
    loop_start = np.empty(polys, np.int32)
    mesh.polygons.foreach_get("loop_start", loop_start)
    finish = loop_finish[loop_start]
    centre = np.empty(polys * 3)
    mesh.polygons.foreach_get("center", centre)
    centre = centre.reshape(-1, 3)
    normal = np.empty(polys * 3)
    mesh.polygons.foreach_get("normal", normal)
    normal = normal.reshape(-1, 3)
    # Faces no one can see stay for the closed shells, but take no atlas: undersides, the tray floor, the lid under the
    # plate and whatever canvas is under the housing. They share a few texels in the atlas's corner, and later LODs drop them.
    under_housing = (np.abs(centre[:, 0]) < 4.35) & (np.abs(centre[:, 1]) < 3.55)
    hidden = (
        (normal[:, 2] < -0.7)
        | ((finish == RUBBER) & (normal[:, 2] > 0.7) & (centre[:, 2] < 0.5))
        | ((finish == HOUSING) & (normal[:, 2] > 0.7) & (centre[:, 2] > 3.6))
        | ((finish == GASKET) & (normal[:, 2] > 0.7) & (np.abs(centre[:, 2] - 3.75) < 0.01))
        | (np.isin(finish, (CANVAS, BINDING)) & under_housing)
    )
    print("hidden faces", int(hidden.sum()), "of", polys, flush=True)

    # The plate, keys and window get more of the atlas: packed from a copy with those parts blown up, since pack_real_scale
    # lays out every island by its size in 3D. The copy has no hidden faces. Its UVs are copied back face by face.
    swollen = mesh.copy()
    co = np.empty(len(mesh.vertices) * 3)
    swollen.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    loop_vert = np.empty(len(mesh.loops), np.int32)
    swollen.loops.foreach_get("vertex_index", loop_vert)
    co[np.unique(loop_vert[np.isin(loop_finish, HIGH_DENSITY)])] *= DENSITY_BOOST
    swollen.vertices.foreach_set("co", co.ravel())
    origin = swollen.attributes.new("origin", "INT", "FACE")
    origin.data.foreach_set("value", np.arange(polys, dtype=np.int32))
    swollen.update()
    bm = bmesh.new()
    bm.from_mesh(swollen)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.flatnonzero(hidden)], context="FACES_ONLY")
    bm.to_mesh(swollen)
    bm.free()
    kit.pack_real_scale(swollen, 2048, 3)
    kept = np.empty(len(swollen.polygons), np.int32)
    swollen.attributes["origin"].data.foreach_get("value", kept)
    packed = np.empty(len(swollen.loops) * 2, np.float32)
    swollen.uv_layers["UVMap"].data.foreach_get("uv", packed)
    # An 8-texel margin along two sides keeps the corner free for the hidden faces.
    packed = packed.reshape(-1, 2) * (1 - 8 / 2048) + 8 / 2048
    uv = np.empty((len(mesh.loops), 2), np.float32)
    corner = 1.5 / 2048
    for k in np.flatnonzero(hidden):
        start = loop_start[k]
        uv[start : start + 3] = ((corner, corner), (corner * 2, corner), (corner, corner * 2))
    for poly, face in zip(swollen.polygons, kept):
        start = loop_start[face]
        uv[start : start + poly.loop_total] = packed[poly.loop_start : poly.loop_start + poly.loop_total]
    mesh.uv_layers["UVMap"].data.foreach_set("uv", uv.ravel())
    bpy.data.meshes.remove(swollen)
    # Facts' blue says a face is hidden, for the LODs.
    for k in np.flatnonzero(hidden):
        facts[loop_start[k] : loop_start[k] + 3, 2] = 1.0
    mesh.color_attributes["facts"].data.foreach_set("color", facts.ravel())

    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mesh.calc_loop_triangles()
    area3 = uva = 0.0
    for tri in mesh.loop_triangles:
        if hidden[tri.polygon_index] or loop_finish[tri.loops[0]] in HIGH_DENSITY:
            continue
        a, b, c = co[list(tri.vertices)]
        area3 += 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        p, q, r = uv[list(tri.loops)]
        uva += 0.5 * abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]))
    density = 2048 * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "px/in %.1f, plate %.1f" % (density, density * DENSITY_BOOST), flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def lod(name, keep, ratio):
        copy = dev.copy()
        copy.data = dev.data.copy()
        copy.name = copy.data.name = name
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        layer = bm.loops.layers.float_color["facts"]
        drop = []
        for f in bm.faces:
            fact = f.loops[0][layer]
            part = lookup.get(round(fact[1], 4))
            if fact[2] > 0.5 or (part is not None and part.lod < keep):
                drop.append(f)
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

    lod("fd_lod1", 1, 0.6)
    lod("fd_lod2", 2, 0.3)
    lod("fd_lod3", 3, 0.12)
    with open(os.path.join(WORK, "device.json"), "w") as h:
        json.dump(dict(density=density, boost=DENSITY_BOOST), h)
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
    dev = bpy.data.objects["fd_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not dev
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.01))
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 1.6
    with open(os.path.join(WORK, "baked_uv_hash.txt"), "w") as h:
        h.write(uv_hash(dev))

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
            scale = 1 / 40.0 if kind == "pos" else 0.5
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
        dev.data.materials.clear()
        dev.data.materials.append(mat)
        scene.cycles.samples = samples
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = dev
        dev.select_set(True)
        bpy.ops.object.bake(type=kind, margin=0, use_clear=True, target="IMAGE_TEXTURES")
        data = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(size, size, 4))
        print("baked", out, flush=True)

    bake_one(2048, "EMIT", source("pos"), 1, "bake_fd_pos")
    bake_one(2048, "EMIT", source("nor"), 1, "bake_fd_nor")
    bake_one(2048, "EMIT", source("facts"), 1, "bake_fd_facts")
    bake_one(1024, "AO", None, 48, "bake_fd_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", "Weapons", "C4", "field_device_v2")
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["fd_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2, 3):
        ob = bpy.data.objects[f"fd_lod{lod}"]
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
        with open(os.path.join(out, f"field_device_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Weapons/field-device-v2/device.py\nmtllib field_device.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl fd_device\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "field_device.mtl"), "w", newline="\n") as h:
        h.write("newmtl fd_device\nKd 1 1 1\nd 1\n")

    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/field_device_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 40.0, 120.0, 300.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Weapons/field-device-v2/device.py
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
							{{ from = "fd_device.vmat" to = "{MODEL}/fd_device.vmat" }}
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
    with open(os.path.join(out, "field_device.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Weapons/field-device-v2/device.py

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
	TextureAmbientOcclusion "{MODEL}/fd_device_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/fd_device_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MODEL}/fd_device_metal.png"

	//---- Normal ----
	TextureNormal "{MODEL}/fd_device_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/fd_device_rough.png"

	//---- Self Illum ----
	TextureSelfIllumMask "{MODEL}/fd_device_glow.png"
	g_flSelfIllumBrightness "1.6"
	g_flSelfIllumAlbedoFactor "1.0"
}}
"""
    with open(os.path.join(out, "fd_device.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("device stages done", flush=True)
