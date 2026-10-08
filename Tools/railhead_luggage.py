"""Railhead's reusable, reference-matched railway luggage trolley.

Run this file to rebuild the prop and its two atlased materials. The colour atlas
is an ImageGen source asset; its prompt is in railhead_luggage_imagegen.json.
All sizes below are inches. The cart's long axis is local Y, with its drawbar at
+Y. The map uses four instances instead of baking four copies into the station.
"""

from contextlib import contextmanager
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import map_kit as K
import railhead_props as P
from railhead_buffer import bevel_box


RESOURCE = "models/props/railhead/luggage"
OUT = K.ASSETS / RESOURCE
MODEL = f"{RESOURCE}/luggage_trolley.vmdl"
TEX = "materials/railhead/luggage"
MATERIALS = K.ASSETS / TEX
BODY, INK = "rw_luggage_body", "rw_luggage_markings"
F = P.Frame((0, 0, 0), (0, 1))
DECK, HALF_W, HALF_L = 24.0, 23.6, 49.2
# (key, east, north, forward). These keep the previous map's placements.
PLACEMENTS = (
    ("east/concourse", 600.0, 950.0, "e"),
    ("west/concourse", -600.0, 950.0, "e"),
    ("east/platform", 632.0, -1250.0, "n"),
    ("west/platform", -632.0, -1250.0, "n"),
)
WOOD, DARK_WOOD, GREEN, STEEL, BLUE, RED, BLACK, GREY = range(8)
CANVAS, RUBBER, WEBBING, HARDWARE, RUST, ALUMINIUM, OLIVE_STRAP, EDGE = range(8, 16)
MARK_RECTS = {
    "db": (16, 16, 240, 208),
    "number": (272, 16, 688, 208),
    "weight": (720, 16, 2032, 208),
    "fragile": (16, 256, 408, 632),
    "shipping": (448, 256, 848, 448),
    "reflector": (880, 256, 1192, 432),
    "case_label": (1232, 256, 1616, 448),
}


def unit(v):
    v = np.asarray(v, float)
    return v / max(1e-9, np.linalg.norm(v))


def local(p):
    return np.asarray((np.dot(p, F.x), np.dot(p, F.y), np.dot(p, F.z)), float)


def atlas_uv(cell, coords):
    # Eight texels of gutters on each side keep mip-filtering out of neighbouring
    # materials. V is up in OBJ but down in the source bitmap.
    col, row = int(cell) % 4, int(cell) // 4
    gutter = 8 / 1254
    return [((col / 4 + gutter) + np.clip(u, 0, 1) * (.25 - 2 * gutter),
             1 - ((row + 1) / 4 - gutter) + np.clip(v, 0, 1) * (.25 - 2 * gutter))
            for u, v in coords]


class AtlasModel(K.Model):
    """One material draw for all solids, with UVs attached to individual parts."""

    def __init__(self):
        super().__init__()
        self.bounds = None
        self.material_overrides.update({BODY: f"{TEX}/{BODY}.vmat", INK: f"{TEX}/{INK}.vmat"})
        self.tile_overrides.update({BODY: 1, INK: 1})

    @contextmanager
    def part(self, lo, hi):
        previous = self.bounds
        self.bounds = (np.asarray(lo, float), np.asarray(hi, float))
        try:
            yield
        finally:
            self.bounds = previous

    def polygon(self, paint, points, normal=None, both_sides=False, uv=None, normals=None):
        if isinstance(paint, (int, np.integer)):
            if uv is None:
                pts = np.asarray([local(p) for p in points])
                n = local(normal) if normal is not None else np.cross(pts[1] - pts[0], pts[2] - pts[0])
                remaining = [i for i in range(3) if i != int(np.argmax(np.abs(n)))]
                lo, hi = self.bounds if self.bounds is not None else (pts.min(axis=0), pts.max(axis=0))
                # Horizontal timber grain follows the longest horizontal edge.
                if paint in (WOOD, DARK_WOOD):
                    a = max(remaining, key=lambda i: (i != 2, hi[i] - lo[i]))
                    b = next(i for i in remaining if i != a)
                else:
                    b = 2 if 2 in remaining else remaining[1]
                    a = next(i for i in remaining if i != b)
                # Preserve the texture's aspect ratio. Stretching a square
                # swatch over a long, thin rail turned paint chips into stripes.
                # A different crop per part avoids repeated timber knots.
                span = max(.01, hi[a] - lo[a], hi[b] - lo[b])
                widths = ((hi[a] - lo[a]) / span, (hi[b] - lo[b]) / span)
                phase = abs(math.sin(float(np.dot(lo, (.731, .391, 1.117))) + paint * .37))
                offsets = ((1 - widths[0]) * phase, (1 - widths[1]) * (1 - phase))
                uv = [((p[a] - lo[a]) / span + offsets[0],
                       (p[b] - lo[b]) / span + offsets[1]) for p in pts]
            uv = atlas_uv(paint, uv)
            paint = BODY
        return super().polygon(paint, points, normal, both_sides, uv, normals)


def box(m, lo, hi, paint, bevel=.12, collision=None):
    with m.part(lo, hi):
        if min(np.asarray(hi) - np.asarray(lo)) < .3:
            # Thin folded sheet, straps and individual board veneers have crisp
            # edges. Bevels here would be invisible subpixel strips.
            F.box(m, *[v for pair in zip(lo, hi) for v in pair], paint)
        else:
            bevel_box(m, F, lo, hi, paint, bevel)
    if collision:
        F.collide(m, *[v for pair in zip(lo, hi) for v in pair], collision)


def quad(m, paint, centre, right, up, width, height, coords=None):
    c = F.p(*centre)
    r, u = unit(F.x * right[0] + F.y * right[1] + F.z * right[2]), unit(F.x * up[0] + F.y * up[1] + F.z * up[2])
    P.quad(m, paint, c, r, u, width, height, uv=coords)


def mark(m, name, centre, width, height, facing="left"):
    x0, y0, x1, y1 = MARK_RECTS[name]
    uv = [(x0 / 2048, 1 - y1 / 1024), (x1 / 2048, 1 - y1 / 1024),
          (x1 / 2048, 1 - y0 / 1024), (x0 / 2048, 1 - y0 / 1024)]
    F.quad(m, INK, *centre, width, height, facing, uv)


def tube(m, points, radius, paint, sides=12, caps=True):
    """Continuous round tube, with transported rings and smooth vertex normals."""
    points = np.asarray(points, float)
    tangent = [unit(points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]) for i in range(len(points))]
    axis = np.eye(3)[int(np.argmin(np.abs(tangent[0])))]
    v = unit(np.cross(tangent[0], axis))
    rings, norms = [], []
    length = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    for p, t in zip(points, tangent):
        v = unit(v - t * np.dot(v, t))
        w = np.cross(t, v)
        ns = [math.cos(a * math.tau / sides) * v + math.sin(a * math.tau / sides) * w for a in range(sides)]
        rings.append([F.p(*(p + radius * n)) for n in ns])
        norms.append([F.x * n[0] + F.y * n[1] + F.z * n[2] for n in ns])
    for j in range(len(points) - 1):
        v0, v1 = length[j] / max(.01, length[-1]), length[j + 1] / max(.01, length[-1])
        for a in range(sides):
            b = (a + 1) % sides
            pts = [rings[j][a], rings[j][b], rings[j + 1][b], rings[j + 1][a]]
            ns = [norms[j][a], norms[j][b], norms[j + 1][b], norms[j + 1][a]]
            P.outward(m, paint, pts, sum(ns), uv=[(a / sides, v0), ((a + 1) / sides, v0),
                                               ((a + 1) / sides, v1), (a / sides, v1)], normals=ns)
    if caps:
        for j, sign in ((0, -1), (-1, 1)):
            with m.part(points[j] - radius, points[j] + radius):
                P.outward(m, paint, rings[j], F.x * tangent[j][0] * sign + F.y * tangent[j][1] * sign + F.z * tangent[j][2] * sign)


def cylinder(m, centre, axis, radius, length, paint, sides=16):
    c, a = np.asarray(centre, float), unit(axis)
    tube(m, [c - a * length / 2, c + a * length / 2], radius, paint, sides)


def beam_collision(m, a, b, width=1.48):
    a, b = F.p(*a), F.p(*b)
    along = unit(b - a)
    across = unit(np.cross((0, 0, 1), along))
    up = np.cross(along, across)
    m.boxes.append(((a + b) / 2, [along, across, up], (float(np.linalg.norm(b - a)), width, width), "metal"))


def screw(m, centre, normal=(0, 0, 1), radius=.22, hexagon=False):
    c, n = np.asarray(centre, float), unit(normal)
    # Small screws are bevelled eight-sided heads: at this scale the texture and
    # silhouette carry the detail. Three nested cylinders wasted most of the
    # original prototype's triangles on hardware only a few pixels across.
    a = unit(np.cross(n, np.eye(3)[np.argmin(np.abs(n))]))
    b = np.cross(n, a)
    rings = []
    count = 6 if hexagon else 8
    profile = ((.025, radius), (.18, radius * .84)) if radius < .2 else ((.025, radius * 1.25), (.14, radius), (.18, radius * .84))
    for depth, r in profile:
        rings.append([F.p(*(c + n * depth + (a * math.cos(t * math.tau / count) + b * math.sin(t * math.tau / count)) * r)) for t in range(count)])
    with m.part(c - radius, c + radius):
        for j in range(len(rings) - 1):
            for t in range(count):
                q = (t + 1) % count
                P.outward(m, HARDWARE if hexagon else STEEL, [rings[j][t], rings[j][q], rings[j + 1][q], rings[j + 1][t]],
                          F.x * n[0] + F.y * n[1] + F.z * n[2])
        P.outward(m, HARDWARE if hexagon else STEEL, rings[-1], F.x * n[0] + F.y * n[1] + F.z * n[2])
    if not hexagon:
        quad(m, HARDWARE, c + n * .185, a, b, radius * 1.35, .055,
             coords=[(.35, .5), (.65, .5), (.65, .53), (.35, .53)])


def rounded_loop(m, centre, width, height, radius, paint=HARDWARE, facing="left", tube_radius=.18):
    """A bent metal carrying handle, standing clear of its recessed mounting plate."""
    c = np.asarray(centre, float)
    right = np.array((0, 1, 0)) if facing == "left" else np.array((1, 0, 0))
    up = np.array((0, 0, 1))
    if facing == "top":
        right, up = np.array((0, 1, 0)), np.array((1, 0, 0))
    path = []
    for sx, sy, angle in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        origin = c + right * sx * (width / 2 - radius) + up * sy * (height / 2 - radius)
        for k in range(5):
            a = math.radians(angle + k * 90 / 4)
            path.append(origin + right * math.cos(a) * radius + up * math.sin(a) * radius)
    path.append(path[0])
    tube(m, path, tube_radius, paint, 8)


def lathe(m, centre, axis, profile, paint, sides=48):
    """Wheel rings with a properly dished profile, rather than flat faceted discs."""
    centre, axis = np.asarray(centre, float), unit(axis)
    r = unit(np.cross(axis, (0, 0, 1)))
    u = np.cross(axis, r)
    for j in range(len(profile) - 1):
        for i in range(sides):
            verts, ns, uv = [], [], []
            for k, a in ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)):
                t, rad = profile[k]
                ring = math.cos(a * math.tau / sides) * r + math.sin(a * math.tau / sides) * u
                p = centre + axis * t + ring * rad
                before, after = profile[max(k - 1, 0)], profile[min(k + 1, len(profile) - 1)]
                dt, dr = after[0] - before[0], after[1] - before[1]
                n = unit(ring * dt - axis * dr)
                verts.append(F.p(*p))
                ns.append(F.x * n[0] + F.y * n[1] + F.z * n[2])
                # Radial mapping across each complete wheel keeps tyre texture
                # small and follows its circumference without an atlas seam.
                uv.append((.5 + math.cos(a * math.tau / sides) * rad / 17,
                           .5 + math.sin(a * math.tau / sides) * rad / 17))
            P.outward(m, paint, verts, sum(ns), uv=uv, normals=ns)


def wheel(m, x, y):
    side = 1 if x > 0 else -1
    axis = (side, 0, 0)
    c = np.array((x, y, 8.05))
    lathe(m, c, axis, [(-1.8, 5.9), (-1.8, 7), (-1.4, 7.75), (-.85, 8.05),
                       (.85, 8.05), (1.4, 7.75), (1.8, 7), (1.8, 5.9)], RUBBER)
    lathe(m, c, axis, [(1.83, 5.95), (2.03, 5.95), (2.14, 5.6), (2.02, 5.35),
                       (1.35, 4.8), (1.23, 2.3), (1.56, 1.85)], GREEN)
    # Raised sidewall rings and a narrow rim lip, both true circular geometry.
    for rad, paint, t, thick in ((7.15, RUBBER, 1.78, .065), (6.42, RUBBER, 1.83, .05),
                                 (5.7, STEEL, 2.15, .055)):
        path = [c + np.array(axis) * t + np.array((0, math.cos(a * math.tau / 48) * rad, math.sin(a * math.tau / 48) * rad)) for a in range(49)]
        tube(m, path, thick, paint, 4, caps=False)
    cylinder(m, c + np.array(axis) * 1.8, axis, 1.88, .8, GREEN, 20)
    cylinder(m, c + np.array(axis) * 2.27, axis, .9, .25, HARDWARE, 16)
    cylinder(m, c + np.array(axis) * 2.47, axis, .61, .19, HARDWARE, 6)
    for a in np.linspace(0, math.tau, 6, endpoint=False):
        screw(m, c + np.array(axis) * 1.5 + np.array((0, math.cos(a) * 3.25, math.sin(a) * 3.25)), axis, .26, True)
    # Fine tread grooves follow the tyre's curved shoulder. They are recessed
    # strips, not deep notches that would turn its silhouette into a gear.
    for a in range(48):
        theta = (a + .5) * math.tau / 48
        verts = []
        for t, rad in ((-1.25, 7.85), (-.75, 8.065), (.75, 8.065), (1.25, 7.85)):
            verts.append([F.p(*(c + np.array(axis) * t + np.array((0, math.cos(theta + t * .028 + d) * rad,
                                                                   math.sin(theta + t * .028 + d) * rad)))) for d in (-.0035, .0035)])
        for j in range(3):
            P.outward(m, EDGE, [verts[j][0], verts[j][1], verts[j + 1][1], verts[j + 1][0]],
                      F.y * math.cos(theta) + F.z * math.sin(theta), uv=[(.25, .4), (.75, .4), (.75, .6), (.25, .6)])
    # A simple convex tyre collision is much cheaper than the detailed mesh.
    pts = [F.p(*(c + np.array(axis) * t + np.array((0, math.cos(a) * 8.05, math.sin(a) * 8.05))))
           for t in (-1.8, 1.8) for a in np.linspace(0, math.tau, 16, endpoint=False)]
    m.hull(pts, "rubber")


def end_gate(m, y):
    # A single bent tube makes rounded end-gate corners and continuous highlights.
    x, z, radius = HALF_W - 1, 43.4, 2.6
    points = [(-x, y, DECK - 1), (-x, y, z - radius)]
    for a in np.linspace(math.pi, math.pi / 2, 7):
        points.append((-x + radius + radius * math.cos(a), y, z - radius + radius * math.sin(a)))
    for a in np.linspace(math.pi / 2, 0, 7):
        points.append((x - radius + radius * math.cos(a), y, z - radius + radius * math.sin(a)))
    points.append((x, y, DECK - 1))
    tube(m, points, .9, GREEN, 12)
    tube(m, [(-x, y, 32.5), (x, y, 32.5)], .65, GREEN, 12)
    for xx in (-x, x):
        box(m, (xx - 1.75, y - 1.65, 20.4), (xx + 1.75, y + 1.65, 27.3), GREEN, .12)
        for dz in (21.8, 25.8):
            screw(m, (xx, y - 1.67, dz), (0, -1, 0), .32, True)
        F.collide(m, xx - .9, xx + .9, y - .9, y + .9, DECK - 1, z, "metal")
    for zz, r in ((32.5, .65), (43.4, .9)):
        F.collide(m, -x, x, y - r, y + r, zz - r, zz + r, "metal")


def chassis(m):
    # Perimeter channels, cross members and individual boards, all with real bevels.
    for x in (-HALF_W, HALF_W):
        box(m, (x - .55, -HALF_L, 18.9), (x + .55, HALF_L, 22.9), GREEN, .14)
        box(m, (x - 1, -HALF_L, 22.6), (x + 1, HALF_L, 23.35), GREEN, .12)
    for y in (-HALF_L, HALF_L, -34, -8, 18, 34):
        box(m, (-HALF_W, y - .8, 19.3), (HALF_W, y + .8, 22.75), GREEN, .12)
    # Grain runs along the short planks, matching the railway platform trolley.
    for i in range(12):
        y0 = -HALF_L + i * (HALF_L * 2 / 12)
        box(m, (-HALF_W + .5, y0 + .055, 22.65), (HALF_W - .5, y0 + HALF_L * 2 / 12 - .055, DECK),
            WOOD if i % 4 else DARK_WOOD, .095)
        for x in (-HALF_W + 2, HALF_W - 2):
            screw(m, (x, y0 + 1.55, DECK + .01), radius=.19)
    F.collide(m, -HALF_W - .55, HALF_W + .55, -HALF_L, HALF_L, 18.9, DECK, "wood")
    for y in (-37, 33):
        cylinder(m, (0, y, 8.05), (1, 0, 0), 1.12, 42.8, HARDWARE)
        # Axle hangers and leaf-spring packs below the timber deck.
        for x in (-16.5, 16.5):
            box(m, (x - 1.2, y - 2, 9.8), (x + 1.2, y + 2, 19.5), GREEN, .15)
            for dz in range(3):
                path = [(x, y + q, 14 + dz * .32 + (abs(q) / 13) ** 2 * 2.2) for q in np.linspace(-13, 13, 9)]
                tube(m, path, .23, HARDWARE, 6)
        for x in (-19.8, 19.8):
            wheel(m, x, y)
    cylinder(m, (0, 33, 18), (0, 0, 1), 6.4, .8, HARDWARE, 32)
    # Forked pivoting towbar, closed towing eye, and welded mounting ears.
    for x in (-5, 5):
        box(m, (x - .9, 38.5, 13), (x + .9, 41.8, 18.7), GREEN, .12)
        screw(m, (x, 40.1, 18.8), radius=.55, hexagon=True)
        path = [(x, 40, 15.1), (x * .6, 58, 9.5), (x * .34, 73, 7.2)]
        tube(m, path, .74, GREEN, 12)
        for a, b in zip(path, path[1:]):
            beam_collision(m, a, b)
    eye = [(math.cos(a) * 2.2, 76 + math.sin(a) * 3.2, 7.1) for a in np.linspace(0, math.tau, 33)]
    tube(m, eye, .65, GREEN, 10, caps=False)
    tube(m, [(-2, 70, 7.4), (2, 70, 7.4)], .6, GREEN, 10)
    for y in (-HALF_L + 1, HALF_L - 1):
        end_gate(m, y)
    for side in (-1, 1):
        # Enamel chassis stencils and amber reflectors sit on the frame, not on
        # opaque rectangular label cards.
        face = "left" if side < 0 else "right"
        x = side * (HALF_W + .57)
        mark(m, "db", (x, -35, 20.9), 4.2, 3.2, face)
        mark(m, "number", (x, -24, 20.9), 8.2, 2.65, face)
        mark(m, "weight", (x, 25, 20.75), 23.2, 1.85, face)
        for y in (-44, 44):
            box(m, (x - .1, y - 2.1, 19.5), (x + .1, y + 2.1, 22.1), HARDWARE, .06)
            mark(m, "reflector", (x + side * .115, y, 20.8), 3.9, 2.3, face)
    # Plate overlaps, rivets and edge wear make the frame a fabricated assembly.
    for x in (-HALF_W - .65, HALF_W + .65):
        for y in (-HALF_L + 2, HALF_L - 2):
            box(m, (x - .11, y - 1.75, 18.4), (x + .11, y + 1.75, 23.1), GREEN, .1)
            for dz in (19.3, 22.2):
                screw(m, (x + math.copysign(.12, x), y, dz), (math.copysign(1, x), 0, 0), .27, True)


def corner_guard(m, lo, hi, cx, cy, cz, size=1.6, paint=ALUMINIUM):
    # Three thin folded metal faces protect each corner. Bevels stop their edges
    # looking like white toy blocks, as in the old mesh.
    sx, sy, sz = cx, cy, cz
    c = np.where(np.array((sx, sy, sz)) < 0, lo, hi)
    for axis in range(3):
        a, b = c.copy(), c.copy()
        for i, sign in enumerate((sx, sy, sz)):
            if i == axis:
                a[i], b[i] = c[i] - .09, c[i] + .09
            else:
                a[i], b[i] = sorted((c[i], c[i] - sign * size))
        box(m, a, b, paint, .07)
    for axis in (0, 1):
        q = c.copy()
        for i, sign in enumerate((sx, sy, sz)):
            q[i] += sign * .11 if i == axis else -sign * size * .57
        n = np.eye(3)[axis] * (sx if axis == 0 else sy)
        screw(m, q, n, .16)


def recessed_handle(m, x, y, z, width=4.1, height=2.6, paint=HARDWARE, facing="left"):
    if facing != "left":
        # Reuse the actual recessed hardware on the other sides, with the same
        # attached UVs and normals. No blank crate faces when viewed from behind.
        source = AtlasModel()
        recessed_handle(source, 0, 0, 0, width, height, paint)
        normal = np.array({"right": (1, 0, 0), "front": (0, 1, 0), "back": (0, -1, 0)}[facing], float)
        axes = (-normal, -np.cross((0, 0, 1), normal), np.array((0, 0, 1)))
        def vector(v):
            return sum(a * q for a, q in zip(axes, local(v)))
        for material, polys in source.polygons.items():
            for i, (pts, n) in enumerate(polys):
                ns = source.polygon_normals.get((material, i))
                v = vector(n)
                m.polygon(material, [F.p(*(np.array((x, y, z)) + vector(p))) for p in pts],
                          F.x * v[0] + F.y * v[1] + F.z * v[2],
                          uv=source.polygon_uvs[(material, i)],
                          normals=[F.x * v[0] + F.y * v[1] + F.z * v[2] for v in map(vector, ns)] if ns else None)
        return
    box(m, (x - .08, y - width / 2, z - height / 2), (x + .08, y + width / 2, z + height / 2), paint, .12)
    box(m, (x - .14, y - width * .38, z - height * .34), (x - .09, y + width * .38, z + height * .34), EDGE, .08)
    rounded_loop(m, (x - .4, y, z - .07), width * .8, height * .58, .25, STEEL, tube_radius=.15)
    for dy in (-width * .43, width * .43):
        screw(m, (x - .105, y + dy, z), (-1, 0, 0), .15)


def crate(m, lo, hi, seed):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    # Board joints expose a narrow dark recess. No large reinforcing battens
    # obscure the broad planked faces in the reference.
    box(m, lo + .14, hi - .14, DARK_WOOD, .08)
    height = hi[2] - lo[2]
    rows = 5
    for i in range(rows):
        z0, z1 = lo[2] + i * height / rows + .055, lo[2] + (i + 1) * height / rows - .055
        for axis in (0, 1):
            for side in (-1, 1):
                a, b = lo.copy(), hi.copy()
                a[2], b[2] = z0, z1
                a[axis], b[axis] = (lo[axis] - .015, lo[axis] + .2) if side < 0 else (hi[axis] - .2, hi[axis] + .015)
                box(m, a, b, WOOD if (i + seed) % 5 else DARK_WOOD, .05)
    for i in range(4):
        a, b = lo.copy(), hi.copy()
        a[0] = lo[0] + i * (hi[0] - lo[0]) / 4 + .04
        b[0] = lo[0] + (i + 1) * (hi[0] - lo[0]) / 4 - .04
        a[2], b[2] = hi[2] - .22, hi[2] + .04
        box(m, a, b, WOOD if i % 4 else DARK_WOOD, .045)
    # Narrow end grain lips define the lid, with a dark separation underneath.
    for x in (lo[0], hi[0]):
        box(m, (x - .05, lo[1], hi[2] - 1.15), (x + .15, hi[1], hi[2] - .35), WOOD, .055)
    for cx in (-1, 1):
        for cy in (-1, 1):
            for cz in (-1, 1):
                corner_guard(m, lo - .04, hi + .04, cx, cy, cz, 1.9, HARDWARE)
    for y in (lo[1] + 4.5, hi[1] - 4.5):
        recessed_handle(m, lo[0] - .075, y, hi[2] - 6, 3.25, 2.25)
        recessed_handle(m, hi[0] + .075, y, hi[2] - 6, 3.25, 2.25, facing="right")
    for y, facing in ((lo[1] - .075, "back"), (hi[1] + .075, "front")):
        recessed_handle(m, (lo[0] + hi[0]) / 2, y, hi[2] - 6, 3.5, 2.25, facing=facing)
    # The black handling symbols are screen-printed directly onto timber.
    mark(m, "fragile", (lo[0] - .045, hi[1] - 4.9, lo[2] + 3.9), 6.4, 5.65)
    for y in np.linspace(lo[1] + 2.2, hi[1] - 2.2, 4):
        for z in (lo[2] + 1.15, hi[2] - 1.5):
            screw(m, (lo[0] - .04, y, z), (-1, 0, 0), .10)
    F.collide(m, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], "wood")


def catch(m, x, y, z, paint=STEEL):
    # Hinged toggle latch crossing the lid seam. Dark relief and a metal release
    # lever make its shape readable even with the case in shade.
    box(m, (x - .11, y - .48, z - 1.25), (x + .11, y + .48, z + 1.0), HARDWARE, .08)
    box(m, (x - .26, y - .34, z - .65), (x - .14, y + .34, z + .55), paint, .09)
    cylinder(m, (x - .3, y, z - .6), (0, 1, 0), .14, .95, paint, 12)
    box(m, (x - .36, y - .21, z + .08), (x - .29, y + .21, z + .43), HARDWARE, .045)
    for dz in (-.99, .78):
        screw(m, (x - .13, y, z + dz), (-1, 0, 0), .11)


def case(m, lo, hi, paint, upright=False):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    # Lid and tub are separate rounded shells, with a recessed dark gasket.
    axis = 0 if upright else 2
    seam = hi[axis] - (hi[axis] - lo[axis]) * .27
    lowhi, highlo = hi.copy(), lo.copy()
    lowhi[axis], highlo[axis] = seam - .045, seam + .045
    box(m, lo, lowhi, paint, .52)
    box(m, highlo, hi, paint, .52)
    a, b = lo + .15, hi - .15
    a[axis], b[axis] = seam - .05, seam + .05
    box(m, a, b, EDGE, .04)
    # Riveted angle sections around the shell edges.
    for y in (lo[1] + .22, hi[1] - .22):
        box(m, (lo[0] + .12, y - .17, lo[2] + .3), (hi[0] - .12, y + .17, lo[2] + .62), HARDWARE, .08)
        box(m, (lo[0] + .12, y - .17, hi[2] - .62), (hi[0] - .12, y + .17, hi[2] - .3), HARDWARE, .08)
        box(m, (lo[0] + .1, y - .16, lo[2] + .45), (lo[0] + .4, y + .16, hi[2] - .45), HARDWARE, .09)
        box(m, (hi[0] - .4, y - .16, lo[2] + .45), (hi[0] - .1, y + .16, hi[2] - .45), HARDWARE, .09)
    for cx in (-1, 1):
        for cy in (-1, 1):
            for cz in (-1, 1):
                corner_guard(m, lo + .05, hi - .05, cx, cy, cz, 1.23, ALUMINIUM if upright or paint == GREY else HARDWARE)
    if upright:
        # Lid catches belong on the edge of a tall case, leaving its broad face
        # clear as in the reference. They straddle the depth-wise lid seam.
        for z in (lo[2] + 7.0, hi[2] - 7.0):
            y = hi[1] + .04
            box(m, (seam - .48, y, z - 1.25), (seam + .48, y + .11, z + 1), HARDWARE, .08)
            box(m, (seam - .34, y + .14, z - .65), (seam + .34, y + .26, z + .55), STEEL, .08)
            cylinder(m, (seam, y + .3, z - .6), (1, 0, 0), .14, .95, STEEL, 10)
            for dz in (-.99, .78):
                screw(m, (seam, y + .12, z + dz), (0, 1, 0), .11)
    else:
        for y in (lo[1] + 2.1, hi[1] - 2.1):
            catch(m, lo[0] - .03, y, seam)
    # Swinging carry handle on the broad side, with proper recessed brackets.
    z = lo[2] + (hi[2] - lo[2]) * .46
    y = (lo[1] + hi[1]) / 2
    if not upright:
        recessed_handle(m, lo[0] - .035, y, z, min(6.2, (hi[1] - lo[1]) * .4), 2.5, HARDWARE)
        recessed_handle(m, hi[0] + .035, y, z, min(6.2, (hi[1] - lo[1]) * .4), 2.5, HARDWARE, facing="right")
    else:
        # Upright flight cases have a hinged top handle, stood just off the lid.
        box(m, (lo[0] + 2, y - 2.8, hi[2] + .025), (hi[0] - 2, y + 2.8, hi[2] + .16), HARDWARE, .07)
        x = (lo[0] + hi[0]) / 2
        path = [(x, y - 2.4, hi[2] + .2), (x, y - 2.4, hi[2] + 1.3),
                (x, y - 1.8, hi[2] + 1.85), (x, y + 1.8, hi[2] + 1.85),
                (x, y + 2.4, hi[2] + 1.3), (x, y + 2.4, hi[2] + .2)]
        tube(m, path, .26, EDGE, 10)
        mark(m, "case_label", (lo[0] - .022, hi[1] - 2.7, hi[2] - 2.35), 3.2, 1.62)
    # Strap wraps have separate runs on each face, keeping texture weave small.
    if not upright:
        for y in (lo[1] + (hi[1] - lo[1]) * .21, lo[1] + (hi[1] - lo[1]) * .77):
            w = .75
            box(m, (lo[0] - .04, y - w / 2, lo[2] + .45), (lo[0] + .025, y + w / 2, hi[2] - .45), WEBBING, .02)
            box(m, (hi[0] - .025, y - w / 2, lo[2] + .45), (hi[0] + .04, y + w / 2, hi[2] - .45), WEBBING, .02)
            box(m, (lo[0] + .45, y - w / 2, hi[2] - .025), (hi[0] - .45, y + w / 2, hi[2] + .055), WEBBING, .025)
    # Rivet heads along the sides, not big decorative studs.
    for y in np.linspace(lo[1] + 1.7, hi[1] - 1.7, 4):
        for z in (lo[2] + .7, hi[2] - .7):
            screw(m, (lo[0] - .01, y, z), (-1, 0, 0), .085)
    F.collide(m, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], "metal" if paint in (BLUE, RED, GREY) else "plastic")


def bedroll(m):
    # A compressed cloth cylinder with real folds and a rolled end. The canvas
    # texture is wrapped several times rather than stretched once over 3 feet.
    x0, x1, cy, cz, radius = -20.1, 17.4, 40.4, DECK + 5.1, 5.1
    axials, sides = 24, 48
    rings, normals = [], []
    for j in range(axials + 1):
        x = x0 + (x1 - x0) * j / axials
        compressed = sum(.36 * math.exp(-((x - at) / .82) ** 2) for at in (-9.8, 8.8))
        edge = .15 + .38 * math.exp(-((j / axials - .5) / .48) ** 8)
        pts, ns = [], []
        for a in range(sides):
            angle = a * math.tau / sides
            wrinkle = .14 * math.cos(angle * 7 + x * .17) + .10 * math.sin(angle * 11 - x * .34)
            r = radius - compressed + wrinkle + edge
            p = (x, cy + math.cos(angle) * r, cz + math.sin(angle) * r * .94)
            pts.append(F.p(*p))
            ns.append(F.y * math.cos(angle) + F.z * math.sin(angle))
        rings.append(pts)
        normals.append(ns)
    for j in range(axials):
        # Four longitudinal repeats, each bounded exactly at a ring. This keeps
        # atlas UVs in their own swatch without crossing its edge.
        u0, u1 = (j % 6) / 6, ((j % 6) + 1) / 6
        for a in range(sides):
            b = (a + 1) % sides
            v0, v1 = (a % 12) / 12, ((a % 12) + 1) / 12
            pts = [rings[j][a], rings[j][b], rings[j + 1][b], rings[j + 1][a]]
            ns = [normals[j][a], normals[j][b], normals[j + 1][b], normals[j + 1][a]]
            P.outward(m, CANVAS, pts, sum(ns), uv=[(u0, v0), (u0, v1), (u1, v1), (u1, v0)], normals=ns)
    for x, sign in ((x0, -1), (x1, 1)):
        # Shaded backing of the bundled cloth, and an actual 2.6-turn rolled hem.
        disk = [F.p(x, cy + math.cos(a) * radius, cz + math.sin(a) * radius * .94) for a in np.linspace(0, math.tau, sides, endpoint=False)]
        P.outward(m, CANVAS, disk, F.x * sign,
                  uv=[(.5 + math.cos(a) * .48, .5 + math.sin(a) * .48) for a in np.linspace(0, math.tau, sides, endpoint=False)])
        spiral = []
        for i in range(193):
            a = i / 192 * math.tau * 5.2
            r = .7 + i / 192 * 4.36
            spiral.append((x + sign * (.15 + .055 * math.sin(a * 3)), cy + math.cos(a) * r, cz + math.sin(a) * r * .94))
        tube(m, spiral, .16, OLIVE_STRAP, 6)
        cylinder(m, (x + sign * .12, cy, cz), (1, 0, 0), .42, .035, HARDWARE, 16)
    for x in (-9.8, 8.8):
        # Olive woven straps compress the bedding, with two realistic buckles.
        for a in range(sides):
            verts = []
            for xx, angle in ((x - .55, a), (x + .55, a), (x + .55, a + 1), (x - .55, a + 1)):
                t = angle * math.tau / sides
                compressed = sum(.36 * math.exp(-((xx - at) / .82) ** 2) for at in (-9.8, 8.8))
                fraction = (xx - x0) / (x1 - x0)
                edge = .15 + .38 * math.exp(-((fraction - .5) / .48) ** 8)
                r = radius - compressed + edge + .14 * math.cos(t * 7 + xx * .17) + .1 * math.sin(t * 11 - xx * .34) + .08
                verts.append(F.p(xx, cy + math.cos(t) * r, cz + math.sin(t) * r * .94))
            P.outward(m, OLIVE_STRAP, verts, F.y * math.cos((a + .5) * math.tau / sides) + F.z * math.sin((a + .5) * math.tau / sides),
                      uv=[(0, a % 8 / 8), (1, a % 8 / 8), (1, (a % 8 + 1) / 8), (0, (a % 8 + 1) / 8)])
        rounded_loop(m, (x, cy, cz + radius - .02), 1.7, 1.45, .18, HARDWARE, "top", .11)
        tube(m, [(x, cy - .7, cz + radius), (x, cy + .7, cz + radius)], .11, HARDWARE, 8)
    # One low loop of folded webbing is visible over the roll, rather than two
    # black sticks protruding from its top.
    tube(m, [(-4.2, cy, cz + 5), (-3.3, cy, cz + 6.05), (1.5, cy, cz + 6.05), (2.4, cy, cz + 5)], .19, OLIVE_STRAP, 8)
    pts = [F.p(x, cy + math.cos(a) * 5.45, cz + math.sin(a) * 5.2)
           for x in (x0, x1) for a in np.linspace(0, math.tau, 12, endpoint=False)]
    m.hull(pts, "cloth")


def build(loaded=True):
    m = AtlasModel()
    chassis(m)
    if loaded:
        # The reference has crates at either end, a tall blue pair in the middle,
        # red and aluminium cases behind the left crate, and black case + roll
        # in front of the right one. Keep real gaps between these separate items.
        crate(m, (-21, -45.5, DECK), (7.2, -18.5, 43.9), 0)
        case(m, (7.9, -46, DECK), (21.5, -19, 38.3), GREY)
        case(m, (7.9, -45.8, 38.55), (21.5, -19.2, 47.4), RED)
        case(m, (-19.1, -15.2, DECK), (-10.0, -.6, 52.1), BLUE, upright=True)
        case(m, (-7.5, -13.6, DECK), (1.7, 1.0, 50.3), BLUE, upright=True)
        crate(m, (-3.7, 9.6, DECK), (20.0, 34.0, 42.5), 2)
        case(m, (-20.8, 7.9, DECK), (-7.0, 33.4, 34.2), BLACK)
        bedroll(m)
    return m


def materials():
    MATERIALS.mkdir(parents=True, exist_ok=True)
    source = MATERIALS / "luggage_atlas_color.png"
    if not source.exists():
        raise FileNotFoundError("Keep the ImageGen source atlas; see railhead_luggage_imagegen.json.")
    image = Image.open(source).convert("RGB")
    # Power-of-two runtime textures, keeping the generated source untouched.
    size = 2048
    rgb = np.asarray(image.resize((size, size), Image.Resampling.LANCZOS), np.float32) / 255
    # A second generated source replaced the original coarse black swatch.
    # Resampling it into the runtime atlas is ordinary UV-atlas packing; both
    # original generated sources and their prompts remain available.
    black_source = MATERIALS / "luggage_black_source.png"
    if black_source.exists():
        rgb[512:1024, 1024:1536] = np.asarray(Image.open(black_source).convert("RGB").resize((512, 512), Image.Resampling.LANCZOS), np.float32) / 255
    rough, metal, ao = [np.ones((size, size), np.float32) for _ in range(3)]
    normal = np.zeros((size, size, 3), np.float32)
    normal[:, :, 2] = 1
    for cell in range(16):
        col, row = cell % 4, cell // 4
        ys, xs = slice(row * 512, (row + 1) * 512), slice(col * 512, (col + 1) * 512)
        tile = rgb[ys, xs]
        if cell in (WOOD, DARK_WOOD):
            grey = tile @ np.array((.2126, .7152, .0722), np.float32)
            tile[:] = (tile * .88 + grey[:, :, None] * .12) * np.array((.87, .84, .83))
        elif cell == GREEN:
            tile[:] *= np.array((.73, .80, .83))
        elif cell == BLUE:
            grey = tile @ np.array((.2126, .7152, .0722), np.float32)
            tile[:] = tile * .80 + grey[:, :, None] * .20
        elif cell == BLACK:
            tile[:] *= .80
        elif cell == OLIVE_STRAP:
            tile[:] *= .64
        lum = tile @ np.array((.2126, .7152, .0722), np.float32)
        # Metallic only where the worn coating exposes bare metal. Timber,
        # canvas, rubber and synthetic cases remain dielectric.
        base_rough = (.78, .85, .69, .38, .59, .59, .76, .54, .96, .91, .95, .69, .9, .42, .96, .82)[cell]
        rough[ys, xs] = np.clip(base_rough + (lum - lum.mean()) * .16, .25, .98)
        metal[ys, xs] = (.0, .0, .12, .95, .12, .12, .0, .65, .0, .0, .0, .65, .16, .93, .0, .0)[cell]
        if cell in (GREEN, BLUE, RED):
            spread = tile.max(axis=2) - tile.min(axis=2)
            bare = np.clip((.10 - spread) * 5, 0, .45)
            metal[ys, xs] = np.maximum(metal[ys, xs], bare)
        low = np.asarray(Image.fromarray(np.uint8(lum * 255)).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
        relief = lum - low
        height = lum * (.075 if cell in (WOOD, DARK_WOOD) else .008 if cell == BLACK else .055) + relief * (.20 if cell in (CANVAS, WEBBING, OLIVE_STRAP) else .045 if cell in (WOOD, DARK_WOOD) else .02 if cell == BLACK else .10)
        gy, gx = np.gradient(height)
        n = np.stack((-gx * 6, gy * 6, np.ones_like(gx)), axis=-1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        normal[ys, xs] = n
        ao[ys, xs] = np.clip(1 + np.minimum(relief, 0) * .65, .84, 1)
    Image.fromarray(np.uint8(np.clip(rgb, 0, 1) * 255)).save(MATERIALS / "luggage_color.png")
    Image.fromarray(np.uint8((normal * .5 + .5) * 255)).save(MATERIALS / "luggage_normal.png")
    for name, values in (("roughness", rough), ("metalness", metal), ("ao", ao)):
        Image.fromarray(np.uint8(np.clip(values, 0, 1) * 255)).save(MATERIALS / f"luggage_{name}.png")
    K.write_text(MATERIALS / f"{BODY}.vmat", f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_METALNESS_TEXTURE "1"
    g_flRoughnessScaleFactor "1"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
    TextureColor "{TEX}/luggage_color.png"
    TextureNormal "{TEX}/luggage_normal.png"
    TextureRoughness "{TEX}/luggage_roughness.png"
    TextureMetalness "{TEX}/luggage_metalness.png"
    TextureAmbientOcclusion "{TEX}/luggage_ao.png"
}}
''')
    markings()


def markings():
    image = Image.new("RGBA", (2048, 1024))
    d = ImageDraw.Draw(image)
    font = K.ASSETS / "fonts/Dinish-Bold.ttf"
    regular = K.ASSETS / "fonts/Dinish-Regular.ttf"
    white, black = (219, 222, 206, 255), (24, 23, 19, 250)

    def fit(text, rect, color, bold=True, border=10):
        x0, y0, x1, y1 = rect
        for size in range(y1 - y0, 6, -1):
            f = ImageFont.truetype(str(font if bold else regular), size)
            bb = d.textbbox((0, 0), text, font=f)
            if bb[2] - bb[0] <= x1 - x0 - border * 2 and bb[3] - bb[1] <= y1 - y0 - border * 2:
                d.text(((x0 + x1 - bb[2] + bb[0]) / 2, (y0 + y1 - bb[3] - bb[1]) / 2), text, font=f, fill=color)
                break

    d.rounded_rectangle((26, 26, 230, 198), radius=22, outline=white, width=10)
    fit("DB", (40, 40, 216, 184), white)
    fit("L-312", MARK_RECTS["number"], white)
    fit("Zul. Gesamtgew. 2000 kg", MARK_RECTS["weight"], white, False)
    # Upright and fragile pictograms, matching the shipping crates in the photo.
    for x0, x1 in ((28, 196), (220, 392)):
        d.rectangle((x0, 268, x1, 620), outline=black, width=8)
    for x in (78, 146):
        d.polygon(((x, 302), (x - 23, 349), (x - 10, 349), (x - 10, 570), (x + 10, 570), (x + 10, 349), (x + 23, 349)), fill=black)
    d.rectangle((56, 580, 169, 592), fill=black)
    d.polygon(((256, 302), (357, 302), (349, 402), (329, 430), (315, 435), (315, 565), (352, 565), (352, 584),
               (263, 584), (263, 565), (300, 565), (300, 435), (282, 430), (266, 402)), fill=black)
    d.line((258, 332, 354, 332), fill=(0, 0, 0, 0), width=5)
    for name in ("shipping", "case_label"):
        x0, y0, x1, y1 = MARK_RECTS[name]
        d.rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), fill=(188, 186, 166, 246))
        fit("RAILHEAD  0312", (x0 + 10, y0 + 12, x1 - 10, y0 + 68), black, False, 8)
        rng = np.random.default_rng(312)
        x = x0 + 30
        while x < x1 - 30:
            width = int(rng.integers(2, 8))
            d.rectangle((x, y0 + 86, x + width, y1 - 26), fill=(42, 41, 34, 220))
            x += width + int(rng.integers(3, 7))
    x0, y0, x1, y1 = MARK_RECTS["reflector"]
    d.rounded_rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), radius=6, fill=(210, 137, 9, 255), outline=(242, 184, 44, 255), width=7)
    for y in range(y0 + 13, y1 - 12, 9):
        for x in range(x0 + 13, x1 - 12, 9):
            d.polygon(((x, y - 3), (x + 3, y), (x, y + 3), (x - 3, y)), fill=(235, 166, 31, 255))
    # Small scattered losses in the ink, rather than clean digital text. Keep
    # these away from the paper labels and the reflective orange panels.
    rgba = np.asarray(image).copy()
    rng = np.random.default_rng(312)
    dirt = rng.random((1024, 2048))
    mask = np.zeros((1024, 2048), bool)
    mask[:220] = True
    mask[250:640, :420] = True
    rgba[:, :, 3][mask & (dirt < .022)] = 0
    image = Image.fromarray(rgba)
    image.save(MATERIALS / "luggage_markings_color.png")
    image.getchannel("A").save(MATERIALS / "luggage_markings_alpha.png")
    Image.new("RGB", image.size, (128, 128, 255)).save(MATERIALS / "luggage_markings_normal.png")
    Image.new("L", image.size, 195).save(MATERIALS / "luggage_markings_roughness.png")
    K.write_text(MATERIALS / f"{INK}.vmat", f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_ALPHA_TEST "1"
    g_flAlphaTestReference "0.45"
    g_flAntiAliasedEdgeStrength "1"
    g_flMetalness "0"
    g_flRoughnessScaleFactor "1"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
    TextureColor "{TEX}/luggage_markings_color.png"
    TextureTranslucency "{TEX}/luggage_markings_alpha.png"
    TextureNormal "{TEX}/luggage_markings_normal.png"
    TextureRoughness "{TEX}/luggage_markings_roughness.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
''')


def scene_group():
    from railhead_map import ids
    children = []
    for label, e, n, along in PLACEMENTS:
        key = f"luggage/{label}"
        children.append(K.game_object(ids, "Luggage Trolley " + label.replace("/", " ").title(), key,
            K.to_world((e, n, 0)), K.yaw_rotation(-90 if along == "e" else 0),
            components=[
                K.component(ids, "Sandbox.ModelRenderer", key + "/renderer", Model=MODEL, RenderType="On", Tint="1,1,1,1",
                            BodyGroups=18446744073709551615),
                K.component(ids, "Sandbox.ModelCollider", key + "/collider", Model=MODEL, IsTrigger=False, Static=True),
            ]))
    return K.game_object(ids, "Luggage Trolleys", "luggage", children=children)


def placed_collisions():
    """The generator's navigation checks see exactly the colliders in the prop."""
    source = build()
    m = K.Model()
    for _, e, n, along in PLACEMENTS:
        frame = P.Frame((e, n, 0), (1, 0) if along == "e" else (0, 1))
        def transform(p):
            return frame.p(*local(p))
        def vector(v):
            return transform(v) - frame.o
        for centre, axes, size, surface in source.boxes:
            m.boxes.append((transform(centre), [vector(a) for a in axes], size, surface))
        for pts, surface in source.hulls:
            m.hulls.append(([transform(p) for p in pts], surface))
    return m


def emit(model, e, n, along="n", z0=0, loaded=True):
    """Compatibility for tools that want the mesh itself instead of an instance."""
    source = build(loaded)
    sign = -1 if along.startswith("-") else 1
    frame = P.Frame((e, n, z0), (0, sign) if along.endswith("n") else (sign, 0))
    def transform(p):
        return frame.p(*local(p))
    def vector(v):
        return transform(v) - frame.o
    for paint, polys in source.polygons.items():
        for i, (pts, normal) in enumerate(polys):
            ns = source.polygon_normals.get((paint, i))
            model.polygon(paint, [transform(p) for p in pts], vector(normal),
                          uv=source.polygon_uvs[(paint, i)], normals=[vector(v) for v in ns] if ns else None)
    for centre, axes, size, surface in source.boxes:
        model.boxes.append((transform(centre), [vector(a) for a in axes], size, surface))
    for pts, surface in source.hulls:
        model.hulls.append(([transform(p) for p in pts], surface))
    model.material_overrides.update(source.material_overrides)
    model.tile_overrides.update(source.tile_overrides)


def missing():
    return not (K.ASSETS / MODEL).exists() or any(not (MATERIALS / name).exists() for name in (
        f"{BODY}.vmat", f"{INK}.vmat", "luggage_color.png", "luggage_normal.png",
        "luggage_roughness.png", "luggage_metalness.png", "luggage_ao.png", "luggage_markings_alpha.png"))


def write():
    OUT.mkdir(parents=True, exist_ok=True)
    materials()
    model = build()
    count = K.write_model(OUT, RESOURCE, "luggage_trolley", model)
    print(f"Luggage trolley: {count:,} triangles, {len(model.polygons)} materials, {len(model.boxes)} boxes, {len(model.hulls)} hulls")
    return model


if __name__ == "__main__":
    write()
