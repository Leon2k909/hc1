"""Burn drum v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python drum.py -- <work dir> <project root> <build|bake|export> ...

Riverside's old drum (Tools/riverside_parts.py, drum) is a 14-sided flat-colour cylinder with a flat card for embers and six
floating quads for air holes. This is a real 55 gallon drum made into a burn barrel: a sheet-steel shell with wall thickness,
rolled chimes and rolling hoops, knocked about, its lid chiselled out leaving a jagged ring, six air holes cut right through,
and a bed of embers with charred logs in it. One mesh with four materials: blue, red and rust burning, and rust gone cold.

Same size as the old one (22.5 across, 34.5 tall), and its bed is at the same height, under where MapFire's flames sit. Inches,
engine axes, origin on the ground at the drum's axis. There are 14 on the map, so LOD 0 is under 4,000 triangles.
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as kit  # noqa: E402
from drum_pack import pack_weighted  # noqa: E402

from build import Part, add, lathe, spline, tube  # noqa: E402

SHELL, LID, BED, CHAR, COAL = range(5)
NAME = "burn_drum"
MODEL = "models/zombies/burn_drum_v2"
MATS = "materials/zombies/burn_drum_v2"
BLEND = os.path.join(WORK, "drum_build.blend")
VARIANTS = ("blue", "red", "rust", "cold")

SIDES = 32
H, R = 34.5, 11.25
IN = R - 0.15
FLOOR_Z = 0.7
BED_Z = H * 0.75
LOW, HIGH = (4.0, 5.6), (7.0, 8.6)
HOLES = ((1, LOW), (6, HIGH), (11, LOW), (17, HIGH), (22, LOW), (27, HIGH))
# Angle, height, depth, half-width round the drum and half-height: knocks taken over the years.
DENTS = ((-40.0, 17.0, 0.75, 3.8, 4.2), (150.0, 28.0, 0.8, 4.5, 3.4), (70.0, 8.0, 0.55, 3.2, 3.0), (-125.0, 30.2, 0.55, 3.2, 2.3), (-15.0, 3.0, 0.35, 2.4, 2.0))
SEAM_DEG = 170.0

PROFILE = [
    (10.7, 0.0),
    (11.42, 0.0),
    (11.52, 0.22),
    (11.46, 0.62),
    (R, 0.86),
    (R, LOW[0]),
    (R, LOW[1]),
    (R, HIGH[0]),
    (R, HIGH[1]),
    (R, 10.45),
    (R + 0.2, 10.85),
    (R + 0.37, 11.39),
    (R + 0.2, 11.93),
    (R, 12.33),
    (R, 16.0),
    (R, 19.5),
    (R, 21.85),
    (R + 0.2, 22.25),
    (R + 0.37, 22.77),
    (R + 0.2, 23.29),
    (R, 23.69),
    (R, 27.0),
    (R, 30.2),
    (R, 33.35),
    (11.42, 33.6),
    (11.52, 34.0),
    (11.44, 34.38),
    (11.2, 34.5),
    (IN, 34.42),
    # The inner wall needs a row wherever a dent is deepest, or the outer wall dents through it.
    (IN, 33.4),
    (IN, 30.2),
    (IN, 27.0),
    (IN, 19.5),
    (IN, 16.0),
    (IN, 10.4),
    (IN, HIGH[1]),
    (IN, HIGH[0]),
    (IN, LOW[1]),
    (IN, LOW[0]),
    (IN, FLOOR_Z),
]


def angle_of(k):
    return 2 * math.pi * k / SIDES


def dent_at(theta, z):
    total = 0.0
    for deg, zc, depth, wide, tall in DENTS:
        d = math.atan2(math.sin(theta - math.radians(deg)), math.cos(theta - math.radians(deg))) * R
        total += depth * math.exp(-((d / wide) ** 2) - ((z - zc) / tall) ** 2)
    return total


def shell():
    part = add(Part(SHELL, 3, name="drum shell"))
    bm = part.bm
    rows = [[bm.verts.new((r * math.cos(angle_of(k)), r * math.sin(angle_of(k)), z)) for k in range(SIDES)] for r, z in PROFILE]
    under = bm.verts.new((0, 0, 0))
    floor = bm.verts.new((0, 0, FLOOR_Z))

    # A hole is a cell of the outer wall and the same cell of the inner one, joined by four faces.
    skip = set()
    tunnels = []
    for k, (z0, z1) in HOLES:
        i = next(n for n, (r, z) in enumerate(PROFILE) if r == R and z == z0)
        j = next(n for n, (r, z) in enumerate(PROFILE) if r == IN and z == z1)
        skip.add((i, k))
        skip.add((j, k))
        tunnels.append((i, j, k))
    for i in range(len(rows) - 1):
        for k in range(SIDES):
            if (i, k) not in skip:
                n = (k + 1) % SIDES
                bm.faces.new((rows[i][k], rows[i][n], rows[i + 1][n], rows[i + 1][k]))
    for k in range(SIDES):
        n = (k + 1) % SIDES
        bm.faces.new((under, rows[0][n], rows[0][k]))
        bm.faces.new((rows[-1][k], rows[-1][n], floor))
    for i, j, k in tunnels:
        n = (k + 1) % SIDES
        A, B, C, D = rows[i][k], rows[i][n], rows[i + 1][n], rows[i + 1][k]
        d, c, b, a = rows[j][k], rows[j][n], rows[j + 1][n], rows[j + 1][k]
        bm.faces.new((A, B, b, a))
        bm.faces.new((D, d, c, C))
        bm.faces.new((A, a, d, D))
        bm.faces.new((B, C, c, b))
        # Cut by hand with a chisel, so no two corners are square.
        for outer, inner in ((A, a), (B, b), (C, c), (D, d)):
            dt, dz = float(kit.rng.uniform(-0.016, 0.016)), float(kit.rng.uniform(-0.17, 0.17))
            for vert in (outer, inner):
                radius, theta = math.hypot(vert.co.x, vert.co.y), math.atan2(vert.co.y, vert.co.x) + dt
                vert.co = (radius * math.cos(theta), radius * math.sin(theta), vert.co.z + dz)

    # Dents move both walls together, and the top wanders where it was knocked.
    for row, (_, z) in zip(rows, PROFILE):
        for vert in row:
            radius, theta = math.hypot(vert.co.x, vert.co.y), math.atan2(vert.co.y, vert.co.x)
            radius -= dent_at(theta, z)
            sink = (0.07 * (1 + math.sin(3 * theta + 1.0)) + 0.03 * (1 + math.sin(7 * theta))) if z > 33 else 0.0
            vert.co = (radius * math.cos(theta) * 1.005, radius * math.sin(theta) * 0.995, vert.co.z - sink)


def lid_remnant():
    """What the chisel left of the lid: a thin ring, torn to a different width all the way round."""
    part = add(Part(LID, 1, name="lid remnant"))
    bm = part.bm
    z0, z1 = 33.68, 33.75
    rings = [[], [], [], []]
    for k in range(SIDES):
        theta = angle_of(k)
        ro = IN - dent_at(theta, 33.7) + 0.02
        ri = ro - float(kit.rng.uniform(0.3, 1.25)) - (0.45 if k % 2 else 0.0)
        for ring, (radius, z) in zip(rings, ((ro, z0), (ro, z1), (ri, z1), (ri, z0))):
            ring.append(bm.verts.new((radius * math.cos(theta), radius * math.sin(theta), z)))
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(SIDES):
            n = (k + 1) % SIDES
            bm.faces.new((a[k], a[n], b[n], b[k]))


def bed_height(radius, theta):
    return BED_Z + 1.3 * (1 - (radius / 11.0) ** 2) + 0.42 * math.sin(2 * theta + 0.7) * radius / 11.0 + 0.3 * math.sin(5 * theta + radius * 0.8) * min(radius / 4.0, 1.0)


def fire():
    """The ember bed, with coals and charred logs lying in it. All of it below the rim."""
    part = add(Part(BED, 3, name="ember bed"))
    bm = part.bm
    sectors = 20
    centre = bm.verts.new((0, 0, bed_height(0, 0)))
    rings = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        ring = []
        for k in range(sectors):
            theta = 2 * math.pi * k / sectors
            radius = min(10.95, IN - dent_at(theta, BED_Z) - 0.06) * frac
            ring.append(bm.verts.new((radius * math.cos(theta), radius * math.sin(theta), bed_height(radius, theta))))
        rings.append(ring)
    low = [bm.verts.new((v.co.x, v.co.y, BED_Z - 0.9)) for v in rings[-1]]
    for k in range(sectors):
        n = (k + 1) % sectors
        bm.faces.new((centre, rings[0][k], rings[0][n]))
        for a, b in zip(rings, rings[1:]):
            bm.faces.new((a[k], b[k], b[n], a[n]))
        bm.faces.new((low[k], low[n], rings[-1][n], rings[-1][k]))
    bm.faces.new(list(reversed(low)))

    for _ in range(9):
        radius, theta = float(kit.rng.uniform(1.5, 8.8)), float(kit.rng.uniform(0, 2 * math.pi))
        s = float(kit.rng.uniform(0.75, 1.5))
        at = Vector((radius * math.cos(theta), radius * math.sin(theta), bed_height(radius, theta) + 0.2))
        m = Matrix.Translation(at) @ Matrix.Rotation(float(kit.rng.uniform(0, 6.28)), 4, "Z") @ Matrix.Diagonal((s * float(kit.rng.uniform(0.8, 1.3)), s, s * 0.8, 1))
        lathe(add(Part(COAL, 1, name="coal")), [(0.0, -0.7), (0.85, -0.3), (0.95, 0.2), (0.5, 0.62), (0.0, 0.75)], 6, m)

    logs = (
        ((-6.0, -5.2, 25.4), (-1.5, -0.8, 29.4), (2.8, 3.6, 32.6), 1.75),
        ((6.4, -3.2, 25.6), (1.6, -0.4, 28.6), (-3.2, 2.2, 31.2), 1.5),
        ((-1.8, 7.2, 25.8), (-0.4, 1.4, 27.8), (0.9, -5.2, 30.2), 1.35),
        ((3.8, 6.4, 26.2), (5.8, 3.4, 27.2), (7.8, 0.2, 28.6), 1.15),
    )
    for a, b, c, radius in logs:
        path = spline([a, b, c], 2)
        radii = [radius * float(kit.rng.uniform(0.86, 1.1)) for _ in path]
        radii[-1] *= 0.72
        tube(add(Part(CHAR, 2, name="log")), path, radii, 8, flatten=0.88)


def weight_of(face, facts):
    """How much texture a face gets, as a multiple of the real size: the outside first, then what you see from above."""
    finish = int(round(face.loops[0][facts][0] * 16))
    n = face.normal
    c = face.calc_center_median()
    if finish == SHELL:
        r = max(math.hypot(c.x, c.y), 1e-3)
        if c.z < 0.75 and abs(n.z) > 0.7:
            return 0.06
        if (n.x * c.x + n.y * c.y) / r < -0.3:
            return 0.55 if c.z > 25 else 0.16
        return 1.0
    return {LID: 0.6, BED: 0.9, CHAR: 1.0, COAL: 0.8}[finish]


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    shell()
    lid_remnant()
    fire()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "drum_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    density = pack_weighted(hw.data, weight_of)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), flush=True)

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

    lod("drum_lod1", 1, 0.45)
    # Any harder and the air holes' tunnels smear into dark streaks up the side.
    lod("drum_lod2", 3, 0.34)
    holes = [(angle_of(k + 0.5), (z0 + z1) / 2) for k, (z0, z1) in HOLES]
    with open(os.path.join(WORK, "drum.json"), "w") as h:
        json.dump(dict(density=density, height=H, radius=R, inner=IN, bed=BED_Z, holes=holes, seam=math.radians(SEAM_DEG)), h)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("saved build", flush=True)


def relod_stage(ratio):
    """Make LOD 2 again from the saved LOD 0 at another ratio. It leaves the UVs alone, so the bakes stay good."""
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    hw = bpy.data.objects["drum_lod0"]
    bpy.data.objects.remove(bpy.data.objects["drum_lod2"])
    copy = hw.copy()
    copy.data = hw.data.copy()
    copy.name = copy.data.name = "drum_lod2"
    bpy.context.scene.collection.objects.link(copy)
    bm = bmesh.new()
    bm.from_mesh(copy.data)
    facts = bm.loops.layers.float_color["facts"]
    drop = [f for f in bm.faces if int(round(f.loops[0][facts][0] * 16)) not in (SHELL, BED)]
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
    copy.data.calc_loop_triangles()
    print("drum_lod2 tris", len(copy.data.loop_triangles), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


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
    hw = bpy.data.objects["drum_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
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

    bake_one(2048, "EMIT", source("pos"), 1, "bake_drum_pos")
    bake_one(2048, "EMIT", source("nor"), 1, "bake_drum_nor")
    bake_one(2048, "EMIT", source("facts"), 1, "bake_drum_facts")
    bake_one(1024, "AO", None, 32, "bake_drum_ao")


def vmat_text(variant):
    state = "rust" if variant in ("rust", "cold") else "painted"
    glow = ""
    if variant != "cold":
        glow = f"""
	//---- Self Illum ----
	F_SELF_ILLUM 1
	TextureSelfIllumMask "{MATS}/{NAME}_glow.png"
	g_flSelfIllumBrightness "4.500"
	g_flSelfIllumAlbedoFactor "1.000"
	g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"
"""
    return f"""// Generated by Sources/Zombies/burn-drum-v2/drum.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1
{glow}
	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/{NAME}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/{NAME}_{variant}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/{NAME}_{state}_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/{NAME}_{state}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/{NAME}_{state}_rough.png"
}}
"""


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["drum_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"drum_lod{lod}"]
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
            h.write(f"# Generated by Sources/Zombies/burn-drum-v2/drum.py\nmtllib {NAME}.mtl\n")
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
    for variant in VARIANTS:
        doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Zombies/burn-drum-v2/drum.py
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
							{{ from = "{NAME}.vmat" to = "{MATS}/{NAME}_{variant}.vmat" }}
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
        with open(os.path.join(out, f"{NAME}_{variant}.vmdl"), "w", newline="\n") as h:
            h.write(doc)
        with open(os.path.join(mats, f"{NAME}_{variant}.vmat"), "w", newline="\n") as h:
            h.write(vmat_text(variant))
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "relod" in STAGES:
    relod_stage(0.34)
if "export" in STAGES:
    export_stage()
print("drum stages done", flush=True)
