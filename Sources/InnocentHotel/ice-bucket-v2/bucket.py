"""Innocent Hotel's ice bucket v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python bucket.py -- <work dir> <project root> <build|bake|export> ...

A proper hotel ice bucket in place of a black tapered cylinder: stitched black vinyl over a steel liner, a rolled brass rim
and base band, brass ring handles on riveted plates, ice standing in melt water. It has the old model's size, origin and
handle axis (Y), so it sits where the old one sits. Inches, engine axes, origin on the counter at the bucket's centre.
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

from build import Part, add, box, frame, lathe, ring_path, tube  # noqa: E402

# Finishes for this model. Facts store them over 16; paint_bucket.py has the same list.
VINYL, BRASS, STEEL, ICE, WATER = 1, 2, 3, 4, 5
MODEL = "models/maps/innocenthotel/ice_bucket_v2"
MATS = "materials/innocenthotel/ice_bucket_v2"
NAME = "ice_bucket"
BLEND = os.path.join(WORK, "bucket_build.blend")
SIDES = 64
WALL_LOW, WALL_HIGH = 1.15, 11.75
WATER_Z = 10.75
HANDLE_Z = 10.45
rng = np.random.default_rng(1971)


def wall_r(z):
    """The vinyl's outer radius: straight taper with the wrap's slight belly."""
    t = (z - WALL_LOW) / (WALL_HIGH - WALL_LOW)
    return 5.06 + 1.14 * t + 0.03 * math.sin(math.pi * t)


def liner_r(z):
    return 5.98 - (12.6 - z) * 0.105


def open_lathe(part, profile, sides=SIDES):
    """A lathe with no end caps: these meet the next finish's rings, and welding closes the shell."""
    lathe(part, profile, sides)
    bm = part.bm
    bm.faces.ensure_lookup_table()
    caps = [f for f in bm.faces if len(f.verts) == sides]
    bmesh.ops.delete(bm, geom=caps, context="FACES_ONLY")


def piping(profile, z, up=0.085, out=0.075):
    r = wall_r(z)
    profile.extend([(wall_r(z - up), z - up), (r + out * 0.8, z - up * 0.5), (r + out, z), (r + out * 0.8, z + up * 0.5), (wall_r(z + up), z + up)])


def shell():
    """One closed skin from the middle of the underside, over the lip, down to the water: four finishes welded at shared rings."""
    base = add(Part(BRASS, 3, name="base band"))
    joint_low = (wall_r(WALL_LOW), WALL_LOW)
    lathe(base, [(0.0, 0.0), (4.55, 0.0), (4.86, 0.06), (5.0, 0.22), (5.03, 0.72), (5.12, 0.82), (5.17, 0.94), (5.14, 1.06), joint_low], SIDES)
    bm = base.bm
    caps = [f for f in bm.faces if len(f.verts) == SIDES]
    bmesh.ops.delete(bm, geom=caps, context="FACES_ONLY")

    wall = [joint_low]
    piping(wall, 1.42)
    for k in range(1, 8):
        z = 1.55 + (11.35 - 1.55) * k / 8
        wall.append((wall_r(z), z))
    piping(wall, 11.45)
    joint_high = (wall_r(WALL_HIGH), WALL_HIGH)
    wall.append(joint_high)
    open_lathe(add(Part(VINYL, 3, name="vinyl wrap")), wall)

    # The rolled rim. A step off the vinyl, a tall band, a bead over the lip.
    rim = [
        joint_high,
        (6.27, 11.78),
        (6.31, 11.84),
        (6.36, 12.62),
        (6.46, 12.72),
        (6.55, 12.88),
        (6.53, 13.04),
        (6.42, 13.15),
        (6.26, 13.17),
        (6.1, 13.12),
        (6.02, 12.98),
        (liner_r(12.6), 12.6),
    ]
    open_lathe(add(Part(BRASS, 3, name="rim")), rim)

    liner = [(liner_r(12.6), 12.6)]
    for z in (12.1, 11.4, WATER_Z):
        liner.append((liner_r(z), z))
    open_lathe(add(Part(STEEL, 3, name="liner")), liner)

    # The melt water is the shell's floor: ice stands in it and hides the rest of the well.
    water = add(Part(WATER, 3, name="water"))
    lathe(water, [(liner_r(WATER_Z), WATER_Z), (liner_r(WATER_Z) * 0.55, WATER_Z), (0.0, WATER_Z)], SIDES)
    bm = water.bm
    caps = [f for f in bm.faces if len(f.verts) == SIDES]
    bmesh.ops.delete(bm, geom=caps, context="FACES_ONLY")


def handle(side, swing):
    """A riveted plate, an eye through its boss, and a ring hanging from the eye. side is +1 or -1 along Y."""
    r = wall_r(HANDLE_Z)
    slope = math.atan2(1.14, WALL_HIGH - WALL_LOW)
    normal = Vector((0, side * math.cos(slope), -math.sin(slope)))
    at = Vector((0, side * (r - 0.03), HANDLE_Z))
    m = frame(at, normal, (1, 0, 0))
    lathe(
        add(Part(BRASS, 2, name="handle plate")),
        [(1.2, -0.04), (1.2, 0.05), (1.1, 0.12), (0.8, 0.18), (0.52, 0.27), (0.36, 0.42), (0.26, 0.5), (0.0, 0.52)],
        28,
        m,
    )
    for sx in (-1, 1):
        rivet = m @ Vector((sx * 0.86, 0, 0.13))
        lathe(add(Part(BRASS, 0, name="rivet")), [(0.13, -0.03), (0.13, 0.02), (0.09, 0.07), (0.0, 0.09)], 8, frame(rivet, normal, (1, 0, 0)))
    eye_c = at + normal * 0.55 + Vector((0, 0, -0.1))
    eye = frame(eye_c, (1, 0, 0), (0, 1, 0))
    tube(add(Part(BRASS, 1, name="handle eye")), ring_path(0.27, 14, eye), 0.075, 7, closed=True)
    # The ring hangs in the plane across the bucket, swung a little off the wall.
    hang = Matrix.Rotation(math.radians(swing), 4, "X")
    top = eye_c + Vector((0, side * 0.03, -0.2))
    centre = top + (hang @ Vector((0, 0, -1.42)))
    ring = frame(centre, hang @ Vector((0, 1, 0)), (1, 0, 0))
    tube(add(Part(BRASS, 3, name="handle ring")), ring_path(1.42, 32, ring), 0.165, 10, closed=True)


def ice():
    """Cubes standing in the water, heaped towards the middle. They are kept off the liner so none pokes through."""
    placed = []
    tries = 0
    while len(placed) < 26 and tries < 1500:
        tries += 1
        size = float(rng.uniform(1.2, 2.05))
        a = float(rng.uniform(0, math.tau))
        dist = float(4.75 * math.sqrt(rng.uniform(0, 1)))
        layer = 1 - dist / 4.75
        z = WATER_Z + 0.1 + 0.75 * size * 0.5 + float(rng.uniform(0, 0.25)) + 1.05 * layer * float(rng.uniform(0.3, 1.0))
        c = Vector((dist * math.cos(a), dist * math.sin(a), z))
        if dist + size * 0.78 > liner_r(z):
            continue
        # A cube can sink into the water or lean on a neighbour, but not sit inside one.
        if any((c - q).length < (size + s) * 0.46 for q, s in placed):
            continue
        placed.append((c, size))
    placed.sort(key=lambda item: -item[1])
    for k, (c, size) in enumerate(placed):
        axis = Vector(rng.normal(size=3)).normalized()
        turn = Matrix.Rotation(float(rng.uniform(0.25, 1.1)), 4, axis)
        m = Matrix.Translation(c) @ turn
        h = size / 2
        squash = float(rng.uniform(0.82, 1.0))
        part = add(Part(ICE, 3 if k < 6 else 2, bevel=0.2, segs=2, angle=40, name="ice"))
        box(part, (-h, -h, -h * squash), (h, h, h * squash), m)
    print("ice cubes", len(placed), flush=True)
    return placed


def melt(part):
    """Melting takes the straightness out of a cube's edges: a slow wobble, different for each."""
    a, b, c = (float(rng.uniform(0, math.tau)) for _ in range(3))
    for v in part.bm.verts:
        x, y, z = v.co
        v.co += Vector((math.sin(2.1 * y + a), math.sin(1.9 * z + b), math.sin(2.4 * x + c))) * 0.075


def geometry():
    shell()
    handle(1, 5.0)
    handle(-1, -3.0)
    return ice()


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    placed = geometry()
    for p in kit.parts:
        kit.harden(p)
        if p.finish == ICE:
            melt(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "bucket_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-4, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, 2048, 6)
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
    density = 2048 * math.sqrt(uva / area3)
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

    lod("bucket_lod1", 1, 0.45)
    lod("bucket_lod2", 3, 0.2)
    with open(os.path.join(WORK, "bucket.json"), "w") as h:
        json.dump(dict(density=density, wall_low=WALL_LOW, wall_high=WALL_HIGH, water=WATER_Z, handle=HANDLE_Z, cubes=[[list(c), s] for c, s in placed]), h)
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
    hw = bpy.data.objects["bucket_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    # The counter it stands on darkens its foot.
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.01))
    bpy.context.object.hide_render = False
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 4.0
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

    bake_one(2048, "EMIT", source("pos"), 1, "bake_bucket_pos")
    bake_one(2048, "EMIT", source("nor"), 1, "bake_bucket_nor")
    bake_one(2048, "EMIT", source("facts"), 1, "bake_bucket_facts")
    bake_one(1024, "AO", None, 32, "bake_bucket_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["bucket_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    bounds = None
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"bucket_lod{lod}"]
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
        if lod == 0:
            bounds = (co.reshape(-1, 3).min(0).tolist(), co.reshape(-1, 3).max(0).tolist())
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
            h.write(f"# Generated by Sources/InnocentHotel/ice-bucket-v2/bucket.py\nmtllib {NAME}.mtl\n")
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
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 80.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/InnocentHotel/ice-bucket-v2/bucket.py
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
    vmat = f"""// Generated by Sources/InnocentHotel/ice-bucket-v2/bucket.py

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
    print("exported", counts, "bounds", bounds, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("bucket stages done", flush=True)
