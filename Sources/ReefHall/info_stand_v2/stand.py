"""Reef Hall's information stand v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python stand.py -- <work dir> <project root> <build|bake|export> ...

A visitor information stand of the size `reefhall_map.lectern` makes, about the same collision box (its post, 16 x 10 x 34): a folded steel column on a rubber kick
and a bolted floor plate, an etched plate on its front and a service door on its back, and a sloped head holding a touch screen behind black glass. The screen is a
second material with the map's own `rh_screen_map` picture and glow, so it lights as the old one did. Its width is along +X and the visitor stands on +Y, on the ground about its origin.
A map yaw of h becomes an engine yaw of h - 90. Inches, engine axes (Z up).
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

from build import Part, add  # noqa: E402

COAT, ZINC = kit.OXIDE, kit.ZINC
RUBBER, GLOSS, PLATE = 12, 13, 14
FOLDER = "models/maps/reefhall/info_stand_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "reefhall", "info_stand_v2")
BLEND = os.path.join(WORK, "stand_build.blend")
NAME = "info_stand"
SCREEN = "info_stand_screen"
RES = 2048
POS_RANGE = 256.0  # The position bake spans this many inches.
HEAD_X = 15.0
LIP = Vector((0.0, 6.8, 33.2))  # The front lip of the head's sloped top.
TOP_BACK = Vector((0.0, -8.6, 44.3))
SLOPE = (TOP_BACK - LIP).normalized()
UP = Vector((0.0, -SLOPE.z, SLOPE.y))
if UP.z < 0:
    UP = -UP
SLOPE_LENGTH = (TOP_BACK - LIP).length
SCREEN_X = 13.0
SCREEN_S = (1.7, 17.3)
SCREEN_T = 0.075
# The inner picture of rh_screen_map_color, cropped to the screen's shape so it isn't stretched as the old one was.
SCREEN_U = (0.085, 0.915)
SCREEN_V = (0.26, 0.758)
screws, edge_lines = [], []


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def rounded(hx, hy, r, segs=3):
    """A rounded rectangle's outline, counter-clockwise."""
    out = []
    for cx, cy, start in ((hx - r, hy - r, 0), (-(hx - r), hy - r, 90), (-(hx - r), -(hy - r), 180), (hx - r, -(hy - r), 270)):
        for k in range(segs + 1):
            a = math.radians(start + 90 * k / segs)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def loft(part, rings):
    """Closed rings of ( outline, z ), climbing, with a cap at each end."""
    bm = part.bm
    made = [[bm.verts.new((x, y, z)) for x, y in outline] for outline, z in rings]
    for a, b in zip(made, made[1:]):
        for k in range(len(a)):
            bm.faces.new((a[k], a[(k + 1) % len(a)], b[(k + 1) % len(a)], b[k]))
    bm.faces.new(list(reversed(made[0])))
    bm.faces.new(list(made[-1]))


def slab(part, corners, normal, thick):
    """Four corners, counter-clockwise from the normal's side, raised along it."""
    bm = part.bm
    low = [bm.verts.new(c) for c in corners]
    high = [bm.verts.new(Vector(c) + normal * thick) for c in corners]
    for k in range(4):
        bm.faces.new((low[k], low[(k + 1) % 4], high[(k + 1) % 4], high[k]))
    bm.faces.new(list(reversed(low)))
    bm.faces.new(list(high))


def extrude_x(part, profile, x0, x1):
    """A ( y, z ) outline, swept from x0 to x1. harden_all sets which way its faces look."""
    bm = part.bm
    a = [bm.verts.new((x0, y, z)) for y, z in profile]
    b = [bm.verts.new((x1, y, z)) for y, z in profile]
    n = len(profile)
    for k in range(n):
        bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(list(b))


def column_half_depth(z):
    return 4.6 + (3.9 - 4.6) * (z - 4.0) / 27.0


def column_half_width(z):
    return 7.6 + (6.7 - 7.6) * (z - 4.0) / 27.0


def foot():
    plate = piece(COAT, 3, bevel=0.07, segs=2, angle=40, name="floor plate")
    loft(plate, [(rounded(12.0, 9.0, 1.1, 3), 0.0), (rounded(12.0, 9.0, 1.1, 3), 0.55)])
    loft(piece(RUBBER, 3, name="shadow gap"), [(rounded(7.2, 4.3, 0.6, 2), 0.5), (rounded(7.2, 4.3, 0.6, 2), 1.7)])
    kick = piece(RUBBER, 3, bevel=0.1, segs=2, angle=40, name="kick")
    loft(kick, [(rounded(7.85, 4.85, 0.75, 3), 1.6), (rounded(7.85, 4.85, 0.75, 3), 4.05)])
    for sx in (-1, 1):
        for sy in (-1, 1):
            kit.hex_bolt((sx * 10.2, sy * 7.2, 0.55), (0, 0, 1), size=0.62, lod=1, washer=True, finish=ZINC)


def column():
    loft(piece(COAT, 3, name="column"), [(rounded(column_half_width(z), column_half_depth(z), 0.7, 3), z) for z in (4.0, 12.0, 22.0, 31.0)])


def on_front(x, z, proud=0.0):
    return Vector((x, column_half_depth(z) + proud, z))


def on_back(x, z, proud=0.0):
    return Vector((x, -column_half_depth(z) - proud, z))


FRONT_NORMAL = Vector((0, 1, 0.7 / 27.0)).normalized()
BACK_NORMAL = Vector((0, -1, 0.7 / 27.0)).normalized()


def plate():
    corners = [on_front(5.0, 14.5), on_front(5.0, 26.5), on_front(-5.0, 26.5), on_front(-5.0, 14.5)]
    slab(piece(PLATE, 1, bevel=0.025, angle=40, name="etched plate"), corners, FRONT_NORMAL, 0.08)
    for x, z in ((4.5, 15.0), (-4.5, 15.0), (4.5, 26.0), (-4.5, 26.0)):
        screws.append(tuple(on_front(x, z) + FRONT_NORMAL * 0.08))


def service_door():
    corners = [on_back(5.2, 6.5), on_back(-5.2, 6.5), on_back(-5.2, 27.5), on_back(5.2, 27.5)]
    slab(piece(COAT, 1, bevel=0.03, angle=40, name="door"), corners, BACK_NORMAL, 0.06)
    for x, z in ((4.7, 7.0), (-4.7, 7.0), (4.7, 27.0), (-4.7, 27.0)):
        screws.append(tuple(on_back(x, z) + BACK_NORMAL * 0.06))
    # Two cam locks, hinges up one side, and a cable gland under it.
    for z in (15.0, 19.0):
        m = kit.frame(on_back(-3.8, z, 0.05), BACK_NORMAL)
        kit.lathe(piece(ZINC, 0, bevel=0.015, angle=45, name="lock"), [(0.42, 0.0), (0.42, 0.1), (0.3, 0.16), (0.0, 0.16)], 12, m)
    for z0, z1 in ((9.0, 11.5), (22.5, 25.0)):
        path = [on_back(5.42, z0, 0.1), on_back(5.42, z1, 0.1)]
        kit.tube(piece(ZINC, 0, name="hinge"), path, 0.17, 8)
    m = kit.frame(on_back(0.0, 5.2, 0.0), BACK_NORMAL)
    kit.lathe(piece(RUBBER, 0, bevel=0.02, angle=45, name="gland"), [(0.52, 0.0), (0.52, 0.28), (0.34, 0.42), (0.0, 0.42)], 10, m)


def head():
    profile = [(6.8, 33.2), (6.4, 31.9), (3.9, 30.4), (-3.9, 30.4), (-8.9, 41.4), (-9.0, 43.9), (-8.6, 44.3)]
    extrude_x(piece(COAT, 3, bevel=0.2, segs=2, angle=25, name="head"), profile, -HEAD_X, HEAD_X)
    # A panel on its back, under the slope, held by four screws.
    d = (Vector((0, -8.9, 41.4)) - Vector((0, -3.9, 30.4))).normalized()
    n = Vector((0, -d.z, d.y))
    if n.y > 0:
        n = -n
    at = Vector((0, -3.9, 30.4))
    corners = [at + d * s + Vector((x, 0, 0)) for s, x in ((2.0, 8.0), (2.0, -8.0), (9.6, -8.0), (9.6, 8.0))]
    slab(piece(COAT, 1, bevel=0.03, angle=40, name="rear panel"), corners, n, 0.05)
    for s, x in ((2.5, 7.5), (2.5, -7.5), (9.1, -7.5), (9.1, 7.5)):
        screws.append(tuple(at + d * s + Vector((x, 0, 0)) + n * 0.05))


def on_slope(x, s, t=0.0):
    return LIP + Vector((x, 0, 0)) + SLOPE * s + UP * t


def screen_housing():
    glass = [on_slope(14.2, 0.7), on_slope(-14.2, 0.7), on_slope(-14.2, 18.3), on_slope(14.2, 18.3)]
    slab(piece(GLOSS, 3, name="glass"), glass, UP, 0.06)
    # A thin steel trim round the glass.
    trim = piece(ZINC, 1, bevel=0.02, angle=40, name="trim")
    x0, x1, s0, s1, w = 14.2, 14.62, 0.28, 18.72, 0.42
    for corners in (
        [on_slope(x1, s0), on_slope(-x1, s0), on_slope(-x1, s0 + w), on_slope(x1, s0 + w)],
        [on_slope(x1, s1 - w), on_slope(-x1, s1 - w), on_slope(-x1, s1), on_slope(x1, s1)],
        [on_slope(x1, s0 + w), on_slope(x0, s0 + w), on_slope(x0, s1 - w), on_slope(x1, s1 - w)],
        [on_slope(-x0, s0 + w), on_slope(-x1, s0 + w), on_slope(-x1, s1 - w), on_slope(-x0, s1 - w)],
    ):
        slab(trim, corners, UP, 0.09)
    for sx in (-1, 1):
        for z, y in ((36.2, -2.4), (41.0, -6.6)):
            screws.append((sx * (HEAD_X + 0.0), y, z))


def geometry():
    foot()
    column()
    plate()
    service_door()
    head()
    screen_housing()


def harden_all():
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish == COAT:
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.15))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "stand_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, RES, 5)
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
    density = RES * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def lod(number, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = f"stand_lod{number}"
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
    lod(2, 3, 0.4)
    np.save(os.path.join(WORK, "stand_edges.npy"), np.array(edge_lines, np.float32))
    np.save(os.path.join(WORK, "stand_screws.npy"), np.array(screws, np.float32))
    with open(os.path.join(WORK, "stand.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE, lip=list(LIP), slope=list(SLOPE), up=list(UP)), h)
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
    hw = bpy.data.objects["stand_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 6.0
    with open(os.path.join(WORK, "stand_baked_uv_hash.txt"), "w") as h:
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_st_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_st_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_st_facts")
    bake_one(1024, "AO", None, 64, "bake_st_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["stand_lod0"]) != open(os.path.join(WORK, "stand_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"stand_lod{number}"]
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

        def index_of(position, texture, normal):
            idx = []
            for table, store, prefix, vec, digits in zip(tables, lines, ("v ", "vt ", "vn "), (position, texture, normal), (5, 6, 5)):
                key = tuple(np.round(vec, digits))
                got = table.get(key)
                if got is None:
                    got = len(table) + 1
                    table[key] = got
                    store.append(prefix + " ".join(f"{x:.{digits}f}" for x in key) + "\n")
                idx.append(got)
            return "%d/%d/%d" % tuple(idx)

        faces = []
        for k in range(n_tris):
            faces.append("f " + " ".join(index_of(p[k * 3 + c], t[k * 3 + c], n[k * 3 + c]) for c in range(3)) + "\n")
        # The screen: the map's own material, one quad, on every LOD. Seen from the visitor's side, +X is on the left of the picture.
        s0, s1 = SCREEN_S
        u0, u1 = SCREEN_U
        v0, v1 = SCREEN_V
        corners = ((SCREEN_X, s0, u0, v0), (-SCREEN_X, s0, u1, v0), (-SCREEN_X, s1, u1, v1), (SCREEN_X, s1, u0, v1))
        up = np.array(UP)[[1, 2, 0]]
        marks = [index_of(np.array(on_slope(x, s, SCREEN_T))[[1, 2, 0]], np.array((u, v)), up) for x, s, u, v in corners]
        screen_faces = [f"f {marks[0]} {marks[1]} {marks[2]}\n", f"f {marks[0]} {marks[2]} {marks[3]}\n"]
        with open(os.path.join(OUT, f"{NAME}_lod{number}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/ReefHall/info_stand_v2/stand.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {NAME}\n")
            h.writelines(faces)
            h.write(f"usemtl {SCREEN}\n")
            h.writelines(screen_faces)
        counts[number] = n_tris + 2
        print("lod", number, "tris", counts[number], flush=True)
    with open(os.path.join(OUT, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\nnewmtl {SCREEN}\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{FOLDER}/{NAME}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 80.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/ReefHall/info_stand_v2/stand.py
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
							{{ from = "{NAME}.vmat" to = "{FOLDER}/{NAME}.vmat" }},
							{{ from = "{SCREEN}.vmat" to = "{FOLDER}/{SCREEN}.vmat" }}
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
    vmat = f"""// Generated by Sources/ReefHall/info_stand_v2/stand.py

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
    # The map's picture and glow, as rh_screen_map has them, on matt anti-glare glass: its own gloss showed the hall's lights as a blown-out spot in the engine.
    screen = f"""// Generated by Sources/ReefHall/info_stand_v2/stand.py
Layer0
{{
	shader "shaders/complex.shader"
	F_SPECULAR 1
	F_SELF_ILLUM 1
	TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"
	g_flSelfIllumBrightness "2.20"
	g_flSelfIllumAlbedoFactor "1.0"
	g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"
	g_flRoughnessScaleFactor "1"
	g_flMetalness "0.00"
	TextureColor "materials/reefhall/rh_screen_map_color.png"
	TextureRoughness "[0.720000 0.720000 0.720000 0.000000]"
	TextureAmbientOcclusion "materials/default/default_ao.tga"
	g_vColorTint "[1.0 1.0 1.0 1.0]"
	g_flModelTintAmount "1.0"
}}
"""
    with open(os.path.join(OUT, f"{SCREEN}.vmat"), "w", newline="\n") as h:
        h.write(screen)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("stand stages done", flush=True)
