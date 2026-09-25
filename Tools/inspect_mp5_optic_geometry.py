"""Inspect imported Workshop optic geometry for ADS calibration."""

from collections import defaultdict
from pathlib import Path
import json
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def material_centers(obj_path):
    vertices = []
    faces = defaultdict(set)
    material = None
    for line in obj_path.open(encoding="utf-8"):
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith("usemtl "):
            material = line.split()[1]
        elif line.startswith("f "):
            faces[material].update(
                int(point.split("/")[0]) - 1 for point in line.split()[1:]
            )
    centers = {}
    for name, indices in faces.items():
        points = [vertices[i] for i in indices]
        low = tuple(min(p[axis] for p in points) for axis in range(3))
        high = tuple(max(p[axis] for p in points) for axis in range(3))
        centers[name] = {
            "center": tuple(round((a + b) / 2, 3) for a, b in zip(low, high)),
            "low": tuple(round(v, 3) for v in low),
            "high": tuple(round(v, 3) for v in high),
        }
    return centers


for part_file in sorted((ROOT / "Assets/gunsmith/mpapa5/optics").glob("*.gnsmth")):
    part = json.loads(part_file.read_text(encoding="utf-8"))
    prefab = json.loads((ROOT / "Assets" / part["MainPrefab"]["prefab"]).read_text(encoding="utf-8"))
    model_path = next(
        component["Model"]
        for component in prefab["RootObject"]["Components"]
        if component["__type"] == "Sandbox.ModelRenderer"
    )
    model = ROOT / "Assets" / model_path
    data = model.read_text(encoding="utf-8")
    mat_map = dict(re.findall(r'from = "(m_[a-f0-9]+)\.vmat" to = "([^"]+)"', data))
    centers = material_centers(model.with_suffix(".obj"))
    reticles = [
        bounds for name, bounds in centers.items()
        if mat_map.get(name, "").endswith(f"/{part_file.stem}_reticle.vmat")
    ]
    if len(reticles) != 1:
        raise ValueError(f"Expected one reticle mesh in {model_path}, found {len(reticles)}")
    height = reticles[0]["center"][1]
    # Aim-Op was calibrated in a live 1920x1080 ADS capture at -0.55. Imported
    # OBJ's second axis is model up, so other reticles need the height delta.
    z_offset = round(-0.55 - (height - 1.254), 3)
    print(f"{part_file.stem:34} reticle height={height:.3f} ADS z={z_offset:.3f}")
    if "--apply" in sys.argv:
        part["OverrideAimOffset"] = True
        part["OpticAimOffset"] = f"0,0,{z_offset:g}"
        part["OpticAimAngles"] = "0,0,0"
        part_file.write_text(json.dumps(part, indent=2) + "\n", encoding="utf-8")
