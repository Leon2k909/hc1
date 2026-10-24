"""Belltower's photographed material definitions, staged for import through the editor.

Photographed textures remain original CC0 sources. Generated limestone and ivy
provenance is recorded in Sources/Belltower/wall-v3/generation.json. UV scales
convert existing mesh UVs to surface dimensions. Old procedural generators
delegate these definitions so rebuilding retains the current finish.
"""
from pathlib import Path
import argparse
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


def scanned_relief(ident, scale, depth, tint=(1, 1, 1), roughness=1):
    properties = {key: value for key, value in scan(ident, scale).items() if key.startswith("Texture")}
    properties.update({
        "shader": "shaders/belltower_relief.shader",
        "TextureHeight": f"{SCAN}/{ident}_displacement_4k.png",
        "g_vStoneUvScale": f"[{scale:.5f} {scale:.5f}]",
        "g_flTintColor": "[" + " ".join(map(str, tint)) + "]",
        "g_flReliefDepth": depth,
        "g_flStoneRoughness": roughness,
    })
    return properties


def scanned_plaster(tint, coverage=.24):
    properties = {key: value for key, value in scan("painted_plaster_wall", 1).items()
                  if key.startswith("Texture")}
    properties.update({
        "shader": "shaders/belltower_plaster.shader",
        "TextureWearColor": f"{SCAN}/rough_plaster_broken_diffuse_4k.png",
        "TextureWearNormal": f"{SCAN}/rough_plaster_broken_nor_gl_4k.png",
        "TextureWearRoughness": f"{SCAN}/rough_plaster_broken_rough_4k.png",
        "TextureWearAo": f"{SCAN}/rough_plaster_broken_ao_4k.png",
        "TextureWearHeight": f"{SCAN}/rough_plaster_broken_displacement_4k.png",
        "g_vPlasterUvScale": "[6.5024 6.5024]",
        "g_vWearUvScale": "[8.66987 8.66987]",
        "g_flTintColor": "[" + " ".join(f"{x*1.35:.5f}" for x in tint) + "]",
        "g_flWearCoverage": coverage,
        "g_flWearBrightness": 2.3,
    })
    return properties


def definitions():
    result = {
        "ashlar": scan("medieval_blocks_03", 1.4, (1.45, 1.42, 1.35)),
        "ashlar_grey": scan("medieval_blocks_03", 1.4, (1.17, 1.23, 1.29)),
        # ImageGen's irregular limestone pattern and matching height supply the
        # broad stone faces and recessed joints. The source pixels are retained.
        "rubble": {
            "shader": "shaders/belltower_masonry_v3.shader",
            "TextureStoneColor": "materials/belltower/generated/wall-limestone-v3-color.png",
            "TextureStoneHeight": "materials/belltower/generated/wall-limestone-v3-height.png",
            "TextureStoneSeams": "materials/belltower/generated/wall-limestone-v3-quilt.png",
            "g_vMasonryUvScale": "[.677333 .677333]",
            "g_vMasonryQuiltShift": "[.37001595 .42982456]",
            "g_vMasonryTint": "[1.04 1.0 .90]",
            "g_flMasonryDepth": .65,
            "g_flMasonryNormal": .65,
            "g_flMasonrySaturation": .72,
            "g_flMasonryContrast": 1.04,
            "g_flMasonryWeather": .12,
        },
        "ivy_climb": {
            "shader": "shaders/belltower_plants.shader",
            "TexturePlants": "materials/belltower/generated/ivy-climb-v3.png",
            "F_ALPHA_TEST": 1,
            "g_flAlphaTestReference": .4,
            "g_flAntiAliasedEdgeStrength": 1,
        },
        **{f"plaster_{name}": scanned_plaster(tint)
           for name, tint in PAINTS.items()},
        "roof_tiles": scan("clay_roof_tiles", 1, (1.0,1.0,1.0), .85),
        "plaster_interior": scan("painted_plaster_wall",128/(2000/25.4),(1.35,1.32,1.24),.8),
        "wood_planks": scan("brown_planks_03",48/(1000/25.4),(1.08,.97,.82),.8),
        "wood_planks_dark": scan("brown_planks_03",48/(1000/25.4),(.83,.73,.60),.8),
        "furniture_wood": scan("brown_planks_03",1,(1.08,.97,.82),.8),
        "furniture_wood_dark": scan("brown_planks_03",1,(.83,.73,.60),.8),
        **{name: {
            **scan("brown_planks_03",1,tint),
            "shader": "shaders/belltower_door_wood_v1.shader",
            "g_flDoorNormal": .16,
            "g_flDoorRoughnessScale": .68,
            "g_flDoorAo": .18,
        } for name,tint in (("door_b",(.78,.65,.50)),("door_e",(1.18,.95,.72)))},
    }
    # The original ripple normal supplies imperfect glass, while the bright
    # painted pane is replaced by genuine transparent glass and a separate bulb.
    result["lantern_glass"] = {
        "shader": "shaders/glass.shader",
        "F_GLASS_QUALITY": 2,
        "F_RENDER_BACKFACES": 1,
        "TextureColor": "materials/buildings/glass_clear_color.png",
        "TextureNormal": "materials/belltower/lantern_glass_normal.png",
        "TextureRoughness": "materials/buildings/glass_clear_rough.png",
        "g_flTintColor": "[0.96 0.92 0.82]",
        "g_flBlurAmount": .04,
        "g_flRefractionStrength": 1.003,
        "AlbedoAbsorption": .2,
    }
    for name, brightness in (("lamp_bulb",1.4),("lamp_reflector",0)):
        result[name] = {
            "F_SPECULAR": 1,
            **{f"Texture{channel}":f"materials/belltower/{name}_{suffix}.png" for channel,suffix in
               (("Color","color"),("Normal","normal"),("Roughness","rough"),("AmbientOcclusion","ao"))},
            "g_flRoughnessScaleFactor": .8,
            "g_flMetalness": 0,
            "g_vColorTint": "[1 .94 .80 1]",
        }
        if brightness:
            result[name].update({"F_SELF_ILLUM":1,"TextureSelfIllumMask":f"materials/belltower/{name}_illum.png",
                                "g_flSelfIllumBrightness":brightness,"g_flSelfIllumAlbedoFactor":1,
                                "g_vSelfIllumTint":"[1 .82 .55 0]"})
    result["street_cobbles"] = {
        "shader": "shaders/belltower_relief.shader",
        "TextureColor": "materials/stone/cobble_stones_tight_basecolor.png",
        "TextureNormal": "materials/stone/cobble_stones_tight_normal.png",
        "TextureRoughness": "materials/stone/cobble_stones_tight_roughness.png",
        "TextureAmbientOcclusion": "materials/stone/cobble_stones_tight_ambientocclusion.png",
        "TextureHeight": "materials/stone/cobble_stones_tight_height.png",
        # 256-inch UV tile, two-metre surface: approximately 12 x 25 cm setts.
        "g_vStoneUvScale": "[3.2512 3.2512]",
        "g_flTintColor": "[0.92 0.93 0.92]",
        "g_flReliefDepth": .6,
        "g_flStoneRoughness": .85,
        # The source's dark joints should read as dry mortar in this afternoon scene.
        "g_flStoneRoughnessMin": .7,
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
    from belltower_shop_displays_v2 import glass_properties
    for k in "abc":
        result[f"shopfront_{k}"] = glass_properties()
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
    provenance = "Sources/Belltower/wall-v3/generation.json" if name in ("rubble", "ivy_climb") else "Sources/Belltower/scans/manifest.json"
    lines = [f"// Tools/belltower_quality_materials.py; sources: {provenance}",
             '"Layer0"', "{", f'    shader "{properties.get("shader", "shaders/complex.shader")}"']
    lines += [f'    {key} "{value}"' for key, value in properties.items() if key != "shader"]
    return "\n".join(lines + ["}", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=sorted(definitions()), help="Stage only these materials.")
    args = parser.parse_args()
    staged = []
    for name in args.only or definitions():
        text = material_text(name, staged=True)
        if text is None:
            raise RuntimeError(f"Missing source maps for {name}; run belltower_quality_sources.py first")
        staged.append({"path": f"materials/belltower/{name}.vmat", "text": text})
    if not args.only:
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
