"""Reference-matched kiosk payment terminal, in inches and the kiosk's local frame.

    rtk python Tools/railhead_card_reader.py

Writes its three materials and shared 2048px atlas. The kiosk calls build() so
the detailed reader is included in all three station dressing models. No scene
objects or gameplay components are needed.
"""
import argparse
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Assets/materials/railhead"
SIZE = 2048
PLASTIC = "rw_card_reader"
METAL = "rw_card_reader_metal"
SCREEN = "rw_card_reader_screen"
RECTS = {
    "screen": (32, 32, 1056, 800),
    "body": (1088, 32, 1600, 544),
    "steel": (1632, 32, 2016, 544),
    "tap": (1088, 576, 1520, 880),
    "insert": (1568, 576, 1840, 880),
    "glass": (1880, 576, 2016, 880),
    "base": (1480, 944, 1992, 1456),
    "black": (1480, 1504, 1992, 2016),
}
KEYS = (("1", "2", "3", "more"), ("4", "5", "6", "back"),
        ("7", "8", "9", "receipt"), ("cancel", "0", None, "accept"))
for row, names in enumerate(KEYS):
    for col, name in enumerate(names):
        if name is not None:
            RECTS[name] = (32 + col * 352, 920 + row * 216,
                           352 + col * 352, 1104 + row * 216)

# Leave enough room for each entry's repeated edge texels at every mip level.
for i, (name, a) in enumerate(RECTS.items()):
    for other, b in list(RECTS.items())[i + 1:]:
        assert a[2] + 16 <= b[0] or b[2] + 16 <= a[0] or a[3] + 16 <= b[1] or b[3] + 16 <= a[1], (name, other)


def rect_uv(name):
    x0, y0, x1, y1 = RECTS[name]
    return x0 / SIZE, 1 - y1 / SIZE, x1 / SIZE, 1 - y0 / SIZE


def _uv(name, x, z):
    u0, v0, u1, v1 = rect_uv(name)
    return u0 + x * (u1 - u0), v0 + z * (v1 - v0)


def _outline(x0, x1, z0, z1, radius, steps=5):
    """A counterclockwise rounded rectangle and its outward normals in x/z."""
    radius = min(radius, (x1 - x0) / 2, (z1 - z0) / 2)
    points, normals = [], []
    for cx, cz, start in ((x1 - radius, z0 + radius, -90),
                           (x1 - radius, z1 - radius, 0),
                           (x0 + radius, z1 - radius, 90),
                           (x0 + radius, z0 + radius, 180)):
        for step in range(steps + 1):
            angle = math.radians(start + step * 90 / steps)
            nx, nz = math.cos(angle), math.sin(angle)
            points.append((cx + radius * nx, cz + radius * nz))
            normals.append((nx, nz))
    return points, normals


def _solid(model, F, place, angle, bounds, radius, bevel, entry="body",
           paint=PLASTIC, side_entry=None):
    """Rounded extrusion with real chamfers, smooth corners and explicit UVs."""
    import railhead_props as P
    x0, x1, y0, y1, z0, z1 = bounds
    bevel = min(bevel, (y1 - y0) / 2, radius * .8)
    rings = []
    for y, inset in ((y0, bevel), (y0 + bevel, 0), (y1 - bevel, 0), (y1, bevel)):
        points, normals = _outline(x0 + inset, x1 - inset, z0 + inset, z1 - inset, radius - inset)
        rings.append((y, inset, points, normals))

    def normal(nx, ny, nz):
        return P._world(F, P._lean((nx, ny, nz), angle))

    for a, b in zip(rings, rings[1:]):
        ya, ia, pa, na = a
        yb, ib, pb, nb = b
        dy, dr = yb - ya, ia - ib
        length = math.hypot(dy, dr)
        if length < 1e-9:
            continue
        for i in range(len(pa)):
            j = (i + 1) % len(pa)
            ns = [normal(na[k][0] * dy / length, -dr / length, na[k][1] * dy / length)
                  for k in (i, j, j, i)]
            pts = [place(*p) for p in ((pa[i][0], ya, pa[i][1]), (pa[j][0], ya, pa[j][1]),
                                      (pb[j][0], yb, pb[j][1]), (pb[i][0], yb, pb[i][1]))]
            # The silver grain follows the long edge of each rail, not world axes.
            uv = [_uv(side_entry or entry, u, v) for u, v in ((0, 0), (1, 0), (1, 1), (0, 1))]
            P.outward(model, paint, pts, sum(ns), uv=uv, normals=ns)
    for ring, direction, name in ((rings[0], -1, side_entry or entry), (rings[-1], 1, entry)):
        y, _, points, _ = ring
        pts = [place(px, y, pz) for px, pz in points]
        uv = [_uv(name, (px - x0) / (x1 - x0), (pz - z0) / (z1 - z0)) for px, pz in points]
        P.outward(model, paint, pts, normal(0, direction, 0), uv=uv)


def _face(model, F, place, angle, bounds, name, radius=.02, paint=PLASTIC):
    import railhead_props as P
    x0, x1, y, z0, z1 = bounds
    points, _ = _outline(x0, x1, z0, z1, radius)
    uv = [_uv(name, (px - x0) / (x1 - x0), (pz - z0) / (z1 - z0)) for px, pz in points]
    P.outward(model, paint, [place(px, y, pz) for px, pz in points],
              P._world(F, P._lean((0, 1, 0), angle)), uv=uv)


def _turned(model, F, at, profile, entries, paints, sides=64):
    """Lathed pedestal with radial UVs on its brushed circular top."""
    import railhead_props as P
    o = F.p(*at)
    radius = max(p[0] for p in profile)
    for k, ((r0, z0), (r1, z1)) in enumerate(zip(profile, profile[1:])):
        if r0 == r1 == 0:
            continue
        slope = P._unit((z1 - z0, r0 - r1))
        for i in range(sides):
            t0, t1 = i * 2 * math.pi / sides, (i + 1) * 2 * math.pi / sides
            d0 = math.cos(t0) * F.x + math.sin(t0) * F.y
            d1 = math.cos(t1) * F.x + math.sin(t1) * F.y
            pts = [o + r0 * d0 + z0 * F.z, o + r0 * d1 + z0 * F.z,
                   o + r1 * d1 + z1 * F.z, o + r1 * d0 + z1 * F.z]
            ns = [slope[0] * d0 + slope[1] * F.z, slope[0] * d1 + slope[1] * F.z,
                  slope[0] * d1 + slope[1] * F.z, slope[0] * d0 + slope[1] * F.z]
            if entries[k] == "base":
                uv = [_uv("base", .5 + r * math.cos(t) / (2 * radius),
                          .5 + r * math.sin(t) / (2 * radius))
                      for r, t in ((r0, t0), (r0, t1), (r1, t1), (r1, t0))]
            else:
                uv = [_uv(entries[k], u, v) for u, v in ((i / sides, 0), ((i + 1) / sides, 0),
                                                        ((i + 1) / sides, 1), (i / sides, 1))]
            if r0 == 0:
                pts, ns, uv = [pts[j] for j in (0, 2, 3)], [ns[j] for j in (0, 2, 3)], [uv[j] for j in (0, 2, 3)]
            elif r1 == 0:
                pts, ns, uv = pts[:3], ns[:3], uv[:3]
            P.outward(model, paints[k], pts, sum(ns), uv=uv, normals=ns)


def build(model, F, x, y, z):
    """The reference's full front layout on a slightly tilted countertop stand."""
    import railhead_props as P
    for paint in (PLASTIC, METAL, SCREEN):
        model.material_overrides[paint] = f"materials/railhead/{paint}.vmat"
        model.tile_overrides[paint] = 1.0

    # Black non-slip foot, turned stainless base, socket and thick black stem.
    _turned(model, F, (x, y - .45, z),
            ((0, .015), (2.12, .015), (2.22, .08), (2.24, .40), (2.18, .48), (0, .50)),
            ("black", "black", "steel", "steel", "base"), (PLASTIC, PLASTIC, METAL, METAL, METAL))
    _turned(model, F, (x, y - .45, z),
            ((0, .49), (.73, .49), (.73, .56), (.60, .60), (.55, 1.68), (0, 1.68)),
            ("black", "steel", "steel", "body", "body"), (PLASTIC, METAL, METAL, PLASTIC, PLASTIC), sides=40)

    angle = math.radians(12)
    place = P._leaned(F, (x, y, z + 1.64), angle)
    _solid(model, F, place, angle, (-2.35, 2.35, -.94, 0, 0, 7.6), .22, .08)
    # Metal cheeks wrap round the top and bottom; narrow dark seams inside.
    for side in (-1, 1):
        xc = side * 2.215
        _solid(model, F, place, angle, (xc - .135, xc + .135, -.87, .046, .01, 7.59),
               .125, .038, "steel", METAL)
        xc = side * 2.055
        _solid(model, F, place, angle, (xc - .024, xc + .024, -.01, .072, .15, 7.44),
               .020, .012, "black")

    # Deep glossy bezel and 4:3 LCD. Four narrow physical soft keys below it.
    _solid(model, F, place, angle, (-2.015, 2.015, -.012, .085, 4.13, 7.285), .09, .024, "black")
    _face(model, F, place, angle, (-1.975, 1.975, .088, 4.175, 7.245), "glass", .075)
    _solid(model, F, place, angle, (-1.725, 1.725, .083, .102, 4.425, 7.015), .026, .005, "black")
    _face(model, F, place, angle, (-1.69, 1.69, .105, 4.455, 6.99), "screen", .012, SCREEN)
    for xc in (-1.25, -.42, .42, 1.25):
        _solid(model, F, place, angle, (xc - .22, xc + .22, .085, .112, 4.23, 4.31),
               .035, .012, "steel", METAL)

    # Raised silver keys on black rubber seats, including the separate function column.
    _solid(model, F, place, angle, (-2.005, 2.005, -.004, .035, 1.675, 4.13), .045, .013)
    columns = (-1.285, -.395, .495, 1.385)
    rows = (3.755, 3.225, 2.695, 2.13)
    for row, names in enumerate(KEYS):
        for col, name in enumerate(names):
            if name is None:
                continue
            xc, zc = columns[col], rows[row]
            width = .91 if name == "0" else .85 if name == "accept" else .755
            height = .44 if row < 3 else .465
            _solid(model, F, place, angle, (xc - width / 2 - .024, xc + width / 2 + .024,
                   .034, .096, zc - height / 2 - .022, zc + height / 2 + .022), .065, .018, "black")
            _solid(model, F, place, angle, (xc - width / 2, xc + width / 2,
                   .082, .185, zc - height / 2, zc + height / 2), .056, .021,
                   name, PLASTIC if name in ("cancel", "accept") else METAL,
                   side_entry=name if name in ("cancel", "accept") else "steel")

    # Separate lower contactless pad and card-insertion panel, divided by a seam.
    _solid(model, F, place, angle, (-2.01, -.025, -.01, .06, .30, 1.655), .036, .014, "tap")
    _solid(model, F, place, angle, (.025, 2.01, -.01, .06, .30, 1.655), .036, .014)
    _face(model, F, place, angle, (.715, 1.315, .063, .41, .96), "insert", .012)

    # A hollow slot: frame strips surround an inset opening, with an actual dark throat.
    _solid(model, F, place, angle, (.25, 1.815, .058, .090, .97, 1.37), .058, .012, "black")
    _solid(model, F, place, angle, (.32, 1.745, .083, .112, 1.01, 1.335), .039, .01, "steel", METAL)
    _solid(model, F, place, angle, (.35, 1.715, .112, .165, 1.205, 1.315), .032, .008, "black")
    _solid(model, F, place, angle, (.35, 1.715, .112, .165, 1.035, 1.115), .028, .008, "black")
    for x0, x1 in ((.35, .425), (1.64, 1.715)):
        _solid(model, F, place, angle, (x0, x1, .112, .165, 1.09, 1.24), .025, .008, "black")
    _face(model, F, place, angle, (.42, 1.645, .113, 1.11, 1.21), "black", .009)


def missing(out=OUT):
    return any(not (Path(out) / name).is_file() for name in
               ("rw_card_reader_color.png", "rw_card_reader_normal.png", "rw_card_reader_rough.png",
                "rw_card_reader_illum.png", "rw_card_reader.vmat", "rw_card_reader_metal.vmat",
                "rw_card_reader_screen.vmat"))


def _font(size, bold=False):
    from PIL import ImageFont
    name = "Dinish-Bold.ttf" if bold else "Dinish-Regular.ttf"
    return ImageFont.truetype(str(ROOT / "Assets/fonts" / name), size)


def _text(draw, at, words, size, color, bold=False, anchor="mm"):
    draw.text(at, words, font=_font(size, bold), fill=color, anchor=anchor,
              stroke_width=0, spacing=3, align="center")


def _screen():
    from PIL import Image, ImageDraw
    w, h = 1024, 768
    yy, xx = np.mgrid[:h, :w]
    dark = np.array((25, 43, 65))
    field = dark + (1 - yy[..., None] / h) * np.array((0, 14, 30))
    field = field + np.exp(-((xx - 150) / 530) ** 2)[..., None] * 5
    img = Image.fromarray(np.uint8(np.clip(field, 0, 255)))
    d = ImageDraw.Draw(img)
    for row in range(124):
        d.line((0, row, w, row), fill=(29, int(84 - row * .1), int(145 - row * .12)))
    _text(d, (38, 69), "Zahlungsmittel wählen", 48, "white", anchor="lm")
    _text(d, (996, 34), "14:37", 33, "white", anchor="rm")
    colors = ((82, 182, 151), (44, 135, 242), (234, 187, 82),
              (159, 83, 224), (43, 180, 222), (235, 74, 78))
    labels = ("Karte", "Kreditkarte", "Mobil zahlen", "Fahrkarte", "Weitere\nProdukte", "Information")
    white = (250, 253, 255)
    for k, color in enumerate(colors):
        x, y = 26 + k % 3 * 256, 154 + k // 3 * 267
        d.rounded_rectangle((x, y, x + 231, y + 244), radius=13, fill=color,
                            outline=tuple(min(255, c + 14) for c in color), width=2)
        # Gentle screen tile gradients without baking environment reflections into the LCD.
        for row in range(8, 237):
            shade = 1.07 - .13 * row / 244
            d.line((x + 3, y + row, x + 228, y + row),
                   fill=tuple(min(255, int(c * shade)) for c in color))
        cx, cy = x + 115, y + 87
        if k == 0:
            d.ellipse((cx - 56, cy - 48, cx + 56, cy + 48), outline=white, width=4)
            for r in (18, 30, 42):
                d.arc((cx - r - 16, cy - r, cx + r - 16, cy + r), -52, 52, fill=white, width=6)
            d.line((cx + 28, cy - 37, cx + 33, cy + 37), fill=white, width=4)
        elif k == 1:
            d.rounded_rectangle((cx - 45, cy - 31, cx + 45, cy + 31), radius=5, outline=white, width=5)
            d.rectangle((cx - 44, cy - 16, cx + 43, cy - 4), fill=white)
            d.line((cx - 33, cy + 19, cx - 18, cy + 19), fill=white, width=3)
        elif k == 2:
            d.rounded_rectangle((cx - 26, cy - 45, cx + 26, cy + 45), radius=6, outline=white, width=5)
            d.line((cx - 22, cy - 32, cx + 22, cy - 32), fill=white, width=4)
            d.ellipse((cx - 4, cy + 32, cx + 4, cy + 40), fill=white)
        elif k == 3:
            d.rounded_rectangle((cx - 33, cy - 40, cx + 33, cy + 40), radius=5, fill=white)
            d.ellipse((cx - 45, cy - 8, cx - 20, cy + 17), fill=color)
            d.ellipse((cx + 20, cy - 8, cx + 45, cy + 17), fill=color)
            d.line((cx - 20, cy - 23, cx + 20, cy + 24), fill=color, width=6)
            d.line((cx + 20, cy - 23, cx - 20, cy + 24), fill=color, width=6)
        elif k == 4:
            d.rounded_rectangle((cx - 30, cy - 39, cx + 30, cy + 39), radius=4, outline=white, width=5)
            d.line((cx - 22, cy - 23, cx + 23, cy - 23), fill=white, width=5)
            for dy, length in ((-7, 40), (8, 40), (23, 23)):
                d.line((cx - 21, cy + dy, cx - 21 + length, cy + dy), fill=white, width=3)
        else:
            d.ellipse((cx - 42, cy - 42, cx + 42, cy + 42), outline=white, width=5)
            _text(d, (cx, cy + 3), "i", 75, white)
        _text(d, (cx, y + (199 if k == 4 else 193)), labels[k], 35, white)
    d.rounded_rectangle((798, 139, 1007, 739), radius=13, fill=(229, 238, 250))
    d.rounded_rectangle((798, 139, 1007, 261), radius=13, fill=(202, 222, 245))
    d.rectangle((798, 249, 1007, 261), fill=(202, 222, 245))
    for k, words in enumerate(("Deutsch", "English", "Français", "Polski", "Italiano")):
        _text(d, (902, 203 + k * 108), words, 34, (6, 14, 25), bold=True)
    return img


def _grain(w, h, kind, rng):
    """Subtle surface detail, with tangent normals and measured roughness ranges."""
    yy, xx = np.mgrid[:h, :w]
    noise = rng.normal(0, 1, (h, w))
    if kind == "steel":
        grain = rng.normal(0, 2.6, (h, 1)) + noise * .7
        value = 186 + grain
        rgb = np.stack((value * 1.01, value, value * .975), axis=-1)
        height = grain * .012
        rough = 115 + grain * .8
    elif kind == "base":
        radius = np.hypot(xx - w / 2, yy - h / 2)
        grain = np.sin(radius * 1.72) * 1.3 + noise * .75
        value = 169 + grain
        rgb = np.stack((value * 1.01, value, value * .975), axis=-1)
        height, rough = grain * .012, 100 + grain
    else:
        value = (9 if kind == "black" else 39) + noise * (1 if kind == "black" else 1.8)
        rgb = np.stack((value, value * 1.015, value * 1.035), axis=-1)
        height, rough = noise * .07, 145 + noise * 4
    gy, gx = np.gradient(height)
    normal = np.stack((-gx, gy, np.ones_like(gx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return (np.uint8(np.clip(rgb, 0, 255)), np.uint8(np.clip(rough, 0, 255)),
            np.uint8(np.clip((normal * .5 + .5) * 255, 0, 255)))


def _key(image, name):
    from PIL import ImageDraw
    d = ImageDraw.Draw(image)
    w, h = image.size
    ink = (22, 25, 24)
    letters = {"2": "ABC", "3": "DEF", "4": "GHI", "5": "JKL", "6": "MNO",
               "7": "PQRS", "8": "TUV", "9": "WXYZ"}
    if name in letters:
        _text(d, (78, h / 2 + 2), name, 106, ink)
        _text(d, (192, h / 2 + 5), letters[name], 42, ink)
    elif name in ("1", "0"):
        _text(d, (w / 2, h / 2 + 2), name, 110, ink)
    elif name == "more":
        for x in (121, 160, 199):
            d.ellipse((x - 8, 85, x + 8, 101), fill=ink)
    elif name == "back":
        d.line((204, 92, 114, 92), fill=ink, width=10)
        d.line((152, 57, 114, 92, 152, 127), fill=ink, width=10, joint="curve")
    elif name == "receipt":
        d.rounded_rectangle((119, 49, 196, 134), radius=5, outline=ink, width=7)
        d.line((187, 47, 204, 58, 204, 143, 125, 143), fill=ink, width=5)
        for y, length in ((69, 48), (88, 48), (107, 35)):
            d.line((133, y, 133 + length, y), fill=ink, width=6)
    elif name == "cancel":
        d.line((126, 58, 195, 127), fill=(35, 28, 26), width=17)
        d.line((195, 58, 126, 127), fill=(35, 28, 26), width=17)
    elif name == "accept":
        d.line((114, 93, 145, 122, 209, 58), fill=(15, 58, 25), width=18, joint="curve")


def _tap(image):
    from PIL import ImageDraw
    d = ImageDraw.Draw(image)
    ink = (220, 224, 224)
    d.ellipse((92, 75, 281, 235), outline=ink, width=4)
    for r in (22, 37, 53, 70):
        d.arc((142 - r, 151 - r, 142 + r, 151 + r), -45, 45, fill=ink, width=9)
    # Card and the outline of a hand presenting it, as on the reference pad.
    d.rounded_rectangle((244, 110, 291, 153), radius=6, outline=ink, width=3)
    d.line((253, 119, 281, 140), fill=ink, width=3)
    d.line((306, 221, 286, 205, 276, 183, 254, 170, 251, 162, 257, 157,
            276, 166, 258, 148, 259, 140, 266, 137, 301, 168, 305, 160,
            290, 146, 291, 136, 300, 133, 317, 145, 329, 166, 349, 198),
           fill=ink, width=4, joint="curve")


def _insert(image):
    from PIL import ImageDraw
    d = ImageDraw.Draw(image)
    w, h = image.size
    ink = (210, 215, 217)
    d.rounded_rectangle((w * .38, h * .25, w * .62, h * .81), radius=6, outline=ink, width=4)
    d.polygon(((w * .405, h * .43), (w * .5, h * .315), (w * .595, h * .43)), fill=ink)
    d.polygon(((w * .46, h * .73), (w * .5, h * .66), (w * .54, h * .73)), fill=ink)


def vmat(metal=False, screen=False):
    lines = ['// Tools/railhead_card_reader.py', '"Layer0"', '{',
             '    shader "shaders/complex.shader"', f'    F_SPECULAR "{0 if screen else 1}"',
             '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{.35 if metal else 0:.2f}"']
    if screen:
        lines += ['    F_SELF_ILLUM "1"',
                  '    TextureSelfIllumMask "materials/railhead/rw_card_reader_illum.png"',
                  '    g_flSelfIllumBrightness "0.35"', '    g_flSelfIllumAlbedoFactor "1.0"',
                  '    g_vSelfIllumTint "[1 1 1 0]"']
    lines += ['    TextureColor "materials/railhead/rw_card_reader_color.png"',
              '    TextureNormal "materials/railhead/rw_card_reader_normal.png"',
              '    TextureRoughness "materials/railhead/rw_card_reader_rough.png"',
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
              '    g_vColorTint "[1 1 1 1]"', '    g_flModelTintAmount "1.0"', '}']
    return '\n'.join(lines) + '\n'


def write(out=OUT):
    from PIL import Image
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    color = Image.new("RGB", (SIZE, SIZE), (39, 40, 41))
    normal = Image.new("RGB", (SIZE, SIZE), (128, 128, 255))
    rough = Image.new("L", (SIZE, SIZE), 145)
    illum = Image.new("L", (SIZE, SIZE), 0)
    rng = np.random.default_rng(73119)
    for name, (x0, y0, x1, y1) in RECTS.items():
        w, h = x1 - x0, y1 - y0
        kind = "steel" if name in ("steel", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "more", "back", "receipt") else name
        rgb, rr, nn = _grain(w, h, kind, rng)
        tile = Image.fromarray(rgb)
        if name == "screen":
            tile = _screen()
            rr[:] = 28
            nn[:] = (128, 128, 255)
            illum.paste(255, (x0, y0, x1, y1))
        elif name == "glass":
            tile = Image.new("RGB", (w, h), (18, 21, 23))
            rr[:], nn[:] = 32, (128, 128, 255)
        elif name in ("cancel", "accept"):
            base = np.array((219, 47, 42) if name == "cancel" else (40, 154, 58))
            noise = rng.normal(0, 1, (h, w, 1))
            tile = Image.fromarray(np.uint8(np.clip(base + noise, 0, 255)))
            rr[:] = 92
            _key(tile, name)
        elif name in {n for row in KEYS for n in row if n is not None}:
            _key(tile, name)
        elif name == "tap":
            _tap(tile)
        elif name == "insert":
            _insert(tile)
        for atlas, patch in ((color, tile), (rough, Image.fromarray(rr)), (normal, Image.fromarray(nn))):
            atlas.paste(patch, (x0, y0))
            # Eight-pixel gutters repeat edge texels to prevent neighboring entries bleeding into mipmaps.
            atlas.paste(patch.crop((0, 0, 1, h)).resize((8, h)), (x0 - 8, y0))
            atlas.paste(patch.crop((w - 1, 0, w, h)).resize((8, h)), (x1, y0))
            atlas.paste(patch.crop((0, 0, w, 1)).resize((w, 8)), (x0, y0 - 8))
            atlas.paste(patch.crop((0, h - 1, w, h)).resize((w, 8)), (x0, y1))
    for name, atlas in (("color", color), ("normal", normal), ("rough", rough), ("illum", illum)):
        atlas.save(out / f"rw_card_reader_{name}.png", optimize=True)
    import map_kit as K
    for metal, screen, name in ((False, False, PLASTIC), (True, False, METAL), (False, True, SCREEN)):
        K.write_text(out / f"{name}.vmat", vmat(metal, screen))
    print(f"wrote card reader: {len(RECTS)} atlas entries, three materials, {SIZE}px")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    write(ap.parse_args().out)


if __name__ == "__main__":
    main()
