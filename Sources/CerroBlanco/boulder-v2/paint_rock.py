"""Paint the boulders' maps from their bakes: python paint_rock.py <work dir> <output dir>

A coarse grey granite with warm feldspar and dark mica in it, keeping the old stones' colours. Paler and crusted with lichen on top, dark in its cracks,
stained where rain runs, and damp and mossy at the lawn. Every mask is soft: a hard edge on coarse noise reads as pixels at this density. Worked out from each
texel's 3D position, so it crosses UV seams. Its light and shade from the sculpt are in the normal map, with the fine grain added here.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, save_gray, save_normal, save_rgb, srgb_to_linear, to_normal  # noqa: E402
from rock_noise import fbm, smooth  # noqa: E402

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

pos4 = load("bake_rk_pos")
nor4 = load("bake_rk_nor")
tangent4 = load("bake_rk_tangent")
masks4 = load("bake_rk_masks")
ao4 = load("bake_rk_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
meta = json.load(open(os.path.join(WORK, "rock.json")))
density, RANGE = meta["density"], meta["range"]
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
tangent = tangent4[..., :3] * 2 - 1
masks = masks4[..., :3]
# The masks bake from the sculpt, and a ray that missed it leaves nothing there.
hit = cover & (np.abs(tangent).max(-1) > 1e-3)
pos, nor = fill_from(cover, pos, nor)
tangent, masks = fill_from(hit, tangent, masks)
ao = fill_from(ao4[..., 0] > 0.001, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ao, W / ao.shape[1], order=1), 0, 1)
del pos4, nor4, tangent4, masks4, ao4
pts = pos[cover].astype(np.float32)
print("coverage %.2f, %.1f px/in, sculpt reaches %.3f" % (cover.mean(), density, hit.sum() / max(cover.sum(), 1)), flush=True)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def solid(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


Z = pos[..., 2]
up = np.clip(nor[..., 2], 0, 1)
crack, ledge, exposed = masks[..., 0], masks[..., 1], masks[..., 2]
crevice = np.clip((1 - ao) * 1.35, 0, 1)

big = field(fbm(pts, 0.03, 101, 3))
mid = field(fbm(pts, 0.13, 102, 3))
small = field(fbm(pts, 0.6, 103, 3))
print("noise 1", flush=True)
grain = field(fbm(pts, 3.2, 104, 2))
grain2 = field(fbm(pts, 5.5, 105, 2))
print("noise 2", flush=True)

# ---- The stone: grey with warm patches, its grains of feldspar and mica ----
# Darker than looks right in Cycles, and with the old stones' strong mottling: the map's sun bleaches it, and a pale even stone reads as plaster.
color = mix(solid(84, 83, 80), solid(112, 102, 86), smooth(-0.35, 0.45, big + mid * 0.4))
color = mix(color, solid(58, 62, 68), smooth(-0.15, 0.4, mid * 0.6 + small * 0.55) * 0.68)
color = mix(color, solid(150, 142, 126), smooth(0.08, 0.5, -small * 0.75 + mid * 0.3) * 0.5)
feldspar = smooth(0.15, 0.5, grain)
mica = smooth(0.2, 0.55, grain2)
color = mix(color, solid(190, 176, 152), feldspar * 0.38)
color = mix(color, solid(24, 24, 26), mica * 0.6)
rough = 0.8 + 0.05 * small - mica * 0.18
height = 0.014 * grain + 0.008 * grain2 + 0.02 * small

# ---- Its ledges show paler, fresher stone at their lips ----
color = mix(color, solid(150, 142, 128), np.clip(ledge * 0.3, 0, 1) * smooth(-0.2, 0.3, small))

# ---- Weather: a little paler and dry on top, stained where rain runs off ----
sun = smooth(0.35, 0.95, up) * smooth(-0.1, 0.5, big * 0.4 + exposed - 0.3)
color = mix(color, solid(140, 136, 126), sun * 0.14)
runs = field(fbm(pts * np.array((1.0, 1.0, 0.09), np.float32), 0.42, 106, 3))
falls = smooth(0.0, 0.5, runs) * smooth(0.75, 0.2, up) * smooth(1.0, 12.0, Z)
color = color * (1 - falls[..., None] * np.array((0.3, 0.29, 0.26), np.float32))
rough = rough + falls * 0.05

# ---- Lichen on what faces the sky: pale grey crusts and a little ochre, soft at their edges ----
crust = field(fbm(pts, 0.18, 107, 4))
print("noise 3", flush=True)
lichen = smooth(0.02, 0.34, crust + (small * 0.25) + (up - 0.55) * 0.5) * smooth(0.2, 0.55, up + 0.15) * smooth(6.0, 16.0, Z)
speck = smooth(-0.1, 0.35, grain + small * 0.5)
pale = mix(solid(170, 172, 158), solid(146, 154, 128), smooth(-0.3, 0.3, mid))
color = mix(color, pale * (0.84 + 0.3 * speck[..., None]), lichen * 0.42 * (0.55 + 0.45 * speck))
ochre = smooth(0.22, 0.52, field(fbm(pts, 0.31, 108, 3)) + (crust - 0.1) * 0.5) * smooth(0.25, 0.7, up)
color = mix(color, solid(168, 134, 66) * (0.8 + 0.3 * speck[..., None]), ochre * 0.46 * (0.5 + 0.5 * speck))
rough = rough + lichen * 0.08
height = height + (lichen * 0.018 + ochre * 0.012) * speck

# ---- Cracks and hollows hold dirt ----
dirt = np.clip(crack * 1.1 + smooth(0.3, 0.95, crevice) * 0.75, 0, 1)
color = mix(color, solid(34, 31, 27), dirt * 0.72)
rough = rough + dirt * 0.06

# ---- Damp and green at the lawn, soil splashed on it ----
wet = smooth(9.0, 0.5, Z + small * 2.4 + mid * 2.6)
color = mix(color, solid(50, 48, 40), wet * 0.62)
rough = rough - wet * 0.14
moss_where = smooth(14.0, 3.0, Z + mid * 7.0) * smooth(-0.15, 0.22, crust + small * 0.3)
moss = moss_where * smooth(-0.25, 0.25, grain * 0.6 + small * 0.6)
color = mix(color, mix(solid(62, 78, 34), solid(88, 100, 44), smooth(-0.3, 0.4, mid)) * (0.8 + 0.34 * speck[..., None]), moss * 0.74)
rough = rough + moss * 0.14
height = height + moss * 0.03 * speck
soil = smooth(2.6, 0.2, Z + small * 0.9)
color = mix(color, solid(44, 36, 26), soil * 0.8)
rough = rough * (1 - soil) + 0.92 * soil

# Lifted as a whole, to about the old stones' grey in the map's light. At 1.28 they matched in shade but went nearly white in full sun.
color = color * 1.1 * (0.72 + 0.28 * ao[..., None])
print("painted", flush=True)

# The sculpt's normals, with the fine grain laid over them.
detail = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
normal = tangent + detail * np.array((1, 1, 0), np.float32)
normal = normal / np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-6)
normal[..., 2] = np.abs(normal[..., 2])
color, rough, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.3, 1), normal)
save_rgb(os.path.join(OUT, "bd_rock_color.png"), color)
save_gray(os.path.join(OUT, "bd_rock_rough.png"), rough)
save_gray(os.path.join(OUT, "bd_rock_ao.png"), np.clip(ndi.zoom(ao, 0.5, order=1) * 1.03, 0, 1))
save_normal(os.path.join(OUT, "bd_rock_normal.png"), normal)
print("rock painted", flush=True)
