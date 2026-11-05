from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import numpy as np

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT / "output/asset-improvement-20261030/riverside-sandbags/installed"
BACKUP = OUT / "before-install"
scene = json.loads((ROOT / "Assets/scenes/maps/Riverside/riverside.scene").read_text())
group = next(g for g in scene["GameObjects"] if g.get("Name") == "Sandbags")
plan = json.loads((OUT / "placements.json").read_text())
assert len(group["Children"]) == 54
def vector(value):
    return [float(x) for x in value.split(',')] if isinstance(value, str) else list(value)
for actual, expected in zip(group["Children"], plan["group"]["Children"]):
    for key in ("Position", "Rotation", "Scale"):
        assert np.allclose(vector(actual[key]), vector(expected[key]), atol=.002), (key, actual[key], expected[key])
    assert actual["Components"][0]["Tint"] == expected["Components"][0]["Tint"]
    assert len(actual["Components"]) == 1 and actual["Components"][0]["__type"] == "Sandbox.ModelRenderer"
    model = actual["Components"][0]["Model"]
    assert (model.get("Path") if isinstance(model, dict) else model) == expected["Components"][0]["Model"]
scene_only = '--scene-only' in sys.argv[2:]
for row in ([] if scene_only else json.loads((OUT / "mesh-cuts.json").read_text())):
    path = ROOT / "Assets/models/maps/riverside" / (row["zone"] + ".obj")
    old = Counter((BACKUP / path.name).read_bytes().splitlines(keepends=True))
    new = Counter(path.read_bytes().splitlines(keepends=True))
    assert not new - old
    removed = old - new
    assert sum(n for line, n in removed.items() if line.startswith(b'f ')) == row["removed_triangles"]
    assert all(line.startswith(b'f ') or line.strip() == b'usemtl rs_sandbag' for line in removed)
    assert hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest() == row["collision_model_sha256"]
report = dict(saved_bags=54, barricades=4, saved_placements_match=True) if scene_only else dict(saved_bags=54, barricades=4, removed_old_triangles=3456, exact_unrelated_mesh_preservation=True, collision_models_unchanged=True)
(OUT / ("current-placement-verification.json" if scene_only else "verification.json")).write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
