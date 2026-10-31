"""Paint the ammo case's maps from its bakes: python paint_ammo.py <work dir> <materials dir>

Olive enamel over grey primer over steel, yellow stencils, galvanised hardware, black and grey magazines with a brass round
on each, cardboard cartons taped shut. Wear is worked out in 3D, so it runs across UV seams. Lettering is generic.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, OD, CARD, PAPER, COPPER, MAG, HARD = range(15)

pos4 = load("bake_ac_pos")
nor4 = load("bake_ac_nor")
facts4 = load("bake_ac_facts")
ao4 = load("bake_ac_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
density = json.load(open(os.path.join(WORK, "ammo_case.json")))["density"]
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
print("coverage %.2f" % cover.mean(), "finishes", np.unique(finish).tolist(), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 2.6) * 0.38, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 2.2) * 2.4 + ndi.gaussian_filter(convex, 6.0) * 3.0, 0, 1)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


big = field(noise(pts, 0.14, 1, 3))
mid = field(noise(pts, 0.7, 2, 4))
fine = field(noise(pts, 3.0, 3, 3))
micro = field(noise(pts, 10.0, 4, 2))
streak = field(noise(pts * np.array((3.6, 3.6, 0.14), np.float32), 0.3, 6, 4))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NX, NY, NZ = nor[..., 0], nor[..., 1], nor[..., 2]

steel = srgb_to_linear((160, 160, 156))
rust_c = mix(flat((58, 32, 20)), flat((122, 70, 38)), smooth(0.35, 0.8, field(noise(pts, 3.1, 8, 3))))

color = np.zeros((H, W, 3), np.float32)
rough = np.zeros((H, W), np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)


def place(art, left_to_right, up, u_mid, v_mid, long_in, tall_in):
    """Lettering from a world axis along the line and one up the letters, with its middle at u_mid, v_mid."""
    uu = 0.5 + (left_to_right - u_mid) / long_in
    vv = 0.5 + (up - v_mid) / tall_in
    return sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))


# ---- Olive enamel. ----
od = finish == OD
inside = (np.abs(X) < 6.86) & (np.abs(Y) < 11.86) & (Z > -1.8) & (Z < 3.0)
chip = edge * smooth(0.3, 0.68, mid * 0.65 + fine * 0.35) * 1.12 + (mid - 0.5) * 0.6 + (big - 0.5) * 0.4 + (fine - 0.5) * 0.85 + (micro - 0.5) * 0.3
# Dragged about on concrete: the paint goes in long scuffs low down on the body, along the box.
drag = smooth(0.62, 0.7, field(noise(pts * np.array((0.3, 0.14, 3.0), np.float32), 0.8, 21, 4)) + np.clip((-Z - 5.0) / 5.0, 0, 1) * 0.1)
chip = chip + drag * 0.2 * (Z < -2) * (~inside)
bare = smooth(0.72, 0.74, chip)
under = smooth(0.67, 0.69, chip)
green = mix(flat((72, 76, 50)), flat((96, 100, 68)), smooth(0.2, 0.7, mid * 0.5 + big * 0.5))
green = mix(green, flat((122, 124, 92)), smooth(0.35, 0.85, big + 0.14 * np.clip(NZ, 0, 1)) * 0.3)
green = green * (0.92 + 0.16 * part[..., None])
upright = 1 - np.abs(NZ)
green = green * (1 + upright[..., None] * (streak[..., None] - 0.5) * 0.34)
o_color = green.copy()

# Stencils in yellow, worn with the coat.
letter = np.zeros((H, W), np.float32)
front = od & (NX > 0.7) & (X > 6.9) & (Z < 2.1)
letter = np.maximum(letter, place(stencil_image(["AMMUNITION"], (1260, 260)), Y, Z, 0.0, -1.0, 12.6, 2.6) * front)
small = stencil_image(["5.56 MM RIFLE MAGAZINES  LOADED", "QTY 24   LOT 04417-92   KEEP DRY"], (2120, 260), bridge=False)
letter = np.maximum(letter, place(small, Y, Z, 0.0, -6.4, 21.2, 2.6) * front)
for side, sign in ((Y > 11.9, -1), (Y < -11.9, 1)):
    end = od & side & (np.abs(NY) > 0.7) & (Z < 2.1)
    letter = np.maximum(letter, place(stencil_image(["AMMUNITION"], (1000, 200)), X * sign, Z, 0.0, 0.4, 10.0, 2.0) * end)
panel = od & (NX < -0.7) & (X < -9.2)
letter = np.maximum(letter, place(stencil_image(["AMMUNITION", "5.56 MM"], (1600, 500)), -Y, Z, 0.0, 10.9, 16.0, 5.0) * panel)
letter = letter * smooth(0.12, 0.3, field(noise(pts, 3.3, 10, 3)) + (big - 0.5) * 0.15)
band = panel & (Z > 7.2) & (Z < 7.85)
o_color = mix(o_color, flat((198, 168, 58)) * (0.84 + 0.2 * mid[..., None]), np.maximum(letter, band * smooth(0.12, 0.3, fine + 0.1)) * 0.94)
o_rough = 0.46 + 0.18 * mid + 0.08 * fine + letter * 0.08
o_height = 0.0045 * (micro - 0.5) + 0.002 * (fine - 0.5) + letter * 0.0018

# The tray's slotted floor: dark card, a slot for every magazine, four of them standing empty.
floor = od & (NZ > 0.8) & (np.abs(Z + 1.7) < 0.08) & (np.abs(X) < 6.9) & (np.abs(Y) < 11.9)
slot = np.zeros((H, W), bool)
for row_x in (-4.3, -0.05, 4.2):
    for col_y in np.arange(-10.7, 3.6, 1.75):
        slot |= (np.abs(X - row_x) < 1.82) & (np.abs(Y - col_y) < 0.72)
f_color = np.where(slot[..., None], np.array((0.006, 0.006, 0.006), np.float32), flat((74, 62, 46)) * (0.8 + 0.4 * fine[..., None]))
o_color = np.where(floor[..., None], f_color, o_color)
o_rough = np.where(floor, 0.9, o_rough)
o_height = np.where(floor, np.where(slot, -0.05, 0.0), o_height)

# Through the coats, and rust that starts at the rivets and corners and only runs downhill.
o_bare = bare * (~floor)
o_under = under * (~floor)
o_color = mix(o_color, flat((104, 104, 92)), o_under)
o_color = mix(o_color, np.broadcast_to(steel, (H, W, 3)) * (0.66 + 0.42 * fine[..., None]), o_bare)
o_rust = o_bare * smooth(0.44, 0.7, field(noise(pts, 1.7, 12, 3)) + crevice * 0.4)
o_color = mix(o_color, rust_c, o_rust)
runs = smooth(0.52, 0.76, streak + crevice * 0.34) * smooth(0.25, 0.6, mid + crevice * 0.42) * (~floor)
o_color = mix(o_color, o_color * rust_c * 3.1, runs * 0.55)
o_rough = o_rough * (1 - o_bare) + 0.42 * o_bare
o_rough = o_rough * (1 - o_rust) + 0.86 * o_rust + runs * 0.1
o_metal = o_bare * (1 - o_rust)
o_height = o_height + (1 - o_under) * 0.009 + (1 - o_bare) * 0.008 + o_rust * 0.006 * (fine - 0.3)
color = np.where(od[..., None], o_color, color)
rough = np.where(od, o_rough, rough)
metal = np.where(od, o_metal, metal)
height = np.where(od, o_height, height)

# Dark hardware: skids and handles, black enamel worn through where they touch things.
hard = finish == HARD
h_bare = smooth(0.62, 0.66, edge * 0.7 + (fine - 0.5) * 0.9 + (mid - 0.5) * 0.5 + 0.26)
h_color = mix(flat((34, 36, 34)) * (0.76 + 0.5 * mid[..., None]), np.broadcast_to(steel, (H, W, 3)) * (0.5 + 0.34 * fine[..., None]), h_bare)
h_rust = smooth(0.46, 0.7, field(noise(pts, 1.4, 15, 3)) + crevice * 0.4) * np.maximum(h_bare, smooth(0.6, 0.8, streak) * 0.5)
h_color = mix(h_color, rust_c, h_rust)
color = np.where(hard[..., None], h_color, color)
rough = np.where(hard, (0.48 + 0.2 * mid) * (1 - h_rust) + 0.86 * h_rust, rough)
metal = np.where(hard, h_bare * (1 - h_rust), metal)
height = np.where(hard, 0.004 * (micro - 0.5) + h_rust * 0.006 * (fine - 0.3), height)

# Zinc-plated latches, hinges and cables.
zinc = finish == ZINC
z_rust = smooth(0.5, 0.74, mid * 0.5 + big * 0.2 + crevice * 0.5)
z_color = flat((186, 180, 150)) * (0.52 + 0.3 * mid[..., None])
z_color = mix(z_color, rust_c, z_rust * 0.5)
z_color = mix(z_color, np.broadcast_to(steel, (H, W, 3)), smooth(0.5, 0.8, edge) * 0.5)
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, 0.3 + 0.2 * fine + 0.4 * z_rust, rough)
metal = np.where(zinc, 1 - z_rust * 0.75, metal)
height = np.where(zinc, 0.0012 * (micro - 0.5), height)

# Rubber: the gasket and the handle grips, the grips ribbed.
rubber = finish == RUBBER
ribs = 0.5 + 0.5 * np.sin(X * 2 * math.pi / 0.42)
color = np.where(rubber[..., None], flat((30, 30, 30)) * (0.72 + 0.5 * fine[..., None]), color)
rough = np.where(rubber, 0.7 + 0.16 * fine, rough)
metal = np.where(rubber, 0.0, metal)
height = np.where(rubber, 0.012 * ribs * (Z < 0) + 0.002 * (micro - 0.5), height)

# Magazines from three suppliers: black polymer, tan polymer and grey anodised, every one rubbed pale on its lips.
mag = finish == MAG
style = np.mod(part * 5.0, 1.0)
alloy = style > 0.72
tan = (style > 0.48) & ~alloy
lips = smooth(3.4, 5.3, Z) * smooth(0.3, 0.7, edge + (fine - 0.5))
m_color = np.where(alloy[..., None], flat((132, 134, 130)) * (0.8 + 0.3 * mid[..., None]), flat((28, 28, 28)) * (0.8 + 0.4 * mid[..., None]))
m_color = np.where(tan[..., None], flat((122, 102, 72)) * (0.82 + 0.3 * mid[..., None]), m_color)
m_color = mix(m_color, flat((168, 170, 164)), lips * alloy * 0.7)
m_color = mix(m_color, flat((70, 70, 66)), lips * (~alloy) * 0.5)
color = np.where(mag[..., None], m_color, color)
rough = np.where(mag, np.where(alloy, 0.42 + 0.14 * fine, 0.56 + 0.14 * fine), rough)
metal = np.where(mag, np.where(alloy, 0.7, 0.0), metal)
# Stamped ribs up the sides, as a magazine's stiffening has.
wall = np.abs(NY) > 0.8
ribbed = 0.5 + 0.5 * np.sin(X * 2 * math.pi / 0.9)
height = np.where(mag, 0.003 * (micro - 0.5) + wall * 0.016 * ribbed, height)

# The rounds.
brass = finish == BRASS
color = np.where(brass[..., None], mix(flat((222, 176, 96)), flat((130, 92, 46)), smooth(0.4, 0.8, mid)), color)
rough = np.where(brass, 0.26 + 0.2 * fine, rough)
metal = np.where(brass, 1.0, metal)
height = np.where(brass, 0.001 * (micro - 0.5), height)
copper = finish == COPPER
color = np.where(copper[..., None], mix(flat((196, 116, 72)), flat((110, 62, 38)), smooth(0.4, 0.85, mid)), color)
rough = np.where(copper, 0.3 + 0.18 * fine, rough)
metal = np.where(copper, 1.0, metal)

# Cartons: corrugated card, taped along the middle and printed on top.
card = finish == CARD
c_color = flat((172, 140, 98)) * (0.84 + 0.22 * mid[..., None]) * (0.94 + 0.12 * part[..., None])
flutes = 0.5 + 0.5 * np.sin(Z * 2 * math.pi / 0.22)
c_top = card & (NZ > 0.7)
print_mask = np.zeros((H, W), np.float32)
tape = np.zeros((H, W), bool)
for (x0, x1), lines in (((-6.62, -2.3), ["5.56 X 45", "30 CTG"]), ((-2.2, 2.1), ["9 MM", "50 CTG"]), ((2.2, 6.62), ["12 GA", "25 SHELLS"])):
    here = c_top & (X > x0 - 0.1) & (X < x1 + 0.1)
    art = stencil_image(lines, (520, 340), bridge=False)
    print_mask = np.maximum(print_mask, place(art, Y, -X, 8.3, -(x0 + x1) / 2 - 0.0, 5.2, 3.4) * here)
    tape |= here & (np.abs(X - (x0 + x1) / 2) > 1.55) & (np.abs(X - (x0 + x1) / 2) < 2.3)
c_color = mix(c_color, flat((22, 20, 18)), print_mask * smooth(0.14, 0.3, fine + 0.1) * 0.9)
c_scuff = smooth(0.56, 0.72, field(noise(pts, 1.1, 22, 4)))
c_color = c_color * (1 - c_scuff[..., None] * np.array((0.2, 0.24, 0.3), np.float32))
c_color = np.where(tape[..., None], c_color * 0.45 + srgb_to_linear((206, 186, 140)) * 0.55, c_color)
color = np.where(card[..., None], c_color, color)
rough = np.where(card, np.where(tape, 0.3, 0.86 + 0.1 * fine), rough)
metal = np.where(card, 0.0, metal)
height = np.where(card, (1 - c_top) * 0.006 * flutes + 0.003 * (fine - 0.5) + tape * 0.004, height)

# The packing list inside the lid, read from the front. Close up it's a label more than a document.
paper = finish == PAPER
art = stencil_image(["PACKING LIST", "24 MAGS   3 CARTONS", "LOT 04417-92"], (1200, 700), bridge=False)
p_print = place(art, Y, Z, -2.5, 9.95, 7.4 * 0.92, 4.6 * 0.86)
p_color = flat((186, 178, 150)) * (0.78 + 0.26 * mid[..., None])
p_color = mix(p_color, flat((126, 100, 64)), smooth(0.44, 0.78, big + (mid - 0.5) * 0.7) * 0.6)
p_color = mix(p_color, flat((26, 26, 28)), p_print * 0.9)
color = np.where(paper[..., None], p_color, color)
rough = np.where(paper, 0.82, rough)
metal = np.where(paper, 0.0, metal)
height = np.where(paper, 0.002 * (fine - 0.5), height)

# Dust on what faces up, grime climbing from the floor. Not on the paper or the rounds.
upward = np.clip(NZ, 0, 1)
settled = smooth(0.42, 0.92, upward * 0.84 + (big - 0.5) * 0.36 + crevice * 0.2)
lowness = np.clip((-Z - 5.0) / 5.0, 0, 1) ** 1.5
splash = lowness * smooth(0.46, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 17, 4)) + lowness * 0.12)
dirt = np.clip(settled * 0.34 + splash * 0.56 + crevice * 0.18, 0, 0.8)
dirt = dirt * (~paper) * (~brass) * (~copper) * (~floor)
dirt_c = flat((92, 84, 70)) * (0.75 + 0.5 * fine[..., None])
color = mix(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.93 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.004 * (fine - 0.35)

color = color * (0.72 + 0.28 * ao[..., None])
# Fill the gutters from every covered texel: eroding first would lose bevel strips a pixel or two wide.
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "ac_chest_color.png"), color)
save_gray(os.path.join(OUT, "ac_chest_rough.png"), rough)
save_gray(os.path.join(OUT, "ac_chest_metal.png"), metal)
save_gray(os.path.join(OUT, "ac_chest_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "ac_chest_normal.png"), normal)
print("ammo case painted", flush=True)
