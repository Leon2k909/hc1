"""
Cerro Blanco's own materials (Assets/materials/cerroblanco/), which Tools/cerroblanco_map.py paints with.

    python Tools/cerroblanco_materials.py [name ...] [--out <dir>] [--sheet <png>]

The museum is built the way the hilltop art museums of the 1990s were: cleft-cut travertine below, off-white enamelled
aluminium panels above, both on a 30-inch square module, on honed travertine paving. Nothing in the project looked like
any of it, so it's drawn here with numpy, from height fields in inches as belltower_materials' stone is:
- travertine: the walls' cleft-cut blocks, 30 inches high and 30 or 60 long, hung with open joints. Travertine splits
  along its bedding, so a cleft face is ridged along the beds, and pitted with the long voids the spring water left.
  Each block is its own cream to honey colour.
- paving: honed, filled cross-cut travertine in 30-inch squares with 3/16-inch sanded grout joints, weathered by years
  outdoors: a warm beige whose beds show as swirls of ivory and walnut, the voids filled with a greyer cement, grime
  along the joints, a few spills and chipped arrises. It tiles every 240 inches (8 x 8 slabs) at 4096 px.
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
import os
import time
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
TILES = { "travertine": TILE, "paving": 240.0, "honed": TILE, "panel": TILE }


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


def save_image( image, path ):
    """ Saves through a temporary file, retrying the rename for up to 10 s: the open editor compiles each map as it
    lands, and holds the next one's file open while it does. """
    path = Path( path )
    temp = path.with_name( f".{path.name}.tmp" )
    image.save( temp, format="PNG", optimize=True )
    for attempt in range( 40 ):
        try:
            os.replace( temp, path )
            return
        except OSError:
            if attempt == 39:
                raise
            time.sleep( 0.25 )


def save_grey( path, a ):
    save_image( Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), path )


def save_rgb( path, a ):
    save_image( Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" ), path )


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

# Close in tone, as the pictures' stone is: from a distance the blocks read as one wall, not a checkerboard.
TRAVERTINE = [ ( 224, 211, 186 ), ( 219, 205, 177 ), ( 227, 216, 195 ), ( 216, 202, 174 ), ( 222, 208, 181 ),
               ( 218, 207, 188 ), ( 225, 213, 190 ) ]


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
    base = palette[rng.integers( 0, len( palette ), count )] * rng.uniform( 0.975, 1.02, ( count, 1 ) )
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

# The paving tiles every 240 inches (8 x 8 slabs) at twice the size, the same 17 px an inch as the other stone: at 120
# inches its 16 slabs repeated every 10 feet across the courtyard.
PAVE_TILE = 240.0
PAVE_SIZE = 4096

# Classic cross-cut travertine, honed and filled, after years outdoors: a warm beige with ivory and walnut beds, close in
# tone slab to slab. It used to be a near-white cream (225, 214, 193), which the sun blew out (the user, 2026-10-09:
# "too bright"). A honed light travertine's albedo is about 0.45-0.5.
PAVING = [ ( 189, 177, 155 ), ( 185, 172, 149 ), ( 192, 181, 160 ), ( 183, 171, 150 ), ( 188, 175, 152 ),
           ( 186, 176, 157 ) ]
IVORY = ( 211, 202, 183 )     # the light beds
WALNUT = ( 156, 132, 98 )     # the dark ones
FILLER = ( 166, 159, 146 )    # the cement filler in the voids: greyer than the stone
GROUT = ( 152, 144, 130 )     # sanded grout, matched to the stone a shade down


def fblur( a, sigma ):
    """ A periodic Gaussian blur through the FFT, for big sigmas on big maps (sigma in px; ( rows, columns ) too). """
    sy, sx = sigma if isinstance( sigma, tuple ) else ( sigma, sigma )
    fy = np.fft.fftfreq( a.shape[0] )[:, None]
    fx = np.fft.rfftfreq( a.shape[1] )[None, :]
    g = np.exp( -2.0 * math.pi ** 2 * ( ( fy * sy ) ** 2 + ( fx * sx ) ** 2 ) )
    return np.fft.irfft2( np.fft.rfft2( a ) * g, s=a.shape )


def fcavity( height, ppu, radii=( 0.2, 0.8 ), weights=( 1.0, 0.5 ) ):
    return sum( w * np.maximum( fblur( height, r * ppu ) - height, 0.0 ) for r, w in zip( radii, weights ) )


def strata( rng, length=400.0, step=0.01 ):
    """ The beds the spring water laid, along a line down through them, step inches a sample: each bed's tone (about
    unit deviation, a correlated walk from bed to bed, a little graded within it), whether it's porous, and a thin
    dark seam at the top of some. Most beds are a fifth of an inch, a few over an inch. """
    m = int( length / step )
    tone = np.zeros( m )
    porous = np.zeros( m )
    t, level = 0.0, 0.0
    while t < length:
        thick = float( np.clip( rng.lognormal( math.log( 0.2 ), 0.9 ), 0.03, 2.5 ) )
        level = 0.75 * level + 0.66 * rng.standard_normal()
        i0, i1 = int( t / step ), min( m, int( ( t + thick ) / step ) + 1 )
        tone[i0:i1] = level + rng.normal( 0.0, 0.3 ) * np.linspace( -0.5, 0.5, i1 - i0 )
        porous[i0:i1] = float( rng.random() < 0.3 )
        if rng.random() < 0.22:
            w = max( 1, int( rng.uniform( 0.012, 0.04 ) / step ) )
            tone[i0:i0 + w] -= rng.uniform( 0.8, 1.6 )
        t += thick
    return tone, porous, step


def sample_strata( profile, t, ppu, grad ):
    """ The beds' tone and porosity at depth t, filtered to each px's footprint across them (grad: inches of depth an
    inch along the face), so beds crowded where the cut runs along them don't alias into noise. """
    tone, porous, step = profile
    length = len( tone ) * step
    footprint = np.maximum( 0.6 * grad / ppu, 0.03 )
    sigmas = 0.012 * 2.2 ** np.arange( 7 )
    level = np.clip( np.log( footprint / sigmas[0] ) / math.log( 2.2 ), 0, len( sigmas ) - 1 )
    tm = np.mod( t, length )
    out_tone = np.zeros_like( t )
    out_porous = np.zeros_like( t )
    xp = np.arange( len( tone ) ) * step
    for k, sigma in enumerate( sigmas ):
        weight = np.maximum( 0.0, 1.0 - np.abs( level - k ) )
        if not weight.any():
            continue
        a = ndimage.gaussian_filter1d( tone, sigma / step, mode="wrap" )
        b = ndimage.gaussian_filter1d( porous, max( sigma, 0.05 ) / step, mode="wrap" )
        out_tone += weight * np.interp( tm, xp, a, period=length )
        out_porous += weight * np.interp( tm, xp, b, period=length )
    return out_tone, out_porous


def honed_face( rng, n, ppu, slab, count, edge ):
    """ A honed, filled cross-cut face. The saw cut across the beds, which undulate, so each slab shows them as cloudy
    swirls of ivory and walnut. The voids, most in the porous beds, are filled with a greyer cement flush with the face,
    and a few have lost it. Then years outdoors: a mottle of weathering, dirt along the joints (edge: inches to the
    nearest, None for jointless stone), a few spills, and paths polished by feet.

    slab is each px's slab id (count of them). Each slab is its own piece of stone, from another part of the block and
    turned any of the eight ways. Returns the colour (linear), the face's fine height, the filled and open voids, and
    the roughness. """
    iy, ix = np.mgrid[0:n, 0:n].astype( np.int32 )
    turn = rng.integers( 0, 8, count )[slab]
    swap = ( turn & 4 ) > 0
    a = np.where( swap, ix, iy )
    b = np.where( swap, iy, ix )
    a = np.where( ( turn & 1 ) > 0, -a, a )
    b = np.where( ( turn & 2 ) > 0, -b, b )
    a = ( a + rng.integers( 0, n, count )[slab] ) % n
    b = ( b + rng.integers( 0, n, count )[slab] ) % n
    del iy, ix, swap, turn

    tile = n / ppu
    # The beds' depth under the face: broad undulations (periods of 6 inches to 3 feet) with smaller folds on them, and
    # a slight dip one way, so the swirls run a little along the slab.
    bed = ( 1.6 * noise( rng, n, 3.2, tile / 36.0, tile / 6.0 ) + 0.35 * noise( rng, n, 2.4, tile / 6.0, tile / 1.2 )
            + 0.06 * noise( rng, n, 1.6, tile / 1.2, tile / 0.3 ) )
    gy = ( np.roll( bed, -1, 0 ) - np.roll( bed, 1, 0 ) ) * 0.5 * ppu
    gx = ( np.roll( bed, -1, 1 ) - np.roll( bed, 1, 1 ) ) * 0.5 * ppu
    grad = np.hypot( gy, gx )[a, b]
    t = bed[a, b] + rng.uniform( 0, 400, count )[slab]
    del bed, gy, gx
    dip = rng.uniform( 0, 2 * math.pi, count )
    yy, xx = np.mgrid[0:n, 0:n] / ppu
    t += 0.05 * ( xx * np.cos( dip )[slab] + yy * np.sin( dip )[slab] )
    grad += 0.05
    del yy, xx
    tone, porous = sample_strata( strata( rng ), t, ppu, grad )
    del t, grad

    mean = to_linear( PAVING ).mean( axis=0 )
    palette = to_linear( PAVING )
    base = palette[rng.integers( 0, len( palette ), count )] * rng.uniform( 0.975, 1.025, ( count, 1 ) )
    stone = base[slab]
    tone = np.clip( tone, -3.0, 3.0 )
    stone = lerp( stone, stone * to_linear( IVORY ) / mean, 0.45 * smoothstep( 0.3, 2.2, tone ) )
    stone = lerp( stone, stone * to_linear( WALNUT ) / mean, 0.5 * smoothstep( -0.2, -2.2, tone ) )
    # The crystals: a fine grain, and a few sparkles of clear calcite.
    grain = noise( rng, n, 0.6, tile / 2.0, None )
    stone *= ( 1.0 + 0.018 * grain )[..., None]
    sparkle = smoothstep( 3.0, 3.6, noise( rng, n, 0.0, tile / 1.0, None ) )
    stone = lerp( stone, stone * 1.08, 0.5 * sparkle )

    # The voids: small rounded ones and a few longer, many more in the porous beds. Filled, they're what tells a plain
    # stretch of the stone from concrete.
    small = unit( ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ), 0.09 * ppu, mode="wrap" ) )
    large = unit( ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ), ( 0.22 * ppu, 0.5 * ppu ), mode="wrap" ) )
    lift = 0.8 * np.clip( porous, 0, 1 )
    voids = np.maximum( smoothstep( 2.65 - lift, 2.95 - lift, small ), smoothstep( 3.0 - lift, 3.3 - lift, large[a, b] ) )
    del small, large, porous, a, b
    lost = voids * ( noise( rng, n, 2.0, tile / 8.0, tile / 1.5 ) > 1.9 )
    filler = to_linear( FILLER ) * ( 1.0 + 0.03 * grain )[..., None]
    stone = lerp( stone, filler, 0.6 * voids )
    stone = lerp( stone, stone * 0.62, 0.8 * lost )

    # Outdoors: a broad mottle of weathering, grime along the joints, a few spills, and the paths feet take.
    mottle = noise( rng, n, 2.6, tile / 72.0, tile / 6.0 )
    stone *= ( 1.0 + 0.035 * mottle )[..., None]
    if edge is not None:
        streaky = smoothstep( -1.0, 1.0, noise( rng, n, 1.5, tile / 4.0, None ) )
        grime = np.exp( -np.maximum( edge, 0.0 ) / 0.7 ) * ( 0.65 + 0.35 * streaky )
        stone = lerp( stone, stone * to_linear( ( 120, 110, 95 ) ) / mean, 0.22 * grime )
    else:
        grime = np.zeros( ( n, n ) )
    spills = smoothstep( 2.3, 3.0, noise( rng, n, 3.0, tile / 10.0, tile / 1.5 ) )
    stone = lerp( stone, stone * to_linear( ( 172, 158, 136 ) ) / mean, 0.5 * spills )
    worn = noise( rng, n, 3.4, tile / 120.0, tile / 20.0 )

    fine = 0.0015 * noise( rng, n, 1.0, tile / 1.0, None ) - 0.004 * voids - 0.05 * lost
    rough = ( 0.66 + 0.03 * noise( rng, n, 1.0, tile / 2.0, None ) - 0.05 * smoothstep( 0.3, 1.8, worn )
              + 0.06 * grime + 0.04 * spills - 0.07 * voids * ( 1 - lost ) + 0.2 * lost )
    return stone, fine, voids, lost, rough


def paving( rng, n ):
    """ 30-inch slabs with 3/16-inch sanded grout joints a sixteenth under the face, the arrises eased, each slab a hair
    proud or shy of the next and a little out of level, and here and there an arris chipped. """
    ppu = n / PAVE_TILE
    y, x = np.mgrid[0:n, 0:n] / ppu
    across = int( PAVE_TILE / 30 )
    count = across * across
    slab = ( np.floor( y / 30.0 ) * across + np.floor( x / 30.0 ) ).astype( np.int32 )
    u, v = x % 30.0, y % 30.0
    del x, y
    wobble = 0.015 * noise( rng, n, 2.0, PAVE_TILE / 12.0, PAVE_TILE / 0.5 )
    edge = np.minimum( np.minimum( u, 30 - u ), np.minimum( v, 30 - v ) ) + wobble
    joint = 0.094
    inside = smoothstep( joint - 0.015, joint + 0.015, edge )
    eased = smoothstep( joint, joint + 0.09, edge )
    stone, fine, voids, lost, rough = honed_face( rng, n, ppu, slab, count, edge - joint )
    chips = smoothstep( 2.7, 3.3, unit( ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ), 0.3 * ppu, mode="wrap" ) ) )
    chips *= 1.0 - smoothstep( joint + 0.2, joint + 0.6, edge )
    lip = rng.normal( 0.0, 0.012, count )[slab]
    tilt = ( rng.normal( 0.0, 0.006, count )[slab] * ( u / 15.0 - 1.0 )
             + rng.normal( 0.0, 0.006, count )[slab] * ( v / 15.0 - 1.0 ) )
    face = 0.0625 + lip + tilt + fine - 0.025 * ( 1.0 - eased ) - 0.07 * chips
    sand = 0.004 * noise( rng, n, 0.8, PAVE_TILE / 1.0, None )
    height = sand + ( face - sand ) * inside
    grout = to_linear( GROUT ) * ( 0.94 + 0.05 * noise( rng, n, 1.2, PAVE_TILE / 2.0, None ) )[..., None]
    stone = lerp( stone, stone * 0.8, 0.6 * chips )
    hollow = fcavity( height, ppu )
    colour = lerp( grout, stone, inside ) * np.exp( -0.5 * hollow )[..., None]
    rough = np.clip( np.where( inside < 0.5, 0.9, rough + 0.15 * chips ), 0, 1 )
    return to_srgb( colour ), height, rough, hollow, ppu


def honed( rng, n ):
    """ The same stone with no joints, for copings, benches, steps and planters' edges. """
    ppu = n / TILE
    slab = np.zeros( ( n, n ), np.int32 )
    stone, fine, voids, lost, rough = honed_face( rng, n, ppu, slab, 1, None )
    hollow = fcavity( fine, ppu )
    return to_srgb( stone ), fine, np.clip( rough - 0.03, 0, 1 ), hollow, ppu


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
    white = to_linear( ( 212, 207, 198 ) ) * rng.uniform( 0.985, 1.012, ( 16, 1 ) )   # a light warm grey, as pictured
    stone = white[cell] * ( 1.0 + 0.006 * noise( rng, n, 1.0, 60, None ) )[..., None]
    # A faint grey wash down from each panel's top edge (rain), and some dust settled near the joints.
    rain = smoothstep( 1.0, 2.6, blur( noise( rng, n, 1.4, 8, 200 ), ( 3.0 * ppu, 0.08 * ppu ) ) ) * ( 1 - v / 30.0 )
    stone = lerp( stone, stone * 0.9, 0.35 * rain )
    stone = lerp( stone, stone * 0.93, 0.5 * ( 1 - bevel ) * inside )
    joint = to_linear( ( 104, 100, 93 ) ) * np.ones( ( n, n, 3 ) )
    colour = lerp( joint, stone, inside ) * np.exp( -0.8 * hollow )[..., None]
    rough = np.clip( 0.3 + 0.03 * rng.uniform( -1, 1, 16 )[cell] + 0.04 * noise( rng, n, 1.0, 60, None ) + 0.1 * rain, 0, 1 )
    rough = np.where( inside < 0.5, 0.9, rough )
    return to_srgb( colour ), height, rough, hollow, ppu


# Each drawn material: how it's drawn, its seed and its maps' size.
DRAWN = { "travertine": ( travertine, 11, SIZE ), "paving": ( paving, 12, PAVE_SIZE ), "honed": ( honed, 13, SIZE ),
          "panel": ( panel, 14, SIZE ) }
SHEETS = {}


def drawn_material( name, out ):
    draw, seed, size = DRAWN[name]
    colour, height, rough, hollow, ppu = draw( np.random.default_rng( seed ), size )
    normal = gl_normal( height, ppu, 1.0 )
    ao = np.clip( np.exp( -1.4 * hollow ), 0.0, 1.0 )
    save_rgb( out / f"{name}_color.png", colour )
    save_rgb( out / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( out / f"{name}_rough.png", rough )
    save_grey( out / f"{name}_ao.png", ao )
    r = RESOURCE_DIR
    write_vmat( out, f"cb_{name}", vmat( f"cb_{name}", f"{r}/{name}_color.png", f"{r}/{name}_normal.png", f"{r}/{name}_rough.png",
                                         f"{r}/{name}_ao.png" ) )
    SHEETS[name] = ( colour, normal, ppu )


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


# The galleries' names on their walls: grey letters, alpha tested, 8:1

LABELS = { "sur": "galería sur" }


def labels( out ):
    for key, text in LABELS.items():
        mask = Image.new( "L", ( SIGN_W, SIGN_H ), 0 )
        draw = ImageDraw.Draw( mask )
        draw.text( ( SIGN_W / 2, SIGN_H / 2 ), text, font=font( "Dinish-Regular.ttf", 170 ), fill=255, anchor="mm" )
        a = np.asarray( mask, float ) / 255.0
        grey = np.full( ( SIGN_H, SIGN_W, 3 ), 92.0 )
        save_rgb( out / f"label_{key}_color.png", grey )
        save_grey( out / f"label_{key}_trans.png", a )
        write_vmat( out, f"cb_label_{key}", vmat( f"cb_label_{key}", f"{RESOURCE_DIR}/label_{key}_color.png",
                                                  "materials/default/default_normal.tga", "[0.600000 0.600000 0.600000 0.000000]",
                                                  "materials/default/default_ao.tga", metal=0.6,
                                                  extra=( '    F_ALPHA_TEST "1"\n'
                                                          f'    TextureTranslucency "{RESOURCE_DIR}/label_{key}_trans.png"\n'
                                                          '    g_flAlphaTestReference "0.5"\n'
                                                          '    g_flAntiAliasedEdgeStrength "1"\n' ) ) )


# ---------------------------------------------------------------------------------------------------------------------

def missing( out=OUT_DIR ):
    """ Whether any map is missing (the PNGs live in Git LFS: a checkout without them gets them drawn again). """
    names = [ f"{name}_{kind}.png" for name in DRAWN for kind in ( "color", "normal", "rough", "ao" ) ]
    names += [ f"banner_{k}_color.png" for k in range( len( BANNERS ) ) ] + [ "sign_color.png", "sign_trans.png" ]
    names += [ f"label_{key}_{kind}.png" for key in LABELS for kind in ( "color", "trans" ) ]
    return [ name for name in names if not ( out / name ).exists() ]


def write_sheet( path ):
    tiles = []
    light = np.array( ( -0.5, 0.5, 0.7 ) )
    light /= np.linalg.norm( light )
    for name, ( colour, normal, ppu ) in SHEETS.items():
        crop = slice( 0, int( round( 60 * ppu ) ) )          # 60 inches of each, at 1024 px
        shade = np.clip( ( normal[crop, crop] * light ).sum( -1 ), 0, 1 ) * 0.75 + 0.35
        lit = np.clip( colour[crop, crop] * shade[..., None], 0, 255 ).astype( np.uint8 )
        tiles.append( np.asarray( Image.fromarray( lit, "RGB" ).resize( ( 1024, 1024 ), Image.LANCZOS ), float ) )
    if tiles:
        save_rgb( Path( path ), np.concatenate( tiles, axis=1 ) )
        print( f"wrote {path}" )


def main( argv=None ):
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help="only these (travertine, paving, honed, panel, banners, sign, labels)" )
    parser.add_argument( "--out", help="write here instead" )
    parser.add_argument( "--sheet", help="also write a lit sheet of the stone and panels" )
    args = parser.parse_args( argv )
    out = Path( args.out ) if args.out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    names = args.names or list( DRAWN ) + [ "banners", "sign", "labels" ]
    for name in names:
        if name in DRAWN:
            drawn_material( name, out )
        elif name == "banners":
            banners( out )
        elif name == "sign":
            sign( out )
        elif name == "labels":
            labels( out )
        print( f"drew {name}" )
    if args.sheet:
        write_sheet( args.sheet )


if __name__ == "__main__":
    main()
