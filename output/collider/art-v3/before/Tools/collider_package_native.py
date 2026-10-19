"""Package the reviewed Collider build as an overlay for the existing hc1 repository."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output/collider"
STAGE=OUT/"stage"
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name): return json.loads((OUT/name).read_text())

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--build",default="native-v2")
    args=parser.parse_args()
    assert args.build.replace("-","").isalnum(),"Use a simple build name"
    layout=read("layout-validation.json")
    assert layout["checked_spots"]==68 and all(layout[k]==0 for k in
        ("obstructed_or_unsupported","unreachable","exposed_retakes_pairs"))
    scene=read("scene-validation.json")
    assert scene["success"] and scene["scene_sha256"]==digest(STAGE/"collider.scene.json"),"Scene validation is stale"
    assert (STAGE/"collider.scene.json").read_bytes()==(ROOT/"Assets/scenes/maps/Collider/collider.scene").read_bytes(),"Stage differs from the saved document"
    native=read("native-validation.json")
    assert native["Checked"]==68 and not native["Failed"] and not native["MissingModels"] and not native["MissingMaterials"]
    assert native["ModelCount"]==4 and native["SceneSha256"]==scene["scene_sha256"],"Native validation is stale"
    assert native["NavEnabled"] and not native["IsGenerating"]
    live=read("live-round-validation.json")
    assert live["GameMode"]=="tdm" and live["PlayerCameraSelected"] and live["MovingBots"]>0
    assert live["SceneSha256"]==scene["scene_sha256"],"Live check is stale"
    stairs=read("stair-validation.json")
    assert stairs["Passed"]
    capture=read("captures/capture-report.json")
    assert capture["NativeEngineCapture"] and capture["GamePreserved"] and capture["SelectedDocumentPreserved"]
    assert capture["SavedSceneCurrent"] and capture["SavedSceneSha256"]==scene["scene_sha256"],"Captures are stale"
    review=read("lighting-review.json")
    assert review["Success"] and review["SceneSha256"]==scene["scene_sha256"],"Lighting needs review"
    assert (STAGE/"ui/maps/collider.png").read_bytes()==(OUT/"captures/art.png").read_bytes(),"Menu image is stale"
    lighting=json.loads((ROOT/"Sources/Collider/lighting/indirect-light.json").read_text())["Components"][0]
    reflections=json.loads((ROOT/"Sources/Collider/lighting/reflections.json").read_text())
    def texture_path(value): return value["Path"] if isinstance(value,dict) else value
    textures=[texture_path(lighting[k]) for k in ("IrradianceTexture","DistanceTexture","RelocationTexture")]
    for obj in reflections:
        probe=obj["Components"][0]
        assert probe["Mode"]=="CustomTexture"
        textures.append(texture_path(probe["Texture"]))
    assert len(textures)==7
    for path in textures:
        assert digest(STAGE/(path+"_c"))==digest(ROOT/"Assets"/(path+"_c"))
    network=read("network-validation.json") if (OUT/"network-validation.json").exists() else {}
    performance=read("performance-validation.json") if (OUT/"performance-validation.json").exists() else {}
    network_verified=network.get("Success",False) and network.get("SceneSha256")==scene["scene_sha256"]
    performance_verified=performance.get("NativeEngineProfile",False) and performance.get("SceneSha256")==scene["scene_sha256"]
    network_snapshots=[]
    if network_verified:
        for snapshot in network["Snapshots"]:
            path=Path(snapshot["Path"])
            assert path.resolve().is_relative_to((OUT/"network").resolve()),"Network snapshot is outside its evidence directory"
            assert digest(path)==snapshot["Sha256"],"Network evidence changed after verification"
            network_snapshots.append(path)
        assert len(network_snapshots)==4
        assert read("network-test-state.json").get("RestoredAt"),"Restore temporary test settings first"
        assert json.loads((OUT/"owned-client.json").read_text(encoding="utf-8-sig")).get("ClosedAt"),"Close the owned test client first"
    status={"build":args.build,"checked_at":datetime.now(timezone.utc).isoformat(),
        "native_import_pending":False,"native_lighting_verified":True,"native_navigation_verified":True,
        "native_local_tdm_verified":True,"separate_client_multiplayer_verified":network_verified,"native_performance_profiled":performance_verified,
        "scene_sha256":scene["scene_sha256"],"native_checked_positions":68,
        "tdm_moving_bots":live["MovingBots"],"tdm_connections":live["Connections"],"lighting_textures":textures,
        "separate_client_connections":len(network["Host"]["Connections"]) if network_verified else None,
        "geometry_note":"Current saved scene, all four stairs, native views and local TDM verified after the services and lighting pass.",
        "source_sha256":{p.relative_to(ROOT).as_posix():digest(p) for p in sorted((ROOT/"Tools").glob("collider_*.py"))},
        "remaining":([] if network_verified else ["Separate-client multiplayer check"])+([] if performance_verified else ["Match performance measurement"])}
    (OUT/"native-build-status.json").write_text(json.dumps(status,indent=2)+"\n")
    files={}
    for p in STAGE.rglob("*"):
        if p.is_file():
            rel=p.relative_to(STAGE).as_posix()
            if rel.startswith("lighting/") and rel not in {path+"_c" for path in textures}: continue
            if rel.startswith(("models/","materials/")) and not rel.endswith("_c"):
                assert (ROOT/"Assets"/rel).is_file() and digest(p)==digest(ROOT/"Assets"/rel),"Stage asset differs from the editor build: "+rel
            files["Assets/scenes/maps/Collider/collider.scene" if rel=="collider.scene.json" else "Assets/"+rel]=p
    for p in (ROOT/"Tools").glob("collider_*.py"): files[p.relative_to(ROOT).as_posix()]=p
    for p in (ROOT/"Sources/Collider").rglob("*"):
        if p.is_file() and p.suffix in (".py",".txt",".json"): files[p.relative_to(ROOT).as_posix()]=p
    for name in ("layout-validation.json","scene-validation.json","native-validation.json","live-round-validation.json","stair-validation.json",
                 "lighting-review.json","native-build-status.json","check-points.json","captures/capture-report.json","reflections/validation.json"):
        files["output/collider/"+name]=OUT/name
    for name in ("network-validation.json","performance-validation.json"):
        if (OUT/name).exists(): files["output/collider/"+name]=OUT/name
    for p in network_snapshots: files[p.relative_to(ROOT).as_posix()]=p
    for p in (OUT/"captures").glob("*.png"): files[p.relative_to(ROOT).as_posix()]=p
    manifest={"map":"Collider","build":args.build,"verification":status,
        "files":[{"path":name,"size":p.stat().st_size,"sha256":digest(p)} for name,p in sorted(files.items())]}
    notes="""Collider — native editor build

Saved and selectable in hc1's multiplayer map picker. Includes the observation
chamber, two-level hall, control displays, red doors, four stairs and cover.
All 68 authored gameplay positions passed native floor, clearance and complete
navmesh path checks. A local TDM session spawned the correct player camera and
moving bots. The manifest records separate-client and performance verification
individually; only checks tied to this saved scene count as verified. The network
report includes ownership, map resource identity and before/after positions from
both processes. Position replication uses a controlled QA teleport; it does not
claim keyboard traversal or Internet latency testing. Performance captures are
short editor-hosted samples, not a full-match benchmark.

Art, floor, observation and control images are native editor captures.
The menu image uses art.png. Seven compiled lighting textures ship with this build: a two-pass
GI bake and four static reflections. Reflection sources use ordinary native
camera faces and the sky texture compiler, avoiding the unstable GPU GGX path.

This archive overlays the existing hc1 repository and uses its shared materials,
helpers, prefabs and gameplay code. GameUtils.cs already registers Collider and
is intentionally not overwritten. Use the native import script with the editor
open; never overwrite an open Collider document. Regeneration retains the
accepted lighting cache. The current build includes beveled cases and railings,
open stairs, service-room glazing, ceiling pipe fittings and cable trays.
"""
    archive=OUT/("collider-"+args.build+".zip")
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as package:
        for name,p in sorted(files.items()): package.write(p,name)
        package.writestr("Collider-build-manifest.json",json.dumps(manifest,indent=2))
        package.writestr("Collider-build-notes.txt",notes)
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        for record in manifest["files"]:
            assert hashlib.sha256(package.read(record["path"])).hexdigest()==record["sha256"],record["path"]
    (OUT/"build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (OUT/"current-build.json").write_text(json.dumps({"build":args.build,"archive":archive.relative_to(ROOT).as_posix(),
        "sha256":digest(archive),"status":"output/collider/native-build-status.json","integrity_verified":True,
        "native_validation_pending":False,"package_predates_worktree":False},indent=2)+"\n")
    print(json.dumps({"archive":str(archive),"files":len(files),"bytes":archive.stat().st_size,"integrity_verified":True},indent=2))

if __name__=="__main__": main()
