"""Paint the wall vent from world-space bakes, with paint wear on real edges and rain under fasteners."""
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Sources/Gameplay/capture-flag-v2'))
from paint import WORK, OUT, load, fill_from, noise, smooth, mix, srgb_to_linear, save_rgb, save_gray, save_normal, to_normal, sample_image

meta = json.load(open(os.path.join(WORK, 'pallet.json')))
pos4, nor4, facts = load('bake_pl_pos'), load('bake_pl_nor'), load('bake_pl_facts')
cover = pos4[..., :3].max(-1) > .001
pos, nor, finish, random = fill_from(cover, (pos4[..., :3] - .5) * meta['range'], nor4[..., :3] * 2 - 1,
                                    np.rint(facts[..., 0] * 16).astype(np.int32), facts[..., 1])
raw = load('bake_pl_ao')[..., 0]
raw = fill_from(raw > .001, raw)[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(raw, .65), cover.shape[0] / raw.shape[0], order=1), 0, 1)
H, W = cover.shape
pts = pos[cover]


def field(value):
    result = np.zeros((H, W), np.float32)
    result[cover] = value
    return result


def rgb(color):
    return np.broadcast_to(srgb_to_linear(color), (H, W, 3))


turn = np.asarray(((.71, -.4, .57), (.63, .76, -.18), (-.36, .5, .79)), np.float32)
large = field(noise(pts @ turn, .045, 211, 3))
mid = field(noise(pts @ turn, .38, 212, 3))
fine = field(noise(pts @ turn, 3.3, 213, 2))
grain = field(noise(pts @ turn, 8.0, 214, 1))
streaks = field(noise(pts * np.asarray((.6, .7, .028)), 1, 215, 2))
paint, alloy, steel, black, plate = [finish == k for k in range(5)]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
front = np.clip(-nor[..., 1], 0, 1)
up = np.clip(nor[..., 2], 0, 1)
crevice = smooth(.1, .65, 1 - ao)
edges = np.load(os.path.join(WORK, 'pallet_edges.npy'))
distance, _ = cKDTree(edges).query(pts, distance_upper_bound=.65, workers=4)
edge = smooth(.4, .035, field(np.where(np.isfinite(distance), distance, 1)))
chipped = edge * smooth(.47, .72, mid * .6 + fine * .4) * paint
old_rust = edge * smooth(.6, .77, large * .6 + mid * .4) * paint
base = rgb((83, 100, 109)) * (.88 + .24 * large[..., None] + (random[..., None] - .5) * .06)
base = mix(base, rgb((148, 151, 140)), chipped * .7)
base = mix(base, rgb((112, 69, 39)), old_rust * .6)
grime = np.clip(crevice * .28 + smooth(.55, .77, streaks) * front * .18 + up * .09, 0, .5)
base = mix(base, rgb((63, 66, 58)), grime)

# A little corrosion washed down from the lower fasteners, not blanket rust over every surface.
bolts = np.load(os.path.join(WORK, 'vent_bolts.npy'))
drips = np.zeros((H, W), np.float32)
for x, y, z in bolts:
    drop = z - Z
    run = np.exp(-((X - x) / (.16 + drop.clip(0) * .018))**2) * smooth(0, 1, drop) * smooth(12, 2, drop)
    drips = np.maximum(drips, run * (np.abs(Y - y) < 1.1) * front)
base = mix(base, rgb((101, 71, 46)), drips * .22 * paint)

aluminium = rgb((150, 157, 155)) * (.85 + .24 * mid[..., None] + (random[..., None] - .5) * .08)
aluminium = mix(aluminium, rgb((112, 116, 106)), crevice * .25 + smooth(.63, .8, streaks) * .13)
color = np.where(alloy[..., None], aluminium, base)
color = np.where(steel[..., None], rgb((100, 107, 106)) * (.85 + .24 * mid[..., None]), color)
color = np.where(black[..., None], rgb((24, 29, 28)), color)
color = np.where(plate[..., None], rgb((177, 182, 169)), color)

image = Image.new('L', (640, 140))
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf', 79)
draw.text((12, 15), 'EXTRACT  T1', font=font, fill=255)
ink = sample_image(np.asarray(image, np.float32) / 255, (X - 20) / 19, (Z - 5) / 5.5) * plate * front
color = mix(color, rgb((38, 46, 47)), ink * .9)
color *= .94 + .06 * ao[..., None]

rough = .65 + .1 * (fine - .5) + grime * .2 - chipped * .15
rough = np.where(alloy, .49 + .14 * (mid - .5) + crevice * .1, rough)
rough = np.where(steel, .37 + .12 * (fine - .5), rough)
rough = np.where(black, .92, rough)
rough = np.where(plate, .55 + .1 * (fine - .5), rough)
metal = np.where(paint, chipped * .65 * (1 - old_rust), np.where(alloy | steel, .93, np.where(plate, .8, 0)))
height = (grain - .5) * np.where(paint, .0035, .0015) + chipped * -.009
normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], .5), meta['density'])
normal = fill_from(ndi.binary_erosion(cover, iterations=2), normal)[0]
color, rough, metal, normal, ao = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, .2, 1), np.clip(metal, 0, 1), normal, ao)
for suffix, values in [('color', color), ('rough', rough), ('metal', metal), ('ao', ao), ('normal', normal)]:
    writer = save_rgb if suffix == 'color' else save_normal if suffix == 'normal' else save_gray
    writer(os.path.join(OUT, 'wall_vent_' + suffix + '.png'), values)
print('vent painted', 'density', round(meta['density'], 1), 'covered', round(float(cover.mean()), 3), flush=True)
