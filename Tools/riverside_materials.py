"""
Riverside's materials: a Florida trailer park at night after rain, drawn with numpy into Assets/materials/riverside/.

    python Tools/riverside_materials.py [names ...] [--out <dir>] [--sheet <jpg>] [--scale 0.25]

Drawn at their real size, as Boxyard's and Riverdale's are (Tools/boxyard_materials.py's helpers). Every name, sign and
slogan is the map's own: Riverside Trailer Park, the Lucky Stop and its slogans are made up. The spray paint, the brush
lettering and the neon script are drawn from strokes (STROKES, SCRIPT below), not from a font, so they read hand-made.
Run this before Tools/riverside_map.py. It writes:
    rs_mud          the park's lanes: wet mud with wandering tyre ruts, standing water and stones (768 in tile)
    rs_yard         the lots: trampled grass, bare mud and litter (512 in tile)
    rs_gravel       the entrance pad's wet gravel (256 in tile)
    rs_siding       aluminium trailer siding, ribbed, chalked and streaked, anchored: v 0 at the wall's foot (96 in square)
    rs_roof         galvanised trailer roofing, rusting at its seams (96 in tile)
    rs_skirt        corrugated skirting round a trailer's base, mud splashed (96 in square, anchored)
    rs_boards       the store's painted board and batten, peeling (96 in square, anchored)
    rs_plywood      plywood sheets nailed over windows, water stained (96 in tile)
    rs_wood         weathered grey planks: porches, decks, crates, fences (64 in tile)
    rs_pole         creosoted pole timber, checked along its grain (64 in tile)
    rs_ties         railroad ties stacked into the retaining walls (96 in tile)
    rs_concrete     cracked, dirty slabs and steps (192 in tile)
    rs_rust         rusted sheet steel: drums, the wrecked truck, the towers (48 in tile)
    rs_chainlink    galvanised 2 in chain-link, alpha tested (24 in tile)
    rs_sandbag      polypropylene and burlap sandbags (48 in tile)
    rs_lit          lit signs, self-lit (LIT): the park sign's neon and bulbs, the marquee, the Lucky Stop's board, the
                    NO PLACE BETTER neon, an OPEN sign, the store's window glow and drinks fridge
    rs_signs        painted and printed signs (SIGNS): the speed limit, the TRAILER PARK PEOPLE TOO board, the cooler's
                    lid, posters, lot numbers, the office's sign
    rs_paint_red, rs_paint_white, rs_paint_dark   spray paint and brushed lettering from one alpha atlas (PAINT)
and flat paints (PAINTED), the bulbs, lamps and lit windows among them self-lit.
"""
import argparse
import math
import platform
import sys
from pathlib import Path


def _no_wmi( *args, **kwargs ):
    raise OSError( "WMI query skipped" )


# Python 3.13's platform module asks Windows' WMI service for the OS version, and scipy's import reaches it through
# numpy.testing. When WMI stops answering, the import hangs for good (seen 2026-10-15), so skip it: platform falls back
# to its older way.
platform._wmi_query = _no_wmi

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
from scipy import ndimage, signal

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import boxyard_materials as BM  # noqa: E402

T = BM.T
lin, mix, smoothstep = BM.lin, BM.mix, BM.smoothstep

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/riverside"
RESOURCE_DIR = "materials/riverside"
DEFAULT_AO = "materials/default/default_ao.tga"
FONT = ROOT / "Assets/fonts/Dinish-Bold.ttf"
FONT_LIGHT = ROOT / "Assets/fonts/Dinish-Regular.ttf"
FONT_CHAKRA = ROOT / "Assets/fonts/ChakraPetch-Bold.ttf"

SCALE = 1.0

# Tile sizes (inches) for the map's world-mapped UVs. Anchored paints (siding, boards, skirting) take explicit UVs.
TILES = { "rs_mud": 768.0, "rs_yard": 512.0, "rs_gravel": 256.0, "rs_siding": 96.0, "rs_roof": 96.0, "rs_skirt": 96.0,
          "rs_boards": 96.0, "rs_plywood": 96.0, "rs_wood": 64.0, "rs_pole": 64.0, "rs_ties": 96.0, "rs_concrete": 192.0,
          "rs_rust": 48.0, "rs_chainlink": 24.0, "rs_sandbag": 48.0 }


def px( n ):
    return max( 16, int( round( n * SCALE ) ) )


def field( rng, n, tile, m=None ):
    """ A tile's noise maker and its x, z grids (inches, z up). m: its height in pixels if it isn't square. """
    m = m or n
    ppi = n / tile

    def nz( beta, longest, shortest=None ):
        return BM.noise( rng, ( m, n ), ( ppi, ppi ), beta, longest, shortest )

    y, x = np.mgrid[0:m, 0:n].astype( np.float32 ) / ppi
    return nz, x, m / ppi - y, ppi


def runs_down( sources, ppi, length, wrap=True ):
    """ Stains running down from sources: each pixel takes what's above it, decaying over length inches. """
    a = math.exp( -1.0 / max( 1.0, length * ppi ) )
    if wrap:
        twice = np.concatenate( [ sources, sources ], 0 )
        out = signal.lfilter( [ 1.0 - a ], [ 1.0, -a ], twice, axis=0 )
        return out[sources.shape[0]:].astype( np.float32 )
    return signal.lfilter( [ 1.0 - a ], [ 1.0, -a ], sources, axis=0 ).astype( np.float32 )


def blur( a, sigma, wrap=True ):
    return ndimage.gaussian_filter( a, sigma, mode="wrap" if wrap else "nearest" )


# ---------------------------------------------------------------------------------------------------------------------
# Ground

def mud( seed=101, n=None ):
    """ The lanes after rain: sticky dark mud churned into wandering ruts by tyres, standing water in the ruts and the
    hollows (dark, glassy: it mirrors the park's lights), a scatter of limestone gravel trodden in, and twigs. """
    n = n or px( 4096 )
    tile = TILES["rs_mud"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    broad, mid, fine = nz( 2.6, 400, 30 ), nz( 2.0, 40, 2 ), nz( 1.0, 2, 0.15 )
    colour = lin( ( 74, 58, 44 ) )[None, None, :] * ( 1.0 + 0.10 * broad + 0.06 * mid + 0.05 * fine )[..., None]
    colour *= ( 1.0 + 0.05 * nz( 3.0, 300, 60 )[..., None] * np.array( [ 0.5, 0.1, -0.6 ], np.float32 ) )
    height = 0.8 * broad + 0.35 * mid + 0.08 * fine
    # Tyre ruts: pairs of tracks 60 in apart wandering across the tile, each a rounded trough with churned rims.
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    rims = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( 10 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.uniform( 0, 2 * math.pi )
        L = rng.uniform( 300, 900 )
        bend = rng.normal( 0, 0.0018 )
        width = rng.uniform( 7, 10 )
        for off in ( -30.0, 30.0 ):
            pts = []
            for t in np.linspace( 0, 1, 40 ):
                s = L * t
                ang = a + bend * s
                px_, pz_ = cx + math.cos( ang ) * s - math.sin( ang ) * off, cz + math.sin( ang ) * s + math.cos( ang ) * off
                pts.append( ( px_, pz_ ) )
            for dx in ( -tile, 0.0, tile ):
                for dz in ( -tile, 0.0, tile ):
                    shifted = [ ( p[0] + dx, p[1] + dz ) for p in pts ]
                    cv.line( shifted, width, rng.uniform( 0.7, 1.0 ) )
                    rims.line( shifted, width + 6, 0.6 )
    trough = blur( cv.result(), 2.0 * ppi / 5.3 )
    rim = np.clip( blur( rims.result(), 3.0 * ppi / 5.3 ) - trough, 0, 1 )
    tread = smoothstep( 0.2, 1.4, nz( 1.0, 3, 0.4 ) ) * trough
    height += -2.2 * trough + 0.9 * rim + 0.25 * tread
    colour = mix( colour, colour * 0.72, trough[..., None] * 0.5 )
    colour = mix( colour, colour * 1.12, rim[..., None] * 0.4 )
    # Gravel trodden in: small pale stones, more at the edges of the ruts, sunk to their tops.
    stones = np.zeros( ( n, n ), np.float32 )
    count = int( 9000 * ( n / 4096 ) ** 2 )
    sx, sz = rng.integers( 0, n, count ), rng.integers( 0, n, count )
    stones[sz, sx] = rng.uniform( 0.5, 1.0, count )
    stones = ndimage.grey_dilation( stones, size=( 2, 2 ) )
    stones = blur( stones, 0.7 ) * ( 1.0 - 0.7 * trough )
    colour = mix( colour, lin( ( 150, 140, 122 ) ), np.clip( stones * 1.6, 0, 1 )[..., None] * 0.8 )
    height += 0.3 * stones
    # Twigs and leaves: thin dark strokes.
    tw = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( int( 900 * ( n / 4096 ) ** 2 ) + 40 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        a = rng.uniform( 0, math.pi )
        L = rng.uniform( 1.5, 7 )
        tw.line( [ ( cx, cz ), ( cx + math.cos( a ) * L, cz + math.sin( a ) * L ) ], rng.uniform( 0.15, 0.35 ), rng.uniform( 0.4, 1.0 ) )
    twigs = tw.result()
    colour = mix( colour, lin( ( 34, 26, 20 ) ), twigs[..., None] * 0.8 )
    # Wetness: all of it damp, wetter in the ruts; water stands where the ground is lowest.
    low = -height + 0.6 * nz( 2.2, 200, 20 )
    wet = np.clip( 0.55 + 0.35 * trough + 0.25 * smoothstep( -0.5, 1.5, low ), 0, 1 )
    colour *= ( 1.0 - 0.35 * wet )[..., None]
    rough = 0.72 - 0.38 * wet + 0.05 * mid
    water = smoothstep( 1.25, 1.55, low )
    edge = smoothstep( 1.0, 1.25, low ) * ( 1 - water )
    colour = mix( colour, colour * 0.45 + lin( ( 6, 7, 9 ) ), water[..., None] * 0.92 )
    colour = mix( colour, colour * 0.75, edge[..., None] * 0.5 )
    rough = mix( rough, 0.03, water )
    rough = mix( rough, 0.12, edge )
    flat = np.where( water > 0.5, height.min() * 0 + np.percentile( height, 8 ), height )
    height = mix( height, flat, water )
    return colour, np.clip( rough, 0.02, 1.0 ), height, ppi


def yard( seed=111, n=None ):
    """ A lot between trailers: tufts of coarse grass (St. Augustine gone wild, bahia seed heads) worn to mud where people
    walk, sand showing through, cigarette ends and bottle caps. """
    n = n or px( 2048 )
    tile = TILES["rs_yard"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    worn = smoothstep( -0.6, 0.8, nz( 2.4, 220, 20 ) + 0.4 * nz( 1.8, 30, 3 ) )
    blades = nz( 0.8, 1.2, 0.12 )
    tufts = smoothstep( -0.3, 1.2, nz( 1.6, 8, 0.6 ) )
    grass = lin( ( 58, 66, 34 ) )[None, None, :] * ( 1.0 + 0.25 * blades + 0.12 * nz( 2.0, 40, 3 ) )[..., None]
    grass = mix( grass, lin( ( 92, 86, 52 ) ), smoothstep( 0.8, 2.2, blades )[..., None] * 0.4 )
    dirt = lin( ( 70, 58, 44 ) )[None, None, :] * ( 1.0 + 0.08 * nz( 2.0, 30, 2 ) + 0.06 * nz( 0.8, 1, 0.15 ) )[..., None]
    sand = smoothstep( 1.0, 2.2, nz( 2.2, 60, 6 ) )
    dirt = mix( dirt, lin( ( 124, 112, 88 ) ), sand[..., None] * 0.5 )
    cover = np.clip( ( 1 - worn ) * ( 0.4 + 0.6 * tufts ), 0, 1 )
    colour = mix( dirt, grass, cover[..., None] )
    height = 0.25 * blades * cover + 0.3 * nz( 2.0, 30, 2 ) - 0.1 * worn
    rough = 0.82 - 0.2 * worn * smoothstep( 0.0, 1.5, nz( 2.4, 120, 12 ) )
    colour *= ( 1.0 - 0.18 * worn )[..., None]
    litter = ( rng.random( ( n, n ) ) < 0.00004 ).astype( np.float32 )
    litter = ndimage.grey_dilation( litter, size=( 2, 3 ) )
    colour = mix( colour, lin( ( 190, 180, 160 ) ), litter[..., None] * 0.6 )
    return colour, np.clip( rough, 0.05, 1.0 ), height, ppi


def gravel( seed=121, n=None ):
    """ The entrance pad: crushed limestone gone grey, wet, rutted lightly, mud tracked over it. """
    n = n or px( 2048 )
    tile = TILES["rs_gravel"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    cells = np.zeros( ( n, n ), np.float32 )
    count = int( 120000 * ( n / 2048 ) ** 2 )
    sx, sz = rng.integers( 0, n, count ), rng.integers( 0, n, count )
    cells[sz, sx] = rng.uniform( 0.3, 1.0, count )
    stones = blur( ndimage.grey_dilation( cells, size=( 3, 3 ) ), 0.8 )
    stones /= stones.max() + 1e-6
    colour = lin( ( 112, 106, 96 ) )[None, None, :] * ( 0.7 + 0.6 * stones )[..., None]
    colour *= ( 1.0 + 0.08 * nz( 2.4, 60, 4 ) )[..., None]
    tracked = smoothstep( 0.3, 1.6, nz( 2.2, 120, 10 ) )
    colour = mix( colour, lin( ( 70, 56, 42 ) ), tracked[..., None] * 0.6 )
    wet = 0.5 + 0.4 * smoothstep( -0.5, 1.5, nz( 2.4, 100, 10 ) )
    colour *= ( 1.0 - 0.3 * wet )[..., None]
    height = 0.35 * stones + 0.2 * nz( 2.0, 20, 2 )
    rough = 0.7 - 0.35 * wet + 0.1 * ( 1 - stones )
    water = smoothstep( 1.6, 1.9, nz( 2.4, 140, 14 ) )
    colour = mix( colour, colour * 0.5, water[..., None] * 0.8 )
    rough = mix( rough, 0.04, water )
    return colour, np.clip( rough, 0.02, 1 ), height, ppi


# ---------------------------------------------------------------------------------------------------------------------
# Trailers

def siding( seed=131, n=None ):
    """ Aluminium trailer siding on a wall 96 in high (v 0 at its foot): horizontal ribs every 6 in with a lap shadow,
    vertical panel joints every 48 in, the paint chalked by the sun, rust and black mildew running down from the joints
    and the drip edge, mud splashed up the bottom foot. Near white: each trailer tints it. """
    n = n or px( 1024 )
    tile = TILES["rs_siding"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    base = lin( ( 226, 224, 214 ) )
    colour = base[None, None, :] * ( 1.0 + 0.035 * nz( 2.6, 60, 6 ) + 0.02 * nz( 0.8, 0.8, 0.1 ) )[..., None]
    rib = 6.0
    phase = ( z % rib ) / rib
    lap = smoothstep( 0.0, 0.08, phase ) * smoothstep( 1.0, 0.85, phase )
    shadow = np.exp( -( phase / 0.035 ) ** 2 )
    crimp = np.exp( -( ( phase - 0.5 ) / 0.04 ) ** 2 )
    colour *= ( 0.80 + 0.2 * lap - 0.12 * crimp )[..., None]
    height = 0.12 * lap - 0.05 * crimp + 0.08 * phase
    joint = np.minimum( x % 48.0, 48.0 - x % 48.0 )
    j = np.exp( -( joint / 0.3 ) ** 2 )
    colour *= ( 1.0 - 0.25 * j )[..., None]
    height += 0.05 * j
    # Runs from the joints, the window corners and the drip edge at the top.
    src = np.zeros_like( x )
    src[( joint < 0.5 ) & ( rng.random( x.shape ) < 0.02 )] = 1.0
    src[( z > 93 )] += ( rng.random( src[z > 93].shape ) < 0.01 ) * 1.0
    src = blur( src, ( 0.6, 1.2 ) )
    runs = np.clip( runs_down( src, ppi, 30.0, wrap=False ) * 10.0, 0, 1 ) * smoothstep( -1.0, 0.8, nz( 1.6, 20, 2 ) )
    rust = runs * smoothstep( 0.0, 1.5, nz( 1.8, 10, 1 ) )
    colour = mix( colour, lin( ( 92, 90, 82 ) ), ( runs * 0.6 )[..., None] )
    colour = mix( colour, BM.RUST_STAIN, ( rust * 0.7 )[..., None] )
    mildew = smoothstep( 0.8, 2.2, nz( 2.2, 30, 2 ) ) * ( 0.4 + 0.6 * smoothstep( 40, 0, z ) )
    colour = mix( colour, lin( ( 60, 64, 48 ) ), mildew[..., None] * 0.35 )
    splash = smoothstep( 22, 0, z ) * smoothstep( -0.8, 1.2, nz( 1.4, 6, 0.5 ) )
    colour = mix( colour, lin( ( 78, 62, 46 ) ), splash[..., None] * 0.8 )
    dents = smoothstep( 2.2, 2.8, nz( 2.4, 14, 3 ) )
    height -= 0.4 * dents
    rough = 0.55 + 0.15 * runs + 0.1 * splash - 0.05 * lap
    return colour, np.clip( rough, 0.1, 1 ), height, ppi


def roof( seed=141, n=None ):
    """ A trailer's roof: galvanised steel, a standing rib every 16 in, rust at the laps and screws, black streaks. """
    n = n or px( 1024 )
    tile = TILES["rs_roof"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    colour = lin( ( 132, 134, 132 ) )[None, None, :] * ( 1.0 + 0.08 * nz( 2.4, 40, 4 ) + 0.04 * nz( 0.8, 1, 0.1 ) )[..., None]
    rib = np.minimum( x % 16.0, 16.0 - x % 16.0 )
    r = np.exp( -( rib / 0.6 ) ** 2 )
    height = 0.6 * r
    colour *= ( 1.0 + 0.12 * r )[..., None]
    lap = np.exp( -( np.minimum( z % 96.0, 96.0 - z % 96.0 ) / 1.0 ) ** 2 )
    rust = np.clip( smoothstep( 0.6, 2.0, nz( 2.0, 16, 1 ) ) + lap * 0.8, 0, 1 ) * smoothstep( -0.6, 1.0, nz( 2.2, 60, 6 ) )
    colour = mix( colour, BM.RUST, rust[..., None] * 0.75 )
    streak = smoothstep( 0.5, 2.0, blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 30, 1.5 ) ) * 12 )
    colour = mix( colour, lin( ( 40, 40, 38 ) ), streak[..., None] * 0.4 )
    rough = 0.45 + 0.4 * rust + 0.1 * streak
    return colour, np.clip( rough, 0.1, 1 ), height, ppi


def skirt( seed=151, n=None ):
    """ Corrugated skirting round a trailer's foot, 32 in high, painted dark, mud splashed and dented. """
    n = n or px( 512 )
    tile = TILES["rs_skirt"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    w = np.sin( 2 * math.pi * x / 2.67 )
    colour = lin( ( 70, 72, 70 ) )[None, None, :] * ( 1.0 + 0.1 * w + 0.06 * nz( 2.4, 20, 2 ) )[..., None]
    height = 0.3 * w
    splash = smoothstep( 40, 0, z ) * smoothstep( -0.6, 1.4, nz( 1.4, 5, 0.4 ) )
    colour = mix( colour, lin( ( 80, 64, 48 ) ), splash[..., None] * 0.85 )
    rust = smoothstep( 1.5, 2.6, nz( 1.8, 8, 1 ) )
    colour = mix( colour, BM.RUST_DARK, rust[..., None] * 0.6 )
    dents = smoothstep( 2.0, 2.8, nz( 2.4, 12, 2 ) )
    height -= 0.6 * dents
    rough = 0.6 + 0.2 * splash
    return colour, np.clip( rough, 0.1, 1 ), height, ppi


def boards( seed=161, n=None ):
    """ Board and batten on the store, 96 in high (anchored): 10 in boards with 2.5 in battens, painted a sea-salt white
    long ago, the paint flaking to grey wood, grime and mildew low down, rust from the nails. """
    n = n or px( 1024 )
    tile = TILES["rs_boards"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    grain = blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 14, 0.6 ) )
    grain /= grain.std() + 1e-6
    wood = lin( ( 118, 110, 98 ) )[None, None, :] * ( 1.0 + 0.12 * grain + 0.06 * nz( 2.0, 20, 2 ) )[..., None]
    paint = lin( ( 214, 212, 200 ) )[None, None, :] * ( 1.0 + 0.04 * nz( 2.4, 30, 3 ) )[..., None]
    flake = smoothstep( 1.1, 1.7, nz( 1.6, 6, 0.3 ) + 0.4 * grain + 0.5 * smoothstep( 30, 0, z ) )
    colour = mix( paint, wood, flake[..., None] )
    pitch = 12.5
    bx = x % pitch
    batten = smoothstep( 0.0, 0.3, bx ) * smoothstep( 2.8, 2.5, bx )
    edge = np.exp( -( ( bx - 2.65 ) / 0.25 ) ** 2 ) + np.exp( -( ( bx - 0.0 ) / 0.25 ) ** 2 )
    colour *= ( 1.0 + 0.06 * batten - 0.3 * edge )[..., None]
    height = 0.7 * batten - 0.1 * flake + 0.05 * grain
    grime = smoothstep( 36, 0, z ) * smoothstep( -0.5, 1.2, nz( 2.0, 20, 2 ) )
    colour = mix( colour, lin( ( 66, 60, 50 ) ), grime[..., None] * 0.6 )
    src = np.zeros_like( x )
    src[( rng.random( x.shape ) < 0.00012 )] = 1
    src = blur( src, ( 0.5, 0.8 ) )
    nails = np.clip( runs_down( src, ppi, 8.0, wrap=False ) * 30.0, 0, 1 )
    colour = mix( colour, BM.RUST_STAIN, nails[..., None] * 0.7 )
    rough = 0.72 + 0.12 * flake
    return colour, np.clip( rough, 0.1, 1 ), height, ppi


def plywood( seed=171, n=None ):
    """ 4 x 8 ft plywood sheets: face veneer grain, plugs, the edges grey and swollen, water stains, nail lines. """
    n = n or px( 1024 )
    tile = TILES["rs_plywood"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    warp = 6.0 * nz( 2.0, 40, 4 )
    rings = np.sin( ( x + warp ) * 0.9 + 3 * nz( 2.0, 20, 2 ) ) * 0.5 + 0.5
    colour = lin( ( 168, 140, 104 ) )[None, None, :] * ( 0.9 + 0.12 * rings + 0.05 * nz( 2.0, 10, 1 ) )[..., None]
    sheet = np.minimum( np.minimum( x % 48.0, 48.0 - x % 48.0 ), np.minimum( z % 96.0, 96.0 - z % 96.0 ) )
    edge = smoothstep( 6.0, 0.0, sheet )
    colour = mix( colour, lin( ( 104, 98, 90 ) ), edge[..., None] * 0.6 )
    stains = smoothstep( 0.6, 1.8, nz( 2.2, 40, 4 ) )
    colour = mix( colour, colour * 0.6, stains[..., None] * 0.5 )
    gap = np.exp( -( sheet / 0.15 ) ** 2 )
    colour *= ( 1.0 - 0.6 * gap )[..., None]
    nails = ( ( np.abs( x % 48.0 - 0.75 ) < 0.18 ) | ( np.abs( x % 48.0 - 47.25 ) < 0.18 ) ) & ( np.abs( z % 6.0 - 3.0 ) < 0.18 )
    colour = mix( colour, lin( ( 50, 46, 40 ) ), nails.astype( np.float32 )[..., None] * 0.8 )
    height = 0.05 * rings - 0.3 * gap
    rough = 0.78 + 0.1 * edge
    return colour, np.clip( rough, 0.1, 1 ), height, ppi


def planks( seed=181, n=None ):
    """ Weathered planks, silver-grey: 5.5 in boards with gaps, grain, splits, darker where they stay wet. """
    n = n or px( 1024 )
    tile = TILES["rs_wood"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    grain = blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 0.6, 18 ) )
    grain /= grain.std() + 1e-6
    board = np.floor( x / 5.75 ).astype( int )
    shade = rng.normal( 0, 0.08, 64 ).astype( np.float32 )[board % 64]
    colour = lin( ( 118, 112, 102 ) )[None, None, :] * ( 1.0 + 0.14 * grain + shade + 0.05 * nz( 2.0, 20, 2 ) )[..., None]
    g = np.minimum( x % 5.75, 5.75 - x % 5.75 )
    gap = smoothstep( 0.22, 0.05, g )
    colour = mix( colour, lin( ( 20, 18, 16 ) ), gap[..., None] * 0.9 )
    wet = smoothstep( -0.3, 1.5, nz( 2.4, 40, 4 ) )
    colour *= ( 1.0 - 0.3 * wet )[..., None]
    height = 0.12 * grain - 0.4 * gap
    rough = 0.8 - 0.25 * wet
    return colour, np.clip( rough, 0.1, 1 ), height, ppi


def pole( seed=191, n=None ):
    """ Creosoted southern pine: brown-black, checks along the grain, lighter where the creosote's weathered off. """
    n = n or px( 512 )
    tile = TILES["rs_pole"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    grain = blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 20, 0.5 ) )
    grain /= grain.std() + 1e-6
    colour = lin( ( 70, 54, 40 ) )[None, None, :] * ( 1.0 + 0.15 * grain + 0.1 * nz( 2.2, 30, 3 ) )[..., None]
    checks = smoothstep( 2.2, 2.8, blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 40, 0.4 ) ) * 14 )
    colour = mix( colour, lin( ( 14, 12, 10 ) ), checks[..., None] )
    bleach = smoothstep( 0.4, 1.8, nz( 2.4, 40, 4 ) )
    colour = mix( colour, lin( ( 112, 100, 86 ) ), bleach[..., None] * 0.4 )
    height = 0.1 * grain - 0.3 * checks
    rough = 0.82
    return colour, np.full( ( n, n ), rough, np.float32 ), height, ppi


def ties( seed=201, n=None ):
    """ Railroad ties laid flat into a retaining wall: 7 in courses, 102 in ties staggered, creosote black-brown going
    grey, split ends, moss and mud in the joints. """
    n = n or px( 1024 )
    tile = TILES["rs_ties"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    course = np.floor( z / 8.0 ).astype( int )
    offset = ( course % 3 ) * 32.0
    along = ( x + offset ) % 96.0
    grain = blur( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 0.5, 16 ) )
    grain /= grain.std() + 1e-6
    shade = rng.normal( 0, 0.12, 64 ).astype( np.float32 )[course % 64]
    colour = lin( ( 66, 56, 46 ) )[None, None, :] * ( 1.0 + 0.16 * grain + shade + 0.08 * nz( 2.2, 30, 3 ) )[..., None]
    joint_h = np.exp( -( np.minimum( z % 8.0, 8.0 - z % 8.0 ) / 0.45 ) ** 2 )
    joint_v = np.exp( -( np.minimum( along, 96.0 - along ) / 0.5 ) ** 2 )
    joint = np.clip( joint_h + joint_v, 0, 1 )
    colour = mix( colour, lin( ( 22, 20, 16 ) ), joint[..., None] * 0.9 )
    grey = smoothstep( 0.0, 1.8, nz( 2.4, 50, 5 ) )
    colour = mix( colour, lin( ( 120, 112, 100 ) ), grey[..., None] * 0.35 )
    moss = smoothstep( 0.6, 1.8, nz( 2.0, 12, 1 ) ) * ( 0.3 + joint )
    colour = mix( colour, lin( ( 50, 64, 30 ) ), np.clip( moss, 0, 1 )[..., None] * 0.4 )
    height = 0.15 * grain - 1.0 * joint
    rough = 0.85
    return colour, np.full( ( n, n ), rough, np.float32 ) - 0.1 * moss, height, ppi


def concrete( seed=211, n=None ):
    n = n or px( 2048 )
    tile = TILES["rs_concrete"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    colour = lin( ( 120, 116, 108 ) )[None, None, :] * ( 1.0 + 0.08 * nz( 2.6, 80, 8 ) + 0.05 * nz( 0.8, 1, 0.12 ) )[..., None]
    cv = BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for _ in range( 22 ):
        p = np.array( ( rng.uniform( 0, tile ), rng.uniform( 0, tile ) ) )
        a = rng.uniform( 0, 2 * math.pi )
        pts = [ tuple( p ) ]
        for _ in range( 12 ):
            a += rng.normal( 0, 0.5 )
            p = p + np.array( ( math.cos( a ), math.sin( a ) ) ) * rng.uniform( 3, 9 )
            pts.append( tuple( p ) )
        cv.line( pts, rng.uniform( 0.08, 0.2 ), 1.0 )
    cracks = cv.result()
    colour = mix( colour, lin( ( 30, 28, 26 ) ), cracks[..., None] )
    dirt = smoothstep( 0.0, 2.0, nz( 2.2, 40, 4 ) )
    colour = mix( colour, lin( ( 70, 60, 48 ) ), dirt[..., None] * 0.5 )
    wet = 0.4 + 0.4 * smoothstep( -0.5, 1.5, nz( 2.4, 80, 8 ) )
    colour *= ( 1 - 0.3 * wet )[..., None]
    height = 0.05 * nz( 2.0, 20, 2 ) - 0.2 * cracks
    rough = 0.75 - 0.3 * wet
    return colour, np.clip( rough, 0.05, 1 ), height, ppi


def rust( seed=221, n=None ):
    n = n or px( 1024 )
    tile = TILES["rs_rust"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    a = smoothstep( -0.5, 1.5, nz( 2.2, 20, 2 ) )
    colour = mix( lin( ( 72, 40, 24 ) ), lin( ( 150, 72, 32 ) ), a[..., None] )
    colour *= ( 1.0 + 0.15 * nz( 0.9, 1, 0.1 ) )[..., None]
    scale = smoothstep( 1.4, 2.4, nz( 1.6, 4, 0.3 ) )
    colour = mix( colour, lin( ( 40, 26, 18 ) ), scale[..., None] * 0.6 )
    height = 0.1 * nz( 1.4, 3, 0.2 ) + 0.2 * scale
    rough = 0.82 + 0.1 * scale
    return colour, np.clip( rough, 0.1, 1 ), height, ppi


def chainlink( seed=231, n=None ):
    """ 2 in diamond chain-link of 11 gauge galvanised wire: alpha tested, a little dulled and rusted at the knuckles. """
    n = n or px( 512 )
    tile = TILES["rs_chainlink"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    p = 2.0 * math.sqrt( 2 )
    u, v = ( x + z ) / p, ( x - z ) / p
    du = np.abs( ( u % 1.0 ) - 0.5 )
    dv = np.abs( ( v % 1.0 ) - 0.5 )
    wire_r = 0.06 / p
    wires = np.maximum( smoothstep( 0.5 - wire_r * 2.2, 0.5 - wire_r * 0.6, du ), smoothstep( 0.5 - wire_r * 2.2, 0.5 - wire_r * 0.6, dv ) )
    colour = lin( ( 150, 152, 150 ) )[None, None, :] * ( 1.0 + 0.1 * nz( 1.6, 4, 0.4 ) )[..., None]
    knuckle = np.clip( ( 1 - du * 4 ) * ( 1 - dv * 4 ), 0, 1 )
    colour = mix( colour, BM.RUST, ( smoothstep( 0.6, 2.0, nz( 1.8, 8, 1 ) ) * 0.6 + knuckle * 0.2 )[..., None] )
    height = 0.05 * wires
    rough = 0.45 + 0.2 * nz( 1.6, 6, 1 ) * 0.2
    return colour, np.clip( rough, 0.1, 1 ) * np.ones( ( n, n ), np.float32 ), height, ppi, wires


def sandbag( seed=241, n=None ):
    n = n or px( 512 )
    tile = TILES["rs_sandbag"]
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = field( rng, n, tile )
    weave = ( np.sin( x * 2 * math.pi / 0.18 ) * np.sin( z * 2 * math.pi / 0.18 ) ) * 0.5
    colour = lin( ( 132, 118, 88 ) )[None, None, :] * ( 1.0 + 0.06 * weave + 0.1 * nz( 2.2, 12, 1 ) )[..., None]
    dirt = smoothstep( 0.0, 1.8, nz( 2.0, 16, 2 ) )
    colour = mix( colour, lin( ( 74, 62, 46 ) ), dirt[..., None] * 0.6 )
    height = 0.03 * weave + 0.3 * nz( 2.0, 8, 1 )
    return colour, np.full( ( n, n ), 0.88, np.float32 ), height, ppi


# ---------------------------------------------------------------------------------------------------------------------
# Strokes: a hand-drawn capital alphabet for spray paint and brush lettering, and the neon script

def _arc( cx, cy, rx, ry, a0, a1, steps=10 ):
    return [ ( cx + rx * math.cos( math.radians( a0 + ( a1 - a0 ) * k / steps ) ),
               cy + ry * math.sin( math.radians( a0 + ( a1 - a0 ) * k / steps ) ) ) for k in range( steps + 1 ) ]


def _cat( *parts ):
    out = []
    for p in parts:
        out += list( p )
    return out


# Each letter: ( width, [ strokes ] ), a stroke a polyline in a box 1 high (y up from the baseline).
STROKES = {
    "A": ( 0.72, [ [ ( 0, 0 ), ( 0.36, 1 ), ( 0.72, 0 ) ], [ ( 0.14, 0.38 ), ( 0.58, 0.38 ) ] ] ),
    "B": ( 0.66, [ _cat( [ ( 0, 0 ), ( 0, 1 ), ( 0.34, 1 ) ], _arc( 0.34, 0.765, 0.22, 0.235, 90, -90, 8 ), [ ( 0, 0.53 ) ] ),
                   _cat( [ ( 0.36, 0.53 ) ], _arc( 0.38, 0.265, 0.27, 0.265, 90, -90, 8 ), [ ( 0, 0 ) ] ) ] ),
    "C": ( 0.66, [ _arc( 0.38, 0.5, 0.38, 0.5, 45, 315, 14 ) ] ),
    "D": ( 0.68, [ _cat( [ ( 0, 0 ), ( 0, 1 ), ( 0.28, 1 ) ], _arc( 0.28, 0.5, 0.38, 0.5, 90, -90, 12 ), [ ( 0, 0 ) ] ) ] ),
    "E": ( 0.56, [ [ ( 0.55, 1 ), ( 0, 1 ), ( 0, 0 ), ( 0.56, 0 ) ], [ ( 0, 0.52 ), ( 0.44, 0.52 ) ] ] ),
    "F": ( 0.54, [ [ ( 0.55, 1 ), ( 0, 1 ), ( 0, 0 ) ], [ ( 0, 0.52 ), ( 0.44, 0.52 ) ] ] ),
    "G": ( 0.74, [ _cat( _arc( 0.38, 0.5, 0.38, 0.5, 45, 330, 14 ), [ ( 0.74, 0.44 ), ( 0.44, 0.44 ) ] ) ] ),
    "H": ( 0.62, [ [ ( 0, 0 ), ( 0, 1 ) ], [ ( 0.62, 0 ), ( 0.62, 1 ) ], [ ( 0, 0.52 ), ( 0.62, 0.52 ) ] ] ),
    "I": ( 0.10, [ [ ( 0.05, 0 ), ( 0.05, 1 ) ] ] ),
    "J": ( 0.48, [ _cat( [ ( 0.46, 1 ), ( 0.46, 0.28 ) ], _arc( 0.23, 0.28, 0.23, 0.28, 0, -170, 8 ) ) ] ),
    "K": ( 0.62, [ [ ( 0, 0 ), ( 0, 1 ) ], [ ( 0.58, 1 ), ( 0, 0.4 ) ], [ ( 0.2, 0.6 ), ( 0.62, 0 ) ] ] ),
    "L": ( 0.5, [ [ ( 0, 1 ), ( 0, 0 ), ( 0.5, 0 ) ] ] ),
    "M": ( 0.8, [ [ ( 0, 0 ), ( 0.02, 1 ), ( 0.4, 0.28 ), ( 0.78, 1 ), ( 0.8, 0 ) ] ] ),
    "N": ( 0.64, [ [ ( 0, 0 ), ( 0, 1 ), ( 0.64, 0 ), ( 0.64, 1 ) ] ] ),
    "O": ( 0.78, [ _arc( 0.39, 0.5, 0.39, 0.5, 90, 452, 20 ) ] ),
    "P": ( 0.6, [ _cat( [ ( 0, 0 ), ( 0, 1 ), ( 0.32, 1 ) ], _arc( 0.32, 0.745, 0.26, 0.255, 90, -90, 8 ), [ ( 0, 0.49 ) ] ) ] ),
    "Q": ( 0.8, [ _arc( 0.39, 0.5, 0.39, 0.5, 90, 452, 20 ), [ ( 0.48, 0.24 ), ( 0.82, -0.06 ) ] ] ),
    "R": ( 0.62, [ _cat( [ ( 0, 0 ), ( 0, 1 ), ( 0.32, 1 ) ], _arc( 0.32, 0.745, 0.26, 0.255, 90, -90, 8 ), [ ( 0, 0.49 ) ] ),
                   [ ( 0.28, 0.49 ), ( 0.62, 0 ) ] ] ),
    "S": ( 0.6, [ _cat( _arc( 0.3, 0.75, 0.29, 0.25, 15, 270, 10 ), _arc( 0.3, 0.25, 0.3, 0.25, 90, -165, 10 ) ) ] ),
    "T": ( 0.64, [ [ ( 0, 1 ), ( 0.64, 1 ) ], [ ( 0.32, 1 ), ( 0.32, 0 ) ] ] ),
    "U": ( 0.62, [ _cat( [ ( 0, 1 ), ( 0, 0.32 ) ], _arc( 0.31, 0.32, 0.31, 0.32, 180, 360, 10 ), [ ( 0.62, 1 ) ] ) ] ),
    "V": ( 0.68, [ [ ( 0, 1 ), ( 0.34, 0 ), ( 0.68, 1 ) ] ] ),
    "W": ( 0.92, [ [ ( 0, 1 ), ( 0.22, 0 ), ( 0.46, 0.72 ), ( 0.7, 0 ), ( 0.92, 1 ) ] ] ),
    "X": ( 0.62, [ [ ( 0, 1 ), ( 0.62, 0 ) ], [ ( 0.62, 1 ), ( 0, 0 ) ] ] ),
    "Y": ( 0.64, [ [ ( 0, 1 ), ( 0.32, 0.5 ), ( 0.64, 1 ) ], [ ( 0.32, 0.5 ), ( 0.32, 0 ) ] ] ),
    "Z": ( 0.6, [ [ ( 0, 1 ), ( 0.6, 1 ), ( 0, 0 ), ( 0.6, 0 ) ] ] ),
    "?": ( 0.56, [ _cat( _arc( 0.28, 0.73, 0.28, 0.27, 165, -70, 10 ), [ ( 0.28, 0.3 ) ] ), [ ( 0.28, 0.06 ), ( 0.28, 0.0 ) ] ] ),
    "!": ( 0.12, [ [ ( 0.06, 1 ), ( 0.06, 0.28 ) ], [ ( 0.06, 0.06 ), ( 0.06, 0.0 ) ] ] ),
    "1": ( 0.36, [ [ ( 0.04, 0.8 ), ( 0.28, 1 ), ( 0.28, 0 ) ] ] ),
    "7": ( 0.56, [ [ ( 0, 1 ), ( 0.56, 1 ), ( 0.18, 0 ) ] ] ),
    "↙": ( 0.9, [ [ ( 0.9, 0.95 ), ( 0.08, 0.13 ) ], [ ( 0.06, 0.6 ), ( 0.06, 0.1 ), ( 0.56, 0.1 ) ] ] ),
    "-": ( 0.4, [ [ ( 0.02, 0.5 ), ( 0.38, 0.5 ) ] ] ),
    " ": ( 0.42, [] ),
}


def stroke_lines( text, rng, jitter=0.03, slant=0.0, wobble=0.04, spacing=0.22 ):
    """ The strokes of a line of capitals, hand-drawn: each letter a little off size, height and angle, each point
    nudged. Returns ( strokes in em units, width ). """
    out, x = [], 0.0
    for ch in text:
        w, strokes = STROKES.get( ch, STROKES[" "] )
        sc = 1.0 + rng.normal( 0, wobble )
        dy = rng.normal( 0, wobble * 0.6 )
        rot = rng.normal( 0, wobble * 0.6 )
        for s in strokes:
            pts = []
            for px_, py_ in s:
                qx = px_ * sc + rng.normal( 0, jitter ) * 0.6
                qy = py_ * sc + dy + rng.normal( 0, jitter ) * 0.6
                qx, qy = qx * math.cos( rot ) - ( qy - 0.5 ) * math.sin( rot ), qx * math.sin( rot ) + ( qy - 0.5 ) * math.cos( rot ) + 0.5
                pts.append( ( x + qx + slant * qy, qy ) )
            out.append( pts )
        x += w * sc + spacing
    return out, max( x - spacing, 0.1 )


def draw_paint( size, box, lines, rng, kind="spray", thickness=0.13, drips=0.5, align="left", jitter=0.03, slant=0.0,
                line_gap=0.32, pad=0.06 ):
    """ Hand lettering into box ( x, y, w, h ) of a picture size ( W, H ): spray paint (soft edges, overspray, drips) or
    brush (firm, dry-brushed edges). Returns the coverage 0..1 as a float picture. """
    W, H = size
    x, y, w, h = box
    sets = [ stroke_lines( ln, rng, jitter=jitter, slant=slant ) for ln in lines ]
    widest = max( wd for _, wd in sets )
    rows = len( lines )
    em = min( ( h * ( 1 - 2 * pad ) ) / ( rows + line_gap * ( rows - 1 ) ), ( w * ( 1 - 2 * pad ) ) / widest )
    ss = 2
    img = Image.new( "L", ( W * ss, H * ss ), 0 )
    d = ImageDraw.Draw( img )
    stroke_w = max( 2, int( em * thickness * ss ) )
    total_h = em * ( rows + line_gap * ( rows - 1 ) )
    top = y + ( h - total_h ) / 2
    ends = []
    for r, ( strokes, wd ) in enumerate( sets ):
        if align == "left":
            ox = x + w * pad
        elif align == "right":
            ox = x + w * ( 1 - pad ) - wd * em
        else:
            ox = x + ( w - wd * em ) / 2
        base = top + em * ( r + 1 ) + em * line_gap * r
        for s in strokes:
            pts = [ ( ( ox + px_ * em ) * ss, ( base - py_ * em ) * ss ) for px_, py_ in s ]
            if len( pts ) == 1:
                pts = pts + [ ( pts[0][0] + 1, pts[0][1] ) ]
            d.line( pts, fill=255, width=stroke_w, joint="curve" )
            for p in pts[:1] + pts[-1:]:
                d.ellipse( ( p[0] - stroke_w / 2, p[1] - stroke_w / 2, p[0] + stroke_w / 2, p[1] + stroke_w / 2 ), fill=255 )
            ends += pts
    a = np.asarray( img.resize( ( W, H ), Image.LANCZOS ), np.float32 ) / 255.0
    sw = stroke_w / ss
    if kind == "spray":
        soft = ndimage.gaussian_filter( a, sw * 0.18 )
        halo = ndimage.gaussian_filter( a, sw * 0.9 )
        speck = ( rng.random( a.shape ) < 0.06 ).astype( np.float32 ) * smoothstep( 0.02, 0.25, halo )
        a = np.clip( np.maximum( smoothstep( 0.25, 0.6, soft ), speck * 0.8 ), 0, 1 )
        # Drips: paint runs down from where it pooled.
        if drips > 0:
            dm = Image.new( "L", ( W, H ), 0 )
            dd = ImageDraw.Draw( dm )
            for p in ends:
                if rng.random() < drips * 0.12:
                    px_, py_ = p[0] / ss, p[1] / ss
                    L = rng.uniform( 0.2, 1.2 ) * em
                    wd = max( 1.0, sw * rng.uniform( 0.25, 0.45 ) )
                    dd.line( [ ( px_, py_ ), ( px_ + rng.normal( 0, 0.5 ), py_ + L ) ], fill=255, width=int( wd ) )
                    dd.ellipse( ( px_ - wd * 0.7, py_ + L - wd * 0.7, px_ + wd * 0.7, py_ + L + wd * 0.7 ), fill=255 )
            a = np.maximum( a, np.asarray( dm, np.float32 ) / 255.0 )
    else:
        dry = ndimage.gaussian_filter( rng.random( a.shape ).astype( np.float32 ), 0.8 )
        streaks = ndimage.gaussian_filter( rng.standard_normal( a.shape ).astype( np.float32 ), ( 0.5, sw * 1.5 ) )
        a = np.clip( smoothstep( 0.35, 0.65, ndimage.gaussian_filter( a, 0.6 ) ) * ( 0.85 + 0.6 * streaks ) - 0.2 * ( dry < 0.3 ), 0, 1 )
    return a


def _catmull( points, steps=8 ):
    pts = [ np.array( points[0] ) ] + [ np.array( p ) for p in points ] + [ np.array( points[-1] ) ]
    out = []
    for k in range( 1, len( pts ) - 2 ):
        p0, p1, p2, p3 = pts[k - 1], pts[k], pts[k + 1], pts[k + 2]
        for s in range( steps ):
            t = s / steps
            out.append( 0.5 * ( 2 * p1 + ( -p0 + p2 ) * t + ( 2 * p0 - 5 * p1 + 4 * p2 - p3 ) * t * t + ( -p0 + 3 * p1 - 3 * p2 + p3 ) * t ** 3 ) )
    out.append( np.array( points[-1] ) )
    return [ tuple( p ) for p in out ]


# The neon script "Riverside": one tube from the R's foot to the last e's tail, as a sign bender bends it, plus the
# i's dots. Control points in a box where the x-height is 0.5 and the capital 1.0 (y up from the baseline).
SCRIPT = [
    # R: the stem up, the bowl, the leg kicking out into the i's entry stroke.
    [ ( 0.02, 0.02 ), ( 0.12, 0.5 ), ( 0.2, 0.98 ), ( 0.42, 1.04 ), ( 0.6, 0.92 ), ( 0.56, 0.72 ), ( 0.36, 0.6 ), ( 0.22, 0.58 ),
      ( 0.38, 0.5 ), ( 0.5, 0.22 ), ( 0.58, 0.04 ), ( 0.7, 0.02 ),
      # i
      ( 0.8, 0.3 ), ( 0.86, 0.5 ), ( 0.84, 0.2 ), ( 0.88, 0.03 ), ( 0.98, 0.06 ),
      # v
      ( 1.06, 0.36 ), ( 1.08, 0.5 ), ( 1.14, 0.2 ), ( 1.2, 0.02 ), ( 1.3, 0.3 ), ( 1.36, 0.5 ), ( 1.38, 0.4 ), ( 1.46, 0.36 ),
      # e
      ( 1.62, 0.3 ), ( 1.66, 0.44 ), ( 1.58, 0.5 ), ( 1.48, 0.36 ), ( 1.5, 0.1 ), ( 1.6, 0.0 ), ( 1.72, 0.06 ),
      # r
      ( 1.8, 0.36 ), ( 1.84, 0.5 ), ( 1.9, 0.42 ), ( 1.98, 0.5 ), ( 1.96, 0.26 ), ( 1.98, 0.04 ), ( 2.08, 0.04 ),
      # s
      ( 2.2, 0.36 ), ( 2.26, 0.52 ), ( 2.34, 0.3 ), ( 2.32, 0.08 ), ( 2.2, 0.02 ), ( 2.12, 0.08 ), ( 2.3, 0.0 ), ( 2.42, 0.04 ),
      # i
      ( 2.5, 0.3 ), ( 2.56, 0.5 ), ( 2.54, 0.2 ), ( 2.58, 0.03 ), ( 2.68, 0.06 ) ],
    # d: from its bowl's top round anticlockwise, closing on its stem, up the ascender and back down the same line.
    [ ( 2.95, 0.42 ), ( 2.86, 0.52 ), ( 2.74, 0.45 ), ( 2.7, 0.22 ), ( 2.77, 0.02 ), ( 2.9, 0.05 ), ( 2.955, 0.3 ), ( 2.97, 0.7 ),
      ( 2.985, 1.04 ), ( 2.98, 0.7 ), ( 2.97, 0.3 ), ( 2.975, 0.06 ), ( 3.06, 0.03 ),
      # e, and its tail swept up and back under the word
      ( 3.28, 0.3 ), ( 3.32, 0.44 ), ( 3.24, 0.5 ), ( 3.14, 0.36 ), ( 3.16, 0.1 ), ( 3.28, 0.0 ), ( 3.44, 0.06 ), ( 3.58, 0.2 ) ],
]
SCRIPT_DOTS = [ ( 0.88, 0.68 ), ( 2.58, 0.68 ) ]
SCRIPT_WIDTH = 3.6


def draw_neon( size, box, colour, tube=0.05, glow=0.16, rng=None ):
    """ The script in box of a picture size: ( colour picture, illum mask ), a tube with a hot white core, its coloured
    skin and a glow round it. """
    W, H = size
    x, y, w, h = box
    em = min( h * 0.8 / 1.1, w * 0.92 / SCRIPT_WIDTH )
    ox = x + ( w - SCRIPT_WIDTH * em ) / 2
    base = y + h * 0.5 + em * 0.52
    ss = 2
    img = Image.new( "L", ( W * ss, H * ss ), 0 )
    d = ImageDraw.Draw( img )
    tw = max( 2, int( em * tube * ss ) )
    for stroke in SCRIPT:
        pts = [ ( ( ox + px_ * em ) * ss, ( base - py_ * em ) * ss ) for px_, py_ in _catmull( stroke, 6 ) ]
        d.line( pts, fill=255, width=tw, joint="curve" )
    for px_, py_ in SCRIPT_DOTS:
        cx, cy = ( ox + px_ * em ) * ss, ( base - py_ * em ) * ss
        d.ellipse( ( cx - tw, cy - tw, cx + tw, cy + tw ), fill=255 )
    core = np.asarray( img.resize( ( W, H ), Image.LANCZOS ), np.float32 ) / 255.0
    halo = ndimage.gaussian_filter( core, em * glow * 0.35 )
    halo /= halo.max() + 1e-6
    skin = np.clip( core * 1.2, 0, 1 )
    white = smoothstep( 0.6, 1.0, ndimage.gaussian_filter( core, 0.6 ) )
    c = np.asarray( colour, np.float32 )
    rgb = skin[..., None] * c[None, None, :] + white[..., None] * ( 1 - c[None, None, :] ) * 0.6 + halo[..., None] * c[None, None, :] * 0.5
    illum = np.clip( skin + halo * 0.5, 0, 1 )
    return np.clip( rgb, 0, 1 ), illum


# ---------------------------------------------------------------------------------------------------------------------
# Lit signs (rs_lit): opaque, self-lit by their illum mask's brightness

LIT_ATLAS = ( 4096, 4096 )
LIT = {
    "park_sign": ( 0, 0, 2048, 1152 ),            # the roadside sign's top board: neon script and bulb letters
    "marquee": ( 2048, 0, 2048, 640 ),            # GOOD TIMES / BIGGER TOMORROW
    "lucky_stop": ( 2048, 640, 2048, 512 ),       # the store's sign board
    "no_place": ( 0, 1152, 896, 1024 ),           # NO PLACE BETTER, red neon in a dark box
    "open": ( 896, 1152, 640, 320 ),              # OPEN, in the store's window
    "beer": ( 896, 1472, 640, 320 ),              # a beer sign in the window: COLD BEER
    "window": ( 1536, 1152, 1024, 768 ),          # the store's window: shelves of goods lit from inside
    "fridge": ( 2560, 1152, 768, 1024 ),          # a drinks fridge's glass door
    "vending": ( 3328, 1152, 768, 1024 ),         # an ice machine's front: ICE
    "trailer_window": ( 0, 2176, 1024, 768 ),     # a lit trailer window: curtains, a lamp's glow
    "trailer_window_b": ( 1024, 2176, 1024, 768 ),
    "trailer_window_tv": ( 2048, 2176, 1024, 768 ),  # a TV's blue flicker behind blinds
    "office": ( 3072, 2176, 1024, 384 ),          # OFFICE over the park office's door, a lit box
    "bulbs": ( 3072, 2560, 1024, 384 ),           # a strip of warm bulbs
}


def _font( path, size ):
    return ImageFont.truetype( str( path ), max( 6, int( size ) ) )


def _fit_text( d, box, text, path, fill, pad=0.08, track=0.04, align="center", valign=0.5 ):
    x, y, w, h = box
    size = h * ( 1 - 2 * pad ) / 0.72
    for _ in range( 60 ):
        f = _font( path, size )
        tw = sum( f.getlength( ch ) for ch in text ) + track * size * ( len( text ) - 1 )
        if tw <= w * ( 1 - 2 * pad ):
            break
        size *= 0.96
    cap = 0.72 * size
    cx = x + ( w - tw ) / 2 if align == "center" else x + w * pad if align == "left" else x + w * ( 1 - pad ) - tw
    cy = y + ( h - cap ) * valign - 0.26 * size
    for ch in text:
        d.text( ( cx, cy ), ch, font=f, fill=fill )
        cx += f.getlength( ch ) + track * size
    return size


def lit_atlas():
    """ ( colour 0..255, illum 0..1 ) """
    W, H = px( LIT_ATLAS[0] ), px( LIT_ATLAS[1] )
    k = W / LIT_ATLAS[0]
    rng = np.random.default_rng( 7 )
    colour = np.zeros( ( H, W, 3 ), np.float32 )
    illum = np.zeros( ( H, W ), np.float32 )

    def box( name ):
        x, y, w, h = LIT[name]
        return ( int( x * k ), int( y * k ), int( w * k ), int( h * k ) )

    def region( name ):
        x, y, w, h = box( name )
        return slice( y, y + h ), slice( x, x + w ), ( w, h )

    # The park sign's board: painted steel gone dark maroon-brown, a raised frame, rust runs; the script in red neon,
    # TRAILER PARK in warm bulbs (each a lit dot in the letters' shape, a few dead).
    ys, xs, ( w, h ) = region( "park_sign" )
    sub_rng = np.random.default_rng( 11 )
    nz = BM.noise( sub_rng, ( h, w ), ( w / 120.0, w / 120.0 ), 2.2, 40, 0.5 )
    board = lin( ( 46, 30, 28 ) )[None, None, :] * ( 1.0 + 0.15 * nz )[..., None]
    frame = np.zeros( ( h, w ), np.float32 )
    fw = int( w * 0.02 )
    frame[:fw, :] = frame[-fw:, :] = 1
    frame[:, :fw] = frame[:, -fw:] = 1
    board = mix( board, lin( ( 110, 96, 84 ) ), frame[..., None] * 0.6 )
    runs = np.clip( runs_down( ( sub_rng.random( ( h, w ) ) < 0.0006 ).astype( np.float32 ), w / 120.0, 20, wrap=False ) * 20, 0, 1 )
    board = mix( board, BM.RUST, runs[..., None] * 0.5 )
    sign = T.linear_to_srgb( board ) / 255.0
    neon_rgb, neon_il = draw_neon( ( w, h ), ( 0.06 * w, 0.02 * h, 0.88 * w, 0.5 * h ), ( 1.0, 0.16, 0.12 ) )
    sign = sign * ( 1 - neon_il[..., None] ) + neon_rgb * neon_il[..., None] + neon_rgb * ( 1 - neon_il[..., None] ) * 0.0
    il = neon_il * 0.95
    mask = Image.new( "L", ( w, h ), 0 )
    _fit_text( ImageDraw.Draw( mask ), ( 0.05 * w, 0.52 * h, 0.9 * w, 0.42 * h ), "TRAILER PARK", FONT, 255, pad=0.06, track=0.06 )
    m = np.asarray( mask, np.float32 ) / 255.0
    bulb_d = max( 4, int( h * 0.028 ) )
    bulbs = np.zeros( ( h, w ), np.float32 )
    yy, xx = np.mgrid[0:h, 0:w]
    for cy in range( int( 0.52 * h ), int( 0.96 * h ), int( bulb_d * 1.5 ) ):
        for cx in range( int( 0.04 * w ), int( 0.96 * w ), int( bulb_d * 1.5 ) ):
            if m[min( cy, h - 1 ), min( cx, w - 1 )] < 0.5:
                continue
            dead = sub_rng.random() < 0.05
            r2 = ( ( xx[cy - bulb_d:cy + bulb_d, cx - bulb_d:cx + bulb_d] - cx ) ** 2 + ( yy[cy - bulb_d:cy + bulb_d, cx - bulb_d:cx + bulb_d] - cy ) ** 2 )
            spot = np.exp( -r2 / ( bulb_d * 0.45 ) ** 2 ) * ( 0.15 if dead else 1.0 )
            bulbs[cy - bulb_d:cy + bulb_d, cx - bulb_d:cx + bulb_d] = np.maximum( bulbs[cy - bulb_d:cy + bulb_d, cx - bulb_d:cx + bulb_d], spot )
    letters_face = np.clip( m * 0.85, 0, 1 )
    glow = ndimage.gaussian_filter( bulbs, bulb_d * 1.2 )
    glow /= glow.max() + 1e-6
    warm = np.array( ( 1.0, 0.82, 0.5 ), np.float32 )
    sign = sign * ( 1 - letters_face[..., None] ) + letters_face[..., None] * np.array( ( 0.98, 0.9, 0.72 ) )
    sign = np.clip( sign + bulbs[..., None] * warm + glow[..., None] * warm * 0.35, 0, 1 )
    il = np.maximum( il, np.clip( bulbs + glow * 0.3 + letters_face * 0.45, 0, 1 ) * 0.9 )
    colour[ys, xs] = sign * 255
    illum[ys, xs] = il

    # The marquee: a backlit white panel with black changeable letters, grimy, a crack.
    ys, xs, ( w, h ) = region( "marquee" )
    panel = Image.new( "RGB", ( w, h ), ( 236, 232, 218 ) )
    d = ImageDraw.Draw( panel )
    d.rectangle( ( 0, 0, w - 1, h - 1 ), outline=( 40, 36, 34 ), width=int( h * 0.06 ) )
    _fit_text( d, ( 0.06 * w, 0.1 * h, 0.88 * w, 0.38 * h ), "GOOD TIMES", FONT, ( 22, 20, 20 ), pad=0.06, track=0.08 )
    _fit_text( d, ( 0.06 * w, 0.52 * h, 0.88 * w, 0.38 * h ), "BIGGER TOMORROW", FONT, ( 22, 20, 20 ), pad=0.06, track=0.08 )
    a = np.asarray( panel, np.float32 ) / 255.0
    sub_rng = np.random.default_rng( 12 )
    grime = smoothstep( -0.5, 1.5, BM.noise( sub_rng, ( h, w ), ( w / 100.0, w / 100.0 ), 2.0, 30, 0.5 ) )
    a = a * ( 1 - 0.35 * grime[..., None] )
    lum = a.mean( axis=-1 )
    colour[ys, xs] = a * 255
    illum[ys, xs] = smoothstep( 0.4, 0.9, lum ) * 0.32

    # The Lucky Stop's board: cream, backlit, red letters with a dark edge, the slogan under it in dark red.
    ys, xs, ( w, h ) = region( "lucky_stop" )
    panel = Image.new( "RGB", ( w, h ), ( 238, 226, 196 ) )
    d = ImageDraw.Draw( panel )
    d.rectangle( ( 0, 0, w - 1, h - 1 ), outline=( 120, 30, 24 ), width=int( h * 0.05 ) )
    big = Image.new( "L", ( w, h ), 0 )
    _fit_text( ImageDraw.Draw( big ), ( 0.05 * w, 0.06 * h, 0.9 * w, 0.62 * h ), "LUCKY STOP", FONT, 255, pad=0.04, track=0.05 )
    bm = np.asarray( big, np.float32 ) / 255.0
    edge = np.clip( ndimage.grey_dilation( bm, size=( 9, 9 ) ) - bm, 0, 1 )
    _fit_text( d, ( 0.06 * w, 0.7 * h, 0.88 * w, 0.24 * h ), "BEER • SNACKS • FUEL • SURVIVAL", FONT, ( 150, 28, 22 ), pad=0.04, track=0.06 )
    a = np.asarray( panel, np.float32 ) / 255.0
    a = mix( a, np.array( ( 0.78, 0.1, 0.08 ), np.float32 ), bm )
    a = mix( a, np.array( ( 0.2, 0.06, 0.05 ), np.float32 ), edge * 0.8 )
    sub_rng = np.random.default_rng( 13 )
    grime = smoothstep( -0.2, 1.8, BM.noise( sub_rng, ( h, w ), ( w / 100.0, w / 100.0 ), 2.0, 30, 0.5 ) )
    a = a * ( 1 - 0.3 * grime[..., None] )
    colour[ys, xs] = a * 255
    illum[ys, xs] = 0.1 + 0.2 * bm

    # NO PLACE BETTER: red tube capitals in a black box.
    ys, xs, ( w, h ) = region( "no_place" )
    base = np.full( ( h, w, 3 ), 0.03, np.float32 )
    cov = draw_paint( ( w, h ), ( 0.08 * w, 0.08 * h, 0.84 * w, 0.84 * h ), [ "NO", "PLACE", "BETTER" ], np.random.default_rng( 14 ),
                      kind="brush", thickness=0.09, drips=0, align="center", jitter=0.004, line_gap=0.38 )
    tube = smoothstep( 0.3, 0.7, cov )
    halo = ndimage.gaussian_filter( tube, w * 0.012 )
    halo /= halo.max() + 1e-6
    red = np.array( ( 1.0, 0.14, 0.1 ), np.float32 )
    rgb = base + tube[..., None] * ( red + 0.25 ) + halo[..., None] * red * 0.45
    colour[ys, xs] = np.clip( rgb, 0, 1 ) * 255
    illum[ys, xs] = np.clip( tube + halo * 0.6, 0, 1 )

    # OPEN and COLD BEER: tube signs in the window.
    for name, words, col in ( ( "open", [ "OPEN" ], ( 1.0, 0.3, 0.12 ) ), ( "beer", [ "COLD BEER" ], ( 0.25, 0.6, 1.0 ) ) ):
        ys, xs, ( w, h ) = region( name )
        cov = draw_paint( ( w, h ), ( 0.08 * w, 0.15 * h, 0.84 * w, 0.7 * h ), words, np.random.default_rng( len( name ) ),
                          kind="brush", thickness=0.1, drips=0, align="center", jitter=0.003 )
        tube = smoothstep( 0.3, 0.7, cov )
        halo = ndimage.gaussian_filter( tube, w * 0.02 )
        halo /= halo.max() + 1e-6
        c = np.array( col, np.float32 )
        colour[ys, xs] = np.clip( 0.02 + tube[..., None] * ( c + 0.3 ) + halo[..., None] * c * 0.5, 0, 1 ) * 255
        illum[ys, xs] = np.clip( tube + halo * 0.7, 0, 1 )

    # The store's window: shelves of tins, boxes and bottles under fluorescent light, a hand-written sign taped on.
    ys, xs, ( w, h ) = region( "window" )
    sub = np.random.default_rng( 21 )
    img = Image.new( "RGB", ( w, h ), ( 196, 204, 190 ) )
    d = ImageDraw.Draw( img )
    for row in range( 4 ):
        sy = int( h * ( 0.12 + 0.22 * row ) )
        d.rectangle( ( 0, sy + int( h * 0.16 ), w, sy + int( h * 0.18 ) ), fill=( 90, 90, 86 ) )
        cx = int( sub.uniform( 0, 20 ) )
        while cx < w:
            gw = int( sub.uniform( 0.025, 0.07 ) * w )
            gh = int( sub.uniform( 0.06, 0.15 ) * h )
            col = tuple( int( c ) for c in sub.choice( [ ( 200, 40, 30 ), ( 230, 200, 60 ), ( 40, 90, 160 ), ( 240, 240, 230 ),
                                                          ( 60, 140, 70 ), ( 150, 80, 40 ), ( 30, 30, 30 ) ] ) )
            d.rectangle( ( cx, sy + int( h * 0.16 ) - gh, cx + gw, sy + int( h * 0.16 ) ), fill=col )
            d.rectangle( ( cx + 2, sy + int( h * 0.16 ) - gh + int( gh * 0.3 ), cx + gw - 2, sy + int( h * 0.16 ) - gh + int( gh * 0.5 ) ),
                         fill=( 245, 240, 228 ) )
            cx += gw + int( sub.uniform( 1, 6 ) )
    a = np.asarray( img, np.float32 ) / 255.0
    paper = Image.new( "L", ( w, h ), 0 )
    pd = ImageDraw.Draw( paper )
    pd.rectangle( ( int( 0.62 * w ), int( 0.06 * h ), int( 0.92 * w ), int( 0.36 * h ) ), fill=255 )
    pm = np.asarray( paper, np.float32 ) / 255.0
    ink = draw_paint( ( w, h ), ( int( 0.63 * w ), int( 0.08 * h ), int( 0.28 * w ), int( 0.26 * h ) ), [ "CASH", "ONLY" ],
                      np.random.default_rng( 22 ), kind="brush", thickness=0.12, drips=0, align="center", jitter=0.03 )
    a = mix( a, np.array( ( 0.95, 0.94, 0.88 ), np.float32 ), pm )
    a = mix( a, np.array( ( 0.08, 0.08, 0.1 ), np.float32 ), ink * pm )
    vign = 1.0 - 0.45 * ( ( np.mgrid[0:h, 0:w][0] / h - 0.4 ) ** 2 * 2 )
    a *= vign[..., None]
    colour[ys, xs] = np.clip( a, 0, 1 ) * 255
    illum[ys, xs] = 0.75 * np.clip( a.mean( axis=-1 ) * 1.2, 0, 1 )

    # A drinks fridge: glass door, cans and bottles in rows, bright.
    ys, xs, ( w, h ) = region( "fridge" )
    img = Image.new( "RGB", ( w, h ), ( 220, 232, 240 ) )
    d = ImageDraw.Draw( img )
    sub = np.random.default_rng( 23 )
    d.rectangle( ( 0, 0, w - 1, h - 1 ), outline=( 30, 30, 32 ), width=int( w * 0.05 ) )
    for row in range( 5 ):
        sy = int( h * ( 0.08 + 0.18 * row ) )
        d.rectangle( ( int( w * 0.05 ), sy + int( h * 0.15 ), int( w * 0.95 ), sy + int( h * 0.16 ) ), fill=( 120, 124, 128 ) )
        for col in range( 7 ):
            cx = int( w * ( 0.08 + col * 0.125 ) )
            c = tuple( int( v ) for v in sub.choice( [ ( 200, 30, 30 ), ( 30, 80, 180 ), ( 220, 200, 40 ), ( 230, 230, 230 ), ( 60, 150, 60 ) ] ) )
            d.rounded_rectangle( ( cx, sy + int( h * 0.03 ), cx + int( w * 0.09 ), sy + int( h * 0.15 ) ), radius=int( w * 0.02 ), fill=c )
    a = np.asarray( img, np.float32 ) / 255.0
    colour[ys, xs] = a * 255
    illum[ys, xs] = 0.85 * np.clip( a.mean( axis=-1 ), 0, 1 )

    # An ice machine's front.
    ys, xs, ( w, h ) = region( "vending" )
    img = Image.new( "RGB", ( w, h ), ( 224, 230, 236 ) )
    d = ImageDraw.Draw( img )
    d.rectangle( ( int( w * 0.08 ), int( h * 0.06 ), int( w * 0.92 ), int( h * 0.4 ) ), fill=( 30, 110, 190 ) )
    _fit_text( d, ( int( w * 0.1 ), int( h * 0.08 ), int( w * 0.8 ), int( h * 0.3 ) ), "ICE", FONT, ( 250, 250, 250 ), pad=0.1, track=0.1 )
    d.rectangle( ( int( w * 0.15 ), int( h * 0.5 ), int( w * 0.85 ), int( h * 0.9 ) ), outline=( 90, 96, 100 ), width=int( w * 0.03 ) )
    a = np.asarray( img, np.float32 ) / 255.0
    colour[ys, xs] = a * 255
    illum[ys, xs] = 0.5 * np.clip( a.mean( axis=-1 ), 0, 1 )

    # Lit trailer windows: curtains drawn, a lamp's warm glow; another with a blind half down; a TV's blue light.
    for name, tone in ( ( "trailer_window", "curtain" ), ( "trailer_window_b", "blind" ), ( "trailer_window_tv", "tv" ) ):
        ys, xs, ( w, h ) = region( name )
        yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
        u, v = xx / w, yy / h
        lamp = np.exp( -( ( u - 0.35 ) ** 2 / 0.18 + ( v - 0.55 ) ** 2 / 0.25 ) )
        if tone == "tv":
            base_c = np.array( ( 0.22, 0.36, 0.62 ), np.float32 )
            glow = 0.35 + 0.65 * np.exp( -( ( u - 0.6 ) ** 2 / 0.1 + ( v - 0.6 ) ** 2 / 0.2 ) )
        else:
            base_c = np.array( ( 1.0, 0.72, 0.42 ), np.float32 )
            glow = 0.35 + 0.65 * lamp
        rgb = base_c[None, None, :] * glow[..., None]
        if tone == "curtain":
            folds = 0.75 + 0.25 * np.sin( u * 2 * math.pi * 9 + np.sin( v * 6 ) )
            opening = smoothstep( 0.42, 0.46, u ) * smoothstep( 0.62, 0.58, u )
            rgb = rgb * ( folds * ( 1 - opening * 0.0 ) )[..., None]
            rgb = mix( rgb, rgb * 1.3 + 0.05, opening )
        elif tone == "blind":
            slats = 0.6 + 0.4 * ( np.sin( v * 2 * math.pi * 26 ) > -0.3 )
            down = v < 0.55
            rgb = np.where( down[..., None], rgb * slats[..., None], rgb * 1.15 )
        else:
            slats = 0.55 + 0.45 * ( np.sin( v * 2 * math.pi * 22 ) > 0.0 )
            rgb = rgb * slats[..., None]
        # The frame and a dirty pane.
        frame = ( u < 0.04 ) | ( u > 0.96 ) | ( v < 0.05 ) | ( v > 0.95 ) | ( np.abs( u - 0.5 ) < 0.012 )
        rgb = np.where( frame[..., None], np.array( ( 0.55, 0.55, 0.52 ), np.float32 ), rgb )
        dirt = smoothstep( 0.0, 1.5, BM.noise( np.random.default_rng( len( name ) * 3 ), ( h, w ), ( w / 40.0, w / 40.0 ), 2.0, 20, 0.5 ) )
        rgb = rgb * ( 1 - 0.25 * dirt[..., None] )
        colour[ys, xs] = np.clip( rgb, 0, 1 ) * 255
        illum[ys, xs] = np.where( frame, 0.0, np.clip( rgb.mean( axis=-1 ) * 1.3, 0, 1 ) )

    # OFFICE: a lit box sign.
    ys, xs, ( w, h ) = region( "office" )
    img = Image.new( "RGB", ( w, h ), ( 236, 234, 224 ) )
    d = ImageDraw.Draw( img )
    d.rectangle( ( 0, 0, w - 1, h - 1 ), outline=( 30, 30, 30 ), width=int( h * 0.07 ) )
    _fit_text( d, ( 0, 0, w, h ), "OFFICE", FONT, ( 24, 60, 120 ), pad=0.16, track=0.12 )
    a = np.asarray( img, np.float32 ) / 255.0
    colour[ys, xs] = a * 255
    illum[ys, xs] = 0.6 * a.mean( axis=-1 )

    # Bulbs: warm dots on a dark strip (string lights seen close).
    ys, xs, ( w, h ) = region( "bulbs" )
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    sp = h * 1.0
    dots = np.exp( -( ( ( xx % sp ) - sp / 2 ) ** 2 + ( yy - h / 2 ) ** 2 ) / ( h * 0.18 ) ** 2 )
    colour[ys, xs] = np.clip( dots[..., None] * np.array( ( 1.0, 0.8, 0.5 ) ) + 0.04, 0, 1 ) * 255
    illum[ys, xs] = dots
    return colour, illum


# ---------------------------------------------------------------------------------------------------------------------
# Painted and printed signs (rs_signs): opaque

SIGN_ATLAS = ( 4096, 4096 )
SIGNS = {
    "speed": ( 0, 0, 512, 640 ),                 # SPEED LIMIT 15
    "people_too": ( 512, 0, 1536, 896 ),         # TRAILER PARK / PEOPLE TOO, brushed on a board
    "cooler_lid": ( 2048, 0, 1024, 640 ),        # SOME THINGS / SHOULD STAY / FORGOTTEN, marker on the cooler's lid
    "poster_ice": ( 3072, 0, 512, 704 ),         # posters on the store
    "poster_propane": ( 3584, 0, 512, 704 ),
    "poster_bait": ( 3072, 704, 512, 704 ),
    "poster_lotto": ( 3584, 704, 512, 704 ),
    "office_rules": ( 0, 640, 512, 704 ),        # PARK RULES
    "no_trespass": ( 512, 896, 1024, 512 ),      # NO TRESPASSING
    "lots": ( 1536, 896, 1536, 512 ),            # lot numbers 1-12, a strip of them
    "plate": ( 0, 1344, 512, 256 ),              # a licence plate
    "board_blank": ( 512, 1408, 1024, 512 ),     # a plain weathered board
    "sign_back": ( 1536, 1408, 512, 512 ),       # the grey back of a sign
    "tire": ( 2048, 1408, 512, 512 ),            # a tyre's tread and wall
    "crate_label": ( 2560, 1408, 512, 512 ),     # a crate's stencil: FRAGILE / THIS SIDE UP
    "beer_case": ( 3072, 1408, 1024, 512 ),      # a beer case's printed side
}


def signs_atlas():
    W, H = px( SIGN_ATLAS[0] ), px( SIGN_ATLAS[1] )
    k = W / SIGN_ATLAS[0]
    colour = np.full( ( H, W, 3 ), 0.5, np.float32 )
    rough = np.full( ( H, W ), 0.6, np.float32 )

    def region( name ):
        x, y, w, h = SIGNS[name]
        x, y, w, h = int( x * k ), int( y * k ), int( w * k ), int( h * k )
        return slice( y, y + h ), slice( x, x + w ), ( w, h )

    def weather( a, seed, amount=0.3, scale=60.0 ):
        h_, w_ = a.shape[:2]
        sub = np.random.default_rng( seed )
        g = smoothstep( -0.3, 1.6, BM.noise( sub, ( h_, w_ ), ( w_ / scale, w_ / scale ), 2.0, 20, 0.4 ) )
        runs = np.clip( runs_down( ( sub.random( ( h_, w_ ) ) < 0.0008 ).astype( np.float32 ), w_ / scale, 6, wrap=False ) * 18, 0, 1 )
        a = a * ( 1 - amount * g[..., None] )
        a = mix( a, np.array( ( 0.45, 0.25, 0.12 ), np.float32 ), runs * 0.5 )
        return np.clip( a, 0, 1 )

    # SPEED LIMIT 15 (the standard US regulatory sign's layout).
    ys, xs, ( w, h ) = region( "speed" )
    img = Image.new( "RGB", ( w, h ), ( 236, 236, 230 ) )
    d = ImageDraw.Draw( img )
    d.rounded_rectangle( ( int( w * 0.04 ), int( h * 0.04 ), int( w * 0.96 ), int( h * 0.96 ) ), radius=int( w * 0.06 ),
                         outline=( 16, 16, 16 ), width=int( w * 0.025 ) )
    _fit_text( d, ( 0, int( h * 0.08 ), w, int( h * 0.18 ) ), "SPEED", FONT, ( 16, 16, 16 ), pad=0.12, track=0.04 )
    _fit_text( d, ( 0, int( h * 0.27 ), w, int( h * 0.18 ) ), "LIMIT", FONT, ( 16, 16, 16 ), pad=0.12, track=0.04 )
    _fit_text( d, ( 0, int( h * 0.48 ), w, int( h * 0.42 ) ), "15", FONT, ( 16, 16, 16 ), pad=0.06, track=0.02 )
    a = weather( np.asarray( img, np.float32 ) / 255.0, 31, 0.25 )
    colour[ys, xs] = a
    rough[ys, xs] = 0.35

    # TRAILER PARK / PEOPLE TOO: black house paint brushed on a white-painted board.
    ys, xs, ( w, h ) = region( "people_too" )
    sub = np.random.default_rng( 32 )
    board = np.full( ( h, w, 3 ), ( 0.82, 0.8, 0.74 ), np.float32 )
    board *= ( 1.0 + 0.06 * BM.noise( sub, ( h, w ), ( w / 60.0, w / 60.0 ), 2.0, 30, 0.3 ) )[..., None]
    grain = ndimage.gaussian_filter( sub.standard_normal( ( h, w ) ).astype( np.float32 ), ( 1, 30 ) )
    board *= ( 1.0 + 0.05 * grain / ( grain.std() + 1e-6 ) )[..., None]
    ink = draw_paint( ( w, h ), ( 0.04 * w, 0.06 * h, 0.92 * w, 0.88 * h ), [ "TRAILER PARK", "PEOPLE TOO" ], sub, kind="brush",
                      thickness=0.12, align="center", jitter=0.035, line_gap=0.36 )
    a = mix( board, np.array( ( 0.06, 0.06, 0.06 ), np.float32 ), ink )
    colour[ys, xs] = weather( a, 33, 0.35 )
    rough[ys, xs] = 0.8

    # The cooler's lid inside: off-white plastic, black marker.
    ys, xs, ( w, h ) = region( "cooler_lid" )
    sub = np.random.default_rng( 34 )
    base = np.full( ( h, w, 3 ), ( 0.86, 0.86, 0.84 ), np.float32 )
    ink = draw_paint( ( w, h ), ( 0.06 * w, 0.06 * h, 0.88 * w, 0.88 * h ), [ "SOME THINGS", "SHOULD STAY", "FORGOTTEN" ], sub,
                      kind="brush", thickness=0.08, align="center", jitter=0.03, line_gap=0.34 )
    a = mix( base, np.array( ( 0.05, 0.05, 0.06 ), np.float32 ), ink )
    colour[ys, xs] = weather( a, 35, 0.4 )
    rough[ys, xs] = 0.5

    # Posters: plain made-up printed bills.
    for name, top, bottom, col in ( ( "poster_ice", "ICE", "BAGS $3", ( 30, 100, 180 ) ), ( "poster_propane", "PROPANE", "EXCHANGE", ( 200, 60, 30 ) ),
                                    ( "poster_bait", "LIVE BAIT", "TACKLE", ( 40, 120, 60 ) ), ( "poster_lotto", "LOTTERY", "SOLD HERE", ( 220, 170, 30 ) ) ):
        ys, xs, ( w, h ) = region( name )
        img = Image.new( "RGB", ( w, h ), ( 238, 234, 222 ) )
        d = ImageDraw.Draw( img )
        d.rectangle( ( 0, 0, w, int( h * 0.45 ) ), fill=col )
        _fit_text( d, ( 0, int( h * 0.05 ), w, int( h * 0.32 ) ), top, FONT, ( 250, 250, 245 ), pad=0.1, track=0.04 )
        _fit_text( d, ( 0, int( h * 0.55 ), w, int( h * 0.2 ) ), bottom, FONT, ( 30, 30, 30 ), pad=0.1, track=0.04 )
        a = weather( np.asarray( img, np.float32 ) / 255.0, hash( name ) % 1000, 0.45 )
        colour[ys, xs] = a
        rough[ys, xs] = 0.7

    for name, lines in ( ( "office_rules", [ "PARK RULES", "SPEED 15", "NO PETS OFF LEASH", "QUIET AFTER 10", "RENT DUE 1ST" ] ),
                         ( "no_trespass", [ "NO TRESPASSING" ] ) ):
        ys, xs, ( w, h ) = region( name )
        img = Image.new( "RGB", ( w, h ), ( 236, 236, 230 ) if name == "office_rules" else ( 196, 30, 26 ) )
        d = ImageDraw.Draw( img )
        fill = ( 20, 20, 20 ) if name == "office_rules" else ( 250, 250, 245 )
        rows = len( lines )
        for i, ln in enumerate( lines ):
            hh = h / ( rows + 0.6 )
            _fit_text( d, ( 0, int( hh * ( i + 0.3 ) ), w, int( hh * ( 0.9 if i else 1.1 ) ) ), ln, FONT, fill, pad=0.08, track=0.04 )
        colour[ys, xs] = weather( np.asarray( img, np.float32 ) / 255.0, len( name ), 0.35 )
        rough[ys, xs] = 0.45

    ys, xs, ( w, h ) = region( "lots" )
    img = Image.new( "RGB", ( w, h ), ( 230, 226, 214 ) )
    d = ImageDraw.Draw( img )
    for i in range( 12 ):
        x0 = int( w * i / 12 )
        d.rectangle( ( x0 + 4, 4, x0 + w // 12 - 4, h - 4 ), outline=( 30, 30, 30 ), width=6 )
        _fit_text( d, ( x0, 0, w // 12, h ), str( i + 1 ), FONT, ( 24, 24, 24 ), pad=0.18, track=0.0 )
    colour[ys, xs] = weather( np.asarray( img, np.float32 ) / 255.0, 41, 0.35 )
    rough[ys, xs] = 0.6

    ys, xs, ( w, h ) = region( "plate" )
    img = Image.new( "RGB", ( w, h ), ( 236, 236, 230 ) )
    d = ImageDraw.Draw( img )
    d.rectangle( ( 3, 3, w - 3, h - 3 ), outline=( 40, 90, 50 ), width=6 )
    _fit_text( d, ( 0, int( h * 0.18 ), w, int( h * 0.66 ) ), "RVR 615", FONT, ( 30, 70, 40 ), pad=0.1, track=0.06 )
    colour[ys, xs] = weather( np.asarray( img, np.float32 ) / 255.0, 42, 0.4 )
    rough[ys, xs] = 0.35

    ys, xs, ( w, h ) = region( "board_blank" )
    sub = np.random.default_rng( 43 )
    grain = ndimage.gaussian_filter( sub.standard_normal( ( h, w ) ).astype( np.float32 ), ( 1, 25 ) )
    a = np.full( ( h, w, 3 ), ( 0.5, 0.46, 0.4 ), np.float32 ) * ( 1 + 0.12 * grain / ( grain.std() + 1e-6 ) )[..., None]
    colour[ys, xs] = weather( a, 44, 0.3 )
    rough[ys, xs] = 0.85

    ys, xs, ( w, h ) = region( "sign_back" )
    a = np.full( ( h, w, 3 ), 0.55, np.float32 )
    colour[ys, xs] = weather( a, 45, 0.3 )
    rough[ys, xs] = 0.5

    ys, xs, ( w, h ) = region( "tire" )
    yy, xx = np.mgrid[0:h, 0:w].astype( np.float32 )
    tread = ( np.sin( yy / h * 2 * math.pi * 14 ) > 0.2 ).astype( np.float32 ) * ( ( xx / w > 0.2 ) & ( xx / w < 0.8 ) )
    a = np.full( ( h, w, 3 ), 0.07, np.float32 ) * ( 1 - 0.4 * tread )[..., None]
    colour[ys, xs] = a
    rough[ys, xs] = 0.85

    ys, xs, ( w, h ) = region( "crate_label" )
    sub = np.random.default_rng( 46 )
    grain = ndimage.gaussian_filter( sub.standard_normal( ( h, w ) ).astype( np.float32 ), ( 1, 20 ) )
    a = np.full( ( h, w, 3 ), ( 0.62, 0.5, 0.36 ), np.float32 ) * ( 1 + 0.1 * grain / ( grain.std() + 1e-6 ) )[..., None]
    img = Image.new( "L", ( w, h ), 0 )
    d = ImageDraw.Draw( img )
    _fit_text( d, ( 0, int( h * 0.2 ), w, int( h * 0.25 ) ), "FRAGILE", FONT, 255, pad=0.1 )
    _fit_text( d, ( 0, int( h * 0.55 ), w, int( h * 0.2 ) ), "THIS SIDE UP", FONT, 255, pad=0.1 )
    m = np.asarray( img, np.float32 ) / 255.0
    a = mix( a, np.array( ( 0.12, 0.1, 0.08 ), np.float32 ), m * 0.85 )
    colour[ys, xs] = weather( a, 47, 0.3 )
    rough[ys, xs] = 0.85

    ys, xs, ( w, h ) = region( "beer_case" )
    img = Image.new( "RGB", ( w, h ), ( 30, 60, 130 ) )
    d = ImageDraw.Draw( img )
    d.rectangle( ( 0, int( h * 0.7 ), w, h ), fill=( 230, 230, 230 ) )
    _fit_text( d, ( 0, int( h * 0.1 ), w, int( h * 0.5 ) ), "GATOR LIGHT", FONT, ( 245, 245, 240 ), pad=0.08, track=0.05 )
    _fit_text( d, ( 0, int( h * 0.72 ), w, int( h * 0.24 ) ), "24 CANS", FONT, ( 30, 60, 130 ), pad=0.1, track=0.05 )
    colour[ys, xs] = weather( np.asarray( img, np.float32 ) / 255.0, 48, 0.35 )
    rough[ys, xs] = 0.6
    return colour * 255, rough


# ---------------------------------------------------------------------------------------------------------------------
# Paint (rs_paint_*): spray paint, brush lettering and blood, alpha tested, tinted by material

PAINT_ATLAS = ( 4096, 4096 )
PAINT = {
    "still_here": ( 0, 0, 1024, 896 ),                  # STILL / HERE, under the park sign
    "fuel_food": ( 1024, 0, 1024, 1536 ),               # FUEL / FOOD / GUNS / A BETTER / TOMORROW?
    "safe_higher": ( 2048, 0, 1280, 1152 ),             # SAFE / HIGHER / STRONGER and an arrow
    "sticks": ( 0, 896, 1024, 1024 ),                   # RIVERSIDE / STICKS / TOGETHER, on the water tower
    "hand": ( 3328, 0, 768, 896 ),                      # a bloody handprint, dripping
    "smear": ( 3328, 896, 768, 640 ),                   # a smear and spatter
    "tag_a": ( 2048, 1152, 1024, 384 ),                 # scrawled tags: initials and a lot number
    "tag_b": ( 3072, 1536, 1024, 384 ),
    "x_mark": ( 1024, 1536, 512, 512 ),                 # an X sprayed on a door
    "help": ( 1536, 1536, 1536, 512 ),                  # HELP US
    "stripe": ( 0, 1920, 1024, 128 ),                   # a plain painted stripe (the RV's)
    "keep_out": ( 0, 2048, 1536, 512 ),                 # KEEP OUT
    "lot_7": ( 1536, 2048, 512, 512 ),                  # 7, brushed big
    "splatter": ( 2048, 2048, 1024, 1024 ),             # blood splatter on the ground
    "trail": ( 3072, 2048, 1024, 1024 ),                # a dragged blood trail
}


def paint_atlas():
    W, H = px( PAINT_ATLAS[0] ), px( PAINT_ATLAS[1] )
    k = W / PAINT_ATLAS[0]
    a = np.zeros( ( H, W ), np.float32 )

    def put( name, cov ):
        x, y, w, h = PAINT[name]
        x, y, w, h = int( x * k ), int( y * k ), int( w * k ), int( h * k )
        a[y:y + h, x:x + w] = np.maximum( a[y:y + h, x:x + w], cov[y:y + h, x:x + w] )

    size = ( W, H )

    def box( name ):
        x, y, w, h = PAINT[name]
        return ( x * k, y * k, w * k, h * k )

    put( "still_here", draw_paint( size, box( "still_here" ), [ "STILL", "HERE" ], np.random.default_rng( 51 ), thickness=0.14,
                                   drips=0.8, align="left", slant=0.12, jitter=0.05 ) )
    put( "fuel_food", draw_paint( size, box( "fuel_food" ), [ "FUEL", "FOOD", "GUNS", "A BETTER", "TOMORROW?" ], np.random.default_rng( 52 ),
                                  thickness=0.13, drips=0.6, align="center", slant=0.04, jitter=0.04, line_gap=0.3 ) )
    put( "safe_higher", draw_paint( size, box( "safe_higher" ), [ "SAFE", "HIGHER", "STRONGER", "    ↙" ], np.random.default_rng( 53 ),
                                    thickness=0.12, drips=0.5, align="left", slant=0.06, jitter=0.04, line_gap=0.28 ) )
    put( "sticks", draw_paint( size, box( "sticks" ), [ "RIVERSIDE", "STICKS", "TOGETHER" ], np.random.default_rng( 54 ),
                               kind="brush", thickness=0.13, drips=0, align="center", jitter=0.02, line_gap=0.3 ) )
    put( "tag_a", draw_paint( size, box( "tag_a" ), [ "JD 4 KT" ], np.random.default_rng( 55 ), thickness=0.16, drips=0.6, slant=0.3, jitter=0.08 ) )
    put( "tag_b", draw_paint( size, box( "tag_b" ), [ "LOT 7 RIP" ], np.random.default_rng( 56 ), thickness=0.15, drips=0.7, slant=0.2, jitter=0.06 ) )
    put( "x_mark", draw_paint( size, box( "x_mark" ), [ "X" ], np.random.default_rng( 57 ), thickness=0.22, drips=0.9, align="center" ) )
    put( "help", draw_paint( size, box( "help" ), [ "HELP US" ], np.random.default_rng( 58 ), thickness=0.15, drips=0.8, align="center", slant=0.1 ) )
    put( "keep_out", draw_paint( size, box( "keep_out" ), [ "KEEP OUT" ], np.random.default_rng( 59 ), thickness=0.16, drips=0.7, align="center" ) )
    put( "lot_7", draw_paint( size, box( "lot_7" ), [ "7" ], np.random.default_rng( 60 ), kind="brush", thickness=0.2, align="center" ) )

    # The stripe: solid, a little worn.
    x, y, w, h = ( int( v * k ) for v in PAINT["stripe"] )
    sub = np.random.default_rng( 61 )
    wear = smoothstep( 1.2, 2.0, BM.noise( sub, ( h, w ), ( w / 60.0, w / 60.0 ), 1.8, 10, 0.3 ) )
    a[y + int( h * 0.1 ):y + int( h * 0.9 ), x:x + w] = ( 1 - wear )[int( h * 0.1 ):int( h * 0.9 ), :]

    # A handprint: palm and fingers, smudged, the blood running down from it.
    x, y, w, h = ( int( v * k ) for v in PAINT["hand"] )
    img = Image.new( "L", ( w, h ), 0 )
    d = ImageDraw.Draw( img )
    cx, cy = w * 0.5, h * 0.58
    d.ellipse( ( cx - w * 0.2, cy - h * 0.13, cx + w * 0.2, cy + h * 0.15 ), fill=255 )
    for ang, L, wd in ( ( -60, 0.3, 0.07 ), ( -20, 0.36, 0.075 ), ( 0, 0.38, 0.075 ), ( 18, 0.34, 0.07 ), ( 40, 0.26, 0.06 ) ):
        a0 = math.radians( ang - 90 )
        bx, by = cx + math.cos( a0 ) * w * 0.12, cy - h * 0.08 + math.sin( a0 ) * h * 0.08
        ex, ey = bx + math.cos( a0 ) * w * L * 0.7, by + math.sin( a0 ) * h * L * 0.62
        d.line( ( bx, by, ex, ey ), fill=255, width=int( w * wd * 2 ) )
        d.ellipse( ( ex - w * wd, ey - w * wd, ex + w * wd, ey + w * wd ), fill=255 )
    thumb = math.radians( 200 )
    d.line( ( cx - w * 0.15, cy + h * 0.02, cx - w * 0.38, cy - h * 0.1 ), fill=255, width=int( w * 0.13 ) )
    sub = np.random.default_rng( 62 )
    for _ in range( 7 ):
        sx_ = cx + sub.uniform( -0.18, 0.18 ) * w
        L = sub.uniform( 0.15, 0.4 ) * h
        wd = sub.uniform( 0.012, 0.03 ) * w
        d.line( ( sx_, cy + h * 0.1, sx_ + sub.normal( 0, 3 ), cy + h * 0.1 + L ), fill=255, width=int( wd ) )
        d.ellipse( ( sx_ - wd, cy + h * 0.1 + L - wd, sx_ + wd, cy + h * 0.1 + L + wd ), fill=255 )
    m = np.asarray( img, np.float32 ) / 255.0
    m = ndimage.gaussian_filter( m, 2.0 )
    smudge = smoothstep( -0.5, 1.2, BM.noise( sub, ( h, w ), ( w / 20.0, w / 20.0 ), 1.6, 6, 0.1 ) )
    a[y:y + h, x:x + w] = np.maximum( a[y:y + h, x:x + w], smoothstep( 0.3, 0.6, m ) * ( 0.55 + 0.45 * smudge ) )

    # A smear and spatter; splatter on the ground; a dragged trail.
    for name, seed, kind in ( ( "smear", 63, "smear" ), ( "splatter", 64, "splat" ), ( "trail", 65, "trail" ) ):
        x, y, w, h = ( int( v * k ) for v in PAINT[name] )
        sub = np.random.default_rng( seed )
        img = Image.new( "L", ( w, h ), 0 )
        d = ImageDraw.Draw( img )
        if kind == "smear":
            for _ in range( 6 ):
                y0 = sub.uniform( 0.2, 0.6 ) * h
                d.line( ( w * 0.1, y0, w * 0.9, y0 + sub.uniform( -0.1, 0.25 ) * h ), fill=int( sub.uniform( 120, 255 ) ), width=int( h * sub.uniform( 0.03, 0.08 ) ) )
        elif kind == "splat":
            d.ellipse( ( w * 0.35, h * 0.35, w * 0.65, h * 0.62 ), fill=255 )
            for _ in range( 80 ):
                ang = sub.uniform( 0, 2 * math.pi )
                r = sub.uniform( 0.12, 0.48 ) * w
                s = sub.uniform( 2, 14 ) * ( 1.2 - r / w )
                cx_, cy_ = w * 0.5 + math.cos( ang ) * r, h * 0.5 + math.sin( ang ) * r
                d.ellipse( ( cx_ - s, cy_ - s * 0.7, cx_ + s, cy_ + s * 0.7 ), fill=255 )
        else:
            pts = [ ( w * 0.5 + math.sin( t * 3 ) * w * 0.08, h * t ) for t in np.linspace( 0, 1, 30 ) ]
            d.line( pts, fill=200, width=int( w * 0.16 ) )
            for _ in range( 60 ):
                t = sub.uniform( 0, 1 )
                cx_ = w * 0.5 + math.sin( t * 3 ) * w * 0.08 + sub.normal( 0, w * 0.1 )
                s = sub.uniform( 2, 10 )
                d.ellipse( ( cx_ - s, h * t - s, cx_ + s, h * t + s ), fill=255 )
        m = np.asarray( img, np.float32 ) / 255.0
        m = ndimage.gaussian_filter( m, 1.5 )
        broken = smoothstep( -0.8, 1.0, BM.noise( sub, ( h, w ), ( w / 30.0, w / 30.0 ), 1.6, 8, 0.2 ) )
        a[y:y + h, x:x + w] = np.maximum( a[y:y + h, x:x + w], smoothstep( 0.25, 0.6, m ) * ( 0.5 + 0.5 * broken ) )
    return a


# ---------------------------------------------------------------------------------------------------------------------
# Writing

# Flat paints: colour (sRGB), metalness, roughness, self-illumination brightness (0 for none)
PAINTED = {
    "rs_black": ( ( 18, 18, 19 ), 0.0, 0.7, 0 ),
    "rs_dark": ( ( 34, 34, 36 ), 0.2, 0.6, 0 ),
    "rs_steel": ( ( 92, 94, 96 ), 0.7, 0.45, 0 ),
    "rs_alu": ( ( 168, 170, 170 ), 0.8, 0.4, 0 ),
    "rs_rubber": ( ( 20, 20, 20 ), 0.0, 0.85, 0 ),
    "rs_glass": ( ( 18, 22, 26 ), 0.4, 0.06, 0 ),
    "rs_window_dark": ( ( 16, 20, 24 ), 0.5, 0.08, 0 ),
    "rs_bulb": ( ( 255, 196, 120 ), 0.0, 0.3, 5 ),
    "rs_bulb_dead": ( ( 90, 80, 66 ), 0.0, 0.3, 0 ),
    "rs_lamp_warm": ( ( 255, 210, 150 ), 0.0, 0.3, 6 ),
    "rs_lantern": ( ( 255, 214, 160 ), 0.0, 0.4, 2.5 ),
    "rs_lamp_sodium": ( ( 255, 168, 80 ), 0.0, 0.3, 7 ),
    "rs_lamp_cool": ( ( 220, 236, 255 ), 0.0, 0.3, 6 ),
    "rs_lamp_search": ( ( 236, 244, 255 ), 0.0, 0.2, 9 ),
    "rs_ember": ( ( 255, 120, 40 ), 0.0, 0.5, 8 ),
    "rs_red_stripe": ( ( 150, 26, 22 ), 0.0, 0.5, 0 ),
    "rs_cooler": ( ( 40, 92, 150 ), 0.0, 0.45, 0 ),
    "rs_cooler_white": ( ( 214, 214, 208 ), 0.0, 0.5, 0 ),
    "rs_teddy": ( ( 112, 80, 52 ), 0.0, 0.95, 0 ),
    "rs_teddy_dark": ( ( 52, 36, 24 ), 0.0, 0.9, 0 ),
    "rs_fridge": ( ( 200, 198, 188 ), 0.2, 0.4, 0 ),
    "rs_truck": ( ( 92, 70, 52 ), 0.3, 0.6, 0 ),
    "rs_truck_blue": ( ( 46, 66, 90 ), 0.3, 0.55, 0 ),
    "rs_drum_blue": ( ( 36, 62, 104 ), 0.3, 0.55, 0 ),
    "rs_drum_red": ( ( 120, 36, 28 ), 0.3, 0.55, 0 ),
    "rs_drum_inside": ( ( 22, 16, 12 ), 0.2, 0.8, 0 ),
    "rs_tank": ( ( 74, 84, 90 ), 0.5, 0.5, 0 ),
    "rs_pine_bark": ( ( 62, 48, 38 ), 0.0, 0.9, 0 ),
    "rs_palm_trunk": ( ( 96, 84, 70 ), 0.0, 0.9, 0 ),
    "rs_wire": ( ( 14, 14, 14 ), 0.0, 0.6, 0 ),
    "rs_curtain": ( ( 120, 60, 40 ), 0.0, 0.9, 0 ),
    "rs_tarp_blue": ( ( 30, 70, 130 ), 0.0, 0.6, 0 ),
    "rs_crate": ( ( 128, 102, 70 ), 0.0, 0.85, 0 ),
    "rs_fur": ( ( 70, 70, 70 ), 0.0, 0.9, 0 ),
    "rs_concrete_block": ( ( 128, 126, 120 ), 0.0, 0.9, 0 ),
    "rs_water": ( ( 10, 14, 16 ), 0.3, 0.04, 0 ),
    "rs_porch_light": ( ( 255, 220, 160 ), 0.0, 0.3, 5 ),
    "rs_tv": ( ( 120, 170, 255 ), 0.0, 0.2, 6 ),
    "rs_flag": ( ( 150, 30, 30 ), 0.0, 0.9, 0 ),
    "rs_lawn_chair": ( ( 46, 120, 90 ), 0.0, 0.6, 0 ),
    "rs_propane": ( ( 220, 220, 214 ), 0.3, 0.45, 0 ),
    "rs_ash": ( ( 24, 22, 20 ), 0.0, 0.95, 0 ),
}

# Tree cards: alpha-tested sprays drawn here too.
TREES = ( "rs_pine_needles", "rs_palm_frond", "rs_pine_far" )


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
          tint=( 1.0, 1.0, 1.0 ), alpha_ref=0.5 ):
    lines = [ "// Tools/riverside_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if alpha:
        lines += [ '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{alpha}"', f'    g_flAlphaTestReference "{alpha_ref:.2f}"',
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
    return ( '// Tools/riverside_materials.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n' + illum +
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metalness:.2f}"\n'
             '    TextureColor "materials/default/default_color.tga"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"\n'
             f'    TextureAmbientOcclusion "{DEFAULT_AO}"\n'
             f'    g_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"\n'
             '    g_flModelTintAmount "1.0"\n}\n' )


def write_text( path, text ):
    for attempt in range( 40 ):
        try:
            if path.exists() and path.read_text( encoding="utf-8" ) == text:
                return
            tmp = path.with_suffix( path.suffix + ".tmp" )
            tmp.write_text( text, encoding="utf-8", newline="\n" )
            tmp.replace( path )
            return
        except PermissionError:
            import time
            time.sleep( 0.25 )
    raise PermissionError( path )


def save_image( img, path, **kw ):
    """ Through a temporary file, retried: the open editor compiles each picture as it lands and holds the next. """
    import time
    tmp = path.with_name( path.stem + ".tmp" + path.suffix )
    img.save( tmp, **kw )
    for attempt in range( 40 ):
        try:
            tmp.replace( path )
            return
        except PermissionError:
            time.sleep( 0.25 )
    raise PermissionError( path )


def normal_map( height, ppi ):
    return BM.normals( height, ( ppi, ppi ) )


def write_surface( out, name, colour, rough, height, ppi, metalness=0.0, alpha=None, illum=None, illum_brightness=0.0,
                   illum_tint=( 1, 1, 1 ), tints=None, alpha_ref=0.5 ):
    """ tints: { variant name: ( r, g, b ) } more vmats sharing these maps, each with its colour tint. """
    srgb = T.linear_to_srgb( colour )
    save_image( Image.fromarray( np.clip( np.rint( srgb ), 0, 255 ).astype( np.uint8 ), "RGB" ), out / f"{name}_color.jpg", quality=92, subsampling=0 )
    nrm = ( normal_map( height, ppi ) * 0.5 + 0.5 ) * 255
    save_image( Image.fromarray( np.clip( np.rint( nrm ), 0, 255 ).astype( np.uint8 ), "RGB" ), out / f"{name}_normal.jpg", quality=94, subsampling=0 )
    save_image( Image.fromarray( np.clip( np.rint( rough * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), out / f"{name}_rough.png", optimize=True )
    alpha_path = illum_path = None
    if alpha is not None:
        save_image( Image.fromarray( np.clip( np.rint( alpha * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), out / f"{name}_trans.png", optimize=True )
        alpha_path = f"{RESOURCE_DIR}/{name}_trans.png"
    if illum is not None:
        save_image( Image.fromarray( np.clip( np.rint( illum * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), out / f"{name}_illum.png", optimize=True )
        illum_path = f"{RESOURCE_DIR}/{name}_illum.png"
    maps = ( f"{RESOURCE_DIR}/{name}_color.jpg", f"{RESOURCE_DIR}/{name}_normal.jpg", f"{RESOURCE_DIR}/{name}_rough.png" )
    write_text( out / f"{name}.vmat", vmat( *maps, metalness, alpha_path, illum_path, illum_brightness, illum_tint, alpha_ref=alpha_ref ) )
    for variant, tint in ( tints or {} ).items():
        t = tuple( c / 255.0 for c in tint )
        write_text( out / f"{variant}.vmat", vmat( *maps, metalness, alpha_path, illum_path, illum_brightness, illum_tint, tint=t, alpha_ref=alpha_ref ) )
    print( f"wrote {name}" + ( f" (+{len( tints )} tints)" if tints else "" ) )
    return srgb


# Trailer siding tints (each trailer one of them): sun-chalked white, cream, faded turquoise, tan, pale green, salmon.
SIDING_TINTS = { "rs_siding_white": ( 255, 255, 255 ), "rs_siding_cream": ( 250, 236, 200 ), "rs_siding_teal": ( 168, 214, 206 ),
                 "rs_siding_tan": ( 222, 196, 160 ), "rs_siding_green": ( 196, 214, 176 ), "rs_siding_salmon": ( 240, 196, 176 ),
                 "rs_siding_grey": ( 196, 198, 200 ), "rs_siding_blue": ( 176, 196, 222 ),
                 "rs_siding_burnt": ( 58, 52, 48 ) }
BOARD_TINTS = { "rs_boards_blue": ( 170, 196, 214 ), "rs_boards_yellow": ( 240, 220, 160 ), "rs_boards_dark": ( 128, 132, 130 ) }


def trees():
    """ Alpha-tested cards: a slash pine's needle tuft (long needles in clusters, bark-brown twigs through it), a cabbage
    palm's fan frond (segments splitting from the costa, threads at the tips), and a far forest's crown band. """
    out = {}
    rng = np.random.default_rng( 301 )
    n = px( 1024 )
    # Needle tuft: needles radiate from twig points along a branch running up the card.
    img = Image.new( "L", ( n, n ), 0 )
    col = Image.new( "RGB", ( n, n ), ( 0, 0, 0 ) )
    d, dc = ImageDraw.Draw( img ), ImageDraw.Draw( col )
    for _ in range( 22 ):
        cx, cy = rng.uniform( 0.15, 0.85 ) * n, rng.uniform( 0.12, 0.88 ) * n
        for _ in range( 120 ):
            ang = rng.uniform( 0, 2 * math.pi )
            L = rng.uniform( 0.06, 0.13 ) * n
            ex, ey = cx + math.cos( ang ) * L, cy + math.sin( ang ) * L * 0.9 - L * 0.15
            shade = int( rng.uniform( 60, 140 ) )
            d.line( ( cx, cy, ex, ey ), fill=255, width=max( 1, int( n / 500 ) ) )
            dc.line( ( cx, cy, ex, ey ), fill=( int( shade * 0.55 ), shade, int( shade * 0.45 ) ), width=max( 1, int( n / 500 ) ) )
    for _ in range( 8 ):
        pts = [ ( rng.uniform( 0.3, 0.7 ) * n, n ) ]
        for _ in range( 5 ):
            pts.append( ( pts[-1][0] + rng.normal( 0, n * 0.05 ), pts[-1][1] - n * 0.18 ) )
        d.line( pts, fill=255, width=max( 2, int( n / 180 ) ) )
        dc.line( pts, fill=( 60, 44, 32 ), width=max( 2, int( n / 180 ) ) )
    a = np.asarray( img, np.float32 ) / 255.0
    c = np.asarray( col, np.float32 )
    c = np.where( a[..., None] > 0.05, c, np.array( ( 30, 46, 26 ), np.float32 ) )
    out["rs_pine_needles"] = ( c, a )
    # Palm frond: a fan of 40 segments from a point at the card's foot, each a tapering blade, split at its tip.
    img = Image.new( "L", ( n, n ), 0 )
    col = Image.new( "RGB", ( n, n ), ( 0, 0, 0 ) )
    d, dc = ImageDraw.Draw( img ), ImageDraw.Draw( col )
    ox, oy = n * 0.5, n * 0.95
    for i in range( 44 ):
        ang = math.radians( -160 + 140 * i / 43 + rng.normal( 0, 1.5 ) )
        L = n * ( 0.62 + 0.25 * math.sin( math.pi * i / 43 ) ) * rng.uniform( 0.9, 1.05 )
        droop = rng.uniform( 0.02, 0.12 ) * n
        pts = []
        for t in np.linspace( 0.12, 1, 12 ):
            pts.append( ( ox + math.cos( ang ) * L * t, oy + math.sin( ang ) * L * t + droop * t * t ) )
        w0 = n * 0.022
        poly = []
        for j, p in enumerate( pts ):
            wj = w0 * ( 1 - j / len( pts ) ) + 1
            nx, ny = -math.sin( ang ), math.cos( ang )
            poly.append( ( p[0] + nx * wj, p[1] + ny * wj ) )
        for j, p in reversed( list( enumerate( pts ) ) ):
            wj = w0 * ( 1 - j / len( pts ) ) + 1
            nx, ny = -math.sin( ang ), math.cos( ang )
            poly.append( ( p[0] - nx * wj, p[1] - ny * wj ) )
        shade = int( rng.uniform( 70, 120 ) )
        d.polygon( poly, fill=255 )
        dc.polygon( poly, fill=( int( shade * 0.7 ), shade, int( shade * 0.5 ) ) )
        dc.line( pts, fill=( int( shade * 0.9 ), int( shade * 1.15 ), int( shade * 0.7 ) ), width=max( 1, int( n / 600 ) ) )
    d.line( ( ox, oy, ox, n ), fill=255, width=int( n * 0.02 ) )
    dc.line( ( ox, oy, ox, n ), fill=( 90, 80, 60 ), width=int( n * 0.02 ) )
    a = np.asarray( img, np.float32 ) / 255.0
    c = np.asarray( col, np.float32 )
    c = np.where( a[..., None] > 0.05, c, np.array( ( 50, 64, 40 ), np.float32 ) )
    out["rs_palm_frond"] = ( c, a )
    # A far forest's crown band: a row of pine crowns and palm heads against the sky, its foot solid, 2:1.
    w2, h2 = n * 2, n
    img = Image.new( "L", ( w2, h2 ), 0 )
    d = ImageDraw.Draw( img )
    d.rectangle( ( 0, int( h2 * 0.75 ), w2, h2 ), fill=255 )
    x = 0.0
    while x < w2:
        top = rng.uniform( 0.05, 0.5 ) * h2
        width = rng.uniform( 0.03, 0.08 ) * w2
        if rng.random() < 0.18:
            # A palm head: a puff of fronds on a thin trunk.
            d.line( ( x, h2 * 0.8, x + rng.normal( 0, 4 ), top + width * 0.4 ), fill=255, width=max( 2, int( w2 / 600 ) ) )
            for _ in range( 12 ):
                ang = rng.uniform( math.pi * 0.9, math.pi * 2.1 )
                L = width * rng.uniform( 0.5, 0.9 )
                d.line( ( x, top + width * 0.4, x + math.cos( ang ) * L, top + width * 0.4 + math.sin( ang ) * L * 0.6 + L * 0.3 ),
                        fill=255, width=max( 2, int( w2 / 900 ) ) )
        else:
            for _ in range( 30 ):
                cy = rng.uniform( top, h2 * 0.8 )
                rx = width * rng.uniform( 0.2, 0.6 ) * ( 0.3 + ( cy - top ) / ( h2 * 0.8 - top + 1 ) ) * 0.6
                jx = x + rng.normal( 0, 3 )
                d.ellipse( ( jx - rx, cy - rx * 0.5, jx + rx + 0.5, cy + rx * 0.5 + 0.5 ), fill=255 )
            d.line( ( x, top, x, h2 ), fill=255, width=max( 2, int( w2 / 500 ) ) )
        x += width * rng.uniform( 0.5, 1.0 )
    a = np.asarray( img, np.float32 ) / 255.0
    a = ndimage.gaussian_filter( a, 0.6 )
    c = np.zeros( ( h2, w2, 3 ), np.float32 ) + np.array( ( 22, 30, 24 ), np.float32 )
    c *= ( 1.0 + 0.2 * BM.noise( rng, ( h2, w2 ), ( 1.0, 1.0 ), 2.0, 60, 2 ) )[..., None]
    out["rs_pine_far"] = ( c, a )
    return out


SURFACES = {
    "rs_mud": lambda: mud(),
    "rs_yard": lambda: yard(),
    "rs_gravel": lambda: gravel(),
    "rs_siding": lambda: siding(),
    "rs_roof": lambda: roof(),
    "rs_skirt": lambda: skirt(),
    "rs_boards": lambda: boards(),
    "rs_plywood": lambda: plywood(),
    "rs_wood": lambda: planks(),
    "rs_pole": lambda: pole(),
    "rs_ties": lambda: ties(),
    "rs_concrete": lambda: concrete(),
    "rs_rust": lambda: rust(),
    "rs_sandbag": lambda: sandbag(),
}
METALNESS = { "rs_siding": 0.35, "rs_roof": 0.6, "rs_skirt": 0.3, "rs_rust": 0.2 }
NAMES = list( SURFACES ) + [ "rs_chainlink", "lit", "signs", "paint", "trees", "painted" ]


# The searchlight's beam (riverside_parts.beam_cone): additive light through the haze, hc1_light_beam.shader.
BEAM_VMAT = """// Tools/riverside_materials.py
"Layer0"
{
    shader "shaders/hc1_light_beam.shader"
    g_vBeamColour "[0.780000 0.840000 1.000000 0.000000]"
    g_flBeamIntensity "0.9"
    g_flBeamReach "1.0"
    g_flSoftDepth "60"
}
"""


def all_paints():
    return ( list( SURFACES ) + list( SIDING_TINTS ) + list( BOARD_TINTS ) +
             [ "rs_chainlink", "rs_lit", "rs_signs", "rs_paint_red", "rs_paint_white", "rs_paint_dark", "rs_blood", "rs_beam" ] +
             list( TREES ) + [ "rs_palm_dead" ] + list( PAINTED ) )


def build( name, out ):
    done = {}
    if name in SURFACES:
        c, r, h, ppi = SURFACES[name]()
        tints = SIDING_TINTS if name == "rs_siding" else BOARD_TINTS if name == "rs_boards" else None
        done[name] = write_surface( out, name, c, r, h, ppi, METALNESS.get( name, 0.0 ), tints=tints )
    elif name == "rs_chainlink":
        c, r, h, ppi, wires = chainlink()
        done[name] = write_surface( out, name, c, r, h, ppi, 0.6, alpha=wires, alpha_ref=0.35 )
    elif name == "lit":
        c, il = lit_atlas()
        save_image( Image.fromarray( np.clip( np.rint( c ), 0, 255 ).astype( np.uint8 ), "RGB" ), out / "rs_lit_color.png", optimize=True )
        save_image( Image.fromarray( np.clip( np.rint( il * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), out / "rs_lit_illum.png", optimize=True )
        write_text( out / "rs_lit.vmat", vmat( f"{RESOURCE_DIR}/rs_lit_color.png", "materials/default/default_normal.tga",
                                               "[0.350000 0.350000 0.350000 0.000000]", illum=f"{RESOURCE_DIR}/rs_lit_illum.png",
                                               illum_brightness=4.5 ) )
        done["rs_lit"] = c
        print( "wrote rs_lit" )
    elif name == "signs":
        c, r = signs_atlas()
        save_image( Image.fromarray( np.clip( np.rint( c ), 0, 255 ).astype( np.uint8 ), "RGB" ), out / "rs_signs_color.png", optimize=True )
        save_image( Image.fromarray( np.clip( np.rint( r * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), out / "rs_signs_rough.png", optimize=True )
        write_text( out / "rs_signs.vmat", vmat( f"{RESOURCE_DIR}/rs_signs_color.png", "materials/default/default_normal.tga",
                                                 f"{RESOURCE_DIR}/rs_signs_rough.png" ) )
        done["rs_signs"] = c
        print( "wrote rs_signs" )
    elif name == "paint":
        a = paint_atlas()
        save_image( Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), out / "rs_paint_trans.png", optimize=True )
        for tone, tint, rough in ( ( "red", ( 0.42, 0.025, 0.02 ), 0.55 ), ( "white", ( 0.86, 0.86, 0.84 ), 0.6 ),
                                   ( "dark", ( 0.03, 0.03, 0.03 ), 0.7 ) ):
            text = vmat( "[1.000000 1.000000 1.000000 0.000000]", "materials/default/default_normal.tga",
                         f"[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]", 0.0, f"{RESOURCE_DIR}/rs_paint_trans.png", tint=tint, alpha_ref=0.4 )
            write_text( out / f"rs_paint_{tone}.vmat", text )
        # Blood: dark, glossy where it's fresh.
        text = vmat( "[1.000000 1.000000 1.000000 0.000000]", "materials/default/default_normal.tga",
                     "[0.180000 0.180000 0.180000 0.000000]", 0.0, f"{RESOURCE_DIR}/rs_paint_trans.png", tint=( 0.2, 0.01, 0.01 ), alpha_ref=0.4 )
        write_text( out / "rs_blood.vmat", text )
        done["rs_paint"] = np.repeat( a[..., None] * 255, 3, -1 )
        print( "wrote rs_paint" )
    elif name == "trees":
        for tname, ( c, a ) in trees().items():
            save_image( Image.fromarray( np.clip( np.rint( c ), 0, 255 ).astype( np.uint8 ), "RGB" ), out / f"{tname}_color.png", optimize=True )
            save_image( Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), out / f"{tname}_trans.png", optimize=True )
            write_text( out / f"{tname}.vmat", vmat( f"{RESOURCE_DIR}/{tname}_color.png", "materials/default/default_normal.tga",
                                                     "[0.850000 0.850000 0.850000 0.000000]", 0.0, f"{RESOURCE_DIR}/{tname}_trans.png", alpha_ref=0.4 ) )
            done[tname] = c
        # Dead fronds hanging under a palm's crown: the frond's cards, browned.
        write_text( out / "rs_palm_dead.vmat", vmat( f"{RESOURCE_DIR}/rs_palm_frond_color.png", "materials/default/default_normal.tga",
                                                     "[0.900000 0.900000 0.900000 0.000000]", 0.0, f"{RESOURCE_DIR}/rs_palm_frond_trans.png",
                                                     tint=( 1.25, 0.85, 0.5 ), alpha_ref=0.4 ) )
        print( "wrote tree cards" )
    elif name == "painted":
        write_text( out / "rs_beam.vmat", BEAM_VMAT )
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
