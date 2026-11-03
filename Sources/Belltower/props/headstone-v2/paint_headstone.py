"""Paint the stones' maps from their bakes and a real stone scan: python paint_headstone.py <work dir> <materials dir> headstone

The stone is the photo scan in scan_stone.npy (see scan_stone.py), laid on at its true scale, so its pits, grain, mottling and roughness are real. Over it goes an old
churchyard's weather, in strong values, as procedural soft colour reads as chalk: black crust where rain can't wash, dark runs under the heads, cut letters full of
soot, crusts of lichen with cracked surfaces, moss cushions and soil from the ground. The names and dates are made up, and there's no metal anywhere.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

STONE, FOOTING = range(2)
NAME = "headstone"
SCALE = 41.0  # The stone sheet's pixels to the inch. See scan_stone.py.
WINDOW_W, WINDOW_H = 25.0, 50.0  # The sheet is cut into windows this size, so no two stones or faces share the same bit of stone.
facts = json.load(open(os.path.join(WORK, "headstone.json")))
density, SLOT, STONES = facts["density"], facts["slot"], facts["stones"]

pos4 = load("bake_headstone_pos")
nor4 = load("bake_headstone_nor")
facts4 = load("bake_headstone_facts")
ao4 = load("bake_headstone_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = ((pos4[..., :3] - 0.5) * 400.0).astype(np.float32)
nor = (nor4[..., :3] * 2 - 1).astype(np.float32)
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
pos, nor, finish = fill_from(cover, pos, nor, finish)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0].astype(np.float32)
del pos4, nor4, facts4, ao4
print("loaded", cover.mean(), np.unique(finish), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
del dn, dp
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
edge = np.clip(ndi.gaussian_filter(np.clip((curve - 1.5) * 0.4, 0, 1), 4.0) * 3.0, 0, 1).astype(np.float32)
del curve
rows, cols = np.nonzero(cover)
pts = pos[rows, cols]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
slot = np.rint(Y / SLOT + 1.5).astype(np.int32)
slot = np.clip(slot, 0, 3)
local_y = Y - (slot - 1.5) * SLOT


def field(values):
    out = np.zeros((H, W), np.float32)
    out[rows, cols] = values
    return out


def C(r, g, b):
    return srgb_to_linear((r, g, b)).astype(np.float32)


def flat(c):
    return np.broadcast_to(c, (H, W, 3))


def blend(a, b, t):
    return a + (b - a) * t[..., None]


# The real stone, boxed on from whichever side a texel faces, each stone and side from its own part of the sheet.
sheet = np.load(os.path.join(WORK, "scan_stone.npy"))
cn = nor[rows, cols]
weight = np.abs(cn) ** 8
weight /= weight.sum(1, keepdims=True)
cs = slot[rows, cols]
cy = local_y[rows, cols]
scan = np.zeros((len(rows), sheet.shape[-1]), np.float32)
total = np.zeros(len(rows), np.float32)
for axis in range(3):
    pick = np.nonzero(weight[:, axis] > 0.01)[0]
    back = (cn[pick, axis] < 0).astype(np.float32)
    px, pz = pts[pick, 0], pts[pick, 2]
    if axis == 0:
        a, b, col = cy[pick] + 12.5, pz + 3.0, cs[pick]
    elif axis == 1:
        a, b, col = px + 12.5, pz + 3.0, (cs[pick] + 1) % 4
    else:
        a, b, col = px + 12.5, cy[pick] + 12.5, (cs[pick] + 2) % 4
    uu = (a + col * WINDOW_W) * SCALE
    vv = (b + back * WINDOW_H) * SCALE
    for c in range(sheet.shape[-1]):
        scan[pick, c] += weight[pick, axis] * ndi.map_coordinates(sheet[..., c], (vv, uu), order=1, mode="reflect")
    total[pick] += weight[pick, axis]
scan /= np.maximum(total, 1e-5)[:, None]
del sheet, total, weight, cn, cy, cs
scan_c = np.zeros((H, W, 3), np.float32)
scan_c[rows, cols] = scan[:, :3]
scan_h = field(scan[:, 3])
scan_r = field(scan[:, 4])
scan_ao = field(np.clip(scan[:, 5], 0, 1))
del scan
print("scan on", flush=True)

luma = scan_c @ np.array((0.2126, 0.7152, 0.0722), np.float32)
mean_luma = float(luma[rows, cols].mean())
relief = np.clip(scan_h / max(float(scan_h[rows, cols].std()), 1e-5) * 0.22 + 0.5, 0, 1)  # High on the stone's bumps, low in its pits.
speck = np.clip(luma / mean_luma * 0.5, 0, 1)  # Half at the scan's average tone.

big = field(noise(pts, 0.11, 1, 4))
mid = field(noise(pts, 0.62, 2, 4))
fine = field(noise(pts, 3.0, 3, 3))
micro = field(noise(pts, 8.5, 4, 2))
crevice = np.clip((1 - ao) * 1.4, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
top = np.choose(slot, (32.0, 29.0, 26.0, 40.0)).astype(np.float32)
print("fields", flush=True)

# Inscriptions, at 80 px to the inch: each stone's face as a picture, centred on its slot. Sharp for the letters' edges, wide for the cut's depth.
FONT = r"C:\Windows\Fonts\georgia.ttf"
PX = 80
K = PX // 40


def line_of(d, text, y, size, width, spacing=0.06):
    f = ImageFont.truetype(FONT, size * K)
    widths = [d.textlength(c, font=f) for c in text]
    total_w = sum(widths) + spacing * size * K * (len(text) - 1)
    x = (width - total_w) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, 255, font=f)
        x += w + spacing * size * K


def face_picture(kind):
    w, h = int(24 * PX), int(TOP_OF[kind] * PX)
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    cx = w / 2
    if kind == "arched":
        r = 9.8 * PX
        spring = h - (TOP_OF[kind] - 11.0) * PX
        d.arc((cx - r, spring - r, cx + r, spring + r), 180, 360, 255, 4 * K)
        d.line((cx - r, spring, cx - r, h - 5 * PX), 255, 4 * K)
        d.line((cx + r, spring, cx + r, h - 5 * PX), 255, 4 * K)
        d.line((cx, 1.7 * PX, cx, 4.6 * PX), 255, 5 * K)
        d.line((cx - 1.1 * PX, 2.6 * PX, cx + 1.1 * PX, 2.6 * PX), 255, 5 * K)
        rows_ = (("IN LOVING MEMORY OF", 6.0, 40), ("EDITH ARDLEY", 8.0, 66), ("WHO FELL ASLEEP", 11.0, 36), ("3 MARCH 1871", 13.0, 40), ("AGED 62 YEARS", 15.2, 36))
    elif kind == "shouldered":
        for k in range(8):
            a = k * math.tau / 8
            q = (cx + 1.15 * PX * math.cos(a), 3.4 * PX + 1.15 * PX * math.sin(a))
            d.ellipse((q[0] - 0.42 * PX, q[1] - 0.42 * PX, q[0] + 0.42 * PX, q[1] + 0.42 * PX), outline=255, width=4 * K)
        rows_ = (("HERE LIETH", 6.4, 46), ("THOS. WENLOCK", 8.8, 62), ("OF THIS PARISH", 11.6, 38), ("DIED 1794", 13.8, 44))
    elif kind == "low":
        rows_ = (("R. H.", 6.0, 92), ("1832", 9.6, 64))
    else:
        rows_ = (("AT REST", TOP_OF[kind] - 4.45, 26),)
    for text, inch, size in rows_:
        line_of(d, text, inch * PX, size, w)
    if kind == "shouldered":
        # A crack up from the foot, wandering, and wider low down.
        path, x_ = [], cx + 5.2 * PX
        rs = np.random.default_rng(23)
        for yy in np.linspace(h, h - 14 * PX, 40):
            x_ += float(rs.uniform(-0.2, 0.18)) * PX
            path.append((x_, yy))
        for k in range(len(path) - 1):
            d.line(path[k : k + 2], 255, max(2, int((5 - 3.5 * k / len(path)) * K)))
    sharp = np.asarray(img.filter(ImageFilter.GaussianBlur(0.7 * K)), np.float32) / 255.0
    wide = np.asarray(img.filter(ImageFilter.GaussianBlur(2.2 * K)), np.float32) / 255.0
    return sharp, wide


TOP_OF = dict(arched=32.0, shouldered=29.0, low=26.0, cross=40.0)
carved = np.zeros((H, W), np.float32)
cut_depth = np.zeros((H, W), np.float32)
# Weather has eaten the letters' edges a little, more in some places than others.
wander = np.stack((field(noise(pts, 1.5, 61, 2)), field(noise(pts + 40.0, 1.5, 62, 2))), -1) - 0.5
for index, kind in enumerate(STONES):
    sharp, wide = face_picture(kind)
    h_in = sharp.shape[0] / PX
    pick = (slot[rows, cols] == index) & (nor[rows, cols, 0] > 0.72)
    ri, ci = rows[pick], cols[pick]
    # From +X, a viewer's right is +Y, so the picture's left is -Y.
    uu = (local_y[ri, ci] + wander[ri, ci, 0] * 0.09 + 12.0) / 24.0
    vv = (Z[ri, ci] + wander[ri, ci, 1] * 0.09) / h_in
    carved[ri, ci] = sample_image(sharp, uu, vv)
    cut_depth[ri, ci] = sample_image(wide, uu, vv)
del wander
wear = smooth(0.42, 0.78, mid * 0.7 + fine * 0.3)
carved = smooth(0.3, 0.62, carved + (relief - 0.5) * 0.34) * (1 - wear * 0.32)
# A mason's dressed face holds less grime and growth round the letters than elsewhere, so they stay readable.
zone = np.clip(ndi.gaussian_filter((cut_depth > 0.02).astype(np.float32), 14.0) * 2.2, 0, 1)


# Each stone is its own block: saturation, gain, and tint on the scan's own colour. Contrast is pushed, so its darks stay dark after the tonemap.
GRADES = (
    (0.82, 1.02, (1.02, 1.0, 0.88)),  # Arched: a grey limestone.
    (0.9, 0.74, (1.03, 1.0, 0.86)),  # Shouldered: a darker, browner stone.
    (1.1, 0.9, (1.08, 1.0, 0.8)),  # Low: a warm sandstone.
    (0.74, 0.84, (1.01, 1.0, 0.88)),  # Cross: grey, and more blacked.
)
sat = np.choose(slot, [g[0] for g in GRADES]).astype(np.float32)
gain = np.choose(slot, [g[1] for g in GRADES]).astype(np.float32)
tint = np.stack([np.choose(slot, [g[2][c] for g in GRADES]).astype(np.float32) for c in range(3)], -1)
contrast = (np.maximum(luma, 1e-4) / mean_luma) ** 1.16
graded = (luma[..., None] + (scan_c - luma[..., None]) * sat[..., None]) / np.maximum(luma[..., None], 1e-4)
stone = graded * tint * (contrast * mean_luma * gain)[..., None]
del graded, contrast, tint, sat, gain

# Broad weather the scan's flattening took away: whole areas of a face lighter or darker.
tone = 0.8 + 0.42 * smooth(0.22, 0.78, big * 0.55 + mid * 0.45)
stone = stone * tone[..., None]
footing = finish == FOOTING
stone = np.where(footing[..., None], stone * 0.82, stone)
print("graded", flush=True)

# Soot mottling: the scan's own dark spots grow together in patches, so the shapes are the stone's and not a noise's.
soot = smooth(0.55, 0.72, mid * 0.5 + big * 0.18 + (1 - speck) * 0.42) * (1 - zone * 0.8)
stone = blend(stone, stone * 0.56, soot * 0.55)

# Rain: dark runs down from under the head, between paler washed lines where the water runs most.
streak = field(noise(pts * np.array((1.4, 1.4, 0.07), np.float32), 1.0, 12, 4))
upright = (np.abs(nor[..., 2]) < 0.6).astype(np.float32)
run = smooth(0.47, 0.6, streak + (relief - 0.5) * 0.1) * smooth(25.0, 3.0, top - Z) * upright
wash = smooth(0.62, 0.72, field(noise(pts * np.array((2.2, 2.2, 0.06), np.float32), 1.0, 13, 3))) * upright * smooth(1.0, 8.0, top - Z) * smooth(2.0, 10.0, Z)
stone = blend(stone, stone * 0.5, run * (1 - zone * 0.45) * 0.62)
stone = blend(stone, stone * 1.28, wash * 0.5)

# Green film, thin and uneven, on what stays damp: the lower half, and everything on the side away from the sun.
film = smooth(0.42, 0.68, big * 0.6 + fine * 0.2 + (1 - np.clip(Z / 30.0, 0, 1)) * 0.3)
stone = blend(stone, stone * np.array((0.62, 0.74, 0.42), np.float32), film * 0.42)

# Edges: rubbed paler, with small fresh chips out of them.
pale = (stone * 1.35 + C(138, 128, 108)) * 0.5 * np.clip(speck * 2.0, 0.55, 1.5)[..., None]
stone = blend(stone, pale, smooth(0.2, 0.85, edge) * 0.55)
chip = smooth(0.56, 0.63, edge * 0.74 + (mid - 0.5) * 0.45 + (relief - 0.5) * 0.45)
stone = blend(stone, flat(C(146, 136, 116)) * np.clip(speck * 2.0, 0.6, 1.4)[..., None], chip * 0.85)

# Black crust where rain can't wash: under arms and shoulders, in the corners, and under anything that overhangs.
under = smooth(-0.2, -0.75, nor[..., 2])
crust = np.clip(smooth(0.2, 0.7, crevice + (0.5 - speck) * 0.35) + under * 0.8, 0, 1)
stone = blend(stone, flat(C(30, 27, 22)) * np.clip(speck * 2.0, 0.7, 1.4)[..., None], crust * 0.86)
print("weather", flush=True)

# The letters, cut through whatever the weather has done.
stone = blend(stone, stone * 0.1 + C(8, 7, 6), carved * 0.96)
print("carved", flush=True)

# Lichen, sparse: small irregular colonies in a few patches, their outlines wandering at every size, cracked into plates and sunk into the stone's own surface.
patches = smooth(0.54, 0.68, field(noise(pts, 0.2, 52, 3)) + (fine - 0.5) * 0.16) * smooth(3.0, 8.0, Z) * (1 - zone * 0.9)
rng = np.random.default_rng(1781)
where = np.nonzero(patches[rows, cols] > 0.2)[0]
centre_idx = rng.choice(where, min(520, len(where)), replace=False)
centres = pts[centre_idx]
kinds = rng.choice(3, len(centres), p=(0.62, 0.1, 0.28))
radii = np.clip(rng.lognormal(-1.0, 0.55, len(centres)), 0.09, 1.25)
radii = np.where(kinds == 1, radii * 0.55, radii)
radii = np.r_[radii, 1.0].astype(np.float32)
wobble = np.stack([noise(pts, 0.9, 56 + k, 3) for k in range(3)], -1) - 0.5
dist, which = cKDTree(centres).query(pts + wobble * 0.55, k=3, distance_upper_bound=3.0, workers=4)
del wobble
ratio = dist / radii[which]
arg = np.argmin(ratio, 1)
inside = np.arange(len(pts))
ratio_min = ratio[inside, arg]
colony = which[inside, arg]
del dist, which, ratio, arg
lobes = 0.8 + 0.4 * noise(pts, 4.5, 53, 2)
shape = np.where(np.isfinite(ratio_min), ratio_min, 9.0) * lobes
alpha_ = smooth(1.0, 0.8, shape).astype(np.float32)
rim = (smooth(0.68, 0.94, shape) * alpha_).astype(np.float32)
busy = np.nonzero(alpha_ > 0.01)[0]
print("colonies", len(centres), "covered", len(busy) / len(pts), flush=True)
cells = rng.choice(busy, max(len(busy) // 44, 16), replace=False)
cell_tone = rng.uniform(0.84, 1.1, len(cells)).astype(np.float32)
near, cell = cKDTree(pts[cells]).query(pts[busy], k=2, workers=4)
crack = smooth(0.0, 0.05, near[:, 1] - near[:, 0]).astype(np.float32)
del near
kind_of = kinds[np.clip(colony[busy], 0, len(kinds) - 1)]
TABLE = np.stack((C(118, 124, 94), C(164, 104, 28), C(146, 146, 130)))
RIMS = np.stack((C(150, 154, 122), C(194, 142, 48), C(172, 172, 156)))
rgb = TABLE[kind_of] + (RIMS[kind_of] - TABLE[kind_of]) * rim[busy][:, None]
rgb = rgb * cell_tone[cell[:, 0]][:, None] * (0.55 + 0.45 * crack)[:, None]
# The pale crust carries tiny black fruiting dots.
dots = smooth(0.84, 0.9, noise(pts[busy], 20.0, 55, 1)) * (kind_of == 2)
rgb = rgb + (C(18, 16, 14) - rgb) * dots[:, None]
lichen_rgb = np.zeros((H, W, 3), np.float32)
lichen_rgb[rows[busy], cols[busy]] = rgb
lichen_rgb = lichen_rgb * np.clip(speck * 2.0, 0.6, 1.3)[..., None]
lichen = field(alpha_) * patches * (1 - carved * 0.8) * (0.65 + 0.7 * relief)
plates = np.zeros((H, W), np.float32)
plates[rows[busy], cols[busy]] = crack * alpha_[busy]
stone = blend(stone, lichen_rgb, np.clip(lichen, 0, 0.84))
del lichen_rgb, rgb, cells, cell_tone, cell, crack, kind_of, dots, alpha_, rim, colony, ratio_min, shape, lobes
print("lichen", flush=True)

# Moss, in broken clumps of small cushions: at the foot here and there, on some ledges and in sheltered corners. It takes the stone's pits first.
climb = smooth(5.5, 0.8, Z + (mid - 0.5) * 7.0 + (fine - 0.5) * 2.5) * smooth(0.38, 0.62, big * 0.5 + mid * 0.5)
ledge = smooth(0.7, 0.97, upward) * smooth(0.5, 0.7, big + (mid - 0.5) * 0.5) * (Z < 36.0)
corners = smooth(0.5, 0.95, crevice) * smooth(12.0, 3.0, Z) * smooth(0.35, 0.6, mid)
reach = np.clip(climb * 0.95 + ledge * 0.8 + corners * 0.55, 0, 1)
moss = smooth(0.46, 0.62, reach * 0.72 + fine * 0.28 + (0.5 - relief) * 0.18)
moss_at = np.nonzero(moss[rows, cols] > 0.01)[0]
seeds = rng.choice(moss_at, max(len(moss_at) // 160, 16), replace=False)
reach_d, _ = cKDTree(pts[seeds]).query(pts[moss_at], k=1, workers=4)
dome = np.zeros((H, W), np.float32)
dome[rows[moss_at], cols[moss_at]] = np.clip(1 - (reach_d / 0.32) ** 2, 0, 1)
del reach_d, seeds, moss_at
tips = smooth(0.52, 0.7, micro * 0.4 + fine * 0.6)
moss_c = blend(flat(C(16, 24, 9)), flat(C(50, 70, 22)), smooth(0.05, 0.6, dome))
moss_c = blend(moss_c, flat(C(96, 112, 34)), tips * smooth(0.3, 0.9, dome) * 0.6)
color = blend(stone, moss_c, moss * 0.92)
del moss_c, stone

# The foot: damp and dark where it meets the ground, with soil thrown up it by rain.
damp = smooth(5.0, 0.0, Z + (mid - 0.5) * 3.0)
color = blend(color, color * 0.46, damp * 0.85)
soil_c = flat(C(31, 24, 17)) * (0.7 + 0.6 * fine[..., None])
splash = smooth(0.62, 0.7, field(noise(pts, 3.4, 60, 2))) * smooth(8.0, 1.0, Z)
color = blend(color, soil_c, np.clip(smooth(1.8, 0.0, Z + (fine - 0.5) * 2.0) + splash * 0.8, 0, 0.94))

# Light on the surface follows the same stories.
rough = 0.56 + 0.42 * scan_r - damp * 0.2 - crust * 0.1 - run * 0.06
rough = rough + (0.96 - rough) * moss + (0.9 - rough) * np.clip(lichen, 0, 1) * 0.8 + (0.92 - rough) * carved * 0.7
metal = np.zeros((H, W), np.float32)
lumps = (big - 0.5) * 0.09 + (mid - 0.5) * 0.04
height = scan_h * 1.15 + lumps - cut_depth * (1 - wear * 0.32) * 0.13 - carved * 0.03 - chip * 0.05 + lichen * (0.012 + 0.012 * plates) + moss * (0.1 * dome + 0.02 * micro)
color = color * (0.5 + 0.5 * ao[..., None]) * np.clip(scan_ao, 0.25, 1)[..., None] ** 1.4
# A touch of sharpening makes up for the sampling's softness.
color = color + (color - np.stack([ndi.gaussian_filter(color[..., c], 1.2) for c in range(3)], -1)) * 0.4
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
half = lambda a: (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), half(half(metal)))
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), half(np.clip(ao * 1.03, 0, 1)))
print("stones painted", flush=True)
