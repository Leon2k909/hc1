"""
Ridgeback's buildings, built by script like the rest of the map (Tools/ridgeback_map.py): each is one model made of
boxes, painted with Tools/building_textures.py's materials, whose collision is the same boxes. So what you see is what
stops you, the bots and the bullets.

    python Tools/ridgeback_buildings.py [--measure] [--place] [--preview <png>]

The first is the Town House, north-east of Town's crossroads: a two-storey village house of rendered brick under a clay
tile roof, 42 by 30 feet. It has three doors (front, back and side), two rooms at the front and two at the back on each
floor, a straight stair, doors in every doorway and glazed casement windows with shutters.

- Writes Assets/models/buildings/<name>/<name>.obj (the render mesh), <name>_roof.obj (the roof's collision) and
  <name>.vmdl; the models of its doors and window panes beside them (<name>_door_outer, _door_inner, _pane and
  _pane_broken_<n>, each an OBJ and a vmdl, with no collision of their own); Assets/prefabs/buildings/<name>.prefab
  (a ModelRenderer and a static ModelCollider, with the doors, panes and window clips as children); and
  Assets/prefabs/buildings/glass_shatter.prefab (a breaking pane's shards). ModelDoc reads an OBJ as Y-up: model
  (X, Y, Z) is written as OBJ (Y, Z, X), as in Tools/ks74u_worldmodel.py.
- Collision is every structural box (PhysicsShapeBox): walls, floors, stairs, the stairwell's low wall, the plinth and
  steps, the porch roof and the chimney. Window and door frames, sashes, sills, surrounds, shutters, gutters and
  downpipes are only for the eye.
- Doors (Door, door_leaf) are four-panel leaves with lever handles, each an object in the prefab with a
  TerrorTown.FuncDoorRotating that swings it 90 degrees away from whoever opens it, and a wooden box collider that
  moves with it. check_swings stops the script if any door, turned either way, would meet anything drawn or another
  door's swing.
- Windows are pairs of casement sashes, six panes of glass to a window (window_panes). Each pane is an object of its
  own (Facepunch.BreakableGlass, tagged glass): a bullet, a blast or something thrown breaks it, leaving a jagged rim
  in the sash (one of BROKEN_PANES), and throws its shards (glass_shatter.prefab). The panes' colliders tile the whole
  opening, frame and sashes too, so nothing goes through a window without breaking a pane. Sight checks see through
  the glass, and a round through it isn't a wallbang.
- One object tagged playerclip holds a box in each window, so nobody climbs in or out through a broken one. Bullets,
  grenades and sight checks pass it (the collision rules' and traces' playerclip rules).
- The roof's collision is one convex hull from the upper ceiling to the tiles (PhysicsHullFile), plus a box under each
  verge. So there's no attic floor for the navmesh to find (a walkable island nobody can reach), and the roof is 42
  degrees, steeper than the navmesh's 40, so nothing walks on it.
- Model space: +X points out of the front door, +Y is on your right as you face the front, and the origin is on the
  ground floor at the middle of the footprint. The code draws in plan coordinates: a along the front, from its left
  end as you face it, b in from the front, z up from the ground floor (to_model turns them into model space).
- PLACEMENTS says where each building stands in ridgeback.scene. --measure reads the ground under each one from
  Tools/ridgeback_map.py's terrain and prints where it stands (the ground floor 10 units over the highest ground), how
  high each doorstep is, how close it comes to a road, and whether any of its footprint is grass ground (grass is
  scattered on meadow and dry meadow, and would grow up through the floor).
- --place writes them into ridgeback.scene there: a prefab instance each under the scene's "Buildings" object, which
  it replaces and leaves the rest of the hand-edited scene alone. Close the scene in the editor first, or saving it
  there puts the old buildings back.
- Units are inches: storeys 10 feet floor to floor, doors 50 by 88, windows 44 by 60 with sills 34 above the floor,
  stairs 8 up and 11 along.
"""
import argparse
import json
import math
import uuid
from collections import defaultdict
from pathlib import Path

import numpy as np

import building_textures as BT

ROOT = Path( __file__ ).resolve().parent.parent
ASSETS = ROOT / "Assets"
NAMESPACE = uuid.UUID( "0d8f7b52-3a64-4b5e-9c1d-6a2f4e8b9c70" )


def gid( key ):
    return str( uuid.uuid5( NAMESPACE, key ) )


# ---------------------------------------------------------------------------------------------------------------------
# Mesh and collision

def normalise( v ):
    v = np.asarray( v, float )
    return v / np.linalg.norm( v )


def face_uv( point, normal, paint ):
    """ World-scale UVs (v up the picture), as seen from in front of the face: up is uphill along the face (+X on a
    floor or ceiling), right is to your right looking at it. """
    n = normalise( normal )
    if abs( n[2] ) > 0.999:
        up = np.array( ( 1.0, 0.0, 0.0 ) )
    else:
        up = normalise( np.array( ( 0.0, 0.0, 1.0 ) ) - n[2] * n )
    right = np.cross( -n, up )
    scale = BT.tile_units( paint )
    return ( float( np.dot( point, right ) / scale ), float( np.dot( point, up ) / scale ) )


def newell( points ):
    """ A polygon's area vector: along its normal, as long as twice its area. """
    total = np.zeros( 3 )
    for p, q in zip( points, points[1:] + points[:1] ):
        total += np.cross( p, q )
    return total


class Model:
    """ Polygons by paint, the collision shapes, and every box drawn (solids, for checking the doors' swings). A
    building's also lists the objects that go in its prefab beside it: doors (Door), window panes and player clips. """

    def __init__( self ):
        self.polygons = defaultdict( list )     # paint -> [ ( points, normal, uvs or None ) ]
        self.boxes = []                          # ( centre, size, angles, surface )
        self.hull = None                         # points and faces of the roof's hull
        self.solids = []                         # ( centre, axes as columns, half sizes )
        self.doors = []
        self.panes = []                          # dicts, see window_panes
        self.clips = []

    def polygon( self, paint, points, normal=None, uvs=None ):
        """ A flat polygon, counter-clockwise seen from the front, drawn as a fan from its first point. Given a normal,
        it's turned to face that way whichever way it was listed. uvs, one per point, replace the world-scale mapping
        (face_uv): a decal's are 0..1 across it. """
        points = [ np.asarray( p, float ) for p in points ]
        if normal is None:
            normal = np.cross( points[1] - points[0], points[2] - points[0] )
        elif np.dot( newell( points ), normal ) < 0:
            points = points[::-1]
            uvs = uvs[::-1] if uvs is not None else None
        self.polygons[paint].append( ( points, normalise( normal ), uvs ) )

    def add( self, other, origin, axes ):
        """ Another model's polygons, placed with its x, y and z along axes (model-space vectors) from origin. """
        turn = np.column_stack( axes )
        for paint, items in other.polygons.items():
            for points, normal, uvs in items:
                self.polygons[paint].append( ( [ origin + turn @ p for p in points ], turn @ normal, uvs ) )

    def cylinder( self, p0, p1, radius, paint, sides=12 ):
        """ A round bar from p0 to p1, capped at both ends. """
        p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
        axis = normalise( p1 - p0 )
        u = normalise( np.cross( axis, ( 0.0, 0.0, 1.0 ) if abs( axis[2] ) < 0.9 else ( 1.0, 0.0, 0.0 ) ) )
        v = np.cross( axis, u )
        ring = [ u * math.cos( 2 * math.pi * k / sides ) + v * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
        for k in range( sides ):
            a, b = ring[k], ring[( k + 1 ) % sides]
            self.polygon( paint, [ p0 + radius * a, p0 + radius * b, p1 + radius * b, p1 + radius * a ], a + b )
        self.polygon( paint, [ p1 + radius * a for a in ring ], axis )
        self.polygon( paint, [ p0 + radius * a for a in ring ], -axis )

    def box( self, lo, hi, paints, surface=None, skip=() ):
        """ An axis-aligned box in model space. paints is one paint or { face: paint } with faces '+x', '-x', '+y', '-y',
        '+z', '-z' (and 'default'); a face painted None, or listed in skip, isn't drawn. surface adds it to the
        collision. """
        lo, hi = np.minimum( lo, hi ).astype( float ), np.maximum( lo, hi ).astype( float )
        if np.any( hi - lo < 1e-6 ):
            return
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        faces = {
            "+x": [ ( x1, y0, z0 ), ( x1, y1, z0 ), ( x1, y1, z1 ), ( x1, y0, z1 ) ],
            "-x": [ ( x0, y1, z0 ), ( x0, y0, z0 ), ( x0, y0, z1 ), ( x0, y1, z1 ) ],
            "+y": [ ( x1, y1, z0 ), ( x0, y1, z0 ), ( x0, y1, z1 ), ( x1, y1, z1 ) ],
            "-y": [ ( x0, y0, z0 ), ( x1, y0, z0 ), ( x1, y0, z1 ), ( x0, y0, z1 ) ],
            "+z": [ ( x0, y0, z1 ), ( x1, y0, z1 ), ( x1, y1, z1 ), ( x0, y1, z1 ) ],
            "-z": [ ( x0, y1, z0 ), ( x1, y1, z0 ), ( x1, y0, z0 ), ( x0, y0, z0 ) ],
        }
        for face, points in faces.items():
            paint = paints.get( face, paints.get( "default" ) ) if isinstance( paints, dict ) else paints
            if paint is None or face in skip:
                continue
            self.polygon( paint, points )
        if surface:
            self.boxes.append( ( ( lo + hi ) / 2, hi - lo, ( 0.0, 0.0, 0.0 ), surface ) )
        self.solids.append( ( ( lo + hi ) / 2, np.eye( 3 ), ( hi - lo ) / 2 ) )

    def oriented_box( self, centre, axes, size, paints, surface=None ):
        """ A box turned by axes (its own x, y and z as model-space vectors: orthonormal, right-handed), size along
        each. paints as for box, with faces named along the box's own axes. """
        centre = np.asarray( centre, float )
        ax = [ normalise( a ) for a in axes ]
        h = np.asarray( size, float ) / 2

        def corner( sx, sy, sz ):
            return centre + ax[0] * sx * h[0] + ax[1] * sy * h[1] + ax[2] * sz * h[2]

        faces = {
            "+x": [ corner( 1, -1, -1 ), corner( 1, 1, -1 ), corner( 1, 1, 1 ), corner( 1, -1, 1 ) ],
            "-x": [ corner( -1, 1, -1 ), corner( -1, -1, -1 ), corner( -1, -1, 1 ), corner( -1, 1, 1 ) ],
            "+y": [ corner( 1, 1, -1 ), corner( -1, 1, -1 ), corner( -1, 1, 1 ), corner( 1, 1, 1 ) ],
            "-y": [ corner( -1, -1, -1 ), corner( 1, -1, -1 ), corner( 1, -1, 1 ), corner( -1, -1, 1 ) ],
            "+z": [ corner( -1, -1, 1 ), corner( 1, -1, 1 ), corner( 1, 1, 1 ), corner( -1, 1, 1 ) ],
            "-z": [ corner( -1, 1, -1 ), corner( 1, 1, -1 ), corner( 1, -1, -1 ), corner( -1, -1, -1 ) ],
        }
        for face, points in faces.items():
            paint = paints.get( face, paints.get( "default" ) ) if isinstance( paints, dict ) else paints
            if paint is not None:
                self.polygon( paint, points )
        if surface:
            self.boxes.append( ( centre, np.asarray( size, float ), angles_of( ax ), surface ) )
        self.solids.append( ( centre, np.column_stack( ax ), h ) )

    def beam( self, p0, p1, size, paint ):
        """ A box from p0 to p1 (model space), size ( across it along +Y, and the third way ). """
        p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
        x_axis = normalise( p1 - p0 )
        y_axis = normalise( np.array( ( 0.0, 1.0, 0.0 ) ) - x_axis[1] * x_axis )
        z_axis = np.cross( x_axis, y_axis )
        self.oriented_box( ( p0 + p1 ) / 2, ( x_axis, y_axis, z_axis ), ( np.linalg.norm( p1 - p0 ), *size ), paint )


def rotation_matrix( pitch, yaw, roll ):
    """ The matrix of s&box's Rotation.From( pitch, yaw, roll ) (columns: the turned x, y and z axes). """
    sp, cp = math.sin( math.radians( pitch ) / 2 ), math.cos( math.radians( pitch ) / 2 )
    sy, cy = math.sin( math.radians( yaw ) / 2 ), math.cos( math.radians( yaw ) / 2 )
    sr, cr = math.sin( math.radians( roll ) / 2 ), math.cos( math.radians( roll ) / 2 )
    x, y, z, w = ( sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy,
                   cr * cp * cy + sr * sp * sy )
    return np.array( [
        [ 1 - 2 * ( y * y + z * z ), 2 * ( x * y - z * w ), 2 * ( x * z + y * w ) ],
        [ 2 * ( x * y + z * w ), 1 - 2 * ( x * x + z * z ), 2 * ( y * z - x * w ) ],
        [ 2 * ( x * z - y * w ), 2 * ( y * z + x * w ), 1 - 2 * ( x * x + y * y ) ],
    ] )


def angles_of( axes ):
    """ Pitch, yaw and roll (degrees) that turn the model's axes onto these, checked against rotation_matrix. """
    m = np.column_stack( axes )
    pitch = math.degrees( math.asin( max( -1.0, min( 1.0, -m[2, 0] ) ) ) )
    yaw = math.degrees( math.atan2( m[1, 0], m[0, 0] ) )
    roll = math.degrees( math.atan2( m[2, 1], m[2, 2] ) )
    assert np.allclose( rotation_matrix( pitch, yaw, roll ), m, atol=1e-6 ), ( m, pitch, yaw, roll )
    return ( pitch, yaw, roll )


# ---------------------------------------------------------------------------------------------------------------------
# The Town House

LENGTH, DEPTH = 504.0, 360.0         # along the front (a) and front to back (b)
EXT = 10.0                            # outside wall thickness (inside walls are 6)
FOUNDATION = -48.0                    # how far the walls and floor go below the ground floor
FLOORS = ( 0.0, 120.0 )               # the storeys' floors
CEILINGS = ( 112.0, 232.0 )           # and ceilings (the upper floor is 8 thick)
PLINTH_TOP, PLINTH_OUT = 18.0, 2.0
BAND = ( 112.0, 122.0, 1.5 )          # the string course between the storeys: bottom, top, how far it stands out
WINDOW = ( 44.0, 34.0, 60.0 )         # width, sill over the floor, height
DOOR = ( 50.0, 88.0 )                 # width, height
INNER_DOOR = ( 44.0, 84.0 )
SURROUND = ( 4.0, 0.75 )              # the pale band round the windows and doors: width, how far it stands out
PITCH = 42.0                          # the roof: steeper than the navmesh's 40 degrees
EAVE = 20.0                           # how far the roof reaches past the front and back walls
VERGE = 12.0                          # and past the gable walls
EAVE_TOP = 238.0                      # the roof's top surface at the eave's edge
ROOF_THICK = 6.0
STEP_RISE, STEP_RUN = 8.0, 11.0
STEPS = int( round( ( FLOORS[1] - FLOORS[0] ) / STEP_RISE ) ) - 1     # the fifteenth step is the upper floor itself
# The flight's foot and its lane along the back wall of the stair hall. The navmesh keeps its agents' radius (16) from
# every wall and drop, so the flight needs room at both ends: with 6 at its foot and 28 at its top it was an island that
# no bot could reach. Now it has 40 at its foot and 50 at its top.
STAIR = dict( a0=290.0, b0=302.0, b1=DEPTH - EXT )
# The opening in the upper floor over the flight (a): from its third step (the second has 96 of headroom) to its top.
STAIRWELL = ( STAIR["a0"] + 2 * STEP_RUN, STAIR["a0"] + STEPS * STEP_RUN )

# Openings in the outside walls: wall -> [ ( storey, kind, centre along the wall ) ]. The front and back run along a,
# the sides along b.
OPENINGS = {
    "front": [ ( 0, "window", 100 ), ( 0, "window", 256 ), ( 0, "door", 346 ), ( 0, "window", 445 ),
               ( 1, "window", 100 ), ( 1, "window", 256 ), ( 1, "window", 346 ), ( 1, "window", 445 ) ],
    "back": [ ( 0, "window", 84 ), ( 0, "door", 204 ), ( 1, "window", 84 ), ( 1, "window", 204 ), ( 1, "window", 400 ) ],
    "left": [ ( 0, "window", 105 ), ( 0, "window", 278 ), ( 1, "window", 105 ), ( 1, "window", 278 ) ],
    "right": [ ( 0, "window", 105 ), ( 0, "door", 244 ), ( 1, "window", 105 ), ( 1, "window", 244 ) ],
}

# Which jamb each outside door hangs on: "lo" is the end of the opening nearer the start of the wall's run (a for the
# front and back, b for the sides).
OUTER_HINGES = { "front": "lo", "back": "hi", "right": "lo" }
DOOR_NAMES = { "front": "Front Door", "back": "Back Door", "right": "Side Door" }

# Inside walls: ( runs along, run, across, [ ( storey, door centre, the jamb its door hangs on ) ] ).
PARTITIONS = [
    ( "a", ( EXT, LENGTH - EXT ), ( 200.0, 206.0 ), [ ( 0, 124, "lo" ), ( 0, 424, "hi" ), ( 1, 424, "hi" ) ] ),  # front rooms | back
    ( "b", ( 206.0, DEPTH - EXT ), ( 244.0, 250.0 ), [ ( 0, 244, "hi" ), ( 1, 244, "hi" ) ] ),                 # kitchen | stair hall
    ( "b", ( EXT, 200.0 ), ( 190.0, 196.0 ), [ ( 0, 150, "hi" ), ( 1, 150, "hi" ) ] ),                         # the front rooms
]

# Doors (see Door): the doorways' wooden linings, then the gaps round a shut leaf. The hinge gap is at the leaf's
# rounded edge, which never swings out of it.
LINING = 2.0
DOOR_GAPS = dict( hinge=0.25, latch=0.125, floor=0.375, head=0.25 )
PIVOT_HEIGHT = 42.0                     # a door's origin on its hinge line, over the floor: where its sounds come from
HANDLE_HEIGHT, BACKSET = 39.0, 2.375    # the lever handles: over the floor, and in from the latch edge
ROSE = ( 1.1, 0.3 )                     # a handle's round plate on the leaf: radius, thickness
LEVER = ( 4.75, 0.3, 2.1 )              # its lever: length towards the hinge, radius, and how far out from the face
PANEL_RECESS = 0.375                    # how far a leaf's panels sit back from each face
# Four-panel leaves: thickness, then the widths of the stiles, the muntin between the panels, and the top, lock and
# bottom rails. The outside doors are painted green like the shutters, the inside ones varnished like their linings.
LEAVES = {
    "outer": dict( thick=1.75, stile=4.5, muntin=4.0, top=4.5, lock=7.0, bottom=8.0, paint="trim_green" ),
    "inner": dict( thick=1.375, stile=4.0, muntin=3.5, top=4.0, lock=6.0, bottom=7.0, paint="trim_brown" ),
}
OPEN_DURATION, CLOSE_DURATION = 0.9, 0.75
# How far each move has gone (0-1) over its time (0-1), as MapMover's curves: pushed open and slowing as it goes;
# pulled shut from half speed, speeding up until it meets the frame (door_close.sound is the latch).
OPEN_CURVE = [ ( k / 8, 1 - ( 1 - k / 8 ) ** 2 ) for k in range( 9 ) ]
CLOSE_CURVE = [ ( k / 8, ( k / 8 + ( k / 8 ) ** 2 ) / 2 ) for k in range( 9 ) ]
DOOR_SOUNDS = dict( OpenSound="sounds/buildings/door_open.sound", CloseSound="sounds/buildings/door_swing.sound",
                    CloseFinishedSound="sounds/buildings/door_close.sound" )

# Windows: a pair of casement sashes in each frame, meeting in the middle, three panes up each (see sashes).
WINDOW_FRAME = 2.5                      # the frame's face width
SASH, BAR = 1.75, 0.75                  # the sashes' stiles and rails, and the glazing bars
PANES_UP = 3
GLASS = 0.16                            # the glass's thickness (4 mm)
GLASS_IN = 0.7                          # the glass's plane, in from the sashes' outside face
REBATE = 0.25                           # how far the glass reaches into the sashes and bars round it
GLASS_COLLIDER = 0.5                    # the panes' colliders' thickness
SHARDS_PER_FOOT = 22.0                  # glass shards thrown per square foot of a pane when it breaks
BROKEN_PANES = 3                        # how many jagged edges a broken pane can leave (one picked per pane)
CLIP_THICK = 3.0                        # the windows' player clips, across the wall where the frame stands
GLASS_SOUND = "sounds/buildings/glass_break.sound"
SHATTER_PREFAB = "prefabs/buildings/glass_shatter.prefab"

# Paints
OUTSIDE, TRIM, INSIDE = "render_ochre", "render_pale", "whitewash"
STONE, FRAME, WOOD, SHUTTER = "concrete", "trim_white", "trim_brown", "shutter_green"
GROUND_FLOOR, UPPER_FLOOR, ROOF, CHIMNEY, METAL = "quarry_tiles", "floorboards", "roof_tiles", "brick", "metal"
HANDLE, GLASS_PAINT = "iron_black", "glass_clear"

# Plan directions as model faces: a runs along +Y, b runs in from the front (-X).
FACE = { "+a": "+y", "-a": "-y", "+b": "-x", "-b": "+x", "+z": "+z", "-z": "-z" }
FACE_VECTOR = { "+x": np.array( ( 1.0, 0.0, 0.0 ) ), "-x": np.array( ( -1.0, 0.0, 0.0 ) ),
                "+y": np.array( ( 0.0, 1.0, 0.0 ) ), "-y": np.array( ( 0.0, -1.0, 0.0 ) ) }
ALONG = { "a": FACE_VECTOR["+y"], "b": FACE_VECTOR["-x"] }      # a wall's run, in model space
UP = np.array( ( 0.0, 0.0, 1.0 ) )
STOREYS = ( "Ground", "Upper" )


def to_model( a, b, z ):
    return np.array( ( DEPTH / 2 - b, a - LENGTH / 2, z ) )


def to_plan( p ):
    return ( p[1] + LENGTH / 2, DEPTH / 2 - p[0], p[2] )


def plan_box( model, lo, hi, paints, surface=None, skip=() ):
    """ A box given in plan coordinates ( a, b, z ); faces in paints and skip are plan faces ('+a', '-b', ...). """
    faces = { FACE.get( k, k ): v for k, v in paints.items() } if isinstance( paints, dict ) else paints
    model.box( to_model( *lo ), to_model( *hi ), faces, surface, [ FACE[k] for k in skip ] )


def plan_polygon( model, paint, points, both_sides=False ):
    """ A polygon given in plan coordinates, counter-clockwise seen from the front; both_sides draws its back too. """
    model.polygon( paint, [ to_model( *p ) for p in points ] )
    if both_sides:
        model.polygon( paint, [ to_model( *p ) for p in points[:1] + points[:0:-1] ] )


def overlaps( p, q, gap=0.0 ):
    """ Whether two ( r0, r1, z0, z1 ) rectangles overlap, or come within gap of each other along r. """
    return p[0] < q[1] + gap and q[0] < p[1] + gap and p[2] < q[3] and q[2] < p[3]


class Wall:
    """ A straight wall: run ( r0, r1 ) along axis ('a' or 'b'), across ( d0, d1 ) on the other, z0 to z1. outward is
    the plan direction its outside faces ('-b' for the front), None for an inside wall. """

    def __init__( self, axis, run, across, z, outward=None, name=None ):
        self.axis, self.run, self.across, self.z, self.outward, self.name = axis, run, across, z, outward, name
        self.openings = []            # ( r0, r1, z0, z1, kind )

    def add( self, centre, width, z0, z1, kind ):
        self.openings.append( ( centre - width / 2, centre + width / 2, z0, z1, kind ) )

    def lo_hi( self, r0, r1, d0, d1, z0, z1 ):
        """ Plan lo/hi of a box: r along the wall, d across it, z up. """
        if self.axis == "a":
            return ( r0, min( d0, d1 ), z0 ), ( r1, max( d0, d1 ), z1 )
        return ( min( d0, d1 ), r0, z0 ), ( max( d0, d1 ), r1, z1 )

    def outer( self ):
        """ The plan coordinate of the outside face, and which way out is along the across axis ( +1 / -1 ). """
        d0, d1 = self.across
        return ( d0, -1.0 ) if self.outward.startswith( "-" ) else ( d1, 1.0 )

    def faces( self ):
        """ Plan face names: the wall's ends, then its two sides. """
        along = ( "-a", "+a" ) if self.axis == "a" else ( "-b", "+b" )
        across = ( "-b", "+b" ) if self.axis == "a" else ( "-a", "+a" )
        return along, across

    def build( self, model, outside, inside, reveal, end, surface="default" ):
        """ The wall in vertical strips between its openings' edges, each strip solid wherever no opening crosses it.
        Openings' sides, heads and sills are painted reveal (a door's sill, outside, is stone), and the wall's two
        ends end (None where they're hidden in another wall). """
        ( r_lo, r_hi ), ( z_lo, z_hi ) = self.run, self.z
        along, across = self.faces()
        if self.outward:
            out_face = self.outward
            in_face = across[1] if out_face == across[0] else across[0]
        else:
            out_face, in_face = across
            outside = inside
        edges = sorted( { r_lo, r_hi } | { r for o in self.openings for r in o[:2] } )
        strips = list( zip( edges, edges[1:] ) )

        def holes( s0, s1 ):
            return sorted( ( z0, z1, kind ) for r0, r1, z0, z1, kind in self.openings if r0 <= s0 and r1 >= s1 )

        def open_beside( r, z0, z1, before ):
            """ Whether the strip before (or after) r is open anywhere between z0 and z1. """
            for s0, s1 in strips:
                if ( s1 == r ) if before else ( s0 == r ):
                    return any( h0 < z1 and h1 > z0 for h0, h1, _ in holes( s0, s1 ) )
            return False

        for s0, s1 in strips:
            bottom = z_lo
            for h0, h1, kind in holes( s0, s1 ) + [ ( z_hi, z_hi, None ) ]:
                if h0 > bottom:
                    top = h0
                    sill = STONE if kind == "door" and self.outward else reveal
                    paints = { out_face: outside, in_face: inside,
                               "+z": sill if top < z_hi else None,
                               "-z": reveal if bottom > z_lo else None,
                               along[0]: end if s0 == r_lo else ( reveal if open_beside( s0, bottom, top, True ) else None ),
                               along[1]: end if s1 == r_hi else ( reveal if open_beside( s1, bottom, top, False ) else None ) }
                    plan_box( model, *self.lo_hi( s0, s1, *self.across, bottom, top ), paints, surface )
                bottom = max( bottom, h1 )


def outer_walls():
    """ The four outside walls, foundation to eaves, with their openings. """
    top = CEILINGS[1]
    walls = {
        "front": Wall( "a", ( 0.0, LENGTH ), ( 0.0, EXT ), ( FOUNDATION, top ), "-b", "front" ),
        "back": Wall( "a", ( 0.0, LENGTH ), ( DEPTH - EXT, DEPTH ), ( FOUNDATION, top ), "+b", "back" ),
        "left": Wall( "b", ( EXT, DEPTH - EXT ), ( 0.0, EXT ), ( FOUNDATION, top ), "-a", "left" ),
        "right": Wall( "b", ( EXT, DEPTH - EXT ), ( LENGTH - EXT, LENGTH ), ( FOUNDATION, top ), "+a", "right" ),
    }
    for name, openings in OPENINGS.items():
        for storey, kind, centre in openings:
            floor = FLOORS[storey]
            if kind == "door":
                walls[name].add( centre, DOOR[0], floor, floor + DOOR[1], kind )
            else:
                width, sill, height = WINDOW
                walls[name].add( centre, width, floor + sill, floor + sill + height, kind )
    return walls


def shutters( wall ):
    """ Each window's pair of shutters, open flat against the wall either side of it, as ( r0, r1, z0, z1 ). Windows
    are taken along the wall, and a pair is hung only where both leaves clear the wall's ends, every other opening's
    surround and the shutters already hung. """
    sw = SURROUND[0]
    r_hi = LENGTH if wall.axis == "a" else DEPTH
    surrounds = [ ( r0 - sw, r1 + sw, z0 - 3, z1 + sw ) for r0, r1, z0, z1, kind in wall.openings ]
    hung = []
    for k, ( r0, r1, z0, z1, kind ) in sorted( enumerate( wall.openings ), key=lambda item: item[1] ):
        if kind != "window":
            continue
        leaf = ( r1 - r0 ) / 2 + 3
        pair = [ ( r0 - sw - leaf, r0 - sw, z0 - 2, z1 + 2 ), ( r1 + sw, r1 + sw + leaf, z0 - 2, z1 + 2 ) ]
        others = [ s for j, s in enumerate( surrounds ) if j != k ] + hung
        if pair[0][0] >= 8 and pair[1][1] <= r_hi - 8 and not any( overlaps( p, q, 2.0 ) for p in pair for q in others ):
            hung += pair
    return hung


def plan_point( wall, r, d, z ):
    """ A point r along the wall and d across it, in model space. """
    return to_model( r, d, z ) if wall.axis == "a" else to_model( d, r, z )


def pane_rows( z0, z1 ):
    """ A window's glass rows, bottom to top, as ( y0, y1 ): inside the frame and the sashes' rails, PANES_UP of them
    between the glazing bars. """
    g0, g1 = z0 + WINDOW_FRAME + SASH, z1 - WINDOW_FRAME - SASH
    high = ( g1 - g0 - ( PANES_UP - 1 ) * BAR ) / PANES_UP
    return [ ( g0 + k * ( high + BAR ), g0 + k * ( high + BAR ) + high ) for k in range( PANES_UP ) ]


def pane_columns( r0, r1 ):
    """ The two sashes' glass along the wall, as ( ( q0, q1 ) of the glass, ( q0, q1 ) of the part of the opening its
    panes' colliders cover: from the opening's edge to the middle, where the sashes meet ). """
    c = ( r0 + r1 ) / 2
    return [ ( ( r0 + WINDOW_FRAME + SASH, c - SASH ), ( r0, c ) ), ( ( c + SASH, r1 - WINDOW_FRAME - SASH ), ( c, r1 ) ) ]


def glass_plane( wall ):
    """ Where the windows' glass stands across the wall: GLASS_IN in from the sashes' outside face, which is flush with
    the frame's. """
    face, out = wall.outer()
    return sum( wall.across ) / 2 + out * ( 1.5 - GLASS_IN )


def sashes( model, wall, r0, r1, z0, z1 ):
    """ A pair of casement sashes in a window's frame, flush with its outside face and meeting in the middle, with
    glazing bars between their panes. The glass isn't part of the house: each pane is an object that breaks
    (window_panes). """
    face, out = wall.outer()
    s_out = sum( wall.across ) / 2 + out * 1.5
    s_in = s_out - out * SASH
    glass = glass_plane( wall )
    rows = pane_rows( z0, z1 )
    bottom, top = z0 + WINDOW_FRAME, z1 - WINDOW_FRAME
    for ( g0, g1 ), _ in pane_columns( r0, r1 ):
        for p0, p1, y0, y1 in ( ( g0 - SASH, g0, bottom, top ), ( g1, g1 + SASH, bottom, top ),
                                ( g0, g1, bottom, bottom + SASH ), ( g0, g1, top - SASH, top ) ):
            plan_box( model, *wall.lo_hi( p0, p1, s_out, s_in, y0, y1 ), FRAME )
        for ( _, y0 ), ( y1, _ ) in zip( rows, rows[1:] ):
            plan_box( model, *wall.lo_hi( g0, g1, glass - 0.5, glass + 0.5, y0, y1 ), FRAME )


def dress_openings( model, wall ):
    """ Frames in the openings, and casement sashes in the windows' frames; and on the outside, the pale surrounds,
    concrete sills and open shutters. """
    face, out = wall.outer()
    middle = sum( wall.across ) / 2
    sw, proud = SURROUND
    s_face = face + out * proud
    for r0, r1, z0, z1, kind in wall.openings:
        # Frames: in the middle of the wall for windows, lining the opening for doors.
        if kind == "window":
            f0, f1, t = middle - 1.5, middle + 1.5, WINDOW_FRAME
        else:
            f0, f1, t = wall.across[0], wall.across[1], LINING
        rails = [ ( r0, r0 + t, z0, z1 ), ( r1 - t, r1, z0, z1 ), ( r0, r1, z1 - t, z1 ) ]
        if kind == "window":
            rails.append( ( r0, r1, z0, z0 + t ) )
            sashes( model, wall, r0, r1, z0, z1 )
            window_panes( model, wall, r0, r1, z0, z1 )
        for q0, q1, y0, y1 in rails:
            plan_box( model, *wall.lo_hi( q0, q1, f0, f1, y0, y1 ), FRAME )

        # Surround: jambs and head, standing out from the wall.
        bottom = z0 - 3.0 if kind == "window" else z0
        for q0, q1, y0, y1 in ( ( r0 - sw, r0, bottom, z1 + sw ), ( r1, r1 + sw, bottom, z1 + sw ), ( r0, r1, z1, z1 + sw ) ):
            plan_box( model, *wall.lo_hi( q0, q1, face, s_face, y0, y1 ), TRIM )

        # Sill: concrete, standing out under the window and a little past the surround.
        if kind == "window":
            plan_box( model, *wall.lo_hi( r0 - sw - 1, r1 + sw + 1, face + out * 3.0, face - out * 2.0, z0 - 2.5, z0 + 0.75 ),
                      STONE )
    for q0, q1, y0, y1 in shutters( wall ):
        plan_box( model, *wall.lo_hi( q0, q1, face, face + out * 1.5, y0, y1 ), SHUTTER )


def plinth_and_steps( model, walls ):
    """ The concrete plinth round the foot of the walls (at the doors, only up to the floor), and a doorstep of two
    steps outside each door. """
    for wall in walls.values():
        face, out = wall.outer()
        inner = wall.faces()[1][1 if out < 0 else 0]           # the plinth's face against the wall
        doors = sorted( ( r0, r1 ) for r0, r1, z0, z1, kind in wall.openings if kind == "door" )
        r_lo, r_hi = ( -PLINTH_OUT, LENGTH + PLINTH_OUT ) if wall.axis == "a" else ( 0.0, DEPTH )
        cuts = [ ( r_lo, r_lo ) ] + doors + [ ( r_hi, r_hi ) ]
        for ( _, s0 ), ( s1, _ ) in zip( cuts, cuts[1:] ):
            plan_box( model, *wall.lo_hi( s0, s1, face, face + out * PLINTH_OUT, FOUNDATION, PLINTH_TOP ), STONE, "default",
                      skip=[ inner ] )
        for r0, r1 in doors:
            plan_box( model, *wall.lo_hi( r0, r1, face, face + out * PLINTH_OUT, FOUNDATION, 0.0 ), STONE, "default",
                      skip=[ inner ] )
            for d0, d1, top in ( ( PLINTH_OUT, 24.0, -6.0 ), ( 24.0, 36.0, -12.0 ) ):
                plan_box( model, *wall.lo_hi( r0 - 8, r1 + 8, face + out * d0, face + out * d1, FOUNDATION, top ), STONE,
                          "default", skip=[ inner ] )


def floors( model ):
    """ The ground floor (a slab down to the foundation), the upper floor round the stairwell, and the top ceiling. """
    plan_box( model, ( EXT, EXT, FOUNDATION ), ( LENGTH - EXT, DEPTH - EXT, FLOORS[0] ),
              { "+z": GROUND_FLOOR, "default": None }, "default" )
    z0, z1 = CEILINGS[0], FLOORS[1]
    s0, s1 = STAIRWELL
    b0 = STAIR["b0"]
    for lo, hi in ( ( ( EXT, EXT, z0 ), ( LENGTH - EXT, b0, z1 ) ),
                    ( ( EXT, b0, z0 ), ( s0, DEPTH - EXT, z1 ) ),
                    ( ( s1, b0, z0 ), ( LENGTH - EXT, DEPTH - EXT, z1 ) ) ):
        faces = { "+z": UPPER_FLOOR, "default": INSIDE }
        if lo[0] == s1:
            faces["-a"] = WOOD                    # the top riser
        plan_box( model, lo, hi, faces, "wood" )
    top = CEILINGS[1]
    plan_polygon( model, INSIDE, [ ( EXT, EXT, top ), ( EXT, DEPTH - EXT, top ), ( LENGTH - EXT, DEPTH - EXT, top ),
                                   ( LENGTH - EXT, EXT, top ) ] )


def string_course( model ):
    z0, z1, out = BAND
    for lo, hi in ( ( ( -out, -out, z0 ), ( LENGTH + out, 2.0, z1 ) ),
                    ( ( -out, DEPTH - 2.0, z0 ), ( LENGTH + out, DEPTH + out, z1 ) ),
                    ( ( -out, 2.0, z0 ), ( 2.0, DEPTH - 2.0, z1 ) ),
                    ( ( LENGTH - 2.0, 2.0, z0 ), ( LENGTH + out, DEPTH - 2.0, z1 ) ) ):
        plan_box( model, lo, hi, TRIM )


def partitions( model ):
    """ The inside walls, their doorways' linings and their doors. """
    count = [ 0, 0 ]
    for axis, run, across, doors in PARTITIONS:
        for storey in ( 0, 1 ):
            wall = Wall( axis, run, across, ( FLOORS[storey], CEILINGS[storey] ) )
            floor = FLOORS[storey]
            for s, centre, hinge in doors:
                if s == storey:
                    wall.add( centre, INNER_DOOR[0], floor, floor + INNER_DOOR[1], "door" )
                    count[storey] += 1
                    r0, r1 = centre - INNER_DOOR[0] / 2, centre + INNER_DOOR[0] / 2
                    model.doors.append( Door( f"door/{axis}{across[0]:g}/{storey}/{centre:g}",
                                              f"{STOREYS[storey]} Floor Door {count[storey]}", "inner", wall, r0, r1,
                                              floor, floor + INNER_DOOR[1], hinge ) )
            wall.build( model, INSIDE, INSIDE, INSIDE, None )
            for r0, r1, z0, z1, kind in wall.openings:
                for q0, q1, y0, y1 in ( ( r0, r0 + LINING, z0, z1 ), ( r1 - LINING, r1, z0, z1 ), ( r0, r1, z1 - LINING, z1 ) ):
                    plan_box( model, *wall.lo_hi( q0, q1, *across, y0, y1 ), WOOD )


def stairs( model ):
    """ A straight flight along the back wall of the stair hall, rising towards the side door: solid steps, each a box
    down to the floor. The fifteenth step is the upper floor itself. """
    a0, b0, b1 = STAIR["a0"], STAIR["b0"], STAIR["b1"]
    for k in range( 1, STEPS + 1 ):
        lo = ( a0 + STEP_RUN * ( k - 1 ), b0, FLOORS[0] )
        hi = ( a0 + STEP_RUN * k, b1, FLOORS[0] + STEP_RISE * k )
        plan_box( model, lo, hi, { "+z": UPPER_FLOOR, "-b": INSIDE, "default": None }, "wood" )
        # The riser: only the top of the step's front shows.
        plan_polygon( model, WOOD, [ ( lo[0], b1, hi[2] - STEP_RISE ), ( lo[0], b0, hi[2] - STEP_RISE ),
                                     ( lo[0], b0, hi[2] ), ( lo[0], b1, hi[2] ) ] )
    end = a0 + STEP_RUN * STEPS
    plan_box( model, ( end, b0, FLOORS[0] ), ( LENGTH - EXT, b1, CEILINGS[0] ), { "-b": INSIDE, "default": None }, "default" )
    # A low wall round the stairwell upstairs, capped with a wooden rail. Along the hall it stops a step short of the
    # top, so the top step opens onto the hall as well as the landing: the landing alone was too tight for the navmesh.
    s0, s1 = STAIRWELL
    z0, z1 = FLOORS[1], FLOORS[1] + 36
    for lo, hi in ( ( ( s0 - 4, b0 - 4, z0 ), ( s1 - STEP_RUN, b0, z1 ) ), ( ( s0 - 4, b0, z0 ), ( s0, b1, z1 ) ) ):
        plan_box( model, lo, hi, INSIDE, "default" )
        plan_box( model, ( lo[0] - 1, lo[1] - 1, z1 ), ( hi[0] + 1, hi[1] + 1, z1 + 2 ), WOOD )


def roof_top( b ):
    """ The height of the roof's top surface over b (plan). """
    run = min( b + EAVE, DEPTH + EAVE - b )
    return EAVE_TOP + math.tan( math.radians( PITCH ) ) * run


def roof( model ):
    """ Two tiled slopes on a ridge along the house, reaching past the walls, with fascias and gutters along the
    eaves, boarded soffits, verges past the gables, ridge tiles and a brick chimney. The collision is a hull from the
    upper ceiling to the tiles over the walls' length, plus a box under each verge. """
    t = math.radians( PITCH )
    ridge_b = DEPTH / 2
    top = roof_top( ridge_b )
    a0, a1 = -VERGE, LENGTH + VERGE
    under = ROOF_THICK / math.cos( t )                 # the tiles' thickness straight down
    for side in ( -1, 1 ):                              # front slope, back slope
        eave_b = -EAVE if side < 0 else DEPTH + EAVE
        wall_b = 0.0 if side < 0 else DEPTH
        top_eave = to_model( LENGTH / 2, eave_b, EAVE_TOP )
        top_ridge = to_model( LENGTH / 2, ridge_b, top )
        # Box axes: x up the slope, z out of the roof, y along the ridge.
        x_axis = normalise( top_ridge - top_eave )
        z_axis = normalise( np.cross( np.array( ( 0.0, 1.0, 0.0 ) ), x_axis ) )
        if z_axis[2] < 0:
            z_axis = -z_axis
        axes = ( x_axis, np.cross( z_axis, x_axis ), z_axis )
        length = np.linalg.norm( top_ridge - top_eave )
        centre = ( top_eave + top_ridge ) / 2 - z_axis * ROOF_THICK / 2
        model.oriented_box( centre, axes, ( length, a1 - a0, ROOF_THICK ), { "+z": ROOF, "default": WOOD } )
        for v0, v1 in ( ( a0, 0.0 ), ( LENGTH, a1 ) ):        # the verges' collision
            verge = centre.copy()
            verge[1] = to_model( ( v0 + v1 ) / 2, 0, 0 )[1]
            model.boxes.append( ( verge, np.array( ( length, v1 - v0, ROOF_THICK ) ), angles_of( axes ), "ceramic" ) )

        # Fascia and gutter along the eave, the soffit under it, and at each end of the eave a board closing the box
        # between the soffit and the tiles (drawn both sides: from under the verge you see its back).
        fascia = ( eave_b - 1.5, eave_b ) if side < 0 else ( eave_b, eave_b + 1.5 )
        plan_box( model, ( a0, fascia[0], CEILINGS[1] - 3 ), ( a1, fascia[1], EAVE_TOP - 1 ), WOOD )
        gutter = ( eave_b - 6.0, eave_b - 1.5 ) if side < 0 else ( eave_b + 1.5, eave_b + 6.0 )
        plan_box( model, ( a0, gutter[0], CEILINGS[1] - 3 ), ( a1, gutter[1], CEILINGS[1] + 1 ), METAL )
        soffit = [ ( a0, eave_b, CEILINGS[1] ), ( a1, eave_b, CEILINGS[1] ), ( a1, wall_b, CEILINGS[1] ), ( a0, wall_b, CEILINGS[1] ) ]
        plan_polygon( model, WOOD, soffit if side > 0 else soffit[::-1] )
        corner = to_plan( top_eave - z_axis * ROOF_THICK )
        for va in ( a0, a1 ):
            plan_polygon( model, WOOD, [ ( va, corner[1], corner[2] ), ( va, wall_b, roof_top( wall_b ) - under ),
                                         ( va, wall_b, CEILINGS[1] ), ( va, eave_b, CEILINGS[1] ), ( va, eave_b, EAVE_TOP ) ],
                          both_sides=True )

    # Gable walls, from the eaves up under the tiles.
    for a, outward in ( ( 0.0, -1 ), ( LENGTH, 1 ) ):
        points = [ ( a, 0.0, CEILINGS[1] ), ( a, DEPTH, CEILINGS[1] ), ( a, DEPTH, roof_top( DEPTH ) - under ),
                   ( a, ridge_b, top - under ), ( a, 0.0, roof_top( 0.0 ) - under ) ]
        plan_polygon( model, OUTSIDE, points if outward > 0 else points[::-1] )

    # Ridge tiles.
    plan_box( model, ( a0, ridge_b - 4.5, top - 5 ), ( a1, ridge_b + 4.5, top + 3.5 ), ROOF )

    # Chimney through the back slope, with a concrete cap.
    c0, c1, d0, d1 = 72.0, 96.0, 214.0, 236.0
    plan_box( model, ( c0, d0, CEILINGS[1] ), ( c1, d1, top + 32 ), { "default": CHIMNEY, "-z": None }, "default" )
    plan_box( model, ( c0 - 3, d0 - 3, top + 32 ), ( c1 + 3, d1 + 3, top + 36 ), STONE, "default" )

    # The hull: ceiling to the tiles, over the walls' length.
    slope = math.tan( t )
    section = [ ( -EAVE - 1.5, CEILINGS[1] ), ( -EAVE - 1.5, EAVE_TOP - slope * 1.5 ), ( ridge_b, top ),
                ( DEPTH + EAVE + 1.5, EAVE_TOP - slope * 1.5 ), ( DEPTH + EAVE + 1.5, CEILINGS[1] ) ]
    n = len( section )
    points = [ to_model( a, b, z ) for a in ( 0.0, LENGTH ) for b, z in section ]
    faces = [ list( range( n ) ), list( range( n, 2 * n ) ) ] + \
            [ [ k, ( k + 1 ) % n, n + ( k + 1 ) % n, n + k ] for k in range( n ) ]
    middle = np.mean( points, axis=0 )
    for k, face in enumerate( faces ):                  # every face turned outwards
        p = [ points[i] for i in face ]
        if np.dot( np.cross( p[1] - p[0], p[2] - p[0] ), np.mean( p, axis=0 ) - middle ) < 0:
            faces[k] = face[::-1]
    model.hull = ( points, faces )


def gutter_pipes( model ):
    """ A downpipe at each corner: from the gutter back under the eave to the wall, and down it to the plinth. """
    bend = CEILINGS[1] - 18
    for a0, a1 in ( ( 2.0, 5.5 ), ( LENGTH - 5.5, LENGTH - 2.0 ) ):
        for wall_b, eave_b, out in ( ( 0.0, -EAVE, -1 ), ( DEPTH, DEPTH + EAVE, 1 ) ):
            near, far = wall_b + out * 1.0, wall_b + out * 4.5
            gutter = eave_b + out * 3.75                # the gutter's middle
            plan_box( model, ( a0, min( near, far ), PLINTH_TOP ), ( a1, max( near, far ), bend + 3.5 ), METAL )
            plan_box( model, ( a0, min( near, gutter ), bend ), ( a1, max( near, gutter ), bend + 3.5 ), METAL )
            plan_box( model, ( a0, gutter - 1.75, bend ), ( a1, gutter + 1.75, CEILINGS[1] - 3 ), METAL )


def porch( model ):
    """ A little tiled roof over the front door, on two brackets. """
    door = next( c for s, k, c in OPENINGS["front"] if k == "door" )
    a0, a1 = door - DOOR[0] / 2 - 14, door + DOOR[0] / 2 + 14
    depth, high, low, thick = 28.0, CEILINGS[0] - 2, CEILINGS[0] - 10, 4.0
    top_wall, top_edge = to_model( ( a0 + a1 ) / 2, 0.0, high ), to_model( ( a0 + a1 ) / 2, -depth, low )
    x_axis = normalise( top_edge - top_wall )
    z_axis = normalise( np.cross( np.array( ( 0.0, 1.0, 0.0 ) ), x_axis ) )
    if z_axis[2] < 0:
        z_axis = -z_axis
    centre = ( top_wall + top_edge ) / 2 - z_axis * thick / 2
    model.oriented_box( centre, ( x_axis, np.cross( z_axis, x_axis ), z_axis ),
                        ( np.linalg.norm( top_edge - top_wall ), a1 - a0, thick ), { "+z": ROOF, "default": WOOD }, "ceramic" )

    def underside( b ):
        """ The porch roof's underside over b (0 at the wall, -depth at its edge). """
        return high + ( high - low ) * b / depth - thick / math.cos( math.atan( ( high - low ) / depth ) )

    for a in ( a0 + 5, a1 - 5 ):
        model.beam( to_model( a, 0.0, underside( 0.0 ) - 1.5 ), to_model( a, 3 - depth, underside( 3 - depth ) - 1.5 ),
                    ( 3.0, 3.0 ), WOOD )
        model.beam( to_model( a, 0.0, high - 34 ), to_model( a, -0.6 * depth, underside( -0.6 * depth ) - 2.5 ),
                    ( 3.0, 3.0 ), WOOD )


def town_house():
    model = Model()
    walls = outer_walls()
    for name, wall in walls.items():
        wall.build( model, OUTSIDE, INSIDE, TRIM, OUTSIDE if wall.axis == "a" else None )
        dress_openings( model, wall )
        for r0, r1, z0, z1, kind in wall.openings:
            if kind == "door":
                model.doors.append( Door( f"door/{name}", DOOR_NAMES[name], "outer", wall, r0, r1, z0, z1,
                                          OUTER_HINGES[name] ) )
    plinth_and_steps( model, walls )
    string_course( model )
    floors( model )
    partitions( model )
    stairs( model )
    roof( model )
    gutter_pipes( model )
    porch( model )
    check_swings( model )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Doors and window glass: objects of their own in the prefab beside the house (write_prefab), with their own models

class Door:
    """ A hinged leaf in a doorway: a TerrorTown.FuncDoorRotating that turns 90 degrees either way, away from whoever
    opens it. Its origin is on the hinge line in the middle of the wall, PIVOT_HEIGHT over the floor. In its own space
    +Y runs along the leaf from the hinge to the latch, +Z is up and +X is out of one face. The leaf's hinge edge is
    rounded about that line (door_leaf), so however far it turns it stays out of the hinge gap. """

    def __init__( self, key, name, kind, wall, r0, r1, z0, z1, hinge ):
        self.key, self.name, self.kind = key, name, kind
        self.thick = LEAVES[kind]["thick"]
        clear0, clear1 = r0 + LINING, r1 - LINING
        self.reach = clear1 - clear0 - DOOR_GAPS["hinge"] - DOOR_GAPS["latch"] - self.thick / 2    # hinge line to latch edge
        self.bottom = DOOR_GAPS["floor"] - PIVOT_HEIGHT
        self.top = z1 - LINING - DOOR_GAPS["head"] - z0 - PIVOT_HEIGHT
        offset = DOOR_GAPS["hinge"] + self.thick / 2
        self.origin = plan_point( wall, clear0 + offset if hinge == "lo" else clear1 - offset, sum( wall.across ) / 2,
                                  z0 + PIVOT_HEIGHT )
        self.y = ALONG[wall.axis] * ( 1.0 if hinge == "lo" else -1.0 )
        self.x = np.cross( self.y, UP )
        self.yaw = math.degrees( math.atan2( self.x[1], self.x[0] ) )

    def axes( self, angle=0.0 ):
        """ Its own axes (model space, as columns) when it's angle degrees open. A positive angle turns +Y towards -X,
        as FuncDoorRotating's TargetRotation does. """
        t = math.radians( angle )
        turn = np.array( [ [ math.cos( t ), -math.sin( t ), 0.0 ], [ math.sin( t ), math.cos( t ), 0.0 ], [ 0.0, 0.0, 1.0 ] ] )
        return np.column_stack( ( self.x, self.y, UP ) ) @ turn

    def boxes( self, angle ):
        """ The leaf from its hinge line on, and its handles' reach either side, when it's angle degrees open, as
        ( centre, axes as columns, half sizes ). """
        axes, h = self.axes( angle ), self.thick / 2
        handle_y, handle_z = self.reach - BACKSET, HANDLE_HEIGHT - PIVOT_HEIGHT
        local = [ ( ( 0.0, self.reach / 2, ( self.bottom + self.top ) / 2 ), ( h, self.reach / 2, ( self.top - self.bottom ) / 2 ) ),
                  ( ( 0.0, handle_y + ( ROSE[0] - LEVER[0] - LEVER[1] ) / 2, handle_z ),
                    ( h + LEVER[2] + LEVER[1], ( ROSE[0] + LEVER[0] + LEVER[1] ) / 2, ROSE[0] ) ) ]
        return [ ( self.origin + axes @ np.array( centre ), axes, np.array( half ) ) for centre, half in local ]


def door_leaf( door ):
    """ A door's leaf in its own space (see Door): two stiles, a top, a lock and a bottom rail and a muntin framing four
    sunk panels, the hinge edge rounded about the hinge line, and a lever handle on each face. """
    leaf = LEAVES[door.kind]
    paint, h, bottom, top = leaf["paint"], door.thick / 2, door.bottom, door.top
    y0, y1 = -h, door.reach                                           # the hinge and latch edges
    s0, s1 = y0 + leaf["stile"], y1 - leaf["stile"]                   # the stiles' inner edges
    m0, m1 = ( y0 + y1 - leaf["muntin"] ) / 2, ( y0 + y1 + leaf["muntin"] ) / 2
    lock = HANDLE_HEIGHT - PIVOT_HEIGHT
    b1, t0, l0, l1 = bottom + leaf["bottom"], top - leaf["top"], lock - leaf["lock"] / 2, lock + leaf["lock"] / 2
    model = Model()
    for q0, q1, z0, z1 in ( ( 0.0, s0, bottom, top ), ( s1, y1, bottom, top ), ( s0, s1, bottom, b1 ), ( s0, s1, t0, top ),
                            ( s0, s1, l0, l1 ), ( m0, m1, b1, l0 ), ( m0, m1, l1, t0 ) ):
        model.box( ( -h, q0, z0 ), ( h, q1, z1 ), paint, skip=( "-y", ) if q0 == 0.0 else () )
    for q0, q1 in ( ( s0, m0 ), ( m1, s1 ) ):
        for z0, z1 in ( ( b1, l0 ), ( l1, t0 ) ):
            model.box( ( PANEL_RECESS - h, q0, z0 ), ( h - PANEL_RECESS, q1, z1 ), paint, skip=( "-y", "+y", "-z", "+z" ) )

    # The rounded hinge edge: half a cylinder about the hinge line, behind the hinge stile.
    ring = [ np.array( ( h * math.sin( a ), -h * math.cos( a ), 0.0 ) ) for a in np.linspace( -math.pi / 2, math.pi / 2, 9 ) ]
    for p, q in zip( ring, ring[1:] ):
        model.polygon( paint, [ p + ( 0, 0, bottom ), q + ( 0, 0, bottom ), q + ( 0, 0, top ), p + ( 0, 0, top ) ], p + q )
    for z, up in ( ( top, 1.0 ), ( bottom, -1.0 ) ):
        model.polygon( paint, [ p + ( 0, 0, z ) for p in ring ], ( 0.0, 0.0, up ) )

    # A lever handle each side: a round plate, a neck out from it, and the lever back towards the hinge.
    y, z = door.reach - BACKSET, lock
    for side in ( 1.0, -1.0 ):
        face, out = side * h, side * ( h + LEVER[2] )
        model.cylinder( ( face, y, z ), ( face + side * ROSE[1], y, z ), ROSE[0], HANDLE, sides=16 )
        model.cylinder( ( face + side * ROSE[1], y, z ), ( out + side * LEVER[1], y, z ), LEVER[1], HANDLE, sides=8 )
        model.cylinder( ( out, y + LEVER[1], z ), ( out, y - LEVER[0], z ), LEVER[1], HANDLE, sides=8 )
    return model


def glass_piece( model, outline, half ):
    """ A flat piece of a pane (outline: ( y, z ) round it, in the pane's space) as its two faces, GLASS apart, with the
    glass's picture mapped once across the whole pane ( half: the pane's half width and height ). """
    hw, hh = half
    for side in ( 1.0, -1.0 ):
        model.polygon( GLASS_PAINT, [ ( side * GLASS / 2, y, z ) for y, z in outline ], ( side, 0.0, 0.0 ),
                       [ ( ( side * y + hw ) / ( 2 * hw ), ( z + hh ) / ( 2 * hh ) ) for y, z in outline ] )


def pane_model( size ):
    """ A whole pane in its own space: centred on the glass, +X out of the wall, +Y along it and +Z up, reaching
    REBATE into the sash all round. """
    hw, hh = size[0] / 2 + REBATE, size[1] / 2 + REBATE
    model = Model()
    glass_piece( model, [ ( -hw, -hh ), ( hw, -hh ), ( hw, hh ), ( -hw, hh ) ], ( hw, hh ) )
    return model


def broken_pane( size, seed ):
    """ What a pane leaves in the sash when it breaks: a rim of glass round the edge, mostly an inch or less, with a
    few long shards left standing and bigger pieces in the corners. """
    rng = np.random.default_rng( seed )
    hw, hh = size[0] / 2 + REBATE, size[1] / 2 + REBATE
    corners = [ np.array( c ) for c in ( ( -hw, -hh ), ( hw, -hh ), ( hw, hh ), ( -hw, hh ) ) ]
    sides = list( zip( corners, corners[1:] + corners[:1] ) )
    inward = [ normalise( ( ( a - b )[1], ( b - a )[0] ) ) for a, b in sides ]
    longest = 0.42 * min( hw, hh )
    rim, shard = [], False                          # ( a point on the edge, the way in, how far in the glass reaches )
    for k, ( a, b ) in enumerate( sides ):
        rim.append( ( a, normalise( inward[k] + inward[k - 1] ), ( REBATE + rng.uniform( 0.6, 2.8 ) ) * math.sqrt( 2 ) ) )
        steps = max( 3, int( round( np.linalg.norm( b - a ) / 1.8 ) ) )
        for i in range( 1, steps ):
            shard = not shard and rng.random() < 0.16
            depth = REBATE + ( rng.uniform( 2.0, longest ) if shard else rng.uniform( 0.25, 1.1 ) )
            rim.append( ( a + ( b - a ) * ( i + rng.uniform( -0.3, 0.3 ) ) / steps, inward[k], depth ) )
    model = Model()
    for ( p, dp, lp ), ( q, dq, lq ) in zip( rim, rim[1:] + rim[:1] ):
        glass_piece( model, [ p, q, q + dq * lq ], ( hw, hh ) )
        glass_piece( model, [ p, q + dq * lq, p + dp * lp ], ( hw, hh ) )
    return model


def window_panes( model, wall, r0, r1, z0, z1 ):
    """ A window's six panes, each an object that breaks by itself (Facepunch.BreakableGlass), and its player clip. The
    panes' colliders tile the whole opening, frame and sashes too, so nothing goes through a window without breaking a
    pane; the clip stops players, whatever's broken. """
    storey = 0 if z0 < FLOORS[1] else 1
    number = 1 + sum( 1 for o in wall.openings if o[4] == "window" and ( o[2] < FLOORS[1] ) == ( storey == 0 ) and o[0] < r0 )
    title = f"{wall.name.capitalize()} {STOREYS[storey]} Window {number}"
    key = f"{wall.name}/{storey}/{( r0 + r1 ) / 2:g}"
    normal = FACE_VECTOR[FACE[wall.outward]]
    flip = float( np.dot( np.cross( UP, normal ), ALONG[wall.axis] ) )     # whether the panes' +Y runs with the wall
    glass = glass_plane( wall )
    rows = pane_rows( z0, z1 )
    cuts = [ z0 ] + [ ( low[1] + high[0] ) / 2 for low, high in zip( rows, rows[1:] ) ] + [ z1 ]
    for k, ( ( g0, g1 ), ( q0, q1 ) ) in enumerate( pane_columns( r0, r1 ) ):
        for j, ( y0, y1 ) in enumerate( rows ):
            middle_r, middle_z = ( g0 + g1 ) / 2, ( y0 + y1 ) / 2
            model.panes.append( dict(
                key=f"pane/{key}/{k}{j}", name=f"{title} Pane {k * len( rows ) + j + 1}", normal=normal,
                position=plan_point( wall, middle_r, glass, middle_z ), size=( g1 - g0, y1 - y0 ),
                collider=( ( 0.0, ( ( q0 + q1 ) / 2 - middle_r ) * flip, ( cuts[j] + cuts[j + 1] ) / 2 - middle_z ),
                           ( GLASS_COLLIDER, q1 - q0, cuts[j + 1] - cuts[j] ) ) ) )
    middle = sum( wall.across ) / 2
    lo, hi = wall.lo_hi( r0, r1, middle - CLIP_THICK / 2, middle + CLIP_THICK / 2, z0, z1 )
    lo, hi = to_model( *lo ), to_model( *hi )
    model.clips.append( dict( key=f"clip/{key}", centre=( lo + hi ) / 2, size=np.abs( hi - lo ) ) )


def overlapping( box, solids, margin=0.01 ):
    """ Which of solids ( centres ( N, 3 ), axes as columns ( N, 3, 3 ), half sizes ( N, 3 ) ) a box overlaps by more
    than margin, by the separating axis test. """
    centre, axes, half = box
    centres, solid_axes, halves = solids
    n = len( centres )
    own = np.broadcast_to( axes.T, ( n, 3, 3 ) )                          # each row one of the box's axes
    theirs = np.transpose( solid_axes, ( 0, 2, 1 ) )
    cross = np.cross( own[:, :, None, :], theirs[:, None, :, :] ).reshape( n, 9, 3 )
    length = np.linalg.norm( cross, axis=2 )
    tests = np.concatenate( ( own, theirs, cross / np.maximum( length, 1e-9 )[..., None] ), axis=1 )
    valid = np.concatenate( ( np.ones( ( n, 6 ), bool ), length > 1e-6 ), axis=1 )
    reach = np.abs( tests @ axes ) @ half + \
        np.einsum( "ntk,nk->nt", np.abs( np.einsum( "ntj,njk->ntk", tests, solid_axes ) ), halves )
    apart = np.abs( np.einsum( "ntj,nj->nt", tests, centres - centre ) )
    return ~np.any( valid & ( apart >= reach - margin ), axis=1 )


def check_swings( model ):
    """ Every door turns its whole 90 degrees either way clear of everything drawn (the model's solids) and of every
    other door, so none sticks in a wall or the stairs however it's opened. Stops the script at the first that doesn't. """
    centres = np.array( [ s[0] for s in model.solids ] )
    axes = np.array( [ s[1] for s in model.solids ] )
    halves = np.array( [ s[2] for s in model.solids ] )
    extents = np.einsum( "njk,nk->nj", np.abs( axes ), halves )          # each solid's half size along x, y and z
    angles = [ sign * a for sign in ( 1, -1 ) for a in range( 0, 91, 3 ) ]
    swept = {}
    for door in model.doors:
        reach = math.hypot( door.reach, door.thick / 2 + LEVER[2] + LEVER[1] ) + 1.0
        low, high = door.origin[2] + door.bottom, door.origin[2] + door.top
        gap = np.maximum( np.abs( centres[:, :2] - door.origin[:2] ) - extents[:, :2], 0.0 )
        near = ( np.linalg.norm( gap, axis=1 ) < reach ) & ( centres[:, 2] - extents[:, 2] < high ) & \
               ( centres[:, 2] + extents[:, 2] > low )
        solids = ( centres[near], axes[near], halves[near] )
        swept[door.key] = []
        for angle in angles:
            for box in door.boxes( angle ):
                hits = overlapping( box, solids )
                if hits.any():
                    where = to_plan( solids[0][np.argmax( hits )] )
                    raise SystemExit( f"{door.name} hits the box round plan {tuple( round( float( c ), 1 ) for c in where )} "
                                      f"at {angle:+d} degrees open" )
                swept[door.key].append( box )
    for i, a in enumerate( model.doors ):
        for b in model.doors[i + 1:]:
            if np.linalg.norm( a.origin - b.origin ) > a.reach + b.reach + 8.0:
                continue
            theirs = tuple( np.array( [ box[k] for box in swept[b.key] ] ) for k in range( 3 ) )
            if any( overlapping( box, theirs ).any() for box in swept[a.key] ):
                raise SystemExit( f"{a.name} and {b.name} can swing into each other" )
    print( f"checked the {len( model.doors )} doors' swings: each turns 90 degrees either way clear of everything" )


BUILDINGS = { "town_house": ( "Town House", town_house ) }

# Where each stands in ridgeback.scene: world x, y (the ground floor's middle) and yaw. --measure works the height out
# from the terrain. The Town House fronts the Airfield road ~660 north-east of Town's crossroads, the one spot near
# them that is all bare earth (Town's is ragged past ~900, and the road beds take the rest) and faces a road.
PLACEMENTS = {
    "town_house": dict( position=( -1615.0, -2040.0 ), yaw=87.5 ),
}


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def obj_vector( p ):
    """ Model space to the OBJ's axes ( Y, Z, X ). """
    return f"{p[1]:.4f} {p[2]:.4f} {p[0]:.4f}"


def write_obj( path, model ):
    lines = [ "# Tools/ridgeback_buildings.py", f"mtllib {path.stem}.mtl", f"o {path.stem}" ]
    vertices, uvs, normals, faces = [], [], [], []
    for paint in sorted( model.polygons ):
        faces.append( f"usemtl {paint}" )
        for points, normal, given in model.polygons[paint]:
            assert given is not None or paint not in BT.DECALS, f"{path.name}: {paint} is mapped across each polygon"
            base = len( vertices )
            normals.append( f"vn {obj_vector( normal )}" )
            for k, p in enumerate( points ):
                vertices.append( f"v {obj_vector( p )}" )
                u, v = given[k] if given is not None else face_uv( p, normal, paint )
                uvs.append( f"vt {u:.5f} {v:.5f}" )
            n = len( normals )
            for k in range( 1, len( points ) - 1 ):
                a, b, c = base + 1, base + k + 1, base + k + 2
                faces.append( f"f {a}/{a}/{n} {b}/{b}/{n} {c}/{c}/{n}" )
    path.write_text( "\n".join( lines + vertices + uvs + normals + faces ) + "\n", encoding="utf-8", newline="\n" )
    path.with_suffix( ".mtl" ).write_text( "".join( f"newmtl {paint}\nKd 1 1 1\nd 1\n" for paint in sorted( model.polygons ) ),
                                           encoding="utf-8", newline="\n" )
    return sum( 1 for f in faces if f.startswith( "f " ) )


def write_hull_obj( path, model ):
    points, faces = model.hull
    lines = [ "# Tools/ridgeback_buildings.py: the roof's collision hull", f"o {path.stem}" ]
    lines += [ f"v {obj_vector( p )}" for p in points ]
    for face in faces:
        for k in range( 1, len( face ) - 1 ):
            lines.append( f"f {face[0] + 1} {face[k] + 1} {face[k + 1] + 1}" )
    path.write_text( "\n".join( lines ) + "\n", encoding="utf-8", newline="\n" )


def vec3( v ):
    return "[ " + ", ".join( f"{c:.4f}" for c in v ) + " ]"


def write_vmdl( path, resource_dir, name, model ):
    """ A model's vmdl: its OBJ with the paints' materials, and its collision if it has any (the boxes, and the roof's
    hull from <name>_roof.obj). """
    remaps = ",\n".join( f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{BT.material_path( paint )}" }}'
                         for paint in sorted( model.polygons ) )
    shapes = []
    for centre, size, angles, surface in model.boxes:
        shapes.append( "\t\t\t\t\t{\n"
                       '\t\t\t\t\t\t_class = "PhysicsShapeBox"\n'
                       '\t\t\t\t\t\tparent_bone = ""\n'
                       f'\t\t\t\t\t\tsurface_prop = "{surface}"\n'
                       '\t\t\t\t\t\tcollision_tags = "solid"\n'
                       f"\t\t\t\t\t\torigin = {vec3( centre )}\n"
                       f"\t\t\t\t\t\tangles = {vec3( angles )}\n"
                       f"\t\t\t\t\t\tdimensions = {vec3( size )}\n"
                       "\t\t\t\t\t}," )
    if model.hull is not None:
        shapes.append( hull_shape( resource_dir, name ) )
    physics = ( "\t\t\t{\n"
                '\t\t\t\t_class = "PhysicsShapeList"\n'
                "\t\t\t\tchildren =\n"
                "\t\t\t\t[\n"
                + "\n".join( shapes ) + "\n"
                "\t\t\t\t]\n"
                "\t\t\t},\n" ) if shapes else ""
    text = ( "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
             "{\n"
             "\trootNode =\n"
             "\t{\n"
             '\t\t_class = "RootNode"\n'
             "\t\tchildren =\n"
             "\t\t[\n"
             "\t\t\t{\n"
             '\t\t\t\t_class = "MaterialGroupList"\n'
             "\t\t\t\tchildren =\n"
             "\t\t\t\t[\n"
             "\t\t\t\t\t{\n"
             '\t\t\t\t\t\t_class = "DefaultMaterialGroup"\n'
             "\t\t\t\t\t\tremaps =\n"
             "\t\t\t\t\t\t[\n"
             + remaps + "\n"
             "\t\t\t\t\t\t]\n"
             "\t\t\t\t\t\tuse_global_default = false\n"
             '\t\t\t\t\t\tglobal_default_material = ""\n'
             "\t\t\t\t\t},\n"
             "\t\t\t\t]\n"
             "\t\t\t},\n"
             "\t\t\t{\n"
             '\t\t\t\t_class = "RenderMeshList"\n'
             "\t\t\t\tchildren =\n"
             "\t\t\t\t[\n"
             "\t\t\t\t\t{\n"
             '\t\t\t\t\t\t_class = "RenderMeshFile"\n'
             f'\t\t\t\t\t\tname = "{name}"\n'
             f'\t\t\t\t\t\tfilename = "{resource_dir}/{name}.obj"\n'
             "\t\t\t\t\t\timport_translation = [ 0.0, 0.0, 0.0 ]\n"
             "\t\t\t\t\t\timport_rotation = [ 0.0, 0.0, 0.0 ]\n"
             "\t\t\t\t\t\timport_scale = 1.0\n"
             '\t\t\t\t\t\talign_origin_x_type = "None"\n'
             '\t\t\t\t\t\talign_origin_y_type = "None"\n'
             '\t\t\t\t\t\talign_origin_z_type = "None"\n'
             '\t\t\t\t\t\tparent_bone = ""\n'
             "\t\t\t\t\t\timport_filter = { exclude_by_default = false exception_list = [ ] }\n"
             "\t\t\t\t\t},\n"
             "\t\t\t\t]\n"
             "\t\t\t},\n"
             + physics +
             "\t\t]\n"
             '\t\tmodel_archetype = ""\n'
             '\t\tprimary_associated_entity = ""\n'
             '\t\tanim_graph_name = ""\n'
             '\t\tbase_model_name = ""\n'
             "\t}\n"
             "}\n" )
    path.write_text( text, encoding="utf-8", newline="\n" )


def hull_shape( resource_dir, name ):
    """ The roof's collision: one hull, from <name>_roof.obj. """
    return ( "\t\t\t\t\t{\n"
             '\t\t\t\t\t\t_class = "PhysicsHullFile"\n'
             '\t\t\t\t\t\tname = "roof"\n'
             '\t\t\t\t\t\tparent_bone = ""\n'
             '\t\t\t\t\t\tsurface_prop = "ceramic"\n'
             '\t\t\t\t\t\tcollision_tags = "solid"\n'
             "\t\t\t\t\t\trecenter_on_parent_bone = false\n"
             "\t\t\t\t\t\toffset_origin = [ 0.0, 0.0, 0.0 ]\n"
             "\t\t\t\t\t\toffset_angles = [ 0.0, 0.0, 0.0 ]\n"
             '\t\t\t\t\t\talign_origin_x_type = "None"\n'
             '\t\t\t\t\t\talign_origin_y_type = "None"\n'
             '\t\t\t\t\t\talign_origin_z_type = "None"\n'
             f'\t\t\t\t\t\tfilename = "{resource_dir}/{name}_roof.obj"\n'
             "\t\t\t\t\t\timport_scale = 1.0\n"
             "\t\t\t\t\t\tfaceMergeAngle = 10.0\n"
             "\t\t\t\t\t\tmaxHullVertices = 0\n"
             '\t\t\t\t\t\timport_mode = "HullPerElement"\n'
             '\t\t\t\t\t\toptimization_algorithm = "QEM"\n'
             "\t\t\t\t\t\timport_filter = { exclude_by_default = false exception_list = [ ] }\n"
             "\t\t\t\t\t}," )


def number_text( c, places ):
    return f"{round( float( c ), places ) + 0.0:.{places}f}".rstrip( "0" ).rstrip( "." )


def vec_text( v ):
    return ",".join( number_text( c, 4 ) for c in v )


def yaw_text( yaw ):
    """ A turn about Z as a prefab's Rotation ( x, y, z, w ). """
    half = math.radians( yaw ) / 2
    return ",".join( number_text( c, 7 ) for c in ( 0.0, 0.0, math.sin( half ), math.cos( half ) ) )


def curve_frames( points ):
    """ A Curve's frames: straight lines between the points. """
    frames = []
    for k, ( x, y ) in enumerate( points ):
        before = ( y - points[k - 1][1] ) / ( x - points[k - 1][0] ) if k > 0 else 0.0
        after = ( points[k + 1][1] - y ) / ( points[k + 1][0] - x ) if k + 1 < len( points ) else before
        frames.append( { "x": round( x, 6 ), "y": round( y, 6 ), "in": round( before if k > 0 else after, 6 ),
                         "out": round( after, 6 ), "mode": "Linear" } )
    return frames


def prefab_object( key, name, components=(), children=(), position=( 0.0, 0.0, 0.0 ), yaw=0.0, tags="" ):
    return { "__guid": gid( key ), "Flags": 0, "Name": name, "Position": vec_text( position ), "Rotation": yaw_text( yaw ),
             "Scale": "1,1,1", "Tags": tags, "Enabled": True, "NetworkMode": 2, "Components": list( components ),
             "Children": list( children ) }


def renderer( key, model_path, shadows=True ):
    return { "__type": "Sandbox.ModelRenderer", "__guid": gid( key ), "__enabled": True, "BodyGroups": 18446744073709551615,
             "Model": model_path, "RenderType": "On" if shadows else "Off", "Tint": "1,1,1,1" }


def box_collider( key, centre, size, surface=None, static=True ):
    collider = { "__type": "Sandbox.BoxCollider", "__guid": gid( key ), "__enabled": True, "Center": vec_text( centre ),
                 "IsTrigger": False, "Scale": vec_text( size ), "Static": static }
    if surface:
        collider["Surface"] = surface
    return collider


def door_object( name, door, model_path ):
    """ A door: its leaf, a box round it that moves with it (bullets go through at wood's rate) and the mover. """
    key, h = f"{name}/{door.key}", door.thick / 2
    mover = { "__type": "TerrorTown.FuncDoorRotating", "__guid": gid( f"{key}/mover" ), "__enabled": True,
              "AllowDirectUse": True, "StartsOpen": False, "StartsLocked": False, "AutoReset": False, "ResetTime": 1,
              "OpenAwayFromActivator": True, "Pivot": "0,0,0", "PivotTarget": None, "TargetRotation": "0,90,0",
              "OpenDuration": OPEN_DURATION, "CloseDuration": CLOSE_DURATION,
              "OpenMovementCurve": curve_frames( OPEN_CURVE ), "CloseMovementCurve": curve_frames( CLOSE_CURVE ),
              "PartnerObject": None, "PartnerName": None, "OpenFinishedSound": None, **DOOR_SOUNDS }
    return prefab_object( key, door.name, [
        renderer( f"{key}/renderer", model_path ),
        box_collider( f"{key}/collider", ( 0.0, ( door.reach - h ) / 2, ( door.bottom + door.top ) / 2 ),
                      ( door.thick, door.reach + h, door.top - door.bottom ), "surfaces/wood.surface", static=False ),
        mover ], position=door.origin, yaw=door.yaw )


def pane_object( name, pane, parts ):
    """ A pane: the glass (casting no shadow), its collider over its share of the opening, and what breaks it. """
    key = f"{name}/{pane['key']}"
    centre, size = pane["collider"]
    glass = { "__type": "Facepunch.BreakableGlass", "__guid": gid( f"{key}/glass" ), "__enabled": True,
              "BreakSound": GLASS_SOUND, "ShardEffect": { "_type": "gameobject", "prefab": SHATTER_PREFAB },
              "IntactModel": parts["pane"], "BrokenModels": [ parts[f"pane_broken_{k + 1}"] for k in range( BROKEN_PANES ) ],
              "PaneSize": vec_text( pane["size"] ), "ShardDensity": SHARDS_PER_FOOT }
    normal = pane["normal"]
    return prefab_object( key, pane["name"], [
        renderer( f"{key}/renderer", parts["pane"], shadows=False ),
        box_collider( f"{key}/collider", centre, size, "surfaces/glass.surface" ),
        glass ], position=pane["position"], yaw=math.degrees( math.atan2( normal[1], normal[0] ) ), tags="glass" )


def write_prefab( path, name, title, model_path, model, parts ):
    """ The building (a ModelRenderer and a static ModelCollider), its doors, its window panes and, on one object tagged
    playerclip, a box in each window that stops players. """
    children = [
        prefab_object( f"{name}/doors", "Doors", children=[ door_object( name, door, parts[f"door_{door.kind}"] )
                                                              for door in model.doors ] ),
        prefab_object( f"{name}/windows", "Windows", children=[ pane_object( name, pane, parts ) for pane in model.panes ] ),
        prefab_object( f"{name}/window_clips", "Window Clips",
                       [ box_collider( f"{name}/{clip['key']}", clip["centre"], clip["size"] ) for clip in model.clips ],
                       tags="playerclip" ),
    ]
    prefab = {
        "RootObject": {
            "__guid": gid( f"{name}/root" ),
            "Flags": 0,
            "Name": title,
            "Position": "0,0,0",
            "Rotation": "0,0,0,1",
            "Scale": "1,1,1",
            "Enabled": True,
            "NetworkMode": 2,
            "Components": [
                { "__type": "Sandbox.ModelRenderer", "__guid": gid( f"{name}/renderer" ), "__enabled": True,
                  "BodyGroups": 18446744073709551615, "Model": model_path, "RenderType": "On", "Tint": "1,1,1,1" },
                { "__type": "Sandbox.ModelCollider", "__guid": gid( f"{name}/collider" ), "__enabled": True,
                  "IsTrigger": False, "Model": model_path, "Static": True },
            ],
            "Children": children,
        },
        "ShowInMenu": False,
        "MenuPath": None,
        "MenuIcon": None,
        "ResourceVersion": 1,
        "__references": [],
        "__version": 1,
    }
    path.write_text( json.dumps( prefab, indent=2 ) + "\n", encoding="utf-8", newline="\n" )


def write_shatter_prefab( path ):
    """ The shards a breaking pane throws. Facepunch.BreakableGlass emits them over the pane by hand, so there's no
    emitter: the core glass impact's chunk sprites, the size of a window's pieces, falling under gravity, coming to
    rest where they land and fading. They pass through the windows' player clips, which they start inside. """
    def ranged( low, high ):
        return { "Type": "Range", "Evaluation": "Seed", "Constants": f"{low},{high},0,0" }

    zero = { "X": 0, "Y": 0, "Z": 0 }
    events = { f"OnComponent{event}": None for event in ( "Destroy", "Disabled", "Enabled", "FixedUpdate", "Start", "Update" ) }
    particles = {
        "__type": "Sandbox.ParticleEffect", "__guid": gid( "glass_shatter/particles" ), "__enabled": True, "Flags": 0,
        "__version": 3,
        "Alpha": { "Type": "Curve", "Evaluation": "Life", "CurveA": curve_frames( [ ( 0.0, 1.0 ), ( 0.8, 1.0 ), ( 1.0, 0.0 ) ] ),
                   "CurveB": [ { "x": 0.5, "y": 0.5, "in": 0, "out": 0, "mode": "Mirrored" } ] },
        "ApplyAlpha": True, "ApplyColor": True, "ApplyRotation": True, "ApplyShape": True,
        "Bounce": 0.15, "Brightness": 1, "Bumpiness": 0,
        "Collision": True, "CollisionIgnore": "playerclip", "CollisionPrefab": None, "CollisionPrefabAlign": False,
        "CollisionPrefabChance": 1, "CollisionPrefabRotation": 0, "CollisionRadius": 0.25,
        "ConstantMovement": zero, "Damping": 0.2, "DieOnCollisionChance": 0,
        "FollowerPrefab": None, "FollowerPrefabChance": 1, "FollowerPrefabKill": True,
        "Force": True, "ForceDirection": "0,0,-386", "ForceScale": 1, "ForceSpace": "World", "Friction": 50,
        "Gradient": "1,1,1,1", "InitialVelocity": zero, "Lifetime": ranged( 3.5, 5.5 ), "LocalSpace": 0,
        "MaxParticles": 100, **events, "OnParticleCreated": None, "OnParticleDestroyed": None,
        "OrbitalForce": zero, "OrbitalPull": 0, "PerParticleTimeScale": 1, "Pitch": 0, "PreWarm": 0, "PushStrength": 0,
        "Roll": ranged( 0, 360 ), "Scale": ranged( 0.6, 2.0 ), "SequenceId": ranged( 0, 4 ), "SequenceSpeed": 0,
        "SequenceTime": 1, "SheetSequence": True, "SnapToFrame": False, "StartDelay": 0, "StartVelocity": 0,
        "Stretch": 0, "TimeScale": 1, "Timing": "GameTime", "Tint": "0.78,0.84,0.82,1", "UsePrefabFeature": False,
        "Yaw": 0,
    }
    sprites = {
        "__type": "Sandbox.ParticleSpriteRenderer", "__guid": gid( "glass_shatter/sprites" ), "__enabled": True,
        "Flags": 0, "__version": 2, "Additive": False, "Alignment": "LookAtCamera", "BlurAmount": 0.5,
        "BlurOpacity": 0.5, "BlurSpacing": 0.5, "DepthFeather": 0, "FaceVelocity": False, "FogStrength": 1,
        "LeadingTrail": False, "Lighting": True, "MotionBlur": True, **events, "Opaque": False, "PlaybackSpeed": 1,
        "RenderOptions": { "GameLayer": True, "OverlayLayer": False, "BloomLayer": False, "AfterUILayer": False },
        "RotationOffset": 0, "Scale": 1, "Shadows": False, "SortMode": "Unsorted",
        "Sprite": { "$compiler": "embed", "$source": None, "data": {
            "Animations": [ { "Name": "Default", "FrameRate": 15, "Origin": "0.5,0.5", "LoopMode": "Loop",
                              "Frames": [ { "Texture": "textures/particles/impact/glass_chunks_01.vtex",
                                            "BroadcastMessages": [] } ] } ],
            "__references": None }, "compiled": None },
        "StartingAnimationName": "Default", "TextureFilter": "Bilinear",
    }
    shards = prefab_object( "glass_shatter/shards", "shards", [ particles, sprites ], tags="particles" )
    prefab = {
        "RootObject": prefab_object( "glass_shatter/root", "glass_shatter", [
            { "__type": "TemporaryEffect", "__guid": gid( "glass_shatter/temporary" ), "__enabled": True, "Flags": 0,
              "BecomeOrphan": True, "DestroyAfterSeconds": 6, **events, "WaitForChildEffects": True } ], [ shards ] ),
        "ShowInMenu": False,
        "MenuPath": None,
        "MenuIcon": None,
        "ResourceVersion": 1,
        "__references": [],
        "__version": 1,
    }
    path.write_text( json.dumps( prefab, indent=2 ) + "\n", encoding="utf-8", newline="\n" )


def part_models( model ):
    """ The models a building's prefab uses beside its own, by name: a leaf for each kind of door (every door of a
    kind is the same size), the pane (as is every pane) and the broken panes. """
    parts, sizes = {}, {}
    for door in model.doors:
        name, size = f"door_{door.kind}", tuple( round( v, 4 ) for v in ( door.reach, door.bottom, door.top, door.thick ) )
        assert sizes.setdefault( name, size ) == size, f"{door.name} isn't the size of the other {door.kind} doors"
        parts.setdefault( name, door_leaf( door ) )
    panes = { tuple( round( v, 4 ) for v in pane["size"] ) for pane in model.panes }
    assert len( panes ) == 1, f"panes of {len( panes )} sizes"
    size = model.panes[0]["size"]
    parts["pane"] = pane_model( size )
    for k in range( BROKEN_PANES ):
        parts[f"pane_broken_{k + 1}"] = broken_pane( size, 100 + k )
    return parts


def write_building( name ):
    title, build = BUILDINGS[name]
    model = build()
    out_dir = ASSETS / "models/buildings" / name
    resource_dir = f"models/buildings/{name}"
    out_dir.mkdir( parents=True, exist_ok=True )
    triangles = write_obj( out_dir / f"{name}.obj", model )
    write_hull_obj( out_dir / f"{name}_roof.obj", model )
    write_vmdl( out_dir / f"{name}.vmdl", resource_dir, name, model )
    parts, paths = part_models( model ), {}
    for part, part_model in parts.items():
        write_obj( out_dir / f"{name}_{part}.obj", part_model )
        write_vmdl( out_dir / f"{name}_{part}.vmdl", resource_dir, f"{name}_{part}", part_model )
        paths[part] = f"{resource_dir}/{name}_{part}.vmdl"
    prefab_dir = ASSETS / "prefabs/buildings"
    prefab_dir.mkdir( parents=True, exist_ok=True )
    write_shatter_prefab( ASSETS / SHATTER_PREFAB )
    write_prefab( prefab_dir / f"{name}.prefab", name, title, f"{resource_dir}/{name}.vmdl", model, paths )
    print( f"wrote {title}: {triangles} triangles in {len( model.polygons )} materials, {len( model.boxes )} collision "
           f"boxes and the roof's hull; {len( model.doors )} doors, {len( model.panes )} window panes and "
           f"{len( model.clips )} window clips; parts: {', '.join( parts )}" )
    return model, parts


# ---------------------------------------------------------------------------------------------------------------------
# Placement

def survey():
    """ Where each placement stands and what's round it, from the map's own terrain. """
    import ridgeback_map as R
    from scipy import ndimage
    z, pads, river, roads, edge, notes = R.build()
    dominant = np.argmax( R.paint( z, notes["slope"], pads, river, roads ), axis=0 )
    road_distance = np.min( [ field.distance for field in roads.values() ], axis=0 )

    def sample( grid, p, order=1 ):
        i, j = R.to_index( p[0], p[1] )
        return ndimage.map_coordinates( grid, [ [ j ], [ i ] ], order=order, mode="nearest" )[0]

    stands = {}
    for name, spec in PLACEMENTS.items():
        position, yaw = np.array( spec["position"] ), spec["yaw"]
        turn = rotation_matrix( 0, yaw, 0 )[:2, :2]

        def world( a, b ):
            return position + turn @ to_model( a, b, 0 )[:2]

        around = [ world( a, b ) for a in np.arange( -40, LENGTH + 41, 15 ) for b in np.arange( -40, DEPTH + 41, 15 ) ]
        inside = [ world( a, b ) for a in np.arange( 0, LENGTH + 1, 15 ) for b in np.arange( 0, DEPTH + 1, 15 ) ]
        heights = [ float( sample( z, p ) ) for p in around ]
        floor = round( max( heights ) + 10.0, 1 )
        doors = []
        for wall, openings in OPENINGS.items():
            for storey, kind, centre in openings:
                if kind == "door":
                    a, b = { "front": ( centre, -40.0 ), "back": ( centre, DEPTH + 40.0 ), "left": ( -40.0, centre ),
                             "right": ( LENGTH + 40.0, centre ) }[wall]
                    doors.append( ( wall, float( sample( z, world( a, b ) ) ) - floor ) )
        stands[name] = dict(
            position=( float( position[0] ), float( position[1] ), floor ), yaw=yaw,
            ground=( min( heights ), max( heights ) ), doors=doors,
            road=min( float( sample( road_distance, p ) ) for p in around ) - R.ROAD_HALF,
            grass=sum( int( sample( dominant, p, 0 ) ) in ( R.MEADOW, R.DRY ) for p in inside ), samples=len( inside ) )
    return stands


def measure( stands ):
    for name, stand in stands.items():
        x, y, floor = stand["position"]
        low, high = stand["ground"]
        print( f"{name}: stand at {x:.1f},{y:.1f},{floor:.1f} yaw {stand['yaw']:.1f}; ground under it {low:.1f} to "
               f"{high:.1f}; {stand['road']:.0f} units clear of the road beds; {stand['grass']} of {stand['samples']} "
               f"footprint samples on grass ground" )
        for wall, height in stand["doors"]:
            print( f"  {wall} door: the ground outside is {height:.1f} from the floor" )


def place( stands ):
    """ Every building into ridgeback.scene, as prefab instances under its "Buildings" object (made after "Sites" the
    first time). The rest of the scene is written back exactly as the editor saved it. """
    import ridgeback_map as R
    text = R.SCENE_FILE.read_bytes().decode( "utf-8" )
    newline = "\r\n" if "\r\n" in text else "\n"
    scene = json.loads( text )

    instances = []
    for name, stand in stands.items():
        path = f"prefabs/buildings/{name}.prefab"
        prefab = json.loads( ( ASSETS / path ).read_text( encoding="utf-8" ) )
        root = prefab["RootObject"]["__guid"]
        ids = []

        def collect( node ):
            ids.append( node["__guid"] )
            ids.extend( component["__guid"] for component in node.get( "Components", [] ) )
            for child in node.get( "Children", [] ):
                collect( child )

        collect( prefab["RootObject"] )
        instance = gid( f"scene/{name}" )
        target = { "Type": "GameObject", "IdValue": root }
        instances.append( {
            "__guid": instance, "__version": 2,
            "__Prefab": { "Id": json.loads( ( ASSETS / f"{path}.meta" ).read_text( encoding="utf-8" ) )["guid"], "Path": path },
            "__PrefabInstancePatch": {
                "AddedObjects": [], "RemovedObjects": [],
                "PropertyOverrides": [
                    { "Target": target, "Property": "Position", "Value": R.vec( stand["position"] ) },
                    { "Target": target, "Property": "Rotation", "Value": R.yaw_rotation( stand["yaw"] ) },
                ],
                "MovedObjects": [],
            },
            "__PrefabIdToInstanceId": { pid: instance if pid == root else gid( f"scene/{name}/{pid}" ) for pid in sorted( ids ) },
        } )

    group = R.game_object( "Buildings", "buildings", children=instances )
    objects = scene["GameObjects"]
    index = next( ( i for i, o in enumerate( objects ) if o.get( "__guid" ) == group["__guid"] ), None )
    if index is not None:
        objects[index] = group
    else:
        sites = next( ( i for i, o in enumerate( objects ) if o.get( "Name" ) == "Sites" ), len( objects ) - 1 )
        objects.insert( sites + 1, group )
    out = json.dumps( scene, indent=2, ensure_ascii=False )
    R.SCENE_FILE.write_bytes( ( out.replace( "\n", newline ) + ( newline if text.endswith( "\n" ) else "" ) ).encode( "utf-8" ) )
    print( f"placed {len( instances )} building(s) in {R.SCENE_FILE.relative_to( ROOT )}" )


PREVIEW_COLOURS = { "render_ochre": ( 204, 178, 134 ), "render_pale": ( 222, 215, 196 ), "whitewash": ( 214, 211, 199 ),
                    "concrete": ( 150, 147, 140 ), "trim_white": ( 232, 228, 216 ), "trim_brown": ( 88, 60, 42 ),
                    "trim_green": ( 58, 90, 64 ), "shutter_green": ( 66, 96, 70 ), "quarry_tiles": ( 160, 84, 58 ),
                    "floorboards": ( 140, 100, 66 ), "roof_tiles": ( 146, 72, 50 ), "brick": ( 150, 70, 50 ),
                    "metal": ( 150, 153, 156 ), "iron_black": ( 40, 40, 40 ), "glass_clear": ( 176, 196, 204 ) }
BOX_CORNERS = [ ( sx, sy, sz ) for sx in ( -1.0, 1.0 ) for sy in ( -1.0, 1.0 ) for sz in ( -1.0, 1.0 ) ]
BOX_EDGES = [ ( i, j ) for i in range( 8 ) for j in range( i + 1, 8 ) if bin( i ^ j ).count( "1" ) == 1 ]


def placed_parts( model, parts, angle ):
    """ The doors, angle degrees open, and the window panes, as one model in the building's space. """
    placed = Model()
    for door in model.doors:
        placed.add( parts[f"door_{door.kind}"], door.origin, door.axes( angle ).T )
    for pane in model.panes:
        n = pane["normal"]
        placed.add( parts["pane"], np.asarray( pane["position"], float ), ( n, np.cross( UP, n ), UP ) )
    return placed


def section( centre, axes, half, cut ):
    """ Where a box ( centre, axes as columns, half sizes ) meets the level plane z = cut: its outline in order round
    it, or None. """
    corners = [ centre + axes @ ( np.asarray( half ) * s ) for s in BOX_CORNERS ]
    points = [ corners[i] + ( corners[j] - corners[i] ) * ( cut - corners[i][2] ) / ( corners[j][2] - corners[i][2] )
               for i, j in BOX_EDGES if ( corners[i][2] - cut ) * ( corners[j][2] - cut ) < 0 ]
    if len( points ) < 3:
        return None
    middle = np.mean( points, axis=0 )
    return sorted( points, key=lambda p: math.atan2( p[1] - middle[1], p[0] - middle[0] ) )


def clip_below( points, cut ):
    """ The part of a polygon at or below z = cut. """
    kept = []
    for p, q in zip( points, points[1:] + points[:1] ):
        if p[2] <= cut:
            kept.append( p )
        if ( p[2] - cut ) * ( q[2] - cut ) < 0:
            kept.append( p + ( q - p ) * ( cut - p[2] ) / ( q[2] - p[2] ) )
    return kept


def render_view( title, polys, right, up, scale, overlays=() ):
    """ An image of polys ( depth, points, colour ), drawn far to near, then overlays ( points, fill, outline ) over
    them, projected onto right and up at scale pixels to the inch. """
    from PIL import Image, ImageDraw
    pad = 24
    right, up = np.asarray( right, float ), np.asarray( up, float )
    polys = sorted( polys, key=lambda item: item[0] )
    us = [ float( np.dot( p, right ) ) for _, points, _ in polys for p in points ]
    vs = [ float( np.dot( p, up ) ) for _, points, _ in polys for p in points ]
    u0, u1, v0, v1 = min( us ), max( us ), min( vs ), max( vs )
    image = Image.new( "RGB", ( int( ( u1 - u0 ) * scale ) + 2 * pad, int( ( v1 - v0 ) * scale ) + 2 * pad ), ( 30, 34, 40 ) )
    draw = ImageDraw.Draw( image )

    def xy( p ):
        return ( pad + ( float( np.dot( p, right ) ) - u0 ) * scale, pad + ( v1 - float( np.dot( p, up ) ) ) * scale )

    for _, points, colour in polys:
        draw.polygon( [ xy( p ) for p in points ], fill=colour )
    for points, fill, outline in overlays:
        draw.polygon( [ xy( p ) for p in points ], fill=fill, outline=outline )
    draw.text( ( 6, 6 ), title, fill=( 255, 255, 255 ) )
    return image


def write_preview( path, model, parts ):
    """ Flat-shaded front, side, back and top views with the doors shut and the glass in, then a plan of each storey
    cut through its doors and windows: walls and frames dark, the glass pale blue, the windows' player clips in red,
    and each door's leaf shut (outlined) and open 90 degrees either way. """
    from PIL import Image
    light = normalise( ( 0.5, 0.4, 0.75 ) )

    def shaded( paint, normal ):
        shade = 0.5 + 0.5 * max( 0.0, float( np.dot( normal, light ) ) )
        return tuple( int( c * shade ) for c in PREVIEW_COLOURS[paint] )

    def faces( *models ):
        for m in models:
            for paint, items in m.polygons.items():
                for points, normal, _ in items:
                    yield paint, points, normal

    shut = placed_parts( model, parts, 0.0 )
    # Title, then towards the viewer, image right and image up.
    views = [ ( "front", ( 1, 0, 0 ), ( 0, 1, 0 ), ( 0, 0, 1 ) ), ( "right side", ( 0, 1, 0 ), ( -1, 0, 0 ), ( 0, 0, 1 ) ),
              ( "back", ( -1, 0, 0 ), ( 0, -1, 0 ), ( 0, 0, 1 ) ), ( "left side", ( 0, -1, 0 ), ( 1, 0, 0 ), ( 0, 0, 1 ) ),
              ( "top", ( 0, 0, 1 ), ( 0, -1, 0 ), ( 1, 0, 0 ) ) ]
    elevations = []
    for title, eye, right, up in views:
        eye = np.array( eye, float )
        polys = [ ( float( np.mean( [ np.dot( p, eye ) for p in points ] ) ), points, shaded( paint, normal ) )
                  for paint, points, normal in faces( model, shut ) if np.dot( normal, eye ) > 1e-6 ]
        elevations.append( render_view( title, polys, right, up, 1.0 ) )

    plans = []
    for storey, floor in enumerate( FLOORS ):
        cut = floor + 60.3                               # through the doors and the windows
        polys = []
        for paint, points, normal in faces( model ):
            if normal[2] > 1e-6:
                kept = clip_below( points, cut )
                if len( kept ) >= 3:
                    polys.append( ( float( np.mean( [ p[2] for p in kept ] ) ), kept, shaded( paint, normal ) ) )
        overlays = [ ( outline, ( 52, 54, 60 ), None ) for outline in
                     ( section( *solid, cut ) for solid in model.solids ) if outline is not None ]
        for pane in model.panes:
            n, size = pane["normal"], pane["size"]
            outline = section( np.asarray( pane["position"], float ), np.column_stack( ( n, np.cross( UP, n ), UP ) ),
                               ( GLASS / 2, size[0] / 2 + REBATE, size[1] / 2 + REBATE ), cut )
            if outline is not None:
                overlays.append( ( outline, PREVIEW_COLOURS[GLASS_PAINT], ( 150, 205, 235 ) ) )
        for clip in model.clips:
            outline = section( np.asarray( clip["centre"], float ), np.eye( 3 ), np.asarray( clip["size"] ) / 2, cut )
            if outline is not None:
                overlays.append( ( outline, None, ( 235, 60, 60 ) ) )
        for door in model.doors:
            for angle in ( 0.0, 90.0, -90.0 ):
                outline = section( *door.boxes( angle )[0], cut )
                if outline is None:
                    continue
                if angle == 0.0:
                    overlays.append( ( outline, None, ( 255, 255, 255 ) ) )
                else:
                    overlays.append( ( outline, PREVIEW_COLOURS[LEAVES[door.kind]["paint"]], ( 250, 230, 120 ) ) )
        plans.append( render_view( f"{STOREYS[storey].lower()} floor plan, cut {cut - floor:g} up", polys, ( 0, 1, 0 ),
                                   ( -1, 0, 0 ), 2.0, overlays ) )

    rows = [ elevations, plans ]
    sheet = Image.new( "RGB", ( max( sum( i.width for i in row ) for row in rows ),
                                sum( max( i.height for i in row ) for row in rows ) ), ( 30, 34, 40 ) )
    y = 0
    for row in rows:
        x = 0
        for image in row:
            sheet.paste( image, ( x, y ) )
            x += image.width
        y += max( i.height for i in row )
    sheet.save( path )
    print( f"wrote {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--measure", action="store_true", help="print where each building stands, from the terrain" )
    parser.add_argument( "--place", action="store_true", help="put the buildings in ridgeback.scene there" )
    parser.add_argument( "--preview", help="write flat-shaded views and plans of the Town House here" )
    args = parser.parse_args()

    for name in BUILDINGS:
        model, parts = write_building( name )
        if args.preview:
            write_preview( args.preview, model, parts )
    if args.measure or args.place:
        stands = survey()
        measure( stands )
        if args.place:
            place( stands )


if __name__ == "__main__":
    main()
