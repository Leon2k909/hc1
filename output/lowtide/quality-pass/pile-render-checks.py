"""Verify the applied mooring-pile assets and final engine-capture diagnostics."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_piles as P

folder = Path(__file__).parent
assets = ROOT / "Assets"
stage = folder / "piles-stage"
report = {"captures": {}, "assets": {}, "materials": {}}
for name in ("live-piles-final", "live-piles-end", "live-canal-piles-final"):
    diagnostics = (folder / (name + "-diagnostics.txt")).read_text()
    models = re.findall(r"^(.+): modelError=(\w+); materialErrors=(\d+)$", diagnostics, re.M)
    assert len(models) == 15 and all(error == "False" and count == "0" for _, error, count in models)
    assert diagnostics.count("downwardClear=True") == 18
    assert "Lights: points=24; spots=0" in diagnostics
    assert "captureVersion=2" in diagnostics
    assert (folder / (name + ".png")).is_file()
    report["captures"][name] = {"renderers": 15, "model_errors": 0, "material_errors": 0,
                                 "clear_warehouse_emitters": 18}

for ext in (".obj", ".mtl", ".vmdl"):
    name = "lowtide_fleet" + ext
    current = (assets / "models/maps/lowtide" / name).read_bytes()
    assert current == (stage / name).read_bytes(), name
    report["assets"][name] = hashlib.sha256(current).hexdigest()

for relative, source in P.material_sources().items():
    path = assets / relative
    assert path.read_text() == source == (stage / "Assets" / relative).read_text(), relative
    compiled = path.with_suffix(".vmat_c")
    references = sorted(set(x.decode() for x in re.findall(
        rb"materials/[a-zA-Z0-9_./-]+[.]vtex", compiled.read_bytes())))
    assert references, relative
    dependencies = {ref: (assets / (ref + "_c")).is_file() for ref in references}
    assert all(dependencies.values()), dependencies
    report["materials"][relative] = dependencies

shader = "shaders/hc1_lowtide_pile.shader"
assert (assets / shader).read_bytes() == (stage / "Assets" / shader).read_bytes()
assert (assets / (shader + "_c")).is_file()
assert json.loads((folder / "window-cleanup-check.json").read_text())["remainingQaScenes"] == []
scope = json.loads((folder / "pile-scope-checks.json").read_text())
report["geometry"] = {"clusters": scope["clusters"], "posts": scope["posts"],
    "replacement_triangles": scope["new_triangles"], "removed_triangles": 612,
    "net_added_triangles": scope["new_triangles"] - 612,
    "collision_unchanged": scope["physics_and_model_declarations_retained"],
    "unrelated_faces_retained": scope["unrelated_faces_retained"]}
report["remaining_qa_scenes"] = []
report["performance"] = "No controlled benchmark performed"
(folder / "pile-render-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
