"""
Lowtide: a multiplayer map. The warehouse quarter of a made-up North German port at low tide, after Hamburg's
Speicherstadt: red-brick warehouses six storeys high with stepped gables, copper-roofed winch oriels and loading doors
stacked up their fronts, standing straight up out of a tidal canal (a Fleet). The tide is out, so the Fleet is a bed of
mud with a channel of water down its middle, and you can drop into it.

    python Tools/lowtide_map.py [--preview <dir>] [--no-scene] [--art]

Built by script like Belltower, Reef Hall and Railhead, out of map_kit's boxes and polygons. It paints with
building_textures' and railhead_materials' paints and its own lt_ paints, including a generated brick material and
tinted project textures (wet mud, painted doors and frames, jute): see LT_MATERIALS. Furniture
and vehicles come from railhead_props, through railhead_map's `use`. Writes:
- the models, to Assets/models/maps/lowtide/: the Fleet (its bed, the bridges and the barge), the east half and its
  mirror the west half, the glass, the water, and the backdrop (the Fleet running on north, the harbour and its far
  shore), the last two drawn only;
- the scene, Assets/scenes/maps/Lowtide/lowtide.scene, rewritten whole on every run (change the layout here, not in
  the editor);
- the materials, Assets/materials/lowtide/*.vmat;
- the radar picture, ui/minimaps/minimap_lowtide.png, and with --art a stand-in menu picture, ui/maps/lowtide.png.

Plan coordinates: e east, n north, z up, in inches (map_kit's). The map is mirrored across e = 0, the Fleet's middle:
Red Team spawns on the west square, Blue Team on the east one. The play area is e -2200..2200, n -1650..1450. The
streets and quays are at z 0, the Fleet's mud 128 below them at its walls (a drop of 3.25 m, under the 156 that hurts),
and its channel 146 below.

The three lanes, each crossing the Fleet:
- North: the street along the north row of warehouses, over the Fleet on an iron girder bridge.
- Middle: through the two warehouses (Speicher) either side of the Fleet. Each is open on its ground floor and on a
  mezzanine over its north half, and has loading bays onto the Fleet, with landings and stairs down into it. Between them
  the Fleet's bed, with a barge lying on the mud. Bomb site A is the east warehouse's ground floor under the mezzanine.
- South: the yards south of the warehouses and the harbour quay, over the Fleet's mouth on a truss footbridge. Bomb site B
  is on the east quay among the cargo, under a quay crane.
Between them, a cross street each side from the north street to the quay, past the spawn square.

Every run checks every spawn, objective and cash spot as Railhead's script does (railhead_map's check_spots,
check_reach and check_retakes_sight, with this map's bounds), and prints what's wrong.

The navmesh stops at NAV_TOP (300), over the mezzanines (176) and under the warehouses' ceilings (352). Above that the
warehouses are closed, and the blocks round the play are one collision box each.
"""
import argparse
import json
import math
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

import building_textures as BT
import map_kit as K
from map_kit import Model, Wall, arc
import railhead_map as R
import railhead_preview as PV
import lowtide_skip as SKIP
import lowtide_forklift as FORKLIFT
import lowtide_stairs as STAIRS
import lowtide_pallets as PALLETS
import lowtide_shipyard as SHIPYARD
import lowtide_brick as BRICK
import lowtide_sacks as SACKS
import lowtide_water as WATER
import lowtide_bridge as DECK
import lowtide_bridge_rails as RAILS
import lowtide_doors as DOORS
import lowtide_crane as CRANE
import lowtide_plaster as PLASTER
import lowtide_lamps as LAMPS
import lowtide_lanterns as LANTERNS
import lowtide_paving as PAVING
import lowtide_container as CONTAINER

TITLE = "Lowtide"
OUT_DIR = K.ASSETS / "models/maps/lowtide"
RESOURCE_DIR = "models/maps/lowtide"
SCENE_FILE = K.ASSETS / "scenes/maps/Lowtide/lowtide.scene"
MAT_DIR = K.ASSETS / "materials/lowtide"
MINIMAP_PATH = "ui/minimaps/minimap_lowtide.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_lowtide.png"     # the folder is ui/Minimaps on disk
MAP_ART_PATH = "ui/maps/lowtide.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "c3f0a2d4-6b1e-4f7a-9d25-8e41b7c06a93" )

METAL, STONE, WOOD, GLASS, DIRT = "metal", "default", "wood", "glass", "dirt"

# Keep the warm afternoon sun shining up the Fleet from the harbour. Lowtide has
# its own coastal sky: shaded cloud layers drift while the sun remains fixed.
SUN_PITCH, SUN_YAW = R.SUN_PITCH, R.SUN_YAW
SKY_MATERIAL = "materials/lowtide/sky/lowtide_sky.vmat"
SKY_EXPOSURE = R.SKY_EXPOSURE
FOG_COLOUR = R.FOG_COLOUR
CATCH_FLOOR_Z = -3000

PLAY = ( -2200.0, 2200.0, -1650.0, 1450.0 )         # e0, e1, n0, n1
NAV_TOP = 300.0

# Levels
BED_Z = -128.0                 # the Fleet's mud at the foot of its walls
CHANNEL_Z = -146.0             # the bottom of the low-water channel down its middle
WATER_Z = -137.0               # the channel's water: 9 deep at most
HARBOUR_Z = -150.0             # the harbour's water at low tide, beyond the quay
FLEET = 240.0                  # the Fleet's walls' faces, at e +-FLEET
QUAY_N = -1600.0               # the harbour quay's edge
STREET_N = ( 1150.0, 1450.0 )  # the north street, between the warehouse and the north row
FLOOR1 = 176.0                 # the warehouses' mezzanine floor
CEILING = 352.0                # their ceiling over both floors
EAVES = 952.0                  # their eaves: four storeys of 150 over the ceiling

# The Fleet's bed across it: ( distance from the middle, height ): the channel, its banks, a level flat of mud along
# each wall, and the mud banked against the wall's foot. The collision follows it; the drawn mud has a little
# unevenness over it, so the water's edge wanders.
BED_PROFILE = [ ( 0.0, CHANNEL_Z ), ( 70.0, CHANNEL_Z ), ( 120.0, -137.0 ), ( 160.0, -130.0 ), ( 220.0, -130.0 ),
                ( 240.0, BED_Z ) ]


def bed_z( e ):
    xs, zs = zip( *BED_PROFILE )
    return np.interp( np.abs( e ), xs, zs )


# ---------------------------------------------------------------------------------------------------------------------
# Paints: existing project materials, with a generated albedo and matching surface maps for Lowtide's bricks.

# name: ( the material it copies, tint, roughness (None: the copy's own) ) or, for a flat paint, ( colour, metalness,
# roughness ).
LT_MATERIALS = {
    "lt_brick_soot": ( "buildings/brick", ( 0.66, 0.58, 0.54 ), None ),       # the west side's: weathered darker
    "lt_brick_glazed": ( "buildings/brick", ( 0.34, 0.28, 0.27 ), 0.32 ),    # the bands, sills and arches' dark glazed brick
    "lt_brick_slime": ( "buildings/brick", ( 0.36, 0.42, 0.30 ), 0.3 ),      # the Fleet's walls under the tide line
    "lt_mud": ( "buildings/soil", ( 0.26, 0.40, 0.62 ), 0.42 ),             # grey estuary mud, drying on the flats
    "lt_mud_wet": ( "buildings/soil", ( 0.17, 0.27, 0.42 ), 0.14 ),         # and wet towards the channel
    "lt_water": ( "buildings/water", ( 1.0, 1.0, 1.0 ), None ),            # dedicated animated material, written by WATER
    "lt_door_green": ( "buildings/planks", ( 0.40, 0.56, 0.46 ), None ),      # dedicated generated boards, written by DOORS
    "lt_door_red": ( "buildings/planks", ( 0.62, 0.34, 0.30 ), None ),
    "lt_jute": ( "buildings/canvas_plain", ( 0.84, 0.70, 0.50 ), None ),      # coffee sacks
    "lt_timber": ( "railhead/rw_wood", ( 0.13, 0.13, 0.14 ), None ),          # tarred piles and balks
    "lt_grating": ( "buildings/metal", ( 0.42, 0.44, 0.45 ), None ),         # the landings' and Fleet stairs' steel
    "lt_hold_rust": ( "boxyard/bx_rust", ( 0.64, 0.55, 0.50 ), None ),       # the lighter's hold: rusted brown
}
LT_PAINTED = {
    "lt_frame_green": ( ( 34, 62, 50 ), 0.0, 0.45 ),         # the east's window frames and ironwork
    "lt_frame_cream": ( ( 210, 202, 182 ), 0.0, 0.5 ),       # the west's
    "lt_steel": ( ( 78, 86, 88 ), 0.3, 0.5 ),                # the footbridge and the cranes' painted steel
    "lt_crane_red": ( ( 150, 52, 38 ), 0.2, 0.45 ),          # generated painted steel, written by CRANE
    "lt_hull_red": ( ( 104, 40, 32 ), 0.1, 0.6 ),            # the barge's antifouling
    "lt_hull_black": ( ( 30, 31, 33 ), 0.2, 0.5 ),
    "lt_rope": ( ( 140, 118, 84 ), 0.0, 0.85 ),
    "lt_rubber": ( ( 26, 26, 27 ), 0.0, 0.8 ),
}
GRAIN = { "lt_timber" }          # wood whose grain runs along each piece
# The west half's repaint, so each side reads as its team's: sooty brick, cream frames, red doors.
WEST_PAINTS = { "brick": "lt_brick_soot", "lt_frame_green": "lt_frame_cream", "lt_door_green": "lt_door_red" }


def lt_tile( paint ):
    """ A paint's tile size: its source's (building_textures', railhead_materials' or boxyard_materials'), else 64. """
    if paint == "lt_jute":
        return SACKS.TILE
    if paint in DOORS.VARIANTS:
        return DOORS.TILE_UNITS
    if paint in LT_MATERIALS:
        folder, name = LT_MATERIALS[paint][0].split( "/" )
        if folder == "railhead":
            return float( R.RM.paints()[name][1] )
        if folder == "boxyard":
            return 48.0             # boxyard_materials.SMALL's, at their real size (boxyard_map.bx_tile)
        return BT.tile_units( name )
    return 64.0


def write_materials():
    MAT_DIR.mkdir( parents=True, exist_ok=True )
    BRICK.write_materials()
    WATER.write_materials()
    DECK.write_materials()
    RAILS.write_materials()
    DOORS.write_materials()
    CRANE.write_materials()
    PLASTER.write_materials()
    LAMPS.write_materials()
    LANTERNS.write_materials()
    PAVING.write_materials()
    for name, ( source, tint, rough ) in LT_MATERIALS.items():
        if name == "lt_water" or name in DOORS.VARIANTS:
            continue
        if name == "lt_jute":
            SACKS.write_materials()
            continue
        if source == "buildings/brick":
            continue  # Lowtide's brick variants were written above, with their original tint and wet/glazed finish.
        text = ( K.ASSETS / f"materials/{source}.vmat" ).read_text( encoding="utf-8" )
        lines = []
        for line in text.splitlines():
            key = line.strip().split( " " )[0].strip( '"' )
            if key == "g_vColorTint":
                line = f'    g_vColorTint "[{tint[0]:.3f} {tint[1]:.3f} {tint[2]:.3f} 1.0]"'
            elif key == "TextureRoughness" and rough is not None:
                line = f'    TextureRoughness "[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]"'
            elif line.startswith( "//" ):
                line = f"// Tools/lowtide_map.py, from materials/{source}.vmat"
            lines.append( line )
        K.write_text( MAT_DIR / f"{name}.vmat", "\n".join( lines ) + "\n" )
    import railhead_materials as RM
    for name, ( colour, metal, rough ) in LT_PAINTED.items():
        if name == CRANE.PAINT:
            continue
        text = RM.painted_vmat( name, colour, metal, rough ).replace( "Tools/railhead_materials.py", "Tools/lowtide_map.py" )
        K.write_text( MAT_DIR / f"{name}.vmat", text )
    SKIP.write_materials()
    FORKLIFT.write_materials()
    STAIRS.write_materials()
    PALLETS.write_materials()
    SHIPYARD.write_materials()
    CONTAINER.write_materials()


def configure( model ):
    """ Points the lt_ paints at their materials, then the rest as Railhead's script does (rw_ and building_textures'). """
    for paint in model.polygons:
        if paint.startswith( "lt_" ):
            model.material_overrides[paint] = f"materials/lowtide/{paint}.vmat"
            model.tile_overrides[paint] = lt_tile( paint )
    R.configure( model )
    SKIP.configure( model )
    FORKLIFT.configure( model )
    STAIRS.configure( model )
    PALLETS.configure( model )
    SHIPYARD.configure( model )
    BRICK.configure( model )
    PAVING.configure( model )
    CONTAINER.configure( model )
    CRANE.configure( model )
    DECK.configure( model )
    RAILS.configure( model )
    PLASTER.configure( model )
    LAMPS.configure( model )
    LANTERNS.configure( model )
    model.grain_paints |= { p for p in model.polygons if p in GRAIN }
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers

def keyed( *key ):
    text = ",".join( f"{float( k ):.1f}" if isinstance( k, ( int, float, np.integer, np.floating ) ) else str( k ) for k in key )
    return zlib.crc32( text.encode() )


def chance( share, *key ):
    return ( keyed( *key ) % 10007 ) / 10007.0 < share


def card( m, paint, points, towards, uv=None, both=False ):
    """ A polygon wound to face towards (a plan vector). """
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
        if uv is not None:
            uv = list( uv[:1] ) + list( uv[:0:-1] )
    m.polygon( paint, pts, both_sides=both, uv=uv )


def rod( m, a, b, r, paint, sides=6 ):
    """ A round bar from a to b (drawn only). """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    axis = K.normalise( b - a )
    side = np.cross( axis, ( 0.0, 0.0, 1.0 ) )
    if np.linalg.norm( side ) < 1e-6:
        side = np.array( ( 1.0, 0.0, 0.0 ) )
    side = K.normalise( side )
    up = np.cross( side, axis )
    ring = [ side * math.cos( 2 * math.pi * k / sides ) * r + up * math.sin( 2 * math.pi * k / sides ) * r for k in range( sides ) ]
    for k in range( sides ):
        p, q = ring[k], ring[( k + 1 ) % sides]
        card( m, paint, [ a + p, a + q, b + q, b + p ], ( p + q ) / 2 )


def bar( m, a, b, r, paint, sides=8 ):
    """ A round bar from a to b, shaded smooth, its end at b capped (drawn only). """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    axis = K.normalise( b - a )
    side = np.cross( axis, ( 0.0, 0.0, 1.0 ) )
    if np.linalg.norm( side ) < 1e-6:
        side = np.array( ( 1.0, 0.0, 0.0 ) )
    side = K.normalise( side )
    up = np.cross( side, axis )
    out = [ side * math.cos( 2 * math.pi * k / sides ) + up * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
    for k in range( sides ):
        p, q = out[k], out[( k + 1 ) % sides]
        pts, nrm = [ a + p * r, a + q * r, b + q * r, b + p * r ], [ p, q, q, p ]
        if np.dot( np.cross( pts[1] - pts[0], pts[2] - pts[0] ), p + q ) < 0:
            pts, nrm = pts[:1] + pts[:0:-1], nrm[:1] + nrm[:0:-1]
        m.polygon( paint, pts, normals=nrm )
    card( m, paint, [ b + p * r for p in out ], axis )


def torus( m, centre, u, v, R, r, paint, segments=18, sides=8 ):
    """ A ring: its centre line a circle of radius R in the plane of u and v, the bar r thick, shaded smooth (drawn
    only). """
    c = np.asarray( centre, float )
    u, v = K.normalise( u ), K.normalise( v )
    w = K.normalise( np.cross( u, v ) )

    def point( i, j ):
        t, p = 2 * math.pi * i / segments, 2 * math.pi * j / sides
        radial = u * math.cos( t ) + v * math.sin( t )
        normal = radial * math.cos( p ) + w * math.sin( p )
        return c + radial * R + normal * r, normal

    for i in range( segments ):
        for j in range( sides ):
            quad = [ point( i, j ), point( i + 1, j ), point( i + 1, j + 1 ), point( i, j + 1 ) ]
            pts, nrm = [ q[0] for q in quad ], [ q[1] for q in quad ]
            if np.dot( np.cross( pts[1] - pts[0], pts[2] - pts[0] ), sum( nrm ) ) < 0:
                pts, nrm = pts[:1] + pts[:0:-1], nrm[:1] + nrm[:0:-1]
            m.polygon( paint, pts, normals=nrm )


def column( m, e, n, z0, z1, r, paint, sides=10, surface=None ):
    """ An upright round column, with its collision as a box round it. """
    m.cylinder( ( e, n ), r, z0, z1, { "side": paint, "top": None, "bottom": None }, sides=sides )
    if surface:
        m.collision_box( ( e - r, n - r, z0 ), ( e + r, n + r, z1 ), surface )


def railing( m, p0, p1, z0, height=40.0, paint="iron_black", posts=60.0, surface=METAL, lattice=False ):
    """ An iron railing from p0 to p1 (plan ( e, n )): posts, a top rail and a bottom rail, bars between (or a diagonal
    lattice), and a thin collision box its height. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    length = float( np.linalg.norm( p1 - p0 ) )
    if length < 1:
        return
    along = ( p1 - p0 ) / length
    count = max( 1, int( round( length / posts ) ) )
    for k in range( count + 1 ):
        p = p0 + along * length * k / count
        m.box( ( p[0] - 1.2, p[1] - 1.2, z0 ), ( p[0] + 1.2, p[1] + 1.2, z0 + height + 1 ), paint )
    for z, size in ( ( z0 + height - 1.5, 1.5 ), ( z0 + 4, 1.0 ) ):
        a, b = np.append( p0, z ), np.append( p1, z )
        m.beam( a, b, ( 1.6, size * 2 ), paint )
    if lattice:
        step = 12.0
        bars = int( length / step )
        for k in range( bars ):
            a = p0 + along * ( k * step )
            b = p0 + along * min( length, ( k + 1 ) * step )
            rod( m, ( *a, z0 + 5 ), ( *b, z0 + height - 2.5 ), 0.45, paint, sides=4 )
            rod( m, ( *b, z0 + 5 ), ( *a, z0 + height - 2.5 ), 0.45, paint, sides=4 )
    else:
        bars = int( length / 5.5 )
        for k in range( 1, bars ):
            a = p0 + along * ( length * k / bars )
            m.box( ( a[0] - 0.35, a[1] - 0.35, z0 + 5 ), ( a[0] + 0.35, a[1] + 0.35, z0 + height - 2.5 ),
                   { "default": paint, "+z": None, "-z": None } )
    if surface:
        lo = np.minimum( p0, p1 ) - np.abs( np.array( ( along[1], along[0] ) ) ) * 1.5
        hi = np.maximum( p0, p1 ) + np.abs( np.array( ( along[1], along[0] ) ) ) * 1.5
        m.collision_box( ( lo[0], lo[1], z0 ), ( hi[0], hi[1], z0 + height ), surface )


def stairs( m, e0, e1, n_top, n_foot, z_top, z_foot, tread="ashlar_grey", riser="ashlar_grey", side="brick",
            surface=STONE ):
    """ A straight flight along n from its top (n_top, level with z_top) down to its foot (n_foot, z_foot): risers of
    7.4 at most, the steps drawn, the collision one ramp hull along the nosings (a wedge down under the foot, so nothing
    walks under it). """
    rise = z_top - z_foot
    count = max( 1, int( math.ceil( rise / 7.4 ) ) )
    step_z = rise / count
    sign = 1.0 if n_foot > n_top else -1.0
    step_n = abs( n_foot - n_top ) / count
    base = z_foot - 12
    for k in range( count ):
        top = z_top - step_z * k
        na = n_top + sign * step_n * k
        nb = na + sign * step_n
        if tread == STAIRS.TREAD:
            STAIRS.step( m, e0, e1, na, nb, top, base, step_z, k, side )
        else:
            m.box( ( e0, min( na, nb ), base ), ( e1, max( na, nb ), top ),
                   { "+z": tread, "default": side, ( "+n" if sign > 0 else "-n" ): riser, ( "-n" if sign > 0 else "+n" ): None,
                     "-z": None } )
    first, last = n_top + sign * step_n, n_foot + sign * step_n
    pts = [ ( e, n, z ) for e in ( e0, e1 ) for n, z in ( ( n_top, z_top ), ( first, z_top ), ( last, z_foot ), ( n_top, base ),
                                                           ( last, base ) ) ]
    m.hull( pts, surface )


def sloped_rail( m, a, b, height=38.0, paint="iron_black", posts=50.0, surface=METAL ):
    """ A handrail on posts along a stair, from a to b (points on its treads' line), with its collision a thin slab
    following it. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    length = float( np.linalg.norm( b - a ) )
    count = max( 1, int( round( length / posts ) ) )
    for k in range( count + 1 ):
        p = a + ( b - a ) * k / count
        m.box( ( p[0] - 1.1, p[1] - 1.1, p[2] ), ( p[0] + 1.1, p[1] + 1.1, p[2] + height + 1 ), paint )
    up = np.array( ( 0.0, 0.0, height ) )
    m.beam( a + up, b + up, ( 1.6, 2.6 ), paint )
    m.beam( a + up * 0.5, b + up * 0.5, ( 1.0, 1.4 ), paint )
    if surface:
        along = K.normalise( b - a )
        level = K.normalise( np.array( ( along[0], along[1], 0.0 ) ) )
        side = np.array( ( -level[1], level[0], 0.0 ) )
        upward = np.cross( along, side )
        if upward[2] < 0:
            side, upward = -side, -upward
        m.oriented_box( ( a + b ) / 2 + upward * height / 2, ( along, side, upward ), ( length, 2.0, height ), None, surface )


# ---------------------------------------------------------------------------------------------------------------------
# Walls and their dressing (as Belltower's)

def wall_out( wall ):
    d, sign = wall.outer()
    out = np.zeros( 3 )
    out[1 if wall.axis == "e" else 0] = sign
    return d, sign, out


def slab( m, wall, r0, r1, d0, d1, z0, z1, paint, surface=None, back=False ):
    """ A box on wall's outer face: r0..r1 along it, d0..d1 out of it (negative: into it), z0..z1. Its back (the face
    towards the wall) isn't drawn when it's on the face or in it, where nobody sees it. """
    d, sign, _ = wall_out( wall )
    lo, hi = wall.lo_hi( min( r0, r1 ), max( r0, r1 ), d + sign * d0, d + sign * d1, z0, z1 )
    if paint is not None and ( back or ( min( d0, d1 ) >= -0.01 and max( d0, d1 ) > 0 ) ):
        back = { "+n": "-n", "-n": "+n", "+e": "-e", "-e": "+e" }[wall.outward]
        paint = { **( paint if isinstance( paint, dict ) else { "default": paint } ), back: None }
    m.box( lo, hi, paint, surface )


def outline( o, steps=10 ):
    if o.arched:
        return [ ( o.r0, o.z0 ), ( o.r1, o.z0 ) ] + arc( ( o.r0 + o.r1 ) / 2, o.spring, o.radius, steps, 0.0, 180.0 )
    return [ ( o.r0, o.z0 ), ( o.r1, o.z0 ), ( o.r1, o.z1 ), ( o.r0, o.z1 ) ]


def head_at( o, r ):
    """ The top of an opening at r along its wall (an arch's curve). """
    if not o.arched:
        return o.z1
    rc, rad = ( o.r0 + o.r1 ) / 2, o.radius
    return o.spring + math.sqrt( max( 0.0, rad * rad - ( r - rc ) ** 2 ) )


class Style:
    def __init__( self, brick="brick", frame="lt_frame_green", door="lt_door_green", band="lt_brick_glazed",
                  stone="ashlar_grey", pane="rw_window_dark" ):
        self.brick, self.frame, self.door, self.band, self.stone, self.pane = brick, frame, door, band, stone, pane


EAST = Style()


def window( m, wall, o, style, pane=None, glass=None ):
    """ A window: its pane 6 into the wall (in glass, with a collision pane, where the building's open), a cast-iron
    frame of small panes, the glazed brick arch over it and a stone sill. """
    d, sign, out = wall_out( wall )
    depth = 6.0
    pts = [ wall.point( r, d - sign * depth, z ) for r, z in outline( o ) ]
    if glass is not None:
        card( glass, "rw_glass", pts, out )
        slab( glass, wall, o.r0, o.r1, -depth - 1, -depth + 1, o.z0, o.z1, None, GLASS )
    else:
        card( m, pane or style.pane, pts, out )
    bar, fd = 1.6, -depth + 0.8
    top = o.spring if o.arched else o.z1
    # Sides, foot and head of the frame, then glazing bars: two uprights and a bar every 20.
    slab( m, wall, o.r0, o.r0 + 3, fd - 1, fd + 1.4, o.z0, top, style.frame, back=True )
    slab( m, wall, o.r1 - 3, o.r1, fd - 1, fd + 1.4, o.z0, top, style.frame, back=True )
    slab( m, wall, o.r0, o.r1, fd - 1, fd + 1.4, o.z0, o.z0 + 3, style.frame, back=True )
    if not o.arched:
        slab( m, wall, o.r0, o.r1, fd - 1, fd + 1.4, o.z1 - 3, o.z1, style.frame, back=True )
    width = o.r1 - o.r0
    for k in ( 1, 2 ):
        r = o.r0 + width * k / 3
        slab( m, wall, r - bar / 2, r + bar / 2, fd - 0.5, fd + 0.9, o.z0 + 3, head_at( o, r ) - 0.5, style.frame, back=True )
    z = o.z0 + 3 + 19
    while z < top - 4:
        slab( m, wall, o.r0 + 3, o.r1 - 3, fd - 0.5, fd + 0.9, z - bar / 2, z + bar / 2, style.frame, back=True )
        z += 20
    if o.arched:
        slab( m, wall, o.r0 + 3, o.r1 - 3, fd - 0.5, fd + 0.9, top - bar / 2, top + bar / 2, style.frame, back=True )
        arch_ring( m, wall, o, style.band )
    else:
        slab( m, wall, o.r0 - 3, o.r1 + 3, 0.0, 1.2, o.z1, o.z1 + 9, style.band )
    slab( m, wall, o.r0 - 4, o.r1 + 4, -1.0, 2.6, o.z0 - 4, o.z0, style.stone )


def arch_ring( m, wall, o, paint, width=7.0, proud=1.0, steps=10 ):
    """ The ring of glazed bricks round an arch's head, a little proud of the wall. """
    d, sign, out = wall_out( wall )
    rc, zs, rad = ( o.r0 + o.r1 ) / 2, o.spring, o.radius
    inner = arc( rc, zs, rad, steps, 180.0, 0.0 )
    outer = arc( rc, zs, rad + width, steps, 180.0, 0.0 )
    face = d + sign * proud
    for k in range( steps ):
        quad = [ wall.point( inner[k][0], face, inner[k][1] ),
                 wall.point( inner[k + 1][0], face, inner[k + 1][1] ), wall.point( outer[k + 1][0], face, outer[k + 1][1] ),
                 wall.point( outer[k][0], face, outer[k][1] ) ]
        card( m, paint, quad, out )
        # The ring's outer edge, back to the wall.
        a, b = outer[k], outer[k + 1]
        edge = [ wall.point( a[0], d, a[1] ), wall.point( b[0], d, b[1] ), wall.point( b[0], face, b[1] ), wall.point( a[0], face, a[1] ) ]
        mid = np.array( ( ( a[0] + b[0] ) / 2 - rc, ( a[1] + b[1] ) / 2 - zs ) )
        towards = wall.point( mid[0], 0, mid[1] ) - wall.point( 0, 0, 0 )
        card( m, paint, edge, towards )
    for r0, r1 in ( ( o.r0 - width, o.r0 ), ( o.r1, o.r1 + width ) ):
        slab( m, wall, r0, r1, 0.0, proud, zs - 4, zs, paint )


def leaves_open( m, wall, o, style ):
    """ A loading bay's or a gate's two wooden leaves, folded back flat against the wall either side, with their iron
    strap hinges. """
    half = ( o.r1 - o.r0 ) / 2
    top = o.z1 - 2
    for r0, r1 in ( ( o.r0 - half - 2, o.r0 - 2 ), ( o.r1 + 2, o.r1 + 2 + half ) ):
        slab( m, wall, r0, r1, 0.0, 2.6, o.z0 + 2, top, style.door )
        for z in ( o.z0 + 14, top - 14 ):
            slab( m, wall, r0 + 2, r1 - 2, 2.6, 3.1, z - 1.5, z + 1.5, "iron_black" )
    slab( m, wall, o.r0 - 6, o.r1 + 6, 0.0, 1.4, o.z1, o.z1 + 10, style.band )
    # Ground-level openings have no wall below them to form a sill. Join the inner floor to the outer stone lip.
    if o.z0 <= wall.z[0] + 1e-6:
        slab( m, wall, o.r0, o.r1, -wall_thick( wall ), -0.5, o.z0 - 4, o.z0,
              { "+z": style.stone, "default": None } )
    slab( m, wall, o.r0 - 3, o.r1 + 3, -0.5, 3.0, o.z0 - 4, o.z0, style.stone )


def leaves_shut( m, wall, o, style ):
    """ A pair of wooden doors shut in the opening, 8 into the wall, with strap hinges and the meeting stile. """
    slab( m, wall, o.r0, o.r1, -10.0, -8.0, o.z0, o.z1, style.door )
    rc = ( o.r0 + o.r1 ) / 2
    slab( m, wall, rc - 1, rc + 1, -8.0, -7.4, o.z0, o.z1, "iron_black" )
    for z in ( o.z0 + 14, o.z1 - 14 ):
        slab( m, wall, o.r0 + 2, rc - 3, -8.0, -7.5, z - 1.5, z + 1.5, "iron_black" )
        slab( m, wall, rc + 3, o.r1 - 2, -8.0, -7.5, z - 1.5, z + 1.5, "iron_black" )
    slab( m, wall, o.r0 - 6, o.r1 + 6, 0.0, 1.4, o.z1, o.z1 + 10, style.band )
    if o.z0 <= wall.z[0] + 1e-6:
        # At the wall's foot there's no wall under the opening, so the recess in front of the leaves had no floor and
        # the sky showed through it. A stone threshold fills it, under the leaves and an inch over the street.
        slab( m, wall, o.r0, o.r1, -10.0, -0.5, o.z0 - 4, o.z0 + 1, { "+z": style.stone, "default": None } )
        slab( m, wall, o.r0 - 3, o.r1 + 3, -0.5, 3.0, o.z0 - 4, o.z0 + 1, style.stone )
    elif o.z0 > 10:
        slab( m, wall, o.r0 - 3, o.r1 + 3, -0.5, 3.0, o.z0 - 4, o.z0, style.stone )


def dress( m, wall, style, glass=None ):
    """ Every opening of a wall dressed by its kind: windows ('glass_arch', 'glass'), open bays and gates ('door', with
    their leaves folded back unless o.bare), shut loading doors ('shut'). """
    for o in wall.openings:
        if o.kind in ( "glass_arch", "glass" ):
            window( m, wall, o, style, glass=glass if getattr( o, "real", False ) else None )
        elif o.kind == "door":
            if not getattr( o, "bare", False ):
                leaves_open( m, wall, o, style )
        elif o.kind == "shut":
            leaves_shut( m, wall, o, style )


def corner_reach( corners, depth ):
    """ How far past each end of its run a moulding depth proud of the wall goes, so it turns the building's outside
    corners. corners holds, for each end, None where there's no corner, else how far short of the corner the run stops:
    T where it runs inside the end front's thickness (a side front), 0 where it reaches the corner (an end front). The
    side front carries the moulding round, out to the end front's own projection; the end front stops at the corner, so
    nothing is drawn twice. """
    return tuple( gap + depth if gap is not None and gap > 0 else 0.0 for gap in corners )


def courses( m, wall, style, levels, skip=(), corners=( None, None ) ):
    """ The glazed brick bands at each floor line, along the whole wall, and a granite plinth at its foot between its
    doorways, both turning the outside corners (corner_reach). """
    r0, r1 = wall.run
    lo, hi = corner_reach( corners, 2.0 )
    for z in levels:
        slab( m, wall, r0 - lo, r1 + hi, 0.0, 2.0, z - 11, z - 2, style.band )
    if "plinth" not in skip:
        lo, hi = corner_reach( corners, 2.5 )
        edges = sorted( [ ( o.r0, o.r1 ) for o in wall.openings if o.z0 <= 1 ] )
        at = r0 - lo
        for a, b in edges + [ ( r1 + hi, r1 + hi ) ]:
            if a > at + 1:
                slab( m, wall, at, a, 0.0, 2.5, 0.0, 44.0, style.stone )
            at = max( at, b )


def pilasters( m, wall, style, at, z0, z1, width=20.0 ):
    for r in at:
        slab( m, wall, r - width / 2, r + width / 2, 0.0, 4.0, z0, z1, style.brick )
        slab( m, wall, r - width / 2 - 2, r + width / 2 + 2, 0.0, 5.5, z1 - 6, z1, style.band )


def cornice( m, wall, style, eaves, corners=( None, None ) ):
    """ The eaves: a corbel frieze, a projecting band, and the parapet's granite coping (the wall rises to eaves + 40).
    The band turns the outside corners like the courses (corner_reach). The coping is the other way round: at a corner
    the end front's coping runs out over the side front's projection, and the side front's starts behind it. """
    r0, r1 = wall.run
    r = r0 + 10
    while r < r1 - 6:
        slab( m, wall, r - 3, r + 3, 0.0, 5.0, eaves - 36, eaves - 22, style.band )
        r += 16
    lo, hi = corner_reach( corners, 7.0 )
    slab( m, wall, r0 - lo, r1 + hi, 0.0, 7.0, eaves - 22, eaves - 12, style.band )
    cap = [ 2.0 if gap is None else ( -2.0 if gap > 0 else 4.0 ) for gap in corners ]
    slab( m, wall, r0 - cap[0], r1 + cap[1], -wall_thick( wall ) - 2, 4.0, eaves + 40, eaves + 46, style.stone )


def wall_thick( wall ):
    return abs( wall.across[1] - wall.across[0] )


def stepped_gable( m, wall, style, r0, r1, z0, steps=5, step_h=46.0, pinnacles=True ):
    """ A Hanseatic stepped gable on the wall's top between r0 and r1, from z0: a stack of steps narrowing to the
    middle, each capped with granite, with a blind arched niche in each step and a pinnacle on top. """
    rc = ( r0 + r1 ) / 2
    half = ( r1 - r0 ) / 2
    d, sign, out = wall_out( wall )
    t = wall_thick( wall )
    for k in range( steps ):
        w = half * ( 1 - k / steps )
        za, zb = z0 + k * step_h, z0 + ( k + 1 ) * step_h
        slab( m, wall, rc - w, rc + w, -t, 0.0, za, zb, style.brick )
        slab( m, wall, rc - w - 1.5, rc - w + half / steps + 1.5, -t - 1.5, 1.5, zb, zb + 5, style.stone )
        slab( m, wall, rc + w - half / steps - 1.5, rc + w + 1.5, -t - 1.5, 1.5, zb, zb + 5, style.stone )
        if pinnacles:
            for side in ( -1, 1 ):
                r = rc + side * ( w - half / steps / 2 )
                slab( m, wall, r - 4, r + 4, -t / 2 - 4, -t / 2 + 4, zb + 5, zb + 26, style.brick )
                slab( m, wall, r - 5, r + 5, -t / 2 - 5, -t / 2 + 5, zb + 26, zb + 29, style.stone )
        # Blind niches in each step, arched, in glazed brick.
        niche_w = min( 24.0, w * 2 / max( 1, round( w / 40 ) ) - 14 )
        count = max( 1, int( round( w / 40 ) ) )
        for j in range( count ):
            r = rc - w + ( 2 * w ) * ( j + 0.5 ) / count
            if niche_w > 8 and zb - za > 30:
                o = K.Opening( r - niche_w / 2, r + niche_w / 2, za + 8, zb - 6, "glass_arch" )
                pts = [ wall.point( rr, d + sign * 0.6, zz ) for rr, zz in outline( o, 6 ) ]
                card( m, style.band, pts, out )
    top = z0 + steps * step_h + 5
    slab( m, wall, rc - 6, rc + 6, -t / 2 - 6, -t / 2 + 6, top, top + 40, style.brick )
    slab( m, wall, rc - 7, rc + 7, -t / 2 - 7, -t / 2 + 7, top + 40, top + 44, style.stone )
    spire( m, wall.point( rc, d - sign * t / 2, 0 )[:2], top + 44, 7.0, 34.0, "copper" )


def spire( m, centre, z0, radius, height, paint, sides=8 ):
    c = np.asarray( centre, float )
    ring = [ np.array( ( c[0] + radius * math.cos( 2 * math.pi * ( k + 0.5 ) / sides ),
                         c[1] + radius * math.sin( 2 * math.pi * ( k + 0.5 ) / sides ), z0 ) ) for k in range( sides ) ]
    apex = np.array( ( c[0], c[1], z0 + height ) )
    for k in range( sides ):
        a, b = ring[k], ring[( k + 1 ) % sides]
        mid = ( a + b ) / 2
        card( m, paint, [ a, b, apex ], np.array( ( mid[0] - c[0], mid[1] - c[1], radius / max( height, 1 ) ) ) )
    m.box( ( c[0] - 0.8, c[1] - 0.8, z0 + height - 2 ), ( c[0] + 0.8, c[1] + 0.8, z0 + height + 14 ), "iron_black" )


def oriel( m, wall, style, r, z0, z1, width=96.0, depth=40.0, hoist=True ):
    """ A winch oriel (Windenerker) at the top of a column of loading doors: a brick bay corbelled out of the wall, with
    a copper hood over it and the hoist's beam reaching out of its gable, with a pulley and a rope with a hook. """
    d, sign, out = wall_out( wall )
    slab( m, wall, r - width / 2, r + width / 2, 0.0, depth, z0, z1, style.brick )
    for k in range( 4 ):
        slab( m, wall, r - width / 2 + 2 + k * 2, r + width / 2 - 2 - k * 2, 0.0, depth - 6 - k * 9, z0 - 8 * ( k + 1 ), z0 - 8 * k,
              style.band )
    slab( m, wall, r - width / 2 - 2, r + width / 2 + 2, 0.0, depth + 2, z1, z1 + 5, style.stone )
    # The hood: a little gabled copper roof, its ridge out from the wall.
    hw, rise = width / 2 + 3, width * 0.42
    base = z1 + 5
    for side in ( -1, 1 ):
        pts = [ wall.point( r + side * hw, d, base ), wall.point( r + side * hw, d + sign * ( depth + 4 ), base ),
                wall.point( r, d + sign * ( depth + 4 ), base + rise ), wall.point( r, d, base + rise ) ]
        towards = wall.point( side, 0, 1.0 ) - wall.point( 0, 0, 0 )
        card( m, "copper", pts, towards )
    gable = [ wall.point( r - hw, d + sign * ( depth + 4 ), base ), wall.point( r + hw, d + sign * ( depth + 4 ), base ),
              wall.point( r, d + sign * ( depth + 4 ), base + rise ) ]
    card( m, style.brick, gable, out )
    # A small arched door in the oriel's face, shut.
    o = K.Opening( r - 16, r + 16, z0 + 14, z1 - 10, "glass_arch" )
    pts = [ wall.point( rr, d + sign * ( depth + 0.4 ), zz ) for rr, zz in outline( o, 6 ) ]
    card( m, style.door, pts, out )
    if hoist:
        beam_z = base + rise * 0.45
        a = wall.point( r, d + sign * ( depth - 4 ), beam_z )
        b = wall.point( r, d + sign * ( depth + 34 ), beam_z )
        m.box( np.minimum( a, b ) - 3, np.maximum( a, b ) + 3, "iron_black" )
        tip = wall.point( r, d + sign * ( depth + 30 ), beam_z - 3 )
        m.cylinder( tip[:2], 5.0, tip[2] - 10, tip[2] - 3, "iron_black", sides=8 )
        hang = keyed( "hook", r, z0, wall.across[0] ) % 300
        bottom = max( FLOOR1 + 120.0, z0 - 160.0 - hang )
        rod( m, ( *tip[:2], tip[2] - 10 ), ( *tip[:2], bottom ), 0.6, "lt_rope", sides=4 )
        m.box( ( tip[0] - 2, tip[1] - 2, bottom - 10 ), ( tip[0] + 2, tip[1] + 2, bottom ), "iron_black" )


def roof( m, e0, e1, n0, n1, z0, along="n", pitch=0.8, paint="slate", ridge="copper", ends=True ):
    """ A pitched roof over a block, its ridge along `along`, ends left open (gables close them): drawn only. """
    if along == "n":
        half = ( e1 - e0 ) / 2
        top = z0 + half * pitch
        ec = ( e0 + e1 ) / 2
        card( m, paint, [ ( e0, n0, z0 ), ( e0, n1, z0 ), ( ec, n1, top ), ( ec, n0, top ) ], ( -pitch, 0, 1 ) )
        card( m, paint, [ ( e1, n0, z0 ), ( e1, n1, z0 ), ( ec, n1, top ), ( ec, n0, top ) ], ( pitch, 0, 1 ) )
        m.box( ( ec - 4, n0, top - 3 ), ( ec + 4, n1, top + 4 ), ridge )
        for n in ( n0, n1 ) if ends else ():
            card( m, "brick", [ ( e0, n, z0 ), ( e1, n, z0 ), ( ec, n, top ) ], ( 0, 1 if n == n1 else -1, 0 ) )
    else:
        half = ( n1 - n0 ) / 2
        top = z0 + half * pitch
        nc = ( n0 + n1 ) / 2
        card( m, paint, [ ( e0, n0, z0 ), ( e1, n0, z0 ), ( e1, nc, top ), ( e0, nc, top ) ], ( 0, -pitch, 1 ) )
        card( m, paint, [ ( e0, n1, z0 ), ( e1, n1, z0 ), ( e1, nc, top ), ( e0, nc, top ) ], ( 0, pitch, 1 ) )
        m.box( ( e0, nc - 4, top - 3 ), ( e1, nc + 4, top + 4 ), ridge )
        for e in ( e0, e1 ) if ends else ():
            card( m, "brick", [ ( e, n0, z0 ), ( e, n1, z0 ), ( e, nc, top ) ], ( 1 if e == e1 else -1, 0, 0 ) )
    return top


# ---------------------------------------------------------------------------------------------------------------------
# The warehouse (Speicher) each side of the Fleet. Built east (e 240..1000, n -400..1150); the west one is its mirror.

SPEICHER = ( FLEET, 1000.0, -400.0, 1150.0 )      # e0, e1, n0, n1: outside faces
T = 20.0                                           # its walls' thickness
LEVELS = ( FLOOR1, CEILING, 502.0, 652.0, 802.0 )   # floor lines up the fronts (string courses under each)
UPPER = ( CEILING, 502.0, 652.0, 802.0 )           # the closed storeys over the ceiling
FLEET_BAYS = [ -315.0 + 130.0 * k for k in range( 11 ) ]     # bays along the Fleet front and the cross street front
END_BAYS = [ 310.0, 430.0, 620.0, 810.0, 930.0 ]             # bays along the north and south ends
A_BAY, S_BAY = 855.0, -55.0                        # the ground floor's loading bays onto the Fleet
UPPER_BAYS = ( 595.0, 985.0 )                      # the mezzanine's, over the Fleet
MEZZ_N = 380.0                                     # the mezzanine covers n 380..1130 (the north half)
STAIR = ( 922.0, 978.0, 440.0, 733.0 )             # e0, e1, its foot's n, its top's n (up northwards)
COLUMNS = [ ( e, n ) for e in ( 500.0, 740.0 ) for n in ( -120.0, 130.0, 396.0, 630.0, 880.0 ) ]
GIRDER_W = 8.0                                     # the timber girders' half-width (a 16-inch square balk)
CEILING_GIRDER = ( CEILING - 28, CEILING - 12 )   # under the ceiling's joists
MEZZ_GIRDER = ( FLOOR1 - 44, FLOOR1 - 28 )        # under the mezzanine's joists
LANDING_W = 50.0                                   # the landings and stairs onto the Fleet stand out this far


def ground_storey( wall, bays, doors, real=True, z=( 64.0, 150.0 ), width=44.0, door_w=100.0, door_h=140.0 ):
    for r in bays:
        if r in doors:
            o = wall.add( r, doors[r] if isinstance( doors[r], float ) else door_w, 0.0, door_h, "door" )
        else:
            o = wall.add( r, width, z[0], z[1], "glass_arch" )
            o.real = real


def upper_storeys( wall, bays, levels, columns=(), top_oriel=True, width=40.0 ):
    """ Windows on every storey from levels, and in the columns shut loading doors (the top storey's left for the
    oriel). """
    for i, z in enumerate( levels ):
        for r in bays:
            if r in columns:
                if top_oriel and i == len( levels ) - 1:
                    continue
                wall.add( r, 76.0, z + 8, z + 122, "shut" )
            else:
                wall.add( r, width, z + 30, z + 110, "glass_arch" )


def speicher( m, glass, style ):
    e0, e1, n0, n1 = SPEICHER
    ie0, ie1, in0, in1 = e0 + T, e1 - T, n0 + T, n1 - T
    top = EAVES + 40
    # The lower walls (z 0..368), open where people go.
    west = Wall( "n", ( in0, in1 ), ( e0, ie0 ), ( 0.0, CEILING + 16 ), "-e" )
    east = Wall( "n", ( in0, in1 ), ( ie1, e1 ), ( 0.0, CEILING + 16 ), "+e" )
    north = Wall( "e", ( e0, e1 ), ( in1, n1 ), ( 0.0, CEILING + 16 ), "+n" )
    south = Wall( "e", ( e0, e1 ), ( n0, in0 ), ( 0.0, CEILING + 16 ), "-n" )
    ground_storey( west, FLEET_BAYS, { A_BAY: 80.0, S_BAY: 80.0 }, door_h=112.0 )
    ground_storey( east, FLEET_BAYS, { A_BAY: 100.0, S_BAY: 100.0 } )
    ground_storey( north, END_BAYS, { 620.0: 120.0 }, door_h=150.0 )
    ground_storey( south, END_BAYS, { 620.0: 120.0 }, door_h=150.0 )
    for r in FLEET_BAYS:
        if r in UPPER_BAYS:
            o = west.add( r, 80.0, FLOOR1, FLOOR1 + 114, "door" )
        else:
            west.add( r, 44.0, FLOOR1 + 44, FLOOR1 + 144, "glass_arch" ).real = True
        east.add( r, 44.0, FLOOR1 + 44, FLOOR1 + 144, "glass_arch" ).real = True
    for wall in ( north, south ):
        for r in END_BAYS:
            if r == 620.0:
                wall.add( r, 80.0, FLOOR1 + 10, FLOOR1 + 124, "shut" )
            else:
                wall.add( r, 44.0, FLOOR1 + 44, FLOOR1 + 144, "glass_arch" ).real = True
    for wall in ( west, east, north, south ):
        # The end walls run the full width, so their ends are the building's corners.
        wall.build( m, style.brick, "whitewash", style.brick, style.brick if wall.axis == "e" else None, STONE )
        dress( m, wall, style, glass )
    # The safety bars across the mezzanine's bays, and the ground bays' thresholds.
    for r in UPPER_BAYS:
        slab( m, west, r - 40, r + 40, -T + 4, -T + 6, FLOOR1 + 34, FLOOR1 + 37, "iron_black" )
        m.collision_box( ( e0, r - 40, FLOOR1 ), ( e0 + 6, r + 40, FLOOR1 + 37 ), METAL )
    # The upper walls (368 to the parapet): closed storeys, drawn only, and one collision box each.
    up = {}
    for name, wall in ( ( "west", Wall( "n", ( in0, in1 ), ( e0, ie0 ), ( CEILING + 16, top ), "-e" ) ),
                        ( "east", Wall( "n", ( in0, in1 ), ( ie1, e1 ), ( CEILING + 16, top ), "+e" ) ),
                        ( "north", Wall( "e", ( e0, e1 ), ( in1, n1 ), ( CEILING + 16, top ), "+n" ) ),
                        ( "south", Wall( "e", ( e0, e1 ), ( n0, in0 ), ( CEILING + 16, top ), "-n" ) ) ):
        up[name] = wall
    upper_storeys( up["west"], FLEET_BAYS, UPPER, columns=( S_BAY, ) + UPPER_BAYS )
    upper_storeys( up["east"], FLEET_BAYS, UPPER, columns=( 335.0, ) )
    upper_storeys( up["north"], END_BAYS, UPPER, columns=( 620.0, ) )
    upper_storeys( up["south"], END_BAYS, UPPER, columns=( 620.0, ) )
    for name, wall in up.items():
        wall.build( m, style.brick, None, style.brick, style.brick if name in ( "north", "south" ) else None, None )
        dress( m, wall, style )
        lo, hi = wall.lo_hi( *wall.run, *wall.across, *wall.z )
        m.collision_box( lo, hi, STONE )
    # The long walls run inside the end walls, so their mouldings carry round the four corners (corner_reach).
    for wall, bays in ( ( west, FLEET_BAYS ), ( east, FLEET_BAYS ), ( north, END_BAYS ), ( south, END_BAYS ) ):
        corners = ( T, T ) if wall.axis == "n" else ( 0.0, 0.0 )
        courses( m, wall, style, ( FLOOR1, ), skip=() if wall is not west else ( "plinth", ), corners=corners )
    for name, wall in up.items():
        corners = ( T, T ) if wall.axis == "n" else ( 0.0, 0.0 )
        courses( m, wall, style, LEVELS[1:], skip=( "plinth", ), corners=corners )
        cornice( m, wall, style, EAVES, corners=corners )
    # Pilasters every third bay up the long fronts over the open storeys (whose bays' leaves fold back where they'd
    # stand), and up the ends from the plinth.
    for name in ( "west", "east" ):
        pilasters( m, up[name], style, ( -120.0, 270.0, 660.0, 1050.0 ), CEILING + 16, EAVES - 36 )
    for wall in ( north, south ):
        pilasters( m, wall, style, ( 370.0, 870.0 ), 0.0, CEILING + 16 )
    for name in ( "north", "south" ):
        pilasters( m, up[name], style, ( 370.0, 870.0 ), CEILING + 16, EAVES - 36 )
    # Winch oriels at the tops of the loading columns, their hooks hanging over the Fleet and the street.
    for r in ( S_BAY, ) + UPPER_BAYS:
        oriel( m, up["west"], style, r, 812.0, 930.0 )
    oriel( m, up["east"], style, 335.0, 812.0, 930.0 )
    for name in ( "north", "south" ):
        oriel( m, up[name], style, 620.0, 812.0, 930.0 )
    # The roof, its ridge north to south, and the stepped gables over both ends.
    roof( m, e0 - 2, e1 + 2, n0 + 10, n1 - 10, top, along="n", pitch=0.8, ends=False )
    for name in ( "north", "south" ):
        stepped_gable( m, up[name], style, e0, e1, top + 6, steps=5, step_h=61.0 )
    turret( m, style, ( e0, n1 ), 560.0, top + 60 )
    # Inside: the ceiling, the mezzanine, the columns, beams, the stair and the railings.
    m.box( ( ie0, in0, CEILING ), ( ie1, in1, CEILING + 16 ), { "-z": "planks_dark", "default": None }, WOOD )
    for k in range( 12 ):
        n = in0 + 60 + 125 * k
        if n < in1 - 20:
            m.box( ( ie0, n - 5, CEILING - 12 ), ( ie1, n + 5, CEILING ), "lt_timber" )
    mezz = [ ( ie0, STAIR[0], MEZZ_N, in1 ), ( STAIR[0], ie1, MEZZ_N, STAIR[2] ), ( STAIR[0], ie1, STAIR[3], in1 ) ]
    for a, b, c, d in mezz:
        m.box( ( a, c, FLOOR1 - 16 ), ( b, d, FLOOR1 ), { "+z": "floorboards", "-z": "planks_dark", "default": "lt_timber" }, WOOD )
    for k in range( 7 ):
        n = MEZZ_N + 60 + 110 * k
        if n < in1 - 20 and not ( STAIR[2] - 10 < n < STAIR[3] + 10 ):
            m.box( ( ie0, n - 5, FLOOR1 - 28 ), ( ie1, n + 5, FLOOR1 - 16 ), "lt_timber" )
        elif n < in1 - 20:
            m.box( ( ie0, n - 5, FLOOR1 - 28 ), ( STAIR[0], n + 5, FLOOR1 - 16 ), "lt_timber" )
    m.box( ( ie0, MEZZ_N - 4, FLOOR1 - 30 ), ( ie1, MEZZ_N + 4, FLOOR1 - 16 ), "lt_timber" )
    # Each row of columns carries a timber girder under the joists, on a bolster over each column's cap. Under the
    # mezzanine the girder runs from its edge beam, whose end stands free, to the north wall; the upper columns stand
    # on the mezzanine's floor over the lower ones, and are a little slighter.
    for e in sorted( { e for e, _ in COLUMNS } ):
        girder( m, e, in0, in1, *CEILING_GIRDER, width=GIRDER_W )
        girder( m, e, MEZZ_N - 4, in1, *MEZZ_GIRDER, width=GIRDER_W, south_end=FLOOR1 - 30 )
    for e, n in COLUMNS:
        if n >= MEZZ_N - 1:
            iron_column( m, e, n, 0.0, MEZZ_GIRDER[0] - 8 )
            bolster( m, e, n, MEZZ_GIRDER[0] - 8, lo=MEZZ_N - 4, hi=in1, width=GIRDER_W )
            iron_column( m, e, n, FLOOR1, CEILING_GIRDER[0] - 8, r0=5.2, r1=4.4 )
        else:
            iron_column( m, e, n, 0.0, CEILING_GIRDER[0] - 8 )
        bolster( m, e, n, CEILING_GIRDER[0] - 8, lo=in0, hi=in1, width=GIRDER_W )
    stairs( m, STAIR[0] + 2, STAIR[1] - 2, STAIR[3], STAIR[2], FLOOR1, 0.0, tread=STAIRS.TREAD, riser=STAIRS.RISER,
            side="lt_timber", surface=WOOD )
    sloped_rail( m, ( STAIR[0] + 2, STAIR[2] + 12, 0.0 ), ( STAIR[0] + 2, STAIR[3], FLOOR1 ), surface=None )
    railing( m, ( ie0, MEZZ_N + 2 ), ( ie1, MEZZ_N + 2 ), FLOOR1, height=40.0, paint="iron_black", posts=90.0 )
    railing( m, ( STAIR[0] - 2, STAIR[2] ), ( STAIR[0] - 2, STAIR[3] ), FLOOR1, height=40.0, posts=70.0 )
    railing( m, ( STAIR[0], STAIR[2] - 2 ), ( ie1, STAIR[2] - 2 ), FLOOR1, height=40.0, posts=60.0 )
    # The bays' landings and their stairs down into the Fleet: from the A bay north, from the south bay south.
    for r, way in ( ( A_BAY, 1 ), ( S_BAY, -1 ) ):
        landing( m, r - 60, r + 60, way )


def iron_column( m, e, n, z0, zt, r0=6.0, r1=5.0 ):
    """ A cast-iron warehouse column as the Speicherstadt's were cast, from its floor at z0 to its cap at zt, where a
    timber bolster (bolster) takes the girder: a square foot plate with its edge chamfered, a moulded base (a torus,
    a fillet, a cove and an astragal), a round shaft tapering from r0 to r1 with a little entasis, an astragal round
    its neck, a bell capital flaring out to its lip, and a square cap plate, chamfered under, with its bolts' heads.
    Turned smooth, every moulding sized to the shaft (drawn for a 6-inch shaft's radius). Its collision is boxes for
    the plates and hulls round the rest. """
    s = r0 / 6.0
    plate, cap = 10.5 * s, 10.4 * s
    height = zt - z0
    m.box( ( e - plate, n - plate, z0 ), ( e + plate, n + plate, z0 + 3 * s ), { "-z": None, "+z": None, "default": "iron_black" } )
    frustum( m, ( e, n ), z0 + 3 * s, z0 + 4 * s, plate, plate - 1.0 * s, "iron_black" )
    base = arc_points( ( 7.9, 5.6 ), 1.6, -90.0, 90.0, 6 )                   # the torus, on the plate
    base += [ ( 7.3, 7.2 ), ( 7.3, 7.7 ) ]                                  # a fillet
    base += arc_points( ( 7.3, 8.7 ), 1.0, -90.0, -180.0, 3 )[1:]           # the cove
    base += arc_points( ( 6.3, 9.5 ), 0.8, -90.0, 90.0, 4 )[1:]             # the astragal
    profile = [ ( r * s, h * s ) for r, h in base ]
    h_shaft, h_neck = 10.3 * s, height - 14.0 * s
    for k in range( 5 ):
        t = k / 4
        profile.append( ( r0 - ( r0 - r1 ) * t ** 1.4, h_shaft + ( h_neck - h_shaft ) * t ) )
    # The capital: the necking astragal, the neck, the bell to its lip, the lip.
    profile.append( ( r1 + 0.3 * s, h_neck ) )
    profile += arc_points( ( r1 + 0.3 * s, h_neck + 0.8 * s ), 0.8 * s, -90.0, 90.0, 4 )[1:]
    profile += [ ( r1, h_neck + 1.6 * s ), ( r1, h_neck + 2.6 * s ) ]
    for k in range( 1, 6 ):
        t = k / 5
        profile.append( ( r1 + 3.6 * s * t ** 2.2, h_neck + ( 2.6 + 6.0 * t ) * s ) )
    profile += [ ( 9.2 * s, height - 5.4 * s ), ( 9.2 * s, height - 4.2 * s ) ]
    lathe( m, ( e, n ), z0, profile, "iron_black" )
    frustum( m, ( e, n ), zt - 4.2 * s, zt - 3.4 * s, cap - 0.8 * s, cap, "iron_black", top=False )
    m.box( ( e - cap, n - cap, zt - 3.4 * s ), ( e + cap, n + cap, zt ), { "-z": None, "+z": None, "default": "iron_black" } )
    for de in ( -1, 1 ):
        for dn in ( -1, 1 ):
            bolt_head( m, ( e + de * 3.5 * s, n + dn * 9.4 * s ), zt - 4.2 * s, 0.8 * s, 0.6 * s )
    m.collision_box( ( e - plate, n - plate, z0 ), ( e + plate, n + plate, z0 + 4 * s ), METAL )
    m.hull( ring( ( e, n ), 9.5 * s, z0 + 4 * s ) + ring( ( e, n ), 9.5 * s, z0 + 7.2 * s )
            + ring( ( e, n ), 7.1 * s, z0 + h_shaft ), METAL )
    m.hull( ring( ( e, n ), r0, z0 + h_shaft ) + ring( ( e, n ), r1, z0 + h_neck ), METAL )
    m.hull( ring( ( e, n ), r1 + 1.1 * s, z0 + h_neck ) + ring( ( e, n ), 9.2 * s, zt - 5.4 * s )
            + ring( ( e, n ), 9.2 * s, zt - 4.2 * s ), METAL )
    m.collision_box( ( e - cap, n - cap, zt - 4.2 * s ), ( e + cap, n + cap, zt ), METAL )


def ring( centre, r, z, sides=12 ):
    """ Points round a level circle, for a hull. """
    return [ ( centre[0] + r * math.cos( 2 * math.pi * k / sides ), centre[1] + r * math.sin( 2 * math.pi * k / sides ), z )
             for k in range( sides ) ]


def arc_points( centre, radius, a0, a1, steps ):
    """ steps + 1 points along a circle in a profile's plane, from a0 to a1 degrees (0 along its x, 90 along its y). """
    return [ ( centre[0] + radius * math.cos( math.radians( a0 + ( a1 - a0 ) * k / steps ) ),
               centre[1] + radius * math.sin( math.radians( a0 + ( a1 - a0 ) * k / steps ) ) ) for k in range( steps + 1 ) ]


def paint_tile( paint ):
    return lt_tile( paint ) if paint.startswith( "lt_" ) else BT.tile_units( paint )


def profile_normals( pts, closed=False, crease=40.0 ):
    """ For a 2D outline with its material on the left of the way it runs, each edge's normals at its two ends: its
    own outward normal ( dy, -dx ), shared with its neighbour's where the two turn by less than crease degrees (a
    smooth curve), else its own (an arris). """
    pts = [ np.asarray( p, float ) for p in pts ]
    count = len( pts ) if closed else len( pts ) - 1
    own = []
    for k in range( count ):
        d = pts[( k + 1 ) % len( pts )] - pts[k]
        own.append( K.normalise( ( d[1], -d[0] ) ) )
    limit = math.cos( math.radians( crease ) )

    def shared( k, other ):
        if other is None or np.dot( own[k], own[other] ) < limit:
            return own[k]
        return K.normalise( own[k] + own[other] )

    ends = []
    for k in range( count ):
        before = ( k - 1 ) % count if closed or k > 0 else None
        after = ( k + 1 ) % count if closed or k < count - 1 else None
        ends.append( ( shared( k, before ), shared( k, after ) ) )
    return ends


def smooth_quad( m, paint, points, normals, uv=None ):
    """ A quad shaded by a normal at each point, wound to face the way they do. """
    pts = [ np.asarray( p, float ) for p in points ]
    face = np.cross( pts[1] - pts[0], pts[2] - pts[0] ) + np.cross( pts[2] - pts[0], pts[3] - pts[0] )
    if np.linalg.norm( face ) < 1e-9:
        return
    normals = list( normals )
    if np.dot( face, np.sum( normals, axis=0 ) ) < 0:
        pts, normals = pts[:1] + pts[:0:-1], normals[:1] + normals[:0:-1]
        if uv is not None:
            uv = list( uv[:1] ) + list( uv[:0:-1] )
    m.polygon( paint, pts, normals=normals, uv=uv )


def lathe( m, centre, z0, profile, paint, sides=20 ):
    """ A round thing turned about an upright axis through centre (drawn only, its ends open): profile is its ( r, h )
    points from the bottom up, h over z0. Smooth round it, and down the profile where it curves. """
    ends = profile_normals( profile )
    tile = paint_tile( paint )
    r_uv = profile[0][0]
    turns = [ 2 * math.pi * j / sides for j in range( sides + 1 ) ]
    for k in range( len( profile ) - 1 ):
        ( ra, ha ), ( rb, hb ) = profile[k], profile[k + 1]
        na, nb = ends[k]
        for j in range( sides ):
            t0, t1 = turns[j], turns[j + 1]
            c0, s0, c1, s1 = math.cos( t0 ), math.sin( t0 ), math.cos( t1 ), math.sin( t1 )
            pts = [ ( centre[0] + ra * c0, centre[1] + ra * s0, z0 + ha ), ( centre[0] + ra * c1, centre[1] + ra * s1, z0 + ha ),
                    ( centre[0] + rb * c1, centre[1] + rb * s1, z0 + hb ), ( centre[0] + rb * c0, centre[1] + rb * s0, z0 + hb ) ]
            nrm = [ ( na[0] * c0, na[0] * s0, na[1] ), ( na[0] * c1, na[0] * s1, na[1] ),
                    ( nb[0] * c1, nb[0] * s1, nb[1] ), ( nb[0] * c0, nb[0] * s0, nb[1] ) ]
            uv = [ ( t0 * r_uv / tile, ha / tile ), ( t1 * r_uv / tile, ha / tile ),
                   ( t1 * r_uv / tile, hb / tile ), ( t0 * r_uv / tile, hb / tile ) ]
            smooth_quad( m, paint, pts, nrm, uv )


def frustum( m, centre, z0, z1, a0, a1, paint, top=True ):
    """ A square frustum about an upright axis (drawn only): half-widths a0 at z0 and a1 at z1, and its top (or, with
    top False, its bottom) closed. """
    e, n = centre
    lo = [ ( e - a0, n - a0, z0 ), ( e + a0, n - a0, z0 ), ( e + a0, n + a0, z0 ), ( e - a0, n + a0, z0 ) ]
    hi = [ ( e - a1, n - a1, z1 ), ( e + a1, n - a1, z1 ), ( e + a1, n + a1, z1 ), ( e - a1, n + a1, z1 ) ]
    for k in range( 4 ):
        out = ( np.add( lo[k], lo[( k + 1 ) % 4] ) / 2 - ( e, n, z0 ) ) * ( 1, 1, 0 )
        card( m, paint, [ lo[k], lo[( k + 1 ) % 4], hi[( k + 1 ) % 4], hi[k] ], out + ( 0, 0, a0 - a1 ) )
    m.polygon( paint, hi if top else lo[::-1] )


def bolt_head( m, centre, z, r, h ):
    """ A hex bolt head under a plate at z (drawn only). """
    m.cylinder( centre, r, z - h, z, { "side": "iron_black", "bottom": "iron_black", "top": None }, sides=6, turn=math.pi / 6,
                collide=None )


def bolster( m, e, n, z, lo=None, hi=None, half=30.0, depth=8.0, width=6.5, bearing=14.0, rise=4.0 ):
    """ A timber bolster (Sattelholz) on a column's cap at z, under a girder along n: depth deep, as wide as the girder
    (2 x width) and 2 x half long. Its ends are rounded off underneath, from the bearing (bearing either side of the
    column) up into the end face, rise up. An end past lo or hi, where the girder stops, is cut square there. Drawn
    only: the girder's collision covers it, and its top is under the girder. """
    tile = lt_tile( "lt_timber" )
    cut = [ ( bearing + ( half - bearing ) * math.sin( math.radians( a ) ), rise * ( 1 - math.cos( math.radians( a ) ) ) )
            for a in range( 0, 91, 15 ) ]
    right = cut if hi is None or n + half <= hi else [ ( hi - n, 0.0 ) ]
    left = [ ( -x, y ) for x, y in reversed( cut ) ] if lo is None or n - half >= lo else [ ( lo - n, 0.0 ) ]
    # Counter-clockwise seen from +e (n to the right, z up), from the bottom's right end, closed along the bottom.
    outline = right + [ ( right[-1][0], depth ), ( left[0][0], depth ) ] + left
    ends = profile_normals( outline, closed=True )
    run = [ 0.0 ]
    for k in range( len( outline ) ):
        run.append( run[-1] + math.dist( outline[k], outline[( k + 1 ) % len( outline )] ) )
    for k in range( len( outline ) ):
        a, b = outline[k], outline[( k + 1 ) % len( outline )]
        if a[1] == depth and b[1] == depth:
            continue
        na, nb = ends[k]
        pts = [ ( e - width, n + a[0], z + a[1] ), ( e + width, n + a[0], z + a[1] ),
                ( e + width, n + b[0], z + b[1] ), ( e - width, n + b[0], z + b[1] ) ]
        nrm = [ ( 0.0, na[0], na[1] ), ( 0.0, na[0], na[1] ), ( 0.0, nb[0], nb[1] ), ( 0.0, nb[0], nb[1] ) ]
        uv = [ ( -width / tile, run[k] / tile ), ( width / tile, run[k] / tile ),
               ( width / tile, run[k + 1] / tile ), ( -width / tile, run[k + 1] / tile ) ]
        smooth_quad( m, "lt_timber", pts, nrm, uv )
    # Its two sides, in upright strips under each edge of the bottom (the outline isn't convex).
    under = left + right
    for side in ( -1, 1 ):
        for ( xa, ya ), ( xb, yb ) in zip( under, under[1:] ):
            pts = [ ( e + side * width, n + xa, z + ya ), ( e + side * width, n + xb, z + yb ),
                    ( e + side * width, n + xb, z + depth ), ( e + side * width, n + xa, z + depth ) ]
            uv = [ ( ya / tile, ( n + xa ) / tile ), ( yb / tile, ( n + xb ) / tile ),
                   ( depth / tile, ( n + xb ) / tile ), ( depth / tile, ( n + xa ) / tile ) ]
            card( m, "lt_timber", pts, ( side, 0, 0 ), uv=uv )


def girder( m, e, n0, n1, z0, z1, width=6.5, chamfer=1.0, south_end=None ):
    """ A timber girder (Unterzug) along n from n0 to n1 under the joists, its bottom arrises chamfered. Its top is in
    the joists and its ends in the walls, so they aren't drawn, but for a south end standing free: south_end is how
    high it shows (up to whatever rests on it). """
    m.box( ( e - width, n0, z0 + chamfer ), ( e + width, n1, z1 ), { "+e": "lt_timber", "-e": "lt_timber", "default": None } )
    m.box( ( e - width + chamfer, n0, z0 ), ( e + width - chamfer, n1, z0 + chamfer ), { "-z": "lt_timber", "default": None } )
    for side in ( -1, 1 ):
        card( m, "lt_timber", [ ( e + side * width, n0, z0 + chamfer ), ( e + side * width, n1, z0 + chamfer ),
                                ( e + side * ( width - chamfer ), n1, z0 ), ( e + side * ( width - chamfer ), n0, z0 ) ],
              ( side, 0, -1 ) )
    if south_end is not None:
        top = min( south_end, z1 )
        card( m, "lt_timber", [ ( e - width, n0, top ), ( e - width, n0, z0 + chamfer ), ( e - width + chamfer, n0, z0 ),
                                ( e + width - chamfer, n0, z0 ), ( e + width, n0, z0 + chamfer ), ( e + width, n0, top ) ],
              ( 0, -1, 0 ) )
    m.collision_box( ( e - width, n0, z0 ), ( e + width, n1, z1 ), WOOD )


def landing( m, n0, n1, way ):
    """ A steel landing outside a loading bay on the Fleet, and its stair down to the mud, along the wall: northwards
    (way 1) from the landing's north end, or southwards (-1) from its south end. Handrails on the Fleet side. """
    e0, e1 = FLEET - LANDING_W, FLEET
    m.box( ( e0, n0, -8.0 ), ( e1, n1, 0.0 ), { "+z": "lt_grating", "default": "lt_steel" }, METAL )
    for n in ( n0 + 10, n1 - 10 ):
        m.beam( ( e0 + 4, n, -8 ), ( e1, n, -48 ), ( 3.0, 3.0 ), "iron_black" )
    top = n1 if way > 0 else n0
    first, last_nosing, z_last = steel_stair( m, e0, e1, top, way, 0.0, BED_Z )
    back = n0 if way > 0 else n1
    railing( m, ( e0 + 1, back ), ( e0 + 1, first ), 0.0, height=40.0, paint="iron_black", posts=40.0 )
    railing( m, ( e0, back + way * -1 ), ( e1, back + way * -1 ), 0.0, height=40.0, paint="iron_black", posts=40.0 )
    # Its handrail on the stringer's top flange, 38 over the nosings.
    sloped_rail( m, ( e0 + 1, first, 1.5 ), ( e0 + 1, last_nosing, z_last + 1.5 ), height=36.5 )


def steel_stair( m, e0, e1, n_top, way, z_top, z_foot ):
    """ An open steel stair along the Fleet's wall (at e1), from a landing's edge at n_top down to the mud, way 1
    northwards or -1 southwards: two channel stringers and open grating treads, each with a steel nosing, every face
    drawn, so it looks right from under the landing and behind it. The steps are stairs()'s (the first a tread at the
    landing's level) at the 0.6 slope the bays have always had. Its collision is only the ramp along the nosings and
    the stringers' depth under it, so there's headroom under its upper half. Returns the first and last nosings' n and
    the last one's height. """
    rise = z_top - z_foot
    count = max( 1, int( math.ceil( rise / 7.4 ) ) )
    step_z = rise / count
    step_n = rise / 0.6 / count
    slope = step_z / step_n

    def at( u, z, e ):
        return ( e, n_top + way * u, z )

    def nosing( u ):
        """ The line through the nosings (also the walking surface), at u along the stair from n_top. """
        return z_top + step_z - slope * u

    def face( paint, points, outward ):
        normal = np.zeros( 3 )
        pts = [ np.asarray( p, float ) for p in points ]
        for k in range( 1, len( pts ) - 1 ):
            normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
        if np.dot( normal, outward ) < 0:
            pts = pts[::-1]
        m.polygon( paint, pts )

    # The stringers: 10-inch channels (11.7 deep measured plumb at this slope), their top flange 1.5 over the nosings
    # and level over the landing's tread, cut plumb against the landing and level on the mud. The wall's stringer
    # shows no face against the wall.
    over, depth = 1.5, 10.0 * math.sqrt( 1.0 + slope * slope )
    under = depth - over
    foot_z = z_foot - 3.0
    heel = ( nosing( 0.0 ) - under - foot_z ) / slope
    toe = max( count * step_n + 3.0, heel + 4.0 )
    outline = [ ( 0.0, z_top + over ), ( step_n, z_top + over ), ( toe, nosing( toe ) + over ), ( toe, foot_z ),
                ( heel, foot_z ), ( 0.0, nosing( 0.0 ) - under ) ]
    centre_u = sum( u for u, _ in outline ) / len( outline )
    centre_z = sum( z for _, z in outline ) / len( outline )
    for ea, eb, against_wall in ( ( e0, e0 + 3.0, False ), ( e1 - 3.0, e1, True ) ):
        face( "lt_steel", [ at( u, z, ea ) for u, z in outline ], np.array( ( -1.0, 0.0, 0.0 ) ) )
        if not against_wall:
            face( "lt_steel", [ at( u, z, eb ) for u, z in outline ], np.array( ( 1.0, 0.0, 0.0 ) ) )
        for k in range( len( outline ) ):
            ( ua, za ), ( ub, zb ) = outline[k], outline[( k + 1 ) % len( outline )]
            mid_u, mid_z = ( ua + ub ) / 2 - centre_u, ( za + zb ) / 2 - centre_z
            face( "lt_steel", [ at( ua, za, ea ), at( ub, zb, ea ), at( ub, zb, eb ), at( ua, za, eb ) ],
                  np.array( ( 0.0, way * mid_u, mid_z ) ) )

    # The treads: 1.25 bar grating between the stringers, each reaching an inch back under the one above, with a
    # steel nosing bar along its front. Open risers.
    ta, tb, thick, bar = e0 + 3.0, e1 - 3.0, 1.25, 1.5
    for k in range( count ):
        top = z_top - step_z * k
        front = ( k + 1 ) * step_n
        back = k * step_n - ( 1.0 if k else 0.0 )
        for u0, u1, paint in ( ( back, front - bar, "lt_grating" ), ( front - bar, front, "lt_steel" ) ):
            na, nb = n_top + way * u0, n_top + way * u1
            m.box( ( ta, min( na, nb ), top - thick ), ( tb, max( na, nb ), top ),
                   { "+z": paint, "-z": paint, "default": "lt_steel", "+e": None, "-e": None } )

    # Collision: the ramp, from the landing's tread down the nosings to the mud, about as deep as the stringers.
    end = ( count + 1 ) * step_n
    profile = [ ( 0.0, z_top ), ( step_n, z_top ), ( end, z_foot ), ( end, z_foot - 4.0 ),
                ( 0.0, nosing( 0.0 ) - under ) ]
    m.hull( [ at( u, z, e ) for e in ( e0, e1 ) for u, z in profile ], METAL )
    return n_top + way * step_n, n_top + way * count * step_n, z_foot + step_z


def turret( m, style, centre, z0, z1, radius=46.0, sides=14 ):
    """ The round corner turret over the bridge: corbelled out of the corner, with arched slit windows, a crown of
    glazed brick and a tall copper spire. Drawn only (it's well over everyone's head). """
    c = np.asarray( centre, float )
    ring = lambda r, z: [ np.array( ( c[0] + r * math.cos( 2 * math.pi * k / sides ), c[1] + r * math.sin( 2 * math.pi * k / sides ), z ) )
                          for k in range( sides ) ]
    # The corbelling: courses stepping out from the corner.
    for k in range( 6 ):
        r = radius * ( 0.3 + 0.7 * k / 5 )
        zb, zt = z0 - 90 + k * 15, z0 - 75 + k * 15
        m.cylinder( c, r, zb, zt, { "side": style.band if k % 2 else style.brick, "bottom": style.brick, "top": None }, sides=sides )
    m.cylinder( c, radius, z0, z1, { "side": style.brick, "top": None, "bottom": style.brick }, sides=sides )
    for k in range( 0, sides, 2 ):
        t = 2 * math.pi * ( k + 0.5 ) / sides
        for z in ( z0 + 120, z0 + 300 ):
            out = np.array( ( math.cos( t ), math.sin( t ), 0.0 ) )
            side = np.array( ( -math.sin( t ), math.cos( t ), 0.0 ) )
            p = np.append( c + out[:2] * ( radius + 0.4 ), 0.0 )
            pts = [ p + ( 0, 0, z ) + side * -7, p + ( 0, 0, z ) + side * 7 ]
            pts += [ p + ( 0, 0, z + 70 ) + side * 7 * math.cos( a ) + np.array( ( 0, 0, 7 * math.sin( a ) ) ) for a in np.linspace( 0, math.pi, 7 ) ]
            card( m, "rw_window_dark", pts, out )
    m.cylinder( c, radius + 5, z1 - 30, z1 - 18, { "side": style.band, "bottom": style.band, "top": None }, sides=sides )
    m.cylinder( c, radius + 3, z1 - 18, z1, { "side": style.brick, "top": "lt_brick_glazed", "bottom": None }, sides=sides )
    spire( m, c, z1, radius + 4, 330.0, "copper", sides=sides )


# ---------------------------------------------------------------------------------------------------------------------
# The rest of the east half: the Fleet's wall, the ground, the yard, the blocks round the play, the quay

EDGE_E = 2700.0                 # how far east the half is built (the play stops at 2200)
SQUARE = ( 1300.0, 2200.0, -600.0, 600.0 )
CROSS = ( 1000.0, 1300.0 )
YARD_SHED = ( 300.0, 620.0, -980.0, -700.0 )
QUAY_SHED = ( 1300.0, 1950.0, -1050.0, -600.0 )
NORTH_ROW_N = 3400.0            # the north row's blocks reach back this far (up the Fleet)
QUAY_STAIR = ( -1050.0, -1010.0 )
FOOTBRIDGE = ( -1300.0, -1180.0 )
BLOCK_LEVELS = ( 200.0, 350.0, 500.0, 650.0 )


def facade( m, wall, style, eaves, bays, levels=BLOCK_LEVELS, columns=(), doors=(), gable=None, gable_steps=5,
            pilaster_every=3, base=0.0, end=True, door_w=64.0, door_h=132.0, corners=( None, None ) ):
    """ A blind front (nobody goes in): shut doors and dark windows on the ground storey, windows up the storeys from
    levels, loading columns (shut doors to the top storey, an oriel over that), string courses, pilasters, the
    cornice, and a stepped gable over gable ( r0, r1 ). The wall itself is drawn only: its block has a box. corners
    are its ends' outside corners (corner_reach). """
    for r in bays:
        if r in columns:
            wall.add( r, 90.0, base, base + 150.0, "shut" )
        elif r in doors:
            wall.add( r, door_w, base, base + door_h, "shut" )
        else:
            wall.add( r, 48.0, base + 66.0, base + 166.0, "glass_arch" )
    upper_storeys( wall, bays, levels, columns=columns )
    wall.build( m, style.brick, None, style.brick, style.brick if end else None, None )
    dress( m, wall, style )
    courses( m, wall, style, levels, corners=corners )
    cornice( m, wall, style, eaves, corners=corners )
    if pilaster_every and len( bays ) > 1:
        pitch = bays[1] - bays[0]
        for k in range( pilaster_every, len( bays ), pilaster_every ):
            r = bays[k] - pitch / 2
            if all( abs( r - c ) > 60 for c in columns ):
                pilasters( m, wall, style, ( r, ), base + 44, eaves - 36 )
    for r in columns:
        oriel( m, wall, style, r, levels[-1] + 10, levels[-1] + 128 )
    if gable:
        stepped_gable( m, wall, style, gable[0], gable[1], eaves + 46, steps=gable_steps, step_h=56.0 )


def bays_along( r0, r1, pitch=120.0, margin=70.0 ):
    count = max( 1, int( ( r1 - r0 - 2 * margin ) // pitch ) + 1 )
    start = ( r0 + r1 ) / 2 - pitch * ( count - 1 ) / 2
    return [ start + pitch * k for k in range( count ) ]


def block( m, e0, e1, n0, n1, eaves, faces, style, z0=0.0, roof_along="n" ):
    """ A block nobody goes into: one collision box, its fronts on the faces listed ( face: dict of facade()'s
    arguments, with 'run' to draw only part of it ), and a roof. """
    m.collision_box( ( e0, n0, z0 - 10 ), ( e1, n1, eaves + 40 ), STONE )
    # Each front's run. The side fronts (+-e) run inside the end fronts' thickness where there are any, so the corners
    # aren't drawn twice.
    ends = any( f in faces for f in ( "+n", "-n" ) )
    runs = { face: tuple( kw.get( "run", ( e0, e1 ) if face in ( "+n", "-n" ) else ( n0 + T, n1 - T ) if ends else ( n0, n1 ) ) )
             for face, kw in faces.items() }

    def meet( end_face, side_face ):
        """ Whether an end front and a side front both reach the corner between them. """
        if end_face not in runs or side_face not in runs:
            return False
        e_end = runs[end_face][0 if side_face == "-e" else 1]
        n_side = runs[side_face][0 if end_face == "-n" else 1]
        return abs( e_end - ( e0 if side_face == "-e" else e1 ) ) < 0.01 and \
            abs( n_side - ( n0 + T if end_face == "-n" else n1 - T ) ) < 0.01

    for face, kw in faces.items():
        kw = dict( kw )
        kw.pop( "run", None )
        run = runs[face]
        if face in ( "+n", "-n" ):
            across = ( n1 - T, n1 ) if face == "+n" else ( n0, n0 + T )
            wall = Wall( "e", run, across, ( z0, eaves + 40 ), face )
            corners = tuple( 0.0 if meet( face, side ) else None for side in ( "-e", "+e" ) )
        else:
            across = ( e1 - T, e1 ) if face == "+e" else ( e0, e0 + T )
            wall = Wall( "n", run, across, ( z0, eaves + 40 ), face )
            corners = tuple( T if meet( end, face ) else None for end in ( "-n", "+n" ) )
        bays = kw.pop( "bays", None ) or bays_along( *run )
        facade( m, wall, style, eaves, bays, corners=corners, **kw )
    return roof( m, e0, e1, n0, n1, eaves + 40, along=roof_along, pitch=0.75 )


def fleet_wall( m, style, n0, n1 ):
    """ The Fleet's wall under the quay, its face at e 240 from below the mud to the quay: brick, slimed green under the
    tide line, a dark line where the tide stands longest. """
    card( m, style.brick, [ ( FLEET, n0, -54 ), ( FLEET, n1, -54 ), ( FLEET, n1, 0 ), ( FLEET, n0, 0 ) ], ( -1, 0, 0 ) )
    card( m, "lt_brick_slime", [ ( FLEET, n0, BED_Z - 12 ), ( FLEET, n1, BED_Z - 12 ), ( FLEET, n1, -58 ), ( FLEET, n0, -58 ) ],
          ( -1, 0, 0 ) )
    m.box( ( FLEET - 0.6, n0, -60 ), ( FLEET, n1, -54 ), { "-e": "lt_brick_glazed", "default": None } )


def quay_ladder( m, n ):
    """ An iron ladder up the Fleet's wall, from the mud to the coping (there's no climbing in the game: it's dressing). """
    e = FLEET - 5
    for side in ( -8, 8 ):
        m.box( ( e - 1, n + side - 1, BED_Z - 4 ), ( e + 1, n + side + 1, 18 ), "iron_black" )
    z = BED_Z + 8
    while z < 0:
        m.box( ( e - 1, n - 8, z - 0.6 ), ( e + 1, n + 8, z + 0.6 ), "iron_black" )
        z += 12
    for side in ( -8, 8 ):
        m.box( ( e, n + side - 1, -6 ), ( FLEET + 4, n + side + 1, -3 ), "iron_black" )


def ground( m, rects ):
    for e0, e1, n0, n1, paint in rects:
        m.polygon( paint, [ ( e0, n0, 0 ), ( e1, n0, 0 ), ( e1, n1, 0 ), ( e0, n1, 0 ) ] )


def pavement( m, e0, e1, n0, n1, kerbs ):
    """ A pavement 5 up, granite kerbs on the sides listed and concrete closing its back and ends. """
    m.box( ( e0, n0, -6 ), ( e1, n1, 5 ),
           { "+z": "rw_paving", "-z": None, "default": "rw_concrete", **{ k: "ashlar_grey" for k in kerbs } }, STONE )


ALLEY_WALL = ( QUAY_SHED[1], SQUARE[1], -1050.0, -1050.0 + T, 132.0 )   # e0, e1, n0, n1, height


def alley_wall( m, style ):
    """ The brick wall across the alley's quay end, between the quay shed and the block east of the alley, with a shut
    pair of gates, a granite plinth on both faces and a granite coping. One collision box: the gate has none of its own. """
    e0, e1, n0, n1, height = ALLEY_WALL
    gate = ( ( e0 + e1 ) / 2, 100.0, 0.0, 112.0 )
    wall = Wall( "e", ( e0, e1 ), ( n0, n1 ), ( 0.0, height ), "-n" )
    wall.add( *gate, kind="shut" )
    wall.build( m, style.brick, style.brick, style.brick, None, None )
    dress( m, wall, style )
    courses( m, wall, style, () )
    inner = Wall( "e", ( e0, e1 ), ( n0, n1 ), ( 0.0, height ), "+n" )
    inner.add( *gate, kind="shut" )
    courses( m, inner, style, () )
    m.box( ( e0, n0 - 2, height ), ( e1, n1 + 2, height + 6 ), { "+z": style.stone, "-n": style.stone, "+n": style.stone,
                                                                 "-z": style.stone, "default": None } )
    m.collision_box( ( e0, n0, -10.0 ), ( e1, n1, height + 6 ), STONE )


def half():
    """ The east half (the west is its mirror): everything east of the Fleet's wall. """
    m, glass = Model(), Model()
    style = EAST
    # The ground: one slab under it all, its top painted by area. The Fleet's wall is its west face.
    m.collision_box( ( FLEET, QUAY_N, BED_Z - 60 ), ( EDGE_E + 300, STREET_N[1] + 10, 0.0 ), STONE )
    ground( m, [
        ( FLEET + 22, EDGE_E, QUAY_N, -1050.0, "setts" ),                    # the quay
        ( FLEET + 22, CROSS[0], -1050.0, SPEICHER[2], "rw_concrete_dark" ),  # the yard
        ( CROSS[0], CROSS[1], -1050.0, STREET_N[0], "setts" ),              # the cross street
        ( SQUARE[0], SQUARE[1], SQUARE[2], SQUARE[3], "setts" ),             # the square
        ( QUAY_SHED[1], SQUARE[1], -1050.0, SQUARE[2], "setts" ),           # the alley beside the quay shed
        ( FLEET, EDGE_E, STREET_N[0] + 50, STREET_N[1] - 50, "setts" ),       # the street
        ( FLEET + T, SPEICHER[1] - T, SPEICHER[2] + T, SPEICHER[3] - T, "rw_concrete" ),
    ] )
    pavement( m, FLEET, EDGE_E, STREET_N[0], STREET_N[0] + 50, ( "+n", ) )
    pavement( m, FLEET, EDGE_E, STREET_N[1] - 50, STREET_N[1], ( "-n", ) )
    # The coping along the yard's and the quay's edge, a little proud of the wall.
    m.box( ( FLEET - 2, QUAY_N, -8 ), ( FLEET + 22, SPEICHER[2], 0.0 ), { "-e": "ashlar_grey", "+z": "ashlar_grey",
                                                                          "-z": "ashlar_grey", "-n": "ashlar_grey",
                                                                          "default": None } )
    fleet_wall( m, style, QUAY_N, STREET_N[1] )
    for n in ( -1450.0, -560.0, 1020.0 ):
        quay_ladder( m, n )
    # The harbour quay's edge: its wall down into the harbour, the granite edge, and the fender piles.
    card( m, "ashlar_grey", [ ( FLEET, QUAY_N, -30 ), ( EDGE_E, QUAY_N, -30 ), ( EDGE_E, QUAY_N, 0 ), ( FLEET, QUAY_N, 0 ) ], ( 0, -1, 0 ) )
    card( m, style.brick, [ ( FLEET, QUAY_N, -60 ), ( EDGE_E, QUAY_N, -60 ), ( EDGE_E, QUAY_N, -30 ), ( FLEET, QUAY_N, -30 ) ], ( 0, -1, 0 ) )
    card( m, "lt_brick_slime", [ ( FLEET, QUAY_N, HARBOUR_Z - 60 ), ( EDGE_E, QUAY_N, HARBOUR_Z - 60 ), ( EDGE_E, QUAY_N, -60 ),
                                 ( FLEET, QUAY_N, -60 ) ], ( 0, -1, 0 ) )
    for e in np.arange( FLEET + 110, EDGE_E, 220 ):
        m.cylinder( ( e, QUAY_N - 8 ), 7.5, HARBOUR_Z - 40, -4, { "side": "lt_timber", "top": "lt_timber", "bottom": None }, sides=8 )

    speicher( m, glass, style )

    # Railings along the Fleet's edge south of the warehouse, open at the footbridge and the quay's stair.
    for a, b in ( ( QUAY_N + 10, FOOTBRIDGE[0] ), ( FOOTBRIDGE[1], QUAY_STAIR[0] ), ( QUAY_STAIR[1], SPEICHER[2] ) ):
        railing( m, ( FLEET + 3, a ), ( FLEET + 3, b ), 0.0, height=40.0 )
    landing( m, QUAY_STAIR[0], QUAY_STAIR[1], 1 )

    # The yard's shed: a low brick store with a slate roof.
    e0, e1, n0, n1 = YARD_SHED
    block( m, e0, e1, n0, n1, 196.0, {
        "+e": dict( bays=[ -900.0, -780.0 ], doors=( -780.0, ), levels=(), pilaster_every=0 ),
        "-n": dict( bays=[ 380.0, 540.0 ], levels=(), pilaster_every=0 ),
        "+n": dict( bays=[ 380.0, 540.0 ], doors=( 540.0, ), levels=(), pilaster_every=0 ),
        "-e": dict( bays=[ -900.0, -780.0 ], levels=(), pilaster_every=0 ),
    }, style, roof_along="e" )

    # The quay shed between the square and the quay: big sliding doors to both, high windows.
    e0, e1, n0, n1 = QUAY_SHED
    block( m, e0, e1, n0, n1, 236.0, {
        "+n": dict( bays=bays_along( e0, e1, 150 ), doors=tuple( bays_along( e0, e1, 150 )[1::2] ), levels=(), pilaster_every=2,
                    door_w=120.0, door_h=170.0 ),
        "-n": dict( bays=bays_along( e0, e1, 150 ), doors=tuple( bays_along( e0, e1, 150 )[::2] ), levels=(),
                    pilaster_every=2, door_w=120.0, door_h=170.0 ),
        "-e": dict( bays=bays_along( n0, n1, 140 ), levels=(), pilaster_every=0 ),
        "+e": dict( bays=bays_along( n0, n1, 140 ), levels=(), pilaster_every=0 ),
    }, style, roof_along="e" )

    # The blocks round the play: north of the square (offices over the cross street and the north street), east of the
    # square and the alley, and the north row across the street, whose back runs up the Fleet.
    block( m, SQUARE[0], EDGE_E, SQUARE[3], STREET_N[0], 760.0, {
        "-n": dict( run=( SQUARE[0], SQUARE[1] ), doors=( bays_along( SQUARE[0], SQUARE[1] )[2], ),
                    columns=( bays_along( SQUARE[0], SQUARE[1] )[5], ) ),
        "-e": dict( run=( SQUARE[3] + T, STREET_N[0] - T ), doors=( bays_along( SQUARE[3] + T, STREET_N[0] - T )[1], ) ),
        "+n": dict( columns=( bays_along( SQUARE[0], EDGE_E )[3], ), gable=( SQUARE[0], SQUARE[0] + 560 ),
                    doors=( bays_along( SQUARE[0], EDGE_E )[7], ) ),
    }, style )
    block( m, SQUARE[1], EDGE_E, -1050.0, SQUARE[3], 860.0, {
        "-e": dict( columns=( bays_along( -1050.0, SQUARE[3] )[4], ), gable=( -300.0, 300.0 ),
                    doors=( bays_along( -1050.0, SQUARE[3] )[1], bays_along( -1050.0, SQUARE[3] )[10] ),
                    levels=( 200.0, 350.0, 500.0, 650.0 ) ),
    }, style, roof_along="n" )
    # The alley beside the quay shed is closed from the quay by a yard wall with a shut gate: the way from the spawn
    # square to the quay is the cross street. Too high to mantle, and a player clip over it stops a boost.
    alley_wall( m, style )
    north_row( m, style )
    # Closing the street's and the quay's views east of the play.
    block( m, EDGE_E, EDGE_E + 300, STREET_N[0] - 60, STREET_N[1] + 60, 700.0, {
        "-e": dict( run=( STREET_N[0], STREET_N[1] ), bays=[ 1230.0, 1370.0 ], doors=( 1230.0, ) ) }, style, roof_along="e" )
    block( m, EDGE_E, EDGE_E + 600, QUAY_N, -1050.0, 420.0, {
        "-e": dict( bays=bays_along( QUAY_N, -1050.0, 140 ), doors=( bays_along( QUAY_N, -1050.0, 140 )[1], ),
                    levels=( 200.0, ) ) }, style, roof_along="e" )
    return m, glass


def north_row( m, style ):
    """ The warehouses across the north street, three of them side by side, each its own height, and their backs on the
    Fleet as it runs on north (drawn for the backdrop; nobody gets there). """
    n0 = STREET_N[1]
    m.collision_box( ( FLEET, n0, BED_Z - 20 ), ( EDGE_E, NORTH_ROW_N, 960.0 ), STONE )
    for e0, e1, eaves, gable, columns in ( ( FLEET, 1020.0, 900.0, True, 1 ), ( 1020.0, 1900.0, 820.0, False, 3 ),
                                          ( 1900.0, EDGE_E, 880.0, True, 2 ) ):
        wall = Wall( "e", ( e0, e1 ), ( n0, n0 + T ), ( 0.0, eaves + 40 ), "-n" )
        bays = bays_along( e0, e1 )
        facade( m, wall, style, eaves, bays, columns=( bays[columns], ), doors=( bays[columns + 2 if columns + 2 < len( bays ) else 0], ),
                gable=( ( e0 + e1 ) / 2 - 300, ( e0 + e1 ) / 2 + 300 ) if gable else None )
        roof( m, e0, e1, n0, n0 + 700, eaves + 40, along="e", pitch=0.75 )
    # The back on the Fleet, from the mud up: loading columns with oriels every few bays.
    wall = Wall( "n", ( n0 + T, NORTH_ROW_N ), ( FLEET, FLEET + T ), ( BED_Z - 12, 940.0 ), "-e" )
    bays = bays_along( n0 + T, NORTH_ROW_N, 125 )
    columns = tuple( bays[2::4] )
    for r in bays:
        if r in columns:
            wall.add( r, 80.0, 0.0, 112.0, "shut" )
        else:
            wall.add( r, 44.0, 64.0, 150.0, "glass_arch" )
    upper_storeys( wall, bays, ( FLOOR1, CEILING, 502.0, 652.0 ), columns=columns )
    wall.build( m, style.brick, None, style.brick, None, None )
    dress( m, wall, style )
    courses( m, wall, style, ( FLOOR1, CEILING, 502.0, 652.0 ), skip=( "plinth", ) )
    cornice( m, wall, style, 900.0 )
    for r in columns:
        oriel( m, wall, style, r, 662.0, 780.0 )
    card( m, "lt_brick_slime", [ ( FLEET - 0.3, n0, BED_Z - 12 ), ( FLEET - 0.3, NORTH_ROW_N, BED_Z - 12 ),
                                 ( FLEET - 0.3, NORTH_ROW_N, -58 ), ( FLEET - 0.3, n0, -58 ) ], ( -1, 0, 0 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The Fleet: its bed, the bridges, the barge on the mud

MOUTH_N = -1500.0              # south of here the bed falls away into the harbour
BARGE = ( -112.0, 38.0, 170.0, 750.0 )     # e0, e1, n0, n1 of the barge (an open lighter, a Schute) on the mud
STEPS_E = tuple( -e for e, _ in BED_PROFILE[:0:-1] ) + tuple( e for e, _ in BED_PROFILE[1:] )


def fall( n ):
    """ How far the bed has fallen at n, towards the harbour: none north of MOUTH_N, 14 by the play's edge, 44 beyond. """
    n = np.asarray( n, float )
    near = np.clip( ( MOUTH_N - n ) / 150.0, 0.0, 1.0 ) * 14.0
    far = np.clip( ( PLAY[2] - n ) * 0.12, 0.0, 30.0 )
    return -( near + far )


def mud_noise( e, n ):
    """ The mud's unevenness: none against the walls, a couple of inches out on the flats. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    shape = ( 1.1 * np.sin( e * 0.031 + n * 0.0071 ) * np.sin( n * 0.0123 - e * 0.017 )
              + 0.6 * np.sin( n * 0.043 + e * 0.052 ) + 0.4 * np.sin( n * 0.0021 + 1.7 ) )
    envelope = np.clip( ( FLEET - 4 - np.abs( e ) ) / 30.0, 0.0, 1.0 )
    return shape * envelope


def mud_z( e, n ):
    return bed_z( e ) + fall( n ) + mud_noise( e, n )


def mud( m, n0, n1, step_e=12.0, step_n=40.0, collide=True ):
    """ The Fleet's bed from n0 to n1: drawn as a smooth grid over its profile, wetter towards the channel; its
    collision a hull per piece of the profile (the drawn mud is within 2 of it). """
    es = np.arange( -FLEET, FLEET + 0.1, step_e )
    ns = np.arange( n0, n1 + 0.1, step_n )
    E, N = np.meshgrid( es, ns, indexing="ij" )
    Z = mud_z( E, N )
    dz_de = np.gradient( Z, step_e, axis=0 )
    dz_dn = np.gradient( Z, step_n, axis=1 )
    normals = np.stack( ( -dz_de, -dz_dn, np.ones_like( Z ) ), -1 )
    normals /= np.linalg.norm( normals, axis=-1, keepdims=True )
    for i in range( len( es ) - 1 ):
        for j in range( len( ns ) - 1 ):
            corners = [ ( i, j ), ( i + 1, j ), ( i + 1, j + 1 ), ( i, j + 1 ) ]
            pts = [ ( E[a, b], N[a, b], Z[a, b] ) for a, b in corners ]
            centre = abs( ( es[i] + es[i + 1] ) / 2 )
            wet = centre < 135 or ( centre < 175 and chance( 0.35, "wet", i, j ) )
            m.polygon( "lt_mud_wet" if wet else "lt_mud", pts, normal=( 0, 0, 1 ), normals=[ normals[a, b] for a, b in corners ] )
    if collide:
        n0 = max( n0, PLAY[2] - 20 )                 # the drawn mud runs on into the harbour, the collision doesn't
        for ea, eb in zip( STEPS_E, STEPS_E[1:] ):
            za, zb = float( bed_z( ea ) ), float( bed_z( eb ) )
            for na, nb in ( ( max( n0, MOUTH_N ), n1 ), ( n0, MOUTH_N ) ):
                if nb <= na:
                    continue
                fa, fb = float( fall( na ) ), float( fall( nb ) )
                pts = [ ( ea, na, za + fa ), ( eb, na, zb + fa ), ( ea, nb, za + fb ), ( eb, nb, zb + fb ) ]
                pts += [ ( p[0], p[1], -300.0 ) for p in pts ]
                m.hull( pts, DIRT )


def puddles( m, n0, n1, count, seed ):
    """ Small pools left on the mud flats, between the channel and the walls. """
    rng = np.random.default_rng( seed )
    for _ in range( count ):
        side = rng.choice( ( -1.0, 1.0 ) )
        e = side * rng.uniform( 150.0, 222.0 )
        n = rng.uniform( n0, n1 )
        radius = rng.uniform( 8.0, 26.0 )
        z = float( mud_z( e, n ) ) + 0.35
        ring = []
        for k in range( 10 ):
            t = 2 * math.pi * k / 10
            r = radius * ( 0.7 + 0.3 * rng.random() )
            ring.append( ( e + r * math.cos( t ) * 1.4, n + r * math.sin( t ), z ) )
        m.polygon( "lt_water", ring, normal=( 0, 0, 1 ) )


def street_bridge( m, n0, n1, collide=True ):
    """ The north street's bridge: a steel deck on cross girders between two riveted plate girders, which are its
    parapets, with a cast-iron lattice railing along their tops and a lamp on each end post. Paved like the street. """
    surface = STONE if collide else None
    metal = METAL if collide else None
    m.polygon( "setts", [ ( -FLEET, n0 + 50, 0 ), ( FLEET, n0 + 50, 0 ), ( FLEET, n1 - 50, 0 ), ( -FLEET, n1 - 50, 0 ) ] )
    for a, b, kerb in ( ( n0 + 18, n0 + 50, "+n" ), ( n1 - 50, n1 - 18, "-n" ) ):
        m.box( ( -FLEET, a, -6 ), ( FLEET, b, 5 ), { "+z": "rw_paving", kerb: "ashlar_grey", "default": None }, surface )
    m.box( ( -FLEET, n0 + 18, -30 ), ( FLEET, n1 - 18, 0 ), { "-z": "lt_steel", "default": None }, surface )
    for e in np.arange( -FLEET + 24, FLEET - 10, 48 ):
        m.box( ( e - 3, n0 + 18, -42 ), ( e + 3, n1 - 18, -30 ), "iron_green" )
    for a, b in ( ( n0, n0 + 18 ), ( n1 - 18, n1 ) ):
        m.box( ( -FLEET, a, -44 ), ( FLEET, b, 12 ), "iron_green", metal )
        out = -1 if a == n0 else 1
        face = a if out < 0 else b
        # Rivet rows and stiffeners on the girder's outer face.
        for e in np.arange( -FLEET + 30, FLEET - 20, 30 ):
            m.box( ( e - 1.5, min( face, face + out * 1.2 ), -42 ), ( e + 1.5, max( face, face + out * 1.2 ), 10 ), "iron_green" )
        for z in ( -38.0, 6.0 ):
            m.box( ( -FLEET, min( face, face + out * 0.8 ), z - 1 ), ( FLEET, max( face, face + out * 0.8 ), z + 1 ), "iron_green" )
        railing( m, ( -FLEET + 8, ( a + b ) / 2 ), ( FLEET - 8, ( a + b ) / 2 ), 12.0, height=32.0, paint="iron_green",
                 posts=48.0, surface=metal, lattice=True )
        for e in ( -FLEET, FLEET ):
            m.box( ( e - 8, a - 2, -44 ), ( e + 8, b + 2, 52 ), "iron_green", metal )
            m.box( ( e - 10, a - 4, 52 ), ( e + 10, b + 4, 58 ), "iron_green" )
            bridge_lamp( m, e, ( a + b ) / 2, 58.0 )


def bridge_lamp( m, e, n, z0 ):
    """Glazed cast-iron lantern; its matching point light is supplied by lights()."""
    return LANTERNS.build( m, e, n, z0 )


def footbridge( m ):
    """ The footbridge over the Fleet's mouth: a timber deck between two Warren trusses of painted steel. """
    n0, n1 = FOOTBRIDGE
    first_steel = len( m.polygons["lt_steel"] )
    m.box( ( -FLEET, n0 + 6, -14 ), ( FLEET, n1 - 6, 0 ), { "+z": None, "-z": "lt_steel", "default": "lt_steel" }, WOOD )
    DECK.deck_surface( m, -FLEET, FLEET, n0 + 6, n1 - 6 )
    m.grain_paints.add( "planks" )
    # Its sides are Warren trusses at handrail height (a pony truss), so the view over the Fleet stays open.
    for a, b in ( ( n0, n0 + 6 ), ( n1 - 6, n1 ) ):
        m.box( ( -FLEET, a, -18 ), ( FLEET, b, -2 ), "lt_steel" )
        m.box( ( -FLEET, a - 0.5, 38 ), ( FLEET, b + 0.5, 43 ), "lt_steel" )
        panels = 16
        width = 2 * FLEET / panels
        for k in range( panels + 1 ):
            e = -FLEET + width * k
            m.box( ( e - 1.5, a + 0.5, -2 ), ( e + 1.5, b - 0.5, 38 ), "lt_steel" )
        for k in range( panels ):
            e = -FLEET + width * k
            p, q = ( e, ( a + b ) / 2, -2 ), ( e + width, ( a + b ) / 2, 38 )
            if k % 2:
                p, q = ( e, ( a + b ) / 2, 38 ), ( e + width, ( a + b ) / 2, -2 )
            m.beam( p, q, ( 2.5, 3.0 ), "lt_steel", up=( 0, 1, 0 ) )
        for e in np.arange( -FLEET + 15, FLEET, 30 ):
            m.box( ( e - 0.4, a + 2, 2 ), ( e + 0.4, b - 2, 37 ), "lt_steel" )      # the mesh's uprights inside it
        m.collision_box( ( -FLEET, a, 0 ), ( FLEET, b, 43 ), METAL )
    RAILS.finish_bridge( m, first_steel )


def barge( m ):
    """ An old steel lighter left lying on the mud: raked ends, an open hold of rusted plate with some cargo left in
    it, rubbing strakes and bitts. Its sides are 70-82 over the mud and 70 over its hold's floor, so you can mantle in
    and out. The hold's floor is over the channel's water, which runs on under the hull: level with it, they fought. """
    e0, e1, n0, n1 = BARGE
    zb, zt, t, rake = -143.0, -64.0, 3.0, 40.0
    waterline = -112.0
    for e, out in ( ( e0, -1.0 ), ( e1, 1.0 ) ):
        inner = e - out * t
        for z0, z1, paint in ( ( zb, waterline, "lt_hull_red" ), ( waterline, zt, "lt_hull_black" ) ):
            f0, f1 = ( z0 - zb ) / ( zt - zb ), ( z1 - zb ) / ( zt - zb )
            pts = [ ( e, n0 + rake * ( 1 - f0 ), z0 ), ( e, n1 - rake * ( 1 - f0 ), z0 ), ( e, n1 - rake * ( 1 - f1 ), z1 ),
                    ( e, n0 + rake * ( 1 - f1 ), z1 ) ]
            card( m, paint, pts, ( out, 0, 0 ) )
        pts = [ ( inner, n0 + rake, zb ), ( inner, n1 - rake, zb ), ( inner, n1, zt ), ( inner, n0, zt ) ]
        card( m, "lt_hold_rust", pts, ( -out, 0, 0 ) )
        lo, hi = sorted( ( e, inner ) )
        m.box( ( lo - ( 1.5 if out < 0 else 0 ), n0 - 1, zt - 4 ), ( hi + ( 1.5 if out > 0 else 0 ), n1 + 1, zt ), "lt_hull_black" )
        m.box( ( min( e, e + out * 2 ), n0 + 30, -96 ), ( max( e, e + out * 2 ), n1 - 30, -91 ), "lt_hull_black" )
        m.hull( [ ( x, n, z ) for x in ( lo, hi ) for n, z in ( ( n0 + rake, zb ), ( n1 - rake, zb ), ( n1, zt ), ( n0, zt ) ) ], METAL )
    for n_out, n_in, sign in ( ( n0, n0 + rake, -1.0 ), ( n1, n1 - rake, 1.0 ) ):
        pts = [ ( e0, n_in, zb ), ( e1, n_in, zb ), ( e1, n_out, zt ), ( e0, n_out, zt ) ]
        card( m, "lt_hull_black", pts, ( 0, sign * ( zt - zb ), rake ) )
        pts = [ ( e0 + t, n_in - sign * t, zb + t ), ( e1 - t, n_in - sign * t, zb + t ), ( e1 - t, n_out - sign * t, zt ), ( e0 + t, n_out - sign * t, zt ) ]
        card( m, "lt_hold_rust", pts, ( 0, -sign * ( zt - zb ), -rake ) )
        m.hull( [ ( e, n, z ) for e in ( e0, e1 ) for n, z in ( ( n_in, zb ), ( n_out, zt ), ( n_in - sign * t, zb ), ( n_out - sign * t, zt ) ) ],
                METAL )
        m.box( ( e0, min( n_out, n_out - sign * 4 ), zt - 4 ), ( e1, max( n_out, n_out - sign * 4 ), zt ), "lt_hull_black" )
        # A pair of bitts on the end's deck.
        for e in ( e0 + 30, e1 - 30 ):
            m.cylinder( ( e, n_out - sign * 14 ), 3.5, zt - 4, zt + 9, "iron_black", sides=8 )
    floor = WATER_Z + 3
    m.box( ( e0 + t, n0 + rake, zb ), ( e1 - t, n1 - rake, floor ), { "+z": "lt_hold_rust", "default": None }, METAL )
    # Left in the hold: a few sacks under a tarpaulin, and timber.
    sacks( m, e0 + 40, n1 - 140, floor, rows=2, cols=2, layers=2, along="n" )
    for k, ( e, n ) in enumerate( ( ( e1 - 30, n0 + 120 ), ( e1 - 40, n0 + 150 ) ) ):
        m.box( ( e - 5, n - 60, floor ), ( e + 5, n + 60, floor + 10 ), "lt_timber", WOOD )


def sacks( m, e, n, z0, rows=2, cols=3, layers=3, along="e", pallet=True ):
    """ Filled jute sacks stacked on a pallet, laid in alternating courses. """
    sw, sl, sh = 22.0, 34.0, 11.0
    if pallet:
        width, depth = cols * sw if along == "e" else rows * sl, rows * sl if along == "e" else cols * sw
        PALLETS.build( m, ( e - 2, n - 2, z0 ), ( width + 4, depth + 4, 5.5 ) )
        z0 += 5.5
    for layer in range( layers ):
        flip = layer % 2
        for i in range( cols ):
            for j in range( rows ):
                if along == "e":
                    a = ( e + i * sw + ( 1 if flip else 0 ), n + j * sl )
                    size = ( sw - 1, sl - 1 )
                else:
                    a = ( e + j * sl, n + i * sw + ( 1 if flip else 0 ) )
                    size = ( sl - 1, sw - 1 )
                z = z0 + layer * sh
                SACKS.sack( m, ( a[0], a[1], z ), ( size[0], size[1], sh ) )
    if along == "e":
        lo, hi = ( e, n, z0 - 5.5 ), ( e + cols * sw, n + rows * sl, z0 + layers * sh )
    else:
        lo, hi = ( e, n, z0 - 5.5 ), ( e + rows * sl, n + cols * sw, z0 + layers * sh )
    m.collision_box( lo, hi, WOOD )
    return hi


def piles( m, e, n, top=-8.0 ):
    """ A dolphin (Dalben): three tarred timber piles driven into the mud, bound with an iron band. """
    for k in range( 3 ):
        t = 2 * math.pi * k / 3 + 0.4
        c = ( e + 8 * math.cos( t ), n + 8 * math.sin( t ) )
        m.cylinder( c, 6.5, BED_Z - 20, top - k * 3, { "side": "lt_timber", "top": "lt_timber", "bottom": None }, sides=8 )
    m.cylinder( ( e, n ), 15.5, top - 24, top - 20, { "side": "iron_black", "top": "iron_black", "bottom": "iron_black" }, sides=10 )
    m.collision_box( ( e - 15, n - 15, BED_Z - 20 ), ( e + 15, n + 15, top ), WOOD )


def tyre( m, e, n, z, r=14.0, w=8.0 ):
    m.cylinder( ( e, n ), r, z, z + w, { "side": "lt_rubber", "top": "lt_rubber", "bottom": None }, sides=12 )
    m.cylinder( ( e, n ), r * 0.55, z + w + 0.05, z + w + 0.1, { "top": "rw_black", "side": None, "bottom": None }, sides=10 )


# Along each wall: clear of the ladders (-1450, -560, 1020), the footbridge, the quay stair and the bays' landings.
MOORING_RINGS = ( -1520, -1370, -1110, -700, -450, 150, 400, 650 )
RING_STONE = ( 10.0, -52.0, -35.0, 1.2 )    # half its width, its foot and head, and how far it stands proud
RING_STONE_PX = ( 280, 498, 514, 612 )      # a joint-free block of ashlar_grey's 1024 picture (x0, x1, y0, y1)


def mooring_ring( m, s, n0 ):
    """ A Fleet wall's mooring ring at n0 on the wall at e s*FLEET: a granite ring stone set in the brick, an eye bolt
    leaded into it and a wrought iron ring hanging from the eye, resting against the stone. Drawn only. """
    half, z0, z1, proud = RING_STONE
    bevel = 0.3

    def at( d, n, z ):
        """ The wall's own frame: d out from the brick into the Fleet, n along it, z up. """
        return ( s * ( FLEET - d ), n0 + n, z )

    def out( d, n, z ):
        return ( -s * d, n, z )

    # The stone, unrolled onto one granite block: its sides and bevels run on from the face, so the grain carries
    # round its edges. A ring's own part of the block, and which way round, come from where it is.
    x0, x1, y0, y1 = RING_STONE_PX
    span_n, span_z = 2 * ( half + proud ), z1 - z0 + 2 * proud
    px = min( ( x1 - x0 ) / span_n, ( y1 - y0 ) / span_z )
    wide = span_n * px
    left = x0 + ( keyed( "ring stone", s, n0 ) % 1000 ) / 1000.0 * ( x1 - x0 - wide )
    flip = chance( 0.5, "ring stone flip", s, n0 )

    def uv( d, n, z, sn, sz ):
        n, z = n + sn * ( proud - d ), z + sz * ( proud - d )
        a = ( n + half + proud ) / span_n
        a = 1 - a if flip else a
        b = ( z - z0 + proud ) / span_z
        return ( ( left + a * wide ) / 1024.0, 1 - ( y1 - b * span_z * px ) / 1024.0 )

    face = [ ( -half + bevel, z0 + bevel ), ( half - bevel, z0 + bevel ), ( half - bevel, z1 - bevel ), ( -half + bevel, z1 - bevel ) ]
    rim = [ ( -half, z0 ), ( half, z0 ), ( half, z1 ), ( -half, z1 ) ]
    card( m, "ashlar_grey", [ at( proud, n, z ) for n, z in face ], out( 1, 0, 0 ),
          uv=[ uv( proud, n, z, 0, 0 ) for n, z in face ] )
    for k, ( sn, sz ) in enumerate( ( ( 0, -1 ), ( 1, 0 ), ( 0, 1 ), ( -1, 0 ) ) ):
        a, b = rim[k], rim[( k + 1 ) % 4]
        fa, fb = face[k], face[( k + 1 ) % 4]
        bevel_pts = [ ( proud - bevel, *a ), ( proud - bevel, *b ), ( proud, *fb ), ( proud, *fa ) ]
        card( m, "ashlar_grey", [ at( *p ) for p in bevel_pts ], out( 1, sn, sz ),
              uv=[ uv( *p, sn, sz ) for p in bevel_pts ] )
        side_pts = [ ( -0.5, *a ), ( -0.5, *b ), ( proud - bevel, *b ), ( proud - bevel, *a ) ]
        card( m, "ashlar_grey", [ at( *p ) for p in side_pts ], out( 0, sn, sz ),
              uv=[ uv( *p, sn, sz ) for p in side_pts ] )

    # The eye bolt: a washer on the stone, the shank, and the eye with its hole along the wall.
    z_eye, d_eye, r_eye = -38.0, 3.6, 1.3
    bar( m, at( proud - 0.2, 0, z_eye ), at( proud + 0.3, 0, z_eye ), 1.4, "lt_hold_rust", sides=10 )
    bar( m, at( proud + 0.3, 0, z_eye ), at( d_eye - r_eye + 0.2, 0, z_eye ), 0.45, "lt_hold_rust", sides=6 )
    torus( m, at( d_eye, 0, z_eye ), out( 1, 0, 0 ), out( 0, 0, 1 ), r_eye, 0.4, "lt_hold_rust", segments=12, sides=6 )

    # The ring: hung through the eye, its bar resting on the eye's bottom, its foot against the stone, and swung a
    # little to one side or the other.
    R, r = 5.5, 0.7
    top = np.array( ( d_eye, 0.0, z_eye - ( r_eye - 0.4 - r ) ) )
    foot_d = proud + r
    tilt = math.asin( min( 1.0, ( top[0] - foot_d ) / ( 2 * R ) ) )
    down = np.array( ( -math.sin( tilt ), 0.0, -math.cos( tilt ) ) )
    along = np.array( ( 0.0, 1.0, 0.0 ) )
    swing = math.radians( ( ( keyed( "ring swing", s, n0 ) % 1001 ) / 1000.0 - 0.5 ) * 10.0 )
    v = down * math.cos( swing ) + along * math.sin( swing )
    u = along * math.cos( swing ) - down * math.sin( swing )
    centre = top + R * v
    torus( m, at( *centre ), out( *u ), out( *v ), R, r, "lt_hold_rust", segments=24, sides=8 )


def fleet():
    """ The Fleet in the play: the bed, the bridges, the barge, the dolphins and what the tide left. """
    m = Model()
    mud( m, PLAY[2] - 250, STREET_N[1] + 10 )
    street_bridge( m, *STREET_N )
    footbridge( m )
    barge( m )
    for e, n in ( ( 205, -720 ), ( -205, -690 ), ( 208, 360 ), ( -206, 1000 ), ( 204, -1440 ), ( -204, -1460 ) ):
        piles( m, e, n )
    for e, n, r in ( ( 168, -460, 14 ), ( 176, -440, 13 ), ( -190, 120, 14 ), ( -150, 1240, 13 ) ):
        tyre( m, e, n, float( mud_z( e, n ) ) - 1.5, r )
    for e0, n0, e1, n1 in ( ( -200, -300, -160, -230 ), ( 150, 820, 190, 900 ), ( -60, -980, 30, -1000 ) ):
        z = float( mud_z( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2 ) )
        m.beam( ( e0, n0, z + 3 ), ( e1, n1, z + 4 ), ( 9.0, 8.0 ), "lt_timber" )
    # Mooring rings along both walls, clear of the ladders, the stairs and the footbridge.
    for n in MOORING_RINGS:
        for s in ( -1, 1 ):
            mooring_ring( m, s, n )
    return m


def water_model():
    """ The water: the channel down the Fleet, falling to the harbour at its mouth; the harbour; and the pools on the
    mud. Drawn only, no shadows. """
    m = Model()
    w = 128.0
    m.polygon( "lt_water", [ ( -w, MOUTH_N, WATER_Z ), ( w, MOUTH_N, WATER_Z ), ( w, NORTH_ROW_N, WATER_Z ), ( -w, NORTH_ROW_N, WATER_Z ) ] )
    m.polygon( "lt_water", [ ( -w - 20, PLAY[2], HARBOUR_Z + 4 ), ( w + 20, PLAY[2], HARBOUR_Z + 4 ), ( w, MOUTH_N, WATER_Z ), ( -w, MOUTH_N, WATER_Z ) ] )
    harbour_width = SHIPYARD.SHORE_EXTENT + 500.0
    m.polygon( "lt_water", [ ( -harbour_width, -16000, HARBOUR_Z ), ( harbour_width, -16000, HARBOUR_Z ),
                            ( harbour_width, QUAY_N, HARBOUR_Z ), ( -harbour_width, QUAY_N, HARBOUR_Z ) ] )
    puddles( m, MOUTH_N, STREET_N[0] - 40, 26, 7 )
    puddles( m, STREET_N[1] + 40, NORTH_ROW_N - 100, 18, 11 )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# The backdrop: the Fleet running on north to the building over its head and the harbour's far shore

def backdrop():
    m = Model()
    mud( m, STREET_N[1] + 10, NORTH_ROW_N + 40, step_e=24.0, step_n=80.0, collide=False )
    # The building over the Fleet's head, which it runs under through a dark arch.
    wall = Wall( "e", ( -FLEET, FLEET ), ( NORTH_ROW_N, NORTH_ROW_N + T ), ( BED_Z - 12, 880.0 ), "-n" )
    culvert = wall.add( 0.0, 300.0, BED_Z - 12, BED_Z + 180, "arch" )
    culvert.bare = True
    bays = [ -165.0, -55.0, 55.0, 165.0 ]
    for z in ( FLOOR1, CEILING, 502.0, 652.0 ):
        for r in bays:
            wall.add( r, 40.0, z + 30, z + 110, "glass_arch" )
    wall.build( m, EAST.brick, None, EAST.brick, EAST.brick, None )
    dress( m, wall, EAST )
    courses( m, wall, EAST, ( FLOOR1, CEILING, 502.0, 652.0 ), skip=( "plinth", ) )
    cornice( m, wall, EAST, 840.0 )
    arch_ring( m, wall, culvert, "lt_brick_glazed", width=14.0, proud=2.0, steps=14 )
    m.box( ( -FLEET, NORTH_ROW_N + T, BED_Z - 12 ), ( FLEET, NORTH_ROW_N + T + 4, BED_Z + 200 ), { "-n": "rw_black", "default": None } )
    stepped_gable( m, wall, EAST, -FLEET, FLEET, 886.0, steps=4, step_h=50.0 )
    card( m, "lt_brick_slime", [ ( -150, NORTH_ROW_N - 0.3, BED_Z - 12 ), ( 150, NORTH_ROW_N - 0.3, BED_Z - 12 ),
                                 ( 150, NORTH_ROW_N - 0.3, -58 ), ( -150, NORTH_ROW_N - 0.3, -58 ) ], ( 0, -1, 0 ) )
    far_shore( m )
    return m


def far_shore( m ):
    """ Detailed photographic shipyard across the harbour; the near quay remains normal map geometry. """
    SHIPYARD.build( m )


# ---------------------------------------------------------------------------------------------------------------------
# Dressing, built for each side in place (so number plates read the right way round): s is +1 east, -1 west

def use( name, m, *args, **kw ):
    """Lowtide's forklift, or shared Railhead props through its checked builder."""
    if name == "forklift":
        return FORKLIFT.build( m, *args, **kw )
    if name == "lamp_post":
        return LAMPS.build( m, *args, **kw )
    return R.use( name, m, *args, **kw )


def face( s, facing ):
    return { "+e": "-e", "-e": "+e" }.get( facing, facing ) if s < 0 else facing


def crates( m, s, e, n, z0, layout, along="n", seed=0 ):
    """ Crates stacked in a little group: layout is a list of ( de, dn, levels ) offsets in crate sizes. """
    size = ( 47.2, 31.5, 31.5 )
    for k, ( de, dn, levels ) in enumerate( layout ):
        for level in range( levels ):
            paint = "rw_wood" if ( k + level + seed ) % 3 else "planks"
            use( "crate", m, s * ( e + de * ( size[1] + 1 ) ), n + dn * ( size[0] + 1 ), z0 + level * size[2], size, along, paint )


def quay_crane( m, s, e ):
    """Blender-authored rail crane; retains the original placement and portal collision."""
    CRANE.build( m, s * e )


def skip_bin( m, s, e, n, along="n" ):
    """Reference-detailed yellow steel skip, with collision around its open interior."""
    SKIP.build( m, ( s * e, n, 0.0 ), along )


def tree( m, s, e, n, scale=1.0 ):
    """ A plane tree in a cast-iron grate: Facepunch's cloud oak, with a collision box for its trunk. """
    e = s * e
    m.props.append( { "path": "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl", "position": ( e, n, 0.0 ),
                      "yaw": float( keyed( "tree", e, n ) % 360 ), "scale": ( scale, scale, scale ) } )
    m.box( ( e - 30, n - 30, -1 ), ( e + 30, n + 30, 0.4 ), { "+z": "iron_black", "default": None } )
    m.collision_box( ( e - 9, n - 9, 0 ), ( e + 9, n + 9, 160 ), WOOD )


def dress_side( s ):
    m = Model()
    # The warehouse's ground floor: the A site under the mezzanine (east), and the hall to the south. Cargo in lanes,
    # leaving the column aisles open.
    crates( m, s, 330, 700, 0.0, [ ( 0, 0, 3 ), ( 1, 0, 2 ), ( 0, 1, 2 ), ( 1, 1, 1 ) ], seed=1 )
    sacks_at( m, s, 600, 780, 0.0, rows=3, cols=3, layers=4, along="e" )
    crates( m, s, 820, 1000, 0.0, [ ( 0, 0, 2 ), ( 1, 0, 3 ), ( 2, 0, 1 ) ], seed=2 )
    use( "forklift", m, s * 640, 560, face( s, "-e" ), 0.0, 0.0 )
    sacks_at( m, s, 330, 1010, 0.0, rows=2, cols=3, layers=3, along="e" )
    crates( m, s, 400, 180, 0.0, [ ( 0, 0, 2 ), ( 1, 0, 2 ), ( 0, 1, 1 ) ], seed=3 )
    use( "pallet_stack", m, s * 860, 220, 0.0, 6, "n" )
    use( "pallet_stack", m, s * 860, 280, 0.0, 4, "n" )
    sacks_at( m, s, 560, -220, 0.0, rows=2, cols=2, layers=5, along="n" )
    crates( m, s, 820, -300, 0.0, [ ( 0, 0, 1 ), ( 1, 0, 2 ) ], seed=4 )
    crates( m, s, 520, 760, 0.0, [ ( 0, 0, 2 ), ( 1, 0, 1 ), ( 0, 1, 1 ) ], seed=9 )
    sacks_at( m, s, 600, 1040, 0.0, rows=2, cols=3, layers=2, along="e" )
    # The mezzanine: sacks by the bays and the railing.
    sacks_at( m, s, 300, 700, FLOOR1, rows=2, cols=2, layers=3, along="n" )
    sacks_at( m, s, 700, 1040, FLOOR1, rows=2, cols=3, layers=2, along="e" )
    crates( m, s, 560, 460, FLOOR1, [ ( 0, 0, 2 ), ( 1, 0, 1 ) ], seed=5 )
    crates( m, s, 420, 900, FLOOR1, [ ( 0, 0, 1 ), ( 1, 0, 2 ), ( 1, 1, 1 ) ], seed=10 )
    crates( m, s, 820, 600, FLOOR1, [ ( 0, 0, 2 ), ( 0, 1, 1 ) ], seed=11 )
    # The yard: a skip and pallets.
    skip_bin( m, s, 860, -560 )
    use( "pallet_stack", m, s * 700, -1000, 0.0, 5, "e" )
    crates( m, s, 420, -560, 0.0, [ ( 0, 0, 2 ), ( 1, 0, 1 ) ], seed=6 )
    # The cross street and the square.
    for n in ( -820.0, -100.0, 620.0 ):
        use( "lamp_post", m, s * 1285, n, 190.0 )
    tree( m, s, 1450, -430 )
    tree( m, s, 1450, 430 )
    for n in ( -280.0, 280.0 ):
        use( "bench", m, s * 1420, n, 0.0, face( s, "+e" ) )
    use( "pallet_stack", m, s * 2130, 300, 0.0, 5, "n" )
    # The north street: bollards along the kerb, lamps.
    for e in np.arange( 1050, 2200, 160 ):
        use( "bollard", m, s * e, 1205, 5.0 )
    for e in ( 900.0, 1700.0 ):
        use( "lamp_post", m, s * e, 1425, 190.0, 5.0 )
    # The quay: the crane at the B site and one further west, cargo, a container pair, a forklift.
    quay_crane( m, s, 1650 )
    quay_crane( m, s, 620 )
    use( "container", m, s * 1500, -1240, 0.0, "20", "e", "rw_container_blue" if s > 0 else "rw_container_red" )
    use( "container", m, s * 1760, -1150, 0.0, "20", "e", "rw_container_grey" )
    crates( m, s, 1380, -1470, 0.0, [ ( 0, 0, 2 ), ( 1, 0, 3 ), ( 0, 1, 1 ) ], seed=7 )
    sacks_at( m, s, 1820, -1450, 0.0, rows=2, cols=3, layers=3, along="e" )
    use( "forklift", m, s * 1100, -1180, face( s, "+e" ), 0.0, 0.0 )
    crates( m, s, 900, -1420, 0.0, [ ( 0, 0, 2 ), ( 0, 1, 2 ), ( 1, 1, 1 ) ], seed=8 )
    use( "pallet_stack", m, s * 2080, -1150, 0.0, 6, "n" )
    for e in np.arange( 360, 2200, 330 ):
        mooring_bollard( m, s * e, QUAY_N + 20 )
    return m


def sacks_at( m, s, e, n, z0, rows=2, cols=3, layers=3, along="e" ):
    """ sacks() with its near corner at e on the east, and mirrored onto the west. """
    width = cols * 22.0 if along == "e" else rows * 34.0
    sacks( m, e if s > 0 else -e - width, n, z0, rows=rows, cols=cols, layers=layers, along=along )


def mooring_bollard( m, e, n ):
    """ A cast-iron mooring bollard (a Poller) on the quay's edge: a short drum with a flared head. """
    m.cylinder( ( e, n ), 9.0, 0.0, 4.0, { "side": "iron_black", "top": "iron_black" }, sides=12 )
    m.cylinder( ( e, n ), 6.5, 4.0, 20.0, { "side": "iron_black" }, sides=12 )
    m.cylinder( ( e, n ), 8.5, 20.0, 25.0, { "side": "iron_black", "top": "iron_black", "bottom": "iron_black" }, sides=12 )
    m.collision_box( ( e - 9, n - 9, 0 ), ( e + 9, n + 9, 25 ), METAL )


# ---------------------------------------------------------------------------------------------------------------------
# Lights: ( name, position, colour, radius, shadows ), and the reflection probes

WARM = "1.6,1.3,0.95,1"
COOL = "1.0,1.12,1.3,1"


def lights():
    out = []
    for s, side in ( ( -1, "West" ), ( 1, "East" ) ):
        for k, n in enumerate( ( -200.0, 160.0 ) ):
            out.append( ( f"{side} Warehouse Hall {k + 1}", ( s * 620, n, 320 ), WARM, 520, k == 0 ) )
        for k, ( e, n ) in enumerate( ( ( 420, 560 ), ( 820, 560 ), ( 420, 960 ), ( 820, 960 ) ) ):
            out.append( ( f"{side} Warehouse Ground {k + 1}", ( s * e, n, 140 ), WARM, 340, False ) )
        for k, ( e, n ) in enumerate( ( ( 420, 760 ), ( 820, 760 ), ( 620, 1060 ) ) ):
            out.append( ( f"{side} Mezzanine {k + 1}", ( s * e, n, 320 ), WARM, 320, False ) )
    out.append( ( "Under the Bridge", ( 0, 1300, -70 ), COOL, 360, False ) )
    out.append( ( "Under the Footbridge", ( 0, -1240, -80 ), COOL, 260, False ) )
    out.extend( LANTERNS.lights() )
    return out


# ( name, centre, the box they cover e0, e1, n0, n1, z0, z1 )
PROBES = [
    ( "Fleet North", ( 0, 900, -60 ), ( -240, 240, 300, 1450, -150, 400 ) ),
    ( "Fleet South", ( 0, -500, -60 ), ( -240, 240, -1650, 300, -150, 400 ) ),
    ( "Bridge", ( 0, 1300, 80 ), ( -600, 600, 1150, 1450, -50, 400 ) ),
]
for _s, _side in ( ( -1, "West" ), ( 1, "East" ) ):
    _lo, _hi = sorted( ( _s * 260, _s * 980 ) )
    PROBES += [
        ( f"{_side} Warehouse Hall", ( _s * 620, 0, 160 ), ( _lo, _hi, -380, 380, 0, 352 ) ),
        ( f"{_side} Warehouse Ground", ( _s * 620, 760, 80 ), ( _lo, _hi, 380, 1130, 0, 160 ) ),
        ( f"{_side} Mezzanine", ( _s * 620, 760, 250 ), ( _lo, _hi, 380, 1130, 176, 352 ) ),
    ]


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

MUD = float( bed_z( 190.0 ) )          # the mud flats along the walls
RED_SPAWNS = [ ( -e, n, 0.0 ) for e in ( 1620.0, 1820.0, 2020.0 ) for n in ( -390.0, -130.0, 130.0, 390.0 ) ]
BLUE_SPAWNS = [ ( -e, n, z ) for e, n, z in RED_SPAWNS ]
BUY_ZONE = ( 1300, 2200, -600, 600, -10, 260 )

DM_HALF = [ ( 620, -250, 0 ), ( 380, 860, 0 ), ( 860, 760, 0 ), ( 620, 900, FLOOR1 ), ( 900, -950, 0 ), ( 1150, 300, 0 ),
            ( 1150, -800, 0 ), ( 1700, 0, 0 ), ( 1400, 1300, 0 ), ( 1080, -1300, 0 ), ( 2080, -800, 0 ), ( 2050, -1450, 0 ),
            ( 190, -500, MUD ), ( 190, 600, MUD ) ]
DM_SPAWNS = [ p for e, n, z in DM_HALF for p in ( ( e, n, z ), ( -e, n, z ) ) ] + [ ( 0, 1300, 0 ), ( 0, -1240, 0 ) ]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 300, 760, 640, 1100, 0 ),
               ( "bombsite_b", "Bomb Site B", 1300, 1900, -1560, -1100, 0 ) ]

# Retakes: the planter and the defenders are Red Team (Terrorist), the attackers Blue Team (CounterTerrorist).
RETAKES = {
    "bombsite_a": { "planter": [ ( 450, 950, 0 ), ( 660, 720, 0 ) ],
                    "defender": [ ( 520, 1000, FLOOR1 ), ( 620, -250, 0 ), ( 1150, 900, 0 ), ( 1600, 400, 0 ) ],
                    "attacker": [ ( -620, 200, 0 ), ( -190, -560, MUD ), ( -900, -950, 0 ), ( -1700, -300, 0 ),
                                  ( -1150, -600, 0 ) ] },
    "bombsite_b": { "planter": [ ( 1500, -1420, 0 ), ( 1560, -1150, 0 ) ],
                    "defender": [ ( 2080, -800, 0 ), ( 1150, -950, 0 ), ( 1800, -300, 0 ), ( 620, 100, 0 ) ],
                    "attacker": [ ( -1700, -300, 0 ), ( -700, -760, 0 ), ( -620, -100, 0 ), ( -180, -1150, MUD ),
                                  ( -1150, -600, 0 ) ] },
}

DOMINATION = [ ( "A", ( -620, 100, 0 ) ), ( "B", ( 0, -350, CHANNEL_Z ) ), ( "C", ( 620, 100, 0 ) ) ]
HOT_ZONES = [ ( "North Bridge", ( 0, 1300, 0 ) ), ( "Fleet", ( 0, -350, CHANNEL_Z ) ),
              ( "West Warehouse", ( -620, 760, 0 ) ), ( "East Warehouse", ( 620, 760, 0 ) ),
              ( "West Quay", ( -1100, -1350, 0 ) ), ( "East Quay", ( 1100, -1350, 0 ) ) ]
# Cash Grab: ( name, the cash, where it's taken ). The cash sits 8 over the floor and the extraction point 32.
CASH_POINTS = [ ( "Fleet", ( 0, -350, CHANNEL_Z ), ( 0, 1300, 0 ) ),
                ( "West Quay", ( -1100, -1350, 0 ), ( 620, 760, FLOOR1 ) ),
                ( "East Quay", ( 1100, -1350, 0 ), ( -620, 760, FLOOR1 ) ) ]

UP = ( 170, 420 )


def callouts():
    out = [ ( "BRIDGE", -240, 240, 1150, 1450, -10, 300 ), ( "FOOTBRIDGE", -240, 240, -1320, -1160, -10, 300 ),
            ( "FLEET NORTH", -190, 190, 600, 1450, -220, -10 ), ( "FLEET", -190, 190, -400, 600, -220, -10 ),
            ( "FLEET SOUTH", -190, 190, -1650, -400, -220, -10 ) ]
    for s, side in ( ( 1, "EAST" ), ( -1, "WEST" ) ):
        def box( name, e0, e1, *rest ):
            a, b = sorted( ( s * e0, s * e1 ) )
            return ( name, a, b, *rest )
        out += [
            box( f"{side} STREET", 240, 2200, 1150, 1450, -10, 400 ),
            box( f"{side} WAREHOUSE", 240, 1000, -400, 380, -10, 400 ),
            box( "A SITE" if s > 0 else "WEST STORE", 240, 1000, 380, 1150, -10, UP[0] ),
            box( f"{side} MEZZANINE", 240, 1000, 380, 1150, *UP ),
            box( f"{side} BAYS", 190, 240, -400, 1150, -220, 300 ),
            box( f"{side} WALL", 190, 240, 1150, 1450, -220, -10 ),
            box( f"{side} YARD", 240, 1000, -1050, -400, -10, 400 ),
            box( f"{side} STEPS", 190, 240, -1650, -400, -220, 300 ),
            box( f"{side} CROSS STREET", 1000, 1300, -1050, 1150, -10, 400 ),
            box( f"{side} SQUARE", 1300, 2200, -600, 600, -10, 400 ),
            box( f"{side} ALLEY", 1950, 2200, -1050, -600, -10, 400 ),
        ]
        if s > 0:
            out += [ ( "EAST QUAY", 240, 1300, -1650, -1050, -10, 400 ), ( "B SITE", 1300, 1900, -1650, -1050, -10, 400 ),
                     ( "QUAY END", 1900, 2200, -1650, -1050, -10, 400 ) ]
        else:
            out += [ ( "WEST QUAY", -2200, -240, -1650, -1050, -10, 400 ) ]
    return out


def all_spots():
    spots = [ ( f"red spawn {k}", p ) for k, p in enumerate( RED_SPAWNS ) ]
    spots += [ ( f"blue spawn {k}", p ) for k, p in enumerate( BLUE_SPAWNS ) ]
    spots += [ ( f"dm spawn {k}", p ) for k, p in enumerate( DM_SPAWNS ) ]
    spots += [ ( f"retakes {site} {role} {k}", p ) for site, roles in RETAKES.items() for role, points in roles.items()
               for k, p in enumerate( points ) ]
    spots += [ ( f"domination {name}", p ) for name, p in DOMINATION ]
    spots += [ ( f"hot zone {name}", p ) for name, p in HOT_ZONES ]
    spots += [ ( f"cash {name}", p ) for name, p, _ in CASH_POINTS ]
    spots += [ ( f"cash {name} extract", p ) for name, _, p in CASH_POINTS ]
    return spots


# ---------------------------------------------------------------------------------------------------------------------
# The radar picture

MINIMAP_CENTRE = ( 0.0, -100.0 )
MINIMAP_SIZE = 4600.0
MINIMAP_PIXELS = 1024


def floor_level( e, n ):
    """ The ground's walking level: 0, and the Fleet's bed between its walls (but not under the bridges). """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    z = np.zeros( np.broadcast( e, n ).shape )
    bridged = ( ( n >= STREET_N[0] ) & ( n <= STREET_N[1] ) ) | ( ( n >= FOOTBRIDGE[0] ) & ( n <= FOOTBRIDGE[1] ) )
    return np.where( ( np.abs( e ) < FLEET ) & ~bridged, bed_z( e ) + fall( n ), z )


def write_minimap( models ):
    """ Railhead's radar style: where you can walk (grey, the Fleet a little bluer), low cover darker, walls and
    buildings left clear, a light line round the edges. North up. """
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "low", "tall" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    for pts in R.collision_shapes( models ):
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = R.hull_2d( pts[:, :2] )
        if len( outline ) < 3:
            continue
        centre = outline.mean( axis=0 )
        if not ( PLAY[0] - 50 <= centre[0] <= PLAY[1] + 50 and PLAY[2] - 400 <= centre[1] <= PLAY[3] + 50 ):
            continue
        f = float( floor_level( *centre ) )
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if z1 > f + 250 and z0 > f + 100:
            continue
        if f - 24 <= z1 <= f + 18:
            draws["walk"].polygon( screen, fill=255 )
        elif z0 < f + 72 and z1 > f + 18:
            draws["low" if z1 < f + 100 else "tall"].polygon( screen, fill=255 )
    walk, low, tall = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "low", "tall" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    level = floor_level( *np.meshgrid( cols, rows ) )
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[walk & ( level < -10 )] = ( 80, 90, 100, 235 )
    image[low] = ( 64, 68, 74, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    shown = ( walk | low ) & ~tall
    edge = np.zeros_like( shown )
    edge[1:, :] |= ~shown[:-1, :]
    edge[:-1, :] |= ~shown[1:, :]
    edge[:, 1:] |= ~shown[:, :-1]
    edge[:, :-1] |= ~shown[:, 1:]
    image[shown & edge] = ( 226, 233, 240, 255 )
    MINIMAP_FILE.parent.mkdir( parents=True, exist_ok=True )
    Image.fromarray( image, "RGBA" ).save( MINIMAP_FILE )
    print( f"wrote {MINIMAP_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------
# The scene (as Railhead's)

CALLOUT_COLOUR = "0.51056,0.70698,0.49653,1"


def plan_box( e0, e1, n0, n1, z0, z1 ):
    return K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) ), ( n1 - n0, e1 - e0, z1 - z0 )


def box_collider( key, scale, trigger=True, static=True, center=( 0, 0, 0 ) ):
    return K.component( ids, "Sandbox.BoxCollider", key, Center=K.vec( center ), ColliderFlags=0, Elasticity=None,
                        Friction=None, IsTrigger=trigger, RollingResistance=None, Scale=K.vec( scale ), Static=static,
                        Surface=None, SurfaceVelocity="0,0,0" )


def ref( go_key, component_key, component_type ):
    return { "_type": "component", "component_id": ids( component_key ), "go": ids( go_key ), "component_type": component_type }


def zone_object( name, key, box, color, display, components=(), tags="zone" ):
    centre, scale = plan_box( *box )
    return K.game_object( ids, name, key, centre, tags=tags, components=[
        *components,
        K.component( ids, "Zone", f"{key}/zone", Color=color, DisplayName=display ),
        box_collider( f"{key}/box", scale ),
    ] )


def spawn_object( name, key, position, team, tags="" ):
    """ A TeamSpawnPoint facing the map's middle (the team spawns face across their square towards the Fleet). """
    yaw = K.plan_yaw( ( -position[0], -position[1] * 0.35 ) )
    return K.game_object( ids, name, key, K.to_world( position ), K.yaw_rotation( yaw ), tags=tags, components=[
        K.component( ids, "TeamSpawnPoint", f"{key}/point", Team=team ) ] )


def mode_group( name, key, modes, children, inverse=False ):
    return K.game_object( ids, name, key, components=[
        K.component( ids, "Facepunch.GameModeObject", f"{key}/modes", GameModes=list( modes ), Inverse=inverse ) ],
        children=children )


def cash_point( name, key, cash, extract ):
    at = K.to_world( ( cash[0], cash[1], cash[2] + 8 ) )
    local = K.to_world( ( extract[0], extract[1], extract[2] + 32 ) ) - at
    panel = K.game_object( ids, "Object", f"{key}/extract/panel", ( 0, 0, -31.8333797 ), "0,-0.707106829,0,0.707106829",
                           components=[
                               { **K.component( ids, "Sandbox.WorldPanel", f"{key}/extract/panel/world", HorizontalAlign="Center",
                                                InteractionRange=1000, LookAtCamera=False, PanelSize="1500,1500",
                                                RenderOptions={ "GameLayer": True, "OverlayLayer": False, "BloomLayer": False,
                                                                "AfterUILayer": False },
                                                RenderScale=1, VerticalAlign="Center" ), "__enabled": False },
                               K.component( ids, "Facepunch.UI.GameModes.CashGrab.ExtractPointWorldPanel", f"{key}/extract/panel/ui" ),
                           ] )
    extract_object = { **K.game_object( ids, f"Extract {name}", f"{key}/extract", local, components=[
        K.component( ids, "Facepunch.ExtractionPoint", f"{key}/extract/point", CashPoint=ref( key, f"{key}/point", "CashPoint" ),
                     Trigger=ref( f"{key}/extract", f"{key}/extract/box", "BoxCollider" ),
                     WorldPanel=ref( f"{key}/extract/panel", f"{key}/extract/panel/world", "WorldPanel" ) ),
        box_collider( f"{key}/extract/box", ( 50, 50, 50 ), static=False ),
    ], children=[ panel ] ), "NetworkMode": 1 }
    return { **K.game_object( ids, f"Cash Grab ({name})", key, at, components=[
        K.component( ids, "Facepunch.CashPoint", f"{key}/point",
                     Extracts=[ ref( f"{key}/extract", f"{key}/extract/point", "ExtractionPoint" ) ],
                     Resource="weapons/special/cash_bag/cash_bag.equip", State="Inactive" ),
    ], children=[ extract_object ] ), "NetworkMode": 1 }


# ( model name, scene name, collide, shadows )
SCENE_MODELS = [
    ( "lowtide_fleet", "Fleet", True, True ), ( "lowtide_east", "East", True, True ), ( "lowtide_west", "West", True, True ),
    ( "lowtide_dress_east", "Dressing East", True, True ), ( "lowtide_dress_west", "Dressing West", True, True ),
    ( "lowtide_glass", "Glass", True, False ), ( "lowtide_water", "Water", False, False ),
    ( "lowtide_backdrop", "Backdrop", False, True ),
]
NAV_SKIP = { "lowtide_glass" }
PROP_PACKAGES = R.PROP_PACKAGES


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    tags = "navskip" if model_name in NAV_SKIP else ( "water" if model_name == "lowtide_water" else "" )
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return K.game_object( ids, name, key, components=components, tags=tags )


def probe_object( name, centre, box ):
    e0, e1, n0, n1, z0, z1 = box
    at = K.to_world( centre )
    lo = K.to_world( ( e1, n0, z0 ) ) - at
    hi = K.to_world( ( e0, n1, z1 ) ) - at
    key = f"probe/{name}"
    return K.game_object( ids, f"Probe {name}", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", Bounds={ "Mins": K.vec( lo ), "Maxs": K.vec( hi ) },
                     DelayBetweenUpdates=0.1, Feathering=0.04, FrameInterval=5, MaxDistance=512, Projection="Box",
                     RenderDynamically=True, TintColor="1,1,1,1", UpdateStrategy="OnEnabled", ZFar=4096, ZNear=8 ) ] )


def look_object():
    """ Railhead's grade: ambient occlusion, a warm white balance, a light vignette, the outdoor exposure. """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.6, Radius=96,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=5900,
                     BlendFactor=0.45, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.22, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=SKY_EXPOSURE, MaximumExposure=3,
                     Mode="ACES", Rate=1 ),
    ] )


def write_scene( written, light_list, props ):
    foliage = []
    for index, prop in enumerate( props ):
        key = f"foliage/{index}"
        foliage.append( K.game_object( ids, prop.get( "name", "Tree" ), key, K.to_world( prop["position"] ),
                                       K.yaw_rotation( prop.get( "yaw", 0.0 ) ), scale=K.vec( prop.get( "scale", ( 1, 1, 1 ) ) ),
                                       components=[ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model=prop["path"],
                                                                 RenderType="On", Tint="1,1,1,1" ) ] ) )
    world = K.game_object( ids, "Lowtide", "world", children=[
        model_object( title, f"world/{name}", name, collide, shadows )
        for name, title, collide, shadows in SCENE_MODELS if name in written ] )
    light_objects = [
        K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled",
                         FogStrength=0.15 if name.startswith( "Bridge Lantern " ) else 1,
                         LightColor=color, Radius=radius, Shadows=shadows ) ] )
        for name, position, color, radius, shadows in light_list ]

    team_spawns = [ spawn_object( f"Red Spawn {k + 1}", f"spawn/red/{k}", p, "Terrorist" ) for k, p in enumerate( RED_SPAWNS ) ]
    team_spawns += [ spawn_object( f"Blue Spawn {k + 1}", f"spawn/blue/{k}", p, "CounterTerrorist" ) for k, p in enumerate( BLUE_SPAWNS ) ]
    dm_spawns = [ spawn_object( f"DM Spawn {k + 1}", f"spawn/dm/{k}", p, "Unassigned", tags="deathmatch" )
                  for k, p in enumerate( DM_SPAWNS ) ]
    retakes_spawns = []
    for site, roles in RETAKES.items():
        for role, points in roles.items():
            team = "CounterTerrorist" if role == "attacker" else "Terrorist"
            retakes_spawns += [ spawn_object( f"{site} {role} {k + 1}", f"spawn/retakes/{site}/{role}/{k}", p, team,
                                              tags=f"retakes,{site},{role}" ) for k, p in enumerate( points ) ]

    bomb_sites = []
    for index, ( name, display, e0, e1, n0, n1, z ) in enumerate( BOMB_SITES ):
        key = f"site/{name}"
        centre, scale = plan_box( e0, e1, n0, n1, z, z )
        bomb_sites.append( K.game_object( ids, name, key, centre, tags="zone,bombsite", components=[
            K.component( ids, "BombSite", f"{key}/site", DamageFalloffDistance=1750, Index=index, MaxBombDamage=500 ),
            K.component( ids, "Zone", f"{key}/zone", Color="1,0,0,1", DisplayName=display ),
            box_collider( f"{key}/box", ( scale[0], scale[1], 156 ), static=False, center=( 0, 0, 78 ) ),
        ] ) )

    e0, e1, n0, n1, z0, z1 = BUY_ZONE
    buy_zones = [
        zone_object( "buyzone_t", "buy/t", ( -e1, -e0, n0, n1, z0, z1 ), "1,0.18,0.2,1", "Red Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/t/zone_buy", Team="Terrorist" ) ] ),
        zone_object( "buyzone_ct", "buy/ct", ( e0, e1, n0, n1, z0, z1 ), "0,0.41569,1,1", "Blue Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/ct/zone_buy", Team="CounterTerrorist" ) ] ),
    ]

    callout_objects = []
    for k, c in enumerate( callouts() ):
        name, ce0, ce1, cn0, cn1, cz0, cz1 = c
        callout_objects.append( zone_object( name, f"callout/{k}/{name}", ( ce0, ce1, cn0, cn1, cz0, cz1 ), CALLOUT_COLOUR,
                                             name, [ K.component( ids, "Facepunch.MapLocation", f"callout/{k}/{name}/location" ) ] ) )

    play_centre, play_scale = plan_box( PLAY[0], PLAY[1], PLAY[2], PLAY[3], -300, 1000 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
    # Player clips where the map is open: along the harbour quay's edge (across the Fleet's mouth too, down to its
    # bed), across the Fleet's bed north of the bridge, and across the street's and the quay's ends east and west.
    clips = [ ( "Quay Edge", ( PLAY[0] - 400, PLAY[1] + 400, QUAY_N - 12, QUAY_N, -400, 1600 ) ),
              ( "Fleet North", ( -FLEET, FLEET, STREET_N[1], STREET_N[1] + 12, -400, -10 ) ) ]
    for s, side in ( ( 1, "East" ), ( -1, "West" ) ):
        for name, ( n0_, n1_ ) in ( ( "Street", STREET_N ), ( "Quay", ( QUAY_N, -1050.0 ) ) ):
            a, b = sorted( ( s * PLAY[1], s * ( PLAY[1] + 12 ) ) )
            clips.append( ( f"{side} {name} End", ( a, b, n0_, n1_, -10, 1600 ) ) )
        a, b = sorted( ( s * ALLEY_WALL[0], s * ALLEY_WALL[1] ) )
        clips.append( ( f"{side} Alley Wall", ( a, b, ALLEY_WALL[2], ALLEY_WALL[3], -10, 1600 ) ) )
    clip_objects = []
    for name, box in clips:
        centre, scale = plan_box( *box )
        clip_objects.append( K.game_object( ids, f"Player Clip {name}", f"clip/{name}", centre, tags="playerclip", components=[
            box_collider( f"clip/{name}/box", scale, trigger=False ) ] ) )
    catch = K.game_object( ids, "Catch Floor", "catch", ( 0, 0, CATCH_FLOOR_Z ), components=[
        box_collider( "catch/box", ( 60000, 60000, 100 ), trigger=False ) ] )

    objective_spots = [
        K.game_object( ids, f"Domination {label}", f"objective/dom/{label}", K.to_world( p ), components=[
            K.component( ids, "Facepunch.ObjectiveSpot", f"objective/dom/{label}/spot", Kind="Domination", Label=label ) ] )
        for label, p in DOMINATION ]
    objective_spots += [
        K.game_object( ids, f"Hot Zone {label}", f"objective/hot/{label}", K.to_world( p ), components=[
            K.component( ids, "Facepunch.ObjectiveSpot", f"objective/hot/{label}/spot", Kind="HotZone", Label=label ) ] )
        for label, p in HOT_ZONES ]
    cash = [ cash_point( name, f"cash/{name}", c, x ) for name, c, x in CASH_POINTS ]

    objects = [
        K.game_object( ids, "Scene Information", "info", components=[
            K.component( ids, "Sandbox.SceneInformation", "info/scene", Title=TITLE, Author=None, Changes="",
                         Description="A port's old warehouse quarter at low tide: red-brick warehouses either side of a "
                                     "tidal canal whose bed is mud and a channel of water, a bridge at its north end, a "
                                     "footbridge over its mouth and the harbour quay with its cranes.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # The sun, matching Lowtide's sky: from the south-south-west, 38 degrees up, so it shines up the Fleet from
        # the harbour and lights the warehouses' south ends and the quay.
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor="1.32,1.08,0.82,1", ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.42,0.48,0.58,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="1,1,1,1" ),
            K.component( ids, "Facepunch.DriftingCloudSky", "sky/cloud_clock" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.75", StartDistance=3000,
                         EndDistance=60000, FalloffExponent=1.5, Height=9000, VerticalFalloffExponent=1.2 ),
        ] ),
        look_object(),
        world,
        K.game_object( ids, "Trees", "foliage", children=foliage ),
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in PROBES ] ),
        mode_group( "Team Spawns", "spawns", ( "Deathmatch", "Gun Game" ), team_spawns, inverse=True ),
        mode_group( "Deathmatch Spawns", "spawns/dm", ( "Deathmatch", "Gun Game" ), dm_spawns ),
        mode_group( "Retakes Spawns", "spawns/retakes", ( "Retakes", ), retakes_spawns ),
        K.game_object( ids, "Bomb Sites", "sites", children=bomb_sites ),
        K.game_object( ids, "Buy Zones", "buy", children=buy_zones ),
        K.game_object( ids, "Callouts", "callouts", children=callout_objects ),
        play_area,
        K.game_object( ids, "Player Clips", "clips", children=clip_objects ),
        catch,
        K.game_object( ids, "Objective Spots", "objectives", children=objective_spots ),
        mode_group( "Cash Grab", "cash", ( "Cash Grab", ), cash ),
        K.prefab_instance( ids, "prefabs/game_modes/team_deathmatch.prefab" ),
        K.prefab_instance( ids, "prefabs/game_modes/bomb_defusal.prefab" ),
        K.prefab_instance( ids, "scenes/maps/defusemap_01/game_setup.prefab" ),
    ]
    references = sorted( { reference for prop in props for reference in PROP_PACKAGES.get( prop["path"], () ) } )
    scene = {
        "__guid": ids( "scene" ),
        "GameObjects": objects,
        "SceneProperties": {
            "NetworkInterpolation": True,
            "PhysicsMode": "Physics3D",
            "TimeScale": 1,
            "WantsSystemScene": True,
            "Metadata": {
                "Title": TITLE, "Image": MAP_ART_PATH, "IsVisibleInMenu": "True",
                "GameModes": "prefabs/game_modes/team_deathmatch.prefab, prefabs/game_modes/bomb_defusal.prefab",
            },
            "NavMesh": {
                "Enabled": True, "IncludeStaticBodies": True, "IncludeKeyframedBodies": True, "EditorAutoUpdate": True,
                "AgentHeight": 64, "AgentRadius": 16, "AgentStepSize": 18, "AgentMaxSlope": 40, "ExcludedBodies": "zone,navskip",
                "IncludedBodies": "", "DeferGeneration": False, "CustomBounds": True,
                "Bounds": { "Mins": K.vec( K.to_world( ( PLAY[1], PLAY[2], CHANNEL_Z - 40 ) ) ),
                            "Maxs": K.vec( K.to_world( ( PLAY[0], PLAY[3], NAV_TOP ) ) ) },
            },
        },
        "ResourceVersion": 3,
        "Title": TITLE,
        "Description": None,
        "__references": references,
        "__version": 3,
    }
    SCENE_FILE.parent.mkdir( parents=True, exist_ok=True )
    K.write_text( SCENE_FILE, json.dumps( scene, indent=2 ), newline=None )
    print( f"wrote {SCENE_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------

def build():
    """ Every model by name. """
    east, glass = half()
    models = {
        "lowtide_fleet": fleet(),
        "lowtide_east": east,
        "lowtide_west": east.mirrored( WEST_PAINTS ),
        "lowtide_dress_east": dress_side( 1 ),
        "lowtide_dress_west": dress_side( -1 ),
        "lowtide_glass": Model().extend( glass ).extend( glass.mirrored() ),
        "lowtide_water": water_model(),
        "lowtide_backdrop": backdrop(),
    }
    for model in models.values():
        configure( model )
    return models


def write_map_art( models ):
    """ The menus' picture, a stand-in until there's an in-engine capture: the preview's view up the Fleet from over the
    footbridge, 1920 x 1080. """
    for paint, ( source, tint, _ ) in LT_MATERIALS.items():
        jpg = K.ASSETS / f"materials/{source}_color.jpg"        # the preview only looks for PNGs (Boxyard's are JPGs)
        if jpg.exists():
            small = np.asarray( Image.open( jpg ).convert( "RGB" ).resize( ( 32, 32 ) ), float )
            PV._colours.setdefault( source.split( "/" )[1], small.reshape( -1, 3 ).mean( axis=0 ) / 255.0 )
        PV._colours[paint] = PV.paint_colour( source.split( "/" )[1] ) * np.array( tint )
    for paint, ( colour, _, _ ) in LT_PAINTED.items():
        PV._colours[paint] = np.array( colour ) / 255.0
    PV._colours[DECK.PAINT] = np.asarray( Image.open( DECK.SOURCE ).convert( "RGB" ), float ).mean( axis=( 0, 1 ) ) / 255.0
    PV._colours[RAILS.PAINT] = np.asarray( Image.open( RAILS.SOURCE ).convert( "RGB" ), float ).mean( axis=( 0, 1 ) ) / 255.0
    skip_colour = np.asarray( Image.open( MAT_DIR / "lt_skip_color.png" ).convert( "RGB" ), float ).mean( axis=( 0, 1 ) ) / 255.0
    for paint, ( tint, _ ) in SKIP.PAINTS.items():
        PV._colours[paint] = skip_colour * np.array( tint )
    opaque, glass = PV.triangles( models ), PV.triangles( models, glass=True )
    image = PV.perspective( opaque, glass, ( 0, -1900, 420 ), ( 0, 600, 60 ), size=( 960, 540 ), fov=70 )
    MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
    image.resize( ( 1920, 1080 ), Image.LANCZOS ).convert( "RGB" ).save( MAP_ART_FILE )
    print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", metavar="DIR", help="also write the reach grid's picture to this folder" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture" )
    args = parser.parse_args()

    write_materials()
    models = build()
    written = set()
    for name, model in models.items():
        if K.is_empty( model ):
            print( f"{name}: empty, not written" )
            continue
        count = K.write_model( OUT_DIR, RESOURCE_DIR, name, model )
        written.add( name )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
    if R.MISSING:
        print( "from railhead_props, left out:" )
        for name, why in sorted( R.MISSING.items() ):
            print( f"  {name}: {why}" )
    if R.UNKNOWN_PAINTS:
        print( f"paints with no material: {', '.join( sorted( R.UNKNOWN_PAINTS ) )}" )
    light_list = lights()
    print( f"{len( light_list )} lights" )

    solid_names = [ name for name, _, collide, _ in SCENE_MODELS if collide and name in models ]
    solid = [ models[name] for name in solid_names ]
    print( "checking spots:" )
    problems = R.check_spots( R.collision_aabbs( solid ), all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    out = Path( args.preview ) if args.preview else None
    if out:
        out.mkdir( parents=True, exist_ok=True )
    walked = [ models[name] for name in solid_names if name not in NAV_SKIP ]
    bounds = ( PLAY[0], PLAY[1], PLAY[2], PLAY[3] + 8 )
    cut_off = R.check_reach( walked, all_spots(), out / "reach.png" if out else None, bounds=bounds )
    print( f"  {cut_off} spot(s) cut off from the spawns" )
    seen = R.check_retakes_sight( R.Blockers( solid ), RETAKES )
    print( f"  {seen} Retakes pair(s) in sight of each other" )

    props = [ prop for model in models.values() for prop in model.props ]
    if not args.no_scene:
        write_minimap( solid )
        write_scene( written, light_list, props )
    if args.art:
        write_map_art( [ m for name, m in models.items() if name != "lowtide_backdrop" ] + [ models["lowtide_backdrop"] ] )


if __name__ == "__main__":
    main()
