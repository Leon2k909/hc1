import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
folder = root / "output/belltower/bell-v2"


def read(name):
    return json.loads((folder / name).read_text(encoding="utf-8-sig"))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


manifest = read("stage/manifest.json")
publication = read("native-import.json")
live = read("game-bell-close.json")
native = read("final-check/call_tools.json")
records = [json.loads(item["text"]) for item in native["content"] if item["type"] == "text"]
assets = [r for r in records if "IsCompiledAndUpToDate" in r]
editor = next(r for r in records if "LastCompileErrors" in r)
assert len(assets) == 3 and all(r["IsCompiledAndUpToDate"] and not r["IsCompileFailed"] for r in assets)
assert editor["LastCompileSucceeded"] and editor["LastCompileErrors"] == 0
assert live["Runtime"] and live["IsPlaying"] and live["Scene"] == "belltower" and live["BellMaterialLoaded"]
assert live["CameraRestored"] and live["SceneUnchanged"] and not live["IsError"]
assert all(not r["IsError"] for r in live["Materials"])
assert publication["Imported"] == 8 and publication["EditorStatePreserved"]
matches = {p: sha(root/p) == row["after"] for p, row in manifest["files"].items()}
assert all(matches.values()), "Inspect a later shared asset change before reporting final hashes."
assert all(sha(root/p) == value for p, value in manifest["protected_sha256"].items())
result = {
    "revision": "bell-v2",
    "status": "applied_compiled_and_verified_in_live_belltower",
    "canonical_project": str(root),
    "published_files_match_stage": matches,
    "original_shared_bronze_unchanged": True,
    "collision_scene_yoke_and_all_non_bell_obj_bytes_preserved": True,
    "code_compile_errors": editor["LastCompileErrors"],
    "assets_compiled_and_up_to_date": [r["Path"] for r in assets],
    "live_new_material_loaded": live["BellMaterialLoaded"],
    "live_centre_vertices": live["Vertices"],
    "camera_restored": live["CameraRestored"],
    "scene_unchanged": live["SceneUnchanged"],
    "existing_play_session_preserved": True,
    "play_session_started_by_this_side_chat": False,
    "image": "output/belltower/bell-v2/game-bell-close.png",
    "image_sha256": sha(folder / "game-bell-close.png"),
    "editor_detail_image": "output/belltower/bell-v2/after-bell-close.png",
    "limits": ["Runtime close-up uses a temporarily framed camera; it includes the existing weapon overlay.",
               "The first diagnostic before capture is blocked by a column and is not a comparison image."],
}
(folder / "verification.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "files": len(matches), "compile_errors": 0,
                  "runtime_material_verified": True, "camera_restored": True}))
