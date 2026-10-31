"""Paint the shutter's maps from its bakes: python paint_shutter.py <work dir> <materials dir> shutter

Thick old green paint on softwood, the same green as the old shutter's. The sun has faded it and it's flaking off the slats' front edges
and the stiles' arrises, down to grey weathered timber. The iron is black, with rust and the rust's streaks below it.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

BOARD_Y, BOARD_Z, IRON, LINER = range(4)
NAME = "shutter"
facts = json.load(open(os.path.join(WORK, "shutter.json")))
density = facts["density"]

pos4 = load("bake_shutter_pos")
nor4 = load("bake_shutter_nor")
facts4 = load("bake_shutter_facts")
ao4 = load("bake_shutter_ao")
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
convex = np.clip((curve - 2.0) * 0.4, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.6) * 2.4 + ndi.gaussian_filter(convex, 4.0) * 2.8, 0, 1).astype(np.float32)
rows, cols = np.nonzero(cover)
pts = pos[rows, cols]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]


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


big = field(noise(pts, 0.14, 1, 3))
mid = field(noise(pts, 0.8, 2, 3))
fine = field(noise(pts, 3.4, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
print("fields", flush=True)

# The wood under the paint, with its grain running each member's way, and brush marks in the paint running with it.
vertical = finish == BOARD_Z
offset = part[rows, cols][:, None] * np.array((131.0, 57.0, 91.0), np.float32)
along_z = pts * np.array((4.2, 4.2, 0.09), np.float32) + offset
along_y = pts * np.array((4.2, 0.09, 4.2), np.float32) + offset
grain = np.where(vertical, field(noise(along_z, 1.0, 31, 3)), field(noise(along_y, 1.0, 32, 3)))
lines = 0.5 + 0.5 * np.sin(grain * 20.0)
brush_z = pts * np.array((12.0, 12.0, 0.25), np.float32)
brush_y = pts * np.array((12.0, 0.25, 12.0), np.float32)
brush = np.where(vertical, field(noise(brush_z, 1.0, 33, 2)), field(noise(brush_y, 1.0, 34, 2)))
timber = blend(flat(C(146, 136, 116)), flat(C(84, 74, 62)), lines * 0.7 + 0.15 * (mid - 0.5))

# Sun fade comes from above and off the slats' faces; a second, older coat shows through where it's flaked.
fade = smooth(0.3, 0.75, big + (mid - 0.5) * 0.3) * 0.34 + smooth(0.4, 0.95, upward) * 0.3
paint = blend(flat(C(62, 96, 70)), flat(C(112, 134, 104)), np.clip(fade, 0, 1)) * (0.86 + 0.3 * part[..., None])
paint = paint * (0.9 + 0.2 * brush[..., None])
chip = edge * smooth(0.25, 0.65, mid * 0.6 + fine * 0.4) * 1.1 + (mid - 0.5) * 0.48 + (fine - 0.5) * 0.74 + (micro - 0.5) * 0.28 + (big - 0.5) * 0.2
to_under = smooth(0.6, 0.62, chip)
to_wood = smooth(0.68, 0.7, chip)
under = flat(C(170, 158, 124)) * (0.85 + 0.25 * fine[..., None])
b_color = blend(blend(paint, under, to_under), timber, to_wood)
b_color = blend(b_color, b_color * 0.5, smooth(0.4, 0.9, crevice) * 0.7)
b_rough = 0.46 + 0.14 * mid + 0.1 * brush + fade * 0.3
b_rough = b_rough * (1 - to_under) + (0.66 + 0.1 * fine) * to_under
b_rough = b_rough * (1 - to_wood) + (0.82 + 0.1 * fine) * to_wood
b_height = 0.0035 * (brush - 0.5) + (1 - to_under) * 0.01 + (1 - to_wood) * 0.008 + 0.006 * (grain - 0.5) * (1 + to_wood)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.7, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)
board = (finish == BOARD_Y) | vertical
color[board] = b_color[board]
rough[board] = b_rough[board]
height[board] = b_height[board]
print("boards", flush=True)

# What shows between the slats, and of the leaf from far off once they've gone at the last LOD: a dark, dull version of its green.
liner = finish == LINER
color[liner] = C(38, 54, 42)
rough[liner] = 0.9

# Iron: black paint, rubbed and rusting, and rust stains hanging under each hinge.
iron = finish == IRON
rust = blend(flat(C(60, 34, 22)), flat(C(128, 72, 38)), smooth(0.3, 0.75, mid * 0.6 + fine * 0.4))
i_rust = smooth(0.46, 0.66, field(noise(pts, 1.6, 13, 3)) + edge * 0.18)
i_color = blend(flat(C(24, 24, 25)) * (0.75 + 0.5 * mid[..., None]), rust, i_rust * 0.9)
color[iron] = i_color[iron]
rough[iron] = (0.52 + 0.16 * fine + 0.3 * i_rust)[iron]
metal[iron] = ((1 - i_rust) * 0.7)[iron]
height[iron] = ((fine - 0.4) * i_rust * 0.018)[iron]
streak = field(noise(pts * np.array((2.8, 2.8, 0.1), np.float32), 1.0, 41, 2))
for z in (11.5, 52.5):
    below = smooth(z + 1.0, z, Z) * smooth(z - 11.0, z - 1.0, Z) * smooth(11.5, 3.0, 12.5 - Y) * board
    stain = below * smooth(0.46, 0.66, streak)
    color[...] = blend(color, rust * 0.75, np.clip(stain * 0.75, 0, 1))
print("iron", flush=True)

# Dirt: dust on what faces up, in the slats' throats and rising from the sill below.
settled = smooth(0.5, 0.92, upward * 0.8 + crevice * 0.3 + (big - 0.5) * 0.3)
dirt = np.clip(settled * 0.34 + smooth(9.0, 0.5, Z) * 0.26, 0, 0.7) * ~liner * ~iron
color = blend(color, flat(C(112, 102, 86)) * (0.8 + 0.4 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.9 * dirt

color = color * (0.66 + 0.34 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
half = lambda a: (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), half(metal))
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), half(np.clip(ao * 1.03, 0, 1)))
print("shutter painted", flush=True)
