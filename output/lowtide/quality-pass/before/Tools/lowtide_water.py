"""Write Lowtide's shallow-water material, using continuous, pixel-filtered shader waves."""

from pathlib import Path
import json
import uuid

import map_kit as K

DIRECTORY = K.ASSETS / "materials/lowtide"
MATERIAL = DIRECTORY / "lt_water.vmat"
SHADER = K.ASSETS / "shaders/hc1_lowtide_water.shader"


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
    g_vWaterColor "[0.100 0.160 0.140]"
    g_vWaterFlow "[-3.4 0.9]"
    g_flRippleTile "512"
    g_flRippleStrength "0.7"
    g_flWaterRoughness "0.20"
    g_flAbsorptionDistance "42"
    g_flBankFade "0.3"
}
''')
    metadata(MATERIAL)
    metadata(SHADER)


if __name__ == "__main__":
    write_materials()
    print(f"Wrote {MATERIAL.name}: continuous waves, screen-footprint filtering and transparent shallows")
