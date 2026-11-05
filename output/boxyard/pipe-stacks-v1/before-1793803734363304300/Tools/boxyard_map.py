"""
Boxyard: a small multiplayer map on Shipment's layout. A walled container yard: two rows of shipping containers along
the north and south walls, four pairs of stacks round an open middle, and a few lone boxes at each team's end.

    python Tools/boxyard_map.py [--preview <dir>] [--no-scene] [--art]

Shipment is Facepunch's map, made in Hammer with flat dev colours, and it can't be edited here. So this is our own,
built by script like Belltower, Reef Hall, Railhead and Lowtide out of map_kit's boxes and polygons, painted with
Tools/boxyard_materials.py's drawn materials (run that first). It keeps Shipment's plan, but where Shipment had a car and
a SWAT van there's a grey container and a corner of pallets and drums. Writes:
- the models, to Assets/models/maps/boxyard/: the yard (its floor, the markings and the perimeter wall), the containers,
  the props, and the backdrop (the terminal round the yard: container stacks, gantry cranes and light masts), the last
  drawn only;
- the scene, Assets/scenes/maps/Boxyard/boxyard.scene, rewritten whole on every run (change the layout here, not in the
  editor);
- the radar picture, ui/minimaps/minimap_boxyard.png, and with --art a stand-in menu picture, ui/maps/boxyard.png.

Plan coordinates: e east, n north, z up, in inches (map_kit's). The yard is e -800..800, n -832..832 inside its wall,
all at z 0. Red Team spawns at the west end, Blue Team at the east end. Three lanes run between them:
- North: between the north row of containers and the north stacks. Bomb site A is its east end.
- Middle: through the gap between the stacks, past a lone container at each end.
- South: between the south stacks and the south row. Bomb site B is its east end.

The containers are ISO 1CC 20 ft boxes at their real size (boxyard_materials' constants). Their side walls' trapezoidal
corrugation is built here, bend by bend, and the paint was drawn to match it. Five are open, with their doors swung
back and their insides drawn. Every container's and the wall's top is player-clipped.

Every run checks every spawn, objective and cash spot with railhead_map's check_spots, check_reach and
check_retakes_sight, with this map's bounds, and prints what's wrong.
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
from map_kit import Model
import railhead_map as R
import railhead_preview as PV
import boxyard_materials as BM

TITLE = "Boxyard"
OUT_DIR = K.ASSETS / "models/maps/boxyard"
RESOURCE_DIR = "models/maps/boxyard"
SCENE_FILE = K.ASSETS / "scenes/maps/Boxyard/boxyard.scene"
MINIMAP_PATH = "ui/minimaps/minimap_boxyard.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_boxyard.png"     # the folder is ui/Minimaps on disk
MAP_ART_PATH = "ui/maps/boxyard.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "8b2d6e41-3f7c-4a9e-b1d5-27c94e0f6a18" )

METAL, STONE, WOOD, PLASTIC = "metal", "default", "wood", "plastic"
from map_daylight import PROFILES as DAYLIGHT_PROFILES
SUN_PITCH, SUN_YAW = DAYLIGHT_PROFILES[TITLE]["sun_angles"][:2]
SKY_MATERIAL = DAYLIGHT_PROFILES[TITLE]["components"]["SkyBox2D"]["SkyMaterial"]
SKY_EXPOSURE = DAYLIGHT_PROFILES[TITLE]["components"]["Tonemapping"]["MinimumExposure"]
FOG_COLOUR = ",".join(DAYLIGHT_PROFILES[TITLE]["components"]["GradientFog"]["Color"].split(",")[:3])
CATCH_FLOOR_Z = -3000

PLAY = ( -800.0, 800.0, -832.0, 832.0 )          # e0, e1, n0, n1: the wall's inner faces
NAV_TOP = 98.0                                   # under the containers' roofs (102)


# ---------------------------------------------------------------------------------------------------------------------
# Paints

def bx_tile( paint ):
    """ A bx_ paint's tile size: the atlases and the wall panel are mapped 1:1 here (tile 1), the rest tile at their
    real size. """
    if paint == "bx_concrete":
        return BM.CONCRETE_TILE
    if paint == "bx_galv":
        return 32.0
    if paint in BM.SMALL:
        return 48.0
    if paint in BM.PAINTED:
        return 64.0
    return 1.0


def configure( model ):
    """ Points the bx_ paints at Boxyard's materials, and the rw_ paints (railhead_props' crates and pallets)
    at Railhead's, as railhead_map.configure does but without its masonry alignment. """
    known = {}
    if R.RM is not None and hasattr( R.RM, "paints" ):
        try:
            known = R.RM.paints()
        except Exception as error:
            print( f"railhead_materials.paints() failed: {error}" )
    tiles = getattr( R.RB, "RW_TILES", {} ) if R.RB is not None else {}
    for paint in list( model.polygons ):
        if paint.startswith( "bx_" ):
            model.material_overrides[paint] = f"{BM.RESOURCE_DIR}/{paint}.vmat"
            model.tile_overrides[paint] = bx_tile( paint )
            if paint not in BM.all_paints():
                R.UNKNOWN_PAINTS.add( paint )
        elif paint.startswith( "rw_" ):
            try:
                path = R.RM.material_path( paint )
            except Exception:
                path = f"materials/railhead/{paint}.vmat"
            model.material_overrides[paint] = path
            model.tile_overrides[paint] = float( ( known[paint][1] if paint in known else tiles.get( paint ) ) or 64.0 )
            if known and paint not in known:
                R.UNKNOWN_PAINTS.add( paint )
        elif paint not in model.material_overrides:
            try:
                BT.tile_units( paint )
            except Exception:
                R.UNKNOWN_PAINTS.add( paint )
                model.material_overrides[paint] = "materials/railhead/rw_concrete.vmat"
                model.tile_overrides[paint] = 64.0
    grain = set( getattr( R.RM, "GRAIN", () ) ) | set( getattr( R.P, "GRAIN", () ) )
    model.grain_paints |= { p for p in model.polygons if p in grain }
    model.anchored_paints = set()
    model.decal_paints = set()
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers

def keyed( *key ):
    text = ",".join( f"{float( k ):.1f}" if isinstance( k, ( int, float, np.integer, np.floating ) ) else str( k ) for k in key )
    return zlib.crc32( text.encode() )


def chance( share, *key ):
    return ( keyed( *key ) % 10007 ) / 10007.0 < share


def card( m, paint, points, towards, uv=None, both=False, normals=None ):
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
        if normals is not None:
            normals = list( normals[:1] ) + list( normals[:0:-1] )
    m.polygon( paint, pts, both_sides=both, uv=uv, normals=normals )


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


def lathe( m, base, axis, profile, paints, sides=16, cap=None, surface=None, turn=0.0 ):
    """ A round thing turned about axis from base: profile [ ( radius, height ) ] up the axis, paints one paint or one
    per band (profile[k] to profile[k + 1], None for none), cap the paint over the last ring. Shaded smooth round the
    axis. surface adds one hull round it. """
    base = np.asarray( base, float )
    axis = K.normalise( np.asarray( axis, float ) )
    side = np.cross( axis, ( 0.0, 0.0, 1.0 ) )
    if np.linalg.norm( side ) < 1e-6:
        side = np.array( ( 1.0, 0.0, 0.0 ) )
    u = K.normalise( side )
    w = np.cross( axis, u )
    dirs = [ u * math.cos( turn + 2 * math.pi * k / sides ) + w * math.sin( turn + 2 * math.pi * k / sides )
             for k in range( sides ) ]
    rings = [ [ base + axis * h + d * r for d in dirs ] for r, h in profile ]
    for j in range( len( profile ) - 1 ):
        paint = paints[j] if isinstance( paints, ( list, tuple ) ) else paints
        if paint is None:
            continue
        ( r0, h0 ), ( r1, h1 ) = profile[j], profile[j + 1]
        slope = np.array( ( h1 - h0, r0 - r1 ), float )      # the band's outward normal: ( radial, along the axis )
        if np.linalg.norm( slope ) < 1e-9:
            continue
        slope /= np.linalg.norm( slope )
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            pts = [ rings[j][k], rings[j][k1], rings[j + 1][k1], rings[j + 1][k] ]
            normals = [ dirs[i] * slope[0] + axis * slope[1] for i in ( k, k1, k1, k ) ]
            card( m, paint, pts, normals[0] + normals[1], normals=normals )
    if cap and profile[-1][0] > 1e-6:
        card( m, cap, rings[-1], axis )
    if surface:
        m.hull( [ p for ring in rings for p in ring ], surface )
    return rings


class Frame:
    """ A thing's own axes: x along heading (degrees from +e towards +n), y to its left, z up from z0. """

    def __init__( self, e, n, heading, z0=0.0 ):
        self.o = np.array( ( e, n, z0 ), float )
        t = math.radians( heading )
        self.x = np.array( ( math.cos( t ), math.sin( t ), 0.0 ) )
        self.y = np.array( ( -math.sin( t ), math.cos( t ), 0.0 ) )
        self.z = np.array( ( 0.0, 0.0, 1.0 ) )
        self.heading = heading

    def p( self, x, y, z ):
        return self.o + self.x * x + self.y * y + self.z * z

    def v( self, x, y, z=0.0 ):
        return self.x * x + self.y * y + self.z * z

    def quad( self, m, paint, corners, towards, uv=None, both=False ):
        card( m, paint, [ self.p( *c ) for c in corners ], self.v( *towards ), uv=uv, both=both )

    def box( self, m, x0, x1, y0, y1, z0, z1, paints=None, surface=None ):
        m.oriented_box( self.p( ( x0 + x1 ) / 2, ( y0 + y1 ) / 2, ( z0 + z1 ) / 2 ), ( self.x, self.y, self.z ),
                        ( x1 - x0, y1 - y0, z1 - z0 ), paints if paints is not None else { "default": None }, surface )

    def rod( self, m, a, b, r, paint, sides=6 ):
        rod( m, self.p( *a ), self.p( *b ), r, paint, sides )


# ---------------------------------------------------------------------------------------------------------------------
# The containers (ISO 1CC: boxyard_materials' sizes)

HL, HW, H = BM.LENGTH / 2, BM.WIDTH / 2, BM.HEIGHT     # 119.3, 48, 102
POST_X = HL - BM.POST                                  # the corrugated walls run between the corner posts
OUT_Y = HW - BM.SKIN                                   # the corrugation's outer flats...
IN_Y = OUT_Y - BM.DEPTH                                # ...and its inner flats
X0 = -BM.PITCH * BM.PITCHES / 2                        # where the first pitch starts
CA = BM.OUTER_FLAT / 2                                 # within a pitch: the end of the outer flat's half...
CB = CA + BM.SLOPE                                     # ...the foot of the slope...
CC = CB + BM.INNER_FLAT                                # ...the end of the inner flat...
CD = CC + BM.SLOPE                                     # ...and the top of the next slope
Z0, Z1 = BM.BOTTOM_RAIL, BM.TOP_RAIL
INSIDE_X = HL - 3.5                                    # inside: the front wall's and the door frame's inner faces
INSIDE_Y = 46.0                                        # the side walls' insides
CEILING = BM.FLOOR + BM.INSIDE_HEIGHT                  # 100
DOOR_Y = BM.DOOR_POST                                  # the door opening's half width (41)


def side_uv( sigma, x, z ):
    if sigma < 0:
        return BM.region_uv( "side_a", ( x + HL ) / BM.LENGTH, z / H )
    return BM.region_uv( "side_b", ( HL - x ) / BM.LENGTH, z / H )


def doors_uv( y, z ):
    return BM.region_uv( "doors", ( y + HW ) / BM.WIDTH, z / H )


def front_uv( y, z ):
    return BM.region_uv( "front", ( HW - y ) / BM.WIDTH, z / H )


def roof_uv( x, y ):
    return BM.region_uv( "roof", ( x + HL ) / BM.LENGTH, ( y + HW ) / BM.WIDTH )


def inside_uv( name, s, t ):
    return BM.region_uv( name, min( max( s, 0.0 ), 1.0 ), min( max( t, 0.0 ), 1.0 ), regions=BM.INSIDE )


def corrugated_side( m, F, paint, sigma ):
    """ One side wall, seen from outside: the rails and the corner posts' sides at the rails' face, and between them the
    trapezoidal corrugation, bend by bend, with the rails' top and underside closing it off. """
    out = ( 0, sigma, 0 )

    def flat( x0, x1, y, z0, z1, towards ):
        F.quad( m, paint, [ ( x0, y, z0 ), ( x1, y, z0 ), ( x1, y, z1 ), ( x0, y, z1 ) ], towards,
                uv=[ side_uv( sigma, x0, z0 ), side_uv( sigma, x1, z0 ), side_uv( sigma, x1, z1 ), side_uv( sigma, x0, z1 ) ] )

    yr = sigma * HW
    flat( -HL, HL, yr, 0.0, Z0, out )
    flat( -HL, HL, yr, Z1, H, out )
    flat( -HL, -POST_X, yr, Z0, Z1, out )
    flat( POST_X, HL, yr, Z0, Z1, out )
    for x, towards in ( ( -POST_X, ( 1, 0, 0 ) ), ( POST_X, ( -1, 0, 0 ) ) ):
        F.quad( m, paint, [ ( x, sigma * OUT_Y, Z0 ), ( x, yr, Z0 ), ( x, yr, Z1 ), ( x, sigma * OUT_Y, Z1 ) ], towards,
                uv=[ side_uv( sigma, x, Z0 ) ] * 2 + [ side_uv( sigma, x, Z1 ) ] * 2 )

    xs = [ X0 + BM.PITCH * k for k in range( BM.PITCHES ) ]
    yo, yi = sigma * OUT_Y, sigma * IN_Y
    flat( -POST_X, xs[0] + CA, yo, Z0, Z1, out )
    for k in range( BM.PITCHES - 1 ):
        flat( xs[k] + CD, xs[k + 1] + CA, yo, Z0, Z1, out )
    flat( xs[-1] + CD, POST_X, yo, Z0, Z1, out )
    for x in xs:
        for xa, ya, xb, yb, towards in ( ( x + CA, yo, x + CB, yi, ( 1, 2 * sigma, 0 ) ),
                                         ( x + CB, yi, x + CC, yi, out ),
                                         ( x + CC, yi, x + CD, yo, ( -1, 2 * sigma, 0 ) ) ):
            F.quad( m, paint, [ ( xa, ya, Z0 ), ( xb, yb, Z0 ), ( xb, yb, Z1 ), ( xa, ya, Z1 ) ], towards,
                    uv=[ side_uv( sigma, xa, Z0 ), side_uv( sigma, xb, Z0 ), side_uv( sigma, xb, Z1 ), side_uv( sigma, xa, Z1 ) ] )
    # The rails' top (under the corrugation) and underside (over it), from the rail's face in to the wall.
    for z, towards in ( ( Z0, ( 0, 0, 1 ) ), ( Z1, ( 0, 0, -1 ) ) ):
        F.quad( m, paint, [ ( -POST_X, yo, z ), ( POST_X, yo, z ), ( POST_X, yr, z ), ( -POST_X, yr, z ) ], towards,
                uv=[ side_uv( sigma, -POST_X, z ), side_uv( sigma, POST_X, z ), side_uv( sigma, POST_X, z ), side_uv( sigma, -POST_X, z ) ] )
        for x in xs:
            pts = [ ( x + CA, yo, z ), ( x + CB, yi, z ), ( x + CC, yi, z ), ( x + CD, yo, z ) ]
            F.quad( m, paint, pts, towards, uv=[ side_uv( sigma, p[0], z ) for p in pts ] )


def door_hardware( m, F, x, z0=3.0, z1=99.0 ):
    """ The four locking bars on the doors (outside at x), with their handles. """
    for y in ( -BM.BARS[1], -BM.BARS[0], BM.BARS[0], BM.BARS[1] ):
        F.rod( m, ( x, y, z0 ), ( x, y, z1 ), 1.0, "bx_galv", sides=6 )
        out = 1.0 if y > 0 else -1.0
        F.rod( m, ( x + 1.0, y, 46.0 ), ( x + 1.6, y + out * 9.0, 46.0 ), 0.6, "bx_galv", sides=5 )
        for z in ( z0 + 1.0, z1 - 1.0 ):
            F.box( m, x - 1.0, x + 1.4, y - 1.6, y + 1.6, z - 1.2, z + 1.2, "bx_galv" )


def door_frame( m, F, paint, depth ):
    """ The door end's posts, header and sill at x HL, and the opening's reveals back to x HL - depth. """
    x = HL
    for sigma in ( -1, 1 ):
        y0, y1 = sorted( ( sigma * DOOR_Y, sigma * HW ) )
        F.quad( m, paint, [ ( x, y0, 0 ), ( x, y1, 0 ), ( x, y1, H ), ( x, y0, H ) ], ( 1, 0, 0 ),
                uv=[ doors_uv( y0, 0 ), doors_uv( y1, 0 ), doors_uv( y1, H ), doors_uv( y0, H ) ] )
    for z0, z1 in ( ( BM.DOOR_HEADER, H ), ( 0.0, BM.DOOR_SILL ) ):
        F.quad( m, paint, [ ( x, -DOOR_Y, z0 ), ( x, DOOR_Y, z0 ), ( x, DOOR_Y, z1 ), ( x, -DOOR_Y, z1 ) ], ( 1, 0, 0 ),
                uv=[ doors_uv( -DOOR_Y, z0 ), doors_uv( DOOR_Y, z0 ), doors_uv( DOOR_Y, z1 ), doors_uv( -DOOR_Y, z1 ) ] )
    xb = x - depth
    zs, zh = BM.DOOR_SILL, BM.DOOR_HEADER
    for sigma in ( -1, 1 ):
        y = sigma * DOOR_Y
        F.quad( m, paint, [ ( xb, y, zs ), ( x, y, zs ), ( x, y, zh ), ( xb, y, zh ) ], ( 0, -sigma, 0 ),
                uv=[ doors_uv( y, zs ) ] * 2 + [ doors_uv( y, zh ) ] * 2 )
    F.quad( m, paint, [ ( xb, -DOOR_Y, zh ), ( x, -DOOR_Y, zh ), ( x, DOOR_Y, zh ), ( xb, DOOR_Y, zh ) ], ( 0, 0, -1 ),
            uv=[ doors_uv( -DOOR_Y, zh ) ] * 2 + [ doors_uv( DOOR_Y, zh ) ] * 2 )
    F.quad( m, paint, [ ( xb, -DOOR_Y, zs ), ( x, -DOOR_Y, zs ), ( x, DOOR_Y, zs ), ( xb, DOOR_Y, zs ) ], ( 0, 0, 1 ),
            uv=[ doors_uv( -DOOR_Y, zs ) ] * 2 + [ doors_uv( DOOR_Y, zs ) ] * 2 )


def shell( m, F, paint, roof ):
    """ What every container shows outside: both corrugated sides, the blank front end and (unless another is stacked on
    it) the roof. """
    for sigma in ( -1, 1 ):
        corrugated_side( m, F, paint, sigma )
    F.quad( m, paint, [ ( -HL, -HW, 0 ), ( -HL, HW, 0 ), ( -HL, HW, H ), ( -HL, -HW, H ) ], ( -1, 0, 0 ),
            uv=[ front_uv( -HW, 0 ), front_uv( HW, 0 ), front_uv( HW, H ), front_uv( -HW, H ) ] )
    if roof:
        F.quad( m, paint, [ ( -HL, -HW, H ), ( HL, -HW, H ), ( HL, HW, H ), ( -HL, HW, H ) ], ( 0, 0, 1 ),
                uv=[ roof_uv( -HL, -HW ), roof_uv( HL, -HW ), roof_uv( HL, HW ), roof_uv( -HL, HW ) ] )


def closed_container( m, F, paint, roof=True ):
    shell( m, F, paint, roof )
    door_frame( m, F, paint, 0.75 )
    xl = HL - 0.75
    zs, zh = BM.DOOR_SILL, BM.DOOR_HEADER
    F.quad( m, paint, [ ( xl, -DOOR_Y, zs ), ( xl, DOOR_Y, zs ), ( xl, DOOR_Y, zh ), ( xl, -DOOR_Y, zh ) ], ( 1, 0, 0 ),
            uv=[ doors_uv( -DOOR_Y, zs ), doors_uv( DOOR_Y, zs ), doors_uv( DOOR_Y, zh ), doors_uv( -DOOR_Y, zh ) ] )
    door_hardware( m, F, HL + 0.35 )
    F.box( m, -HL, HL, -HW, HW, 0.0, H, surface=METAL )


def open_leaf( m, F, paint, sigma, alpha ):
    """ One door leaf, swung open alpha degrees about its hinge on the post at y sigma * 41.5. """
    hinge = np.array( ( HL + 0.5, sigma * 41.5 ) )
    t = math.radians( alpha )
    d = np.array( ( math.sin( t ), -sigma * math.cos( t ) ) )      # along the leaf, away from the hinge
    nv = np.array( ( math.cos( t ), sigma * math.sin( t ) ) )      # its outer face's normal
    zs, zh = BM.DOOR_SILL, BM.DOOR_HEADER
    a0, a1, thick = 0.5, 41.1, 1.6

    def P( a, b, z ):
        xy = hinge + a * d - b * nv
        return ( xy[0], xy[1], z )

    def out_uv( a, z ):
        return BM.region_uv( "doors", ( sigma * ( 41.5 - a ) + HW ) / BM.WIDTH, z / H )

    def in_uv( a, z ):
        return inside_uv( "doors", ( INSIDE_Y - sigma * ( 41.5 - a ) ) / ( 2 * INSIDE_Y ), ( z - BM.FLOOR ) / BM.INSIDE_HEIGHT )

    out3, d3 = ( nv[0], nv[1], 0.0 ), ( d[0], d[1], 0.0 )
    F.quad( m, paint, [ P( a0, 0, zs ), P( a1, 0, zs ), P( a1, 0, zh ), P( a0, 0, zh ) ], out3,
            uv=[ out_uv( a0, zs ), out_uv( a1, zs ), out_uv( a1, zh ), out_uv( a0, zh ) ] )
    F.quad( m, "bx_container_inside", [ P( a0, thick, zs ), P( a1, thick, zs ), P( a1, thick, zh ), P( a0, thick, zh ) ],
            ( -nv[0], -nv[1], 0.0 ), uv=[ in_uv( a0, zs ), in_uv( a1, zs ), in_uv( a1, zh ), in_uv( a0, zh ) ] )
    for a, towards in ( ( a0, ( -d[0], -d[1], 0.0 ) ), ( a1, d3 ) ):
        F.quad( m, paint, [ P( a, 0, zs ), P( a, thick, zs ), P( a, thick, zh ), P( a, 0, zh ) ], towards,
                uv=[ out_uv( a, zs ) ] * 2 + [ out_uv( a, zh ) ] * 2 )
    for z, towards in ( ( zs, ( 0, 0, -1 ) ), ( zh, ( 0, 0, 1 ) ) ):
        F.quad( m, paint, [ P( a0, 0, z ), P( a1, 0, z ), P( a1, thick, z ), P( a0, thick, z ) ], towards,
                uv=[ out_uv( a0, z ), out_uv( a1, z ), out_uv( a1, z ), out_uv( a0, z ) ] )
    for a in ( 31.0, 11.0 ):
        F.rod( m, P( a, -1.0, zs + 1.5 ), P( a, -1.0, zh - 2.0 ), 1.0, "bx_galv", sides=6 )
        F.rod( m, P( a + 1.0, -2.0, 46.0 ), P( a - 8.0, -2.6, 46.0 ), 0.6, "bx_galv", sides=5 )
    m.hull( [ F.p( *P( a, b, z ) ) for a in ( a0, a1 ) for b in ( 0.0, thick ) for z in ( zs, zh ) ], METAL )
    out = P( 41.1, 0, 0 )
    return np.hypot( out[0], out[1] )


def open_container( m, F, paint, roof=True, leaves=( 115.0, 115.0 ) ):
    """ A container standing open: its doors swung back, and its inside (plywood floor, painted walls and ceiling). """
    shell( m, F, paint, roof )
    door_frame( m, F, paint, HL - INSIDE_X )
    xi, yi, zf, zc = INSIDE_X, INSIDE_Y, BM.FLOOR, CEILING
    ins = "bx_container_inside"

    def wall_uv( sigma, x, z ):
        s = ( x + xi ) / ( 2 * xi ) if sigma > 0 else ( xi - x ) / ( 2 * xi )
        return inside_uv( "wall", s, ( z - zf ) / BM.INSIDE_HEIGHT )

    for sigma in ( -1, 1 ):
        y = sigma * yi
        F.quad( m, ins, [ ( -xi, y, zf ), ( xi, y, zf ), ( xi, y, zc ), ( -xi, y, zc ) ], ( 0, -sigma, 0 ),
                uv=[ wall_uv( sigma, -xi, zf ), wall_uv( sigma, xi, zf ), wall_uv( sigma, xi, zc ), wall_uv( sigma, -xi, zc ) ] )
    for z, name, towards in ( ( zf, "floor", ( 0, 0, 1 ) ), ( zc, "ceiling", ( 0, 0, -1 ) ) ):
        pts = [ ( -xi, -yi, z ), ( xi, -yi, z ), ( xi, yi, z ), ( -xi, yi, z ) ]
        F.quad( m, ins, pts, towards, uv=[ inside_uv( name, ( p[0] + xi ) / ( 2 * xi ), ( p[1] + yi ) / ( 2 * yi ) ) for p in pts ] )
    pts = [ ( -xi, -yi, zf ), ( -xi, yi, zf ), ( -xi, yi, zc ), ( -xi, -yi, zc ) ]
    F.quad( m, ins, pts, ( 1, 0, 0 ), uv=[ inside_uv( "front", ( p[1] + yi ) / ( 2 * yi ), ( p[2] - zf ) / BM.INSIDE_HEIGHT ) for p in pts ] )
    # The door frame's inner face round the opening.
    ring = [ [ ( xi, -yi, zf ), ( xi, -DOOR_Y, zf ), ( xi, -DOOR_Y, zc ), ( xi, -yi, zc ) ],
             [ ( xi, DOOR_Y, zf ), ( xi, yi, zf ), ( xi, yi, zc ), ( xi, DOOR_Y, zc ) ],
             [ ( xi, -DOOR_Y, BM.DOOR_HEADER ), ( xi, DOOR_Y, BM.DOOR_HEADER ), ( xi, DOOR_Y, zc ), ( xi, -DOOR_Y, zc ) ],
             [ ( xi, -DOOR_Y, zf ), ( xi, DOOR_Y, zf ), ( xi, DOOR_Y, BM.DOOR_SILL ), ( xi, -DOOR_Y, BM.DOOR_SILL ) ] ]
    for pts in ring:
        F.quad( m, ins, pts, ( -1, 0, 0 ), uv=[ inside_uv( "doors", ( yi - p[1] ) / ( 2 * yi ), ( p[2] - zf ) / BM.INSIDE_HEIGHT ) for p in pts ] )
    for sigma, alpha in zip( ( -1, 1 ), leaves ):
        open_leaf( m, F, paint, sigma, alpha )
    # Collision: the floor, the roof, both sides, the front, and the door frame round the opening.
    F.box( m, -HL, HL, -HW, HW, 0.0, zf, surface=WOOD )
    F.box( m, -HL, HL, -HW, HW, zc, H, surface=METAL )
    for sigma in ( -1, 1 ):
        y0, y1 = sorted( ( sigma * yi, sigma * HW ) )
        F.box( m, -HL, HL, y0, y1, zf, zc, surface=METAL )
        y0, y1 = sorted( ( sigma * DOOR_Y, sigma * yi ) )
        F.box( m, xi, HL, y0, y1, zf, zc, surface=METAL )
    F.box( m, -HL, -xi, -yi, yi, zf, zc, surface=METAL )
    F.box( m, xi, HL, -DOOR_Y, DOOR_Y, BM.DOOR_HEADER, zc, surface=METAL )


def far_container( m, F, paint, roof ):
    """ A container in the backdrop: four flat sides and, on top of its stack, the roof. """
    for sigma in ( -1, 1 ):
        y = sigma * HW
        F.quad( m, paint, [ ( -HL, y, 0 ), ( HL, y, 0 ), ( HL, y, H ), ( -HL, y, H ) ], ( 0, sigma, 0 ),
                uv=[ side_uv( sigma, -HL, 0 ), side_uv( sigma, HL, 0 ), side_uv( sigma, HL, H ), side_uv( sigma, -HL, H ) ] )
    F.quad( m, paint, [ ( -HL, -HW, 0 ), ( -HL, HW, 0 ), ( -HL, HW, H ), ( -HL, -HW, H ) ], ( -1, 0, 0 ),
            uv=[ front_uv( -HW, 0 ), front_uv( HW, 0 ), front_uv( HW, H ), front_uv( -HW, H ) ] )
    F.quad( m, paint, [ ( HL, -HW, 0 ), ( HL, HW, 0 ), ( HL, HW, H ), ( HL, -HW, H ) ], ( 1, 0, 0 ),
            uv=[ doors_uv( -HW, 0 ), doors_uv( HW, 0 ), doors_uv( HW, H ), doors_uv( -HW, H ) ] )
    if roof:
        F.quad( m, paint, [ ( -HL, -HW, H ), ( HL, -HW, H ), ( HL, HW, H ), ( -HL, HW, H ) ], ( 0, 0, 1 ),
                uv=[ roof_uv( -HL, -HW ), roof_uv( HL, -HW ), roof_uv( HL, HW ), roof_uv( -HL, HW ) ] )


def paint_for( colour, *key ):
    variants = [ v for c, v in BM.CONTAINERS if c == colour ]
    return f"bx_container_{colour}_{variants[keyed( colour, *key ) % len( variants )]}"


# name, e, n, heading (the door end's way), colour, open, the colour stacked on it (or None), its leaves' swing
CONTAINERS = [
    ( "North Row", 0.0, 784.0, 0.0, "green", False, None, None ),
    ( "North Row Open", 0.0, 688.0, 0.0, "red", True, None, ( 115.0, 115.0 ) ),
    ( "South Row Open", 0.0, -784.0, 0.0, "green", True, None, ( 90.0, 115.0 ) ),
    ( "South Row", 0.0, -688.0, 0.0, "red", False, None, None ),
    ( "East Stack", 586.6, 0.0, 90.0, "blue", False, "green", None ),
    ( "East Angled", 714.6, 0.0, 75.0, "red", False, None, None ),
    ( "West Stack", -592.3, 0.0, 90.0, "red", False, None, None ),
    ( "West Angled", -720.3, 0.0, 105.0, "blue", False, None, None ),
    ( "South East Inner", 176.0, -288.0, 90.0, "red", False, "blue", None ),
    ( "South East Outer", 272.0, -288.0, 90.0, "blue", True, "green", ( 115.0, 115.0 ) ),
    ( "South West Inner", -176.0, -288.0, 90.0, "red", True, None, ( 115.0, 115.0 ) ),
    ( "South West Outer", -272.0, -288.0, 90.0, "green", False, None, None ),
    ( "North West Inner", -176.0, 288.0, 90.0, "green", False, None, None ),
    ( "North West Outer", -272.0, 288.0, -90.0, "blue", True, None, ( 115.0, 115.0 ) ),
    ( "North East Inner", 176.0, 288.0, -90.0, "blue", True, None, ( 115.0, 115.0 ) ),
    ( "North East Outer", 272.0, 288.0, 90.0, "red", False, None, None ),
    ( "A Site", 627.9, 677.5, -24.6, "orange", False, None, None ),
    ( "South East Lone", 508.0, -630.0, 11.0, "grey", False, None, None ),
]


def containers():
    """ Every container, and what the scene needs from them: ( frame, top ) for the clips, and the open ones' insides
    for their lights and probes. """
    m = Model()
    tops, insides = [], []
    for name, e, n, heading, colour, is_open, on_top, leaves in CONTAINERS:
        F = Frame( e, n, heading )
        paint = paint_for( colour, e, n )
        if is_open:
            open_container( m, F, paint, roof=on_top is None, leaves=leaves )
            corners = [ F.p( x, y, z ) for x in ( -INSIDE_X, INSIDE_X ) for y in ( -INSIDE_Y, INSIDE_Y ) for z in ( BM.FLOOR, CEILING ) ]
            insides.append( ( name, F, np.min( corners, axis=0 ), np.max( corners, axis=0 ) ) )
        else:
            closed_container( m, F, paint, roof=on_top is None )
        top = H
        if on_top:
            upper = Frame( e, n, heading + ( 180.0 if chance( 0.5, "turn", e, n ) else 0.0 ), H )
            closed_container( m, upper, paint_for( on_top, e, n, "top" ) )
            top = 2 * H
        tops.append( ( name, F, top ) )
    return m, tops, insides


# ---------------------------------------------------------------------------------------------------------------------
# The yard: its floor, markings and perimeter wall

WALL_T, WALL_H = 8.0, 128.0
# The wall's runs, seen from inside: ( name, inward normal, the left end, the right end ) of the inner face. The east and
# west runs go 8 past the corners so the outside and the top close up there.
WALL_RUNS = [
    ( "East", ( -1.0, 0.0 ), ( 800.0, 840.0 ), ( 800.0, -840.0 ) ),
    ( "West", ( 1.0, 0.0 ), ( -800.0, -840.0 ), ( -800.0, 840.0 ) ),
    ( "North", ( 0.0, -1.0 ), ( -800.0, 832.0 ), ( 800.0, 832.0 ) ),
    ( "South", ( 0.0, 1.0 ), ( 800.0, -832.0 ), ( -800.0, -832.0 ) ),
]
PANELS = 7


def wall( m ):
    """ Precast concrete panels between steel H-posts, 128 high, with two strands of wire over them. """
    for name, normal, left, right in WALL_RUNS:
        N = np.array( ( *normal, 0.0 ) )
        a0, b0 = np.array( ( *left, 0.0 ) ), np.array( ( *right, 0.0 ) )
        along = K.normalise( b0 - a0 )
        up = np.array( ( 0.0, 0.0, 1.0 ) )
        back = -N * WALL_T
        for k in range( PANELS ):
            a = a0 + ( b0 - a0 ) * k / PANELS
            b = a0 + ( b0 - a0 ) * ( k + 1 ) / PANELS
            card( m, "bx_wall_panel", [ a, b, b + up * WALL_H, a + up * WALL_H ], N,
                  uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] )
            card( m, "bx_wall_panel", [ a + back, b + back, b + back + up * WALL_H, a + back + up * WALL_H ], -N,
                  uv=[ ( 1, 0 ), ( 0, 0 ), ( 0, 1 ), ( 1, 1 ) ] )
            card( m, "bx_wall_panel", [ a + up * WALL_H, b + up * WALL_H, b + back + up * WALL_H, a + back + up * WALL_H ], up,
                  uv=[ ( 0, 1 ), ( 1, 1 ), ( 1, 0.95 ), ( 0, 0.95 ) ] )
        for k in range( PANELS + 1 ):
            c = a0 + ( b0 - a0 ) * k / PANELS
            m.oriented_box( c + N * ( 2.0 - ( WALL_T + 4.0 ) / 2 ) + up * 70.0, ( along, N, up ), ( 6.0, WALL_T + 4.0, 140.0 ),
                            "bx_steel_dark" )
        middle = -N * ( WALL_T / 2 )
        for z in ( 134.0, 140.0 ):
            rod( m, a0 + middle + up * z, b0 + middle + up * z, 0.15, "bx_galv", sides=4 )
    m.collision_box( ( 798, -870, -16 ), ( 830, 870, WALL_H ), STONE )
    m.collision_box( ( -830, -870, -16 ), ( -798, 870, WALL_H ), STONE )
    m.collision_box( ( -870, 830, -16 ), ( 870, 862, WALL_H ), STONE )
    m.collision_box( ( -870, -862, -16 ), ( 870, -830, WALL_H ), STONE )


def line_strip( m, paint, p0, p1, width, z ):
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    along = p1 - p0
    length = float( np.linalg.norm( along ) )
    side = np.array( ( -along[1], along[0] ) ) / length * width / 2
    pts = [ ( *( p0 - side ), z ), ( *( p1 - side ), z ), ( *( p1 + side ), z ), ( *( p0 + side ), z ) ]
    card( m, paint, pts, ( 0, 0, 1 ), uv=[ ( 0, 0 ), ( length / 192.0, 0 ), ( length / 192.0, 1 ), ( 0, 1 ) ] )


def rectangle_lines( m, paint, e0, e1, n0, n1, width, z ):
    """ A painted rectangle, its centreline on these edges, the long sides drawn through the corners. """
    h = width / 2
    line_strip( m, paint, ( e0 - h, n0 ), ( e1 + h, n0 ), width, z )
    line_strip( m, paint, ( e0 - h, n1 ), ( e1 + h, n1 ), width, z )
    line_strip( m, paint, ( e0, n0 + h ), ( e0, n1 - h ), width, z )
    line_strip( m, paint, ( e1, n0 + h ), ( e1, n1 - h ), width, z )


def yard():
    m = Model()
    card( m, "bx_concrete", [ ( -840, -872, 0 ), ( 840, -872, 0 ), ( 840, 872, 0 ), ( -840, 872, 0 ) ], ( 0, 0, 1 ) )
    m.collision_box( ( -832, -864, -16 ), ( 832, 864, 0 ), STONE )
    # A yellow walkway line round the yard, and white outlines round the four stacks.
    rectangle_lines( m, "bx_line_yellow", -770, 770, -802, 802, 4.0, 0.05 )
    for se in ( -1, 1 ):
        for sn in ( -1, 1 ):
            e0, e1 = sorted( ( se * 116.0, se * 332.0 ) )
            n0, n1 = sorted( ( sn * 157.0, sn * 419.0 ) )
            rectangle_lines( m, "bx_line_white", e0, e1, n0, n1, 4.0, 0.07 )
    wall( m )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Props

TRAFFIC_CONE_MODEL = "models/maps/boxyard/traffic_cone_v2/traffic_cone.vmdl"
CONE_LEAN = 0.16    # how far the model's tip leans along its own x, as Sources/Boxyard/traffic_cone_v2/cone.py bends it
CONES = []      # the cones props() has placed: ( name, plan position, rotation ), for write_scene


def rotation_text( x, y, z ):
    """ The x,y,z,w rotation taking a model's own axes onto these world directions. """
    r = np.column_stack( ( x, y, z ) )
    w = math.sqrt( max( 0.0, 1.0 + r[0, 0] + r[1, 1] + r[2, 2] ) ) / 2
    a = math.sqrt( max( 0.0, 1.0 + r[0, 0] - r[1, 1] - r[2, 2] ) ) / 2
    b = math.sqrt( max( 0.0, 1.0 - r[0, 0] + r[1, 1] - r[2, 2] ) ) / 2
    c = math.sqrt( max( 0.0, 1.0 - r[0, 0] - r[1, 1] + r[2, 2] ) ) / 2
    a, b, c = math.copysign( a, r[2, 1] - r[1, 2] ), math.copysign( b, r[0, 2] - r[2, 0] ), math.copysign( c, r[1, 0] - r[0, 1] )
    return f"{a:.7f},{b:.7f},{c:.7f},{w:.7f}"


def cone_collision( m, at, axes ):
    """ The model's own shape as collision: one hull for its base and collar, one for its body with its lean. at is its origin
    in plan, axes its own x, y and z in world directions. """
    def plan( x, y, z ):
        world = axes[0] * x + axes[1] * y + axes[2] * z
        return np.asarray( at, float ) + np.array( ( -world[1], world[0], world[2] ) )

    def ring( radius, z, sides=16 ):
        lean = CONE_LEAN * ( z / 28.0 ) ** 2
        return [ plan( radius * math.cos( 2 * math.pi * k / sides ) + lean, radius * math.sin( 2 * math.pi * k / sides ), z ) for k in range( sides ) ]

    def rounded_square( half, radius, z ):
        inner = half - radius
        return [ plan( sx * inner + radius * math.cos( math.radians( start + 22.5 * k ) ), sy * inner + radius * math.sin( math.radians( start + 22.5 * k ) ), z )
                 for sx, sy, start in ( ( 1, 1, 0 ), ( -1, 1, 90 ), ( -1, -1, 180 ), ( 1, -1, 270 ) ) for k in range( 5 ) ]

    base = [ p for half, radius, z in ( ( 6.86, 1.0, 0.0 ), ( 7.0, 1.1, 0.12 ), ( 7.0, 1.1, 0.84 ), ( 6.66, 1.0, 1.2 ) ) for p in rounded_square( half, radius, z ) ]
    m.hull( base + ring( 5.62, 1.88 ), PLASTIC )
    m.hull( ring( 5.6, 1.2 ) + ring( 1.09, 27.8 ) + ring( 0.98, 28.0 ), PLASTIC )


def cone( m, e, n, heading=0.0 ):
    """ A 28 in traffic cone on its square base. Sources/Boxyard/traffic_cone_v2's model draws it, placed by the scene, and only its
    collision goes in the props model. """
    t = math.radians( heading )
    x, y, z = np.array( ( math.cos( t ), math.sin( t ), 0.0 ) ), np.array( ( -math.sin( t ), math.cos( t ), 0.0 ) ), np.array( ( 0.0, 0.0, 1.0 ) )
    cone_collision( m, ( e, n, 0.0 ), ( x, y, z ) )
    CONES.append( ( "Cone", ( e, n, 0.0 ), K.yaw_rotation( heading ) ) )


def lying_cone( m, e, n, heading ):
    """ A cone knocked over, along heading: it rests on its base's edge and its tip. It lies 3 back from ( e, n ) along heading, which
    keeps its tip out of the crate behind it. """
    F = Frame( e, n, heading )
    tilt = math.atan2( 7.0 - 1.0, 28.0 )
    base = F.p( -3.0, 0, 7.0 * math.cos( tilt ) )
    z = K.to_world( F.v( math.cos( tilt ), 0, -math.sin( tilt ) ) )
    # The base's edge lies level: the model's y stays flat, square to the way it points.
    y = np.cross( ( 0.0, 0.0, 1.0 ), z )
    y = y / np.linalg.norm( y )
    x = np.cross( y, z )
    cone_collision( m, base, ( x, y, z ) )
    CONES.append( ( "Cone knocked over", tuple( map( float, base ) ), rotation_text( x, y, z ) ) )


OIL_DRUM_DIR = "models/maps/boxyard/oil_drum_v2"
DRUMS = []      # the drums props() has placed: ( e, n, colour, yaw ), for write_scene


def drum( m, e, n, colour, yaw ):
    """ A 205 l steel drum: 22.5 in across, 34.8 high, with two rolling hoops. Only its hull goes in the props model, as it
    always did. Sources/Boxyard/oil_drum_v2's model draws it, placed by the scene. yaw turns its lettering to the lane. """
    r = 11.25
    profile = [ ( r, 0.0 ), ( r, 11.4 ), ( r + 0.5, 11.55 ), ( r + 0.5, 11.85 ), ( r, 12.0 ), ( r, 22.8 ), ( r + 0.5, 22.95 ),
                ( r + 0.5, 23.25 ), ( r, 23.4 ), ( r, 34.8 ), ( r - 0.6, 34.8 ), ( r - 0.6, 34.3 ) ]
    lathe( m, ( e, n, 0.0 ), ( 0, 0, 1 ), profile, None, sides=16, surface=METAL,
           turn=( keyed( "drum", e, n ) % 360 ) * math.pi / 180 )
    DRUMS.append( ( e, n, colour, yaw ) )


IBC_TOTE_MODEL = "models/props/boxyard/ibc_tote_v2/ibc_tote.vmdl"
IBCS = []       # the totes props() has placed: ( e, n, heading ), for write_scene


def ibc( m, e, n, heading ):
    """ An IBC tote, 47.2 x 39.4 x 45.8 in. Only its collision box goes in the props model. Sources/Boxyard/ibc_tote_v2's model
    draws it, placed by the scene, with its valve at the +x end. """
    F = Frame( e, n, heading )
    hl, hw = 47.2 / 2, 39.4 / 2
    F.box( m, -hl, hl, -hw, hw, 0.0, 45.8, surface=METAL )
    IBCS.append( ( e, n, heading ) )


def skip( m, e, n, heading ):
    """ A 6 cubic yard builder's skip: 144 in long at its rim, 108 at its floor, 66 wide and 48 high, on two runners. """
    F = Frame( e, n, heading )
    paint = "bx_skip_green"
    top, bottom, hw, h, floor = 72.0, 54.0, 33.0, 48.0, 4.0
    for sx in ( -1, 1 ):
        F.box( m, -bottom + 6, bottom - 6, sx * 22 - 3, sx * 22 + 3, 0.0, floor, paint )
    for sigma in ( -1, 1 ):
        pts = [ ( -bottom, sigma * hw, floor ), ( bottom, sigma * hw, floor ), ( top, sigma * hw, h ), ( -top, sigma * hw, h ) ]
        F.quad( m, paint, pts, ( 0, sigma, 0 ), both=True )
        m.hull( [ F.p( *p[:1], p[1] - sigma * t, p[2] ) for p in pts for t in ( 0.0, 1.5 ) ], METAL )
        F.box( m, -top, top, sigma * hw - 1.5 if sigma > 0 else sigma * hw - 1.5, sigma * hw + 1.5, h - 3.0, h, paint )
        for x in ( -top + 10.0, top - 10.0 ):
            F.rod( m, ( x * 0.9, sigma * ( hw + 2.5 ), h - 10 ), ( x * 0.9, sigma * ( hw + 2.5 ), h - 4 ), 1.6, paint, sides=8 )
    for sx in ( -1, 1 ):
        pts = [ ( sx * bottom, -hw, floor ), ( sx * bottom, hw, floor ), ( sx * top, hw, h ), ( sx * top, -hw, h ) ]
        F.quad( m, paint, pts, ( sx * 2.4, 0, -1.0 ), both=True )
        m.hull( [ F.p( p[0] - sx * t, p[1], p[2] ) for p in pts for t in ( 0.0, 1.5 ) ], METAL )
        F.box( m, sx * top - ( 3.0 if sx > 0 else 0.0 ), sx * top + ( 3.0 if sx < 0 else 0.0 ), -hw, hw, h - 3.0, h, paint )
    F.quad( m, paint, [ ( -bottom, -hw, floor ), ( bottom, -hw, floor ), ( bottom, hw, floor ), ( -bottom, hw, floor ) ], ( 0, 0, 1 ) )
    F.box( m, -bottom, bottom, -hw, hw, 0.0, floor, surface=METAL )


def pipes( m, e, n, heading ):
    """ Six rusty steel pipes, 8.6 in across and 160 long, stacked 3-2-1 on two timber bearers. """
    F = Frame( e, n, heading )
    for x in ( -55.0, 55.0 ):
        F.box( m, x - 2.0, x + 2.0, -14.0, 14.0, 0.0, 3.0, "rw_wood" )
    r = 4.3
    rows = [ ( 3.0 + r, ( -2 * r, 0.0, 2 * r ) ), ( 3.0 + r + 2 * r * math.sin( math.pi / 3 ), ( -r, r ) ),
             ( 3.0 + r + 4 * r * math.sin( math.pi / 3 ), ( 0.0, ) ) ]
    for z, ys in rows:
        for y in ys:
            shift = ( keyed( "pipe", e, n, z, y ) % 9 ) - 4.0
            a, b = F.p( -80.0 + shift, y, z ), F.p( 80.0 + shift, y, z )
            rod( m, a, b, r, "bx_rust", sides=10 )
            for end, towards in ( ( a, -F.x ), ( b, F.x ) ):
                side = np.cross( F.x, ( 0, 0, 1 ) )
                ring = [ end + ( side * math.cos( 2 * math.pi * k / 10 ) + np.array( ( 0, 0, 1.0 ) ) * math.sin( 2 * math.pi * k / 10 ) ) * ( r - 0.4 )
                         for k in range( 10 ) ]
                card( m, "bx_dark", ring, towards )
    F.box( m, -84.0, 84.0, -14.0, 14.0, 0.0, 3.0 + r + 4 * r * math.sin( math.pi / 3 ) + r, surface=METAL )


WHEELIE_BIN_DIR = "models/maps/boxyard/wheelie_bin_v2"
BINS = []       # the bins props() has placed: ( e, n, heading, colour ), for write_scene


def wheelie_bin( m, e, n, heading, colour ):
    """ A 240 l wheelie bin: 23 wide, 29 deep and 42 high. Only its collision box goes in the props model. Sources/Boxyard/wheelie_bin_v2's
    model draws it, placed by the scene, with its lid hinged at -y over its two wheels. """
    F = Frame( e, n, heading )
    F.box( m, -12.0, 12.0, -16.5, 16.0, 0.0, 42.2, surface=PLASTIC )
    BINS.append( ( e, n, heading, colour ) )


def props():
    m = Model()
    DRUMS.clear()
    CONES.clear()
    IBCS.clear()
    BINS.clear()
    # The north-west corner: a crate on a grounded pallet, and a skip.
    deck = R.use( "pallet_stack", m, -571.2, 560.0, z0=0.0, layers=1, along="e" )
    R.use( "crate", m, -571.2, 560.0, z0=deck if deck is not None else 5.7, along="e" )
    skip( m, -555.0, 675.0, 0.0 )
    # A site: crates by the angled container, cones.
    R.use( "crate", m, 640.0, 544.0, along="n" )
    R.use( "crate", m, 672.0, 544.0, along="n", paint="rw_wood" )
    R.use( "crate", m, 656.0, 544.0, z0=31.5, along="n" )
    for e, n in ( ( 688.0, 511.0 ), ( 558.0, 549.0 ), ( 593.0, 563.0 ) ):
        cone( m, e, n, keyed( "cone", e, n ) % 90 )
    # Big crates at the stacks' inner ends, IBCs by the north-east stack.
    R.use( "crate", m, 96.0, 207.0, size=( 60.0, 48.0, 48.0 ), along="n" )
    R.use( "crate", m, -93.0, -207.0, size=( 60.0, 48.0, 48.0 ), along="n" )
    ibc( m, 352.0, 319.0, 90.0 )
    ibc( m, 352.0, 372.0, 90.0 )
    cone( m, -54.0, -166.0, 20.0 )
    lying_cone( m, -45.0, -191.0, 200.0 )
    # B site: pipes against the east wall and the south wall, drums.
    pipes( m, 782.0, -480.0, 90.0 )
    pipes( m, 640.0, -816.0, 0.0 )
    for e, n, colour, yaw in ( ( 557.0, -498.0, "blue", 200.0 ), ( 592.0, -515.0, "red", 160.0 ), ( 562.0, -534.0, "blue", 75.0 ) ):
        drum( m, e, n, colour, yaw )
    # Bins in the middle.
    for e, colour in ( ( 34.0, "green" ), ( 60.0, "grey" ), ( 86.0, "blue" ) ):
        wheelie_bin( m, e, 150.0, 180.0 + ( keyed( "bin", e ) % 7 ) - 3.0, colour )
    # The south-west corner: a stack of pallets and two drums.
    R.use( "pallet_stack", m, -632.0, -589.0, layers=3, along="e" )
    drum( m, -600.0, -620.0, "red", 40.0 )
    drum( m, -575.0, -600.0, "blue", 300.0 )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# The backdrop: the terminal round the yard (drawn only)

STACK_ROWS = 100.0          # rows of stacks, along e, this far apart in n
STACK_COLUMNS = 245.0       # and boxes along each row this far apart
COLOURS = [ c for c in BM.COLOURS ]
MASTS = [ ( -1100.0, -1150.0 ), ( 1100.0, -1150.0 ), ( -1100.0, 1150.0 ), ( 1100.0, 1150.0 ) ]


def gantry_crane( m, e, n, heading, paint ):
    """ A rubber-tyred gantry crane straddling six rows: legs 925 apart across them, 710 high. """
    F = Frame( e, n, heading )
    span, base, top = 462.0, 140.0, 710.0
    for sy in ( -1, 1 ):
        for sx in ( -1, 1 ):
            F.box( m, sx * base - 12, sx * base + 12, sy * span - 10, sy * span + 10, 40.0, top, paint )
            F.box( m, sx * base - 30, sx * base + 30, sy * span - 16, sy * span + 16, 0.0, 40.0, "bx_rubber" )
        F.box( m, -base - 20, base + 20, sy * span - 14, sy * span + 14, 40.0, 70.0, paint )
        F.box( m, -base - 20, base + 20, sy * span - 16, sy * span + 16, top, top + 50.0, paint )
        F.box( m, -base - 40, -base + 40, sy * ( span + 30 ), sy * ( span + 90 ), top - 20, top + 60, "bx_crane_white" )
    for sx in ( -1, 1 ):
        F.box( m, sx * base - 14, sx * base + 14, -span - 20, span + 20, top + 10, top + 60, paint )
    F.box( m, -60, 60, -110, 0, top + 60, top + 110, "bx_crane_white" )
    F.box( m, -40, 40, -40, 20, top - 120, top - 20, "bx_crane_white" )
    F.box( m, -36, 36, -41, 21, top - 100, top - 40, "bx_cab_glass" )
    F.box( m, -50, 50, -60, 60, 300, 330, "bx_dark" )
    F.rod( m, ( -30, 0, top ), ( -30, 0, 330 ), 1.0, "bx_dark", sides=4 )
    F.rod( m, ( 30, 0, top ), ( 30, 0, 330 ), 1.0, "bx_dark", sides=4 )


def light_mast( m, e, n ):
    """ A high-mast floodlight: a tapered galvanised pole about 30 m high, with a ring of lamps. """
    lathe( m, ( e, n, 0.0 ), ( 0, 0, 1 ), [ ( 18.0, 0.0 ), ( 18.0, 6.0 ), ( 11.0, 6.0 ), ( 6.5, 1150.0 ) ], "bx_galv", sides=10 )
    m.cylinder( ( e, n ), 42.0, 1150.0, 1158.0, { "side": "bx_galv", "top": "bx_galv", "bottom": "bx_galv" }, sides=12 )
    for k in range( 6 ):
        t = 2 * math.pi * k / 6
        F = Frame( e + 36.0 * math.cos( t ), n + 36.0 * math.sin( t ), math.degrees( t ), 1158.0 )
        F.box( m, -8.0, 8.0, -12.0, 12.0, 0.0, 18.0, { "default": "bx_steel_dark", "+x": "bx_lamp_off" } )


def backdrop():
    m = Model()
    # The ground round the yard.
    for e0, e1, n0, n1 in ( ( -6000, 6000, 872, 6000 ), ( -6000, 6000, -6000, -872 ), ( 840, 6000, -872, 872 ),
                            ( -6000, -840, -872, 872 ) ):
        card( m, "bx_concrete", [ ( e0, n0, 0 ), ( e1, n0, 0 ), ( e1, n1, 0 ), ( e0, n1, 0 ) ], ( 0, 0, 1 ) )
    count = 0
    for i in range( -32, 33 ):
        n = i * STACK_ROWS
        if i % 9 == 4:                       # a road between blocks of rows
            continue
        for j in range( -13, 14 ):
            e = j * STACK_COLUMNS
            if j % 6 == 3:                   # and between blocks of columns
                continue
            d = max( abs( e ) - HL, abs( n ) - HW )
            if d < 1100.0 or max( abs( e ), abs( n ) ) > 3200.0:
                continue
            if any( abs( e - me ) < 200 and abs( n - mn ) < 120 for me, mn in MASTS ):
                continue
            cap = min( 5, int( 2 + ( d - 1100.0 ) / 600.0 ) )
            height = 1 + keyed( "stack", e, n ) % cap
            if chance( 0.08, "gap", e, n ):
                continue
            heading = 180.0 if chance( 0.5, "way", e, n ) else 0.0
            for level in range( height ):
                colour = COLOURS[keyed( "colour", e, n, level ) % len( COLOURS )]
                F = Frame( e + ( keyed( "jog", e, n, level ) % 5 ) - 2.0, n, heading, level * H )
                far_container( m, F, paint_for( colour, e, n, level ), roof=level == height - 1 )
                count += 1
    for e, n, heading, paint in ( ( -1715.0, 1650.0, 0.0, "bx_crane_yellow" ), ( 1960.0, -1600.0, 0.0, "bx_crane_yellow" ),
                                  ( 2450.0, 1950.0, 0.0, "bx_crane_red" ) ):
        gantry_crane( m, e, n, heading, paint )
    for e, n in MASTS:
        light_mast( m, e, n )
    print( f"backdrop: {count} containers" )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Lights and probes

INSIDE_LIGHT = "0.45,0.42,0.38,1"


def lights( insides ):
    out = []
    for name, F, _, _ in insides:
        out.append( ( f"{name} Inside", tuple( F.p( 30.0, 0.0, 85.0 ) ), INSIDE_LIGHT, 180, False ) )
    return out


def probes( insides ):
    out = [ ( "Yard", ( 0, 0, 100 ), ( -800, 800, -832, 832, -20, 400 ) ) ]
    for name, F, lo, hi in insides:
        centre = F.p( 0.0, 0.0, 50.0 )
        out.append( ( name, tuple( centre ), ( lo[0], hi[0], lo[1], hi[1], lo[2], hi[2] ) ) )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( -480.0, 160.0, 0.0 ), ( -480.0, -160.0, 0.0 ), ( -480.0, 300.0, 0.0 ), ( -480.0, -300.0, 0.0 ),
               ( -420.0, 450.0, 0.0 ), ( -420.0, -450.0, 0.0 ), ( -700.0, 220.0, 0.0 ), ( -700.0, -220.0, 0.0 ),
               ( -700.0, 380.0, 0.0 ), ( -700.0, -380.0, 0.0 ), ( -520.0, 420.0, 0.0 ), ( -560.0, -480.0, 0.0 ) ]
BLUE_SPAWNS = [ ( -e, -n, z ) for e, n, z in RED_SPAWNS ]
BUY_ZONE = ( 380, 800, -520, 520, -10, 260 )         # Blue Team's; Red Team's is its mirror

DM_SPAWNS = [ ( 400, 0, 0 ), ( -400, 0, 0 ), ( 0, 100, 0 ), ( 0, -100, 0 ), ( -90, -500, 0 ), ( 90, 500, 0 ),
              ( 330, -470, 0 ), ( -330, 500, 0 ), ( -740, -780, 0 ), ( 750, 790, 0 ), ( 700, -760, 0 ), ( -700, 760, 0 ),
              ( 220, -760, 0 ), ( -220, 760, 0 ), ( -200, -560, 0 ), ( 200, 560, 0 ) ]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 280, 560, 520, 800, 0 ),
               ( "bombsite_b", "Bomb Site B", 280, 600, -800, -520, 0 ) ]

# Retakes: the planter and the defenders are Red Team (Terrorist), the attackers Blue Team (CounterTerrorist).
_ATTACKERS = [ ( -480, 160, 0 ), ( -480, -160, 0 ), ( -480, 300, 0 ), ( -480, -300, 0 ), ( -700, 220, 0 ), ( -700, -220, 0 ) ]
RETAKES = {
    "bombsite_a": { "planter": [ ( 400, 700, 0 ), ( 330, 590, 0 ) ],
                    "defender": [ ( 640, 790, 0 ), ( 180, 600, 0 ), ( 740, 792, 0 ) ],
                    "attacker": list( _ATTACKERS ) },
    "bombsite_b": { "planter": [ ( 400, -760, 0 ), ( 330, -600, 0 ) ],
                    "defender": [ ( 640, -775, 0 ), ( 180, -600, 0 ), ( 720, -440, 0 ) ],
                    "attacker": list( _ATTACKERS ) },
}

DOMINATION = [ ( "A", ( -480, 0, 0 ) ), ( "B", ( 0, 0, 0 ) ), ( "C", ( 480, 0, 0 ) ) ]
HOT_ZONES = [ ( "Middle", ( 0, 0, 0 ) ), ( "North Lane", ( 0, 520, 0 ) ), ( "South Lane", ( 0, -520, 0 ) ),
              ( "West Yard", ( -480, 0, 0 ) ), ( "East Yard", ( 480, 0, 0 ) ) ]
# ( name, where the cash is, where it's taken )
CASH_POINTS = [ ( "North Lane", ( 0, 520, 0 ), ( 0, -520, 0 ) ), ( "South Lane", ( 0, -520, 0 ), ( 0, 520, 0 ) ),
                ( "Middle", ( 0, 0, 0 ), ( 0, 688, BM.FLOOR ) ) ]


def callouts():
    out = []
    for name, n0, n1 in ( ( "NORTH WEST", 450, 832 ), ( "RED YARD", -450, 450 ), ( "SOUTH WEST", -832, -450 ) ):
        out.append( ( name, -800, -332, n0, n1, -10, 400 ) )
    for name, n0, n1 in ( ( "A SITE", 450, 832 ), ( "BLUE YARD", -450, 450 ), ( "B SITE", -832, -450 ) ):
        out.append( ( name, 332, 800, n0, n1, -10, 400 ) )
    out += [ ( "NORTH ROW", -332, 332, 640, 832, -10, 400 ), ( "NORTH LANE", -332, 332, 419, 640, -10, 400 ),
             ( "WEST STACKS", -332, -116, -419, 419, -10, 400 ), ( "MIDDLE", -116, 116, -419, 419, -10, 400 ),
             ( "EAST STACKS", 116, 332, -419, 419, -10, 400 ), ( "SOUTH LANE", -332, 332, -640, -419, -10, 400 ),
             ( "SOUTH ROW", -332, 332, -832, -640, -10, 400 ) ]
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

MINIMAP_CENTRE = ( 0.0, 0.0 )
MINIMAP_SIZE = 1800.0
MINIMAP_PIXELS = 1024


def write_minimap( models ):
    """ Railhead's radar style: where you can walk grey, low cover darker, the containers and the wall left clear, a
    light line round the edges. North up. """
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "low", "tall" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    shapes = sorted( R.collision_shapes( models ), key=lambda pts: -float( np.ptp( pts[:, 0] ) * np.ptp( pts[:, 1] ) ) )
    for pts in shapes:
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = R.hull_2d( pts[:, :2] )
        if len( outline ) < 3:
            continue
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if z0 > 100:
            continue
        if -24 <= z1 <= 18:
            draws["walk"].polygon( screen, fill=255 )
        elif z0 < 72 and z1 > 18:
            draws["low" if z1 < 100 else "tall"].polygon( screen, fill=255 )
    walk, low, tall = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "low", "tall" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    E, N = np.meshgrid( cols, rows )
    inside = ( E > PLAY[0] ) & ( E < PLAY[1] ) & ( N > PLAY[2] ) & ( N < PLAY[3] )
    walk &= inside
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[low & inside] = ( 64, 68, 74, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    shown = ( walk | ( low & inside ) ) & ~tall
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
# The scene (as Lowtide's)

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
    """ A TeamSpawnPoint facing the yard's middle. """
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
    ( "boxyard_yard", "Yard", True, True ), ( "boxyard_containers", "Containers", True, True ),
    ( "boxyard_props", "Props", True, True ), ( "boxyard_backdrop", "Backdrop", False, True ),
]


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return K.game_object( ids, name, key, components=components )


def drum_object( e, n, colour, yaw ):
    """ A drum's model where props() put its hull. It has no collider of its own: the Props model's hull stops things. """
    key = f"world/drum/{e}/{n}"
    return K.game_object( ids, f"Drum {colour}", key, K.to_world( ( e, n, 0.0 ) ), K.yaw_rotation( yaw ), components=[
        K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615,
                     Model=f"{OIL_DRUM_DIR}/oil_drum_{colour}.vmdl", RenderType="On", Tint="1,1,1,1" ) ] )


def cone_object( name, at, rotation ):
    """ A cone's model where props() put its collision. It has no collider of its own: the Props model's hulls stop things. """
    key = f"world/cone/{at[0]:g}/{at[1]:g}"
    return K.game_object( ids, name, key, K.to_world( at ), rotation, components=[
        K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615,
                     Model=TRAFFIC_CONE_MODEL, RenderType="On", Tint="1,1,1,1" ) ] )


def ibc_object( e, n, heading ):
    """ A tote's model where props() put its collision box. It has no collider of its own. """
    key = f"world/ibc/{e}/{n}"
    return K.game_object( ids, "IBC tote", key, K.to_world( ( e, n, 0.0 ) ), K.yaw_rotation( heading ), components=[
        K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615,
                     Model=IBC_TOTE_MODEL, RenderType="On", Tint="1,1,1,1" ) ] )


def bin_object( e, n, heading, colour ):
    """ A bin's model where props() put its collision box. It has no collider of its own. The model's front is +y, which is Frame's y at heading - 90. """
    key = f"world/bin/{e}/{n}"
    return K.game_object( ids, f"Bin {colour}", key, K.to_world( ( e, n, 0.0 ) ), K.yaw_rotation( heading - 90.0 ), components=[
        K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615,
                     Model=f"{WHEELIE_BIN_DIR}/wheelie_bin_{colour}.vmdl", RenderType="On", Tint="1,1,1,1" ) ] )


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


def write_scene( written, light_list, probe_list, tops ):
    world = K.game_object( ids, "Boxyard", "world", children=[
        *( model_object( title, f"world/{name}", name, collide, shadows )
           for name, title, collide, shadows in SCENE_MODELS if name in written ),
        *( drum_object( *placed ) for placed in DRUMS ),
        *( cone_object( *placed ) for placed in CONES ),
        *( ibc_object( *placed ) for placed in IBCS ),
        *( bin_object( *placed ) for placed in BINS ) ] )
    light_objects = [
        K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
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
        zone_object( "buyzone_t", "buy/t", ( -e1, -e0, -n1, -n0, z0, z1 ), "1,0.18,0.2,1", "Red Team Buy Zone",
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
    # Player clips over every container (from its roof up) and over the wall, so nobody stands on them.
    clip_objects = []
    for name, F, top in tops:
        key = f"clip/{name}"
        centre = F.p( 0.0, 0.0, ( top + 1000.0 ) / 2 )
        clip_objects.append( K.game_object( ids, f"Player Clip {name}", key, K.to_world( centre ), K.yaw_rotation( F.heading - 90.0 ),
                                            tags="playerclip", components=[
            box_collider( f"{key}/box", ( BM.LENGTH, BM.WIDTH, 1000.0 - top ), trigger=False ) ] ) )
    for name, box in ( ( "East Wall", ( 790, 880, -880, 880, WALL_H, 1000 ) ), ( "West Wall", ( -880, -790, -880, 880, WALL_H, 1000 ) ),
                       ( "North Wall", ( -880, 880, 822, 880, WALL_H, 1000 ) ), ( "South Wall", ( -880, 880, -880, -822, WALL_H, 1000 ) ) ):
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
                         Description="A walled container yard at a port terminal: two rows of shipping containers along its "
                                     "walls and four stacks round an open middle, for close, fast fights.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # Railhead's sun and sky: an early autumn afternoon, the sun 38 degrees up from the south-south-west.
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor="1.32,1.08,0.82,1", ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.42,0.48,0.58,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="1,1,1,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.75", StartDistance=2500,
                         EndDistance=40000, FalloffExponent=1.5, Height=9000, VerticalFalloffExponent=1.2 ),
        ] ),
        look_object(),
        world,
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in probe_list ] ),
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
                "AgentHeight": 64, "AgentRadius": 16, "AgentStepSize": 18, "AgentMaxSlope": 40, "ExcludedBodies": "zone",
                "IncludedBodies": "", "DeferGeneration": False, "CustomBounds": True,
                "Bounds": { "Mins": K.vec( K.to_world( ( PLAY[1], PLAY[2], -40 ) ) ),
                            "Maxs": K.vec( K.to_world( ( PLAY[0], PLAY[3], NAV_TOP ) ) ) },
            },
        },
        "ResourceVersion": 3,
        "Title": TITLE,
        "Description": None,
        "__references": [],
        "__version": 3,
    }
    from map_daylight import apply_profile
    apply_profile( scene )
    SCENE_FILE.parent.mkdir( parents=True, exist_ok=True )
    K.write_text( SCENE_FILE, json.dumps( scene, indent=2 ), newline=None )
    print( f"wrote {SCENE_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------

def build():
    """ Every model by name, and the containers' tops and insides. """
    boxes, tops, insides = containers()
    models = {
        "boxyard_yard": yard(),
        "boxyard_containers": boxes,
        "boxyard_props": props(),
        "boxyard_backdrop": backdrop(),
    }
    for model in models.values():
        configure( model )
    return models, tops, insides


def preview_colours():
    """ The flat preview's colours: each drawn material's mean colour, the flat paints' own. """
    for paint in BM.all_paints():
        if paint in BM.PAINTED:
            PV._colours[paint] = np.array( BM.PAINTED[paint][0] ) / 255.0
            continue
        path = BM.OUT_DIR / f"{paint}_color.jpg"
        if path.exists():
            small = Image.open( path ).convert( "RGB" ).resize( ( 64, 32 ) )
            PV._colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0


def write_map_art( models ):
    """ The menus' picture, a stand-in until there's an in-engine capture: over the south-west corner, looking across the
    yard to the north-east, 1920 x 1080. """
    preview_colours()
    opaque, glass = PV.triangles( models ), PV.triangles( models, glass=True )
    image = PV.perspective( opaque, glass, ( -900, -1100, 520 ), ( 100, 100, 40 ), size=( 960, 540 ), fov=70 )
    MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
    image.resize( ( 1920, 1080 ), Image.LANCZOS ).convert( "RGB" ).save( MAP_ART_FILE )
    print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", metavar="DIR", help="also write the reach grid's picture to this folder" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture" )
    args = parser.parse_args()

    missing = [ p for p in BM.all_paints() if not ( BM.OUT_DIR / f"{p}.vmat" ).exists() ]
    if missing:
        print( f"run Tools/boxyard_materials.py first: no material for {', '.join( missing )}" )
    models, tops, insides = build()
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
    light_list = lights( insides )
    probe_list = probes( insides )
    print( f"{len( light_list )} lights, {len( probe_list )} probes" )

    solid = [ models[name] for name, _, collide, _ in SCENE_MODELS if collide and name in models ]
    print( "checking spots:" )
    problems = R.check_spots( R.collision_aabbs( solid ), all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    out = Path( args.preview ) if args.preview else None
    if out:
        out.mkdir( parents=True, exist_ok=True )
    bounds = ( PLAY[0], PLAY[1], PLAY[2], PLAY[3] + 8 )
    cut_off = R.check_reach( solid, all_spots(), out / "reach.png" if out else None, bounds=bounds )
    print( f"  {cut_off} spot(s) cut off from the spawns" )
    seen = R.check_retakes_sight( R.Blockers( solid ), RETAKES )
    print( f"  {seen} Retakes pair(s) in sight of each other" )

    if not args.no_scene:
        write_minimap( solid )
        write_scene( written, light_list, probe_list, tops )
    if args.art:
        write_map_art( list( models.values() ) )
    if out:
        preview_colours()
        opaque, glass = PV.triangles( list( models.values() ) ), PV.triangles( list( models.values() ), glass=True )
        for name, eye, target in ( ( "west", ( -1050, 0, 260 ), ( 300, 0, 40 ) ), ( "aerial", ( 0, -1400, 1900 ), ( 0, 0, 0 ) ),
                                   ( "lane", ( -700, 520, 64 ), ( 400, 520, 64 ) ) ):
            PV.perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=75 ).convert( "RGB" ).save( out / f"{name}.png" )
            print( f"wrote {out / f'{name}.png'}" )


if __name__ == "__main__":
    main()
