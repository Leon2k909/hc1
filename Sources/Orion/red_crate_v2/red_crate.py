"""Orion's red steel crate v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python red_crate.py -- <work dir> <project root> <build|bake|export> ...

`orion_parts.red_crate` draws a flat red box with four dark corner bars and three flat strips. This is the transit crate that describes, in the map's 44 x 34 x 40 inch size on the same origin: pressed
corrugated walls in a welded frame, cast corner fittings to stack on, fork pockets you can see through, a hinged lid on a gasket, two over-centre latches, a padlocked hasp, fold-down end handles.
No collider: the map's own box stays. ORN and every marking are the map's own. Inches, engine axes: on the ground, the long side along Y, the latches at +X.
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

from build import Part, add, box, frame, hex_bolt, lathe, prism, spline, tube, weld_line  # noqa: E402

ZINC, BRASS, RUBBER, PLATE = kit.ZINC, kit.BRASS, kit.RUBBER, kit.PLATE
RED, STEEL, INNER, CARD, SEAL = 9, 10, 11, 12, 13
MODEL = "models/props/orion/red_crate_v2"
MATS = "materials/orion/red_crate_v2"
BLEND = os.path.join(WORK, "red_crate_build.blend")
SIZE, AO_SIZE = 2048, 1024
X, Y = 16.6, 21.6  # The frame's outside.
RAIL = 16.55
I = Matrix.Identity(4)


def ccw(outline):
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1]))
    return outline if area > 0 else list(reversed(outline))


def strip(part, chain, z0, z1, m=I, closed=False, top=False):
    """Only the outside of a wall, walking with the outside on the right: what's behind it is never seen, and shouldn't take up the atlas."""
    bm = part.bm
    low = [bm.verts.new(m @ Vector((a, b, z0))) for a, b in chain]
    high = [bm.verts.new(m @ Vector((a, b, z1))) for a, b in chain]
    n = len(chain)
    for k in range(n if closed else n - 1):
        j = (k + 1) % n
        bm.faces.new((low[k], low[j], high[j], high[k]))
    if top:
        bm.faces.new(high)


def rivet(at, axis, size=0.16, finish=None):
    lathe(add(Part(finish or ZINC, 0, name="rivet")), [(size, 0), (size * 0.8, size * 0.32), (0, size * 0.5)], 6, frame(at, axis))


def corrugation(lo, hi, centres, crown=1.45, slope=0.34):
    pts = [(lo, 0)]
    for c in centres:
        pts += [(c - crown / 2 - slope, 0), (c - crown / 2, 1), (c + crown / 2, 1), (c + crown / 2 + slope, 0)]
    pts.append((hi, 0))
    return pts


def walls():
    bay = [3.2 + k * 3.4 for k in range(5)]
    side = corrugation(-21.1, 21.1, [-c for c in reversed(bay)] + bay)
    end = corrugation(-16.0, 16.0, [-13.2 + 1.65 + k * 3.3 for k in range(8)])
    for sx in (-1, 1):
        chain = [(sx * (15.65 + 0.55 * lv), a) for a, lv in side]
        strip(add(Part(RED, 3, bevel=0.05, angle=14, name="side wall")), chain if sx > 0 else chain[::-1], 5.4, 35.4)
    for sy in (-1, 1):
        chain = [(a, sy * (20.55 + 0.55 * lv)) for a, lv in end]
        strip(add(Part(RED, 3, bevel=0.05, angle=14, name="end wall")), chain[::-1] if sy > 0 else chain, 5.4, 35.4)


def socket(at, axis, right):
    """A corner fitting's oval hole for a lashing hook."""
    m = frame(at, axis, right)
    oval = [(1.0 * math.cos(2 * math.pi * k / 10), 0.72 * math.sin(2 * math.pi * k / 10)) for k in range(10)]
    prism(add(Part(STEEL, 1, bevel=0.02, angle=30, name="socket lip")), oval, 0, 0.07, m)
    hole = [(a * 0.68, b * 0.62) for a, b in oval]
    prism(add(Part(INNER, 1, name="socket")), hole, 0, 0.075, m)


def frames():
    for sx in (-1, 1):
        for sy in (-1, 1):
            # The corner post, an angle, between its two fittings.
            post = [(16.6, 18.6), (16.6, 21.6), (13.6, 21.6), (13.6, 21.32), (16.32, 21.32), (16.32, 18.6)]
            prism(add(Part(STEEL, 3, bevel=0.05, angle=40, name="post")), ccw([(a * sx, b * sy) for a, b in post]), 3.2, 36.9)
            for z0, z1 in ((0.0, 3.2), (36.9, 40.2)):
                c = (sx * 15.25, sy * 20.25)
                box(add(Part(STEEL, 3, bevel=0.14, segs=2, angle=40, name="fitting")), (c[0] - 1.7, c[1] - 1.7, z0), (c[0] + 1.7, c[1] + 1.7, z1))
                mid = (z0 + z1) / 2
                socket((sx * 16.95, c[1], mid), (sx, 0, 0), (0, 1, 0))
                socket((c[0], sy * 21.95, mid), (0, sy, 0), (1, 0, 0))
            socket((sx * 15.25, sy * 20.25, 40.2), (0, 0, 1), (1, 0, 0))
            # Under the lid's notch, where the rails stop short of the fitting.
            box(add(Part(STEEL, 2, name="corner plate")), (min(sx * 12.6, sx * 16.0), min(sy * 17.6, sy * 21.0), 36.0), (max(sx * 12.6, sx * 16.0), max(sy * 17.6, sy * 21.0), 36.35))

    def side_rail(sx, z0, z1, name, inner=15.4, outer=RAIL, reach=18.6):
        a, b = sorted((sx * inner, sx * outer))
        box(add(Part(STEEL, 3, bevel=0.09, angle=40, name=name)), (a, -reach, z0), (b, reach, z1))

    def end_rail(sy, z0, z1, name):
        a, b = sorted((sy * 20.0, sy * 21.55))
        box(add(Part(STEEL, 3, bevel=0.09, angle=40, name=name)), (-13.6, a, z0), (13.6, b, z1))

    for sx in (-1, 1):
        side_rail(sx, 33.6, 36.4, "top rail")
        side_rail(sx, 5.6, 7.6, "low rail")
        side_rail(sx, 19.7, 21.5, "mid rail", 16.0, 16.45)
        a, b = sorted((sx * 16.0, sx * RAIL))
        box(add(Part(STEEL, 3, bevel=0.07, angle=40, name="centre post")), (a, -1.2, 7.6), (b, 1.2, 33.6))
        # Welded where the bars meet, painted over.
        for sy in (-1, 1):
            weld_line((sx * 16.46, sy * 1.28, 19.7), (sx * 16.46, sy * 1.28, 21.5), 0.09, 0)
            weld_line((sx * 16.46, sy * 18.5, 19.7), (sx * 16.46, sy * 18.5, 21.5), 0.09, 0)
            weld_line((sx * 16.56, sy * 18.56, 33.6), (sx * 16.56, sy * 18.56, 36.4), 0.09, 0)
            weld_line((sx * 16.56, sy * 18.56, 5.6), (sx * 16.56, sy * 18.56, 7.6), 0.09, 0)
            # A gusset in each top corner of the frame.
            m = frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
            tri = ccw([(sy * 18.5, 33.6), (sy * 18.5, 29.4), (sy * 14.3, 33.6)])
            z0, z1 = sorted((sx * 16.1, sx * 16.42))
            prism(add(Part(STEEL, 1, bevel=0.03, angle=40, name="gusset")), tri, z0, z1, m)
            for k, y in enumerate((5.2, 10.3, 14.9)):
                rivet((sx * 16.45, sy * y, 20.6), (sx, 0, 0), 0.17, STEEL)
    for sy in (-1, 1):
        end_rail(sy, 33.6, 36.4, "top rail")
        end_rail(sy, 5.6, 7.6, "low rail")


def pocket(y0, y1, m, wall=0.14, reach=16.25):
    """A fork pocket: a square steel tube with real walls, its faces out on both skins, so it's a closed solid with a hole through it."""
    part = add(Part(INNER, 3, name="fork pocket"))
    bm = part.bm
    inner = [(y0, 0.95), (y1, 0.95), (y1, 4.3), (y0, 4.3)]
    outer = [(a + (wall if a > (y0 + y1) / 2 else -wall), b + (wall if b > 2 else -wall)) for a, b in inner]

    def at(points, x):
        return [bm.verts.new(m @ Vector((a, b, x))) for a, b in points]

    in_low, in_high, out_low, out_high = at(inner, -reach), at(inner, reach), at(outer, -reach), at(outer, reach)
    for k in range(4):
        j = (k + 1) % 4
        bm.faces.new((out_low[k], out_low[j], out_high[j], out_high[k]))
        bm.faces.new((in_high[k], in_high[j], in_low[j], in_low[k]))
        bm.faces.new((out_high[k], out_high[j], in_high[j], in_high[k]))
        bm.faces.new((in_low[k], in_low[j], out_low[j], out_low[k]))


def base():
    """A sill on three sides of each fork pocket; the pockets run right through, so daylight shows under the crate."""
    for sx in (-1, 1):
        a, b = sorted((sx * 15.2, sx * 16.4))
        box(add(Part(STEEL, 3, bevel=0.06, angle=40, name="sill top")), (a, -18.6, 4.3), (b, 18.6, 5.6))
        box(add(Part(STEEL, 3, bevel=0.06, angle=40, name="sill foot")), (a, -18.6, 0.35), (b, 18.6, 0.95))
        a, b = sorted((sx * 15.2, sx * 16.3))
        for y0, y1 in ((-18.6, -14.0), (-6.0, 6.0), (14.0, 18.6)):
            box(add(Part(STEEL, 3, name="sill web")), (a, y0, 0.95), (b, y1, 4.3))
    for sy in (-1, 1):
        a, b = sorted((sy * 20.1, sy * 21.4))
        box(add(Part(STEEL, 3, bevel=0.06, angle=40, name="end sill")), (-13.6, a, 0.35), (13.6, b, 5.6))
    m = frame((0, 0, 0), (1, 0, 0), (0, 1, 0))
    for y0, y1 in ((-14.0, -6.0), (6.0, 14.0)):
        pocket(y0, y1, m)


def lid():
    notched = [(16.1, -18.2), (16.1, 18.2), (13.2, 18.2), (13.2, 21.1), (-13.2, 21.1), (-13.2, 18.2), (-16.1, 18.2), (-16.1, -18.2), (-13.2, -18.2), (-13.2, -21.1), (13.2, -21.1), (13.2, -18.2)]

    def inset(d):
        return [(math.copysign(abs(a) - d, a), math.copysign(abs(b) - d, b)) for a, b in notched]

    strip(add(Part(STEEL, 3, name="gasket seat")), inset(0.28), 36.2, 36.45, closed=True)
    strip(add(Part(RUBBER, 3, bevel=0.03, angle=30, name="gasket")), inset(0.14), 36.4, 36.75, closed=True)
    strip(add(Part(RED, 3, bevel=0.14, segs=2, angle=40, name="lid")), notched, 36.7, 38.5, closed=True, top=True)
    strip(add(Part(RED, 3, bevel=0.26, segs=2, angle=30, name="lid panel")), inset(1.3), 38.5, 39.3, closed=True, top=True)
    for y in (-7.5, 7.5):
        box(add(Part(RED, 2, bevel=0.14, segs=2, angle=30, name="lid swage")), (-10.4, y - 1.0, 39.3), (10.4, y + 1.0, 39.6))


def hinges():
    for y in (-13.0, 0.0, 13.0):
        box(add(Part(STEEL, 2, bevel=0.03, angle=40, name="hinge leaf")), (-16.72, y - 1.7, 34.3), (-RAIL, y + 1.7, 36.1))
        box(add(Part(STEEL, 2, bevel=0.03, angle=40, name="hinge leaf")), (-16.34, y - 1.7, 36.75), (-16.08, y + 1.7, 38.2))
        box(add(Part(STEEL, 2, bevel=0.03, angle=40, name="hinge arm")), (-16.72, y - 1.7, 36.1), (-16.34, y + 1.7, 36.75))
        for a, b in ((-1.7, -0.6), (-0.56, 0.56), (0.6, 1.7)):
            lathe(add(Part(STEEL, 1, bevel=0.03, angle=40, name="knuckle")), [(0.3, a), (0.3, b)], 10, frame((-16.86, y, 36.42), (0, 1, 0)))
        lathe(add(Part(ZINC, 0, name="pin")), [(0.17, -1.82), (0.17, 1.82)], 6, frame((-16.86, y, 36.42), (0, 1, 0)))
        for dy in (-1.15, 1.15):
            hex_bolt((-16.72, y + dy, 35.2), (-1, 0, 0), 0.36, 1, washer=False)
            rivet((-16.34, y + dy, 37.5), (-1, 0, 0))


def latch(y):
    box(add(Part(ZINC, 2, bevel=0.03, angle=40, name="latch plate")), (RAIL, y - 1.25, 34.0), (16.72, y + 1.25, 35.9))
    for dy in (-0.98, 0.98):
        for z in (34.28, 35.62):
            rivet((16.72, y + dy, z), (1, 0, 0), 0.13)
        box(add(Part(ZINC, 1, bevel=0.02, angle=40, name="latch lug")), (16.72, y + dy - 0.11, 34.4), (17.08, y + dy + 0.11, 35.1))
    lathe(add(Part(ZINC, 0, name="latch pin")), [(0.11, -1.14), (0.11, 1.14)], 6, frame((16.94, y, 34.76), (0, 1, 0)))
    # The lever, bent from plate, thrown shut against the lid.
    side = [(16.86, 34.5), (17.2, 34.5), (17.32, 35.0), (17.32, 37.1), (17.08, 37.62), (16.84, 37.52), (17.0, 37.0), (17.0, 35.1)]
    prism(add(Part(ZINC, 2, bevel=0.035, angle=25, name="latch lever")), ccw([(a, -b) for a, b in side]), -0.8, 0.8, frame((0, y, 0), (0, 1, 0), (1, 0, 0)))
    # The draw loop, over the keeper on the lid.
    box(add(Part(ZINC, 2, bevel=0.03, angle=40, name="keeper")), (16.08, y - 0.9, 37.15), (16.44, y + 0.9, 37.75))
    loop = [(17.02, y - 0.56, 35.1), (16.88, y - 0.56, 36.6), (16.62, y - 0.56, 37.5), (16.5, y - 0.36, 37.83), (16.5, y + 0.36, 37.83), (16.62, y + 0.56, 37.5), (16.88, y + 0.56, 36.6), (17.02, y + 0.56, 35.1)]
    tube(add(Part(ZINC, 1, name="draw loop")), [Vector(p) for p in loop], 0.085, 6)


def hasp():
    """A hasp over a staple on the frame, padlocked, in the middle of the front."""
    box(add(Part(ZINC, 2, bevel=0.03, angle=40, name="hasp")), (16.62, -0.85, 34.3), (16.78, 0.85, 37.95))
    box(add(Part(ZINC, 2, bevel=0.03, angle=40, name="hasp top")), (16.08, -0.85, 37.65), (16.78, 0.85, 37.95))
    for z in (37.0, 37.5):
        rivet((16.78, 0, z), (1, 0, 0), 0.12)
    tube(add(Part(ZINC, 1, name="staple")), spline([(RAIL, -0.34, 35.0), (16.86, -0.36, 35.0), (17.06, -0.2, 35.0), (17.06, 0.2, 35.0), (16.86, 0.36, 35.0), (RAIL, 0.34, 35.0)], 2), 0.09, 6)
    box(add(Part(BRASS, 2, bevel=0.07, segs=2, angle=40, name="padlock")), (16.72, -0.74, 32.3), (17.22, 0.74, 33.9))
    tube(add(Part(ZINC, 1, name="shackle")), spline([(16.97, -0.36, 33.85), (16.97, -0.36, 34.75), (16.97, -0.18, 35.16), (16.97, 0.18, 35.16), (16.97, 0.36, 34.75), (16.97, 0.36, 33.85)], 3), 0.1, 6)
    # A numbered wire seal on one latch.
    y = -11.5
    tube(add(Part(ZINC, 0, name="seal wire")), spline([(17.1, y - 0.04, 34.76), (17.16, y + 0.1, 34.2), (17.1, y + 0.05, 33.5)], 3), 0.03, 4)
    box(add(Part(SEAL, 0, bevel=0.012, angle=40, name="seal tag")), (17.06, y - 0.42, 31.8), (17.13, y + 0.5, 33.55))


def handle(sy):
    a, b = sorted((sy * 20.9, sy * 21.3))
    y1, y2 = sy * 21.25, sy * 21.8
    for sx in (-1, 1):
        box(add(Part(STEEL, 2, bevel=0.03, angle=40, name="handle plate")), (sx * 5.6 - 0.95, a, 26.5), (sx * 5.6 + 0.95, b, 28.5))
        for dz in (-0.72, 0.72):
            hex_bolt((sx * 5.6 + 0.58, sy * 21.3, 27.5 + dz), (0, sy, 0), 0.34, 0, washer=False)
        a2, b2 = sorted((sy * 21.3, sy * 21.72))
        box(add(Part(STEEL, 1, bevel=0.03, angle=40, name="handle lug")), (sx * 5.6 - 0.4, a2, 27.0), (sx * 5.6 + 0.1, b2, 28.0))
    points = [(-5.75, y1, 27.5), (-5.75, y2, 27.2), (-5.5, y2, 25.5), (-4.5, y2, 24.2), (-3.6, y2, 24.0), (3.6, y2, 24.0), (4.5, y2, 24.2), (5.5, y2, 25.5), (5.75, y2, 27.2), (5.75, y1, 27.5)]
    tube(add(Part(STEEL, 2, name="bail")), spline(points, 3), 0.23, 8)
    lathe(add(Part(RUBBER, 2, bevel=0.03, angle=30, name="grip")), [(0.34, -3.5), (0.34, 3.5)], 10, frame((0, y2, 24.0), (1, 0, 0)))


def fittings():
    # A card in a holder on the front, right of the post as you look at it, and the data plate on the rail.
    box(add(Part(STEEL, 2, bevel=0.03, angle=40, name="holder")), (16.18, 5.0, 24.4), (16.34, 14.0, 31.0))
    box(add(Part(CARD, 2, name="card")), (16.34, 5.4, 24.8), (16.37, 13.6, 30.6))
    for lo, hi in (((16.34, 5.0, 24.4), (16.46, 14.0, 24.8)), ((16.34, 5.0, 24.8), (16.46, 5.4, 31.0)), ((16.34, 13.6, 24.8), (16.46, 14.0, 31.0))):
        box(add(Part(STEEL, 1, bevel=0.02, angle=40, name="holder rim")), lo, hi)
    box(add(Part(PLATE, 2, bevel=0.012, angle=40, name="data plate")), (RAIL, 3.4, 34.2), (16.62, 8.2, 35.9))
    for y in (3.75, 7.85):
        for z in (34.5, 35.6):
            rivet((16.62, y, z), (1, 0, 0), 0.1, PLATE)


def geometry():
    walls()
    frames()
    base()
    lid()
    hinges()
    latch(-11.5)
    latch(11.5)
    hasp()
    handle(-1)
    handle(1)
    fittings()


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "rc_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, SIZE, 4)

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
    density = SIZE * math.sqrt(uva / area3)
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

    lod("rc_lod1", 1, 0.5)
    lod("rc_lod2", 2, 0.2)
    with open(os.path.join(WORK, "red_crate.json"), "w") as h:
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
    hw = bpy.data.objects["rc_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 5.0
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

    bake_one(SIZE, "EMIT", source("pos"), 1, "bake_rc_pos")
    bake_one(SIZE, "EMIT", source("nor"), 1, "bake_rc_nor")
    bake_one(SIZE, "EMIT", source("facts"), 1, "bake_rc_facts")
    bake_one(AO_SIZE, "AO", None, 48, "bake_rc_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["rc_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"rc_lod{lod}"]
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
        with open(os.path.join(out, f"red_crate_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Orion/red_crate_v2/red_crate.py\nmtllib red_crate.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl rc_crate\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "red_crate.mtl"), "w", newline="\n") as h:
        h.write("newmtl rc_crate\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/red_crate_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 28.0, 80.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Orion/red_crate_v2/red_crate.py
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
							{{ from = "rc_crate.vmat" to = "{MATS}/rc_crate.vmat" }}
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
    with open(os.path.join(out, "red_crate.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Orion/red_crate_v2/red_crate.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/rc_crate_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/rc_crate_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/rc_crate_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/rc_crate_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/rc_crate_rough.png"
}}
"""
    with open(os.path.join(mats, "rc_crate.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("red crate stages done", flush=True)
