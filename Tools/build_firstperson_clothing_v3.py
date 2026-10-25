"""Stage authored UV regions and technical fold normals; publish with the native editor."""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/firstperson-clothing-v3-20261021"
STAGE = OUT / "stage"
assert not (STAGE / "manifest.json").exists(), "Preserve existing staging evidence."
STAGE.mkdir(parents=True, exist_ok=True)
prompts = json.loads((ROOT / "Sources/Clothing/firstperson-v3/imagegen-prompts.json").read_text())
regions = json.loads((OUT / "regions/manifest.json").read_text())
region_by_name = {r["Name"]: r for r in regions["Regions"]}

files, density = {}, []


def record(target, source, **extra):
    files[target] = {
        "source": source.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        **extra,
    }


for entry in prompts["records"]:
    name = entry["name"]
    source = Path(entry["source"])
    raw = OUT / "imagegen" / (name + ".png")
    raw.parent.mkdir(parents=True, exist_ok=True)
    assert not raw.exists(), raw
    shutil.copy2(source, raw)
    with Image.open(raw) as image:
        size = image.size
    region = region_by_name[name]
    compiler_size = [1024, 2048] if name == "cuff-strip" else [2048, 1024]
    # Resampling is performed separately by the native bitmap pipeline. Density
    # improvement is measured from generated pixels, never compiler dimensions.
    record("Assets/materials/operators/first_person/v3/" + name + ".png", raw,
           native_size=list(size), compiler_size=compiler_size)
    density.append({"region": name, "bounds": region["Bounds"],
                    "source_pixels": [region["Width"], region["Height"]],
                    "authored_pixels": list(size),
                    "linear_gain": [size[0] / region["Width"], size[1] / region["Height"]]})

# Remove the stock map's coarse woven normal pattern, while retaining folds.
# Exported source normal XY are reconstructed into a unit tangent-space normal;
# detailed weave is supplied independently by the existing fine-normal layer.
original = OUT.parent / "firstperson-clothing-v2-20261021/originals/shirt-g_tNormal.png"
encoded = np.asarray(Image.open(original).convert("RGBA"), dtype=np.float32) / 255
xy = gaussian_filter(encoded[:, :, :2] * 2 - 1, sigma=(1.6, 1.6, 0), mode="nearest")
z = np.sqrt(np.maximum(1 - (xy * xy).sum(axis=2), 0.0001))
normal = np.dstack((xy, z))
normal /= np.linalg.norm(normal, axis=2, keepdims=True)
normal_path = STAGE / "shirt-fold-normal.png"
Image.fromarray(np.rint(np.clip(normal * .5 + .5, 0, 1) * 255).astype(np.uint8)).save(normal_path)
record("Assets/materials/operators/first_person/v3/shirt-fold-normal.png", normal_path)

material = (ROOT / "Assets/materials/operators/first_person/v2/shirt.vmat").read_text()
material = material.replace("viewmodel_fabric_v2.shader", "viewmodel_fabric_v3.shader")
material = material.replace("v2/shirt_macro_normal.png", "v3/shirt-fold-normal.png")
material = material.replace('g_flFineNormalStrength "0.45"', 'g_flFineNormalStrength "0.4"')
material = material.replace('g_flFineColourStrength "0.025"', 'g_flFineColourStrength "0.02"')
for input_name, filename in [("SleeveLeft", "sleeve-left"), ("SleeveRight", "sleeve-right"),
                             ("CuffMain", "cuff-main"), ("CuffStrip", "cuff-strip")]:
    material = material.replace("\n}", '\n    Texture' + input_name + ' "materials/operators/first_person/v3/' + filename + '.png"\n}')
material_path = STAGE / "shirt.vmat"
material_path.write_text(material, encoding="utf-8")
record("Assets/materials/operators/first_person/v3/shirt.vmat", material_path)
record("Assets/shaders/viewmodel_fabric_v3.shader", ROOT / "Sources/Clothing/firstperson-v3/viewmodel_fabric_v3.shader")

manifest = {"files": files, "density": density,
            "compiler_resize_adds_detail": False,
            "source_normal_sha256": hashlib.sha256(original.read_bytes()).hexdigest()}
(STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({"staged_assets": len(files), "native_detail_gain": density}, indent=2))
