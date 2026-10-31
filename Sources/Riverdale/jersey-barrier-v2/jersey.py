"""Jersey barrier v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python-exit-code 1 --python jersey.py -- <work dir> <project root> <build|bake|export> ...

The precast barrier Riverdale and Spillway use as cover, with the old model's exact F-shaped section, so its collision hull still fits:
32 tall, 24 at the foot, 9.5 at the top, 118 long, on the ground, centred on the origin with its length along X. New in the shape: a
real surface to chip, drain scuppers and lifting slots cut clean through as before, a cast-in lifting loop recess at each end, a broken
corner with rebar showing. Inches, engine axes.
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
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, frame, lathe, spline, tube  # noqa: E402

CONCRETE, RUST, STEEL = 0, 1, 2
MODEL = "models/props/riverdale/jersey_barrier_v2"
OUT = os.path.join(ROOT, "Assets", "models", "props", "riverdale", "jersey_barrier_v2")
BLEND = os.path.join(WORK, "jersey_build.blend")
RES = 2048
HALF = 59.0
RANGE = 160.0
# One broken corner: where the concrete has gone, and how far in.
BREAK = Vector((HALF, 3.2, 31.0))
BREAK_R = 5.2
rng = np.random.default_rng(1961)


def slope_y(z):
    return 8.5 - (z - 10.0) * (3.75 / 22.0)


def section():
    """Half the section's outline, foot to crown, with points close enough for chips to show. Y across, Z up."""
    half = [(12.0, 0.0), (12.0, 1.6), (12.0, 3.0)]
    half += [(12.0 - 3.5 * t, 3.0 + 7.0 * t) for t in (0.2, 0.4, 0.6, 0.8, 1.0)]
    half += [(slope_y(z), z) for z in (12.5, 15.0, 17.5, 20.0, 22.5, 25.0, 27.0, 28.8, 30.2, 31.0)]
    half += [(4.75 - 0.33, 31.68), (3.8, 32.0), (2.4, 32.0), (0.0, 32.0)]
    return half


def stations():
    """Along the barrier: close at the ends, where the wear is, and evenly spread between them."""
    tight = [0.0, 0.25, 0.7, 1.3, 2.1, 3.1, 4.4, 6.0, 8.0, 10.5]
    mid = list(np.linspace(13.5, HALF * 2 - 13.5, 34))
    return [-HALF + t for t in tight] + [-HALF + m for m in mid] + [HALF - t for t in reversed(tight)]


def chip_field(p):
    """How far this point is pushed in, by small chips along the arrises and the one broken corner."""
    y, z = abs(p.y), p.z
    near_end = max(0.0, 1.0 - (HALF - abs(p.x)) / 2.5)
    near_top = max(0.0, 1.0 - math.hypot(y - 4.2, z - 31.6) / 1.5)
    near_knee = max(0.0, 1.0 - math.hypot(y - 8.5, z - 10.0) / 1.3)
    wave = 0.5 + 0.5 * math.sin(p.x * 0.73 + y * 0.4 + 1.1) * math.sin(p.x * 0.31 + p.y * 1.7 + 0.4)
    bite = max(0.0, wave - 0.62) * 2.6
    depth = (0.55 * near_end + 0.5 * near_top + 0.22 * near_knee) * bite
    # The broken corner, rough-edged.
    d = (p - BREAK).length
    if d < BREAK_R:
        t = 1.0 - d / BREAK_R
        depth += 3.4 * t * t * (0.75 + 0.25 * math.sin(p.x * 3.1 + p.y * 2.3 + p.z * 1.7))
    return depth


def body():
    part = add(Part(CONCRETE, 3, name="barrier"))
    bm = part.bm
    half = section()
    outline = [(y, z) for y, z in half] + [(-y, z) for y, z in reversed(half[:-1])]
    n = len(outline)
    rings = []
    xs = stations()
    for x in xs:
        end = max(0.0, 1.0 - (HALF - abs(x)) / 1.0)
        ring = []
        for y, z in outline:
            # The ends chamfer in by an inch, as the old ones do, keeping the foot on the ground.
            inset = end
            yy = y - math.copysign(min(inset, abs(y)), y) if abs(y) > 0 else 0.0
            zz = z - inset * 0.9 if z > 0.1 else z
            p = Vector((x, yy, zz))
            # Soft unevenness from the form, and a slight wander along its length.
            lump = 0.05 * math.sin(x * 0.11 + 0.6) + 0.03 * math.sin(x * 0.37 + z * 0.3)
            if z > 0.1 and abs(y) > 1.0:
                p.y += math.copysign(lump, y)
            depth = chip_field(p) if z > 0.1 else 0.0
            if depth > 0.0:
                centre = Vector((p.x * 0.985, 0.0, 15.0))
                p = p + (centre - p).normalized() * depth
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(rings[0])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    return part


def cutter(lo, hi, round_top=0.0):
    """A box to cut with, in the barrier's coordinates, with a rounded top if asked."""
    verts = []
    faces = []
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    profile = [(x0, z0), (x1, z0)]
    if round_top:
        for k in range(7):
            a = math.radians(k * 15)
            profile.append((x1 - round_top + round_top * math.cos(a), z1 - round_top + round_top * math.sin(a)))
        for k in range(7):
            a = math.radians(90 + k * 15)
            profile.append((x0 + round_top + round_top * math.cos(a), z1 - round_top + round_top * math.sin(a)))
    else:
        profile += [(x1, z1), (x0, z1)]
    n = len(profile)
    for y in (y0, y1):
        verts += [(x, y, z) for x, z in profile]
    for k in range(n):
        faces.append((k, (k + 1) % n, n + (k + 1) % n, n + k))
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple(range(n, 2 * n)))
    mesh = bpy.data.meshes.new("cutter")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new("cutter", mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def cut_openings(part):
    """The scuppers, lifting slots and end recesses, cut through by a real boolean."""
    mesh = bpy.data.meshes.new("barrier")
    part.bm.to_mesh(mesh)
    ob = bpy.data.objects.new("barrier", mesh)
    bpy.context.scene.collection.objects.link(ob)
    cuts = []
    # Drain scuppers at the foot, as on the old model: 16 wide, 4 high, a quarter of the way along each side.
    for sx in (-1, 1):
        x = sx * HALF * 2 * 0.24
        cuts.append(cutter((x - 8.0, -14.0, -1.0), (x + 8.0, 14.0, 4.0), round_top=0.9))
    # Lifting slots through the top, as on the old model.
    for sx in (-1, 1):
        x = sx * (HALF - 19.0)
        cuts.append(cutter((x - 2.5, -14.0, 23.0), (x + 2.5, 14.0, 26.5), round_top=0.5))
    # A recess in each end, holding the connecting loops.
    for sx in (-1, 1):
        lo, hi = sorted((sx * (HALF - 1.6), sx * (HALF + 1.0)))
        cuts.append(cutter((lo, -2.6, 11.0), (hi, 2.6, 26.0)))
    bpy.context.view_layer.objects.active = ob
    for c in cuts:
        mod = ob.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = c
        mod.solver = "EXACT"
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    part.bm.free()
    part.bm = bm
    for c in cuts:
        bpy.data.objects.remove(c)
    bpy.data.objects.remove(ob)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    # Nothing sees the underside, so it takes no atlas. A plane through the origin adds nothing to the outward check's volume.
    bottom = [f for f in bm.faces if f.normal.z < -0.9 and f.calc_center_median().z < 0.05]
    bmesh.ops.delete(bm, geom=bottom, context="FACES_ONLY")


def fittings():
    # Rebar loops in each end recess, cast in, that the next barrier's pin passes through.
    for sx in (-1, 1):
        x = sx * (HALF - 1.5)
        for z in (14.5, 22.5):
            path = spline([(x, -1.7, z), (x + sx * 0.55, -1.5, z), (x + sx * 1.05, -0.7, z), (x + sx * 1.15, 0.0, z), (x + sx * 1.05, 0.7, z), (x + sx * 0.55, 1.5, z), (x, 1.7, z)], 3)
            tube(add(Part(RUST, 1, name="end loop")), path, 0.3, 8)
    # A galvanised identification plate on the end with the unbroken corner... held by two bolts.
    at = -HALF - 0.0
    bm_part = add(Part(STEEL, 1, bevel=0.03, angle=40, name="end plate"))
    kit.box(bm_part, (at + 0.5, 3.4, 15.0), (at + 0.75, 7.0, 19.0))
    for z in (15.7, 18.3):
        lathe(add(Part(STEEL, 0, bevel=0.02, angle=40, name="bolt")), [(0.3, 0), (0.3, 0.14), (0.2, 0.2), (0, 0.2)], 6, frame((at + 0.5, 5.2, z), (-1, 0, 0)))
    # Rebar bared by the broken corner. They stop inside the old bounds.
    for off, turn in (((-1.6, -0.6, -0.4), (0.92, 0.1, 0.3)), ((-2.6, 0.6, -1.6), (0.9, -0.1, 0.42)), ((-1.0, 0.9, -2.4), (0.8, 0.0, 0.55))):
        start = BREAK + Vector(off) - Vector((1.0, 0, 1.2))
        direction = Vector(turn).normalized()
        points = [start, start + direction * 1.0, start + direction * 2.0 + Vector((0.08, 0.05, -0.1))]
        tube(add(Part(RUST, 0, name="rebar")), spline(points, 3), 0.27, 8)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    barrier = body()
    cut_openings(barrier)
    fittings()
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    dev = kit.join_parts(kit.parts, "jb_lod0")
    dev.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = dev
    dev.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    dev.select_set(False)
    kit.pack_real_scale(dev.data, RES, 3)

    mesh = dev.data
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    # The packer doesn't reject an island wider than the atlas, and a barrier's long faces can be. An even scale keeps the real scale.
    largest = uv.max()
    if largest > 0.998:
        uv *= 0.998 / largest
        mesh.uv_layers["UVMap"].data.foreach_set("uv", uv)
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

    lod("jb_lod1", 1, 0.5)
    lod("jb_lod2", 2, 0.2)
    lod("jb_lod3", 2, 0.06)
    with open(os.path.join(WORK, "jersey.json"), "w") as h:
        json.dump(dict(density=density, range=RANGE, half=HALF, broken=list(BREAK), broken_r=BREAK_R), h)
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
    dev = bpy.data.objects["jb_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not dev
    bpy.ops.mesh.primitive_plane_add(size=500, location=(0, 0, -0.01))
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 9.0
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
            scale = 1 / RANGE if kind == "pos" else 0.5
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_jb_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_jb_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_jb_facts")
    bake_one(1024, "AO", None, 48, "bake_jb_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["jb_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2, 3):
        ob = bpy.data.objects[f"jb_lod{lod}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(50))
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
        with open(os.path.join(OUT, f"jersey_barrier_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Riverdale/jersey-barrier-v2/jersey.py\nmtllib jersey_barrier.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl jb_concrete\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(OUT, "jersey_barrier.mtl"), "w", newline="\n") as h:
        h.write("newmtl jb_concrete\nKd 1 1 1\nd 1\n")

    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/jersey_barrier_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 90.0, 220.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Riverdale/jersey-barrier-v2/jersey.py
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
							{{ from = "jb_concrete.vmat" to = "{MODEL}/jb_concrete.vmat" }}
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
    with open(os.path.join(OUT, "jersey_barrier.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Riverdale/jersey-barrier-v2/jersey.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MODEL}/jb_concrete_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/jb_concrete_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MODEL}/jb_concrete_metal.png"

	//---- Normal ----
	TextureNormal "{MODEL}/jb_concrete_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/jb_concrete_rough.png"
}}
"""
    with open(os.path.join(OUT, "jb_concrete.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("jersey stages done", flush=True)
