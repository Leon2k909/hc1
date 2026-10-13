"""Lowtide's generated warehouse lime plaster and matching surface maps.

    rtk proxy python Tools/lowtide_plaster.py

Preserve the generated source and every albedo pixel inside a power-of-two atlas.
Bake fine plaster relief and roughness, then remap only Lowtide's existing
whitewash material without rebuilding meshes.
"""
import hashlib
import io
import json
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K
import terrain_textures as T

PAINT = "whitewash"
TILE_UNITS = 128.0
DIRECTORY = K.ASSETS / "materials/lowtide"
RESOURCE = "materials/lowtide/lt_plaster"
MATERIAL = RESOURCE + ".vmat"
SOURCE = K.ROOT / "Tools/lowtide_plaster_source.png"
REPORT = K.ROOT / "output/lowtide/plaster-pass"


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        temporary = path.with_name(path.name + ".writing")
        temporary.write_bytes(data)
        temporary.replace(path)


def metadata(path):
    sidecar = path.with_name(path.name + ".meta")
    if not sidecar.exists():
        key = "hc1/lowtide/plaster/" + path.relative_to(K.ASSETS).as_posix()
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL, key))}, indent=2) + "\n")


def bake():
    with Image.open(SOURCE) as image:
        if image.width != image.height or image.width < 1024:
            raise ValueError("Expected a square generated plaster texture of at least 1024 pixels")
        dimensions = image.size
        colour_pixels = np.asarray(image.convert("RGB"))
    rgb = colour_pixels.astype(np.float32) / 255.0
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    warm = (rgb[..., 0] - rgb[..., 2]) / np.maximum(rgb[..., 0], 0.05)
    exposed = T.smoothstep(0.13, 0.25, warm)
    fine = gaussian_filter(luminance, 0.65, mode="wrap") - gaussian_filter(luminance, 3.0, mode="wrap")
    trowel = gaussian_filter(luminance, 2.0, mode="wrap") - gaussian_filter(luminance, 14.0, mode="wrap")
    # Millimetre-scale mineral grain, shallow trowel ridges and lost limewash.
    # Large colour changes are deliberately excluded from the relief.
    height = fine * 0.18 + trowel * 0.05 - gaussian_filter(exposed, 1.0, mode="wrap") * 0.025
    pixels_per_inch = dimensions[0] / TILE_UNITS
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5 * pixels_per_inch
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5 * pixels_per_inch
    normal = np.stack((-dx, dy, np.ones_like(luminance)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    roughness = np.clip(0.93 + exposed * 0.05 + np.abs(fine) * 0.10, 0.91, 0.995)
    ao = 1.0 - exposed * 0.04
    maps = {
        "color": colour_pixels,
        "normal": np.rint((normal + 1.0) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(roughness * 255.0).astype(np.uint8),
        "ao": np.rint(ao * 255.0).astype(np.uint8),
    }
    atlas = 1 << int(np.ceil(np.log2(dimensions[0])))
    for suffix, array in maps.items():
        path = DIRECTORY / f"lt_plaster_{suffix}.png"
        buffer = io.BytesIO()
        repetitions = (int(np.ceil(atlas / array.shape[0])), int(np.ceil(atlas / array.shape[1])))
        if array.ndim == 3:
            repetitions += (1,)
        packed = np.tile(array, repetitions)[:atlas, :atlas]
        Image.fromarray(packed).save(buffer, format="PNG", optimize=True)
        write_bytes(path, buffer.getvalue())
        metadata(path)
    colour = DIRECTORY / "lt_plaster_color.png"
    with Image.open(colour) as packed:
        assert np.array_equal(np.asarray(packed)[:dimensions[1], :dimensions[0]], colour_pixels)
    REPORT.mkdir(parents=True, exist_ok=True)
    K.write_text(REPORT / "surface.json", json.dumps({
        "material": MATERIAL,
        "albedo_dimensions": dimensions,
        "atlas_dimensions": [atlas, atlas],
        "surface_map_dimensions": [atlas, atlas],
        "albedo_sha256": hashlib.sha256(colour.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "generated_albedo_pixels_preserved": True,
        "normal_convention": "OpenGL, fine mineral grain and shallow limewash relief",
        "tile_inches": TILE_UNITS,
        "roughness_range": [float(roughness.min()), float(roughness.max())],
        "damp_staining": "world-height anchored, irregular fade above ground-floor contact",
        "geometry_uvs_and_collisions_changed": False,
    }, indent=2) + "\n")


def write_materials():
    for suffix in ("color", "normal", "rough", "ao"):
        if not (DIRECTORY / f"lt_plaster_{suffix}.png").exists():
            raise FileNotFoundError("Bake the generated Lowtide plaster textures first")
    with Image.open(SOURCE) as source:
        size = source.width
    with Image.open(DIRECTORY / "lt_plaster_color.png") as packed:
        atlas = packed.width
    region = (0.5 / atlas, 0.5 / atlas, (size - 1) / atlas, (size - 1) / atlas)
    path = K.ASSETS / MATERIAL
    K.write_text(path, f'''// Tools/lowtide_plaster.py: generated lime plaster, matching grain, ground-floor damp wear.
"Layer0"
{{
    shader "shaders/hc1_lowtide_plaster.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.00"
    TextureColor "{RESOURCE}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness "{RESOURCE}_rough.png"
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    g_vPlasterRegion "[{region[0]:.8f} {region[1]:.8f} {region[2]:.8f} {region[3]:.8f}]"
    g_flDampHeight "28"
    g_flDampStrength "0.40"
    g_vDampColor "[0.53 0.49 0.43]"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}}
''')
    metadata(path)
    metadata(K.ASSETS / "shaders/hc1_lowtide_plaster.shader")


def configure(model):
    if PAINT in model.polygons:
        model.material_overrides[PAINT] = MATERIAL
        model.tile_overrides[PAINT] = TILE_UNITS


def remap_existing_models():
    old = b'to = "materials/buildings/whitewash.vmat"'
    new = f'to = "{MATERIAL}"'.encode()
    for path in (K.ASSETS / "models/maps/lowtide").glob("*.vmdl"):
        original = path.read_bytes()
        if old not in original:
            continue
        if original.count(old) != 1:
            raise ValueError(f"Expected exactly one whitewash remap in {path.name}")
        updated = original.replace(old, new)
        assert updated.replace(new, old) == original
        backup = REPORT / "before" / path.relative_to(K.ROOT)
        if not backup.exists():
            write_bytes(backup, original)
        write_bytes(path, updated)
        print(f"{path.name}: Lowtide-only plaster material remap; all model and collision data preserved")


def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    bake()
    write_materials()
    remap_existing_models()
    print("Lowtide warehouse plaster: generated warm limewash, sharp mineral grain, matching relief and "
          "roughness, irregular floor-contact staining.")


if __name__ == "__main__":
    main()
