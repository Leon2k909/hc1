"""Paint the cafe table's maps from its bakes: python paint_table.py <work dir> <output dir>

A museum cafe's table after a few years of service. The top is white compact laminate: matte, with the faint rings of cups and glasses that wiping never quite lifts, fine scratches from plates and
cutlery, a little grey where forearms rest at the rim, and its black core showing at the edge, satin and sanded, knocked pale in a few places. The underside is bare and a little dusty. The spider,
column and base are anthracite powder coat, the base kicked to bare steel at its rim and the column scuffed low down by shoes. Black nylon glides, zinc screws with a cross. Values are kept strong.
Worked out in 3D from the baked position of each texel, and by part from the build's list.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

LAMINATE, POWDER, CAST, NYLON, STEEL = range(5)
facts_file = json.load(open(os.path.join(WORK, "table.json")))
density, RANGE = facts_file["density"], facts_file["range"]
TOP_Z, TOP_T, TOP_R, EASE = facts_file["top"]
SCREWS = facts_file["screws"]
NAME = "table"

pos4 = load("bake_tb_pos")
nor4 = load("bake_tb_nor")
facts4 = load("bake_tb_facts")
ao4 = load("bake_tb_ao")
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

listed = json.load(open(os.path.join(WORK, "table_parts.json")))
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
NZ = nor[..., 2]
RHO = np.hypot(X, Y)
laminate = (finish == LAMINATE) & cover
powder = finish == POWDER
nylon = finish == NYLON
steel = finish == STEEL
upward = np.clip(NZ, 0, 1)
big = field(noise(pts, 0.1, 1, 3))
mid = field(noise(pts, 0.7, 2, 4))
fine = field(noise(pts, 4.0, 3, 3))
micro = field(noise(pts, 16.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
r = np.random.default_rng(41)

# ---- The top. ----
# By height, not by the baked normal: that one is smoothed across the arris and cuts it a little differently on every facet, which drew as notches along the edge.
face = laminate & (Z > TOP_Z - 0.004)
under = laminate & (Z < TOP_Z - TOP_T + 0.004)
edge_band = laminate & ~face & ~under
# The eased arrises cut through the decor layer, so the whole band from face to face is black core. (A painted white hairline at the arris was finer than a texel and drew as a sawtooth.)
core = edge_band
white = rgb(234, 232, 225) * (0.985 + 0.03 * big[..., None] + 0.012 * fine[..., None])
# Rings from cups and glasses: thin, faint, most of them broken where a cloth went over them.
rings = np.zeros((H, W), np.float32)
for _ in range(9):
    a, d = r.uniform(0, 2 * math.pi), r.uniform(2.0, 10.5)
    cx, cy, rad = d * math.cos(a), d * math.sin(a), r.uniform(1.15, 1.6)
    ring = smooth(0.06, 0.0, np.abs(np.hypot(X - cx, Y - cy) - rad))
    broken = smooth(0.35, 0.6, field(noise(pts, 1.6, int(r.integers(100, 999)), 2)))
    rings = np.maximum(rings, ring * broken * r.uniform(0.4, 1.0))
rings = rings * face
scratches = np.zeros((H, W), np.float32)
for _ in range(70):
    cx, cy = r.uniform(-12, 12), r.uniform(-12, 12)
    if math.hypot(cx, cy) > 13.2:
        continue
    turn, length = r.uniform(0, math.pi), r.uniform(0.3, 2.2)
    dx, dy = math.cos(turn), math.sin(turn)
    along = (X - cx) * dx + (Y - cy) * dy
    across = np.abs(-(X - cx) * dy + (Y - cy) * dx)
    scratches = np.maximum(scratches, smooth(0.018, 0.004, across) * smooth(length / 2, length / 2 - 0.15, np.abs(along)) * r.uniform(0.4, 1.0))
scratches = scratches * face
elbows = smooth(8.0, 12.5, RHO) * smooth(0.35, 0.7, mid) * face
l_color = mix(white, white * np.array((0.86, 0.84, 0.8), np.float32), elbows * 0.4)
l_color = mix(l_color, rgb(170, 152, 126), rings * 0.45)
l_color = mix(l_color, rgb(212, 212, 208), scratches * 0.5)
# The underside is bare board, dusty, a little yellowed.
l_color = np.where(under[..., None], mix(rgb(226, 222, 212), rgb(160, 152, 136), smooth(0.4, 0.8, mid) * 0.35), l_color)
# The black core: satin, sanded round, knocked pale in places.
sanding = 0.5 + 0.5 * np.sin(Z * 2 * math.pi / 0.03 + fine * 2)
knocks = soft(smooth(0.62, 0.78, field(noise(pts, 1.8, 61, 3)) * 0.8 + fine * 0.3), 0.4) * core
core_c = rgb(22, 22, 23) * (0.9 + 0.12 * sanding[..., None])
core_c = mix(core_c, rgb(78, 76, 72), knocks * 0.6)
l_color = np.where(core[..., None], core_c, l_color)
l_rough = np.where(face, 0.52 + 0.04 * fine - rings * 0.06 + scratches * 0.12 - elbows * 0.1, 0.62)
l_rough = np.where(core, 0.42 + 0.06 * sanding + knocks * 0.2, l_rough)
l_height = np.where(face, 0.0006 * (micro - 0.5) + 0.0003 * (fine - 0.5) - scratches * 0.0015, 0.0004 * (micro - 0.5))
l_height = np.where(core, 0.0008 * (sanding - 0.5) - knocks * 0.003, l_height)

# ---- Anthracite powder coat. ----
edge_points = np.load(os.path.join(WORK, "table_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=0.3, workers=4)
edge = smooth(0.08, 0.01, field(np.where(np.isfinite(d), d, 0.3).astype(np.float32)))
print("edges", flush=True)
peel = field(noise(pts, 6.0, 44, 2))
base = np.isin(part_name, ("base",))
column = np.isin(part_name, ("column", "collar"))
kicks = soft(smooth(0.55, 0.7, (edge * 1.2 + smooth(1.3, 0.6, Z) * 0.25) * smooth(0.4, 0.75, mid) + (fine - 0.5) * 0.12), 0.4) * base
shoe = column * smooth(2.5, 4.0, Z) * smooth(14.0, 9.0, Z) * smooth(0.6, 0.85, field(lattice_noise(np.column_stack((X[cover] * 2.0, Y[cover] * 2.0, Z[cover] * 0.25)).astype(np.float32), 1.0, 52, 3)))
grit = base * upward * smooth(0.35, 0.75, mid) * 0.5 + base * smooth(3.4, 2.4, RHO) * (Z < 2.0) * 0.4
p_color = rgb(50, 52, 56) * (0.94 + 0.08 * big[..., None] + 0.04 * fine[..., None])
p_color = mix(p_color, mix(rgb(118, 120, 122), rgb(96, 58, 34), smooth(0.6, 0.85, micro)[..., None] * 0.45), kicks)
p_color = mix(p_color, rgb(78, 78, 76), shoe * 0.55)
p_color = mix(p_color, rgb(112, 104, 88) * (0.8 + 0.4 * fine[..., None]), np.clip(grit, 0, 0.6))
p_rough = 0.46 + 0.05 * mid + 0.03 * fine - kicks * 0.1 + shoe * 0.12 + grit * 0.2
p_metal = kicks * 0.8
p_height = 0.0011 * (peel - 0.5) - kicks * 0.002

# ---- Glides and screws. ----
n_color = rgb(20, 20, 21) * (0.85 + 0.3 * fine[..., None])
heads = np.array([s[0] for s in SCREWS], np.float32)
_, which = cKDTree(heads).query(pts, k=1, workers=4)
which = field(which.astype(np.float32)).astype(np.int64)
rel = pos - heads[which]
cross = (smooth(0.026, 0.014, np.minimum(np.abs(rel[..., 0] + rel[..., 1]), np.abs(rel[..., 0] - rel[..., 1])) / math.sqrt(2)) * smooth(0.12, 0.1, np.hypot(rel[..., 0], rel[..., 1]))) * steel
s_color = mix(rgb(150, 150, 144) * (0.85 + 0.2 * fine[..., None]), rgb(26, 26, 26), cross * 0.9)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = 0.0004 * (micro - 0.5)
for mask, c, ro, me, he in (
    (laminate, l_color, l_rough, None, l_height),
    (powder, p_color, p_rough, p_metal, p_height),
    (nylon, n_color, 0.55, None, 0.0008 * (fine - 0.5)),
    (steel, s_color, 0.34 + 0.1 * fine + cross * 0.4, np.ones((H, W), np.float32) * 0.9 * (1 - cross), -cross * 0.01),
):
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, ro, rough)
    if me is not None:
        metal = np.where(mask, me, metal)
    if he is not None:
        height = np.where(mask, he, height)

gathered = smooth(0.3, 0.75, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4) * ~face
color = mix(color, rgb(106, 98, 84), gathered * 0.3)
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
print("table painted", flush=True)
