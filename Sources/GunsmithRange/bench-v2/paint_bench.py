"""Paint the shooting bench's maps from its bakes: python paint_bench.py <work dir> <output dir>

A bench that thousands of rounds have gone over, kept in order. Oiled oak from the old bench's own source photos, a shade different stave by stave and
kept even: darkened by hands and oil where people lean, scored by magazines and sooted along its downrange edge, with a stencil going off it. A powder-coated
frame, chipped at its edges and kicked bare low down on the shooter's side. A ribbed rubber mat, canvas rests, olive ammo cans, brass, and one orange sign.
Wear is worked out in 3D and its masks kept soft: hard-edged chips read as pixels at this density in s&box. Paint dark colours darker than looks right.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

FRAME, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE = 0, 2, 3, 4, 5, 6, 7
CARTON, OAK, MAT, CANVAS, OLIVE, ORANGE = 9, 11, 12, 13, 14, 15
facts_file = json.load(open(os.path.join(WORK, "bench.json")))
density, RANGE, HL, HD, TOP, BOTTOM = (facts_file[k] for k in ("density", "range", "half_length", "half_depth", "top", "bottom"))
STAVES, STAVE, GAP = (facts_file[k] for k in ("staves", "stave", "gap"))
NAME = "bench"

pos4 = load("bake_rb_pos")
nor4 = load("bake_rb_nor")
facts4 = load("bake_rb_facts")
ao4 = load("bake_rb_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
weight = facts4[..., 2]
pos, nor, finish, part, weight = fill_from(cover, pos, nor, finish, part, weight)
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


def soft(mask, sigma=0.6):
    return ndi.gaussian_filter(mask.astype(np.float32), sigma)


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
oak = finish == OAK
frame_ = finish == FRAME
oxide = finish == OXIDE
zinc = finish == ZINC
brass = finish == BRASS
rubber = finish == RUBBER
weld = finish == WELD
plate = finish == PLATE
mat = finish == MAT
canvas = finish == CANVAS
olive = finish == OLIVE
orange = finish == ORANGE
carton = finish == CARTON
upward = np.clip(nor[..., 2], 0, 1)

edge_points = np.load(os.path.join(WORK, "bench_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=1.2, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 1.2).astype(np.float32))
edge = smooth(0.38, 0.03, edge_d)
print("edges", flush=True)

big = field(noise(pts, 0.05, 1, 3))
mid = field(noise(pts, 0.35, 2, 4))
fine = field(noise(pts, 2.0, 3, 3))
micro = field(noise(pts, 7.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)


# ---- The oak, from the old bench's own photographs. ----
def linear_image(path):
    return srgb_to_linear(np.asarray(Image.open(path).convert("RGB"), np.float32))


source = os.path.join(ROOT, "Sources", "GunsmithRange", "bench")
long_grain = linear_image(os.path.join(source, "oak_longgrain_source.png"))
end_grain = linear_image(os.path.join(source, "oak_endgrain_source.png"))


def sample_rgb(image, rows, cols):
    return np.stack([ndi.map_coordinates(image[..., c], (rows, cols), order=1, mode="mirror") for c in range(3)], -1)


stave_of = np.clip(np.floor((X + HD) / (STAVE + GAP)).astype(np.int32), 0, STAVES - 1)
r = np.random.default_rng(61)
across_shift = r.uniform(0, 1254, STAVES)
along_shift = r.uniform(0, 1254, STAVES)
flip = r.choice((-1.0, 1.0), STAVES)
tone_of = np.array((0.97, 1.05, 0.93, 1.02, 0.96, 1.06), np.float32)

oak_tex = np.where(oak)
ox, oy, oz = X[oak_tex], Y[oak_tex], Z[oak_tex]
nx, ny, nz = np.abs(nor[..., 0][oak_tex]), np.abs(nor[..., 1][oak_tex]), np.abs(nor[..., 2][oak_tex])
k = stave_of[oak_tex]
# A stave's face gets a run of 4.9 inches of the photo, wider on the page than along its length as a real board's figure is.
PX_ACROSS, PX_ALONG = 1254 / 26.0, 1254 / 74.0
across = np.where(nz >= nx, ox, oz * 1.0)
cols = (across * PX_ACROSS + across_shift[k]) * 1.0
rows = (oy * flip[k] * PX_ALONG + along_shift[k]) * 1.0
wood = sample_rgb(long_grain, rows, cols)
ends = ny > np.maximum(nx, nz)
if ends.any():
    e_cols = (ox[ends] - (-HD + k[ends] * (STAVE + GAP))) / STAVE * 620.0 + k[ends] * 90.0
    e_rows = (oz[ends] - BOTTOM) / (TOP - BOTTOM) * 450.0 + k[ends] * 55.0
    wood[ends] = sample_rgb(end_grain, e_rows, e_cols)
# Oiled: deeper and warmer than the bare photo, and still even from stave to stave.
luma = (wood @ np.array((0.2126, 0.7152, 0.0722), np.float32))[:, None]
wood = luma + (wood - luma) * 1.28
wood = np.clip(wood, 0, 1) ** 1.14 * 0.82 * tone_of[k][:, None] * np.array((1.0, 0.95, 0.87), np.float32)
timber = np.zeros((H, W, 3), np.float32)
timber[oak_tex] = wood
grain_height = np.zeros((H, W), np.float32)
grain_height[oak_tex] = (luma[:, 0] - ndi.gaussian_filter(np.zeros(1), 1)[0]).astype(np.float32)
fine_grain = grain_height - ndi.gaussian_filter(grain_height, 5.0)

# Worked out over the top. Where people lean: two forearms' worth, either side of the mat, on the shooter's edge. Their hands and sleeves take the oil on and polish it.
leaning = oak * upward * smooth(8.5, 1.0, np.abs(X + 11.0)) * np.maximum(smooth(13.0, 3.0, np.abs(Y - 40.0)), smooth(13.0, 3.0, np.abs(Y + 40.0)) * 0.7) * (0.7 + 0.3 * smooth(0.3, 0.7, big))
front_rub = oak * smooth(2.2, 0.0, X + HD) * (0.55 + 0.45 * mid)

# Soot along the downrange edge, from muzzles held over it, in a fan where the rests are.
blast = oak * upward * smooth(4.2, 15.2, X) * smooth(26.0, 3.0, np.abs(Y)) * (0.55 + 0.45 * smooth(0.25, 0.75, mid))
soot = oak * upward * smooth(9.5, 15.0, X) * smooth(0.46, 0.8, big * 0.45 + mid * 0.55)

# Scored by magazines and tools: long light scratches, mostly along the boards, some across.
rs = np.random.default_rng(7)
lines3, widths, depth = [], [], []
for _ in range(340):
    x0, y0 = rs.uniform(-14.5, 14.5), rs.uniform(-83.0, 83.0)
    length = float(rs.uniform(0.8, 7.5))
    w = float(rs.uniform(0.035, 0.085))
    turn = rs.normal(0.0, 0.45) if rs.random() < 0.72 else rs.normal(math.pi / 2, 0.5)
    steps = max(4, int(length / 0.05))
    for j in range(steps):
        f = j / (steps - 1)
        lines3.append((x0 + math.sin(turn) * (f - 0.5) * length, y0 + math.cos(turn) * (f - 0.5) * length, TOP - 0.01))
        widths.append(w * (1 - abs(f - 0.5) * 1.3))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines3, np.float32)).query(pts, k=1, distance_upper_bound=0.16, workers=4)
which = np.minimum(which, len(widths) - 1)
scratch = soft(field(smooth(1.0, 0.35, np.where(np.isfinite(dist), dist, 1.0) / widths[which]).astype(np.float32)), 0.6) * oak * upward
print("scratches", flush=True)

# Dings on the shooter's edge and dents here and there on the top.
rd = np.random.default_rng(23)
dents = np.column_stack((rd.uniform(-15.0, 15.0, 90), rd.uniform(-84.0, 84.0, 90), np.full(90, TOP)))
dents[:40, 0] = rd.uniform(-15.0, -13.2, 40)
dist, which = cKDTree(dents).query(pts, k=1, distance_upper_bound=0.8, workers=4)
ding_size = rd.uniform(0.18, 0.5, 90)
which = np.minimum(which, 89)
ding = field(smooth(1.0, 0.2, np.where(np.isfinite(dist), dist, 9.0) / ding_size[which]).astype(np.float32)) * oak

# Cups, and oil.
ring = np.zeros((H, W), np.float32)
for cx, cy, cr in ((-8.5, 52.5, 1.55), (9.0, -28.5, 1.45), (-7.0, 69.0, 1.6)):
    ring = np.maximum(ring, smooth(0.14, 0.04, np.abs(np.hypot(X - cx, Y - cy) - cr + (fine - 0.5) * 0.1)) * smooth(0.25, 0.6, field(noise(pts, 1.0, 26, 2))))
ring = ring * oak * upward
oil = np.zeros((H, W), np.float32)
for cx, cy, rx, ry in ((-5.5, -58.0, 5.0, 8.0), (-6.0, -33.0, 4.0, 5.0), (7.5, 34.0, 4.5, 7.0), (2.0, 72.0, 5.0, 6.0)):
    oil = np.maximum(oil, smooth(1.0, 0.25, np.hypot((X - cx) / rx, (Y - cy) / ry) + (mid - 0.5) * 0.45))
oil = oil * oak * upward

# A faded stencil on the top: DOWNRANGE and an arrow, either side of the mat, read from the shooter's place.
words = stencil_image(["DOWNRANGE"], (1400, 300), bridge=False)
stencil = np.zeros((H, W), np.float32)
for y_mid in (-66.0, 66.0):
    uu = (y_mid + 14.0 - Y) / 28.0
    vv = (X + 11.0) / 5.0
    stencil = np.maximum(stencil, sample_image(words, uu, vv))
    # Arrowhead and shaft, pointing +X.
    cy = np.abs(Y - y_mid)
    arrow = np.maximum((X > -5.0) * (X < 1.0) * (cy < 1.1), (X >= 1.0) * (X < 6.0) * (cy < (6.0 - X) * 0.82))
    stencil = np.maximum(stencil, arrow.astype(np.float32))
stencil = soft(stencil, 0.8) * oak * (nor[..., 2] > 0.7)
paint_left = smooth(0.26, 0.56, mid * 0.4 + fine * 0.3 + big * 0.3 + np.where(np.abs(X + 8.0) < 7.0, 0.02, 0.0))
stencil = stencil * paint_left * (1 - 0.35 * smooth(0.45, 0.75, micro)) * (1 - leaning * 0.5)

timber = timber * (0.965 + 0.07 * big[..., None])
timber = mix(timber, timber * 0.62, np.clip(leaning * 0.5 + front_rub * 0.15, 0, 1))
timber = mix(timber, timber * 0.72, oil * 0.75)
timber = mix(timber, timber * 0.42 + rgb(16, 15, 14) * 0.25, np.clip(blast * 0.42 + soot * 0.5, 0, 0.8))
# The eased edges rub back paler; the scratches show the pale wood under the oil.
pale = rgb(196, 158, 112) * (0.84 + 0.26 * fine[..., None])
outer = np.maximum(smooth(HD - 1.0, HD - 0.05, np.abs(X)), smooth(HL - 1.0, HL - 0.05, np.abs(Y)))
timber = mix(timber, pale, np.clip(soft(smooth(0.42, 0.74, outer * edge * (0.45 + 0.55 * smooth(0.25, 0.7, fine)) + outer * front_rub * 0.24 + (micro - 0.5) * 0.15), 0.7) * 0.72, 0, 0.8))
timber = mix(timber, pale * 0.92, np.clip(scratch * 0.55, 0, 1))
timber = mix(timber, timber * 0.56, ring * 0.7)
timber = mix(timber, timber * 0.7, ding * 0.55)
timber = mix(timber, rgb(186, 182, 170) * (0.72 + 0.34 * fine[..., None]), stencil * 0.58)
t_rough = 0.42 + 0.08 * mid + 0.14 * np.clip(fine_grain * 8.0, -0.5, 0.5) - leaning * 0.16 - oil * 0.14 + blast * 0.22 + soot * 0.2 + scratch * 0.26 + ring * 0.16 + outer * edge * 0.12 + stencil * 0.12
t_height = np.clip(fine_grain, -0.25, 0.25) * 0.05 - scratch * 0.006 - ding * 0.03 + stencil * 0.0018

# ---- The frame: dark powder coat, chipped at its edges and kicked low on the shooter's side. ----
kicks = frame_ * smooth(8.0, 1.0, Z) * smooth(-2.0, -11.5, X) * smooth(0.3, 0.72, mid * 0.5 + fine * 0.5)
boots = frame_ * upward * (np.abs(Z - 12.5) < 1.2) * smooth(0.28, 0.7, mid)
# Chips come in patches along an edge, not in a line down the whole of it.
patches = smooth(0.46, 0.72, field(noise(pts, 0.2, 41, 3)))
f_chip = soft(smooth(0.36, 0.62, edge * patches * (0.45 + 0.55 * smooth(0.3, 0.7, fine)) + kicks * 0.42 + boots * 0.26 + (fine - 0.5) * 0.14), 0.7) * frame_
f_color = rgb(34, 50, 74) * (0.88 + 0.24 * mid[..., None])
bare = rgb(126, 124, 120) * (0.72 + 0.4 * fine[..., None])
rust_c = mix(rgb(70, 40, 24), rgb(118, 70, 40), smooth(0.35, 0.8, field(noise(pts, 3.1, 8, 3))))
rust = frame_ * soft(smooth(0.6, 0.88, crevice * 0.5 + field(noise(pts, 0.9, 9, 3)) * 0.55 + f_chip * 0.3 + smooth(10.0, 0.0, Z) * 0.14), 0.8)
f_color = mix(f_color, bare, f_chip)
f_color = mix(f_color, rust_c, rust * 0.7)
f_rough = 0.44 + 0.1 * mid + 0.06 * fine + rust * 0.36 - f_chip * 0.06
f_metal = 0.06 + f_chip * 0.62 * (1 - rust)

# ---- Blacked steel: the tray and the small ironwork. ----
o_wear = soft(smooth(0.42, 0.7, edge * smooth(0.35, 0.7, mid) + (fine - 0.5) * 0.3), 0.6)
o_color = mix(rgb(24, 24, 26) * (0.8 + 0.4 * mid[..., None]), rgb(120, 118, 114), o_wear * 0.8)
o_rough = 0.62 + 0.14 * fine - 0.16 * o_wear
o_metal = 0.12 + 0.5 * o_wear

# ---- Rubber mat: near-black with a diamond tread, a plain bound border, stitched. Worn smooth and pale in the middle. ----
M_X, M_Y, HX, HY = -4.0, 0.0, 9.2, 28.0
inset = np.minimum(HX - np.abs(X - M_X), HY - np.abs(Y - M_Y))
tread_on = smooth(0.85, 1.05, inset)
P = 0.7
d1, d2 = np.abs(((X + Y) / P) % 1.0 - 0.5) * 2, np.abs(((X - Y) / P) % 1.0 - 0.5) * 2
groove = np.maximum(smooth(0.68, 0.9, d1), smooth(0.68, 0.9, d2))
m_used = mat * smooth(0.2, 0.75, smooth(23.0, 5.0, np.abs(Y)) * smooth(9.0, 1.0, np.abs(X + 4.0)) * 0.72 + (mid - 0.5) * 0.3)
m_color = rgb(40, 44, 40) * (0.9 + 0.2 * mid[..., None])
m_color = mix(m_color, rgb(70, 72, 66) * (0.88 + 0.2 * fine[..., None]), m_used * 0.6)
m_color = mix(m_color, rgb(10, 11, 10), groove[..., None] * tread_on[..., None] * (1 - m_used[..., None] * 0.45) * 0.85)
along = np.where(HX - np.abs(X - M_X) < HY - np.abs(Y - M_Y), Y, X)
stitch = mat * smooth(0.075, 0.035, np.abs(inset - 0.42)) * (np.mod(along / 0.42, 1.0) < 0.62)
m_color = mix(m_color, rgb(150, 146, 128), stitch * 0.8)
m_rough = 0.8 - m_used * 0.2 + 0.05 * fine
m_height = (1 - groove) * tread_on * 0.03 * (1 - m_used * 0.55) + stitch * 0.004

# ---- Canvas: an even tan, a plain coarse weave, puckered in to its piped seam and a little lumpy over the sand. ----
period = 0.19
weave_a = 0.5 + 0.5 * np.sin((X * 0.92 + Y * 0.39) * 2 * math.pi / period)
weave_b = 0.5 + 0.5 * np.sin((Y * 0.92 - X * 0.39 + Z * 0.7) * 2 * math.pi / period)
weave = weave_a * 0.5 + weave_b * 0.5
pucker = np.zeros((H, W), np.float32)
piping = np.zeros((H, W), np.float32)
for bag in facts_file["bags"]:
    ux, uy = (X - bag["x"]) / (bag["lx"] / 2), (Y - bag["y"]) / (bag["ly"] / 2)
    near = (np.abs(ux) < 1.15) & (np.abs(uy) < 1.15) & (np.abs(Z - bag["z"]) < 6.0) & canvas
    turn = np.arctan2(uy, ux)
    pucker = np.where(near, np.sin(turn * 46.0 + (mid - 0.5) * 9.0) * smooth(0.55, 0.97, np.hypot(ux, uy)) * smooth(2.4, 0.3, np.abs(Z - bag["z"])), pucker)
    piping = np.where(near, np.maximum(piping, smooth(0.2, 0.1, np.abs(Z - bag["z"]))), piping)
lumps = field(noise(pts, 0.9, 51, 2))
c_color = rgb(136, 116, 80) * (0.95 + 0.08 * mid[..., None]) * (0.86 + 0.2 * weave[..., None])
c_color = mix(c_color, rgb(72, 62, 44), np.clip(piping * 0.65 + (pucker < -0.15) * np.abs(pucker) * 0.4, 0, 1))
c_color = mix(c_color, c_color * 0.62, crevice[..., None] * 0.3)
c_rough = 0.88 - 0.05 * weave
c_height = weave * 0.009 + 0.05 * (lumps - 0.5) + pucker * 0.035

# ---- Ammo cans: olive enamel with yellow stencils, chipped at their corners. ----
a_chip = soft(smooth(0.52, 0.76, edge * (0.3 + 0.55 * smooth(0.3, 0.7, fine)) + (fine - 0.5) * 0.25), 0.6) * olive
a_color = rgb(52, 62, 34) * (0.88 + 0.26 * mid[..., None])
a_print = np.zeros((H, W), np.float32)
for can in facts_file["cans"]:
    img = stencil_image(list(can["text"]), (760, 420), bridge=False)
    # Read from the shooter's side, -X, so left on the page is +Y.
    uu = (can["y"] + 3.0 - Y) / 6.0
    vv = (Z - (can["z"] + 1.1)) / 3.4
    a_print = np.maximum(a_print, sample_image(img, uu, vv) * (nor[..., 0] < -0.7) * (X < can["x"]) * (np.abs(X - can["x"]) < can["hx"] + 0.3))
a_print = soft(a_print, 0.55) * olive * smooth(0.2, 0.42, mid * 0.5 + fine * 0.5)
a_color = mix(a_color, rgb(208, 176, 72) * (0.86 + 0.2 * fine[..., None]), a_print * 0.92)
a_color = mix(a_color, rgb(138, 138, 128) * (0.75 + 0.35 * fine[..., None]), a_chip)
a_rough = 0.5 + 0.12 * mid + a_print * 0.1 - a_chip * 0.1
a_metal = a_chip * 0.62

# ---- The sign: safety orange enamel on steel, with the firing line's own colour, black lettering. ----
sign_text = stencil_image(["FIRING POINT"], (1400, 170), bridge=False)
p = facts_file["plates"][0]
s_print = sample_image(sign_text, (p["y1"] - 0.8 - Y) / (p["y1"] - p["y0"] - 1.6), (Z - p["z0"] - 0.35) / (p["z1"] - p["z0"] - 0.7)) * (nor[..., 0] < -0.7)
s_print = soft(s_print, 0.45) * plate
s_chip = soft(smooth(0.54, 0.76, edge * 0.5 + (fine - 0.5) * 0.4 + (mid - 0.5) * 0.3), 0.6) * plate
s_color = rgb(226, 88, 20) * (0.88 + 0.2 * mid[..., None])
s_color = mix(s_color, rgb(10, 10, 10), s_print * (0.92 - 0.25 * s_chip))
s_color = mix(s_color, rgb(136, 134, 128), s_chip * 0.85)
s_rough = 0.42 + 0.14 * mid + s_print * 0.1
s_metal = s_chip * 0.62

# ---- The carton: printed card, red with a white band, soft at its corners. ----
carton_text = stencil_image(["5.56 MM"], (760, 240), bridge=False)
k_print = soft(sample_image(carton_text, (-38.8 - Y) / 2.4, (X + 8.6) / 5.4) * (nor[..., 2] > 0.7), 0.45) * carton
k_band = carton * smooth(0.12, 0.05, np.abs(X + 8.9) - 0.42)
k_wear = soft(smooth(0.42, 0.72, edge * smooth(0.3, 0.7, mid) + (fine - 0.5) * 0.3), 0.7) * carton
k_color = rgb(168, 36, 26) * (0.92 + 0.16 * mid[..., None])
k_color = mix(k_color, rgb(226, 220, 204), k_band)
k_color = mix(k_color, rgb(232, 226, 210), k_print)
k_color = mix(k_color, rgb(176, 154, 118), k_wear * 0.8)
k_rough = 0.66 + 0.08 * fine

# ---- Everything else. ----
b_tarnish = smooth(0.35, 0.75, mid * 0.6 + fine * 0.4)
b_color = mix(rgb(214, 170, 96), rgb(144, 106, 54), b_tarnish * 0.75)
e_color = rgb(232, 96, 18) * (0.9 + 0.16 * mid[..., None])
e_color = mix(e_color, rgb(92, 40, 16), crevice[..., None] * 0.35)
z_color = rgb(146, 144, 136) * (0.72 + 0.36 * mid[..., None])
r_color = rgb(14, 14, 15) * (0.9 + 0.3 * fine[..., None])
w_color = mix(rgb(26, 30, 34), rgb(70, 70, 70), smooth(0.4, 0.75, fine))

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = 0.0014 * (micro - 0.5) + 0.0012 * (fine - 0.5)
for mask, c, ro, me, he in (
    (oak, timber, t_rough, None, t_height),
    (frame_, f_color, f_rough, f_metal, 0.0016 * (micro - 0.5) + 0.002 * (fine - 0.5) + (1 - f_chip) * 0.0035 + rust * 0.006),
    (oxide, o_color, o_rough, o_metal, None),
    (mat, m_color, m_rough, None, m_height),
    (canvas, c_color, c_rough, None, c_height),
    (olive, a_color, a_rough, a_metal, 0.0016 * (fine - 0.5) + (1 - a_chip) * 0.0035),
    (plate, s_color, s_rough, s_metal, (1 - s_chip) * 0.003),
    (brass, b_color, 0.3 + 0.28 * b_tarnish, 0.68 * np.ones((H, W), np.float32), None),
    (orange, e_color, 0.44 + 0.08 * fine, None, 0.002 * (fine - 0.5)),
    (carton, k_color, k_rough, None, 0.002 * (fine - 0.5)),
    (zinc, z_color, 0.38 + 0.2 * mid, 0.62 * np.ones((H, W), np.float32), None),
    (rubber, r_color, 0.82 + 0.1 * fine, None, 0.004 * (micro - 0.5)),
    (weld, w_color, 0.62, 0.3 * np.ones((H, W), np.float32), 0.008 * (micro - 0.5)),
):
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, ro, rough)
    if me is not None:
        metal = np.where(mask, me, metal)
    if he is not None:
        height = np.where(mask, he, height)

# Dust gathers on what faces up and in the corners, more on the frame than on a top that's wiped.
gathered = smooth(0.15, 0.62, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4)
settled = (frame_ | olive | oxide) * upward * smooth(0.3, 0.7, big * 0.5 + mid * 0.5)
low = smooth(4.0, 0.2, Z) * frame_
grime = np.clip(gathered * 0.42 + settled * 0.3 + low * smooth(0.3, 0.7, fine) * 0.42, 0, 0.72)
grime = grime * (1 - oak * 0.6) * (1 - orange * 0.8) * (1 - plate * 0.7) * (1 - carton * 0.7)
color = mix(color, rgb(66, 60, 52) * (0.8 + 0.4 * fine[..., None]), grime)
rough = rough * (1 - grime * 0.6) + 0.84 * grime * 0.6
metal = metal * (1 - grime)
color = color * (0.66 + 0.34 * ao[..., None])

height = fill_from(cover, height)[0]
filtered = ndi.gaussian_filter(height, 0.5)
px = np.maximum(density * weight, 1.0)
dv, du = np.gradient(filtered)
normal = np.stack((-du * px, -dv * px, np.ones_like(filtered)), -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border takes its normal from just inside.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("bench painted", flush=True)
