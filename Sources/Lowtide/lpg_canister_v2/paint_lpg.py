"""Paint the LPG cylinder's maps from its bakes: python paint_lpg.py <work dir> <materials dir> <intact|ruptured|cap>

A fuel bottle that has spent years on a dock forklift: pale grey enamel with a red shoulder band, stencilled and placarded,
chipped where it gets dragged in and out of its saddles, rust weeping from under the straps and the welds. No impact
damage is painted on the intact bottle, because players shoot it and the game shows that with its own leak and fire.
Burst, the same paint is scorched back from the tear; inside it's all soot. Lettering is generic: no brand, real or game.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import FONT, OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

VARIANT = sys.argv[3]
MAT = {"intact": "lpg_intact", "ruptured": "lpg_ruptured", "cap": "lpg_cap"}[VARIANT]
PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, SHELL, GUARD, RED, SOOT, DIAL, TORN = range(15)

pos4 = load(f"bake_{VARIANT}_pos")
nor4 = load(f"bake_{VARIANT}_nor")
facts4 = load(f"bake_{VARIANT}_facts")
ao4 = load(f"bake_{VARIANT}_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
density = json.load(open(os.path.join(WORK, f"{VARIANT}.json")))["density"]
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
# The shell's own curve (1/6.3) and the hoop's aren't edges: only tighter than a 3/8 inch radius is.
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
A = np.arctan2(Z, X)
RAD = np.hypot(X, Z)

steel = srgb_to_linear((160, 160, 156))
rust_c = mix(flat((58, 32, 20)), flat((122, 70, 38)), smooth(0.35, 0.8, field(noise(pts, 3.1, 8, 3))))

color = np.zeros((H, W, 3), np.float32)
rough = np.zeros((H, W), np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)


def around(centre_deg):
    """Inches round the shell from an angle, on the 6.3 radius."""
    return np.angle(np.exp(1j * (A - math.radians(centre_deg)))) * 6.3


def stencil_on_rear(art, y_mid, a_deg, long_in, tall_in):
    """Lettering read from behind the truck: left to right is -Y, and up is falling angle (a above 90 degrees)."""
    uu = 0.5 + (y_mid - Y) / long_in
    vv = 0.5 - around(a_deg) / tall_in
    return sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))


def stencil_on_front(art, y_mid, a_deg, long_in, tall_in):
    """Lettering read from the truck's side: left to right is +Y, and up is rising angle (a below 90 degrees)."""
    uu = 0.5 + (Y - y_mid) / long_in
    vv = 0.5 + around(a_deg) / tall_in
    return sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))


def placard(size=512):
    """A class 2 flammable-gas diamond: red ground, a flame and the class number, no maker's anything. Returns (diamond, marks)."""
    ground = Image.new("L", (size, size), 0)
    ImageDraw.Draw(ground).polygon([(size / 2, 2), (size - 2, size / 2), (size / 2, size - 2), (2, size / 2)], fill=255)
    marks = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(marks)
    inset = size * 0.05
    d.polygon([(size / 2, inset), (size - inset, size / 2), (size / 2, size - inset), (inset, size / 2)], outline=255, width=max(4, size // 90))
    s = size / 512
    tongues = [(186, 292), (172, 252), (184, 214), (206, 186), (214, 218), (228, 196), (224, 160), (240, 126), (264, 88), (268, 128), (286, 150), (296, 178), (308, 160), (326, 192), (336, 234), (326, 272), (322, 292)]
    p = np.array(tongues, float)
    flame = []
    for i in range(len(p) - 1):
        a, b, c, e = p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, len(p) - 1)]
        for t in np.linspace(0, 1, 7, endpoint=False):
            flame.append(tuple(0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - e) * t * t + (3 * b - a - 3 * c + e) * t**3) * s))
    flame.append(tuple(p[-1] * s))
    d.polygon(flame, fill=255)
    d.rectangle((186 * s, 304 * s, 322 * s, 316 * s), fill=255)
    font = ImageFont.truetype(FONT, int(92 * s))
    bb = d.textbbox((0, 0), "2", font=font)
    d.text((256 * s - (bb[2] - bb[0]) / 2 - bb[0], 346 * s - bb[1]), "2", 255, font=font)
    return np.asarray(ground, np.float32) / 255.0, np.asarray(marks, np.float32) / 255.0


# ---- The tear, in 3D, for the burst model. ----
scorch = np.zeros((H, W), np.float32)
blackened = np.zeros((H, W), np.float32)
to_lip = np.full((H, W), 99.0, np.float32)
if VARIANT == "ruptured":
    lips = np.load(os.path.join(WORK, "lips.npy"))
    dist, _ = cKDTree(lips).query(pts, k=1, workers=1)
    to_lip = field(dist.astype(np.float32))
if VARIANT == "cap":
    to_lip = np.clip((6.3 - RAD) * 1.7, 0, 9).astype(np.float32)
heat = np.zeros((H, W), np.float32)
if VARIANT != "intact":
    wander = (field(noise(pts, 0.45, 40, 4)) - 0.5) * 5.0 + (fine - 0.5) * 1.4
    scorch = 1 - smooth(0.8, 5.0, to_lip + wander)
    blackened = 1 - smooth(3.0, 10.0, to_lip + wander * 1.4)
    heat = 1 - smooth(5.0, 12.5, to_lip + wander * 1.4)
if VARIANT == "cap":
    # It flew out through the fireball: sooted in patches right across, not just near its edge.
    blackened = np.maximum(blackened, 0.6 * smooth(0.36, 0.7, mid * 0.6 + big * 0.4))

# ---- Enamel over steel: the shell, its guard and its foot ring. ----
shell = finish == SHELL
weld = finish == WELD
chip = edge * smooth(0.3, 0.68, mid * 0.65 + fine * 0.35) * 1.12 + (mid - 0.5) * 0.6 + (big - 0.5) * 0.4 + (fine - 0.5) * 0.85 + (micro - 0.5) * 0.3
# Dragged in and out of the saddles for years: the paint goes in long scuffs along the bottle near them, and lower down.
drag_noise = field(noise(pts * np.array((3.0, 0.16, 3.0), np.float32), 0.8, 21, 4))
saddle_near = np.exp(-(np.minimum(np.abs(Y - 10), np.abs(Y + 10)) / 4.5) ** 2)
drag = smooth(0.62, 0.7, drag_noise + saddle_near * 0.1 + np.clip(-Z / 6.3, 0, 1) * 0.1) * (RAD > 5.6) * (RAD < 7)
chip = chip + drag * 0.3
# A cylinder that stands on a concrete floor between jobs is worn all round its foot ring and the guard's top.
bare = smooth(0.72, 0.74, chip)
under = smooth(0.67, 0.69, chip)

grey = flat((168, 170, 164)) * (0.88 + 0.16 * mid[..., None])
grey = grey * (1 - smooth(0.35, 0.85, big)[..., None] * np.array((0.04, 0.05, 0.09), np.float32))
band = (np.abs(Y) > 11.0) & (np.abs(Y) < 13.0) & (RAD > 5.5) & (RAD < 7.0)
band_edge = smooth(11.0, 11.03, np.abs(Y) + (micro - 0.5) * 0.03) * smooth(13.0, 12.97, np.abs(Y) + (micro - 0.5) * 0.03)
red = flat((136, 30, 24)) * (0.82 + 0.26 * mid[..., None])
s_color = mix(grey, red, band_edge * band)
# Rain has run down it for years, faintly, round the curve.
upright = 1 - np.abs(nor[..., 2])
s_color = s_color * (1 + upright[..., None] * (streak[..., None] - 0.5) * 0.3)

# Lettering, sprayed through a stencil and worn with the coat. Where the bottle has burst it burns off with the paint.
letter = np.zeros((H, W), np.float32)
placard_ground = np.zeros((H, W), np.float32)
placard_marks = np.zeros((H, W), np.float32)
plate_stamp = None
if VARIANT != "cap":
    on_body = shell & (RAD > 5.8) & (RAD < 7.2) & (np.abs(Y) < 9.4)
    letter = np.maximum(letter, stencil_on_rear(stencil_image(["LPG"], (1100, 620)), 4.55, 128, 8.1, 4.6) * on_body)
    letter = np.maximum(letter, stencil_on_rear(stencil_image(["FLAMMABLE GAS", "NO SMOKING  NO NAKED FLAME"], (1000, 180), bridge=False), 4.55, 158, 8.1, 1.45) * on_body)
    letter = np.maximum(letter, stencil_on_front(stencil_image(["LPG"], (900, 620)), 2.0, 48, 5.4, 3.7) * on_body)
    letter = np.maximum(letter, stencil_on_front(stencil_image(["FORKLIFT FUEL", "VALVE END >"], (1000, 260), bridge=False), 2.0, 22, 5.4, 1.45) * on_body)
    worn = smooth(0.14, 0.34, field(noise(pts, 3.3, 10, 3)) + (big - 0.5) * 0.15)
    letter = letter * worn
    ground, marks = placard()
    placard_ground = stencil_on_rear(ground, -2.4, 128, 4.4, 4.4) * on_body
    placard_marks = stencil_on_rear(marks, -2.4, 128, 4.4, 4.4) * on_body
    placard_ground = placard_ground * smooth(0.1, 0.26, field(noise(pts, 2.6, 11, 3)) + 0.05)
s_color = mix(s_color, flat((16, 16, 16)), letter * 0.94)
s_color = mix(s_color, flat((176, 32, 24)) * (0.86 + 0.2 * mid[..., None]), placard_ground)
s_color = mix(s_color, flat((232, 228, 214)), placard_marks * placard_ground * 0.95)
s_rough = 0.42 + 0.16 * mid + 0.08 * fine + 0.1 * letter
s_rough = s_rough + placard_ground * -0.06
s_height = 0.0045 * (micro - 0.5) + 0.002 * (fine - 0.5) + letter * 0.0018 + placard_ground * 0.0035

# The long seam along the underside, ground and painted over, and a stamped-in ripple each side of the head welds.
seam = np.exp(-(around(-118) / 0.09) ** 2) * (np.abs(Y) < 13.5) * shell
s_height = s_height + seam * 0.03

s_color = mix(s_color, flat((96, 96, 86)), under)
s_color = mix(s_color, np.broadcast_to(steel, (H, W, 3)) * (0.66 + 0.42 * fine[..., None]), bare)
s_rust = bare * smooth(0.44, 0.7, field(noise(pts, 1.7, 12, 3)) + crevice * 0.4)
s_color = mix(s_color, rust_c, s_rust)
# Rust weeps from under the straps, from the welds and from the guard's feet, and only ever downhill.
strap_side = np.exp(-(np.maximum(np.minimum(np.abs(Y - 10), np.abs(Y + 10)) - 0.55, 0) / 0.5) ** 2)
head_seam = np.exp(-(np.abs(np.abs(Y) - 13.5) / 0.35) ** 2)
guard_feet = np.exp(-((np.abs(RAD - 4.6) / 0.7) ** 2)) * (Y > 15.8) * (Y < 17) * (np.abs(np.angle(np.exp(1j * (A * 4 - math.pi)))) < 1.0)
source = np.clip(strap_side * 0.9 + head_seam * 0.55 + guard_feet * 0.6 + crevice * 0.5, 0, 1.2)
s_runs = smooth(0.5, 0.74, streak + source * 0.34) * smooth(0.22, 0.56, mid + source * 0.42)
s_color = mix(s_color, s_color * rust_c * 3.1, s_runs * 0.5)
s_rough = s_rough * (1 - bare) + 0.42 * bare
s_rough = s_rough * (1 - s_rust) + 0.86 * s_rust
s_rough = s_rough + s_runs * 0.12
s_metal = bare * (1 - s_rust)
s_height = s_height + (1 - under) * 0.009 + (1 - bare) * 0.008 + s_rust * 0.006 * (fine - 0.3)

color = np.where(shell[..., None], s_color, color)
rough = np.where(shell, s_rough, rough)
metal = np.where(shell, s_metal, metal)
height = np.where(shell, s_height, height)

# Welds: laid before the coat, so they're the same paint over a lumpy bead, and they hold the grime and start the rust.
w_detail = field(noise(pts, 4.2, 13, 3))
near_red = (np.abs(Y) > 11.0) & (np.abs(Y) < 13.7)
w_paint = np.where(near_red[..., None], red, grey) * 0.74
w_rust = smooth(0.46, 0.68, field(noise(pts, 2.4, 14, 3)) + crevice * 0.3)
w_color = mix(w_paint, rust_c, w_rust * 0.7)
color = np.where(weld[..., None], w_color, color)
rough = np.where(weld, 0.6 + 0.2 * mid + 0.15 * w_rust, rough)
metal = np.where(weld, 0.0, metal)
height = np.where(weld, 0.05 * (w_detail - 0.5) + 0.02 * (micro - 0.5), height)

# Saddles and straps: black enamel that nobody has ever repainted.
guard_f = finish == GUARD
g_chip = edge * smooth(0.3, 0.66, mid * 0.65 + fine * 0.35) * 1.2 + (mid - 0.5) * 0.62 + (big - 0.5) * 0.36 + (fine - 0.5) * 0.85
g_bare = smooth(0.7, 0.72, g_chip)
g_color = flat((34, 36, 36)) * (0.76 + 0.5 * mid[..., None]) * (0.9 + 0.2 * part[..., None])
g_color = mix(g_color, np.broadcast_to(steel, (H, W, 3)) * (0.56 + 0.34 * fine[..., None]), g_bare)
g_rust = smooth(0.42, 0.66, field(noise(pts, 1.4, 15, 3)) + crevice * 0.45) * np.maximum(g_bare, smooth(0.62, 0.8, streak + crevice * 0.3) * 0.75)
g_color = mix(g_color, rust_c, g_rust)
color = np.where(guard_f[..., None], g_color, color)
rough = np.where(guard_f, (0.46 + 0.2 * mid + 0.1 * fine) * (1 - g_rust) + 0.86 * g_rust, rough)
metal = np.where(guard_f, g_bare * (1 - g_rust), metal)
height = np.where(guard_f, 0.0045 * (micro - 0.5) + 0.002 * (fine - 0.5) + (1 - g_bare) * 0.01 + g_rust * 0.007 * (fine - 0.3), height)

# Plated fasteners.
zinc = finish == ZINC
z_color = flat((186, 188, 186)) * (0.5 + 0.3 * mid[..., None])
z_rust = smooth(0.48, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.5)
z_color = mix(z_color, rust_c, z_rust * 0.55)
z_color = mix(z_color, np.broadcast_to(steel, (H, W, 3)), smooth(0.5, 0.8, edge) * 0.5)
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, 0.3 + 0.2 * fine + 0.4 * z_rust, rough)
metal = np.where(zinc, 1 - z_rust * 0.75, metal)
height = np.where(zinc, 0.0012 * (micro - 0.5), height)

# The crimped ferrule and the gauge's bezel: dull galvanising.
galv = finish == GALV
gv_color = flat((156, 158, 154)) * (0.62 + 0.3 * fine[..., None] + 0.28 * (big[..., None] - 0.5))
gv_white = smooth(0.58, 0.78, streak + crevice * 0.22)
gv_color = mix(gv_color, flat((180, 178, 168)) * 0.8, gv_white * 0.6)
color = np.where(galv[..., None], gv_color * (1 - smooth(0.1, 0.8, crevice)[..., None] * 0.45), color)
rough = np.where(galv, 0.36 + 0.24 * fine + gv_white * 0.28, rough)
metal = np.where(galv, 1 - gv_white * 0.65, metal)
height = np.where(galv, 0.0012 * (micro - 0.5), height)

# Brass valve work: tarnished brown in the hollows, bright where hands and spanners touch it, a little verdigris low down.
brass = finish == BRASS
b_tarnish = smooth(0.32, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.7 - edge * 0.45)
b_color = mix(flat((214, 170, 92)), flat((92, 66, 34)), b_tarnish)
b_green = smooth(0.66, 0.84, field(noise(pts, 2.1, 16, 3)) + crevice * 0.26)
b_color = mix(b_color, flat((86, 112, 86)), b_green * 0.5)
color = np.where(brass[..., None], b_color, color)
rough = np.where(brass, 0.24 + 0.34 * b_tarnish + 0.1 * fine + 0.2 * b_green, rough)
metal = np.where(brass, 1 - b_green * 0.7, metal)
height = np.where(brass, 0.0012 * (micro - 0.5), height)

# The red handwheel, cast alloy under thick paint.
wheel = finish == RED
w_chip = smooth(0.5, 0.56, edge * 0.5 + (fine - 0.5) * 0.9 + (mid - 0.5) * 0.5 + 0.34)
wh_color = mix(flat((168, 30, 22)) * (0.8 + 0.3 * mid[..., None]), flat((176, 176, 170)), w_chip)
color = np.where(wheel[..., None], wh_color, color)
rough = np.where(wheel, 0.36 + 0.14 * fine + w_chip * 0.1, rough)
metal = np.where(wheel, w_chip, metal)
height = np.where(wheel, 0.003 * (micro - 0.5) + (1 - w_chip) * 0.006, height)

# Rubber: the hose, the liners and the rain cap, with the hose's ribbed cover.
rubber = finish == RUBBER
color = np.where(rubber[..., None], flat((30, 30, 30)) * (0.72 + 0.5 * fine[..., None]), color)
rough = np.where(rubber, 0.68 + 0.16 * fine, rough)
metal = np.where(rubber, 0.0, metal)
height = np.where(rubber, 0.0035 * (fine - 0.5) + 0.0016 * (micro - 0.5), height)

# The contents gauge: white face, a printed arc, black needle at a third full. Seen from +Y, so right is -X.
dial_f = finish == DIAL
if dial_f.any():
    S = 512
    img = Image.new("L", (S, S), 235)
    d = ImageDraw.Draw(img)
    c = S / 2
    for k in range(11):
        t = math.radians(210 - 240 * k / 10)
        r0, r1 = (0.62 if k % 5 else 0.56) * S / 2, 0.8 * S / 2
        d.line((c + r0 * math.cos(t), c - r0 * math.sin(t), c + r1 * math.cos(t), c - r1 * math.sin(t)), fill=20, width=8 if k % 5 == 0 else 5)
    font = ImageFont.truetype(FONT, 58)
    for text, x, y in (("E", 0.2, 0.74), ("F", 0.8, 0.74), ("LPG", 0.5, 0.74)):
        bb = d.textbbox((0, 0), text, font=font)
        d.text((x * S - (bb[2] - bb[0]) / 2 - bb[0], y * S - (bb[3] - bb[1]) / 2 - bb[1]), text, 20, font=font)
    t = math.radians(210 - 240 * 0.32)
    d.line((c - 0.1 * S * math.cos(t), c + 0.1 * S * math.sin(t), c + 0.36 * S * math.cos(t), c - 0.36 * S * math.sin(t)), fill=10, width=12)
    d.ellipse((c - 26, c - 26, c + 26, c + 26), fill=10)
    art = np.asarray(img, np.float32) / 255.0
    uu = 0.5 - (X + 0.2) / 1.44
    vv = 0.5 + (Z + 2.6) / 1.44
    face = sample_image(art, np.clip(uu, 0, 1), np.clip(vv, 0, 1))
    dirty = np.clip(0.8 + 0.2 * fine, 0, 1)
    color = np.where(dial_f[..., None], (face[..., None] ** 2.2) * dirty[..., None] * np.array((0.86, 0.85, 0.78), np.float32), color)
    rough = np.where(dial_f, 0.24, rough)
    metal = np.where(dial_f, 0.0, metal)
    height = np.where(dial_f, 0.0, height)

# The data plate, stamped. Long side along the bottle, read from behind the truck.
plate = finish == PLATE
if plate.any():
    art = stencil_image(["LPG CYLINDER  S/N 04417", "WC 33.5 L   TARE 13.6 KG", "TEST 3.3 MPA  03-24"], (1020, 600), bridge=False)
    uu = 0.5 + (-7.1 - Y) / 3.4 * 0.94
    vv = 0.5 - around(130) / 1.76 * 0.86
    stamp = sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))
    pc = flat((176, 176, 170)) * (0.82 + 0.3 * mid[..., None])
    pc = mix(pc, np.broadcast_to(np.array((0.015, 0.015, 0.016), np.float32), (H, W, 3)), stamp * 0.85)
    pc = mix(pc, pc * 0.45, smooth(0.45, 0.8, crevice + (mid - 0.5)))
    color = np.where(plate[..., None], pc, color)
    rough = np.where(plate, 0.42 + 0.22 * fine + stamp * 0.3, rough)
    metal = np.where(plate, 1 - stamp * 0.85, metal)
    height = np.where(plate, stamp * 0.012 + 0.001 * (micro - 0.5), height)

# ---- What the blast did. ----
if VARIANT != "intact":
    # Enamel burned back: first soot, then blistered and flaking, then bare scaled steel at the tear.
    ash = flat((96, 92, 86))
    blister = field(noise(pts, 2.2, 41, 3))
    flake = smooth(0.42, 0.5, blister + (micro - 0.5) * 0.3 + (scorch - 0.5) * 0.9)
    tint = np.broadcast_to(np.array((0.05, 0.042, 0.04), np.float32), (H, W, 3)) * (0.7 + 0.9 * mid[..., None])
    blue = np.broadcast_to(np.array((0.03, 0.04, 0.07), np.float32), (H, W, 3))
    scale = mix(tint, blue, smooth(0.45, 0.7, field(noise(pts, 1.2, 42, 3))) * 0.6)
    painted_goods = shell | weld | guard_f
    # Going in toward the tear: enamel browned by the heat, then black, then gone to ash and scale.
    c = mix(color, color * np.array((0.62, 0.5, 0.36), np.float32), heat)
    c = mix(c, c * 0.24, blackened * 0.94)
    c = mix(c, ash * (0.5 + 0.5 * fine[..., None]), scorch * 0.6)
    c = mix(c, scale, scorch * flake)
    color = np.where(painted_goods[..., None], c, color)
    rough = np.where(painted_goods, np.clip(rough + heat * 0.22, 0, 1) * (1 - scorch) + (0.8 + 0.14 * fine) * scorch, rough)
    metal = np.where(painted_goods, metal * (1 - scorch) + flake * scorch * 0.65, metal)
    height = np.where(painted_goods, height + scorch * (0.03 * (blister - 0.5) + 0.012 * (fine - 0.5)), height)
    # Everything nearby took the smoke, even what wasn't painted.
    others = (zinc | galv | brass | wheel | rubber | dial_f)
    color = np.where(others[..., None], mix(color, color * 0.22, np.clip(blackened * 1.05, 0, 0.92)), color)
    rough = np.where(others, rough * (1 - blackened * 0.6) + 0.86 * blackened * 0.6, rough)

    # Inside: never painted, then scoured by the burn. Sooty, with scale flaking in patches.
    soot = finish == SOOT
    pat = smooth(0.42, 0.64, field(noise(pts, 0.9, 43, 4)))
    inside = mix(flat((46, 42, 40)) * (0.7 + 0.6 * fine[..., None]), flat((88, 66, 52)) * (0.7 + 0.5 * fine[..., None]), pat * 0.75)
    inside = mix(inside, flat((124, 80, 48)), smooth(0.66, 0.8, field(noise(pts, 2.4, 44, 3))) * 0.5)
    color = np.where(soot[..., None], inside, color)
    rough = np.where(soot, 0.82 + 0.14 * fine, rough)
    metal = np.where(soot, 0.0, metal)
    height = np.where(soot, 0.02 * (fine - 0.5) + 0.01 * (micro - 0.5) + 0.03 * (mid - 0.5), height)

    # The raw torn edge, bright where the steel sheared.
    torn = finish == TORN
    t_color = mix(np.broadcast_to(steel, (H, W, 3)) * (0.5 + 0.34 * micro[..., None]), rust_c * 0.5, smooth(0.5, 0.7, fine))
    color = np.where(torn[..., None], t_color, color)
    rough = np.where(torn, 0.4 + 0.26 * fine, rough)
    metal = np.where(torn, 1 - smooth(0.5, 0.7, fine) * 0.8, metal)
    height = np.where(torn, 0.02 * (micro - 0.5), height)

# Dockside dirt: settled on what faces up, grease round the valve end, and grime that climbs from below.
upward = np.clip(nor[..., 2], 0, 1)
settled = smooth(0.42, 0.92, upward * 0.84 + (big - 0.5) * 0.36 + crevice * 0.2)
lowness = np.clip((-Z - 2.0) / 4.7, 0, 1) ** 1.5
splash = lowness * smooth(0.46, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 17, 4)) + lowness * 0.12)
dirt = np.clip(settled * 0.42 + splash * 0.56 + crevice * 0.2, 0, 0.88)
dirt = dirt * (finish != DIAL) * (finish != SOOT)
dirt_c = flat((92, 84, 70)) * (0.75 + 0.5 * fine[..., None])
color = mix(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.93 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.004 * (fine - 0.35)
if VARIANT != "cap":
    grease = smooth(13.0, 17.0, Y + (mid - 0.5) * 5.0) * smooth(0.4, 0.75, big * 0.5 + mid * 0.5 + crevice * 0.3)
    color = color * (1 - grease[..., None] * 0.26 * np.array((1.0, 1.0, 1.05), np.float32))
    rough = rough * (1 - grease * 0.22)

color = color * (0.72 + 0.28 * ao[..., None])
# Fill the gutters from every covered texel: eroding first would lose bevel strips a pixel or two wide.
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{MAT}_color.png"), color)
save_gray(os.path.join(OUT, f"{MAT}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{MAT}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{MAT}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{MAT}_normal.png"), normal)
print(VARIANT, "painted", flush=True)
