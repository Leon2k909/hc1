"""Legacy offline-v2 packager. Use collider_package_native.py for the reviewed build."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output/collider"
STAGE=OUT/"stage"

def main():
    layout=json.loads((OUT/"layout-validation.json").read_text())
    assert layout["checked_spots"]==68 and all(layout[key]==0 for key in
        ("obstructed_or_unsupported","unreachable","exposed_retakes_pairs")),"Layout validation has not passed"
    scene=json.loads((OUT/"scene-validation.json").read_text())
    assert scene["success"] and scene["scene_sha256"]==hashlib.sha256((STAGE/"collider.scene.json").read_bytes()).hexdigest(),"Scene validation is stale"
    assert (STAGE/"ui/maps/collider.png").read_bytes()==(OUT/"offline-preview/art.png").read_bytes(),"Staged menu image is stale"
    files={}
    for path in STAGE.rglob("*"):
        if not path.is_file(): continue
        relative=path.relative_to(STAGE).as_posix()
        target=("Assets/scenes/maps/Collider/collider.scene" if relative=="collider.scene.json" else "Assets/"+relative)
        files[target]=path
    for path in (ROOT/"Tools").glob("collider_*.py"): files[path.relative_to(ROOT).as_posix()]=path
    for path in (ROOT/"Sources/Collider").rglob("*"):
        if path.is_file() and path.suffix in (".py",".txt",".json"):
            files[path.relative_to(ROOT).as_posix()]=path
    for name in ("layout-validation.json","scene-validation.json","offline-build-status.json","offline-preview/provenance.json","offline-preview/art.png"):
        files["output/collider/"+name]=OUT/name
    for name in ("control.png","control-provenance.json"):
        path=OUT/"offline-preview"/name
        if path.is_file(): files["output/collider/offline-preview/"+name]=path
    manifest={"map":"Collider","build":"offline-v2","native_gameplay_verified":False,
              "native_lighting_verified":False,"files":[{"path":name,"size":path.stat().st_size,
              "sha256":hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in sorted(files.items())]}
    notes="""Collider — offline build

This archive contains the accelerator laboratory, its scene and all newly authored assets.
The source generators reuse map_kit, Ares and Railhead helpers already in this repository.

The reference's blue accelerator, observation window, control galleries, red access doors,
two-level atrium, stairs and equipment cover are represented in actual map geometry.
The second offline revision adds instrument displays, operator desks and chairs, a rounded
window surround, heavier structural columns, panelled machine rings and detailed equipment cases.
The preview is software-rendered with approximate light. It is not a gameplay screenshot.

All 68 placement/connectivity checks and Retakes sight checks pass. Scene references,
resource files, mode-specific spawns, objectives and Cash Grab wiring also pass offline checks.
Engine lighting, engine navmesh paths, bots and multiplayer performance are not verified.

The project's GameUtils.cs already includes Collider in MainMenuMapOrder, IsMainMenuMap
and IsMatchReadyMap. That shared file is intentionally not overwritten by this archive.

Integration: with the editor closed, extract Assets into the repository. With the editor open,
use Sources/Collider/editor/import-build.cs.txt from the native MCP session exchange directory
after staging the Assets content under output/collider/stage (the scene as collider.scene.json).
Do not overwrite an open Collider document. Compile the four Collider models and changed materials.
The menu image is an offline preview; replace it with a native capture after the lighting check.
capture.cs.txt requires an already-open Collider editor document and uses its persistent editor
camera. Its live execution is still pending; it does not create temporary scenes or bake probes.
"""
    archive=OUT/"collider-offline-v2.zip"
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as package:
        for name,path in sorted(files.items()): package.write(path,name)
        package.writestr("Collider-build-manifest.json",json.dumps(manifest,indent=2))
        package.writestr("Collider-build-notes.txt",notes)
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None,"Archive CRC verification failed"
        for record in manifest["files"]:
            assert hashlib.sha256(package.read(record["path"])).hexdigest()==record["sha256"],record["path"]
    (OUT/"build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"archive":str(archive),"files":len(files),"bytes":archive.stat().st_size,
                      "integrity_verified":True},indent=2))

if __name__=="__main__": main()
