"""Paint the drum's maps from its bakes: python paint_oil_drum.py <work dir> <output dir>

Enamel over primer over steel, left out in a container yard: chipped along the chimes and hoops where a drum gets rolled and
knocked, rust at the chips running down the paint, dust on the head and a dark spill round its bungs. No bullet damage, since players
shoot these themselves. Shared roughness, metalness, normal and AO, with a colour map per paint. All the lettering is made
up. Wear is worked out in 3D.
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
facts = json.load(open(os.path.join(WORK, "oil_drum.json")))
density, RANGE, R, TOP, HEAD_Z = facts["density"], facts["range"], facts["radius"], facts["top"], facts["head_z"]
HOOPS, BEADS = facts["hoops"], facts["beads"]
NAME = "oil_drum"
# name: enamel, what's stencilled on it, a seed for its own tone and dirt.
DRUMS = {
    "blue": ((30, 62, 112), (46, 82, 134), ("LUBE OIL 46", "NET 205 L"), 21),
    "red": ((122, 30, 26), (148, 50, 38), ("SOLVENT 12", "NET 205 L"), 22),
}

pos4 = load("bake_od_pos")
nor4 = load("bake_od_nor")
facts4 = load("bake_od_facts")
ao4 = load("bake_od_ao")
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
paint_area = finish == PAINT
zinc = finish == ZINC
on_head = paint_area & (radial < 10.85) & (nor[..., 2] > 0.5)
wall = paint_area & ~on_head

edge_points = np.load(os.path.join(WORK, "oil_drum_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=1.5, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 1.5).astype(np.float32))
curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
# A drum's own curvature is about 0.09 per inch, so only what's rolled tighter than its bodywork counts as an edge.
rolled = ndi.gaussian_filter(np.clip((curve - 0.9) * 0.45, 0, 1), 1.0)
edge = np.clip(np.maximum(smooth(0.22, 0.02, edge_d), rolled * 1.5), 0, 1)
print("edges measured", len(edge_points), flush=True)

big = field(noise(pts, 0.1, 1, 3))
mid = field(noise(pts, 0.55, 2, 4))
fine = field(noise(pts, 2.8, 3, 3))
micro = field(noise(pts, 10.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
# The hoops take the knocks when a drum is rolled, the chimes when it's dropped or walked on its rim.
hoop_d = np.minimum(np.abs(Z - HOOPS[0]), np.abs(Z - HOOPS[1]))
rim_d = np.minimum(Z, TOP - Z)
knocks = wall * np.clip(smooth(0.5, 0.05, hoop_d) * 0.9 + smooth(0.9, 0.05, rim_d), 0, 1) * radial.clip(0, 12) / 12
# Dents crack the paint. These match the build's DENTS.
dents = np.zeros((H, W), np.float32)
for deg, at, wide, high in ((78.0, 7.0, 3.8, 2.6), (205.0, 27.2, 3.2, 3.8), (312.0, 17.6, 5.0, 2.3), (140.0, 23.1, 2.8, 1.5), (25.0, 2.6, 3.0, 1.5)):
    arc = (theta - math.radians(deg) + math.pi) % (2 * math.pi) - math.pi
    dents = np.maximum(dents, np.exp(-((arc * R / wide) ** 2) - ((Z - at) / high) ** 2))
dents *= wall

# Scratches, level from being stood against things, or running down.
r = np.random.default_rng(205)
lines, widths = [], []
for _ in range(70):
    x0, y0 = r.uniform(-7.0, 7.0, 2)
    length = float(r.uniform(1.0, 6.0))
    w = float(r.uniform(0.045, 0.09))
    turn = r.uniform(-math.pi, math.pi)
    steps = max(4, int(length / 0.04))
    for k in range(steps):
        f = k / (steps - 1)
        lines.append((x0 + math.cos(turn) * (f - 0.5) * length, y0 + math.sin(turn) * (f - 0.5) * length, HEAD_Z + 0.01))
        widths.append(w * (1 - abs(f - 0.5) * 1.3))
for _ in range(190):
    a = r.uniform(-math.pi, math.pi)
    z0 = r.uniform(1.0, 33.5)
    length = float(r.uniform(1.0, 8.0))
    w = float(r.uniform(0.045, 0.1))
    tilt = r.normal(0.0, 0.22) + (math.pi / 2 if r.random() < 0.22 else 0.0)
    steps = max(4, int(length / 0.04))
    for k in range(steps):
        f = k / (steps - 1)
        along = (f - 0.5) * length
        at = a + along * math.cos(tilt) / R
        lines.append((R * math.cos(at), R * math.sin(at), z0 + along * math.sin(tilt)))
        widths.append(w * (1 - abs(f - 0.5) * 1.3))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines, np.float32)).query(pts, k=1, distance_upper_bound=0.16, workers=4)
which = np.minimum(which, len(widths) - 1)
scratch = ndi.gaussian_filter(field(smooth(1.0, 0.4, np.where(np.isfinite(dist), dist, 1.0) / widths[which]).astype(np.float32)), 0.6) * paint_area

chip = (
    edge * (0.2 + 0.72 * smooth(0.3, 0.72, mid * 0.5 + fine * 0.5))
    + knocks * (mid - 0.34) * 0.7
    + (fine - 0.5) * 0.24
    + (mid - 0.5) * 0.22
    + (big - 0.5) * 0.1
    + dents * smooth(0.42, 0.72, fine) * 0.42
    + scratch * 0.46
)
to_primer = ndi.gaussian_filter(smooth(0.6, 0.66, chip), 0.6)
to_steel = ndi.gaussian_filter(smooth(0.71, 0.77, chip), 0.6)

# Rust runs down from a chip. On a cylinder that's easy to do flat: lay the chips out by angle and height, and run them downhill.
ROWS, COLS = 1024, 2800
grid = np.zeros((ROWS, COLS), np.float32)
hot = wall & (to_primer > 0.5) & cover
rows = np.clip((Z[hot] / TOP * (ROWS - 1)).astype(np.int32), 0, ROWS - 1)
cols = np.clip(((theta[hot] + math.pi) / (2 * math.pi) * COLS).astype(np.int32), 0, COLS - 1)
np.maximum.at(grid, (rows, cols), to_primer[hot])
stain = np.random.default_rng(206).uniform(0.982, 0.9965, COLS).astype(np.float32)
for row in range(ROWS - 2, -1, -1):
    grid[row] = np.maximum(grid[row], grid[row + 1] * stain)
grid = ndi.gaussian_filter(grid, (0.7, 0.7), mode=("nearest", "wrap"))
runs = ndi.map_coordinates(grid, (np.clip(Z / TOP, 0, 1) * (ROWS - 1), (theta + math.pi) / (2 * math.pi) * COLS), order=1, mode="grid-wrap").astype(np.float32) * wall
runs = np.clip(runs, 0, 1) * smooth(0.25, 0.7, field(noise(pts * np.array((7.0, 7.0, 0.2), np.float32), 1.0, 5, 3)))

# The head: water stands in its dish, so there's a rust ring just inside the chime, and something has been spilt round the big bung.
head_ring = on_head * smooth(9.0, 10.0, radial + (mid - 0.5) * 2.4) * smooth(0.36, 0.62, mid * 0.35 + fine * 0.65)
spill = on_head * smooth(2.9, 2.0, np.hypot(X - 6.5, Y) + (mid - 0.5) * 2.6 + (fine - 0.5) * 1.1)
drip = wall * smooth(0.5, 0.08, np.abs(((theta + 0.05 + math.pi) % (2 * math.pi) - math.pi) * R + (field(noise(pts * np.array((0.3, 0.3, 0.3), np.float32), 1.0, 9, 2)) - 0.5) * 3.0)) * smooth(14.0, 33.0, Z)
upper = smooth(0.5, 0.75, field(noise(pts * np.array((0.4, 0.4, 0.14), np.float32), 1.0, 10, 2)))
drip = drip * upper

rough = 0.36 + 0.12 * mid + 0.05 * fine + 0.14 * big + on_head * 0.14
rough = rough * (1 - to_primer) + (0.6 + 0.12 * fine) * to_primer
rough = rough * (1 - to_steel) + (0.38 + 0.18 * fine) * to_steel
rust_mask = np.clip(to_steel * smooth(0.42, 0.72, field(noise(pts, 3.2, 11, 3))) + runs * 0.3 + head_ring * 0.62, 0, 1)
rough = rough * (1 - rust_mask) + (0.84 + 0.1 * fine) * rust_mask
rough = rough * (1 - spill * 0.8) + 0.16 * spill * 0.8
rough = rough * (1 - drip * 0.7) + 0.2 * drip * 0.7
metal = np.clip(to_steel * (1 - rust_mask) * 0.95, 0, 1)
weld = wall * smooth(0.13, 0.05, np.abs(((theta + math.pi) % (2 * math.pi) - math.pi) * R))
ripple = 0.5 + 0.5 * np.sin(Z * 2 * math.pi / 0.36)
height = 0.0028 * (fine - 0.5) + 0.0016 * (micro - 0.5) + 0.03 * (field(noise(pts, 0.2, 12, 2)) - 0.5)
height = height + (1 - to_primer) * 0.006 + (1 - to_steel) * 0.003 + rust_mask * 0.006 * fine + weld * (0.022 + 0.008 * ripple) - scratch * 0.003

zinc_tarnish = smooth(0.3, 0.75, field(noise(pts, 3.0, 13, 3)))
rough = np.where(zinc, 0.42 + 0.26 * zinc_tarnish, rough)
metal = np.where(zinc, 1.0 - zinc_tarnish * 0.25, metal)
height = np.where(zinc, 0.002 * (micro - 0.5), height)

settled = smooth(0.5, 0.92, upward * 0.74 + (big - 0.5) * 0.4 + (mid - 0.5) * 0.25)
gathered = smooth(0.1, 0.55, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4)
grit = smooth(0.28, 0.62, fine * 0.55 + micro * 0.45)
dust = np.clip(settled * 0.66 * (0.3 + 0.7 * grit) + gathered * 0.42, 0, 0.8) * (1 - spill * 0.8)
low = smooth(9.0, 0.5, Z)
splash = low * smooth(0.3, 0.72, mid * 0.5 + fine * 0.35 + low * 0.35) * wall
grime = np.clip(smooth(0.42, 0.9, crevice + (mid - 0.5) * 0.4) * 0.62 + splash * 0.55, 0, 0.9)
rough = rough * (1 - dust) + 0.9 * dust
rough = rough * (1 - grime * 0.6) + 0.86 * grime * 0.6
metal = metal * (1 - np.maximum(dust, grime))


def colour_map(enamel, faded, words, seed):
    own = field(noise(pts, 0.14, seed, 3))
    own_mid = field(noise(pts, 0.7, seed + 10, 3))
    paint = mix(rgb(*enamel), rgb(*faded), smooth(0.3, 0.8, own * 0.6 + upward * 0.5))
    paint = paint * (0.88 + 0.24 * mid[..., None]) * (0.93 + 0.14 * own_mid[..., None])
    # Lettering on two sides, as drums have, so one always shows. Azimuth runs left to right seen from outside.
    stencil = stencil_image(list(words), (1500, 560), bridge=True)
    ink = np.zeros((H, W), np.float32)
    for centre in (math.radians(90), math.radians(270)):
        arc = (theta - centre + math.pi) % (2 * math.pi) - math.pi
        ink = np.maximum(ink, np.where(wall & (radial > 10.9), sample_image(stencil, arc * R / 16.0 + 0.5, (Z - 13.3) / 8.4), 0))
    worn = smooth(0.42, 0.62, field(noise(pts, 4.0, seed + 20, 3)) + (own_mid - 0.5) * 0.45 + scratch * 0.5)
    ink = np.clip(ndi.gaussian_filter(ink, 0.5) * (1 - worn * 0.82), 0, 1)
    paint = mix(paint, rgb(186, 184, 172) * (0.84 + 0.22 * fine[..., None]), ink * 0.94)
    # A band of the paint run thin where it has been rolled on the hoops.
    paint = mix(paint, paint * 1.28 + rgb(16, 15, 13), knocks * smooth(0.35, 0.7, own_mid) * 0.34)

    colour = np.array(paint, np.float32)
    primer = rgb(64, 66, 62) * (0.8 + 0.4 * fine[..., None])
    colour = mix(colour, primer, to_primer)
    colour = mix(colour, rgb(146, 144, 138) * (0.72 + 0.4 * fine[..., None]), to_steel)
    rust = mix(rgb(56, 32, 20), rgb(112, 66, 36), smooth(0.3, 0.8, fine + (own_mid - 0.5) * 0.4))
    colour = mix(colour, rust, np.clip(rust_mask * 0.92, 0, 0.95))
    colour = mix(colour, colour * 0.34 + rgb(6, 5, 4), np.clip(spill * 0.85 + drip * 0.7, 0, 0.9))
    plated = mix(rgb(172, 170, 160), rgb(88, 86, 78), zinc_tarnish * 0.75)
    colour = np.where(zinc[..., None], plated, colour)
    colour = mix(colour, rgb(120, 110, 88) * (0.8 + 0.4 * fine[..., None]), dust * (0.76 + 0.48 * own))
    colour = mix(colour, rgb(56, 48, 38) * (0.75 + 0.45 * fine[..., None]), np.clip(grime * (0.74 + 0.5 * own), 0, 0.92))
    colour = colour * (0.66 + 0.34 * ao[..., None])
    return fill_from(cover, np.clip(colour, 0, 1))[0]


for name, (enamel, faded, words, seed) in DRUMS.items():
    save_rgb(os.path.join(OUT, f"{NAME}_{name}_color.png"), colour_map(enamel, faded, words, seed))
    print("painted", name, flush=True)

normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border
# takes its normal from just inside. Islands too thin to have an inside keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
rough, metal, normal = fill_from(cover, np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("oil drum painted", flush=True)
