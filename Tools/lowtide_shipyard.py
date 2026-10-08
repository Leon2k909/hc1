"""Photographic, alpha-masked far shore for Lowtide; no gameplay geometry or billboarding.

The source panoramas are generated with the built-in image tool from the user's shipyard reference.
Colour and opacity are packed into separate engine textures without modifying the generated artwork.
The outer panorama supplies distinct peripheral docks rather than repeating the central gantry cranes.
"""
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K

MAT_DIR = K.ASSETS / "materials/lowtide/shipyard"
RESOURCE_DIR = "materials/lowtide/shipyard"
PAINTS = ("lt_shipyard_panorama", "lt_shipyard_peripheral")
SHORE_N = -11000.0
HALF_WIDTH = 9000.0
WING_END = 18000.0
PERIPHERAL_WIDTH = 18000.0
JOIN_OVERLAP = 350.0
OUTER_PANELS = 4
SHORE_EXTENT = WING_END + OUTER_PANELS * (PERIPHERAL_WIDTH - JOIN_OVERLAP)
WATER_Z = -150.0
# The UV foot is inside the fully opaque quay, so there is no transparent strip at the waterline.
FOOT_ROWS = {"lt_shipyard_panorama": 680, "lt_shipyard_peripheral": 650}
SOURCE_SIZE = (2172, 724)
ATLAS_SIZE = (4096, 1024)


def prepare(sources):
    """Keep the original pixels inside a power-of-two atlas required by the native mip compiler."""
    MAT_DIR.mkdir(parents=True, exist_ok=True)
    for paint, source in zip(PAINTS, sources):
        target = MAT_DIR / f"{paint}.png"
        source = Path(source)
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        with Image.open(target) as image:
            if image.mode != "RGBA" or image.size != SOURCE_SIZE:
                raise ValueError(f"Unexpected source for {paint}: {image.mode}, {image.size}")
            # Padding, rather than resizing, keeps every generated pixel and the crane cutout intact.
            atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
            atlas.paste(image, (0, 0))
            atlas.convert("RGB").save(MAT_DIR / f"{paint}_color.png")
            atlas.getchannel("A").save(MAT_DIR / f"{paint}_alpha.png")
    write_materials()


def write_materials():
    for paint in PAINTS:
        if not (MAT_DIR / f"{paint}_color.png").exists():
            raise FileNotFoundError(f"Shipyard source asset is missing: {paint}")
        text = f'''// Tools/lowtide_shipyard.py: baked-light distant shipyard, original generated alpha.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_ALPHA_TEST "1"
    F_SELF_ILLUM "1"
    TextureColor "{RESOURCE_DIR}/{paint}_color.png"
    TextureTranslucency "{RESOURCE_DIR}/{paint}_alpha.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureRoughness "[1 1 1 0]"
    TextureSelfIllumMask "materials/default/default_color.tga"
    g_flAlphaTestReference "0.5"
    g_flAntiAliasedEdgeStrength "1"
    g_flSelfIllumBrightness "0.22"
    g_flSelfIllumAlbedoFactor "1"
    g_flMetalness "0"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
}}
'''
        K.write_text(MAT_DIR / f"{paint}.vmat", text)


def configure(model):
    for paint in PAINTS:
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE_DIR}/{paint}.vmat"
            model.tile_overrides[paint] = 1.0


def _panel(model, paint, e0, e1, n, u0, u1):
    foot = FOOT_ROWS[paint] / SOURCE_SIZE[1]
    # One texture pixel has the same physical size across the adjoining cards. OBJ UV v runs upwards.
    raw_height = abs(e1 - e0) / abs(u1 - u0) / (SOURCE_SIZE[0] / SOURCE_SIZE[1])
    z0, z1 = WATER_Z - 6.0, WATER_Z - 6.0 + raw_height * foot
    points = [(e0, n, z0), (e1, n, z0), (e1, n, z1), (e0, n, z1)]
    atlas_u = SOURCE_SIZE[0] / ATLAS_SIZE[0]
    atlas_foot = FOOT_ROWS[paint] / ATLAS_SIZE[1]
    # Looking south across the harbour, plan e increases toward screen-left.
    # Reverse u so the main gantry and hull keep the reference's right-hand placement.
    uv = [((1 - u0) * atlas_u, 1 - atlas_foot), ((1 - u1) * atlas_u, 1 - atlas_foot),
          ((1 - u1) * atlas_u, 1), ((1 - u0) * atlas_u, 1)]
    # Reverse the winding to look north, toward the playable quay.
    model.polygon(paint, points[::-1], normal=(0, 1, 0), uv=uv[::-1])


def build(model):
    """Fixed shore cards, with low outer docks continuing beyond the oblique views from the quay."""
    _panel(model, PAINTS[0], -HALF_WIDTH, HALF_WIDTH, SHORE_N, 0, 1)
    _panel(model, PAINTS[1], -WING_END, -8650, SHORE_N - 110, 0, .52)
    _panel(model, PAINTS[1], 8650, WING_END, SHORE_N - 110, .48, 1)
    # The main view has unique gantry cranes. The lower peripheral docks continue at the same pixel scale,
    # behind overlapping foreground sections, until their ends are hidden by the playable boundary buildings.
    for index in range(OUTER_PANELS):
        near = WING_END - JOIN_OVERLAP + index * (PERIPHERAL_WIDTH - JOIN_OVERLAP)
        far = near + PERIPHERAL_WIDTH
        n = SHORE_N - 220 - index * 110
        _panel(model, PAINTS[1], -far, -near, n, 0, 1)
        _panel(model, PAINTS[1], near, far, n, 0, 1)
    configure(model)


def validate():
    """Asset transparency, uninterrupted opaque quay, and view coverage at the gameplay extremities."""
    report = []
    for paint in PAINTS:
        with Image.open(MAT_DIR / f"{paint}.png") as image:
            rgba = np.asarray(image)
        alpha = np.asarray(Image.open(MAT_DIR / f"{paint}_alpha.png"))
        colour = np.asarray(Image.open(MAT_DIR / f"{paint}_color.png"))
        h, w = rgba.shape[:2]
        assert alpha.shape == ATLAS_SIZE[::-1], "Native textures must use power-of-two dimensions"
        assert colour.shape[:2] == alpha.shape, "Packed colour and alpha must use the same atlas dimensions"
        assert np.array_equal(alpha[:h, :w], rgba[:, :, 3]), "Opacity must preserve the original generated alpha"
        assert np.array_equal(colour[:h, :w], rgba[:, :, :3]), "Colour packing must not alter the generated image"
        assert not alpha[h:, :].any() and not alpha[:, w:].any(), "Atlas padding must remain transparent"
        assert (alpha[FOOT_ROWS[paint], :w] >= 178).mean() > .999, "The visible quay foot must be opaque across its width"
        assert alpha[:100].max() < 128, "Sky margin must be transparent"
        report.append(f"PASS: {paint}: {w}x{h} in {ATLAS_SIZE[0]}x{ATLAS_SIZE[1]} atlas, original colour/alpha preserved, opaque waterline, transparent sky")
    for e in (-2200, 0, 2200):
        for n in (-1650, 1450):
            outer_n = SHORE_N - 220 - (OUTER_PANELS - 1) * 110
            left = math.degrees(math.atan2(-SHORE_EXTENT - e, n - outer_n))
            right = math.degrees(math.atan2(SHORE_EXTENT - e, n - outer_n))
            assert left < -80 and right > 80, "Shore ends must stay outside a 160-degree harbour view throughout the play area"
            report.append(f"PASS: shore coverage from plan ({e}, {n}): {left:.1f}..{right:.1f} degrees")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs=2, metavar=("CENTRAL", "PERIPHERAL"))
    args = parser.parse_args()
    if args.sources:
        prepare(args.sources)
    print("\n".join(validate()))
