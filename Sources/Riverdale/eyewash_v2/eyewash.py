"""Riverdale's wall-mounted eye wash v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python eyewash.py -- <work dir> <project root> <build|bake|export> ...

Of the size and in the place `riverdale_hall.eyewash` draws, for the wall it's on: a dished bowl, stainless inside and green outside, on a bolted bracket, twin spray heads under flip-off dust caps,
a brass ball valve with a green push paddle, a green supply riser with clamps, a coupling and a union, and a chrome waste trap into the wall. Its width is along +X, +Y comes out of the wall, and its origin
is on the floor at the wall. It has no collision, as the old one had none. Its sign stays in the map's model. Inches, engine axes (Z up).
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

COAT, ZINC, BRASS = kit.OXIDE, kit.ZINC, kit.BRASS
BOWL, CAP = 13, 14
FOLDER = "models/maps/riverdale/eyewash_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "riverdale", "eyewash_v2")
BLEND = os.path.join(WORK, "eyewash_build.blend")
NAME = "eyewash"
RES = 2048
POS_RANGE = 128.0  # The position bake spans this many inches.
BOWL_Y = 7.0
RISER_X, RISER_Y = 4.4, 1.7
VALVE_Z = 31.6
screws, edge_lines = [], []


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def rounded_path(points, radius, segs=6):
    """A polyline with its corners filleted: pipe bends, not kinks."""
    pts = [Vector(p) for p in points]
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        u, v = (a - b).normalized(), (c - b).normalized()
        turn = u.angle(v)
        back = min(radius / max(math.tan(turn / 2), 1e-4), (a - b).length * 0.49, (c - b).length * 0.49)
        p0, p2 = b + u * back, b + v * back
        for k in range(segs + 1):
            t = k / segs
            out.append((p0 * (1 - t) ** 2) + (b * 2 * t * (1 - t)) + (p2 * t * t))
    out.append(pts[-1])
    return out


def rounded_outline(hx, hy, r, segs=4):
    out = []
    for cx, cy, start in ((hx - r, hy - r, 0), (-(hx - r), hy - r, 90), (-(hx - r), -(hy - r), 180), (hx - r, -(hy - r), 270)):
        for k in range(segs + 1):
            a = math.radians(start + 90 * k / segs)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def extrude_x(part, profile, x0, x1):
    """A ( y, z ) outline swept from x0 to x1. harden_all sets which way its faces look."""
    bm = part.bm
    a = [bm.verts.new((x0, y, z)) for y, z in profile]
    b = [bm.verts.new((x1, y, z)) for y, z in profile]
    n = len(profile)
    for k in range(n):
        bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(list(b))


def bowl():
    """One closed turning: its outside is painted green and its inside left as spun stainless, which the paint tells apart by which way a face looks."""
    profile = [(1.25, 33.5), (1.4, 34.2), (2.8, 34.55), (4.2, 35.2), (5.4, 36.2), (6.0, 37.0), (6.12, 37.3), (6.05, 37.55), (5.8, 37.6), (5.55, 37.4), (5.0, 36.6), (3.8, 35.75), (2.2, 35.25), (1.0, 35.05), (0.0, 35.02)]
    kit.lathe(piece(BOWL, 3, name="bowl"), profile, 32, kit.frame((0, BOWL_Y, 0)))
    kit.lathe(piece(ZINC, 1, name="strainer"), [(1.02, 35.0), (1.04, 35.1), (0.92, 35.17), (0.0, 35.17)], 16, kit.frame((0, BOWL_Y, 0)))


def bracket():
    corners = [(3.4, 0.0, 31.8), (-3.4, 0.0, 31.8), (-3.4, 0.0, 38.2), (3.4, 0.0, 38.2)]
    plate = piece(COAT, 3, bevel=0.03, angle=40, name="back plate")
    bm = plate.bm
    low = [bm.verts.new(c) for c in corners]
    high = [bm.verts.new((c[0], 0.14, c[2])) for c in corners]
    for k in range(4):
        bm.faces.new((low[k], low[(k + 1) % 4], high[(k + 1) % 4], high[k]))
    bm.faces.new(list(reversed(low)))
    bm.faces.new(list(high))
    for x in (-2.85, 2.85):
        for z in (32.4, 37.6):
            kit.hex_bolt((x, 0.14, z), (0, 1, 0), size=0.46, lod=1, washer=True, finish=ZINC)
        extrude_x(piece(COAT, 1, bevel=0.02, angle=40, name="gusset"), [(0.14, 32.6), (0.14, 36.6), (1.5, 36.2), (3.8, 35.0), (3.8, 34.5)], x * 0.72 - 0.12, x * 0.72 + 0.12)


def waste():
    path = rounded_path([(0, BOWL_Y, 33.6), (0, BOWL_Y, 28.6), (0, 0.1, 28.6)], 1.7)
    kit.tube(piece(ZINC, 3, name="tailpiece"), path, 0.6, 12)
    kit.lathe(piece(ZINC, 1, bevel=0.03, angle=40, name="slip nut"), [(0.62, 32.1), (0.86, 32.15), (0.86, 32.8), (0.62, 32.85)], 12, kit.frame((0, BOWL_Y, 0)))
    kit.lathe(piece(ZINC, 1, name="escutcheon"), [(1.7, 0.0), (1.7, 0.1), (1.3, 0.2), (0.75, 0.42), (0.6, 0.42)], 20, kit.frame((0, 0, 28.6), (0, 1, 0)))


def clamp(z):
    bm_tab = piece(ZINC, 1, bevel=0.015, angle=40, name="clamp tab")
    kit.box(bm_tab, (RISER_X - 1.5, 0.0, z), (RISER_X + 1.5, 0.12, z + 0.72))
    kit.box(bm_tab, (RISER_X - 0.36, 0.1, z), (RISER_X + 0.36, RISER_Y, z + 0.72))
    kit.lathe(piece(ZINC, 1, bevel=0.015, angle=40, name="clamp band"), [(0.6, z), (0.74, z), (0.74, z + 0.72), (0.6, z + 0.72)], 14, kit.frame((RISER_X, RISER_Y, 0)))
    for sx in (-1, 1):
        screws.append((RISER_X + sx * 1.14, 0.12, z + 0.36))


def supply():
    path = rounded_path([(RISER_X, 0.1, 7.0), (RISER_X, RISER_Y, 7.0), (RISER_X, RISER_Y, VALVE_Z), (RISER_X, 5.1, VALVE_Z)], 1.0)
    kit.tube(piece(COAT, 3, name="riser"), path, 0.6, 12)
    kit.lathe(piece(ZINC, 1, name="escutcheon"), [(1.5, 0.0), (1.5, 0.1), (1.1, 0.2), (0.72, 0.38), (0.6, 0.38)], 18, kit.frame((RISER_X, 0, 7.0), (0, 1, 0)))
    at = kit.frame((RISER_X, RISER_Y, 0))
    kit.lathe(piece(COAT, 1, bevel=0.02, angle=40, name="coupling"), [(0.6, 18.3), (0.84, 18.4), (0.84, 19.6), (0.6, 19.7)], 14, at)
    kit.lathe(piece(BRASS, 1, bevel=0.04, angle=40, name="union nut"), [(0.62, 26.4), (0.98, 26.5), (0.98, 27.5), (0.62, 27.6)], 6, at)
    kit.lathe(piece(BRASS, 1, bevel=0.02, angle=40, name="union collar"), [(0.62, 27.6), (0.78, 27.65), (0.78, 28.1), (0.62, 28.15)], 14, at)
    clamp(12.0)
    clamp(23.5)


def valve():
    """A two-piece brass ball valve, the push paddle on its stem."""
    body = kit.frame((RISER_X, 5.0, VALVE_Z), (0, 1, 0))
    kit.lathe(piece(BRASS, 3, name="valve body"), [(0.62, 0.0), (0.86, 0.1), (0.86, 0.5), (1.2, 0.75), (1.2, 1.65), (0.86, 1.9), (0.86, 2.3), (0.62, 2.4)], 18, body)
    top = kit.frame((RISER_X, 6.2, VALVE_Z + 1.1))
    kit.lathe(piece(BRASS, 1, name="stem"), [(0.3, 0.0), (0.3, 0.42), (0.0, 0.42)], 10, top)
    kit.lathe(piece(ZINC, 0, bevel=0.015, angle=40, name="stem nut"), [(0.38, 0.42), (0.38, 0.62), (0.0, 0.62)], 6, top)
    # The paddle's lever, then the paddle itself, out to the side where a hand finds it.
    lever = piece(ZINC, 1, bevel=0.03, angle=40, name="lever")
    kit.box(lever, (RISER_X - 0.4, 5.92, VALVE_Z + 1.35), (RISER_X + 3.6, 6.48, VALVE_Z + 1.62))
    kit.box(lever, (RISER_X + 3.0, 5.92, VALVE_Z + 0.6), (RISER_X + 3.6, 6.48, VALVE_Z + 1.62))
    frame = kit.frame((RISER_X + 3.3, 6.48, VALVE_Z - 0.5), (0, 1, 0), x=(1, 0, 0))
    kit.prism(piece(COAT, 3, bevel=0.06, segs=2, angle=40, name="paddle"), rounded_outline(1.7, 2.6, 0.5), 0.0, 0.28, frame)


def heads():
    outlet = rounded_path([(RISER_X, 7.3, VALVE_Z), (RISER_X, 8.7, VALVE_Z), (RISER_X, 8.7, 33.2), (-2.4, 8.7, 33.2)], 0.8)
    kit.tube(piece(ZINC, 3, name="manifold"), outlet, 0.42, 10)
    for x in (-2.4, 2.4):
        side = 1.0 if x > 0 else -1.0
        kit.tube(piece(ZINC, 3, name="head stem"), [(x, 8.7, 33.0), (x, 8.7, 37.7)], 0.3, 10)
        at = kit.frame((x, 8.7, 0))
        kit.lathe(piece(ZINC, 3, name="spray head"), [(0.3, 37.7), (0.42, 37.75), (0.66, 38.1), (0.66, 38.35), (0.58, 38.42), (0.0, 38.42)], 16, at)
        kit.lathe(piece(CAP, 3, name="dust cap"), [(0.72, 38.22), (0.77, 38.4), (0.7, 38.85), (0.45, 39.05), (0.0, 39.1)], 16, at)
        strap = rounded_path([(x + side * 0.72, 8.7, 38.3), (x + side * 1.05, 8.7, 37.6), (x + side * 0.3, 8.7, 37.05)], 0.3, 4)
        kit.tube(piece(CAP, 0, name="cap strap"), strap, 0.055, 6)


def geometry():
    bowl()
    bracket()
    waste()
    supply()
    valve()
    heads()


def harden_all():
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in (COAT, BOWL):
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
    hw = kit.join_parts(kit.parts, "eyewash_lod0")
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
        copy.name = copy.data.name = f"eyewash_lod{number}"
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
    lod(2, 3, 0.3)
    np.save(os.path.join(WORK, "eyewash_edges.npy"), np.array(edge_lines, np.float32))
    np.save(os.path.join(WORK, "eyewash_screws.npy"), np.array(screws, np.float32))
    with open(os.path.join(WORK, "eyewash.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE, bowl_y=BOWL_Y, valve_z=VALVE_Z, riser_x=RISER_X), h)
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
    hw = bpy.data.objects["eyewash_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 6.0
    with open(os.path.join(WORK, "eyewash_baked_uv_hash.txt"), "w") as h:
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_ew_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_ew_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_ew_facts")
    bake_one(1024, "AO", None, 64, "bake_ew_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["eyewash_lod0"]) != open(os.path.join(WORK, "eyewash_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"eyewash_lod{number}"]
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
        with open(os.path.join(OUT, f"{NAME}_lod{number}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/Riverdale/eyewash_v2/eyewash.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {NAME}\n")
            h.writelines(faces)
        counts[number] = n_tris
        print("lod", number, "tris", counts[number], flush=True)
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
// Generated by Sources/Riverdale/eyewash_v2/eyewash.py
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
    vmat = f"""// Generated by Sources/Riverdale/eyewash_v2/eyewash.py

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
print("eye wash stages done", flush=True)
