"""Wall-buy board v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python board.py -- <work dir> <project root> <build|bake|export> ...

The old board is models/dev/box.vmdl stretched to 2 x 60 x 40 and tinted brown, hanging 20 inches off the floor with
nothing holding it or the gun up. This is an armoury rack that stands on the floor: a welded steel frame on two foot
plates, five bolted planks where the old board was, and a padded rail behind the gun. A padlock on a vinyl cable hangs
off the rail's end. The planks keep the old board's size and place, and the frame fills the station's box collider
(10 x 60 x 60), which is what stops players, so nothing can stand inside the feet.

Inches, engine axes (+X towards the player, Z up), origin at the old board's centre: station (-4, 0, 40), so the floor is
z -40 and the gun's centre x +6, z 0. There are three to a match, so LOD 0 is a few thousand triangles.
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

from build import Part, add, box, frame, hex_bolt, lathe, prism, spline, tube, weld_line  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE = kit.PAINT, kit.GALV, kit.OXIDE, kit.ZINC, kit.BRASS, kit.RUBBER, kit.WELD, kit.PLATE
CABLE, FOOT, TIMBER, PAPER, CLIPBOARD = 9, 10, 11, 12, 13
NAME = "wall_buy_board"
MODEL = "models/zombies/wall_buy_board_v2"
MATS = "materials/zombies/wall_buy_board_v2"
BLEND = os.path.join(WORK, "board_build.blend")

FLOOR, TOP, HALF = -40.0, 20.0, 30.0
PLANKS = 5
PLANK_SPAN = 18.4
PLANK_PITCH = 2 * PLANK_SPAN / PLANKS
PLANK_FACE = 0.45
RAIL_FRONT = 3.15
CLIP_Y, CLIP_Z, CLIP_TILT = -20.0, 16.2, 2.5
XZ = frame((0, 0, 0), (0, -1, 0), (1, 0, 0))  # Local (x, y, z) is world (x, -z, y).


def yz(x=0.0):
    """Local (a, b, c) is world (x + c, a, b)."""
    return frame((x, 0, 0), (1, 0, 0), (0, 1, 0))


def side_prism(part, outline_xz, ya, yb):
    """A counter-clockwise (x, z) outline extruded between ya and yb."""
    prism(part, outline_xz, -max(ya, yb), -min(ya, yb), XZ)


def stand():
    for s in (-1, 1):
        ya, yb = sorted((s * 28.04, s * 29.96))
        box(add(Part(PAINT, 3, bevel=0.09, name="post")), (-0.96, ya, FLOOR + 0.4), (0.96, yb, TOP - 0.17))
        ca, cb = sorted((s * 28.0, s * 30.0))
        box(add(Part(RUBBER, 3, bevel=0.07, name="post cap")), (-1.0, ca, TOP - 0.17), (1.0, cb, TOP))

        foot = [(-1.0, 26.5), (8.1, 26.5), (9.0, 27.4), (9.0, 29.1), (8.1, 30.0), (-1.0, 30.0)]
        if s < 0:
            foot = [(x, -y) for x, y in reversed(foot)]
        prism(add(Part(FOOT, 3, bevel=0.05, name="foot plate")), foot, FLOOR, FLOOR + 0.4)
        for x in (3.0, 7.0):
            hex_bolt((x, s * 27.45, FLOOR + 0.4), (0, 0, 1), 0.72, lod=1, stud=0.2)

        # The brace that lets it stand free of a wall.
        by0, by1 = sorted((s * 28.5, s * 29.5))
        side_prism(add(Part(PAINT, 3, bevel=0.07, name="brace")), [(6.5, FLOOR + 0.4), (7.95, FLOOR + 0.4), (0.96, -14.8), (0.96, -16.8)], by0, by1)
        for y in (by0, by1):
            weld_line((6.5, y, FLOOR + 0.46), (7.95, y, FLOOR + 0.46), 0.075, lod=1)
            weld_line((1.0, y, -16.8), (1.0, y, -14.8), 0.075, lod=1)

        # Welds round the post's foot and where the rails meet it.
        inner = s * 28.04
        for a, b in (
            ((0.99, ya, FLOOR + 0.46), (0.99, yb, FLOOR + 0.46)),
            ((-0.9, ya, FLOOR + 0.46), (-0.9, yb, FLOOR + 0.46)),
            ((-0.96, inner, FLOOR + 0.46), (0.96, inner, FLOOR + 0.46)),
        ):
            weld_line(a, b, 0.095, lod=1)
        for z0, z1, depth in ((18.4, 19.8, 0.75), (-20.0, -18.4, 0.75), (-33.5, -32.1, 0.6)):
            weld_line((depth + 0.03, inner, z0), (depth + 0.03, inner, z1), 0.085, lod=1)

    box(add(Part(PAINT, 3, bevel=0.08, name="top rail")), (-0.75, -28.05, 18.4), (0.75, 28.05, 19.82))
    box(add(Part(PAINT, 3, bevel=0.08, name="bottom rail")), (-0.75, -28.05, -20.0), (0.75, 28.05, -18.4))
    box(add(Part(PAINT, 3, bevel=0.07, name="low rail")), (-0.6, -28.05, -33.5), (0.6, 28.05, -32.1))

    # A flat-bar X between the low rail and the bottom rail, pinned where the bars cross.
    bar_a = [(-27.7, -32.05), (-25.5, -32.05), (27.7, -19.95), (25.5, -19.95)]
    bar_b = [(25.5, -32.05), (27.7, -32.05), (-25.5, -19.95), (-27.7, -19.95)]
    prism(add(Part(PAINT, 2, bevel=0.035, name="cross bar")), bar_a, 0.04, 0.26, yz())
    prism(add(Part(PAINT, 2, bevel=0.035, name="cross bar")), bar_b, -0.26, -0.04, yz())
    hex_bolt((0.26, 0.0, -26.0), (1, 0, 0), 0.72, lod=1)
    hex_bolt((-0.26, 0.0, -26.0), (-1, 0, 0), 0.72, lod=0)

    # A stamped data plate on the top rail.
    box(add(Part(PLATE, 2, bevel=0.01, angle=30, name="data plate")), (0.75, -5.0, 18.62), (0.79, 5.0, 19.6))
    for y in (-4.7, 4.7):
        lathe(add(Part(ZINC, 0, name="rivet")), [(0.1, 0.0), (0.09, 0.03), (0.04, 0.05), (0, 0.055)], 6, frame((0.79, y, 19.11), (1, 0, 0)))


def planks():
    for k in range(PLANKS):
        z0 = -PLANK_SPAN + k * PLANK_PITCH + 0.04
        z1 = -PLANK_SPAN + (k + 1) * PLANK_PITCH - 0.04
        # They were cut and hung by hand: none sits quite flush with the next.
        dx = float(kit.rng.uniform(-0.05, 0.05))
        box(add(Part(TIMBER, 3, bevel=0.085, angle=30, name="plank")), (-PLANK_FACE + dx, -27.98, z0), (PLANK_FACE + dx, 27.98, z1))
        mid = (z0 + z1) / 2
        for y in (-26.2, -10.5, 10.5, 26.2):
            dome = [(0.36, 0.0), (0.34, 0.035), (0.24, 0.09), (0.0, 0.125)]
            lathe(add(Part(ZINC, 1, name="carriage bolt")), dome, 8, frame((PLANK_FACE + dx, y, mid), (1, 0, 0)))
            hex_bolt((-PLANK_FACE - 0.16, y, mid), (-1, 0, 0), 0.52, lod=0, washer=False)
    # The straps behind them, which the bolts pull the planks against.
    for y in (-26.2, -10.5, 10.5, 26.2):
        box(add(Part(PAINT, 2, bevel=0.03, name="strap")), (-PLANK_FACE - 0.16, y - 0.75, -18.4), (-PLANK_FACE - 0.04, y + 0.75, 18.4))


def rail():
    box(add(Part(OXIDE, 3, bevel=0.06, name="gun rail")), (2.15, -25.5, -0.8), (RAIL_FRONT, 25.5, 0.8))
    for s in (-1, 1):
        ya, yb = sorted((s * 25.5, s * 25.74))
        box(add(Part(RUBBER, 1, bevel=0.04, name="rail cap")), (2.11, ya, -0.84), (RAIL_FRONT + 0.04, yb, 0.84))
    for y in (-22.5, -7.5, 7.5, 22.5):
        box(add(Part(OXIDE, 3, bevel=0.03, name="standoff")), (PLANK_FACE + 0.18, y - 0.55, -0.55), (2.15, y + 0.55, 0.55))
        box(add(Part(OXIDE, 2, bevel=0.03, angle=30, name="standoff plate")), (PLANK_FACE, y - 1.5, -1.5), (PLANK_FACE + 0.18, y + 1.5, 1.5))
        for dy, dz in ((-1.15, -1.15), (1.15, -1.15), (-1.15, 1.15), (1.15, 1.15)):
            lathe(add(Part(ZINC, 0, name="screw")), [(0.16, 0.0), (0.14, 0.04), (0.0, 0.07)], 6, frame((PLANK_FACE + 0.18, y + dy, dz), (1, 0, 0)))
    # Rubber saddles on steel bands: close enough together for a pistol, far enough apart to steady a rifle.
    for y in (-15.0, -4.4, 4.4, 15.0):
        box(add(Part(OXIDE, 2, bevel=0.04, name="saddle band")), (2.05, y - 1.25, -0.92), (RAIL_FRONT + 0.1, y + 1.25, 0.92))
        box(add(Part(RUBBER, 2, bevel=0.09, segs=2, name="saddle")), (RAIL_FRONT + 0.1, y - 1.2, -1.1), (RAIL_FRONT + 0.6, y + 1.2, 1.1))


def lock():
    """A vinyl security cable looped round the rail's end, and the padlock that closes it, hanging open to the world."""
    loop = [
        (1.85, 24.45, 0.98),
        (2.65, 24.5, 1.2),
        (3.45, 24.48, 0.96),
        (3.62, 24.68, -0.7),
        (3.42, 25.05, -4.2),
        (3.12, 25.32, -8.4),
        (2.85, 25.38, -9.42),
        (2.58, 25.3, -8.4),
        (2.06, 24.98, -4.2),
        (1.72, 24.6, -0.7),
    ]
    path = spline(loop + [loop[0]], 3)[:-1]
    tube(add(Part(CABLE, 1, name="cable")), path, 0.115, 8, closed=True)
    shackle = spline([(2.85, 24.97, -10.6), (2.85, 24.97, -9.6), (2.85, 25.07, -9.17), (2.85, 25.38, -8.98), (2.85, 25.69, -9.17), (2.85, 25.79, -9.6), (2.85, 25.79, -10.6)], 3)
    tube(add(Part(ZINC, 1, name="shackle")), shackle, 0.125, 8)
    box(add(Part(BRASS, 1, bevel=0.1, segs=2, name="padlock")), (2.47, 24.5, -11.9), (3.23, 26.26, -10.45))
    box(add(Part(ZINC, 0, bevel=0.02, name="padlock keyway")), (2.75, 25.25, -11.95), (2.95, 25.51, -11.89))


def clipboard():
    """The sign-out sheet, hung on a nail and a little crooked. Above where a rifle's stock lies, so a gun won't hide it."""
    at = (PLANK_FACE + 0.08, CLIP_Y, CLIP_Z)
    tilt = math.radians(CLIP_TILT)
    m = frame(at, (1, 0, 0), (0, math.cos(tilt), math.sin(tilt)))
    box(add(Part(CLIPBOARD, 2, bevel=0.03, angle=30, name="clipboard")), (-3.1, -9.6, 0.0), (3.1, 0.0, 0.12), m)
    box(add(Part(PAPER, 2, name="sheet")), (-2.75, -9.2, 0.12), (2.75, -0.5, 0.145), m)
    box(add(Part(ZINC, 1, bevel=0.05, name="clip")), (-1.25, -1.05, 0.12), (1.25, -0.2, 0.34), m)
    tube(add(Part(ZINC, 0, name="clip wire")), [m @ Vector((x, y, z)) for x, y, z in ((-0.6, -0.35, 0.36), (-0.6, 0.35, 0.52), (0.6, 0.35, 0.52), (0.6, -0.35, 0.36))], 0.05, 6)
    lathe(add(Part(ZINC, 0, name="nail")), [(0.05, 0.0), (0.05, 0.3), (0.14, 0.31), (0.14, 0.36), (0.0, 0.36)], 6, frame((PLANK_FACE, CLIP_Y, CLIP_Z - 0.35), (1, 0, 0)))


def weight_of(face, facts):
    """How much texture a face gets, as a multiple of the real size. The planks' fronts are what a player reads."""
    finish = int(round(face.loops[0][facts][0] * 16))
    n = face.normal
    c = face.calc_center_median()
    if finish == TIMBER:
        return 1.0 if n.x > 0.7 else (0.34 if n.x < -0.7 else 0.25)
    if finish == PLATE:
        return 3.2
    if finish == PAPER:
        return 2.3
    if c.x < -0.42:
        return 0.3
    if finish == WELD:
        return 0.45
    if finish == ZINC:
        return 0.6
    if finish in (OXIDE, BRASS, CABLE, RUBBER):
        return 0.75
    return 0.6


def pack_weighted(mesh, res=2048, pad_px=4):
    """pack_real_scale from the capture flag's kit, with each island's size taken from its faces' weights."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    layer = bm.loops.layers.uv.active
    facts = bm.loops.layers.float_color["facts"]
    bm.faces.ensure_lookup_table()
    bm.normal_update()
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
        area3 = sum(f.calc_area() * weight_of(f, facts) ** 2 for f in faces)
        pts = np.array([tuple(l[layer].uv) for f in faces for l in f.loops])
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
        scale = math.sqrt(area3 / max(areauv, 1e-12))
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
    print("islands", len(rects), "plank face px/in %.1f" % density, flush=True)
    return density


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    stand()
    planks()
    rail()
    lock()
    clipboard()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "board_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    # Wider than the kit's 52 degrees: it joins the facets of small hex and tube parts, which at 52 are 1,200 tiny islands.
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    density = pack_weighted(hw.data)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), flush=True)

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

    lod("board_lod1", 1, 0.6)
    lod("board_lod2", 3, 0.7)
    with open(os.path.join(WORK, "board.json"), "w") as h:
        json.dump(dict(density=density, floor=FLOOR, plank_span=PLANK_SPAN, plank_pitch=PLANK_PITCH, plank_face=PLANK_FACE, clip=(CLIP_Y, CLIP_Z, CLIP_TILT)), h)
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
    hw = bpy.data.objects["board_lod0"]
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

    bake_one(2048, "EMIT", source("pos"), 1, "bake_board_pos")
    bake_one(2048, "EMIT", source("nor"), 1, "bake_board_nor")
    bake_one(2048, "EMIT", source("facts"), 1, "bake_board_facts")
    bake_one(1024, "AO", None, 32, "bake_board_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["board_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"board_lod{lod}"]
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
            h.write(f"# Generated by Sources/Zombies/wall-buy-board-v2/board.py\nmtllib {NAME}.mtl\n")
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
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 20.0, 60.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Zombies/wall-buy-board-v2/board.py
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
    vmat = f"""// Generated by Sources/Zombies/wall-buy-board-v2/board.py

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
    with open(os.path.join(mats, f"{NAME}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("board stages done", flush=True)
