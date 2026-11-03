"""Paint the canvas cover's maps from its bakes: python paint_canvas.py <work dir> <materials dir>

Made from Orion's paint_tarp.py. Mustard-khaki cotton duck, the old cover's colour as the game draws it (its live sw_tarp is canvas_plain tinted 0.78, 0.69, 0.54),
kept even: sun-paled where it faces up, rubbed pale over the load's corners, darker and tide-marked where rain has soaked in, a little
mildew low down. Its sewn seams, stitched hem, brass grommets and corner patches are placed on the flat sheet, so they follow the folds,
and so is a faded stencil, B2 GEN 2, the map's own deck name. Orange polyester ratchet straps with zinc-plated steel hardware.
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

TARP, STRAP, BUCKLE = 9, 10, 11
HALF_X, HALF_Y = 65.0, 70.0

pos4 = load("bake_cc_pos")
nor4 = load("bake_cc_nor")
facts4 = load("bake_cc_facts")
sheet4 = load("bake_cc_sheet")
ao4 = load("bake_cc_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
info = json.load(open(os.path.join(WORK, "canvas.json")))
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


big = field(noise(pts, 0.04, 1, 3))
mid = field(noise(pts, 0.25, 2, 4))
fine = field(noise(pts, 2.2, 3, 3))
micro = field(noise(pts, 8.0, 4, 2))
streak = field(noise(pts * np.array((3.0, 3.0, 0.1), np.float32), 0.3, 6, 4))
crevice = np.clip((1 - ao) * 1.25, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NZ = nor[..., 2]
upward = np.clip(NZ, 0, 1)

tarp = finish == TARP
strap = finish == STRAP
steel = finish == BUCKLE
color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.8, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

# ---- Where each texel is on the flat sheet, in inches. ----
SX, SY = st[..., 0] * SHEET_X, st[..., 1] * SHEET_Y
inset_x = np.minimum(SX, SHEET_X - SX)
inset_y = np.minimum(SY, SHEET_Y - SY)
inset = np.minimum(inset_x, inset_y)
sheet_pts = np.stack((SX[cover], SY[cover], np.zeros(int(cover.sum()), np.float32)), 1).astype(np.float32)


def stitches(distance, at, spacing=0.3):
    """A sewn line at inset `at`: dashes of thread a stitch long."""
    line = np.exp(-(((distance - at) / 0.09) ** 2))
    return line * smooth(0.25, 0.45, 0.5 + 0.5 * np.sin(along_sheet * 2 * np.pi / spacing))


# The hem, turned over twice and sewn: a triple thickness to 2.2 in, two rows of stitches.
along_sheet = np.where(inset_x < inset_y, SY, SX)
hem = smooth(2.35, 2.05, inset)
hem_stitch = np.maximum(stitches(inset, 0.6), stitches(inset, 1.9))
# Panels sewn across it, 36 in wide as duck comes off the roll, each lap a little raised and stitched each side.
seam = np.zeros((H, W), np.float32)
seam_stitch = np.zeros((H, W), np.float32)
for k in range(1, int(SHEET_Y // 36) + 1):
    at = k * 36.0
    if at > SHEET_Y - 6:
        break
    d = np.abs(SY - at)
    seam = np.maximum(seam, smooth(0.85, 0.65, d))
    seam_stitch = np.maximum(seam_stitch, np.maximum(np.exp(-(((d - 0.55) / 0.09) ** 2)), np.exp(-(((d - 0.2) / 0.09) ** 2))) * smooth(0.25, 0.45, 0.5 + 0.5 * np.sin(SX * 2 * np.pi / 0.3)))
# A patch across each corner, and brass grommets every 24 in round the hem.
corner = smooth(11.5, 11.0, inset_x + inset_y)
near = np.round(along_sheet / 24.0) * 24.0
hole_d = np.hypot(along_sheet - near, inset - 1.2)
grommet = smooth(0.62, 0.5, hole_d)
hole = smooth(0.33, 0.25, hole_d)
# The lines it was folded along in store, straight across the flat sheet, each a fine crease that comes and goes.
wobble = (field(noise(sheet_pts, 0.03, 21, 2)) - 0.5) * 2.4
fold = np.zeros((H, W), np.float32)
for k in range(1, 6):
    fold = np.maximum(fold, np.exp(-(((SX + wobble - k * SHEET_X / 6) / 0.24) ** 2)))
for k in range(1, 4):
    fold = np.maximum(fold, np.exp(-(((SY - wobble - k * SHEET_Y / 4 + 9.0) / 0.24) ** 2)))
fold = fold * smooth(0.3, 0.6, field(noise(sheet_pts, 0.08, 22, 2)))

# ---- The stencil, sprayed once on the flat sheet and long since faded: on the two sides players see, the map's north (+X) and east (-Y). ----
deck = stencil_image(["B2  GEN 2"], (1500, 260), bridge=True)
mx, my = SHEET_X / 2, SHEET_Y / 2
sten = np.maximum(place(deck, SY, -SX, my - 6.0, -(mx + HALF_X + 26.0), 40.0, 7.0),
                  place(deck, SX, SY, mx + 4.0, my - (HALF_Y + 26.0), 40.0, 7.0))
sprayed = sten * tarp * smooth(0.12, 0.4, field(noise(pts, 1.6, 10, 3)) + (mid - 0.5) * 0.25 + 0.1)

# ---- The canvas: khaki cotton duck. ----
base = flat((156, 126, 78)) * (0.95 + 0.1 * big[..., None])
paled = smooth(0.3, 0.85, upward * 0.7 + big * 0.5)
t_color = mix(base, flat((180, 154, 108)), paled * 0.45)
t_color = t_color * (1 - 0.08 * np.clip(hem + seam + corner, 0, 1))[..., None]
# Thread: a shade paler than the cloth, as cotton thread fades less.
thread = np.clip(hem_stitch + seam_stitch, 0, 1) * tarp
t_color = mix(t_color, flat((186, 166, 126)), thread * 0.45)
rubbed = smooth(0.5, 0.95, edge + (mid - 0.5) * 0.2) * tarp
t_color = mix(t_color, flat((182, 160, 118)), rubbed * 0.24)
t_color = mix(t_color, flat((166, 140, 96)), fold * 0.3)
t_color = mix(t_color, flat((40, 38, 32)) * (0.9 + 0.2 * fine[..., None]), sprayed[..., None] * 0.62)
# Canvas soaks the rain up rather than shedding it: darker where it has stood on top, with paler tide lines where it dried.
wet = smooth(0.56, 0.88, upward * 0.7 + crevice * 0.24 + (big - 0.5) * 0.5)
runs = smooth(0.6, 0.86, streak + crevice * 0.12) * smooth(0.3, 0.62, mid) * (1 - upward)
soaked = np.clip(wet * 0.8 + runs * 0.32, 0, 1)
tide = np.exp(-(((soaked - 0.42) / 0.05) ** 2)) * smooth(0.2, 0.6, fine) * 0.5
t_color = t_color * (1 - 0.26 * soaked)[..., None]
t_color = mix(t_color, flat((182, 160, 118)), tide * 0.25)
# Mildew in specks low down and in the deepest folds, sparse.
# Fine, so a cluster doesn't read as a hole.
specks = smooth(0.77, 0.83, field(noise(pts, 7.0, 23, 2))) * smooth(0.55, 0.85, crevice * 0.3 + np.clip((20.0 - Z) / 20.0, 0, 1) * 0.8)
t_color = mix(t_color, flat((86, 84, 62)), specks * 0.3)
color = np.where(tarp[..., None], t_color, color)
t_rough = 0.88 + 0.05 * mid + 0.03 * fine + sprayed * 0.03 - soaked * 0.06
rough = np.where(tarp, t_rough, rough)
# Duck's weave is too fine to draw at this size; its roughness and the hem, seams and folds are what read.
t_height = 0.0018 * (micro - 0.5) + 0.0012 * (fine - 0.5) + hem * 0.016 + seam * 0.012 + corner * 0.012 - fold * 0.012 + thread * 0.004
height = np.where(tarp, t_height, height)
g_mask = grommet * tarp
brass = mix(flat((120, 96, 52)) * (0.74 + 0.4 * fine[..., None]), flat((178, 150, 88)), smooth(0.5, 0.75, fine))
color = mix(color, brass, g_mask)
color = mix(color, np.broadcast_to(np.array((0.008, 0.008, 0.008), np.float32), (H, W, 3)), hole * tarp)
rough = rough * (1 - g_mask) + 0.45 * g_mask
metal = np.where(tarp, g_mask * (1 - hole) * 0.7, metal)
height = height + g_mask * 0.025 - hole * tarp * 0.04

# ---- Orange polyester webbing, sun-faded on top, grubby where it's handled. ----
ribs = 0.5 + 0.5 * np.sin(field(noise(pts, 0.9, 31, 2)) * 60.0)
s_color = flat((206, 92, 28)) * (0.82 + 0.26 * mid[..., None] + 0.06 * ribs[..., None])
s_color = mix(s_color, flat((196, 128, 86)), upward[..., None] * 0.28)
s_color = mix(s_color, flat((70, 50, 36)), smooth(0.55, 0.9, fine * 0.5 + np.clip((40.0 - Z) / 40.0, 0, 1) * 0.5) * 0.3)
color = np.where(strap[..., None], s_color, color)
rough = np.where(strap, 0.7 + 0.08 * fine, rough)
height = np.where(strap, 0.004 * (ribs - 0.5) + 0.003 * (micro - 0.5), height)

# ---- Zinc-plated steel: dull, with rust coming through at the edges. ----
rust = smooth(0.55, 0.8, edge * 0.6 + fine * 0.5) * steel
z_color = mix(flat((140, 140, 134)) * (0.8 + 0.3 * fine[..., None]), flat((112, 62, 30)), rust * 0.8)
color = np.where(steel[..., None], z_color, color)
rough = np.where(steel, 0.42 + 0.3 * rust + 0.08 * fine, rough)
metal = np.where(steel, 0.68 * (1 - rust), metal)
height = np.where(steel, 0.002 * (micro - 0.5) + rust * 0.003, height)

# Deck grit round the hem and in what faces up.
lowness = np.clip((10.0 - Z) / 10.0, 0, 1) ** 1.6
splash = lowness * smooth(0.28, 0.82, field(noise(pts * np.array((1.2, 1.2, 0.5), np.float32), 0.9, 17, 4)) + lowness * 0.14)
dirt = np.clip(splash * 0.32 + crevice * 0.08, 0, 0.5)
color = mix(color, flat((60, 56, 48)) * (0.76 + 0.48 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.88 * dirt
metal = metal * (1 - dirt)

color = color * (0.8 + 0.2 * ao[..., None])
color = color * (0.86 + 0.14 * smooth(0.1, 1.2, Z))[..., None]
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.6), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "cc_canvas_color.png"), color)
save_gray(os.path.join(OUT, "cc_canvas_rough.png"), rough)
save_gray(os.path.join(OUT, "cc_canvas_metal.png"), metal)
save_gray(os.path.join(OUT, "cc_canvas_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "cc_canvas_normal.png"), normal)
print("canvas painted", flush=True)
