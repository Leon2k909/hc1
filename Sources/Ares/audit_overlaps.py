"""Find faces in the Ares meshes that nearly coincide and overlap, which is what z-fights.

python audit_overlaps.py <project root> [camera x y z yaw pitch]

Compares every axis-aligned face within 0.4 inches of a parallel one, across all the map's meshes. With a camera pose it
ranks them by distance from that view's centre line. Read-only.
"""
import collections
import math
import os
import sys

import numpy as np

ROOT = sys.argv[1]
MODELS = os.path.join(ROOT, "Assets", "models", "maps", "ares")
FILES = ["ares_hall.obj", "ares_dressing.obj", "ares_reactor.obj", "ares_backdrop.obj", "stair-rear-wall/ares_stair_rear_closures.obj"]
TOLERANCE = 0.4
MIN_OVERLAP = 0.6


def load(path):
    v, tris, mats = [], [], []
    current = None
    for line in open(path, encoding="utf-8", errors="ignore"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = line[2:].split()[:3]
            v.append((float(c), float(a), float(b)))
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif tag == "f ":
            ids = [int(tok.split("/")[0]) - 1 for tok in line.split()[1:]]
            for k in range(1, len(ids) - 1):
                tris.append((ids[0], ids[k], ids[k + 1]))
                mats.append(current)
    return np.array(v), np.array(tris), mats


records = []
for name in FILES:
    path = os.path.join(MODELS, name)
    if not os.path.exists(path):
        continue
    v, t, mats = load(path)
    tri = v[t]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(n, axis=1) * 0.5
    unit = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    print(name, "triangles", len(t))
    for axis in range(3):
        for sign in (1, -1):
            pick = np.nonzero((unit[:, axis] * sign > 0.999) & (area > 0.05))[0]
            for i in pick:
                others = [k for k in range(3) if k != axis]
                records.append((axis, sign, float(tri[i, :, axis].mean()), tri[i, :, others[0]].min(), tri[i, :, others[0]].max(), tri[i, :, others[1]].min(), tri[i, :, others[1]].max(), name, mats[i], float(area[i])))

print("axis-aligned faces", len(records))
by_face = collections.defaultdict(list)
for r in records:
    by_face[(r[0], r[1])].append(r)
found = []
for key, faces in by_face.items():
    faces.sort(key=lambda r: r[2])
    coords = np.array([f[2] for f in faces])
    a0 = np.array([f[3] for f in faces])
    a1 = np.array([f[4] for f in faces])
    b0 = np.array([f[5] for f in faces])
    b1 = np.array([f[6] for f in faces])
    for i, f in enumerate(faces):
        j = np.searchsorted(coords, f[2] + TOLERANCE, side="right")
        if j <= i + 1:
            continue
        rng = np.arange(i + 1, j)
        ov_a = np.minimum(a1[rng], f[4]) - np.maximum(a0[rng], f[3])
        ov_b = np.minimum(b1[rng], f[6]) - np.maximum(b0[rng], f[5])
        hit = rng[(ov_a > 0.05) & (ov_b > 0.05) & (ov_a * ov_b > MIN_OVERLAP)]
        for k in hit:
            g = faces[k]
            if g[8] == f[8] and g[7] == f[7] and abs(g[2] - f[2]) < 1e-3:
                # The two triangles of one quad, or a mesh's own neighbours in one material, look the same either way.
                continue
            found.append((key[0], key[1], f, g))
print("near-coincident overlapping pairs", len(found))

clusters = collections.defaultdict(lambda: dict(count=0, a0=1e9, a1=-1e9, b0=1e9, b1=-1e9, gap=0.0))
for axis, sign, f, g in found:
    pair = tuple(sorted(((f[7].rsplit("/", 1)[-1], f[8]), (g[7].rsplit("/", 1)[-1], g[8]))))
    key = (axis, sign, round(f[2], 1), pair)
    c = clusters[key]
    c["count"] += 1
    c["a0"], c["a1"] = min(c["a0"], max(f[3], g[3])), max(c["a1"], min(f[4], g[4]))
    c["b0"], c["b1"] = min(c["b0"], max(f[5], g[5])), max(c["b1"], min(f[6], g[6]))
    c["gap"] = max(c["gap"], abs(f[2] - g[2]))

camera = None
if len(sys.argv) >= 7:
    x, y, z, yaw, pitch = map(float, sys.argv[2:7])
    cy, sy, cp, sp = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    camera = (np.array((x, y, z)), np.array((cy * cp, sy * cp, -sp)))
rows = []
for (axis, sign, coord, pair), c in clusters.items():
    others = [k for k in range(3) if k != axis]
    centre = np.zeros(3)
    centre[axis] = coord
    centre[others[0]] = (c["a0"] + c["a1"]) / 2
    centre[others[1]] = (c["b0"] + c["b1"]) / 2
    miss = dist = 0.0
    if camera is not None:
        d = centre - camera[0]
        dist = float(d @ camera[1])
        miss = float(np.linalg.norm(d - camera[1] * dist))
    rows.append((miss if dist > 0 else 1e6, dist, "XYZ"[axis] + ("+" if sign > 0 else "-"), coord, c, pair, centre))
rows.sort(key=lambda r: r[0])
only = os.environ.get("AUDIT_ONLY")
if only:
    rows = [r for r in rows if only in r[5][0][0] or only in r[5][1][0]]
    rows.sort(key=lambda r: -(r[4]["a1"] - r[4]["a0"]) * (r[4]["b1"] - r[4]["b0"]))
for miss, dist, face, coord, c, pair, centre in rows[:24]:
    print(f"{face} {coord:8.1f} centre {np.round(centre, 1).tolist()} size {c['a1'] - c['a0']:.1f}x{c['b1'] - c['b0']:.1f} gap {c['gap']:.3f} n{c['count']} off-axis {miss:.0f} dist {dist:.0f}  {pair[0][1]}[{pair[0][0][:14]}] / {pair[1][1]}[{pair[1][0][:14]}]")
print("clusters", len(rows))
