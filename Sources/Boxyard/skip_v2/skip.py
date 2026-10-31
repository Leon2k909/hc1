"""Boxyard's skip v2: build, bake and export. Uses the capture flag's mesh toolkit.

blender -b --factory-startup -t 4 --python skip.py -- <work dir> <project root> <build|bake|export> ...

The old skip is four flat slabs and a rim. This one is a chain-lift builder's skip as they're welded up: dented plate walls
with pressed ribs, a square rim that has taken a lot of knocks, corner posts, lifting trunnions on gussets, forged rings on
its raked ends, two runners, and a floor with some rubble left in it. Same 144 x 66 x 48 in body, and the old collision.
Inches, engine axes: +X along the skip, Y across, Z up, origin on the ground at its centre. Boxyard places it at engine
(675, 555, 0) turned -90 degrees, so its +X is the map's east.
Exported outside Assets until the user approves, because an open editor compiles whatever it finds there.
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

from build import Part, add, box, frame, lathe, prism, spline, tube  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, RUST, BRICK, CONCRETE, TIMBER = range(11)
NAME = "skip"
MODEL = "models/props/boxyard/skip_v2"
MATS = "materials/boxyard/skip_v2"
EXPORT = os.path.join(WORK, "skip_v2")  # Laid out like Assets, ready to copy in.
BLEND = os.path.join(WORK, "skip_build.blend")
ATLAS = 4096

TOP, BOTTOM, HW, H, FLOOR, WALL = 72.0, 54.0, 33.0, 48.0, 4.0, 1.5
RAKE = (TOP - BOTTOM) / (H - FLOOR)
ALONG_X = frame((0, 0, 0), (1, 0, 0), (0, 1, 0))  # Local x to +Y, local y to +Z, local z to +X.
rng = np.random.default_rng(4471)
welds = []  # Weld runs too fine to be worth triangles: painted from these, ((x, y, z), (x, y, z)).


def end_x(z):
    return BOTTOM + (z - FLOOR) * RAKE


def bx(finish, lod, lo, hi, bevel=0.06, name="", m=Matrix.Identity(4), segs=1, angle=40, texel=1.0):
    p = add(Part(finish, lod, bevel=bevel, segs=segs, angle=angle, name=name))
    box(p, lo, hi, m)
    p.texel = texel
    return p


def ribbon(part, path, w, h, up=(0, 0, 1)):
    """A square bar along a path."""
    bm = part.bm
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        s = t.cross(Vector(up)).normalized()
        u = s.cross(t).normalized()
        rings.append([bm.verts.new(p + s * sa * w / 2 + u * ua * h / 2) for sa, ua in ((-1, -1), (-1, 1), (1, 1), (1, -1))])
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(list(rings[-1]))


def ring_sweep(part, profile, sides, m=Matrix.Identity(4)):
    """A closed profile of (radius, z) spun about local Z, with no end caps: a tyre."""
    bm = part.bm
    rings = [[bm.verts.new(m @ Vector((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z))) for k in range(sides)] for r, z in profile]
    for i, a in enumerate(rings):
        b = rings[(i + 1) % len(rings)]
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))


def panel(finish, lod, corners, rows, cols, inward, dents=(), name="", texel=1.0):
    """A plate with thickness on four corners (bilinear), knocked in at each dent: (centre, radius, depth)."""
    part = add(Part(finish, lod, name=name))
    part.texel = texel
    bm = part.bm
    a, b, c, d = [Vector(p) for p in corners]
    normal = (b - a).cross(d - a).normalized()
    inward = Vector(inward)

    def point(i, j, offset):
        u, v = i / cols, j / rows
        p = (a * (1 - u) + b * u) * (1 - v) + (d * (1 - u) + c * u) * v
        knock = 0.0
        for centre, radius, depth in dents:
            knock += depth * math.exp(-(((p - Vector(centre)).length / radius) ** 2))
        return p - normal * knock + inward * offset

    outer = [[bm.verts.new(point(i, j, 0.0)) for i in range(cols + 1)] for j in range(rows + 1)]
    inner = [[bm.verts.new(point(i, j, 1.0)) for i in range(cols + 1)] for j in range(rows + 1)]
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((outer[j][i], outer[j][i + 1], outer[j + 1][i + 1], outer[j + 1][i]))
            bm.faces.new((inner[j][i], inner[j + 1][i], inner[j + 1][i + 1], inner[j][i + 1]))
    for i in range(cols):
        bm.faces.new((outer[0][i], inner[0][i], inner[0][i + 1], outer[0][i + 1]))
        bm.faces.new((outer[rows][i], outer[rows][i + 1], inner[rows][i + 1], inner[rows][i]))
    for j in range(rows):
        bm.faces.new((outer[j][0], outer[j + 1][0], inner[j + 1][0], inner[j][0]))
        bm.faces.new((outer[j][cols], inner[j][cols], inner[j + 1][cols], outer[j + 1][cols]))
    return part


def walls():
    z0, z1 = FLOOR - 0.3, H - 1.5
    side_dents = {
        1: [((-30, 33, 18), 11, 1.1), ((14, 33, 34), 8, 0.7), ((46, 33, 14), 7, 0.9), ((-6, 33, 10), 5, 0.5)],
        -1: [((22, -33, 22), 13, 1.3), ((-38, -33, 30), 9, 0.8), ((-12, -33, 13), 6, 0.6), ((52, -33, 34), 6, 0.6)],
    }
    for s in (-1, 1):
        y = s * HW
        corners = [(-end_x(z0) + 0.15, y, z0), (end_x(z0) - 0.15, y, z0), (end_x(z1) - 0.15, y, z1), (-end_x(z1) + 0.15, y, z1)]
        if s > 0:
            corners = [corners[1], corners[0], corners[3], corners[2]]
        panel(PAINT, 3, corners, 8, 26, (0, -s * WALL, 0), side_dents[s], "side wall")
    end_dents = {
        1: [((62, -14, 26), 8, 0.8), ((64, 16, 34), 6, 0.5)],
        -1: [((-60, 10, 20), 9, 0.9), ((-64, -18, 36), 6, 0.6)],
    }
    for sx in (-1, 1):
        y = HW - 0.15
        corners = [(sx * end_x(z0), -y, z0), (sx * end_x(z0), y, z0), (sx * end_x(z1), y, z1), (sx * end_x(z1), -y, z1)]
        if sx < 0:
            corners = [corners[1], corners[0], corners[3], corners[2]]
        panel(PAINT, 3, corners, 8, 14, (-sx * WALL, 0, 0), end_dents[sx], "end wall")
    floor_dents = [((14, 8, 4), 12, -0.5), ((-26, -14, 4), 9, -0.4)]
    panel(PAINT, 3, [(-BOTTOM + 0.2, -HW + 0.2, FLOOR), (BOTTOM - 0.2, -HW + 0.2, FLOOR), (BOTTOM - 0.2, HW - 0.2, FLOOR), (-BOTTOM + 0.2, HW - 0.2, FLOOR)], 6, 10, (0, 0, -0.35), floor_dents, "floor", 0.8)


def rim_and_posts():
    # The square rim, knocked about along its length, with no real straight run left in it.
    for s in (-1, 1):
        path = []
        for x in np.linspace(-TOP, TOP, 15):
            edge = 1 - min(1.0, (TOP - abs(x)) / 8.0)
            path.append((x, s * HW + float(rng.uniform(-0.14, 0.14)) * (1 - edge), H - 1.56 + float(rng.uniform(-0.06, 0.06)) * (1 - edge)))
        p = add(Part(PAINT, 3, bevel=0.32, segs=2, angle=30, name="rim"))
        ribbon(p, path, 3.0, 2.88)
    for sx in (-1, 1):
        path = [(sx * (TOP - 1.5), y, H - 1.5) for y in np.linspace(-HW + 1.3, HW - 1.3, 7)]
        p = add(Part(PAINT, 3, bevel=0.32, segs=2, angle=30, name="rim"))
        ribbon(p, path, 3.0, 3.0)
        for s in (-1, 1):
            p = add(Part(PAINT, 3, bevel=0.14, angle=30, name="corner post"))
            ribbon(p, [(sx * (BOTTOM - 0.55), s * (HW - 0.1), FLOOR - 0.25), (sx * (end_x(H - 2.0) - 0.75), s * (HW - 0.1), H - 2.0)], 1.7, 1.7, up=(0, 1, 0))
    for s in (-1, 1):
        for sx in (-1, 1):
            welds.append(((sx * (BOTTOM - 0.3), s * (HW + 0.75), FLOOR), (sx * (end_x(H - 3) - 0.3), s * (HW + 0.75), H - 3)))


def ribs():
    # Pressed top-hat ribs welded up the sides and the raked ends.
    for s in (-1, 1):
        for x in (-46.0, -23.0, 0.0, 23.0, 46.0):
            outline = [(x - 2.1, s * HW - s * 0.05), (x + 2.1, s * HW - s * 0.05), (x + 1.25, s * (HW + 1.25)), (x - 1.25, s * (HW + 1.25))]
            if s < 0:
                outline.reverse()
            prism(add(Part(PAINT, 3, bevel=0.07, angle=30, name="rib")), outline, FLOOR + 0.7, H - 2.6)
            for dx in (-2.15, 2.15):
                welds.append(((x + dx, s * (HW + 0.05), FLOOR + 0.7), (x + dx, s * (HW + 0.05), H - 2.6)))
    length = math.hypot(TOP - BOTTOM, H - FLOOR)
    for sx in (-1, 1):
        d = Vector((sx * RAKE, 0, 1)).normalized()
        n = Vector((sx, 0, -RAKE)).normalized()
        for y in (-24.0, -9.0, 9.0, 24.0):
            at = Vector((sx * end_x(FLOOR + 1.2), y, FLOOR + 1.2))
            m = frame(at, d, Vector((0, 1, 0)))
            # Local y is (d x +Y); out of the face is along n, whichever way round that is.
            out = 1.0 if (d.cross(Vector((0, 1, 0)))).dot(n) > 0 else -1.0
            outline = [(-2.1, -out * 0.05), (2.1, -out * 0.05), (1.25, out * 1.25), (-1.25, out * 1.25)]
            if out < 0:
                outline.reverse()
            prism(add(Part(PAINT, 3, bevel=0.07, angle=30, name="rib")), outline, 0.0, length - 6.6, m)


def lifting_gear():
    for sx in (-1, 1):
        for s in (-1, 1):
            x = sx * 56.0
            a, b = sorted((s * (HW - 0.05), s * (HW + 0.5)))
            bx(PAINT, 2, (x - 5.2, a, 34.6), (x + 5.2, b, 45.2), 0.06, "lug plate", angle=30)
            for dx in (-2.3, 2.3):
                outline = [(s * (HW + 0.45), 35.2), (s * (HW + 3.0), 40.0), (s * (HW + 3.0), 42.6), (s * (HW + 0.45), 45.0)]
                if s < 0:
                    outline.reverse()
                prism(add(Part(PAINT, 2, bevel=0.05, angle=30, name="gusset")), outline, x + dx - 0.28, x + dx + 0.28, ALONG_X)
            m = frame((x, s * (HW + 0.5), 41.2), (0, s, 0))
            lathe(add(Part(OXIDE, 3, bevel=0.0, name="trunnion")), [(1.55, 0.0), (1.55, 2.95), (2.15, 2.95), (2.15, 3.4), (1.8, 3.58), (0, 3.6)], 14, m)
            welds.append(((x - 5.2, s * (HW + 0.5), 34.6), (x + 5.2, s * (HW + 0.5), 34.6)))
            welds.append(((x - 5.2, s * (HW + 0.5), 45.2), (x + 5.2, s * (HW + 0.5), 45.2)))
        # A forged ring on each raked end, hanging in a welded lug.
        z = 15.0
        n = Vector((sx, 0, -RAKE)).normalized()
        d = Vector((sx * RAKE, 0, 1)).normalized()
        at = Vector((sx * end_x(z), 0, z))
        m = frame(at + n * 0.1, n, Vector((0, 1, 0)))
        bx(OXIDE, 2, (-2.6, -2.1, -0.1), (2.6, 2.1, 0.5), 0.1, "ring lug", m)
        bx(OXIDE, 2, (-0.9, -0.55, 0.45), (0.9, 0.55, 1.5), 0.12, "ring eye", m)
        centre = at + n * 1.2 - d * 2.3
        ring = [centre + Vector((0, 2.2 * math.cos(t), 0)) + d * (2.6 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 18, endpoint=False)]
        tube(add(Part(OXIDE, 2, name="forged ring")), ring, 0.52, 7, closed=True)


def base():
    # Two runners with their toes turned up, and cross members under the floor.
    for y in (-22.0, 22.0):
        outline = [(-48.0, 0.0), (48.0, 0.0), (51.0, 3.7), (-51.0, 3.7)]
        m = frame((0, y, 0), (0, 1, 0), (0, 0, 1))
        # Local x along Z, local y along X: swap the outline so it lies in (Z, X) and faces out.
        prism(add(Part(OXIDE, 3, bevel=0.12, angle=30, name="runner")), [(z, x) for x, z in reversed(outline)], -3.0, 3.0, m)
    for x in (-40.0, -13.0, 13.0, 40.0):
        bx(OXIDE, 2, (x - 1.2, -19.0, 1.2), (x + 1.2, 19.0, 3.65), 0.08, "cross member", texel=0.4)


def rubble():
    # What's left in it after the last load: never more than a few inches deep, as the floor is still what you stand on.
    for _ in range(18):
        x, y = float(rng.uniform(-6, 50)), float(rng.uniform(-27, 27))
        yaw_, tip = float(rng.uniform(0, math.pi)), float(rng.uniform(-0.35, 0.35))
        m = Matrix.Translation((x, y, FLOOR + 1.6 + abs(tip) * 3.0 + rng.uniform(0, 1.2))) @ Matrix.Rotation(yaw_, 4, "Z") @ Matrix.Rotation(tip, 4, "X")
        size = rng.uniform(0.86, 1.0)
        bx(BRICK, 1, (-4.2 * size, -2.0, -1.3), (4.2 * size, 2.0, 1.3), 0.09, "brick", m, texel=0.6)
    for _ in range(8):
        x, y = float(rng.uniform(-14, 50)), float(rng.uniform(-26, 26))
        r = float(rng.uniform(2.6, 5.0))
        p = add(Part(CONCRETE, 1, name="concrete lump"))
        p.texel = 0.6
        bmesh.ops.create_icosphere(p.bm, subdivisions=2, radius=r)
        for v in p.bm.verts:
            v.co *= 0.72 + 0.56 * float(rng.uniform(0, 1))
            v.co.z *= 0.62
            v.co += Vector((x, y, FLOOR + r * 0.4))
    for x, y, length, yaw_, tip in ((-34.0, 14.0, 44.0, 0.2, 0.05), (-22.0, -17.0, 38.0, -0.5, 0.08), (-8.0, 4.0, 30.0, 1.1, 0.12), (-38.0, -6.0, 26.0, 2.5, 0.04)):
        m = Matrix.Translation((x, y, FLOOR + 1.3 + length * tip * 0.5)) @ Matrix.Rotation(yaw_, 4, "Z") @ Matrix.Rotation(tip, 4, "Y")
        bx(TIMBER, 1, (-length / 2, -2.4, -0.45), (length / 2, 2.4, 0.45), 0.05, "plank", m, texel=0.6)
    for x, y, yaw_ in ((8.0, 15.0, 0.6), (30.0, -20.0, 2.2)):
        turn = Matrix.Rotation(yaw_, 4, "Z")
        pts = [Vector((-13.0, 0, 7.0)), Vector((-7.0, 0.6, 6.4)), Vector((1.0, -0.4, 5.8)), Vector((8.0, 0.5, 8.0)), Vector((12.0, 0.2, 13.0))]
        tube(add(Part(RUST, 1, name="rebar")), [turn @ p + Vector((x, y, 0)) for p in spline(pts, 2)], 0.3, 5)
    # A dead car tyre, lying on the rest.
    m = Matrix.Translation((-24.0, -6.0, FLOOR + 3.6)) @ Matrix.Rotation(0.12, 4, "X")
    tyre = [(7.2, -2.8), (9.6, -3.2), (11.4, -2.6), (12.0, -1.2), (12.0, 1.2), (11.4, 2.6), (9.6, 3.2), (7.2, 2.8)]
    p = add(Part(RUBBER, 1, name="old tyre"))
    ring_sweep(p, tyre, 20, m)
    p.texel = 0.7


def geometry():
    walls()
    rim_and_posts()
    ribs()
    lifting_gear()
    base()
    rubble()


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
    """Real-scale islands, skyline packed, weighted face by face: the outside gets the most, what nobody sees the least."""
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
        if tree.ray_cast(c + f.normal * 0.012, f.normal, 0.6)[0] is not None:
            texel = min(texel, 0.2)
        elif f.normal.z < -0.75 and c.z < 5:
            texel = min(texel, 0.25)
        elif FLOOR + 0.1 < c.z < H - 2 and abs(c.y) < HW and abs(c.x) < end_x(c.z) and f.normal.x * c.x + f.normal.y * c.y < 0 and abs(f.normal.z) < 0.7:
            texel = min(texel, 0.7)  # The inside faces: seen from above, but mostly in shade.
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
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        pts = tris.reshape(-1, 2)
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
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

    lo, hi = 2.0, 60.0
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
        p.rand = (float(order[i]) + 0.5) / count  # Unique per part: the LODs look parts up by it.
    print("parts", count, flush=True)
    hw = kit.join_parts(kit.parts, "skip_lod0")
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

    lod("skip_lod1", 1, 0.6)
    lod("skip_lod2", 2, 0.4)
    lod("skip_lod3", 3, 0.25)
    with open(os.path.join(WORK, "skip.json"), "w") as h:
        json.dump(dict(density=density, welds=welds), h)
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
    hw = bpy.data.objects["skip_lod0"]
    for ob in scene.objects:
        ob.hide_render = ob is not hw
    world = bpy.data.worlds.new("bake")
    scene.world = world
    world.light_settings.distance = 14.0
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

    bake_one(ATLAS, "EMIT", source("pos"), 1, "bake_skip_pos")
    bake_one(ATLAS, "EMIT", source("nor"), 1, "bake_skip_nor")
    bake_one(ATLAS, "EMIT", source("facts"), 1, "bake_skip_facts")
    bake_one(2048, "AO", None, 24, "bake_skip_ao")


def old_collision_hulls():
    """The old skip's four wall hulls, from the same numbers the map script gives them, in this model's frame."""
    hulls = []
    for sigma in (-1, 1):
        pts = [(-BOTTOM, sigma * HW, FLOOR), (BOTTOM, sigma * HW, FLOOR), (TOP, sigma * HW, H), (-TOP, sigma * HW, H)]
        hulls.append([(p[0], p[1] - sigma * t, p[2]) for p in pts for t in (0.0, WALL)])
    for sx in (-1, 1):
        pts = [(sx * BOTTOM, -HW, FLOOR), (sx * BOTTOM, HW, FLOOR), (sx * TOP, HW, H), (sx * TOP, -HW, H)]
        hulls.append([(p[0] - sx * t, p[1], p[2]) for p in pts for t in (0.0, WALL)])
    return hulls


def write_hulls(path):
    with open(path, "w", newline="\n") as h:
        h.write("# Sources/Boxyard/skip_v2/skip.py: the old skip's collision hulls\no skip_hulls_metal\n")
        base_index = 1
        for hull in old_collision_hulls():
            v = np.array(hull, float)
            centre = v.mean(0)
            for x, y, z in hull:
                h.write(f"v {y:.3f} {z:.3f} {x:.3f}\n")
            # Corners go (0: edge A, 1: its offset) round the plate: 0, 2, 4, 6 on the outer face, 1, 3, 5, 7 on the inner.
            quads = [(0, 2, 4, 6), (7, 5, 3, 1), (0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6), (6, 7, 1, 0)]
            for q in quads:
                a, b, c = v[q[0]], v[q[1]], v[q[2]]
                normal = np.cross(b - a, c - a)
                order = q if normal.dot((a + b + c) / 3 - centre) > 0 else tuple(reversed(q))
                # OBJ axes are (Y, Z, X), a rotation, so winding carries over.
                h.write("f " + " ".join(str(base_index + i) for i in order) + "\n")
            base_index += 8


PHYSICS = """{
				_class = "PhysicsShapeList"
				children =
				[
					{
						_class = "PhysicsShapeBox"
						parent_bone = ""
						surface_prop = "metal"
						collision_tags = "solid"
						origin = [ 0.0000, 0.0000, 2.0000 ]
						angles = [ 0.0000, 0.0000, 0.0000 ]
						dimensions = [ 108.0000, 66.0000, 4.0000 ]
					},
					{
						_class = "PhysicsHullFile"
						name = "skip_hulls_metal"
						parent_bone = ""
						surface_prop = "metal"
						collision_tags = "solid"
						recenter_on_parent_bone = false
						offset_origin = [ 0.0, 0.0, 0.0 ]
						offset_angles = [ 0.0, 0.0, 0.0 ]
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						filename = "%s/skip_hulls_metal.obj"
						import_scale = 1.0
						faceMergeAngle = 10.0
						maxHullVertices = 0
					},
				]
			}""" % MODEL


def export_stage():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    out = os.path.join(EXPORT, MODEL)
    mats = os.path.join(EXPORT, MATS)
    os.makedirs(out, exist_ok=True)
    os.makedirs(mats, exist_ok=True)
    if uv_hash(bpy.data.objects["skip_lod0"]) != open(os.path.join(WORK, "baked_uv_hash.txt")).read().strip():
        raise SystemExit("The build's UVs are not the ones the textures were baked on.")
    counts = {}
    for lod in range(4):
        ob = bpy.data.objects[f"skip_lod{lod}"]
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
            h.write(f"# Generated by Sources/Boxyard/skip_v2/skip.py\nmtllib {NAME}.mtl\n")
            for block in lines:
                h.writelines(block)
            h.write(f"usemtl {NAME}\n")
            h.writelines(faces)
        counts[lod] = n_tris
        print("lod", lod, "tris", n_tris, flush=True)
    with open(os.path.join(out, f"{NAME}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {NAME}\nKd 1 1 1\nd 1\n")
    write_hulls(os.path.join(out, "skip_hulls_metal.obj"))
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL}/{NAME}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } }" for l in counts
    )
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}' for l, t in zip(counts, (0.0, 15.0, 40.0, 90.0)))
    doc = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Boxyard/skip_v2/skip.py
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
			{PHYSICS},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
"""
    with open(os.path.join(out, f"{NAME}.vmdl"), "w", newline="\n") as h:
        h.write(doc)
    vmat = f"""// Generated by Sources/Boxyard/skip_v2/skip.py

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
print("skip stages done", flush=True)
