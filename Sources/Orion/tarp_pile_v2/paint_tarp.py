"""Paint the tarp pile's maps from its bakes: python paint_tarp.py <work dir> <materials dir>

Olive PVC tarpaulin, kept even: sun-paled where it faces up, rubbed pale over the load's corners, dark and glossy where the rain has stayed in its hollows. Its welded panel seams, hemmed edge, brass eyelets and corner patches are placed on the flat
sheet, so they follow the folds. Yellow rope and hessian sandbags. ORN and every marking are the map's own.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

import numpy as np  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

TARP, ROPE, BAG = 9, 10, 11

pos4 = load("bake_tp_pos")
nor4 = load("bake_tp_nor")
facts4 = load("bake_tp_facts")
sheet4 = load("bake_tp_sheet")
ao4 = load("bake_tp_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
info = json.load(open(os.path.join(WORK, "tarp.json")))
density = info["density"]
SHEET_X, SHEET_Y = info["sheet"]
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
pos, nor, finish, st = fill_from(cover, pos, nor, finish, sheet4[..., :2])
aoc = ao4[..., 0] > 0.001
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
print("coverage %.2f" % cover.mean(), "finishes", np.unique(finish).tolist(), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 1.2) * 0.6, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 4.0) * 3.0, 0, 1)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


def place(art, left_to_right, up, u_mid, v_mid, long_in, tall_in):
    uu = 0.5 + (left_to_right - u_mid) / long_in
    vv = 0.5 + (up - v_mid) / tall_in
    return sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))


big = field(noise(pts, 0.05, 1, 3))
mid = field(noise(pts, 0.3, 2, 4))
fine = field(noise(pts, 2.2, 3, 3))
micro = field(noise(pts, 8.0, 4, 2))
streak = field(noise(pts * np.array((3.0, 3.0, 0.1), np.float32), 0.3, 6, 4))
crevice = np.clip((1 - ao) * 1.25, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NZ = nor[..., 2]
upward = np.clip(NZ, 0, 1)

tarp = finish == TARP
rope = finish == ROPE
bag = finish == BAG
color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.7, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

# ---- Where each texel is on the flat sheet, in inches. ----
SX, SY = st[..., 0] * SHEET_X, st[..., 1] * SHEET_Y
inset_x = np.minimum(SX, SHEET_X - SX)
inset_y = np.minimum(SY, SHEET_Y - SY)
inset = np.minimum(inset_x, inset_y)
sheet_pts = np.stack((SX[cover], SY[cover], np.zeros(int(cover.sum()), np.float32)), 1).astype(np.float32)

# The hem, folded over and welded: a double thickness to 2.6 in, with the weld's line at its edge.
hem = smooth(2.75, 2.45, inset)
weld_line = np.exp(-(((inset - 2.6) / 0.14) ** 2))
# Panels welded across the sheet, each overlap a little raised.
seam = np.zeros((H, W), np.float32)
seam_line = np.zeros((H, W), np.float32)
for at in (SHEET_Y / 4, SHEET_Y / 2, SHEET_Y * 3 / 4):
    seam = np.maximum(seam, smooth(1.15, 0.95, np.abs(SY - at)))
    seam_line = np.maximum(seam_line, np.exp(-(((np.abs(SY - at) - 1.05) / 0.14) ** 2)))
# A patch across each corner, where the sheet takes the strain.
corner = smooth(13.5, 13.0, inset_x + inset_y)
corner_line = np.exp(-(((inset_x + inset_y - 13.25) / 0.2) ** 2))
# Eyelets every 20 in round the hem.
along = np.where(inset_x < inset_y, SY, SX)
near = np.round(along / 20.0) * 20.0
hole_d = np.hypot(along - near, inset - 1.3)
eyelet = smooth(0.72, 0.6, hole_d)
hole = smooth(0.4, 0.3, hole_d)
# The lines it was folded along in store: straight across the flat sheet, each a fine crease that comes and goes.
wobble = (field(noise(sheet_pts, 0.03, 21, 2)) - 0.5) * 2.4
fold = np.zeros((H, W), np.float32)
for k in range(1, 5):
    fold = np.maximum(fold, np.exp(-(((SX + wobble - k * SHEET_X / 5) / 0.22) ** 2)))
for k in range(1, 3):
    fold = np.maximum(fold, np.exp(-(((SY - wobble - k * SHEET_Y / 3 + 12.0) / 0.22) ** 2)))
fold = fold * smooth(0.3, 0.6, field(noise(sheet_pts, 0.09, 22, 2)))


# ---- Stencils, sprayed on the flat sheet, each where it falls on one side of the load. ----

orn = stencil_image(["ORN"], (900, 420), bridge=False)
code = stencil_image(["GSE COVER 07"], (1400, 200), bridge=False)
sten = np.zeros((H, W), np.float32)
# (across the side, up it, the side's middle on the sheet) for the two long sides and the two ends.
mx, my = SHEET_X / 2, SHEET_Y / 2
for across, up, u, v in ((SY, -SX, my, -(mx + 61.0)), (-SY, SX, -my, mx - 61.0), (-SX, -SY, -mx, -(my + 73.0)), (SX, SY, mx, my - 73.0)):
    sten = np.maximum(sten, place(orn, across, up, u, v, 26.0, 12.0))
    sten = np.maximum(sten, place(code, across, up, u, v - 11.0, 34.0, 4.2))
sprayed = sten * tarp * smooth(0.1, 0.34, field(noise(pts, 1.6, 10, 3)) + (mid - 0.5) * 0.2 + 0.12)

# ---- The sheet. ----
base = flat((78, 90, 56)) * (0.94 + 0.12 * big[..., None])
paled = smooth(0.3, 0.85, upward * 0.7 + big * 0.5)
t_color = mix(base, flat((106, 112, 76)), paled * 0.5)
# Overlaps show darker where the coating is doubled, and each weld is a fine dark line.
t_color = t_color * (1 - 0.1 * np.clip(hem + seam + corner, 0, 1))[..., None]
t_color = t_color * (1 - 0.3 * np.clip(weld_line + seam_line + corner_line, 0, 1))[..., None]
# Rubbed pale over the load's corners and along its tension lines, softly.
rubbed = smooth(0.5, 0.95, edge + (mid - 0.5) * 0.2) * tarp
t_color = mix(t_color, flat((128, 130, 100)), rubbed * 0.26)
t_color = mix(t_color, flat((116, 120, 90)), fold * 0.3)
t_color = mix(t_color, flat((196, 196, 180)) * (0.84 + 0.16 * fine[..., None]), sprayed[..., None] * 0.88)
# After the rain: water stays in the hollows on top and runs down the folds in dark tracks.
wet = smooth(0.54, 0.86, upward * 0.72 + crevice * 0.22 + (big - 0.5) * 0.5)
runs = smooth(0.58, 0.86, streak + crevice * 0.12) * smooth(0.3, 0.62, mid) * (1 - upward)
wetness = np.clip(wet * 0.9 + runs * 0.3, 0, 1)
t_color = t_color * (1 - 0.3 * wetness)[..., None]
color = np.where(tarp[..., None], t_color, color)
t_rough = 0.8 + 0.06 * mid + 0.04 * fine + rubbed * 0.04 + sprayed * 0.04
t_rough = t_rough * (1 - wetness) + (0.5 + 0.08 * fine) * wetness
rough = np.where(tarp, t_rough, rough)
t_height = 0.0016 * (micro - 0.5) + 0.0014 * (fine - 0.5) + hem * 0.018 + seam * 0.016 + corner * 0.014 - fold * 0.012
height = np.where(tarp, t_height, height)
# The eyelets: brass rings, bright where rubbed, over a hole.
e_mask = eyelet * tarp
brass = mix(flat((132, 104, 54)) * (0.74 + 0.4 * fine[..., None]), flat((196, 166, 96)), smooth(0.5, 0.75, fine))
color = mix(color, brass, e_mask)
color = mix(color, np.broadcast_to(np.array((0.008, 0.008, 0.008), np.float32), (H, W, 3)), hole * tarp)
rough = rough * (1 - e_mask) + 0.42 * e_mask
metal = np.where(tarp, e_mask * (1 - hole), metal)
height = height + e_mask * 0.03 - hole * tarp * 0.05

# ---- Polypropylene rope: yellow with a black trace, fuzzy. ----
twist = smooth(0.64, 0.76, field(noise(pts, 3.6, 12, 2)))
r_color = mix(flat((214, 164, 30)) * (0.82 + 0.34 * mid[..., None]), flat((26, 26, 24)), twist * 0.7)
color = np.where(rope[..., None], r_color, color)
rough = np.where(rope, 0.72 + 0.12 * fine, rough)
height = np.where(rope, 0.016 * (field(noise(pts, 4.2, 13, 2)) - 0.5), height)

# ---- Hessian sandbags: dry on top, dark and damp from the ground up. ----
damp = smooth(3.4, 0.6, Z + (mid - 0.5) * 2.2)
weave = 0.5 + 0.5 * np.sin(X * 6.283) * np.sin(Y * 6.283)
b_color = flat((146, 128, 98)) * (0.78 + 0.26 * mid[..., None] + 0.14 * weave[..., None])
b_color = mix(b_color, b_color * np.array((0.48, 0.46, 0.44), np.float32), damp * 0.86)
color = np.where(bag[..., None], b_color, color)
rough = np.where(bag, 0.92 - damp * 0.2, rough)
height = np.where(bag, 0.01 * (field(noise(pts, 3.0, 14, 2)) - 0.5) + 0.006 * (micro - 0.5), height)

# Yard dirt: grit in what faces up and a tide of mud round the hem, with no blotches on the sheet itself.
lowness = np.clip((11.0 - Z) / 11.0, 0, 1) ** 1.6
splash = lowness * smooth(0.28, 0.82, field(noise(pts * np.array((1.2, 1.2, 0.5), np.float32), 0.9, 17, 4)) + lowness * 0.14)
dirt = np.clip(splash * 0.34 + crevice * 0.08, 0, 0.5)
color = mix(color, flat((50, 46, 38)) * (0.76 + 0.48 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.86 * dirt
metal = metal * (1 - dirt)

color = color * (0.72 + 0.28 * ao[..., None])
# The hem lying on the ground, dark where it meets it.
color = color * (0.8 + 0.2 * smooth(0.1, 1.2, Z))[..., None]
# Fill the gutters from every covered texel: eroding first would lose bevel strips a pixel or two wide.
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.6), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "tp_tarp_color.png"), color)
save_gray(os.path.join(OUT, "tp_tarp_rough.png"), rough)
save_gray(os.path.join(OUT, "tp_tarp_metal.png"), metal)
save_gray(os.path.join(OUT, "tp_tarp_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "tp_tarp_normal.png"), normal)
print("tarp painted", flush=True)
