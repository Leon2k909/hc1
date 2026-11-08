"""Paint the Orion launch-deck control shed's PBR maps from the bakes, with numpy. Every map is authored here; nothing is downloaded.

python paint_shed.py <work dir> <materials dir>

Reads bake_shed_{pos,nor,facts,ao}.npy, shed_edges.npy and shed.json from the work dir (shed.py's build and bake stages write
them) and writes shed_body_{color,normal}.png (2048 px) and shed_body_{rough,metal,ao}.png (1024 px) into the materials dir.

Wear is worked out in 3D from the baked position and normal of every texel, so it runs across UV seams and stays the same size
in inches whatever density an island was packed at. Graphite paint over galvanised sheet, chalked on the faces that look up,
chipped along the corrugation ridges and the posts, rusting through at the foot where the deck splashes it and streaked below the
eave; black primer on the base channel and posts with hazard stripes on the front posts; pale powder coat on the cabinet, louvre
and air-conditioner casing; zinc spangle on the roof sheet and fittings; three stencilled plates.
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

BODY, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, YELLOW, RED, DARK, LIGHT = range(13)
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
META = json.load(open(os.path.join(WORK, "shed.json")))
POS_RANGE = META["range"]
DENSITY = META["density"]          # texels per inch at weight 1
PARTS = {float(k): v for k, v in META["parts"].items()}
KEYS = np.array(sorted(PARTS), np.float64)
NAMES = [PARTS[k]["name"] for k in KEYS]


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
    """White lettering on black, each line as large as the band and the width allow."""
    w, h = size
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    rows = len(lines)
    band = h / rows
    for k, line in enumerate(lines):
        font = ImageFont.truetype(FONT, int(band * 0.62))
        try:
            font.set_variation_by_name("Bold Condensed")
        except Exception:
            pass
        bb = d.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        if tw > w * 0.9:
            font = ImageFont.truetype(FONT, int(band * 0.62 * w * 0.9 / tw))
            try:
                font.set_variation_by_name("Bold Condensed")
            except Exception:
                pass
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
pos4 = load("bake_shed_pos")
nor4 = load("bake_shed_nor")
facts4 = load("bake_shed_facts")
ao4 = load("bake_shed_ao")
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

# Curvature from how the smooth normal turns over the surface: real bevels light up, flat sheet and round tubes stay quiet.
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
up = np.clip(Nn[:, 2], 0, 1)
upright = 1 - np.abs(Nn[:, 2])
crevice = np.clip((1 - AO) * 1.3, 0, 1)
print("texels", N, flush=True)

# Which part each texel belongs to, by name.
_i = np.clip(np.searchsorted(KEYS, prt), 1, len(KEYS) - 1)
NAME_ID = np.where(np.abs(prt - KEYS[_i - 1]) <= np.abs(prt - KEYS[_i]), _i - 1, _i)
del _i


def named(*names):
    ids = [i for i, n in enumerate(NAMES) if n in names]
    return np.isin(NAME_ID, ids)


# Distance to the nearest sharp convex edge, from the points the build recorded along them.
edge_pts = np.load(os.path.join(WORK, "shed_edges.npy"))
dist_edge, _ = cKDTree(edge_pts).query(P, k=1, workers=-1)
edge = np.clip(np.maximum(EDGEC, (1 - smooth(0.03, 0.22, dist_edge)) * 0.9), 0, 1)

big = noise(P, 0.11, 1, 3)
mid = noise(P, 0.55, 2, 4)
fine = noise(P, 2.7, 3, 3)
micro = noise(P, 11.0, 4, 2)
age = noise(P, 0.045, 20, 3)
# Rain and rust run downhill: noise squashed along z, long up the wall and narrow across it.
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

low = np.clip(1 - Z / 26.0, 0, 1) ** 1.4    # the deck's splash zone


def put(mask, c, r, m, h):
    color[mask] = c[mask] if c.ndim == 2 and c.shape[0] == N else c
    rough[mask] = r[mask]
    metal[mask] = m[mask]
    height[mask] = h[mask]


# ---------------------------------------------------------------- graphite paint over galvanised sheet: the walls and the eave
bd = fin == BODY
paint = mixc(C((44, 48, 51)), C((70, 75, 78)), smooth(0.2, 0.85, mid * 0.55 + big * 0.45))
paint = mixc(paint, C((112, 116, 118)), smooth(0.45, 0.95, up * 0.8 + (big - 0.5) * 0.4) * 0.34)   # chalked where it looks up
paint = paint * (1 + upright[:, None] * (streak[:, None] - 0.5) * 0.5)
# Dark grime streaks under the eave, running most of the way down.
grime = smooth(0.52, 0.72, streak2 + (1 - AO) * 0.1) * upright * smooth(36.0, 108.0, Z)
paint = paint * (1 - 0.3 * grime)[:, None]
chip = edge_patchy * 1.15 + (mid - 0.5) * 0.5 + (big - 0.5) * 0.4 + (fine - 0.5) * 0.8 + (micro - 0.5) * 0.3 + 0.15 + low * 0.18 - CONC * 0.1
b_bare = smooth(0.70, 0.722, chip)
b_thin = smooth(0.645, 0.67, chip)
zinc_under = mixc(C((150, 154, 152)), C((118, 122, 120)), smooth(0.3, 0.8, age)) * (0.72 + 0.4 * fine[:, None])
paint = mixc(paint, paint * 0.78, b_thin * (1 - b_bare))
paint = mixc(paint, zinc_under, b_bare)
# Rust: through the chips, and blooming at the foot where the sheet stands in splash.
b_rust = np.maximum(b_bare * smooth(0.40, 0.70, rust_tone + crevice * 0.4 + low * 0.35),
                    low * smooth(0.60, 0.78, noise(P, 1.3, 31, 3) + low * 0.35 + crevice * 0.2))
paint = mixc(paint, rust_c, b_rust * 0.88)
paint = mixc(paint, steel * 0.84, SCR * 0.5 * (1 - b_bare))
# Sheet laps: where the back and side walls' sheets overlap, a dark seam with a row of rivets down it.
lap = np.zeros(N, np.float32)
rivet = np.zeros(N, np.float32)
for name, along, at_ in (("back wall", Y, (-18.5, 18.5)), ("east wall", X, (0.0,)), ("west wall", X, (0.0,))):
    m_ = named(name)
    for s0 in at_:
        d_ = np.abs(along - s0)
        lap = np.maximum(lap, m_ * (1 - smooth(0.12, 0.45, d_)))
        ph = np.abs(np.mod(Z, 5.0) - 2.5)
        rivet = np.maximum(rivet, m_ * (1 - smooth(0.16, 0.26, np.hypot(d_, ph))))
paint = paint * (1 - 0.55 * lap - 0.0)[:, None]
paint = mixc(paint, C((130, 134, 134)), rivet * 0.7)
b_rough = 0.52 + 0.18 * mid + 0.1 * fine + 0.12 * smooth(0.45, 0.95, up)
b_rough = b_rough * (1 - b_thin * 0.35) + (0.42 + 0.3 * fine) * b_bare
b_rough = b_rough * (1 - b_rust) + 0.86 * b_rust
b_metal = np.maximum(b_bare * (1 - b_rust), SCR * 0.5)
b_height = 0.004 * (micro - 0.5) + 0.002 * (fine - 0.5) - b_bare * 0.01 + b_rust * 0.008 * (rust_tone - 0.2) - lap * 0.03 + rivet * 0.05
put(bd, paint, b_rough, b_metal, b_height)

# ---------------------------------------------------------------- black primer: the base channel, the corner posts, the posts' hazard stripes
dk = fin == DARK
d_paint = mixc(C((24, 25, 27)), C((46, 48, 50)), smooth(0.2, 0.85, mid * 0.6 + big * 0.4))
d_paint = mixc(d_paint, C((70, 72, 72)), smooth(0.5, 0.95, up * 0.8 + (big - 0.5) * 0.3) * 0.3)
d_chip = edge_patchy * 1.3 + (mid - 0.5) * 0.45 + (fine - 0.5) * 0.8 + (micro - 0.5) * 0.3 + 0.2 + low * 0.28
d_bare = smooth(0.68, 0.71, d_chip)
d_rust = np.maximum(d_bare * smooth(0.36, 0.66, rust_tone + crevice * 0.4 + low * 0.4), low * smooth(0.55, 0.74, noise(P, 1.9, 32, 3) + low * 0.4))
d_paint = mixc(d_paint, C((92, 94, 92)) * (0.7 + 0.4 * fine[:, None]), d_bare)
d_paint = mixc(d_paint, rust_c, d_rust * 0.9)
# Hazard stripes on the front face of the front posts, up to knee-and-bumper height: diagonal, 2 in a stripe.
post = named("corner post") & (Nn[:, 0] < -0.7) & (X < 0) & (Z < 40.0)
phase = np.mod((Z + 1.1 * np.abs(Y)) / 4.0, 1.0)
stripe_y = smooth(0.0, 0.03, phase) * (1 - smooth(0.5, 0.53, phase))
haz = mixc(np.broadcast_to(C((22, 22, 22)), (N, 3)), C((226, 168, 18)) * (0.8 + 0.3 * mid[:, None]), stripe_y)
haz = haz * (1 - 0.4 * low)[:, None]
haz = mixc(haz, C((60, 56, 50)), smooth(0.5, 0.8, fine + low * 0.3) * 0.45)
haz = mixc(haz, zinc_under, d_bare)
haz = mixc(haz, rust_c, d_rust * 0.9)
d_paint = np.where(post[:, None], haz, d_paint)
d_rough = 0.56 + 0.2 * mid + 0.1 * fine
d_rough = d_rough * (1 - d_bare) + (0.42 + 0.3 * fine) * d_bare
d_rough = d_rough * (1 - d_rust) + 0.86 * d_rust
d_metal = np.maximum(d_bare * (1 - d_rust), SCR * 0.4)
d_height = 0.004 * (micro - 0.5) - d_bare * 0.012 + d_rust * 0.008 * (rust_tone - 0.2) + post * stripe_y * 0.002
put(dk, d_paint, d_rough, d_metal, d_height)

# ---------------------------------------------------------------- pale powder coat: the cabinet, louvre frame, hoods, gland box, A/C casing
lt = fin == LIGHT
l_paint = mixc(C((176, 180, 180)), C((204, 207, 205)), smooth(0.2, 0.85, mid * 0.55 + big * 0.45))
l_paint = mixc(l_paint, C((196, 180, 130)), smooth(0.55, 0.9, age + 0.15 * up) * 0.28)           # yellowed in the sun
l_paint = l_paint * (1 + upright[:, None] * (streak2[:, None] - 0.5) * 0.7)
l_drip = smooth(0.5, 0.72, streak + (1 - AO) * 0.18) * upright
l_paint = mixc(l_paint, C((88, 82, 70)), l_drip * 0.34)
l_wear = smooth(0.58, 0.72, edge_patchy * 1.2 + (fine - 0.5) * 0.9 + (micro - 0.5) * 0.3 + low * 0.1)
l_paint = mixc(l_paint, C((150, 154, 152)) * (0.7 + 0.4 * fine[:, None]), l_wear)
l_paint = mixc(l_paint, rust_c, smooth(0.62, 0.8, rust_tone + crevice * 0.3 + l_wear * 0.2 + low * 0.3) * l_wear * 0.8)
l_paint = mixc(l_paint, steel * 0.7, SCR * 0.4)
l_rough = 0.46 + 0.18 * mid + 0.1 * fine
l_rough = l_rough * (1 - l_wear) + (0.4 + 0.25 * fine) * l_wear
l_metal = np.maximum(l_wear * 0.8, SCR * 0.4)
l_height = 0.003 * (micro - 0.5) - l_wear * 0.006 - SCR * 0.002
put(lt, l_paint, l_rough, l_metal, l_height)

# ---------------------------------------------------------------- the beacon's red lens: moulded plastic, dusty and a little crazed
rd = fin == RED
r_paint = mixc(C((150, 14, 12)), C((196, 30, 22)), smooth(0.3, 0.8, mid))
r_paint = mixc(r_paint, C((112, 78, 62)), smooth(0.5, 0.8, up * 0.6 + age * 0.4) * 0.35)
put(rd, r_paint, 0.2 + 0.28 * smooth(0.5, 0.8, up * 0.6 + age * 0.4) + 0.08 * fine, np.zeros(N, np.float32), 0.002 * (micro - 0.5))

# ---------------------------------------------------------------- hot-dip galvanised steel: the roof, blades, rails, conduit, brackets, mast
galv = fin == GALV
ident, ident_b, border = voronoi(P[galv], 0.40, seed=3)


def spread(v, default=0.0):
    out = np.full(N, default, np.float32)
    out[galv] = v
    return out


ident, ident_b, border = spread(ident, 0.5), spread(ident_b, 0.5), spread(border, 1.0)
lum = 0.86 + 0.18 * ident + 0.30 * (big - 0.5) + 0.12 * (fine - 0.5)
dull = smooth(0.35, 0.78, age + (mid - 0.5) * 0.3 + 0.2 * up)                      # old zinc goes dark and flat, most on the roof
g_color = mixc(C((158, 162, 160)), C((112, 116, 114)), dull) * lum[:, None]
g_color = g_color * (1 - 0.1 * smooth(0.10, 0.0, border))[:, None]        # crystal boundaries, faint
g_color = g_color * (0.93 + 0.14 * prt)[:, None]
g_white = smooth(0.58, 0.78, streak + crevice * 0.22 + (age - 0.5) * 0.2 + 0.1 * up)  # white rust under anything that holds water
g_color = mixc(g_color, C((200, 198, 186)) * 0.78, g_white * 0.55)
g_rust = smooth(0.77, 0.93, noise(P, 1.5, 22, 3) + crevice * 0.34 + low * 0.26) * (1 - g_white * 0.5)
roof_wet = smooth(106.0, 110.0, Z) * up                                     # standing water in the roof's valleys
g_color = mixc(g_color, C((70, 62, 50)), smooth(0.5, 0.75, streak2 + crevice * 0.2) * roof_wet * 0.45)
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

# ---------------------------------------------------------------- black oxide: hinges, handles, glands, the A/C fan and grilles
ox = fin == OXIDE
o_wear = smooth(0.44, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
o_color = np.broadcast_to(C((42, 42, 44)), (N, 3)) * (0.75 + 0.5 * mid[:, None])
o_color = mixc(o_color, steel * 0.8, o_wear * 0.9)
o_rust = smooth(0.8, 0.9, noise(P, 3.6, 11, 3) + crevice * 0.06 + low * 0.1)
o_color = mixc(o_color, rust_c, o_rust * 0.7)
put(ox, o_color, 0.4 + 0.2 * fine - 0.1 * o_wear + 0.35 * o_rust, (1 - o_rust) * 0.92, 0.0016 * (micro - 0.5) + o_rust * 0.006 * (rust_tone - 0.3) - o_wear * 0.002)

# ---------------------------------------------------------------- plated fasteners
zn = fin == ZINC
yellow_pass = np.mod(prt * 7.0, 1.0) > 0.68
z_base = np.where(yellow_pass[:, None], C((176, 158, 112)), C((186, 188, 186)))
z_white = smooth(0.48, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.5 + low * 0.2)
z_color = z_base * (0.52 + 0.3 * mid[:, None])
z_color = mixc(z_color, rust_mid, z_white * 0.55)
z_color = mixc(z_color, steel, smooth(0.5, 0.8, edge) * 0.5)
put(zn, z_color, 0.3 + 0.2 * fine + 0.4 * z_white, 1 - z_white * 0.75, 0.0012 * (micro - 0.5))

# ---------------------------------------------------------------- brass lock barrel
br = fin == BRASS
b_tarnish = smooth(0.32, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.7 - edge * 0.45)
bc = mixc(C((214, 170, 92)), C((92, 66, 34)), b_tarnish)
b_green = smooth(0.66, 0.84, noise(P, 2.1, 12, 3) + crevice * 0.26)
bc = mixc(bc, C((86, 112, 86)), b_green * 0.55)
put(br, bc, 0.24 + 0.34 * b_tarnish + 0.1 * fine + 0.2 * b_green, 1 - b_green * 0.7, 0.0012 * (micro - 0.5))

# ---------------------------------------------------------------- rubber: the pipe boots' collars
rb = fin == RUBBER
cracks = smooth(0.62, 0.7, noise(P, 7.0, 23, 3))
r_color = C((30, 30, 30)) * (0.75 + 0.5 * fine[:, None])
r_color = mixc(r_color, C((62, 60, 56)), smooth(0.4, 0.8, upright * 0.7 + (big - 0.5) * 0.5) * 0.5)
put(rb, r_color, 0.74 + 0.14 * fine, np.zeros(N, np.float32), 0.003 * (micro - 0.5) - cracks * 0.003)

# ---------------------------------------------------------------- the three plates, stencilled
pl = fin == PLATE
PLATES = (
    # name, base colour, ink, lines, u axis (world coordinate, origin, size, sign), v origin and height
    ("plate auth", (232, 232, 226), (14, 14, 16), ["AUTHORISED PERSONNEL", "ONLY - A-2 CONTROL SHELTER"], (Y, -32.0, 22.0, -1.0), (74.0, 9.0), (880, 360)),
    ("plate danger", (232, 184, 20), (16, 16, 14), ["DANGER", "415 V"], (Y, -38.0, 9.0, -1.0), (44.5, 9.0), (360, 360)),
    ("plate side", (172, 174, 170), (20, 20, 22), ["CONTROL SHELTER", "UNIT A-2", "2600 KG"], (X, -31.0, 12.0, 1.0), (36.0, 7.0), (600, 350)),
)
p_color = np.broadcast_to(C((178, 178, 172)), (N, 3)).copy()
p_stamp = np.zeros(N, np.float32)
p_rough = np.full(N, 0.45, np.float32)
for name, base, ink, lines, (axis_val, u0, usize, usign), (v0, vsize), img_size in PLATES:
    m_ = named(name)
    if not m_.any():
        continue
    art = stencil_image(lines, img_size)
    uu = np.clip((axis_val - u0) * usign / usize, -1, 2)
    vv = np.clip((Z - v0) / vsize, -1, 2)
    inside = np.clip(np.minimum(np.minimum(uu, 1 - uu) * usize, np.minimum(vv, 1 - vv) * vsize), 0, 9)
    border = (1 - smooth(0.34, 0.42, inside)) * smooth(0.18, 0.26, inside)           # a thin printed border inset from the edge
    ink_mask = np.maximum(sample_image(art, uu, vv), border)
    colour = mixc(np.broadcast_to(C(base), (N, 3)), np.broadcast_to(C(ink), (N, 3)), np.clip(ink_mask, 0, 1) * 0.92)
    colour = colour * (0.82 + 0.3 * mid[:, None])
    colour = mixc(colour, colour * 0.45, smooth(0.45, 0.8, crevice + (mid - 0.5)) * 0.8)
    colour = mixc(colour, C((96, 84, 66)), smooth(0.5, 0.78, streak2 + low * 0.2) * upright * 0.3)
    p_color = np.where(m_[:, None], colour, p_color)
    p_stamp = np.where(m_, ink_mask, p_stamp)
    p_rough = np.where(m_, 0.42 + 0.22 * fine + ink_mask * 0.25, p_rough)
put(pl, p_color, p_rough, np.where(p_stamp > 0.5, 0.0, 0.7) * np.ones(N, np.float32), p_stamp * 0.01 + 0.001 * (micro - 0.5))

# ---------------------------------------------------------------- stray colours: anything left unpainted shows as magenta
left = ~(bd | dk | lt | rd | galv | ox | zn | br | rb | pl)
print("unpainted texels", int(left.sum()), "finishes", sorted(set(np.unique(fin[left]).tolist())), flush=True)
color[left] = C((255, 0, 255))
rough[left] = 0.5

# ---------------------------------------------------------------- dirt over everything
settled = smooth(0.38, 0.88, up * 0.82 + (big - 0.5) * 0.34 + crevice * 0.2)
splash = low * smooth(0.46, 0.64, noise(P * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 13, 4) + low * 0.16)
speckle = low * smooth(0.64, 0.72, noise(P, 7.5, 14, 2))
dirt = np.clip(settled * 0.3 + splash * 0.75 + speckle * 0.55, 0, 0.9)
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
save_rgb(os.path.join(OUT, "shed_body_color.png"), color_i)
save_gray(os.path.join(OUT, "shed_body_rough.png"), rough_i, 1024)
save_gray(os.path.join(OUT, "shed_body_metal.png"), metal_i, 1024)
save_gray(os.path.join(OUT, "shed_body_ao.png"), np.clip(ao * 1.03, 0, 1), 1024)
save_normal(os.path.join(OUT, "shed_body_normal.png"), normal)
print("painted", flush=True)
