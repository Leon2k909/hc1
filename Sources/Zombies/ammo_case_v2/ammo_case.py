"""Zombies ammo case v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python ammo_case.py -- <work dir> <project root> <build|bake|export> ...

`ZombiesPowerUp.CreateAmmoCase` builds today's case at runtime from tinted dev cubes with three magazines standing on top.
This is one model in its place, at the same origin and about the same size: a pressed-steel ammunition chest with its lid
stood open on two stay cables, a tray of loaded rifle magazines and three cartons of rounds. No collider, as before.
Inches, engine axes, the front (latches) at +X, the hinges at -X, Z up. Lettering is generic, with no brand, real or game.
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

from build import Part, add, box, frame, lathe, prism, spline, tube  # noqa: E402

BRASS, RUBBER, ZINC = kit.BRASS, kit.RUBBER, kit.ZINC
OD, CARD, PAPER, COPPER, MAG, HARD = 9, 10, 11, 12, 13, 14
MODEL = "models/zombies/ammo_case_v2"
MATS = "materials/zombies/ammo_case_v2"
BLEND = os.path.join(WORK, "ammo_case_build.blend")
SIZE, AO_SIZE = 2048, 1024
rng = np.random.default_rng(4417)

# The lid swings about this line and stands just past upright.
PIVOT = Vector((-7.55, 0.0, 3.1))
LID = Matrix.Translation(PIVOT) @ Matrix.Rotation(math.radians(-91), 4, "Y") @ Matrix.Translation(-PIVOT)


def rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def tray(part, x0, x1, y0, y1, z0, z1, wall, floor, m=Matrix.Identity(4)):
    """An open-topped box with real walls: one closed solid."""
    bm = part.bm
    ring = lambda pts, z: [bm.verts.new(m @ Vector((x, y, z))) for x, y in pts]
    outer, inner = rect(x0, x1, y0, y1), rect(x0 + wall, x1 - wall, y0 + wall, y1 - wall)
    ob, ot, it, ib = ring(outer, z0), ring(outer, z1), ring(inner, z1), ring(inner, z0 + floor)
    bm.faces.new(list(reversed(ob)))
    for k in range(4):
        n = (k + 1) % 4
        bm.faces.new((ob[k], ob[n], ot[n], ot[k]))
        bm.faces.new((ot[k], ot[n], it[n], it[k]))
        bm.faces.new((it[k], it[n], ib[n], ib[k]))
    bm.faces.new(ib)


def ring_box(part, x0, x1, y0, y1, z0, z1, wall, m=Matrix.Identity(4)):
    """A rectangular band: no top or bottom plate, so it doesn't spend the atlas on faces nobody sees."""
    bm = part.bm
    ring = lambda pts, z: [bm.verts.new(m @ Vector((x, y, z))) for x, y in pts]
    outer, inner = rect(x0, x1, y0, y1), rect(x0 + wall, x1 - wall, y0 + wall, y1 - wall)
    ob, ot, it, ib = ring(outer, z0), ring(outer, z1), ring(inner, z1), ring(inner, z0)
    for k in range(4):
        n = (k + 1) % 4
        bm.faces.new((ob[k], ob[n], ot[n], ot[k]))
        bm.faces.new((ot[k], ot[n], it[n], it[k]))
        bm.faces.new((it[k], it[n], ib[n], ib[k]))
        bm.faces.new((ib[k], ib[n], ob[n], ob[k]))


def rivet(at, axis, size=0.15, finish=OD):
    profile = [(size, 0), (size * 0.92, size * 0.34), (size * 0.5, size * 0.62), (0, size * 0.68)]
    lathe(add(Part(finish, 0, name="rivet")), profile, 8, frame(at, axis))


def body():
    tray(add(Part(OD, 3, bevel=0.04, segs=2, angle=40, name="body")), -7, 7, -12, 12, -9.5, 3.0, 0.16, 7.8)
    # Pressed-on bands and the rolled rim.
    for z0, z1 in ((-8.7, -7.9), (-4.2, -3.4)):
        ring_box(add(Part(OD, 3, bevel=0.03, angle=40, name="band")), -7.07, 7.07, -12.07, 12.07, z0, z1, 0.2)
    ring_box(add(Part(OD, 3, bevel=0.035, angle=40, name="rim")), -7.1, 7.1, -12.1, 12.1, 2.0, 3.03, 0.3)
    # Angle iron on the corners, riveted through.
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = [(7.13, 10.5), (7.13, 12.13), (5.5, 12.13), (5.5, 11.98), (6.98, 11.98), (6.98, 10.5)]
            pts = [(sx * x, sy * y) for x, y in pts]
            if sx * sy < 0:
                pts.reverse()
            prism(add(Part(OD, 3, bevel=0.03, angle=40, name="corner")), pts, -9.6, 2.0)
            for z in (-6.2, -1.9, 0.9):
                rivet((sx * 7.13, sy * 11.3, z), (sx, 0, 0))
                rivet((sx * 6.3, sy * 12.13, z), (0, sy, 0))
    for sx in (-1, 1):
        low, high = sorted((sx * 5.8, sx * 4.4))
        box(add(Part(HARD, 3, bevel=0.04, angle=40, name="skid")), (low, -11.7, -10.0), (high, 11.7, -9.5))


def latch(y):
    """An over-centre draw latch, hanging undone because the lid is up."""
    m = lambda: Matrix.Translation((7.24, y, -1.3)) @ Matrix.Rotation(math.radians(-9), 4, "Y") @ Matrix.Translation((-7.24, -y, 1.3))
    box(add(Part(ZINC, 2, bevel=0.012, angle=40, name="latch base")), (7.04, y - 1.1, -2.9), (7.14, y + 1.1, -0.85))
    for dy in (-0.82, 0.82):
        rivet((7.14, y + dy, -1.15), (1, 0, 0), 0.11, ZINC)
        rivet((7.14, y + dy, -2.6), (1, 0, 0), 0.11, ZINC)
    lathe(add(Part(ZINC, 2, bevel=0.0, name="knuckle")), [(0, -0.72), (0.15, -0.72), (0.15, 0.72), (0, 0.72)], 10, frame((7.24, y, -1.3), (0, 1, 0)))
    box(add(Part(ZINC, 2, bevel=0.012, angle=40, name="latch lever")), (7.19, y - 0.68, -4.3), (7.29, y + 0.68, -1.3), m())
    bail = spline([(7.3, y - 0.58, -1.8), (7.5, y - 0.58, -3.6), (7.62, y - 0.42, -4.75), (7.63, y, -4.92), (7.62, y + 0.42, -4.75), (7.5, y + 0.58, -3.6), (7.3, y + 0.58, -1.8)], 2)
    tube(add(Part(ZINC, 1, name="latch bail")), bail, 0.065, 6)
    box(add(Part(ZINC, 2, bevel=0.012, angle=40, name="lid catch")), (7.5, y - 0.7, 3.3), (7.6, y + 0.7, 4.5), LID)
    lathe(add(Part(ZINC, 1, name="catch hook")), [(0, -0.42), (0.1, -0.42), (0.1, 0.42), (0, 0.42)], 8, LID @ frame((7.72, y, 3.65), (0, 1, 0)))


def handle(side):
    ys = side * 12.42
    for x in (-3.1, 3.1):
        low, high = sorted((side * 12.05, side * 12.62))
        box(add(Part(HARD, 2, bevel=0.03, angle=40, name="handle lug")), (x - 0.34, low, -1.95), (x + 0.34, high, -0.85))
        rivet((x, side * 12.62, -1.4), (0, side, 0), 0.13, ZINC)
    path = spline([(-3.1, ys, -1.45), (-3.1, ys, -2.45), (-2.6, ys, -3.1), (2.6, ys, -3.1), (3.1, ys, -2.45), (3.1, ys, -1.45)], 3)
    tube(add(Part(HARD, 3, name="handle")), path, 0.15, 8)
    lathe(add(Part(RUBBER, 3, name="handle grip")), [(0.19, -2.25), (0.26, -2.14), (0.26, 2.14), (0.19, 2.25)], 10, frame((0, ys, -3.1), (1, 0, 0)))


def lid():
    m = LID @ Matrix.Translation((0, 0, 5)) @ Matrix.Rotation(math.pi, 4, "X")
    tray(add(Part(OD, 3, bevel=0.04, segs=2, angle=40, name="lid")), -7.5, 7.5, -12.5, 12.5, 0, 2, 0.15, 0.15, m)
    ring_box(add(Part(OD, 3, bevel=0.03, angle=40, name="lid rim")), -7.56, 7.56, -12.56, 12.56, 3.0, 3.8, 0.2, LID)
    box(add(Part(OD, 2, bevel=0.05, segs=2, angle=40, name="lid panel")), (-5.6, -10, 4.97), (5.6, 10, 5.07), LID)
    ring_box(add(Part(RUBBER, 1, name="gasket")), -7.35, 7.35, -12.35, 12.35, 4.5, 4.86, 0.34, LID)
    box(add(Part(PAPER, 1, name="packing list")), (-3.0, -6.2, 4.8), (1.6, 1.2, 4.86), LID)
    for y in (-8.0, 0.0, 8.0):
        lathe(add(Part(ZINC, 3, name="hinge barrel")), [(0, -1.5), (0.17, -1.5), (0.17, 1.5), (0, 1.5)], 10, frame((PIVOT.x, y, PIVOT.z), (0, 1, 0)))
        box(add(Part(ZINC, 2, bevel=0.012, angle=40, name="hinge leaf")), (-7.2, y - 1.4, 1.5), (-7.12, y + 1.4, 3.0))
        box(add(Part(ZINC, 2, bevel=0.012, angle=40, name="hinge arm")), (-7.55, y - 1.4, 2.95), (-7.1, y + 1.4, 3.05))
        box(add(Part(ZINC, 2, bevel=0.012, angle=40, name="hinge leaf")), (-7.58, y - 1.4, 3.1), (-7.5, y + 1.4, 4.6), LID)
        for dy in (-1.05, 1.05):
            rivet((-7.2, y + dy, 2.1), (-1, 0, 0), 0.1, ZINC)
    # Two stay cables hold it up.
    for side in (-1, 1):
        a = Vector((-1.0, side * 11.55, 2.95))
        b = LID @ Vector((2.5, side * 12.15, 3.7))
        path = spline([a, a.lerp(b, 0.33) + Vector((0, 0, -0.42)), a.lerp(b, 0.66) + Vector((0, 0, -0.34)), b], 3)
        tube(add(Part(ZINC, 1, name="stay cable")), path, 0.05, 5)
        lathe(add(Part(ZINC, 1, name="stay eye")), [(0, 0), (0.14, 0), (0.14, 0.12), (0.07, 0.18), (0, 0.18)], 8, frame(a - Vector((0, 0, 0.06)), (0, 0, 1)))


def magazine(x, y, top, yaw, tilt):
    """A loaded curved rifle magazine standing in the slotted tray; only what shows above the tray is built."""
    z0, zt = -2.2, top
    k = 0.016
    side = lambda z: k * (zt - z) ** 2
    front, back = [], []
    for t in np.linspace(0, 1, 6):
        z = z0 + (zt - z0) * t
        front.append((side(z) + 1.68 - 0.18 * t, z))
        back.append((side(z) - 1.68 + 0.1 * t, z))
    outline = front + [(1.1, zt + 0.2), (-1.1, zt + 0.2), (-1.58, zt - 0.22)] + list(reversed(back[:-1]))
    to_world = (
        Matrix.Translation((x, y, 0))
        @ Matrix.Rotation(yaw, 4, "Z")
        @ Matrix.Rotation(tilt, 4, "X")
        @ Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    )
    prism(add(Part(MAG, 2, bevel=0.035, angle=40, name="magazine")), outline, -0.62, 0.62, to_world)
    # The top round, its tip to the magazine's front.
    frame_round = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(tilt, 4, "X") @ frame((-0.2, 0, zt + 0.25), (1, 0, 0))
    lathe(add(Part(BRASS, 0, name="round")), [(0, -1.05), (0.25, -1.05), (0.25, 0.12), (0.15, 0.36), (0.15, 0.72)], 8, frame_round)
    lathe(add(Part(COPPER, 0, name="tip")), [(0.15, 0.7), (0.12, 1.0), (0.04, 1.25), (0, 1.28)], 8, frame_round)


def contents():
    skip = {(0, 3), (1, 6), (2, 1), (2, 7)}
    for row, x in enumerate((-4.3, -0.05, 4.2)):
        for col, y in enumerate(np.arange(-10.7, 3.6, 1.75)):
            if (row, col) in skip:
                continue
            top = 5.2 + float(rng.uniform(-0.3, 0.3))
            magazine(x, float(y), top, math.radians(float(rng.uniform(-4, 4))), math.radians(float(rng.uniform(-2.2, 2.2))))
    for (x0, x1), top, turn in (((-6.62, -2.3), 3.7, 1.2), ((-2.2, 2.1), 4.25, -1.6), ((2.2, 6.62), 2.95, 0.7)):
        centre = Vector(((x0 + x1) / 2, 8.3, 0))
        m = Matrix.Translation(centre) @ Matrix.Rotation(math.radians(turn), 4, "Z") @ Matrix.Translation(-centre)
        box(add(Part(CARD, 3, bevel=0.02, angle=40, name="carton")), (x0, 5.05, -1.75), (x1, 11.55, top), m)


def geometry():
    body()
    lid()
    for y in (-8.0, 8.0):
        latch(y)
    for side in (-1, 1):
        handle(side)
    contents()


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "ac_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
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

    lod("ac_lod1", 1, 0.55)
    lod("ac_lod2", 2, 0.22)
    with open(os.path.join(WORK, "ammo_case.json"), "w") as h:
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
    hw = bpy.data.objects["ac_lod0"]
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

    bake_one(SIZE, "EMIT", source("pos"), 1, "bake_ac_pos")
    bake_one(SIZE, "EMIT", source("nor"), 1, "bake_ac_nor")
    bake_one(SIZE, "EMIT", source("facts"), 1, "bake_ac_facts")
    bake_one(AO_SIZE, "AO", None, 48, "bake_ac_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["ac_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"ac_lod{lod}"]
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
        with open(os.path.join(out, f"ammo_case_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Zombies/ammo_case_v2/ammo_case.py\nmtllib ammo_case.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl ac_chest\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "ammo_case.mtl"), "w", newline="\n") as h:
        h.write("newmtl ac_chest\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/ammo_case_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 24.0, 70.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Zombies/ammo_case_v2/ammo_case.py
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
							{{ from = "ac_chest.vmat" to = "{MATS}/ac_chest.vmat" }}
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
    with open(os.path.join(out, "ammo_case.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Zombies/ammo_case_v2/ammo_case.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/ac_chest_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/ac_chest_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/ac_chest_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/ac_chest_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/ac_chest_rough.png"
}}
"""
    with open(os.path.join(mats, "ac_chest.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("ammo case stages done", flush=True)
