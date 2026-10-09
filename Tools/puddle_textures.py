"""
Puddles for the rain (Code/World/RainPuddles.cs), drawn with numpy like Tools/fire_textures.py.

    python Tools/puddle_textures.py [--size 512] [--sheet <png>] [--out <dir>]

Writes decals/weather/puddle_<ground>_<shape>.decal for two grounds and three shapes, and their maps:

- puddle_shape_<n>_height.png: the hollow the water lies in, white at its deepest and black on the dry ground round
  it. The decal's height coverage fills it from the white up (Decals.hlsl: a texel shows once its height passes
  1 - CoverageAmount), so RainPuddles sets CoverageAmount to the water's depth over the hollow's and the water's edge
  follows the hollow's contours as it fills: lobes join and the rises in it stay islands until they're under. The
  depth goes linearly with the grey, so a texel at 0.5 is wet once the water is half the hollow's depth.
  - The hollows are a few broad dips run together, each a different depth, under gentle unevenness. The rim is the
    highest the border band reaches, so the full puddle stays inside the decal's square.
- puddle_<ground>_<shape>_color.png: the water. A decal can only lerp the ground's colour towards its own, so a puddle
  darkens what's under it by lerping half way (ColorMix 0.5) towards near black. That about halves the albedo, which is
  what water does to concrete (wet concrete reflects ~0.5-0.6 of dry, standing water a little less). Muddy water is
  silt-brown and hides more of its bed (ColorMix 0.8), more so where it's deeper. Alpha is 1 inside the hollow and 0 on
  the dry ground round it, so even a full puddle stops at its rim.
- puddle_water_rmo.png and puddle_flat_normal.png: shared. Still water is a mirror: roughness 0.02 (a wind-rippled one
  is rougher; the ripples from the drops are RainView's sprites), metalness 0, occlusion 1. Its surface is flat, so the
  normal is straight up whatever the bed's bumps.

Sizes: paving puddles are 20-140 units across, mud's 40-180, set by RainPuddles (the .decal's Width and Height are
100, which RainPuddles scales).

--sheet draws each puddle half full and full over concrete and earth, lit from the top left, with its height map.

It also writes Code/World/PuddleShapes.cs, where RainView puts the rain's rings on the water (--code-only writes just
that, from the height maps already in Assets). For each shape it keeps four 32x32 tables, a cell per 1/32 of the
decal's width: the lowest height within 1, 2, 3 and 4 cells of each cell's middle. A cell is under water when its first
table's value is over 1 - CoverageAmount, and a ring of radius k cells round it stays on the water while its k-th
table's value is.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import terrain_textures as tt  # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
DECAL_DIR = ROOT / "Assets/decals/weather"
DECAL_RESOURCE_DIR = "decals/weather"

SHAPES = 3
WIDTH = 100.0

# sRGB colours. Clear water over paving: near black, so ColorMix 0.5 halves what's under it. Muddy water: suspended
# silt, a little lighter where it's shallow and the bed shows through.
GROUNDS = {
    "paving": { "deep": ( 30, 29, 28 ), "shallow": ( 36, 35, 33 ), "mix": 0.5 },
    "mud": { "deep": ( 74, 60, 44 ), "shallow": ( 96, 80, 60 ), "mix": 0.8 },
}


def hollow( rng, n ):
    """ A hollow 0..1 (1 deepest) inside the square, 0 outside it. Three to five broad dips of different depths, an
    uneven floor, and a rim at the highest the border band reaches. """
    yy, xx = np.mgrid[0:n, 0:n].astype( float )
    x = ( xx + 0.5 ) / n * 2.0 - 1.0
    y = ( yy + 0.5 ) / n * 2.0 - 1.0

    depth = np.zeros( ( n, n ) )
    count = int( rng.integers( 3, 6 ) )
    for k in range( count ):
        # The first dip is the main one, near the middle; the others round it.
        reach = 0.1 if k == 0 else 0.36
        cx, cy = rng.uniform( -reach, reach, 2 )
        sx = rng.uniform( 0.2, 0.34 ) * ( 1.3 if k == 0 else 1.0 )
        sy = sx * rng.uniform( 0.55, 1.0 )
        angle = rng.uniform( 0, np.pi )
        u = ( x - cx ) * np.cos( angle ) + ( y - cy ) * np.sin( angle )
        v = -( x - cx ) * np.sin( angle ) + ( y - cy ) * np.cos( angle )
        weight = 1.0 if k == 0 else rng.uniform( 0.45, 0.9 )
        depth += weight * np.exp( -0.5 * ( ( u / sx ) ** 2 + ( v / sy ) ** 2 ) )

    # The floor's unevenness: low swells, and lumps a tenth as deep a few centimetres across. Water levels them into
    # smooth curves, so there's nothing finer: fractal noise made the edges look like spilt paint.
    depth += 0.1 * tt.spectral( rng, n, 3.0, 2, 7 ) + 0.012 * tt.spectral( rng, n, 2.5, 6, 18 )
    depth = tt.warp( rng, n, depth, n * 0.02, 2, 8 )

    band = ( np.abs( x ) > 0.88 ) | ( np.abs( y ) > 0.88 )
    rim = depth[band].max() + 0.02
    h = np.clip( ( depth - rim ) / ( depth.max() - rim ), 0.0, 1.0 )
    # Round off the floor's last few per cent, so a nearly full puddle doesn't show a pinhole of dry ground.
    return ndimage.gaussian_filter( h, n / 512.0, mode="nearest" )


def colour_of( ground, h ):
    g = GROUNDS[ground]
    deep = np.array( g["deep"], float )
    shallow = np.array( g["shallow"], float )
    t = tt.smoothstep( 0.0, 0.6, h )[..., None]
    colour = shallow * ( 1 - t ) + deep * t
    # Alpha: the hollow, feathered over its outermost fraction so the rim isn't a hard pixel edge.
    alpha = tt.smoothstep( 0.0, 0.02, h )
    return colour, alpha


def save_png( path, array, mode ):
    Image.fromarray( np.clip( np.rint( array ), 0, 255 ).astype( np.uint8 ), mode ).save( path, optimize=True )


def texture_block( path ):
    return {
        "$compiler": "texture",
        "$source": "imagefile",
        "data": {
            "FilePath": path,
            "MaxSize": 4096,
            "ConvertHeightToNormals": False,
            "NormalScale": 1,
            "Rotate": 0,
            "FlipVertical": False,
            "FlipHorizontal": False,
            "Padding": { "Size": "0,0", "EdgeSize": "0,0" },
            "Sharpen": 0,
            "InvertColor": False,
            "Blur": 0,
            "Brightness": 1,
            "Contrast": 1,
            "Saturation": 1,
            "Hue": 0,
            "Colorize": False,
            "TargetColor": "0,1,0,1",
            "CacheToDisk": True,
        },
        "compiled": None,
    }


def write_decal( ground, shape ):
    name = f"puddle_{ground}_{shape}"
    decal = {
        "ColorTexture": texture_block( f"{DECAL_RESOURCE_DIR}/{name}_color.png" ),
        "NormalTexture": texture_block( f"{DECAL_RESOURCE_DIR}/puddle_flat_normal.png" ),
        "RoughMetalOcclusionTexture": texture_block( f"{DECAL_RESOURCE_DIR}/puddle_water_rmo.png" ),
        "HeightTexture": texture_block( f"{DECAL_RESOURCE_DIR}/puddle_shape_{shape}_height.png" ),
        "ParallaxStrength": 0,
        "CoverageAmount": 1,
        "Tint": "1,1,1,1",
        "ColorMix": GROUNDS[ground]["mix"],
        "Width": WIDTH,
        "Height": WIDTH,
        "__references": [],
        "__version": 0,
    }
    ( DECAL_DIR / f"{name}.decal" ).write_text( json.dumps( decal, indent=2 ), encoding="utf-8" )


def covered( h, fill, spread=0.1 ):
    """ Decals.hlsl's height coverage mask for a CoverageAmount of fill and a CoverageRange of spread. """
    if fill >= 1.0:
        return np.ones_like( h )
    thr = 1.0 - fill
    lo = thr - min( spread, thr, 1.0 - thr )
    return tt.smoothstep( lo, thr + 0.001, h )


def write_sheet( shapes, colours, path ):
    size = 320
    tiles = []
    grounds = {
        "paving": np.full( ( 3, ), 128.0 ),
        "mud": np.array( ( 112, 92, 70 ), float ),
    }
    for shape, h in enumerate( shapes ):
        row = [ Image.fromarray( np.clip( h * 255, 0, 255 ).astype( np.uint8 ), "L" ).convert( "RGB" ).resize( ( size, size ) ) ]
        for ground in GROUNDS:
            colour, alpha = colours[( ground, shape )]
            base = np.broadcast_to( grounds[ground], colour.shape ).copy()
            base += 10 * tt.spectral( np.random.default_rng( 5 ), h.shape[0], 1.5, 8, 128 )[..., None]
            mix = GROUNDS[ground]["mix"]
            for fill in ( 0.35, 0.7, 0.97 ):
                a = ( alpha * covered( h, fill ) )[..., None]
                wet = base * ( 1 - a * mix ) + colour * a * mix
                # The sky in the water: a mirror shows the overcast as a light grey sheen.
                wet = wet * ( 1 - 0.35 * a ) + 150 * 0.35 * a
                row.append( Image.fromarray( np.clip( wet, 0, 255 ).astype( np.uint8 ) ).resize( ( size, size ) ) )
        tiles.append( row )
    sheet = Image.new( "RGB", ( size * len( tiles[0] ), size * len( tiles ) ), ( 20, 20, 20 ) )
    for r, row in enumerate( tiles ):
        for c, tile in enumerate( row ):
            sheet.paste( tile, ( size * c, size * r ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


CODE_PATH = ROOT / "Code/World/PuddleShapes.cs"
CELLS = 32
RING_REACH = 4


def shape_tables( h ):
    """ The shape's four tables for the rings (see the docstring), as bytes: table k, then row (v), then column (u). """
    n = h.shape[0]
    cell = n / CELLS
    centres = ( ( np.arange( CELLS ) + 0.5 ) * cell ).astype( int )
    out = bytearray()
    for k in range( 1, RING_REACH + 1 ):
        r = k * cell
        span = int( np.ceil( r ) )
        yy, xx = np.mgrid[-span:span + 1, -span:span + 1]
        disc = xx * xx + yy * yy <= r * r
        low = ndimage.grey_erosion( h, footprint=disc, mode="constant", cval=0.0 )
        # Rounded down, so a cell never counts as wetter than it is.
        out += np.floor( low[np.ix_( centres, centres )] * 255.0 ).astype( np.uint8 ).tobytes()
    return bytes( out )


def write_code( shapes, path ):
    import base64
    lines = [
        "namespace Facepunch;",
        "",
        "// Written by Tools/puddle_textures.py from the puddles' height maps: don't edit it by hand.",
        "",
        "/// <summary>",
        "/// Where the water lies in each puddle shape, for the rain's rings (<see cref=\"RainPuddles\"/>). Each shape has four",
        f"/// {CELLS}x{CELLS} tables, a cell per 1/{CELLS} of the decal's width (rows down its v, columns along its u): the lowest",
        "/// height (0-255) within 1, 2, 3 and 4 cells of each cell's middle.",
        "/// </summary>",
        "public static class PuddleShapes",
        "{",
        f"\tpublic const int Cells = {CELLS};",
        f"\tpublic const int RingReach = {RING_REACH};",
        "",
        "\tprivate static readonly string[] Data =",
        "\t{",
    ]
    for h in shapes:
        lines.append( f"\t\t\"{base64.b64encode( shape_tables( h ) ).decode()}\"," )
    lines += [
        "\t};",
        "",
        "\tprivate static byte[][] _tables;",
        "",
        "\t/// <summary> A shape's tables: table k-1 (within k cells) starts at (k-1) * Cells * Cells. </summary>",
        "\tpublic static byte[] Tables( int shape )",
        "\t{",
        "\t\t_tables ??= Data.Select( Convert.FromBase64String ).ToArray();",
        "\t\treturn _tables[Math.Clamp( shape, 0, _tables.Length - 1 )];",
        "\t}",
        "",
        "\tpublic static int Count => Data.Length;",
        "}",
        "",
    ]
    path.write_text( "\n".join( lines ), encoding="utf-8", newline="\n" )
    print( f"wrote {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--size", type=int, default=512 )
    parser.add_argument( "--sheet", help="also write a contact sheet here" )
    parser.add_argument( "--out", help="write everything here instead of Assets (for trying things out)" )
    parser.add_argument( "--code-only", action="store_true", help="only write PuddleShapes.cs, from the height maps in Assets" )
    args = parser.parse_args()

    global DECAL_DIR
    if args.code_only:
        shapes = [ np.asarray( Image.open( DECAL_DIR / f"puddle_shape_{shape}_height.png" ).convert( "L" ), float ) / 255.0
                   for shape in range( SHAPES ) ]
        write_code( shapes, CODE_PATH )
        return

    if args.out:
        DECAL_DIR = Path( args.out )
    DECAL_DIR.mkdir( parents=True, exist_ok=True )
    n = args.size

    save_png( DECAL_DIR / "puddle_water_rmo.png", np.dstack( [ np.full( ( 16, 16 ), 0.02 * 255 ), np.zeros( ( 16, 16 ) ),
                                                                 np.full( ( 16, 16 ), 255.0 ) ] ), "RGB" )
    save_png( DECAL_DIR / "puddle_flat_normal.png", np.dstack( [ np.full( ( 16, 16 ), 128.0 ), np.full( ( 16, 16 ), 128.0 ),
                                                                   np.full( ( 16, 16 ), 255.0 ) ] ), "RGB" )

    shapes = []
    colours = {}
    for shape in range( SHAPES ):
        h = hollow( np.random.default_rng( 410 + shape ), n )
        shapes.append( h )
        save_png( DECAL_DIR / f"puddle_shape_{shape}_height.png", h * 255.0, "L" )
        for ground in GROUNDS:
            colour, alpha = colour_of( ground, h )
            colours[( ground, shape )] = ( colour, alpha )
            save_png( DECAL_DIR / f"puddle_{ground}_{shape}_color.png", np.dstack( [ colour, alpha * 255.0 ] ), "RGBA" )
            write_decal( ground, shape )
        wet = ( h > 0 ).mean()
        print( f"shape {shape}: {wet:.0%} of the square under water when full" )
    write_code( [ np.floor( np.clip( h, 0, 1 ) * 255.0 + 0.5 ) / 255.0 for h in shapes ],
                CODE_PATH if not args.out else DECAL_DIR / "PuddleShapes.cs" )

    if args.sheet:
        write_sheet( shapes, colours, args.sheet )


if __name__ == "__main__":
    main()
