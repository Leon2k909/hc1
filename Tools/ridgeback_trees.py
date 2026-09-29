"""
Ridgeback's trees, bushes and hedgerows: where each one goes, planned from the map's own layout (Tools/ridgeback_map.py)
and written into ridgeback_trees.clutter, which the scene's "Trees" clutter places.

    python Tools/ridgeback_trees.py [--preview <png>]

- The models are Facepunch's cloud packages (SPECIES): oaks with a few dry (autumn) ones, beech and pine bushes, and
  beech hedges.
- Woods round Lumber Camp and up the foothills behind it, a ragged ring from the valley's rim up the lower mountains,
  copses on the hills and here and there in the valley, and strips along the river. The mountains above them are bare:
  Facepunch's low-poly vista oaks were tried there and read as dark balls on the rock.
- Lone oaks in the open meadows, and hedgerows round the Farm's fields and along its two roads, with an oak now and then.
- Bushes under the woods and thicker along their edges, on the river's banks, dotted over the meadows, and pine bushes on
  the foothills.
- Nothing on the sites' pads, Radio Hill's top, the roads, the runway and its approaches or the river bed, nor on ground
  that isn't grass (ridgeback_map.paint), too steep or too high.
- Each placement is an entry, a spot, a turn and a size; the scene's clutter (Code/Maps/PlannedScatterer.cs) stands it
  on the ground. The trees and hedges have their models' collision; the bushes have none.

After running this, open ridgeback.scene, press Generate on the "Trees" object's Clutter Renderer and save the scene:
the placed instances are stored in it (ridgeback.scene_d).
"""
import argparse
import base64
import json
import math
import struct

import numpy as np
from scipy import ndimage

import ridgeback_map as rm

CLUTTER_FILE = rm.MAP_DIR / "ridgeback_trees.clutter"
SEED = 2718
HECTARE = 1e4 / 0.0254 ** 2        # square units in a hectare
LIMIT = rm.HALF - 400.0            # keep clear of the map's walls


class Species:
    """ spacing: how far apart two of them stand (their crowns may overlap), trunk: how close a bush may come to a
    tree. Both in units at scale 1. kind: tree (upright, with collision), bush (lies with the ground) or hedge (a bush
    with collision, laid end to end). """

    def __init__( self, key, model, package, spacing, trunk=0.0, scale=( 0.75, 1.3 ), kind="bush", shadows=True ):
        self.key, self.model, self.package = key, model, package
        self.spacing, self.trunk, self.scale, self.kind, self.shadows = spacing, trunk, scale, kind, shadows


OAK = "models/sbox_props/trees/oak"
BEECH = "models/sbox_props/shrubs/beech"
PINE = "models/sbox_props/shrubs/pine"

SPECIES = [
    Species( "oak_big_a", f"{OAK}/tree_oak_big_a.vmdl", "facepunch.tree_oak_big_a#288919", 330, 70, ( 0.8, 1.05 ), "tree" ),
    Species( "oak_big_b", f"{OAK}/tree_oak_big_b.vmdl", "facepunch.tree_oak_big_b#288918", 230, 60, ( 0.85, 1.1 ), "tree" ),
    Species( "oak_medium", f"{OAK}/tree_oak_medium_a.vmdl", "facepunch.tree_oak_medium_a#288916", 170, 35, ( 0.8, 1.2 ), "tree" ),
    Species( "oak_small", f"{OAK}/tree_oak_small_a.vmdl", "facepunch.tree_oak_small_a#288917", 95, 18, ( 0.8, 1.25 ), "tree" ),
    Species( "dry_big", f"{OAK}/tree_oak_dry_big_a.vmdl", "facepunch.treeoakdrybiga#288924", 330, 70, ( 0.8, 1.05 ), "tree" ),
    Species( "dry_medium", f"{OAK}/tree_oak_dry_medium_a.vmdl", "facepunch.treeoakdrymediuma#289352", 170, 35, ( 0.8, 1.2 ), "tree" ),
    Species( "dry_small", f"{OAK}/tree_oak_dry_small_a.vmdl", "facepunch.treeoakdrysmalla#288926", 95, 18, ( 0.8, 1.25 ), "tree" ),
    Species( "bush_large", f"{BEECH}/beech_bush_large.vmdl", "facepunch.beech_bush_large#145427", 110 ),
    Species( "bush_medium", f"{BEECH}/beech_bush_medium.vmdl", "facepunch.beech_bush_medium#145428", 85 ),
    Species( "bush_small", f"{BEECH}/beech_bush_small.vmdl", "facepunch.beech_bush_small#145429", 62 ),
    Species( "bush_round_a", f"{BEECH}/beech_bush_regular_medium_a.vmdl", "facepunch.beech_bush_regular_medium_a#145432", 60 ),
    Species( "bush_round_b", f"{BEECH}/beech_bush_regular_medium_b.vmdl", "facepunch.beech_bush_regular_medium_b#145424", 52 ),
    Species( "bush_round_small", f"{BEECH}/beech_bush_regular_small.vmdl", "facepunch.beech_bush_regular_small#145430", 44 ),
    Species( "shrub_tall", f"{BEECH}/beech_shrub_tall_medium.vmdl", "facepunch.beech_shrub_tall_medium#145483", 78 ),
    Species( "shrub_wide", f"{BEECH}/beech_shrub_wide_large.vmdl", "facepunch.beech_shrub_wide_large#145481", 140 ),
    Species( "hedge", f"{BEECH}/beech_hedge_96x128.vmdl", "facepunch.beech_hedge_96x128#145491", 60, scale=( 1.0, 1.0 ),
             kind="hedge" ),
    Species( "pine_low_a", f"{PINE}/pine_bush_low_a.vmdl", "facepunch.pine_bush_low_a#145425", 58 ),
    Species( "pine_low_b", f"{PINE}/pine_bush_low_b.vmdl", "facepunch.pine_bush_low_b#145433", 52 ),
    Species( "pine_round", f"{PINE}/pine_bush_regular_c.vmdl", "facepunch.pine_bush_regular_c#145436", 42 ),
    Species( "pine_tall", f"{PINE}/pine_shrub_tall_b.vmdl", "facepunch.pine_shrub_tall_b#145478", 42 ),
    Species( "pine_wide", f"{PINE}/pine_shrub_wide.vmdl", "facepunch.pine_shrub_wide#145484", 50 ),
]
INDEX = { s.key: i for i, s in enumerate( SPECIES ) }
DRY = { "oak_big_a": "dry_big", "oak_big_b": "dry_big", "oak_medium": "dry_medium", "oak_small": "dry_small" }

# Stems per hectare where the woods are thickest, and their mix. Lone trees are mostly the big ones.
WOOD_DENSITY = 90.0
WOOD_MIX = { "oak_big_a": 0.045, "oak_big_b": 0.045, "oak_medium": 0.41, "oak_small": 0.5 }
LONE_DENSITY = 1.0
LONE_MIX = { "oak_big_a": 0.25, "oak_big_b": 0.25, "oak_medium": 0.38, "oak_small": 0.12 }

HEDGE_STEP = 130.0                 # the hedge model is 141 long (its Y axis), so segments overlap a little
HEDGE_TREE_GAP = ( 1400.0, 2600.0 )
HEDGE_TREE_MIX = { "oak_medium": 0.55, "oak_small": 0.3, "oak_big_b": 0.15 }
FARM_FIELDS = dict( angle=20.0, size=( 2600.0, 2200.0 ), reach=9500.0, keep=0.7 )
ROADSIDE_HEDGES = [ "Town - Farm", "Farm - Quarry" ]
ROADSIDE_OFFSET = rm.ROAD_HALF + 170.0

BUSHES = {
    # name: (stems per hectare at full strength, mix)
    "fringe": ( 60.0, { "bush_large": 0.3, "shrub_tall": 0.25, "shrub_wide": 0.15, "bush_medium": 0.2, "bush_round_a": 0.1 } ),
    "riverbank": ( 30.0, { "bush_large": 0.25, "bush_medium": 0.3, "shrub_tall": 0.2, "bush_round_a": 0.25 } ),
    "understory": ( 22.0, { "bush_medium": 0.2, "bush_small": 0.25, "bush_round_a": 0.15, "bush_round_b": 0.15,
                            "bush_round_small": 0.15, "shrub_tall": 0.1 } ),
    "meadow": ( 4.0, { "bush_round_a": 0.25, "bush_round_b": 0.25, "bush_round_small": 0.2, "bush_small": 0.15,
                       "bush_large": 0.1, "shrub_wide": 0.05 } ),
    "pines": ( 14.0, { "pine_low_a": 0.25, "pine_low_b": 0.2, "pine_round": 0.2, "pine_tall": 0.15, "pine_wide": 0.2 } ),
}


def ramp( v, a, b ):
    return rm.ramp( v, a, b )


def sample( field, x, y ):
    """ A grid field at world points (nearest sample). """
    i, j = rm.to_index( np.asarray( x, float ), np.asarray( y, float ) )
    i = np.clip( np.rint( i ).astype( int ), 0, rm.RES - 1 )
    j = np.clip( np.rint( j ).astype( int ), 0, rm.RES - 1 )
    return field[j, i]


# ---------------------------------------------------------------------------------------------------------------------
# The map's fields, and where things may grow

class Fields:
    def __init__( self ):
        z, pads, river, roads, edge, notes = rm.build()
        self.z, self.slope, self.pads, self.roads, self.edge = z, notes["slope"], pads, roads, edge
        self.river_field = river
        self.weights = rm.paint( z, self.slope, pads, river, roads )
        weights = self.weights
        self.grass = weights[rm.MEADOW] + weights[rm.DRY]
        self.dryness = weights[rm.DRY] / np.maximum( self.grass, 1e-6 )
        x, y = rm.grid_xy()
        self.x, self.y = x, y
        self.out = np.hypot( x, y ) - edge                 # past the valley's rim (the foothills start at 0)
        self.river = river.distance
        self.road = np.min( [ field.distance for field in roads.values() ], axis=0 )

        # How far outside the nearest pad (negative inside): the sites, Radio Hill's top, and the runway with room to
        # fly in at both ends.
        gap = np.full( z.shape, np.inf )
        for name, centre, radius in rm.SITES:
            cx, cy = rm.world_of( *centre )
            gap = np.minimum( gap, np.hypot( x - cx, y - cy ) - radius )
        hx, hy = rm.world_of( *rm.RADIO_HILL[0] )
        gap = np.minimum( gap, np.hypot( x - hx, y - hy ) - rm.RADIO_HILL[3] )
        self.pad = gap
        a, b, half = rm.AIRFIELD
        a, b = np.array( rm.world_of( *a ) ), np.array( rm.world_of( *b ) )
        along = ( b - a ) / np.linalg.norm( b - a )
        self.runway = rm.segment_distance( x, y, a - along * 3000.0, b + along * 3000.0 ) - half


def woods_and_rules( f, rng ):
    """ How wooded each sample is (0-1: the woods have narrow edges, so they read as woods and not as trees spread
    thin), how thick the scattered trees are, and where trees and bushes may grow at all. """
    x, y = f.x, f.y
    fine = rm.fractal( rng, 1.8, 60, 300 )
    # Woods: hundreds of metres. broad[4] is unused (it placed the vista oaks), but drawing it keeps the layout put.
    broad = [ rm.fractal( rng, 2.6, 5, 40 ) + 0.08 * fine for _ in range( 6 ) ]
    copses = rm.fractal( rng, 2.4, 12, 60 ) + 0.08 * fine                          # copses: tens of metres

    def near( centre, radius, soft ):
        cx, cy = rm.world_of( *centre )
        return ramp( radius - np.hypot( x - cx, y - cy ), -soft, soft )

    lumber_camp = rm.SITES[2][1]
    lumber = near( ( lumber_camp[0] + 2500, lumber_camp[1] + 2500 ), 8000.0 + 1800.0 * broad[0], 600.0 )
    rim = ramp( f.out, -3500.0, -2500.0 ) * ramp( broad[1], -0.1, 0.1 )
    hills = np.max( [ near( centre, radius * 0.75, 500.0 ) for centre, _, radius in rm.HILLS ], axis=0 ) \
        * ramp( broad[2], -0.2, 0.0 )
    banks = ramp( f.river, rm.RIVER_BED + 250.0, rm.RIVER_BED + 450.0 ) * ( 1.0 - ramp( f.river, 1300.0, 1800.0 ) ) \
        * ramp( broad[3], 0.0, 0.2 )
    groves = ramp( copses, 1.3, 1.45 )
    woods = np.max( [ lumber, rim, hills, banks, groves ], axis=0 )
    # Just outside the woods, for the thicket along their edges.
    edge = ndimage.gaussian_filter( woods, 400.0 / rm.CELL ) * ( 1.0 - ramp( woods, 0.3, 0.6 ) )
    # Out in the meadows, lone trees, thicker round the copses.
    scattered = ( 1.0 + 5.0 * ramp( copses, 0.7, 1.4 ) ) * ( 1.0 - ramp( woods, 0.05, 0.3 ) )

    ground = ramp( f.grass, 0.45, 0.75 )
    clear = ramp( f.road, rm.ROAD_HALF + 250.0, rm.ROAD_HALF + 450.0 ) * ramp( f.pad, 300.0, 700.0 ) \
        * ramp( f.runway, 1000.0, 1600.0 ) * ramp( f.river, rm.RIVER_BED + 150.0, rm.RIVER_BED + 350.0 )
    trees = ground * ( 1.0 - ramp( f.slope, 30.0, 36.0 ) ) * ( 1.0 - ramp( f.z + 300.0 * fine, 2300.0, 2800.0 ) ) * clear
    valley = 1.0 - ramp( f.out, -1500.0, -500.0 )
    soil = 1.0 - ramp( f.weights[rm.ROCK], 0.3, 0.6 )

    clear_bush = ramp( f.road, rm.ROAD_HALF + 80.0, rm.ROAD_HALF + 200.0 ) * ramp( f.pad, 100.0, 300.0 ) \
        * ramp( f.runway, 300.0, 600.0 ) * ramp( f.river, rm.RIVER_BED + 40.0, rm.RIVER_BED + 120.0 )
    bush = ramp( f.grass, 0.35, 0.6 ) * ( 1.0 - ramp( f.slope, 36.0, 42.0 ) ) * clear_bush
    bushes = {
        "fringe": ramp( edge, 0.08, 0.25 ) * bush * trees.clip( 0.3, 1.0 ),
        "riverbank": ramp( f.river, rm.RIVER_BED + 60.0, rm.RIVER_BED + 200.0 ) * ( 1.0 - ramp( f.river, 700.0, 1100.0 ) )
        * ramp( broad[5], -0.3, 0.3 ) * bush,
        "understory": woods * bush * trees.clip( 0.3, 1.0 ),
        "meadow": ( 1.0 - ramp( woods, 0.1, 0.3 ) ) * valley * ramp( copses, 0.0, 1.0 ) * bush,
        "pines": ramp( f.out, -1500.0, 0.0 ) * ( 1.0 - ramp( f.z + 300.0 * fine, 3500.0, 4200.0 ) )
        * ramp( broad[5] + 0.5 * copses, -0.4, 0.2 ) * soil * ( 1.0 - ramp( f.slope, 38.0, 44.0 ) ) * clear_bush,
    }
    return woods, scattered, trees, valley, bushes


# ---------------------------------------------------------------------------------------------------------------------
# Placing, with room kept round each one

class Placed:
    CELL = 400.0

    def __init__( self ):
        self.items = []            # (species index, x, y, yaw, scale)
        self.info = []             # (x, y, spacing, trunk, kind)
        self.grid = {}

    def fits( self, species, x, y, scale, ignore_hedges=False ):
        if abs( x ) > LIMIT or abs( y ) > LIMIT:
            return False
        r, t = species.spacing * scale, species.trunk * scale
        upright = species.kind == "tree"
        cx, cy = int( math.floor( x / self.CELL ) ), int( math.floor( y / self.CELL ) )
        for gx in range( cx - 2, cx + 3 ):
            for gy in range( cy - 2, cy + 3 ):
                for k in self.grid.get( ( gx, gy ), () ):
                    ox, oy, orad, otrunk, okind = self.info[k]
                    d = math.hypot( x - ox, y - oy )
                    if okind == "hedge":
                        if ignore_hedges:
                            continue
                        need = ( t + 70.0 ) if upright else ( r + 40.0 )
                    elif okind == "tree":
                        need = ( r + orad ) if upright else ( otrunk + r * 0.6 )
                    else:
                        need = ( t + orad * 0.5 ) if upright else ( r + orad )
                    if d < need:
                        return False
        return True

    def add( self, key, x, y, yaw, scale, check=True, ignore_hedges=False ):
        species = SPECIES[INDEX[key]]
        if check and not self.fits( species, x, y, scale, ignore_hedges ):
            return False
        cell = ( int( math.floor( x / self.CELL ) ), int( math.floor( y / self.CELL ) ) )
        self.grid.setdefault( cell, [] ).append( len( self.info ) )
        self.info.append( ( x, y, species.spacing * scale, species.trunk * scale, species.kind ) )
        self.items.append( ( INDEX[key], x, y, yaw % 360.0, scale ) )
        return True


def pick( rng, mix ):
    keys = list( mix )
    weights = np.array( [ mix[k] for k in keys ], float )
    return keys[rng.choice( len( keys ), p=weights / weights.sum() )]


def candidates( rng, density, spacing=150.0 ):
    """ Points thinned from a jittered grid so there are about density (per hectare, a grid field) of them. """
    n = int( rm.SIZE // spacing )
    gx, gy = np.meshgrid( np.arange( n ), np.arange( n ) )
    x = ( -rm.HALF + ( gx + rng.random( gx.shape ) ) * spacing ).ravel()
    y = ( -rm.HALF + ( gy + rng.random( gy.shape ) ) * spacing ).ravel()
    chance = sample( density, x, y ) * spacing * spacing / HECTARE
    keep = rng.random( x.size ) < chance
    order = rng.permutation( int( keep.sum() ) )
    return x[keep][order], y[keep][order]


def plant( placed, rng, density, mix, dry_chance=None ):
    """ Each kind in mix at its share of density, largest first so the small ones fill in round them. """
    count = 0
    for key in sorted( mix, key=lambda k: -SPECIES[INDEX[k]].spacing ):
        xs, ys = candidates( rng, density * mix[key] )
        for x, y in zip( xs, ys ):
            chosen = key
            if dry_chance is not None and key in DRY and rng.random() < sample( dry_chance, x, y ):
                chosen = DRY[key]
            low, high = SPECIES[INDEX[chosen]].scale
            count += placed.add( chosen, x, y, rng.uniform( 0.0, 360.0 ), rng.uniform( low, high ) )
    return count


# ---------------------------------------------------------------------------------------------------------------------
# Hedgerows

def hedge_ok( f, woods, x, y ):
    return ( sample( f.road, x, y ) > rm.ROAD_HALF + 150.0 and sample( f.pad, x, y ) > 150.0
             and sample( f.river, x, y ) > rm.RIVER_BED + 250.0 and sample( f.slope, x, y ) < 22.0
             and sample( f.grass, x, y ) > 0.4 and sample( woods, x, y ) < 0.5 and sample( f.runway, x, y ) > 300.0 )


def lay_hedge( placed, rng, f, woods, points, own_road=None ):
    """ Hedge segments end to end along a polyline of world points, with a gate now and then and an oak every so often.
    own_road: the road a roadside hedge follows, which its distance from the road doesn't count against. """
    points = np.asarray( points, float )
    steps = np.hypot( *np.diff( points, axis=0 ).T )
    length = float( steps.sum() )
    if length < HEDGE_STEP * 3:
        return 0
    along = np.concatenate( [ [ 0.0 ], np.cumsum( steps ) ] )
    gates = set()
    for _ in range( rng.integers( 0, 2 ) + int( length // 6000 ) ):
        start = int( rng.integers( 0, max( 1, int( length // HEDGE_STEP ) - 2 ) ) )
        gates.update( ( start, start + 1 ) )
    next_tree = rng.uniform( *HEDGE_TREE_GAP ) * 0.5
    count = 0
    for k, s in enumerate( np.arange( HEDGE_STEP * 0.5, length, HEDGE_STEP ) ):
        x = float( np.interp( s, along, points[:, 0] ) )
        y = float( np.interp( s, along, points[:, 1] ) )
        dx = float( np.interp( s + 20.0, along, points[:, 0] ) - np.interp( s - 20.0, along, points[:, 0] ) )
        dy = float( np.interp( s + 20.0, along, points[:, 1] ) - np.interp( s - 20.0, along, points[:, 1] ) )
        ok = hedge_ok( f, woods, x, y ) if own_road is None else roadside_ok( f, woods, x, y, own_road )
        if not ok or k in gates:
            continue
        if s >= next_tree:
            key = pick( rng, HEDGE_TREE_MIX )
            low, high = SPECIES[INDEX[key]].scale
            if placed.add( key, x, y, rng.uniform( 0.0, 360.0 ), rng.uniform( low, high ), ignore_hedges=True ):
                count += 1
            next_tree = s + rng.uniform( *HEDGE_TREE_GAP )
        placed.add( "hedge", x, y, math.degrees( math.atan2( dy, dx ) ) - 90.0, 1.0, check=False )
        count += 1
    return count


def roadside_ok( f, woods, x, y, own_road ):
    others = min( sample( fld.distance, x, y ) for name, fld in f.roads.items() if name != own_road )
    return ( others > rm.ROAD_HALF + 150.0 and sample( f.pad, x, y ) > 150.0
             and sample( f.river, x, y ) > rm.RIVER_BED + 250.0 and sample( f.slope, x, y ) < 22.0
             and sample( woods, x, y ) < 0.5 and sample( f.runway, x, y ) > 300.0 )


def hedgerows( placed, rng, f, woods ):
    """ A patchwork of fields round the Farm, each side hedged or not, and hedges along the Farm's roads. """
    count = 0
    farm = np.array( rm.world_of( *rm.SITES[1][1] ) )
    angle = math.radians( FARM_FIELDS["angle"] )
    u = np.array( ( math.cos( angle ), math.sin( angle ) ) )
    v = np.array( ( -u[1], u[0] ) )
    width, depth = FARM_FIELDS["size"]
    cells = int( FARM_FIELDS["reach"] // min( width, depth ) ) + 1

    def corner( i, j ):
        return farm + u * ( i - 0.5 ) * width + v * ( j - 0.5 ) * depth

    def field_ok( i, j ):
        centre = farm + u * i * width + v * j * depth
        return ( np.hypot( *( centre - farm ) ) < FARM_FIELDS["reach"] and sample( f.out, *centre ) < -1500.0
                 and sample( f.pad, *centre ) > 600.0 and sample( f.river, *centre ) > 900.0 )

    for i in range( -cells, cells + 1 ):
        for j in range( -cells, cells + 1 ):
            here = field_ok( i, j )
            # The side between this field and the next one along u, then along v: hedged if either is a field.
            for di, dj, a, b in ( ( 1, 0, corner( i + 1, j ), corner( i + 1, j + 1 ) ),
                                  ( 0, 1, corner( i, j + 1 ), corner( i + 1, j + 1 ) ) ):
                there = field_ok( i + di, j + dj )
                if ( here or there ) and ( rng.random() < FARM_FIELDS["keep"] or here != there ):
                    count += lay_hedge( placed, rng, f, woods, [ a, b ] )

    for name in ROADSIDE_HEDGES:
        points = f.roads[name].points
        tangent = np.gradient( points, axis=0 )
        tangent /= np.maximum( np.hypot( *tangent.T )[:, None], 1e-6 )
        normal = np.stack( [ -tangent[:, 1], tangent[:, 0] ], axis=1 )
        for side in ( -1.0, 1.0 ):
            line = points + normal * side * ROADSIDE_OFFSET
            # Only stretches of it: split where a noise-like run of coin flips says so.
            run = int( rng.integers( 150, 400 ) )
            start = 0
            while start < len( line ):
                end = min( len( line ), start + run )
                if rng.random() < 0.6:
                    count += lay_hedge( placed, rng, f, woods, line[start:end], own_road=name )
                start = end + int( rng.integers( 30, 120 ) )
                run = int( rng.integers( 150, 400 ) )
    return count


# ---------------------------------------------------------------------------------------------------------------------

def plan( f ):
    rng = np.random.default_rng( SEED )
    woods, scattered, trees, valley, bushes = woods_and_rules( f, rng )
    dry_chance = 0.03 + 0.15 * f.dryness
    placed = Placed()
    counts = {}
    counts["hedgerows"] = hedgerows( placed, rng, f, woods )
    counts["lone trees"] = plant( placed, rng, LONE_DENSITY * scattered * trees * valley, LONE_MIX, dry_chance )
    counts["woods"] = plant( placed, rng, WOOD_DENSITY * woods * trees, WOOD_MIX, dry_chance )
    for name, ( density, mix ) in BUSHES.items():
        counts[f"bushes: {name}"] = plant( placed, rng, density * bushes[name], mix )
    return placed.items, counts, woods


def encode( items ):
    data = bytearray()
    for index, x, y, yaw, scale in items:
        data += struct.pack( "<BhhBB", index, int( round( x ) ), int( round( y ) ), int( round( yaw / 360.0 * 256.0 ) ) % 256,
                             int( round( np.clip( ( scale - 0.25 ) / 2.25, 0.0, 1.0 ) * 255.0 ) ) )
    return base64.b64encode( bytes( data ) ).decode( "ascii" )


def write_clutter( items ):
    clutter = {
        "Entries": [ {
            "Prefab": None, "Model": s.model, "Weight": 1, "LocalScale": 1, "CastShadows": s.shadows,
            "EnablePhysics": s.kind in ( "tree", "hedge" ),
        } for s in SPECIES ],
        # Volume mode generates the whole map once, a job per tile: the biggest tiles make the fewest jobs.
        "TileSizeEnum": "Size4096",
        "TileRadius": 1,
        "Scatterer": {
            "Type": "PlannedScatterer",
            "Placements": encode( items ),
            "AlignedEntries": [ i for i, s in enumerate( SPECIES ) if s.kind in ( "bush", "hedge" ) ],
            "Sink": 4,
        },
        "__references": sorted( { s.package for s in SPECIES } ),
        "__version": 0,
    }
    CLUTTER_FILE.write_text( json.dumps( clutter, indent=2 ), encoding="utf-8" )
    print( f"wrote {CLUTTER_FILE.relative_to( rm.ROOT )} ({len( items )} placements)" )


def write_preview( f, items, woods, path ):
    """ The ground map with every placement on it: trees dark green (dry ones orange), bushes light green, pines teal
    and hedges brown. """
    from PIL import Image, ImageDraw
    rm.write_preview( f.z, f.pads, f.river_field, f.roads, f.edge, path, rm.splat_map( f.weights ) )
    image = Image.open( path ).convert( "RGB" )
    scale = 2
    image = image.resize( ( image.width * scale, image.height * scale ), Image.LANCZOS )
    draw = ImageDraw.Draw( image )
    colours = { "tree": ( 20, 70, 20 ), "dry": ( 210, 120, 30 ), "bush": ( 120, 190, 70 ), "pine": ( 40, 140, 120 ),
                "hedge": ( 110, 70, 30 ) }
    for index, x, y, yaw, size in items:
        s = SPECIES[index]
        colour = colours["dry"] if s.key.startswith( "dry" ) else colours["pine"] if s.key.startswith( "pine" ) \
            else colours[s.kind]
        east, north = -y, x
        px = ( east + rm.HALF ) / rm.SIZE * image.width
        py = ( rm.HALF - north ) / rm.SIZE * image.height
        crown = s.spacing / 0.6 if s.kind == "tree" else s.spacing * 1.1
        radius = max( 1.0, crown * size / rm.SIZE * image.width )
        draw.ellipse( [ px - radius, py - radius, px + radius, py + radius ], fill=colour )
    image.save( path )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", help="write the ground map with every placement drawn on it here" )
    args = parser.parse_args()

    f = Fields()
    items, counts, woods = plan( f )
    for name, count in counts.items():
        print( f"  {name}: {count}" )
    kinds = {}
    for index, *_ in items:
        kinds[SPECIES[index].key] = kinds.get( SPECIES[index].key, 0 ) + 1
    print( "  by model: " + ", ".join( f"{k} {n}" for k, n in sorted( kinds.items() ) ) )
    write_clutter( items )
    if args.preview:
        write_preview( f, items, woods, args.preview )


if __name__ == "__main__":
    main()
