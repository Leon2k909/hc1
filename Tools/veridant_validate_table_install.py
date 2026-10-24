"""Verify the scoped table install and retain its final native evidence."""
import json
from pathlib import Path

from belltower_safe_imports import span
from railhead_stage_extinguisher import sha
from veridant_stage_tables import ROOT,OUT,check_top

stages=["stage-v8","stage-v9","stage-pedestal-v1"]
manifests=[json.loads((OUT/stage/"manifest.json").read_text()) for stage in stages]
installed={p:data for m in manifests for p,data in m["files"].items()}
for relative,data in installed.items():
    assert sha(ROOT/relative)==data["after"],("Shared file changed after validation",relative)
physics={}
for stem in ("buildings","dress"):
    relative=f"Assets/models/maps/veridant/veridant_{stem}.vmdl"
    original=(OUT/"stage-v2/before"/relative).read_text()
    current=(ROOT/relative).read_text()
    a,b=span(original,'_class = "PhysicsShapeList"')
    c,d=span(current,'_class = "PhysicsShapeList"')
    assert original[a:b]==current[c:d]
    physics[relative]=True
compiled=json.loads((OUT/"compiled-check.json").read_text())
assert compiled["CompleteCaps"]==11 and not compiled["HasUnsavedChanges"] and not compiled["IsPlaying"]
for model in compiled["Models"]:
    assert model["ModelAndMaterialsValid"] and all(n==64 for n in model["BaseRimVertices"])
    assert .09<=model["UvMinimum"][1]<model["UvMaximum"][1]<=.41
restore_path=ROOT/"output/veridant/quality/table-v2-complete/angled-restore.json"
restoration=json.loads(restore_path.read_text())
assert all(restoration.values())
result={"revision":"veridant-table-v2","date":"2026-10-24","instances":11,
        "geometry":check_top(),"compiled":compiled,"physics_bytes_exact":physics,
        "installed_source_sha256":{p:data["after"] for p,data in installed.items()},
        "capture":"output/veridant/quality/table-v2-complete/angled.png",
        "camera_and_scene_restoration":restoration,
        "source_helper":"Tools/veridant_table.py"}
(OUT/"validation.json").write_text(json.dumps(result,indent=2)+"\n")
source=ROOT/"Sources/Veridant/table-v2"
source.mkdir(parents=True,exist_ok=True)
(source/"installed.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"instances":11,"compiled_caps_complete":True,"pedestal_rims":64,
                  "single_panel_uvs":True,"physics_bytes_exact":True,"editor_state_preserved":True}))
