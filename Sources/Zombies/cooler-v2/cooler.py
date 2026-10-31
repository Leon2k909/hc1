"""Riverside's cooler v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python cooler.py -- <work dir> <project root> <build|bake|export> ...

The old cooler (Tools/riverside_parts.py, cooler) is three boxes and four cans by the dog run's gate, in the reference picture
with SOME THINGS SHOULD STAY FORGOTTEN in marker inside its lid. This is a real moulded ice chest: rounded and drafted walls
with a band round them, a hollow liner, a hollow lid hinged open at the same angle, swing handles, a drain plug, keepers for its
latches, and cans floating in old meltwater. The lid keeps the picture's lettering in the same hand.

Same footprint, height and lid angle as the old one. Inches, engine axes: origin on the ground under its middle, its length
along x and its open side +y. The one on the map is turned to suit when it's placed.
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
sys.path.insert(0, os.path.join(ROOT, "Sources", "Zombies", "burn-drum-v2"))
import build as kit  # noqa: E402
from drum_pack import pack_weighted  # noqa: E402

from build import Part, add, box, frame, lathe, spline, tube  # noqa: E402

BODY, LID, WATER, CAN, STEEL, RUBBER, ICE = range(7)
NAME = "cooler"
MODEL = "models/zombies/cooler_v2"
MATS = "materials/zombies/cooler_v2"
BLEND = os.path.join(WORK, "cooler_build.blend")

HINGE_Y, HINGE_Z = -8.45, 16.0
LID_DEG = 105.0
LID_M = Matrix.Translation((0, HINGE_Y, HINGE_Z)) @ Matrix.Rotation(math.radians(LID_DEG), 4, "X") @ Matrix.Translation((0, -HINGE_Y, -HINGE_Z))
WATER_Z = 9.6


def rounded(hx, hy, r, z, seg=4):
    """A counter-clockwise rounded rectangle, the same number of points whatever its size."""
    pts = []
    for cx, cy, start in ((hx - r, -(hy - r), -90), (hx - r, hy - r, 0), (-(hx - r), hy - r, 90), (-(hx - r), -(hy - r), 180)):
        for k in range(seg + 1):
            a = math.radians(start + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    return pts


def stack(part, rows, start_z, end_z, m=Matrix.Identity(4)):
    """Rings in order, closed with a fan at each end: faces point out for rings climbing the outside."""
    bm = part.bm
    rings = [[bm.verts.new(m @ Vector(p)) for p in rounded(*row)] for row in rows]
    n = len(rings[0])
    first = bm.verts.new(m @ Vector((0, 0, start_z)))
    last = bm.verts.new(m @ Vector((0, 0, end_z)))
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((a[k], a[j], b[j], b[k]))
    for k in range(n):
        j = (k + 1) % n
        bm.faces.new((first, rings[0][j], rings[0][k]))
        bm.faces.new((rings[-1][k], rings[-1][j], last))


def body():
    # Half length, half width, corner radius, height: the outside climbing, over the rim, then the liner going down.
    rows = [
        (14.6, 7.1, 1.2, 0.0),
        (15.3, 7.8, 1.5, 0.06),
        (15.55, 8.05, 1.6, 0.5),
        (15.6, 8.1, 1.6, 2.3),
        (15.75, 8.25, 1.7, 2.55),
        (15.75, 8.25, 1.7, 5.6),
        (15.62, 8.12, 1.65, 5.85),
        (15.72, 8.22, 1.7, 11.4),
        (15.95, 8.45, 1.85, 11.7),
        (16.0, 8.5, 1.9, 15.4),
        (15.9, 8.4, 1.85, 15.95),
        (15.6, 8.1, 1.7, 16.0),
        (14.6, 7.1, 1.3, 15.9),
        (14.4, 6.9, 1.2, 15.2),
        (14.0, 6.5, 1.0, 2.6),
        (13.7, 6.2, 0.8, 2.2),
    ]
    stack(add(Part(BODY, 3, name="body")), rows, -0.0, 2.2)
    # Swing handles at the ends, on two bosses each.
    for s in (-1, 1):
        for y in (-3.6, 3.6):
            lathe(add(Part(RUBBER, 2, name="handle boss")), [(0, 0.0), (0.62, 0.0), (0.62, 0.3), (0.42, 0.42), (0, 0.42)], 8, frame((s * 15.96, y, 13.0), (s, 0, 0)))
        path = spline([(s * 16.12, -3.6, 13.0), (s * 16.26, -3.5, 11.4), (s * 16.28, -2.4, 10.2), (s * 16.28, 2.4, 10.2), (s * 16.26, 3.5, 11.4), (s * 16.12, 3.6, 13.0)], 3)
        tube(add(Part(RUBBER, 2, name="handle")), path, 0.26, 8)
    # The drain plug, low on one end.
    lathe(add(Part(RUBBER, 1, name="drain boss")), [(0, 0.0), (0.88, 0.0), (0.88, 0.2), (0.62, 0.3), (0, 0.3)], 12, frame((15.72, 4.6, 1.5), (1, 0, 0)))
    lathe(add(Part(RUBBER, 0, name="drain plug")), [(0, 0.0), (0.5, 0.0), (0.5, 0.26), (0, 0.32)], 6, frame((16.0, 4.6, 1.5), (1, 0, 0)))
    # Latch keepers on the front, their straps hanging off the open lid.
    for x in (-9.5, 9.5):
        box(add(Part(RUBBER, 2, bevel=0.07, name="keeper")), (x - 1.05, 8.4, 13.1), (x + 1.05, 8.78, 15.1))
        box(add(Part(RUBBER, 1, bevel=0.05, name="strap")), (x - 0.82, 8.42, 16.6), (x + 0.82, 8.68, 18.0), LID_M)
    # Hinges along the back.
    for x in (-9.0, 9.0):
        box(add(Part(LID, 2, bevel=0.06, name="hinge block")), (x - 1.0, -8.72, 14.5), (x + 1.0, -8.42, 16.0))
        box(add(Part(LID, 2, bevel=0.06, name="hinge block")), (x - 1.0, -8.72, 16.05), (x + 1.0, -8.42, 17.4), LID_M)
        lathe(add(Part(STEEL, 1, name="hinge pin")), [(0, -1.3), (0.26, -1.3), (0.26, 1.3), (0, 1.3)], 8, frame((x, HINGE_Y - 0.1, HINGE_Z), (1, 0, 0)))


def lid():
    rows = [
        (14.2, 6.7, 1.1, 16.55),
        (14.3, 6.8, 1.1, 16.18),
        (15.0, 7.5, 1.4, 16.14),
        (15.75, 8.25, 1.8, 16.05),
        (15.95, 8.45, 1.9, 16.35),
        (15.95, 8.45, 1.9, 17.7),
        (15.7, 8.2, 1.75, 18.25),
        (14.4, 6.9, 1.2, 18.4),
    ]
    stack(add(Part(LID, 3, name="lid")), rows, 16.55, 18.45, LID_M)


def contents():
    # Old meltwater, as a slab whose edges are hidden in the liner's walls.
    stack(add(Part(WATER, 3, name="meltwater")), [(14.2, 6.72, 1.1, WATER_Z - 0.4), (14.2, 6.72, 1.1, WATER_Z)], WATER_Z - 0.4, WATER_Z)
    cans = []
    profile = [(0, 0.0), (1.05, 0.0), (1.28, 0.3), (1.28, 4.3), (1.05, 4.7), (1.02, 4.8), (0.9, 4.72), (0, 4.68)]
    # At, axis: bobbing at an angle, or lying half under, each low enough to float.
    placed = (
        ((-9.4, -2.2, 8.4), (0.2, 0.25, 1.0), "red"),
        ((-3.2, 3.4, 10.0), (0.95, 0.2, 0.2), "alu"),
        ((2.4, -3.2, 8.6), (-0.42, 0.1, 0.9), "red"),
        ((7.6, 3.0, 9.9), (-0.8, -0.55, 0.15), "alu"),
        ((10.8, -3.6, 8.5), (0.1, -0.35, 0.95), "red"),
    )
    for at, axis, kind in placed:
        part = add(Part(CAN, 1, name=f"can {kind}"))
        lathe(part, profile, 12, frame(at, axis))
        cans.append((part, at, axis, kind))
    return cans


def weight_of(face, facts):
    """How much texture a face gets, as a multiple of the real size. The lid's underside carries the lettering."""
    finish = int(round(face.loops[0][facts][0] * 16))
    n = face.normal
    c = face.calc_center_median()
    if finish == BODY:
        if c.z < 0.2:
            return 0.06
        if abs(c.x) < 14.8 and abs(c.y) < 7.3:
            return 0.65 if c.z > WATER_Z else 0.05
        return 1.0
    if finish == LID:
        # With the lid open its underside faces +y and up.
        return 1.5 if (n.y > 0.5 and n.z > 0.0) else 0.7
    return {WATER: 0.6, CAN: 1.0, STEEL: 0.5, RUBBER: 0.75, ICE: 0.7}[finish]


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body()
    lid()
    cans = contents()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "cooler_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    density = pack_weighted(hw.data, weight_of)
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

    lod("cooler_lod1", 1, 0.6)
    lod("cooler_lod2", 3, 0.6)
    with open(os.path.join(WORK, "cooler.json"), "w") as h:
        json.dump(
            dict(
                density=density,
                hinge=(HINGE_Y, HINGE_Z),
                lid_deg=LID_DEG,
                water_z=WATER_Z,
                cans=[dict(rand=part.rand, at=at, axis=axis, kind=kind) for part, at, axis, kind in cans],
            ),
            h,
        )
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
    hw = bpy.data.objects["cooler_lod0"]
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

    bake_one(2048, "EMIT", source("pos"), 1, "bake_cooler_pos")
    bake_one(2048, "EMIT", source("nor"), 1, "bake_cooler_nor")
    bake_one(2048, "EMIT", source("facts"), 1, "bake_cooler_facts")
    bake_one(1024, "AO", None, 32, "bake_cooler_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["cooler_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"cooler_lod{lod}"]
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
            h.write(f"# Generated by Sources/Zombies/cooler-v2/cooler.py\nmtllib {NAME}.mtl\n")
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
// Generated by Sources/Zombies/cooler-v2/cooler.py
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
    vmat = f"""// Generated by Sources/Zombies/cooler-v2/cooler.py

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
print("cooler stages done", flush=True)
