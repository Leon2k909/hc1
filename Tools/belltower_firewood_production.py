"""Stage the previously reviewed Belltower firewood albedos as native PBR assets.

Albedos come from the approved ImageGen trial without pixel edits. Derived
normals and roughness maps supply small bark and split-fibre relief. All assets
are staged independently of the editor; publish via the guarded native importer.

    python Tools/belltower_firewood_production.py
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "output/belltower/quality/firewood-production-v1"
RESOURCE = "materials/belltower/firewood-v2"
SOURCE_DIR = ROOT / "Sources/Belltower/generated"
OLD_TRIAL = ROOT / "Sources/Belltower/gardens/firewood-trial-v1.json"

TEXTURES = {
    "bark": ("firewood-bark-v1.png", .88, 1.35),
    "cuts": ("firewood-cuts-v1.png", .90, .45),
    "split": ("firewood-split-v1.png", .86, 1.1),
}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def derived_maps(image, rough_base, relief):
    source = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    srgb = source[..., :3].astype(np.float32) / 255.0
    luminance = .2126 * srgb[..., 0] + .7152 * srgb[..., 1] + .0722 * srgb[..., 2]
    # Separate broad photographed colour variation from fine physical cracks.
    soft = gaussian_filter(luminance, 1.4, mode="wrap")
    broad = gaussian_filter(luminance, 17.0, mode="wrap")
    height = soft * .75 + (soft - broad) * .65
    dy, dx = np.gradient(height)
    nx, ny = -dx * relief * 65.0, -dy * relief * 65.0
    nz = np.ones_like(nx)
    mag = np.sqrt(nx * nx + ny * ny + nz * nz)
    encoded = np.stack((nx / mag, ny / mag, nz / mag), axis=2)
    normals = np.uint8(np.clip(np.rint((encoded * .5 + .5) * 255.0), 0, 255))
    # A cut-face atlas contains genuine transparency; leave its empty pixels
    # neutral so compression cannot pull stray normal colour into wood edges.
    normals[source[..., 3] < 128] = (128, 128, 255)
    rough = np.uint8(np.clip(np.rint(255 * (
        rough_base - .12 * (luminance - broad) + .025 * (1.0 - np.abs(luminance - broad))
    )), 0, 255))
    rough[source[..., 3] < 128] = 255
    return Image.fromarray(normals, "RGB"), Image.fromarray(rough, "L")


def material_text(kind):
    extra = '    F_ALPHA_TEST "1"\n    g_flAlphaTestReference "0.5"\n' if kind == "cuts" else ""
    return (
        '// Original ImageGen albedo; derived roughness and normal: Tools/belltower_firewood_production.py\n'
        '"Layer0"\n{\n'
        '    shader "shaders/complex.shader"\n'
        '    F_SPECULAR "1"\n'
        + extra
        + f'    TextureColor "{RESOURCE}/{kind}_color.png"\n'
        + f'    TextureNormal "{RESOURCE}/{kind}_normal.png"\n'
        + f'    TextureRoughness "{RESOURCE}/{kind}_rough.png"\n'
        + '    g_flRoughnessScaleFactor "1"\n'
          '    g_flMetalness "0"\n'
          '    g_vColorTint "[1 1 1 1]"\n'
          '}\n'
    )


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    previous = json.loads(OLD_TRIAL.read_text(encoding="utf-8"))
    source_hashes = previous["source_sha256"]
    entries = []
    for kind, (name, rough, relief) in TEXTURES.items():
        source = SOURCE_DIR / name
        relative_source = source.relative_to(ROOT).as_posix()
        assert digest(source) == source_hashes[relative_source], f"Firewood source changed: {source}"
        with Image.open(source) as input_image:
            # The ImageGen requests specified 2K, but retained originals are
            # actually 1254px. Preserve their authentic pixels and dimensions.
            assert input_image.width == input_image.height and input_image.width >= 1024, f"Unexpected {kind} texture size"
            assert input_image.mode in ("RGB", "RGBA")
            normal, roughness = derived_maps(input_image, rough, relief)
            normal = normal.resize((2048, 2048), Image.Resampling.BICUBIC)
            roughness = roughness.resize((2048, 2048), Image.Resampling.BICUBIC)
            normal.save(STAGE / f"{kind}_normal.png", compress_level=6)
            roughness.save(STAGE / f"{kind}_rough.png", compress_level=6)
        # Keep source ImageGen pixels in Sources; scale only the production copy
        # to a power-of-two size required by native normal/alpha mip filtering.
        with Image.open(source) as image:
            image.resize((2048, 2048), Image.Resampling.LANCZOS).save(STAGE / f"{kind}_color.png")
        (STAGE / f"{kind}.vmat").write_text(material_text(kind), encoding="utf-8", newline="\n")
        for filename in (f"{kind}_color.png", f"{kind}_normal.png", f"{kind}_rough.png", f"{kind}.vmat"):
            output = STAGE / filename
            target = ROOT / "Assets" / RESOURCE / filename
            if target.exists():
                assert digest(target) == digest(output), f"Different production asset already exists: {target}"
            entries.append({"path": f"{RESOURCE}/{filename}",
                            "source": output.relative_to(ROOT).as_posix(),
                            "sha256": digest(output)})
    manifest = {
        "revision": "firewood-production-v1",
        "state": "staged for native comparison and guarded import",
        "sources": {key: value for key, value in source_hashes.items()
                    if key.startswith("Sources/Belltower/generated/firewood-")},
        "geometry_generator": "Tools/belltower_firewood_trial.py",
        "geometry_generator_sha256": digest(ROOT / "Tools/belltower_firewood_trial.py"),
        "staging_generator": "Tools/belltower_firewood_production.py",
        "staging_generator_sha256": digest(Path(__file__)),
        "original_source_albedos_untouched": True,
        "production_resolution": 2048,
        "normal_maps_derived_from_existing_albedo": True,
        "collision_changes": False,
        "files": entries,
    }
    (STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"staged": len(entries), "resources": RESOURCE, "source_albedos_preserved": True}))


if __name__ == "__main__":
    main()
