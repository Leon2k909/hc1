"""Paint the stones' maps from their bakes: python paint_headstone.py <work dir> <materials dir> headstone

Old limestone in the map's own warm grey: faint bedding, rain streaks under the heads, lichen in soft rosettes, moss creeping up from the ground, and
inscriptions cut in the faces and worn by two centuries of weather. Every mask is soft, since hard cut-offs read as blocks at this density. The names and dates
are made up, and there's no metal anywhere.
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
part = facts4[..., 1].astype(np.float32)
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0].astype(np.float32)
del pos4, nor4, facts4, ao4
print("loaded", cover.mean(), np.unique(finish), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=1)] = 0
edge = np.clip(ndi.gaussian_filter(np.clip((curve - 1.5) * 0.4, 0, 1), 2.0) * 3.0, 0, 1).astype(np.float32)
rows, cols = np.nonzero(cover)
pts = pos[rows, cols]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
slot = np.rint(Y / SLOT + 1.5).astype(np.int32)
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


big = field(noise(pts, 0.11, 1, 3))
mid = field(noise(pts, 0.62, 2, 3))
fine = field(noise(pts, 3.0, 3, 3))
micro = field(noise(pts, 8.5, 4, 2))
crevice = np.clip((1 - ao) * 1.4, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
print("fields", flush=True)

# The stone: warm limestone, its bedding running level, each block its own colour.
bedding = field(noise(pts * np.array((0.28, 0.28, 2.2), np.float32) + part[rows, cols][:, None] * 37.0, 1.0, 11, 3))
tone = np.choose(np.clip(slot, 0, 3), (0.96, 1.05, 0.9, 1.0)).astype(np.float32)
stone = blend(flat(C(150, 140, 120)), flat(C(126, 116, 98)), smooth(0.25, 0.75, bedding * 0.28 + big * 0.72))
# Fine grain and small weathered pits, which a limestone's face is mostly made of up close.
pits = smooth(0.66, 0.84, micro * 0.65 + fine * 0.35)
stone = stone * tone[..., None] * (0.95 + 0.1 * fine[..., None]) * (0.95 + 0.1 * micro[..., None]) * (1 - pits[..., None] * 0.3)
footing = finish == FOOTING
stone = np.where(footing[..., None], stone * 0.86, stone)
# Edges have weathered paler; rain has left long soft streaks under the head.
stone = blend(stone, flat(C(168, 158, 136)), smooth(0.2, 0.8, edge) * 0.42)
streak = field(noise(pts * np.array((1.5, 1.5, 0.08), np.float32), 1.0, 12, 3))
top = np.choose(np.clip(slot, 0, 3), (32.0, 29.0, 26.0, 40.0)).astype(np.float32)
run = smooth(0.42, 0.7, streak) * smooth(22.0, 2.0, top - Z) * (np.abs(nor[..., 2]) < 0.6)
stone = blend(stone, stone * 0.64, run * 0.75)
# Black crust gathers where rain can't wash: under arms, the ring and the shoulders, and in the corners.
stone = blend(stone, flat(C(44, 40, 34)), smooth(0.32, 0.85, crevice) * 0.62)
print("stone", flush=True)

# Inscriptions. Each stone's face as a picture, 40 px to the inch, centred on its slot: right is -... +Y seen from +X, so y runs right to left.
FONT = r"C:\Windows\Fonts\georgia.ttf"
PX = 40
carved = np.zeros((H, W), np.float32)


def line_of(d, text, y, size, width, spacing=0.06):
    f = ImageFont.truetype(FONT, size)
    widths = [d.textlength(c, font=f) for c in text]
    total = sum(widths) + spacing * size * (len(text) - 1)
    x = (width - total) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, 255, font=f)
        x += w + spacing * size


def face_picture(kind):
    w, h = int(24 * PX), int(top_of[kind] * PX)
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    cx = w / 2
    if kind == "arched":
        r = 9.8 * PX
        spring = h - (top_of[kind] - 11.0) * PX
        d.arc((cx - r, spring - r, cx + r, spring + r), 180, 360, 255, 4)
        d.line((cx - r, spring, cx - r, h - 5 * PX), 255, 4)
        d.line((cx + r, spring, cx + r, h - 5 * PX), 255, 4)
        d.line((cx - 0.5 * PX, 2.6 * PX, cx + 0.5 * PX, 2.6 * PX), 255, 5)
        d.line((cx, 1.7 * PX, cx, 4.6 * PX), 255, 5)
        d.line((cx - 1.1 * PX, 2.6 * PX, cx + 1.1 * PX, 2.6 * PX), 255, 5)
        rows_ = (("IN LOVING MEMORY OF", 6.0, 40), ("EDITH ARDLEY", 8.0, 66), ("WHO FELL ASLEEP", 11.0, 36), ("3 MARCH 1871", 13.0, 40), ("AGED 62 YEARS", 15.2, 36))
    elif kind == "shouldered":
        for k in range(8):
            a = k * math.tau / 8
            q = (cx + 1.15 * PX * math.cos(a), 3.4 * PX + 1.15 * PX * math.sin(a))
            d.ellipse((q[0] - 0.42 * PX, q[1] - 0.42 * PX, q[0] + 0.42 * PX, q[1] + 0.42 * PX), outline=255, width=4)
        rows_ = (("HERE LIETH", 6.4, 46), ("THOS. WENLOCK", 8.8, 62), ("OF THIS PARISH", 11.6, 38), ("DIED 1794", 13.8, 44))
    elif kind == "low":
        rows_ = (("R. H.", 6.0, 92), ("1832", 9.6, 64))
    else:
        rows_ = (("AT REST", top_of[kind] - 4.45, 26),)
    for text, inch, size in rows_:
        line_of(d, text, inch * PX, size, w)
    if kind == "shouldered":
        # A crack up from the foot, soft-edged, wandering a little.
        path, x_ = [], cx + 5.2 * PX
        rs = np.random.default_rng(23)
        for yy in np.linspace(h, h - 12 * PX, 18):
            x_ += float(rs.uniform(-0.34, 0.3)) * PX
            path.append((x_, yy))
        d.line(path, 255, 3)
    return np.asarray(img.filter(ImageFilter.GaussianBlur(1.1)), np.float32) / 255.0


top_of = dict(arched=32.0, shouldered=29.0, low=26.0, cross=40.0)
wear_mask = smooth(0.42, 0.78, mid * 0.7 + fine * 0.3)
for index, kind in enumerate(STONES):
    pic = face_picture(kind)
    h_in = pic.shape[0] / PX
    pick = (slot[rows, cols] == index) & (nor[rows, cols, 0] > 0.72)
    ri, ci = rows[pick], cols[pick]
    # From +X, a viewer's right is +Y, so the picture's left is -Y.
    uu = (local_y[ri, ci] + 12.0) / 24.0
    vv = Z[ri, ci] / h_in
    carved[ri, ci] = sample_image(pic, uu, vv)
carved = carved * (1 - wear_mask * 0.45)
stone = blend(stone, stone * 0.34, np.clip(carved * 1.05, 0, 1))
print("carved", flush=True)

# Lichen grows in patches where the weather suits it, each patch made of many small lobed crusts, close to the stone's own colour.
patches = smooth(0.5, 0.68, field(noise(pts, 0.2, 52, 3)) + (fine - 0.5) * 0.2) * smooth(1.5, 8.0, Z)
rng = np.random.default_rng(1781)
stone_pts = np.nonzero((patches > 0.15).ravel())[0]
seed_idx = rng.choice(stone_pts, min(9000, len(stone_pts)), replace=False)
seed_pos = pos.reshape(-1, 3)[seed_idx]
radii = rng.uniform(0.07, 0.5, len(seed_pos)) ** 1.3
dist, which = cKDTree(seed_pos).query(pts, k=1, workers=1)
lobes = 0.74 + 0.5 * noise(pts, 5.0, 53, 2)
crust = smooth(1.0, 0.62, dist / radii[which] * lobes)
lichen = field(crust.astype(np.float32)) * patches * (1 - carved * 0.5)
warm_here = smooth(0.6, 0.72, field(noise(pts, 0.16, 54, 2)))
pale = flat(C(170, 170, 148)) * (0.9 + 0.18 * micro[..., None])
warm = flat(C(166, 136, 78)) * (0.9 + 0.18 * micro[..., None])
stone = blend(stone, pale, patches * 0.12)
stone = blend(stone, blend(pale, warm, warm_here), lichen * 0.62)
print("lichen", flush=True)

# Moss: from the ground up the foot, and on what faces the sky, thick in the shade of corners. No hard edge.
climb = smooth(9.5, 1.5, Z + (mid - 0.5) * 7.0 + (fine - 0.5) * 2.0)
ledge = smooth(0.55, 0.95, upward) * smooth(0.42, 0.72, big + (mid - 0.5) * 0.35) * (Z < 34.0)
moss = np.clip(climb * 0.85 + ledge * 0.75 + smooth(0.5, 0.95, crevice) * smooth(14.0, 3.0, Z) * 0.5, 0, 1) * smooth(0.25, 0.6, fine * 0.5 + mid * 0.5)
moss_c = blend(flat(C(62, 80, 34)), flat(C(104, 112, 50)), smooth(0.35, 0.8, fine)) * (0.84 + 0.3 * micro[..., None])
color = blend(stone, moss_c, moss * 0.9)
# The foot stays damp and dark where it meets the ground.
color = blend(color, color * 0.52, smooth(2.6, 0.0, Z) * 0.8)

rough = 0.88 + 0.06 * fine + moss * 0.05 - run * 0.04 + lichen * 0.02
metal = np.zeros((H, W), np.float32)
height = 0.03 * (fine - 0.5) + 0.014 * (micro - 0.5) + 0.012 * (bedding - 0.5) + (big - 0.5) * 0.05 - pits * 0.018 - carved * 0.075 + lichen * 0.012 + moss * (fine * 0.045)
color = color * (0.7 + 0.3 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.6), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
half = lambda a: (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), half(metal))
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), half(np.clip(ao * 1.03, 0, 1)))
print("stones painted", flush=True)
