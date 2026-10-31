"""Paint the cooler's maps from its bakes: python paint_cooler.py <work dir> <materials dir>

Moulded plastic left out in a trailer park for years: the blue chalky and faded by sun, its corners scuffed pale, mud up its sides.
The lid has yellowed, with the picture's marker lettering inside it. Inside, old meltwater with a tide mark up the liner, and cans
in it. All worked out in 3D, so it runs across UV seams.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

BODY, LID, WATER, CAN, STEEL, RUBBER, ICE = range(7)
NAME = "cooler"
facts = json.load(open(os.path.join(WORK, "cooler.json")))
density = facts["density"]
HINGE_Y, HINGE_Z = facts["hinge"]
WATER_Z = facts["water_z"]

pos4 = load("bake_cooler_pos")
nor4 = load("bake_cooler_nor")
facts4 = load("bake_cooler_facts")
ao4 = load("bake_cooler_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
print("coverage %.2f" % cover.mean(), flush=True)
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 1.2) * 0.42, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.6) * 2.4 + ndi.gaussian_filter(convex, 4.0) * 3.0, 0, 1)
del curve, dn, dp
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


big = field(noise(pts, 0.1, 1, 3))
mid = field(noise(pts, 0.55, 2, 4))
fine = field(noise(pts, 2.7, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
print("noise done", flush=True)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = 0.0016 * (micro - 0.5)

upward = np.clip(nor[..., 2], 0, 1)
floor_near = smooth(6.5, 0.0, Z + (mid - 0.5) * 3.0)
streak = field(noise(pts * np.array((4.0, 4.0, 0.14), np.float32), 0.3, 6, 4))
# Scratches run along what's been dragged and carried: mostly the length of it.
scrape = smooth(0.7, 0.8, field(noise(pts * np.array((0.45, 9.0, 9.0), np.float32), 1.0, 7, 3))) * smooth(0.4, 0.7, big + (mid - 0.5))

# ---- The body: moulded blue, chalky with sun, scuffed pale at the corners -------------------------------------------
is_body = finish == BODY
liner = is_body & (np.abs(X) < 14.75) & (np.abs(Y) < 7.25) & (Z > 2.0) & (Z < 15.95)
blue = mix(flat((40, 92, 150)), flat((30, 70, 116)), smooth(0.3, 0.7, mid * 0.6 + big * 0.4))
chalk = smooth(0.34, 0.74, big * 0.6 + mid * 0.25 + upward * 0.4 + (Z / 16.0) * 0.14)
b_col = mix(blue, flat((122, 148, 168)), chalk * 0.56)
b_col = b_col * (0.94 + 0.12 * fine[..., None])
b_col = mix(b_col, flat((150, 166, 176)), np.clip(edge * smooth(0.28, 0.66, mid * 0.6 + fine * 0.4) * 0.8 + scrape * 0.34, 0, 1))
runs = smooth(0.54, 0.78, streak) * smooth(0.3, 0.7, mid)
b_col = mix(b_col, flat((54, 50, 42)), runs * 0.32)
b_rough = 0.5 + 0.2 * chalk + 0.1 * fine + scrape * 0.14
b_height = -scrape * 0.006 + 0.002 * (fine - 0.5)

# A moulded mark on the front, the same colour as the plastic. Invented wording. Seen from +y, +x is on the left.
mark = sample_image(ndi.gaussian_filter(stencil_image(["100 QT"], (420, 110), bridge=False), 1.0), np.clip((3.4 - X) / 6.8, -1, 2), np.clip((Z - 7.2) / 1.8, -1, 2)) * (nor[..., 1] > 0.6)
b_height = b_height + mark * 0.02
b_col = b_col * (1 - mark[..., None] * 0.16)

# The liner: off-white, with a tide mark for every level the water has stood at.
wobble = (mid - 0.5) * 0.5
tide = np.maximum.reduce([smooth(0.16, 0.0, np.abs(Z - zz + wobble)) * s for zz, s in ((WATER_Z + 0.25, 1.0), (WATER_Z + 1.5, 0.7), (WATER_Z + 3.2, 0.45))])
l_col = flat((186, 182, 166)) * (0.82 + 0.26 * mid[..., None])
stain = smooth(WATER_Z + 5.0, WATER_Z, Z) * smooth(0.3, 0.7, mid * 0.6 + big * 0.4)
l_col = mix(l_col, flat((96, 84, 60)), stain * 0.55)
l_col = mix(l_col, flat((54, 44, 30)), tide[..., None] * 0.7)
spots = smooth(0.68, 0.76, field(noise(pts, 11.0, 8, 2))) * smooth(0.5, 0.74, mid)
l_col = mix(l_col, flat((44, 46, 40)), spots[..., None] * 0.42)
b_col = np.where(liner[..., None], l_col, b_col)
b_rough = np.where(liner, 0.55 + 0.25 * stain, b_rough)
color = np.where(is_body[..., None], b_col, color)
rough = np.where(is_body, b_rough, rough)
height = np.where(is_body, height + b_height, height)

# ---- The lid: white gone yellow, with the marker lettering on its underside -------------------------------------------
is_lid = finish == LID
ang = math.radians(facts["lid_deg"])
dy, dz = Y - HINGE_Y, Z - HINGE_Z
closed_y = dy * math.cos(ang) + dz * math.sin(ang) + HINGE_Y
closed_z = -dy * math.sin(ang) + dz * math.cos(ang) + HINGE_Z
closed_nz = -nor[..., 1] * math.sin(ang) + nor[..., 2] * math.cos(ang)
under_lid = is_lid & (closed_nz < -0.7) & (closed_z < 16.7)
top_lid = is_lid & (closed_nz > 0.7)
l_white = flat((214, 214, 208)) * (0.84 + 0.2 * mid[..., None])
yellow = smooth(0.3, 0.76, big * 0.55 + mid * 0.45)
l_white = mix(l_white, flat((186, 170, 128)), yellow * 0.5)
l_white = mix(l_white, flat((96, 88, 70)), np.clip(smooth(0.5, 0.78, streak) * 0.35 + crevice * 0.4, 0, 0.7))
l_white = mix(l_white, flat((226, 226, 218)), np.clip(edge * smooth(0.3, 0.66, mid) * 0.5, 0, 1))
mildew = smooth(0.66, 0.76, field(noise(pts, 11.0, 9, 2))) * smooth(0.48, 0.74, mid * 0.5 + (np.abs(X) / 15.0) * 0.4)
l_white = mix(l_white, flat((52, 54, 46)), (mildew * under_lid * 0.38)[..., None])

# The same marker as the old lid: its dark pixels, cropped from the atlas by old_cooler.py. A player reads it from +y, so +x is their left.
art = np.asarray(Image.open(os.path.join(WORK, "lid_lettering.png")).convert("L"), np.float32) / 255.0
# The crop has the old lid's grey blotches in it too, which are much paler than the strokes.
ink = smooth(0.34, 0.16, art)
ink_mask = sample_image(ink, np.clip((-X + 13.4) / 26.8, -1, 2), np.clip((closed_y + 6.5) / 13.0, -1, 2)) * under_lid
ink_mask = ink_mask * smooth(0.14, 0.34, field(noise(pts, 3.0, 10, 3)) + big * 0.2)
l_white = mix(l_white, flat((16, 16, 18)), ink_mask[..., None] * 0.94)

# Moulded ribs across its top, to stiffen it. They show from behind.
ribs = 0.5 + 0.5 * np.cos(np.clip(X, -14.0, 14.0) * 2 * math.pi / 3.5)
l_height = (top_lid * smooth(0.25, 0.75, ribs) * 0.05) - scrape * 0.004
color = np.where(is_lid[..., None], l_white, color)
rough = np.where(is_lid, 0.52 + 0.2 * yellow + 0.08 * fine - ink_mask * 0.12, rough)
height = np.where(is_lid, height + l_height, height)

# ---- What's in it ---------------------------------------------------------------------------------------------------
is_water = finish == WATER
scum = smooth(0.44, 0.7, mid * 0.55 + big * 0.2 + np.maximum(np.abs(X) / 14.2, np.abs(Y) / 6.7) ** 6 * 0.5)
w_col = mix(flat((30, 32, 18)), flat((64, 62, 40)), scum)
flecks = smooth(0.66, 0.72, field(noise(pts, 6.0, 11, 2)))
w_col = mix(w_col, flat((26, 20, 12)), flecks[..., None] * 0.7)
color = np.where(is_water[..., None], w_col, color)
rough = np.where(is_water, 0.1 + scum * 0.55, rough)
height = np.where(is_water, 0.006 * (field(noise(pts, 0.8, 12, 2)) - 0.5), height)

is_ice = finish == ICE
color = np.where(is_ice[..., None], flat((176, 190, 192)) * (0.8 + 0.3 * fine[..., None]), color)
rough = np.where(is_ice, 0.18 + 0.2 * fine, rough)

# Cans, red and bare aluminium, each with a printed band found from its own axis.
is_can = finish == CAN
c_col = flat((146, 146, 142)) * (0.8 + 0.3 * mid[..., None])
c_metal = np.ones((H, W), np.float32)
c_rough = 0.3 + 0.2 * fine
for can in facts["cans"]:
    here = is_can & (np.abs(part - can["rand"]) < 1e-3)
    if not here.any():
        continue
    axis = np.array(can["axis"], np.float32)
    axis /= np.linalg.norm(axis)
    along = ((pos - np.array(can["at"], np.float32)) * axis).sum(-1)
    printed = (along > 0.35) & (along < 4.25)
    band = smooth(0.1, 0.0, np.abs(along - 2.3) - 0.55)
    if can["kind"] == "red":
        ink_c = mix(flat((150, 30, 26)), flat((210, 206, 196)), band)
    else:
        ink_c = mix(flat((176, 178, 176)), flat((40, 62, 104)), band)
    scuff = smooth(0.56, 0.7, fine * 0.7 + mid * 0.3)
    ink_c = mix(ink_c, flat((168, 168, 164)), scuff * 0.7)
    c_col = np.where((here & printed)[..., None], ink_c, c_col)
    c_metal = np.where(here & printed, scuff * 0.9 + 0.1, c_metal)
    c_rough = np.where(here & printed, 0.34 + 0.1 * fine, c_rough)
color = np.where(is_can[..., None], c_col, color)
rough = np.where(is_can, c_rough, rough)
metal = np.where(is_can, c_metal, metal)

# ---- Hardware --------------------------------------------------------------------------------------------------------
is_rubber = finish == RUBBER
color = np.where(is_rubber[..., None], flat((30, 30, 29)) * (0.75 + 0.5 * fine[..., None]), color)
rough = np.where(is_rubber, 0.72 + 0.16 * fine, rough)
is_steel = finish == STEEL
rust = smooth(0.46, 0.7, mid * 0.6 + fine * 0.4)
color = np.where(is_steel[..., None], mix(flat((142, 142, 138)), flat((84, 50, 30)), rust), color)
rough = np.where(is_steel, 0.42 + 0.4 * rust, rough)
metal = np.where(is_steel, 1 - rust, metal)

# ---- Mud and dust, over the outside only --------------------------------------------------------------------------------
outside = ~(liner | is_water | is_ice | is_can | under_lid)
mud = smooth(0.46, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 14, 4)) + floor_near * 0.3) * floor_near
speck = floor_near * smooth(0.64, 0.72, field(noise(pts, 7.5, 15, 2)))
settled = smooth(0.42, 0.9, upward * 0.84 + (big - 0.5) * 0.3 + crevice * 0.26)
dirt = np.clip(mud * 0.85 + speck * 0.5 + settled * 0.46, 0, 0.92) * outside
color = mix(color, flat((84, 70, 50)) * (0.75 + 0.5 * fine[..., None]), dirt[..., None])
rough = rough * (1 - dirt) + 0.92 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.006 * (fine - 0.35)

color = color * (0.72 + 0.28 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("cooler painted", flush=True)
