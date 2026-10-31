"""Paint the bin's maps from its bakes: python paint_bin.py <work dir> <output dir>

Brushed stainless, grained up the doors and along the hood and rails, handled round the slots and locks, kicked low down, with tea stains where water sits
and soot from the trains settled on what faces up. Enamel colour plates, anthracite plinth, worn rubber flaps, a used ashtray. A few things people have
done to it: an old sticker scraped off, a marker scribble that spells nothing. All worked out from each texel's 3D position, so it crosses UV seams.
The plates say what the old ones said. No brands.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

STEEL, DARK, RUBBER, PLATE, HARD, DOOR, HOOD, ASH = range(8)
W, D, TOP = 19.7, 8.3, 33.6
CENTRES = (-13.3, 0.0, 13.3)

pos4 = load("bake_sb_pos")
nor4 = load("bake_sb_nor")
facts4 = load("bake_sb_facts")
ao4 = load("bake_sb_ao")
H, W_PX = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "bin.json")))
density, RANGE = meta["density"], meta["range"]
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W_PX / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4
pts = pos[cover]
print("coverage %.2f, %.1f px/in" % (cover.mean(), density), flush=True)


def field(values):
    out = np.zeros((H, W_PX), np.float32)
    out[cover] = values
    return out


def solid(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W_PX, 3))


def streaks(scale, freq, seed, octaves=2):
    return field(noise(pts * np.array(scale, np.float32), freq, seed, octaves))


big = field(noise(pts, 0.06, 1, 3))
mid = field(noise(pts, 0.26, 2, 4))
fine = field(noise(pts, 1.2, 3, 3))
micro = field(noise(pts, 4.5, 4, 2))
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
crevice = np.clip((1 - ao) * 1.4, 0, 1)
up = np.clip(nor[..., 2], 0, 1)
upright = np.abs(nor[..., 2]) < 0.6
is_front = nor[..., 0] > 0.6
yl = Y - np.select([Y < -6.65, Y > 6.65], [CENTRES[0], CENTRES[2]], CENTRES[1])
# Along an upright face, whichever way it runs: where the scratches, dents and stickers are worked out.
along = np.where(np.abs(nor[..., 0]) > np.abs(nor[..., 1]), Y, X)


def on_surface(image, centre, size, z, wanted):
    """A top-down image laid flat on the upright faces that wanted picks, centred on along = centre and z."""
    uu = (along - centre) / size[0] + 0.5
    vv = (Z - z) / size[1] + 0.5
    return sample_image(image, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) * wanted


# ---- Brushed stainless ----
# Grain runs up the body and doors and along the hood. Each door came off its own sheet.
up_grain = streaks((1.0, 1.0, 0.012), 8.0, 5)
across_grain = streaks((0.012, 1.0, 1.0), 8.0, 6)
hood = finish == HOOD
grain = np.where(hood | (Z > 27.0) | (Z < 4.0), across_grain, up_grain)
tone = 1.0 + (part - 0.5) * 0.05
color = solid(190, 191, 190) * (tone * (0.92 + 0.14 * grain))[..., None]
rough = 0.34 + 0.13 * grain + 0.05 * mid
metal = np.ones((H, W_PX), np.float32)
height = 0.0007 * (grain - 0.5)

# Handled: greasy and darker in a halo under and round each slot, polished on the collar's lower lip where bags are dragged over it.
slot_near = np.exp(-(np.maximum(np.abs(yl) - 4.6, 0) / 1.5) ** 2) * np.exp(-(np.maximum(np.maximum(26.5 - Z, Z - 32.5), 0) / 2.2) ** 2) * is_front
grease = slot_near * smooth(0.25, 0.7, mid * 0.6 + fine * 0.4)
color = color * (1 - grease[..., None] * 0.26)
rough = rough - grease * 0.1
lip = smooth(0.2, 0.0, np.abs(Z - 28.75)) * (np.abs(yl) < 5.2) * is_front
rough = rough - lip * 0.14
color = color * (1 + lip[..., None] * 0.08)

# Round each lock, the key has missed: short bright arcs.
for yc in CENTRES:
    r = np.hypot(Y - yc, Z - 24.6)
    theta = np.arctan2(Z - 24.6, Y - yc)
    arcs = smooth(1.9, 0.7, r) * smooth(0.6, 1.0, r) * smooth(0.62, 0.72, field(noise(np.column_stack((np.cos(theta[cover]) * 2.0, np.sin(theta[cover]) * 2.0, r[cover] * 9.0)), 1.0, 20, 2))) * is_front
    color = mix(color, solid(214, 214, 212), arcs * 0.6)
    rough = rough + arcs * 0.14

# Shoes and trolleys: rubber marks and dull scrapes along the kick zone.
kick = smooth(13.0, 5.0, Z + (big - 0.5) * 5.0) * upright * (Z > 2.0)
marks = kick * smooth(0.62, 0.76, field(noise(pts * np.array((0.8, 0.09, 0.8), np.float32), 1.3, 21, 3))) * smooth(0.32, 0.56, mid)
color = mix(color, solid(44, 42, 40), marks * 0.62)
rough = rough + marks * 0.3
metal = metal * (1 - marks * 0.6)

# Scratches: long keys and short scrapes, on every upright face, thickest low down.
rng = np.random.default_rng(404)
SCALE = 24
scratch_img = Image.new("L", (40 * SCALE, 40 * SCALE), 0)
draw = ImageDraw.Draw(scratch_img)
for _ in range(460):
    x = rng.uniform(0, 40)
    z = float(np.clip(rng.gamma(2.0, 7.0), 0, 39))
    length = rng.uniform(0.5, 4.5) if rng.random() < 0.9 else rng.uniform(5.0, 14.0)
    a = rng.normal(0.0, 0.3) if rng.random() < 0.7 else rng.uniform(-1.5, 1.5)
    x1, z1 = x + np.cos(a) * length, z + np.sin(a) * length
    draw.line([(x * SCALE, (40 - z) * SCALE), (x1 * SCALE, (40 - z1) * SCALE)], fill=int(rng.uniform(70, 230)), width=1)
scratch = np.asarray(scratch_img, np.float32) / 255.0
scratches = on_surface(scratch, 0.0, (40.0, 40.0), 20.0, upright & ((finish == STEEL) | (finish == DOOR)))
color = mix(color, solid(226, 226, 224), scratches * 0.62)
rough = rough + scratches * 0.16
height = height - scratches * 0.004

# Dents, knocked in low on the corners and once on a door. Only in the normal map, and shallow.
for wanted, c_along, c_z, radius, depth in (
    (nor[..., 0] > 0.6, -18.2, 8.0, 1.5, 0.06),
    (nor[..., 0] > 0.6, 2.8, 9.5, 2.2, 0.08),
    (nor[..., 0] > 0.6, 15.6, 6.4, 1.2, 0.05),
    (nor[..., 1] > 0.6, 5.5, 7.5, 1.9, 0.08),
    (nor[..., 1] < -0.6, -3.0, 11.0, 2.4, 0.07),
    (nor[..., 0] < -0.6, -9.0, 6.0, 2.0, 0.07),
):
    dent = np.exp(-((along - c_along) ** 2 + (Z - c_z) ** 2) / radius ** 2) * wanted
    height = height - dent * depth
    color = color * (1 - dent[..., None] * 0.05)

# Tea stain: rust-brown bloom where water sits, in crevices and round rivets, on the lower seams, running down a little.
bloom = smooth(0.42, 0.85, crevice * 0.9 + (mid - 0.5) * 0.7 + (fine - 0.5) * 0.3) * (Z < 33.0)
runs_tea = smooth(0.58, 0.78, streaks((1.0, 1.0, 0.09), 0.8, 7, 3)) * smooth(0.3, 0.6, mid) * smooth(0.0, 6.0, Z) * smooth(14.0, 5.0, Z) * upright
tea = np.clip(bloom * 0.6 + runs_tea * 0.3, 0, 1)
color = mix(color, solid(132, 110, 86) * (0.8 + 0.4 * fine[..., None]), tea * 0.3)
metal = metal * (1 - tea * 0.2)
rough = rough + tea * 0.14

# Rain blown under the shed has run off the hood's lip: darker streaks down the header and doors, stopping at random.
fall = streaks((1.0, 1.0, 0.04), 0.9, 8, 4)
reach = np.clip((33.0 - Z) / 22.0, 0, 1)
runs = smooth(0.52, 0.74, fall) * (1 - smooth(0.35, 1.0, reach + (mid - 0.5) * 0.5)) * is_front * (Z < 33.0)
color = color * (1 - runs[..., None] * np.array((0.28, 0.28, 0.26), np.float32))
rough = rough + runs * 0.1

# Fingerprints and wipe marks from cleaning: broad changes in the shine.
wipe = smooth(0.3, 0.7, streaks((0.15, 0.15, 0.4), 0.32, 9, 3))
rough = rough + (wipe - 0.5) * 0.09

# ---- What people have done to it ----
# A sticker on the third door, scraped off long ago: glue ghost, torn scraps and scrape lines.
ghost = np.zeros((96, 144), np.float32)
ghost[6:90, 6:138] = 1
ghost = ndi.gaussian_filter(ghost, 1.2)
g = on_surface(ghost, 13.3, (6.0, 4.0), 10.6, (finish == DOOR) & is_front) * smooth(0.25, 0.42, fine + (mid - 0.5) * 0.4)
color = mix(color, solid(138, 136, 128), g * 0.4)
metal = metal * (1 - g * 0.6)
rough = rough + g * 0.26
scrap = g * smooth(0.7, 0.75, field(noise(pts, 1.5, 22, 3)))
color = mix(color, solid(206, 204, 194), scrap * 0.8)
height = height + scrap * 0.006


# A marker scribble on the end panel, half cleaned off, which spells nothing: one running hand of loops.
def scribble(seed, size, width):
    r = np.random.default_rng(seed)
    t = np.linspace(0.0, 1.0, 900)
    swing = np.interp(t, np.linspace(0, 1, 12), r.uniform(0.45, 1.0, 12))
    x = 0.08 + 0.84 * t + 0.05 * np.sin(t * 58.0 + 0.7)
    y = 0.5 + 0.36 * swing * np.sin(t * 46.0 + 1.3 * np.sin(t * 9.0))
    points = list(zip(x * size[0], y * size[1]))
    img = Image.new("L", size, 0)
    ImageDraw.Draw(img).line(points, fill=255, width=width, joint="curve")
    return ndi.gaussian_filter(np.asarray(img, np.float32) / 255.0, 0.8)


ink = on_surface(scribble(31, (480, 200), 6), 1.0, (11.0, 4.6), 18.0, (nor[..., 1] < -0.6) & (finish == STEEL))
ink = ink * smooth(0.28, 0.52, fine * 0.6 + mid * 0.4)
color = mix(color, solid(24, 24, 30), ink * 0.66)
metal = metal * (1 - ink * 0.75)
rough = rough * (1 - ink * 0.7) + 0.46 * ink * 0.7

# The cleaning label on the outer end, faded: the operator's number and tick boxes, no one's name.
label = Image.new("RGB", (400, 260), (222, 220, 208))
d = ImageDraw.Draw(label)
bold = ImageFont.truetype(os.path.join(ROOT, "Assets", "fonts", "Dinish-Bold.ttf"), 56)
regular = ImageFont.truetype(os.path.join(ROOT, "Assets", "fonts", "Dinish-Regular.ttf"), 30)
d.rectangle((0, 0, 400, 66), fill=(46, 54, 66))
d.text((16, 5), "RHD 0412", font=bold, fill=(226, 226, 216))
d.text((16, 76), "Reinigung", font=regular, fill=(40, 40, 42))
for row in range(3):
    for col in range(7):
        x0, y0 = 16 + col * 53, 118 + row * 45
        d.rectangle((x0, y0, x0 + 46, y0 + 38), outline=(50, 50, 52), width=2)
        if row == 0 or (row == 1 and col < 3):
            d.line((x0 + 8, y0 + 20, x0 + 20, y0 + 31, x0 + 40, y0 + 7), fill=(30, 40, 92), width=4)
label_rgb = np.asarray(label, np.float32) / 255.0
wanted_label = (nor[..., 1] > 0.6) & (finish == STEEL)
label_cover = on_surface(np.ones(label_rgb.shape[:2], np.float32), 2.0, (4.6, 3.0), 27.0, wanted_label)
label_cover = (label_cover > 0.5) & (smooth(0.12, 0.3, fine * 0.5 + mid * 0.5) > 0.3)
label_color = np.stack([on_surface(label_rgb[..., c] ** 2.2, 2.0, (4.6, 3.0), 27.0, wanted_label) for c in range(3)], -1)
color = np.where(label_cover[..., None], label_color * (0.74 + 0.2 * mid[..., None]), color)
metal = np.where(label_cover, 0.0, metal)
rough = np.where(label_cover, 0.52 + 0.1 * fine, rough)

# Pockets are black behind the shadow lines and in the throats of the slots.
inner_door = (X < 8.12) & (X > 4.0) & (np.abs(yl) < 5.45) & (Z > 3.9) & (Z < 27.1) & (finish == STEEL)
inner_slot = (X < 8.1) & (X > 4.0) & (np.abs(yl) < 4.9) & (Z > 28.9) & (Z < 31.9) & (finish == STEEL)
inner = inner_door | inner_slot
color = np.where(inner[..., None], solid(18, 18, 19), color)
rough = np.where(inner, 0.82, rough)
metal = np.where(inner, 0.0, metal)

# ---- The hood: soot, dust and the odd cigarette put out on it ----
hood_top = hood & (nor[..., 2] > 0.6)
film = hood_top * smooth(0.2, 0.75, big * 0.6 + mid * 0.4)
color = mix(color, solid(88, 87, 84) * (0.8 + 0.4 * fine[..., None]), film * 0.42)
rough = rough + film * 0.26
metal = metal * (1 - film * 0.4)
# Rain marks running down the slope, towards the lip.
slope_runs = smooth(0.54, 0.76, streaks((0.05, 1.0, 1.0), 0.7, 10, 3)) * hood_top
color = color * (1 - slope_runs[..., None] * 0.18)
for k, (sx, sy) in enumerate(((-2.4, 3.3), (-3.4, -3.8), (-1.2, -2.7), (-4.1, 5.2))):
    d2 = (X - sx) ** 2 + ((Y - sy) * (0.8 if k % 2 else 1.3)) ** 2
    burn = np.exp(-d2 / 0.06) * hood_top * smooth(0.2, 0.5, micro + 0.2)
    color = mix(color, solid(44, 38, 32), np.clip(burn * 0.8, 0, 1))
    metal = metal * (1 - np.clip(burn * 0.8, 0, 1) * 0.9)
    rough = rough + burn * 0.3

# ---- Anthracite on the plinth, spine and rails, knocked to bare metal on its edges ----
dark = finish == DARK
d_color = solid(50, 52, 55) * (0.86 + 0.2 * mid[..., None])
d_rough = 0.56 + 0.12 * fine
chips = smooth(0.6, 0.75, crevice * 0.0 + mid * 0.5 + fine * 0.5) * smooth(3.0, 0.5, Z) * upright
d_color = mix(d_color, solid(118, 116, 110), chips * 0.5)

# ---- Enamel plates ----
FONT = os.path.join(ROOT, "Assets", "fonts", "Dinish-Bold.ttf")


def plate_art(name, fill, ink, label_text):
    size = 400
    img = Image.new("RGB", (size, size), fill)
    d = ImageDraw.Draw(img)
    cx, cy = size / 2, 148
    if name == "paper":
        d.rectangle((cx - 84, cy - 68, cx + 84, cy + 68), outline=ink, width=14)
        for k in range(4):
            d.line((cx - 60, cy - 36 + 24 * k, cx + (12 if k == 0 else 60), cy - 36 + 24 * k), fill=ink, width=10)
    elif name == "pack":
        d.rectangle((cx - 92, cy - 36, cx - 12, cy + 72), outline=ink, width=14)
        d.polygon(((cx - 92, cy - 36), (cx - 52, cy - 72), (cx - 12, cy - 36)), outline=ink, width=12)
        d.rounded_rectangle((cx + 20, cy - 28, cx + 80, cy + 72), 16, outline=ink, width=14)
        d.rectangle((cx + 38, cy - 64, cx + 62, cy - 28), fill=ink)
    else:
        d.polygon(((cx - 80, cy + 72), (cx + 80, cy + 72), (cx + 60, cy - 36), (cx - 60, cy - 36)), outline=ink, width=14)
        d.line((cx - 28, cy - 36, cx - 16, cy - 68, cx + 16, cy - 68, cx + 28, cy - 36), fill=ink, width=12)
    font_size = 88
    while ImageFont.truetype(FONT, font_size).getlength(label_text) > size * 0.86:
        font_size -= 2
    d.text((cx, 322), label_text, font=ImageFont.truetype(FONT, font_size), fill=ink, anchor="mm")
    return (np.asarray(img, np.float32) / 255.0) ** 2.2


p_color = np.array(solid(120, 120, 118))
is_plate = finish == PLATE
for yc, art in zip(CENTRES, (
    plate_art("paper", (26, 82, 160), (240, 240, 236), "Papier"),
    plate_art("pack", (232, 186, 34), (22, 22, 22), "Verpackung"),
    plate_art("rest", (92, 96, 100), (240, 240, 236), "Restabfall"),
)):
    uu = np.clip((Y - yc + 3.6) / 7.2, 0, 1)
    vv = np.clip((Z - 14.0) / 7.2, 0, 1)
    here = is_plate & (np.abs(Y - yc) < 4.0)
    for c in range(3):
        p_color[..., c] = np.where(here, sample_image(art[..., c], uu, vv), p_color[..., c])
# Enamel: faded a little, chipped pale on its edges, scratched.
p_along = np.minimum(3.6 - np.abs(yl), 3.6 - np.abs(Z - 17.6))
p_chip = smooth(0.34, 0.06, p_along + (fine - 0.5) * 0.3) * smooth(0.5, 0.72, mid * 0.5 + fine * 0.5)
p_color = p_color * 0.9 + 0.022
p_color = mix(p_color, solid(190, 190, 186), p_chip * 0.85)
p_scratch = on_surface(scratch, 0.0, (40.0, 40.0), 20.0, is_plate)
p_color = mix(p_color, solid(216, 216, 212), p_scratch * 0.16)
p_rough = 0.3 + 0.1 * fine + p_chip * 0.3 + p_scratch * 0.2
p_color = mix(p_color, solid(112, 92, 68), smooth(0.5, 0.9, crevice) * 0.4)

# ---- Rubber: dull, shiny where the bags rub, dusty at its tips ----
rub = finish == RUBBER
r_color = solid(26, 26, 26) * (0.86 + 0.26 * fine[..., None])
r_color = mix(r_color, solid(70, 66, 60), smooth(30.4, 29.9, Z) * 0.34)
r_rough = 0.66 - smooth(30.6, 30.0, Z) * 0.14 + 0.08 * fine

# ---- Rivets, hinges, the lock: dull zinc, stained ----
hard = finish == HARD
h_color = mix(solid(152, 152, 148) * (0.84 + 0.26 * fine[..., None]), solid(116, 90, 62), smooth(0.45, 0.8, mid) * 0.45)
h_rough = 0.42 + 0.16 * fine
# The lock's triangular socket.
for yc in CENTRES:
    dy, dz = Y - yc, Z - 24.6
    tri = np.maximum.reduce([dz - 0.2, -dz * 0.5 + dy * 0.866 - 0.1, -dz * 0.5 - dy * 0.866 - 0.1]) < 0
    socket = hard & (np.abs(X - 8.3) < 0.1) & tri & (np.hypot(dy, dz) < 0.34)
    h_color = np.where(socket[..., None], solid(14, 14, 14), h_color)
    h_rough = np.where(socket, 0.8, h_rough)

# ---- The ashtray: a stainless cup, its dish burnt black with perforations, ash in it ----
ash = finish == ASH
dish = ash & (np.hypot(X + 5.9, Y) < 2.2) & (Z < 39.5)
a_color = solid(166, 166, 162) * (0.82 + 0.24 * across_grain[..., None])
a_color = mix(a_color, solid(84, 74, 64), smooth(0.4, 0.8, mid) * 0.4)
a_rough = 0.42 + 0.14 * fine
holes = np.zeros((H, W_PX), bool)
for r_hole, count, shift in ((0.0, 1, 0.0), (0.55, 6, 0.2), (1.1, 12, 0.0), (1.62, 18, 0.13)):
    for k in range(count):
        ang = shift + 2 * np.pi * k / count
        holes |= np.hypot(X + 5.9 - r_hole * np.cos(ang), Y - r_hole * np.sin(ang)) < 0.15
tar = solid(26, 22, 18) * (0.7 + 0.6 * micro[..., None])
tar = mix(tar, solid(120, 116, 108), smooth(0.56, 0.72, fine * 0.6 + micro * 0.4) * 0.5)
a_color = np.where(dish[..., None], tar, a_color)
a_color = np.where((dish & holes)[..., None], solid(4, 4, 4), a_color)
a_rough = np.where(dish, 0.82, a_rough)
a_metal = np.where(dish, 0.0, 1.0).astype(np.float32)

is_steel_like = (finish == STEEL) | (finish == DOOR) | hood
color = np.where(is_steel_like[..., None], color, solid(120, 120, 118))
color = np.where(dark[..., None], d_color, color)
color = np.where(is_plate[..., None], p_color, color)
color = np.where(rub[..., None], r_color, color)
color = np.where(hard[..., None], h_color, color)
color = np.where(ash[..., None], a_color, color)
rough = np.where(dark, d_rough, np.where(is_plate, p_rough, np.where(rub, r_rough, np.where(hard, h_rough, np.where(ash, a_rough, rough)))))
metal = np.where(dark, chips * 0.5, np.where(is_plate | rub, 0.0, np.where(hard, 1.0, np.where(ash, a_metal, metal)))).astype(np.float32)
height = np.where(is_steel_like, height, np.where(dark, 0.003 * (fine - 0.5), np.where(rub, 0.003 * (micro - 0.5), 0.0)))
# Enamel holds a very faint orange peel.
height = height + is_plate * 0.0012 * (fine - 0.5)

# Everything collects dust low down and on what faces up, and grime in its corners.
floor_dirt = smooth(9.0, 0.5, Z + (mid - 0.5) * 3.6) * upright
color = mix(color, solid(72, 70, 66) * (0.82 + 0.3 * fine[..., None]), floor_dirt * 0.42)
rough = rough * (1 - floor_dirt * 0.6) + 0.82 * floor_dirt * 0.6
metal = metal * (1 - floor_dirt * 0.5)
dust = smooth(0.6, 0.95, up * 0.72 + (big - 0.5) * 0.3 + (fine - 0.5) * 0.2) * 0.26 * (1 - hood_top * 0.5)
color = mix(color, solid(118, 116, 110), dust)
rough = rough * (1 - dust) + 0.9 * dust
metal = metal * (1 - dust)
grime = smooth(0.25, 0.9, crevice) * smooth(0.3, 0.7, mid) * (~inner)
color = mix(color, solid(36, 35, 33), grime * 0.5)
rough = rough * (1 - grime * 0.5) + 0.82 * grime * 0.5
metal = metal * (1 - grime * 0.4)

color = color * (0.78 + 0.22 * ao[..., None])
# Seen in s&box on Railhead: full metal draws near black where the reflections are dim, and 0.35 reads as white paint. The old bin's stainless is 0.85.
metal = metal * 0.68
normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope across an island's border sees the flat gutter and draws a line down the seam, so wide islands take their border's normal
# from just inside. Thin islands, which have no inside, keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.12, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "sb_bin_color.png"), color)
save_gray(os.path.join(OUT, "sb_bin_rough.png"), rough)
save_gray(os.path.join(OUT, "sb_bin_metal.png"), metal)
save_gray(os.path.join(OUT, "sb_bin_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "sb_bin_normal.png"), normal)
print("bin painted", flush=True)
