"""
Ridgeback, the battle royale map: a valley about 1.2 km across, ringed by mountains, with a dry river through the
middle, flat pads where the towns will go and road beds between them. This builds its terrain, and with --scene the
starting scene. Heights are in world units (inches); north is +X, as on the battle royale radar.

    python Tools/ridgeback_map.py [--scene] [--preview <png>]

- Writes Assets/scenes/maps/Ridgeback/ridgeback.terrain, a TerrainStorage in the pre-blob JSON form ("Maps" holding
  base64 of raw-deflated arrays, __version 2), which the engine's own upgrader turns into its blob on load. Saving the
  terrain or the scene in the editor writes the new form (a header, with the maps in ridgeback.terrain_d). Hand edits
  made in the editor's terrain tools are lost if this script runs again.
- Paints the ground too (`paint`): the materials from Tools/terrain_textures.py (meadow, dry meadow, dirt, gravel,
  rock, scree) by height, slope, sun and closeness to the river, with the sites, roads and river bed laid over them.
  Each sample's two strongest materials go in the splat map, blended. The preview's `_ground.png` shows the result.
- --scene also writes ridgeback.scene: the terrain, its grass (clutter), sun, sky, fog, the map's invisible walls, the first circle
  (BattleRoyaleArea), the battle royale mode, the game setup and a spawn point at each site. Only on the first run: the scene is hand-edited after that, so this
  refuses to overwrite it (delete it to start again).

Layout (east, north), valley radius about 24500:
  Town (centre), Farm (NW), Airfield (N), Lumber Camp (NE), Quarry (SW, a pit), Military Base (SE), Radio Hill (S,
  flat-topped), West Camp and East Crossing (small outposts). The river runs west to east through gorges in the ring,
  roads cross it at fords.
"""
import argparse
import base64
import json
import math
import uuid
import zlib
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path( __file__ ).resolve().parent.parent
ASSETS = ROOT / "Assets"
MAP_DIR = ASSETS / "scenes/maps/Ridgeback"
TERRAIN_FILE = MAP_DIR / "ridgeback.terrain"
SCENE_FILE = MAP_DIR / "ridgeback.scene"
TERRAIN_RESOURCE = "scenes/maps/ridgeback/ridgeback.terrain"
GRASS_RESOURCE = "scenes/maps/ridgeback/ridgeback_grass.clutter"     # Tools/ridgeback_grass.py

TITLE = "Ridgeback"
RES = 2048                     # heightmap samples per side
SIZE = 61440.0                 # terrain width, units (1.56 km)
CELL = SIZE / RES              # 30 units between samples
HALF = SIZE / 2
HEIGHT = 13000.0               # TerrainHeight: the range the 16-bit heights cover (0.2 units a step)
BASE_Z = -2000.0               # world z of height 0: the terrain object sits here
SEED = 1729

VALLEY_RADIUS = 24500.0        # where the foothills start, give or take RING_WOBBLE
RING_WOBBLE = 1900.0
FOOTHILL_WIDTH = 3500.0        # walkable foothills (under ~30 degrees) round the valley's edge
FOOTHILL_HEIGHT = 1200.0
MOUNTAIN_RISE = 6000.0         # then mountains too steep to climb, from the foothills' middle to full height
PAD_SLOPE = 22                 # cut and fill round the flattened sites, degrees
NAV_BOUNDS = 28500.0           # navmesh bounds either side of the centre (the valley, not the mountains)
AREA_RADIUS = 24000.0          # the first circle (BattleRoyaleArea): the valley, not the ledges up in the mountains

# Sites: name, (east, north), pad radius. Pads are flattened to their own average height.
SITES = [
    ( "Town", ( 1500, -2000 ), 3400 ),
    ( "Farm", ( -13000, 10000 ), 2800 ),
    ( "Lumber Camp", ( 15500, 12000 ), 2000 ),
    ( "Quarry", ( -15000, -9000 ), 3200 ),
    ( "Military Base", ( 15000, -10000 ), 3400 ),
    ( "West Camp", ( -20000, -6000 ), 1500 ),
    ( "East Crossing", ( 21000, -1500 ), 1500 ),
]
AIRFIELD = ( ( -3500, 15500 ), ( 6500, 16500 ), 1100 )     # runway ends (east, north) and half-width
RADIO_HILL = ( ( -2500, -16000 ), 2400, 5500, 900 )         # centre, height, radius, flat top radius
QUARRY_PIT = ( 1000, 1000, 32 )                             # floor radius, depth, wall angle (deg)

# Big hills with no site on them: (east, north), height, radius.
HILLS = [
    ( ( -7500, -5500 ), 1300, 4200 ),
    ( ( 8500, 10500 ), 1500, 4600 ),
    ( ( -8000, 18000 ), 1400, 3800 ),
    ( ( 9000, -15500 ), 1200, 3600 ),
    ( ( -19500, 4500 ), 900, 3000 ),
]

# The river, west to east through gorges in the ring.
RIVER = [ ( -32000, 3500 ), ( -24000, 5200 ), ( -17000, 3800 ), ( -10500, 5600 ), ( -4500, 7200 ), ( 1500, 6400 ),
          ( 7500, 4000 ), ( 13000, 2600 ), ( 19000, 4200 ), ( 25000, 2000 ), ( 32000, 500 ) ]
RIVER_BED = 380                # half-width of the flat bed
RIVER_BANK_SLOPE = 24          # banks up to the ground either side (degrees)
RIVER_DEPTH = 300              # bed below the valley floor along it
RIVER_MAX_DEPTH = 650          # never deeper than this below the ground along it

# Roads: waypoints (east, north). Road beds are flattened across and smoothed along.
ROADS = {
    "Town - Airfield": [ ( 1500, -2000 ), ( 2000, 3000 ), ( 1000, 6400 ), ( 1500, 11000 ), ( 1500, 15600 ) ],
    "Town - Farm": [ ( 1500, -2000 ), ( -4000, 1200 ), ( -9500, 5300 ), ( -13000, 10000 ) ],
    "Town - Quarry": [ ( 1500, -2000 ), ( -5500, -3000 ), ( -11000, -7200 ), ( -15000, -9000 ) ],
    "Town - Military Base": [ ( 1500, -2000 ), ( 7000, -5000 ), ( 11500, -9000 ), ( 15000, -10000 ) ],
    "Town - Radio Hill": [ ( 1500, -2000 ), ( 500, -7500 ), ( -1800, -11000 ) ],
    "Military Base - Lumber Camp": [ ( 15000, -10000 ), ( 19500, -5000 ), ( 21000, -1500 ), ( 20000, 3800 ),
                                     ( 17500, 8500 ), ( 15500, 12000 ) ],
    "Farm - Quarry": [ ( -13000, 10000 ), ( -17500, 4000 ), ( -20000, -6000 ), ( -15000, -9000 ) ],
    "Airfield - Lumber Camp": [ ( 6500, 16500 ), ( 11000, 14600 ), ( 15500, 12000 ) ],
}
ROAD_HALF = 300                # flat either side of the centre line
ROAD_SLOPE = 20                # cuttings and embankments, degrees
ROAD_SMOOTH = 1400             # along-road smoothing (sigma, units)


# ---------------------------------------------------------------------------------------------------------------------
# Grid helpers. Arrays are [j, i]: i along world X (north), j along world Y (west). Index i + j * RES, as the engine's
# heightmap. Sample (i, j) sits at the middle of its cell.

def world_of( east, north ):
    return north, -east


def grid_xy():
    axis = -HALF + ( np.arange( RES ) + 0.5 ) * CELL
    x = np.broadcast_to( axis[None, :], ( RES, RES ) )
    y = np.broadcast_to( axis[:, None], ( RES, RES ) )
    return x, y


def to_index( x, y ):
    return ( x + HALF ) / CELL - 0.5, ( y + HALF ) / CELL - 0.5


def smoothstep( t ):
    t = np.clip( t, 0.0, 1.0 )
    return t * t * ( 3.0 - 2.0 * t )


def fractal( rng, beta, fmin, fmax=None ):
    """ Periodic fractal noise, unit deviation: white noise shaped to a 1/f^beta spectrum. f is cycles per map. """
    white = rng.standard_normal( ( RES, RES ) )
    spectrum = np.fft.rfft2( white )
    fy = np.fft.fftfreq( RES )[:, None] * RES
    fx = np.fft.rfftfreq( RES )[None, :] * RES
    f = np.sqrt( fx * fx + fy * fy )
    f[0, 0] = 1.0
    amp = f ** ( -beta / 2.0 )
    amp *= smoothstep( ( f - fmin * 0.5 ) / ( fmin * 0.5 ) )
    if fmax:
        amp *= 1.0 - smoothstep( ( f - fmax ) / fmax )
    out = np.fft.irfft2( spectrum * amp, s=( RES, RES ) )
    return ( out - out.mean() ) / out.std()


def ridged( rng, base, octaves ):
    """ Ridged multifractal, 0..1: sharp crests where each octave's noise crosses zero, finer ones weaker. """
    total, weights, amp = 0.0, 0.0, 1.0
    for k in range( octaves ):
        f = base * 2 ** k
        crest = np.clip( 1.0 - np.abs( fractal( rng, 2.0, f, f * 2.0 ) ) / 2.2, 0.0, 1.0 ) ** 2
        total = total + amp * crest
        weights += amp
        amp *= 0.5
    return total / weights


def catmull_rom( points, step=10.0 ):
    """ World-space points every ~step units along a Catmull-Rom curve through (east, north) waypoints. """
    pts = np.array( [ world_of( *p ) for p in points ], dtype=float )
    padded = np.vstack( [ 2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2] ] )
    out = []
    for k in range( 1, len( padded ) - 2 ):
        p0, p1, p2, p3 = padded[k - 1], padded[k], padded[k + 1], padded[k + 2]
        n = max( 2, int( np.linalg.norm( p2 - p1 ) / step ) )
        t = np.linspace( 0.0, 1.0, n, endpoint=False )[:, None]
        out.append( 0.5 * ( 2 * p1 + ( -p0 + p2 ) * t + ( 2 * p0 - 5 * p1 + 4 * p2 - p3 ) * t * t
                            + ( -p0 + 3 * p1 - 3 * p2 + p3 ) * t * t * t ) )
    out.append( pts[-1][None, :] )
    return np.vstack( out )


class PathField:
    """ Distance from every sample to a curve (units), and which point along the curve is nearest. """

    def __init__( self, points ):
        self.points = points
        i, j = to_index( points[:, 0], points[:, 1] )
        i = np.clip( np.rint( i ).astype( int ), 0, RES - 1 )
        j = np.clip( np.rint( j ).astype( int ), 0, RES - 1 )
        mask = np.zeros( ( RES, RES ), bool )
        which = np.zeros( ( RES, RES ), np.int32 )
        mask[j, i] = True
        which[j, i] = np.arange( len( points ) )
        dist, ( jj, ii ) = ndimage.distance_transform_edt( ~mask, return_indices=True )
        self.distance = dist * CELL
        self.nearest = which[jj, ii]

    def profile_heights( self, z ):
        """ The ground's height along the curve. """
        i, j = to_index( self.points[:, 0], self.points[:, 1] )
        return ndimage.map_coordinates( z, [ j, i ], order=1, mode="nearest" )


def segment_distance( x, y, a, b ):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip( ( ( x - ax ) * dx + ( y - ay ) * dy ) / ( dx * dx + dy * dy ), 0.0, 1.0 )
    return np.hypot( x - ( ax + t * dx ), y - ( ay + t * dy ) )


def terrace( z, d, radius, target, slope, round_off=150.0 ):
    """ Flat at target out to radius (d is each sample's distance from the flat's centre, or centre line). Past that
    the ground may leave target by at most slope degrees, so cuttings and fills are never steeper. The change is
    blurred by round_off (units) so the cut's top and the fill's toe aren't sharp creases. """
    reach = np.maximum( 0.0, d - radius ) * math.tan( math.radians( slope ) )
    change = target + np.clip( z - target, -reach, reach ) - z
    return z + ndimage.gaussian_filter( change, round_off / CELL )


# ---------------------------------------------------------------------------------------------------------------------

def build():
    rng = np.random.default_rng( SEED )
    x, y = grid_xy()
    r = np.hypot( x, y )
    theta = np.arctan2( y, x )
    notes = {}

    river = PathField( catmull_rom( RIVER ) )

    # The valley floor: broad swells, rolling hills where the roughness mask allows, and a trough along the river.
    broad = fractal( rng, 3.2, 1.5, 7.0 ) * 480.0
    roughness = np.clip( 0.55 + 0.45 * fractal( rng, 4.0, 1.0, 4.0 ), 0.15, 1.0 )
    rolling = fractal( rng, 2.6, 5.0, 18.0 ) * 140.0 * roughness
    micro = fractal( rng, 2.0, 40.0, 160.0 ) * 4.0
    z = 150.0 + broad + rolling + micro
    z -= 420.0 * np.exp( -( river.distance / 5200.0 ) ** 2 )

    for centre, height, radius in HILLS + [ ( RADIO_HILL[0], RADIO_HILL[1], RADIO_HILL[2] ) ]:
        cx, cy = world_of( *centre )
        wobble = 1.0 + 0.07 * fractal( rng, 3.0, 2.0, 6.0 )
        d = np.hypot( x - cx, y - cy ) * wobble
        z += height * 0.5 * ( 1.0 + np.cos( np.pi * np.clip( d / radius, 0.0, 1.0 ) ) )

    # The ring: foothills from a wobbly edge, then ridged mountains out to the terrain's border, with gorges for the river.
    edge = VALLEY_RADIUS + sum( a * np.sin( k * theta + rng.uniform( 0, 2 * np.pi ) )
                                for k, a in ( ( 2, 0.45 ), ( 3, 0.3 ), ( 5, 0.18 ), ( 8, 0.07 ) ) ) * RING_WOBBLE
    out = r - edge
    lumps = np.clip( 0.75 + 0.25 * fractal( rng, 3.0, 4.0, 16.0 ), 0.2, 1.4 )
    crests = ridged( rng, 5.0, 4 )
    climb = out - FOOTHILL_WIDTH * 0.4
    mountains = ( FOOTHILL_HEIGHT * lumps * smoothstep( out / FOOTHILL_WIDTH )
                  + smoothstep( climb / MOUNTAIN_RISE ) * ( 2400.0 + 5600.0 * crests )
                  + np.maximum( 0.0, climb - MOUNTAIN_RISE ) * 0.08 )
    gorge = np.exp( -( river.distance / 2400.0 ) ** 2 )
    z += mountains * ( 1.0 - 0.9 * gorge )

    # The river: a bed that only ever runs downhill eastward, below the ground along it. It's cut again after the roads,
    # so they ford it rather than dam it.
    along = ndimage.gaussian_filter1d( river.profile_heights( z ), 250, mode="nearest" )
    bed = np.maximum( np.minimum.accumulate( along ) - RIVER_DEPTH, along - RIVER_MAX_DEPTH )
    bed = ndimage.gaussian_filter1d( bed, 60, mode="nearest" )
    bed_z = bed[river.nearest]
    banks = bed_z + np.maximum( 0.0, river.distance - RIVER_BED ) * math.tan( math.radians( RIVER_BANK_SLOPE ) )
    banks = ndimage.gaussian_filter( banks, 2.0 )
    z = np.minimum( z, banks )
    notes["river bed"] = ( float( bed.max() ), float( bed.min() ) )

    # Site pads.
    pads = {}
    for name, centre, radius in SITES:
        cx, cy = world_of( *centre )
        d = np.hypot( x - cx, y - cy )
        target = float( z[d < radius * 0.8].mean() )
        z = terrace( z, d, radius, target, PAD_SLOPE )
        pads[name] = target

    a, b, half = AIRFIELD
    d = segment_distance( x, y, world_of( *a ), world_of( *b ) )
    target = float( z[d < half].mean() )
    z = terrace( z, d, half, target, PAD_SLOPE )
    pads["Airfield"] = target

    # The quarry: a pit in its pad, walls walkable (32 degrees), flat floor.
    floor_radius, depth, angle = QUARRY_PIT
    qx, qy = world_of( *SITES[3][1] )
    d = np.hypot( x - qx, y - qy )
    pit = pads["Quarry"] - depth + np.maximum( 0.0, d - floor_radius ) * math.tan( math.radians( angle ) )
    z = np.minimum( z, pit )

    # Roads, one after another, each following the smoothed ground along it.
    road_fields = {}
    for name, waypoints in ROADS.items():
        field = PathField( catmull_rom( waypoints ) )
        profile = ndimage.gaussian_filter1d( field.profile_heights( z ), ROAD_SMOOTH / 10.0, mode="nearest" )
        z = terrace( z, field.distance, ROAD_HALF, profile[field.nearest], ROAD_SLOPE )
        road_fields[name] = field

    z = np.minimum( z, banks )

    # Radio Hill's flat top, for a mast or an outpost later.
    hx, hy = world_of( *RADIO_HILL[0] )
    d = np.hypot( x - hx, y - hy )
    top = float( z[d < RADIO_HILL[3] * 0.7].mean() )
    z = terrace( z, d, RADIO_HILL[3], top, 34 )
    pads["Radio Hill"] = top

    z = ndimage.gaussian_filter( z, 0.8 )

    # Stats: how much of the valley is too steep for the bots' navmesh (40 degrees).
    gy, gx = np.gradient( z, CELL )
    slope = np.degrees( np.arctan( np.hypot( gx, gy ) ) )
    valley = r < edge - 800.0
    notes["valley z"] = ( float( z[valley].min() ), float( z[valley].max() ) )
    for limit in ( 20, 30, 35, 40 ):
        notes[f"valley over {limit} deg %"] = round( float( ( slope[valley] > limit ).mean() * 100 ), 2 )
    notes["terrain z"] = ( float( z.min() ), float( z.max() ) )
    notes["slope"] = slope

    return z, pads, river, road_fields, edge, notes


def height_at( z, east, north ):
    wx, wy = world_of( east, north )
    i, j = to_index( wx, wy )
    return float( ndimage.map_coordinates( z, [ [ j ], [ i ] ], order=1, mode="nearest" )[0] )


# ---------------------------------------------------------------------------------------------------------------------
# Ground materials (drawn by Tools/terrain_textures.py), in the terrain's material order, and where each one goes.

MATERIALS = [ "meadow", "meadow_dry", "dirt", "gravel", "rock", "scree" ]
MEADOW, DRY, DIRT, GRAVEL, ROCK, SCREE = range( len( MATERIALS ) )
MATERIAL_DIR = "materials/terrain"
SUN = np.array( ( 0.384, -0.548, 0.743 ) )     # towards the scene's sun (pitch 48, yaw 125), for sunny slopes


def ramp( v, a, b ):
    """ 0 at a, 1 at b, smooth between. """
    return smoothstep( ( v - a ) / ( b - a ) )


def paint( z, slope, pads, river, roads ):
    """ How much of each material every sample gets ([material, j, i], summing to 1). Grass everywhere to start, green
    or dry; then each rule below claims a share of the ground for its material, later rules over earlier ones. The
    edges are ragged with noise and a few samples wide: the terrain blends a sample's two materials by their height
    maps (grass over soil, stones out of dirt), but between samples it only cross-fades, which shows the grid. """
    rng = np.random.default_rng( SEED + 1 )        # noise of its own, so painting never moves the ground
    x, y = grid_xy()
    fine = fractal( rng, 1.8, 60, 300 )            # ten samples or so across
    patchy = fractal( rng, 2.4, 16, 160 )          # ten to a hundred metres
    broad = fractal( rng, 3.0, 3, 24 )             # hundreds of metres
    weights = np.zeros( ( len( MATERIALS ), RES, RES ) )

    def claim( material, share ):
        share = np.clip( share, 0.0, 1.0 )
        weights[...] *= 1.0 - share
        weights[material] += share

    def near( centre, radius, soft=150.0 ):
        """ 1 inside radius of (east, north), 0 outside, over a ragged edge soft units wide. """
        cx, cy = world_of( *centre )
        return ramp( radius - np.hypot( x - cx, y - cy ) + soft * fine, -0.5 * soft, 0.5 * soft )

    # Grass: drier on slopes facing the sun, higher up and by chance, greener low down near the river.
    gy, gx = np.gradient( z, CELL )
    sunward = ( -gx * SUN[0] - gy * SUN[1] + SUN[2] ) / np.sqrt( 1.0 + gx * gx + gy * gy ) - SUN[2]
    wet = np.exp( -( river.distance / 2500.0 ) ** 2 )
    dryness = 0.6 * broad + 0.45 * patchy + 3.0 * sunward + ( z - 400.0 ) / 2500.0 - 1.1 * wet - 0.25
    weights[DRY] = ramp( dryness, -0.45, 0.45 )
    weights[MEADOW] = 1.0 - weights[DRY]

    # High in the mountains the grass gives out to stones.
    claim( SCREE, ramp( z + 700.0 * patchy + 250.0 * fine, 3300.0, 5000.0 ) )

    # Sites. Town and the camps have trodden earth in the middle, the farm lush grass round its yard, the base a
    # gravel yard, the quarry a gravel floor (its 32 degree walls are scree, below), Radio Hill a gravel top.
    site = { name: centre for name, centre, _ in SITES }
    claim( DIRT, near( site["Town"], 1100 ) + near( site["Town"], 3100 ) * ramp( patchy, 0.5, 1.0 ) )
    claim( MEADOW, near( site["Farm"], 2600, 300 ) * 0.85 )
    claim( DIRT, near( site["Farm"], 750 ) )
    claim( DIRT, near( site["Lumber Camp"], 1700 ) * ( 0.4 + 0.6 * ramp( patchy, -0.6, 0.2 ) ) )
    claim( GRAVEL, near( site["Military Base"], 2800 ) * ( 0.5 + 0.5 * ramp( patchy, -0.6, 0.2 ) ) )
    claim( DIRT, near( site["Military Base"], 3100 ) * ramp( patchy, 0.7, 1.1 ) * 0.8 )
    claim( DIRT, near( site["West Camp"], 650 ) )
    claim( DIRT, near( site["East Crossing"], 650 ) )
    claim( GRAVEL, near( site["Quarry"], 3000 ) * ( 0.35 + 0.4 * ramp( patchy, -0.4, 0.4 ) ) )
    claim( GRAVEL, near( site["Quarry"], 3200 ) * ramp( pads["Quarry"] - z, 20.0, 80.0 ) )
    claim( GRAVEL, near( RADIO_HILL[0], 650 ) )
    a, b, _ = AIRFIELD
    runway = segment_distance( x, y, world_of( *a ), world_of( *b ) )
    claim( GRAVEL, ramp( 650.0 - runway + 60.0 * fine, -60.0, 60.0 ) )

    # Roads: an earth track, gravelled down the middle in places.
    for field in roads.values():
        d = field.distance
        claim( DIRT, ramp( ROAD_HALF - 60.0 + 60.0 * fine - d, -60.0, 60.0 ) )
        claim( GRAVEL, ramp( 150.0 + 40.0 * fine - d, -50.0, 50.0 ) * ramp( patchy, 0.3, 0.9 ) * 0.75 )

    # The river: a gravel bed with bare earth and stones up its banks.
    d = river.distance
    bank = ramp( RIVER_BED + 300.0 + 150.0 * fine - d, -90.0, 90.0 )
    claim( DIRT, bank * ( 0.5 + 0.5 * ramp( patchy, -0.5, 0.5 ) ) )
    claim( SCREE, bank * ramp( patchy, 0.4, 0.9 ) )
    claim( GRAVEL, ramp( RIVER_BED + 50.0 + 80.0 * fine - d, -60.0, 60.0 ) )

    # Slopes last: dry grass on the steeper banks, scree where it's steep (the quarry's walls, the foothills' steeper
    # sides) with grass holding on in places, rock where it's steeper still.
    steep = slope + 5.0 * fine
    claim( DRY, ramp( steep, 22.0, 30.0 ) * 0.6 )
    claim( SCREE, ramp( steep, 27.0, 33.0 ) * ramp( patchy + 0.3 * fine, -0.7, 0.1 ) )
    claim( ROCK, ramp( steep, 37.0, 44.0 ) )
    return weights


def splat_map( weights ):
    """ The terrain's control map: each sample's strongest material as its base and the next as its overlay, with the
    overlay's share of the two as the blend (CompactTerrainMaterial: bits 0-4 base, 5-9 overlay, 10-17 blend). """
    order = np.argsort( -weights, axis=0 )
    first, second = order[0], order[1]
    w1 = np.take_along_axis( weights, first[None], 0 )[0]
    w2 = np.take_along_axis( weights, second[None], 0 )[0]
    blend = np.rint( 255.0 * w2 / np.maximum( w1 + w2, 1e-6 ) ).astype( np.uint32 )
    second = np.where( blend > 0, second, first )
    return ( first.astype( np.uint32 ) | ( second.astype( np.uint32 ) << 5 ) | ( blend << 10 ) ).astype( "<u4" )


def material_refs():
    """ The terrain's material list: each .tmat by its asset id (from its .meta, which the editor writes on import). """
    refs = []
    for name in MATERIALS:
        path = f"{MATERIAL_DIR}/{name}.tmat"
        meta = ASSETS / f"{path}.meta"
        if not meta.exists():
            raise SystemExit( f"{path} isn't imported yet: run Tools/terrain_textures.py with the editor open" )
        refs.append( { "Id": json.loads( meta.read_text( encoding="utf-8" ) )["guid"], "Path": path } )
    return refs


# ---------------------------------------------------------------------------------------------------------------------
# Output

def deflate_base64( array ):
    packer = zlib.compressobj( 9, zlib.DEFLATED, -15 )   # raw deflate, as .NET's DeflateStream
    data = packer.compress( array.tobytes() ) + packer.flush()
    return base64.b64encode( data ).decode( "ascii" )


def write_terrain( z, splat ):
    if z.min() < BASE_Z or z.max() > BASE_Z + HEIGHT:
        raise SystemExit( f"terrain z {z.min():.0f}..{z.max():.0f} is outside the storage's {BASE_Z}..{BASE_Z + HEIGHT}" )

    heights = np.rint( ( z - BASE_Z ) / HEIGHT * 65535.0 ).astype( "<u2" )
    storage = {
        "Resolution": RES,
        "TerrainSize": SIZE,
        "TerrainHeight": HEIGHT,
        "Maps": { "heightmap": deflate_base64( heights ), "splatmap": deflate_base64( splat ) },
        "Materials": material_refs(),
        "MaterialSettings": {
            "HeightBlendEnabled": True, "HeightBlendSharpness": 0.87,
            "Sampler": { "Filter": "Anisotropic", "AddressModeU": "Wrap", "AddressModeV": "Wrap", "AddressModeW": "Wrap",
                         "MipLodBias": 0, "MaxAnisotropy": 8, "BorderColor": "0,0,0,0" },
        },
        "__references": [],
        "__version": 2,
    }
    MAP_DIR.mkdir( parents=True, exist_ok=True )
    TERRAIN_FILE.write_text( json.dumps( storage, indent=2 ), encoding="utf-8" )
    # The editor saves the terrain (with the scene, too) as a header plus its maps in ridgeback.terrain_d. This file
    # carries its own maps, so an old _d would only be a stale copy.
    TERRAIN_FILE.with_name( TERRAIN_FILE.name + "_d" ).unlink( missing_ok=True )
    print( f"wrote {TERRAIN_FILE.relative_to( ROOT )} ({TERRAIN_FILE.stat().st_size / 1e6:.1f} MB)" )


def material_colours():
    """ Each material's average colour, from its colour map (grey if it hasn't been drawn). """
    from PIL import Image
    colours = []
    for name in MATERIALS:
        png = ASSETS / f"{MATERIAL_DIR}/{name}_color.png"
        colours.append( np.asarray( Image.open( png ).convert( "RGB" ).resize( ( 64, 64 ) ), float ).mean( ( 0, 1 ) )
                        if png.exists() else np.array( ( 128.0, 128.0, 128.0 ) ) )
    return np.array( colours )


def write_preview( z, pads, river, roads, edge, path, splat=None ):
    """ A shaded map, north up. By height, with the river, roads and slopes too steep to walk in red; or, given the
    splat map, in the ground materials' colours as the terrain blends them. """
    from PIL import Image, ImageDraw, ImageFont

    # North up: image up is +X, image right is -Y (east).
    view = z.T[::-1, ::-1]
    gy, gx = np.gradient( view, CELL )
    azimuth, altitude = math.radians( 315 ), math.radians( 40 )
    slope = np.arctan( np.hypot( gx, gy ) )
    aspect = np.arctan2( -gx, gy )
    shade = np.sin( altitude ) * np.cos( slope ) + np.cos( altitude ) * np.sin( slope ) * np.cos( azimuth - aspect )
    if splat is not None:
        palette = material_colours()
        s = splat.T[::-1, ::-1]
        blend = ( ( s >> 10 ) & 255 )[..., None] / 255.0
        colour = palette[s & 31] * ( 1.0 - blend ) + palette[( s >> 5 ) & 31] * blend
        colour *= ( 0.35 + 0.9 * np.clip( shade, 0, 1 ) )[..., None]
    else:
        stops = [ ( -800, ( 70, 90, 70 ) ), ( 0, ( 104, 128, 84 ) ), ( 800, ( 150, 150, 100 ) ), ( 2000, ( 160, 130, 95 ) ),
                  ( 4000, ( 125, 110, 100 ) ), ( 7000, ( 225, 225, 230 ) ) ]
        levels = np.array( [ s[0] for s in stops ], float )
        colour = np.stack( [ np.interp( view, levels, [ s[1][c] for s in stops ] ) for c in range( 3 ) ], -1 )
        colour *= ( 0.45 + 0.75 * np.clip( shade, 0, 1 ) )[..., None]
        band = np.floor( view / 250.0 )
        contour = ( band != np.roll( band, 1, 0 ) ) | ( band != np.roll( band, 1, 1 ) )
        colour[contour] *= 0.75
        steep = np.degrees( slope ) > 40.0                  # too steep to walk (the navmesh's AgentMaxSlope)
        colour[steep] = colour[steep] * 0.55 + np.array( ( 190, 40, 40 ) ) * 0.45

        for field, tint in [ ( river, ( 70, 120, 200 ) ) ] + [ ( f, ( 60, 50, 40 ) ) for f in roads.values() ]:
            mask = field.distance.T[::-1, ::-1] < ( RIVER_BED if field is river else ROAD_HALF * 0.6 )
            colour[mask] = colour[mask] * 0.3 + np.array( tint ) * 0.7

    image = Image.fromarray( np.clip( colour, 0, 255 ).astype( np.uint8 ) ).resize( ( 1024, 1024 ), Image.LANCZOS )
    draw = ImageDraw.Draw( image )
    try:
        font = ImageFont.truetype( "C:/Windows/Fonts/arialbd.ttf", 15 )
    except OSError:
        font = ImageFont.load_default()

    def pixel( east, north ):
        return ( ( east + HALF ) / SIZE * 1024, ( HALF - north ) / SIZE * 1024 )

    labels = [ ( n, c ) for n, c, _ in SITES ] + [ ( "Airfield", ( 1500, 16000 ) ), ( "Radio Hill", RADIO_HILL[0] ) ]
    for name, ( east, north ) in labels:
        px, py = pixel( east, north )
        draw.ellipse( [ px - 4, py - 4, px + 4, py + 4 ], fill=( 255, 200, 60 ), outline=( 0, 0, 0 ) )
        text = f"{name} {pads.get( name, 0 ):.0f}"
        draw.text( ( px + 7, py - 8 ), text, fill=( 0, 0, 0 ), font=font )
        draw.text( ( px + 6, py - 9 ), text, fill=( 255, 255, 255 ), font=font )
    legend = "ground materials" if splat is not None else "250u contours, red over 40 deg"
    draw.text( ( 12, 10 ), f"{TITLE}  N up  {SIZE * 0.0254:.0f} m across  {legend}", fill=( 255, 255, 255 ), font=font )
    image.save( path )
    print( f"wrote preview {path}" )


# ---------------------------------------------------------------------------------------------------------------------
# Scene

NAMESPACE = uuid.UUID( "5b0c9a52-8c1e-4f5e-9d7a-2e1b6f0c4a11" )


def gid( key ):
    return str( uuid.uuid5( NAMESPACE, f"ridgeback/{key}" ) )


def vec( v ):
    return ",".join( f"{c:g}" for c in v )


def yaw_rotation( degrees ):
    half = math.radians( degrees ) / 2
    return f"0,0,{math.sin( half ):.7f},{math.cos( half ):.7f}"


def angles_rotation( pitch, yaw, roll=0.0 ):
    """ Rotation.From( pitch, yaw, roll ) as x,y,z,w. """
    sp, cp = math.sin( math.radians( pitch ) / 2 ), math.cos( math.radians( pitch ) / 2 )
    sy, cy = math.sin( math.radians( yaw ) / 2 ), math.cos( math.radians( yaw ) / 2 )
    sr, cr = math.sin( math.radians( roll ) / 2 ), math.cos( math.radians( roll ) / 2 )
    return ",".join( f"{v:.7f}" for v in ( sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
                                            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy ) )


def component( type_name, key, **props ):
    return { "__type": type_name, "__guid": gid( key ), "__enabled": True, "Flags": 0, **props }


def game_object( name, key, position=( 0, 0, 0 ), rotation="0,0,0,1", components=(), children=(), tags="" ):
    return {
        "__guid": gid( key ), "__version": 2, "Flags": 0, "Name": name, "Position": vec( position ),
        "Rotation": rotation, "Scale": "1,1,1", "Tags": tags, "Enabled": True, "NetworkMode": 2, "NetworkFlags": 0,
        "NetworkOrphaned": 0, "NetworkTransmit": True, "OwnerTransfer": 1, "Components": list( components ),
        "Children": list( children ),
    }


def prefab_instance( path ):
    """ A prefab dropped into the scene, with an instance id for everything in it (as the editor writes). """
    prefab = json.loads( ( ASSETS / path ).read_text( encoding="utf-8" ) )
    ids = set()

    def collect( node ):
        if isinstance( node, dict ):
            if "__guid" in node:
                ids.add( node["__guid"] )
            if isinstance( node.get( "__PrefabIdToInstanceId" ), dict ):
                ids.update( node["__PrefabIdToInstanceId"].values() )
            for key, value in node.items():
                if key != "__PrefabIdToInstanceId":
                    collect( value )
        elif isinstance( node, list ):
            for value in node:
                collect( value )

    collect( prefab["RootObject"] )
    root = prefab["RootObject"]["__guid"]
    resource = json.loads( ( ASSETS / f"{path}.meta" ).read_text( encoding="utf-8" ) )["guid"]
    instance = gid( f"prefab/{path}" )
    mapping = { pid: instance if pid == root else gid( f"prefab/{path}/{pid}" ) for pid in sorted( ids ) }
    return {
        "__guid": instance, "__version": 2, "__Prefab": { "Id": resource, "Path": path },
        "__PrefabInstancePatch": { "AddedObjects": [], "RemovedObjects": [], "PropertyOverrides": [], "MovedObjects": [] },
        "__PrefabIdToInstanceId": mapping,
    }


def wall( name, centre, half_extents ):
    return game_object( name, f"wall/{name}", centre, components=[
        component( "Sandbox.BoxCollider", f"wall/{name}/box", Center="0,0,0", Scale=vec( [ 2 * h for h in half_extents ] ),
                   IsTrigger=False, Static=True ),
    ] )


def write_scene( z, pads ):
    if SCENE_FILE.exists():
        raise SystemExit( f"{SCENE_FILE.relative_to( ROOT )} exists and may have hand edits: delete it to write it again" )

    spawns = []
    for name, ( east, north ), _ in SITES + [ ( "Airfield", ( 1500, 16000 ), 0 ), ( "Radio Hill", RADIO_HILL[0], 0 ) ]:
        position = ( *world_of( east, north ), height_at( z, east, north ) + 8 )
        spawns.append( game_object( name, f"spawn/{name}", position, yaw_rotation( 0 ), components=[
            component( "TeamSpawnPoint", f"spawn/{name}/point", Team="Unassigned" ),
        ] ) )

    sites = [ game_object( name, f"site/{name}", ( *world_of( *centre ), pads[name] ) ) for name, centre, _ in SITES ]
    sites.append( game_object( "Airfield", "site/Airfield", ( *world_of( 1500, 16000 ), pads["Airfield"] ) ) )
    sites.append( game_object( "Radio Hill", "site/Radio Hill", ( *world_of( *RADIO_HILL[0] ), pads["Radio Hill"] ) ) )

    top = BASE_Z + HEIGHT + 2000
    walls = [
        wall( "North Wall", ( HALF + 100, 0, top / 2 ), ( 100, HALF + 200, top / 2 + 1500 ) ),
        wall( "South Wall", ( -HALF - 100, 0, top / 2 ), ( 100, HALF + 200, top / 2 + 1500 ) ),
        wall( "West Wall", ( 0, HALF + 100, top / 2 ), ( HALF + 200, 100, top / 2 + 1500 ) ),
        wall( "East Wall", ( 0, -HALF - 100, top / 2 ), ( HALF + 200, 100, top / 2 + 1500 ) ),
    ]

    objects = [
        game_object( "Scene Information", "info", components=[
            component( "Sandbox.SceneInformation", "info/scene", Title=TITLE, Description="Battle royale: a valley ringed by mountains.",
                       Author=None, Changes="", Group=None, SceneTags="", Version=None ),
            component( "Facepunch.MapInformation", "info/map", Image="", IsVisibleInMenu=True ),
        ] ),
        game_object( "Terrain", "terrain", ( -HALF, -HALF, BASE_Z ), components=[
            { **component( "Sandbox.Terrain", "terrain/terrain", Storage=TERRAIN_RESOURCE, EnableCollision=True,
                           TerrainSize=SIZE, TerrainHeight=HEIGHT, Static=True ), "__version": 1 },
        ] ),
        game_object( "Grass", "grass", components=[
            component( "Sandbox.Clutter.ClutterComponent", "grass/clutter", Clutter=GRASS_RESOURCE, Mode="Infinite", Seed=4242,
                       Bounds={ "Mins": "-512,-512,-512", "Maxs": "512,512,512" } ),
        ] ),
        game_object( "Sun", "sun", ( 0, 0, 12000 ), angles_rotation( 48, 125 ), tags="light_directional,light", components=[
            component( "Sandbox.DirectionalLight", "sun/light", ContactShadows=False, FogMode="Enabled", FogStrength=1,
                       LightColor="1,0.95,0.84,1", ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                       ShadowHardness=0, Shadows=True, SkyColor="0.36,0.43,0.52,1" ),
        ] ),
        game_object( "Sky", "sky", tags="skybox", components=[
            component( "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial="materials/sky/atmosphere_sky.vmat",
                       Tint="1,1,1,1" ),
        ] ),
        game_object( "Fog", "fog", components=[
            component( "Sandbox.GradientFog", "fog/gradient", Color="0.7,0.77,0.85,0.55", StartDistance=6000, EndDistance=70000,
                       FalloffExponent=1.4, Height=5000, VerticalFalloffExponent=1.5 ),
        ] ),
        game_object( "Map Bounds", "bounds", children=walls ),
        game_object( "Battle Royale Area", "area", ( 0, 0, pads["Town"] ), components=[
            component( "Facepunch.BattleRoyaleArea", "area/area", Radius=AREA_RADIUS ),
        ] ),
        game_object( "Spawn Points", "spawns", children=spawns ),
        game_object( "Sites", "sites", children=sites ),
        game_object( "Lightweight Bot Manager", "bots", components=[
            component( "Facepunch.LightweightBotManager", "bots/manager", BotPrefabPath="prefabs/bots/hc1_combat_bot.prefab",
                       MapSpawnChance=0.35, MapSpawnMinPlayerDistance=500, MinSpawnDistanceFromBots=800,
                       MinSpawnDistanceFromPlayers=900 ),
        ] ),
        prefab_instance( "prefabs/game_modes/battle_royale.prefab" ),
        prefab_instance( "scenes/maps/defusemap_01/game_setup.prefab" ),
    ]

    scene = {
        "__guid": gid( "scene" ),
        "GameObjects": objects,
        "SceneProperties": {
            "NetworkInterpolation": True,
            "PhysicsMode": "Physics3D",
            "TimeScale": 1,
            "WantsSystemScene": True,
            "Metadata": {
                "Title": TITLE, "Image": "", "IsVisibleInMenu": "True",
                "GameModes": "prefabs/game_modes/battle_royale.prefab",
            },
            "NavMesh": {
                "Enabled": True, "IncludeStaticBodies": True, "IncludeKeyframedBodies": True, "EditorAutoUpdate": False,
                "AgentHeight": 64, "AgentRadius": 16, "AgentStepSize": 18, "AgentMaxSlope": 40, "ExcludedBodies": "",
                "IncludedBodies": "", "DeferGeneration": False, "CustomBounds": True,
                "Bounds": { "Mins": vec( ( -NAV_BOUNDS, -NAV_BOUNDS, BASE_Z - 500 ) ),
                            "Maxs": vec( ( NAV_BOUNDS, NAV_BOUNDS, BASE_Z + HEIGHT ) ) },
            },
        },
        "ResourceVersion": 3,
        "Title": TITLE,
        "Description": None,
        "__references": [],
        "__version": 3,
    }
    SCENE_FILE.write_text( json.dumps( scene, indent=2 ), encoding="utf-8" )
    print( f"wrote {SCENE_FILE.relative_to( ROOT )}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--scene", action="store_true", help="also write the starting scene (first run only)" )
    parser.add_argument( "--preview", help="write a shaded top-down picture of the terrain here, and of its ground "
                                               "materials beside it (<name>_ground.png)" )
    parser.add_argument( "--no-terrain", action="store_true", help="don't write the terrain file (preview only)" )
    args = parser.parse_args()

    z, pads, river, roads, edge, notes = build()
    slope = notes.pop( "slope" )
    for key, value in notes.items():
        print( f"{key}: {value}" )
    for name, height in pads.items():
        print( f"  {name}: pad z {height:.0f}" )

    weights = paint( z, slope, pads, river, roads )
    splat = splat_map( weights )
    valley = np.hypot( *grid_xy() ) < AREA_RADIUS
    shares = np.bincount( ( splat & 31 )[valley], minlength=len( MATERIALS ) ) / valley.sum() * 100
    print( "valley ground %: " + ", ".join( f"{name} {share:.1f}" for name, share in zip( MATERIALS, shares ) ) )

    if not args.no_terrain:
        write_terrain( z, splat )
    if args.preview:
        write_preview( z, pads, river, roads, edge, args.preview )
        ground = Path( args.preview )
        write_preview( z, pads, river, roads, edge, ground.with_name( f"{ground.stem}_ground{ground.suffix}" ), splat )
    if args.scene:
        write_scene( z, pads )


if __name__ == "__main__":
    main()
