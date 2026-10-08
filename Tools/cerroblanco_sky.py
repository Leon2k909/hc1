"""
Cerro Blanco's sky: a cloudless, deep blue highland sky over the museum's hill, baked with Belltower's sky code
(Tools/belltower_sky.py) into its own panorama.

    python Tools/cerroblanco_sky.py [belltower_sky's options: --width, --seed, --out, --preview, --views-only, ...]

- The pictures the map is dressed after have no cloud at all, and a sky far deeper than Belltower's summer haze: the
  dry, thin air over a hill town at altitude, cobalt overhead and paling to a light blue only near the hills. So the
  cumulus are left out (no heaps, no puffs, no near ring) and the sky's colours by height are darker and bluer.
- The sun is cerroblanco_map's (SUN_PITCH, SUN_YAW), so the sky's brightening round it sits where the light comes from.
- Everything else is belltower_sky's: the haze by height, the sun's halo, how it's shown at the outdoor exposure.
- Writes Assets/materials/cerroblanco/sky/cerroblanco_sky.exr and cerroblanco_sky.vmat.
"""
import sys
from pathlib import Path

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/cerroblanco/sky"
RESOURCE_DIR = "materials/cerroblanco/sky"
NAME = "cerroblanco_sky"

SUN_PITCH, SUN_YAW = 34.0, -63.0      # cerroblanco_map's

# The sky's colour (as a match shows it) by degrees above the horizon: pale at the hills, cobalt overhead.
SKY_KEYS = ( ( 0.0, ( 176, 198, 222 ) ), ( 6.0, ( 146, 178, 216 ) ), ( 15.0, ( 106, 148, 204 ) ),
             ( 30.0, ( 70, 116, 190 ) ), ( 55.0, ( 48, 92, 174 ) ), ( 90.0, ( 38, 80, 166 ) ) )


def main():
    import belltower_sky as S

    S.SUN_PITCH, S.SUN_YAW = SUN_PITCH, SUN_YAW
    S.OUT_DIR, S.RESOURCE_DIR, S.NAME = OUT_DIR, RESOURCE_DIR, NAME
    S.SKY_KEYS = SKY_KEYS
    # No cloud: no heaps or puffs, and the near ring's heaps are never placed.
    S.HEAPS, S.PUFF_GROUPS = 0.0, 0.0
    S.heap_domes = lambda *args, **kwargs: []
    S.puff_domes = lambda *args, **kwargs: []
    # An empty dome list comes out one-dimensional, which the compiled drawing can't type: give it its columns.
    draw = S._draw_domes
    S._draw_domes = lambda domes, *args: draw( domes.reshape( 0, 5 ) if domes.size == 0 else domes, *args )
    sys.argv[0] = __file__
    S.main()


if __name__ == "__main__":
    main()
