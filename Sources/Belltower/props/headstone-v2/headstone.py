"""Belltower's churchyard stones v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python headstone.py -- <work dir> <project root> <build|bake|export> ...

The old stones are one box each, or two bars for a cross, with a wall texture stretched over them. These are four cut stones sharing one atlas: an arched
headstone on a footing, a shouldered one, a low one with its corner gone, and a ringed cross on a stepped base. Their edges are worn and nicked, their faces
carved, and each keeps the old collision box for its kind. Inches, engine axes: +X out of the inscribed face, Y across, Z up, origin on the ground at the middle.
They're built side by side, each in its own slot along Y, so one bake and one atlas serve all four. Exported outside Assets until the user approves.
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
WORK_ROOT, ROOT = argv[0], argv[1]
STAGES = argv[2:]
WORK = WORK_ROOT
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, box, prism  # noqa: E402

STONE, FOOTING = range(2)
NAME = "headstone"
MODEL = "models/props/belltower/headstone_v2"
MATS = "materials/belltower/headstone_v2"
EXPORT = os.path.join(WORK_ROOT, "headstone_v2")  # Laid out like Assets, ready to copy in.
BLEND = os.path.join(WORK, "headstone_build.blend")
ATLAS = 4096
SLOT = 45.0
STONES = ("arched", "shouldered", "low", "cross")
HEIGHTS = dict(arched=32.0, shouldered=29.0, low=26.0, cross=40.0)
rng = np.random.default_rng(1743)


# Local x along Y, local y along Z, extruded along X: a stone's outline drawn as you'd face it.
FACE = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def slab(outline, thick, y, lod=3, bevel=0.3, name="stone", nick=0.1, sink=2.0):
    """A cut stone from its outline, its edges a little out of true, sunk into the ground, with no underside."""
    rough = []
    for a, b in outline:
        if b > 0.5:
            a += float(rng.uniform(-nick, nick))
            b += float(rng.uniform(-nick, nick)) * 0.7
        rough.append((a + y, b if b > 0.5 else -sink))
    p = add(Part(STONE, lod, bevel=bevel, angle=25, name=name))
    prism(p, rough, -thick / 2, thick / 2, FACE)
    p.bm.normal_update()
    bmesh.ops.delete(p.bm, geom=[f for f in p.bm.faces if f.normal.z < -0.9], context="FACES")
    return p


def arc(cy, cz, r, a0, a1, n):
    return [(cy + r * math.cos(t), cz + r * math.sin(t)) for t in np.linspace(a0, a1, n)]


def footing(y, half_x, half_y, height, lod=3):
    p = add(Part(FOOTING, lod, bevel=0.42, angle=25, name="footing"))
    box(p, (-half_x, y - half_y, -2.0), (half_x, y + half_y, height))
    p.bm.normal_update()
    bmesh.ops.delete(p.bm, geom=[f for f in p.bm.faces if f.normal.z < -0.9], context="FACES")
    for v in p.bm.verts:
        if v.co.z > 0:
            v.co.x += float(rng.uniform(-0.12, 0.12))
            v.co.y += float(rng.uniform(-0.12, 0.12))
            v.co.z += float(rng.uniform(-0.1, 0.1))


def arched(y):
    h, half = HEIGHTS["arched"], 11.0
    spring = h - half
    outline = [(-half, 0.0), (half, 0.0)] + arc(0.0, spring, half, 0.0, math.pi, 25)
    footing(y, 3.9, 12.2, 2.7)
    slab(outline, 5.2, y, nick=0.07)


def shouldered(y):
    h, half = HEIGHTS["shouldered"], 11.0
    # Rounded shoulders, stepping in to a low round head.
    head = arc(0.0, h - 7.6, 7.6, 0.25, math.pi - 0.25, 15)
    right = [(half, 0.0), (half, h - 9.0), (half - 0.35, h - 8.1), (half - 1.3, h - 7.55), (half - 2.5, h - 7.4), (half - 3.3, h - 6.9)]
    left = [(-a, b) for a, b in reversed(right)]
    slab(right + head + left, 4.6, y, nick=0.06)


def low(y):
    h, half = HEIGHTS["low"], 10.6
    # A shallow curved head, with one top corner long since broken away.
    head = [(half * math.cos(t), h - 2.6 + 2.6 * math.sin(t) * 1.0) for t in np.linspace(0.32, math.pi - 0.05, 15)]
    broken = [(half, 0.0), (half + 0.1, h - 8.5), (half - 0.7, h - 6.9), (half - 0.5, h - 5.4), (half - 2.0, h - 4.3), (half - 2.5, h - 2.9), (half - 3.6, h - 2.1)]
    head = [p for p in head if p[0] < half - 4.0]
    p = slab([(-half, 0.0)] + broken + head + [(-half, h - 3.2)], 5.6, y, nick=0.12, bevel=0.38)
    return p


def cross(y):
    h = HEIGHTS["cross"]
    footing(y, 5.6, 7.2, 2.8)
    footing(y, 4.1, 5.2, 5.2)
    p = add(Part(STONE, 3, bevel=0.42, angle=25, name="shaft"))
    box(p, (-2.7, y - 2.7, 5.0), (2.7, y + 2.7, h))
    p = add(Part(STONE, 3, bevel=0.42, angle=25, name="arms"))
    box(p, (-2.45, y - 12.0, 26.0), (2.45, y + 12.0, 32.0))
    # The ring round the crossing: a flat stone band, square in section, thinner than the arms so it reads behind them.
    p = add(Part(STONE, 2, bevel=0.2, angle=25, name="ring"))
    rings = []
    for k in range(28):
        a = k * math.tau / 28
        out = 9.3 + float(rng.uniform(-0.05, 0.05))
        inner = 6.9 + float(rng.uniform(-0.05, 0.05))
        rings.append([p.bm.verts.new((x, y + r * math.cos(a), 29.0 + r * math.sin(a))) for x, r in ((1.6, out), (1.6, inner), (-1.6, inner), (-1.6, out))])
    for k in range(28):
        a, b = rings[k], rings[(k + 1) % 28]
        for j in range(4):
            p.bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))


def geometry():
    for k, name in enumerate(STONES):
        y = (k - 1.5) * SLOT
        {"arched": arched, "shouldered": shouldered, "low": low, "cross": cross}[name](y)


def skyline(rects, limit):
    """Bottom-left placement of (w, h, key) in a limit-sized square. Returns key: (x, y), or None if they don't fit."""
    line = [[0.0, 0.0, limit]]
    places = {}
    for w, h, key in rects:
        best, best_y = None, None
        for i, (x, _, _) in enumerate(line):
            if x + w > limit + 1e-6:
                break
            y, covered, j = 0.0, 0.0, i
            while covered < w:
                y = max(y, line[j][1])
                covered += line[j][2]
                j += 1
            if best_y is None or y < best_y:
                best, best_y = i, y
        if best is None or best_y + h > limit:
            return None
        x = line[best][0]
        places[key] = (x, best_y)
        rest, j = w, best
        while rest > 1e-9:
            if line[j][2] <= rest:
                rest -= line[j][2]
                del line[j]
            else:
                line[j][0] += rest
                line[j][2] -= rest
                rest = 0
        line.insert(best, [x, best_y + h, w])
        i = max(best - 1, 0)
        while i < len(line) - 1:
            if abs(line[i][1] - line[i + 1][1]) < 1e-9:
                line[i][2] += line[i + 1][2]
                del line[i + 1]
            else:
                i += 1
    return places


def pack_atlas(mesh, lookup, res, pad_px):
    """Real-scale islands, skyline packed. What's buried in other parts or faces the floor gets little of the atlas."""
    from mathutils.bvhtree import BVHTree

    facts = mesh.color_attributes["facts"].data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    layer = bm.loops.layers.uv.active
    tree = BVHTree.FromBMesh(bm)
    weight = {}
    for f in bm.faces:
        c = f.calc_center_median()
        texel = getattr(lookup[round(facts[f.loops[0].index].color[1], 4)], "texel", 1.0)
        if tree.ray_cast(c + f.normal * 0.012, f.normal, 0.5)[0] is not None:
            texel = min(texel, 0.25)
        elif f.normal.z < -0.75:
            texel = min(texel, 0.3)
        weight[f.index] = texel
    seen = set()
    islands = []
    for seed in bm.faces:
        if seed.index in seen:
            continue
        seen.add(seed.index)
        stack, faces = [seed], []
        while stack:
            f = stack.pop()
            faces.append(f)
            for l in f.loops:
                a, b = l[layer].uv, l.link_loop_next[layer].uv
                for other in l.link_loops:
                    g = other.face
                    if g.index in seen:
                        continue
                    c, d = other[layer].uv, other.link_loop_next[layer].uv
                    if ((a - d).length < 1e-5 and (b - c).length < 1e-5) or ((a - c).length < 1e-5 and (b - d).length < 1e-5):
                        seen.add(g.index)
                        stack.append(g)
        islands.append(faces)
    rects = []
    for n, faces in enumerate(islands):
        areas = [f.calc_area() for f in faces]
        area3 = sum(areas)
        tris = [[tuple(l[layer].uv) for l in f.loops] for f in faces]
        pts = np.array([p for t in tris for p in t])
        areauv = sum(0.5 * abs(sum(t[i][0] * t[(i + 1) % len(t)][1] - t[(i + 1) % len(t)][0] * t[i][1] for i in range(len(t)))) for t in tris)
        texel = sum(a * weight[f.index] for a, f in zip(areas, faces)) / max(area3, 1e-9)
        scale = math.sqrt(area3 / max(areauv, 1e-12)) * texel
        centre = pts.mean(0)
        inches = (pts - centre) * scale
        best = None
        for deg in np.linspace(0, 90, 13):
            r = math.radians(deg)
            rot = np.array(((math.cos(r), -math.sin(r)), (math.sin(r), math.cos(r))))
            q = inches @ rot.T
            w, h = np.ptp(q, axis=0)
            if best is None or w * h < best[0]:
                best = (w * h, rot, w, h)
        _, rot, w, h = best
        if h > w:
            rot = np.array(((0.0, 1.0), (-1.0, 0.0))) @ rot
            w, h = h, w
        q = inches @ rot.T
        rects.append((w, h, n, centre, scale, rot, q.min(0)))
    order = sorted(rects, key=lambda r: (-round(r[1], 1), -r[0]))

    def attempt(px_per_in):
        pad = pad_px / px_per_in
        return skyline([(r[0] + pad, r[1] + pad, r[2]) for r in order], res / px_per_in)

    lo, hi = 2.0, 80.0
    places = None
    for _ in range(11):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            places, lo = got, mid
        else:
            hi = mid
    density = lo
    half = pad_px / density / 2
    for w, h, n, centre, scale, rot, low in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px + half) * density / res, (q[1] + py + half) * density / res)
    bm.to_mesh(mesh)
    bm.free()
    print("islands", len(rects), "density px/in %.1f" % density, flush=True)
    return density


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    count = len(kit.parts)
    order = np.random.default_rng(77).permutation(count)
    for i, p in enumerate(kit.parts):
        p.bm.normal_update()
        bmesh.ops.recalc_face_normals(p.bm, faces=p.bm.faces)
        kit.harden(p)
        p.done = p.bm
        p.rand = (float(order[i]) + 0.5) / count
    print("parts", count, flush=True)
    hw = kit.join_parts(kit.parts, "headstone_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    lookup = {round(p.rand, 4): p for p in kit.parts}
    density = pack_atlas(hw.data, lookup, ATLAS, 3)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), flush=True)

    def lod(name, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = name
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
        print(name, "tris", len(copy.data.loop_triangles), flush=True)

    lod("headstone_lod1", 1, 0.5)
    lod("headstone_lod2", 2, 0.28)
    lod("headstone_lod3", 3, 0.14)
    with open(os.path.join(WORK, "headstone.json"), "w") as h:
        json.dump(dict(density=density, slot=SLOT, stones=STONES), h)
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
    hw = bpy.data.objects["headstone_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 10.0
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

    bake_one(ATLAS, "EMIT", source("pos"), 1, "bake_headstone_pos")
    bake_one(ATLAS, "EMIT", source("nor"), 1, "bake_headstone_nor")
    bake_one(ATLAS, "EMIT", source("facts"), 1, "bake_headstone_facts")
    bake_one(ATLAS, "AO", None, 24, "bake_headstone_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(EXPORT, MODEL)
    mats = os.path.join(EXPORT, MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["headstone_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {name: {} for name in STONES}
    for lod in range(4):
        ob = bpy.data.objects[f"headstone_lod{lod}"]
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
        p0 = co.reshape(-1, 3)[verts[loops]][:, [1, 2, 0]]
        t = uv.reshape(-1, 2)[loops]
        n = nn.reshape(-1, 3)[loops][:, [1, 2, 0]]
        e.to_mesh_clear()
        # Each triangle belongs to the stone whose slot its middle falls in. OBJ's first axis is engine Y.
        slots = np.rint(p0[::3, 0] * 0 + (p0[0::3, 0] + p0[1::3, 0] + p0[2::3, 0]) / 3 / SLOT + 1.5).astype(int)
        for index, name in enumerate(STONES):
            offset = np.array(((index - 1.5) * SLOT, 0.0, 0.0))
            tables = ({}, {}, {})
            lines = ([], [], [])
            faces = []
            picked = np.nonzero(slots == index)[0]
            for k in picked:
                tri = []
                for c in range(3):
                    i = k * 3 + c
                    idx = []
                    for table, store, prefix, vec in zip(tables, lines, ("v ", "vt ", "vn "), (p0[i] - offset, t[i], n[i])):
                        key = tuple(np.round(vec, 5))
                        got = table.get(key)
                        if got is None:
                            got = len(table) + 1
                            table[key] = got
                            store.append(prefix + " ".join(f"{x:.5f}" for x in key) + "\n")
                        idx.append(got)
                    tri.append("%d/%d/%d" % tuple(idx))
                faces.append("f " + " ".join(tri) + "\n")
            with open(os.path.join(out, f"{NAME}_{name}_lod{lod}.obj"), "w", newline="\n") as h:
                h.write(f"# Generated by Sources/Belltower/props/headstone-v2/headstone.py\nmtllib {NAME}.mtl\n")
                for block in lines:
                    h.writelines(block)
                h.write(f"usemtl {NAME}\n")
                h.writelines(faces)
            counts[name][lod] = len(picked)
        print("lod", lod, {name: counts[name][lod] for name in STONES}, flush=True)
    with open(os.path.join(out, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")
    for name in STONES:
        tall = HEIGHTS[name]
        # The old collision for this kind: a slab's box, or a cross's shaft alone, as its arms never had any.
        size = (6.0, 6.0, 40.0) if name == "cross" else (6.0, 22.0, tall)
        meshes = ",\n".join(
            f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/{NAME}_{name}_lod{l}.obj" '
            'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
            'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
            "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in range(4)
        )
        groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(range(4), (0.0, 30.0, 70.0, 150.0)))
        doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Belltower/props/headstone-v2/headstone.py
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
			{{
				_class = "PhysicsShapeList"
				children =
				[
					{{
						_class = "PhysicsShapeBox"
						parent_bone = ""
						surface_prop = "default"
						collision_tags = "solid"
						origin = [ 0.0000, 0.0000, {size[2] / 2:.4f} ]
						angles = [ 0.0000, 0.0000, 0.0000 ]
						dimensions = [ {size[0]:.4f}, {size[1]:.4f}, {size[2]:.4f} ]
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
        with open(os.path.join(out, f"{NAME}_{name}.vmdl"), "w", newline="\n") as h:
            h.write(doc)
    vmat = f"""// Generated by Sources/Belltower/props/headstone-v2/headstone.py

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
print("headstone stages done", flush=True)
