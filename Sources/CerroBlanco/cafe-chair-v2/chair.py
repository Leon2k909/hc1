"""Cerro Blanco's cafe chair v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python chair.py -- <work dir> <project root> <build|bake|export> ...

A steel bistro chair with a teak seat in place of a slab on four square bars: five teak slats screwed down to a flat-bar apron, front legs splayed a little, the rear legs sweeping up into raked back
posts with two curved teak slats across them, side stretchers, nylon glides and domed post caps. Anthracite powder coat, as the courtyard's parasols. No maker's names.

Inches. +X is the way it faces, Y across it, Z up, and the origin is on the floor under the seat's middle, as the old chair's. The seat's top is at 18.
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

TEAK, POWDER, CAST, NYLON, STEEL = 0, 1, 2, 3, 4
FOLDER = "models/maps/cerroblanco/cafe_chair_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "cerroblanco", "cafe_chair_v2")
BLEND = os.path.join(WORK, "chair_build.blend")
NAME = "chair"
W, H = 2048, 2048
POS_RANGE = 80.0  # The position bake spans this many inches, centred on the origin.

SEAT_TOP, SLAT_T = 18.0, 0.75
SLAT_DEPTH, SLAT_GAP, SLAT_HALF = 2.9, 0.36, 8.5
REAR_SLAT_HALF = 7.55  # The back slat of the seat fits between the posts.
APRON_Z0, APRON_Z1, APRON_T = 16.0, SEAT_TOP - SLAT_T, 0.22
TUBE_R = 0.4
FRONT_TOP, FRONT_FOOT = (6.6, 7.2), (7.5, 7.9)  # ( x, y ) of a front leg at the apron and on the floor.
REAR_SEAT = (-6.75, 8.1)  # Where a rear leg passes the seat.
STRETCH_Z = 6.0
BACK_RAKE = 10.0  # Degrees the back leans.
BACK_SLATS = ((30.0, 3.4), (25.2, 2.4))  # Middle height and height of each back slat.
BACK_BOW = 0.8
rng = np.random.default_rng(2617)
edge_lines = []
SCREWS = []  # Each screw's head centre and axis, for the paint.
SLATS = {}  # Each slat's middle: x for the seat's, ( x at its ends, z ) for the back's.
NO_EDGE = ("screw", "glide", "weld")


def piece(finish, lod, bevel=0.0, segs=1, angle=35.0, name=""):
    return add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))


def bar(part, path, w, h, up_hint=(0, 0, 1)):
    """A rectangular section, w across and h along up_hint (as near as the path allows), swept along points."""
    bm = part.bm
    pts = [Vector(p) for p in path]
    hint = Vector(up_hint).normalized()
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(hint)
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * sx * w / 2 + up * sz * h / 2) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for a, b in zip(rings, rings[1:]):
        for c in range(4):
            bm.faces.new((a[c], a[(c + 1) % 4], b[(c + 1) % 4], b[c]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def rear_leg(side):
    """A rear leg from its glide up past the seat and on into the back post, as one bent tube: plan ( x, y, z ) points."""
    s = side
    return kit.spline([(-8.0, s * 7.95, 0.45), (-7.35, s * 8.02, 8.0), (REAR_SEAT[0], s * REAR_SEAT[1], 16.4), (-6.85, s * 8.08, 18.6), (-7.55, s * 8.0, 22.5), (-8.55, s * 7.9, 27.5), (-9.4, s * 7.8, 32.6)], 6)


def post_x(z):
    """Where the back posts' middle is, at height z."""
    path = rear_leg(1)
    for a, b in zip(path, path[1:]):
        if a.z <= z <= b.z:
            t = (z - a.z) / max(b.z - a.z, 1e-6)
            return a.lerp(b, t)
    return path[-1]


def seat():
    x0 = -(5 * SLAT_DEPTH + 4 * SLAT_GAP) / 2
    for k in range(5):
        lo = x0 + k * (SLAT_DEPTH + SLAT_GAP)
        half = REAR_SLAT_HALF if k == 0 else SLAT_HALF
        kit.box(piece(TEAK, 3, bevel=0.16, segs=2, angle=40, name=f"seat slat {k}"), (lo, -half, SEAT_TOP - SLAT_T), (lo + SLAT_DEPTH, half, SEAT_TOP))
        SLATS[f"seat slat {k}"] = lo + SLAT_DEPTH / 2
        # Two screws at each end, into the apron's side bars.
        for sy in (-1, 1):
            y = sy * (apron_side_y(lo + SLAT_DEPTH / 2))
            for dx in (0.75, SLAT_DEPTH - 0.75):
                kit.lathe(piece(STEEL, 0, name="screw"), [(0.15, -0.02), (0.15, 0.0), (0.1, 0.03), (0, 0.035)], 10, kit.frame((lo + dx, y, SEAT_TOP)))
                SCREWS.append(((lo + dx, y, SEAT_TOP), (0.0, 0.0, 1.0)))


def apron_side_y(x):
    """The apron's side bar runs from the front leg to the rear one: its y at x."""
    fx, fy = FRONT_TOP
    rx, ry = REAR_SEAT
    t = (x - rx) / (fx - rx)
    return ry + (fy - ry) * t - 0.05


def frame():
    z = (APRON_Z0 + APRON_Z1) / 2
    h = APRON_Z1 - APRON_Z0
    fx, fy = FRONT_TOP
    rx, ry = REAR_SEAT
    # The apron: four flat bars standing on edge under the slats, welded to the legs.
    for sy in (-1, 1):
        bar(piece(POWDER, 3, bevel=0.04, angle=40, name="apron"), [Vector((fx, sy * (fy - 0.05), z)), Vector((rx, sy * (ry - 0.05), z))], APRON_T, h)
    bar(piece(POWDER, 3, bevel=0.04, angle=40, name="apron"), [Vector((fx + 0.1, -fy, z)), Vector((fx + 0.1, fy, z))], APRON_T, h)
    bar(piece(POWDER, 3, bevel=0.04, angle=40, name="apron"), [Vector((rx + 0.05, -ry, z)), Vector((rx + 0.05, ry, z))], APRON_T, h)
    for sy in (-1, 1):
        front = [Vector((FRONT_FOOT[0], sy * FRONT_FOOT[1], 0.45)), Vector((fx, sy * fy, APRON_Z1 - 0.1))]
        tube(piece(POWDER, 3, name="leg"), front, TUBE_R, 12)
        rear = rear_leg(sy)
        tube(piece(POWDER, 3, name="leg"), rear, TUBE_R, 12)
        # A domed cap welded on the post's top.
        top, before = rear[-1], rear[-2]
        kit.lathe(piece(POWDER, 1, name="cap"), [(TUBE_R + 0.02, -0.02), (TUBE_R + 0.02, 0.05), (TUBE_R * 0.75, 0.2), (0.2, 0.28), (0, 0.3)], 12, kit.frame(top, top - before))
        # Glides on both feet, along each leg.
        for foot, above in ((front[0], front[1]), (rear[0], rear[1])):
            axis = (above - foot).normalized()
            kit.lathe(piece(NYLON, 1, name="glide"), [(0, -0.42), (TUBE_R + 0.06, -0.42), (TUBE_R + 0.1, -0.32), (TUBE_R + 0.06, 0.12), (TUBE_R - 0.02, 0.16)], 12, kit.frame(foot, axis))
        # The side stretcher between the legs, and its welds.
        f = front[0].lerp(front[1], (STRETCH_Z - 0.45) / (front[1].z - 0.45))
        r = next(p for p in rear if p.z >= STRETCH_Z)
        tube(piece(POWDER, 2, name="stretcher"), [f - Vector((0.25, 0, 0)), r + Vector((0.25, 0, 0))], 0.27, 10)
        for at, along in ((f, front[1] - front[0]), (r, rear[3] - rear[0])):
            tube(piece(POWDER, 0, name="weld"), kit.ring_path(TUBE_R + 0.03, 14, kit.frame(at, along)), 0.07, 4, closed=True)
        for at in (Vector((fx, sy * fy, APRON_Z0 - 0.02)),):
            tube(piece(POWDER, 0, name="weld"), kit.ring_path(TUBE_R + 0.03, 14, kit.frame(at, front[1] - front[0])), 0.07, 4, closed=True)


def back():
    """Two teak slats across the posts' fronts, bowed back to the sitter and leaning with the posts, each held by a screw at each end."""
    lean = Vector((-math.sin(math.radians(BACK_RAKE)), 0, math.cos(math.radians(BACK_RAKE))))
    for k, (zc, height) in enumerate(BACK_SLATS):
        post = post_x(zc)
        x_end = post.x + TUBE_R + 0.36
        span = post.y + 0.55
        path = []
        for j in range(17):
            y = -span + 2 * span * j / 16
            path.append(Vector((x_end - BACK_BOW * (1 - (y / span) ** 2), y, zc)))
        bar(piece(TEAK, 3, bevel=0.14, segs=2, angle=40, name=f"back slat {k}"), path, 0.65, height, lean)
        SLATS[f"back slat {k}"] = (x_end, zc)
        for sy in (-1, 1):
            for dz in (-height * 0.25, height * 0.25):
                at = Vector((x_end + 0.33, sy * post.y, zc + dz))
                kit.lathe(piece(STEEL, 0, name="screw"), [(0.15, -0.02), (0.15, 0.0), (0.1, 0.03), (0, 0.035)], 10, kit.frame(at, (1, 0, 0)))
                SCREWS.append((tuple(at), (1.0, 0.0, 0.0)))


def geometry():
    seat()
    frame()
    back()


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
    """How much texture an island gets, against the seat's top at 1."""
    if finish == TEAK:
        if normal.z > 0.7 or normal.x > 0.7:
            return 1.0
        if normal.z < -0.7:
            return 0.45
        return 0.75
    if finish == NYLON:
        return 0.6
    if finish == STEEL:
        return 1.2
    return 0.9


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
    hw = kit.join_parts(kit.parts, "chair_lod0")
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
        copy.name = copy.data.name = f"chair_lod{number}"
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
    np.save(os.path.join(WORK, "chair_edges.npy"), np.array(edge_lines, np.float32))
    with open(os.path.join(WORK, "chair_parts.json"), "w") as h:
        json.dump([[p.rand, p.name, p.finish] for p in kit.parts], h)
    with open(os.path.join(WORK, "chair.json"), "w") as h:
        json.dump(
            dict(density=density, range=POS_RANGE, seat_top=SEAT_TOP, slat=(SLAT_T, SLAT_DEPTH, SLAT_GAP, SLAT_HALF, REAR_SLAT_HALF), back=BACK_SLATS, rake=BACK_RAKE, bow=BACK_BOW, screws=SCREWS, slats=SLATS),
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
    hw = bpy.data.objects["chair_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 3.0
    with open(os.path.join(WORK, "chair_baked_uv_hash.txt"), "w") as h:
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

    bake_one(W, H, "EMIT", source("pos"), 1, "bake_ch_pos")
    bake_one(W, H, "EMIT", source("nor"), 1, "bake_ch_nor")
    bake_one(W, H, "EMIT", source("facts"), 1, "bake_ch_facts")
    bake_one(W // 2, H // 2, "AO", None, 40, "bake_ch_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(OUT, exist_ok=True)
    if uv_hash(bpy.data.objects["chair_lod0"]) != open(os.path.join(WORK, "chair_baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for number in (0, 1, 2):
        ob = bpy.data.objects[f"chair_lod{number}"]
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
            h.write(f"# Generated by Sources/CerroBlanco/cafe-chair-v2/chair.py\nmtllib {NAME}.mtl\n")
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
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/CerroBlanco/cafe-chair-v2/chair.py
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
    with open(os.path.join(OUT, f"{NAME}.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/CerroBlanco/cafe-chair-v2/chair.py

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
print("chair stages done", flush=True)
