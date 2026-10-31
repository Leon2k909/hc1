"""Paint the field device's maps from its bakes: python paint_device.py <work dir> <output dir>

Colour, roughness, metalness, normal, AO and a glow mask, all in numpy. Wear is worked out from each texel's 3D position
and normal, so it crosses UV seams. Weaves are laid out in UV: every island is at real scale with its long side along U.
All lettering is invented and descriptive, drawn with Windows' Bahnschrift and, for the pen on the lot block, Segoe Print. No brands.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import FONT, OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal, weave  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

CANVAS, BINDING, WEB, RUBBER, KEY, HOUSING, PLATE, STEEL, GLASS, GASKET, LABEL = range(11)
KEY_X = [0.919 - 1.189 * i for i in range(4)]
KEY_Y = [1.335, 0.0, -1.335]
LEGENDS = ["123", "456", "789", "*0#"]
LAMP = (3.74, -2.92)
SCREWS = [(x, y) for x in (-4.13, 4.13) for y in (-3.28, 3.28)]

pos4 = load("bake_fd_pos")
nor4 = load("bake_fd_nor")
facts4 = load("bake_fd_facts")
ao4 = load("bake_fd_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "device.json")))
pos = (pos4[..., :3] - 0.5) * 40.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4
print("coverage %.2f" % cover.mean(), flush=True)

density = np.where(np.isin(finish, (KEY, PLATE, GLASS, LABEL)), meta["density"] * meta["boost"], meta["density"]).astype(np.float32)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-6)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 3.5) * 0.22, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.4) * 2.0 + ndi.gaussian_filter(convex, 4.0) * 2.4, 0, 1)
del curve, dn, dp
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


big = field(noise(pts, 0.2, 1, 3))
mid = field(noise(pts, 0.95, 2, 4))
fine = field(noise(pts, 4.2, 3, 3))
micro = field(noise(pts, 13.0, 4, 2))
tone = field(noise(pts, 2.2, 5, 3))
print("noise done", flush=True)
crevice = np.clip((1 - ao) * 1.35, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
up = np.clip(nor[..., 2], 0, 1)
top_face = nor[..., 2] > 0.8

aluminium = srgb_to_linear((186, 186, 182))
rust_c = mix(np.broadcast_to(srgb_to_linear((58, 34, 22)), (H, W, 3)), np.broadcast_to(srgb_to_linear((108, 64, 38)), (H, W, 3)), smooth(0.35, 0.8, tone))


def solid(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.7, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)
glow = np.zeros((H, W), np.float32)


def put(mask, c, r, m, h):
    global color, rough, metal, height
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, r, rough)
    metal = np.where(mask, m, metal)
    height = np.where(mask, h, height)


# Scratches, drawn in UV so they stay sharp.
scratch_img = Image.new("L", (W, H), 0)
draw = ImageDraw.Draw(scratch_img)
rs = np.random.default_rng(7)
for _ in range(1300):
    x, y = rs.uniform(0, W), rs.uniform(0, H)
    a = rs.uniform(0, 2 * math.pi)
    n = rs.integers(8, 70)
    bend = rs.normal(0, 0.004)
    line = []
    for s in np.linspace(0, n, 6):
        line.append((x + math.cos(a) * s, y + math.sin(a) * s))
        a += bend * 6
    draw.line(line, fill=int(rs.uniform(60, 220)), width=1)
scratch = np.asarray(scratch_img, np.float32)[::-1] / 255.0
scratch = scratch * smooth(0.4, 0.62, big + (mid - 0.5) * 0.5)

# ---- Canvas ----
canvas = finish == CANVAS
woven = weave(H, W, meta["density"], meta["density"], 0.1, 21, slub=0.3)
woven = np.clip(woven, 0, 1.2)
od = srgb_to_linear((88, 90, 56))
od_dark = srgb_to_linear((60, 64, 40))
od_sun = srgb_to_linear((120, 116, 82))
c_color = mix(np.broadcast_to(od_dark, (H, W, 3)), np.broadcast_to(od, (H, W, 3)), smooth(0.25, 0.7, mid * 0.5 + big * 0.5))
c_color = mix(c_color, np.broadcast_to(od_sun, (H, W, 3)), smooth(0.45, 0.95, up * 0.65 + big * 0.5) * 0.55)
c_color = c_color * (0.84 + 0.3 * field(noise(pts, 0.6, 35, 3))[..., None])
c_color = c_color * (0.74 + 0.42 * woven[..., None])
# Long creases where the bands pull the cloth, soft dents everywhere else. Both are height, and darken a little.
band_near = np.exp(-np.maximum(np.abs(np.abs(X) - 5.2) - 0.5, 0) / 1.0)
pull = field(noise(pts * np.array((3.2, 0.42, 0.7), np.float32), 1.0, 31, 3))
crease = np.abs(pull - 0.5) * 2
crease_lines = smooth(0.26, 0.0, crease) * (0.25 + 1.0 * band_near)
dents = field(noise(pts * np.array((0.8, 1.3, 1.0), np.float32), 1.5, 32, 3))
c_height = 0.0065 * woven + 0.042 * (dents - 0.5) - 0.042 * crease_lines
c_color = c_color * (1 - crease_lines[..., None] * 0.4)
# Two rows of machine stitching round every pouch, just under the binding.
for row_z in (2.2, 2.31):
    groove = (np.abs(nor[..., 2]) < 0.6) & (np.abs(Z - row_z) < 0.045)
    row = (np.abs(nor[..., 2]) < 0.6) & (np.abs(Z - row_z) < 0.016) & (np.mod(X + Y, 0.16) < 0.105)
    c_height = c_height - groove * 0.008 + row * 0.012
    c_color = np.where(groove[..., None], c_color * 0.8, c_color)
    c_color = np.where(row[..., None], solid((146, 138, 100)), c_color)
# A sewn seam down the middle of each pouch top, and two lines of stitching beside the binding of each outer pouch.
stitch_dash = np.mod(X, 0.17) < 0.11
for y0 in (-3.65, 0.0, 3.65):
    seam = np.abs(Y - y0) < 0.018
    line = seam & stitch_dash & (Z > 2.4)
    c_height = c_height - (np.abs(Y - y0) < 0.07) * (Z > 2.4) * 0.012 + line * 0.016
    c_color = np.where(line[..., None], solid((142, 136, 100)), c_color)
    c_color = np.where(((np.abs(Y - y0) < 0.07) & (Z > 2.4) & ~line)[..., None], c_color * 0.74, c_color)
# Box-stitch patches where the grab loops are sewn down.
for sy in (-1, 1):
    for sx in (-1, 1):
        patch = (np.abs(X - sx * 1.65) < 0.3) & (np.abs(Y - sy * 4.62) < 0.42) & (Z > 2.7)
        c_height = c_height - patch * 0.008
# Stencilled lettering on the outer sides and ends, sprayed and worn.
art_side = stencil_image(["FIELD UNIT 04", "SEALED ASSEMBLY"], (1400, 300))
art_end = stencil_image(["04"], (300, 260))
# Worn in specks and thin patches, never so far that a letter goes.
worn_paint = 0.45 + 0.55 * smooth(0.28, 0.46, field(noise(pts, 3.3, 33, 3)) + big * 0.12)
lettering = np.zeros((H, W), np.float32)
for sy, flip in ((-1, 1.0), (1, -1.0)):
    # Below the stitching and above the tray.
    uu = (flip * X + 2.55) / 5.1
    vv = (Z - 0.92) / 1.1
    lettering = np.maximum(lettering, sample_image(art_side, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) * (nor[..., 1] * sy > 0.55))
for sx, flip in ((-1, -1.0), (1, 1.0)):
    uu = (flip * Y + 0.95) / 1.9
    vv = (Z - 1.05) / 1.25
    for y0 in (-3.65, 3.65):
        uu2 = (flip * (Y - y0) + 0.62) / 1.24
        lettering = np.maximum(lettering, sample_image(art_end, np.clip(uu2, -1, 2), np.clip(vv, -1, 2)) * (nor[..., 0] * sx > 0.55))
c_color = mix(c_color, solid((168, 164, 134)) * (0.78 + 0.3 * woven[..., None]), lettering * worn_paint * 0.88)
# Rubbed pale on the shoulders, and dark oil and grease in blotches.
shoulder = smooth(0.0, 0.6, 1 - np.abs(nor[..., 2] - 0.62) * 3.0) * smooth(0.46, 0.72, mid * 0.6 + fine * 0.4)
c_color = mix(c_color, solid((132, 128, 96)) * (0.8 + 0.3 * woven[..., None]), shoulder * 0.42)
oil = smooth(0.66, 0.78, field(noise(pts, 0.75, 34, 4)))
c_color = c_color * (1 - oil[..., None] * 0.42)
c_rough = 0.88 + 0.08 * fine - oil * 0.26
put(canvas, c_color, c_rough, np.zeros((H, W), np.float32), c_height)

# ---- Binding tape: ribbed along its length, and darker than the cloth ----
binding = finish == BINDING
V, U = np.mgrid[0:H, 0:W].astype(np.float32)
u_in, v_in = U / meta["density"], V / meta["density"]
ribs = 0.5 + 0.5 * np.sin(2 * np.pi * u_in / 0.075)
put(binding, solid((52, 54, 36)) * (0.82 + 0.3 * ribs[..., None]) * (0.85 + 0.3 * mid[..., None]), 0.86 + 0.08 * fine, np.zeros((H, W), np.float32), 0.004 * ribs)

# ---- Webbing: herringbone ribs across its width, along the island's long side ----
web = finish == WEB
across = np.abs(np.mod(v_in, 0.3) / 0.3 - 0.5) * 2
tw = np.mod((u_in + across * 0.09) / 0.075, 1.0)
twill = np.sqrt(np.clip(1 - (2 * tw - 1) ** 2, 0, 1))
w_color = solid((62, 64, 50)) * (0.56 + 0.72 * twill[..., None]) * (0.82 + 0.36 * mid[..., None])
w_color = mix(w_color, solid((112, 108, 86)) * (0.62 + 0.5 * twill[..., None]), smooth(0.42, 0.74, edge * 0.7 + fine * 0.35 + big * 0.2) * 0.5)
# Tan bar tacks where the band is sewn near each shoulder, and at both ends of the grab loops.
tack = (np.abs(np.abs(Y) - 5.02) < 0.09) & (np.abs(np.abs(X) - 5.2) < 0.42) & (Z > 2.6)
tack = tack | ((np.abs(np.abs(X) - 1.48) < 0.08) & (np.abs(np.abs(Y) - 4.62) < 0.3) & (Z > 2.6))
zig = np.mod(X * 11.0 + Y * 11.0, 1.0) < 0.55
w_color = np.where((tack & zig)[..., None], solid((146, 128, 90)), w_color)
put(web, w_color, 0.82 + 0.1 * fine, np.zeros((H, W), np.float32), 0.008 * twill + (tack & zig) * 0.008)

# ---- Moulded rubber ----
rubber = finish == RUBBER
pebble = field(noise(pts, 18.0, 41, 2))
r_scuff = smooth(0.46, 0.72, edge * 0.65 + (fine - 0.5) * 0.9 + (mid - 0.5) * 0.5)
r_color = solid((31, 31, 30)) * (0.82 + 0.34 * mid[..., None])
r_color = mix(r_color, solid((96, 94, 88)), r_scuff * 0.38)
r_rough = 0.66 + 0.14 * fine + r_scuff * 0.14
put(rubber, r_color, r_rough, np.zeros((H, W), np.float32), 0.0042 * pebble - r_scuff * 0.004)

# ---- Gaskets and pads: softer, matter rubber, with ribs on the buckle's thumb pad ----
gasket = finish == GASKET
pad_ribs = (0.5 + 0.5 * np.sin(2 * np.pi * Y / 0.12)) * (Z < 3.6) * up
put(gasket, solid((24, 24, 24)) * (0.86 + 0.28 * mid[..., None]), 0.76 + 0.12 * fine, np.zeros((H, W), np.float32), 0.0022 * micro + 0.014 * pad_ribs)

# ---- Housing: cast aluminium under a dark coat ----
housing = finish == HOUSING
cast = 0.6 * field(noise(pts, 7.0, 42, 3)) + 0.4 * micro
chip = edge * smooth(0.3, 0.66, mid * 0.65 + fine * 0.35) * 0.82 + (mid - 0.5) * 0.42 + (big - 0.5) * 0.28 + (fine - 0.5) * 0.6 + (micro - 0.5) * 0.25
bare = smooth(0.74, 0.76, chip)
coat = solid((47, 49, 50)) * (0.8 + 0.36 * mid[..., None]) * (0.94 + 0.12 * part[..., None])
h_color = mix(coat, solid((150, 150, 146)), scratch[..., None] * 0.38)
h_color = mix(h_color, np.broadcast_to(aluminium, (H, W, 3)) * (0.72 + 0.34 * fine[..., None]), bare)
h_rough = 0.56 + 0.16 * mid + 0.08 * fine
h_rough = h_rough * (1 - bare) + (0.34 + 0.22 * fine) * bare
h_metal = np.maximum(bare, scratch * 0.32)
put(housing, h_color, h_rough, h_metal, 0.0085 * (cast - 0.5) + (1 - bare) * 0.008 - scratch * 0.004)

# ---- Control plate: the same coat, finer, with its printing ----
SCALE = 220
art = Image.new("L", (int(7.25 * SCALE), int(8.9 * SCALE)), 0)
d = ImageDraw.Draw(art)


def font(size, style="SemiBold"):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name(style)
    except Exception:
        pass
    return f


def page(x, y):
    """Plate coordinates to pixels of the printing."""
    return ((3.625 - y) * SCALE, (4.45 - x) * SCALE)


def text(x, y, value, size, style="SemiBold", fill=255, spacing=0):
    f = font(int(size * SCALE), style)
    if spacing:
        total = sum(d.textlength(c, font=f) + spacing * SCALE for c in value) - spacing * SCALE
        px, py = page(x, y)
        px -= total / 2
        for c in value:
            d.text((px, py), c, fill, font=f, anchor="lm")
            px += d.textlength(c, font=f) + spacing * SCALE
    else:
        px, py = page(x, y)
        d.text((px, py), value, fill, font=f, anchor="mm")


def rect(x0, y0, x1, y1, width=0.012, fill=None, ink=255):
    a, b = page(x1, y0)
    c, e = page(x0, y1)
    box_ = (min(a, c), min(b, e), max(a, c), max(b, e))
    d.rectangle(box_, fill=fill, outline=ink, width=max(1, int(width * SCALE)))


# The maker's mark: a made-up hexagon and bar, and plain words rather than a name.
hx, hy = page(3.84, 2.05)
r = 0.2 * SCALE
d.polygon([(hx + r * math.cos(math.radians(a)), hy + r * math.sin(math.radians(a))) for a in range(30, 390, 60)], outline=255, width=int(0.028 * SCALE))
d.rectangle((hx - r * 0.5, hy - r * 0.13, hx + r * 0.5, hy + r * 0.13), fill=255)
text(3.86, -0.15, "FIELD UNIT 04", 0.3, "SemiBold", spacing=0.03)
text(3.45, -0.15, "SEALED ASSEMBLY  -  NO USER PARTS", 0.135, "Regular", fill=200, spacing=0.012)
rect(1.74, -2.36, 3.24, 2.36, 0.012)
text(LAMP[0] - 0.33, LAMP[1], "STATUS", 0.1, "Regular", fill=200)
# Rules around the keypad and small ticks either side of it.
rect(-3.42, -2.14, 1.66, 2.14, 0.012)
for k, x in enumerate(KEY_X):
    for sy in (-1, 1):
        a, b = page(x, sy * 2.86)
        d.line((a - 0.07 * SCALE, b, a + 0.07 * SCALE, b), fill=170, width=2)
text(-3.86, 0.0, "HANDLE WITH CARE", 0.15, "Regular", fill=210, spacing=0.03)
a, b = page(-3.86, 2.05)
c, e = page(-3.86, 1.68)
d.rectangle((a, b - 0.022 * SCALE, c, e + 0.022 * SCALE), fill=210)
a, b = page(-3.86, -1.68)
c, e = page(-3.86, -2.05)
d.rectangle((a, b - 0.022 * SCALE, c, e + 0.022 * SCALE), fill=210)
print_art = np.asarray(art, np.float32) / 255.0

# The white lot block, filled in with a paint pen. Black on white, so it's its own layer.
block = Image.new("L", (int(0.86 * 300), int(1.5 * 300)), 0)
bd = ImageDraw.Draw(block)
pen = ImageFont.truetype(r"C:\Windows\Fonts\segoepr.ttf", 62) if os.path.exists(r"C:\Windows\Fonts\segoepr.ttf") else font(62)
for k, line in enumerate(("LOT", "7731", "D")):
    bd.text((block.width / 2, 75 + k * 145), line, 255, font=pen, anchor="mm")
block_ink = np.asarray(block, np.float32) / 255.0

# Key legends.
legend_img = Image.new("L", (int(7.25 * SCALE), int(8.9 * SCALE)), 0)
ld = ImageDraw.Draw(legend_img)
kf = font(int(0.46 * SCALE), "SemiBold")
for row, x in enumerate(KEY_X):
    for col, y in enumerate(KEY_Y):
        ld.text(page(x, y), LEGENDS[row][col], 255, font=kf, anchor="mm")
legend = np.asarray(legend_img, np.float32) / 255.0

plate = finish == PLATE
face_uu, face_vv = (3.625 - Y) / 7.25, (X + 4.45) / 8.9
printing = sample_image(print_art, np.clip(face_uu, -1, 2), np.clip(face_vv, -1, 2)) * (plate & (Z > 3.91) & top_face)
ink_wear = smooth(0.15, 0.34, field(noise(pts, 5.0, 43, 3)) + big * 0.1 + 0.05)
printing = printing * ink_wear
p_chip = edge * smooth(0.3, 0.66, mid * 0.65 + fine * 0.35) * 1.4 + (mid - 0.5) * 0.3 + (big - 0.5) * 0.2 + (fine - 0.5) * 0.5 + (micro - 0.5) * 0.25
p_bare = smooth(0.76, 0.78, p_chip)
p_color = solid((43, 45, 46)) * (0.84 + 0.3 * mid[..., None])
# Fingers have polished the coat round the keypad and thumbs the lower edge.
polish = smooth(1.0, 0.0, np.hypot((X + 1.0) / 3.9, Y / 3.0)) * smooth(0.3, 0.6, fine * 0.5 + mid * 0.5)
p_color = p_color * (1 + polish[..., None] * 0.14)
# Patches of fine scuffing, from being carried and set down.
scuff = smooth(0.56, 0.8, field(noise(pts, 8.0, 51, 3))) * smooth(0.35, 0.7, mid * 0.6 + big * 0.4)
p_color = mix(p_color, solid((92, 92, 90)), scuff * 0.42)
p_color = mix(p_color, solid((208, 206, 192)), printing * 0.95)
# The well floor is the keypad's rubber mat.
floor = plate & (Z < 3.86) & (np.abs(Y) < 2.1) & (X < 1.6) & (X > -3.35)
p_color = np.where(floor[..., None], solid((22, 22, 22)) * (0.85 + 0.3 * mid[..., None]), p_color)
p_color = mix(p_color, solid((140, 140, 136)), scratch[..., None] * 0.26)
p_color = mix(p_color, np.broadcast_to(aluminium, (H, W, 3)) * (0.74 + 0.32 * fine[..., None]), p_bare)
p_rough = 0.46 + 0.22 * mid + 0.06 * fine - polish * 0.12 + printing * 0.1 + scuff * 0.16
p_rough = np.where(floor, 0.78 + 0.1 * fine, p_rough)
p_rough = p_rough * (1 - p_bare) + (0.32 + 0.2 * fine) * p_bare
p_metal = np.maximum(p_bare, scratch * 0.3)
p_height = 0.0026 * (micro - 0.5) + 0.0016 * (fine - 0.5) + (1 - p_bare) * 0.006 - scratch * 0.003 + printing * 0.0012
# The sounder's row of little drilled holes, right of the keypad.
for col in range(3):
    for row_ in range(6):
        hole = np.hypot(Y - (-2.98 - col * 0.17), X - (-1.25 + row_ * 0.17)) < 0.05
        rim = np.hypot(Y - (-2.98 - col * 0.17), X - (-1.25 + row_ * 0.17)) < 0.066
        where = plate & top_face & (Z > 3.91)
        p_color = np.where((hole & where)[..., None], solid((6, 6, 6)), p_color)
        p_height = p_height - (hole & where) * 0.03 + ((rim & ~hole) & where) * 0.004
# The lot block.
lot = plate & top_face & (Z > 3.91) & (np.abs(Y - 3.17) < 0.43) & (np.abs(X + 0.8) < 0.75)
lot_ink = sample_image(block_ink, np.clip((3.6 - Y) / 0.86, -1, 2), np.clip((X + 1.55) / 1.5, -1, 2))
lot_c = mix(solid((170, 168, 152)) * (0.82 + 0.22 * mid[..., None]), solid((16, 16, 20)), lot_ink)
lot_edge = smooth(0.2, 0.3, field(noise(pts, 6.0, 44, 2)) * 0.4 + np.minimum(0.43 - np.abs(Y - 3.17), 0.75 - np.abs(X + 0.8)) * 9.0)
p_color = np.where(lot[..., None], mix(p_color, lot_c, lot_edge), p_color)
p_rough = np.where(lot, 0.62, p_rough)
put(plate, p_color, p_rough, p_metal, p_height)

# ---- Keys: moulded silicone, the printing worn off the ones used most, tops polished by thumbs ----
keys = finish == KEY
key_top = keys & (Z > 4.1)
k_legend = sample_image(legend, np.clip(face_uu, -1, 2), np.clip(face_vv, -1, 2)) * key_top
worn_more = np.exp(-(((X - KEY_X[1]) ** 2 + (Y - KEY_Y[1]) ** 2) / 0.5)) + np.exp(-(((X - KEY_X[3]) ** 2 + (Y - KEY_Y[1]) ** 2) / 0.5)) + 0.5 * np.exp(-(((X - KEY_X[0]) ** 2 + (Y - KEY_Y[0]) ** 2) / 0.5))
k_keep = smooth(0.1, 0.34, field(noise(pts, 9.0, 45, 2)) + 0.32 - worn_more * 0.2)
k_legend = k_legend * k_keep
k_shine = np.zeros((H, W), np.float32)
for x in KEY_X:
    for y in KEY_Y:
        k_shine = np.maximum(k_shine, np.exp(-(((X - x) ** 2 + (Y - y) ** 2) / 0.09)))
k_color = solid((35, 35, 36)) * (0.86 + 0.28 * mid[..., None]) * (0.94 + 0.12 * part[..., None])
k_color = k_color * (1 + k_shine[..., None] * 0.2)
k_color = mix(k_color, solid((214, 212, 200)), k_legend * 0.95)
put(keys, k_color, 0.62 + 0.1 * fine - k_shine * 0.24 + k_legend * 0.1, np.zeros((H, W), np.float32), 0.0024 * (micro - 0.5) * (1 - k_shine * 0.7) + k_legend * 0.0025)

# ---- Fittings: black oxide, rubbed back on edges ----
steel = finish == STEEL
s_wear = smooth(0.42, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
s_color = solid((38, 38, 40)) * (0.75 + 0.5 * mid[..., None])
s_color = mix(s_color, np.broadcast_to(aluminium, (H, W, 3)) * 0.86, s_wear * 0.9)
s_rust = smooth(0.76, 0.88, field(noise(pts, 3.6, 46, 3)) + crevice * 0.1)
s_color = mix(s_color, rust_c, s_rust * 0.6)
put(steel, s_color, 0.36 + 0.2 * fine - 0.08 * s_wear + 0.35 * s_rust, (1 - s_rust) * 0.92, 0.0016 * (micro - 0.5) + s_rust * 0.005)

# ---- Data plate: bright aluminium, the words etched and filled black ----
label = finish == LABEL
words = stencil_image(["FIELD UNIT 04", "ASSEMBLY 7731-D    SEALED", "NO USER PARTS INSIDE"], (1320, 300), bridge=False)
# This face looks towards -X, so a reader's right is -Y. Reading along +Y mirrored it, which only showed in s&box.
stamp = sample_image(words, np.clip((1.8 - Y) / 3.6, -1, 2), np.clip((Z - 3.1) / 0.4, -1, 2)) * (nor[..., 0] < -0.7)
l_color = solid((168, 168, 162)) * (0.84 + 0.26 * mid[..., None])
l_color = mix(l_color, solid((14, 14, 15)), stamp * 0.92)
l_color = mix(l_color, l_color * 0.72, smooth(0.5, 1.0, crevice * 0.6 + (mid - 0.5)))
put(label, l_color, 0.4 + 0.2 * fine + stamp * 0.3, 1 - stamp * 0.88, stamp * -0.006 + 0.0012 * (micro - 0.5))

# ---- The window: dark glass over an amber dot-matrix line, and the status lamp ----
pane = finish == GLASS
FONT5 = {
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
}
PITCH = 0.082
COLS, ROWS = 52, 11
lit_table = np.zeros((ROWS, COLS), np.float32)
start = (COLS - (7 * 6 - 1)) // 2
for n, ch in enumerate("STANDBY"):
    for row, bits in enumerate(FONT5[ch]):
        for col, bit in enumerate(bits):
            if bit == "1":
                lit_table[ROWS - 2 - row, start + n * 6 + col] = 1.0
col_f = (-Y + COLS * PITCH / 2) / PITCH
row_f = (X - 2.49 + ROWS * PITCH / 2) / PITCH
in_matrix = pane & (col_f >= 0) & (col_f < COLS) & (row_f >= 0) & (row_f < ROWS) & top_face & (Z < 3.9)
ci = np.clip(col_f.astype(np.int32), 0, COLS - 1)
ri = np.clip(row_f.astype(np.int32), 0, ROWS - 1)
dot = smooth(0.44, 0.28, np.hypot(col_f - ci - 0.5, row_f - ri - 0.5))
lit = lit_table[ri, ci] * dot * in_matrix
ghost = dot * in_matrix
amber = solid((255, 150, 30))
g_color = solid((8, 9, 8)) * (0.9 + 0.2 * mid[..., None])
g_color = g_color + ghost[..., None] * solid((26, 18, 8))
g_color = mix(g_color, amber, lit * 0.96)
smudge = smooth(0.42, 0.7, field(noise(pts, 1.6, 47, 4)))
# A matt anti-glare film, so the line stays readable at a low angle instead of mirroring the sky.
g_rough = 0.3 + 0.1 * smudge + scratch * 0.15 + field(noise(pts, 30.0, 48, 1)) * 0.03
lamp_d = np.hypot(X - LAMP[0], Y - LAMP[1])
is_lamp = pane & (lamp_d < 0.13)
g_color = np.where(is_lamp[..., None], solid((255, 120, 24)) * (0.65 + 0.35 * smooth(0.11, 0.02, lamp_d)[..., None]), g_color)
g_rough = np.where(is_lamp, 0.16, g_rough)
glow = np.where(pane, np.maximum(lit * 0.9, is_lamp * smooth(0.12, 0.03, lamp_d) * 0.85), glow)
put(pane, g_color, g_rough, np.zeros((H, W), np.float32), 0.0004 * (fine - 0.5))

# ---- A tamper seal across the joint on the operator's side, cut and printed, not a marking of anyone's ----
seal_box = (np.abs(Y + 2.62) < 0.42) & (np.isin(finish, (PLATE, HOUSING, GASKET)))
seal_top = seal_box & top_face & (X < -3.96) & (X > -4.5)
seal_side = seal_box & (nor[..., 0] < -0.55) & (Z > 3.34) & (Z < 3.93)
seal_round = seal_box & (X < -4.3) & (Z > 3.85)
seal_mask = (seal_top | seal_side | seal_round).astype(np.float32)
tear = smooth(0.2, 0.3, field(noise(pts, 5.5, 49, 3)) + 0.05 + np.minimum(0.42 - np.abs(Y + 2.62), 0.2) * 1.2)
seal = seal_mask * tear
seal_words = stencil_image(["SEALED", "SEALED"], (340, 380), bridge=False)
seal_ink = sample_image(seal_words, np.clip((-2.2 - Y) / 0.84, -1, 2), np.clip((X + 4.48) / 0.52, -1, 2)) * seal_top
color = mix(color, mix(solid((138, 44, 30)) * (0.8 + 0.3 * mid[..., None]), solid((204, 196, 178)), seal_ink), seal)
rough = rough * (1 - seal) + 0.42 * seal
metal = metal * (1 - seal)
height = height + seal * 0.006

# ---- Dust on what faces up, grime in the corners ----
settled = smooth(0.46, 0.95, up * 0.62 + (big - 0.5) * 0.5 + crevice * 0.3 + (fine - 0.5) * 0.22)
low = np.clip(1 - Z / 2.2, 0, 1) ** 1.6
splash = low * smooth(0.46, 0.66, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.8, 50, 4)) + low * 0.16)
grime = smooth(0.2, 0.9, crevice) * smooth(0.25, 0.7, mid)
dirt = np.clip(settled * 0.3 + splash * 0.42 + grime * 0.4, 0, 0.88)
# Dust doesn't sit on glass, and on black rubber a little goes a long way.
dirt = dirt * np.where(pane, 0.25, np.where(rubber, 0.5, 1.0))
dirt_c = solid((92, 85, 72)) * (0.75 + 0.5 * fine[..., None])
color = mix(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.92 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.003 * (fine - 0.35)
glow = glow * (1 - dirt)

color = color * (0.74 + 0.26 * ao[..., None])
# The faces no one sees share the atlas's corner. If they ever show, they're plain dark rubber.
color[:6, :6] = srgb_to_linear((26, 26, 26))
rough[:6, :6] = 0.8
metal[:6, :6] = 0.0
height[:6, :6] = 0.0
glow[:6, :6] = 0.0
# Fill the gutters from the covered texels, with no erosion: most islands here are thin, and eroding one away would hand it
# the colours of whichever island is nearest (that's how bevels ended up glowing like the window).
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal, glow_f = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.04, 1), np.clip(metal, 0, 1), normal, glow)
save_rgb(os.path.join(OUT, "fd_device_color.png"), color)
save_gray(os.path.join(OUT, "fd_device_rough.png"), rough)
save_gray(os.path.join(OUT, "fd_device_metal.png"), metal)
save_gray(os.path.join(OUT, "fd_device_ao.png"), np.clip(ao * 1.03, 0, 1))
save_gray(os.path.join(OUT, "fd_device_glow.png"), np.clip(glow_f, 0, 1))
save_normal(os.path.join(OUT, "fd_device_normal.png"), normal)
print("device painted", flush=True)
