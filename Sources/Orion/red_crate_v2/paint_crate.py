"""Paint the red crate's maps from its bakes: python paint_crate.py <work dir> <materials dir>

Signal red on pressed steel, chalked by the sun, chipped through primer at the ribs' crowns and scraped by whatever it has been stacked against; rust bleeding from the rails; a charcoal frame with bright steel where forks rub;
white stencils that cross the corrugations. Wear is worked out in 3D, with no bullet marks. ORN and every marking are the map's own.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import FONT, OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

ZINC, BRASS, RUBBER, WELD, PLATE, RED, STEEL, INNER, CARD, SEAL = 3, 4, 5, 6, 7, 9, 10, 11, 12, 13

pos4 = load("bake_rc_pos")
nor4 = load("bake_rc_nor")
facts4 = load("bake_rc_facts")
ao4 = load("bake_rc_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
density = json.load(open(os.path.join(WORK, "red_crate.json")))["density"]
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = ao4[..., 0] > 0.001
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
print("coverage %.2f" % cover.mean(), "finishes", np.unique(finish).tolist(), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 2.4) * 0.4, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 2.0) * 2.2 + ndi.gaussian_filter(convex, 5.0) * 2.6, 0, 1)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


def place(art, left_to_right, up, u_mid, v_mid, long_in, tall_in):
    uu = 0.5 + (left_to_right - u_mid) / long_in
    vv = 0.5 + (up - v_mid) / tall_in
    return sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))


big = field(noise(pts, 0.07, 1, 3))
mid = field(noise(pts, 0.42, 2, 4))
fine = field(noise(pts, 2.4, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))
streak = field(noise(pts * np.array((3.4, 3.4, 0.12), np.float32), 0.3, 6, 4))
scrape = field(noise(pts * np.array((0.2, 0.2, 7.0), np.float32), 0.5, 7, 3))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NX, NY, NZ = nor[..., 0], nor[..., 1], nor[..., 2]
upward = np.clip(NZ, 0, 1)

red = finish == RED
steel = (finish == STEEL) | (finish == WELD)
inner = finish == INNER
zinc = finish == ZINC
brass = finish == BRASS
rubber = finish == RUBBER
plate = finish == PLATE
card = finish == CARD
seal = finish == SEAL

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

# The crowns of the ribs stand proud, so they take the knocks; the valleys hold the dirt.
crown = np.clip(np.maximum(smooth(15.95, 16.15, np.abs(X)) * (np.abs(NX) > 0.8), smooth(20.85, 21.05, np.abs(Y)) * (np.abs(NY) > 0.8)), 0, 1)
valley = red & (Z < 35.0) & (Z > 7.0) & (crown < 0.5) & (np.abs(NZ) < 0.3)

# ---- White stencils. Each face reads from outside it, and they cross the ribs. ----
def mark_image():
    """Orion's own mark: a planet with an orbit round it."""
    art = Image.new("L", (800, 800), 0)
    d = ImageDraw.Draw(art)
    d.ellipse((272, 272, 528, 528), fill=255)
    orbit = Image.new("L", (800, 800), 0)
    o = ImageDraw.Draw(orbit)
    o.ellipse((40, 290, 760, 510), outline=255, width=30)
    orbit = orbit.rotate(24, resample=Image.BICUBIC)
    gap = Image.new("L", (800, 800), 0)
    g = ImageDraw.Draw(gap)
    g.ellipse((10, 260, 790, 540), outline=255, width=30)
    gap = gap.rotate(24, resample=Image.BICUBIC)
    a = np.asarray(art, np.float32)
    a = np.where(np.asarray(orbit) > 128, 0, a)
    a = np.where(np.asarray(gap) > 128, 255, a)
    return a / 255.0


def arrows_image():
    art = Image.new("L", (640, 640), 0)
    d = ImageDraw.Draw(art)
    for cx in (190, 450):
        d.polygon([(cx, 60), (cx + 100, 230), (cx + 38, 230), (cx + 38, 500), (cx - 38, 500), (cx - 38, 230), (cx - 100, 230)], fill=255)
    d.rectangle((60, 545, 580, 590), fill=255)
    return np.asarray(art, np.float32) / 255.0


front = red & (NX > 0.25) & (X > 15)
back = red & (NX < -0.25) & (X < -15)
near_end = red & (NY < -0.25) & (Y < -20)
far_end = red & (NY > 0.25) & (Y > 20)
on_top = red & (NZ > 0.7) & (Z > 39)
sten = np.zeros((H, W), np.float32)


def stamp(art, mask, across, u_mid, v_mid, long_in, tall_in):
    global sten
    sten = np.maximum(sten, place(art, across, Z, u_mid, v_mid, long_in, tall_in) * mask)


orn = stencil_image(["ORN"], (900, 420))
gse = stencil_image(["GSE-4417"], (1200, 300))
gross = stencil_image(["MAX GROSS 450 KG"], (1500, 200), bridge=False)
keep_dry = stencil_image(["THIS WAY UP"], (1000, 180), bridge=False)
number = stencil_image(["4417"], (900, 380))
mark, arrows = mark_image(), arrows_image()
# Front (+X): its right is +Y, and the card holder takes the upper right.
stamp(mark, front, Y, -14.6, 26.6, 6.0, 6.0)
stamp(orn, front, Y, -7.0, 26.6, 9.2, 4.4)
stamp(gse, front, Y, -9.8, 15.2, 14.4, 3.6)
stamp(gross, front, Y, -9.8, 11.0, 14.0, 1.9)
stamp(arrows, front, Y, 9.8, 14.4, 7.4, 7.4)
stamp(keep_dry, front, Y, 9.8, 9.6, 9.4, 1.7)
# Back (-X): its right is -Y.
stamp(mark, back, -Y, -14.6, 26.6, 6.0, 6.0)
stamp(orn, back, -Y, -7.0, 26.6, 9.2, 4.4)
stamp(gse, back, -Y, 9.8, 26.6, 14.4, 3.6)
stamp(arrows, back, -Y, 9.8, 14.4, 7.4, 7.4)
stamp(gross, back, -Y, -9.8, 11.0, 14.0, 1.9)
# Ends: the number under the handle, either way round.
stamp(number, near_end, X, 0.0, 15.0, 15.6, 6.6)
stamp(number, far_end, -X, 0.0, 15.0, 15.6, 6.6)
stamp(mark, near_end, X, 0.0, 30.6, 5.0, 5.0)
stamp(mark, far_end, -X, 0.0, 30.6, 5.0, 5.0)
sten = np.maximum(sten, place(number, Y, -X, 0.0, 0.0, 15.6, 6.6) * on_top * (Z > 39.2))
# On the frame, above each pocket.
fork = stencil_image(["FORK"], (600, 220), bridge=False)
low_rail = steel & (Z > 5.6) & (Z < 7.6)
for y in (-10.0, 10.0):
    sten = np.maximum(sten, place(fork, Y, Z, y, 6.6, 3.8, 1.4) * low_rail * (NX > 0.8))
    sten = np.maximum(sten, place(fork, -Y, Z, -y, 6.6, 3.8, 1.4) * low_rail * (NX < -0.8))
# A worn stencil: sprayed thinner in places, and worn off the crowns.
sprayed = sten * smooth(0.08, 0.3, field(noise(pts, 2.9, 10, 3)) + (big - 0.5) * 0.2 + 0.14) * (1 - crown * smooth(0.62, 0.8, scrape) * 0.5)

# ---- The red. ----
chalk = smooth(0.32, 0.8, big * 0.62 + upward * 0.42 + (mid - 0.5) * 0.22)
r_color = mix(flat((142, 32, 25)) * (0.86 + 0.26 * mid[..., None]), flat((166, 64, 50)), chalk * 0.74)
# Water has run down the walls after rain, cleaner under the rails, and paler at the crowns where it's rubbed.
r_color = mix(r_color, r_color * np.array((0.74, 0.7, 0.68), np.float32), smooth(0.5, 0.78, streak) * 0.34)
r_color = mix(r_color, flat((208, 206, 192)) * (0.82 + 0.18 * fine[..., None]), sprayed[..., None] * 0.94 * (1 - chalk[..., None] * 0.14))

chips = edge * 0.34 + (fine - 0.5) * 0.92 + (mid - 0.5) * 0.46 + crown * 0.05
r_primer = smooth(0.42, 0.46, chips)
r_bare = smooth(0.47, 0.52, chips + (fine - 0.5) * 0.14)
rust_c = mix(flat((54, 28, 18)), flat((126, 66, 34)), smooth(0.35, 0.8, field(noise(pts, 3.2, 8, 3))))
r_color = mix(r_color, flat((92, 88, 78)), r_primer * 0.92)
r_color = mix(r_color, rust_c, r_bare)
# Long scrapes along the crowns, from sliding against whatever it was stacked by.
scraped = crown * smooth(0.7, 0.76, scrape + (mid - 0.5) * 0.5) * smooth(0.46, 0.66, big + (fine - 0.5) * 0.3)
r_color = mix(r_color, flat((120, 104, 92)), scraped * 0.5)
# Rust bleeding out under the rails and running down, and pooling at the foot of each wall.
under_top = smooth(33.6, 22.0, Z) * (Z < 33.6) * (Z > 21.0)
under_mid = smooth(19.7, 8.0, Z) * (Z < 19.7)
bleed = smooth(0.54, 0.8, streak + crevice * 0.12) * np.clip(under_top + under_mid * (np.abs(NX) > 0.2), 0, 1) * smooth(0.28, 0.6, mid)
pool = smooth(11.5, 7.5, Z + (mid - 0.5) * 3.0) * smooth(0.38, 0.62, fine * 0.5 + mid * 0.5 + crevice * 0.24)
r_rust = np.clip(bleed * 0.5 + pool * 0.6, 0, 1) * (Z < 35.4) * (Z > 5)
r_color = mix(r_color, rust_c * 1.06, r_rust)
color = np.where(red[..., None], r_color, color)
rough = np.where(red, (0.42 + 0.18 * chalk + 0.1 * mid + 0.06 * fine) * (1 - r_primer) + r_primer * 0.72 + sprayed * 0.1 + r_rust * 0.22 + scraped * 0.08, rough)
metal = np.where(red, scraped * 0.6 * (1 - r_rust), metal)
peel = 0.0032 * (micro - 0.5) + 0.0024 * (fine - 0.5)
height = np.where(red, peel + (1 - r_primer) * 0.012 + sprayed * 0.002 - scraped * 0.003 + (r_bare + r_rust * 0.5) * 0.01 * (fine - 0.2), height)

# ---- The frame: charcoal, chipped, bright where forks and neighbours have rubbed it. ----
s_field = edge * 0.52 + (fine - 0.5) * 0.9 + (mid - 0.5) * 0.46
s_chip = smooth(0.44, 0.5, s_field)
s_bright = smooth(0.54, 0.58, s_field)
s_color = flat((46, 46, 44)) * (0.8 + 0.42 * mid[..., None])
s_color = mix(s_color, flat((68, 64, 56)), chalk * 0.4)
s_color = mix(s_color, flat((212, 210, 198)) * 0.86, sprayed[..., None] * low_rail[..., None])
s_color = mix(s_color, flat((86, 66, 50)), s_chip * 0.86)
s_color = mix(s_color, flat((128, 124, 116)), s_bright * smooth(0.5, 0.3, fine) * 0.8)
# Rust on the castings and sills, low down and in the joints.
s_rust = smooth(0.68, 0.88, field(noise(pts, 1.7, 13, 3)) + crevice * 0.16 + smooth(7.0, 0.0, Z) * 0.14 + s_chip * 0.08)
s_color = mix(s_color, rust_c, s_rust * 0.7)
color = np.where(steel[..., None], s_color, color)
rough = np.where(steel, 0.5 + 0.16 * mid + 0.08 * fine + s_chip * 0.14 + s_rust * 0.24, rough)
metal = np.where(steel, s_bright * smooth(0.5, 0.3, fine) * (1 - s_rust) * 0.8, metal)
height = np.where(steel, 0.003 * (micro - 0.5) + (1 - s_chip) * 0.008 + s_rust * 0.01 * (fine - 0.2), height)

# Inside the pockets: black paint with the forks' bright tracks along the floor, by the mouth.
tracks = (NZ > 0.7) * smooth(0.4, 0.7, field(noise(pts * np.array((0.15, 2.2, 0.15), np.float32), 0.6, 14, 3))) * smooth(9.0, 15.0, np.abs(X))
i_color = mix(flat((22, 22, 21)) * (0.8 + 0.5 * mid[..., None]), flat((112, 106, 96)), tracks * 0.7)
color = np.where(inner[..., None], i_color, color)
rough = np.where(inner, 0.72 - tracks * 0.24, rough)
metal = np.where(inner, tracks * 0.7, metal)

# Plated latches, bolts and pins: dull zinc, chalked in the joints, and spotted with rust.
z_white = smooth(0.54, 0.76, streak + crevice * 0.3)
z_rust = smooth(0.66, 0.82, field(noise(pts, 3.4, 15, 3)) + crevice * 0.2)
z_color = flat((162, 160, 150)) * (0.56 + 0.34 * mid[..., None])
z_color = mix(mix(z_color, flat((176, 174, 164)) * 0.74, z_white * 0.6), rust_c, z_rust * 0.74)
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, (0.34 + 0.2 * fine + z_white * 0.3) * (1 - z_rust) + z_rust * 0.84, rough)
metal = np.where(zinc, (1 - z_white * 0.6) * (1 - z_rust), metal)
height = np.where(zinc, 0.002 * (micro - 0.5) + z_rust * 0.006 * (fine - 0.2), height)

# The padlock, brass gone brown, bright on its corners.
b_bright = smooth(0.42, 0.64, edge * 0.8 + (fine - 0.5) * 0.5)
b_color = mix(flat((118, 92, 46)) * (0.72 + 0.34 * mid[..., None]), flat((196, 164, 92)), b_bright)
color = np.where(brass[..., None], b_color, color)
rough = np.where(brass, 0.48 - b_bright * 0.2 + 0.1 * fine, rough)
metal = np.where(brass, 1.0, metal)

# Rubber: the gasket and the handles' grips, grey with dust.
g_ribs = (0.5 + 0.5 * np.sin(X * 8.0)) * smooth(23.5, 23.7, Z) * smooth(24.5, 24.3, Z)
color = np.where(rubber[..., None], flat((30, 30, 29)) * (0.8 + 0.5 * mid[..., None]), color)
rough = np.where(rubber, 0.76 + 0.12 * fine, rough)
metal = np.where(rubber, 0.0, metal)
height = np.where(rubber, g_ribs * 0.02 + 0.002 * (micro - 0.5), height)

# The seal, a yellow plastic tag with its number.
s_num = place(stencil_image(["0417"], (600, 300), bridge=False), Y, Z, -11.46, 32.7, 0.8, 0.42) * seal
color = np.where(seal[..., None], mix(flat((206, 168, 36)) * (0.84 + 0.22 * mid[..., None]), np.broadcast_to(np.array((0.02, 0.02, 0.02), np.float32), (H, W, 3)), s_num * 0.9), color)
rough = np.where(seal, 0.4 + 0.1 * fine, rough)
metal = np.where(seal, 0.0, metal)

# The card: a form printed in black, gone yellow, with a stain in one corner. Generic.
sheet = Image.new("L", (900, 660), 0)
d = ImageDraw.Draw(sheet)
head = ImageFont.truetype(FONT, 74)
body = ImageFont.truetype(FONT, 46)
d.text((30, 18), "ORION AEROSPACE", 255, font=head)
d.rectangle((30, 108, 870, 114), fill=255)
for k, text in enumerate(("GROUND SUPPORT EQUIPMENT", "UNIT  GSE-4417", "LAST INSPECTED  03-24", "STORE AT  YARD 3", "RETURN TO  B3 STORES")):
    d.text((30, 136 + k * 84), text, 255, font=body)
    d.rectangle((30, 196 + k * 84, 870, 199 + k * 84), fill=255)
print_art = np.asarray(sheet, np.float32) / 255.0
printed = place(print_art, Y, Z, 9.5, 27.7, 7.8, 5.6) * card
stain = smooth(0.4, 0.7, mid * 0.6 + big * 0.6 + smooth(28.0, 25.0, Z) * 0.2)
c_color = mix(flat((214, 206, 176)), flat((160, 138, 92)), stain * 0.74)
c_color = mix(c_color, np.broadcast_to(np.array((0.03, 0.03, 0.035), np.float32), (H, W, 3)), printed * 0.84)
color = np.where(card[..., None], c_color, color)
rough = np.where(card, 0.82, rough)
metal = np.where(card, 0.0, metal)

# The data plate, stamped.
words = place(stencil_image(["ORN  GSE TRANSIT CRATE", "TARE 96 KG   GROSS 450 KG", "SER 4417   TYPE T2   03-19"], (1100, 390), bridge=False), Y, Z, 5.8, 35.05, 3.6, 1.28) * plate
p_color = flat((172, 172, 164)) * (0.72 + 0.34 * mid[..., None])
p_color = mix(p_color, np.broadcast_to(np.array((0.015, 0.015, 0.016), np.float32), (H, W, 3)), words * 0.85)
color = np.where(plate[..., None], p_color, color)
rough = np.where(plate, 0.42 + 0.22 * fine + words * 0.3, rough)
metal = np.where(plate, 1 - words * 0.85, metal)
height = np.where(plate, words * 0.012 + 0.001 * (micro - 0.5), height)

# Yard dirt: dust on what faces up and in the valleys, and grime climbing from the ground.
settled = smooth(0.44, 0.94, upward * 0.8 + (big - 0.5) * 0.36 + crevice * 0.2)
lowness = np.clip((13.0 - Z) / 13.0, 0, 1) ** 1.5
splash = lowness * smooth(0.46, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 17, 4)) + lowness * 0.14)
dirt = np.clip(settled * 0.3 + splash * 0.6 + crevice * 0.24 + valley * smooth(0.46, 0.7, streak) * 0.18, 0, 0.82) * (~plate) * (~card) * (~seal)
color = mix(color, flat((78, 70, 58)) * (0.75 + 0.5 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.92 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.004 * (fine - 0.35)

color = color * (0.74 + 0.26 * ao[..., None])
# Fill the gutters from every covered texel: eroding first would lose bevel strips a pixel or two wide.
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "rc_crate_color.png"), color)
save_gray(os.path.join(OUT, "rc_crate_rough.png"), rough)
save_gray(os.path.join(OUT, "rc_crate_metal.png"), metal)
save_gray(os.path.join(OUT, "rc_crate_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "rc_crate_normal.png"), normal)
print("red crate painted", flush=True)
