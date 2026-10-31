"""Paint the IBC tote's maps from its bakes: python paint_tote.py <work dir> <materials dir>

Milky HDPE gone a little yellow, with the liquid's level showing through it, algae low down where it has stood in the sun, a printed scale and a sprayed stock number; galvanised tube with
its spangle, white rust and rust at the crossings and feet; black plastic fittings and a red valve lever. Wear is worked out in 3D. Lettering is generic.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import FONT, OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

GALV, ZINC, PLATE, TANK, DARK, LEVER = 1, 3, 7, 9, 10, 11

pos4 = load("bake_it_pos")
nor4 = load("bake_it_nor")
facts4 = load("bake_it_facts")
ao4 = load("bake_it_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
density = json.load(open(os.path.join(WORK, "ibc_tote.json")))["density"]
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
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
convex = np.clip((curve - 2.4) * 0.4, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 2.0) * 2.2 + ndi.gaussian_filter(convex, 5.0) * 2.6, 0, 1)
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


big = field(noise(pts, 0.09, 1, 3))
mid = field(noise(pts, 0.5, 2, 4))
fine = field(noise(pts, 2.6, 3, 3))
micro = field(noise(pts, 10.0, 4, 2))
streak = field(noise(pts * np.array((3.6, 3.6, 0.14), np.float32), 0.3, 6, 4))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NX, NY, NZ = nor[..., 0], nor[..., 1], nor[..., 2]
RAD = np.hypot(X, Y)

tank = finish == TANK
galv = finish == GALV
zinc = finish == ZINC
dark = finish == DARK
lever = finish == LEVER
plate = finish == PLATE
wall = tank & (np.abs(NZ) < 0.55)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

# ---- The tank. ----
# The liquid shows through the wall, up to a level that wavers a little with the moulding's thickness.
level = 21.5 + (field(noise(pts, 0.35, 21, 3)) - 0.5) * 0.25
below = smooth(level + 0.14, level - 0.14, Z) * wall
meniscus = np.exp(-(((Z - level) / 0.2) ** 2)) * wall
milky = mix(flat((208, 204, 186)), flat((184, 178, 152)), smooth(0.25, 0.8, big * 0.6 + mid * 0.4))
t_color = mix(milky, milky * np.array((0.56, 0.62, 0.6), np.float32), below * (0.86 + 0.2 * (mid - 0.5)))
t_color = mix(t_color, t_color * 0.62, meniscus * 0.8)
# Algae, where it has stood in the sun: green in the lower walls, thickest in the corners, not on top.
algae_map = smooth(0.46, 0.72, field(noise(pts, 0.22, 22, 4)) + smooth(28.0, 8.0, Z) * 0.2 + np.clip((RAD - 24.0) * 0.04, 0, 0.1))
algae = algae_map * wall * smooth(32.0, 16.0, Z)
t_color = mix(t_color, flat((86, 104, 60)) * (0.8 + 0.4 * fine[..., None]), algae * 0.56)
# Scuffed by the cage it has rubbed against, a bright line behind every bar, and streaked down from the cap.
scuff = smooth(0.62, 0.74, field(noise(pts * np.array((3.0, 3.0, 0.3), np.float32), 0.7, 23, 4)) + (mid - 0.5) * 0.25)
t_color = mix(t_color, flat((214, 212, 204)), scuff * 0.3)
runs = smooth(0.54, 0.78, streak + crevice * 0.2) * smooth(0.3, 0.62, mid)
t_color = mix(t_color, t_color * np.array((0.72, 0.66, 0.56), np.float32), runs * 0.5)
# Spilled from the filler, long ago, a pale amber on top and over the shoulder.
spill = smooth(8.5, 3.0, RAD + (mid - 0.5) * 7.0) * tank
t_color = mix(t_color, t_color * np.array((0.8, 0.68, 0.44), np.float32), spill * 0.66)

# A printed scale up one corner of the valve end, read from the valve.
art = Image.new("L", (360, 1100), 0)
d = ImageDraw.Draw(art)
font = ImageFont.truetype(FONT, 72)
for k, litres in enumerate((200, 400, 600, 800, 1000)):
    y = 1100 - int((k + 1) * 200)
    d.rectangle((0, y - 3, 90, y + 3), fill=255)
    d.rectangle((0, y + 97, 44, y + 101), fill=255)
    d.text((104, y - 44), str(litres), 255, font=font)
d.rectangle((0, 0, 6, 1100), fill=255)
scale = np.asarray(art, np.float32) / 255.0
# The cage's bars stand at x = +-3.83 and +-11.49, so the printing keeps to the gaps between them.
marks = place(scale, X, Z, 15.3, 26.0, 6.0, 30.0) * tank * (NY < -0.7)
# A stock number and warnings, sprayed through a stencil.
long_side = tank & (NX < -0.7)
sprayed = place(stencil_image(["T-14"], (900, 480)), -Y, Z, -6.5, 27.8, 15.0, 8.0) * long_side
back_side = tank & (NX > 0.7)
sprayed = np.maximum(sprayed, place(stencil_image(["T-14"], (900, 480)), Y, Z, 6.0, 27.8, 15.0, 8.0) * back_side)
sprayed = np.maximum(sprayed, place(stencil_image(["INDUSTRIAL USE ONLY", "NOT FOR DRINKING WATER"], (1400, 300), bridge=False), -Y, Z, -6.5, 17.8, 22.0, 4.8) * long_side)
sprayed = np.maximum(sprayed, place(stencil_image(["1000 L"], (800, 320), bridge=False), X, Z, 0.0, 29.3, 6.8, 2.8) * tank * (NY < -0.7))
sprayed = sprayed * smooth(0.12, 0.3, field(noise(pts, 3.3, 10, 3)) + (big - 0.5) * 0.15)
t_color = mix(t_color, flat((22, 22, 22)), np.clip(marks * 0.82 + sprayed * 0.92, 0, 1))
color = np.where(tank[..., None], t_color, color)
rough = np.where(tank, 0.44 + 0.12 * mid + 0.06 * fine + scuff * 0.12 + algae * 0.3 + runs * 0.08, rough)
metal = np.where(tank, 0.0, metal)
pebble = 0.003 * (micro - 0.5) + 0.0024 * (fine - 0.5)
height = np.where(tank, pebble - scuff * 0.002 + algae * 0.003 * (fine - 0.3) + 0.02 * (mid - 0.5) * wall, height)

# ---- Galvanised: spangled, chalked with white rust, and rusting at its crossings and low down. ----
seeds = np.random.default_rng(3).uniform((-25, -25, 0), (25, 25, 50), (30000, 3))
values = np.random.default_rng(4).random(30000).astype(np.float32)
_, near = cKDTree(seeds).query(pos[galv], k=1, workers=1)
spangle = np.zeros((H, W), np.float32)
spangle[galv] = values[near]
g_color = flat((176, 178, 176)) * (0.62 + 0.3 * spangle[..., None] + 0.26 * (big[..., None] - 0.5))
g_white = smooth(0.56, 0.78, streak + crevice * 0.24)
g_color = mix(g_color, flat((186, 184, 174)) * 0.82, g_white * 0.6)
# Zinc holds out for years: rust only where it's been knocked through, at the crossings and down at the feet.
g_rust = smooth(0.64, 0.84, field(noise(pts, 1.8, 13, 3)) + crevice * 0.32 + smooth(9.0, 0.0, Z) * 0.2 + edge * 0.04)
g_runs = smooth(0.62, 0.84, streak + crevice * 0.26) * smooth(0.44, 0.72, mid)
rust_c = mix(flat((58, 32, 20)), flat((122, 70, 38)), smooth(0.35, 0.8, field(noise(pts, 3.1, 8, 3))))
g_color = mix(g_color, rust_c, np.clip(g_rust * 0.82 + g_runs * 0.2, 0, 1))
g_bright = smooth(0.6, 0.78, edge * 0.8 + (fine - 0.5) * 0.7)
g_color = mix(g_color, flat((180, 182, 180)), g_bright * (1 - g_rust) * 0.45)
color = np.where(galv[..., None], g_color, color)
rough = np.where(galv, (0.34 + 0.26 * spangle + 0.16 * mid + g_white * 0.28) * (1 - g_rust) + 0.86 * g_rust, rough)
metal = np.where(galv, (1 - g_white * 0.65) * (1 - g_rust), metal)
height = np.where(galv, 0.0022 * (spangle - 0.5) + 0.0012 * (micro - 0.5) + g_rust * 0.008 * (fine - 0.3), height)

# Plated bolts and the tether.
color = np.where(zinc[..., None], flat((176, 174, 164)) * (0.52 + 0.3 * mid[..., None]), color)
rough = np.where(zinc, 0.34 + 0.24 * fine, rough)
metal = np.where(zinc, 1.0, metal)

# Black plastic fittings, scuffed grey at their corners; the cap's ribs are in the normal map.
d_scuff = smooth(0.52, 0.7, edge * 0.8 + (fine - 0.5) * 0.7)
d_color = mix(flat((30, 30, 30)) * (0.74 + 0.44 * mid[..., None]), flat((88, 88, 86)), d_scuff * 0.7)
color = np.where(dark[..., None], d_color, color)
rough = np.where(dark, 0.56 + 0.16 * fine + d_scuff * 0.1, rough)
metal = np.where(dark, 0.0, metal)
theta = np.arctan2(Y, X)
cap_ribs = (0.5 + 0.5 * np.sin(theta * 60)) * (Z > 44.3) * (Z < 45.2) * (RAD > 5.3)
height = np.where(dark, cap_ribs * 0.04 + 0.002 * (micro - 0.5), height)

# The valve lever, red, chipped.
l_chip = smooth(0.5, 0.58, edge * 0.5 + (fine - 0.5) * 0.9 + (mid - 0.5) * 0.5 + 0.34)
color = np.where(lever[..., None], mix(flat((166, 30, 22)) * (0.82 + 0.3 * mid[..., None]), flat((172, 172, 166)), l_chip), color)
rough = np.where(lever, 0.38 + 0.14 * fine + l_chip * 0.1, rough)
metal = np.where(lever, l_chip, metal)
height = np.where(lever, 0.003 * (micro - 0.5) + (1 - l_chip) * 0.006, height)

# The data plate, stamped, read from the -X side.
stamp = place(stencil_image(["IBC 1000 L", "TARE 58 KG  MAX 1.6 T", "LOT 04417  03-24"], (1000, 620), bridge=False), -Y, Z, -7.7, 42.1, 6.0, 3.8) * plate
p_color = flat((176, 176, 170)) * (0.82 + 0.3 * mid[..., None])
p_color = mix(p_color, np.broadcast_to(np.array((0.015, 0.015, 0.016), np.float32), (H, W, 3)), stamp * 0.85)
color = np.where(plate[..., None], p_color, color)
rough = np.where(plate, 0.42 + 0.22 * fine + stamp * 0.3, rough)
metal = np.where(plate, 1 - stamp * 0.85, metal)
height = np.where(plate, stamp * 0.012 + 0.001 * (micro - 0.5), height)

# Yard dirt: dust on what faces up, grime and splash climbing from the ground.
upward = np.clip(NZ, 0, 1)
settled = smooth(0.42, 0.92, upward * 0.84 + (big - 0.5) * 0.36 + crevice * 0.2)
lowness = np.clip((14.0 - Z) / 14.0, 0, 1) ** 1.5
splash = lowness * smooth(0.46, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 17, 4)) + lowness * 0.14)
dirt = np.clip(settled * 0.34 + splash * 0.64 + crevice * 0.26, 0, 0.88) * (~plate) * (~lever)
color = mix(color, flat((84, 76, 62)) * (0.75 + 0.5 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.92 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.004 * (fine - 0.35)

color = color * (0.74 + 0.26 * ao[..., None])
# Fill the gutters from every covered texel: eroding first would lose bevel strips a pixel or two wide.
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "it_tote_color.png"), color)
save_gray(os.path.join(OUT, "it_tote_rough.png"), rough)
save_gray(os.path.join(OUT, "it_tote_metal.png"), metal)
save_gray(os.path.join(OUT, "it_tote_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "it_tote_normal.png"), normal)
print("ibc tote painted", flush=True)
