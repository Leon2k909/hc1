"""Paint the bollard's maps from its bakes: python paint_bollard.py <work dir> <output dir>

Cast iron on a salt-water quay: coats of black bitumen flaking to rust, deepest at the foot where the wet stands and on the head's lip, with
rust running down the paint. Ropes have polished its neck to dull bare iron on the harbour side. Salt bloom at the foot, and a made-up
foundry mark cast into the neck. Wear is worked out in 3D.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

PAINT, ZINC = 0, 3
NAME = "mooring_bollard"
facts = json.load(open(os.path.join(WORK, f"{NAME}.json")))
density, RANGE, FLANGE = facts["density"], facts["range"], facts["flange"]
pos4 = load(f"bake_{NAME}_pos")
nor4 = load(f"bake_{NAME}_nor")
facts4 = load(f"bake_{NAME}_facts")
ao4 = load(f"bake_{NAME}_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
pos, nor, finish = fill_from(cover, pos, nor, finish)
# The AO bake's alpha is 1 everywhere, so its value is what says which texels it covered.
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

# Turned off the axes: on a surface square to the lattice, low-frequency noise thresholds into square-edged patches.
TURN = np.array(((0.70, -0.42, 0.58), (0.61, 0.77, -0.19), (-0.37, 0.48, 0.79)), np.float32)


def noise(p, freq, seed=0, octaves=1):
    return lattice_noise(p @ TURN, freq, seed, octaves)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
radial = np.hypot(X, Y)
theta = np.arctan2(Y, X)
iron = finish == PAINT
bolt = finish == ZINC
upward = np.clip(nor[..., 2], 0, 1)
crevice = np.clip((1 - ao) * 1.4, 0, 1)
d, _ = cKDTree(np.load(os.path.join(WORK, f"{NAME}_edges.npy"))).query(pts.astype(np.float64), k=1, distance_upper_bound=1.0, workers=4)
edge = smooth(0.26, 0.03, field(np.where(np.isfinite(d), d, 1.0).astype(np.float32)))
curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
rolled = ndi.gaussian_filter(np.clip((curve - 0.55) * 0.5, 0, 1), 1.0)
edge = np.clip(np.maximum(edge, rolled * 1.4), 0, 1)

big = field(noise(pts, 0.16, 1, 3))
mid = field(noise(pts, 0.8, 2, 4))
fine = field(noise(pts, 3.2, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))

# Cast lettering round the neck, and the mould's seam up both sides.
mark = stencil_image(["RZD FOUNDRY  T.4"], (1500, 150), bridge=False)
arc = (theta - math.radians(180) + math.pi) % (2 * math.pi) - math.pi
cast = np.where(iron & (radial < 6.8), sample_image(mark, arc * 6.1 / 13.5 + 0.5, (Z - 15.0) / 1.25), 0)
cast = ndi.gaussian_filter(cast, 0.6)
seam = np.minimum(np.abs((theta - math.pi / 2 + math.pi) % (2 * math.pi) - math.pi), np.abs((theta + math.pi / 2 + math.pi) % (2 * math.pi) - math.pi)) * radial
seam = smooth(0.13, 0.04, seam) * iron * (np.abs(nor[..., 2]) < 0.7)

# Where the wet stands, and where ropes run: the neck, on the harbour side, which is -X here and turned to the water when placed.
low = smooth(5.0, 0.5, Z) * iron
lip = smooth(1.0, 0.1, np.abs(Z - 20.8)) * iron
harbour = smooth(-0.15, 0.85, -np.cos(theta))
rope_band = smooth(6.4, 8.2, Z) * smooth(16.2, 13.8, Z) * harbour * iron
rub = field(noise(pts * np.array((0.6, 0.6, 16.0), np.float32), 1.0, 22, 3))
rope = rope_band * smooth(0.28, 0.58, rub + harbour * 0.1)

chip = 0.09 + edge * (0.25 + 0.75 * smooth(0.3, 0.7, mid * 0.5 + fine * 0.5)) + (fine - 0.5) * 0.3 + (mid - 0.5) * 0.36 + (big - 0.5) * 0.14 + low * 0.2 * smooth(0.3, 0.7, mid) + lip * 0.16 + cast * 0.12 + seam * 0.14
to_rust = ndi.gaussian_filter(smooth(0.58, 0.65, chip), 0.5)
to_deep = ndi.gaussian_filter(smooth(0.73, 0.82, chip), 0.5)

# Rust running down the paint from the flaked places: laid out flat by angle and height, and run downhill.
ROWS, COLS = 512, 1024
grid = np.zeros((ROWS, COLS), np.float32)
hot = iron & (to_rust > 0.5) & cover & (radial > 5.9)
rows = np.clip((Z[hot] / 25.0 * (ROWS - 1)).astype(np.int32), 0, ROWS - 1)
cols = np.clip(((theta[hot] + math.pi) / (2 * math.pi) * COLS).astype(np.int32), 0, COLS - 1)
np.maximum.at(grid, (rows, cols), to_rust[hot])
stain = np.random.default_rng(206).uniform(0.975, 0.996, COLS).astype(np.float32)
for row in range(ROWS - 2, -1, -1):
    grid[row] = np.maximum(grid[row], grid[row + 1] * stain)
grid = ndi.gaussian_filter(grid, (0.7, 0.8), mode=("nearest", "wrap"))
runs = ndi.map_coordinates(grid, (np.clip(Z / 25.0, 0, 1) * (ROWS - 1), (theta + math.pi) / (2 * math.pi) * COLS), order=1, mode="grid-wrap").astype(np.float32)
runs = np.clip(runs, 0, 1) * (np.abs(nor[..., 2]) < 0.85) * iron * smooth(0.3, 0.7, field(noise(pts * np.array((5.0, 5.0, 0.2), np.float32), 1.0, 5, 3)))

bitumen = rgb(30, 30, 32) * (0.82 + 0.36 * mid[..., None])
bitumen = mix(bitumen, rgb(58, 56, 54), smooth(0.2, 0.9, upward * 0.7 + (big - 0.5) * 0.6) * 0.5)
rust = mix(rgb(66, 38, 22), rgb(128, 74, 38), smooth(0.3, 0.75, fine + (mid - 0.5) * 0.4))
deep = mix(rgb(44, 26, 18), rgb(82, 46, 26), smooth(0.3, 0.75, micro))
color = mix(bitumen, rust, np.clip(to_rust + runs * 0.42, 0, 1))
color = mix(color, deep, to_deep)
bare = rgb(116, 110, 100) * (0.8 + 0.3 * rub[..., None])
color = mix(color, bare, rope * 0.86)
rough = 0.42 + 0.14 * mid + 0.06 * fine + 0.12 * big
rough = rough * (1 - to_rust) + (0.78 + 0.12 * fine) * to_rust
rough = rough * (1 - rope * 0.9) + 0.3 * rope * 0.9
metal = rope * 0.8 * (1 - to_deep)
height = 0.004 * (fine - 0.5) + 0.0025 * (micro - 0.5) + 0.028 * (field(noise(pts, 0.7, 12, 2)) - 0.5) + (1 - to_rust) * 0.012 + (1 - to_deep) * 0.012 + to_deep * 0.018 * micro + cast * 0.05 + seam * 0.035 - rope * 0.006 * rub

# The bolts: rusted through their paint.
b_color = mix(rust * 0.8, rgb(40, 38, 36), smooth(0.4, 0.75, fine) * 0.5)
color = np.where(bolt[..., None], b_color, color)
rough = np.where(bolt, 0.74 + 0.12 * fine, rough)
metal = np.where(bolt, 0.0, metal)
height = np.where(bolt, 0.004 * (micro - 0.5), height)

# Salt where the spray dries, gull droppings on the head, and dirt round the foot.
salt = np.clip(smooth(0.15, 0.6, crevice) * 0.3 + low * smooth(0.45, 0.75, mid * 0.5 + fine * 0.5) * 0.46, 0, 0.7)
color = mix(color, rgb(178, 176, 164) * (0.76 + 0.4 * fine[..., None]), salt)
rough = rough * (1 - salt) + 0.92 * salt
guano = iron * upward * smooth(19.0, 24.0, Z) * smooth(0.7, 0.8, field(noise(pts, 2.6, 26, 3)) + (fine - 0.5) * 0.3)
color = mix(color, rgb(172, 168, 152) * (0.8 + 0.3 * fine[..., None]), guano * 0.5)
rough = rough * (1 - guano) + 0.86 * guano
metal = metal * (1 - np.maximum(salt, guano))
grime = np.clip(smooth(0.42, 0.9, crevice + (mid - 0.5) * 0.4) * 0.6, 0, 0.8)
color = mix(color, rgb(46, 40, 32) * (0.75 + 0.45 * fine[..., None]), grime)
rough = rough * (1 - grime * 0.6) + 0.88 * grime * 0.6
color = color * (0.64 + 0.36 * ao[..., None])

normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border
# takes its normal from just inside. Islands too thin to have an inside keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("bollard painted", flush=True)
