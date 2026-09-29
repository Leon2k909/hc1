"""
Legacy procedural rank emblems, kept for reference. Writes to output/legacy_rank_emblems.
The live generated artwork is in Assets/ui/ranked; prompts are in Tools/ranked_emblems/prompts.json.

    python Tools/rank_emblems.py [--preview <png>]

Each is a metal shield in the tier's colour (Rank.TierColors) with the tier's symbol on a dark field, and more trim
the higher the tier: Bronze one chevron, Silver two, Gold three and a star on top, Platinum a star and side blades,
Diamond a gem and wings, Master a crown and bigger wings. All six share one frame, so they line up side by side.
Everything is drawn at 4x and scaled down for smooth edges.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "output", "legacy_rank_emblems")
S = 2048  # drawing size
FINAL = 512

# Shapes are laid out in 0..1 units, then scaled by FRAME about the design's centre, so the widest wings and their
# glow stay inside the image.
FRAME = 0.94
DESIGN_CENTRE = (0.5, 0.46)

# name, colour (keep in step with Rank.TierColors), centre symbol, trim level
TIERS = [
    ("bronze", "#cd7f32", "chevrons1", 0),
    ("silver", "#c4cdd4", "chevrons2", 1),
    ("gold", "#ffcf40", "chevrons3", 2),
    ("platinum", "#4fd0e0", "star", 3),
    ("diamond", "#8a6cff", "gem", 4),
    ("master", "#ff5c5c", "crown", 5),
]

OUTLINE = (7, 8, 10)


def rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def to_px(x, y):
    """Design units to pixels."""
    return ((0.5 + (x - DESIGN_CENTRE[0]) * FRAME) * S, (0.5 + (y - DESIGN_CENTRE[1]) * FRAME) * S)


def mask(polygons=(), circles=()):
    image = Image.new("L", (S, S), 0)
    draw = ImageDraw.Draw(image)
    for poly in polygons:
        draw.polygon([to_px(x, y) for x, y in poly], fill=255)
    for (cx, cy, r) in circles:
        x, y = to_px(cx, cy)
        rp = r * FRAME * S
        draw.ellipse([x - rp, y - rp, x + rp, y + rp], fill=255)
    return image


def metal(colour, y0, y1, bright=0.0):
    """A vertical metal ramp in the colour from design row y0 to y1: light at the top, dark at the bottom."""
    c = np.clip(colour + bright, 0, 1)
    white = np.ones(3)
    stops = [
        (0.00, c + (white - c) * 0.72),
        (0.28, c + (white - c) * 0.28),
        (0.50, c),
        (0.76, c * 0.56),
        (1.00, c * 0.34),
    ]
    p0, p1 = to_px(0, y0)[1] / S, to_px(0, y1)[1] / S
    ys = np.clip((np.arange(S) / S - p0) / max(1e-6, p1 - p0), 0, 1)
    ramp = np.zeros((S, 3))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        sel = (ys >= t0) & (ys <= t1)
        f = ((ys[sel] - t0) / (t1 - t0))[:, None]
        ramp[sel] = c0 * (1 - f) + c1 * f
    image = np.repeat(ramp[:, None, :], S, axis=1)
    return Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8), "RGB")


def paint(canvas, fill, shape_mask):
    """Composites fill (an RGB image or colour) onto canvas through the mask."""
    if isinstance(fill, tuple):
        fill = Image.new("RGB", (S, S), fill)
    layer = fill.convert("RGBA")
    layer.putalpha(shape_mask)
    canvas.alpha_composite(layer)


def dilate(shape_mask, px):
    out = shape_mask
    while px > 0:
        step = min(px, 12)
        out = out.filter(ImageFilter.MaxFilter(step * 2 + 1))
        px -= step
    return out


def erode(shape_mask, px):
    out = shape_mask
    while px > 0:
        step = min(px, 12)
        out = out.filter(ImageFilter.MinFilter(step * 2 + 1))
        px -= step
    return out


# ── shapes (design units) ──────────────────────────────────────────────────────────────────────

def bezier(p0, p1, p2, n=24):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]


def shield(cx, top, w, h):
    hw = w / 2
    corner = h * 0.05
    top_edge = bezier((cx - hw, top + corner), (cx, top - corner * 0.9), (cx + hw, top + corner))
    bottom_right = bezier((cx + hw, top + h * 0.48), (cx + hw, top + h * 0.80), (cx, top + h))
    bottom_left = bezier((cx, top + h), (cx - hw, top + h * 0.80), (cx - hw, top + h * 0.48))
    return top_edge + [(cx + hw, top + h * 0.48)] + bottom_right[1:] + bottom_left[1:]


def star(cx, cy, r, inner=0.44, rotation=-90):
    pts = []
    for i in range(10):
        a = math.radians(rotation + i * 36)
        rr = r if i % 2 == 0 else r * inner
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def chevron(cx, cy, w, h, thick):
    """An upward chevron (a rank stripe) centred on cx, apex at cy - h/2."""
    return [(cx - w / 2, cy + h / 2), (cx, cy - h / 2), (cx + w / 2, cy + h / 2),
            (cx + w / 2, cy + h / 2 + thick), (cx, cy - h / 2 + thick), (cx - w / 2, cy + h / 2 + thick)]


def gem(cx, cy, r):
    return [(cx - r, cy - r * 0.28), (cx - r * 0.52, cy - r * 0.78), (cx + r * 0.52, cy - r * 0.78),
            (cx + r, cy - r * 0.28), (cx, cy + r * 1.02)]


def crown(cx, cy, r):
    return [(cx - r, cy + r * 0.62), (cx - r, cy - r * 0.42), (cx - r * 0.5, cy + r * 0.06), (cx, cy - r * 0.78),
            (cx + r * 0.5, cy + r * 0.06), (cx + r, cy - r * 0.42), (cx + r, cy + r * 0.62)]


def feather(root, angle, length, width):
    """A blade from root, angle in degrees above the horizontal (pointing right), widest a third of the way out."""
    a = math.radians(angle)
    d = (math.cos(a), -math.sin(a))
    n = (-d[1], d[0])
    tip = (root[0] + d[0] * length, root[1] + d[1] * length)
    mid = (root[0] + d[0] * length * 0.38, root[1] + d[1] * length * 0.38)
    return [(root[0] + n[0] * width * 0.2, root[1] + n[1] * width * 0.2),
            (mid[0] + n[0] * width / 2, mid[1] + n[1] * width / 2),
            tip,
            (mid[0] - n[0] * width / 2, mid[1] - n[1] * width / 2),
            (root[0] - n[0] * width * 0.2, root[1] - n[1] * width * 0.2)]


def mirror(poly, cx=0.5):
    return [(2 * cx - x, y) for x, y in poly]


# ── one emblem ─────────────────────────────────────────────────────────────────────────────────

def emblem(colour_hex, symbol, trim):
    colour = rgb(colour_hex)
    colour_255 = tuple(int(v * 255) for v in colour)
    cx = 0.5
    top, w, h = 0.2, 0.46, 0.64
    body = shield(cx, top, w, h)
    inner = shield(cx, top + 0.05, w - 0.1, h - 0.1)

    # Trim behind the shield: wings for Diamond and Master, short blades for Platinum.
    wings = []
    if trim >= 4:
        count = 4 if trim >= 5 else 3
        scale = 1.0 if trim >= 5 else 0.9
        for i, (angle, length) in enumerate(list(zip((44, 26, 9, -8), (0.31, 0.28, 0.24, 0.18)))[:count]):
            f = feather((cx + w * 0.34, top + h * (0.2 + i * 0.1)), angle, length * scale, 0.085)
            wings += [f, mirror(f)]
    elif trim >= 3:
        for i, (angle, length) in enumerate(((18, 0.2), (-6, 0.16))):
            f = feather((cx + w * 0.4, top + h * (0.26 + i * 0.14)), angle, length, 0.07)
            wings += [f, mirror(f)]

    top_star = star(cx, top - 0.055, 0.075 if trim >= 5 else 0.06) if trim >= 2 else None

    # The centre symbol, on the dark field: (polygons, circles).
    sy = top + h * 0.47
    symbols = []
    if symbol.startswith("chevrons"):
        n = int(symbol[-1])
        gap = 0.078
        for i in range(n):
            symbols.append(([chevron(cx, sy - (n - 1) * gap / 2 + i * gap, 0.22, 0.09, 0.046)], []))
    elif symbol == "star":
        symbols.append(([star(cx, sy, 0.13)], []))
    elif symbol == "gem":
        symbols.append(([gem(cx, sy - 0.01, 0.12)], []))
    elif symbol == "crown":
        r = 0.12
        jewels = [(cx - r, sy - r * 0.42 - 0.012, 0.018), (cx, sy - r * 0.78 - 0.012, 0.02),
                  (cx + r, sy - r * 0.42 - 0.012, 0.018)]
        symbols.append(([crown(cx, sy, r)], jewels))

    silhouette = mask([body] + wings + ([top_star] if top_star else []))
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # A soft glow in the tier's colour, then a dark keyline round everything.
    glow = dilate(silhouette, 30).filter(ImageFilter.GaussianBlur(56))
    glow = glow.point(lambda v: int(v * (0.55 if trim >= 4 else 0.38)))
    paint(canvas, colour_255, glow)
    paint(canvas, OUTLINE, dilate(silhouette, 16))

    # Wings and blades: the metal a shade darker, each feather keylined.
    for poly in wings:
        m = mask([poly])
        paint(canvas, OUTLINE, dilate(m, 9))
        paint(canvas, metal(colour, top - 0.1, top + h * 0.8, bright=-0.08), m)

    # The shield: metal rim, dark field with the colour glowing through, a light line round the field.
    paint(canvas, metal(colour, top, top + h), mask([body]))
    field = mask([inner])
    paint(canvas, OUTLINE, dilate(field, 7))
    yy, xx = np.mgrid[0:S, 0:S] / S
    gx, gy = to_px(cx, top + h * 0.45)
    dist = np.sqrt((xx - gx / S) ** 2 + ((yy - gy / S) * 0.9) ** 2) / FRAME
    glow_amount = np.clip(1 - dist / 0.3, 0, 1)[..., None] ** 1.6
    dark = np.array([0.05, 0.055, 0.07]) + glow_amount * colour * 0.42
    paint(canvas, Image.fromarray((np.clip(dark, 0, 1) * 255).astype(np.uint8), "RGB"), field)
    edge = Image.fromarray((np.array(field).astype(int) - np.array(erode(field, 6))).clip(0, 255).astype(np.uint8), "L")
    light = tuple(int(v * 255) for v in np.clip(colour + (1 - colour) * 0.5, 0, 1))
    paint(canvas, light, edge.point(lambda v: int(v * 0.75)))

    # The symbol and the top star: bright metal, keylined.
    shapes = symbols + ([([top_star], [])] if top_star else [])
    for polys, circles in shapes:
        m = mask(polys, circles)
        paint(canvas, OUTLINE, dilate(m, 8))
        ys = [y for poly in polys for _, y in poly] + [c[1] - c[2] for c in circles]
        paint(canvas, metal(colour, min(ys) - 0.02, max(ys) + 0.02, bright=0.06), m)

    # The gem's facets.
    if symbol == "gem":
        g = gem(cx, sy - 0.01, 0.12)
        draw = ImageDraw.Draw(canvas)
        facet = tuple(int(v * 255 * 0.45) for v in colour) + (255,)
        for a, b in ((g[1], g[4]), (g[2], g[4]), (g[0], g[3])):
            draw.line([to_px(*a), to_px(*b)], fill=facet, width=int(S * 0.006))

    return canvas.resize((FINAL, FINAL), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    images = []
    for name, colour, symbol, trim in TIERS:
        image = emblem(colour, symbol, trim)
        path = os.path.normpath(os.path.join(OUT, f"{name}.png"))
        image.save(path)
        images.append(image)
        print("wrote", path, "bounds", image.getbbox())

    if "--preview" in sys.argv:
        path = sys.argv[sys.argv.index("--preview") + 1]
        half = FINAL // 2
        sheet = Image.new("RGBA", (half * len(images), half), (16, 17, 21, 255))
        for i, image in enumerate(images):
            sheet.alpha_composite(image.resize((half, half), Image.LANCZOS), (i * half, 0))
        sheet.save(path)
        print("preview", path)


if __name__ == "__main__":
    main()
