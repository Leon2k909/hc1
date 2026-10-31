"""Railhead's hand pallet truck v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python-exit-code 1 --python pallet_truck.py -- <work dir> <project root> <build|bake|export> ...

The truck in the goods yard was two red boxes for forks, a tube for a pump and a thin red stick with a bar on it. This keeps its size and bold red and builds the real
thing: pressed channel forks open underneath, with load rollers in their tips, a welded frame, a hydraulic pump with its chrome ram, two rubber steering wheels in a yoke, and a
tiller with a looped handle, a ribbed grip and a release lever. On the ground at the origin, the forks along +X, which is where the map's frame puts them. Inches, engine axes.
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

from build import Part, add, box, frame, lathe, prism, spline, tube  # noqa: E402

PAINT, BLACK, RUBBER, CHROME, ZINC, NYLON = range(6)
MODEL = "models/props/railhead/pallet_truck_v2"
OUT = os.path.join(ROOT, "Assets", "models", "props", "railhead", "pallet_truck_v2")
BLEND = os.path.join(WORK, "truck_build.blend")
RES = 2048
RANGE = 200.0
FORK_Y = 7.5
FORK_W = 3.15
FORK_H = 3.35


def channel(half, height, skin=0.17, r=0.3, segs=2):
    """A pressed channel's section, open underneath: (y, z) round the outside and back along the inside."""
    outer = [(-half, 0.0)]
    for k in range(segs + 1):
        a = math.pi - (math.pi / 2) * k / segs
        outer.append((-half + r + r * math.cos(a), height - r + r * math.sin(a)))
    for k in range(segs + 1):
        a = math.pi / 2 - (math.pi / 2) * k / segs
        outer.append((half - r + r * math.cos(a), height - r + r * math.sin(a)))
    outer.append((half, 0.0))
    inner = [(half - skin, 0.0), (half - skin, height - skin), (-half + skin, height - skin), (-half + skin, 0.0)]
    return outer + inner


def loft(part, stations):
    """Sections joined along X. Each station is (x, half width, height), all with the same number of points, capped at both ends."""
    bm = part.bm
    rings = []
    for x, half, height in stations:
        rings.append([bm.verts.new((x, part.y0 + y, z)) for y, z in channel(half, height)])
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def side_plate(part, y0, y1, outline):
    """A plate cut to an outline of (x, z), between y0 and y1."""
    m = frame((0, y0, 0), (0, 1, 0), (1, 0, 0))
    prism(part, [(x, -z) for x, z in outline], 0.0, y1 - y0, m)


def hex_bolt(at, axis, r=0.34, finish=ZINC, lod=0):
    lathe(add(Part(finish, lod, name="bolt")), [(r, 0.0), (r, r * 0.5), (r * 0.82, r * 0.68), (0.0, r * 0.68)], 6, frame(at, axis))


def wheel(y, r=3.6, width=2.2):
    """A steering wheel with its axis across: a rubber tyre on a steel centre with a cap."""
    x, z = -6.5, 3.6
    m = frame((x, y - width / 2, z), (0, 1, 0), (1, 0, 0))
    lathe(add(Part(RUBBER, 3, name="tyre")), [(r - 1.5, 0.08), (r - 0.28, 0.08), (r - 0.08, 0.24), (r, 0.5), (r, width - 0.5), (r - 0.08, width - 0.24), (r - 0.28, width - 0.08), (r - 1.5, width - 0.08)], 28, m)
    lathe(add(Part(ZINC, 2, name="hub")), [(r - 1.5, 0.28), (r - 1.62, 0.2), (0.9, 0.2), (0.74, 0.0), (0.0, 0.0)], 18, m)
    lathe(add(Part(ZINC, 2, name="hub")), [(r - 1.5, width - 0.28), (r - 1.62, width - 0.2), (0.9, width - 0.2), (0.74, width), (0.0, width)], 18, m)


def fork(y0):
    part = add(Part(PAINT, 3, bevel=0.035, angle=50, name="fork"))
    part.y0 = y0
    loft(part, ((-2.9, FORK_W, FORK_H), (41.8, FORK_W, FORK_H), (45.2, FORK_W, FORK_H * 0.76), (47.15, FORK_W * 0.86, FORK_H * 0.52)))
    # The load rollers in the tip, a pair on a pin, and the small entry roller in front of them. The pin's heads show on the fork's sides.
    for dy in (-1.32, 1.32):
        m = frame((41.0, y0 + dy - 1.0, 1.26), (0, 1, 0), (1, 0, 0))
        lathe(add(Part(NYLON, 2, name="roller")), [(0.0, 0.0), (1.08, 0.0), (1.22, 0.12), (1.22, 1.88), (1.08, 2.0), (0.0, 2.0)], 16, m)
    m = frame((46.1, y0 - 1.9, 0.72), (0, 1, 0), (1, 0, 0))
    lathe(add(Part(NYLON, 1, name="entry roller")), [(0.0, 0.0), (0.66, 0.0), (0.72, 0.08), (0.72, 3.72), (0.66, 3.8), (0.0, 3.8)], 12, m)
    for side in (-1, 1):
        hex_bolt((41.0, y0 + side * FORK_W, 1.26), (0, side, 0), 0.38)
        hex_bolt((46.1, y0 + side * FORK_W * 0.9, 0.72), (0, side, 0), 0.26)
    # The push rod inside it that lifts the rollers.
    box(add(Part(BLACK, 1, name="push rod")), (-2.0, y0 - 0.42, 1.2), (40.0, y0 + 0.42, 1.9))


def geometry():
    for y0 in (-FORK_Y, FORK_Y):
        fork(y0)
    # The frame across the forks' heels, with its top rising to the pump, and gussets welded on to each fork.
    frame_section = [(-2.9, 1.0), (2.8, 1.0), (2.8, 3.3), (-0.6, 5.2), (-2.3, 5.2), (-2.9, 4.6)]
    side_plate(add(Part(PAINT, 3, bevel=0.06, angle=30, name="frame")), -10.7, 10.7, frame_section)
    for y in (-FORK_Y - 2.7, -FORK_Y + 2.7, FORK_Y - 2.7, FORK_Y + 2.7):
        side_plate(add(Part(PAINT, 2, bevel=0.03, angle=40, name="gusset")), y - 0.12, y + 0.12, [(2.0, FORK_H - 0.1), (9.4, FORK_H - 0.1), (2.0, 4.0)])
    # The steering yoke: a top plate, a plate each side, the axle's bolts through them, and the wheels between.
    top = add(Part(PAINT, 3, bevel=0.05, angle=40, name="yoke"))
    box(top, (-8.5, -5.26, 7.3), (-2.0, 5.26, 7.96))
    for sy in (-1, 1):
        y0, y1 = sorted((sy * 4.98, sy * 5.26))
        side_plate(add(Part(PAINT, 3, bevel=0.04, angle=40, name="yoke side")), y0, y1, [(-8.2, 7.4), (-7.9, 3.2), (-6.9, 2.5), (-6.1, 2.5), (-5.1, 3.2), (-2.3, 7.4)])
        hex_bolt((-6.5, sy * 5.26, 3.6), (0, sy, 0), 0.5)
        wheel(sy * 3.4)
    box(add(Part(ZINC, 2, name="axle")), (-6.78, -5.0, 3.32), (-6.22, 5.0, 3.88))
    # Two arms from the frame up to the pump's collar.
    for y in (-2.6, 2.6):
        side_plate(add(Part(PAINT, 2, bevel=0.03, angle=40, name="arm")), y - 0.2, y + 0.2, [(-2.9, 3.0), (-1.4, 3.0), (-2.2, 9.2), (-3.8, 9.2)])
    # The pump, up out of the yoke: its collar, the oil-filled body with its filler plug, the chrome ram, and the head that takes the tiller's pivot.
    axis = frame((-4.2, 0.0, 0.0), (0, 0, 1))
    lathe(add(Part(PAINT, 3, name="pump")), [(3.05, 7.9), (3.05, 8.5), (2.92, 8.72), (2.42, 8.82), (2.42, 11.9), (2.3, 12.04), (1.5, 12.14), (1.5, 12.3), (0.0, 12.3)], 22, axis)
    lathe(add(Part(CHROME, 3, name="ram")), [(1.2, 12.1), (1.2, 13.72), (0.0, 13.72)], 18, axis)
    lathe(add(Part(ZINC, 1, name="wiper")), [(1.42, 12.26), (1.42, 12.52), (1.22, 12.6), (0.0, 12.6)], 16, axis)
    hex_bolt((-1.8, 0.0, 10.4), (1, 0, 0), 0.42, ZINC, 1)
    head = add(Part(PAINT, 3, bevel=0.07, angle=40, name="head"))
    box(head, (-5.9, -2.1, 13.6), (-2.5, 2.1, 14.9))
    for y in (-1.15, 1.15):
        side_plate(add(Part(PAINT, 3, bevel=0.03, angle=40, name="clevis")), y - 0.17, y + 0.17, [(-6.2, 14.8), (-3.4, 14.8), (-3.9, 17.4), (-5.7, 17.6)])
    hex_bolt((-4.8, 1.32, 16.2), (0, 1, 0), 0.34, ZINC, 1)
    hex_bolt((-4.8, -1.32, 16.2), (0, -1, 0), 0.34, ZINC, 1)
    # The pump's lever spring, inside the clevis, and the release rod running up the tiller's back.
    tube(add(Part(ZINC, 1, name="rod")), [Vector((-5.9, 0.0, 17.0)), Vector((-10.15, 0.0, 41.4))], 0.15, 6)
    # The tiller: a tube up from the pivot to the loop.
    bottom = Vector((-4.8, 0.0, 15.6))
    neck = Vector((-9.0, 0.0, 41.8))
    tube(add(Part(PAINT, 3, name="tiller")), [bottom, bottom.lerp(neck, 0.5), neck], 0.8, 14)
    # The looped handle: two arms from the neck round to the grip's ends.
    for sy in (-1, 1):
        points = [(-9.0, 0.0, 41.4), (-9.08, sy * 1.5, 42.9), (-9.2, sy * 3.9, 44.4), (-9.3, sy * 5.2, 45.7), (-9.3, sy * 4.9, 46.7), (-9.3, sy * 3.7, 47.02)]
        tube(add(Part(PAINT, 3, name="loop")), [Vector(p) for p in spline(points, 5)], 0.58, 10)
    # The grip, ribbed, with its end flares, and the lever under it.
    profile = [(0.0, 0.0), (0.92, 0.0), (0.92, 0.22), (0.78, 0.3)]
    y, step = 0.3, 0.42
    while y < 7.1:
        profile += [(0.78, y + step * 0.45), (0.84, y + step * 0.55), (0.78, y + step)]
        y += step
    profile += [(0.78, 7.34), (0.92, 7.42), (0.92, 7.64), (0.0, 7.64)]
    lathe(add(Part(BLACK, 3, name="grip")), profile, 12, frame((-9.3, -3.82, 47.02), (0, 1, 0), (1, 0, 0)))
    lever = add(Part(BLACK, 1, bevel=0.03, angle=40, name="lever"))
    box(lever, (-10.02, -1.3, 45.72), (-9.82, 1.3, 46.42))
    side_plate(add(Part(ZINC, 1, name="lever arm")), -0.1, 0.1, [(-10.2, 41.2), (-10.0, 41.2), (-9.86, 45.8), (-10.06, 45.8)])
    # Screws along the frame's back.
    for y in (-8.6, -6.2, 6.2, 8.6):
        hex_bolt((-2.9, y, 3.1), (-1, 0, 0), 0.34)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    dev = kit.join_parts(kit.parts, "pt_lod0")
    dev.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = dev
    dev.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # A low limit, so eased edges part from the flats. As one island, they'd waste half the atlas.
    bpy.ops.uv.smart_project(angle_limit=math.radians(20), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    dev.select_set(False)
    kit.pack_real_scale(dev.data, RES, 3)

    mesh = dev.data
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    # The packer doesn't reject an island wider than the atlas, and a long fork can be. An even scale keeps the real scale.
    largest = uv.max()
    if largest > 0.998:
        uv *= 0.998 / largest
        mesh.uv_layers["UVMap"].data.foreach_set("uv", uv)
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
    density = RES * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def lod(name, keep, ratio):
        copy = dev.copy()
        copy.data = dev.data.copy()
        copy.name = copy.data.name = name
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        layer = bm.loops.layers.float_color["facts"]
        drop = [f for f in bm.faces if lookup.get(round(f.loops[0][layer][1], 4)) is not None and lookup[round(f.loops[0][layer][1], 4)].lod < keep]
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

    lod("pt_lod1", 1, 0.6)
    lod("pt_lod2", 2, 0.35)
    lod("pt_lod3", 3, 0.2)
    with open(os.path.join(WORK, "truck.json"), "w") as h:
        json.dump(dict(density=density, range=RANGE), h)
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
    dev = bpy.data.objects["pt_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not dev
    bpy.ops.mesh.primitive_plane_add(size=500, location=(0, 0, -0.01))
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 3.0
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
            scale = 1 / RANGE if kind == "pos" else 0.5
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_pt_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_pt_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_pt_facts")

    def edges(nt, emit):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        bevel = nt.nodes.new("ShaderNodeBevel")
        bevel.samples = 8
        bevel.inputs["Radius"].default_value = 0.09
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(geo.outputs["Normal"], dot.inputs[0])
        nt.links.new(bevel.outputs["Normal"], dot.inputs[1])
        turn = nt.nodes.new("ShaderNodeMath")
        turn.operation = "SUBTRACT"
        turn.inputs[0].default_value = 1.0
        nt.links.new(dot.outputs["Value"], turn.inputs[1])
        nt.links.new(turn.outputs[0], emit.inputs[0])

    bake_one(RES, "EMIT", edges, 16, "bake_pt_edge")
    bake_one(1024, "AO", None, 48, "bake_pt_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["pt_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2, 3):
        ob = bpy.data.objects[f"pt_lod{lod}"]
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
        with open(os.path.join(OUT, f"truck_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Railhead/pallet-truck-v2/pallet_truck.py\nmtllib truck.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl pt_truck\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(OUT, "truck.mtl"), "w", newline="\n") as h:
        h.write("newmtl pt_truck\nKd 1 1 1\nd 1\n")

    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/truck_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 90.0, 220.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Railhead/pallet-truck-v2/pallet_truck.py
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
							{{ from = "pt_truck.vmat" to = "{MODEL}/pt_truck.vmat" }}
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
    with open(os.path.join(OUT, "truck.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Railhead/pallet-truck-v2/pallet_truck.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MODEL}/pt_truck_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/pt_truck_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MODEL}/pt_truck_metal.png"

	//---- Normal ----
	TextureNormal "{MODEL}/pt_truck_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/pt_truck_rough.png"
}}
"""
    with open(os.path.join(OUT, "pt_truck.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("truck stages done", flush=True)
