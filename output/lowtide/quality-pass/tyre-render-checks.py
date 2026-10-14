"""Verify the final tyre captures, resources and preservation of the pile pass."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT / "Tools"))
import lowtide_tyres as T

folder = Path(__file__).parent
assets,stage = ROOT / "Assets",folder / "tyres-stage"
report = {"captures":{},"assets":{}}
for name in ("live-tyres-final","live-tyres-low","live-canal-timber-tyres-final"):
    text = (folder / (name+"-diagnostics.txt")).read_text()
    models = re.findall(r"^(.+): modelError=(\w+); materialErrors=(\d+)$",text,re.M)
    assert len(models)==15 and all(e=="False" and n=="0" for _,e,n in models)
    assert text.count("downwardClear=True")==18
    assert "Lights: points=24; spots=0" in text
    assert (folder / (name+".png")).is_file()
    report["captures"][name] = {"renderers":15,"model_errors":0,"material_errors":0,"clear_emitters":18}
pile_report = json.loads((folder / "pile-render-checks.json").read_text())
for ext in (".obj",".mtl",".vmdl"):
    name = "lowtide_fleet"+ext
    current = (assets / "models/maps/lowtide" / name).read_bytes()
    assert current == (stage / name).read_bytes(),name
    prior = (folder / "tyres-before/Assets/models/maps/lowtide" / name).read_bytes()
    assert hashlib.sha256(prior).hexdigest()==pile_report["assets"][name]
    report["assets"][name] = hashlib.sha256(current).hexdigest()
assert (assets / T.RESOURCE).read_text()==T.material_source()
compiled = (assets / T.RESOURCE).with_suffix(".vmat_c")
references = sorted(set(x.decode() for x in re.findall(rb"materials/[a-zA-Z0-9_./-]+[.]vtex",compiled.read_bytes())))
assert references
dependencies = {ref:(assets / (ref+"_c")).is_file() for ref in references}
assert all(dependencies.values()),dependencies
report["texture_dependencies"] = dependencies
assert json.loads((folder / "window-cleanup-check.json").read_text())["remainingQaScenes"]==[]
report["remaining_qa_scenes"] = []
report["pile_snapshot_preserved_before_tyre_patch"] = True
report["geometry_scope_report"] = "tyre-scope-checks.json"
report["performance"] = "No controlled benchmark performed"
(folder / "tyre-render-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
