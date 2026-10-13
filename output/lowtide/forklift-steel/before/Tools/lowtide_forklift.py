"""Lowtide's worn yellow LPG forklift, authored against the supplied side photograph.

Local inches: x across the truck, y towards its forks, z up. Small mechanical parts
are visual; the original cover, mast and overhead-guard collision stays unchanged.
Run this file to rebuild its materials and standalone preview; --dress also updates
the two existing Lowtide dressing meshes without rewriting the scene or other maps.
"""
import argparse
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import map_kit as K
from railhead_props import frame_for, outward

OUT = K.ASSETS / "materials/lowtide/forklift"
RESOURCE = "materials/lowtide/forklift"
MODEL_OUT = K.ASSETS / "models/props/lowtide"
MODEL_RESOURCE = "models/props/lowtide"
PAINT = "lt_fl_yellow"
STEEL = "lt_fl_steel"
HUB = "lt_fl_hub"
SILVER = "lt_fl_silver"
CHROME = "lt_fl_chrome"
RUBBER = "lt_fl_rubber"
VINYL = "lt_fl_vinyl"
BLACK = "lt_fl_black"
AMBER = "lt_fl_amber"
RED = "lt_fl_red"
WHITE = "lt_fl_white"
GLASS = "lt_fl_glass"
WARNING = "lt_fl_warning"
PAINTS = (PAINT, STEEL, HUB, SILVER, CHROME, RUBBER, VINYL, BLACK, AMBER, RED, WHITE, GLASS, WARNING)


def unit(v):
    return K.normalise(np.asarray(v, float))


def basis(axis):
    axis = unit(axis)
    ref = (0, 0, 1) if abs(axis[2]) < .9 else (1, 0, 0)
    u = unit(np.cross(ref, axis))
    return axis, u, np.cross(axis, u)


def _surface(name, colour, seed, silver=False):
    """Deterministic material data for chipped painted steel and tarnished aluminium."""
    size = 1024
    rng = np.random.default_rng(seed)
    noise = rng.normal(size=(size, size)).astype(np.float32)
    fine = ndimage.gaussian_filter(noise, .7, mode="wrap")
    coarse = ndimage.gaussian_filter(noise, 16, mode="wrap")
    coarse /= max(coarse.std(), 1e-6)
    stains = ndimage.gaussian_filter(noise, (42, 8), mode="wrap")
    stains /= max(stains.std(), 1e-6)
    wear = np.zeros((size, size), np.uint8)
    canvas = Image.fromarray(wear)
    draw = ImageDraw.Draw(canvas)
    for _ in range(850 if silver else 1200):
        x, y = rng.integers(0, size, 2)
        length = rng.uniform(1, 15)
        angle = rng.uniform(0, math.pi * 2)
        draw.line((int(x), int(y), int(x + math.cos(angle) * length), int(y + math.sin(angle) * length)),
                  fill=int(rng.uniform(95, 240)), width=int(rng.choice((1, 1, 2))))
    chips = np.asarray(canvas, float) / 255
    rust = np.clip((coarse - (1.5 if silver else 1.8)) * .40, 0, .65)
    rgb = np.broadcast_to(np.asarray(colour, float), (size, size, 3)).copy()
    rgb += (fine * 6 + coarse * 3 + np.clip(stains, -2, 2) * (12 if silver else 2))[..., None]
    rgb = rgb * (1 - rust[..., None]) + np.array((94, 64, 39)) * rust[..., None]
    rgb = rgb * (1 - chips[..., None] * .65) + np.array((113, 107, 91)) * chips[..., None] * .65
    rough = np.clip((.64 if silver else .65) + fine * .035 + rust * .32 - chips * .19, .25, .95)
    metal = np.clip((.72 if silver else .04) * (1 - rust) + chips * .86, 0, .95)
    height = fine * .007 + chips * -.017 + rust * .03
    dy, dx = np.gradient(ndimage.gaussian_filter(height, .6, mode="wrap"))
    normal = np.dstack((-dx * 4, dy * 4, np.ones_like(dx)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    for channel, data in (("color", rgb), ("normal", (normal * .5 + .5) * 255),
                          ("rough", rough * 255), ("metal", metal * 255)):
        stream = io.BytesIO()
        Image.fromarray(np.clip(np.rint(data), 0, 255).astype(np.uint8)).save(stream, format="PNG", optimize=True)
        path, payload = OUT / f"{name}_{channel}.png", stream.getvalue()
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)


def _warning_label():
    """Printed vinyl artwork, with restrained edge grime and scuffed ink."""
    w, h = 384, 960
    paper, ink = (218, 211, 189), (32, 32, 28)
    canvas = Image.new("RGB", (w, h), paper)
    draw = ImageDraw.Draw(canvas)

    def text(y, value, size, bold=True):
        font = ImageFont.truetype(str(K.ASSETS / "fonts" / f"Dinish-{'Bold' if bold else 'Regular'}.ttf"), size)
        draw.text((w / 2, y), value, font=font, fill=ink, anchor="mt")

    draw.rounded_rectangle((7, 7, w - 8, h - 8), radius=10, outline=ink, width=4)
    draw.rectangle((12, 12, w - 13, 139), fill=(205, 126, 42))
    text(46, "WARNING", 53)
    draw.line((12, 140, w - 13, 140), fill=ink, width=5)
    draw.polygon(((192, 173), (52, 411), (332, 411)), fill=ink)
    draw.polygon(((192, 202), (83, 391), (301, 391)), fill=(224, 183, 64))
    draw.polygon(((176, 260), (208, 260), (204, 333), (180, 333)), fill=ink)
    draw.ellipse((179, 348, 205, 374), fill=ink)
    text(450, "TIP-OVER", 43)
    text(503, "HAZARD", 43)
    draw.line((35, 576, w - 36, 576), fill=ink, width=3)
    text(606, "STAY WITH TRUCK", 31)
    for y, value in ((667, "HOLD ON"), (718, "BRACE FEET"), (769, "LEAN AWAY")):
        text(y, value, 29)
    draw.line((35, 838, w - 36, 838), fill=ink, width=2)
    text(866, "READ OPERATOR MANUAL", 22, False)
    text(910, "FL-07   /   SAFETY", 18, False)

    rng = np.random.default_rng(7404)
    noise = rng.normal(size=(h, w)).astype(np.float32)
    coarse = ndimage.gaussian_filter(noise, 13)
    coarse /= max(coarse.std(), 1e-6)
    yy, xx = np.indices((h, w))
    edge = np.minimum.reduce((xx, w - 1 - xx, yy, h - 1 - yy))
    grime = np.clip((coarse + .7) * .012 + np.exp(-edge / 19) * .15, 0, .23)
    rgb = np.asarray(canvas, float) * (1 - grime[..., None]) + np.array((91, 77, 55)) * grime[..., None]
    rgb += noise[..., None] * 1.1
    # Fine scratches fade the ink instead of punching conspicuous holes in the label.
    scuffs = Image.new("L", (w, h))
    marks = ImageDraw.Draw(scuffs)
    for _ in range(145):
        x, y = rng.integers(0, w), rng.integers(0, h)
        marks.line((int(x), int(y), int(x + rng.integers(-3, 4)), int(y + rng.integers(2, 13))),
                   fill=int(rng.integers(30, 105)), width=1)
    wear = np.asarray(scuffs, float)[..., None] / 255
    rgb = rgb * (1 - wear) + np.array(paper) * wear
    rough = np.clip(.77 + grime * .55 + noise * .012, .70, .94) * 255
    for channel, data in (("color", rgb), ("rough", rough)):
        stream = io.BytesIO()
        # The model UVs restore the printed aspect; texture dimensions suit the compiler's mip chain.
        texture = Image.fromarray(np.clip(np.rint(data), 0, 255).astype(np.uint8))
        texture.resize((512, 1024), Image.Resampling.LANCZOS).save(stream, format="PNG", optimize=True)
        path, payload = OUT / f"warning_{channel}.png", stream.getvalue()
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)


def write_materials():
    OUT.mkdir(parents=True, exist_ok=True)
    _surface("steel", (47, 49, 50), 7402)
    _surface("silver", (153, 150, 138), 7403, silver=True)
    _warning_label()
    for paint in PAINTS:
        tint = (1, 1, 1)
        metal, rough, colour = 0, .6, None
        texture = None
        roughness = "materials/default/default_rough.tga"
        if paint == PAINT:
            texture = "materials/lowtide/lt_skip"
            tint = (1.04, 1.20, 1.02)
        elif paint in (STEEL, HUB):
            texture = f"{RESOURCE}/steel"
            tint = (1.03, .88, .73) if paint == HUB else (1, 1, 1)
        elif paint == SILVER:
            texture = f"{RESOURCE}/silver"
        elif paint == WARNING:
            colour = f"{RESOURCE}/warning_color.png"
            roughness = f"{RESOURCE}/warning_rough.png"
            rough = 1
        elif paint in (RUBBER, VINYL):
            colour = "materials/railhead/rw_rubber_color.png"
            tint = (.90, .90, .90) if paint == RUBBER else (1.1, 1.14, 1.18)
            rough = .79 if paint == RUBBER else .43
        else:
            tint, metal, rough = {
                CHROME: ((.65, .68, .69), .95, .24),
                BLACK: ((.025, .030, .033), .05, .53),
                AMBER: ((1, .48, .025), .05, .23),
                RED: ((.39, .023, .015), .0, .37),
                WHITE: ((.71, .70, .63), .0, .62),
                GLASS: ((.32, .39, .42), .97, .11),
            }[paint]
        lines = ["// Tools/lowtide_forklift.py", '"Layer0"', "{", '    shader "shaders/complex.shader"',
                 '    F_SPECULAR "1"', f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"',
                 '    g_flModelTintAmount "1"', '    TextureAmbientOcclusion "materials/default/default_ao.tga"']
        if texture:
            lines += ['    F_METALNESS_TEXTURE "1"', '    g_flMetalness "0"',
                      '    g_flRoughnessScaleFactor "1"']
            for parameter, channel in (("TextureColor", "color"), ("TextureNormal", "normal"),
                                       ("TextureRoughness", "rough"), ("TextureMetalness", "metal")):
                lines.append(f'    {parameter} "{texture}_{channel}.png"')
        else:
            lines += [f'    g_flMetalness "{metal}"', f'    g_flRoughnessScaleFactor "{rough}"',
                      f'    TextureColor "{colour or "materials/default/default_color.tga"}"',
                      '    TextureNormal "materials/railhead/rubber_normal.png"' if paint in (RUBBER, VINYL) else
                      '    TextureNormal "materials/default/default_normal.tga"',
                      f'    TextureRoughness "{roughness}"']
        K.write_text(OUT / f"{paint}.vmat", "\n".join(lines + ["}", ""]))


def configure(model):
    for paint in PAINTS:
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = 48.0


class Forklift:
    def __init__(self, model, e, n, facing="+n", z0=0, lift=0):
        self.m = model
        self.frame = frame_for(e, n, z0, facing)
        self.axes = np.array((self.frame.x, self.frame.y, self.frame.z))
        self.lift = max(0.0, lift)

    def p(self, q):
        return self.frame.o + np.asarray(q, float) @ self.axes

    def poly(self, paint, points, normal, normals=None, uv=None):
        points, normal = np.asarray(points, float), unit(normal)
        # A lathe's pole is a triangle, not a quad with two coincident vertices.
        keep = [i for i, p in enumerate(points) if np.linalg.norm(p - points[(i - 1) % len(points)]) > 1e-8]
        if len(keep) < 3:
            return
        if len(keep) != len(points):
            points = points[keep]
            normals = None if normals is None else [normals[i] for i in keep]
            uv = None if uv is None else [uv[i] for i in keep]
        if uv is None:
            if paint == PAINT:
                if abs(normal[0]) > .55:
                    uv = np.column_stack(((points[:, 1] + 53) / 96, (points[:, 2] - 5) / 41))
                else:
                    uv = np.column_stack(((points[:, 1] + 53) / 96, .14 + (points[:, 0] + 25) / 70))
            else:
                # Project in local space so both mirrored trucks retain the same texel density.
                i = int(np.argmax(np.abs(normal)))
                a, b = [k for k in range(3) if k != i]
                uv = points[:, (a, b)] / 32 + (.137, .283)
        uv = np.asarray(uv, float)
        if np.linalg.matrix_rank(uv[1:] - uv[0], tol=1e-9) < 2:
            edge = unit(max((q - points[0] for q in points[1:]), key=np.linalg.norm))
            side = unit(np.cross(normal, edge))
            values = np.column_stack((points @ edge, points @ side))
            uv = (values - values.min(axis=0)) / np.maximum(values.ptp(axis=0) if hasattr(values, "ptp") else np.ptp(values, axis=0), 32) * .7 + (.14, .13)
        if paint == PAINT:
            uv = np.clip(uv, .004, .996)
        outward(self.m, paint, [self.p(q) for q in points], normal @ self.axes, uv=uv,
                normals=None if normals is None else [unit(q) @ self.axes for q in normals])

    def box(self, centre, size, paint=STEEL, bevel=.06, axes=None):
        c, h = np.asarray(centre, float), np.asarray(size, float) / 2
        axes = np.eye(3) if axes is None else np.asarray(axes, float)
        b = min(bevel, float(h.min()) * .75)

        def draw(points, normal):
            self.poly(paint, [c + np.asarray(p) @ axes for p in points], np.asarray(normal) @ axes)

        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            for s in (-1, 1):
                pts = []
                for sj, sk in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    p = np.zeros(3); p[i], p[j], p[k] = s * h[i], sj * (h[j] - b), sk * (h[k] - b)
                    pts.append(p)
                normal = np.zeros(3); normal[i] = s
                draw(pts, normal)
        if b <= 1e-6:
            return
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            for sj in (-1, 1):
                for sk in (-1, 1):
                    pts = []
                    for si, near_j in ((-1, True), (1, True), (1, False), (-1, False)):
                        p = np.zeros(3); p[i] = si * (h[i] - b)
                        p[j], p[k] = sj * (h[j] if near_j else h[j] - b), sk * (h[k] - b if near_j else h[k])
                        pts.append(p)
                    normal = np.zeros(3); normal[j], normal[k] = sj, sk
                    draw(pts, normal)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    signs = np.array((sx, sy, sz))
                    draw([signs * (h - b) + signs * np.eye(3)[i] * b for i in range(3)], signs)

    def beam(self, a, b, width, depth=None, paint=STEEL, bevel=.08):
        a, b = np.asarray(a, float), np.asarray(b, float)
        z, x, y = basis(b - a)
        self.box((a + b) / 2, (width, depth or width, np.linalg.norm(b - a)), paint, bevel, (x, y, z))

    def post(self, points, width, depth, paint=STEEL):
        """A continuous rolled rectangular guard post, including the curved roof corner."""
        points = np.asarray(points, float)
        across = np.array((1, 0, 0))
        h, d, bevel = width / 2, depth / 2, .22
        section = ((-h, -d + bevel), (-h + bevel, -d), (h - bevel, -d), (h, -d + bevel),
                   (h, d - bevel), (h - bevel, d), (-h + bevel, d), (-h, d - bevel))
        rings, normals = [], []
        for i, p in enumerate(points):
            tangent = unit(points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)])
            side = unit(np.cross(across, tangent))
            rings.append([p + across * x + side * y for x, y in section])
            normals.append([unit(across * x / h + side * y / d) for x, y in section])
        for i, (a, b) in enumerate(zip(rings, rings[1:])):
            for k in range(8):
                j = (k + 1) % 8
                n = (normals[i][k], normals[i + 1][k], normals[i + 1][j], normals[i][j])
                self.poly(paint, (a[k], b[k], b[j], a[j]), sum(n), n)
        self.poly(paint, rings[0], points[0] - points[1])
        self.poly(paint, rings[-1], points[-1] - points[-2])

    def lathe(self, centre, axis, profile, paint=STEEL, segments=40, closed=False, smooth=True):
        """A surface of revolution with authored smooth normals and a continuous UV seam."""
        c = np.asarray(centre, float)
        axis, u, v = basis(axis)
        profile = list(profile)
        if closed:
            profile.append(profile[0])
        coefficients = [unit((a[1] - b[1], b[0] - a[0])) for a, b in zip(profile, profile[1:])]
        def coefficient(index):
            if not smooth:
                return coefficients[min(index, len(coefficients) - 1)]
            before = coefficients[index - 1] if index else coefficients[-1] if closed else coefficients[0]
            after = coefficients[index] if index < len(coefficients) else coefficients[0] if closed else coefficients[-1]
            return unit(before + after)
        travelled = np.cumsum([0] + [np.linalg.norm(np.subtract(b, a)) for a, b in zip(profile, profile[1:])])
        for k, ((a, ra), (b, rb)) in enumerate(zip(profile, profile[1:])):
            normal_axial, normal_radial = ra - rb, b - a
            for i in range(segments):
                t, q = i / segments * 2 * math.pi, (i + 1) / segments * 2 * math.pi
                d0, d1 = math.cos(t) * u + math.sin(t) * v, math.cos(q) * u + math.sin(q) * v
                pts = (c + axis * a + d0 * ra, c + axis * a + d1 * ra,
                       c + axis * b + d1 * rb, c + axis * b + d0 * rb)
                na, nb = coefficient(k), coefficient(k + 1)
                normals = [axis * coef[0] + d * coef[1] for d, coef in ((d0, na), (d1, na), (d1, nb), (d0, nb))]
                coords = ((i / segments, travelled[k] / 24), ((i + 1) / segments, travelled[k] / 24),
                          ((i + 1) / segments, travelled[k + 1] / 24), (i / segments, travelled[k + 1] / 24))
                if paint == PAINT:
                    coords = None
                self.poly(paint, pts, axis * normal_axial + (d0 + d1) * normal_radial, normals, coords)

    def rod(self, a, b, r, paint=STEEL, sides=16, caps=True):
        a, b = np.asarray(a, float), np.asarray(b, float)
        axis, u, v = basis(b - a)
        length = np.linalg.norm(b - a)
        self.lathe(a, axis, ((0, r), (length, r)), paint, sides)
        if caps:
            for c, normal in ((a, -axis), (b, axis)):
                self.poly(paint, [c + r * (math.cos(t) * u + math.sin(t) * v)
                                 for t in np.linspace(0, 2 * math.pi, sides, endpoint=False)], normal)

    def tube(self, points, radius, paint=BLACK, sides=8):
        points = [np.asarray(p, float) for p in points]
        tangents = [unit(points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]) for i in range(len(points))]
        rings = []
        for p, tangent in zip(points, tangents):
            _, u, v = basis(tangent)
            rings.append([(p + radius * (math.cos(t) * u + math.sin(t) * v), math.cos(t) * u + math.sin(t) * v)
                          for t in np.linspace(0, 2 * math.pi, sides, endpoint=False)])
        for a, b in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                p, n = zip(a[i], a[j], b[j], b[i])
                self.poly(paint, p, sum(n), n)

    def ring(self, centre, axis, radius, thickness, paint=STEEL, segments=40, sides=8):
        c = np.asarray(centre, float)
        axis, u, v = basis(axis)
        for i in range(segments):
            aa, bb = i / segments * 2 * math.pi, (i + 1) / segments * 2 * math.pi
            da, db = math.cos(aa) * u + math.sin(aa) * v, math.cos(bb) * u + math.sin(bb) * v
            for j in range(sides):
                t, q = j / sides * 2 * math.pi, (j + 1) / sides * 2 * math.pi
                normals = (da * math.cos(t) + axis * math.sin(t), db * math.cos(t) + axis * math.sin(t),
                           db * math.cos(q) + axis * math.sin(q), da * math.cos(q) + axis * math.sin(q))
                points = [c + d * radius + n * thickness for d, n in zip((da, db, db, da), normals)]
                self.poly(paint, points, sum(normals), normals)

    def bolt(self, centre, axis=(1, 0, 0), r=.37, paint=HUB):
        c, a = np.asarray(centre, float), unit(axis)
        self.lathe(c, a, ((-.1, r * 1.28), (0, r * 1.28), (.07, r), (.27, r), (.32, r * .82)), paint, 6)
        self.rod(c + a * .30, c + a * .32, r * .81, paint, 6)

    def body(self, ys, top, bottom, width, paint=PAINT, radius=1.5):
        """Loft a shaped casting: curved plan corners, smooth rolled shoulders, real wheel cut-outs."""
        rings = []
        for y in ys:
            w, hi, lo = width(y), top(y), bottom(y)
            r = min(radius, (hi - lo) / 2.5)
            section = [(-w, lo), (-w, hi - r)]
            for t in np.linspace(math.pi, math.pi / 2, 5)[1:]:
                section.append((-w + r + r * math.cos(t), hi - r + r * math.sin(t)))
            section.append((w - r, hi))
            for t in np.linspace(math.pi / 2, 0, 5)[1:]:
                section.append((w - r + r * math.cos(t), hi - r + r * math.sin(t)))
            section += [(w, lo)]
            rings.append([np.array((x, y, z)) for x, z in section])
        # Sections have matching vertices, including the underside closing edge.
        for a, b in zip(rings, rings[1:]):
            for k in range(len(a)):
                j = (k + 1) % len(a)
                pts = (a[k], b[k], b[j], a[j])
                normal = -unit(np.cross(b[k] - a[k], a[j] - a[k]))
                # Round only the shoulder. Vertical panel and bottom keep their exact shading.
                normals = None
                if 1 <= k < len(a) - 2:
                    normals = []
                    for ring, index in ((a, k), (b, k), (b, j), (a, j)):
                        n = -unit(np.cross(b[index] - a[index], ring[min(index + 1, len(ring) - 1)] - ring[max(index - 1, 0)]))
                        normals.append(n)
                self.poly(paint, pts, normal, normals)
        for ring, n in ((rings[0], (0, -1, 0)), (rings[-1], (0, 1, 0))):
            self.poly(paint, ring, n)

    def wheel(self, sign, y, radius, width, x):
        c = np.array((sign * x, y, radius))
        h = width / 2
        profile = [(-h, radius * .61), (-h - .05, radius * .73), (-h + .18, radius * .87),
                   (-h + .55, radius * .93), (-h + 1.1, radius * .963), (-h + 1.8, radius * .972),
                   (h - 1.8, radius * .972), (h - 1.1, radius * .963), (h - .55, radius * .93),
                   (h - .18, radius * .87), (h + .05, radius * .73), (h, radius * .61)]
        self.lathe(c, (sign, 0, 0), profile, RUBBER, 64, closed=True)
        # Rolled tread lugs follow the tire's curved shoulder. The grooves are real geometry.
        tread_profile = [(-h - .02, radius * .872), (-h + .20, radius * .925),
                         (-h + .65, radius * .970), (-h + 1.35, radius * .994),
                         (0, radius * 1.004), (h - 1.35, radius * .994),
                         (h - .65, radius * .970), (h - .20, radius * .925), (h + .02, radius * .872)]
        for i in range(28):
            rings = []
            for x, r in tread_profile:
                phase = .036 * abs(x) / h
                t, q = (i / 28 * 2 * math.pi + phase, (i + .71) / 28 * 2 * math.pi + phase)
                da, db = np.array((0, math.cos(t), math.sin(t))), np.array((0, math.cos(q), math.sin(q)))
                rings.append((c + (x, 0, 0) + da * (r - .38), c + (x, 0, 0) + da * r,
                              c + (x, 0, 0) + db * r, c + (x, 0, 0) + db * (r - .38)))
            for a, b in zip(rings, rings[1:]):
                for k in (0, 1, 2):
                    pts = (a[k], b[k], b[k + 1], a[k + 1])
                    towards = np.mean(pts, axis=0) - c
                    towards[0] = 0
                    if k != 1:
                        radial = unit(towards)
                        towards = np.cross((1, 0, 0), radial) * (-1 if k == 0 else 1)
                    self.poly(RUBBER, pts, towards)
            self.poly(RUBBER, rings[0], (-1, 0, 0))
            self.poly(RUBBER, rings[-1], (1, 0, 0))
        outer = c + (sign * (h + .06), 0, 0)
        self.lathe(outer, (sign, 0, 0), ((-.36, radius * .63), (.18, radius * .63), (.42, radius * .60),
                   (.50, radius * .56), (.33, radius * .53), (-.05, radius * .49), (-.16, radius * .44),
                   (.06, radius * .40), (.43, radius * .36), (.64, radius * .33), (.65, radius * .18),
                   (1.10, radius * .17), (1.18, radius * .14), (1.18, 0)), HUB, 64)
        for r, off in ((.59, .45), (.51, .24), (.36, .50)):
            self.ring(outer + (sign * off, 0, 0), (1, 0, 0), radius * r, .095, HUB, 48, 6)
        for r, count, off in ((.28, 6, .83), (.45, 8, .51)):
            for i in range(count):
                t = (i + .12) / count * 2 * math.pi
                self.bolt(outer + (sign * off, radius * r * math.cos(t), radius * r * math.sin(t)), (sign, 0, 0), .34 if count == 8 else .39)
        self.bolt(outer + (sign * 1.21, 0, 0), (sign, 0, 0), .66)
        # Moulded sidewall rings, outside the rim and below the block shoulders.
        for r in (.77, .88):
            self.ring(outer + (-sign * .02, 0, 0), (1, 0, 0), radius * r, .055, RUBBER, 48, 4)

    def chassis(self):
        self.box((0, -3, 10), (28, 76, 8), STEEL, .8)
        self.rod((-19, -38, 10.6), (19, -38, 10.6), 1.6, STEEL)
        self.rod((-20, 26, 13.2), (20, 26, 13.2), 2.2, STEEL)

        def rear_bottom(y):
            dy = y + 38
            return max(6.2, 10.6 + math.sqrt(max(0, 12.0 ** 2 - dy ** 2))) if abs(dy) < 12 else 6.2

        def rear_width(y):
            return 17.5 + math.sqrt(max(0, 5 ** 2 - (y + 48) ** 2)) if y < -48 else 22.5

        # Rear casting is yellow all the way round; the tire arches really penetrate the body.
        self.body(np.unique(np.r_[np.linspace(-53, -48, 12), np.linspace(-48, -29, 34)]),
                  lambda y: 42.5 - (max(0, -49 - y) / 4) ** 2 * 1.7,
                  rear_bottom, rear_width, radius=2)
        self.body(np.linspace(-29, 10.5, 48),
                  lambda y: float(np.interp(y, (-29, -10, -7, 5, 10.5), (29, 29, 17.8, 17.8, 22.5))),
                  rear_bottom, lambda y: 22.5, radius=.7)
        # Rounded engine bonnet supporting the seat, with a small panel gap at its foot.
        self.box((0, -18, 29.3), (43, 27, .65), BLACK, .18)
        self.body(np.linspace(-31, -5.7, 35),
                  lambda y: float(np.interp(y, (-31, -28, -11, -8, -5.7), (40, 43.6, 43.6, 42, 37.8))),
                  lambda y: 29.7, lambda y: 21.5 - max(0, y + 10) * .22, radius=2.6)
        for s in (-1, 1):
            # Rolled fenders follow the large front tire rather than capping it with a flat slab.
            centre = np.array((s * 20.9, 26, 13.2))
            for i in range(32):
                t, q = .02 + i / 32 * (math.pi - .04), .02 + (i + 1) / 32 * (math.pi - .04)
                a, b = np.array((0, math.cos(t), math.sin(t))), np.array((0, math.cos(q), math.sin(q)))
                for x0, x1, r0, r1, n in ((-3.5, 3.5, 14.15, 14.95, (s, 0, 0)),):
                    for side in (-1, 1):
                        offset = np.array((side * 3.5, 0, 0))
                        self.poly(PAINT, (centre + offset + a * r0, centre + offset + b * r0,
                                          centre + offset + b * r1, centre + offset + a * r1), (side, 0, 0))
                    for r, flip in ((r1, 1), (r0, -1)):
                        pts = (centre + (-3.5, 0, 0) + a * r, centre + (3.5, 0, 0) + a * r,
                               centre + (3.5, 0, 0) + b * r, centre + (-3.5, 0, 0) + b * r)
                        self.poly(PAINT if flip > 0 else STEEL, pts, (a + b) * flip, [a * flip, a * flip, b * flip, b * flip])
            # Open entry with a perforated lower step and black, grooved driver's floor.
            self.box((s * 21.1, -1, 18.3), (5.5, 15, .7), STEEL, .18)
            for y in np.arange(-7.2, 6.7, 1.25):
                self.box((s * 21.2, y, 18.70), (4.4, .38, .18), BLACK, .04)
            # Bonnet latch, cooling louvers and exposed mounting bolts.
            self.box((s * 21.6, -28.8, 33.9), (.45, 5.0, 4.0), BLACK, .2)
            self.box((s * 21.95, -28.7, 33.0), (.7, 3.25, 1.05), STEEL, .18)
            for z in np.arange(36.2, 38.4, .55):
                self.box((s * 21.68, -28.7, z), (.18, 4.7, .24), BLACK, .025)
            for y, z in ((-31.5, 26), (-13.0, 26), (7, 14), (-48, 27)):
                self.bolt((s * 22.65, y, z), (s, 0, 0), .25)
        self.box((0, 3.5, 25), (36.5, 27, 1.4), STEEL, .35)
        self.box((0, 3.5, 25.8), (35, 25, .38), RUBBER, .1)
        for x in np.arange(-16, 16.5, 1.25):
            self.box((x, 3.5, 26.07), (.38, 24, .15), BLACK, .025)
        # Rear radiator recess, protected lamp clusters and a tow pin beneath the counterweight.
        self.box((0, -53.08, 25), (26, .42, 11), BLACK, .5)
        for z in np.arange(20.7, 29.8, 1.15):
            self.box((0, -53.4, z), (24, .55, .28), STEEL, .04)
        for s in (-1, 1):
            self.box((s * 17.8, -51.7, 32), (5.5, 1.7, 7.6), BLACK, .5)
            self.box((s * 17.8, -52.65, 33.9), (4.2, .45, 2.6), AMBER, .22)
            self.box((s * 17.8, -52.65, 30.7), (4.2, .45, 2.6), RED, .22)
            for z in (28.5, 32.1, 35.5):
                self.rod((s * 17.8 - 3, -53.5, z), (s * 17.8 + 3, -53.5, z), .16, SILVER, 10)
        self.box((0, -53.9, 11), (9, 2.7, 4.8), STEEL, .6)
        self.rod((0, -54, 8.5), (0, -54, 14.2), .6, SILVER, 16)

    def seat(self):
        for x in (-6.8, 6.8):
            self.box((x, -19, 44.6), (1.3, 17, 1), STEEL, .12)
        # Soft rectangular cushion: rounded footprint and rolled upholstered edges.
        rings = []
        for z, scale in ((44.9, .83), (45.3, .96), (46.1, 1), (47.5, .98), (48.1, .87)):
            pts = []
            for t in np.linspace(0, 2 * math.pi, 48, endpoint=False):
                x = math.copysign(abs(math.cos(t)) ** .42, math.cos(t)) * 9.4 * scale
                y = math.copysign(abs(math.sin(t)) ** .42, math.sin(t)) * 8.2 * scale - 18.7
                pts.append(np.array((x, y, z)))
            rings.append(pts)
        for a, b in zip(rings, rings[1:]):
            for i in range(48):
                j = (i + 1) % 48
                n = [unit((p[0] / 9.4, (p[1] + 18.7) / 8.2, .25 if p[2] > 47 else -.15)) for p in (a[i], a[j], b[j], b[i])]
                self.poly(VINYL, (a[i], a[j], b[j], b[i]), sum(n), n)
        self.poly(VINYL, rings[-1], (0, 0, 1))
        self.tube(rings[-1] + [rings[-1][0]], .055, BLACK, 6)
        # Contoured reclined back, narrower at the waist, with a separate rear plastic shell.
        back_rings = []
        for z, w in ((47.5, 6.8), (49, 8.0), (54, 8.9), (60.7, 8.5), (63, 7.4), (63.7, 5.9)):
            cy = -26.1 - (z - 47.5) * .20
            pts = []
            for t in np.linspace(0, 2 * math.pi, 40, endpoint=False):
                x = w * math.copysign(abs(math.cos(t)) ** .42, math.cos(t))
                y = cy + 1.55 * math.copysign(abs(math.sin(t)) ** .55, math.sin(t))
                pts.append(np.array((x, y, z)))
            back_rings.append(pts)
        for a, b in zip(back_rings, back_rings[1:]):
            for i in range(40):
                j = (i + 1) % 40
                pts = (a[i], a[j], b[j], b[i])
                n = [unit((p[0] / 9, (p[1] + 26.1 + (p[2] - 47.5) * .2) / 1.55, .18)) for p in pts]
                self.poly(VINYL, pts, sum(n), n)
        self.poly(VINYL, back_rings[-1], (0, 0, 1))
        for s in (-1, 1):
            self.rod((s * 9.6, -26.0, 46.5), (s * 11.0, -26.0, 46.5), 2.2, STEEL, 32)
            self.bolt((s * 11.07, -26.0, 46.5), (s, 0, 0), .6, SILVER)
            self.beam((s * 10.1, -26.0, 47.5), (s * 10.1, -23.5, 54.8), 1.0, 1.6, STEEL)
            self.box((s * 10.6, -20.8, 55.2), (2.35, 13.2, 1.8), VINYL, .64)
        self.beam((8, -20.8, 46.2), (8.8, -21.2, 50.2), .6, .6, BLACK)
        self.box((8.8, -21.2, 50.4), (1.4, 1.3, 1.0), RED, .2)

    def controls(self):
        # Steering binnacle slopes back from the floor rather than occupying the whole footwell.
        self.beam((0, 16.5, 27), (0, 9.1, 42.5), 10.5, 7.2, STEEL, .4)
        self.rod((0, 11, 39), (0, 6.2, 52), 1.95, BLACK, 24)
        self.lathe((0, 6.2, 52), (0, -.35, 1), ((-1.5, 2), (-.4, 2.0), (0, 1.5)), STEEL, 24)
        c, normal = np.array((0, 4.8, 55.2)), unit((0, -.6, .8))
        self.rod((0, 6.2, 52), c, .75, STEEL, 20)
        _, u, v = basis(normal)
        self.ring(c, normal, 6.6, .43, VINYL, 64, 10)
        self.rod(c - normal * .6, c + normal * .22, 1.35, BLACK, 24)
        for angle in (0, 2.1, 4.2):
            d = math.cos(angle) * u + math.sin(angle) * v
            self.beam(c + d * 1.1, c + d * 6.3, .52, .32, STEEL)
        self.rod(c + u * 5.5, c + u * 5.5 + normal * 1.3, .55, BLACK, 16)
        self.box((12.0, -3.5, 33.2), (7.8, 9.8, 13), BLACK, .8)
        for i, x in enumerate((9.5, 12, 14.5)):
            y = -2.5 - i * 1.25
            self.lathe((x, y, 39.5), (0, 0, 1), ((-.8, .72), (0, .72), (.25, .9), (.5, .6), (.75, .83), (1, .5)), RUBBER, 16)
            self.rod((x, y, 40.3), (x, y - .6, 46.6 - i * 1.1), .18, STEEL, 12)
            self.lathe((x, y - .6, 46.6 - i * 1.1), (0, 0, 1), ((-.8, .4), (-.4, .68), (.2, .73), (.8, .4)), VINYL, 20)
        for x, y, w in ((-5.2, 12, 3.6), (1.2, 15, 3), (7.0, 11, 2.4)):
            self.beam((x, y, 26.1), (x, y - 1.3, 29.2), .48, .48, STEEL)
            self.box((x, y - 1.0, 29.5), (w, 4.3, .6), RUBBER, .15,
                     axes=((1, 0, 0), (0, .94, .342), (0, -.342, .94)))
            for z in (-1, 0, 1):
                self.box((x, y - 1 + z, 29.85), (w - .4, .22, .12), BLACK, .02)

    def guard_label(self, front, sign):
        # A thin sheet on the post's flat side, with its long edge following the rake.
        a, b = np.asarray(front[:2], float)
        up, normal = unit(b - a), np.array((sign, 0, 0))
        right = np.cross(up, normal)
        centre = a + (b - a) * ((58.5 - a[2]) / (b[2] - a[2]))
        centre += normal * (2.65 / 2 + .02)
        w, h, corner = .95, 2.375, .045
        outline = ((-w, -h + corner), (-w + corner, -h), (w - corner, -h), (w, -h + corner),
                   (w, h - corner), (w - corner, h), (-w + corner, h), (-w, h - corner))
        # Frame's across/forward axes are reflected; reverse U so the print reads correctly.
        self.poly(WARNING, [centre + right * u + up * v for u, v in outline], normal,
                  uv=[((w - u) / (2 * w), (v + h) / (2 * h)) for u, v in outline])

    def guard(self):
        for s in (-1, 1):
            x = s * 20.8
            front = [(x, 22, 28.9), (x, 11.8, 66), (x, 9.6, 73.4), (x, 8.1, 76.2),
                     (x, 6.6, 78.6), (x, 4.5, 80.5), (x, 2.2, 81.9), (x, -.7, 82.7)]
            self.post(front, 2.65, 3.1)
            self.beam((x, -31.8, 43), (x, -30.0, 82.5), 3.4, 3.0, STEEL, .24)
            self.box((x, -10.8, 82.7), (3.4, 45.0, 2.5), STEEL, .35)
            self.box((x, 21.5, 29.9), (4.3, 5.2, .7), STEEL, .12)
            self.box((x, -31.7, 43.5), (5, 5.3, .7), STEEL, .1)
            for y, z in ((20.5, 30.4), (-31.7, 44), (-30, 78.8)):
                self.bolt((x + s * 1.8, y, z), (s, 0, 0), .35, SILVER)
            # Grab handle, mirror arm and oval mirror housing.
            self.tube(((x + s * 1.7, 17, 44), (x + s * 2, 15.6, 44), (x + s * 2, 11.6, 57), (x + s * 1.7, 10.8, 57.5)), .30, BLACK, 12)
            self.rod((x, 8, 71.5), (x + s * 4.1, 8, 71.5), .25, STEEL, 12)
            self.box((x + s * 4.1, 8, 69.2), (3.7, 1.8, 6), BLACK, .6)
            self.box((x + s * 4.1, 7.02, 69.2), (3.1, .15, 5.3), GLASS, .35)
            self.box((x, 8.8, 75.4), (5.0, 3.3, 5.4), BLACK, .55)
            self.box((x, 10.55, 75.4), (4.1, .25, 4.25), WHITE, .45)
            self.guard_label(front, s)
        for y in (-32.5, 11.5):
            self.box((0, y, 82.7), (43.4, 2.5, 2.5), STEEL, .28)
        for x in (-14, -7, 0, 7, 14):
            self.box((x, -10.5, 82.35), (1.75, 43, 1.3), STEEL, .12)
        c = np.array((20.8, -30, 84))
        self.lathe(c, (0, 0, 1), ((0, 2.6), (.6, 2.6), (1, 1.9)), BLACK, 32)
        self.lathe(c, (0, 0, 1), ((1, 2.0), (1.5, 2.05), (4.9, 1.9), (5.5, 1.7), (5.8, 1.1), (5.85, 0)), AMBER, 48)
        for z in (1.7, 2.3, 3.0, 3.7, 4.4):
            self.ring(c + (0, 0, z), (0, 0, 1), 1.94, .045, AMBER, 40, 4)

    def gas_tank(self):
        # Horizontal LPG bottle with dished ends, wrap straps, mounting feet and a valve guard.
        c = np.array((0, -42.2, 49.8))
        profile = [(-17.0, 0), (-17.0, 2.3), (-16.4, 4.7), (-15.2, 5.9), (-13.5, 6.3),
                   (13.5, 6.3), (15.2, 5.9), (16.4, 4.7), (17.0, 2.3), (17.0, 0)]
        self.lathe(c, (1, 0, 0), profile, SILVER, 64)
        for x in (-10.0, 10.0):
            self.box((x, -42.2, 43.7), (2.1, 13, 1.2), STEEL, .2)
            self.lathe(c + (x, 0, 0), (1, 0, 0), ((-.55, 6.42), (.55, 6.42)), STEEL, 64)
            self.box((x, -36.15, 46.2), (1.8, 1, 2.2), STEEL, .14)
            self.bolt((x, -35.6, 46.1), (0, 1, 0), .32, SILVER)
        for x in (-14, 14):
            self.ring(c + (x, 0, 0), (1, 0, 0), 6.1, .09, SILVER, 56, 6)
        self.rod(c + (16.4, 0, 0), c + (18.8, 0, 0), 1.0, SILVER, 20)
        self.rod(c + (17.7, 0, 0), c + (17.7, 0, 2), .47, HUB, 12)
        self.ring(c + (17.7, 0, 2), (0, 0, 1), .9, .17, HUB, 16, 6)
        self.tube((c + (18.5, 0, 0), c + (19.6, 0, -1.6), c + (20, 2.5, -4), c + (17.8, 5, -6),
                   (17, -34, 39), (15, -27, 35)), .24, BLACK, 10)
        self.ring(c + (18.7, 0, 0), (1, 0, 0), 4.6, .35, SILVER, 48, 8)
        for z, y in ((4.6, 0), (-4.6, 0), (0, 4.6), (0, -4.6)):
            self.rod(c + (15.3, y, z), c + (18.7, y, z), .25, SILVER, 12)

    def mast(self):
        lift = self.lift
        extension = max(0, lift - 6)
        for s in (-1, 1):
            x = s * 14.2
            # Heavy outer C-channel and the nested sliding member.
            self.box((x + s * 1.1, 41.5, 44.2), (1.15, 5.3, 80.4), STEEL, .13)
            for y in (39.2, 43.8):
                self.box((x, y, 44.2), (4.6, .9, 80.4), STEEL, .12)
            self.box((s * 10.65, 42.5, 41.6 + extension), (2.5, 3.6, 73.2), STEEL, .13)
            self.box((s * 12.0, 40.58, 41.6 + extension), (.25, .22, 71), CHROME, .03)
            for z in (12, 32, 61, 80):
                self.bolt((s * 16, 41.6, z), (s, 0, 0), .38, SILVER)
            self.rod((s * 13.0, 40.7, 30.6), (s * 17.2, 40.7, 30.6), 2.4, STEEL, 36)
            self.bolt((s * 17.28, 40.7, 30.6), (s, 0, 0), .88, SILVER)
            a, b = np.array((s * 14.2, 28, 25)), np.array((s * 14.2, 39.5, 35))
            d = b - a
            self.rod(a, a + d * .67, 1.32, STEEL, 24)
            self.rod(a + d * .65, b, .67, CHROME, 20)
            self.ring(a + d * .64, d, 1.33, .16, SILVER, 24, 6)
            self.rod(b - (1.8, 0, 0), b + (1.8, 0, 0), 1.5, STEEL, 24)
            # Chain sheaves and actual roller-chain pins/alternating link plates.
            ztop = 79.5 + extension
            self.rod((s * 8.2, 39.9, ztop), (s * 8.2, 43.0, ztop), 2.3, HUB, 32)
            self.ring((s * 8.2, 39.84, ztop), (0, 1, 0), 1.8, .17, SILVER, 32, 6)
            self.bolt((s * 8.2, 39.6, ztop), (0, -1, 0), .6, HUB)
            zs = np.arange(lift + 15, ztop - 1.7, 1.36)
            for i, z in enumerate(zs):
                for xside in (-1, 1):
                    self.box((s * 8.2 + xside * (.43 if i % 2 else .57), 39.6, z + .61),
                             (.20, .7, 1.62), HUB, .16)
                self.rod((s * 8.2 - .65, 39.6, z), (s * 8.2 + .65, 39.6, z), .24, HUB, 10)
            for z in (lift + 16, lift + 40):
                self.rod((s * 10.4, 41, z), (s * 14.8, 41, z), 1.5, HUB, 24)
        for z in (7, 37, 82.7):
            self.box((0, 41.6, z), (29, 4.1, 2.8), STEEL, .14)
        self.box((0, 41.6, 83.8), (33.3, 6.9, 1.5), STEEL, .22)
        # Lift ram, hydraulic manifold and flexible lines visible through the mast.
        self.lathe((0, 40.3, 14.8), (0, 0, 1), ((0, 1.9), (1, 1.65), (35, 1.65), (36, 1.9)), STEEL, 32)
        self.rod((0, 40.3, 50.8), (0, 40.3, 76.7 + extension), .82, CHROME, 24)
        self.ring((0, 40.3, 50.4), (0, 0, 1), 1.78, .16, SILVER, 32, 6)
        self.box((0, 37.5, 15.2), (6.5, 3.6, 3.2), STEEL, .16)
        for x in (-4, 3, 5.5):
            self.tube(((x, 36, 15), (x - .8, 35.2, 19), (x - 1.0, 35.8, 28), (x + .6, 37.2, 39),
                       (x + 1.8, 39.0, 53), (x + 1.8, 39.5, 66)), .23, BLACK, 10)
            self.lathe((x + 1.8, 39.5, 65.5), (0, 0, 1), ((0, .39), (.9, .39)), SILVER, 6)
        # Carriage and open load backrest; these move together when the fork height changes.
        for z in (lift + 9, lift + 18):
            self.box((0, 46.3, z), (38.7, 2.5, 3.1), STEEL, .16)
        for x in (-18.7, -10, 0, 10, 18.7):
            self.box((x, 46.0, lift + 32), (1.3, 1.5, 29), STEEL, .1)
        self.box((0, 46.0, lift + 46.5), (40, 1.9, 2.0), STEEL, .14)
        for x in (-10.2, 10.2):
            self.box((x, 45, lift + 17.5), (5.5, 3.3, 3.8), STEEL, .2)
            self.bolt((x, 47.0, lift + 18.3), (0, 1, 0), .44, SILVER)
            # Tapered forged tines, with a radiused heel and slightly polished tips.
            self.box((x, 47.2, lift + 14), (4.0, 2.1, 24), STEEL, .16)
            sections = [(47.2, 3.4, .7, 2.0), (49, 2.9, .7, 2.0), (53, 2.6, .7, 2.0),
                        (81, 2.2, .7, 2.0), (89, 1.65, .72, 1.9), (94, .95, .72, 1.3)]
            rings = [np.array(((x - w, y, lift + lo), (x - w, y, lift + hi),
                               (x + w, y, lift + hi), (x + w, y, lift + lo))) for y, hi, lo, w in sections]
            for i, (a, b) in enumerate(zip(rings, rings[1:])):
                for k in range(4):
                    j = (k + 1) % 4
                    pts = (a[k], b[k], b[j], a[j])
                    self.poly(HUB if i >= 3 else STEEL, pts, -np.cross(b[k] - a[k], a[j] - a[k]))
            self.poly(HUB, rings[-1], (0, 1, 0))
        self.safety_labels()

    def safety_labels(self):
        # Small enamel warning plates: a red prohibition ring and a black person symbol.
        for s in (-1, 1):
            x = s * 16.08
            for z in (52.7, 57.4):
                self.box((x, 41.4, z), (.08, 2.4, 4.0), WHITE, .02)
                c = np.array((x + s * .06, 41.4, z))
                self.ring(c, (1, 0, 0), .95, .095, RED, 32, 6)
                self.rod(c + (s * .035, 0, .55), c + (s * .075, 0, .55), .18, BLACK, 12)
                self.rod(c + (s * .04, 0, .27), c + (s * .04, 0, -.32), .13, BLACK, 8)
                for side in (-1, 1):
                    self.rod(c + (s * .05, 0, -.20), c + (s * .05, side * .32, -.75), .09, BLACK, 6)
                self.rod(c + (s * .12, -.72, .74), c + (s * .12, .72, -.74), .09, RED, 8)

    def collision(self):
        # Keep the original blocking boxes: forks, hoses and fittings don't snag movement.
        for lo, hi in (((-22.6, -51, 0), (22.6, 39.5, 46)), ((-16.5, 39.5, 0), (16.5, 46, 80)),
                       ((-21.1, -30.1, 46), (-18.9, -27.9, 82)), ((18.9, -30.1, 46), (21.1, -27.9, 82)),
                       ((-21.1, 19, 46), (-18.9, 23.5, 82)), ((18.9, 19, 46), (21.1, 23.5, 82)),
                       ((-21.1, -30.1, 82), (21.1, 21.1, 84))):
            points = [self.p((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
            self.m.collision_box(np.min(points, axis=0), np.max(points, axis=0), "metal")

    def build(self):
        self.chassis()
        for s in (-1, 1):
            self.wheel(s, 26, 13.2, 8.2, 20.0)
            self.wheel(s, -38, 10.6, 6.3, 19.2)
        self.seat()
        self.controls()
        self.guard()
        self.gas_tank()
        self.mast()
        self.collision()
        configure(self.m)


def build(model, e, n, facing="+n", z0=0, lift=0):
    Forklift(model, e, n, facing, z0, lift).build()


def validate(model):
    for paint, faces in model.polygons.items():
        for i, (points, normal) in enumerate(faces):
            assert np.isfinite(points).all() and np.isfinite(normal).all(), (paint, i, "non-finite")
            uv = np.asarray(model.polygon_uvs[(paint, i)])
            assert np.isfinite(uv).all(), (paint, i, "UV")
            for k in range(1, len(points) - 1):
                area = np.linalg.norm(np.cross(points[k] - points[0], points[k + 1] - points[0]))
                assert area > 1e-7, (paint, i, k, "zero-area triangle")
                tangent = abs(np.linalg.det(np.array((uv[k] - uv[0], uv[k + 1] - uv[0]))))
                assert tangent > 1e-10, (paint, i, k, "collapsed UV triangle")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dress", action="store_true")
    parser.add_argument("--dress-only", action="store_true", help="update map dressing using the already-checked model")
    args = parser.parse_args()
    write_materials()
    for name, lift in (() if args.dress_only else (("forklift", 0), ("forklift_raised", 20))):
        model = K.Model()
        build(model, 0, 0, lift=lift)
        validate(model)
        count = K.write_model(MODEL_OUT, MODEL_RESOURCE, name, model)
        print(f"{name}: {count} triangles; {len(model.boxes)} cover boxes; bounds {model.bounds()}")
    ground = K.Model()
    ground.box((-450, -450, -2), (450, 450, 0), {"+z": "setts", "default": None})
    K.write_model(MODEL_OUT, MODEL_RESOURCE, "forklift_ground", ground)
    if args.dress or args.dress_only:
        import lowtide_map as LT
        for s, side in ((1, "east"), (-1, "west")):
            model = LT.configure(LT.dress_side(s))
            count = K.write_model(LT.OUT_DIR, LT.RESOURCE_DIR, f"lowtide_dress_{side}", model)
            print(f"Lowtide {side}: {count} triangles; {len(model.boxes)} boxes; {len(model.hulls)} hulls")
        assert "forklift" not in LT.R.MISSING, LT.R.MISSING


if __name__ == "__main__":
    main()
