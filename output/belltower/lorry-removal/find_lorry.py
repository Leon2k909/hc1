"""Belltower: find the Market Street lorry's triangles and collision boxes in the installed town models.

Builds the lorry alone with Tools/belltower_map.py's own `lorry()` (west, and mirrored with EAST_PAINTS for the east), turns
each polygon into the triangles map_kit.write_obj writes, and looks each one up in the installed OBJ by its three
vertex positions (as written, %.3f) and its material. Reads only; writes a report beside this script."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import belltower_map as BM

def lorry_model(east):
    m = K.Model()
    BM.lorry(m, (-900, 1290), 8)
    return m.mirrored(BM.EAST_PAINTS) if east else m

def triangles(model):
    out = Counter()
    for paint, items in model.polygons.items():
        for points, _ in items:
            world = [K.obj_vector(K.to_world(p)) for p in points]
            for k in range(1, len(points) - 1):
                out[(paint, frozenset((world[0], world[k], world[k + 1])))] += 1
    return out

def boxes(model):
    return [(K.vec3(K.to_world(c)), K.vec3(s), surface) for c, axes, s, surface in model.boxes]

report = {}
for name, east in (("belltower_west", False), ("belltower_east", True)):
    model = lorry_model(east)
    wanted = triangles(model)
    obj = ROOT / f"Assets/models/maps/belltower/{name}.obj"
    verts = [None]
    found = Counter(); lines = []
    paint = None
    with open(obj, encoding="utf-8") as f:
        for number, line in enumerate(f):
            if line.startswith("v "):
                verts.append(line[2:].strip())
            elif line.startswith("usemtl "):
                paint = line[7:].strip()
            elif line.startswith("f "):
                key = (paint, frozenset(verts[int(t.split("/")[0])] for t in line.split()[1:]))
                if key in wanted and found[key] < wanted[key]:
                    found[key] += 1
                    lines.append(number)
    vmdl = (ROOT / f"Assets/models/maps/belltower/{name}.vmdl").read_text(encoding="utf-8")
    box_hits = [b for b in boxes(model) if f"origin = {b[0]}" in vmdl]
    report[name] = {
        "LorryTriangles": sum(wanted.values()),
        "Matched": sum(found.values()),
        "MissingByPaint": dict(Counter(k[0] for k in wanted for _ in range(wanted[k] - found[k]))),
        "Paints": sorted({k[0] for k in wanted}),
        "Boxes": len(model.boxes), "BoxesMatched": len(box_hits), "Hulls": len(model.hulls),
        "FaceLines": lines,
        "BoxOrigins": [b[0] for b in box_hits],
    }
    print(name, {k: v for k, v in report[name].items() if k not in ("FaceLines", "BoxOrigins")})
(Path(__file__).parent / "find-report.json").write_text(json.dumps(report), encoding="utf-8")
