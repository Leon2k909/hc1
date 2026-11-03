"""Paint the information stand's maps from its bakes: python paint_stand.py <work dir> <output dir>

An aquarium's visitor stand, looked after but used: blue-grey powder-coated steel, scuffed soft at shin height and on the floor plate's front where people stand, its
edges rubbed, its lip bright from hands. A rubber kick with shoe marks. Black glass with smudges and three printed buttons, and an etched steel plate with made-up lettering.
It's indoors and mopped, so there's little dirt and no weathering. Wear is worked out in 3D, and kept soft: a hard threshold on noise reads as dashes in the engine.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

COAT, ZINC, RUBBER, GLOSS, PLATE = 2, 3, 12, 13, 14
facts = json.load(open(os.path.join(WORK, "stand.json")))
density, RANGE = facts["density"], facts["range"]
LIP, SLOPE = np.array(facts["lip"], np.float32), np.array(facts["slope"], np.float32)
NAME = "info_stand"

pos4 = load("bake_st_pos")
nor4 = load("bake_st_nor")
facts4 = load("bake_st_facts")
ao4 = load("bake_st_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
# The AO bake's alpha is 1 everywhere, so its value is what says which texels it covered.
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

# Turned off the axes: on a surface square to the lattice, low-frequency noise thresholds into square-edged patches.
TURN = np.array(((0.70, -0.42, 0.58), (0.61, 0.77, -0.19), (-0.37, 0.48, 0.79)), np.float32)


def noise(p, freq, seed=0, octaves=1):
    return lattice_noise(p @ TURN, freq, seed, octaves)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
coat = finish == COAT
zinc = finish == ZINC
rubber = finish == RUBBER
gloss = finish == GLOSS
plate = finish == PLATE

edge_points = np.load(os.path.join(WORK, "stand_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=1.0, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 1.0).astype(np.float32))
edge = smooth(0.2, 0.02, edge_d)

big = field(noise(pts, 0.06, 1, 3))
mid = field(noise(pts, 0.4, 2, 4))
fine = field(noise(pts, 2.2, 3, 3))
micro = field(noise(pts, 7.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
# Long streaks running across, for scuffs and brushed steel.
streak = field(lattice_noise(pts * np.array((0.18, 2.4, 2.4), np.float32), 1.0, 7, 3))
drag = field(lattice_noise(pts * np.array((0.3, 1.1, 1.8), np.float32), 1.0, 9, 3))

# Where people stand and lean. A soft rub at shin height on the column's front and sides, shoes on the floor plate, hands on the head's front lip.
shins = coat * smooth(17.0, 6.0, Z) * smooth(5.0, 8.0, Z) * np.clip(0.35 + nor[..., 1] * 0.65, 0, 1) * smooth(0.36, 0.72, drag * 0.7 + mid * 0.3)
shoes = coat * smooth(1.2, 0.6, Z) * upward * smooth(-2.0, 6.0, Y) * smooth(0.34, 0.74, drag * 0.5 + big * 0.5)
hands = coat * smooth(4.6, 6.4, Y) * smooth(36.0, 33.0, Z) * smooth(0.3, 0.7, mid)
rubbed = ndi.gaussian_filter(edge * smooth(0.34, 0.74, big * 0.5 + mid * 0.5), 1.2)

# Screws, from their places.
screws = np.load(os.path.join(WORK, "stand_screws.npy"))
dist, _ = cKDTree(screws).query(pts, k=1, distance_upper_bound=0.5, workers=4)
screw_d = field(np.where(np.isfinite(dist), dist, 1.0).astype(np.float32))
screw = smooth(0.15, 0.11, screw_d)
screw_rim = smooth(0.24, 0.17, screw_d) * (1 - screw)

# Slots pressed in the coat: a speaker along the head's front lip, louvres at the top of the service door.
lip_face = coat & (nor[..., 1] > 0.25) & (Z > 31.7) & (Z < 33.4)
speaker = lip_face * smooth(0.4, 0.62, 0.5 + 0.5 * np.sin(X * 2 * math.pi * 1.5)) * smooth(0.36, 0.26, np.abs(Z - 32.45)) * smooth(9.4, 9.0, np.abs(X))
door_back = coat & (nor[..., 1] < -0.7)
louvres = door_back * smooth(0.42, 0.62, 0.5 + 0.5 * np.sin(Z * 2 * math.pi * 1.1)) * smooth(3.7, 3.4, np.abs(X)) * smooth(23.6, 23.9, Z) * smooth(26.6, 26.3, Z)
slots = np.clip(speaker + louvres, 0, 1)

# Seen in the engine, in the hall's dim blue light: sRGB 58, 66, 78 read as a black shape with no detail, and 106, 116, 130 as pale beside the hall's dark furniture.
s_color = rgb(80, 90, 104) * (0.94 + 0.12 * mid[..., None])
s_color = mix(s_color, rgb(126, 132, 140) * (0.88 + 0.2 * fine[..., None]), np.clip(shins * 0.28 + shoes * 0.55 + rubbed * 0.42 + hands * 0.26, 0, 0.8))
s_color = mix(s_color, rgb(8, 9, 11), slots * 0.92)
s_color = mix(s_color, rgb(138, 140, 138), screw_rim * 0.75)
s_color = mix(s_color, rgb(36, 36, 38), screw)
s_rough = 0.44 + 0.06 * mid + 0.04 * fine - hands * 0.14 - shins * 0.05 + shoes * 0.14
s_metal = 0.06 + np.clip(rubbed * 0.3 + shoes * 0.2, 0, 0.5) + screw_rim * 0.6

r_color = rgb(20, 20, 22) * (0.85 + 0.3 * mid[..., None])
marks = rubber * np.clip(nor[..., 1], 0, 1) * smooth(0.42, 0.74, drag) * smooth(1.0, 3.0, Z)
r_color = mix(r_color, rgb(62, 62, 64), marks * 0.6)
r_rough = 0.8 + 0.08 * mid - marks * 0.1

# Black glass: smudged lower down where it's touched, with three printed buttons in the bezel below the picture.
along = (Y - LIP[1]) * SLOPE[1] + (Z - LIP[2]) * SLOPE[2]
smudge = gloss * smooth(0.42, 0.74, big * 0.5 + mid * 0.5) * smooth(12.0, 3.0, along)
buttons = np.zeros((H, W), np.float32)
for x in (-6.0, 0.0, 6.0):
    buttons = np.maximum(buttons, smooth(0.075, 0.03, np.abs(np.hypot(X - x, along - 1.2) - 0.2)))
buttons = buttons * gloss * upward
g_color = mix(rgb(9, 11, 14), rgb(150, 170, 180), buttons * 0.85)
g_rough = 0.1 + smudge * 0.16 + buttons * 0.3

# The etched plate, read from the front, so +X is on the left. A ring with an "i", and the words under it.
face = plate & (nor[..., 1] > 0.7)
words = stencil_image(["VISITOR", "INFORMATION"], (1000, 520), bridge=False)
print_mask = sample_image(words, (4.2 - X) / 8.4, (Z - 15.4) / 4.4)
ring_d = np.hypot(X, Z - 23.0)
print_mask = np.maximum(print_mask, smooth(0.16, 0.08, np.abs(ring_d - 2.2)))
stem = smooth(0.34, 0.26, np.abs(X)) * smooth(21.3, 21.4, Z) * smooth(23.45, 23.35, Z)
dot = smooth(0.42, 0.34, np.hypot(X, Z - 24.1))
print_mask = np.maximum(print_mask, np.maximum(stem, dot))
print_mask = ndi.gaussian_filter((print_mask * face).astype(np.float32), 0.45)
p_color = mix(rgb(158, 160, 160) * (0.84 + 0.26 * streak[..., None]), rgb(14, 22, 36), print_mask * 0.96)
p_color = mix(p_color, rgb(36, 36, 38), screw * plate)
p_rough = 0.36 + 0.1 * streak + print_mask * 0.3
p_metal = 0.66 * (1 - print_mask)

z_color = rgb(150, 150, 148) * (0.78 + 0.3 * streak[..., None])
z_rough = 0.34 + 0.14 * mid
z_metal = 0.68

color = np.zeros((H, W, 3), np.float32)
color = np.where(coat[..., None], s_color, color)
color = np.where(zinc[..., None], z_color, color)
color = np.where(rubber[..., None], r_color, color)
color = np.where(gloss[..., None], g_color, color)
color = np.where(plate[..., None], p_color, color)
rough = np.where(coat, s_rough, np.where(zinc, z_rough, np.where(rubber, r_rough, np.where(gloss, g_rough, np.where(plate, p_rough, 0.6)))))
metal = np.where(coat, s_metal, np.where(zinc, z_metal, np.where(plate, p_metal, 0.0)))
height = np.where(coat, 0.0016 * (micro - 0.5) + 0.0012 * (fine - 0.5) - slots * 0.03 - screw * 0.02 + screw_rim * 0.004, 0.0)
height = np.where(rubber, 0.004 * (fine - 0.5) + 0.002 * (micro - 0.5), height)
height = np.where(plate, -print_mask * 0.004 + 0.0008 * (streak - 0.5) - screw * 0.02, height)
height = np.where(zinc, 0.0008 * (streak - 0.5), height)

# It's mopped: a little dust in the corners, some on the floor plate, and that's all.
gathered = smooth(0.15, 0.6, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4) * (1 - gloss)
low = smooth(2.2, 0.2, Z) * smooth(0.3, 0.7, fine)
grime = np.clip(gathered * 0.34 + low * 0.26, 0, 0.6)
color = mix(color, rgb(58, 54, 48) * (0.8 + 0.4 * fine[..., None]), grime)
rough = rough * (1 - grime * 0.6) + 0.8 * grime * 0.6
metal = metal * (1 - grime)
color = color * (0.68 + 0.32 * ao[..., None])

normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border
# takes its normal from just inside. Islands too thin to have an inside keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("stand painted", flush=True)
