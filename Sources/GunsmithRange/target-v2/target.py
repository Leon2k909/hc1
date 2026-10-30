"""Range target v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python target.py -- <work dir> <project root> <build|bake|export> ...

A real steel silhouette: a hardened plate cut to the old target's exact outline, hung on a welded frame behind a
deflector plate, on a trolley whose wheels reach down to the range's track plate (the old one floats 1.9 above it).
Physics is copied from the old model untouched, so what's hit, the head line at z = 59 and the 18-wide stem don't change.
Inches, engine axes, the firing line at -X.
"""
import hashlib
import json
import math
import os
import re
import shutil
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

from build import Part, add, box, frame, hex_bolt, lathe, prism, weld_line, yaw  # noqa: E402

PAINT, GALV, OXIDE, ZINC, RUBBER, WELD = kit.PAINT, kit.GALV, kit.OXIDE, kit.ZINC, kit.RUBBER, kit.WELD
FACE, APRON = 9, 10
MODEL = "models/gunsmith_range/range_target_v2"
MATS = "materials/gunsmith_range/range_target_v2"
BLEND = os.path.join(WORK, "target_build.blend")

# Plate coordinates: local x is the world's Y, local y is Z, local z is X (toward the back).
SIDE = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def geometry():
    head = []
    start, end = math.atan2(60.26 - 66.0, 4.0), math.pi - math.atan2(60.26 - 66.0, 4.0)
    for k in range(29):
        a = start + (end - start) * k / 28
        head.append((7.0 * math.cos(a), 66.0 + 7.0 * math.sin(a)))
    outline = [(-10, 28), (10, 28), (16, 34), (16, 51), (9, 57), (4, 57)] + head + [(-4, 57), (-9, 57), (-16, 51), (-16, 34)]
    prism(add(Part(FACE, 3, bevel=0.05, segs=2, angle=25, name="strike plate")), outline, -0.46, 0.04, SIDE)

    # Hung from behind on two carriage bolts, whose heads show on the face.
    for y in (-12.5, 12.5):
        lathe(add(Part(FACE, 1, name="carriage bolt")), [(0.62, 0), (0.56, 0.08), (0.34, 0.17), (0, 0.2)], 12, frame((-0.46, y, 42.5), (-1, 0, 0)))
        hex_bolt((0.04, y, 42.5), (1, 0, 0), 0.8, lod=1, finish=ZINC, stud=0.25)

    # The frame behind the plate.
    box(add(Part(PAINT, 3, bevel=0.05, segs=2, name="spine")), (0.04, -1.1, 0.7), (2.24, 1.1, 53.0))
    box(add(Part(PAINT, 2, bevel=0.04, name="hanger")), (0.04, -14, 41.6), (1.5, 14, 43.4))
    box(add(Part(PAINT, 2, bevel=0.04, name="lower rail")), (0.04, -9.5, 33.0), (1.5, 9.5, 34.6))
    for z in (42.5, 33.8):
        for side in (-1, 1):
            weld_line((1.5, side * 1.14, z - 0.8), (1.5, side * 1.14, z + 0.8), 0.1, lod=0)
            weld_line((0.2, side * 1.14, z + 0.9), (1.5, side * 1.14, z + 0.9), 0.09, lod=0)

    # The deflector plate that keeps low shots off the trolley.
    apron = [(-9, 0.7), (9, 0.7), (9, 26), (7.4, 27.6), (-7.4, 27.6), (-9, 26)]
    prism(add(Part(APRON, 3, bevel=0.05, segs=2, angle=25, name="deflector")), apron, -0.6, 0.0, SIDE)
    for y in (-7.4, 0.0, 7.4):
        lathe(add(Part(APRON, 1, name="carriage bolt")), [(0.5, 0), (0.45, 0.07), (0.28, 0.14), (0, 0.17)], 12, frame((-0.6, y, 22.6), (-1, 0, 0)))

    # The trolley: a base, two gussets and four wheels that run along the track.
    base = [(-7, -11.4), (-5.9, -12.5), (11, -12.5), (12.1, -11.4), (12.1, 11.4), (11, 12.5), (-5.9, 12.5), (-7, 11.4)]
    prism(add(Part(PAINT, 3, bevel=0.05, segs=2, name="base")), base, 0.0, 0.7)
    gusset = [(0.0, 0.7), (10.6, 0.7), (10.6, 2.0), (2.3, 24.0), (0.0, 24.0)]
    for y in (-7.8, 7.8):
        m = Matrix.Translation((0, y, 0)) @ Matrix.Rotation(math.radians(90), 4, "X")
        prism(add(Part(PAINT, 2, bevel=0.04, name="gusset")), gusset, -0.2, 0.2, m)
        for side in (-0.26, 0.26):
            weld_line((0.3, y + side, 0.82), (10.4, y + side, 0.82), 0.1, lod=0)
            weld_line((0.14, y + side, 0.9), (0.14, y + side, 23.8), 0.1, lod=0)
    weld_line((-0.68, -8.9, 0.82), (-0.68, 8.9, 0.82), 0.12, lod=1)
    weld_line((2.3, -1.2, 0.82), (2.3, 1.2, 0.82), 0.12, lod=0)
    for x in (-5.4, 10.6):
        for y in (-10.6, 10.6):
            hex_bolt((x, y, 0.7), (0, 0, 1), 0.7, lod=1, stud=0.2)
    for x in (-3.4, 8.4):
        for y in (-9.4, 9.4):
            at = Vector((x, y, -0.95))
            ear = add(Part(OXIDE, 2, bevel=0.03, name="wheel fork"))
            for off in (-0.75, 0.75):
                box(ear, (x + off - 0.12, y - 0.8, -1.2), (x + off + 0.12, y + 0.8, 0.0))
            lathe(
                add(Part(RUBBER, 2, bevel=0.0, name="wheel")),
                [(0.0, -0.5), (0.72, -0.5), (0.95, -0.34), (0.95, 0.34), (0.72, 0.5), (0.0, 0.5)],
                20,
                frame(at, (1, 0, 0)),
            )
            lathe(add(Part(ZINC, 1, name="axle")), [(0, -0.98), (0.16, -0.98), (0.16, 0.98), (0, 0.98)], 8, frame(at, (1, 0, 0)))


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "rt_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, 2048, 5)

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

    lod("rt_lod1", 1, 0.6)
    lod("rt_lod2", 2, 0.22)
    with open(os.path.join(WORK, "target.json"), "w") as h:
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
    hw = bpy.data.objects["rt_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -1.9))
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

    bake_one(2048, "EMIT", source("pos"), 1, "bake_rt_pos")
    bake_one(2048, "EMIT", source("nor"), 1, "bake_rt_nor")
    bake_one(2048, "EMIT", source("facts"), 1, "bake_rt_facts")
    bake_one(1024, "AO", None, 48, "bake_rt_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["rt_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"rt_lod{lod}"]
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
        with open(os.path.join(out, f"range_target_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/GunsmithRange/target-v2/target.py\nmtllib range_target.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl rt_steel\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "range_target.mtl"), "w", newline="\n") as h:
        h.write("newmtl rt_steel\nKd 1 1 1\nd 1\n")

    # The old physics, word for word, with the hulls copied alongside so this folder stands alone.
    old_doc = open(os.path.join(ROOT, "output/asset-improvement-20261030/range-target/retired-range_target/range_target.vmdl"), encoding="utf-8").read()
    start = old_doc.index('_class = "PhysicsShapeList"')
    start = old_doc.rindex("{", 0, start)
    end = old_doc.index("model_archetype")
    end = old_doc.rindex("]", 0, end)
    physics = old_doc[start:end].rstrip()
    physics = physics.replace("models/gunsmith_range/range_target_hulls_metal.obj", f"{MODEL}/range_target_hulls_metal.obj")
    shutil.copyfile(os.path.join(ROOT, "output/asset-improvement-20261030/range-target/retired-range_target/range_target_hulls_metal.obj"), os.path.join(out, "range_target_hulls_metal.obj"))
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/range_target_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 90.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/GunsmithRange/target-v2/target.py
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
							{{ from = "rt_steel.vmat" to = "{MATS}/rt_steel.vmat" }}
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
			{physics}
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
"""
    with open(os.path.join(out, "range_target.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/GunsmithRange/target-v2/target.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/rt_steel_ao.png"

	//---- Color ----
	// FiringRangeTarget flashes the renderer's tint on every hit, as it did with the old materials.
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/rt_steel_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/rt_steel_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/rt_steel_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/rt_steel_rough.png"
}}
"""
    with open(os.path.join(mats, "rt_steel.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("target stages done", flush=True)
