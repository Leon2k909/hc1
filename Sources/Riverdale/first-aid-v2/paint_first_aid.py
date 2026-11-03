"""Paint the first aid cabinet's maps from its bakes: python paint_first_aid.py <work dir> <output dir> [scans]

A plant's safety cabinet, years on a concrete wall and opened now and then. Deep bottle green stoved enamel, glossy, knocked to primer and steel at its edges and rubbed dull round the handle. A riveted sign
plate in saturated safety green with hard white print, sun-yellowed a little and scratched, its corners worn to aluminium. Dust lies on what faces up. Masks are kept tight rather than soft and the values strong:
the old box's mid-tone flat paint is what read as pastel. Rust is only ever at a chip or a rivet, in small amounts. Worked out in 3D from the baked position of each texel.
With "scans", the enamel's mottle, the shapes of its chips and scratches, and its dulled patches come from the photo scans in forestbase/scans (CC0), as the eye wash's do, and the sign plate takes a little of the same.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise as lattice_noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

ENAMEL, ZINC, BRASS, RUBBER, PLATE = 0, 3, 4, 5, 7
RATING, SEAL, TAG = 9, 12, 13
facts_file = json.load(open(os.path.join(WORK, "first_aid.json")))
density, RANGE = facts_file["density"], facts_file["range"]
HY, Z0, Z1, DOOR = (facts_file[k] for k in ("hy", "z0", "z1", "door"))
SY0, SY1, SZ0, SZ1, ST = facts_file["sign"]
LOCK_Y, LOCK_Z = facts_file["lock"]
RY0, RY1, RZ0, RZ1 = facts_file["rating"]
NAME = "first_aid"
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"

pos4 = load("bake_fa_pos")
nor4 = load("bake_fa_nor")
facts4 = load("bake_fa_facts")
ao4 = load("bake_fa_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
weight = facts4[..., 2]
pos, nor, finish, part, weight = fill_from(cover, pos, nor, finish, part, weight)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)

TURN = np.array(((0.70, -0.42, 0.58), (0.61, 0.77, -0.19), (-0.37, 0.48, 0.79)), np.float32)


def noise(p, freq, seed=0, octaves=1):
    return lattice_noise(p @ TURN, freq, seed, octaves)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


def soft(mask, sigma=0.5):
    return ndi.gaussian_filter(mask.astype(np.float32), sigma)


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
enamel = finish == ENAMEL
zinc = finish == ZINC
brass = finish == BRASS
rubber = finish == RUBBER
plate = finish == PLATE
rating = finish == RATING
seal = finish == SEAL
tag = finish == TAG
front = nor[..., 0] > 0.6
upward = np.clip(nor[..., 2], 0, 1)

edge_points = np.load(os.path.join(WORK, "first_aid_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=0.5, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 0.5).astype(np.float32))
edge = smooth(0.16, 0.015, edge_d)
print("edges", flush=True)

big = field(noise(pts, 0.14, 1, 3))
mid = field(noise(pts, 0.9, 2, 4))
fine = field(noise(pts, 4.5, 3, 3))
micro = field(noise(pts, 16.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)

SCANNED = "scans" in sys.argv[3:]
if SCANNED:
    SCANS = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans")
    SCAN_PX_PER_IN = 44.0  # A little finer than the eye wash's, for the door's size, so its chips are small.

    def scan(name):
        return np.asarray(Image.open(os.path.join(SCANS, name)).convert("L"), np.float32) / 255.0

    def no_seams(a):
        """metal_plate_02's plates meet in straight lines that would draw straight lines across the door: take out what a whole row or column has in common."""
        for axis in (0, 1):
            line = a.mean(axis=axis)
            keep = line - ndi.gaussian_filter1d(line, 40, mode="wrap")
            a = a - (np.expand_dims(keep, axis) * 1.6)
        return np.clip(a, 0, 1)

    def triplanar(image, seed):
        """A scan laid over the model at its true scale from the three axes, blended by which way each texel looks, moved along for each part so no two pieces show the same patch."""
        h, w = image.shape
        shift = (part[cover] * 1000.0 + seed * 97.0)[:, None]
        p = pts * SCAN_PX_PER_IN + shift
        weights = np.abs(nor[cover]) ** 6
        weights = weights / np.maximum(weights.sum(1, keepdims=True), 1e-6)
        out = np.zeros(len(p), np.float32)
        for axis, (a, b) in enumerate(((1, 2), (0, 2), (0, 1))):
            coords = np.stack((p[:, a] % h, p[:, b] % w))
            out += weights[:, axis] * ndi.map_coordinates(image, coords, order=1, mode="wrap")
        return field(out)

    plate_metal = no_seams(1.0 - scan("metal_plate_02_metal.jpg"))
    plate_rough = scan("metal_plate_02_rough.jpg")
    scratch_map = np.clip((plate_rough - ndi.gaussian_filter(plate_rough, 10, mode="wrap")) * 5.0, -1, 1)
    scratch_map = no_seams(scratch_map * 0.5 + 0.5)
    container = scan("container_side_diff.jpg")
    container = container - container.mean(axis=0, keepdims=True) + container.mean()  # The corrugations run up its columns.
    mottle_map = container / np.maximum(ndi.gaussian_filter(container, 48, mode="wrap"), 1e-3)
    mottle_map = np.clip(1.0 + (mottle_map - 1.0) * 2.4, 0.6, 1.4)
    scan_wear = triplanar(np.clip(plate_metal * 1.6, 0, 1), 1)
    scan_scratches = triplanar(scratch_map, 2)
    scan_dull = triplanar(no_seams(ndi.gaussian_filter(plate_rough, 3, mode="wrap")), 3)
    scan_mottle = np.where(cover, triplanar(mottle_map, 4), 1.0)
    print("scans: wear", scan_wear[cover].mean(), "mottle sd", scan_mottle[cover].std(), flush=True)


def lines_mask(seed, count, y_range, z_range, x, lengths, widths, spread=None):
    """Thin straight scratches on a face at depth x, as a mask."""
    r = np.random.default_rng(seed)
    points, width = [], []
    for _ in range(count):
        y0, z0 = r.uniform(*y_range), r.uniform(*z_range)
        length = float(r.uniform(*lengths))
        w = float(r.uniform(*widths))
        turn = float(r.uniform(0, math.pi)) if spread is None else float(r.normal(spread[0], spread[1]))
        steps = max(4, int(length / 0.02))
        for k in range(steps):
            f = k / (steps - 1)
            points.append((x, y0 + math.cos(turn) * (f - 0.5) * length, z0 + math.sin(turn) * (f - 0.5) * length))
            width.append(w * (1 - abs(f - 0.5) * 1.2))
    width = np.array(width)
    dist, which = cKDTree(np.array(points, np.float32)).query(pts, k=1, distance_upper_bound=0.08, workers=4)
    which = np.minimum(which, len(width) - 1)
    return soft(field(smooth(1.0, 0.45, np.where(np.isfinite(dist), dist, 1.0) / width[which]).astype(np.float32)), 0.4)


# ---- The enamel: deep bottle green, knocked to primer then steel at its edges. ----
green = rgb(26, 108, 66) * (0.92 + 0.16 * big[..., None])
patches = smooth(0.32, 0.58, field(noise(pts, 0.5, 41, 3)))
# The plates' own edges mustn't chip the door's enamel beside them.
beside_plate = np.maximum(
    smooth(0.36, 0.16, np.maximum(np.maximum(SY0 - Y, Y - SY1), np.maximum(SZ0 - Z, Z - SZ1))),
    smooth(0.36, 0.16, np.maximum(np.maximum(RY0 - Y, Y - RY1), np.maximum(RZ0 - Z, Z - RZ1))),
) * enamel * front
chip_raw = edge * (1 - beside_plate) * patches * (0.5 + 0.5 * smooth(0.28, 0.66, fine)) + (fine - 0.5) * 0.09 + (micro - 0.5) * 0.08
to_primer = soft(smooth(0.24, 0.34, chip_raw), 0.4) * enamel
to_steel = soft(smooth(0.36, 0.48, chip_raw), 0.4) * enamel
# Door side chips: a few dings away from the edges too, on the case's sides and low on the door, each with a hard edge.
r = np.random.default_rng(14)
dings = np.column_stack((r.uniform(0.6, 5.1, 70), r.uniform(-7.1, 7.1, 70), r.uniform(-0.1, 17.1, 70)))
dist, which = cKDTree(dings).query(pts, k=1, distance_upper_bound=0.3, workers=4)
ding_size = r.uniform(0.035, 0.13, 70)
which = np.minimum(which, 69)
ding = soft(field(smooth(1.0, 0.65, np.where(np.isfinite(dist), dist, 9.0) / ding_size[which] + (fine[cover] - 0.5) * 0.45).astype(np.float32)), 0.4) * enamel
to_primer = np.maximum(to_primer, ding)
to_steel = np.maximum(to_steel, ding * smooth(0.45, 0.62, fine))
if SCANNED:
    # The chips' shapes are the scan's, gathered where the cabinet sticks out and gets knocked.
    exposed = edge * (1 - beside_plate) * (0.35 + 0.65 * smooth(0.3, 0.7, mid)) + smooth(5.0, 0.0, Z) * enamel * 0.16
    to_primer = soft(smooth(0.44, 0.58, scan_wear * (0.42 + exposed * 1.5)), 0.45) * enamel
    to_steel = soft(smooth(0.66, 0.78, scan_wear * (0.42 + exposed * 1.5)), 0.4) * enamel
    green = green * scan_mottle[..., None]
rust_ring = soft(np.maximum(to_steel, 0), 2.2) * smooth(0.4, 0.75, mid) * enamel
rust_c = mix(rgb(58, 30, 18), rgb(118, 62, 30), smooth(0.35, 0.8, field(noise(pts, 8.0, 8, 3))))
# Hands: duller and a touch darker round the handle.
hand = smooth(4.4, 0.8, np.hypot(Y - (LOCK_Y - 1.2), (Z - LOCK_Z) * 1.3)) * enamel * front
scratches_door = lines_mask(21, 16, (LOCK_Y - 4.2, LOCK_Y + 1.6), (0.5, 3.4), DOOR, (0.25, 1.5), (0.01, 0.02)) * enamel * front
# Hands wear the gloss off round the handle and leave it darker, and the case's foot collects a film of grime.
foot = smooth(4.6, 0.0, Z) * smooth(0.2, 0.75, field(noise(pts * np.array((1.0, 1.0, 0.35), np.float32), 0.5, 45, 3)))
e_color = mix(green, green * 0.62, np.clip(hand * 0.62 + foot * 0.34, 0, 1))
e_color = mix(e_color, rgb(70, 112, 88), np.clip(scratches_door * 0.45, 0, 1))
e_color = mix(e_color, rust_c * 0.8, np.clip(rust_ring * 0.22, 0, 1))
e_color = mix(e_color, rgb(142, 144, 134) * (0.8 + 0.3 * fine[..., None]), to_primer)
e_color = mix(e_color, rgb(142, 142, 138) * (0.7 + 0.45 * fine[..., None]), to_steel)
# Orange peel in the stoving enamel gives the highlight its life.
peel = field(noise(pts, 7.0, 44, 2))
e_rough = 0.3 + 0.04 * mid + 0.05 * fine + hand * 0.2 + foot * 0.2 + scratches_door * 0.2 + to_primer * 0.42 - to_steel * 0.12
e_metal = to_steel * 0.62
if SCANNED:
    scan_scratch = smooth(0.6, 0.78, scan_scratches) * enamel
    e_color = mix(e_color, rgb(84, 120, 96), scan_scratch * 0.3 * (1 - to_primer))
    e_rough = e_rough + (scan_dull - 0.5) * 0.5 + scan_scratch * 0.2
e_height = 0.0016 * (peel - 0.5) + (1 - to_primer) * 0.0035 - scratches_door * 0.0012 + 0.0009 * (micro - 0.5)

# ---- The sign: the print is rendered big, and sampled by position so it stays hard at this density. ----
PX = 240  # per inch of plate
pw, ph = int((SY1 - SY0) * PX), int((SZ1 - SZ0) * PX)
canvas = Image.new("L", (pw, ph), 0)
draw = ImageDraw.Draw(canvas)
inch = PX
# A hard white keyline inside the plate.
draw.rounded_rectangle((int(0.22 * inch), int(0.22 * inch), pw - int(0.22 * inch), ph - int(0.22 * inch)), radius=int(0.28 * inch), outline=255, width=int(0.085 * inch))
# The cross, heavy, as safety signs draw it.
cx, cy = pw // 2, int(ph * 0.40)
arm, bar = int(3.25 * inch), int(1.2 * inch)
draw.rounded_rectangle((cx - bar, cy - arm, cx + bar, cy + arm), radius=int(0.06 * inch), fill=255)
draw.rounded_rectangle((cx - arm, cy - bar, cx + arm, cy + bar), radius=int(0.06 * inch), fill=255)


def text_at(draw_on, text, centre_y, height_px, width_limit, spacing=0.0, variation="Bold", centre_x=None, width_total=None):
    font = ImageFont.truetype(FONT, height_px)
    try:
        font.set_variation_by_name(variation)
    except Exception:
        pass
    widths = [draw_on.textlength(c, font=font) for c in text]
    gap = spacing * height_px
    total = sum(widths) + gap * (len(text) - 1)
    if total > width_limit:
        return text_at(draw_on, text, centre_y, int(height_px * width_limit / total), width_limit, spacing, variation, centre_x, width_total)
    box = draw_on.textbbox((0, 0), text, font=font)
    x = (width_total if width_total is not None else pw) / 2 - total / 2 if centre_x is None else centre_x - total / 2
    y = centre_y - (box[3] + box[1]) / 2
    for c, w in zip(text, widths):
        draw_on.text((x, y), c, 255, font=font)
        x += w + gap


text_at(draw, "FIRST AID", int(ph * 0.862), int(1.72 * inch), pw - int(1.2 * inch), spacing=0.05)
sign_print = np.asarray(canvas, np.float32) / 255.0
uu, vv = (Y - SY0) / (SY1 - SY0), (Z - SZ0) / (SZ1 - SZ0)
printed = sample_image(ndi.zoom(sign_print, 0.5, order=1), uu, vv) * plate * (X > DOOR + ST * 0.6) * front
printed = soft(printed, 0.35)
s_scuff = lines_mask(31, 24, (SY0, SY1), (SZ0, SZ1), DOOR + ST, (0.3, 2.2), (0.01, 0.018), spread=(0.0, 0.3)) * plate * front
s_scuff_fine = lines_mask(32, 60, (SY0, SY1), (SZ0, SZ1), DOOR + ST, (0.1, 0.5), (0.008, 0.012)) * plate * front
s_rub = smooth(0.52, 0.8, field(noise(pts * np.array((1.0, 0.3, 1.0), np.float32), 0.8, 33, 3))) * smooth(9.0, 2.0, Z - SZ0) * plate
corner_d = np.minimum(np.abs(Y - SY0), np.abs(Y - SY1)) + np.minimum(np.abs(Z - SZ0), np.abs(Z - SZ1))
s_worn = soft(smooth(0.5, 0.66, edge * smooth(1.3, 0.25, corner_d) * (0.5 + 0.5 * smooth(0.3, 0.7, fine)) + edge * smooth(0.62, 0.8, mid) * 0.62 + (fine - 0.5) * 0.08), 0.4) * plate
safety = rgb(0, 116, 60) * (0.93 + 0.1 * big[..., None] + 0.04 * mid[..., None])
print_white = rgb(240, 240, 228) * (0.97 + 0.05 * mid[..., None])
# A little yellowing and fade toward the top, where the hall's lights are.
yellow = smooth(SZ0 + 7.0, SZ1, Z) * (0.5 + 0.5 * big)
print_white = mix(print_white, rgb(232, 226, 196), yellow * 0.5)
safety = mix(safety, safety * 1.12 + rgb(10, 12, 8), yellow * 0.3)
s_color = mix(safety, print_white, printed)
tears = np.zeros((H, W), np.float32)
for ry in (SY0 + 0.42, SY1 - 0.42):
    for rz in (SZ0 + 0.42, SZ1 - 0.42):
        length = 1.5 + 0.8 * abs(math.sin(ry * 3.1 + rz))
        wander = 0.03 * np.sin(Z * 2.3 + ry)
        tears = np.maximum(tears, smooth(0.11, 0.015, np.abs(Y - ry + wander)) * smooth(rz + 0.1, rz - 0.18, Z) * smooth(rz - length, rz - 0.3, Z))
tears = tears * plate * front * (0.55 + 0.45 * smooth(0.25, 0.7, field(noise(pts * np.array((1.0, 2.0, 0.3), np.float32), 1.2, 46, 2))))
film = plate * smooth(SZ0 + 3.2, SZ0 + 0.1, Z) * smooth(0.25, 0.7, field(noise(pts * np.array((1.0, 1.0, 0.45), np.float32), 0.55, 47, 3)))
s_color = mix(s_color, s_color * 0.72, film * 0.42)
s_color = mix(s_color, rgb(82, 46, 24), np.clip(tears * 0.5, 0, 1))
s_color = mix(s_color, s_color * 0.86, np.clip(s_rub * 0.3, 0, 1))
if SCANNED:
    # Printed sheet ages less than paint, but it does age: a third of the enamel's mottle, and faint scratches over the print.
    s_color = s_color * (1.0 + (scan_mottle[..., None] - 1.0) * 0.35)
    s_color = mix(s_color, rgb(170, 190, 174), smooth(0.62, 0.8, scan_scratches) * plate * 0.14)
s_color = mix(s_color, rgb(160, 180, 164), np.clip(s_scuff * 0.2 + s_scuff_fine * 0.09, 0, 1))
s_color = mix(s_color, rgb(128, 130, 126) * (0.8 + 0.3 * fine[..., None]), s_worn)
s_rough = 0.36 + 0.05 * mid + printed * 0.05 + s_rub * 0.05 + s_scuff * 0.16 + s_worn * 0.05 + film * 0.16 + tears * 0.2
s_metal = s_worn * 0.62
if SCANNED:
    s_rough = s_rough + (scan_dull - 0.5) * 0.4 + smooth(0.62, 0.8, scan_scratches) * 0.14
s_height = 0.0007 * (micro - 0.5) - s_scuff * 0.0009 - s_scuff_fine * 0.0005 + 0.012 * smooth(1.8, 0.0, np.hypot(Y - SY1, Z - SZ0)) + printed * 0.00045

# ---- The rating plate: stamped steel with black print. ----
PXR = 300
rw, rh = int((RY1 - RY0) * PXR), int((RZ1 - RZ0) * PXR)
canvas = Image.new("L", (rw, rh), 0)
draw = ImageDraw.Draw(canvas)
text_at(draw, "SAFETY STATION 12", int(rh * 0.3), int(0.28 * PXR), rw - int(0.7 * PXR), spacing=0.03, width_total=rw)
text_at(draw, "INSPECT MONTHLY", int(rh * 0.68), int(0.26 * PXR), rw - int(0.7 * PXR), spacing=0.03, variation="SemiBold", width_total=rw)
rating_print = soft(sample_image(np.asarray(canvas, np.float32) / 255.0, (Y - RY0) / (RY1 - RY0), (Z - RZ0) / (RZ1 - RZ0)) * rating * front, 0.3)
r_color = mix(rgb(160, 160, 154) * (0.82 + 0.26 * fine[..., None]), rgb(14, 14, 14), rating_print * 0.95)
r_rough = 0.42 + 0.14 * fine + rating_print * 0.2
r_metal = 0.62 * (1 - rating_print)

# ---- The inspection tag: yellow card, printed black, with pen ticks. ----
y_t, z_t = LOCK_Y - 2.36, LOCK_Z - 1.31
PXT = 400
tw, th = int(0.92 * PXT), int(2.3 * PXT)
canvas = Image.new("L", (tw, th), 0)
draw = ImageDraw.Draw(canvas)
text_at(draw, "CHECKED", int(th * 0.2), int(0.17 * PXT), tw - 40, variation="Bold", width_total=tw)
for k in range(6):
    yy = int(th * (0.3 + k * 0.105))
    draw.rectangle((30, yy, tw - 30, yy + int(0.1 * PXT)), outline=255, width=4)
    if k < 4:
        draw.line((46, yy + 26, tw * (0.42 + 0.06 * (k % 3)), yy + 14), fill=255, width=5)
tag_print = soft(sample_image(np.asarray(canvas, np.float32) / 255.0, (Y - (y_t - 0.46)) / 0.92, (Z - (z_t - 2.05)) / 2.3) * tag, 0.3)
t_color = mix(rgb(232, 178, 28) * (0.9 + 0.16 * mid[..., None]), rgb(18, 16, 12), tag_print * 0.92)

# ---- Small parts. ----
z_color = rgb(104, 104, 98) * (0.74 + 0.36 * mid[..., None])
b_tarnish = smooth(0.35, 0.72, mid * 0.6 + fine * 0.4)
b_color = mix(rgb(208, 164, 86), rgb(128, 96, 48), b_tarnish * 0.7)
k_color = rgb(12, 12, 13) * (0.85 + 0.35 * fine[..., None])
k_shine = smooth(0.55, 0.86, edge + (fine - 0.5) * 0.3)
red = rgb(190, 22, 18) * (0.92 + 0.14 * mid[..., None])

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = 0.0007 * (micro - 0.5)
for mask, c, ro, me, he in (
    (enamel, e_color, e_rough, e_metal, e_height),
    (plate, s_color, s_rough, s_metal, s_height),
    (rating, r_color, r_rough, r_metal, None),
    (tag, t_color, 0.72, None, None),
    (zinc, z_color, 0.42 + 0.2 * mid, 0.62 * np.ones((H, W), np.float32), None),
    (brass, b_color, 0.28 + 0.26 * b_tarnish, 0.68 * np.ones((H, W), np.float32), None),
    (rubber, k_color, 0.42 + 0.14 * fine, None, 0.0012 * (fine - 0.5)),
    (seal, red, 0.38, None, None),
):
    color = np.where(mask[..., None], c, color)
    rough = np.where(mask, ro, rough)
    if me is not None:
        metal = np.where(mask, me, metal)
    if he is not None:
        height = np.where(mask, he, height)

# Dust on what faces up, and in the door's gaps, sparse on the sign, which gets wiped.
settled = upward * smooth(0.25, 0.7, big * 0.4 + mid * 0.6) * (Z > 16.5)
gathered = smooth(0.25, 0.7, crevice) * smooth(0.3, 0.72, mid * 0.6 + fine * 0.4)
ledge = plate * smooth(SZ0 + 0.4, SZ0 + 0.02, Z) * smooth(0.3, 0.72, fine)
grime = np.clip(settled * 0.85 + gathered * 0.28 + ledge * 0.25, 0, 0.9)
dust = rgb(112, 106, 92) * (0.82 + 0.36 * fine[..., None])
color = mix(color, dust, grime)
rough = rough * (1 - grime * 0.8) + 0.86 * grime * 0.8
metal = metal * (1 - grime)
# A rust tear under each sign rivet, small.
color = color * (0.68 + 0.32 * ao[..., None])

height = fill_from(cover, height)[0]
filtered = ndi.gaussian_filter(height, 0.45)
px = np.maximum(density * weight, 1.0)
dv, du = np.gradient(filtered)
normal = np.stack((-du * px, -dv * px, np.ones_like(filtered)), -1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("first aid painted", flush=True)
