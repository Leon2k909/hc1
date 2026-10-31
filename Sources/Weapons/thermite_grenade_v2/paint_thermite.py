"""Paint the thermite grenade's maps from its bakes: python paint_thermite.py <work dir> <output dir>

Semi-gloss light red paint over a thin steel can, with black lettering (the modern scheme; before 1987 it was grey and purple), rubbed back on its chimes and
the lever's edges by being carried. Cloth tape over the top. A phosphated fuze body, plated pin and ring, a made-up lot number. Wear is
worked out in 3D. On the frag grenade v2's recipe, so the throwables look like one family.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, sample_image, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, stencil_image, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

PAINT, OXIDE, ZINC, LEVER, TAPE = 0, 2, 3, 11, 12
facts = json.load(open(os.path.join(WORK, "grenade.json")))
density, RANGE, ZC, RADIUS = facts["density"], facts["range"], facts["zc"], facts["radius"]
NAME = "thermite_grenade"
# THERMITE_SCHEME=early paints the grey and purple skin: only its colour map differs, so it shares the other maps.
EARLY = os.environ.get("THERMITE_SCHEME") == "early"

pos4 = load("bake_gr_pos")
nor4 = load("bake_gr_nor")
facts4 = load("bake_gr_facts")
ao4 = load("bake_gr_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
part = facts4[..., 1]
pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
# The AO bake's own coverage: at half the size it rasterises differently, and its alpha is 1 everywhere, so the value is what tells.
aoc = ao4[..., 0] > 0.001
ao = fill_from(aoc, ao4[..., 0])[0]
ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1)
pts = pos[cover]
print("covered", cover.mean(), "finishes", np.unique(finish[cover], return_counts=True), flush=True)


def field(values):
    out = np.zeros((H, W), np.float32)
    out[cover] = values
    return out


def rgb(*c):
    return np.broadcast_to(srgb_to_linear(c), (H, W, 3))


# Distance to the nearest convex edge, in inches: measured in 3D, so it doesn't care how thin a bevel's UVs came out.
edge_points = np.load(os.path.join(WORK, "gr_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=0.2, workers=4)
d = np.where(np.isfinite(d), d, 0.2)
edge_d = field(d.astype(np.float32))
print("edges measured", len(edge_points), flush=True)

big = field(noise(pts, 0.7, 1, 3))
mid = field(noise(pts, 4.5, 2, 4))
fine = field(noise(pts, 24.0, 3, 3))
micro = field(noise(pts, 70.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
radial = np.hypot(X, Y)
az = np.arctan2(Y, X)

body = finish == PAINT
lever = finish == LEVER
head = finish == OXIDE
zinc = finish == ZINC
tape = finish == TAPE
painted = body | lever
wall = body & (radial > 1.2) & (Z > 0.2) & (Z < 4.36)
r = np.random.default_rng(1414)


def scatter(count, low, high, seed, warp):
    """Knocks on the can's wall: nearly all in the middle of it, where it meets things."""
    spots_a = r.uniform(-math.pi, math.pi, count)
    spots_z = np.clip(r.normal(2.4, 1.0, count), 0.3, 4.3)
    spots = np.column_stack((RADIUS * np.cos(spots_a), RADIUS * np.sin(spots_a), spots_z))
    sizes = r.uniform(low, high, count)
    dist, which = cKDTree(spots).query(pts, k=1, workers=4)
    rough_edge = field(noise(pts, 55.0, seed, 3))[cover] - 0.5
    return field(smooth(1.0, 0.4, dist / sizes[which] * (1.0 + rough_edge * warp)).astype(np.float32)) * body


dent = scatter(18, 0.018, 0.038, 21, 2.2)
fleck = scatter(260, 0.004, 0.014, 26, 2.8)

# Scratches: short shallow runs on the can, walked on its surface so they stay on it.
lines, widths = [], []
for _ in range(190):
    a0 = float(r.uniform(-math.pi, math.pi))
    z0 = float(r.uniform(0.3, 4.3))
    heading = float(r.uniform(0, 2 * math.pi))
    length = float(r.uniform(0.09, 0.5))
    w = float(r.uniform(0.003, 0.0065))
    steps = max(4, int(length / 0.003))
    for k in range(steps):
        s = (k / (steps - 1) - 0.5) * length
        a = a0 + s * math.cos(heading) / RADIUS
        lines.append((RADIUS * math.cos(a), RADIUS * math.sin(a), z0 + s * math.sin(heading)))
        widths.append(w * (1 - abs(k / (steps - 1) - 0.5) * 1.3))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines)).query(pts, k=1, distance_upper_bound=0.02, workers=4)
which = np.minimum(which, len(widths) - 1)
scratch = field(smooth(1.0, 0.45, np.where(np.isfinite(dist), dist, 1.0) / widths[which]).astype(np.float32)) * body
scratch = ndi.gaussian_filter(scratch, 0.6)

# Lettering. Azimuth runs left to right seen from outside, so the letters read straight. Away from the lever and the hand's fingers.
text = stencil_image(["INCENDIARY", "TH3  AN-M14"], (1600, 760), bridge=False)
small = stencil_image(["GRENADE  HAND", "LOT RZD 26-0419"], (1500, 420), bridge=False)
centre = math.radians(-30)
span = math.radians(118)
mark = np.where(wall, sample_image(text, (az - centre) / span + 0.5, (Z - 1.9) / 1.3), 0)
mark = np.maximum(mark, np.where(wall, sample_image(small, (az - centre) / span + 0.5, (Z - 0.6) / 0.72), 0))
# A second block on the far side, so a spinning can still reads.
centre2 = math.radians(112)
span2 = math.radians(84)
far = np.where(wall, sample_image(small, np.angle(np.exp(1j * (az - centre2))) / span2 + 0.5, (Z - 2.4) / 0.6), 0)
mark = np.maximum(mark, far)
wear_mark = smooth(0.42, 0.62, field(noise(pts, 34.0, 22, 3)) + (mid - 0.5) * 0.5)
mark = np.clip(mark * (1 - wear_mark * 0.3), 0, 1)

# Stamped into the lever's top, read looking down with +X to the right.
stamp_img = stencil_image(["RZD TH3", "26-0419"], (1000, 520), bridge=False)
stamp = np.where(lever & (nor[..., 2] > 0.7) & (Z > 5.98), sample_image(stamp_img, (X + 0.42) / 0.64, (Y + 0.225) / 0.45), 0)
stamp = ndi.gaussian_filter(stamp, 0.8)

# The can's lock seam: a thin raised line up the wall on the far side from the lever, with a touch of solder bloom.
seam_off = np.angle(np.exp(1j * (az - math.radians(62)))) * RADIUS
seam = np.exp(-((seam_off / 0.028) ** 2)) * wall

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)
steel = rgb(152, 151, 146)

# The paint on the can and the lever.
outward = (nor * (pos - np.array((0, 0, 2.8), np.float32))).sum(-1) / np.maximum(np.linalg.norm(pos - np.array((0, 0, 2.8), np.float32), axis=-1), 1e-3)
underside = lever & (outward < -0.05)
edge = smooth(0.042, 0.004, edge_d)
near = smooth(0.13, 0.02, edge_d)
# Where a hand grips: the lever's middle and the can's flank.
thumb = lever * smooth(0.8, 0.0, np.abs(Z - 3.3)) * smooth(0.36, 0.1, np.abs(Y))
palm = wall * smooth(0.9, 0.1, np.abs(Z - ZC)) * smooth(0.32, 0.72, big)
# Rubbed from being carried: streaks round the can and along the lever, in patches.
rub_a = field(noise((pts + pts[:, [0]] * np.array((0, 0, 0.28), np.float32)) * np.array((5.0, 5.0, 62.0), np.float32), 1.0, 41, 3))
rub_b = field(noise((pts - pts[:, [1]] * np.array((0, 0, 0.36), np.float32)) * np.array((5.0, 5.0, 62.0), np.float32), 1.0, 44, 3))
rub_body = np.where(field(noise(pts, 2.2, 45, 2)) > 0.5, rub_a, rub_b)
rub_lever = field(noise(pts * np.array((0.9, 24.0, 0.9), np.float32), 1.0, 42, 3))
rub = np.where(lever, rub_lever, rub_body)
patch = smooth(0.5, 0.78, field(noise(pts, 1.5, 43, 3)))
rubbed = smooth(0.46, 0.7, rub) * patch * painted
chip = (
    edge * (0.3 + 0.8 * smooth(0.3, 0.72, mid * 0.5 + fine * 0.5))
    + near * (mid - 0.5) * 0.36
    + (fine - 0.5) * 0.24
    + (mid - 0.5) * 0.2
    + (big - 0.5) * 0.08
    + dent * 0.5
    + fleck * 0.62
    + scratch * 0.42
    + thumb * 0.14 * smooth(0.4, 0.7, rub_lever)
    + rubbed * 0.1
)
to_under = ndi.gaussian_filter(smooth(0.62, 0.68, chip), 0.6)
to_steel = ndi.gaussian_filter(smooth(0.74, 0.8, chip), 0.6)
if EARLY:
    can = mix(rgb(96, 99, 98), rgb(112, 114, 111), smooth(0.25, 0.75, big))
    ink = mix(rgb(128, 110, 140), rgb(108, 94, 120), smooth(0.3, 0.7, mid))
else:
    can = mix(rgb(118, 44, 38), rgb(136, 54, 44), smooth(0.25, 0.75, big))
    ink = mix(rgb(26, 24, 23), rgb(38, 35, 33), smooth(0.3, 0.7, mid))
can = can * (0.86 + 0.28 * mid[..., None])
can = np.where(lever[..., None], rgb(72, 74, 68) * (0.86 + 0.28 * mid[..., None]), can)
can = mix(can, can * 1.3 + rgb(12, 11, 10), np.clip(thumb * 0.42 + palm * 0.22 + rubbed * 0.16, 0, 1))
p_color = can
if EARLY:
    band_wear = smooth(0.5, 0.68, field(noise(pts, 16.0, 23, 3)) + (mid - 0.5) * 0.6)
    p_color = mix(p_color, ink, smooth(3.4, 3.41, Z) * smooth(3.86, 3.85, Z) * wall * (1 - band_wear * 0.5))
p_color = mix(p_color, ink, mark)
p_color = mix(p_color, p_color * 0.55, stamp * 0.8)
p_color = mix(p_color, p_color * 0.72 + rgb(60, 54, 40) * 0.28, seam * 0.5)
primer = rgb(58, 58, 54) * (0.8 + 0.4 * fine[..., None])
p_color = np.where(underside[..., None], primer, p_color)
p_color = mix(p_color, primer, to_under)
p_color = mix(p_color, steel * (0.72 + 0.4 * fine[..., None]), to_steel)
p_rough = 0.38 + 0.1 * mid + 0.05 * fine + 0.1 * big - palm * 0.06 - thumb * 0.1 + rubbed * 0.08 + mark * 0.08
p_rough = np.where(underside, 0.62 + 0.14 * fine, p_rough)
p_rough = p_rough * (1 - to_under) + (0.58 + 0.12 * fine) * to_under
p_rough = p_rough * (1 - to_steel) + (0.34 + 0.16 * fine) * to_steel
p_metal = to_steel * 0.95 + to_under * (1 - to_steel) * 0.25
p_height = 0.00050 * (micro - 0.5) + 0.00040 * (fine - 0.5) + 0.0034 * (field(noise(pts, 1.1, 24, 2)) - 0.5) * wall
p_height = p_height + (1 - to_under) * 0.0016 + (1 - to_steel) * 0.0008 + mark * 0.0004 - stamp * 0.0035 - dent * 0.0045 - fleck * 0.0006 - scratch * 0.001 + seam * 0.006
color = np.where(painted[..., None], p_color, color)
rough = np.where(painted, p_rough, rough)
metal = np.where(painted, p_metal, metal)
height = np.where(painted, p_height, height)

# The cloth tape over the top: dull, stained darker in patches, its surface mottled rather than woven, since threads this fine would moire.
# Short creases run outward from the well, where flat tape was pressed round a curve, and one lap line shows where it was started.
crease = field(noise(np.column_stack((np.cos(az[cover]) * 9.0, np.sin(az[cover]) * 9.0, radial[cover] * 1.4)).astype(np.float32), 1.0, 47, 2))
lap = np.exp(-((np.angle(np.exp(1j * (az - math.radians(-70)))) * radial / 0.012) ** 2)) * tape
t_color = mix(rgb(98, 94, 72), rgb(88, 84, 64), smooth(0.35, 0.65, big)) * (0.9 + 0.2 * fine[..., None]) * (0.92 + 0.16 * crease[..., None])
t_color = mix(t_color, t_color * 0.62, lap)
color = np.where(tape[..., None], t_color, color)
rough = np.where(tape, 0.82 + 0.1 * fine, rough)
metal = np.where(tape, 0.0, metal)
height = np.where(tape, 0.0007 * (micro - 0.5) + 0.0008 * (fine - 0.5) + 0.0022 * (crease - 0.5) + lap * 0.0035, height)

# The fuze body: dark phosphate with a cast skin; the well, the nut and the lock ring below it were turned, not cast.
turned = head & (Z < 5.38)
# Only the hardest corners and a few high spots are rubbed bright: a band along every edge reads as a wireframe.
h_edge = smooth(0.022, 0.003, edge_d)
h_wear = ndi.gaussian_filter(smooth(0.5, 0.6, h_edge * (0.3 + 0.62 * smooth(0.35, 0.7, mid * 0.5 + fine * 0.5)) + (fine - 0.5) * 0.34 + (mid - 0.5) * 0.22), 0.6)
h_color = rgb(72, 72, 68) * (0.78 + 0.44 * mid[..., None]) * (0.88 + 0.24 * fine[..., None])
h_color = np.where(turned[..., None], h_color * 1.1, h_color)
h_color = mix(h_color, steel * 0.85, h_wear * 0.95)
h_rust = smooth(0.74, 0.86, field(noise(pts, 15.0, 13, 3)) + crevice * 0.2)
rust = mix(rgb(58, 36, 22), rgb(104, 62, 34), smooth(0.35, 0.8, fine))
h_color = mix(h_color, rust, h_rust * 0.6)
cast = 0.0018 * (micro - 0.5) + 0.002 * (fine - 0.5)
lathe_marks = 0.00016 * np.sin(Z * 2 * math.pi / 0.021)
h_height = np.where(turned, lathe_marks + 0.0002 * (micro - 0.5), cast) + (1 - h_wear) * 0.0007
color = np.where(head[..., None], h_color, color)
rough = np.where(head, 0.66 + 0.12 * mid + 0.06 * fine - 0.22 * h_wear - turned * 0.04 + h_rust * 0.2, rough)
metal = np.where(head, np.clip(0.48 + 0.52 * h_wear - h_rust * 0.7, 0, 1), metal)
height = np.where(head, h_height, height)

# The plated pin and ring: dull zinc with a little gold in it, dark where it has tarnished, bright where it rubs.
z_tarnish = smooth(0.35, 0.75, field(noise(pts, 7.0, 25, 3)))
z_color = mix(rgb(176, 174, 160), rgb(170, 152, 104), smooth(0.4, 0.75, big + (mid - 0.5) * 0.5) * 0.3)
z_color = mix(z_color, rgb(92, 90, 82), z_tarnish * 0.6 + crevice * 0.3)
color = np.where(zinc[..., None], z_color, color)
rough = np.where(zinc, 0.3 + 0.2 * z_tarnish + 0.08 * fine, rough)
metal = np.where(zinc, 1.0 - z_tarnish * 0.12, metal)
height = np.where(zinc, 0.0003 * (micro - 0.5), height)

# Dirt: pale dust settled on what faces up and gathered round the corners, dark grime packed right into them.
upward = np.clip(nor[..., 2], 0, 1)
settled = smooth(0.5, 0.95, upward * 0.66 + (big - 0.5) * 0.38 + (mid - 0.5) * 0.2)
gathered = smooth(0.08, 0.5, crevice) * smooth(0.3, 0.7, mid * 0.6 + fine * 0.4)
dust = np.clip(settled * 0.2 + gathered * 0.42, 0, 0.7) * np.where(head, 0.3, 1.0)
color = mix(color, rgb(112, 104, 84) * (0.8 + 0.4 * fine[..., None]), dust)
rough = rough * (1 - dust) + 0.9 * dust
metal = metal * (1 - dust)
grime = smooth(0.42, 0.9, crevice + (mid - 0.5) * 0.45)
dirt = np.clip(grime * 0.6, 0, 0.8)
color = mix(color, rgb(58, 52, 42) * (0.72 + 0.5 * fine[..., None]), dirt)
rough = rough * (1 - dirt) + 0.88 * dirt
metal = metal * (1 - dirt)

color = color * (0.7 + 0.3 * ao[..., None])
normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border takes
# its normal from just inside. Islands too thin to have an inside, like bevels, keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
# Fill from the islands themselves: noise only exists on covered texels, and thin bevel islands must keep their own colour.
color, rough, metal, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), np.clip(metal, 0, 1), normal)
if EARLY:
    save_rgb(os.path.join(OUT, f"{NAME}_early_color.png"), color)
    print("thermite grenade painted", flush=True)
    sys.exit(0)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("thermite grenade painted", flush=True)
