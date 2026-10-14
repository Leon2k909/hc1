"""Write Lowtide's shallow-water material, using continuous, pixel-filtered shader waves."""

from pathlib import Path
import json
import uuid

import map_kit as K

DIRECTORY = K.ASSETS / "materials/lowtide"
MATERIAL = DIRECTORY / "lt_water.vmat"
SHADER = K.ASSETS / "shaders/hc1_lowtide_water.shader"


def reflection_component(ids, key):
    return K.component(ids, "Facepunch.LowtideWaterReflections", f"{key}/reflections",
                       WaterHeight=-137, MaximumWidth=960)


def apply_scene(scene, L):
    water = next(o for o in next(o for o in scene["GameObjects"] if o.get("Name") == "Lowtide")["Children"]
                 if o.get("Name") == "Water")
    water["Components"][:] = [c for c in water["Components"] if c["__type"] != "Facepunch.LowtideWaterReflections"]
    water["Components"].append(reflection_component(L.ids, "world/lowtide_water"))


def metadata(path):
    sidecar = Path(str(path) + ".meta")
    if not sidecar.exists():
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid4())}, indent=2) + "\n")


def write_materials():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    K.write_text(MATERIAL, '''// Tools/lowtide_water.py: filtered continuous waves and depth-based absorption.
"Layer0"
{
    shader "shaders/hc1_lowtide_water.shader"
    g_vWaterColor "[0.014 0.022 0.018]"
    g_vWaterFlow "[-2.1 0.65]"
    g_flRippleTile "48"
    g_flRippleStrength "0.8"
    g_flWaterRoughness "0.10"
    g_flAbsorptionDistance "18"
    g_flBankFade "0.3"
}
''')
    metadata(MATERIAL)
    metadata(SHADER)


if __name__ == "__main__":
    write_materials()
    print(f"Wrote {MATERIAL.name}: continuous waves, screen-footprint filtering and transparent shallows")
