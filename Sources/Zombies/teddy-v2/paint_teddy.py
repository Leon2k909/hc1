"""Paint the teddy's maps from its bakes: python paint_teddy.py <work dir> <materials dir>

Short brown plush, kept even so it reads as one soft toy, with a pale muzzle, ear linings and foot pads, seams with their stitches, and matted dark
mud where it has sat in the wet. All worked out in 3D, so it runs across UV seams. It keeps the old teddy's brown.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

SKIN, RIBBON, BUTTON, NOSE, STUFFING, THREAD = range(6)
NAME = "teddy"
facts = json.load(open(os.path.join(WORK, "teddy.json")))
density = facts["density"]
HEAD_INV = np.array(facts["head_inverse"], np.float32)

pos4 = load("bake_teddy_pos")
nor4 = load("bake_teddy_nor")
facts4 = load("bake_teddy_facts")
ao4 = load("bake_teddy_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
print("coverage %.2f" % cover.mean(), flush=True)
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, facts4, ao4
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
# The head's own axes, so the face's marks tip over with it.
hx = HEAD_INV[0, 0] * X + HEAD_INV[0, 1] * Y + HEAD_INV[0, 2] * Z + HEAD_INV[0, 3]
hy = HEAD_INV[1, 0] * X + HEAD_INV[1, 1] * Y + HEAD_INV[1, 2] * Z + HEAD_INV[1, 3]
hz = HEAD_INV[2, 0] * X + HEAD_INV[2, 1] * Y + HEAD_INV[2, 2] * Z + HEAD_INV[2, 3]
hnx = HEAD_INV[0, 0] * nor[..., 0] + HEAD_INV[0, 1] * nor[..., 1] + HEAD_INV[0, 2] * nor[..., 2]

big = field(noise(pts, 0.14, 1, 3))
mid = field(noise(pts, 0.8, 2, 3))
fine = field(noise(pts, 3.0, 3, 3))
# Nap: fur at about the size the map can hold, tufted in small clumps.
nap = field(noise(pts, 14.0, 4, 2))
clumps = field(noise(pts, 4.5, 5, 2))
crevice = np.clip((1 - ao) * 1.2, 0, 1)
is_skin = finish == SKIN

# ---- The plush ------------------------------------------------------------------------------------------------------
# Kept even, or it reads as stained: all the variation is small, and the shape does the rest.
fur = mix(flat((116, 82, 52)), flat((104, 73, 46)), smooth(0.3, 0.72, clumps))
# Tips catch the light and roots don't.
fur = mix(fur * 0.84, fur * 1.14, smooth(0.32, 0.72, nap))
fur = fur * (0.98 + 0.04 * big[..., None])

# Pale parts: the muzzle, the ear linings and the foot pads, in a shorter felt.
muzzle = smooth(2.45, 2.0, np.sqrt((hx - 3.5) ** 2 + hy ** 2 + (hz + 1.05) ** 2)) * (hx > 1.8)
ear_r = np.minimum(np.hypot(hy - 3.85, hz - 3.7), np.hypot(hy + 3.85, hz - 3.7))
# In the engine, paler and harder-edged than this read as flat discs stuck on.
ear_lining = smooth(1.25, 0.7, ear_r) * smooth(0.1, 0.5, hnx) * (hz > 2.2)
pad_r = np.minimum(np.hypot(Y - 4.75, Z - 2.75), np.hypot(Y + 4.75, Z - 2.75))
foot_pad = smooth(1.6, 1.05, pad_r) * smooth(0.25, 0.6, nor[..., 0]) * (X > 7.5)
felt = np.clip(np.maximum.reduce([muzzle, ear_lining, foot_pad]), 0, 1) * is_skin
felt_c = flat((134, 108, 78)) * (0.92 + 0.12 * mid[..., None]) * (0.86 + 0.28 * nap[..., None])
fur = mix(fur, felt_c, felt)

# Seams: down the middle of the body and head, round the muzzle and pads, each a dark groove with its stitches across it.
seam_body = smooth(0.09, 0.02, np.abs(Y)) * (Z < 9.4) * (X > -1)
seam_head = smooth(0.09, 0.02, np.abs(hy)) * (hx > -6) * (hz > -3.6)
seam_ring = np.maximum(smooth(0.09, 0.02, np.abs(pad_r - 1.42)) * (X > 7.5) * (nor[..., 0] > 0.15), smooth(0.08, 0.02, np.abs(np.sqrt((hx - 3.5) ** 2 + hy ** 2 + (hz + 1.05) ** 2) - 2.25)) * (hx > 1.8))
seam = np.maximum.reduce([seam_body, seam_head * (1 - muzzle), seam_ring]) * is_skin
stitch_at = (Z * 2.4 + hz * 2.4 + X * 0.8)
stitches = seam * smooth(0.25, 0.1, np.abs(np.mod(stitch_at, 1.0) - 0.5))
fur = fur * (1 - seam[..., None] * 0.5)
fur = mix(fur, flat((64, 48, 34)), stitches[..., None] * 0.5)

# The mouth, stitched under the nose: a short line down from it, and a shallow curve either side.
mouth_drop = smooth(0.09, 0.03, np.abs(hy)) * (hz < -0.9) * (hz > -2.05) * (hx > 3.5)
smile_z = -2.0 + 0.13 * hy * hy
mouth_curve = smooth(0.09, 0.03, np.abs(hz - smile_z)) * (np.abs(hy) < 1.25) * (hx > 3.5)
mouth = np.maximum(mouth_drop, mouth_curve) * is_skin
fur = mix(fur, flat((26, 20, 16)), mouth[..., None] * 0.9)

# The split the stuffing comes out of: a dark tear, frayed at its edges.
split = np.array(facts["split"], np.float32)
# A slit running up and down, not a round hole.
to_split = np.sqrt(((X - split[0]) * 2.6) ** 2 + ((Y - split[1]) * 1.0) ** 2 + ((Z - split[2]) * 0.72) ** 2) + (fine - 0.5) * 0.3
tear = smooth(1.15, 0.85, to_split) * is_skin
fur = mix(fur, flat((30, 22, 16)), tear[..., None])
socket = np.array(facts["eye_socket"], np.float32)
to_socket = np.sqrt(((pos - socket) ** 2).sum(-1)) + (fine - 0.5) * 0.12
hole = smooth(0.42, 0.2, to_socket) * is_skin
fur = mix(fur, flat((36, 28, 20)), hole[..., None])

# Mud: dark and matted where it has sat, spattered higher, and wet. It stays low, so the toy keeps an even colour.
low = smooth(3.0, 0.2, Z + (mid - 0.5) * 2.0)
spatter = smooth(0.64, 0.7, field(noise(pts, 6.0, 6, 2))) * smooth(6.5, 1.5, Z)
downward = smooth(-0.2, -0.8, nor[..., 2])
# The pads face forward, up out of the worst of it, and stay readable.
mud = np.clip(low * 0.86 + spatter * 0.5 + downward * 0.42, 0, 0.92) * is_skin * (1 - foot_pad * 0.7)
fur = mix(fur, flat((46, 36, 26)) * (0.8 + 0.4 * fine[..., None]), mud)

color = fur.copy()
rough = np.where(is_skin, 0.9 - felt * 0.06 - mud * 0.34, 0.6)
metal = np.zeros((H, W), np.float32)
# The nap lies down where it's wet or felted. Everywhere else it's what the normal map is for.
fuzz = (1 - np.maximum(felt * 0.4, mud * 0.8))
height = is_skin * (0.05 * (nap - 0.5) * fuzz + 0.03 * (clumps - 0.5) * fuzz - seam * 0.04 + stitches * 0.03 - tear * 0.05 - hole * 0.05 + 0.004 * (fine - 0.5))

# ---- The rest ---------------------------------------------------------------------------------------------------------
ribbon = finish == RIBBON
weave = 0.5 + 0.5 * np.sin((X + Y * 1.3 + Z * 2.2) * 26.0)
r_c = mix(flat((132, 34, 32)), flat((172, 72, 62)), smooth(0.3, 0.75, big * 0.5 + fine * 0.5) * 0.7)
r_c = r_c * (0.88 + 0.16 * weave[..., None])
r_c = mix(r_c, flat((58, 42, 32)), np.clip(smooth(10.5, 5.5, Z + (mid - 0.5) * 2.0) * 0.5 + crevice * 0.4, 0, 0.7))
color = np.where(ribbon[..., None], r_c, color)
rough = np.where(ribbon, 0.62 + 0.14 * fine, rough)
height = np.where(ribbon, 0.004 * weave, height)

# The buttons: black and shiny, scratched, with four holes they'd be sewn through.
button = finish == BUTTON
color = np.where(button[..., None], flat((14, 13, 13)) * (0.9 + 0.5 * fine[..., None]), color)
rough = np.where(button, 0.22 + 0.2 * smooth(0.5, 0.8, fine), rough)

nose = finish == NOSE
thread = 0.5 + 0.5 * np.sin((hz * 0.2 + hy) * 20.0)
color = np.where(nose[..., None], flat((22, 18, 16)) * (0.8 + 0.5 * thread[..., None]), color)
rough = np.where(nose, 0.66, rough)
height = np.where(nose, 0.012 * thread, height)

stuffing = finish == STUFFING
s_dirty = smooth(0.4, 0.75, fine * 0.6 + mid * 0.4)
color = np.where(stuffing[..., None], mix(flat((176, 168, 148)), flat((112, 100, 80)), s_dirty * 0.8), color)
rough = np.where(stuffing, 0.96, rough)
height = np.where(stuffing, 0.05 * (nap - 0.5) + 0.03 * (fine - 0.5), height)

loose = finish == THREAD
color = np.where(loose[..., None], flat((30, 28, 26)), color)
rough = np.where(loose, 0.8, rough)

color = color * (0.68 + 0.32 * ao[..., None])
height = fill_from(cover, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.45), density, 1.0)
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
os.makedirs(OUT, exist_ok=True)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("teddy painted", flush=True)
