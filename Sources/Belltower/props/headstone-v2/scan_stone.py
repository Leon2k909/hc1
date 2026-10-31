"""A clean sheet of real stone for the headstones: python scan_stone.py <project root> <work dir>

The surface comes from a photo scan already in the project, medieval_blocks_03, the same one Belltower's walls use. Patches from its blocks' faces are
quilted together with no joints in them, at the scan's own scale, so a stone's face is real weathered stone with its real pits, mottling and roughness. The scan's
displacement map is blank, so height is worked out from its normal map. Saves scan_stone.npy: colour (linear) x 3, height in inches, roughness, occlusion, at SCALE px/in.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT, WORK = sys.argv[1], sys.argv[2]
BASE = os.path.join(ROOT, "Assets", "materials", "belltower", "scans", "medieval_blocks_03_")
SCALE = 41.0  # Scan pixels to the inch: its blocks then come out about 25 in wide, as real ashlar is.
OUT_SIZE, PATCH, OVERLAP, TRIES = 4096, 640, 120, 140
# The faces of the scan's darker, more weathered blocks, marked by eye, kept clear of joints and arrises: left, top, right, bottom. Its pale sandy blocks are left out.
BLOCKS = (
    (620, 40, 1880, 770),
    (1990, 40, 3050, 770),
    (3240, 40, 4080, 770),
    (240, 900, 1100, 1590),
    (1210, 900, 2660, 1590),
    (2410, 1720, 4080, 2440),
    (1330, 2590, 3010, 3270),
    (3120, 2590, 3810, 3270),
    (810, 3390, 2060, 4080),
    (2700, 3390, 4080, 4080),
)
rng = np.random.default_rng(1871)
Image.MAX_IMAGE_PIXELS = None


def channel(name):
    return np.array(Image.open(BASE + name + "_4k.png"))


def integrate(nx, ny):
    """Height in pixels from a normal map's slopes (Frankot-Chellappa). Rows run down the image and GL normals' y runs up it."""
    h, w = nx.shape
    p = -nx
    q = ny
    wx = np.fft.fftfreq(w) * 2 * np.pi
    wy = np.fft.fftfreq(h) * 2 * np.pi
    u, v = np.meshgrid(wx, wy)
    denom = u * u + v * v
    denom[0, 0] = 1.0
    out = np.fft.ifft2((-1j * u * np.fft.fft2(p) - 1j * v * np.fft.fft2(q)) / denom).real
    return out.astype(np.float32)


srgb = channel("diffuse")[..., :3].astype(np.float32) / 255.0
linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4).astype(np.float32)
del srgb
normal = channel("nor_gl")[..., :3].astype(np.float32) / 255.0 * 2 - 1
slope_x = normal[..., 0] / np.maximum(normal[..., 2], 0.25)
slope_y = normal[..., 1] / np.maximum(normal[..., 2], 0.25)
del normal
height = integrate(slope_x, slope_y)
del slope_x, slope_y
rough = channel("rough").astype(np.float32) / 65535.0
ao = channel("ao").astype(np.float32) / 65535.0
print("loaded", flush=True)

# Height's broad shape is the wall's, not the stone's: keep only what a cut stone's face would have.
height = (height - ndi.gaussian_filter(height, 120)).astype(np.float32) / SCALE
src = np.dstack((linear, height, rough, ao)).astype(np.float32)
del linear, height, rough, ao
LUMA = np.array((0.3, 0.6, 0.1, 6.0, 0.0, 0.0), np.float32)
weights = np.array([(r - l - PATCH) * (d - t - PATCH) for l, t, r, d in BLOCKS], np.float64)
weights = weights / weights.sum()


def candidate():
    """A random place on a block's face, and one of its eight turns: stone has no up, and the scan is evenly lit."""
    l, t, r, d = BLOCKS[int(rng.choice(len(BLOCKS), p=weights))]
    return int(rng.integers(l, r - PATCH)), int(rng.integers(t, d - PATCH)), int(rng.integers(0, 8))


def cut(x, y, turn):
    patch = np.rot90(src[y : y + PATCH, x : x + PATCH], turn % 4)
    return patch[:, ::-1] if turn >= 4 else patch


def seam_mask(err):
    """Where the new patch takes over, across an overlap of err (rows, cols): 0 keeps what's there on the left, 1 the new patch on the right."""
    cost = err.copy()
    for r in range(1, cost.shape[0]):
        row = cost[r - 1]
        left = np.r_[np.inf, row[:-1]]
        right = np.r_[row[1:], np.inf]
        cost[r] += np.minimum(np.minimum(left, row), right)
    path = np.zeros(cost.shape[0], np.int32)
    path[-1] = int(np.argmin(cost[-1]))
    for r in range(cost.shape[0] - 2, -1, -1):
        c = path[r + 1]
        lo, hi = max(c - 1, 0), min(c + 2, cost.shape[1])
        path[r] = lo + int(np.argmin(cost[r, lo:hi]))
    columns = np.arange(cost.shape[1])[None, :]
    return (columns >= path[:, None]).astype(np.float32)


step = PATCH - OVERLAP
out = np.zeros((OUT_SIZE + PATCH, OUT_SIZE + PATCH, src.shape[-1]), np.float32)
used = 0
taken = []
for top in range(0, OUT_SIZE, step):
    for left in range(0, OUT_SIZE, step):
        here = out[top : top + PATCH, left : left + PATCH]
        scored = []
        while len(scored) < TRIES:
            x, y, turn = candidate()
            # Never the same bit of stone twice the same way round, or the eye finds the repeat.
            if any(t == turn and abs(x - ux) < 420 and abs(y - uy) < 420 for ux, uy, t in taken):
                continue
            patch = cut(x, y, turn)
            err = 0.0
            if left:
                err += float((((patch[:, :OVERLAP] - here[:, :OVERLAP]) * LUMA) ** 2).sum())
            if top:
                err += float((((patch[:OVERLAP] - here[:OVERLAP]) * LUMA) ** 2).sum())
            scored.append((err, x, y, turn))
        scored.sort()
        # Not always the very best fit, which would drift to the blandest stone in the scan.
        _, x, y, turn = scored[int(rng.integers(0, max(TRIES // 10, 1)))]
        taken.append((x, y, turn))
        cand = cut(x, y, turn)
        mask = np.ones((PATCH, PATCH), np.float32)
        if left:
            e = (((cand[:, :OVERLAP] - here[:, :OVERLAP]) * LUMA) ** 2).sum(-1)
            mask[:, :OVERLAP] = np.minimum(mask[:, :OVERLAP], seam_mask(e))
        if top:
            e = (((cand[:OVERLAP] - here[:OVERLAP]) * LUMA) ** 2).sum(-1).T
            mask[:OVERLAP, :] = np.minimum(mask[:OVERLAP, :], seam_mask(e).T)
        soft = ndi.gaussian_filter(mask, 2.0)
        soft = np.where(mask > 0, np.maximum(soft, 0.5), soft)
        if not left:
            soft[:, :8] = 1
        if not top:
            soft[:8, :] = 1
        out[top : top + PATCH, left : left + PATCH] = here + (cand - here) * soft[..., None]
        used += 1
    print("row", top, flush=True)
out = out[:OUT_SIZE, :OUT_SIZE]
print("patches", used, "colour mean", out[..., :3].mean((0, 1)), "height std", out[..., 3].std(), flush=True)
np.save(os.path.join(WORK, "scan_stone.npy"), out)
shown = np.clip(out[..., :3], 0, 1) ** (1 / 2.2)
Image.fromarray(np.uint8(shown * 255)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(WORK, "scan_stone_whole.png"))
Image.fromarray(np.uint8(shown[1800:2800, 1800:2800] * 255)).save(os.path.join(WORK, "scan_stone_crop.png"))
print("saved", SCALE, flush=True)
