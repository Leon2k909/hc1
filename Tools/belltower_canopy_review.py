"""Compare captured Belltower canopy trials against the same native camera views.

Only reads saved capture images/metadata and writes a review contact sheet and
machine-readable result under output/belltower/quality. This never edits game
assets, renderer assignments or the editor scene.

    python Tools/belltower_canopy_review.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "output/belltower/quality"
BASE = QUALITY / "canopy-photo-v2-baseline-20261016"
TRIAL = QUALITY / "canopy-photo-v2-trial-20261016"
VIEWS = ("valley", "west-ridge", "terrace")


def main():
    sheet = Image.new("RGB", (1600, 3 * 505 + 32), "#172025")
    draw = ImageDraw.Draw(sheet)
    reports = {}
    for row, view in enumerate(VIEWS):
        a = json.loads((BASE / f"{view}-camera.json").read_text())
        b = json.loads((TRIAL / f"{view}-camera.json").read_text())
        restore = json.loads((TRIAL / f"{view}-restore.json").read_text())
        assert b["TrialCanopySlots"] > 0 and a["TrialCanopySlots"] == 0
        assert restore["MaterialsRestored"] and restore["Slots"] == b["TrialCanopySlots"]
        for result in (a, b):
            assert result["GamePreserved"] and result["SelectedDocumentPreserved"]
            assert not result["SceneHasUnsavedChanges"]
            assert all(light["TexturesValid"] for light in result["Lighting"])
            assert result["Projection"]["FovAxis"] == "Horizontal"
        assert a["Capture"] == b["Capture"], "Camera / exposure changed between comparisons"
        assert a["Projection"] == b["Projection"], "Projection mismatch"

        with Image.open(BASE / f"{view}.png") as image:
            before = image.convert("RGB")
        with Image.open(TRIAL / f"{view}.png") as image:
            after = image.convert("RGB")
        assert before.size == after.size == (1920, 1080)
        before_array = np.asarray(before, dtype=np.int16)
        after_array = np.asarray(after, dtype=np.int16)
        difference = np.abs(before_array - after_array)
        reports[view] = {
            "mean_absolute_difference_rgb": [round(float(x), 4) for x in difference.mean(axis=(0, 1))],
            "fraction_pixels_difference_above_8": round(float(np.mean(difference.max(axis=2) > 8)), 5),
            "trial_material_slots": b["TrialCanopySlots"],
            "materials_restored": restore["MaterialsRestored"],
            "camera_and_projection_identical": True,
            "scene_and_game_preserved": True,
        }
        y = row * 505 + 25
        draw.text((10, y - 18), f"{view} — baseline", fill="#f2f5f6")
        draw.text((810, y - 18), f"{view} — photographic canopy trial", fill="#f2f5f6")
        sheet.paste(before.resize((790, 444), Image.Resampling.LANCZOS), (5, y))
        sheet.paste(after.resize((790, 444), Image.Resampling.LANCZOS), (805, y))

    destination = QUALITY / "canopy-photo-v2-native-review-20261016"
    destination.mkdir(parents=True, exist_ok=True)
    sheet.save(destination / "comparison.jpg", quality=89, subsampling=0)
    (destination / "report.json").write_text(json.dumps({
        "review_type": "matched native saved-scene comparison",
        "original_assets_modified": False,
        "manual_visual_acceptance_needed": True,
        "views": reports,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, indent=2))
    print(destination / "comparison.jpg")


if __name__ == "__main__":
    main()
