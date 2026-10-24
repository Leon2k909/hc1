"""
The soldier training medal's badge, Assets/ui/medals/training.png, which MedalFeed shows when a skill levels up.

    python Tools/training_emblem.py [--preview <png>]

The medal art is image-generated (Tools/ranked_emblems/prompts.json), and there's no generator to hand, so this badge
is derived from the plain Ranked shield (Assets/ui/ranked/unranked.png): the same steel frame round an empty diamond.
- The frame is warmed to brass, so it doesn't read as a Ranked tier emblem (those are steel or a solid tier colour, and
  Ranked's gold has chevrons in it). The dark field and the shadows stay gunmetal.
- The diamond, transparent in the shield, is filled with a dark gunmetal field under an inner shadow. MedalFeed draws
  the new level's number over it (.medal-level), centred on the diamond: x 49.9%, y 50.1% of the image.
--preview also writes the badge over a mid-grey and a dark ground, to check its edges.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SOURCE = os.path.join(ROOT, "Assets", "ui", "ranked", "unranked.png")
OUT = os.path.join(ROOT, "Assets", "ui", "medals", "training.png")
CENTRE = (627, 627)  # inside the diamond

# Brass by brightness: the steel's shadows, mid tones and highlights.
BRASS = np.array([
    (0.00, (0.05, 0.04, 0.03)),
    (0.30, (0.30, 0.21, 0.10)),
    (0.55, (0.66, 0.48, 0.22)),
    (0.78, (0.90, 0.74, 0.44)),
    (1.00, (1.00, 0.95, 0.80)),
], dtype=object)


def brass(lum):
    stops = np.array([s for s, _ in BRASS], dtype=np.float32)
    colours = np.array([c for _, c in BRASS], dtype=np.float32)
    return np.stack([np.interp(lum, stops, colours[:, i]) for i in range(3)], axis=-1)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def build():
    src = np.asarray(Image.open(SOURCE).convert("RGBA")).astype(np.float32) / 255.0
    rgb, alpha = src[..., :3], src[..., 3]
    h, w = alpha.shape

    # Warm the bright steel (the frame and the diamond's bevels) to brass; leave the dark field near gunmetal.
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    warmth = smoothstep(0.22, 0.5, lum) * 0.9
    warmed = rgb * (1.0 - warmth[..., None]) + brass(lum * 1.08) * warmth[..., None]

    # The diamond: the transparent region round the centre, grown a little to sit under its soft edge.
    labels, _ = ndimage.label(alpha < 0.5)
    hole = labels == labels[CENTRE[1], CENTRE[0]]
    ys, xs = np.nonzero(hole)
    print(f"diamond: x {xs.min()}-{xs.max()}, y {ys.min()}-{ys.max()}, "
          f"centre {100 * (xs.min() + xs.max()) / 2 / w:.1f}% {100 * (ys.min() + ys.max()) / 2 / h:.1f}%")
    under = ndimage.binary_dilation(hole, iterations=4)

    # Its field: dark gunmetal, a touch lighter in the middle, with fine grain, shaded in from its edges.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    radius = (xs.max() - xs.min()) / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    rng = np.random.default_rng(7)
    grain = ndimage.gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 1.2) * 0.012
    base = 0.075 + 0.05 * np.clip(1.0 - r, 0.0, 1.0) + grain
    edge = ndimage.distance_transform_edt(hole)
    shadow = np.exp(-edge / 26.0) * 0.75
    # Light from above: the lower inside edge catches a thin highlight.
    lip = np.exp(-edge / 3.0) * smoothstep(0.0, 0.6, (yy - cy) / radius) * 0.10
    field_v = np.clip(base * (1.0 - shadow) + lip, 0.0, 1.0)
    field = np.stack([field_v * 0.95, field_v * 0.98, field_v * 1.06], axis=-1)

    # The shield over its field.
    a = alpha[..., None]
    fill = under[..., None].astype(np.float32)
    out_rgb = warmed * a + field * (1.0 - a) * fill
    out_a = np.maximum(alpha, under.astype(np.float32))
    out_rgb = np.where(out_a[..., None] > 0, out_rgb / np.maximum(out_a[..., None], 1e-6), 0.0)

    image = np.concatenate([np.clip(out_rgb, 0, 1), out_a[..., None]], axis=-1)
    return Image.fromarray((image * 255 + 0.5).astype(np.uint8), "RGBA")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", help="also write the badge over two grounds to this PNG")
    args = parser.parse_args()

    badge = build()
    tmp = OUT + ".tmp.png"
    badge.save(tmp, optimize=True)
    os.replace(tmp, OUT)
    print("wrote", os.path.relpath(OUT, ROOT))

    if args.preview:
        small = badge.resize((400, 400), Image.LANCZOS)
        sheet = Image.new("RGBA", (800, 400), (0, 0, 0, 255))
        for i, ground in enumerate([(128, 128, 128, 255), (18, 20, 24, 255)]):
            tile = Image.new("RGBA", (400, 400), ground)
            tile.alpha_composite(small)
            sheet.paste(tile, (400 * i, 0))
        sheet.convert("RGB").save(args.preview)
        print("preview", args.preview)


if __name__ == "__main__":
    sys.exit(main())
