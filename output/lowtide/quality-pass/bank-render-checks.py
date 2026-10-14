"""Verify current bank assets and the final warm-exposure engine captures."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
folder = Path(__file__).parent
stage = folder / "banks-stage"
report = {}
for name in ("live-bank-final-close", "live-bank-final-oblique", "live-canal-bank-final"):
    diagnostics = (folder / (name + "-diagnostics.txt")).read_text()
    models = re.findall(r"^(.+): modelError=(\w+); materialErrors=(\d+)$", diagnostics, re.M)
    assert len(models) == 15 and all(error == "False" and count == "0" for _, error, count in models)
    assert diagnostics.count("downwardClear=True") == 18
    assert (folder / (name + ".png")).exists()
    report[name] = {"model_renderers": len(models), "model_errors": 0, "material_errors": 0,
                    "unobstructed_warehouse_emitters": 18}
for name in ("lowtide_marine", "lowtide_finish"):
    for ext in (".obj", ".mtl", ".vmdl"):
        assert (ROOT / "Assets/models/maps/lowtide" / (name + ext)).read_bytes() == (stage / (name + ext)).read_bytes()
for relative, source in json.loads((stage / "materials.json").read_text()).items():
    assert (ROOT / "Assets" / relative).read_text() == source
assert (ROOT / "Assets/shaders/hc1_lowtide_stone.shader").read_bytes() == (stage / "hc1_lowtide_stone.shader").read_bytes()
assert json.loads((folder / "window-cleanup-check.json").read_text())["remainingQaScenes"] == []
report["remaining_qa_scenes"] = []
report["saved_assets_match_validated_stage"] = True
report["performance"] = "No controlled benchmark performed"
(folder / "bank-render-checks.json").write_text(json.dumps(report, indent=2) + "\n")
scope = json.loads((folder / "bank-scope-checks.json").read_text())
scope["engine_validation"] = "Geometry checks only; engine evidence is recorded separately in bank-render-checks.json"
(folder / "bank-scope-checks.json").write_text(json.dumps(scope, indent=2) + "\n")
print(json.dumps(report, indent=2))
