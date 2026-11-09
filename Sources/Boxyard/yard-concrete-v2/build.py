"""Boxyard yard concrete v2 (review trial, 2026-11-09).

The yard's floor was one procedural 4096 px picture stretched over 64 ft (5.3 px/in): soft, pale and blurred at a
player's feet.  This builds a two-layer replacement from a real scan:

  slab tile   4096 px = one 16 ft slab (21.3 px/in).  The surface is Poly Haven's `concrete_floor_02` scan (CC0, 2 m
              square, already in the project at Assets/materials/forestbase/scans/) laid at its true scale, quilted from
              sixteen turned and shifted patches so the 2 m scan never shows as a grid, with the sawn joint, its
              sealant, dirt and spalled edges at the tile's border.
  macro layer 4096 px = nine by nine slabs (the whole yard, 2.4 px/in), multiplied over the slabs by the shader's
              detail slot (Mod2X): every slab's own tone, weather staining, tyre rubber, oil, rust ghosts of
              containers that stood there, dirt against the wall and round the containers that stand there now.
              It is locked to the world, so it only fits this yard's floor quad and this layout of containers.

    python build.py            both layers and the material
    python build.py macro      the macro layer only

Writes Assets/materials/boxyard/yard_concrete_v2/.
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCAN = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans", "concrete_floor_02_")
OUT = os.path.join(ROOT, "Assets", "materials", "boxyard", "yard_concrete_v2")
RES = "materials/boxyard/yard_concrete_v2"
MODELS = os.path.join(ROOT, "Assets", "models", "maps", "boxyard")

N = 4096                      # slab tile, px
SLAB = 192.0                  # inches
PPI = N / SLAB
SCAN_IN = 2000.0 / 25.4       # the scan is 2 m square
T = int(round(SCAN_IN * PPI)) # the scan at the tile's density (1680 px)

M = 4096                      # macro layer, px
SLABS = 9                     # slabs across the macro layer
MACRO_IN = SLABS * SLAB       # 1728 in
MPI = M / MACRO_IN

# The floor quad's UVs in boxyard_yard.obj: u = U0 + (840 - x) / 768, v = V0 + (z + 872) / 768 (OBJ x, z).
U0, V0, TILE = 1.60318, 2.45799, 768.0
VFLIP = True                  # the importer turns OBJ v upside down
# Checked in the editor from above with a numbered calibration texture: world (X, Y) = OBJ (z, x), the macro layer's
# picture x runs toward world -Y and its picture y toward world -X, and slab joints land on its ninths.


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def pnoise(n, f_lo, f_hi, beta, seed):
    """Periodic noise n x n, band limited to f_lo..f_hi cycles a tile, power 1/f^beta; zero mean, unit deviation."""
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n)).astype(np.float32)
    F = np.fft.rfft2(w)
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.rfftfreq(n)[None, :] * n
    f = np.sqrt(fx * fx + fy * fy)
    amp = np.where((f >= f_lo) & (f <= f_hi), 1.0 / np.maximum(f, 1e-6) ** (beta / 2.0), 0.0)
    out = np.fft.irfft2(F * amp, s=(n, n)).astype(np.float32)
    out -= out.mean()
    out /= out.std() + 1e-9
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The slab tile

def sym(a, k):
    if k & 1:
        a = a.transpose(1, 0, 2) if a.ndim == 3 else a.T
    if k & 2:
        a = a[:, ::-1]
    if k & 4:
        a = a[::-1]
    return np.ascontiguousarray(a)


def sym_normal(n, k):
    """The same turn for a GL normal map's x (right) and y (up) parts."""
    if k & 1:
        n = n.transpose(1, 0, 2)
        n = np.stack([-n[..., 1], -n[..., 0]], -1)
    if k & 2:
        n = n[:, ::-1] * np.array([-1.0, 1.0], np.float32)
    if k & 4:
        n = n[::-1] * np.array([1.0, -1.0], np.float32)
    return np.ascontiguousarray(n.astype(np.float32))


def load_scan():
    def rd(name, mode):
        a = np.asarray(Image.open(SCAN + name + ".jpg").convert(mode))
        return cv2.resize(a, (T, T), interpolation=cv2.INTER_AREA)
    diff = rd("diff", "RGB").astype(np.float32) / 255.0
    nor = rd("nor_gl", "RGB").astype(np.float32) / 255.0 * 2.0 - 1.0
    rough = rd("rough", "L").astype(np.float32) / 255.0
    ao = rd("ao", "L").astype(np.float32) / 255.0
    return diff, nor[..., :2].copy(), rough, ao


def quilt():
    """The scan over the whole tile: sixteen patches, each a turned and shifted copy, meeting on wandering seams."""
    rng = np.random.default_rng(20261109)
    diff, nxy, rough, ao = load_scan()
    mu_c = diff.reshape(-1, 3).mean(0)
    mu_r, mu_a = float(rough.mean()), float(ao.mean())
    G = 4
    seeds, offs, kinds = [], [], []
    for gy in range(G):
        for gx in range(G):
            seeds.append(((gx + rng.uniform(0.15, 0.85)) * N / G, (gy + rng.uniform(0.15, 0.85)) * N / G))
            offs.append((int(rng.integers(0, T)), int(rng.integers(0, T))))
            kinds.append(int(rng.integers(0, 8)))
    cache = {}

    def variant(k):
        if k not in cache:
            cache[k] = (sym(diff, k), sym_normal(nxy, k), sym(rough, k), sym(ao, k))
        return cache[k]

    wx = pnoise(N, 3, 40, 2.4, 11) * 55.0
    wy = pnoise(N, 3, 40, 2.4, 12) * 55.0
    BAND = 44.0
    col = np.zeros((N, N, 3), np.float32)
    nrm = np.zeros((N, N, 2), np.float32)
    rg = np.zeros((N, N), np.float32)
    occ = np.zeros((N, N), np.float32)
    CH = 256
    xs_all = np.arange(N, dtype=np.float32)
    for r0 in range(0, N, CH):
        r1 = r0 + CH
        yy, xx = np.meshgrid(np.arange(r0, r1, dtype=np.float32), xs_all, indexing="ij")
        px, py = xx + wx[r0:r1], yy + wy[r0:r1]
        d = np.stack([np.hypot(((px - sx + N / 2) % N) - N / 2, ((py - sy + N / 2) % N) - N / 2) for sx, sy in seeds])
        w = np.clip(1.0 - (d - d.min(0)) / BAND, 0.0, 1.0) ** 2
        w /= w.sum(0)
        inv = 1.0 / np.sqrt((w * w).sum(0))
        c = np.zeros((CH, N, 3), np.float32)
        n2 = np.zeros((CH, N, 2), np.float32)
        r_ = np.zeros((CH, N), np.float32)
        a_ = np.zeros((CH, N), np.float32)
        for i in range(len(seeds)):
            m = w[i] > 0
            if not m.any():
                continue
            ys, xs = np.nonzero(m)
            wi = w[i][m]
            sx = (xs + offs[i][0]) % T
            sy = (ys + r0 + offs[i][1]) % T
            vd, vn, vr, va = variant(kinds[i])
            c[m] += wi[:, None] * (vd[sy, sx] - mu_c)
            n2[m] += wi[:, None] * vn[sy, sx]
            r_[m] += wi * (vr[sy, sx] - mu_r)
            a_[m] += wi * (va[sy, sx] - mu_a)
        col[r0:r1] = mu_c + c * inv[..., None]         # keeps the scan's contrast where two patches mix
        nrm[r0:r1] = n2 * inv[..., None]
        rg[r0:r1] = mu_r + r_ * inv
        occ[r0:r1] = mu_a + a_ * inv
    return col, nrm, rg, occ


def slab():
    col, nxy, rough, ao = quilt()
    # Grade: the scan is a mossy brown floor; a port's yard is greyer.  Keep its values strong.
    lum = col @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    col = lum[..., None] + (col - lum[..., None]) * 0.50
    col *= np.array([0.985, 1.0, 1.03], np.float32)
    mean = col.mean()
    col = mean + (col - mean) * 1.12
    col *= (1.0 - 0.55 * (1.0 - np.clip(ao, 0, 1)))[..., None]
    col *= 0.455 / col.mean()                         # mean sRGB about 116: dirty outdoor concrete, not chalk

    # The sawn joint at the tile's border.
    c = (np.arange(N, dtype=np.float32) + 0.5) / PPI
    e = np.minimum(c, SLAB - c)
    dj = np.minimum(e[None, :], e[:, None])           # inches to the nearest joint
    fine = pnoise(N, 60, 900, 1.2, 21)
    blobs = pnoise(N, 40, 260, 2.0, 22)
    lf = pnoise(N, 4, 60, 2.2, 23)
    hw = 0.19 + 0.035 * fine
    groove = 1.0 - smoothstep(hw - 0.05, hw + 0.05, dj)
    chip = smoothstep(1.15, 1.9, blobs) * (1.0 - smoothstep(0.35, 1.25, dj)) * (1.0 - groove)
    dirt = np.exp(-dj / 1.5) * np.clip(0.6 + 0.35 * lf + 0.15 * fine, 0.0, 1.0) * (1.0 - groove)
    col *= (1.0 - 0.34 * dirt - 0.30 * chip)[..., None]
    seal = np.array([0.115, 0.11, 0.105], np.float32) * (1.0 + 0.25 * np.clip(fine, -1, 1))[..., None]
    col = col * (1.0 - groove[..., None]) + seal * groove[..., None]

    # Height of what was added, to bend the scan's normals.
    h = -0.16 * smoothstep(0.0, 1.0, groove) - 0.07 * chip
    h = cv2.GaussianBlur(np.pad(h, 8, mode="wrap"), (0, 0), 0.8)[8:-8, 8:-8]
    gy, gx = np.gradient(np.pad(h, 1, mode="wrap"))
    gx, gy = gx[1:-1, 1:-1] * PPI, gy[1:-1, 1:-1] * PPI
    nx = nxy[..., 0] * 1.45 - gx
    ny = nxy[..., 1] * 1.45 + gy
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack([nx / ln, ny / ln, nz / ln], -1)

    # Roughness: the scan's variation round a dry outdoor value; sealant a little slicker, dirt drier.
    rg = 0.80 + (rough - rough.mean()) * 1.5
    rg = rg + 0.05 * dirt
    rg = rg * (1.0 - groove) + 0.58 * groove
    rg = np.clip(rg, 0.35, 0.97)

    os.makedirs(OUT, exist_ok=True)
    Image.fromarray((np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8)).save(
        os.path.join(OUT, "yc_slab_color.jpg"), quality=94, subsampling=0)
    Image.fromarray(((normal * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)).save(
        os.path.join(OUT, "yc_slab_normal.jpg"), quality=96, subsampling=0)
    Image.fromarray((rg * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, "yc_slab_rough.png"), optimize=True)
    print("slab: colour mean", (col.reshape(-1, 3).mean(0, dtype=np.float64) * 255).round(1), "rough mean", round(float(rg.mean()), 3))


# ---------------------------------------------------------------------------------------------------------------------
# The macro layer

def obj_to_macro(x, z):
    """OBJ plan position to the macro layer's unwrapped pixel position."""
    u = U0 + (840.0 - np.asarray(x, float)) / TILE
    vo = V0 + (np.asarray(z, float) + 872.0) / TILE
    v = (1.0 - vo) if VFLIP else vo
    return (4.0 * u + 3.0) / SLABS * M, (4.0 * v + 3.0) / SLABS * M


def macro_to_obj():
    """Every macro pixel's OBJ plan position (x, z), wrapped into the yard."""
    t = (np.arange(M, dtype=np.float64) + 0.5) / M
    u = (SLABS * t - 3.0) / 4.0
    x = 840.0 - (u - U0) * TILE
    v = (SLABS * t - 3.0) / 4.0
    vo = (1.0 - v) if VFLIP else v
    z = (vo - V0) * TILE - 872.0
    wrap = lambda a: ((a + MACRO_IN / 2) % MACRO_IN) - MACRO_IN / 2
    return wrap(x)[None, :].astype(np.float32), wrap(z)[:, None].astype(np.float32)


def read_obj(path):
    V, F = [], []
    with open(path) as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()
                V.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("f "):
                F.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    return np.array(V), F


def footprints():
    """What stands on the floor now (the containers' and the heavy props' models), as a mask over the macro layer."""
    canvas = np.zeros((2 * M, 2 * M), np.uint8)
    bu = math.floor((4.0 * U0 + 3.0) / SLABS)
    v_lo = min((4.0 * ((1.0 - v) if VFLIP else v) + 3.0) / SLABS for v in (V0, V0 + 1744.0 / TILE))
    bv = math.floor(v_lo)
    for name, low in (("boxyard_containers.obj", 14.0), ("boxyard_props.obj", 3.0)):
        V, F = read_obj(os.path.join(MODELS, name))
        for f in F:
            p = V[f]
            if p[:, 1].min() > low or p[:, 1].max() > 112.0:
                continue
            cx, cy = obj_to_macro(p[:, 0], p[:, 2])
            pts = np.stack([cx - bu * M, cy - bv * M], -1)
            cv2.fillPoly(canvas, [np.round(pts).astype(np.int32)], 255)
            cv2.polylines(canvas, [np.round(pts).astype(np.int32)], True, 255, 1)
    occ = np.maximum(np.maximum(canvas[:M, :M], canvas[:M, M:]), np.maximum(canvas[M:, :M], canvas[M:, M:])) > 0
    occ = ndimage.binary_closing(occ, iterations=2)
    occ = ndimage.binary_fill_holes(occ)
    return occ


def strokes(rng):
    """Tyre rubber: paired tracks along the lanes, turns and short braking smears."""
    layer = np.zeros((M, M), np.float32)

    def draw(points, width_in, value):
        tmp = np.zeros((M, M), np.uint8)
        pts = np.asarray(points, np.float64)
        for ox in (-M, 0, M):
            for oy in (-M, 0, M):
                cv2.polylines(tmp, [np.round(pts + (ox, oy)).astype(np.int32)], False, 255,
                              max(1, int(round(width_in * MPI))), cv2.LINE_AA)
        np.maximum(layer, tmp.astype(np.float32) / 255.0 * value, out=layer)

    def pair(centre, gauge_in, width_in, value):
        c = np.asarray(centre, np.float64)
        t = np.gradient(c, axis=0)
        t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
        n = np.stack([-t[:, 1], t[:, 0]], -1)
        for s in (-0.5, 0.5):
            draw(c + n * s * gauge_in * MPI, width_in, value * rng.uniform(0.75, 1.0))

    for _ in range(11):                               # long runs along the lanes (the u axis), wandering a little
        y0 = rng.uniform(0, M)
        x = np.linspace(-0.1 * M, 1.1 * M, 60)
        y = y0 + np.cumsum(rng.normal(0, 3.0, 60)) + 40 * np.sin(x / M * rng.uniform(2, 6) + rng.uniform(0, 6))
        a, b = sorted(rng.uniform(-0.1, 1.1, 2))
        k = (x > a * M) & (x < max(b, a + 0.25) * M)
        if k.sum() > 4:
            pair(np.stack([x[k], y[k]], -1), rng.uniform(44, 62), rng.uniform(7, 11), rng.uniform(0.25, 0.6))
    for _ in range(5):                                # across the lanes
        x0 = rng.uniform(0, M)
        y = np.linspace(rng.uniform(0, 0.5) * M, rng.uniform(0.6, 1.1) * M, 40)
        x = x0 + np.cumsum(rng.normal(0, 3.0, 40))
        pair(np.stack([x, y], -1), rng.uniform(44, 62), rng.uniform(7, 10), rng.uniform(0.2, 0.45))
    for _ in range(12):                               # turns
        cx, cy = rng.uniform(0, M, 2)
        rad = rng.uniform(70, 210) * MPI
        a0 = rng.uniform(0, 2 * math.pi)
        a = np.linspace(a0, a0 + rng.uniform(1.0, 2.4), 40)
        pair(np.stack([cx + rad * np.cos(a), cy + rad * np.sin(a)], -1), rng.uniform(44, 62), rng.uniform(8, 12),
             rng.uniform(0.3, 0.7))
    for _ in range(10):                               # braking smears
        cx, cy = rng.uniform(0, M, 2)
        ang = rng.choice([0.0, math.pi / 2]) + rng.normal(0, 0.12)
        ln = rng.uniform(40, 110) * MPI
        p = np.stack([cx + np.linspace(0, ln, 12) * math.cos(ang), cy + np.linspace(0, ln, 12) * math.sin(ang)], -1)
        pair(p, rng.uniform(44, 62), rng.uniform(8, 11), rng.uniform(0.55, 0.95))
    return layer


def macro():
    rng = np.random.default_rng(909)
    mult = np.ones((M, M, 3), np.float32)
    t = (np.arange(M, dtype=np.float32) + 0.5) / M * SLABS
    si, sj = np.floor(t).astype(int)[None, :], np.floor(t).astype(int)[:, None]

    # Every slab was poured on its own day.
    tone = np.clip(rng.normal(1.0, 0.04, (SLABS, SLABS)), 0.90, 1.10).astype(np.float32)
    warm = rng.normal(0.0, 0.012, (SLABS, SLABS)).astype(np.float32)
    for _ in range(5):                                # newer slabs
        a, b = rng.integers(0, SLABS, 2)
        tone[a, b] = rng.uniform(1.07, 1.13)
        warm[a, b] = -0.02
    cell = tone[sj, si]
    cw = warm[sj, si]
    mult *= cell[..., None]
    mult *= np.stack([1.0 + cw, np.ones_like(cw), 1.0 - cw], -1)

    # Weather: broad staining, and damp patches with an edge.
    broad = pnoise(M, 2, 14, 2.6, 31)
    mid = pnoise(M, 10, 90, 2.2, 32)
    fine = pnoise(M, 60, 700, 1.6, 33)
    mult *= (1.0 + 0.07 * broad + 0.06 * mid)[..., None]   # the mid term also hides that every slab is one tile
    damp = smoothstep(0.9, 1.15, pnoise(M, 5, 40, 2.4, 34) + 0.25 * mid)
    mult *= (1.0 - 0.10 * damp)[..., None]

    x, z = macro_to_obj()
    dwall = np.minimum(800.0 - np.abs(x), 832.0 - np.abs(z))

    # Tyre rubber.  Nothing drives into the wall: the tracks fade out short of it.
    rub = strokes(rng)
    rub = cv2.GaussianBlur(rub, (0, 0), 2.6)
    streak = np.clip(0.72 + 0.14 * fine + 0.20 * mid, 0.3, 1.0)     # soft and even: hard blots read as spilt tar
    rub = rub * streak * smoothstep(25.0, 120.0, dwall)
    mult *= (1.0 - 0.45 * rub)[..., None]

    px, pz = np.meshgrid(np.arange(M, dtype=np.float32), np.arange(M, dtype=np.float32))

    def torus(cx, cy):
        return ((px - cx + M / 2) % M) - M / 2, ((pz - cy + M / 2) % M) - M / 2

    # Oil soaked into concrete: a soft grey-brown stain, darkest where it dripped, a faint spread round it and a few
    # spots near by.  (A hard, ragged edge here drew as spilt tar in the editor.)
    oil = np.zeros((M, M), np.float32)
    wob = np.clip(1.0 + 0.30 * mid, 0.45, 1.6)
    for _ in range(22):
        cx, cy = rng.uniform(0, M, 2)
        rad = rng.uniform(4.0, 15.0) * MPI
        k = rng.uniform(0.45, 0.9)
        dx, dy = torus(cx, cy)
        r = np.hypot(dx, dy) / rad / wob
        spot = (1.0 - smoothstep(0.25, 1.0, r)) * k + (1.0 - smoothstep(0.6, 2.0, r)) * 0.22 * k
        np.maximum(oil, np.clip(spot, 0.0, 1.0), out=oil)
        for _ in range(int(rng.integers(3, 9))):
            a, dist = rng.uniform(0, 2 * math.pi), rng.uniform(1.2, 3.2) * rad
            ddx, ddy = torus(cx + dist * math.cos(a), cy + dist * math.sin(a))
            rr = np.hypot(ddx, ddy) / (rng.uniform(0.6, 2.2) * MPI)
            np.maximum(oil, (1.0 - smoothstep(0.2, 1.0, rr)) * rng.uniform(0.4, 0.8) * 0.8, out=oil)
    oil = cv2.GaussianBlur(oil, (0, 0), 0.6 * MPI)
    mult *= 1.0 - oil[..., None] * np.array([0.50, 0.53, 0.58], np.float32)

    # Rust ghosts: where a container's corner castings and bottom rails once sat.
    rust = np.zeros((M, M), np.float32)
    for _ in range(7):
        cx, cy = rng.uniform(0, M, 2)
        L, W = (238.6, 96.0) if rng.random() < 0.6 else (96.0, 238.6)
        dx, dy = torus(cx, cy)
        dx, dy = dx / MPI, dy / MPI
        k = rng.uniform(0.5, 1.0)
        for sx in (-1, 1):
            for sy in (-1, 1):
                d = np.maximum(np.abs(dx - sx * (L / 2 - 3.5)) - 3.5, np.abs(dy - sy * (W / 2 - 3.2)) - 3.2)
                np.maximum(rust, (1.0 - smoothstep(-0.5, 2.5, d)) * k, out=rust)
        long_x = L > W
        for s in (-1, 1):                             # the two bottom side rails
            if long_x:
                d = np.maximum(np.abs(dy - s * (W / 2 - 1.5)) - 1.2, np.abs(dx) - L / 2)
            else:
                d = np.maximum(np.abs(dx - s * (L / 2 - 1.5)) - 1.2, np.abs(dy) - W / 2)
            np.maximum(rust, (1.0 - smoothstep(-0.3, 1.2, d)) * 0.38 * k * np.clip(0.5 + 0.6 * mid, 0, 1), out=rust)
    rust *= np.clip(0.75 + 0.3 * fine, 0.3, 1.0)
    mult *= 1.0 - rust[..., None] * np.array([0.22, 0.48, 0.66], np.float32)

    # Against the wall, and round what stands in the yard now.
    foot = np.exp(-np.clip(dwall, 0, None) / 13.0) * np.clip(0.65 + 0.3 * mid + 0.15 * fine, 0.1, 1.0)
    mult *= 1.0 - foot[..., None] * np.array([0.34, 0.31, 0.36], np.float32)
    occ = footprints()
    dist = ndimage.distance_transform_edt(~occ).astype(np.float32) / MPI
    near = np.exp(-dist / 4.5) * np.clip(0.7 + 0.3 * mid + 0.2 * fine, 0.15, 1.0)
    wide = np.exp(-dist / 26.0) * np.clip(0.5 + 0.5 * broad * 0.5 + 0.35 * mid, 0.0, 1.0)
    contact = np.clip(0.34 * near + 0.10 * wide, 0.0, 0.5)
    contact[occ] = 0.35
    mult *= 1.0 - contact[..., None] * np.array([0.92, 1.0, 1.08], np.float32)
    weep = np.exp(-dist / 7.0) * smoothstep(0.5, 1.4, pnoise(M, 30, 200, 2.0, 35)) * (~occ)
    mult *= 1.0 - weep[..., None] * np.array([0.10, 0.30, 0.46], np.float32)

    mult /= mult.reshape(-1, 3).mean(0, dtype=np.float64).astype(np.float32)   # the layer shifts nothing overall: mid grey is "no change"
    # Everything above is the ratio wanted on screen.  The shader reads this texture as linear and multiplies the
    # linear albedo by twice its value, so the ratio goes in as its 2.2 power (checked in the editor: a flat 60/128
    # block drew at about 0.7 of its neighbours, not 0.47).
    img = np.clip(np.power(np.clip(mult, 0.02, None), 2.2) * 128.0, 0, 255).astype(np.uint8)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(img).save(os.path.join(OUT, "yc_macro_detail.png"), optimize=True)
    check = os.path.join(ROOT, "output", "boxyard", "yard-concrete-v2")
    os.makedirs(check, exist_ok=True)
    Image.fromarray((occ * 255).astype(np.uint8)).resize((1024, 1024)).save(os.path.join(check, "footprints_check.png"))
    print("macro: mean", img.reshape(-1, 3).mean(0, dtype=np.float64).round(1), "min", img.min(), "max", img.max(),
          "occupied", round(float(occ.mean()) * 100, 1), "%")


VMAT = """// Sources/Boxyard/yard-concrete-v2/build.py
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_DETAIL_TEXTURE "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.00"
    TextureColor "%(res)s/yc_slab_color.jpg"
    TextureNormal "%(res)s/yc_slab_normal.jpg"
    TextureRoughness "%(res)s/yc_slab_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureDetail "%(res)s/yc_macro_detail.png"
    g_vTexCoordScale "[4.000 4.000]"
    g_vDetailTexCoordScale "[%(ds).6f %(ds).6f]"
    g_vDetailTexCoordOffset "[%(do).6f %(do).6f]"
    g_flDetailTexCoordRotation "0.000"
    g_flDetailBlendFactor "1.000"
    g_bUseSecondaryUvForDetailTexture "0"
    g_bUseSecondaryUvForDetailMask "0"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}
"""


def vmat():
    # The floor's UVs run 768 in a unit: 4 slab tiles a unit, and the macro layer 9 slabs a tile.  The shader turns
    # the detail UVs about (0.5, 0.5), so the offset puts slab edges back on ninths of the macro layer.
    ds = 4.0 / SLABS
    do = (3.0 / SLABS) - 0.5 + 0.5 * ds
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "bx_yard_concrete.vmat"), "w", newline="\n") as fh:
        fh.write(VMAT % {"res": RES, "ds": ds, "do": do})
    print("vmat: detail scale", round(ds, 6), "offset", round(do, 6))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "slab"):
        slab()
    if what in ("all", "macro"):
        macro()
    vmat()
