"""Stage clean albedo regions and fold-only normals, preserving the rejected filter experiment."""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/firstperson-clothing-v4-20261021"
STAGE = OUT / "clean-stage"
SOURCE = ROOT / "Sources/Clothing/firstperson-v4"
assert not (STAGE / "manifest.json").exists(), "Preserve prior staging evidence."
STAGE.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# The earlier filtering candidate was never selected for the production binding.
# Save it explicitly and require its publication hashes before replacing it.
rejected = OUT / "rejected-filter"
rejected.mkdir(exist_ok=True)
old = json.loads((OUT / "native-import.json").read_text())
for item in old["Published"]:
    path = ROOT / item["Path"]
    assert sha(path) == item["Sha256"], "Candidate changed externally."
    backup = rejected / path.name
    assert not backup.exists()
    shutil.copy2(path, backup)

files = {}


def record(target, source, **extra):
    path = ROOT / target
    files[target] = {"source": source.relative_to(ROOT).as_posix(), "sha256": sha(source),
                     "before": sha(path) if path.exists() else None, **extra}


prompts = json.loads((SOURCE / "imagegen-prompts.json").read_text())
for item in prompts["records"]:
    raw = OUT / "imagegen" / (item["name"] + ".png")
    raw.parent.mkdir(exist_ok=True)
    assert not raw.exists()
    shutil.copy2(item["source"], raw)
    if not item["selected"]:
        continue
    with Image.open(raw) as image:
        size = list(image.size)
    target_size = [1024, 2048] if item["name"] == "cuff-strip" else [2048, 1024]
    record("Assets/materials/operators/first_person/v4/" + item["name"] + ".png", raw,
           native_size=size, compiler_size=target_size)

original = ROOT / "output/firstperson-clothing-v2-20261021/originals/shirt-g_tNormal.png"
encoded = np.asarray(Image.open(original).convert("RGBA"), dtype=np.float32) / 255
xy = gaussian_filter(encoded[:, :, :2] * 2 - 1, sigma=(3.2, 3.2, 0), mode="nearest")
z = np.sqrt(np.maximum(1 - (xy * xy).sum(axis=2), .0001))
normal = np.dstack((xy, z))
normal /= np.linalg.norm(normal, axis=2, keepdims=True)
normal_path = STAGE / "shirt-fold-normal.png"
Image.fromarray(np.rint(np.clip(normal * .5 + .5, 0, 1) * 255).astype(np.uint8)).save(normal_path)
record("Assets/materials/operators/first_person/v4/shirt-fold-normal.png", normal_path)

# Keep region sampling sharp. The rejected colour filter is completely absent.
shader = (ROOT / "Sources/Clothing/firstperson-v3/viewmodel_fabric_v3.shader").read_text()
shader = shader.replace('Description = "First-person sleeves with separately authored close-up UV regions";',
                        'Description = "First-person cotton: clean dye, fold normals and independent fine weave";')
shader = shader.replace('    // Each image is authored over just this UV rectangle',
                        '    float g_flFoldNormalStrength < Default( 0.7 ); Range( 0.0, 1.0 ); UiGroup( "Surface,20/60" ); >;\n\n    // Each image is authored over just this UV rectangle')
shader = shader.replace('g_tColor.SampleBias( TextureFiltering, uv, -0.65 )', 'g_tColor.Sample( TextureFiltering, uv )')
shader = shader.replace('g_tNormal.SampleBias( TextureFiltering, uv, -0.35 )', 'g_tNormal.Sample( TextureFiltering, uv )')
shader = shader.replace('float3( folds.xy + fine.xy * g_flFineNormalStrength, folds.z )',
                        'float3( folds.xy * g_flFoldNormalStrength + fine.xy * g_flFineNormalStrength, folds.z )')
shader = shader.replace('clamp( m.Roughness + data.x * 0.06, 0.55, 0.96 )',
                        'clamp( max( m.Roughness, 0.82 ) + data.x * 0.035, 0.78, 0.96 )')
assert "g_flFabricClean" not in shader and "g_flFabricFilterTexels" not in shader
shader_path = SOURCE / "viewmodel_fabric_v4.shader"
assert sha(shader_path) == sha(rejected / shader_path.name)
shader_path.write_text(shader, encoding="utf-8")
record("Assets/shaders/viewmodel_fabric_v4.shader", shader_path)

material = (ROOT / "Assets/materials/operators/first_person/v3/shirt.vmat").read_text()
material = material.replace("viewmodel_fabric_v3.shader", "viewmodel_fabric_v4.shader")
for name in ["shirt-fold-normal", "sleeve-left", "sleeve-right", "cuff-main", "cuff-strip"]:
    material = material.replace("v3/" + name + ".png", "v4/" + name + ".png")
material = material.replace('g_flFineNormalStrength "0.4"', 'g_flFineNormalStrength "0.22"')
material = material.replace('g_flFineColourStrength "0.02"', 'g_flFineColourStrength "0.012"')
material = material.replace('\n}', '\n    g_flFoldNormalStrength "0.7"\n}')
material_path = STAGE / "shirt.vmat"
material_path.write_text(material, encoding="utf-8")
record("Assets/materials/operators/first_person/v4/shirt.vmat", material_path)
manifest = {"files": files, "rejected_filter_preserved": True,
            "change": "Remove baked coarse weave from albedo; keep fine fibres and fold lighting separate",
            "compiler_resize_adds_detail": False}
(STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({"assets": len(files), "cleaned_albedo_regions": 4, "rejected_filter_preserved": True}))
