"""Lowtide's generated brick albedo and matching material data.

The generated source image is preserved unchanged. A mortar-bounded interior tile is resampled into a square
power-of-two texture, with matching numeric surface maps baked from its mortar mask. Material UV scale keeps
approximately 8-inch bricks and
2 2/3-inch courses on the map's existing 64-inch UV tiles; no geometry or collisions need rebuilding.

    rtk proxy python Tools/lowtide_brick.py --source <generated.png>
    rtk proxy python Tools/lowtide_brick.py
"""
import argparse
import hashlib
import io
import json
import re
import shutil
import uuid
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage, signal

import map_kit as K
import terrain_textures as T

DIRECTORY = K.ASSETS / "materials/lowtide"
COLOUR = DIRECTORY / "lt_brick_v2_color.png"
SOURCE = K.ROOT / "Tools/lowtide_brick_v2_source.png"
RESOURCE = "materials/lowtide/lt_brick_v2"
TEXTURE_SIZE = 2048
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
        guid = uuid.uuid5(uuid.NAMESPACE_URL, path.relative_to(K.ASSETS).as_posix())
        K.write_text(sidecar, json.dumps({"guid": str(guid)}, indent=2) + "\n")


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
    # Choose matching head joints, not simply two red columns: two brick faces can have similar masks while
    # joining half of one brick to a differently coloured half of another. Joint-density peaks constrain the
    # candidates to real running-bond boundaries, then the row-by-row phase selects the matching stagger.
    column_profile = ndimage.gaussian_filter1d(mortar.mean(axis=0), 1.0)
    boundaries, _ = signal.find_peaks(column_profile, distance=brick * 0.30, prominence=0.02)
    lefts = [int(x) for x in boundaries if brick * 0.35 < x < brick * 1.5]
    rights = [int(x) for x in boundaries if width - brick * 1.75 < x < width - brick * 0.35]
    if not lefts or not rights:
        raise ValueError("Could not find matching interior head-joint boundaries")
    best = None
    for left in lefts:
        for right in rights:
            phase = float(np.mean(np.abs(clay[:, left] - clay[:, right])))
            colour = float(np.mean(np.abs(rgb[:, left] - rgb[:, right])))
            score = phase * 2.0 + colour - float(column_profile[left] + column_profile[right])
            if best is None or score < best[0]:
                best = (score, left, right)
    _, left, right = best
    # Even course spans retain the stagger phase. Match bed-joint masks and colour near the source margins,
    # allowing a couple of courses to be dropped where the generated boundary is uneven.
    beds = []
    for start in range(min(4, len(rows) - 4)):
        for finish in range(max(start + 4, len(rows) - 4), len(rows)):
            if (finish - start) % 2:
                continue
            a, b = int(rows[start]), int(rows[finish])
            phase = float(np.mean(np.abs(clay[a, left:right] - clay[b, left:right])))
            colour = float(np.mean(np.abs(rgb[a, left:right] - rgb[b, left:right])))
            beds.append((phase * 2.0 + colour, a, b))
    _, first, last = min(beds)
    atlas = 1 << int(np.ceil(np.log2(max(height, width))))
    region = (left / atlas, first / atlas, (right - left) / atlas, (last - first) / atlas)
    scale = (8.0 * brick / (right - left), 24.0 * course / (last - first))
    return scale, region


def bake_surface_maps():
    rgb, clay = read_surface()
    scale, region = layout(clay, rgb)
    atlas = 1 << int(np.ceil(np.log2(max(clay.shape))))
    left, top, width, height = (int(round(value * atlas)) for value in region)
    # The tile wraps at matching mortar courses and bond phases. Sampling an unwrapped UV coordinate then lets
    # the GPU choose correct mip levels even at a repeat boundary, unlike frac() into a non-periodic atlas.
    crop = Image.fromarray(np.rint(rgb * 255).astype(np.uint8)).crop((left, top, left + width, top + height))
    rgb = np.asarray(crop.resize((TEXTURE_SIZE, TEXTURE_SIZE), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    mask = Image.fromarray(clay[top:top + height, left:left + width], mode="F")
    clay = np.asarray(mask.resize((TEXTURE_SIZE, TEXTURE_SIZE), Image.Resampling.BILINEAR), dtype=np.float32)
    # Close tiny neutral flecks inside the clay, so pale mineral inclusions do not become mortar-depth craters.
    clay = ndimage.minimum_filter(ndimage.maximum_filter(clay, size=3, mode="wrap"), size=3, mode="wrap")
    smooth_clay = ndimage.gaussian_filter(clay, 2.2, mode="wrap")
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    detail = luminance - ndimage.gaussian_filter(luminance, 3.5, mode="wrap")
    # Height in millimetres: shallow recessed joints and submillimetre gritty detail. Calculate each gradient
    # against the tile's physical dimensions, rather than changing relief when texture resolution changes.
    relief = smooth_clay * 7.0 + detail * smooth_clay * 3.0
    mm_u, mm_v = TILE_UNITS * 25.4 / np.asarray(scale)
    dx = (np.roll(relief, -1, 1) - np.roll(relief, 1, 1)) * (TEXTURE_SIZE / mm_u) * 0.5
    dy = (np.roll(relief, -1, 0) - np.roll(relief, 1, 0)) * (TEXTURE_SIZE / mm_v) * 0.5
    normal = np.stack([-dx, dy, np.ones_like(relief)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    roughness = np.clip(0.95 - smooth_clay * 0.13 + detail * 0.20, 0.76, 0.98)
    ao = np.clip(0.88 + smooth_clay * 0.12, 0.88, 1.0)
    maps = {
        "color": np.rint(rgb * 255.0).clip(0, 255).astype(np.uint8),
        "normal": np.rint((normal + 1.0) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(roughness * 255.0).astype(np.uint8),
        "ao": np.rint(ao * 255.0).astype(np.uint8),
    }
    for suffix, array in maps.items():
        path = DIRECTORY / f"lt_brick_v2_{suffix}.png"
        buffer = io.BytesIO()
        Image.fromarray(array).save(buffer, format="PNG", optimize=True)
        data = buffer.getvalue()
        if not path.exists() or path.read_bytes() != data:
            temporary = path.with_name(path.name + ".writing")
            temporary.write_bytes(data)
            temporary.replace(path)
        metadata(path)
    return scale


def material_text(tint=(1.0, 1.0, 1.0), roughness=None):
    rgb, clay = read_surface()
    (u, v), _ = layout(clay, rgb)
    rough = f'"{RESOURCE}_rough.png"' if roughness is None else f'"[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"'
    return f'''// Tools/lowtide_brick.py: seamless generated albedo, matching mortar relief, physical brick scale.
"Layer0"
{{
    shader "shaders/hc1_brick.shader"
    TextureColor "{RESOURCE}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness {rough}
    TextureMetalness "materials/default/default_black_mask.tga"
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    TextureBlendMask "materials/default/default_black_mask.tga"
    g_vBrickScale "[{u:.6f} {v:.6f} 0.0 0.0]"
    g_flTintColor "[{tint[0]:.3f} {tint[1]:.3f} {tint[2]:.3f}]"
}}
'''


def write_materials():
    if not SOURCE.exists() or not COLOUR.exists():
        raise FileNotFoundError(f"Generated Lowtide brick source/tile is missing: {SOURCE}")
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
