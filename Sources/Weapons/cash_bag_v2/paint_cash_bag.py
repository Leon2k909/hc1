"""Paint the cash bag's maps from its bakes: python paint_cash_bag.py <work dir> <materials dir>

Faded olive canvas, creased where a stuffed bag creases, stitched along its seams, scuffed dark along its base; black web and zip
tape; bundles of invented banknotes in paper bands. The notes copy no real currency: no portrait, no country, no issuer.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import FONT, OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, BAG, LINING, ZIP, WEB, BILL, BAND = range(15)

pos4 = load("bake_cb_pos")
nor4 = load("bake_cb_nor")
facts4 = load("bake_cb_facts")
ao4 = load("bake_cb_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "cash_bag.json")))
density = meta["density"]
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
print("coverage %.2f" % cover.mean(), "finishes", np.unique(finish).tolist(), flush=True)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


big = field(noise(pts, 0.12, 1, 3))
mid = field(noise(pts, 0.6, 2, 4))
fine = field(noise(pts, 2.6, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
NX, NY, NZ = nor[..., 0], nor[..., 1], nor[..., 2]
YC = -0.21

color = np.zeros((H, W, 3), np.float32)
rough = np.zeros((H, W), np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)

# ---- The canvas. ----
bag = finish == BAG
# Long creases, running round the bag where it's stuffed and fanning from the handles' feet: ridged noise stretched that way.
stretch = np.array((0.5, 2.2, 0.5), np.float32)
# Warped first, or the folds line up in rows like corrugated iron.
warped = pts.copy()
warped[:, 1] += (noise(pts, 0.22, 31, 2) - 0.5) * 7.0
warped[:, 0] += (noise(pts, 0.3, 32, 2) - 0.5) * 3.0
ridge_a = 1 - np.abs(2 * field(noise(warped * stretch, 0.2, 21, 4)) - 1)
ridge_b = 1 - np.abs(2 * field(noise(warped * np.array((1.6, 0.6, 0.6), np.float32), 0.3, 22, 3)) - 1)
creases = smooth(0.62, 0.96, ridge_a) * 0.1 + smooth(0.66, 0.96, ridge_b) * 0.06
# The threads are too fine for this atlas to hold: drawn at their real size they only make moire. This is their mottle instead.
weave = fine
c_height = -creases + 0.008 * (fine - 0.5) + 0.004 * (micro - 0.5)
c_color = mix(flat((98, 96, 72)), flat((124, 120, 94)), smooth(0.25, 0.75, mid * 0.5 + big * 0.5))
# Bleached along what the sun and the handling catch; darker down in the creases.
c_color = mix(c_color, flat((150, 144, 118)), smooth(0.5, 0.95, big + 0.2 * np.clip(NZ, 0, 1)) * 0.38)
c_color = c_color * (1 - smooth(0.7, 0.96, ridge_a)[..., None] * 0.26 - smooth(0.7, 0.96, ridge_b)[..., None] * 0.16)
c_color = c_color * (0.92 + 0.12 * weave[..., None])

# The rubbed base panel, darker and scuffed, with its stitching above it.
base = smooth(2.5, 2.2, Z + (micro - 0.5) * 0.02)
scuffs = smooth(0.48, 0.72, field(noise(pts * np.array((0.4, 0.14, 2.2), np.float32), 0.9, 23, 4)))
c_color = mix(c_color, flat((62, 54, 44)) * (0.8 + 0.4 * mid[..., None]), base)
c_color = mix(c_color, flat((110, 100, 84)), base * scuffs * 0.5)
c_height = c_height + base * 0.018
base_stitch = (np.abs(Z - 2.58) < 0.03) & (np.mod(np.abs(Y) + np.abs(X), 0.22) < 0.13)
# Seams: a run along each side of the zip tape, and round both end panels.
lips = np.load(os.path.join(WORK, "lips.npy"))
# The rows of the mesh are nearly an inch apart: join the dots, or the tape's edge comes out in scallops.
dense = []
for run in (lips[0::2], lips[1::2]):
    for a, b in zip(run, run[1:]):
        dense.append(a + (b - a) * np.linspace(0, 1, 24, endpoint=False)[:, None])
to_lip = field(cKDTree(np.concatenate(dense)).query(pts, k=1, workers=1)[0].astype(np.float32))
tape = smooth(0.62, 0.56, to_lip) * bag * (np.abs(Y - YC) < 10.6)
lip_stitch = (np.abs(to_lip - 0.74) < 0.03) & (np.mod(Y, 0.22) < 0.13) & (np.abs(Y - YC) < 10.4)
end = np.abs(Y - YC)
end_stitch = (np.abs(end - 12.75) < 0.03) & (np.mod(X + Z, 0.22) < 0.13)
stitches = base_stitch | lip_stitch | end_stitch
# Box stitches where the handles land.
for side in (-1, 1):
    for yy in (YC - 4.85, YC + 4.85):
        here = (np.sign(X) == side) & (np.abs(Y - yy) < 0.95) & (np.abs(Z - 3.9) < 1.25)
        border = here & ((np.abs(np.abs(Y - yy) - 0.82) < 0.03) | (np.abs(np.abs(Z - 3.9) - 1.12) < 0.03))
        diag = here & ((np.abs((Y - yy) * 1.3 - (Z - 3.9)) < 0.04) | (np.abs((Y - yy) * 1.3 + (Z - 3.9)) < 0.04))
        stitches = stitches | border | diag
stitch_mask = stitches.astype(np.float32)
c_color = mix(c_color, flat((170, 160, 128)), stitch_mask * 0.82)
c_height = c_height + stitch_mask * 0.012 - smooth(0.14, 0.0, np.abs(to_lip - 0.74)) * 0.006
# Zip tape on the canvas, with the teeth down its middle.
teeth = (0.5 + 0.5 * np.sin(Y * 2 * math.pi / 0.2)) * smooth(0.2, 0.06, to_lip)
c_color = mix(c_color, flat((26, 26, 26)) * (0.8 + 0.3 * fine[..., None]), tape)
c_color = mix(c_color, flat((150, 150, 142)), teeth * tape * 0.8)
c_height = c_height + tape * 0.02 + teeth * tape * 0.02
# Grime in the creases, a stain low down, and dust on the top.
stain = smooth(0.56, 0.78, field(noise(pts, 0.28, 24, 4)))
c_color = c_color * (1 - stain[..., None] * np.array((0.2, 0.22, 0.26), np.float32))
c_color = mix(c_color, flat((142, 128, 100)), smooth(0.5, 0.95, np.clip(NZ, 0, 1) * 0.84 + (big - 0.5) * 0.3) * 0.16)
color = np.where(bag[..., None], c_color, color)
rough = np.where(bag, np.where(tape > 0.5, 0.62, 0.9 + 0.08 * fine), rough)
metal = np.where(bag, teeth * tape * 0.8, metal)
height = np.where(bag, c_height, height)

# Dark lining.
lining = finish == LINING
color = np.where(lining[..., None], flat((30, 32, 28)) * (0.8 + 0.4 * mid[..., None]), color)
rough = np.where(lining, 0.86, rough)
metal = np.where(lining, 0.0, metal)
height = np.where(lining, 0.008 * (fine - 0.5), height)

# The cut edge of the opening: bound in tape.
zip_edge = finish == ZIP
color = np.where(zip_edge[..., None], flat((26, 26, 26)) * (0.8 + 0.3 * fine[..., None]), color)
rough = np.where(zip_edge, 0.62, rough)
metal = np.where(zip_edge, 0.0, metal)

# Web: black nylon herringbone, frayed a little paler at the edges of use.
web = finish == WEB
herring = 0.5 + 0.5 * np.sin((X + Y + Z) * 2 * math.pi / 0.16) * np.sign(np.sin((X - Y) * 2 * math.pi / 0.5))
w_color = flat((34, 34, 32)) * (0.74 + 0.34 * herring[..., None] + 0.3 * mid[..., None])
w_color = mix(w_color, flat((94, 90, 74)), smooth(0.62, 0.84, big * 0.5 + fine * 0.5) * 0.34)
color = np.where(web[..., None], w_color, color)
rough = np.where(web, 0.84, rough)
metal = np.where(web, 0.0, metal)
height = np.where(web, 0.008 * herring + 0.002 * (micro - 0.5), height)

# Rubber wrap and pulls.
rubber = finish == RUBBER
color = np.where(rubber[..., None], flat((26, 26, 26)) * (0.72 + 0.5 * fine[..., None]), color)
rough = np.where(rubber, 0.66 + 0.16 * fine, rough)
metal = np.where(rubber, 0.0, metal)
height = np.where(rubber, 0.003 * (fine - 0.5), height)

# Plated hardware.
zinc = finish == ZINC
z_color = flat((170, 170, 164)) * (0.5 + 0.36 * mid[..., None])
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, 0.32 + 0.22 * fine, rough)
metal = np.where(zinc, 1.0, metal)
height = np.where(zinc, 0.001 * (micro - 0.5), height)


# ---- The cash, on each bundle's own axes. ----
def note_art(size=(600, 260)):
    w, h = size
    img = Image.new("RGB", size, (178, 190, 160))
    d = ImageDraw.Draw(img)
    ink = (56, 86, 62)
    for k in range(0, w, 5):
        d.line((k, 0, k + 26, h), fill=(166, 180, 150), width=1)
    d.rectangle((10, 10, w - 11, h - 11), outline=ink, width=7)
    d.rectangle((24, 24, w - 25, h - 25), outline=ink, width=2)
    for r in range(100, 20, -9):
        d.ellipse((w * 0.5 - r, h * 0.5 - r * 0.92, w * 0.5 + r, h * 0.5 + r * 0.92), outline=ink, width=2)
    font = ImageFont.truetype(FONT, 76)
    big_font = ImageFont.truetype(FONT, 100)
    for text, x, y, f in (("100", 86, 66, font), ("100", w - 86, h - 66, font), ("100", w * 0.5, h * 0.5, big_font)):
        bb = d.textbbox((0, 0), text, font=f)
        d.text((x - (bb[2] - bb[0]) / 2 - bb[0], y - (bb[3] - bb[1]) / 2 - bb[1]), text, ink, font=f)
    a = np.asarray(img, np.float32) / 255.0
    return a


art = note_art()
art_channels = [art[..., c] for c in range(3)]
b_color = np.zeros((H, W, 3), np.float32)
b_height = np.zeros((H, W), np.float32)
for item in meta["bundles"]:
    here = (finish == BILL) & (np.abs(part - item["rand"]) < 1.5e-4)
    if not here.any():
        continue
    m = np.array(item["to_local"], np.float32)
    local = pos @ m[:3, :3].T + m[:3, 3]
    lx, ly, lz = local[..., 0], local[..., 1], local[..., 2]
    face_on = np.abs(lz) > 0.47
    # A note's long side runs along the bundle. Each bundle sits a touch differently in its band.
    uu, vv = 0.5 + ly / 6.16, 0.5 + lx / 2.72
    note = np.stack([sample_image(ch, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) for ch in art_channels], -1)
    note = note ** 2.2
    # The sides are the edges of a hundred sheets.
    sheets = 0.5 + 0.5 * np.sin(lz * 2 * math.pi / 0.05)
    edges = srgb_to_linear((186, 188, 164)) * (0.5 + 0.5 * sheets[..., None]) * (0.86 + 0.2 * fine[..., None])
    tone = note * (0.84 + 0.24 * mid[..., None])
    b_color = np.where(here[..., None], np.where(face_on[..., None], tone, edges), b_color)
    b_height = np.where(here, np.where(face_on, 0.002 * (micro - 0.5), 0.008 * sheets), b_height)
bill = finish == BILL
color = np.where(bill[..., None], b_color, color)
rough = np.where(bill, 0.74 + 0.12 * fine, rough)
metal = np.where(bill, 0.0, metal)
height = np.where(bill, b_height, height)

# Paper bands, mustard, with no print worth reading at this size.
band = finish == BAND
color = np.where(band[..., None], flat((196, 164, 82)) * (0.84 + 0.22 * mid[..., None]), color)
rough = np.where(band, 0.7, rough)
metal = np.where(band, 0.0, metal)
height = np.where(band, 0.002 * (micro - 0.5), height)

color = color * (0.72 + 0.28 * ao[..., None])
# Fill the gutters from every covered texel: eroding first would lose bevel strips a pixel or two wide.
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "cb_bag_color.png"), color)
save_gray(os.path.join(OUT, "cb_bag_rough.png"), rough)
save_gray(os.path.join(OUT, "cb_bag_metal.png"), metal)
save_gray(os.path.join(OUT, "cb_bag_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "cb_bag_normal.png"), normal)
print("cash bag painted", flush=True)
