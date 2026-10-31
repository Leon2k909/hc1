"""Paint the traffic cone's maps from its bakes: python paint_cone.py <work dir> <output dir>

Soft orange plastic faded by the sun, with two sleeves of white prismatic sheeting, nicked at their edges and scraped. Short black tyre
rubs and pale stress marks where it has been hit, and a film of road dirt low down with specks above it. A base of black recycled
rubber, flecked and dusty. Everything is worked out in 3D, so the UV seams don't show in it.
"""
import json
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
from paint import OUT, WORK, fill_from, load, mix, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

BODY, BASE = 12, 13
facts = json.load(open(os.path.join(WORK, "cone.json")))
density, RANGE, BEND, SLEEVES, PLATE = facts["density"], facts["range"], facts["bend"], facts["sleeves"], facts["plate"]
NAME = "traffic_cone"

pos4 = load("bake_tc_pos")
nor4 = load("bake_tc_nor")
facts4 = load("bake_tc_facts")
ao4 = load("bake_tc_ao")
H, W = pos4.shape[:2]
cover = pos4[..., :3].max(-1) > 1e-3
pos = (pos4[..., :3] - 0.5) * RANGE
nor = nor4[..., :3] * 2 - 1
finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
pos, nor, finish = fill_from(cover, pos, nor, finish)
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


def stretched(sx, sy, sz, seed, octaves=3):
    return field(noise(pts * np.array((sx, sy, sz), np.float32), 1.0, seed, octaves))


edge_points = np.load(os.path.join(WORK, "cone_edges.npy"))
d, _ = cKDTree(edge_points).query(pts.astype(np.float64), k=1, distance_upper_bound=0.4, workers=4)
edge_d = field(np.where(np.isfinite(d), d, 0.4).astype(np.float32))

big = field(noise(pts, 0.22, 1, 3))
mid = field(noise(pts, 1.5, 2, 4))
fine = field(noise(pts, 9.0, 3, 3))
micro = field(noise(pts, 34.0, 4, 2))
crevice = np.clip((1 - ao) * 1.35, 0, 1)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
lean = BEND * (Z / 28.0) ** 2
radial = np.hypot(X - lean, Y)
az = np.arctan2(Y, X - lean)
wall_r = 5.6 - 4.6 / 26.8 * (Z - PLATE)

body = finish == BODY
base = finish == BASE
throat = body & (radial < 0.85) & (Z < 27.9)
# By which way it faces, not how far in it is: the dents push the outside in further than the hollow's depth.
facing_out = (nor[..., 0] * (X - lean) + nor[..., 1] * Y) / np.maximum(radial, 1e-3)
hollow = body & (Z < 5.2) & ((facing_out < 0.0) | (nor[..., 2] < -0.7))
wall = body & ~throat & ~hollow
r = np.random.default_rng(750)

# The sleeves, cut straight, with their edges lifted and torn away in places.
sleeve = np.zeros((H, W), np.float32)
to_edge = np.full((H, W), 9.0, np.float32)
for z0, z1 in SLEEVES:
    sleeve = np.maximum(sleeve, smooth(z0, z0 + 0.02, Z) * smooth(z1, z1 - 0.02, Z))
    to_edge = np.minimum(to_edge, np.minimum(np.abs(Z - z0), np.abs(Z - z1)))
sleeve = sleeve * wall
tear = smooth(0.72, 0.76, stretched(1.1, 1.1, 2.4, 31) + smooth(0.32, 0.0, to_edge) * 0.2)
sleeve_left = sleeve * (1 - tear)
# Prismatic cells, too fine to read but at arm's length, which is what makes the sheeting look like sheeting.
PITCH = 0.2
u = az * radial
row = np.floor(Z / (PITCH * 0.866))
cell_u = ((u + (row % 2) * PITCH * 0.5) / PITCH) % 1.0 - 0.5
cell_v = (Z / (PITCH * 0.866)) % 1.0 - 0.5
cell = smooth(0.46, 0.3, np.hypot(cell_u, cell_v * 0.866))

# Scratches on the wall, walked on its surface so they stay on it.
lines, widths = [], []
for _ in range(170):
    a0 = float(r.uniform(-math.pi, math.pi))
    z0 = float(r.uniform(2.0, 26.0))
    heading = float(r.uniform(0, 2 * math.pi))
    length = float(r.uniform(0.3, 2.2))
    w = float(r.uniform(0.012, 0.03))
    steps = max(4, int(length / 0.015))
    for k in range(steps):
        s = (k / (steps - 1) - 0.5) * length
        z = z0 + s * math.sin(heading)
        rad = 5.6 - 4.6 / 26.8 * (z - PLATE)
        a = a0 + s * math.cos(heading) / rad
        lines.append((rad * math.cos(a) + BEND * (z / 28.0) ** 2, rad * math.sin(a), z))
        widths.append(w * (1 - abs(k / (steps - 1) - 0.5) * 1.3))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines)).query(pts, k=1, distance_upper_bound=0.06, workers=4)
which = np.minimum(which, len(widths) - 1)
scratch = field(smooth(1.0, 0.45, np.where(np.isfinite(dist), dist, 1.0) / widths[which]).astype(np.float32)) * wall
scratch = ndi.gaussian_filter(scratch, 0.6)


def hit(angle, height, wide, high):
    """Where something struck the cone: a soft patch of the wall."""
    arc = np.angle(np.exp(1j * (az - math.radians(angle)))) * radial
    return np.exp(-((arc / wide) ** 2) - ((Z - height) / high) ** 2) * wall


struck = np.clip(hit(-35, 7.0, 2.6, 4.5) + hit(128, 18.0, 1.7, 3.2) * 0.8, 0, 1)
# Tyre rubber: a few short, nearly level rubs where a wheel caught it, with hard edges, broken up as a dry brush would be.
lines, widths = [], []
for angle, height, count in ((-35.0, 6.5, 12), (128.0, 18.5, 4)):
    for _ in range(count):
        a0 = math.radians(angle + float(r.uniform(-24, 24)))
        z0 = height + float(r.uniform(-3.0, 3.0))
        heading = float(r.uniform(-0.3, 0.3))
        length = float(r.uniform(1.0, 2.8))
        w = float(r.uniform(0.07, 0.18))
        steps = max(4, int(length / 0.03))
        for k in range(steps):
            s = (k / (steps - 1) - 0.5) * length
            z = z0 + s * math.sin(heading)
            rad = 5.6 - 4.6 / 26.8 * (z - PLATE)
            a = a0 + s * math.cos(heading) / rad
            lines.append((rad * math.cos(a) + BEND * (z / 28.0) ** 2, rad * math.sin(a), z))
            widths.append(w * (1 - abs(k / (steps - 1) - 0.5) * 1.1))
widths = np.array(widths)
dist, which = cKDTree(np.array(lines)).query(pts, k=1, distance_upper_bound=0.2, workers=4)
which = np.minimum(which, len(widths) - 1)
rub = field(smooth(1.0, 0.72, np.where(np.isfinite(dist), dist, 1.0) / widths[which]).astype(np.float32)) * wall
tyre = rub * smooth(0.3, 0.52, stretched(5.0, 5.0, 13.0, 32, 2))
# A short, wandering crease where the worst dent bent the plastic pale.
wander = (field(noise(pts, 1.1, 33, 2)) - 0.5) * 0.5
crease = np.exp(-(((np.angle(np.exp(1j * (az - math.radians(-35)))) * radial + wander) / 0.04) ** 2)) * smooth(2.2, 1.0, np.abs(Z - 7.0)) * wall
stress = np.clip(crease * 0.32, 0, 1)
seam = np.exp(-((np.angle(np.exp(1j * (az - math.radians(72)))) * radial / 0.022) ** 2)) * wall * (1 - sleeve)

color = np.zeros((H, W, 3), np.float32)
rough = np.full((H, W), 0.6, np.float32)
height = np.zeros((H, W), np.float32)

# The plastic: strongest where it's kept out of the sun, chalky towards the tip and on its weather side.
fade = np.clip(smooth(0.3, 0.72, big) * 0.55 + smooth(8.0, 28.0, Z) * 0.4 + (mid - 0.5) * 0.25, 0, 1)
orange = mix(rgb(238, 84, 16), rgb(226, 118, 62), fade) * (0.92 + 0.16 * mid[..., None])
flow = stretched(9.0, 9.0, 1.6, 34)
c_body = mix(orange, orange * 0.9, smooth(0.42, 0.72, flow) * 0.25)
c_body = mix(c_body, rgb(240, 196, 150), stress * 0.7)
c_body = mix(c_body, rgb(238, 190, 150) * (0.85 + 0.3 * fine[..., None]), scratch * (1 - sleeve) * 0.55)
r_body = 0.46 + 0.14 * mid + 0.05 * fine + fade * 0.12 + stress * 0.1 + scratch * 0.15
h_body = 0.0009 * (micro - 0.5) + 0.0012 * (flow - 0.5) - scratch * 0.0035 + seam * 0.007 - crease * 0.008

# The sheeting over it: bright, smooth and a little raised, its scrapes going to the grey backing.
white = mix(rgb(222, 224, 216), rgb(196, 196, 186), smooth(0.3, 0.75, mid))
white = white * (0.94 + 0.09 * cell[..., None])
grey_back = rgb(118, 116, 108)
c_sleeve = mix(white, grey_back, np.clip(scratch * 1.1 + smooth(0.8, 0.86, fine + stress * 0.3) * 0.55, 0, 1))
c_body = mix(c_body, c_sleeve, sleeve_left)
r_body = r_body * (1 - sleeve_left) + (0.32 + 0.1 * (1 - cell) + 0.1 * mid + scratch * 0.25) * sleeve_left
h_body = h_body + ndi.gaussian_filter(sleeve_left, 0.8) * 0.009 + cell * sleeve_left * 0.0013

# Everything the wall has picked up, over plastic and sheeting alike.
streak = stretched(6.0, 6.0, 0.28, 35)
runs = smooth(0.5, 0.74, streak) * smooth(0.3, 0.7, mid) * wall
c_body = mix(c_body, rgb(92, 68, 46), runs * 0.12)
# Road film: a soft tide line low on the wall, with small dried specks splashed above it.
splash = smooth(7.5, 1.2, Z + (mid - 0.5) * 1.6)
specks = smooth(0.68, 0.8, field(noise(pts, 24.0, 36, 2))) * smooth(9.0, 2.0, Z)
mud = np.clip(splash * 0.62 + specks * 0.6, 0, 1) * wall
c_body = mix(c_body, rgb(104, 88, 66) * (0.84 + 0.32 * fine[..., None]), mud * 0.62)
r_body = r_body * (1 - mud) + 0.86 * mud
h_body = h_body + specks * wall * 0.0016
# The tyre rubs came last, so they sit on the dirt.
c_body = mix(c_body, rgb(28, 27, 27) * (0.85 + 0.3 * fine[..., None]), tyre * 0.85)
r_body = r_body * (1 - tyre * 0.8) + 0.72 * tyre * 0.8
# The open throat is dark with what has fallen in, and the hollow underneath is the bare plastic in shadow.
c_body = np.where(throat[..., None], rgb(34, 26, 20), c_body)
r_body = np.where(throat, 0.9, r_body)
c_body = np.where(hollow[..., None], rgb(58, 26, 12) * (0.8 + 0.4 * mid[..., None]), c_body)
r_body = np.where(hollow, 0.66, r_body)
h_body = np.where(hollow, 0.0, h_body)

color = np.where(body[..., None], c_body, color)
rough = np.where(body, r_body, rough)
height = np.where(body, h_body, height)

# The base: black recycled rubber with pale flecks in it, pebbled, rubbed grey on its corners and edges.
flecks = smooth(0.7, 0.76, field(noise(pts, 16.0, 37, 2)))
c_base = rgb(38, 38, 39) * (0.82 + 0.36 * fine[..., None])
c_base = mix(c_base, rgb(92, 88, 80), flecks * 0.5)
worn = smooth(0.14, 0.015, edge_d) * smooth(0.3, 0.7, mid * 0.5 + fine * 0.5)
c_base = mix(c_base, rgb(74, 72, 68), worn * 0.7)
r_base = 0.78 + 0.12 * fine - worn * 0.22
h_base = 0.0042 * (field(noise(pts, 14.0, 38, 2)) - 0.5) + 0.0016 * (micro - 0.5) - flecks * 0.001
color = np.where(base[..., None], c_base, color)
rough = np.where(base, r_base, rough)
height = np.where(base, h_base, height)

# Dust: settled on the base's top, gathered in the corners, dark grime packed right in.
upward = np.clip(nor[..., 2], 0, 1)
settled = smooth(0.45, 0.95, upward * 0.7 + (mid - 0.5) * 0.5) * np.where(base, 1.0, 0.35)
gathered = smooth(0.08, 0.5, crevice) * smooth(0.3, 0.7, mid * 0.6 + fine * 0.4)
dust = np.clip(settled * 0.62 + gathered * 0.5, 0, 0.82) * (1 - throat) * (1 - hollow)
color = mix(color, rgb(128, 118, 98) * (0.82 + 0.36 * fine[..., None]), dust)
rough = rough * (1 - dust) + 0.92 * dust
grime = np.clip(smooth(0.42, 0.9, crevice + (mid - 0.5) * 0.45) * 0.6, 0, 0.8)
color = mix(color, rgb(52, 46, 38) * (0.72 + 0.5 * fine[..., None]), grime)
rough = rough * (1 - grime) + 0.88 * grime

color = color * (0.72 + 0.28 * ao[..., None])
normal = to_normal(ndi.gaussian_filter(fill_from(cover, height)[0], 0.5), density, 1.0)
# A slope worked out across an island's border sees the flat gutter and draws a line along the seam, so a wide island's border takes
# its normal from just inside. Islands too thin to have an inside, like bevels, keep what they have.
inside = ndi.binary_erosion(cover, iterations=2)
wide = ndi.binary_dilation(inside, iterations=3) & cover
normal = fill_from(inside | (cover & ~wide), normal)[0]
color, rough, normal = fill_from(cover, np.clip(color, 0, 1), np.clip(rough, 0.08, 1), normal)
save_rgb(os.path.join(OUT, f"{NAME}_color.png"), color)
save_gray(os.path.join(OUT, f"{NAME}_rough.png"), rough)
save_gray(os.path.join(OUT, f"{NAME}_ao.png"), np.clip(ao * 1.03, 0, 1))
save_normal(os.path.join(OUT, f"{NAME}_normal.png"), normal)
print("traffic cone painted", flush=True)
