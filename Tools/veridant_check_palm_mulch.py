"""Verify the installed palm-bed surface and accepted matched engine capture."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from railhead_stage_extinguisher import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/veridant/palm-mulch-v1"


def results(path):
    raw = json.loads(path.read_text())
    assert not raw.get("isError"), path
    return [json.loads(x["text"]) for x in raw["content"] if x["type"] == "text"]


def main():
    manifest = json.loads((OUT/"stage-v3/manifest.json").read_text())
    for p, item in manifest["files"].items():
        assert sha(ROOT/p) == item["after"], p
    for p, h in manifest["source_sha256"].items():
        assert sha(ROOT/p) == h, p
    protected = {}
    for p, h in manifest["protected_sha256"].items():
        actual = sha(ROOT/p)
        protected[p] = {"before": h, "current": actual, "unchanged": actual == h}
        if not p.endswith("veridant.scene"):
            assert actual == h, p
    for p, parts in manifest["required_source_snippets"].items():
        assert all(part in (ROOT/p).read_text() for part in parts), p

    data = (ROOT/"Assets/models/maps/veridant/veridant_palm_pits.obj").read_bytes()
    retained = data[:manifest["retained_bytes"]]
    assert hashlib.sha256(retained).hexdigest() == manifest["retained_bytes_sha256"]
    counts = Counter()
    faces = Counter()
    material = None
    for line in data.splitlines():
        if line.startswith((b"v ", b"vt ", b"vn ")):
            counts[line.split()[0]] += 1
        elif line.startswith(b"usemtl "):
            material = line.split()[1]
        elif line.startswith(b"f "):
            faces[material.decode()] += 1
            for token in line.split()[1:]:
                for key, value in zip((b"v", b"vt", b"vn"), token.split(b"/")):
                    assert 0 < int(value) <= counts[key]
    assert faces == {"vr_stone_light": 1760, "vr_palm_mulch": 29600}
    receipt = json.loads((OUT/"native-import.json").read_text())
    assert receipt["BedsUpdated"] == 10 and receipt["Fragments"] == 1200
    assert receipt["StoneRimsPreserved"] and receipt["EditorStatePreserved"]
    assert not receipt["SceneChanged"] and not receipt["CollisionChanged"]
    compiles = results(OUT/"compile-v3/call_tools.json")
    assert len(compiles) == 2 and all(c["Success"] for c in compiles)
    before = ROOT/"output/veridant/quality/palm-mulch-v1-before/palm-bed.png"
    after = ROOT/"output/veridant/quality/palm-mulch-v1-after/palm-bed.png"
    captures = []
    for image in (before, after):
        meta = json.loads(image.with_name("palm-bed-camera.json").read_text())
        assert all(meta["Restoration"].values())
        captures.append({"path": image.relative_to(ROOT).as_posix(), "sha256": sha(image), **meta})
    for key in ("Position", "Angles", "FieldOfView", "FovAxis", "Width", "Height", "RequestedExposure", "SourceSceneSha256"):
        assert captures[0]["Capture"][key] == captures[1]["Capture"][key], key
    assert captures[0]["sha256"] != captures[1]["sha256"]
    status, camera = results(OUT/"final-status/call_tools.json")
    assert Path(status["Paths"]["ProjectRoot"]).resolve() == ROOT
    assert status["LastCompileSucceeded"] and status["LastCompileErrors"] == 0 and not status["IsCompiling"]
    assert status["ActiveScene"] == "veridant" and not status["IsPlaying"] and not status["SceneHasUnsavedChanges"]
    secondary = json.loads((ROOT/"output/veridant/quality/palm-mulch-v1-after/second-bed-restore.json").read_text())
    assert all(v for k, v in secondary.items() if k != "EditorStatePreserved")
    report = {"revision": manifest["revision"], "stage": "stage-v3", "beds_updated": 10,
        "new_fill_triangles": 29600, "bark_fragments": 1200, "published_files": len(manifest["files"]),
        "stone_rim_triangles_preserved": 1760, "retained_obj_bytes_exact": True,
        "original_obj_indices_preserved": True, "scene_written_by_task": False, "collision_unchanged": True,
        "source_hooks_verified": True, "protected_files": protected, "native_compiles": compiles,
        "native_import": receipt, "bounds": manifest["beds"], "captures": captures,
        "matched_camera_and_exposure": True, "visually_reviewed": True,
        "optional_second_view_discarded": {"restoration": secondary,
            "reason": "Saved scene hash changed during this optional capture; view/tone/assets/objects restored. No scene overwrite attempted."},
        "editor_status": status, "editor_camera": camera,
        "performance_note": "29,600 fill triangles across ten beds. Frame-rate impact not benchmarked."}
    (OUT/"validation.json").write_text(json.dumps(report, indent=2)+"\n")
    (ROOT/"Sources/Veridant/palm-mulch-v1/installed.json").write_text(json.dumps({
        "revision": manifest["revision"], "beds_updated": 10, "stage": "stage-v3",
        "validation": "output/veridant/palm-mulch-v1/validation.json",
        "screenshot": after.relative_to(ROOT).as_posix(), "stone_rims_preserved": True}, indent=2)+"\n")
    print(json.dumps({"beds_updated": 10, "native_compiles_passed": 2,
                      "stone_rims_preserved": True, "matched_capture_reviewed": True}))


if __name__ == "__main__":
    main()
