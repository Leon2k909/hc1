"""Bake architectural weathering data from Lowtide's actual warehouse openings.

RGB is numerical shader data: contact occlusion, rain deposits, lime deposits.
Four wall elevations across, east/west buildings down. No scene or mesh writes.
"""
import json
import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K
from lowtide_brick import metadata

CELL = 1024
PAD = 8
Z_RANGE = (0.0, 1024.0)
RESOURCE = "materials/lowtide/masonry/facade_wear.png"


def layout(L):
    records = []
    original = L.window
    def collect(model, wall, opening, style, pane=None, glass=None):
        depth, _, _ = L.wall_out(wall)
        if wall.axis == "n" and depth in (L.SPEICHER[0], L.SPEICHER[1]):
            cell = 0 if depth == L.SPEICHER[0] else 1
        elif wall.axis == "e" and depth in (L.SPEICHER[2], L.SPEICHER[3]):
            cell = 2 if depth == L.SPEICHER[3] else 3
        else:
            return
        records.append({"cell": cell, "r0": opening.r0, "r1": opening.r1,
                        "sill": opening.z0 - 4.4, "head": opening.z1})
    try:
        L.window = collect
        L.speicher(K.Model(), K.Model(), L.EAST)
    finally:
        L.window = original
    return records


def smooth_noise(rng, shape, grid):
    values = rng.random(grid)
    return ndimage.zoom(values, (shape[0] / grid[0], shape[1] / grid[1]), order=1)


def elevation(L, records, column, side):
    rng = np.random.default_rng(95173 + column * 179 + side * 531)
    size = CELL - 2 * PAD
    run = L.SPEICHER[2:] if column < 2 else L.SPEICHER[:2]
    horizontal = np.linspace(*run, size)
    vertical = np.linspace(Z_RANGE[1], Z_RANGE[0], size)
    width_noise = smooth_noise(rng, (size, size), (22, 290))
    patches = smooth_noise(rng, (size, size), (31, 23))
    result = np.zeros((size, size, 3), dtype=np.float32)
    for record in (r for r in records if r["cell"] == column):
        r0, r1, top = record["r0"] - 4.2, record["r1"] + 4.2, record["sill"]
        depth = rng.uniform(22, 65)
        xi = np.flatnonzero((horizontal >= r0 - 5) & (horizontal <= r1 + 5))
        yi = np.flatnonzero((vertical <= top + 1) & (vertical >= top - depth))
        if not len(xi) or not len(yi):
            continue
        section = np.s_[yi[0]:yi[-1]+1, xi[0]:xi[-1]+1]
        x = horizontal[xi][None, :]
        drop = np.maximum(top - vertical[yi, None], 0)
        span = np.clip((x - r0 + 2) / 4, 0, 1) * np.clip((r1 + 2 - x) / 4, 0, 1)
        contact = np.exp(-drop / 2.3) * span * .8
        # Stronger deposits at the stone's edges, with narrow irregular runs.
        edge = np.maximum(np.exp(-((x-r0-3)/4.8)**2), np.exp(-((x-r1+3)/4.8)**2))
        streak = np.clip((width_noise[section] - .24) * 1.65, 0, 1)
        fade = np.maximum(1 - drop / depth, 0) ** 1.8
        wear = (span * .15 + edge * .78) * streak * fade * rng.uniform(.35, 1.0)
        salt = wear * np.clip((patches[section] - .62) * 3, 0, 1) * rng.uniform(.0, .65)
        stamp = np.stack(np.broadcast_arrays(contact, wear, salt), axis=-1)
        result[section] = np.maximum(result[section], stamp)
    # Deposits and a small contact term under projecting floor courses/eaves.
    x, z = horizontal[None, :], vertical[:, None]
    for top in [v-11 for v in L.LEVELS] + [L.EAVES-22]:
        drop = top-z
        below = (drop >= 0)
        contact = np.exp(-np.maximum(drop, 0)/2.8) * below * .42
        dirt = np.exp(-np.maximum(drop, 0)/11) * below * (.20 + width_noise*.3) * (.4 + patches*.6)
        result[..., 0] = np.maximum(result[..., 0], contact)
        result[..., 1] = np.maximum(result[..., 1], dirt)
    # Local soot in the recess beside the raised masonry pilasters.
    pilasters = (-120, 270, 660, 1050) if column < 2 else (370, 870)
    start = L.CEILING + 16 if column < 2 else 0
    for centre in pilasters:
        edge_distance = np.abs(np.abs(x-centre)-10)
        term = np.exp(-edge_distance/2.5) * (z >= start) * (z <= L.EAVES-36)
        result[..., 0] = np.maximum(result[..., 0], term*.4)
        result[..., 1] = np.maximum(result[..., 1], term*(.16 + patches*.16))
    return np.pad(np.rint(np.clip(result, 0, 1)*255).astype(np.uint8),
                  ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")


def bake(L):
    # Kept explicit in the shader so every pixel avoids dynamic layout lookups.
    # A layout change must update that mapping before rebaking this mask.
    assert tuple(L.SPEICHER) == (240, 1000, -400, 1150)
    records = layout(L)
    atlas = np.concatenate([np.concatenate([elevation(L, records, c, s) for c in range(4)], axis=1)
                            for s in range(2)], axis=0)
    path = K.ASSETS / RESOURCE
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(atlas).save(path)
    metadata(path)
    report = {"meaning": ["contact", "rain deposits", "lime deposits"],
              "size": list(atlas.shape[1::-1]), "cell_size": CELL, "padding": PAD,
              "z_range": Z_RANGE, "speicher": L.SPEICHER,
              "openings_per_building": len(records), "openings": records}
    folder = K.ROOT / "output/lowtide/quality-pass"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "facade-layout.json").write_text(json.dumps(report, indent=2)+"\n")
    print(f"Baked {atlas.shape[1]}x{atlas.shape[0]} facade data for {len(records)*2} window sills and eight wall elevations")
    from lowtide_shed_weathering import bake as bake_sheds
    bake_sheds(L)


if __name__ == "__main__":
    import lowtide_map as L
    bake(L)
