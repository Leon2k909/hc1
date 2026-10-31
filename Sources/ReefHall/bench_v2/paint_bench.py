"""Paint the bench's maps from its bakes: python paint_bench.py <work dir> <output dir>

An aquarium's bench, looked after but used: oiled hardwood slats, a little different from each other, dulled and paler where people sit
and rubbed along the front edge by legs. Powder-coated steel, kicked bare low down. A brass plaque polished by hands, and made-up
lettering on it. It's indoors and mopped, so there's little dirt and no weathering. Wear is worked out in 3D.
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

OXIDE, ZINC, BRASS, OAK = 2, 3, 4, 11
facts = json.load(open(os.path.join(WORK, "bench.json")))
density, RANGE, HL, HD, TOP = (facts[k] for k in ("density", "range", "half_length", "half_depth", "top"))
NAME = "bench"

pos4 = load("bake_bn_pos")
nor4 = load("bake_bn_nor")
facts4 = load("bake_bn_facts")
ao4 = load("bake_bn_ao")
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
oak = finish == OAK
steel = finish == OXIDE
zinc = finish == ZINC
brass = finish == BRASS

edge_points = np.load(os.path.join(WORK, "bench_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=1.0, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 1.0).astype(np.float32))
edge = smooth(0.2, 0.02, edge_d)

big = field(noise(pts, 0.06, 1, 3))
mid = field(noise(pts, 0.4, 2, 4))
fine = field(noise(pts, 2.2, 3, 3))
micro = field(noise(pts, 7.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)

# Grain along each slat, each from its own place in the tree, with lines at least four texels apart.
offset = pts + part[cover][:, None] * 37.0
grain = field(lattice_noise(offset * np.array((0.08, 1.2, 1.2), np.float32), 1.0, 31, 4))
lines = 0.5 + 0.5 * np.sin(grain * 26.0)
figure = field(lattice_noise(offset * np.array((0.03, 0.34, 0.34), np.float32), 1.0, 32, 4))

# Where people sit: two places, wider than a person, and the slat edges at the front where the backs of their legs rub.
seats = np.maximum(smooth(16.0, 4.0, np.abs(X + 23.0)), smooth(16.0, 4.0, np.abs(X - 21.0)))
sat = oak * upward * seats * smooth(9.0, 3.0, np.abs(Y - 0.6)) * smooth(0.25, 0.7, big * 0.6 + mid * 0.4)
legs = oak * seats * smooth(6.4, 8.6, Y) * smooth(0.25, 0.65, mid)

# Long light scratches on the seat, from bags and keys, walked along its top.
r = np.random.default_rng(18)
lines3, widths = [], []
for _ in range(120):
    x0, y0 = r.uniform(-46.0, 46.0), r.uniform(-8.6, 8.6)
    length = float(r.uniform(1.0, 7.0))
    w = float(r.uniform(0.045, 0.09))
    turn = r.normal(0.0, 0.5)
    steps = max(4, int(length / 0.04))
    for k in range(steps):
        f = k / (steps - 1)
        lines3.append((x0 + math.cos(turn) * (f - 0.5) * length, y0 + math.sin(turn) * (f - 0.5) * length, TOP - 0.01))
        widths.append(w * (1 - abs(f - 0.5) * 1.3))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines3, np.float32)).query(pts, k=1, distance_upper_bound=0.14, workers=4)
which = np.minimum(which, len(widths) - 1)
scratch = ndi.gaussian_filter(field(smooth(1.0, 0.4, np.where(np.isfinite(dist), dist, 1.0) / widths[which]).astype(np.float32)), 0.6) * oak * upward

# Someone's cup, once.
ring_d = np.hypot(X - 31.0, Y + 3.6)
ring = oak * upward * smooth(0.13, 0.04, np.abs(ring_d - 1.55 + (fine - 0.5) * 0.1)) * smooth(0.25, 0.6, field(noise(pts, 1.0, 26, 2)))

screws = np.load(os.path.join(WORK, "bench_screws.npy"))
dist, _ = cKDTree(screws).query(pts, k=1, distance_upper_bound=0.5, workers=4)
screw = field(smooth(0.17, 0.11, np.where(np.isfinite(dist), dist, 1.0)).astype(np.float32)) * oak * upward
plug = field(smooth(0.31, 0.2, np.where(np.isfinite(dist), dist, 1.0)).astype(np.float32)) * oak * upward

tone = (0.8 + 0.42 * part) * (0.9 + 0.2 * mid)
timber = mix(rgb(156, 104, 62), rgb(82, 50, 28), np.clip(lines * 0.42 + (figure - 0.5) * 1.5 + 0.22, 0, 1)) * tone[..., None]
timber = mix(timber, timber * 1.22 + rgb(16, 12, 8), np.clip(sat * 0.6 + legs * 0.7, 0, 1))
# Worn edges: long uneven runs and soft. Gated by fine noise and a hard threshold they read in the engine as pale dashes along every slat, like lane markings.
timber = mix(timber, rgb(170, 128, 86) * (0.9 + 0.16 * fine[..., None]), np.clip(ndi.gaussian_filter(edge * smooth(0.34, 0.74, big * 0.5 + mid * 0.5), 1.2) * 0.42 + scratch * 0.2, 0, 0.9))
timber = mix(timber, timber * 0.56, ring * 0.7)
timber = mix(timber, timber * 0.7, plug * 0.4)
timber = mix(timber, rgb(40, 38, 36), screw)
t_rough = 0.3 + 0.1 * mid + 0.05 * lines + sat * 0.26 + legs * 0.18 + scratch * 0.18 + ring * 0.2 + edge * 0.1

# Powder-coated steel: chipped at the edges, kicked bare low down on the front and back.
kicks = steel * smooth(5.0, 0.8, Z) * smooth(5.5, 7.8, np.abs(Y)) * smooth(0.36, 0.72, mid * 0.5 + fine * 0.5)
s_chip = ndi.gaussian_filter(smooth(0.58, 0.68, edge * (0.2 + 0.6 * smooth(0.3, 0.7, fine)) + (fine - 0.5) * 0.3 + kicks * 0.62), 0.5) * steel
s_color = rgb(72, 75, 82) * (0.84 + 0.32 * mid[..., None])
s_color = mix(s_color, rgb(136, 136, 132) * (0.74 + 0.4 * fine[..., None]), s_chip)
s_rough = 0.4 + 0.1 * mid + 0.06 * fine - s_chip * 0.08
s_metal = 0.1 + s_chip * 0.85

# The plaque: brass, dull in its corners, bright across its middle. Read from the bench's front, so +X is on the left.
plate_text = stencil_image(["FRIENDS OF REEF HALL"], (1000, 180), bridge=False)
letters = np.where(brass & (nor[..., 2] > 0.7), sample_image(plate_text, (3.0 - X) / 6.0, (0.62 - Y) / 1.24), 0)
letters = ndi.gaussian_filter(letters, 0.4)
rubbed = smooth(0.0, 2.6, 3.2 - np.abs(X)) * smooth(0.25, 0.75, mid)
b_color = mix(rgb(96, 78, 48), rgb(186, 154, 92), rubbed)
b_color = mix(b_color, rgb(22, 20, 16), letters * 0.95)
b_rough = 0.46 - rubbed * 0.2 + 0.08 * fine + letters * 0.3
b_metal = np.clip(1.0 - letters * 0.9, 0, 1)

color = np.zeros((H, W, 3), np.float32)
color = np.where(oak[..., None], timber, color)
color = np.where(steel[..., None], s_color, color)
color = np.where(zinc[..., None], rgb(150, 148, 140) * (0.74 + 0.36 * mid[..., None]), color)
color = np.where(brass[..., None], b_color, color)
rough = np.where(oak, t_rough, np.where(steel, s_rough, np.where(zinc, 0.38 + 0.2 * mid, np.where(brass, b_rough, 0.6))))
metal = np.where(oak, screw * 0.8, np.where(steel, s_metal, np.where(zinc, 0.95, np.where(brass, b_metal, 0.0))))
height = np.where(oak, 0.012 * (lines - 0.5) + 0.018 * (figure - 0.5) * 2.0 - scratch * 0.004 - plug * 0.005 - screw * 0.02, 0.0015 * (micro - 0.5) + 0.0012 * (fine - 0.5))
height = np.where(brass, -letters * 0.006, height)
height = np.where(steel, height + (1 - s_chip) * 0.003, height)

# It's mopped: a little dust in the corners, grime on the floor rails, and that's all.
gathered = smooth(0.15, 0.6, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4)
low = smooth(3.5, 0.2, Z)
grime = np.clip(gathered * 0.4 + low * smooth(0.3, 0.7, fine) * 0.4, 0, 0.7)
color = mix(color, rgb(62, 56, 48) * (0.8 + 0.4 * fine[..., None]), grime)
rough = rough * (1 - grime * 0.6) + 0.8 * grime * 0.6
metal = metal * (1 - grime)
color = color * (0.68 + 0.32 * ao[..., None])

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
print("bench painted", flush=True)
