"""Spillway's yard pallet v2: build, bake and export. Uses the capture flag's mesh toolkit, as Reef Hall's bench does.

blender -b --factory-startup -t 4 --python pallet.py -- <work dir> <project root> <build|bake|export> ...

A used 48 x 40 in stringer pallet: three notched 2x4 stringers along its length, seven top boards (two wide lead boards) and three
bottom boards across them, nailed. Its length is along +X and its width along +Y, standing on the ground about its origin, 4.75 in
tall. The old prop it stands in for was seven flat grey slabs (spillway_map.cargo_yard). Inches, engine axes (Z up).
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
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add  # noqa: E402

PINE, NAIL = 12, kit.ZINC
FOLDER = "models/maps/spillway/pallet_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "spillway", "pallet_v2")
BLEND = os.path.join(WORK, "pallet_build.blend")
NAME = "pallet"
RES = 2048
POS_RANGE = 128.0  # The position bake spans this many inches.
HL, HW = 24.0, 20.0  # Half the length (X) and width (Y).
DECK = 0.625  # Board thickness.
STRINGER_W, STRINGER_H = 1.5, 3.5
BOTTOM = DECK
TOP = DECK + STRINGER_H  # Underside of the top deck.
HEIGHT = TOP + DECK
STRINGERS = (-HW + STRINGER_W / 2, 0.0, HW - STRINGER_W / 2)
NOTCHES = ((-16.0, -7.0), (7.0, 16.0))
rng = np.random.default_rng(4812)
boards, nails, edge_lines = [], [], []


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def around_z(centre, degrees):
    return Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "Z") @ Matrix.Translation([-c for c in centre])


def board(outline, z0, z1, along, centre, turn, name):
    """A board from its plan outline, turned a little about its middle, as boards are never nailed quite square."""
    part = piece(PINE, 3, bevel=0.07, segs=1, angle=40, name=name)
    kit.prism(part, outline, z0, z1, around_z((centre[0], centre[1], 0.0), turn))
    xs, ys = [p[0] for p in outline], [p[1] for p in outline]
    boards.append(dict(name=name, along=along, lo=[min(xs), min(ys), z0], hi=[max(xs), max(ys), z1], centre=list(centre), turn=turn, part=part))
    return part


def deck(xs, widths, z0, z1, label, chipped=None):
    for k, (x, w) in enumerate(zip(xs, widths)):
        w += float(rng.uniform(-0.12, 0.12))
        half = HW + float(rng.uniform(-0.2, 0.15))
        sag = float(rng.uniform(0.0, 0.035))
        x += float(rng.uniform(-0.12, 0.12))
        a, b = x - w / 2, x + w / 2
        outline = [(a, -half), (b, -half), (b, half), (a, half)]
        if chipped == k:
            # A corner split off where a fork tine caught it.
            outline = [(a, -half), (b, -half), (b, half - 2.6), (b - 1.4, half), (a, half)]
        board(outline, z0 - (sag if z0 > 1 else 0.0), z1 - sag, "y", (x, 0.0), float(rng.uniform(-0.45, 0.45)), f"{label} {k}")
        # Two or three nails into each stringer it crosses, a little off line.
        count = 3 if w > 5 else 2
        for y in STRINGERS:
            for j in range(count):
                off = (j - (count - 1) / 2) * (w - 1.3) / max(count - 1, 1)
                nails.append((x + off + float(rng.uniform(-0.15, 0.15)), y + float(rng.uniform(-0.3, 0.3)), z1 - sag if z0 > 1 else 0.0))


def stringer(y, k):
    """A 2x4 along the pallet's length with two fork notches cut from its underside, their ends rounded by the saw."""
    part = piece(PINE, 3, bevel=0.07, segs=1, angle=40, name=f"stringer {k}")
    lo, top, depth, r = BOTTOM, TOP, 1.5, 1.1
    grow = float(rng.uniform(-0.15, 0.15))
    outline = [(-HL - grow, lo)]
    for a, b in NOTCHES:
        outline += [(a - r, lo), (a - r * 0.3, lo + depth * 0.55), (a + r * 0.2, lo + depth), (b - r * 0.2, lo + depth), (b + r * 0.3, lo + depth * 0.55), (b + r, lo)]
    outline += [(HL + grow, lo), (HL + grow, top), (-HL - grow, top)]
    # Local x is the pallet's length, local y is up and local z runs to -Y.
    m = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    kit.prism(part, outline, -y - STRINGER_W / 2, -y + STRINGER_W / 2, m)
    boards.append(dict(name=f"stringer {k}", along="x", lo=[-HL - grow, y - STRINGER_W / 2, lo], hi=[HL + grow, y + STRINGER_W / 2, top], centre=[0.0, y], turn=0.0, part=part))


def geometry():
    for k, y in enumerate(STRINGERS):
        stringer(y, k)
    lead = HL - 2.75
    inner = [-13.5, -6.75, 0.0, 6.75, 13.5]
    deck([-lead] + inner + [lead], [5.5] + [3.5] * 5 + [5.5], TOP, HEIGHT, "top board", chipped=5)
    deck([-lead, 0.0, lead], [5.5, 5.5, 5.5], 0.0, BOTTOM, "bottom board")


def harden_all():
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
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
    hw = kit.join_parts(kit.parts, "pallet_lod0")
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
        copy.name = copy.data.name = f"pallet_lod{number}"
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

    lod(1, 1, 0.5)
    lod(2, 3, 0.2)
    np.save(os.path.join(WORK, "pallet_edges.npy"), np.array(edge_lines, np.float32))
    np.save(os.path.join(WORK, "pallet_nails.npy"), np.array(nails, np.float32))
    record = [dict({k: v for k, v in b.items() if k != "part"}, rand=round(b["part"].rand, 4)) for b in boards]
    with open(os.path.join(WORK, "pallet.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE, half_length=HL, half_width=HW, height=HEIGHT, top=TOP, bottom=BOTTOM, boards=record), h, indent=1)
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
    hw = bpy.data.objects["pallet_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    # The ground it stands on, for the AO bake only: a pallet is darkest where it meets the floor.
    floor = bpy.data.meshes.new("floor")
    floor.from_pydata([(-80, -80, 0), (80, -80, 0), (80, 80, 0), (-80, 80, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("floor", floor)
    scene.collection.objects.link(ground)
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 6.0
    with open(os.path.join(WORK, "pallet_baked_uv_hash.txt"), "w") as h:
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
        ground.hide_render = kind != "AO"
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_pl_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_pl_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_pl_facts")
    bake_one(1024, "AO", None, 64, "bake_pl_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["pallet_lod0"]) != open(os.path.join(WORK, "pallet_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"pallet_lod{number}"]
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
            h.write(f"# Generated by Sources/Spillway/cargo-props-v2/pallet.py\nmtllib {NAME}.mtl\n")
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
    # A pallet is about as big as a crate, so its LODs hold to 30 and 80 (about 15 m and 40 m): see docs/notes on prop distances.
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 80.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Spillway/cargo-props-v2/pallet.py
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
			{{
				_class = "PhysicsShapeList"
				children =
				[
					{{
						_class = "PhysicsShapeBox"
						parent_bone = ""
						surface_prop = "wood"
						collision_tags = "solid"
						origin = [ 0.0000, 0.0000, {HEIGHT / 2:.4f} ]
						angles = [ 0.0000, 0.0000, 0.0000 ]
						dimensions = [ {HL * 2:.4f}, {HW * 2:.4f}, {HEIGHT:.4f} ]
					}},
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
    vmat = f"""// Generated by Sources/Spillway/cargo-props-v2/pallet.py

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
print("pallet stages done", flush=True)
