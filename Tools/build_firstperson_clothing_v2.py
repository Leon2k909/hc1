"""Stage clothing-only imagegen atlases, faithful coverage, and fine PBR detail.

Generated albedos are copied unchanged. Derived normal/roughness/coverage maps
are technical material data, not an upscale presented as newly resolved art.
Publishing staged Assets is done through the native editor separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/firstperson-clothing-v2-20261021"
RESOURCE = "materials/operators/first_person/v2"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_map(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(values*255+.5, 0, 255).astype(np.uint8)).save(path)


def fine_maps(image, folder, name, leather=False):
    # Remove broad lighting and use wrap derivatives for periodic shader data.
    grey = np.asarray(image.convert("L"), dtype=np.float32)/255
    height = grey-gaussian_filter(grey, 5, mode="wrap")
    height /= max(float(height.std()), .005)
    height = gaussian_filter(height, .55, mode="wrap")
    dx = (np.roll(height, -1, axis=1)-np.roll(height, 1, axis=1))*.5
    dy = (np.roll(height, -1, axis=0)-np.roll(height, 1, axis=0))*.5
    # Fine, shallow fibres/pores; do not turn printed camouflage into relief.
    strength = .055 if leather else .075
    normals = np.dstack((-dx*strength, dy*strength, np.ones_like(height)))
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    save_map(folder/f"{name}_fine_normal.png", normals*.5+.5)
    data = np.dstack((.5+np.clip(height*.085, -.35, .35),
                      .5+np.clip(height*.07, -.3, .3), np.full_like(height, .5)))
    save_map(folder/f"{name}_fine_data.png", data)
    return {"size": image.size, "normal_max_xy": float(np.abs(normals[:, :, :2]).max()),
            "normal_rms_xy": float(np.sqrt(np.mean(normals[:, :, :2]**2)))}


def material(name, alpha_test, roughness, fine_scale, fine_strength):
    return f'''"Layer0"
{{
    shader "shaders/viewmodel_fabric_v2.shader"
    F_ALPHA_TEST "{int(alpha_test)}"
    TextureColor "{RESOURCE}/{name}_albedo.png"
    TextureNormal "{RESOURCE}/{name}_macro_normal.png"
    TextureRoughness "{RESOURCE}/{name}_roughness.png"
    TextureMetalness "materials/default/default_metal.tga"
    TextureAmbientOcclusion "{RESOURCE}/{name}_ao.png"
    TextureTranslucency "{RESOURCE}/{name}_coverage.png"
    TextureTintMask "{RESOURCE}/{name}_tint.png"
    TextureFineNormal "{RESOURCE}/{name}_fine_normal.png"
    TextureFineData "{RESOURCE}/{name}_fine_data.png"
    g_flFineScale "{fine_scale}"
    g_flFineNormalStrength "{fine_strength}"
    g_flFineColourStrength "0.025"
}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("shirt", "gloves", "weave"):
        parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args()
    stage = OUT/"stage"
    assert not (stage/"manifest.json").exists(), "Preserve the staged revision"
    source_folder = OUT/"imagegen"
    source_folder.mkdir(parents=True, exist_ok=True)
    folder = stage/"Assets"/RESOURCE
    folder.mkdir(parents=True, exist_ok=True)
    generated = {}
    for name in ("shirt", "gloves", "weave"):
        source = getattr(args, name).resolve()
        target = source_folder/(name+".png")
        shutil.copy2(source, target)
        generated[name] = {"path": target.relative_to(ROOT).as_posix(), "sha256": sha(target),
                           "native_dimensions": Image.open(target).size, "upscaled": False}
    fine = {}
    fine["shirt"] = fine_maps(Image.open(args.weave), folder, "shirt")
    glove_art = Image.open(args.gloves)
    w, h = glove_art.size
    # Clear leather away from the island boundaries, lacing and seams.
    leather = glove_art.crop((int(w*.14), int(h*.24), int(w*.31), int(h*.41)))
    fine["gloves"] = fine_maps(leather, folder, "gloves", leather=True)
    for name, roughness, scale, strength in (("shirt", .85, 12, .45), ("gloves", .71, 7, .42)):
        shutil.copy2(getattr(args, name), folder/f"{name}_albedo.png")
        original = OUT/"originals"
        color = Image.open(original/f"{name}-g_tColor.png").convert("RGBA")
        normal = Image.open(original/f"{name}-g_tNormal.png").convert("RGBA")
        ao = Image.open(original/f"{name}-g_tAmbientOcclusion.png").convert("RGB")
        # complex.shader's compiled normal texture is packed, not an RGB XYZ
        # source normal. Reconstruct its positive Z from tangent-space XY.
        # Normalising the packed blue surface channel exaggerates the slopes.
        packed = np.asarray(normal, dtype=np.float32)/255
        xy = gaussian_filter(packed[:, :, :2]*2-1, (.55, .55, 0), mode="nearest")
        z = np.sqrt(np.maximum(1-np.sum(xy*xy, axis=2), .0001))
        n = np.dstack((xy, z))
        n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6)
        save_map(folder/f"{name}_macro_normal.png", n*.5+.5)
        # Coverage and tint masks retain their exact original texels and layout.
        mask = color.getchannel("A")
        Image.merge("RGB", (mask, mask, mask)).save(folder/f"{name}_coverage.png")
        tint = normal.getchannel("A")
        Image.merge("RGB", (tint, tint, tint)).save(folder/f"{name}_tint.png")
        # Some compiled single-channel engine AO textures read back as all zero.
        # Such a readback is not usable occlusion; do not black out the garment.
        if not np.asarray(ao).any():
            ao = Image.new("RGB", normal.size, (245, 245, 245))
        ao.save(folder/f"{name}_ao.png")
        r = np.clip(packed[:, :, 2]*.65+roughness*.35, .60 if name=="gloves" else .76, .92)
        save_map(folder/f"{name}_roughness.png", np.repeat(r[:, :, None], 3, axis=2))
        (folder/f"{name}.vmat").write_text(material(name, name=="gloves", roughness, scale, strength), encoding="utf-8")
        assert np.array_equal(np.asarray(Image.open(folder/f"{name}_coverage.png"))[:, :, 0], np.asarray(mask))
    shader = stage/"Assets/shaders/viewmodel_fabric_v2.shader"
    shader.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/"Sources/Clothing/firstperson-v2/viewmodel_fabric_v2.shader", shader)
    manifest = {"revision": "firstperson-clothing-v2", "generated_with": "built-in image_gen",
                "generated": generated, "fine_maps": fine, "files": {},
                "coverage_and_tint_masks_exact": True, "original_assets_modified": False,
                "scene_and_prefabs_are_not_targets": True}
    for path in (stage/"Assets").rglob("*"):
        if path.is_file():
            relative = path.relative_to(stage).as_posix()
            current = ROOT/relative
            assert not current.exists(), "Private v2 resource already exists: "+relative
            manifest["files"][relative] = {"before": None, "after": sha(path),
                "source": path.relative_to(ROOT).as_posix()}
    manifest["source_sha256"] = {str(p.relative_to(ROOT).as_posix()): sha(p) for p in
        (Path(__file__).resolve(), ROOT/"Sources/Clothing/firstperson-v2/viewmodel_fabric_v2.shader")}
    (stage/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"generated": generated, "fine_maps": fine, "files": len(manifest["files"]),
                      "coverage_exact": True, "canonical_assets_written": False}))


if __name__ == "__main__":
    main()
