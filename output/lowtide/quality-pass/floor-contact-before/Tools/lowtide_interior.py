"""Warehouse concrete and enamel pendants, preserving existing light positions."""
import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K
from lowtide_brick import metadata

DIRECTORY = K.ASSETS / "materials/lowtide/interior"
RESOURCE = "materials/lowtide/interior"
SOURCE = K.ROOT / "Sources/Lowtide/visual-target/concrete-source.png"
MATERIAL = f"{RESOURCE}/lt_concrete.vmat"
CEILING_MATERIAL = f"{RESOURCE}/lt_ceiling.vmat"


def bake(source):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() != SOURCE.resolve():
        shutil.copy2(source, SOURCE)
    rgb = np.asarray(Image.open(SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), float) / 255
    lum = rgb @ np.array([.2126, .7152, .0722])
    detail = lum - ndimage.gaussian_filter(lum, 5, mode="wrap")
    pits = np.clip((-detail - .045) * 6, 0, 1)
    # Technical map derivation only; the generated albedo remains unchanged.
    # Troweled cement has shallow aggregate and sub-millimetre pits.
    height = ndimage.gaussian_filter(detail, .7, mode="wrap") * .0012 - pits * .0006
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 512
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 512
    normal = np.stack([-dx, dy, np.ones_like(lum)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    maps = {"color": rgb, "normal": normal * .5 + .5,
            "rough": np.clip(.61 + pits * .23 - detail * .35, .46, .88)}
    for suffix, data in maps.items():
        path = DIRECTORY / f"concrete_{suffix}.png"
        Image.fromarray(np.rint(data * 255).clip(0, 255).astype(np.uint8)).save(path)
        metadata(path)


def bake_ceiling(source):
    target = SOURCE.with_name("ceiling-boards-source.png")
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() != target.resolve():
        shutil.copy2(source, target)
    rgb = np.asarray(Image.open(target).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), float) / 255
    lum = rgb @ np.array([.2126, .7152, .0722])
    detail = lum - ndimage.gaussian_filter(lum, 8, mode="wrap")
    joints = np.clip((.15 - lum) * 12, 0, 1)
    height = ndimage.gaussian_filter(detail, .8, mode="wrap") * .002 - joints * .002
    # Nine 24 cm boards across the selected image; 2.4 m along their grain.
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * (2048 / 4.32)
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * (2048 / 4.8)
    normal = np.stack([-dx, dy, np.ones_like(lum)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    maps = {"color": rgb, "normal": normal*.5+.5,
            "rough": np.clip(.72 + joints*.15 - detail*.3, .55, .91)}
    for suffix, data in maps.items():
        path = DIRECTORY / f"ceiling_{suffix}.png"
        Image.fromarray(np.rint(data * 255).clip(0, 255).astype(np.uint8)).save(path)
        metadata(path)


def write_materials():
    if not (DIRECTORY / "concrete_color.png").exists():
        raise FileNotFoundError("Bake the generated concrete source first")
    if not (DIRECTORY / "ceiling_color.png").exists():
        raise FileNotFoundError("Bake the generated ceiling source first")
    K.write_text(K.ASSETS / MATERIAL, f'''// Tools/lowtide_interior.py: two-metre concrete scan.
"Layer0"
{{
    shader "shaders/hc1_lowtide_concrete.shader"
    TextureColor "{RESOURCE}/concrete_color.png"
    TextureNormal "{RESOURCE}/concrete_normal.png"
    TextureRoughness "{RESOURCE}/concrete_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_flConcreteScale "3.2512"
}}
''')
    K.write_text(K.ASSETS / CEILING_MATERIAL, f'''// Tools/lowtide_interior.py: long pine boards at 24 cm width.
"Layer0"
{{
    shader "shaders/hc1_lowtide_timber.shader"
    TextureColor "{RESOURCE}/ceiling_color.png"
    TextureNormal "{RESOURCE}/ceiling_normal.png"
    TextureRoughness "{RESOURCE}/ceiling_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vTimberScale "[1.1288889 1.016]"
    g_vTimberTint "[.72 .67 .60]"
}}
''')
    bulb = DIRECTORY / "lt_pendant_bulb.vmat"
    K.write_text(bulb, '''// A warm opal bulb inside the enamel shade.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_SELF_ILLUM "1"
    TextureSelfIllumMask "[1 1 1 0]"
    g_flSelfIllumBrightness "1.7"
    g_flSelfIllumAlbedoFactor "1.0"
    g_vSelfIllumTint "[1 0.94 0.83 0]"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0"
    TextureColor "materials/railhead/rw_lamp_warm_color.png"
    TextureNormal "materials/railhead/lamps_normal.png"
    TextureRoughness "materials/railhead/lamps_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
}
''')
    for path in (K.ASSETS / MATERIAL, K.ASSETS / CEILING_MATERIAL, bulb,
                 K.ASSETS / "shaders/hc1_lowtide_concrete.shader", K.ASSETS / "shaders/hc1_lowtide_timber.shader"):
        metadata(path)


def configure(model):
    if "rw_concrete" in model.polygons:
        model.material_overrides["rw_concrete"] = MATERIAL
        model.tile_overrides["rw_concrete"] = 256.0
    if "lt_pendant_bulb" in model.polygons:
        model.material_overrides["lt_pendant_bulb"] = f"{RESOURCE}/lt_pendant_bulb.vmat"
    if "planks_dark" in model.polygons:
        model.material_overrides["planks_dark"] = CEILING_MATERIAL
        model.tile_overrides["planks_dark"] = 96.0


def pendant(m, L, e, n, light_z, ceiling):
    centre = (e, n)
    rim_z = light_z - 4
    # A spun metal shell with a separately wound, cream enamel interior.
    profile = [(12, 0), (11.7, .8), (9.8, 2.2), (6.0, 6.2), (3.1, 10), (2.6, 11)]
    L.lathe(m, centre, rim_z, profile, "lt_frame_green", sides=32)
    inner = [(r-.18, z-.18) for r, z in reversed(profile)]
    L.lathe(m, centre, rim_z, inner, "lt_frame_cream", sides=32)
    L.torus(m, (e, n, rim_z), (1, 0, 0), (0, 1, 0), 11.9, .27,
            "lt_frame_green", segments=32, sides=6)
    # Ceramic neck, opal bulb and a short hanging rod attached to the ceiling.
    L.lathe(m, centre, light_z, [(1.7, 6.5), (1.7, 7), (2.6, 7), (2.6, 8)], "lt_frame_cream", sides=12)
    # Keep the emitter just below the bulb's closed geometry so shadowed lights
    # are not occluded by their own luminaire.
    L.lathe(m, centre, light_z, [(0, .8), (2.5, 2), (3.2, 3.9), (2.8, 5.9), (1.7, 7.2), (0, 7.2)],
            "lt_pendant_bulb", sides=16)
    L.bar(m, (e, n, light_z+7), (e, n, ceiling-1), .42, "lt_drain_iron", sides=8)
    L.lathe(m, centre, ceiling-2, [(0, 0), (3.5, 0), (4, 1), (4, 2), (0, 2)], "lt_frame_green", sides=16)


def add_fixtures(m, L):
    for name, (e, n, z), _color, _radius, _shadow in L.lights():
        if "Warehouse" in name or "Mezzanine" in name:
            ceiling = L.FLOOR1-16 if "Ground" in name else L.CEILING
            pendant(m, L, e, n, z, ceiling)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--ceiling-source", type=Path)
    args = parser.parse_args()
    if args.source:
        bake(args.source)
    if args.ceiling_source:
        bake_ceiling(args.ceiling_source)
    write_materials()
    print("Warehouse materials ready; apply scoped model remaps through the editor")


if __name__ == "__main__":
    main()
