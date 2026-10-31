"""Paint one sofa length's maps from its bakes: python paint_sofa.py <work dir> <materials dir> <length>

An ivory frame and warm tan cushions, as the old one's two colours were, in real upholstery: a looped frame cloth, a woven
cushion cloth, seams gathered into their piping, creases where people sit, teal and ochre pillows, a dark plinth with brass.
It's a hotel's sofa, so it's looked after: use shows as sit marks and a little fading, not damage.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

BODY, CUSHION, PIPE, ACCENT_A, ACCENT_B, BLACK, BRASS_TRIM = range(7)
LENGTH = int(sys.argv[3])
NAME = f"sofa_{LENGTH}"
facts = json.load(open(os.path.join(WORK, "sofa.json")))
density = facts["density"]

pos4 = load("bake_sofa_pos")
nor4 = load("bake_sofa_nor")
facts4 = load("bake_sofa_facts")
ao4 = load("bake_sofa_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = ((pos4[..., :3] - 0.5) * 400.0).astype(np.float32)
nor = (nor4[..., :3] * 2 - 1).astype(np.float32)
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1].astype(np.float32)
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0].astype(np.float32)
del pos4, nor4, facts4, ao4
print("loaded", cover.mean(), np.unique(finish), flush=True)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=1)] = 0
edge = np.clip(ndi.gaussian_filter(np.clip((curve - 0.5) * 0.5, 0, 1), 1.6) * 3.0, 0, 1).astype(np.float32)
rows, cols = np.nonzero(cover)
pts = pos[rows, cols]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[rows, cols] = values
    return out


def C(r, g, b):
    return srgb_to_linear((r, g, b)).astype(np.float32)


def flat(c):
    return np.broadcast_to(c, (H, W, 3))


def blend(a, b, t):
    return a + (b - a) * t[..., None]


big = field(noise(pts, 0.1, 1, 3))
mid = field(noise(pts, 0.6, 2, 3))
fine = field(noise(pts, 2.6, 3, 3))
micro = field(noise(pts, 7.0, 4, 2))
crevice = np.clip((1 - ao) * 1.5, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
print("fields", flush=True)

# Creases run round each soft shape, with a stretch of their own per part, and gather hard into the seams.
offset = part[rows, cols][:, None] * np.array((53.0, 19.0, 71.0), np.float32)
folds = field(noise(pts * np.array((0.75, 0.2, 0.75), np.float32) + offset, 1.0, 21, 3))
creases = np.abs(folds - 0.5) * 2
crease_lines = smooth(0.22, 0.02, creases) * smooth(0.25, 0.6, mid)
seam_points = np.array(facts["seams"], np.float32)
samples = []
for k in range(len(seam_points) - 1):
    a, b = seam_points[k], seam_points[k + 1]
    gap = float(np.linalg.norm(b - a))
    if gap < 6.0:  # Consecutive seams aren't joined.
        samples.append(np.linspace(a, b, max(2, int(gap / 0.3))))
samples = np.vstack(samples)
dist, _ = cKDTree(samples).query(pts, k=1, workers=1)
near = field(dist.astype(np.float32))
gather_band = smooth(2.6, 0.2, near)
pucker = field(np.sin(noise(pts * np.array((1.6, 1.6, 1.6), np.float32) + offset, 1.0, 22, 2) * 46.0)) * 0.5 + 0.5
print("creases", flush=True)

# Two weaves. Neither may go finer than about three texels, or it turns to moire.
pitch = max(2.0, min(3.2, density / 4.0))
loops = field(noise(pts * pitch * 3.0, 1.0, 23, 1))
weave = (np.sin(X * 2 * math.pi * pitch) + np.sin(Y * 2 * math.pi * pitch) + np.sin(Z * 2 * math.pi * pitch)) / 6 + 0.5
weave = weave.astype(np.float32)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.8, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)


def apply(mask, c, r, m=None, h=None):
    color[mask] = c[mask] if getattr(c, "ndim", 1) == 3 else c
    rough[mask] = r[mask] if getattr(r, "ndim", 0) == 2 else r
    if m is not None:
        metal[mask] = m[mask] if getattr(m, "ndim", 0) == 2 else m
    if h is not None:
        height[mask] = h[mask] if getattr(h, "ndim", 0) == 2 else h


shape = (folds - 0.5) * 0.07 + (big - 0.5) * 0.03 - crease_lines * 0.035 - gather_band * pucker * 0.05

# The frame: looped ivory, a touch brighter where the light has faded it, greyer where hands go.
body = finish == BODY
b_color = flat(C(204, 194, 174)) * (0.93 + 0.14 * loops[..., None]) * (0.975 + 0.05 * mid[..., None])
b_color = blend(b_color, flat(C(216, 208, 192)), smooth(0.35, 0.85, upward) * 0.25)
hands = smooth(21.5, 24.0, Z) * (np.abs(Y) > LENGTH / 2 - 8.5)
b_color = blend(b_color, flat(C(172, 162, 146)), hands * 0.3)
apply(body, b_color, 0.9 + 0.06 * loops, 0.0, shape * 0.8 + loops * 0.012)

# The cushions: a warm woven tan, darker and a little polished where people sit and lean.
cushion = finish == CUSHION
c_color = blend(flat(C(150, 116, 88)), flat(C(138, 104, 78)), smooth(0.25, 0.75, big))
c_color = c_color * (0.955 + 0.09 * weave[..., None]) * (0.98 + 0.04 * fine[..., None])
sit_top = smooth(0.6, 0.9, upward) * smooth(9.0, 2.0, np.abs(X - 4.0)) * (Z < 22.0)
sit_back = smooth(0.5, 0.9, nor[..., 0]) * (Z > 18.0) * smooth(6.0, 1.0, np.abs(Z - 25.0))
wear = np.clip(sit_top + sit_back, 0, 1)
c_color = blend(c_color, c_color * 0.86, wear * 0.55)
c_color = blend(c_color, c_color * 0.82, crease_lines * 0.35)
c_rough = 0.86 + 0.06 * weave - wear * 0.14
apply(cushion, c_color, c_rough, 0.0, shape + weave * 0.007)

# Piping, a shade darker than what it edges, and rubbed pale along its outside.
pipe = finish == PIPE
arm_pipe = np.abs(Y) > LENGTH / 2 - 8.4
p_color = np.where(arm_pipe[..., None], flat(C(150, 138, 118)), flat(C(84, 60, 44)))
p_color = blend(p_color, flat(C(176, 150, 118)), smooth(0.45, 0.8, fine) * 0.25)
apply(pipe, p_color, 0.74, 0.0, 0.0)

# Pillows: a deep teal and a burnt ochre.
for finish_id, base, dark in ((ACCENT_A, C(30, 88, 96), C(18, 56, 64)), (ACCENT_B, C(198, 130, 40), C(142, 86, 24))):
    mask = finish == finish_id
    a_color = blend(flat(base), flat(dark), smooth(0.25, 0.75, big) * 0.25) * (0.94 + 0.12 * weave[..., None])
    a_color = blend(a_color, a_color * 0.8, crease_lines * 0.35)
    apply(mask, a_color, 0.84 + 0.06 * weave, 0.0, shape * 0.9 + weave * 0.007)

# The plinth, satin black and scuffed by shoes low down; its brass trim tarnished, bright where it's touched.
plinth = finish == BLACK
scuff = smooth(0.62, 0.8, field(noise(pts * np.array((0.3, 0.15, 3.0), np.float32), 1.0, 24, 3)))
k_color = flat(C(24, 24, 26)) * (0.8 + 0.4 * mid[..., None])
k_color = blend(k_color, flat(C(84, 84, 84)), scuff * 0.5)
apply(plinth, k_color, 0.46 + 0.2 * mid + scuff * 0.2, 0.55 * (1 - scuff), 0.002 * (fine - 0.5))
trim = finish == BRASS_TRIM
touch = smooth(0.42, 0.74, edge * 0.6 + (mid - 0.5) * 0.7 + (fine - 0.5) * 0.5)
t_color = blend(flat(C(118, 96, 56)), flat(C(196, 166, 104)), touch)
apply(trim, t_color, 0.3 + 0.24 * (1 - touch), 1.0, 0.001 * (micro - 0.5))
print("cloth", flush=True)

# A light dusting on top, and grime only where cloth meets the plinth.
dust = smooth(0.7, 0.95, upward) * smooth(0.55, 0.9, big) * 0.14
low = smooth(9.0, 4.0, Z) * ~plinth * ~trim
color = blend(color, flat(C(150, 140, 122)), dust)
color = blend(color, color * 0.86, low * 0.5)

color = color * (0.66 + 0.34 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.6), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
half = lambda a: (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), half(metal))
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), half(np.clip(ao * 1.03, 0, 1)))
print("sofa painted", flush=True)
