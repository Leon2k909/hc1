"""Paint the rifle suppressor's maps from its bakes: python paint_suppressor.py <work dir> <output dir>

The story is heat. It starts as a dark ceramic coat over steel and is sound behind, then toward the muzzle the coat chalks and
burns back, the cap's bare steel takes on temper colours, and soot gathers in the flutes and round the bore. All of it is
worked out from each texel's 3D position, so it crosses UV seams. Lettering is invented and plainly descriptive. No brands.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

COAT, STEEL, BARE, LABEL = range(4)

pos4 = load("bake_rs_pos")
nor4 = load("bake_rs_nor")
facts4 = load("bake_rs_facts")
ao4 = load("bake_rs_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "suppressor.json")))
density = meta["density"]
pos = (pos4[..., :3] - 0.5) * 40.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
ao = np.clip(fill_from(cover, ao4[..., 0])[0], 0, 1)
del pos4, nor4, facts4, ao4
print("coverage %.2f, %.0f px/in" % (cover.mean(), density), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-7)
# Thin islands would lose everything to a wide erosion here, so only the outermost texel goes.
curve[~ndi.binary_erosion(cover, iterations=1)] = 0
convex = np.clip((curve - 4.0) * 0.12, 0, 1)
# Tight, because the parts are small: a wide edge turns a whole grip bar into "edge" and wears it all to bright metal.
edge = np.clip(ndi.gaussian_filter(convex, 0.8) * 1.4 + ndi.gaussian_filter(convex, 2.2) * 0.9, 0, 1)
del curve, dn, dp
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def solid(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


big = field(noise(pts, 0.5, 1, 3))
mid = field(noise(pts, 2.2, 2, 4))
fine = field(noise(pts, 9.0, 3, 3))
micro = field(noise(pts, 28.0, 4, 2))
tone = field(noise(pts, 4.5, 5, 3))
print("noise done", flush=True)
crevice = np.clip((1 - ao) * 1.5, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
radius = np.hypot(Y, Z)
theta = np.arctan2(Z, Y)
outer = np.clip((Y * nor[..., 1] + Z * nor[..., 2]) / np.maximum(radius, 1e-4), -1, 1)
# Heat climbs toward the muzzle, unevenly.
heat = smooth(2.6, 6.1, X + (big - 0.5) * 1.3 + (mid - 0.5) * 0.5)

# Bare steel, tempered by how hot it has been. Kept muted, as fired steel under soot is: straw, bronze, a dull violet, then the
# dark grey it ends at. A saturated blue here reads as a fantasy prop. The ramp is in linear colour.
ramp_at = np.array((0.0, 0.3, 0.5, 0.68, 0.84, 1.0), np.float32)
ramp = np.stack([srgb_to_linear(c) for c in ((158, 158, 154), (166, 150, 116), (134, 108, 84), (98, 84, 92), (74, 74, 82), (56, 56, 58))])
temper = np.clip(heat * 1.1 + (tone - 0.5) * 0.28, 0, 1)
tempered = np.stack([np.interp(temper, ramp_at, ramp[:, c]) for c in range(3)], -1).astype(np.float32)
tempered = tempered * (0.8 + 0.3 * fine[..., None])

# Long scratches, mostly lengthwise: drawn in UV, where every island's long side lies along U.
scratch_img = Image.new("L", (W, H), 0)
draw = ImageDraw.Draw(scratch_img)
rs = np.random.default_rng(11)
for _ in range(900):
    x, y = rs.uniform(0, W), rs.uniform(0, H)
    a = rs.normal(0, 0.14) + (math.pi if rs.random() < 0.5 else 0)
    n = rs.integers(10, 110)
    draw.line((x, y, x + math.cos(a) * n, y + math.sin(a) * n), fill=int(rs.uniform(60, 210)), width=1)
scratch = np.asarray(scratch_img, np.float32)[::-1] / 255.0
scratch = scratch * smooth(0.38, 0.62, big + (mid - 0.5) * 0.5)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)


def put(mask, c, r, m, h):
    global color, rough, metal, height
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, r, rough)
    metal = np.where(mask, m, metal)
    height = np.where(mask, h, height)


# ---- The ceramic coat on the can ----
coat = finish == COAT
# Small flecks on the flats, more on real edges. Big noise here makes blobs, so the weight is on the fine octaves.
chip = edge * smooth(0.3, 0.66, mid * 0.65 + fine * 0.35) * 1.05 + (mid - 0.5) * 0.2 + (big - 0.5) * 0.12 + (fine - 0.5) * 0.62 + (micro - 0.5) * 0.3 + heat * 0.05
bare = smooth(0.74, 0.76, chip)
c_color = solid((43, 44, 44)) * (0.84 + 0.3 * mid[..., None])
# Fired, the coat chalks to a dull grey-brown, and it's burnt thin at the hottest end.
chalk = heat * smooth(0.2, 0.62, mid * 0.55 + tone * 0.45)
c_color = mix(c_color, solid((116, 108, 96)) * (0.82 + 0.28 * fine[..., None]), chalk * 0.84)
crackle = smooth(0.54, 0.6, field(noise(pts, 16.0, 6, 2))) * smooth(0.5, 1.0, heat)
c_color = c_color * (1 - crackle[..., None] * 0.34)
c_color = mix(c_color, solid((150, 150, 146)), scratch[..., None] * 0.28)
# The flutes and grooves catch the soot.
soot = smooth(0.1, 0.8, crevice * 1.2 + (mid - 0.5) * 0.4) * smooth(2.8, 5.6, X)
c_color = mix(c_color, solid((13, 13, 13)), soot * 0.82)
c_color = mix(c_color, tempered, bare)
c_rough = 0.56 + 0.14 * mid + 0.06 * fine + chalk * 0.2 + soot * 0.12
c_rough = c_rough * (1 - bare) + (0.3 + 0.2 * fine) * bare
c_metal = np.maximum(bare, scratch * 0.3) * (1 - soot * 0.8)
c_height = 0.0024 * (micro - 0.5) + 0.0016 * (fine - 0.5) + (1 - bare) * 0.0045 - scratch * 0.002 - crackle * 0.0028
# A torque witness mark in red paint, across the joint from shoulder to can.
witness = smooth(0.034, 0.026, np.abs(np.angle(np.exp(1j * (theta - math.radians(58)))) * 0.78)) * (X > 0.96) * (X < 1.92) * (outer > 0.5)
witness = witness * smooth(0.2, 0.4, field(noise(pts, 8.0, 7, 2)) + 0.08)
# Etched lettering on the can's upper side, behind the grooves.
words = stencil_image(["PATTERN 6"], (900, 130), bridge=False)
# Seen from this side, reading right runs toward the rear, and up runs with the angle.
uu = (2.62 - X) / 1.06
vv = (np.angle(np.exp(1j * (theta - math.radians(34)))) * 0.78 + 0.075) / 0.15
etched = sample_image(words, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) * (outer > 0.5)
c_color = mix(c_color, solid((158, 158, 152)), etched * 0.9)
c_rough = c_rough + etched * 0.16
c_height = c_height - etched * 0.002
put(coat, c_color, c_rough, c_metal, c_height)

# ---- Phosphated steel: collar, shoulder, cap ----
steel_part = finish == STEEL
s_wear = smooth(0.5, 0.78, edge * 0.8 + (fine - 0.5) * 0.6 + (mid - 0.5) * 0.25)
s_color = solid((58, 58, 56)) * (0.8 + 0.34 * mid[..., None])
s_color = mix(s_color, solid((150, 150, 146)), scratch[..., None] * 0.3)
s_rough = 0.44 + 0.16 * mid + 0.08 * fine
s_height = 0.0022 * (micro - 0.5)
# A diamond knurl on the collar's grip band, its tops rubbed bright by hands.
band = (X > 0.12) & (X < 0.54) & (radius > 0.76)
pitch = 0.062
along = X / pitch
round_ = theta * 0.776 / pitch
a = np.abs(np.mod(along + round_, 1.0) - 0.5) * 2
b = np.abs(np.mod(along - round_, 1.0) - 0.5) * 2
knurl = np.minimum(a, b)
rubbed = smooth(0.55, 0.85, knurl) * smooth(0.25, 0.7, mid + 0.1)
s_height = s_height + band * knurl * 0.018
s_color = np.where(band[..., None], s_color * (0.5 + 0.7 * knurl[..., None]), s_color)
s_color = np.where(band[..., None], mix(s_color, solid((170, 170, 166)), rubbed * 0.5), s_color)
s_rough = np.where(band, s_rough - rubbed * 0.14, s_rough)
s_color = mix(s_color, tempered * 0.78, s_wear * 0.9)
s_rough = s_rough * (1 - s_wear) + (0.34 + 0.18 * fine) * s_wear
s_metal = 0.86 + 0.14 * s_wear
# The cap burns: temper colours through the phosphate, then soot right round the bore, in fans.
cap = X > 5.7
burn = cap * smooth(0.25, 0.75, heat + (tone - 0.5) * 0.4) * smooth(0.5, 0.64, field(noise(pts, 3.2, 8, 3)) + 0.1)
s_color = mix(s_color, tempered, burn * 0.5)
s_metal = np.maximum(s_metal, burn)
fans = 0.5 + 0.5 * np.sin(theta * 9 + (tone - 0.5) * 6)
face = (nor[..., 0] > 0.5) & cap
c_soot = np.where(face, smooth(0.86, 0.34, radius + (fans - 0.5) * 0.16 + (fine - 0.5) * 0.14), 0.0) + smooth(6.0, 6.5, X) * smooth(0.25, 0.7, tone * 0.6 + fine * 0.4) * 0.62
c_soot = np.clip(c_soot, 0, 1)
s_color = mix(s_color, solid((11, 11, 11)) * (0.8 + 0.4 * fine[..., None]), c_soot * 0.93)
s_rough = s_rough * (1 - c_soot) + 0.9 * c_soot
s_metal = s_metal * (1 - c_soot * 0.92)
s_height = s_height + c_soot * 0.002 * (fine - 0.3)
# Eight milled dimples round the face, where a pin wrench goes.
for k in range(8):
    a0 = 2 * math.pi * (k + 0.5) / 8
    d = np.hypot(Y - 0.6 * math.cos(a0), Z - 0.6 * math.sin(a0))
    pit = (d < 0.052) & face
    lip = (d < 0.068) & face
    s_color = np.where(pit[..., None], solid((6, 6, 6)), s_color)
    s_rough = np.where(pit, 0.9, s_rough)
    s_metal = np.where(pit, 0.0, s_metal)
    s_height = s_height - pit * 0.03 + (lip & ~pit) * 0.004
put(steel_part, s_color, s_rough, s_metal, s_height)
# The red witness mark crosses both finishes, so it goes on last.
red = witness * (coat | steel_part)
color = mix(color, solid((132, 44, 32)) * (0.82 + 0.28 * mid[..., None]), red * 0.9)
rough = rough * (1 - red) + 0.6 * red
metal = metal * (1 - red)

# ---- Machined bare steel: the socket, its threads and the detent ----
bare_part = finish == BARE
threads = bare_part & (X < 0.5) & (radius < 0.4)
d_color = solid((158, 158, 154)) * (0.72 + 0.34 * fine[..., None])
d_color = np.where(threads[..., None], d_color * (0.36 + 0.3 * mid[..., None]), d_color)
put(bare_part, d_color, 0.3 + 0.2 * fine + threads * 0.2, np.full((H, W), 0.96, np.float32), 0.001 * (micro - 0.5))
# Only the threads and the pin are bare. The socket's outside has the collar's phosphate, rubbed on its rim.
rear = bare_part & (radius > 0.4) & (X < 0.2)
r_color = mix(solid((60, 60, 58)) * (0.8 + 0.34 * mid[..., None]), tempered * 0.78, s_wear * 0.9)
put(rear, r_color, 0.44 + 0.16 * mid - s_wear * 0.1, np.full((H, W), 0.88, np.float32), 0.0022 * (micro - 0.5))
# The bore itself goes black a short way in.
bore = steel_part & (radius < 0.24) & (X < 6.52)
color = np.where(bore[..., None], solid((8, 8, 8)) * (0.75 + 0.5 * fine[..., None]), color)
rough = np.where(bore, 0.88, rough)
metal = np.where(bore, 0.0, metal)

# ---- The plate: aluminium, with its words etched and filled ----
label = finish == LABEL
plate_words = stencil_image(["LOT 4408", "HOT WHEN FIRED"], (680, 320), bridge=False)
# Seen from this side, reading right runs toward the muzzle, and up runs against the angle.
uu = (X - 1.76) / 0.7
vv = (0.17 - np.angle(np.exp(1j * (theta - math.pi))) * 0.795) / 0.34
stamp = sample_image(plate_words, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) * (outer > 0.6)
l_color = solid((146, 146, 140)) * (0.84 + 0.26 * mid[..., None])
l_color = mix(l_color, solid((14, 14, 15)), stamp * 0.92)
l_color = mix(l_color, l_color * 0.66, smooth(0.5, 1.0, crevice * 0.6 + (mid - 0.5)))
put(label, l_color, 0.42 + 0.2 * fine + stamp * 0.28, 1 - stamp * 0.88, stamp * -0.004 + 0.001 * (micro - 0.5))

# ---- Grime, kept in the corners: this is carried and fired, not left out ----
grime = smooth(0.25, 0.9, crevice) * smooth(0.25, 0.7, mid)
oil = smooth(0.6, 0.76, field(noise(pts, 1.1, 9, 3)))
dirt = np.clip(grime * 0.4, 0, 0.7) * (1 - c_soot * 0.8)
color = mix(color, solid((60, 56, 50)) * (0.75 + 0.5 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.86 * dirt
metal = metal * (1 - dirt)
rough = rough - oil * 0.08 * (1 - dirt)
height = height + dirt * 0.002 * (fine - 0.35)

color = color * (0.72 + 0.28 * ao[..., None])
# Fill the gutters from the covered texels, with no erosion: eroding a thin island away hands it another island's colours.
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.05, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "rs_can_color.png"), color)
save_gray(os.path.join(OUT, "rs_can_rough.png"), rough)
save_gray(os.path.join(OUT, "rs_can_metal.png"), metal)
save_gray(os.path.join(OUT, "rs_can_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "rs_can_normal.png"), normal)
print("suppressor painted", flush=True)
