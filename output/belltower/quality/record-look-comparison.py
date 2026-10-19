"""Record the completed, temporary tone-mapper comparison without publishing it."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/belltower/quality"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = read(OUT / "look-v1-plan.json")
camera_state = read(OUT / "capture-camera-state.json")
assert camera_state["GamePreserved"] and camera_state["SelectedDocumentPreserved"]
scene = ROOT / "Assets/scenes/maps/belltower/belltower.scene"
assert digest(scene) == plan["scene_sha256"], "Saved Belltower scene changed"
views = plan["views"]
variants = {
    "agx-saved": views,
    "aces-lower": ["west-street"],
    "agx-lower": ["west-street"],
    "aces-comp": ["west-street"],
}
records = []
camera_keys = ["Scene", "CameraScene", "Position", "Angles", "FieldOfView"]
for variant, variant_views in variants.items():
    for view in variant_views:
        before = OUT / "look-v1-baseline" / view
        after = OUT / f"look-v1-{variant}" / view
        baseline = read(before.with_name(view + "-camera.json"))
        comparison = read(after.with_name(view + "-camera.json"))
        restore = read(after.with_name(view + "-look-restore.json"))
        assert restore["ToneRestored"] is True
        for data in (baseline, comparison):
            assert data["GamePreserved"] and data["SelectedDocumentPreserved"]
            assert not data["SceneHasUnsavedChanges"]
            assert data["SourceScene"] == "scenes/maps/belltower/belltower.scene"
            assert all(item["TexturesValid"] for item in data["Lighting"])
        assert baseline["Lighting"] == comparison["Lighting"]
        assert all(baseline["Capture"][key] == comparison["Capture"][key] for key in camera_keys)
        a = np.asarray(Image.open(before.with_suffix(".png")).convert("RGB"), dtype=np.int16)
        b = np.asarray(Image.open(after.with_suffix(".png")).convert("RGB"), dtype=np.int16)
        assert a.shape == b.shape == (1080, 1920, 3)
        difference = np.abs(a - b)
        records.append({
            "variant": variant, "view": view,
            "baseline": str(before.with_suffix(".png").relative_to(ROOT)).replace("\\", "/"),
            "comparison": str(after.with_suffix(".png").relative_to(ROOT)).replace("\\", "/"),
            "baseline_sha256": digest(before.with_suffix(".png")),
            "comparison_sha256": digest(after.with_suffix(".png")),
            "requested_look": comparison["TrialLook"],
            "reported_camera": comparison["Capture"],
            "mean_absolute_rgb_difference_0_255": float(difference.mean()),
            "fraction_pixels_with_any_channel_difference_over_2": float((difference.max(axis=2) > 2).mean()),
            "exact_tone_component_restored": True,
        })

report = {
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "state": "native comparisons reviewed; exposure comparison inconclusive; no lighting publication",
    "engine_version": "26.10.13",
    "scene_sha256": digest(scene),
    "saved_look": plan["saved_look"],
    "views_reviewed": 11,
    "comparisons": records,
    "visual_review": {
        "agx": "More legible pale plaster and paving, richer warm timber in the hall. It is a useful candidate, but does not resolve the map's material and landscape limitations.",
        "exposure": "Exposure bounds and compensation changed camera metadata but produced nearly identical RGB pixels. These images do not verify their effective rendered exposure.",
    },
    "local_engine_inspection": {
        "report": "output/belltower/quality/capture-render-il.txt",
        "sha256": digest(OUT / "capture-render-il.txt"),
        "observed": [
            "CameraComponent.CopyPostProcessing applies AutoExposure to SceneCamera.Tonemap.",
            "InitializeRendering additionally copies Scene.Camera post-processing onto an editor camera when Scene.Camera is present.",
            "TonemapSystem setters forward parameters to a native ITonemapSystem when its handle is valid.",
            "SceneCamera.RenderToBitmap crosses into the native renderer. The inspected managed code does not establish the effective native exposure used for its pixels.",
        ],
        "root_cause": "unconfirmed",
    },
    "read_only_live_camera_check": {
        "report": "output/belltower/quality/capture-camera-state.json",
        "sha256": digest(OUT / "capture-camera-state.json"),
        "main_camera_name": camera_state["MainCamera"]["Name"],
        "camera_names": [item["Name"] for item in camera_state["Cameras"]],
        "observation": "A separate main camera and editor_camera both have valid native tone-map systems. This makes main-camera overwrite a concrete hypothesis to test, not a confirmed root cause.",
    },
    "next_probe": [
        "In a coordinated editor window, compare the main camera, editor camera and native SceneCamera tone-map settings after rendering initialization.",
        "Use two deliberately separated fixed exposure bounds to distinguish a genuine response from animation noise, then verify the same settings in the live viewport before evaluating lighting.",
        "The staged capture helper now records NativeExposureAfterRender. Its opt-in sync_main_postprocess comparison updates both cameras and restores the main camera exposure values; this branch has not yet run natively.",
    ],
    "limitations": [
        "No gameplay readability or frame-time claim is made by this screenshot comparison.",
        "The saved scene remains ACES with exposure bounds 1.05 to 2.2 and compensation 0.",
    ],
}
(OUT / "look-v1-review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
plan["state"] = report["state"]
plan["review"] = "output/belltower/quality/look-v1-review.json"
plan["current_capture"] = "output/belltower/quality/look-v1-baseline/west-street.png"
(OUT / "look-v1-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"comparisons": len(records), "restored": True, "scene_unchanged": True,
                  "report": "output/belltower/quality/look-v1-review.json"}))
