"""Town house doors v2: build, bake and export one door. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python door.py -- <work dir> <project root> <outer|inner> <build|bake|export> ...

Real joinery in place of a flat slab: stiles, rails and a mullion with their joints showing, four fielded panels and
their mouldings, on hinges, with a lever and backplate each side. The front doors add a brass letter plate, kick plates,
a knocker and a weather bar on their exterior face, which is +X on all three. The leaf fills the prefab's box collider
exactly and swings about the same origin, so nothing about using a door changes. There are ten doors to a house, so the
close LOD is kept to a few thousand triangles and the far ones drop quickly. Inches, engine axes.
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
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, box, frame, lathe, prism, ring_path, spline, tube  # noqa: E402

OXIDE, ZINC, BRASS, RUBBER = kit.OXIDE, kit.ZINC, kit.BRASS, kit.RUBBER
ALONG, ACROSS = 11, 12  # Timber with its grain running up the door, and across it.
MODEL = "models/buildings/town_house/door_v2"
MATS = "materials/buildings/town_house_door_v2"
NAME = f"door_{VARIANT}"
BLEND = os.path.join(WORK, "door_build.blend")
# From the prefab's box colliders: centre +- half scale.
LEAF = {
    "outer": dict(y0=-0.875, y1=44.75, z0=-41.625, z1=43.75, t=0.875, stile=4.6),
    "inner": dict(y0=-0.6875, y1=38.9375, z0=-41.625, z1=39.75, t=0.6875, stile=4.0),
}[VARIANT]


def plate_frame(at, side):
    """Local x along +Y, local y up the door (mirrored on the -X face), local z out of the face."""
    return frame(at, (side, 0, 0), (0, 1, 0))


def rounded_plate(part, w, h, thick, m, c=0.3):
    a, b = w / 2, h / 2
    prism(part, [(-a + c, -b), (a - c, -b), (a, -b + c), (a, b - c), (a - c, b), (-a + c, b), (-a, b - c), (-a, -b + c)], 0.0, thick, m)


def geometry():
    y0, y1, z0, z1, t, s = (LEAF[k] for k in ("y0", "y1", "z0", "z1", "t", "stile"))
    lock = z0 + 36.0
    rail_low, rail_high = lock - 3.5, lock + 3.5
    bottom = z0 + 9.4
    top = z1 - s
    middle = (y0 + y1) / 2
    mull = 2.1

    # The frame of the door, each member its own timber so the joints show.
    add_box = lambda finish, lod, lo, hi, bevel=0.07: box(add(Part(finish, lod, bevel=bevel, name="timber")), lo, hi)
    add_box(ALONG, 3, (-t, y0, z0), (t, y0 + s, z1))
    add_box(ALONG, 3, (-t, y1 - s, z0), (t, y1, z1))
    add_box(ACROSS, 3, (-t, y0 + s, top), (t, y1 - s, z1))
    add_box(ACROSS, 3, (-t, y0 + s, rail_low), (t, y1 - s, rail_high))
    add_box(ACROSS, 3, (-t, y0 + s, z0), (t, y1 - s, bottom))
    add_box(ALONG, 2, (-t, middle - mull, rail_high), (t, middle + mull, top))
    add_box(ALONG, 2, (-t, middle - mull, bottom), (t, middle + mull, rail_low))

    # Four panels, fielded on both faces, each framed by a moulding.
    for ya, yb in ((y0 + s, middle - mull), (middle + mull, y1 - s)):
        for za, zb in ((bottom, rail_low), (rail_high, top)):
            # Only the panel's rim shows: the fields cover its middle, so it isn't given texture space it would waste.
            rim = add(Part(ALONG, 3, name="panel rim"))
            box(rim, (-0.3, ya, za), (0.3, ya + 1.7, zb))
            box(rim, (-0.3, yb - 1.7, za), (0.3, yb, zb))
            box(rim, (-0.3, ya + 1.7, za), (0.3, yb - 1.7, za + 1.7))
            box(rim, (-0.3, ya + 1.7, zb - 1.7), (0.3, yb - 1.7, zb))
            for side in (-1, 1):
                lo, hi = (0.22, 0.6) if side > 0 else (-0.6, -0.22)
                field = add(Part(ALONG, 3, bevel=0.16, name="field"))
                box(field, (lo, ya + 1.6, za + 1.6), (hi, yb - 1.6, zb - 1.6))
                field.bm.normal_update()
                back = [f for f in field.bm.faces if f.normal.x * side < -0.9]
                bmesh.ops.delete(field.bm, geom=back, context="FACES")
                x0, x1 = (0.28, t - 0.12) if side > 0 else (-t + 0.12, -0.28)
                w = 0.6
                add_box(ALONG, 1, (x0, ya, za), (x1, ya + w, zb), 0.09)
                add_box(ALONG, 1, (x0, yb - w, za), (x1, yb, zb), 0.09)
                add_box(ACROSS, 1, (x0, ya + w, za), (x1, yb - w, za + w), 0.09)
                add_box(ACROSS, 1, (x0, ya + w, zb - w), (x1, yb - w, zb), 0.09)

    # Lever and backplate on each face.
    hy = y1 - 2.5
    hz = lock
    for side in (-1, 1):
        m = plate_frame((side * t, hy, hz - 1.3), side)
        rounded_plate(add(Part(OXIDE, 2, bevel=0.02, angle=30, name="backplate")), 2.0, 8.0, 0.1, m)
        for dy, dz in ((-0.65, 3.4), (0.65, 3.4), (-0.65, -3.4), (0.65, -3.4)):
            at = Vector((side * (t + 0.1), hy + dy, hz - 1.3 + dz))
            lathe(add(Part(ZINC, 0, name="screw")), [(0.13, 0), (0.1, 0.05), (0, 0.06)], 6, frame(at, (side, 0, 0)))
        lathe(
            add(Part(OXIDE, 1, name="rose")),
            [(0.62, 0.1), (0.62, 0.2), (0.46, 0.3), (0.3, 0.38), (0.3, 0.72)],
            14,
            frame((side * t, hy, hz), (side, 0, 0)),
        )
        lever = spline(
            [
                (side * (t + 0.55), hy, hz),
                (side * (t + 1.5), hy, hz),
                (side * (t + 2.1), hy - 0.6, hz),
                (side * (t + 2.25), hy - 2.5, hz + 0.02),
                (side * (t + 2.2), hy - 4.8, hz - 0.05),
            ],
            3,
        )
        radii = [0.27] * (len(lever) - 2) + [0.31, 0.2]
        tube(add(Part(OXIDE, 2, name="lever")), lever, radii, 10, flatten=0.85)
        key = plate_frame((side * (t + 0.1), hy, hz - 3.7), side)
        box(add(Part(RUBBER, 0, name="keyhole")), (-0.11, -0.3, 0.0), (0.11, 0.3, 0.015), key)

    # Three butt hinges, knuckles showing on the side the door swings to.
    for hinge in (z1 - 8.0, (z0 + z1) / 2 + 1.0, z0 + 10.0):
        lathe(
            add(Part(OXIDE, 1, name="hinge")),
            [(0, -2.05), (0.2, -2.05), (0.33, -1.92), (0.33, 1.92), (0.2, 2.05), (0, 2.05)],
            10,
            frame((-t - 0.08, y0 + 0.1, hinge)),
        )
        box(add(Part(OXIDE, 1, bevel=0.01, angle=30, name="hinge leaf")), (-t - 0.03, y0 + 0.2, hinge - 1.9), (-t, y0 + 1.5, hinge + 1.9))

    if VARIANT == "outer":
        # Brass kick plate on both faces, worn by shoes.
        for side in (-1, 1):
            lo = (t, y0 + s - 1.6, z0 + 0.8) if side > 0 else (-t - 0.05, y0 + s - 1.6, z0 + 0.8)
            hi = (t + 0.05, y1 - s + 1.6, z0 + 8.8) if side > 0 else (-t, y1 - s + 1.6, z0 + 8.8)
            box(add(Part(BRASS, 2, bevel=0.012, angle=30, name="kick plate")), lo, hi)
            m = plate_frame((side * t, middle, lock), side)
            rounded_plate(add(Part(BRASS, 2, bevel=0.018, angle=30, name="letter plate")), 10.0, 2.8, 0.09, m, 0.25)
            rounded_plate(add(Part(BRASS, 1, bevel=0.015, angle=30, name="letter flap")), 8.4, 1.5, 0.15, m, 0.12)
        # The exterior face: a knocker, and a weather bar shedding rain off the threshold.
        ring = frame((t + 0.42, middle, top - 9.6), (1, 0, 0))
        lathe(add(Part(OXIDE, 1, name="knocker boss")), [(0.5, 0.0), (0.5, 0.18), (0.26, 0.38), (0, 0.46)], 12, frame((t, middle, top - 8.6), (1, 0, 0)))
        tube(add(Part(OXIDE, 1, name="knocker")), ring_path(1.15, 20, ring), 0.17, 8, closed=True)
        bar = add(Part(ACROSS, 2, bevel=0.1, name="weather bar"))
        prism(bar, [(t, z0 + 0.5), (t + 0.8, z0 + 0.5), (t + 0.8, z0 + 1.0), (t, z0 + 2.2)], -(y1 - 0.1), -(y0 + 0.1), frame((0, 0, 0), (0, -1, 0), (1, 0, 0)))


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "door_lod0")
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

    lod("door_lod1", 1, 0.5)
    lod("door_lod2", 3, 0.35)
    with open(os.path.join(WORK, "door.json"), "w") as h:
        json.dump(dict(density=density, variant=VARIANT, **LEAF), h)
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
    hw = bpy.data.objects["door_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 6.0
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

    bake_one(2048, "EMIT", source("pos"), 1, "bake_door_pos")
    bake_one(2048, "EMIT", source("nor"), 1, "bake_door_nor")
    bake_one(2048, "EMIT", source("facts"), 1, "bake_door_facts")
    bake_one(1024, "AO", None, 32, "bake_door_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["door_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"door_lod{lod}"]
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
            h.write(f"# Generated by Sources/Buildings/town-house-doors-v2/door.py\nmtllib {NAME}.mtl\n")
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
// Generated by Sources/Buildings/town-house-doors-v2/door.py
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
    vmat = f"""// Generated by Sources/Buildings/town-house-doors-v2/door.py

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
print("door stages done", flush=True)
