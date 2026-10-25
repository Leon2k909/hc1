"""Place the twelve authored shrubs with undoable native editor tools."""
import json
import os
from pathlib import Path
import subprocess
import sys
import winreg

ROOT = Path.cwd()
OUT = ROOT / "output/veridant/planter-bushes-v1"
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import veridant_planter_bushes as B

engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
cli = str(Path(engine) / "bin/managed/sbox-cli.exe")
record = []

def call(name, args=None):
    result = subprocess.run([cli, "--call", name, json.dumps(args or {})], capture_output=True, text=True)
    record.append(dict(tool=name, arguments=args or {}, exit_code=result.returncode, output=result.stdout, error=result.stderr))
    (OUT / "scene-tool-receipts.json").write_text(json.dumps(record, indent=2))
    if result.returncode:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)

status = call("editor_status")
assert status["ActiveScenePath"] == "scenes/maps/veridant/veridant.scene"
assert not status["IsPlaying"] and not status["SceneHasUnsavedChanges"]
assert Path(status["Paths"]["ProjectRoot"]).resolve() == ROOT
existing = call("find_game_objects", {"name": B.GROUP})
assert existing["Total"] == 0, "Existing group: inspect it instead of retrying."
baseline = json.loads((OUT / "stage/baseline/Assets/scenes/maps/veridant/veridant.scene").read_text())
world = next(go for go in baseline["GameObjects"] if go.get("Name") == "Veridant")
group = call("create_game_object", {"name": B.GROUP, "parent": world["__guid"]})
for p in B.props():
    call("spawn_model", dict(model=p["path"], name=p["name"], parent=group["Id"],
                              position=K.vec(K.to_world(p["position"])), angles=f"0,{p['yaw']},0",
                              scale=K.vec(p["scale"])))
saved = call("save_scene")
print(json.dumps({"CreatedBushes": len(B.PLANTS), "Group": group, "Saved": saved}))
