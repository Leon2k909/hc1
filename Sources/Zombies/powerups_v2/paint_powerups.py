"""Paint a power-up's maps from its bakes: python paint_powerups.py <work dir> <materials dir> <one_hit|clean_sweep>

One-Hit Kills: tarnished brass, copper jackets, red-painted tips, black-oxide base, olive web strap and a stamped tag.
Clean Sweep: safety-orange enamel chipped back to steel, hazard stripes, black hardware, rubber grips, red and dark leads.
Wear is worked out in 3D, so it runs across UV seams. Lettering is generic, with no brand, real or game.
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

VARIANT = sys.argv[3]
MAT = {"one_hit": "pu_one_hit", "clean_sweep": "pu_clean_sweep"}[VARIANT]
PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, CARRY, COPPER, HARD, TIP, WEB, ORANGE, WIRE_RED, WIRE_DARK = range(16)

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
convex = np.clip((curve - 2.6) * 0.38, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.4) * 2.4 + ndi.gaussian_filter(convex, 4.0) * 3.0, 0, 1)
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


big = field(noise(pts, 0.3, 1, 3))
mid = field(noise(pts, 1.2, 2, 4))
fine = field(noise(pts, 4.5, 3, 3))
micro = field(noise(pts, 14.0, 4, 2))
streak = field(noise(pts * np.array((3.6, 3.6, 0.2), np.float32), 0.5, 6, 4))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NX, NY, NZ = nor[..., 0], nor[..., 1], nor[..., 2]
A = np.arctan2(Y, X)
steel = srgb_to_linear((160, 160, 156))
rust_c = mix(flat((58, 32, 20)), flat((122, 70, 38)), smooth(0.35, 0.8, field(noise(pts, 3.1, 8, 3))))

color = np.zeros((H, W, 3), np.float32)
rough = np.zeros((H, W), np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

# Brass: warm where it's been handled, browned and spotted where it hasn't.
brass = finish == BRASS
tarnish = smooth(0.34, 0.74, mid * 0.5 + big * 0.3 + crevice * 0.6 - edge * 0.3)
spots = smooth(0.7, 0.8, field(noise(pts, 6.0, 5, 2)))
b_color = mix(flat((226, 180, 100)), flat((120, 84, 42)), tarnish)
b_color = mix(b_color, flat((70, 48, 28)), spots * 0.5)
color = np.where(brass[..., None], b_color, color)
rough = np.where(brass, 0.22 + 0.3 * tarnish + 0.1 * fine, rough)
metal = np.where(brass, 1.0, metal)
height = np.where(brass, 0.0012 * (micro - 0.5), height)

# Copper jackets.
copper = finish == COPPER
color = np.where(copper[..., None], mix(flat((198, 118, 74)), flat((104, 58, 36)), smooth(0.36, 0.8, mid + crevice * 0.3)), color)
rough = np.where(copper, 0.28 + 0.2 * fine, rough)
metal = np.where(copper, 1.0, metal)
height = np.where(copper, 0.001 * (micro - 0.5), height)

# Painted red: the rounds' tips and the switch's flip cover, chipped to what's beneath.
tip = finish == TIP
t_chip = smooth(0.62, 0.66, (fine - 0.5) * 0.9 + (mid - 0.5) * 0.5 + edge * 0.5 + 0.42)
t_under = flat((190, 120, 76)) if VARIANT == "one_hit" else flat((168, 168, 162))
color = np.where(tip[..., None], mix(flat((170, 22, 18)) * (0.82 + 0.26 * mid[..., None]), t_under, t_chip), color)
rough = np.where(tip, 0.34 + 0.14 * fine + t_chip * 0.06, rough)
metal = np.where(tip, t_chip, metal)
height = np.where(tip, (1 - t_chip) * 0.005 + 0.002 * (micro - 0.5), height)

# Black oxide and black enamel hardware, with its knurled base ring on the bundle.
hard = finish == HARD
h_bare = smooth(0.6, 0.64, edge * 0.72 + (fine - 0.5) * 0.9 + (mid - 0.5) * 0.5 + 0.24)
h_color = mix(flat((34, 35, 36)) * (0.74 + 0.5 * mid[..., None]), np.broadcast_to(steel, (H, W, 3)) * (0.52 + 0.34 * fine[..., None]), h_bare)
h_rust = smooth(0.48, 0.72, field(noise(pts, 1.6, 15, 3)) + crevice * 0.4) * np.maximum(h_bare, smooth(0.62, 0.8, streak) * 0.5)
h_color = mix(h_color, rust_c, h_rust)
color = np.where(hard[..., None], h_color, color)
rough = np.where(hard, (0.44 + 0.2 * mid) * (1 - h_rust) + 0.86 * h_rust, rough)
metal = np.where(hard, np.maximum(h_bare, 0.55) * (1 - h_rust) if VARIANT == "one_hit" else h_bare * (1 - h_rust), metal)
h_height = 0.003 * (micro - 0.5) + h_rust * 0.006 * (fine - 0.3)
if VARIANT == "one_hit":
    wall = (np.hypot(X, Y) > 4.05) & (np.abs(NZ) < 0.4)
    knurl = 0.5 + 0.5 * np.sin(A * 96) * np.sin(Z * 2 * math.pi / 0.36)
    h_height = h_height + wall * (Z < -6.95) * 0.012 * knurl
height = np.where(hard, h_height, height)

# Plated steel.
zinc = finish == ZINC
z_rust = smooth(0.5, 0.74, mid * 0.5 + big * 0.2 + crevice * 0.5)
z_color = flat((186, 184, 172)) * (0.54 + 0.3 * mid[..., None])
z_color = mix(z_color, rust_c, z_rust * 0.5)
z_color = mix(z_color, np.broadcast_to(steel, (H, W, 3)), smooth(0.5, 0.8, edge) * 0.5)
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, 0.3 + 0.2 * fine + 0.4 * z_rust, rough)
metal = np.where(zinc, 1 - z_rust * 0.75, metal)
height = np.where(zinc, 0.0012 * (micro - 0.5), height)

# Rubber.
rubber = finish == RUBBER
color = np.where(rubber[..., None], flat((30, 30, 30)) * (0.72 + 0.5 * fine[..., None]), color)
rough = np.where(rubber, 0.7 + 0.16 * fine, rough)
metal = np.where(rubber, 0.0, metal)
height = np.where(rubber, 0.003 * (fine - 0.5), height)

# Olive web strap, woven.
web = finish == WEB
weave = (0.5 + 0.5 * np.sin(A * 170)) * (0.5 + 0.5 * np.sin(Z * 2 * math.pi / 0.13))
color = np.where(web[..., None], flat((86, 88, 58)) * (0.72 + 0.34 * mid[..., None] + 0.16 * weave[..., None]), color)
rough = np.where(web, 0.9, rough)
metal = np.where(web, 0.0, metal)
height = np.where(web, 0.008 * weave, height)

# Insulated leads, in lengths of bright and dark, with the spool's turns showing as ribs.
for wire, tone in ((WIRE_RED, (150, 26, 20)), (WIRE_DARK, (28, 28, 30))):
    here = finish == wire
    turns = 0.5 + 0.5 * np.sin(X * 2 * math.pi / 0.17)
    on_spool = (X > 4.6) & (np.hypot(Y, Z + 4.4) > 0.9) & (np.hypot(Y, Z + 4.4) < 1.42)
    color = np.where(here[..., None], flat(tone) * (0.76 + 0.4 * mid[..., None]) * (1 - on_spool[..., None] * (1 - turns[..., None]) * 0.5), color)
    rough = np.where(here, 0.44 + 0.2 * fine, rough)
    metal = np.where(here, 0.0, metal)
    height = np.where(here, on_spool * turns * 0.03, height)

# The stamped plate.
plate = finish == PLATE
if plate.any():
    if VARIANT == "one_hit":
        stamp = place(stencil_image(["HEAVY AP-T", "12.7 MM  LOT 04417"], (540, 300), bridge=False), X, Z, 0.0, -0.1, 2.5, 1.4)
    else:
        stamp = place(stencil_image(["FIRING UNIT 10-CAP", "S/N 04417   03-24"], (760, 340), bridge=False), -X, Z, 0.0, -5.25, 3.5, 1.45)
    pc = flat((176, 176, 170)) * (0.82 + 0.3 * mid[..., None])
    pc = mix(pc, np.broadcast_to(np.array((0.015, 0.015, 0.016), np.float32), (H, W, 3)), stamp * 0.85)
    pc = mix(pc, pc * 0.5, smooth(0.45, 0.8, crevice + (mid - 0.5)))
    color = np.where(plate[..., None], pc, color)
    rough = np.where(plate, 0.42 + 0.22 * fine + stamp * 0.3, rough)
    metal = np.where(plate, 1 - stamp * 0.85, metal)
    height = np.where(plate, stamp * 0.01 + 0.001 * (micro - 0.5), height)

# Safety orange, for the blasting machine: chipped at every edge, with hazard stripes round its foot.
orange = finish == ORANGE
if orange.any():
    chip = edge * smooth(0.3, 0.68, mid * 0.65 + fine * 0.35) * 1.12 + (mid - 0.5) * 0.6 + (big - 0.5) * 0.4 + (fine - 0.5) * 0.85 + (micro - 0.5) * 0.3
    bare = smooth(0.72, 0.74, chip)
    under = smooth(0.67, 0.69, chip)
    o_color = mix(flat((186, 82, 16)), flat((214, 110, 26)), smooth(0.25, 0.75, mid * 0.5 + big * 0.5))
    o_color = mix(o_color, flat((176, 110, 62)), smooth(0.4, 0.9, big + 0.2 * np.clip(NZ, 0, 1)) * 0.36)
    upright = 1 - np.abs(NZ)
    o_color = o_color * (1 + upright[..., None] * (streak[..., None] - 0.5) * 0.4)
    stripes = np.mod((X + Y + Z) / 1.5, 1.0) < 0.5
    foot = Z < -6.15
    o_color = np.where((foot & stripes)[..., None], flat((24, 24, 24)) * (0.8 + 0.4 * mid[..., None]), o_color)
    letter = np.zeros((H, W), np.float32)
    front, back = orange & (NY < -0.7), orange & (NY > 0.7)
    letter = np.maximum(letter, place(stencil_image(["DANGER"], (800, 200)), X, Z, 0.0, -2.72, 6.6, 1.65) * front)
    letter = np.maximum(letter, place(stencil_image(["DETONATOR  KEEP CLEAR"], (800, 120), bridge=False), X, Z, 0.0, -5.15, 7.6, 1.15) * front)
    letter = np.maximum(letter, place(stencil_image(["KEEP CLEAR"], (800, 200)), -X, Z, 0.0, -3.1, 6.6, 1.65) * back)
    letter = letter * smooth(0.12, 0.3, field(noise(pts, 3.3, 10, 3)) + (big - 0.5) * 0.15)
    o_color = mix(o_color, flat((18, 18, 18)), letter * 0.94)
    o_color = mix(o_color, flat((110, 106, 92)), under)
    o_color = mix(o_color, np.broadcast_to(steel, (H, W, 3)) * (0.66 + 0.42 * fine[..., None]), bare)
    o_rust = bare * smooth(0.44, 0.7, field(noise(pts, 1.7, 12, 3)) + crevice * 0.4)
    o_color = mix(o_color, rust_c, o_rust)
    runs = smooth(0.54, 0.78, streak + crevice * 0.3) * smooth(0.26, 0.6, mid + crevice * 0.4)
    o_color = mix(o_color, o_color * rust_c * 3.0, runs * 0.5)
    color = np.where(orange[..., None], o_color, color)
    rough = np.where(orange, (0.4 + 0.16 * mid + 0.08 * fine) * (1 - bare) + 0.42 * bare + o_rust * 0.44, rough)
    metal = np.where(orange, bare * (1 - o_rust), metal)
    height = np.where(orange, 0.004 * (micro - 0.5) + 0.002 * (fine - 0.5) + (1 - under) * 0.008 + (1 - bare) * 0.007 + letter * 0.0016, height)

# A little dust and grime, kept light on the rounds so they still catch the eye.
upward = np.clip(NZ, 0, 1)
settled = smooth(0.46, 0.94, upward * 0.8 + (big - 0.5) * 0.36 + crevice * 0.2)
dirt = np.clip(settled * 0.26 + crevice * 0.14, 0, 0.6) * (~brass) * (~copper) * (~tip)
color = mix(color, flat((92, 84, 70)) * (0.75 + 0.5 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.93 * dirt
metal = metal * (1 - dirt)

color = color * (0.74 + 0.26 * ao[..., None])
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
