"""Boxyard's steel drum v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python oil_drum.py -- <work dir> <project root> <build|bake|export> ...

A 205 l tight-head drum at the size `boxyard_map.drum` makes it, standing on the ground about its origin: rolled chimes top and
bottom, two rolling hoops, swaged beads, a dished head with its two bungs, and the dents a drum picks up. The body is one
strip of UVs seamed at its weld. One mesh, with a material each for the map's blue and red. Its floor is on the ground, so it
isn't modelled. Inches, engine axes (Z up).
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

PAINT, ZINC = kit.PAINT, kit.ZINC
FOLDER = "models/maps/boxyard/oil_drum_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "boxyard", "oil_drum_v2")
BLEND = os.path.join(WORK, "oil_drum_build.blend")
NAME = "oil_drum"
COLOURS = ("blue", "red")
RES = 2048
POS_RANGE = 96.0  # The position bake spans this many inches.
R, TOP = 11.25, 34.8
HEAD_Z = 34.1
HOOPS = (11.7, 23.1)
BEADS = (5.8, 17.4, 29.0)
SIDES = 48
# Where each dent is: angle in degrees, height, depth, half width round the drum and half height, in inches.
DENTS = ((78.0, 7.0, 0.62, 3.8, 2.6), (205.0, 27.2, 0.46, 3.2, 3.8), (312.0, 17.6, 0.32, 5.0, 2.3), (140.0, 23.1, 0.42, 2.8, 1.5), (25.0, 2.6, 0.32, 3.0, 1.5))
edge_lines = []


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def shell_profile():
    """The outside, bottom to top, each hoop and bead a little S of rings. Plain lengths get rings too, so the dents can bend."""
    points = [(10.72, 0.35), (10.84, 0.08), (11.02, 0.0), (11.32, 0.0), (11.52, 0.1), (11.6, 0.32), (11.52, 0.54), (R, 0.72)]

    def plain(z0, z1):
        count = max(1, int(round((z1 - z0) / 3.0)))
        return [(R, z0 + (z1 - z0) * k / count) for k in range(1, count + 1)]

    def bead(z):
        return [(R - 0.05, z - 0.1), (R - 0.07, z), (R - 0.05, z + 0.1), (R, z + 0.2)]

    def hoop(z):
        return [(R + 0.18, z - 0.3), (R + 0.46, z - 0.12), (R + 0.46, z + 0.12), (R + 0.18, z + 0.3), (R, z + 0.44)]

    z = 0.72
    for at, make in ((BEADS[0], bead), (HOOPS[0], hoop), (BEADS[1], bead), (HOOPS[1], hoop), (BEADS[2], bead)):
        start = at - (0.2 if make is bead else 0.44)
        points += plain(z, start)
        points += make(at)
        z = at + (0.2 if make is bead else 0.44)
    points += plain(z, 34.08)
    points += [(11.52, 34.26), (11.6, 34.48), (11.52, 34.7), (11.32, TOP), (11.02, TOP), (10.84, 34.72), (10.72, 34.45)]
    return points


def dented(k, r, z):
    """How far a body vertex moves in or out: a drum isn't quite round, and it has been knocked about."""
    if not 0.72 <= z <= 34.08:
        return r
    a = 2 * math.pi * k / SIDES
    r += 0.05 * math.sin(2 * a + 1.0) * math.sin(math.pi * z / TOP)
    for deg, at, depth, wide, high in DENTS:
        arc = (a - math.radians(deg) + math.pi) % (2 * math.pi) - math.pi
        r -= depth * math.exp(-((arc * R / wide) ** 2) - ((z - at) / high) ** 2)
    return r


def shell():
    """The body. It's built first, so a vertex's number says which ring and column it's on when its UVs are laid out."""
    part = piece(PAINT, 3, name="shell")
    bm = part.bm
    profile = shell_profile()
    rings = []
    for r, z in profile:
        ring = []
        for k in range(SIDES):
            a = 2 * math.pi * k / SIDES
            d = dented(k, r, z)
            ring.append(bm.verts.new((d * math.cos(a), d * math.sin(a), z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(SIDES):
            bm.faces.new((a[k], a[(k + 1) % SIDES], b[(k + 1) % SIDES], b[k]))
    # Along the profile, for the strip's UVs.
    s = [0.0]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        s.append(s[-1] + math.hypot(r1 - r0, z1 - z0))
    part.strip = s


def head():
    """The top: dished down inside the chime, with a stiffening ring pressed into it."""
    profile = [(10.82, 34.5), (10.5, 34.2), (10.2, HEAD_Z + 0.02), (9.6, HEAD_Z), (8.55, HEAD_Z), (8.4, HEAD_Z + 0.07), (8.15, HEAD_Z + 0.07), (8.0, HEAD_Z), (3.0, HEAD_Z + 0.015), (0.0, HEAD_Z + 0.02)]
    # A lathe winds for a profile climbing z, so it's listed from the middle out and left to harden_all to settle.
    lathe(piece(PAINT, 3, name="head"), list(reversed(profile)), 32)


def bungs():
    for x, r, lugs in ((6.5, 1.3, 2), (-6.5, 0.8, 1)):
        at = (x, 0.0, HEAD_Z)
        flange = [(r + 0.34, 0.0), (r + 0.34, 0.1), (r + 0.26, 0.2), (r + 0.08, 0.24)]
        lathe(piece(ZINC, 2, bevel=0.015, name="flange"), flange, 20, frame(at))
        cap = [(r - 0.06, 0.2), (r, 0.3), (r, 0.46), (r - 0.1, 0.54), (0.0, 0.54)]
        lathe(piece(ZINC, 2, bevel=0.012, name="cap"), cap, 16 if r > 1 else 12, frame(at))
        for k in range(lugs):
            turn = math.radians(90 * k + 22)
            m = frame(at, (0, 0, 1), (math.cos(turn), math.sin(turn), 0))
            kit.box(piece(ZINC, 0, bevel=0.02, name="lug"), (-r * 0.82, -0.14, 0.5), (r * 0.82, 0.14, 0.65), m)


def geometry():
    shell()
    head()
    bungs()


def harden_all():
    """Settle each part's winding, note its convex edges for the wear, then bevel it. The shell keeps its vertex order."""
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish == PAINT:
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.1))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))


def lay_out_strip(mesh, strip):
    """The body's UVs: one strip, real size, seamed where the drum is welded (column 0). The packer treats it as one island."""
    rows = len(strip)
    layer = mesh.uv_layers["UVMap"].data
    circle = 2 * math.pi * R
    for poly in mesh.polygons:
        indices = [mesh.loops[i].vertex_index for i in poly.loop_indices]
        if max(indices) >= rows * SIDES:
            continue
        columns = [v % SIDES for v in indices]
        wrap = max(columns) == SIDES - 1 and min(columns) == 0
        for loop_index, v, column in zip(poly.loop_indices, indices, columns):
            if wrap and column == 0:
                column = SIDES
            layer[loop_index].uv = (column / SIDES * circle, strip[v // SIDES])


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    strip = kit.parts[0].strip
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "oil_drum_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    lay_out_strip(hw.data, strip)
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
        copy.name = copy.data.name = f"oil_drum_lod{number}"
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

    lod(1, 1, 0.42)
    lod(2, 2, 0.14)
    np.save(os.path.join(WORK, "oil_drum_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "oil_drum.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE, radius=R, top=TOP, head_z=HEAD_Z, hoops=HOOPS, beads=BEADS), h)
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
    hw = bpy.data.objects["oil_drum_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 5.0
    with open(os.path.join(WORK, "oil_drum_baked_uv_hash.txt"), "w") as h:
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_od_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_od_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_od_facts")
    bake_one(1024, "AO", None, 64, "bake_od_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["oil_drum_lod0"]) != open(os.path.join(WORK, "oil_drum_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"oil_drum_lod{number}"]
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
            h.write(f"# Generated by Sources/Boxyard/oil_drum_v2/oil_drum.py\nmtllib {NAME}.mtl\n")
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
    for colour in COLOURS:
        doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Boxyard/oil_drum_v2/oil_drum.py
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
							{{ from = "{NAME}.vmat" to = "{FOLDER}/{NAME}_{colour}.vmat" }}
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
        with open(os.path.join(OUT, f"{NAME}_{colour}.vmdl"), "w", newline="\n") as h:
            h.write(doc)
        vmat = f"""// Generated by Sources/Boxyard/oil_drum_v2/oil_drum.py

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
	TextureColor "{FOLDER}/{NAME}_{colour}_color.png"

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
        with open(os.path.join(OUT, f"{NAME}_{colour}.vmat"), "w", newline="\n") as h:
            h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("oil drum stages done", flush=True)
