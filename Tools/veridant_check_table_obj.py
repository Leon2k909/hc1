"""Read back the actual OBJ triangle indices at the photographed north-terrace top."""
import json
from pathlib import Path
import sys
import numpy as np

root = Path(__file__).resolve().parents[1]
for relative in (sys.argv[1:] or ["Assets/models/maps/veridant/lounger-v2/veridant_buildings-base.obj"]):
    vertices, selected = [], []
    centres = [(520.,157.5,800.),(330.,157.5,820.),(-220.,29.5,-1060.),(460.,29.5,-1240.)] if "veridant_dress" in relative else [(-110.,157.5,380.)]
    caps = [[] for _ in centres]
    paint = None
    firstface, lastvertex = None, 0
    for i, line in enumerate((root / relative).read_text().splitlines()):
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:])))
            lastvertex = i
        elif line.startswith("usemtl "):
            paint = line.split()[1]
            if firstface is None:
                firstface = i
        elif line.startswith("f ") and paint == "vr_table_honed":
            pts = np.array([vertices[int(t.split("/")[0])-1] for t in line.split()[1:]])
            selected.extend(pts)
            for j,(x,y,z) in enumerate(centres):
                if (np.max(np.abs(pts[:, 1]-y)) < .001 and
                    np.max(np.abs(pts[:, 2]-z)) < 15.1 and np.max(np.abs(pts[:, 0]-x)) < 15.1):
                    caps[j].append(float(np.cross(pts[1]-pts[0], pts[2]-pts[0])[1])*.5)
    print(json.dumps({"path": relative, "flat_triangles": list(map(len,caps)), "flat_area": list(map(sum,caps)),
                      "first_material": firstface, "last_vertex": lastvertex,
                      "new_bounds": [np.min(selected, axis=0).tolist(), np.max(selected, axis=0).tolist()]}))
    assert all(len(c)>=126 and 694<sum(c)<698 for c in caps), "The actual indexed cap must cover its full 30-inch top."
