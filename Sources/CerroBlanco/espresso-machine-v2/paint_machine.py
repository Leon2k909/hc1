"""Paint the espresso machine's maps from its bakes: python paint_machine.py <work dir> <output dir>

A busy cafe's machine, wiped down each night and used hard all day. Brushed stainless, its grain running along each panel, smudged with fingerprints round the controls and along the head's
front; polished chrome on the groups, wands and rail, a faint straw-and-blue heat tint low on the groups. Coffee grounds and dried drips on the drip tray's grate under the groups, limescale spots
on it, brown runs down the work area's back wall. Satin black handles worn glossy where they're gripped. Two gauges: the pump's, 0 to 16 bar, its needle at 9, and the boiler's, 0 to 2.5, at 1.2
with a red band at the top. Worked out in 3D from the baked position of each texel, and by part from the build's list. Values are kept strong.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

STEEL, CHROME, BLACK, RUBBER, PORCELAIN, GAUGE = 0, 3, 4, 5, 6, 7
facts_file = json.load(open(os.path.join(WORK, "machine.json")))
density, RANGE = facts_file["density"], facts_file["range"]
HALF_W, BACK_X, FRONT_X = facts_file["half_w"], facts_file["back_x"], facts_file["front_x"]
HEAD_X, HEAD_Z = facts_file["head"]
BASE_Z, TOP_Z = facts_file["base_z"], facts_file["top_z"]
GROUP_X, GROUP_Y = facts_file["group"]
TRAY_X = facts_file["tray_x"]
GAUGES = facts_file["gauges"]
NAME = "machine"
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"

pos4 = load("bake_em_pos")
nor4 = load("bake_em_nor")
facts4 = load("bake_em_facts")
ao4 = load("bake_em_ao")
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
ao = 0.35 + 0.65 * ao  # The bake reaches 3 in: deep in the work area that's too much.
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

listed = json.load(open(os.path.join(WORK, "machine_parts.json")))
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


def named(*which):
    return np.isin(part_name, which)


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NX, NY, NZ = nor[..., 0], nor[..., 1], nor[..., 2]
steel = (finish == STEEL) & cover
chrome = finish == CHROME
black = finish == BLACK
rubber = finish == RUBBER
porcelain = finish == PORCELAIN
gauge = finish == GAUGE
big = field(noise(pts, 0.15, 1, 3))
mid = field(noise(pts, 0.9, 2, 4))
fine = field(noise(pts, 5.0, 3, 3))
micro = field(noise(pts, 20.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
r = np.random.default_rng(11)

# ---- Brushed stainless: the grain runs along each panel, across the machine on its back, front and top, front to back on its sides. ----
along_x = np.abs(NY) > 0.6
c = pos[cover]
brush_y = lattice_noise(np.column_stack((c[:, 0] * 60.0, c[:, 1] * 0.6, c[:, 2] * 60.0)).astype(np.float32), 1.0, 40, 2)
brush_x = lattice_noise(np.column_stack((c[:, 0] * 0.6, c[:, 1] * 60.0, c[:, 2] * 60.0)).astype(np.float32), 1.0, 41, 2)
brushed = field(np.where(along_x[cover], brush_x, brush_y))
s_color = rgb(172, 174, 176) * (0.93 + 0.1 * brushed[..., None] + 0.04 * big[..., None])
s_rough = 0.3 + 0.1 * brushed + 0.03 * mid
# Fingerprints where hands go: round the keypads and levers, along the head's front edge, at the side panels' front corners.
hand_zone = (steel | chrome) * (smooth(4.0, 1.0, np.minimum(np.abs(np.abs(Y) - GROUP_Y), np.abs(np.abs(Y) - 11.4)) + np.abs(Z - 15.0) * 0.6) * (X > HEAD_X - 1.5)
             + smooth(2.0, 0.3, np.abs(X - (HEAD_X + 0.3))) * (np.abs(Y) > HALF_W - 1.0) * smooth(8.0, 12.0, Z))
prints = smooth(0.55, 0.75, field(noise(pts, 3.4, 42, 3))) * np.clip(hand_zone, 0, 1)
s_color = mix(s_color, s_color * 0.86, prints * 0.6)
s_rough = s_rough + prints * 0.18
# The drip tray's grate: slots across it, grounds and dried drips under the groups, limescale.
grate = named("grate") & (NZ > 0.5)
slot_u = np.mod((X - FRONT_X) / 0.55, 1.0)
slots = smooth(0.18, 0.08, np.abs(slot_u - 0.5)) * smooth(HALF_W - 2.1, HALF_W - 2.4, np.abs(Y)) * grate
under_groups = smooth(3.4, 1.4, np.minimum(np.abs(Y - GROUP_Y), np.abs(Y + GROUP_Y))) * smooth(3.5, 1.0, np.abs(X - (GROUP_X + 0.6)))
grounds = (smooth(0.62, 0.72, field(noise(pts, 9.0, 43, 2))) * (0.3 + 0.7 * under_groups) + smooth(0.75, 0.82, field(noise(pts, 14.0, 44, 1))) * 0.4) * grate
lime = smooth(0.08, 0.0, np.abs(field(noise(pts, 2.2, 45, 2)) - 0.5) - 0.06) * smooth(0.45, 0.7, mid) * grate
dried = smooth(0.4, 0.7, field(noise(pts, 1.6, 46, 3))) * under_groups * grate
s_color = mix(s_color, rgb(22, 22, 22), slots * 0.92)
s_color = mix(s_color, rgb(118, 82, 52), dried * 0.45)
s_color = mix(s_color, rgb(52, 34, 22) * (0.8 + 0.3 * micro[..., None]), np.clip(grounds, 0, 1))
s_color = mix(s_color, rgb(212, 210, 200), lime * 0.5)
s_rough = s_rough + grounds * 0.5 + lime * 0.4 + dried * 0.25
# Runs down the work area's back wall under each group.
wall = steel & (NX > 0.7) & (np.abs(X - FRONT_X) < 0.05) & (Z < HEAD_Z)
runs = np.zeros((H, W), np.float32)
for _ in range(14):
    y0 = r.choice((-GROUP_Y, GROUP_Y)) + r.normal(0, 1.4)
    w = r.uniform(0.04, 0.12)
    top = r.uniform(HEAD_Z - 4.0, HEAD_Z - 1.0)
    runs = np.maximum(runs, smooth(w, w * 0.3, np.abs(Y - y0 - 0.06 * np.sin(Z * 2.1 + y0))) * smooth(top + 0.2, top - 0.6, Z) * r.uniform(0.4, 1.0))
runs = runs * wall
s_color = mix(s_color, rgb(124, 86, 54), runs * 0.55)
s_height = 0.0008 * (brushed - 0.5) - slots * 0.03 + grounds * 0.004

# ---- Chrome: polished, a faint heat tint low on the groups, coffee round their gaskets. ----
k_color = rgb(206, 208, 212) * (0.95 + 0.06 * mid[..., None])
groups = named("group")
heat = groups * smooth(HEAD_Z - 1.0, HEAD_Z - 2.4, Z)
k_color = mix(k_color, rgb(208, 184, 140), heat[..., None] * smooth(0.3, 0.7, mid)[..., None] * 0.3)
k_color = mix(k_color, rgb(150, 160, 200), heat * smooth(HEAD_Z - 2.2, HEAD_Z - 2.6, Z) * 0.2)
residue = named("portafilter", "spout", "group") * smooth(HEAD_Z - 2.4, HEAD_Z - 3.2, Z) * smooth(0.5, 0.75, field(noise(pts, 4.0, 47, 2)))
k_color = mix(k_color, rgb(70, 46, 30), residue * 0.5)
milk = named("wand") * smooth(HEAD_Z - 5.6, HEAD_Z - 6.8, Z) * smooth(0.35, 0.65, fine)
k_color = mix(k_color, rgb(228, 224, 210), milk * 0.55)
k_prints = smooth(0.6, 0.78, field(noise(pts, 3.0, 48, 3))) * chrome
k_color = mix(k_color, k_color * 0.88, k_prints * 0.4)
k_rough = 0.05 + 0.02 * fine + k_prints * 0.12 + residue * 0.3 + milk * 0.4

# ---- Black: satin, the handles worn glossy toward their grip ends. ----
handles = named("handle")
grip = handles * smooth(GROUP_X + 4.0, GROUP_X + 7.0, X)
b_color = rgb(22, 22, 23) * (0.88 + 0.22 * fine[..., None])
b_rough = 0.42 + 0.06 * fine - grip * 0.16
# Little green lights over each keypad's buttons.
keypad = named("keypad") & (NX > 0.5)
leds = np.zeros((H, W), np.float32)
for gy in (-GROUP_Y, GROUP_Y):
    for k in range(4):
        leds = np.maximum(leds, smooth(0.09, 0.05, np.hypot(Y - (gy - 1.25 + 0.85 * k), Z - (14.6 + 0.52))))
leds = leds * keypad
b_color = mix(b_color, rgb(120, 230, 120), leds)

# ---- The gauges' dials, drawn big and sampled by position on each face. ----
PX = 300
def dial(maximum, major, minor, needle, red_from=None):
    size = int(2.24 * PX)
    img = Image.new("RGB", (size, size), (236, 234, 226))
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    start, sweep = 225.0, 270.0  # Clock degrees, clockwise from 12: from half past seven round to half past four, as gauges read.

    def clock(theta, radius):
        a = math.radians(theta)
        return cx + radius * math.sin(a), cy - radius * math.cos(a)

    def at(value, radius):
        return clock(start + sweep * value / maximum, radius)
    if red_from is not None:
        for k in range(60):
            v = red_from + (maximum - red_from) * k / 59
            x0, y0 = at(v, size * 0.4)
            d.ellipse((x0 - size * 0.018, y0 - size * 0.018, x0 + size * 0.018, y0 + size * 0.018), fill=(200, 36, 30))
    steps = int(round(maximum / minor))
    for k in range(steps + 1):
        v = k * minor
        is_major = abs(v / major - round(v / major)) < 1e-6
        r0, r1 = size * (0.36 if is_major else 0.39), size * 0.44
        d.line((*at(v, r0), *at(v, r1)), fill=(18, 18, 18), width=int(size * (0.012 if is_major else 0.006)))
        if is_major:
            font = ImageFont.truetype(FONT, int(size * 0.085))
            label = f"{v:g}"
            tx, ty = at(v, size * 0.27)
            box = d.textbbox((0, 0), label, font=font)
            d.text((tx - (box[2] - box[0]) / 2, ty - (box[3] - box[1]) / 2 - box[1]), label, fill=(18, 18, 18), font=font)
    font = ImageFont.truetype(FONT, int(size * 0.07))
    box = d.textbbox((0, 0), "BAR", font=font)
    d.text((cx - (box[2] - box[0]) / 2, cy + size * 0.16), "BAR", fill=(60, 60, 60), font=font)
    tip = at(needle, size * 0.4)
    tail = clock(start + sweep * needle / maximum + 180.0, size * 0.08)
    d.line((*tail, *tip), fill=(196, 28, 24), width=int(size * 0.016))
    d.ellipse((cx - size * 0.04, cy - size * 0.04, cx + size * 0.04, cy + size * 0.04), fill=(30, 30, 30))
    return np.asarray(img, np.float32) / 255.0


dials = (dial(16, 4, 1, 9.2), dial(2.5, 0.5, 0.1, 1.2, red_from=1.6))
g_color = np.broadcast_to(srgb_to_linear((236, 234, 226)), (H, W, 3)).copy()
face = gauge & (NX > 0.5)
for (gy, gz), img in zip(GAUGES, dials):
    uu = (Y - gy) / 2.24 + 0.5
    vv = (Z - gz) / 2.24 + 0.5
    near = face & (np.abs(Y - gy) < 1.2)
    for ch in range(3):
        sampled = sample_image(img[..., ch], uu, vv)
        g_color[..., ch] = np.where(near, srgb_to_linear(sampled * 255.0), g_color[..., ch])
g_rough = np.full((H, W), 0.5, np.float32)  # The dial itself, matte: as a gloss it mirrored the windows and washed its print out.

p_color = rgb(240, 238, 234)
color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.5, np.float32)
metal = np.zeros((H, W), np.float32)
height = 0.0004 * (micro - 0.5)
for mask, cc, ro, me, he in (
    (steel, s_color, s_rough, 1.0 - np.clip(grounds + slots + dried * 0.5 + lime * 0.6, 0, 1), s_height),
    (chrome, k_color, k_rough, 1.0 - np.clip(residue * 0.6 + milk, 0, 1), None),
    (black, b_color, b_rough, None, 0.0006 * (fine - 0.5)),
    (rubber, rgb(16, 16, 16) * (0.85 + 0.3 * fine[..., None]), 0.75, None, 0.001 * (fine - 0.5)),
    (porcelain, p_color, 0.08, None, None),
    (gauge, g_color, g_rough, None, None),
):
    color = np.where(mask[..., None], cc, color)
    rough = np.where(mask, ro, rough)
    if me is not None:
        metal = np.where(mask, me, metal)
    if he is not None:
        height = np.where(mask, he, height)

gathered = smooth(0.35, 0.8, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4) * ~gauge
color = mix(color, rgb(96, 84, 70), gathered * 0.25)
color = color * (0.75 + 0.25 * ao)[..., None]

height = fill_from(cover, height)[0]
filtered = ndi.gaussian_filter(height, 0.45)
px = np.maximum(density * weight, 1.0)
dv, du = np.gradient(filtered)
normal = np.stack((-du * px, -dv * px, np.ones_like(filtered)), -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.04, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("machine painted", flush=True)
