"""Cash Grab's bag v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python cash_bag.py -- <work dir> <project root> <build|bake|export> ...

The mode's objective is today a cloud dev model, `models/dev/duffelbag/dufflebag_money`, on the flat white dev material. This is
a canvas duffel the same size with the same origin (on the ground under its middle), so the first-person, carried and dropped
prefabs that place the old one hold this one the same way: piped end panels, a zip standing open along the top on bundles of
invented banknotes, two web handles lying to either side and a slack shoulder strap on D-rings.
Inches, engine axes, the bag along Y, Z up. Bounds to match: x +-6.45, y -14.51 to 14.08, z -0.06 to 12.05.
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

from build import Part, add, box, frame, lathe, ring_path, spline, tube  # noqa: E402

BRASS, RUBBER, ZINC = kit.BRASS, kit.RUBBER, kit.ZINC
BAG, LINING, ZIP, WEB, BILL, BAND = 9, 10, 11, 12, 13, 14
MODEL = "weapons/special/cash_bag/cash_bag_v2"
OUT_DIR = "Weapons/Special/Cash_Bag/cash_bag_v2"
BLEND = os.path.join(WORK, "cash_bag_build.blend")
SIZE, AO_SIZE = 2048, 1024
rng = np.random.default_rng(4417)

YC, HALF, ZC, HW, HH = -0.21, 14.25, 5.42, 6.2, 5.3
OPEN_HALF, OPEN_MAX = 9.8, 0.66
bundles = []


def shell_noise(seed, count=7, fy=(0.2, 0.8), fa=(1, 5)):
    r = np.random.default_rng(seed)
    terms = [(r.uniform(*fy) * r.choice((-1, 1)), int(r.integers(*fa)), r.uniform(0, 6.28), r.uniform(0.4, 1.0)) for _ in range(count)]
    total = sum(t[3] for t in terms)

    def f(y, a):
        return sum(w * math.sin(k * y + m * a + p) for k, m, p, w in terms) / total

    return f


slump = shell_noise(21)
crease = shell_noise(22, fy=(0.8, 1.8), fa=(2, 9))


def surface(t, a, lift=0.0):
    """A point on the bag and its rough outward direction. t runs -1..1 along it, a is 0 under it and +-pi on top, rising over +X."""
    e = max(0.0, 1.0 - abs(t) ** 8) ** 0.125
    sx, cz = math.sin(a), math.cos(a)
    n = 2.8
    x = HW * e * math.copysign(abs(sx) ** (2 / n), sx)
    z = ZC - HH * e * math.copysign(abs(cz) ** (2 / n), cz)
    y = YC + HALF * t
    weight = e * e
    d = (0.34 * slump(y, a) + 0.13 * crease(y, a)) * weight + lift
    out = Vector((x / max(HW, 1e-6), t**7 * 1.2 * (1 if abs(t) < 1 else 1), (z - ZC) / HH))
    if e < 1e-6:
        out = Vector((0, math.copysign(1, t), 0))
    out.normalize()
    p = Vector((x, y, z)) + out * d
    # It sits on the ground, and what's inside pulls the top down either side of the opening.
    p.z -= 0.55 * weight * max(0.0, -cz) * (1 - t * t) * (0.6 + 0.4 * slump(y * 0.6, 1.0))
    p.z = max(p.z, 0.0)
    p.x = max(min(p.x, 6.4), -6.4)
    return p, out


def face(bm, vs):
    out = []
    for v in vs:
        if not out or out[-1] is not v:
            out.append(v)
    while len(out) > 1 and out[0] is out[-1]:
        out.pop()
    if len(out) >= 3 and len(set(out)) == len(out):
        try:
            bm.faces.new(out)
        except ValueError:
            pass


def grid_solid(outer, inner, edge, O, I, closed):
    """Two surfaces of a sheet and the raw edge between them. Rows run +Y, columns by rising angle; first and last rows are poles."""
    N, count = O.shape[:2]
    M = count - 1

    def verts(part, G):
        rows = []
        for i in range(N):
            if i in (0, N - 1):
                rows.append([part.bm.verts.new(G[i, 0])] * count)
                continue
            row = [part.bm.verts.new(G[i, j]) for j in range(M + (0 if closed[i] else 1))]
            rows.append(row + [row[0]] if closed[i] else row)
        return rows

    a, b = verts(outer, O), verts(inner, I)
    for i in range(N - 1):
        for j in range(M):
            face(outer.bm, (a[i][j], a[i + 1][j], a[i + 1][j + 1], a[i][j + 1]))
            face(inner.bm, (b[i][j + 1], b[i + 1][j + 1], b[i + 1][j], b[i][j]))
    new = edge.bm.verts.new
    for i in range(N - 1):
        if closed[i] and closed[i + 1]:
            continue
        for j, flip in ((M, False), (0, True)):
            q = [new(O[i, j]), new(O[i + 1, j]), new(I[i + 1, j]), new(I[i, j])]
            face(edge.bm, q[::-1] if flip else q)


def shell():
    M = 40
    ends = [0.93, 0.955, 0.975, 0.99, 0.998, 1.0]
    ts = [-x for x in reversed(ends)] + list(np.linspace(-0.9, 0.9, 34)) + ends
    N = len(ts)
    O = np.zeros((N, M + 1, 3))
    I = np.zeros((N, M + 1, 3))
    closed = np.zeros(N, bool)
    lips = []
    for i, t in enumerate(ts):
        y = YC + HALF * t
        s = max(0.0, 1 - (y / OPEN_HALF) ** 2)
        phi = OPEN_MAX * s**0.6 if s > 0.015 else 0.0
        closed[i] = phi == 0.0
        A = math.pi - phi
        for j in range(M + 1):
            x = 2.0 * j / M - 1.0
            a = (0.45 * x + 0.55 * math.sin(x * math.pi / 2)) * A
            # The lips of the open zip stand up a little, stiffened by their tape.
            near = math.exp(-max(A - abs(a), 0.0) * 6.0 / 0.9) if phi > 0 else 0.0
            p, out = surface(t, a, 0.1 * near)
            O[i, j] = tuple(p)
            q = p - out * 0.09
            I[i, j] = tuple(q)
        if not closed[i]:
            lips.append(O[i, 0].copy())
            lips.append(O[i, M].copy())
    np.save(os.path.join(WORK, "lips.npy"), np.array(lips, np.float32))
    print("body bounds", O.min((0, 1)).round(2), O.max((0, 1)).round(2), flush=True)
    grid_solid(add(Part(BAG, 3, name="body")), add(Part(LINING, 3, name="lining")), add(Part(ZIP, 3, name="zip edge")), O, I, closed)


def piping():
    for t in (-0.93, 0.93):
        path = [surface(t, -math.pi + 2 * math.pi * k / 40, 0.06)[0] for k in range(40)]
        tube(add(Part(WEB, 1, name="piping")), path, 0.11, 6, closed=True)


def ribbon(part, points, normals, width, thick):
    """A flat strap along points, its broad face turned to the given normals: a tube would lie any way it liked."""
    bm = part.bm
    rings = []
    n = len(points)
    for i, p in enumerate(points):
        t = (points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized()
        side = t.cross(normals[i]).normalized()
        up = side.cross(t).normalized()
        w, h = side * (width / 2), up * (thick / 2)
        rings.append([bm.verts.new(p + c) for c in (-w - h, -w + h, w + h, w - h)])
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def laid_along(stations):
    """Smooth points and normals through (t, a, lift) stations on the bag."""
    pts, outs = [], []
    for t, a, lift in stations:
        p, out = surface(t, a, lift)
        pts.append(p)
        outs.append(out)
    return spline(pts, 2), [v.normalized() for v in spline(outs, 2)]


def handle(side):
    """A web loop stitched to the side, up over the shoulder and lying by the open zip, wrapped where it's held."""
    t0 = 0.34
    stations = [(-t0, side * (1.15 + 1.0 * f), 0.07) for f in np.linspace(0, 1, 6)]
    stations += [(t0 * k, side * 2.2, 0.1 + 0.52 * (1 - k * k)) for k in np.linspace(-0.9, 0.9, 9)]
    stations += [(t0, side * (2.15 - 1.0 * f), 0.07) for f in np.linspace(0, 1, 6)]
    pts, outs = laid_along(stations)
    ribbon(add(Part(WEB, 3, name="handle")), pts, outs, 1.3, 0.11)
    grip = [(t0 * k, side * 2.2, 0.1 + 0.52 * (1 - k * k)) for k in np.linspace(-0.42, 0.42, 5)]
    pts, outs = laid_along(grip)
    ribbon(add(Part(RUBBER, 2, name="handle wrap")), pts, outs, 1.55, 0.42)


def shoulder_strap():
    rings = {}
    for side in (-1, 1):
        at = Vector((0, YC + side * 13.98, 8.1))
        box(add(Part(WEB, 2, name="d tab")), (-0.62, min(at.y, at.y + side * 0.12), 6.9), (0.62, max(at.y, at.y + side * 0.12), 8.2))
        ring = ring_path(0.72, 16, frame(at + Vector((0, side * 0.14, 0.86)), (0, 1, 0)))
        tube(add(Part(ZINC, 2, name="d ring")), ring, 0.075, 6, closed=True)
        rings[side] = at + Vector((0, side * 0.14, 1.56))
    # Slack on the +X side, from one end's ring down across the bag's flank and up to the other.
    stations = [(t, 1.34 + 1.42 * abs(t) ** 1.6, 0.08) for t in np.linspace(-0.97, 0.97, 15)]
    body, outs = [], []
    for t, a, lift in stations:
        p, out = surface(t, a, lift)
        body.append(p)
        outs.append(out)
    pts = spline([rings[-1]] + body + [rings[1]], 2)
    normals = [v.normalized() for v in spline([Vector((0, -1, 0))] + outs + [Vector((0, 1, 0))], 2)]
    ribbon(add(Part(WEB, 3, name="shoulder strap")), pts, normals, 1.1, 0.1)
    p, _ = surface(-0.12, 1.36, 0.08)
    box(add(Part(ZINC, 2, bevel=0.015, angle=40, name="slider")), (6.3, p.y - 0.34, p.z - 0.72), (6.47, p.y + 0.34, p.z + 0.72))


def zip_pulls():
    for y, side in ((YC + OPEN_HALF * 0.86, 1), (YC - OPEN_HALF * 0.86, -1)):
        p, out = surface((y - YC) / HALF, side * (math.pi - 0.2), 0.14)
        box(add(Part(ZINC, 2, bevel=0.015, angle=40, name="zip slider")), (p.x - 0.28, p.y - 0.42, p.z - 0.06), (p.x + 0.28, p.y + 0.42, p.z + 0.15))
        pull = spline([(p.x, p.y, p.z + 0.12), (p.x + side * 0.5, p.y + 0.28, p.z + 0.2), (p.x + side * 1.25, p.y + 0.34, p.z - 0.05)], 2)
        tube(add(Part(RUBBER, 1, name="zip pull")), pull, 0.13, 6, flatten=0.5)


def banknote_bundle(x, y, z, yaw, roll, pitch):
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(roll, 4, "Y") @ Matrix.Rotation(pitch, 4, "X")
    part = add(Part(BILL, 2, bevel=0.025, angle=40, name="bundle"))
    box(part, (-1.36, -3.08, -0.5), (1.36, 3.08, 0.5), m)
    bundles.append((part, m.inverted()))
    box(add(Part(BAND, 2, name="band")), (-1.39, -0.62, -0.53), (1.39, 0.62, 0.53), m)


def contents():
    d = math.radians
    # The layer you see, then one under it so a look down the gaps finds more cash rather than lining.
    banknote_bundle(-2.72, YC - 5.3, 9.05, d(3), d(-8), d(2))
    banknote_bundle(0.06, YC - 5.9, 9.3, d(-4), d(2), d(-3))
    banknote_bundle(2.8, YC - 5.0, 8.95, d(5), d(7), d(1))
    banknote_bundle(-2.9, YC + 1.3, 9.2, d(-3), d(-7), d(-2))
    banknote_bundle(-0.05, YC + 0.75, 9.95, d(9), d(-5), d(7))
    banknote_bundle(2.75, YC + 1.6, 9.1, d(-5), d(9), d(3))
    banknote_bundle(-2.6, YC + 7.3, 8.8, d(6), d(-9), d(-3))
    banknote_bundle(0.25, YC + 7.5, 9.0, d(-8), d(1), d(2))
    banknote_bundle(2.95, YC + 7.1, 8.6, d(2), d(10), d(-1))
    for x, y, z, yaw in ((-1.5, YC - 3.0, 7.95, 88), (1.55, YC - 2.4, 8.0, 92), (-1.45, YC + 4.2, 7.95, 91), (1.6, YC + 4.6, 7.9, 87)):
        banknote_bundle(x, y, z, d(yaw), 0.0, 0.0)


def geometry():
    shell()
    piping()
    for side in (-1, 1):
        handle(side)
    shoulder_strap()
    zip_pulls()
    contents()


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "cb_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5, use_sharp_edge_from_normals=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
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

    lod("cb_lod1", 1, 0.5)
    lod("cb_lod2", 2, 0.2)
    frames = [dict(rand=part.rand, to_local=[list(row) for row in inv]) for part, inv in bundles]
    with open(os.path.join(WORK, "cash_bag.json"), "w") as h:
        json.dump(dict(density=density, bundles=frames), h)
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
    hw = bpy.data.objects["cb_lod0"]
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

    bake_one(SIZE, "EMIT", source("pos"), 1, "bake_cb_pos")
    bake_one(SIZE, "EMIT", source("nor"), 1, "bake_cb_nor")
    bake_one(SIZE, "EMIT", source("facts"), 1, "bake_cb_facts")
    bake_one(AO_SIZE, "AO", None, 48, "bake_cb_ao")


def write_hull(out):
    """A simple box for a dropped bag to rest on, as the old model had an embedded hull that can't be copied from its compiled file."""
    x, y0, y1, z = 6.1, YC - 14.0, YC + 14.0, 10.4
    corners = [(a, b, c) for a in (-x, x) for b in (y0, y1) for c in (0.0, z)]
    faces = [(1, 2, 4, 3), (5, 7, 8, 6), (1, 5, 6, 2), (3, 4, 8, 7), (1, 3, 7, 5), (2, 6, 8, 4)]
    with open(os.path.join(out, "cash_bag_hulls.obj"), "w", newline="\n") as h:
        h.write("# Generated by Sources/Weapons/cash_bag_v2/cash_bag.py\no cash_bag_hull\n")
        for a, b, c in corners:
            h.write(f"v {b:.3f} {c:.3f} {a:.3f}\n")
        for f in faces:
            h.write("f " + " ".join(str(i) for i in f) + "\n")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", OUT_DIR)
    os.makedirs(out, exist_ok=True)
    if uv_hash(bpy.data.objects["cb_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"cb_lod{lod}"]
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
        with open(os.path.join(out, f"cash_bag_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Weapons/cash_bag_v2/cash_bag.py\nmtllib cash_bag.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl cb_bag\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "cash_bag.mtl"), "w", newline="\n") as h:
        h.write("newmtl cb_bag\nKd 1 1 1\nd 1\n")
    write_hull(out)
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/cash_bag_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 24.0, 70.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Weapons/cash_bag_v2/cash_bag.py
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
							{{ from = "cb_bag.vmat" to = "{MODEL}/cb_bag.vmat" }}
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
						name = "cash_bag_hull"
						parent_bone = ""
						surface_prop = "default"
						collision_tags = "solid"
						recenter_on_parent_bone = false
						offset_origin = [ 0.0, 0.0, 0.0 ]
						offset_angles = [ 0.0, 0.0, 0.0 ]
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						filename = "{MODEL}/cash_bag_hulls.obj"
						import_scale = 1.0
						faceMergeAngle = 10.0
						maxHullVertices = 0
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
    with open(os.path.join(out, "cash_bag.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Weapons/cash_bag_v2/cash_bag.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MODEL}/cb_bag_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/cb_bag_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MODEL}/cb_bag_metal.png"

	//---- Normal ----
	TextureNormal "{MODEL}/cb_bag_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/cb_bag_rough.png"
}}
"""
    with open(os.path.join(out, "cb_bag.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("cash bag stages done", flush=True)
