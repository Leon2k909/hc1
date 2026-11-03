"""Paint the eye wash's maps from its bakes and the project's real scans: python paint_eyewash.py <work dir> <output dir>

The surface comes from photo scans at their true scale, with procedural work only saying where things go. `forestbase/scans/container_side` (CC0) gives the enamel's own mottle, and
`metal_plate_02` (CC0) gives the shapes of its wear, its scratches and its dulled patches. Deep safety-green enamel, chipped on the edges where the scan says, a spun stainless bowl with water marks,
brass that's been handled, chrome, and yellow rubber dust caps. It's a plant's safety fitting: inspected, knocked and cleaned, not derelict. Keep the darks dark and the colours strong.
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

from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

COAT, ZINC, BRASS, BOWL, CAP = 2, 3, 4, 13, 14
facts = json.load(open(os.path.join(WORK, "eyewash.json")))
density, RANGE, BOWL_Y, VALVE_Z, RISER_X = (facts[k] for k in ("density", "range", "bowl_y", "valve_z", "riser_x"))
NAME = "eyewash"
SCANS = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans")
SCAN_PX_PER_IN = 34.0  # metal_plate_02's plates then come out about 10 in wide, and its scratches at a true size for a fitting this small.

pos4 = load("bake_ew_pos")
nor4 = load("bake_ew_nor")
facts4 = load("bake_ew_facts")
ao4 = load("bake_ew_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
# The AO bake's alpha is 1 everywhere, so its value is what says which texels it covered.
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
pts = pos[cover]
nrm = nor[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), "px/in", density, flush=True)

TURN = np.array(((0.70, -0.42, 0.58), (0.61, 0.77, -0.19), (-0.37, 0.48, 0.79)), np.float32)


def noise(p, freq, seed=0, octaves=1):
    return lattice_noise(p @ TURN, freq, seed, octaves)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


def scan(name):
    return np.asarray(Image.open(os.path.join(SCANS, name)).convert("L"), np.float32) / 255.0


# The scans, as maps with the sheets' seams and broad tone taken out.
def no_seams(a):
    """metal_plate_02's plates meet in straight lines that would draw straight lines across a pipe: take out what a whole row or column has in common."""
    for axis in (0, 1):
        line = a.mean(axis=axis)
        keep = line - ndi.gaussian_filter1d(line, 40, mode="wrap")
        a = a - (np.expand_dims(keep, axis) * 1.6)
    return np.clip(a, 0, 1)


plate_metal = no_seams(1.0 - scan("metal_plate_02_metal.jpg"))
plate_rough = scan("metal_plate_02_rough.jpg")
wear_map = np.clip(plate_metal * 1.6, 0, 1)
scratch_map = np.clip((plate_rough - ndi.gaussian_filter(plate_rough, 10, mode="wrap")) * 5.0, -1, 1)
scratch_map = no_seams(scratch_map * 0.5 + 0.5)
dull_map = no_seams(ndi.gaussian_filter(plate_rough, 3, mode="wrap"))
green = scan("container_side_diff.jpg")
green = green - green.mean(axis=0, keepdims=True) + green.mean()  # The corrugations run up its columns.
mottle_map = green / np.maximum(ndi.gaussian_filter(green, 48, mode="wrap"), 1e-3)
mottle_map = np.clip(1.0 + (mottle_map - 1.0) * 2.4, 0.6, 1.4)
print("scan ranges: wear", wear_map.mean(), "mottle sd", mottle_map.std(), flush=True)


def triplanar(image, seed):
    """A scan laid over the model at its true scale from the three axes, blended by which way each texel looks, and moved along for each part so no two pieces show the same patch."""
    h, w = image.shape
    shift = (part[cover] * 1000.0 + seed * 97.0)[:, None]
    p = pts * SCAN_PX_PER_IN + shift
    weights = np.abs(nrm) ** 6
    weights = weights / np.maximum(weights.sum(1, keepdims=True), 1e-6)
    out = np.zeros(len(p), np.float32)
    for axis, (a, b) in enumerate(((1, 2), (0, 2), (0, 1))):
        coords = np.stack((p[:, a] % h, p[:, b] % w))
        out += weights[:, axis] * ndi.map_coordinates(image, coords, order=1, mode="wrap")
    return field(out)


wear = triplanar(wear_map, 1)
scratches = triplanar(scratch_map, 2)
dull = triplanar(dull_map, 3)
mottle = triplanar(mottle_map, 4)
mottle = np.where(cover, mottle, 1.0)

X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
coat = finish == COAT
zinc = finish == ZINC
brass = finish == BRASS
bowl = finish == BOWL
cap = finish == CAP
radius = np.hypot(X, Y - BOWL_Y)
# The bowl's one turning: inside looks up and stays bare stainless, with the rim, and the outside looks down and is painted.
inside = bowl & (nor[..., 2] > 0.1) & (radius < 5.95)
paint = coat | (bowl & ~inside)

edge_points = np.load(os.path.join(WORK, "eyewash_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=0.6, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 0.6).astype(np.float32))
edge = smooth(0.14, 0.02, edge_d)

mid = field(noise(pts, 0.5, 2, 4))
fine = field(noise(pts, 2.6, 3, 3))
crevice = np.clip((1 - ao) * 1.5, 0, 1)
# Knocks come where a thing sticks out and where a boot or a trolley reaches: the rim, the paddle's corners, the riser's lower part.
exposed = edge * (0.35 + 0.65 * smooth(0.3, 0.7, mid)) + smooth(16.0, 7.0, Z) * coat * 0.16 + (bowl & ~inside) * smooth(35.5, 37.0, Z) * 0.2
chip = ndi.gaussian_filter(smooth(0.46, 0.6, wear * (0.42 + exposed * 1.5)), 0.45) * paint
chip_deep = ndi.gaussian_filter(smooth(0.68, 0.8, wear * (0.42 + exposed * 1.5)), 0.4) * paint
scratch = smooth(0.6, 0.78, scratches) * paint

# Deep safety-green enamel, with the real scan's mottle in it. Chips show grey primer, and at their middles bare steel with a little rust.
# The mottle stays faint: any stronger and in the engine it reads as moss on the pipe, not enamel. Gloss is what makes enamel read.
g_color = rgb(22, 104, 60) * (1.0 + (mottle[..., None] - 1.0) * 0.4) * (0.97 + 0.06 * mid[..., None])
g_color = mix(g_color, rgb(44, 136, 88), scratch[..., None] * 0.45)
g_color = mix(g_color, rgb(120, 122, 118) * (0.8 + 0.3 * fine[..., None]), chip)
g_color = mix(g_color, mix(rgb(74, 74, 76), rgb(92, 52, 30), smooth(0.4, 0.7, mid))[...] * (0.8 + 0.3 * fine[..., None]), chip_deep)
g_rough = 0.17 + 0.13 * dull + 0.1 * scratch + chip * 0.36
g_metal = 0.02 + chip_deep * 0.6

# Stainless, spun round the bowl's middle, with water marks: a pale ring by the strainer and dull spots where the scan has them.
wobble = field(noise(pts, 0.8, 11, 2)) * 0.12
rng = np.random.default_rng(41)
rings = rng.random(4096).astype(np.float32)
rings = ndi.gaussian_filter1d(rings, 1.0, mode="wrap")
rings = (rings - rings.min()) / (rings.max() - rings.min())
spin = np.interp((radius + wobble) * 34.0 % 4096, np.arange(4096), rings)
scale_ring = smooth(2.4, 1.2, radius) * smooth(0.25, 0.65, mid * 0.5 + wear * 0.8)
s_color = rgb(176, 178, 178) * (0.82 + 0.3 * spin[..., None])
s_color = mix(s_color, rgb(206, 202, 186), np.clip(scale_ring * 0.5 + smooth(0.45, 0.75, wear) * 0.25, 0, 0.7)[..., None])
s_rough = 0.2 + 0.1 * spin + 0.22 * dull + scale_ring * 0.3
s_metal = 0.78 - scale_ring * 0.5

# Chrome on the fittings, a little pitted where the scan says.
pits = smooth(0.58, 0.78, wear)
z_color = mix(rgb(226, 228, 230), rgb(120, 118, 112), pits[..., None] * 0.5)
z_rough = 0.08 + 0.1 * dull + pits * 0.18
z_metal = 0.86 - pits * 0.25  # The old fittings' full metal draws black in this hall, and 0.78 at more roughness read as grey plastic.

# Brass, gone dull and brown in the hollows, bright where hands go.
handled = smooth(0.3, 0.7, mid * 0.6 + (1 - crevice) * 0.5)
b_color = mix(rgb(112, 84, 42), rgb(196, 156, 84), handled[..., None]) * (0.86 + 0.26 * fine[..., None])
b_color = mix(b_color, rgb(58, 62, 44), (smooth(0.52, 0.72, wear) * (1 - handled) * 0.7)[..., None])
b_rough = 0.24 + 0.26 * dull + (1 - handled) * 0.14
b_metal = 0.72 - smooth(0.52, 0.72, wear) * (1 - handled) * 0.4

# Yellow rubber, sun-free but scuffed.
c_color = rgb(226, 178, 22) * (0.86 + 0.2 * fine[..., None])
c_color = mix(c_color, rgb(112, 92, 44), smooth(0.48, 0.72, wear)[..., None] * 0.5)
c_rough = 0.5 + 0.2 * dull

# Screws: dark slots in zinc heads.
screw_points = np.load(os.path.join(WORK, "eyewash_screws.npy"))
dist, _ = cKDTree(screw_points).query(pts, k=1, distance_upper_bound=0.4, workers=4)
screw_d = field(np.where(np.isfinite(dist), dist, 1.0).astype(np.float32))
screw = smooth(0.1, 0.06, screw_d)
screw_rim = smooth(0.2, 0.14, screw_d) * (1 - screw)

# The strainer's holes.
strainer = zinc & (radius < 1.0) & (Z > 35.05) & (nor[..., 2] > 0.5)
holes = strainer * smooth(0.12, 0.07, np.hypot(((X + 0.15) % 0.3) - 0.15, ((Y - BOWL_Y + 0.15) % 0.3) - 0.15)) * smooth(0.9, 0.8, radius)

# The paddle's lettering, printed white on its front, read from in front: +X is on the left.
paddle = coat & (nor[..., 1] > 0.7) & (X > RISER_X + 1.6) & (Z > VALVE_Z - 3.2) & (Z < VALVE_Z + 2.2) & (Y > 6.3)
words = stencil_image(["PUSH"], (800, 300), bridge=False)
lettering = sample_image(words, (RISER_X + 4.7 - X) / 2.8, (Z - (VALVE_Z - 0.9)) / 1.05)
ring_x = RISER_X + 3.3
arrow = smooth(0.09, 0.05, np.abs(np.abs(X - ring_x) + (Z - (VALVE_Z - 2.05)) - 0.55)) * smooth(0.65, 0.55, np.abs(X - ring_x))
lettering = ndi.gaussian_filter((np.maximum(lettering, arrow) * paddle).astype(np.float32), 0.4)
worn_print = lettering * (1 - smooth(0.42, 0.62, wear) * 0.8)

color = np.zeros((H, W, 3), np.float32)
color = np.where(paint[..., None], g_color, color)
color = np.where(inside[..., None], s_color, color)
color = np.where(zinc[..., None], z_color, color)
color = np.where(brass[..., None], b_color, color)
color = np.where(cap[..., None], c_color, color)
color = mix(color, rgb(226, 230, 222), worn_print[..., None] * 0.92)
color = mix(color, rgb(10, 10, 12), holes[..., None])
color = mix(color, rgb(150, 150, 148), (screw_rim * paint)[..., None] * 0.8)
color = mix(color, rgb(26, 26, 28), (screw * paint)[..., None])
rough = np.where(paint, g_rough, np.where(inside, s_rough, np.where(zinc, z_rough, np.where(brass, b_rough, np.where(cap, c_rough, 0.5)))))
rough = rough + worn_print * 0.2
metal = np.where(paint, g_metal, np.where(inside, s_metal, np.where(zinc, z_metal, np.where(brass, b_metal, 0.0))))
metal = metal * (1 - holes) * (1 - worn_print * paint)
height = np.where(paint, -chip * 0.006 - chip_deep * 0.006 + 0.0012 * (mottle - 1.0) * 6.0 - scratch * 0.0025 - screw * 0.02, 0.0)
height = np.where(inside, 0.0009 * (spin - 0.5), height)
height = np.where(zinc, 0.0012 * (dull - 0.5) - holes * 0.03, height)
height = np.where(brass, 0.0016 * (dull - 0.5), height)

# A wiped fitting, but the corners hold dust.
gathered = smooth(0.2, 0.7, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4)
grime = np.clip(gathered * 0.5, 0, 0.7)
color = mix(color, rgb(40, 38, 32) * (0.8 + 0.4 * fine[..., None]), grime[..., None])
rough = rough * (1 - grime * 0.6) + 0.8 * grime * 0.6
metal = metal * (1 - grime)
color = color * (0.55 + 0.45 * ao[..., None])
print("chip cover on paint", float(chip[paint & cover].mean()), "deep", float(chip_deep[paint & cover].mean()), flush=True)

normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border
# takes its normal from just inside. Islands too thin to have an inside keep what they have.
inside_cover = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside_cover, iterations=3) & cover
normal = fill_from(inside_cover | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("eye wash painted", flush=True)
