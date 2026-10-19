"""Record the verified production state without altering historical evidence."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rel(path):
    return path.relative_to(ROOT).as_posix()

manifest = read(BASE / "manifest.json")
for name, expected in manifest["staged_files"].items():
    assert sha(ROOT / name) == expected, name
for name, expected in manifest["protected_models"].items():
    if not name.endswith(".obj"):
        assert sha(ROOT / name.replace("\\", "/")) == expected, name
installed = read(BASE / "production-import.json")
assert sha(ROOT / "Assets/scenes/maps/Lowtide/lowtide.scene") == installed["SceneHash"]
readback = read(BASE / "production-readback.json")
assert readback["AllMatch"]
grates = read(BASE / "grate-verification.json")
assert len(grates["grates"]) == 24
capture = read(BASE / "production-review/capture.json")
assert capture["TabRestored"] and not capture["capture"]["modelErrors"] and not capture["capture"]["materialErrors"]
retired = read(BASE / "review-retired.json")
assert len(retired["ArchivedFiles"]) == 26
now = datetime.now(timezone.utc).isoformat()
path = ROOT / "Sources/Lowtide/construction/recomposed-status.json"
status = read(path)
status.update({
    "status": "installed_native_visual_review_complete",
    "observed_utc": now,
    "project_root": str(ROOT),
    "production_changed": True,
    "live_models_unchanged": False,
    "native_accepted": True,
    "native_acceptance_scope": "Geometry, materials and still-image appearance; gameplay performance and temporal stability remain open.",
    "canonical_generator_integrated": True,
    "canonical_generators": ["Tools/lowtide_map.py", "Tools/lowtide_finish.py", "Tools/lowtide_construction.py"],
    "canonical_verification": rel(BASE / "canonical-verification.json"),
    "installed_files": manifest["staged_files"],
    "production_import": rel(BASE / "production-import.json"),
    "native_mesh_readback": rel(BASE / "production-readback.json"),
    "native_triangles": {m["name"]: m["Triangles"] for m in readback["models"]},
    "source_triangle_delta": 287048,
    "material_slots_added": 0,
    "visual_review": {"comparison_images": 20, "production_images": 5, "comparison_directory": rel(BASE / "native-review"), "production_capture": rel(BASE / "production-review/capture.json")},
    "preserved_grates": 24,
    "grate_verification": rel(BASE / "grate-verification.json"),
    "scene_sha256": installed["SceneHash"],
    "scene_changed": False,
    "collision_changed": False,
    "review_assets_archived": rel(BASE / "review-retired.json"),
    "performance_measured": False,
    "temporal_verification_complete": False,
    "overall_AAA_verified": False,
    "note": "Scoped construction is installed and reproduced by the canonical generators. All 24 street grates remain intact. Production native mesh data matches the reviewed candidates; 25 native images were reviewed. Discard mixed-scene performance samples; a controlled gameplay benchmark remains required. Historical manifests retain their original pre-import snapshots.",
})
write(path, status)

path = ROOT / "Sources/Lowtide/drainage/grate-status.json"
status = read(path)
status.setdefault("initial_import_files", dict(status["installed_files"]))
status["installed_files"] = {n: sha(ROOT / n) for n in status["installed_files"]}
status.setdefault("initial_editor_restoration", status["current_editor_state"])
status.update({"observed_utc": now, "subsequent_construction": "Sources/Lowtide/construction/recomposed-status.json", "latest_native_geometry_evidence": rel(BASE / "grate-verification.json"), "current_editor_state": "Spillway edit tab restored after production capture; preserved the user's subsequently stopped play state."})
write(path, status)

path = ROOT / "Sources/Lowtide/construction/checkout-status.json"
status = read(path)
status.update({"status": "grates_and_construction_installed_other_candidates_pending", "observed_utc": now, "project_root": str(ROOT), "live_assets_or_code_changed": True, "latest_native_work": "Sources/Lowtide/construction/recomposed-status.json", "native_work": ["Sources/Lowtide/drainage/grate-status.json", "Sources/Lowtide/construction/recomposed-status.json"], "historical_snapshot_note": "Candidate counts and protected-file counts describe the earlier offline snapshot. Grates and construction were subsequently installed and verified. Water, paving and sacks remain staged; historical full-mesh snapshots must be recomposed against current sources.", "remaining": ["Review staged paving and water in the native scene before promotion.", "Sack distance candidates require current-source recomposition, native grouping, switching and performance review.", "Revalidate floor and foliage integration against the canonical checkout.", "Controlled gameplay performance, temporal behavior and overall visual quality remain open."]})
write(path, status)
print(json.dumps({"installed_source_files_verified": len(manifest["staged_files"]), "production_models_verified": len(readback["models"]), "grates_verified": 24, "review_assets_archived": len(retired["ArchivedFiles"])}))
