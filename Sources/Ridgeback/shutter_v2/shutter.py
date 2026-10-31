"""Ridgeback's town house shutter v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python shutter.py -- <work dir> <project root> <build|bake|export> ...

The old shutter is one flat box, 34 times over. This is a louvred timber leaf in the same 25 x 64 x 1.5 in: stiles, rails and angled
slats, on black strap hinges and pintles, with a pull ring and a shutter dog holding it open. Two models, mirror images of one mesh and
one atlas, since a leaf is hinged on the side nearest its window. No collision, as the old one had none.
Inches, engine axes: +X out from the wall, Y along it, Z up, origin at the leaf's foot where it meets the wall, in the middle.
`shutter_l` is hinged at +Y, `shutter_r` at -Y. Exported outside Assets until the user approves, because an open editor compiles what it finds.
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

from build import Part, add, box, lathe, spline, tube  # noqa: E402

BOARD_Y, BOARD_Z, IRON, LINER = range(4)
NAME = "shutter"
MODEL = "models/props/ridgeback/shutter_v2"
MATS = "materials/ridgeback/shutter_v2"
EXPORT = os.path.join(WORK_ROOT, "shutter_v2")  # Laid out like Assets, ready to copy in.
BLEND = os.path.join(WORK, "shutter_build.blend")
ATLAS = 2048
WIDTH, HEIGHT, THICK = 25.0, 64.0, 1.5
rng = np.random.default_rng(2231)
seams = []  # Points along every piped seam, so the paint stage can gather the cloth into them.


def spaced(half, r, interior):
    """Lattice lines across a box: tight round the rounded edge, sparse across the middle."""
    edge = [-half, -half + r * 0.42, -half + r]
    middle = list(np.linspace(-half + r, half - r, interior + 2)[1:-1])
    return edge + middle + [-x for x in reversed(edge)]


class Soft:
    """A rounded, crowned, slightly lumpy upholstered box: a lattice on its surface, pushed into shape."""

    def __init__(self, finish, lod, lo, hi, r, crown=(0, 0, 0, 0, 0, 0), interior=(2, 2, 0), m=Matrix.Identity(4), lump=0.1, name="", texel=1.0):
        self.c = (Vector(lo) + Vector(hi)) / 2
        self.h = (Vector(hi) - Vector(lo)) / 2
        self.r, self.crown, self.m, self.lump = r, crown, m, lump
        self.seed = rng.uniform(0, 40, 6)
        part = add(Part(finish, lod, name=name))
        part.texel = texel
        bm = part.bm
        xs = spaced(self.h.x, r, interior[0])
        ys = spaced(self.h.y, r, interior[1])
        zs = spaced(self.h.z, r, interior[2])
        verts = {}

        def vert(i, j, k):
            key = (i, j, k)
            if key not in verts:
                verts[key] = bm.verts.new(self.point(Vector((xs[i], ys[j], zs[k]))))
            return verts[key]

        nx, ny, nz = len(xs) - 1, len(ys) - 1, len(zs) - 1
        for i in range(nx):
            for j in range(ny):
                bm.faces.new((vert(i, j, nz), vert(i + 1, j, nz), vert(i + 1, j + 1, nz), vert(i, j + 1, nz)))
                bm.faces.new((vert(i, j + 1, 0), vert(i + 1, j + 1, 0), vert(i + 1, j, 0), vert(i, j, 0)))
        for i in range(nx):
            for k in range(nz):
                bm.faces.new((vert(i, 0, k), vert(i + 1, 0, k), vert(i + 1, 0, k + 1), vert(i, 0, k + 1)))
                bm.faces.new((vert(i, ny, k + 1), vert(i + 1, ny, k + 1), vert(i + 1, ny, k), vert(i, ny, k)))
        for j in range(ny):
            for k in range(nz):
                bm.faces.new((vert(0, j, k + 1), vert(0, j + 1, k + 1), vert(0, j + 1, k), vert(0, j, k)))
                bm.faces.new((vert(nx, j, k), vert(nx, j + 1, k), vert(nx, j + 1, k + 1), vert(nx, j, k + 1)))

    def point(self, q):
        """A point on the box's surface, in its own frame, to where it ends up in the model."""
        h, r = self.h, self.r
        inner = Vector((max(-h.x + r, min(h.x - r, q.x)), max(-h.y + r, min(h.y - r, q.y)), max(-h.z + r, min(h.z - r, q.z))))
        d = q - inner
        p = inner + d.normalized() * r if d.length > 1e-6 else q.copy()
        u, v, w = q.x / h.x, q.y / h.y, q.z / h.z
        cx, cy, cz = (1 - u * u), (1 - v * v), (1 - w * w)
        top, bottom, front, back, right, left = self.crown
        p.z += top * cx * cy * max(0.0, w) ** 0.5 - bottom * cx * cy * max(0.0, -w) ** 0.5
        p.x += front * cy * cz * max(0.0, u) ** 0.5 - back * cy * cz * max(0.0, -u) ** 0.5
        p.y += right * cx * cz * max(0.0, v) ** 0.5 - left * cx * cz * max(0.0, -v) ** 0.5
        s = self.seed
        wobble = math.sin(p.x * 0.31 + s[0]) * math.sin(p.y * 0.27 + s[1]) + 0.5 * math.sin(p.x * 0.73 + s[2]) * math.sin(p.z * 0.81 + s[3])
        n = p - inner
        if n.length > 1e-6:
            p += n.normalized() * wobble * self.lump
        return self.m @ (p + self.c)

    def piping(self, finish, axis, at, lod=0, radius=0.16):
        """A piped seam round the box at a fraction of its height along axis, following its shape."""
        h, r = self.h, self.r
        a, b = [i for i in range(3) if i != axis]
        ha, hb = h[a], h[b]
        rr = min(r * 0.9, ha, hb)
        corner = []
        for sa, sb, start in ((1, 1, 0.0), (-1, 1, 90.0), (-1, -1, 180.0), (1, -1, 270.0)):
            for t in np.linspace(0, 90, 4):
                ang = math.radians(start + t)
                corner.append((sa * (ha - rr) + rr * math.cos(ang), sb * (hb - rr) + rr * math.sin(ang)))
        # Extra points along the long runs, so the crown is followed.
        path2d = []
        for k, p0 in enumerate(corner):
            p1 = corner[(k + 1) % len(corner)]
            path2d.append(p0)
            gap = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            for t in np.linspace(0, 1, max(0, int(gap / 4.5)) + 2)[1:-1]:
                path2d.append((p0[0] + (p1[0] - p0[0]) * float(t), p0[1] + (p1[1] - p0[1]) * float(t)))
        path = []
        for pa, pb in path2d:
            q = Vector((0, 0, 0))
            q[a], q[b] = pa, pb
            q[axis] = h[axis] * at
            # Lie on the side faces, not inside: push out to the box's own surface in its plane.
            scale = max(abs(pa) / ha, abs(pb) / hb)
            q[a] /= scale
            q[b] /= scale
            path.append(self.point(q))
        tube(add(Part(finish, lod, name="piping")), path, radius, 5, closed=True)
        seams.extend([tuple(p) for p in path])


def tilt_about(pivot, axis, degrees):
    return Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(degrees), 4, axis) @ Matrix.Translation(-Vector(pivot))


def bx(finish, lod, lo, hi, bevel=0.06, name="", m=Matrix.Identity(4), angle=40, segs=1, texel=1.0):
    p = add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))
    box(p, lo, hi, m)
    p.texel = texel
    return p


def strap_hinge(z):
    half = WIDTH / 2
    # A tapered iron strap on the leaf's face, running in from the hinge side, on a knuckle round its pintle.
    p = add(Part(IRON, 2, bevel=0.015, angle=30, name="strap"))
    bm = p.bm
    outline = [(half + 0.05, z - 0.62), (half + 0.05, z + 0.62), (half - 3.0, z + 0.55), (half - 7.4, z + 0.3), (half - 7.9, z), (half - 7.4, z - 0.3), (half - 3.0, z - 0.55)]
    front = [bm.verts.new((THICK + 0.1, y, zz)) for y, zz in outline]
    back = [bm.verts.new((THICK - 0.02, y, zz)) for y, zz in outline]
    n = len(outline)
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for k in range(n):
        bm.faces.new((front[k], back[k], back[(k + 1) % n], front[(k + 1) % n]))
    lathe(add(Part(IRON, 1, name="pintle")), [(0.42, -0.95), (0.42, 0.95), (0.3, 1.06), (0, 1.1)], 8, kit.frame((THICK * 0.72, half + 0.3, z)))
    for y in (half - 1.3, half - 3.5, half - 6.0):
        lathe(add(Part(IRON, 0, name="bolt head")), [(0.2, 0.0), (0.18, 0.05), (0.08, 0.1), (0, 0.11)], 6, kit.frame((THICK + 0.1, y, z), (1, 0, 0)))


def geometry():
    half = WIDTH / 2
    stile = 2.7
    # A dark board behind the slats, so what shows between them is shadow, not lit wall.
    bx(LINER, 3, (0.02, -half + 0.4, 0.4), (0.2, half - 0.4, HEIGHT - 0.4), 0.0, "backing", texel=0.25)
    for y0, y1 in ((-half, -half + stile), (half - stile, half)):
        bx(BOARD_Z, 3, (0.0, y0, 0.0), (THICK, y1, HEIGHT), 0.1, "stile", texel=1.15)
    y0, y1 = -half + stile, half - stile
    bottom, mid_lo, mid_hi, top = 5.2, 29.6, 32.8, 60.8
    for z0, z1 in ((0.0, bottom), (mid_lo, mid_hi), (top, HEIGHT)):
        bx(BOARD_Y, 3, (0.08, y0, z0), (THICK - 0.08, y1, z1), 0.1, "rail", texel=1.15)
    # The slats, sloping down and out, so rain runs off the face.
    pitch, tilt = 1.12, math.radians(38.0)
    for z0, z1 in ((bottom, mid_lo), (mid_hi, top)):
        count = int((z1 - z0) / pitch)
        step = (z1 - z0) / count
        for k in range(count):
            z = z0 + step * (k + 0.5)
            m = Matrix.Translation((THICK / 2 + 0.02, 0, z)) @ Matrix.Rotation(tilt, 4, "Y")
            bx(BOARD_Y, 2, (-0.72, y0 - 0.1, -0.11), (0.72, y1 + 0.1, 0.11), 0.0, "slat", m, texel=0.8)
    # Hardware: two hinges on the +Y stile, a pull ring on the free one, and the dog that holds it open.
    for z in (11.5, 52.5):
        strap_hinge(z)
    lathe(add(Part(IRON, 1, name="ring plate")), [(0.7, 0.0), (0.7, 0.05), (0.42, 0.14), (0, 0.18)], 10, kit.frame((THICK, -half + stile / 2, 31.2), (1, 0, 0)))
    ring = [(THICK + 0.26, -half + stile / 2 + 0.62 * math.sin(a), 31.2 - 0.62 + 0.62 * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    tube(add(Part(IRON, 0, name="pull ring")), ring, 0.08, 5, closed=True)
    dog = spline([(0.0, -half - 1.1, 4.0), (0.8, -half - 1.1, 4.2), (1.6, -half - 0.2, 4.1), (2.1, -half + 0.9, 3.9), (2.0, -half + 1.5, 3.1)], 3)
    tube(add(Part(IRON, 1, name="shutter dog")), dog, 0.19, 6)
    lathe(add(Part(IRON, 1, name="dog plate")), [(0.55, 0.0), (0.55, 0.06), (0.3, 0.1), (0, 0.12)], 8, kit.frame((0.0, -half - 1.1, 4.0), (1, 0, 0)))


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
    hw = kit.join_parts(kit.parts, "shutter_lod0")
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

    lod("shutter_lod1", 1, 0.5)
    lod("shutter_lod2", 2, 0.28)
    lod("shutter_lod3", 3, 0.14)
    with open(os.path.join(WORK, "shutter.json"), "w") as h:
        json.dump(dict(density=density, seams=seams), h)
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
    hw = bpy.data.objects["shutter_lod0"]
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

    bake_one(ATLAS, "EMIT", source("pos"), 1, "bake_shutter_pos")
    bake_one(ATLAS, "EMIT", source("nor"), 1, "bake_shutter_nor")
    bake_one(ATLAS, "EMIT", source("facts"), 1, "bake_shutter_facts")
    bake_one(ATLAS, "AO", None, 24, "bake_shutter_ao")


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(EXPORT, MODEL)
    mats = os.path.join(EXPORT, MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["shutter_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in range(4):
        ob = bpy.data.objects[f"shutter_lod{lod}"]
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
        n0 = nn.reshape(-1, 3)[loops][:, [1, 2, 0]]
        e.to_mesh_clear()
        counts[lod] = n_tris
        for side, sign in (("l", 1.0), ("r", -1.0)):
            # OBJ's first axis is engine Y. Mirroring it turns the triangles inside out, so they wind the other way too.
            flip = np.array((sign, 1.0, 1.0))
            p, n = p0 * flip, n0 * flip
            tables = ({}, {}, {})
            lines = ([], [], [])
            faces = []
            for k in range(n_tris):
                tri = []
                for c in (range(3) if sign > 0 else (2, 1, 0)):
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
            with open(os.path.join(out, f"{NAME}_{side}_lod{lod}.obj"), "w", newline="\n") as h:
                h.write(f"# Generated by Sources/Ridgeback/shutter_v2/shutter.py\nmtllib {NAME}.mtl\n")
                for block in lines:
                    h.writelines(block)
                h.write(f"usemtl {NAME}\n")
                h.writelines(faces)
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")
    for side in ("l", "r"):
        meshes = ",\n".join(
            f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/{NAME}_{side}_lod{l}.obj" '
            'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
            'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
            "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
        )
        groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 25.0, 70.0, 160.0)))
        doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Ridgeback/shutter_v2/shutter.py
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
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
"""
        with open(os.path.join(out, f"{NAME}_{side}.vmdl"), "w", newline="\n") as h:
            h.write(doc)
    vmat = f"""// Generated by Sources/Ridgeback/shutter_v2/shutter.py

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
print("shutter stages done", flush=True)
