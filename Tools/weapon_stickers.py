"""Gunsmith stickers: original die-cut vinyl stickers that GunsmithSticker prints on the guns' sticker points.

python Tools/weapon_stickers.py              writes the stickers' assets (below)
python Tools/weapon_stickers.py --preview <png>   draws every sticker on a grey sheet instead, and writes nothing else

Per sticker it writes:
  Assets/materials/stickers/<name>.png       the artwork, RGBA, cropped to its cut. It's the gunsmith tile and the
                                             print's colour; outside the cut the colour is bled from the edge, so
                                             filtering never pulls black into the border.
  Assets/materials/stickers/<name>_mask.png  the cut (white inside), the material's alpha-test mask
  Assets/materials/stickers/<name>.vmat      complex.shader, alpha tested, satin vinyl
  Assets/gunsmith/stickers/<name>.gnsmth     the Sticker part (universal: every gun with a sticker point takes it)
and once, Assets/prefabs/gunsmith/stickers/sticker.prefab: the GunsmithSticker every sticker part mounts.

The designs are drawn here with numpy and PIL, supersampled 4x, from the game's own fonts (Assets/fonts). None of them
comes from another game: no names, logos or markings but the game's own name. Stickers have no gameplay effect.
Materials are named sticker_*, which none of GunsmithSystem.IsPreviewArmMaterial's arm and hand patterns match."""
import argparse
import json
import math
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets"
FONTS = ASSETS / "fonts"
ART = ASSETS / "materials" / "stickers"
PARTS = ASSETS / "gunsmith" / "stickers"
PREFAB = ASSETS / "prefabs" / "gunsmith" / "stickers" / "sticker.prefab"
PREFAB_PATH = "prefabs/gunsmith/stickers/sticker.prefab"

SS = 4            # supersampling
LONG_SIDE = 1024  # the artwork's long side in the PNG
NAMESPACE = uuid.UUID("5d1c1f7e-2f4b-4a53-9d1e-7b0c6a1e5a11")

# Brand colours (GunsmithPanel.razor.scss's $accent) and print inks.
ORANGE = (255, 122, 26)
INK = (20, 20, 22)
VINYL = (244, 244, 240)    # the white vinyl round a die-cut
PAPER = (243, 239, 228)    # the playing card's face
YELLOW = (255, 206, 48)
RED = (214, 38, 30)
HAZARD_YELLOW = (246, 194, 28)


def rgb(colour):
    return np.array(colour, float) / 255.0


class Sheet:
    """A design drawn in its own units on a supersampled canvas: layers of coverage and colour painted in order."""

    def __init__(self, width, height, pad):
        # pad: room round the design for the vinyl border, in units
        self.units = (width + 2 * pad, height + 2 * pad)
        self.pad = pad
        self.scale = LONG_SIDE * SS / max(self.units)  # supersampled pixels per unit
        self.size = (int(math.ceil(self.units[0] * self.scale)), int(math.ceil(self.units[1] * self.scale)))
        self.colour = np.zeros((self.size[1], self.size[0], 3))
        self.cover = np.zeros((self.size[1], self.size[0]), bool)

    def px(self, points):
        p = np.asarray(points, float)
        return (p + self.pad) * self.scale

    def mask(self, polygons):
        im = Image.new("L", self.size, 0)
        d = ImageDraw.Draw(im)
        for poly in polygons:
            q = self.px(poly)
            d.polygon([tuple(v) for v in q], fill=255)
        return np.array(im) > 127

    def paint(self, mask, colour):
        c = rgb(colour) if not isinstance(colour, np.ndarray) or colour.ndim == 1 else colour
        if isinstance(c, np.ndarray) and c.ndim == 3:
            self.colour[mask] = c[mask]
        else:
            self.colour[mask] = c
        self.cover |= mask

    def text(self, text, font, size, spacing=0.0, anchor=(0.0, 0.0), align="left"):
        """A line of text as a mask: size is the font size in units, spacing extra advance per letter in units, anchor
        the text's top-left (align left) or top-centre (align centre) in units. Returns (mask, (left, top, right,
        bottom)) with the ink's box in units."""
        font_px = size * self.scale
        f = ImageFont.truetype(str(FONTS / font), max(8, int(round(font_px))))
        advances = [f.getlength(ch) for ch in text]
        width = sum(advances) + spacing * self.scale * (len(text) - 1)
        x0 = anchor[0] * self.scale + self.pad * self.scale
        if align == "centre":
            x0 -= width / 2
        y0 = anchor[1] * self.scale + self.pad * self.scale
        im = Image.new("L", self.size, 0)
        d = ImageDraw.Draw(im)
        x = x0
        for ch, adv in zip(text, advances):
            d.text((x, y0), ch, font=f, fill=255)
            x += adv + spacing * self.scale
        m = np.array(im) > 127
        ys, xs = np.nonzero(m)
        box = (xs.min() / self.scale - self.pad, ys.min() / self.scale - self.pad,
               (xs.max() + 1) / self.scale - self.pad, (ys.max() + 1) / self.scale - self.pad)
        return m, box

    def grow(self, mask, by):
        """The mask grown by a distance in units, with round corners."""
        return ndimage.distance_transform_edt(~mask) <= by * self.scale

    def finish(self):
        """Box-filters down to the PNG: returns RGBA uint8, cropped to the cut, the colour bled outside it."""
        h, w = self.cover.shape
        h4, w4 = h // SS * SS, w // SS * SS
        cover = self.cover[:h4, :w4].astype(float)
        colour = self.colour[:h4, :w4] * cover[..., None]
        a = cover.reshape(h4 // SS, SS, w4 // SS, SS).mean((1, 3))
        c = colour.reshape(h4 // SS, SS, w4 // SS, SS, 3).sum((1, 3)) / np.maximum(
            cover.reshape(h4 // SS, SS, w4 // SS, SS).sum((1, 3)), 1e-9)[..., None]
        inside = a > 0.0
        ys, xs = np.nonzero(inside)
        top, bottom = max(ys.min() - 2, 0), min(ys.max() + 3, a.shape[0])
        left, right = max(xs.min() - 2, 0), min(xs.max() + 3, a.shape[1])
        # whole multiples of 4, for block compression
        bottom = min(top + (bottom - top + 3) // 4 * 4, a.shape[0])
        right = min(left + (right - left + 3) // 4 * 4, a.shape[1])
        a, c, inside = a[top:bottom, left:right], c[top:bottom, left:right], inside[top:bottom, left:right]
        solid = a >= 0.5
        _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
        c = np.where(solid[..., None], c, c[iy, ix])
        out = np.dstack([np.clip(c * 255 + 0.5, 0, 255), np.clip(a * 255 + 0.5, 0, 255)]).astype(np.uint8)
        return out


# ── Shapes ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def rounded_rect(x0, y0, x1, y1, r, steps=12):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(steps + 1):
            a = math.radians(a0 + 90 * i / steps)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def skew(points, angle_deg, centre_y):
    """Leans a shape right by angle (its top goes right), like italic type."""
    p = np.array(points, float)
    p[:, 0] += (centre_y - p[:, 1]) * math.tan(math.radians(angle_deg))
    return p


def bezier(p0, p1, p2, p3, n=64):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def spade(cx, cy, height):
    """A spade: an upside-down heart on a flared stem. cy is the shape's middle; height its full height."""
    t = np.linspace(0, 2 * math.pi, 400)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    # the heart spans y -17..12 (point down); upside down in image space the point is on top
    heart = np.stack([x, y], -1)
    stem_left = bezier((-1.6, 3.0), (-1.8, 12.0), (-4.0, 19.0), (-9.5, 22.5), 40)
    stem_right = bezier((9.5, 22.5), (4.0, 19.0), (1.8, 12.0), (1.6, 3.0), 40)
    stem = np.concatenate([stem_left, [(-9.5, 24.0), (9.5, 24.0)], stem_right])
    total = 17 + 24.0
    s = height / total
    mid = (-17 + 24.0) / 2
    return [(heart - (0, mid)) * s + (cx, cy), (stem - (0, mid)) * s + (cx, cy)]


def tongue(p0, p1, p2, p3, width, taper=0.85, n=90):
    """A flame tongue along a cubic curve, width at its root narrowing to a point at its tip."""
    c = bezier(p0, p1, p2, p3, n)
    d = np.gradient(c, axis=0)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    nrm = np.stack([-d[:, 1], d[:, 0]], -1)
    s = np.linspace(0, 1, n)[:, None]
    half = width / 2 * (1 - s) ** taper
    return np.concatenate([c + nrm * half, (c - nrm * half)[::-1]])


# ── The designs ─────────────────────────────────────────────────────────────────────────────────────────────────────

def razed_logo():
    """The game's name on a black plate leaning like italic type, an orange rule under it and three orange slashes."""
    height, lean, size, spacing = 116.0, 14.0, 74.0, 8.0
    over = height / 2 * math.tan(math.radians(lean))  # how far the lean takes the plate's corners past its box
    probe = Sheet(600, height, 10)
    _, box = probe.text("RAZED", "ChakraPetch-BoldItalic.ttf", size, spacing=spacing)
    text_w = box[2] - box[0]
    left, gap, slash_w, slash_step, right = 34.0, 30.0, 13.0, 21.0, 30.0
    width = left + text_w + gap + 2 * slash_step + slash_w + right
    s = Sheet(width + 2 * over, height, 10)

    def lean_right(points):
        return skew(np.asarray(points, float) + (over, 0), lean, height / 2)

    plate_m = s.mask([lean_right(rounded_rect(0, 0, width, height, 11))])
    s.paint(s.grow(plate_m, 7.0), VINYL)
    s.paint(plate_m, INK)
    # the word's ink centred on the plate's upper part, clear of the rule
    _, box = s.text("RAZED", "ChakraPetch-BoldItalic.ttf", size, spacing=spacing, anchor=(0, 0))
    top = (16 + 80) / 2 - (box[3] - box[1]) / 2 - box[1]
    word, box = s.text("RAZED", "ChakraPetch-BoldItalic.ttf", size, spacing=spacing,
                       anchor=(over + left - box[0] + 6, top))
    s.paint(word, VINYL)
    rule = lean_right([(box[0] - over - 4, 88), (box[2] - over - 2, 88), (box[2] - over - 2, 97), (box[0] - over - 4, 97)])
    s.paint(s.mask([rule]), ORANGE)
    x = box[2] - over + gap
    slashes = [skew(np.array([(x + i * slash_step, 18), (x + i * slash_step + slash_w, 18),
                              (x + i * slash_step + slash_w, 98), (x + i * slash_step, 98)]) + (over, 0), 32, height / 2)
               for i in range(3)]
    s.paint(s.mask(slashes), ORANGE)
    return s


def ace_of_spades():
    """A playing card's ace of spades."""
    w, h = 250.0, 350.0
    s = Sheet(w, h, 2)
    card = rounded_rect(0, 0, w, h, 20)
    s.paint(s.mask([card]), (205, 199, 186))
    s.paint(s.mask([rounded_rect(2.5, 2.5, w - 2.5, h - 2.5, 17.5)]), PAPER)
    s.paint(s.mask(spade(w / 2, h / 2, 170)), INK)
    corner = []
    letter, box = s.text("A", "ChakraPetch-Bold.ttf", 52, anchor=(33, 10), align="centre")
    small = spade(33, box[3] + 20, 30)
    s.paint(letter, INK)
    s.paint(s.mask(small), INK)
    # the same index upside down in the opposite corner
    turned = np.rot90(letter, 2)
    s.paint(turned, INK)
    s.paint(np.rot90(s.mask(small), 2), INK)
    del corner
    return s


def hot_rod_flames():
    """Hot rod flames licking back from a rounded front: red outside, then orange, then a yellow core, outlined in
    black, on white vinyl."""
    w, h = 260.0, 110.0
    s = Sheet(w, h, 14)
    # centrelines of the tongues, root to tip, and their widths at the root
    tongues = [
        ((34, 40), (90, 6), (150, 52), (232, 14), 40),
        ((34, 58), (110, 82), (160, 30), (258, 56), 42),
        ((34, 76), (92, 112), (140, 64), (206, 102), 36),
        ((30, 30), (64, 6), (98, 24), (136, 2), 24),
    ]
    body = [np.array([(40 + 38 * math.cos(a), 57 + 40 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 120)])]

    def layer(scale_len, scale_w, root_shift=0.0):
        polys = []
        for p0, p1, p2, p3, wd in tongues:
            p0 = np.array(p0, float) + (root_shift, 0)
            pts = [np.array(p, float) for p in (p1, p2, p3)]
            pts = [p0 + (p - p0) * scale_len for p in pts]
            polys.append(tongue(p0, *pts, wd * scale_w))
        b = [(body[0] - (40, 57)) * (scale_w * 0.95) + (40 + root_shift, 57)]
        return polys + b

    outer = s.mask(layer(1.0, 1.0))
    s.paint(s.grow(outer, 11.0), VINYL)
    s.paint(s.grow(outer, 4.5), INK)
    s.paint(outer, RED)
    s.paint(s.mask(layer(0.78, 0.72, 6)), ORANGE)
    s.paint(s.mask(layer(0.52, 0.42, 12)), YELLOW)
    return s


def hazard_stripes():
    """Black and yellow hazard stripes on a rounded bar."""
    w, h = 280.0, 76.0
    s = Sheet(w, h, 9)
    bar = rounded_rect(0, 0, w, h, 12)
    bar_m = s.mask([bar])
    s.paint(s.grow(bar_m, 7.0), VINYL)
    s.paint(bar_m, INK)
    inner = s.mask([rounded_rect(5, 5, w - 5, h - 5, 7)])
    stripes = []
    period = 38.0
    for i in range(-3, int(w / period) + 4):
        x0 = i * period
        stripes.append([(x0, h), (x0 + period / 2, h), (x0 + period / 2 + h, 0), (x0 + h, 0)])
    s.paint(inner & s.mask(stripes), HAZARD_YELLOW)
    return s


STICKERS = {
    # file name: (display name, drawing)
    "sticker_razed_logo": ("Razed Logo", razed_logo),
    "sticker_ace_of_spades": ("Ace of Spades", ace_of_spades),
    "sticker_hot_rod_flames": ("Hot Rod Flames", hot_rod_flames),
    "sticker_hazard_stripes": ("Hazard Stripes", hazard_stripes),
}


def vmat(name: str) -> str:
    return "\n".join([
        "// Tools/weapon_stickers.py",
        '"Layer0"',
        "{",
        '    shader "shaders/complex.shader"',
        '    F_ALPHA_TEST "1"',
        '    F_SPECULAR "1"',
        '    g_flAlphaTestReference "0.5"',
        '    g_flRoughnessScaleFactor "1"',
        '    g_flMetalness "0.00"',
        f'    TextureColor "materials/stickers/{name}.png"',
        f'    TextureTranslucency "materials/stickers/{name}_mask.png"',
        '    TextureNormal "materials/default/default_normal.tga"',
        '    TextureRoughness "materials/default/default_rough_s1import.tga"',
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
        '    g_vColorTint "[1.0 1.0 1.0 1.0]"',
        "}",
        "",
    ])


def part(name: str, title: str) -> dict:
    return {
        "Name": title,
        "Category": "Sticker",
        "MainPrefab": {"_type": "gameobject", "prefab": PREFAB_PATH},
        "StickerImage": f"materials/stickers/{name}.png",
        "StickerMaterial": f"materials/stickers/{name}.vmat",
        "__references": [],
        "IsValid": True,
        "__version": 0,
    }


def prefab() -> dict:
    guid = lambda key: str(uuid.uuid5(NAMESPACE, key))  # noqa: E731
    return {
        "RootObject": {
            "__guid": guid("sticker"),
            "Flags": 0,
            "Name": "sticker",
            "Enabled": True,
            "Components": [
                {"__type": "Facepunch.Gunsmith.GunsmithSticker", "__guid": guid("sticker/component")},
                {
                    "__type": "Sandbox.ModelRenderer",
                    "__guid": guid("sticker/renderer"),
                    "BodyGroups": 18446744073709551615,
                    "RenderOptions": {"GameLayer": True, "OverlayLayer": True, "BloomLayer": False,
                                      "AfterUILayer": False},
                    "RenderType": "On",
                    "Tint": "1,1,1,1",
                },
            ],
            "Children": [],
            "__variables": [],
        },
        "ShowInMenu": False,
        "MenuPath": None,
        "MenuIcon": None,
        "DontBreakAsTemplate": False,
        "ResourceVersion": 1,
        "__references": [],
        "IsValid": True,
        "__version": 1,
    }


def preview(path: Path, images: dict) -> None:
    tiles = []
    for name, img in images.items():
        im = Image.fromarray(img, "RGBA")
        im.thumbnail((460, 300), Image.LANCZOS)
        tiles.append(im)
    width = sum(t.width for t in tiles) + 40 * (len(tiles) + 1)
    height = max(t.height for t in tiles) * 2 + 120
    sheet = Image.new("RGB", (width, height), (70, 72, 76))
    x = 40
    for t in tiles:
        sheet.paste(t, (x, 40), t)
        # on dark gunmetal too
        dark = Image.new("RGB", (t.width + 40, t.height + 40), (34, 35, 38))
        sheet.paste(dark, (x - 20, t.height + 80 - 20 + 20))
        sheet.paste(t, (x, t.height + 80 + 20), t)
        x += t.width + 40
    sheet.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", type=Path, help="draw the stickers on a sheet here and write nothing else")
    args = parser.parse_args()
    images = {name: draw().finish() for name, (_, draw) in STICKERS.items()}
    if args.preview:
        preview(args.preview, images)
        print(args.preview)
        return
    ART.mkdir(parents=True, exist_ok=True)
    PARTS.mkdir(parents=True, exist_ok=True)
    PREFAB.parent.mkdir(parents=True, exist_ok=True)
    for name, (title, _) in STICKERS.items():
        img = images[name]
        Image.fromarray(img, "RGBA").save(ART / f"{name}.png", optimize=True)
        Image.fromarray(img[..., 3], "L").save(ART / f"{name}_mask.png", optimize=True)
        (ART / f"{name}.vmat").write_text(vmat(name), encoding="utf-8", newline="\n")
        (PARTS / f"{name}.gnsmth").write_text(json.dumps(part(name, title), indent=2) + "\n", encoding="utf-8",
                                              newline="\n")
        print(f"{name}: {img.shape[1]}x{img.shape[0]}")
    PREFAB.write_text(json.dumps(prefab(), indent=2) + "\n", encoding="utf-8", newline="\n")
    print(PREFAB)


if __name__ == "__main__":
    main()
