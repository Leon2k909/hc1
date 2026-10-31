"""HC1 rifle suppressor v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python suppressor.py -- <work dir> <project root> <build|bake|export> ...

The old suppressor's layout and size, rebuilt: threaded socket, locking collar with its 16 grip bars, shoulder, a can with
witness grooves and a fluted middle, a riveted plate, and an end cap with wrench flats. It's game art, exterior only: the bore
is a blind hole and nothing inside is modelled. Same origin and axes as the old model, so the gunsmith's 6.26 muzzle shift
still holds. Inches, engine axes, +X toward the muzzle.
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

from build import Part, add, box, frame, lathe  # noqa: E402

COAT, STEEL, BARE, LABEL = range(4)
MODEL = "attachments/hc1/rifle_suppressor_v2"
BLEND = os.path.join(WORK, "suppressor_build.blend")
ATLAS = 1024
# Local (x, y, z) is world (z, x, y): a lathe's axis runs along the suppressor, and angle 0 is +Y, 90 degrees is +Z.
ALONG = frame((0, 0, 0), (1, 0, 0))


def fluted(part, x0, x1, radius, depth, count, width, runout, flat=False):
    """A closed tube with lengthwise cuts that run out smoothly at both ends. width is the share of each cut's pitch.

    With flat, each cut is a true flat, as a wrench needs: a chord across the circle rather than a scoop.
    """
    bm = part.bm
    per = 9
    n = count * per
    stations = [(x0, 0.0), (x0 + runout * 0.35, 0.3), (x0 + runout * 0.7, 0.75), (x0 + runout, 1.0), (x1 - runout, 1.0), (x1 - runout * 0.7, 0.75), (x1 - runout * 0.35, 0.3), (x1, 0.0)]
    rings = []
    for x, cut in stations:
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            phase = (k % per) / per
            inside = abs(phase - 0.5) * 2 / width
            shape = math.cos(inside * math.pi / 2) ** 2 if inside < 1 else 0.0
            r = radius - depth * cut * shape
            if flat:
                from_centre = (phase - 0.5) * 2 * math.pi / count
                r = min(radius, (radius - depth * cut) / math.cos(from_centre))
            ring.append(bm.verts.new(ALONG @ Vector((r * math.cos(a), r * math.sin(a), x))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def curved_plate(part, x0, x1, radius, thick, centre, half, cols=10):
    """A thin plate wrapped to the can, with the same winding as the toolkit's data plate."""
    bm = part.bm
    a0, a1 = centre - half, centre + half
    outer, inner = [], []
    for x in (x0, x1):
        angles = [a0 + (a1 - a0) * k / cols for k in range(cols + 1)]
        outer.append([bm.verts.new(ALONG @ Vector(((radius + thick) * math.cos(a), (radius + thick) * math.sin(a), x))) for a in angles])
        inner.append([bm.verts.new(ALONG @ Vector((radius * math.cos(a), radius * math.sin(a), x))) for a in angles])
    for k in range(cols):
        bm.faces.new((outer[0][k], outer[0][k + 1], outer[1][k + 1], outer[1][k]))
        bm.faces.new((inner[0][k + 1], inner[0][k], inner[1][k], inner[1][k + 1]))
        bm.faces.new((outer[0][k], inner[0][k], inner[0][k + 1], outer[0][k + 1]))
        bm.faces.new((outer[1][k], outer[1][k + 1], inner[1][k + 1], inner[1][k]))
    bm.faces.new((outer[0][0], outer[1][0], inner[1][0], inner[0][0]))
    bm.faces.new((outer[0][cols], inner[0][cols], inner[1][cols], outer[1][cols]))


def rivet(x, radius, angle, size, finish=STEEL):
    at = ALONG @ Vector((radius * math.cos(angle), radius * math.sin(angle), x))
    out = (ALONG.to_3x3() @ Vector((math.cos(angle), math.sin(angle), 0))).normalized()
    lathe(add(Part(finish, 0, name="rivet")), [(size, 0), (size * 0.92, size * 0.3), (size * 0.5, size * 0.56), (0, size * 0.62)], 10, frame(at, out))


def geometry():
    # The socket that threads onto the barrel: a blind hole with thread rings, the gun hides most of it.
    socket = [(0.0, 0.5), (0.29, 0.5)]
    x = 0.46
    while x > -0.12:
        socket += [(0.29, x), (0.325, x - 0.035)]
        x -= 0.07
    socket += [(0.325, -0.16), (0.42, -0.25), (0.69, -0.25), (0.742, -0.2), (0.742, 0.06)]
    lathe(add(Part(BARE, 3, name="socket")), socket, 32, ALONG)

    # The locking collar and its grip bars. The bars set the old model's largest radius.
    collar = [(0.7, 0.04), (0.742, 0.06), (0.776, 0.1), (0.776, 0.56), (0.79, 0.6), (0.79, 0.88), (0.77, 0.92), (0.74, 0.94)]
    lathe(add(Part(STEEL, 3, bevel=0.01, segs=1, angle=25, name="collar")), collar, 48, ALONG)
    for k in range(16):
        turn = Matrix.Rotation(2 * math.pi * k / 16, 4, "X")
        box(add(Part(STEEL, 1, bevel=0.012, segs=1, angle=40, name="grip bar")), (0.6, -0.065, 0.76), (0.88, 0.065, 0.812), turn)
    # A detent pin in the collar, where a thumb finds it.
    lathe(add(Part(BARE, 1, bevel=0.006, angle=40, name="detent")), [(0.085, 0), (0.085, 0.028), (0.05, 0.04), (0, 0.042)], 12, frame((0.33, 0, 0.77), (0, 0, 1)))

    # The shoulder from collar to can, with one real groove in it.
    shoulder = [(0.72, 0.93), (0.77, 0.96), (0.793, 1.0), (0.793, 1.16), (0.772, 1.19), (0.772, 1.25), (0.793, 1.28), (0.793, 1.4), (0.77, 1.44)]
    lathe(add(Part(STEEL, 3, bevel=0.01, segs=1, angle=25, name="shoulder")), shoulder, 48, ALONG)

    # The can: plain behind, where the plate and lettering are, then witness grooves, flutes, more grooves.
    rear = [(0.76, 1.42), (0.78, 1.45), (0.78, 2.72), (0.766, 2.74), (0.766, 2.78), (0.78, 2.8), (0.78, 2.86), (0.766, 2.88), (0.766, 2.92), (0.78, 2.94), (0.78, 2.97)]
    lathe(add(Part(COAT, 3, name="can rear")), rear, 64, ALONG)
    fluted(add(Part(COAT, 3, name="fluted can")), 2.96, 5.36, 0.78, 0.058, 10, 0.62, 0.24)
    front = [(0.78, 5.35), (0.78, 5.56), (0.766, 5.58), (0.766, 5.62), (0.79, 5.66), (0.79, 5.76)]
    lathe(add(Part(COAT, 3, name="can front")), front, 64, ALONG)

    # The end cap: a band, six wrench flats, then a dished face around the blind bore.
    lathe(add(Part(STEEL, 3, bevel=0.008, segs=1, angle=25, name="cap band")), [(0.77, 5.74), (0.793, 5.78), (0.793, 5.86)], 48, ALONG)
    fluted(add(Part(STEEL, 3, name="wrench flats")), 5.85, 6.26, 0.793, 0.05, 6, 0.8, 0.05, flat=True)
    face = [(0.793, 6.25), (0.793, 6.46), (0.77, 6.54), (0.72, 6.6), (0.5, 6.61), (0.46, 6.565), (0.29, 6.545), (0.215, 6.5), (0.198, 6.46), (0.198, 5.7), (0.0, 5.7)]
    lathe(add(Part(STEEL, 3, bevel=0.008, segs=1, angle=30, name="cap face")), face, 48, ALONG)

    # The plate, on the old one's side, wrapped to the can.
    curved_plate(add(Part(LABEL, 2, bevel=0.006, angle=40, name="plate")), 1.6, 2.62, 0.78, 0.016, math.pi, 0.3)
    for x in (1.68, 2.54):
        rivet(x, 0.795, math.pi, 0.038)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    dev = kit.join_parts(kit.parts, "rs_lod0")
    dev.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = dev
    dev.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    dev.select_set(False)
    kit.pack_real_scale(dev.data, ATLAS, 3)

    mesh = dev.data
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
    density = ATLAS * math.sqrt(uva / area3)
    print("tris", len(mesh.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def lod(name, keep, ratio):
        copy = dev.copy()
        copy.data = dev.data.copy()
        copy.name = copy.data.name = name
        bpy.context.scene.collection.objects.link(copy)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        layer = bm.loops.layers.float_color["facts"]
        drop = [f for f in bm.faces if lookup.get(round(f.loops[0][layer][1], 4)) is not None and lookup[round(f.loops[0][layer][1], 4)].lod < keep]
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

    lod("rs_lod1", 1, 0.6)
    lod("rs_lod2", 2, 0.3)
    lod("rs_lod3", 3, 0.14)
    with open(os.path.join(WORK, "suppressor.json"), "w") as h:
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
    dev = bpy.data.objects["rs_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not dev
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 0.5
    with open(os.path.join(WORK, "baked_uv_hash.txt"), "w") as h:
        h.write(uv_hash(dev))

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
            scale = 1 / 40.0 if kind == "pos" else 0.5
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
        dev.data.materials.clear()
        dev.data.materials.append(mat)
        scene.cycles.samples = samples
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = dev
        dev.select_set(True)
        bpy.ops.object.bake(type=kind, margin=0, use_clear=True, target="IMAGE_TEXTURES")
        data = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(size, size, 4))
        print("baked", out, flush=True)

    bake_one(ATLAS, "EMIT", source("pos"), 1, "bake_rs_pos")
    bake_one(ATLAS, "EMIT", source("nor"), 1, "bake_rs_nor")
    bake_one(ATLAS, "EMIT", source("facts"), 1, "bake_rs_facts")
    bake_one(ATLAS, "AO", None, 48, "bake_rs_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", "attachments", "hc1", "rifle_suppressor_v2")
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["rs_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2, 3):
        ob = bpy.data.objects[f"rs_lod{lod}"]
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
        with open(os.path.join(out, f"rifle_suppressor_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Weapons/rifle-suppressor-v2/suppressor.py\nmtllib rifle_suppressor.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl rs_can\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "rifle_suppressor.mtl"), "w", newline="\n") as h:
        h.write("newmtl rs_can\nKd 1 1 1\nd 1\n")

    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/rifle_suppressor_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 40.0, 120.0, 300.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Weapons/rifle-suppressor-v2/suppressor.py
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
							{{ from = "rs_can.vmat" to = "{MODEL}/rs_can.vmat" }}
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
    with open(os.path.join(out, "rifle_suppressor.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Weapons/rifle-suppressor-v2/suppressor.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MODEL}/rs_can_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/rs_can_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MODEL}/rs_can_metal.png"

	//---- Normal ----
	TextureNormal "{MODEL}/rs_can_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/rs_can_rough.png"
}}
"""
    with open(os.path.join(out, "rs_can.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("suppressor stages done", flush=True)
