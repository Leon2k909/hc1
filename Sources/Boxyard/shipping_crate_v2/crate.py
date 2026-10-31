"""Boxyard's shipping crate v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python crate.py -- <work dir> <project root> <standard|large> <build|bake|export> ...

The sizes `railhead_props.crate` makes for Boxyard, and the same collision box round each, but built as a crate is: boards with gaps
between them, a frame of battens lapped at the corners with a diagonal brace on each long side, skids, steel strapping and a
handle at each end. Its length is along +X, standing on the ground about its origin. Inches, engine axes (Z up).
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
WORK, ROOT, VARIANT = argv[0], argv[1], argv[2]
STAGES = argv[3:]
WORK = os.path.join(WORK, VARIANT)
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, frame, tube  # noqa: E402

OXIDE = kit.OXIDE
BRACE, WOOD_X, WOOD_Y, WOOD_Z, DARK = 10, 11, 12, 13, 15
FOLDER = "models/maps/boxyard/shipping_crate_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "boxyard", "shipping_crate_v2")
BLEND = os.path.join(WORK, "crate_build.blend")
NAME = f"crate_{VARIANT}"
LENGTH, WIDTH, HEIGHT = {"standard": (47.2, 31.5, 31.5), "large": (60.0, 48.0, 48.0)}[VARIANT]
HL, HW = LENGTH / 2, WIDTH / 2
RES = 2048
POS_RANGE = 192.0  # The position bake spans this many inches.
SKID = 2.4
BATTEN = 3.5
T = 0.8
BOARD = 0.75
rng = np.random.default_rng(4471 if VARIANT == "standard" else 4472)
edge_lines, nails = [], []


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def plank(finish, lod, lo, hi, bevel=0.035, name="board", hide=()):
    """A box with the faces no one can see left off, which saves their texture space. hide: axis and sign, as (0, -1) for its -X face."""
    part = piece(finish, lod, bevel=bevel, angle=40, name=name)
    kit.box(part, lo, hi)
    part.bm.normal_update()
    bmesh.ops.recalc_face_normals(part.bm, faces=part.bm.faces)
    drop = [f for f in part.bm.faces for axis, sign in hide if f.normal[axis] * sign > 0.9]
    if drop:
        bmesh.ops.delete(part.bm, geom=drop, context="FACES")
    return part


def nail_row(a, b, count):
    a, b = Vector(a), Vector(b)
    for k in range(count):
        nails.append(tuple(a.lerp(b, (k + 0.5) / count)))


def core():
    """Behind the gaps. It's first, so its eight vertices can be shrunk while the atlas is packed: it needs no texture space to speak of."""
    kit.box(piece(DARK, 3, name="core"), (-(HL - 1.9), -(HW - 1.9), SKID + 0.2), (HL - 1.9, HW - 1.9, HEIGHT - 1.9))


def boards():
    """Only as far under the frame as a board's edge can be seen: what's behind a batten would only take texture space."""
    b_ = BATTEN - 0.3
    z0, z1 = SKID + b_, HEIGHT - b_
    count = max(3, int(round((z1 - z0) / 5.6)))
    gap = 0.16
    tall = ((z1 - z0) - gap * (count - 1)) / count
    # The long sides: boards along the crate. The ends: boards across it.
    for side in (-1, 1):
        for k in range(count):
            a = z0 + k * (tall + gap) + float(rng.uniform(-0.04, 0.04))
            b = a + tall + float(rng.uniform(-0.06, 0.05))
            drift = float(rng.uniform(-0.03, 0.03))
            y0, y1 = sorted((side * (HW - T - BOARD + drift), side * (HW - T - 0.04 + drift)))
            plank(WOOD_X, 3, (-(HL - b_), y0, a), (HL - b_, y1, b), hide=((1, -side), (0, 1), (0, -1)))
        for k in range(count):
            a = z0 + k * (tall + gap) + float(rng.uniform(-0.04, 0.04))
            b = a + tall + float(rng.uniform(-0.06, 0.05))
            drift = float(rng.uniform(-0.03, 0.03))
            x0, x1 = sorted((side * (HL - T - BOARD + drift), side * (HL - T - 0.04 + drift)))
            plank(WOOD_Y, 3, (x0, -(HW - T - b_), a), (x1, HW - T - b_, b), hide=((0, -side), (1, 1), (1, -1)))
    # The lid: boards along the crate.
    across = max(3, int(round((WIDTH - 2 * b_) / 5.6)))
    wide = (WIDTH - 2 * b_ - gap * (across - 1)) / across
    for k in range(across):
        a = -(HW - b_) + k * (wide + gap)
        b = a + wide + float(rng.uniform(-0.05, 0.03))
        top = HEIGHT - T - 0.04 + float(rng.uniform(-0.03, 0.03))
        plank(WOOD_X, 3, (-(HL - b_), a, top - BOARD), (HL - b_, b, top), hide=((2, -1), (0, 1), (0, -1)))


def frame_battens():
    """Lapped, as a crate is nailed up, so no two battens share a face: the long sides' battens run the full length, the ends' fit between
    them, and the lid's frame sits on top of all of it. A shared face bakes fully occluded and shows through as a black line."""
    b, t, h = BATTEN, T, HEIGHT
    rails = (SKID, h - t - b)
    for side in (-1, 1):
        y0, y1 = sorted((side * HW, side * (HW - t)))
        x0, x1 = sorted((side * HL, side * (HL - t)))
        for z in rails:
            plank(WOOD_X, 3, (-HL, y0, z), (HL, y1, z + b), 0.06, "rail", hide=((1, -side),))
            nail_row((-HL, side * HW, z + b / 2), (HL, side * HW, z + b / 2), int(LENGTH / 4.8))
            plank(WOOD_Y, 3, (x0, -(HW - t), z), (x1, HW - t, z + b), 0.06, "rail", hide=((0, -side), (1, 1), (1, -1)))
            nail_row((side * HL, -(HW - t), z + b / 2), (side * HL, HW - t, z + b / 2), int(WIDTH / 4.8))
        # Corner posts between the rails.
        post0, post1 = SKID + b, h - t - b
        for end in (-1, 1):
            xa, xb = sorted((end * HL, end * (HL - b)))
            plank(WOOD_Z, 3, (xa, y0, post0), (xb, y1, post1), 0.06, "post", hide=((1, -side), (2, 1), (2, -1)))
            nail_row((end * (HL - b / 2), side * HW, post0), (end * (HL - b / 2), side * HW, post1), max(2, int(h / 7.5)))
            ya, yb = sorted((end * (HW - t), end * (HW - t - b)))
            plank(WOOD_Z, 2, (x0, ya, post0), (x1, yb, post1), 0.06, "post", hide=((0, -side), (1, end), (2, 1), (2, -1)))
        # The lid's frame: rails along the long sides, full length, and between them across the ends.
        ya, yb = sorted((side * HW, side * (HW - b)))
        plank(WOOD_X, 3, (-HL, ya, h - t), (HL, yb, h), 0.06, "lid rail", hide=((2, -1),))
        nail_row((-HL, side * (HW - b / 2), h), (HL, side * (HW - b / 2), h), int(LENGTH / 4.8))
        xa, xb = sorted((side * HL, side * (HL - b)))
        plank(WOOD_Y, 2, (xa, -(HW - b), h - t), (xb, HW - b, h), 0.06, "lid rail", hide=((2, -1), (1, 1), (1, -1)))


def braces():
    """Set just behind the frame's face, so its ends tuck behind the rails and posts rather than sharing their faces."""
    run, rise = 2 * HL - 2 * BATTEN, HEIGHT - T - SKID - 2 * BATTEN
    angle = math.atan2(rise, run)
    span = math.hypot(run, rise) + 1.0
    for side in (-1, 1):
        m = frame((0.0, side * (HW - T), SKID + BATTEN + rise / 2), (0, side, 0), (math.cos(angle), 0, math.sin(angle)))
        part = piece(BRACE, 3, bevel=0.06, angle=40, name="brace")
        kit.box(part, (-span / 2, -BATTEN / 2, -0.05), (span / 2, BATTEN / 2, T - 0.05), m)
        ends = [Vector(p) for p in (m @ Vector((-span / 2 + 3, 0, T)), m @ Vector((span / 2 - 3, 0, T)))]
        nail_row(ends[0], ends[1], max(3, int(span / 7.5)))
    return angle


def skids():
    for y in (-(HW * 0.62), HW * 0.62):
        plank(WOOD_X, 2, (-HL, y - 1.75, 0.0), (HL, y + 1.75, SKID - 0.02), 0.08, "skid", hide=((2, -1),))


def strapping():
    """Steel bands over the lid and down both long sides, with a seal where each one's ends are joined."""
    h, w, proud = HEIGHT, 0.38, 0.05
    for x in (-(HL * 0.56), HL * 0.56):
        strap = piece(OXIDE, 2, bevel=0.012, angle=40, name="strap").bm
        loop = [(-(HW + proud), SKID + 0.4), (-(HW + proud), h + proud), (HW + proud, h + proud), (HW + proud, SKID + 0.4), (HW, SKID + 0.4), (HW, h), (-HW, h), (-HW, SKID + 0.4)]
        a = [strap.verts.new((x - w, y, z)) for y, z in loop]
        b = [strap.verts.new((x + w, y, z)) for y, z in loop]
        n = len(loop)
        for k in range(n):
            strap.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
        strap.faces.new(a)
        strap.faces.new(b)
        kit.box(piece(OXIDE, 1, bevel=0.02, angle=40, name="seal"), (x - w * 1.25, 3.6, h + proud), (x + w * 1.25, 5.0, h + proud + 0.13))


def handles():
    z = HEIGHT * 0.62
    for side in (-1, 1):
        reach = 0.95
        path = [(side * (HL - 0.1), -4.4, z), (side * (HL + reach * 0.8), -4.2, z), (side * (HL + reach), -3.2, z), (side * (HL + reach), 3.2, z), (side * (HL + reach * 0.8), 4.2, z), (side * (HL - 0.1), 4.4, z)]
        tube(piece(OXIDE, 2, name="handle"), kit.spline(path, 2), 0.3, 8)
        for y in (-4.4, 4.4):
            xa, xb = sorted((side * HL, side * (HL + 0.12)))
            plank(OXIDE, 1, (xa, y - 0.8, z - 1.1), (xb, y + 0.8, z + 1.1), 0.02, "plate", hide=((0, -side),))


def geometry():
    core()
    boards()
    frame_battens()
    angle = braces()
    skids()
    strapping()
    handles()
    return angle


def harden_all():
    """Settle each part's winding, note its convex edges for the wear, then bevel it."""
    for p in kit.parts:
        bm = p.bm
        # Parts with faces left off are open, so their winding was settled before the faces went.
        if all(len(e.link_faces) == 2 for e in bm.edges):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in (WOOD_X, WOOD_Y, WOOD_Z, BRACE):
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.2))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    angle = geometry()
    harden_all()
    print("parts", len(kit.parts), "nails", len(nails), flush=True)
    hw = kit.join_parts(kit.parts, "crate_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    # The core goes small while the atlas is laid out, so it takes hardly any of it, and back afterwards.
    mesh = hw.data
    kept = [v.co.copy() for v in mesh.vertices[:8]]
    centre = sum(kept, Vector()) / 8
    for v, co in zip(mesh.vertices[:8], kept):
        v.co = centre + (co - centre) * 0.02
    kit.pack_real_scale(mesh, RES, 5)
    for v, co in zip(mesh.vertices[:8], kept):
        v.co = co
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mesh.calc_loop_triangles()
    area3 = uva = 0.0
    core_verts = set(range(8))
    for tri in mesh.loop_triangles:
        if tri.vertices[0] in core_verts:
            continue
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
        copy.name = copy.data.name = f"crate_lod{number}"
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
    np.save(os.path.join(WORK, "crate_edges.npy"), np.array(edge_lines, np.float32))
    np.save(os.path.join(WORK, "crate_nails.npy"), np.array(nails, np.float32))
    with open(os.path.join(WORK, "crate.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE, length=LENGTH, width=WIDTH, height=HEIGHT, skid=SKID, batten=BATTEN, brace=angle, variant=VARIANT), h)
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
    hw = bpy.data.objects["crate_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 6.0
    with open(os.path.join(WORK, "crate_baked_uv_hash.txt"), "w") as h:
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_cr_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_cr_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_cr_facts")
    bake_one(1024, "AO", None, 64, "bake_cr_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["crate_lod0"]) != open(os.path.join(WORK, "crate_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"crate_lod{number}"]
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
            h.write(f"# Generated by Sources/Boxyard/shipping_crate_v2/crate.py\nmtllib {NAME}.mtl\n")
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
// Generated by Sources/Boxyard/shipping_crate_v2/crate.py
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
    vmat = f"""// Generated by Sources/Boxyard/shipping_crate_v2/crate.py

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
print("crate stages done", flush=True)
