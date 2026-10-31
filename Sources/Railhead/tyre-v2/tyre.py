"""Railhead's stacked tyres v2: sculpt them, bake them and write their files.

blender -b --factory-startup -t 4 --python-exit-code 1 --python tyre.py -- <work dir> <project root> <build|bake|export> ...

The old tyres were drums with rounded rims and 32 black stickers for tread. These are a real car tyre, 650 mm across and 205 mm tall as the old ones were, and hollow, so you can look into the hole and see its liner.
A high sculpt with real grooves, blocks, shoulder lugs and sidewall ribs is baked onto a turned low mesh. Two tyres share one atlas: a used one and a nearly bald one. Each lies flat with its foot on the ground at the
origin and its axis up. They're sculpted 100 apart along X, so their paint differs, and moved back when written. Inches, engine axes.
"""
import hashlib
import json
import math
import os
import sys

sys.dont_write_bytecode = True
import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "CerroBlanco", "boulder-v2"))
from rock_noise import fbm, smooth  # noqa: E402

MODEL = "models/props/railhead/tyre_v2"
OUT = os.path.join(ROOT, "Assets", "models", "props", "railhead", "tyre_v2")
BLEND = os.path.join(WORK, "tyre_build.blend")
RES = 2048
RANGE = 400.0
CENTRE_Z = 4.035
# name, offset along X, tread depth, UV row
TYRES = (("a", -50.0, 0.3, (0.01, 0.49)), ("b", 50.0, 0.11, (0.51, 0.99)))
# LOD: sides, points round the section
LODS = ((72, 30), (44, 19), (26, 12), (14, 8))
# How much atlas the inside of the tyre gets, against the outside's 1.
LINER_WEIGHT = 0.3


def section():
    """The tyre's section as a closed loop of (r, dz), from the lower bead out over the tread to the upper bead, and back along the liner. And which points are liner."""
    side = [(8.25, 3.05), (8.5, 3.25), (8.75, 3.35), (9.4, 3.7), (10.2, 3.98), (10.9, 4.03), (11.5, 3.92), (11.95, 3.62), (12.3, 3.3), (12.6, 2.9), (12.75, 2.4), (12.8, 1.2)]
    outer = [(r, -d) for r, d in side] + [(12.82, 0.0)] + [(r, d) for r, d in reversed(side)]
    half = [(8.2, 2.7), (8.45, 2.35), (8.8, 2.6), (9.3, 3.1), (10.3, 3.4), (11.2, 3.2), (11.8, 2.6), (12.05, 1.4)]
    liner = half + [(12.1, 0.0)] + [(r, -d) for r, d in reversed(half)]
    points = np.array(outer + liner, float)
    is_liner = np.array([False] * len(outer) + [True] * len(liner))
    return points, is_liner


def resample(count, tread_share=None):
    """Points along the closed section, smoothed. Returns r, dz, outward normal (nr, nz), arc length from the start, and the liner flag. tread_share gives the tread that share of the points."""
    points, is_liner = section()
    # Catmull-Rom, densely, then pick by arc length.
    n = len(points)
    fine = []
    flags = []
    for i in range(n):
        p0, p1, p2, p3 = points[(i - 1) % n], points[i], points[(i + 1) % n], points[(i + 2) % n]
        for k in range(24):
            t = k / 24
            fine.append(0.5 * ((2 * p1) + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t * t * t))
            flags.append(is_liner[i])
    fine = np.array(fine)
    flags = np.array(flags)
    closed = np.vstack((fine, fine[:1]))
    steps = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    arc = np.concatenate(([0.0], np.cumsum(steps)))
    total = arc[-1]
    if tread_share:
        # More points where the tread is: weight each stretch of arc.
        weight = np.where((fine[:, 0] > 12.1) & ~flags & (np.abs(fine[:, 1]) < 3.7), 1.0 / tread_share, 1.0)
        warped = np.concatenate(([0.0], np.cumsum(steps * weight)))
        picks = np.linspace(0, warped[-1], count, endpoint=False)
        at = np.interp(picks, warped, arc)
    else:
        at = np.linspace(0, total, count, endpoint=False)
    r = np.interp(at, arc, closed[:, 0])
    dz = np.interp(at, arc, closed[:, 1])
    liner = np.interp(at, arc[:-1], flags.astype(float)) > 0.5
    # Normals from neighbours, outward from the section's solid: the loop runs so that its right-hand side is outside.
    tr = np.roll(r, -1) - np.roll(r, 1)
    tz = np.roll(dz, -1) - np.roll(dz, 1)
    length = np.maximum(np.hypot(tr, tz), 1e-9)
    nr, nz = tz / length, -tr / length
    # Check the guess: the tread's crown must face out.
    crown = np.argmax(r * (~liner))
    if nr[crown] < 0:
        nr, nz = -nr, -nz
    return r, dz, nr, nz, at, liner, total


def uv_v(at, liner, total, row):
    """Where each point of the section falls across its row: the outside at full size and the liner smaller, since it's hardly seen."""
    r, dz, _, _, fine_at, fine_liner, _ = resample(2000)
    ds = np.diff(np.concatenate((fine_at, [total])))
    weight = np.where(fine_liner, LINER_WEIGHT, 1.0)
    cumulative = np.concatenate(([0.0], np.cumsum(ds * weight)))
    v = np.interp(at, np.concatenate((fine_at, [total])), cumulative) / cumulative[-1]
    return row[0] + v * (row[1] - row[0]), cumulative[-1]


def grid(sides, count, name, offset, row, normals_out=True):
    """A turned mesh: positions, normals, UVs and quads, with a seam both ways, so the UVs can wrap."""
    r, dz, nr, nz, at, liner, total = resample(count)
    v_row, _ = uv_v(at, liner, total, row)
    v_end = row[1]
    r = np.concatenate((r, r[:1]))
    dz = np.concatenate((dz, dz[:1]))
    nr = np.concatenate((nr, nr[:1]))
    nz = np.concatenate((nz, nz[:1]))
    v = np.concatenate((v_row, [v_end]))
    theta = np.linspace(0, 2 * math.pi, sides + 1)
    tt, jj = np.meshgrid(theta, np.arange(count + 1), indexing="ij")
    rr, zz = r[jj], dz[jj]
    pos = np.stack((np.cos(tt) * rr + offset, np.sin(tt) * rr, zz + CENTRE_Z), -1).reshape(-1, 3)
    nor = np.stack((np.cos(tt) * nr[jj], np.sin(tt) * nr[jj], nz[jj]), -1).reshape(-1, 3)
    uvs = np.stack((tt / (2 * math.pi) * 0.998 + 0.001, v[jj]), -1).reshape(-1, 2)
    quads = []
    stride = count + 1
    for i in range(sides):
        for j in range(count):
            a, b, c, d = i * stride + j, (i + 1) * stride + j, (i + 1) * stride + j + 1, i * stride + j + 1
            quads.append((a, b, c, d))
    return pos, nor, uvs, np.array(quads)


def wound_outward(pos, nor, quads):
    """Which way round the quads must go for their faces to agree with the normals."""
    q = quads[:: max(len(quads) // 50, 1)]
    cross = np.cross(pos[q[:, 1]] - pos[q[:, 0]], pos[q[:, 3]] - pos[q[:, 0]])
    return float((cross * nor[q[:, 0]]).sum()) > 0


def sculpt(name, offset, depth):
    """The high mesh: real grooves in the tread and ribs on the sidewalls. A groove mask goes with it for the paint."""
    sides, count = 1300, 260
    r, dz, nr, nz, at, liner, total = resample(count, tread_share=0.62)
    theta = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    tt, jj = np.meshgrid(theta, np.arange(count), indexing="ij")
    rr, zz = r[jj], dz[jj]
    outside = ~liner[jj]
    # Distance across the tread from its middle line. dz does for this, near enough, since the crown is nearly flat.
    w = zz
    on_tread = (rr > 12.1) & outside
    # Rain grooves running round it.
    round_grooves = np.zeros_like(rr)
    for centre in (-2.25, -0.85, 0.85, 2.25):
        round_grooves = np.maximum(round_grooves, 1.0 - smooth(0.09, 0.17, np.abs(w - centre)))
    # Blocks: grooves across, swept back from the middle, staggered row to row, and wider lugs at the shoulders.
    pitch_mid = 62
    phase = tt * pitch_mid / (2 * math.pi) + np.abs(w) * 0.42 + np.where(w > 0, 0.5, 0.0)
    across_mid = (1.0 - smooth(0.05, 0.1, np.abs(phase - np.floor(phase) - 0.5) / pitch_mid * (2 * math.pi * 12.8))) * ((np.abs(w) > 0.85) & (np.abs(w) < 2.25))
    pitch_shoulder = 48
    phase = tt * pitch_shoulder / (2 * math.pi) + np.where(w > 0, 0.5, 0.0)
    across_shoulder = (1.0 - smooth(0.09, 0.16, np.abs(phase - np.floor(phase) - 0.5) / pitch_shoulder * (2 * math.pi * 12.8))) * (np.abs(w) >= 2.25)
    groove = np.maximum.reduce((round_grooves, across_mid, across_shoulder)) * on_tread
    fade = smooth(3.9, 3.3, np.abs(w))
    groove = groove * fade
    push = -depth * groove
    # The tread's blocks are worn round at their tops, and a bald tyre has hardly any crown left.
    push = push + (0.22 - depth) * 0.14 * on_tread
    # The sidewall: the rim guard, a rib where it bulges, and fine serrations up by the shoulder.
    side_part = outside & (rr < 12.2)
    push = push + 0.09 * (1.0 - smooth(0.0, 0.14, np.abs(rr - 9.05))) * side_part
    push = push + 0.05 * (1.0 - smooth(0.0, 0.09, np.abs(rr - 11.35))) * side_part
    teeth = np.abs(((tt * 180 / math.pi * 2.0) % 1.0) - 0.5) * 2.0
    push = push + 0.03 * teeth * smooth(11.5, 11.65, rr) * smooth(12.15, 12.0, rr) * outside
    # A real tyre isn't perfectly round: a slight wander, and the bald one has taken a knock.
    points = np.stack((np.cos(tt) * rr, np.sin(tt) * rr, zz), -1).reshape(-1, 3).astype(np.float32)
    lump = fbm(points, 0.09, 301 + (name == "b"), 2).reshape(rr.shape)
    push = push + lump * (0.05 if name == "a" else 0.11) * outside
    rr2 = rr + nr[jj] * push
    zz2 = zz + nz[jj] * push
    pos = np.stack((np.cos(tt) * rr2 + offset, np.sin(tt) * rr2, zz2 + CENTRE_Z), -1).reshape(-1, 3)
    i = np.arange(sides)
    j = np.arange(count)
    ii, jj2 = np.meshgrid(i, j, indexing="ij")
    a = ii * count + jj2
    b = ((ii + 1) % sides) * count + jj2
    c = ((ii + 1) % sides) * count + (jj2 + 1) % count
    d = ii * count + (jj2 + 1) % count
    quads = np.stack((a, b, c, d), -1).reshape(-1, 4)
    mesh = bpy.data.meshes.new(f"high_{name}")
    mesh.from_pydata(pos.tolist(), [], quads.tolist())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    colour = mesh.color_attributes.new("masks", "FLOAT_COLOR", "POINT")
    mask = np.stack((groove.ravel(), np.zeros(groove.size), np.zeros(groove.size), np.ones(groove.size)), -1).astype(np.float32)
    colour.data.foreach_set("color", mask.ravel())
    ob = bpy.data.objects.new(f"high_{name}", mesh)
    bpy.context.scene.collection.objects.link(ob)
    print(name, "high quads", len(quads), flush=True)
    return ob


def low_mesh(meshes, name):
    positions, normals, uvs, faces = [], [], [], []
    base = 0
    for pos, nor, uv, quads in meshes:
        if not wound_outward(pos, nor, quads):
            quads = quads[:, ::-1]
        positions.append(pos)
        normals.append(nor)
        uvs.append(uv)
        faces.append(quads + base)
        base += len(pos)
    positions, normals, uvs, faces = np.vstack(positions), np.vstack(normals), np.vstack(uvs), np.vstack(faces)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(positions.tolist(), [], faces.tolist())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    layer = mesh.uv_layers.new(name="UVMap")
    corner = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get("vertex_index", corner)
    layer.data.foreach_set("uv", uvs[corner].astype(np.float32).ravel())
    mesh.normals_split_custom_set_from_vertices(normals.tolist())
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name, offset, depth, _ in TYRES:
        sculpt(name, offset, depth)
    meshes = [grid(*LODS[0], name, offset, row) for name, offset, _, row in TYRES]
    low_mesh(meshes, "ty_lod0")
    _, _, _, _, at, liner, total = resample(2000)
    _, weighted = uv_v(at, liner, total, (0.0, 1.0))
    row_height = (TYRES[0][3][1] - TYRES[0][3][0]) * RES
    with open(os.path.join(WORK, "tyre.json"), "w") as h:
        json.dump(dict(range=RANGE, res=RES, px_per_in_v=row_height / weighted, offsets={n: o for n, o, _, _ in TYRES}, rows={n: r for n, _, _, r in TYRES}), h)
    print("px/in across the section", row_height / weighted, "and round the tread", RES / (2 * math.pi * 12.8), flush=True)
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
    dev = bpy.data.objects["ty_lod0"]
    highs = [bpy.data.objects[f"high_{t[0]}"] for t in TYRES]
    for ob in scene.objects:
        ob.hide_render = ob is not dev and ob not in highs
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 6.0
    with open(os.path.join(WORK, "baked_uv_hash.txt"), "w") as h:
        h.write(uv_hash(dev))
    mat = bpy.data.materials.new("masks")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    a = nt.nodes.new("ShaderNodeVertexColor")
    a.layer_name = "masks"
    nt.links.new(a.outputs[0], e.inputs[0])
    nt.links.new(e.outputs[0], o.inputs[0])
    for high in highs:
        high.data.materials.clear()
        high.data.materials.append(mat)

    def target(size, out, setup=None):
        img = bpy.data.images.new(out, size, size, alpha=True, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        m = bpy.data.materials.new(out)
        m.use_nodes = True
        tree = m.node_tree
        if setup:
            tree.nodes.clear()
            out_node = tree.nodes.new("ShaderNodeOutputMaterial")
            emit = tree.nodes.new("ShaderNodeEmission")
            tree.links.new(emit.outputs[0], out_node.inputs[0])
            setup(tree, emit)
        tex = tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tree.nodes.active = tex
        tex.select = True
        dev.data.materials.clear()
        dev.data.materials.append(m)
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
        def setup(tree, emit):
            geo = tree.nodes.new("ShaderNodeNewGeometry")
            mapped = tree.nodes.new("ShaderNodeVectorMath")
            mapped.operation = "MULTIPLY_ADD"
            scale = 1 / RANGE if kind == "pos" else 0.5
            mapped.inputs[1].default_value = (scale, scale, scale)
            mapped.inputs[2].default_value = (0.5, 0.5, 0.5)
            tree.links.new(geo.outputs["Position" if kind == "pos" else "Normal"], mapped.inputs[0])
            tree.links.new(mapped.outputs[0], emit.inputs[0])

        return setup

    for kind in ("pos", "nor"):
        img = target(RES, f"bake_ty_{kind}", geometry(kind))
        select_for(False)
        scene.cycles.samples = 1
        bpy.ops.object.bake(type="EMIT", margin=0, use_clear=True, target="IMAGE_TEXTURES")
        finish(img, RES, f"bake_ty_{kind}")
    img = target(RES, "bake_ty_tangent")
    select_for(True)
    scene.cycles.samples = 4
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_selected_to_active=True, cage_extrusion=0.45, max_ray_distance=0.9, margin=0, use_clear=True, target="IMAGE_TEXTURES")
    finish(img, RES, "bake_ty_tangent")
    img = target(RES, "bake_ty_masks")
    select_for(True)
    bpy.ops.object.bake(type="EMIT", use_selected_to_active=True, cage_extrusion=0.45, max_ray_distance=0.9, margin=0, use_clear=True, target="IMAGE_TEXTURES")
    finish(img, RES, "bake_ty_masks")
    img = target(1024, "bake_ty_ao")
    select_for(True)
    scene.cycles.samples = 32
    bpy.ops.object.bake(type="AO", use_selected_to_active=True, cage_extrusion=0.45, max_ray_distance=0.9, margin=0, use_clear=True, target="IMAGE_TEXTURES")
    finish(img, 1024, "bake_ty_ao")


def write_obj(path, pos, nor, uv, quads):
    if not wound_outward(pos, nor, quads):
        quads = quads[:, ::-1]
    tris = np.vstack((quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]))
    with open(path, "w", newline="\n") as h:
        h.write("# Generated by Sources/Railhead/tyre-v2/tyre.py\nmtllib tyre.mtl\n")
        h.writelines(f"v {y:.5f} {z:.5f} {x:.5f}\n" for x, y, z in pos)
        h.writelines(f"vt {u:.6f} {v:.6f}\n" for u, v in uv)
        h.writelines(f"vn {y:.5f} {z:.5f} {x:.5f}\n" for x, y, z in nor)
        h.write("usemtl ty_tyre\n")
        h.writelines("f " + " ".join(f"{i + 1}/{i + 1}/{i + 1}" for i in t) + "\n" for t in tris)
    return len(tris)


def export_stage():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    if uv_hash(bpy.data.objects["ty_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    for name, offset, _, row in TYRES:
        counts = {}
        for lod, (sides, count) in enumerate(LODS):
            pos, nor, uv, quads = grid(sides, count, name, 0.0, row)
            counts[lod] = write_obj(os.path.join(OUT, f"tyre_{name}_lod{lod}.obj"), pos, nor, uv, quads)
        print("exported", name, counts, flush=True)
        meshes = ",\n".join(
            f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/tyre_{name}_lod{l}.obj" '
            'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
            'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
            "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
        )
        groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 90.0, 220.0)))
        doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Railhead/tyre-v2/tyre.py
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
							{{ from = "ty_tyre.vmat" to = "{MODEL}/ty_tyre.vmat" }}
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
        with open(os.path.join(OUT, f"tyre_{name}.vmdl"), "w", newline="\n") as h:
            h.write(doc)
    with open(os.path.join(OUT, "tyre.mtl"), "w", newline="\n") as h:
        h.write("newmtl ty_tyre\nKd 1 1 1\nd 1\n")
    vmat = f"""// Generated by Sources/Railhead/tyre-v2/tyre.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_SPECULAR 1
	g_flMetalness "0.000"

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MODEL}/ty_tyre_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/ty_tyre_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Normal ----
	TextureNormal "{MODEL}/ty_tyre_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/ty_tyre_rough.png"
}}
"""
    with open(os.path.join(OUT, "ty_tyre.vmat"), "w", newline="\n") as h:
        h.write(vmat)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("tyre stages done", flush=True)
