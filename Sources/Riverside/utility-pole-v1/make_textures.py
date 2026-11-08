"""Riverside utility pole v1: the creosote pole's wood texture, made from the project's real scan.

The old pole (`rs_pole`) is a 512 px procedural tile painted at 64 in a repeat (8 px per inch), with a mean colour of
about (72, 57, 43) and almost no contrast. This one is built from the weathered CC0 brown_planks_03 crops of the approved
Riverside crate atlas (the same crops the Lucky Stop timber steps and the watch deck use), rotated so the grain runs
along the pole, tone-matched strip by strip, blended across the seams (wrapping both ways, so it tiles), then graded to
the old pole's creosote brown with more contrast: long dark creosote bleed, sparse silvered streaks, and a few long
seasoning checks (cracks) that are in the colour, normal and roughness maps. The result is 1024 x 2048: u goes round the
pole (about 27 px per inch at the butt), v along it (30 px per inch, one repeat every 68 in).

Output (Assets/materials/riverside/utility_pole_v1/): pole_wood_color.png, pole_wood_normal.png (OpenGL, +Y up, like the
crate's), pole_wood_rough.png, and a preview sheet in output/riverside/utility-pole-v1/.

Usage: python -B make_textures.py
"""
from pathlib import Path
import sys, math, json

import numpy as np
from PIL import Image, ImageFilter

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
SRC = ROOT / 'Assets/materials/riverside/crate_v2'
OUT = ROOT / 'Assets/materials/riverside/utility_pole_v1'
PREVIEW = ROOT / 'output/riverside/utility-pole-v1'

W, H = 1024, 2048
COLUMNS = 7
ROW_H = 1024                      # two rows stacked make the 2048 px height
BLEND_V = 28                      # half-overlap between rows (px)
BLEND_U = 10                      # half-overlap between strips (px)
SEED = 20261106
TARGET_MEAN = np.array((70.0, 55.0, 41.0)) / 255.0      # the old pole's mean (72, 57, 43), a touch darker

# Weathered plank bands of the approved crate atlas (x0, y0, height in pixels; each 1008 px wide). They skip the
# stencilled lettering and the dark joint lines.
CROPS = [(8, 342, 138), (8, 547, 129), (8, 700, 140), (8, 848, 137), (8, 1012, 138), (8, 1382, 138), (8, 1534, 138),
         (8, 1700, 130), (8, 1858, 134), (1032, 370, 120), (1032, 540, 140), (1032, 692, 144), (1032, 856, 134),
         (1032, 1014, 138), (1032, 1216, 124), (1032, 1364, 136), (1032, 1512, 142), (1032, 1676, 142), (1032, 1822, 134)]
CROP_W = 1008


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def periodic_blur(arr, sy, sx):
    """ Gaussian blur that wraps round both edges, so what it makes tiles. """
    h, w = arr.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2.0 * math.pi ** 2 * ((sy * fy) ** 2 + (sx * fx) ** 2))
    return np.fft.irfft2(np.fft.rfft2(arr) * g, s=arr.shape).astype(np.float32)


def noise(rng, sy, sx):
    n = periodic_blur(rng.standard_normal((H, W)).astype(np.float32), sy, sx)
    return (n - n.mean()) / (n.std() + 1e-9)


def load():
    col = np.asarray(Image.open(SRC / 'crate_color.png').convert('RGB'), np.uint8)
    nor = np.asarray(Image.open(SRC / 'crate_normal.png').convert('RGB'), np.uint8)
    rou = np.asarray(Image.open(SRC / 'crate_rough.png').convert('L'), np.uint8)
    return col, nor, rou


def rotated_crop(maps, crop, flip_u, flip_v, width):
    """ One plank band turned so its grain runs up and down, scaled to `width` px across, all three maps alike.
    The normal's x and y are turned with the picture ((nx, ny) -> (-ny, nx) for a quarter turn) and mirrored with it. """
    col, nor, rou = maps
    x0, y0, h = crop
    c = col[y0:y0 + h, x0:x0 + CROP_W]
    n = nor[y0:y0 + h, x0:x0 + CROP_W].astype(np.float32) / 255.0
    r = rou[y0:y0 + h, x0:x0 + CROP_W]
    c, n, r = np.rot90(c, 1), np.rot90(n, 1).copy(), np.rot90(r, 1)
    nx, ny = n[..., 0].copy(), n[..., 1].copy()
    n[..., 0], n[..., 1] = 1.0 - ny, nx
    if flip_u:
        c, n, r = c[:, ::-1], n[:, ::-1].copy(), r[:, ::-1]
        n[..., 0] = 1.0 - n[..., 0]
    if flip_v:
        c, n, r = c[::-1], n[::-1].copy(), r[::-1]
        n[..., 1] = 1.0 - n[..., 1]
    n8 = np.clip(n * 255.0 + 0.5, 0, 255).astype(np.uint8)
    scale = width / c.shape[1]
    size = (width, int(round(c.shape[0] * scale)))
    ci = Image.fromarray(np.ascontiguousarray(c)).resize(size, Image.LANCZOS)
    ni = Image.fromarray(np.ascontiguousarray(n8)).resize(size, Image.LANCZOS)
    ri = Image.fromarray(np.ascontiguousarray(r)).resize(size, Image.LANCZOS)
    # Tone-match: take most of the plank's own large-scale tone out, so the strips differ in grain, not in brightness.
    cf = np.asarray(ci, np.float32) / 255.0
    low = np.asarray(ci.filter(ImageFilter.GaussianBlur(30)), np.float32) / 255.0
    cf = cf - 0.85 * low + 0.85 * np.array((126.5, 109.5, 85.0), np.float32) / 255.0
    return cf, np.asarray(ni, np.float32) / 255.0, np.asarray(ri, np.float32) / 255.0


def compose(maps, rng):
    """ Three canvases (colour, normal, roughness), H x W, wrapped in both directions. """
    pitch = W / COLUMNS
    strip_w = int(round(pitch + 2 * BLEND_U))
    row_h = ROW_H + 2 * BLEND_V
    col = np.zeros((H, W, 3), np.float32)
    nor = np.zeros((H, W, 3), np.float32)
    rou = np.zeros((H, W), np.float32)
    wsum = np.zeros((H, W), np.float32)
    last = -1
    for r in range(H // ROW_H):
        # a row of strips
        rc = np.zeros((row_h, W, 3), np.float32)
        rn = np.zeros((row_h, W, 3), np.float32)
        rr = np.zeros((row_h, W), np.float32)
        rw = np.zeros((row_h, W), np.float32)
        for j in range(COLUMNS):
            k = rng.integers(len(CROPS))
            while k == last:
                k = rng.integers(len(CROPS))
            last = k
            c, n, ro = rotated_crop(maps, CROPS[k], bool(rng.integers(2)), bool(rng.integers(2)), strip_w)
            y0 = int(rng.integers(0, c.shape[0] - row_h + 1))
            c, n, ro = c[y0:y0 + row_h], n[y0:y0 + row_h], ro[y0:y0 + row_h]
            x = np.arange(strip_w)
            ramp = np.minimum(smoothstep(0.0, 2.0 * BLEND_U, x), smoothstep(0.0, 2.0 * BLEND_U, strip_w - 1 - x)).astype(np.float32)
            idx = (np.round(j * pitch - BLEND_U).astype(int) + x) % W
            wgt = np.broadcast_to(ramp[None, :], (row_h, strip_w))
            rc[:, idx] += c * wgt[..., None]
            rn[:, idx] += n * wgt[..., None]
            rr[:, idx] += ro * wgt
            rw[:, idx] += wgt
        rc /= rw[..., None]
        rn /= rw[..., None]
        rr /= rw
        # the row onto the canvas, feathered top and bottom, wrapping in v
        y = np.arange(row_h)
        ramp = np.minimum(smoothstep(0.0, 2.0 * BLEND_V, y), smoothstep(0.0, 2.0 * BLEND_V, row_h - 1 - y)).astype(np.float32)
        rows = (r * ROW_H - BLEND_V + y) % H
        col[rows] += rc * ramp[:, None, None]
        nor[rows] += rn * ramp[:, None, None]
        rou[rows] += rr * ramp[:, None]
        wsum[rows] += ramp[:, None] * np.ones((1, W), np.float32)
    col /= wsum[..., None]
    nor /= wsum[..., None]
    rou /= wsum
    return col, nor, rou


def checks(rng, count=9):
    """ Long seasoning cracks along the grain: a height field (0 = surface, negative = groove), wrapping. """
    hgt = np.zeros((H, W), np.float32)
    for _ in range(count):
        u = rng.uniform(0, W)
        v0 = rng.uniform(0, H)
        length = int(rng.uniform(260, 820))
        width = rng.uniform(1.8, 3.4)
        drift = 0.0
        for j in range(length):
            drift += rng.normal(0.0, 0.18)
            drift *= 0.985
            taper = math.sin(math.pi * (j + 0.5) / length) ** 0.6
            hw = max(0.6, width * taper)
            uc = u + drift * 2.5 + 0.8 * math.sin(j / 61.0 + u)
            v = int(v0 + j) % H
            for dx in range(-int(hw) - 2, int(hw) + 3):
                depth = 1.0 - (abs(dx + (uc - round(uc))) / hw) ** 1.4
                if depth > 0:
                    x = int(round(uc)) + dx
                    hgt[v, x % W] = min(hgt[v, x % W], -depth * taper)
    return periodic_blur(hgt, 0.8, 0.7)


def build():
    rng = np.random.default_rng(SEED)
    maps = load()
    col, nor, rou = compose(maps, rng)

    # --- colour: the old pole's creosote brown, with more contrast, bleed streaks, silvered patches and checks ---
    mean = col.reshape(-1, 3).mean(axis=0)
    col = col * (TARGET_MEAN / mean)[None, None, :]                      # to the old pole's mean colour
    mu = col.reshape(-1, 3).mean(axis=0)
    col = mu + (col - mu) * 1.30                                        # strong values (the old pole's p5..p95 was 59..89)
    tone = noise(rng, 230, 8)
    col *= np.exp(0.17 * tone)[..., None]
    bleed = noise(rng, 280, 3)
    col *= (1.0 - 0.34 * smoothstep(0.9, 2.1, bleed))[..., None]       # long dark creosote runs
    silver = noise(rng, 100, 14)
    sm = smoothstep(1.15, 2.0, silver)
    # sun-silvered wood keeps its grain: the colour's own luminance, lifted and desaturated, not a flat grey
    luma = (col @ np.array((0.299, 0.587, 0.114), np.float32))[..., None]
    silvered = np.clip(luma * 1.55 + 0.045, 0.0, 1.0) * np.array((0.99, 0.95, 0.88), np.float32)[None, None, :]
    col = col * (1.0 - 0.62 * sm)[..., None] + silvered * (0.62 * sm)[..., None]
    speck = rng.standard_normal((H, W)).astype(np.float32)
    col *= (1.0 + 0.05 * periodic_blur(speck, 0.9, 0.9) * 6.0)[..., None]
    hgt = checks(rng)
    groove = np.clip(-hgt * 1.6, 0.0, 1.0)
    col *= (1.0 - 0.62 * groove)[..., None]
    col = np.clip(col, 0.0, 1.0)

    # --- normal: the crop's own relief plus the checks' slope ---
    v = nor * 2.0 - 1.0
    gu = (np.roll(hgt, -1, axis=1) - np.roll(hgt, 1, axis=1)) * 0.5
    gv = (np.roll(hgt, -1, axis=0) - np.roll(hgt, 1, axis=0)) * 0.5     # rows run down, +v is up
    v[..., 0] += -gu * 2.2
    v[..., 1] += +gv * 2.2
    v[..., 2] = np.maximum(v[..., 2], 0.05)
    v /= np.linalg.norm(v, axis=2, keepdims=True)
    nor = v * 0.5 + 0.5

    # --- roughness: creosote is a little glossier than raw wood, the silvered patches and the checks are dry ---
    rou = np.clip(rou * 0.85 + 0.12 + 0.12 * sm + 0.35 * groove - 0.06 * smoothstep(0.9, 2.1, bleed), 0.0, 1.0)
    return col, nor, rou, hgt


def save(col, nor, rou):
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(col * 255.0 + 0.5, 0, 255).astype(np.uint8), 'RGB').save(OUT / 'pole_wood_color.png', optimize=True)
    Image.fromarray(np.clip(nor * 255.0 + 0.5, 0, 255).astype(np.uint8), 'RGB').save(OUT / 'pole_wood_normal.png', optimize=True)
    Image.fromarray(np.clip(rou * 255.0 + 0.5, 0, 255).astype(np.uint8), 'L').save(OUT / 'pole_wood_rough.png', optimize=True)


def preview(col, nor, rou):
    PREVIEW.mkdir(parents=True, exist_ok=True)
    c8 = np.clip(col * 255.0 + 0.5, 0, 255).astype(np.uint8)
    tiled = np.tile(c8, (2, 2, 1))                                      # 2 x 2 repeats, to look for seams
    Image.fromarray(tiled).resize((1024, 2048), Image.LANCZOS).save(PREVIEW / 'texture_tiled_2x2.png')
    old = np.asarray(Image.open(ROOT / 'Assets/materials/riverside/rs_pole_color.jpg').convert('RGB'))
    sheet = Image.new('RGB', (4 * 260, 1040), (24, 24, 24))
    sheet.paste(Image.fromarray(c8).resize((256, 512), Image.LANCZOS), (2, 4))
    sheet.paste(Image.fromarray(np.clip(nor * 255.0 + 0.5, 0, 255).astype(np.uint8)).resize((256, 512), Image.LANCZOS), (262, 4))
    sheet.paste(Image.fromarray(np.clip(rou * 255.0 + 0.5, 0, 255).astype(np.uint8), 'L').convert('RGB').resize((256, 512), Image.LANCZOS), (522, 4))
    sheet.paste(Image.fromarray(old).resize((256, 256), Image.LANCZOS), (782, 4))
    # the same 24 in of pole at the same scale: old (8 px/in) vs new (27 px/in), as the engine would show it at 1 m
    new_crop = Image.fromarray(c8[600:600 + 648, 0:1024]).resize((1024, 648), Image.LANCZOS)
    sheet2 = Image.new('RGB', (1024 + 8, 1040), (24, 24, 24))
    sheet2.paste(new_crop.resize((1024, 648)), (4, 4))
    sheet.save(PREVIEW / 'texture_sheet.png')
    return {'mean_new': (col.reshape(-1, 3).mean(axis=0) * 255).round(1).tolist(),
            'p5_new': np.percentile(col.reshape(-1, 3) * 255, 5, axis=0).round(1).tolist(),
            'p95_new': np.percentile(col.reshape(-1, 3) * 255, 95, axis=0).round(1).tolist(),
            'mean_old': old.reshape(-1, 3).mean(axis=0).round(1).tolist(),
            'p5_old': np.percentile(old.reshape(-1, 3), 5, axis=0).round(1).tolist(),
            'p95_old': np.percentile(old.reshape(-1, 3), 95, axis=0).round(1).tolist()}


if __name__ == '__main__':
    col, nor, rou, hgt = build()
    save(col, nor, rou)
    info = preview(col, nor, rou)
    print(json.dumps(info, indent=1))
