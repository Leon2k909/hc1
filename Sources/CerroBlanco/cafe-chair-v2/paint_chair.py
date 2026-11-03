"""Paint the cafe chair's maps from its bakes: python paint_chair.py <work dir> <output dir>

A museum cafe's chair, a few years in use indoors and out. The teak is the forestbase wood_planks scan (CC0) at its true scale, laid along each slat from inside one of its planks so the grain runs
the slat's length, shifted to oiled teak: silvered a little where it faces up, rubbed pale at the arrises, darker at the end grain and round each screw. The frame is anthracite powder coat, kicked
to bare steel low on the legs and worn bright where feet rest on the stretchers and hands take the post tops. Black nylon glides, stainless screws with a cross. Values are kept strong. Worked out
in 3D from the baked position of each texel, and by part from the build's list.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

TEAK, POWDER, CAST, NYLON, STEEL = range(5)
facts_file = json.load(open(os.path.join(WORK, "chair.json")))
density, RANGE = facts_file["density"], facts_file["range"]
SEAT_TOP = facts_file["seat_top"]
SLAT_T = facts_file["slat"][0]
SLATS = facts_file["slats"]
SCREWS = facts_file["screws"]
NAME = "chair"
SCANS = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans")
SCAN_PX_PER_IN = 40.0  # Its planks come out about 5.7 in wide.
SLAT_HALF_PX = facts_file["slat"][3] * SCAN_PX_PER_IN + 30  # Half a seat slat's length, in the scan, and its bevel.
PLANKS = (397, 637, 863, 1072, 1301, 1530, 1739)  # The middle row of each whole plank in the scan, between its gaps.
# Where each plank's butt joints cross it, the tile's own wrap at 0 among them, so a slat can take a run of grain clear of them all.
JOINTS = {397: (0, 1293, 2048), 1072: (464, 2045)}

pos4 = load("bake_ch_pos")
nor4 = load("bake_ch_nor")
facts4 = load("bake_ch_facts")
ao4 = load("bake_ch_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
weight = facts4[..., 2]
pos, nor, finish, part, weight = fill_from(cover, pos, nor, finish, part, weight)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), (H / ao.shape[0], W / ao.shape[1]), order=1), 0, 1)
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

listed = json.load(open(os.path.join(WORK, "chair_parts.json")))
rands = np.array([r for r, _, _ in listed], np.float32)
order = np.argsort(rands)
names = np.array([n for _, n, _ in listed])[order]
at = np.clip(np.searchsorted(rands[order], part), 1, len(rands) - 1)
nearer = np.where(np.abs(rands[order][at - 1] - part) < np.abs(rands[order][at] - part), at - 1, at)
part_name = names[nearer]

TURN = np.array(((0.70, -0.42, 0.58), (0.61, 0.77, -0.19), (-0.37, 0.48, 0.79)), np.float32)


def noise(p, freq, seed=0, octaves=1):
    return lattice_noise(p @ TURN, freq, seed, octaves)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


def soft(mask, sigma=0.5):
    return ndi.gaussian_filter(mask.astype(np.float32), sigma)


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NX, NY, NZ = nor[..., 0], nor[..., 1], nor[..., 2]
teak = (finish == TEAK) & cover
powder = finish == POWDER
nylon = finish == NYLON
steel = finish == STEEL
upward = np.clip(NZ, 0, 1)
big = field(noise(pts, 0.12, 1, 3))
mid = field(noise(pts, 0.8, 2, 4))
fine = field(noise(pts, 4.0, 3, 3))
micro = field(noise(pts, 14.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)

# ---- The teak, from the scan: each slat takes its own plank and its own stretch of it. ----
def scan(name, mode="RGB"):
    return np.asarray(Image.open(os.path.join(SCANS, name)).convert(mode), np.float32) / 255.0


wood = srgb_to_linear(scan("wood_planks_diff.jpg") * 255.0)
wood_rough = scan("wood_planks_rough.jpg", "L")
wood_lum = wood.mean(-1)
# The scan's warm oak-brown, moved to oiled teak's golden brown, keeping its grain.
wood = wood / np.maximum(wood.reshape(-1, 3).mean(0), 1e-4) * srgb_to_linear((148, 103, 64))
grain_height = wood_lum - ndi.gaussian_filter(wood_lum, 6, mode="wrap")
r = np.random.default_rng(31)
along = np.zeros((H, W), np.float32)
across = np.zeros((H, W), np.float32)
depth = np.zeros((H, W), np.float32)
band = np.zeros((H, W), np.float32)
shift = np.zeros((H, W), np.float32)
facing = np.zeros((H, W), np.float32)  # 1 on the faces the grain shows on, 0 on edges.
end_grain = np.zeros((H, W), bool)
for k, (name, where) in enumerate(sorted(SLATS.items())):
    m = teak & (part_name == name)
    along[m] = Y[m]
    if name.startswith("seat"):
        across[m] = X[m] - where
        depth[m] = Z[m] - (SEAT_TOP - SLAT_T / 2)
        facing[m] = np.abs(NZ[m]) > 0.6
    else:
        across[m] = Z[m] - where[1]
        depth[m] = X[m] - where[0]
        facing[m] = np.abs(NX[m]) > 0.55
    plank = PLANKS[k % len(PLANKS)]
    band[m] = plank
    joints = sorted({j % 2048 for j in JOINTS.get(plank, (0,))})
    runs = [(a, b if b > a else b + 2048) for a, b in zip(joints, joints[1:] + [joints[0] + 2048])]
    start, end = max(runs, key=lambda ab: ab[1] - ab[0])
    reach = SLAT_HALF_PX + 24
    shift[m] = r.uniform(start + reach, end - reach)
    end_grain |= m & (np.abs(NY) > 0.6)
side_coord = np.where(facing > 0.5, across, depth + 1.3)  # The edges read a strip of the same plank just beside the face's.
rows = band - side_coord * SCAN_PX_PER_IN
cols = shift + along * SCAN_PX_PER_IN
coords = np.stack((rows[teak], np.mod(cols[teak], 2048)))
t_color = np.zeros((H, W, 3), np.float32)
for c in range(3):
    t_color[..., c][teak] = ndi.map_coordinates(wood[..., c], coords, order=1, mode="wrap")
t_rough_scan = np.zeros((H, W), np.float32)
t_rough_scan[teak] = ndi.map_coordinates(wood_rough, coords, order=1, mode="wrap")
t_grain = np.zeros((H, W), np.float32)
t_grain[teak] = ndi.map_coordinates(grain_height, coords, order=1, mode="wrap")
# End grain: darker, in rings.
rings = 0.5 + 0.5 * np.sin((np.hypot(across + 3.0, depth + 5.0)) * 2 * np.pi / 0.09 + fine * 3)
end_c = rgb(92, 60, 36) * (0.8 + 0.25 * rings[..., None])
t_color = np.where(end_grain[..., None], end_c, t_color)
# Faces up and out silver a little, the arrises rub pale, and the wood darkens round each screw.
heads = np.array([s[0] for s in SCREWS], np.float32)
d_screw, _ = cKDTree(heads).query(pts, k=1, distance_upper_bound=1.0, workers=4)
d_screw = field(np.where(np.isfinite(d_screw), d_screw, 1.0).astype(np.float32))
round_screw = smooth(0.42, 0.16, d_screw) * teak
exposed = teak & (facing > 0.5) & ((NZ > 0.6) | (NX > 0.55))
silver = exposed * (0.22 + 0.18 * smooth(0.3, 0.7, big))
grey = (t_color.mean(-1, keepdims=True) * np.array((1.02, 1.0, 0.96), np.float32)) * 1.18
t_color = mix(t_color, grey, silver)
edge_rub = teak & ~end_grain & (facing < 0.5)
t_color = mix(t_color, t_color * 1.25 + rgb(14, 10, 6), edge_rub * smooth(0.3, 0.7, fine) * 0.3)
t_color = mix(t_color, t_color * 0.6, round_screw * 0.55)
spills = smooth(0.8, 0.88, field(noise(pts, 1.1, 9, 2))) * teak * (NZ > 0.6)
t_color = mix(t_color, t_color * 0.72, spills * 0.5)
t_rough = 0.5 + 0.32 * t_rough_scan + silver * 0.12 + end_grain * 0.12 - spills * 0.08
t_height = 0.006 * t_grain - 0.003 * end_grain * (rings - 0.5) + 0.0005 * (micro - 0.5)

# ---- Anthracite powder coat on steel tube. ----
edge_points = np.load(os.path.join(WORK, "chair_edges.npy"))
if len(edge_points):
    d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=0.3, workers=4)
    edge_d = field(np.where(np.isfinite(d), d, 0.3).astype(np.float32))
else:
    edge_d = np.full((H, W), 0.3, np.float32)
edge = smooth(0.08, 0.01, edge_d)
print("edges", flush=True)
peel = field(noise(pts, 6.0, 44, 2))
legs = np.isin(part_name, ("leg", "weld", "cap"))
low = smooth(4.5, 0.6, Z)
kicks = soft(smooth(0.55, 0.72, (field(noise(pts, 2.4, 50, 3)) * 0.8 + mid * 0.3) * low + edge * 0.35 * smooth(0.5, 0.8, mid)), 0.4) * powder
stretcher_top = np.isin(part_name, ("stretcher",)) & (NZ > 0.35)
feet_rest = stretcher_top * smooth(0.35, 0.65, field(noise(pts * np.array((0.4, 1.0, 1.0), np.float32), 1.4, 51, 3)))
hands = legs * smooth(29.5, 32.0, Z)
p_color = rgb(50, 52, 56) * (0.94 + 0.08 * big[..., None] + 0.04 * fine[..., None])
bare = rgb(122, 124, 126) * (0.8 + 0.3 * fine[..., None])
p_color = mix(p_color, mix(bare, rgb(96, 58, 34), smooth(0.6, 0.85, micro)[..., None] * 0.4), np.clip(kicks + feet_rest * 0.8, 0, 1))
p_color = mix(p_color, rgb(62, 64, 68), hands * 0.5)
p_rough = 0.46 + 0.05 * mid + 0.03 * fine - hands * 0.14 - feet_rest * 0.12 - kicks * 0.08
p_metal = np.clip(kicks + feet_rest * 0.8, 0, 1) * 0.85
p_height = 0.0011 * (peel - 0.5) - kicks * 0.002

# ---- Glides and screws. ----
n_color = rgb(20, 20, 21) * (0.85 + 0.3 * fine[..., None])
n_scuff = smooth(0.25, -0.05, Z) * nylon
n_color = mix(n_color, rgb(58, 58, 56), n_scuff * 0.6)
s_color = rgb(158, 158, 154) * (0.86 + 0.2 * fine[..., None])
# A cross in each head.
cross = np.zeros((H, W), np.float32)
tree = cKDTree(heads)
_, which = tree.query(pts, k=1, workers=4)
which = field(which.astype(np.float32)).astype(np.int64)
centre = heads[which]
axis = np.array([s[1] for s in SCREWS], np.float32)[which]
rel = pos - centre
u_dir = np.where(np.abs(axis[..., 2:3]) > 0.5, np.array((1.0, 0.0, 0.0), np.float32), np.array((0.0, 1.0, 0.0), np.float32))
v_dir = np.cross(axis, u_dir)
cu, cv = (rel * u_dir).sum(-1), (rel * v_dir).sum(-1)
cross = (smooth(0.022, 0.012, np.minimum(np.abs(cu), np.abs(cv))) * smooth(0.1, 0.08, np.hypot(cu, cv))) * steel
s_color = mix(s_color, rgb(26, 26, 26), cross * 0.9)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = 0.0005 * (micro - 0.5)
for mask, c, ro, me, he in (
    (teak, t_color, t_rough, None, t_height),
    (powder, p_color, p_rough, p_metal, p_height),
    (nylon, n_color, 0.55 - n_scuff * 0.1, None, 0.0008 * (fine - 0.5)),
    (steel, s_color, 0.3 + 0.1 * fine + cross * 0.4, np.ones((H, W), np.float32) * 0.95 * (1 - cross), -cross * 0.01),
):
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, ro, rough)
    if me is not None:
        metal = np.where(mask, me, metal)
    if he is not None:
        height = np.where(mask, he, height)

# Dust in the frame's corners and on what faces up, light: it's wiped.
gathered = smooth(0.3, 0.75, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4)
color = mix(color, rgb(106, 98, 84), gathered * 0.3 + upward * powder * smooth(0.5, 0.8, mid) * 0.15)
color = color * (0.66 + 0.34 * ao)[..., None]

height = fill_from(cover, height)[0]
filtered = ndi.gaussian_filter(height, 0.45)
px = np.maximum(density * weight, 1.0)
dv, du = np.gradient(filtered)
normal = np.stack((-du * px, -dv * px, np.ones_like(filtered)), -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("chair painted", flush=True)
