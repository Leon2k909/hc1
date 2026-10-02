"""
Belltower's vista land, painted from above: the colour (with the ground's kind) and the normal map of each of
hc1_vista.shader's four zones, and the tiling detail the shader adds up close.

    python Tools/belltower_vista_paint.py [--size N] [--zones abcd] [--out <dir>] [--sheet <png>]
                                          [--preview <dir>] [--views name ...]

--size is the colour maps' size (4096; the normal maps are half that). --out writes the textures somewhere else, to try
changes, and --sheet writes a picture of the zones to look at. --preview renders the textured land and the town from
the town's streets (belltower_vista.PREVIEW_VIEWS, or the --views named) from the textures in --out (or the
project's), per pixel as the shader picks the zones; the town is flat-coloured. With --preview and no --zones, nothing
is painted.

The land's shape is belltower_vista's. Painted on it:
- Patterns are laid out where the forced perspective plays them (belltower_vista.apparent), at their real sizes there.
  The farmland is districts a few kilometres across (DISTRICT), each with its own heading, field size and taste for
  hedges, and a mix of crops by the land at its middle (REGION_CROPS). Their fields lie in staggered rows like a brick
  wall's, bent by noise, some split in two. A field's crop comes from its district and the land at its middle: steep
  ones are woods or pasture, the floodplain grows maize, meadow and poplars, vineyards and olives like sunny slopes.
  Wheat and barley have tramlines, stubble its swaths, hay its windrows, ploughed clay its furrows, vineyards their rows
  and the rows' shadows.
- Between the fields: grass margins, dirt tracks, hedges, ditches and lines of oaks (EDGE_*).
- Woods where noise, slope and height say, thicker on the hills and the mountains and none on the town's hill; scrub
  and rock where it's too steep for soil; the river in its gravel bed with poplars and willows along its banks; olive
  terraces stepping down the town's own hill behind dry-stone walls.
- Trees are drawn one at a time where they're at least a texel and a half across, at their real size over the forced
  perspective's scale, with the sun's light on their crowns and the shadows they throw onto the ground and each other
  (a ray from each texel towards belltower_vista.SUN, against each crown's spheroid). Smaller, they're painted as their
  mean: the canopy's colour and shading, and the share of the ground between that's in shade. From 1.5 to 3 texels
  across, fewer trees are drawn and the mean makes up the rest. Trees are placed where they're played and drawn round
  where they stand, so a tree is the same in every zone that draws it.
- The vista's buildings and trees (Tools/belltower_vista_props.py) are models, so only what they do to the ground is
  painted: the ground they stand on (a town's paving and kitchen gardens, a farm's beaten earth, the villa's parterre,
  a cemetery's gravel), their white roads, and their shadows (each building as a box up to halfway up its roof). The
  painter's own trees keep off all of it.
- Anything finer than a texel is left out: noise, stripes and edges are box-filtered over the texel's footprint where
  it's played (its size times the forced perspective's stretch there).

Colours are albedo: the engine lights the land by the normal maps and the sun. Only the trees' shading and shadows are
painted in, for the sun and sky belltower_map's light has (SUN_RGB, AMBIENT): a shadow keeps the sky's light alone.
"""
import argparse
import math
import time
from pathlib import Path

import numba
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

import belltower_vista as V


def _fresh_cache():
    """ numba keys each function's cache by its own file, but these compile belltower_vista's functions into theirs:
    drop the cache when belltower_vista.py is newer. """
    cache = Path( __file__ ).resolve().parent / "__pycache__"
    if cache.exists():
        vista = Path( V.__file__ ).stat().st_mtime
        for f in list( cache.glob( "belltower_vista_paint.*.nbi" ) ) + list( cache.glob( "belltower_vista_paint.*.nbc" ) ):
            if f.stat().st_mtime < vista:
                f.unlink()


_fresh_cache()

OUT_DIR = V.TEXTURE_DIR
RESOURCE_DIR = V.TEXTURE_RESOURCE
MATERIAL = "vista_land"
M = 39.37                   # units a metre
HECTARE = 1e4 * M * M

# The zones: each one's texture covers the town's rectangle grown by its margin (hc1_vista.shader's g_vZoneMargins), and
# blends into the next over the last ZONE_BLEND of it.
ZONES = ( ( "a", 1600.0 ), ( "b", 6000.0 ), ( "c", 34000.0 ), ( "d", 92000.0 ) )
ZONE_BLEND = 0.12
COLOUR_SIZE = 4096
DETAIL_SIZE = 1024
DETAIL_TILES = ( 70.0, 290.0 )
DETAIL_FADE = ( 700.0, 2600.0 )
ROUGHNESS = ( 0.95, 0.9, 0.8, 0.12 )        # grass, soil, stone, water
GRASS, SOIL, STONE, WATER = 0.0, 1.0, 2.0, 3.0


def linear( srgb ):
    c = np.asarray( srgb, float ) / 255.0
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def srgb8( lin ):
    c = np.clip( lin, 0.0, 1.0 )
    s = np.where( c <= 0.0031308, c * 12.92, 1.055 * c ** ( 1 / 2.4 ) - 0.055 )
    return np.clip( np.rint( s * 255 ), 0, 255 ).astype( np.uint8 )


# ---------------------------------------------------------------------------------------------------------------------
# What grows: crops, the ground's colours, trees

WHEAT, BARLEY, STUBBLE, HAY, MEADOW, PASTURE, PLOUGH, FALLOW, SUNFLOWER, MAIZE, VINEYARD, OLIVES, WOOD, POPLARS = range( 14 )
CROP_COLOURS = linear( [
    ( 176, 164, 92 ),       # wheat (its ripeness mixes WHEAT_GREEN and WHEAT_GOLD)
    ( 204, 186, 124 ),      # barley
    ( 196, 178, 130 ),      # stubble
    ( 166, 164, 98 ),       # hay, cut
    ( 108, 124, 56 ),       # meadow
    ( 98, 118, 52 ),        # pasture
    ( 150, 118, 86 ),       # ploughed clay
    ( 140, 132, 80 ),       # fallow
    ( 84, 110, 46 ),        # sunflowers, a month up
    ( 70, 102, 40 ),        # maize
    ( 128, 124, 76 ),       # a vineyard's grass between the rows
    ( 158, 148, 100 ),      # an olive grove's dry grass
    ( 56, 58, 36 ),         # a wood's floor
    ( 106, 116, 58 ),       # a poplar plantation's grass
] )
WHEAT_GREEN = linear( ( 128, 144, 70 ) )
WHEAT_GOLD = linear( ( 198, 176, 102 ) )
STRAW = linear( ( 214, 196, 140 ) )
HAY_ROW = linear( ( 122, 128, 64 ) )
SOIL_COLOUR = linear( ( 152, 122, 90 ) )
DRY_SOIL = linear( ( 176, 150, 116 ) )
MARGIN = linear( ( 118, 128, 62 ) )
DUST = linear( ( 188, 174, 146 ) )
DITCH = linear( ( 62, 82, 40 ) )
UNDERGROWTH = linear( ( 64, 70, 40 ) )
WOOD_FLOOR = linear( ( 56, 58, 36 ) )
DRY_GRASS = linear( ( 164, 152, 102 ) )
GREEN_GRASS = linear( ( 110, 124, 58 ) )
ROCK = linear( ( 168, 162, 146 ) )
SCREE = linear( ( 150, 144, 128 ) )
WALL_STONE = linear( ( 150, 142, 124 ) )
WALL_TOP = linear( ( 176, 170, 154 ) )
WATER_EDGE = linear( ( 40, 56, 50 ) )
WATER_DEEP = linear( ( 18, 30, 32 ) )
GRAVEL = linear( ( 180, 172, 152 ) )
BANK = linear( ( 88, 104, 48 ) )
VINE = linear( ( 66, 94, 40 ) )
FOOT_GRASS = linear( ( 128, 128, 72 ) )
FLOWERS = linear( [ ( 196, 28, 22 ), ( 220, 192, 40 ), ( 226, 224, 210 ), ( 126, 84, 160 ) ] )   # poppy, buttercup,
                                                                                                # daisy, vetch
# Each crop's flowers: how many (in a lush patch) and which, as weights of FLOWERS.
POPPIES = np.array( ( 0.8, 0.1, 0.1, 0.0 ) )
# The props' ground (belltower_vista_props.YARD_*): a town's paving, a farm's beaten earth, a garden's lawn, gravel.
YARD_COLOURS = linear( [ ( 152, 142, 122 ), ( 176, 160, 128 ), ( 104, 120, 60 ), ( 190, 184, 166 ) ] )
YARD_KINDS = np.array( ( STONE, SOIL, GRASS, SOIL ) )
YARD_FLAT = np.array( ( 0.7, 0.4, 0.6, 0.5 ) )      # how much of the land's small relief each smooths away
KITCHEN_GARDEN = linear( ( 92, 106, 56 ) )
BOX_HEDGE = linear( ( 52, 70, 36 ) )
ROAD = linear( ( 206, 194, 166 ) )                  # a strada bianca: limestone gravel
VERGE = linear( ( 168, 156, 112 ) )                 # its dust on the grass beside it
MEADOW_FLOWERS = np.array( ( 0.15, 0.4, 0.3, 0.15 ) )

# The districts: what they grow, by the land at their middle.
PLAIN, HILLFARM, VINES, UPLAND = range( 4 )
REGION_CROPS = np.array( [
    # wheat barley stubble hay meadow pasture plough fallow sunfl maize vine olive wood poplar
    ( 22, 8, 9, 10, 8, 5, 10, 4, 9, 8, 2, 2, 1, 2 ),
    ( 12, 4, 4, 12, 12, 9, 7, 5, 4, 0, 8, 13, 10, 0 ),
    ( 4, 2, 2, 5, 8, 3, 6, 3, 0, 0, 34, 24, 9, 0 ),
    ( 3, 1, 1, 12, 20, 26, 2, 6, 0, 0, 0, 4, 25, 0 ),
], float )

# Trees: crown radius, the crown's middle over the ground and its half-height (metres), and shadow's opacity.
OAK, HOLM, OLIVE, CYPRESS, POPLAR, WILLOW, PINE, SHRUB, BEECH, BALE = range( 10 )
TREES = np.array( [
    ( 5.0, 8.0, 4.2, 0.88 ),        # oak
    ( 3.8, 5.6, 3.0, 0.92 ),        # holm oak
    ( 2.4, 2.9, 1.7, 0.78 ),        # olive
    ( 0.9, 8.5, 7.5, 0.95 ),        # cypress
    ( 2.6, 13.0, 9.0, 0.82 ),       # poplar
    ( 3.6, 5.2, 3.0, 0.8 ),         # willow
    ( 5.5, 11.5, 2.4, 0.9 ),        # umbrella pine
    ( 1.4, 1.2, 1.1, 0.85 ),        # shrub
    ( 5.5, 11.0, 5.5, 0.9 ),        # beech
    ( 0.75, 0.75, 0.7, 1.0 ),       # a round bale
] )
TREES[:, :3] *= M
TREE_COLOURS = linear( [ ( 62, 82, 38 ), ( 46, 62, 33 ), ( 112, 122, 86 ), ( 36, 52, 30 ), ( 88, 112, 50 ),
                         ( 108, 126, 72 ), ( 56, 76, 42 ), ( 70, 86, 44 ), ( 70, 96, 44 ), ( 198, 178, 122 ) ] )
# How much ground a tree's shadow covers past its own crown, as a share of the crown's area, with the sun at its height
# (for painting a tree's mean where it's too small to draw).
SPREAD = np.array( ( 2.3, 2.0, 1.3, 17.0, 6.0, 1.7, 2.5, 1.3, 2.4, 1.6 ) )
CROWN_MEAN = 0.8            # a crown's mean shading seen from above, the sun at 34 degrees
LAYER_CELL = np.array( ( 4.0, 3.0, 2.0 ) ) * M       # the candidate grids: big trees, planted rows, small things
PX_MIN, PX_FULL = 1.5, 3.0  # crowns this many texels across are drawn: none, all

# belltower_map's sun and sky light. Flat ground in the sun gets FLAT_LIT, and in shadow the sky's light alone: this
# share of it, bluer.
SUN_RGB = np.array( ( 1.32, 1.06, 0.76 ) )
AMBIENT = np.array( ( 0.30, 0.40, 0.58 ) )
FLAT_LIT = AMBIENT + SUN_RGB * float( V.SUN[2] )
SHADOW_TINT = AMBIENT / FLAT_LIT
LEAF_SUN = 0.85             # how much of the sun a crown's lit side keeps: its own leaves shade the rest
SHADE_MAX = 1.3

# Field edges: kinds, and each one's half-width either side of the boundary (metres).
EDGE_PLAIN, EDGE_TRACK, EDGE_HEDGE, EDGE_DITCH, EDGE_TREES = range( 5 )
EDGE_HALF = np.array( ( 0.8, 1.5, 1.6, 1.0, 1.4 ) ) * M

DISTRICT = 110000.0         # the districts' size where they're played (2.8 km)
ROW = 4600.0                # a row of fields' depth where it's played (117 m), times its district's scale
ROW_RUN = 21000.0           # how far along a row its boundary keeps to one kind
TERRACE_STEP = 1.8 * M      # the olive terraces' rise
TERRACE_REACH = 3000.0      # how far out from the walls they go
FOOT = 160.0                # the grass strip along the walls' foot
BANK_WIDTH = 900.0          # the river's wooded banks
SUN_PLAN = V.SUN[:2] / np.linalg.norm( V.SUN[:2] )
DECIDE_CUTOFF = 150.0       # the trees are decided on the land at this cutoff, the same in every zone,
DECIDE_STEP = 60.0          # its slope measured over this,
DECIDE_W = 20.0             # and its patterns as a texel this size sees them


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

@numba.njit( cache=True, fastmath=True, inline="always" )
def _h( a, b, c ):
    return V._hash( np.int64( a ), np.int64( b ), np.int64( c ) )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _u( h, k ):
    """ The k-th number 0..1 from hash h. """
    return ( V._hash( np.int64( h ), np.int64( k ), np.int64( 7919 ) ) & 0xFFFFFF ) / 16777216.0


@numba.njit( cache=True, fastmath=True, inline="always" )
def _box( x, wP ):
    """ The share of a footprint wP across, centred x past an edge, that's past it. """
    return min( max( x / wP + 0.5, 0.0 ), 1.0 )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _covered( x, period, width ):
    """ How much of 0..x stripes width wide every period (starting at 0) cover. """
    k = math.floor( x / period )
    return k * width + min( x - k * period, width )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _stripes( x, period, width, wP ):
    """ The share of a footprint wP across, centred at x, that stripes width wide every period (from 0) cover. """
    return ( _covered( x + 0.5 * wP, period, width ) - _covered( x - 0.5 * wP, period, width ) ) / wP


@numba.njit( cache=True, fastmath=True, inline="always" )
def _stretch( a, b, c, d ):
    """ The largest stretch of the 2x2 matrix ( a b; c d ): its larger singular value. """
    t = a * a + b * b + c * c + d * d
    det = a * d - b * c
    return math.sqrt( 0.5 * ( t + math.sqrt( max( t * t - 4.0 * det * det, 0.0 ) ) ) )


@numba.njit( cache=True, fastmath=True )
def _real_place( pe, pn ):
    """ The plan point whose apparent place is ( pe, pn ) (belltower_vista.real_place). """
    re, rn = pe - V.CENTRE[0], pn - V.CENTRE[1]
    lo, hi = 0.0, 1.0
    for _ in range( 48 ):
        mid = 0.5 * ( lo + hi )
        d = V._town_offset( V.CENTRE[0] + re * mid, V.CENTRE[1] + rn * mid )[0]
        if mid * V._scale( d )[0] < 1.0:
            lo = mid
        else:
            hi = mid
    mid = 0.5 * ( lo + hi )
    return V.CENTRE[0] + re * mid, V.CENTRE[1] + rn * mid


@numba.njit( cache=True, fastmath=True, inline="always" )
def _bilinear( grid, x, y ):
    rows, cols = grid.shape
    x = min( max( x, 0.0 ), cols - 1.0 )
    y = min( max( y, 0.0 ), rows - 1.0 )
    j = min( int( x ), cols - 2 )
    i = min( int( y ), rows - 2 )
    fx, fy = x - j, y - i
    return ( ( grid[i, j] * ( 1.0 - fx ) + grid[i, j + 1] * fx ) * ( 1.0 - fy )
             + ( grid[i + 1, j] * ( 1.0 - fx ) + grid[i + 1, j + 1] * fx ) * fy )


# ---------------------------------------------------------------------------------------------------------------------
# The farmland's layout, where it's played

@numba.njit( cache=True, fastmath=True )
def _district( E, N ):
    """ The district a played point is in: its hash and its middle. """
    ci = np.int64( math.floor( E / DISTRICT ) )
    cj = np.int64( math.floor( N / DISTRICT ) )
    best = 1e300
    bh = np.int64( 0 )
    be = 0.0
    bn = 0.0
    for di in range( -1, 2 ):
        for dj in range( -1, 2 ):
            h = _h( ci + di, cj + dj, 9001 )
            se = ( ci + di + 0.15 + 0.7 * _u( h, 1 ) ) * DISTRICT
            sn = ( cj + dj + 0.15 + 0.7 * _u( h, 2 ) ) * DISTRICT
            g = ( E - se ) * ( E - se ) + ( N - sn ) * ( N - sn )
            if g < best:
                best, bh, be, bn = g, h, se, sn
    return bh, be, bn


@numba.njit( cache=True, fastmath=True )
def _region( dh, de, dn, grads ):
    """ What a district mostly grows, by the land at its middle. """
    e, n = _real_place( de, dn )
    z = V._height( e, n, 3000.0, grads )
    g = math.hypot( V._height( e + 1500.0, n, 3000.0, grads ) - z, V._height( e, n + 1500.0, 3000.0, grads ) - z ) / 1500.0
    r = _u( dh, 7 )
    if z < -3800.0:
        return PLAIN if r < 0.8 else HILLFARM
    if z < -1500.0 and g < 0.25:
        return PLAIN if r < 0.4 else ( HILLFARM if r < 0.8 else VINES )
    if z < 2500.0:
        return HILLFARM if r < 0.45 else ( VINES if r < 0.8 else UPLAND )
    return UPLAND if r < 0.7 else HILLFARM


@numba.njit( cache=True, fastmath=True )
def _frame( E, N, dh, de, dn, grads ):
    """ ( u along the district's rows of fields, v across them, the rows' heading ) at a played point. The rows bend:
    noise moves u and v by up to a field or so over a few kilometres. """
    a = math.pi * _u( dh, 3 )
    ca, sa = math.cos( a ), math.sin( a )
    x, y = E - de, N - dn
    seed = np.int64( dh & 1023 )
    u = x * ca + y * sa + 2200.0 * V._fbm( E, N, 46000.0, 2, 0.5, 800 + seed, 1.0, grads )
    v = -x * sa + y * ca + 1600.0 * V._fbm( E, N, 38000.0, 2, 0.5, 1900 + seed, 1.0, grads )
    return u, v, a


@numba.njit( cache=True, fastmath=True )
def _edge_kind( h, dh ):
    hedges = 0.5 + _u( dh, 8 )          # the district's taste for hedges
    r = _u( h, 9 )
    if r < 0.14:
        return EDGE_TRACK
    r = ( r - 0.14 ) / 0.86
    if r < 0.2 * hedges:
        return EDGE_HEDGE
    if r < 0.2 * hedges + 0.1:
        return EDGE_DITCH
    if r < 0.2 * hedges + 0.2:
        return EDGE_TREES
    return EDGE_PLAIN


@numba.njit( cache=True, fastmath=True )
def _cell( u, v, dh ):
    """ The field at ( u, v ) in its district's frame: its hash, where in it ( fu, fv ), and its edges' distances and
    kinds ( left, right, bottom, top ). Rows are ROW deep (times the district's scale), and each row's fields its own
    length, offset from the next row's like bricks. A third of the fields are split in two. """
    H = ROW * ( 0.65 + 0.8 * _u( dh, 4 ) )
    j = np.int64( math.floor( v / H ) )
    hj = _h( dh, j, 31 )
    L = H * ( 1.15 + 2.4 * _u( hj, 1 ) )
    phase = L * _u( hj, 2 )
    i = np.int64( math.floor( ( u + phase ) / L ) )
    fid = _h( hj, i, 37 )
    fu = u + phase - i * L
    fv = v - j * H
    kl = _edge_kind( _h( hj, i, 41 ), dh )
    kr = _edge_kind( _h( hj, i + 1, 41 ), dh )
    run = np.int64( math.floor( u / ROW_RUN ) )
    kb = _edge_kind( _h( _h( dh, j, 43 ), run, 47 ), dh )
    kt = _edge_kind( _h( _h( dh, j + 1, 43 ), run, 47 ), dh )
    dl, dr, db, dt = fu, L - fu, fv, H - fv
    split = _u( fid, 5 )
    if split < 0.22:
        t = ( 0.3 + 0.4 * _u( fid, 6 ) ) * L
        k = _edge_kind( _h( fid, 0, 53 ), dh )
        if fu < t:
            fid = _h( fid, 1, 59 )
            dr = t - fu
            kr = k
        else:
            fid = _h( fid, 2, 59 )
            dl = fu - t
            kl = k
    elif split < 0.34:
        t = ( 0.35 + 0.3 * _u( fid, 6 ) ) * H
        k = _edge_kind( _h( fid, 0, 61 ), dh )
        if fv < t:
            fid = _h( fid, 3, 59 )
            dt = t - fv
            kt = k
        else:
            fid = _h( fid, 4, 59 )
            db = fv - t
            kb = k
    return fid, fu, fv, dl, dr, db, dt, kl, kr, kb, kt


@numba.njit( cache=True, fastmath=True )
def _crop( fid, region, z, gx, gy, dv, reach ):
    """ A field's crop, from its district's mix and the land at its middle. """
    w = REGION_CROPS[region].copy()
    slope = math.hypot( gx, gy )
    south = gy / max( slope, 1e-6 ) * V._smooth( 0.04, 0.18, slope )     # 1 facing south, -1 north
    if slope > 0.5:
        return WOOD if _u( fid, 12 ) < 0.75 else PASTURE
    if slope > 0.28:
        for c in ( WHEAT, BARLEY, STUBBLE, PLOUGH, SUNFLOWER, MAIZE ):
            w[c] *= 0.2
    flood = reach * ( 1.0 - V._smooth( V.FLOODPLAIN, V.FLOODPLAIN + 1500.0, dv ) )
    if flood > 0.5:
        w[MAIZE] *= 4.0
        w[MEADOW] *= 2.0
        w[POPLARS] = 6.0
        w[VINEYARD] *= 0.1
        w[OLIVES] *= 0.1
        w[WOOD] *= 0.2
    else:
        w[POPLARS] = 0.0
        w[MAIZE] *= 0.3
    w[VINEYARD] *= 0.4 + 1.6 * max( south, 0.0 )
    w[OLIVES] *= 0.6 + 0.8 * max( south, 0.0 )
    if z > 6000.0:
        for c in ( WHEAT, BARLEY, STUBBLE, PLOUGH, SUNFLOWER, MAIZE, VINEYARD, OLIVES ):
            w[c] = 0.0
    total = 0.0
    for c in range( w.size ):
        total += w[c]
    r = _u( fid, 12 ) * total
    for c in range( w.size ):
        r -= w[c]
        if r < 0.0:
            return c
    return MEADOW


@numba.njit( cache=True, fastmath=True, inline="always" )
def _mix( a, b, t ):
    return a + ( b - a ) * t


@numba.njit( cache=True, fastmath=True )
def _flowers( E, N, wP, density, weights, r, g, b ):
    """ Flowers over grass: one in a cell 8 cm across here and there where a texel is that fine, their mean tint where
    it isn't. """
    cell = 0.08 * M
    mr = mg = mb = 0.0
    total = weights[0] + weights[1] + weights[2] + weights[3]
    for k in range( 4 ):
        mr += weights[k] / total * FLOWERS[k, 0]
        mg += weights[k] / total * FLOWERS[k, 1]
        mb += weights[k] / total * FLOWERS[k, 2]
    sharp = max( 1.0 - wP / ( 2.0 * cell ), 0.0 )
    rr = r + ( 1.0 - sharp ) * density * ( mr - r )
    gg = g + ( 1.0 - sharp ) * density * ( mg - g )
    bb = b + ( 1.0 - sharp ) * density * ( mb - b )
    if sharp > 0.0:
        h = _h( math.floor( E / cell ), math.floor( N / cell ), 4441 )
        if _u( h, 1 ) < density:
            pick = _u( h, 2 ) * total
            k = 0
            while k < 3 and pick > weights[k]:
                pick -= weights[k]
                k += 1
            rr += sharp * ( FLOWERS[k, 0] - r )
            gg += sharp * ( FLOWERS[k, 1] - g )
            bb += sharp * ( FLOWERS[k, 2] - b )
    return rr, gg, bb


# ---------------------------------------------------------------------------------------------------------------------
# What's at a point

@numba.njit( cache=True, fastmath=True )
def _use( e, n, E, N, s, w, wP, z, gx, gy, d, crop, ang, fid, fu, fv, dl, dr, db, dt, kl, kr, kb, kt, grads ):
    """ The ground at a point (plan e, n; played E, N; the forced perspective's scale s there, a texel's size w and its
    footprint where it's played, wP): its colour (linear), kind, the small relief the normal map adds (micro, in
    units), and the trees of each candidate layer there: ( type, how many a square unit where they're played ). Layer
    1's trees are planted: ( type, how many, the share of candidates that are kept, and the way from the point to its
    planting spot where it's played ). """
    slope = math.hypot( gx, gy )
    south = gy / max( slope, 1e-6 ) * V._smooth( 0.04, 0.18, slope )
    ca, sa = math.cos( ang ), math.sin( ang )
    seed = np.int64( fid & 4095 )
    q1 = V._fbm( E, N, 2600.0, 3, 0.5, 3000 + seed, wP, grads )
    q2 = V._fbm( E, N, 420.0, 3, 0.5, 5000 + seed, wP, grads )
    q3 = V._fbm( E, N, 70.0, 2, 0.5, 7001, wP, grads )
    tone = ( 0.92 + 0.16 * _u( fid, 11 ) ) * ( 1.0 + 0.09 * q1 + 0.06 * q2 + 0.05 * q3 )
    hue = _u( fid, 13 ) - 0.5
    r, g, b = CROP_COLOURS[crop, 0], CROP_COLOURS[crop, 1], CROP_COLOURS[crop, 2]
    kind = GRASS
    micro = 0.0
    t0, n0 = -1, 0.0
    t1, n1, a1, s1e, s1n = -1, 0.0, 0.0, 0.0, 0.0
    t2, n2 = -1, 0.0
    off = _u( fid, 17 )
    flower, fw = 0.0, MEADOW_FLOWERS

    if crop == WHEAT or crop == BARLEY:
        ripe = min( max( _u( fid, 14 ) + 0.3 * q1, 0.0 ), 1.0 )
        if crop == WHEAT:
            r, g, b = _mix( WHEAT_GREEN[0], WHEAT_GOLD[0], ripe ), _mix( WHEAT_GREEN[1], WHEAT_GOLD[1], ripe ), \
                _mix( WHEAT_GREEN[2], WHEAT_GOLD[2], ripe )
        else:
            r, g, b = _mix( r, STRAW[0], 0.3 * ripe ), _mix( g, STRAW[1], 0.3 * ripe ), _mix( b, STRAW[2], 0.3 * ripe )
        # Tramlines along the rows every 24 m: two wheel tracks 1.8 m apart, soil showing.
        o = off * 24.0 * M
        tram = _stripes( fv - o + 1.125 * M, 24.0 * M, 0.45 * M, wP ) + _stripes( fv - o - 0.675 * M, 24.0 * M, 0.45 * M, wP )
        r, g, b = _mix( r, SOIL_COLOUR[0] * 0.8, 0.6 * tram ), _mix( g, SOIL_COLOUR[1] * 0.8, 0.6 * tram ), \
            _mix( b, SOIL_COLOUR[2] * 0.8, 0.6 * tram )
        flower, fw = 0.006 * V._smooth( 0.2, 0.7, q2 ), POPPIES
    elif crop == STUBBLE:
        swath = _stripes( fv - off * 7.5 * M, 7.5 * M, 1.6 * M, wP )
        tone *= 0.96 + 0.16 * swath
        t2, n2 = BALE, 25.0 / HECTARE
    elif crop == HAY:
        row = _stripes( fv - off * 7.0 * M, 7.0 * M, 1.3 * M, wP )
        r, g, b = _mix( r, HAY_ROW[0], 0.8 * row ), _mix( g, HAY_ROW[1], 0.8 * row ), _mix( b, HAY_ROW[2], 0.8 * row )
        t2, n2 = BALE, 12.0 / HECTARE
    elif crop == MEADOW:
        flower = 0.05 * V._smooth( -0.1, 0.6, q2 )
        t0, n0 = OAK, 1.5 / HECTARE
        t2, n2 = CYPRESS, 0.4 / HECTARE
    elif crop == PASTURE:
        tone *= 1.0 + 0.06 * q3
        flower = 0.015
        t0, n0 = OAK, 2.0 / HECTARE
    elif crop == PLOUGH:
        kind = SOIL
        tone = ( 0.9 + 0.2 * _u( fid, 11 ) ) * ( 1.0 + 0.16 * q1 + 0.08 * q2 + 0.09 * q3 )
        if _u( fid, 15 ) < 0.4:            # harrowed: finer, drier
            r, g, b = _mix( r, DRY_SOIL[0], 0.5 ), _mix( g, DRY_SOIL[1], 0.5 ), _mix( b, DRY_SOIL[2], 0.5 )
        else:                               # furrows across the field, 36 cm apart
            period = 0.36 * M
            fade = 1.0 - V._smooth( period * 0.2, period * 0.5, wP )
            if fade > 0.0:
                wave = math.sin( 2.0 * math.pi * fv / period )
                micro += fade * 0.07 * M / s * wave
                tone *= 1.0 + 0.05 * fade * wave
    elif crop == FALLOW:
        green = V._smooth( -0.4, 0.4, q1 + 0.6 * q2 )
        r, g, b = _mix( r, GREEN_GRASS[0], 0.5 * green ), _mix( g, GREEN_GRASS[1], 0.5 * green ), \
            _mix( b, GREEN_GRASS[2], 0.5 * green )
        flower, fw = 0.08 * V._smooth( 0.0, 0.6, q2 ), POPPIES
        t2, n2 = SHRUB, 8.0 / HECTARE
    elif crop == SUNFLOWER or crop == MAIZE:
        width = 0.5 * M if crop == SUNFLOWER else 0.6 * M
        rows = _stripes( fv - off * 0.75 * M, 0.75 * M, width, wP )
        r, g, b = _mix( SOIL_COLOUR[0], r, rows ), _mix( SOIL_COLOUR[1], g, rows ), _mix( SOIL_COLOUR[2], b, rows )
    elif crop == VINEYARD:
        along_u = _u( fid, 16 ) < 0.6
        x = fv if along_u else fu
        across_e, across_n = ( -sa, ca ) if along_u else ( ca, sa )
        # The ground between the rows: grass, or tilled.
        if _u( fid, 18 ) < 0.45:
            r, g, b = SOIL_COLOUR[0], SOIL_COLOUR[1], SOIL_COLOUR[2]
            kind = SOIL
        period = 2.6 * M
        cw = 0.9 * M
        o = off * period
        canopy = _stripes( x - o, period, cw, wP )
        # Each row throws a shadow onto the ground beside it, away from the sun.
        sc = SUN_PLAN[0] * across_e + SUN_PLAN[1] * across_n
        ws = min( 1.5 * M * V.SHADOW_LENGTH * abs( sc ), period - cw )
        if sc > 0.0:
            shade = _stripes( x - o + ws, period, ws, wP )
        else:
            shade = _stripes( x - o - cw, period, ws, wP )
        lit = max( 1.0 - canopy - shade, 0.0 )
        r = canopy * VINE[0] + ( lit + shade * SHADOW_TINT[0] ) * r
        g = canopy * VINE[1] + ( lit + shade * SHADOW_TINT[1] ) * g
        b = canopy * VINE[2] + ( lit + shade * SHADOW_TINT[2] ) * b
        tone = 1.0 + 0.05 * q1 + 0.04 * q2
        if canopy > 0.5:
            kind = GRASS
    elif crop == OLIVES or crop == POPLARS:
        if crop == OLIVES and _u( fid, 18 ) < 0.4:
            r, g, b = SOIL_COLOUR[0], SOIL_COLOUR[1], SOIL_COLOUR[2]
            kind = SOIL
        sp = 6.5 * M if crop == OLIVES else 6.0 * M
        ou, ov = off * sp, _u( fid, 19 ) * sp
        iu = math.floor( ( fu - ou ) / sp + 0.5 )
        iv = math.floor( ( fv - ov ) / sp + 0.5 )
        node = _h( _h( fid, iu, 71 ), iv, 73 )
        jit = 0.35 * M if crop == OLIVES else 0.12 * M
        du = ou + iu * sp - fu + jit * ( 2.0 * _u( node, 1 ) - 1.0 )
        dv_ = ov + iv * sp - fv + jit * ( 2.0 * _u( node, 2 ) - 1.0 )
        room = min( min( dl + du, dr - du ), min( db + dv_, dt - dv_ ) )
        t1 = OLIVE if crop == OLIVES else POPLAR
        n1 = 1.0 / ( sp * sp )
        a1 = 1.0 if room > 2.6 * M and _u( node, 3 ) > 0.06 else 0.0
        s1e, s1n = du * ca - dv_ * sa, du * sa + dv_ * ca
    elif crop == WOOD:
        t0, n0 = ( HOLM if q1 + 0.6 * south > 0.2 else OAK ), 0.0
        n0 = -math.log( 1.0 - 0.9 ) / ( math.pi * TREES[t0, 0] * TREES[t0, 0] )

    r *= tone * ( 1.0 + 0.08 * hue )
    g *= tone
    b *= tone * ( 1.0 - 0.1 * hue )
    if flower > 0.0:
        r, g, b = _flowers( E, N, wP, flower, fw, r, g, b )

    # The field's edges: the nearest one's strip, if the point's in it.
    best, kind_e, de_ = 0.0, -1, 0.0
    for k in range( 4 ):
        dk = dl if k == 0 else ( dr if k == 1 else ( db if k == 2 else dt ) )
        kk = kl if k == 0 else ( kr if k == 1 else ( kb if k == 2 else kt ) )
        cov = _box( EDGE_HALF[kk] - dk, wP )
        if cov > best:
            best, kind_e, de_ = cov, kk, dk
    if best > 0.0 and crop != WOOD:
        mr, mg, mb = MARGIN[0], MARGIN[1], MARGIN[2]
        mk = GRASS
        if kind_e == EDGE_TRACK:
            # Two ruts with grass between them and along the verges.
            rut = _box( 0.85 * M - de_, wP ) - _box( 0.35 * M - de_, wP )
            mr, mg, mb = _mix( mr, DUST[0], 0.4 + 0.6 * rut ), _mix( mg, DUST[1], 0.4 + 0.6 * rut ), \
                _mix( mb, DUST[2], 0.4 + 0.6 * rut )
            mk = SOIL if rut > 0.5 else GRASS
            micro -= 0.06 * M / s * rut
        elif kind_e == EDGE_HEDGE:
            mr, mg, mb = UNDERGROWTH[0], UNDERGROWTH[1], UNDERGROWTH[2]
            t2, n2 = SHRUB, -math.log( 1.0 - 0.85 ) / ( math.pi * TREES[SHRUB, 0] ** 2 )
            t0, n0 = OAK, 1.0 / ( 22.0 * M * 2.0 * EDGE_HALF[EDGE_HEDGE] )
            t1, n1, a1 = -1, 0.0, 0.0
        elif kind_e == EDGE_DITCH:
            mr, mg, mb = DITCH[0], DITCH[1], DITCH[2]
            micro -= 0.35 * M / s * max( 1.0 - de_ / EDGE_HALF[EDGE_DITCH], 0.0 ) * best
        elif kind_e == EDGE_TREES:
            t0, n0 = OAK, 1.0 / ( 14.0 * M * 2.0 * EDGE_HALF[EDGE_TREES] )
            t1, n1, a1 = -1, 0.0, 0.0
        if kind_e == EDGE_PLAIN or kind_e == EDGE_TREES:
            mr, mg, mb = _flowers( E, N, wP, 0.04, MEADOW_FLOWERS, mr, mg, mb )
        mt = 1.0 + 0.06 * q2 + 0.06 * q3
        r, g, b = _mix( r, mr * mt, best ), _mix( g, mg * mt, best ), _mix( b, mb * mt, best )
        if best > 0.5:
            kind = mk

    # Woods: patches kilometres across where they're played, more on steep and high ground and on the mountains, none
    # on the town's own hill; ragged at the edges.
    wv = 0.85 * V._fbm( E, N, 170000.0, 4, 0.5, 501, wP, grads )
    wv += 0.6 * V._smooth( 0.18, 0.55, slope ) + 0.35 * V._smooth( -1500.0, 3500.0, z )
    wv += 0.5 * V._smooth( 42000.0, 62000.0, d ) - 0.8 * ( 1.0 - V._smooth( 2500.0, 9000.0, d ) )
    wv += 0.2 * V._fbm( E, N, 21000.0, 3, 0.55, 502, wP, grads )
    woods = wv > 0.42 or crop == WOOD
    if woods:
        species = HOLM if V._fbm( E, N, 30000.0, 2, 0.5, 503, wP, grads ) + 0.6 * south - 0.5 * V._smooth( 0.0, 4000.0, z ) > 0.15 else OAK
        if d > 42000.0 and z > 3000.0:
            species = BEECH
        cover = min( max( 0.86 + 0.12 * q2 - 0.25 * V._smooth( 0.7, 1.3, slope ), 0.55 ), 0.96 )
        t0, n0 = species, -math.log( 1.0 - cover ) / ( math.pi * TREES[species, 0] * TREES[species, 0] )
        t1, n1, a1, t2, n2 = -1, 0.0, 0.0, -1, 0.0
        wt = 1.0 + 0.1 * q2 + 0.08 * q3
        r, g, b = WOOD_FLOOR[0] * wt, WOOD_FLOOR[1] * wt, WOOD_FLOOR[2] * wt
        kind = GRASS

    # Too steep for fields: scrub, then rock. Woods hold on to steep slopes until the rock comes through.
    if slope > 0.55:
        rock = V._smooth( 0.95, 1.4, slope + 0.15 * q2 )
        scrub = V._smooth( 0.55, 0.75, slope ) * ( 1.0 - rock )
        if scrub > 0.0 and not woods:
            r, g, b = _mix( r, DRY_GRASS[0], scrub ), _mix( g, DRY_GRASS[1], scrub ), _mix( b, DRY_GRASS[2], scrub )
            t2, n2 = SHRUB, -math.log( 1.0 - 0.45 * scrub ) / ( math.pi * TREES[SHRUB, 0] ** 2 )
            t0, n0 = HOLM, -math.log( 1.0 - 0.2 * scrub ) / ( math.pi * TREES[HOLM, 0] ** 2 )
            t1, n1, a1 = -1, 0.0, 0.0
        if rock > 0.0:
            rt = 1.0 + 0.12 * q2 + 0.1 * q3
            rr, rg, rb = _mix( ROCK[0], SCREE[0], 0.5 + 0.5 * q1 ), _mix( ROCK[1], SCREE[1], 0.5 + 0.5 * q1 ), \
                _mix( ROCK[2], SCREE[2], 0.5 + 0.5 * q1 )
            r, g, b = _mix( r, rr * rt, rock ), _mix( g, rg * rt, rock ), _mix( b, rb * rt, rock )
            micro += rock * 0.25 * M / s * V._fbm( E, N, 4.0 * M, 3, 0.5, 504, wP, grads )
            if rock > 0.5:
                kind = STONE
                t0, n0, t1, n1, a1 = -1, 0.0, -1, 0.0, 0.0
                t2, n2 = SHRUB, 30.0 / HECTARE

    # The olive terraces on the town's own hill, behind dry-stone walls.
    if FOOT < d < TERRACE_REACH + 800.0 and 0.1 < slope < 1.3:
        reach = TERRACE_REACH + 700.0 * V._fbm( e, n, 3000.0, 2, 0.5, 9100, w, grads )
        if d < reach:
            bench = TERRACE_STEP / slope                         # a terrace's width
            f = V._height( e, n, 600.0, grads ) / TERRACE_STEP
            level = math.floor( f )
            f -= level
            riser = min( 0.5 * M / bench, 0.3 )
            sharp = V._smooth( 4.0, 10.0, bench / w )
            if f < 1.0 - riser:
                profile = 0.1 * f / ( 1.0 - riser )
            else:
                profile = 0.1 + 0.9 * ( f - ( 1.0 - riser ) ) / riser
            micro += sharp * TERRACE_STEP * ( profile - f )
            hl = _h( level, 0, 8101 )
            pick = _u( hl, 1 )
            if pick < 0.6:
                tr, tg, tb = DRY_GRASS[0], DRY_GRASS[1], DRY_GRASS[2]
                kind = GRASS
            elif pick < 0.85:
                tr, tg, tb = SOIL_COLOUR[0], SOIL_COLOUR[1], SOIL_COLOUR[2]
                kind = SOIL
            else:
                tr, tg, tb = GREEN_GRASS[0], GREEN_GRASS[1], GREEN_GRASS[2]
                kind = GRASS
            tt = 1.0 + 0.08 * q2 + 0.07 * q3
            r, g, b = tr * tt, tg * tt, tb * tt
            if kind == GRASS:
                r, g, b = _flowers( e, n, w, 0.03, MEADOW_FLOWERS, r, g, b )
            # The wall: its face, and its top's capstones just above.
            x = f * bench
            face = _stripes( x - ( 1.0 - riser ) * bench, bench, riser * bench, w )
            cap = _stripes( x - ( 1.0 - riser - 0.06 ) * bench, bench, 0.06 * bench, w ) * sharp
            wt = 1.0 + 0.1 * V._fbm( e, n, 0.6 * M, 2, 0.5, 8102, w, grads )
            r = _mix( _mix( r, WALL_TOP[0] * wt, cap ), WALL_STONE[0] * wt, face )
            g = _mix( _mix( g, WALL_TOP[1] * wt, cap ), WALL_STONE[1] * wt, face )
            b = _mix( _mix( b, WALL_TOP[2] * wt, cap ), WALL_STONE[2] * wt, face )
            if face > 0.5:
                kind = STONE
            # Olives along each terrace's middle, planted where they're played (here, where they stand).
            t0, n0, t2, n2 = -1, 0.0, -1, 0.0
            t1 = OLIVE
            n1 = 1.0 / ( 6.0 * M * bench )
            a1 = 0.45 if bench > 3.0 * M else 0.0
            way = ( 0.45 - f ) * bench / slope                 # uphill along the gradient, scaled to its length
            s1e, s1n = way * gx, way * gy

    # The river: water in the middle of its bed, gravel either side, poplars and willows along its banks.
    reach = 1.0 - V._smooth( V.RIVER_REACH[0], V.RIVER_REACH[1], abs( e ) )
    if reach > 0.0:
        dv = V._valley_offset( e, n )
        if dv < V.RIVER_SWING + V.RIVER_BED + BANK_WIDTH:
            dr_ = V._river_distance( e, n )
            water = V.RIVER_BED * ( 0.55 + 0.15 * V._fbm( e, n, 5000.0, 2, 0.5, 9300, w, grads ) )
            if dr_ < V.RIVER_BED * 1.1:
                wet = _box( water - dr_, w )
                gt = 1.0 + 0.1 * V._fbm( e, n, 3.0 * M, 3, 0.5, 9301, w, grads )
                deep = min( max( 1.0 - dr_ / water, 0.0 ), 1.0 )
                wr, wg, wb = _mix( WATER_EDGE[0], WATER_DEEP[0], deep ), _mix( WATER_EDGE[1], WATER_DEEP[1], deep ), \
                    _mix( WATER_EDGE[2], WATER_DEEP[2], deep )
                bed = _box( V.RIVER_BED - dr_, w )
                r = _mix( _mix( r, GRAVEL[0] * gt, bed ), wr, wet )
                g = _mix( _mix( g, GRAVEL[1] * gt, bed ), wg, wet )
                b = _mix( _mix( b, GRAVEL[2] * gt, bed ), wb, wet )
                kind = WATER if wet > 0.5 else ( SOIL if bed > 0.5 else kind )
                t0, n0, t1, n1, a1, t2, n2 = -1, 0.0, -1, 0.0, 0.0, -1, 0.0
                micro = 0.0
            elif dr_ < V.RIVER_BED + BANK_WIDTH * reach:
                cover = min( max( 0.55 + 0.4 * V._fbm( e, n, 2500.0, 2, 0.5, 9302, w, grads ), 0.0 ), 0.92 )
                t0 = POPLAR if V._fbm( e, n, 4000.0, 2, 0.5, 9303, w, grads ) > 0.0 else WILLOW
                n0 = -math.log( 1.0 - cover ) / ( math.pi * TREES[t0, 0] ** 2 )
                t1, n1, a1, t2, n2 = -1, 0.0, 0.0, SHRUB, -math.log( 1.0 - 0.3 ) / ( math.pi * TREES[SHRUB, 0] ** 2 )
                bt = 1.0 + 0.08 * q2
                r, g, b = BANK[0] * bt, BANK[1] * bt, BANK[2] * bt
                kind = GRASS

    # The grass along the walls' foot.
    if d < FOOT:
        ft = 1.0 + 0.08 * q2 + 0.06 * q3
        r, g, b = _flowers( e, n, w, 0.02, MEADOW_FLOWERS, FOOT_GRASS[0] * ft, FOOT_GRASS[1] * ft, FOOT_GRASS[2] * ft )
        kind = GRASS
        micro = 0.0
        t0, n0, t1, n1, a1, t2, n2 = -1, 0.0, -1, 0.0, 0.0, -1, 0.0

    return r, g, b, kind, micro, t0, n0, t1, n1, a1, s1e, s1n, t2, n2


@numba.njit( cache=True, fastmath=True )
def _site( e, n, grads ):
    """ A plan point's apparent place, scale and stretch, and how far out from the town it is. """
    d = V._town_offset( e, n )[0]
    ap = V._apparent( e, n )
    return d, ap[0], ap[1], ap[2], _stretch( ap[3], ap[4], ap[5], ap[6] )


@numba.njit( cache=True, fastmath=True )
def _field_crop( E, N, ang, fid, dl, dr, db, dt, region, grads ):
    """ A field's crop, by the land at its middle. """
    du, dv = 0.5 * ( dr - dl ), 0.5 * ( dt - db )
    ca, sa = math.cos( ang ), math.sin( ang )
    ec, nc = _real_place( E + du * ca - dv * sa, N + du * sa + dv * ca )
    zc = V._height( ec, nc, 800.0, grads )
    gxc = ( V._height( ec + 400.0, nc, 800.0, grads ) - zc ) / 400.0
    gyc = ( V._height( ec, nc + 400.0, 800.0, grads ) - zc ) / 400.0
    reach = 1.0 - V._smooth( V.RIVER_REACH[0], V.RIVER_REACH[1], abs( ec ) )
    return _crop( fid, region, zc, gxc, gyc, V._valley_offset( ec, nc ), reach )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _mean_trees( t, nn, cell, s, w, sigma, r, g, b, alpha, shade, grads, e, n ):
    """ Trees too small to draw, as their mean, over what's under them so far: ( the canopy's colour (premultiplied),
    its share, and how much of the open ground between is lit ). """
    if t < 0 or nn <= 0.0:
        return r, g, b, alpha, shade
    nn = min( nn, 1.0 / ( cell * cell ) )
    rad = TREES[t, 0]
    f = V._smooth( PX_MIN, PX_FULL, 2.0 * rad / ( s * w ) )
    if f >= 1.0:
        return r, g, b, alpha, shade
    cover = 1.0 - math.exp( -nn * math.pi * rad * rad )
    c = cover * ( 1.0 - f )
    # The canopy's grain: as many crowns as fall in a texel make it smoother.
    many = nn * w * w * s * sigma
    grain = 1.0 + 0.4 / math.sqrt( 1.0 + many ) * V._fbm( e, n, 5.0 * w, 2, 0.5, 4242, w, grads )
    m = CROWN_MEAN * ( 1.0 - 0.3 * cover ) * grain
    r = r * ( 1.0 - c ) + TREE_COLOURS[t, 0] * m * c
    g = g * ( 1.0 - c ) + TREE_COLOURS[t, 1] * m * c
    b = b * ( 1.0 - c ) + TREE_COLOURS[t, 2] * m * c
    alpha = 1.0 - ( 1.0 - alpha ) * ( 1.0 - c )
    shaded = 1.0 - math.exp( -cover * SPREAD[t] / max( 1.0 - cover, 0.05 ) )
    shade *= 1.0 - shaded * ( 1.0 - f ) * TREES[t, 3]
    return r, g, b, alpha, shade


@numba.njit( parallel=True, cache=True, fastmath=True )
def _paint( es, ns, Z, GX, GY, w, grads, ground, kind, micro, over, alpha, shade ):
    """ Every texel's ground, and the mean of the trees too small to draw there. """
    rows, cols = Z.shape
    we, wn = es[1] - es[0], ns[0] - ns[1]
    for row in numba.prange( rows ):
        n = ns[row]
        last_dh = np.int64( -1 )
        region = 0
        last_fid = np.int64( -1 )
        crop = 0
        for col in range( cols ):
            e = es[col]
            d, E, N, s, sigma = _site( e, n, grads )
            wP = w * sigma
            dh, de, dn = _district( E, N )
            if dh != last_dh:
                region = _region( dh, de, dn, grads )
                last_dh = dh
            u, v, ang = _frame( E, N, dh, de, dn, grads )
            fid, fu, fv, dl, dr, db, dt, kl, kr, kb, kt = _cell( u, v, dh )
            if fid != last_fid:
                crop = _field_crop( E, N, ang, fid, dl, dr, db, dt, region, grads )
                last_fid = fid
            res = _use( e, n, E, N, s, w, wP, Z[row, col], GX[row, col], GY[row, col], d, crop, ang, fid, fu, fv,
                        dl, dr, db, dt, kl, kr, kb, kt, grads )
            ground[row, col, 0] = res[0]
            ground[row, col, 1] = res[1]
            ground[row, col, 2] = res[2]
            kind[row, col] = res[3]
            micro[row, col] = res[4]
            r, g, b, al, sh = 0.0, 0.0, 0.0, 0.0, 1.0
            r, g, b, al, sh = _mean_trees( res[5], res[6], LAYER_CELL[0], s, w, sigma, r, g, b, al, sh, grads, e, n )
            r, g, b, al, sh = _mean_trees( res[7], res[8] * res[9], LAYER_CELL[1], s, w, sigma, r, g, b, al, sh, grads,
                                           e, n )
            r, g, b, al, sh = _mean_trees( res[12], res[13], LAYER_CELL[2], s, w, sigma, r, g, b, al, sh, grads, e, n )
            over[row, col, 0] = r
            over[row, col, 1] = g
            over[row, col, 2] = b
            alpha[row, col] = al
            shade[row, col] = sh


# ---------------------------------------------------------------------------------------------------------------------
# The trees big enough to draw: candidates on grids where they're played (the same in every zone), each kept by what
# grows there

CROWN_FIELDS = 12           # e, n, ground z, radius, crown's middle, half-height, type, r, g, b, shadow opacity, seed


@numba.njit( cache=True, fastmath=True, inline="always" )
def _land( e, n, grads ):
    """ The land's height and slope where trees are decided. """
    z = V._height( e, n, DECIDE_CUTOFF, grads )
    gx = ( V._height( e + DECIDE_STEP, n, DECIDE_CUTOFF, grads ) - z ) / DECIDE_STEP
    gy = ( V._height( e, n + DECIDE_STEP, DECIDE_CUTOFF, grads ) - z ) / DECIDE_STEP
    return z, gx, gy


@numba.njit( cache=True, fastmath=True )
def _decide( e, n, grads ):
    """ What grows at a plan point, as the trees are decided: ( the forced perspective's scale there, the ground's
    height, and _use's answer ). """
    d, E, N, s, sigma = _site( e, n, grads )
    z, gx, gy = _land( e, n, grads )
    dh, de, dn = _district( E, N )
    region = _region( dh, de, dn, grads )
    u, v, ang = _frame( E, N, dh, de, dn, grads )
    fid, fu, fv, dl, dr, db, dt, kl, kr, kb, kt = _cell( u, v, dh )
    crop = _field_crop( E, N, ang, fid, dl, dr, db, dt, region, grads )
    res = _use( e, n, E, N, s, DECIDE_W, DECIDE_W * sigma, z, gx, gy, d, crop, ang, fid, fu, fv, dl, dr, db, dt,
                kl, kr, kb, kt, grads )
    return s, z, res


@numba.njit( parallel=True, cache=True, fastmath=True )
def _candidates( layer, g, i0, j0, out, dmin, dmax, Z, e0, n0, we, wn, w, grads ):
    """ The crowns kept from layer's candidates in cells i0.., j0.. (out's shape): one per cell at most, nan if none. """
    rows_c, cols_c = out.shape[0], out.shape[1]
    rows, cols = Z.shape
    for jj in numba.prange( rows_c ):
        j = j0 + jj
        last_dh = np.int64( -1 )
        region = 0
        last_fid = np.int64( -1 )
        crop = 0
        for ii in range( cols_c ):
            out[jj, ii, 0] = np.nan
            i = i0 + ii
            h = _h( i, j, 1000 + layer )
            pe = ( i + 0.1 + 0.8 * _u( h, 1 ) ) * g
            pn = ( j + 0.1 + 0.8 * _u( h, 2 ) ) * g
            e, n = _real_place( pe, pn )
            d, E, N, s, sigma = _site( e, n, grads )
            if d < dmin or d > dmax:
                continue
            x, y = ( e - e0 ) / we, ( n0 - n ) / wn
            if x < 0.0 or y < 0.0 or x > cols - 1.0 or y > rows - 1.0:
                continue
            z, gx, gy = _land( e, n, grads )
            dh, de, dn = _district( E, N )
            if dh != last_dh:
                region = _region( dh, de, dn, grads )
                last_dh = dh
            u, v, ang = _frame( E, N, dh, de, dn, grads )
            fid, fu, fv, dl, dr, db, dt, kl, kr, kb, kt = _cell( u, v, dh )
            if fid != last_fid:
                crop = _field_crop( E, N, ang, fid, dl, dr, db, dt, region, grads )
                last_fid = fid
            res = _use( e, n, E, N, s, DECIDE_W, DECIDE_W * sigma, z, gx, gy, d, crop, ang, fid, fu, fv, dl, dr, db, dt,
                        kl, kr, kb, kt, grads )
            t = res[5] if layer == 0 else ( res[7] if layer == 1 else res[12] )
            nn = res[6] if layer == 0 else ( res[8] if layer == 1 else res[13] )
            if t < 0 or nn <= 0.0:
                continue
            keep = V._smooth( PX_MIN, PX_FULL, 2.0 * TREES[t, 0] / ( s * w ) )
            if keep <= 0.0:
                continue
            if layer == 1:
                # Planted: move to the planting spot, which only the cell it falls in keeps. The spot comes from the
                # field's grid, which the rows' bending makes only near enough from a step away: twice more from the
                # spot itself finds it to a few millimetres, wherever the candidate started.
                pe2, pn2 = pe + res[10], pn + res[11]
                if math.floor( pe2 / g ) != i or math.floor( pn2 / g ) != j:
                    continue
                if _u( h, 3 ) >= res[9] * keep:
                    continue
                lost = False
                for _ in range( 2 ):
                    e, n = _real_place( pe2, pn2 )
                    s, z, again = _decide( e, n, grads )
                    if again[7] != t or again[9] <= 0.0:
                        lost = True
                        break
                    pe2, pn2 = pe2 + again[10], pn2 + again[11]
                if lost or math.floor( pe2 / g ) != i or math.floor( pn2 / g ) != j:
                    continue
                e, n = _real_place( pe2, pn2 )
                d, E, N, s, sigma = _site( e, n, grads )
                x, y = ( e - e0 ) / we, ( n0 - n ) / wn
                if x < 0.0 or y < 0.0 or x > cols - 1.0 or y > rows - 1.0:
                    continue
                z = _land( e, n, grads )[0]
            elif _u( h, 3 ) >= nn * g * g * keep:
                continue
            size = 0.78 + 0.44 * _u( h, 4 )
            tall = 0.85 + 0.3 * _u( h, 5 )
            bright = 0.84 + 0.32 * _u( h, 6 )
            green = 0.94 + 0.12 * _u( h, 7 )
            out[jj, ii, 0] = e
            out[jj, ii, 1] = n
            out[jj, ii, 2] = z
            out[jj, ii, 3] = TREES[t, 0] * size / s
            out[jj, ii, 4] = TREES[t, 1] * tall / s
            out[jj, ii, 5] = TREES[t, 2] * tall * ( 0.9 + 0.2 * _u( h, 8 ) ) / s
            out[jj, ii, 6] = t
            out[jj, ii, 7] = TREE_COLOURS[t, 0] * bright
            out[jj, ii, 8] = TREE_COLOURS[t, 1] * bright * green
            out[jj, ii, 9] = TREE_COLOURS[t, 2] * bright
            out[jj, ii, 10] = TREES[t, 3]
            out[jj, ii, 11] = _u( h, 9 ) * 1000.0


def crowns_for( zone, margin, es, ns, Z, w, inner ):
    """ Every crown big enough to draw in a zone: ( count, CROWN_FIELDS ). inner is the out-distance inside which the
    zone is never shown. """
    we, wn = es[1] - es[0], ns[0] - ns[1]
    e0, n0 = es[0], ns[0]
    out = []
    dmin = max( inner - 2000.0, 0.0 )
    for layer, kinds in enumerate( ( ( OAK, HOLM, POPLAR, WILLOW, PINE, BEECH ), ( OLIVE, POPLAR ),
                                     ( SHRUB, CYPRESS, BALE ) ) ):
        g = float( LAYER_CELL[layer] )
        # The furthest out any of this layer's trees could be drawn: where the biggest is PX_MIN texels across.
        biggest = float( max( TREES[k, 0] for k in kinds ) )
        reach = np.linspace( 0, margin * 1.5, 4000 )
        drawn = 2 * biggest / ( V.scale( reach ) * w ) >= PX_MIN
        if not drawn.any() or reach[drawn].max() + 100.0 <= dmin:
            continue
        dmax = float( reach[drawn].max() ) + 100.0
        # The candidates' cells: round the apparent places of the zone's ground within dmax.
        ge, gn = np.meshgrid( np.linspace( es[0], es[-1], 512 ), np.linspace( ns[-1], ns[0], 512 ) )
        near = V.town_distance( ge, gn ) <= dmax
        pe, pn, _ = V.apparent( ge[near], gn[near] )
        i0, i1 = int( math.floor( pe.min() / g ) ) - 2, int( math.ceil( pe.max() / g ) ) + 2
        j0, j1 = int( math.floor( pn.min() / g ) ) - 2, int( math.ceil( pn.max() / g ) ) + 2
        t0 = time.time()
        kept = 0
        chunk = max( 1, int( 1e6 // max( i1 - i0, 1 ) ) )
        for j in range( j0, j1, chunk ):
            block = np.empty( ( min( chunk, j1 - j ), i1 - i0, CROWN_FIELDS ) )
            _candidates( layer, g, i0, j, block, dmin, dmax, Z, e0, n0, we, wn, w, V._GRADIENTS )
            found = block[~np.isnan( block[:, :, 0] )]
            kept += len( found )
            out.append( found )
        print( f"  zone {zone} layer {layer}: {( i1 - i0 ) * ( j1 - j0 ) / 1e6:.1f}M candidates, {kept} crowns "
               f"in {time.time() - t0:.1f} s" )
    return np.concatenate( out ) if out else np.empty( ( 0, CROWN_FIELDS ) )


@numba.njit( cache=True, fastmath=True )
def _tops( crowns, e0, n0, we, wn, w, top, ccol, cov, cid, grads ):
    """ Each crown's top over the ground: where it's the highest thing, its colour, lit as a spheroid (lumpy where it's
    big enough to show its clumps of leaves). A crown with no colour (-1) is a prop's: its model draws it. """
    rows, cols = top.shape
    for k in range( crowns.shape[0] ):
        if crowns[k, 7] < 0.0:
            continue
        ce, cn, zg, a, hc, bb = crowns[k, 0], crowns[k, 1], crowns[k, 2], crowns[k, 3], crowns[k, 4], crowns[k, 5]
        c0 = max( int( ( ce - a - e0 ) / we ) - 1, 0 )
        c1 = min( int( ( ce + a - e0 ) / we ) + 1, cols - 1 )
        r0 = max( int( ( n0 - ( cn + a ) ) / wn ) - 1, 0 )
        r1 = min( int( ( n0 - ( cn - a ) ) / wn ) + 1, rows - 1 )
        lumpy = V._smooth( 3.0, 8.0, a / w )
        seed = np.int64( crowns[k, 11] )
        for row in range( r0, r1 + 1 ):
            dy = n0 - row * wn - cn
            for col in range( c0, c1 + 1 ):
                dx = e0 + col * we - ce
                rr = math.sqrt( dx * dx + dy * dy )
                cv = min( max( ( a - rr ) / w + 0.5, 0.0 ), 1.0 )
                if cv <= 0.0:
                    continue
                rho2 = min( rr * rr / ( a * a ), 1.0 )
                hz = hc + bb * math.sqrt( 1.0 - rho2 )
                if cid[row, col] >= 0 and zg + hz <= top[row, col]:
                    continue
                nx, ny, nz = dx / ( a * a ), dy / ( a * a ), ( hz - hc ) / ( bb * bb )
                ln = math.sqrt( nx * nx + ny * ny + nz * nz )
                nx, ny, nz = nx / ln, ny / ln, nz / ln
                if lumpy > 0.0:
                    lx = V._gradient_noise( dx / ( 0.35 * a ), dy / ( 0.35 * a ), seed, grads )
                    ly = V._gradient_noise( dx / ( 0.35 * a ) + 17.3, dy / ( 0.35 * a ) - 5.1, seed, grads )
                    nx += 0.45 * lumpy * lx
                    ny += 0.45 * lumpy * ly
                    ln = math.sqrt( nx * nx + ny * ny + nz * nz )
                    nx, ny, nz = nx / ln, ny / ln, nz / ln
                lit = max( nx * V.SUN[0] + ny * V.SUN[1] + nz * V.SUN[2], 0.0 )
                sky = 0.75 + 0.25 * nz
                # The leaves' grain, finer than the clumps.
                grain = 1.0
                if lumpy > 0.0:
                    grain += 0.12 * lumpy * V._gradient_noise( dx / ( 0.1 * a ), dy / ( 0.1 * a ), seed + 5, grads )
                old = cov[row, col]
                for c in range( 3 ):
                    sh = min( ( AMBIENT[c] * sky + SUN_RGB[c] * LEAF_SUN * lit ) / FLAT_LIT[c], SHADE_MAX ) * grain
                    ccol[row, col, c] = ccol[row, col, c] * ( 1.0 - cv ) + crowns[k, 7 + c] * sh * cv
                cov[row, col] = 1.0 - ( 1.0 - old ) * ( 1.0 - cv )
                if cv >= 0.5:
                    top[row, col] = zg + hz
                    cid[row, col] = k


@numba.njit( cache=True, fastmath=True )
def _shadows( crowns, e0, n0, we, wn, w, top, cid, shadow ):
    """ Where each crown keeps the sun off: a ray from each texel's surface towards the sun, against the crown's
    spheroid, soft over its last part. """
    rows, cols = top.shape
    lx, ly, lz = V.SUN[0], V.SUN[1], V.SUN[2]
    away_e, away_n = -SUN_PLAN[0], -SUN_PLAN[1]
    for k in range( crowns.shape[0] ):
        ce, cn, zg, a, hc, bb = crowns[k, 0], crowns[k, 1], crowns[k, 2], crowns[k, 3], crowns[k, 4], crowns[k, 5]
        opacity = crowns[k, 10]
        reach = ( hc + bb ) * V.SHADOW_LENGTH * 1.8
        emin = min( ce - a, ce - a + away_e * reach )
        emax = max( ce + a, ce + a + away_e * reach )
        nmin = min( cn - a, cn - a + away_n * reach )
        nmax = max( cn + a, cn + a + away_n * reach )
        c0 = max( int( ( emin - e0 ) / we ) - 1, 0 )
        c1 = min( int( ( emax - e0 ) / we ) + 1, cols - 1 )
        r0 = max( int( ( n0 - nmax ) / wn ) - 1, 0 )
        r1 = min( int( ( n0 - nmin ) / wn ) + 1, rows - 1 )
        kz = a / bb
        dz_ = lz * kz
        dd = lx * lx + ly * ly + dz_ * dz_
        soft = max( 0.8 * w, 0.1 * a )
        for row in range( r0, r1 + 1 ):
            dy = n0 - row * wn - cn
            for col in range( c0, c1 + 1 ):
                if cid[row, col] == k:
                    continue
                dx = e0 + col * we - ce
                dz = ( top[row, col] - zg - hc ) * kz
                p2 = dx * dx + dy * dy + dz * dz
                if p2 < a * a:
                    val = opacity
                else:
                    t = -( dx * lx + dy * ly + dz * dz_ ) / dd
                    if t <= 0.0:
                        continue
                    qx, qy, qz = dx + t * lx, dy + t * ly, dz + t * dz_
                    q = math.sqrt( qx * qx + qy * qy + qz * qz )
                    if q >= a:
                        continue
                    val = opacity * min( ( a - q ) / soft, 1.0 )
                if val > shadow[row, col]:
                    shadow[row, col] = val


# ---------------------------------------------------------------------------------------------------------------------
# What the vista's buildings and trees (Tools/belltower_vista_props.py) do to the ground

_PROPS = []


def props_world():
    """ belltower_vista_props' buildings and trees, built once. """
    if not _PROPS:
        import belltower_vista_props as B
        _PROPS.append( B.build() )
    return _PROPS[0]


@numba.njit( cache=True, fastmath=True, inline="always" )
def _lay( ground, kinds, micro, over, alpha, shade, row, col, r, g, b, a, kind, flat ):
    """ Ground of colour r, g, b over a share a of a texel, of a kind where it's most of it. It clears the mean of the
    trees there, their shade with it, and flat of the land's small relief. """
    ground[row, col, 0] = ground[row, col, 0] * ( 1.0 - a ) + r * a
    ground[row, col, 1] = ground[row, col, 1] * ( 1.0 - a ) + g * a
    ground[row, col, 2] = ground[row, col, 2] * ( 1.0 - a ) + b * a
    if a > 0.5:
        kinds[row, col] = kind
    micro[row, col] *= 1.0 - flat * a
    for c in range( 3 ):
        over[row, col, c] *= 1.0 - a
    alpha[row, col] *= 1.0 - a
    shade[row, col] += ( 1.0 - shade[row, col] ) * a


@numba.njit( cache=True, fastmath=True, inline="always" )
def _strip( d, half, w ):
    """ The share of a footprint w across, centred d from a band's middle, that a band half either side covers. """
    return max( min( d + 0.5 * w, half ) - max( d - 0.5 * w, -half ), 0.0 ) / w


@numba.njit( cache=True, fastmath=True )
def _yard( poly, kind, k, e0, n0, we, wn, w, ground, kinds, micro, over, alpha, shade, weight, grads ):
    """ A yard's ground inside a plan outline, k units a metre: soft-edged (a farm's ragged, where the yard wears into
    the grass), each kind with its own wear and pattern. weight keeps the most of a texel any yard or road covers. """
    rows, cols = weight.shape
    count = poly.shape[0]
    soft = max( w, 1.0 * k )
    ragged = 2.5 * k if kind == 1 else 0.0
    pad = 0.5 * soft + 1.5 * ragged + w
    c0 = max( int( ( poly[:, 0].min() - pad - e0 ) / we ), 0 )
    c1 = min( int( ( poly[:, 0].max() + pad - e0 ) / we ) + 1, cols - 1 )
    r0 = max( int( ( n0 - poly[:, 1].max() - pad ) / wn ), 0 )
    r1 = min( int( ( n0 - poly[:, 1].min() + pad ) / wn ) + 1, rows - 1 )
    # A garden's own frame, for its parterre: metres along its first edge and its last.
    ue, un = poly[1, 0] - poly[0, 0], poly[1, 1] - poly[0, 1]
    ve, vn = poly[count - 1, 0] - poly[0, 0], poly[count - 1, 1] - poly[0, 1]
    ul, vl = math.sqrt( ue * ue + un * un ), math.sqrt( ve * ve + vn * vn )
    wm = w / k
    for row in range( r0, r1 + 1 ):
        n = n0 - row * wn
        for col in range( c0, c1 + 1 ):
            e = e0 + col * we
            inside = False
            d2 = 1e30
            for i in range( count ):
                j = i + 1 if i + 1 < count else 0
                ae, an, be, bn = poly[i, 0], poly[i, 1], poly[j, 0], poly[j, 1]
                if ( an > n ) != ( bn > n ):
                    if ae + ( n - an ) * ( be - ae ) / ( bn - an ) > e:
                        inside = not inside
                de, dn = be - ae, bn - an
                t = min( max( ( ( e - ae ) * de + ( n - an ) * dn ) / max( de * de + dn * dn, 1e-9 ), 0.0 ), 1.0 )
                qe, qn = ae + t * de - e, an + t * dn - n
                d2 = min( d2, qe * qe + qn * qn )
            s = math.sqrt( d2 ) if inside else -math.sqrt( d2 )
            if ragged > 0.0:
                s += ragged * V._fbm( e, n, 9.0 * k, 3, 0.5, 4401, w, grads )
            a = min( max( s / soft + 0.5, 0.0 ), 1.0 )
            if a <= 0.0:
                continue
            mottle = 1.0 + 0.12 * V._fbm( e, n, 5.0 * k, 3, 0.55, 4402 + kind, w, grads )
            r = YARD_COLOURS[kind, 0] * mottle
            g = YARD_COLOURS[kind, 1] * mottle
            b = YARD_COLOURS[kind, 2] * mottle
            kd = YARD_KINDS[kind]
            if kind == 0:
                # Kitchen gardens between the houses.
                veg = 0.8 * V._smooth( 0.1, 0.45, V._fbm( e, n, 16.0 * k, 2, 0.5, 4403, w, grads ) )
                r, g, b = _mix( r, KITCHEN_GARDEN[0], veg ), _mix( g, KITCHEN_GARDEN[1], veg ), _mix( b, KITCHEN_GARDEN[2], veg )
            elif kind == 1:
                # Dry grass in patches, more of it towards the edge, and straw.
                grass = V._smooth( 0.0, 0.6, V._fbm( e, n, 7.0 * k, 3, 0.5, 4404, w, grads ) + 0.5 - s / ( 9.0 * k ) )
                r, g, b = _mix( r, DRY_GRASS[0], grass ), _mix( g, DRY_GRASS[1], grass ), _mix( b, DRY_GRASS[2], grass )
            elif kind == 2:
                # A parterre: gravel walks round and across, four lawn beds edged with low box, a basin in the middle.
                um = ( ( e - poly[0, 0] ) * ue + ( n - poly[0, 1] ) * un ) / ( ul * k )
                vm = ( ( e - poly[0, 0] ) * ve + ( n - poly[0, 1] ) * vn ) / ( vl * k )
                lu, lv = ul / k, vl / k
                into = min( min( um - 5.0, lu - 5.0 - um ), abs( um - 0.5 * lu ) - 1.5 )
                into = min( into, min( min( vm - 3.0, lv - 3.0 - vm ), abs( vm - 0.5 * lv ) - 1.5 ) )
                bed = min( max( into / wm + 0.5, 0.0 ), 1.0 )
                hedge = _strip( into - 0.35, 0.35, wm )
                basin = min( max( ( 2.5 - math.hypot( um - 0.5 * lu, vm - 0.5 * lv ) ) / wm + 0.5, 0.0 ), 1.0 )
                rim = _strip( math.hypot( um - 0.5 * lu, vm - 0.5 * lv ) - 2.7, 0.3, wm )
                r = _mix( YARD_COLOURS[3, 0], YARD_COLOURS[2, 0] * mottle, bed )
                g = _mix( YARD_COLOURS[3, 1], YARD_COLOURS[2, 1] * mottle, bed )
                b = _mix( YARD_COLOURS[3, 2], YARD_COLOURS[2, 2] * mottle, bed )
                r, g, b = _mix( r, BOX_HEDGE[0], hedge ), _mix( g, BOX_HEDGE[1], hedge ), _mix( b, BOX_HEDGE[2], hedge )
                r, g, b = _mix( r, WALL_TOP[0], rim ), _mix( g, WALL_TOP[1], rim ), _mix( b, WALL_TOP[2], rim )
                r, g, b = _mix( r, WATER_EDGE[0], basin ), _mix( g, WATER_EDGE[1], basin ), _mix( b, WATER_EDGE[2], basin )
                kd = GRASS if bed > 0.5 else ( WATER if basin > 0.5 else SOIL )
            else:
                # Gravel, the grass coming through it.
                grass = 0.35 * V._smooth( 0.05, 0.5, V._fbm( e, n, 4.0 * k, 2, 0.5, 4405, w, grads ) )
                r, g, b = _mix( r, GREEN_GRASS[0], grass ), _mix( g, GREEN_GRASS[1], grass ), _mix( b, GREEN_GRASS[2], grass )
            _lay( ground, kinds, micro, over, alpha, shade, row, col, r, g, b, a, kd, YARD_FLAT[kind] )
            weight[row, col] = max( weight[row, col], a )


@numba.njit( cache=True, fastmath=True )
def _road( line, ks, half, e0, n0, we, wn, w, ground, kinds, micro, over, alpha, shade, weight, grads ):
    """ A white road along a plan line, half either side of it: limestone gravel, palest in the wheel tracks, grass
    down its crown, and its dust on the verges. ks: units a metre at each point. """
    rows, cols = weight.shape
    count = line.shape[0]
    pad = half + 2.5 * ks.max() + w
    c0 = max( int( ( line[:, 0].min() - pad - e0 ) / we ), 0 )
    c1 = min( int( ( line[:, 0].max() + pad - e0 ) / we ) + 1, cols - 1 )
    r0 = max( int( ( n0 - line[:, 1].max() - pad ) / wn ), 0 )
    r1 = min( int( ( n0 - line[:, 1].min() + pad ) / wn ) + 1, rows - 1 )
    for row in range( r0, r1 + 1 ):
        n = n0 - row * wn
        for col in range( c0, c1 + 1 ):
            e = e0 + col * we
            d2 = 1e30
            k = ks[0]
            for i in range( count - 1 ):
                ae, an, be, bn = line[i, 0], line[i, 1], line[i + 1, 0], line[i + 1, 1]
                if e < min( ae, be ) - pad or e > max( ae, be ) + pad or n < min( an, bn ) - pad or n > max( an, bn ) + pad:
                    continue
                de, dn = be - ae, bn - an
                t = min( max( ( ( e - ae ) * de + ( n - an ) * dn ) / max( de * de + dn * dn, 1e-9 ), 0.0 ), 1.0 )
                qe, qn = ae + t * de - e, an + t * dn - n
                q2 = qe * qe + qn * qn
                if q2 < d2:
                    d2 = q2
                    k = ks[i]
            if d2 >= pad * pad:
                continue
            d = math.sqrt( d2 )
            soft = max( w, 0.5 * k )
            a = min( max( ( half - d ) / soft + 0.5, 0.0 ), 1.0 )
            verge = min( max( ( half + 2.0 * k - d ) / soft + 0.5, 0.0 ), 1.0 ) - a
            if a <= 0.0 and verge <= 0.0:
                continue
            if verge > 0.0:
                _lay( ground, kinds, micro, over, alpha, shade, row, col, VERGE[0], VERGE[1], VERGE[2], 0.5 * verge,
                      kinds[row, col], 0.0 )
            if a > 0.0:
                mottle = 1.0 + 0.07 * V._fbm( e, n, 3.0 * k, 3, 0.5, 4410, w, grads )
                crown = 0.5 * _strip( d, 0.3 * k, w )
                r = _mix( ROAD[0] * mottle, DRY_GRASS[0], crown )
                g = _mix( ROAD[1] * mottle, DRY_GRASS[1], crown )
                b = _mix( ROAD[2] * mottle, DRY_GRASS[2], crown )
                _lay( ground, kinds, micro, over, alpha, shade, row, col, r, g, b, a, SOIL, 0.8 )
            weight[row, col] = max( weight[row, col], a + 0.5 * verge )


@numba.njit( cache=True, fastmath=True )
def _building_shadows( boxes, e0, n0, we, wn, w, top, shadow ):
    """ Where each building keeps the sun off: a ray from each texel's surface towards the sun, against the building
    as a box up to halfway up its roof, box-filtered over the texel at its sides and its tip. boxes: the four corners'
    e and n, the base, the eaves and the ridge. """
    rows, cols = top.shape
    se, sn = SUN_PLAN[0], SUN_PLAN[1]
    rise = V.SUN[2] / math.hypot( V.SUN[0], V.SUN[1] )     # the ray's climb along the ground
    pe, pn = -sn, se                                        # across the rays
    ce = np.empty( 5 )
    cn = np.empty( 5 )
    for b in range( boxes.shape[0] ):
        height = boxes[b, 9] + 0.5 * ( boxes[b, 10] - boxes[b, 9] )
        area = 0.0
        for i in range( 4 ):
            ce[i], cn[i] = boxes[b, 2 * i], boxes[b, 2 * i + 1]
        ce[4], cn[4] = ce[0], cn[0]
        for i in range( 4 ):
            area += ce[i] * cn[i + 1] - ce[i + 1] * cn[i]
        turn = 1.0 if area > 0.0 else -1.0         # the outward normals' side
        lo, hi = 1e30, -1e30
        emin, emax, nmin, nmax = 1e30, -1e30, 1e30, -1e30
        for i in range( 4 ):
            p = ce[i] * pe + cn[i] * pn
            lo, hi = min( lo, p ), max( hi, p )
            emin, emax = min( emin, ce[i] ), max( emax, ce[i] )
            nmin, nmax = min( nmin, cn[i] ), max( nmax, cn[i] )
        reach = 1.5 * ( height - boxes[b, 8] ) / rise + 2.0 * w
        c0 = max( int( ( min( emin, emin - se * reach ) - w - e0 ) / we ), 0 )
        c1 = min( int( ( max( emax, emax - se * reach ) + w - e0 ) / we ) + 1, cols - 1 )
        r0 = max( int( ( n0 - max( nmax, nmax - sn * reach ) - w ) / wn ), 0 )
        r1 = min( int( ( n0 - min( nmin, nmin - sn * reach ) + w ) / wn ) + 1, rows - 1 )
        for row in range( r0, r1 + 1 ):
            n = n0 - row * wn
            for col in range( c0, c1 + 1 ):
                e = e0 + col * we
                z = top[row, col]
                if z >= height + rise * w:
                    continue
                # Across the rays: the share of the texel the building's silhouette covers, and the ray through it.
                p = e * pe + n * pn
                side = max( min( p + 0.5 * w, hi ) - max( p - 0.5 * w, lo ), 0.0 ) / w
                if side <= 0.0:
                    continue
                shift = min( max( p, lo + 1e-3 ), hi - 1e-3 ) - p
                re, rn = e + pe * shift, n + pn * shift
                s_in, s_out = 0.0, 1e30
                miss = False
                for i in range( 4 ):
                    xe, xn = turn * ( cn[i + 1] - cn[i] ), -turn * ( ce[i + 1] - ce[i] )
                    num = xe * ( re - ce[i] ) + xn * ( rn - cn[i] )
                    den = xe * se + xn * sn
                    if abs( den ) < 1e-12:
                        if num > 0.0:
                            miss = True
                        continue
                    t = -num / den
                    if den < 0.0:
                        s_in = max( s_in, t )
                    else:
                        s_out = min( s_out, t )
                if miss or s_out <= s_in:
                    continue
                tip = min( max( ( height - z - s_in * rise ) / ( rise * w ) + 0.5, 0.0 ), 1.0 )
                val = tip * side
                if val > shadow[row, col]:
                    shadow[row, col] = val


def clear_crowns( crowns, es, ns, weight, boxes, prop_crowns ):
    """ The painter's own crowns, less those on the props' yards and roads, over their buildings, or in their trees. """
    if not len( crowns ):
        return crowns
    we, wn = es[1] - es[0], ns[0] - ns[1]
    col = np.clip( ( ( crowns[:, 0] - es[0] ) / we ).astype( np.int64 ), 0, len( es ) - 1 )
    row = np.clip( ( ( ns[0] - crowns[:, 1] ) / wn ).astype( np.int64 ), 0, len( ns ) - 1 )
    keep = weight[row, col] < 0.3
    if len( boxes ):
        corners = boxes[:, :8].reshape( -1, 4, 2 )
        middle = corners.mean( 1 )
        reach = np.linalg.norm( corners - middle[:, None], axis=2 ).max( 1 )
        tree = cKDTree( middle )
        far = crowns[:, 3].max() + reach.max()
        near = np.flatnonzero( keep & np.isfinite( tree.query( crowns[:, :2], distance_upper_bound=far )[0] ) )
        for i in near:
            for j in tree.query_ball_point( crowns[i, :2], crowns[i, 3] + reach.max() ):
                if _quad_distance( crowns[i, :2], corners[j] ) < crowns[i, 3]:
                    keep[i] = False
                    break
    if len( prop_crowns ):
        d, j = cKDTree( prop_crowns[:, :2] ).query( crowns[:, :2] )
        keep &= d >= 0.8 * ( crowns[:, 3] + prop_crowns[j, 3] )
    return crowns[keep]


def _quad_distance( p, quad ):
    """ How far plan point p is from a convex quad (0 inside it). """
    inside = True
    best = np.inf
    area = sum( quad[i, 0] * quad[( i + 1 ) % 4, 1] - quad[( i + 1 ) % 4, 0] * quad[i, 1] for i in range( 4 ) )
    for i in range( 4 ):
        a, b = quad[i], quad[( i + 1 ) % 4]
        ab = b - a
        if ( ab[0] * ( p[1] - a[1] ) - ab[1] * ( p[0] - a[0] ) ) * area < 0.0:
            inside = False
        t = min( max( float( np.dot( p - a, ab ) / max( np.dot( ab, ab ), 1e-9 ) ), 0.0 ), 1.0 )
        best = min( best, float( np.linalg.norm( a + ab * t - p ) ) )
    return 0.0 if inside else best


def props_ground( es, ns, w, ground, kind, micro, over, alpha, shade ):
    """ The props' yards and roads, painted into a zone's ground. Returns how much of each texel they cover. """
    t0 = time.time()
    world = props_world()
    _, _, yards, roads = world.paint_data()
    we, wn = es[1] - es[0], ns[0] - ns[1]
    weight = np.zeros( kind.shape, np.float32 )
    for yard_kind, outline in yards:
        outline = np.ascontiguousarray( outline, float )
        k = world.k_at( *outline.mean( 0 ) )
        _yard( outline, int( yard_kind ), k, es[0], ns[0], we, wn, w, ground, kind, micro, over, alpha, shade,
               weight, V._GRADIENTS )
    for half, line in roads:
        line = np.ascontiguousarray( line, float )
        ks = np.array( [ world.k_at( e, n ) for e, n in line ] )
        _road( line, ks, half, es[0], ns[0], we, wn, w, ground, kind, micro, over, alpha, shade, weight, V._GRADIENTS )
    print( f"  {len( yards )} yards and {len( roads )} roads in {time.time() - t0:.1f} s" )
    return weight


# ---------------------------------------------------------------------------------------------------------------------
# A zone, start to finish

def zone_grid( margin, size ):
    """ The texel centres of a zone's texture: e along a row (west to east), n down the columns (north to south). """
    e0, e1 = V.TE0 - margin, V.TE1 + margin
    n0, n1 = V.TN0 - margin, V.TN1 + margin
    es = e0 + ( np.arange( size ) + 0.5 ) * ( e1 - e0 ) / size
    ns = n1 - ( np.arange( size ) + 0.5 ) * ( n1 - n0 ) / size
    return es, ns


def paint_zone( zone, margin, inner, size, props=True ):
    """ A zone's colour (sRGB, H x W x 3), kind (0..3) and normal map (half size, plan normals). With props, what
    belltower_vista_props' buildings and trees do to the ground. """
    t0 = time.time()
    es, ns = zone_grid( margin, size )
    we, wn = es[1] - es[0], ns[0] - ns[1]
    w = max( we, wn )
    E, N = np.meshgrid( es, ns )
    Z = V.land_height( E, N, w )
    GX = np.gradient( Z, axis=1 ) / we
    GY = -np.gradient( Z, axis=0 ) / wn
    del E, N
    print( f"zone {zone}: {size} x {size}, {w:.1f} units a texel, heights in {time.time() - t0:.1f} s" )

    t1 = time.time()
    ground = np.zeros( ( size, size, 3 ), np.float32 )
    kind = np.zeros( ( size, size ), np.float32 )
    micro = np.zeros( ( size, size ), np.float32 )
    over = np.zeros( ( size, size, 3 ), np.float32 )
    alpha = np.zeros( ( size, size ), np.float32 )
    shade = np.ones( ( size, size ), np.float32 )
    _paint( es, ns, Z, GX, GY, w, V._GRADIENTS, ground, kind, micro, over, alpha, shade )
    print( f"  ground in {time.time() - t1:.1f} s" )
    if props:
        boxes, prop_crowns, _, _ = props_world().paint_data()
        covered = props_ground( es, ns, w, ground, kind, micro, over, alpha, shade )

    t2 = time.time()
    crowns = crowns_for( zone, margin, es, ns, Z, w, inner )
    if props:
        crowns = np.concatenate( ( clear_crowns( crowns, es, ns, covered, boxes, prop_crowns ), prop_crowns ) )
    top = Z.copy()
    ccol = np.zeros( ( size, size, 3 ) )
    cov = np.zeros( ( size, size ) )
    cid = np.full( ( size, size ), -1, np.int64 )
    _tops( crowns, es[0], ns[0], we, wn, w, top, ccol, cov, cid, V._GRADIENTS )
    shadow = np.zeros( ( size, size ) )
    _shadows( crowns, es[0], ns[0], we, wn, w, top, cid, shadow )
    if props:
        _building_shadows( np.ascontiguousarray( boxes ), es[0], ns[0], we, wn, w, top, shadow )
    print( f"  {len( crowns )} crowns drawn in {time.time() - t2:.1f} s" )

    # The ground in the shade of the trees too small to draw, their mean canopy over it, the drawn trees over that, and
    # the drawn trees' shadows over everything.
    base = ground * ( 1.0 - ( 1.0 - shade[..., None] ) * ( 1.0 - SHADOW_TINT ) )
    base = base * ( 1.0 - alpha[..., None] ) + over
    surface = ccol + base * ( 1.0 - cov[..., None] )
    colour = surface * ( 1.0 - shadow[..., None] * ( 1.0 - SHADOW_TINT ) )
    trees = np.maximum( cov, alpha )
    kind = np.where( trees > 0.5, GRASS, kind )

    # The normal map: the land and its small relief, at half size.
    h = Z + micro
    gx = np.gradient( h, axis=1 ) / we
    gy = -np.gradient( h, axis=0 ) / wn
    normal = np.stack( ( -gx, -gy, np.ones_like( gx ) ), -1 )
    normal /= np.linalg.norm( normal, axis=-1, keepdims=True )
    normal = normal.reshape( size // 2, 2, size // 2, 2, 3 ).mean( ( 1, 3 ) )
    normal /= np.linalg.norm( normal, axis=-1, keepdims=True )
    print( f"zone {zone} painted in {time.time() - t0:.1f} s" )
    return srgb8( colour ), kind, normal


def write_zone( out_dir, zone, colour, kind, normal ):
    out_dir.mkdir( parents=True, exist_ok=True )
    Image.fromarray( colour, "RGB" ).save( out_dir / f"vista_{zone}_color.jpg", quality=92, subsampling=0 )
    Image.fromarray( np.clip( np.rint( kind / 3.0 * 255 ), 0, 255 ).astype( np.uint8 ), "L" ).save(
        out_dir / f"vista_{zone}_kind.png", optimize=True )
    packed = np.stack( ( normal[..., 0] * 0.5 + 0.5, normal[..., 1] * 0.5 + 0.5, normal[..., 2] ), -1 )
    Image.fromarray( np.clip( np.rint( packed * 255 ), 0, 255 ).astype( np.uint8 ), "RGB" ).save(
        out_dir / f"vista_{zone}_normal.jpg", quality=95, subsampling=0 )


# ---------------------------------------------------------------------------------------------------------------------
# Tiling detail: grass, soil and stone up close

def periodic_noise( size, lo, hi, beta, rng ):
    """ Noise that tiles, with a 1 / f^beta spectrum between lo and hi cycles a tile, scaled to unit spread. """
    f = np.fft.fftfreq( size ) * size
    fx, fy = np.meshgrid( f, f )
    k = np.hypot( fx, fy )
    amp = np.where( ( k >= lo ) & ( k <= hi ), 1.0 / np.maximum( k, 1.0 ) ** beta, 0.0 )
    phase = rng.standard_normal( ( size, size ) ) + 1j * rng.standard_normal( ( size, size ) )
    out = np.real( np.fft.ifft2( amp * phase ) )
    return out / max( out.std(), 1e-9 )


def detail( kind, size=DETAIL_SIZE, seed=1 ):
    """ A detail texture: red and green tilt the normal east and north (0.5 none), blue brightens (0.5 none). It's read
    at a 70-unit tile and a 290-unit one. """
    rng = np.random.default_rng( seed )
    tile = DETAIL_TILES[0]
    if kind == "grass":
        # Tufts a few centimetres across, blades between, and the soil showing in places.
        height = periodic_noise( size, 20, 90, 1.2, rng ) + 0.6 * periodic_noise( size, 90, 400, 0.8, rng )
        bright = 0.5 + 0.11 * periodic_noise( size, 6, 60, 1.0, rng ) + 0.05 * height
        strength = 0.55
    elif kind == "soil":
        # Clods and crumbs, a few pebbles.
        clods = periodic_noise( size, 12, 70, 1.4, rng )
        crumbs = periodic_noise( size, 70, 400, 0.9, rng )
        pebbles = np.clip( periodic_noise( size, 30, 120, 0.5, rng ) - 2.2, 0, None ) * 2.0
        height = clods + 0.5 * crumbs + pebbles
        bright = 0.5 + 0.08 * clods + 0.06 * pebbles - 0.03 * crumbs
        strength = 0.45
    else:
        # Weathered limestone: lumps, pits and cracks.
        lumps = periodic_noise( size, 4, 40, 1.6, rng )
        grain = periodic_noise( size, 40, 400, 0.9, rng )
        cracks = np.exp( -np.abs( periodic_noise( size, 6, 30, 1.2, rng ) ) * 6.0 )
        height = lumps + 0.3 * grain - 1.2 * cracks
        bright = 0.5 + 0.07 * lumps + 0.03 * grain - 0.12 * cracks
        strength = 0.5
    texel = tile / size
    gx = ( np.roll( height, -1, 1 ) - np.roll( height, 1, 1 ) ) / ( 2 * texel )
    gy = -( np.roll( height, -1, 0 ) - np.roll( height, 1, 0 ) ) / ( 2 * texel )
    scale = strength / max( np.percentile( np.hypot( gx, gy ), 95 ), 1e-9 )
    out = np.stack( ( 0.5 - 0.5 * np.clip( gx * scale, -1, 1 ), 0.5 - 0.5 * np.clip( gy * scale, -1, 1 ),
                      np.clip( bright, 0.2, 0.8 ) ), -1 )
    return np.clip( np.rint( out * 255 ), 0, 255 ).astype( np.uint8 )


def write_details( out_dir ):
    for k, ( name, seed ) in enumerate( ( ( "grass", 11 ), ( "soil", 12 ), ( "stone", 13 ) ) ):
        Image.fromarray( detail( name, seed=seed ), "RGB" ).save( out_dir / f"detail_{name}.png", optimize=True )


def vmat_text():
    lines = [ "// Tools/belltower_vista_paint.py", '"Layer0"', "{", '    shader "shaders/hc1_vista.shader"',
              f'    g_vTown "[{V.TE0:.3f} {V.TE1:.3f} {V.TN0:.3f} {V.TN1:.3f}]"',
              '    g_vZoneMargins "[' + " ".join( f"{m:.3f}" for _, m in ZONES ) + ']"',
              f'    g_flZoneBlend "{ZONE_BLEND:.3f}"',
              '    g_vRoughness "[' + " ".join( f"{r:.3f}" for r in ROUGHNESS ) + ']"',
              f'    g_vDetailTiles "[{DETAIL_TILES[0]:.3f} {DETAIL_TILES[1]:.3f}]"',
              f'    g_vDetailFade "[{DETAIL_FADE[0]:.3f} {DETAIL_FADE[1]:.3f}]"',
              '    g_flDetailNormal "0.800"', '    g_flDetailAlbedo "0.700"' ]
    for zone, _ in ZONES:
        z = zone.upper()
        lines += [ f'    TextureColor{z} "{RESOURCE_DIR}/vista_{zone}_color.jpg"',
                   f'    TextureKind{z} "{RESOURCE_DIR}/vista_{zone}_kind.png"',
                   f'    TextureNormal{z} "{RESOURCE_DIR}/vista_{zone}_normal.jpg"' ]
    for name in ( "Grass", "Soil", "Stone" ):
        lines.append( f'    TextureDetail{name} "{RESOURCE_DIR}/detail_{name.lower()}.png"' )
    return "\n".join( lines + [ "}", "" ] )


def write_sheet( out_dir, path ):
    """ The zones side by side, each 640 across, with a 1:1 crop from the middle of each under it. """
    tiles, crops = [], []
    for zone, _ in ZONES:
        f = out_dir / f"vista_{zone}_color.jpg"
        if not f.exists():
            continue
        img = Image.open( f )
        tiles.append( img.resize( ( 640, 640 ), Image.LANCZOS ) )
        w, h = img.size
        c = min( 320, w // 4 )
        crops.append( img.crop( ( w // 2 + w // 8 - c, h // 2 + h // 8 - c, w // 2 + w // 8 + c,
                                  h // 2 + h // 8 + c ) ).resize( ( 640, 640 ), Image.NEAREST ) )
    sheet = Image.new( "RGB", ( 640 * len( tiles ), 1280 ) )
    for k, ( t, c ) in enumerate( zip( tiles, crops ) ):
        sheet.paste( t, ( 640 * k, 0 ) )
        sheet.paste( c, ( 640 * k, 640 ) )
    sheet.save( path, quality=90 )


class _RawLook:
    """ A Look for render_view's raw passes: no fog, and the sky as NaN (or the real sky). """

    def __init__( self, look, sky=False ):
        self.look, self.sky, self.fog_colour = look, sky, np.zeros( 3 )

    def fog_amount( self, eye, points ):
        return np.zeros( points.shape[:-1] )

    def sky_colour( self, eye, rays ):
        return self.look.sky_colour( eye, rays ) if self.sky else np.full( rays.shape, np.nan )


def preview( out_dir, tex_dir, views, props=True ):
    """ The town's views of the land with its painted colour maps: render_view's raw passes give each pixel's place,
    normal and the town's colour, then each land pixel takes its zones' texels, lit and fogged by belltower_vista's
    Look. With props, the buildings and trees of Tools/belltower_vista_props.py stand on it, textured the same way
    from their own maps (built afresh, so they needn't have been written). """
    import belltower_map as BM
    out_dir.mkdir( parents=True, exist_ok=True )
    look = V.Look()
    verts, normals, tris, _ = V.land_mesh()
    town, town_normals, paints = V.town_triangles()
    names = sorted( set( paints ) )
    albedo = np.array( [ BM.paint_colour( p ) for p in names ] ) ** 2.2
    index = { p: k for k, p in enumerate( names ) }
    town_colours = np.repeat( look.light( albedo[[ index[p] for p in paints ]], town_normals )[:, None, :], 3, axis=1 )
    town_up = np.repeat( town_normals[:, None, :], 3, axis=1 )
    maps = { zone: np.asarray( Image.open( tex_dir / f"vista_{zone}_color.jpg" ).convert( "RGB" ) ) for zone, _ in ZONES }
    reach = max( V.TE1 - V.CENTRE[0], V.CENTRE[0] - V.TE0, V.TN1 - V.CENTRE[1], V.CENTRE[1] - V.TN0 )
    flat, sky = _RawLook( look ), _RawLook( look, sky=True )
    land_tris = verts[tris]
    land_mark = np.full( ( len( tris ), 3, 3 ), -1.0 )
    if props:
        world = props_world()
        prop_tris, prop_normals, prop_uvm = world.mesh.preview_triangles()
        prop_maps = world.preview_textures()
        prop_mark = np.full( prop_tris.shape, -2.0 )

    def scene( land_values, town_values, prop_values ):
        out = [ ( land_tris, land_values ), ( town, town_values ) ]
        if props:
            out.append( ( prop_tris, prop_values ) )
        return out

    for name, eye, target, fov in V.PREVIEW_VIEWS:
        if views and name not in views:
            continue
        place = V.render_view( flat, scene( land_tris, town, prop_tris if props else None ), eye, target, fov=fov,
                               raw=True )
        up = V.render_view( flat, scene( normals[tris], town_up, prop_normals if props else None ), eye, target,
                            fov=fov, raw=True )
        colour = V.render_view( flat, scene( land_mark, town_colours, prop_mark if props else None ), eye, target,
                                fov=fov, raw=True )
        image = V.render_view( sky, [], eye, target, fov=fov, raw=True )
        hit = ~np.isnan( place[..., 0] )
        land = hit & ( colour[..., 0] < -0.5 ) & ( colour[..., 0] > -1.5 )
        if props:
            # The props' pixels: their maps' texels at the UVs a further pass gives, lit by their normals.
            uvm = V.render_view( flat, scene( np.zeros_like( land_tris ), np.zeros_like( town ), prop_uvm ), eye,
                                 target, fov=fov, raw=True )
            mine = hit & ( colour[..., 0] < -1.5 )
            u, v, m = uvm[mine, 0], uvm[mine, 1], np.rint( uvm[mine, 2] ).astype( int )
            texel = np.zeros( ( len( u ), 3 ) )
            for k, tex in enumerate( prop_maps ):
                sel = m == k
                size = tex.shape[0]
                texel[sel] = tex[np.floor( ( 1.0 - v[sel] ) * size ).astype( int ) % size,
                                 np.floor( u[sel] * size ).astype( int ) % size]
            n = up[mine] / np.maximum( np.linalg.norm( up[mine], axis=1, keepdims=True ), 1e-6 )
            colour[mine] = look.light( texel, n )
        p = place[land]
        out = V.town_distance( p[:, 0], p[:, 1] )
        texel = np.zeros_like( p )
        left = np.ones( len( p ) )
        for k, ( zone, margin ) in enumerate( ZONES ):
            weight = left if k == len( ZONES ) - 1 else left * np.clip( ( margin - out ) / ( ZONE_BLEND * margin ), 0, 1 )
            half = reach + margin
            size = maps[zone].shape[0]
            col = np.clip( ( ( p[:, 0] - V.CENTRE[0] + half ) / ( 2 * half ) * size ).astype( int ), 0, size - 1 )
            row = np.clip( ( ( V.CENTRE[1] + half - p[:, 1] ) / ( 2 * half ) * size ).astype( int ), 0, size - 1 )
            texel += weight[:, None] * ( maps[zone][row, col] / 255.0 ) ** 2.2
            left = left - weight
        n = up[land] / np.maximum( np.linalg.norm( up[land], axis=1, keepdims=True ), 1e-6 )
        colour[land] = look.light( texel, n )
        fog = look.fog_amount( np.asarray( eye, float ), place[hit] )[:, None]
        image[hit] = colour[hit] * ( 1 - fog ) + look.fog_colour * fog
        Image.fromarray( look.S.display( image ) ).save( out_dir / f"{name}.jpg", quality=90 )
        print( f"wrote {out_dir / name}.jpg" )


def main():
    parser = argparse.ArgumentParser( description=__doc__.split( "\n\n" )[0] )
    parser.add_argument( "--size", type=int, default=COLOUR_SIZE )
    parser.add_argument( "--zones" )
    parser.add_argument( "--out", type=Path, default=OUT_DIR )
    parser.add_argument( "--sheet", type=Path )
    parser.add_argument( "--preview", type=Path )
    parser.add_argument( "--views", nargs="*" )
    parser.add_argument( "--no-props", action="store_true",
                         help="leave the vista's buildings and trees out: their ground, their shadows and --preview" )
    args = parser.parse_args()
    if args.zones is None:
        args.zones = "" if args.preview else "abcd"
    args.out.mkdir( parents=True, exist_ok=True )
    inner = 0.0
    for zone, margin in ZONES:
        if zone in args.zones:
            colour, kind, normal = paint_zone( zone, margin, inner, args.size, props=not args.no_props )
            write_zone( args.out, zone, colour, kind, normal )
        inner = margin * ( 1.0 - ZONE_BLEND )
    write_details( args.out )
    vmat = args.out / f"{MATERIAL}.vmat"
    text = vmat_text()
    if not vmat.exists() or vmat.read_text( encoding="utf-8" ) != text:
        vmat.write_text( text, encoding="utf-8", newline="\n" )
    if args.sheet:
        write_sheet( args.out, args.sheet )
    if args.preview:
        preview( args.preview, args.out, args.views, props=not args.no_props )


if __name__ == "__main__":
    main()
