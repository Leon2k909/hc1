"""Cerro Blanco's cafe espresso machine v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python machine.py -- <work dir> <project root> <build|bake|export> ...

A two-group commercial espresso machine in place of a steel box with two chrome stubs. Brushed stainless side panels on chrome feet and a black base pan; the head over the work area with two
group heads, their portafilters locked in with black handles and double spouts; a steam wand at each end on a ball joint with a cool-touch sleeve and a lever above it; a hot water spout in the
middle; two pressure gauges and a keypad over each group; a drip tray with its grate; a cup warmer on top inside a chrome rail, cups upside down on it; and the water and drain hoses down into the
counter at the back. No maker's names.

Inches. +X is its working front, which faces the barista behind the counter; the customers see its back. Y runs across it and Z is up, with the origin on the counter top under its middle.
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

STEEL, POWDER, CAST, CHROME, BLACK, RUBBER, PORCELAIN, GAUGE = 0, 1, 2, 3, 4, 5, 6, 7  # POWDER and CAST aren't used: the shared stages look for them.
FOLDER = "models/maps/cerroblanco/espresso_machine_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "espresso_machine_v2")
BLEND = os.path.join(WORK, "machine_build.blend")
NAME = "machine"
W, H = 2048, 2048
POS_RANGE = 48.0  # The position bake spans this many inches, centred on the origin.

HALF_W = 14.0  # Half its width, to the side panels' outsides.
BACK_X, FRONT_X = -10.0, 6.5  # The body's back, and the work area's back wall under the head.
HEAD_X, HEAD_Z = 9.0, 12.0  # The head's front and its underside, where the groups hang.
BASE_Z, TOP_Z = 2.4, 19.2
GROUP_Y = 6.5
GROUP_X = 8.6
WAND_Y = 11.4
TRAY_X = 13.0
GAUGES = ((-2.3, 16.7), (2.3, 16.7))  # ( y, z ) of each gauge's middle on the head's front.
CUPS = [(-6.6, -9.0, "espresso"), (-4.2, -9.3, "espresso"), (-1.8, -9.0, "espresso"), (-6.4, -5.4, "espresso"), (-3.9, -5.6, "espresso"), (1.6, -6.2, "cappuccino"), (5.4, -6.4, "cappuccino")]
rng = np.random.default_rng(2651)
edge_lines = []
NO_EDGE = ("cup", "hose", "screw")


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def rounded(x0, x1, z0, z1, top, bottom, per=6):
    """A rectangle's outline in ( x, z ), its top corners rounded by top and its bottom ones by bottom, counter-clockwise."""
    out = []
    for cx, cz, r, a0 in ((x1 - bottom, z0 + bottom, bottom, -90), (x1 - top, z1 - top, top, 0), (x0 + top, z1 - top, top, 90), (x0 + bottom, z0 + bottom, bottom, 180)):
        for k in range(per + 1):
            a = math.radians(a0 + 90.0 * k / per)
            out.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return out


def side_frame(y):
    """Local ( x, y ) is world ( x, z ), and local +z runs toward -y, from world y."""
    return kit.frame((0, y, 0), (0, -1, 0), (1, 0, 0))


def body():
    # The side panels, stainless, their top corners rounded.
    for y in (HALF_W, -HALF_W + 0.8):
        kit.prism(piece(STEEL, 3, bevel=0.12, segs=2, angle=40, name="side panel"), rounded(BACK_X, HEAD_X + 0.3, BASE_Z + 0.8, TOP_Z + 0.2, 1.7, 0.4), 0.0, 0.8, side_frame(y))
    inner = HALF_W - 0.8
    kit.box(piece(STEEL, 3, bevel=0.1, angle=40, name="body"), (BACK_X + 0.2, -inner, BASE_Z + 0.8), (FRONT_X, inner, TOP_Z))
    kit.box(piece(STEEL, 3, bevel=0.18, segs=2, angle=40, name="head"), (FRONT_X - 0.1, -inner, HEAD_Z), (HEAD_X, inner, TOP_Z))
    # Trim strips across the back, where the customers see it.
    for z in (6.2, 17.0):
        kit.box(piece(CHROME, 2, bevel=0.06, angle=40, name="trim"), (BACK_X + 0.05, -inner, z), (BACK_X + 0.25, inner, z + 0.45))
    # The base pan, black, and chrome feet with rubber pads.
    kit.box(piece(BLACK, 3, bevel=0.1, angle=40, name="base"), (BACK_X + 0.4, -HALF_W + 0.4, BASE_Z), (HEAD_X - 0.4, HALF_W - 0.4, BASE_Z + 0.8))
    for x in (-7.6, 5.6):
        for y in (-11.8, 11.8):
            kit.lathe(piece(CHROME, 2, name="foot"), [(0, 0.25), (0.62, 0.25), (0.62, 0.45), (0.5, 0.6), (0.5, BASE_Z - 0.2), (0.75, BASE_Z), (0, BASE_Z)], 16, kit.frame((x, y, 0)))
            kit.lathe(piece(RUBBER, 1, name="foot"), [(0, 0.0), (0.7, 0.0), (0.72, 0.25), (0, 0.25)], 16, kit.frame((x, y, 0)))


def group(y):
    """A group head under the head, its portafilter locked in with the handle out toward the barista."""
    o = Vector((GROUP_X, y, HEAD_Z))
    kit.lathe(piece(CHROME, 3, name="group"), [(0, 0.0), (2.05, 0.0), (2.05, -0.5), (1.85, -0.75), (1.8, -2.2), (1.95, -2.35), (1.95, -2.7), (0, -2.7)], 32, kit.frame(o))
    kit.lathe(piece(RUBBER, 0, name="gasket"), [(0, -2.69), (1.9, -2.69), (1.9, -2.8), (0, -2.8)], 32, kit.frame(o))
    # The portafilter: its basket's body, the double spout under it, and the handle.
    kit.lathe(piece(CHROME, 3, name="portafilter"), [(0, -2.8), (1.82, -2.8), (1.86, -3.0), (1.78, -3.5), (1.45, -3.85), (0.5, -4.0), (0, -4.0)], 32, kit.frame(o))
    for lug in (-1, 1):
        kit.box(piece(CHROME, 1, bevel=0.05, angle=40, name="portafilter"), (-0.4, -0.25, -0.18), (0.4, 0.25, 0.18), kit.frame(o + Vector((0, lug * 1.95, -2.95)), (0, 0, 1), (0, 1, 0)))
    kit.lathe(piece(CHROME, 2, name="spout"), [(0, -3.9), (0.45, -3.9), (0.4, -4.3), (0.3, -4.5), (0, -4.5)], 16, kit.frame(o))
    for side in (-1, 1):
        a = o + Vector((0.0, side * 0.2, -4.35))
        b = a + Vector((0.15, side * 0.55, -0.55))
        tube(piece(CHROME, 1, name="spout"), [a, b], 0.16, 10)
    neck0 = o + Vector((1.75, 0, -3.25))
    neck1 = o + Vector((2.7, 0, -3.45))
    tube(piece(CHROME, 2, name="portafilter"), [neck0, neck1], 0.36, 14)
    handle = kit.spline([neck1, neck1 + Vector((1.6, 0, -0.32)), neck1 + Vector((3.5, 0, -0.75)), neck1 + Vector((5.0, 0, -1.08))], 4)
    n = len(handle)
    tube(piece(BLACK, 3, name="handle"), handle, [0.42 + 0.16 * (k / (n - 1)) ** 0.8 for k in range(n)], 16, caps=True)


def wands():
    for side in (-1, 1):
        y = side * WAND_Y
        joint = Vector((HEAD_X - 0.4, y, HEAD_Z - 0.35))
        kit.lathe(piece(CHROME, 2, name="wand"), [(0, 0.35), (0.42, 0.35), (0.5, 0.1), (0.5, -0.2), (0.4, -0.45), (0, -0.5)], 16, kit.frame(joint))
        path = kit.spline([joint + Vector((0, 0, -0.4)), joint + Vector((0.5, side * 0.15, -2.0)), joint + Vector((1.3, side * 0.45, -4.5)), joint + Vector((1.85, side * 0.65, -6.4))], 5)
        tube(piece(CHROME, 3, name="wand"), path, 0.24, 12)
        sleeve = kit.spline([path[1], path[len(path) // 3], path[len(path) // 2]], 3)
        tube(piece(RUBBER, 2, name="sleeve"), sleeve, 0.38, 14)
        tip_axis = (path[-1] - path[-2]).normalized()
        kit.lathe(piece(CHROME, 2, name="wand"), [(0, -0.05), (0.3, -0.05), (0.32, 0.4), (0.18, 0.55), (0, 0.56)], 12, kit.frame(path[-1], tip_axis))
        # The lever that opens it, on the head's front above.
        pivot = Vector((HEAD_X, y, 15.4))
        kit.lathe(piece(CHROME, 1, name="lever"), [(0, 0.0), (0.7, 0.0), (0.7, 0.3), (0.45, 0.45), (0, 0.48)], 16, kit.frame(pivot, (1, 0, 0)))
        stick_end = pivot + Vector((1.3, 0, 1.0))
        tube(piece(CHROME, 1, name="lever"), [pivot + Vector((0.4, 0, 0)), stick_end], 0.15, 10)
        kit.lathe(piece(BLACK, 1, name="lever"), [(0, -0.48), (0.35, -0.42), (0.48, -0.1), (0.46, 0.2), (0.3, 0.42), (0, 0.48)], 14, kit.frame(stick_end))
    # The hot water spout and its button.
    o = Vector((HEAD_X - 0.6, 0, HEAD_Z))
    path = kit.spline([o, o + Vector((0.3, 0, -1.2)), o + Vector((0.9, 0, -2.6))], 4)
    tube(piece(CHROME, 2, name="water spout"), path, 0.26, 12)


def controls():
    """Two gauges in the middle of the head's front, and a keypad over each group."""
    for y, z in GAUGES:
        m = kit.frame((HEAD_X, y, z), (1, 0, 0))
        # A ring swept round, not turned: the toolkit's lathe caps its ends, and a turned bezel put a chrome disc over the dial.
        tube(piece(CHROME, 2, name="bezel"), kit.ring_path(1.26, 40, kit.frame((HEAD_X + 0.2, y, z), (1, 0, 0))), 0.17, 10, closed=True)
        kit.lathe(piece(GAUGE, 2, name="gauge"), [(0, 0.02), (1.12, 0.02), (1.12, 0.22), (0, 0.22)], 32, m)
    for y in (-GROUP_Y, GROUP_Y):
        m = kit.frame((HEAD_X, y, 14.6), (1, 0, 0), (0, 1, 0))
        kit.box(piece(BLACK, 2, bevel=0.06, angle=40, name="keypad"), (-1.9, -0.75, 0.0), (1.9, 0.75, 0.12), m)
        for k in range(4):
            kit.box(piece(STEEL, 1, bevel=0.05, angle=40, name="button"), (-1.55 + 0.85 * k, -0.32, 0.12), (-0.95 + 0.85 * k, 0.32, 0.24), m)


def tray():
    """The drip tray in front of the work area, a grate on top."""
    kit.box(piece(STEEL, 3, bevel=0.2, segs=2, angle=40, name="drip tray"), (FRONT_X, -HALF_W + 1.2, BASE_Z + 0.8), (TRAY_X, HALF_W - 1.2, BASE_Z + 2.3))
    kit.box(piece(STEEL, 2, bevel=0.03, angle=40, name="grate"), (FRONT_X + 0.3, -HALF_W + 1.6, BASE_Z + 2.3), (TRAY_X - 0.4, HALF_W - 1.6, BASE_Z + 2.42))


def warmer():
    """The cup warmer on top: a grid inside a chrome rail on posts, cups upside down on it."""
    inner = HALF_W - 1.1
    kit.box(piece(STEEL, 3, bevel=0.04, angle=40, name="warmer"), (BACK_X + 1.0, -inner, TOP_Z), (HEAD_X - 1.0, inner, TOP_Z + 0.2))
    z = TOP_Z + 1.5
    corners = [(BACK_X + 0.9, -inner), (HEAD_X - 0.9, -inner), (HEAD_X - 0.9, inner), (BACK_X + 0.9, inner)]
    rail = []
    for (xa, ya), (xb, yb) in zip(corners, corners[1:] + corners[:1]):
        for k in range(8):
            rail.append(Vector((xa + (xb - xa) * k / 8, ya + (yb - ya) * k / 8, z)))
    tube(piece(CHROME, 2, name="rail"), rail, 0.26, 10, closed=True)
    for x, y in corners + [((BACK_X + HEAD_X) / 2, -inner), ((BACK_X + HEAD_X) / 2, inner)]:
        tube(piece(CHROME, 1, name="rail"), [Vector((x, y, TOP_Z + 0.15)), Vector((x, y, z))], 0.2, 10)
    for x, y, kind in CUPS:
        if kind == "espresso":
            profile = [(0, 0.05), (0.58, 0.05), (0.62, 0.0), (0.7, 0.0), (0.74, 0.08), (0.95, 0.5), (1.12, 1.2), (1.18, 1.85), (1.17, 1.98), (1.1, 2.02), (1.03, 1.95), (1.0, 1.7), (0.88, 1.0), (0.6, 0.45), (0, 0.38)]
        else:
            profile = [(0, 0.06), (0.82, 0.06), (0.88, 0.0), (0.98, 0.0), (1.03, 0.07), (1.28, 0.45), (1.54, 1.1), (1.7, 2.0), (1.73, 2.47), (1.71, 2.53), (1.62, 2.53), (1.6, 2.45), (1.57, 1.95), (1.38, 1.05), (0.95, 0.4), (0, 0.27)]
        h = max(zz for _, zz in profile)
        kit.lathe(piece(PORCELAIN, 2, name="cup"), profile, 24, kit.frame((x, y, TOP_Z + 0.2 + h), (0, 0, -1)))


def hoses():
    """The water feed and the drain, from the back of the base down through a grommet in the counter."""
    for y, r, finish in ((9.6, 0.28, CHROME), (10.6, 0.42, RUBBER)):
        path = kit.spline([(BACK_X + 1.2, y, BASE_Z + 0.4), (BACK_X - 0.3, y + 0.2, BASE_Z - 0.4), (BACK_X - 0.9, y + 0.5, 0.2), (BACK_X - 1.0, y + 0.6, -1.5)], 5)
        tube(piece(finish, 1, name="hose"), path, r, 12)
    kit.lathe(piece(BLACK, 1, name="grommet"), [(0.0, -0.05), (1.4, -0.05), (1.45, 0.05), (1.2, 0.12), (0, 0.12)], 24, kit.frame((BACK_X - 0.95, 10.6, 0)))


def geometry():
    body()
    for y in (-GROUP_Y, GROUP_Y):
        group(y)
    wands()
    controls()
    tray()
    warmer()
    hoses()


def harden_all():
    seen = set()
    for p in kit.parts:
        bm = p.bm
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
    """How much texture an island gets, against a side panel at 1. Half the boxes' area is hidden: the body and head behind the side panels, the tops under the cup warmer, its underside,
    the base pan under the body and the drip tray, and the machine's underside. Those get next to none."""
    if normal.z < -0.7 and centre.z < BASE_Z + 0.5:
        return 0.03
    if abs(normal.y) > 0.7 and abs(abs(centre.y) - (HALF_W - 0.8)) < 0.12 and centre.x < HEAD_X + 0.2:
        return 0.04
    if abs(normal.z) > 0.7 and (abs(centre.z - TOP_Z) < 0.05 or abs(centre.z - (BASE_Z + 0.8)) < 0.05):
        return 0.04
    if finish == GAUGE:
        return 3.2 if normal.x > 0.5 else 0.3
    if finish == BLACK:
        return 1.2
    if finish in (PORCELAIN, RUBBER):
        return 0.6
    return 1.0


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
    hw = kit.join_parts(kit.parts, "machine_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    lookup = {round(p.rand, 4): p for p in kit.parts}
    bm = bmesh.new()
    bm.from_mesh(hw.data)
    facts = bm.loops.layers.float_color["facts"]
    areas = {}
    for f in bm.faces:
        p = lookup[round(f.loops[0][facts][1], 4)]
        areas[p.name] = areas.get(p.name, 0.0) + f.calc_area()
    bm.free()
    print("areas", {k: round(v) for k, v in sorted(areas.items(), key=lambda kv: -kv[1])}, flush=True)
    density = pack(hw.data, 4)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), "px/in %.1f" % density, flush=True)

    def lod(number, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = f"machine_lod{number}"
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
    np.save(os.path.join(WORK, "machine_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "machine_parts.json"), "w") as h:
        json.dump([[p.rand, p.name, p.finish] for p in kit.parts], h)
    with open(os.path.join(WORK, "machine.json"), "w") as h:
        json.dump(
            dict(density=density, range=POS_RANGE, half_w=HALF_W, back_x=BACK_X, front_x=FRONT_X, head=(HEAD_X, HEAD_Z), base_z=BASE_Z, top_z=TOP_Z, group=(GROUP_X, GROUP_Y), wand_y=WAND_Y, tray_x=TRAY_X, gauges=GAUGES),
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
    hw = bpy.data.objects["machine_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 3.0
    with open(os.path.join(WORK, "machine_baked_uv_hash.txt"), "w") as h:
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

    bake_one(W, H, "EMIT", source("pos"), 1, "bake_em_pos")
    bake_one(W, H, "EMIT", source("nor"), 1, "bake_em_nor")
    bake_one(W, H, "EMIT", source("facts"), 1, "bake_em_facts")
    bake_one(W // 2, H // 2, "AO", None, 40, "bake_em_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["machine_lod0"]) != open(os.path.join(WORK, "machine_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"machine_lod{number}"]
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
            h.write(f"# Generated by Sources/CerroBlanco/espresso-machine-v2/machine.py\nmtllib {NAME}.mtl\n")
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
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 20.0, 60.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/CerroBlanco/espresso-machine-v2/machine.py
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
    vmat = f"""// Generated by Sources/CerroBlanco/espresso-machine-v2/machine.py

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
print("machine stages done", flush=True)
