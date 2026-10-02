"""
Belltower's sky: a clear summer afternoon with fair-weather cumulus, baked into an HDR panorama for s&box's sky shader.

    python Tools/belltower_sky.py [--width 4096] [--seed N] [--out <dir>] [--preview <dir>] [--views-only]

The scene's sky was the core atmosphere shader, which has no clouds and tints its whole sky by the sun light's colour, so
the afternoon's warm light (belltower_map's LightColor) turned it a pale grey-cyan. The reference this map is dressed
after has a light summer blue, whiter towards the hills, with heaped white cumulus and a few ragged puffs.

- Its colours are made for how a match shows them: s&box's ACES (Hill's fit, core/shaders/tonemapping) at exposure
  DESIGN_EXPOSURE, where belltower_map's Look volume holds the outdoor views. Offscreen renders (Editor/Hc1BelltowerQa)
  skip post-processing, so there the sky is darker and much more saturated than in a match.
- The blue is the reference's colour at each height above the horizon (SKY_KEYS, sampled from it between its roofs),
  taken back through that tonemap. Round that, the old sky's own light (core/shaders/atmosphere_sky.shader's single
  scattering, ported with its coefficients and the way it measures its rays) brightens it round the sun and dims it
  across from it.
- The clouds are fair-weather cumulus ray-marched through a layer on a round earth, with flat bases BASE above the town
  and tops up to TOP:
  - Each heap is a pile of domes, wide at its base and narrowing to a crown, leaning a little downwind (WorldWind's
    default heading), from a few hundred metres to well over a kilometre across. Small thin puffs drift in loose
    groups. The domes are drawn into a height field: each column's top and, under a bulge, its bottom. Some stretches
    have more than others, and none crosses the sun, which lights the town.
  - Turbulent 3D noise bends the domes' outlines (a domain warp), billows swell and dent their surfaces, and finer noise
    frays their edges, less with distance and more on the thin puffs.
  - The sun lights them through the cloud between it and each point (Beer's law, with Wrenninge's octaves for the light
    scattered many times inside, and a forward-scattering phase for the bright rims towards the sun). The sky lights
    them from above and the ground from below, and with distance they fade into the haze.
- The sun's disk is where the scene's light comes from (belltower_map.SUN_PITCH and SUN_YAW), drawn as the atmosphere
  shader draws it.
- Below the horizon, which the vista's hills hide, the haze gives way to the light the sunlit ground throws up: the sky
  is also what the town reflects (SkyBox2D's SkyIndirectLighting).

It writes Assets/materials/belltower/sky/belltower_sky.exr (half floats, zip-compressed, like the core skies' sources)
and belltower_sky.vmat (core shaders/sky.shader). numba marches the clouds, skipping the empty sky by how far each column
is from the nearest cloud. --preview writes the panorama and views round the horizon, the views marched at their own
resolution and shown as a match would show them, to compare with the reference; --views-only skips the panorama and
the files.
"""
import argparse
import math
import struct
import time
import zlib
from pathlib import Path

import numba
import numpy as np
from PIL import Image
from scipy import ndimage

from belltower_map import SUN_PITCH, SUN_YAW

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/belltower/sky"
RESOURCE_DIR = "materials/belltower/sky"
NAME = "belltower_sky"

# How s&box wraps a panorama round the world: the world azimuth (degrees from x, north, towards y, west) at the
# panorama's left edge, and which way it turns along u. The texture compiler makes the panorama a cube, which the sky
# shader samples along the world direction, and u runs clockwise seen from above: north, east, south, west. Found by
# compiling a panorama with coloured marks (resourcecompiler) and reading the cube back, both its faces and its
# lighting coefficients (2026-10-02).
U0_AZIMUTH = 0.0
U_SIGN = -1.0

LUMA = np.array( ( 0.2126, 0.7152, 0.0722 ) )

# How a match shows it: s&box's ACES (Hill's fit: mul( rgb, m1 ), the rational curve, mul( ..., m2 )) at the exposure
# belltower_map's Look volume holds outdoors at.
DESIGN_EXPOSURE = 2.0
ACES_IN = np.array( ( ( 0.59719, 0.07600, 0.02840 ), ( 0.35458, 0.90834, 0.13383 ), ( 0.04823, 0.01566, 0.83777 ) ) )
ACES_OUT = np.array( ( ( 1.60475, -0.10208, -0.00327 ), ( -0.53108, 1.10813, -0.07276 ),
                       ( -0.07367, -0.00605, 1.07602 ) ) )

# The sky's colour by elevation (degrees), sRGB as shown: sampled from the reference between its roofs (about 14-30
# degrees up), then carried on to the horizon and the zenith.
SKY_KEYS = ( ( 0.0, ( 200, 216, 232 ) ), ( 6.0, ( 186, 210, 232 ) ), ( 15.0, ( 168, 199, 231 ) ),
             ( 30.0, ( 140, 181, 228 ) ), ( 55.0, ( 118, 164, 222 ) ), ( 90.0, ( 104, 152, 216 ) ) )
SUN_HALO = 0.6          # how much of the old sky's brightening round the sun (and dimming across from it) is kept
HALO_WHITE = np.array( ( 1.06, 1.0, 0.9 ) )
SUN_INTENSITY = 50.0    # the atmosphere shader's
LIGHT = np.array( ( 1.32, 1.06, 0.76 ) )                # belltower_map's sun LightColor
GROUND = np.array( ( 0.24, 0.22, 0.18 ) )               # sunlit fields and scrub, as the town's light shows them

# The cloud layer, metres above the town.
BASE, TOP = 1400.0, 2700.0
BASE_FADE = 40.0        # metres over which a base thickens: flat, sharp bases
HEAPS = 0.1             # heaps per square kilometre, before the field thins them
HEAP_GROUP = ( 2.2, 1200.0 )                            # in groups of about this many, this far apart
HEAP_SIZE = ( 600.0, 0.5, 220.0, 1800.0 )                # their radius: lognormal median and spread, and limits
HEAP_HEIGHT = ( 0.7, 1.4 )                              # their height, times the radius
PUFF_GROUPS = 0.07      # groups of small thin puffs per square kilometre
FIELD_SCALE = 18000.0   # the size of the stretches with more or fewer clouds
SUN_GAP = 1800.0        # no cloud within this of where the sun's light to the town crosses the layer
WIND_TOWARDS = -53.0    # WorldWind's default heading: the heaps' crowns lean this way
# Every eighth of the sky gets a heap this far out (metres), 13-39 degrees up, if the field left it none: the streets,
# the square and the terrace each look out at one, as an artist would compose the sky over a level.
NEAR_RING = ( 2500.0, 6000.0 )
NEAR_SIZE = ( 700.0, 0.35, 450.0, 1100.0 )              # their radius, as HEAP_SIZE
LEAN = 0.15             # by this share of their height
WARP, WARP_TILE = 90.0, 2400.0                          # how far turbulence bends the outlines; its noise's tile
BILLOW, SHAPE_TILE = 70.0, 1500.0                       # how far billows swell or dent the surfaces; their tile
FRAY, DETAIL_TILE = 30.0, 400.0                         # how deep the fine noise frays the edges (thin puffs more)
DETAIL_NEAR, DETAIL_FAR = 6000.0, 16000.0               # the fraying fades out over these distances
SOFT = 40.0             # metres in from an edge to full density
SIGMA = 0.05            # extinction at full density, per metre (cumulus' mean free path is a few tens of metres)
EARTH = 6371e3
HAZE = 20000.0          # metres for the haze to hide 63% of a cloud: a summer day's 40-50 km visibility at the
                        # ground, thinning upwards (the haze's 1.2 km scale height) on the way to the cloud layer
MAX_T = 90000.0
WEATHER_EXTENT = 150000.0
WEATHER_SIZE = 4096
TEXEL = WEATHER_EXTENT / WEATHER_SIZE
MARGIN = WARP + 3 * TEXEL   # how far outside a column's outline the warp can carry cloud
OUTSIDE_TOP, OUTSIDE_BOTTOM = -2000.0, 4000.0           # columns without cloud: far from any surface, so the outline
                                                        # cuts off within a texel
STEP_SHARE, STEP_MIN, STEP_MAX = 0.0012, 10.0, 90.0     # the march's steps inside a cloud: a share of the distance

# The clouds' light: the sun's, and the sky's from above and the ground's from below, as radiance a white cloud shows.
CLOUD_SUN = LIGHT * 1.1
AMB_HIGH = np.array( ( 0.15, 0.33, 0.8 ) )               # the sky's, about its upper half's mean
AMB_LOW = np.array( ( 0.26, 0.27, 0.3 ) )                # the ground's and the haze's round the horizon
AMB_OCCLUSION = 0.35
SIDE_LIGHT = 0.3        # the share of each that comes in from the sides, whatever cloud is above or below
MS_A, MS_B, MS_C = 0.6, 0.38, 0.5      # Wrenninge's octaves: energy, extinction and anisotropy kept per octave
G_FORWARD, G_BACK, BACK_SHARE = 0.72, -0.22, 0.3
LIGHT_STEPS = ( 18.0, 36.0, 72.0, 144.0, 288.0, 600.0 )

# ( name, yaw from north towards west or None for one round the sun, pitch, horizontal field of view )
PREVIEW_VIEWS = ( ( "reference", None, 16, 75 ), ( "towards_sun", None, 18, 85 ), ( "away", None, 18, 85 ),
                  ( "west_street", 90, 16, 80 ), ( "east_street", -90, 16, 80 ), ( "north", 0, 12, 85 ),
                  ( "south", 180, 12, 85 ), ( "up", None, 62, 90 ) )
VIEW_OFF_SUN = { "reference": -130, "towards_sun": 0, "away": 180, "up": 90 }


def smoothstep( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def srgb_linear( c ):
    c = np.asarray( c, float ) / 255
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def sun_direction():
    """ Towards the sun: the scene's light points along its forward, pitch down and yaw round from x. """
    p, y = math.radians( SUN_PITCH ), math.radians( SUN_YAW )
    return -np.array( ( math.cos( p ) * math.cos( y ), math.cos( p ) * math.sin( y ), -math.sin( p ) ) )


def panorama_directions( w, h, rows=None ):
    """ The world direction of each texel's centre, ( rows, w, 3 ). """
    rows = range( h ) if rows is None else rows
    v = ( np.asarray( rows, float ) + 0.5 ) / h
    u = ( np.arange( w ) + 0.5 ) / w
    el = ( 0.5 - v ) * math.pi
    az = math.radians( U0_AZIMUTH ) + U_SIGN * 2 * math.pi * u
    ce = np.cos( el )[:, None]
    return np.stack( ( ce * np.cos( az )[None, :], ce * np.sin( az )[None, :],
                       np.broadcast_to( np.sin( el )[:, None], ( len( el ), w ) ) ), -1 )


def panorama_uv( d ):
    """ The panorama's u, v (0..1) for world directions. """
    az = np.arctan2( d[..., 1], d[..., 0] )
    u = ( ( az - math.radians( U0_AZIMUTH ) ) * U_SIGN / ( 2 * math.pi ) ) % 1.0
    v = 0.5 - np.arcsin( np.clip( d[..., 2], -1, 1 ) ) / math.pi
    return u, v


def view_directions( yaw, pitch, fov, size ):
    """ A camera at the town looking at yaw (degrees from x towards y) and pitch up, fov across: ( h, w, 3 ). """
    w, h = size
    f = 0.5 * w / math.tan( math.radians( fov ) / 2 )
    xs, ys = np.meshgrid( np.arange( w ) - w / 2 + 0.5, h / 2 - np.arange( h ) - 0.5 )
    cy, sy = math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) )
    cp, sp = math.cos( math.radians( pitch ) ), math.sin( math.radians( pitch ) )
    forward = np.array( ( cp * cy, cp * sy, sp ) )
    left = np.array( ( -sy, cy, 0.0 ) )
    up = np.cross( forward, left )
    d = forward * f - left * xs[..., None] + up * ys[..., None]
    return d / np.linalg.norm( d, axis=-1, keepdims=True )


# ---------------------------------------------------------------------------------------------------------------------
# How a match shows it

def aces( rgb ):
    """ s&box's ACES on linear colours already scaled by the exposure, to linear display colours. """
    v = rgb @ ACES_IN
    a = v * ( v + 0.0245786 ) - 0.000090537
    b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081
    return np.clip( ( a / b ) @ ACES_OUT, 0, 1 )


def display( rgb, exposure=DESIGN_EXPOSURE ):
    """ The sRGB bytes a match shows for these linear HDR colours. """
    x = aces( np.maximum( rgb, 0 ) * exposure )
    x = np.where( x <= 0.0031308, 12.92 * x, 1.055 * np.power( x, 1 / 2.4 ) - 0.055 )
    return np.clip( np.rint( x * 255 ), 0, 255 ).astype( np.uint8 )


def undisplay( srgb, exposure=DESIGN_EXPOSURE ):
    """ The linear HDR colour a match shows as these sRGB bytes: the tonemap taken back (its curve is a ratio of
    quadratics, so each channel solves a quadratic). """
    y = np.clip( srgb_linear( srgb ) @ np.linalg.inv( ACES_OUT ), 1e-5, 0.999 )
    a = 1 - 0.983729 * y
    b = 0.0245786 - 0.4329510 * y
    c = -( 0.000090537 + 0.238081 * y )
    v = ( -b + np.sqrt( b * b - 4 * a * c ) ) / ( 2 * a )
    return np.maximum( v @ np.linalg.inv( ACES_IN ), 1e-5 ) / exposure


# ---------------------------------------------------------------------------------------------------------------------
# The blue

def ray_sphere( o, v, radius ):
    """ RaySphereIntersection: the two distances, or ( 1e5, -1e5 ) for a miss. """
    a = np.sum( v * v, -1 )
    b = 2 * np.sum( v * o, -1 )
    c = np.sum( o * o, -1 ) - radius * radius
    disc = b * b - 4 * a * c
    root = np.sqrt( np.maximum( disc, 0 ) )
    miss = disc < 0
    return np.where( miss, 1e5, ( -b - root ) * 0.5 / a ), np.where( miss, -1e5, ( -b + root ) * 0.5 / a )


def atmosphere( v, sun ):
    """ atmosphere_sky.shader's atmosphere() for directions v ( n, 3 ), z up, as GetAtmosphere calls it: a camera 600 up
    (its sea level plus the town), sun intensity 50, a planet of 6371 km under 100 km of air. Its march runs from the
    camera over the distance between the ray's two crossings of the atmosphere, clipped at the ground, as the shader's
    does. """
    planet, air = 6371e3, 6371e3 + 100e3
    rayleigh, mie = np.array( ( 5.5e-6, 13.0e-6, 22.4e-6 ) ), 21e-6
    h_rayleigh, h_mie, g = 8e3, 1.2e3, 0.758
    origin = np.array( ( 0.0, 0.0, planet + 600.0 ) )
    x, y = ray_sphere( origin, v, air )
    inside = x <= y
    y = np.minimum( y, ray_sphere( origin, v, planet )[0] )
    step = ( y - x ) / 16
    cos = v @ sun
    phase_r = 3 / ( 16 * math.pi ) * ( 1 + cos * cos )
    phase_m = 3 / ( 8 * math.pi ) * ( ( 1 - g * g ) * ( cos * cos + 1 ) /
                                      ( np.power( 1 + g * g - 2 * cos * g, 1.5 ) * ( 2 + g * g ) ) )
    depth_r, depth_m = np.zeros( len( v ) ), np.zeros( len( v ) )
    sum_r, sum_m = np.zeros( ( len( v ), 3 ) ), np.zeros( ( len( v ), 3 ) )
    t = np.zeros( len( v ) )
    for _ in range( 16 ):
        p = origin + v * ( t + step * 0.5 )[:, None]
        height = np.linalg.norm( p, axis=-1 ) - planet
        step_r = np.exp( -height / h_rayleigh ) * step
        step_m = np.exp( -height / h_mie ) * step
        depth_r += step_r
        depth_m += step_m
        light_step = ray_sphere( p, np.broadcast_to( sun, p.shape ), air )[1] / 2
        light_r, light_m, s = np.zeros( len( v ) ), np.zeros( len( v ) ), np.zeros( len( v ) )
        for _ in range( 2 ):
            q = p + sun * ( s + light_step * 0.5 )[:, None]
            q_height = np.linalg.norm( q, axis=-1 ) - planet
            light_r += np.exp( -q_height / h_rayleigh ) * light_step
            light_m += np.exp( -q_height / h_mie ) * light_step
            s += light_step
        through = np.exp( -( mie * ( depth_m + light_m ) )[:, None] - rayleigh * ( depth_r + light_r )[:, None] )
        sum_r += step_r[:, None] * through
        sum_m += step_m[:, None] * through
        t += step
    colour = SUN_INTENSITY * ( phase_r[:, None] * rayleigh * sum_r + ( phase_m * mie )[:, None] * sum_m )
    return np.where( inside[:, None], colour, 0.0 )


def reference_sky( el_deg ):
    """ The linear colour a match shows as the reference's sky at these elevations, interpolated between the keys by
    ratios (in log space). """
    keys = np.array( [ k for k, _ in SKY_KEYS ] )
    logs = np.log( np.array( [ undisplay( c ) for _, c in SKY_KEYS ] ) )
    return np.exp( np.stack( [ np.interp( el_deg, keys, logs[:, c] ) for c in range( 3 ) ], -1 ) )


def clear_sky_base( w, h, sun ):
    """ The cloudless sky without the sun's disk, on a w x h panorama: the reference's colours, brightened round the sun
    and dimmed across from it by some of the old sky's own variation, and whitened in its glare. Under the horizon it
    mirrors the sky. """
    d = panorama_directions( w, h )
    lum = atmosphere( d.reshape( -1, 3 ), sun ).reshape( h, w, 3 ) @ LUMA
    variation = ( lum / np.maximum( lum.mean( 1 )[:, None], 1e-9 ) ) ** SUN_HALO
    el = np.degrees( np.arcsin( np.clip( d[:, 0, 2], -1, 1 ) ) )
    sky = reference_sky( np.abs( el ) )[:, None, :] * variation[..., None]
    halo = np.clip( variation - 1, 0, None )
    white = ( halo / ( halo + 1.0 ) )[..., None]
    return sky * ( 1 - white ) + ( sky @ LUMA )[..., None] * ( HALO_WHITE / float( HALO_WHITE @ LUMA ) ) * white


def clear_sky_at( d, base, sun ):
    """ The cloudless sky in directions d ( ..., 3 ): the base, the sun's disk, and the ground's light under the
    horizon. """
    bh, bw = base.shape[:2]
    u, v = panorama_uv( d )
    coords = ( np.clip( v * bh - 0.5, 0, bh - 1 ), u * bw - 0.5 )
    sky = np.stack( [ ndimage.map_coordinates( base[..., c], coords, order=1, mode="grid-wrap" ) for c in range( 3 ) ],
                    -1 )
    # The sun's disk, as the shader draws it (pow( dot + 0.00025, 10000 ) * 10), in the scene's light's colour.
    disk = np.power( np.clip( d @ sun + 0.00025, 0, None ), 10000.0 ) * 10 * np.clip( d[..., 2], 0, 1 )
    sky += disk[..., None] * LIGHT
    below = smoothstep( 0.0, -0.12, np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )[..., None]
    return sky * ( 1 - below ) + GROUND * below


# ---------------------------------------------------------------------------------------------------------------------
# Noise

@numba.njit( parallel=True, cache=True )
def _perlin_volume( n, grads ):
    """ Tileable 3D gradient noise from a period^3 lattice of unit gradients, n^3 texels, about -1..1. """
    period = grads.shape[0]
    out = np.zeros( ( n, n, n ), np.float32 )
    for z in numba.prange( n ):
        for y in range( n ):
            for x in range( n ):
                px, py, pz = x * period / n, y * period / n, z * period / n
                ix, iy, iz = int( px ), int( py ), int( pz )
                fx, fy, fz = px - ix, py - iy, pz - iz
                ux = fx * fx * fx * ( fx * ( fx * 6 - 15 ) + 10 )
                uy = fy * fy * fy * ( fy * ( fy * 6 - 15 ) + 10 )
                uz = fz * fz * fz * ( fz * ( fz * 6 - 15 ) + 10 )
                total = 0.0
                for dz in range( 2 ):
                    for dy in range( 2 ):
                        for dx in range( 2 ):
                            g = grads[( iz + dz ) % period, ( iy + dy ) % period, ( ix + dx ) % period]
                            dot = g[0] * ( fx - dx ) + g[1] * ( fy - dy ) + g[2] * ( fz - dz )
                            weight = ( ux if dx else 1 - ux ) * ( uy if dy else 1 - uy ) * ( uz if dz else 1 - uz )
                            total += weight * dot
                out[z, y, x] = total * 1.6
    return out


@numba.njit( parallel=True, cache=True )
def _worley_volume( n, points ):
    """ Tileable 3D Worley noise inverted, n^3 texels, from one point per cell ( cells^3 x 3, 0..1 within the cell ): 1
    at each point, falling to 0 a cell away. """
    cells = points.shape[0]
    out = np.zeros( ( n, n, n ), np.float32 )
    for z in numba.prange( n ):
        for y in range( n ):
            for x in range( n ):
                px, py, pz = ( x + 0.5 ) * cells / n, ( y + 0.5 ) * cells / n, ( z + 0.5 ) * cells / n
                ix, iy, iz = int( px ), int( py ), int( pz )
                best = 9.0
                for dz in range( -1, 2 ):
                    for dy in range( -1, 2 ):
                        for dx in range( -1, 2 ):
                            cx, cy, cz = ix + dx, iy + dy, iz + dz
                            p = points[cz % cells, cy % cells, cx % cells]
                            ex = cx + p[0] - px
                            ey = cy + p[1] - py
                            ez = cz + p[2] - pz
                            dist = ex * ex + ey * ey + ez * ez
                            if dist < best:
                                best = dist
                out[z, y, x] = max( 0.0, 1.0 - math.sqrt( best ) )
    return out


def noise_volumes( rng, n=128 ):
    """ The shape volume (Schneider's Perlin-Worley: rounded billows a twelfth to a third of its tile across), centred
    on 0 and about -1..1, and the detail volume (Worley octaves, 0..1 about 0.5). """

    def perlin( period ):
        grads = rng.normal( size=( period, period, period, 3 ) )
        return _perlin_volume( n, grads / np.linalg.norm( grads, axis=-1, keepdims=True ) )

    def worley( cells ):
        return _worley_volume( n, rng.random( ( cells, cells, cells, 3 ) ) )

    p = np.clip( ( 0.55 * perlin( 3 ) + 0.3 * perlin( 6 ) + 0.15 * perlin( 12 ) ) * 0.5 + 0.5, 0, 1 )
    w = 0.55 * worley( 6 ) + 0.3 * worley( 12 ) + 0.15 * worley( 24 )
    w /= w.max()
    shape = 0.4 * np.clip( ( p - ( w - 1 ) ) / ( 2 - w ), 0, 1 ) + 0.6 * w
    shape -= shape.mean()
    detail = 0.55 * worley( 6 ) + 0.3 * worley( 12 ) + 0.15 * worley( 24 )
    detail = np.clip( detail / detail.max() - ( detail / detail.max() ).mean() + 0.5, 0, 1 )
    return ( shape / np.abs( shape ).max() ).astype( np.float32 ), detail.astype( np.float32 )


def fbm2( rng, n, scale ):
    """ Smooth 2D noise, about -1..1, with features scale texels across. """
    total = np.zeros( ( n, n ) )
    for k, amp in enumerate( ( 1.0, 0.5, 0.25 ) ):
        s = scale / 2 ** k
        cells = max( 2, int( n / s ) + 2 )
        grid = rng.normal( 0, 1, ( cells, cells ) )
        total += amp * ndimage.zoom( grid, n / ( cells - 1 ), order=3 )[:n, :n]
    return total / 1.3


# ---------------------------------------------------------------------------------------------------------------------
# Where the clouds are

def heap_domes( rng, x, y, r, top, lean ):
    """ One cumulus heap of r radius and top metres high: domes ( x, y, z, radius, density ) piled wide at its base and
    narrowing to a crown, the higher ones further downwind. """
    domes = []
    for k in range( 6 + int( 10 * r / 500 ) ):
        if k < 3:
            f, rho = 0.0, r * rng.uniform( 0.35, 0.55 )
        else:
            f = rng.random() ** 1.3
            rho = r * rng.uniform( 0.28, 0.5 ) * ( 1 - 0.45 * f )
        off = max( r * ( 1 - 0.65 * f ) - rho, 0.0 ) * math.sqrt( rng.random() )
        a = rng.uniform( 0, 2 * math.pi )
        domes.append( ( x + off * math.cos( a ) + lean[0] * f, y + off * math.sin( a ) + lean[1] * f,
                        f * max( top - rho, 0.0 ), rho, 1.0 ) )
    rho = r * rng.uniform( 0.3, 0.42 )
    domes.append( ( x + lean[0], y + lean[1], max( top - rho, 0.0 ), rho, 1.0 ) )
    return domes


def puff_domes( rng, x, y ):
    """ A loose group of small thin puffs (cumulus fractus), which the fraying tears up. """
    domes = []
    spread = rng.uniform( 250, 900 )
    for _ in range( int( rng.integers( 3, 9 ) ) ):
        a = rng.uniform( 0, 2 * math.pi )
        off = spread * math.sqrt( rng.random() )
        rho = rng.uniform( 50, 200 )
        domes.append( ( x + off * math.cos( a ), y + off * math.sin( a ),
                        rng.uniform( 0, 250 ) + rho * rng.uniform( -0.4, 0.2 ), rho, rng.uniform( 0.35, 0.8 ) ) )
    return domes


@numba.njit( cache=True )
def _draw_domes( domes, n, texel, top, bottom, strength ):
    """ Each column's top (its highest dome's), bottom (its lowest dome's underside, at least the base) and density (its
    densest dome's). """
    half = n * 0.5
    for k in range( domes.shape[0] ):
        cx, cy, cz, rho, s = domes[k, 0], domes[k, 1], domes[k, 2], domes[k, 3], domes[k, 4]
        i0 = max( int( ( cx - rho ) / texel + half ), 0 )
        i1 = min( int( ( cx + rho ) / texel + half ) + 1, n - 1 )
        j0 = max( int( ( cy - rho ) / texel + half ), 0 )
        j1 = min( int( ( cy + rho ) / texel + half ) + 1, n - 1 )
        for j in range( j0, j1 + 1 ):
            yy = ( j - half + 0.5 ) * texel - cy
            for i in range( i0, i1 + 1 ):
                xx = ( i - half + 0.5 ) * texel - cx
                d2 = rho * rho - xx * xx - yy * yy
                if d2 <= 0.0:
                    continue
                up = math.sqrt( d2 )
                hi = cz + up
                if hi <= 0.0:
                    continue
                if hi > top[j, i]:
                    top[j, i] = hi
                lo = max( cz - up, 0.0 )
                if lo < bottom[j, i]:
                    bottom[j, i] = lo
                if s > strength[j, i]:
                    strength[j, i] = s


def weather( rng, sun ):
    """ The clouds as a height field over the town: each column's top and bottom (metres above the base), its density,
    and how far it is from the nearest cloud. """
    n, coarse = WEATHER_SIZE, 512
    field = 0.2 + 0.8 * smoothstep( -0.45, 0.55, fbm2( rng, coarse, FIELD_SCALE / ( WEATHER_EXTENT / coarse ) ) )
    km2 = ( WEATHER_EXTENT / 1000 ) ** 2
    flat = math.hypot( sun[0], sun[1] )
    near, far = BASE / sun[2] * flat, TOP / sun[2] * flat
    wind = np.array( ( math.cos( math.radians( WIND_TOWARDS ) ), math.sin( math.radians( WIND_TOWARDS ) ) ) )

    def clear_of_sun( x, y, reach ):
        along = ( x * sun[0] + y * sun[1] ) / flat
        across = ( -x * sun[1] + y * sun[0] ) / flat
        return math.hypot( across, along - min( max( along, near ), far ) ) - reach >= SUN_GAP

    def welcome( x, y, reach ):
        if not clear_of_sun( x, y, reach ):
            return False
        i = int( np.clip( ( x / WEATHER_EXTENT + 0.5 ) * coarse, 0, coarse - 1 ) )
        j = int( np.clip( ( y / WEATHER_EXTENT + 0.5 ) * coarse, 0, coarse - 1 ) )
        return rng.random() < field[j, i]

    domes, heaps, groups, centres = [], 0, 0, []
    median, spread, smallest, largest = HEAP_SIZE
    size, apart = HEAP_GROUP
    for _ in range( int( HEAPS / size * km2 ) ):
        gx, gy = rng.uniform( -WEATHER_EXTENT / 2, WEATHER_EXTENT / 2, 2 )
        for _ in range( 1 + int( rng.poisson( size - 1 ) ) ):
            x, y = gx + rng.normal( 0, apart ), gy + rng.normal( 0, apart )
            r = float( np.clip( rng.lognormal( math.log( median ), spread ), smallest, largest ) )
            if welcome( x, y, r * 1.3 ):
                top = min( r * rng.uniform( *HEAP_HEIGHT ), TOP - BASE )
                domes += heap_domes( rng, x, y, r, top, wind * LEAN * top )
                heaps += 1
                centres.append( ( x, y ) )
    for _ in range( int( PUFF_GROUPS * km2 ) ):
        x, y = rng.uniform( -WEATHER_EXTENT / 2, WEATHER_EXTENT / 2, 2 )
        if welcome( x, y, 1100.0 ):
            domes += puff_domes( rng, x, y )
            groups += 1

    # The near ring, after everything else so the rest of the sky is the same with or without it.
    ring, (median, spread, smallest, largest) = 0, NEAR_SIZE
    inner, outer = NEAR_RING
    for sector in range( 8 ):
        a0 = sector * math.pi / 4
        if any( inner <= math.hypot( x, y ) <= outer and int( ( math.atan2( y, x ) % ( 2 * math.pi ) ) // ( math.pi / 4 ) ) == sector
                for x, y in centres ):
            continue
        for _ in range( 30 ):
            a, d = a0 + rng.uniform( 0.1, 0.685 ), rng.uniform( inner, outer )
            r = float( np.clip( rng.lognormal( math.log( median ), spread ), smallest, largest ) )
            x, y = d * math.cos( a ), d * math.sin( a )
            if clear_of_sun( x, y, r * 1.3 ):
                top = min( r * rng.uniform( *HEAP_HEIGHT ), TOP - BASE )
                domes += heap_domes( rng, x, y, r, top, wind * LEAN * top )
                heaps, ring = heaps + 1, ring + 1
                break

    top = np.zeros( ( n, n ), np.float32 )
    bottom = np.full( ( n, n ), 1e9, np.float32 )
    strength = np.zeros( ( n, n ), np.float32 )
    _draw_domes( np.array( domes, np.float64 ), n, TEXEL, top, bottom, strength )
    inside = top > 0
    top[~inside] = OUTSIDE_TOP
    bottom[~inside] = OUTSIDE_BOTTOM
    room = ( ndimage.distance_transform_edt( ~inside ) * TEXEL ).astype( np.float32 )
    print( f"{heaps} heaps ({ring} of them in the near ring) and {groups} groups of puffs, {len( domes )} domes; "
           f"{inside.mean() * 100:.1f}% of the ground under cloud" )
    return top, bottom, strength, room


# ---------------------------------------------------------------------------------------------------------------------
# The clouds' march

@numba.njit( fastmath=True, inline="always" )
def _bilinear( tex, u, v ):
    n = tex.shape[0]
    if u < 0.0 or v < 0.0 or u >= n - 1.0 or v >= n - 1.0:
        return 0.0
    i, j = int( u ), int( v )
    fu, fv = u - i, v - j
    return ( ( tex[j, i] * ( 1 - fu ) + tex[j, i + 1] * fu ) * ( 1 - fv ) +
             ( tex[j + 1, i] * ( 1 - fu ) + tex[j + 1, i + 1] * fu ) * fv )


@numba.njit( fastmath=True, inline="always" )
def _trilinear( tex, x, y, z ):
    n = tex.shape[0]
    x -= n * math.floor( x / n )
    y -= n * math.floor( y / n )
    z -= n * math.floor( z / n )
    i, j, k = int( x ) % n, int( y ) % n, int( z ) % n
    i1, j1, k1 = ( i + 1 ) % n, ( j + 1 ) % n, ( k + 1 ) % n
    fx, fy, fz = x - math.floor( x ), y - math.floor( y ), z - math.floor( z )
    c00 = tex[k, j, i] * ( 1 - fx ) + tex[k, j, i1] * fx
    c10 = tex[k, j1, i] * ( 1 - fx ) + tex[k, j1, i1] * fx
    c01 = tex[k1, j, i] * ( 1 - fx ) + tex[k1, j, i1] * fx
    c11 = tex[k1, j1, i] * ( 1 - fx ) + tex[k1, j1, i1] * fx
    return ( c00 * ( 1 - fy ) + c10 * fy ) * ( 1 - fz ) + ( c01 * ( 1 - fy ) + c11 * fy ) * fz


@numba.njit( fastmath=True, inline="always" )
def _room( room, x, y ):
    """ How far the column at x, y is from the nearest cloud's outline, metres; -1 off the map. """
    n = room.shape[0]
    i, j = int( x / TEXEL + n * 0.5 ), int( y / TEXEL + n * 0.5 )
    if i < 1 or j < 1 or i >= n - 1 or j >= n - 1:
        return -1.0
    return room[j, i]


@numba.njit( fastmath=True, inline="always" )
def _density( x, y, h, t, top, bottom, strength, room, shape, detail ):
    """ The cloud's density at x, y (metres from the town) and h (height), seen from t away, 0..1. """
    rel = h - BASE
    if rel <= 0.0 or rel >= TOP - BASE + BILLOW:
        return 0.0
    space = _room( room, x, y )
    if space < 0.0 or space > MARGIN:
        return 0.0
    n = top.shape[0]
    half = n * 0.5 - 0.5
    ns = shape.shape[0]
    k = ns / WARP_TILE
    wx = _trilinear( shape, x * k, y * k, h * k ) * WARP
    wy = _trilinear( shape, x * k + 61.3, y * k + 23.9, h * k + 47.1 ) * WARP
    u, v = ( x + wx ) / TEXEL + half, ( y + wy ) / TEXEL + half
    s = min( _bilinear( top, u, v ) - rel, rel - _bilinear( bottom, u, v ) )
    if s < -BILLOW:
        return 0.0
    k = ns / SHAPE_TILE
    s += _trilinear( shape, x * k, y * k, h * k ) * BILLOW
    if s <= 0.0:
        return 0.0
    st = _bilinear( strength, u, v )
    if st <= 0.0:
        return 0.0
    # Frayed by the fine noise near to, and by its mean further off, where it's finer than a pixel.
    near = 1.0 - min( max( ( t - DETAIL_NEAR ) / ( DETAIL_FAR - DETAIL_NEAR ), 0.0 ), 1.0 )
    fray = 0.5
    if near > 0.0:
        nd = detail.shape[0]
        k = nd / DETAIL_TILE
        fray += ( 0.5 - _trilinear( detail, x * k, y * k, h * k ) ) * near
    s -= fray * FRAY * ( 2.0 - st )
    if s <= 0.0:
        return 0.0
    base = min( rel / BASE_FADE, 1.0 )
    return min( s / SOFT, 1.0 ) * base * base * ( 3 - 2 * base ) * st


@numba.njit( fastmath=True, inline="always" )
def _hg( cos, g ):
    """ Henyey-Greenstein, times 4 pi (1 for light scattered evenly). """
    return ( 1 - g * g ) / ( 1 + g * g - 2 * g * cos ) ** 1.5


@numba.njit( parallel=True, fastmath=True )
def _march( dirs, sky, sun, top, bottom, strength, room, shape, detail, cloud_sun, amb_high, amb_low ):
    """ Each direction's colour with the clouds in front of its sky ( rows, w, 3 ), and how much of the sky shows. """
    rows, w = dirs.shape[0], dirs.shape[1]
    out = np.empty( ( rows, w, 3 ), np.float32 )
    clear = np.ones( ( rows, w ), np.float32 )
    for j in numba.prange( rows ):
        for i in range( w ):
            dx, dy, dz = dirs[j, i, 0], dirs[j, i, 1], dirs[j, i, 2]
            r, g, b = sky[j, i, 0], sky[j, i, 1], sky[j, i, 2]
            out[j, i, 0], out[j, i, 1], out[j, i, 2] = r, g, b
            if dz <= 0.0:
                continue
            # Where the ray crosses the layer's base and top, on a round earth from the ground.
            t0 = -EARTH * dz + math.sqrt( ( EARTH * dz ) ** 2 + 2 * EARTH * BASE + BASE * BASE )
            t1 = -EARTH * dz + math.sqrt( ( EARTH * dz ) ** 2 + 2 * EARTH * ( TOP + BILLOW ) +
                                          ( TOP + BILLOW ) ** 2 )
            if t0 > MAX_T:
                continue
            t1 = min( t1, MAX_T )
            flat = max( math.sqrt( dx * dx + dy * dy ), 1e-4 )
            # A fixed jitter per texel (interleaved gradient noise), so the steps don't band.
            jitter = ( 52.9829189 * ( ( 0.06711056 * i + 0.00583715 * j ) % 1.0 ) ) % 1.0
            cos = dx * sun[0] + dy * sun[1] + dz * sun[2]
            through = 1.0
            lr, lg, lb = 0.0, 0.0, 0.0
            t = t0
            skipped = True
            for _ in range( 6000 ):
                if t >= t1:
                    break
                x, y = dx * t, dy * t
                space = _room( room, x, y )
                if space < 0.0:
                    break
                dt = min( max( t * STEP_SHARE, STEP_MIN ), STEP_MAX )
                if space > MARGIN:
                    # Nothing nearer than that: on to where the ray could first reach a cloud.
                    t += ( space - MARGIN ) / flat + dt * 0.5
                    skipped = True
                    continue
                if skipped:
                    t += dt * jitter
                    skipped = False
                    x, y = dx * t, dy * t
                h = math.sqrt( EARTH * EARTH + t * t + 2 * EARTH * t * dz ) - EARTH
                dens = _density( x, y, h, t, top, bottom, strength, room, shape, detail )
                if dens > 0.0:
                    # The sun through the cloud between it and here, the samples spread a little per texel so the
                    # shading doesn't terrace.
                    tau, gone = 0.0, 0.0
                    for s in LIGHT_STEPS:
                        mid = gone + s * ( 0.25 + 0.5 * jitter )
                        tau += _density( x + sun[0] * mid, y + sun[1] * mid, h + sun[2] * mid, t, top, bottom,
                                         strength, room, shape, detail ) * s
                        gone += s
                    tau *= SIGMA
                    lit, energy, ext, aniso = 0.0, 1.0, 1.0, 1.0
                    for _k in range( 4 ):
                        p = ( 1 - BACK_SHARE ) * _hg( cos, G_FORWARD * aniso ) + BACK_SHARE * _hg( cos, G_BACK * aniso )
                        lit += energy * p * math.exp( -ext * tau )
                        energy *= MS_A
                        ext *= MS_B
                        aniso *= MS_C
                    # The sky's light from above and the ground's from below, less what the cloud over and under here
                    # shades, though some comes in from the sides.
                    up = ( _density( x, y, h + 60.0, t, top, bottom, strength, room, shape, detail ) * 80.0 +
                           _density( x, y, h + 220.0, t, top, bottom, strength, room, shape, detail ) * 240.0 ) * SIGMA
                    down = ( _density( x, y, h - 60.0, t, top, bottom, strength, room, shape, detail ) * 80.0 +
                             _density( x, y, h - 220.0, t, top, bottom, strength, room, shape, detail ) * 240.0 ) * SIGMA
                    above = SIDE_LIGHT + ( 1 - SIDE_LIGHT ) * math.exp( -AMB_OCCLUSION * up )
                    below = SIDE_LIGHT + ( 1 - SIDE_LIGHT ) * math.exp( -AMB_OCCLUSION * down )
                    sr = cloud_sun[0] * lit + amb_high[0] * above + amb_low[0] * below
                    sg = cloud_sun[1] * lit + amb_high[1] * above + amb_low[1] * below
                    sb = cloud_sun[2] * lit + amb_high[2] * above + amb_low[2] * below
                    # The haze between here and the eye.
                    fade = math.exp( -t / HAZE )
                    sr = sr * fade + r * ( 1 - fade )
                    sg = sg * fade + g * ( 1 - fade )
                    sb = sb * fade + b * ( 1 - fade )
                    step_through = math.exp( -dens * SIGMA * dt )
                    taken = through * ( 1 - step_through )
                    lr += taken * sr
                    lg += taken * sg
                    lb += taken * sb
                    through *= step_through
                    if through < 0.003:
                        through = 0.0
                        break
                t += dt
            out[j, i, 0] = r * through + lr
            out[j, i, 1] = g * through + lg
            out[j, i, 2] = b * through + lb
            clear[j, i] = through
    return out, clear


# ---------------------------------------------------------------------------------------------------------------------
# Writing it

def write_exr( path, rgb ):
    """ A scanline EXR of half floats, zip-compressed in blocks of 16 lines (OpenEXR's ZIP_COMPRESSION). """
    h, w = rgb.shape[:2]
    half = np.ascontiguousarray( rgb.astype( np.float16 ) )

    def attribute( name, kind, data ):
        return name.encode() + b"\0" + kind.encode() + b"\0" + struct.pack( "<i", len( data ) ) + data

    channels = b"".join( c.encode() + b"\0" + struct.pack( "<iB3xii", 1, 0, 1, 1 ) for c in "BGR" ) + b"\0"
    header = ( struct.pack( "<ii", 20000630, 2 ) +
               attribute( "channels", "chlist", channels ) +
               attribute( "compression", "compression", b"\x03" ) +
               attribute( "dataWindow", "box2i", struct.pack( "<iiii", 0, 0, w - 1, h - 1 ) ) +
               attribute( "displayWindow", "box2i", struct.pack( "<iiii", 0, 0, w - 1, h - 1 ) ) +
               attribute( "lineOrder", "lineOrder", b"\0" ) +
               attribute( "pixelAspectRatio", "float", struct.pack( "<f", 1.0 ) ) +
               attribute( "screenWindowCenter", "v2f", struct.pack( "<ff", 0.0, 0.0 ) ) +
               attribute( "screenWindowWidth", "float", struct.pack( "<f", 1.0 ) ) + b"\0" )
    blocks = []
    for y0 in range( 0, h, 16 ):
        lines = half[y0:y0 + 16]
        raw = b"".join( line[:, c].tobytes() for line in lines for c in ( 2, 1, 0 ) )
        a = np.frombuffer( raw, np.uint8 )
        mixed = np.concatenate( ( a[0::2], a[1::2] ) ).astype( np.int16 )
        mixed[1:] = ( mixed[1:] - mixed[:-1] + 128 ) & 255
        packed = zlib.compress( mixed.astype( np.uint8 ).tobytes(), 6 )
        if len( packed ) >= len( raw ):
            packed = raw
        blocks.append( struct.pack( "<ii", y0, len( packed ) ) + packed )
    offsets, at = [], len( header ) + 8 * len( blocks )
    for block in blocks:
        offsets.append( at )
        at += len( block )
    with open( path, "wb" ) as f:
        f.write( header )
        f.write( struct.pack( f"<{len( offsets )}Q", *offsets ) )
        for block in blocks:
            f.write( block )


def read_exr( path ):
    """ The panorama write_exr wrote, as float32 RGB ( h, w, 3 ). Reads only that layout: one part, scanlines of half
    floats in blocks of 16 lines, zip-compressed or raw. """
    data = Path( path ).read_bytes()
    at, attributes = 8, {}
    while data[at] != 0:
        name_end = data.index( b"\0", at )
        kind_end = data.index( b"\0", name_end + 1 )
        size = struct.unpack_from( "<i", data, kind_end + 1 )[0]
        attributes[data[at:name_end].decode()] = data[kind_end + 5:kind_end + 5 + size]
        at = kind_end + 5 + size
    at += 1
    x0, y0, x1, y1 = struct.unpack( "<iiii", attributes["dataWindow"] )
    w, h = x1 - x0 + 1, y1 - y0 + 1
    blocks = ( h + 15 ) // 16
    offsets = struct.unpack_from( f"<{blocks}Q", data, at )
    out = np.empty( ( h, w, 3 ), np.float32 )
    for offset in offsets:
        line, size = struct.unpack_from( "<ii", data, offset )
        lines = min( 16, h - line )
        packed = data[offset + 8:offset + 8 + size]
        raw_size = lines * w * 3 * 2
        if size < raw_size:
            mixed = np.frombuffer( zlib.decompress( packed ), np.uint8 ).astype( np.int64 )
            mixed[1:] -= 128
            mixed = np.cumsum( mixed ) & 255
            a = np.empty( raw_size, np.uint8 )
            a[0::2], a[1::2] = mixed[:( raw_size + 1 ) // 2], mixed[( raw_size + 1 ) // 2:]
            raw = a.tobytes()
        else:
            raw = packed
        halves = np.frombuffer( raw, np.float16 ).reshape( lines, 3, w )
        out[line:line + lines] = halves[:, ::-1].transpose( 0, 2, 1 )
    return out


def vmat_text():
    """ The core skies' material (materials/skybox/skybox_day_01.vmat). The sky shader's texture is SkyTexture: under
    any other key the compiler gives it the default texture, with no error. """
    return ( "// Tools/belltower_sky.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/sky.shader"\n'
             '    F_TEXTURE_FORMAT2 "6"\n'
             '    g_flBrightnessExposureBias "0"\n'
             '    g_flRenderOnlyExposureBias "0"\n'
             f'    SkyTexture "{RESOURCE_DIR}/{NAME}.exr"\n'
             "}\n" )


def shade( d, base, sun, maps, ss ):
    """ The sky with its clouds in directions d ( h * ss, w * ss, 3 ), averaged down ss x ss: the colour and how much
    of the sky shows. """
    out, clear = _march( d, clear_sky_at( d, base, sun ), sun, *maps, CLOUD_SUN, AMB_HIGH, AMB_LOW )
    h, w = d.shape[0] // ss, d.shape[1] // ss
    return out.reshape( h, ss, w, ss, 3 ).mean( ( 1, 3 ) ), clear.reshape( h, ss, w, ss ).mean( ( 1, 3 ) )


def cloud_share( d, clear ):
    """ The share of the sky from 2 degrees up that's mostly cloud, by solid angle where d is a panorama's. """
    up = d[..., 2] > math.sin( math.radians( 2 ) )
    weight = np.sqrt( np.clip( 1 - d[..., 2] ** 2, 0, 1 ) )
    return float( np.sum( weight * ( ( clear < 0.5 ) & up ) ) / max( np.sum( weight * up ), 1e-9 ) )


def describe( shown, clear, d ):
    """ How a view's clouds and clear sky look as shown: the sunlit clouds (their brightest 5%), the shaded ones (their
    darkest fifth), and the clear sky 15 and 30 degrees up. """
    lum = shown.astype( float ) @ LUMA
    cloud = clear < 0.15
    parts = [ f"{np.mean( clear < 0.5 ) * 100:.1f}% cloud" ]
    if cloud.sum() > 50:
        bright, dark = np.percentile( lum[cloud], 95 ), np.percentile( lum[cloud], 20 )
        parts.append( f"sunlit {np.round( shown[cloud & ( lum >= bright )].mean( 0 ) ).astype( int )}" )
        parts.append( f"shaded {np.round( shown[cloud & ( lum <= dark )].mean( 0 ) ).astype( int )}" )
    el = np.degrees( np.arcsin( np.clip( d[..., 2], -1, 1 ) ) )
    for at in ( 15, 30 ):
        band = ( np.abs( el - at ) < 1.0 ) & ( clear > 0.99 )
        if band.sum() > 20:
            parts.append( f"sky {at}: {np.round( shown[band].mean( 0 ) ).astype( int )}" )
    return ", ".join( parts )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--width", type=int, default=4096 )
    parser.add_argument( "--seed", type=int, default=7 )
    parser.add_argument( "--out", type=Path, default=OUT_DIR )
    parser.add_argument( "--preview", type=Path )
    parser.add_argument( "--views-only", action="store_true" )
    parser.add_argument( "--view-width", type=int, default=960 )
    parser.add_argument( "--supersample", type=int, default=2, help="rays per texel across (and down)" )
    args = parser.parse_args()
    ss = args.supersample
    start = time.time()
    sun = sun_direction()
    rng = np.random.default_rng( args.seed )

    base = clear_sky_base( 1024, 512, sun )
    shape, detail = noise_volumes( rng )
    maps = weather( rng, sun ) + ( shape, detail )
    print( f"sky, noise and weather in {time.time() - start:.1f} s" )

    if args.preview:
        args.preview.mkdir( parents=True, exist_ok=True )
        yaw_sun = math.degrees( math.atan2( sun[1], sun[0] ) )
        for name, yaw, pitch, fov in PREVIEW_VIEWS:
            if yaw is None:
                yaw = yaw_sun + VIEW_OFF_SUN[name]
            size = ( args.view_width, args.view_width * 9 // 16 )
            out, clear = shade( view_directions( yaw, pitch, fov, ( size[0] * ss, size[1] * ss ) ), base, sun, maps, ss )
            d = view_directions( yaw, pitch, fov, size )
            shown = display( out )
            Image.fromarray( shown ).save( args.preview / f"{name}.png" )
            print( f"  {name}: {describe( shown, clear, d )}; {time.time() - start:.1f} s" )

    if args.views_only:
        return
    w, h = args.width, args.width // 2
    d = panorama_directions( w, h )
    pano = clear_sky_at( d, base, sun )
    upper = h // 2
    clear = np.ones( ( upper, w ), np.float32 )
    band = 64
    for row in range( 0, upper, band ):
        rows = range( row * ss, min( row + band, upper ) * ss )
        pano[row:row + band], clear[row:row + band] = shade( panorama_directions( w * ss, h * ss, rows ), base, sun,
                                                             maps, ss )
    lit = pano[:upper][clear < 0.2]
    print( f"{cloud_share( d[:upper], clear ) * 100:.1f}% of the sky from 2 degrees up is cloud; brightest cloud "
           f"{np.round( np.percentile( lit, 99, axis=0 ), 3 ) if len( lit ) else '-'}; marched in "
           f"{time.time() - start:.1f} s" )

    args.out.mkdir( parents=True, exist_ok=True )
    write_exr( args.out / f"{NAME}.exr", pano.astype( np.float32 ) )
    text = vmat_text()
    path = args.out / f"{NAME}.vmat"
    if not path.exists() or path.read_text( encoding="utf-8" ) != text:
        path.write_text( text, encoding="utf-8", newline="\n" )
    print( "wrote", args.out / f"{NAME}.exr" )
    if args.preview:
        small = pano[::2, ::2] if w > 2048 else pano
        Image.fromarray( display( small ) ).save( args.preview / "panorama.png" )


if __name__ == "__main__":
    main()
