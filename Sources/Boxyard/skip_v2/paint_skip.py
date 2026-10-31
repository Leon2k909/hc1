"""Paint the skip's maps from its bakes: python paint_skip.py <work dir> <materials dir> skip

A skip has the hardest life of anything in the yard, and should look it: bright fleet green over an older yellow over steel,
gouged by chains and loads, its rim worn bare, rust blooming along the bottom and running down from every knock, the inside
scoured back to brown steel. Wear is worked out in 3D, so it runs across UV seams. Every word on it is made up: TARVEN is
invented, and 01632 960xxx is the UK range set aside for fiction.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, RUST, BRICK, CONCRETE, TIMBER = range(11)
NAME = "skip"
BOLD = os.path.join(ROOT, "Assets", "fonts", "Dinish-Bold.ttf")
facts = json.load(open(os.path.join(WORK, "skip.json")))
density = facts["density"]
TOP, BOTTOM, HW, H, FLOOR = 72.0, 54.0, 33.0, 48.0, 4.0
RAKE = (TOP - BOTTOM) / (H - FLOOR)

pos4 = load("bake_skip_pos")
nor4 = load("bake_skip_nor")
facts4 = load("bake_skip_facts")
ao4 = load("bake_skip_ao")
H_, W_ = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = ((pos4[..., :3] - 0.5) * 400.0).astype(np.float32)
nor = (nor4[..., :3] * 2 - 1).astype(np.float32)
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1].astype(np.float32)
del pos4, nor4, facts4
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W_ / ao.shape[1], order=1), 0, 1).astype(np.float32)
del ao4
print("loaded", cover.mean(), np.unique(finish), flush=True)

curve = np.zeros((H_, W_), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
    del dn, dp
curve[~ndi.binary_erosion(cover, iterations=1)] = 0
convex = np.clip((curve - 2.0) * 0.4, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.6) * 2.4 + ndi.gaussian_filter(convex, 4.5) * 3.0, 0, 1).astype(np.float32)
del curve, convex
rows, cols = np.nonzero(cover)
pts = pos[rows, cols]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
N = nor[rows, cols]


def field(values):
    out = np.zeros((H_, W_), np.float32)
    out[rows, cols] = values
    return out


def C(r, g, b):
    return srgb_to_linear((r, g, b)).astype(np.float32)


def flat(c):
    return np.broadcast_to(c, (H_, W_, 3))


def blend(a, b, t):
    return a + (b - a) * t[..., None]


big = field(noise(pts, 0.07, 1, 3))
mid = field(noise(pts, 0.42, 2, 4))
fine = field(noise(pts, 2.4, 3, 3))
micro = field(noise(pts, 7.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
print("fields", flush=True)

# Which side of the plate: the body's insides look at its middle and sit inside its walls.
end_at = BOTTOM + (Z - FLOOR) * RAKE
inner = ((X * nor[..., 0] + Y * nor[..., 1]) < 0) & (np.abs(Y) < HW - 0.2) & (np.abs(X) < end_at - 0.2) & (Z > FLOOR - 0.1) & (Z < H - 2.6) & (np.abs(nor[..., 2]) < 0.75)
floor_top = (nor[..., 2] > 0.75) & (Z < FLOOR + 0.8) & (np.abs(X) < BOTTOM) & (np.abs(Y) < HW)
inside = inner | floor_top
rim = Z > H - 3.05

color = np.zeros((H_, W_, 3), np.float32)
rough = np.full((H_, W_), 0.7, np.float32)
metal = np.zeros((H_, W_), np.float32)
height = np.zeros((H_, W_), np.float32)


def apply(mask, c, r, m=None, h=None):
    color[mask] = c[mask] if getattr(c, "ndim", 1) == 3 else c
    rough[mask] = r[mask] if getattr(r, "ndim", 0) == 2 else r
    if m is not None:
        metal[mask] = m[mask] if getattr(m, "ndim", 0) == 2 else m
    if h is not None:
        height[mask] = h[mask] if getattr(h, "ndim", 0) == 2 else h


rust_dark = flat(C(50, 28, 18))
rust_mid = flat(C(112, 58, 30))
rust_hot = flat(C(138, 72, 34))
rust_c = blend(blend(rust_dark, rust_mid, smooth(0.25, 0.6, mid * 0.7 + fine * 0.3)), rust_hot, smooth(0.6, 0.85, mid * 0.75 + fine * 0.25))
steel = flat(C(128, 126, 122))

# Long gouges where loads and chains have dragged, mostly level, deepest low down and at the ends' corners.
gouge_a = field(noise(pts * np.array((0.07, 0.07, 2.2), np.float32), 1.0, 21, 3))
gouge_b = field(noise(pts * np.array((0.05, 0.05, 3.4), np.float32) + 17.0, 1.0, 22, 2))
low = smooth(30.0, 6.0, Z)
gouges = smooth(0.72, 0.8, gouge_a + (mid - 0.5) * 0.25 + low * 0.06) + smooth(0.76, 0.82, gouge_b + (fine - 0.5) * 0.18)
gouges = np.clip(gouges, 0, 1)
# Impacts: blots of bare metal where something heavy landed.
impact = smooth(0.74, 0.8, field(noise(pts, 0.34, 23, 3)) + (fine - 0.5) * 0.28)
# Rust grows out of the bottom edge, under the rim and in the body's corners.
bottom_rot = smooth(14.0, 5.0, Z + (big - 0.5) * 16.0 + (mid - 0.5) * 9.0)
under_rim = smooth(H - 9.0, H - 3.5, Z + (mid - 0.5) * 7.0) * (1 - rim)
corner = smooth(10.0, 2.0, np.minimum(np.abs(np.abs(Y) - HW), np.abs(np.abs(X) - end_at)) + (mid - 0.5) * 7.0)
bloom = np.clip(bottom_rot * 0.9 + under_rim * 0.46 + corner * 0.34, 0, 1)
bloom = smooth(0.42, 0.66, bloom * 0.86 + (mid - 0.5) * 0.45 + (fine - 0.5) * 0.3)
# Streaks hang from the rim and everything else that holds water, and run with gravity.
streak = field(noise(pts * np.array((1.9, 1.9, 0.09), np.float32), 1.0, 24, 3))
fall = smooth(4.0, 26.0, H - Z)
hanging = smooth(0.56, 0.74, streak) * (1 - fall * 0.72)
print("wear", flush=True)

# --- The plate.
plate = finish == PAINT
green = flat(C(36, 92, 58))
green_lit = flat(C(68, 124, 80))
chalk = flat(C(112, 142, 112))
shade = smooth(0.2, 0.8, big) * 0.5 + smooth(0.3, 0.7, mid) * 0.5
top_coat = blend(green, green_lit, shade * 0.6)
top_coat = top_coat * (0.88 + 0.26 * part[..., None])
top_coat = blend(top_coat, chalk, smooth(0.5, 0.86, big + (mid - 0.5) * 0.4) * 0.3)
# A brushed-out patch where the fleet touched it up in a green that doesn't quite match.
patch = smooth(0.66, 0.7, field(noise(pts * np.array((0.8, 0.8, 0.5), np.float32), 0.12, 25, 1)) + (fine - 0.5) * 0.02)
top_coat = blend(top_coat, flat(C(24, 72, 44)) * (0.85 + 0.3 * fine[..., None]), patch * 0.85)
chip = edge * smooth(0.25, 0.65, mid * 0.6 + fine * 0.4) * 1.1 + (mid - 0.5) * 0.6 + (fine - 0.5) * 0.58 + (micro - 0.5) * 0.2 + bloom * 0.22 + gouges * 0.3 + impact * 0.3
to_yellow = smooth(0.62, 0.64, chip)
to_steel = np.clip(smooth(0.72, 0.74, chip) + gouges * smooth(0.28, 0.5, fine) + impact * 0.9, 0, 1)
old_yellow = flat(C(186, 146, 42)) * (0.78 + 0.4 * fine[..., None])
pit = smooth(0.35, 0.7, fine * 0.6 + mid * 0.4)
bare = blend(steel * (0.72 + 0.3 * micro[..., None]), rust_c, np.clip(pit + bloom * 0.8, 0, 1))
o_color = blend(top_coat, old_yellow, to_yellow)
o_color = blend(o_color, bare, to_steel)
o_color = blend(o_color, rust_c, bloom * 0.92)
stain = rust_c * 0.8
o_color = blend(o_color, stain, np.clip(hanging * 0.72, 0, 1) * (1 - to_steel * 0.5))
o_rough = 0.4 + 0.12 * mid + 0.22 * smooth(0.5, 0.86, big) + to_yellow * 0.14 + to_steel * (0.05 + pit * 0.42) + bloom * 0.4 + hanging * 0.22
o_metal = to_steel * (1 - np.clip(pit + bloom * 0.8, 0, 1)) * 0.95
o_height = 0.002 * (micro - 0.5) + (1 - to_yellow) * 0.012 + (1 - to_steel) * 0.01 - gouges * 0.018 - impact * 0.02 + bloom * (fine - 0.3) * 0.045

# The inside has been scoured: a little paint high up, brown steel below, gouges everywhere.
paint_left = smooth(22.0, 40.0, Z + (mid - 0.5) * 22.0 + (big - 0.5) * 12.0) * smooth(0.2, 0.5, mid + (fine - 0.5) * 0.2)
i_steel = blend(rust_c, steel * 0.55, smooth(0.5, 0.74, gouge_a + (fine - 0.5) * 0.12) * 0.75)
i_color = blend(i_steel, top_coat * 0.82, paint_left)
i_rough = 0.72 + 0.16 * fine - smooth(0.5, 0.74, gouge_a) * 0.34
i_metal = smooth(0.5, 0.74, gouge_a) * 0.8 * (1 - paint_left)
i_height = (fine - 0.5) * 0.03 - smooth(0.62, 0.74, gouge_a) * 0.03
o_color = np.where(inside[..., None], i_color, o_color)
o_rough = np.where(inside, i_rough, o_rough)
o_metal = np.where(inside, i_metal, o_metal)
o_height = np.where(inside, i_height, o_height)

# The rim's top is worn bright by chains and bars, and rust takes the rest.
worn_bright = rim & (nor[..., 2] > 0.5) & (smooth(0.36, 0.56, mid * 0.5 + fine * 0.5) > 0.4)
rim_rub = smooth(0.42, 0.62, mid * 0.75 + fine * 0.25 + edge * 0.25) * rim * (nor[..., 2] > 0.4)
o_color = blend(o_color, blend(steel * 0.95, rust_c, smooth(0.45, 0.72, mid)), rim_rub)
o_rough = o_rough * (1 - rim_rub) + (0.34 + 0.34 * fine) * rim_rub
o_metal = o_metal * (1 - rim_rub) + (1 - smooth(0.45, 0.72, mid)) * 0.9 * rim_rub
apply(plate, o_color, o_rough, o_metal, o_height)
del top_coat, o_color, o_rough, o_metal, o_height, i_color, i_rough, i_metal, i_height, i_steel, bare, stain, old_yellow, paint_left, to_yellow, worn_bright
print("plate", flush=True)

# Welds along the ribs, the corners and the lug plates: beaded, burnt and the first thing to rust.
segments = np.array(facts["welds"], np.float32)
samples = []
for a, b in segments:
    n = max(2, int(np.linalg.norm(b - a) / 0.25))
    samples.append(np.linspace(a, b, n))
samples = np.vstack(samples)
dist, nearest = cKDTree(samples).query(pts, k=1, workers=1)
near = field(dist.astype(np.float32))
bead_phase = field((nearest % 7).astype(np.float32) / 7.0)
bead = smooth(0.34, 0.08, near) * plate * ~inside
height += bead * (0.045 + 0.025 * np.sin(bead_phase * 2 * math.pi))
burn = smooth(0.95, 0.25, near) * plate * ~inside
color[...] = blend(color, color * 0.52, burn * 0.55)
color[...] = blend(color, rust_c, bead * 0.5)
rough[...] = rough + bead * 0.18
del dist, nearest, near, bead_phase, bead, burn, samples
print("welds", flush=True)

# --- Steelwork: trunnions, rings, runners. Black, and worn bright where chains go.
gear = finish == OXIDE
g_wear = smooth(0.46, 0.66, edge * 0.8 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
g_rust = smooth(0.54, 0.72, field(noise(pts, 1.1, 13, 3)) + low * 0.22 + crevice * 0.1)
g_color = flat(C(26, 26, 27)) * (0.75 + 0.5 * mid[..., None])
g_color = blend(g_color, steel * 0.85, g_wear * 0.9)
g_color = blend(g_color, rust_c, g_rust * 0.9)
apply(gear, g_color, 0.42 + 0.2 * fine - 0.12 * g_wear + 0.36 * g_rust, (1 - g_rust) * 0.9, 0.002 * (micro - 0.5) + g_rust * (fine - 0.3) * 0.03)
del g_color, g_wear, g_rust

# --- What's left inside.
bricks = finish == BRICK
b_color = blend(flat(C(146, 66, 42)), flat(C(96, 44, 30)), smooth(0.3, 0.7, mid))
b_color = b_color * (0.74 + 0.5 * part[..., None]) * (0.86 + 0.28 * fine[..., None])
b_color = blend(b_color, flat(C(150, 144, 130)), smooth(0.5, 0.7, field(noise(pts, 1.2, 31, 3))) * 0.65)
apply(bricks, b_color, 0.86, 0.0, (fine - 0.5) * 0.05 + (micro - 0.5) * 0.02)
concrete = finish == CONCRETE
k_color = flat(C(142, 138, 128)) * (0.76 + 0.44 * mid[..., None]) * (0.88 + 0.24 * micro[..., None])
apply(concrete, k_color, 0.92, 0.0, (fine - 0.5) * 0.09 + (micro - 0.5) * 0.04)
timber = finish == TIMBER
g2 = field(noise(pts * np.array((0.12, 2.8, 2.8), np.float32) + part[rows, cols][:, None] * np.array((31.0, 77.0, 13.0), np.float32), 1.0, 32, 3))
w_lines = 0.5 + 0.5 * np.sin(g2 * 24)
w_color = blend(flat(C(146, 120, 88)), flat(C(82, 62, 42)), w_lines * 0.75)
w_color = blend(w_color, flat(C(120, 116, 106)), smooth(0.4, 0.7, mid) * 0.45)
apply(timber, w_color, 0.82, 0.0, (g2 - 0.5) * 0.03)
rubber = finish == RUBBER
apply(rubber, flat(C(24, 24, 25)) * (0.8 + 0.5 * mid[..., None]), 0.85, 0.0, (fine - 0.5) * 0.02)
rebar = finish == RUST
apply(rebar, rust_c, 0.88, 0.1, (fine - 0.5) * 0.04)
del b_color, k_color, w_color, g2, w_lines
print("rubble", flush=True)

# --- Markings. Each is laid through the baked position on faces looking its way: right x up = the face's normal.
stencil_wear = smooth(0.5, 0.64, field(noise(pts, 1.1, 51, 3)) * 0.6 + fine * 0.4 + edge * 0.25)
outside_plate = plate & ~inside & ~rim


def stamp_grey(image, centre, right, up, w, h, normal, ink, worn=0.7, depth=3.0):
    c, r, u, n = (np.array(v, np.float32) for v in (centre, right, up, normal))
    d = pts - c
    uu = d @ r / w + 0.5
    vv = d @ u / h + 0.5
    keep = (uu >= 0) & (uu <= 1) & (vv >= 0) & (vv <= 1) & (np.abs(d @ n) < depth) & (N @ n > 0.55) & outside_plate[rows, cols]
    a = sample_image(image, uu[keep], vv[keep])
    ri, ci = rows[keep], cols[keep]
    a = a * (1 - stencil_wear[ri, ci] * worn) * (1 - np.clip(bloom[ri, ci] * 0.9, 0, 1))
    color[ri, ci] = color[ri, ci] + (ink - color[ri, ci]) * a[:, None]
    rough[ri, ci] = rough[ri, ci] + (0.5 - rough[ri, ci]) * a
    metal[ri, ci] = metal[ri, ci] * (1 - a)


def stamp_rgb(image, centre, right, up, w, h, normal, worn=0.6, depth=3.0):
    c, r, u, n = (np.array(v, np.float32) for v in (centre, right, up, normal))
    d = pts - c
    uu = d @ r / w + 0.5
    vv = d @ u / h + 0.5
    keep = (uu >= 0) & (uu <= 1) & (vv >= 0) & (vv <= 1) & (np.abs(d @ n) < depth) & (N @ n > 0.55) & outside_plate[rows, cols]
    ri, ci = rows[keep], cols[keep]
    samples_ = [sample_image(image[..., k], uu[keep], vv[keep]) for k in range(3)]
    rgb = srgb_to_linear(np.stack(samples_, -1) * 255.0).astype(np.float32)
    a = (1 - stencil_wear[ri, ci] * worn) * (1 - np.clip(bloom[ri, ci] * 0.95, 0, 1))
    color[ri, ci] = color[ri, ci] + (rgb - color[ri, ci]) * a[:, None]
    rough[ri, ci] = rough[ri, ci] + (0.38 - rough[ri, ci]) * a
    metal[ri, ci] = metal[ri, ci] * (1 - a)


def chevrons(size, flip):
    """Red and yellow hazard stripes, as on the ends of real road-going skips."""
    w, h = size
    img = Image.new("RGB", (w, h), (232, 192, 40))
    d = ImageDraw.Draw(img)
    pitch = h * 1.3
    x = -h * 2.0
    while x < w + h:
        if flip:
            d.polygon([(x, 0), (x + pitch / 2, 0), (x + pitch / 2 + h, h), (x + h, h)], fill=(190, 30, 24))
        else:
            d.polygon([(x + h, 0), (x + h + pitch / 2, 0), (x + pitch / 2, h), (x, h)], fill=(190, 30, 24))
        x += pitch
    return np.asarray(img, np.float32) / 255.0


cream = C(226, 224, 206)
for s in (-1, 1):
    right = (-s, 0, 0)  # The viewer's right, looking at this long side.
    n = (0, s, 0)
    y = s * 33.6
    stamp_grey(stencil_image(["TARVEN"], (1500, 340), bridge=True), (0, y, 30.0), right, (0, 0, 1), 76.0, 17.0, n, cream, 0.42)
    stamp_grey(stencil_image(["SKIP HIRE   01632 960417"], (1500, 110), bridge=False), (0, y, 17.2), right, (0, 0, 1), 76.0, 5.4, n, cream, 0.42)
    stamp_grey(stencil_image(["NR. 47"], (420, 120), bridge=False), (s * 48.0, y, 40.0), right, (0, 0, 1), 9.0, 2.5, n, cream, 0.6)
for sx in (-1, 1):
    length = math.hypot(TOP - BOTTOM, H - FLOOR)
    n = np.array((sx, 0, -RAKE), np.float32)
    n /= np.linalg.norm(n)
    up = np.array((sx * RAKE, 0, 1), np.float32)
    up /= np.linalg.norm(up)
    right = (0, sx, 0)
    # Measured up the raked face from the floor's edge.
    at = lambda along: np.array((sx * BOTTOM, 0, FLOOR), np.float32) + up * along
    stamp_rgb(chevrons((1300, 240), sx > 0), at(length - 12.0), right, up, 62.0, 11.0, n, 0.5)
    stamp_grey(stencil_image(["MAX 8 T"], (700, 150), bridge=False), at(length - 24.5), right, up, 24.0, 5.0, n, cream, 0.55)
    stamp_grey(stencil_image(["NR. 47"], (420, 120), bridge=False), at(5.5), right, up, 18.0, 5.0, n, cream, 0.6)
print("markings", flush=True)

# --- Dirt: road film rising from the ground, mortar dust on what faces up and thick on the floor.
low_film = smooth(16.0, 2.0, Z) * smooth(0.36, 0.62, field(noise(pts * np.array((0.5, 0.5, 0.24), np.float32), 1.0, 14, 4)) + (1 - Z.clip(0, 16) / 16) * 0.2)
settled = smooth(0.5, 0.92, upward * 0.8 + (big - 0.5) * 0.34 + crevice * 0.22)
dust_inside = (floor_top | (inside & (Z < 10))) * smooth(0.28, 0.6, big * 0.5 + mid * 0.5)
rubble_parts = bricks | concrete | timber | rubber | rebar
dirt = np.clip(settled * 0.3 + low_film * 0.5 + crevice * 0.1, 0, 0.8)
dirt = np.where(inside, np.clip(dust_inside * 0.72 + settled * 0.25, 0, 0.9), dirt)
dirt = np.where(rubble_parts, np.clip(settled * 0.55, 0, 0.7), dirt)
dirt_c = flat(C(128, 120, 104)) * (0.76 + 0.46 * fine[..., None])
color = blend(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.93 * dirt
metal = metal * (1 - dirt)
del settled, low_film, dirt, dirt_c, dust_inside

color = color * (0.68 + 0.32 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
# Metalness and AO don't need the full atlas, so they cost a quarter of the memory.
half = lambda a: (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), half(metal))
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), half(np.clip(ao * 1.03, 0, 1)))
print("skip painted", flush=True)
