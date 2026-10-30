"""Paint the range target's maps from its bakes: python paint_target.py <work dir> <materials dir>

The face keeps the old target's colours and aiming marks, freshly sprayed and with no shot marks at all: the user wants the
only marks on it to be the player's own. The age is all in the edges, the rust and the dirt.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, linear_to_srgb, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, FACE, APRON = range(11)

pos4 = load("bake_rt_pos")
nor4 = load("bake_rt_nor")
facts4 = load("bake_rt_facts")
ao4 = load("bake_rt_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
density = json.load(open(os.path.join(WORK, "target.json")))["density"]
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
convex = np.clip(curve * 0.38, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 2.2) * 2.4 + ndi.gaussian_filter(convex, 6.0) * 3.0, 0, 1)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


big = field(noise(pts, 0.14, 1, 3))
mid = field(noise(pts, 0.7, 2, 4))
fine = field(noise(pts, 3.0, 3, 3))
micro = field(noise(pts, 10.0, 4, 2))
streak = field(noise(pts * np.array((3.6, 3.6, 0.14), np.float32), 0.3, 6, 4))
crevice = np.clip((1 - ao) * 1.3, 0, 1)

steel = srgb_to_linear((160, 160, 156))
rust_c = mix(np.broadcast_to(srgb_to_linear((62, 36, 22)), (H, W, 3)), np.broadcast_to(srgb_to_linear((112, 66, 38)), (H, W, 3)), smooth(0.35, 0.8, field(noise(pts, 3.1, 8, 3))))

Y, Z = pos[..., 1], pos[..., 2]
front = nor[..., 0] < -0.5
plate = finish == FACE
apron = finish == APRON


color = np.zeros((H, W, 3), np.float32)
rough = np.zeros((H, W), np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

chip = edge * smooth(0.3, 0.68, mid * 0.65 + fine * 0.35) * 1.12 + (mid - 0.5) * 0.6 + (big - 0.5) * 0.4 + (fine - 0.5) * 0.85 + (micro - 0.5) * 0.3
bare = smooth(0.72, 0.74, chip)
under = smooth(0.67, 0.69, chip)

# The face. Colours are the old target's own, and its marks sit in the same places at the same sizes.
white = np.broadcast_to(srgb_to_linear((222, 224, 216)), (H, W, 3)) * (0.86 + 0.2 * mid[..., None])
white = white * (1 - (smooth(0.4, 0.85, big)[..., None] * np.array((0.06, 0.08, 0.14), np.float32)))
spray = 0.12 * (fine - 0.5) + 0.05 * (micro - 0.5)
bull = smooth(9.08, 8.92, np.hypot(Y, Z - 44) + spray)
centre = smooth(3.05, 2.95, np.hypot(Y, Z - 44) + spray * 0.6)
head_mark = smooth(2.66, 2.54, np.hypot(Y, Z - 66) + spray * 0.6)
black = np.broadcast_to(np.array((0.045, 0.06, 0.072), np.float32), (H, W, 3)) * (0.82 + 0.4 * mid[..., None])
orange = np.broadcast_to(np.array((0.95, 0.29, 0.055), np.float32), (H, W, 3)) * (0.8 + 0.28 * mid[..., None])
f_color = mix(white, black, bull)
f_color = mix(f_color, black, head_mark)
f_color = mix(f_color, orange, centre)
# Runs of dirty water below each mark and off the bolts.
runs = smooth(0.56, 0.78, streak) * smooth(0.25, 0.7, mid)
f_color = f_color * (1 - runs[..., None] * np.array((0.14, 0.17, 0.22), np.float32))
f_rough = 0.56 + 0.16 * mid + 0.08 * fine
f_metal = np.zeros((H, W), np.float32)
f_height = 0.0045 * (micro - 0.5) + 0.002 * (fine - 0.5) + (bull + head_mark + centre) * 0.002

# The plate's back and edges were only ever primed.
back = np.broadcast_to(srgb_to_linear((84, 86, 80)), (H, W, 3)) * (0.8 + 0.4 * mid[..., None])
f_color = np.where(front[..., None], f_color, back)

# Worn edges.
f_color = mix(f_color, np.broadcast_to(steel, (H, W, 3)) * 0.74, bare)
f_metal = np.maximum(f_metal, bare)
f_rough = f_rough * (1 - bare) + 0.42 * bare
rusted = bare * smooth(0.48, 0.72, field(noise(pts, 1.7, 9, 3)) + crevice * 0.3)
f_color = mix(f_color, rust_c, rusted)
f_metal = f_metal * (1 - rusted)
f_rough = f_rough * (1 - rusted) + 0.86 * rusted
f_height = f_height + (1 - bare) * 0.008

color = np.where(plate[..., None], f_color, color)
rough = np.where(plate, f_rough, rough)
metal = np.where(plate, f_metal, metal)
height = np.where(plate, f_height, height)

# Frame, trolley and deflector: dull grey-green enamel, rusted a lot more, since no one repaints those.
is_frame = (finish == PAINT) | (finish == WELD) | apron
enamel = np.broadcast_to(srgb_to_linear((80, 86, 74)), (H, W, 3)) * (0.78 + 0.44 * mid[..., None]) * (0.9 + 0.2 * part[..., None])
upright = 1 - np.abs(nor[..., 2])
enamel = enamel * (1 + upright[..., None] * (streak[..., None] - 0.5) * 0.5)
art = stencil_image(["AR500 STEEL", "NO AP ROUNDS"], (900, 300))
lettering = sample_image(art, np.clip((7.2 - Y) / 14.4, -1, 2), np.clip((Z - 7.0) / 4.8, -1, 2)) * (apron & front) * smooth(0.14, 0.34, field(noise(pts, 3.3, 10, 3)))
fr_color = mix(enamel, np.broadcast_to(srgb_to_linear((204, 200, 182)), (H, W, 3)), lettering * 0.92)
fr_color = mix(fr_color, np.broadcast_to(srgb_to_linear((104, 104, 92)), (H, W, 3)), under)
fr_color = mix(fr_color, np.broadcast_to(steel, (H, W, 3)) * (0.68 + 0.4 * fine[..., None]), bare)
fr_rust = bare * smooth(0.42, 0.66, field(noise(pts, 1.7, 11, 3)) + crevice * 0.4)
fr_runs = smooth(0.54, 0.76, streak + crevice * 0.26) * smooth(0.25, 0.6, mid + crevice * 0.55)
fr_color = mix(fr_color, rust_c, fr_rust)
fr_color = mix(fr_color, fr_color * rust_c * 3.0, fr_runs * 0.5)
fr_color = np.where((finish == WELD)[..., None], fr_color * 0.72, fr_color)
fr_rough = 0.52 + 0.2 * mid + 0.1 * fine
fr_rough = fr_rough * (1 - bare) + 0.42 * bare
fr_rough = fr_rough * (1 - fr_rust) + 0.86 * fr_rust
fr_metal = bare * (1 - fr_rust)
fr_height = 0.0055 * (micro - 0.5) + 0.0024 * (fine - 0.5) + (1 - under) * 0.009 + (1 - bare) * 0.008 + fr_rust * 0.006 * (fine - 0.3)
weld = finish == WELD
fr_height = fr_height + weld * (0.05 * (field(noise(pts, 4.2, 12, 3)) - 0.5) + 0.02 * (micro - 0.5))
color = np.where(is_frame[..., None], fr_color, color)
rough = np.where(is_frame, fr_rough, rough)
metal = np.where(is_frame, fr_metal, metal)
height = np.where(is_frame, fr_height, height)

# Black-oxide fittings.
oxide = finish == OXIDE
o_wear = smooth(0.44, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
o_color = np.broadcast_to(srgb_to_linear((42, 42, 44)), (H, W, 3)) * (0.75 + 0.5 * mid[..., None])
o_color = mix(o_color, np.broadcast_to(steel, (H, W, 3)) * 0.78, o_wear * 0.9)
o_rust = smooth(0.74, 0.88, field(noise(pts, 3.6, 13, 3)) + crevice * 0.08)
o_color = mix(o_color, rust_c, o_rust * 0.7)
color = np.where(oxide[..., None], o_color, color)
rough = np.where(oxide, 0.4 + 0.2 * fine - 0.1 * o_wear + 0.35 * o_rust, rough)
metal = np.where(oxide, (1 - o_rust) * 0.92, metal)
height = np.where(oxide, 0.0016 * (micro - 0.5) + o_rust * 0.006, height)

# Plated bolts and axles.
zinc = finish == ZINC
z_color = np.broadcast_to(srgb_to_linear((186, 188, 186)), (H, W, 3)) * (0.5 + 0.3 * mid[..., None])
z_rust = smooth(0.48, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.5)
z_color = mix(z_color, rust_c, z_rust * 0.55)
z_color = mix(z_color, np.broadcast_to(steel, (H, W, 3)), smooth(0.5, 0.8, edge) * 0.5)
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, 0.3 + 0.2 * fine + 0.4 * z_rust, rough)
metal = np.where(zinc, 1 - z_rust * 0.75, metal)
height = np.where(zinc, 0.0012 * (micro - 0.5), height)

# Hard rubber wheels, worn shiny on the tread.
rubber = finish == RUBBER
radial = np.abs(np.hypot(pos[..., 2] + 0.95, 0))
color = np.where(rubber[..., None], np.broadcast_to(srgb_to_linear((30, 30, 30)), (H, W, 3)) * (0.75 + 0.5 * fine[..., None]), color)
rough = np.where(rubber, 0.66 + 0.16 * fine, rough)
metal = np.where(rubber, 0.0, metal)
height = np.where(rubber, 0.004 * (fine - 0.5), height)

# Dust on what faces up, grime and lead dust gathering low.
upward = np.clip(nor[..., 2], 0, 1)
low = np.clip(1 - (pos[..., 2] + 1.9) / 14.0, 0, 1) ** 1.5
settled = smooth(0.4, 0.9, upward * 0.84 + (big - 0.5) * 0.34 + crevice * 0.2)
splash = low * smooth(0.48, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 14, 4)) + low * 0.12)
dirt = np.clip(settled * 0.5 + splash * 0.6, 0, 0.9)
dirt_c = np.broadcast_to(srgb_to_linear((98, 88, 72)), (H, W, 3)) * (0.75 + 0.5 * fine[..., None])
color = mix(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.93 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.004 * (fine - 0.35)

color = color * (0.72 + 0.28 * ao[..., None])
solid = ndi.binary_erosion(cover, iterations=1)
height = fill_from(solid, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(solid, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "rt_steel_color.png"), color)
save_gray(os.path.join(OUT, "rt_steel_rough.png"), rough)
save_gray(os.path.join(OUT, "rt_steel_metal.png"), metal)
save_gray(os.path.join(OUT, "rt_steel_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "rt_steel_normal.png"), normal)
print("target painted", flush=True)
