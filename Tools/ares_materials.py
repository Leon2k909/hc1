"""
Ares's materials, drawn with numpy into Assets/materials/ares/: the Ares Facility's atmosphere-processing plant on Mars
(Tools/ares_map.py builds the map), and the Martian sky over it.

    python Tools/ares_materials.py [names ...] [--out <dir>] [--sheet <png>] [--scale 0.5]

The look follows the user's reference picture (2026-10-14): a dark industrial hall of steel plate and charcoal wall
panels, polished floors that hold the lights, brass trim on the railings, black hard cases stencilled MARS / BIGGER /
CLEANER / BRIGHTER, light concrete walls carrying the facility's posters, and the ATMOS PROCESSING column glowing
orange through its glass. Everything is drawn here at its real size; the lettering is the reference's, in the project's
own Dinish and Chakra Petch fonts. ARES FACILITY and its red triangle logo are the picture's made-up company.

Tiling materials (their tile in inches is TILES):
    ar_floor        48 in steel deck plates, bolted, polished where people walk, dirt in the seams
    ar_wall         charcoal steel wall panels, 48 x 96, with pressed borders and rivets
    ar_concrete     light cast concrete, form-tie holes every 24 in, joints every 96
    ar_steel        dark painted structural steel
    ar_brass        brushed brass trim
    ar_grating      steel bar grating (bridges, stair treads)
    ar_hazard       worn yellow and black stripes
    ar_regolith     Martian dust and pebbles (the land outside)
    ar_rock         layered red rock
    ar_tower        the distant spires' dark cladding with lit windows (self-lit)

Atlases (ares_map maps faces onto their regions with region_uv):
    ar_crate        the hard cases: CRATE regions
    ar_signs        posters and banners: SIGN regions
    ar_signs_lit    lit door signs: LIT regions (self-lit)
    ar_screens      control-room screens: SCREEN regions (self-lit)
    ar_plasma       the column's plasma; slowly circulating custom shader, with dark amber pockets and a small pulse
    ar_dome         a habitat dome's lattice, u round it and v up (self-lit cells)

Flat paints (PAINTED) and lights (EMISSIVE), and the glass (GLASS, glass.shader).
`outpost` writes the private ar_ext_* thermal shells, dusty metals, glazing, shielded lamps and painted sign atlas
for Tools/ares_outpost.py, without changing the facility's paints.

The sky (`sky`): a Martian evening, a near black sky over a rust haze at the horizon, the stars and the two moons, as
belltower_sky's panorama (EXR, its write_exr and wrapping), Assets/materials/ares/sky/ares_sky.exr and .vmat.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import terrain_textures as T  # noqa: E402
import boxyard_materials as BX  # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/ares"
RESOURCE_DIR = "materials/ares"
DEFAULT_AO = "materials/default/default_ao.tga"
DEFAULT_NORMAL = "materials/default/default_normal.tga"
FONT_BOLD = ROOT / "Assets/fonts/Dinish-Bold.ttf"
FONT_TECH = ROOT / "Assets/fonts/ChakraPetch-Bold.ttf"
FONT_TECH_MEDIUM = ROOT / "Assets/fonts/ChakraPetch-SemiBold.ttf"

smoothstep = T.smoothstep
lin = BX.lin
mix = BX.mix
noise = BX.noise
normals = BX.normals
Region = BX.Region

SCALE = 1.0


def px( n ):
    return max( 8, int( round( n * SCALE ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Tiles and atlas regions (shared with ares_map)

TILES = { "ar_floor": 192.0, "ar_wall": 192.0, "ar_concrete": 192.0, "ar_steel": 64.0, "ar_brass": 48.0,
          "ar_grating": 24.0, "ar_hazard": 24.0, "ar_regolith": 640.0, "ar_rock": 1024.0, "ar_tower": 256.0 }
TILES.update( { name: 192.0 for name in ( "ar_ext_shell", "ar_ext_metal", "ar_ext_dark", "ar_ext_base", "ar_ext_ochre" ) } )

# The hard case's faces, at the standard case's size (48 long, 30 high, 32 deep): pixels x, y, w, h in a 2048 atlas.
CASE = ( 48.0, 30.0, 32.0 )
CRATE_ATLAS = ( 2048, 2048 )
CRATE = { "front_text": ( 0, 0, 1024, 640 ), "front_plain": ( 1024, 0, 1024, 640 ), "side": ( 0, 640, 683, 640 ),
          "side_logo": ( 683, 640, 683, 640 ), "end_plain": ( 1366, 640, 682, 640 ), "top": ( 0, 1280, 1024, 683 ),
          "top_ribs": ( 1024, 1280, 1024, 683 ) }

SIGN_ATLAS = ( 4096, 4096 )
SIGN = { "poster_ares": ( 0, 0, 1536, 1920 ), "band_atmos": ( 1536, 0, 2048, 1024 ),
         "banner_humanity": ( 0, 1920, 640, 1920 ), "banner_habitat": ( 640, 1920, 640, 1920 ),
         "poster_redplanet": ( 1536, 1024, 2048, 768 ), "logo": ( 1280, 1920, 1024, 1024 ),
         "poster_mars": ( 2304, 1920, 1280, 1024 ), "plate_cargo": ( 1280, 2944, 1536, 384 ),
         "plate_rover": ( 1280, 3328, 1536, 384 ), "plate_core": ( 2816, 2944, 1280, 384 ),
         "plate_observation": ( 2816, 3328, 1280, 384 ), "stripe_warning": ( 1280, 3712, 2816, 384 ),
         "band_atmos_back": ( 3584, 0, 512, 1024 ), "zone_03": ( 3584, 1024, 512, 448 ),
         "zone_b": ( 3584, 1472, 512, 448 ) }

LIT_ATLAS = ( 2048, 1024 )
LIT = { "sector03": ( 0, 0, 1024, 256 ), "habitatb": ( 1024, 0, 1024, 256 ), "observation": ( 0, 256, 1024, 256 ),
        "cargo": ( 1024, 256, 1024, 256 ), "rover": ( 0, 512, 1024, 256 ), "airlock03": ( 1024, 512, 1024, 256 ),
        "airlock07": ( 0, 768, 1024, 256 ), "exit": ( 1024, 768, 1024, 256 ) }
LIT_TEXT = { "sector03": ( "SECTOR 03", ">" ), "habitatb": ( "HABITAT B", ">" ), "observation": ( "OBSERVATION DECK", "" ),
             "cargo": ( "CARGO CONCOURSE", ">" ), "rover": ( "ROVER BAY", "" ), "airlock03": ( "AIRLOCK 03", "" ),
             "airlock07": ( "AIRLOCK 07", "" ), "exit": ( "ATMOS HALL", ">" ) }

SCREEN_ATLAS = ( 2048, 1024 )
SCREEN = { f"screen{k}": ( ( k % 4 ) * 512, ( k // 4 ) * 512, 512, 512 ) for k in range( 8 ) }


def region_uv( regions, atlas, name, s, t ):
    """ ( u, v ) in an atlas for ( s, t ) 0..1 across a region (s to the right, t up), v up from the picture's foot. """
    x, y, w, h = regions[name]
    return ( x + s * w ) / atlas[0], 1.0 - ( y + ( 1.0 - t ) * h ) / atlas[1]


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers

def periodic_hash( ix, iy, seed ):
    """ A steady 0..1 per integer cell. """
    h = ( ix.astype( np.int64 ) * 374761393 + iy.astype( np.int64 ) * 668265263 + seed * 2147483647 ) & 0xFFFFFFFF
    h = ( ( h ^ ( h >> 13 ) ) * 1274126177 ) & 0xFFFFFFFF
    return ( ( h ^ ( h >> 16 ) ) & 0xFFFF ).astype( np.float32 ) / 65535.0


def grid( n, tile ):
    """ Inch coordinates of a tile's pixel centres, x across and y down. """
    c = ( np.arange( n, dtype=np.float32 ) + 0.5 ) / n * tile
    return np.meshgrid( c, c )


def font( path, size ):
    return ImageFont.truetype( str( path ), max( 6, int( size ) ) )


def fit_cap( text, path, cap, tracking, max_width ):
    """ The cap height (px) at which text is at most max_width px wide. """
    f = font( path, 100 / 0.72 )
    width = ( sum( f.getlength( ch ) for ch in text ) + tracking * 100 * max( 0, len( text ) - 1 ) ) / 100
    return min( cap, max_width / max( width, 1e-6 ) )


def text_layer( shape, items, ss=2 ):
    """ Coverage 0..1 of lettering: items ( text, font path, cap height px, x px, y px (top of the capitals), anchor
    'l'/'m'/'r', tracking (share of the cap height) ). """
    h, w = shape
    image = Image.new( "L", ( w * ss, h * ss ), 0 )
    draw = ImageDraw.Draw( image )
    for item in items:
        text, path, cap, x, y, anchor, tracking = item[:7]
        if len( item ) > 7 and item[7]:
            cap = fit_cap( text, path, cap, tracking, item[7] )
        f = font( path, cap * ss / 0.72 )
        top = f.getbbox( "H" )[1]
        gap = tracking * cap * ss
        widths = [ f.getlength( ch ) for ch in text ]
        total = sum( widths ) + gap * max( 0, len( text ) - 1 )
        cx = x * ss - ( total / 2 if anchor == "m" else total if anchor == "r" else 0 )
        for ch, cw in zip( text, widths ):
            draw.text( ( cx, y * ss - top ), ch, font=f, fill=255 )
            cx += cw + gap
    a = np.asarray( image, np.float32 ) / 255.0
    return a.reshape( h, ss, w, ss ).mean( axis=( 1, 3 ) )


def shapes_layer( shape, polygons, ss=3 ):
    h, w = shape
    image = Image.new( "L", ( w * ss, h * ss ), 0 )
    draw = ImageDraw.Draw( image )
    for points, value in polygons:
        draw.polygon( [ ( x * ss, y * ss ) for x, y in points ], fill=int( 255 * value ) )
    a = np.asarray( image, np.float32 ) / 255.0
    return a.reshape( h, ss, w, ss ).mean( axis=( 1, 3 ) )


def logo_polygons( x, y, size ):
    """ The facility's mark: a red triangle with a chevron notch out of its foot (an A with no crossbar), size across,
    its apex at ( x, y ) in pixels. """
    hgt = size * 0.86
    outer = [ ( x, y ), ( x + size / 2, y + hgt ), ( x - size / 2, y + hgt ) ]
    notch = [ ( x, y + hgt * 0.52 ), ( x + size * 0.27, y + hgt ), ( x - size * 0.27, y + hgt ) ]
    return [ ( outer, 1.0 ), ( notch, 0.0 ) ]


def wear( rng, shape, amount, ppi=8.0, size=6.0 ):
    """ Scuffs and flaking 0..1, for worn lettering and paint. """
    n1 = noise( rng, shape, ( ppi, ppi ), 1.6, size, 0.15 )
    n2 = noise( rng, shape, ( ppi, ppi ), 2.4, size * 4, 1.0 )
    return np.clip( smoothstep( 2.4 - amount * 2.0, 3.2 - amount * 2.0, n1 + 0.5 * n2 ), 0, 1 )


# ---------------------------------------------------------------------------------------------------------------------
# Tiling materials

def floor_plates( n=None ):
    """ 48 in steel deck plates: recessed seams, countersunk bolts, polished paths, grime in the seams. """
    n = n or px( 2048 )
    tile = TILES["ar_floor"]
    ppi = n / tile
    rng = np.random.default_rng( 301 )
    x, y = grid( n, tile )
    plate = 48.0
    ix, iy = np.floor( x / plate ).astype( int ), np.floor( y / plate ).astype( int )
    fx, fy = x - ix * plate, y - iy * plate
    edge = np.minimum( np.minimum( fx, plate - fx ), np.minimum( fy, plate - fy ) )
    seam = 1.0 - smoothstep( 0.18, 0.42, edge )
    tone = periodic_hash( ix % 4, iy % 4, 7 )
    height = -0.06 * seam
    # Bolts: three along each edge, 2.5 in in.
    bolts = np.zeros_like( x )
    for bx_ in ( 2.5, 24.0, 45.5 ):
        for by_ in ( 2.5, 24.0, 45.5 ):
            if bx_ == 24.0 and by_ == 24.0:
                continue
            d = np.hypot( fx - bx_, fy - by_ )
            bolts = np.maximum( bolts, 1.0 - smoothstep( 0.32, 0.42, d ) )
            height += 0.03 * np.clip( 1.0 - d / 0.32, 0, 1 ) ** 0.5 * ( d < 0.42 )
    ring = np.zeros_like( x )
    for bx_ in ( 2.5, 24.0, 45.5 ):
        for by_ in ( 2.5, 24.0, 45.5 ):
            if bx_ == 24.0 and by_ == 24.0:
                continue
            d = np.hypot( fx - bx_, fy - by_ )
            ring = np.maximum( ring, np.exp( -( ( d - 0.45 ) / 0.07 ) ** 2 ) )
    big = noise( rng, ( n, n ), ( ppi, ppi ), 2.6, 96, 6 )
    mid = noise( rng, ( n, n ), ( ppi, ppi ), 2.0, 12, 0.6 )
    fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.0, 1.0, 0.1 )
    # Brushed scratches along each plate's own way (alternating).
    scratch_a = noise( rng, ( n, n ), ( ppi * 0.08, ppi ), 1.2, 4.0, 0.2 )
    scratch_b = noise( rng, ( n, n ), ( ppi, ppi * 0.08 ), 1.2, 4.0, 0.2 )
    scratch = np.where( ( ix + iy ) % 2 == 0, scratch_a, scratch_b )
    base = lin( ( 58, 56, 54 ) )
    colour = base[None, None, :] * ( 0.86 + 0.22 * tone + 0.06 * big + 0.03 * mid + 0.02 * fine )[..., None]
    polish = smoothstep( 0.2, 1.8, big + 0.4 * mid )
    colour = mix( colour, lin( ( 92, 90, 86 ) ), polish * 0.35 )
    colour = mix( colour, lin( ( 104, 102, 98 ) ), smoothstep( 1.2, 2.6, scratch ) * 0.3 )
    dirt = np.clip( seam * 0.9 + 0.5 * ring + smoothstep( 0.8, 2.6, -big + 0.5 * mid ) * 0.5, 0, 1 )
    colour = mix( colour, lin( ( 30, 26, 22 ) ), dirt * 0.8 )
    # Abraded plate lips and walk-polished grain reveal clean steel beneath worn paint.
    lip = smoothstep( 0.25, 0.45, edge ) * ( 1.0 - smoothstep( 0.55, 1.05, edge ) )
    abrasion = ( 1.0 - smoothstep( 0.35, 1.7, edge ) ) * smoothstep( 0.1, 2.0, scratch + 0.35 * mid )
    grain = smoothstep( 0.85, 2.25, scratch + 0.25 * mid ) * ( 1.0 - seam )
    colour = mix( colour, lin( ( 128, 124, 116 ) ), np.clip( abrasion * 0.55 + lip * 0.3 + grain * 0.12, 0, 1 ) )
    # A little red Martian dust gathers at plate seams and fasteners.
    dust = ( 1.0 - smoothstep( 0.2, 2.4, edge ) ) * smoothstep( 0.2, 2.3, -mid + 0.3 * big )
    colour = mix( colour, lin( ( 112, 70, 51 ) ), np.clip( dust * 0.28 + ring * 0.08, 0, 0.3 ) )
    colour = mix( colour, lin( ( 120, 118, 112 ) ), bolts * 0.45 )
    rough = ( 0.34 + 0.06 * tone - 0.12 * polish + 0.35 * dirt + 0.03 * fine
              + 0.05 * smoothstep( 1.0, 2.0, scratch ) - 0.11 * abrasion - 0.04 * grain + 0.2 * dust )
    height += 0.018 * lip - 0.006 * abrasion - 0.003 * grain + 0.004 * scratch + 0.006 * fine
    return T.linear_to_srgb( colour ), np.clip( rough, 0.08, 1 ), normals( height, ( ppi, ppi ) )


def wall_panels( n=None ):
    """ Charcoal steel wall panels 48 wide and 96 high, each with a pressed border, rivets down the joints and grime
    run down from the joints. """
    n = n or px( 2048 )
    tile = TILES["ar_wall"]
    ppi = n / tile
    rng = np.random.default_rng( 302 )
    x, y = grid( n, tile )
    pw, ph = 48.0, 96.0
    ix, iy = np.floor( x / pw ).astype( int ), np.floor( y / ph ).astype( int )
    fx, fy = x - ix * pw, y - iy * ph
    ex = np.minimum( fx, pw - fx )
    ey = np.minimum( fy, ph - fy )
    edge = np.minimum( ex, ey )
    seam = 1.0 - smoothstep( 0.2, 0.5, edge )
    # The pressed border: a 3 in frame raised round a flat field.
    frame = smoothstep( 2.6, 3.2, edge ) * ( 1.0 - smoothstep( 3.2, 3.8, edge ) )
    field = smoothstep( 3.4, 4.0, edge )
    height = -0.12 * seam + 0.08 * field + 0.04 * frame
    rivets = np.zeros_like( x )
    for k in range( 16 ):
        cy = ( k + 0.5 ) * ph / 16
        for cx in ( 1.2, pw - 1.2 ):
            d = np.hypot( fx - cx, fy - cy )
            rivets = np.maximum( rivets, np.clip( 1 - d / 0.3, 0, 1 ) )
    height += 0.05 * rivets ** 0.5
    tone = periodic_hash( ix % 4, iy % 2, 11 )
    big = noise( rng, ( n, n ), ( ppi, ppi ), 2.6, 96, 6 )
    fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.0, 1.0, 0.1 )
    streak = noise( rng, ( n, n ), ( ppi, ppi * 0.05 ), 1.6, 8.0, 0.5 )
    base = lin( ( 70, 70, 74 ) )
    colour = base[None, None, :] * ( 0.85 + 0.25 * tone + 0.07 * big + 0.02 * fine )[..., None]
    grime = np.clip( seam + 0.5 * smoothstep( 0.5, 2.2, streak ) * ( 1 - fy / ph ) + 0.3 * smoothstep( 1.0, 2.5, -big ), 0, 1 )
    colour = mix( colour, lin( ( 34, 31, 28 ) ), grime * 0.6 )
    # Scuffed pressed rims and intermittent oxidation leaking down from fasteners.
    rim_wear = np.exp( -( ( edge - 3.35 ) / 0.55 ) ** 2 ) * smoothstep( 0.4, 1.8, big + 0.28 * fine )
    rivet_pitch = ph / 16
    rivet_row = np.floor( ( fy - rivet_pitch * 0.5 ) / rivet_pitch ).astype( int )
    rivet_down = ( fy - rivet_pitch * 0.5 ) % rivet_pitch
    runoff_x = np.exp( -( ( fx - 1.2 ) / 0.52 ) ** 2 ) + np.exp( -( ( fx - ( pw - 1.2 ) ) / 0.52 ) ** 2 )
    active = smoothstep( 0.55, 0.8, periodic_hash( ix * 17 + rivet_row, iy, 35 ) )
    runoff = runoff_x * active * smoothstep( 0.2, 1.0, rivet_down ) * np.exp( -rivet_down / 4.0 )
    colour = mix( colour, lin( ( 120, 118, 114 ) ), frame * 0.2 + rivets * 0.3 + rim_wear * 0.42 )
    colour = mix( colour, lin( ( 110, 63, 43 ) ), np.clip( runoff * 0.4, 0, 0.3 ) )
    rough = 0.48 + 0.08 * tone + 0.2 * grime - 0.1 * frame + 0.03 * fine - 0.09 * rim_wear + 0.13 * runoff
    height += 0.005 * fine - 0.006 * rim_wear - 0.004 * runoff
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( height, ( ppi, ppi ) )


def concrete( n=None ):
    """ Light cast concrete panels: form-tie holes on a 24 in grid, panel joints every 96, mottling and stains. """
    n = n or px( 2048 )
    tile = TILES["ar_concrete"]
    ppi = n / tile
    rng = np.random.default_rng( 303 )
    x, y = grid( n, tile )
    joint_x = np.minimum( x % 96.0, 96.0 - x % 96.0 )
    joint_y = np.minimum( y % 96.0, 96.0 - y % 96.0 )
    joint = 1.0 - smoothstep( 0.15, 0.4, np.minimum( joint_x, joint_y ) )
    tx, ty = ( x - 12.0 ) % 24.0, ( y - 12.0 ) % 24.0
    tie = 1.0 - smoothstep( 0.45, 0.6, np.hypot( np.minimum( tx, 24 - tx ), np.minimum( ty, 24 - ty ) ) )
    big = noise( rng, ( n, n ), ( ppi, ppi ), 2.6, 96, 4 )
    mid = noise( rng, ( n, n ), ( ppi, ppi ), 2.0, 8, 0.5 )
    fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.0, 0.6, 0.1 )
    streak = noise( rng, ( n, n ), ( ppi, ppi * 0.06 ), 1.8, 10.0, 0.6 )
    pores = smoothstep( 2.2, 3.0, noise( rng, ( n, n ), ( ppi, ppi ), 1.0, 0.4, 0.08 ) )
    colour = lin( ( 152, 149, 142 ) )[None, None, :] * ( 0.9 + 0.08 * big + 0.04 * mid + 0.03 * fine )[..., None]
    stain = np.clip( 0.6 * smoothstep( 0.8, 2.6, streak ) + 0.3 * smoothstep( 1.0, 2.8, -big ), 0, 1 )
    colour = mix( colour, lin( ( 92, 86, 78 ) ), stain * 0.55 )
    colour = mix( colour, lin( ( 60, 58, 54 ) ), np.clip( joint + tie + pores * 0.5, 0, 1 ) * 0.8 )
    height = -0.1 * joint - 0.4 * tie - 0.02 * pores + 0.01 * mid + 0.004 * fine
    rough = 0.78 + 0.05 * mid + 0.1 * stain
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( height, ( ppi, ppi ) )


def painted_dark_steel( n=None ):
    n = n or px( 1024 )
    tile = TILES["ar_steel"]
    ppi = n / tile
    rng = np.random.default_rng( 304 )
    big = noise( rng, ( n, n ), ( ppi, ppi ), 2.4, 24, 2 )
    fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.0, 0.8, 0.1 )
    scuff = smoothstep( 1.8, 2.8, noise( rng, ( n, n ), ( ppi * 0.15, ppi ), 1.3, 3.0, 0.15 ) )
    chips = smoothstep( 2.4, 3.1, noise( rng, ( n, n ), ( ppi, ppi ), 1.2, 1.5, 0.1 ) )
    colour = lin( ( 44, 45, 48 ) )[None, None, :] * ( 0.92 + 0.08 * big + 0.03 * fine )[..., None]
    colour = mix( colour, lin( ( 96, 96, 98 ) ), scuff * 0.4 + chips * 0.6 )
    rough = 0.42 + 0.06 * big - 0.12 * scuff + 0.03 * fine
    height = 0.004 * fine - 0.01 * chips
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( height, ( ppi, ppi ) )


def brushed_brass( n=None ):
    n = n or px( 512 )
    tile = TILES["ar_brass"]
    ppi = n / tile
    rng = np.random.default_rng( 305 )
    brush = noise( rng, ( n, n ), ( ppi * 0.03, ppi ), 1.0, 6.0, 0.1 )
    tarnish = smoothstep( 0.5, 2.5, noise( rng, ( n, n ), ( ppi, ppi ), 2.4, 16, 1 ) )
    colour = lin( ( 186, 140, 66 ) )[None, None, :] * ( 0.95 + 0.06 * brush )[..., None]
    colour = mix( colour, lin( ( 110, 82, 44 ) ), tarnish * 0.5 )
    rough = 0.28 + 0.05 * brush + 0.2 * tarnish
    height = 0.003 * brush
    return T.linear_to_srgb( colour ), np.clip( rough, 0.05, 1 ), normals( height, ( ppi, ppi ) )


def bar_grating( n=None ):
    """ Welded bar grating: bearing bars 1 3/16 in apart, cross bars every 4 in, dark gaps between. """
    n = n or px( 1024 )                 # a power of two: the engine can't mip a 768 normal map with its roughness
    tile = TILES["ar_grating"]
    ppi = n / tile
    rng = np.random.default_rng( 306 )
    x, y = grid( n, tile )
    pitch = tile / 20.0                     # 1.2 in
    bx_ = np.abs( ( x % pitch ) - pitch / 2 )
    bearing = 1.0 - smoothstep( 0.1, 0.16, np.abs( bx_ - pitch / 2 ) )
    cy = np.abs( ( y % 4.0 ) - 2.0 )
    cross = 1.0 - smoothstep( 0.1, 0.16, np.abs( cy - 2.0 ) )
    metal = np.clip( bearing + cross, 0, 1 )
    fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.0, 0.8, 0.1 )
    wearn = noise( rng, ( n, n ), ( ppi, ppi ), 2.2, 12, 1 )
    colour = lin( ( 70, 70, 72 ) )[None, None, :] * ( 0.9 + 0.1 * wearn + 0.03 * fine )[..., None]
    colour = mix( colour, lin( ( 120, 118, 114 ) ), smoothstep( 0.8, 2.2, wearn ) * metal * 0.5 )
    colour = mix( lin( ( 6, 6, 6 ) )[None, None, :] * np.ones_like( colour ), colour, metal[..., None] )
    height = 0.6 * metal + 0.01 * fine
    rough = np.where( metal > 0.5, 0.4 + 0.1 * wearn, 0.95 )
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( height, ( ppi, ppi ) )


def hazard_stripes( n=None ):
    n = n or px( 512 )
    tile = TILES["ar_hazard"]
    ppi = n / tile
    rng = np.random.default_rng( 307 )
    x, y = grid( n, tile )
    stripe = ( ( ( x + y ) / 3.0 ) % 2.0 ) < 1.0
    # Smooth the stripe edge a little.
    t = ( ( x + y ) / 3.0 ) % 1.0
    edge = smoothstep( 0.0, 0.03, t ) * ( 1 - smoothstep( 0.97, 1.0, t ) )
    yellow = np.where( stripe, edge, 0.0 ).astype( np.float32 )
    worn = wear( rng, ( n, n ), 0.55, ppi, 3.0 )
    colour = mix( lin( ( 24, 24, 24 ) )[None, None, :] * np.ones( ( n, n, 3 ), np.float32 ), lin( ( 214, 160, 28 ) ), yellow )
    colour = mix( colour, lin( ( 92, 92, 90 ) ), worn * 0.7 )
    dirt = smoothstep( 0.5, 2.5, noise( rng, ( n, n ), ( ppi, ppi ), 2.4, 12, 1 ) )
    colour = mix( colour, lin( ( 40, 34, 26 ) ), dirt * 0.35 )
    rough = 0.55 + 0.2 * worn + 0.1 * dirt
    height = -0.01 * worn
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( height, ( ppi, ppi ) )


def regolith( n=None ):
    """ Muted ochre dust, fine basalt grit and shallow wind ripples, based on Curiosity's sandy plains. """
    n = n or px( 2048 )
    tile = TILES["ar_regolith"]
    ppi = n / tile
    rng = np.random.default_rng( 308 )
    big = noise( rng, ( n, n ), ( ppi, ppi ), 2.8, 320, 8 )
    mid = noise( rng, ( n, n ), ( ppi, ppi ), 2.2, 40, 2 )
    fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.2, 4, 0.4 )
    rocks = smoothstep( 1.6, 2.4, noise( rng, ( n, n ), ( ppi, ppi ), 1.6, 12, 1.0 ) )
    colour = lin( ( 159, 121, 93 ) )[None, None, :] * ( 0.96 + 0.055 * big + 0.025 * mid + 0.02 * fine )[..., None]
    colour = mix( colour, lin( ( 183, 145, 112 ) ), smoothstep( 0.4, 2.0, big + 0.3 * mid ) * 0.38 )
    colour = mix( colour, lin( ( 102, 90, 79 ) ), np.clip( rocks + smoothstep( 1.0, 2.6, -mid ) * 0.25, 0, 1 ) * 0.55 )
    # Fine wind-scoured ripples interrupt the broad volcanic dust fields.
    x, y = grid( n, tile )
    drift = smoothstep( 0.05, 1.8, big + 0.25 * mid )
    # Integer periods in both axes keep the wind-ripple phase continuous at texture tile boundaries.
    ripple = ( 0.5 + 0.5 * np.sin( 2 * math.pi * ( 29 * x + 6 * y ) / tile + 0.65 * mid ) ) * drift
    colour = mix( colour, lin( ( 180, 142, 109 ) ), ripple * 0.09 )
    height = 0.65 * rocks + 0.18 * mid + 0.04 * fine + 0.10 * ripple
    rough = 0.9 - 0.08 * rocks + 0.04 * drift
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( height, ( ppi, ppi ) )


def rock( n=None ):
    """ Layered sedimentary rock: bands of rust and brown, cracks, dust caught on the ledges. """
    n = n or px( 2048 )
    tile = TILES["ar_rock"]
    ppi = n / tile
    rng = np.random.default_rng( 309 )
    x, y = grid( n, tile )
    warp = noise( rng, ( n, n ), ( ppi, ppi ), 2.8, 512, 16 )
    layers = np.sin( ( y + 30 * warp ) / tile * 2 * math.pi * 14 ) * 0.5 + 0.5
    layers2 = np.sin( ( y + 18 * warp ) / tile * 2 * math.pi * 41 ) * 0.5 + 0.5
    mid = noise( rng, ( n, n ), ( ppi, ppi ), 2.2, 60, 3 )
    fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.4, 6, 0.5 )
    cracks = 1.0 - smoothstep( 0.0, 0.08, np.abs( noise( rng, ( n, n ), ( ppi, ppi ), 2.0, 80, 4 ) ) )
    colour = mix( lin( ( 139, 111, 90 ) )[None, None, :] * np.ones( ( n, n, 3 ), np.float32 ), lin( ( 108, 88, 74 ) ),
                  np.clip( layers * 0.7 + 0.3 * layers2, 0, 1 ) )
    colour *= ( 0.92 + 0.08 * mid + 0.04 * fine )[..., None]
    colour = mix( colour, lin( ( 177, 139, 108 ) ), smoothstep( 0.6, 0.95, layers2 ) * smoothstep( 0.0, 1.5, mid ) * 0.4 )
    colour = mix( colour, lin( ( 76, 63, 55 ) ), cracks * 0.45 )
    height = 1.3 * layers + 0.4 * layers2 + 0.7 * mid + 0.12 * fine - 0.7 * cracks
    rough = 0.88
    return T.linear_to_srgb( colour ), np.full( ( n, n ), rough, np.float32 ), normals( height, ( ppi, ppi ) )


def tower_cladding( n=None ):
    """ The far spires' cladding: dark ribbed panels and rows of small windows, a third of them lit amber. Returns
    the self-illumination mask too. """
    n = n or px( 1024 )
    tile = TILES["ar_tower"]
    ppi = n / tile
    rng = np.random.default_rng( 310 )
    x, y = grid( n, tile )
    wx, wy = 16.0, 24.0
    ix, iy = np.floor( x / wx ).astype( int ), np.floor( y / wy ).astype( int )
    fx, fy = x - ix * wx, y - iy * wy
    window = ( np.abs( fx - wx / 2 ) < 2.5 ) & ( np.abs( fy - wy / 2 ) < 4.0 )
    lit = periodic_hash( ix % 16, iy % 10, 13 ) < 0.3
    rib = np.abs( fx - 0.0 ) < 1.0
    big = noise( rng, ( n, n ), ( ppi, ppi ), 2.6, 128, 8 )
    colour = lin( ( 52, 48, 46 ) )[None, None, :] * ( 0.9 + 0.08 * big )[..., None] * np.ones( ( n, n, 3 ), np.float32 )
    colour = np.where( rib[..., None], lin( ( 80, 72, 64 ) ), colour )
    colour = np.where( ( window & ~lit )[..., None], lin( ( 18, 18, 22 ) ), colour )
    warm = lin( ( 255, 178, 92 ) ) * ( 0.8 + 0.2 * periodic_hash( ix % 16, iy % 10, 17 ) )[..., None]
    colour = np.where( ( window & lit )[..., None], warm, colour )
    illum = ( window & lit ).astype( np.float32 )
    height = np.where( window, -1.0, 0.0 ) + np.where( rib, 0.5, 0.0 )
    rough = np.where( window, 0.15, 0.6 ).astype( np.float32 )
    return T.linear_to_srgb( colour ), rough, normals( height.astype( np.float32 ), ( ppi, ppi ) ), illum


# ---------------------------------------------------------------------------------------------------------------------
# The hard cases

def crate_atlas():
    """ Black hard cases, moulded with a raised rim round each face, scuffed grey; the front stencilled MARS / BIGGER /
    CLEANER / BRIGHTER, a side with the facility's label. """
    W, H = px( CRATE_ATLAS[0] ), px( CRATE_ATLAS[1] )
    rng = np.random.default_rng( 311 )
    colour = np.zeros( ( H, W, 3 ), np.float32 )
    rough = np.full( ( H, W ), 0.6, np.float32 )
    height = np.zeros( ( H, W ), np.float32 )
    sizes = { "front_text": ( CASE[0], CASE[1] ), "front_plain": ( CASE[0], CASE[1] ), "side": ( CASE[2], CASE[1] ),
              "side_logo": ( CASE[2], CASE[1] ), "end_plain": ( CASE[2], CASE[1] ), "top": ( CASE[0], CASE[2] ),
              "top_ribs": ( CASE[0], CASE[2] ) }
    for name, ( rx, ry, rw, rh ) in CRATE.items():
        rx, ry, rw, rh = px( rx ), px( ry ), px( rw ), px( rh )
        fw, fh = sizes[name]
        ppi = ( rw / fw, rh / fh )
        xs = ( np.arange( rw, dtype=np.float32 ) + 0.5 ) / ppi[0]
        ys = ( np.arange( rh, dtype=np.float32 ) + 0.5 ) / ppi[1]
        X, Y = np.meshgrid( xs, ys )
        edge = np.minimum( np.minimum( X, fw - X ), np.minimum( Y, fh - Y ) )
        rim = 1.0 - smoothstep( 1.6, 2.0, edge )
        inner = smoothstep( 2.0, 2.4, edge )
        h_ = 0.25 * rim - 0.05 * inner
        if name == "top_ribs":
            rib = ( np.abs( ( X % 6.0 ) - 3.0 ) < 0.6 ) & ( edge > 3.0 )
            h_ += 0.15 * rib
        if name in ( "side", "side_logo", "end_plain" ):
            # A recessed handle pocket.
            pocket = ( np.abs( X - fw / 2 ) < 5.0 ) & ( np.abs( Y - fh * 0.38 ) < 1.6 )
            h_ -= 0.6 * pocket
        fine = noise( rng, ( rh, rw ), ppi, 1.0, 0.5, 0.08 )
        big = noise( rng, ( rh, rw ), ppi, 2.4, 20, 2 )
        scuff = smoothstep( 1.8, 2.8, noise( rng, ( rh, rw ), ( ppi[0] * 0.2, ppi[1] ), 1.3, 3.0, 0.2 ) )
        c = lin( ( 26, 26, 27 ) )[None, None, :] * ( 0.9 + 0.1 * big + 0.04 * fine )[..., None]
        c = mix( c, lin( ( 70, 70, 70 ) ), np.clip( scuff + rim * 0.15, 0, 1 ) * 0.5 )
        dust = smoothstep( 1.2, 3.0, big ) * ( 0.12 if name.startswith( "top" ) else 0.05 )
        c = mix( c, lin( ( 96, 72, 58 ) ), dust )
        r_ = 0.62 + 0.08 * big - 0.15 * scuff
        if name == "front_text":
            items = []
            cap = rh * 0.115
            for k, word in enumerate( ( "MARS", "BIGGER", "CLEANER", "BRIGHTER" ) ):
                items.append( ( word, FONT_BOLD, cap, rw * 0.07, rh * 0.16 + k * cap * 1.45, "l", 0.06 ) )
            letters = text_layer( ( rh, rw ), items )
            letters *= 1.0 - wear( rng, ( rh, rw ), 0.5, ppi[0], 2.0 ) * 0.8
            c = mix( c, lin( ( 196, 194, 186 ) ), letters * 0.85 )
            r_ = mix( r_, 0.5, letters )
        if name == "side_logo":
            label = ( np.abs( X - fw / 2 ) < 9.0 ) & ( np.abs( Y - fh * 0.7 ) < 4.0 )
            c = np.where( label[..., None], lin( ( 200, 198, 190 ) ), c )
            mark = shapes_layer( ( rh, rw ), logo_polygons( rw * 0.36, rh * 0.6, rw * 0.11 ) )
            c = mix( c, lin( ( 196, 36, 30 ) ), mark )
            words = text_layer( ( rh, rw ), [ ( "ARES FACILITY", FONT_BOLD, rh * 0.035, rw * 0.44, rh * 0.62, "l", 0.08 ),
                                              ( "ATMOS DIV. 07", FONT_BOLD, rh * 0.025, rw * 0.44, rh * 0.68, "l", 0.08 ) ] )
            c = mix( c, lin( ( 30, 30, 30 ) ), words )
        colour[ry:ry + rh, rx:rx + rw] = c
        rough[ry:ry + rh, rx:rx + rw] = r_
        height[ry:ry + rh, rx:rx + rw] = h_ + 0.004 * fine
    ppi = W / 96.0
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( height, ( ppi, ppi ) )


# ---------------------------------------------------------------------------------------------------------------------
# Posters, banners and signs

def grimy_panel( rng, shape, base, ppi=6.0, streaks=0.4 ):
    h, w = shape
    big = noise( rng, shape, ( ppi, ppi ), 2.6, 60, 3 )
    fine = noise( rng, shape, ( ppi, ppi ), 1.0, 0.6, 0.1 )
    streak = noise( rng, shape, ( ppi, ppi * 0.06 ), 1.8, 10.0, 0.6 )
    c = lin( base )[None, None, :] * ( 0.92 + 0.07 * big + 0.03 * fine )[..., None]
    c = mix( c, lin( ( 70, 64, 58 ) ), np.clip( smoothstep( 0.8, 2.8, streak ) * streaks + smoothstep( 1.2, 3.0, -big ) * 0.3, 0, 1 ) )
    return c, big


def warning_stripe( shape, rng=None ):
    """Warning lettering sits in a clear yellow panel, inset from the stripes."""
    h, w = shape
    rng = rng if rng is not None else np.random.default_rng( 312 )
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    stripe = ( ( ( xx + yy ) / ( h * 0.25 ) ) % 2.0 ) < 1.0
    c = np.where( stripe[..., None], lin( ( 214, 160, 28 ) ), lin( ( 24, 24, 24 ) ) ).astype( np.float32 )
    box = ( np.abs( xx - w / 2 ) < w * 0.40 ) & ( np.abs( yy - h / 2 ) < h * 0.40 )
    c = np.where( box[..., None], lin( ( 214, 160, 28 ) ), c )
    words = text_layer( ( h, w ), [ ( "CAUTION  HIGH ENERGY", FONT_BOLD, h * 0.3, w * 0.5, h * 0.35, "m", 0.06, w * 0.62 ) ] )
    c = mix( c, lin( ( 20, 20, 20 ) ), words )
    worn = wear( rng, ( h, w ), 0.5, 6.0, 3.0 )
    return mix( c, lin( ( 90, 90, 88 ) ), worn * 0.5 )


def sign_atlas():
    W, H = px( SIGN_ATLAS[0] ), px( SIGN_ATLAS[1] )
    rng = np.random.default_rng( 312 )
    colour = np.zeros( ( H, W, 3 ), np.float32 )
    rough = np.full( ( H, W ), 0.7, np.float32 )
    red = lin( ( 196, 36, 30 ) )
    dark = lin( ( 38, 38, 40 ) )
    white = lin( ( 226, 224, 216 ) )

    def put( name, c, r ):
        x, y, w, h = ( px( v ) for v in SIGN[name] )
        colour[y:y + h, x:x + w] = c
        rough[y:y + h, x:x + w] = r

    def size( name ):
        _, _, w, h = ( px( v ) for v in SIGN[name] )
        return h, w

    # ARES FACILITY: a light concrete panel, the red mark over the name, the slogan under it.
    h, w = size( "poster_ares" )
    c, big = grimy_panel( rng, ( h, w ), ( 168, 164, 156 ), 6.0, 0.5 )
    mark = shapes_layer( ( h, w ), logo_polygons( w * 0.5, h * 0.12, w * 0.30 ) )
    c = mix( c, red, mark * 0.95 )
    words = text_layer( ( h, w ), [ ( "ARES", FONT_BOLD, h * 0.12, w * 0.5, h * 0.40, "m", 0.04 ),
                                    ( "FACILITY", FONT_BOLD, h * 0.072, w * 0.5, h * 0.565, "m", 0.04 ),
                                    ( "A CLEANER TOMORROW", FONT_BOLD, h * 0.034, w * 0.5, h * 0.74, "m", 0.06 ),
                                    ( "A BRIGHTER MARS", FONT_BOLD, h * 0.034, w * 0.5, h * 0.79, "m", 0.06 ) ] )
    words *= 1.0 - wear( rng, ( h, w ), 0.35, 4.0, 4.0 ) * 0.6
    c = mix( c, dark, words * 0.95 )
    frame = np.zeros( ( h, w ), np.float32 )
    b = max( 4, w // 60 )
    frame[:b] = frame[-b:] = 1
    frame[:, :b] = frame[:, -b:] = 1
    c = mix( c, lin( ( 60, 60, 62 ) ), frame )
    put( "poster_ares", c, 0.75 - 0.2 * frame )

    # ATMOS PROCESSING: the column's dark panel.
    h, w = size( "band_atmos" )
    c, big = grimy_panel( rng, ( h, w ), ( 48, 48, 50 ), 8.0, 0.25 )
    words = text_layer( ( h, w ), [ ( "ATMOS", FONT_BOLD, h * 0.15, w * 0.5, h * 0.17, "m", 0.04 ),
                                    ( "PROCESSING", FONT_BOLD, h * 0.15, w * 0.5, h * 0.37, "m", 0.04 ),
                                    ( "STABILIZING", FONT_BOLD, h * 0.055, w * 0.5, h * 0.60, "m", 0.08 ),
                                    ( "A BRIGHTER TOMORROW", FONT_BOLD, h * 0.055, w * 0.5, h * 0.68, "m", 0.08 ) ] )
    c = mix( c, white, words * 0.92 )
    outline = shapes_layer( ( h, w ), logo_polygons( w * 0.5, h * 0.78, h * 0.13 ) )
    inner = shapes_layer( ( h, w ), [ ( [ ( w * 0.5, h * 0.80 ), ( w * 0.5 + h * 0.05, h * 0.89 ), ( w * 0.5 - h * 0.05, h * 0.89 ) ], 1.0 ) ] )
    c = mix( c, white, np.clip( outline - inner, 0, 1 ) * 0.9 )
    rim = np.zeros( ( h, w ), np.float32 )
    b = max( 4, h // 40 )
    rim[:b] = rim[-b:] = 1
    rim[:, :b] = rim[:, -b:] = 1
    c = mix( c, lin( ( 90, 90, 92 ) ), rim )
    put( "band_atmos", c, 0.5 )
    h, w = size( "band_atmos_back" )
    c, _ = grimy_panel( rng, ( h, w ), ( 48, 48, 50 ), 8.0, 0.25 )
    put( "band_atmos_back", c, 0.5 )

    # The hanging banners: black cloth, white lettering, the red mark at the foot.
    def banner( name, lines, mark_at=0.84 ):
        h, w = size( name )
        weave = noise( rng, ( h, w ), ( 8.0, 8.0 ), 1.0, 0.3, 0.05 )
        folds = noise( rng, ( h, w ), ( 8.0, 0.4 ), 2.0, 30, 2 )
        c = lin( ( 22, 22, 24 ) )[None, None, :] * ( 0.9 + 0.08 * weave + 0.12 * folds )[..., None] * np.ones( ( h, w, 3 ), np.float32 )
        items = []
        for text, cap, y, path in lines:
            items.append( ( text, path, h * cap, w * 0.5, h * y, "m", 0.05 ) )
        words = text_layer( ( h, w ), items )
        c = mix( c, white, words * 0.92 )
        mark = shapes_layer( ( h, w ), logo_polygons( w * 0.5, h * mark_at, w * 0.22 ) )
        c = mix( c, red, mark )
        edge = np.zeros( ( h, w ), np.float32 )
        edge[: max( 6, h // 60 )] = 1
        c = mix( c, lin( ( 90, 90, 90 ) ), edge )
        put( name, c, 0.85 )

    banner( "banner_humanity", [ ( "HUMANITY", 0.032, 0.10, FONT_BOLD ), ( "FURTHER", 0.032, 0.14, FONT_BOLD ) ], 0.30 )
    h_, w_ = size( "banner_habitat" )
    banner( "banner_habitat", [ ( "HABITAT", 0.030, 0.07, FONT_BOLD ), ( "B", 0.16, 0.12, FONT_BOLD ),
                                ( "RESEARCH", 0.024, 0.36, FONT_BOLD ), ( "INDUSTRY", 0.024, 0.395, FONT_BOLD ),
                                ( "A STRONGER", 0.024, 0.43, FONT_BOLD ), ( "TOMORROW", 0.024, 0.465, FONT_BOLD ) ], 0.86 )

    # RED PLANET / REAL PROGRESS.
    h, w = size( "poster_redplanet" )
    c, _ = grimy_panel( rng, ( h, w ), ( 176, 172, 164 ), 6.0, 0.4 )
    mark = shapes_layer( ( h, w ), logo_polygons( w * 0.16, h * 0.30, h * 0.40 ) )
    c = mix( c, red, mark )
    words = text_layer( ( h, w ), [ ( "RED PLANET", FONT_BOLD, h * 0.15, w * 0.29, h * 0.30, "l", 0.04 ),
                                    ( "REAL PROGRESS", FONT_BOLD, h * 0.15, w * 0.29, h * 0.52, "l", 0.04 ) ] )
    c = mix( c, red, words * 0.9 )
    put( "poster_redplanet", c, 0.75 )

    # MARS BIGGER CLEANER BRIGHTER, as a poster.
    h, w = size( "poster_mars" )
    c, _ = grimy_panel( rng, ( h, w ), ( 34, 34, 36 ), 6.0, 0.2 )
    words = text_layer( ( h, w ), [ ( "MARS", FONT_BOLD, h * 0.13, w * 0.1, h * 0.14, "l", 0.04 ),
                                    ( "BIGGER", FONT_BOLD, h * 0.13, w * 0.1, h * 0.33, "l", 0.04 ),
                                    ( "CLEANER", FONT_BOLD, h * 0.13, w * 0.1, h * 0.52, "l", 0.04 ),
                                    ( "BRIGHTER", FONT_BOLD, h * 0.13, w * 0.1, h * 0.71, "l", 0.04 ) ] )
    c = mix( c, white, words * 0.9 )
    mark = shapes_layer( ( h, w ), logo_polygons( w * 0.8, h * 0.62, w * 0.18 ) )
    c = mix( c, red, mark )
    put( "poster_mars", c, 0.7 )

    # The logo alone, on white.
    h, w = size( "logo" )
    c, _ = grimy_panel( rng, ( h, w ), ( 220, 218, 210 ), 6.0, 0.2 )
    c = mix( c, red, shapes_layer( ( h, w ), logo_polygons( w * 0.5, h * 0.12, w * 0.8 ) ) )
    put( "logo", c, 0.6 )

    # Painted name plates: white stencil on a dark plate.
    for name, text in ( ( "plate_cargo", "CARGO CONCOURSE" ), ( "plate_rover", "ROVER BAY" ),
                        ( "plate_core", "ATMOS CORE" ), ( "plate_observation", "OBSERVATION" ) ):
        h, w = size( name )
        c, _ = grimy_panel( rng, ( h, w ), ( 40, 40, 42 ), 6.0, 0.2 )
        words = text_layer( ( h, w ), [ ( text, FONT_BOLD, h * 0.4, w * 0.5, h * 0.3, "m", 0.08, w * 0.88 ) ] )
        words *= 1.0 - wear( rng, ( h, w ), 0.4, 4.0, 3.0 ) * 0.7
        c = mix( c, lin( ( 214, 160, 28 ) ), words )
        put( name, c, 0.6 )

    # The wings' zone markers: the sector's number painted big on a dark plate, its name over it.
    for name, small, big in ( ( "zone_03", "SECTOR", "03" ), ( "zone_b", "HABITAT", "B" ) ):
        h, w = size( name )
        c, _ = grimy_panel( rng, ( h, w ), ( 46, 46, 48 ), 6.0, 0.3 )
        words = text_layer( ( h, w ), [ ( small, FONT_BOLD, h * 0.09, w * 0.5, h * 0.1, "m", 0.12, w * 0.8 ),
                                        ( big, FONT_BOLD, h * 0.56, w * 0.5, h * 0.28, "m", 0.02, w * 0.86 ) ] )
        words *= 1.0 - wear( rng, ( h, w ), 0.45, 4.0, 3.0 ) * 0.7
        c = mix( c, white, words * 0.9 )
        bar = np.zeros( ( h, w ), np.float32 )
        bar[int( h * 0.9 ):int( h * 0.94 ), int( w * 0.1 ):int( w * 0.9 )] = 1
        c = mix( c, lin( ( 214, 160, 28 ) ), bar )
        put( name, c, 0.65 )

    # A warning stripe with text.
    h, w = size( "stripe_warning" )
    put( "stripe_warning", warning_stripe( ( h, w ), rng ), 0.6 )

    fine = noise( rng, ( H, W ), ( 20.0, 20.0 ), 1.0, 0.4, 0.05 )
    return T.linear_to_srgb( colour ), np.clip( rough, 0.1, 1 ), normals( 0.01 * fine, ( 20.0, 20.0 ) )


def lit_atlas():
    """ Back-lit door signs: white lettering and a chevron on a dark plate with a lit rim. """
    W, H = px( LIT_ATLAS[0] ), px( LIT_ATLAS[1] )
    colour = np.zeros( ( H, W, 3 ), np.float32 )
    illum = np.zeros( ( H, W ), np.float32 )
    for name, ( x, y, w, h ) in LIT.items():
        x, y, w, h = px( x ), px( y ), px( w ), px( h )
        text, arrow = LIT_TEXT[name]
        c = np.ones( ( h, w, 3 ), np.float32 ) * lin( ( 24, 26, 28 ) )
        items = [ ( text, FONT_BOLD, h * 0.36, w * 0.06, h * 0.32, "l", 0.08, w * ( 0.74 if arrow else 0.86 ) ) ]
        if arrow:
            items.append( ( arrow, FONT_BOLD, h * 0.42, w * 0.94, h * 0.29, "r", 0.0 ) )
        words = text_layer( ( h, w ), items )
        rim = np.zeros( ( h, w ), np.float32 )
        b = max( 3, h // 24 )
        rim[b:2 * b] = rim[-2 * b:-b] = 1
        rim[b:-b, b:2 * b] = rim[b:-b, -2 * b:-b] = 1
        c = mix( c, lin( ( 236, 240, 244 ) ), np.clip( words + rim * 0.6, 0, 1 ) )
        colour[y:y + h, x:x + w] = c
        illum[y:y + h, x:x + w] = np.clip( words + rim * 0.5 + 0.06, 0, 1 )
    return T.linear_to_srgb( colour ), illum


def screen_atlas():
    """Preserve the built-in ImageGen control displays; regenerating materials must not redraw placeholders."""
    source = ROOT / "Sources/Ares/screens/screen-atlas.png"
    if not source.exists():
        raise FileNotFoundError( f"Missing generated screen atlas: {source}; see Sources/Ares/screens/screen-atlas-prompt.txt" )
    with Image.open( source ) as image:
        if abs( image.width / image.height - 2.0 ) > 0.01:
            raise ValueError( "The generated screen atlas must contain four columns and two rows (2:1 canvas)" )
        image = image.convert( "RGB" ).resize( ( px( SCREEN_ATLAS[0] ), px( SCREEN_ATLAS[1] ) ), Image.Resampling.LANCZOS )
        # BX.save_rgb takes sRGB bytes (0..255), whereas the emission mask below takes 0..1.
        colour = np.asarray( image, np.uint8 )
    return colour, np.ones( colour.shape[:2], np.float32 )



def plasma():
    """ The column's plasma, u round it and v up: an orange furnace glow, brighter turbulence and white-yellow arcs.
    Wraps in u. """
    n = px( 1024 )
    rng = np.random.default_rng( 314 )
    shape = ( n, n )
    big = noise( rng, shape, ( 1, 1 ), 2.6, 600, 10 )
    mid = noise( rng, shape, ( 1, 1 ), 2.0, 120, 3 )
    arcs = np.zeros( shape, np.float32 )
    for scale, weight in ( ( 300, 1.0 ), ( 120, 0.7 ), ( 50, 0.4 ) ):
        r = noise( rng, shape, ( 1, 0.6 ), 2.2, scale, 2 )
        arcs = np.maximum( arcs, weight * ( 1.0 - np.clip( np.abs( r ) / 0.09, 0, 1 ) ) ** 3 )
    heat = np.clip( 0.45 + 0.18 * big + 0.12 * mid, 0, 1 )
    yy = np.linspace( 0, 1, n, dtype=np.float32 )[:, None]
    heat = heat * ( 0.8 + 0.2 * np.sin( yy * math.pi ) )
    base = mix( lin( ( 120, 22, 4 ) )[None, None, :] * np.ones( ( n, n, 3 ), np.float32 ), lin( ( 255, 108, 16 ) ), heat )
    base = mix( base, lin( ( 255, 196, 90 ) ), np.clip( arcs, 0, 1 ) )
    base = mix( base, lin( ( 255, 244, 214 ) ), np.clip( arcs - 0.6, 0, 1 ) * 2 )
    illum = np.clip( 0.55 + 0.45 * heat + arcs, 0, 1 )
    return T.linear_to_srgb( base ), illum


def plasma_vmat():
    """GPU-driven circulation; keep these values when regenerating the column's material."""
    return '\n'.join( [ '// Tools/ares_materials.py', 'Layer0', '{',
        '    shader "shaders/hc1_ares_plasma.shader"',
        f'    TextureColor "{RESOURCE_DIR}/ar_plasma_color.png"',
        '    g_flBrightness "1.8"', '    g_flRiseSpeed "0.018"', '    g_flSwirlSpeed "0.008"',
        '    g_flFlowHeight "180"', '    g_flWarp "0.055"', '    g_flDarkAreas "0.85"',
        '    g_flPulseAmount "0.03"', '}', '' ] )


def dome_lattice():
    """ A habitat dome's skin, u round it (16 bays) and v from its foot to its crown: white struts in a diamond
    lattice, dark glass, a scatter of cells lit warm from inside. """
    n = px( 1024 )
    rng = np.random.default_rng( 315 )
    yy, xx = np.mgrid[0:n, 0:n].astype( np.float32 ) / n
    bays, rows = 16, 10
    a = ( xx * bays + yy * rows ) % 1.0
    b = ( xx * bays - yy * rows ) % 1.0
    strut = ( np.minimum( a, 1 - a ) < 0.05 ) | ( np.minimum( b, 1 - b ) < 0.05 )
    ring = ( np.minimum( ( yy * rows ) % 1.0, 1 - ( yy * rows ) % 1.0 ) < 0.03 )
    frame = strut | ring
    cell_i = np.floor( xx * bays + yy * rows ).astype( int ) % 64
    cell_j = np.floor( xx * bays - yy * rows ).astype( int ) % 64
    lit = ( periodic_hash( cell_i, cell_j, 21 ) < 0.22 ) & ( yy > 0.7 )
    shade = noise( rng, ( n, n ), ( 1.0, 1.0 ), 2.0, 200, 8 )
    panel = lin( ( 168, 162, 154 ) )[None, None, :] * ( 0.92 + 0.08 * shade )[..., None] * np.ones( ( n, n, 3 ), np.float32 )
    panel = mix( panel, lin( ( 120, 112, 104 ) ), smoothstep( 0.0, 0.25, 1 - yy ) * 0.0 + ( periodic_hash( cell_i, cell_j, 23 ) < 0.12 ) * 0.5 )
    c = np.where( lit[..., None], lin( ( 255, 196, 128 ) ), panel )
    c = np.where( frame[..., None], lin( ( 170, 160, 152 ) ), c )
    dust = smoothstep( 0.6, 1.0, yy ) * 0.0 + smoothstep( 0.0, 0.3, 1 - yy ) * 0.3
    c = mix( c, lin( ( 170, 100, 64 ) ), dust * frame )
    illum = ( lit & ~frame ).astype( np.float32 )
    rough = np.where( frame, 0.62, 0.38 ).astype( np.float32 )
    return T.linear_to_srgb( c ), illum, rough


# ---------------------------------------------------------------------------------------------------------------------
# Flat paints and lights

# Flat paints: colour (sRGB), metalness, roughness.
PAINTED = {
    "ar_black": ( ( 20, 20, 21 ), 0.0, 0.6 ),
    "ar_rubber": ( ( 16, 16, 16 ), 0.0, 0.85 ),
    "ar_dark": ( ( 10, 10, 10 ), 0.0, 0.9 ),
    "ar_gunmetal": ( ( 36, 37, 40 ), 0.6, 0.35 ),
    "ar_white": ( ( 206, 204, 198 ), 0.0, 0.5 ),
    "ar_red": ( ( 176, 34, 28 ), 0.0, 0.5 ),
    "ar_yellow": ( ( 214, 160, 28 ), 0.0, 0.5 ),
    "ar_copper": ( ( 170, 96, 60 ), 0.9, 0.35 ),
    "ar_pipe": ( ( 84, 86, 88 ), 0.6, 0.4 ),
    "ar_cable": ( ( 22, 22, 24 ), 0.0, 0.7 ),
    "ar_concrete_dark": ( ( 70, 66, 62 ), 0.0, 0.85 ),
    "ar_dome_frame": ( ( 170, 160, 152 ), 0.3, 0.56 ),
    "ar_tower_dark": ( ( 40, 36, 34 ), 0.4, 0.5 ),
    "ar_spire": ( ( 70, 60, 54 ), 0.5, 0.45 ),
    "ar_bezel": ( ( 30, 31, 33 ), 0.3, 0.4 ),
    "ar_rover_white": ( ( 196, 192, 184 ), 0.0, 0.45 ),
    "ar_rover_orange": ( ( 204, 98, 34 ), 0.0, 0.45 ),
    "ar_tyre": ( ( 28, 27, 26 ), 0.0, 0.9 ),
    "ar_moon": ( ( 120, 112, 104 ), 0.0, 0.9 ),
}

# Lights: colour (sRGB), self-illumination brightness.
EMISSIVE = {
    "ar_led": ( ( 236, 244, 255 ), 6.0 ),
    "ar_led_warm": ( ( 255, 214, 160 ), 5.0 ),
    "ar_led_amber": ( ( 255, 150, 50 ), 5.0 ),
    "ar_led_red": ( ( 255, 60, 40 ), 4.0 ),
    "ar_led_cyan": ( ( 120, 220, 255 ), 4.0 ),
    "ar_core": ( ( 255, 190, 110 ), 3.2 ),
    "ar_far_light": ( ( 255, 164, 96 ), 2.5 ),
}

# Glass: tint (sRGB, for TextureColor), roughness, AlbedoAbsorption.
GLASS = {
    "ar_glass": ( ( 236, 238, 234 ), 0.03, 0.12 ),
    "ar_reactor_glass": ( ( 255, 224, 188 ), 0.05, 0.1 ),
    "ar_room_glass": ( ( 220, 230, 232 ), 0.04, 0.2 ),
}


def vmat( name, colour, normal=None, rough=None, metalness=0.0, alpha=None, illum=None, brightness=1.0,
          rough_value=None, tint=( 1.0, 1.0, 1.0 ) ):
    lines_ = [ "// Tools/ares_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if alpha:
        lines_ += [ '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{RESOURCE_DIR}/{alpha}"', '    g_flAlphaTestReference "0.5"',
                    '    g_flAntiAliasedEdgeStrength "1"' ]
    lines_ += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metalness:.2f}"',
                f'    TextureColor "{colour}"', f'    TextureNormal "{normal or DEFAULT_NORMAL}"' ]
    if rough:
        lines_.append( f'    TextureRoughness "{rough}"' )
    else:
        v = rough_value if rough_value is not None else 0.5
        lines_.append( f'    TextureRoughness "[{v:.6f} {v:.6f} {v:.6f} 0.000000]"' )
    lines_ += [ f'    TextureAmbientOcclusion "{DEFAULT_AO}"', f'    g_vColorTint "[{tint[0]:.6f} {tint[1]:.6f} {tint[2]:.6f} 1.000000]"',
                '    g_flModelTintAmount "1.0"' ]
    if illum:
        lines_ += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{illum}"', f'    g_flSelfIllumBrightness "{brightness:.3f}"',
                    '    g_flSelfIllumAlbedoFactor "1.0"', '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines_.append( "}" )
    return "\n".join( lines_ ) + "\n"


def glass_vmat( tint, roughness, absorption ):
    r, g, b = ( c / 255.0 for c in tint )
    return ( "// Tools/ares_materials.py\n\"Layer0\"\n{\n"
             '    shader "shaders/glass.shader"\n'
             '    F_GLASS_QUALITY "2"\n'
             '    g_bFogEnabled "1"\n'
             '    g_flBlurAmount "0.02"\n'
             '    g_flRefractionStrength "1.006"\n'
             f'    AlbedoAbsorption "{absorption:.3f}"\n'
             '    g_flTintColor "[1.000000 1.000000 1.000000 0.000000]"\n'
             f'    TextureColor "[{r:.6f} {g:.6f} {b:.6f} 0.000000]"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"\n'
             '    TextureMetalness "[0.000000 0.000000 0.000000 0.000000]"\n'
             '    TextureAmbientOcclusion "[1.000000 1.000000 1.000000 0.000000]"\n'
             '    TextureBlendMask "materials/default/default_blend.tga"\n'
             '    TextureTintMask "materials/default/default.tga"\n'
             '    TextureTranslucency "materials/default/default_trans.tga"\n}\n' )


def write_text( path, text ):
    data = text.encode( "utf-8" )
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes( data )


def write_maps( out, name, colour, rough, normal, metalness=0.0, illum=None, brightness=1.0, rough_size=None ):
    colour_file = f"{name}_color.png" if illum is not None or name == "ar_signs" else f"{name}_color.jpg"
    BX.save_rgb( out / colour_file, colour )
    BX.save_normal( out / f"{name}_normal.jpg", normal )
    BX.save_grey( out / f"{name}_rough.png", rough, rough_size )
    illum_path = None
    if illum is not None:
        BX.save_grey( out / f"{name}_illum.png", illum )
        illum_path = f"{RESOURCE_DIR}/{name}_illum.png"
    write_text( out / f"{name}.vmat", vmat( name, f"{RESOURCE_DIR}/{colour_file}", f"{RESOURCE_DIR}/{name}_normal.jpg",
                                            f"{RESOURCE_DIR}/{name}_rough.png", metalness, illum=illum_path, brightness=brightness ) )
    print( f"wrote {name}" )
    return colour, normal


OUTPOST_SURFACES = {
    # Coated thermal shells and dusty structural metal, without luminous cells or mirror-like finishes.
    "ar_ext_shell": ( ( 166, 160, 148 ), .08, .86 ),
    "ar_ext_metal": ( ( 94, 97, 94 ), .48, .68 ),
    "ar_ext_dark": ( ( 43, 49, 51 ), .3, .76 ),
    "ar_ext_base": ( ( 115, 101, 86 ), .0, .95 ),
    "ar_ext_ochre": ( ( 155, 91, 51 ), .08, .82 ),
}
OUTPOST_PAINTS = list( OUTPOST_SURFACES ) + [ "ar_ext_glazing", "ar_ext_lamp", "ar_ext_signs" ]


def build_outpost( out ):
    results = {}
    n, tile = px( 1024 ), 192.0
    ppi = n / tile
    x, y = grid( n, tile )
    for index, ( name, ( rgb, metalness, roughness ) ) in enumerate( OUTPOST_SURFACES.items() ):
        rng = np.random.default_rng( 420 + index )
        broad = noise( rng, ( n, n ), ( ppi, ppi ), 2.2, 160, 12 )
        fine = noise( rng, ( n, n ), ( ppi, ppi ), 1.1, 2, .2 )
        ix, iy = np.floor( x / 48 ).astype( int ), np.floor( y / 48 ).astype( int )
        edge_x, edge_y = np.minimum( x % 48, 48 - x % 48 ), np.minimum( y % 48, 48 - y % 48 )
        seam = 1 - smoothstep( .12, .45, np.minimum( edge_x, edge_y ) )
        variation = .98 + .025 * broad + .01 * fine
        if name == "ar_ext_shell":
            variation += .04 * ( periodic_hash( ix % 4, iy % 4, 59 ) - .5 )
        colour = lin( rgb )[None, None, :] * variation[..., None]
        if name in ( "ar_ext_shell", "ar_ext_metal" ):
            colour *= ( 1 - .16 * seam )[..., None]
        dust = smoothstep( .5, 2.2, broad ) * .08
        colour = mix( colour, lin( ( 151, 117, 88 ) ), dust )
        h = .004 * fine - .025 * seam if name != "ar_ext_base" else .04 * fine
        normal = normals( h, ( ppi, ppi ) )
        results[name] = write_maps( out, name, T.linear_to_srgb( colour ),
                                   np.clip( roughness + .015 * fine, .1, 1 ), normal, metalness )
    write_text( out / "ar_ext_glazing.vmat", vmat( "ar_ext_glazing", "materials/default/default_color.tga",
                rough_value=.31, metalness=.12, tint=( 36 / 255, 51 / 255, 55 / 255 ) ) )
    write_text( out / "ar_ext_lamp.vmat", vmat( "ar_ext_lamp", "materials/default/default_color.tga",
                rough_value=.7, illum="[1 1 1 0]", brightness=.7, tint=( 1, .76, .49 ) ) )
    # An opaque painted sign atlas: category labels, with no baked lights or alpha fringes.
    w, h = px( 2048 ), px( 256 )
    sign = np.ones( ( h, w, 3 ), np.float32 ) * lin( ( 38, 43, 44 ) )
    for slot, title in enumerate( ( "HABITAT", "AIRLOCK", "ATMOS", "SERVICE" ) ):
        width = w // 4
        lettering = text_layer( ( h, width ), [ ( "ARES / SURFACE SYSTEMS", FONT_TECH, h * .075, width * .09, h * .15, "l", .07 ),
                                               ( title, FONT_BOLD, h * .24, width * .09, h * .39, "l", .04 ) ] )
        region = sign[:, slot * width:( slot + 1 ) * width]
        region[:] = mix( region, lin( ( 192, 182, 158 ) ), lettering )
        region[int( h * .82 ):int( h * .87 ), int( width * .09 ):int( width * .6 )] = lin( ( 157, 91, 51 ) )
    BX.save_rgb( out / "ar_ext_signs_color.png", T.linear_to_srgb( sign ) )
    write_text( out / "ar_ext_signs.vmat", vmat( "ar_ext_signs", f"{RESOURCE_DIR}/ar_ext_signs_color.png", rough_value=.9 ) )
    print( "wrote outpost glazing, shielded lamps and signs" )
    return results


TILING = {
    "ar_floor": ( floor_plates, 0.55 ),
    "ar_wall": ( wall_panels, 0.35 ),
    "ar_concrete": ( concrete, 0.0 ),
    "ar_steel": ( painted_dark_steel, 0.5 ),
    "ar_brass": ( brushed_brass, 0.95 ),
    "ar_grating": ( bar_grating, 0.6 ),
    "ar_hazard": ( hazard_stripes, 0.0 ),
    "ar_regolith": ( regolith, 0.0 ),
    "ar_rock": ( rock, 0.0 ),
}
NAMES = list( TILING ) + [ "ar_terrain", "ar_tower", "ar_crate", "ar_signs", "ar_signs_lit", "ar_screens", "ar_plasma", "ar_dome",
                           "outpost", "flat", "sky" ]


def all_paints():
    """ Every paint name these materials give ares_map. """
    return ( list( TILING ) + [ "ar_terrain", "ar_tower", "ar_crate", "ar_signs", "ar_signs_lit", "ar_screens", "ar_plasma", "ar_dome" ]
             + OUTPOST_PAINTS + list( PAINTED ) + list( EMISSIVE ) + list( GLASS ) )


def build( name, out ):
    done = {}
    if name in TILING:
        draw, metalness = TILING[name]
        c, r, n = draw()
        done[name] = write_maps( out, name, c, r, n, metalness )
    elif name == "outpost":
        done.update( build_outpost( out ) )
    elif name == "ar_terrain":
        write_text( out / "ar_terrain.vmat", '\n'.join( [ '// Tools/ares_materials.py', 'Layer0', '{',
            '    shader "shaders/hc1_ares_land.shader"',
            f'    DustColor "{RESOURCE_DIR}/ar_regolith_color.jpg"',
            f'    DustNormal "{RESOURCE_DIR}/ar_regolith_normal.jpg"',
            f'    RockColor "{RESOURCE_DIR}/ar_rock_color.jpg"',
            f'    RockNormal "{RESOURCE_DIR}/ar_rock_normal.jpg"',
            '    g_flDustTile "640"', '    g_flRockTile "1024"', '}', '' ] ) )
        print( "wrote ar_terrain" )
    elif name == "ar_tower":
        c, r, n, illum = tower_cladding()
        done[name] = write_maps( out, name, c, r, n, 0.3, illum=illum, brightness=3.0 )
    elif name == "ar_crate":
        c, r, n = crate_atlas()
        done[name] = write_maps( out, name, c, r, n, 0.0 )
    elif name == "ar_signs":
        c, r, n = sign_atlas()
        done[name] = write_maps( out, name, c, r, n, 0.0, rough_size=( px( 1024 ), px( 1024 ) ) )
    elif name == "ar_signs_lit":
        c, illum = lit_atlas()
        BX.save_rgb( out / "ar_signs_lit_color.png", c )
        BX.save_grey( out / "ar_signs_lit_illum.png", illum )
        write_text( out / "ar_signs_lit.vmat", vmat( name, f"{RESOURCE_DIR}/ar_signs_lit_color.png", rough_value=0.3,
                                                     illum=f"{RESOURCE_DIR}/ar_signs_lit_illum.png", brightness=4.0 ) )
        done[name] = ( c, np.dstack( [ np.zeros_like( illum ), np.zeros_like( illum ), np.ones_like( illum ) ] ) )
        print( f"wrote {name}" )
    elif name == "ar_screens":
        c, illum = screen_atlas()
        BX.save_rgb( out / "ar_screens_color.png", c )
        BX.save_grey( out / "ar_screens_illum.png", illum )
        write_text( out / "ar_screens.vmat", vmat( name, f"{RESOURCE_DIR}/ar_screens_color.png", rough_value=0.65,
                                                   illum=f"{RESOURCE_DIR}/ar_screens_illum.png", brightness=0.75 )
                    .replace( 'F_SPECULAR "1"', 'F_SPECULAR "0"' ) )
        done[name] = ( c, np.dstack( [ np.zeros_like( illum ), np.zeros_like( illum ), np.ones_like( illum ) ] ) )
        print( f"wrote {name}" )
    elif name == "ar_plasma":
        c, illum = plasma()
        BX.save_rgb( out / "ar_plasma_color.png", c )
        BX.save_grey( out / "ar_plasma_illum.png", illum )
        write_text( out / "ar_plasma.vmat", plasma_vmat() )
        done[name] = ( c, np.dstack( [ np.zeros_like( illum ), np.zeros_like( illum ), np.ones_like( illum ) ] ) )
        print( f"wrote {name}" )
    elif name == "ar_dome":
        c, illum, r = dome_lattice()
        BX.save_rgb( out / "ar_dome_color.png", c )
        BX.save_grey( out / "ar_dome_illum.png", illum )
        BX.save_grey( out / "ar_dome_rough.png", r )
        write_text( out / "ar_dome.vmat", vmat( name, f"{RESOURCE_DIR}/ar_dome_color.png", rough=f"{RESOURCE_DIR}/ar_dome_rough.png",
                                                metalness=0.2, illum=f"{RESOURCE_DIR}/ar_dome_illum.png", brightness=3.0 ) )
        done[name] = ( c, np.dstack( [ np.zeros_like( illum ), np.zeros_like( illum ), np.ones_like( illum ) ] ) )
        print( f"wrote {name}" )
    elif name == "flat":
        for p, ( rgb, metal, rough ) in PAINTED.items():
            write_text( out / f"{p}.vmat", BX.painted_vmat( rgb, metal, rough ).replace( "boxyard_materials", "ares_materials" ) )
        for p, ( rgb, brightness ) in EMISSIVE.items():
            r, g, b = ( c / 255.0 for c in rgb )
            write_text( out / f"{p}.vmat", vmat( p, "materials/default/default_color.tga", rough_value=0.2,
                                                 illum="[1.000000 1.000000 1.000000 0.000000]", brightness=brightness,
                                                 tint=( r, g, b ) ) )
        for p, ( tint, roughness, absorption ) in GLASS.items():
            write_text( out / f"{p}.vmat", glass_vmat( tint, roughness, absorption ) )
        print( f"wrote {len( PAINTED )} flat paints, {len( EMISSIVE )} lights, {len( GLASS )} glasses" )
    elif name == "sky":
        import ares_sky
        ares_sky.main( out / "sky" )
    else:
        raise SystemExit( f"unknown texture {name}" )
    return done


def write_sheet( results, path ):
    tiles = []
    for name, ( colour, normal ) in results.items():
        img = Image.fromarray( BX.lit( colour, normal ).astype( np.uint8 ) )
        img.thumbnail( ( 1024, 512 ), Image.LANCZOS )
        canvas = Image.new( "RGB", ( 1024, 512 ), ( 16, 16, 16 ) )
        canvas.paste( img, ( 0, 0 ) )
        ImageDraw.Draw( canvas ).text( ( 6, 6 ), name, fill=( 255, 255, 255 ) )
        tiles.append( canvas )
    cols = 2
    rows = ( len( tiles ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( 1024 * cols, 512 * rows ), ( 16, 16, 16 ) )
    for k, t in enumerate( tiles ):
        sheet.paste( t, ( 1024 * ( k % cols ), 512 * ( k // cols ) ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    global SCALE
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"what to draw (default all: {', '.join( NAMES )})" )
    parser.add_argument( "--out", help="write somewhere else (for trying things out)" )
    parser.add_argument( "--sheet", help="also write a lit contact sheet here" )
    parser.add_argument( "--scale", type=float, default=1.0, help="draw at this share of the size (previews)" )
    args = parser.parse_args()
    SCALE = args.scale
    out = Path( args.out ) if args.out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    results = {}
    for name in args.names or NAMES:
        results.update( build( name, out ) )
    if args.sheet and results:
        write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
