"""Enamel and thin glazing for Lowtide's existing warehouse windows.

Only material assets are replaced. Existing geometry, UVs and collision remain.
"""
import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K
from lowtide_brick import metadata

DIRECTORY = K.ASSETS / "materials/lowtide/frames"
RESOURCE = "materials/lowtide/frames"
SOURCE = K.ROOT / "Sources/Lowtide/visual-target/frame-enamel-source.png"


def bake(source):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() != SOURCE.resolve():
        shutil.copy2(source, SOURCE)
    rgb = np.asarray(Image.open(SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), float) / 255
    lum = rgb @ np.array([.2126, .7152, .0722])
    detail = lum - ndimage.gaussian_filter(lum, 8, mode="wrap")
    chips = np.clip((ndimage.gaussian_filter(lum, 5, mode="wrap") - lum - .025) * 12, 0, 1)
    # Paint chips are fractions of a millimetre deep, never hammered concrete.
    height = ndimage.gaussian_filter(detail, .8, mode="wrap") * .00024 - chips * .00030
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 1024
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 1024
    normal = np.stack([-dx, dy, np.ones_like(lum)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    maps = {"color": rgb, "normal": normal * .5 + .5,
            "rough": np.clip(.43 + chips * .26 - detail * .15, .34, .79)}
    for suffix, data in maps.items():
        path = DIRECTORY / f"enamel_{suffix}.png"
        Image.fromarray(np.rint(data * 255).clip(0, 255).astype(np.uint8)).save(path)
        metadata(path)


def write_materials():
    if not (DIRECTORY / "enamel_color.png").exists():
        raise FileNotFoundError("Bake the generated enamel source before writing frame materials")
    for name, tint in (("green", ".065 .115 .082"), ("cream", ".47 .43 .35")):
        path = K.ASSETS / f"materials/lowtide/lt_frame_{name}.vmat"
        K.write_text(path, f'''// Tools/lowtide_frames.py: generated enamel with physical surface scale.
"Layer0"
{{
    shader "shaders/hc1_lowtide_enamel.shader"
    TextureColor "{RESOURCE}/enamel_color.png"
    TextureNormal "{RESOURCE}/enamel_normal.png"
    TextureRoughness "{RESOURCE}/enamel_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vEnamelTint "[{tint}]"
    g_flEnamelScale "5.08"
}}
''')
        metadata(path)
    metadata(K.ASSETS / "shaders/hc1_lowtide_enamel.shader")
    glass = K.ASSETS / "materials/lowtide/lt_glass.vmat"
    K.write_text(glass, '''// Lowtide's thin, slightly wavy warehouse glazing.
"Layer0"
{
    shader "shaders/glass.shader"
    F_GLASS_QUALITY "2"
    g_bFogEnabled "1"
    g_flBlurAmount "0.12"
    g_flRefractionStrength "1.0015"
    AlbedoAbsorption "0.08"
    g_flTintColor "[1 1 1]"
    TextureColor "[0.97 0.985 0.98 0]"
    TextureNormal "materials/railhead/window_dark_normal.png"
    TextureRoughness "[0.10 0.10 0.10 0]"
    TextureMetalness "[0 0 0 0]"
    TextureAmbientOcclusion "[1 1 1 0]"
    TextureBlendMask "materials/default/default_blend.tga"
    TextureTintMask "materials/default/default.tga"
    TextureTranslucency "materials/default/default_trans.tga"
}
''')
    metadata(glass)


def configure(model):
    if "rw_glass" in model.polygons:
        model.material_overrides["rw_glass"] = "materials/lowtide/lt_glass.vmat"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.source:
        bake(args.source)
    write_materials()
    print("Windows: generated enamel and thin glazing; no geometry changes")


if __name__ == "__main__":
    main()
