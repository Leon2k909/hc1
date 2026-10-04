"""
Railhead's sky: Belltower's clear afternoon with fair-weather cumulus (Tools/belltower_sky.py), baked again with
Railhead's sun into its own panorama.

    python Tools/railhead_sky.py [belltower_sky's options: --width, --seed, --out, --preview, --views-only, ...]

- The sun is where it stands over a south German city at the time the station's clocks and displays show: 14:03
  summer time on 3 October, about 12:47 solar time at 11 degrees east, 48 degrees north. That's 38 degrees up, 15
  degrees west of south. railhead_map's Sun light takes the same angles (SUN_PITCH, SUN_YAW: pitch down, and yaw round
  from x, north, towards y, west, as the light points).
- Everything else is belltower_sky's: the haze and blue by height, the cumulus field (none across the sun), how it's
  shown at the outdoor exposure. Its module globals are set before it runs: the sun, where it writes and the name.
- Writes Assets/materials/railhead/sky/railhead_sky.exr and railhead_sky.vmat.
"""
import sys
from pathlib import Path

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/railhead/sky"
RESOURCE_DIR = "materials/railhead/sky"
NAME = "railhead_sky"

SUN_PITCH, SUN_YAW = 38.0, -15.0


def main():
    import belltower_sky as S

    S.SUN_PITCH, S.SUN_YAW = SUN_PITCH, SUN_YAW
    S.OUT_DIR, S.RESOURCE_DIR, S.NAME = OUT_DIR, RESOURCE_DIR, NAME
    sys.argv[0] = __file__
    S.main()


if __name__ == "__main__":
    main()
