"""Build, bake and export stages for a single-material map prop, on the capture flag's toolkit. Imported, not run.

A prop's own script defines its geometry and calls `run`. Parts join into one mesh, get one UV atlas, and export as three LODs with a
vmdl and a vmat per colour. Convex edges and any points the prop notes are saved for its paint script. Inches, engine axes (Z up).
"""
import hashlib
import json
import math
import os

import bmesh
import bpy
import numpy as np


def uv_hash(ob):
    data = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers["UVMap"].data.foreach_get("uv", data)
    return hashlib.sha1(data.tobytes()).hexdigest()


def harden_all(kit, edge_finishes, spacing=0.15):
    """Settle each part's winding, note its convex edges for the wear, then bevel it."""
    edges = []
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in edge_finishes:
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / spacing))
                    for k in range(count + 1):
                        edges.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    return edges


def build_stage(kit, name, work, res, pos_range, geometry, edge_finishes, lods, pad, facts, points=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    edges = harden_all(kit, edge_finishes)
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, f"{name}_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, res, pad)
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
    density = res * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)
    lookup = {round(p.rand, 4): p for p in kit.parts}
    for number, (keep, ratio) in enumerate(lods, 1):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = f"{name}_lod{number}"
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        layer = bm.loops.layers.float_color["facts"]
        drop = [f for f in bm.faces if lookup[round(f.loops[0][layer][1], 4)].lod < keep]
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
    np.save(os.path.join(work, f"{name}_edges.npy"), np.array(edges, np.float32))
    if points is not None:
        np.save(os.path.join(work, f"{name}_points.npy"), np.array(points, np.float32))
    with open(os.path.join(work, f"{name}.json"), "w") as h:
        json.dump(dict(density=density, res=res, range=pos_range, **facts), h)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(work, f"{name}_build.blend"))
    print("saved build", flush=True)


def bake_stage(name, work, res, pos_range, ao_distance):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(work, f"{name}_build.blend"))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.max_bounces = 2
    hw = bpy.data.objects[f"{name}_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = ao_distance
    with open(os.path.join(work, f"{name}_baked_uv_hash.txt"), "w") as h:
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
            scale = 1 / pos_range if kind == "pos" else 0.5
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
        np.save(os.path.join(work, out + ".npy"), data.reshape(size, size, 4))
        print("baked", out, flush=True)

    bake_one(res, "EMIT", source("pos"), 1, f"bake_{name}_pos")
    bake_one(res, "EMIT", source("nor"), 1, f"bake_{name}_nor")
    bake_one(res, "EMIT", source("facts"), 1, f"bake_{name}_facts")
    bake_one(max(512, res // 2), "AO", None, 64, f"bake_{name}_ao")


def export_stage(name, work, out, folder, colours, thresholds, generated_by):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(work, f"{name}_build.blend"))
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects[f"{name}_lod0"]) != open(os.path.join(work, f"{name}_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    number = 0
    while f"{name}_lod{number}" in bpy.data.objects:
        ob = bpy.data.objects[f"{name}_lod{number}"]
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
        tables, lines, faces = ({}, {}, {}), ([], [], []), []
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
        with open(os.path.join(out, f"{name}_lod{number}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by {generated_by}\nmtllib {name}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {name}\n")
            h.writelines(faces)
        counts[number] = n_tris
        print("lod", number, "tris", n_tris, flush=True)
        number += 1
    with open(os.path.join(out, f"{name}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {name}\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{folder}/{name}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, thresholds))
    for colour in colours:
        stem = f"{name}_{colour}" if colour else name
        doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by {generated_by}
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
							{{ from = "{name}.vmat" to = "{folder}/{stem}.vmat" }}
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
        with open(os.path.join(out, f"{stem}.vmdl"), "w", newline="\n") as h:
            h.write(doc)
        vmat = f"""// Generated by {generated_by}

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{folder}/{name}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{folder}/{stem}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{folder}/{name}_metal.png"

	//---- Normal ----
	TextureNormal "{folder}/{name}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{folder}/{name}_rough.png"
}}
"""
        with open(os.path.join(out, f"{stem}.vmat"), "w", newline="\n") as h:
            h.write(vmat)
    print("exported", counts, flush=True)
