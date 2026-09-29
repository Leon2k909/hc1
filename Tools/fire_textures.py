"""
Burnt ground for the fire system (Code/Weapons/Grenades/Fire/), drawn from scratch with numpy like
Tools/terrain_textures.py, whose helpers it uses.

    python Tools/fire_textures.py [--size 1024] [--sheet <png>]

- materials/terrain/burnt.tmat and its maps: the ash that burnt grass leaves on terrain. SurfaceFire paints it onto
  the terrain's control map at runtime where grass burnt out (SurfaceFire.Terrain.cs) and takes it off again when the
  fire goes, so it's never painted in the editor.
- decals/fire/burnt_patch.decal: the char where a patch of anything else burnt (a lawn, a wooden floor, fabric). The
  patches overlap their neighbours, 40 units apart, so their edges fade out gently.
- decals/fire/thermite_scorch.decal: where a thermite grenade burnt out. A crust of iron and slag under the canister
  (dark iron, white alumina, rust), the ground round it burnt black, and beads of iron spattered about, most within a
  hand's breadth or two and none past 0.75 m.

Albedos are real ones: charcoal and soot reflect 3-5% of the light (sRGB 50-63), freshly burnt grassland 5-10%, white
ash 30-50%. So the black here is dark grey in the picture, as it is in a photograph.

Decal colour maps hold the colour in RGB and how much it covers in alpha. RMO maps hold roughness, metalness and
ambient occlusion. Normal maps are OpenGL style (green up the picture), as s&box's own decals are (the impact decals'
normals against their height maps).

--sheet writes the ash material tiled 2x2 and both decals over grass and concrete, lit from the top left.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import terrain_textures as tt  # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
DECAL_DIR = ROOT / "Assets/decals/fire"
DECAL_RESOURCE_DIR = "decals/fire"


# ---------------------------------------------------------------------------------------------------------------------
# The ash on terrain

CHAR = np.array( ( 50, 47, 44 ), float )          # black ash and charcoal, ~3% albedo
SCORCHED_SOIL = np.array( ( 72, 62, 52 ), float )  # the soil under it, darkened by the heat
GREY_ASH = np.array( ( 116, 112, 106 ), float )
WHITE_ASH = np.array( ( 172, 168, 160 ), float )   # thatch that burnt right through
SINGED = np.array( ( 128, 108, 72 ), float )       # the odd stem the flames passed over


def burnt( rng, n ):
    """ Grass after a fire: black ash over nearly all of it, the scorched soil showing where it's thin, faint grey
    patches where the thatch lay thickest, the tussocks' charred stubble standing in clumps, and grey-white ash stems
    lying in drifts where thatch burnt right through and kept its shape. 1 px is 2.4 mm. """
    broad = tt.spectral( rng, n, 2.8, 3, 20 )
    medium = tt.spectral( rng, n, 2.0, 14, 120 )
    grain = tt.spectral( rng, n, 1.0, 120, n / 2 )

    crust = tt.smoothstep( -1.8, -0.2, tt.warp( rng, n, tt.spectral( rng, n, 2.4, 4, 40 ), 20 ) + 0.3 * grain )
    colour = SCORCHED_SOIL * ( 1 - crust[..., None] ) + CHAR * crust[..., None]
    colour *= ( 1.0 + 0.05 * broad + 0.06 * medium + 0.1 * grain )[..., None]
    grey = 0.4 * tt.smoothstep( 0.3, 1.8, tt.warp( rng, n, tt.spectral( rng, n, 2.4, 4, 40 ), 20 ) )
    colour = colour * ( 1 - grey[..., None] ) + GREY_ASH * grey[..., None]
    height = 0.12 + 0.03 * broad + 0.02 * medium + 0.015 * grain + 0.03 * grey

    strokes = tt.Strokes( colour, np.clip( height, 0, 1 ), ss=3 )
    scale = ( n / 1024 ) ** 2

    # Ash stems, broken up as they lie, more of them in drifts.
    drift = tt.smoothstep( -0.4, 1.2, tt.warp( rng, n, tt.spectral( rng, n, 2.3, 6, 64 ), 18 ) )
    placed = 0
    while placed < int( 2200 * scale ):
        x, y = rng.uniform( 0, n, 2 )
        if rng.uniform() > 0.1 + 0.9 * drift[int( y ) % n, int( x ) % n]:
            continue
        placed += 1
        points = tt.curve_points( x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 10, 34 ), rng.normal( 0, 0.25 ), 5 )
        tone = WHITE_ASH * rng.uniform( 0.8, 1.0 ) if rng.uniform() < 0.55 else GREY_ASH * rng.uniform( 0.9, 1.15 )
        w = rng.uniform( 0.55, 1.0 )
        for k in range( len( points ) - 1 ):
            if rng.uniform() < 0.75:
                shade = tone * rng.uniform( 0.9, 1.05 )
                strokes.blade( points[k:k + 2], [ w ], [ shade ], [ 0.26 ] )

    # Tussocks: the charred stubble of each clump standing 2-4 cm, leaning out from its crown, some tips grey.
    for _ in range( int( 420 * scale ) ):
        x, y = rng.uniform( 0, n, 2 )
        radius = rng.uniform( 6.0, 16.0 )
        strokes.dot( x, y, radius * 0.55, radius * 0.5, CHAR * rng.uniform( 0.7, 0.85 ), 0.35 )
        for _ in range( int( radius * 2.5 ) ):
            a = rng.uniform( 0, 2 * math.pi )
            r0 = radius * 0.55 * math.sqrt( rng.uniform() )
            angle = a + rng.normal( 0, 0.5 )
            points = tt.curve_points( x + math.cos( a ) * r0, y + math.sin( a ) * r0, angle, rng.uniform( 3.0, 8.0 ),
                                      rng.normal( 0, 0.3 ), 2 )
            base = CHAR * rng.uniform( 0.6, 0.85 )
            tip = GREY_ASH * rng.uniform( 0.7, 1.0 ) if rng.uniform() < 0.35 else CHAR * rng.uniform( 0.9, 1.15 )
            w = rng.uniform( 0.9, 1.5 )
            strokes.blade( points, [ w * 1.2, w * 0.9 ], [ base, tip ], [ rng.uniform( 0.6, 0.8 ), 0.55 ] )

    # Charred stems lying flat, and the odd one the flames only singed.
    for _ in range( int( 700 * scale ) ):
        x, y = rng.uniform( 0, n, 2 )
        points = tt.curve_points( x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 8, 26 ), rng.normal( 0, 0.3 ), 3 )
        singed = rng.uniform() < 0.06
        tone = SINGED * rng.uniform( 0.8, 1.05 ) if singed else CHAR * rng.uniform( 0.7, 1.1 )
        w = rng.uniform( 0.6, 1.2 )
        strokes.blade( points, [ w ] * 3, [ tone * f for f in ( 0.9, 1.0, 1.05 ) ], [ 0.3 ] * 3 )

    # Flakes of char.
    for _ in range( int( 2500 * scale ) ):
        x, y = rng.uniform( 0, n, 2 )
        r = rng.uniform( 0.6, 1.8 )
        strokes.dot( x, y, r, r * rng.uniform( 0.5, 1.0 ), CHAR * rng.uniform( 0.6, 0.9 ), 0.22 )
    colour, height, cover = strokes.result()

    height = tt.blur( height, 0.5 )
    rough = np.clip( 0.96 - 0.08 * cover, 0.85, 1.0 )
    ao = tt.cavity_ao( height, ( ( 1.5, 2.0 ), ( 8.0, 1.2 ) ), 1.0 )
    return tt.shaded( colour, ao ), rough, height, ao, 3.0


# ---------------------------------------------------------------------------------------------------------------------
# Decals. Each drawing returns colour (0..255 sRGB), alpha, roughness, metalness, ao (0..1) and a height field for the
# normals (None for a flat one), over a square of n px.

def radial( n ):
    """ Each px's distance from the middle (1 at the square's edge) and its angle. """
    c = ( np.arange( n ) + 0.5 ) / n * 2.0 - 1.0
    x, y = np.meshgrid( c, c )
    return np.hypot( x, y ), np.arctan2( y, x )


def ragged( rng, n, r, theta, amount ):
    """ The radius pushed in and out round the circle, so edges aren't round, and roughened by finer noise. """
    wobble = sum( rng.normal( 0, amount / k ) * np.cos( k * theta + rng.uniform( 0, 2 * math.pi ) ) for k in range( 2, 9 ) )
    fine = tt.spectral( rng, n, 2.0, 8, 96 ) * amount * 0.3
    return r * ( 1.0 + wobble ) + fine


def burnt_patch( rng, n ):
    """ Char where a patch of something burnt: black in the middle with flecks of grey ash, a ring of dark brown where
    it only scorched, then a brown halo fading into the ground. """
    r, theta = radial( n )
    d = ragged( rng, n, r, theta, 0.08 )
    grain = tt.spectral( rng, n, 1.0, 60, n / 2 )
    medium = tt.spectral( rng, n, 2.0, 8, 64 )

    char = 1.0 - tt.smoothstep( 0.32, 0.55, d + 0.05 * medium )
    scorch = 1.0 - tt.smoothstep( 0.5, 0.78, d + 0.04 * medium )
    halo = 1.0 - tt.smoothstep( 0.65, 0.97, d )

    colour = np.empty( ( n, n, 3 ) )
    colour[:] = ( 92, 72, 52 )
    colour = colour * ( 1 - scorch[..., None] ) + np.array( ( 60, 46, 36 ) ) * scorch[..., None]
    colour = colour * ( 1 - char[..., None] ) + CHAR * char[..., None]
    colour *= ( 1.0 + 0.08 * grain + 0.05 * medium )[..., None]

    # Grey ash flecks in the char.
    flecks = tt.smoothstep( 1.4, 2.4, tt.spectral( rng, n, 0.8, 40, n / 2 ) ) * char
    colour = colour * ( 1 - 0.7 * flecks[..., None] ) + GREY_ASH * 0.7 * flecks[..., None]

    alpha = np.clip( 0.92 * char + 0.75 * ( scorch - char ) + 0.35 * ( halo - scorch ), 0.0, 1.0 )
    alpha *= np.clip( 1.0 + 0.08 * grain, 0.0, 1.0 )
    alpha *= 1.0 - tt.smoothstep( 0.9, 1.0, r )          # nothing at the square's edge
    rough = 0.86 + 0.08 * char
    metal = np.zeros_like( r )
    ao = 1.0 - 0.08 * char
    return colour, alpha, rough, metal, ao, None


IRON = np.array( ( 66, 64, 62 ), float )
SLAG_DARK = np.array( ( 40, 37, 35 ), float )
ALUMINA = np.array( ( 184, 180, 170 ), float )
RUST = np.array( ( 122, 72, 42 ), float )


def thermite_scorch( rng, n ):
    """ Where a thermite grenade burnt out: a crust of iron and slag under the canister, the ground burnt black round
    it, and beads of iron spattered about. 1 in the picture is 0.75 m. """
    r, theta = radial( n )
    grain = tt.spectral( rng, n, 1.0, 80, n / 2 )
    medium = tt.spectral( rng, n, 2.0, 10, 80 )

    # The burnt ground: black soot out to ~0.35 m, fading through scorched brown to ~0.6 m.
    d = ragged( rng, n, r, theta, 0.1 )
    soot = 1.0 - tt.smoothstep( 0.3, 0.55, d + 0.05 * medium )
    scorch = 1.0 - tt.smoothstep( 0.45, 0.85, d + 0.05 * medium )
    colour = np.empty( ( n, n, 3 ) )
    colour[:] = ( 84, 66, 50 )
    colour = colour * ( 1 - soot[..., None] ) + np.array( ( 42, 39, 37 ) ) * soot[..., None]
    colour *= ( 1.0 + 0.07 * grain + 0.05 * medium )[..., None]
    alpha = 0.9 * soot + 0.55 * ( scorch - soot )
    rough = 0.9 + 0.0 * r
    metal = np.zeros_like( r )
    height = np.zeros_like( r )

    # White ash blown out round the burning point, in streaks.
    streaks = tt.smoothstep( 0.8, 1.8, np.cos( theta * rng.integers( 9, 15 ) + 2.0 * tt.spectral( rng, n, 2.0, 3, 24 ) )
                             + tt.spectral( rng, n, 1.5, 20, 200 ) ) * tt.smoothstep( 0.1, 0.25, r ) * ( 1.0 - tt.smoothstep( 0.3, 0.7, d ) )
    colour = colour * ( 1 - 0.5 * streaks[..., None] ) + np.array( ( 150, 146, 140 ) ) * 0.5 * streaks[..., None]

    # The crust: a lumpy, pitted cake of iron and slag ~25 cm across, white alumina in its hollows, rust at its rim.
    p = ragged( rng, n, r, theta, 0.12 )
    crust = 1.0 - tt.smoothstep( 0.13, 0.18, p )
    lumps = tt.spectral( rng, n, 2.2, 12, 160 )
    pits = tt.smoothstep( 0.9, 1.6, tt.spectral( rng, n, 1.6, 40, 240 ) )
    cake = crust * ( 0.55 + 0.2 * lumps - 0.3 * pits ) * np.sqrt( np.clip( 1.0 - ( p / 0.2 ) ** 2, 0.0, 1.0 ) )
    hollows = tt.smoothstep( 0.7, 1.5, -lumps ) * crust
    rim = tt.smoothstep( 0.08, 0.17, p ) * crust
    iron_lumps = tt.smoothstep( -0.2, 1.0, lumps )
    crust_colour = SLAG_DARK * ( 1 - iron_lumps[..., None] ) + IRON * ( 1.0 + 0.1 * lumps )[..., None] * iron_lumps[..., None]
    crust_colour = crust_colour * ( 1 - 0.5 * pits[..., None] ) + SLAG_DARK * 0.8 * 0.5 * pits[..., None]
    crust_colour = crust_colour * ( 1 - 0.7 * hollows[..., None] ) + ALUMINA * 0.7 * hollows[..., None]
    crust_colour = crust_colour * ( 1 - 0.6 * rim[..., None] ) + RUST * 0.6 * rim[..., None]
    colour = colour * ( 1 - crust[..., None] ) + crust_colour * crust[..., None]
    alpha = alpha * ( 1 - crust ) + crust
    iron = crust * iron_lumps * ( 1.0 - hollows ) * ( 1.0 - 0.6 * rim )
    rough = rough * ( 1 - crust ) + ( 0.5 + 0.35 * hollows + 0.2 * pits ) * crust
    metal = metal * ( 1 - crust ) + 0.55 * iron
    height = np.maximum( height, cake )

    # Beads of iron: a dome each, most close in (0.35 m on average, as ThermiteGrenade spatters them).
    pad = 4
    picture = Image.new( "L", ( n * pad, n * pad ), 0 )
    domes = np.zeros( ( n, n ) )
    draw = ImageDraw.Draw( picture )
    beads = []
    for _ in range( 900 ):
        metres = min( rng.exponential( 0.3 ), 0.72 )
        angle = rng.uniform( 0, 2 * math.pi )
        radius_px = rng.uniform( 0.6, 2.4 ) * ( 1.6 if metres < 0.15 else 1.0 ) * n / 1024
        cx = n / 2 + math.cos( angle ) * metres / 0.75 * n / 2
        cy = n / 2 + math.sin( angle ) * metres / 0.75 * n / 2
        beads.append( ( cx, cy, radius_px ) )
        draw.ellipse( [ ( cx - radius_px ) * pad, ( cy - radius_px ) * pad, ( cx + radius_px ) * pad, ( cy + radius_px ) * pad ], fill=255 )
    bead = np.asarray( picture.reduce( pad ), float ) / 255.0
    for cx, cy, radius_px in beads:
        x0, x1 = int( max( cx - radius_px - 1, 0 ) ), int( min( cx + radius_px + 2, n ) )
        y0, y1 = int( max( cy - radius_px - 1, 0 ) ), int( min( cy + radius_px + 2, n ) )
        yy, xx = np.mgrid[y0:y1, x0:x1]
        q = np.hypot( xx + 0.5 - cx, yy + 0.5 - cy ) / max( radius_px, 0.5 )
        domes[y0:y1, x0:x1] = np.maximum( domes[y0:y1, x0:x1], np.sqrt( np.clip( 1.0 - q * q, 0.0, 1.0 ) ) * 0.5 )
    rusty = tt.smoothstep( 0.3, 1.2, tt.spectral( rng, n, 1.5, 30, 200 ) )
    bead_colour = IRON * ( 0.85 + 0.3 * domes )[..., None]
    bead_colour = bead_colour * ( 1 - 0.5 * rusty[..., None] ) + RUST * 0.5 * rusty[..., None]
    colour = colour * ( 1 - bead[..., None] ) + bead_colour * bead[..., None]
    alpha = np.maximum( alpha, bead )
    rough = rough * ( 1 - bead ) + ( 0.35 + 0.3 * rusty ) * bead
    metal = metal * ( 1 - bead ) + ( 0.7 - 0.5 * rusty ) * bead
    height = np.maximum( height, domes )

    alpha *= 1.0 - tt.smoothstep( 0.92, 1.0, r )
    ao = np.clip( 1.0 - 0.6 * np.maximum( 0.0, tt.blur( height, 3.0 ) - height ) * 4.0, 0.4, 1.0 )
    return colour, np.clip( alpha, 0, 1 ), np.clip( rough, 0, 1 ), np.clip( metal, 0, 1 ), ao, height


# name: ( draw, px, width in units, seed, normal strength )
DECALS = {
    "burnt_patch": ( burnt_patch, 512, 64, 31, 0.0 ),
    "thermite_scorch": ( thermite_scorch, 1024, 60, 32, 6.0 ),
}


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


def write_decal( name ):
    draw, n, width, seed, strength = DECALS[name]
    rng = np.random.default_rng( seed )
    colour, alpha, rough, metal, ao, height = draw( rng, n )

    DECAL_DIR.mkdir( parents=True, exist_ok=True )
    rgba = np.dstack( [ np.clip( np.rint( colour ), 0, 255 ), np.clip( np.rint( alpha * 255 ), 0, 255 ) ] ).astype( np.uint8 )
    Image.fromarray( rgba, "RGBA" ).save( DECAL_DIR / f"{name}_color.png", optimize=True )
    rmo = np.dstack( [ rough, metal, ao ] )
    Image.fromarray( np.clip( np.rint( rmo * 255 ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( DECAL_DIR / f"{name}_rmo.png", optimize=True )

    normal_block = None
    normal = None
    if height is not None and strength > 0:
        normal = tt.normal_map( tt.blur( height, 0.7 ), strength * n / 1024.0 )
        normal[..., 1] *= -1.0                              # OpenGL style: green up the picture
        Image.fromarray( np.clip( np.rint( ( normal * 0.5 + 0.5 ) * 255 ), 0, 255 ).astype( np.uint8 ), "RGB" ).save(
            DECAL_DIR / f"{name}_normal.png", optimize=True )
        normal_block = texture_block( f"{DECAL_RESOURCE_DIR}/{name}_normal.png" )

    decal = {
        "ColorTexture": texture_block( f"{DECAL_RESOURCE_DIR}/{name}_color.png" ),
        "NormalTexture": normal_block,
        "RoughMetalOcclusionTexture": texture_block( f"{DECAL_RESOURCE_DIR}/{name}_rmo.png" ),
        "HeightTexture": None,
        "ParallaxStrength": 0,
        "Tint": "1,1,1,1",
        "ColorMix": 1,
        "Width": width,
        "Height": width,
        "__references": [],
        "__version": 0,
    }
    ( DECAL_DIR / f"{name}.decal" ).write_text( json.dumps( decal, indent=2 ), encoding="utf-8" )
    print( f"wrote decal {name}: {n}px over {width} units" )
    return colour, alpha, normal


# ---------------------------------------------------------------------------------------------------------------------

def write_sheet( ash, decals, path ):
    colour, normal, _ = ash
    ash_tile = Image.fromarray( tt.lit( np.tile( colour, ( 2, 2, 1 ) ), np.tile( normal, ( 2, 2, 1 ) ) ).astype( np.uint8 ) ).resize( ( 768, 768 ), Image.LANCZOS )
    grass = np.asarray( Image.open( ROOT / "Assets/materials/terrain/meadow_dry_color.png" ).convert( "RGB" ), float )
    rows = [ ash_tile ]
    for name, ( decal_colour, alpha, decal_normal ) in decals.items():
        n = decal_colour.shape[0]
        for ground in ( np.asarray( Image.fromarray( grass.astype( np.uint8 ) ).resize( ( n, n ) ), float ),
                        np.full( ( n, n, 3 ), ( 128, 126, 122 ), float ) ):
            lit_decal = decal_colour if decal_normal is None else tt.lit( decal_colour, decal_normal * np.array( ( 1, -1, 1 ) ) )
            mixed = ground * ( 1 - alpha[..., None] ) + lit_decal * alpha[..., None]
            rows.append( Image.fromarray( np.clip( mixed, 0, 255 ).astype( np.uint8 ) ).resize( ( 768, 768 ), Image.LANCZOS ) )
    sheet = Image.new( "RGB", ( 768 * len( rows ), 768 ), ( 20, 20, 20 ) )
    for k, row in enumerate( rows ):
        sheet.paste( row, ( 768 * k, 0 ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--size", type=int, default=1024, help="the ash material's size in px" )
    parser.add_argument( "--sheet", help="also write a lit contact sheet here" )
    parser.add_argument( "--out", help="write everything here instead of Assets (for trying things out)" )
    args = parser.parse_args()

    global DECAL_DIR
    if args.out:
        tt.OUT_DIR = Path( args.out )
        DECAL_DIR = Path( args.out )

    tt.MATERIALS["burnt"] = ( burnt, 96, "surfaces/dirt.surface", 21 )
    ash = tt.write_material( "burnt", args.size )
    decals = { name: write_decal( name ) for name in DECALS }
    if args.sheet:
        write_sheet( ash, decals, args.sheet )


if __name__ == "__main__":
    main()
