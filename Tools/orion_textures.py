"""
Orion's materials: a rocket launch facility's concrete, steel, cases and signs at golden hour after rain, drawn with
numpy into Assets/materials/orion/ (the oa_ paints).

    python Tools/orion_textures.py [names ...] [--out <dir>] [--sheet <jpg>] [--scale 0.25]

Drawn at their real size, on Boxyard's and Riverdale's helpers (Tools/boxyard_materials.py, riverdale_materials.py).
Orion Aerospace, its planet-and-ring mark, ORN and every marking are the map's own. Run this before
Tools/orion_map.py. It writes:
    oa_wall         cast concrete, light grey: 3 m x 1.5 m formwork panels, their seams and ties, soot and rain stains,
                    cracks and chips (236 in tile). Its grain is Sources/Orion/v2/concrete-grain.png's, an
                    image_gen picture of 3 m of real concrete (Sources/Orion/v2/concrete-grain-prompt.txt)
    oa_wall_dark    the same, grimier: the lower walls, the undercroft, plinths and parapets
    oa_yard         the yard's slabs after rain: dark and wet, sawn joints, cracks, oil and tyre marks, standing water
                    that mirrors the sky (768 in tile)
    oa_deck         the deck's and walkways' slabs: the same, drier, the puddles smaller (384 in tile)
    oa_yellow, oa_steel, oa_orange, oa_red, oa_white_steel   painted steel, chipped and grimed
    oa_pipe         polished aluminium jacketing: the big fuel lines, the silver pipes
    oa_olive, oa_case   moulded olive and charcoal equipment cases
    oa_tarp         an olive tarpaulin, wet and creased
    oa_hazard, oa_grating   yellow and black stripes; galvanised bar grating, alpha tested
    oa_rocket       the launch vehicle's white skin: panel seams, rivet lines, scorching low down
    oa_radome       the radome's white panels: a geodesic grid of triangles and its seams
    oa_hill         dry hillside: golden grass, scrub and earth, for the near slopes
    oa_letters_dark, oa_letters_light   painted lettering and the mark, alpha tested, from one atlas (LETTERS)
    oa_plates       signs and pictures: the fire point sign, warnings, posters, the whiteboard, the flag (PLATES)
    oa_screens      the control rooms' monitors and CCTV walls, self-lit (SCREENS)
and flat paints (PAINTED), the lamps among them self-lit.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import boxyard_materials as BM  # noqa: E402
import riverdale_materials as RM  # noqa: E402

T = BM.T
lin, mix, smoothstep = BM.lin, BM.mix, BM.smoothstep

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/orion"
RESOURCE_DIR = "materials/orion"
DEFAULT_AO = "materials/default/default_ao.tga"
FONTS = ROOT / "Assets/fonts"
GRAIN = ROOT / "Sources/Orion/v2/concrete-grain.png"

SCALE = 1.0

TILES = { "oa_wall": 236.0, "oa_wall_dark": 236.0, "oa_yard": 768.0, "oa_deck": 384.0, "oa_yellow": 48.0, "oa_steel": 48.0,
          "oa_orange": 64.0, "oa_gantry": 64.0, "oa_red": 48.0, "oa_white_steel": 96.0, "oa_pipe": 64.0, "oa_olive": 48.0, "oa_case": 48.0,
          "oa_tarp": 96.0, "oa_tarp_grey": 96.0, "oa_hazard": 32.0, "oa_grating": 24.0, "oa_rocket": 120.0, "oa_radome": 240.0, "oa_hill": 1600.0, "oa_hill_far": 9000.0 }


def px( n ):
    return max( 16, int( round( n * SCALE ) ) )


def field( rng, n, tile ):
    ppi = n / tile

    def nz( beta, longest, shortest=None ):
        return BM.noise( rng, ( n, n ), ( ppi, ppi ), beta, longest, shortest )

    y, x = np.mgrid[0:n, 0:n].astype( np.float32 ) / ppi
    return nz, x, tile - y, ppi


def cracks( rng, n, ppi, tile, count, length=( 20, 90 ), width=0.08, branch=0.35 ):
    """ Hairline cracks: random walks that wander and fork, drawn on a wrapping canvas. Returns the mask (0..1). """
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( count ):
        x, z = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.uniform( 0, 2 * math.pi )
        L = rng.uniform( *length )
        pts = [ ( x, z ) ]
        step = 1.2
        for _ in range( int( L / step ) ):
            a += rng.normal( 0, 0.35 )
            x += math.cos( a ) * step
            z += math.sin( a ) * step
            pts.append( ( x, z ) )
            if rng.random() < branch * step / L * 4 and len( pts ) > 4:
                b = a + rng.choice( [ -1, 1 ] ) * rng.uniform( 0.5, 1.1 )
                bx, bz = x, z
                sub = [ ( bx, bz ) ]
                for _ in range( int( rng.uniform( 6, 25 ) / step ) ):
                    b += rng.normal( 0, 0.4 )
                    bx += math.cos( b ) * step
                    bz += math.sin( b ) * step
                    sub.append( ( bx, bz ) )
                cv.line( sub, width * 0.8, rng.uniform( 0.5, 0.9 ) )
        cv.line( pts, width * rng.uniform( 0.8, 1.6 ), rng.uniform( 0.6, 1.0 ) )
    return np.clip( cv.result(), 0, 1 )


def runs_down( sources, ppi, length ):
    return RM.runs_down( sources, ppi, length )


# ---------------------------------------------------------------------------------------------------------------------
# Concrete

def grain( n, repeats ):
    """ The image_gen concrete's linear colour, tiled repeats x repeats across n pixels, its mean set to 1. """
    src = Image.open( GRAIN ).convert( "RGB" ).resize( ( n // repeats, n // repeats ), Image.LANCZOS )
    a = T.srgb_to_linear( np.asarray( src, np.float32 ) )
    a = np.tile( a, ( repeats, repeats, 1 ) )
    if a.shape[0] != n:
        a = np.asarray( Image.fromarray( np.clip( T.linear_to_srgb( a ), 0, 255 ).astype( np.uint8 ) ).resize( ( n, n ) ), np.float32 )
        a = T.srgb_to_linear( a )
    return a / a.reshape( -1, 3 ).mean( axis=0 )


def concrete( seed=11, base=( 150, 150, 147 ), grime=0.35, n=None ):
    """ Cast concrete: formwork panels 118 in wide and 59 in tall (each a slightly different pour), their seams' fins,
    tie holes, the image_gen grain, soot patches and rain runs down from the ties and seams, cracks and chips. """
    n = n or px( 2048 )
    tile = TILES["oa_wall"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    g = grain( n, 2 )
    colour = lin( base )[None, None, :] * g
    cure, mid, fine = nz( 2.8, 180, 18 ), nz( 2.0, 24, 1.5 ), nz( 0.7, 0.6, 0.1 )
    colour *= ( 1.0 + 0.04 * cure + 0.02 * mid )[..., None]
    pw, ph = 118.0, 59.0
    pi, pj = np.floor( x / pw ).astype( int ), np.floor( z / ph ).astype( int )
    offsets = rng.normal( 0, 0.045, ( 2, 4 ) ).astype( np.float32 )
    colour *= ( 1.0 + offsets[pi % 2, pj % 4] )[..., None]
    rough = 0.84 + 0.05 * mid
    height = 0.03 * mid + 0.025 * fine
    sx = np.minimum( x % pw, pw - x % pw )
    sz = np.minimum( z % ph, ph - z % ph )
    seam = np.minimum( sx, sz )
    fin = np.exp( -( seam / 0.22 ) ** 2 )
    colour *= ( 1.0 - 0.22 * fin )[..., None]
    height += 0.05 * fin - 0.08 * np.exp( -( seam / 0.6 ) ** 2 )
    hx, hz = x % pw, z % ph
    holes = np.zeros_like( x )
    for cx in ( pw * 0.25, pw * 0.75 ):
        for cz in ( ph * 0.5, ):
            d = np.sqrt( ( hx - cx ) ** 2 + ( hz - cz ) ** 2 )
            holes = np.maximum( holes, smoothstep( 0.8, 0.55, d ) )
    colour = mix( colour, lin( ( 78, 78, 76 ) ), holes * 0.85 )
    height -= 0.18 * holes
    # Soot and grime: big soft patches, darker in their cores (the picture's walls are mottled with them).
    patches = nz( 2.6, 140, 10 ) + 0.5 * nz( 2.0, 30, 3 )
    soot = smoothstep( 0.2, 1.8, patches ) * ( 0.55 + 0.45 * grime )
    colour = mix( colour, colour * 0.42 + lin( ( 20, 19, 18 ) ), soot[..., None] * ( 0.55 + 0.3 * grime ) )
    # Rain runs: from the tie holes and the panels' top seams, streaking down.
    src = holes * 0.6 + np.exp( -( ( z % ph ) / 0.7 ) ** 2 ) * smoothstep( 0.6, 1.6, nz( 1.6, 20, 2 ) ) * 0.8
    src += ( rng.random( ( n, n ) ) < 0.0004 ).astype( np.float32 ) * 2.0
    runs = np.clip( runs_down( ndimage.gaussian_filter( src, ( 0.5, 2.0 ), mode="wrap" ), ppi, 40.0 ) * 3.0, 0, 1 )
    runs *= 0.5 + 0.5 * smoothstep( -1.0, 1.0, nz( 1.8, 12, 1 ) )
    colour = mix( colour, colour * 0.55, runs[..., None] * ( 0.5 + 0.4 * grime ) )
    # Efflorescence: pale bloom under some seams.
    bloom = np.clip( runs_down( ( np.exp( -( ( z % ph ) / 0.8 ) ** 2 ) * smoothstep( 1.2, 2.2, nz( 1.6, 30, 3 ) ) ), ppi, 14.0 ) * 2.5, 0, 1 )
    colour = mix( colour, lin( ( 196, 196, 190 ) ), bloom[..., None] * 0.35 )
    crack = cracks( rng, n, ppi, tile, 14, ( 30, 140 ), 0.14 )
    colour = mix( colour, lin( ( 30, 30, 30 ) ), crack[..., None] * 0.8 )
    height -= 0.12 * crack
    chips = smoothstep( 2.5, 2.9, nz( 1.4, 3, 0.2 ) )
    colour = mix( colour, colour * 1.25, chips[..., None] * 0.6 )
    height -= 0.1 * chips
    rough = np.clip( rough + 0.06 * soot - 0.05 * runs, 0.4, 1.0 )
    return colour, rough, height, ppi


def slabs( seed, tile_key, slab=192.0, wet=1.0, puddles=1.0, base=( 120, 118, 114 ), n=None, rough_add=0.0, film=0.0 ):
    """ Slabs after rain: sawn joints with dark sealant, cracks, damp darkening, oil, tyre marks and standing water in
    the dips (glassy and dark, the texture flat under it). film is the share of the slabs still under a thin water film
    (glossy, darker), in drifts that follow the slabs' falls; the rest has dried to a damp satin. The puddles' edges are
    broken and soft: water creeps into the texture's lows, so the gloss fades out over the last of the dip. """
    n = n or px( 4096 if tile_key == "oa_yard" else 2048 )
    tile = TILES[tile_key]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    g = grain( n, max( 1, int( round( tile / 118.0 ) ) ) )
    cure, mid, fine = nz( 2.8, 300, 30 ), nz( 2.0, 30, 2 ), nz( 0.6, 0.6, 0.19 )
    colour = lin( base )[None, None, :] * g * ( 1.0 + 0.07 * cure + 0.04 * mid + 0.04 * fine )[..., None]
    si, sj = np.floor( x / slab ).astype( int ), np.floor( z / slab ).astype( int )
    k = int( round( tile / slab ) )
    offs = rng.normal( 0, 0.1, ( k, k ) ).astype( np.float32 )
    colour *= ( 1.0 + offs[si % k, sj % k] )[..., None]
    joint = np.minimum( np.minimum( x % slab, slab - x % slab ), np.minimum( z % slab, slab - z % slab ) )
    spall = smoothstep( 1.4, 2.6, nz( 1.4, 10, 0.4 ) )
    groove = smoothstep( 0.8 + spall, 0.3, joint )
    colour = mix( colour, lin( ( 14, 14, 14 ) ), groove[..., None] * 0.92 )
    # Water lies along the joints: a damp, darker, glossier band either side of each.
    seam = smoothstep( 5.0, 0.8, joint ) * ( 1 - groove )
    height = 0.03 * mid + 0.03 * fine - 0.4 * groove
    crack = cracks( rng, n, ppi, tile, int( 26 * ( tile / 768.0 ) ** 2 * 4 ), ( 40, 220 ), 0.3, branch=0.5 )
    colour = mix( colour, lin( ( 14, 14, 14 ) ), crack[..., None] * 0.85 )
    height -= 0.2 * crack
    patch = smoothstep( 1.2, 1.6, nz( 2.4, 90, 8 ) )
    colour = mix( colour, colour * 0.8 + lin( ( 12, 12, 12 ) ), patch[..., None] * 0.5 )
    damp = ( 0.55 + 0.45 * smoothstep( -1.2, 1.0, nz( 2.4, 200, 20 ) ) ) * wet
    colour = colour * ( 1.0 - 0.45 * damp / max( wet, 1.0 ) )[..., None] * ( 1.0 - 0.3 * seam )[..., None]
    rough = np.clip( 0.62 + rough_add - 0.32 * damp + 0.05 * mid - 0.15 * seam, 0.08, 1.0 )
    if film > 0:
        # The film: drifts of glossy water across the slabs, thinning to a sheen at their edges.
        t = -0.25 - 1.2 * ( film - 0.5 )
        drift = nz( 2.2, 180, 6 ) + 0.45 * nz( 1.6, 30, 1.5 )
        fl = smoothstep( t - 0.35, t + 0.35, drift )
        colour = mix( colour, colour * 0.72, fl[..., None] )
        rough = mix( rough, 0.07 + 0.05 * smoothstep( -1.0, 1.0, mid ), fl )
    oil = smoothstep( 1.5, 2.7, nz( 2.0, 40, 3 ) )
    colour = mix( colour, lin( ( 20, 18, 16 ) ), oil[..., None] * 0.6 )
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( int( 70 * ( tile / 768.0 ) ** 2 * 2 ) ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.choice( [ 0.0, math.pi / 2 ] ) + rng.normal( 0, 0.25 )
        L = rng.uniform( 60, 300 )
        bend = rng.normal( 0, 0.002 )
        for off in ( -14.0, 14.0 ):
            pts = []
            for t in np.linspace( 0, 1, 16 ):
                s = L * t
                ang = a + bend * s
                pts.append( ( cx + math.cos( ang ) * s - math.sin( a ) * off, cz + math.sin( ang ) * s + math.cos( a ) * off ) )
            cv.line( pts, rng.uniform( 4, 7 ), rng.uniform( 0.15, 0.45 ) )
    tyres = ndimage.gaussian_filter( cv.result(), 1.5, mode="wrap" )
    colour = mix( colour, colour * 0.55, tyres[..., None] * 0.7 )
    # Puddles: where the slab dips, shallow and glassy; damp darker halos round them.
    dip = nz( 2.4, 260, 20 ) + 0.4 * nz( 1.8, 40, 4 ) + 0.3 * groove + 0.3 * nz( 1.2, 10, 0.6 )
    lo = 1.35 - 0.45 * puddles
    puddle = smoothstep( lo, lo + 0.34, dip )
    halo = smoothstep( lo - 0.5, lo, dip ) * ( 1 - puddle )
    colour = mix( colour, colour * 0.75, halo[..., None] * 0.5 * wet )
    rough = mix( rough, rough * 0.6, halo * wet )
    colour = mix( colour, colour * 0.5 + lin( ( 8, 9, 11 ) ), puddle[..., None] * 0.85 )
    rough = mix( rough, 0.02, puddle )
    height = mix( height, -0.05, puddle )
    rough = np.clip( rough - 0.05 * tyres, 0.02, 1.0 )
    return colour, rough, height, ppi


# ---------------------------------------------------------------------------------------------------------------------
# Steel, cases, cloth

def painted( seed, colour, tile, chips=0.4, rough=0.45, grime=0.4, bare=( 64, 64, 66 ), rust=0.0, n=None ):
    n = n or px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    c = lin( colour )[None, None, :] * ( 1.0 + 0.04 * nz( 2.4, 30, 2 ) + 0.015 * nz( 0.8, 0.8, 0.1 ) )[..., None]
    r = np.full( ( n, n ), rough, np.float32 ) + 0.04 * nz( 2.0, 10, 1 )
    h = 0.004 * nz( 1.0, 1, 0.1 )
    chip = smoothstep( 2.4 - chips, 2.7 - chips, nz( 1.6, 6, 0.15 ) + 0.4 * nz( 0.8, 0.6, 0.08 ) )
    c = mix( c, lin( bare ), chip[..., None] )
    r = mix( r, 0.55, chip )
    h -= 0.01 * chip
    rusty = np.clip( smoothstep( 2.6, 3.0, nz( 1.6, 4, 0.2 ) ) * chip + rust * smoothstep( 0.6, 2.0, nz( 2.2, 14, 1 ) ), 0, 1 )
    c = mix( c, BM.RUST, rusty[..., None] * 0.85 )
    src = ( rng.random( ( n, n ) ) < 0.0003 + 0.001 * rust ).astype( np.float32 )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.5 ), mode="wrap" ) * 4
    runs = np.clip( runs_down( src, ppi, 10.0 + 20 * rust ) * 4.0, 0, 1 )
    c = mix( c, mix( c * 0.7, BM.RUST_STAIN, rust ), runs[..., None] * ( grime + rust ) * 0.8 )
    dirt = smoothstep( 0.4, 2.2, nz( 2.4, 20, 2 ) ) * grime
    c = mix( c, BM.GRIME, dirt[..., None] * 0.3 )
    r = np.clip( r + 0.15 * dirt + 0.2 * rusty, 0.05, 1 )
    return c, r, h, ppi


def pipe_jacket( seed=51, n=None ):
    """ Aluminium jacketing over lagging, polished by the weather: brushed along the pipe, its overlaps' seams, smudges,
    the odd dent. """
    n = n or px( 1024 )
    tile = TILES["oa_pipe"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    brush = ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 0.4, 22 ), mode="wrap" )
    brush /= brush.std() + 1e-6
    c = lin( ( 196, 200, 202 ) )[None, None, :] * ( 1.0 + 0.03 * brush + 0.05 * nz( 2.4, 30, 3 ) )[..., None]
    r = 0.2 + 0.04 * brush + 0.08 * smoothstep( 0.5, 2.0, nz( 2.2, 16, 2 ) )
    lap = np.exp( -( ( x % 36.0 ) / 0.25 ) ** 2 )
    c = mix( c, c * 0.55, lap[..., None] * 0.8 )
    h = -0.05 * smoothstep( 2.0, 2.6, nz( 2.4, 8, 1.5 ) ) + 0.002 * brush + 0.05 * lap
    smudge = smoothstep( 1.0, 2.4, nz( 2.2, 20, 2 ) )
    c = mix( c, c * 0.68, smudge[..., None] * 0.6 )
    r = r + 0.1 * smudge
    return c, np.clip( r, 0.08, 1 ), h, ppi


def tarp( seed=61, n=None, base=( 96, 104, 84 ) ):
    """ An olive PVC tarpaulin pulled over a load: creases and sags, the weave, wet and glossy where water sits. """
    n = n or px( 1024 )
    tile = TILES["oa_tarp"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    folds = nz( 2.2, 30, 2 ) + 0.6 * np.abs( nz( 1.8, 12, 1 ) )
    weave = 0.5 + 0.5 * np.sin( x * 2 * math.pi / 0.12 ) * np.sin( z * 2 * math.pi / 0.12 )
    c = lin( base )[None, None, :] * ( 1.0 + 0.1 * folds + 0.03 * weave )[..., None]
    wetness = smoothstep( 0.4, 1.6, nz( 2.4, 40, 4 ) )
    c = mix( c, c * 0.7, wetness[..., None] * 0.5 )
    c = mix( c, BM.GRIME, smoothstep( 0.8, 2.2, nz( 2.4, 20, 2 ) )[..., None] * 0.25 )
    r = 0.45 - 0.33 * wetness + 0.05 * weave
    h = 0.25 * folds + 0.01 * weave
    return c, np.clip( r, 0.08, 1 ), h, ppi


def rocket_skin( seed=71, n=None ):
    """ The launch vehicle's white skin: barrel panels 60 in tall and 30 round, their seams and rivet rows, a faint
    stained grime that runs down, scorching towards the bottom of the tile (the engines' end sits low on the model). """
    n = n or px( 2048 )
    tile = TILES["oa_rocket"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    c = lin( ( 232, 232, 226 ) )[None, None, :] * ( 1.0 + 0.025 * nz( 2.4, 40, 3 ) + 0.01 * nz( 0.8, 0.5, 0.1 ) )[..., None]
    pw, ph = 30.0, 60.0
    sx, sz = np.minimum( x % pw, pw - x % pw ), np.minimum( z % ph, ph - z % ph )
    seam = np.exp( -( np.minimum( sx, sz ) / 0.15 ) ** 2 )
    rivets = ( np.exp( -( ( sz - 1.2 ) / 0.25 ) ** 2 ) * ( np.cos( x * 2 * math.pi / 1.5 ) > 0.92 ) +
               np.exp( -( ( sx - 1.2 ) / 0.25 ) ** 2 ) * ( np.cos( z * 2 * math.pi / 1.5 ) > 0.92 ) )
    c = mix( c, lin( ( 120, 122, 124 ) ), np.clip( seam * 0.7 + rivets * 0.4, 0, 1 )[..., None] )
    src = ( rng.random( ( n, n ) ) < 0.0002 ).astype( np.float32 ) * 2 + seam * 0.04
    runs = np.clip( runs_down( ndimage.gaussian_filter( src, ( 0.5, 2 ), mode="wrap" ), ppi, 30.0 ) * 3, 0, 1 )
    c = mix( c, lin( ( 170, 166, 156 ) ), runs[..., None] * 0.35 )
    r = 0.42 + 0.05 * nz( 2.0, 10, 1 ) + 0.1 * runs
    h = -0.06 * seam + 0.03 * rivets
    return c, np.clip( r, 0.1, 1 ), h, ppi


def radome( seed=81, n=None ):
    """ A radome's fibreglass panels: a triangular grid 40 in a side (a geodesic dome's panels look so up close), their
    seams darker and raised, each panel a touch different, weathered. """
    n = n or px( 2048 )
    tile = TILES["oa_radome"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    s = tile / 6.0
    h3 = s * math.sqrt( 3 ) / 2
    # Distance to the nearest line of the three families.
    d0 = np.abs( ( ( z / h3 ) + 0.5 ) % 1.0 - 0.5 ) * h3
    u = ( x * math.sqrt( 3 ) / 2 + z * 0.5 ) / h3
    w = ( -x * math.sqrt( 3 ) / 2 + z * 0.5 ) / h3
    d1 = np.abs( ( u + 0.5 ) % 1.0 - 0.5 ) * h3
    d2 = np.abs( ( w + 0.5 ) % 1.0 - 0.5 ) * h3
    d = np.minimum( np.minimum( d0, d1 ), d2 )
    seam = np.exp( -( d / 0.5 ) ** 2 )
    cell = ( np.floor( z / h3 ) * 7 + np.floor( u ) * 13 + np.floor( w ) * 5 ).astype( int )
    tone = rng.normal( 0, 0.03, 64 ).astype( np.float32 )[cell % 64]
    c = lin( ( 214, 214, 208 ) )[None, None, :] * ( 1.0 + tone + 0.03 * nz( 2.2, 30, 2 ) )[..., None]
    c = mix( c, lin( ( 150, 150, 146 ) ), seam[..., None] * 0.6 )
    c = mix( c, BM.GRIME, smoothstep( 1.0, 2.4, nz( 2.4, 60, 6 ) )[..., None] * 0.2 )
    r = 0.6 + 0.05 * nz( 2.0, 10, 1 )
    h = 0.08 * seam
    return c, np.clip( r, 0.1, 1 ), h, ppi


def hill( seed=91, n=None ):
    """ A dry Mediterranean hillside seen from a few hundred metres: golden grass, dark clumps of scrub and holm oak,
    bare earth and rock showing through. """
    n = n or px( 2048 )
    tile = TILES["oa_hill"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    grass = lin( ( 152, 132, 84 ) )
    dry = lin( ( 176, 156, 110 ) )
    scrub = lin( ( 58, 70, 40 ) )
    earth = lin( ( 132, 104, 76 ) )
    a = nz( 2.4, 300, 10 )
    c = mix( grass[None, None, :] * np.ones( ( n, n, 1 ), np.float32 ), dry, smoothstep( -0.5, 1.0, a )[..., None] )
    bush = smoothstep( 0.7, 1.2, nz( 1.6, 40, 4 ) + 0.5 * nz( 2.4, 200, 20 ) )
    c = mix( c, scrub * ( 1.0 + 0.2 * nz( 1.0, 4, 1 ) )[..., None], bush[..., None] )
    bare = smoothstep( 1.4, 1.9, nz( 2.2, 120, 6 ) ) * ( 1 - bush )
    c = mix( c, earth, bare[..., None] * 0.8 )
    c *= ( 1.0 + 0.08 * nz( 1.2, 3, 0.5 ) )[..., None]
    r = 0.9 - 0.05 * bush
    h = 0.6 * bush + 0.1 * nz( 1.2, 3, 0.5 )
    return c, np.clip( r, 0.3, 1 ), h, ppi


def hill_far( seed=93, n=None ):
    """ The far hills seen from a kilometre and more: a mottle of holm oak and pine canopy, darker in its hollows, with
    clearings of dry grass and earth, as the picture's hills read through the haze (a flat paint made smooth
    silhouettes). Its mean is about the old flat paint's, so the fog leaves the hills where they were. """
    n = n or px( 2048 )
    tile = TILES["oa_hill_far"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    shade = lin( ( 38, 46, 36 ) )
    canopy = lin( ( 62, 72, 50 ) )
    grass = lin( ( 128, 114, 80 ) )
    earth = lin( ( 104, 88, 70 ) )
    clump = nz( 1.4, 60, 6 ) + 0.6 * nz( 2.4, 400, 30 )
    c = mix( shade[None, None, :] * np.ones( ( n, n, 1 ), np.float32 ), canopy, smoothstep( -0.6, 0.9, clump )[..., None] )
    clearing = smoothstep( 1.0, 1.5, nz( 2.2, 900, 40 ) + 0.4 * nz( 1.6, 120, 10 ) )
    c = mix( c, grass * ( 1.0 + 0.1 * nz( 1.0, 30, 3 ) )[..., None], clearing[..., None] * 0.85 )
    bare = smoothstep( 1.5, 1.9, nz( 2.0, 300, 20 ) ) * clearing
    c = mix( c, earth, bare[..., None] * 0.7 )
    c *= ( 1.0 + 0.1 * nz( 1.2, 12, 1 ) )[..., None]
    h = 0.5 * smoothstep( -0.6, 0.9, clump ) + 0.1 * nz( 1.2, 12, 1 )
    return c, np.full( ( n, n ), 0.92, np.float32 ), h, ppi


def hazard( seed=95 ):
    return RM.hazard( seed )


def grating( seed=96 ):
    return RM.grating( seed )


# ---------------------------------------------------------------------------------------------------------------------
# Lettering and the mark (an alpha atlas, white on transparent; two materials tint it dark or light)

LETTER_ATLAS = ( 4096, 4096 )
LETTERS = {
    "launch_control": ( 0, 0, 768, 768 ),           # LAUNCH / CONTROL, condensed, two lines left-aligned
    "n01": ( 768, 0, 608, 768 ),                   # 01, condensed
    "b3": ( 2560, 0, 512, 512 ),                    # B3, condensed
    "ops": ( 3328, 0, 768, 512 ),                   # OPS
    "orion": ( 2560, 512, 1536, 512 ),              # ORION
    "fuel_processing": ( 0, 768, 1536, 1024 ),      # FUEL / PROCESSING / long arrow
    "satellite_control": ( 1536, 768, 1024, 576 ), # SATELLITE / CONTROL
    "aerospace": ( 2560, 1024, 1536, 256 ),         # A E R O S P A C E
    "mark": ( 2560, 1280, 768, 768 ),               # the planet and its ring
    "orn": ( 3328, 1280, 384, 1280 ),               # O R N, stacked (the rocket's side)
    "arrow": ( 3712, 1280, 384, 384 ),              # a chevron
    "x": ( 3712, 1664, 384, 384 ),                  # a big X (crossed tape on crates)
    "mark_wordmark": ( 0, 1792, 2048, 1280 ),       # the mark over ORION over AEROSPACE (the block's face)
    "pad": ( 2048, 2048, 1280, 512 ),               # PAD 2
    "a": ( 2048, 2560, 512, 512 ), "b": ( 2560, 2560, 512, 512 ),
    "lc_small": ( 3072, 2560, 1024, 256 ),           # LAUNCH CONTROL (door lintels)
    "fuel_small": ( 3072, 2816, 1024, 256 ),         # FUEL PROCESSING (small)
    "deck": ( 0, 3072, 2048, 384 ),                 # LAUNCH DECK
    "service_tunnel": ( 0, 3456, 2048, 384 ),       # SERVICE TUNNEL
    "no_entry": ( 2048, 3072, 2048, 384 ),           # NO ENTRY BEYOND THIS POINT
    "one_team": ( 2048, 3456, 2048, 640 ),          # FURTHER / TOGETHER (a slogan)
}


def font( name, size ):
    return ImageFont.truetype( str( FONTS / f"{name}.ttf" ), max( 6, int( size ) ) )


def lines_block( draw, box, lines, face="Dinish-Bold", align="left", spacing=0.25, track=0.04, pad=0.06, stroke=0.0,
                 sizes=None, fill=255 ):
    """ Lines of capitals fitted into box ( x, y, w, h ): as large as fit, each line's relative size in sizes. """
    x, y, w, h = box
    iw, ih = w * ( 1 - 2 * pad ), h * ( 1 - 2 * pad )
    sizes = sizes or [ 1.0 ] * len( lines )
    total_rel = sum( sizes ) + spacing * ( len( lines ) - 1 )
    size = ih / total_rel / 0.72
    widths = []
    for _ in range( 60 ):
        widths = []
        for ln, rel in zip( lines, sizes ):
            f = font( face, size * rel )
            widths.append( sum( f.getlength( ch ) for ch in ln ) + track * size * rel * ( len( ln ) - 1 ) )
        if max( widths ) <= iw:
            break
        size *= 0.96
    caps = [ 0.72 * size * rel for rel in sizes ]
    total = sum( caps ) + spacing * 0.72 * size * ( len( lines ) - 1 )
    top = y + ( h - total ) / 2
    for ln, rel, lw, cap in zip( lines, sizes, widths, caps ):
        f = font( face, size * rel )
        if align == "left":
            cx = x + w * pad
        elif align == "right":
            cx = x + w * ( 1 - pad ) - lw
        else:
            cx = x + ( w - lw ) / 2
        asc = f.getbbox( "H" )[1]
        cy = top - asc
        for ch in ln:
            draw.text( ( cx, cy ), ch, font=f, fill=fill, stroke_width=int( stroke * size * rel ), stroke_fill=fill )
            cx += f.getlength( ch ) + track * size * rel
        top += cap + spacing * 0.72 * size
    return size


def condensed_block( img, box, lines, squeeze, stem=0.0, **kw ):
    """ lines_block drawn into box squeezed across by squeeze (a condensed face from Dinish, like the picture's narrow
    DIN stencils), its upright stems thickened again by stem (a share of the cap height). """
    x, y, w, h = ( int( round( q ) ) for q in box )
    W = max( 1, int( round( w / squeeze ) ) )
    tmp = Image.new( "L", ( W, h ), 0 )
    size = lines_block( ImageDraw.Draw( tmp ), ( 0, 0, W, h ), lines, **kw )
    a = np.asarray( tmp.resize( ( w, h ), Image.LANCZOS ), np.float32 )
    if stem > 0:
        a = ndimage.grey_dilation( a, size=( 1, max( 1, int( round( stem * 0.72 * size ) ) ) ) )
    region = np.asarray( img.crop( ( x, y, x + w, y + h ) ), np.float32 )
    img.paste( Image.fromarray( np.maximum( region, a ).astype( np.uint8 ) ), ( x, y ) )


def draw_mark( img, box, fill=255 ):
    """ Orion Aerospace's mark, drawn into img (L): a planet ring with a crescent shadowed inside it, and an orbit tilted
    across it whose far side passes behind the planet. """
    x, y, w, h = box
    S = 4
    big = Image.new( "L", ( int( w * S ), int( h * S ) ), 0 )
    d = ImageDraw.Draw( big )
    cx, cy = w * S / 2, h * S / 2
    R = min( w, h ) * S * 0.27
    t = R * 0.2
    planet = Image.new( "L", big.size, 0 )
    pd = ImageDraw.Draw( planet )
    pd.ellipse( ( cx - R, cy - R, cx + R, cy + R ), fill=255 )
    pd.ellipse( ( cx - R + t, cy - R + t, cx + R - t, cy + R - t ), fill=0 )
    # The crescent: the lower-left inside of the ring filled.
    cres = Image.new( "L", big.size, 0 )
    cd = ImageDraw.Draw( cres )
    cd.ellipse( ( cx - R + t, cy - R + t, cx + R - t, cy + R - t ), fill=255 )
    cd.ellipse( ( cx - R + t + R * 0.42, cy - R + t - R * 0.36, cx + R - t + R * 0.42, cy + R - t - R * 0.36 ), fill=0 )
    # The orbit: an ellipse tilted 22 degrees, as a thick line; its back half hidden inside the planet's disc.
    orbit = Image.new( "L", big.size, 0 )
    od = ImageDraw.Draw( orbit )
    a, b = R * 1.75, R * 0.52
    tilt = math.radians( -22 )
    pts = []
    for k in range( 361 ):
        th = math.radians( k )
        ex, ey = a * math.cos( th ), b * math.sin( th )
        pts.append( ( cx + ex * math.cos( tilt ) - ey * math.sin( tilt ), cy + ex * math.sin( tilt ) + ey * math.cos( tilt ), math.sin( th ) ) )
    lw = int( R * 0.15 )
    for p, q in zip( pts, pts[1:] ):
        od.line( ( p[0], p[1], q[0], q[1] ), fill=255, width=lw )
    behind = Image.new( "L", big.size, 0 )
    bd = ImageDraw.Draw( behind )
    for p, q in zip( pts, pts[1:] ):
        if p[2] < 0:
            bd.line( ( p[0], p[1], q[0], q[1] ), fill=255, width=lw + 2 )
    disc = Image.new( "L", big.size, 0 )
    ImageDraw.Draw( disc ).ellipse( ( cx - R - lw * 0.5, cy - R - lw * 0.5, cx + R + lw * 0.5, cy + R + lw * 0.5 ), fill=255 )
    o = np.asarray( orbit, np.float32 ) / 255
    hide = ( np.asarray( behind, np.float32 ) / 255 ) * ( np.asarray( disc, np.float32 ) / 255 )
    o = o * ( 1 - hide )
    # A gap in the planet's ring where the orbit's near side crosses in front of it.
    front = o * ( np.asarray( disc, np.float32 ) / 255 )
    gap = ndimage.grey_dilation( front, size=( int( lw * 1.6 ), int( lw * 1.6 ) ) )
    p_ = np.maximum( np.asarray( planet, np.float32 ) / 255, np.asarray( cres, np.float32 ) / 255 ) * ( 1 - gap ) + front
    total = np.clip( np.maximum( p_, o ), 0, 1 )
    small = Image.fromarray( ( total * 255 ).astype( np.uint8 ) ).resize( ( int( w ), int( h ) ), Image.LANCZOS )
    img.paste( Image.new( "L", small.size, fill ), ( int( x ), int( y ) ), small )


def letters_atlas():
    W, H = px( LETTER_ATLAS[0] ), px( LETTER_ATLAS[1] )
    k = W / LETTER_ATLAS[0]
    img = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( img )

    def box( name ):
        x, y, w, h = LETTERS[name]
        return ( x * k, y * k, w * k, h * k )

    condensed_block( img, box( "launch_control" ), [ "LAUNCH", "CONTROL" ], 0.36, stem=0.045, face="Dinish-Regular", spacing=0.16,
                     track=0.14, pad=0.03 )
    condensed_block( img, box( "n01" ), [ "01" ], 0.52, stem=0.05, face="Dinish-Bold", align="center", track=0.12, pad=0.03 )
    condensed_block( img, box( "b3" ), [ "B3" ], 0.56, stem=0.04, face="Dinish-Bold", align="left", track=0.06, pad=0.04 )
    x, y, w, h = box( "fuel_processing" )
    condensed_block( img, ( x, y, w, h * 0.62 ), [ "FUEL", "PROCESSING" ], 0.52, stem=0.03, face="Dinish-Bold", spacing=0.3,
                     track=0.06, pad=0.05 )
    # The arrow under it: a long shaft and a filled head, sloping a touch down to the right as the picture's does.
    ax0, ay0, ax1 = x + w * 0.05, y + h * 0.74, x + w * 0.8
    ay1 = ay0 + h * 0.08
    lw = max( 2, int( h * 0.05 ) )
    d.line( ( ax0, ay0, ax1 - h * 0.06, ay1 - h * 0.01 ), fill=255, width=lw )
    hl = h * 0.15
    ang = math.atan2( ay1 - ay0, ax1 - ax0 )
    tip = ( ax1, ay1 )
    left = ( ax1 - hl * math.cos( ang ) + hl * 0.45 * math.sin( ang ), ay1 - hl * math.sin( ang ) - hl * 0.45 * math.cos( ang ) )
    right = ( ax1 - hl * math.cos( ang ) - hl * 0.45 * math.sin( ang ), ay1 - hl * math.sin( ang ) + hl * 0.45 * math.cos( ang ) )
    d.polygon( [ tip, left, right ], fill=255 )
    lines_block( d, box( "ops" ), [ "OPS" ], face="Dinish-Bold", align="left", track=0.04, pad=0.06 )
    lines_block( d, box( "satellite_control" ), [ "SATELLITE", "CONTROL" ], face="Dinish-Regular", align="left", spacing=0.3, track=0.03,
                 pad=0.06, stroke=0.01 )
    lines_block( d, box( "orion" ), [ "ORION" ], face="Mina-Regular", align="center", track=0.06, pad=0.05, stroke=0.012 )
    lines_block( d, box( "aerospace" ), [ "AEROSPACE" ], face="Mina-Regular", align="center", track=0.55, pad=0.06 )
    draw_mark( img, box( "mark" ) )
    x, y, w, h = box( "mark_wordmark" )
    draw_mark( img, ( x + w * 0.5 - h * 0.28, y, h * 0.56, h * 0.56 ) )
    lines_block( d, ( x, y + h * 0.56, w, h * 0.3 ), [ "ORION" ], face="Mina-Regular", align="center", track=0.06, pad=0.04, stroke=0.012 )
    lines_block( d, ( x, y + h * 0.86, w, h * 0.12 ), [ "AEROSPACE" ], face="Mina-Regular", align="center", track=0.55, pad=0.08 )
    x, y, w, h = box( "orn" )
    for i, ch in enumerate( "ORN" ):
        lines_block( d, ( x, y + h * i / 3, w, h / 3 ), [ ch ], face="Dinish-Bold", align="center", pad=0.12 )
    lines_block( d, box( "pad" ), [ "PAD 2" ], face="Dinish-Bold", align="center", track=0.06 )
    lines_block( d, box( "a" ), [ "A" ], face="Dinish-Bold", align="center", pad=0.08 )
    lines_block( d, box( "b" ), [ "B" ], face="Dinish-Bold", align="center", pad=0.08 )
    lines_block( d, box( "deck" ), [ "LAUNCH DECK" ], face="Dinish-Bold", align="center", track=0.08 )
    lines_block( d, box( "service_tunnel" ), [ "SERVICE TUNNEL" ], face="Dinish-Bold", align="center", track=0.08 )
    lines_block( d, box( "no_entry" ), [ "NO ENTRY BEYOND THIS POINT" ], face="Dinish-Bold", align="center", track=0.05 )
    lines_block( d, box( "one_team" ), [ "FURTHER", "TOGETHER" ], face="Dinish-Regular", align="left", spacing=0.3, track=0.12, stroke=0.01 )
    x, y, w, h = box( "arrow" )
    d.polygon( [ ( x + w * 0.2, y + h * 0.15 ), ( x + w * 0.5, y + h * 0.15 ), ( x + w * 0.85, y + h * 0.5 ), ( x + w * 0.5, y + h * 0.85 ),
                 ( x + w * 0.2, y + h * 0.85 ), ( x + w * 0.55, y + h * 0.5 ) ], fill=255 )
    lines_block( d, box( "lc_small" ), [ "LAUNCH CONTROL" ], face="Dinish-Bold", align="center", track=0.1 )
    lines_block( d, box( "fuel_small" ), [ "FUEL PROCESSING" ], face="Dinish-Bold", align="center", track=0.1 )
    x, y, w, h = box( "x" )
    lw = int( w * 0.12 )
    d.line( ( x + w * 0.1, y + h * 0.1, x + w * 0.9, y + h * 0.9 ), fill=255, width=lw )
    d.line( ( x + w * 0.9, y + h * 0.1, x + w * 0.1, y + h * 0.9 ), fill=255, width=lw )
    a = np.asarray( img, np.float32 ) / 255.0
    # Paint wear: worn through in specks and patches, as on the picture's stencils.
    rng = np.random.default_rng( 5 )
    wear = BM.noise( rng, a.shape, ( k * 8, k * 8 ), 1.6, 40, 0.5 )
    speck = BM.noise( rng, a.shape, ( k * 8, k * 8 ), 0.8, 2, 0.2 )
    a *= 1.0 - smoothstep( 1.7, 2.5, wear ) * 0.9
    a *= 1.0 - smoothstep( 2.0, 2.6, speck ) * 0.8
    return a


# ---------------------------------------------------------------------------------------------------------------------
# Plates: opaque signs and pictures

PLATE_ATLAS = ( 2048, 2048 )
PLATES = {
    "fire": ( 0, 0, 256, 256 ),                   # FIRE POINT: an extinguisher on red
    "warning": ( 256, 0, 384, 336 ),              # a yellow triangle over DANGER / HIGH PRESSURE
    "keep_clear": ( 640, 0, 512, 160 ),           # KEEP CLEAR, yellow and black
    "no_smoking": ( 1152, 0, 256, 256 ),
    "authorised": ( 1408, 0, 640, 192 ),          # AUTHORISED PERSONNEL ONLY
    "poster_launch": ( 0, 336, 384, 544 ),        # a launch poster: the rocket going up over the hills
    "poster_safety": ( 384, 336, 384, 544 ),      # SAFETY FIRST, a list
    "poster_mission": ( 768, 160, 384, 544 ),     # MISSION 07 and the orbit
    "whiteboard": ( 1152, 256, 896, 512 ),        # a whiteboard with a launch timeline drawn on it
    "board": ( 0, 880, 768, 448 ),                # a cork board with sheets pinned on it
    "flag": ( 768, 768, 1280, 768 ),              # Orion's flag: black with the mark in white
    "banner": ( 0, 1328, 384, 720 ),              # a dark banner with the mark
    "red_door": ( 384, 1328, 256, 512 ),          # a red steel door with its push plate
    "door_sign": ( 640, 1536, 256, 128 ),          # a door placard
    "hazmat": ( 896, 1536, 256, 256 ),             # a hazardous materials diamond
    "exit": ( 1152, 1536, 384, 128 ),              # EXIT, green
    "chart": ( 1536, 1536, 512, 512 ),             # a launch window chart
}


def plates_atlas():
    W, H = px( PLATE_ATLAS[0] ), px( PLATE_ATLAS[1] )
    k = W / PLATE_ATLAS[0]
    img = Image.new( "RGB", ( W, H ), ( 40, 40, 40 ) )
    rough = Image.new( "L", ( W, H ), 140 )
    d = ImageDraw.Draw( img )
    dr = ImageDraw.Draw( rough )

    def box( name ):
        x, y, w, h = PLATES[name]
        return ( x * k, y * k, w * k, h * k )

    def fill( name, colour, r=0.5 ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=colour )
        dr.rectangle( ( x, y, x + w, y + h ), fill=int( r * 255 ) )
        return x, y, w, h

    def text( bx, lines, colour, face="Dinish-Bold", align="center", **kw ):
        layer = Image.new( "L", ( W, H ), 0 )
        lines_block( ImageDraw.Draw( layer ), bx, lines, face=face, align=align, **kw )
        img.paste( Image.new( "RGB", ( W, H ), colour ), ( 0, 0 ), layer )

    x, y, w, h = fill( "fire", ( 196, 30, 28 ), 0.45 )
    # An extinguisher: body, nozzle and hose; FIRE POINT under it.
    d.rounded_rectangle( ( x + w * 0.38, y + h * 0.22, x + w * 0.62, y + h * 0.7 ), radius=w * 0.06, fill=( 240, 240, 236 ) )
    d.rectangle( ( x + w * 0.45, y + h * 0.14, x + w * 0.55, y + h * 0.22 ), fill=( 240, 240, 236 ) )
    d.line( ( x + w * 0.55, y + h * 0.17, x + w * 0.74, y + h * 0.3 ), fill=( 240, 240, 236 ), width=int( w * 0.04 ) )
    text( ( x, y + h * 0.74, w, h * 0.22 ), [ "FIRE POINT" ], ( 240, 240, 236 ), track=0.06 )
    x, y, w, h = fill( "warning", ( 236, 186, 30 ), 0.5 )
    d.polygon( [ ( x + w * 0.5, y + h * 0.06 ), ( x + w * 0.82, y + h * 0.6 ), ( x + w * 0.18, y + h * 0.6 ) ], fill=( 20, 20, 20 ) )
    d.polygon( [ ( x + w * 0.5, y + h * 0.16 ), ( x + w * 0.74, y + h * 0.56 ), ( x + w * 0.26, y + h * 0.56 ) ], fill=( 236, 186, 30 ) )
    d.rectangle( ( x + w * 0.485, y + h * 0.27, x + w * 0.515, y + h * 0.45 ), fill=( 20, 20, 20 ) )
    d.ellipse( ( x + w * 0.483, y + h * 0.48, x + w * 0.517, y + h * 0.52 ), fill=( 20, 20, 20 ) )
    text( ( x, y + h * 0.63, w, h * 0.34 ), [ "DANGER", "HIGH PRESSURE" ], ( 20, 20, 20 ), spacing=0.25 )
    x, y, w, h = fill( "keep_clear", ( 236, 186, 30 ), 0.5 )
    for i in range( 0, int( w ), int( h * 0.5 ) ):
        d.polygon( [ ( x + i, y ), ( x + i + h * 0.25, y ), ( x + i + h * 0.25 - h * 0.3, y + h * 0.28 ), ( x + i - h * 0.3, y + h * 0.28 ) ], fill=( 20, 20, 20 ) )
    text( ( x, y + h * 0.3, w, h * 0.7 ), [ "KEEP CLEAR" ], ( 20, 20, 20 ), track=0.1 )
    x, y, w, h = fill( "no_smoking", ( 236, 236, 232 ), 0.5 )
    d.ellipse( ( x + w * 0.1, y + h * 0.1, x + w * 0.9, y + h * 0.9 ), outline=( 200, 30, 30 ), width=int( w * 0.08 ) )
    d.rectangle( ( x + w * 0.28, y + h * 0.46, x + w * 0.66, y + h * 0.54 ), fill=( 30, 30, 30 ) )
    d.line( ( x + w * 0.22, y + h * 0.22, x + w * 0.78, y + h * 0.78 ), fill=( 200, 30, 30 ), width=int( w * 0.08 ) )
    x, y, w, h = fill( "authorised", ( 26, 70, 140 ), 0.5 )
    text( ( x, y, w, h ), [ "AUTHORISED", "PERSONNEL ONLY" ], ( 236, 236, 232 ), spacing=0.25 )
    # Posters.
    x, y, w, h = fill( "poster_launch", ( 22, 30, 48 ), 0.4 )
    for i in range( int( h * 0.6 ) ):
        c = int( 30 + 120 * i / ( h * 0.6 ) )
        d.line( ( x, y + i, x + w, y + i ), fill=( c, int( c * 0.7 ), int( c * 0.45 ) ) )
    d.polygon( [ ( x, y + h * 0.62 ), ( x + w * 0.3, y + h * 0.5 ), ( x + w * 0.6, y + h * 0.58 ), ( x + w, y + h * 0.48 ), ( x + w, y + h * 0.7 ), ( x, y + h * 0.7 ) ],
               fill=( 30, 36, 40 ) )
    d.rectangle( ( x + w * 0.47, y + h * 0.2, x + w * 0.53, y + h * 0.45 ), fill=( 236, 236, 232 ) )
    d.polygon( [ ( x + w * 0.47, y + h * 0.2 ), ( x + w * 0.5, y + h * 0.13 ), ( x + w * 0.53, y + h * 0.2 ) ], fill=( 236, 236, 232 ) )
    d.polygon( [ ( x + w * 0.46, y + h * 0.45 ), ( x + w * 0.54, y + h * 0.45 ), ( x + w * 0.52, y + h * 0.58 ), ( x + w * 0.48, y + h * 0.58 ) ], fill=( 255, 190, 90 ) )
    text( ( x, y + h * 0.72, w, h * 0.12 ), [ "ORION AEROSPACE" ], ( 236, 236, 232 ), track=0.08 )
    text( ( x, y + h * 0.84, w, h * 0.12 ), [ "FURTHER TOGETHER" ], ( 236, 160, 60 ), face="Dinish-Regular", track=0.12 )
    x, y, w, h = fill( "poster_safety", ( 232, 230, 220 ), 0.5 )
    d.rectangle( ( x, y, x + w, y + h * 0.2 ), fill=( 30, 110, 60 ) )
    text( ( x, y, w, h * 0.2 ), [ "SAFETY FIRST" ], ( 240, 240, 236 ), track=0.06 )
    for i in range( 7 ):
        yy = y + h * ( 0.28 + i * 0.1 )
        d.rectangle( ( x + w * 0.1, yy, x + w * 0.16, yy + h * 0.04 ), fill=( 30, 110, 60 ) )
        d.rectangle( ( x + w * 0.22, yy + h * 0.01, x + w * ( 0.5 + 0.4 * ( ( i * 37 ) % 10 ) / 10 ), yy + h * 0.03 ), fill=( 60, 60, 60 ) )
    x, y, w, h = fill( "poster_mission", ( 16, 18, 26 ), 0.4 )
    d.ellipse( ( x + w * 0.25, y + h * 0.18, x + w * 0.75, y + h * 0.53 ), fill=( 40, 70, 120 ) )
    d.arc( ( x + w * 0.05, y + h * 0.22, x + w * 0.95, y + h * 0.48 ), 190, 350, fill=( 236, 160, 60 ), width=int( w * 0.02 ) )
    text( ( x, y + h * 0.62, w, h * 0.16 ), [ "MISSION 07" ], ( 236, 236, 232 ), track=0.08 )
    text( ( x, y + h * 0.8, w, h * 0.1 ), [ "LOW EARTH ORBIT" ], ( 180, 180, 180 ), face="Dinish-Regular", track=0.1 )
    x, y, w, h = fill( "whiteboard", ( 226, 228, 226 ), 0.15 )
    d.rectangle( ( x, y, x + w, y + h ), outline=( 150, 154, 158 ), width=int( w * 0.012 ) )
    d.line( ( x + w * 0.06, y + h * 0.7, x + w * 0.94, y + h * 0.7 ), fill=( 40, 60, 140 ), width=3 )
    for i in range( 9 ):
        xx = x + w * ( 0.08 + i * 0.105 )
        d.line( ( xx, y + h * 0.66, xx, y + h * 0.74 ), fill=( 40, 60, 140 ), width=3 )
        d.line( ( xx, y + h * 0.36, xx + w * 0.07, y + h * ( 0.3 + 0.06 * ( i % 3 ) ) ), fill=( 160, 40, 40 ) if i % 4 == 0 else ( 30, 30, 30 ), width=2 )
    d.line( ( x + w * 0.1, y + h * 0.18, x + w * 0.5, y + h * 0.18 ), fill=( 30, 30, 30 ), width=4 )
    d.line( ( x + w * 0.1, y + h * 0.26, x + w * 0.4, y + h * 0.26 ), fill=( 30, 30, 30 ), width=3 )
    d.ellipse( ( x + w * 0.66, y + h * 0.1, x + w * 0.86, y + h * 0.5 ), outline=( 40, 60, 140 ), width=3 )
    x, y, w, h = fill( "board", ( 150, 112, 70 ), 0.8 )
    rng = np.random.default_rng( 4 )
    for i in range( 14 ):
        sx, sy = x + w * rng.uniform( 0.04, 0.8 ), y + h * rng.uniform( 0.04, 0.7 )
        sw, sh = w * rng.uniform( 0.1, 0.18 ), h * rng.uniform( 0.18, 0.28 )
        tone = int( rng.uniform( 200, 240 ) )
        d.rectangle( ( sx, sy, sx + sw, sy + sh ), fill=( tone, tone, int( tone * 0.95 ) ) )
        for j in range( 5 ):
            d.line( ( sx + sw * 0.1, sy + sh * ( 0.2 + j * 0.14 ), sx + sw * 0.85, sy + sh * ( 0.2 + j * 0.14 ) ), fill=( 90, 90, 90 ), width=1 )
    x, y, w, h = fill( "flag", ( 14, 14, 16 ), 0.75 )
    layer = Image.new( "L", ( W, H ), 0 )
    draw_mark( layer, ( x + w * 0.5 - h * 0.42, y + h * 0.08, h * 0.84, h * 0.84 ) )
    img.paste( Image.new( "RGB", ( W, H ), ( 226, 226, 222 ) ), ( 0, 0 ), layer )
    x, y, w, h = fill( "banner", ( 30, 32, 34 ), 0.8 )
    layer = Image.new( "L", ( W, H ), 0 )
    draw_mark( layer, ( x + w * 0.15, y + h * 0.18, w * 0.7, w * 0.7 ) )
    img.paste( Image.new( "RGB", ( W, H ), ( 200, 200, 196 ) ), ( 0, 0 ), layer )
    x, y, w, h = fill( "red_door", ( 150, 30, 26 ), 0.4 )
    d.rectangle( ( x + w * 0.06, y + h * 0.04, x + w * 0.94, y + h * 0.98 ), outline=( 110, 20, 18 ), width=int( w * 0.03 ) )
    d.rectangle( ( x + w * 0.7, y + h * 0.48, x + w * 0.86, y + h * 0.54 ), fill=( 170, 170, 170 ) )
    d.rectangle( ( x + w * 0.25, y + h * 0.12, x + w * 0.75, y + h * 0.3 ), fill=( 40, 30, 30 ) )
    x, y, w, h = fill( "door_sign", ( 230, 230, 226 ), 0.4 )
    text( ( x, y, w, h ), [ "PLANT ROOM" ], ( 30, 30, 30 ), track=0.08 )
    x, y, w, h = fill( "hazmat", ( 236, 236, 232 ), 0.5 )
    d.polygon( [ ( x + w * 0.5, y + h * 0.04 ), ( x + w * 0.96, y + h * 0.5 ), ( x + w * 0.5, y + h * 0.96 ), ( x + w * 0.04, y + h * 0.5 ) ], fill=( 200, 40, 30 ) )
    d.polygon( [ ( x + w * 0.5, y + h * 0.12 ), ( x + w * 0.88, y + h * 0.5 ), ( x + w * 0.5, y + h * 0.88 ), ( x + w * 0.12, y + h * 0.5 ) ], outline=( 236, 236, 232 ),
               width=int( w * 0.02 ) )
    text( ( x + w * 0.3, y + h * 0.36, w * 0.4, h * 0.28 ), [ "2" ], ( 236, 236, 232 ) )
    x, y, w, h = fill( "exit", ( 30, 140, 70 ), 0.3 )
    text( ( x, y, w, h ), [ "EXIT" ], ( 240, 240, 236 ), track=0.12 )
    x, y, w, h = fill( "chart", ( 236, 236, 232 ), 0.3 )
    for i in range( 8 ):
        d.line( ( x + w * 0.08, y + h * ( 0.15 + i * 0.1 ), x + w * 0.92, y + h * ( 0.15 + i * 0.1 ) ), fill=( 200, 200, 200 ), width=1 )
    pts = [ ( x + w * ( 0.08 + 0.84 * t ), y + h * ( 0.7 - 0.45 * math.sin( t * 3.2 ) * math.exp( -t ) - 0.1 * t ) ) for t in np.linspace( 0, 1, 40 ) ]
    d.line( pts, fill=( 200, 60, 40 ), width=3 )
    c = T.srgb_to_linear( np.asarray( img, np.float32 ) )
    c *= ( 1.0 + 0.03 * BM.noise( np.random.default_rng( 3 ), c.shape[:2], ( k * 4, k * 4 ), 2.2, 20, 1 ) )[..., None]
    return np.clip( T.linear_to_srgb( c ), 0, 255 ), np.asarray( rough, np.float32 ) / 255.0


# ---------------------------------------------------------------------------------------------------------------------
# Screens: the control rooms' monitors (self-lit)

SCREEN_ATLAS = ( 2048, 1024 )
SCREENS = {
    "cctv": ( 0, 0, 1024, 576 ),         # a 3 x 3 grid of camera feeds: the yard, the pad, corridors
    "telemetry": ( 1024, 0, 1024, 576 ), # graphs and numbers
    "orbit": ( 0, 576, 768, 448 ),       # a world map with the ground track
    "status": ( 768, 576, 640, 448 ),    # a list of systems, green and amber
    "camera": ( 1408, 576, 640, 448 ),   # one camera's view of the rocket on its pad
}


def screens_atlas():
    W, H = px( SCREEN_ATLAS[0] ), px( SCREEN_ATLAS[1] )
    k = W / SCREEN_ATLAS[0]
    img = Image.new( "RGB", ( W, H ), ( 6, 8, 10 ) )
    d = ImageDraw.Draw( img )
    rng = np.random.default_rng( 8 )

    def box( name ):
        x, y, w, h = SCREENS[name]
        return ( x * k, y * k, w * k, h * k )

    def feed( x, y, w, h, kind ):
        """ A grey camera picture: a horizon, blocks, a rocket or a corridor's perspective. """
        top = rng.uniform( 70, 110 )
        for i in range( int( h ) ):
            t = i / h
            c = int( top * ( 1 - t ) + 40 * t )
            d.line( ( x, y + i, x + w, y + i ), fill=( c, c, int( c * 1.05 ) ) )
        if kind == 0:
            for _ in range( 6 ):
                bx, bw, bh = x + rng.uniform( 0, w * 0.9 ), w * rng.uniform( 0.08, 0.25 ), h * rng.uniform( 0.15, 0.5 )
                d.rectangle( ( bx, y + h * 0.75 - bh, bx + bw, y + h * 0.75 ), fill=( 60, 62, 64 ) )
            d.rectangle( ( x, y + h * 0.75, x + w, y + h ), fill=( 48, 50, 52 ) )
        elif kind == 1:
            d.rectangle( ( x + w * 0.47, y + h * 0.12, x + w * 0.53, y + h * 0.78 ), fill=( 200, 200, 196 ) )
            d.rectangle( ( x + w * 0.36, y + h * 0.1, x + w * 0.44, y + h * 0.8 ), fill=( 90, 80, 60 ) )
            d.rectangle( ( x, y + h * 0.78, x + w, y + h ), fill=( 52, 52, 54 ) )
        else:
            d.polygon( [ ( x, y ), ( x + w * 0.35, y + h * 0.4 ), ( x + w * 0.35, y + h * 0.6 ), ( x, y + h ) ], fill=( 52, 54, 56 ) )
            d.polygon( [ ( x + w, y ), ( x + w * 0.65, y + h * 0.4 ), ( x + w * 0.65, y + h * 0.6 ), ( x + w, y + h ) ], fill=( 58, 60, 62 ) )
            d.rectangle( ( x + w * 0.35, y + h * 0.4, x + w * 0.65, y + h * 0.6 ), fill=( 120, 120, 118 ) )
        d.text( ( x + 4, y + 2 ), f"CAM {rng.integers( 1, 40 ):02d}", fill=( 220, 220, 220 ) )

    x, y, w, h = box( "cctv" )
    for r in range( 3 ):
        for c in range( 3 ):
            feed( x + c * w / 3 + 2, y + r * h / 3 + 2, w / 3 - 4, h / 3 - 4, ( r * 3 + c ) % 3 )
    x, y, w, h = box( "telemetry" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 8, 14, 22 ) )
    for g in range( 4 ):
        gx, gy = x + ( g % 2 ) * w / 2 + 10, y + ( g // 2 ) * h / 2 + 10
        gw, gh = w / 2 - 20, h / 2 - 20
        d.rectangle( ( gx, gy, gx + gw, gy + gh ), outline=( 40, 70, 90 ) )
        pts = []
        val = 0.5
        for t in range( 60 ):
            val = np.clip( val + rng.normal( 0, 0.06 ), 0.1, 0.9 )
            pts.append( ( gx + gw * t / 59, gy + gh * ( 1 - val ) ) )
        d.line( pts, fill=( 80, 220, 255 ) if g % 2 == 0 else ( 255, 180, 60 ), width=2 )
    x, y, w, h = box( "orbit" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 8, 18, 30 ) )
    for _ in range( 22 ):
        cx, cy = x + rng.uniform( 0.05, 0.95 ) * w, y + rng.uniform( 0.2, 0.8 ) * h
        r = rng.uniform( 10, 50 ) * k
        d.ellipse( ( cx - r * 1.5, cy - r, cx + r * 1.5, cy + r ), fill=( 30, 60, 50 ) )
    pts = [ ( x + w * t, y + h * ( 0.5 - 0.3 * math.sin( t * 2 * math.pi * 1.5 ) ) ) for t in np.linspace( 0, 1, 80 ) ]
    d.line( pts, fill=( 255, 200, 70 ), width=3 )
    x, y, w, h = box( "status" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 10, 12, 16 ) )
    for i in range( 12 ):
        yy = y + h * ( 0.06 + i * 0.078 )
        ok = rng.random() > 0.2
        d.rectangle( ( x + w * 0.05, yy, x + w * 0.09, yy + h * 0.05 ), fill=( 60, 210, 90 ) if ok else ( 240, 170, 40 ) )
        d.rectangle( ( x + w * 0.13, yy + h * 0.012, x + w * rng.uniform( 0.4, 0.9 ), yy + h * 0.035 ), fill=( 170, 176, 180 ) )
    x, y, w, h = box( "camera" )
    feed( x, y, w, h, 1 )
    a = np.asarray( img, np.float32 )
    # Scan lines and a little bloom of the lit pixels.
    a *= ( 0.92 + 0.08 * ( ( np.arange( a.shape[0] ) % 3 ) > 0 ) )[:, None, None]
    return np.clip( a, 0, 255 )


# ---------------------------------------------------------------------------------------------------------------------
# Flat paints: ( sRGB colour, metalness, roughness, self-illumination )

PAINTED = {
    "oa_black": ( ( 20, 20, 22 ), 0.0, 0.6, 0 ),
    "oa_rubber": ( ( 16, 16, 16 ), 0.0, 0.85, 0 ),
    "oa_dark": ( ( 34, 36, 38 ), 0.2, 0.55, 0 ),
    "oa_frame": ( ( 66, 70, 74 ), 0.6, 0.42, 0 ),
    "oa_door": ( ( 92, 98, 104 ), 0.3, 0.45, 0 ),
    "oa_door_red": ( ( 140, 28, 24 ), 0.2, 0.45, 0 ),
    "oa_red_glow": ( ( 200, 40, 30 ), 0.0, 0.5, 2.5 ),
    "oa_lamp_warm": ( ( 255, 210, 150 ), 0.0, 0.3, 8 ),
    "oa_lamp_cool": ( ( 222, 236, 255 ), 0.0, 0.3, 4 ),
    "oa_lamp_flood": ( ( 255, 236, 200 ), 0.0, 0.2, 9 ),
    "oa_beacon": ( ( 255, 40, 30 ), 0.0, 0.3, 16 ),
    "oa_window_lit": ( ( 255, 214, 160 ), 0.0, 0.2, 2.0 ),
    "oa_window_cool": ( ( 200, 220, 240 ), 0.0, 0.2, 2.5 ),
    "oa_window_dark": ( ( 26, 32, 40 ), 0.6, 0.1, 0 ),
    "oa_interior": ( ( 128, 108, 82 ), 0.0, 0.7, 0 ),
    "oa_interior_dark": ( ( 70, 70, 68 ), 0.0, 0.7, 0 ),
    "oa_desk": ( ( 84, 88, 94 ), 0.1, 0.4, 0 ),
    "oa_chair": ( ( 40, 42, 48 ), 0.0, 0.6, 0 ),
    "oa_gold": ( ( 200, 150, 60 ), 0.9, 0.3, 0 ),
    "oa_rocket_dark": ( ( 40, 40, 44 ), 0.3, 0.45, 0 ),
    "oa_nozzle": ( ( 70, 66, 62 ), 0.8, 0.4, 0 ),
    "oa_zinc": ( ( 150, 156, 160 ), 0.6, 0.45, 0 ),
    "oa_line_yellow": ( ( 186, 146, 72 ), 0.0, 0.3, 0 ),
    "oa_line_white": ( ( 200, 200, 196 ), 0.0, 0.35, 0 ),
    "oa_flag_pole": ( ( 160, 164, 168 ), 0.8, 0.3, 0 ),
    "oa_pine": ( ( 52, 66, 50 ), 0.0, 0.9, 0 ),
    "oa_tree": ( ( 72, 84, 52 ), 0.0, 0.9, 0 ),
    "oa_tree_far": ( ( 70, 82, 70 ), 0.0, 0.9, 0 ),
    "oa_scrub": ( ( 92, 96, 60 ), 0.0, 0.9, 0 ),
    "oa_grass_far": ( ( 150, 136, 96 ), 0.0, 0.95, 0 ),
    "oa_rock": ( ( 128, 118, 104 ), 0.0, 0.9, 0 ),
    "oa_rock_far": ( ( 120, 124, 136 ), 0.0, 0.92, 0 ),
    "oa_mountain": ( ( 56, 62, 62 ), 0.0, 0.95, 0 ),
    "oa_earth": ( ( 120, 98, 76 ), 0.0, 0.92, 0 ),
    "oa_render": ( ( 214, 204, 184 ), 0.0, 0.8, 0 ),
    "oa_render_ochre": ( ( 206, 168, 112 ), 0.0, 0.8, 0 ),
    "oa_render_grey": ( ( 168, 166, 160 ), 0.0, 0.8, 0 ),
    "oa_render_pink": ( ( 210, 170, 150 ), 0.0, 0.8, 0 ),
    "oa_roof_tile": ( ( 150, 84, 56 ), 0.0, 0.75, 0 ),
    "oa_roof_dark": ( ( 70, 66, 64 ), 0.0, 0.7, 0 ),
    "oa_stone": ( ( 170, 160, 142 ), 0.0, 0.85, 0 ),
    "oa_asphalt": ( ( 44, 44, 46 ), 0.0, 0.7, 0 ),
    "oa_steam": ( ( 230, 230, 230 ), 0.0, 0.9, 0 ),
    "oa_glass_frame": ( ( 50, 54, 58 ), 0.7, 0.35, 0 ),
    "oa_interior_floor": ( ( 96, 98, 100 ), 0.0, 0.35, 0 ),
    "oa_red_wall": ( ( 110, 26, 22 ), 0.0, 0.6, 0.18 ),
    "oa_cable": ( ( 24, 24, 26 ), 0.0, 0.6, 0 ),
    "oa_brass": ( ( 170, 130, 60 ), 0.85, 0.35, 0 ),
    "oa_pallet": ( ( 150, 128, 98 ), 0.0, 0.82, 0 ),
}


def save_grey( path, a, size=None ):
    RM.save_grey( path, a, size )


def save_rgb( path, a, quality=92 ):
    RM.save_rgb( path, a, quality )


def vmat( colour, normal, rough, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0, illum_tint=( 1, 1, 1 ),
          tint=( 1.0, 1.0, 1.0 ) ):
    return RM.vmat( colour, normal, rough, metalness, alpha, illum, illum_brightness, illum_tint, tint ).replace(
        "// Tools/riverdale_materials.py", "// Tools/orion_textures.py" )


def painted_vmat( colour, metalness, roughness, glow ):
    return RM.painted_vmat( colour, metalness, roughness, glow ).replace( "// Tools/riverdale_materials.py", "// Tools/orion_textures.py" )


def write_text( path, text ):
    RM.write_text( path, text )


def write_surface( out, name, colour, rough, height, ppi, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0,
                   illum_tint=( 1, 1, 1 ) ):
    srgb = T.linear_to_srgb( colour )
    save_rgb( out / f"{name}_color.jpg", srgb )
    save_rgb( out / f"{name}_normal.jpg", ( BM.normals( height, ( ppi, ppi ) ) * 0.5 + 0.5 ) * 255, quality=94 )
    save_grey( out / f"{name}_rough.png", rough )
    alpha_path = illum_path = None
    if alpha is not None:
        save_grey( out / f"{name}_trans.png", alpha )
        alpha_path = f"{RESOURCE_DIR}/{name}_trans.png"
    if illum is not None:
        save_grey( out / f"{name}_illum.png", illum )
        illum_path = f"{RESOURCE_DIR}/{name}_illum.png"
    write_text( out / f"{name}.vmat", vmat( f"{RESOURCE_DIR}/{name}_color.jpg", f"{RESOURCE_DIR}/{name}_normal.jpg",
                                            f"{RESOURCE_DIR}/{name}_rough.png", metalness, alpha_path, illum_path,
                                            illum_brightness, illum_tint ) )
    print( f"wrote {name}" )
    return srgb


SURFACES = {
    "oa_wall": lambda: concrete(),
    "oa_wall_dark": lambda: concrete( seed=12, base=( 104, 104, 100 ), grime=1.0 ),
    "oa_yard": lambda: slabs( 31, "oa_yard", slab=96.0, wet=1.0, puddles=1.1, rough_add=0.12, base=( 112, 108, 102 ), film=0.55 ),
    "oa_deck": lambda: slabs( 32, "oa_deck", slab=128.0, wet=0.6, puddles=0.25, base=( 128, 126, 122 ), film=0.3 ),
    "oa_yellow": lambda: painted( 41, ( 196, 150, 66 ), TILES["oa_yellow"], chips=0.55, rough=0.38, grime=0.5 ),
    "oa_steel": lambda: painted( 42, ( 72, 76, 80 ), TILES["oa_steel"], chips=0.3, rough=0.5 ),
    "oa_orange": lambda: painted( 43, ( 186, 96, 40 ), TILES["oa_orange"], chips=0.6, rough=0.55, grime=0.5, rust=0.45, bare=( 70, 50, 40 ) ),
    "oa_gantry": lambda: painted( 47, ( 74, 62, 52 ), TILES["oa_gantry"], chips=0.5, rough=0.45, grime=0.5, rust=0.4, bare=( 48, 40, 34 ) ),
    "oa_red": lambda: painted( 44, ( 150, 38, 30 ), TILES["oa_red"], chips=0.45, rough=0.5, grime=0.5, rust=0.2 ),
    "oa_white_steel": lambda: painted( 45, ( 214, 214, 208 ), TILES["oa_white_steel"], chips=0.2, rough=0.5, grime=0.55 ),
    "oa_olive": lambda: painted( 46, ( 80, 88, 66 ), TILES["oa_olive"], chips=0.25, rough=0.5, bare=( 60, 62, 54 ), grime=0.45 ),
    "oa_case": lambda: painted( 47, ( 56, 60, 60 ), TILES["oa_case"], chips=0.25, rough=0.5, bare=( 80, 82, 84 ), grime=0.4 ),
    "oa_pipe": lambda: pipe_jacket(),
    "oa_tarp": lambda: tarp(),
    "oa_tarp_grey": lambda: tarp( seed=62, base=( 132, 117, 101 ) ),
    "oa_rocket": lambda: rocket_skin(),
    "oa_radome": lambda: radome(),
    "oa_hill": lambda: hill(),
    "oa_hill_far": lambda: hill_far(),
}
METALNESS = { "oa_pipe": 0.9 }
# A little self-light where a paint stands in for light the scene can't afford: the service towers' steel, lit gold
# all over by the hundreds of work lamps the picture's towers carry (the towers cast a few dozen). ( brightness, tint )
GLOW = { "oa_gantry": ( 0.04, ( 1.0, 0.82, 0.6 ) ) }
NAMES = list( SURFACES ) + [ "oa_hazard", "oa_grating", "letters", "oa_plates", "oa_screens", "painted" ]


def all_paints():
    return list( SURFACES ) + [ "oa_hazard", "oa_grating", "oa_letters_dark", "oa_letters_light", "oa_plates", "oa_screens" ] + list( PAINTED )


def build( name, out ):
    done = {}
    if name in SURFACES:
        c, r, h, ppi = SURFACES[name]()
        glow, tint = GLOW.get( name, ( 0.0, ( 1, 1, 1 ) ) )
        done[name] = write_surface( out, name, c, r, h, ppi, METALNESS.get( name, 0.0 ),
                                    illum=np.ones( c.shape[:2], np.float32 ) if glow else None, illum_brightness=glow, illum_tint=tint )
    elif name == "oa_hazard":
        c, r, h, ppi = hazard()
        done[name] = write_surface( out, name, c, r, h, ppi )
    elif name == "oa_grating":
        c, r, h, ppi, steel = grating()
        done[name] = write_surface( out, name, c, r, h, ppi, 0.5, alpha=steel )
    elif name == "letters":
        a = letters_atlas()
        save_grey( out / "oa_letters_trans.png", a )
        for tone, tint, rough in ( ( "dark", ( 0.026, 0.027, 0.029 ), 0.7 ), ( "light", ( 0.84, 0.85, 0.84 ), 0.6 ) ):
            text = vmat( "[1.000000 1.000000 1.000000 0.000000]", "materials/default/default_normal.tga",
                         f"[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]", 0.0, f"{RESOURCE_DIR}/oa_letters_trans.png", tint=tint )
            write_text( out / f"oa_letters_{tone}.vmat", text )
        done["oa_letters"] = np.repeat( a[..., None] * 255, 3, -1 )
        print( "wrote oa_letters" )
    elif name == "oa_plates":
        c, r = plates_atlas()
        save_rgb( out / "oa_plates_color.png", c )
        save_grey( out / "oa_plates_rough.png", r )
        write_text( out / "oa_plates.vmat", vmat( f"{RESOURCE_DIR}/oa_plates_color.png", "materials/default/default_normal.tga",
                                                   f"{RESOURCE_DIR}/oa_plates_rough.png" ) )
        done[name] = c
        print( "wrote oa_plates" )
    elif name == "oa_screens":
        c = screens_atlas()
        save_rgb( out / "oa_screens_color.png", c )
        write_text( out / "oa_screens.vmat", vmat( f"{RESOURCE_DIR}/oa_screens_color.png", "materials/default/default_normal.tga",
                                                    "[0.200000 0.200000 0.200000 0.000000]", illum="[1.000000 1.000000 1.000000 0.000000]",
                                                    illum_brightness=1.4 ) )
        done[name] = c
        print( "wrote oa_screens" )
    elif name == "painted":
        for p, ( rgb, metal, rough, glow ) in PAINTED.items():
            write_text( out / f"{p}.vmat", painted_vmat( rgb, metal, rough, glow ) )
        print( f"wrote {len( PAINTED )} flat paints" )
    else:
        raise SystemExit( f"unknown texture {name}" )
    return done


def atlas_uv( table, size, name, s, t ):
    """ ( u, v ) in an atlas for ( s, t ) 0..1 across a region (s right, t up). """
    x, y, w, h = table[name]
    return ( x + s * w ) / size[0], 1.0 - ( y + ( 1.0 - t ) * h ) / size[1]


def aspect( table, name ):
    x, y, w, h = table[name]
    return w / h


def main():
    global SCALE
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"what to draw (default all: {', '.join( NAMES )})" )
    parser.add_argument( "--out", help="write somewhere else" )
    parser.add_argument( "--sheet", help="also write a contact sheet here" )
    parser.add_argument( "--scale", type=float, default=1.0 )
    args = parser.parse_args()
    SCALE = args.scale
    RM.SCALE = args.scale
    out = Path( args.out ) if args.out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    results = {}
    for name in args.names or NAMES:
        results.update( build( name, out ) )
    if args.sheet and results:
        RM.write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
