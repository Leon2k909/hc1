"""Riverside's teddy v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python teddy.py -- <work dir> <project root> <build|bake|export> ...

The old teddy (Tools/riverside_parts.py, teddy) is eight 8-sided lumps with visible facets and no face, in the mud by the dog run's gate. This is a
child's plush bear, sat where it was dropped with its head tipped over: one soft skin from metaballs, so its limbs run into its body like stuffed
cloth, a stitched nose, one button eye and the other hanging by a thread, a faded ribbon, and stuffing coming out of a split seam.

Same place and about the same size. Inches, engine axes: origin on the ground under its seat, facing +x. It has no collision, as the old one had none.
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
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Zombies", "burn-drum-v2"))
import build as kit  # noqa: E402
from drum_pack import pack_weighted  # noqa: E402

from build import Part, add, frame, lathe, spline, tube  # noqa: E402

SKIN, RIBBON, BUTTON, NOSE, STUFFING, THREAD = range(6)
NAME = "teddy"
MODEL = "models/zombies/teddy_v2"
MATS = "materials/zombies/teddy_v2"
BLEND = os.path.join(WORK, "teddy_build.blend")
SIZE = 2048
SKIN_TRIS = 3000

# The head, tipped over to one side and forward as it slumped: head-local points about its own middle.
HEAD_AT = Vector((0.5, 0.0, 12.9))
HEAD_TURN = Euler((math.radians(-13), math.radians(11), math.radians(9)), "XYZ").to_matrix().to_4x4()
HEAD_M = Matrix.Translation(HEAD_AT) @ HEAD_TURN


def head(x, y, z):
    return (HEAD_M @ Vector((x, y, z))).to_tuple()


def make_skin():
    """A metaball's surface sits at 0.575 of its radius, when it's alone. Neighbours add to each other, which is what makes the fillets."""
    mb = bpy.data.metaballs.new("teddy_skin")
    mb.resolution = mb.render_resolution = 0.3
    mb.threshold = 0.6
    ob = bpy.data.objects.new("teddy_skin", mb)
    bpy.context.scene.collection.objects.link(ob)

    def ball(at, radius, sx=1.0, sy=1.0, sz=1.0):
        e = mb.elements.new(type="ELLIPSOID" if (sx, sy, sz) != (1.0, 1.0, 1.0) else "BALL")
        e.co = at
        e.radius = radius / 0.575
        e.size_x, e.size_y, e.size_z = sx, sy, sz
        e.stiffness = 2.0

    # The body, pear-shaped and sat low.
    ball((0.0, 0.0, 4.2), 4.4)
    ball((0.4, 0.0, 7.2), 3.2)
    # The head and its muzzle.
    ball(head(0, 0, 0), 4.2)
    ball(head(3.5, 0, -1.05), 1.75)
    # Ears, round and flattened front to back. They're far enough out that they keep their shape.
    for s in (-1, 1):
        ball(head(-0.2, s * 3.85, 3.7), 1.5)
    # Arms hanging out and down, and legs stuck out in front, thick at the top.
    for s in (-1, 1):
        ball((0.5, s * 4.1, 8.4), 1.5)
        ball((1.5, s * 5.8, 6.6), 1.45)
        ball((2.6, s * 6.7, 4.8), 1.5)
        ball((3.5, s * 7.1, 3.1), 1.65)
        ball((2.6, s * 3.1, 2.2), 2.05)
        ball((5.1, s * 3.9, 1.95), 1.8)
        ball((7.4, s * 4.5, 2.0), 1.8)
        # The foot stands up from the leg's end.
        ball((8.2, s * 4.75, 2.75), 1.85)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    print("skin raw tris", sum(len(p.vertices) - 2 for p in mesh.polygons), flush=True)

    temp = bpy.data.objects.new("skin_temp", mesh)
    bpy.context.scene.collection.objects.link(temp)
    bpy.context.view_layer.objects.active = temp
    temp.select_set(True)
    mod = temp.modifiers.new("collapse", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = min(1.0, SKIN_TRIS / max(1, sum(len(p.vertices) - 2 for p in mesh.polygons)))
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    temp.select_set(False)

    part = add(Part(SKIN, 3, name="skin"))
    part.bm.from_mesh(temp.data)
    bpy.data.objects.remove(temp)
    # It sits on the ground, flattened a little under its seat and legs.
    bmesh.ops.recalc_face_normals(part.bm, faces=part.bm.faces)
    low = min(v.co.z for v in part.bm.verts)
    for v in part.bm.verts:
        v.co.z = max(v.co.z - low - 0.12, 0.0)
    part.bm.normal_update()
    return part


def details(skin):
    bvh = BVHTree.FromBMesh(skin.bm)

    def on_skin(origin, towards):
        """Where a ray from outside, along towards, first lands on the skin, and its normal there."""
        where, normal, _, _ = bvh.ray_cast(Vector(origin), Vector(towards).normalized())
        if where is None:
            raise SystemExit(f"Nothing to land on from {origin}")
        return where, normal

    # The nose: dark stitched thread over a pad, on the muzzle's front.
    at, n = on_skin(head(9, 0, -0.55), (HEAD_M.to_3x3() @ Vector((-1, 0, 0))))
    m = frame(at + n * 0.02, n, (0, 1, 0)) @ Matrix.Diagonal((1.05, 0.62, 0.42, 1))
    lathe(add(Part(NOSE, 3, name="nose")), [(0, -0.2), (0.74, -0.15), (0.9, 0.2), (0.86, 0.46), (0.66, 0.7), (0.34, 0.86), (0, 0.9)], 18, m)

    # One button eye, and the other's empty socket with its button hanging on the thread.
    button = [(0, 0.0), (0.76, 0.0), (0.84, 0.09), (0.76, 0.24), (0.36, 0.3), (0, 0.28)]
    eye_y = 1.75
    at, n = on_skin(head(9, eye_y, 1.05), (HEAD_M.to_3x3() @ Vector((-1, 0, 0))))
    lathe(add(Part(BUTTON, 2, name="eye")), button, 12, frame(at - n * 0.04, n, (0, 0, 1)))
    root, n2 = on_skin(head(9, -eye_y, 1.05), (HEAD_M.to_3x3() @ Vector((-1, 0, 0))))
    # The hanging button hangs straight down in the world, and rests against the chest.
    hang_to, hang_n = on_skin((12, root.y - 0.3, root.z - 6.2), (-1, 0, 0))
    hang = hang_to + hang_n * 0.12
    thread = spline([root + n2 * 0.02, root + n2 * 0.34 - Vector((0, 0, 0.5)), root + n2 * 0.5 - Vector((0, 0.1, 2.4)), hang + hang_n * 0.3 + Vector((0, 0, 1.0)), hang + hang_n * 0.1], 4)
    tube(add(Part(THREAD, 1, name="eye thread")), thread, 0.045, 5)
    lathe(add(Part(BUTTON, 1, name="loose eye")), button, 12, frame(hang - hang_n * 0.02, hang_n, (0.3, 0, 1)))

    # A ribbon round the neck, on the skin all the way round, and a knot with its tails.
    neck_z = 10.0
    # A band an inch wide, round the neck on a smooth line: where the skin bulges at the shoulders it rides over, rather than jutting out in a corner.
    band = add(Part(RIBBON, 3, name="ribbon"))
    sides = 28
    centre = Vector((0.35, 0.0, 0.0))
    radii = []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        d = Vector((math.cos(a), math.sin(a), 0))
        where, _ = on_skin((centre.x + d.x * 14, d.y * 14, neck_z - 0.25 * d.x), -d)
        radii.append(math.hypot(where.x - centre.x, where.y))
    radii = np.array(radii)

    def soften(a):
        return (np.roll(a, 2) + 2 * np.roll(a, 1) + 3 * a + 2 * np.roll(a, -1) + np.roll(a, -2)) / 9.0

    for _ in range(3):
        radii = soften(np.maximum(radii, soften(radii)))
    rows = [[], [], [], []]
    for k in range(sides):
        a = 2 * math.pi * k / sides
        d = Vector((math.cos(a), math.sin(a), 0))
        at = centre + d * float(radii[k]) + Vector((0, 0, neck_z - 0.25 * d.x))
        # Thin, with a narrow top: a cloth band, not a collar.
        for row, (out, up) in zip(rows, ((0.1, -0.5), (0.1, 0.5), (-0.1, 0.46), (-0.1, -0.46))):
            row.append(band.bm.verts.new(at + d * out + Vector((0, 0, up))))
    for a, b in zip(rows, rows[1:] + rows[:1]):
        for k in range(sides):
            n = (k + 1) % sides
            band.bm.faces.new((a[k], a[n], b[n], b[k]))
    front = centre + Vector((float(radii[0]) + 0.1, 0.0, neck_z - 0.25))
    front_n = Vector((1, 0, 0))
    m = frame(front + front_n * 0.1, front_n, (0, 1, 0)) @ Matrix.Diagonal((0.72, 0.6, 0.5, 1))
    lathe(add(Part(RIBBON, 2, name="knot")), [(0, -0.3), (0.7, -0.2), (0.86, 0.2), (0.5, 0.6), (0, 0.7)], 8, m)
    for s, drop, out in ((-1, 3.0, 1.5), (1, 2.3, 1.75)):
        tail = spline([front + front_n * 0.3, front + front_n * 0.42 + Vector((0, s * out * 0.5, -drop * 0.45)), front + front_n * 0.5 + Vector((0, s * out, -drop))], 3)
        tube(add(Part(RIBBON, 2, name="ribbon tail")), tail, [0.26, 0.42, 0.5, 0.5, 0.5, 0.5, 0.52][: len(tail)], 6, flatten=0.22)

    # Stuffing out of a split seam, low on its side.
    split, split_n = on_skin((3.0, 12, 5.5), (-0.25, -1, 0))
    rng = np.random.default_rng(14)
    # Small soft tufts along the split, which runs up and down its side.
    for k in range(10):
        off = Vector((float(rng.normal(0, 0.22)), 0, float(rng.uniform(-1.05, 1.05))))
        where = split + off + split_n * float(rng.uniform(0.0, 0.26))
        s = float(rng.uniform(0.26, 0.46))
        m = Matrix.Translation(where) @ Euler(tuple(float(x) for x in rng.uniform(0, 6.28, 3))).to_matrix().to_4x4() @ Matrix.Diagonal((s, s * 0.9, s * 0.8, 1))
        lathe(add(Part(STUFFING, 1, name="stuffing")), [(0.0, -0.9), (0.5, -0.74), (0.86, -0.34), (0.95, 0.05), (0.8, 0.45), (0.46, 0.76), (0.0, 0.9)], 8, m)
    return dict(split=split.to_tuple(), split_n=split_n.to_tuple(), eye_socket=root.to_tuple())


def weight_of(face, facts):
    finish = int(round(face.loops[0][facts][0] * 16))
    return {SKIN: 1.0, RIBBON: 0.8, BUTTON: 0.9, NOSE: 0.9, STUFFING: 0.7, THREAD: 0.4}[finish]


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    skin = make_skin()
    marks = details(skin)
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "teddy_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    density = pack_weighted(hw.data, weight_of, res=SIZE, pad_px=4)
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

    lod("teddy_lod1", 1, 0.5)
    lod("teddy_lod2", 3, 0.22)
    with open(os.path.join(WORK, "teddy.json"), "w") as h:
        json.dump(dict(density=density, head_inverse=[list(r) for r in HEAD_M.inverted()], **marks), h)
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
    hw = bpy.data.objects["teddy_lod0"]
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

    bake_one(SIZE, "EMIT", source("pos"), 1, "bake_teddy_pos")
    bake_one(SIZE, "EMIT", source("nor"), 1, "bake_teddy_nor")
    bake_one(SIZE, "EMIT", source("facts"), 1, "bake_teddy_facts")
    bake_one(SIZE // 2, "AO", None, 32, "bake_teddy_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["teddy_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"teddy_lod{lod}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(75))
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
            h.write(f"# Generated by Sources/Zombies/teddy-v2/teddy.py\nmtllib {NAME}.mtl\n")
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
// Generated by Sources/Zombies/teddy-v2/teddy.py
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
    vmat = f"""// Generated by Sources/Zombies/teddy-v2/teddy.py

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
print("teddy stages done", flush=True)
