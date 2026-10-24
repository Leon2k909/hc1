"""Save the reviewed native geometry evidence; do not claim a lighting comparison."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path.cwd().resolve()
HERE = Path(__file__).resolve().parent
IMAGES = ROOT / "output/belltower/quality/soft-props-native-20261020"
NAMES = ("shop-detail-saved", "parcel-fold-detail", "card-and-shelf-detail", "card-oblique-detail")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")

scene = ROOT / "Assets/scenes/maps/Belltower/belltower.scene"
scene_hash = digest(scene)
records = []
for name in NAMES:
    image = IMAGES / (name + ".png")
    camera = IMAGES / (name + "-camera.json")
    receipt = json.loads(camera.read_text(encoding="utf-8"))
    assert receipt["Capture"]["SourceSceneSha256"] == scene_hash
    assert all(receipt["Restoration"].values())
    assert not receipt["Capture"]["EffectiveGpuExposureVerified"]
    records.append({"image": relative(image), "image_sha256": digest(image),
                    "camera_receipt": relative(camera), "camera_receipt_sha256": digest(camera),
                    "restoration": receipt["Restoration"]})

review = {
    "reviewed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "accepted": True,
    "scope": "Qualitative geometry review in the existing saved Belltower editor document; one representative shop display photographed.",
    "installed_model_covers_displays": 18,
    "source_scene_sha256": scene_hash,
    "captures": records,
    "observations": [
        "Shelf fronts have a restrained continuous bow and retain their supported contents.",
        "Parcel bodies and folded tops have uneven contours; printed labels conform and read upright.",
        "The oblique close-up shows slight price-card depth variation with the centre held by its clip.",
        "No error materials or newly floating parcel flaps were visible in these views."
    ],
    "lighting_limit": "The hidden-document captures did not settle GPU exposure. These images establish local geometry appearance, not a calibrated lighting or before/after brightness comparison.",
    "existing_issue": "Block-shaped shadow bands behind the products are also visible in the earlier shop-detail-balanced.png native capture; their lighting was not changed by this pass.",
    "reference_image": "output/belltower/quality/shop-displays-v2-native-final/shop-detail-balanced.png",
    "scene_or_play_changes": False,
    "all_camera_tone_object_and_editor_state_restoration_checks_passed": True,
    "capture_helper_source": "Sources/Belltower/editor/capture-preview-consistent.cs.txt",
    "capture_helper_copy_sha256": digest(HERE / "capture-shop-detail.cs.txt")
}
review_path = HERE / "native-visual-review.json"
review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")

report_path = HERE / "native-verification.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
assert report["native_compilation_verified"]
assert digest(ROOT / "Assets/models/maps/belltower/shop-display-v2/shop_displays.obj") == report["native_model"]["SourceSha256"]
report.update(native_map_visual_review_verified=True, native_visual_review=relative(review_path), remaining=[])
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

manifest_path = ROOT / "Sources/Belltower/props/soft-shop-props-v1.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["model_sha256"] == report["native_model"]["SourceSha256"]
manifest.update(state="native compilation and representative saved-map geometry review verified",
                native_map_visual_review_verified=True, native_visual_review=relative(review_path))
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

verification_path = ROOT / "output/belltower/prop-edge-audit/verification.json"
verification = json.loads(verification_path.read_text(encoding="utf-8"))
verification.update(native_map_visual_review_verified=True, native_visual_review=relative(review_path))
verification_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"native_compilation_verified": True, "native_map_geometry_review_verified": True,
                  "native_images_reviewed": len(records), "all_restoration_checks_passed": True,
                  "saved_scene_unchanged": True, "lighting_comparison_verified": False}))
