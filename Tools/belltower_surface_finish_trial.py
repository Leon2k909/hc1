"""Stage restrained plaster wear and warm limestone using the accepted PBR maps."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import belltower_quality_materials as materials


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/belltower/quality/surface-finish-v1"
RESOURCE = "materials/belltower/trials/surface-finish-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records, inputs = [], [Path(__file__), ROOT / "Tools/belltower_quality_materials.py"]
    changes = {
        **{f"plaster_{color}": {"g_flWearCoverage": ("0.49", "0.24")} for color in materials.PAINTS},
        "rubble": {"g_vMasonryTint": ("[.92 1.0 .84]", "[1.04 1.0 .90]"),
                   "g_flMasonryContrast": ("0.86", "1.04"), "g_flMasonryWeather": ("0.28", "0.12")},
    }
    for name, values in changes.items():
        original = ROOT / f"Assets/materials/belltower/{name}.vmat"
        text = original.read_text(encoding="utf-8")
        assert text.strip() == materials.material_text(name).strip(), f"Accepted material drift: {name}"
        candidate = text
        for key, (before, after) in values.items():
            pattern = rf'({re.escape(key)}\s+)"{re.escape(before)}"'
            candidate, count = re.subn(pattern, lambda m: m[1]+f'"{after}"', candidate)
            assert count == 1, (name, key, count)
        path = f"{RESOURCE}/{name}.vmat"
        staged = OUT / "Assets" / path
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(candidate, encoding="utf-8", newline="\n")
        live = ROOT / "Assets" / path
        assert not live.exists() or sha(live) == sha(staged), f"Use a new revision: {path}"
        keys = dict(re.findall(r'^\s*(\w+)\s+"([^"]*)"', text, re.MULTILINE))
        for key, value in keys.items():
            if key == "shader" or key.startswith("Texture"):
                inputs.append(ROOT / "Assets" / value)
        inputs.append(original)
        records.append({"target": original.relative_to(ROOT / "Assets").as_posix(), "path": path,
                        "source": staged.relative_to(ROOT).as_posix(), "sha256": sha(staged),
                        "original_sha256": sha(original), "changed_parameters": values})
    inputs = list(dict.fromkeys(inputs))
    manifest = {"revision": "surface-finish-v1", "state": "staged; native comparison pending", "records": records,
                "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                "source_pixels_changed": False, "shaders_modified": False, "geometry_modified": False,
                "accepted_assets_written": False, "native_verified": False,
                "purpose": "Retain mostly intact coloured limewash with localized wear, and separate warm limestone faces without broad artificial grunge. Original photographed/generated colour, normal, roughness, height and AO maps remain untouched."}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"materials": len(records), "staged_to": str(OUT), "accepted_assets_written": False, "native_verified": False}))


if __name__ == "__main__":
    main()
