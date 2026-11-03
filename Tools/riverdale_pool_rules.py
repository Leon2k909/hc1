"""Riverdale's enamel pool rules plates: dedicated lettering and physical mountings."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PAINT = "rv_pool_rules_v2"
WIDTH, HEIGHT = 26.0, 34.0
NORTH_CENTRE = -228.0  # Clear of the north wall pilaster, whose left edge is -191.


def artwork():
    """Draw at the physical plate's aspect, then pack into a power-of-two texture."""
    w, h = 1560, 2040
    image = Image.new("RGB", (w, h), (227, 228, 221))
    d = ImageDraw.Draw(image)
    ink, blue, white = (33, 42, 47), (24, 57, 89), (237, 239, 231)

    def font(size, bold=True):
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")), size)

    def text(x, y, value, size, fill=ink, bold=True):
        f = font(size, bold)
        assert d.textlength(value, font=f) <= w - x - 85, value
        d.text((x, y), value, font=f, fill=fill, anchor="lt")

    d.rectangle((0, 0, w, 440), fill=blue)
    # The plant's own A symbol and operator name.
    d.polygon(((116, 68), (163, 150), (69, 150)), fill=white)
    d.polygon(((116, 112), (134, 151), (98, 151)), fill=blue)
    text(194, 89, "RIVERDALE NUCLEAR", 42, white)
    text(85, 194, "SPENT FUEL POOL", 98, white)
    text(85, 308, "SAFETY RULES", 84, white)
    d.rectangle((0, 440, w, 454), fill=(191, 155, 64))
    rules = [
        ("NO LOOSE ITEMS", "OVER THE POOL"),
        ("TETHER ALL TOOLS",),
        ("WEAR YOUR DOSIMETER", "AT ALL TIMES"),
        ("DO NOT GO BEYOND", "THE SAFETY RAIL"),
        ("REPORT ALL", "DROPPED OBJECTS"),
        ("KEEP CLEAR DURING", "CRANE MOVEMENTS"),
    ]
    for i, lines in enumerate(rules):
        top = 502 + i * 218
        if i:
            d.line((85, top - 25, w - 85, top - 25), fill=(182, 189, 185), width=2)
        d.ellipse((88, top + 26, 180, top + 118), fill=blue)
        d.text((134, top + 71), str(i + 1), font=font(56), anchor="mm", fill=white)
        for j, line in enumerate(lines):
            text(223, top + (40 if len(lines) == 1 else 12) + j * 76, line, 64)
    d.rectangle((85, 1830, w - 85, 1835), fill=blue)
    text(85, 1864, "FUEL HANDLING BUILDING", 38, blue)
    text(85, 1925, "RDN / FH-06", 28, (77, 86, 87), bold=False)
    # Quiet edge wear and coating variation, kept away from the lettering.
    rng = np.random.default_rng(631)
    a = np.asarray(image, dtype=np.float32).copy()
    yy, xx = np.mgrid[:h, :w]
    edge = np.minimum.reduce((xx, w - 1 - xx, yy, h - 1 - yy))
    a *= (1 - 0.055 * np.exp(-edge / 15.0))[..., None]
    a += rng.normal(0, 0.45, (h, w, 1))
    image = Image.fromarray(np.uint8(np.clip(a, 0, 255)))
    return image.resize((1024, 2048), Image.Resampling.LANCZOS)


def surface():
    """The material generator uses the same source artwork as the installed plate."""
    import riverdale_materials as rm
    rgb = np.asarray(artwork(), dtype=np.float32)
    return rm.T.srgb_to_linear(rgb), np.full(rgb.shape[:2], 0.54, np.float32), np.zeros(rgb.shape[:2], np.float32), 1024 / WIDTH


def board(detail, fine, face, s, z):
    import riverdale_hall as hall

    # Spacers, folded metal backing and a narrow raised lip; the face clears the wall coating.
    for sx in (-1, 1):
        for sz in (1.05, HEIGHT - 1.05):
            centre = face.p(s + sx * (WIDTH / 2 - 1.05), z + sz, 0.30)
            hall.lathe_on(detail, centre, face.out, [(0.34, 0), (0.34, 0.43)], "rv_stainless", 8, cap0="rv_stainless", cap1="rv_stainless")
    face.box(detail, s - WIDTH / 2, s + WIDTH / 2, z, z + HEIGHT, 0.58, 1.08, "rv_frame", back=True)
    for x0, x1, z0, z1 in (
        (s - 13, s - 12.65, z, z + HEIGHT), (s + 12.65, s + 13, z, z + HEIGHT),
        (s - 12.65, s + 12.65, z, z + 0.35), (s - 12.65, s + 12.65, z + HEIGHT - 0.35, z + HEIGHT),
    ):
        face.box(detail, x0, x1, z0, z1, 1.08, 1.21, "rv_stainless")
    # Explicit UVs prevent the shared hall texture atlas from limiting the sign's resolution.
    face.quad(fine, PAINT, s - 12.65, s + 12.65, z + 0.35, z + HEIGHT - 0.35, 1.12,
              [(0, 0), (1, 0), (1, 1), (0, 1)])
    for sx in (-1, 1):
        for sz in (1.05, HEIGHT - 1.05):
            x, zz = s + sx * (WIDTH / 2 - 1.05), z + sz
            hall.lathe_on(detail, face.p(x, zz, 1.12), face.out,
                          [(0.28, 0), (0.28, 0.06), (0.22, 0.12), (0.13, 0.15)], "rv_stainless", 12, cap1="rv_stainless")
            face.quad(fine, "rv_dark", x - 0.12, x + 0.12, zz - 0.025, zz + 0.025, 1.275)
