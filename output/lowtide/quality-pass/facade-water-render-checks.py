"""Record diagnostics for the final facade/water in-engine captures."""
import json
from pathlib import Path
import re

folder = Path(__file__).resolve().parent
captures = ("live-facade-wear-close", "live-command-ripple-camera",
            "live-ripple-projection-oblique", "live-canal-facade-water-final")
report = {}
for name in captures:
    text = (folder / (name + "-diagnostics.txt")).read_text()
    models = re.findall(r"^(.+): modelError=(\w+); materialErrors=(\d+)$", text, re.M)
    assert len(models) >= 11 and all(error == "False" and count == "0" for _, error, count in models)
    assert text.count("downwardClear=True") == 18
    assert (folder / (name + ".png")).exists()
    report[name] = {"model_renderers": len(models), "model_errors": 0, "material_errors": 0,
                    "unobstructed_warehouse_emitters": 18}
assert "Reflection lifecycle: PASS:" in (folder / "live-command-ripple-camera-diagnostics.txt").read_text()
assert json.loads((folder / "window-cleanup-check.json").read_text())["remainingQaScenes"] == []
report["reflection_lifecycle"] = "passed"
report["remaining_qa_scenes"] = []
(folder / "facade-water-render-checks.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report, indent=2))
