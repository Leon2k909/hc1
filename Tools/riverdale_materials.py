"""
Riverdale's materials: a nuclear plant's concrete, steel and signage, drawn with numpy into Assets/materials/riverdale/.

    python Tools/riverdale_materials.py [names ...] [--out <dir>] [--sheet <jpg>] [--scale 0.25]

Drawn at their real size, as Boxyard's are (Tools/boxyard_materials.py's helpers draw them). Every name and marking is
the map's own: Riverdale Nuclear is a made-up operator, its logo a triangle round an orbit, and the plant's slogans are
plain words. Run this before Tools/riverdale_map.py. It writes:
    rv_wall         cast-in-place concrete: 8 ft formwork panels, their seams and tie holes, rain runs (192 in tile)
    rv_plinth       the same, darker and grimier: bases, the pool's coping, barriers
    rv_floor        the reactor hall's power-floated floor: sealed, sawn joints, scuffs, wet patches (384 in tile)
    rv_yard         the yard's slabs after rain: dark, joints, oil, tyre marks and standing puddles (768 in tile)
    rv_grating      galvanised bar grating, alpha tested: bearing bars 30 mm apart, cross bars every 4 in
    rv_yellow       safety yellow on steel, chipped and grimed: railings, the crane, stair stringers
    rv_steel        dark grey painted structural steel
    rv_pipe         aluminium pipe jacketing and stainless
    rv_white        white painted tank steel
    rv_liner        the fuel pool's stainless liner plates and their welds
    rv_rack         the spent fuel racks' cells, their insides lit as the pool's light catches them
    rv_hazard       yellow and black hazard stripes
    rv_olive, rv_case   moulded olive and charcoal equipment cases
    rv_letters_dark, rv_letters_light   painted lettering and the logo, alpha tested, from one atlas (LETTERS)
    rv_plates       signs: the radiation caution sign, the UNIT banners, door placards, a clipboard (PLATES)
    rv_screens      the control room's monitors, self-lit (SCREENS)
    rv_pool_water   the pool's surface on hc1_tank_glass.shader: the water's colour by the path through it
and flat paints (PAINTED), the lamps among them self-lit.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage, signal

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import boxyard_materials as BM  # noqa: E402

T = BM.T
lin, mix, smoothstep = BM.lin, BM.mix, BM.smoothstep

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/riverdale"
RESOURCE_DIR = "materials/riverdale"
DEFAULT_AO = "materials/default/default_ao.tga"
FONT = ROOT / "Assets/fonts/Dinish-Bold.ttf"
FONT_LIGHT = ROOT / "Assets/fonts/Dinish-Regular.ttf"

SCALE = 1.0

# Tile sizes (inches) for the map's UVs.
TILES = { "rv_wall": 192.0, "rv_plinth": 192.0, "rv_floor": 384.0, "rv_yard": 768.0, "rv_grating": 24.0,
          "rv_yellow": 48.0, "rv_steel": 48.0, "rv_pipe": 48.0, "rv_white": 96.0, "rv_liner": 96.0, "rv_rack": 30.0,
          "rv_hazard": 32.0, "rv_olive": 48.0, "rv_case": 48.0 }
WATER_Z = -30.0          # riverdale_map's pool surface (world z)


def px( n ):
    return max( 16, int( round( n * SCALE ) ) )


def field( rng, n, tile ):
    """ A square tile's noise maker and its x, z (inches, z up) grids. """
    ppi = n / tile

    def nz( beta, longest, shortest=None ):
        return BM.noise( rng, ( n, n ), ( ppi, ppi ), beta, longest, shortest )

    y, x = np.mgrid[0:n, 0:n].astype( np.float32 ) / ppi
    return nz, x, tile - y, ppi


def runs_down( sources, ppi, length ):
    """ Stains running down from sources (a picture, 1 at the top of a run): each pixel takes what's above it, decaying
    over length inches. Periodic (the tile repeats). """
    a = math.exp( -1.0 / max( 1.0, length * ppi ) )
    twice = np.concatenate( [ sources, sources ], 0 )
    out = signal.lfilter( [ 1.0 - a ], [ 1.0, -a ], twice, axis=0 )
    return out[sources.shape[0]:].astype( np.float32 )


def wobble( rng, shape, sigma ):
    return ndimage.gaussian_filter( rng.standard_normal( shape ).astype( np.float32 ), sigma, mode="wrap" )


# ---------------------------------------------------------------------------------------------------------------------
# Concrete

def concrete_wall( seed=11, base=( 148, 149, 146 ), grime=0.0, n=None ):
    """ Cast-in-place concrete: 96 in square formwork panels (a little different each), their seams' fins, four tie
    holes each, bug holes, efflorescence and rain runs from the ties. """
    n = n or px( 2048 )
    tile = TILES["rv_wall"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    panel = 96.0
    cure, mid, grit = nz( 2.8, 160, 16 ), nz( 2.0, 24, 1.5 ), nz( 0.6, 0.6, 0.1 )
    colour = lin( base )[None, None, :] * ( 1.0 + 0.055 * cure + 0.03 * mid + 0.035 * grit )[..., None]
    colour *= ( 1.0 + 0.02 * nz( 3.0, 200, 40 )[..., None] * np.array( [ 0.6, 0.2, -0.7 ], np.float32 ) )
    pi, pj = np.floor( x / panel ).astype( int ), np.floor( z / panel ).astype( int )
    offsets = rng.normal( 0, 0.035, ( 4, 4 ) ).astype( np.float32 )
    colour *= ( 1.0 + offsets[pi % 4, pj % 4] )[..., None]
    rough = 0.86 + 0.04 * mid
    height = 0.03 * mid + 0.02 * grit + 0.05 * cure * 0.2
    # Seams: a thin fin where the panels met, and a slight step.
    sx = np.minimum( x % panel, panel - x % panel )
    sz = np.minimum( z % panel, panel - z % panel )
    seam = np.minimum( sx, sz )
    fin = np.exp( -( seam / 0.18 ) ** 2 )
    colour *= ( 1.0 - 0.18 * fin + 0.06 * np.exp( -( ( seam - 0.5 ) / 0.35 ) ** 2 ) )[..., None]
    height += 0.06 * fin
    # Tie holes: four a panel, plugged with darker grout, a little sunk.
    hx, hz = x % panel, z % panel
    holes = np.zeros_like( x )
    for cx in ( panel * 0.25, panel * 0.75 ):
        for cz in ( panel * 0.25, panel * 0.75 ):
            d = np.sqrt( ( hx - cx ) ** 2 + ( hz - cz ) ** 2 )
            holes = np.maximum( holes, smoothstep( 0.75, 0.55, d ) )
    colour = mix( colour, lin( ( 92, 92, 90 ) ), holes * 0.85 )
    height -= 0.25 * holes
    # Rain runs: from the ties and the seams' tops, and anywhere a little.
    src = np.zeros_like( x )
    src[( holes > 0.5 )] = 0.6
    dots = ( rng.random( src.shape ) < 0.00004 ).astype( np.float32 )
    src = np.maximum( src, ndimage.grey_dilation( dots, size=( 1, 3 ) ) * rng.uniform( 0.3, 0.9 ) )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.2 ), mode="wrap" )
    runs = np.clip( runs_down( src, ppi, 40.0 ) * 6.0, 0, 1 ) * smoothstep( -0.8, 0.8, nz( 1.6, 30, 3 ) )
    colour = mix( colour, colour * 0.72, runs[..., None] * 0.7 )
    # Bug holes: small air voids.
    pits = smoothstep( 2.9, 3.4, nz( 0.4, 0.5, 0.08 ) )
    colour = mix( colour, colour * 0.45, pits[..., None] )
    height -= 0.08 * pits
    # Efflorescence and dirt in broad clouds.
    salts = smoothstep( 1.4, 2.6, nz( 2.2, 40, 4 ) )
    colour = mix( colour, lin( ( 196, 196, 190 ) ), salts[..., None] * 0.25 )
    dirt = smoothstep( 0.0, 2.0, nz( 2.4, 60, 6 ) ) * ( 0.25 + grime )
    colour = mix( colour, colour * lin( ( 150, 138, 120 ) ) * 3.4, dirt[..., None] * 0.35 )
    if grime:
        colour *= ( 1.0 - 0.25 * grime )
    rough = np.clip( rough + 0.05 * salts - 0.06 * runs, 0.4, 1.0 )
    return colour, rough, height, ppi


def floor_hall( seed=21, n=None ):
    """ A power-floated slab under a clear sealer: dark grey, burnished where the trowel went, sawn joints every 16 ft,
    tyre scuffs, and damp near the pool. """
    n = n or px( 2048 )
    tile = TILES["rv_floor"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    cure, mid, grit = nz( 2.6, 200, 20 ), nz( 1.8, 20, 1.5 ), nz( 0.6, 0.5, 0.1 )
    colour = lin( ( 104, 106, 106 ) )[None, None, :] * ( 1.0 + 0.08 * cure + 0.04 * mid + 0.03 * grit )[..., None]
    swirl = smoothstep( -1.0, 1.4, nz( 1.4, 6, 0.6 ) )
    rough = 0.42 + 0.12 * swirl + 0.06 * cure
    height = 0.01 * mid + 0.006 * grit
    slab = 192.0
    joint = np.minimum( np.minimum( x % slab, slab - x % slab ), np.minimum( z % slab, slab - z % slab ) )
    groove = smoothstep( 0.2, 0.08, joint )
    colour = mix( colour, lin( ( 26, 26, 26 ) ), groove[..., None] * 0.9 )
    height -= 0.25 * groove
    # Tyre scuffs: long soft strokes.
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( 40 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.uniform( 0, math.pi )
        L = rng.uniform( 30, 160 )
        pts = [ ( cx + math.cos( a ) * L * t + rng.normal( 0, 0.4 ), cz + math.sin( a ) * L * t + 6 * math.sin( t * 3 ) ) for t in np.linspace( 0, 1, 12 ) ]
        cv.line( pts, rng.uniform( 2, 5 ), rng.uniform( 0.2, 0.7 ) )
    scuff = ndimage.gaussian_filter( cv.result(), 2.0, mode="wrap" )
    colour = mix( colour, colour * 0.6, scuff[..., None] * 0.6 )
    wet = smoothstep( 1.0, 2.0, nz( 2.6, 120, 12 ) )
    colour = mix( colour, colour * 0.7, wet[..., None] * 0.6 )
    rough = np.clip( mix( rough, 0.12, wet ) + 0.15 * scuff, 0.08, 1.0 )
    return colour, rough, height, ppi


def yard( seed=31, n=None ):
    """ The yard after rain: 16 ft slabs, darker where they're wet, sawn joints with black sealant, oil and tyre marks,
    and standing water where the slabs dip (glassy, darker, the texture flat under it). """
    n = n or px( 4096 )
    tile = TILES["rv_yard"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    cure, mid, grit = nz( 2.8, 300, 30 ), nz( 2.0, 30, 2 ), nz( 0.6, 0.6, 0.19 )
    colour = lin( ( 128, 126, 122 ) )[None, None, :] * ( 1.0 + 0.08 * cure + 0.04 * mid + 0.05 * grit )[..., None]
    slab = 192.0
    joint = np.minimum( np.minimum( x % slab, slab - x % slab ), np.minimum( z % slab, slab - z % slab ) )
    spall = smoothstep( 1.4, 2.6, nz( 1.4, 10, 0.4 ) ) * 1.0
    groove = smoothstep( 0.24 + spall, 0.1, joint )
    colour = mix( colour, lin( ( 18, 18, 18 ) ), groove[..., None] * 0.9 )
    height = 0.03 * mid + 0.03 * grit - 0.4 * groove
    # Damp everywhere (rain): concrete darkens to ~60% wet.
    damp = 0.55 + 0.45 * smoothstep( -1.2, 1.0, nz( 2.4, 200, 20 ) )
    colour = colour * ( 1.0 - 0.4 * damp )[..., None]
    rough = 0.62 - 0.22 * damp + 0.05 * mid
    # Oil and tyre marks.
    oil = smoothstep( 1.6, 2.8, nz( 2.0, 40, 3 ) )
    colour = mix( colour, lin( ( 22, 20, 18 ) ), oil[..., None] * 0.6 )
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( 70 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.choice( [ 0.0, math.pi / 2 ] ) + rng.normal( 0, 0.2 )
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
    # Puddles: where the slab dips (a low-frequency field), shallow and glassy.
    dip = nz( 2.4, 260, 20 ) + 0.35 * nz( 1.8, 40, 4 )
    puddle = smoothstep( 1.05, 1.3, dip )
    colour = mix( colour, colour * 0.55 + lin( ( 8, 10, 12 ) ), puddle[..., None] * 0.85 )
    rough = mix( rough, 0.02, puddle )
    height = mix( height, -0.05, puddle )
    rough = np.clip( rough + 0.1 * oil * 0 - 0.05 * tyres, 0.02, 1.0 )
    return colour, rough, height, ppi


# ---------------------------------------------------------------------------------------------------------------------
# Steel

def painted( seed, colour, chips=0.4, tile=48.0, rough=0.45, grime=0.4, n=None, bare=( 64, 64, 66 ) ):
    """ Paint on steel: mottled, chipped to dark steel at edges (anywhere, since the UVs are planar), grime runs. """
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
    rust = smoothstep( 2.6, 3.0, nz( 1.6, 4, 0.2 ) ) * chip
    c = mix( c, BM.RUST, rust[..., None] * 0.8 )
    src = ( rng.random( ( n, n ) ) < 0.0002 ).astype( np.float32 )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.5 ), mode="wrap" ) * 4
    runs = np.clip( runs_down( src, ppi, 10.0 ) * 4.0, 0, 1 )
    c = mix( c, c * 0.7, runs[..., None] * grime )
    dirt = smoothstep( 0.4, 2.2, nz( 2.4, 20, 2 ) ) * grime
    c = mix( c, BM.GRIME, dirt[..., None] * 0.3 )
    r = np.clip( r + 0.15 * dirt, 0.05, 1 )
    return c, r, h, ppi


def pipe_jacket( seed=51, n=None ):
    n = n or px( 1024 )
    tile = TILES["rv_pipe"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    brush = ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 0.4, 18 ), mode="wrap" )
    brush /= brush.std() + 1e-6
    c = lin( ( 182, 186, 188 ) )[None, None, :] * ( 1.0 + 0.03 * brush + 0.06 * nz( 2.4, 30, 3 ) )[..., None]
    r = 0.32 + 0.05 * brush + 0.1 * smoothstep( 0.5, 2.0, nz( 2.2, 16, 2 ) )
    h = -0.04 * smoothstep( 2.0, 2.6, nz( 2.4, 8, 1.5 ) ) + 0.002 * brush
    smudge = smoothstep( 1.0, 2.4, nz( 2.2, 20, 2 ) )
    c = mix( c, c * 0.75, smudge[..., None] * 0.6 )
    return c, np.clip( r, 0.1, 1 ), h, ppi


def liner( seed=61, n=None ):
    n = n or px( 1024 )
    tile = TILES["rv_liner"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    plate = 48.0
    off = rng.normal( 0, 0.04, ( 2, 2 ) ).astype( np.float32 )
    pi, pj = ( x // plate ).astype( int ) % 2, ( z // plate ).astype( int ) % 2
    c = lin( ( 168, 172, 174 ) )[None, None, :] * ( 1.0 + off[pi, pj] + 0.04 * nz( 2.2, 20, 1 ) )[..., None]
    r = 0.26 + 0.06 * nz( 2.0, 12, 1 ) + 0.04 * off[pi, pj] * 10
    d = np.minimum( np.minimum( x % plate, plate - x % plate ), np.minimum( z % plate, plate - z % plate ) )
    weld = np.exp( -( d / 0.3 ) ** 2 )
    c = mix( c, lin( ( 120, 112, 100 ) ), weld[..., None] * 0.6 )
    h = 0.05 * weld + 0.004 * nz( 0.8, 0.5, 0.1 )
    r = mix( r, 0.55, weld )
    return c, np.clip( r, 0.08, 1 ), h, ppi


def rack( seed=71, n=None ):
    """ Square fuel storage cells, 10 in a side in a 30 in tile: bright steel walls, dark cells whose depth glows. """
    n = n or px( 512 )
    tile = TILES["rv_rack"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    cell = 10.0
    d = np.minimum( np.minimum( x % cell, cell - x % cell ), np.minimum( z % cell, cell - z % cell ) )
    wall = smoothstep( 0.55, 0.35, d )
    inner = smoothstep( 0.6, 2.4, d )
    c = mix( lin( ( 10, 26, 32 ) )[None, None, :] * np.ones( ( n, n, 1 ), np.float32 ), lin( ( 180, 188, 190 ) ), wall[..., None] )
    c *= ( 1.0 + 0.05 * nz( 2.0, 10, 1 ) )[..., None]
    illum = inner * ( 0.7 + 0.3 * smoothstep( -1, 1, nz( 2.0, 20, 2 ) ) )
    r = mix( np.full( ( n, n ), 0.5, np.float32 ), 0.25, wall )
    h = 0.3 * wall
    return c, r, h, ppi, illum


def hazard( seed=81, n=None ):
    n = n or px( 512 )
    tile = TILES["rv_hazard"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    stripe = ( ( x + z ) % 16.0 ) < 8.0
    edge = smoothstep( 0.0, 0.15, np.minimum( ( x + z ) % 8.0, 8.0 - ( x + z ) % 8.0 ) )
    yellow, black = lin( ( 230, 178, 22 ) ), lin( ( 22, 22, 22 ) )
    c = np.where( stripe[..., None], yellow, black ) * ( 1.0 + 0.05 * nz( 2.2, 10, 1 ) )[..., None]
    wear = smoothstep( 1.6, 2.4, nz( 1.6, 4, 0.2 ) )
    c = mix( c, lin( ( 80, 80, 80 ) ), wear[..., None] * 0.7 )
    c = mix( c, BM.GRIME, smoothstep( 0.5, 2.2, nz( 2.4, 16, 2 ) )[..., None] * 0.25 )
    r = 0.55 + 0.1 * wear
    h = 0.01 * edge - 0.02 * wear
    return c, np.full( ( n, n ), 1.0, np.float32 ) * r, h, ppi


def grating( seed=91, n=None ):
    """ Bar grating seen from above: bearing bars every 1.18 in (30 mm), 3/16 in thick, cross bars every 4 in. Returns
    the colour, roughness, height and the alpha (1 on steel). """
    n = n or px( 512 )
    tile = TILES["rv_grating"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    pitch = tile / 20.0                      # 1.2 in, a whole number in the tile
    bx = np.minimum( x % pitch, pitch - x % pitch )
    bearing = smoothstep( 0.13, 0.08, bx )
    cz = np.minimum( z % 4.0, 4.0 - z % 4.0 )
    cross = smoothstep( 0.14, 0.09, cz )
    steel = np.maximum( bearing, cross )
    c = lin( ( 96, 98, 98 ) )[None, None, :] * ( 1.0 + 0.08 * nz( 2.2, 8, 0.5 ) )[..., None]
    dirt = smoothstep( 0.2, 2.0, nz( 2.4, 12, 1 ) )
    c = mix( c, BM.GRIME, dirt[..., None] * 0.4 )
    c = mix( c, lin( ( 214, 168, 30 ) ), cross[..., None] * 0.0 )
    r = 0.55 + 0.15 * dirt
    h = 0.15 * steel + 0.1 * cross
    return c, np.full( ( n, n ), 1.0, np.float32 ) * r, h, ppi, steel


# ---------------------------------------------------------------------------------------------------------------------
# Lettering and the logo (alpha atlas): white on transparent; two materials tint it dark or light.

LETTER_ATLAS = ( 4096, 4096 )
# name -> ( x, y, w, h ) in pixels
LETTERS = {
    "A1": ( 0, 0, 1024, 640 ), "A2": ( 1024, 0, 1024, 640 ), "B1": ( 2048, 0, 1024, 640 ), "B2": ( 3072, 0, 1024, 640 ),
    "reactor_hall_r": ( 0, 640, 1024, 512 ), "reactor_hall_l": ( 1024, 640, 1024, 512 ),
    "turbine_r": ( 2048, 640, 1024, 512 ), "turbine_l": ( 3072, 640, 1024, 512 ),
    "clean_energy": ( 0, 1152, 1536, 896 ), "safety": ( 1536, 1152, 1024, 896 ),
    "logo": ( 2560, 1152, 896, 896 ), "n02": ( 3456, 1152, 640, 448 ), "n04": ( 3456, 1600, 640, 448 ),
    "wordmark": ( 0, 2048, 1280, 640 ), "logo_wordmark": ( 1280, 2048, 2816, 640 ),
    "water_purification": ( 0, 2688, 1536, 896 ), "swl": ( 1536, 2688, 1280, 256 ),
    "unit_text": ( 2816, 2688, 1280, 256 ), "pool_level": ( 1536, 2944, 1280, 256 ),
    "fuel_handling": ( 2816, 2944, 1280, 256 ), "C1": ( 0, 3584, 1024, 512 ),
    "control_room": ( 1024, 3584, 1536, 256 ), "turbine_hall": ( 1024, 3840, 1536, 256 ), "unit1": ( 2560, 3200, 768, 896 ),
    "unit2": ( 3328, 3200, 768, 896 ),
}


def font( size, light=False ):
    return ImageFont.truetype( str( FONT_LIGHT if light else FONT ), max( 6, int( size ) ) )


def text_block( draw, box, lines, fill=255, align="left", light=False, spacing=0.22, track=0.06, pad=0.08 ):
    """ Lines of capitals fitted into box ( x, y, w, h ), as large as fit. """
    x, y, w, h = box
    iw, ih = w * ( 1 - 2 * pad ), h * ( 1 - 2 * pad )
    size = ih / ( len( lines ) + spacing * ( len( lines ) - 1 ) ) / 0.72
    for _ in range( 40 ):
        f = font( size, light )
        widths = [ sum( f.getlength( ch ) for ch in ln ) + track * size * ( len( ln ) - 1 ) for ln in lines ]
        if max( widths ) <= iw:
            break
        size *= 0.95
    cap = 0.72 * size
    total = cap * len( lines ) + spacing * cap * ( len( lines ) - 1 )
    top = y + ( h - total ) / 2
    for k, ( ln, lw ) in enumerate( zip( lines, widths ) ):
        if align == "left":
            cx = x + w * pad
        elif align == "right":
            cx = x + w * ( 1 - pad ) - lw
        else:
            cx = x + ( w - lw ) / 2
        cy = top + k * cap * ( 1 + spacing ) - 0.26 * size
        for ch in ln:
            draw.text( ( cx, cy ), ch, font=f, fill=fill )
            cx += f.getlength( ch ) + track * size


def logo( draw, box, size, fill=255 ):
    """ Riverdale Nuclear's mark: a solid triangle, cut through by an orbit ring, a stem from the apex and a core. Draws
    the triangle and returns the cuts (a mask the size of the atlas). """
    x, y, w, h = box
    s = min( w, h ) * 0.9
    cx, base = x + w / 2, y + ( h + s * 0.866 ) / 2
    top = base - s * 0.866
    draw.polygon( [ ( cx, top ), ( cx + s / 2, base ), ( cx - s / 2, base ) ], fill=fill )
    ring = Image.new( "L", size, 0 )
    rd = ImageDraw.Draw( ring )
    w_ = max( 2, int( s * 0.05 ) )
    # An A: a notch up from the base's middle between its legs...
    rd.polygon( [ ( cx - s * 0.15, base + 2 ), ( cx + s * 0.15, base + 2 ), ( cx, base - s * 0.30 ) ], fill=255 )
    # ...and a swoosh sweeping up across it from the left edge to the right: an orbit seen edge-on.
    rd.arc( ( cx - s * 0.62, base - s * 0.62, cx + s * 0.38, base - s * 0.12 ), 250, 340, fill=255, width=w_ )
    rd.arc( ( cx - s * 0.55, base - s * 0.50, cx + s * 0.45, base - s * 0.02 ), 255, 335, fill=255, width=max( 2, w_ // 2 ) )
    return ring


def letters_atlas():
    W, H = px( LETTER_ATLAS[0] ), px( LETTER_ATLAS[1] )
    k = W / LETTER_ATLAS[0]
    img = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( img )
    cuts = Image.new( "L", ( W, H ), 0 )

    def box( name ):
        x, y, w, h = LETTERS[name]
        return ( x * k, y * k, w * k, h * k )

    for name in ( "A1", "A2", "B1", "B2" ):
        text_block( d, box( name ), [ name ], align="center", track=0.02, pad=0.06 )
    text_block( d, box( "reactor_hall_r" ), [ "> REACTOR", "  HALL" ], align="left" )
    text_block( d, box( "reactor_hall_l" ), [ "REACTOR <", "HALL  " ], align="right" )
    text_block( d, box( "turbine_r" ), [ "TURBINE", "BUILDING >" ], align="left" )
    text_block( d, box( "turbine_l" ), [ "TURBINE", "< BUILDING" ], align="right" )
    text_block( d, box( "clean_energy" ), [ "CLEAN ENERGY", "A BRIGHTER", "TOMORROW" ], align="left", light=True, track=0.12 )
    text_block( d, box( "safety" ), [ "SAFETY", "PEOPLE", "PROGRESS" ], align="left", light=True, track=0.12 )
    ring = logo( d, box( "logo" ), ( W, H ) )
    cuts.paste( ring, ( 0, 0 ), ring )
    text_block( d, box( "n02" ), [ "02" ], align="center", track=0.02 )
    text_block( d, box( "n04" ), [ "04" ], align="center", track=0.02 )
    text_block( d, box( "wordmark" ), [ "RIVERDALE", "NUCLEAR" ], align="center", track=0.08 )
    x, y, w, h = box( "logo_wordmark" )
    lb = ( x, y, h, h )
    ring = logo( d, lb, ( W, H ) )
    cuts.paste( ring, ( 0, 0 ), ring )
    text_block( d, ( x + h * 1.02, y, w - h * 1.02, h ), [ "RIVERDALE", "NUCLEAR" ], align="left", track=0.08, pad=0.1 )
    text_block( d, box( "water_purification" ), [ "WATER", "PURIFICATION", "SYSTEM" ], align="center", track=0.06 )
    text_block( d, box( "swl" ), [ "SWL 125 T" ], align="center", track=0.1 )
    text_block( d, box( "unit_text" ), [ "UNIT 1" ], align="center", track=0.1 )
    text_block( d, box( "pool_level" ), [ "SPENT FUEL POOL" ], align="center", track=0.1 )
    text_block( d, box( "fuel_handling" ), [ "FUEL HANDLING" ], align="center", track=0.1 )
    text_block( d, box( "C1" ), [ "C1" ], align="center", track=0.02, pad=0.06 )
    text_block( d, box( "control_room" ), [ "CONTROL ROOM" ], align="center", track=0.1 )
    text_block( d, box( "turbine_hall" ), [ "TURBINE HALL" ], align="center", track=0.1 )
    text_block( d, box( "unit1" ), [ "UNIT", "1" ], align="center" )
    text_block( d, box( "unit2" ), [ "UNIT", "2" ], align="center" )
    a = np.asarray( img, np.float32 ) / 255.0
    a = a * ( 1.0 - np.asarray( cuts, np.float32 ) / 255.0 )
    rng = np.random.default_rng( 5 )
    wear = BM.noise( rng, a.shape, ( k * 8, k * 8 ), 1.6, 40, 0.5 )
    a *= 1.0 - smoothstep( 1.8, 2.6, wear )
    return a


# ---------------------------------------------------------------------------------------------------------------------
# Plates: opaque signs

PLATE_ATLAS = ( 2048, 2048 )
PLATES = {
    "caution": ( 0, 0, 640, 768 ), "unit1": ( 640, 0, 448, 1024 ), "unit2": ( 1088, 0, 448, 1024 ),
    "door_sign": ( 1536, 0, 256, 320 ), "clipboard": ( 1792, 0, 256, 352 ), "exit": ( 1536, 320, 512, 192 ),
    "lifering_sign": ( 1536, 512, 256, 256 ), "notice": ( 1792, 512, 256, 352 ), "danger": ( 0, 768, 640, 384 ),
    "red": ( 0, 1152, 256, 256 ), "yellow": ( 256, 1152, 256, 256 ), "board": ( 640, 1024, 896, 512 ),
}


def trefoil( d, cx, cy, r, fill ):
    d.ellipse( ( cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18 ), fill=fill )
    for k in range( 3 ):
        a0 = -90 + 120 * k - 30
        d.pieslice( ( cx - r, cy - r, cx + r, cy + r ), a0, a0 + 60, fill=fill )
    hole = r * 0.3
    return hole


def plates_atlas():
    W, H = px( PLATE_ATLAS[0] ), px( PLATE_ATLAS[1] )
    k = W / PLATE_ATLAS[0]
    img = Image.new( "RGB", ( W, H ), ( 60, 60, 60 ) )
    d = ImageDraw.Draw( img )

    def box( name ):
        x, y, w, h = PLATES[name]
        return ( x * k, y * k, w * k, h * k )

    yellow, black, red, white = ( 232, 186, 30 ), ( 22, 22, 22 ), ( 156, 30, 26 ), ( 236, 236, 230 )
    x, y, w, h = box( "caution" )
    d.rectangle( ( x, y, x + w, y + h ), fill=yellow )
    d.rectangle( ( x + w * 0.04, y + w * 0.04, x + w * 0.96, y + h - w * 0.04 ), outline=black, width=int( w * 0.03 ) )
    text_block( d, ( x, y + h * 0.04, w, h * 0.2 ), [ "CAUTION" ], fill=black, align="center", track=0.04 )
    cx, cy, r = x + w / 2, y + h * 0.47, w * 0.26
    d.ellipse( ( cx - r * 1.12, cy - r * 1.12, cx + r * 1.12, cy + r * 1.12 ), fill=black )
    d.ellipse( ( cx - r * 1.02, cy - r * 1.02, cx + r * 1.02, cy + r * 1.02 ), fill=yellow )
    trefoil( d, cx, cy, r * 0.92, black )
    d.ellipse( ( cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3 ), fill=yellow )
    d.ellipse( ( cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18 ), fill=black )
    text_block( d, ( x, y + h * 0.74, w, h * 0.2 ), [ "RADIATION AREA" ], fill=black, align="center", track=0.02 )
    for name, num in ( ( "unit1", "1" ), ( "unit2", "2" ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=red )
        d.rectangle( ( x + w * 0.05, y + w * 0.05, x + w * 0.95, y + h - w * 0.05 ), outline=( 120, 22, 20 ), width=int( w * 0.012 ) )
        text_block( d, ( x, y + h * 0.12, w, h * 0.12 ), [ "UNIT" ], fill=white, align="center" )
        text_block( d, ( x, y + h * 0.26, w, h * 0.22 ), [ num ], fill=white, align="center" )
    x, y, w, h = box( "door_sign" )
    d.rectangle( ( x, y, x + w, y + h ), fill=yellow )
    d.rectangle( ( x + 6 * k, y + 6 * k, x + w - 6 * k, y + h - 6 * k ), outline=black, width=int( 6 * k ) )
    cx = x + w / 2
    d.ellipse( ( cx - w * 0.1, y + h * 0.22, cx + w * 0.1, y + h * 0.22 + w * 0.2 ), fill=black )
    d.polygon( [ ( cx - w * 0.18, y + h * 0.75 ), ( cx - w * 0.12, y + h * 0.42 ), ( cx + w * 0.12, y + h * 0.42 ), ( cx + w * 0.18, y + h * 0.75 ) ], fill=black )
    x, y, w, h = box( "clipboard" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 120, 84, 48 ) )
    d.rectangle( ( x + w * 0.08, y + h * 0.1, x + w * 0.92, y + h * 0.96 ), fill=( 236, 234, 226 ) )
    for j in range( 14 ):
        yy = y + h * ( 0.2 + 0.052 * j )
        d.line( ( x + w * 0.14, yy, x + w * ( 0.86 if j % 3 else 0.6 ), yy ), fill=( 90, 90, 100 ), width=max( 1, int( 2 * k ) ) )
    d.rectangle( ( x + w * 0.3, y + h * 0.02, x + w * 0.7, y + h * 0.12 ), fill=( 160, 160, 164 ) )
    x, y, w, h = box( "exit" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 26, 140, 70 ) )
    text_block( d, ( x, y, w, h ), [ "EXIT" ], fill=white, align="center", track=0.12 )
    x, y, w, h = box( "lifering_sign" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 26, 120, 70 ) )
    d.ellipse( ( x + w * 0.2, y + h * 0.2, x + w * 0.8, y + h * 0.8 ), outline=white, width=int( w * 0.1 ) )
    x, y, w, h = box( "notice" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 230, 230, 224 ) )
    d.rectangle( ( x, y, x + w, y + h * 0.2 ), fill=( 30, 80, 150 ) )
    for j in range( 10 ):
        yy = y + h * ( 0.3 + 0.06 * j )
        d.line( ( x + w * 0.1, yy, x + w * 0.9, yy ), fill=( 110, 110, 116 ), width=max( 1, int( 3 * k ) ) )
    x, y, w, h = box( "danger" )
    d.rectangle( ( x, y, x + w, y + h ), fill=white )
    d.rectangle( ( x, y, x + w, y + h * 0.36 ), fill=( 190, 24, 24 ) )
    text_block( d, ( x, y, w, h * 0.36 ), [ "DANGER" ], fill=white, align="center", track=0.06 )
    text_block( d, ( x, y + h * 0.4, w, h * 0.56 ), [ "AUTHORISED", "PERSONNEL ONLY" ], fill=black, align="center" )
    for name, col in ( ( "red", red ), ( "yellow", yellow ) ):
        x, y, w, h = box( name )
        d.rectangle( ( x, y, x + w, y + h ), fill=col )
    x, y, w, h = box( "board" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 236, 236, 232 ) )
    d.rectangle( ( x, y, x + w, y + h * 0.18 ), fill=( 40, 46, 54 ) )
    text_block( d, ( x, y, w, h * 0.18 ), [ "DAYS WITHOUT A LOST-TIME INCIDENT" ], fill=white, align="center", track=0.04 )
    text_block( d, ( x, y + h * 0.24, w, h * 0.6 ), [ "1462" ], fill=( 30, 110, 60 ), align="center" )
    c = np.asarray( img, np.float32 )
    rng = np.random.default_rng( 9 )
    dirt = smoothstep( 0.2, 2.4, BM.noise( rng, c.shape[:2], ( k * 4, k * 4 ), 2.2, 60, 1 ) )
    c = c * ( 1.0 - 0.18 * dirt[..., None] )
    rough = 0.5 + 0.2 * dirt
    return c, rough


# ---------------------------------------------------------------------------------------------------------------------
# Screens: the control room's monitors (self-lit)

SCREEN_ATLAS = ( 2048, 1024 )
SCREENS = { "schematic": ( 0, 0, 1024, 576 ), "graphs": ( 1024, 0, 1024, 576 ), "table": ( 0, 576, 768, 448 ),
            "camera": ( 768, 576, 768, 448 ), "panel": ( 1536, 576, 512, 448 ) }


def screens_atlas():
    W, H = px( SCREEN_ATLAS[0] ), px( SCREEN_ATLAS[1] )
    k = W / SCREEN_ATLAS[0]
    img = Image.new( "RGB", ( W, H ), ( 6, 12, 20 ) )
    d = ImageDraw.Draw( img )
    rng = np.random.default_rng( 13 )

    def box( name ):
        x, y, w, h = SCREENS[name]
        return ( x * k, y * k, w * k, h * k )

    cyan, blue, amber, green, white = ( 60, 210, 240 ), ( 40, 110, 200 ), ( 240, 170, 40 ), ( 60, 220, 120 ), ( 210, 230, 240 )
    x, y, w, h = box( "schematic" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 8, 24, 44 ) )
    d.rectangle( ( x, y, x + w, y + h * 0.08 ), fill=( 20, 60, 110 ) )
    cx, cy = x + w * 0.35, y + h * 0.55
    for r in ( 0.32, 0.24, 0.12 ):
        d.ellipse( ( cx - h * r, cy - h * r, cx + h * r, cy + h * r ), outline=cyan, width=max( 1, int( 3 * k ) ) )
    for j in range( 7 ):
        for i in range( 7 ):
            if ( i - 3 ) ** 2 + ( j - 3 ) ** 2 <= 10:
                col = green if rng.random() < 0.8 else amber
                d.rectangle( ( cx + ( i - 3.5 ) * h * 0.045, cy + ( j - 3.5 ) * h * 0.045, cx + ( i - 2.6 ) * h * 0.045, cy + ( j - 2.6 ) * h * 0.045 ), fill=col )
    for j in range( 8 ):
        yy = y + h * ( 0.16 + 0.1 * j )
        d.rectangle( ( x + w * 0.66, yy, x + w * ( 0.7 + 0.25 * rng.random() ), yy + h * 0.05 ), fill=blue )
    x, y, w, h = box( "graphs" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 6, 18, 30 ) )
    for g in range( 3 ):
        gy = y + h * ( 0.08 + 0.31 * g )
        d.rectangle( ( x + w * 0.04, gy, x + w * 0.96, gy + h * 0.27 ), outline=( 30, 70, 100 ), width=max( 1, int( 2 * k ) ) )
        pts, v = [], 0.5
        for t in np.linspace( 0, 1, 60 ):
            v = np.clip( v + rng.normal( 0, 0.06 ), 0.1, 0.9 )
            pts.append( ( x + w * ( 0.05 + 0.9 * t ), gy + h * 0.27 * ( 1 - v ) ) )
        d.line( pts, fill=( cyan, green, amber )[g], width=max( 1, int( 3 * k ) ) )
    x, y, w, h = box( "table" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 10, 14, 22 ) )
    for j in range( 14 ):
        yy = y + h * ( 0.05 + 0.065 * j )
        for i in range( 4 ):
            col = white if i == 0 else ( green if rng.random() < 0.85 else amber )
            d.rectangle( ( x + w * ( 0.05 + 0.24 * i ), yy, x + w * ( 0.05 + 0.24 * i + 0.08 + 0.1 * rng.random() ), yy + h * 0.03 ), fill=col )
    x, y, w, h = box( "camera" )
    arr = np.zeros( ( int( h ), int( w ), 3 ), np.float32 )
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]] / max( arr.shape )
    pool = np.clip( 1.0 - ( ( xx - 0.5 ) ** 2 * 3 + ( yy - 0.65 ) ** 2 * 6 ), 0, 1 )
    arr[..., 0] = 20 + 20 * pool
    arr[..., 1] = 40 + 160 * pool
    arr[..., 2] = 60 + 180 * pool
    arr += rng.normal( 0, 6, arr.shape )
    img.paste( Image.fromarray( np.clip( arr, 0, 255 ).astype( np.uint8 ) ), ( int( x ), int( y ) ) )
    d.text( ( x + 8 * k, y + 8 * k ), "CAM 04  POOL", fill=white, font=font( 26 * k ) )
    x, y, w, h = box( "panel" )
    d.rectangle( ( x, y, x + w, y + h ), fill=( 40, 44, 48 ) )
    for j in range( 6 ):
        for i in range( 8 ):
            col = [ ( 200, 40, 30 ), green, amber, ( 30, 30, 34 ), white ][int( rng.integers( 0, 5 ) )]
            d.ellipse( ( x + w * ( 0.06 + 0.115 * i ), y + h * ( 0.08 + 0.15 * j ), x + w * ( 0.06 + 0.115 * i + 0.06 ), y + h * ( 0.08 + 0.15 * j + 0.08 ) ), fill=col )
    c = np.asarray( img, np.float32 )
    # Scanlines and a soft vignette per screen read as glass and pixels.
    c *= ( 0.92 + 0.08 * ( np.arange( H )[:, None, None] % 3 > 0 ) )
    return c


# ---------------------------------------------------------------------------------------------------------------------
# Writing

# Flat paints: colour (sRGB), metalness, roughness, self-illumination brightness (0 for none)
PAINTED = {
    "rv_black": ( ( 22, 22, 24 ), 0.0, 0.6, 0 ),
    "rv_rubber": ( ( 18, 18, 18 ), 0.0, 0.85, 0 ),
    "rv_dark": ( ( 34, 36, 38 ), 0.2, 0.55, 0 ),
    "rv_louvre": ( ( 52, 54, 56 ), 0.5, 0.45, 0 ),
    "rv_door": ( ( 104, 112, 118 ), 0.3, 0.45, 0 ),
    "rv_door_yellow": ( ( 214, 166, 30 ), 0.2, 0.45, 0 ),
    "rv_frame": ( ( 70, 74, 78 ), 0.6, 0.4, 0 ),
    "rv_ring_orange": ( ( 226, 92, 28 ), 0.0, 0.5, 0 ),
    "rv_ring_white": ( ( 230, 230, 224 ), 0.0, 0.5, 0 ),
    "rv_lamp_warm": ( ( 255, 214, 160 ), 0.0, 0.3, 10 ),
    "rv_lamp_cool": ( ( 220, 236, 255 ), 0.0, 0.3, 10 ),
    "rv_lamp_cyan": ( ( 90, 230, 255 ), 0.0, 0.3, 14 ),
    "rv_beacon": ( ( 255, 40, 30 ), 0.0, 0.3, 12 ),
    "rv_window_lit": ( ( 255, 220, 170 ), 0.0, 0.2, 3 ),
    "rv_window_dark": ( ( 30, 38, 46 ), 0.6, 0.12, 0 ),
    "rv_cyan_glow": ( ( 70, 220, 255 ), 0.0, 0.3, 6 ),
    "rv_canvas": ( ( 62, 70, 52 ), 0.0, 0.85, 0 ),
    "rv_desk": ( ( 88, 94, 102 ), 0.1, 0.4, 0 ),
    "rv_chair": ( ( 44, 46, 52 ), 0.0, 0.6, 0 ),
    "rv_forest": ( ( 24, 36, 26 ), 0.0, 0.9, 0 ),
    "rv_pine": ( ( 38, 58, 40 ), 0.0, 0.85, 0 ),
    "rv_pine_far": ( ( 46, 60, 58 ), 0.0, 0.9, 0 ),
    "rv_rock": ( ( 104, 100, 98 ), 0.0, 0.9, 0 ),
    "rv_rock_far": ( ( 128, 136, 150 ), 0.0, 0.9, 0 ),
    "rv_snow": ( ( 236, 240, 246 ), 0.0, 0.7, 0 ),
    "rv_grass": ( ( 70, 78, 50 ), 0.0, 0.9, 0 ),
    "rv_gravel": ( ( 110, 106, 100 ), 0.0, 0.9, 0 ),
    "rv_zinc": ( ( 150, 156, 160 ), 0.6, 0.45, 0 ),
    "rv_line_yellow": ( ( 206, 160, 30 ), 0.0, 0.55, 0 ),
}


def save_grey( path, a, size=None ):
    img = Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" )
    if size:
        img = img.resize( size, Image.LANCZOS )
    img.save( path, optimize=True )


def save_rgb( path, a, quality=92 ):
    img = Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" )
    if str( path ).endswith( ".jpg" ):
        img.save( path, quality=quality, subsampling=0 )
    else:
        img.save( path, optimize=True )


def vmat( colour, normal, rough, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0, illum_tint=( 1, 1, 1 ),
          tint=( 1.0, 1.0, 1.0 ) ):
    lines = [ "// Tools/riverdale_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if alpha:
        lines += [ '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{alpha}"', '    g_flAlphaTestReference "0.5"',
                   '    g_flAntiAliasedEdgeStrength "1"' ]
    if illum:
        lines += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{illum}"', f'    g_flSelfIllumBrightness "{illum_brightness:.2f}"',
                   '    g_flSelfIllumAlbedoFactor "1.0"',
                   f'    g_vSelfIllumTint "[{illum_tint[0]:.6f} {illum_tint[1]:.6f} {illum_tint[2]:.6f} 0.000000]"' ]
    lines += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metalness:.2f}"', f'    TextureColor "{colour}"',
               f'    TextureNormal "{normal}"', f'    TextureRoughness "{rough}"', f'    TextureAmbientOcclusion "{DEFAULT_AO}"',
               f'    g_vColorTint "[{tint[0]:.6f} {tint[1]:.6f} {tint[2]:.6f} 1.000000]"', '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines ) + "\n"


def painted_vmat( colour, metalness, roughness, glow ):
    r, g, b = ( c / 255.0 for c in colour )
    illum = ""
    if glow:
        illum = ( '    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"\n'
                  f'    g_flSelfIllumBrightness "{glow:.2f}"\n    g_flSelfIllumAlbedoFactor "1.0"\n'
                  '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"\n' )
    return ( '// Tools/riverdale_materials.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n' + illum +
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metalness:.2f}"\n'
             '    TextureColor "materials/default/default_color.tga"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"\n'
             f'    TextureAmbientOcclusion "{DEFAULT_AO}"\n'
             f'    g_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"\n'
             '    g_flModelTintAmount "1.0"\n}\n' )


def water_vmat():
    return ( '// Tools/riverdale_materials.py: the fuel pool\'s surface (Reef Hall\'s tank glass, looking down)\n"Layer0"\n{\n'
             '    shader "shaders/hc1_tank_glass.shader"\n'
             '    g_vWaterAbsorb "[0.004200 0.000900 0.000420 0.000000]"\n'
             '    g_flTurbidity "0.0004"\n'
             '    g_vWaterScatter "[0.100000 0.950000 1.350000 0.000000]"\n'
             '    g_vWaterDeep "[0.020000 0.300000 0.550000 0.000000]"\n'
             f'    g_flSurfaceZ "{WATER_Z:.1f}"\n'
             '    g_flDeepRange "340.0"\n'
             '    g_flMaxWater "900.0"\n'
             '    g_flCaustics "1.40"\n'
             '    g_flCausticScale "56.0"\n'
             '    g_flShafts "0.70"\n'
             '    g_flRefraction "0.0030"\n'
             '    g_flGlassRoughness "0.02"\n'
             '    g_vGlassEdge "[0.780000 0.920000 0.960000 0.000000]"\n}\n' )


def write_text( path, text ):
    for attempt in range( 40 ):
        try:
            tmp = path.with_suffix( path.suffix + ".tmp" )
            tmp.write_text( text, encoding="utf-8", newline="\n" )
            tmp.replace( path )
            return
        except PermissionError:
            import time
            time.sleep( 0.25 )
    raise PermissionError( path )


def normal_map( height, ppi ):
    return BM.normals( height, ( ppi, ppi ) )


def write_surface( out, name, colour, rough, height, ppi, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0,
                   illum_tint=( 1, 1, 1 ) ):
    srgb = T.linear_to_srgb( colour )
    save_rgb( out / f"{name}_color.jpg", srgb )
    save_rgb( out / f"{name}_normal.jpg", ( normal_map( height, ppi ) * 0.5 + 0.5 ) * 255, quality=94 )
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
    "rv_wall": lambda: concrete_wall(),
    "rv_plinth": lambda: concrete_wall( seed=12, base=( 122, 122, 118 ), grime=0.6 ),
    "rv_floor": lambda: floor_hall(),
    "rv_yard": lambda: yard(),
    "rv_yellow": lambda: painted( 41, ( 226, 172, 24 ), chips=0.5 ),
    "rv_steel": lambda: painted( 42, ( 76, 80, 84 ), chips=0.3, rough=0.5 ),
    "rv_white": lambda: painted( 43, ( 222, 222, 216 ), chips=0.15, tile=96.0, rough=0.5, grime=0.6 ),
    "rv_olive": lambda: painted( 44, ( 74, 80, 56 ), chips=0.2, rough=0.62, bare=( 50, 52, 44 ) ),
    "rv_case": lambda: painted( 45, ( 44, 46, 48 ), chips=0.2, rough=0.6, bare=( 70, 72, 74 ) ),
    "rv_pipe": lambda: pipe_jacket(),
    "rv_liner": lambda: liner(),
}
METALNESS = { "rv_pipe": 0.85, "rv_liner": 0.9 }
NAMES = list( SURFACES ) + [ "rv_rack", "rv_hazard", "rv_grating", "letters", "rv_plates", "rv_screens", "rv_pool_water", "painted" ]


def all_paints():
    names = list( SURFACES ) + [ "rv_rack", "rv_hazard", "rv_grating", "rv_letters_dark", "rv_letters_light", "rv_plates",
                                 "rv_screens", "rv_pool_water" ] + list( PAINTED )
    return names


def build( name, out ):
    done = {}
    if name in SURFACES:
        c, r, h, ppi = SURFACES[name]()
        done[name] = write_surface( out, name, c, r, h, ppi, METALNESS.get( name, 0.0 ) )
    elif name == "rv_rack":
        c, r, h, ppi, illum = rack()
        done[name] = write_surface( out, name, c, r, h, ppi, 0.5, illum=illum, illum_brightness=8.0, illum_tint=( 0.35, 0.9, 1.0 ) )
    elif name == "rv_hazard":
        c, r, h, ppi = hazard()
        done[name] = write_surface( out, name, c, r, h, ppi )
    elif name == "rv_grating":
        c, r, h, ppi, steel = grating()
        done[name] = write_surface( out, name, c, r, h, ppi, 0.5, alpha=steel )
    elif name == "letters":
        a = letters_atlas()
        save_grey( out / "rv_letters_trans.png", a )
        for tone, tint, rough in ( ( "dark", ( 0.030, 0.032, 0.034 ), 0.7 ), ( "light", ( 0.86, 0.87, 0.86 ), 0.6 ) ):
            text = vmat( "[1.000000 1.000000 1.000000 0.000000]", "materials/default/default_normal.tga",
                         f"[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]", 0.0, f"{RESOURCE_DIR}/rv_letters_trans.png", tint=tint )
            write_text( out / f"rv_letters_{tone}.vmat", text )
        done["rv_letters"] = np.repeat( a[..., None] * 255, 3, -1 )
        print( "wrote rv_letters" )
    elif name == "rv_plates":
        c, r = plates_atlas()
        save_rgb( out / "rv_plates_color.png", c )
        save_grey( out / "rv_plates_rough.png", r )
        write_text( out / "rv_plates.vmat", vmat( f"{RESOURCE_DIR}/rv_plates_color.png", "materials/default/default_normal.tga",
                                                   f"{RESOURCE_DIR}/rv_plates_rough.png" ) )
        done[name] = c
        print( "wrote rv_plates" )
    elif name == "rv_screens":
        c = screens_atlas()
        save_rgb( out / "rv_screens_color.png", c )
        write_text( out / "rv_screens.vmat", vmat( f"{RESOURCE_DIR}/rv_screens_color.png", "materials/default/default_normal.tga",
                                                    "[0.200000 0.200000 0.200000 0.000000]", illum="[1.000000 1.000000 1.000000 0.000000]",
                                                    illum_brightness=3.0 ) )
        done[name] = c
        print( "wrote rv_screens" )
    elif name == "rv_pool_water":
        write_text( out / "rv_pool_water.vmat", water_vmat() )
        print( "wrote rv_pool_water" )
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


def write_sheet( results, path ):
    tiles = []
    for name, colour in results.items():
        img = Image.fromarray( np.clip( colour, 0, 255 ).astype( np.uint8 ) ).convert( "RGB" )
        img.thumbnail( ( 512, 512 ), Image.LANCZOS )
        canvas = Image.new( "RGB", ( 512, 512 ), ( 16, 16, 16 ) )
        canvas.paste( img, ( 0, 0 ) )
        ImageDraw.Draw( canvas ).text( ( 6, 6 ), name, fill=( 255, 60, 60 ) )
        tiles.append( canvas )
    cols = 4
    rows = ( len( tiles ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( 512 * cols, 512 * rows ), ( 16, 16, 16 ) )
    for k, tl in enumerate( tiles ):
        sheet.paste( tl, ( 512 * ( k % cols ), 512 * ( k // cols ) ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    global SCALE
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"what to draw (default all: {', '.join( NAMES )})" )
    parser.add_argument( "--out", help="write somewhere else" )
    parser.add_argument( "--sheet", help="also write a contact sheet here" )
    parser.add_argument( "--scale", type=float, default=1.0 )
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
