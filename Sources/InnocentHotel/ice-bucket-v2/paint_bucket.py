"""Paint the ice bucket's maps from its bakes: python paint_bucket.py <work dir> <materials dir>

Pebbled black vinyl, stitched along its piping and down a seam under one handle, with a gold-foil hotel crest stamped on the
front and back. Brass tarnished in its recesses and rubbed bright on the rim, the plates and where a hand takes the rings.
A brushed steel liner with a tide line, and ice with cloudy hearts in dark melt water. Worn where a bucket is worn: round
the base, by the handles, along the piping. Lettering is the fictional hotel's own name.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

VINYL, BRASS, STEEL, ICE, WATER = 1, 2, 3, 4, 5
NAME = "ice_bucket"
facts = json.load(open(os.path.join(WORK, "bucket.json")))
density = facts["density"]
WALL_LOW, WALL_HIGH, WATER_Z, HANDLE_Z = facts["wall_low"], facts["wall_high"], facts["water"], facts["handle"]

pos4 = load("bake_bucket_pos")
nor4 = load("bake_bucket_nor")
facts4 = load("bake_bucket_facts")
ao4 = load("bake_bucket_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 1.4) * 0.3, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.5) * 2.2 + ndi.gaussian_filter(convex, 4.0) * 2.4, 0, 1)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


big = field(noise(pts, 0.28, 1, 3))
mid = field(noise(pts, 1.1, 2, 4))
fine = field(noise(pts, 4.5, 3, 3))
micro = field(noise(pts, 15.0, 4, 2))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
radius = np.hypot(X, Y)
theta = np.arctan2(Y, X)
# Runs around the bucket and up it, so strokes can lie around the body whatever the UVs do.
arc = theta * radius
around = np.stack((np.cos(theta) * radius, np.sin(theta) * radius, Z), -1)

vinyl = finish == VINYL
brass = finish == BRASS
steel = finish == STEEL
ice = finish == ICE
water = finish == WATER

# The crest, in inches on the wall: a ringed monogram above the hotel's name.
SCALE = 64
CW, CH = int(8.0 * SCALE), int(7.4 * SCALE)
crest_img = Image.new("L", (CW, CH), 0)
d = ImageDraw.Draw(crest_img)
serif = r"C:\Windows\Fonts\georgiab.ttf"
cx, cy = CW // 2, int(2.45 * SCALE)
outer = int(2.1 * SCALE)
d.ellipse((cx - outer, cy - outer, cx + outer, cy + outer), outline=255, width=int(0.11 * SCALE))
inner = int(1.84 * SCALE)
d.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), outline=255, width=int(0.04 * SCALE))
font = ImageFont.truetype(serif, int(2.25 * SCALE))
bb = d.textbbox((0, 0), "IH", font=font)
d.text((cx - (bb[2] - bb[0]) // 2 - bb[0], cy - (bb[3] - bb[1]) // 2 - bb[1]), "IH", 255, font=font)
font = ImageFont.truetype(serif, int(0.68 * SCALE))
for line, row in (("INNOCENT", 5.0), ("HOTEL", 5.95)):
    # Letter by letter, opened up the way foil stamps are.
    widths = [d.textlength(ch, font=font) for ch in line]
    gap = 0.11 * SCALE
    x = cx - (sum(widths) + gap * (len(line) - 1)) / 2
    for ch, w in zip(line, widths):
        d.text((x, int(row * SCALE)), ch, 255, font=font)
        x += w + gap
crest_map = np.asarray(crest_img, np.float32) / 255.0
crest_map = ndi.gaussian_filter(crest_map, 0.6)


def stamp(x_sign):
    """The crest at the wall's front (+X) or back (-X): viewed from outside, right is +Y on the front, -Y on the back."""
    th = np.arctan2(Y * x_sign, X * x_sign)
    s = th * np.maximum(radius, 1e-3)
    uu = (s + 4.0) * SCALE
    vv = (9.95 - Z) * SCALE
    out = ndi.map_coordinates(crest_map, (vv, uu), order=1, mode="constant", cval=0.0)
    return np.where((np.abs(th) < 1.0) & vinyl, out, 0.0).astype(np.float32)


crest = np.maximum(stamp(1), stamp(-1))
crest_edge = np.clip(ndi.gaussian_filter(crest, 1.6) - crest, 0, 1)

# Pebbled leatherette: fine cells, soft, with long creases where the wrap has flexed.
pebble_a = field(noise(pts, 6.0, 21, 2))
pebble = 1 - np.abs(pebble_a - 0.5) * 2.0
pebble = smooth(0.2, 0.92, pebble)
crease = smooth(0.82, 0.97, 1 - np.abs(field(noise(np.stack((arc[cover] * 0.3, Z[cover] * 0.09, np.zeros(cover.sum(), np.float32)), -1), 1.0, 22, 3)) - 0.5) * 2.0)

# Wear: short fine scuffs in patches, never wide flat bands. Heaviest round the base and by the handles.
low = smooth(3.4, 1.15, Z)
upper = smooth(10.2, 11.5, Z)
hand = smooth(3.1, 1.1, np.hypot(X, np.abs(Y) - 6.2) + np.abs(Z - (HANDLE_Z - 1.4)) * 0.5)
strokes = field(noise(np.stack((arc[cover] * 1.1, Z[cover] * 11.0, np.zeros(cover.sum(), np.float32)), -1), 1.0, 23, 3))
patches = smooth(0.38, 0.6, big + (mid - 0.5) * 0.5 + low * 0.3 + hand * 0.3)
scuff = smooth(0.5, 0.64, strokes) * patches
rub = smooth(0.44, 0.78, edge * 0.8 + (fine - 0.5) * 0.45 + (mid - 0.5) * 0.25 + low * 0.1)
through = smooth(0.7, 0.82, strokes * 0.4 + mid * 0.2 + fine * 0.25 + low * 0.34 + edge * 0.2)

# Stitching along both pipings, and a lapped seam down the wall under the -Y handle.
stitch = np.zeros((H, W), np.float32)
for zs in (1.7, 11.17):
    band = smooth(0.042, 0.018, np.abs(Z - zs))
    stitch = np.maximum(stitch, band * smooth(-0.12, 0.34, np.sin(arc * 2 * np.pi / 0.3)))
seam_s = (theta + np.pi / 2) * radius
seam_groove = smooth(0.05, 0.015, np.abs(seam_s)) * (Y < 0) * (Z > 1.5) * (Z < 11.2)
for off in (-0.2, 0.2):
    band = smooth(0.038, 0.014, np.abs(seam_s - off)) * (Y < 0) * (Z > 1.6) * (Z < 11.1)
    stitch = np.maximum(stitch, band * smooth(-0.12, 0.34, np.sin(Z * 2 * np.pi / 0.3)))

v_base = rgb(27, 26, 27) * (0.82 + 0.3 * big[..., None]) * (0.9 + 0.16 * pebble[..., None])
v_color = mix(v_base, rgb(84, 80, 76), scuff * 0.55)
v_color = mix(v_color, rgb(72, 68, 64), rub * 0.7)
v_color = mix(v_color, rgb(92, 80, 66), through * 0.85)
v_color = mix(v_color, rgb(106, 96, 80), stitch * 0.9)
v_color = v_color * (1 - seam_groove[..., None] * 0.65)
foil_keep = smooth(0.2, 0.42, fine * 0.5 + mid * 0.3 + (1 - scuff) * 0.32)
foil = crest * foil_keep
gold = mix(rgb(225, 178, 84), rgb(250, 215, 135), smooth(0.35, 0.75, mid))
v_color = mix(v_color, gold * (0.82 + 0.3 * fine[..., None]), foil)
v_rough = 0.42 + 0.14 * pebble + 0.1 * mid + scuff * 0.14 + rub * 0.14 + through * 0.16
v_rough = v_rough * (1 - stitch) + 0.8 * stitch
v_rough = v_rough * (1 - foil) + (0.3 + 0.16 * fine) * foil
v_metal = foil * 0.4
v_height = 0.011 * pebble + 0.002 * (micro - 0.5) - 0.012 * crease * smooth(0.5, 0.8, mid) - 0.012 * crest + 0.01 * stitch - 0.02 * seam_groove - through * 0.004

# Brass: an old lacquer gone brown in the recesses, bare and bright on what's rubbed.
b_touch = smooth(0.38, 0.72, edge * 0.82 + (mid - 0.5) * 0.55 + (fine - 0.5) * 0.4 + smooth(12.4, 13.05, Z) * 0.2)
b_color = mix(rgb(140, 105, 54) * (0.8 + 0.4 * big[..., None]), rgb(232, 190, 110), b_touch)
b_tarnish = smooth(0.42, 0.82, crevice * 0.75 + (big - 0.5) * 0.6 + (fine - 0.5) * 0.25)
b_color = mix(b_color, rgb(58, 42, 24), b_tarnish * 0.72)
b_green = smooth(0.72, 0.9, field(noise(pts, 2.4, 12, 3)) + crevice * 0.32)
b_color = mix(b_color, rgb(76, 92, 72), b_green * 0.36)
b_rough = 0.34 + 0.2 * (1 - b_touch) + 0.1 * fine + 0.2 * b_tarnish + 0.14 * b_green
b_metal = np.clip(0.45 + 0.12 * b_touch - 0.18 * b_tarnish - 0.25 * b_green, 0, 1)
b_height = 0.0016 * (micro - 0.5) + 0.0012 * (fine - 0.5)

# The liner: brushed round its circumference, with a tide line a little above the water.
brush = field(noise(np.stack((arc[cover] * 0.08, Z[cover] * 26.0, np.zeros(cover.sum(), np.float32)), -1), 1.0, 24, 2))
tide = smooth(0.16, 0.0, np.abs(Z - (WATER_Z + 0.55 + (big - 0.5) * 0.3))) * steel
wet = smooth(WATER_Z + 0.75, WATER_Z + 0.1, Z)
s_color = rgb(168, 170, 168) * (0.8 + 0.3 * brush[..., None]) * (0.9 + 0.16 * mid[..., None])
s_color = mix(s_color, rgb(108, 102, 90), tide * 0.7)
s_color = mix(s_color, s_color * 0.72, wet)
s_rough = 0.3 + 0.2 * brush + 0.08 * fine - wet * 0.12 + tide * 0.26
s_metal = 0.45 * (1 - tide * 0.5)
s_height = 0.0012 * (brush - 0.5)

# Ice: clear at its faces, cloudy at its heart, bright along the melted edges.
cloud = field(noise(pts, 0.9, 25, 3))
frost = field(noise(pts, 7.0, 26, 2))
cubes = np.array([c for c, _ in facts["cubes"]], np.float32)
sizes = np.array([s for _, s in facts["cubes"]], np.float32)
near_d, near_i = cKDTree(cubes).query(pts, k=1, workers=1)
heart = field(smooth(0.8, 0.48, near_d / sizes[near_i]))
i_tone = np.clip(0.14 + 0.5 * heart * (0.72 + 0.56 * cloud) + 0.55 * edge + (frost - 0.5) * 0.16 + (part - 0.5) * 0.1, 0, 1)
i_color = mix(rgb(112, 152, 172), rgb(236, 248, 253), i_tone)
i_rough = 0.05 + 0.08 * frost + 0.07 * heart
i_height = 0.004 * (cloud - 0.5) + 0.0012 * (frost - 0.5)

w_color = rgb(22, 34, 38) * (0.86 + 0.26 * big[..., None])

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)
for mask, c, r, m, h in (
    (vinyl, v_color, v_rough, v_metal, v_height),
    (brass, b_color, b_rough, b_metal, b_height),
    (steel, s_color, s_rough, s_metal, s_height),
    (ice, i_color, i_rough, 0.0, i_height),
    (water, w_color, 0.07 + 0.04 * big, 0.0, 0.0012 * (big - 0.5)),
):
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, r, rough)
    metal = np.where(mask, m, metal)
    height = np.where(mask, h, height)

color = color * (0.7 + 0.3 * ao[..., None])
solid = ndi.binary_erosion(cover, iterations=1)
height = fill_from(solid, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(solid, np.clip(color, 0, 1), np.clip(rough, 0.05, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("bucket painted", "px/in %.1f" % density, flush=True)
