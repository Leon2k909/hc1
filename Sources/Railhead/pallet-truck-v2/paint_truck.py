"""Paint the pallet truck's maps from its bakes: python paint_truck.py <work dir> <output dir>

Bold red enamel, worn to bare steel where pallets drag along the forks' tops and knocked on its real edges, oily round the pump, dirty low down. Black ribbed grip polished by hands, chrome ram, zinc bolts, grey rubber
wheels. A printed capacity label on each fork. Wear masks are soft or fine, and made of strokes rather than thresholded blobs, because coarse thresholded noise reads as camouflage and pixels in the engine.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "CerroBlanco", "boulder-v2"))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, sample_image, save_gray, save_normal, save_rgb, srgb_to_linear, to_normal  # noqa: E402
from rock_noise import fbm, smooth  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

PAINT, BLACK, RUBBER, CHROME, ZINC, NYLON = range(6)
FORK_Y, FORK_W, FORK_H = 7.5, 3.15, 3.35

pos4 = load("bake_pt_pos")
nor4 = load("bake_pt_nor")
facts4 = load("bake_pt_facts")
edge4 = load("bake_pt_edge")
ao4 = load("bake_pt_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "truck.json")))
density, RANGE = meta["density"], meta["range"]
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
edge = edge4[..., 0]
pos, nor, finish, part, edge = fill_from(cover, pos, nor, finish, part, edge)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, edge4, ao4
pts = pos[cover].astype(np.float32)
print("coverage %.2f, %.1f px/in" % (cover.mean(), density), flush=True)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def solid(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
up = np.clip(nor[..., 2], 0, 1)
crevice = np.clip((1 - ao) * 1.4, 0, 1)
worn_edge = smooth(0.012, 0.09, edge)
big = field(fbm(pts, 0.06, 201, 3))
mid = field(fbm(pts, 0.34, 202, 3))
fine = field(fbm(pts, 1.8, 203, 3))
micro = field(fbm(pts, 7.0, 204, 2))
print("noise", flush=True)

# ---- Strokes: pallets dragged along the forks and knocks about the frame, drawn as lines on the plan so they run true ----
rng = np.random.default_rng(77)
SCALE = 24
scrape_img = Image.new("L", (int(60 * SCALE), int(30 * SCALE)), 0)
d = ImageDraw.Draw(scrape_img)
for side in (-FORK_Y, FORK_Y):
    for _ in range(170):
        x0 = rng.uniform(-2, 47)
        length = rng.uniform(1.5, 14.0)
        y = side + rng.normal(0.0, 1.5)
        drift = rng.normal(0.0, 0.05)
        d.line([((x0 + 6) * SCALE, (y + 15) * SCALE), ((x0 + length + 6) * SCALE, (y + drift * length + 15) * SCALE)], fill=int(rng.uniform(60, 255)), width=int(rng.integers(1, 4)))
scrape_art = ndi.gaussian_filter(np.asarray(scrape_img, np.float32) / 255.0, 0.7)
on_top = nor[..., 2] > 0.75
scrapes = sample_image(scrape_art, np.clip((X + 6) / 60.0, -1, 2), 1.0 - np.clip((Y + 15) / 30.0, -1, 2)) * on_top * (finish == PAINT) * (np.abs(np.abs(Y) - FORK_Y) < FORK_W)
# Where pallets ride, the paint has gone in a band, ragged at its edges.
rides = smooth(0.0, 1.0, np.clip(1.0 - np.abs(np.abs(Y) - FORK_Y) / 2.3, 0, 1) * 1.5 + (mid * 0.5)) * on_top * (finish == PAINT) * (X > 3.0) * (np.abs(np.abs(Y) - FORK_Y) < FORK_W) * smooth(-0.15, 0.4, big + fine * 0.3)

# ---- Red enamel ----
# Near the old one's bold red, which is 185, 33, 29.
red = mix(solid(178, 28, 24), solid(150, 20, 16), smooth(-0.4, 0.5, big))
red = red * (0.92 + 0.12 * mid[..., None])
# Dulled by weather on what faces up, and a little pinker where the sun has been at it.
red = mix(red, solid(150, 62, 52), smooth(0.4, 0.95, up) * smooth(-0.2, 0.5, big) * 0.2)
bare = solid(112, 110, 106) * (0.8 + 0.34 * fine[..., None])
rust = solid(84, 46, 26) * (0.8 + 0.4 * micro[..., None])
chip_where = worn_edge * smooth(-0.2, 0.3, mid * 0.6 + fine * 0.7)
chips = np.clip(chip_where * 1.2, 0, 1)
# Lower down it takes more knocks: kicks and pallets.
knocks = smooth(-0.1, 0.34, fine * 0.8 + mid * 0.5) * smooth(9.0, 1.5, Z) * worn_edge
chips = np.maximum(chips, np.clip(knocks * 0.8, 0, 1))
steel_shows = np.clip(np.maximum(chips, np.maximum(scrapes * 0.85, rides * smooth(-0.1, 0.25, fine) * 0.72)), 0, 1)
primer = smooth(0.0, 0.45, steel_shows) * (1.0 - smooth(0.4, 0.9, steel_shows))
p_color = mix(red, solid(70, 62, 56), primer * 0.55)
p_color = mix(p_color, bare, smooth(0.4, 0.8, steel_shows))
p_rust = smooth(0.5, 0.9, steel_shows) * smooth(-0.1, 0.4, mid + fine * 0.3)
p_color = mix(p_color, rust, p_rust * 0.5)
p_rough = 0.42 + 0.1 * mid + 0.06 * fine + steel_shows * 0.26 + p_rust * 0.2
p_metal = smooth(0.5, 0.85, steel_shows) * (1 - p_rust * 0.8) * 0.62
p_height = -0.008 * smooth(0.1, 0.5, steel_shows) + 0.0012 * fine

# ---- Printed capacity label on each fork's outer side: a white block with black lettering, faded ----
FONT = os.path.join(ROOT, "Assets", "fonts", "Dinish-Bold.ttf")
label = Image.new("L", (900, 220), 255)
ImageDraw.Draw(label).text((450, 110), "MAX 2500 kg", font=ImageFont.truetype(FONT, 170), fill=0, anchor="mm")
label_art = ndi.gaussian_filter(np.asarray(label, np.float32) / 255.0, 0.8)
for sy, sign in ((1.0, -1.0), (-1.0, 1.0)):
    # On a face looking along +Y a reader's right is -X, and on one looking along -Y it's +X.
    uu = (sign * (X - 26.0) + 4.0) / 8.0
    vv = (Z - 0.95) / 1.95
    here = (finish == PAINT) * (nor[..., 1] * sy > 0.8) * (np.abs(Y * sy - (FORK_Y + FORK_W)) < 0.02) * (uu > 0) * (uu < 1) * (vv > 0) * (vv < 1)
    # Lost only in a few nicks: more than that and at this density the words break up.
    keep = smooth(-0.75, -0.45, fine * 0.5 + mid * 0.5)
    block = here * keep
    letters = sample_image(label_art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))
    p_color = np.where((block > 0.5)[..., None], mix(solid(20, 20, 20), solid(206, 202, 188), letters) * (0.84 + 0.2 * mid[..., None]), p_color)
    p_rough = np.where(block > 0.5, 0.56, p_rough)
    p_metal = np.where(block > 0.5, 0.0, p_metal)

# ---- Other finishes ----
g_color = solid(20, 20, 20) * (0.86 + 0.26 * fine[..., None])
polish = smooth(44.0, 47.0, Z)
g_rough = 0.62 - polish * 0.2 + 0.06 * micro
tyre = solid(30, 30, 30) * (0.84 + 0.3 * micro[..., None])
r_color = mix(tyre, solid(74, 70, 62), smooth(-0.1, 0.5, mid) * smooth(4.0, 0.2, Z) * 0.5)
r_rough = 0.78 + 0.08 * fine
c_color = solid(214, 214, 212) * (0.94 + 0.08 * fine[..., None])
c_stain = smooth(0.0, 0.5, mid + crevice) * 0.5
c_color = mix(c_color, solid(70, 54, 36), c_stain * 0.6)
z_color = mix(solid(150, 150, 144) * (0.84 + 0.26 * fine[..., None]), solid(92, 66, 44), smooth(0.05, 0.6, mid) * 0.5)
n_color = solid(196, 190, 170) * (0.8 + 0.26 * fine[..., None])
n_color = mix(n_color, solid(60, 54, 46), smooth(-0.2, 0.5, mid) * 0.6)

color = np.where((finish == PAINT)[..., None], p_color, np.where((finish == BLACK)[..., None], g_color, np.where((finish == RUBBER)[..., None], r_color, np.where((finish == CHROME)[..., None], c_color, np.where((finish == ZINC)[..., None], z_color, n_color)))))
rough = np.where(finish == PAINT, p_rough, np.where(finish == BLACK, g_rough, np.where(finish == RUBBER, r_rough, np.where(finish == CHROME, 0.2 + c_stain * 0.3, np.where(finish == ZINC, 0.46 + 0.14 * fine, 0.5 + 0.1 * fine)))))
# Seen in s&box on Railhead: full metal draws near black where the reflections are dim. These stay well under it.
metal = np.where(finish == PAINT, p_metal, np.where(finish == CHROME, 0.7 * (1 - c_stain * 0.5), np.where(finish == ZINC, 0.62, 0.0))).astype(np.float32)
height = np.where(finish == PAINT, p_height, np.where(finish == RUBBER, 0.004 * micro, 0.0008 * fine))

# ---- Oil from the pump, dirt low down, dust on top, grime in the corners ----
d_pump = np.hypot(X + 4.2, Y)
oil = smooth(5.5, 1.5, d_pump + mid * 2.0) * smooth(17.0, 8.0, Z) * smooth(-0.15, 0.4, mid + fine * 0.3)
runs = smooth(0.0, 0.5, field(fbm(pts * np.array((1.0, 1.0, 0.1), np.float32), 1.6, 205, 2))) * smooth(3.4, 2.4, d_pump) * (Z > 8.0) * (Z < 12.5)
oil = np.maximum(oil, runs)
color = mix(color, solid(24, 20, 14), oil * 0.62)
rough = rough * (1 - oil * 0.7) + 0.26 * oil * 0.7
# Only the last inch or so: the forks are barely higher than that, and more than this buried their red.
floor_dirt = smooth(1.5, 0.15, Z + mid * 0.5) * (nor[..., 2] < 0.7)
color = mix(color, solid(62, 54, 44) * (0.8 + 0.3 * fine[..., None]), floor_dirt * 0.42)
rough = rough * (1 - floor_dirt * 0.5) + 0.86 * floor_dirt * 0.5
metal = metal * (1 - floor_dirt * 0.5)
dust = smooth(0.55, 0.95, up * 0.72 + (big * 0.25) + (fine * 0.12)) * 0.1 * (1 - smooth(0.0, 0.4, steel_shows) * (finish == PAINT))
color = mix(color, solid(104, 96, 84), dust)
rough = rough * (1 - dust) + 0.88 * dust
metal = metal * (1 - dust)
grime = smooth(0.25, 0.9, crevice) * smooth(-0.2, 0.3, mid)
color = mix(color, solid(26, 22, 18), grime * 0.55)
rough = rough * (1 - grime * 0.5) + 0.84 * grime * 0.5
metal = metal * (1 - grime * 0.5)

color = color * (0.82 + 0.18 * ao[..., None])
normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.14, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, "pt_truck_color.png"), color)
save_gray(os.path.join(OUT, "pt_truck_rough.png"), rough)
save_gray(os.path.join(OUT, "pt_truck_metal.png"), metal)
save_gray(os.path.join(OUT, "pt_truck_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, "pt_truck_normal.png"), normal)
print("truck painted", flush=True)
