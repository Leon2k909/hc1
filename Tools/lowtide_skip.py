"""Lowtide's welded, open builder's skip and its reference-derived steel material.

The base colour is an unchanged imagegen asset. The generated normal, roughness and
metalness images are material data derived from its paint/steel/rust regions. Small
fittings are visual detail; the skip keeps its original cover collider and location.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K
from railhead_props import outward

OUT = K.ASSETS / "materials/lowtide"
RESOURCE = "materials/lowtide"
PAINTS = {
    "lt_skip": ((1.0, 1.0, 1.0), 1.0),
    "lt_skip_end": ((1.0, 1.0, 1.0), 1.0),
    "lt_skip_inner": ((0.84, 0.85, 0.82), 1.12),
    "lt_skip_floor": ((0.61, 0.61, 0.57), 1.16),
    "lt_skip_trim": ((0.95, 0.95, 0.93), 1.0),
    "lt_skip_weld": ((0.68, 0.67, 0.64), 1.12),
}
WIDTH, LENGTH, BOTTOM, TOP = 38.0, 72.0, 4.0, 38.0


def write_materials():
    """Keep the original albedo; derive physical surface response, without baked shading."""
    OUT.mkdir(parents=True, exist_ok=True)
    # The normal/roughness compiler requires a power-of-two sampling grid.
    # Resample only the numerical input to the response maps; keep the albedo asset intact.
    sample = Image.open(OUT / "lt_skip_color.png").convert("RGB").resize((2048, 1024), Image.Resampling.LANCZOS)
    rgb = np.asarray(sample, dtype=np.float32) / 255
    h, w = rgb.shape[:2]
    r, g, b = np.moveaxis(rgb, -1, 0)
    yellow = np.clip((r - b - 0.15) * 6, 0, 1) * np.clip((g - 0.16) * 5, 0, 1)
    steel = np.clip((0.20 - (rgb.max(axis=2) - rgb.min(axis=2))) * 8, 0, 1) * (1 - yellow)
    rust = np.clip(1 - yellow - steel, 0, 1)
    rng = np.random.default_rng(7318)
    grain = ndimage.gaussian_filter(rng.normal(size=(h, w)).astype(np.float32), 0.7)
    grain /= max(grain.std(), 1e-6)
    roughness = np.clip(0.57 * yellow + 0.45 * steel + 0.86 * rust + grain * 0.025, 0.35, 0.94)
    metalness = np.clip(steel * 0.86, 0, 1)
    # Paint is about 0.2 mm thick. Rust is rougher and slightly raised; scratches expose the substrate.
    height = ndimage.gaussian_filter(yellow * 0.008 + rust * 0.025, 0.65)
    height += grain * (0.002 + 0.003 * rust)
    dy, dx = np.gradient(height)
    normal = np.dstack((-dx * w / 144.0, dy * h / 34.0, np.ones((h, w))))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    maps = {"normal": (normal * 0.5 + 0.5) * 255, "rough": roughness * 255, "metal": metalness * 255}
    for channel, data in maps.items():
        Image.fromarray(np.clip(np.rint(data), 0, 255).astype(np.uint8)).save(OUT / f"lt_skip_{channel}.png", optimize=True)
    # Contact occlusion corresponds to the actual rim and welded ribs in the mesh.
    # Its broad falloff supplies the small crevices that a map-wide shadow atlas cannot resolve.
    yy, xx = np.mgrid[:h, :w]
    x, z = (xx / (w - 1) * 2 - 1) * LENGTH, BOTTOM + (1 - yy / (h - 1)) * (TOP - BOTTOM)
    lip = np.exp(-np.abs(z - 36.25) / 2.1)
    body_ao = 1 - .37 * lip
    for rib in (-34, 0, 34):
        body_ao *= 1 - .32 * np.exp(-np.maximum(np.abs(x - rib) - 1.1, 0) / 1.1)
    diagonal = 49.2 + (z - 5.2) * (68.3 - 49.2) / (36.3 - 5.2)
    body_ao *= 1 - .24 * np.exp(-np.maximum(np.abs(np.abs(x) - diagonal) - .85, 0) / .8)
    inner_ao = (1 - .20 * lip) * (1 - .22 * np.exp(-(z - BOTTOM) / 2.0))
    for name, data in (("ao", body_ao), ("inner_ao", inner_ao)):
        Image.fromarray(np.rint(np.clip(data, .35, 1) * 255).astype(np.uint8)).save(OUT / f"lt_skip_{name}.png", optimize=True)
    for paint, (tint, rough) in PAINTS.items():
        lines = ["// Tools/lowtide_skip.py: yellow enamel, chipped steel and corrosion", '"Layer0"', "{",
                 '    shader "shaders/complex.shader"', '    F_SPECULAR "1"', '    F_METALNESS_TEXTURE "1"',
                 '    g_flAmbientOcclusionDirectDiffuse "1"', '    g_flAmbientOcclusionDirectSpecular "1"',
                 f'    g_flRoughnessScaleFactor "{rough:.3f}"', '    g_flMetalness "0"',
                 f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"', '    g_flModelTintAmount "1"']
        ao = "lt_skip_ao.png" if paint == "lt_skip" else "lt_skip_inner_ao.png" if paint in {"lt_skip_inner", "lt_skip_floor", "lt_skip_end"} else None
        lines.append(f'    TextureAmbientOcclusion "{RESOURCE}/{ao}"' if ao else '    TextureAmbientOcclusion "materials/default/default_ao.tga"')
        for parameter, channel in (("TextureColor", "color"), ("TextureNormal", "normal"),
                                   ("TextureRoughness", "rough"), ("TextureMetalness", "metal")):
            lines.append(f'    {parameter} "{RESOURCE}/lt_skip_{channel}.png"')
        K.write_text(OUT / f"{paint}.vmat", "\n".join(lines + ["}", ""]))


def configure(model):
    for paint in PAINTS:
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = 144.0


class Skip:
    def __init__(self, model, origin, along):
        self.m = model
        self.o = np.asarray(origin, float)
        self.axes = np.array(((0, 1, 0), (1, 0, 0), (0, 0, 1)) if along == "n"
                             else ((1, 0, 0), (0, 1, 0), (0, 0, 1)), float)

    def p(self, point):
        return self.o + np.asarray(point) @ self.axes

    @staticmethod
    def uv(points, normal, role):
        pts = np.asarray(points)
        if abs(normal[0]) > abs(normal[1]) and abs(normal[0]) > abs(normal[2]):
            u = (pts[:, 1] + 38) / 144 + 0.18
        else:
            u = (pts[:, 0] + 72) / 144
        v = (pts[:, 2] - BOTTOM) / (TOP - BOTTOM)
        if abs(normal[2]) > 0.8:
            if role == "floor":
                u, v = (pts[:, 0] + 52) / 104, (pts[:, 1] + 34) / 68
            else:
                v = 0.15 + 0.10 * (pts[:, 1] + 38) / 76
        elif role == "handled":
            v = 0.14 + (pts[:, 2] - 35) / 34
        elif role == "edge":
            v = 0.012 + 0.035 * np.clip((pts[:, 2] - 35) / 10, 0, 1)
        elif role == "weld":
            v = 0.015 + np.clip(v, 0, 1) * 0.025
        return list(zip(u, np.clip(v, 0.004, 0.996)))

    def poly(self, paint, points, normal, role="panel", normals=None, uv=None):
        normal = K.normalise(np.asarray(normal, float))
        coords = np.clip(self.uv(points, normal, role) if uv is None else uv, .001, .999)
        if np.linalg.matrix_rank(coords[1:] - coords[0], tol=1e-10) < 2:
            # A thin bevel at the base can reach the texture border. Keep its tangent basis valid.
            flat = [i for i in range(3) if i != int(np.argmax(np.abs(normal)))]
            values = np.asarray(points)[:, flat]
            coords = (.28, .83) + (values - values.min(axis=0)) / (144, 34)
        outward(self.m, paint, [self.p(q) for q in points], normal @ self.axes,
                uv=np.clip(coords, .001, .999),
                normals=None if normals is None else [np.asarray(n) @ self.axes for n in normals])

    def box(self, centre, size, paint="lt_skip", bevel=0.12, axes=None, role="panel"):
        """Solid steel part with six faces, twelve bevels and eight bevelled corners."""
        c, half = np.asarray(centre, float), np.asarray(size, float) / 2
        axes = np.eye(3) if axes is None else np.asarray(axes, float)
        bevel = min(bevel, float(half.min()) * 0.7)

        def draw(points, normal, chamfer=False):
            coords = None
            if role in {"handled", "foot"} and not chamfer:
                # Small fittings need their own texel scale, including the rim's narrow top face.
                facing = int(np.argmax(np.abs(normal)))
                other = [i for i in range(3) if i != facing]
                u_axis = max(other, key=lambda i: half[i])
                v_axis = next(i for i in other if i != u_axis)
                u_span = max(144.0, half[u_axis] * 2)
                base_v = .76 if role == "foot" else .14
                coords = [((q[u_axis] + half[u_axis]) / u_span,
                           base_v + (q[v_axis] + half[v_axis]) / 34) for q in points]
            self.poly(paint, [c + np.asarray(p) @ axes for p in points], np.asarray(normal) @ axes,
                      "edge" if chamfer and role in {"handled", "foot"} else role, uv=coords)

        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            for sign in (-1, 1):
                points = []
                for sj, sk in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    q = np.zeros(3)
                    q[i], q[j], q[k] = sign * half[i], sj * (half[j] - bevel), sk * (half[k] - bevel)
                    points.append(q)
                normal = np.zeros(3); normal[i] = sign
                draw(points, normal)
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            for sj in (-1, 1):
                for sk in (-1, 1):
                    points = []
                    for si, near_j in ((-1, True), (1, True), (1, False), (-1, False)):
                        q = np.zeros(3)
                        q[i] = si * (half[i] - bevel)
                        q[j] = sj * (half[j] if near_j else half[j] - bevel)
                        q[k] = sk * (half[k] - bevel if near_j else half[k])
                        points.append(q)
                    normal = np.zeros(3); normal[j], normal[k] = sj, sk
                    draw(points, normal, True)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    signs = np.array((sx, sy, sz), float)
                    draw([signs * (half - bevel) + signs * np.eye(3)[i] * bevel for i in range(3)], signs, True)

    def beam(self, a, b, width, depth, normal, paint="lt_skip", role="panel"):
        a, b, normal = np.asarray(a, float), np.asarray(b, float), np.asarray(normal, float)
        z = K.normalise(b - a)
        y = K.normalise(normal - z * np.dot(normal, z))
        x = K.normalise(np.cross(y, z))
        self.box((a + b) / 2, (width, depth, np.linalg.norm(b - a)), paint,
                 axes=(x, y, z), bevel=0.10, role=role)

    def weld(self, a, b, radius=0.065):
        """A shallow, continuous raised weld; the response map supplies the fine pitting."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        along = K.normalise(b - a)
        side = np.cross(along, (0, 0, 1))
        if np.linalg.norm(side) < 1e-6:
            side = np.cross(along, (1, 0, 0))
        side = K.normalise(side)
        up = np.cross(along, side)
        dirs = [side * math.cos(t) + up * math.sin(t) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
        # Slightly vary the bead instead of using a perfectly straight dark line.
        segments = max(2, int(np.linalg.norm(b - a) / 3.6))
        for i in range(segments):
            aa, bb = a + (b - a) * i / segments, a + (b - a) * (i + 1) / segments
            ra, rb = radius * (1 + .11 * math.sin(i * 2.4)), radius * (1 + .11 * math.sin((i + 1) * 2.4))
            for k, d in enumerate(dirs):
                q = dirs[(k + 1) % len(dirs)]
                self.poly("lt_skip_weld", (aa + d * ra, aa + q * ra, bb + q * rb, bb + d * rb),
                          d + q, "weld", (d, q, q, d))

    def panel(self, end, sign):
        """An 8 mm steel plate, with a separate inside face and subtle broad dents."""
        def at(u, v, inner=False):
            z = BOTTOM + v * (TOP - BOTTOM)
            length, width = 52 + 20 * v, 34 + 4 * v
            dent = -0.17 * math.exp(-((u - .27) / .18) ** 2 - ((v - .43) / .23) ** 2)
            if end:
                return np.array((sign * (length - (.37 if inner else 0) + dent), (2 * u - 1) * (width - (.35 if inner else 0)), z))
            return np.array(((2 * u - 1) * (length - (.37 if inner else 0)), sign * (width - (.35 if inner else 0) + dent), z))

        direction = np.array((sign, 0, -20 / 34) if end else (0, sign, -4 / 34))

        def normal(u, v, inner):
            n = K.normalise(np.cross(at(u + .0001, v, inner) - at(u - .0001, v, inner),
                                     at(u, v + .0001, inner) - at(u, v - .0001, inner)))
            if np.dot(n, direction) < 0:
                n = -n
            return -n if inner else n

        us, vs = np.linspace(0, 1, 13 if not end else 7), np.linspace(0, 1, 7)
        for inner in (False, True):
            for u0, u1 in zip(us, us[1:]):
                for v0, v1 in zip(vs, vs[1:]):
                    coords = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
                    normals = [normal(u, v, inner) for u, v in coords]
                    self.poly("lt_skip_inner" if inner else "lt_skip_end" if end else "lt_skip", [at(u, v, inner) for u, v in coords],
                              sum(normals), normals=normals)
        for axis, value in ((0, 0), (0, 1), (1, 0), (1, 1)):
            seq = vs if axis == 0 else us
            for p, q in zip(seq, seq[1:]):
                uv0, uv1 = ((value, p), (value, q)) if axis == 0 else ((p, value), (q, value))
                pts = (at(*uv0), at(*uv1), at(*uv1, True), at(*uv0, True))
                if axis == 1:
                    towards = (0, 0, -1 if value == 0 else 1)
                else:
                    towards = (0, -1 if value == 0 else 1, 0) if end else (-1 if value == 0 else 1, 0, 0)
                self.poly("lt_skip_trim", pts, towards)

    def eye(self, x, y):
        """A thick rounded lifting plate with a genuinely open, bevelled hole."""
        centre = np.array((x, y, 42.0))
        segments, thickness, bevel = 40, .82, .10
        angles = np.linspace(0, 2 * math.pi, segments, endpoint=False)
        outer = [np.array((2.25 * math.copysign(abs(math.cos(t)) ** .5, math.cos(t)),
                           0, 2.05 * math.copysign(abs(math.sin(t)) ** .5, math.sin(t)))) for t in angles]
        inner = [np.array((1.25 * math.cos(t), 0, 1.25 * math.sin(t))) for t in angles]
        for i in range(segments):
            j = (i + 1) % segments
            for side in (-1, 1):
                d = np.array((0, side * thickness / 2, 0))
                oi, oj = outer[i] * .955, outer[j] * .955
                ii, ij = inner[i] * 1.08, inner[j] * 1.08
                self.poly("lt_skip_trim", (centre + d + oi, centre + d + oj, centre + d + ij, centre + d + ii), (0, side, 0), "handled")
                d2 = np.array((0, side * (thickness / 2 - bevel), 0))
                self.poly("lt_skip_trim", (centre + d + oi, centre + d + oj, centre + d2 + outer[j], centre + d2 + outer[i]),
                          (0, side, 0), "handled")
                self.poly("lt_skip_trim", (centre + d + ii, centre + d + ij, centre + d2 + inner[j], centre + d2 + inner[i]),
                          (0, side, 0), "handled")
            d = np.array((0, thickness / 2 - bevel, 0))
            self.poly("lt_skip_trim", (centre - d + outer[i], centre - d + outer[j], centre + d + outer[j], centre + d + outer[i]),
                      outer[i] + outer[j], "handled")
            self.poly("lt_skip_weld", (centre - d + inner[i], centre - d + inner[j], centre + d + inner[j], centre + d + inner[i]),
                      -inner[i] - inner[j], "handled")
        self.box((x, y, 39.65), (5.2, 2.2, .65), "lt_skip_trim", role="handled")

    def build(self):
        # Four welded plates and a real dirty steel floor replace the former rubble cap.
        self.box((0, 0, 4.0), (104, 68, .8), "lt_skip_floor", bevel=.08, role="floor")
        for sign in (-1, 1):
            self.panel(False, sign)
            self.panel(True, sign)
        # Rolled hollow-section rim, with softly rounded external corners.
        for y in (-38.0, 38.0):
            self.box((0, y, 38.2), (148, 3.0, 3.5), "lt_skip_trim", bevel=.18, role="handled")
        for x in (-72.0, 72.0):
            self.box((x, 0, 38.2), (3.0, 73.0, 3.5), "lt_skip_trim", bevel=.18, role="handled")
        for sign in (-1, 1):
            normal = K.normalise((0, sign, -4 / 34))
            for x in (-34.0, 0.0, 34.0):
                a, b = np.array((x, sign * 34.6, 4.7)), np.array((x, sign * 38.35, 36.8))
                self.beam(a, b, 2.5, 1.0, normal, "lt_skip_trim")
                for dx in (-1.32, 1.32):
                    self.weld(a + (dx, 0, 0), b + (dx, 0, 0), .055)
                # Short reinforcing collar embraces the rim, as in the reference.
                self.beam((x, sign * 38.14, 31.5), (x, sign * 39.1, 39.4), 4.3, .75, normal,
                          "lt_skip_trim", "handled")
            # Diagonal strips brace both sloping ends of each long side.
            for end in (-1, 1):
                a, b = np.array((end * 49.2, sign * 34.6, 5.2)), np.array((end * 68.3, sign * 38.25, 36.3))
                self.beam(a, b, 1.9, .58, normal)
                self.weld(a + (end * 1.03, 0, 0), b + (end * 1.03, 0, 0), .05)
                self.eye(end * 69.5, sign * 36.9)
            # Visible lower plate weld, deliberately raised rather than overlapping cards.
            z = 10.3
            v = (z - BOTTOM) / (TOP - BOTTOM)
            y, length = sign * (34 + 4 * v + .055), 52 + 20 * v
            self.weld((-length + .5, y, z), (length - .5, y, z), .055)
            # Corner welds inside the open skip.
            for end in (-1, 1):
                self.weld((end * 51.5, sign * 33.65, 4.7), (end * 71.4, sign * 37.65, 36.4), .07)
        # Four squat support feet; no floating bottom or paper-thin silhouette.
        for x in (-39.0, 39.0):
            for y in (-25.5, 25.5):
                self.box((x, y, 2.15), (8.8, 7.5, 4.3), "lt_skip_trim", bevel=.22, role="foot")
                self.weld((x - 4.4, y - 3.8, 3.8), (x + 4.4, y - 3.8, 3.8), .075)
        # Original AABB remains the gameplay cover. Rim, lugs and welds are visual fittings.
        corners = [self.p((x, y, z)) for x in (-LENGTH, LENGTH) for y in (-WIDTH, WIDTH) for z in (0, TOP)]
        self.m.collision_box(np.min(corners, axis=0), np.max(corners, axis=0), "metal")


def build(model, origin, along="n"):
    Skip(model, origin, along).build()


if __name__ == "__main__":
    write_materials()
    print("wrote Lowtide skip materials")
