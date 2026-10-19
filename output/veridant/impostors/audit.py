"""Independent OBJ audit: every retained non-image triangle keeps its source geometry and UVs."""
from collections import Counter
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent

def triangles(path):
    vertices, uv = [], []
    material = None
    result = Counter()
    images = 0
    for line in path.open(encoding="utf-8"):
        if line.startswith("v "):
            vertices.append(line[2:].strip())
        elif line.startswith("vt "):
            uv.append(line[3:].strip())
        elif line.startswith("usemtl "):
            material = line.split()[1]
        elif line.startswith("f "):
            if material.startswith("vr_bay_"):
                images += 1
                continue
            corners = []
            for corner in line.split()[1:]:
                vi, ti, _ = map(int, corner.split("/"))
                corners.append(vertices[vi-1] + " / " + uv[ti-1])
            fingerprint = hashlib.blake2b((material + " | " + " | ".join(sorted(corners))).encode(), digest_size=16).digest()
            result[fingerprint] += 1
    return result, images

models = {}
for name in ("veridant_backdrop", "veridant_backdrop_props"):
    relative = Path("Assets/models/maps/veridant") / (name + ".obj")
    before, _ = triangles(root / "before-assets" / relative)
    after, images = triangles(root / "stage" / relative)
    changed = sum((after - before).values())
    assert changed == 0, (name, changed)
    models[name] = {"before": sum(before.values()), "after": sum(after.values()) + images,
                    "image_triangles": images, "changed_retained_geometry_or_uvs": changed}
record = {"models": models, "all_retained_triangles_match_original": True}
(root / "retained-geometry.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
