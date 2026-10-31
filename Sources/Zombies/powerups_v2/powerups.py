"""Zombies power-up drops v2: build their meshes, bake their facts and write their files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python powerups.py -- <work dir> <project root> <one_hit|clean_sweep> <build|bake|export> ...

`ZombiesPowerUp.Spawn` shows these two as a tinted dev cube, 15 inches on a side, spinning in the air. Each becomes an object
that says what it does at a glance, inside the same 15-inch cube, centred on the same origin:
- One-Hit Kills: a strapped bundle of seven oversized red-tipped armour-piercing rounds on a steel base.
- Clean Sweep: a hand-plunger blasting machine in chipped safety orange, its T-handle up and its leads run to a wire spool.
Generic game props with invented lettering and no brand, real or game. No collider, as before. Inches, engine axes, Z up.
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
WORK, ROOT, VARIANT = argv[0], argv[1], argv[2]
STAGES = argv[3:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, box, frame, hex_bolt, lathe, prism, ring_path, spline, tube  # noqa: E402

BRASS, RUBBER, ZINC, PLATE = kit.BRASS, kit.RUBBER, kit.ZINC, kit.PLATE
COPPER, HARD, TIP, WEB, ORANGE, WIRE_RED, WIRE_DARK, CARRY = 9, 10, 11, 12, 13, 14, 15, 8
MODEL = "models/zombies/powerups_v2"
MATS = "materials/zombies/powerups_v2"
NAMES = {"one_hit": ("powerup_one_hit", "pu_one_hit"), "clean_sweep": ("powerup_clean_sweep", "pu_clean_sweep")}
NAME, MAT = NAMES[VARIANT]
BLEND = os.path.join(WORK, f"{VARIANT}_build.blend")
SIZE, AO_SIZE = 1024, 512
rng = np.random.default_rng(4417)


def ring(part, r0, r1, z0, z1, segs, m=Matrix.Identity(4), a0=0.0, a1=2 * math.pi):
    """A flat band swept about local Z from angle a0 to a1, with no discs across it."""
    bm = part.bm
    outline = [(r0, z0), (r1, z0), (r1, z1), (r0, z1)]
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    count = segs if full else segs + 1
    rows = []
    for k in range(count):
        t = a0 + (a1 - a0) * k / segs
        rows.append([bm.verts.new(m @ Vector((r * math.cos(t), r * math.sin(t), z))) for r, z in outline])
    for k in range(segs):
        a, b = rows[k], rows[(k + 1) % count]
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((a[i], b[i], b[j], a[j]))
    if not full:
        bm.faces.new(rows[0])
        bm.faces.new(list(reversed(rows[-1])))


def rivet(at, axis, size=0.14, finish=HARD):
    profile = [(size, 0), (size * 0.92, size * 0.34), (size * 0.5, size * 0.62), (0, size * 0.68)]
    lathe(add(Part(finish, 0, name="rivet")), profile, 8, frame(at, axis))


def heavy_round(x, y, zb):
    """A 12.7 mm round's real proportions at about two and a half times life size, standing on its base at zb."""
    m = frame((x, y, zb))
    brass = [(0, 0), (0.95, 0), (1.02, 0.05), (1.02, 0.19), (0.95, 0.24), (0.86, 0.3), (0.86, 0.48), (0.96, 0.56), (1.02, 0.66), (0.97, 3.0), (0.91, 7.65), (0.8, 7.92), (0.72, 8.16), (0.71, 9.3), (0.73, 9.36), (0.73, 9.5), (0.71, 9.56), (0.71, 9.97)]
    lathe(add(Part(BRASS, 3, name="case")), brass, 16, m)
    jacket = [(0.66, 9.93), (0.66, 10.28), (0.63, 10.33), (0.63, 10.47), (0.65, 10.52), (0.6, 11.2), (0.46, 12.15)]
    lathe(add(Part(COPPER, 3, name="jacket")), jacket, 16, m)
    tip = [(0.46, 12.13), (0.36, 12.7), (0.2, 13.4), (0.08, 13.82), (0, 13.9)]
    lathe(add(Part(TIP, 3, name="tip")), tip, 12, m)


def one_hit():
    zb = -6.4
    centres = [(0.0, 0.0)] + [(2.38 * math.cos(math.radians(30 + 60 * k)), 2.38 * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    for x, y in centres:
        heavy_round(x, y, zb)
        lathe(add(Part(HARD, 1, name="socket")), [(1.22, -6.05), (1.22, -5.62), (1.13, -5.54), (1.03, -5.52)], 16, frame((x, y, 0)))
    lathe(
        add(Part(HARD, 3, bevel=0.03, angle=30, name="base")),
        [(0, -7.5), (3.92, -7.5), (4.14, -7.34), (4.14, -6.12), (3.96, -5.96), (3.62, -5.92), (0, -5.92)],
        40,
    )
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        axis = Vector((math.cos(a), math.sin(a), 0))
        rivet(axis * 4.14 + Vector((0, 0, -6.72)), axis, 0.17, ZINC)
    # A steel band low down and a web strap with a buckle higher up hold the bundle together.
    ring(add(Part(ZINC, 3, bevel=0.012, angle=40, name="band")), 3.32, 3.44, -2.3, -1.45, 36)
    ring(add(Part(WEB, 3, name="web strap")), 3.27, 3.4, 2.1, 3.3, 36)
    box(add(Part(ZINC, 2, bevel=0.015, angle=40, name="clip")), (-0.55, -3.56, -2.42), (0.55, -3.42, -1.33))
    for dx in (-0.36, 0.36):
        rivet((dx, -3.56, -1.88), (0, -1, 0), 0.09, ZINC)
    box(add(Part(ZINC, 2, bevel=0.015, angle=40, name="buckle")), (-0.72, -3.52, 2.02), (0.72, -3.4, 3.38))
    box(add(Part(WEB, 2, name="buckle keeper")), (-0.42, -3.6, 2.1), (0.42, -3.5, 3.3))
    # A stamped tag on a wire, hanging off the buckle.
    box(add(Part(PLATE, 2, bevel=0.01, angle=40, name="tag")), (-1.35, -3.72, -0.92), (1.35, -3.66, 0.72))
    for dx in (-0.6, 0.6):
        tube(add(Part(ZINC, 1, name="tag wire")), spline([(dx, -3.68, 0.62), (dx * 0.85, -3.62, 1.3), (dx * 0.6, -3.55, 2.1)], 3), 0.03, 5)


def clean_sweep():
    box(add(Part(ORANGE, 3, bevel=0.07, segs=2, angle=40, name="body")), (-4.5, -3.75, -7.2), (4.5, 3.75, -1.6))
    box(add(Part(HARD, 3, bevel=0.05, angle=40, name="top plate")), (-4.75, -4.0, -1.62), (4.75, 4.0, -1.25))
    for x in (-4.3, 0.0, 4.3):
        for y in (-3.62, 3.62):
            rivet((x, y, -1.25), (0, 0, 1), 0.15, ZINC)
    # Angle iron on the corners, riveted through, and rubber feet.
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = [(4.56, 2.75), (4.56, 3.81), (3.5, 3.81), (3.5, 3.68), (4.43, 3.68), (4.43, 2.75)]
            pts = [(sx * x, sy * y) for x, y in pts]
            if sx * sy < 0:
                pts.reverse()
            prism(add(Part(HARD, 3, bevel=0.025, angle=40, name="corner")), pts, -7.26, -1.62)
            for z in (-6.5, -4.4, -2.3):
                rivet((sx * 4.56, sy * 3.3, z), (sx, 0, 0), 0.12)
                rivet((sx * 4.0, sy * 3.81, z), (0, sy, 0), 0.12)
            lathe(add(Part(RUBBER, 2, name="foot")), [(0.62, -7.5), (0.68, -7.44), (0.68, -7.2)], 12, frame((sx * 3.7, sy * 2.95, 0)))

    # The plunger: a bushing, the toothed rack and the T-handle.
    lathe(add(Part(BRASS, 3, bevel=0.015, angle=30, name="bushing")), [(1.05, -1.3), (1.05, -0.98), (0.88, -0.82), (0.72, -0.78)], 18)
    box(add(Part(ZINC, 3, bevel=0.035, angle=40, name="rack")), (-0.56, -0.36, -1.3), (0.56, 0.36, 6.2))
    for k in range(13):
        z = -0.55 + k * 0.5
        tooth = [(-0.1, z), (0.1, z), (0.04, z + 0.22), (-0.04, z + 0.22)]
        m = Matrix.Translation((0, 0.36, 0)) @ Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
        prism(add(Part(ZINC, 0, name="tooth")), [(y * 1.0 + 0.1, zz) for y, zz in tooth], -0.44, 0.44, m)
    box(add(Part(HARD, 3, bevel=0.05, angle=40, name="t block")), (-0.82, -0.52, 5.95), (0.82, 0.52, 6.86))
    axis = frame((0, 0, 6.4), (1, 0, 0))
    lathe(add(Part(ZINC, 3, name="t bar")), [(0, -4.1), (0.27, -4.1), (0.27, 4.1), (0, 4.1)], 12, axis)
    for side in (-1, 1):
        grip = [(0.28, 1.45), (0.4, 1.5), (0.46, 1.62)]
        for k in range(6):
            s = 1.8 + k * 0.42
            grip += [(0.44, s), (0.48, s + 0.08), (0.48, s + 0.26), (0.44, s + 0.34)]
        grip += [(0.5, 4.38), (0.5, 4.6), (0.36, 4.72), (0, 4.75)]
        m = frame((0, 0, 6.4), (side, 0, 0))
        lathe(add(Part(RUBBER, 3, name="t grip")), grip, 12, m)
    hex_bolt((0, -0.52, 6.4), (0, -1, 0), 0.5, lod=1, washer=False)

    # The two terminals with their leads, running to a spool of firing wire on the side.
    for y, wire in ((-1.5, WIRE_RED), (1.5, WIRE_DARK)):
        m = frame((2.9, y, -1.25))
        lathe(add(Part(BRASS, 3, bevel=0.012, angle=40, name="terminal")), [(0.44, 0), (0.44, 0.16)], 6, m)
        lathe(add(Part(BRASS, 2, name="stud")), [(0.15, 0.1), (0.15, 0.78), (0.08, 0.84), (0, 0.85)], 8, m)
        lathe(add(Part(BRASS, 2, bevel=0.01, angle=40, name="wing nut")), [(0.26, 0.42), (0.26, 0.68)], 8, m)
        box(add(Part(BRASS, 1, bevel=0.01, angle=40, name="wing")), (2.9 - 0.62, y - 0.05, -0.86), (2.9 + 0.62, y + 0.05, -0.56))
        lead = spline([(2.9, y, -0.85), (3.5, y * 0.92, -0.72), (4.6, y * 0.8, -0.95), (5.25, y * 0.55, -2.2), (5.42, y * 0.4, -3.1)], 4)
        tube(add(Part(wire, 3, name="lead")), lead, 0.085, 6)
    spool = frame((4.5, 0, -4.4), (1, 0, 0))
    lathe(add(Part(HARD, 3, name="spool core")), [(0, 0), (1.5, 0), (1.5, 0.14), (0.95, 0.2), (0.95, 1.5), (1.5, 1.56), (1.5, 1.7), (0, 1.7)], 22, spool)
    lathe(add(Part(WIRE_RED, 3, name="spool wire")), [(0.95, 0.2), (1.28, 0.26), (1.34, 0.5), (1.34, 1.2), (1.28, 1.44), (0.95, 1.5)], 22, spool)

    # The arming switch under its red flip cover, a carry handle and a plate.
    box(add(Part(HARD, 2, bevel=0.02, angle=40, name="switch base")), (-3.6, -1.05, -1.25), (-2.2, 1.05, -1.05))
    box(add(Part(TIP, 3, bevel=0.03, angle=40, name="flip cover")), (-3.45, -0.72, -1.05), (-2.35, 0.72, -0.72))
    for x in (-3.2, 3.2):
        box(add(Part(HARD, 2, bevel=0.03, angle=40, name="lug")), (x - 0.34, -4.34, -3.1), (x + 0.34, -3.75, -2.1))
    handle = spline([(-3.2, -4.1, -2.6), (-3.2, -4.38, -3.3), (-2.6, -4.42, -3.9), (2.6, -4.42, -3.9), (3.2, -4.38, -3.3), (3.2, -4.1, -2.6)], 3)
    tube(add(Part(HARD, 2, name="carry handle")), handle, 0.13, 8)
    box(add(Part(PLATE, 2, bevel=0.012, angle=40, name="plate")), (-1.9, 3.75, -6.1), (1.9, 3.81, -4.4))
    for x in (-1.72, 1.72):
        for z in (-5.92, -4.58):
            rivet((x, 3.81, z), (0, 1, 0), 0.07, PLATE)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    one_hit() if VARIANT == "one_hit" else clean_sweep()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "pu_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, SIZE, 3)

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

    lod("pu_lod1", 1, 0.5)
    lod("pu_lod2", 2, 0.2)
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
    hw = bpy.data.objects["pu_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 4.0
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

    bake_one(SIZE, "EMIT", source("pos"), 1, f"bake_{VARIANT}_pos")
    bake_one(SIZE, "EMIT", source("nor"), 1, f"bake_{VARIANT}_nor")
    bake_one(SIZE, "EMIT", source("facts"), 1, f"bake_{VARIANT}_facts")
    bake_one(AO_SIZE, "AO", None, 48, f"bake_{VARIANT}_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["pu_lod0"]) != open(os.path.join(WORK, f"{VARIANT}_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"pu_lod{lod}"]
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
            h.write(f"# Generated by Sources/Zombies/powerups_v2/powerups.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {MAT}\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {MAT}\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/{NAME}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 20.0, 60.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Zombies/powerups_v2/powerups.py
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
							{{ from = "{MAT}.vmat" to = "{MATS}/{MAT}.vmat" }}
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
    vmat = f"""// Generated by Sources/Zombies/powerups_v2/powerups.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/{MAT}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/{MAT}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/{MAT}_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/{MAT}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/{MAT}_rough.png"
}}
"""
    with open(os.path.join(mats, f"{MAT}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("powerup stages done", flush=True)
