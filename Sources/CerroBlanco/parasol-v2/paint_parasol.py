"""Paint the parasol's maps from its bakes: python paint_parasol.py <work dir> <output dir>

A museum courtyard's cafe parasol, a few summers out. The canopy is ecru solution-dyed acrylic: its top sun-faded and filmed with city dirt, which rain has carried down each gore's middle and along
the seams to the hem; the underside cleaner, rubbed grey beside the ribs and spotted with mildew near the hem. Felled seams over the ribs and hem stitching are in the height. Tension wrinkles fan in
from the corner tips, and storage creases run down the gores. Edges, valance foot and piping are bound in anthracite. The frame is anthracite powder coat with a few chips to bare aluminium and the
runner's scuffs on the pole; the base is black textured powder coat on cast iron, kicked at its rim, gritty on top, with its weight cast in. Values are kept strong. Worked out in 3D from the baked
position of each texel, and by part from the build's list.
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
from scipy.spatial import cKDTree  # noqa: E402

CANVAS, POWDER, CAST, NYLON, STEEL, ROPE, BINDING = range(7)
facts_file = json.load(open(os.path.join(WORK, "parasol.json")))
density, RANGE = facts_file["density"], facts_file["range"]
HALF = facts_file["half"]
TIP_CORNER, TIP_SIDE = facts_file["tip_z"]
VALANCE = facts_file["valance"]
RUN_Z = facts_file["run_z"]
BASE_R = facts_file["base_r"]
SAG, SCALLOP, THICK = 0.85, 1.05, 0.025
NAME = "parasol"
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"

pos4 = load("bake_ps_pos")
nor4 = load("bake_ps_nor")
facts4 = load("bake_ps_facts")
ao4 = load("bake_ps_ao")
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
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

# Which part each texel is on, from the build's list.
listed = json.load(open(os.path.join(WORK, "parasol_parts.json")))
rands = np.array([r for r, _, _ in listed], np.float32)
order = np.argsort(rands)
names = np.array([n for _, n, _ in listed])[order]
at = np.clip(np.searchsorted(rands[order], part), 1, len(rands) - 1)
nearer = np.where(np.abs(rands[order][at - 1] - part) < np.abs(rands[order][at] - part), at - 1, at)
part_name = names[nearer]


def named(*which):
    return np.isin(part_name, which)


TURN = np.array(((0.70, -0.42, 0.58), (0.61, 0.77, -0.19), (-0.37, 0.48, 0.79)), np.float32)


def noise(p, freq, seed=0, octaves=1):
    return lattice_noise(p @ TURN, freq, seed, octaves)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


def soft(mask, sigma=0.5):
    return ndi.gaussian_filter(mask.astype(np.float32), sigma)


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NZ = nor[..., 2]
RHO = np.hypot(X, Y)
THETA = np.mod(np.arctan2(Y, X), 2 * np.pi)
canvas = (finish == CANVAS) & cover
powder = finish == POWDER
cast = finish == CAST
nylon = finish == NYLON
steel = finish == STEEL
rope = finish == ROPE
binding = finish == BINDING
canopy = canvas & named("canvas")
valance = canvas & named("valance")
vent = canvas & named("vent")
pocket = canvas & named("pocket")
strap = canvas & named("strap")
top = (canopy | vent) & (NZ > 0.3)
under = (canopy | vent) & (NZ < -0.3)
vent_drop = vent & (np.abs(NZ) <= 0.3)
outward = (nor[..., 0] * X + nor[..., 1] * Y) > 0
upward = np.clip(NZ, 0, 1)

# ---- Where a texel is on the canopy: its gore, how far across it, how far from the nearest rib line, and from the hem. ----
G = THETA / (np.pi / 4)
GORE = np.floor(G)
V = G - GORE
D_SEAM = RHO * np.minimum(V, 1 - V) * (np.pi / 4)
AX, AY = np.abs(X), np.abs(Y)
on_x = AX >= AY
along_half = np.where(on_x, AY, AX) / HALF
D_EDGE = HALF - np.where(on_x, AX, AY) - SCALLOP * np.sin(np.pi * np.clip(along_half, 0, 1))
# The hem's height along each side, and how far down the valance a texel hangs.
HEM_Z = (TIP_SIDE - 0.35) + (TIP_CORNER - TIP_SIDE) * along_half + THICK - SAG * np.sin(np.pi * np.clip(along_half, 0, 1)) - 0.12
DROP = HEM_Z - Z


big = field(noise(pts, 0.05, 1, 3))
mid = field(noise(pts, 0.35, 2, 4))
fine = field(noise(pts, 2.2, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)

# ---- The cloth. ----
# Each gore is cut with its warp down its middle, so the grain turns at every seam.
MID_ANGLE = (GORE + 0.5) * np.pi / 4
DOWN = X * np.cos(MID_ANGLE) + Y * np.sin(MID_ANGLE)
ACROSS = -X * np.sin(MID_ANGLE) + Y * np.cos(MID_ANGLE)
grain_a = field(lattice_noise(np.column_stack((DOWN[cover] * 0.5, ACROSS[cover] * 6.0, GORE[cover] * 7.0)).astype(np.float32), 1.0, 20, 2))
grain_b = field(lattice_noise(np.column_stack((DOWN[cover] * 6.0, ACROSS[cover] * 0.5, GORE[cover] * 7.0)).astype(np.float32), 1.0, 21, 2))
# The valance's grain runs across and down it instead.
ALONG = np.where(on_x, Y, X)
v_grain_a = field(lattice_noise(np.column_stack((ALONG[cover] * 0.5, Z[cover] * 6.0, RHO[cover] * 0.1)).astype(np.float32), 1.0, 22, 2))
v_grain_b = field(lattice_noise(np.column_stack((ALONG[cover] * 6.0, Z[cover] * 0.5, RHO[cover] * 0.1)).astype(np.float32), 1.0, 23, 2))
flat_cloth = canopy | vent | pocket | strap
grain = np.where(flat_cloth, grain_a * 0.5 + grain_b * 0.5, v_grain_a * 0.5 + v_grain_b * 0.5)

# Seams over every rib, felled, with two rows of stitching; the hem's fold and its row.
seam = smooth(0.44, 0.34, D_SEAM) * (canopy | vent | pocket)
stitch_rows = smooth(0.06, 0.0, np.abs(D_SEAM - 0.27)) * (canopy | vent) * (RHO > 5.0)
dashes = smooth(0.25, 0.65, 0.5 + 0.5 * np.sin(2 * np.pi * RHO / 0.24))
stitches = stitch_rows * dashes
hem = smooth(1.3, 1.15, D_EDGE) * canopy
hem_row = smooth(0.06, 0.0, np.abs(D_EDGE - 0.95)) * canopy * smooth(0.25, 0.65, 0.5 + 0.5 * np.sin(2 * np.pi * (RHO * THETA) / 0.24))
# The valance's top seam under the piping, and its bound foot with a row through the binding.
v_top_row = smooth(0.06, 0.0, np.abs(DROP - 0.9)) * valance * smooth(0.25, 0.65, 0.5 + 0.5 * np.sin(2 * np.pi * ALONG / 0.24))
v_binding = smooth(VALANCE - 0.82, VALANCE - 0.74, DROP) * valance
v_binding_row = smooth(0.05, 0.0, np.abs(DROP - (VALANCE - 0.42))) * valance * smooth(0.25, 0.65, 0.5 + 0.5 * np.sin(2 * np.pi * ALONG / 0.22))
vent_drop_binding = vent_drop & (Z < 98.9 - 1.3 + 0.38)

# Tension wrinkles fanning in from each tip, the corners' longest, and creases from the canopy being furled.
wrinkle = np.zeros((H, W), np.float32)
for k in range(8):
    a = k * np.pi / 4
    corner = k % 2 == 1
    reach = HALF * (math.sqrt(2) if corner else 1.0)
    tx, ty = reach * math.cos(a), reach * math.sin(a)
    dx, dy = X - tx, Y - ty
    L = np.hypot(dx, dy)
    phi = np.arctan2(-(dx * math.sin(a) - dy * math.cos(a)), -(dx * math.cos(a) + dy * math.sin(a)))
    span = 0.42 if corner else 0.3
    length = 15.0 if corner else 8.0
    wobble = field(noise(pts, 0.6, 30 + k, 2)) - 0.5
    ridges = np.sin(phi * (44 if corner else 36) + wobble * 2.5)
    fade = smooth(length, 2.0, L) * smooth(0.4, 1.8, L) * smooth(span, span * 0.4, np.abs(phi))
    wrinkle += ridges * fade * (0.035 if corner else 0.02)
r = np.random.default_rng(77)
crease = np.zeros((H, W), np.float32)
crease_fade = 0.5 + 0.5 * smooth(0.3, 0.7, field(noise(pts, 0.2, 60, 2)))
for k in range(8):
    for _ in range(3):
        th = (k + r.uniform(0.15, 0.85)) * np.pi / 4
        d = RHO * np.abs(np.mod(THETA - th + np.pi, 2 * np.pi) - np.pi)
        sign = 1.0 if r.uniform() < 0.5 else -1.0
        crease += sign * np.exp(-(d / 0.09) ** 2) * smooth(6.0, 14.0, RHO) * crease_fade * 0.014
fold_fade = smooth(0.3, 0.6, field(noise(pts, 0.15, 70, 2)))
for _ in range(5):
    zc = 84.0 - r.uniform(1.8, 6.6)
    crease += (1.0 if r.uniform() < 0.5 else -1.0) * np.exp(-((Z - zc) / 0.07) ** 2) * valance * 0.01 * fold_fade
wrinkle = wrinkle * (canopy | vent)
crease = crease * (canopy | valance | vent)

ecru = rgb(205, 190, 160) * (0.94 + 0.1 * big[..., None] + 0.05 * mid[..., None])
c_color = ecru * (0.96 + 0.08 * grain[..., None])
# The top: sun-faded lighter and greyer, then filmed with city dirt, which rain carries down each gore's middle and along the seams, and leaves along the hem.
c_color = mix(c_color, rgb(214, 207, 188) * (0.95 + 0.08 * big[..., None]), top * 0.5)
film = smooth(0.3, 0.75, big * 0.5 + mid * 0.5) * top
# Streaks run straight down the slope, so they are keyed to the angle round the pole (192 cells round, three turns of the lattice, so no seam) and change slowly with distance.
streak_noise = field(lattice_noise(np.column_stack((THETA[cover] * (192.0 / (2 * np.pi)), RHO[cover] * 0.05, np.zeros(cover.sum()))).astype(np.float32), 1.0, 40, 3))
valley = 0.4 + 0.6 * np.sin(np.pi * np.clip(V, 0, 1)) ** 2
streaks = smooth(0.5, 0.78, streak_noise * 0.8 + mid * 0.3) * valley * smooth(6.0, 30.0, RHO) * top
seam_dirt = smooth(0.7, 0.2, D_SEAM) * top * (0.4 + 0.6 * smooth(0.35, 0.7, mid))
hem_tide = smooth(4.5, 0.8, D_EDGE) * top * (0.5 + 0.5 * smooth(0.3, 0.7, fine))
tide_line = smooth(0.18, 0.0, np.abs(D_EDGE - (3.0 + 1.2 * (mid - 0.5)))) * top
stains = np.zeros((H, W), np.float32)
for _ in range(6):
    sx, sy = r.uniform(-34, 34), r.uniform(-34, 34)
    rad = r.uniform(0.6, 1.6)
    d = np.hypot(X - sx, Y - sy) / rad + (fine - 0.5) * 0.5
    stains = np.maximum(stains, (smooth(1.0, 0.75, d) * 0.4 + smooth(0.14, 0.0, np.abs(d - 0.95)) * 0.6))
stains = stains * top
dirt = rgb(112, 101, 82)
c_color = mix(c_color, dirt * (0.9 + 0.2 * fine[..., None]), np.clip(film * 0.14 + streaks * 0.2 + seam_dirt * 0.22 + hem_tide * 0.24 + tide_line * 0.2, 0, 0.5))
c_color = mix(c_color, rgb(150, 118, 78), stains * 0.32)
# The underside: rubbed grey beside each rib, mildew spotting near the hem, a little dirtier round the pockets.
rub = smooth(0.12, 0.0, np.abs(D_SEAM - 0.36)) * under * smooth(8.0, 14.0, RHO) * (0.4 + 0.6 * smooth(0.3, 0.7, fine))
spots_raw = field(noise(pts, 3.2, 50, 2))
mildew = smooth(0.84, 0.9, spots_raw + smooth(0.0, 5.0, D_EDGE) * -0.12 + (mid - 0.5) * 0.2) * smooth(5.0, 0.5, D_EDGE)
mildew = mildew * (under | (valance & ~outward)) + smooth(0.87, 0.93, spots_raw) * (valance & ~outward) * smooth(3.0, 7.0, DROP)
c_color = mix(c_color, rgb(124, 120, 110), rub * 0.4)
c_color = mix(c_color, rgb(84, 86, 72), np.clip(mildew, 0, 1) * 0.35)
c_color = mix(c_color, dirt, (pocket | strap) * (0.18 + 0.2 * smooth(0.3, 0.7, mid)))
# The valance outside: dirt run down from the hem in streaks, and tide marks over its foot.
v_streak_noise = field(lattice_noise(np.column_stack((ALONG[cover] * 1.6, Z[cover] * 0.08, RHO[cover] * 0.02)).astype(np.float32), 1.0, 41, 3))
v_streaks = smooth(0.52, 0.8, v_streak_noise * 0.8 + mid * 0.3) * smooth(0.5, 2.5, DROP) * valance * outward
v_tide = (smooth(0.16, 0.0, np.abs(DROP - (VALANCE - 1.9 + 0.6 * (mid - 0.5)))) * 0.7 + smooth(VALANCE - 2.0, VALANCE - 0.8, DROP) * 0.35) * valance
c_color = mix(c_color, dirt * (0.9 + 0.2 * fine[..., None]), np.clip(v_streaks * 0.38 + v_tide * 0.32 + valance * outward * 0.08, 0, 0.8))
# Thread, a shade darker than the cloth where it sinks in.
thread = np.clip(stitches * 0.9 + hem_row + v_top_row + v_binding_row * 0.5, 0, 1)
c_color = mix(c_color, c_color * 0.72, thread * 0.55)
# The binding tape at the valance's foot and the vent's drop.
bind = np.clip(v_binding + vent_drop_binding, 0, 1)
anthracite = rgb(46, 48, 51) * (0.92 + 0.14 * grain[..., None])
c_color = mix(c_color, anthracite, bind)
c_rough = 0.94 + 0.04 * grain - thread * 0.04 + film * 0.02 - bind * 0.05
c_height = 0.0014 * (grain - 0.5) + 0.012 * seam + 0.008 * hem - 0.006 * stitches - 0.004 * hem_row + wrinkle + crease - 0.004 * v_top_row + 0.006 * bind - 0.004 * v_binding_row
c_metal = np.zeros((H, W), np.float32)

# ---- Anthracite powder coat on aluminium: orange peel, a few chips at its edges, the runner's scuffs and hands on the pole. ----
edge_points = np.load(os.path.join(WORK, "parasol_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=0.4, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 0.4).astype(np.float32))
edge = smooth(0.1, 0.01, edge_d)
print("edges", flush=True)
peel = field(noise(pts, 6.0, 44, 2))
chip_raw = edge * smooth(0.55, 0.8, mid) * (0.5 + 0.5 * smooth(0.3, 0.7, fine)) + (micro - 0.5) * 0.06
chips = soft(smooth(0.44, 0.56, chip_raw), 0.35) * (powder | cast)
pole = named("pole")
runner_zone = pole * smooth(RUN_Z - 9.0, RUN_Z - 4.0, Z) * smooth(RUN_Z + 3.4, RUN_Z + 2.6, Z)
# Round the pole without a seam: x and y scaled up, z stretched out, so the lines run down it.
scuff_lines = smooth(0.62, 0.86, field(lattice_noise(np.column_stack((X[cover] * 3.0, Y[cover] * 3.0, Z[cover] * 0.12)).astype(np.float32), 1.0, 45, 2)))
scuffs = runner_zone * scuff_lines
hands = pole * smooth(36.0, 44.0, Z) * smooth(62.0, 54.0, Z) * (0.5 + 0.5 * smooth(0.3, 0.7, mid))
p_color = rgb(50, 52, 56) * (0.94 + 0.08 * big[..., None] + 0.04 * fine[..., None])
p_color = mix(p_color, rgb(64, 66, 70), scuffs * 0.6)
p_color = mix(p_color, p_color * 0.8, hands * 0.35)
alu = rgb(168, 170, 174) * (0.85 + 0.2 * fine[..., None])
p_color = mix(p_color, alu, chips * powder)
p_rough = 0.46 + 0.05 * mid + 0.03 * fine - scuffs * 0.18 - hands * 0.12 - chips * 0.12
p_metal = chips * 0.92
p_height = 0.0011 * (peel - 0.5) - chips * 0.003 - scuffs * 0.0005

# ---- The base: black textured coat on cast iron, kicked at the rim, rusting a little at its chips, gritty on top, its weight cast in. ----
sand = field(noise(pts, 14.0, 46, 2))
on_base = named("base")
rim_kicks = soft(smooth(0.5, 0.64, edge * smooth(1.9, 1.2, Z) * smooth(0.3, 0.7, mid) + (fine - 0.5) * 0.12), 0.4) * on_base
cast_chips = np.maximum(chips * cast * 0.6, rim_kicks)
rust_ring = soft(cast_chips, 2.0) * smooth(0.35, 0.75, fine) * cast
iron = rgb(80, 78, 76) * (0.85 + 0.25 * fine[..., None])
b_color = rgb(27, 27, 29) * (0.92 + 0.12 * big[..., None] + 0.06 * sand[..., None])
b_color = mix(b_color, rgb(98, 54, 30), np.clip(rust_ring * 0.5, 0, 1))
b_color = mix(b_color, mix(iron, rgb(110, 62, 34), smooth(0.5, 0.8, micro)[..., None] * 0.5), cast_chips)
# The cast lettering on the dome, its tops rubbed to iron.
PX = 200
lw, lh = int(6.0 * PX), int(1.6 * PX)
canvas_img = Image.new("L", (lw, lh), 0)
draw = ImageDraw.Draw(canvas_img)
font = ImageFont.truetype(FONT, int(1.05 * PX))
try:
    font.set_variation_by_name("Bold")
except Exception:
    pass
box = draw.textbbox((0, 0), "25 KG", font=font)
draw.text(((lw - (box[2] - box[0])) / 2 - box[0], (lh - (box[3] - box[1])) / 2 - box[1]), "25 KG", 255, font=font)
letters_img = ndi.gaussian_filter(np.asarray(canvas_img, np.float32) / 255.0, 2.0)
# Read round the dome: the letters sit on a band at radius 6.5, across -y.
uu = (X + 3.0) / 6.0
vv = (Y + 7.3) / 1.6
letters = sample_image(letters_img, uu, vv) * on_base * (NZ > 0.4) * (RHO > 4.0)
letter_top = smooth(0.7, 0.95, letters)
b_color = mix(b_color, iron * 0.85, letter_top * 0.35)
grit = smooth(0.3, 0.75, mid * 0.6 + fine * 0.4) * upward * (Z < 5.8) * (cast | nylon)
grit = np.clip(grit * 0.6 + smooth(4.0, 2.6, RHO) * (Z < 3.7) * cast * 0.5 + crevice * 0.3 * cast, 0, 1)
lime = smooth(0.12, 0.0, np.abs(RHO - (7.6 + 1.4 * (mid - 0.5)))) * upward * on_base * 0.5
b_color = mix(b_color, rgb(124, 114, 96) * (0.8 + 0.4 * fine[..., None]), grit * 0.55)
b_color = mix(b_color, rgb(150, 146, 136), lime * 0.4)
b_rough = 0.62 + 0.06 * sand + grit * 0.15 - cast_chips * 0.1 - letter_top * 0.15
b_metal = cast_chips * 0.75 + letter_top * 0.2
b_height = 0.0035 * (sand - 0.5) + 0.06 * letters - cast_chips * 0.004

# ---- Small parts. ----
n_color = rgb(22, 22, 23) * (0.85 + 0.3 * fine[..., None])
n_scuff = smooth(0.5, 0.8, edge + (fine - 0.5) * 0.4)
n_color = mix(n_color, rgb(48, 48, 48), n_scuff * 0.5)
s_color = rgb(160, 160, 157) * (0.86 + 0.2 * fine[..., None])
r_color = rgb(204, 199, 184) * (0.92 + 0.12 * fine[..., None])
r_handled = np.clip(smooth(0.3, 0.75, mid) * 0.4 + smooth(49.0, 47.0, Z) * smooth(39.0, 41.0, Z) * 0.35, 0, 1)
r_color = mix(r_color, rgb(150, 140, 120), r_handled)
braid = 0.5 + 0.5 * np.sin((X + Y) * 2 * np.pi / 0.3 + Z * 2 * np.pi / 0.3)
k_color = rgb(46, 48, 51) * (0.9 + 0.16 * grain[..., None])
k_color = mix(k_color, dirt * 0.6, smooth(0.4, 0.75, mid) * 0.15)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = 0.0005 * (micro - 0.5)
for mask, c, ro, me, he in (
    (canvas, c_color, c_rough, c_metal, c_height),
    (powder, p_color, p_rough, p_metal, p_height),
    (cast, b_color, b_rough, b_metal, b_height),
    (nylon, n_color, 0.55 - n_scuff * 0.12, None, 0.0008 * (fine - 0.5)),
    (steel, s_color, 0.28 + 0.12 * fine, np.ones((H, W), np.float32) * 0.95, None),
    (rope, r_color, 0.82, None, 0.004 * braid),
    (binding, k_color, 0.8 + 0.05 * grain, None, 0.0012 * (grain - 0.5)),
):
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, ro, rough)
    if me is not None:
        metal = np.where(mask, me, metal)
    if he is not None:
        height = np.where(mask, he, height)

# Dust in the frame's crevices and on what faces up out of the rain's way; contact shadow from the bake.
gathered = smooth(0.3, 0.75, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4) * (powder | nylon | steel)
color = mix(color, rgb(104, 98, 86), gathered * 0.35)
rough = rough * (1 - gathered * 0.4) + 0.85 * gathered * 0.4
metal = metal * (1 - gathered * 0.6)
color = color * (np.where(canvas, 0.8, 0.66) + np.where(canvas, 0.2, 0.34) * ao)[..., None]

height = fill_from(cover, height)[0]
filtered = ndi.gaussian_filter(height, 0.45)
px = np.maximum(density * weight, 1.0)
dv, du = np.gradient(filtered)
normal = np.stack((-du * px, -dv * px, np.ones_like(filtered)), -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("parasol painted", flush=True)
