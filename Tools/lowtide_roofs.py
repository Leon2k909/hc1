"""Generated natural slate for Lowtide, preserving all roof geometry and collision."""
import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K
from lowtide_brick import metadata

DIRECTORY = K.ASSETS / "materials/lowtide/roofs"
RESOURCE = "materials/lowtide/roofs"
SOURCE = K.ROOT / "Sources/Lowtide/visual-target/slate-source.png"
MATERIAL = f"{RESOURCE}/lt_slate.vmat"


def bake(source):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() != SOURCE.resolve():
        shutil.copy2(source, SOURCE)
    rgb = np.asarray(Image.open(SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), float) / 255
    lum = rgb @ np.array([.2126, .7152, .0722])
    smooth = ndimage.gaussian_filter(lum, 5, mode="wrap")
    detail = lum - smooth
    joints = np.clip((smooth - lum - .035) * 8, 0, 1)
    # Technical relief from the scan: thin split-stone edges, not deep cobbles.
    # Physical sampling covers two metres. No baked sun or extra colour noise.
    height = ndimage.gaussian_filter(detail, 1.0, mode="wrap") * .002 - joints * .0045
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 512
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 512
    normal = np.stack([-dx, dy, np.ones_like(lum)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    mineral = np.maximum(rgb[..., 0] - rgb[..., 2], 0)
    maps = {"color": rgb, "normal": normal * .5 + .5,
            "ao": np.clip(1 - ndimage.gaussian_filter(joints, 2, mode="wrap") * .45, .65, 1),
            "rough": np.clip(.57 + joints * .23 + mineral * .7 - detail * .2, .43, .83)}
    for suffix, data in maps.items():
        path = DIRECTORY / f"slate_{suffix}.png"
        Image.fromarray(np.rint(data * 255).clip(0, 255).astype(np.uint8)).save(path)
        metadata(path)


def write_materials():
    if not (DIRECTORY / "slate_color.png").exists():
        raise FileNotFoundError("Bake the generated slate source first")
    path = K.ASSETS / MATERIAL
    # Existing UVs cover 96 inches; the scan covers two metres, eight slates wide.
    K.write_text(path, f'''// Tools/lowtide_roofs.py: generated slate at physical scale.
"Layer0"
{{
    shader "shaders/hc1_slate.shader"
    TextureColor "{RESOURCE}/slate_color.png"
    TextureNormal "{RESOURCE}/slate_normal.png"
    TextureRoughness "{RESOURCE}/slate_rough.png"
    TextureAmbientOcclusion "{RESOURCE}/slate_ao.png"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vSlateScale "[1.2192 1.2192]"
    g_flTintColor "[0.40 0.44 0.48]"
    g_flSlateWeathering "0.7"
}}
''')
    metadata(path)


def configure(model):
    if "slate" in model.polygons:
        model.material_overrides["slate"] = MATERIAL
        model.tile_overrides["slate"] = 96.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.source:
        bake(args.source)
    write_materials()
    print("Slate maps ready; apply the scoped material remap through the editor")


if __name__ == "__main__":
    main()
