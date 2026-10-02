"""
Belltower's vista: the land round the hill town out to the horizon, with its farms, villages and trees. Drawn only:
nothing out there collides, and only the trees on the town's own hill cast shadows.

    python Tools/belltower_vista.py [--preview <dir>] [--no-textures] [--size N]

Tools/belltower_map.py builds it with the town (build()). Run on its own, it writes the vista's models and textures only.

- The land is one mesh of rings round the town's rectangle, close together at the walls and further apart out to REACH
  (90000, ~2.3 km), which keeps the player camera's far plane (ZFar 100000) beyond the last ring wherever you stand in
  the town. Each ring is a crest or rises to the next, so the mesh's edge is never seen against the sky.
- The land's shape (land_height) is the town's hill falling to valleys (a profile for each side), round hills placed by
  hand (HILLS), rolling noise, the river's floodplain winding along the south valley, the olive terraces on the town's
  own hill, and ridged mountains past MOUNTAINS. Its band-limited: each sample leaves out the noise finer than the mesh
  or texture holding it, so the mesh doesn't alias and the textures' normals carry the finer relief.
- Past ~1 km the land plays a landscape further off than it is (forced perspective): fields, woods and villages there
  are drawn smaller (field_scale), and the fog (belltower_map's Fog) thickens towards the horizon.
- The land is textured from above in four zones (ZONES), each its own material with a colour and a normal map, each
  zone's texels about a pixel wide where its own land is seen. Every texel is painted from the same land: fields,
  vineyards, olive groves, woods, the river, roads and farmyards, with the painted trees' shading and the shadows the
  sun throws from them (the sun is fixed: belltower_map's SUN).
- The props are their own model: cypresses (along the roads, round farms and villas, on the hills), olive trees on the
  terraces, oaks and holm oaks at the woods' edges and in the fields, poplars along the river, umbrella pines by the
  villas, farmhouses with their barns and dovecote towers, a villa, chapels, the castle on the west hill and the
  village on the south-west hill. The ones on the town's hill (NEAR_SHADOWS) are a model of their own that casts
  shadows; the land's painting doesn't darken under those.

Plan coordinates: e east, n north, z up (map_kit's docstring has the world axes). The town's streets are at z 0.
"""
import argparse
import math
import time
from pathlib import Path

import numba
import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.interpolate import PchipInterpolator

import map_kit as K

MODEL_DIR = K.ASSETS / "models" / "maps" / "belltower"
MODEL_RESOURCE = "models/maps/belltower"
TEXTURE_DIR = K.ASSETS / "materials" / "belltower" / "vista"
TEXTURE_RESOURCE = "materials/belltower/vista"

# The town's rectangle (belltower_map's town wall, south parapet and north row), and its middle.
TOWN_RECT = ( -2380.0, 2380.0, -1466.0, 1800.0 )
TE0, TE1, TN0, TN1 = TOWN_RECT
CENTRE = ( 0.0, ( TN0 + TN1 ) / 2 )
REACH = 90000.0

# Towards the sun in plan (belltower_map.SUN: pitch 34, yaw -63), and where shadows fall: away from it, 1.48 times as
# long as what throws them is tall.
SUN = np.array( ( -0.739, -0.376, 0.559 ) ) / np.linalg.norm( ( -0.739, -0.376, 0.559 ) )
SHADOW_DIR = -SUN[:2] / np.linalg.norm( SUN[:2] )
SHADOW_LENGTH = math.hypot( SUN[0], SUN[1] ) / SUN[2]


# ---------------------------------------------------------------------------------------------------------------------
# Noise: 2D gradient noise, summed in octaves. Every octave finer than a sample's cutoff (a world length: the mesh's
# spacing there, or a texel) is left out, and the one just above it faded, so a sample is the land as seen at that size.

_GRADIENTS = np.array( [ ( math.cos( a ), math.sin( a ) ) for a in np.linspace( 0, 2 * math.pi, 64, endpoint=False ) ] )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _hash( ix, iy, seed ):
    h = ( ix * 0x27D4EB2D ) ^ ( iy * 0x165667B1 ) ^ ( seed * 0x9E3779B1 )
    h &= 0xFFFFFFFF
    h ^= h >> 15
    h = ( h * 0x2C1B3C6D ) & 0xFFFFFFFF
    h ^= h >> 12
    h = ( h * 0x297A2D39 ) & 0xFFFFFFFF
    h ^= h >> 15
    return h


@numba.njit( cache=True, fastmath=True )
def _gradient_noise( x, y, seed, grads ):
    """ Perlin's gradient noise, about -1..1. """
    fx0 = math.floor( x )
    fy0 = math.floor( y )
    ix = np.int64( fx0 )
    iy = np.int64( fy0 )
    fx = x - fx0
    fy = y - fy0
    g00 = _hash( ix, iy, seed ) & 63
    g10 = _hash( ix + 1, iy, seed ) & 63
    g01 = _hash( ix, iy + 1, seed ) & 63
    g11 = _hash( ix + 1, iy + 1, seed ) & 63
    n00 = grads[g00, 0] * fx + grads[g00, 1] * fy
    n10 = grads[g10, 0] * ( fx - 1.0 ) + grads[g10, 1] * fy
    n01 = grads[g01, 0] * fx + grads[g01, 1] * ( fy - 1.0 )
    n11 = grads[g11, 0] * ( fx - 1.0 ) + grads[g11, 1] * ( fy - 1.0 )
    u = fx * fx * fx * ( fx * ( fx * 6.0 - 15.0 ) + 10.0 )
    v = fy * fy * fy * ( fy * ( fy * 6.0 - 15.0 ) + 10.0 )
    a = n00 + u * ( n10 - n00 )
    b = n01 + u * ( n11 - n01 )
    return 1.414 * ( a + v * ( b - a ) )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _band( wavelength, cutoff ):
    """ How much of an octave of this wavelength a sample cut off at cutoff keeps: all of it from twice the cutoff. """
    t = wavelength / cutoff - 1.0
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return t * t * ( 3.0 - 2.0 * t )


@numba.njit( cache=True, fastmath=True )
def _fbm( e, n, wavelength, octaves, gain, seed, cutoff, grads ):
    """ Fractal noise: octaves of halving wavelength from wavelength, each gain times the last. """
    total = 0.0
    amp = 1.0
    w = wavelength
    for k in range( octaves ):
        keep = _band( w, cutoff )
        if keep <= 0.0:
            break
        total += keep * amp * _gradient_noise( e / w, n / w, seed + k * 101, grads )
        amp *= gain
        w *= 0.5
    return total


@numba.njit( cache=True, fastmath=True )
def _ridged( e, n, wavelength, octaves, gain, seed, cutoff, grads ):
    """ Ridged noise for mountains: sharp crests where the noise crosses zero, each octave weighted by the one above it
    (Musgrave's ridged multifractal), 0..~1. """
    total = 0.0
    amp = 1.0
    weight = 1.0
    w = wavelength
    for k in range( octaves ):
        keep = _band( w, cutoff )
        if keep <= 0.0:
            break
        r = 1.0 - abs( _gradient_noise( e / w, n / w, seed + k * 131, grads ) )
        r = r * r * weight
        weight = min( max( r * 1.6, 0.0 ), 1.0 )
        total += keep * amp * r
        amp *= gain
        w *= 0.5
    return total * 0.62


@numba.njit( cache=True, fastmath=True, inline="always" )
def _smooth( a, b, x ):
    t = ( x - a ) / ( b - a )
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return t * t * ( 3.0 - 2.0 * t )


# ---------------------------------------------------------------------------------------------------------------------
# The land's shape

# The lowland round the town's hill: the river's floodplain along the south valley, and the land either side of it
# rising LOWLAND[1] from the floodplain's edge to the valleys' level, LOWLAND[0] (west, north and east of the hill, and
# under the hills across the river), give or take LOWLAND[2] over kilometres.
LOWLAND = ( -2800.0, 20000.0, 350.0 )

# How far the town's hill has fallen from its walls (z -250) to the lowland, as a share, by distance out from the town's
# rectangle: a hillside's shape, steepest 1.5-6 km down and easing onto the lowland.
FALL_D = np.array( [ 0, 400, 1500, 3500, 6000, 9000, 13000, 20000, 200000 ], float )
FALL = np.array( [ 0, 0.03, 0.15, 0.38, 0.63, 0.84, 0.98, 1.0, 1.0 ] )

# Spurs and gullies: the hill's fall stretches out along some directions and shortens between them, by this share,
# about seven times round (noise read round a circle of this radius).
SPURS = ( 0.12, 1250.0, 1400.0 )

# Hills: ( e, n, radius along, radius across, heading of 'along' (degrees from east, anticlockwise), height ). Each
# rises height * exp( -( x / along )^2 - ( y / across )^2 ) over the land under it, its outline bent by noise. The
# steepest slope across a hill is about 0.86 height / across.
HILLS = np.array( [
    # The west ridge, running north and south 700 m out, and the castle's summit on it: it shows over the west wall and
    # the gate from West Street and the square, as the reference's hill does over its gate.
    ( -28500, 3500, 15000, 15000, 90, 8600 ),
    ( -27000, 4800, 4200, 3600, 0, 1000 ),
    # The east ridge, and the villa's knoll.
    ( 27500, 1500, 14500, 14500, 100, 7900 ),
    ( 25500, -4600, 4200, 3600, 0, 800 ),
    # The saddle that joins the town's hill to the ridge north of it, and that ridge.
    ( 0, 7500, 5500, 4500, 0, 1300 ),
    ( -7000, 24000, 22000, 12500, 5, 7000 ),
    ( 16000, 21000, 14000, 11000, -20, 6200 ),
    # Knolls on the valley's floor across the river.
    ( -13000, -35000, 4500, 4000, 20, 1500 ),
    ( 15000, -35500, 5000, 4000, -30, 1300 ),
    # The hills along the valley's far side, the village's to the south-west.
    ( -19000, -49000, 11500, 11000, 30, 7600 ),
    ( 3000, -51000, 12000, 10500, 10, 6400 ),
    ( 22000, -48500, 11500, 11000, -20, 7000 ),
    ( -42000, -51000, 12000, 11500, 40, 7600 ),
    ( 42000, -50000, 12000, 11500, -40, 7400 ),
    # The mountains along the horizon, the highest to the south-east and the north.
    ( 26000, -84000, 24000, 17000, 20, 11500 ),
    ( -42000, -80000, 22000, 16000, -15, 10000 ),
    ( -78000, 25000, 26000, 20000, 60, 10500 ),
    ( 74000, 30000, 26000, 18000, -50, 10000 ),
    ( 5000, 84000, 34000, 18000, 0, 12000 ),
    ( -50000, 68000, 22000, 16000, 30, 10000 ),
    ( 50000, 70000, 24000, 16000, -30, 10500 ),
    ( 75000, -50000, 22000, 16000, 40, 9500 ),
    ( -75000, -46000, 22000, 16000, -40, 9500 ),
], float )

# The river: its line (n by e) winding along the south valley, flowing east, and its floodplain. It's far enough out
# for the ridges west and east of the town to come down to the valley at hillside slopes, and it swings south under them.
RIVER_N = -24000.0
RIVER_WAVES = np.array( [ ( 2200.0, 26000.0, -1.571 ), ( 900.0, 9000.0, 2.1 ), ( 350.0, 4100.0, 4.0 ) ] )
FLOODPLAIN = 2200.0              # half-width either side of the valley's middle, flat (the river winds within it)
FLOODPLAIN_BLEND = 3200.0        # then easing up into the valley's sides over this
RIVER_BED = 260.0                # the gravel bed's half-width
RIVER_REACH = ( 55000.0, 75000.0 )   # where the river's valley gives way to the far hills, east and west
RIVER_SEARCH = 24000             # how far along the river to look for its nearest point: past the valley's sides
RIVER_SWING = float( np.abs( RIVER_WAVES[1:, 0] ).sum() )   # how far the river winds from the valley's middle

# Rolling relief: its longest wavelength, and how much each octave half as long keeps (less than half, so each adds
# less slope than the last).
RELIEF = ( 16000.0, 0.36 )

# The ridged crests past the hills, and the rim: the last rings stand at least RIM[2] high (with noise), so from the
# town the land's edge is always over the horizon.
MOUNTAINS = ( 48000.0, 76000.0, 3400.0 )
RIM = ( 76000.0, REACH, 1900.0 )


FALL_SLOPES = PchipInterpolator( FALL_D, FALL ).derivative()( FALL_D )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _hermite( d, knots, heights, slopes ):
    k = 0
    while k < knots.size - 2 and d > knots[k + 1]:
        k += 1
    h = knots[k + 1] - knots[k]
    t = min( max( ( d - knots[k] ) / h, 0.0 ), 1.0 )
    t2 = t * t
    t3 = t2 * t
    return ( ( 2 * t3 - 3 * t2 + 1 ) * heights[k] + ( t3 - 2 * t2 + t ) * h * slopes[k]
             + ( -2 * t3 + 3 * t2 ) * heights[k + 1] + ( t3 - t2 ) * h * slopes[k + 1] )


@numba.njit( cache=True, fastmath=True )
def _town_offset( e, n ):
    """ ( distance out from the town's rectangle, and the way out: unit east and north parts ). """
    de = e - min( max( e, TE0 ), TE1 )
    dn = n - min( max( n, TN0 ), TN1 )
    d = math.sqrt( de * de + dn * dn )
    if d < 1e-6:
        return 0.0, 0.0, -1.0
    return d, de / d, dn / d


@numba.njit( cache=True, fastmath=True )
def _river_line( e ):
    """ The river's n at e, and its slope dn/de. """
    n = RIVER_N
    s = 0.0
    for k in range( RIVER_WAVES.shape[0] ):
        a, w, p = RIVER_WAVES[k, 0], RIVER_WAVES[k, 1], RIVER_WAVES[k, 2]
        n += a * math.sin( 2 * math.pi * e / w + p )
        s += a * 2 * math.pi / w * math.cos( 2 * math.pi * e / w + p )
    return n, s


@numba.njit( cache=True, fastmath=True, inline="always" )
def _river_gap( x, e, n ):
    """ The squared distance from ( e, n ) to the river's point at x. """
    rn = RIVER_N
    for k in range( RIVER_WAVES.shape[0] ):
        rn += RIVER_WAVES[k, 0] * math.sin( 2 * math.pi * x / RIVER_WAVES[k, 1] + RIVER_WAVES[k, 2] )
    return ( x - e ) * ( x - e ) + ( rn - n ) * ( rn - n )


@numba.njit( cache=True, fastmath=True )
def _river_distance( e, n ):
    """ How far ( e, n ) is from the river's line, out to RIVER_SEARCH (further only reads as at least that): the nearest
    of points along the river every 1000, then every 100 round that one, then a golden-section search. Measured
    straight across from the line's n at e instead, the distance changed by thousands over a few hundred units wherever
    the line turned, and the floodplain's edges rose at up to 57 degrees. """
    best, best_x = 1e30, e
    for k in range( -RIVER_SEARCH // 1000, RIVER_SEARCH // 1000 + 1 ):
        x = e + 1000.0 * k
        g = _river_gap( x, e, n )
        if g < best:
            best, best_x = g, x
    centre = best_x
    for k in range( -6, 7 ):
        x = centre + 100.0 * k
        g = _river_gap( x, e, n )
        if g < best:
            best, best_x = g, x
    a, b = best_x - 100.0, best_x + 100.0
    ratio = 0.6180339887
    c, d = b - ratio * ( b - a ), a + ratio * ( b - a )
    gc, gd = _river_gap( c, e, n ), _river_gap( d, e, n )
    for _ in range( 12 ):
        if gc < gd:
            b, d, gd = d, c, gc
            c = b - ratio * ( b - a )
            gc = _river_gap( c, e, n )
        else:
            a, c, gc = c, d, gd
            d = a + ratio * ( b - a )
            gd = _river_gap( d, e, n )
    return math.sqrt( min( best, gc, gd ) )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _valley_offset( e, n ):
    """ How far north or south ( e, n ) is from the valley's middle: the river's line with only its longest meander, so
    the valley's sides are smooth. The true distance from the winding river creases them along every bend's middle,
    where two stretches of the river are as near as each other. """
    return abs( n - RIVER_N - RIVER_WAVES[0, 0] * math.sin( 2 * math.pi * e / RIVER_WAVES[0, 1] + RIVER_WAVES[0, 2] ) )


@numba.njit( cache=True, fastmath=True )
def _hills( e, n, cutoff, grads ):
    total = 0.0
    for k in range( HILLS.shape[0] ):
        ce, cn, ra, rc, heading, height = HILLS[k, 0], HILLS[k, 1], HILLS[k, 2], HILLS[k, 3], HILLS[k, 4], HILLS[k, 5]
        a = math.radians( heading )
        x = ( e - ce ) * math.cos( a ) + ( n - cn ) * math.sin( a )
        y = -( e - ce ) * math.sin( a ) + ( n - cn ) * math.cos( a )
        r2 = ( x / ra ) ** 2 + ( y / rc ) ** 2
        if r2 > 9.0:
            continue
        # Bend the outline so no hill is an ellipse.
        r2 *= 1.0 + 0.3 * _fbm( e, n, 11000.0, 2, 0.5, 700 + k, cutoff, grads )
        total += height * math.exp( -r2 )
    return total


@numba.njit( cache=True, fastmath=True )
def _height( e, n, cutoff, grads ):
    d, ue, un = _town_offset( e, n )
    # The lowland: the floodplain (falling gently east, with the river), rising either side to the valleys' level, which
    # takes over past the river's reach.
    reach = 1.0 - _smooth( RIVER_REACH[0], RIVER_REACH[1], abs( e ) )
    dv = _valley_offset( e, n )
    plain = -5050.0 - 0.004 * e + 25.0 * _fbm( e, n, 5000.0, 4, 0.5, 51, cutoff, grads )
    level = LOWLAND[0] + LOWLAND[2] * _fbm( e, n, 30000.0, 2, 0.5, 61, cutoff, grads )
    valley = plain + ( level - plain ) * _smooth( 0.0, LOWLAND[1], dv - FLOODPLAIN )
    low = level + reach * ( valley - level )

    # The town's hill falling to it, its fall stretched along its spurs.
    angle = math.atan2( n - CENTRE[1], e - CENTRE[0] )
    spur = _fbm( SPURS[1] * math.cos( angle ), SPURS[1] * math.sin( angle ), SPURS[2], 3, 0.5, 3, 1.0, grads )
    dt = d / ( 1.0 + SPURS[0] * spur * _smooth( 0.0, 1500.0, d ) )
    h = -250.0 + ( low + 250.0 ) * _hermite( dt, FALL_D, FALL, FALL_SLOPES )

    # The hills, their feet fading out short of the town, which stands on its own hill's top.
    hills = _hills( e, n, cutoff, grads ) * _smooth( 600.0, 8000.0, d )
    h += hills

    # Rolling relief: gentle on the town's hill, more out in the valleys and most on the hills, warped so its folds
    # aren't aligned.
    wx = 3000.0 * _fbm( e, n, 24000.0, 2, 0.5, 11, cutoff, grads )
    wy = 3000.0 * _fbm( e, n, 24000.0, 2, 0.5, 12, cutoff, grads )
    amp = 35.0 + 330.0 * _smooth( 1500.0, 12000.0, d ) + 0.12 * hills
    h += amp * _fbm( e + wx, n + wy, RELIEF[0], 9, RELIEF[1], 21, cutoff, grads )

    # Ridged crests on the far hills and mountains.
    far = _smooth( MOUNTAINS[0], MOUNTAINS[1], d )
    if far > 0.0:
        h += far * MOUNTAINS[2] * ( _ridged( e + 2.0 * wx, n + 2.0 * wy, 26000.0, 8, 0.42, 31, cutoff, grads ) - 0.25 )

    # The floodplain itself flat, the river's bed in it.
    if reach > 0.0:
        if dv < FLOODPLAIN + FLOODPLAIN_BLEND:
            h += reach * ( 1.0 - _smooth( FLOODPLAIN, FLOODPLAIN + FLOODPLAIN_BLEND, dv ) ) * ( plain - h )
        # The river winds no more than RIVER_SWING from the valley's middle, so only there can its bed be.
        if dv < RIVER_SWING + RIVER_BED * 1.6:
            dr = _river_distance( e, n )
            if dr < RIVER_BED * 1.6:
                h -= reach * 140.0 * ( 1.0 - _smooth( RIVER_BED * 0.4, RIVER_BED * 1.6, dr ) )

    # The rim: nowhere on the last rings is the land low enough for the horizon to show over its edge.
    rim = _smooth( RIM[0], RIM[1], d )
    if rim > 0.0:
        floor = RIM[2] + 900.0 * _fbm( e, n, 14000.0, 3, 0.5, 41, cutoff, grads )
        if h < floor:
            h += rim * ( floor - h )
    return h


@numba.njit( parallel=True, cache=True, fastmath=True )
def _heights( e, n, cutoff, grads, out ):
    for i in numba.prange( e.size ):
        out[i] = _height( e[i], n[i], cutoff[i], grads )


def land_height( e, n, cutoff=1.0 ):
    """ The land's height at plan points, leaving out relief finer than cutoff (a length, or one per point). """
    e = np.asarray( e, float )
    n = np.asarray( n, float )
    shape = np.broadcast( e, n ).shape
    e, n = np.broadcast_to( e, shape ).ravel().copy(), np.broadcast_to( n, shape ).ravel().copy()
    cut = np.broadcast_to( np.asarray( cutoff, float ), shape ).ravel().copy()
    out = np.empty( e.size )
    _heights( e, n, cut, _GRADIENTS, out )
    return out.reshape( shape ) if shape else float( out[0] )


# ---------------------------------------------------------------------------------------------------------------------
# Forced perspective: past SCALE[0] out from the walls, the land plays a landscape further off than it is. A point d out
# is drawn as if it were scale( d ) times as far from the town's middle (its apparent place), so whatever is painted or
# stands there is drawn 1 / scale( d ) of its real size, and the fog thickens towards the horizon to match. scale rises
# from 1 with no kink, so the land's patterns grow no faster at the walls' foot than out from it: 1.07 at 3000 out,
# 1.7 at 12000, 2.6 at the river, 2.9 on the ridges west and east (660 m off, playing 1.9 km), 4.8 at 50000 and 8 at the
# land's edge (2.3 km, playing 18 km).
#
# A radial map can't keep shapes: it stretches the land along the way out from the town more than across it. So only
# patterns (fields, rows, districts) are laid out at the apparent place; things (trees, bales, buildings) stand where
# their apparent place says but are drawn round, at their real size over scale.
SCALE = ( 1200.0, 2000.0, 12400.0 )


@numba.njit( cache=True, fastmath=True, inline="always" )
def _scale( d ):
    """ ( scale, its rate of change with d ) at d out from the town's rectangle. """
    x = max( d - SCALE[0], 0.0 )
    q = SCALE[2] * ( x + SCALE[1] )
    return 1.0 + x * x / q, ( x * x + 2.0 * SCALE[1] * x ) / ( q * ( x + SCALE[1] ) )


@numba.njit( cache=True, fastmath=True )
def _apparent( e, n ):
    """ The apparent place of plan point ( e, n ): ( E, N, scale, and the map's Jacobian dP / dp as j11 j12 j21 j22,
    rows E and N, columns e and n ). """
    d, ue, un = _town_offset( e, n )
    s, ds = _scale( d )
    re, rn = e - CENTRE[0], n - CENTRE[1]
    if d <= 0.0:
        ue = un = 0.0
    return ( CENTRE[0] + re * s, CENTRE[1] + rn * s, s,
             s + re * ds * ue, re * ds * un, rn * ds * ue, s + rn * ds * un )


def scale( d ):
    """ The forced perspective's scale at d out from the town's rectangle (see SCALE). """
    x = np.maximum( np.asarray( d, float ) - SCALE[0], 0.0 )
    return 1.0 + x * x / ( SCALE[2] * ( x + SCALE[1] ) )


def apparent( e, n ):
    """ The apparent places ( E, N ) of plan points, and their scales. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    s = scale( town_distance( e, n ) )
    return CENTRE[0] + ( e - CENTRE[0] ) * s, CENTRE[1] + ( n - CENTRE[1] ) * s, s


def real_place( pe, pn ):
    """ The plan points whose apparent places are ( pe, pn ): along the ray from the town's middle, by halving. """
    pe, pn = np.asarray( pe, float ), np.asarray( pn, float )
    lo, hi = np.zeros( np.broadcast( pe, pn ).shape ), np.ones( np.broadcast( pe, pn ).shape )
    for _ in range( 60 ):
        mid = ( lo + hi ) / 2
        e, n = CENTRE[0] + ( pe - CENTRE[0] ) * mid, CENTRE[1] + ( pn - CENTRE[1] ) * mid
        reach = mid * scale( town_distance( e, n ) )
        lo, hi = np.where( reach < 1.0, mid, lo ), np.where( reach < 1.0, hi, mid )
    mid = ( lo + hi ) / 2
    return CENTRE[0] + ( pe - CENTRE[0] ) * mid, CENTRE[1] + ( pn - CENTRE[1] ) * mid


def town_distance( e, n ):
    """ How far plan points are outside the town's rectangle (0 inside). """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    de = np.maximum( np.maximum( TE0 - e, e - TE1 ), 0.0 )
    dn = np.maximum( np.maximum( TN0 - n, n - TN1 ), 0.0 )
    return np.hypot( de, dn )


def river_line( e ):
    e = np.asarray( e, float )
    n = np.full_like( e, RIVER_N )
    for a, w, p in RIVER_WAVES:
        n = n + a * np.sin( 2 * np.pi * e / w + p )
    return n


# ---------------------------------------------------------------------------------------------------------------------
# The land's mesh: rings round the town's rectangle

def ring_step( d ):
    """ The rings' spacing at d out: about 1.4 degrees seen from the town, at least 36. """
    return np.clip( 0.025 * ( np.asarray( d, float ) + 1200.0 ), 36.0, 2500.0 )


def ring_distances():
    """ The rings' distances out from the walls, every ring_step. """
    rings, d = [ 0.0 ], 0.0
    while d < REACH:
        d = min( d + float( ring_step( d ) ), REACH )
        rings.append( d )
    return np.array( rings )


def ring_points( d, count ):
    """ count points round the ring d out from the town's rectangle, evenly along it, starting due east of the middle
    and going anticlockwise; and each one's angle round the middle. """
    a, b = ( TE1 - TE0 ) / 2, ( TN1 - TN0 ) / 2
    # The rounded rectangle's outline, finely, by arc length.
    fine = 8192
    theta = np.linspace( 0, 2 * np.pi, fine, endpoint=False )
    ct, st = np.cos( theta ), np.sin( theta )
    # Where the ray from the middle at theta meets the outline: solve by halving.
    lo, hi = np.zeros( fine ), np.full( fine, a + b + d + 10.0 )
    for _ in range( 50 ):
        mid = ( lo + hi ) / 2
        x, y = mid * ct, mid * st
        dist = np.hypot( np.maximum( np.abs( x ) - a, 0 ), np.maximum( np.abs( y ) - b, 0 ) )
        inside = ( dist < d ) & ( np.abs( x ) <= a + d + 1e-9 ) & ( np.abs( y ) <= b + d + 1e-9 )
        if d <= 0:
            inside = ( np.abs( x ) <= a ) & ( np.abs( y ) <= b )
        lo, hi = np.where( inside, mid, lo ), np.where( inside, hi, mid )
    r = ( lo + hi ) / 2
    px, py = r * ct, r * st
    seg = np.hypot( np.diff( np.append( px, px[0] ) ), np.diff( np.append( py, py[0] ) ) )
    arc = np.concatenate( ( [ 0 ], np.cumsum( seg ) ) )
    want = np.linspace( 0, arc[-1], count, endpoint=False )
    t = np.interp( want, arc, np.append( theta, 2 * np.pi ) )
    ct, st = np.cos( t ), np.sin( t )
    lo, hi = np.zeros( count ), np.full( count, a + b + d + 10.0 )
    for _ in range( 50 ):
        mid = ( lo + hi ) / 2
        x, y = mid * ct, mid * st
        if d <= 0:
            inside = ( np.abs( x ) <= a ) & ( np.abs( y ) <= b )
        else:
            inside = np.hypot( np.maximum( np.abs( x ) - a, 0 ), np.maximum( np.abs( y ) - b, 0 ) ) < d
        lo, hi = np.where( inside, mid, lo ), np.where( inside, hi, mid )
    r = ( lo + hi ) / 2
    return np.stack( ( CENTRE[0] + r * ct, CENTRE[1] + r * st ), -1 ), t


def zipper( theta_a, theta_b, base_a, base_b ):
    """ Triangles between two rings of points sorted by angle (both starting at 0 and going round once). """
    na, nb = len( theta_a ), len( theta_b )
    ta = np.append( theta_a, theta_a[0] + 2 * np.pi )
    tb = np.append( theta_b, theta_b[0] + 2 * np.pi )
    tris = []
    i = j = 0
    while i < na or j < nb:
        if j >= nb or ( i < na and ta[i + 1] <= tb[j + 1] ):
            tris.append( ( base_a + i % na, base_b + j % nb, base_a + ( i + 1 ) % na ) )
            i += 1
        else:
            tris.append( ( base_a + i % na, base_b + j % nb, base_b + ( j + 1 ) % nb ) )
            j += 1
    return tris


def land_mesh( step_scale=1.0 ):
    """ The land's vertices ( V, 3 ), normals ( V, 3 ) and triangles ( T, 3 ), wound to face up. Each vertex is the land
    as seen at its ring's spacing. """
    rings = ring_distances()
    points, thetas, spacing = [], [], []
    for k, d in enumerate( rings ):
        gap = rings[min( k + 1, len( rings ) - 1 )] - rings[max( k - 1, 0 )]
        along = float( ring_step( d ) ) * step_scale
        perimeter = 2 * ( ( TE1 - TE0 ) + ( TN1 - TN0 ) ) + 2 * np.pi * d
        count = int( max( perimeter / along, 720 if d < 20000 else 1440 ) )
        p, t = ring_points( d, count )
        points.append( p )
        thetas.append( t )
        spacing.append( np.full( count, max( along, gap / 2 ) ) )
    tris = []
    base = np.cumsum( [ 0 ] + [ len( p ) for p in points ] )
    for k in range( len( rings ) - 1 ):
        tris += zipper( thetas[k], thetas[k + 1], base[k], base[k + 1] )
    plan = np.concatenate( points )
    cut = np.concatenate( spacing )
    z = land_height( plan[:, 0], plan[:, 1], cut )
    verts = np.column_stack( ( plan, z ) )
    tris = np.array( tris, np.int64 )
    # Up-facing: the rings run anticlockwise, so the zipper's triangles are wound clockwise seen from above.
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    up = np.cross( b - a, c - a )[:, 2]
    tris[up < 0] = tris[up < 0][:, ::-1]
    # Normals from the land at the same cutoff (central differences half a spacing across).
    h = cut * 0.5
    dzde = ( land_height( plan[:, 0] + h, plan[:, 1], cut ) - land_height( plan[:, 0] - h, plan[:, 1], cut ) ) / ( 2 * h )
    dzdn = ( land_height( plan[:, 0], plan[:, 1] + h, cut ) - land_height( plan[:, 0], plan[:, 1] - h, cut ) ) / ( 2 * h )
    normals = np.column_stack( ( -dzde, -dzdn, np.ones_like( dzde ) ) )
    normals /= np.linalg.norm( normals, axis=1, keepdims=True )
    return verts, normals, tris, rings


# ---------------------------------------------------------------------------------------------------------------------
# Previews: the land and the town's own models (their last written OBJs) from the town's streets, under the sky
# panorama, lit by the sun and fogged as the scene's GradientFog fogs them, through the tonemap a match uses.

PREVIEW_VIEWS = [
    # name, eye, target (plan), fov
    ( "west_street_west", ( -250, 125, 64 ), ( -8000, 125, 520 ), 80 ),
    ( "east_street_east", ( 250, 125, 64 ), ( 8000, 125, 520 ), 80 ),
    ( "square_west", ( -380, -330, 64 ), ( -9000, 600, 300 ), 80 ),
    ( "gardens_south", ( -640, -1230, 16 ), ( -2000, -9000, -1200 ), 80 ),
    ( "terrace_south", ( -700, -950, 64 ), ( 1500, -9000, -900 ), 80 ),
    ( "market_street_west", ( -150, 1300, 64 ), ( -9000, 1275, 300 ), 80 ),
    ( "north_row_north", ( 600, 1500, 64 ), ( 2000, 9000, 400 ), 80 ),
    ( "council_hall_east", ( -380, 620, 232 ), ( 9000, -2000, 400 ), 90 ),
    ( "aerial", ( -9000, -11000, 6000 ), ( 0, 200, -800 ), 75 ),
]


@numba.njit( cache=True )
def _rasterise( screen, nearness, colours, image, zbuf ):
    """ Triangles ( T, 3 ) in pixels, with 1 / depth at each corner and colours ( T, 3, 3 ) interpolated perspective-
    correct, into image ( H, W, 3 ) over a depth buffer where larger is nearer. """
    height, width = zbuf.shape
    for t in range( screen.shape[0] ):
        ax, ay = screen[t, 0, 0], screen[t, 0, 1]
        bx, by = screen[t, 1, 0], screen[t, 1, 1]
        cx, cy = screen[t, 2, 0], screen[t, 2, 1]
        x0 = max( int( math.floor( min( ax, min( bx, cx ) ) ) ), 0 )
        x1 = min( int( math.ceil( max( ax, max( bx, cx ) ) ) ), width - 1 )
        y0 = max( int( math.floor( min( ay, min( by, cy ) ) ) ), 0 )
        y1 = min( int( math.ceil( max( ay, max( by, cy ) ) ) ), height - 1 )
        if x1 < x0 or y1 < y0:
            continue
        area = ( bx - ax ) * ( cy - ay ) - ( by - ay ) * ( cx - ax )
        if abs( area ) < 1e-12:
            continue
        for y in range( y0, y1 + 1 ):
            py = y + 0.5
            for x in range( x0, x1 + 1 ):
                px = x + 0.5
                w0 = ( ( bx - px ) * ( cy - py ) - ( by - py ) * ( cx - px ) ) / area
                w1 = ( ( cx - px ) * ( ay - py ) - ( cy - py ) * ( ax - px ) ) / area
                w2 = 1.0 - w0 - w1
                if w0 < -1e-7 or w1 < -1e-7 or w2 < -1e-7:
                    continue
                q0, q1, q2 = w0 * nearness[t, 0], w1 * nearness[t, 1], w2 * nearness[t, 2]
                z = q0 + q1 + q2
                if z <= zbuf[y, x]:
                    continue
                zbuf[y, x] = z
                for c in range( 3 ):
                    image[y, x, c] = ( q0 * colours[t, 0, c] + q1 * colours[t, 1, c] + q2 * colours[t, 2, c] ) / z


def town_triangles():
    """ The town's models as last written: triangles ( T, 3, 3 ) in plan, their normals and each one's paint. """
    tris, paints = [], []
    for name in ( "belltower_centre", "belltower_west", "belltower_east" ):
        verts, faces, face_paints, paint = [], [], [], None
        with open( MODEL_DIR / f"{name}.obj", encoding="utf-8" ) as f:
            for line in f:
                if line.startswith( "v " ):
                    x, y, z = line.split()[1:4]
                    verts.append( ( -float( x ), float( z ), float( y ) ) )
                elif line.startswith( "f " ):
                    faces.append( [ int( p.split( "/" )[0] ) - 1 for p in line.split()[1:4] ] )
                    face_paints.append( paint )
                elif line.startswith( "usemtl" ):
                    paint = line.split()[1]
        tris.append( np.array( verts )[np.array( faces )] )
        paints += face_paints
    tris = np.concatenate( tris )
    normals = np.cross( tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0] )
    normals /= np.maximum( np.linalg.norm( normals, axis=1, keepdims=True ), 1e-9 )
    return tris, normals, paints


class Look:
    """ The scene's light, sky and fog, and the tonemap a match shows them through. """

    def __init__( self ):
        import belltower_map as BM
        import belltower_sky as S
        self.S = S
        self.sky = S.read_exr( S.OUT_DIR / f"{S.NAME}.exr" )
        self.sun_colour = np.array( ( 1.32, 1.06, 0.76 ) )
        self.ambient = np.array( ( 0.30, 0.40, 0.58 ) )
        self.fog_colour = np.array( [ float( c ) for c in BM.FOG_COLOUR.split( "," ) ] )
        self.fog = dict( alpha=0.75, start=3000.0, end=95000.0, falloff=1.5, z=5000.0, height=9000.0, vertical=1.0 )

    def fog_amount( self, eye, points ):
        f = self.fog
        dist = np.hypot( points[..., 0] - eye[0], points[..., 1] - eye[1] )
        d = np.clip( ( dist - f["start"] ) / ( f["end"] - f["start"] ), 0, 1 ) ** f["falloff"]
        v = np.clip( 1 - ( points[..., 2] - f["z"] ) / f["height"], 0, 1 ) ** f["vertical"]
        return f["alpha"] * d * v

    def light( self, albedo, normals ):
        """ Linear HDR colour of sunlit albedo (linear) facing normals ( plan ). """
        ndl = np.clip( normals @ SUN, 0, None )[..., None]
        sky = ( 0.55 + 0.45 * normals[..., 2:3] )
        return albedo * ( self.sun_colour * ndl + self.ambient * sky )

    def sky_colour( self, eye, directions ):
        """ The panorama in plan directions ( ..., 3 ), fogged as the scene fogs the sky (at 100000 out). """
        world = np.stack( ( directions[..., 1], -directions[..., 0], directions[..., 2] ), -1 )
        u, v = self.S.panorama_uv( world )
        h, w = self.sky.shape[:2]
        coords = ( np.clip( v * h - 0.5, 0, h - 1 ), u * w - 0.5 )
        colour = np.stack( [ ndimage.map_coordinates( self.sky[..., c], coords, order=1, mode="grid-wrap" )
                             for c in range( 3 ) ], -1 )
        far = eye + directions * 100000.0
        f = self.fog_amount( eye, far )[..., None]
        return colour * ( 1 - f ) + self.fog_colour * f


def camera( eye, target, size, fov ):
    eye, target = np.asarray( eye, float ), np.asarray( target, float )
    forward = target - eye
    forward /= np.linalg.norm( forward )
    right = np.cross( forward, ( 0.0, 0.0, 1.0 ) )
    right /= np.linalg.norm( right )
    up = np.cross( right, forward )
    focal = ( size[0] / 2 ) / math.tan( math.radians( fov ) / 2 )
    return eye, forward, right, up, focal


def render_view( look, scene, eye, target, size=( 1280, 720 ), fov=80.0 ):
    """ scene: a list of ( triangles ( T, 3, 3 ) in plan, colours ( T, 3, 3 ) linear HDR before fog ). """
    width, height = size
    eye, forward, right, up, focal = camera( eye, target, size, fov )
    xs = ( np.arange( width ) + 0.5 - width / 2 ) / focal
    ys = ( height / 2 - np.arange( height ) - 0.5 ) / focal
    rays = forward + xs[None, :, None] * right + ys[:, None, None] * up
    rays /= np.linalg.norm( rays, axis=2, keepdims=True )
    image = look.sky_colour( eye, rays ).astype( np.float64 )
    zbuf = np.zeros( ( height, width ) )
    near = 4.0
    for tris, colours in scene:
        rel = tris - eye
        cam = np.stack( ( rel @ right, rel @ up, rel @ forward ), axis=-1 )
        f = look.fog_amount( eye, tris )[..., None]
        cols = colours * ( 1 - f ) + look.fog_colour * f
        depth = cam[:, :, 2]
        whole = depth.min( axis=1 ) >= near
        parts = depth.max( axis=1 ) >= near
        pieces, piece_colours = [ cam[whole] ], [ cols[whole] ]
        for k in np.nonzero( parts & ~whole )[0]:
            # Clip at the near plane, carrying the colours along.
            points, cs = [], []
            for i in range( 3 ):
                a, b = cam[k, i], cam[k, ( i + 1 ) % 3]
                ca, cb = cols[k, i], cols[k, ( i + 1 ) % 3]
                if a[2] >= near:
                    points.append( a )
                    cs.append( ca )
                if ( a[2] >= near ) != ( b[2] >= near ):
                    s = ( near - a[2] ) / ( b[2] - a[2] )
                    points.append( a + s * ( b - a ) )
                    cs.append( ca + s * ( cb - ca ) )
            for i in range( 1, len( points ) - 1 ):
                pieces.append( np.array( ( points[0], points[i], points[i + 1] ) )[None] )
                piece_colours.append( np.array( ( cs[0], cs[i], cs[i + 1] ) )[None] )
        cam, cols = np.concatenate( pieces ), np.concatenate( piece_colours )
        screen = np.stack( ( width / 2 + focal * cam[:, :, 0] / cam[:, :, 2],
                             height / 2 - focal * cam[:, :, 1] / cam[:, :, 2] ), axis=-1 )
        _rasterise( np.ascontiguousarray( screen ), np.ascontiguousarray( 1.0 / cam[:, :, 2] ),
                    np.ascontiguousarray( cols ), image, zbuf )
    return Image.fromarray( look.S.display( image ) )


def preview_land_albedo( verts, normals ):
    """ Rough land colours for checking the shape: fields, woods, olives on the terraces, rock up high and steep. """
    e, n, z = verts[:, 0], verts[:, 1], verts[:, 2]
    rng_noise = land_height( e * 3.1 + 77000.0, n * 3.1 - 51000.0, 1.0 )      # any smooth field will do
    d = town_distance( e, n )
    slope = np.degrees( np.arccos( np.clip( normals[:, 2], -1, 1 ) ) )
    fields = np.array( [ ( 196, 172, 112 ), ( 124, 138, 72 ), ( 150, 118, 86 ), ( 112, 124, 62 ) ] )
    pick = ( ( np.floor( e / 1700.0 ) * 7 + np.floor( n / 1300.0 ) * 13 ) % 4 ).astype( int )
    albedo = fields[pick].astype( float )
    woods = ( np.sin( rng_noise / 900.0 ) > 0.2 ) | ( z > 1500 )
    albedo[woods] = ( 66, 82, 44 )
    olives = ( d > 300 ) & ( d < 4200 )
    albedo[olives] = ( 128, 130, 96 )
    rock = ( slope > 34 ) | ( z > 6500 )
    albedo[rock] = ( 146, 140, 128 )
    plain = np.abs( n - river_line( e ) ) < FLOODPLAIN
    albedo[plain & ~rock] = ( 104, 132, 66 )
    return ( albedo / 255.0 ) ** 2.2


def write_land_previews( out_dir, views=None ):
    out_dir = Path( out_dir )
    out_dir.mkdir( parents=True, exist_ok=True )
    import belltower_map as BM
    look = Look()
    t0 = time.time()
    verts, normals, tris, rings = land_mesh()
    land_colours = look.light( preview_land_albedo( verts, normals ), normals )
    scene = [ ( verts[tris], land_colours[tris] ) ]
    town, town_normals, paints = town_triangles()
    albedo = np.array( [ BM.paint_colour( p ) for p in sorted( set( paints ) ) ] ) ** 2.2
    index = { p: k for k, p in enumerate( sorted( set( paints ) ) ) }
    town_albedo = albedo[[ index[p] for p in paints ]]
    town_colours = look.light( town_albedo, town_normals )
    scene.append( ( town, np.repeat( town_colours[:, None, :], 3, axis=1 ) ) )
    print( f"scene ready in {time.time() - t0:.1f} s: {len( tris )} land and {len( town )} town triangles" )
    for name, eye, target, fov in PREVIEW_VIEWS:
        if views and name not in views:
            continue
        t1 = time.time()
        render_view( look, scene, eye, target, fov=fov ).save( out_dir / f"{name}.png" )
        print( f"wrote {out_dir / name}.png in {time.time() - t1:.1f} s" )


def slope_report( verts, normals ):
    """ How much of the land, out to the mountains, is steeper than a hillside farm would be. """
    d = town_distance( verts[:, 0], verts[:, 1] )
    slope = np.degrees( np.arccos( np.clip( normals[:, 2], -1, 1 ) ) )
    for lo, hi in ( ( 0, 1500 ), ( 1500, 6000 ), ( 6000, 20000 ), ( 20000, 48000 ), ( 48000, REACH + 1 ) ):
        inside = ( d >= lo ) & ( d < hi )
        s = slope[inside]
        print( f"  {lo:>6.0f}-{hi:<6.0f} out: {inside.sum():>6} vertices, slope p50 {np.percentile( s, 50 ):4.1f} "
               f"p95 {np.percentile( s, 95 ):4.1f} max {s.max():4.1f}, over 30: {( s > 30 ).mean() * 100:4.1f}%, "
               f"over 34: {( s > 34 ).mean() * 100:4.1f}%" )


LAND_NAME = "belltower_vista"
LAND_MATERIAL = "materials/belltower/vista/vista_land.vmat"


def write_land( out_dir, resource_dir ):
    """ The land's model: <LAND_NAME>.obj/.mtl and .vmdl in out_dir, drawn with vista_land.vmat (Tools/
    belltower_vista_paint.py paints it), with no collision. Its vertices are shared, unlike map_kit's write_obj, which
    gives every polygon its own. Returns ( triangles, the land's lowest point ). """
    verts, normals, tris, _ = land_mesh()
    e, n, z = verts[:, 0], verts[:, 1], verts[:, 2]
    # Plan ( e, n, z ) is world ( n, -e, z ), and the OBJ is world ( y, z, x ) (ModelDoc reads it Y-up). Both keep the
    # winding, so the triangles still face up.
    lines = [ "# Tools/belltower_vista.py", f"mtllib {LAND_NAME}.mtl", f"o {LAND_NAME}" ]
    lines += [ f"v {-a:.2f} {c:.2f} {b:.2f}" for a, b, c in zip( e, n, z ) ]
    lines += [ f"vt {a / 10000:.5f} {b / 10000:.5f}" for a, b in zip( e, n ) ]
    lines += [ f"vn {-a:.4f} {c:.4f} {b:.4f}" for a, b, c in normals ]
    lines.append( "usemtl vista_land" )
    lines += [ f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}" for a, b, c in tris + 1 ]
    out_dir.mkdir( parents=True, exist_ok=True )
    K.write_text( out_dir / f"{LAND_NAME}.obj", "\n".join( lines ) + "\n" )
    K.write_text( out_dir / f"{LAND_NAME}.mtl", "newmtl vista_land\nKd 1 1 1\nd 1\n" )
    holder = K.Model()
    holder.polygons["vista_land"] = []
    holder.material_overrides["vista_land"] = LAND_MATERIAL
    K.write_vmdl( out_dir / f"{LAND_NAME}.vmdl", resource_dir, LAND_NAME, holder )
    return len( tris ), float( z.min() )


def main():
    parser = argparse.ArgumentParser( description=__doc__.split( "\n\n" )[0] )
    parser.add_argument( "--preview", type=Path, help="write views of the land from the town to this folder" )
    parser.add_argument( "--views", nargs="*", help="only these views" )
    args = parser.parse_args()
    t0 = time.time()
    verts, normals, tris, rings = land_mesh()
    print( f"{len( rings )} rings, {len( verts )} vertices, {len( tris )} triangles in {time.time() - t0:.1f} s" )
    slope_report( verts, normals )
    if args.preview:
        write_land_previews( args.preview, args.views )


if __name__ == "__main__":
    main()
