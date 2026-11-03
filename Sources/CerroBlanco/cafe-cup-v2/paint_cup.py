"""Paint the cup and saucer's maps from their bakes: python paint_cup.py <work dir> <output dir>

Hotel-weight white porcelain, glazed glossy all over but for the foot rings, which are bare bisque, greyed by tables. The saucer's well has a coffee ring where a cup was set down off its middle and
a few drips toward the spoon. Inside the cup, a line of dried foam at the coffee's level with fainter ones below it, dregs on its floor, a smear on the lip where it was drunk from and one drip down
the outside. The full cup's top is a cappuccino: a heart of milk foam on crema, darker at the wall. The spoon is polished steel, a coffee film in its bowl. Worked out in 3D from the baked position
of each texel, and by part from the build's list. Values are kept strong.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

PORCELAIN, STEEL, COFFEE = 0, 4, 5
facts_file = json.load(open(os.path.join(WORK, "cup.json")))
density, RANGE = facts_file["density"], facts_file["range"]
CUP_Z, COFFEE_Z = facts_file["cup_z"], facts_file["coffee_z"]
SPOON = math.radians(facts_file["spoon_angle"])
NAME = "cup"

pos4 = load("bake_cu_pos")
nor4 = load("bake_cu_nor")
facts4 = load("bake_cu_facts")
ao4 = load("bake_cu_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
weight = facts4[..., 2]
pos, nor, finish, part, weight = fill_from(cover, pos, nor, finish, part, weight)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), (H / ao.shape[0], W / ao.shape[1]), order=1), 0, 1)
# The bake's occlusion reaches 3 in, the whole cup, so its inside came out black: keep only the near half of it.
ao = 0.5 + 0.5 * ao
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

listed = json.load(open(os.path.join(WORK, "cup_parts.json")))
rands = np.array([r for r, _, _ in listed], np.float32)
order = np.argsort(rands)
names = np.array([n for _, n, _ in listed])[order]
at = np.clip(np.searchsorted(rands[order], part), 1, len(rands) - 1)
nearer = np.where(np.abs(rands[order][at - 1] - part) < np.abs(rands[order][at] - part), at - 1, at)
part_name = names[nearer]

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
NZ = nor[..., 2]
RHO = np.hypot(X, Y)
ANGLE = np.arctan2(Y, X)
porcelain = (finish == PORCELAIN) & cover
steel = finish == STEEL
coffee = finish == COFFEE
saucer = porcelain & (part_name == "saucer")
cup = porcelain & np.isin(part_name, ("cup", "handle"))
big = field(noise(pts, 0.6, 1, 3))
mid = field(noise(pts, 3.0, 2, 4))
fine = field(noise(pts, 14.0, 3, 3))
micro = field(noise(pts, 50.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
CZ = Z - CUP_Z  # Height above the cup's foot.
# Inside the cup: the faces that look in toward its middle.
radial = (nor[..., 0] * X + nor[..., 1] * Y) / np.maximum(RHO, 1e-4)
inside = cup & (part_name == "cup") & (radial < -0.2) & (CZ > 0.25) & (CZ < 2.5)
floor = cup & (part_name == "cup") & (CZ > 0.2) & (CZ < 0.32) & (NZ > 0.5) & (RHO < 0.62)

# ---- The glaze, and the bare foot rings. ----
glaze = rgb(242, 240, 236) * (0.985 + 0.02 * big[..., None])
saucer_foot = saucer & (Z < 0.065) & (RHO > 1.5) & (RHO < 1.9) & (NZ < 0.2)
cup_foot = cup & (part_name == "cup") & (CZ < 0.075) & (RHO > 0.8) & (NZ < 0.2)
bisque = saucer_foot | cup_foot
bisque_c = rgb(204, 198, 186) * (0.92 + 0.1 * mid[..., None])
bisque_c = mix(bisque_c, rgb(132, 126, 116), smooth(0.4, 0.8, mid) * 0.45)
# No kiln specks: at this size any the noise made read as grey flecks over the whole glaze, like terrazzo.
color = glaze.copy()
color = np.where(bisque[..., None], bisque_c, color)
rough = np.where(bisque, 0.72 + 0.08 * fine, 0.07 + 0.03 * fine)
height = np.where(bisque, 0.0012 * (fine - 0.5) + 0.0008 * (micro - 0.5), 0.0006 * (big - 0.5) + 0.00015 * (micro - 0.5))

# ---- Coffee left on the porcelain. ----
stain = rgb(122, 80, 44)
dry = rgb(176, 136, 92)
# A ring in the well where a cup was set down off its middle, and drips toward the spoon.
ring = smooth(0.05, 0.012, np.abs(np.hypot(X - 0.22, Y + 0.16) - 1.02)) * smooth(0.25, 0.6, field(noise(pts, 2.0, 11, 2))) * saucer * (NZ > 0.5)
drips = np.zeros((H, W), np.float32)
r = np.random.default_rng(5)
for _ in range(5):
    dr = r.uniform(1.3, 2.2)
    da = SPOON + r.uniform(-0.45, 0.45)
    cx, cy, rad = dr * math.cos(da), dr * math.sin(da), r.uniform(0.04, 0.12)
    d = np.hypot(X - cx, Y - cy) / rad + (fine - 0.5) * 0.4
    drips = np.maximum(drips, smooth(1.0, 0.7, d) * 0.6 + smooth(0.12, 0.0, np.abs(d - 0.95)) * 0.5)
drips = drips * saucer * (NZ > 0.4)
# Inside: a line of dried foam at the coffee's level and fainter ones as it was drunk down, dregs on the floor.
foam_line = smooth(0.07, 0.0, np.abs(CZ - (COFFEE_Z + 0.045 + 0.015 * (mid - 0.5)))) * inside
lower_lines = np.zeros((H, W), np.float32)
for k, level in enumerate((1.68, 1.31, 0.98, 0.7)):
    lower_lines = np.maximum(lower_lines, smooth(0.035, 0.0, np.abs(CZ - level - 0.03 * (mid - 0.5))) * (0.7 - 0.12 * k))
lower_lines = lower_lines * inside * smooth(0.3, 0.6, field(noise(pts, 1.5, 12, 2)))
film = inside * smooth(COFFEE_Z + 0.02, COFFEE_Z - 0.4, CZ) * 0.1
dregs = floor * smooth(0.48, 0.25, RHO + (mid - 0.5) * 0.15)
# A smear on the lip where it was drunk from, a quarter turn from the handle, and a drip down the outside under it.
drink = math.pi / 2
lip = cup & (part_name == "cup") & (CZ > 2.42)
smear = lip * smooth(0.55, 0.2, np.abs(np.angle(np.exp(1j * (ANGLE - drink))))) * smooth(0.35, 0.7, fine)
outside = cup & (part_name == "cup") & (radial > 0.2)
run = outside * smooth(0.06, 0.02, RHO * np.abs(np.angle(np.exp(1j * (ANGLE - drink - 0.12)))) + 0.01 * (CZ - 2.4) ** 2) * smooth(1.25, 1.6, CZ) * smooth(2.52, 2.4, CZ)
color = mix(color, stain * (0.9 + 0.2 * fine[..., None]), np.clip(ring * 0.6 + drips * 0.55 + run * 0.5, 0, 1))
color = mix(color, dry, np.clip(foam_line * 0.75 + lower_lines * 0.45 + film + smear * 0.35, 0, 1))
color = mix(color, rgb(84, 50, 26), np.clip(dregs, 0, 1) * 0.9)
rough = rough + dregs * 0.25 + foam_line * 0.3 + lower_lines * 0.15 + ring * 0.12 + drips * 0.1
height = height + foam_line * 0.002 + dregs * 0.003

# ---- The cappuccino: a heart of milk foam on crema. ----
top = coffee & (NZ > 0.5)
u, v = X / 0.9, (Y + 0.12) / 0.9  # The heart is about 2 in across, its point toward +y, where it is drunk from.
hx, hy = u * 1.05, -v * 1.05 + 0.15
heart = (hx * hx + hy * hy - 1) ** 3 - hx * hx * hy ** 3  # The classic heart curve: inside where it's below 0.
# The curve's values are tiny near its line, so the line is found from them over their slope, and only then given a soft, slightly ragged edge as foam has.
gy, gx = np.gradient(heart)
slope = np.maximum(np.hypot(gx, gy) * density * np.maximum(weight, 1e-3), 1e-3)
edge_in = heart / slope
heart_edge = smooth(0.035, -0.035, edge_in + (fine - 0.5) * 0.03)
inner = np.zeros((H, W), np.float32)
edge_r = np.max(RHO[top]) if top.any() else 1.6
crema = mix(rgb(132, 84, 46), rgb(98, 60, 32), smooth(edge_r - 0.35, edge_r, RHO)[..., None])
crema = crema * (0.92 + 0.14 * fine[..., None])
foam = rgb(240, 230, 212) * (0.96 + 0.05 * micro[..., None])
c_color = mix(crema, foam, np.clip(heart_edge - inner, 0, 1))
c_color = np.where((coffee & ~top)[..., None], rgb(98, 60, 32), c_color)
bubbles = field(noise(pts, 60.0, 21, 1))
c_rough = 0.28 + 0.2 * heart_edge + 0.05 * fine
c_height = 0.0012 * (bubbles - 0.5) * (1 - heart_edge * 0.6) + 0.004 * heart_edge
color = np.where(coffee[..., None], c_color, color)
rough = np.where(coffee, c_rough, rough)
height = np.where(coffee, c_height, height)

# ---- The spoon. ----
along = X * math.cos(SPOON) + Y * math.sin(SPOON)
bowl = steel & (along < 1.9) & (NZ > 0.3)
brushed = field(lattice_noise(np.column_stack(((X * math.cos(SPOON) + Y * math.sin(SPOON))[cover] * 0.8, (-X * math.sin(SPOON) + Y * math.cos(SPOON))[cover] * 30.0, Z[cover])).astype(np.float32), 1.0, 31, 2))
s_color = rgb(196, 196, 192) * (0.9 + 0.12 * brushed[..., None])
s_color = mix(s_color, rgb(150, 112, 74), bowl * smooth(0.3, 0.7, mid) * 0.45)
color = np.where(steel[..., None], s_color, color)
rough = np.where(steel, 0.1 + 0.08 * brushed + bowl * 0.15, rough)
metal = np.where(steel, 1.0 - bowl * 0.3, 0.0).astype(np.float32)

color = color * (0.8 + 0.2 * ao)[..., None]
height = fill_from(cover, height)[0]
filtered = ndi.gaussian_filter(height, 0.45)
px = np.maximum(density * weight, 1.0)
dv, du = np.gradient(filtered)
normal = np.stack((-du * px, -dv * px, np.ones_like(filtered)), -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
keep_in = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(keep_in, iterations=3) & cover
normal = fill_from(keep_in | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.05, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("cup painted", flush=True)
