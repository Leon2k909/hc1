"""Reusable mechanical lever frame for Railhead's glazed signal cabin.

Inches, local X across the frame, +Y towards its operator, Z above the floor.
Keep the ImageGen albedo source; rebuild with this script, not a room photograph.
The cabinet, mechanisms, indicators and lamps share one opaque PBR atlas.
"""

from contextlib import contextmanager
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import map_kit as K
import railhead_props as P
from railhead_buffer import bevel_box


RESOURCE = "models/props/railhead/signal_frame"
OUT = K.ASSETS / RESOURCE
MODEL = f"{RESOURCE}/signal_frame.vmdl"
TEX = "materials/railhead/signal_frame"
MATERIALS = K.ASSETS / TEX
BODY, LABEL, AMBER, BULB = (f"rw_signal_frame_{s}" for s in ("body", "labels", "amber", "bulb"))
GREEN, RED, YELLOW, IVORY, IRON, STEEL, WOOD, BLACK = range(8)
F = P.Frame((0, 0, 0), (0, 1))
POSITION = (-16, -2160, 130)
LEVER_PITCH = 7.1
PALETTE = (BLACK, BLACK, RED, RED, BLACK, YELLOW, IVORY, RED, RED,
           YELLOW, YELLOW, IVORY, BLACK, YELLOW, IVORY, RED, RED, BLACK,
           IVORY, YELLOW, IVORY, RED, RED, BLACK, YELLOW, RED, BLACK)


def unit(v):
    v = np.asarray(v, float)
    return v / max(1e-9, np.linalg.norm(v))


def local(p):
    return np.array((np.dot(p, F.x), np.dot(p, F.y), np.dot(p, F.z)))


def atlas_uv(cell, coords):
    col, row = int(cell) % 4, int(cell) // 4
    # Cell-specific gutters prevent neighbouring colours bleeding in mipmaps.
    gu, gv = 8 / 2048, 8 / 1024
    return [(col / 4 + gu + np.clip(u, 0, 1) * (.25 - 2 * gu),
             1 - (row + 1) / 2 + gv + np.clip(v, 0, 1) * (.5 - 2 * gv)) for u, v in coords]


class AtlasModel(K.Model):
    def __init__(self):
        super().__init__()
        self.part_bounds = None
        self.material_overrides.update({s: f"{TEX}/{s}.vmat" for s in (BODY, LABEL, AMBER, BULB)})
        self.tile_overrides.update({s: 1 for s in (BODY, LABEL, AMBER, BULB)})

    @contextmanager
    def part(self, lo, hi):
        previous = self.part_bounds
        self.part_bounds = (np.asarray(lo, float), np.asarray(hi, float))
        try:
            yield
        finally:
            self.part_bounds = previous

    def polygon(self, paint, points, normal=None, both_sides=False, uv=None, normals=None):
        if isinstance(paint, (int, np.integer)):
            if uv is None:
                pts = np.array([local(p) for p in points])
                n = local(normal) if normal is not None else np.cross(pts[1] - pts[0], pts[2] - pts[0])
                remaining = [j for j in range(3) if j != int(np.argmax(np.abs(n)))]
                lo, hi = self.part_bounds if self.part_bounds else (pts.min(axis=0), pts.max(axis=0))
                b = 2 if 2 in remaining else remaining[1]
                a = next(j for j in remaining if j != b)
                # No stretching a square scan into stripes on slender shafts.
                span = max(.01, hi[a] - lo[a], hi[b] - lo[b])
                phase = abs(math.sin(float(np.dot(lo, (.731, .391, 1.117))) + int(paint) * .37))
                offsets = ((1 - (hi[a] - lo[a]) / span) * phase,
                           (1 - (hi[b] - lo[b]) / span) * (1 - phase))
                uv = [((p[a] - lo[a]) / span + offsets[0], (p[b] - lo[b]) / span + offsets[1]) for p in pts]
            uv, paint = atlas_uv(paint, uv), BODY
        return super().polygon(paint, points, normal, both_sides, uv, normals)


def box(m, lo, hi, paint, bevel=.10):
    with m.part(lo, hi):
        if min(np.asarray(hi) - lo) < .25:
            F.box(m, *[v for pair in zip(lo, hi) for v in pair], paint)
        else:
            bevel_box(m, F, lo, hi, paint, bevel)


def lathe(m, centre, axis, profile, paint, sides=16, caps=True):
    """Smooth turned metal with a real curved profile, including rounded grips."""
    c, ax = np.asarray(centre, float), unit(axis)
    r = unit(np.cross(ax, np.eye(3)[np.argmin(np.abs(ax))]))
    u = np.cross(ax, r)
    radius = max(p[1] for p in profile)
    a, b = c + ax * profile[0][0], c + ax * profile[-1][0]
    with m.part(np.minimum(a, b) - radius, np.maximum(a, b) + radius):
        for j in range(len(profile) - 1):
            for i in range(sides):
                pts, ns = [], []
                for k, q in ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)):
                    t, rad = profile[k]
                    ring = math.cos(q * math.tau / sides) * r + math.sin(q * math.tau / sides) * u
                    before, after = profile[max(k - 1, 0)], profile[min(k + 1, len(profile) - 1)]
                    n = unit(ring * (after[0] - before[0]) - ax * (after[1] - before[1]))
                    pts.append(F.p(*(c + ax * t + ring * rad)))
                    ns.append(F.x * n[0] + F.y * n[1] + F.z * n[2])
                P.outward(m, paint, pts, sum(ns), normals=ns)
        if caps:
            for j, sign in ((0, -1), (-1, 1)):
                t, rad = profile[j]
                ring = [F.p(*(c + ax * t + rad * (r * math.cos(q * math.tau / sides) + u * math.sin(q * math.tau / sides)))) for q in range(sides)]
                P.outward(m, paint, ring, (F.x * ax[0] + F.y * ax[1] + F.z * ax[2]) * sign)


def tube(m, a, b, radius, paint, sides=12):
    a, b = np.asarray(a, float), np.asarray(b, float)
    lathe(m, a, b - a, [(0, radius), (float(np.linalg.norm(b - a)), radius)], paint, sides)


def screw(m, centre, radius=.22, axis=(0, 1, 0), steel=True):
    c, n = np.asarray(centre, float), unit(axis)
    lathe(m, c, n, [(0, radius), (.17, radius * .82)], STEEL if steel else IRON, 8)
    if radius >= .2:
        # The screwdriver slot has depth and remains dark under highlights.
        a = unit(np.cross(n, np.eye(3)[np.argmin(np.abs(n))]))
        b = np.cross(n, a)
        c = c + n * .176
        P.quad(m, BLACK, F.p(*c), F.x * a[0] + F.y * a[1] + F.z * a[2],
               F.x * b[0] + F.y * b[1] + F.z * b[2], radius * 1.2, .06)


def plate(m, number, x, y, z):
    box(m, (x - 2.05, y - .2, z - 1.9), (x + 2.05, y, z + 1.9), IRON, .12)
    index = number - 1
    col, row = index % 8, index // 8
    u0, u1 = (col * 256 + 8) / 2048, ((col + 1) * 256 - 8) / 2048
    v0, v1 = 1 - ((row + 1) * 256 - 8) / 1024, 1 - (row * 256 + 8) / 1024
    # Frame X points to screen right: text is upright on the operating side.
    F.quad(m, LABEL, x, y + .012, z, 3.9, 3.6, uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def sector(m, x, side):
    """Cast curved quadrant cheeks, separate from the swinging lever and latch."""
    xx = x + side * 2.25
    # Annular sector in the YZ plane, extruded in X, with polished running edge.
    cy, cz, inner, outer = -1.3, 28.2, 3.15, 4.5
    angles = np.linspace(math.radians(22), math.radians(156), 13)
    for a, b in zip(angles[:-1], angles[1:]):
        yz = [(cy + rad * math.cos(t), cz + rad * math.sin(t))
              for rad, t in ((inner, a), (outer, a), (outer, b), (inner, b))]
        with m.part((xx - .34, -6, 28), (xx + .34, 4, 33)):
            for at, sign in ((xx - .34, -1), (xx + .34, 1)):
                P.outward(m, IRON, [F.p(at, y, z) for y, z in yz], F.x * sign)
            # Only the inner and outer running edges; adjacent wedges share
            # their end planes and do not need hidden internal geometry.
            for q in (1, 3):
                r = (q + 1) % 4
                pts = [F.p(at, *yz[k]) for at, k in ((xx - .34, q), (xx + .34, q), (xx + .34, r), (xx - .34, r))]
                normal = (F.y * math.cos((a + b) / 2) + F.z * math.sin((a + b) / 2)) * (1 if q == 1 else -1)
                P.outward(m, STEEL if q == 1 else IRON, pts, normal)
    for a, sign in ((angles[0], 1), (angles[-1], -1)):
        pts = [F.p(at, cy + rad * math.cos(a), cz + rad * math.sin(a))
               for at, rad in ((xx - .34, inner), (xx + .34, inner), (xx + .34, outer), (xx - .34, outer))]
        P.outward(m, IRON, pts, (F.y * math.sin(a) - F.z * math.cos(a)) * sign)
    box(m, (xx - .5, -6.3, 28), (xx + .5, 5.6, 29.5), IRON)
    for y in (-5.7, 4.9):
        screw(m, (xx, y, 29.55), .20, (0, 0, 1))


def lever(m, k, x, paint):
    # A few operated levers break the uniform picket-fence appearance.
    tilt = -6.0 if k in (4, 12, 23) else 4.2 if k in (8, 19) else 0
    axis = unit((0, tilt, 41.5))
    pivot = np.array((x, -.5, 29.3))
    for side in (-1, 1):
        sector(m, x, side)
    lathe(m, (x, -.5, 29.7), (1, 0, 0), [(-2.7, .9), (2.7, .9)], STEEL, 12)
    # The root is a forged taper, rather than two disconnected cylinders.
    lathe(m, pivot, axis, [(0, 1.02), (18.5, .97), (19.3, .68), (33.4, .66)], paint, 16)
    lathe(m, pivot, axis, [(33.3, .65), (33.7, .83), (40.7, .83), (41.2, .70), (41.55, .38)], STEEL, 20)
    latch = pivot + np.array((1.05, 1.04, 0))
    tube(m, latch + axis * 1.2, latch + axis * 37.1, .19, STEEL, 8)
    end = latch + axis * 37.1
    box(m, end - (.48, .8, .4), end + (.48, .8, 1.65), STEEL, .18)
    box(m, (x - 1.65, 3.5, 28.0), (x + 1.65, 6.9, 28.75), IRON)
    box(m, (x - .60, 2.9, 28.75), (x + .60, 7.9, 29.18), STEEL)
    for y in (4.0, 6.4):
        screw(m, (x, y, 29.19), .23, (0, 0, 1))
    # Thin physical shafts also stop projectiles; cabinet collision covers feet.
    top = pivot + axis * 41.55
    F.collide(m, x - 1.25, x + 1.5, min(pivot[1], top[1]) - 1,
              max(pivot[1], top[1]) + 1.4, 28, 71, "metal")


def cabinet(m):
    # The first three mechanisms must clear the adjoining operating desk.
    box(m, (-100, -12, 0), (100, 10, 27.5), GREEN, .45)
    # Short cast cover plates keep the scanned paint at the same physical
    # scale as the doors; one six-metre UV island made the grain look cloudy.
    for lo, hi in (((-101, -13, 26.4), (-96.0, 11.3, 28)),
                   ((96.0, -13, 26.4), (101, 11.3, 28)),
                   ((-96.0, -13, 26.4), (96.0, -11.9, 28)),
                   ((-96.0, 10.2, 26.4), (96.0, 11.3, 28))):
        box(m, lo, hi, GREEN, .18)
    box(m, (-100.2, 9.9, 1.1), (100.2, 10.65, 3), IRON)
    box(m, (-100.2, 10.0, 25.0), (100.2, 10.72, 26.4), GREEN)
    # Separate access panels, recessed dark seams and restrained rim wear.
    spacing = LEVER_PITCH
    for k in range(27):
        x = (k - 13) * spacing
        box(m, (x - 3.52, -11.95, 26.65), (x + 3.52, 10.25, 28), GREEN, .12)
        box(m, (x - 3.36, 10.01, 3.3), (x + 3.36, 10.49, 25), GREEN, .16)
        plate(m, 27 - k, x, 10.59, 22.0)
        for dx in (-2.85, 2.85):
            for z in (4.4, 18.4, 24.3):
                screw(m, (x + dx, 10.51, z), .17)
        if k in (0, 9, 18, 26):
            box(m, (x - 2.6, 10.52, 4.7), (x + 2.6, 10.75, 8.0), IRON)
            for z in np.linspace(5.2, 7.5, 5):
                box(m, (x - 2.25, 10.76, z), (x + 2.25, 10.94, z + .14), GREEN)
        lever(m, k, x, PALETTE[k])
    F.collide(m, -101, 101, -13, 11.3, 0, 28, "metal")


def annunciators(m):
    for k, x in enumerate((-78, -39, 0, 39, 78)):
        tube(m, (x, -8, 96.3), (x, -8, 108), .34, BLACK, 10)
        lathe(m, (x, -8, 107.5), (0, 0, 1), [(0, .8), (.5, .8)], STEEL, 12)
        box(m, (x - 18.2, -13, 79), (x + 18.2, -6, 97), GREEN, .65)
        box(m, (x - 16.6, -6.05, 80.9), (x + 16.6, -5.6, 95.1), BLACK, .10)
        for lo, hi in (((x - 18, -6, 79), (x + 18, -5.1, 81)),
                       ((x - 18, -6, 95), (x + 18, -5.1, 97)),
                       ((x - 18, -6, 81), (x - 16.5, -5.1, 95)),
                       ((x + 16.5, -6, 81), (x + 18, -5.1, 95))):
            box(m, lo, hi, GREEN, .15)
        for j in range(3):
            xx = x - 10.6 + j * 10.6
            box(m, (xx - 1.75, -5.5, 83), (xx + 1.75, -5.16, 93.8), IVORY, .08)
            box(m, (xx - .48, -5.15, 84.1), (xx + .48, -5.06, 92.8), IRON, .025)
            z = 84.2 + ((k + j * 2) % 4) * .85
            box(m, (xx - .32, -5.05, z), (xx + .32, -4.94, z + 3.6), AMBER, .03)
            for zz in (83.55, 93.3):
                screw(m, (xx, -5.13, zz), .11, steel=False)
        for dx in (-17.15, 17.15):
            for z in (80, 96):
                screw(m, (x + dx, -5.05, z), .25)
        F.collide(m, x - 18.2, x + 18.2, -13, -5, 79, 97, "metal")


def pendants(m):
    for e, n in ((30, -1960), (35, -2040), (20, -2120)):
        # Convert the old absolute placements into this asset's local frame.
        x, y = POSITION[0] - e, n - POSITION[1]
        tube(m, (x, y, 92), (x, y, 107), .27, BLACK, 10)
        lathe(m, (x, y, 92), (0, 0, 1), [(0, 1.0), (1, 1.55), (3.2, 1.55), (3.6, .8)], GREEN, 24)
        # A curved spun shade, with its actual cream enamel underside.
        outer = [(85.5, 8.1), (86.0, 8.1), (87.2, 7.5), (89.1, 5.95), (90.7, 4.2), (91.9, 2.25), (92.3, 1.6)]
        lathe(m, (x, y, 0), (0, 0, 1), outer, GREEN, 32, False)
        inner = [(z - .15, r - .17) for z, r in reversed(outer)]
        lathe(m, (x, y, 0), (0, 0, 1), inner, IVORY, 32, False)
        lathe(m, (x, y, 0), (0, 0, 1), [(85.5, 7.9), (85.5, 8.13), (85.9, 8.13)], GREEN, 32, False)
        lathe(m, (x, y, 87.1), (0, 0, 1), [(0, .72), (2.1, .72), (2.4, 1.0)], IRON, 16)
        lathe(m, (x, y, 82.6), (0, 0, 1), [(0, .12), (.3, .7), (1.0, 1.27), (2.2, 1.50), (3.3, 1.25), (4.3, .68), (4.6, .55)], BULB, 24)


def build():
    m = AtlasModel()
    cabinet(m)
    annunciators(m)
    pendants(m)
    return m


def materials():
    MATERIALS.mkdir(parents=True, exist_ok=True)
    source = MATERIALS / "signal_frame_source.png"
    rgb = np.array(Image.open(source).convert("RGB").resize((2048, 1024), Image.Resampling.LANCZOS), np.float32) / 255
    rough, metal, ao = [np.ones((1024, 2048), np.float32) for _ in range(3)]
    normal = np.zeros((1024, 2048, 3), np.float32)
    normal[:, :, 2] = 1
    for k in range(8):
        xs, ys = slice(k % 4 * 512, (k % 4 + 1) * 512), slice(k // 4 * 512, (k // 4 + 1) * 512)
        tile = rgb[ys, xs]
        if k == GREEN:
            tile[:] *= (1.09, 1.13, 1.06)
        if k == STEEL:
            # Nickel is bright enough to pick up the real room reflections.
            tile[:] = np.clip(tile * 1.27, 0, .85)
        if k == BLACK:
            tile[:] *= .65
        lum = tile @ np.array((.2126, .7152, .0722))
        blur = np.array(Image.fromarray(np.uint8(np.clip(lum, 0, 1) * 255)).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
        detail = lum - blur
        rough[ys, xs] = np.clip((.55, .46, .5, .51, .67, .39, .70, .52)[k] + detail * .4, .23, .9)
        metal[ys, xs] = (.03, .02, .02, .01, .72, .94, 0, .10)[k]
        gy, gx = np.gradient(lum * .025 + detail * .055)
        n = np.stack((-gx * 5, gy * 5, np.ones_like(gx)), axis=-1)
        normal[ys, xs] = n / np.linalg.norm(n, axis=-1, keepdims=True)
        ao[ys, xs] = np.clip(1 + np.minimum(detail, 0) * .7, .87, 1)
    Image.fromarray(np.uint8(np.clip(rgb, 0, 1) * 255)).save(MATERIALS / "frame_color.png")
    Image.fromarray(np.uint8((normal * .5 + .5) * 255)).save(MATERIALS / "frame_normal.png")
    for name, values in (("roughness", rough), ("metalness", metal), ("ao", ao)):
        Image.fromarray(np.uint8(np.clip(values, 0, 1) * 255)).save(MATERIALS / f"frame_{name}.png")
    K.write_text(MATERIALS / f"{BODY}.vmat", f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_METALNESS_TEXTURE "1"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
    g_flRoughnessScaleFactor "1"
    TextureColor "{TEX}/frame_color.png"
    TextureNormal "{TEX}/frame_normal.png"
    TextureRoughness "{TEX}/frame_roughness.png"
    TextureMetalness "{TEX}/frame_metalness.png"
    TextureAmbientOcclusion "{TEX}/frame_ao.png"
}}
''')
    labels()
    for name, colour, brightness in ((AMBER, (255, 187, 27), 5), (BULB, (255, 217, 153), 6)):
        # Use the same albedo-driven emission as Railhead's working lamps.
        # The uniform default-colour texture made the original bulbs look dull.
        Image.new("RGB", (32, 32), colour).save(MATERIALS / f"{name}_color.png")
        K.write_text(MATERIALS / f"{name}.vmat", f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_SELF_ILLUM "1"
    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"
    g_flSelfIllumBrightness "{brightness}"
    g_flSelfIllumAlbedoFactor "1.0"
    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1.0"
    g_flMetalness "0"
    g_flRoughnessScaleFactor "0.3"
    TextureColor "{TEX}/{name}_color.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "materials/default/default_rough.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
''')


def labels():
    image = Image.new("RGB", (2048, 1024), (222, 211, 185))
    d = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(K.ASSETS / "fonts/Dinish-Regular.ttf"), 154)
    for k in range(27):
        x, y = k % 8 * 256, k // 8 * 256
        d.rounded_rectangle((x + 8, y + 8, x + 248, y + 248), radius=15, fill=(207, 198, 173), outline=(87, 77, 55), width=3)
        d.rounded_rectangle((x + 14, y + 14, x + 242, y + 242), radius=12, fill=(226, 217, 195))
        # Fine uneven enamel patina, without baking dramatic directional light.
        rng = np.random.default_rng(572 + k)
        for _ in range(150):
            px, py = int(rng.integers(x + 17, x + 239)), int(rng.integers(y + 17, y + 239))
            d.point((px, py), fill=(177, 166, 140))
        text = str(k + 1)
        bb = d.textbbox((0, 0), text, font=font)
        d.text((x + (256 - bb[2]) / 2, y + (256 - (bb[3] - bb[1])) / 2 - bb[1]), text, font=font, fill=(24, 24, 19))
    image.save(MATERIALS / "frame_labels.png")
    K.write_text(MATERIALS / f"{LABEL}.vmat", f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_vColorTint "[1 1 1 1]"
    g_flMetalness "0"
    g_flRoughnessScaleFactor "0.55"
    TextureColor "{TEX}/frame_labels.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "materials/default/default_rough.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
''')


def scene_group():
    from railhead_map import ids
    key = "signal-frame"
    return K.game_object(ids, "Mechanical Signal Frame", key, K.to_world(POSITION), components=[
        K.component(ids, "Sandbox.ModelRenderer", key + "/renderer", Model=MODEL, RenderType="On", Tint="1,1,1,1", BodyGroups=18446744073709551615),
        K.component(ids, "Sandbox.ModelCollider", key + "/collider", Model=MODEL, IsTrigger=False, Static=True),
    ])


def placed_collisions():
    source, m = build(), K.Model()
    offset = np.array(POSITION)
    for centre, axes, size, surface in source.boxes:
        m.boxes.append((centre + offset, axes, size, surface))
    return m


def missing():
    return not (K.ASSETS / MODEL).exists() or any(not (MATERIALS / f"{s}.vmat").exists() for s in (BODY, LABEL, AMBER, BULB))


def write():
    materials()
    model = build()
    count = K.write_model(OUT, RESOURCE, "signal_frame", model)
    print(f"Signal frame: {count:,} triangles, {len(model.polygons)} materials, {len(model.boxes)} collision boxes")
    return model


if __name__ == "__main__":
    write()
