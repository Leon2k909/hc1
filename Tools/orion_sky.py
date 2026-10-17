"""
Orion's sky: golden hour after rain over the launch facility, baked with Belltower's sky code (Tools/belltower_sky.py)
into its own panorama, as Riverdale's is.

    python Tools/orion_sky.py [belltower_sky's options: --width, --seed, --out, --preview, --views-only, ...]

- The reference picture looks north over the yard into a low sun: the sun stands 8.3 degrees up, 25 degrees west of
  north, half behind Launch Control's corner (SUN_PITCH, SUN_YAW; orion_map's sun is the same). Its colours were
  sampled from the picture along the view (orion_map's reference camera) and keyed by height as the row's mean: pale
  cream at the horizon, a clean blue overhead (SKY_KEYS). The atmosphere's own variation brightens the sun's side, and a
  glow round the sun (GLOW) whitens the sky there, as the picture's does past the tower's corner.
- Thin, flat fair-weather patches and small heaps, a cloud layer higher than Belltower's, gold-rimmed near the sun and
  white-grey away from it. FORCED puts patches where the picture has them; elsewhere the field scatters fewer. Their
  sunlight is a little dimmer than the scene's (CLOUD_SUN), so the tonemap leaves the sunward ones gold rather than white.
- Writes Assets/materials/orion/sky/oa_sky.exr and oa_sky.vmat.
"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/orion/sky"
RESOURCE_DIR = "materials/orion/sky"
NAME = "oa_sky"

SUN_PITCH, SUN_YAW = 8.3, -155.0      # orion_map's: 8.3 degrees up, towards 25 degrees west of north
LIGHT = np.array( ( 1.75, 1.20, 0.70 ) )

# The clear sky's displayed colours (sRGB) by degrees above the horizon, from the picture's clear patches.
SKY_KEYS = ( ( 0.0, ( 148, 144, 146 ) ), ( 3.0, ( 146, 145, 150 ) ), ( 6.0, ( 144, 149, 162 ) ), ( 9.0, ( 130, 144, 169 ) ),
             ( 12.0, ( 115, 138, 174 ) ), ( 17.0, ( 92, 120, 163 ) ), ( 25.0, ( 80, 108, 156 ) ), ( 40.0, ( 70, 98, 148 ) ),
             ( 90.0, ( 62, 88, 140 ) ) )

# The glow round the sun, added to the clear sky: ( angular radius in degrees, linear brightness, colour ).
GLOW = ( ( 2.6, 2.4, ( 1.0, 0.97, 0.92 ) ), ( 8.0, 0.41, ( 1.0, 0.9, 0.76 ) ), ( 22.0, 0.064, ( 1.0, 0.86, 0.7 ) ) )

# The cloud layer, metres above the facility: higher and thinner than Belltower's.
BASE, TOP = 2400.0, 3300.0

# Patches the picture has, placed by their bearing and height in it ( bearing east of north, distance, radius, height ),
# metres, at the cloud base: gold lumps and thin streaks right of the sun over the tall mast, a broken patch over the
# viaduct, a streak behind the pad, small white heaps on the right over the radome. The sky above the pad and in the
# top right stays clear.
# The picture's clouds, painted into the panorama as a thin 2D layer (paint_streaks), each a region in bearing (east of
# north) and elevation, degrees: ( style, bearing, elevation, spread across, spread up, opacity ). Lumps are the gold
# heaped patches right of the sun; streaks are drawn out across the view; patches are small broken cells. Above the pad
# and in the top right the sky stays clear, as in the picture.
STREAKS = ( ( "lump", -19.0, 13.8, 4.6, 2.2, 1.0 ), ( "streak", -17.0, 10.2, 6.0, 1.6, 0.9 ),
            ( "streak", -12.0, 11.6, 4.0, 1.1, 0.7 ), ( "patch", -7.5, 11.8, 6.0, 1.6, 0.85 ),
            ( "streak", -1.0, 9.6, 6.5, 0.8, 0.75 ), ( "lump", 20.5, 13.4, 3.2, 1.1, 0.95 ),
            ( "lump", 25.5, 10.8, 4.5, 1.4, 0.85 ), ( "patch", 24.0, 12.5, 4.0, 1.2, 0.6 ),
            ( "streak", 18.5, 7.6, 2.6, 0.6, 0.6 ), ( "lump", -25.5, 15.5, 4.0, 2.0, 0.9 ) )
CLEAR = ( ( 4.0, 20.0, 9.0, 6.0 ), ( 33.0, 21.0, 8.0, 6.0 ) )      # ( bearing, elevation, spread across, spread up )

PREVIEW_VIEWS = ( ( "reference", 0.0, -9.4, 75 ), ( "towards_sun", None, 10, 85 ), ( "away", None, 14, 85 ),
                  ( "east", -90.0, 10, 85 ), ( "west", 90.0, 10, 85 ), ( "up", None, 62, 90 ) )


PREVIEW_DIR = None


def lattice_noise( B, E, cell_b, cell_e, rng ):
    """ Value noise over bearing (wrapping round 360) and elevation, degrees, on cells cell_b by cell_e, smoothed. """
    nb = max( 2, int( round( 360.0 / cell_b ) ) )
    ne = int( 100.0 / cell_e ) + 3
    grid = rng.random( ( ne, nb ) )
    gb = ( ( B + 180.0 ) % 360.0 ) / ( 360.0 / nb )
    ge = np.clip( E + 5.0, 0, None ) / cell_e
    ib, ie = np.floor( gb ).astype( int ), np.floor( ge ).astype( int )
    fb, fe = gb - ib, ge - ie
    fb, fe = fb * fb * ( 3 - 2 * fb ), fe * fe * ( 3 - 2 * fe )
    ie = np.clip( ie, 0, ne - 2 )
    v00, v10 = grid[ie, ib % nb], grid[ie, ( ib + 1 ) % nb]
    v01, v11 = grid[ie + 1, ib % nb], grid[ie + 1, ( ib + 1 ) % nb]
    return ( v00 * ( 1 - fb ) + v10 * fb ) * ( 1 - fe ) + ( v01 * ( 1 - fb ) + v11 * fb ) * fe


def fbm( B, E, cell_b, cell_e, octaves, seed ):
    rng = np.random.default_rng( seed )
    total, amp, norm = 0.0, 1.0, 0.0
    for k in range( octaves ):
        total = total + amp * lattice_noise( B, E, cell_b / 2 ** k, cell_e / 2 ** k, rng )
        norm += amp
        amp *= 0.5
    return total / norm


def paint_streaks( S, rgb ):
    """ The picture's thin clouds over the panorama's sky: anisotropic noise in bearing and elevation, inside STREAKS'
    regions (and a sparse field elsewhere), lit gold and backlit towards the sun, white-grey away from it. """
    h, w = rgb.shape[:2]
    d = S.panorama_directions( w, h )
    B = np.degrees( np.arctan2( -d[..., 1], d[..., 0] ) )
    E = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
    band = ( E > 1.0 ) & ( E < 32.0 )
    rows = np.where( band.any( 1 ) )[0]
    r0, r1 = rows.min(), rows.max() + 1
    B, E = B[r0:r1], E[r0:r1]
    streak = fbm( B, E, 9.0, 0.9, 5, 101 )
    patch = fbm( B, E, 1.8, 0.75, 4, 202 )
    lump = fbm( B, E, 2.8, 1.3, 4, 303 )
    keep = np.ones_like( B )
    for kind, b0, e0, sb, se, opacity in STREAKS:
        db = ( ( B - b0 + 180.0 ) % 360.0 ) - 180.0
        mask = np.exp( -( db / sb ) ** 2 - ( ( E - e0 ) / se ) ** 2 )
        if kind == "streak":
            dens = S.smoothstep( 0.5, 0.7, streak )
        elif kind == "patch":
            dens = S.smoothstep( 0.52, 0.72, 0.7 * patch + 0.3 * streak )
        else:
            dens = S.smoothstep( 0.44, 0.66, lump )
        keep = keep * ( 1.0 - np.clip( mask * 1.25, 0, 1 ) * dens * opacity )
    # A sparse field of thin streaks round the rest of the sky, clear where the picture is.
    field = S.smoothstep( 0.6, 0.78, fbm( B, E, 40.0, 7.0, 3, 404 ) )
    for b0, e0, sb, se in CLEAR + tuple( ( b, e, sb_, se_ ) for _, b, e, sb_, se_, _ in STREAKS ):
        db = ( ( B - b0 + 180.0 ) % 360.0 ) - 180.0
        field = field * ( 1.0 - np.exp( -( db / ( sb * 1.6 ) ) ** 2 - ( ( E - e0 ) / ( se * 2.5 ) ) ** 2 ) )
    lift = S.smoothstep( 2.0, 6.0, E ) * ( 1.0 - S.smoothstep( 24.0, 32.0, E ) )
    keep = keep * ( 1.0 - field * S.smoothstep( 0.52, 0.7, streak ) * 0.7 * lift )
    alpha = ( 1.0 - keep )[..., None]
    sun = S.sun_direction()
    ang = np.degrees( np.arccos( np.clip( d[r0:r1] @ sun, -1, 1 ) ) )
    near = np.exp( -( ang / 26.0 ) ** 2 )[..., None]
    bright_sun, dim_sun = S.undisplay( np.array( ( 252, 236, 206 ) ) ), S.undisplay( np.array( ( 150, 136, 138 ) ) )
    bright_far, dim_far = S.undisplay( np.array( ( 232, 233, 238 ) ) ), S.undisplay( np.array( ( 150, 158, 178 ) ) )
    t = np.clip( alpha * 1.4, 0, 1 ) ** 1.3
    # Backlit towards the sun: thin edges glow, thick cores go grey-violet underneath. Side-lit away from it: white
    # tops, grey-blue undersides (the lower part of each cloud, where its density falls off below).
    below = np.clip( ( np.roll( alpha, 3, axis=0 ) - np.roll( alpha, -3, axis=0 ) ) * 4.0, 0, 1 )
    rim = 1.0 + 0.6 * ( 1.0 - t ) * near
    under = np.clip( 0.55 * t + 0.8 * below, 0, 1 )
    sunward = ( bright_sun * ( 1 - under ) + dim_sun * under ) * rim
    away = bright_far * ( 1 - 0.6 * below ) + dim_far * ( 0.6 * below )
    colour = sunward * near + away * ( 1 - near )
    out = rgb.copy()
    out[r0:r1] = rgb[r0:r1] * ( 1 - alpha ) + colour * alpha
    return out


def reference_view( S, rgb ):
    """ The panorama as orion_map's reference picture frames it: a level view due north with its horizon 346 down (the
    picture's shifted lens), 1536 x 1024, 75 degrees across. """
    W, H, f = 1536, 1024, 768 / math.tan( math.radians( 37.5 ) )
    x, y = np.meshgrid( np.arange( W ) + 0.5, np.arange( H ) + 0.5 )
    east, up = ( x - W / 2 ) / f, ( 346.0 - y ) / f
    d = np.stack( [ np.ones_like( east ), -east, up ], -1 )
    d /= np.linalg.norm( d, axis=-1, keepdims=True )
    u, v = S.panorama_uv( d )
    h, w = rgb.shape[:2]
    return rgb[np.clip( ( v * h ).astype( int ), 0, h - 1 ), np.clip( ( u * w ).astype( int ), 0, w - 1 )]


def main():
    global PREVIEW_DIR
    import belltower_sky as S
    if "--preview" in sys.argv:
        PREVIEW_DIR = Path( sys.argv[sys.argv.index( "--preview" ) + 1] )

    S.SUN_PITCH, S.SUN_YAW = SUN_PITCH, SUN_YAW
    S.OUT_DIR, S.RESOURCE_DIR, S.NAME = OUT_DIR, RESOURCE_DIR, NAME
    S.SKY_KEYS = SKY_KEYS
    S.LIGHT = LIGHT
    S.CLOUD_SUN = LIGHT * 1.05
    S.HALO_WHITE = np.array( ( 1.22, 1.0, 0.72 ) )
    S.SUN_HALO = 0.4
    S.GROUND = np.array( ( 0.20, 0.18, 0.15 ) )
    S.AMB_HIGH = np.array( ( 0.15, 0.25, 0.50 ) )
    S.AMB_LOW = np.array( ( 0.34, 0.29, 0.25 ) )
    S.BASE, S.TOP = BASE, TOP
    S.HEAPS = 0.0            # every cloud is painted (paint_streaks): the marcher's round heaps read as cartoon puffs
    S.HEAP_SIZE = ( 480.0, 0.5, 180.0, 1300.0 )
    S.HEAP_HEIGHT = ( 0.2, 0.45 )
    S.PUFF_GROUPS = 0.0
    S.NEAR_RING = ( 1e7, 1e7 + 1 )
    S.SUN_GAP = 600.0
    S.NEAR_SIZE = ( 700.0, 0.35, 400.0, 1000.0 )
    S.PREVIEW_VIEWS = PREVIEW_VIEWS
    S.VIEW_OFF_SUN = { "towards_sun": 0, "away": 180, "up": 90 }
    draw = S._draw_domes

    def with_forced( domes, n, texel, top, bottom, strength ):
        import math
        rng = np.random.default_rng( 31 )
        wind = np.array( ( math.cos( math.radians( S.WIND_TOWARDS ) ), math.sin( math.radians( S.WIND_TOWARDS ) ) ) )
        extra = []
        for kind, bearing, dist, *rest in ():
            b = math.radians( bearing )
            # The sky's x is north and y west.
            x, y = dist * math.cos( b ), -dist * math.sin( b )
            if kind == "heap":
                r, h = rest
                extra += S.heap_domes( rng, x, y, r, min( h, S.TOP - S.BASE ), wind * S.LEAN * h )
            elif kind == "streak":
                length, width, thick, density = rest
                across = np.array( ( math.sin( b ), math.cos( b ) ) )      # level, across the line of sight
                for k in range( max( 3, int( length / ( width * 0.55 ) ) ) ):
                    f = rng.uniform( -0.5, 0.5 )
                    rho = width * rng.uniform( 0.6, 1.2 ) * ( 1 - 0.5 * abs( f ) * 2 ) + 40
                    jitter = rng.normal( 0, width * 0.35 )
                    cx = x + across[0] * f * length - across[1] * jitter * 0.6
                    cy = y + across[1] * f * length + across[0] * jitter * 0.6
                    extra.append( ( cx, cy, thick * rng.uniform( 0.5, 1.0 ) - rho, rho, density * rng.uniform( 0.6, 1.0 ) ) )
            else:
                spread, count, thick, density = rest
                across = np.array( ( math.sin( b ), math.cos( b ) ) )
                along = np.array( ( math.cos( b ), -math.sin( b ) ) )
                for k in range( count ):
                    a = rng.uniform( 0, 2 * math.pi )
                    off = spread * math.sqrt( rng.random() )
                    rho = rng.uniform( 140, 320 )
                    q = across * off * math.cos( a ) * 1.5 + along * off * math.sin( a ) * 0.6
                    extra.append( ( x + q[0], y + q[1], thick * rng.uniform( 0.5, 1.0 ) - rho, rho, density * rng.uniform( 0.6, 1.0 ) ) )
        return draw( np.concatenate( [ np.asarray( domes, np.float64 ).reshape( -1, 5 ), np.array( extra, np.float64 ).reshape( -1, 5 ) ] ), n, texel, top,
                     bottom, strength )

    S._draw_domes = with_forced
    base_sky = S.clear_sky_base

    def with_glow( w, h, sun ):
        sky = base_sky( w, h, sun )
        d = S.panorama_directions( w, h )
        ang = np.degrees( np.arccos( np.clip( d @ np.asarray( sun ), -1, 1 ) ) )
        above = np.clip( d[..., 2] * 20 + 1, 0, 1 )[..., None]
        for radius, strength, colour in GLOW:
            sky = sky + ( strength * np.exp( -( ang / radius ) ** 2 ) )[..., None] * np.array( colour ) * above
        return sky

    S.clear_sky_base = with_glow
    write = S.write_exr

    def with_streaks( path, rgb ):
        rgb = paint_streaks( S, rgb )
        write( path, rgb )
        if PREVIEW_DIR is not None:
            from PIL import Image
            Image.fromarray( S.display( reference_view( S, rgb ) ) ).save( PREVIEW_DIR / "reference_level.png" )

    S.write_exr = with_streaks
    sys.argv[0] = __file__
    S.main()


if __name__ == "__main__":
    main()
