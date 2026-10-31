"""Traffic cone v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python cone.py -- <work dir> <project root> <build|bake|export> ...

A 28 in traffic cone at the size `boxyard_map.cone` makes it, standing on the ground about its origin: a moulded rubber base with a
chamfered edge, a collar and four ribs, and a soft plastic cone with an open tip and a hollow underneath, a little out of true from
being driven into. The reflective sleeves are painted, where the old cone has them. Inches, engine axes (Z up).
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

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, frame, lathe  # noqa: E402

BODY, BASE = 12, 13
FOLDER = "models/maps/boxyard/traffic_cone_v2"
OUT = os.path.join(WORK, "export")  # Outside Assets until the user approves: an open editor compiles whatever it finds there.
BLEND = os.path.join(WORK, "cone_build.blend")
NAME = "traffic_cone"
RES = 2048
POS_RANGE = 64.0  # The position bake spans this many inches.
HALF, PLATE = 7.0, 1.2
HOLE_R = 5.3  # The hole through the base.
HOLLOW_R, HOLLOW_Z = 4.72, 5.0  # Where the hollow inside the cone ends.
SIDES = 56
BEND = 0.16  # How far the tip leans, in inches.
SLEEVES = ((10.0, 14.0), (17.0, 20.0))  # The old cone's bands.
# Where the wall has been pushed in: angle in degrees, height, depth, half width round the cone and half height, in inches.
DENTS = ((-35.0, 7.0, 0.16, 2.2, 4.0), (128.0, 18.0, 0.1, 1.5, 3.0))
edge_lines = []


def wall_radius(z):
    """The old cone's taper: 5.6 in at the top of the base, 1 in at the tip."""
    return 5.6 - 4.6 / 26.8 * (z - PLATE)


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def drop_caps(part):
    """A lathe's end caps, where they'd only be hidden inside something else."""
    for face in [f for f in part.bm.faces if len(f.verts) > 4]:
        part.bm.faces.remove(face)


def body():
    part = piece(BODY, 3, name="cone")
    bm = part.bm
    heights = sorted({1.05, 27.6, *[e for pair in SLEEVES for e in pair], *[2.0 + 1.8 * k for k in range(14)]})
    heights = [z for k, z in enumerate(heights) if k == 0 or z - heights[k - 1] > 0.5]
    # Up from the hollow's ceiling, down its inside to the rim the base hides, then the outside.
    profile = [(HOLLOW_R, HOLLOW_Z), (5.1, 3.0), (5.42, 1.05)]
    profile += [(wall_radius(z), z) for z in heights]
    # Over the tip's rolled lip and a little way down its open throat.
    profile += [(1.09, 27.8), (1.06, 27.95), (0.98, 28.0), (0.88, 27.97), (0.82, 27.85), (0.8, 27.5), (0.76, 26.0)]
    rings = []
    for r, z in profile:
        ring = []
        lean = BEND * (z / 28.0) ** 2
        for k in range(SIDES):
            a = 2 * math.pi * k / SIDES
            d = r * (1.0 + 0.009 * math.sin(2 * a + 1.0) * math.sin(math.pi * z / 28.0))
            for deg, at, depth, wide, high in DENTS:
                arc = (a - math.radians(deg) + math.pi) % (2 * math.pi) - math.pi
                d -= depth * math.exp(-((arc * r / wide) ** 2) - ((z - at) / high) ** 2)
            ring.append(bm.verts.new((d * math.cos(a) + lean, d * math.sin(a), z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(SIDES):
            bm.faces.new((a[k], a[(k + 1) % SIDES], b[(k + 1) % SIDES], b[k]))
    # The throat's dark floor, and the hollow's ceiling: the cone is really hollow only as far up as a lying one shows.
    floor = bm.verts.new((BEND * (26.0 / 28.0) ** 2, 0.0, 26.0))
    ceiling = bm.verts.new((BEND * (HOLLOW_Z / 28.0) ** 2, 0.0, HOLLOW_Z))
    for k in range(SIDES):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % SIDES], floor))
        bm.faces.new((ceiling, rings[0][(k + 1) % SIDES], rings[0][k]))


def plate_angles():
    """Even all the way round, so the hole is round, and closer together at the corners, so they're round too."""
    even = [360.0 * k / SIDES for k in range(SIDES)]
    corners = [centre + step for centre in (45.0, 135.0, 225.0, 315.0) for step in (-5.0, -2.5, 0.0, 2.5, 5.0)]
    kept = sorted(set(a for a in even if all(abs(a - c) > 1.2 for c in corners)) | set(corners))
    return [math.radians(a) for a in kept]


def square_point(half, radius, a):
    """Where a ray from the middle at angle a meets a rounded square."""
    c, s = math.cos(a), math.sin(a)
    t = half / max(abs(c), abs(s))
    x, y = t * c, t * s
    inner = half - radius
    if abs(x) > inner and abs(y) > inner:
        cx, cy = math.copysign(inner, x), math.copysign(inner, y)
        along = c * cx + s * cy
        t = along + math.sqrt(along * along - (cx * cx + cy * cy - radius * radius))
        x, y = t * c, t * s
    return x, y


def base():
    plate = piece(BASE, 3, bevel=0.03, angle=30, name="base")
    bm = plate.bm
    angles = plate_angles()
    # Foot, side and a chamfer up to the top face.
    loops = [(HALF - 0.14, 1.0, 0.0), (HALF, 1.1, 0.12), (HALF, 1.1, 0.84), (HALF - 0.34, 1.0, PLATE)]
    rings = [[bm.verts.new((*square_point(h, r, a), z)) for a in angles] for h, r, z in loops]
    # A ring, not a plate: the top and the underside turn in to the hole the cone's hollow opens through.
    for z in (PLATE, 0.0):
        rings.append([bm.verts.new((HOLE_R * math.cos(a), HOLE_R * math.sin(a), z)) for a in angles])
    n = len(rings[0])
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))

    collar = piece(BASE, 2, name="collar")
    lathe(collar, [(6.35, PLATE - 0.02), (6.3, 1.34), (6.0, 1.64), (5.62, 1.88), (5.35, 1.94)], SIDES)
    drop_caps(collar)

    # Four ribs from the collar out to the corners.
    for k in range(4):
        a = math.radians(45 + 90 * k)
        m = frame((0.0, 0.0, 0.0), (0, 0, 1), (math.cos(a), math.sin(a), 0))
        rib = piece(BASE, 1, bevel=0.035, angle=30, name="rib")
        kit.box(rib, (6.1, -0.24, PLATE - 0.04), (8.55, 0.24, PLATE + 0.2), m)


def geometry():
    body()
    base()


def harden_all():
    """Settle each part's winding, note its convex edges for the wear, then bevel it."""
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                a, b = e.verts[0].co, e.verts[1].co
                count = max(1, int((b - a).length / 0.05))
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
    hw = kit.join_parts(kit.parts, "cone_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
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
        copy.name = copy.data.name = f"cone_lod{number}"
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

    lod(1, 2, 0.45)
    lod(2, 3, 0.16)
    np.save(os.path.join(WORK, "cone_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "cone.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE, bend=BEND, sleeves=SLEEVES, plate=PLATE), h)
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
    hw = bpy.data.objects["cone_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 4.0
    with open(os.path.join(WORK, "cone_baked_uv_hash.txt"), "w") as h:
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_tc_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_tc_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_tc_facts")
    bake_one(1024, "AO", None, 64, "bake_tc_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["cone_lod0"]) != open(os.path.join(WORK, "cone_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"cone_lod{number}"]
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
            h.write(f"# Generated by Sources/Boxyard/traffic_cone_v2/cone.py\nmtllib {NAME}.mtl\n")
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
// Generated by Sources/Boxyard/traffic_cone_v2/cone.py
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
    vmat = f"""// Generated by Sources/Boxyard/traffic_cone_v2/cone.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
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
	g_flMetalness "0.000"

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
print("cone stages done", flush=True)
