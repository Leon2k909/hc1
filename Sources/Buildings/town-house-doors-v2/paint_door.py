"""Paint a door's maps from its bakes: python paint_door.py <work dir> <materials dir> <outer|inner>

Decades of house paint over timber. Its grain shows through the coats and runs the way each member's wood runs. It wears
where doors wear: the lock stile, round the lever, along the bottom. The outer doors' weather side has crazed and faded.
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
from scipy.spatial import cKDTree  # noqa: E402

VARIANT = sys.argv[3]
PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST, FACE, APRON, ALONG, ACROSS = range(13)
facts = json.load(open(os.path.join(WORK, "door.json")))
density = facts["density"]
y1, z0 = facts["y1"], facts["z0"]
NAME = f"door_{VARIANT}"

pos4 = load("bake_door_pos")
nor4 = load("bake_door_nor")
facts4 = load("bake_door_facts")
ao4 = load("bake_door_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * 400.0
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
convex = np.clip((curve - 2.6) * 0.38, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 2.0) * 2.4 + ndi.gaussian_filter(convex, 5.0) * 3.0, 0, 1)
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


big = field(noise(pts, 0.1, 1, 3))
mid = field(noise(pts, 0.6, 2, 4))
fine = field(noise(pts, 3.0, 3, 3))
micro = field(noise(pts, 10.0, 4, 2))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
along = finish == ALONG
across = finish == ACROSS
timber = along | across
lock_z = z0 + 36.0

# The wood. Stretched noise runs with the grain; the sine of it draws growth lines.
stretch_along = np.array((3.6, 3.6, 0.1), np.float32)
stretch_across = np.array((3.6, 0.1, 3.6), np.float32)
grain = np.where(along, field(noise(pts * stretch_along, 1.0, 31, 4)), field(noise(pts * stretch_across, 1.0, 32, 4)))
lines = 0.5 + 0.5 * np.sin(grain * 48.0)
brush = np.where(along, field(noise(pts * np.array((16, 16, 0.5), np.float32), 1.0, 33, 2)), field(noise(pts * np.array((16, 0.5, 16), np.float32), 1.0, 34, 2)))
wood = mix(np.broadcast_to(srgb_to_linear((150, 112, 72)), (H, W, 3)), np.broadcast_to(srgb_to_linear((88, 60, 38)), (H, W, 3)), lines * 0.7 + 0.15 * (mid - 0.5))

outdoor = (VARIANT == "outer") * (X > 0)
lock_edge = smooth(y1 - 7.0, y1, Y)
low = smooth(z0 + 16.0, z0, Z)
hand = smooth(10.0, 2.5, np.hypot(Y - (y1 - 5.0), Z - lock_z))

# Crazing: old paint on the weather side breaks into long cells that follow the grain.
crack = np.zeros((H, W), np.float32)
if VARIANT == "outer":
    r = np.random.default_rng(6)
    weather = cover & (X > 0)
    seeds = r.uniform((-12.0, -60.0), (140.0, 60.0), (5500, 2))
    p2 = np.column_stack((Y[weather] * 2.6, Z[weather] * 0.62))
    d, _ = cKDTree(seeds).query(p2, k=2, workers=1)
    gap = d[:, 1] - d[:, 0]
    crack[weather] = smooth(0.22, 0.05, gap) * smooth(0.52, 0.74, big[weather] + (mid[weather] - 0.5) * 0.7)
    crack = ndi.gaussian_filter(crack, 0.9)

chip = (
    edge * smooth(0.3, 0.68, mid * 0.65 + fine * 0.35) * 1.05
    + (mid - 0.5) * 0.5
    + (big - 0.5) * 0.32
    + (fine - 0.5) * 0.85
    + (micro - 0.5) * 0.3
    + lock_edge * 0.11
    + low * 0.14
    + hand * 0.12
    + outdoor * 0.05
    + crack * 0.08
)
to_wood = smooth(0.74, 0.755, chip)
to_under = smooth(0.685, 0.7, chip)

if VARIANT == "outer":
    topcoat = np.broadcast_to(srgb_to_linear((46, 74, 52)), (H, W, 3))
    faded = np.broadcast_to(srgb_to_linear((88, 104, 82)), (H, W, 3))
    undercoat = np.broadcast_to(srgb_to_linear((176, 158, 112)), (H, W, 3))
else:
    topcoat = np.broadcast_to(srgb_to_linear((96, 62, 40)), (H, W, 3))
    faded = np.broadcast_to(srgb_to_linear((122, 86, 60)), (H, W, 3))
    undercoat = np.broadcast_to(srgb_to_linear((186, 170, 136)), (H, W, 3))

fade = smooth(0.34, 0.72, field(noise(pts * np.array((1.0, 1.0, 0.16), np.float32), 0.34, 37, 3)) + (mid - 0.5) * 0.2) * (0.14 + outdoor * 0.4)
paint = mix(topcoat * (0.88 + 0.24 * part[..., None]), faded, fade)
paint = paint * (0.9 + 0.2 * brush[..., None]) * (0.92 + 0.16 * lines[..., None])
paint = mix(paint, paint * 0.62, hand * smooth(0.3, 0.7, mid) * 0.75)
paint = paint * (1 - crack[..., None] * 0.34)
# Scuffs from boots and bags, along the door's bottom.
scuff = low * smooth(0.6, 0.72, field(noise(pts * np.array((2.0, 0.14, 8.0), np.float32), 1.0, 35, 3)))
paint = mix(paint, np.broadcast_to(srgb_to_linear((60, 56, 50)), (H, W, 3)), scuff * 0.6)

t_color = mix(paint, undercoat * (0.85 + 0.25 * fine[..., None]), to_under)
t_color = mix(t_color, wood, to_wood)
t_rough = 0.4 + 0.14 * mid + 0.1 * brush + fade * 0.26 + scuff * 0.2 - hand * 0.08
t_rough = t_rough * (1 - to_under) + (0.68 + 0.1 * fine) * to_under
t_rough = t_rough * (1 - to_wood) + (0.8 + 0.12 * fine) * to_wood
t_height = 0.0065 * (grain - 0.5) + 0.0028 * (brush - 0.5) + 0.0012 * (micro - 0.5) + (1 - to_under) * 0.009 + (1 - to_wood) * 0.006 - crack * 0.006 - to_wood * lines * 0.004

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)
color = np.where(timber[..., None], t_color, color)
rough = np.where(timber, t_rough, rough)
height = np.where(timber, t_height, height)

rust_c = mix(np.broadcast_to(srgb_to_linear((62, 36, 22)), (H, W, 3)), np.broadcast_to(srgb_to_linear((112, 66, 38)), (H, W, 3)), smooth(0.35, 0.8, field(noise(pts, 3.1, 8, 3))))
steel = np.broadcast_to(srgb_to_linear((150, 150, 148)), (H, W, 3))

# Blacked iron: rubbed back to bare metal where hands and pins work it.
iron = finish == OXIDE
i_wear = smooth(0.46, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3 + hand * 0.22)
i_color = np.broadcast_to(srgb_to_linear((36, 36, 38)), (H, W, 3)) * (0.75 + 0.5 * mid[..., None])
i_color = mix(i_color, steel * 0.8, i_wear * 0.9)
i_rust = smooth(0.72, 0.86, field(noise(pts, 3.4, 13, 3)) + crevice * 0.1)
i_color = mix(i_color, rust_c, i_rust * 0.75)
color = np.where(iron[..., None], i_color, color)
rough = np.where(iron, 0.46 + 0.2 * fine - 0.14 * i_wear + 0.32 * i_rust, rough)
metal = np.where(iron, (1 - i_rust) * 0.9, metal)
height = np.where(iron, 0.0018 * (micro - 0.5) + i_rust * 0.006, height)

# Brass: tarnished brown, bright where it's touched and kicked.
brass = finish == BRASS
b_touch = smooth(0.42, 0.74, edge * 0.6 + (mid - 0.5) * 0.7 + (fine - 0.5) * 0.5 + hand * 0.2 + low * 0.1)
b_color = mix(np.broadcast_to(srgb_to_linear((92, 82, 62)), (H, W, 3)), np.broadcast_to(srgb_to_linear((168, 150, 112)), (H, W, 3)), b_touch * 0.8)
b_green = smooth(0.7, 0.86, field(noise(pts, 2.1, 12, 3)) + crevice * 0.24)
b_color = mix(b_color, np.broadcast_to(srgb_to_linear((86, 104, 84)), (H, W, 3)), b_green * 0.3)
b_scratch = low * smooth(0.62, 0.74, field(noise(pts * np.array((3.0, 0.3, 26.0), np.float32), 1.0, 36, 3)))
b_color = mix(b_color, np.broadcast_to(srgb_to_linear((186, 170, 134)), (H, W, 3)), b_scratch * 0.25)
color = np.where(brass[..., None], b_color, color)
rough = np.where(brass, 0.42 + 0.24 * (1 - b_touch) + 0.1 * fine + 0.15 * b_green, rough)
metal = np.where(brass, 1 - b_green * 0.7, metal)
height = np.where(brass, 0.0012 * (micro - 0.5) - b_scratch * 0.002, height)

# Screw heads, and the keyhole's dark slot.
zinc = finish == ZINC
color = np.where(zinc[..., None], steel * (0.5 + 0.4 * fine[..., None]), color)
rough = np.where(zinc, 0.4 + 0.2 * fine, rough)
metal = np.where(zinc, 1.0, metal)
slot = finish == RUBBER
color = np.where(slot[..., None], np.array((0.004, 0.004, 0.004), np.float32), color)
rough = np.where(slot, 0.9, rough)

# Dirt: dust on what faces up and in the mouldings' corners, grime rising from the ground.
upward = np.clip(nor[..., 2], 0, 1)
settled = smooth(0.42, 0.9, upward * 0.84 + (big - 0.5) * 0.3 + crevice * 0.26)
splash = low * smooth(0.5, 0.7, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 14, 4)) + low * 0.12)
strength = 0.75 if VARIANT == "outer" else 0.4
dirt = np.clip((settled * 0.5 + splash * 0.6) * strength, 0, 0.85)
dirt_c = np.broadcast_to(srgb_to_linear((98, 88, 72)), (H, W, 3)) * (0.75 + 0.5 * fine[..., None])
color = mix(color, dirt_c, dirt)
rough = rough * (1 - dirt) + 0.92 * dirt
metal = metal * (1 - dirt)

color = color * (0.72 + 0.28 * ao[..., None])
solid = ndi.binary_erosion(cover, iterations=1)
height = fill_from(solid, height)[0]
normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
color, rough, metal, normal = fill_from(solid, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("door painted", flush=True)
