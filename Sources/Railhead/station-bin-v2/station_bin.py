"""Railhead's station bin v2: build its meshes, bake its facts and write its files. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python-exit-code 1 --python station_bin.py -- <work dir> <project root> <build|bake|export> ...

The three-bay recycling bin on the map's platforms, concourse, booking hall and cab rank, which was three boxes with its door seams and slots drawn on as
flat black strips. Same overall size and the same hood line, so its collision box still fits. Now its doors sit in real pockets with a shadow line
round them, its slots go in with a rubber flap hanging in them, and its plates, rivets, locks, hinges, hood and ashtray are all there. Origin on the
floor at the middle, front towards +X, width along Y, which is where the map's frame puts them. Inches, engine axes.
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
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, box, frame, lathe, prism  # noqa: E402

STEEL, DARK, RUBBER, PLATE, HARD, DOOR, HOOD, ASH = range(8)
W, D, TOP = 19.7, 8.3, 33.6
GAP = 0.5
BAY = (2 * W - 2 * GAP) / 3
CENTRES = (-(BAY + GAP), 0.0, BAY + GAP)
MODEL = "models/props/railhead/station_bin_v2"
OUT = os.path.join(ROOT, "Assets", "models", "props", "railhead", "station_bin_v2")
BLEND = os.path.join(WORK, "bin_build.blend")
RES = 2048
RANGE = 140.0


def outline(hy, hz, r, segs=3):
    """A rounded rectangle, counter-clockwise, with the same point count at any size."""
    pts = []
    for sy, sz, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for k in range(segs + 1):
            a = math.radians(start + 90 * k / segs)
            pts.append((sy * (hy - r) + r * math.cos(a), sz * (hz - r) + r * math.sin(a)))
    return pts


def plate(part, y, z, hy, hz, r, profile, segs=3, back=True):
    """A rounded plate facing +X: rings of (inset, x), capped in front and, unless nothing sees it, behind."""
    bm = part.bm
    rings = []
    for inset, x in profile:
        ring = outline(hy - inset, hz - inset, max(r - inset, 0.012), segs)
        rings.append([bm.verts.new((x, y + a, z + b)) for a, b in ring])
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    if back:
        bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def relief(part, back, ys, zs, front_at):
    """A box from back to its front, the front a grid of cells each at its own depth, the way pockets sit in a folded panel. Closed."""
    bm = part.bm
    verts = {}

    def v(x, i, j):
        key = (round(x, 4), i, j)
        if key not in verts:
            verts[key] = bm.verts.new((x, ys[i], zs[j]))
        return verts[key]

    ni, nj = len(ys) - 1, len(zs) - 1
    cell = [[front_at((ys[i] + ys[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2) for j in range(nj)] for i in range(ni)]
    for i in range(ni):
        for j in range(nj):
            x = cell[i][j]
            bm.faces.new((v(x, i, j), v(x, i + 1, j), v(x, i + 1, j + 1), v(x, i, j + 1)))
            side = cell[i + 1][j] if i + 1 < ni else back
            if side != x:
                bm.faces.new((v(x, i + 1, j), v(side, i + 1, j), v(side, i + 1, j + 1), v(x, i + 1, j + 1)))
            over = cell[i][j + 1] if j + 1 < nj else back
            if over != x:
                bm.faces.new((v(x, i, j + 1), v(x, i + 1, j + 1), v(over, i + 1, j + 1), v(over, i, j + 1)))
            if i == 0:
                bm.faces.new((v(back, 0, j), v(x, 0, j), v(x, 0, j + 1), v(back, 0, j + 1)))
            if j == 0:
                bm.faces.new((v(back, i, 0), v(back, i + 1, 0), v(x, i + 1, 0), v(x, i, 0)))
    ring = [v(back, i, 0) for i in range(ni)] + [v(back, ni, j) for j in range(nj)]
    ring += [v(back, i, nj) for i in range(ni, 0, -1)] + [v(back, 0, j) for j in range(nj, 0, -1)]
    bm.faces.new(ring)


def picture_frame(part, y, z, hy, hz, t, x0, x1):
    """A flat rectangular ring facing +X, its hole open right through."""
    bm = part.bm

    def loop(h_y, h_z, x):
        return [bm.verts.new((x, y + a * h_y, z + b * h_z)) for a, b in ((1, 1), (-1, 1), (-1, -1), (1, -1))]

    outer0, outer1 = loop(hy, hz, x0), loop(hy, hz, x1)
    inner0, inner1 = loop(hy - t, hz - t, x0), loop(hy - t, hz - t, x1)
    for k in range(4):
        m = (k + 1) % 4
        bm.faces.new((outer0[k], outer0[m], outer1[m], outer1[k]))
        bm.faces.new((inner1[k], inner1[m], inner0[m], inner0[k]))
        bm.faces.new((outer1[k], outer1[m], inner1[m], inner1[k]))
        bm.faces.new((inner0[k], inner0[m], outer0[m], outer0[k]))


def dome(part, at, axis, r, sides=8):
    """A dome-headed rivet or screw."""
    lathe(part, [(r, 0.0), (r, r * 0.2), (r * 0.62, r * 0.48), (0.0, r * 0.55)], sides, frame(at, axis))


def bay(yc):
    y0, y1 = yc - BAY / 2, yc + BAY / 2
    door_y, slot_y = 5.4, 4.8
    # The pocket's floor only needs to be there behind the door's shadow line. Its middle is hidden, so it's left out and takes no atlas.
    ys = sorted({y0, yc - door_y, yc - door_y + 0.28, yc - slot_y, yc + slot_y, yc + door_y - 0.28, yc + door_y, y1})
    zs = (2.2, 4.0, 4.28, 26.72, 27.0, 29.0, 31.8, TOP)

    def front_at(y, z):
        if 4.0 < z < 27.0 and abs(y - yc) < door_y:
            return 7.7
        if 29.0 < z < 31.8 and abs(y - yc) < slot_y:
            return 4.6
        return D

    body = add(Part(STEEL, 3, bevel=0.05, angle=40, name="body"))
    relief(body, -D, ys, zs, front_at)
    bm = body.bm
    bm.normal_update()
    # The folded corners, round enough to catch a highlight. Two segments stay under harden()'s angle, so it leaves them alone.
    folds = [e for e in bm.edges if all(abs(abs(v.co.y - yc) - BAY / 2) < 1e-3 and (abs(v.co.x - D) < 1e-3 or abs(v.co.x + D) < 1e-3) for v in e.verts)]
    bmesh.ops.bevel(bm, geom=folds, offset=0.28, segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
    bm.normal_update()
    hidden = []
    for f in bm.faces:
        c = f.calc_center_median()
        n = f.normal
        if n.z > 0.9 and c.z > TOP - 0.01 or n.z < -0.9 and c.z < 2.21:
            hidden.append(f)  # Under the hood and on the plinth.
        elif abs(n.y) > 0.95 and abs(c.x) < D - 0.2 and abs(c.y) < W - 0.1:
            hidden.append(f)  # Against its neighbour, which the spine between them closes.
        elif n.x > 0.9 and abs(c.x - 7.7) < 1e-3 and abs(c.y - yc) < door_y - 0.3 and 4.3 < c.z < 26.7:
            hidden.append(f)  # Behind the door.
    bmesh.ops.delete(bm, geom=hidden, context="FACES_ONLY")

    # The door in its pocket, with a shadow line all round and its middle pressed in a little, as sheet doors are.
    door = add(Part(DOOR, 3, bevel=0.0, name="door"))
    plate(door, yc, 15.5, door_y - 0.09, 11.41, 0.4, [(0.05, 7.72), (0.05, 8.2), (0.0, 8.24), (0.04, 8.27), (0.78, 8.27), (0.9, 8.235), (0.98, 8.225)], back=False)
    # A triangular-key lock, near the top of the door.
    lock = add(Part(HARD, 1, name="lock"))
    lathe(lock, [(0.66, 0.0), (0.66, 0.09), (0.56, 0.15), (0.34, 0.15), (0.3, 0.07), (0.0, 0.07)], 16, frame((8.22, yc, 24.6), (1, 0, 0)))
    # Two barrels of the hinge on the door's left.
    for z0 in (7.2, 22.0):
        lathe(add(Part(HARD, 0, name="hinge")), [(0.0, 0.0), (0.15, 0.03), (0.2, 0.08), (0.2, 1.72), (0.15, 1.77), (0.0, 1.8)], 8, frame((8.26, yc - door_y + 0.02, z0), (0, 0, 1)))
    # The colour plate, riveted on.
    tag = add(Part(PLATE, 3, name="plate"))
    plate(tag, yc, 17.6, 3.6, 3.6, 0.28, [(0.0, 8.2), (0.0, 8.29), (0.04, 8.32)], back=False)
    for sy, sz in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        dome(add(Part(HARD, 0, name="rivet")), (8.32, yc + sy * 3.14, 17.6 + sz * 3.14), (1, 0, 0), 0.15)
    # The slot's collar, a little proud, and the rubber flap hanging in it, cut into strips that sit a little differently.
    picture_frame(add(Part(STEEL, 1, bevel=0.03, angle=40, name="collar")), yc, 30.4, slot_y + 0.42, 1.82, 0.46, 8.26, 8.42)
    strips = 6
    for k in range(strips):
        a = yc - slot_y + (k + 0.03) * (2 * slot_y / strips)
        b = yc - slot_y + (k + 0.97) * (2 * slot_y / strips)
        tilt = math.radians(float(kit.rng.uniform(6.0, 15.0)))
        drop = float(kit.rng.uniform(1.72, 1.92))
        m = Matrix.Translation((7.4, 0.0, 31.8)) @ Matrix.Rotation(tilt, 4, "Y")
        box(add(Part(RUBBER, 1, name="flap")), (-0.05, a, -drop), (0.05, b, 0.12), m)


def geometry():
    for yc in CENTRES:
        bay(yc)
    # What closes the gaps between the bays, set back behind their folded corners.
    for y in (-(BAY + GAP) / 2, (BAY + GAP) / 2):
        box(add(Part(DARK, 3, name="spine")), (-D + 0.15, y - GAP / 2 - 0.3, 2.2), (D - 0.25, y + GAP / 2 + 0.3, TOP))
    # The plinth, set in as a toe kick, on a flange bolted to the floor.
    toe = add(Part(DARK, 3, bevel=0.04, name="plinth"))
    box(toe, (-D + 1.2, -W + 1.2, 0.0), (D - 1.2, W - 1.2, 2.26))
    flange = add(Part(DARK, 2, bevel=0.03, name="flange"))
    box(flange, (-D + 0.6, -W + 0.6, 0.0), (D - 0.6, W - 0.6, 0.22))
    for part in (toe, flange):
        bm = part.bm
        bm.normal_update()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.9 and (f.normal.z < 0 or part is toe)], context="FACES_ONLY")
    # What closes the bays' undersides, only where the toe kick lets it be seen: four bars round the plinth.
    for lo, hi in (
        ((D - 1.3, -W + 0.1, 2.14), (D - 0.1, W - 0.1, 2.2)),
        ((-D + 0.1, -W + 0.1, 2.14), (-D + 1.3, W - 0.1, 2.2)),
        ((-D + 1.3, W - 1.3, 2.14), (D - 1.3, W - 0.1, 2.2)),
        ((-D + 1.3, -W + 0.1, 2.14), (D - 1.3, -W + 1.3, 2.2)),
    ):
        box(add(Part(DARK, 2, name="soffit")), lo, hi)
    for x in (-D + 0.95, D - 0.95):
        for y in (-13.3, 0.0, 13.3):
            lathe(add(Part(HARD, 0, name="anchor")), [(0.42, 0.0), (0.42, 0.05), (0.31, 0.05), (0.31, 0.2), (0.24, 0.25), (0.0, 0.25)], 6, frame((x, y, 0.22), (0, 0, 1)))
    # Two rails across the back, bolted through to each bay.
    for z in (9.0, 25.0):
        box(add(Part(DARK, 2, bevel=0.03, name="rail")), (-D - 0.22, -W + 0.8, z), (-D + 0.02, W - 0.8, z + 1.8))
        for y in CENTRES:
            for dy in (-3.6, 3.6):
                dome(add(Part(HARD, 0, name="bolt")), (-D - 0.22, y + dy, z + 0.9), (-1, 0, 0), 0.26)

    # The hood over all three, sloping down to the front, with a drip lip that hangs below the bay tops. As the old one's line.
    section = [(-8.7, 33.1), (-8.4, 33.1), (-8.4, TOP), (8.2, TOP), (9.15, TOP), (9.15, 33.05), (9.5, 33.05), (9.5, 35.0), (-8.7, 38.8)]
    # Local Y runs down the world here, so this outline winds the wrong way. Its normals have to be right before they choose what to delete.
    m = frame((0, -19.94, 0), (0, 1, 0), (1, 0, 0))
    hood = add(Part(HOOD, 3, bevel=0.07, angle=30, name="hood"))
    prism(hood, [(x, -z) for x, z in section], 0.0, 39.88, m)
    bm = hood.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < -0.9 and f.calc_center_median().x < 8.1], context="FACES_ONLY")
    for sy, y0 in ((-1, -20.02), (1, 19.94)):
        end = add(Part(HOOD, 3, bevel=0.03, angle=30, name="hood end"))
        prism(end, [(x, -z) for x, z in section], 0.0, 0.08, frame((0, y0, 0), (0, 1, 0), (1, 0, 0)))
        bm = end.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        # The face against the hood is hidden.
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.y * sy < -0.9], context="FACES_ONLY")
        for x, z in ((-7.5, 35.2), (0.0, 34.6), (7.6, 34.3)):
            dome(add(Part(HARD, 0, name="rivet")), (x, sy * 20.02, z), (0, sy, 0), 0.14)
    # Screws along the lip and along the hood's back edge. The hood's top rises 0.2088 for each inch back.
    for y in CENTRES:
        for dy in (-4.2, 4.2):
            dome(add(Part(HARD, 0, name="screw")), (9.5, y + dy, 34.1), (1, 0, 0), 0.16)
            dome(add(Part(HARD, 0, name="screw")), (-7.6, y + dy, 35.0 + (9.5 + 7.6) * 0.2088), (0.2044, 0.0, 0.9789), 0.2)
    # The ashtray let into the hood: a seat following the slope and a stainless cup with its dish sunk in.
    at = (-5.9, 0.0, 35.0 + (9.5 + 5.9) * 0.2088)
    lathe(add(Part(HOOD, 1, name="seat")), [(2.78, -0.05), (2.78, 0.05), (2.7, 0.11), (2.6, 0.13), (0.0, 0.13)], 24, frame(at, (0.2044, 0.0, 0.9789)))
    cup = add(Part(ASH, 3, name="cup"))
    lathe(cup, [(2.6, 37.5), (2.6, 39.44), (2.53, 39.57), (2.38, 39.62), (2.22, 39.57), (2.14, 39.18), (1.95, 39.1), (0.0, 39.1)], 24, frame((-5.9, 0.0, 0.0), (0, 0, 1)))


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    geometry()
    for p in kit.parts:
        bm = p.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    dev = kit.join_parts(kit.parts, "sb_lod0")
    dev.data.uv_layers.new(name="UVMap")
    bpy.context.view_layer.objects.active = dev
    dev.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # A low limit, so eased edges part from the flats. As one island, they'd waste half the atlas.
    bpy.ops.uv.smart_project(angle_limit=math.radians(20), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    dev.select_set(False)
    kit.pack_real_scale(dev.data, RES, 3)

    mesh = dev.data
    uv = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["UVMap"].data.foreach_get("uv", uv)
    # The packer doesn't reject an island wider than the atlas, and the hood's long faces can be. An even scale keeps the real scale.
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

    lod("sb_lod1", 1, 0.55)
    lod("sb_lod2", 2, 0.3)
    lod("sb_lod3", 3, 0.12)
    with open(os.path.join(WORK, "bin.json"), "w") as h:
        json.dump(dict(density=density, range=RANGE), h)
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
    dev = bpy.data.objects["sb_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not dev
    bpy.ops.mesh.primitive_plane_add(size=500, location=(0, 0, -0.01))
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 5.0
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

    bake_one(RES, "EMIT", source("pos"), 1, "bake_sb_pos")
    bake_one(RES, "EMIT", source("nor"), 1, "bake_sb_nor")
    bake_one(RES, "EMIT", source("facts"), 1, "bake_sb_facts")
    bake_one(1024, "AO", None, 48, "bake_sb_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["sb_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2, 3):
        ob = bpy.data.objects[f"sb_lod{lod}"]
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
        with open(os.path.join(OUT, f"bin_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Railhead/station-bin-v2/station_bin.py\nmtllib bin.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl sb_bin\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(OUT, "bin.mtl"), "w", newline="\n") as h:
        h.write("newmtl sb_bin\nKd 1 1 1\nd 1\n")

    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/bin_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 90.0, 220.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Railhead/station-bin-v2/station_bin.py
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
							{{ from = "sb_bin.vmat" to = "{MODEL}/sb_bin.vmat" }}
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
    with open(os.path.join(OUT, "bin.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Railhead/station-bin-v2/station_bin.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MODEL}/sb_bin_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MODEL}/sb_bin_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MODEL}/sb_bin_metal.png"

	//---- Normal ----
	TextureNormal "{MODEL}/sb_bin_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MODEL}/sb_bin_rough.png"
}}
"""
    with open(os.path.join(OUT, "sb_bin.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("bin stages done", flush=True)
