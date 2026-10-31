"""Paint the tyres' maps from their bakes: python paint_tyre.py <work dir> <output dir>

Black rubber, aged grey on its sidewalls, with raised lettering that says only its size and type, kerb scuffs, dirt packed in its grooves and dust on what faces up. The bald one is more worn, shinier on its crown and crazed with fine
cracks on its sidewalls. Masks are soft or fine, since coarse thresholded noise reads as camouflage in the engine. No brands.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "CerroBlanco", "boulder-v2"))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, sample_image, save_gray, save_normal, save_rgb, srgb_to_linear, to_normal  # noqa: E402
from rock_noise import fbm, smooth  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

CENTRE_Z = 4.035
pos4 = load("bake_ty_pos")
nor4 = load("bake_ty_nor")
tangent4 = load("bake_ty_tangent")
masks4 = load("bake_ty_masks")
ao4 = load("bake_ty_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "tyre.json")))
RANGE = meta["range"]
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
tangent = tangent4[..., :3] * 2 - 1
masks = masks4[..., :3]
hit = cover & (np.abs(tangent).max(-1) > 1e-3)
pos, nor = fill_from(cover, pos, nor)
tangent, masks = fill_from(hit, tangent, masks)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ao, W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, tangent4, masks4, ao4
pts = pos[cover].astype(np.float32)
print("coverage %.2f, sculpt reaches %.3f" % (cover.mean(), hit.sum() / max(cover.sum(), 1)), flush=True)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def solid(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


bald = pos[..., 0] > 0
X = pos[..., 0] - np.where(bald, meta["offsets"]["b"], meta["offsets"]["a"])
Y, dz = pos[..., 1], pos[..., 2] - CENTRE_Z
r = np.hypot(X, Y)
theta = np.arctan2(Y, X)
groove = np.clip(masks[..., 0], 0, 1)
crevice = np.clip((1 - ao) * 1.4, 0, 1)
# Which way each texel faces, against which way it'd face on the outside of the section, says whether it's the liner.
radial = (nor[..., 0] * X + nor[..., 1] * Y) / np.maximum(r, 1e-6)
liner = (radial * (r - 10.3) + nor[..., 2] * dz) < 0
tread = (r > 12.1) & ~liner
sidewall = (r <= 12.1) & ~liner

big = field(fbm(pts, 0.05, 401, 3))
mid = field(fbm(pts, 0.28, 402, 3))
fine = field(fbm(pts, 1.5, 403, 2))
micro = field(fbm(pts, 6.0, 404, 2))
print("noise", flush=True)
polar = np.column_stack((theta[cover] * 12.0, r[cover], dz[cover] * 1.0)).astype(np.float32)
along_ring = field(fbm(polar * np.array((0.05, 2.2, 2.2), np.float32), 1.0, 405, 3))
across_ring = field(fbm(polar * np.array((3.2, 0.12, 0.12), np.float32), 1.0, 406, 2))

# ---- Rubber: nearly black, greyed by age on its sidewalls ----
color = solid(26, 26, 26) * (0.86 + 0.24 * micro[..., None] + 0.1 * fine[..., None])
age = sidewall * smooth(-0.45, 0.45, big + mid * 0.4)
aged = np.where(bald, 0.62, 0.34)
color = mix(color, solid(66, 65, 62), age * aged)
rough = 0.72 + 0.08 * mid + 0.05 * fine
height = 0.004 * micro + 0.003 * fine

# ---- The tread: blocks' tops worn smooth, dirt packed in their grooves ----
crown = tread * (1.0 - groove)
rough = rough - crown * np.where(bald, 0.26, 0.12)
color = mix(color, solid(44, 43, 41), crown * np.where(bald, 0.5, 0.25))
# Fine lengthwise wear lines round the crown.
wear = crown * smooth(-0.1, 0.45, along_ring)
color = mix(color, solid(60, 58, 54), wear * 0.22)
height = height - wear * 0.004
dirt = groove * smooth(-0.35, 0.25, mid + fine * 0.4)
color = mix(color, solid(72, 62, 48) * (0.8 + 0.34 * fine[..., None]), dirt * 0.74)
rough = rough + dirt * 0.14

# ---- The sidewall's raised lettering, its size and type only, round both sides ----
FONT = os.path.join(ROOT, "Assets", "fonts", "Dinish-Bold.ttf")
strip = Image.new("L", (6144, 180), 0)
d = ImageDraw.Draw(strip)
font = ImageFont.truetype(FONT, 118)
for k, words in enumerate(("RADIAL TUBELESS", "205/65 R16", "STEEL BELTED", "205/65 R16")):
    d.text((6144 * (k + 0.5) / 4, 90), words, font=font, fill=255, anchor="mm")
letters_art = ndi.gaussian_filter(np.asarray(strip, np.float32) / 255.0, 0.9)
letters = np.zeros((H, W), np.float32)
# Reading round the ring with letter tops outward: seen from each side, a reader's right runs opposite ways.
for side, direction in ((1.0, -1.0), (-1.0, 1.0)):
    uu = ((direction * theta + np.where(bald, 1.1, 0.2)) / (2 * math.pi)) % 1.0
    vv = (r - 9.55) / 0.95
    here = (dz * side > 0) & sidewall
    letters = np.maximum(letters, sample_image(letters_art, uu, np.clip(vv, -1, 2)) * here)
color = mix(color, solid(70, 69, 66), letters * smooth(-0.5, 0.2, mid) * 0.5)
height = height + letters * 0.02

# ---- Kerb scuffs: pale scrapes running round its widest part ----
band = sidewall * smooth(10.0, 10.6, r) * smooth(11.75, 11.2, r)
scuff = band * smooth(0.02, 0.4, along_ring) * smooth(-0.25, 0.3, big + across_ring * 0.4)
color = mix(color, solid(98, 96, 90) * (0.8 + 0.3 * micro[..., None]), scuff * np.where(bald, 0.55, 0.32))
rough = rough + scuff * 0.1
height = height - scuff * 0.006

# ---- Fine cracks on the old one's sidewalls ----
crack_field = 1.0 - np.abs(field(fbm(polar * np.array((3.8, 1.1, 1.1), np.float32), 1.0, 407, 2)))
cracks = sidewall * bald * smooth(0.965, 0.995, crack_field) * smooth(-0.3, 0.2, big)
color = mix(color, solid(10, 10, 10), cracks * 0.7)
height = height - cracks * 0.018

# ---- The liner: darker, a little shiny, never clean ----
color = np.where(liner[..., None], solid(16, 16, 16) * (0.8 + 0.3 * fine[..., None]), color)
rough = np.where(liner, 0.58 + 0.08 * mid, rough)

# ---- Dust on what faces up, grime in corners ----
up = np.clip(nor[..., 2], 0, 1)
dust = smooth(0.45, 0.95, up + big * 0.25 + fine * 0.1) * smooth(-0.4, 0.3, mid) * 0.26 * (~liner)
color = mix(color, solid(112, 102, 88) * (0.82 + 0.3 * micro[..., None]), dust)
rough = rough * (1 - dust) + 0.92 * dust
grime = smooth(0.25, 0.9, crevice) * smooth(-0.3, 0.3, mid) * (~liner)
color = mix(color, solid(50, 44, 36), grime * 0.4)

color = color * (0.74 + 0.26 * ao[..., None])
print("painted", flush=True)

# The sculpt's normals with the fine detail laid over them. Texels run denser round the inside of the ring than round the tread.
px_u = W / (2 * math.pi * np.maximum(r, 7.0))
detail = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), px_u, 1.0, meta["px_per_in_v"])
normal = tangent + detail * np.array((1, 1, 0), np.float32)
normal = normal / np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-6)
normal[..., 2] = np.abs(normal[..., 2])
color, rough, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.3, 1), normal)
save_rgb(os.path.join(OUT, "ty_tyre_color.png"), color)
save_gray(os.path.join(OUT, "ty_tyre_rough.png"), rough)
save_gray(os.path.join(OUT, "ty_tyre_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "ty_tyre_normal.png"), normal)
print("tyre painted", flush=True)
