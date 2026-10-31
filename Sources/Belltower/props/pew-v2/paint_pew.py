"""Paint the pew's maps from its bakes: python paint_pew.py <work dir> <materials dir> pew

Old dark oak: a hundred and fifty years of wax over warm timber, the grain running the way each member's wood runs. It's worn pale
and polished where hands and backs go, on the top rail and the seat's front edge, and dull and scuffed low down, where shoes go.
Deep red seat pads, faded where people sit. Every word is made up: the plates carry only pew numbers.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

GRAIN_X, GRAIN_Y, GRAIN_Z, PAD, BOOK, BRASS_TRIM, PIPE = range(7)
NAME = "pew"
facts = json.load(open(os.path.join(WORK, "pew.json")))
density = facts["density"]

pos4 = load("bake_pew_pos")
nor4 = load("bake_pew_nor")
facts4 = load("bake_pew_facts")
ao4 = load("bake_pew_ao")
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
edge = np.clip(ndi.gaussian_filter(np.clip((curve - 2.0) * 0.4, 0, 1), 1.4) * 2.6 + ndi.gaussian_filter(np.clip((curve - 2.0) * 0.4, 0, 1), 3.5) * 2.4, 0, 1).astype(np.float32)
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


big = field(noise(pts, 0.09, 1, 3))
mid = field(noise(pts, 0.55, 2, 3))
fine = field(noise(pts, 2.6, 3, 3))
micro = field(noise(pts, 7.0, 4, 2))
crevice = np.clip((1 - ao) * 1.4, 0, 1)
upward = np.clip(nor[..., 2], 0, 1)
print("fields", flush=True)

# The grain, with each member's own stretch of the tree.
woods = np.isin(finish, (GRAIN_X, GRAIN_Y, GRAIN_Z))
wr, wc = np.nonzero(woods & cover)
wp = pos[wr, wc]
wf = finish[wr, wc]
gdir = np.zeros_like(wp)
gdir[wf == GRAIN_X] = (1, 0, 0)
gdir[wf == GRAIN_Y] = (0, 1, 0)
gdir[wf == GRAIN_Z] = (0, 0, 1)
along = (wp * gdir).sum(1, keepdims=True)
perp = wp - along * gdir
offset = part[wr, wc][:, None] * np.array((131.0, 57.0, 91.0), np.float32)


def wood_field(values):
    out = np.zeros((H, W), np.float32)
    out[wr, wc] = values
    return out


q = perp * 4.6 + gdir * along * 0.07 + offset
grain = wood_field(noise(q, 1.0, 31, 3))
lines = 0.5 + 0.5 * np.sin(grain * 18.0)
figure = wood_field(noise(perp * 0.5 + gdir * along * 0.03 + offset, 1.0, 32, 2))
# Oak's medullary flecks: short, pale and running with the grain.
fleck = wood_field(smooth(0.68, 0.78, noise(perp * 3.6 + gdir * along * 0.4 + offset, 1.0, 33, 2)))
del wp, wf, gdir, along, perp, offset, q
print("grain", flush=True)

timber = woods
oak = blend(flat(C(102, 68, 40)), flat(C(66, 42, 25)), np.clip(lines * 0.7 + (figure - 0.5) * 0.45, 0, 1))
oak = oak * (0.88 + 0.24 * part[..., None])
oak = blend(oak, flat(C(140, 98, 60)), fleck * 0.22)
# Where hands and backs go: the top rail, the bench ends' scrolls and the seat's front edge.
top_rail = smooth(35.4, 37.0, Z) * (X < -2.6)
seat_edge = smooth(6.5, 8.8, X) * smooth(15.4, 16.4, Z) * smooth(19.4, 18.0, Z)
scroll = smooth(19.0, 24.0, Z) * (np.abs(Y) > 47.5)
touched = np.clip(top_rail * 0.9 + seat_edge * 0.8 + scroll * 0.7, 0, 1) * smooth(0.25, 0.6, mid + edge * 0.4)
oak = blend(oak, oak * 1.5 + flat(C(46, 32, 20)), touched * 0.62)
# Edges wear back to paler wood; shoes scuff the lower rails.
worn = smooth(0.42, 0.7, edge + (fine - 0.5) * 0.5)
oak = blend(oak, flat(C(140, 100, 62)) * (0.8 + 0.4 * fine[..., None]), worn * 0.55)
low = smooth(9.0, 1.5, Z)
scuff = low * smooth(0.5, 0.72, field(noise(pts * np.array((0.8, 0.25, 2.8), np.float32), 1.0, 41, 3)))
oak = blend(oak, flat(C(96, 80, 62)), scuff * 0.55)
# Wax and dirt collect in the mouldings.
oak = blend(oak, oak * 0.42, smooth(0.32, 0.8, crevice) * 0.8)
# Tongue-and-groove lines on the back's seat side, and the seat board's joint.
boards = (np.abs(nor[..., 0]) > 0.7) & (X > -6.1) & (X < -5.0) & (Z > 19.2) & (Z < 34.5)
v_joint = smooth(0.92, 0.985, np.abs(np.sin(Y * np.pi / 5.2))) * boards
oak = blend(oak, oak * 0.3, v_joint)
w_rough = 0.36 + 0.14 * lines + 0.1 * mid + scuff * 0.3 + worn * 0.1 - touched * 0.16 + smooth(0.45, 0.9, crevice) * 0.2
w_height = 0.007 * (grain - 0.5) + 0.0025 * (micro - 0.5) - v_joint * 0.05 - fleck * 0.002 - scuff * 0.004
color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.7, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)
color[timber] = oak[timber]
rough[timber] = w_rough[timber]
height[timber] = w_height[timber]
del oak, w_rough, w_height, lines, figure, grain, fleck, worn, scuff, v_joint, boards
print("oak", flush=True)

# The seat pads: deep red wool, faded and flattened where people sit.
pad = finish == PAD
weave = (np.sin(X * 2 * np.pi * 3.0) + np.sin(Y * 2 * np.pi * 3.0) + np.sin(Z * 2 * np.pi * 3.0)) / 6 + 0.5
offset_ = part[rows, cols][:, None] * np.array((53.0, 19.0, 71.0), np.float32)
folds = field(noise(pts * np.array((0.3, 0.3, 0.6), np.float32) + offset_, 1.0, 21, 2))
sat = smooth(0.7, 0.95, upward) * smooth(0.3, 0.7, field(noise(pts * np.array((0.3, 0.12, 0.3), np.float32), 1.0, 42, 2)))
p_color = blend(flat(C(124, 24, 28)), flat(C(106, 18, 24)), smooth(0.25, 0.75, big)) * (0.95 + 0.1 * weave[..., None])
p_color = blend(p_color, flat(C(140, 58, 54)), sat * 0.26)
color[pad] = p_color[pad]
rough[pad] = (0.88 + 0.08 * weave - sat * 0.1)[pad]
height[pad] = ((folds - 0.5) * 0.05 + weave * 0.006)[pad]
pipe = finish == PIPE
color[pipe] = (flat(C(70, 14, 18)) * (0.8 + 0.4 * fine[..., None]))[pipe]
rough[pipe] = 0.74
# Hymn books: cloth boards in dull colours, one each, with paler page blocks on their fore-edges.
books = finish == BOOK
palette = np.array([C(40, 52, 88), C(84, 22, 24), C(30, 62, 44), C(58, 40, 28)], np.float32)
pick = palette[(part * 40).astype(np.int32) % 4]
b_color = pick * (0.82 + 0.3 * fine[..., None])
pages = (np.abs(nor[..., 2]) > 0.7) | (nor[..., 0] > 0.7)
b_color = np.where(pages[..., None], flat(C(176, 160, 128)) * (0.8 + 0.3 * micro[..., None]), b_color)
b_color = blend(b_color, flat(C(150, 130, 96)), smooth(0.5, 0.8, edge + (fine - 0.5) * 0.3) * 0.5)
color[books] = b_color[books]
rough[books] = 0.72
# Brass pew plates, tarnished.
trim = finish == BRASS_TRIM
touch = smooth(0.35, 0.74, (mid - 0.5) * 0.7 + (fine - 0.5) * 0.5 + 0.5)
t_color = blend(flat(C(112, 90, 50)), flat(C(190, 160, 96)), touch)
color[trim] = t_color[trim]
rough[trim] = (0.3 + 0.24 * (1 - touch))[trim]
metal[trim] = 1.0
print("rest", flush=True)

# Dust on the ledges nobody polishes.
ledge = smooth(0.7, 0.95, upward) * (1 - touched) * smooth(0.45, 0.85, big) * 0.22
color = blend(color, flat(C(120, 108, 90)), ledge)
rough = rough * (1 - ledge) + 0.8 * ledge

color = color * (0.62 + 0.38 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
half = lambda a: (a[::2, ::2] + a[1::2, ::2] + a[::2, 1::2] + a[1::2, 1::2]) / 4
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), half(metal))
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), half(np.clip(ao * 1.03, 0, 1)))
print("pew painted", flush=True)
