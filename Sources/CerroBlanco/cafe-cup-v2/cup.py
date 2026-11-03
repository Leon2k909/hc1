"""Cerro Blanco's cafe cup and saucer v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python cup.py -- <work dir> <project root> <build|bake|export> ...

A porcelain cappuccino cup on its saucer, in place of a grey 12-sided disc with an open cone on it: a saucer with an unglazed foot ring, a well and a rolled rim; a cup with a foot, a thick base, a
rounded lip and a strap handle. Two models come out of the one build: "cup", full, its milk foam drawn into a heart on the crema; and "cup_empty", drunk, with a teaspoon on the saucer. No maker's names.

Inches. Z is up and the origin is under the saucer's middle, on the table. The handle is on +X.
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

from build import Part, add, tube  # noqa: E402

PORCELAIN, POWDER, CAST, STEEL, COFFEE = 0, 1, 2, 4, 5  # POWDER and CAST aren't used: the shared stages look for them.
FOLDER = "models/maps/cerroblanco/cafe_cup_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "cafe_cup_v2")
BLEND = os.path.join(WORK, "cup_build.blend")
NAME = "cup"
W, H = 1024, 1024
POS_RANGE = 16.0  # The position bake spans this many inches, centred on the origin.

WELL_Z = 0.13  # The saucer's well, where the cup's foot stands.
CUP_Z = WELL_Z
COFFEE_Z = 2.04  # The coffee's surface, above the cup's foot.
VARIANTS = (("cup", ("spoon",)), ("cup_empty", ("coffee",)))  # Each model, and the parts it goes without.
SPOON_ANGLE = -62.0
rng = np.random.default_rng(2641)
edge_lines = []
NO_EDGE = ("saucer", "cup", "handle", "coffee", "spoon")


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


SAUCER = [(0, 0.06), (1.55, 0.06), (1.6, 0.0), (1.8, 0.0), (1.86, 0.06), (2.1, 0.13), (2.4, 0.23), (2.62, 0.34), (2.76, 0.45), (2.83, 0.52), (2.82, 0.57), (2.76, 0.59), (2.68, 0.56),
          (2.45, 0.42), (2.1, 0.3), (1.7, 0.22), (1.42, 0.19), (1.36, 0.16), (1.32, WELL_Z), (0, WELL_Z)]
# The cup's section, out round its foot, up the outside, over the lip and down the inside to the middle of its floor.
CUP = [(0, 0.06), (0.82, 0.06), (0.88, 0.0), (0.98, 0.0), (1.03, 0.07), (1.14, 0.22), (1.28, 0.45), (1.42, 0.75), (1.54, 1.1), (1.64, 1.55), (1.7, 2.0), (1.725, 2.35), (1.73, 2.47),
       (1.71, 2.53), (1.665, 2.555), (1.62, 2.53), (1.6, 2.45), (1.595, 2.3), (1.57, 1.95), (1.5, 1.5), (1.38, 1.05), (1.2, 0.66), (0.95, 0.4), (0.6, 0.3), (0.25, 0.27), (0, 0.27)]


def inner_r(z):
    """The cup's inside radius at height z above its foot."""
    inside = CUP[CUP.index((1.62, 2.53)) :]
    for (ra, za), (rb, zb) in zip(inside, inside[1:]):
        if zb <= z <= za:
            return ra + (rb - ra) * (z - za) / (zb - za)
    return inside[-1][0]


def strip(part, path, widths, thick, sides=8):
    """A flat section swept along points: widths across (one a point), thick through, its faces up and down."""
    bm = part.bm
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(t).normalized()
        w = widths[i] / 2
        rings.append([bm.verts.new(p + side * w * math.cos(2 * math.pi * k / sides) + up * thick[i] / 2 * math.sin(2 * math.pi * k / sides)) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def saucer():
    kit.lathe(piece(PORCELAIN, 3, name="saucer"), SAUCER, 48)


def cup():
    kit.lathe(piece(PORCELAIN, 3, name="cup"), CUP, 40, kit.frame((0, 0, CUP_Z)))
    # The handle: a strap, wider than it is thick, out from the belly and back, its ends sunk into the wall.
    path = kit.spline([(1.5, 0, CUP_Z + 2.12), (1.95, 0, CUP_Z + 2.24), (2.38, 0, CUP_Z + 2.14), (2.6, 0, CUP_Z + 1.78), (2.56, 0, CUP_Z + 1.32), (2.3, 0, CUP_Z + 0.98), (1.86, 0, CUP_Z + 0.8), (1.3, 0, CUP_Z + 0.72)], 5)
    n = len(path)
    # The tube's width runs across the loop's plane (y), its thickness, flattened, in it: a strap, slimmer at its middle.
    tube(piece(PORCELAIN, 3, name="handle"), path, [0.22 - 0.05 * math.sin(math.pi * k / (n - 1)) for k in range(n)], 10, flatten=0.6)


def coffee():
    """A cappuccino's top: a thin disc of foam sitting in the cup, domed a touch, wetting the wall a little above itself."""
    z = CUP_Z + COFFEE_Z
    r = inner_r(COFFEE_Z) + 0.01
    kit.lathe(piece(COFFEE, 2, name="coffee"), [(0, z - 0.2), (r, z - 0.2), (r, z - 0.01), (r * 0.94, z + 0.012), (r * 0.6, z + 0.03), (0, z + 0.036)], 40)


def spoon():
    """A teaspoon on the saucer, its bowl in the well by the cup's foot and its handle out over the rim."""
    a = math.radians(SPOON_ANGLE)
    out = Vector((math.cos(a), math.sin(a), 0))
    def at(r, z):
        return out * r + Vector((0, 0, z))
    # Along the spoon from the bowl's tip: radius from the middle, height, width, thickness.
    stations = [(1.0, 0.2, 0.12, 0.05), (1.12, 0.2, 0.52, 0.07), (1.35, 0.21, 0.74, 0.08), (1.6, 0.22, 0.72, 0.08), (1.85, 0.25, 0.46, 0.07), (2.05, 0.31, 0.14, 0.06), (2.4, 0.46, 0.12, 0.06),
                (2.78, 0.62, 0.13, 0.06), (3.3, 0.68, 0.18, 0.06), (3.85, 0.73, 0.26, 0.06), (4.25, 0.76, 0.28, 0.06), (4.42, 0.77, 0.14, 0.05)]
    strip(piece(STEEL, 1, name="spoon"), [at(r, z) for r, z, _, _ in stations], [w for _, _, w, _ in stations], [t for _, _, _, t in stations], 12)


def geometry():
    saucer()
    cup()
    coffee()
    spoon()


def harden_all():
    seen = set()
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in (POWDER, CAST) and p.name not in NO_EDGE:
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(24):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.08))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        while True:
            p.rand = float(kit.rng.uniform(0, 1))
            if round(p.rand, 4) not in seen:
                seen.add(round(p.rand, 4))
                break


def share(finish, normal, centre):
    """How much texture an island gets, against the saucer's top at 1."""
    if finish == COFFEE:
        return 1.4 if normal.z > 0.5 else 0.1
    if finish == PORCELAIN and normal.z < -0.6 and centre.z < 0.3:
        return 0.3
    return 1.0


def pack(mesh, pad_px=4):
    """The toolkit's real-scale shelf packing, with a share of the atlas for each island, which is kept in the facts' third channel."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    layer = bm.loops.layers.uv.active
    facts = bm.loops.layers.float_color["facts"]
    bm.faces.ensure_lookup_table()
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
        area3 = sum(f.calc_area() for f in faces)
        pts = np.array([tuple(l[layer].uv) for f in faces for l in f.loops])
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
        weighted = Vector((0, 0, 0))
        middle = Vector((0, 0, 0))
        for f in faces:
            weighted += f.normal * f.calc_area()
            middle += f.calc_center_median() * f.calc_area()
        weight = share(int(round(faces[0].loops[0][facts][0] * 16)), weighted.normalized(), middle / max(area3, 1e-9))
        scale = math.sqrt(area3 / max(areauv, 1e-12)) * weight
        centre = pts.mean(0)
        inches = (pts - centre) * scale
        best = None
        for deg in np.linspace(0, 90, 19):
            r = math.radians(deg)
            rot = np.array(((math.cos(r), -math.sin(r)), (math.sin(r), math.cos(r))))
            q = inches @ rot.T
            w, h = np.ptp(q, axis=0)
            if best is None or w * h < best[0]:
                best = (w * h, rot, w, h)
        _, rot, w, h = best
        q = inches @ rot.T
        if h > w:
            rot = np.array(((0.0, 1.0), (-1.0, 0.0))) @ rot
            q = inches @ rot.T
            w, h = h, w
        rects.append((w, h, n, centre, scale, rot, q.min(0), weight))

    def attempt(px_per_in):
        pad = pad_px / px_per_in
        limit_x, limit_y = W / px_per_in, H / px_per_in
        x = y = pad
        row = 0.0
        places = {}
        for w, h, n, *_ in sorted(rects, key=lambda r: (-round(r[1], 1), -r[0])):
            if x + w + pad > limit_x:
                x = pad
                y += row + pad
                row = 0.0
            if y + h + pad > limit_y:
                return None
            places[n] = (x, y)
            x += w + pad
            row = max(row, h)
        return places

    lo, hi = 2.0, 400.0
    places = None
    for _ in range(30):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            places, lo = got, mid
        else:
            hi = mid
    first = lo
    # The shelves waste half the atlas on so many small islands, so lay them out on the shelves first, in a space as tall as the atlas, and let Blender nest them inside that box.
    for w, h, n, centre, scale, rot, low, weight in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px) * first / H, (q[1] + py) * first / H)
                l[facts][2] = weight
    # Two pinned specks at the box's corners make Blender pack into the whole of it, not the shelves' outline.
    for corner, toward in (((0.0, 0.0), (1, 1)), ((W / H, 1.0), (-1, -1))):
        tri = [bm.verts.new((9000.0 + k, 0.0, -9000.0)) for k in range(3)]
        f = bm.faces.new(tri)
        for l, (du, dv) in zip(f.loops, ((0, 0), (1, 0), (0, 1))):
            l[layer].uv = (corner[0] + toward[0] * du * 1e-5, corner[1] + toward[1] * dv * 1e-5)
            l[layer].pin_uv = True
            l[facts][0], l[facts][1], l[facts][2] = 0.0, -1.0, 1.0
    bm.to_mesh(mesh)
    bm.free()
    ob = next(o for o in bpy.data.objects if o.data is mesh)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="ORIGINAL_AABB", rotate=True, rotate_method="ANY", scale=True, merge_overlap=False, margin_method="ADD", margin=pad_px / H, pin=True, pin_method="LOCKED", shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(False)
    specks = bmesh.new()
    specks.from_mesh(mesh)
    bmesh.ops.delete(specks, geom=[v for v in specks.verts if v.co.x > 8000.0], context="VERTS")
    specks.to_mesh(mesh)
    specks.free()
    uv = np.empty(len(mesh.loops) * 2, np.float64)
    mesh.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    low_uv = uv.min(0)
    # The space is as tall as the atlas, W / H of it wide: fill it, then stretch across to the atlas.
    fit = min((W / H) / np.ptp(uv[:, 0]), 1.0 / np.ptp(uv[:, 1])) * (1 - 1e-4)
    uv = (uv - low_uv) * fit
    uv[:, 0] *= H / W
    mesh.uv_layers.active.data.foreach_set("uv", uv.reshape(-1))
    # Blender scaled the islands too, so measure the density from the result: texels per weighted square inch.
    check = bmesh.new()
    check.from_mesh(mesh)
    lay = check.loops.layers.uv.active
    fl = check.loops.layers.float_color["facts"]
    texels = weighted = 0.0
    for f in check.faces:
        c = [Vector((l[lay].uv.x * W, l[lay].uv.y * H)) for l in f.loops]
        for i in range(1, len(c) - 1):
            texels += abs((c[i] - c[0]).cross(c[i + 1] - c[0])) / 2
        weighted += f.calc_area() * f.loops[0][fl][2] ** 2
    check.free()
    density = math.sqrt(texels / weighted)
    print("islands", len(rects), "shelves px/in %.1f" % first, "nested px/in %.1f" % density, flush=True)
    return density


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "cup_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    lookup = {round(p.rand, 4): p for p in kit.parts}
    bm = bmesh.new()
    bm.from_mesh(hw.data)
    facts = bm.loops.layers.float_color["facts"]
    areas = {}
    for f in bm.faces:
        p = lookup[round(f.loops[0][facts][1], 4)]
        areas[p.name] = areas.get(p.name, 0.0) + f.calc_area()
    bm.free()
    print("areas", {k: round(v) for k, v in sorted(areas.items(), key=lambda kv: -kv[1])}, flush=True)
    density = pack(hw.data, 4)
    hw.data.calc_loop_triangles()
    print("tris", len(hw.data.loop_triangles), "px/in %.1f" % density, flush=True)

    def lod(number, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = f"cup_lod{number}"
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

    lod(1, 1, 0.6)
    lod(2, 3, 0.45)
    np.save(os.path.join(WORK, "cup_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "cup_parts.json"), "w") as h:
        json.dump([[p.rand, p.name, p.finish] for p in kit.parts], h)
    with open(os.path.join(WORK, "cup.json"), "w") as h:
        json.dump(
            dict(density=density, range=POS_RANGE, well=WELL_Z, cup_z=CUP_Z, coffee_z=COFFEE_Z, spoon_angle=SPOON_ANGLE, saucer=SAUCER, cup=CUP),
            h,
        )
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
    hw = bpy.data.objects["cup_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 3.0
    with open(os.path.join(WORK, "cup_baked_uv_hash.txt"), "w") as h:
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

    def bake_one(w, h, kind, setup, samples, out):
        img = bpy.data.images.new(out, w, h, alpha=True, float_buffer=True)
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
        data = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(data)
        np.save(os.path.join(WORK, out + ".npy"), data.reshape(h, w, 4))
        print("baked", out, flush=True)

    bake_one(W, H, "EMIT", source("pos"), 1, "bake_cu_pos")
    bake_one(W, H, "EMIT", source("nor"), 1, "bake_cu_nor")
    bake_one(W, H, "EMIT", source("facts"), 1, "bake_cu_facts")
    bake_one(W // 2, H // 2, "AO", None, 40, "bake_cu_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["cup_lod0"]) != open(os.path.join(WORK, "cup_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    for model, leave_out in VARIANTS:
        export_model(model, leave_out)
    with open(os.path.join(OUT, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")


def export_model(model, leave_out):
    """One model's LOD OBJs and vmdl, and for the full cup the material too. leave_out names parts whose faces it goes without."""
    rand_name = {round(r, 4): n for r, n, _ in json.load(open(os.path.join(WORK, "cup_parts.json")))}
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"cup_lod{number}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(62))
        mod = ob.modifiers.get("wn") or ob.modifiers.new("wn", "WEIGHTED_NORMAL")
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
        fa = np.empty(n_loops * 4, np.float32)
        em.color_attributes["facts"].data.foreach_get("color", fa)
        tri_part = fa.reshape(-1, 4)[loops[0::3], 1]
        kept = np.array([rand_name.get(round(float(r), 4)) not in (leave_out or ()) for r in tri_part])
        p = co.reshape(-1, 3)[verts[loops]][:, [1, 2, 0]]
        t = uv.reshape(-1, 2)[loops]
        n = nn.reshape(-1, 3)[loops][:, [1, 2, 0]]
        e.to_mesh_clear()
        tables = ({}, {}, {})
        lines = ([], [], [])
        faces = []
        for k in range(n_tris):
            if not kept[k]:
                continue
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
        with open(os.path.join(OUT, f"{model}_lod{number}.obj"), "w", newline="\n") as h:
            h.write(f"# Generated by Sources/CerroBlanco/cafe-cup-v2/cup.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {NAME}\n")
            h.writelines(faces)
        counts[number] = int(kept.sum())
        print(model, "lod", number, "tris", counts[number], flush=True)
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{FOLDER}/{model}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 10.0, 30.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/CerroBlanco/cafe-cup-v2/cup.py
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
    with open(os.path.join(OUT, f"{model}.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    if model != NAME:
        print("exported", model, counts, flush=True)
        return
    vmat = f"""// Generated by Sources/CerroBlanco/cafe-cup-v2/cup.py

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
	TextureColor "{FOLDER}/{NAME}_color.png"

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
    with open(os.path.join(OUT, f"{NAME}.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("cup stages done", flush=True)
