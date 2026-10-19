"""Snapshot Collider's saved detail pass without opening or changing the editor.

The archive uses the last saved lighting. The later, unreviewed bake is retained
under Sources/Collider/pending-lighting-v3, never under the archive's Assets tree.
This is a repository overlay, not a standalone game or a multiplayer release.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import zipfile

import collider_validate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output/collider"
DETAIL=OUT/"detail-v2"
STAGE=OUT/"stage"
SCENE=ROOT/"Assets/scenes/maps/Collider/collider.scene"
BUILD="detail-v2-review"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def texture_path(value):
    return value["Path"] if isinstance(value,dict) else value


def main():
    previous=read(DETAIL/"build-status.json")
    # Bind the saved native navigation evidence to the imported detail geometry.
    # Do not silently reuse these reports for a later regenerated model.
    for name,expected in previous["model_sha256"].items():
        for base in (STAGE,ROOT/"Assets"):
            assert digest(base/"models/maps/collider"/name)==expected, f"Geometry changed: {name}"

    layout=read(OUT/"layout-validation.json")
    assert layout["checked_spots"]==68 and all(layout[k]==0 for k in
        ("obstructed_or_unsupported","unreachable","exposed_retakes_pairs"))
    native=read(OUT/"native-validation.json")
    assert native["Checked"]==68 and not native["Failed"]
    assert not native["MissingModels"] and not native["MissingMaterials"]
    assert native["NavEnabled"] and not native["IsGenerating"]
    stairs=read(OUT/"stair-validation.json")
    assert stairs["Passed"] and len(stairs["Stairs"])==4
    assert all(s["Passed"] and s["PathStatus"]=="Complete" and s["UnderClear"] for s in stairs["Stairs"])
    scene_report=collider_validate.validate(SCENE,DETAIL/"scene-validation.json")
    capture=read(OUT/"captures/capture-report.json")
    assert all(capture[k] for k in ("NativeEngineCapture","GamePreserved",
                                  "SelectedDocumentPreserved","SceneDirtyStatePreserved"))

    saved=read(SCENE)
    groups={o.get("Name"):o for o in saved["GameObjects"]}
    indirect=groups["Collider indirect lighting"]["Components"][0]
    refs=groups["Reflection Probes"]["Children"]
    textures=[texture_path(indirect[k]) for k in ("IrradianceTexture","DistanceTexture","RelocationTexture")]
    for obj in refs:
        probe=obj["Components"][0]
        assert probe["Mode"]=="CustomTexture"
        textures.append(texture_path(probe["Texture"]))
    assert len(textures)==7 and all("v2" in t for t in textures), "Saved lighting changed; review its evidence first"

    files={"Assets/scenes/maps/Collider/collider.scene":SCENE}
    for path in sorted(STAGE.rglob("*")):
        if not path.is_file() or path.name=="collider.scene.json":
            continue
        relative=path.relative_to(STAGE).as_posix()
        if relative.startswith("lighting/") and relative not in {t+"_c" for t in textures}:
            continue
        saved_path=ROOT/"Assets"/relative
        assert saved_path.is_file() and digest(path)==digest(saved_path), f"Asset differs from saved build: {relative}"
        files["Assets/"+relative]=saved_path
    assert all("Assets/"+t+"_c" in files for t in textures)

    pending=read(OUT/"lighting-v3/bake-result.json")
    assert pending["Passes"]==2 and pending["SavedFinalIrradiance"]
    pending_files={}
    for name in ("distance","irradiance","relocation"):
        p=ROOT/f"Assets/lighting/collider/lighting-v3/{name}.vtex_c"
        assert p.is_file() and p.stat().st_size>0
        target=f"Sources/Collider/pending-lighting-v3/{name}.vtex_c"
        files[target]=p
        pending_files[target]=digest(p)
    for name in ("bake-result.json","indirect-light.json","relocation-status.json"):
        files["Sources/Collider/pending-lighting-v3/"+name]=OUT/"lighting-v3"/name

    for p in (ROOT/"Tools").glob("collider_*.py"):
        files[p.relative_to(ROOT).as_posix()]=p
    for p in (ROOT/"Sources/Collider").rglob("*"):
        if p.is_file() and p.suffix in (".py",".txt",".json"):
            files[p.relative_to(ROOT).as_posix()]=p
    evidence=("layout-validation.json","native-validation.json","stair-validation.json",
              "check-points.json","live-round-validation.json","captures/capture-report.json",
              "detail-v2/scene-validation.json")
    for name in evidence:
        files["output/collider/"+name]=OUT/name
    for p in (OUT/"captures").glob("*.png"):
        files[p.relative_to(ROOT).as_posix()]=p

    status={
        **previous,
        "build":BUILD,
        "checked_at":datetime.now(timezone.utc).isoformat(),
        "native_import_pending":False,
        "offline_packaging_only":True,
        "saved_scene_sha256":scene_report["scene_sha256"],
        "native_checked_positions":68,
        "native_stair_routes_passed":4,
        "accepted_lighting_revision":"lighting-v2 with reflection v2",
        "accepted_lighting_textures":textures,
        "pending_lighting":{
            "revision":"lighting-v3", "scene_saved_with_bake":False,
            "native_visual_review_passed":False, "game_preserved_during_bake":pending["GamePreserved"],
            "archive_files":pending_files,
            "note":"Retained for inspection only. A different scene started play during the bake; inspect before adopting."
        },
        "capture_note":"Six native detail-pass views precede the final darker case color and the unreviewed v3 bake. The saved menu image is the earlier native-v1 view.",
        "local_tdm_note":"The earlier local TDM test observed nine moving bots. It predates the new stair collision; native navigation was rechecked afterward.",
        "current_build_local_tdm_verified":False,
        "separate_client_multiplayer_verified":False,
        "native_performance_profiled":False,
        "remaining":["Review the final darker case finish in engine",
                     "Inspect lighting-v3 and refresh reflections before adopting it",
                     "Run a local match and a second-client multiplayer check",
                     "Measure full-match performance",
                     "Refresh the map picker image after the final native review"],
        "asset_sha256":{n:digest(p) for n,p in sorted(files.items()) if n.startswith("Assets/")},
        "evidence_sha256":{n:digest(OUT/n) for n in evidence},
    }
    status_path=DETAIL/"build-status.json"
    status_path.write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
    files["output/collider/detail-v2/build-status.json"]=status_path
    notes=(ROOT/"Sources/Collider/review-notes.txt").read_text(encoding="utf-8")
    manifest={"map":"Collider","build":BUILD,"verification":status,
              "files":[{"path":n,"size":p.stat().st_size,"sha256":digest(p)} for n,p in sorted(files.items())]}
    archive=OUT/f"collider-{BUILD}.zip"
    temporary=archive.with_suffix(".zip.partial")
    try:
        with zipfile.ZipFile(temporary,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as package:
            for name,path in sorted(files.items()):
                package.write(path,name)
            package.writestr("Collider-build-manifest.json",json.dumps(manifest,indent=2))
            package.writestr("Collider-build-notes.txt",notes)
        with zipfile.ZipFile(temporary) as package:
            assert package.testzip() is None
            for record in manifest["files"]:
                assert hashlib.sha256(package.read(record["path"])).hexdigest()==record["sha256"],record["path"]
        temporary.replace(archive)
    finally:
        if temporary.exists():
            temporary.unlink()
    (DETAIL/"package-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    current={"build":BUILD,"archive":archive.relative_to(ROOT).as_posix(),"sha256":digest(archive),
             "status":"output/collider/detail-v2/build-status.json","integrity_verified":True,
             "native_validation_pending":True}
    (OUT/"current-build.json").write_text(json.dumps(current,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({**current,"files":len(files),"bytes":archive.stat().st_size},indent=2))


if __name__=="__main__":
    main()
