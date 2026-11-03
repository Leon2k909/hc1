"""Riverside's propane cylinders v2: the 100 lb cylinders on the pad and the porch, and the 20 lb pair on the camper's tongue.
Builds the meshes, paints the maps and writes the models with numpy and PIL, as Sources/Riverdale/hose-reel-v2/hose_reel.py does.

python propane.py <project root>

Engine X and Y are across the cylinder, Z up, the origin at the middle of its foot. The valve's outlet points along +X, through a handhold.
A steel shell in worn off-white paint on a foot ring, a collar with two handholds round a brass valve and its handwheel, the relief valve's cap, a weld seam,
a warning label and a red stencil. Rust bleeds from under the collar and the seam, and the foot and the bottom are muddy. Everything printed is made up.
The paint's mottle and the rust's colour come from forestbase/scans/metal_plate_02, with its plate seams filtered out.
"""
import ctypes
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except AttributeError:
    pass

ROOT = sys.argv[1]
MODEL = "models/props/riverside/propane_v2"
MATS = "materials/riverside/propane_v2"
OUT = os.path.join(ROOT, "Assets", *MODEL.split("/"))
MAT_OUT = os.path.join(ROOT, "Assets", *MATS.split("/"))
SCAN = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans")
for folder in (OUT, MAT_OUT):
    os.makedirs(folder, exist_ok=True)
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT = r"C:\Windows\Fonts\arial.ttf"
STENCIL = r"C:\Windows\Fonts\impact.ttf" if os.path.exists(r"C:\Windows\Fonts\impact.ttf") else FONT_BOLD
PAINT = np.array((0.80, 0.79, 0.74), np.float32)

# Sizes in inches. Shell: radius, where the bottom head meets the straight side, where the side meets the top head, the top of the head. Foot ring: outer
# radius, height. Collar: outer radius, bottom (inside the head), top, and its handholds as (half width in degrees, bottom, top). Valve: the scale of its parts.
SPECS = {
    "propane_100": dict(R=7.25, side0=6.0, side1=37.5, top=43.1, foot=(6.45, 3.7), collar=(4.6, 41.9, 48.0), holes=(24.0, 45.5, 46.9), valve=1.0,
                        ppi=29, atlas=2048, seam=22.0, label=(14.0, 24.5), stencil=31.0, lods=(30.0, 90.0)),
    "propane_20": dict(R=6.1, side0=4.2, side1=13.6, top=16.3, foot=(5.45, 2.6), collar=(4.0, 15.6, 19.6), holes=(36.0, 17.4, 19.0), valve=0.9,
                       ppi=24, atlas=1024, seam=None, label=(5.6, 12.4), stencil=None, lods=(24.0, 70.0)),
}
SWATCH = {"brass": (0.70, 0.52, 0.24), "wheel": (0.42, 0.06, 0.05), "steel": (0.40, 0.40, 0.41), "yellow": (0.86, 0.68, 0.12), "black": (0.04, 0.04, 0.04), "rust": (0.30, 0.15, 0.08)}


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def blobs(shape, sigma, seed, aspect=(1.0, 1.0)):
    """Smooth noise, about unit spread; aspect stretches it (rows, cols)."""
    r = np.random.default_rng(seed).normal(size=(max(4, shape[0] // 4), max(4, shape[1] // 4)))
    r = ndi.gaussian_filter(r, (sigma / 4 * aspect[0], sigma / 4 * aspect[1]), mode="wrap")
    r = ndi.zoom(r, (shape[0] / r.shape[0], shape[1] / r.shape[1]), order=1)[: shape[0], : shape[1]]
    return r / (r.std() * 2.5 + 1e-6)


def to_normal(height, ppi):
    dr, dc = np.gradient(height)
    n = np.stack((-dc * ppi, dr * ppi, np.ones_like(height)), -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


_CLEAN = {}


def scan(name, shape, ppi):
    """A forestbase scan at about true scale (metal_plate_02 covers about 40 in), with its plate seams closed and opened away and only what's smaller than a plate kept."""
    if name not in _CLEAN:
        g = np.asarray(Image.open(os.path.join(SCAN, name)).convert("L"), np.float32) / 255
        for size in ((1, 17), (17, 1)):
            g = ndi.grey_closing(g, size=size)
        for size in ((1, 11), (11, 1)):
            g = ndi.grey_opening(g, size=size)
        g = ndi.gaussian_filter(g, 2.5) - ndi.gaussian_filter(g, 40)
        _CLEAN[name] = Image.fromarray(np.clip(g / (g.std() * 6) * 255 + 128, 0, 255).astype(np.uint8))
    px = max(8, round(40 * ppi))
    tile = (np.asarray(_CLEAN[name].resize((px, px), Image.LANCZOS), np.float32) - 128) / 128
    return np.tile(tile, (shape[0] // px + 1, shape[1] // px + 1))[: shape[0], : shape[1]]


# ---------------------------------------------------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------------------------------------------------


class Mesh:
    def __init__(self):
        self.p, self.t, self.n = [], [], []

    def tri(self, p, t, n):
        self.p.append(np.asarray(p, float))
        self.t.append(np.asarray(t, float))
        self.n.append(np.broadcast_to(np.asarray(n, float), (3, 3)).copy() if np.ndim(n) == 1 else np.asarray(n, float))

    def quad(self, a, b, c, d, uv, n):
        n = np.asarray(n, float)
        if n.ndim == 1:
            n = np.array([n, n, n, n])
        self.tri((a, b, c), (uv[0], uv[1], uv[2]), (n[0], n[1], n[2]))
        self.tri((a, c, d), (uv[0], uv[2], uv[3]), (n[0], n[2], n[3]))

    def lathe(self, profile, rect, ppi, seg, side=1, sharp=40.0, centre=(0.0, 0.0, 0.0), axis=None, start=0.0):
        """Turns a (r, z) profile round z (or round `axis` through `centre`). UVs: around the rect's width, down it by arc length from the profile's start.
        side +1 makes normals face right of the profile's travel in (r, z): outward for a loop run inner top, inner bottom, outer bottom, outer top, or for one run out along a bottom and up a side."""
        P = np.asarray(profile, float)
        seglen = np.linalg.norm(np.diff(P, axis=0), axis=1)
        s = np.concatenate(([0.0], np.cumsum(seglen)))
        tang = np.diff(P, axis=0) / np.maximum(seglen, 1e-9)[:, None]
        segn = np.stack((tang[:, 1], -tang[:, 0]), 1) * side
        x0, y0, w = rect
        centre = np.asarray(centre, float)
        if axis is None:
            e1, e2, ez = np.array((1.0, 0, 0)), np.array((0, 1.0, 0)), np.array((0, 0, 1.0))
        else:
            ez = np.asarray(axis, float) / np.linalg.norm(axis)
            ref = np.array((0, 0, 1.0)) if abs(ez[2]) < 0.9 else np.array((1.0, 0, 0))
            e1 = np.cross(ref, ez)
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(ez, e1)
        ang = start + np.linspace(0, 2 * np.pi, seg + 1)
        rad = [e1 * np.cos(a) + e2 * np.sin(a) for a in ang]
        for j in range(len(P) - 1):
            if seglen[j] < 1e-9:
                continue
            ends = []
            for q, other in ((j, j - 1), (j + 1, j + 1)):
                nn = segn[j]
                if 0 <= other < len(segn) and seglen[other] > 1e-9:
                    cosang = float(np.dot(segn[j], segn[other]))
                    if cosang > np.cos(np.radians(sharp)):
                        nn = segn[j] + segn[other]
                        nn = nn / np.linalg.norm(nn)
                ends.append(nn)
            for k in range(seg):
                pts, nors, uvs = [], [], []
                for q, nn in ((j, ends[0]), (j + 1, ends[1])):
                    for kk in (k, k + 1):
                        pts.append(centre + rad[kk] * P[q, 0] + ez * P[q, 1])
                        nors.append(rad[kk] * nn[0] + ez * nn[1])
                        uvs.append((x0 + w * kk / seg, y0 + s[q] * ppi))
                a_, b_, c_, d_ = pts[0], pts[1], pts[3], pts[2]
                na, nb, nc, nd = nors[0], nors[1], nors[3], nors[2]
                ta, tb, tc, td = uvs[0], uvs[1], uvs[3], uvs[2]
                if np.linalg.norm(np.cross(b_ - a_, c_ - a_)) > 1e-10:
                    self.tri((a_, b_, c_), (ta, tb, tc), (na, nb, nc))
                if np.linalg.norm(np.cross(c_ - a_, d_ - a_)) > 1e-10:
                    self.tri((a_, c_, d_), (ta, tc, td), (na, nc, nd))

    def torus(self, centre, axis, radius, tube, uv_box, seg=24, sides=6):
        axis = np.asarray(axis, float) / np.linalg.norm(axis)
        e1 = np.cross(axis, (0, 0, 1)) if abs(axis[2]) < 0.9 else np.array((1.0, 0, 0))
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        x, y, w, h = uv_box
        grid = []
        for i in range(seg + 1):
            a = 2 * np.pi * i / seg
            radial = e1 * np.cos(a) + e2 * np.sin(a)
            row = []
            for j in range(sides + 1):
                b = 2 * np.pi * j / sides
                n = radial * np.cos(b) + axis * np.sin(b)
                row.append((np.asarray(centre) + radial * radius + n * tube, n, (x + w * i / seg, y + h * j / sides)))
            grid.append(row)
        for i in range(seg):
            for j in range(sides):
                c = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]]
                self.quad(*[q[0] for q in c], [q[2] for q in c], [q[1] for q in c])

    def rod(self, a, b, r, uv, sides=6):
        a, b = np.asarray(a, float), np.asarray(b, float)
        axis = b - a
        L = np.linalg.norm(axis)
        self.lathe([(0.0, 0.0), (r, 0.0), (r, L), (0.0, L)], (uv[0], uv[1], 0.0), 0.0, sides, centre=a, axis=axis / L)

    def band(self, r_out, r_in, z0, z1, holes, rect, ppi, seg, lip_uv):
        """The collar: a ring of plate from z0 to z1 with rectangular handholds, holes being (centre angle, half width, bottom, top) in degrees and inches.
        UVs: the rect's rows run down the outside, then down the inside."""
        x0, y0, w = rect
        H = z1 - z0
        angs = set(np.linspace(0, 360, seg + 1)[:-1].round(6))
        zs = {z0, z1}
        for c, hw, lo, hi in holes:
            angs |= {round((c - hw) % 360, 6), round((c + hw) % 360, 6)}
            zs |= {lo, hi}
        angs = sorted(angs) + [360.0]
        zs = sorted(zs)
        zs = sorted(set(np.concatenate([np.linspace(zs[k], zs[k + 1], max(2, int(np.ceil((zs[k + 1] - zs[k]) / 1.0)) + 1)) for k in range(len(zs) - 1)]).round(6)))

        def inside(a, z):
            for c, hw, lo, hi in holes:
                d = (a - c + 180) % 360 - 180
                if abs(d) < hw and lo < z < hi:
                    return True
            return False

        def pt(a, z, r):
            t = np.radians(a)
            return np.array((np.cos(t) * r, np.sin(t) * r, z))

        def rdir(a):
            t = np.radians(a)
            return np.array((np.cos(t), np.sin(t), 0.0))

        def uv(a, z, inner):
            return (x0 + w * a / 360.0, y0 + ((H + 0.4 + (z1 - z)) if inner else (z1 - z)) * ppi)

        open_ = [[inside((angs[i] + angs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2) for j in range(len(zs) - 1)] for i in range(len(angs) - 1)]
        for i in range(len(angs) - 1):
            a0, a1 = angs[i], angs[i + 1]
            for j in range(len(zs) - 1):
                if open_[i][j]:
                    continue
                za, zb = zs[j], zs[j + 1]
                self.quad(pt(a0, za, r_out), pt(a1, za, r_out), pt(a1, zb, r_out), pt(a0, zb, r_out), [uv(a0, za, 0), uv(a1, za, 0), uv(a1, zb, 0), uv(a0, zb, 0)],
                          [rdir(a0), rdir(a1), rdir(a1), rdir(a0)])
                self.quad(pt(a0, za, r_in), pt(a0, zb, r_in), pt(a1, zb, r_in), pt(a1, za, r_in), [uv(a0, za, 1), uv(a0, zb, 1), uv(a1, zb, 1), uv(a1, za, 1)],
                          [-rdir(a0), -rdir(a0), -rdir(a1), -rdir(a1)])
                # The cut edges round a handhold.
                for di, dj, edge in ((-1, 0, "a0"), (1, 0, "a1"), (0, -1, "z0"), (0, 1, "z1")):
                    ii, jj = i + di, j + dj
                    if not (0 <= ii < len(angs) - 1 and 0 <= jj < len(zs) - 1 and open_[ii][jj]):
                        continue
                    t_ = lip_uv
                    if edge in ("a0", "a1"):
                        a = a0 if edge == "a0" else a1
                        n = np.cross((0, 0, 1.0), rdir(a)) * (-1 if edge == "a0" else 1)
                        self.quad(pt(a, za, r_in), pt(a, za, r_out), pt(a, zb, r_out), pt(a, zb, r_in), [t_] * 4, n)
                    else:
                        z = za if edge == "z0" else zb
                        n = np.array((0, 0, -1.0 if edge == "z0" else 1.0))
                        self.quad(pt(a0, z, r_in), pt(a1, z, r_in), pt(a1, z, r_out), pt(a0, z, r_out), [t_] * 4, n)


def fix_winding(p, t, n):
    face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    flip = (face * n.mean(1)).sum(-1) < 0
    p[flip], t[flip], n[flip] = p[flip][:, [0, 2, 1]], t[flip][:, [0, 2, 1]], n[flip][:, [0, 2, 1]]


def write_obj(path, mesh, atlas, mtl):
    p, t, n = np.array(mesh.p), np.array(mesh.t), np.array(mesh.n)
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
    fix_winding(p, t, n)
    uv = np.stack((t[..., 0] / atlas, 1 - t[..., 1] / atlas), -1)
    po, no = p[..., [1, 2, 0]], n[..., [1, 2, 0]]  # Engine X, Y, Z become OBJ Z, X, Y.
    tables, lines, body = ({}, {}, {}), ([], [], []), []

    def index(k, prefix, values):
        key = tuple(np.round(values, 5))
        got = tables[k].get(key)
        if got is None:
            got = len(tables[k]) + 1
            tables[k][key] = got
            lines[k].append(prefix + " ".join(f"{v_:.5f}" for v_ in key) + "\n")
        return got

    for k in range(len(po)):
        body.append("f " + " ".join("%d/%d/%d" % (index(0, "v ", po[k, c]), index(1, "vt ", uv[k, c]), index(2, "vn ", no[k, c])) for c in range(3)) + "\n")
    with open(path, "w", newline="\n") as h:
        h.write(f"# Generated by Sources/Riverside/propane-v2/propane.py\nmtllib {mtl}.mtl\n")
        for block in lines:
            h.writelines(block)
        h.write(f"usemtl {mtl}\n")
        h.writelines(body)
    print(os.path.basename(path), "triangles", len(po), "bounds", p.reshape(-1, 3).min(0).round(2), p.reshape(-1, 3).max(0).round(2), flush=True)
    return len(po)


# ---------------------------------------------------------------------------------------------------------------------
# One cylinder: its profiles, atlas, paint and mesh
# ---------------------------------------------------------------------------------------------------------------------


def shell_profile(S):
    """The shell, top pole down to the bottom head's middle: an elliptical 2:1 head each end, a straight side between."""
    R, s0, s1, top = S["R"], S["side0"], S["side1"], S["top"]
    pts = []
    for a in np.linspace(0, np.pi / 2, 14):
        pts.append((R * np.sin(a), s1 + (top - s1) * np.cos(a)))
    pts.append((R, (s0 + s1) / 2))
    bottom = S["side0"] - R * 0.45
    for a in np.linspace(np.pi / 2, np.pi, 12)[0:]:
        pts.append((R * np.sin(a), s0 + (s0 - bottom) * np.cos(a)))
    return pts


def head_z(S, r, upper):
    """Where the top (or bottom) head is at radius r."""
    R, s0, s1, top = S["R"], S["side0"], S["side1"], S["top"]
    c = np.sqrt(max(0.0, 1 - (r / R) ** 2))
    return s1 + (top - s1) * c if upper else s0 - R * 0.45 * c


def foot_profile(S):
    """The foot ring, welded up onto the bottom head: its top a little above where the head meets its inner face."""
    r = S["foot"][0]
    t = 0.16
    h = head_z(S, r - t, False) + 0.15
    return [(r - t, h), (r - t, 0.35), (r - t + 0.05, 0.0), (r + 0.12, 0.0), (r + 0.12, 0.42), (r, 0.55), (r, h), (r - t, h)]


def collar(S):
    """The collar's radius, bottom and top: its bottom sunk into the top head a little below where the head meets its outer face."""
    rc, _, z1c = S["collar"]
    return rc, head_z(S, rc, True) - 0.15, z1c


def arc_length(profile):
    P = np.asarray(profile, float)
    return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())


def plan(S):
    """The atlas: rects by name, shelves by height."""
    ppi = S["ppi"]
    R = S["R"]
    rc, z0c, z1c = collar(S)
    rf = S["foot"][0]
    H = z1c - z0c
    rects = {"shell": (round(2 * np.pi * R * ppi), round(arc_length(shell_profile(S)) * ppi) + 2),
             "collar": (round(2 * np.pi * rc * ppi), round((2 * H + 0.4) * ppi) + 2),
             "foot": (round(2 * np.pi * rf * ppi), round(arc_length(foot_profile(S)) * ppi) + 2),
             "swatch": (256, 32)}
    place, x, y, shelf, gutter = {}, 0, 0, 0, 6
    for name, (w, h) in sorted(rects.items(), key=lambda kv: -kv[1][1]):
        if x + w > S["atlas"]:
            x, y, shelf = 0, y + shelf + gutter, 0
        place[name] = (x, y, w, h)
        x += w + gutter
        shelf = max(shelf, h)
    assert y + shelf <= S["atlas"], ("atlas full", y + shelf)
    return place


def swatch_uv(place, name):
    x, y, w, h = place["swatch"]
    k = list(SWATCH).index(name)
    return (x + (k + 0.5) * w / len(SWATCH), y + h / 2)


def rust_colour(shape, ppi, seed):
    m = scan("metal_plate_02_diff.jpg", shape, ppi)
    base = np.array(SWATCH["rust"], np.float32)
    dark = np.array((0.14, 0.07, 0.04), np.float32)
    t = np.clip(0.5 + 0.5 * m + 0.25 * blobs(shape, 18, seed), 0, 1)[..., None]
    return base * (1 - t) + dark * t * 0.9 + np.array((0.08, 0.03, 0.0), np.float32) * (1 - t)


def streaks(shape, ppi, sources, seed, length, per_inch=0.3):
    """Rust run down from the rows in `sources` (a per-column start row array): a few separate runs, each its own width, strength and length in inches."""
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    rows = np.arange(h, dtype=np.float32)
    for _ in range(max(1, int(w / ppi * per_inch))):
        c = rng.uniform(0, w)
        width = rng.uniform(0.08, 0.45) * ppi
        strength = rng.uniform(0.35, 1.0)
        run = length * rng.uniform(0.25, 1.1) * ppi
        c0, c1 = int(c - 4 * width) - 2, int(c + 4 * width) + 3
        cols = np.arange(c0, c1)
        start = sources[np.clip(cols, 0, w - 1)].mean() + rng.uniform(-0.2, 0.4) * ppi
        drift = np.cumsum(rng.normal(0, 0.02, h)) * ppi * 0.15  # It wanders a little as it runs.
        below = rows - start
        fade = np.where(below > 0, np.exp(-below / run) * smooth(0, 0.4 * ppi, below), 0)
        across = np.exp(-((cols[None, :] - c - drift[:, None]) / width) ** 2)
        out[:, np.clip(cols, 0, w - 1)] = np.maximum(out[:, np.clip(cols, 0, w - 1)], strength * fade[:, None] * across)
    return np.clip(out * (0.7 + 0.5 * blobs(shape, 0.4 * ppi, seed + 1, aspect=(5.0, 0.5))), 0, 1)


def paint_cylinder(S, place):
    A, ppi = S["atlas"], S["ppi"]
    COLOUR = np.zeros((A, A, 3), np.float32)
    HEIGHT = np.zeros((A, A), np.float32)
    ROUGH = np.full((A, A), 0.6, np.float32)
    METAL = np.zeros((A, A), np.float32)
    AO = np.ones((A, A), np.float32)
    COVER = np.zeros((A, A), bool)
    NORMAL_EXTRA = {}

    def put(name, colour, height, rough, metal, ao):
        x, y, w, h = place[name]
        COLOUR[y:y + h, x:x + w] = colour
        HEIGHT[y:y + h, x:x + w] = height
        ROUGH[y:y + h, x:x + w] = rough
        METAL[y:y + h, x:x + w] = metal
        AO[y:y + h, x:x + w] = ao
        COVER[y:y + h, x:x + w] = True

    def base_paint(shape, seed):
        mottle = scan("metal_plate_02_diff.jpg", shape, ppi)
        colour = PAINT[None, None, :] * (1 + 0.025 * mottle + 0.03 * blobs(shape, 50, seed))[..., None]
        rough = 0.5 + 0.06 * scan("metal_plate_02_rough.jpg", shape, ppi) + 0.05 * blobs(shape, 20, seed + 1)
        height = 0.0012 * blobs(shape, 1.0, seed + 2)
        return colour, rough, height

    # The shell: rows run down from the top pole by arc length.
    x, y, w, h = place["shell"]
    prof = np.asarray(shell_profile(S))
    s_of = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(prof, axis=0), axis=1))))
    rows = np.arange(h, dtype=np.float32) / ppi
    z_row = np.interp(rows, s_of, prof[:, 1])  # Height at each row.
    r_row = np.interp(rows, s_of, prof[:, 0])
    Z = np.broadcast_to(z_row[:, None], (h, w))
    U = np.broadcast_to((np.arange(w, dtype=np.float32) / w)[None, :], (h, w))  # 0..1 round, 0 along +X.
    colour, rough, height = base_paint((h, w), 11)
    # Dents and knocks, and the weld seam's bead.
    height += 0.05 * np.clip(blobs((h, w), 3.5 * ppi, 12), -1, 1) * smooth(S["side0"], S["side0"] + 2, Z) * smooth(S["side1"], S["side1"] - 2, Z)
    if S["seam"]:
        height += 0.03 * np.exp(-((Z - S["seam"]) / 0.09) ** 2)
    # The label: an off-white sheet with print, its corner torn and its edge lifting, on the side the valve's outlet faces away from (90 degrees round).
    img = Image.new("L", (w, h), 0)
    ink = Image.new("L", (w, h), 0)
    red = Image.new("L", (w, h), 0)
    d, di, dr = ImageDraw.Draw(img), ImageDraw.Draw(ink), ImageDraw.Draw(red)
    lab_lo, lab_hi = S["label"]
    lw = min(8.0, 2 * np.pi * S["R"] * 0.24)

    def row_of(z):
        return float(np.interp(-z, -prof[:, 1], s_of) * ppi)

    cx = 0.25 * w
    top_px, bot_px = row_of(lab_hi), row_of(lab_lo)
    box = [cx - lw / 2 * ppi, top_px, cx + lw / 2 * ppi, bot_px]
    d.rectangle(box, fill=255)
    tear = [(box[2], box[3] - 1.6 * ppi), (box[2] - 0.5 * ppi, box[3] - 1.0 * ppi), (box[2] - 0.9 * ppi, box[3] - 0.6 * ppi), (box[2] - 1.4 * ppi, box[3] + 1), (box[2] + 1, box[3] + 1)]
    d.polygon(tear, fill=0)
    big = ImageFont.truetype(FONT_BOLD, max(8, round(0.62 * ppi)))
    mid = ImageFont.truetype(FONT_BOLD, max(7, round(0.36 * ppi)))
    small = ImageFont.truetype(FONT, max(6, round(0.2 * ppi)))
    by = top_px + 0.25 * ppi
    dr.rectangle([box[0] + 0.25 * ppi, by, box[2] - 0.25 * ppi, by + 0.95 * ppi], fill=255)
    di.text((cx, by + 0.48 * ppi), "DANGER", font=big, fill=255, anchor="mm")
    by += 1.25 * ppi
    for line in ("FLAMMABLE GAS", "UNDER PRESSURE"):
        di.text((cx, by), line, font=mid, fill=255, anchor="mm")
        by += 0.46 * ppi
    by += 0.15 * ppi
    words = ("Keep away from heat, sparks and open flame. Store upright outdoors. Close the valve after use and when empty. "
             "Leaking gas smells of rotten eggs: put out flames, leave the area, call the gas supplier. Do not lay on side. "
             "Fill to no more than 80 percent. Inspect for dents, rust and fire damage before refill.").split()
    line, lines = "", []
    for word in words:
        if small.getlength(line + " " + word) > (lw - 0.6) * ppi:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    lines.append(line)
    for line in lines:
        if by > bot_px - 1.6 * ppi:
            break
        di.text((box[0] + 0.3 * ppi, by), line, font=small, fill=230, anchor="lm")
        by += 0.29 * ppi
    # The class 2 diamond at the label's foot.
    dc_, dy_ = cx - lw / 4 * ppi, bot_px - 0.95 * ppi
    q = 0.75 * ppi
    dr.polygon([(dc_, dy_ - q), (dc_ + q, dy_), (dc_, dy_ + q), (dc_ - q, dy_)], fill=255)
    di.polygon([(dc_, dy_ - q * 0.6), (dc_ + q * 0.22, dy_ - q * 0.05), (dc_ + q * 0.1, dy_ + q * 0.2), (dc_ - q * 0.1, dy_ + q * 0.2), (dc_ - q * 0.22, dy_ - q * 0.05)], fill=0)
    di.text((dc_, dy_ + q * 0.55), "2", font=small, fill=255, anchor="mm")
    di.text((cx + lw / 6 * ppi, dy_), "UN1075", font=mid, fill=255, anchor="mm")
    label = ndi.gaussian_filter(np.asarray(img, np.float32) / 255, 0.5)
    inkm = ndi.gaussian_filter(np.asarray(ink, np.float32) / 255, 0.45)
    redm = ndi.gaussian_filter(np.asarray(red, np.float32) / 255, 0.45)
    paper = np.array((0.86, 0.83, 0.72), np.float32) * (1 + 0.05 * blobs((h, w), 8, 13))[..., None]
    paper = paper * (1 - 0.25 * redm[..., None]) + np.array((0.62, 0.08, 0.06), np.float32) * redm[..., None] * 0.25 / 0.25 * 0
    labc = paper * (1 - redm[..., None]) + np.array((0.66, 0.1, 0.07), np.float32) * redm[..., None]
    labc = labc * (1 - inkm[..., None]) + np.where(redm[..., None] > 0.5, np.array((0.93, 0.9, 0.82), np.float32), np.array((0.06, 0.06, 0.06), np.float32)) * inkm[..., None]
    # The label has weathered: faded, dirty along its foot, flaking where the paint under it rusted.
    flake = smooth(0.7, 0.82, blobs((h, w), 0.3 * ppi, 14) * 0.5 + 0.5) * label
    label = label * (1 - flake)
    labc = labc * (1 - 0.25 * smooth(lab_lo + 2.5, lab_lo, Z)[..., None])
    colour = colour * (1 - label[..., None]) + labc * label[..., None]
    rough = rough * (1 - label) + 0.75 * label
    height += 0.006 * label
    # The stencil, opposite the label.
    if S["stencil"]:
        st = Image.new("L", (w, h), 0)
        ImageDraw.Draw(st).text((0.75 * w, row_of(S["stencil"])), "PROPANE", font=ImageFont.truetype(STENCIL, round(2.3 * ppi)), fill=255, anchor="mm")
        ImageDraw.Draw(st).text((0.75 * w, row_of(S["stencil"] - 2.6)), "100 LB", font=ImageFont.truetype(STENCIL, round(1.1 * ppi)), fill=255, anchor="mm")
        stm = ndi.gaussian_filter(np.asarray(st, np.float32) / 255, 0.7) * (0.75 + 0.25 * np.clip(blobs((h, w), 6, 15) + 0.5, 0, 1))
        stm *= 1 - 0.8 * smooth(0.72, 0.9, blobs((h, w), 0.15 * ppi, 16) * 0.5 + 0.5)
        colour = colour * (1 - stm[..., None]) + np.array((0.62, 0.09, 0.07), np.float32) * stm[..., None]
    # Wear: chips and scuffs where it's knocked about (the widest part, low down), dirt and mud splash at the bottom, rust run from under the collar and the seam.
    L = S["side1"] - S["side0"]
    knock = np.clip(blobs((h, w), 0.12 * ppi, 17) * 0.5 + 0.5, 0, 1) * (0.6 + 0.4 * smooth(S["side0"] + 0.3 * L, S["side0"], Z)) * (0.6 + 0.6 * (blobs((h, w), 2 * ppi, 27) > 0.2))
    chips = smooth(0.84, 0.9, knock)
    rustc = rust_colour((h, w), ppi, 18)
    collar_row = row_of(collar(S)[1] + 0.3)
    src = np.full(w, collar_row, np.float32)
    run = streaks((h, w), ppi, src, 19, length=(S["side1"] - S["side0"]) * 0.3, per_inch=0.35)
    if S["seam"]:
        run = np.maximum(run, 0.8 * streaks((h, w), ppi, np.full(w, row_of(S["seam"]), np.float32), 20, length=4.0, per_inch=0.15))
    rr_ = np.arange(h, dtype=np.float32)[:, None]
    under_collar = smooth(row_of(collar(S)[1]) + 1.0 * ppi, row_of(collar(S)[1]), rr_) * (rr_ < row_of(collar(S)[1]) + 1.2 * ppi)
    under_collar = smooth(0.35, 0.6, under_collar * (0.45 + 0.7 * (blobs((h, w), 0.35 * ppi, 21) * 0.5 + 0.5)))
    bloom = smooth(0.5, 0.62, smooth(S["side0"] + 0.16 * L, S["side0"] - 1.0, Z) * 0.7 + 0.55 * (blobs((h, w), 1.0 * ppi, 26) * 0.5 + 0.5) - 0.1)
    rusty = np.clip(np.maximum.reduce([0.85 * run, under_collar, bloom]), 0, 1)
    colour = colour * (1 - rusty[..., None]) + rustc * rusty[..., None]
    # Chips show rusty steel, not black.
    bare = chips * (1 - bloom)
    colour = colour * (1 - bare[..., None]) + (rustc * 1.15) * bare[..., None]
    rough = rough + 0.25 * rusty + 0.15 * bare
    metal = np.zeros((h, w), np.float32)
    height -= 0.004 * chips
    mud = smooth(S["side0"] + 1.5, S["side0"] - 2.0, Z) * np.clip(0.45 + 0.6 * blobs((h, w), 0.8 * ppi, 22), 0, 1)
    speck = smooth(0.8, 0.88, blobs((h, w), 0.05 * ppi, 23) * 0.5 + 0.5) * smooth(S["side0"] + 0.25 * L, S["side0"], Z)
    mud = np.maximum(mud, 0.8 * speck)
    mudc = np.array((0.22, 0.17, 0.12), np.float32) * (1 + 0.15 * blobs((h, w), 4, 24))[..., None]
    colour = colour * (1 - 0.85 * mud[..., None]) + mudc * 0.85 * mud[..., None]
    rough = np.maximum(rough, 0.8 * mud)
    grime = np.clip(0.25 * blobs((h, w), 1.5 * ppi, 25, aspect=(3.0, 1.0)) + 0.2, 0, 0.5)
    colour = colour * (1 - grime[..., None] * 0.35)
    # Years outdoors: a grey film heavier low down, and scuffs round the widest part where the bottles rub.
    film = smooth(S["side1"], S["side0"], Z) * np.clip(0.55 + 0.5 * blobs((h, w), 2.0 * ppi, 28), 0, 1)
    colour = colour * (1 - 0.22 * film[..., None]) + np.array((0.3, 0.28, 0.24), np.float32) * 0.08 * film[..., None]
    scuff = smooth(0.75, 0.9, blobs((h, w), 0.5 * ppi, 29, aspect=(0.08, 3.0)) * 0.5 + 0.5) * np.exp(-((Z - (S["side0"] + 0.62 * L)) / (0.14 * L)) ** 2)
    colour = colour * (1 - 0.35 * scuff[..., None])
    rough = rough + 0.1 * scuff
    ao = 1 - 0.45 * smooth(row_of(collar(S)[1]) / ppi + 0.1, row_of(collar(S)[1]) / ppi - 1.2, np.arange(h, dtype=np.float32)[:, None] / ppi) * (np.arange(h)[:, None] < row_of(collar(S)[1]) + 2 * ppi)
    ao = ao * (1 - 0.5 * smooth(S["side0"] - 0.5, S["side0"] - 2.5, Z))
    put("shell", np.clip(colour, 0, 1), height, np.clip(rough, 0.05, 1), metal, np.clip(np.broadcast_to(ao, (h, w)), 0, 1))

    # The collar: outside rows, a gap for its lip, inside rows. Stamped marks on the outside between the handholds, rust on its edges and inside.
    x, y, w, h = place["collar"]
    rc, z0c, z1c = collar(S)
    H = z1c - z0c
    colour, rough, height = base_paint((h, w), 31)
    rr = np.arange(h, dtype=np.float32)[:, None] / ppi
    inner = rr > H + 0.2
    zc = np.where(inner, z1c - (rr - H - 0.4), z1c - rr)
    zc = np.broadcast_to(zc, (h, w))
    st = Image.new("L", (w, h), 0)
    ds = ImageDraw.Draw(st)
    f = ImageFont.truetype(FONT_BOLD, max(7, round(0.34 * ppi)))
    marks = (("DOT-4BA240", "TW 68.5   WC 239.0"), ("RS 22917 B", "08 \u2022 19   11 \u2022 24")) if S["stencil"] else (("DOT-4BA240", "TW 17.2  WC 47.6"), ("RS 61430 C", "03 \u2022 21"))
    zr = (z1c - (S["holes"][1] - 0.15)) * ppi
    for k, (a, b) in enumerate(marks):
        cxm = (0.25 + 0.5 * k) * w
        ds.text((cxm, zr - 0.95 * ppi), a, font=f, fill=255, anchor="mm")
        ds.text((cxm, zr - 0.45 * ppi), b, font=f, fill=255, anchor="mm")
    stamp = ndi.gaussian_filter(np.asarray(st, np.float32) / 255, 0.6)
    height -= 0.012 * stamp
    colour = colour * (1 - 0.25 * stamp[..., None])
    edge = np.exp(-np.minimum(np.abs(zc - z1c), 5) / 0.35) + 0.6 * np.exp(-np.minimum(np.abs(zc - z0c), 5) / 0.5)
    rustc = rust_colour((h, w), ppi, 32)
    rusty = np.clip(0.8 * edge * (0.6 + 0.6 * blobs((h, w), 0.4 * ppi, 33)) + inner * (0.45 + 0.5 * blobs((h, w), 0.6 * ppi, 34)), 0, 1)
    run = streaks((h, w), ppi, np.full(w, 0.1 * ppi, np.float32), 35, length=1.8) * ~inner
    rusty = np.clip(np.maximum(rusty, 0.8 * run), 0, 1)
    colour = colour * (1 - rusty[..., None]) + rustc * rusty[..., None]
    rough = rough + 0.3 * rusty
    ao = np.where(inner, 0.55, 1.0) * (1 - 0.3 * smooth(z0c + 1.0, z0c, zc))
    put("collar", np.clip(colour, 0, 1), height, np.clip(rough, 0.05, 1), np.zeros((h, w)), np.clip(ao, 0, 1))
    collar_lip = (x + 0.5 * w, y + (H + 0.2) * ppi)

    # The foot ring: rusty, muddy, scraped along its bottom edge.
    x, y, w, h = place["foot"]
    colour, rough, height = base_paint((h, w), 41)
    fp = np.asarray(foot_profile(S))
    fs = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(fp, axis=0), axis=1))))
    zf = np.broadcast_to(np.interp(np.arange(h, dtype=np.float32) / ppi, fs, fp[:, 1])[:, None], (h, w))
    rustc = rust_colour((h, w), ppi, 42)
    rusty = np.clip(0.62 + 0.45 * blobs((h, w), 0.4 * ppi, 43) + 0.3 * smooth(1.0, 0.0, zf), 0, 1)
    colour = colour * (1 - rusty[..., None]) + rustc * rusty[..., None]
    mud = np.clip(smooth(fp[:, 1].max() * 0.8, 0.0, zf) * (0.5 + 0.6 * blobs((h, w), 0.6 * ppi, 44)), 0, 1)
    colour = colour * (1 - 0.8 * mud[..., None]) + np.array((0.2, 0.16, 0.11), np.float32) * 0.8 * mud[..., None]
    rough = np.clip(rough + 0.3 * rusty + 0.2 * mud, 0, 1)
    put("foot", np.clip(colour, 0, 1), height, rough, np.zeros((h, w)), np.full((h, w), 0.8))

    x, y, w, h = place["swatch"]
    colour = np.zeros((h, w, 3), np.float32)
    rough = np.full((h, w), 0.5, np.float32)
    metal = np.zeros((h, w), np.float32)
    step = w / len(SWATCH)
    for k, (name, c) in enumerate(SWATCH.items()):
        c0, c1 = round(k * step), round((k + 1) * step)
        colour[:, c0:c1] = c
        if name in ("brass", "steel"):
            metal[:, c0:c1], rough[:, c0:c1] = 0.8, 0.42
        if name == "rust":
            rough[:, c0:c1] = 0.9
    put("swatch", colour, np.zeros((h, w)), rough, metal, np.ones((h, w)))

    fill = tuple(ndi.distance_transform_edt(~COVER, return_distances=False, return_indices=True))
    COLOUR, HEIGHT, ROUGH, METAL, AO = COLOUR[fill], HEIGHT[fill], ROUGH[fill], METAL[fill], AO[fill]
    NORMAL = to_normal(HEIGHT, ppi)
    return COLOUR, NORMAL, ROUGH, METAL, AO, collar_lip


def build(S, place, lod, collar_lip):
    m = Mesh()
    ppi = S["ppi"]
    seg = (48, 24, 12)[lod]
    x, y, w, h = place["shell"]
    m.lathe(shell_profile(S), (x, y, w), ppi, seg, side=-1, sharp=30)
    x, y, w, h = place["foot"]
    m.lathe(foot_profile(S), (x, y, w), ppi, seg, side=1, sharp=40)
    rc, z0c, z1c = collar(S)
    hw, lo, hi = S["holes"]
    x, y, w, h = place["collar"]
    if lod < 2:
        m.band(rc, rc - 0.14, z0c, z1c, [(0.0, hw, lo, hi), (180.0, hw, lo, hi)], (x, y, w), ppi, seg, collar_lip)
        m.torus((0, 0, z1c), (0, 0, 1), rc - 0.07, 0.15, (collar_lip[0] - w / 2, collar_lip[1] - 2, w, 4), seg=seg, sides=6 if lod == 0 else 4)
    else:
        m.lathe([(rc, z0c), (rc, z1c), (rc - 0.14, z1c), (rc - 0.14, z0c)], (x, y, w), ppi, seg, side=1)
    # The valve: a brass body on its boss, the bonnet, the handwheel on its stem; the outlet along +X, the relief valve's yellow cap round the side.
    k = S["valve"]
    top = S["top"]
    brass, wheel, yellow, steel = (swatch_uv(place, n) for n in ("brass", "wheel", "yellow", "steel"))
    vs = 16 if lod == 0 else 8
    m.lathe([(0, top - 0.4), (0.95 * k, top - 0.4), (0.95 * k, top + 0.45 * k), (0.78 * k, top + 0.55 * k), (0.78 * k, top + 2.3 * k), (0.62 * k, top + 2.45 * k),
             (0.55 * k, top + 3.1 * k), (0.2 * k, top + 3.2 * k), (0.15 * k, top + 3.7 * k), (0, top + 3.7 * k)], (brass[0], brass[1], 0), 0, vs, side=1, sharp=20)
    wz = top + 3.75 * k
    if lod == 0:
        m.torus((0, 0, wz), (0, 0, 1), 1.25 * k, 0.17 * k, (wheel[0], wheel[1], 0, 0), seg=24, sides=6)
        m.lathe([(0, wz - 0.2 * k), (0.38 * k, wz - 0.2 * k), (0.38 * k, wz + 0.22 * k), (0, wz + 0.25 * k)], (wheel[0], wheel[1], 0), 0, 10, side=1)
        for j in range(5):
            a = np.radians(18 + 72 * j)
            m.rod((np.cos(a) * 0.3 * k, np.sin(a) * 0.3 * k, wz), (np.cos(a) * 1.2 * k, np.sin(a) * 1.2 * k, wz), 0.11 * k, wheel, sides=5)
        oz = top + 1.35 * k
        m.lathe([(0, 0), (0.42 * k, 0), (0.42 * k, 1.1 * k), (0.56 * k, 1.1 * k), (0.56 * k, 1.55 * k), (0.3 * k, 1.6 * k), (0, 1.6 * k)], (brass[0], brass[1], 0), 0, 6,
                side=1, centre=(0.6 * k, 0, oz), axis=(1, 0, 0), sharp=20)
        m.lathe([(0, 0), (0.42 * k, 0), (0.42 * k, 0.75 * k), (0.5 * k, 0.75 * k), (0.5 * k, 1.25 * k), (0, 1.3 * k)], (yellow[0], yellow[1], 0), 0, 12, side=1,
                centre=(0, 0.55 * k, top + 1.9 * k), axis=(-0.35, 1, 0.25), sharp=30)
        m.lathe([(0, 0), (0.22 * k, 0), (0.22 * k, 0.6 * k), (0.3 * k, 0.65 * k), (0.3 * k, 0.9 * k), (0, 0.9 * k)], (steel[0], steel[1], 0), 0, 8, side=1,
                centre=(-0.6 * k, -0.2 * k, top + 1.0 * k), axis=(-1, -0.3, 0), sharp=30)
    else:
        m.lathe([(0, wz - 0.2 * k), (1.35 * k, wz - 0.2 * k), (1.35 * k, wz + 0.2 * k), (0, wz + 0.2 * k)], (wheel[0], wheel[1], 0), 0, 10, side=1)
    return m


def write_model(name, S, counts):
    tail = 'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] }'
    meshes = "\n".join(f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{MODEL}/{name}_lod{k}.obj" {tail} }},' for k in range(3))
    l1, l2 = S["lods"]
    with open(os.path.join(OUT, f"{name}.vmdl"), "w", newline="\n") as h:
        h.write(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Riverside/propane-v2/propane.py: {counts}
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{{ from = "{name}.vmat" to = "{MATS}/{name}.vmat" }}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
{meshes}
				]
			}},
			{{
				_class = "LODGroupList"
				children =
				[
					{{ _class = "LODGroup" switch_threshold = 0.0 meshes = [ "lod0" ] }},
					{{ _class = "LODGroup" switch_threshold = {l1} meshes = [ "lod1" ] }},
					{{ _class = "LODGroup" switch_threshold = {l2} meshes = [ "lod2" ] }}
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
""")
    with open(os.path.join(MAT_OUT, f"{name}.vmat"), "w", newline="\n") as h:
        h.write(f"""// Generated by Sources/Riverside/propane-v2/propane.py

Layer0
{{
	shader "shaders/complex.shader"
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/{name}_ao.png"
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/{name}_color.png"
	g_bFogEnabled "1"
	TextureMetalness "{MATS}/{name}_metal.png"
	TextureNormal "{MATS}/{name}_normal.png"
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/{name}_rough.png"
}}
""")
    with open(os.path.join(OUT, f"{name}.mtl"), "w", newline="\n") as h:
        h.write(f"newmtl {name}\n")


for name, S in SPECS.items():
    place = plan(S)
    COLOUR, NORMAL, ROUGH, METAL, AO, lip = paint_cylinder(S, place)
    Image.fromarray((np.clip(COLOUR, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, f"{name}_color.png"))
    Image.fromarray((np.clip(NORMAL * 0.5 + 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, f"{name}_normal.png"))
    for array, kind in ((ROUGH, "rough"), (METAL, "metal"), (AO, "ao")):
        Image.fromarray((np.clip(array, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((S["atlas"] // 2,) * 2, Image.BOX).save(os.path.join(MAT_OUT, f"{name}_{kind}.png"))
    counts = [write_obj(os.path.join(OUT, f"{name}_lod{k}.obj"), build(S, place, k, lip), S["atlas"], name) for k in range(3)]
    write_model(name, S, counts)
    print(name, "triangles", counts, flush=True)
