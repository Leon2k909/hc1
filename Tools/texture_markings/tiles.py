"""Write review tiles of a material's colour map, shaded by its normal map, with a pixel grid in colour-map coordinates.

usage: python tiles.py <vmat> [<vmat> ...] [--tile 1024] [--overview-only]

Writes out/<vmat stem>/overview.png (the whole map, at most 1024 px) and, for maps bigger than the tile size,
tile_<x>_<y>.png crops at full resolution. Grid lines every 64 px, labelled every 256 px (cyan = x, magenta = y).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

import texlib as T


def write_tiles(vmat: str, tile: int, overview_only: bool) -> list[Path]:
    maps = T.vmat_maps(vmat)
    if "TextureColor" not in maps:
        print(f"{vmat}: no colour map")
        return []
    color, _ = T.load(maps["TextureColor"])
    normal = T.load(maps["TextureNormal"])[0] if "TextureNormal" in maps else None
    lit = T.lit_preview(color, normal)
    h, w = lit.shape[:2]
    out = T.OUT / Path(vmat).stem
    out.mkdir(parents=True, exist_ok=True)
    written = []
    scale = min(1.0, 1024 / max(w, h))
    ov = Image.fromarray(np.clip(lit, 0, 255).astype(np.uint8)).resize((max(1, int(w * scale)), max(1, int(h * scale))),
                                                                         Image.LANCZOS)
    ov_arr = np.asarray(ov).astype(np.float32)
    step = 128 if max(w, h) > 1024 else 64
    im = T.grid_image(ov_arr, 0, 0, step=step, label_every=step * 2 if max(w, h) > 1024 else 256, scale=scale)
    path = out / "overview.png"
    im.save(path)
    written.append(path)
    if overview_only or max(w, h) <= tile:
        if max(w, h) <= tile:
            full = T.grid_image(lit, 0, 0)
            path = out / "full.png"
            full.save(path)
            written.append(path)
        return written
    for y0 in range(0, h, tile):
        for x0 in range(0, w, tile):
            crop = lit[y0:y0 + tile, x0:x0 + tile]
            path = out / f"tile_{x0}_{y0}.png"
            T.grid_image(crop, x0, y0).save(path)
            written.append(path)
    return written


def main() -> None:
    args = sys.argv[1:]
    tile = 1024
    overview_only = "--overview-only" in args
    if "--tile" in args:
        tile = int(args[args.index("--tile") + 1])
    vmats = [a for a in args if a.endswith(".vmat")]
    for vmat in vmats:
        for path in write_tiles(vmat, tile, overview_only):
            print(path)


if __name__ == "__main__":
    main()
