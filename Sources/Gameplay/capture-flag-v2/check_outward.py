"""Are a model's solid parts the right way out? python check_outward.py <obj> <material>

Blender's renders are two-sided, so an inside-out mesh looks fine there and only breaks in the engine, which culls back
faces. Each connected piece of a closed mesh has a signed volume, positive when its faces point outward. Prints the
pieces with a negative one and exits 1 if there are any.
"""
import sys

import numpy as np

path, wanted = sys.argv[1], sys.argv[2]
positions, faces = [], []
current = None
for line in open(path, encoding="utf-8"):
    tag = line[:2]
    if tag == "v ":
        positions.append(line[2:].split())
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif tag == "f " and current == wanted:
        faces.append([int(tok.split("/")[0]) - 1 for tok in line.split()[1:]])
v = np.array(positions, float)
f = np.array(faces, int)

parent = np.arange(len(v))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for a, b, c in f:
    ra, rb, rc = find(a), find(b), find(c)
    parent[rb] = ra
    parent[find(rc)] = ra
roots = np.array([find(a) for a in f[:, 0]])
tri = v[f]
signed = (tri[:, 0] * np.cross(tri[:, 1], tri[:, 2])).sum(1) / 6.0
inside_out = []
pieces = 0
for root in np.unique(roots):
    pick = roots == root
    volume = float(signed[pick].sum())
    if abs(volume) < 1e-3:
        continue
    pieces += 1
    if volume < 0:
        centre = tri[pick].reshape(-1, 3).mean(0)[[2, 0, 1]]
        inside_out.append((round(volume, 2), [round(float(x), 1) for x in centre], int(pick.sum())))
print(f"{pieces} solid pieces, {len(inside_out)} inside out, {sum(n for *_, n in inside_out)} of {len(f)} triangles")
for item in sorted(inside_out)[:8]:
    print("  volume", item[0], "at", item[1], "tris", item[2])
sys.exit(1 if inside_out else 0)
