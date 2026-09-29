"""Zoom into part of a material's colour map (shaded by its normal map), with a grid in colour-map pixels.

usage: python zoom.py <vmat> <x> <y> <w> <h> [--scale N] [--raw] [--map TextureNormal] [--out name.png]

--raw shows the plain map instead of the shaded preview; --map picks another of the vmat's maps (shown plain).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

import texlib as T


def main() -> None:
    args = sys.argv[1:]
    vmat, x, y, w, h = args[0], *map(int, args[1:5])
    scale = int(args[args.index("--scale") + 1]) if "--scale" in args else max(1, min(6, 900 // max(w, h)))
    map_key = args[args.index("--map") + 1] if "--map" in args else "TextureColor"
    out_name = args[args.index("--out") + 1] if "--out" in args else f"zoom_{map_key}_{x}_{y}_{w}x{h}.png"
    maps = T.vmat_maps(vmat)
    color, _ = T.load(maps["TextureColor"])
    ch, cw = color.shape[:2]
    if map_key != "TextureColor" or "--raw" in args:
        img, _ = T.load(maps[map_key])
        img = T.resize_to(img, (ch, cw))
        if img.shape[2] == 1:
            img = np.repeat(img, 3, axis=2)
        img = img[:, :, :3]
    else:
        normal = T.load(maps["TextureNormal"])[0] if "TextureNormal" in maps else None
        img = T.lit_preview(color, normal)
    x0, y0 = max(0, x), max(0, y)
    crop = img[y0:y0 + h, x0:x0 + w]
    big = np.asarray(Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8)).resize(
        (crop.shape[1] * scale, crop.shape[0] * scale), Image.NEAREST)).astype(np.float32)
    step = 8 if max(w, h) <= 160 else 16 if max(w, h) <= 400 else 32
    im = T.grid_image(big, x0, y0, step=step, label_every=step * 4, scale=scale)
    out = T.OUT / Path(vmat).stem
    out.mkdir(parents=True, exist_ok=True)
    im.save(out / out_name)
    print(out / out_name)


if __name__ == "__main__":
    main()
