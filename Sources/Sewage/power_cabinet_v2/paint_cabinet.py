"""Paint the power cabinet's maps from its bakes: python paint_cabinet.py <work dir> <materials dir> cabinet

Blue-grey enamel over red oxide primer over steel, decades in a wet chamber. Wear is worked out in 3D, so it crosses UV
seams. Rust runs are drawn on a flat picture of each side, from what really sheds water (the roof edge, hinges, plates and
vents), then laid back by position. Soft thresholds throughout: hard ones read as pixels at this density.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import FONT, OUT, WORK, fill_from, load, mix, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, HAZARD, LOUVRE, DIAL, LENS_G, LENS_A, LENS_R, RED = range(16)
NAME = "power_cabinet"
facts = json.load(open(os.path.join(WORK, "cabinet.json")))
density = facts["density"]
SKIN = facts["skin"]

pos4 = load("bake_cabinet_pos")
nor4 = load("bake_cabinet_nor")
facts4 = load("bake_cabinet_facts")
ao4 = load("bake_cabinet_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
dense = facts4[..., 2] * 4.0
pos, nor, finish, part, dense = fill_from(cover, pos, nor, finish, part, dense)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
px_per_in = density * np.maximum(dense, 0.05)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 1.6) * 0.3, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.6) * 2.2 + ndi.gaussian_filter(convex, 4.0) * 2.6, 0, 1)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


big = field(noise(pts, 0.05, 1, 3))
mid = field(noise(pts, 0.3, 2, 4))
fine = field(noise(pts, 1.7, 3, 3))
micro = field(noise(pts, 7.0, 4, 2))
tall = field(noise(pts * np.array((1.0, 1.0, 0.05), np.float32), 1.1, 5, 3))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
front = nor[..., 0] > 0.7
side = np.abs(nor[..., 1]) > 0.7
back = nor[..., 0] < -0.7
upward = np.clip(nor[..., 2], 0, 1)

def rect(y0, y1, z0, z1, feather=0.0):
    a = smooth(y0 - feather, y0 + feather, Y) if feather else (Y >= y0) * 1.0
    b = smooth(y1 + feather, y1 - feather, Y) if feather else (Y <= y1) * 1.0
    c = smooth(z0 - feather, z0 + feather, Z) if feather else (Z >= z0) * 1.0
    d = smooth(z1 + feather, z1 - feather, Z) if feather else (Z <= z1) * 1.0
    return a * b * c * d


# ---- Rust runs, drawn flat. The picture is 12 px to the inch.
GRID = 12


def run_map(u0, u1, seed, sources):
    """sources: (u0, u1, z, strength) line sources; rust and water run down from each, some columns far further than others."""
    r = np.random.default_rng(seed)
    w, h = int((u1 - u0) * GRID), int(124 * GRID)
    src = np.zeros((h, w), np.float32)
    for a, b, z, s in sources:
        ia, ib, iz = int((a - u0) * GRID), int((b - u0) * GRID), int(z * GRID)
        src[np.clip(iz, 0, h - 1), max(ia, 0) : min(ib, w)] = s
    # Columns differ: most runs stop in a few inches, a few go to the floor.
    length = ndi.gaussian_filter1d(r.random(w).astype(np.float32), 1.3)
    length = (length - length.min()) / (length.max() - length.min())

    def wander(sigma):
        v = ndi.gaussian_filter1d(r.random(w).astype(np.float32), sigma)
        return (v - v.min()) / (v.max() - v.min())

    # Few and broad: a run is a finger's width, and they gather where water does. Thin ones read as pinstripes.
    weight = smooth(0.46, 0.72, wander(3.0) * 0.6 + wander(16.0) * 0.4)
    decay = 0.982 + 0.0172 * length ** 1.5
    out = np.zeros((h, w), np.float32)
    row = np.zeros(w, np.float32)
    for z in range(h - 1, -1, -1):
        row = np.maximum(row * decay, src[z] * weight)
        out[z] = row
    return ndi.gaussian_filter(out, (2.5, 0.6))


def sample_run(m, u, u0):
    return ndi.map_coordinates(m, (np.clip(Z, 0, 123.9) * GRID, np.clip(u - u0, 0, m.shape[1] / GRID - 0.01) * GRID), order=1)


edges = [(-39, 39, 113.5, 1.0)]
for y in (-36.5, -0.5, 0.5, 36.5):
    pass
hinges = [(s * 30.0, s * 37.0, z - 1.3, 1.0) if s > 0 else (s * 37.0, s * 30.0, z - 1.3, 1.0) for s in (-1, 1) for z in (23.0, 58.0, 93.0)]
vents = [(-33.8, -3.3, 32.6, 0.75), (6.5, 33.8, 32.6, 0.75)]
plates_low = [(-31.0, -6.0, 18.9, 0.7), (10.0, 31.0, 17.9, 0.7), (-31.0, -6.0, 75.9, 0.8), (10.8, 27.2, 78.4, 0.8), (3.4, 9.6, 67.9, 0.7), (3.6, 5.6, 11.0, 0.5)]
bolts = [(float(y) - 0.5, float(y) + 0.5, 111.0, 1.0) for y in np.arange(-33.0, 33.1, 11.0)]
front_runs = run_map(-40, 40, 7, edges + hinges + vents + plates_low + bolts)
side_runs = run_map(-22, 22, 8, [(-20, 20, 107.0, 1.0), (-11.5, 11.5, 14.8, 0.7), (-15, 15, 57.8, 0.6), (-15, 15, 83.8, 0.6)])
side_runs_b = run_map(-22, 22, 9, [(-20, 20, 107.0, 1.0), (-11.5, 11.5, 14.8, 0.7), (-15, 15, 57.8, 0.6), (-15, 15, 83.8, 0.6)])
runs = np.zeros((H, W), np.float32)
runs[front] = sample_run(front_runs, Y, -40)[front]
runs[side & (Y > 0)] = sample_run(side_runs, X, -22)[side & (Y > 0)]
runs[side & (Y < 0)] = sample_run(side_runs_b, X, -22)[side & (Y < 0)]
runs[back] = sample_run(side_runs, Y * 0.28, -22)[back]
runs *= 0.72 + 0.56 * fine


# ---- Flat pictures on the doors.
def stamp(image, y0, y1, z0, z1):
    """Sample a picture (rows top down) by position on the doors. Outside it, 0."""
    h, w = image.shape[:2]
    u = (Y - y0) / (y1 - y0) * (w - 1)
    v = (z1 - Z) / (z1 - z0) * (h - 1)
    if image.ndim == 2:
        return ndi.map_coordinates(image, (v, u), order=1, mode="constant")
    return np.stack([ndi.map_coordinates(image[..., c], (v, u), order=1, mode="constant") for c in range(image.shape[2])], -1)


def bold(size):
    font = ImageFont.truetype(FONT, size)
    try:
        font.set_variation_by_name("Bold Condensed")
    except Exception:
        pass
    return font


def centred(draw, text, cx, cy, size, fill):
    font = bold(size)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (box[0] + box[2]) / 2, cy - (box[1] + box[3]) / 2), text, fill=fill, font=font)


def danger_plate():
    """A yellow plate: a black triangle with a lightning bolt in it, and one word."""
    w, h = 1000, 480
    img = Image.new("RGB", (w, h), (226, 170, 26))
    d = ImageDraw.Draw(img)
    d.rectangle((12, 12, w - 13, h - 13), outline=(20, 18, 14), width=14)
    d.polygon([(70, 410), (330, 410), (200, 70)], fill=(20, 18, 14))
    d.polygon([(158, 372), (212, 268), (184, 268), (246, 170), (206, 252), (236, 252), (168, 372)], fill=(226, 170, 26))
    centred(d, "DANGER", 660, 170, 190, (20, 18, 14))
    centred(d, "440 VOLTS", 660, 350, 130, (20, 18, 14))
    return np.asarray(img, np.float32) / 255.0


def supply_plate():
    w, h = 840, 420
    img = Image.new("RGB", (w, h), (210, 204, 180))
    d = ImageDraw.Draw(img)
    d.rectangle((12, 12, w - 13, h - 13), outline=(36, 36, 34), width=8)
    centred(d, "MAIN SUPPLY", w / 2, 130, 130, (28, 28, 26))
    centred(d, "ISOLATE BEFORE OPENING", w / 2, 300, 72, (28, 28, 26))
    return np.asarray(img, np.float32) / 255.0


def switch_plate():
    w, h = 656, 840
    img = Image.new("RGB", (w, h), (226, 170, 26))
    d = ImageDraw.Draw(img)
    d.rectangle((10, 10, w - 11, h - 11), outline=(20, 18, 14), width=10)
    centred(d, "ON", w * 0.76, 170, 120, (20, 18, 14))
    centred(d, "OFF", w * 0.24, 680, 120, (20, 18, 14))
    centred(d, "MAIN", w / 2, 92, 72, (20, 18, 14))
    return np.asarray(img, np.float32) / 255.0


# ---- Enamel over primer over steel.
low = smooth(46.0, 0.0, Z)
right_door = np.isin(finish, (PAINT, LOUVRE, PLATE)) & (nor[..., 0] > 0.3) & (X > 17.0) & (Y > 0.0) & (Z > 8.0) & (Z < 107.5)
shifted = pts + np.array((0.0, 0.0, 37.0), np.float32)
big_door = np.where(right_door, field(noise(shifted, 0.05, 1, 3)), big)
mid_door = np.where(right_door, field(noise(shifted, 0.3, 2, 4)), mid)
# The stencilling is kept readable: rust eats round it, not through all of it.
lettering = (rect(-33.0, -5.0, 66.5, 76.5, 2.0) + rect(11.0, 33.0, 66.5, 76.5, 2.0)) * (nor[..., 0] > 0.7)
chip = (
    edge * smooth(0.28, 0.66, mid * 0.6 + fine * 0.4) * 0.5
    + (big_door - 0.5) * 0.8
    + (mid_door - 0.5) * 0.74
    - lettering * 0.2
    + (fine - 0.5) * 0.4
    + (micro - 0.5) * 0.16
    + low * 0.16
    + runs * 0.16
)
# The noises sum to about 0 with a spread of about 0.16, so these leave about a third of the paint broken.
to_rust = smooth(0.1, 0.19, chip)
to_primer = smooth(0.055, 0.11, chip)
rust_tone = smooth(0.3, 0.72, field(noise(pts, 0.9, 8, 3)))
rust_c = mix(rgb(70, 34, 18), rgb(150, 76, 32), rust_tone) * (0.78 + 0.44 * micro[..., None])
primer = rgb(138, 60, 42) * (0.86 + 0.28 * fine[..., None])
enamel = rgb(56, 72, 80)
faded = rgb(84, 100, 104)
fade = smooth(0.34, 0.74, tall * 0.7 + big * 0.3) * 0.55
stain = rgb(60, 44, 32)

part_tint = 0.93 + 0.14 * part[..., None]
paint = mix(enamel * part_tint, faded, fade)
paint = paint * (0.93 + 0.14 * fine[..., None])
# Water and rust run down the paint, staining it long before it breaks through.
paint = mix(paint, rgb(88, 48, 26), np.clip(runs * 0.9, 0, 0.86))
paint = mix(paint, stain, smooth(0.52, 0.86, tall + low * 0.26) * 0.42)

# Stencilled lettering, sprayed on and worn back with the paint.
door_paint = (finish == PAINT) & front
text_mask = stamp(stencil_image(["MCC 1"], (640, 200), bridge=False), -32.0, -6.0, 67.8, 75.0)
text_mask += stamp(stencil_image(["440 V"], (560, 200), bridge=False), 12.0, 32.0, 67.8, 75.0)
text_mask = np.clip(text_mask, 0, 1) * door_paint * (1 - smooth(0.68, 0.84, (fine - 0.5) * 0.9 + (mid - 0.5) * 0.7 + 0.5)) * 0.8
paint = mix(paint, rgb(176, 172, 150), text_mask)

color = mix(paint, primer, to_primer)
color = mix(color, rust_c, to_rust)
rough = 0.46 + 0.14 * mid + fade * 0.24 + runs * 0.16
rough = rough * (1 - to_primer) + (0.66 + 0.1 * fine) * to_primer
rough = rough * (1 - to_rust) + (0.82 + 0.14 * fine) * to_rust
metal = np.zeros((H, W), np.float32)
glow = np.zeros((H, W), np.float32)
# The door's pressed pan, stopping short of its edges, and a paint film that rust has lifted.
pan = rect(-34.8, -2.3, 9.5, 106.0, 0.22) + rect(2.3, 34.8, 9.5, 106.0, 0.22)
height = (1 - to_primer) * 0.012 + to_rust * (0.014 + 0.03 * micro + 0.02 * fine) + 0.0012 * (micro - 0.5) + door_paint * pan * 0.13

# Bare steel where the paint has rubbed through on an edge, or round the handle.
hand = smooth(9.0, 2.0, np.hypot(Y - 4.6, Z - 75.5)) * front
bare = smooth(0.62, 0.84, edge * 0.72 + (fine - 0.5) * 0.6 + hand * 0.42 * smooth(0.3, 0.7, mid)) * (1 - to_rust)
steel = rgb(150, 152, 150) * (0.72 + 0.4 * fine[..., None])
color = mix(color, steel, bare)
rough = rough * (1 - bare) + 0.42 * bare
metal = metal + bare * 0.68

# ---- The other finishes, each replacing the paint where it's used.
plinth = finish == HAZARD
u = np.where(np.abs(nor[..., 0]) > 0.7, Y, X)
stripe = 0.5 + 0.5 * np.sin((u + Z) * math.pi / 4.0)
stripe = smooth(0.42, 0.58, stripe)
haz = mix(rgb(16, 16, 15), rgb(226, 160, 22), stripe)
haz = mix(haz, rgb(120, 92, 40), smooth(0.4, 0.7, fine * 0.5 + mid * 0.5) * 0.35)
haz = mix(haz, primer, smooth(0.03, 0.09, chip))
haz = mix(haz, rust_c, smooth(0.07, 0.16, chip))
color = np.where(plinth[..., None], haz, color)

vent = finish == LOUVRE
v_chip = chip + 0.06 + edge * 0.18
v_rust = smooth(0.07, 0.16, v_chip)
v_color = mix(mix(mix(enamel, faded, fade) * 0.9, rgb(88, 48, 26), np.clip(runs * 0.9, 0, 0.86)), rust_c, v_rust)
v_color = mix(v_color, steel, smooth(0.66, 0.84, edge * 0.8 + (fine - 0.5) * 0.5) * (1 - v_rust))
color = np.where(vent[..., None], v_color, color)
rough = np.where(vent, 0.5 + 0.36 * v_rust, rough)
height = np.where(vent, v_rust * (0.014 + 0.018 * micro), height)

zinc = finish == ZINC
z_rust = smooth(0.62, 0.76, fine * 0.5 + mid * 0.3 + crevice * 0.3 + runs * 0.2)
color = np.where(zinc[..., None], mix(rgb(150, 152, 148) * (0.72 + 0.4 * fine[..., None]), rust_c, z_rust), color)
rough = np.where(zinc, 0.38 + 0.2 * fine + 0.4 * z_rust, rough)
metal = np.where(zinc, 0.68 * (1 - z_rust), metal)

galv = finish == GALV
g_rust = smooth(0.56, 0.7, mid * 0.5 + fine * 0.28 + big * 0.2 + low * 0.16 + crevice * 0.3)
g_color = mix(rgb(132, 136, 132), rgb(86, 90, 88), smooth(0.3, 0.7, tall))
g_color = g_color * (0.84 + 0.32 * fine[..., None])
color = np.where(galv[..., None], mix(g_color, rust_c, g_rust), color)
rough = np.where(galv, 0.44 + 0.2 * mid + 0.34 * g_rust, rough)
metal = np.where(galv, 0.66 * (1 - g_rust), metal)
height = np.where(galv, g_rust * (0.012 + 0.016 * micro), height)

iron = (finish == OXIDE) | (finish == WELD)
i_wear = smooth(0.46, 0.66, edge * 0.82 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
i_rust = smooth(0.54, 0.7, mid * 0.45 + fine * 0.3 + big * 0.15 + crevice * 0.34 + low * 0.1)
i_color = mix(rgb(50, 50, 48) * (0.8 + 0.4 * mid[..., None]), rgb(146, 146, 142), i_wear * 0.8)
i_color = mix(i_color, rust_c, i_rust)
color = np.where(iron[..., None], i_color, color)
rough = np.where(iron, 0.48 + 0.2 * fine + 0.3 * i_rust, rough)
metal = np.where(iron, (0.3 + 0.38 * i_wear) * (1 - i_rust), metal)
height = np.where(iron, i_rust * (0.012 + 0.016 * micro), height)

brass = finish == BRASS
b_color = mix(rgb(112, 92, 54), rgb(196, 160, 92), smooth(0.36, 0.72, edge * 0.6 + (mid - 0.5) * 0.7 + 0.3))
b_color = mix(b_color, rgb(88, 108, 84), smooth(0.66, 0.84, mid * 0.6 + crevice * 0.4) * 0.5)
color = np.where(brass[..., None], b_color, color)
rough = np.where(brass, 0.4 + 0.24 * fine, rough)
metal = np.where(brass, 0.66, metal)

dark = finish == RUBBER
mesh = 0.5 + 0.5 * np.sin(Y * math.pi / 0.42) * np.sin(Z * math.pi / 0.42)
color = np.where(dark[..., None], rgb(14, 14, 14) * (0.6 + 0.5 * mesh[..., None]), color)
rough = np.where(dark, 0.86, rough)
metal = np.where(dark, 0.0, metal)
height = np.where(dark, 0.004 * mesh, height)

red = finish == RED
r_wear = smooth(0.5, 0.68, edge * 0.8 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
r_color = mix(rgb(176, 30, 20) * (0.86 + 0.28 * mid[..., None]), rgb(150, 150, 146), r_wear * 0.7)
color = np.where(red[..., None], r_color, color)
rough = np.where(red, 0.36 + 0.2 * mid + 0.1 * r_wear, rough)
metal = np.where(red, 0.6 * r_wear, metal)

# Plates: the instrument panel is black crackle; the rest are enamel pictures, chipped at their edges.
plate = finish == PLATE
facing = plate & front
p_color = rgb(40, 44, 46) * (0.82 + 0.36 * micro[..., None])
p_chip = smooth(0.44, 0.56, edge * 0.7 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.7 + (big - 0.5) * 0.4 + crevice * 0.1)
for picture, y0, y1, z0, z1 in (
    (danger_plate(), -31.0, -6.0, 19.0, 31.0),
    (supply_plate(), 10.0, 31.0, 18.0, 28.5),
    (switch_plate(), 10.8, 27.2, 78.5, 99.5),
):
    inside = rect(y0, y1, z0, z1)[..., None]
    img = stamp(picture ** 2.2, y0, y1, z0, z1)
    img = img * (0.8 + 0.3 * mid[..., None])
    p_color = p_color * (1 - inside) + img * inside
# Rust runs over the plates from what's above them, and grime gathers round their edges.
p_color = mix(p_color, mix(rgb(100, 56, 30), rust_c, 0.5), np.clip(runs * 0.75, 0, 0.75))
p_color = mix(p_color, rgb(46, 40, 30), smooth(0.3, 0.72, crevice + (mid - 0.5) * 1.0 + (big - 0.5) * 0.8) * 0.72)
p_color = mix(p_color, mix(rgb(140, 140, 136), rust_c, smooth(0.4, 0.7, mid)), p_chip)
color = np.where(plate[..., None], p_color, color)
rough = np.where(plate, 0.34 + 0.2 * mid + 0.34 * p_chip, rough)
metal = np.where(plate, 0.0, metal)
height = np.where(plate, 0.002 * (micro - 0.5) + p_chip * 0.006, height)

# Meter dials: cream, a scale of ticks with a red end, and a needle.
dial = finish == DIAL
d_color = rgb(214, 204, 170).copy()
d_glow = np.zeros((H, W), np.float32)
R = facts["gauge_r"]
for index, (gy, gz) in enumerate(facts["gauges"]):
    here = dial & (np.hypot(Y - gy, Z - gz) < R + 0.3)
    r = np.hypot(Y - gy, Z - gz) / R
    a = np.degrees(np.arctan2(Z - gz, Y - gy))
    # The scale runs clockwise from lower left to lower right, through the top.
    sweep = (225.0 - a) % 360.0
    inside = sweep < 270.0
    tick_minor = (np.abs(((sweep + 7.5) % 15.0) - 7.5) < 1.1) & (r > 0.76) & (r < 0.86)
    tick_major = (np.abs(((sweep + 22.5) % 45.0) - 22.5) < 1.7) & (r > 0.68) & (r < 0.86)
    arc = (r > 0.86) & (r < 0.9)
    ink = (tick_minor | tick_major | arc) & inside
    red_zone = (sweep > 205.0) & inside & (r > 0.74) & (r < 0.9)
    needle_at = [172.0, 96.0][index]
    off = (sweep - needle_at + 180.0) % 360.0 - 180.0
    needle = (np.abs(off) * np.pi / 180.0 * np.maximum(r, 0.06) * R < 0.055 + 0.04 * (1 - r)) & (r < 0.86)
    picture = np.where(ink[..., None], np.array((0.012, 0.012, 0.012), np.float32), d_color)
    picture = np.where(red_zone[..., None], np.array((0.5, 0.025, 0.015), np.float32), picture)
    picture = np.where(needle[..., None], np.array((0.01, 0.01, 0.01), np.float32), picture)
    d_color = np.where(here[..., None], picture, d_color)
d_color = mix(d_color, rgb(120, 92, 54), smooth(0.35, 0.75, mid * 0.6 + big * 0.4) * 0.55)
color = np.where(dial[..., None], d_color, color)
rough = np.where(dial, 0.22, rough)
metal = np.where(dial, 0.0, metal)
height = np.where(dial, 0.0, height)
glow = np.where(dial, 0.05, glow)

# Lit lenses glow; the green is the one lit. Glass stays clean enough to read.
for f, tint, lit in ((LENS_G, (40, 255, 90), 1.0), (LENS_A, (255, 150, 30), 0.14), (LENS_R, (255, 36, 20), 0.14)):
    lens = finish == f
    color = np.where(lens[..., None], rgb(*tint), color)
    rough = np.where(lens, 0.16, rough)
    metal = np.where(lens, 0.0, metal)
    height = np.where(lens, 0.0, height)
    glow = np.where(lens, lit, glow)
# A small green push button can't glow as the lamp does: it's only lens-coloured by being lit, and it isn't.

# ---- Dirt: damp grime rising from the floor in streaks, dust on what faces up.
solidish = ~(np.isin(finish, (DIAL, LENS_G, LENS_A, LENS_R)))
rising = smooth(34.0, 2.0, Z + (tall - 0.5) * 34.0) * (0.45 + 0.55 * smooth(0.3, 0.7, tall))
settled = smooth(0.42, 0.9, upward * 0.86 + (big - 0.5) * 0.3 + crevice * 0.22)
dirt = np.clip(rising * 0.5 + settled * 0.5 + crevice * 0.1, 0, 0.72) * solidish
dirt_c = rgb(52, 48, 38) * (0.75 + 0.5 * fine[..., None])
color = mix(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.86 * dirt
metal = metal * (1 - dirt)

color = color * (0.68 + 0.32 * ao[..., None])
solid = ndi.binary_erosion(cover, iterations=1)
height = fill_from(solid, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), px_per_in, 1.0)
color, rough, metal, normal, glow = fill_from(solid, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal, glow)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_gray(os.path.join(OUT, f"{NAME}_glow.png"), glow)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("cabinet painted, base density %.1f px/in" % density, flush=True)
