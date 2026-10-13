"""Lowtide's generated brick albedo and matching material data.

The generated source image is copied unchanged and packed without resampling into a power-of-two GPU atlas.
Numeric surface maps are baked from its mortar mask, rather than
reusing the old texture's differently positioned joints. Material UV scale keeps approximately 8-inch bricks and
2 2/3-inch courses on the map's existing 64-inch UV tiles; no geometry or collisions need rebuilding.

    rtk proxy python Tools/lowtide_brick.py --source <generated.png>
    rtk proxy python Tools/lowtide_brick.py
"""
import argparse
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage, signal

import building_textures as BT
import map_kit as K
import terrain_textures as T

DIRECTORY = K.ASSETS / "materials/lowtide"
COLOUR = DIRECTORY / "lt_brick_color.png"
SOURCE = K.ROOT / "Tools/lowtide_brick_source.png"
RESOURCE = "materials/lowtide/lt_brick"
TILE_UNITS = 64.0
VARIANTS = {
    "lt_brick": ((1.0, 1.0, 1.0), None),
    "lt_brick_soot": ((0.66, 0.58, 0.54), None),
    "lt_brick_glazed": ((0.34, 0.28, 0.27), 0.32),
    "lt_brick_slime": ((0.36, 0.42, 0.30), 0.30),
}


def metadata(path):
    sidecar = Path(str(path) + ".meta")
    if not sidecar.exists():
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid4())}, indent=2) + "\n")


def read_surface():
    with Image.open(SOURCE) as image:
        if image.width != image.height or min(image.size) < 1024:
            raise ValueError("Expected a square high-resolution generated brick texture")
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    # The lime mortar is neutral; red/brown fired clay remains chromatic even on dark bricks. Lighting and brick
    # colour variation must not become large height changes, so only this material mask gives the joint relief.
    chroma = (rgb[..., 0] - rgb[..., 1]) / np.maximum(rgb[..., 0], 0.05)
    clay = T.smoothstep(0.10, 0.25, chroma)
    return rgb, clay


def layout(clay, rgb):
    height, width = clay.shape
    mortar = 1.0 - clay
    rows, _ = signal.find_peaks(ndimage.gaussian_filter1d(mortar.mean(axis=1), 1.0),
                                distance=height / 40, prominence=0.12)
    if len(rows) < 4:
        raise ValueError("Could not identify horizontal mortar courses")
    course = float(np.median(np.diff(rows)))
    widths = []
    for a, b in zip(rows[:-1], rows[1:]):
        middle = int((a + b) / 2)
        profile = ndimage.gaussian_filter1d(mortar[max(0, middle - 3):middle + 4].mean(axis=0), 1.0)
        joints, _ = signal.find_peaks(profile, distance=width / 20, prominence=0.3)
        widths.extend(np.diff(joints).tolist())
    if len(widths) < 8:
        raise ValueError("Could not identify vertical mortar joints")
    brick = float(np.median(widths))
    # Choose matching interior boundaries instead of assuming the generator made its outside edges periodic.
    # Opposing edges should have the same mortar/brick phase on every row, including the half-brick courses.
    best = None
    for left in range(int(brick * 0.6), int(brick * 1.3), 2):
        for right in range(int(width - brick * 1.3), int(width - brick * 0.6), 2):
            phase = float(np.mean(np.abs(clay[:, left] - clay[:, right])))
            colour = float(np.mean(np.abs(rgb[:, left] - rgb[:, right])))
            score = phase * 2.0 + colour
            if best is None or score < best[0]:
                best = (score, left, right)
    _, left, right = best
    first, last = int(rows[0]), int(rows[-1])
    if (len(rows) - 1) % 2:
        last = int(rows[-2])  # An even number of courses keeps the staggered bond phase across the vertical wrap.
    atlas = 1 << int(np.ceil(np.log2(max(height, width))))
    region = (left / atlas, first / atlas, (right - left) / atlas, (last - first) / atlas)
    scale = (8.0 * brick / (right - left), 24.0 * course / (last - first))
    return scale, region


def bake_surface_maps():
    rgb, clay = read_surface()
    smooth_clay = ndimage.gaussian_filter(clay, 0.8, mode="wrap")
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    detail = luminance - ndimage.gaussian_filter(luminance, 2.0, mode="wrap")
    height = 0.15 + smooth_clay * 0.55 + detail * smooth_clay * 0.12
    normal = BT.gl_normals(height, 3.0 * rgb.shape[0] / 1024.0)
    roughness = np.clip(0.94 - smooth_clay * 0.10 + detail * 0.12, 0.75, 0.98)
    ao = np.clip(0.84 + smooth_clay * 0.16, 0.84, 1.0)
    maps = {
        "color": np.rint(rgb * 255.0).clip(0, 255).astype(np.uint8),
        "normal": np.rint((normal + 1.0) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(roughness * 255.0).astype(np.uint8),
        "ao": np.rint(ao * 255.0).astype(np.uint8),
    }
    for suffix, array in maps.items():
        path = DIRECTORY / f"lt_brick_{suffix}.png"
        atlas = 1 << int(np.ceil(np.log2(max(array.shape[:2]))))
        repetitions = (int(np.ceil(atlas / array.shape[0])), int(np.ceil(atlas / array.shape[1])))
        if array.ndim == 3:
            repetitions += (1,)
        packed = np.tile(array, repetitions)[:atlas, :atlas]
        Image.fromarray(packed).save(path, optimize=True)
        metadata(path)
    return layout(clay, rgb)[0]


def material_text(tint=(1.0, 1.0, 1.0), roughness=None):
    rgb, clay = read_surface()
    (u, v), region = layout(clay, rgb)
    rough = f'"{RESOURCE}_rough.png"' if roughness is None else f'"[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"'
    return f'''// Tools/lowtide_brick.py: generated albedo, matching mortar relief, original world brick scale.
"Layer0"
{{
    shader "shaders/hc1_brick.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.00"
    TextureColor "{RESOURCE}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness {rough}
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    g_vBrickScale "[{u:.6f} {v:.6f}]"
    g_vBrickRegion "[{region[0]:.6f} {region[1]:.6f} {region[2]:.6f} {region[3]:.6f}]"
    g_vColorTint "[{tint[0]:.3f} {tint[1]:.3f} {tint[2]:.3f} 1.0]"
    g_flModelTintAmount "1.0"
}}
'''


def write_materials():
    if not SOURCE.exists() or not COLOUR.exists():
        raise FileNotFoundError(f"Generated Lowtide brick source/atlas is missing: {SOURCE}")
    for name, (tint, roughness) in VARIANTS.items():
        path = DIRECTORY / f"{name}.vmat"
        K.write_text(path, material_text(tint, roughness))
        metadata(path)


def configure(model):
    if "brick" in model.polygons:
        model.material_overrides["brick"] = "materials/lowtide/lt_brick.vmat"
        model.tile_overrides["brick"] = TILE_UNITS


def remap_existing_models():
    pattern = r'(from\s*=\s*"brick\.vmat"\s+to\s*=\s*")materials/buildings/brick\.vmat(")'
    for path in (K.ASSETS / "models/maps/lowtide").glob("*.vmdl"):
        text = path.read_text(encoding="utf-8")
        updated, count = re.subn(pattern, r'\g<1>materials/lowtide/lt_brick.vmat\2', text)
        if count:
            K.write_text(path, updated)
            print(f"remapped {path.name}: {count} brick material")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="copy the selected generated albedo unchanged")
    args = parser.parse_args()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if args.source:
        if args.source.resolve() != SOURCE.resolve():
            shutil.copy2(args.source, SOURCE)
        print(f"copied generated albedo unchanged: {hashlib.sha256(SOURCE.read_bytes()).hexdigest()}")
    scale = bake_surface_maps()
    write_materials()
    remap_existing_models()
    print(f"wrote Lowtide brick materials; UV scale {scale[0]:.6f}, {scale[1]:.6f}")


if __name__ == "__main__":
    main()
