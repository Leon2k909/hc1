"""Boxyard's IBC tote v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python ibc_tote.py -- <work dir> <project root> <build|bake|export> ...

`boxyard_map.ibc` draws a 1000 l tote as a plain box of tank inside bare rods on a slab, twice by the north-east stack. This is one as it really is, in the same
47.2 x 39.4 x 45.8 inch footprint on the same origin: a blow-moulded tank with rounded edges and a screw cap, a welded galvanised tube cage with its crossings, a pallet on
three runners, and a butterfly valve with its lever and a capped outlet. No collider: Boxyard's own box stays. Lettering is generic, with no brand.
Inches, engine axes: on the ground, the long side along Y, the valve at -Y. Local (x, y) in the map's `Frame` is engine (y, -x), so a placed tote's yaw is its plan heading.
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

from build import Part, add, box, frame, lathe, tube  # noqa: E402

GALV, ZINC, PLATE = kit.GALV, kit.ZINC, kit.PLATE
TANK, DARK, LEVER = 9, 10, 11
MODEL = "models/props/boxyard/ibc_tote_v2"
MATS = "materials/boxyard/ibc_tote_v2"
BLEND = os.path.join(WORK, "ibc_tote_build.blend")
SIZE, AO_SIZE = 2048, 1024
X0, Y0 = 19.15, 23.05  # The cage's bars' centres, so its outside is the old footprint's.
BAR = 0.42
rng = np.random.default_rng(4417)


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def tank_point(theta, z, grow):
    hx, hy = 18.3 - grow, 22.2 - grow
    c, s = math.cos(theta), math.sin(theta)
    n = 9.0
    return Vector((hx * math.copysign(abs(c) ** (2 / n), c), hy * math.copysign(abs(s) ** (2 / n), s), z))


def tank():
    """Blow-moulded: rounded all over, with a shallow rib where each cage ring passes. The underside isn't built: the pallet's deck hides it."""
    part = add(Part(TANK, 3, name="tank"))
    bm = part.bm
    columns = 72
    rows = [(5.4, 1.1), (5.7, 0.5), (6.3, 0.16), (7.2, 0.02), (9.0, 0.0), (13.2, 0.0), (13.8, 0.14), (15.2, 0.14), (15.8, 0.0), (23.2, 0.0), (23.8, 0.14), (25.2, 0.14), (25.8, 0.0), (33.2, 0.0), (33.8, 0.14), (35.2, 0.14), (35.8, 0.0), (41.0, 0.0), (42.2, 0.06), (43.0, 0.34), (43.55, 1.0), (43.85, 2.1), (44.0, 3.6)]
    rings = [[bm.verts.new(tank_point(2 * math.pi * k / columns, z, g)) for k in range(columns)] for z, g in rows]
    for a, b in zip(rings, rings[1:]):
        for k in range(columns):
            j = (k + 1) % columns
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(rings[-1])
    # The filler: its neck, the big screw cap and the vent plug in it.
    lathe(add(Part(TANK, 2, name="neck")), [(5.4, 43.9), (5.4, 44.2), (4.9, 44.3)], 28)
    lathe(add(Part(DARK, 3, bevel=0.03, angle=30, name="cap")), [(5.05, 44.2), (5.4, 44.25), (5.5, 44.42), (5.5, 45.1), (5.32, 45.34), (4.8, 45.4), (1.5, 45.4)], 40)
    lathe(add(Part(DARK, 1, bevel=0.02, angle=30, name="vent")), [(1.2, 45.3), (1.2, 45.56), (0.95, 45.66), (0, 45.68)], 16)


def bar(part, a, b, radius=BAR, sides=8):
    a, b = Vector(a), Vector(b)
    d = b - a
    lathe(part, [(radius, 0.0), (radius, d.length)], sides, frame(a, d))


def cage():
    xs = list(np.linspace(-X0, X0, 6))
    ys = list(np.linspace(-Y0, Y0, 7))
    rings = (14.5, 24.5, 34.5, 45.35)
    uprights = []
    for y in ys:
        for x in (-X0, X0):
            uprights.append((x, y, 5.2))
    for x in xs[1:-1]:
        for y in (-Y0, Y0):
            # The two either side of the valve stop at the first ring, to leave a hand's room.
            low = 14.5 if y < 0 and abs(x) < 5 else 5.2
            uprights.append((x, y, low))
    for x, y, low in uprights:
        bar(add(Part(GALV, 3, name="upright")), (x, y, low), (x, y, 45.75))
    for z in rings:
        for a, b in (((-X0 - 0.3, -Y0), (X0 + 0.3, -Y0)), ((-X0 - 0.3, Y0), (X0 + 0.3, Y0)), ((-X0, -Y0 - 0.3), (-X0, Y0 + 0.3)), ((X0, -Y0 - 0.3), (X0, Y0 + 0.3))):
            bar(add(Part(GALV, 3, name="rail")), (*a, z), (*b, z))
    for x in (-6.4, 6.4):
        bar(add(Part(GALV, 3, name="top bar")), (x, -Y0, 45.35), (x, Y0, 45.35))
    # The cage's crossings: pinched and welded, each a small lump.
    for x, y, low in uprights:
        for z in rings:
            if z < low:
                continue
            axis = (0, 1, 0) if abs(abs(x) - X0) < 0.01 and abs(abs(y) - Y0) > 0.01 else (1, 0, 0)
            lathe(add(Part(GALV, 0, name="crossing")), [(0, -0.62), (0.5, -0.34), (0.56, 0.0), (0.5, 0.34), (0, 0.62)], 6, frame((x, y, z), axis))
    # Each corner upright drops into a pressed shoe, bolted to the pallet.
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (X0 - 0.4), sy * (Y0 - 0.4)
            box(add(Part(GALV, 2, bevel=0.04, angle=40, name="shoe")), (cx - 1.0, cy - 1.0, 5.3), (cx + 1.0, cy + 1.0, 6.7))
            lathe(add(Part(ZINC, 0, name="shoe bolt")), [(0.3, 0), (0.3, 0.1), (0.18, 0.15), (0, 0.15)], 6, frame((cx, cy, 6.7), (0, 0, 1)))


def pallet():
    box(add(Part(GALV, 3, bevel=0.05, angle=40, name="deck")), (-19.6, -23.5, 4.7), (19.6, 23.5, 5.4))
    for x in (-15.2, 0.0, 15.2):
        box(add(Part(GALV, 3, bevel=0.05, angle=40, name="runner")), (x - 2.2, -23.55, 0.55), (x + 2.2, 23.55, 4.7))
        for y in (-20.6, 0.0, 20.6):
            box(add(Part(DARK, 2, bevel=0.06, angle=40, name="foot")), (x - 2.5, y - 2.9, 0.0), (x + 2.5, y + 2.9, 0.6))
    for y in (-21.2, 21.2):
        box(add(Part(GALV, 2, bevel=0.04, angle=40, name="cross beam")), (-19.6, y - 1.1, 3.4), (19.6, y + 1.1, 4.7))
    # A steel data plate riveted to the top rail.
    box(add(Part(PLATE, 2, bevel=0.012, angle=40, name="data plate")), (-X0 - 0.56, 4.4, 40.0), (-X0 - 0.48, 11.0, 44.2))
    for y in (4.8, 10.6):
        for z in (40.4, 43.8):
            lathe(add(Part(PLATE, 0, name="rivet")), [(0.12, 0), (0.1, 0.04), (0, 0.07)], 6, frame((-X0 - 0.56, y, z), (-1, 0, 0)))


def valve():
    """A two-inch butterfly valve on a moulded spigot, with its lever at closed, and the threaded cap on a tether."""
    axis = frame((0, -22.1, 9.0), (0, -1, 0))
    lathe(add(Part(TANK, 2, name="spigot")), [(3.0, -0.2), (3.0, 0.14), (2.5, 0.42), (2.1, 0.55)], 20, axis)
    lathe(add(Part(DARK, 3, bevel=0.02, angle=30, name="valve body")), [(2.05, 0.45), (2.05, 1.05), (1.72, 1.12), (1.72, 1.3)], 18, axis)
    lathe(add(Part(DARK, 2, bevel=0.03, angle=40, name="union")), [(1.62, 1.26), (1.62, 1.72)], 8, axis)
    lathe(add(Part(DARK, 3, bevel=0.012, angle=30, name="outlet cap")), [(1.38, 1.7), (1.38, 2.02), (1.26, 2.1), (0, 2.12)], 12, axis)
    # The lever and its stem, on top of the valve.
    lathe(add(Part(DARK, 2, name="stem")), [(0.36, 10.9), (0.36, 11.5), (0, 11.52)], 8, frame((0, -22.92, 0), (0, 0, 1)))
    box(add(Part(LEVER, 3, bevel=0.05, segs=2, angle=40, name="lever")), (-0.5, -23.5, 11.42), (4.2, -22.42, 11.84))
    box(add(Part(LEVER, 2, bevel=0.04, angle=40, name="lever hub")), (-0.72, -23.5, 11.3), (0.72, -22.34, 11.96))
    # The cap's tether, back to the cage.
    from build import spline

    tube(add(Part(ZINC, 1, name="tether")), spline([(1.1, -23.9, 8.4), (2.2, -24.1, 7.0), (3.4, -23.9, 7.8), (3.72, -23.2, 10.6), (3.8, -Y0, 13.9)], 3), 0.05, 5)


def geometry():
    tank()
    pallet()
    cage()
    valve()


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "it_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    kit.pack_real_scale(hw.data, SIZE, 4)

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
    density = SIZE * math.sqrt(uva / area3)
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

    lod("it_lod1", 1, 0.42)
    lod("it_lod2", 2, 0.16)
    with open(os.path.join(WORK, "ibc_tote.json"), "w") as h:
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
    hw = bpy.data.objects["it_lod0"]
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

    bake_one(SIZE, "EMIT", source("pos"), 1, "bake_it_pos")
    bake_one(SIZE, "EMIT", source("nor"), 1, "bake_it_nor")
    bake_one(SIZE, "EMIT", source("facts"), 1, "bake_it_facts")
    bake_one(AO_SIZE, "AO", None, 48, "bake_it_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["it_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"it_lod{lod}"]
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
        with open(os.path.join(out, f"ibc_tote_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Boxyard/ibc_tote_v2/ibc_tote.py\nmtllib ibc_tote.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl it_tote\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "ibc_tote.mtl"), "w", newline="\n") as h:
        h.write("newmtl it_tote\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/ibc_tote_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 28.0, 80.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Boxyard/ibc_tote_v2/ibc_tote.py
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
							{{ from = "it_tote.vmat" to = "{MATS}/it_tote.vmat" }}
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
    with open(os.path.join(out, "ibc_tote.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Boxyard/ibc_tote_v2/ibc_tote.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/it_tote_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/it_tote_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/it_tote_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/it_tote_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/it_tote_rough.png"
}}
"""
    with open(os.path.join(mats, "it_tote.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("ibc tote stages done", flush=True)
