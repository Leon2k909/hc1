"""Cerro Blanco's garden boulders v2: sculpt them, bake them and write their files. Uses the capture flag's mesh toolkit to pack its atlas.

blender -b --factory-startup -t 4 --python-exit-code 1 --python rock.py -- <work dir> <project root> <atlas size> <build|bake|export> ...

The six boulders round bomb site B were convex hulls of 18 points, shaded flat, standing on a point. These are two real shapes: a high sculpt of a fractured,
bedded, weathered stone, baked onto a low mesh that sits down into the lawn. Two shapes in one atlas, placed at different turns and sizes. Foot on the
ground at the origin, inches, engine axes. The two are sculpted 400 apart along X, so their paint differs, and moved back when written.
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
RES = int(argv[2])
STAGES = argv[3:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as kit  # noqa: E402
from rock_noise import fbm, smooth  # noqa: E402

from build import Part  # noqa: E402

MODEL = "models/props/cerroblanco/boulder_v2"
OUT = os.path.join(ROOT, "Assets", "models", "props", "cerroblanco", "boulder_v2")
BLEND = os.path.join(WORK, "rock_build.blend")
RANGE = 1200.0
SUBDIVISIONS = 7
LOW_TRIS = 8000
# name, offset along X, seed, half sizes (x, y, z), planes that cut it. A long low stone and a taller rounder one, as the old six's sizes.
ROCKS = (("a", -200.0, 11, (36.0, 27.0, 30.0), 15), ("b", 200.0, 29, (31.0, 30.0, 34.0), 13))


def chips(p, cell, seed, slope):
    """Broken faces: each point takes the tilted plane of its nearest seed, so edges come out where the planes meet, as on split stone."""
    rng = np.random.default_rng(seed)
    lo, hi = p.min(0), p.max(0)
    count = max(int(np.prod((hi - lo) / cell)), 8)
    seeds = rng.uniform(lo, hi, (count, 3))
    tilts = rng.normal(size=(count, 3))
    tilts /= np.linalg.norm(tilts, axis=1, keepdims=True)
    nearest = np.empty(p.shape[0], np.int64)
    for start in range(0, p.shape[0], 4096):
        q = p[start : start + 4096]
        nearest[start : start + 4096] = ((q[:, None, :] - seeds[None, :, :]) ** 2).sum(-1).argmin(1)
    return ((p - seeds[nearest]) * tilts[nearest]).sum(1) * slope


def fractures(p, seed, half, count):
    """Real cracks are nearly flat breaks through the stone, not loops: planes through it, wavering a little, that fade out along their length."""
    rng = np.random.default_rng(seed)
    out = np.zeros(p.shape[0], np.float32)
    for k in range(count):
        normal = rng.normal(size=3)
        normal[2] *= 0.35
        normal /= np.linalg.norm(normal)
        through = rng.uniform(-0.55, 0.55, 3) * np.array(half)
        waver = 2.4 * fbm(p, 0.055, seed + 10 + k, 3)
        apart = np.abs((p - through) @ normal + waver)
        along = smooth(-0.18, 0.22, fbm(p, 0.028, seed + 20 + k, 2))
        out = np.maximum(out, (1.0 - smooth(0.05, 0.62, apart)) * along)
    return out


def sculpt(directions, seed, half, planes):
    """Where each unit direction lands, and three masks for the paint: cracks, ledges and how exposed it stands."""
    rng = np.random.default_rng(seed)
    # A stone broken from a bed: planes cut it, with their corners worn round. Six more keep any corner from running out to a spike.
    normals = rng.normal(size=(planes, 3))
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    heights = rng.uniform(0.74, 1.04, planes)
    normals = np.vstack((normals, np.array(((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)), float)))
    heights = np.concatenate((heights, np.full(6, 1.08)))
    along = directions @ normals.T
    reach = heights[None, :] / np.maximum(along, 1e-3)
    k = 13.0
    radius = -np.log(np.exp(-k * np.minimum(reach, 6.0)).sum(1)) / k
    p = directions * radius[:, None] * np.array(half)
    # Large lumps, so the faces aren't flat.
    lumps = fbm(p, 0.032, seed + 1, 3)
    ridges = 1.0 - np.abs(fbm(p, 0.075, seed + 2, 3)) * 2.0
    # Bedding: thin ledges along a tilted plane, wavering, and only in places.
    axis = rng.normal(size=3)
    axis[2] = abs(axis[2]) * 2.5
    axis /= np.linalg.norm(axis)
    level = p @ axis + 5.0 * fbm(p, 0.04, seed + 3, 2)
    saw = (level * 0.31) % 1.0
    ledge_shape = smooth(0.0, 0.1, saw) * (1.0 - smooth(0.62, 1.0, saw))
    ledge_where = smooth(-0.15, 0.3, fbm(p, 0.05, seed + 4, 2))
    crack = fractures(p, seed + 40, half, 4)
    broken = chips(p, 13.0, seed + 5, 0.2) + chips(p, 4.6, seed + 6, 0.16)
    grain = fbm(p, 0.42, seed + 8, 3)
    fine = fbm(p, 1.5, seed + 9, 2)
    push = 2.3 * lumps + 0.6 * ridges + broken + 0.42 * ledge_shape * ledge_where + 0.26 * grain + 0.09 * fine - 1.1 * crack
    p = p + directions * push[:, None]
    # Its top at the old stone's height and about a third as much again under the lawn, and as wide and long at the ground as the old stone.
    top, foot = p[:, 2].max(), p[:, 2].min()
    p[:, 2] = (p[:, 2] - top) * (half[2] * 1.35 / (top - foot)) + half[2]
    above = p[p[:, 2] > 0]
    for axis_index in (0, 1):
        low, high = above[:, axis_index].min(), above[:, axis_index].max()
        p[:, axis_index] = (p[:, axis_index] - (low + high) / 2) * (2 * half[axis_index] / (high - low))
    exposed = np.clip(0.5 + 0.5 * (lumps * 0.6 + ridges * 0.4), 0, 1)
    return p, np.column_stack((crack, ledge_shape * ledge_where, exposed)).astype(np.float32)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    lows = []
    for name, offset, seed, half, planes in ROCKS:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=SUBDIVISIONS, radius=1.0)
        bm.verts.ensure_lookup_table()
        directions = np.array([v.co for v in bm.verts], np.float64)
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        positions, masks = sculpt(directions, seed, half, planes)
        print(name, "height", positions[:, 2].max(), "foot", positions[:, 2].min(), "x", positions[:, 0].min(), positions[:, 0].max(), "y", positions[:, 1].min(), positions[:, 1].max(), flush=True)
        positions[:, 0] += offset
        for v, co in zip(bm.verts, positions):
            v.co = co
        mesh = bpy.data.meshes.new(f"high_{name}")
        bm.to_mesh(mesh)
        bm.free()
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        colour = mesh.color_attributes.new("masks", "FLOAT_COLOR", "POINT")
        colour.data.foreach_set("color", np.column_stack((masks, np.ones(len(masks), np.float32))).ravel())
        high = bpy.data.objects.new(f"high_{name}", mesh)
        scene.collection.objects.link(high)
        # The low mesh, from the sculpt, with what's under the lawn taken off.
        low_mesh = mesh.copy()
        low_mesh.name = f"low_{name}"
        low = bpy.data.objects.new(f"low_{name}", low_mesh)
        scene.collection.objects.link(low)
        bpy.context.view_layer.objects.active = low
        low.select_set(True)
        mod = low.modifiers.new("collapse", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = (LOW_TRIS * 1.25) / len(mesh.polygons)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        low.select_set(False)
        part = Part(0, 3, name=name)
        part.bm.from_mesh(low.data)
        doomed = [f for f in part.bm.faces if max(v.co.z for v in f.verts) < -2.5]
        bmesh.ops.delete(part.bm, geom=doomed, context="FACES")
        bmesh.ops.triangulate(part.bm, faces=part.bm.faces)
        part.done = part.bm
        part.rand = 0.25 if name == "a" else 0.75
        kit.parts.append(part)
        lows.append(low)
        print(name, "low tris", len(part.bm.faces), flush=True)
    for low in lows:
        bpy.data.objects.remove(low)
    dev = kit.join_parts(kit.parts, "rk_lod0")
    dev.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = dev
    dev.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # A low limit, so a stone's big rounded faces part into pieces. As one island each, they left most of the atlas empty.
    bpy.ops.uv.smart_project(angle_limit=math.radians(34), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    dev.select_set(False)
    kit.pack_real_scale(dev.data, RES, 6)
    mesh = dev.data
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
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

    # One object per stone and per LOD, each keeping the atlas's UVs.
    for name, offset, _, _, _ in ROCKS:
        for lod, ratio in enumerate((1.0, 0.42, 0.16, 0.05)):
            copy = dev.copy()
            copy.data = dev.data.copy()
            copy.name = copy.data.name = f"rk_{name}_lod{lod}"
            scene.collection.objects.link(copy)
            bm = bmesh.new()
            bm.from_mesh(copy.data)
            other = [f for f in bm.faces if (f.calc_center_median().x > 0) != (offset > 0)]
            bmesh.ops.delete(bm, geom=other, context="FACES")
            bm.to_mesh(copy.data)
            bm.free()
            if ratio < 1.0:
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
    with open(os.path.join(WORK, "rock.json"), "w") as h:
        json.dump(dict(density=density, range=RANGE, res=RES), h)
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
    dev = bpy.data.objects["rk_lod0"]
    highs = [bpy.data.objects[f"high_{r[0]}"] for r in ROCKS]
    for ob in scene.objects:
        ob.hide_render = ob is not dev and ob not in highs
    bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 14.0
    with open(os.path.join(WORK, "baked_uv_hash.txt"), "w") as h:
        h.write(uv_hash(dev))

    def emit_from(attribute):
        mat = bpy.data.materials.new("masks")
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        e = nt.nodes.new("ShaderNodeEmission")
        a = nt.nodes.new("ShaderNodeVertexColor")
        a.layer_name = attribute
        nt.links.new(a.outputs[0], e.inputs[0])
        nt.links.new(e.outputs[0], o.inputs[0])
        return mat

    masks_material = emit_from("masks")
    for high in highs:
        high.data.materials.clear()
        high.data.materials.append(masks_material)

    def target(size, out, setup=None):
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
        return img

    def finish(img, size, out):
        data = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(size, size, 4))
        bpy.data.images.remove(img)
        print("baked", out, flush=True)

    def select_for(from_high):
        bpy.ops.object.select_all(action="DESELECT")
        if from_high:
            for high in highs:
                high.select_set(True)
        bpy.context.view_layer.objects.active = dev
        dev.select_set(True)

    def geometry(kind):
        def setup(nt, emit):
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            mapped = nt.nodes.new("ShaderNodeVectorMath")
            mapped.operation = "MULTIPLY_ADD"
            scale = 1 / RANGE if kind == "pos" else 0.5
            mapped.inputs[1].default_value = (scale, scale, scale)
            mapped.inputs[2].default_value = (0.5, 0.5, 0.5)
            nt.links.new(geo.outputs["Position" if kind == "pos" else "Normal"], mapped.inputs[0])
            nt.links.new(mapped.outputs[0], emit.inputs[0])

        return setup

    # What the paint works from: where each texel is, and which way the low mesh faces there.
    for kind in ("pos", "nor"):
        img = target(RES, f"bake_rk_{kind}", geometry(kind))
        select_for(False)
        scene.cycles.samples = 1
        bpy.ops.object.bake(type="EMIT", margin=0, use_clear=True, target="IMAGE_TEXTURES")
        finish(img, RES, f"bake_rk_{kind}")
    # From the sculpt: its normals in tangent space, its masks and its occlusion.
    img = target(RES, "bake_rk_tangent")
    select_for(True)
    scene.cycles.samples = 1
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_selected_to_active=True, cage_extrusion=3.5, max_ray_distance=7.0, margin=0, use_clear=True, target="IMAGE_TEXTURES")
    finish(img, RES, "bake_rk_tangent")
    img = target(RES, "bake_rk_masks")
    select_for(True)
    bpy.ops.object.bake(type="EMIT", use_selected_to_active=True, cage_extrusion=3.5, max_ray_distance=7.0, margin=0, use_clear=True, target="IMAGE_TEXTURES")
    finish(img, RES, "bake_rk_masks")
    size = min(RES, 2048)
    img = target(size, "bake_rk_ao")
    select_for(True)
    scene.cycles.samples = 32
    bpy.ops.object.bake(type="AO", use_selected_to_active=True, cage_extrusion=3.5, max_ray_distance=7.0, margin=0, use_clear=True, target="IMAGE_TEXTURES")
    finish(img, size, "bake_rk_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["rk_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    for name, offset, _, _, _ in ROCKS:
        counts = {}
        for lod in range(4):
            ob = bpy.data.objects[f"rk_{name}_lod{lod}"]
            # Plain smooth normals: the tangent bake was made against these, so splitting or weighting them here would bend its light.
            em = ob.data
            em.polygons.foreach_set("use_smooth", np.ones(len(em.polygons), bool))
            em.calc_loop_triangles()
            n_loops, n_tris = len(em.loops), len(em.loop_triangles)
            loops = np.empty(n_tris * 3, np.int32)
            em.loop_triangles.foreach_get("loops", loops)
            verts = np.empty(n_loops, np.int32)
            em.loops.foreach_get("vertex_index", verts)
            co = np.empty(len(em.vertices) * 3)
            em.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            co[:, 0] -= offset
            uv = np.empty(n_loops * 2)
            em.uv_layers["UVMap"].data.foreach_get("uv", uv)
            nn = np.empty(n_loops * 3)
            em.corner_normals.foreach_get("vector", nn)
            p = co[verts[loops]][:, [1, 2, 0]]
            t = uv.reshape(-1, 2)[loops]
            n = nn.reshape(-1, 3)[loops][:, [1, 2, 0]]
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
            with open(os.path.join(OUT, f"boulder_{name}_lod{lod}.obj"), "w", newline="\n") as h:
                h.write("# Generated by Sources/CerroBlanco/boulder-v2/rock.py\nmtllib boulder.mtl\n")
                for block in lines:
                    h.writelines(block)
                h.write("usemtl bd_rock\n")
                h.writelines(faces)
            counts[lod] = n_tris
        print("exported", name, counts, flush=True)
        # Collision: one convex hull round the far LOD, down to just under the lawn.
        ob = bpy.data.objects[f"rk_{name}_lod2"]
        bm = bmesh.new()
        for v in ob.data.vertices:
            bm.verts.new((v.co.x - offset, v.co.y, max(v.co.z, -2.0)))
        hull = bmesh.ops.convex_hull(bm, input=bm.verts)
        interior = set(hull["geom_interior"]) | set(hull["geom_unused"])
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v in interior], context="VERTS")
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.verts.index_update()
        with open(os.path.join(OUT, f"boulder_{name}_hull.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/CerroBlanco/boulder-v2/rock.py: collision\no boulder_{name}_hull\n")
            for v in bm.verts:
                h.write(f"v {v.co.y:.3f} {v.co.z:.3f} {v.co.x:.3f}\n")
            for f in bm.faces:
                h.write("f " + " ".join(str(v.index + 1) for v in f.verts) + "\n")
        print("hull", name, len(bm.verts), "verts", len(bm.faces), "faces", flush=True)
        bm.free()
        meshes = ",\n".join(
            f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/boulder_{name}_lod{l}.obj" '
            'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
            'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
            "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
        )
        groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 90.0, 220.0)))
        doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/CerroBlanco/boulder-v2/rock.py
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
							{{ from = "bd_rock.vmat" to = "{MODEL}/bd_rock.vmat" }}
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
			{{
				_class = "PhysicsShapeList"
				children =
				[
					{{
						_class = "PhysicsHullFile"
						name = "boulder_{name}_hull"
						parent_bone = ""
						surface_prop = "default"
						collision_tags = "solid"
						recenter_on_parent_bone = false
						offset_origin = [ 0.0, 0.0, 0.0 ]
						offset_angles = [ 0.0, 0.0, 0.0 ]
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						filename = "{MODEL}/boulder_{name}_hull.obj"
						import_scale = 1.0
						faceMergeAngle = 10.0
						maxHullVertices = 64
						import_mode = "HullPerElement"
						optimization_algorithm = "QEM"
						import_filter = {{ exclude_by_default = false exception_list = [ ] }}
					}},
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
        with open(os.path.join(OUT, f"boulder_{name}.vmdl"), "w", newline="\n") as h:
            h.write(doc)
    with open(os.path.join(OUT, "boulder.mtl"), "w", newline="\n") as h:
        h.write("newmtl bd_rock\nKd 1 1 1\nd 1\n")
    vmat = f"""// Generated by Sources/CerroBlanco/boulder-v2/rock.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_SPECULAR 1
	g_flMetalness "0.000"

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MODEL}/bd_rock_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/bd_rock_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Normal ----
	TextureNormal "{MODEL}/bd_rock_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/bd_rock_rough.png"
}}
"""
    with open(os.path.join(OUT, "bd_rock.vmat"), "w", newline="\n") as h:
        h.write(vmat)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("rock stages done", flush=True)
