"""Paint the wall-buy board's maps from its bakes: python paint_board.py <work dir> <materials dir>

Rough-sawn planks, stained long ago and gone grey where the weather reached them, with their grain flowing round knots,
rust weeping from each bolt and a stencil sprayed across them. An enamelled steel frame chipped back through primer on its
edges and rusting from its welds and feet, which wear hazard paint nobody has renewed. All worked out in 3D, so it runs
across UV seams.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, CABLE, FOOT, TIMBER, PAPER, CLIPBOARD = range(14)
NAME = "wall_buy_board"
facts = json.load(open(os.path.join(WORK, "board.json")))
density = facts["density"]
FLOOR, SPAN, PITCH, FACE = facts["floor"], facts["plank_span"], facts["plank_pitch"], facts["plank_face"]

pos4 = load("bake_board_pos")
nor4 = load("bake_board_nor")
facts4 = load("bake_board_facts")
ao4 = load("bake_board_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
print("coverage %.2f" % cover.mean(), flush=True)
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 2.6) * 0.38, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.6) * 2.4 + ndi.gaussian_filter(convex, 4.0) * 3.0, 0, 1)
del curve, dn, dp
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


big = field(noise(pts, 0.09, 1, 3))
mid = field(noise(pts, 0.55, 2, 4))
fine = field(noise(pts, 2.7, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
print("noise done", flush=True)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

rust_tone = field(noise(pts, 3.1, 8, 3))
rust_c = mix(flat((54, 30, 18)), flat((104, 60, 34)), smooth(0.3, 0.75, rust_tone))
rust_c = mix(rust_c, flat((136, 84, 46)), smooth(0.76, 0.96, rust_tone))
steel = flat((158, 158, 154))

# ---- The planks ----------------------------------------------------------------------------------------------------
timber = finish == TIMBER
index = np.clip(np.floor((Z + SPAN) / PITCH), 0, 4).astype(np.int32)
centre_z = -SPAN + (index + 0.5) * PITCH
r = np.random.default_rng(23)

# Knots: the grain's coordinate is squeezed towards each knot, so the lines part and flow round it.
zw = Z - centre_z
knot_dark = np.zeros((H, W), np.float32)
knot_rings = np.zeros((H, W), np.float32)
for k in range(5):
    here = index == k
    for _ in range(int(r.integers(1, 3))):
        ky, kz, kr = r.uniform(-25, 25), r.uniform(-2.2, 2.2), r.uniform(0.5, 1.05)
        # Long along the grain, short across it.
        d = np.hypot((Y - ky) / 3.4, zw - kz)
        squeeze = np.exp(-((d / (kr * 2.1)) ** 2)) * 0.9
        zw = np.where(here, kz + (zw - kz) * (1 - squeeze), zw)
        dk = np.hypot((Y - ky) / 1.15, Z - centre_z - kz)
        knot_dark = np.where(here, np.maximum(knot_dark, smooth(kr * 1.25, kr * 0.45, dk)), knot_dark)
        knot_rings = np.where(here & (dk < kr * 1.3), 0.5 + 0.5 * np.sin(dk * 34.0), knot_rings)

# Grain runs along Y. Each plank is cut from a different part of the tree.
gp = np.stack((X * 3.6 + index * 17.3, Y * 0.06 + index * 31.7, zw * 1.7 + index * 53.1), -1)[cover]
grain = field(noise(gp, 1.0, 31, 4))
# About five texels a line: any finer and it aliases into stripes.
lines = 0.5 + 0.5 * np.sin(grain * 30.0)
tight = 0.5 + 0.5 * np.sin(field(noise(gp * np.array((1, 1, 2.2), np.float32), 1.0, 33, 3)) * 44.0)
saw = field(noise(np.stack((X * 2, Y * 1.9, Z * 0.2), -1)[cover], 1.0, 34, 2))

heart = mix(flat((116, 92, 68)), flat((56, 42, 30)), np.clip(lines * 0.6 + tight * 0.14 + (mid - 0.5) * 0.4 + (big - 0.5) * 0.3, 0, 1))
tone = np.array([1.0, 0.8, 1.12, 0.9, 1.04], np.float32)[index]
heart = heart * tone[..., None]
heart = mix(heart, flat((30, 21, 15)), np.clip(knot_dark * (0.72 + 0.28 * knot_rings), 0, 1))

# The stain has gone, and the wood gone grey, wherever weather reached it. It's deepest low on each plank's sun side.
fade = smooth(0.22, 0.66, big * 0.5 + mid * 0.5 + (lines - 0.5) * 0.16 + (Z / 40.0) * 0.14)
wood = mix(heart, flat((128, 120, 106)) * (0.7 + 0.4 * lines[..., None]), fade * 0.72)
# Wet patches from the rails above, and a darker skirt round each plank's end grain.
ends = smooth(24.5, 27.9, np.abs(Y))
wood = wood * (1 - ends[..., None] * 0.34)
drip = smooth(0.5, 0.74, field(noise(pts * np.array((3.0, 3.0, 0.15), np.float32), 0.26, 6, 4)))
wood = wood * (1 - drip[..., None] * 0.24)

# Long splits along the grain, more of them near the ends.
split = field(noise(np.stack((X * 3.0 + index * 9.1, Y * 0.05, zw * 6.0), -1)[cover], 1.0, 37, 3))
crack = smooth(0.016, 0.0, np.abs(split - 0.5)) * smooth(0.46, 0.66, big + ends * 0.3 + (mid - 0.5) * 0.4)
crack = ndi.gaussian_filter(crack, 0.6)
wood = wood * (1 - crack[..., None] * 0.78)

t_rough = 0.72 + 0.1 * lines + 0.08 * fade - 0.1 * knot_dark
t_height = 0.02 * (grain - 0.5) + 0.012 * (lines - 0.5) + 0.004 * (saw - 0.5) + 0.0012 * (micro - 0.5) - crack * 0.03 + knot_dark * 0.008

# Rust weeps down from every bolt and standoff plate.
front = timber & (nor[..., 0] > 0.6)
weep = np.zeros((H, W), np.float32)
halo = np.zeros((H, W), np.float32)
sway = (field(noise(np.stack((X, Y * 0.3, Z * 0.35), -1)[cover], 1.0, 41, 3)) - 0.5) * 1.6
for k in range(5):
    cz = -SPAN + (k + 0.5) * PITCH
    for by in (-26.2, -10.5, 10.5, 26.2):
        below = cz - Z
        width = 0.36 + np.clip(below, 0, 7) * 0.05
        run = np.exp(-(((Y - by + sway * np.clip(below, 0, 7) * 0.12) / width) ** 2)) * smooth(-0.3, 0.3, below) * smooth(6.5, 0.8, below)
        weep = np.maximum(weep, run * (index == k))
        halo = np.maximum(halo, smooth(1.0, 0.34, np.hypot(Y - by, Z - cz)) * (index == k))
for by in (-22.5, -7.5, 7.5, 22.5):
    below = -1.5 - Z
    run = np.exp(-(((Y - by + sway * np.clip(below, 0, 6) * 0.12) / 1.1) ** 2)) * smooth(-0.2, 0.3, below) * smooth(5.0, 0.5, below)
    weep = np.maximum(weep, run * 0.8 * (index == 2))
weep = weep * smooth(0.28, 0.62, fine + mid * 0.5 - 0.1)
wood = mix(wood, wood * rust_c * 3.4, weep[..., None] * 0.62 * front[..., None])
wood = wood * (1 - halo[..., None] * 0.42 * front[..., None])

# Where guns have been hung and taken down, the planks are rubbed pale and polished behind the rail.
rub = smooth(7.0, 2.5, np.abs(Z)) * smooth(0.36, 0.7, mid) * smooth(27.0, 21.0, np.abs(Y))
scrape = smooth(0.62, 0.76, field(noise(np.stack((X, Y * 0.18, Z * 5.0), -1)[cover], 1.0, 42, 3)))
wood = mix(wood, flat((150, 130, 104)), (rub * scrape * 0.42)[..., None] * front[..., None])
t_rough = t_rough - rub * scrape * 0.16

# Stencils, sprayed in one pass across the top and bottom planks. +Y is a player's right, so they read left to right.
art_top = ndi.gaussian_filter(stencil_image(["ARMS ISSUE"], (1100, 170), bridge=True), 1.3)
art_low = ndi.gaussian_filter(stencil_image(["CLEAR BEFORE RACKING"], (1400, 110), bridge=True), 1.0)
top_mask = sample_image(art_top, np.clip((Y + 15.5) / 31.0, -1, 2), np.clip((Z - 11.95) / 4.8, -1, 2))
low_mask = sample_image(art_low, np.clip((Y + 15.5) / 31.0, -1, 2), np.clip((Z + 16.05) / 2.45, -1, 2))
top_mask = top_mask * (index == 4)
low_mask = low_mask * (index == 0)
spray = np.maximum(top_mask, low_mask) * front
# It sat on the grain's ridges and has flaked along the lines. Overspray leaves a faint halo.
keep = smooth(0.25, 0.5, field(noise(pts, 2.4, 43, 3)) * 0.6 + big * 0.3 + lines * 0.24)
over = ndi.gaussian_filter(spray, 9.0) * 0.5 * front * smooth(0.3, 0.7, mid)
wood = mix(wood, flat((150, 146, 126)), over[..., None] * 0.2)
wood = mix(wood, flat((158, 154, 134)) * (0.74 + 0.36 * lines[..., None]), (spray * keep * 0.9)[..., None])
t_rough = t_rough * (1 - spray * keep) + 0.62 * spray * keep
t_height = t_height + spray * keep * 0.0045

color = np.where(timber[..., None], wood, color)
rough = np.where(timber, t_rough, rough)
height = np.where(timber, t_height, height)

# ---- Enamelled steel, and the welds under it -------------------------------------------------------------------------
painted = (finish == PAINT) | (finish == WELD) | (finish == FOOT)
foot = finish == FOOT
weld = finish == WELD
low = smooth(-20.0, FLOOR, Z)

# Edges wear in patches, never as a line.
chip = (
    edge * smooth(0.3, 0.66, mid * 0.65 + fine * 0.35) * 1.14
    + (mid - 0.5) * 0.56
    + (big - 0.5) * 0.38
    + (fine - 0.5) * 0.8
    + (micro - 0.5) * 0.28
    + low * 0.12
    + foot * 0.09
)
bare = smooth(0.69, 0.705, chip)
primer = smooth(0.645, 0.66, chip)

enamel = mix(flat((42, 48, 38)), flat((66, 72, 56)), smooth(0.25, 0.7, mid * 0.5 + big * 0.5))
enamel = enamel * (0.9 + 0.2 * part[..., None])
upright = 1 - np.abs(nor[..., 2])
streak = field(noise(pts * np.array((4.2, 4.2, 0.13), np.float32), 0.26, 6, 4))
enamel = enamel * (1 + upright[..., None] * (streak[..., None] - 0.5) * 0.46)
enamel = mix(enamel, flat((104, 106, 88)), smooth(0.42, 0.8, big)[..., None] * 0.24)

# Hazard paint on the feet, walked over for years.
stripes = np.mod((X + np.abs(Y)) / 4.2, 1.0) < 0.5
hazard = np.where(stripes[..., None], srgb_to_linear((186, 142, 30)), srgb_to_linear((30, 30, 28)))
hazard = hazard * (0.72 + 0.4 * mid[..., None])
p_color = np.where(foot[..., None], hazard, enamel)
worn_foot = foot * smooth(0.42, 0.62, mid * 0.6 + fine * 0.4) * smooth(-0.2, 0.7, nor[..., 2])
p_color = mix(p_color, flat((84, 78, 62)), worn_foot[..., None] * 0.7)

p_color = mix(p_color, flat((118, 112, 92)) * (0.84 + 0.3 * fine[..., None]), primer[..., None])
p_rough = 0.46 + 0.2 * mid + 0.12 * fine
p_rough = p_rough * (1 - primer) + (0.8 + 0.1 * fine) * primer
p_color = mix(p_color, steel * (0.68 + 0.42 * fine[..., None]), bare[..., None])
p_rough = p_rough * (1 - bare) + (0.36 + 0.26 * fine) * bare
p_metal = bare.copy()
p_height = 0.004 * (micro - 0.5) + 0.0022 * (fine - 0.5) + (1 - primer) * 0.007 + (1 - bare) * 0.006

# Rust in the chips, and down from welds and low on the frame.
in_chip = bare * smooth(0.4, 0.68, field(noise(pts, 1.7, 7, 3)) + crevice * 0.4 + low * 0.2) * 0.92
p_color = mix(p_color, rust_c, in_chip[..., None])
p_rough = p_rough * (1 - in_chip) + (0.84 + 0.12 * fine) * in_chip
p_metal = p_metal * (1 - in_chip)
p_height = p_height + in_chip * 0.006 * (rust_tone - 0.2)
run = smooth(0.54, 0.76, streak + crevice * 0.28) * smooth(0.25, 0.6, mid + crevice * 0.55 + low * 0.2) * 0.55
p_color = mix(p_color, p_color * rust_c * 3.4, run[..., None])
p_rough = p_rough + run * 0.14

ripple = field(noise(pts, 4.2, 9, 3))
p_height = p_height + weld * (0.05 * (ripple - 0.5) + 0.018 * (micro - 0.5))
p_color = np.where(weld[..., None], p_color * 0.72, p_color)
color = np.where(painted[..., None], p_color, color)
rough = np.where(painted, p_rough, rough)
metal = np.where(painted, p_metal, metal)
height = np.where(painted, p_height, height)

# ---- Hardware ------------------------------------------------------------------------------------------------------
# The rail: black oxide, rubbed bright where it has carried guns.
oxide = finish == OXIDE
o_wear = smooth(0.44, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
o_color = flat((34, 34, 36)) * (0.75 + 0.5 * mid[..., None])
o_color = mix(o_color, steel * 0.78, o_wear[..., None] * 0.9)
o_rust = smooth(0.74, 0.88, field(noise(pts, 3.6, 11, 3)) + crevice * 0.1)
o_color = mix(o_color, rust_c, o_rust[..., None] * 0.7)
color = np.where(oxide[..., None], o_color, color)
rough = np.where(oxide, 0.42 + 0.2 * fine - 0.1 * o_wear + 0.34 * o_rust, rough)
metal = np.where(oxide, (1 - o_rust) * 0.92, metal)
height = np.where(oxide, 0.0016 * (micro - 0.5) + o_rust * 0.006 * (rust_tone - 0.3) - o_wear * 0.002, height)

# Bolts: zinc gone dull, with the first rust round their edges.
zinc = finish == ZINC
z_white = smooth(0.46, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.5)
z_color = flat((120, 120, 116)) * (0.42 + 0.3 * mid[..., None])
z_color = mix(z_color, flat((72, 44, 28)), z_white[..., None] * 0.8)
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, 0.5 + 0.18 * fine + 0.3 * z_white, rough)
metal = np.where(zinc, 1 - z_white * 0.75, metal)
height = np.where(zinc, 0.0012 * (micro - 0.5), height)

# The rubber saddles and caps, gone chalky, shiny where a gun rests.
rubber = finish == RUBBER
r_wear = smooth(0.4, 0.8, big + (mid - 0.5))
color = np.where(rubber[..., None], flat((27, 27, 26)) * (0.78 + 0.46 * fine[..., None]) + flat((48, 46, 42)) * (r_wear[..., None] * 0.14), color)
rough = np.where(rubber, 0.76 + 0.14 * fine - r_wear * 0.2, rough)
height = np.where(rubber, 0.003 * (fine - 0.5) + 0.0012 * (micro - 0.5), height)

# The padlock: brass, tarnished brown, handled bright.
brass = finish == BRASS
b_touch = smooth(0.42, 0.74, edge * 0.7 + (mid - 0.5) * 0.7 + (fine - 0.5) * 0.5)
b_color = mix(flat((98, 78, 48)), flat((186, 152, 92)), b_touch[..., None] * 0.86)
b_green = smooth(0.66, 0.84, field(noise(pts, 2.1, 12, 3)) + crevice * 0.24)
b_color = mix(b_color, flat((80, 100, 80)), b_green[..., None] * 0.34)
color = np.where(brass[..., None], b_color, color)
rough = np.where(brass, 0.38 + 0.26 * (1 - b_touch) + 0.1 * fine + 0.15 * b_green, rough)
metal = np.where(brass, 1 - b_green * 0.7, metal)
height = np.where(brass, 0.0012 * (micro - 0.5), height)

# The cable's red vinyl, faded and scuffed through to the steel here and there.
cable = finish == CABLE
c_scuff = smooth(0.62, 0.74, fine * 0.7 + mid * 0.3)
c_color = mix(flat((112, 28, 22)), flat((146, 72, 58)), smooth(0.35, 0.75, big)[..., None] * 0.6)
c_color = mix(c_color, flat((96, 92, 86)), c_scuff[..., None] * 0.7)
twist = 0.5 + 0.5 * np.sin((X + Y + Z) * 2 * np.pi / 0.42)
color = np.where(cable[..., None], c_color, color)
rough = np.where(cable, 0.36 + 0.2 * fine + c_scuff * 0.3, rough)
height = np.where(cable, 0.006 * twist, height)

# The data plate: aluminium, stamped. Invented wording.
plate = finish == PLATE
art = stencil_image(["ISSUE RACK 60   LOT 4471"], (1100, 90), bridge=False)
stamp = sample_image(ndi.gaussian_filter(art, 0.8), np.clip((Y + 4.45) / 8.9, -1, 2), np.clip((Z - 18.84) / 0.54, -1, 2)) * (nor[..., 0] > 0.6)
pc = flat((116, 116, 110)) * (0.72 + 0.34 * mid[..., None])
pc = mix(pc, np.broadcast_to(np.array((0.015, 0.015, 0.016), np.float32), (H, W, 3)), stamp[..., None] * 0.86)
pc = mix(pc, pc * 0.5, smooth(0.45, 0.8, crevice + (mid - 0.5))[..., None])
color = np.where(plate[..., None], pc, color)
rough = np.where(plate, 0.42 + 0.22 * fine + stamp * 0.3, rough)
metal = np.where(plate, 1 - stamp * 0.85, metal)
height = np.where(plate, stamp * -0.008 + 0.001 * (micro - 0.5), height)

# The clipboard, and the sign-out sheet on it: a printed header over ruled rows, filled in by hand. Invented wording.
board = finish == CLIPBOARD
color = np.where(board[..., None], flat((82, 60, 42)) * (0.74 + 0.4 * mid[..., None] + 0.2 * fine[..., None]), color)
rough = np.where(board, 0.7 + 0.14 * fine, rough)
sheet = finish == PAPER
cy, cz, tilt = facts["clip"]
tilt = np.radians(tilt)
ly = -(Y - cy) * np.sin(tilt) + (Z - cz) * np.cos(tilt)
lx = (Y - cy) * np.cos(tilt) + (Z - cz) * np.sin(tilt)
head = sample_image(stencil_image(["SIGN OUT"], (520, 120), bridge=False), np.clip((lx + 2.45) / 4.9, -1, 2), np.clip((ly + 2.1) / 1.25, -1, 2))
row_at = (-ly - 2.5) / 0.5
row = np.floor(row_at)
frac = row_at - row
rows = (row >= 0) & (row < 13)
ruled = rows * smooth(0.05, 0.015, np.abs(frac - 0.92))
pen_field = field(noise(np.stack((lx * 16.0, row * 7.3, frac * 5.0), -1)[cover], 1.0, 44, 2))
written = rows * smooth(0.5, 0.58, pen_field) * smooth(0.22, 0.12, np.abs(frac - 0.62)) * (lx < 1.9 - 0.31 * np.mod(row * 5.0, 7.0))
s_color = flat((176, 170, 148)) * (0.82 + 0.26 * big[..., None])
s_color = mix(s_color, flat((96, 74, 44)), smooth(0.58, 0.82, field(noise(pts, 0.8, 45, 3)))[..., None] * 0.42)
s_color = mix(s_color, flat((70, 72, 78)), ruled[..., None] * 0.7)
s_color = mix(s_color, flat((28, 34, 62)), written[..., None] * 0.76)
s_color = mix(s_color, flat((24, 24, 26)), np.clip(head * (nor[..., 0] > 0.6), 0, 1)[..., None] * 0.92)
color = np.where(sheet[..., None], s_color, color)
rough = np.where(sheet, 0.86 + 0.08 * fine, rough)

# ---- Dirt ----------------------------------------------------------------------------------------------------------
upward = np.clip(nor[..., 2], 0, 1)
settled = smooth(0.4, 0.9, upward * 0.84 + (big - 0.5) * 0.3 + crevice * 0.26)
floor_near = smooth(FLOOR + 16.0, FLOOR, Z)
splash = floor_near * smooth(0.46, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 14, 4)) + floor_near * 0.14)
speckle = floor_near * smooth(0.64, 0.72, field(noise(pts, 7.5, 15, 2)))
dirt = np.clip(settled * 0.52 + splash * 0.68 + speckle * 0.5, 0, 0.9)
dirt_c = flat((96, 84, 66)) * (0.75 + 0.5 * fine[..., None])
color = mix(color, dirt_c, dirt[..., None])
rough = rough * (1 - dirt) + 0.92 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.003 * (fine - 0.35)

color = color * (0.72 + 0.28 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("board painted", flush=True)
