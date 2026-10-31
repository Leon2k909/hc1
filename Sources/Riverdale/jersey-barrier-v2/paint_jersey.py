"""Paint the barrier's maps from its bakes: python paint_jersey.py <work dir> <output dir>

Precast concrete left out in the rain at a hydro plant: form seams and bug holes from the casting, aggregate where the corners have
been knocked, dark damp climbing from the foot, moss in the wet places, rain streaks from every ledge, rust bled from the steel, and
tyre scuffs along the toe. Faded yellow on its ends and a stencilled number. All worked out from each texel's 3D position, so it
crosses UV seams. Lettering is invented and plainly descriptive. No brands.
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
from scipy.spatial import cKDTree  # noqa: E402

CONCRETE, RUST, STEEL = 0, 1, 2

pos4 = load("bake_jb_pos")
nor4 = load("bake_jb_nor")
facts4 = load("bake_jb_facts")
ao4 = load("bake_jb_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "jersey.json")))
density, RANGE, HALF = meta["density"], meta["range"], meta["half"]
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
pos, nor, finish = fill_from(cover, pos, nor, finish)
aoc = ao4[..., 0] > 0.001
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4
pts = pos[cover]
print("coverage %.2f, %.1f px/in" % (cover.mean(), density), flush=True)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def solid(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


big = field(noise(pts, 0.035, 1, 3))
mid = field(noise(pts, 0.16, 2, 4))
fine = field(noise(pts, 0.8, 3, 3))
micro = field(noise(pts, 3.2, 4, 2))
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
crevice = np.clip((1 - ao) * 1.4, 0, 1)
up = np.clip(nor[..., 2], 0, 1)

# Distance to the section's arrises and the ends, worked out from the known profile rather than from the texels' curvature.
ay, az = np.abs(Y), Z
knee_a = np.hypot(ay - 12.0, az - 3.0)
knee_b = np.hypot(ay - 8.5, az - 10.0)
crown = np.hypot(ay - 4.3, az - 31.6)
ends = HALF - np.abs(X)
edge_d = np.minimum.reduce((knee_a * 1.3, knee_b * 1.3, crown, ends))
corner = smooth(3.2, 0.2, edge_d)
near = smooth(7.0, 1.0, edge_d)

# Each barrier was poured in a steel form: panel seams up the sides, one faint pour line.
seam_x = np.minimum.reduce([np.abs(X - s) for s in (-29.5, 29.5)])
seams = smooth(0.35, 0.05, seam_x) * (np.abs(nor[..., 2]) < 0.85)
pour = smooth(0.22, 0.04, np.abs(Z - 19.0 - (big - 0.5) * 1.2)) * (np.abs(nor[..., 2]) < 0.85)

# Bug holes: small round pits where air was trapped against the form, thicker on the sloped faces.
r = np.random.default_rng(1961)
count = 1300
hole_x = r.uniform(-HALF, HALF, count)
hole_z = r.uniform(4.0, 31.0, count)
hole_side = r.choice((-1.0, 1.0), count)
hole_y = hole_side * np.where(hole_z < 10.0, 12.0 - (hole_z - 3.0) * 0.5, 8.5 - (hole_z - 10.0) * (3.75 / 22.0))
sizes = r.uniform(0.035, 0.13, count)
dist, which = cKDTree(np.column_stack((hole_x, hole_y, hole_z))).query(pts, k=1, distance_upper_bound=0.45, workers=4)
which = np.minimum(which, count - 1)
pits = field(smooth(1.0, 0.55, np.where(np.isfinite(dist), dist, 9.0) / sizes[which]).astype(np.float32))

# Rain: running down from the crown and from under every slot and loop, long and straight on the faces.
streak = field(noise(pts * np.array((1.0, 1.0, 0.06), np.float32), 0.42, 5, 4))
falls = smooth(0.5, 0.74, streak + (mid - 0.5) * 0.4) * smooth(2.0, 22.0, Z + (big - 0.5) * 8)
falls = falls * (np.abs(nor[..., 2]) < 0.9)
ledge = smooth(26.0, 23.0, Z) * smooth(10.0, 20.0, Z) * smooth(4.2, 1.6, np.minimum(np.abs(np.abs(X) - 40.0), 99.0)) * (np.abs(nor[..., 2]) < 0.9)

base = mix(solid(148, 145, 136), solid(126, 123, 114), smooth(0.25, 0.75, mid * 0.5 + big * 0.5))
base = base * (0.92 + 0.14 * fine[..., None])
# The cast skin: paler laitance worn off in patches, showing fine aggregate where it's gone.
skin_gone = smooth(0.6, 0.84, field(noise(pts, 0.5, 6, 3)) + near * 0.1 + (fine - 0.5) * 0.2)
aggregate = field(noise(pts, 2.8, 7, 2))
pebbles = mix(solid(112, 108, 98), solid(158, 153, 140), smooth(0.35, 0.65, aggregate))
color = mix(base, pebbles, skin_gone * 0.22)
height = 0.012 * (micro - 0.5) + 0.02 * (fine - 0.5) + 0.05 * (mid - 0.5) - skin_gone * 0.016 + skin_gone * 0.02 * (aggregate - 0.5)
rough = 0.86 + 0.08 * fine

# Form seams and the pour line.
color = color * (1 - seams[..., None] * 0.26) * (1 - pour[..., None] * 0.12)
height = height - seams * 0.05 - pour * 0.012
# Each form panel came out a slightly different grey.
panel = (np.floor((X + 29.5) / 59.0) + 2) % 3
color = color * (0.96 + 0.04 * panel[..., None])
color = np.where((pits > 0.02)[..., None], color * (1 - pits[..., None] * 0.48), color)
height = height - pits * 0.05

# Corners knocked back to the aggregate, in bites. The largest wounds are in the mesh, and this roughens and pales them.
bite = corner * smooth(0.42, 0.68, mid * 0.45 + fine * 0.55) * 0.92 + smooth(0.76, 0.9, field(noise(pts, 0.34, 8, 3))) * 0.36 + near * 0.06 * (fine - 0.3)
chipped = smooth(0.52, 0.62, bite)
raw = mix(solid(116, 110, 100), solid(156, 150, 136), smooth(0.32, 0.68, aggregate))
color = mix(color, raw, chipped)
height = height - chipped * 0.08 + chipped * 0.05 * (aggregate - 0.5)
rough = rough * (1 - chipped) + 0.94 * chipped
# The broken corner itself, by distance from where it broke.
broken = smooth(5.6, 3.4, np.linalg.norm(pos - np.array(meta["broken"], np.float32), axis=-1))
color = mix(color, raw, broken)
height = height + broken * 0.09 * (aggregate - 0.5)

# Faded yellow on both ends: three diagonal stripes on each face's last 12 inches, flaking with the skin.
stripes = (np.mod((np.abs(X) + Z) / 7.0, 1.0) < 0.5) & (np.abs(X) > HALF - 12.5) & (Z > 11.0) & (Z < 31.0) & (np.abs(nor[..., 2]) < 0.85)
flake = smooth(0.26, 0.4, field(noise(pts, 1.1, 9, 3)) + (fine - 0.5) * 0.3 + big * 0.1)
yellow = stripes * flake * (1 - chipped) * (1 - pits) * 0.66
color = mix(color, solid(150, 124, 54) * (0.82 + 0.3 * mid[..., None]), yellow)
height = height + yellow * 0.004
rough = rough - yellow * 0.1
# A stencilled number and the plant's initials on each face, sprayed long ago.
art = stencil_image(["RHP 07", "KEEP 3M CLEAR"], (1000, 420), bridge=False)
letters = np.zeros((H, W), np.float32)
for side, flip in ((-1, 1.0), (1, -1.0)):
    uu = (flip * X + 17.0) / 34.0
    vv = (Z - 14.0) / 14.2
    hit = sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) * (nor[..., 1] * side > 0.5)
    letters = np.maximum(letters, hit)
letters = letters * smooth(0.22, 0.42, field(noise(pts, 1.8, 10, 3)) + big * 0.1) * (1 - chipped)
color = mix(color, solid(180, 176, 160) * (0.84 + 0.2 * fine[..., None]), letters * 0.5)
rough = rough - letters * 0.06

# Rain over the paint: dark streaks, and pale lime where it dried.
color = color * (1 - falls[..., None] * np.array((0.3, 0.3, 0.28), np.float32))
lime = smooth(0.62, 0.78, streak + (fine - 0.5) * 0.2) * smooth(14.0, 6.0, Z) * smooth(0.0, 3.0, Z)
color = mix(color, solid(196, 192, 176), lime * 0.3)
color = color * (1 - ledge[..., None] * smooth(0.45, 0.7, streak)[..., None] * 0.38)
rough = rough - falls * 0.22

# Rust bled from the end loops and plate, down the end faces.
end_face = smooth(HALF - 3.5, HALF - 0.8, np.abs(X))
bleed = end_face * smooth(4.2, 1.0, np.abs(Y) + (fine - 0.5) * 1.2) * smooth(26.0, 12.0, Z) * smooth(0.36, 0.62, field(noise(pts * np.array((1.0, 1.0, 0.1), np.float32), 0.8, 11, 3)))
rust_tint = mix(solid(92, 52, 28), solid(136, 84, 46), smooth(0.3, 0.7, fine))
color = mix(color, rust_tint, bleed * 0.7)
near_break = smooth(9.0, 4.0, np.linalg.norm(pos - np.array(meta["broken"], np.float32), axis=-1)) * smooth(0.48, 0.7, streak)
color = mix(color, rust_tint, near_break * 0.55)

# Damp climbing from the foot, and moss where it stays wet: in the scuppers and on the shaded toe.
low = np.clip(1 - Z / 9.0, 0, 1)
damp = low ** 1.4 * smooth(0.25, 0.65, mid * 0.6 + big * 0.4 + 0.1)
color = color * (1 - damp[..., None] * 0.48)
rough = rough - damp * 0.34
moss_where = smooth(0.42, 0.66, field(noise(pts, 0.26, 12, 3)) + crevice * 0.34 + low * 0.26) * smooth(14.0, 2.0, Z) * smooth(-0.3, 0.1, up * 0.8 + (fine - 0.5) * 0.4)
moss = moss_where * smooth(0.3, 0.6, fine * 0.55 + micro * 0.45)
color = mix(color, mix(solid(44, 54, 26), solid(70, 80, 40), smooth(0.3, 0.7, micro)), moss * 0.62)
rough = rough * (1 - moss) + 0.95 * moss
height = height + moss * 0.03 * (micro - 0.2)

# Tyre scuffs along the toe: long black smears where vehicles have rubbed it.
scuff_band = smooth(1.5, 4.0, Z) * smooth(13.0, 7.0, Z) * (np.abs(nor[..., 2]) < 0.9)
smear = field(noise(pts * np.array((0.05, 1.0, 1.0), np.float32), 0.9, 13, 3))
scuff = scuff_band * smooth(0.6, 0.78, smear) * smooth(0.36, 0.56, field(noise(pts, 0.05, 14, 2)))
color = mix(color, solid(26, 25, 24), scuff * 0.74)
rough = rough - scuff * 0.2

color = color * (1 - crevice[..., None] * 0.28)
metal = np.zeros((H, W), np.float32)

# Rebar and end loops: rough rust, the lugs in the normal map.
rebar = finish == RUST
ribs = 0.5 + 0.5 * np.sin((X + Y + Z) * 2 * math.pi / 0.7)
rb_color = mix(solid(58, 34, 22), solid(120, 72, 40), smooth(0.3, 0.75, fine * 0.5 + micro * 0.5))
color = np.where(rebar[..., None], rb_color, color)
rough = np.where(rebar, 0.86 + 0.1 * micro, rough)
height = np.where(rebar, 0.03 * ribs + 0.02 * (micro - 0.5), height)

# The galvanised plate and its bolts: dull zinc, white-rusted, lettered.
steel = finish == STEEL
plate_words = stencil_image(["RHP PRECAST", "UNIT 07"], (720, 400), bridge=False)
stamp = sample_image(plate_words, np.clip((Y - 3.7) / 3.0, -1, 2), np.clip((Z - 15.6) / 2.8, -1, 2)) * (nor[..., 0] < -0.6)
st_color = solid(128, 130, 128) * (0.72 + 0.34 * mid[..., None])
white_rust = smooth(0.42, 0.7, fine * 0.5 + mid * 0.5 + crevice * 0.3)
st_color = mix(st_color, solid(188, 186, 176), white_rust * 0.5)
st_color = mix(st_color, rust_tint, smooth(0.66, 0.82, fine + crevice * 0.3) * 0.55)
st_color = mix(st_color, solid(22, 22, 22), stamp * 0.86)
color = np.where(steel[..., None], st_color, color)
rough = np.where(steel, 0.5 + 0.24 * white_rust, rough)
metal = np.where(steel, 0.9 - white_rust * 0.6, metal)
height = np.where(steel, 0.003 * (micro - 0.5) - stamp * 0.008, height)

color = color * (0.74 + 0.26 * ao[..., None])
normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope across an island's border sees the flat gutter and draws a line down the seam, so wide islands take their border's normal
# from just inside. Thin islands, which have no inside, keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.12, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "jb_concrete_color.png"), color)
save_gray(os.path.join(OUT, "jb_concrete_rough.png"), rough)
save_gray(os.path.join(OUT, "jb_concrete_metal.png"), metal)
save_gray(os.path.join(OUT, "jb_concrete_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "jb_concrete_normal.png"), normal)
print("barrier painted", flush=True)
