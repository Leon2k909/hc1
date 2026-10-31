"""Paint the flashbang's maps from its bakes: python paint_flash.py <work dir> <output dir>

Semi-gloss olive paint over steel, rubbed back to bare metal on the hex caps' corners and the lever's edges by being carried,
with a pale green band round the middle row of ports. The ports are drilled after painting's primer, so their bores are bare.
A phosphated fuze body with a cast skin and a turned nut, plated pin and ring, a dark can inside. Marked with made-up
lettering. The same family of finishes as the frag grenade. Wear is worked out in 3D.
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

PAINT, OXIDE, ZINC, LEVER, CANISTER = 0, 2, 3, 11, 12
facts = json.load(open(os.path.join(WORK, "flash.json")))
density, RANGE, ZC, RADIUS = facts["density"], facts["range"], facts["zc"], facts["radius"]
NAME = "flashbang"
DZ = 1.952  # From the frag grenade's fuze up to this one's.
TUBE_LOW, TUBE_HIGH = 0.80, 3.72
ROWS = (1.40, 2.25, 3.10)
PITCH = 0.85
PORT = 0.27
APOTHEM = 0.75

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
# The AO bake's own coverage: at half the size it rasterises differently, and an empty texel counted as covered draws a dark line along every seam.
aoc = ao4[..., 3] > 0.5
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

painted_steel = finish == PAINT
lever = finish == LEVER
head = finish == OXIDE
zinc = finish == ZINC
can = finish == CANISTER
in_tube = painted_steel & (Z > TUBE_LOW - 0.03) & (Z < TUBE_HIGH + 0.03) & (radial < RADIUS + 0.004)
# How far each texel is from its nearest port's centre line. The skin's big triangles round a port tilt too far, and dip too
# far under the true radius, to be told from the port by which way they face or how far out they are.
column = np.round(az / (math.pi / 3)) * (math.pi / 3)
across = -X * np.sin(column) + Y * np.cos(column)
up = Z - (ROWS[0] + np.clip(np.round((Z - ROWS[0]) / PITCH), 0, len(ROWS) - 1) * PITCH)
from_port = np.hypot(across, up)
tube_skin = in_tube & (radial > 0.64) & (from_port > PORT + 0.0165)
# Anything else of the tube: the countersinks, the bores and the inner wall.
recess = in_tube & ~tube_skin
inner_wall = in_tube & (radial <= 0.64) & (from_port > PORT + 0.002)
body = painted_steel & ~recess
caps = body & ~tube_skin
painted = body | lever

# Knocks and flecks: small dents where something hard met it, and a scatter of tiny chips, on the tube and most of all on the caps.
r = np.random.default_rng(1944)
skin = body[cover]
skin_points = pts[skin]
cap_points = pts[caps[cover]]


def scatter(tube_count, cap_count, low, high, seed, warp):
    spots = np.vstack((skin_points[r.integers(0, len(skin_points), tube_count)], cap_points[r.integers(0, len(cap_points), cap_count)]))
    sizes = r.uniform(low, high, len(spots))
    dist, which = cKDTree(spots).query(pts, k=1, workers=4)
    rough_edge = field(noise(pts, 55.0, seed, 3))[cover] - 0.5
    return field(smooth(1.0, 0.4, dist / sizes[which] * (1.0 + rough_edge * warp)).astype(np.float32)) * body


dent = scatter(5, 11, 0.016, 0.034, 21, 2.2)
fleck = scatter(120, 110, 0.004, 0.013, 26, 2.8)

# Scratches: short shallow lines, on the tube's skin and across the caps' flats, walked on the surface so they stay on it.
lines, widths = [], []


def add_scratch(point_at, length):
    w = float(r.uniform(0.003, 0.0065))
    steps = max(4, int(length / 0.003))
    for k in range(steps):
        lines.append(point_at((k / (steps - 1) - 0.5) * length))
        widths.append(w * (1 - abs(k / (steps - 1) - 0.5) * 1.3))


for _ in range(105):
    a0, z0 = r.uniform(-math.pi, math.pi), r.uniform(TUBE_LOW, TUBE_HIGH)
    heading = r.uniform(-math.pi, math.pi)
    add_scratch(lambda s: (RADIUS * math.cos(a0 + s * math.cos(heading) / RADIUS), RADIUS * math.sin(a0 + s * math.cos(heading) / RADIUS), z0 + s * math.sin(heading)), float(r.uniform(0.07, 0.4)))
for _ in range(60):
    flat = math.radians(60 * int(r.integers(0, 6)))
    n = np.array((math.cos(flat), math.sin(flat), 0.0))
    t = np.array((-math.sin(flat), math.cos(flat), 0.0))
    s0, z0 = r.uniform(-0.38, 0.38), float(r.choice((r.uniform(0.1, 0.72), r.uniform(3.8, 4.42))))
    heading = r.uniform(-math.pi, math.pi)
    add_scratch(lambda s: tuple(n * APOTHEM + t * (s0 + s * math.cos(heading)) + np.array((0, 0, z0 + s * math.sin(heading)))), float(r.uniform(0.05, 0.28)))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines)).query(pts, k=1, distance_upper_bound=0.02, workers=4)
which = np.minimum(which, len(widths) - 1)
scratch = field(smooth(1.0, 0.45, np.where(np.isfinite(dist), dist, 1.0) / widths[which]).astype(np.float32)) * body
scratch = ndi.gaussian_filter(scratch, 0.6)


def on_flat(image, degrees, z_low, z_high, width=0.72):
    """Lettering on one hex flat, read from outside with Z up."""
    flat = math.radians(degrees)
    nx, ny = math.cos(flat), math.sin(flat)
    facing = (nor[..., 0] * nx + nor[..., 1] * ny) > 0.97
    uu = ((-math.sin(flat) * X + math.cos(flat) * Y) + width / 2) / width
    vv = (Z - z_low) / (z_high - z_low)
    return np.where(caps & facing, sample_image(image, uu, vv), 0)


text = stencil_image(["K-47 STUN", "RZD 26-1182"], (1440, 640), bridge=True)
lot = stencil_image(["LOT 1182"], (1440, 300), bridge=True)
mark = on_flat(text, 0, 3.94, 4.26)
mark = np.maximum(mark, on_flat(text, -120, 3.94, 4.26))
mark = np.maximum(mark, on_flat(lot, 0, 0.32, 0.47))
mark = np.maximum(mark, on_flat(lot, 120, 0.32, 0.47))
wear_mark = smooth(0.42, 0.62, field(noise(pts, 34.0, 22, 3)) + (mid - 0.5) * 0.5)
mark = np.clip(mark * (1 - wear_mark * 0.55), 0, 1)

# The band: pale green round the middle row of ports, painted over the olive and rubbed through in places.
band = smooth(1.885, 1.892, Z) * smooth(2.615, 2.608, Z) * tube_skin
band = np.clip(band * (1 - smooth(0.62, 0.76, field(noise(pts, 30.0, 23, 3)) + (mid - 0.5) * 0.25) * 0.5), 0, 1)

# Stamped into the lever's top, read looking down with +X to the right.
stamp_img = stencil_image(["RZD K-47", "26-1182"], (1000, 520), bridge=False)
su = (X + 0.42) / 0.64
sv = (Y + 0.225) / 0.45
stamp = np.where(lever & (nor[..., 2] > 0.7) & (Z > 3.4 + DZ), sample_image(stamp_img, su, sv), 0)
stamp = ndi.gaussian_filter(stamp, 0.8)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
metal = np.zeros((H, W), np.float32)
height = np.zeros((H, W), np.float32)
steel = rgb(128, 127, 122)

# The paint on the body and the lever.
to_part = pos - np.array((0, 0, 3.0), np.float32)
outward = (nor * to_part).sum(-1) / np.maximum(np.linalg.norm(to_part, axis=-1), 1e-3)
underside = lever & (outward < -0.05)
# The tube's ends are hidden inside the caps: their edges wear nothing you can see.
seen_d = np.where(tube_skin & ((Z < 0.92) | (Z > 3.60)), 0.2, edge_d)
edge = smooth(0.026, 0.003, seen_d)
near = smooth(0.08, 0.012, seen_d)
# Where a hand grips: the lever's middle and the tube between the caps.
thumb = lever * smooth(0.75, 0.0, np.abs(Z - 3.0)) * smooth(0.3, 0.1, np.abs(Y))
palm = tube_skin * smooth(0.9, 0.2, np.abs(Z - ZC)) * smooth(0.32, 0.72, big)
# Rubbed from being carried: streaks round the tube and along the lever, in patches.
rub_a = field(noise((pts + pts[:, [0]] * np.array((0, 0, 0.28), np.float32)) * np.array((1.3, 1.3, 62.0), np.float32), 1.0, 41, 3))
rub_b = field(noise((pts - pts[:, [1]] * np.array((0, 0, 0.36), np.float32)) * np.array((1.3, 1.3, 62.0), np.float32), 1.0, 44, 3))
rub_body = np.where(field(noise(pts, 2.2, 45, 2)) > 0.5, rub_a, rub_b)
rub_lever = field(noise(pts * np.array((0.9, 24.0, 0.9), np.float32), 1.0, 42, 3))
rub = np.where(lever, rub_lever, rub_body)
patch = smooth(0.42, 0.72, field(noise(pts, 1.5, 43, 3)))
rubbed = smooth(0.46, 0.7, rub) * patch * painted
# The caps are what knocks against things, so their corners go first.
knocks = caps * edge * 0.12 * smooth(0.35, 0.7, mid)
chip = (
    edge * (0.22 + 0.7 * smooth(0.3, 0.72, mid * 0.5 + fine * 0.5))
    + knocks
    + near * (mid - 0.5) * 0.36
    + (fine - 0.5) * 0.24
    + (mid - 0.5) * 0.2
    + (big - 0.5) * 0.08
    + dent * 0.5
    + fleck * 0.62
    + scratch * 0.5
    + thumb * 0.14 * smooth(0.4, 0.7, rub_lever)
    + rubbed * 0.1
)
to_under = ndi.gaussian_filter(smooth(0.62, 0.68, chip), 0.6)
to_steel = ndi.gaussian_filter(smooth(0.74, 0.8, chip), 0.6)
olive = mix(rgb(64, 66, 46), rgb(82, 81, 56), smooth(0.25, 0.75, big))
olive = olive * (0.82 + 0.36 * mid[..., None])
olive = np.where(lever[..., None], olive * np.array((1.05, 1.0, 0.9), np.float32) * 0.94, olive)
olive = mix(olive, olive * 1.34 + rgb(12, 11, 9), np.clip(thumb * 0.42 + palm * 0.22 + rubbed * 0.26, 0, 1))
pale = mix(rgb(118, 132, 106), rgb(100, 114, 92), smooth(0.3, 0.7, mid))
pale = pale * (0.9 + 0.2 * fine[..., None])
yellow = mix(rgb(168, 146, 66), rgb(140, 122, 60), smooth(0.3, 0.7, mid))
p_color = mix(olive, pale, band)
p_color = mix(p_color, yellow, mark)
p_color = mix(p_color, p_color * 0.55, stamp * 0.8)
primer = rgb(58, 58, 54) * (0.8 + 0.4 * fine[..., None])
p_color = np.where(underside[..., None], primer, p_color)
p_color = mix(p_color, primer, to_under)
p_color = mix(p_color, steel * (0.72 + 0.4 * fine[..., None]), to_steel)
p_rough = 0.33 + 0.09 * mid + 0.06 * fine + 0.08 * big - palm * 0.06 - thumb * 0.1 + rubbed * 0.14 + (mark + band * 0.6) * 0.08
p_rough = np.where(underside, 0.62 + 0.14 * fine, p_rough)
p_rough = p_rough * (1 - to_under) + (0.58 + 0.12 * fine) * to_under
p_rough = p_rough * (1 - to_steel) + (0.34 + 0.16 * fine) * to_steel
p_metal = to_steel * 0.95 + to_under * (1 - to_steel) * 0.25 + rubbed * 0.12 * (1 - to_under)
# The caps' end faces keep the lathe's rings under the paint.
faced = caps & (np.abs(nor[..., 2]) > 0.95)
rings = 0.00022 * np.sin(radial * 2 * math.pi / 0.024) * faced
# Machined and drawn steel, so nearly flat: a fine orange peel in the paint, and only the lever is pressed sheet that wanders.
p_height = 0.00085 * (micro - 0.5) + 0.00050 * (fine - 0.5) + (0.0004 * body + 0.0012 * lever) * (field(noise(pts, 1.7, 24, 2)) - 0.5) - rubbed * 0.00035 + rings
p_height = p_height + (1 - to_under) * 0.0016 + (1 - to_steel) * 0.0008 + (mark + band) * 0.0004 - stamp * 0.0035 - dent * 0.0045 - fleck * 0.0006 - scratch * 0.001
color = np.where(painted[..., None], p_color, color)
rough = np.where(painted, p_rough, rough)
metal = np.where(painted, p_metal, metal)
height = np.where(painted, p_height, height)

# The ports: bare steel where the countersink cut the paint, dull and darkened down the bore, primer on the wall inside.
bare = steel * (0.74 + 0.36 * fine[..., None])
# The countersinks were painted with the tube, and only their rims have rubbed through.
sink = recess & (from_port > PORT + 0.001) & ~inner_wall
sink_wear = ndi.gaussian_filter(smooth(0.44, 0.56, smooth(0.03, 0.004, seen_d) * 0.5 + (fine - 0.5) * 0.5 + (mid - 0.5) * 0.4), 0.6)
r_color = mix(bare * 0.5, bare * 0.72, smooth(0.61, 0.645, radial))
r_rust = smooth(0.66, 0.84, field(noise(pts, 17.0, 31, 3)) + crevice * 0.22)
rust = mix(rgb(58, 36, 22), rgb(104, 62, 34), smooth(0.35, 0.8, fine))
r_color = mix(r_color, rust, r_rust * 0.5)
r_color = np.where(sink[..., None], mix(olive * 0.82, bare, sink_wear), r_color)
r_color = np.where(inner_wall[..., None], primer * 0.72, r_color)
color = np.where(recess[..., None], r_color, color)
r_rough = np.where(sink, 0.42 + 0.1 * fine - sink_wear * 0.06, 0.46 + 0.14 * fine + r_rust * 0.3)
r_metal = np.where(sink, sink_wear * 0.95, 0.9 - r_rust * 0.7)
rough = np.where(recess, np.where(inner_wall, 0.7, r_rough), rough)
metal = np.where(recess, np.where(inner_wall, 0.1, r_metal), metal)
height = np.where(recess, 0.0003 * (micro - 0.5) + 0.00012 * np.sin(Z * 2 * math.pi / 0.018), height)

# The can inside: dark, a little oily, and hardly ever seen.
c_color = rgb(48, 48, 46) * (0.72 + 0.5 * mid[..., None])
color = np.where(can[..., None], c_color, color)
rough = np.where(can, 0.5 + 0.2 * mid, rough)
metal = np.where(can, 0.35, metal)
height = np.where(can, 0.0004 * (fine - 0.5), height)

# The fuze body: dark phosphate with a cast skin; the nut and lock ring below it were turned, not cast.
turned = head & (Z < 2.76 + DZ)
h_wear = ndi.gaussian_filter(smooth(0.5, 0.58, edge * 0.86 + (fine - 0.5) * 0.46 + (mid - 0.5) * 0.3), 0.6)
h_color = rgb(50, 50, 48) * (0.74 + 0.5 * mid[..., None]) * (0.86 + 0.28 * fine[..., None])
h_color = np.where(turned[..., None], h_color * 1.2, h_color)
h_color = mix(h_color, steel * 0.85, h_wear * 0.95)
h_rust = smooth(0.74, 0.86, field(noise(pts, 15.0, 13, 3)) + crevice * 0.2)
h_color = mix(h_color, rust, h_rust * 0.6)
cast = 0.0011 * (micro - 0.5) + 0.0013 * (fine - 0.5)
lathe_marks = 0.00016 * np.sin(Z * 2 * math.pi / 0.021)
h_height = np.where(turned, lathe_marks + 0.0002 * (micro - 0.5), cast) + (1 - h_wear) * 0.0007
color = np.where(head[..., None], h_color, color)
rough = np.where(head, 0.56 + 0.14 * mid + 0.07 * fine - 0.2 * h_wear + turned * 0.05 + h_rust * 0.25, rough)
metal = np.where(head, np.clip(np.where(turned, 0.45, 0.7) + 0.5 * h_wear - h_rust * 0.7, 0, 1), metal)
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
dust = np.clip(settled * 0.16 + gathered * 0.28, 0, 0.6) * np.where(head | recess | can, 0.3, 1.0)
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
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_metal.png"), metal)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("flash painted", flush=True)
