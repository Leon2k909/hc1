"""Belltower's photographed material definitions, staged for import through the editor.

Textures remain original CC0 sources. UV scales convert the existing generated UVs
to the photographed surface dimensions. The old procedural generators delegate
these material names here so a rebuild cannot silently restore the old finish.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SCAN = "materials/belltower/scans"
PAINTS = {
    "rose": (0.88, 0.59, 0.46),
    "terracotta": (0.79, 0.43, 0.29),
    "ochre": (0.92, 0.69, 0.39),
    "cream": (1.0, 0.92, 0.73),
    "blue": (0.57, 0.72, 0.84),
    "sage": (0.66, 0.77, 0.56),
    "pale": (0.98, 0.95, 0.85),
    "whitewash": (1.0, 0.99, 0.94),
}


def scan(ident, scale, tint=(1, 1, 1), roughness=1):
    return {
        "F_SPECULAR": 1,
        "TextureColor": f"{SCAN}/{ident}_diffuse_4k.png",
        "TextureNormal": f"{SCAN}/{ident}_nor_gl_4k.png",
        "TextureRoughness": f"{SCAN}/{ident}_rough_4k.png",
        "TextureAmbientOcclusion": f"{SCAN}/{ident}_ao_4k.png",
        "g_vTexCoordScale": f"[{scale:.5f} {scale:.5f}]",
        "g_vColorTint": "[" + " ".join(map(str, (*tint, 1))) + "]",
        "g_flRoughnessScaleFactor": roughness,
        "g_flModelTintAmount": 1,
        "g_flMetalness": 0,
    }


def definitions():
    result = {
        "ashlar": scan("medieval_blocks_03", 1.4, (1.45, 1.42, 1.35)),
        "ashlar_grey": scan("medieval_blocks_03", 1.4, (1.17, 1.23, 1.29)),
        "rubble": scan("medieval_blocks_05", 1.6, (1.12, 1.1, 1.04)),
        **{f"plaster_{name}": scan("painted_plaster_wall", 512 / (2000 / 25.4), tuple(x * 1.35 for x in tint), 0.8)
           for name, tint in PAINTS.items()},
        "roof_tiles": scan("clay_roof_tiles", 1, (1.0,1.0,1.0), .85),
        "plaster_interior": scan("painted_plaster_wall",128/(2000/25.4),(1.35,1.32,1.24),.8),
    }
    result["street_cobbles"] = {
        "F_SPECULAR": 1,
        "TextureColor": "materials/stone/cobble_stones_tight_basecolor.png",
        "TextureNormal": "materials/stone/cobble_stones_tight_normal.png",
        "TextureRoughness": "materials/belltower/cobbles_rough.png",
        "TextureAmbientOcclusion": "materials/stone/cobble_stones_tight_ambientocclusion.png",
        "g_vTexCoordScale": "[1.6 1.6]",
        "g_vColorTint": "[0.92 0.93 0.92 1]",
        "g_flRoughnessScaleFactor": 1,
        "g_flModelTintAmount": 1,
        "g_flMetalness": 0,
    }
    for k,tint in enumerate(((.63,.60,.55),(.74,.71,.64),(.86,.81,.72))):
        result[f"roof_clay_{k}"] = {
            "F_SPECULAR": 1,
            "TextureColor": "materials/buildings/clay_pot_color.png",
            "TextureNormal": f"{SCAN}/white_plaster_rough_01_nor_gl_4k.png",
            "TextureRoughness": f"{SCAN}/white_plaster_rough_01_rough_4k.png",
            "g_vColorTint": "["+" ".join(map(str,(*tint,1)))+"]",
            "g_flRoughnessScaleFactor": .7,
            "g_flMetalness": 0,
            "g_flModelTintAmount": 1,
        }
    for k in "abcd":
        result[f"window_{k}"] = {
            "shader": "shaders/belltower_window.shader",
            "TextureRoomBack": f"materials/belltower/window_{k}_color.png",
            "TextureRoomWall": f"{SCAN}/white_plaster_rough_01_diffuse_4k.png",
            "g_flRoomDepth": 34,
            "g_flInteriorBrightness": .13,
            "g_flRoughness": .16,
        }
    for k,depth,brightness in (("a",28,.25),("b",34,.29),("c",24,.23)):
        result[f"shopfront_{k}"] = {
            "shader": "shaders/belltower_window.shader",
            "TextureRoomBack": "materials/belltower/generated/shop-shelves-v1.png",
            "TextureRoomWall": f"{SCAN}/painted_plaster_wall_diffuse_4k.png",
            "g_flRoomDepth": depth,
            "g_flInteriorBrightness": brightness,
        }
    result["window_plants"] = {
        "shader": "shaders/belltower_plants.shader",
        "TexturePlants": "materials/belltower/generated/window-plants-v1.png",
        "F_ALPHA_TEST": 1,
        "g_flAlphaTestReference": .5,
        "g_flAntiAliasedEdgeStrength": 1,
    }
    return result


def material_text(name, staged=False):
    properties = definitions().get(name)
    if properties is None:
        return None
    # Standalone copies of the old generator still work until the scan sources
    # have been fetched. Imported projects have these source maps in Assets.
    def exists(value):
        if (ROOT / "Assets" / value).is_file():
            return True
        return staged and value.startswith("materials/belltower/generated/") and (ROOT / "Sources/Belltower/generated" / Path(value).name).is_file()
    if not all(exists(value) for key, value in properties.items() if key.startswith("Texture")):
        return None
    lines = ["// Tools/belltower_quality_materials.py; sources: Sources/Belltower/scans/manifest.json",
             '"Layer0"', "{", f'    shader "{properties.get("shader", "shaders/complex.shader")}"']
    lines += [f'    {key} "{value}"' for key, value in properties.items() if key != "shader"]
    return "\n".join(lines + ["}", ""])


def main():
    staged = []
    for name in definitions():
        text = material_text(name, staged=True)
        if text is None:
            raise RuntimeError(f"Missing source maps for {name}; run belltower_quality_sources.py first")
        staged.append({"path": f"materials/belltower/{name}.vmat", "text": text})
    staged.append({"path": "materials/belltower/sky/afternoon_scan.vmat", "text": '''// Poly Haven CC0; Sources/Belltower/scans/manifest.json
"Layer0"
{
    shader "shaders/sky.shader"
    F_TEXTURE_FORMAT2 6
    g_flBrightnessExposureBias 0
    g_flRenderOnlyExposureBias 0
    SkyTexture "materials/belltower/scans/kloppenheim_05_puresky_hdri_4k.exr"
}
'''})
    path = ROOT / "output/belltower/quality/material-import.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(staged, indent=2) + "\n", encoding="utf-8")
    print(f"Staged {len(staged)} materials for the native editor: {path}")


if __name__ == "__main__":
    main()
