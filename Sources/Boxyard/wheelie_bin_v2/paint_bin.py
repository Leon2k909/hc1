"""Paint the wheelie bin's maps from its bakes: python paint_bin.py <work dir> <output dir>

Coloured-through moulded plastic left out in a yard: chalked by the sun on what faces up, scuffed pale where it has been dragged
and knocked, with dirt thrown up from the ground and dark runs from under the lid. Its pressed panels and ribs are in the
normal map. Shared roughness, metalness, normal and AO, with a colour map per colour. All the lettering is made up.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

BODY, BLACK, ZINC, RUBBER, HUB = 0, 1, 3, 5, 6
facts = json.load(open(os.path.join(WORK, "wheelie_bin.json")))
density, RANGE = facts["density"], facts["range"]
NAME = "wheelie_bin"
AXLE_Y, AXLE_Z = -12.5, 4.0
# The map's own three colours, and what the sun has been turning them into. boxyard_materials' bx_bin_*.
COLOURS = {
    "green": ((38, 84, 52), (84, 112, 88), 61),
    "grey": ((82, 86, 90), (132, 133, 130), 71),
    "blue": ((30, 64, 120), (92, 118, 152), 81),
}

pos4 = load("bake_bin_pos")
nor4 = load("bake_bin_nor")
facts4 = load("bake_bin_facts")
ao4 = load("bake_bin_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
pos, nor, finish = fill_from(cover, pos, nor, finish)
# The AO bake's own coverage: at half the size it rasterises differently, and an empty texel counted as covered draws a dark line along every seam.
aoc = ao4[..., 0] > 0.001
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


edge_points = np.load(os.path.join(WORK, "wheelie_bin_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=1.0, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 1.0).astype(np.float32))
print("edges measured", len(edge_points), flush=True)

big = field(noise(pts, 0.1, 1, 3))
mid = field(noise(pts, 0.55, 2, 4))
fine = field(noise(pts, 2.8, 3, 3))
micro = field(noise(pts, 11.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
upward = np.clip(nor[..., 2], 0, 1)

body = finish == BODY
black = finish == BLACK
zinc = finish == ZINC
rubber = finish == RUBBER
hub = finish == HUB
plastic = body | black | hub


def panel(u, v, u0, u1, v0, v1, soft):
    """1 inside a rectangle, falling to 0 over `soft` outside its edge."""
    return smooth(u0 - soft, u0, u) * smooth(u1 + soft, u1, u) * smooth(v0 - soft, v0, v) * smooth(v1 + soft, v1, v)


# The moulding: panels pressed into the three walls with raised ribs across them, and into the lid. Told by which way a
# face looks and where it is, so they sit on the walls whatever the unwrap did.
on_body_wall = body & (Z > 3.0) & (Z < 36.0)
front = on_body_wall & (nor[..., 1] > 0.8)
back = on_body_wall & (nor[..., 1] < -0.8)
sides = on_body_wall & (np.abs(nor[..., 0]) > 0.8)
moulded = np.zeros((H, W), np.float32)
moulded = np.where(front, -0.11 * panel(X, Z, -7.0, 7.0, 12.8, 28.8, 0.35), moulded)
moulded = np.where(back, -0.11 * panel(X, Z, -5.8, 5.8, 12.8, 34.0, 0.35), moulded)
side_panel = panel(Y, Z, -7.2, 8.8, 12.8, 28.8, 0.35)
ribs = smooth(0.34, 0.14, np.abs(((Y + 7.2) % 4.0) - 2.0)) * panel(Y, Z, -7.0, 8.6, 13.4, 28.2, 0.15)
moulded = np.where(sides, -0.11 * side_panel + 0.09 * ribs, moulded)
front_ribs = smooth(0.34, 0.14, np.abs(((X + 7.0) % 4.67) - 2.33)) * panel(X, Z, -6.8, 6.8, 13.4, 28.2, 0.15)
moulded = np.where(front, moulded + 0.09 * front_ribs, moulded)
lid_top = body & (Z > 40.6) & (nor[..., 2] > 0.8)
lid_panel = panel(X, Y, -8.6, 8.6, -9.6, 11.4, 0.5)
lid_ribs = smooth(0.36, 0.16, np.abs(Y - 0.9)) + smooth(0.36, 0.16, np.abs(X)) * 0.9
moulded = np.where(lid_top, -0.08 * lid_panel + 0.055 * np.clip(lid_ribs, 0, 1) * lid_panel, moulded)
# A finger grip under the lid's front.
grip = body & (Y > 15.4) & (Z > 39.0) & (Z < 41.0)
moulded = np.where(grip, -0.1 * panel(X, Z, -5.5, 5.5, 39.4, 40.4, 0.2), moulded)


def on_face(image, normal, right, centre, width, z_low, z_high, up=None):
    """Lettering on a flat of the body, read from outside with Z up."""
    facing = (nor[..., 0] * normal[0] + nor[..., 1] * normal[1]) > 0.8
    uu = ((X * right[0] + Y * right[1]) - centre + width / 2) / width
    vv = (Z - z_low) / (z_high - z_low)
    return np.where(body & facing, sample_image(image, uu, vv), 0)


# Moulded in: the capacity, under each wall's panel on the front and on the lid's lip.
emboss = np.zeros((H, W), np.float32)
emboss = np.maximum(emboss, on_face(stencil_image(["240 L"], (640, 240), bridge=False), (0, 1), (-1, 0), 0.0, 4.2, 9.5 - 2.4, 9.5 - 0.8))
emboss = ndi.gaussian_filter(emboss, 0.8)

r = np.random.default_rng(1944)
# Scuffs and scrapes: pale lines where it has been dragged past things, mostly low down and across the walls.
skin = pts[(body | black)[cover]]
skin_normals = nor[cover][(body | black)[cover]]
lines, widths = [], []
for _ in range(300):
    i = int(r.integers(0, len(skin)))
    if skin[i][2] > 30 and r.random() < 0.55:
        continue
    start, n = skin[i], skin_normals[i]
    heading = r.normal(0, 1, 3)
    heading[2] *= 0.35
    heading -= n * heading.dot(n)
    heading /= max(np.linalg.norm(heading), 1e-6)
    length = float(r.uniform(0.7, 7.0))
    w = float(r.uniform(0.012, 0.05))
    steps = max(4, int(length / 0.06))
    for k in range(steps):
        lines.append(start + heading * (k / (steps - 1) - 0.5) * length)
        widths.append(w * (1 - abs(k / (steps - 1) - 0.5) * 1.3))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines)).query(pts, k=1, distance_upper_bound=0.25, workers=4)
which = np.minimum(which, len(widths) - 1)
scuff = field(smooth(1.0, 0.4, np.where(np.isfinite(dist), dist, 9.0) / widths[which]).astype(np.float32)) * plastic
scuff = ndi.gaussian_filter(scuff, 0.5)
# Knocks: a few shallow dents in the walls.
dent_at = skin[r.integers(0, len(skin), 12)]
dent_size = r.uniform(1.2, 3.2, 12)
dist, which = cKDTree(dent_at).query(pts, k=1, workers=4)
dent = field(smooth(1.0, 0.0, dist / dent_size[which]).astype(np.float32)) * body * (Z < 38.0)
# Corners and rims rubbed pale.
rubbed = smooth(0.26, 0.03, edge_d) * smooth(0.3, 0.7, mid * 0.5 + fine * 0.5) * plastic
drag = smooth(0.42, 0.72, field(noise(pts * np.array((0.35, 0.35, 2.4), np.float32), 1.0, 7, 3))) * smooth(16.0, 4.0, Z) * body

height = 0.0032 * (micro - 0.5) + 0.0028 * (fine - 0.5)
height = np.where(rubber, 0.0015 * (micro - 0.5), height) + np.where(plastic, moulded, 0) - dent * 0.09 - scuff * 0.012 + emboss * 0.03 * body
# The tyres: two grooves round the tread, and a shallow block pattern across it. The hubs: five spokes.
wheel_y, wheel_z = Y - AXLE_Y, Z - AXLE_Z
wheel_r = np.hypot(wheel_y, wheel_z)
wheel_a = np.arctan2(wheel_z, wheel_y)
tread = rubber & (wheel_r > 3.93)
ax = np.abs(X)
grooves = smooth(0.09, 0.03, np.abs(ax - 8.86)) + smooth(0.09, 0.03, np.abs(ax - 9.36))
blocks = smooth(0.2, 0.7, np.cos(wheel_a * 36.0) * 0.5 + 0.5)
height = np.where(tread, height - grooves * 0.05 + 0.02 * blocks, height)
spokes = smooth(0.45, 0.85, np.cos(wheel_a * 5.0) * 0.5 + 0.5) * smooth(0.95, 1.1, wheel_r) * smooth(2.0, 1.85, wheel_r)
height = np.where(hub, height + spokes * 0.07, height)

# Roughness: moulded satin, chalky where the sun has had it, polished a little where it has been rubbed.
sunned = np.clip(smooth(0.2, 1.0, upward) * 0.72 + smooth(0.4, 0.82, big) * 0.3 + (mid - 0.5) * 0.14, 0, 1)
rough = 0.56 + 0.08 * mid + 0.05 * fine + sunned * 0.18 - rubbed * 0.14 + scuff * 0.12
rough = np.where(black, 0.5 + 0.08 * mid + scuff * 0.14 - rubbed * 0.12, rough)
rough = np.where(hub, 0.52 + 0.08 * mid, rough)
rough = np.where(rubber, 0.82 + 0.08 * fine, rough)
z_tarnish = smooth(0.35, 0.75, field(noise(pts, 1.1, 25, 3)))
rough = np.where(zinc, 0.34 + 0.3 * z_tarnish, rough)
metal = np.where(zinc, 1.0 - z_tarnish * 0.35, 0.0).astype(np.float32)

# Dirt, the same for every colour: thrown up from the ground, settled on what faces up, run down from under the lid and the rim's lip.
low = smooth(11.0, 1.0, Z)
splash = low * smooth(0.28, 0.72, mid * 0.5 + fine * 0.3 + low * 0.3)
settled = smooth(0.5, 0.95, upward * 0.66 + (big - 0.5) * 0.38 + (mid - 0.5) * 0.2)
gathered = smooth(0.1, 0.5, crevice) * smooth(0.3, 0.7, mid * 0.6 + fine * 0.4)
dust = np.clip(settled * 0.3 + gathered * 0.34, 0, 0.75)
streaks = smooth(0.48, 0.74, field(noise(pts * np.array((1.9, 1.9, 0.07), np.float32), 1.0, 5, 3)))
below_rim = smooth(37.2, 33.0, Z) * smooth(10.0, 27.0, Z)
runs = streaks * below_rim * body * (nor[..., 2] < 0.5)
# What leaks when a full bin gets tipped: dark runs from the front corners of the rim.
leak = smooth(0.52, 0.76, field(noise(pts * np.array((2.6, 2.6, 0.09), np.float32), 1.0, 8, 3))) * smooth(37.0, 34.0, Z) * smooth(16.0, 30.0, Z) * front * smooth(3.0, 8.0, np.abs(X))
grime = np.clip(smooth(0.42, 0.92, crevice + (mid - 0.5) * 0.4) * 0.6 + splash * 0.55 + runs * 0.4 + leak * 0.5, 0, 0.92)
rough = rough * (1 - dust) + 0.92 * dust
rough = rough * (1 - grime * 0.6) + 0.88 * grime * 0.6
metal = metal * (1 - np.maximum(dust, grime))


def colour_map(base, faded, seed):
    own = field(noise(pts, 0.14, seed, 3))
    own_mid = field(noise(pts, 0.7, seed + 10, 3))
    plastic_colour = mix(rgb(*base), rgb(*faded), np.clip(sunned * (0.56 + 0.5 * own), 0, 1))
    plastic_colour = plastic_colour * (0.9 + 0.2 * mid[..., None]) * (0.94 + 0.12 * own_mid[..., None])
    # Stress-whitened where it has been scraped, knocked or rubbed: the same colour, gone pale.
    pale = plastic_colour * 1.55 + rgb(26, 26, 24)
    colour = mix(plastic_colour, pale, np.clip(scuff * 0.85 + rubbed * 0.55 + drag * 0.26 + dent * 0.12, 0, 0.9))
    # Sprayed through a stencil: which bay it belongs to, on the front and both sides, in white gone grey.
    stencil = stencil_image(["BAY 7"], (1100, 420), bridge=False)
    number = stencil_image(["07"], (620, 420), bridge=False)
    ink = on_face(stencil, (0, 1), (-1, 0), 0.0, 9.0, 18.0, 23.2)
    ink = np.maximum(ink, on_face(number, (1, 0), (0, 1), 0.8, 6.2, 18.5, 22.7))
    ink = np.maximum(ink, on_face(number, (-1, 0), (0, -1), -0.8, 6.2, 18.5, 22.7))
    worn = smooth(0.4, 0.62, field(noise(pts, 2.2, seed + 20, 3)) + (own_mid - 0.5) * 0.45 + scuff * 0.5)
    ink = np.clip(ndi.gaussian_filter(ink, 0.6) * (1 - worn * 0.75), 0, 1)
    colour = mix(colour, rgb(198, 196, 186) * (0.84 + 0.22 * fine[..., None]), ink * 0.92)
    colour = np.where(black[..., None], mix(rgb(30, 30, 31), rgb(74, 74, 72), np.clip(scuff * 0.85 + rubbed * 0.7, 0, 0.9)), colour)
    colour = np.where(hub[..., None], mix(rgb(44, 44, 45), rgb(82, 82, 80), rubbed * 0.8), colour)
    colour = np.where(rubber[..., None], rgb(22, 22, 22) * (0.9 + 0.3 * fine[..., None]), colour)
    colour = np.where(zinc[..., None], mix(rgb(170, 168, 158), rgb(74, 58, 44), z_tarnish * 0.82), colour)
    colour = mix(colour, rgb(126, 116, 94) * (0.8 + 0.4 * fine[..., None]), dust * (0.72 + 0.5 * own))
    colour = mix(colour, rgb(54, 46, 36) * (0.75 + 0.45 * fine[..., None]), np.clip(grime * (0.76 + 0.46 * own), 0, 0.92))
    colour = colour * (0.66 + 0.34 * ao[..., None])
    return fill_from(cover, np.clip(colour, 0, 1))[0]


for name, (base, faded, seed) in COLOURS.items():
    save_rgb(os.path.join(OUT, f"{NAME}_{name}_color.png"), colour_map(base, faded, seed))
    print("painted", name, flush=True)

normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border
# takes its normal from just inside. Islands too thin to have an inside keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
rough, metal, normal = fill_from(cover, np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("bin painted", flush=True)
