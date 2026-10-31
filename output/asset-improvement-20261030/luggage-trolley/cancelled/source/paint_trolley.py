"""Paint the trolley's maps from its bakes: python paint_trolley.py <work dir> <materials dir> trolley

Railway green enamel over red oxide over steel, chipped on real edges and rusting under its fasteners. Rough-sawn crates, a
weathered deck, a fibre trunk, an aluminium flight case, hard suitcases with travel stickers, a canvas roll. Wear is worked
out in 3D from each texel's baked position and normal, so it runs across UV seams. Every word on it is made up or plain
German: "rhv" is the made-up operator Railhead's trains already carry.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, CASE, ROPE, BOARD, GRAIN_X, GRAIN_Y, GRAIN_Z, CANVAS, STRAP, LABEL, LINER, AMBER, BRACE = range(19)
NAME = "luggage_trolley"
BOLD = os.path.join(ROOT, "Assets", "fonts", "Dinish-Bold.ttf")
REGULAR = os.path.join(ROOT, "Assets", "fonts", "Dinish-Regular.ttf")
facts = json.load(open(os.path.join(WORK, "trolley.json")))
density = facts["density"]

pos4 = load("bake_trolley_pos")
nor4 = load("bake_trolley_nor")
facts4 = load("bake_trolley_facts")
ao4 = load("bake_trolley_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = ((pos4[..., :3] - 0.5) * 400.0).astype(np.float32)
nor = (nor4[..., :3] * 2 - 1).astype(np.float32)
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1].astype(np.float32)
del pos4, nor4
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
del facts4
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1).astype(np.float32)
del ao4
print("loaded", cover.mean(), np.unique(finish), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
    del dn, dp
curve[~ndi.binary_erosion(cover, iterations=1)] = 0
convex = np.clip((curve - 2.2) * 0.38, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.6) * 2.4 + ndi.gaussian_filter(convex, 4.0) * 3.0, 0, 1).astype(np.float32)
del curve, convex
rows, cols = np.nonzero(cover)
pts = pos[rows, cols]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[rows, cols] = values
    return out


big = field(noise(pts, 0.08, 1, 3))
mid = field(noise(pts, 0.5, 2, 4))
fine = field(noise(pts, 2.6, 3, 3))
micro = field(noise(pts, 8.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
print("fields", flush=True)


def C(r, g, b):
    return srgb_to_linear((r, g, b)).astype(np.float32)


def blend(a, b, t):
    return a + (b - a) * t[..., None]


def inside(lo, hi):
    return (X >= lo[0]) & (X <= hi[0]) & (Y >= lo[1]) & (Y <= hi[1]) & (Z >= lo[2]) & (Z <= hi[2])


color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.7, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)


def apply(mask, c, r, m=None, h=None):
    color[mask] = c[mask] if getattr(c, "ndim", 1) == 3 else c
    rough[mask] = r[mask] if getattr(r, "ndim", 0) == 2 else r
    if m is not None:
        metal[mask] = m[mask] if getattr(m, "ndim", 0) == 2 else m
    if h is not None:
        height[mask] = h[mask] if getattr(h, "ndim", 0) == 2 else h


# --- Fasteners: where they rust from, and their domes. Only what's on the model's own surfaces gets them.
rv = np.array(facts["rivets"], np.float32)
nl = np.array(facts["nails"], np.float32)
studs = np.vstack((rv, np.column_stack((nl, np.full(len(nl), 0.13, np.float32)))))
tree = cKDTree(studs[:, :3])
dist, which = tree.query(pts, k=1, workers=1)
stud_r = field(studs[which, 3])
stud_d = field(dist.astype(np.float32))
stud_on = stud_d < stud_r
dome = np.sqrt(np.clip(1 - (stud_d / np.maximum(stud_r, 1e-3)) ** 2, 0, 1)) * stud_r * 0.42 * stud_on
stretched = cKDTree(studs[:, :3] * np.array((1, 1, 0.16), np.float32))
d2, w2 = stretched.query(pts * np.array((1, 1, 0.16), np.float32), k=1, workers=1)
below = pts[:, 2] < studs[w2, 2] + 0.05
vertical = np.abs(nor[rows, cols, 2]) < 0.5
run = field(smooth(0.42, 0.06, d2) * below * vertical)
run = run * smooth(0.25, 0.7, mid)
halo = smooth(0.42, 0.12, stud_d) * (1 - stud_on)
del d2, w2, stretched, tree, dist, which, below, vertical
print("studs", flush=True)

rust_c = blend(np.broadcast_to(C(58, 34, 22), (H, W, 3)), np.broadcast_to(C(116, 66, 38), (H, W, 3)), smooth(0.35, 0.8, fine))
steel = np.broadcast_to(C(138, 138, 134), (H, W, 3))

# --- Wood. Each texel knows which way its timber's grain runs; every board gets its own stretch of the tree.
woods = np.isin(finish, (BOARD, GRAIN_X, GRAIN_Y, GRAIN_Z, BRACE))
wr, wc = np.nonzero(woods & cover)
wp = pos[wr, wc]
gdir = np.zeros_like(wp)
wf = finish[wr, wc]
gdir[wf == GRAIN_X] = (1, 0, 0)
gdir[(wf == GRAIN_Y) | (wf == BOARD)] = (0, 1, 0)
gdir[wf == GRAIN_Z] = (0, 0, 1)
wparts = part[wr, wc]
for rand, direction in facts["grains"].items():
    pick = (wf == BRACE) & (np.abs(wparts - float(rand)) < 1e-4)
    gdir[pick] = direction
gdir[np.linalg.norm(gdir, axis=1) < 0.5] = (1, 0, 0)
along = (wp * gdir).sum(1, keepdims=True)
perp = wp - along * gdir
offset = wparts[:, None] * np.array((131.0, 57.0, 91.0), np.float32)


def wood_field(values):
    out = np.zeros((H, W), np.float32)
    out[wr, wc] = values
    return out


q = perp * 2.6 + gdir * along * 0.09 + offset
grain = wood_field(noise(q, 1.0, 31, 3))
lines = 0.5 + 0.5 * np.sin(grain * 24.0)
figure = wood_field(noise(perp * 0.5 + gdir * along * 0.03 + offset, 1.0, 32, 2))
saw = wood_field(np.sin(along[:, 0] * 11.0 + noise(q, 0.4, 33, 1) * 16.0) * 0.5 + 0.5)
knot = wood_field(smooth(0.74, 0.84, noise(perp * 0.42 + gdir * along * 0.16 + offset * 2.1, 1.0, 34, 2)))
del wp, gdir, along, perp, offset, q, wf, wparts
print("wood fields", flush=True)

crate_a = inside((-46, -21.5, 23.9), (-18, 7.5, 44.5))
crate_b = inside((9.4, -4, 23.9), (34.3, 20.5, 43))
board_tone = part * 0.5 + 0.25
crates = np.isin(finish, (GRAIN_X, GRAIN_Y, GRAIN_Z, BRACE))
pine = blend(np.broadcast_to(C(168, 140, 100), (H, W, 3)), np.broadcast_to(C(112, 84, 54), (H, W, 3)), np.clip(lines * 0.62 + (figure - 0.5) * 0.9, 0, 1))
pine = pine * (0.82 + 0.36 * board_tone[..., None])
aged = np.clip((big - 0.35) * 1.5, 0, 1) * (0.62 * crate_a + 0.2 * crate_b)
pine = blend(pine, np.broadcast_to(C(122, 114, 100), (H, W, 3)) * (0.82 + 0.36 * lines[..., None]), aged)
pine = blend(pine, np.broadcast_to(C(62, 44, 28), (H, W, 3)), knot * 0.85)
pine = blend(pine, pine * 0.62, smooth(0.5, 0.9, crevice) * 0.42)
pine = blend(pine, np.broadcast_to(C(192, 172, 136), (H, W, 3)), edge * 0.4 * smooth(0.3, 0.7, mid))
c_rough = 0.72 + 0.1 * lines + 0.08 * fine
c_height = 0.012 * (grain - 0.5) + 0.0055 * (saw - 0.5) - knot * 0.012
apply(crates, pine, c_rough, 0.0, c_height)

deck = finish == BOARD
timber = blend(np.broadcast_to(C(106, 86, 64), (H, W, 3)), np.broadcast_to(C(48, 37, 27), (H, W, 3)), np.clip(lines * 0.7 + (figure - 0.5) * 1.0, 0, 1))
timber = timber * (0.78 + 0.44 * board_tone[..., None])
grey = smooth(0.32, 0.7, big + (mid - 0.5) * 0.5) * 0.5
timber = blend(timber, np.broadcast_to(C(118, 112, 102), (H, W, 3)) * (0.75 + 0.45 * lines[..., None]), grey)
drag = field(noise(pts * np.array((0.1, 3.2, 3.2), np.float32), 1.0, 41, 3))
worn_track = smooth(0.45, 0.62, drag) * deck
timber = blend(timber, np.broadcast_to(C(142, 126, 104), (H, W, 3)), worn_track * 0.13)
oil = smooth(0.58, 0.72, field(noise(pts, 0.09, 42, 3)) + (mid - 0.5) * 0.3) * deck
timber = blend(timber, timber * 0.42, oil * 0.8)
d_rough = 0.72 + 0.12 * lines - worn_track * 0.14 - oil * 0.34
d_height = 0.016 * (grain - 0.5) + 0.004 * (saw - 0.5) - worn_track * 0.004 * lines
apply(deck, timber, d_rough, 0.0, d_height)
del pine, timber, c_rough, c_height, d_rough, d_height, saw, figure, knot, aged
print("wood", flush=True)

# --- Green enamel over red oxide over steel: the frame, the gates, the wheels.
enamel = (finish == PAINT) | (finish == WELD)
wheel_zone = (Z < 16.6) & (np.abs(Y) > 17.2) & (np.abs(X - np.where(X < 0, -37, 33)) < 8.3)
green = np.broadcast_to(C(50, 68, 52), (H, W, 3))
faded = np.broadcast_to(C(96, 110, 90), (H, W, 3))
wheel_paint = np.broadcast_to(C(40, 46, 42), (H, W, 3))
chip = (
    edge * smooth(0.28, 0.66, mid * 0.6 + fine * 0.4) * 1.05
    + (mid - 0.5) * 0.46
    + (big - 0.5) * 0.25
    + (fine - 0.5) * 0.75
    + (micro - 0.5) * 0.25
    + smooth(30.0, 4.0, Z) * 0.08
    + halo * 0.12
)
to_steel = smooth(0.765, 0.78, chip)
to_oxide = smooth(0.69, 0.71, chip)
fade = smooth(0.34, 0.76, field(noise(pts * np.array((0.4, 0.4, 0.9), np.float32), 0.4, 43, 3)) + (mid - 0.5) * 0.25) * 0.55 * upward.clip(0.15, 1)
e_color = blend(np.where(wheel_zone[..., None], wheel_paint, green) * (0.86 + 0.3 * part[..., None]), faded, fade)
e_color = e_color * (0.92 + 0.16 * fine[..., None])
e_color = blend(e_color, np.broadcast_to(C(116, 58, 40), (H, W, 3)) * (0.8 + 0.4 * fine[..., None]), to_oxide)
pit = smooth(0.4, 0.75, fine)
e_color = blend(e_color, blend(steel * 0.7, rust_c, pit), to_steel)
e_rust = np.clip(run * 1.05, 0, 1)
e_color = blend(e_color, rust_c * 0.85, e_rust * 0.8)
e_rough = 0.4 + 0.1 * mid + fade * 0.35 + to_oxide * 0.3 + to_steel * (0.12 + pit * 0.2) + e_rust * 0.3
e_metal = to_steel * (1 - pit) * 0.9
e_height = 0.0016 * (micro - 0.5) + (1 - to_oxide) * 0.008 + (1 - to_steel) * 0.005 - to_steel * pit * 0.004
apply(enamel, e_color, e_rough, e_metal, e_height)
del e_color, e_rough, e_metal, e_height, fade, pit, e_rust, chip, to_steel, to_oxide
print("enamel", flush=True)

# Wheels: vent slots stamped in the discs. Polar about each hub, on the outward face only.
wx = np.where(X < 0, -37.0, 33.0).astype(np.float32)
dx, dz = X - wx, Z - 8.05
polar_r = np.hypot(dx, dz)
outward = nor[..., 1] * np.sign(Y) > 0.5
slot = np.abs((np.arctan2(dz, dx) * 6 / (2 * math.pi) + 0.25) % 1 - 0.5)
vents = (finish == PAINT) & wheel_zone & outward & (smooth(0.11, 0.075, slot) * smooth(3.52, 3.68, polar_r) * smooth(4.72, 4.56, polar_r) > 0.5)
color[vents] = C(8, 8, 8)
rough[vents] = 0.9
metal[vents] = 0.0
height[vents] -= 0.05
# Rim rust, where the tyre's bead traps the wet.
rim = (finish == PAINT) & wheel_zone & (polar_r > 4.9)
rim_rust = smooth(0.5, 0.74, fine * 0.5 + mid * 0.5 + smooth(5.4, 6.0, polar_r) * 0.22) * rim
color[...] = blend(color, rust_c * 0.8, rim_rust * 0.5)
rough[...] = rough + rim_rust * 0.18

# --- Tyres: three ribs in the mesh, sipes cut across them here, raised sidewall lettering.
tyres = finish == RUBBER
t_color = np.broadcast_to(C(24, 24, 25), (H, W, 3)) * (0.82 + 0.4 * mid[..., None])
t_height = 0.0035 * (fine - 0.5) + 0.002 * (micro - 0.5)
tread = tyres & wheel_zone & (polar_r > 7.78)
theta = np.arctan2(dz, dx)
sipes = smooth(0.62, 0.8, np.sin(theta * 64 + np.abs(Y) * 3.0) * 0.5 + 0.5)
t_height = np.where(tread, t_height - sipes * 0.05, t_height)
t_rough = np.where(tread, 0.72 - (1 - sipes) * 0.1, 0.84)


def text_strip(text, size, font=BOLD):
    """White letters on black, the image's top row the letters' top."""
    w, h = size
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(font, int(h * 0.92))
    bb = d.textbbox((0, 0), text, font=f)
    if bb[2] - bb[0] > w:
        f = ImageFont.truetype(font, int(h * 0.92 * w / (bb[2] - bb[0])))
        bb = d.textbbox((0, 0), text, font=f)
    d.text(((w - bb[2] + bb[0]) // 2 - bb[0], (h - bb[3] + bb[1]) // 2 - bb[1]), text, 255, font=f)
    return np.asarray(img, np.float32) / 255.0


side = text_strip("5.00-8   6 PR   TT   5.00-8   6 PR   TT", (3000, 96))
right_sign = -np.sign(Y)  # Viewer's right along X, on each side of the cart.
phi = np.arctan2(dx * right_sign, dz) / (2 * math.pi) % 1.0
letters = sample_image(side, phi, (polar_r - 6.55) / 0.55) * (tyres & wheel_zone & outward)
t_height = t_height + ndi.gaussian_filter(letters, 0.6) * 0.05
apply(tyres, t_color, t_rough, 0.0, t_height)
del t_color, t_height, t_rough, sipes, phi, letters, slot, theta, rim_rust, rim, vents
print("tyres", flush=True)

# --- Dark hardware: oxide-blacked steel; aluminium on the flight case.
hardware = finish == OXIDE
flight = inside((-46.1, 7.8, 23.9), (-18.9, 21.6, 38.45))
i_wear = smooth(0.42, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
i_color = np.broadcast_to(C(30, 30, 31), (H, W, 3)) * (0.75 + 0.5 * mid[..., None])
i_color = blend(i_color, steel * 0.72, i_wear * 0.85)
i_rust = smooth(0.66, 0.82, field(noise(pts, 2.4, 13, 3)) + crevice * 0.12)
i_color = blend(i_color, rust_c, i_rust * 0.8)
# The suitcases' corner bumpers are moulded, not steel: no rust on them.
bumper = inside((-15.4, -19.3, 23.9), (1.2, 1.9, 26.8))
i_rust = np.where(bumper, 0.0, i_rust)
i_color = np.where(bumper[..., None], np.broadcast_to(C(30, 30, 31), (H, W, 3)) * (0.8 + 0.4 * mid[..., None]), i_color)
i_color = np.where(flight[..., None], np.broadcast_to(C(96, 98, 100), (H, W, 3)) * (0.82 + 0.3 * fine[..., None]), i_color)
i_rough = np.where(flight, 0.42 + 0.16 * fine - 0.1 * i_wear, 0.5 + 0.2 * fine - 0.14 * i_wear + 0.32 * i_rust)
i_metal = np.where(flight, 1.0, np.where(bumper, 0.0, (1 - i_rust) * 0.85))
i_height = 0.0018 * (micro - 0.5) + i_rust * 0.006
apply(hardware, i_color, i_rough, i_metal, i_height)

# Zinc: bolts, strapping and ball corners.
zinc = finish == ZINC
z_rust = smooth(0.6, 0.78, fine * 0.6 + mid * 0.4 + crevice * 0.15)
z_color = blend(steel * (0.62 + 0.5 * fine[..., None]), rust_c, z_rust * 0.75)
apply(zinc, z_color, 0.42 + 0.2 * fine + 0.3 * z_rust, (1 - z_rust) * 0.95, 0.0015 * (micro - 0.5))

# Brass: tarnished, bright where it's rubbed.
brass = finish == BRASS
b_touch = smooth(0.4, 0.72, edge * 0.7 + (mid - 0.5) * 0.7 + (fine - 0.5) * 0.5)
b_color = blend(np.broadcast_to(C(94, 80, 54), (H, W, 3)), np.broadcast_to(C(176, 152, 102), (H, W, 3)), b_touch * 0.85)
b_green = smooth(0.7, 0.86, field(noise(pts, 1.8, 12, 3)) + crevice * 0.24)
b_color = blend(b_color, np.broadcast_to(C(82, 100, 82), (H, W, 3)), b_green * 0.3)
apply(brass, b_color, 0.4 + 0.24 * (1 - b_touch) + 0.15 * b_green, 1 - b_green * 0.7, 0.0012 * (micro - 0.5))
del i_color, i_rough, i_metal, i_height, i_wear, i_rust, z_color, z_rust, b_color, b_touch, b_green

# --- Aluminium panels, ribbed on the flight case; the suitcases' seams stay plain.
alu = finish == GALV
rib_axis = np.where(np.abs(nor[..., 0]) > 0.6, Y, X)
ribs = (0.5 + 0.5 * np.sin(rib_axis * 2 * math.pi / 1.3)) * flight * (np.abs(nor[..., 2]) < 0.5)
scratch = smooth(0.68, 0.8, field(noise(pts * np.array((0.2, 3.5, 3.5), np.float32), 1.0, 44, 3)))
dents = field(noise(pts, 0.28, 45, 2))
a_color = np.broadcast_to(C(154, 156, 156), (H, W, 3)) * (0.78 + 0.36 * mid[..., None]) * (0.88 + 0.16 * ribs[..., None])
a_color = blend(a_color, np.broadcast_to(C(190, 192, 190), (H, W, 3)), scratch * 0.42)
a_color = blend(a_color, a_color * 0.55, crevice * 0.6)
apply(alu, a_color, 0.42 + 0.2 * mid + 0.12 * scratch - 0.06 * ribs, 1.0, ribs * 0.045 + (dents - 0.5) * 0.09 - scratch * 0.003)
del a_color, scratch, dents, ribs, rib_axis

# --- Cases.
cases = finish == CASE
trunk_box = inside((-46, 7.8, 38.45), (-19, 21.6, 47.6))
blue_a = inside((-15.4, -19.3, 23.9), (-0.5, -9.9, 52.3))
blue_b = inside((-13.8, -7.7, 23.9), (1.2, 1.9, 50.5))
poly = inside((7.7, -21, 23.9), (33.6, -6.8, 34.4))
scuff = smooth(0.46, 0.68, edge * 0.85 + (fine - 0.5) * 0.9 + (mid - 0.5) * 0.4)
# Fibre trunk: oxblood lacquer, worn back to brown board on its corners.
weave = (np.sin(X * 2 * math.pi * 3.6) * np.sin((Y + Z) * 2 * math.pi * 3.6)) * 0.5 + 0.5
t_col = np.broadcast_to(C(82, 26, 24), (H, W, 3)) * (0.78 + 0.5 * mid[..., None]) * (0.92 + 0.12 * weave[..., None])
t_col = blend(t_col, np.broadcast_to(C(120, 86, 58), (H, W, 3)), smooth(0.5, 0.75, scuff) * 0.85)
t_col = blend(t_col, np.broadcast_to(C(104, 60, 50), (H, W, 3)), smooth(0.3, 0.75, big) * 0.3)
# Hard suitcases: two faded blues, with moulded ribs down their broad faces.
broad = np.abs(nor[..., 1]) > 0.7
groove = smooth(0.82, 0.96, np.abs(np.sin((X + 0.6) * math.pi / 2.3))) * broad * (Z > 26.0) * (Z < 49.0)
navy = np.broadcast_to(C(30, 48, 82), (H, W, 3))
slate = np.broadcast_to(C(50, 78, 96), (H, W, 3))
s_col = np.where(blue_a[..., None], navy, slate) * (0.8 + 0.42 * mid[..., None])
s_col = blend(s_col, np.broadcast_to(C(150, 156, 164), (H, W, 3)), smooth(0.52, 0.78, scuff) * 0.75)
s_col = blend(s_col, s_col * 0.62, groove * 0.5)
# Polymer case: pebbled black, its scuffs pale.
pebble = field(noise(pts, 9.0, 46, 1))
p_col = np.broadcast_to(C(24, 25, 26), (H, W, 3)) * (0.82 + 0.3 * mid[..., None])
p_col = blend(p_col, np.broadcast_to(C(72, 72, 70), (H, W, 3)), smooth(0.6, 0.86, edge * 0.9 + (fine - 0.5) * 0.3) * 0.6)
case_c = np.where(trunk_box[..., None], t_col, np.where(poly[..., None], p_col, s_col))
case_r = np.where(trunk_box, 0.48 + 0.2 * weave + 0.14 * big, np.where(poly, 0.62, 0.4 + 0.14 * mid + 0.3 * smooth(0.5, 0.8, scuff)))
case_h = np.where(trunk_box, weave * 0.003, np.where(poly, (pebble - 0.5) * 0.004, -groove * 0.05))
apply(cases, case_c, case_r, 0.0, case_h)
del t_col, s_col, p_col, case_c, case_r, case_h, weave, navy, slate, pebble, groove, broad
print("cases", flush=True)

# --- Soft goods.
canvas = finish == CANVAS
weave = (np.sin(X * 2 * math.pi * 4.0) + np.sin(Z * 2 * math.pi * 4.0) + np.sin(Y * 2 * math.pi * 4.0)) / 6 + 0.5
c_col = np.broadcast_to(C(90, 92, 60), (H, W, 3)) * (0.78 + 0.46 * mid[..., None]) * (0.9 + 0.2 * weave[..., None])
c_col = blend(c_col, np.broadcast_to(C(130, 124, 92), (H, W, 3)), smooth(0.42, 0.8, big) * 0.35)
c_col = blend(c_col, np.broadcast_to(C(44, 42, 30), (H, W, 3)), smooth(0.6, 0.76, field(noise(pts, 0.5, 47, 3))) * 0.45)
# The roll's ends show the cloth's spiral.
rx, rz = X - 40.4, Z - 29.1
rr = np.hypot(rx, rz)
spiral = ((rr / 0.62 - np.arctan2(rz, rx) / (2 * math.pi)) % 1.0)
cap = canvas & (np.abs(nor[..., 1]) > 0.75)
wrap = smooth(0.0, 0.22, spiral) * smooth(1.0, 0.72, spiral)
c_col = np.where(cap[..., None], c_col * (0.3 + 0.7 * wrap[..., None]), c_col)
# Long creases round the roll, and the sag between its straps.
folds = field(noise(pts * np.array((1.0, 0.16, 1.0), np.float32), 0.85, 48, 3))
c_col = c_col * (0.72 + 0.56 * smooth(0.25, 0.75, folds)[..., None])
c_h = np.where(cap, wrap * 0.09, weave * 0.006 + (mid - 0.5) * 0.06 + (folds - 0.5) * 0.3)
apply(canvas, c_col, 0.86 + 0.1 * fine, 0.0, c_h)

straps = finish == STRAP
leather = trunk_box | inside((-19.3, 8, 38), (-17, 21, 46))
handles = inside((-16, -20, 50), (2, 2, 55))
s_web = np.broadcast_to(C(64, 66, 44), (H, W, 3)) * (0.8 + 0.4 * fine[..., None])
s_lea = blend(np.broadcast_to(C(74, 44, 24), (H, W, 3)) * (0.75 + 0.5 * mid[..., None]), np.broadcast_to(C(138, 100, 62), (H, W, 3)), smooth(0.4, 0.72, edge + (fine - 0.5) * 0.5) * 0.75)
s_blk = np.broadcast_to(C(22, 20, 19), (H, W, 3)) * (0.8 + 0.5 * mid[..., None])
s_col = np.where(leather[..., None], s_lea, np.where(handles[..., None], s_blk, s_web))
web_h = (0.5 + 0.5 * np.sin(Y * 2 * math.pi * 3.2)) * 0.006
apply(straps, s_col, np.where(leather | handles, 0.5 + 0.2 * fine, 0.88), 0.0, np.where(leather | handles, 0.004 * (fine - 0.5), web_h))
rope = finish == ROPE
r_col = np.broadcast_to(C(152, 128, 88), (H, W, 3)) * (0.7 + 0.6 * fine[..., None])
apply(rope, r_col, 0.9, 0.0, (fine - 0.5) * 0.03)
apply(finish == LINER, np.broadcast_to(C(18, 16, 14), (H, W, 3)) * (0.8 + 0.4 * mid[..., None]), 0.88, 0.0, 0.0)

# Amber reflector: a moulded prism grid.
amber = finish == AMBER
prism = (np.sin(X * 2 * math.pi * 3.0) * np.sin(Z * 2 * math.pi * 3.0)) * 0.5 + 0.5
apply(amber, np.broadcast_to(C(214, 118, 12), (H, W, 3)) * (0.62 + 0.5 * prism[..., None]), 0.22, 0.0, prism * 0.02)

paper = finish == LABEL
apply(paper, np.broadcast_to(C(212, 202, 174), (H, W, 3)) * (0.86 + 0.2 * mid[..., None]), 0.84, 0.0, 0.002 * (fine - 0.5))
del weave, c_col, c_h, folds, s_web, s_lea, s_blk, s_col, web_h, r_col, prism, rx, rz, rr, spiral, wrap, cap
print("soft", flush=True)

# --- Stencils and print. Each is projected through the baked position, on the faces looking its way.


def text_block(lines, size, font=BOLD):
    """Several lines of (text, share of the height). The image's top row is the block's top."""
    w, h = size
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    y = 0
    for text, share in lines:
        row = int(h * share)
        f = ImageFont.truetype(font, int(row * 0.94))
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] > w:
            f = ImageFont.truetype(font, int(row * 0.94 * w / (bb[2] - bb[0])))
            bb = d.textbbox((0, 0), text, font=f)
        d.text(((w - bb[2] + bb[0]) // 2 - bb[0], y + (row - bb[3] + bb[1]) // 2 - bb[1]), text, 255, font=f)
        y += row
    return np.asarray(img, np.float32) / 255.0


stencil_wear = smooth(0.52, 0.66, field(noise(pts, 1.4, 51, 3)) * 0.65 + fine * 0.35 + edge * 0.2)
pr, pc = rows, cols
P = pts
N = nor[rows, cols]


def stamp(image, centre, right, up, w, h, normal, ink, worn=0.8, depth=2.0, mask=None, soften=0.5, rough_to=None):
    """Lay image on the faces looking along normal. ink is a colour; image the coverage, top row up."""
    c, r, u, n = (np.array(v, np.float32) for v in (centre, right, up, normal))
    d = P - c
    uu = d @ r / w + 0.5
    vv = d @ u / h + 0.5
    keep = (uu >= 0) & (uu <= 1) & (vv >= 0) & (vv <= 1) & (np.abs(d @ n) < depth) & (N @ n > 0.6)
    if mask is not None:
        keep &= mask[pr, pc]
    a = sample_image(image, uu[keep], vv[keep])
    ri, ci = pr[keep], pc[keep]
    a = a * (1 - stencil_wear[ri, ci] * worn)
    color[ri, ci] = color[ri, ci] + (ink - color[ri, ci]) * a[:, None]
    if rough_to is not None:
        rough[ri, ci] = rough[ri, ci] + (rough_to - rough[ri, ci]) * a


def fleet_mark(size):
    w, h = size
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, w - 7, h - 7), radius=h // 6, outline=255, width=max(4, h // 16))
    f = ImageFont.truetype(BOLD, int(h * 0.56))
    bb = d.textbbox((0, 0), "rhv", font=f)
    d.text(((w - bb[2] + bb[0]) // 2 - bb[0], (h - bb[3] + bb[1]) // 2 - bb[1]), "rhv", 255, font=f)
    return np.asarray(img, np.float32) / 255.0


cream = C(214, 216, 196)
black = C(20, 19, 17)
frame_only = enamel
for s in (-1, 1):
    n = (0, s, 0)
    right = (-s, 0, 0)  # The viewer's right, looking at this side.
    y = s * (23.6 + 0.55)
    stamp(fleet_mark((256, 200)), (-s * 33.0, y, 20.45), right, (0, 0, 1), 3.0, 2.3, n, cream, 0.75, 0.6, frame_only)
    stamp(text_strip("L-312", (640, 160)), (-s * 24.0, y, 20.45), right, (0, 0, 1), 8.0, 2.0, n, cream, 0.75, 0.6, frame_only)
    stamp(text_strip("Zul. Gesamtgew. 2000 kg", (1500, 96)), (s * 16.0, y, 20.45), right, (0, 0, 1), 23.0, 1.5, n, cream, 0.75, 0.6, frame_only)
for sx in (-1, 1):
    n = (sx, 0, 0)
    right = (0, sx, 0)
    img = text_block([("rhv", 0.52), ("L-312", 0.48)], (660, 360))
    stamp(img, (sx * 48.95, 0, 36.3), right, (0, 0, 1), 9.6, 5.2, n, cream, 0.7, 0.6, frame_only)

# Crates: consignment stencils, the arrows and glass everyone recognises.


def handling_mark(size):
    w, h = size
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    # Two arrows up, then a stemmed glass: a transit mark, no one's trademark.
    for cx in (w * 0.24, w * 0.76):
        d.polygon([(cx, h * 0.04), (cx + w * 0.16, h * 0.3), (cx + w * 0.055, h * 0.3), (cx + w * 0.055, h * 0.62), (cx - w * 0.055, h * 0.62), (cx - w * 0.055, h * 0.3), (cx - w * 0.16, h * 0.3)], fill=255)
    d.rectangle((w * 0.06, h * 0.7, w * 0.94, h * 0.74), fill=255)
    return np.asarray(img, np.float32) / 255.0


stamp(text_block([("HOHENWALD HBF", 0.34), ("ZERBRECHLICH", 0.33), ("GLEIS 3 - KISTE 7", 0.33)], (1300, 460)), (-32.0, -21.0, 39.0), (1, 0, 0), (0, 0, 1), 12.8, 4.5, (0, -1, 0), black, 0.6, 1.2, crates)
stamp(handling_mark((360, 360)), (-23.15, -21.0, 37.6), (1, 0, 0), (0, 0, 1), 3.3, 3.3, (0, -1, 0), black, 0.5, 1.2, crates)
stamp(text_block([("KISTE 7", 1.0)], (900, 220)), (-32.0, -7.0, 43.9), (0, -1, 0), (1, 0, 0), 11.0, 2.7, (0, 0, 1), black, 0.55, 1.2, crates)
stamp(text_block([("OBEN", 1.0)], (500, 200)), (-18.5, -7.0, 38.4), (0, 1, 0), (0, 0, 1), 7.5, 3.0, (1, 0, 0), black, 0.55, 1.2, crates)
stamp(text_block([("BAHNPOST", 0.5), ("HOHENWALD", 0.5)], (1200, 420)), (21.8, 20.0, 37.6), (-1, 0, 0), (0, 0, 1), 11.6, 4.2, (0, 1, 0), black, 0.6, 1.2, crates)
stamp(handling_mark((360, 360)), (29.8, 20.0, 37.6), (-1, 0, 0), (0, 0, 1), 2.6, 2.6, (0, 1, 0), black, 0.5, 1.2, crates)
stamp(text_block([("KISTE 12", 1.0)], (900, 220)), (21.8, 8.15, 42.5), (0, -1, 0), (1, 0, 0), 10.0, 2.5, (0, 0, 1), black, 0.55, 1.2, crates)
stamp(text_block([("KISTE 12", 1.0)], (900, 220)), (9.6, 8.15, 38.4), (0, -1, 0), (0, 0, 1), 8.5, 2.2, (-1, 0, 0), black, 0.55, 1.2, crates)
# Flight case and polymer case.
stamp(text_block([("MESSTECHNIK", 0.55), ("R-2204", 0.45)], (1100, 360)), (-32.5, 21.4, 28.6), (-1, 0, 0), (0, 0, 1), 11.0, 3.6, (0, 1, 0), black, 0.5, 0.6, finish == GALV)
stamp(text_block([("SIGNALTECHNIK", 1.0)], (1000, 150)), (20.6, -20.75, 32.2), (1, 0, 0), (0, 0, 1), 9.0, 1.35, (0, -1, 0), cream, 0.6, 0.6, cases)


def waybill(size, title, lines):
    w, h = size
    img = Image.new("RGB", (w, h), (214, 204, 176))
    d = ImageDraw.Draw(img)
    ink = (34, 32, 30)
    d.rectangle((8, 8, w - 9, h - 9), outline=ink, width=3)
    f = ImageFont.truetype(BOLD, h // 8)
    d.text((18, 12), title, ink, font=f)
    d.line((8, 16 + h // 7, w - 9, 16 + h // 7), fill=ink, width=3)
    r = ImageFont.truetype(REGULAR, h // 12)
    y = 22 + h // 7
    for line in lines:
        d.text((18, y), line, ink, font=r)
        y += h // 10
    bars = np.random.default_rng(len(title) * 7 + len(lines))
    x = w * 0.08
    while x < w * 0.62:
        b = float(bars.integers(2, 7))
        d.rectangle((x, h * 0.74, x + b, h * 0.93), fill=ink)
        x += b + float(bars.integers(2, 7))
    d.ellipse((w * 0.68, h * 0.5, w * 0.94, h * 0.5 + w * 0.26), outline=(140, 34, 28), width=5)
    s = ImageFont.truetype(BOLD, h // 14)
    d.text((w * 0.71, h * 0.5 + w * 0.09), "GEPRUEFT", (140, 34, 28), font=s)
    return np.asarray(img, np.float32) / 255.0


def stamp_rgb(image, centre, right, up, w, h, normal, depth=1.0, mask=None, wear=0.0, gloss=None):
    c, r, u, n = (np.array(v, np.float32) for v in (centre, right, up, normal))
    d = P - c
    uu = d @ r / w + 0.5
    vv = d @ u / h + 0.5
    keep = (uu >= 0) & (uu <= 1) & (vv >= 0) & (vv <= 1) & (np.abs(d @ n) < depth) & (N @ n > 0.6)
    if mask is not None:
        keep &= mask[pr, pc]
    ri, ci = pr[keep], pc[keep]
    samples = [sample_image(ndi.gaussian_filter(image[..., k], 1.2), uu[keep], vv[keep]) for k in range(image.shape[-1])]
    rgb = srgb_to_linear(np.stack(samples[:3], -1) * 255.0).astype(np.float32)
    a = samples[3] if image.shape[-1] > 3 else np.ones(len(ri), np.float32)
    a = a * (1 - stencil_wear[ri, ci] * wear)
    color[ri, ci] = color[ri, ci] + (rgb - color[ri, ci]) * a[:, None]
    if gloss is not None:
        rough[ri, ci] = rough[ri, ci] + (gloss - rough[ri, ci]) * a
    height[ri, ci] += a * 0.006


stamp_rgb(waybill((780, 540), "FRACHTBRIEF 41-0783", ["Von: Hohenwald Hbf", "Nach: Altenbruck", "Kiste 7   48 kg"]), (-32.0, -21.0, 32.8), (1, 0, 0), (0, 0, 1), 6.5, 4.5, (0, -1, 0), mask=paper)
stamp_rgb(waybill((780, 540), "FRACHTBRIEF 41-1296", ["Von: Hohenwald Hbf", "Nach: Lindmark", "Kiste 12   36 kg"]), (21.8, 20.0, 32.2), (-1, 0, 0), (0, 0, 1), 6.5, 4.5, (0, 1, 0), mask=paper)
stamp_rgb(waybill((340, 560), "GEPAECK", ["Hohenwald", "Gleis 3", "Nr. 2217"]), (-0.5, -14.05, 47.5), (0, 1, 0), (0, 0, 1), 1.9, 3.2, (1, 0, 0), mask=paper)


def sticker(size, fill, ink, lines, ring=False):
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if ring:
        d.ellipse((2, 2, w - 3, h - 3), fill=fill)
        d.ellipse((12, 12, w - 13, h - 13), outline=ink, width=5)
    else:
        d.rounded_rectangle((2, 2, w - 3, h - 3), radius=h // 8, fill=fill)
        d.rectangle((10, 10, w - 11, h - 11), outline=ink, width=4)
    y = h * (0.5 - 0.5 * sum(s for _, s in lines))
    for text, share in lines:
        row = h * share
        f = ImageFont.truetype(BOLD, int(row * 0.88))
        bb = d.textbbox((0, 0), text, font=f)
        limit = w * (0.72 if ring else 0.86)
        if bb[2] - bb[0] > limit:
            f = ImageFont.truetype(BOLD, int(row * 0.88 * limit / (bb[2] - bb[0])))
            bb = d.textbbox((0, 0), text, font=f)
        d.text(((w - bb[2] + bb[0]) / 2 - bb[0], y + (row - bb[3] + bb[1]) / 2 - bb[1]), text, ink, font=f)
        y += row
    return np.asarray(img, np.float32) / 255.0


on_blue = cases & (blue_a | blue_b)
stamp_rgb(sticker((420, 260), (198, 168, 92, 255), (54, 40, 26, 255), [("HOTEL", 0.28), ("ALTENBRUCK", 0.34)]), (-11.0, -19.1, 42.0), (1, 0, 0), (0, 0, 1), 4.8, 3.0, (0, -1, 0), mask=on_blue, wear=0.32, gloss=0.5)
stamp_rgb(sticker((320, 320), (156, 44, 36, 255), (232, 222, 196, 255), [("LINDMARK", 0.2), ("EXPRESS", 0.2)], True), (-4.2, -19.1, 36.0), (1, 0, 0), (0, 0, 1), 3.7, 3.7, (0, -1, 0), mask=on_blue, wear=0.32, gloss=0.5)
stamp_rgb(sticker((460, 240), (222, 214, 190, 255), (32, 62, 96, 255), [("SEEBAD", 0.26), ("OSTERHOLM", 0.34)]), (-9.2, -19.1, 30.2), (1, 0, 0), (0, 0, 1), 4.6, 2.4, (0, -1, 0), mask=on_blue, wear=0.38, gloss=0.5)
stamp_rgb(sticker((420, 260), (68, 104, 84, 255), (232, 226, 200, 255), [("RHEINFAEHRE", 0.3), ("1. KLASSE", 0.24)]), (-3.2, 1.7, 41.5), (-1, 0, 0), (0, 0, 1), 4.8, 3.0, (0, 1, 0), mask=on_blue, wear=0.32, gloss=0.5)
stamp_rgb(sticker((300, 300), (216, 176, 70, 255), (40, 30, 22, 255), [("HBF", 0.26), ("KURIER", 0.2)], True), (-9.8, 1.7, 33.4), (-1, 0, 0), (0, 0, 1), 3.4, 3.4, (0, 1, 0), mask=on_blue, wear=0.38, gloss=0.5)
stamp_rgb(sticker((460, 240), (222, 214, 190, 255), (120, 40, 34, 255), [("ALTENBRUCK", 0.3), ("GRAND HOTEL", 0.24)]), (-32.5, 21.45, 42.0), (-1, 0, 0), (0, 0, 1), 5.0, 2.6, (0, 1, 0), mask=cases & trunk_box, wear=0.38, gloss=0.6)
print("stamps", flush=True)

# --- Fastener domes and their rust, on what they sit on.
studded = enamel | crates | deck | cases | alu | hardware
domed = stud_on & studded
stud_col = blend(steel * (0.5 + 0.4 * fine[..., None]), rust_c, smooth(0.45, 0.72, fine))
color[domed] = stud_col[domed]
rough[domed] = 0.45
metal[domed] = 0.75
height[domed] += dome[domed]
wood_nail = (crates | deck) & (halo > 0) & (stud_r < 0.2)
color[...] = blend(color, color * 0.6, (halo * wood_nail * 0.6).astype(np.float32))
stain = run * (crates | deck | cases)
color[...] = blend(color, rust_c * 0.7, np.clip(stain * 0.55, 0, 1))
del stud_col, domed, stain, wood_nail, dome, stud_d, stud_on, stud_r
print("studs applied", flush=True)

# --- Dirt: dust on what faces up and in corners, road film rising from the wheels.
settled = smooth(0.46, 0.92, upward * 0.8 + (big - 0.5) * 0.34 + crevice * 0.26)
low = smooth(21.0, 4.0, Z)
splash = low * smooth(0.46, 0.68, field(noise(pts * np.array((0.6, 0.6, 0.3), np.float32), 1.0, 14, 4)) + low * 0.16)
dirt = np.clip(settled * 0.42 + splash * 0.55 + crevice * 0.12, 0, 0.85)
dirt_c = np.broadcast_to(C(100, 90, 74), (H, W, 3)) * (0.75 + 0.5 * fine[..., None])
keep_clean = (finish == AMBER) | (finish == LINER) | (finish == LABEL)
dirt = np.where(keep_clean, dirt * 0.2, np.where(tyres, dirt * 0.55, dirt))
color = blend(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.92 * dirt
metal = metal * (1 - dirt)
del settled, splash, dirt, dirt_c, low

color = color * (0.72 + 0.28 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
# Metalness and AO don't need the full atlas, so they cost a quarter of the memory.
half = lambda a: (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), half(metal))
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), half(np.clip(ao * 1.03, 0, 1)))
print("trolley painted", flush=True)
