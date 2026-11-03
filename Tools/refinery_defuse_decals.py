"""Bring back Refinery's Defuse wall markings: its 24 DecalRenderers, which no longer draw, become Decals.

DecalRenderer is an empty obsolete class in s&box, and the scene lost its materials when it was last saved. The art
for each object comes from Facepunch/sbox-hc1 at 8e422543d2, the last commit that recorded it. Many of the old names
were wrong, so the objects are renamed for what they show.

Run once (or safely again) from anywhere. It only writes Assets/decals/refinery/ and the 24 objects in the scene.
See docs/notes/068-maps.md.
"""
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "Assets/scenes/maps/Refinery/Refinery.scene"
DECALS = ROOT / "Assets/decals/refinery"

# Art: (source colour map, the definition's width and height in world units).
ART = {
    "sign_a": ("materials/decals/decal_bombsite_a_color.png", 64, 64),
    "sign_b": ("materials/decals/decal_bombsite_b_color.png", 64, 64),
    "arrow": ("materials/decals/decal_arrow_color.png", 64, 32),
    "cross": ("materials/decals/decal_cross_color.png", 64, 64),
}

# Object guid: (art, new name). An arrow's letter is the site it points to.
OBJECTS = {
    "c3cabca4-7200-4340-ae9e-3fc10780db2b": ("arrow", "decal_arrow_b_1"),
    "786a0821-472d-4567-80da-2600783b5f84": ("sign_b", "decal_sign_b_1"),
    "252ddb30-2f5d-47b3-87bd-f8608b6ca2c4": ("cross", "decal_cross_b"),
    "7e7b2f05-7f3e-4dfa-be16-26739eaae1a8": ("arrow", "decal_arrow_a_1"),
    "a3ed7fa3-a8d0-4c14-ab42-f15e4d5fc871": ("sign_a", "decal_sign_a_1"),
    "ccc7396d-31bc-48ca-931b-c3f6ffc20b7d": ("sign_b", "decal_sign_b_2"),
    "b1c8bcd4-10a6-4206-9496-9c2c0a62710a": ("sign_b", "decal_sign_b_3"),
    "3010c6af-fbf3-4249-b2f5-1337d9583e89": ("sign_b", "decal_sign_b_4"),
    "5f44e9c4-953d-40d7-834b-49b66a2691d4": ("sign_b", "decal_sign_b_5"),
    "7fc1f261-bcba-4036-ae95-43ad34fb51b8": ("arrow", "decal_arrow_a_2"),
    "d679663d-4140-4ed5-aa49-346814bdc9a5": ("arrow", "decal_arrow_b_2"),
    "87a3b0c8-8176-4194-a69f-88ed7e180817": ("arrow", "decal_arrow_b_3"),
    "b94fcaa5-4e76-4166-9a79-21198fa8c5ec": ("arrow", "decal_arrow_b_4"),
    "61b22507-3018-429e-82e8-36555c63884f": ("arrow", "decal_arrow_b_5"),
    "175efc49-42ef-4788-977f-4d568e819ef4": ("arrow", "decal_arrow_a_3"),
    "5bb45f65-acc3-4999-b16d-6801e1495372": ("arrow", "decal_arrow_a_4"),
    "8475930d-054f-434b-96a4-bda2af7360ca": ("arrow", "decal_arrow_a_5"),
    "299a05ae-74c4-49ec-986b-52a267a872bf": ("sign_a", "decal_sign_a_2"),
    "7e1ceca5-782b-4776-939a-123ee5a0477c": ("sign_a", "decal_sign_a_3"),
    "184b7812-aa36-4eda-9334-464450046715": ("sign_a", "decal_sign_a_4"),
    "848fb04f-4388-41fb-af6d-0653ca335057": ("sign_a", "decal_sign_a_5"),
    "3063b9f8-c36b-4cd0-acf7-37d623ce2ac9": ("arrow", "decal_arrow_a_6"),
    "cd0b6719-6c73-4956-a41c-debeafd91cd2": ("arrow", "decal_arrow_a_7"),
    "bbcef1a8-93dd-4a5e-b328-0846f06e73ed": ("cross", "decal_cross_a"),
}

# The old renderer drew its art turned half a turn from Decal's (UV = 0.5 - yz in Decals.hlsl): at these rotations
# the signs would be upside down and every arrow would point away from its site. Decal's default is a random 0-360.
ROLL = 180

# The old 5-unit box is too thin to be sure of reaching the wall: Decal's box is centred on the object.
MIN_DEPTH = 16


def write_definitions():
    DECALS.mkdir(parents=True, exist_ok=True)
    for art, (source, width, height) in ART.items():
        definition = {
            "ColorTexture": {
                "$compiler": "texture",
                "$source": "imagefile",
                "data": {
                    "FilePath": source,
                    "MaxSize": 4096,
                    "ConvertHeightToNormals": False,
                    "NormalScale": 1,
                    "Rotate": 0,
                    "FlipVertical": False,
                    "FlipHorizontal": False,
                    "Padding": {"Size": "0,0", "EdgeSize": "0,0"},
                    "Sharpen": 0,
                    "InvertColor": False,
                    "Blur": 0,
                    "Brightness": 1,
                    "Contrast": 1,
                    "Saturation": 1,
                    "Hue": 0,
                    "Colorize": False,
                    "TargetColor": "0,1,0,1",
                    "CacheToDisk": True,
                },
                "compiled": None,
            },
            "NormalTexture": None,
            "RoughMetalOcclusionTexture": None,
            "HeightTexture": None,
            "ParallaxStrength": 0,
            "Tint": "1,1,1,1",
            "ColorMix": 1,
            "Width": width,
            "Height": height,
            "__references": [],
            "__version": 0,
        }
        (DECALS / f"{art}.decal").write_text(json.dumps(definition, indent=2), encoding="utf-8", newline="\n")
        guid = uuid.uuid5(uuid.NAMESPACE_URL, f"hc1/decals/refinery/{art}.decal")
        (DECALS / f"{art}.decal.meta").write_text(json.dumps({"guid": str(guid)}, indent=2), encoding="utf-8", newline="\n")


def find_decal_renderers(node, found):
    if isinstance(node, dict):
        for component in node.get("Components") or []:
            if component.get("__type") == "Sandbox.DecalRenderer":
                found[node["__guid"]] = component
        for value in node.values():
            find_decal_renderers(value, found)
    elif isinstance(node, list):
        for value in node:
            find_decal_renderers(value, found)


def decal_lines(component, art, indent):
    width, height, depth = (float(x) for x in component["Size"].split(","))
    _, art_width, art_height = ART[art]
    lines = [
        '"__type": "Sandbox.Decal",',
        f'"__guid": "{component["__guid"]}",',
        '"__enabled": true,',
        '"Flags": 0,',
        '"__version": 3,',
        '"AttenuationAngle": 1,',
        '"ColorMix": 1,',
        '"ColorTint": "1,1,1,1",',
        '"CoverageAmount": 1,',
        '"CoverageFadeIn": 0,',
        '"CoverageRange": 0.07,',
        '"Decals": [',
        f'  "decals/refinery/{art}.decal"',
        '],',
        f'"Depth": {max(depth, MIN_DEPTH):g},',
        '"LifeTime": 0,',
        '"Looped": false,',
        '"OnComponentDestroy": null,',
        '"OnComponentDisabled": null,',
        '"OnComponentEnabled": null,',
        '"OnComponentFixedUpdate": null,',
        '"OnComponentStart": null,',
        '"OnComponentUpdate": null,',
        '"Parallax": 1,',
        f'"Rotation": {ROLL},',
        '"Scale": 1,',
        '"SequenceId": 0,',
        '"SheetSequence": false,',
        f'"Size": "{width / art_width:g},{height / art_height:g}",',
        '"SortLayer": 0,',
        '"Transient": false',
    ]
    return [indent + line for line in lines]


def index_of(lines, text, start=0):
    for i in range(start, len(lines)):
        if text in lines[i]:
            return i
    raise SystemExit(f"Not in the scene: {text}")


def convert_scene():
    raw = SCENE.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    found = {}
    find_decal_renderers(json.loads(raw), found)
    if not found:
        print("Nothing to convert: the scene has no DecalRenderers.")
        return
    if set(found) != set(OBJECTS):
        raise SystemExit(f"Expected these {len(OBJECTS)} objects, found {len(found)}: {sorted(set(found) ^ set(OBJECTS))}")

    lines = raw.split(newline)
    for guid, component in found.items():
        art, name = OBJECTS[guid]

        at = index_of(lines, f'"__guid": "{component["__guid"]}"')
        first = at - 1
        while '"__type"' not in lines[first]:
            first -= 1
        indent = re.match(r"\s*", lines[first]).group()
        last = at
        while lines[last + 1].strip() not in ("}", "},") or not lines[last + 1].startswith(indent[:-2] + "}"):
            last += 1
        lines[first : last + 1] = decal_lines(component, art, indent)

        at = index_of(lines, f'"Name": ', index_of(lines, f'"__guid": "{guid}"'))
        lines[at] = re.sub(r'"Name": ".*"', f'"Name": "{name}"', lines[at])

    SCENE.write_bytes(newline.join(lines).encode("utf-8"))
    print(f"Converted {len(found)} decals.")


if __name__ == "__main__":
    write_definitions()
    convert_scene()
