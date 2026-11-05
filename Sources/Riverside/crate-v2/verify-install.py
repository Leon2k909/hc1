"""Check saved placements, precise mesh deletions, retained collision and legacy-material removal."""
from pathlib import Path
from collections import Counter
import json
import re
import sys
import numpy as np

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT / "output/asset-improvement-20261030/riverside-crate/installed"
BACKUP = OUT / "before-install"
plan = json.loads((OUT / "placements.json").read_text())
scene = json.loads((ROOT / "Assets/scenes/maps/Riverside/riverside.scene").read_text())
before = json.loads((BACKUP / "riverside.scene").read_text())
group = next(g for g in scene["GameObjects"] if g.get("Name") == "Supply Crates")
assert len(group["Children"]) == 12

def objects(nodes):
    out = {}
    for node in nodes:
        if "__guid" in node:
            out[node["__guid"]] = node
        out.update(objects(node.get("Children", [])))
    return out

old, new = objects(before["GameObjects"]), objects(scene["GameObjects"])
assert set(old) <= set(new)
assert len(set(new) - set(old)) == 13
for child, spot in zip(group["Children"], plan["spots"]):
    assert np.allclose([float(v) for v in child["Position"].split(',')], spot["position"], atol=.002)
    scale = [float(v) for v in child["Scale"].split(',')]
    assert np.allclose(scale, np.array(spot["size"]) / (30, 24, 22), atol=.0001)
    assert len(child["Components"]) == 1 and child["Components"][0]["__type"] == "Sandbox.ModelRenderer"
    model = child["Components"][0]["Model"]
    assert (model.get("Path") if isinstance(model, dict) else model) == "models/props/riverside/crate_v2/crate.vmdl"

report = json.loads((OUT / "mesh-cuts.json").read_text())
for item in report:
    path = ROOT / item.get("preview", "Assets/models/maps/riverside/" + item.get("zone", "") + ".obj")
    oldlines = (BACKUP / path.name).read_bytes().splitlines(keepends=True)
    newlines = path.read_bytes().splitlines(keepends=True)
    removed = Counter(oldlines) - Counter(newlines)
    added = Counter(newlines) - Counter(oldlines)
    assert not added
    assert sum(n for line, n in removed.items() if line.startswith(b'f ')) == item["removed_triangles"]
    assert all(line.startswith(b'f ') or line.strip() == b'usemtl rs_crate' for line in removed)
    assert b'usemtl rs_crate' not in b''.join(newlines)

physics = []
for path in (BACKUP / "assets/models").rglob("*.vmdl"):
    original = path.read_text()
    expected = re.sub(r'(?m)^[^\r\n]*from = "rs_crate\.vmat"[^\r\n]*\r?\n', '', original)
    live = ROOT / "Assets/models" / path.relative_to(BACKUP / "assets/models")
    assert live.read_text() == expected, str(live) + ": more than a material remap changed"
    physics.append(str(live.relative_to(ROOT)))
assert not list((ROOT / "Assets/materials/riverside").glob("rs_crate.vmat*"))
result = dict(saved_crates=12, replaced_live_triangles=sum(i["removed_triangles"] for i in report if "zone" in i),
              no_added_or_unrelated_removed_faces=True, retained_collision_and_other_model_settings=physics,
              legacy_material_deleted=True, existing_object_ids_preserved=True)
(OUT / "verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
