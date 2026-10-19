"""Stage guarded Belltower plaster-weathering alternatives for native review.

Creates eight separate .vmat files; the current plaster materials, their
photographed 4K source textures and the scene are never modified by this step.
Only the amount and darkness of exposed weathering change. Existing render
UVs, plaster colours, geometry and gameplay collision remain identical.

    python Tools/belltower_plaster_weathering_trial.py
"""
import hashlib
import json
from pathlib import Path

import belltower_quality_materials as Materials

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/belltower/quality/plaster-weathered-v2"
RESOURCE_DIR = "materials/belltower/trials/plaster-weathered-v2"
WEAR_COVERAGE = .49
WEAR_BRIGHTNESS = 2.3


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage():
    OUT.mkdir(parents=True, exist_ok=True)
    records, originals = [], {}
    for color in Materials.PAINTS:
        accepted = ROOT / f"Assets/materials/belltower/plaster_{color}.vmat"
        name = f"plaster_{color}.vmat"
        source = accepted.read_text(encoding="utf-8")
        expected = Materials.material_text(f"plaster_{color}")
        # Refuse to base a trial on some other agent's unpublished material.
        assert expected and source.strip() == expected.strip(), f"Accepted plaster {name} diverged from generator"
        assert source.count('g_flWearCoverage "0.34"') == 1
        assert source.count('g_flWearBrightness "2.6"') == 1
        candidate = source.replace('g_flWearCoverage "0.34"', f'g_flWearCoverage "{WEAR_COVERAGE}"')
        candidate = candidate.replace('g_flWearBrightness "2.6"', f'g_flWearBrightness "{WEAR_BRIGHTNESS}"')
        path = OUT / name
        path.write_text(candidate, encoding="utf-8", newline="\n")
        resource = f"{RESOURCE_DIR}/{name}"
        installed = ROOT / "Assets" / resource
        if installed.exists():
            assert sha(installed) == sha(path), f"Different material already installed: {resource}"
        original_rel = accepted.relative_to(ROOT).as_posix()
        originals[original_rel] = sha(accepted)
        records.append({
            "name": name,
            "path": resource,
            "source": path.relative_to(ROOT).as_posix(),
            "target": accepted.relative_to(ROOT / "Assets").as_posix(),
            "sha256": sha(path),
            "original_sha256": sha(accepted),
        })
    manifest = {
        "revision": "plaster-weathered-v2",
        "state": "separate native material trial; not accepted",
        "coverage": WEAR_COVERAGE,
        "brightness": WEAR_BRIGHTNESS,
        "unchanged_accepted_materials": originals,
        "records": records,
        "source_generator": "Tools/belltower_quality_materials.py",
        "source_sha256": sha(ROOT / "Tools/belltower_quality_materials.py"),
        "scene_geometry_and_collision_modified": False,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"trial_materials": len(records), "coverage": WEAR_COVERAGE,
                      "brightness": WEAR_BRIGHTNESS, "output": OUT.relative_to(ROOT).as_posix()}))


if __name__ == "__main__":
    stage()
