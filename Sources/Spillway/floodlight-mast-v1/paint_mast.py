"""Paint the yard floodlight mast's PBR maps from the bakes, with numpy. Every map is authored here; nothing is downloaded.

python paint_mast.py <work dir> <materials dir>

Reads bake_mast_{pos,nor,facts,ao}.npy and mast_edges.npy from the work dir (mast.py's bake stage writes them) and writes
mast_hw_{color,normal,rough}.png (2048 px) and mast_hw_{metal,ao}.png (1024 px) into the materials dir.

Wear is worked out in 3D from the baked position and normal of every texel, so it runs across UV seams and stays the same
size in inches whatever density an island was packed at. Yellow paint over hot-dip zinc, chipped on the lower mast where
trucks and people reach, rust where the chips are and running downhill from them; zinc spangle with white rust and soot
streaks; a dark powder-coated housing chalked on top and rubbed to aluminium on the fin tips and the bezel rim.
Maps are OpenGL normals (as s&box reads them), rows flipped to image order on save.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

WORK, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

HOUSING, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, YELLOW = range(10)
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
META = json.load(open(os.path.join(WORK, "mast.json")))
POS_RANGE = META["range"]
DENSITY = META["density"]          # texels per inch at weight 1
Z0 = META["z0"]


def srgb_to_linear(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def C(rgb):
    return srgb_to_linear(rgb)


def mixc(a, b, t):
    """Colours a and b (3,) or (N, 3), blended by t (N,)."""
    return a + (b - a) * t[:, None]


def fill_from(cover, *arrays):
    index = ndi.distance_transform_edt(~cover, return_distances=False, return_indices=True)
    return [a[tuple(index)] for a in arrays]


def load(name):
    return np.load(os.path.join(WORK, name + ".npy"))


_lattices = {}


def noise(p, freq, seed=0, octaves=1, gain=0.5):
    """Value noise over points p (N, 3), about 0..1, wrapped on a 64-cell lattice and smoothed so it has no grid look."""
    total = np.zeros(p.shape[0], np.float32)
    amp = 1.0
    norm = 0.0
    for o in range(octaves):
        key = seed * 37 + o
        if key not in _lattices:
            lat = np.random.default_rng(key + 11).random((64, 64, 64), np.float32)
            _lattices[key] = ndi.gaussian_filter(lat, 0.8, mode="wrap")
            _lattices[key] = (_lattices[key] - _lattices[key].mean()) / (_lattices[key].std() * 4.0) + 0.5
        f = freq * 2.0 ** o
        total += amp * ndi.map_coordinates(_lattices[key], (p * f).T, order=1, mode="grid-wrap")
        norm += amp
        amp *= gain
    return total / norm


def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.uint32) * np.uint32(0x8DA6B343)) + (iy.astype(np.uint32) * np.uint32(0xD8163841)) + (iz.astype(np.uint32) * np.uint32(0xCB1AB31F))
    h = h + np.uint32((seed * 0x9E3779B1) & 0xFFFFFFFF)
    h ^= h >> np.uint32(15)
    h *= np.uint32(0x2C1B3C6D)
    h ^= h >> np.uint32(12)
    h *= np.uint32(0x297A2D39)
    h ^= h >> np.uint32(15)
    return (h >> np.uint32(8)).astype(np.float32) / np.float32(1 << 24)


def voronoi(points, cell, seed=0):
    """Jittered-grid Voronoi over 3D points: (random value of the nearest feature, a second one, F2 - F1 in cells)."""
    p = points.astype(np.float64) / cell
    base = np.floor(p).astype(np.int64)
    n = p.shape[0]
    f1 = np.full(n, 9.0, np.float32)
    f2 = np.full(n, 9.0, np.float32)
    va = np.zeros(n, np.float32)
    vb = np.zeros(n, np.float32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = base + np.array((dx, dy, dz), np.int64)
                feat = np.stack([c[:, k] + 0.15 + 0.7 * _hash(c[:, 0], c[:, 1], c[:, 2], seed + 1 + k) for k in range(3)], 1)
                d = np.linalg.norm(p - feat, axis=1).astype(np.float32)
                closer = d < f1
                f2 = np.where(closer, f1, np.minimum(f2, d))
                va = np.where(closer, _hash(c[:, 0], c[:, 1], c[:, 2], seed + 11), va)
                vb = np.where(closer, _hash(c[:, 0], c[:, 1], c[:, 2], seed + 12), vb)
                f1 = np.where(closer, d, f1)
    return va, vb, f2 - f1


def to_normal(height, px_per_in, strength=1.0):
    """Tangent-space normal of a height in inches (px_per_in may vary per texel), rows bottom-up as Blender stores images."""
    dv, du = np.gradient(height)
    n = np.stack((-du * px_per_in * strength, -dv * px_per_in * strength, np.ones_like(height)), -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def save_rgb(path, linear=None, data=None):
    a = linear_to_srgb(linear) if linear is not None else data
    Image.fromarray((np.clip(a, 0, 1)[::-1] * 255 + 0.5).astype(np.uint8)).save(path, optimize=False, compress_level=6)


def save_gray(path, a, size=None):
    img = Image.fromarray((np.clip(a, 0, 1)[::-1] * 255 + 0.5).astype(np.uint8), "L")
    if size and size != img.width:
        img = img.resize((size, size), Image.LANCZOS)
    img.save(path, compress_level=6)


def save_normal(path, n):
    save_rgb(path, data=n * 0.5 + 0.5)


def stencil_image(lines, size):
    """White lettering on black."""
    w, h = size
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    rows = len(lines)
    band = h / rows
    for k, line in enumerate(lines):
        font = ImageFont.truetype(FONT, int(band * 0.72))
        try:
            font.set_variation_by_name("Bold Condensed")
        except Exception:
            pass
        bb = d.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        if tw > w * 0.94:
            font = ImageFont.truetype(FONT, int(band * 0.72 * w * 0.94 / tw))
            bb = d.textbbox((0, 0), line, font=font)
            tw = bb[2] - bb[0]
        d.text(((w - tw) // 2 - bb[0], int(k * band + (band - (bb[3] - bb[1])) / 2) - bb[1]), line, 255, font=font)
    return np.asarray(img, np.float32) / 255.0


def sample_image(image, uu, vv):
    """Sample a top-down image with uu, vv in 0..1 (vv up). Outside is zero."""
    h, w = image.shape
    out = ndi.map_coordinates(image, ((1 - vv) * (h - 1), uu * (w - 1)), order=1, mode="constant", cval=0.0)
    return np.where((uu >= 0) & (uu <= 1) & (vv >= 0) & (vv <= 1), out, 0)


# ---------------------------------------------------------------- the bakes
pos4 = load("bake_mast_pos")
nor4 = load("bake_mast_nor")
facts4 = load("bake_mast_facts")
ao4 = load("bake_mast_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
print("coverage %.2f" % cover.mean(), flush=True)
pos = (pos4[..., :3] - 0.5) * POS_RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
weight = facts4[..., 2] * 8.0
pos, nor, finish, part, weight = fill_from(cover, pos, nor, finish, part, weight)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4

# Curvature from how the smooth normal turns over the surface: real bevels light up, round tubes stay quiet.
curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 2.6) * 0.38, 0, 1)
concave = np.clip((-curve - 2.6) * 0.34, 0, 1)
edge_c = np.clip(ndi.gaussian_filter(convex, 2.0) * 2.4 + ndi.gaussian_filter(convex, 5.0) * 3.0, 0, 1)
del curve, convex

# Everything from here is worked on the covered texels as flat vectors.
P = pos[cover]
Nn = nor[cover]
fin = finish[cover]
prt = part[cover]
wgt = weight[cover]
AO = ao[cover]
CONC = concave[cover]
EDGEC = edge_c[cover]
N = P.shape[0]
X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
radial = np.hypot(X, Y)
theta = np.arctan2(Y, X)
height_above = Z - Z0
up = np.clip(Nn[:, 2], 0, 1)
upright = 1 - np.abs(Nn[:, 2])
crevice = np.clip((1 - AO) * 1.3, 0, 1)
print("texels", N, flush=True)

# Distance to the nearest sharp convex edge, from the points the build recorded along them.
edge_pts = np.load(os.path.join(WORK, "mast_edges.npy"))
dist_edge, _ = cKDTree(edge_pts).query(P, k=1, workers=-1)
edge = np.clip(np.maximum(EDGEC, (1 - smooth(0.035, 0.26, dist_edge)) * 0.92), 0, 1)

big = noise(P, 0.11, 1, 3)
mid = noise(P, 0.55, 2, 4)
fine = noise(P, 2.7, 3, 3)
micro = noise(P, 11.0, 4, 2)
age = noise(P, 0.045, 20, 3)
# Rain and rust run downhill: noise squashed along the mast, long in z and narrow round it.
streak = noise(P * np.array((4.2, 4.2, 0.13), np.float32), 0.26, 6, 4)
streak2 = noise(P * np.array((9.0, 9.0, 0.30), np.float32), 0.30, 15, 3)
print("noise done", flush=True)
edge_patchy = edge * smooth(0.30, 0.64, mid * 0.65 + fine * 0.35)
rust_tone = noise(P, 3.1, 8, 3)
steel = C((170, 170, 167))
rust_dark, rust_mid, rust_bright = C((58, 30, 18)), C((88, 50, 28)), C((128, 74, 40))


def rust_color(t):
    out = mixc(rust_dark, rust_mid, smooth(0.25, 0.6, t))
    return mixc(out, rust_bright, smooth(0.78, 0.98, t))


rust_c = rust_color(rust_tone)

# Long scratches, drawn in UV so they stay sharp.
scratch_img = Image.new("L", (W, H), 0)
draw = ImageDraw.Draw(scratch_img)
rs = np.random.default_rng(7)
for _ in range(1400):
    x, y = rs.uniform(0, W), rs.uniform(0, H)
    a = rs.uniform(0, 2 * math.pi)
    n = rs.integers(10, 80)
    bend = rs.normal(0, 0.012)
    line = []
    for s in np.linspace(0, n, 6):
        line.append((x + math.cos(a) * s, y + math.sin(a) * s))
        a += bend * 6
    draw.line(line, fill=int(rs.uniform(70, 235)), width=1)
SCR = (np.asarray(scratch_img, np.float32)[::-1] / 255.0)[cover] * smooth(0.40, 0.62, big + (mid - 0.5) * 0.5)

color = np.zeros((N, 3), np.float32)
rough = np.zeros(N, np.float32)
metal = np.zeros(N, np.float32)
height = np.zeros(N, np.float32)
tilt = np.zeros((N, 2), np.float32)         # facet tilt of zinc crystals, straight into the normal map


def put(mask, c, r, m, h):
    color[mask] = c[mask] if c.ndim == 2 and c.shape[0] == N else c
    rough[mask] = r[mask]
    metal[mask] = m[mask]
    height[mask] = h[mask]


# ---------------------------------------------------------------- yellow paint over zinc: the lower mast and the ribs
yel = fin == YELLOW
paint = mixc(C((226, 166, 14)), C((242, 196, 36)), smooth(0.25, 0.75, mid * 0.55 + big * 0.45))
paint = mixc(paint, C((226, 198, 108)), smooth(0.3, 0.8, big + 0.15 * up) * 0.26)
paint = paint * (1 + upright[:, None] * (streak[:, None] - 0.5) * 0.42)
# A hazard band of black stripes round the mast where a wing mirror reaches; an integer number of stripes, so no seam.
band = (Z > 28.0) & (Z < 41.0) & (radial < 3.9)
phase = theta * 10.0 / (2 * math.pi) + Z * 10.0 / (2 * math.pi * 3.1)
stripes = np.mod(phase, 1.0) < 0.5
paint = np.where((band & stripes)[:, None], C((30, 30, 28)) * (0.8 + 0.4 * mid[:, None]), paint)
impact = smooth(64.0, 14.0, Z)
chip = edge_patchy * 1.1 + (mid - 0.5) * 0.55 + (big - 0.5) * 0.42 + (fine - 0.5) * 0.85 + (micro - 0.5) * 0.3 + 0.2 + impact * 0.3 + CONC * -0.1
y_bare = smooth(0.735, 0.752, chip)
y_thin = smooth(0.69, 0.71, chip)
zinc_under = mixc(C((150, 154, 152)), C((120, 124, 122)), smooth(0.3, 0.8, age)) * (0.72 + 0.4 * fine[:, None])
paint = mixc(paint, paint * 0.78, y_thin * (1 - y_bare))     # the topcoat thins out before it goes
paint = mixc(paint, zinc_under, y_bare)
y_rust = y_bare * smooth(0.46, 0.72, rust_tone + crevice * 0.4 + impact * 0.12) * 0.85
paint = mixc(paint, rust_c, y_rust)
# Black tyre and bumper rubbed on at the height of a truck: sharp-edged marks, wide round the mast and short up it.
scuff = smooth(0.665, 0.685, noise(P * np.array((0.8, 0.8, 3.2), np.float32), 0.42, 21, 3) + (fine - 0.5) * 0.08) * smooth(52.0, 20.0, Z) * (1 - y_bare)
scuff = scuff * (0.45 + 0.4 * fine)
paint = mixc(paint, C((26, 25, 24)), scuff)
# Rain running down the paint from the data plate and the top lip, a shade duller than the rest.
drip = smooth(0.56, 0.74, streak2 + (1 - AO) * 0.15) * upright * smooth(66.0, 30.0, Z)
paint = paint * (1 - 0.16 * drip)[:, None]
y_rough = 0.46 + 0.2 * mid + 0.1 * fine
y_rough = y_rough * (1 - y_thin * 0.4) + (0.42 + 0.3 * fine) * y_bare
y_rough = y_rough * (1 - y_rust) + 0.84 * y_rust
y_rough = y_rough * (1 - scuff * 0.6) + 0.86 * scuff * 0.6
y_metal = np.maximum(y_bare * (1 - y_rust), SCR * 0.5)
y_height = 0.005 * (micro - 0.5) + 0.0024 * (fine - 0.5) - y_bare * 0.01 + y_rust * 0.007 * (rust_tone - 0.2) + scuff * 0.001
paint = mixc(paint, steel * 0.84, SCR * 0.5 * (1 - y_bare))
put(yel, paint, y_rough, y_metal, y_height)

# ---------------------------------------------------------------- hot-dip galvanised steel: pole, arm, braces, plates
galv = fin == GALV
ident, ident_b, border = voronoi(P[galv], 0.40, seed=3)


def spread(v, default=0.0):
    out = np.full(N, default, np.float32)
    out[galv] = v
    return out


ident, ident_b, border = spread(ident, 0.5), spread(ident_b, 0.5), spread(border, 1.0)
lum = 0.86 + 0.18 * ident + 0.30 * (big - 0.5) + 0.12 * (fine - 0.5)
dull = smooth(0.35, 0.78, age + (mid - 0.5) * 0.3)                      # old zinc goes dark and flat
g_color = mixc(C((158, 162, 160)), C((112, 116, 114)), dull) * lum[:, None]
g_color = g_color * (1 - 0.1 * smooth(0.10, 0.0, border))[:, None]        # crystal boundaries, faint
g_color = g_color * (0.93 + 0.14 * prt)[:, None]
g_white = smooth(0.58, 0.78, streak + crevice * 0.22 + (age - 0.5) * 0.2)  # white rust under anything that holds water
g_color = mixc(g_color, C((200, 198, 186)) * 0.78, g_white * 0.55)
soot = smooth(0.5, 0.8, streak2) * smooth(110.0, 270.0, Z) * upright   # black runs down from the lamp heads
g_color = mixc(g_color, C((58, 54, 48)), soot * 0.55)
low_g = np.clip(1 - height_above / 30.0, 0, 1) ** 1.3
g_rust = smooth(0.77, 0.93, noise(P, 1.5, 22, 3) + crevice * 0.34 + low_g * 0.26) * (1 - g_white * 0.5)
# Water tracks out of every joint and stains the zinc below it brown for a few inches.
joint = np.zeros(N, np.float32)
for z_joint, run in ((150.0, 12.0), (246.5, 10.0), (290.6, 10.0)):
    below = smooth(z_joint + 1.0, z_joint - 0.5, Z)        # 0 above the joint, 1 just under it
    fade = smooth(z_joint - run, z_joint - 1.0, Z)         # 1 at the joint, 0 `run` inches lower
    joint = np.maximum(joint, below * fade)
g_stain = joint * smooth(0.42, 0.7, streak * 0.55 + streak2 * 0.45) * upright
g_color = mixc(g_color, C((104, 78, 52)), g_stain * 0.5)
g_color = mixc(g_color, rust_c, g_rust * 0.8)
g_color = mixc(g_color, steel, SCR * 0.7)
g_color = g_color * (1 - 0.45 * smooth(0.1, 0.8, 1 - AO))[:, None]
g_rough = 0.34 + 0.24 * ident + 0.16 * mid + dull * 0.18 + g_white * 0.28
g_rough = g_rough * (1 - g_rust * 0.8) + (0.8 + 0.12 * fine) * g_rust * 0.8
g_rough = g_rough * (1 - SCR * 0.5) + 0.3 * SCR * 0.5
g_metal = np.clip(1.0 - g_white * 0.65 - g_rust * 0.9, 0, 1)
g_height = 0.0022 * (ident - 0.5) - 0.0016 * smooth(0.1, 0.0, border) + 0.0012 * (micro - 0.5) - SCR * 0.003 + g_rust * 0.006 * (rust_tone - 0.2)
tilt[galv, 0] = ((ident_b - 0.5) * 0.11)[galv] * (1 - g_rust[galv])
tilt[galv, 1] = ((ident - 0.5) * 0.11)[galv] * (1 - g_rust[galv])
put(galv, g_color, g_rough, g_metal, g_height)

# ---------------------------------------------------------------- powder-coated lamp housing
hs = fin == HOUSING
h_base = mixc(C((66, 72, 78)), C((96, 102, 108)), smooth(0.2, 0.8, mid * 0.6 + big * 0.4))
chalk = smooth(0.35, 0.9, up * 0.8 + (big - 0.5) * 0.4)
h_color = mixc(h_base, C((122, 126, 126)), chalk * 0.5)
h_color = h_color * (1 + upright[:, None] * (streak2[:, None] - 0.5) * 0.5) * (0.9 + 0.2 * prt)[:, None]
h_wear = smooth(0.58, 0.72, edge_patchy * 1.2 + (fine - 0.5) * 0.9 + (micro - 0.5) * 0.3)
h_color = mixc(h_color, C((178, 180, 182)) * (0.7 + 0.4 * fine[:, None]), h_wear)
h_color = mixc(h_color, steel * 0.8, SCR * 0.45)
h_rough = 0.5 + 0.18 * mid + 0.1 * fine
h_rough = h_rough * (1 - h_wear) + (0.36 + 0.22 * fine) * h_wear
h_metal = np.maximum(h_wear, SCR * 0.5)
h_height = 0.0035 * (micro - 0.5) - h_wear * 0.004 - SCR * 0.002
put(hs, h_color, h_rough, h_metal, h_height)

# ---------------------------------------------------------------- black oxide: hinges, latches, the cable gland
ox = fin == OXIDE
o_wear = smooth(0.44, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
o_color = np.broadcast_to(C((42, 42, 44)), (N, 3)) * (0.75 + 0.5 * mid[:, None])
o_color = mixc(o_color, steel * 0.8, o_wear * 0.9)
o_rust = smooth(0.8, 0.9, noise(P, 3.6, 11, 3) + crevice * 0.06)
o_color = mixc(o_color, rust_c, o_rust * 0.7)
put(ox, o_color, 0.4 + 0.2 * fine - 0.1 * o_wear + 0.35 * o_rust, (1 - o_rust) * 0.92, 0.0016 * (micro - 0.5) + o_rust * 0.006 * (rust_tone - 0.3) - o_wear * 0.002)

# ---------------------------------------------------------------- plated fasteners
zn = fin == ZINC
yellow_pass = np.mod(prt * 7.0, 1.0) > 0.68
z_base = np.where(yellow_pass[:, None], C((176, 158, 112)), C((186, 188, 186)))
z_white = smooth(0.48, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.5)
z_color = z_base * (0.52 + 0.3 * mid[:, None])
z_color = mixc(z_color, rust_mid, z_white * 0.55)
z_color = mixc(z_color, steel, smooth(0.5, 0.8, edge) * 0.5)
put(zn, z_color, 0.3 + 0.2 * fine + 0.4 * z_white, 1 - z_white * 0.75, 0.0012 * (micro - 0.5))

# ---------------------------------------------------------------- brass earth lug
br = fin == BRASS
b_tarnish = smooth(0.32, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.7 - edge * 0.45)
b_color = mixc(C((214, 170, 92)), C((92, 66, 34)), b_tarnish)
b_green = smooth(0.66, 0.84, noise(P, 2.1, 12, 3) + crevice * 0.26)
b_color = mixc(b_color, C((86, 112, 86)), b_green * 0.55)
put(br, b_color, 0.24 + 0.34 * b_tarnish + 0.1 * fine + 0.2 * b_green, 1 - b_green * 0.7, 0.0012 * (micro - 0.5))

# ---------------------------------------------------------------- rubber: the lamp cable and the bezel gaskets
rb = fin == RUBBER
cracks = smooth(0.62, 0.7, noise(P, 7.0, 23, 3))
r_color = C((30, 30, 30)) * (0.75 + 0.5 * fine[:, None])
r_color = mixc(r_color, C((62, 60, 56)), smooth(0.4, 0.8, up * 0.7 + (big - 0.5) * 0.5) * 0.5)
put(rb, r_color, 0.74 + 0.14 * fine, np.zeros(N, np.float32), 0.003 * (micro - 0.5) - cracks * 0.003)

# ---------------------------------------------------------------- the foot weld: cold-galv paint over the bead
wd = fin == WELD
w_detail = noise(P, 4.2, 9, 3)
w_color = C((118, 120, 118)) * (0.7 + 0.5 * mid[:, None])
w_rust = smooth(0.62, 0.8, rust_tone + crevice * 0.3 + low_g * 0.2)
w_color = mixc(w_color, rust_c, w_rust * 0.6)
put(wd, w_color, 0.66 + 0.2 * fine, np.clip(0.55 - w_rust, 0, 1), 0.05 * (w_detail - 0.5) + 0.02 * (micro - 0.5) + w_rust * 0.004)

# ---------------------------------------------------------------- the data plate, stamped, and its rivets
pl = fin == PLATE
a_plate = np.angle(np.exp(1j * (theta - math.radians(META["plate_at"]))))
art = stencil_image(["MAST 9.5 M", "SWL 150 KG", "SW-04"], (600, 400))
uu = a_plate * radial / 4.2 + 0.5
vv = (Z - (64.0 - 1.4)) / 2.8
stamp = sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) * (np.abs(Z - 64.0) < 1.5) * (np.abs(a_plate * radial) < 2.1)
p_color = C((178, 178, 172)) * (0.82 + 0.3 * mid[:, None])
p_color = mixc(p_color, np.broadcast_to(np.array((0.015, 0.015, 0.016), np.float32), (N, 3)), stamp * 0.85)
p_color = mixc(p_color, p_color * 0.45, smooth(0.45, 0.8, crevice + (mid - 0.5)))
put(pl, p_color, 0.42 + 0.22 * fine + stamp * 0.3, 1 - stamp * 0.85, stamp * 0.012 + 0.001 * (micro - 0.5))

# ---------------------------------------------------------------- stray colours: anything left unpainted shows as magenta
left = ~(yel | galv | hs | ox | zn | br | rb | wd | pl)
print("unpainted texels", int(left.sum()), flush=True)
color[left] = C((255, 0, 255))
rough[left] = 0.5

# ---------------------------------------------------------------- dirt over everything
upward = up
low = np.clip(1 - height_above / 26.0, 0, 1) ** 1.5
settled = smooth(0.38, 0.88, upward * 0.82 + (big - 0.5) * 0.34 + crevice * 0.2)
splash = low * smooth(0.46, 0.64, noise(P * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 13, 4) + low * 0.16)
speckle = low * smooth(0.64, 0.72, noise(P, 7.5, 14, 2))
dirt = np.clip(settled * 0.34 + splash * 0.78 + speckle * 0.6, 0, 0.9)
dirt_c = C((100, 86, 66)) * (0.75 + 0.5 * fine[:, None])
color = mixc(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.93 * dirt
metal = metal * (1 - dirt)
height = height + dirt * 0.004 * (fine - 0.35)

# A little occlusion stays in the colour, so the shapes hold up under engine lighting.
color = color * (0.72 + 0.28 * AO)[:, None]
rough = np.clip(rough, 0.1, 1)
metal = np.clip(metal, 0, 1)


def image(values, shape=()):
    out = np.zeros((H, W) + shape, np.float32)
    out[cover] = values
    return out


solid = ndi.binary_erosion(cover, iterations=1)
height_i = fill_from(solid, image(height))[0]
tilt_i = fill_from(solid, image(tilt, (2,)))[0]
ppi = fill_from(cover, DENSITY * weight)[0]
normal = to_normal(ndi.gaussian_filter(height_i, 0.5), ppi, 1.0)
normal[..., 0] += tilt_i[..., 0]
normal[..., 1] += tilt_i[..., 1]
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
color_i, rough_i, metal_i, normal = fill_from(solid, image(color, (3,)), image(rough), image(metal), normal)
save_rgb(os.path.join(OUT, "mast_hw_color.png"), color_i)
save_gray(os.path.join(OUT, "mast_hw_rough.png"), rough_i)
save_gray(os.path.join(OUT, "mast_hw_metal.png"), metal_i, 1024)
save_gray(os.path.join(OUT, "mast_hw_ao.png"), np.clip(ao * 1.03, 0, 1), 1024)
save_normal(os.path.join(OUT, "mast_hw_normal.png"), normal)
print("painted", flush=True)
