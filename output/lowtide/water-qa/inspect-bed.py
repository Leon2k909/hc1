"""Inspect the existing live-imported mud mesh footprint without modifying it."""
from collections import defaultdict
from pathlib import Path

path = Path(__file__).resolve().parents[3] / "Assets/models/maps/lowtide/lowtide_fleet.obj"
verts = []
mat = None
bounds = defaultdict(lambda: [1e9, -1e9, 1e9, -1e9, 0])
for line in path.open(encoding="utf-8"):
    if line.startswith("v "):
        x, y, z = (float(v) for v in line.split()[1:4])
        verts.append((x, y, z))
    elif line.startswith("usemtl "):
        mat = line[7:].strip()
    elif line.startswith("f ") and mat and "mud" in mat:
        b = bounds[mat]
        for face in line.split()[1:]:
            v = verts[int(face.split("/")[0]) - 1]
            b[0] = min(b[0], v[0])
            b[1] = max(b[1], v[0])
            b[2] = min(b[2], v[2])
            b[3] = max(b[3], v[2])
        b[4] += 1
for name, b in sorted(bounds.items()):
    print(name, "e:", b[:2], "n:", b[2:4], "faces:", b[4])
