"""Spillway's canvas cover v2: simulate the sheet, build its meshes, bake its facts and write its files. Made from Orion's tarp.py
(make_canvas_py.py writes this file), with the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python canvas.py -- <work dir> <project root> <sim|clay|build|bake|export> ...

`spillway_map.equipment_cover` is a box of sagging cards on the B2 loading deck, which draws as a mustard crate. This is what it stands
for: an ochre cotton canvas thrown over a generator set on its skid, held down by two ratchet straps where the old strap boxes were. Its
folds come from Blender's cloth solver, run at real scale on the load's own shape. The load fills the old cover's collision box, which
stays: the model has no physics.
Inches, engine axes: on the deck under its middle. Its X is the map's n and its Y the map's -e, so it's placed with no turn.
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
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
import build as kit  # noqa: E402

from build import Part, add, tube  # noqa: E402

TARP, STRAP, BUCKLE = 9, 10, 11
MODEL = "models/maps/spillway/canvas_cover_v2"
MATS = "materials/spillway/canvas_cover_v2"
BLEND = os.path.join(WORK, "canvas_build.blend")
SHEET_FILE = os.path.join(WORK, "sheet_verts.npy")
SIZE, AO_SIZE = 2048, 1024
METRE = 0.0254
SHEET_X, SHEET_Y = 288.0, 300.0  # A 24 x 25 ft cover, inches: down to the deck all round the load with a little to spare.
PITCH = 2.6
FRAMES = 230
# What's under it, in inches: a generator set on its skid, the canopy, a housing on top and a fuel box at one end, and the exhaust
# silencer standing up beside it. It fills the old cover's collision box: x +-65, y +-70, z 0 to 90.
BOXES = [((-63, -68, 0), (63, 68, 9)), ((-58, -66, 9), (58, 38, 70)), ((-40, -58, 70), (30, -8, 84)), ((-52, 40, 9), (8, 66, 46))]
DRUM = ((28.0, 50.0), 13.0, 9.0, 89.5)
HALF = (65.0, 70.0)
RIVER = np.random.default_rng(6121)
# What's by it on the deck: its railings, 30 in off at -x (the map's south) and 40 in off at +y (its west). The walls stop short of both.
SHEET_PX_PER_IN = 6.0


def box_mesh(lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def drum_mesh(drum=DRUM):
    (cx, cy), r, z0, z1 = drum
    n = 28
    v = [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n), z) for z in (z0, z1) for k in range(n)]
    faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    faces += [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    return v, faces


def grid_shape():
    return int(round(SHEET_X / PITCH)), int(round(SHEET_Y / PITCH))


def grid_faces(ni, nj):
    return [(j * (ni + 1) + i, j * (ni + 1) + i + 1, (j + 1) * (ni + 1) + i + 1, (j + 1) * (ni + 1) + i) for j in range(nj) for i in range(ni)]


def sim_stage():
    """The sheet falls on the load, at real scale in metres, and settles."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4

    def collider(name, verts, faces, friction, thick):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(c * METRE for c in p) for p in verts], [], faces)
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        mod = ob.modifiers.new("collision", "COLLISION")
        ob.collision.cloth_friction = friction
        ob.collision.thickness_outer = thick
        ob.collision.damping = 0.4
        ob.collision.use_culling = False

    for k, (lo, hi) in enumerate(BOXES):
        collider(f"box{k}", *box_mesh(lo, hi), 12.0, 0.012)
    collider("drum", *drum_mesh(), 12.0, 0.012)
    collider("ground", [(-600, -600, 0), (600, -600, 0), (600, 600, 0), (-600, 600, 0)], [(0, 1, 2, 3)], 2.0, 0.012)


    # Hands tucking it in: a sheet thrown on lands wide and tents, so four walls walk its hem in along the ground, hold, and step back to let it relax.
    for name, axis, sign, start, end, span in (("+x", 0, 1, 152.0, 76.0, 240), ("-x", 0, -1, 152.0, 76.0, 240), ("+y", 1, 1, 158.0, 81.0, 240), ("-y", 1, -1, 158.0, 81.0, 240)):
        wall = [(0, -span, 0), (0, span, 0), (0, span, 140), (0, -span, 140)] if axis == 0 else [(-span, 0, 0), (span, 0, 0), (span, 0, 140), (-span, 0, 140)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(c * METRE for c in p) for p in wall], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        ob.modifiers.new("collision", "COLLISION")
        ob.collision.cloth_friction = 1.0
        ob.collision.thickness_outer = 0.02
        # Single-sided by default, and half of these face away from the sheet.
        ob.collision.use_culling = False
        # They step back to 12 in off the load: inside the railings at -x and +y.
        for frame, at in ((1, start), (64, start), (150, end), (170, end), (192, end + 12.0)):
            ob.location[axis] = sign * at * METRE
            ob.keyframe_insert("location", index=axis, frame=frame)
        for curve in ob.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"

    ni, nj = grid_shape()
    verts = []
    for j in range(nj + 1):
        for i in range(ni + 1):
            x, y = (i / ni - 0.5) * SHEET_X + 2.0, (j / nj - 0.5) * SHEET_Y - 3.0
            # Thrown on, not laid: a little off square, and not quite flat, so the folds aren't symmetrical.
            tilt = 0.03
            z = 97.0 + 2.6 * math.sin(x * 0.031 + 1.0) * math.sin(y * 0.027 + 0.4) + float(RIVER.uniform(-0.04, 0.04))
            verts.append(((x - tilt * y) * METRE, (y + tilt * x) * METRE, z * METRE))
    mesh = bpy.data.meshes.new("sheet")
    mesh.from_pydata(verts, [], grid_faces(ni, nj))
    ob = bpy.data.objects.new("sheet", mesh)
    scene.collection.objects.link(ob)
    mod = ob.modifiers.new("cloth", "CLOTH")
    s = mod.settings
    s.quality = 10
    s.mass = 0.22
    s.air_damping = 2.5
    s.tension_stiffness = 40.0
    s.compression_stiffness = 40.0
    s.shear_stiffness = 15.0
    s.bending_stiffness = 5.0
    s.tension_damping = 8.0
    s.compression_damping = 8.0
    s.shear_damping = 8.0
    c = mod.collision_settings
    c.collision_quality = 4
    c.distance_min = 0.008
    c.use_self_collision = True
    c.self_distance_min = 0.007
    c.self_friction = 6.0
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, FRAMES

    for frame in range(1, FRAMES + 1):
        scene.frame_set(frame)
        if frame % 15 == 0 or frame == FRAMES:
            dg = bpy.context.evaluated_depsgraph_get()
            e = ob.evaluated_get(dg).to_mesh()
            co = np.empty(len(e.vertices) * 3)
            e.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3) / METRE
            ob.evaluated_get(dg).to_mesh_clear()
            np.save(SHEET_FILE, co.reshape(nj + 1, ni + 1, 3))
            print(f"frame {frame} lo {co.min(0).round(1)} hi {co.max(0).round(1)}", flush=True)
    print("simulated", flush=True)


def clay_stage():
    """Plain renders of the sheet alone, to judge its shape before spending any more on it."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.view_settings.view_transform = "ACES 1.3"
    V = np.load(SHEET_FILE)
    nj, ni = V.shape[0] - 1, V.shape[1] - 1
    mesh = bpy.data.meshes.new("sheet")
    mesh.from_pydata([tuple(p) for p in V.reshape(-1, 3)], [], grid_faces(ni, nj))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    ob = bpy.data.objects.new("sheet", mesh)
    scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("ochre")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.2, 0.06, 1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    mesh.materials.append(mat)
    bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, -0.02))
    g = bpy.data.materials.new("floor")
    g.use_nodes = True
    g.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.2, 0.19, 1)
    bpy.context.object.data.materials.append(g)
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.56, 0.65, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.5
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = Vector((1.0, -0.75, 1.1)).to_track_quat("Z", "Y").to_euler()
    cam = bpy.data.cameras.new("camera")
    cam.lens = 40
    cam.clip_end = 5000
    co = bpy.data.objects.new("camera", cam)
    scene.collection.objects.link(co)
    scene.camera = co
    scene.render.resolution_x, scene.render.resolution_y = 800, 560
    for name, eye in (("a", (300, -250, 150)), ("b", (-300, 200, 170)), ("c", (330, 40, 60))):
        co.location = eye
        co.rotation_euler = (Vector((0, 0, 45)) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(WORK, f"clay_{name}.png")
        bpy.ops.render.render(write_still=True)
    print("clay done", flush=True)


def convex_top(points):
    """The upper hull of ( a, z ) points, left to right: where a taut rope lies."""
    pts = sorted(points)
    hull = []
    for p in pts:
        while len(hull) >= 2 and (hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1]) - (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0]) >= 0:
            hull.pop()
        hull.append(p)
    return hull


def rope_over(tree, centre, across, lift=0.34, low=0.45):
    """A taut rope over the sheet in the upright plane through centre, along across. Returns its path and where its two ends land on the hem."""
    c = Vector((centre[0], centre[1], 18.0))
    h = Vector((across[0], across[1], 0.0)).normalized()
    hits = []
    for k in range(-40, 221, 2):
        t = math.radians(k)
        d = h * math.cos(t) + Vector((0, 0, 1)) * math.sin(t)
        hit = tree.ray_cast(c + d * 400.0, -d, 420.0)
        if hit[0] is not None:
            q = hit[0] - Vector((centre[0], centre[1], 0.0))
            hits.append((float(q.dot(h)), float(q.z)))
    # It ends at the sheet's own edge in this plane, wherever that lies.
    a0, a1 = min(a for a, _ in hits) + 1.5, max(a for a, _ in hits) - 1.5
    hull = convex_top([p for p in hits if a0 < p[0] < a1] + [(a0, low), (a1, low)])
    # Sampled every inch and rounded a little at each bend, resting on the sheet.
    path = [np.array(hull[0], float)]
    for p, q in zip(hull, hull[1:]):
        p, q = np.array(p, float), np.array(q, float)
        steps = max(1, int(np.linalg.norm(q - p) / 1.0))
        path += [p + (q - p) * (k + 1) / steps for k in range(steps)]
    path = np.array(path)
    for _ in range(6):
        path[1:-1] = (path[:-2] + 2 * path[1:-1] + path[2:]) / 4
    tangent = np.gradient(path, axis=0)
    normal = np.stack((-tangent[:, 1], tangent[:, 0]), 1)
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-6)
    normal = np.where(normal[:, 1:2] < 0, -normal, normal)
    path = path + normal * lift
    path3 = [Vector((centre[0], centre[1], 0.0)) + h * float(a) + Vector((0, 0, float(max(z, 0.3)))) for a, z in path]
    # A strap stops at its hooks on the skid, where the cloth comes down past it.
    keep = [k for k, p in enumerate(path3) if p.z > 7.0]
    path3 = path3[keep[0] : keep[-1] + 1]
    ends = [path3[0], path3[-1]]
    return path3, ends, h


def buckle(tree, at, along):
    """A ratchet on the strap: its steel body lying on the cloth, the handle folded flat on it."""
    near = tree.find_nearest(at)
    out = near[1] if near[1].dot(at - Vector((0, 0, 45))) > 0 else -near[1]
    m = kit.frame(tuple(at + out * 0.75), tuple(out), tuple(along))
    kit.box(add(Part(BUCKLE, 2, bevel=0.06, angle=40, name="ratchet")), (-1.9, -1.35, -0.55), (1.9, 1.35, 0.55), m)
    kit.box(add(Part(BUCKLE, 1, bevel=0.04, angle=40, name="ratchet handle")), (-1.0, -1.1, 0.55), (3.6, 1.1, 0.85), m)


def hook(at, out):
    """The strap's flat hook, caught under the skid's edge."""
    m = kit.frame(tuple(at), (0, 0, 1), (out.x, out.y, 0))
    kit.box(add(Part(BUCKLE, 1, bevel=0.04, angle=40, name="hook")), (-0.4, -1.1, -5.0), (0.4, 1.1, 0.4), m)


def build_stage():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    V = np.load(SHEET_FILE)
    nj, ni = V.shape[0] - 1, V.shape[1] - 1
    faces = grid_faces(ni, nj)
    flat = V.reshape(-1, 3).copy()
    flat[:, 2] = np.maximum(flat[:, 2], 0.12)
    # A corner the walls left standing lies down: nothing past the sides' fall stands higher than a ripple.
    off = np.maximum(np.maximum(np.abs(flat[:, 0]) - HALF[0], np.abs(flat[:, 1]) - HALF[1]), 0.0)
    ripple = 0.7 + 0.5 * np.sin(flat[:, 0] * 0.21 + 0.5) * np.sin(flat[:, 1] * 0.17)
    # Layers keep their order, so they don't fight when they land on each other.
    cap = 91.0 * np.clip(1.0 - off / 15.5, 0.0, 1.0) + ripple
    flat[:, 2] = np.where(flat[:, 2] > cap, cap + np.minimum(1.1, (flat[:, 2] - cap) * 0.06), flat[:, 2])
    tree = BVHTree.FromPolygons([tuple(p) for p in flat], faces)

    # Two straps across, along X, where the old strap boxes were (the map's e 1500 and 1600).
    ropes = [rope_over(tree, (0.0, 47.0), (1, 0.015), lift=0.2, low=4.0), rope_over(tree, (0.0, -49.0), (1, -0.02), lift=0.2, low=4.0)]
    # Where a rope bears on the sheet it presses a shallow groove.
    points = [p for path, _, _ in ropes for p in path]
    kd = KDTree(len(points))
    for k, p in enumerate(points):
        kd.insert(p, k)
    kd.balance()
    grid = flat.reshape(nj + 1, ni + 1, 3)
    du, dv = np.gradient(grid, axis=1), np.gradient(grid, axis=0)
    nor = np.cross(du, dv)
    nor /= np.maximum(np.linalg.norm(nor, axis=2, keepdims=True), 1e-6)
    pressed = 0
    for j in range(nj + 1):
        for i in range(ni + 1):
            _, _, d = kd.find(Vector(grid[j, i]))
            if d < 1.8:
                grid[j, i] -= nor[j, i] * 0.35 * (1 - d / 1.8) ** 2
                pressed += 1
    print("pressed", pressed, flush=True)
    # The solver's finest jitter goes, its folds stay, and the hem stays where it landed.
    inner = grid.copy()
    for lam in (0.55, -0.25) * 6:
        lap = inner.copy()
        lap[1:-1, 1:-1] = 0.25 * (inner[:-2, 1:-1] + inner[2:, 1:-1] + inner[1:-1, :-2] + inner[1:-1, 2:]) - inner[1:-1, 1:-1]
        lap[0, :] = lap[-1, :] = lap[:, 0] = lap[:, -1] = 0.0
        inner = inner + lam * lap
    # Where layers met in the solver they left a sawtooth one cell wide. Only that goes: the smoothing fades out where the surface is already calm.
    for _ in range(10):
        lap = inner.copy()
        lap[1:-1, 1:-1] = 0.25 * (inner[:-2, 1:-1] + inner[2:, 1:-1] + inner[1:-1, :-2] + inner[1:-1, 2:]) - inner[1:-1, 1:-1]
        lap[0, :] = lap[-1, :] = lap[:, 0] = lap[:, -1] = 0.0
        size = np.linalg.norm(lap, axis=2, keepdims=True)
        inner = inner + 0.7 * lap * np.clip((size - 0.1) / 0.3, 0.0, 1.0)
    inner[:, :, 2] = np.maximum(inner[:, :, 2], 0.12)
    final = BVHTree.FromPolygons([tuple(p) for p in inner.reshape(-1, 3)], faces)
    # A torn or dragged sheet shows as an edge far longer than the 2.2 in it started at.
    longest = max(np.linalg.norm(np.diff(inner, axis=0), axis=2).max(), np.linalg.norm(np.diff(inner, axis=1), axis=2).max())
    print("longest cloth edge %.1f in" % longest, flush=True)
    print("sheet bounds", inner.reshape(-1, 3).min(0).round(1), inner.reshape(-1, 3).max(0).round(1), flush=True)
    # The solver leaves at most 2.7 in, and laying the corner flaps flat stretches a few to about 8. Dragged across the pile, an edge is 50 or more.
    if longest > 16.0:
        raise RuntimeError("The sheet has been dragged: longest edge %.1f in" % longest)

    # Thinned before it joins the rest: the flats need few triangles and the folds keep theirs.
    mesh = bpy.data.meshes.new("sheet")
    mesh.from_pydata([tuple(p) for p in inner.reshape(-1, 3)], [], faces)
    layer = mesh.uv_layers.new(name="UVMap")
    uv = np.empty(len(mesh.loops) * 2)
    vert_index = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get("vertex_index", vert_index)
    uv[0::2] = (vert_index % (ni + 1)) / ni
    uv[1::2] = (vert_index // (ni + 1)) / nj
    layer.data.foreach_set("uv", uv)
    ob = bpy.data.objects.new("sheet", mesh)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("thin", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = 0.62
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg).to_mesh()
    bm = bmesh.new()
    bm.from_mesh(e)
    uv_layer = bm.loops.layers.uv.active
    # A fold that lies upside down on the floor shows its underside, which the engine lights as if it faced the ground. So those faces turn over.
    bm.normal_update()
    def facing_in(f):
        c = f.calc_center_median()
        if c.z < 5.0:
            return f.normal.z < -0.25
        near = Vector((min(max(c.x, -HALF[0]), HALF[0]), min(max(c.y, -HALF[1]), HALF[1]), min(max(c.z, 0.0), 90.0)))
        out = c - near
        if out.length < 0.5:
            out = Vector((0, 0, 1))
        return f.normal.dot(out.normalized()) < -0.2

    turned = [f for f in bm.faces if facing_in(f)]
    bmesh.ops.reverse_faces(bm, faces=turned, flip_multires=False)
    print("faces turned to face out:", len(turned), "of", len(bm.faces), flush=True)
    # Which point of the cloth each vertex is, which stays with it through the join.
    sheet = {v.index: None for v in bm.verts}
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        for loop in f.loops:
            sheet[loop.vert.index] = tuple(min(max(c, 0.0), 1.0) for c in loop[uv_layer].uv)
    part = add(Part(TARP, 3, name="sheet"))
    part.bm = bm
    n_sheet = len(bm.verts)
    ob.evaluated_get(dg).to_mesh_clear()

    for path, ends, h in ropes:
        # Two-inch polyester webbing, flat on the cloth.
        tube(add(Part(STRAP, 3, name="strap")), path, 1.0, 8, flatten=0.1)
        for k, end in enumerate(ends):
            hook(end, h * (1 if k else -1))
        # The ratchet halfway down the +X side, the map's north, where it was pulled tight from.
        side = [p for p in path if (p - Vector((0, 0, 0))).dot(h) > 0]
        at = min(side, key=lambda p: abs(p.z - 44.0))
        k = path.index(at)
        buckle(final, at, tuple((path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]).normalized()))

    for p in kit.parts:
        kit.harden(p)
        p.done = p.bm
        p.rand = float(kit.rng.uniform(0, 1))
    print("parts", len(kit.parts), flush=True)
    hw = kit.join_parts(kit.parts, "cc_lod0")
    me = hw.data
    colour = me.color_attributes.new("sheet", "FLOAT_COLOR", "CORNER")
    data = np.zeros(len(me.loops) * 4, np.float32)
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", vi)
    for k, v in enumerate(vi):
        if v < n_sheet:
            s, t = sheet[int(v)]
            data[k * 4 : k * 4 + 4] = (s, t, 1.0, 1.0)
    colour.data.foreach_set("color", data)
    me.uv_layers.new(name="UVMap")
    me.polygons.foreach_set("select", np.array([p.loop_start is not None and data[p.loop_start * 4 + 2] < 0.5 for p in me.polygons], bool))
    bpy.context.view_layer.objects.active = hw
    hw.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), margin_method="SCALED", rotate_method="AXIS_ALIGNED_Y", island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    hw.select_set(False)
    # The sheet keeps its own flat layout, so it's one island and its weave runs true.
    uvs = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["UVMap"].data.foreach_get("uv", uvs)
    aspect = SHEET_X / SHEET_Y
    is_sheet = data[2::4] > 0.5
    uvs[0::2][is_sheet] = data[0::4][is_sheet] * aspect
    uvs[1::2][is_sheet] = data[1::4][is_sheet]
    me.uv_layers["UVMap"].data.foreach_set("uv", uvs)
    # By hand: the sheet takes the atlas's left at one density, and everything else packs into the square left at its top right.
    temp = me.copy()
    bm2 = bmesh.new()
    bm2.from_mesh(temp)
    flag = bm2.loops.layers.float_color["sheet"]
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if f.loops[0][flag][2] > 0.5], context="FACES")
    bm2.to_mesh(temp)
    bm2.free()
    kit.pack_real_scale(temp, SIZE, 3)
    rest = np.empty(len(temp.loops) * 2, np.float32)
    temp.uv_layers["UVMap"].data.foreach_get("uv", rest)
    bpy.data.meshes.remove(temp)
    wide, tall = SHEET_X * SHEET_PX_PER_IN / SIZE, SHEET_Y * SHEET_PX_PER_IN / SIZE
    side = 1.0 - wide - 0.006
    uvs[0::2][is_sheet] = data[0::4][is_sheet] * wide
    uvs[1::2][is_sheet] = data[1::4][is_sheet] * tall
    uvs[0::2][~is_sheet] = 1.0 - side + rest[0::2] * side
    uvs[1::2][~is_sheet] = 1.0 - side + rest[1::2] * side
    me.uv_layers["UVMap"].data.foreach_set("uv", uvs)

    uv = np.empty(len(me.loops) * 2)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    me.calc_loop_triangles()
    area3 = uva = 0.0
    for tri in me.loop_triangles:
        a, b, c = co[list(tri.vertices)]
        area3 += 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        p, q, r = uv[list(tri.loops)]
        uva += 0.5 * abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]))
    density = SIZE * math.sqrt(uva / area3)
    print("tris", len(me.loop_triangles), "fill %.2f" % uva, "px/in %.1f" % density, flush=True)

    lookup = {round(p.rand, 4): p for p in kit.parts}

    def lod(name, keep, ratio):
        copy = hw.copy()
        copy.data = hw.data.copy()
        copy.name = copy.data.name = name
        bpy.context.scene.collection.objects.link(copy)
        bm2 = bmesh.new()
        bm2.from_mesh(copy.data)
        facts = bm2.loops.layers.float_color["facts"]
        drop = [f for f in bm2.faces if lookup.get(round(f.loops[0][facts][1], 4)) is not None and lookup[round(f.loops[0][facts][1], 4)].lod < keep]
        bmesh.ops.delete(bm2, geom=drop, context="FACES")
        bm2.to_mesh(copy.data)
        bm2.free()
        bpy.context.view_layer.objects.active = copy
        copy.select_set(True)
        m2 = copy.modifiers.new("collapse", "DECIMATE")
        m2.decimate_type = "COLLAPSE"
        m2.ratio = ratio
        m2.use_collapse_triangulate = True
        m2.delimit = {"UV", "SEAM"}
        bpy.ops.object.modifier_apply(modifier=m2.name)
        copy.select_set(False)
        copy.data.calc_loop_triangles()
        print(name, "tris", len(copy.data.loop_triangles), flush=True)

    lod("cc_lod1", 1, 0.42)
    lod("cc_lod2", 2, 0.14)
    with open(os.path.join(WORK, "canvas.json"), "w") as h:
        json.dump(dict(density=SHEET_PX_PER_IN, sheet=[SHEET_X, SHEET_Y]), h)
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
    hw = bpy.data.objects["cc_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 12.0
    with open(os.path.join(WORK, "canvas_baked_uv_hash.txt"), "w") as h:
        h.write(uv_hash(hw))

    def source(kind):
        def setup(nt, emit):
            if kind in ("facts", "sheet"):
                attr = nt.nodes.new("ShaderNodeVertexColor")
                attr.layer_name = kind
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

    bake_one(SIZE, "EMIT", source("pos"), 1, "bake_cc_pos")
    bake_one(SIZE, "EMIT", source("nor"), 1, "bake_cc_nor")
    bake_one(SIZE, "EMIT", source("facts"), 1, "bake_cc_facts")
    bake_one(SIZE, "EMIT", source("sheet"), 1, "bake_cc_sheet")
    bake_one(AO_SIZE, "AO", None, 64, "bake_cc_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(ROOT, "Assets", MODEL)
    mats = os.path.join(ROOT, "Assets", MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["cc_lod0"]) != open(os.path.join(WORK, "canvas_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in (0, 1, 2):
        ob = bpy.data.objects[f"cc_lod{lod}"]
        mesh = ob.data
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.set_sharp_from_angle(angle=math.radians(100))
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
        t = np.clip(uv.reshape(-1, 2)[loops], 0.0, 1.0)
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
        with open(os.path.join(out, f"canvas_cover_lod{lod}.obj"), "w", newline="\n") as h:
            h.write("# Generated by Sources/Spillway/canvas-cover-v2/canvas.py\nmtllib canvas_cover.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write("usemtl cc_canvas\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, "canvas_cover.mtl"), "w", newline="\n") as h:
        h.write("newmtl cc_canvas\nKd 1 1 1\nd 1\n")
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/canvas_cover_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 30.0, 90.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Spillway/canvas-cover-v2/canvas.py
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
							{{ from = "cc_canvas.vmat" to = "{MATS}/cc_canvas.vmat" }}
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
    with open(os.path.join(out, "canvas_cover.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Spillway/canvas-cover-v2/canvas.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1
	// One layer of cloth: where a fold turns its underside up, it still has to draw.
	F_RENDER_BACKFACES 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/cc_canvas_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/cc_canvas_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{MATS}/cc_canvas_metal.png"

	//---- Normal ----
	TextureNormal "{MATS}/cc_canvas_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/cc_canvas_rough.png"
}}
"""
    with open(os.path.join(mats, "cc_canvas.vmat"), "w", newline="\n") as h:
        h.write(vmat)
    print("exported", counts, flush=True)


if "sim" in STAGES:
    sim_stage()
if "clay" in STAGES:
    clay_stage()
if "build" in STAGES:
    build_stage()
if "bake" in STAGES:
    bake_stage()
if "export" in STAGES:
    export_stage()
print("canvas stages done", flush=True)
