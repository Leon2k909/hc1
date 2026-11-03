"""Paint the pallet's maps from its bakes and a real wood scan: python paint_pallet.py <work dir> <output dir>

A pallet that has done the rounds of a hydro plant's yard: weathered softwood, each board from its own place in a real scan
(Poly Haven's CC0 wood_planks, in Assets/materials/forestbase/scans) at its true scale, one paler board where it was mended, sawn
end grain, nails rusting into the wood, and dirt from the yard floor on the underside and low down. Wear is worked out in 3D.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from PIL import Image  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

PINE, NAIL = 12, 3
SCAN = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans", "wood_planks")
# The scan's planks lie across it in bands between these gap rows; about 225 px is a 6.25 in plank.
GAPS = [0, 279, 512, 761, 968, 1179, 1426, 1634, 1844, 2048]
SCAN_PPI = 36.0
MARGIN = 9
NAME = "pallet"

facts = json.load(open(os.path.join(WORK, "pallet.json")))
density, RANGE, HEIGHT, TOP, BOTTOM = (facts[k] for k in ("density", "range", "height", "top", "bottom"))
boards = facts["boards"]

pos4 = load("bake_pl_pos")
nor4 = load("bake_pl_nor")
facts4 = load("bake_pl_facts")
ao4 = load("bake_pl_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
pts = pos[cover]
print("covered %.3f" % cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

TURN = np.array(((0.70, -0.42, 0.58), (0.61, 0.77, -0.19), (-0.37, 0.48, 0.79)), np.float32)


def noise(p, freq, seed=0, octaves=1):
    return lattice_noise(p @ TURN, freq, seed, octaves)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


# ---- The scan: colour in linear light, height integrated from its normal map, roughness and its own AO. ----
def integrate(nx, ny):
    """Height in pixels from a normal map's slopes (Frankot-Chellappa), as the headstones' scan_stone.py does."""
    h, w = nx.shape
    wx = np.fft.fftfreq(w) * 2 * np.pi
    wy = np.fft.fftfreq(h) * 2 * np.pi
    u, v = np.meshgrid(wx, wy)
    denom = u * u + v * v
    denom[0, 0] = 1.0
    return np.fft.ifft2((-1j * u * np.fft.fft2(-nx) - 1j * v * np.fft.fft2(ny)) / denom).real.astype(np.float32)


cache = os.path.join(WORK, "scan_wood.npz")
if os.path.exists(cache):
    got = np.load(cache)
    s_col, s_height, s_rough, s_ao = got["col"], got["height"], got["rough"], got["ao"]
else:
    s_col = srgb_to_linear(np.asarray(Image.open(SCAN + "_diff.jpg"))[..., :3].astype(np.float32)).astype(np.float32)
    n = np.asarray(Image.open(SCAN + "_nor_gl.jpg"))[..., :3].astype(np.float32) / 255.0 * 2 - 1
    s_height = integrate(n[..., 0] / np.maximum(n[..., 2], 0.25), n[..., 1] / np.maximum(n[..., 2], 0.25))
    # Only the grain's own relief: broad drift from the integration would tilt whole boards.
    s_height = (s_height - ndi.gaussian_filter(s_height, 30)) / SCAN_PPI
    s_rough = np.asarray(Image.open(SCAN + "_rough.jpg")).astype(np.float32) / 255.0
    s_ao = np.asarray(Image.open(SCAN + "_ao.jpg")).astype(np.float32) / 255.0
    np.savez(cache, col=s_col, height=s_height, rough=s_rough, ao=s_ao)
SH, SW = s_height.shape
print("scan loaded", flush=True)

# ---- Which board each texel is on, and where on it, in the board's own frame. ----
rand_of = {round(b["rand"], 4): k for k, b in enumerate(boards)}
which = np.full(cover.shape, -1, np.int32)
keys = np.round(part, 4)
for r, k in rand_of.items():
    which[np.abs(keys - r) < 5e-5] = k
print("unmatched texels %.4f" % ((which < 0) & cover).mean(), flush=True)

rng = np.random.default_rng(907)
along_c = np.zeros((H, W), np.float32)  # Inches along the board from its start.
across_c = np.zeros((H, W), np.float32)  # Inches across the face, from its edge.
face_kind = np.zeros((H, W), np.int32)  # 0 broad face, 1 narrow edge, 2 end grain.
end_r = np.zeros((H, W), np.float32)  # Distance from the pith, for end grain rings.
board_tone = np.ones((H, W), np.float32)
board_grey = np.zeros((H, W), np.float32)
mended = np.zeros((H, W), bool)
scan_row = np.zeros((H, W), np.float32)
scan_col = np.zeros((H, W), np.float32)
bands = list(range(len(GAPS) - 1))
rng.shuffle(bands)
# The second top board was put in later: paler, yellower, barely weathered. It is off-centre, so a pallet turned end for end differs.
MENDED = "top board 1"
for k, b in enumerate(boards):
    sel = which == k
    if not sel.any():
        continue
    p = pos[sel]
    nn = nor[sel]
    c = np.radians(-b["turn"])
    cx, cy = b["centre"]
    x = (p[:, 0] - cx) * np.cos(c) - (p[:, 1] - cy) * np.sin(c)
    y = (p[:, 0] - cx) * np.sin(c) + (p[:, 1] - cy) * np.cos(c)
    nx = nn[:, 0] * np.cos(c) - nn[:, 1] * np.sin(c)
    ny = nn[:, 0] * np.sin(c) + nn[:, 1] * np.cos(c)
    z = p[:, 2]
    lo, hi = np.array(b["lo"]), np.array(b["hi"])
    if b["along"] == "y":
        length, across, wide_up = y - (lo[1] - cy), x - (lo[0] - cx), True
        n_along, n_across, ends = ny, nx, (x - 0.0, z - (lo[2] + hi[2]) / 2)
    else:
        length, across, wide_up = x - lo[0], z - lo[2], False
        n_along, n_across, ends = nx, ny, (y - 0.0, z - (lo[2] + hi[2]) / 2)
    kind = np.where(np.abs(n_along) > 0.7, 2, 0)
    if wide_up:
        # Deck boards: their top and bottom are broad, their long sides narrow.
        kind = np.where((kind == 0) & (np.abs(nn[:, 2]) < 0.6), 1, kind)
        across_here = np.where(kind == 1, z - lo[2], across)
    else:
        # Stringers: their sides are broad, their top and underside narrow.
        kind = np.where((kind == 0) & (np.abs(nn[:, 2]) > 0.6), 1, kind)
        across_here = np.where(kind == 1, y - (lo[1] - cy) - 0.0, across)
    band = bands[k % len(bands)]
    top_px, bottom_px = GAPS[band] + MARGIN, GAPS[band + 1] - MARGIN
    room = (bottom_px - top_px) / SCAN_PPI
    span = float(hi[0] - lo[0]) if b["along"] == "y" else float(hi[2] - lo[2])
    squeeze = min(1.0, room / max(span, 0.1))
    # Each face of a board from its own stretch of the plank, so the top and underside differ.
    side = np.where(kind == 2, 0, np.where(nn[:, 2] > 0.6, 0, np.where(nn[:, 2] < -0.6, 1, np.where(n_across > 0, 2, 3))))
    start = rng.uniform(0, max(1.0, SW - 1 - 50 * SCAN_PPI), 4)
    flip = rng.random() < 0.5
    col = start[side] + length * SCAN_PPI
    if flip:
        col = SW - 1 - col
    row = top_px + np.clip(across_here, 0, span) * squeeze * SCAN_PPI
    scan_row[sel] = row
    scan_col[sel] = np.clip(col, 0, SW - 1)
    along_c[sel] = length
    across_c[sel] = across_here
    face_kind[sel] = kind
    # End grain: rings round a pith that's off the board, as a board is sawn from beside the heart.
    px, pz = rng.uniform(-9, 9), rng.uniform(-14, -6)
    end_r[sel] = np.hypot(ends[0] - px, ends[1] - pz)
    board_tone[sel] = rng.uniform(0.86, 1.1)
    board_grey[sel] = rng.uniform(0.0, 0.32)
    if b["name"] == MENDED:
        mended[sel] = True

pine = finish == PINE
nail_f = finish == NAIL
coords = (scan_row, scan_col)


def scan(image):
    return ndi.map_coordinates(image, coords, order=1, mode="nearest").astype(np.float32)


wood = np.stack([scan(s_col[..., c]) for c in range(3)], -1)
w_height = scan(s_height)
w_rough = scan(s_rough)
w_ao = scan(s_ao)

X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
big = field(noise(pts, 0.05, 1, 3))
mid = field(noise(pts, 0.35, 2, 4))
fine = field(noise(pts, 2.0, 3, 3))
micro = field(noise(pts, 6.5, 4, 2))
crevice = np.clip((1 - ao) * 1.4, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
downward = np.clip(-nor[..., 2], 0, 1)

edge_points = np.load(os.path.join(WORK, "pallet_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=1.0, workers=4)
edge = smooth(0.22, 0.02, field(np.where(np.isfinite(d), d, 1.0).astype(np.float32)))

# Weathered boards go silver-grey on top, where the sun and rain reach them, and stay browner underneath.
lum = (wood * np.array((0.2126, 0.7152, 0.0722), np.float32)).sum(-1, keepdims=True)
weather = np.clip(board_grey + upward * 0.18 - downward * 0.12 + (big - 0.5) * 0.3, 0, 0.6)
timber = mix(wood, lum * np.array((1.02, 1.0, 0.95), np.float32) * 1.05, weather) * board_tone[..., None]

# The mended board: new softwood, pale and yellow, with the scan's grain kept but lifted.
fresh = (lum / max(float(lum[pine].mean()), 1e-3)) * srgb_to_linear((196, 160, 112)).astype(np.float32)
timber = np.where(mended[..., None], mix(timber, fresh, 0.82), timber)

# End grain: darker, drinks the dirt, rings a fraction of an inch apart and the saw's marks across them.
rings = 0.5 + 0.5 * np.sin(end_r * 2 * np.pi / 0.16 + field(noise(pts, 1.1, 21, 2)) * 5.0)
saw = 0.5 + 0.5 * np.sin((Z * 0.9 + X * 0.25 + Y * 0.25) * 2 * np.pi / 0.09)
endc = face_kind == 2
end_tone = mix(rgb(92, 66, 42), rgb(58, 40, 25), np.clip(rings * 0.6 + saw * 0.2 + (fine - 0.5) * 0.6, 0, 1))
timber = np.where(endc[..., None], mix(timber * 0.62, end_tone, 0.5), timber)

# Arrises rubbed bright where forks and boots catch them, kept soft so they don't read as dashes.
rub = ndi.gaussian_filter(edge * smooth(0.4, 0.78, big * 0.5 + mid * 0.5), 1.2) * pine
timber = mix(timber, timber * 1.28 + rgb(10, 8, 5), np.clip(rub * 0.5, 0, 0.6))

# Nails: dark heads, and rust bled into the wood round them and along the grain.
nails = np.load(os.path.join(WORK, "pallet_nails.npy"))
dist, _ = cKDTree(nails).query(pts, k=1, distance_upper_bound=1.2, workers=4)
nd = field(np.where(np.isfinite(dist), dist, 2.0).astype(np.float32))
head = smooth(0.2, 0.14, nd) * pine
halo = smooth(0.75, 0.16, nd) * pine * smooth(0.25, 0.65, fine * 0.6 + mid * 0.4)
timber = mix(timber, rgb(88, 46, 22), halo * 0.55)
timber = mix(timber, rgb(46, 40, 36) * (0.8 + 0.5 * micro[..., None]), head)

# The yard's floor: grime on the undersides and low down, dust settled in the gaps and corners, a few old wet stains.
low = smooth(1.6, 0.0, Z)
under = downward * smooth(0.3, 0.7, mid)
gathered = smooth(0.2, 0.65, crevice) * smooth(0.3, 0.75, mid * 0.6 + fine * 0.4)
stain = smooth(0.62, 0.74, field(noise(pts, 0.11, 9, 3))) * pine * ~endc
grime = np.clip(low * 0.55 + under * 0.45 + gathered * 0.45, 0, 0.75)
timber = mix(timber, timber * 0.55, stain * 0.5)
color = mix(timber, rgb(58, 52, 45) * (0.8 + 0.4 * fine[..., None]), grime)
color = np.where(nail_f[..., None], rgb(52, 48, 44), color)
color = color * (0.62 + 0.38 * ao[..., None]) * (0.85 + 0.15 * w_ao[..., None])

rough = np.clip(w_rough * 0.96 + weather * 0.05 + grime * 0.05 - head * 0.25 + endc * 0.04, 0.5, 1.0)
rough = np.where(mended, rough - 0.06, rough)
metal = np.clip(head * 0.55, 0, 1)
# The scan's relief, a little proud on the nail heads, rough on the sawn ends.
height = np.where(pine, w_height * 1.4 + head * 0.025 - halo * 0.003, 0.0)
height = np.where(endc, 0.004 * (rings - 0.5) + 0.003 * (saw - 0.5) + 0.002 * (micro - 0.5), height)

normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("pallet painted", flush=True)
