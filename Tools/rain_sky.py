"""
The rain's sky: a low, even overcast of nimbostratus, baked into an HDR panorama for s&box's sky shader. Weather
(RainLook in Code/World/RainView.cs) swaps a map's sky for it while it rains, and puts the map's own back after.

    python Tools/rain_sky.py [--width 2048] [--seed N] [--out <dir>] [--preview <dir>]

- Rain falls from a deck of nimbostratus a few hundred metres to 2 km up, thick enough (optical depth 20-50 and more)
  that no sunlight comes straight through it and no disc shows: the sky is one sheet of grey with no shadows under it.
- How bright it is by height: the CIE standard overcast sky is three times as bright overhead as at the horizon. In rain
  the air under the deck is full of drops and haze, lit by the deck, so a level view ends in that bright haze instead:
  here the horizon is HORIZON_SHARE of the zenith, rising as sin^0.8 of the elevation.
- Its colours are made for how a match shows them, as belltower_sky's are: s&box's ACES at exposure DESIGN_EXPOSURE,
  the outdoor maps' Look volume. ZENITH is the zenith as shown there: a light overcast. RainView darkens it for heavier
  rain with the SkyBox2D's Tint, so one panorama does for drizzle and downpour.
- The deck isn't flat: its base is a plane CLOUD_BASE up with soft, darker thick patches on it (fbm), and under it ragged
  scud SCUD_BASE up, darker still, the way low fractus hangs under rain. Both fade into the rain's haze with distance
  (HAZE metres to hide 63%), so near the horizon the sky is even.
- Round the horizon, rain shafts: darker curtains of heavier rain a few kilometres off, leaning with the wind.
- Below the horizon, which the maps' own hills and walls mostly hide, the haze gives way to wet ground under the overcast.
  The sky is also what the maps reflect (SkyBox2D's SkyIndirectLighting).
- It prints the figures RainView copies (RainLook in RainView.cs): the horizon's colour, which the fog takes so distant
  things fade into the sky, and the overcast's mean light against a clear map's, for the sun's sky colour.

It writes Assets/materials/weather/overcast_sky.exr and overcast_sky.vmat. --preview writes the panorama and views as a
match would show them.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import belltower_sky as S   # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/weather"
RESOURCE_DIR = "materials/weather"
NAME = "overcast_sky"
CLEAR_SKY = ROOT / "Assets/materials/belltower/sky/belltower_sky.exr"   # a clear map's sky, to compare the light with

ZENITH = 192            # the zenith as a match shows it (sRGB grey at DESIGN_EXPOSURE)
HORIZON_SHARE = 0.6     # the horizon's radiance against the zenith's
TINT = np.array( ( 0.955, 0.985, 1.04 ) )   # overcast is a cool grey
CLOUD_BASE, SCUD_BASE = 900.0, 380.0        # metres over the map
HAZE = 5000.0           # metres for the rain's haze to hide 63% of the deck: rain's 3-10 km visibility, overhead less
DECK_TILE = 60000.0     # metres the deck's noise covers; its edges are past where the haze hides it
DECK_PATCHES = ( 0.13, 650.0 )      # how much darker the thick patches are, at most; their size in metres
DECK_SWELLS = ( 0.08, 4000.0 )      # broader swells of the deck
SCUD = ( 0.16, 0.5, 260.0 )         # how much darker scud is; how much of the sky it covers (0..1, as a threshold); size
SCUD_STRETCH = 2.2      # scud is drawn out along the wind
SHAFTS = ( 0.07, 12.0 )             # rain shafts: how much darker, and about how many degrees across
SHAFT_TOP = 11.0        # degrees: the shafts reach up to the deck's base about here, a few km off
WIND_TOWARDS = -53.0    # WorldWind's default heading: the shafts lean this way
GROUND = 0.32           # the wet ground below the horizon against the horizon's radiance
GROUND_TINT = np.array( ( 0.96, 1.0, 0.94 ) )


def deck_noise( rng, size=2048 ):
    """ The deck's darkening as a function of where a view meets it, over DECK_TILE: patches and swells on the deck,
    and the scud under it, ragged at its edges and drawn out along the wind. Each comes with a blurred copy, which far
    views take: the texture of a deck kilometres off is finer than a pixel. """
    texel = DECK_TILE / size
    patches = S.fbm2( rng, size, DECK_PATCHES[1] / texel )
    swells = S.fbm2( rng, size, DECK_SWELLS[1] / texel )
    dark = DECK_PATCHES[0] * S.smoothstep( -0.3, 1.1, patches ) + DECK_SWELLS[0] * swells
    rag = S.fbm2( rng, size, SCUD[2] / texel ) + 0.45 * S.fbm2( rng, size, SCUD[2] / texel / 4 )
    scud = SCUD[0] * S.smoothstep( 1 - SCUD[1], 1 - SCUD[1] + 0.7, rag / 1.45 ) ** 1.5
    blur = lambda x: ndimage.gaussian_filter( x, 8, mode="wrap" ).astype( np.float32 )
    return ( dark.astype( np.float32 ), blur( dark ) ), ( scud.astype( np.float32 ), blur( scud ) )


def sample_plane( tex, d, height, stretch=1.0 ):
    """ tex (a sharp copy and a blurred one) at where directions d (upward) meet a level plane height metres up,
    drawn out stretch times along the wind, and how far that is. """
    size = tex[0].shape[0]
    z = np.maximum( d[..., 2], 1e-4 )
    x, y = d[..., 0] / z * height, d[..., 1] / z * height
    wind = math.radians( WIND_TOWARDS )
    along = ( x * math.cos( wind ) + y * math.sin( wind ) ) / stretch
    across = -x * math.sin( wind ) + y * math.cos( wind )
    u = ( along / DECK_TILE + 0.5 ) * size - 0.5
    v = ( across / DECK_TILE + 0.5 ) * size - 0.5
    at = lambda t: ndimage.map_coordinates( t, [ u.ravel(), v.ravel() ], order=1, mode="nearest" ).reshape( z.shape )
    dist = height / z
    far = S.smoothstep( 1200.0, 4500.0, dist )
    return at( tex[0] ) * ( 1 - far ) + at( tex[1] ) * far, dist


def shaft_noise( rng ):
    """ Periodic noise round the horizon, 3600 steps of 0.1 degree: where the shafts are. """
    n = 3600
    spectrum = rng.normal( 0, 1, n ) + 1j * rng.normal( 0, 1, n )
    f = np.fft.fftfreq( n, 0.1 )    # cycles per degree
    width = SHAFTS[1]
    spectrum *= np.exp( -( f * width ) ** 2 ) * ( np.abs( f ) > 1 / 360 )
    fine = rng.normal( 0, 1, n ) + 1j * rng.normal( 0, 1, n )
    fine *= np.exp( -( f * 1.2 ) ** 2 ) * ( np.abs( f ) > 1 / 60 )
    coarse = np.real( np.fft.ifft( spectrum ) )
    streaks = np.real( np.fft.ifft( fine ) )
    coarse /= np.abs( coarse ).max()
    streaks /= np.abs( streaks ).max()
    return np.clip( coarse, 0, 1 ) * ( 0.75 + 0.25 * streaks )


def sky( d, deck, scud, shafts ):
    """ Linear HDR radiance in directions d ( ..., 3 ). """
    zenith = S.undisplay( np.array( ( ZENITH, ZENITH, ZENITH ) ) ) * TINT
    el = np.arcsin( np.clip( d[..., 2], -1, 1 ) )
    up = np.clip( np.sin( el ), 0, 1 )
    horizon = zenith * HORIZON_SHARE
    base = horizon + ( zenith - horizon ) * ( up ** 0.8 )[..., None]

    # The deck and the scud, fading into the haze with distance.
    upward = d[..., 2] > 1e-3
    dark = np.zeros( d.shape[:-1], np.float32 )
    if upward.any():
        du = d[upward]
        patch, dist = sample_plane( deck, du, CLOUD_BASE )
        rag, dist_scud = sample_plane( scud, du, SCUD_BASE, SCUD_STRETCH )
        dark[upward] = patch * np.exp( -dist / HAZE ) + rag * np.exp( -dist_scud / HAZE )
    out = base * np.clip( 1 - dark, 0.5, 1.2 )[..., None]

    # Rain shafts round the horizon, leaning downwind.
    az = np.degrees( np.arctan2( d[..., 1], d[..., 0] ) )
    el_deg = np.degrees( el )
    lean = np.cos( np.radians( az - WIND_TOWARDS ) ) * 0.35   # degrees of azimuth per degree up, towards the wind
    at = ( ( az + lean * el_deg ) % 360 ) * 10
    shaft = shafts[at.astype( int ) % 3600]
    band = S.smoothstep( -4.0, 0.5, el_deg ) * ( 1 - S.smoothstep( SHAFT_TOP * 0.55, SHAFT_TOP, el_deg ) )
    out *= ( 1 - SHAFTS[0] * shaft * band )[..., None]

    # Below the horizon: the haze, then wet ground.
    ground = horizon * GROUND * GROUND_TINT
    below = S.smoothstep( 0.0, -14.0, el_deg )[..., None]
    return np.where( ( el_deg < 0 )[..., None], out * ( 1 - below ) + ground * below, out )


def mean_light( pano ):
    """ The cosine-weighted mean radiance of a panorama's upper half: what it gives a level surface, over pi. """
    h, w = pano.shape[:2]
    d = S.panorama_directions( w, h )
    weight = np.clip( d[..., 2], 0, 1 ) * np.sqrt( np.clip( 1 - d[..., 2] ** 2, 0, 1 ) )
    return ( pano * weight[..., None] ).sum( ( 0, 1 ) ) / weight.sum()


def vmat_text():
    """ The core skies' material, as belltower_sky writes it: the sky shader's texture is SkyTexture. """
    return ( "// Tools/rain_sky.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/sky.shader"\n'
             '    F_TEXTURE_FORMAT2 "6"\n'
             '    g_flBrightnessExposureBias "0"\n'
             '    g_flRenderOnlyExposureBias "0"\n'
             f'    SkyTexture "{RESOURCE_DIR}/{NAME}.exr"\n'
             "}\n" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--width", type=int, default=2048 )
    parser.add_argument( "--seed", type=int, default=11 )
    parser.add_argument( "--out", type=Path, default=OUT_DIR )
    parser.add_argument( "--preview", type=Path )
    args = parser.parse_args()
    rng = np.random.default_rng( args.seed )
    deck, scud = deck_noise( rng )
    shafts = shaft_noise( rng )

    w, h = args.width, args.width // 2
    ss = 2
    pano = np.empty( ( h, w, 3 ), np.float32 )
    for row in range( 0, h, 64 ):
        rows = range( row * ss, min( row + 64, h ) * ss )
        d = S.panorama_directions( w * ss, h * ss, rows )
        n = len( rows ) // ss
        pano[row:row + n] = sky( d, deck, scud, shafts ).reshape( n, ss, w, ss, 3 ).mean( ( 1, 3 ) )

    d = S.panorama_directions( w, h )
    el = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
    horizon = pano[( el > 0 ) & ( el < 3 )].mean( 0 )
    zenith = pano[el > 80].mean( 0 )
    mean = mean_light( pano )
    luma = lambda c: float( np.dot( c, S.LUMA ) )
    print( f"zenith {np.round( zenith, 4 )} (shown {S.display( zenith )}), horizon {np.round( horizon, 4 )} "
           f"(shown {S.display( horizon )})" )
    print( f"fog colour (the horizon): {horizon[0]:.3f},{horizon[1]:.3f},{horizon[2]:.3f}" )
    if CLEAR_SKY.exists():
        clear = S.read_exr( CLEAR_SKY )
        clear = np.minimum( clear, 4.0 )    # leave out the sun's disc, which lights the maps as the sun light does
        ratio = luma( mean ) / luma( mean_light( clear ) )
        print( f"overcast's mean light {np.round( mean, 4 )}: {ratio:.3f} of a clear map's sky (sun's disc left out)" )

    args.out.mkdir( parents=True, exist_ok=True )
    S.write_exr( args.out / f"{NAME}.exr", pano )
    text = vmat_text()
    path = args.out / f"{NAME}.vmat"
    if not path.exists() or path.read_text( encoding="utf-8" ) != text:
        path.write_text( text, encoding="utf-8", newline="\n" )
    print( "wrote", args.out / f"{NAME}.exr" )

    if args.preview:
        args.preview.mkdir( parents=True, exist_ok=True )
        Image.fromarray( S.display( pano ) ).save( args.preview / "overcast_panorama.png" )
        for name, yaw, pitch, fov in ( ( "level", 30, 8, 85 ), ( "up", -60, 40, 90 ), ( "downwind", WIND_TOWARDS, 4, 85 ) ):
            view = sky( S.view_directions( yaw, pitch, fov, ( 960, 540 ) ), deck, scud, shafts )
            Image.fromarray( S.display( view ) ).save( args.preview / f"overcast_{name}.png" )
        print( "previews in", args.preview )


if __name__ == "__main__":
    main()
