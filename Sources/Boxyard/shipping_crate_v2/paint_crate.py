"""Paint a crate's maps from its bakes: python paint_crate.py <work dir> <output dir> <standard|large>

Rough-sawn pine left out in a yard: grain running with each board, knots, every board its own tone, silvered by weather where it
faces up, darker where rain runs off the rails. Splintered pale along the frame's edges and scraped at the skids, with rusting nails
and painted stencils. Dark steel straps and handles. All the lettering is made up. Wear is worked out in 3D.
"""
import json
import math
import os
import sys

import numpy as np

VARIANT = sys.argv[3]
sys.argv[1] = os.path.join(sys.argv[1], VARIANT)
sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

OXIDE, BRACE, WOOD_X, WOOD_Y, WOOD_Z, DARK = 2, 10, 11, 12, 13, 15
facts = json.load(open(os.path.join(WORK, "crate.json")))
density, RANGE, LENGTH, WIDTH, HEIGHT, SKID, BATTEN, ANGLE = (facts[k] for k in ("density", "range", "length", "width", "height", "skid", "batten", "brace"))
HL, HW = LENGTH / 2, WIDTH / 2
NAME = f"crate_{VARIANT}"
WORDS = {
    "standard": (("MACHINE PARTS", "GROSS 180 KG"), ("BX 4471",), ("TERMINAL 4",)),
    "large": (("GENERATOR SPARES", "GROSS 620 KG"), ("BX 4472",), ("TERMINAL 4",)),
}[VARIANT]

pos4 = load("bake_cr_pos")
nor4 = load("bake_cr_nor")
facts4 = load("bake_cr_facts")
ao4 = load("bake_cr_ao")
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
wood_x, wood_y, wood_z, brace = finish == WOOD_X, finish == WOOD_Y, finish == WOOD_Z, finish == BRACE
wood = wood_x | wood_y | wood_z | brace
steel = finish == OXIDE
dark = finish == DARK

edge_points = np.load(os.path.join(WORK, "crate_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=1.2, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 1.2).astype(np.float32))
edge = smooth(0.32, 0.03, edge_d)
print("edges measured", len(edge_points), flush=True)

big = field(noise(pts, 0.05, 1, 3))
mid = field(noise(pts, 0.35, 2, 4))
fine = field(noise(pts, 2.0, 3, 3))
micro = field(noise(pts, 6.0, 4, 2))
crevice = np.clip((1 - ao) * 1.4, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)

# The grain follows each board, and each board starts from its own place in the tree.
offset = pts + field(0)[cover][:, None] + part[cover][:, None] * 37.0
c, s = math.cos(ANGLE), math.sin(ANGLE)
along_brace = np.column_stack((pts[:, 0] * c + pts[:, 2] * s, pts[:, 1], -pts[:, 0] * s + pts[:, 2] * c)) + part[cover][:, None] * 37.0


def stretched(values, scale, seed):
    return field(lattice_noise(values * np.array(scale, np.float32), 1.0, seed, 4))


grain_x = stretched(offset, (0.09, 1.1, 1.1), 31)
grain_y = stretched(offset, (1.1, 0.09, 1.1), 32)
grain_z = stretched(offset, (1.1, 1.1, 0.09), 33)
grain_b = stretched(along_brace, (0.09, 1.1, 1.1), 34)
grain = np.select([wood_x, wood_y, wood_z, brace], [grain_x, grain_y, grain_z, grain_b], grain_x)
lines = 0.5 + 0.5 * np.sin(grain * 24.0)
coarse_x = stretched(offset, (0.035, 0.34, 0.34), 35)
coarse_y = stretched(offset, (0.34, 0.035, 0.34), 36)
coarse_z = stretched(offset, (0.34, 0.34, 0.035), 37)
coarse_b = stretched(along_brace, (0.035, 0.34, 0.34), 38)
coarse = np.select([wood_x, wood_y, wood_z, brace], [coarse_x, coarse_y, coarse_z, coarse_b], coarse_x)

# Knots: dark, tight rings, a few to a board.
r = np.random.default_rng(4471)
wood_points = np.flatnonzero(wood[cover] & (np.abs(nor[cover][:, 2]) < 0.5))
seeds = pts[r.choice(wood_points, 110, replace=False)]
sizes = r.uniform(0.28, 0.7, 110)
dist, which = cKDTree(seeds).query(pts, k=1, workers=4)
ratio = dist / sizes[which] * (1.0 + (field(noise(pts, 3.0, 21, 2))[cover] - 0.5) * 0.8)
knot = field(smooth(1.0, 0.35, ratio).astype(np.float32)) * wood
knot_ring = field(smooth(2.4, 1.0, ratio).astype(np.float32)) * wood

# Nails: a dark head, and rust weeping down from it.
nail_points = np.load(os.path.join(WORK, "crate_nails.npy"))
dist, which = cKDTree(nail_points).query(pts, k=1, distance_upper_bound=0.8, workers=4)
nail = field(smooth(0.19, 0.11, np.where(np.isfinite(dist), dist, 1.0)).astype(np.float32)) * wood
squash = np.array((1.0, 1.0, 0.16), np.float32)
dist, which = cKDTree(nail_points * squash).query(pts * squash, k=1, distance_upper_bound=0.6, workers=4)
which = np.minimum(which, len(nail_points) - 1)
below = np.where(pts[:, 2] < nail_points[which, 2] + 0.05, 1.0, 0.0)
weep = field((smooth(0.3, 0.06, np.where(np.isfinite(dist), dist, 1.0)) * below).astype(np.float32)) * wood
weep = weep * smooth(0.3, 0.72, field(noise(pts * np.array((3.0, 3.0, 0.5), np.float32), 1.0, 22, 2)))

# Weather: silvering from the top and in patches, rain run off the rails, dirt from the ground, knocks round the skids.
weather = np.clip(upward * 0.62 + smooth(0.35, 0.8, big) * 0.34 + (part - 0.5) * 0.3 + smooth(0.3, 0.7, mid) * 0.18, 0, 1)
rain = (1 - upward) * smooth(0.54, 0.76, field(noise(pts * np.array((2.6, 2.6, 0.1), np.float32), 1.0, 23, 3))) * smooth(SKID + 2, HEIGHT * 0.5, Z)
low = smooth(HEIGHT * 0.34, 1.0, Z)
splash = low * smooth(0.32, 0.72, mid * 0.5 + fine * 0.35 + low * 0.35)
scrape = smooth(SKID + BATTEN + 2.0, SKID, Z) * smooth(0.52, 0.72, field(noise(pts * np.array((0.25, 0.25, 2.2), np.float32), 1.0, 24, 3)))
splinter = np.clip(edge * smooth(0.36, 0.7, fine * 0.55 + mid * 0.45) * 1.05 + scrape * 0.55, 0, 1) * wood
splinter = ndi.gaussian_filter(smooth(0.46, 0.62, splinter + (micro - 0.5) * 0.22), 0.5)

tone = (0.68 + 0.62 * part) * (0.88 + 0.24 * mid)
pine_light = rgb(152, 104, 62)
pine_dark = rgb(72, 46, 28)
timber = mix(pine_light, pine_dark, np.clip(lines * 0.46 + (coarse - 0.5) * 1.5 + 0.2, 0, 1)) * tone[..., None]
silver = mix(rgb(128, 112, 92), rgb(74, 62, 50), np.clip(lines * 0.5 + (coarse - 0.5) * 1.1 + 0.15, 0, 1))
timber = mix(timber, silver, weather * 0.46)
timber = mix(timber, timber * 0.42 + rgb(16, 12, 8), np.clip(knot * 0.9 + knot_ring * 0.25, 0, 1))
timber = mix(timber, timber * 0.56, rain * 0.62)
timber = mix(timber, rgb(176, 136, 92) * (0.86 + 0.24 * fine[..., None]), splinter * 0.86)
rust = mix(rgb(62, 36, 22), rgb(116, 68, 38), smooth(0.3, 0.8, fine))
timber = mix(timber, rust, np.clip(weep * 0.5, 0, 0.6))


def face_text(lines_, wide, tall, cx, cz, mask, across):
    """Stencil paint on one face. across is the texel's position along the face, running left to right as you look at it."""
    image = stencil_image(list(lines_), (int(wide * 26), int(tall * 26)), bridge=False)
    return np.where(mask, sample_image(image, (across - cx) / wide + 0.5, (Z - cz) / tall + 0.5), 0)


outer_y = (np.abs(nor[..., 1]) > 0.8) & (np.abs(Y) > HW - 2.0)
outer_x = (np.abs(nor[..., 0]) > 0.8) & (np.abs(X) > HL - 2.0)
main = WORDS[0]
tag = WORDS[1]
wide_main, tall_main = LENGTH * 0.66, HEIGHT * 0.36
ink = face_text(main, wide_main, tall_main, 0.0, HEIGHT * 0.52, outer_y & (Y > 0), -X)
ink = np.maximum(ink, face_text(main, wide_main, tall_main, 0.0, HEIGHT * 0.52, outer_y & (Y < 0), X))
ink = np.maximum(ink, face_text(tag, WIDTH * 0.6, HEIGHT * 0.17, 0.0, HEIGHT * 0.3, outer_x & (X > 0), Y))
ink = np.maximum(ink, face_text(tag, WIDTH * 0.6, HEIGHT * 0.17, 0.0, HEIGHT * 0.3, outer_x & (X < 0), -Y))
top_face = (nor[..., 2] > 0.8) & (Z > HEIGHT - 2.0)
top_text = stencil_image(list(WORDS[2]), (int(LENGTH * 0.5 * 26), int(WIDTH * 0.22 * 26)), bridge=True)
ink = np.maximum(ink, np.where(top_face, sample_image(top_text, (X + LENGTH * 0.25) / (LENGTH * 0.5), (Y + WIDTH * 0.11) / (WIDTH * 0.22)), 0))
ink = ndi.gaussian_filter(ink, 0.5)
# Sprayed onto rough boards through a card: thin where the wood's grain stands proud and where weather has had it.
worn = smooth(0.46, 0.72, field(noise(pts, 1.1, 25, 3)) * 0.8 + lines * 0.2 + weather * 0.06)
ink = np.clip(ink * (1 - worn * 0.6) * (1 - splinter), 0, 1) * wood
timber = mix(timber, rgb(16, 15, 14), ink * 0.94)

color = np.zeros((H, W, 3), np.float32)
color = np.where(wood[..., None], timber, color)
rough = 0.72 + 0.12 * lines + 0.06 * fine - knot * 0.2 - ink * 0.14 + splinter * 0.05
metal = np.zeros((H, W), np.float32)
height = 0.012 * (lines - 0.5) + 0.03 * (coarse - 0.5) * 2.0 + 0.002 * (micro - 0.5) - nail * -0.018 - splinter * 0.016 + knot * 0.006 + ink * 0.001

# Strapping and handles: blacked steel gone brown at its edges.
s_wear = smooth(0.46, 0.68, fine * 0.6 + mid * 0.4)
s_rust = smooth(0.5, 0.76, field(noise(pts, 1.2, 26, 3)) + crevice * 0.14)
s_color = mix(rgb(34, 34, 36) * (0.78 + 0.44 * mid[..., None]), rgb(120, 118, 112), s_wear * 0.3)
s_color = mix(s_color, rust, s_rust * 0.82)
color = np.where(steel[..., None], s_color, color)
rough = np.where(steel, 0.48 + 0.16 * fine + s_rust * 0.3, rough)
metal = np.where(steel, np.clip(0.92 - s_rust * 0.85, 0, 1), metal)
height = np.where(steel, 0.0016 * (micro - 0.5) + s_rust * 0.003, height)

# The nails' heads.
nail_c = mix(rgb(56, 54, 52), rust, smooth(0.35, 0.7, fine))
color = mix(color, nail_c, nail * 0.95)
rough = rough * (1 - nail) + 0.58 * nail
metal = metal * (1 - nail) + 0.55 * nail

# The dark behind the boards.
color = np.where(dark[..., None], rgb(10, 9, 8), color)
rough = np.where(dark, 0.9, rough)

settled = smooth(0.48, 0.92, upward * 0.72 + (big - 0.5) * 0.4 + (mid - 0.5) * 0.3)
grit = smooth(0.28, 0.62, fine * 0.55 + micro * 0.45)
gathered = smooth(0.1, 0.55, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4)
dust = np.clip(settled * 0.42 * (0.3 + 0.7 * grit) + gathered * 0.34, 0, 0.7) * (1 - dark)
color = mix(color, rgb(122, 112, 90) * (0.8 + 0.4 * fine[..., None]), dust)
rough = rough * (1 - dust) + 0.92 * dust
metal = metal * (1 - dust)
grime = np.clip(smooth(0.42, 0.9, crevice + (mid - 0.5) * 0.4) * 0.55 + splash * 0.55, 0, 0.88) * (1 - dark)
color = mix(color, rgb(52, 45, 36) * (0.75 + 0.45 * fine[..., None]), grime)
rough = rough * (1 - grime * 0.6) + 0.88 * grime * 0.6
metal = metal * (1 - grime)
color = color * (0.64 + 0.36 * ao[..., None])

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
print("crate painted", VARIANT, flush=True)
