"""
Riverdale's sky: a golden morning over the plant's mountains, the sun low over the cooling towers, baked with
Belltower's sky code (Tools/belltower_sky.py) into its own panorama.

    python Tools/riverdale_sky.py [belltower_sky's options: --width, --seed, --out, --preview, --views-only, ...]

- The reference the map is dressed after looks into a low sun: warm cream and peach at the horizon, a clear blue
  overhead, and heaped cumulus with gold edges round the sun. So the sky's colours by height run warm low and blue
  high (SKY_KEYS), the sun's light is golden (LIGHT, also riverdale_map's Sun LightColor), and there are more heaps,
  allowed nearer the sun (SUN_GAP), so some catch its rim light.
- The sun is riverdale_map's (SUN_PITCH, SUN_YAW): 12 degrees up in the east-north-east, so from the west yard the
  light comes from behind the towers, as in the reference.
- Writes Assets/materials/riverdale/sky/riverdale_sky.exr and riverdale_sky.vmat.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/riverdale/sky"
RESOURCE_DIR = "materials/riverdale/sky"
NAME = "riverdale_sky"

SUN_PITCH, SUN_YAW = 12.0, 125.0      # riverdale_map's
LIGHT = np.array( ( 1.55, 1.02, 0.58 ) )

SKY_KEYS = ( ( 0.0, ( 240, 214, 182 ) ), ( 5.0, ( 226, 208, 190 ) ), ( 12.0, ( 196, 200, 208 ) ),
             ( 24.0, ( 156, 180, 212 ) ), ( 45.0, ( 120, 154, 204 ) ), ( 90.0, ( 98, 136, 194 ) ) )


def main():
    import belltower_sky as S

    S.SUN_PITCH, S.SUN_YAW = SUN_PITCH, SUN_YAW
    S.OUT_DIR, S.RESOURCE_DIR, S.NAME = OUT_DIR, RESOURCE_DIR, NAME
    S.SKY_KEYS = SKY_KEYS
    S.LIGHT = LIGHT
    S.CLOUD_SUN = LIGHT * 1.25
    S.HALO_WHITE = np.array( ( 1.16, 1.0, 0.76 ) )
    S.GROUND = np.array( ( 0.20, 0.18, 0.15 ) )
    S.AMB_HIGH = np.array( ( 0.17, 0.28, 0.58 ) )
    S.AMB_LOW = np.array( ( 0.34, 0.28, 0.24 ) )
    S.HEAPS = 0.16
    S.SUN_GAP = 700.0
    S.NEAR_SIZE = ( 900.0, 0.35, 550.0, 1400.0 )
    sys.argv[0] = __file__
    S.main()


if __name__ == "__main__":
    main()
