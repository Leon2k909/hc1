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
- Railhead's own cloud tweaks (2026-10-16): the layer's base raised to 2100 m and softened (BASE_FADE 120 m), the near
  "composed" heaps half the size and further out, and no heap nearer than VISTA_CLEAR (7 km) within 30 degrees of the
  cab roads' axis either way (north and south), so no low, sharp-based blob hangs over the streets' far ends; the heaps
  over the hills either side stay.
- Round 2 (2026-10-16): a thin high cirrus veil (three combed streaks 14-20 degrees long at 40-52 degrees up, at most 20% opaque,
  CIRRUS) and a paler haze band along the horizon (HAZE_BAND), drawn into the cloudless sky's base at twice its old
  resolution; the cumulus are unchanged.
- Writes Assets/materials/railhead/sky/railhead_sky.exr and railhead_sky.vmat (--out DIR to write elsewhere, e.g. a stage's
  materials/railhead/sky).
"""
import sys
from pathlib import Path

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/railhead/sky"
RESOURCE_DIR = "materials/railhead/sky"
NAME = "railhead_sky"

SUN_PITCH, SUN_YAW = 38.0, -15.0
BASE, TOP = 2100.0, 3300.0
BASE_FADE = 120.0
NEAR_RING = ( 4500.0, 8500.0 )
NEAR_SIZE = ( 300.0, 0.3, 220.0, 420.0 )
VISTA_CLEAR = 7000.0                    # metres
VISTA_HALF = 30.0                       # degrees either side of the line's axis
# Round 2: a 3 October afternoon's high cirrus veil and its paler horizon (2026-10-16)
CIRRUS = ( ( -25.0, 40.0, 24.0, 20.0 ), ( 205.0, 46.0, -32.0, 17.0 ), ( 40.0, 52.0, 10.0, 14.0 ) )   # azimuth (from north towards west), elevation,
                                                                        # the streak's slant and its length, degrees
CIRRUS_OPACITY = 0.2
HAZE_BAND = ( 0.32, 4.0 )               # the horizon's whitening: its share at the horizon, and its e-folding degrees


def main():
    import belltower_sky as S

    S.SUN_PITCH, S.SUN_YAW = SUN_PITCH, SUN_YAW
    S.BASE, S.TOP = BASE, TOP
    S.BASE_FADE = BASE_FADE
    S.NEAR_RING, S.NEAR_SIZE = NEAR_RING, NEAR_SIZE
    S.OUT_DIR, S.RESOURCE_DIR, S.NAME = OUT_DIR, RESOURCE_DIR, NAME
    import math
    heap = S.heap_domes

    def clear_of_vistas( rng, x, y, *rest, **kw ):
        d = math.hypot( x, y )
        off_axis = math.degrees( math.atan2( abs( y ), abs( x ) ) )
        if d < VISTA_CLEAR and off_axis < VISTA_HALF:
            heap( rng, x, y, *rest, **kw )      # keep the dice rolling the same, drop the heap
            return []
        return heap( rng, x, y, *rest, **kw )

    S.heap_domes = clear_of_vistas
    import numpy as np
    plain_base = S.clear_sky_base

    def veiled_base( w, h, sun ):
        """ The cloudless sky at twice the resolution, with a paler band of haze along the horizon and three thin cirrus
        streaks high up, lit white by the sun: an early October afternoon, not a skybox's flat blue. """
        w, h = w * 2, h * 2
        sky = plain_base( w, h, sun )
        d = S.panorama_directions( w, h )
        el = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
        az = np.degrees( np.arctan2( d[..., 1], d[..., 0] ) )
        lum = sky @ S.LUMA
        share, fold = HAZE_BAND
        haze = share * np.exp( -np.abs( el ) / fold )[..., None]
        pale = lum[..., None] * 1.12 * np.array( ( 0.98, 0.99, 1.0 ) )
        sky = sky * ( 1 - haze ) + pale * haze
        white = float( np.percentile( lum[( el > 3 ) & ( el < 8 )], 50 ) ) * 1.35 * np.array( ( 1.0, 0.995, 0.985 ) )
        rng = np.random.default_rng( 1003 )
        veil = np.zeros( el.shape )
        for a0, e0, slant, length in CIRRUS:
            da = ( ( az - a0 + 180 ) % 360 - 180 ) * np.cos( np.radians( e0 ) )
            de = el - e0
            t = np.radians( slant )
            u = da * np.cos( t ) + de * np.sin( t )
            v = -da * np.sin( t ) + de * np.cos( t )
            along = S.smoothstep( length / 2, length / 2 - 5.0, np.abs( u ) )
            veil += 0.45 * np.exp( -( v / 1.6 ) ** 2 ) * along         # the veil the filaments lie in
            for k in range( 7 ):                                # its filaments, combed along it
                off, wid, amp = rng.uniform( -1.4, 1.4 ), rng.uniform( 0.3, 0.75 ), rng.uniform( 0.5, 1.0 )
                bend = 0.25 * np.sin( u * rng.uniform( 0.3, 0.6 ) + rng.uniform( 0, 6.28 ) )
                fibre = 0.65 + 0.35 * np.sin( u * rng.uniform( 1.5, 3.0 ) + rng.uniform( 0, 6.28 ) )
                veil += amp * fibre * np.exp( -( ( v - off - bend ) / wid ) ** 2 ) * along
        a = np.clip( veil, 0, 1.6 ) / 1.6 * CIRRUS_OPACITY
        return sky * ( 1 - a[..., None] ) + white * a[..., None]

    S.clear_sky_base = veiled_base
    sys.argv[0] = __file__
    S.main()


if __name__ == "__main__":
    main()
