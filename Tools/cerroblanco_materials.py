"""
Cerro Blanco's own materials (Assets/materials/cerroblanco/), which Tools/cerroblanco_map.py paints with.

    python Tools/cerroblanco_materials.py [name ...] [--out <dir>] [--sheet <png>]

The museum is built the way the hilltop art museums of the 1990s were: cleft-cut travertine below, off-white enamelled
aluminium panels above, both on a 30-inch square module, on honed travertine paving. Nothing in the project looked like
any of it, so it's drawn here with numpy, from height fields in inches as belltower_materials' stone is:
- travertine: the walls' cleft-cut blocks, 30 inches high and 30 or 60 long, hung with open joints. Travertine splits
  along its bedding, so a cleft face is ridged along the beds, and pitted with the long voids the spring water left.
  Each block is its own cream to honey colour.
- paving: honed travertine squares, 30 inches, with thin grouted joints. Its pits are filled, a little darker, and its
  veins run along each slab's bed.
- honed: the same honed stone with no joints, for copings, benches, steps and planters' edges.
- panel: the enamelled panels, 30 inches square with open joints, each a hair different and a little wavy, satin.
- banner_0..3: the exhibition banners hung down the fronts: a made-up museum's own shows, each with its own abstract
  picture, in Spanish (the museum is on a hill above a Mexican town).
- sign: the museum's name in bronze letters, alpha tested, for the travertine wall by the entrance.
The flat paints (white steel, the sculptures' red, glass...) are cerroblanco_map's, as text-only materials.

A material's .vmat is only rewritten when its text changes, so re-running doesn't recompile what hasn't changed. --out
writes somewhere else; --sheet writes a lit picture of each.
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import terrain_textures as T

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/cerroblanco"
RESOURCE_DIR = "materials/cerroblanco"
FONTS = ROOT / "Assets/fonts"

TILE = 120.0                 # every stone and panel material tiles every 120 inches: four 30-inch modules
SIZE = 2048

# Every material's tile, for cerroblanco_map's tile_overrides.
TILES = { "travertine": TILE, "paving": TILE, "honed": TILE, "panel": TILE }


# ---------------------------------------------------------------------------------------------------------------------
# Helpers (as belltower_materials')

def noise( rng, n, beta, fmin, fmax=None ):
    return T.spectral( rng, n, beta, fmin, fmax )


def blur( a, sigma ):
    return ndimage.gaussian_filter( a, sigma, mode="wrap" )


def smoothstep( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def to_linear( rgb ):
    c = np.clip( np.asarray( rgb, float ) / 255.0, 0.0, 1.0 )
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def to_srgb( c ):
    c = np.clip( c, 0.0, 1.0 )
    return 255.0 * np.where( c <= 0.0031308, c * 12.92, 1.055 * c ** ( 1 / 2.4 ) - 0.055 )


def lerp( a, b, t ):
    """ Colours a to b by t, a 2D weight per px. """
    t = np.asarray( t, float )
    return a + ( b - a ) * ( t[..., None] if t.ndim == 2 else t )


def unit( a ):
    return ( a - a.mean() ) / a.std()


def gl_normal( height, ppu, strength=1.0 ):
    hx = ( np.roll( height, -1, 1 ) - np.roll( height, 1, 1 ) ) * 0.5 * ppu * strength
    hr = ( np.roll( height, -1, 0 ) - np.roll( height, 1, 0 ) ) * 0.5 * ppu * strength
    n = np.stack( [ -hx, hr, np.ones_like( height ) ], -1 )
    return n / np.linalg.norm( n, axis=-1, keepdims=True )


def cavity( height, ppu, radii=( 0.3, 1.0, 3.0 ), weights=( 1.0, 0.6, 0.3 ) ):
    return sum( w * np.maximum( blur( height, r * ppu ) - height, 0.0 ) for r, w in zip( radii, weights ) )


def save_grey( path, a ):
    Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ).save( path, optimize=True )


def save_rgb( path, a ):
    Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( path, optimize=True )


def vmat( name, color, normal, rough, ao, metal=0.0, extra="" ):
    return ( "// Tools/cerroblanco_materials.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/complex.shader"\n'
             '    F_SPECULAR "1"\n'
             f"{extra}"
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metal:.2f}"\n'
             f'    TextureColor "{color}"\n'
             f'    TextureNormal "{normal}"\n'
             f'    TextureRoughness "{rough}"\n'
             f'    TextureAmbientOcclusion "{ao}"\n'
             '    g_vColorTint "[1.0 1.0 1.0 1.0]"\n'
             '    g_flModelTintAmount "1.0"\n'
             "}\n" )


def write_vmat( out, name, text ):
    path = out / f"{name}.vmat"
    if path.exists() and path.read_text( encoding="utf-8" ) == text:
        return
    path.write_text( text, encoding="utf-8", newline="\n" )


def courses( rng, n, ppu, lengths=( ( 30, 30, 60 ), ( 60, 60 ), ( 30, 60, 30 ), ( 30, 30, 30, 30 ), ( 60, 30, 30 ) ) ):
    """ The blocks of a 120-inch tile in 30-inch courses, each course a row of 30- and 60-inch blocks (so the joints
    stay on the 30-inch grid, as the module asks): per px its block id, u and v within it (inches) and the block's
    length (inches). """
    y, x = np.mgrid[0:n, 0:n] / ppu
    row = np.floor( y / 30.0 ).astype( int )
    v = y - row * 30.0
    block = np.zeros( ( n, n ), int )
    u = np.zeros( ( n, n ) )
    length = np.zeros( ( n, n ) )
    count = 0
    for r in range( int( TILE / 30 ) ):
        pattern = lengths[rng.integers( 0, len( lengths ) )]
        shift = 30 * rng.integers( 0, 4 )
        starts = np.cumsum( ( 0, ) + pattern[:-1] )
        sel = row == r
        xs = ( x[sel] - shift ) % TILE
        ids = np.searchsorted( starts, xs, side="right" ) - 1
        u[sel] = xs - starts[ids]
        length[sel] = np.asarray( pattern )[ids]
        block[sel] = count + ids
        count += len( pattern )
    return block, u, v, length, count


# ---------------------------------------------------------------------------------------------------------------------
# Travertine

TRAVERTINE = [ ( 224, 211, 186 ), ( 216, 200, 170 ), ( 229, 220, 201 ), ( 209, 194, 166 ), ( 221, 207, 179 ),
               ( 212, 203, 186 ), ( 226, 214, 192 ) ]


def travertine( rng, n ):
    """ Cleft-cut blocks: the face split along the bed, so ridged along it, a little out of true, pitted with long
    voids; 3/8-inch open joints, deep and dark; the arrises a little broken. """
    ppu = n / TILE
    block, u, v, length, count = courses( rng, n, ppu )
    edge = np.minimum( np.minimum( u, length - u ), np.minimum( v, 30.0 - v ) )
    edge = edge + 0.025 * noise( rng, n, 2.0, 10, 200 )
    joint = 0.19
    inside = smoothstep( joint, joint + 0.06, edge )
    arris = smoothstep( joint, joint + 0.7, edge )

    # The bed's ridges: noise drawn out along the bed (horizontal), at a few scales, with each block's own phase.
    beds = blur( rng.standard_normal( ( n, n ) ), ( 0.35 * ppu, 9.0 * ppu ) ) * 6.0
    beds2 = blur( rng.standard_normal( ( n, n ) ), ( 0.12 * ppu, 3.0 * ppu ) ) * 4.0
    swell = noise( rng, n, 2.2, 6, 120 )
    tilt = ( rng.normal( 0, 0.04, count )[block] * ( u / np.maximum( length, 1 ) - 0.5 )
             + rng.normal( 0, 0.05, count )[block] * ( v / 30.0 - 0.5 ) )
    proud = rng.normal( 0.0, 0.08, count )[block]
    # The voids: long thin pits along the bed.
    pits = smoothstep( 2.2, 3.0, unit( blur( rng.standard_normal( ( n, n ) ), ( 0.18 * ppu, 0.9 * ppu ) ) ) )
    small = smoothstep( 2.6, 3.4, unit( blur( rng.standard_normal( ( n, n ) ), 0.12 * ppu ) ) )
    beds = unit( beds )
    beds2 = unit( beds2 )
    face = proud + tilt + 0.09 * beds + 0.05 * beds2 + 0.07 * swell - 0.35 * pits - 0.12 * small
    height = -1.2 * ( 1 - inside ) + inside * ( 0.25 + face * ( 0.35 + 0.65 * arris ) )

    hollow = cavity( height, ppu )
    palette = to_linear( TRAVERTINE )
    base = palette[rng.integers( 0, len( palette ), count )] * rng.uniform( 0.95, 1.04, ( count, 1 ) )
    band = blur( rng.standard_normal( ( n, n ) ), ( 0.6 * ppu, 14.0 * ppu ) )
    band = band / band.std()
    honey = to_linear( ( 196, 170, 128 ) )
    stone = base[block] * ( 1.0 + 0.035 * band + 0.02 * noise( rng, n, 1.2, 60, None ) )[..., None]
    stone = lerp( stone, honey * stone / base[block].mean( axis=-1, keepdims=True ), 0.18 * smoothstep( 0.6, 2.0, band ) )
    stone = lerp( stone, stone * 0.55, 0.85 * pits )
    stone = lerp( stone, stone * 0.7, 0.6 * small )
    grime = smoothstep( 0.5, 2.2, noise( rng, n, 2.8, 1, 12 ) )
    stone = lerp( stone, stone * 0.86, 0.35 * grime )
    joint_colour = to_linear( ( 62, 58, 52 ) ) * np.ones( ( n, n, 3 ) )
    colour = lerp( joint_colour, stone, inside ) * np.exp( -0.9 * hollow )[..., None]
    rough = np.clip( 0.82 + 0.05 * noise( rng, n, 1.0, 80, None ) + 0.06 * pits - 0.04 * ( 1 - arris ) * inside, 0, 1 )
    rough = np.where( inside < 0.5, 0.95, rough )
    return to_srgb( colour ), height, rough, hollow, ppu


# ---------------------------------------------------------------------------------------------------------------------
# Honed travertine: the paving, and without joints for copings and benches

PAVING = [ ( 228, 217, 196 ), ( 222, 209, 186 ), ( 232, 223, 206 ), ( 218, 205, 182 ), ( 226, 214, 194 ) ]


def honed_face( rng, n, ppu, slab, count, angle ):
    """ A honed face: per slab its colour, veins along its bed (angle per slab), filled pits a little darker, a hint of
    traffic grime. Returns the colour (linear) and its fine height. """
    y, x = np.mgrid[0:n, 0:n].astype( float )
    palette = to_linear( PAVING )
    base = palette[rng.integers( 0, len( palette ), count )] * rng.uniform( 0.96, 1.04, ( count, 1 ) )
    along = blur( rng.standard_normal( ( n, n ) ), ( 0.5 * ppu, 12.0 * ppu ) )
    across = blur( rng.standard_normal( ( n, n ) ), ( 12.0 * ppu, 0.5 * ppu ) )
    vein = np.where( angle[slab] > 0, across, along )
    vein = vein / vein.std()
    pits_a = blur( rng.standard_normal( ( n, n ) ), ( 0.15 * ppu, 0.8 * ppu ) )
    pits_b = blur( rng.standard_normal( ( n, n ) ), ( 0.8 * ppu, 0.15 * ppu ) )
    pits = smoothstep( 2.4, 3.2, unit( np.where( angle[slab] > 0, pits_b, pits_a ) ) )
    stone = base[slab] * ( 1.0 + 0.03 * vein + 0.015 * noise( rng, n, 1.0, 100, None ) )[..., None]
    stone = lerp( stone, stone * to_linear( ( 205, 186, 150 ) ) / to_linear( ( 225, 213, 192 ) ), 0.35 * smoothstep( 0.8, 2.2, vein ) )
    stone = lerp( stone, stone * 0.8, 0.6 * pits )
    grime = smoothstep( 0.4, 2.4, noise( rng, n, 3.0, 1, 10 ) )
    stone = lerp( stone, stone * 0.9, 0.4 * grime )
    fine = 0.004 * noise( rng, n, 1.0, 100, None ) - 0.02 * pits
    return stone, fine, pits


def paving( rng, n ):
    ppu = n / TILE
    y, x = np.mgrid[0:n, 0:n] / ppu
    slab = ( np.floor( y / 30.0 ) * 4 + np.floor( x / 30.0 ) ).astype( int )
    count = 16
    u, v = x % 30.0, y % 30.0
    edge = np.minimum( np.minimum( u, 30 - u ), np.minimum( v, 30 - v ) ) + 0.02 * noise( rng, n, 2.0, 20, 300 )
    inside = smoothstep( 0.09, 0.14, edge )
    angle = rng.integers( 0, 2, count )
    stone, fine, pits = honed_face( rng, n, ppu, slab, count, angle )
    lip = rng.normal( 0, 0.012, count )[slab]
    height = inside * ( 0.06 + lip + fine + 0.02 * smoothstep( 0.1, 0.5, edge ) )
    grout = to_linear( ( 176, 166, 150 ) ) * ( 0.9 + 0.05 * noise( rng, n, 1.0, 100, None ) )[..., None]
    hollow = cavity( height, ppu, radii=( 0.2, 0.8 ), weights=( 1.0, 0.5 ) )
    colour = lerp( grout, stone, inside ) * np.exp( -1.5 * hollow )[..., None]
    rough = np.clip( 0.62 + 0.06 * noise( rng, n, 1.0, 60, None ) + 0.12 * pits, 0, 1 )
    rough = np.where( inside < 0.5, 0.92, rough )
    return to_srgb( colour ), height, rough, hollow, ppu


def honed( rng, n ):
    ppu = n / TILE
    slab = np.zeros( ( n, n ), int )
    stone, fine, pits = honed_face( rng, n, ppu, slab, 1, np.zeros( 1, int ) )
    stone *= ( 1.0 + 0.03 * noise( rng, n, 2.6, 2, 30 ) )[..., None]
    height = fine
    hollow = cavity( height, ppu, radii=( 0.2, 0.8 ), weights=( 1.0, 0.5 ) )
    rough = np.clip( 0.58 + 0.06 * noise( rng, n, 1.0, 60, None ) + 0.12 * pits, 0, 1 )
    return to_srgb( stone ), height, rough, hollow, ppu


# ---------------------------------------------------------------------------------------------------------------------
# Enamelled panels

def panel( rng, n ):
    """ 30-inch panels with 5/8-inch open joints: the joint's shadow, each panel's return (a rounded edge), a little
    oil-canning, a satin enamel each a hair different. """
    ppu = n / TILE
    y, x = np.mgrid[0:n, 0:n] / ppu
    cell = ( np.floor( y / 30.0 ) * 4 + np.floor( x / 30.0 ) ).astype( int )
    u, v = x % 30.0, y % 30.0
    edge = np.minimum( np.minimum( u, 30 - u ), np.minimum( v, 30 - v ) )
    inside = smoothstep( 0.29, 0.33, edge )
    bevel = smoothstep( 0.31, 0.55, edge )
    wave = blur( rng.standard_normal( ( n, n ) ), 4.0 * ppu )
    wave = wave / wave.std() * 0.015
    dome = 0.01 * np.sin( math.pi * u / 30 ) * np.sin( math.pi * v / 30 ) * rng.uniform( -1, 1, 16 )[cell]
    height = -0.6 * ( 1 - inside ) + inside * ( 0.1 * bevel + wave + dome )
    hollow = cavity( height, ppu, radii=( 0.2, 0.8 ), weights=( 1.0, 0.4 ) )
    white = to_linear( ( 236, 235, 230 ) ) * rng.uniform( 0.985, 1.012, ( 16, 1 ) )
    stone = white[cell] * ( 1.0 + 0.006 * noise( rng, n, 1.0, 60, None ) )[..., None]
    # A faint grey wash down from each panel's top edge (rain), and some dust settled near the joints.
    rain = smoothstep( 1.0, 2.6, blur( noise( rng, n, 1.4, 8, 200 ), ( 3.0 * ppu, 0.08 * ppu ) ) ) * ( 1 - v / 30.0 )
    stone = lerp( stone, stone * 0.9, 0.35 * rain )
    stone = lerp( stone, stone * 0.93, 0.5 * ( 1 - bevel ) * inside )
    joint = to_linear( ( 40, 40, 41 ) ) * np.ones( ( n, n, 3 ) )
    colour = lerp( joint, stone, inside ) * np.exp( -0.8 * hollow )[..., None]
    rough = np.clip( 0.3 + 0.03 * rng.uniform( -1, 1, 16 )[cell] + 0.04 * noise( rng, n, 1.0, 60, None ) + 0.1 * rain, 0, 1 )
    rough = np.where( inside < 0.5, 0.9, rough )
    return to_srgb( colour ), height, rough, hollow, ppu


DRAWN = { "travertine": ( travertine, 11 ), "paving": ( paving, 12 ), "honed": ( honed, 13 ), "panel": ( panel, 14 ) }
SHEETS = {}


def drawn_material( name, out ):
    draw, seed = DRAWN[name]
    colour, height, rough, hollow, ppu = draw( np.random.default_rng( seed ), SIZE )
    normal = gl_normal( height, ppu, 1.0 )
    ao = np.clip( np.exp( -1.4 * hollow ), 0.0, 1.0 )
    save_rgb( out / f"{name}_color.png", colour )
    save_rgb( out / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( out / f"{name}_rough.png", rough )
    save_grey( out / f"{name}_ao.png", ao )
    r = RESOURCE_DIR
    write_vmat( out, f"cb_{name}", vmat( f"cb_{name}", f"{r}/{name}_color.png", f"{r}/{name}_normal.png", f"{r}/{name}_rough.png",
                                         f"{r}/{name}_ao.png" ) )
    SHEETS[name] = ( colour, normal )


# ---------------------------------------------------------------------------------------------------------------------
# Banners: 1 x 3, printed on both sides of a heavy cloth

BANNER_W, BANNER_H = 512, 1536
MUSEUM = "MUSEO CERRO BLANCO"
BANNERS = [
    # ( title, subtitle, dates, background, ink )
    ( "FORMA Y VACÍO", "escultura del siglo XX", "14.10 — 02.03", ( 238, 232, 218 ), ( 30, 30, 32 ) ),
    ( "MAREAS", "pintura de la costa", "21.09 — 11.01", ( 22, 52, 92 ), ( 240, 236, 226 ) ),
    ( "TIERRA ROJA", "paisajes de la meseta", "05.10 — 16.02", ( 180, 64, 34 ), ( 250, 240, 222 ) ),
    ( "ROSTROS", "retratos 1900 — 1960", "30.09 — 25.01", ( 34, 96, 98 ), ( 246, 238, 228 ) ),
]


def font( name, size ):
    return ImageFont.truetype( str( FONTS / name ), size )


def banner_art( k, draw, box, rng, bg, ink ):
    """ Each show's picture, in box ( x0, y0, x1, y1 ). All made up: a sculpture study, the sea, a red landscape, a
    face. """
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if k == 0:
        draw.rectangle( box, fill=( 228, 220, 202 ) )
        draw.ellipse( ( x0 + w * 0.12, y0 + h * 0.18, x0 + w * 0.88, y0 + h * 0.62 ), fill=( 196, 48, 36 ) )
        draw.polygon( [ ( x0 + w * 0.2, y1 ), ( x0 + w * 0.55, y0 + h * 0.28 ), ( x0 + w * 0.68, y0 + h * 0.3 ),
                        ( x0 + w * 0.4, y1 ) ], fill=( 28, 28, 30 ) )
        draw.rectangle( ( x0 + w * 0.62, y0 + h * 0.66, x0 + w * 0.9, y0 + h * 0.7 ), fill=( 28, 28, 30 ) )
        draw.ellipse( ( x0 + w * 0.7, y0 + h * 0.74, x0 + w * 0.82, y0 + h * 0.83 ), fill=( 226, 182, 60 ) )
    elif k == 1:
        for i in range( 26 ):
            t = i / 25
            yy = y0 + h * t
            colour = tuple( int( a + ( b - a ) * t ) for a, b in zip( ( 120, 176, 206 ), ( 14, 40, 78 ) ) )
            pts = [ ( x0 + w * s / 40, yy + math.sin( s / 40 * math.pi * 3 + i * 0.9 ) * h * 0.018 ) for s in range( 41 ) ]
            draw.polygon( pts + [ ( x1, y1 ), ( x0, y1 ) ], fill=colour )
        draw.ellipse( ( x0 + w * 0.62, y0 + h * 0.06, x0 + w * 0.86, y0 + h * 0.06 + w * 0.24 ), fill=( 244, 226, 170 ) )
    elif k == 2:
        draw.rectangle( box, fill=( 236, 170, 90 ) )
        draw.ellipse( ( x0 + w * 0.3, y0 + h * 0.1, x0 + w * 0.7, y0 + h * 0.1 + w * 0.4 ), fill=( 250, 226, 150 ) )
        for i, ( top, colour ) in enumerate( ( ( 0.42, ( 200, 92, 46 ) ), ( 0.55, ( 160, 58, 34 ) ), ( 0.7, ( 112, 40, 30 ) ),
                                               ( 0.84, ( 70, 30, 26 ) ) ) ):
            pts = [ ( x0 + w * s / 30, y0 + h * ( top + 0.06 * math.sin( s / 30 * math.pi * ( 1.3 + i * 0.4 ) + i ) ) )
                    for s in range( 31 ) ]
            draw.polygon( pts + [ ( x1, y1 ), ( x0, y1 ) ], fill=colour )
    else:
        draw.rectangle( box, fill=( 222, 196, 186 ) )
        cx = x0 + w * 0.5
        draw.polygon( [ ( cx, y0 + h * 0.08 ), ( x0 + w * 0.82, y0 + h * 0.36 ), ( cx + w * 0.12, y0 + h * 0.78 ),
                        ( cx - w * 0.2, y0 + h * 0.74 ), ( x0 + w * 0.2, y0 + h * 0.32 ) ], fill=( 214, 126, 112 ) )
        draw.polygon( [ ( cx, y0 + h * 0.08 ), ( cx, y0 + h * 0.76 ), ( cx - w * 0.2, y0 + h * 0.74 ),
                        ( x0 + w * 0.2, y0 + h * 0.32 ) ], fill=( 166, 82, 84 ) )
        draw.ellipse( ( cx - w * 0.2, y0 + h * 0.3, cx - w * 0.07, y0 + h * 0.36 ), fill=( 30, 40, 44 ) )
        draw.ellipse( ( cx + w * 0.06, y0 + h * 0.3, cx + w * 0.19, y0 + h * 0.36 ), fill=( 30, 40, 44 ) )
        draw.polygon( [ ( cx - w * 0.02, y0 + h * 0.38 ), ( cx + w * 0.06, y0 + h * 0.52 ), ( cx - w * 0.04, y0 + h * 0.52 ) ],
                      fill=( 120, 56, 60 ) )
        draw.rectangle( ( cx - w * 0.12, y0 + h * 0.6, cx + w * 0.1, y0 + h * 0.625 ), fill=( 120, 34, 40 ) )
        draw.rectangle( ( x0, y0 + h * 0.86, x1, y1 ), fill=( 34, 96, 98 ) )


def banners( out ):
    rng = np.random.default_rng( 21 )
    for k, ( title, subtitle, dates, bg, ink ) in enumerate( BANNERS ):
        image = Image.new( "RGB", ( BANNER_W, BANNER_H ), bg )
        draw = ImageDraw.Draw( image )
        m = 34
        draw.text( ( BANNER_W / 2, 58 ), MUSEUM, font=font( "Dinish-Bold.ttf", 36 ), fill=ink, anchor="mm" )
        draw.rectangle( ( m, 86, BANNER_W - m, 89 ), fill=ink )
        art = Image.new( "RGB", ( BANNER_W - 2 * m, 920 ), bg )
        banner_art( k, ImageDraw.Draw( art ), ( 0, 0, art.width, art.height ), rng, bg, ink )
        image.paste( art, ( m, 120 ) )
        size = 92
        while font( "Mina-Bold.ttf", size ).getlength( title ) > BANNER_W - 2 * m:
            size -= 2
        draw.text( ( BANNER_W / 2, 1140 ), title, font=font( "Mina-Bold.ttf", size ), fill=ink, anchor="mm" )
        draw.text( ( BANNER_W / 2, 1222 ), subtitle, font=font( "Dinish-Regular.ttf", 36 ), fill=ink, anchor="mm" )
        draw.text( ( BANNER_W / 2, 1320 ), dates, font=font( "Dinish-Bold.ttf", 44 ), fill=ink, anchor="mm" )
        draw.rectangle( ( m, 1400, BANNER_W - m, 1402 ), fill=ink )
        draw.text( ( BANNER_W / 2, 1450 ), "EXPOSICIÓN TEMPORAL", font=font( "Dinish-Regular.ttf", 30 ), fill=ink, anchor="mm" )
        # Cloth: a little weave and the light through it.
        a = np.asarray( image, float )
        weave = 1.0 + 0.025 * ( np.sin( np.arange( BANNER_W ) * 1.7 )[None, :] * np.sin( np.arange( BANNER_H ) * 1.9 )[:, None] )
        a = a * weave[..., None] * ( 1.0 + 0.02 * rng.standard_normal( ( BANNER_H, BANNER_W ) ) )[..., None]
        save_rgb( out / f"banner_{k}_color.png", a )
        write_vmat( out, f"cb_banner_{k}", vmat( f"cb_banner_{k}", f"{RESOURCE_DIR}/banner_{k}_color.png",
                                                  "materials/default/default_normal.tga", "[0.850000 0.850000 0.850000 0.000000]",
                                                  "materials/default/default_ao.tga", extra='    F_RENDER_BACKFACES "1"\n' ) )


# ---------------------------------------------------------------------------------------------------------------------
# The museum's name: cast bronze letters on the travertine, alpha tested

SIGN_W, SIGN_H = 2048, 256


def sign( out ):
    mask = Image.new( "L", ( SIGN_W, SIGN_H ), 0 )
    draw = ImageDraw.Draw( mask )
    draw.text( ( SIGN_W / 2, SIGN_H / 2 ), MUSEUM, font=font( "Dinish-Bold.ttf", 190 ), fill=255, anchor="mm" )
    a = np.asarray( mask, float ) / 255.0
    rng = np.random.default_rng( 5 )
    bronze = np.array( ( 118, 90, 58 ), float ) * ( 1.0 + 0.06 * rng.standard_normal( ( SIGN_H, SIGN_W ) ) )[..., None]
    rim = np.clip( a - ndimage.uniform_filter( a, 5 ), 0, 1 )
    bronze = bronze * ( 1.0 + 0.6 * rim )[..., None]
    save_rgb( out / "sign_color.png", bronze )
    save_grey( out / "sign_trans.png", a )
    write_vmat( out, "cb_sign", vmat( "cb_sign", f"{RESOURCE_DIR}/sign_color.png", "materials/default/default_normal.tga",
                                      "[0.420000 0.420000 0.420000 0.000000]", "materials/default/default_ao.tga", metal=0.85,
                                      extra=( '    F_ALPHA_TEST "1"\n'
                                              f'    TextureTranslucency "{RESOURCE_DIR}/sign_trans.png"\n'
                                              '    g_flAlphaTestReference "0.5"\n'
                                              '    g_flAntiAliasedEdgeStrength "1"\n' ) ) )


# ---------------------------------------------------------------------------------------------------------------------

def missing( out=OUT_DIR ):
    """ Whether any map is missing (the PNGs live in Git LFS: a checkout without them gets them drawn again). """
    names = [ f"{name}_{kind}.png" for name in DRAWN for kind in ( "color", "normal", "rough", "ao" ) ]
    names += [ f"banner_{k}_color.png" for k in range( len( BANNERS ) ) ] + [ "sign_color.png", "sign_trans.png" ]
    return [ name for name in names if not ( out / name ).exists() ]


def write_sheet( path ):
    tiles = []
    light = np.array( ( -0.5, 0.5, 0.7 ) )
    light /= np.linalg.norm( light )
    for name, ( colour, normal ) in SHEETS.items():
        crop = slice( 0, 1024 )
        shade = np.clip( ( normal[crop, crop] * light ).sum( -1 ), 0, 1 ) * 0.75 + 0.35
        tiles.append( np.clip( colour[crop, crop] * shade[..., None], 0, 255 ) )
    if tiles:
        save_rgb( Path( path ), np.concatenate( tiles, axis=1 ) )
        print( f"wrote {path}" )


def main( argv=None ):
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help="only these (travertine, paving, honed, panel, banners, sign)" )
    parser.add_argument( "--out", help="write here instead" )
    parser.add_argument( "--sheet", help="also write a lit sheet of the stone and panels" )
    args = parser.parse_args( argv )
    out = Path( args.out ) if args.out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    names = args.names or list( DRAWN ) + [ "banners", "sign" ]
    for name in names:
        if name in DRAWN:
            drawn_material( name, out )
        elif name == "banners":
            banners( out )
        elif name == "sign":
            sign( out )
        print( f"drew {name}" )
    if args.sheet:
        write_sheet( args.sheet )


if __name__ == "__main__":
    main()
