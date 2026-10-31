"""Boxyard's wheelie bin v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python wheelie_bin.py -- <work dir> <project root> <build|bake|export> ...

A 240 l moulded bin at the size `boxyard_map.wheelie_bin` makes it, standing on the ground about its origin, with +Y its front and
its hinge and wheels at -Y: a tapered body with pressed-in ribs and pockets for its wheels, a rolled rim, a lifting bar, a
lid on three knuckles, a grab bar, and rubber-tyred wheels on an axle. The body is one strip of UVs seamed at the back. One
mesh, with a material each for the map's green, grey and blue. The moulded panels are in the normal map. Inches, engine axes (Z up).
Exports to <work dir>/export, not Assets: an open editor compiles what it finds there, and this waits for the user's word.
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

from build import Part, add, box, frame, lathe, tube  # noqa: E402

BODY, BLACK, ZINC, RUBBER, HUB = 0, 1, kit.ZINC, kit.RUBBER, 6
FOLDER = "models/maps/boxyard/wheelie_bin_v2"
OUT = os.path.join(WORK, "export")
BLEND = os.path.join(WORK, "wheelie_bin_build.blend")
NAME = "wheelie_bin"
COLOURS = ("green", "grey", "blue")
RES = 2048
POS_RANGE = 96.0  # The position bake spans this many inches.
AXLE_Y, AXLE_Z = -12.5, 4.0
WHEEL_R = 4.0
WHEEL_X = 8.0  # The wheels' inner faces, as the old one's.
RIM_Z = 38.2
LID_Z = 39.0
edge_lines = []


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def rounded_ring(half, front, rear, radius, corner=6, along=(4, 3)):
    """A rounded rectangle's points, anticlockwise from above, starting at the middle of the back. `along` splits its straight
    runs across (back and front) and down the sides. Every ring has the same count, so rings can be lofted."""
    across, side = along
    points = []
    x0, x1 = -half + radius, half - radius
    y0, y1 = rear + radius, front - radius

    def run(a, b, steps, last=False):
        for k in range(steps + (1 if last else 0)):
            t = k / steps
            points.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))

    def arc(cx, cy, start):
        for k in range(corner):
            a = math.radians(start + 90.0 * k / corner)
            points.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))

    run((0.0, rear), (x1, rear), across // 2)
    arc(x1, y0, -90.0)
    run((half, y0), (half, y1), side)
    arc(x1, y1, 0.0)
    run((x1, front), (x0, front), across)
    arc(x0, y1, 90.0)
    run((-half, y1), (-half, y0), side)
    arc(x0, y0, 180.0)
    run((x0, rear), (0.0, rear), across // 2)
    return points


def body_ring(z, out, corner_r):
    """The body at a height: its taper, moved out by `out`, with the back corners pulled in over the wheels."""
    t = (z - 2.0) / 38.0
    half = 10.0 + 1.5 * t + out
    front = 12.5 + 2.0 * t + out
    rear = -12.0 - 1.5 * t - out
    ring = rounded_ring(half, front, rear, corner_r)
    pocket = smoothstep(9.1, 8.3, z)
    moved = []
    for x, y in ring:
        back = smoothstep(-7.0, -9.0, y)
        limit = half - (half - 7.3) * pocket * back
        moved.append((max(-limit, min(limit, x)), y))
    return moved


def loft(part, rings):
    """Rings of (x, y, z) lists into a closed skin. Returns the verts by ring."""
    bm = part.bm
    verts = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(verts, verts[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(verts[0])))
    bm.faces.new(list(verts[-1]))
    return verts


def shell():
    """The tapered body, with two pressed stiffening bands and a rolled rim. Its height is settled for the UV strip here."""
    part = piece(BODY, 3, name="body")
    # z, out, corner radius
    stations = [
        (0.9, -1.0, 2.0),
        (1.3, -0.55, 2.2),
        (2.0, -0.1, 2.4),
        (2.8, 0.0, 2.5),
        (8.3, 0.0, 2.6),
        (9.1, 0.0, 2.6),
        (9.6, 0.0, 2.6),
        (9.95, 0.14, 2.65),
        (11.3, 0.14, 2.7),
        (11.65, 0.0, 2.7),
        (17.0, 0.0, 2.75),
        (24.0, 0.0, 2.8),
        (29.6, 0.0, 2.85),
        (29.95, 0.14, 2.9),
        (31.3, 0.14, 2.9),
        (31.65, 0.0, 2.9),
        (36.2, 0.0, 2.95),
        (36.7, 0.18, 3.0),
        (37.3, 0.62, 3.1),
        (37.8, 0.78, 3.15),
        (RIM_Z, 0.78, 3.15),
        (38.45, 0.5, 3.1),
        (38.5, -0.2, 3.0),
        (38.95, -0.28, 3.0),
    ]
    rings = [[(x, y, z) for x, y in body_ring(z, out, r)] for z, out, r in stations]
    loft(part, rings)
    part.columns = len(rings[0])
    heights, run = [], 0.0
    for k, ring in enumerate(rings):
        if k:
            mid = len(ring) // 2  # The middle of the front.
            run += (Vector(ring[mid]) - Vector(rings[k - 1][mid])).length
        heights.append(run)
    part.strip = heights
    # Real widths round the ring, from a station about halfway up, so the panels' texels are square.
    ref = rings[9]
    widths, run = [0.0], 0.0
    for k in range(len(ref)):
        run += (Vector(ref[(k + 1) % len(ref)]) - Vector(ref[k])).length
        widths.append(run)
    part.widths = widths


def base():
    """Two feet at the front and the moulded tie across under the wheels."""
    for sx in (-1, 1):
        foot = piece(BODY, 2, bevel=0.18, segs=1, angle=30, name="foot")
        box(foot, (sx * 8.4 - 1.9, 8.2, 0.0), (sx * 8.4 + 1.9, 12.0, 1.6))
    tie = piece(BODY, 2, bevel=0.14, segs=1, angle=30, name="axle tie")
    box(tie, (-7.3, -13.0, 2.9), (7.3, -10.9, 5.2))
    for sx in (-1, 1):
        cheek = piece(BODY, 2, bevel=0.12, angle=30, name="axle cheek")
        box(cheek, (sx * 7.65 - 0.45, -14.0, 2.45), (sx * 7.65 + 0.45, -8.5, 5.55))


def lift_bar():
    """The bar a bin lorry's comb hooks under, standing proud of the front on two lands."""
    y = 12.5 + 2.0 * (33.0 / 38.0)
    bar = piece(BODY, 3, bevel=0.14, segs=1, angle=30, name="lift bar")
    box(bar, (-8.8, y - 0.2, 34.2), (8.8, y + 0.95, 35.65))
    for sx in (-1, 0, 1):
        land = piece(BODY, 2, bevel=0.1, angle=30, name="land")
        box(land, (sx * 7.4 - 0.75, y - 0.3, 33.2), (sx * 7.4 + 0.75, y + 0.45, 36.5))


def lid():
    part = piece(BODY, 3, name="lid")
    half, front, rear = 12.0, 16.0, -14.4
    # z, inset, corner radius
    stations = [
        (LID_Z, 0.28, 2.7),
        (LID_Z + 0.08, 0.0, 3.0),
        (40.5, 0.0, 3.0),
        (40.85, 0.08, 2.95),
        (41.25, 0.42, 2.7),
        (41.5, 0.95, 2.3),
        (41.75, 2.2, 1.6),
        (42.0, 4.5, 1.2),
        (42.2, 7.2, 1.0),
    ]
    rings = []
    for z, inset, r in stations:
        rings.append([(x, y, z) for x, y in rounded_ring(half - inset, front - inset, rear + inset, r)])
    loft(part, rings)


def hinge():
    y, z = -15.0, 40.1
    rod = piece(ZINC, 1, name="hinge rod")
    lathe(rod, [(0.0, -9.9), (0.2, -9.9), (0.2, 9.9), (0.0, 9.9)], 10, frame((0, y, z), (1, 0, 0)))
    for x in (-8.2, -2.7, 2.7, 8.2):
        k = piece(BODY, 2, bevel=0.06, angle=30, name="knuckle")
        lathe(k, [(0.0, -1.0), (0.42, -1.0), (0.52, -0.9), (0.52, 0.9), (0.42, 1.0), (0.0, 1.0)], 14, frame((x, y, z), (1, 0, 0)))
        web = piece(BODY, 1, bevel=0.06, angle=30, name="knuckle web")
        box(web, (x - 0.9, y - 0.05, z - 0.42), (x + 0.9, y + 0.85, z + 0.42))


def handle():
    """The grab bar across the back, on two brackets moulded to the rim."""
    y, z = -15.7, 37.6
    bar = piece(BLACK, 3, name="grab bar")
    tube(bar, [Vector((x, y, z)) for x in np.linspace(-10.3, 10.3, 8)], 0.62, 12)
    for sx in (-1, 1):
        bracket = piece(BODY, 3, bevel=0.14, segs=1, angle=30, name="bracket")
        box(bracket, (sx * 9.9 - 0.8, y - 0.85, z - 1.1), (sx * 9.9 + 0.8, -13.2, z + 0.95))


def wheels():
    axle = piece(ZINC, 1, name="axle")
    lathe(axle, [(0.0, -10.75), (0.4, -10.75), (0.4, 10.75), (0.0, 10.75)], 10, frame((0, AXLE_Y, AXLE_Z), (1, 0, 0)))
    for sx in (-1, 1):
        m = frame((sx * WHEEL_X, AXLE_Y, AXLE_Z), (sx, 0, 0))
        tyre = piece(RUBBER, 3, name="tyre")
        # Rubber round the rim, a rounded tread, from the bin side out.
        lathe(tyre, [(2.3, 0.05), (3.35, 0.05), (3.72, 0.16), (3.94, 0.42), (WHEEL_R, 0.72), (WHEEL_R, 1.52), (3.94, 1.82), (3.72, 2.08), (3.35, 2.2), (2.3, 2.2)], 28, m)
        hub = piece(HUB, 3, name="hub")
        lathe(hub, [(0.0, 0.0), (2.38, 0.0), (2.38, 2.3), (2.2, 2.42), (2.02, 2.42), (1.9, 2.12), (1.05, 2.12), (0.96, 2.42), (0.74, 2.5), (0.0, 2.5)], 20, m)


def geometry():
    shell()  # First: its vertices lead the mesh, for the UV strip.
    base()
    lift_bar()
    lid()
    hinge()
    handle()
    wheels()


def harden_all():
    """Settle each part's winding, note its convex edges for the wear, then bevel it. The body keeps its vertex order."""
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        if p.finish in (BODY, BLACK, RUBBER, HUB):
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle_signed(0.0) > math.radians(26):
                    a, b = e.verts[0].co, e.verts[1].co
                    count = max(1, int((b - a).length / 0.1))
                    for k in range(count + 1):
                        edge_lines.append(tuple(a.lerp(b, k / count)))
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))


def lay_out_strip(mesh, strip, widths, columns):
    """The body's UVs: one strip, real size, seamed down the middle of the back. The packer treats it as one island."""
    rows = len(strip)
    layer = mesh.uv_layers["UVMap"].data
    for poly in mesh.polygons:
        indices = [mesh.loops[i].vertex_index for i in poly.loop_indices]
        if max(indices) >= rows * columns or len({v // columns for v in indices}) == 1:
            continue  # Not the body, or one of its end caps.
        cols = [v % columns for v in indices]
        wrap = max(cols) == columns - 1 and min(cols) == 0
        for loop_index, v, column in zip(poly.loop_indices, indices, cols):
            if wrap and column == 0:
                column = columns
            layer[loop_index].uv = (widths[column], strip[v // columns])


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    body = kit.parts[0]
    strip, widths, columns = body.strip, body.widths, body.columns
    harden_all()
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "wheelie_bin_lod0")
    hw.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(52), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    lay_out_strip(hw.data, strip, widths, columns)
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
        copy.name = copy.data.name = f"wheelie_bin_lod{number}"
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

    lod(1, 1, 0.45)
    lod(2, 2, 0.16)
    np.save(os.path.join(WORK, "wheelie_bin_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "wheelie_bin.json"), "w") as h:
        json.dump(dict(density=density, res=RES, range=POS_RANGE), h)
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
    hw = bpy.data.objects["wheelie_bin_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 5.0
    with open(os.path.join(WORK, "wheelie_bin_baked_uv_hash.txt"), "w") as h:
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_bin_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_bin_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_bin_facts")
    bake_one(1024, "AO", None, 48, "bake_bin_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["wheelie_bin_lod0"]) != open(os.path.join(WORK, "wheelie_bin_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"wheelie_bin_lod{number}"]
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
            h.write(f"# Generated by Sources/Boxyard/wheelie_bin_v2/wheelie_bin.py\nmtllib {NAME}.mtl\n")
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
// Generated by Sources/Boxyard/wheelie_bin_v2/wheelie_bin.py
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
        vmat = f"""// Generated by Sources/Boxyard/wheelie_bin_v2/wheelie_bin.py

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
print("bin stages done", flush=True)
