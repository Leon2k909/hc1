"""Paint worn rubber, cast alloy and steel from the shared position/normal/part/AO bakes.

python paint_hose.py <work> <model output directory>. No external photographs or generated textures.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'Sources/Gameplay/capture-flag-v2'))
from paint import WORK, OUT, load, fill_from, noise, smooth, mix, srgb_to_linear, save_rgb, save_gray, save_normal, to_normal, sample_image

facts = json.load(open(os.path.join(WORK, 'pallet.json')))
density, span = facts['density'], facts['range']
pos4, nor4, tags = load('bake_pl_pos'), load('bake_pl_nor'), load('bake_pl_facts')
cover = pos4[..., :3].max(-1) > .001
pos = (pos4[..., :3] - .5) * span
nor = nor4[..., :3] * 2 - 1
finish = np.rint(tags[..., 0] * 16).astype(np.int32)
pos, nor, finish = fill_from(cover, pos, nor, finish)
raw_ao = load('bake_pl_ao')[..., 0]
raw_ao = fill_from(raw_ao > .001, raw_ao)[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(raw_ao, .55), cover.shape[0] / raw_ao.shape[0], order=1), 0, 1)
pts = pos[cover]
H, W = cover.shape


def field(values):
    result = np.zeros((H, W), np.float32)
    result[cover] = values
    return result


def rgb(values):
    return np.broadcast_to(srgb_to_linear(values), (H, W, 3))


turn = np.asarray(((.71, -.4, .57), (.63, .76, -.18), (-.36, .5, .79)), np.float32)
coarse = field(noise(pts @ turn, .08, 101, 3))
medium = field(noise(pts @ turn, .8, 102, 3))
fine = field(noise(pts @ turn, 5.8, 103, 2))
tiny = field(noise(pts @ turn, 13, 104, 1))
rubber, alloy, steel, label, lining = [finish == k for k in range(5)]
up = np.clip(nor[..., 2], 0, 1)
low = smooth(.75, .08, pos[..., 2])
crevice = smooth(.2, .65, 1 - ao)

# Hose coordinates along its length and around the circular cross section. Used for mould marks and maker's stripe.
path = np.load(os.path.join(WORK, 'hose_path.npy'))
lengths = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
tangents = np.gradient(path, axis=0)
tangents /= np.maximum(np.linalg.norm(tangents, axis=1, keepdims=True), 1e-6)
_, nearest = cKDTree(path).query(pts, workers=4)
delta = pts - path[nearest]
side = np.cross(tangents[nearest], np.asarray((0, 0, 1)))
side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-6)
along = field(lengths[nearest] + (delta * tangents[nearest]).sum(-1))
around = field(np.arctan2((delta * side).sum(-1), delta[:, 2]))

base = rgb((49, 54, 51)) * (.88 + .24 * coarse[..., None] + .09 * (medium[..., None] - .5))
scuff = smooth(.55, .76, coarse * .55 + medium * .45) * up
base = mix(base, rgb((92, 90, 77)), scuff * .38)
ground_grime = np.clip(low * .4 + crevice * .25, 0, .65)
base = mix(base, rgb((67, 61, 49)), ground_grime)

# Subdued white print on the top of the hose; a useful scale cue rather than a continuous bright racing stripe.
image = Image.new('L', (1536, 90))
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf', 64)
draw.text((8, 4), 'WATER TRANSFER  /  50 mm', font=font, fill=255)
text = np.asarray(image, np.float32) / 255
u = (along % 165 - 22) / 36
v = .5 + around / .42
ink = sample_image(text, u, v) * rubber * smooth(.26, .5, medium) * .65
base = mix(base, rgb((172, 172, 147)), ink)

# Cast aluminium: dark inside recesses, handled bright on exposed metal; no painted rust on the alloy.
metal_color = rgb((164, 169, 166)) * (.86 + .2 * medium[..., None])
oxidation = np.clip(crevice * .55 + smooth(.62, .78, coarse) * .3, 0, .65)
metal_color = mix(metal_color, rgb((107, 113, 106)), oxidation)
color = np.where(alloy[..., None], metal_color, base)
color = np.where(steel[..., None], rgb((83, 87, 86)) * (.8 + .3 * medium[..., None]), color)
color = np.where(lining[..., None], rgb((26, 29, 27)), color)
yellow = mix(rgb((177, 146, 65)), rgb((82, 79, 56)), smooth(.57, .76, medium) * .7)
color = np.where(label[..., None], yellow, color)
color *= .94 + .06 * ao[..., None]

rough = .66 + .12 * (medium - .5) + ground_grime * .14 - scuff * .12
rough = np.where(alloy, .4 + .15 * oxidation + .1 * (fine - .5), rough)
rough = np.where(steel, .37 + .12 * (fine - .5), rough)
rough = np.where(label | lining, .8 + .08 * (fine - .5), rough)
metal = np.where(alloy, .94 - oxidation * .25, np.where(steel, .95, 0))

# Fine rubber grain and a pair of subtle longitudinal mould seams. Most of the silhouette comes from real geometry.
seam = np.exp(-((np.abs(around) - 1.35) / .07)**2) * .008
rubber_height = (fine - .5) * .007 + (tiny - .5) * .002 + seam
height = np.where(rubber | label, rubber_height, (fine - .5) * .002)
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, .45), density)
inside = ndi.binary_erosion(cover, iterations=2)
normal = fill_from(inside, normal)[0]
color, rough, metal, normal, ao = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, .2, 1), metal, normal, ao)
for suffix, values in [('color', color), ('rough', rough), ('metal', metal), ('ao', ao), ('normal', normal)]:
    writer = save_rgb if suffix == 'color' else save_normal if suffix == 'normal' else save_gray
    writer(os.path.join(OUT, 'hose_coil_' + suffix + '.png'), values)
print('hose painted', 'density', round(density, 1), 'covered', round(float(cover.mean()), 3), flush=True)
