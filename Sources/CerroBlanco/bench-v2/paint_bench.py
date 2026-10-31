"""Paint the bench's maps from its bakes: python paint_bench.py <work dir> <output dir>

Honed travertine, cream with darker bedding running along the block and open pores filled over the years, jointed in two; teak slats
gone silver where the weather reaches and darker where people sit; brushed stainless rails and screws. Scuffed low by shoes and dirty
at the floor. All worked out from each texel's 3D position, so it crosses UV seams. No lettering at all: it's a museum bench.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

STONE, WOOD, STEEL = 0, 1, 2

pos4 = load("bake_bn_pos")
nor4 = load("bake_bn_nor")
facts4 = load("bake_bn_facts")
ao4 = load("bake_bn_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "bench.json")))
density, RANGE = meta["density"], meta["range"]
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4
pts = pos[cover]
print("coverage %.2f, %.1f px/in" % (cover.mean(), density), flush=True)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def solid(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


big = field(noise(pts, 0.05, 1, 3))
mid = field(noise(pts, 0.24, 2, 4))
fine = field(noise(pts, 1.2, 3, 3))
micro = field(noise(pts, 4.5, 4, 2))
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
crevice = np.clip((1 - ao) * 1.4, 0, 1)
up = np.clip(nor[..., 2], 0, 1)
stone = finish == STONE
wood = finish == WOOD
steel = finish == STEEL

# ---- Travertine ----
# Its bedding runs along the block: long thin layers, slightly wavy, and each of the two blocks was cut from a different part of the bed.
block_shift = np.where(X < 0, 3.7, -1.9)
wavy = Z + block_shift + 0.5 * (field(noise(pts * np.array((0.12, 0.12, 0.2), np.float32), 1.0, 5, 3)) - 0.5) * 6.0
beds = field(noise(np.column_stack((pts[:, 0] * 0.012, pts[:, 1] * 0.012, wavy[cover] * 1.1)), 1.0, 6, 4))
fine_beds = field(noise(np.column_stack((pts[:, 0] * 0.05, pts[:, 1] * 0.05, wavy[cover] * 5.0)), 1.0, 7, 3))
cream = mix(solid(204, 190, 162), solid(176, 158, 126), smooth(0.3, 0.72, beds))
cream = mix(cream, solid(150, 130, 98), smooth(0.58, 0.8, fine_beds) * 0.3)
cream = cream * (0.95 + 0.1 * mid[..., None])
# Open pores: small slots along the bedding, an inch long at most, some of them filled with paler cement over the years.
pore_raw = field(noise(np.column_stack((pts[:, 0] * 1.5, pts[:, 1] * 1.5, wavy[cover] * 11.0)), 1.0, 8, 2))
pores = smooth(0.72, 0.78, pore_raw + (fine - 0.5) * 0.06) * smooth(0.3, 0.55, beds)
filled = smooth(0.5, 0.56, field(noise(pts, 0.7, 9, 2)))
pit = pores * (1 - filled)
plug = pores * filled
s_color = mix(cream, solid(84, 72, 54) * (0.8 + 0.3 * fine[..., None]), pit * 0.85)
s_color = mix(s_color, solid(206, 192, 166), plug * 0.5)
s_height = -0.03 * pit + 0.0026 * (micro - 0.5) + 0.002 * (fine - 0.5)
s_rough = 0.4 + 0.1 * mid + 0.06 * fine + pit * 0.46 + plug * 0.14
# The joint between the two blocks: a thin dark line, slightly lipped.
joint = smooth(0.09, 0.03, np.abs(X)) * (Z > 1.0)
s_color = s_color * (1 - joint[..., None] * 0.66)
s_height = s_height - joint * 0.05
s_rough = s_rough + joint * 0.3
# Knocked on its corners, gently: the stone shows paler where it's chipped.
# Distance to an edge is measured along each face: every point of a side already lies on the block's outer plane, so measuring to the
# planes themselves would call the whole face an edge.
along_flank = 48.0 - np.abs(X)
along_end = 10.0 - np.abs(Y)
on_top = nor[..., 2] > 0.7
upright_corner = np.where(np.abs(nor[..., 0]) > np.abs(nor[..., 1]), along_end, along_flank)
edge_d = np.where(on_top, np.minimum(along_flank, along_end), np.minimum(upright_corner, np.abs(17.0 - Z)))
near = smooth(0.42, 0.04, edge_d)
chip = smooth(0.56, 0.68, near * (0.35 + 0.65 * smooth(0.4, 0.7, mid * 0.5 + fine * 0.5)))
s_color = mix(s_color, solid(222, 212, 192) * (0.9 + 0.2 * micro[..., None]), chip)
s_height = s_height - chip * 0.03
s_rough = s_rough * (1 - chip) + 0.72 * chip
# Sat against and walked into: polished where backs of knees rub the upper edge, scuffed by shoes low down, dirty at the floor.
polish = smooth(11.0, 15.5, Z) * smooth(0.5, 0.8, 1 - np.abs(X) / 48.0 + (big - 0.5) * 0.5) * (np.abs(nor[..., 2]) < 0.6)
s_rough = s_rough - polish * 0.1
s_color = s_color * (1 + polish[..., None] * 0.02)
scuff_band = smooth(1.2, 3.0, Z) * smooth(9.5, 4.5, Z) * (np.abs(nor[..., 2]) < 0.6)
scuffs = scuff_band * smooth(0.6, 0.76, field(noise(pts * np.array((0.12, 1.0, 1.0), np.float32), 1.5, 10, 3))) * smooth(0.34, 0.56, big + 0.1)
s_color = mix(s_color, solid(62, 56, 48), scuffs * 0.55)
floor_dirt = smooth(4.2, 1.0, Z + (mid - 0.5) * 1.6)
s_color = s_color * (1 - floor_dirt[..., None] * np.array((0.3, 0.32, 0.36), np.float32))
# Rain has run off the slats and marked the block's ends and flanks a little.
streak = field(noise(pts * np.array((1.0, 1.0, 0.07), np.float32), 0.7, 11, 4))
runs = smooth(0.54, 0.76, streak) * smooth(2.0, 15.0, Z) * (np.abs(nor[..., 2]) < 0.6)
s_color = s_color * (1 - runs[..., None] * np.array((0.13, 0.15, 0.2), np.float32))
s_rough = s_rough + runs * 0.08
# The plinth below the shadow gap is dark, and never seen in the light.
plinth = Z < 0.92
s_color = np.where(plinth[..., None], solid(30, 28, 26), s_color)
s_rough = np.where(plinth, 0.82, s_rough)

# ---- Teak ----
# Grain runs along each slat, and each slat came off a different board: part is that slat's own random number.
board = part * 80.0
grain_p = np.column_stack((pts[:, 0] * 0.035 + board[cover], pts[:, 1] * 5.0 + board[cover] * 3.0, pts[:, 2] * 5.0))
rings = field(noise(grain_p, 1.0, 12, 4))
pores_w = field(noise(np.column_stack((pts[:, 0] * 0.24 + board[cover], pts[:, 1] * 9.0, pts[:, 2] * 9.0)), 1.0, 13, 2))
cathedral = 0.5 + 0.5 * np.sin((rings * 12.0 + X * 0.05 + board) * 2.4)
honey = mix(solid(146, 104, 66), solid(116, 80, 48), smooth(0.28, 0.72, cathedral * 0.5 + rings * 0.5))
# Weathered silver where rain and sun reach; a little darker and slightly oily down the middle, where people sit.
seat = smooth(1.0, 0.55, np.abs(X) / 44.0 + (big - 0.5) * 0.3) * up
silver_amount = smooth(0.25, 0.7, 1 - seat * 0.8 + (mid - 0.5) * 0.5 + (fine - 0.5) * 0.25) * 0.6
silver = mix(solid(150, 140, 124), solid(120, 110, 96), smooth(0.3, 0.7, rings))
w_color = mix(honey, silver, silver_amount)
w_color = w_color * (1 - seat[..., None] * 0.1)
w_color = mix(w_color, w_color * 0.72, smooth(0.62, 0.8, pores_w) * 0.6)
# Slat ends show end grain, paler and checked.
ends = smooth(43.8, 44.0, np.abs(X)) + (np.abs(nor[..., 0]) > 0.6)
ends = np.clip(ends, 0, 1)
end_rings = 0.5 + 0.5 * np.sin(np.hypot(Y - np.round((Y + 9.0 - 1.8) / 3.6) * 3.6 - 1.8 + 9.0, Z - 16.4) * 17.0 + board)
w_color = np.where((ends > 0.5)[..., None], mix(solid(142, 110, 76), solid(114, 84, 56), end_rings), w_color)
w_rough = 0.66 + 0.1 * fine + silver_amount * 0.16 - seat * 0.2
w_height = 0.008 * (rings - 0.5) - 0.012 * smooth(0.62, 0.8, pores_w) + 0.0016 * (micro - 0.5)
# Dark stains where water sat round the screws.
for sx in (-32.0, 32.0):
    around = smooth(1.2, 0.15, np.abs(X - sx)) * up * smooth(0.36, 0.62, fine * 0.6 + mid * 0.4)
    w_color = w_color * (1 - around[..., None] * 0.36)

# ---- Stainless: brushed across, spotted with tea stain ----
brushed = field(noise(pts * np.array((6.0, 0.1, 6.0), np.float32), 1.0, 14, 2))
st_color = solid(176, 176, 172) * (0.86 + 0.2 * brushed[..., None])
tea = smooth(0.55, 0.78, mid + crevice * 0.3) * 0.5
st_color = mix(st_color, solid(120, 88, 58), tea)

color = np.where(stone[..., None], s_color, np.where(wood[..., None], w_color, st_color))
rough = np.where(stone, s_rough, np.where(wood, w_rough, 0.3 + 0.16 * brushed + tea * 0.3))
metal = np.where(steel, 1.0 - tea * 0.5, 0.0).astype(np.float32)
height = np.where(stone, s_height, np.where(wood, w_height, 0.0012 * (brushed - 0.5)))

# Dust on what faces up, least on the seat, and grime in the corners.
dust = smooth(0.5, 0.95, up * 0.6 + (big - 0.5) * 0.4 + crevice * 0.3 + (fine - 0.5) * 0.2) * 0.2 * (1 - np.where(wood, seat, 0.0))
color = mix(color, solid(150, 138, 116) * (0.8 + 0.4 * fine[..., None]), dust)
rough = rough * (1 - dust) + 0.9 * dust
metal = metal * (1 - dust)
grime = smooth(0.25, 0.9, crevice) * smooth(0.3, 0.7, mid)
color = mix(color, solid(62, 54, 44), grime * 0.42)
rough = rough * (1 - grime * 0.42) + 0.88 * grime * 0.42

color = color * (0.74 + 0.26 * ao[..., None])
normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope across an island's border sees the flat gutter and draws a line down the seam, so wide islands take their border's normal
# from just inside. Thin islands, which have no inside, keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.12, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "bn_bench_color.png"), color)
save_gray(os.path.join(OUT, "bn_bench_rough.png"), rough)
save_gray(os.path.join(OUT, "bn_bench_metal.png"), metal)
save_gray(os.path.join(OUT, "bn_bench_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "bn_bench_normal.png"), normal)
print("bench painted", flush=True)
