"""Lowtide's generated granite paving, preserving the scan's original pixels.

The scan is packed into a power-of-two atlas without resampling. An interior
region repeats between grit courses, with the original approximately 8 x 5.33
inch sett size applied to the existing 64-inch mesh UVs. Normal, roughness and
AO data follow the new joints; no geometry or collision needs rebuilding.

    rtk proxy python Tools/lowtide_paving.py --source <generated.png>
    rtk proxy python Tools/lowtide_paving.py
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage, signal

import building_textures as BT
import map_kit as K
import terrain_textures as T
from lowtide_brick import metadata

DIRECTORY = K.ASSETS / "materials/lowtide"
SOURCE = K.ROOT / "Tools/lowtide_paving_source.png"
SETTINGS = K.ROOT / "Tools/lowtide_paving_imagegen.json"
RESOURCE = "materials/lowtide/lt_setts"
TILE_UNITS = 64.0


def read_surface():
    with Image.open(SOURCE) as image:
        if image.width != image.height or image.width < 1024:
            raise ValueError("Expected a square generated granite scan at least 1024px wide")
        return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def layout(rgb):
    # Blur out individual mineral grains before finding the recessed grit lines.
    grey = ndimage.gaussian_filter(rgb.mean(axis=2), 3.0)
    rows, _ = signal.find_peaks(-grey.mean(axis=1), distance=len(grey) / 18, prominence=0.012)
    if len(rows) < 5:
        raise ValueError("Could not identify the paving's grit courses")
    first, last = int(rows[0]), int(rows[-1])
    if (len(rows) - 1) % 2:
        last = int(rows[-2])  # An even course count preserves the stagger at the vertical wrap.
    course = float(np.median(np.diff(rows)))
    widths = []
    for a, b in zip(rows[:-1], rows[1:]):
        middle = int((a + b) / 2)
        profile = grey[middle - 5:middle + 6].mean(axis=0)
        joints, _ = signal.find_peaks(-profile, distance=rgb.shape[1] / 10, prominence=0.055)
        widths.extend(np.diff(joints).tolist())
    if len(widths) < 8:
        raise ValueError("Could not identify the paving's vertical joints")
    stone = float(np.median(widths))
    # Match the stagger and stone/grit phase at the horizontal wrap. Keep a
    # margin around the selected region for filtering and periodic edge samples.
    best = None
    middle = grey[first:last]
    for left in range(int(stone * 0.2), int(stone), 2):
        for right in range(int(rgb.shape[1] - stone * 1.2), int(rgb.shape[1] - stone * 0.2), 2):
            period = (right - left) / stone
            if abs(period - round(period)) > 0.08:
                continue
            phase = np.mean(np.abs((middle[:, left] < 0.40).astype(float)
                                   - (middle[:, right] < 0.40).astype(float)))
            colour = np.mean(np.abs(middle[:, left] - middle[:, right]))
            score = float(phase * 0.5 + colour)
            if best is None or score < best[0]:
                best = (score, left, right)
    if best is None:
        raise ValueError("Could not find matching repeat boundaries")
    _, left, right = best
    atlas = 1 << int(np.ceil(np.log2(rgb.shape[0])))
    region = (left / atlas, first / atlas, (right - left) / atlas, (last - first) / atlas)
    scale = (TILE_UNITS * stone / (8.0 * (right - left)),
             TILE_UNITS * course / ((16.0 / 3.0) * (last - first)))
    return scale, region


def bake_surface_maps():
    rgb = read_surface()
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    smooth = ndimage.gaussian_filter(luminance, 3.0, mode="wrap")
    stone = T.smoothstep(0.33, 0.44, smooth)
    stone = ndimage.gaussian_filter(stone, 1.1, mode="wrap")
    grain = luminance - ndimage.gaussian_filter(luminance, 1.5, mode="wrap")
    # Shallow edge relief and restrained grain keep the tops flat. Colour
    # differences between stones must not turn into inflated cobbles.
    height = 0.18 + stone * 0.38 + grain * stone * 0.055
    normal = BT.gl_normals(height, 4.0 * rgb.shape[0] / 1024.0)
    roughness = np.clip(0.93 - stone * 0.12 + grain * 0.10, 0.78, 0.96)
    ao = 0.92 + stone * 0.08
    arrays = {
        "color": np.rint(rgb * 255).astype(np.uint8),
        "normal": np.rint((normal + 1) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(roughness * 255).astype(np.uint8),
        "ao": np.rint(ao * 255).astype(np.uint8),
    }
    atlas = 1 << int(np.ceil(np.log2(rgb.shape[0])))
    for suffix, array in arrays.items():
        repeats = (int(np.ceil(atlas / array.shape[0])), int(np.ceil(atlas / array.shape[1])))
        if array.ndim == 3:
            repeats += (1,)
        packed = np.tile(array, repeats)[:atlas, :atlas]
        path = DIRECTORY / f"lt_setts_{suffix}.png"
        Image.fromarray(packed).save(path, optimize=True)
        metadata(path)
    scale, region = layout(rgb)
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    settings.update(source_dimensions=list(rgb.shape[:2]), atlas_dimensions=[atlas, atlas],
                    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                    repeat_scale=list(scale), repeat_region_normalized=list(region))
    K.write_text(SETTINGS, json.dumps(settings, indent=2) + "\n")
    return scale, region


def write_materials():
    if not SOURCE.exists() or not (DIRECTORY / "lt_setts_color.png").exists():
        raise FileNotFoundError("Bake Tools/lowtide_paving.py before writing the Lowtide materials")
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    u, v = settings["repeat_scale"]
    region = " ".join(f"{value:.8f}" for value in settings["repeat_region_normalized"])
    path = DIRECTORY / "lt_setts.vmat"
    K.write_text(path, f'''// Tools/lowtide_paving.py: generated granite, matching shallow relief, original world scale.
"Layer0"
{{
    shader "shaders/hc1_lowtide_paving.shader"
    F_SPECULAR "1"
    TextureColor "{RESOURCE}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness "{RESOURCE}_rough.png"
    TextureMetalness "[0.0 0.0 0.0 0.0]"
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    g_vPavingScale "[{u:.8f} {v:.8f}]"
    g_vPavingRegion "[{region}]"
}}
''')
    metadata(path)


def configure(model):
    if "setts" in model.polygons:
        model.material_overrides["setts"] = f"{RESOURCE}.vmat"
        model.tile_overrides["setts"] = TILE_UNITS


def remap_existing_models():
    pattern = r'(from\s*=\s*"setts\.vmat"\s+to\s*=\s*")materials/buildings/setts\.vmat(")'
    for path in (K.ASSETS / "models/maps/lowtide").glob("*.vmdl"):
        updated, count = re.subn(pattern, rf'\g<1>{RESOURCE}.vmat\2', path.read_text(encoding="utf-8"))
        if count:
            K.write_text(path, updated)
            print(f"remapped {path.name}: {count} paving material")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="copy the selected generated granite scan unchanged")
    args = parser.parse_args()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if args.source and args.source.resolve() != SOURCE.resolve():
        shutil.copy2(args.source, SOURCE)
    scale, region = bake_surface_maps()
    write_materials()
    remap_existing_models()
    print(f"wrote Lowtide paving; UV scale {scale}, repeat region {region}")


if __name__ == "__main__":
    main()
