"""
Riverside's sky: a cloudy night with a full moon, over a Florida trailer park, written as a panorama with
belltower_sky's EXR writer and wrapping.

    python Tools/riverside_sky.py [--out <dir>] [--width 4096] [--preview <png>]

- The reference the map is dressed after looks north down the park's lane to a full moon 13-15 degrees up, in a gap
  in broken clouds whose edges it silvers. So the moon is due north, a little west (MOON), drawn 2.4 degrees across
  (the real moon is half a degree, but the picture draws it big, and so does this), with a halo through the thin cloud
  round it.
- The clouds are one layer of broken stratocumulus 2 km up: a fractal field projected onto the layer, its density
  thinned into gaps, lit by the moon through their thin parts and at their edges, dark blue-grey where thick. Near the
  horizon they crowd together, as a layer does seen edge-on.
- Stars show in the gaps, fading into the haze low down. The horizon glows faintly orange where the park burns (north
  and north-east) and where the town is (south), and blue-grey elsewhere.
- The values are linear radiance at the map's exposure (riverside_map's Look: auto exposure between its minimum and
  maximum): the moon's disc about 4, the sky by it a few hundredths, the zenith a few thousandths.
- Writes Assets/materials/riverside/sky/riverside_sky.exr and riverside_sky.vmat.
"""
import argparse
import math
import platform
import sys
from pathlib import Path


def _no_wmi( *args, **kwargs ):
    raise OSError( "WMI query skipped" )


platform._wmi_query = _no_wmi       # see riverside_materials: WMI can hang scipy's import

import numpy as np  # noqa: E402

smoothstep = lambda a, b, x: np.clip( ( x - a ) / ( b - a ), 0, 1 ) ** 2 * ( 3 - 2 * np.clip( ( x - a ) / ( b - a ), 0, 1 ) )  # noqa: E731

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import belltower_sky as BS  # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/riverside/sky"
RESOURCE_DIR = "materials/riverside/sky"
NAME = "riverside_sky"
SKY_MATERIAL = f"{RESOURCE_DIR}/{NAME}.vmat"

# The moon: degrees east of north, degrees up, angular diameter. riverside_map's moonlight comes from about here.
MOON = ( -3.0, 15.0, 2.4 )
MOON_RADIANCE = 4.0

# The clear sky's linear colour by degrees above the horizon.
SKY_KEYS = ( ( -10.0, ( 0.010, 0.012, 0.016 ) ), ( 0.0, ( 0.040, 0.046, 0.060 ) ), ( 4.0, ( 0.030, 0.036, 0.052 ) ),
             ( 12.0, ( 0.016, 0.021, 0.034 ) ), ( 30.0, ( 0.007, 0.010, 0.019 ) ), ( 90.0, ( 0.0035, 0.005, 0.010 ) ) )

CLOUD_HEIGHT = 2000.0       # metres
CLOUD_EXTENT = 48000.0      # metres across the noise field
COVER = 0.58                # the share of the sky the layer hides overhead


def sky_colour( el ):
    keys = np.array( [ k[0] for k in SKY_KEYS ] )
    cols = np.array( [ k[1] for k in SKY_KEYS ] )
    return np.stack( [ np.interp( el, keys, cols[:, c] ) for c in range( 3 ) ], -1 )


def plan_direction( east_of_north, up ):
    """ World direction (x north, y west, z up) from degrees east of north and degrees up. """
    a, e = math.radians( east_of_north ), math.radians( up )
    return np.array( ( math.cos( e ) * math.cos( a ), -math.cos( e ) * math.sin( a ), math.sin( e ) ) )


def fbm_field( rng, n, beta=2.6, longest=None ):
    """ Periodic fractal noise on an n x n grid (unit deviation). """
    white = rng.standard_normal( ( n, n ) )
    spec = np.fft.rfft2( white )
    fy = np.fft.fftfreq( n )[:, None]
    fx = np.fft.rfftfreq( n )[None, :]
    f = np.sqrt( fx * fx + fy * fy )
    f[0, 0] = 1.0
    amp = f ** ( -beta / 2 )
    if longest:
        amp *= np.clip( f * longest, 0, 1 )
    amp[0, 0] = 0
    a = np.fft.irfft2( spec * amp, s=( n, n ) )
    return ( a - a.mean() ) / ( a.std() + 1e-9 )


def bilinear( tex, u, v ):
    n = tex.shape[0]
    x, y = ( u % 1.0 ) * n, ( v % 1.0 ) * n
    x0, y0 = np.floor( x ).astype( int ) % n, np.floor( y ).astype( int ) % n
    x1, y1 = ( x0 + 1 ) % n, ( y0 + 1 ) % n
    fx, fy = x - np.floor( x ), y - np.floor( y )
    return ( tex[y0, x0] * ( 1 - fx ) * ( 1 - fy ) + tex[y0, x1] * fx * ( 1 - fy ) +
             tex[y1, x0] * ( 1 - fx ) * fy + tex[y1, x1] * fx * fy )


def render( width ):
    h = width // 2
    d = BS.panorama_directions( width, h )
    el = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
    rgb = sky_colour( el ).astype( np.float32 )
    rng = np.random.default_rng( 61 )
    moon = plan_direction( *MOON[:2] )
    cos_m = np.clip( d @ moon, -1, 1 )
    angle_m = np.degrees( np.arccos( cos_m ) )

    # The moon's glow in the air round it (forward scattering), before the clouds.
    rgb += ( np.exp( -angle_m / 12.0 )[..., None] * np.array( ( 0.030, 0.035, 0.045 ) ) ).astype( np.float32 )
    rgb += ( np.exp( -angle_m / 1.6 )[..., None] * np.array( ( 0.06, 0.065, 0.07 ) ) ).astype( np.float32 )

    # Horizon glows: the fires to the north-east and north, the town to the south.
    az = np.degrees( np.arctan2( -d[..., 1], d[..., 0] ) )          # east of north
    low = np.exp( -np.clip( el, 0, 90 ) / 4.0 ) * ( el > -3 )
    for centre, width_deg, colour in ( ( 20.0, 30.0, ( 0.06, 0.028, 0.01 ) ), ( -10.0, 18.0, ( 0.03, 0.014, 0.006 ) ),
                                       ( 180.0, 60.0, ( 0.025, 0.018, 0.012 ) ) ):
        da = ( az - centre + 180 ) % 360 - 180
        rgb += ( low * np.exp( -( da / width_deg ) ** 2 ) )[..., None] * np.array( colour, np.float32 )

    # Stars, before the clouds hide some.
    count = width * h // 180
    rows = rng.integers( 0, h // 2, count )
    cols = rng.integers( 0, width, count )
    bright = ( rng.pareto( 2.2, count ) * 0.03 + 0.012 ).astype( np.float32 )
    fade = np.clip( ( el[rows, cols] - 4.0 ) / 18.0, 0, 1 ) * np.clip( angle_m[rows, cols] / 12.0, 0, 1 )
    tint = np.stack( [ 0.9 + 0.1 * rng.random( count ), 0.92 + 0.08 * rng.random( count ), np.ones( count ) ], -1 )
    stars = np.zeros_like( rgb )
    np.add.at( stars, ( rows, cols ), ( bright * fade )[:, None] * tint )

    # The moon's disc: a slightly limb-darkened face with maria.
    radius = math.radians( MOON[2] / 2 )
    near = cos_m > math.cos( radius * 1.05 )
    disc = np.zeros_like( rgb )
    if near.any():
        r_idx, c_idx = np.nonzero( near )
        v = d[r_idx, c_idx]
        ex = np.cross( ( 0.0, 0.0, 1.0 ), moon )
        ex /= np.linalg.norm( ex )
        ey = np.cross( moon, ex )
        tx = ( v @ ex ) / math.sin( radius )
        ty = ( v @ ey ) / math.sin( radius )
        rr = np.sqrt( tx * tx + ty * ty )
        inside = rr < 1.0
        mrng = np.random.default_rng( 9 )
        surf = np.zeros( len( tx ), np.float32 )
        for _ in range( 9 ):
            cx, cy = mrng.uniform( -0.7, 0.7, 2 )
            cr = mrng.uniform( 0.15, 0.4 )
            dist = np.hypot( tx - cx, ty - cy ) / cr
            surf -= 0.22 * np.clip( 1 - dist ** 2, 0, 1 )
        for _ in range( 40 ):
            cx, cy = mrng.uniform( -1, 1, 2 )
            cr = mrng.uniform( 0.02, 0.1 )
            dist = np.hypot( tx - cx, ty - cy ) / cr
            surf += 0.12 * np.exp( -( ( dist - 1.0 ) / 0.2 ) ** 2 ) - 0.06 * np.clip( 1 - dist ** 2, 0, 1 )
        limb = 0.75 + 0.25 * np.sqrt( np.clip( 1 - rr * rr, 0, 1 ) )
        face = ( MOON_RADIANCE * limb * np.clip( 1 + surf, 0.5, 1.3 ) )[:, None] * np.array( ( 1.0, 0.98, 0.94 ) )
        edge = np.clip( ( 1.0 - rr ) / 0.03, 0, 1 )[:, None] * inside[:, None]
        disc[r_idx, c_idx] = ( face * edge ).astype( np.float32 )

    # The cloud layer: project each upward ray onto the layer, read a smooth fractal field there, its gaps soft-edged.
    up = d[..., 2]
    t = CLOUD_HEIGHT / np.maximum( up, 0.03 )
    px_, py_ = d[..., 0] * t, d[..., 1] * t
    big = fbm_field( np.random.default_rng( 71 ), 1024, 3.2 )
    mid = fbm_field( np.random.default_rng( 72 ), 1024, 2.8 )
    fine = fbm_field( np.random.default_rng( 73 ), 1024, 2.4 )
    u, w = px_ / CLOUD_EXTENT, py_ / CLOUD_EXTENT
    warp = 0.02 * bilinear( mid, u * 1.5 + 0.3, w * 1.5 )
    field = ( bilinear( big, u + warp, w ) + 0.45 * bilinear( mid, u * 3 + warp * 2, w * 3 ) +
              0.18 * bilinear( fine, u * 8, w * 8 + warp * 4 ) ) / 1.12
    # Far off the noise is finer than a pixel: fade the fine octaves into their mean, so it doesn't alias into bands.
    far = np.clip( ( t - 6000.0 ) / 14000.0, 0, 1 )
    field = field * ( 1 - 0.35 * far )
    # Seen edge-on near the horizon, the layer closes up.
    thresh = np.quantile( field[up > 0.5], 1 - COVER ) - 1.1 * np.exp( -np.clip( el, 0, 90 ) / 7.0 )
    density = smoothstep( thresh - 0.15, thresh + 0.55, field ) * ( up > 0.0 )
    density = np.where( up > 0.01, density, 1.0 )
    # The reference's moon shines through a gap in the layer: clear round it, thin at the gap's edge.
    density *= 1.0 - np.exp( -( angle_m / 6.0 ) ** 2 )
    # Light: the moon, low in the north, silvers the cloud edges and thin parts round it (light scattered forward
    # through them) and lights their undersides faintly everywhere; the thick middles stay dark. Puffs in the bodies.
    puff = smoothstep( -0.6, 1.2, bilinear( fine, u * 14 + 0.5, w * 14 ) + 0.6 * bilinear( mid, u * 6, w * 6 + 0.2 ) )
    puff = puff * ( 1 - far ) + 0.5 * far
    forward = np.exp( -angle_m / 9.0 ) * 3.0 + np.exp( -angle_m / 35.0 ) * 0.5 + 0.12
    edge = density * ( 1 - density ) * 4 * ( 1 - far )
    lit = forward * ( 0.08 * ( 1 - density ) + 0.45 * edge + 0.10 * puff * density )
    # The bodies catch the moonlight from above and the sky's light all round: grey-blue, lighter than the clear sky,
    # darker where they're thickest.
    body = np.array( ( 0.016, 0.019, 0.027 ) )[None, None, :] * ( 1.0 + 0.8 * puff - 0.4 * density )[..., None]
    cloud_col = body + lit[..., None] * np.array( ( 0.070, 0.075, 0.085 ) )[None, None, :]
    # Low down, the horizon's glows light the cloud bases a little.
    cloud_col += rgb * 0.35 * np.exp( -np.clip( el, 0, 90 ) / 6.0 )[..., None]
    alpha = np.clip( density * 1.05, 0, 1 )[..., None]
    behind = rgb + stars + disc * ( 1 - 0.85 * np.clip( density * 2.5, 0, 1 ) )[..., None]
    out = behind * ( 1 - alpha ) + cloud_col * alpha
    # Below the horizon: dark ground, the haze over it fading down.
    below = el < 0
    out[below] = ( sky_colour( np.zeros( below.sum() ) ) * np.exp( el[below] / 3.0 )[:, None] * 0.7 +
                   np.array( ( 0.004, 0.005, 0.006 ) ) ).astype( np.float32 )
    return out.astype( np.float32 )


def vmat_text():
    return ( "// Tools/riverside_sky.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/sky.shader"\n'
             '    F_TEXTURE_FORMAT2 "6"\n'
             '    g_flBrightnessExposureBias "0"\n'
             '    g_flRenderOnlyExposureBias "0"\n'
             f'    SkyTexture "{RESOURCE_DIR}/{NAME}.exr"\n'
             "}\n" )


def main( out=None, width=4096, preview=None ):
    out = Path( out ) if out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    rgb = render( width )
    BS.write_exr( out / f"{NAME}.exr", rgb )
    ( out / f"{NAME}.vmat" ).write_text( vmat_text(), encoding="utf-8", newline="\n" )
    print( f"wrote {out / f'{NAME}.exr'}" )
    if preview:
        from PIL import Image
        shown = 1.0 - np.exp( -rgb * 30.0 )
        img = ( np.clip( shown, 0, 1 ) ** ( 1 / 2.2 ) * 255 ).astype( np.uint8 )
        Image.fromarray( img ).save( preview )
        print( f"wrote {preview}" )


if __name__ == "__main__":
    ap = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    ap.add_argument( "--out" )
    ap.add_argument( "--width", type=int, default=4096 )
    ap.add_argument( "--preview" )
    args = ap.parse_args()
    main( args.out, args.width, args.preview )
