"""Replace only six known pile clusters in the authored Fleet asset."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
import lowtide_piles as P
from lowtide_brick import metadata

folder = Path(__file__).parent
before = folder / "piles-before"
stage = folder / "piles-stage"
stage.mkdir(exist_ok=True)
manifest = json.loads((before / "manifest.json").read_text())
for relative, expected in manifest.items():
    if relative.startswith("Assets/"):
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, f"Concurrent change: {relative}"
spec = importlib.util.spec_from_file_location("lowtide_before_piles", before / "Tools/lowtide_map.py")
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
previous, replacement = K.Model(), K.Model()
for e, n in P.POSITIONS:
    old.piles(previous, e, n)
    L.piles(replacement, e, n)
assert len(previous.boxes) == len(replacement.boxes) == 6
for a, b in zip(previous.boxes, replacement.boxes):
    assert a[3] == b[3]
    assert all(np.array_equal(x, y) for x, y in zip(a[:3], b[:3]))
assert previous.hulls == replacement.hulls == []
old.configure(previous)
L.configure(replacement)
K.write_obj(stage / "original-piles.obj", previous, "original-piles")
K.write_obj(stage / "replacement-piles.obj", replacement, "replacement-piles")


def face_keys(rows):
    vertices, result, paint = [], {}, None
    for i, row in enumerate(rows):
        if row.startswith("v "):
            vertices.append(tuple(row.split()[1:]))
        elif row.startswith("usemtl "):
            paint = row.split()[1]
        elif row.startswith("f "):
            points = tuple(sorted(vertices[int(token.split("/")[0])-1] for token in row.split()[1:]))
            result[i] = (paint, points)
    return result


original = (before / "Assets/models/maps/lowtide/lowtide_fleet.obj").read_text().splitlines()
expected = Counter(face_keys((stage / "original-piles.obj").read_text().splitlines()).values())
remaining = expected.copy()
removed = set()
for index, key in face_keys(original).items():
    if remaining[key] > 0:
        removed.add(index)
        remaining[key] -= 1
assert not +remaining, f"Authored pile faces don't match original generator: {+remaining}"
assert len(removed) == sum(expected.values())
counts = [sum(row.startswith(prefix) for row in original) for prefix in ("v ", "vt ", "vn ")]
updated = [row for index, row in enumerate(original) if index not in removed]
updated.append("# Worn pile clusters: existing vertex/UV/normal records and unrelated faces preserved")
for row in (stage / "replacement-piles.obj").read_text().splitlines():
    if row.startswith(("mtllib ", "o ", "#")):
        continue
    if row.startswith("f "):
        row = "f " + " ".join("/".join(str(int(index)+counts[k]) for k, index in enumerate(token.split("/"))) for token in row.split()[1:])
    updated.append(row)
K.write_text(stage / "lowtide_fleet.obj", "\n".join(updated)+"\n")
mtl = (before / "Assets/models/maps/lowtide/lowtide_fleet.mtl").read_text()
assert not any(f"newmtl {paint}\n" in mtl for paint in P.PAINTS)
K.write_text(stage / "lowtide_fleet.mtl", mtl + (stage / "replacement-piles.mtl").read_text())
vmdl = (before / "Assets/models/maps/lowtide/lowtide_fleet.vmdl").read_text()
anchor = "\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n"
assert vmdl.count(anchor) == 1
new_remaps = "".join(f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{P.RESOURCE}/{paint}.vmat" }},\n' for paint in P.PAINTS)
K.write_text(stage / "lowtide_fleet.vmdl", vmdl.replace(anchor, anchor+new_remaps))
assets = stage / "Assets"
P.bake_textures(assets / P.RESOURCE)
for relative, text in P.material_sources().items():
    K.write_text(assets / relative, text)
shader = assets / "shaders/hc1_lowtide_pile.shader"
shader.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(folder / "pile-timber.shader", shader)
for path in assets.rglob("*"):
    if path.is_file() and path.suffix != ".meta":
        guid = uuid.uuid5(uuid.NAMESPACE_URL, path.relative_to(assets).as_posix())
        K.write_text(Path(str(path)+".meta"), json.dumps({"guid": str(guid)}, indent=2)+"\n")
report = {"removed_triangles": len(removed), "replacement_triangles": replacement.triangle_count(),
    "added_triangles": replacement.triangle_count()-len(removed), "clusters": 6, "posts": 18,
    "collision_boxes_unchanged": True, "unrelated_obj_records_unchanged": True,
    "original_sha256": manifest, "materials": list(P.material_sources())}
(stage / "manifest.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({k: v for k, v in report.items() if k != "original_sha256"}, indent=2))
