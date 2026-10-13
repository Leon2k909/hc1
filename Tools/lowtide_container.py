"""Lowtide's red freight-container finish, from built-in ImageGen.

rtk proxy python Tools/lowtide_container.py --textures --patch-models

The generated albedo is preserved byte-for-byte. Bake matching surface data and
remap only Lowtide's red container; retain the existing 48-inch UVs and collision.
"""
import argparse
import hashlib
import io
import json
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K

RESOURCE = "materials/lowtide/containers"
OUT = K.ASSETS / RESOURCE
PAINT = "rw_container_red"
MATERIAL = f"{RESOURCE}/lt_container_red.vmat"
COLOUR = OUT / "lt_container_red_color.png"
TILE = 48.0
REPORT = K.ROOT / "output/lowtide/container-pass"


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        temp = path.with_name(path.name + ".writing")
        temp.write_bytes(data)
        temp.replace(path)


def meta(path):
    sidecar = path.with_suffix(path.suffix + ".meta")
    if not sidecar.exists():
        key = "hc1/lowtide/container/" + path.relative_to(K.ASSETS).as_posix()
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL, key))}, indent=2) + "\n")


def write_materials():
    # Leave the image's colour, chips and salt-weathering exactly as generated.
    image = Image.open(COLOUR).convert("RGB")
    # s&box's combined normal/roughness mip filter requires a power-of-two grid.
    # Resample only the numerical bake input; retain the generated albedo file.
    sample = image.resize((2048, 2048), Image.Resampling.LANCZOS)
    rgb = np.asarray(sample, dtype=np.float32) / 255.0
    lum = rgb @ np.array((.2126, .7152, .0722), dtype=np.float32)
    exposed = np.clip((.32 - lum) / .14, 0, 1)
    rust = np.clip((rgb[..., 1] / np.maximum(rgb[..., 0], .01) - .40) / .28, 0, 1) * exposed
    bare = exposed * (1 - rust)
    fine = gaussian_filter(lum, .65, mode="wrap") - gaussian_filter(lum, 5, mode="wrap")
    height = .008 * fine - .008 * gaussian_filter(exposed, .7, mode="wrap")
    # OpenGL normals: image Y is down, tangent Y is up. Reuse the existing
    # container's physical corrugation and add only thin paint/chip relief.
    base_image = Image.open(K.ASSETS / "materials/railhead/container_normal.png")
    base = np.asarray(base_image.convert("RGB").resize(sample.size, Image.Resampling.BILINEAR), dtype=np.float32) / 127.5 - 1
    nz = np.maximum(base[..., 2], .05)
    scale = sample.width / TILE
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5 * scale
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5 * scale
    normal = np.stack((base[..., 0] / nz - dx, base[..., 1] / nz + dy, np.ones_like(lum)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    rough = np.clip(.69 + .12 * exposed + .08 * rust + .08 * fine, .59, .94)
    metal = .68 * bare
    maps = {
        "normal": np.rint((normal * .5 + .5) * 255).clip(0, 255).astype(np.uint8),
        "roughness": np.rint(rough * 255).astype(np.uint8),
        "metalness": np.rint(metal * 255).astype(np.uint8),
    }
    for suffix, data in maps.items():
        path = OUT / f"lt_container_red_{suffix}.png"
        buffer = io.BytesIO()
        Image.fromarray(data).save(buffer, format="PNG", optimize=True)
        write_bytes(path, buffer.getvalue())
        meta(path)
    K.write_text(K.ASSETS / MATERIAL, f'''// Tools/lowtide_container.py: built-in ImageGen weathered red steel
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_METALNESS_TEXTURE "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0"
    TextureColor "{RESOURCE}/lt_container_red_color.png"
    TextureNormal "{RESOURCE}/lt_container_red_normal.png"
    TextureRoughness "{RESOURCE}/lt_container_red_roughness.png"
    TextureMetalness "{RESOURCE}/lt_container_red_metalness.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}}
''')
    meta(COLOUR)
    meta(K.ASSETS / MATERIAL)
    REPORT.mkdir(parents=True, exist_ok=True)
    K.write_text(REPORT / "surface.json", json.dumps({
        "albedo_dimensions": image.size,
        "surface_map_dimensions": sample.size,
        "albedo_sha256": hashlib.sha256(COLOUR.read_bytes()).hexdigest(),
        "normal_convention": "OpenGL, existing corrugation plus thin paint relief",
        "tile_inches": TILE,
        "roughness_range": [float(rough.min()), float(rough.max())],
        "metalness_range": [float(metal.min()), float(metal.max())],
        "material": MATERIAL,
    }, indent=2) + "\n")


def configure(model):
    if PAINT in model.polygons:
        model.material_overrides[PAINT] = MATERIAL
        model.tile_overrides[PAINT] = TILE


def patch_models():
    path = K.ASSETS / "models/maps/lowtide/lowtide_dress_west.vmdl"
    original = path.read_bytes()
    old = b'to = "materials/railhead/rw_container_red.vmat"'
    new = f'to = "{MATERIAL}"'.encode()
    if new in original and old not in original:
        return
    if original.count(old) != 1:
        raise ValueError("Expected exactly one Lowtide red-container material remap")
    updated = original.replace(old, new)
    # A reversible material remap preserves all mesh and collision data.
    assert updated.replace(new, old) == original
    backup = REPORT / "before/lowtide_dress_west.vmdl"
    if not backup.exists():
        write_bytes(backup, original)
    write_bytes(path, updated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--textures", action="store_true")
    parser.add_argument("--patch-models", action="store_true")
    args = parser.parse_args()
    if args.textures:
        write_materials()
        print("Lowtide red container: generated albedo, corrugation normal, roughness and exposed-steel metalness")
    if args.patch_models:
        patch_models()
        print("Lowtide west dressing: red-container material remapped")


if __name__ == "__main__":
    main()
