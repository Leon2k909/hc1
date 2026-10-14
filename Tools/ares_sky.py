"""
Ares's sky: a Martian evening over the Ares Facility, as the reference picture has it (2026-10-14). The sky is near
black overhead and deepens to a rust haze at the horizon, with stars and the two moons standing high in the north,
where the hall's window looks. Written as a panorama with belltower_sky's EXR writer and wrapping.

    python Tools/ares_sky.py [--out <dir>] [--width 4096] [--preview <png>]

- Mars's dust lifts the haze's colour to butterscotch and rust low down; above about 20 degrees the evening sky is
  dark. The values are linear radiance at the hall's exposure (ares_map's Look: auto exposure between SKY_EXPOSURE and
  3): the haze at the horizon about a third of the sunlit ground's brightness, the zenith nearly nothing.
- The moons are the picture's: two cratered moons, the larger 8 degrees across at 33 degrees up and 22 degrees east of
  north, the smaller 3.4 degrees across lower and further east. Phobos and Deimos are far smaller from the ground
  (0.2 and 0.04 degrees), but the picture draws them big, and so does this. They're lit from the sun behind the viewer
  (SUN_PITCH, SUN_YAW), so they show nearly full.
- The sun (low in the south-east, behind the hall) has the small blue halo of a Martian sunset round it.
- Writes Assets/materials/ares/sky/ares_sky.exr and ares_sky.vmat.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import belltower_sky as BS  # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/ares/sky"
RESOURCE_DIR = "materials/ares/sky"
NAME = "ares_sky"
SKY_MATERIAL = f"{RESOURCE_DIR}/{NAME}.vmat"

# The scene's sun: the light points along its forward, pitched down and turned from x (north) towards y (west). It
# comes from the south-east, 20 degrees up, so the land the window looks over is lit from behind the viewer.
SUN_PITCH, SUN_YAW = 20.0, 42.0

# The sky's linear colour by degrees above the horizon.
SKY_KEYS = ( ( -10.0, ( 0.040, 0.020, 0.012 ) ), ( 0.0, ( 0.30, 0.135, 0.062 ) ), ( 3.0, ( 0.22, 0.098, 0.046 ) ),
             ( 10.0, ( 0.095, 0.044, 0.024 ) ), ( 22.0, ( 0.030, 0.016, 0.011 ) ), ( 40.0, ( 0.010, 0.0065, 0.0055 ) ),
             ( 90.0, ( 0.0045, 0.0035, 0.0035 ) ) )

# The moons: degrees east of north, degrees up, angular diameter, albedo, seed.
MOONS = ( ( 22.0, 33.0, 8.0, 0.30, 5 ), ( 34.0, 25.5, 3.4, 0.24, 6 ) )
MOON_LIGHT = 1.6         # the sunlight's radiance on them


def sky_colour( el ):
    keys_el = np.array( [ k[0] for k in SKY_KEYS ] )
    cols = np.array( [ k[1] for k in SKY_KEYS ] )
    return np.stack( [ np.interp( el, keys_el, cols[:, c] ) for c in range( 3 ) ], -1 )


def plan_direction( east_of_north, up ):
    """ World direction (x north, y west, z up) from degrees east of north and degrees up. """
    a, e = math.radians( east_of_north ), math.radians( up )
    return np.array( ( math.cos( e ) * math.cos( a ), -math.cos( e ) * math.sin( a ), math.sin( e ) ) )


def sun_direction():
    BS.SUN_PITCH, BS.SUN_YAW = SUN_PITCH, SUN_YAW
    return BS.sun_direction()


def render( width ):
    h = width // 2
    d = BS.panorama_directions( width, h )
    el = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
    rgb = sky_colour( el ).astype( np.float32 )
    rng = np.random.default_rng( 41 )

    # Stars: a scatter of points, more of them dim, fading into the haze.
    count = width * h // 260
    rows = rng.integers( 0, h // 2, count )
    cols = rng.integers( 0, width, count )
    bright = rng.pareto( 2.4, count ).astype( np.float32 ) * 0.02 + 0.01
    fade = np.clip( ( el[rows, cols] - 6.0 ) / 20.0, 0, 1 )
    tint = np.stack( [ np.ones( count ), 0.92 + 0.08 * rng.random( count ), 0.85 + 0.15 * rng.random( count ) ], -1 )
    np.add.at( rgb, ( rows, cols ), ( bright * fade )[:, None] * tint )

    # The sun's glow and its blue halo, low in the south-east.
    sun = sun_direction()
    cos_sun = np.clip( d @ sun, -1, 1 )
    angle = np.degrees( np.arccos( cos_sun ) )
    rgb += ( np.exp( -angle / 25.0 )[..., None] * np.array( ( 0.35, 0.18, 0.08 ) ) * 0.5 ).astype( np.float32 )
    rgb += ( np.exp( -angle / 6.0 )[..., None] * np.array( ( 0.20, 0.32, 0.55 ) ) ).astype( np.float32 )
    rgb += ( ( angle < 0.18 )[..., None] * np.array( ( 40.0, 38.0, 34.0 ) ) ).astype( np.float32 )

    # The moons.
    for east, up, diameter, albedo, seed in MOONS:
        centre = plan_direction( east, up )
        radius = math.radians( diameter / 2 )
        cos_r = math.cos( radius * 1.05 )
        near = d @ centre > cos_r
        if not near.any():
            continue
        r_idx, c_idx = np.nonzero( near )
        v = d[r_idx, c_idx]
        # The moon's own frame: ex, ey across its face, centre towards the viewer.
        ex = np.cross( ( 0.0, 0.0, 1.0 ), centre )
        ex /= np.linalg.norm( ex )
        ey = np.cross( centre, ex )
        tx = ( v @ ex ) / math.sin( radius )
        ty = ( v @ ey ) / math.sin( radius )
        rr = np.sqrt( tx * tx + ty * ty )
        inside = rr < 1.0
        tz = np.sqrt( np.clip( 1.0 - rr * rr, 0, 1 ) )
        # The sphere's normal in world space (pointing back at the viewer), lit by the sun.
        normal = ( tx[:, None] * ex + ty[:, None] * ey - tz[:, None] * centre )
        lambert = np.clip( normal @ sun, 0, 1 )
        mrng = np.random.default_rng( seed )
        surf = np.zeros( len( tx ), np.float32 )
        for _ in range( 70 ):
            cx, cy = mrng.uniform( -1, 1, 2 )
            cr = mrng.uniform( 0.03, 0.22 ) ** 1.3
            dist = np.hypot( tx - cx, ty - cy ) / cr
            surf += np.where( dist < 1.0, -0.25 * ( 1 - dist ** 2 ), 0.0 ) + 0.18 * np.exp( -( ( dist - 1.0 ) / 0.12 ) ** 2 )
        maria = np.sin( tx * 3.1 + seed ) * np.cos( ty * 2.7 - seed ) * 0.12
        a = albedo * np.clip( 1.0 + surf + maria, 0.4, 1.4 )
        moon = ( MOON_LIGHT * a * lambert )[:, None] * np.array( ( 1.0, 0.93, 0.86 ) ) + 0.004
        edge = np.clip( ( 1.0 - rr ) / 0.02, 0, 1 )[:, None]
        rgb[r_idx, c_idx] = ( rgb[r_idx, c_idx] * ( 1 - edge * inside[:, None] ) + moon * edge * inside[:, None] ).astype( np.float32 )
    return rgb


def vmat_text():
    return ( "// Tools/ares_sky.py\n"
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
        shown = 1.0 - np.exp( -rgb * 2.5 )
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
