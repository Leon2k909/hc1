"""Paint the burn drum's maps from its bakes: python paint_drum.py <work dir> <materials dir>

A drum that has burned for months. Its paint browns and blisters as it climbs towards the fire, then burns off to scaled grey
steel. Soot climbs from each air hole and over the rim, rust runs from the hoops, and mud splashes up from the ground. Inside,
soot, an ember bed with glowing cracks, and logs charred into alligator skin. All worked out in 3D, so it runs across UV seams.

Maps: a colour map per material (blue, red, rust, cold), roughness, metalness and normal for each of the two states the shell
can be in (painted, rust), and one AO and one glow mask. The shader takes a glow's colour from the colour map.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

SHELL, LID, BED, CHAR, COAL = range(5)
NAME = "burn_drum"
facts = json.load(open(os.path.join(WORK, "drum.json")))
density, H_DRUM, R_DRUM, BED_Z = facts["density"], facts["height"], facts["radius"], facts["bed"]

pos4 = load("bake_drum_pos")
nor4 = load("bake_drum_nor")
facts4 = load("bake_drum_facts")
ao4 = load("bake_drum_ao")
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

curve = np.zeros((H, W), np.float32)
for axis in (0, 1):
    dn = np.gradient(nor, axis=axis)
    dp = np.gradient(pos, axis=axis)
    curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
curve[~ndi.binary_erosion(cover, iterations=2)] = 0
# A whole drum curves at one over 11 inches, far under this threshold: only hoops, chimes and creases count as edges.
convex = np.clip((curve - 2.2) * 0.4, 0, 1)
edge = np.clip(ndi.gaussian_filter(convex, 1.6) * 2.4 + ndi.gaussian_filter(convex, 4.0) * 3.0, 0, 1)
del curve, dn, dp
pts = pos[cover]


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def flat(rgb):
    return np.broadcast_to(srgb_to_linear(rgb), (H, W, 3))


def wrap(a):
    return np.angle(np.exp(1j * a))


big = field(noise(pts, 0.09, 1, 3))
mid = field(noise(pts, 0.55, 2, 4))
fine = field(noise(pts, 2.7, 3, 3))
micro = field(noise(pts, 9.0, 4, 2))
crevice = np.clip((1 - ao) * 1.3, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
radius = np.hypot(X, Y)
theta = np.arctan2(Y, X)
radial = (nor[..., 0] * X + nor[..., 1] * Y) / np.maximum(radius, 1e-3)
print("noise done", flush=True)

shell = finish == SHELL
under = shell & (Z < 0.8) & (np.abs(nor[..., 2]) > 0.6) & (radius < 11.3)
inner = shell & (radial < -0.25) & (radius < 11.2) & ~under
cut = shell & (np.abs(radial) < 0.5) & (Z > 3.6) & (Z < 9.0) & ~inner & ~under
outer = shell & ~inner & ~under & ~cut

rust_tone = field(noise(pts, 3.1, 8, 3))
rust_c = mix(flat((50, 28, 17)), flat((100, 56, 32)), smooth(0.3, 0.75, rust_tone))
rust_c = mix(rust_c, flat((138, 82, 44)), smooth(0.76, 0.96, rust_tone))

# Heat: climbing to the rim, and in a widening plume above each air hole.
wander = (mid - 0.5) * 8.0 + (big - 0.5) * 5.0
heat = smooth(15.0, 34.0, Z + wander)
plume_soot = np.zeros((H, W), np.float32)
for a, zh in facts["holes"]:
    dz = Z - zh
    across = wrap(theta - a) * R_DRUM + (mid - 0.5) * 2.2
    plume = np.exp(-((across / (1.5 + 0.2 * np.clip(dz, 0, 24))) ** 2)) * smooth(-0.8, 0.5, dz) * smooth(22.0, 2.0, dz)
    plume_soot = np.maximum(plume_soot, plume)
# The plumes brown the paint on their way up; only the top of the drum gets hot enough to burn it off.
browned = smooth(0.14, 0.5, np.maximum(heat, plume_soot * 0.5) + (fine - 0.5) * 0.14 + (mid - 0.5) * 0.1)
scorched = smooth(0.34, 0.72, heat + (fine - 0.5) * 0.3 + (mid - 0.5) * 0.22)
soot = np.clip(plume_soot ** 1.5 * (0.45 + 0.4 * mid) + smooth(28.0, 34.5, Z + (mid - 0.5) * 6) * smooth(0.2, 0.62, mid * 0.6 + fine * 0.4) * 0.8, 0, 0.92)
# The hoops stand proud, so they take the knocks and hold a line of dirt either side.
hoop_gap = np.minimum(np.abs(Z - 11.39), np.abs(Z - 22.77))
hoop = smooth(0.95, 0.55, hoop_gap) * outer
hoop_edge = smooth(0.24, 0.0, np.abs(hoop_gap - 0.98)) * outer

streak = field(noise(pts * np.array((4.2, 4.2, 0.13), np.float32), 0.26, 6, 4))
below_hoop = np.maximum(smooth(0.0, 0.5, 10.6 - Z) * smooth(9.5, 1.0, 10.6 - Z), smooth(0.0, 0.5, 21.9 - Z) * smooth(9.5, 1.0, 21.9 - Z))
ground = smooth(9.0, 0.0, Z + (mid - 0.5) * 5)
blister = smooth(0.6, 0.7, field(noise(pts, 3.8, 21, 2))) * browned * (1 - scorched)

# The stencil, sprayed twice round the drum between the hoops. It reads left to right: +theta is a viewer's right, from outside.
# Each sits between two air holes, clear of their plumes.
art = ndi.gaussian_filter(stencil_image(["WASTE OIL", "55 GAL  LOT 3381"], (760, 270), bridge=True), 1.2)
stencil = np.zeros((H, W), np.float32)
for centre in (np.radians(-79.0), np.radians(101.0)):
    a = wrap(theta - centre)
    hit = sample_image(art, np.clip((a * R_DRUM + 6.0) / 12.0, -1, 2), np.clip((Z - 13.6) / 5.4, -1, 2))
    stencil = np.maximum(stencil, hit * (np.abs(a) < 1.2))
stencil = stencil * outer * smooth(0.3, 0.52, field(noise(pts, 2.4, 22, 3)) + big * 0.2) * (1 - browned * 0.7)
seam_mask = smooth(0.1, 0.03, np.abs(wrap(theta - facts["seam"]) * R_DRUM)) * outer


def voronoi(mask, cell, seed):
    """Distance from each masked texel to the crack between cells, and a random value per cell."""
    # Warped, or the cells are a clean mosaic and read as a pattern rather than as cracks in burnt wood.
    p = pos[mask]
    warp = np.stack([noise(p, 1.1 / cell, seed + 40 + k, 2) - 0.5 for k in range(3)], -1)
    p = p + warp * cell * 1.6
    lo, hi = p.min(0) - cell, p.max(0) + cell
    count = int(np.prod((hi - lo) / cell))
    sites = np.random.default_rng(seed).uniform(lo, hi, (max(count, 8), 3))
    values = np.random.default_rng(seed + 1).random(len(sites)).astype(np.float32)
    d, near = cKDTree(sites).query(p, k=2, workers=1)
    gap, rand = np.zeros((H, W), np.float32), np.zeros((H, W), np.float32)
    gap[mask] = (d[:, 1] - d[:, 0]).astype(np.float32)
    rand[mask] = values[near[:, 0]]
    return gap, rand


bed = (finish == BED) | (finish == COAL)
wood = finish == CHAR
bed_gap, bed_rand = voronoi(bed, 0.8, 31)
char_gap, char_rand = voronoi(wood, 0.9, 33)
print("cells done", flush=True)

ember_c = mix(flat((186, 52, 12)), flat((244, 112, 28)), smooth(0.5, 0.92, fine * 0.6 + bed_rand * 0.5))
coal_c = flat((17, 15, 14)) * (0.7 + 0.6 * fine[..., None])
ash_c = flat((118, 114, 108)) * (0.72 + 0.4 * fine[..., None])

# What glows. It's the same mask on all the burning materials, and the colour map says what colour.
# Mostly dark coal and ash: the heat shows in the gaps, in patches that have nothing to do with the cells.
bed_crack = smooth(0.13, 0.02, bed_gap)
hot_patch = smooth(0.42, 0.68, mid * 0.65 + big * 0.2 + fine * 0.3)
bed_hot = hot_patch * smooth(0.22, 0.7, bed_rand)
ashy = smooth(0.46, 0.66, big * 0.5 + fine * 0.5) * (1 - hot_patch * 0.85)
char_crack = smooth(0.12, 0.02, char_gap)
char_hot = smooth(0.38, 0.72, char_rand * 0.5 + mid * 0.5) * smooth(32.5, 27.0, Z)
# Seen through the air holes: burning fuel in dark and bright patches, or the holes read as flat orange stickers. The floor burns too: in
# the engine the fire's light reaches it, and bare it read as a pale tan patch through the holes.
hot_inside = inner | (under & (nor[..., 2] > 0.5))
wall_hot = hot_inside * smooth(24.0, 12.0, Z) * (0.07 + 0.85 * smooth(0.4, 0.68, field(noise(pts, 1.5, 51, 3))))
glow = np.zeros((H, W), np.float32)
glow = np.where(bed, np.clip(hot_patch * (bed_crack * 0.85 + bed_hot * 0.16) * (0.55 + 0.45 * fine) * (1 - ashy), 0, 1), glow)
glow = np.where(wood, char_crack * char_hot * (0.5 + 0.5 * fine), glow)
glow = np.where(hot_inside, wall_hot, glow)
glow = np.where(cut, smooth(0.34, 0.8, fine) * 0.28, glow)


def paint_shell(kind):
    """Colour, roughness, metalness and height of the outside for one kind of drum."""
    if kind == "rust":
        base = rust_c * (0.72 + 0.44 * fine[..., None])
        base = mix(base, flat((58, 60, 54)) * (0.75 + 0.4 * mid[..., None]), smooth(0.58, 0.68, big + mid * 0.2 - 0.05) * 0.85)
        rough_base = 0.84 + 0.12 * fine
    else:
        paint = {"blue": (36, 62, 104), "red": (120, 36, 28)}[kind]
        base = flat(paint) * (0.82 + 0.3 * mid[..., None]) * (1 + (streak[..., None] - 0.5) * 0.4)
        base = mix(base, flat(paint) * 1.7 + flat((36, 36, 34)), smooth(0.45, 0.85, big) * 0.26)
        rough_base = 0.42 + 0.18 * mid + 0.08 * fine

    col = base.copy()
    rough = rough_base.copy()
    metal = np.zeros((H, W), np.float32)
    # The stencil goes on over the paint, and burns with it.
    if kind != "rust":
        col = mix(col, flat((186, 182, 162)) * (0.82 + 0.26 * fine[..., None]), stencil * 0.92)
    # Chips on hoops, chimes and creases, and the odd scrape on the flats.
    chip = edge * smooth(0.3, 0.68, mid * 0.65 + fine * 0.35) * 1.16 + (mid - 0.5) * 0.5 + (big - 0.5) * 0.3 + (fine - 0.5) * 0.8 + (micro - 0.5) * 0.26 + ground * 0.14 + hoop * 0.17
    bare = smooth(0.67, 0.685, chip)
    bare_c = flat((132, 130, 124)) * (0.68 + 0.44 * fine[..., None])
    # Road grime and old rain over everything, so no paint is left the colour it came.
    grime = smooth(0.38, 0.78, big * 0.55 + mid * 0.45) * 0.34
    col = mix(col, flat((46, 42, 36)) * (0.8 + 0.4 * fine[..., None]), grime)
    # Heat browns and blisters the paint, then takes it off down to a dark scale with a little pale ash on it.
    col = mix(col, mix(col * 0.3, flat((40, 30, 24)), 0.6), browned)
    oxide = mix(flat((36, 34, 34)), flat((92, 86, 78)), smooth(0.3, 0.8, fine * 0.55 + mid * 0.5))
    oxide = mix(oxide, flat((146, 142, 132)), smooth(0.68, 0.84, fine * 0.55 + micro * 0.2 + mid * 0.3) * 0.5)
    col = mix(col, oxide, scorched)
    rough = rough * (1 - browned * 0.6) + 0.72 * browned * 0.6
    rough = rough * (1 - scorched) + (0.74 + 0.16 * fine) * scorched
    metal = np.maximum(metal, scorched * 0.25)
    col = mix(col, bare_c, bare)
    rough = rough * (1 - bare) + (0.38 + 0.26 * fine) * bare
    metal = np.maximum(metal, bare)
    # Rust: in the chips, on the burned steel, low down, and running from under the hoops.
    amount = 0.16 if kind == "rust" else 0.0
    rust = smooth(0.46, 0.62, scorched * 0.24 + ground * 0.34 + bare * 0.26 + hoop * 0.12 + (mid - 0.5) * 0.8 + (fine - 0.5) * 0.42 + amount)
    runs = smooth(0.52, 0.76, streak + crevice * 0.2) * below_hoop * smooth(0.25, 0.6, mid)
    col = mix(col, rust_c, rust)
    rough = rough * (1 - rust) + (0.84 + 0.12 * fine) * rust
    metal = metal * (1 - rust)
    col = mix(col, col * rust_c * 3.4, runs * 0.62)
    rough = rough + runs * 0.12
    col = mix(col, flat((12, 11, 10)) * (0.7 + 0.6 * fine[..., None]), soot)
    rough = rough * (1 - soot) + 0.94 * soot
    metal = metal * (1 - soot)
    col = col * (1 - seam_mask[..., None] * 0.45) * (1 - hoop_edge[..., None] * 0.42)
    height = 0.003 * (micro - 0.5) + 0.002 * (fine - 0.5) + (1 - bare) * 0.006 + blister * 0.02 + rust * 0.012 * (rust_tone - 0.25) + seam_mask * 0.012
    # Mud up from the ground, dust on the hoops' tops.
    upward = np.clip(nor[..., 2], 0, 1)
    mud = smooth(0.46, 0.68, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 14, 4)) + ground * 0.3) * ground
    speck = ground * smooth(0.64, 0.72, field(noise(pts, 7.5, 15, 2)))
    dirt = np.clip(mud * 0.8 + speck * 0.5 + smooth(0.4, 0.9, upward + (big - 0.5) * 0.3) * 0.5, 0, 0.92)
    col = mix(col, flat((74, 62, 46)) * (0.75 + 0.5 * fine[..., None]), dirt)
    rough = rough * (1 - dirt) + 0.93 * dirt
    metal = metal * (1 - dirt)
    height = height + dirt * 0.008 * (fine - 0.35)
    return col, rough, metal, height


def paint_rest(burning):
    """Colour, roughness, metalness and height of everything else. Only the bed and logs differ with the fire out."""
    col = np.zeros((H, W, 3), np.float32)
    rough = np.full((H, W), 0.9, np.float32)
    metal = np.zeros((H, W), np.float32)
    height = np.zeros((H, W), np.float32)

    in_c = flat((18, 16, 15)) * (0.7 + 0.7 * fine[..., None])
    in_c = mix(in_c, flat((76, 70, 62)), smooth(0.56, 0.74, mid * 0.6 + fine * 0.4) * 0.5)
    if burning:
        in_c = mix(in_c, flat((226, 92, 24)), np.clip(wall_hot * 1.8, 0, 1))
    col = np.where((inner | under)[..., None], in_c, col)
    rough = np.where(inner | under, 0.92, rough)
    height = np.where(inner | under, 0.004 * (fine - 0.5), height)

    # The hole's edge: bright where the chisel tore it, rusting back from there.
    tear = smooth(0.42, 0.62, fine * 0.7 + mid * 0.3)
    cut_c = mix(flat((116, 112, 106)), rust_c, tear)
    if burning:
        cut_c = mix(cut_c, flat((246, 112, 30)), smooth(0.34, 0.8, fine) * 0.28)
    col = np.where(cut[..., None], cut_c, col)
    rough = np.where(cut, 0.5 + 0.36 * tear, rough)
    metal = np.where(cut, 1 - tear, metal)

    # The lid's remnant: scaled grey and black, like everything else up there.
    lid = finish == LID
    lid_c = mix(flat((34, 32, 32)), flat((122, 116, 106)), smooth(0.34, 0.74, fine * 0.6 + mid * 0.5))
    lid_c = mix(lid_c, rust_c, smooth(0.54, 0.7, mid * 0.6 + fine * 0.4))
    col = np.where(lid[..., None], lid_c, col)
    rough = np.where(lid, 0.82, rough)
    height = np.where(lid, 0.012 * (fine - 0.5), height)

    if burning:
        bed_col = mix(coal_c, ash_c, ashy)
        bed_col = mix(bed_col, ember_c, np.clip(hot_patch * (bed_crack * 0.85 + bed_hot * 0.16) * (1 - ashy) * 1.5, 0, 1))
        char_col = mix(flat((16, 14, 13)) * (0.7 + 0.7 * fine[..., None]), flat((98, 94, 88)), smooth(0.56, 0.74, fine * 0.5 + mid * 0.5) * 0.5)
        char_col = mix(char_col, ember_c, np.clip(char_crack * char_hot * 1.4, 0, 1))
    else:
        cold_ash = smooth(0.24, 0.52, big * 0.4 + fine * 0.5 + bed_rand * 0.3)
        bed_col = mix(coal_c, ash_c, cold_ash)
        char_col = mix(flat((16, 14, 13)) * (0.7 + 0.7 * fine[..., None]), flat((110, 106, 100)), smooth(0.42, 0.66, fine * 0.5 + mid * 0.5) * 0.74)
    col = np.where(bed[..., None], bed_col, col)
    rough = np.where(bed, 0.92, rough)
    height = np.where(bed, 0.05 * smooth(0.0, 0.3, bed_gap) + 0.01 * (fine - 0.5), height)
    col = np.where(wood[..., None], char_col, col)
    rough = np.where(wood, 0.88 + 0.08 * fine, rough)
    height = np.where(wood, 0.075 * smooth(0.0, 0.3, char_gap) + 0.012 * (fine - 0.5), height)
    return col, rough, metal, height


os.makedirs(OUT, exist_ok=True)
solid_glow = np.clip(glow, 0, 1)
rest_hot = paint_rest(True)
rest_cold = paint_rest(False)


def compose(shell_maps, rest):
    col = np.where(outer[..., None], shell_maps[0], rest[0])
    rough = np.where(outer, shell_maps[1], rest[1])
    metal = np.where(outer, shell_maps[2], rest[2])
    height = np.where(outer, shell_maps[3], rest[3])
    return col, rough, metal, height


def finish_color(col, lit):
    # Occlusion stays in the colour, except where the surface gives its own light.
    shade = 0.72 + 0.28 * ao
    if lit:
        shade = np.maximum(shade, np.clip(solid_glow * 4.0, 0, 1))
    return np.clip(col * shade[..., None], 0, 1)


written = set()
for variant in ("blue", "red", "rust", "cold"):
    kind = "rust" if variant == "cold" else variant
    state = "rust" if kind == "rust" else "painted"
    maps = compose(paint_shell(kind), rest_cold if variant == "cold" else rest_hot)
    save_rgb(os.path.join(OUT, f"{NAME}_{variant}_color.png"), fill_from(cover, finish_color(maps[0], variant != "cold"))[0])
    if state not in written:
        written.add(state)
        height = fill_from(cover, maps[3])[0]
        normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
        rough, metal, normal = fill_from(cover, np.clip(maps[1], 0.1, 1), np.clip(maps[2], 0, 1), normal)
        save_gray(os.path.join(OUT, f"{NAME}_{state}_rough.png"), rough)
        save_gray(os.path.join(OUT, f"{NAME}_{state}_metal.png"), metal)
        save_normal(os.path.join(OUT, f"{NAME}_{state}_normal.png"), normal)
    print("painted", variant, flush=True)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), fill_from(cover, np.clip(ao * 1.03, 0, 1))[0])
save_gray(os.path.join(OUT, f"{NAME}_glow.png"), fill_from(cover, solid_glow)[0])
print("drum painted", flush=True)
