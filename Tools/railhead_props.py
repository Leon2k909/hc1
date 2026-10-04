"""
Railhead's props (Tools/railhead_map.py): track, turnouts, buffer stops and signals, the overhead line, the trains and
wagons, containers, the platforms' furniture and the goods yard's clutter. Each is a function that draws into a
map_kit.Model in plan coordinates (inches; e east, n north, z up; the tracks run north-south), with collision where it
stops a player.

    python Tools/railhead_props.py --preview <dir>      (renders a showcase of every prop; writes no assets)

Conventions
- Rolling stock: e is the track's centre, n_front the n of the vehicle's front end (its buffers' or coupler's face),
  facing +1 if that end faces north (the vehicle runs south from it) or -1, and rail_z the rails' top (-30 in the shed
  and the throat, 0 on embedded track). Each returns the n of its far end, where the next vehicle couples.
- Track equipment faces the way its front looks: a buffer stop's buffers, a signal's lamps (facing +1 = north).
- Furniture faces "+e", "-e", "+n" or "-n"; (e, n) is its footprint's centre on the floor at z0. Road vehicles point
  their noses along "+n", "-n", "+e" or "-e" from their footprint's centre. Fences run from p0 to p1, their posts and
  rails on the right looking from p0.
- Paints are the design doc's rw_* paints, plus building_textures' copper_brown for the overhead wires.
- Collision: trains, wagons, containers and buffer stops are "metal" boxes from rail_z - 7 up to their roofs; rails,
  sleepers, wires and small detail have none; furniture and yard clutter get a box or a few, and thin things lying on
  the floor (fence feet, a forklift's forks) none. Atlas faces get explicit UVs from railhead_materials.rect_uv() (the
  whole texture until that exists).
- Sizes are real ones: UIC 60 rail on B70 sleepers at standard gauge, UIC buffers 1060 mm over the rail 1750 mm apart,
  Re 200 overhead line, ISO containers, Euro pallets, welded mesh and palisade fencing and mobile fence panels to their
  makers' standard sizes, and the vehicles' typical figures for their class.
"""
import argparse
import math
import sys
import types
from pathlib import Path

import numpy as np

import map_kit as K

M = 39.37                       # inches in a metre
GAUGE_HALF = 29.6               # each rail's centre from the track's: 1435 mm gauge plus the 72 mm head
BUFFER_Z = 41.7                 # buffers' centres over the rail, 1060 mm
BUFFER_HALF = 34.45             # half of the 1750 mm between buffer centres
WIRE_HEIGHT = 216.5             # contact wire over the rail, 5.5 m
SYSTEM_HEIGHT = 55.0            # messenger over the contact wire at a support, 1.4 m
STAGGER = 11.8                  # the contact wire's zig-zag, +-300 mm
GRAIN = ( "rw_rail", "rw_rail_head", "rw_sleeper_wood", "rw_wood" )


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

def _unit( v ):
    v = np.asarray( v, float )
    length = np.linalg.norm( v )
    return v / length if length > 1e-12 else v


def _rect( atlas, name ):
    """ An atlas entry's ( u0, v0, u1, v1 ) from railhead_materials, or the whole texture while it isn't there. """
    try:
        import railhead_materials as RM
        return tuple( float( x ) for x in RM.rect_uv( atlas, name ) )
    except Exception:
        return ( 0.0, 0.0, 1.0, 1.0 )


SIGN_ASPECTS = { "gleis_1_2": 4, "gleis_3_4": 4, "gleis_5_6": 4, "to_gleis_left": 5, "to_gleis_right": 5,
                 "ausgang_left": 5, "ausgang_right": 5, "ausgang_west": 5, "ausgang_ost": 5, "taxi": 2,
                 "fahrkarten": 4, "station_name": 6, "gueterbahnhof": 6, "notausgang": 2, "warn_gleise": 3 }


def aspect( atlas, name ):
    """ Width over height of an atlas entry: its rectangle's in railhead_materials, else the design doc's. """
    u0, v0, u1, v1 = _rect( atlas, name )
    if ( u0, v0, u1, v1 ) != ( 0.0, 0.0, 1.0, 1.0 ):
        try:
            import railhead_materials as RM
            W, H = RM.ATLASES[atlas][:2]
            return ( u1 - u0 ) * W / ( ( v1 - v0 ) * H )
        except Exception:
            pass
    if atlas == "rw_shopsigns":
        return 5.0
    if atlas == "rw_displays":
        return { "departures": 2.4, "ticket_screen": 4 / 3 }.get( name, 5.0 )
    if atlas == "rw_posters":
        return { "network_map": 1.414, "stellwerk_hf": 3.0, "station_enamel": 6.0 }.get( name, 0.707 )
    if atlas == "rw_signs":
        return float( SIGN_ASPECTS.get( name, 1 ) )
    return 1.0


def outward( model, paint, points, towards, uv=None, normals=None ):
    """ A polygon turned to face towards (a direction), whichever way round its points were listed. """
    pts = [ np.asarray( q, float ) for q in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        order = [ 0 ] + list( range( len( pts ) - 1, 0, -1 ) )
        pts = [ pts[i] for i in order ]
        uv = None if uv is None else [ uv[i] for i in order ]
        normals = None if normals is None else [ normals[i] for i in order ]
    model.polygon( paint, pts, uv=uv, normals=normals )


def quad( model, paint, centre, right, up, w, h, uv=None ):
    """ A w x h rectangle facing cross( right, up ): corners bottom-left, bottom-right, top-right, top-left. """
    c = np.asarray( centre, float )
    r, u = _unit( right ) * w / 2, _unit( up ) * h / 2
    model.polygon( paint, [ c - r - u, c + r - u, c + r + u, c - r + u ], uv=uv )


def atlas_quad( model, atlas, name, centre, right, up, w, h ):
    """ An atlas entry on a w x h rectangle facing cross( right, up ), reading the right way round from in front. """
    u0, v0, u1, v1 = _rect( atlas, name )
    quad( model, atlas, centre, right, up, w, h, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )


def _ring_axes( axis ):
    a = _unit( axis )
    ref = np.array( ( 0.0, 0.0, 1.0 ) ) if abs( a[2] ) < 0.9 else np.array( ( 1.0, 0.0, 0.0 ) )
    u = _unit( np.cross( ref, a ) )
    return u, np.cross( a, u )


def rod( model, a, b, r, paint, sides=6, caps=( False, False ), cap_paint=None, turn=0.0 ):
    """ A round bar from a to b, shaded smooth, capped at either end if asked. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    if np.linalg.norm( b - a ) < 1e-6:
        return
    u, v = _ring_axes( b - a )
    dirs = [ math.cos( turn + 2 * math.pi * k / sides ) * u + math.sin( turn + 2 * math.pi * k / sides ) * v
             for k in range( sides ) ]
    for k in range( sides ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % sides]
        outward( model, paint, [ a + r * d0, a + r * d1, b + r * d1, b + r * d0 ], d0 + d1,
                 normals=[ d0, d1, d1, d0 ] )
    axis = _unit( b - a )
    if caps[0]:
        outward( model, cap_paint or paint, [ a + r * d for d in dirs ], -axis )
    if caps[1]:
        outward( model, cap_paint or paint, [ b + r * d for d in dirs ], axis )


def disc( model, paint, centre, normal, r, sides=12, round_uv=False, up=( 0.0, 0.0, 1.0 ) ):
    """ A flat round face; round_uv maps a decal 0..1 across it, upright (its v along up). """
    c, nrm = np.asarray( centre, float ), _unit( normal )
    upv = np.asarray( up, float )
    upv = _unit( upv - nrm * np.dot( upv, nrm ) )
    right = np.cross( upv, nrm )
    angles = [ 2 * math.pi * k / sides for k in range( sides ) ]
    pts = [ c + r * ( math.cos( t ) * right + math.sin( t ) * upv ) for t in angles ]
    uv = [ ( 0.5 + 0.5 * math.cos( t ), 0.5 + 0.5 * math.sin( t ) ) for t in angles ] if round_uv else None
    outward( model, paint, pts, nrm, uv=uv )


def polyline( model, points, r, paint, sides=4 ):
    """ Round bars joining points in turn. """
    for p, q in zip( points, points[1:] ):
        rod( model, p, q, r, paint, sides )


FACE_KEYS = ( "front", "back", "right", "left", "top", "bottom" )


class Frame:
    """ A thing's own axes: x to the right of someone facing its front, y towards its front, z up, from origin. Its
    boxes are the world's axis-aligned boxes, so forward is one of the four plan axes. """

    def __init__( self, origin, forward ):
        self.o = np.asarray( origin, float )
        self.y = _unit( ( forward[0], forward[1], 0.0 ) )
        self.x = np.cross( ( 0.0, 0.0, 1.0 ), self.y )
        self.z = np.array( ( 0.0, 0.0, 1.0 ) )

    def p( self, x, y, z ):
        return self.o + x * self.x + y * self.y + z * self.z

    def world_face( self, key ):
        vec = { "front": self.y, "back": -self.y, "right": self.x, "left": -self.x, "top": self.z,
                "bottom": -self.z }[key]
        k = int( np.argmax( np.abs( vec ) ) )
        return ( "+" if vec[k] > 0 else "-" ) + "enz"[k]

    def faces( self, paints ):
        if not isinstance( paints, dict ):
            return paints
        return { ( self.world_face( k ) if k in FACE_KEYS else k ): v for k, v in paints.items() }

    def box( self, model, x0, x1, y0, y1, z0, z1, paints, surface=None, skip=() ):
        p, q = self.p( x0, y0, z0 ), self.p( x1, y1, z1 )
        model.box( np.minimum( p, q ), np.maximum( p, q ), self.faces( paints ), surface,
                   skip=tuple( self.world_face( s ) if s in FACE_KEYS else s for s in skip ) )

    def collide( self, model, x0, x1, y0, y1, z0, z1, surface ):
        p, q = self.p( x0, y0, z0 ), self.p( x1, y1, z1 )
        model.collision_box( np.minimum( p, q ), np.maximum( p, q ), surface )

    def quad( self, model, paint, x, y, z, w, h, facing="front", uv=None ):
        """ A w x h rectangle centred on ( x, y, z ), facing front, back, right or left. """
        normal = { "front": self.y, "back": -self.y, "right": self.x, "left": -self.x }[facing]
        quad( model, paint, self.p( x, y, z ), np.cross( self.z, normal ), self.z, w, h, uv )

    def atlas( self, model, atlas, name, x, y, z, w, h, facing="front" ):
        u0, v0, u1, v1 = _rect( atlas, name )
        self.quad( model, atlas, x, y, z, w, h, facing, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )


def frame_for( e, n, z0, facing ):
    """ A piece of furniture's frame: origin at ( e, n, z0 ), y along facing ("+e", "-e", "+n" or "-n"). """
    forward = { "+e": ( 1, 0 ), "-e": ( -1, 0 ), "+n": ( 0, 1 ), "-n": ( 0, -1 ) }[facing]
    return Frame( ( e, n, z0 ), forward )


def vehicle_frame( e, n_front, facing, rail_z ):
    """ A vehicle's frame: origin on the track's centre at its front end's face, y forwards, so a point a behind the
    front is at y = -a. """
    return Frame( ( e, n_front, rail_z ), ( 0, 1 if facing > 0 else -1 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Track

# UIC 60 (60E1): 172 mm tall, 72 mm head, 16.5 mm web, 150 mm foot. ( across, down from the head's top ), counter-
# clockwise seen along the rail; the foot's underside isn't drawn.
RAIL_PROFILE = [ ( 2.95, -6.77 ), ( 2.95, -6.3 ), ( 0.33, -5.6 ), ( 0.33, -2.4 ), ( 1.415, -1.85 ), ( 1.415, -0.2 ),
                 ( 1.2, 0.0 ), ( -1.2, 0.0 ), ( -1.415, -0.2 ), ( -1.415, -1.85 ), ( -0.33, -2.4 ), ( -0.33, -5.6 ),
                 ( -2.95, -6.3 ), ( -2.95, -6.77 ) ]
RAIL_HEAD_EDGES = { 5, 6, 7 }
RAIL_CAP_PIECES = ( ( 4, 5, 6, 7, 8, 9 ), ( 3, 4, 9, 10 ), ( 2, 3, 10, 11 ), ( 0, 1, 2, 11, 12, 13 ) )


def rail( model, path, rail_z, paint="rw_rail", head="rw_rail_head", caps=True ):
    """ A UIC 60 rail along path (plan ( e, n ) points), its head's top at rail_z: the running surface rw_rail_head,
    the rest rw_rail. """
    pts = [ np.asarray( p, float )[:2] for p in path ]
    if len( pts ) < 2:
        return
    model.grain_paints.update( ( paint, head ) )
    tangents = [ _unit( pts[i + 1] - pts[i] ) for i in range( len( pts ) - 1 ) ]
    lefts = []
    for i in range( len( pts ) ):
        t = tangents[0] if i == 0 else tangents[-1] if i == len( pts ) - 1 else _unit( tangents[i - 1] + tangents[i] )
        lefts.append( np.array( ( -t[1], t[0] ) ) )

    def at( i, y, z ):
        q = pts[i] + lefts[i] * y
        return ( q[0], q[1], rail_z + z )

    for i in range( len( pts ) - 1 ):
        lm = _unit( lefts[i] + lefts[i + 1] )
        for k in range( len( RAIL_PROFILE ) - 1 ):
            ( ya, za ), ( yb, zb ) = RAIL_PROFILE[k], RAIL_PROFILE[k + 1]
            towards = ( lm[0] * ( zb - za ), lm[1] * ( zb - za ), -( yb - ya ) )
            outward( model, head if k in RAIL_HEAD_EDGES else paint,
                     [ at( i, ya, za ), at( i + 1, ya, za ), at( i + 1, yb, zb ), at( i, yb, zb ) ], towards )
    if caps:
        for i, t in ( ( 0, -tangents[0] ), ( len( pts ) - 1, tangents[-1] ) ):
            for piece in RAIL_CAP_PIECES:
                outward( model, paint, [ at( i, *RAIL_PROFILE[j] ) for j in piece ], ( t[0], t[1], 0.0 ) )


SLEEPERS = {    # length, width, height, spacing, paint
    "concrete": ( 102.4, 11.8, 8.7, 23.6, "rw_sleeper" ),          # B70: 2.6 m x 300 mm x 214 mm, every 600 mm
    "wood": ( 102.4, 10.2, 6.3, 25.6, "rw_sleeper_wood" ),         # oak: 2.6 m x 260 x 160 mm, every 650 mm
}


def sleeper( model, e0, e1, n, rail_z, kind="concrete", rails=() ):
    """ One sleeper across e0..e1 at n, its top under the rails' feet; wooden ones get a ribbed baseplate under each
    rail ( e ). """
    length, width, height, spacing, paint = SLEEPERS[kind]
    top = rail_z - 6.8 - ( 0.6 if kind == "wood" else 0.0 )
    model.box( ( e0, n - width / 2, top - height ), ( e1, n + width / 2, top ), paint, skip=( "-z", ) )
    if kind == "wood":
        for x in rails:
            model.box( ( x - 7.1, n - 3.15, top ), ( x + 7.1, n + 3.15, top + 0.6 ), "rw_rail", skip=( "-z", ) )
    if paint in GRAIN:
        model.grain_paints.add( paint )


def track( model, e, n0, n1, rail_z=-30.0, sleepers="concrete", embedded=False ):
    """ Plain track from n0 to n1: two UIC 60 rails at +-29.6 on B70 concrete sleepers every 600 mm (or wooden ones
    every 650 mm), their tops 6.8 under the rails' heads. embedded: the rails' heads flush with a paved floor at rail_z,
    with the flangeway's dark groove on each one's inside, and no sleepers. """
    lo, hi = min( n0, n1 ), max( n0, n1 )
    if embedded:
        z = rail_z + 0.03
        for side in ( -1, 1 ):
            x = e + side * GAUGE_HALF
            for paint, a, b in ( ( "rw_rail_head", -1.415, 1.415 ), ( "rw_black", -3.15, -1.415 ),
                                 ( "rw_rail", -3.75, -3.15 ) ):
                xa, xb = sorted( ( x + side * a, x + side * b ) )
                model.polygon( paint, [ ( xa, lo, z ), ( xb, lo, z ), ( xb, hi, z ), ( xa, hi, z ) ] )
        model.grain_paints.update( ( "rw_rail", "rw_rail_head" ) )
        return
    for side in ( -1, 1 ):
        rail( model, [ ( e + side * GAUGE_HALF, lo ), ( e + side * GAUGE_HALF, hi ) ], rail_z )
    if sleepers:
        length, width, height, spacing, paint = SLEEPERS[sleepers]
        count = max( 1, int( ( hi - lo ) // spacing ) )
        start = lo + ( hi - lo - ( count - 1 ) * spacing ) / 2
        for i in range( count ):
            sleeper( model, e - length / 2, e + length / 2, start + i * spacing, rail_z, sleepers,
                     ( e - GAUGE_HALF, e + GAUGE_HALF ) )


def crossover( model, e0, e1, n_start, facing, rail_z=-30.0, radius=7480.0, frog=9.0, sleepers="concrete",
               straight=True ):
    """ A crossover from the track at e0 to the parallel one at e1: two turnouts (EW 60-190-1:9 by default: a 190 m
    curve to a 1:9 frog), joined by a straight at the frog angle. The diverging route leaves e0's track at n_start
    heading facing (+1 north). Drawn: both tracks' straight rails over its length (straight=True), the curved stock
    rails and switch blades (set for the straight route: the curved blades stand open), the closure rails, both
    frogs with their wing rails and castings, the four check rails, the point machines and their rods, and sleepers
    under all of it (long ones spanning both tracks between the turnouts). Draw plain track up to n_start and from the
    n it returns, where the crossover ends. At 4.57 m between tracks the default is 62 m long; a 1:7.5 frog on a
    140 m curve (radius=5512, frog=7.5) makes it 53 m. """
    d = 1.0 if e1 > e0 else -1.0
    S, g, h, gap = abs( e1 - e0 ), GAUGE_HALF, 2.9, 4.5
    R, alpha = radius, math.atan( 1.0 / frog )
    xa = R * ( 1 - math.cos( alpha ) )
    if 2 * xa > S:
        alpha = math.acos( 1 - S / ( 2 * R ) )
        xa = S / 2
    sa = R * math.sin( alpha )
    ls = ( S - 2 * xa ) / math.tan( alpha )
    s_end = 2 * sa + ls
    half, blade = s_end / 2, min( 600.0, 0.7 * sa )

    def plan( s, x ):
        return ( e0 + d * x, n_start + facing * s )

    def centre( s ):
        if s <= sa:
            th = math.asin( min( 1.0, s / R ) )
            return R * ( 1 - math.cos( th ) ), th
        if s <= sa + ls:
            return xa + ( s - sa ) * math.tan( alpha ), alpha
        th = math.asin( min( 1.0, ( s_end - s ) / R ) )
        return S - R * ( 1 - math.cos( th ) ), th

    samples = sorted( set( [ float( s ) for s in np.arange( 0.0, s_end, 48.0 ) ] + [ sa, sa + ls, s_end ] ) )

    def line( off ):
        out = []
        for s in samples:
            x, th = centre( s )
            out.append( ( s - off * math.sin( th ), x + off * math.cos( th ) ) )
        return out

    minus = []          # the diverging route's rail nearer e0: turnout 1's curved blade, turnout 2's curved stock rail
    for s, x in line( -g ):
        if s < half:
            x = max( x, -g + h + gap * max( 0.0, 1 - s / blade ) )
        else:
            x = min( x, S - g - h )
        minus.append( ( s, x ) )
    minus.append( ( s_end + 40.0, S - g - h ) )
    plus = [ ( -40.0, g + h ) ]  # turnout 1's curved stock rail, turnout 2's curved blade
    for s, x in line( g ):
        if s < half:
            x = max( x, g + h )
        else:
            x = min( x, S + g - h - gap * max( 0.0, 1 - ( s_end - s ) / blade ) )
        plus.append( ( s, x ) )

    def draw( points ):
        rail( model, [ plan( s, x ) for s, x in points ], rail_z )

    draw( minus )
    draw( plus )
    if straight:
        for x in ( -g, g, S - g, S + g ):
            draw( [ ( 0.0, x ), ( s_end, x ) ] )

    def crossing( points, level ):
        for ( sa_, xa_ ), ( sb, xb ) in zip( points, points[1:] ):
            if ( xa_ - level ) * ( xb - level ) <= 0 and xb != xa_:
                return sa_ + ( level - xa_ ) / ( xb - xa_ ) * ( sb - sa_ )
        return None

    def along( points, s ):
        ss, xs = zip( *points )
        return float( np.interp( s, ss, xs ) )

    slope = math.tan( alpha )
    frogs = []
    f1 = crossing( minus, g )
    if f1 is not None:
        frogs.append( ( f1, g, 1.0, slope ) )      # the V opens towards +s: legs along +s and up the slope
    f2 = crossing( plus, S - g )
    if f2 is not None:
        frogs.append( ( f2, S - g, -1.0, slope ) )
    for sf, xf, way, sl in frogs:
        legs = [ np.array( ( way, 0.0 ) ), _unit( ( way, way * sl ) ) ]
        corners = []
        for i, leg in enumerate( legs ):
            other = legs[1 - i]
            side = np.array( ( -leg[1], leg[0] ) )
            if np.dot( side, other ) > 0:
                side = -side
            base = np.array( ( sf, xf ) )
            wing = [ base + leg * t + side * 4.4 for t in ( -60.0, 50.0 ) ] + [ base + leg * 72.0 + side * 7.0 ]
            draw( [ tuple( p ) for p in wing ] )
            corners += wing
        corners += [ np.array( ( sf + way * 110, xf + way * 110 * sl ) ) ]
        cs = np.array( corners )
        ( s_lo, x_lo ), ( s_hi, x_hi ) = cs.min( axis=0 ) - 3, cs.max( axis=0 ) + 3
        p, q = plan( s_lo, x_lo ), plan( s_hi, x_hi )
        model.box( ( min( p[0], q[0] ), min( p[1], q[1] ), rail_z - 6.8 ),
                   ( max( p[0], q[0] ), max( p[1], q[1] ), rail_z - 6.0 ), "rw_rail", skip=( "-z", ) )

    def check( points ):
        draw( points )

    if f1 is not None:
        x = -g + 4.0
        check( [ ( f1 - 100, x + 2.5 ), ( f1 - 80, x ), ( f1 + 80, x ), ( f1 + 100, x + 2.5 ) ] )
        check( [ ( s, along( plus, s ) - dx ) for s, dx in
                 ( ( f1 - 100, 6.5 ), ( f1 - 80, 4.0 ), ( f1, 4.0 ), ( f1 + 80, 4.0 ), ( f1 + 100, 6.5 ) ) ] )
    if f2 is not None:
        x = S + g - 4.0
        check( [ ( f2 - 100, x - 2.5 ), ( f2 - 80, x ), ( f2 + 80, x ), ( f2 + 100, x - 2.5 ) ] )
        check( [ ( s, along( minus, s ) + dx ) for s, dx in
                 ( ( f2 - 100, 6.5 ), ( f2 - 80, 4.0 ), ( f2, 4.0 ), ( f2 + 80, 4.0 ), ( f2 + 100, 6.5 ) ) ] )

    # Point machines beside each toe, with their rods to the blades.
    for s_toe, x_out, x_in, way in ( ( 0.0, -g - 9.0, g + h + 4.0, 1.0 ), ( s_end, S + g + 9.0, S - g - h - 4.0,
                                                                            -1.0 ) ):
        side = 1.0 if x_out > x_in else -1.0
        for ds, x0, x1, z0, z1, paint in ( ( ( 4.0, 40.0 ), x_out, x_out + side * 22.0, -7.5, 3.0, "rw_steel_grey" ),
                                           ( ( 7.0, 9.0 ), x_in, x_out + side * 4.0, -6.0, -4.8, "rw_steel_dark" ),
                                           ( ( 33.0, 35.0 ), x_in, x_out + side * 4.0, -6.0, -4.8,
                                             "rw_steel_dark" ) ):
            p, q = plan( s_toe + way * ds[0], x0 ), plan( s_toe + way * ds[1], x1 )
            model.box( ( min( p[0], q[0] ), min( p[1], q[1] ), rail_z + z0 ),
                       ( max( p[0], q[0] ), max( p[1], q[1] ), rail_z + z1 ), paint, skip=( "-z", ) )

    if sleepers:
        length, width, height, spacing, paint = SLEEPERS[sleepers]
        for s in np.arange( spacing / 2, s_end, spacing ):
            xs = [ -g, g, S - g, S + g ]
            if s >= 0:
                xs += [ along( minus, s ), along( plus, s ) ]
            xs.sort()
            groups = [ [ xs[0] ] ]
            for x in xs[1:]:
                if x - groups[-1][-1] < 70.0:
                    groups[-1].append( x )
                else:
                    groups.append( [ x ] )
            for grp in groups:
                a, b = plan( s, grp[0] - 21.6 ), plan( s, grp[-1] + 21.6 )
                sleeper( model, min( a[0], b[0] ), max( a[0], b[0] ), a[1], rail_z, sleepers,
                         [ e0 + d * x for x in grp ] )
    return n_start + facing * s_end


def buffer_stop( model, e, n, facing, rail_z=-30.0 ):
    """ A friction buffer stop clamped to the rails: two buffers (450 mm heads, 1750 mm apart, 1060 mm over the rail)
    on a red buffer beam, braced back to brake shoes on both rails, with a Sh 2 board (a red square in a white border)
    and its red lamp. (e, n) is the track's centre at the buffers' faces; facing +1 if they face north. It reaches 140
    behind them: run the track that far. One metal box. """
    f = vehicle_frame( e, n, facing, rail_z )
    red, dark = "rw_red_paint", "rw_steel_dark"
    for y in ( -BUFFER_HALF, BUFFER_HALF ):
        x = y * ( -1 if facing > 0 else 1 )         # Frame x is to the right of someone facing the buffers
        rod( model, f.p( x, 0.0, BUFFER_Z ), f.p( x, -1.6, BUFFER_Z ), 8.9, "rw_steel_grey", 12, caps=( True, False ) )
        rod( model, f.p( x, -1.6, BUFFER_Z ), f.p( x, -9.0, BUFFER_Z ), 3.6, "rw_steel_grey", 8 )
        rod( model, f.p( x, -9.0, BUFFER_Z ), f.p( x, -21.0, BUFFER_Z ), 5.3, red, 10, caps=( True, False ) )
    f.box( model, -47, 47, -33, -21, 30, 54, red )
    for x in ( -GAUGE_HALF, GAUGE_HALF ):
        f.box( model, x - 4, x + 4, -140, -10, -2.0, 6.0, dark )                    # brake shoes on the rail head
        f.box( model, x - 3, x + 3, -31, -23, 6.0, 30.0, red )                      # posts down to them
        model.beam( f.p( x, -30, 46 ), f.p( x, -122, 6 ), ( 6.0, 6.0 ), red )      # struts back to the shoes
    f.box( model, -GAUGE_HALF + 4, GAUGE_HALF - 4, -140, -130, 1.0, 7.0, red )
    f.box( model, -1.5, 1.5, -27.5, -24.5, 54, 98, "rw_steel_grey" )
    f.box( model, -12.6, 12.6, -24.5, -24.0, 72.0, 97.2, "rw_white_paint" )        # Sh 2: 600 mm board
    f.quad( model, "rw_red_paint", 0.0, -23.95, 84.6, 19.6, 19.6 )
    f.box( model, -3.5, 3.5, -24.5, -21.0, 58.5, 68.5, dark )
    disc( model, "rw_signal_red", f.p( 0.0, -20.95, 63.5 ), f.y, 2.6, 12 )
    f.collide( model, -50, 50, -140, 0, -7, 54, "metal" )


def ks_signal( model, e, n, rail_z, facing, side=+1, aspect="red", offset=94.0, height=150.0 ):
    """ A Ks main signal (Germany's combined light signal) on its mast beside the track at e, its screen facing the
    trains coming the other way (facing +1: north). side +1 puts it on the driver's right, the usual side, offset
    from the track's centre; the screen's centre is height over the rail. The 530 x 940 mm black screen in its white
    border carries the green lamp at the top, the yellow on the right, the red lower left and the three white Zs 1
    lamps below, each under its hood; the mast plate is white with red bands. aspect: "red", "green", "yellow",
    "red_zs1" or "dark". A metal box round the mast. """
    toward = 1 if facing > 0 else -1
    em = e + side * ( -toward ) * offset
    ground = rail_z - 7.0
    f = Frame( ( em, n, 0.0 ), ( 0, toward ) )
    model.box( ( em - 11, n - 11, ground - 2 ), ( em + 11, n + 11, ground + 5 ), "rw_concrete", skip=( "-z", ) )
    top = rail_z + height + 21.5
    model.cylinder( ( em, n ), 3.5, ground + 5, top - 1, { "side": "rw_steel_grey", "top": "rw_steel_grey" },
                    sides=10 )
    zc = rail_z + height
    f.box( model, -11.5, 11.5, 3.0, 6.5, zc - 19.5, zc + 19.5,
           { "default": "rw_steel_dark", "front": "rw_white_paint" } )
    f.quad( model, "rw_black", 0.0, 6.55, zc, 20.5, 36.5 )
    lamps = { "green": ( 0.0, 11.0 ), "yellow": ( 5.5, 1.0 ), "red": ( -5.5, -5.0 ) }
    lit = { "red": { "red" }, "green": { "green" }, "yellow": { "yellow" }, "red_zs1": { "red", "zs1" },
            "dark": set() }[aspect]
    for name, ( x, z ) in lamps.items():
        paint = f"rw_signal_{name}" if name in lit else "rw_window_dark"
        disc( model, paint, f.p( x, 6.65, zc + z ), f.y, 2.8, 12 )
        f.box( model, x - 3.6, x + 3.6, 6.6, 10.5, zc + z + 3.0, zc + z + 3.4, "rw_black" )
    for x, z in ( ( -3.0, -13.0 ), ( 3.0, -13.0 ), ( 0.0, -16.5 ) ):
        disc( model, "rw_lamp_cool" if "zs1" in lit else "rw_window_dark", f.p( x, 6.65, zc + z ), f.y, 0.9, 8 )
    for k in range( 5 ):
        f.quad( model, "rw_red_paint" if k % 2 else "rw_white_paint", 0.0, 3.6, rail_z + 69 + 4.72 * ( k + 0.5 ),
                7.9, 4.72 )
    model.collision_box( ( em - 4, n - 4, ground ), ( em + 4, n + 4, top ), "metal" )


# ---------------------------------------------------------------------------------------------------------------------
# Overhead line (Re 200: a 120 mm2 contact wire under a 70 mm2 messenger, 1.4 m of system height at the supports)

WIRE = "copper_brown"


def _sag( span ):
    """ The messenger's sag over a span: w L^2 / ( 8 T ), with 1.6 kg/m of messenger, contact wire and droppers
    under 15 kN. A 60 m span sags 0.47 m. """
    length = span / M
    return 1.6 * 9.81 * length * length / ( 8 * 15000.0 ) * M


def contact_line( model, e, n0, n1, rail_z, supports, wire_height=WIRE_HEIGHT, system_height=SYSTEM_HEIGHT,
                  stagger=STAGGER, first=+1 ):
    """ The overhead line over the track at e from n0 to n1, held at the supports (their n): the contact wire level at
    wire_height over the rail, zig-zagging +-stagger from one support to the next (first sets the first one's side,
    +1 east) so it wears the pantographs evenly; the messenger system_height over it at the supports, sagging between
    them; droppers at most 9 m apart. Visual only. Returns ( n, e offset, wire z, messenger z ) for each support, for
    the cantilever, portal or roof drop that holds it there. """
    lo, hi = min( n0, n1 ), max( n0, n1 )
    ns = sorted( set( float( s ) for s in supports ) )
    wz, mz = rail_z + wire_height, rail_z + wire_height + system_height
    offs = [ first * stagger * ( 1 if i % 2 == 0 else -1 ) for i in range( len( ns ) ) ]
    held = [ ( s, o ) for s, o in zip( ns, offs ) if lo - 1e-6 <= s <= hi + 1e-6 ]
    if not held:
        held = [ ( lo, 0.0 ), ( hi, 0.0 ) ]
    points = [ ( lo, held[0][1] ) ] + held + [ ( hi, held[-1][1] ) ]
    points = [ p for i, p in enumerate( points ) if i == 0 or p[0] - points[i - 1][0] > 1e-6 ]
    polyline( model, [ ( e + o, s, wz ) for s, o in points ], 0.24, WIRE, 4 )
    for ( sa, oa ), ( sb, ob ) in zip( points, points[1:] ):
        span = sb - sa
        supported = any( abs( sa - s ) < 1e-6 for s, _ in held ) and any( abs( sb - s ) < 1e-6 for s, _ in held )
        sag = _sag( span ) if supported else 0.0
        steps = max( 2, int( math.ceil( span / 240.0 ) ) )
        mess = []
        for k in range( steps + 1 ):
            t = k / steps
            mess.append( ( e + oa + ( ob - oa ) * t, sa + span * t, mz - 4 * sag * t * ( 1 - t ) ) )
        polyline( model, mess, 0.21, WIRE, 4 )
        if not supported:
            continue
        count = max( 2, int( math.ceil( span / 354.0 ) ) )
        for k in range( 1, count ):
            t = k / count
            x = e + oa + ( ob - oa ) * t
            rod( model, ( x, sa + span * t, mz - 4 * sag * t * ( 1 - t ) ), ( x, sa + span * t, wz + 0.2 ), 0.12,
                 WIRE, 3 )
    return [ ( s, o, wz, mz ) for s, o in held ]


def _h_mast( model, e, n, ground, top ):
    """ An HEB 200 mast (200 x 200 mm), its web across the track, on a concrete foundation. """
    model.box( ( e - 12, n - 12, ground - 2 ), ( e + 12, n + 12, ground + 6 ), "rw_concrete", skip=( "-z", ) )
    paint = "rw_steel_grey"
    for side in ( -1, 1 ):
        model.box( ( e + side * 3.95 - 0.3, n - 3.95, ground + 6 ), ( e + side * 3.95 + 0.3, n + 3.95, top ), paint,
                   skip=( "-z", ) )
    model.box( ( e - 3.65, n - 0.2, ground + 6 ), ( e + 3.65, n + 0.2, top ), paint, skip=( "-z", ) )


def _insulator( model, a, b ):
    """ A composite insulator along a..b: a rod with its sheds. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    axis = _unit( b - a )
    rod( model, a, b, 1.0, "rw_rubber", 6 )
    for t in np.linspace( 0.15, 0.85, 5 ):
        c = a + ( b - a ) * t
        rod( model, c - axis * 0.25, c + axis * 0.25, 2.3, "rw_rubber", 8, caps=( True, True ) )


def _registration( model, e_from, n, z_tube, e_wire, wz, toward ):
    """ The steady tube out to the registration arm, which holds the contact wire at its stagger. toward: the sign of
    e from the wire back to the support. """
    q = ( e_wire + toward * 40.0, n, wz + 8.0 )
    rod( model, ( e_from, n, z_tube ), ( q[0], n, z_tube ), 1.0, "rw_steel_grey", 6, caps=( True, True ) )
    if abs( z_tube - q[2] ) > 0.5:
        rod( model, ( q[0], n, z_tube ), q, 0.8, "rw_steel_grey", 6 )
    rod( model, q, ( e_wire + toward * 1.0, n, wz + 0.4 ), 0.7, "rw_steel_grey", 6 )
    model.box( ( e_wire - 1.2, n - 1.5, wz - 0.3 ), ( e_wire + 1.2, n + 1.5, wz + 1.2 ), "rw_steel_grey" )


def cantilever_mast( model, e_mast, n, e_track, rail_z, stagger=STAGGER, wire_height=WIRE_HEIGHT,
                     system_height=SYSTEM_HEIGHT ):
    """ A mast beside the track with a tubular swing cantilever (Re 200): the cantilever tube from the mast's head out
    over the track carries the messenger, the brace from lower on the mast props it, and the steady tube's registration
    arm holds the contact wire at e_track + stagger. Both tubes start at insulators by the mast. Metal collision on the
    mast only. Returns the wire's e there. """
    toward = 1.0 if e_track > e_mast else -1.0
    ground = rail_z - 7.0
    wz, mz = rail_z + wire_height, rail_z + wire_height + system_height
    top = mz + 34.0
    _h_mast( model, e_mast, n, ground, top )
    face = e_mast + toward * 4.25
    ew = e_track + stagger
    h1, h2 = np.array( ( face, n, mz + 16.0 ) ), np.array( ( face, n, wz - 4.0 ) )
    tip = np.array( ( ew - toward * 10.0, n, mz + 6.0 ) )
    for hinge in ( h1, h2 ):
        a, b = sorted( ( face, face + toward * 3 ) )
        model.box( ( a, n - 2.5, hinge[2] - 3 ), ( b, n + 2.5, hinge[2] + 3 ), "rw_steel_dark" )
    start1 = h1 + np.array( ( toward * 3.0, 0, 0 ) )
    ins1 = start1 + _unit( tip - start1 ) * 16.0
    _insulator( model, start1, ins1 )
    rod( model, ins1, tip, 1.2, "rw_steel_grey", 6, caps=( False, True ) )
    brace_end = start1 + ( tip - start1 ) * 0.82
    start2 = h2 + np.array( ( toward * 3.0, 0, 0 ) )
    ins2 = start2 + _unit( brace_end - start2 ) * 16.0
    _insulator( model, start2, ins2 )
    rod( model, ins2, brace_end, 1.1, "rw_steel_grey", 6 )
    hang = tip[2] + ( ew - tip[0] ) * ( tip[2] - ins1[2] ) / ( tip[0] - ins1[0] ) if abs( tip[0] - ins1[0] ) > 1 \
        else tip[2]
    rod( model, ( ew, n, mz ), ( ew, n, hang ), 0.5, "rw_steel_dark", 4 )
    model.box( ( ew - 1.5, n - 1.5, mz - 1.0 ), ( ew + 1.5, n + 1.5, mz + 1.0 ), "rw_steel_dark" )
    t = ( wz + 12.0 - ins2[2] ) / max( brace_end[2] - ins2[2], 1e-6 )
    on_brace = ins2 + ( brace_end - ins2 ) * min( max( t, 0.0 ), 1.0 )
    _registration( model, on_brace[0], n, on_brace[2], ew, wz, toward )
    model.collision_box( ( e_mast - 4.5, n - 4.5, ground ), ( e_mast + 4.5, n + 4.5, top ), "metal" )
    return ew


def _drop( model, e_track, n, z_from, wz, mz, stagger ):
    """ A drop tube hung over the track at e_track: an insulator under its hanger, the messenger's clamp on an arm out
    to the stagger, and the steady tube and registration arm for the contact wire. """
    ew = e_track + stagger
    toward = -1.0 if stagger > 0 else 1.0
    bottom = wz + 8.0
    rod( model, ( e_track, n, z_from ), ( e_track, n, z_from - 2.0 ), 1.2, "rw_steel_grey", 6 )
    _insulator( model, ( e_track, n, z_from - 2.0 ), ( e_track, n, z_from - 18.0 ) )
    rod( model, ( e_track, n, z_from - 18.0 ), ( e_track, n, bottom ), 1.2, "rw_steel_grey", 6, caps=( False, True ) )
    if abs( ew - e_track ) > 0.5:
        rod( model, ( e_track, n, mz ), ( ew, n, mz ), 0.8, "rw_steel_grey", 6, caps=( False, True ) )
    model.box( ( ew - 1.5, n - 1.5, mz - 1.0 ), ( ew + 1.5, n + 1.5, mz + 1.0 ), "rw_steel_dark" )
    _registration( model, e_track, n, bottom, ew, wz, toward )


def portal( model, e0, e1, n, rail_z, tracks, wire_height=WIRE_HEIGHT, system_height=SYSTEM_HEIGHT ):
    """ A portal across several tracks: HEB masts at e0 and e1 and a 600 mm lattice girder between them over the
    wires, with a drop tube over each track. tracks: e of each track, or ( e, stagger ). Metal collision on the
    masts. """
    ground = rail_z - 7.0
    wz, mz = rail_z + wire_height, rail_z + wire_height + system_height
    zb, zt = mz + 20.0, mz + 44.0
    for e in ( e0, e1 ):
        _h_mast( model, e, n, ground, zt )
        model.collision_box( ( e - 4.5, n - 4.5, ground ), ( e + 4.5, n + 4.5, zt ), "metal" )
    lo, hi = min( e0, e1 ) + 4.0, max( e0, e1 ) - 4.0
    lattice_box( model, ( lo, n - 6.0, zb ), ( hi, n + 6.0, zt ), axis="e" )
    for item in tracks:
        e, stagger = item if isinstance( item, ( tuple, list ) ) else ( item, STAGGER )
        _drop( model, e, n, zb, wz, mz, stagger )


def roof_drop( model, e_track, n, z_top, rail_z, stagger=STAGGER, wire_height=WIRE_HEIGHT,
               system_height=SYSTEM_HEIGHT ):
    """ The overhead line's support under a roof: a drop tube hung from the roof's steel at z_top, with its messenger
    clamp and registration arm. No collision. """
    wz, mz = rail_z + wire_height, rail_z + wire_height + system_height
    model.box( ( e_track - 4, n - 3, z_top - 1.0 ), ( e_track + 4, n + 3, z_top ), "rw_steel_dark" )
    _drop( model, e_track, n, z_top - 1.0, wz, mz, stagger )


def lattice_box( model, lo, hi, axis="e" ):
    """ A lattice girder along e (or n): its four faces rw_lattice, one panel a depth along and both sides drawn so the
    far face shows through the near one, between angle chords at its corners. """
    lo, hi = np.asarray( lo, float ), np.asarray( hi, float )
    k = 0 if axis == "e" else 1
    other = 1 - k
    depth, length, width = hi[2] - lo[2], hi[k] - lo[k], hi[other] - lo[other]

    def point( a, b, z ):
        p = np.zeros( 3 )
        p[k], p[other], p[2] = a, b, z
        return p

    panels = max( 1, round( length / depth ) )
    for b in ( lo[other], hi[other] ):
        model.polygon( "rw_lattice", [ point( lo[k], b, lo[2] ), point( hi[k], b, lo[2] ), point( hi[k], b, hi[2] ),
                                       point( lo[k], b, hi[2] ) ], both_sides=True,
                       uv=[ ( 0.0, 0.0 ), ( panels, 0.0 ), ( panels, 1.0 ), ( 0.0, 1.0 ) ] )
    across = max( 1, round( length / max( width, 1.0 ) ) )
    for z in ( lo[2], hi[2] ):
        model.polygon( "rw_lattice", [ point( lo[k], lo[other], z ), point( hi[k], lo[other], z ),
                                       point( hi[k], hi[other], z ), point( lo[k], hi[other], z ) ], both_sides=True,
                       uv=[ ( 0.0, 0.0 ), ( across, 0.0 ), ( across, 1.0 ), ( 0.0, 1.0 ) ] )
    for b, db in ( ( lo[other], 1.0 ), ( hi[other], -1.0 ) ):
        for z, dz in ( ( lo[2], 1.0 ), ( hi[2], -1.0 ) ):
            c0, c1 = point( lo[k], b, z ), point( hi[k], b + db * 1.0, z + dz * 1.0 )
            model.box( np.minimum( c0, c1 ), np.maximum( c0, c1 ), "rw_steel" )


# ---------------------------------------------------------------------------------------------------------------------
# Rolling stock: shared parts. In a vehicle's frame a is the depth behind its front face (y = -a), x across, z over
# the rail.

def _fpoly( model, F, paint, pts, towards, uv=None, normals=None ):
    """ A polygon in a frame's coordinates, turned to face towards ( local x, y, z ). """
    t = towards[0] * F.x + towards[1] * F.y + towards[2] * F.z
    world_normals = None if normals is None else [ n[0] * F.x + n[1] * F.y + n[2] * F.z for n in normals ]
    outward( model, paint, [ F.p( *p ) for p in pts ], t, uv=uv, normals=world_normals )


def _subtract( span, holes ):
    """ span ( lo, hi ) less the holes, as a list of pieces. """
    pieces = [ span ]
    for h0, h1 in holes:
        out = []
        for lo, hi in pieces:
            if h1 <= lo or h0 >= hi:
                out.append( ( lo, hi ) )
                continue
            if h0 > lo:
                out.append( ( lo, h0 ) )
            if h1 < hi:
                out.append( ( h1, hi ) )
        pieces = out
    return [ ( lo, hi ) for lo, hi in pieces if hi - lo > 1e-6 ]


def _banded_side( model, F, xs, x, a0, a1, bands, gaps ):
    """ One side wall at x * xs from depth a0 to a1, in horizontal bands ( z0, z1, paint ), less the gaps ( a0, a1,
    z0, z1 ) cut out of it (doorways, bogie cut-outs). """
    cuts = sorted( { a0, a1, *[ g for g0, g1, _, _ in gaps for g in ( g0, g1 ) if a0 < g < a1 ] } )
    for s0, s1 in zip( cuts, cuts[1:] ):
        mid = ( s0 + s1 ) / 2
        holes = [ ( z0, z1 ) for g0, g1, z0, z1 in gaps if g0 <= mid <= g1 ]
        for z0, z1, paint in bands:
            for lo, hi in _subtract( ( z0, z1 ), holes ):
                _fpoly( model, F, paint, [ ( xs * x, -s0, lo ), ( xs * x, -s1, lo ), ( xs * x, -s1, hi ),
                                           ( xs * x, -s0, hi ) ], ( xs, 0, 0 ) )


def _profile_normals( prof ):
    """ The outward normal ( x, z ) of each segment of a right-hand half profile listed bottom to top. """
    out = []
    for ( x0, z0 ), ( x1, z1 ) in zip( prof, prof[1:] ):
        nx, nz = z1 - z0, -( x1 - x0 )
        length = math.hypot( nx, nz ) or 1.0
        out.append( ( nx / length, nz / length ) )
    return out


def _extrude( model, F, prof, a0, a1, paint_of, smooth_from=None ):
    """ A half profile ( x, z ), bottom to top centre, extruded from depth a0 to a1 on both sides. paint_of( k ) paints
    segment k (None skips it); segments from smooth_from on are shaded smooth across their joints. """
    seg_n = _profile_normals( prof )
    point_n = []
    for k in range( len( prof ) ):
        if smooth_from is None or k < smooth_from:
            point_n.append( None )
            continue
        ns = [ seg_n[j] for j in ( k - 1, k ) if 0 <= j < len( seg_n ) and j >= smooth_from ]
        v = np.mean( ns, axis=0 ) if ns else np.array( seg_n[min( k, len( seg_n ) - 1 )] )
        point_n.append( v / ( np.linalg.norm( v ) or 1.0 ) )
    for k in range( len( prof ) - 1 ):
        paint = paint_of( k )
        if paint is None:
            continue
        ( xa, za ), ( xb, zb ) = prof[k], prof[k + 1]
        nx, nz = seg_n[k]
        for xs in ( 1.0, -1.0 ):
            if xa == 0 and xb == 0:
                continue
            pts = [ ( xs * xa, -a0, za ), ( xs * xb, -a0, zb ), ( xs * xb, -a1, zb ), ( xs * xa, -a1, za ) ]
            normals = None
            if point_n[k] is not None and point_n[k + 1] is not None:
                na, nb = point_n[k], point_n[k + 1]
                normals = [ ( xs * na[0], 0, na[1] ), ( xs * nb[0], 0, nb[1] ), ( xs * nb[0], 0, nb[1] ),
                            ( xs * na[0], 0, na[1] ) ]
            _fpoly( model, F, paint, pts, ( xs * nx, 0, nz ), normals=normals )


def _loft( model, F, rings, paint_of, fwd, under="rw_bogie" ):
    """ Strips between successive rings ( a, half profile ), each profile listed bottom to top centre with the same
    number of points, on both sides; paint_of( i, k ) paints the strip from ring i to i + 1, segment k. fwd: +1 or
    -1, the local y the first ring faces. Also closes the underside between the rings' bottom points in under (None:
    left open). """
    under_paint = under
    for i in range( len( rings ) - 1 ):
        ( a0, p0 ), ( a1, p1 ) = rings[i], rings[i + 1]
        seg_n = _profile_normals( p1 )
        for k in range( len( p0 ) - 1 ):
            paint = paint_of( i, k )
            if paint is None:
                continue
            nx, nz = seg_n[k]
            for xs in ( 1.0, -1.0 ):
                pts = [ ( xs * p0[k][0], -a0, p0[k][1] ), ( xs * p0[k + 1][0], -a0, p0[k + 1][1] ),
                        ( xs * p1[k + 1][0], -a1, p1[k + 1][1] ), ( xs * p1[k][0], -a1, p1[k][1] ) ]
                if p0[k][0] == 0 and p0[k + 1][0] == 0 and p1[k][0] == 0 and p1[k + 1][0] == 0:
                    continue
                _fpoly( model, F, paint, pts, ( xs * nx, 0.7 * fwd, nz ) )
        floor = [ ( p0[0][0], -a0, p0[0][1] ), ( -p0[0][0], -a0, p0[0][1] ), ( -p1[0][0], -a1, p1[0][1] ),
                  ( p1[0][0], -a1, p1[0][1] ) ]
        if under_paint:
            _fpoly( model, F, under_paint, floor, ( 0, 0, -1 ) )


def _section( model, F, prof, a, facing_y, paint, bottom=None ):
    """ A vehicle's cross-section as a flat end at depth a, facing local y facing_y (+1 or -1). """
    prof = list( prof )
    if bottom is not None:
        prof[0] = ( prof[0][0], bottom )
    right = [ ( x, -a, z ) for x, z in prof ]
    left = [ ( -x, -a, z ) for x, z in reversed( prof ) if x != 0 ]
    _fpoly( model, F, paint, right + left, ( 0, facing_y, 0 ) )


def _wheelset( model, F, a, r ):
    """ A wheelset at depth a: wheels of radius r (their treads on the rails, flanges inside) on their axle. """
    for xs in ( 1.0, -1.0 ):
        rod( model, F.p( xs * 27.8, -a, r ), F.p( xs * 32.1, -a, r ), r, "rw_bogie", 12,
             caps=( False, True ) )
        rod( model, F.p( xs * 26.8, -a, r ), F.p( xs * 27.8, -a, r ), r + 1.1, "rw_bogie", 12,
             caps=( True, False ) )
    rod( model, F.p( -26.8, -a, r ), F.p( 26.8, -a, r ), 3.3, "rw_bogie", 6 )


def _bogie( model, F, a, wheelbase, r, motor=False ):
    """ A two-axle bogie centred at depth a: its wheelsets, side frames with axle boxes and springs outside the wheels,
    and the transom; a traction motor between the axles if motor. """
    paint = "rw_bogie"
    for k in ( -1, 1 ):
        _wheelset( model, F, a + k * wheelbase / 2, r )
    reach = wheelbase / 2 + r * 0.85
    for xs in ( 1.0, -1.0 ):
        F.box( model, xs * 33.5, xs * 38.5, -( a - reach ), -( a + reach ), r + 1, r + 9, paint )
        F.box( model, xs * 33.5, xs * 38.5, -( a - wheelbase * 0.22 ), -( a + wheelbase * 0.22 ), r - 6, r + 1,
               paint, skip=( "top", ) )
        for k in ( -1, 1 ):
            y = -( a + k * wheelbase / 2 )
            F.box( model, xs * 33.0, xs * 40.0, y - 6, y + 6, r - 6, r + 5, paint, skip=( "top", ) )
            rod( model, F.p( xs * 36.5, y, r + 9 ), F.p( xs * 36.5, y, r + 15 ), 3.2, "rw_steel_dark", 8,
                 caps=( False, False ) )
    F.box( model, -38.5, 38.5, -( a - 7 ), -( a + 7 ), r + 2, r + 10, paint )
    if motor:
        F.box( model, -20, 20, -( a - wheelbase / 2 + r + 2 ), -( a - 4 ), r - 5, r + 9, paint )


def _buffer_end( model, F, a_face, s, beam_half=50.0, paint="rw_bogie", beam_paint="rw_train_dark" ):
    """ UIC side buffers and a screw coupling at an end whose buffer faces are at depth a_face; s +1 if they face the
    front (local +y). Buffers 1750 mm apart, 1060 mm over the rail, 620 mm long, on a buffer beam beam_half each
    way. """
    def y( d ):                 # d behind the buffer faces
        return -( a_face + s * d )

    for xs in ( 1.0, -1.0 ):
        x = xs * BUFFER_HALF
        rod( model, F.p( x, y( 0 ), BUFFER_Z ), F.p( x, y( 1.2 ), BUFFER_Z ), 7.0, "rw_steel_grey", 10,
             caps=( True, False ) )
        rod( model, F.p( x, y( 1.2 ), BUFFER_Z ), F.p( x, y( 10.0 ), BUFFER_Z ), 3.2, "rw_steel_grey", 6 )
        rod( model, F.p( x, y( 10.0 ), BUFFER_Z ), F.p( x, y( 23.0 ), BUFFER_Z ), 4.4, paint, 8,
             caps=( True, False ) )
        F.box( model, x - 6, x + 6, y( 23.0 ), y( 24.4 ), BUFFER_Z - 6, BUFFER_Z + 6, paint )
    F.box( model, -beam_half, beam_half, y( 24.4 ), y( 31.0 ), 30.0, 53.0, beam_paint )
    F.box( model, -1.6, 1.6, y( 4.0 ), y( 24.4 ), BUFFER_Z - 2.5, BUFFER_Z + 1.5, paint )    # draw hook
    for xs in ( 1.0, -1.0 ):                                                                   # the hanging link
        rod( model, F.p( xs * 2.6, y( 5.0 ), BUFFER_Z ), F.p( xs * 2.6, y( 7.0 ), BUFFER_Z - 13.0 ), 0.6,
             "rw_steel_dark", 4 )
    rod( model, F.p( -2.6, y( 7.0 ), BUFFER_Z - 13.0 ), F.p( 2.6, y( 7.0 ), BUFFER_Z - 13.0 ), 0.6, "rw_steel_dark", 4 )


def _pantograph( model, F, a, roof_z, head_z=None ):
    """ A single-arm pantograph on the roof (roof_z) at depth a, its base on four insulators: a 1.8 m lower arm and a
    2.2 m upper arm to a 1950 mm head with two carbon strips. head_z: the head's top (the wire's height over the rail)
    to raise it; None folds it down. """
    L1, L2 = 70.0, 85.0
    hy, hz = -( a - 30.0 ), roof_z + 9.0
    base = ( -( a - 34.0 ), -( a + 18.0 ) )
    for x in ( -18.0, 18.0 ):
        for yy in base:
            rod( model, F.p( x, yy, roof_z ), F.p( x, yy, roof_z + 5.0 ), 1.7, "rw_rubber", 6 )
    F.box( model, -22, 22, base[0], base[1], roof_z + 5.0, roof_z + 7.5, "rw_steel_grey" )
    if head_z is None:                             # folded down: the lower arm 8 degrees up, the upper arm back over it
        ky, kz = hy + L1 * math.cos( math.radians( 8.0 ) ), hz + L1 * math.sin( math.radians( 8.0 ) )
        pz = roof_z + 12.0
        py = ky - math.sqrt( L2 * L2 - ( kz - pz ) ** 2 )
    else:
        py = hy - 16.0                             # the head rides over the base, 16 behind the hinge
        pz = head_z - 4.0
        d = math.hypot( py - hy, pz - hz )
        d = min( max( d, abs( L2 - L1 ) + 0.1 ), L1 + L2 - 0.1 )
        ux, uz = ( py - hy ) / d, ( pz - hz ) / d
        k = ( L1 * L1 - L2 * L2 + d * d ) / ( 2 * d )
        h = math.sqrt( max( L1 * L1 - k * k, 0.0 ) )
        mx, mz = hy + k * ux, hz + k * uz
        cands = [ ( mx - h * uz, mz + h * ux ), ( mx + h * uz, mz - h * ux ) ]
        ky, kz = max( cands, key=lambda c: c[0] )  # the knee folds back past the hinge, away from the head
    for x in ( -11.0, 11.0 ):
        rod( model, F.p( x, hy, hz ), F.p( 0.0, ky, kz ), 1.3, "rw_steel_grey", 6 )
    F.box( model, -13, 13, hy - 3, hy + 3, roof_z + 7.5, hz + 2, "rw_steel_dark" )
    rod( model, F.p( 0.0, hy - 5.0, hz ), F.p( 0.0, ky, kz - 2.5 ), 0.5, "rw_steel_dark", 4 )
    rod( model, F.p( 0.0, ky, kz ), F.p( 0.0, py, pz ), 1.1, "rw_steel_grey", 6 )
    rod( model, F.p( -38.4, py, pz ), F.p( 38.4, py, pz ), 0.8, "rw_steel_grey", 6 )
    for dy in ( -5.5, 5.5 ):
        F.box( model, -30, 30, py + dy - 1.0, py + dy + 1.0, pz + 1.6, pz + 4.0, "rw_black" )
        rod( model, F.p( 0.0, py, pz ), F.p( 0.0, py + dy, pz + 1.6 ), 0.6, "rw_steel_grey", 4 )
        for xs in ( 1.0, -1.0 ):
            rod( model, F.p( xs * 30.0, py + dy, pz + 2.8 ), F.p( xs * 38.4, py + dy, pz - 2.5 ), 0.6,
                 "rw_steel_grey", 4 )
            rod( model, F.p( xs * 30.0, py + dy, pz + 1.6 ), F.p( xs * 30.0, py, pz ), 0.5, "rw_steel_grey", 4 )


# ---------------------------------------------------------------------------------------------------------------------
# The EMU: a two-car articulated low-floor regional unit (like Stadler's FLIRT): 19 m cars on a Jakobs bogie, 2.88 m
# wide and 4.18 m tall, its floor 760 mm over the rail, level with the platforms.

EMU_CAR = 748.0
EMU_W = 56.7
EMU_ROOF = 164.6
EMU_FLOOR = 30.0
EMU_GAP = 12.0
EMU_SKIRT = 19.0
EMU_CUT = 42.0
EMU_PROFILE = [ ( EMU_W, EMU_CUT ), ( EMU_W, 56.0 ), ( EMU_W, 104.0 ), ( EMU_W, 138.0 ), ( 55.5, 148.0 ),
                ( 51.5, 156.0 ), ( 44.0, 161.5 ), ( 30.0, 164.0 ), ( 0.0, EMU_ROOF ) ]
EMU_NOSE = [    # ( depth behind the coupler's face, half profile ): the front face, the windscreen's foot and top
    ( 16.0, [ ( EMU_W - 11, 10.0 ), ( EMU_W - 12, 56.0 ), ( EMU_W - 15, 86.0 ), ( EMU_W - 20, 95.0 ), ( 34.0, 98.0 ),
              ( 28.0, 99.5 ), ( 21.0, 100.5 ), ( 12.0, 101.2 ), ( 0.0, 101.4 ) ] ),
    ( 26.0, [ ( EMU_W - 6, 10.0 ), ( EMU_W - 6.5, 56.0 ), ( EMU_W - 9, 92.0 ), ( EMU_W - 14, 102.0 ), ( 41.0, 106.0 ),
              ( 35.0, 108.5 ), ( 27.0, 110.0 ), ( 16.0, 111.0 ), ( 0.0, 111.3 ) ] ),
    ( 60.0, [ ( EMU_W - 1, EMU_CUT ), ( EMU_W - 1, 56.0 ), ( EMU_W - 1.5, 104.0 ), ( EMU_W - 4, 134.0 ),
              ( 51.0, 144.0 ), ( 46.5, 151.5 ), ( 38.5, 156.5 ), ( 26.0, 159.0 ), ( 0.0, 159.6 ) ] ),
    ( 96.0, EMU_PROFILE ),
]
EMU_BOGIE = 116.0           # an end bogie's centre behind the coupler's face
EMU_WHEELBASE = 106.0       # 2.7 m motor bogies
EMU_WHEEL = 18.1            # 920 mm wheels


def _emu_cab( model, F, a_face, s, body ):
    """ A cab end: the nose lofted from its front face to the full section, the coupler, the lamps. a_face: the
    coupler's face; s +1 for a cab facing the front (local +y), -1 for the far end. """
    rings = [ ( a_face + s * d, prof ) for d, prof in EMU_NOSE ]

    def paint_of( i, k ):
        if i == 0:
            return "rw_train_dark" if k == 0 else body
        if i == 1:
            return body if k <= 1 else "rw_window_dark"
        return { 0: body, 1: "rw_window_dark", 2: body }.get( k, "rw_train_grey" if k >= 4 else body )

    _loft( model, F, rings, paint_of, s )
    a16 = a_face + s * 16.0
    _section( model, F, EMU_NOSE[0][1], a16, s, body )
    front = a_face + s * 15.9
    _fpoly( model, F, "rw_train_dark", [ ( -15, -front, 28 ), ( 15, -front, 28 ), ( 15, -front, 52 ),
                                          ( -15, -front, 52 ) ], ( 0, s, 0 ) )
    _fpoly( model, F, "rw_lamp_cool", [ ( -5, -front, 92 ), ( 5, -front, 92 ), ( 5, -front, 95 ),
                                         ( -5, -front, 95 ) ], ( 0, s, 0 ) )
    for xs in ( 1.0, -1.0 ):
        _fpoly( model, F, "rw_lamp_cool", [ ( xs * 26, -front, 74 ), ( xs * 38, -front, 74 ), ( xs * 38, -front, 79 ),
                                             ( xs * 26, -front, 79 ) ], ( 0, s, 0 ) )
        _fpoly( model, F, "rw_signal_red", [ ( xs * 39.5, -front, 74 ), ( xs * 42.5, -front, 74 ),
                                              ( xs * 42.5, -front, 79 ), ( xs * 39.5, -front, 79 ) ], ( 0, s, 0 ) )
    y0, y1 = -( a_face ), -( a_face + s * 16.0 )
    F.box( model, -4.5, 4.5, y0 - s * 3.0, y1, 34.5, 45.5, "rw_bogie" )
    F.box( model, -7.0, 7.0, y0, y0 - s * 3.0, 33.0, 47.0, "rw_train_dark" )


def emu( model, e, n_front, facing, rail_z=-30.0, cars=2, body="rw_train_blue", platform_side=-1, doors_open=True,
         wire_z=None ):
    """ A low-floor EMU of `cars` 19 m cars (2: 38.5 m over the couplers), cab ends both ways, two pairs of 1.3 m
    sliding plug doors a side per car. Livery: body below a white stripe, a dark window band, a near-black skirt, a
    grey roof. platform_side (+1 east, -1 west): the side whose doors stand open (doors_open), each into a 1.4 m deep
    vestibule floored level with the platform (rail_z + 30) under a 2 m ceiling; the other side's stay shut. wire_z:
    the contact wire's z, to raise the pantograph on to it; None leaves it down. Metal collision per car, hollowed at
    the open vestibules, and across the gangway between cars. Returns the far coupler's n. """
    F = vehicle_frame( e, n_front, facing, rail_z )
    xs_open = platform_side * F.x[0]
    total = 2 * 16.0 + cars * EMU_CAR + ( cars - 1 ) * EMU_GAP
    starts = [ 16.0 + i * ( EMU_CAR + EMU_GAP ) for i in range( cars ) ]
    bogies = [ ( EMU_BOGIE, True ) ] + [ ( s0 - EMU_GAP / 2, False ) for s0 in starts[1:] ] + \
             [ ( total - EMU_BOGIE, True ) ]
    zones = [ ( c - 72.0, c + 72.0 ) for c, _ in bogies ]
    for c, motor in bogies:
        _bogie( model, F, c, EMU_WHEELBASE if motor else 98.0, EMU_WHEEL if motor else 16.0, motor )
    bands = [ ( EMU_SKIRT, EMU_FLOOR, "rw_train_dark" ), ( EMU_FLOOR, 56.0, body ), ( 56.0, 59.0, "rw_train_white" ),
              ( 59.0, 104.0, "rw_window_dark" ), ( 104.0, 108.0, body ), ( 108.0, 138.0, body ) ]
    _emu_cab( model, F, 0.0, 1, body )
    _emu_cab( model, F, total, -1, body )
    pan_at = starts[-1] + 130.0 if cars > 1 else total / 2
    _pantograph( model, F, pan_at, EMU_ROOF, None if wire_z is None else wire_z - rail_z )
    for i, a0 in enumerate( starts ):
        a1 = a0 + EMU_CAR
        s0 = a0 + 80.0 if i == 0 else a0               # the straight body, after any nose
        s1 = a1 - 80.0 if i == cars - 1 else a1
        if i == 0 and cars == 1:
            doors = [ a0 + 234.0, a1 - 285.0 ]
        elif i == 0:
            doors = [ a0 + 234.0, a0 + 524.0 ]
        elif i == cars - 1:
            doors = [ a1 - 285.0, a1 - 575.0 ]
        else:
            doors = [ a0 + 190.0, a1 - 241.0 ]
        doors = sorted( doors )
        cut = [ ( z0, z1, EMU_SKIRT, EMU_CUT ) for z0, z1 in zones ]
        for xs in ( 1.0, -1.0 ):
            gaps = cut + [ ( d, d + 51.0, EMU_FLOOR, 108.0 ) for d in doors ]
            _banded_side( model, F, xs, EMU_W, s0, s1, bands, gaps )
            for p0, p1 in zip( [ s0 ] + [ d + 51.0 for d in doors ], [ d for d in doors ] + [ s1 ] ):   # pillars
                count = int( ( p1 - p0 ) // 70.0 )
                for k in range( 1, count + 1 ):
                    pa = p0 + ( p1 - p0 ) * k / ( count + 1 )
                    _fpoly( model, F, body, [ ( xs * ( EMU_W + 0.08 ), -( pa - 3.5 ), 59.0 ),
                                              ( xs * ( EMU_W + 0.08 ), -( pa + 3.5 ), 59.0 ),
                                              ( xs * ( EMU_W + 0.08 ), -( pa + 3.5 ), 104.0 ),
                                              ( xs * ( EMU_W + 0.08 ), -( pa - 3.5 ), 104.0 ) ], ( xs, 0, 0 ) )
            for d in doors:
                if doors_open and xs == xs_open:
                    _emu_vestibule( model, F, xs, d, d + 51.0 )
                else:
                    _emu_door( model, F, xs, d, d + 51.0 )
        _extrude( model, F, EMU_PROFILE[3:], s0, s1,
                  lambda k: body if k == 0 else "rw_train_grey", smooth_from=0 )
        cuts = sorted( { s0, s1, *[ z for zz in zones for z in zz if s0 < z < s1 ] } )
        for c0, c1 in zip( cuts, cuts[1:] ):
            inside = any( z0 <= ( c0 + c1 ) / 2 <= z1 for z0, z1 in zones )
            zb = EMU_CUT if inside else EMU_SKIRT
            _fpoly( model, F, "rw_bogie", [ ( EMU_W, -c0, zb ), ( -EMU_W, -c0, zb ), ( -EMU_W, -c1, zb ),
                                             ( EMU_W, -c1, zb ) ], ( 0, 0, -1 ) )
        for z0, z1 in zones:
            for b, into in ( ( z0, -1 ), ( z1, 1 ) ):          # the cut-outs' ends, facing the bogie
                if s0 < b < s1:
                    _fpoly( model, F, "rw_bogie", [ ( EMU_W, -b, EMU_SKIRT ), ( -EMU_W, -b, EMU_SKIRT ),
                                                     ( -EMU_W, -b, EMU_CUT ), ( EMU_W, -b, EMU_CUT ) ],
                            ( 0, into, 0 ) )
        if i > 0:
            _section( model, F, EMU_PROFILE, a0, 1, body )
        if i < cars - 1:
            _section( model, F, EMU_PROFILE, a1, -1, body )
            F.box( model, -40, 40, -a1, -( a1 + EMU_GAP ), 33.0, 150.0, "rw_rubber", skip=( "bottom", ) )
            F.collide( model, -40, 40, -a1, -( a1 + EMU_GAP ), -7.0, 150.0, "metal" )
        for k in range( 2 ):                                  # air conditioning on the roof
            ac = a0 + ( 200.0 if k == 0 else 470.0 )
            if abs( ac + 40.0 - pan_at ) < 110.0:
                continue
            F.box( model, -28, 28, -ac, -( ac + 90.0 ), EMU_ROOF - 3.0, EMU_ROOF + 11.0, "rw_train_grey",
                   skip=( "bottom", ) )
        _emu_collision( model, F, i, cars, a0, a1, doors if doors_open else [], xs_open )
    return n_front - ( 1 if facing > 0 else -1 ) * total


def _emu_door( model, F, xs, d0, d1 ):
    """ A shut pair of sliding plug doors filling the doorway d0..d1. """
    x = xs * ( EMU_W + 0.1 )
    _fpoly( model, F, "rw_train_white", [ ( x, -d0, EMU_FLOOR ), ( x, -d1, EMU_FLOOR ), ( x, -d1, 108.0 ),
                                          ( x, -d0, 108.0 ) ], ( xs, 0, 0 ) )
    x2 = xs * ( EMU_W + 0.2 )
    mid = ( d0 + d1 ) / 2
    for p0, p1 in ( ( d0 + 4.0, mid - 3.0 ), ( mid + 3.0, d1 - 4.0 ) ):
        _fpoly( model, F, "rw_window_dark", [ ( x2, -p0, 62.0 ), ( x2, -p1, 62.0 ), ( x2, -p1, 100.0 ),
                                              ( x2, -p0, 100.0 ) ], ( xs, 0, 0 ) )
    _fpoly( model, F, "rw_black", [ ( x2, -( mid - 0.4 ), EMU_FLOOR ), ( x2, -( mid + 0.4 ), EMU_FLOOR ),
                                    ( x2, -( mid + 0.4 ), 108.0 ), ( x2, -( mid - 0.4 ), 108.0 ) ], ( xs, 0, 0 ) )


def _emu_vestibule( model, F, xs, d0, d1 ):
    """ An open doorway: the leaves slid open outside the skin, and the vestibule behind it to the car's centre line,
    floored at the platform's height, with its glazed screens, ceiling light and grab poles. """
    W = EMU_W
    for p0, p1 in ( ( d0 - 25.5, d0 ), ( d1, d1 + 25.5 ) ):
        F.box( model, xs * W, xs * ( W + 1.6 ), -p0, -p1, EMU_FLOOR + 1.0, 107.0, "rw_train_white" )
        F.collide( model, xs * W, xs * ( W + 1.6 ), -p0, -p1, EMU_FLOOR + 1.0, 107.0, "metal" )
        x = xs * ( W + 1.65 )
        _fpoly( model, F, "rw_window_dark", [ ( x, -( p0 + 4.0 ), 62.0 ), ( x, -( p1 - 4.0 ), 62.0 ),
                                              ( x, -( p1 - 4.0 ), 100.0 ), ( x, -( p0 + 4.0 ), 100.0 ) ], ( xs, 0, 0 ) )
    xw = xs * W
    _fpoly( model, F, "rw_rubber", [ ( 0, -d0, EMU_FLOOR ), ( xw, -d0, EMU_FLOOR ), ( xw, -d1, EMU_FLOOR ),
                                     ( 0, -d1, EMU_FLOOR ) ], ( 0, 0, 1 ) )
    _fpoly( model, F, "rw_train_white", [ ( 0, -d0, 108.0 ), ( xw, -d0, 108.0 ), ( xw, -d1, 108.0 ),
                                          ( 0, -d1, 108.0 ) ], ( 0, 0, -1 ) )
    _fpoly( model, F, "rw_lamp_cool", [ ( xs * 8, -( ( d0 + d1 ) / 2 - 2 ), 107.9 ),
                                        ( xs * ( W - 8 ), -( ( d0 + d1 ) / 2 - 2 ), 107.9 ),
                                        ( xs * ( W - 8 ), -( ( d0 + d1 ) / 2 + 2 ), 107.9 ),
                                        ( xs * 8, -( ( d0 + d1 ) / 2 + 2 ), 107.9 ) ], ( 0, 0, -1 ) )
    for a, into in ( ( d0, -1 ), ( d1, 1 ) ):
        for z0, z1, paint in ( ( EMU_FLOOR, 66.0, "rw_train_white" ), ( 66.0, 108.0, "rw_window_dark" ) ):
            _fpoly( model, F, paint, [ ( 0, -a, z0 ), ( xw, -a, z0 ), ( xw, -a, z1 ), ( 0, -a, z1 ) ], ( 0, into, 0 ) )
    for z0, z1, paint in ( ( EMU_FLOOR, 60.0, "rw_train_white" ), ( 60.0, 108.0, "rw_window_dark" ) ):
        _fpoly( model, F, paint, [ ( 0, -d0, z0 ), ( 0, -d1, z0 ), ( 0, -d1, z1 ), ( 0, -d0, z1 ) ], ( xs, 0, 0 ) )
    for a in ( d0 + 4.0, d1 - 4.0 ):
        rod( model, F.p( xs * ( W - 6.0 ), -a, EMU_FLOOR ), F.p( xs * ( W - 6.0 ), -a, 108.0 ), 0.75,
             "rw_yellow_paint", 6 )


def _emu_collision( model, F, i, cars, a0, a1, doors, xs ):
    """ One car's metal boxes: solid from rail_z - 7 to the roof, the nose stepped down, hollowed at the open
    vestibules on side xs. """
    W, top = EMU_W, EMU_ROOF
    lo = a0 + ( 44.0 if i == 0 else 0.0 )
    hi = a1 - ( 44.0 if i == cars - 1 else 0.0 )
    if i == 0:
        F.collide( model, -( W - 6 ), W - 6, -a0, -lo, -7.0, 112.0, "metal" )
    if i == cars - 1:
        F.collide( model, -( W - 6 ), W - 6, -hi, -a1, -7.0, 112.0, "metal" )
    if not doors:
        F.collide( model, -W, W, -lo, -hi, -7.0, top, "metal" )
        return
    F.collide( model, 0.0, -xs * W, -lo, -hi, -7.0, top, "metal" )
    edges = [ lo ] + [ v for d in sorted( doors ) for v in ( d, d + 51.0 ) ] + [ hi ]
    for k in range( 0, len( edges ) - 1 ):
        p0, p1 = edges[k], edges[k + 1]
        if k % 2 == 0:
            F.collide( model, 0.0, xs * W, -p0, -p1, -7.0, top, "metal" )
        else:
            F.collide( model, 0.0, xs * W, -p0, -p1, -7.0, EMU_FLOOR, "metal" )
            F.collide( model, 0.0, xs * W, -p0, -p1, 108.0, top, "metal" )


def _far( n_front, facing, length ):
    return n_front - ( 1 if facing > 0 else -1 ) * length


def _end_collision( model, F, L, inset ):
    """ The buffers' and buffer beams' metal boxes at both ends, ahead of a body that starts inset in. """
    for a0, a1 in ( ( 0.0, inset ), ( L - inset, L ) ):
        F.collide( model, -48, 48, -a0, -a1, 28.0, 55.0, "metal" )


def _lamps( model, F, face, s, z, outer=( 34.0, 44.0 ), tail=( 27.0, 31.0 ), top=None ):
    """ Two headlights (outer: |x| from, to) with a tail light inside each, at height z, on a flat end face at depth
    face facing s; a third headlight centred at top if given. """
    front = face - s * 0.1
    for xs in ( 1.0, -1.0 ):
        for ( x0, x1 ), paint in ( ( outer, "rw_lamp_cool" ), ( tail, "rw_signal_red" ) ):
            _fpoly( model, F, paint, [ ( xs * x0, -front, z ), ( xs * x1, -front, z ), ( xs * x1, -front, z + 5.0 ),
                                       ( xs * x0, -front, z + 5.0 ) ], ( 0, s, 0 ) )
    if top is not None:
        _fpoly( model, F, "rw_lamp_cool", [ ( -4.0, -front, top ), ( 4.0, -front, top ), ( 4.0, -front, top + 3.0 ),
                                             ( -4.0, -front, top + 3.0 ) ], ( 0, s, 0 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The locomotive: a four-axle electric (Bo'Bo', the size of a Vectron or TRAXX): 19.6 m over the buffers, 3.0 m wide,
# the roof 4.0 m over the rail, 1250 mm wheels in bogies 10.4 m apart.

LOCO_LENGTH = 772.0
LOCO_W = 59.0
LOCO_ROOF = 158.0
LOCO_NOSE = [   # ( depth behind the buffers' faces, half profile ): the front face, the windscreen's top, the body
    ( 26.0, [ ( 55.0, 44.0 ), ( 55.0, 95.0 ), ( 53.0, 99.0 ), ( 49.0, 101.0 ), ( 40.0, 102.5 ), ( 26.0, 103.5 ),
              ( 0.0, 104.0 ) ] ),
    ( 46.0, [ ( 57.5, 44.0 ), ( 57.5, 95.0 ), ( 57.0, 112.0 ), ( 55.0, 138.0 ), ( 49.0, 144.0 ), ( 36.0, 147.0 ),
              ( 0.0, 148.0 ) ] ),
    ( 64.0, [ ( LOCO_W, 44.0 ), ( LOCO_W, 95.0 ), ( LOCO_W, 116.0 ), ( LOCO_W, 140.0 ), ( 55.0, 151.0 ),
              ( 40.0, 157.2 ), ( 0.0, LOCO_ROOF ) ] ),
]


def _loco_cab( model, F, a_face, s, body ):
    """ A locomotive's cab end, its buffers' faces at depth a_face, s +1 if it faces the front. """
    rings = [ ( a_face + s * d, prof ) for d, prof in LOCO_NOSE ]

    def paint_of( i, k ):
        if i == 0:
            return body if k <= 1 else "rw_window_dark"
        return { 2: "rw_window_dark" }.get( k, body if k <= 3 else "rw_train_grey" )

    _loft( model, F, rings, paint_of, s )
    face = a_face + s * LOCO_NOSE[0][0]
    _section( model, F, LOCO_NOSE[0][1], face, s, body )
    _lamps( model, F, face, s, 64.0, top=94.0 )
    F.box( model, -50, 50, -( a_face + s * 20.0 ), -( a_face + s * 30.0 ), 4.0, 30.0, "rw_train_dark",
           skip=( "top", ) )                                                     # the obstacle deflector
    _buffer_end( model, F, a_face, s, beam_half=56.0, beam_paint="rw_train_dark" )
    for xs in ( 1.0, -1.0 ):                                                     # the cab door and its steps
        d0, d1 = a_face + s * 68.0, a_face + s * 88.0
        for z in ( 20.0, 32.0 ):
            F.box( model, xs * ( LOCO_W - 5.0 ), xs * ( LOCO_W - 0.5 ), -d0, -d1, z, z + 1.5, "rw_bogie" )
        F.box( model, xs * LOCO_W, xs * ( LOCO_W + 0.4 ), -d0, -d1, 46.0, 138.0, body, skip=( "bottom", ) )
        x = xs * ( LOCO_W + 0.45 )
        _fpoly( model, F, "rw_window_dark", [ ( x, -( d0 + s * 3.0 ), 108.0 ), ( x, -( d1 - s * 3.0 ), 108.0 ),
                                              ( x, -( d1 - s * 3.0 ), 132.0 ), ( x, -( d0 + s * 3.0 ), 132.0 ) ],
                ( xs, 0, 0 ) )
        rod( model, F.p( xs * ( LOCO_W + 1.5 ), -( d0 - s * 2.0 ), 50.0 ),
             F.p( xs * ( LOCO_W + 1.5 ), -( d0 - s * 2.0 ), 130.0 ), 0.6, "rw_steel_grey", 4 )


def loco( model, e, n_front, facing, rail_z=-30.0, body="rw_train_red", wire_z=None ):
    """ A four-axle electric locomotive with a cab at each end: the body in body above a dark skirt, a white line,
    grey cooling grilles, a grey roof with the main breaker and two single-arm pantographs (the trailing one raised to
    the contact wire at wire_z if given), UIC buffers and screw couplings at both ends. Metal collision. Returns the
    far buffers' n. """
    F = vehicle_frame( e, n_front, facing, rail_z )
    L, W = LOCO_LENGTH, LOCO_W
    _loco_cab( model, F, 0.0, 1, body )
    _loco_cab( model, F, L, -1, body )
    s0, s1 = LOCO_NOSE[-1][0], L - LOCO_NOSE[-1][0]
    for xs in ( 1.0, -1.0 ):
        _banded_side( model, F, xs, W, s0, s1, [ ( 44.0, 140.0, body ) ], [] )
        x = xs * ( W + 0.1 )
        for k in range( 4 ):                    # cooling grilles: louvres in the body colour over a dark recess
            g0, g1 = 170.0 + k * 112.0, 262.0 + k * 112.0
            _fpoly( model, F, "rw_train_dark", [ ( x, -g0, 112.0 ), ( x, -g1, 112.0 ), ( x, -g1, 136.0 ),
                                                 ( x, -g0, 136.0 ) ], ( xs, 0, 0 ) )
            for j in range( 6 ):
                z = 113.0 + j * 4.0
                _fpoly( model, F, body, [ ( x + xs * 1.0, -g0, z ), ( x + xs * 1.0, -g1, z ),
                                          ( x + xs * 0.1, -g1, z + 3.0 ), ( x + xs * 0.1, -g0, z + 3.0 ) ],
                        ( xs, 0, -0.3 ) )
        for z0, z1, paint in ( ( 44.0, 52.0, "rw_train_dark" ), ( 56.0, 58.0, "rw_white_paint" ) ):
            _fpoly( model, F, paint, [ ( x, -s0, z0 ), ( x, -s1, z0 ), ( x, -s1, z1 ), ( x, -s0, z1 ) ], ( xs, 0, 0 ) )
    _extrude( model, F, LOCO_NOSE[-1][1][3:], s0, s1, lambda k: body if k == 0 else "rw_train_grey", smooth_from=0 )
    _fpoly( model, F, "rw_bogie", [ ( W, -s0, 44.0 ), ( -W, -s0, 44.0 ), ( -W, -s1, 44.0 ), ( W, -s1, 44.0 ) ],
            ( 0, 0, -1 ) )
    for c in ( L / 2 - 204.5, L / 2 + 204.5 ):
        _bogie( model, F, c, 104.0, 24.6, motor=True )
    F.box( model, -44, 44, -( L / 2 - 118.0 ), -( L / 2 + 118.0 ), 16.0, 44.0, "rw_bogie", skip=( "top", ) )
    for xs in ( 1.0, -1.0 ):
        F.box( model, xs * 44.0, xs * 52.0, -( L / 2 - 110.0 ), -( L / 2 - 30.0 ), 24.0, 44.0, "rw_train_grey",
               skip=( "top", ) )
    for k, c in enumerate( ( 150.0, L - 150.0 ) ):
        raised = wire_z is not None and k == 1
        _pantograph( model, F, c, LOCO_ROOF - 1.0, wire_z - rail_z if raised else None )
    F.box( model, -18, 18, -( L / 2 - 110.0 ), -( L / 2 + 110.0 ), LOCO_ROOF - 1.0, LOCO_ROOF + 7.0, "rw_train_grey",
           skip=( "bottom", ) )
    for c in ( L / 2 - 80.0, L / 2 + 80.0 ):
        for x in ( -10.0, 10.0 ):
            rod( model, F.p( x, -c, LOCO_ROOF + 7.0 ), F.p( x, -c, LOCO_ROOF + 14.0 ), 2.2, "rw_rubber", 6,
                 caps=( False, True ) )
    F.collide( model, -W, W, -LOCO_NOSE[0][0], -( L - LOCO_NOSE[0][0] ), -7.0, LOCO_ROOF, "metal" )
    _end_collision( model, F, L, LOCO_NOSE[0][0] )
    return _far( n_front, facing, L )


# ---------------------------------------------------------------------------------------------------------------------
# Coaches: UIC-Z size, 26.4 m over the buffers, 2.83 m wide, the floor 1.25 m and the roof 4.05 m over the rail, on
# bogies 19 m apart; a door near each end of each side, eleven windows a side.

COACH_LENGTH = 1039.0
COACH_W = 55.5
COACH_ROOF = 159.5
COACH_PROFILE = [ ( 53.5, 38.0 ), ( COACH_W, 48.0 ), ( COACH_W, 72.0 ), ( COACH_W, 112.0 ), ( COACH_W, 122.0 ),
                  ( 54.0, 135.0 ), ( 49.0, 147.0 ), ( 38.0, 155.5 ), ( 22.0, 158.8 ), ( 0.0, COACH_ROOF ) ]
COACH_CAB = [   # a driving trailer's cab: the front face, the windscreen's top, the body
    ( 26.0, [ ( 50.0, 38.0 ), ( 51.0, 48.0 ), ( 50.0, 72.0 ), ( 49.0, 86.0 ), ( 47.0, 92.0 ), ( 42.0, 96.0 ),
              ( 34.0, 98.5 ), ( 24.0, 99.6 ), ( 12.0, 100.2 ), ( 0.0, 100.4 ) ] ),
    ( 46.0, [ ( 53.0, 38.0 ), ( 54.5, 48.0 ), ( 54.5, 72.0 ), ( 54.5, 112.0 ), ( 54.0, 122.0 ), ( 52.0, 134.0 ),
              ( 46.0, 141.0 ), ( 34.0, 145.0 ), ( 18.0, 146.6 ), ( 0.0, 147.0 ) ] ),
    ( 70.0, COACH_PROFILE ),
]
COACH_DOOR = 32.0                # 810 mm doorways


def _coach( model, e, n_front, facing, rail_z, body, cab ):
    F = vehicle_frame( e, n_front, facing, rail_z )
    L, W = COACH_LENGTH, COACH_W
    s0 = COACH_CAB[-1][0] if cab else 26.0
    s1 = L - 26.0
    if cab:
        def paint_of( i, k ):
            if i == 0:
                return body if k <= 2 else "rw_window_dark"
            return body if k <= 4 else "rw_train_grey"

        _loft( model, F, COACH_CAB, paint_of, 1 )
        _section( model, F, COACH_CAB[0][1], COACH_CAB[0][0], 1, body )
        _lamps( model, F, COACH_CAB[0][0], 1, 62.0, outer=( 30.0, 40.0 ), tail=( 23.0, 27.0 ), top=91.0 )
        F.box( model, -46, 46, -20.0, -30.0, 10.0, 30.0, "rw_train_dark", skip=( "top", ) )
        doors = [ 84.0, L - 76.0 ]
        windows = ( 130.0, L - 90.0 )
    else:
        doors = [ 44.0, L - 76.0 ]
        windows = ( 90.0, L - 90.0 )
    _extrude( model, F, COACH_PROFILE[:2], s0, s1, lambda k: body )
    _extrude( model, F, COACH_PROFILE[4:], s0, s1, lambda k: body if k == 0 else "rw_train_grey", smooth_from=1 )
    bands = [ ( 48.0, 72.0, body ), ( 72.0, 112.0, "rw_window_dark" ), ( 112.0, 122.0, body ) ]
    count = int( ( windows[1] - windows[0] ) // 78.0 )
    bay = ( windows[1] - windows[0] ) / count
    door_spans = [ ( d, d + COACH_DOOR ) for d in doors ]
    for xs in ( 1.0, -1.0 ):
        _banded_side( model, F, xs, W, s0, s1, bands, [ ( d0, d1, 30.0, 116.0 ) for d0, d1 in door_spans ] )
        x = xs * ( W + 0.08 )
        piers = [ ( s0, windows[0] ) ] + [ ( windows[0] + k * bay + 56.0, windows[0] + ( k + 1 ) * bay )
                                           for k in range( count ) ] + [ ( windows[1], s1 ) ]
        for p0, p1 in piers:
            for q0, q1 in _subtract( ( p0, p1 ), door_spans ):
                _fpoly( model, F, body, [ ( x, -q0, 72.0 ), ( x, -q1, 72.0 ), ( x, -q1, 112.0 ), ( x, -q0, 112.0 ) ],
                        ( xs, 0, 0 ) )
        if cab:                                                                  # the cab's side window
            xc = xs * ( W + 0.12 )
            _fpoly( model, F, "rw_window_dark", [ ( xc, -72.0, 80.0 ), ( xc, -80.0, 80.0 ), ( xc, -80.0, 108.0 ),
                                                  ( xc, -72.0, 108.0 ) ], ( xs, 0, 0 ) )
        for d0, d1 in door_spans:
            xd = xs * ( W + 0.05 )
            _fpoly( model, F, "rw_train_grey", [ ( xd, -d0, 30.0 ), ( xd, -d1, 30.0 ), ( xd, -d1, 116.0 ),
                                                 ( xd, -d0, 116.0 ) ], ( xs, 0, 0 ) )
            _fpoly( model, F, "rw_window_dark", [ ( x, -( d0 + 6.0 ), 76.0 ), ( x, -( d1 - 6.0 ), 76.0 ),
                                                  ( x, -( d1 - 6.0 ), 108.0 ), ( x, -( d0 + 6.0 ), 108.0 ) ],
                    ( xs, 0, 0 ) )
            F.box( model, xs * ( W - 8.0 ), xs * W, -( d0 + 1.0 ), -( d1 - 1.0 ), 28.0, 30.0, "rw_bogie" )
    _fpoly( model, F, "rw_bogie", [ ( 53.5, -s0, 38.0 ), ( -53.5, -s0, 38.0 ), ( -53.5, -s1, 38.0 ),
                                    ( 53.5, -s1, 38.0 ) ], ( 0, 0, -1 ) )
    for a, way in ( [ ( s1, -1 ) ] if cab else [ ( s0, 1 ), ( s1, -1 ) ] ):          # the gangways
        _section( model, F, COACH_PROFILE, a, way, body )
        g = a - way * 12.0
        F.box( model, -24, 24, -a, -g, 49.0, 132.0, "rw_rubber", skip=( "bottom", ) )
        gy = -( g - way * 0.05 )
        _fpoly( model, F, "rw_train_dark", [ ( -16, gy, 50.0 ), ( 16, gy, 50.0 ), ( 16, gy, 124.0 ),
                                             ( -16, gy, 124.0 ) ], ( 0, way, 0 ) )
    for c in ( L / 2 - 374.0, L / 2 + 374.0 ):
        _bogie( model, F, c, 98.0, 18.1 )
    for c0, c1 in ( ( L / 2 - 250.0, L / 2 - 60.0 ), ( L / 2 + 20.0, L / 2 + 230.0 ) ):
        F.box( model, -34, 34, -c0, -c1, 18.0, 38.0, "rw_bogie", skip=( "top", ) )
    for k in range( 6 ):
        c = L / 2 - 375.0 + k * 150.0
        F.box( model, -6, 6, -c, -( c + 12.0 ), COACH_ROOF - 1.0, COACH_ROOF + 3.5, "rw_train_grey",
               skip=( "bottom", ) )
    _buffer_end( model, F, 0.0, 1, beam_half=50.0, beam_paint="rw_bogie" )
    _buffer_end( model, F, L, -1, beam_half=50.0, beam_paint="rw_bogie" )
    F.collide( model, -W, W, -26.0, -( L - 26.0 ), -7.0, COACH_ROOF, "metal" )
    _end_collision( model, F, L, 26.0 )
    return _far( n_front, facing, L )


def coach( model, e, n_front, facing, rail_z=-30.0, body="rw_train_white" ):
    """ A UIC-Z coach: the body in body with a dark window band and a grey roof, rubber gangways at both ends, a door
    near each end of each side, buffers and screw couplings. Metal collision. Returns the far buffers' n. """
    return _coach( model, e, n_front, facing, rail_z, body, cab=False )


def control_car( model, e, n_front, facing, rail_z=-30.0, body="rw_train_white" ):
    """ A driving trailer: the coach with a cab at its front end (a wraparound windscreen, head and tail lights) and a
    gangway at the other; buffers at both. Metal collision. Returns the far buffers' n. """
    return _coach( model, e, n_front, facing, rail_z, body, cab=True )


# ---------------------------------------------------------------------------------------------------------------------
# Freight wagons and containers

FLAT_LENGTH = 777.0          # Sgns: 19.74 m over the buffers, the deck 1155 mm over the rail, bogies 14.2 m apart
FLAT_DECK = 45.5
OPEN_LENGTH = 553.0          # Eaos: 14.04 m over the buffers, the floor 1.25 m up, 2 m walls, bogies 9 m apart
COVERED_LENGTH = 620.0       # Gbs: 15.75 m over the buffers, two axles 8 m apart
CONTAINER_SIZES = { "20": 238.5, "40": 480.0 }     # ISO 1C and 1AA: 6058 and 12192 mm long


def _y25( model, F, c ):
    """ A Y25 freight bogie (1.8 m wheelbase, 920 mm wheels) centred at depth c. """
    _bogie( model, F, c, 71.0, 18.1 )


def container_flat( model, e, n_front, facing, rail_z=-30.0, containers=( "40", "20" ), paint="rw_wagon_grey" ):
    """ A container flat (Sgns): a skeletal frame with fish-belly sole bars on Y25 bogies, container spigots, buffers
    and screw couplings. containers, front first, each "20", "40" or a dict of container()'s arguments ( size,
    paint, doors_open, high_cube, door_end ), are laid end to end 3 apart, centred on the deck. Metal collision up to
    the deck; each container has its own. Returns the far buffers' n. """
    F = vehicle_frame( e, n_front, facing, rail_z )
    L, W, deck = FLAT_LENGTH, 55.5, FLAT_DECK
    a0, a1 = 26.0, L - 26.0
    for xs in ( 1.0, -1.0 ):
        F.box( model, xs * 47.0, xs * 53.0, -a0, -a1, 35.0, deck, paint )
        for x, way in ( ( 53.0, xs ), ( 47.0, -xs ) ):                         # the fish belly
            _fpoly( model, F, paint, [ ( xs * x, -150.0, 35.0 ), ( xs * x, -( L - 150.0 ), 35.0 ),
                                       ( xs * x, -( L - 220.0 ), 22.0 ), ( xs * x, -220.0, 22.0 ) ], ( way, 0, 0 ) )
        F.box( model, xs * 47.0, xs * 53.0, -220.0, -( L - 220.0 ), 21.0, 22.0, paint, skip=( "top", ) )
    F.box( model, -6.0, 6.0, -a0, -a1, 31.0, deck - 1.0, paint, skip=( "top", ) )
    for k in range( 9 ):
        c = 60.0 + k * ( L - 120.0 ) / 8
        F.box( model, -47.0, 47.0, -( c - 3.0 ), -( c + 3.0 ), 38.0, deck - 1.0, paint, skip=( "top", ) )
    for c in ( 60.0, L / 2 - 121.0, L / 2 + 121.0, L - 60.0 ):                     # 20 ft and 40 ft spigots
        for xs in ( 1.0, -1.0 ):
            F.box( model, xs * 43.0, xs * 50.0, -( c - 4.0 ), -( c + 4.0 ), deck, deck + 1.2, "rw_steel_dark",
                   skip=( "bottom", ) )
    for c in ( L / 2 - 279.5, L / 2 + 279.5 ):
        _y25( model, F, c )
    _buffer_end( model, F, 0.0, 1, beam_half=W, beam_paint=paint )
    _buffer_end( model, F, L, -1, beam_half=W, beam_paint=paint )
    F.collide( model, -W, W, -a0, -a1, -7.0, deck, "metal" )
    _end_collision( model, F, L, a0 )
    items = [ { "size": item } if isinstance( item, str ) else dict( item ) for item in containers ]
    lengths = [ CONTAINER_SIZES[str( a.get( "size", "20" ) )] for a in items ]
    a = L / 2 - ( sum( lengths ) + 3.0 * max( 0, len( lengths ) - 1 ) ) / 2
    for args, length in zip( items, lengths ):
        p = F.p( 0.0, -( a + length / 2 ), deck + 1.2 )
        container( model, p[0], p[1], p[2], axis="n", **args )
        a += length + 3.0
    return _far( n_front, facing, L )


def open_wagon( model, e, n_front, facing, rail_z=-30.0, paint="rw_wagon_rust" ):
    """ An open high-sided wagon (Eaos): steel walls with outside stanchions round a 12.7 m x 2.75 m well, the floor
    1.25 m over the rail and the walls 2 m above it, on Y25 bogies 9 m apart. Collision hollow, so it can be stood
    in: the floor and the four walls. Returns the far buffers' n. """
    F = vehicle_frame( e, n_front, facing, rail_z )
    L, W, floor, top = OPEN_LENGTH, 57.0, 49.0, 128.0
    a0, a1 = 26.0, L - 26.0
    model.grain_paints.add( "rw_wood" )
    F.box( model, -W, W, -a0, -a1, 38.0, floor, { "default": paint, "top": "rw_wood" } )
    for xs in ( 1.0, -1.0 ):
        F.box( model, xs * ( W - 2.0 ), xs * W, -a0, -a1, floor, top, paint, skip=( "bottom", ) )
        F.collide( model, xs * ( W - 2.0 ), xs * W, -a0, -a1, floor, top, "metal" )
        for k in range( 10 ):
            c = a0 + 4.0 + k * ( a1 - a0 - 8.0 ) / 9
            F.box( model, xs * W, xs * ( W + 2.5 ), -( c - 2.0 ), -( c + 2.0 ), 40.0, top - 3.0, paint,
                   skip=( "bottom", "top" ) )
        F.box( model, xs * ( W - 1.0 ), xs * ( W + 2.5 ), -a0, -a1, top - 3.0, top + 0.5, paint )
        F.box( model, xs * W, xs * ( W + 1.0 ), -a0, -a1, 36.0, 46.0, paint, skip=( "top", ) )
    for a, way in ( ( a0, 1 ), ( a1, -1 ) ):
        F.box( model, -( W - 2.0 ), W - 2.0, -a, -( a + way * 2.0 ), floor, top, paint, skip=( "bottom", ) )
        F.collide( model, -( W - 2.0 ), W - 2.0, -a, -( a + way * 2.0 ), floor, top, "metal" )
        for x in ( -30.0, 0.0, 30.0 ):
            F.box( model, x - 2.0, x + 2.0, -( a - way * 2.0 ), -a, 40.0, top, paint, skip=( "bottom", ) )
    for c in ( L / 2 - 177.0, L / 2 + 177.0 ):
        _y25( model, F, c )
    _buffer_end( model, F, 0.0, 1, beam_half=W, beam_paint=paint )
    _buffer_end( model, F, L, -1, beam_half=W, beam_paint=paint )
    F.collide( model, -W, W, -a0, -a1, -7.0, floor, "metal" )
    _end_collision( model, F, L, a0 )
    return _far( n_front, facing, L )


COVERED_PROFILE = [ ( 55.5, 40.0 ), ( 55.5, 120.0 ), ( 53.0, 132.0 ), ( 46.0, 143.0 ), ( 33.0, 151.5 ),
                    ( 17.0, 155.5 ), ( 0.0, 157.0 ) ]


def covered_wagon( model, e, n_front, facing, rail_z=-30.0, paint="rw_wagon_rust", doors_open=False ):
    """ A two-axle covered wagon (Gbs): a 14.4 m steel body with outside stanchions under a grey arched roof, a two-leaf
    sliding door over a 2.6 m doorway in each side (doors_open slides the leaves apart and shows the dark inside), on
    two 1000 mm wheelsets 8 m apart in leaf-spring hangers. Metal collision (one box: it can't be entered). Returns
    the far buffers' n. """
    F = vehicle_frame( e, n_front, facing, rail_z )
    L, W = COVERED_LENGTH, 55.5
    a0, a1 = 26.0, L - 26.0
    mid = L / 2
    door = ( mid - 51.0, mid + 51.0 )
    for xs in ( 1.0, -1.0 ):
        _banded_side( model, F, xs, W, a0, a1, [ ( 40.0, 120.0, paint ) ],
                      [ ( door[0], door[1], 44.0, 120.0 ) ] if doors_open else [] )
    _extrude( model, F, COVERED_PROFILE[1:], a0, a1, lambda k: "rw_wagon_grey", smooth_from=0 )
    for a, way in ( ( a0, 1 ), ( a1, -1 ) ):
        _section( model, F, COVERED_PROFILE, a, way, paint )
        for x in ( -28.0, 0.0, 28.0 ):
            F.box( model, x - 1.5, x + 1.5, -( a - way * 2.0 ), -a, 40.0, 124.0, paint, skip=( "bottom", ) )
    _fpoly( model, F, "rw_bogie", [ ( W, -a0, 40.0 ), ( -W, -a0, 40.0 ), ( -W, -a1, 40.0 ), ( W, -a1, 40.0 ) ],
            ( 0, 0, -1 ) )
    for xs in ( 1.0, -1.0 ):
        x = xs * W
        F.box( model, xs * ( W - 4.0 ), xs * ( W + 0.5 ), -a0, -a1, 32.0, 41.0, "rw_wagon_grey", skip=( "top", ) )
        for k in range( 13 ):
            c = a0 + 4.0 + k * ( a1 - a0 - 8.0 ) / 12
            if abs( c - mid ) < 60.0:
                continue
            F.box( model, x, xs * ( W + 1.8 ), -( c - 1.6 ), -( c + 1.6 ), 41.0, 120.0, paint,
                   skip=( "bottom", "top" ) )
        for z in ( 43.0, 123.0 ):                                                  # the door's runners
            F.box( model, x, xs * ( W + 2.5 ), -( mid - 158.0 ), -( mid + 158.0 ), z - 1.0, z + 1.0, "rw_steel_dark" )
        if doors_open:
            leaves = [ ( mid - 102.0, mid - 51.0 ), ( mid + 51.0, mid + 102.0 ) ]
            for a, into in ( ( door[0], -1 ), ( door[1], 1 ) ):                    # the dark inside
                _fpoly( model, F, "rw_black", [ ( x, -a, 44.0 ), ( 0.0, -a, 44.0 ), ( 0.0, -a, 120.0 ),
                                                ( x, -a, 120.0 ) ], ( 0, into, 0 ) )
            for z, up in ( ( 120.0, -1 ), ( 44.0, 1 ) ):
                _fpoly( model, F, "rw_black", [ ( 0.0, -door[0], z ), ( x, -door[0], z ), ( x, -door[1], z ),
                                                ( 0.0, -door[1], z ) ], ( 0, 0, up ) )
            _fpoly( model, F, "rw_black", [ ( 0.0, -door[0], 44.0 ), ( 0.0, -door[1], 44.0 ),
                                            ( 0.0, -door[1], 120.0 ), ( 0.0, -door[0], 120.0 ) ], ( xs, 0, 0 ) )
        else:
            leaves = [ ( mid - 51.0, mid ), ( mid, mid + 51.0 ) ]
        for p0, p1 in leaves:
            F.box( model, xs * ( W + 2.5 ), xs * ( W + 4.0 ), -p0, -p1, 44.0, 122.0, paint )
            for q in ( p0 + 3.0, p1 - 3.0, ( p0 + p1 ) / 2 ):
                F.box( model, xs * ( W + 4.0 ), xs * ( W + 4.8 ), -( q - 1.2 ), -( q + 1.2 ), 44.0, 122.0, paint,
                       skip=( "bottom", "top" ) )
    for c in ( mid - 157.5, mid + 157.5 ):
        _wheelset( model, F, c, 19.7 )
        for xs in ( 1.0, -1.0 ):
            F.box( model, xs * 33.0, xs * 40.0, -( c - 7.0 ), -( c + 7.0 ), 13.0, 27.0, "rw_bogie" )
            F.box( model, xs * 34.0, xs * 39.0, -( c - 30.0 ), -( c + 30.0 ), 27.0, 31.0, "rw_bogie" )
            for k in ( -1, 1 ):
                F.box( model, xs * 34.5, xs * 38.5, -( c + k * 30.0 - 2.0 ), -( c + k * 30.0 + 2.0 ), 31.0, 40.0,
                       "rw_bogie", skip=( "top", ) )
    _buffer_end( model, F, 0.0, 1, beam_half=W, beam_paint="rw_wagon_grey" )
    _buffer_end( model, F, L, -1, beam_half=W, beam_paint="rw_wagon_grey" )
    F.collide( model, -( W + 4.8 ), W + 4.8, -a0, -a1, -7.0, 157.0, "metal" )
    _end_collision( model, F, L, a0 )
    return _far( n_front, facing, L )


def container( model, e, n, z0, size="20", axis="n", paint="rw_container_blue", doors_open=False, high_cube=False,
               door_end=+1 ):
    """ An ISO freight container, its floor's centre at ( e, n, z0 ) and its length along axis ("n" or "e"): 20 or
    40 ft long, 8 ft wide, 8 ft 6 in tall (9 ft 6 in if high_cube). Corrugated walls (the paint's) between the corner
    posts and rails, cast corner fittings, and the doors at the +axis end (-axis if door_end is -1) with their four
    locking bars; doors_open swings the leaves right round against the sides and shows the inside. Metal collision:
    one box, or with the doors open the floor, walls and roof. """
    length = CONTAINER_SIZES[str( size )]
    hl, hw, height = length / 2, 48.0, 114.0 if high_cube else 102.0
    F = Frame( ( e, n, z0 ), ( door_end, 0 ) if axis == "e" else ( 0, door_end ) )
    post, rail_h = 6.0, 6.0
    out_x = { 1.0: "right", -1.0: "left" }
    for xs in ( 1.0, -1.0 ):                                                     # the side walls, set in 0.75
        F.box( model, xs * ( hw - 0.75 ), xs * ( hw - 2.0 ), hl - post, -( hl - post ), rail_h, height - rail_h,
               { "default": None, out_x[xs]: paint, out_x[-xs]: paint if doors_open else None } )
    F.box( model, -( hw - post ), hw - post, -( hl - 0.75 ), -( hl - 2.0 ), rail_h, height - rail_h,
           { "default": None, "back": paint, "front": paint if doors_open else None } )
    F.box( model, -hw, hw, -hl, hl, height - 1.5, height, { "default": None, "top": paint,
                                                              "bottom": paint if doors_open else None } )
    for xs in ( 1.0, -1.0 ):                                                     # the frame
        for ys in ( 1.0, -1.0 ):
            F.box( model, xs * hw, xs * ( hw - post ), ys * hl, ys * ( hl - post ), 4.6, height - 4.6, paint,
                   skip=( "bottom", "top" ) )
            for c0, c1 in ( ( -0.05, 4.6 ), ( height - 4.6, height + 0.05 ) ):
                F.box( model, xs * ( hw + 0.05 ), xs * ( hw - 7.0 ), ys * ( hl + 0.05 ), ys * ( hl - 6.4 ), c0, c1,
                       "rw_steel_dark" )
        F.box( model, xs * hw, xs * ( hw - 3.0 ), hl - post, -( hl - post ), 0.0, rail_h, paint )
        F.box( model, xs * hw, xs * ( hw - 3.0 ), hl - post, -( hl - post ), height - rail_h, height, paint,
               skip=( "top", ) )
    for ys in ( 1.0, -1.0 ):
        F.box( model, -( hw - post ), hw - post, ys * hl, ys * ( hl - 3.0 ), 0.0, rail_h, paint )
        F.box( model, -( hw - post ), hw - post, ys * hl, ys * ( hl - 3.0 ), height - 8.0, height, paint,
               skip=( "top", ) )
    F.box( model, -( hw - 3.0 ), hw - 3.0, -( hl - 3.0 ), hl - 3.0, 0.0, 5.0,
           { "default": None, "bottom": "rw_steel_dark", "top": "rw_wood" if doors_open else None } )
    if doors_open:
        model.grain_paints.add( "rw_wood" )
        for xs in ( 1.0, -1.0 ):                                         # the leaves, swung back against the sides
            F.box( model, xs * ( hw + 0.2 ), xs * ( hw + 1.6 ), hl - 1.0, hl - 1.0 - ( hw - 1.0 ), rail_h,
                   height - 6.0, paint )
            F.collide( model, xs * ( hw + 0.2 ), xs * ( hw + 1.6 ), hl - 1.0, hl - 1.0 - ( hw - 1.0 ), rail_h,
                       height - 6.0, "metal" )
            for x in ( 12.0, 36.0 ):
                xb = xs * ( hw + 2.6 )
                rod( model, F.p( xb, hl - 1.0 - x, rail_h + 2.0 ), F.p( xb, hl - 1.0 - x, height - 8.0 ), 0.95,
                     "rw_steel_grey", 4 )
        F.collide( model, -hw, hw, -hl, hl, 0.0, 5.0, "metal" )
        F.collide( model, -hw, hw, -hl, hl, height - 2.0, height, "metal" )
        for xs in ( 1.0, -1.0 ):
            F.collide( model, xs * hw, xs * ( hw - 2.0 ), -hl, hl, 5.0, height - 2.0, "metal" )
        F.collide( model, -hw, hw, -hl, -( hl - 2.0 ), 5.0, height - 2.0, "metal" )
        return
    F.box( model, -( hw - post ), hw - post, hl - 0.9, hl - 0.2, rail_h, height - 8.0,
           { "default": None, "front": paint } )
    F.quad( model, "rw_black", 0.0, hl - 0.15, height / 2 - 1.0, 0.6, height - 14.0 )
    for x in ( -36.0, -12.0, 12.0, 36.0 ):
        rod( model, F.p( x, hl + 1.2, 3.0 ), F.p( x, hl + 1.2, height - 3.0 ), 0.95, "rw_steel_grey", 4 )
        for z in ( 4.0, height - 4.0 ):
            F.box( model, x - 1.6, x + 1.6, hl - 0.2, hl + 2.4, z - 1.5, z + 1.5, "rw_steel_grey", skip=( "back", ) )
        F.box( model, x, x + ( 7.0 if x > 0 else -7.0 ), hl + 1.0, hl + 2.4, 44.0, 46.0, "rw_steel_grey",
               skip=( "back", ) )
    F.quad( model, "rw_white_paint", 22.0, hl - 0.1, height - 26.0, 8.0, 4.0 )
    F.collide( model, -hw, hw, -hl, hl, 0.0, height, "metal" )


# ---------------------------------------------------------------------------------------------------------------------
# Platform furniture. Each stands on the floor at z0 with its footprint's centre at ( e, n ), its front facing "+e",
# "-e", "+n" or "-n"; hanging things take the height they hang from (z_top) and which way their faces look (along).

DARK = "rw_steel_dark"
HEADROOM = 96.0                 # the lowest a hanging thing's bottom may come over the platform (2.44 m)


def _world( F, v ):
    return v[0] * F.x + v[1] * F.y + v[2] * F.z


def _obox( model, F, centre, xdir, ydir, size, paint, surface=None ):
    """ A box in a frame's coordinates, its own axes along the local directions xdir and ydir (and their cross), size
    along each. """
    a = _unit( _world( F, xdir ) )
    b = _world( F, ydir )
    b = _unit( b - a * np.dot( a, b ) )
    model.oriented_box( F.p( *centre ), ( a, b, np.cross( a, b ) ), size, paint, surface )


def _fbeam( model, F, p0, p1, size, paint ):
    """ A square bar between two points in a frame's coordinates, size ( across, the third way ). """
    model.beam( F.p( *p0 ), F.p( *p1 ), size, paint )


def _frect( model, F, paint, x0, x1, y, z0, z1, toward=1.0, uv=None ):
    """ A rectangle across the frame at depth y, facing local y toward (+1 front, -1 back). """
    _fpoly( model, F, paint, [ ( x0, y, z0 ), ( x1, y, z0 ), ( x1, y, z1 ), ( x0, y, z1 ) ], ( 0, toward, 0 ), uv=uv )


def _xrect( model, F, paint, x, y0, y1, z0, z1, toward=1.0 ):
    """ A rectangle along the frame at x, facing local x toward. """
    _fpoly( model, F, paint, [ ( x, y0, z0 ), ( x, y1, z0 ), ( x, y1, z1 ), ( x, y0, z1 ) ], ( toward, 0, 0 ) )


def _frustum( model, a, b, r0, r1, paint, sides=12, inside=None ):
    """ A round taper from radius r0 at a to r1 at b, shaded smooth, open at both ends; inside paints its inner face
    too (a lamp shade). """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    axis = _unit( b - a )
    length = np.linalg.norm( b - a )
    u, v = _ring_axes( b - a )
    dirs = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v
             for k in range( sides ) ]
    slope = ( r0 - r1 ) / length
    for k in range( sides ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % sides]
        n0, n1 = _unit( d0 + slope * axis ), _unit( d1 + slope * axis )
        pts = [ a + r0 * d0, a + r0 * d1, b + r1 * d1, b + r1 * d0 ]
        outward( model, paint, pts, n0 + n1, normals=[ n0, n1, n1, n0 ] )
        if inside:
            outward( model, inside, pts, -( n0 + n1 ), normals=[ -n0, -n1, -n1, -n0 ] )


def _side_prism( model, F, prof, x0, x1, paint_of, side_paint ):
    """ A prism across the frame from x0 to x1 over a convex side profile ( y, z ): paint_of( k ) paints the face
    from point k to k + 1 (None leaves it out), side_paint its two ends. """
    area = sum( p[0] * q[1] - q[0] * p[1] for p, q in zip( prof, prof[1:] + prof[:1] ) )
    s = 1.0 if area > 0 else -1.0
    for k, ( p, q ) in enumerate( zip( prof, prof[1:] + prof[:1] ) ):
        paint = paint_of( k )
        if paint is None:
            continue
        dy, dz = q[0] - p[0], q[1] - p[1]
        _fpoly( model, F, paint, [ ( x0, p[0], p[1] ), ( x1, p[0], p[1] ), ( x1, q[0], q[1] ), ( x0, q[0], q[1] ) ],
                ( 0, s * dz, -s * dy ) )
    if side_paint:
        for x, t in ( ( x0, -1.0 ), ( x1, 1.0 ) ):
            _fpoly( model, F, side_paint, [ ( x, y, z ) for y, z in prof ], ( t, 0, 0 ) )


def _along_frame( e, n, along ):
    """ A frame whose front looks along +n (along="n") or +e, for things seen from both ways along it. """
    return Frame( ( e, n, 0.0 ), ( 0, 1 ) if along == "n" else ( 1, 0 ) )


def _hang( z_top, height, floor_z, drop ):
    """ The bottom of a thing height tall hung drop under z_top, raised to keep HEADROOM over the floor. """
    bottom = max( z_top - drop - height, floor_z + HEADROOM )
    if bottom + height > z_top - 1.0:
        raise ValueError( f"{z_top - floor_z:.0f} under z_top is too little to hang {height:.0f} with "
                          f"{HEADROOM:.0f} of headroom" )
    return bottom


def _rods( model, F, xs, z0, z1, plate=2.4 ):
    """ Hanging rods ( 12 mm ) at local x in xs from z0 up to z1, each with its ceiling plate. """
    for x in xs:
        rod( model, F.p( x, 0.0, z0 ), F.p( x, 0.0, z1 - 0.4 ), 0.45, DARK, 6 )
        F.box( model, x - plate, x + plate, -plate, plate, z1 - 0.4, z1, DARK, skip=( "top", ) )


BENCH_SEAT = 17.7           # 450 mm


def bench( model, e, n, z0=0.0, facing="+e", length=78.7, slats="rw_wood", frame=DARK ):
    """ A platform bench (2 m by default): four varnished hardwood seat slats 450 mm up and three in a backrest leaning
    back 14 degrees, on anthracite steel frames of 40 mm square tube at each end (and the middle of a long one). The
    footprint is 560 mm deep. Wooden collision: the seat down to the floor, and the backrest. """
    F = frame_for( e, n, z0, facing )
    model.grain_paints.add( slats )
    c, hl = 2.55, length / 2                                    # c centres the footprint (the backrest leans out)
    width = ( 16.5 - 3 * 0.5 ) / 4
    for k in range( 4 ):
        y0 = -8.0 + c + k * ( width + 0.5 )
        F.box( model, -hl, hl, y0, y0 + width, BENCH_SEAT - 1.3, BENCH_SEAT, slats )
    t = math.radians( 14.0 )
    up, nrm = np.array( ( 0.0, -math.sin( t ), math.cos( t ) ) ), np.array( ( 0.0, math.cos( t ), math.sin( t ) ) )
    base = np.array( ( 0.0, -8.6 + c, 19.0 ) )
    for k in range( 3 ):
        centre = base + up * ( 1.75 + k * 4.05 ) - nrm * 0.6
        _obox( model, F, centre, ( 1, 0, 0 ), nrm, ( length, 1.2, 3.5 ), slats )
    posts = [ -hl + 7.0, hl - 7.0 ] + ( [ 0.0 ] if length > 70.0 else [] )
    back0, back1 = base - nrm * 2.0 - up * 3.0, base - nrm * 2.0 + up * 11.0
    for x in posts:
        _fbeam( model, F, ( x, 6.8 + c, 0.0 ), ( x, 6.8 + c, BENCH_SEAT - 1.3 ), ( 1.6, 1.6 ), frame )
        _fbeam( model, F, ( x, back0[1] + 0.4, BENCH_SEAT - 2.1 ), ( x, 8.4 + c, BENCH_SEAT - 2.1 ), ( 1.4, 1.6 ),
                frame )
        _fbeam( model, F, ( x, -8.4 + c, 0.0 ), ( x, back0[1], back0[2] ), ( 1.6, 1.6 ), frame )
        _fbeam( model, F, ( x, back0[1], back0[2] ), ( x, back1[1], back1[2] ), ( 1.6, 1.6 ), frame )
    F.collide( model, -hl, hl, -9.4 + c, 8.5 + c, 0.0, BENCH_SEAT, "wood" )
    F.collide( model, -hl, hl, back1[1] - 0.8, -9.4 + c, 0.0, back1[2] + 1.0, "wood" )


def bin( model, e, n, z0=0.0, facing="+e" ):
    """ A platform litter bin: a two-compartment steel bin (600 x 300 x 1000 mm) on a plinth, a slot in each half of
    its front under a sloping rain hood, a pictogram plate under each. One metal box. """
    F = frame_for( e, n, z0, facing )
    w, d = 11.8, 5.9
    F.box( model, -w + 0.8, w - 0.8, -d + 0.8, d - 0.8, 0.0, 2.0, DARK, skip=( "bottom", ) )
    F.box( model, -w, w, -d, d, 2.0, 35.0, "rw_steel_grey", skip=( "bottom", "top" ) )
    _side_prism( model, F, [ ( -d - 0.4, 35.0 ), ( d + 0.9, 35.0 ), ( d + 0.9, 36.4 ), ( -d - 0.4, 39.4 ) ],
                 -w - 0.4, w + 0.4, lambda k: DARK, DARK )
    for x in ( -5.7, 5.7 ):
        F.quad( model, "rw_black", x, d + 0.02, 31.4, 8.6, 3.0 )
        F.box( model, x - 4.6, x + 4.6, d, d + 0.6, 29.3, 29.9, DARK, skip=( "back", ) )
        F.quad( model, "rw_white_paint", x, d + 0.02, 24.5, 3.2, 3.2 )
    F.quad( model, DARK, 0.0, d + 0.02, 18.5, 0.6, 33.0 )
    F.collide( model, -w - 0.4, w + 0.4, -d - 0.4, d + 0.9, 0.0, 39.4, "metal" )


def ticket_machine( model, e, n, z0=0.0, facing="+e" ):
    """ A ticket machine (850 x 500 x 1800 mm): light grey cabinet, the touch screen (rw_displays ticket_screen) on a
    panel sloping back under the anthracite head with its backlit "Fahrkarten" sign, the card reader, note and coin
    slots and keypad below, and the ticket tray at knee height. One metal box. """
    F = frame_for( e, n, z0, facing )
    w = 16.7
    F.box( model, -w + 1.0, w - 1.0, -10.0, 7.0, 0.0, 3.0, DARK, skip=( "bottom", ) )
    prof = [ ( -11.0, 3.0 ), ( 8.0, 3.0 ), ( 8.0, 38.0 ), ( 4.0, 57.0 ), ( -11.0, 57.0 ) ]
    _side_prism( model, F, prof, -w, w, lambda k: { 1: "rw_steel_grey", 2: DARK, 4: "rw_steel_grey" }.get( k ),
                 "rw_steel_grey" )
    F.box( model, -w, w, -11.0, 7.5, 57.0, 71.0, DARK )
    F.atlas( model, "rw_signs", "fahrkarten", 0.0, 7.55, 64.0, 28.0, 7.0 )
    slope = _unit( _world( F, ( 0.0, -4.0, 19.0 ) ) )
    out = _unit( _world( F, ( 0.0, 19.0, 4.0 ) ) )
    atlas_quad( model, "rw_displays", "ticket_screen", F.p( 0.0, 6.0, 47.8 ) + out * 0.05, F.x, slope, 15.0, 11.25 )
    F.box( model, -12.5, -7.0, 8.0, 9.4, 33.0, 36.0, "rw_black", skip=( "back", ) )        # card reader
    F.quad( model, "rw_black", 9.5, 8.02, 33.5, 7.0, 5.0 )                                  # keypad
    F.box( model, 6.5, 10.5, 8.0, 8.8, 26.5, 29.0, DARK, skip=( "back", ) )                 # coins
    F.box( model, -13.0, -6.0, 8.0, 8.6, 26.5, 28.5, DARK, skip=( "back", ) )               # notes
    F.quad( model, "rw_black", 0.0, 8.02, 14.0, 18.0, 7.0 )                                 # the ticket tray
    F.box( model, -9.5, 9.5, 8.0, 9.6, 9.6, 10.6, DARK, skip=( "back", ) )
    F.collide( model, -w, w, -11.0, 8.5, 0.0, 71.0, "metal" )


VENDING_GOODS = ( "rw_red_paint", "rw_yellow_paint", "rw_train_blue", "rw_white_paint", "rw_container_green",
                  "rw_container_orange", "rw_train_red" )


def vending_machine( model, e, n, z0=0.0, facing="+e" ):
    """ A snack machine (900 x 850 x 1830 mm): a black cabinet with a red header band, its lit window showing five
    shelves of packets behind the glass, the keypad panel beside it and the pick-up flap below. One metal box. """
    F = frame_for( e, n, z0, facing )
    w, d0, d1, h = 17.7, -16.0, 17.5, 72.0
    gx0, gx1, gz0, gz1 = -15.7, 5.5, 24.0, 68.0
    F.box( model, -w + 1.0, w - 1.0, d0 + 1.0, d1 - 1.5, 0.0, 3.0, DARK, skip=( "bottom", ) )
    F.box( model, -w, w, d0, d1, 3.0, h, { "default": "rw_black", "front": None }, skip=( "bottom", ) )
    for x0, x1, z0_, z1_, paint in ( ( -w, gx0, 3.0, h, "rw_black" ), ( gx1, w, 3.0, h, "rw_black" ),
                                     ( gx0, gx1, 3.0, gz0, "rw_black" ), ( gx0, gx1, gz1, h, "rw_red_paint" ) ):
        _frect( model, F, paint, x0, x1, d1, z0_, z1_ )
    _frect( model, F, "rw_white_paint", gx0, gx1, d1 - 10.0, gz0, gz1 )                   # the lit cavity
    _xrect( model, F, "rw_steel_grey", gx0, d1 - 10.0, d1, gz0, gz1, 1.0 )
    _xrect( model, F, "rw_steel_grey", gx1, d1 - 10.0, d1, gz0, gz1, -1.0 )
    _fpoly( model, F, "rw_lamp_cool", [ ( gx0, d1 - 10.0, gz1 ), ( gx1, d1 - 10.0, gz1 ), ( gx1, d1, gz1 ),
                                        ( gx0, d1, gz1 ) ], ( 0, 0, -1 ) )
    k = 0
    for row in range( 5 ):
        zs = gz0 + 1.0 + row * 8.6
        _fpoly( model, F, "rw_steel_grey", [ ( gx0, d1 - 10.0, zs ), ( gx1, d1 - 10.0, zs ), ( gx1, d1 - 1.5, zs ),
                                             ( gx0, d1 - 1.5, zs ) ], ( 0, 0, 1 ) )
        _frect( model, F, "rw_steel_grey", gx0, gx1, d1 - 1.5, zs - 1.0, zs )
        for col in range( 4 ):
            x0 = gx0 + 0.6 + col * 5.15
            paint = VENDING_GOODS[( k * 3 ) % len( VENDING_GOODS )]
            k += 1
            _frect( model, F, paint, x0, x0 + 4.4, d1 - 3.0, zs, zs + 5.6 )
            _fpoly( model, F, paint, [ ( x0, d1 - 9.0, zs + 5.6 ), ( x0 + 4.4, d1 - 9.0, zs + 5.6 ),
                                       ( x0 + 4.4, d1 - 3.0, zs + 5.6 ), ( x0, d1 - 3.0, zs + 5.6 ) ], ( 0, 0, 1 ) )
    _frect( model, F, "rw_glass", gx0, gx1, d1 - 0.6, gz0, gz1 )
    F.box( model, 7.0, w - 2.0, d1, d1 + 0.6, 30.0, 60.0, "rw_steel_grey", skip=( "back", ) )
    F.quad( model, "rw_black", 12.35, d1 + 0.62, 55.5, 7.0, 3.0 )
    F.quad( model, DARK, 12.35, d1 + 0.62, 45.0, 5.5, 7.5 )
    F.box( model, 10.5, 14.0, d1 + 0.6, d1 + 1.2, 36.0, 38.5, DARK, skip=( "back", ) )
    F.quad( model, DARK, gx0 + 10.6, d1 + 0.02, 15.0, 18.0, 8.0 )                          # the pick-up flap
    F.box( model, gx0 + 3.0, gx1 - 3.0, d1, d1 + 0.8, 19.0, 19.8, "rw_steel_grey", skip=( "back", ) )
    F.collide( model, -w, w, d0, d1 + 1.2, 0.0, h, "metal" )


def timetable_case( model, e, n, z0=0.0, facing="+e", two_sided=False ):
    """ A timetable case on two posts: the yellow departures and white arrivals timetables (A1, 594 x 841 mm) side by
    side behind glass, their bottom edges 900 mm up; two_sided shows them on the back too. One metal box. """
    F = frame_for( e, n, z0, facing )
    pw, ph, gap, border = 23.4, 33.1, 1.6, 1.6
    hw, d = pw + gap / 2 + border, 1.4
    zb = 33.8
    zt = zb + ph + 2 * border
    zc = zb + border + ph / 2
    F.box( model, -hw, hw, -d, d, zb, zt, DARK )
    sides = [ ( 1.0, "front" ) ] + ( [ ( -1.0, "back" ) ] if two_sided else [] )
    for s, face in sides:
        F.atlas( model, "rw_posters", "timetable_dep", -s * ( pw + gap ) / 2, s * ( d + 0.03 ), zc, pw, ph, face )
        F.atlas( model, "rw_posters", "timetable_arr", s * ( pw + gap ) / 2, s * ( d + 0.03 ), zc, pw, ph, face )
        _frect( model, F, "rw_glass", -hw + border, hw - border, s * ( d + 0.5 ), zb + border, zt - border, s )
        y0, y1 = sorted( ( s * d, s * ( d + 0.6 ) ) )
        for x0, x1, z0_, z1_ in ( ( -hw, hw, zb, zb + border ), ( -hw, hw, zt - border, zt ),
                                  ( -hw, -hw + border, zb + border, zt - border ),
                                  ( hw - border, hw, zb + border, zt - border ) ):
            F.box( model, x0, x1, y0, y1, z0_, z1_, DARK, skip=( "back", ) if s > 0 else ( "front", ) )
    for x in ( -hw - 1.2, hw + 1.2 ):
        F.box( model, x - 1.2, x + 1.2, -1.2, 1.2, 0.0, zt + 1.5, DARK, skip=( "bottom", "top" ) )
    F.box( model, -hw - 2.6, hw + 2.6, -2.2, 2.2, zt + 1.5, zt + 2.3, DARK )
    F.collide( model, -hw - 2.6, hw + 2.6, -2.2, 2.2, 0.0, zt + 2.3, "metal" )


def info_pillar( model, e, n, z0=0.0, facing="+e" ):
    """ A help point column (2.55 m): an anthracite post 350 x 250 mm under a backlit head with the "i" sign on every
    side, and the intercom at 1.2-1.5 m on its front: the blue information and red emergency buttons, the speaker
    grille. One metal box. """
    F = frame_for( e, n, z0, facing )
    F.box( model, -6.9, 6.9, -4.9, 4.9, 0.0, 84.0, DARK, skip=( "bottom", "top" ) )
    F.box( model, -8.3, 8.3, -5.9, 5.9, 84.0, 100.4, DARK )
    F.atlas( model, "rw_signs", "info", 0.0, 5.93, 92.2, 14.0, 14.0, "front" )
    F.atlas( model, "rw_signs", "info", 0.0, -5.93, 92.2, 14.0, 14.0, "back" )
    F.atlas( model, "rw_signs", "info", 8.33, 0.0, 92.2, 10.0, 10.0, "right" )
    F.atlas( model, "rw_signs", "info", -8.33, 0.0, 92.2, 10.0, 10.0, "left" )
    F.box( model, -5.0, 5.0, 4.9, 5.4, 44.0, 60.0, "rw_steel_grey", skip=( "back", ) )
    F.quad( model, "rw_black", 0.0, 5.42, 56.5, 6.0, 3.0 )
    for x, paint in ( ( -2.2, "rw_train_blue" ), ( 2.2, "rw_red_paint" ) ):
        disc( model, paint, F.p( x, 5.45, 50.0 ), F.y, 1.3, sides=10 )
        F.quad( model, "rw_white_paint", x, 5.42, 47.4, 3.0, 0.8 )
    F.collide( model, -8.3, 8.3, -5.9, 5.9, 0.0, 100.4, "metal" )


SHELTER_HEIGHT = 98.4           # 2.5 m to the roof's top


def shelter( model, e0, e1, n0, n1, z0=0.0, facing=None, poster=None ):
    """ A glass waiting shelter 2.5 m tall whose roof covers e0..e1, n0..n1: 60 mm steel posts at most 1.3 m apart,
    10 mm toughened glass in the back and both ends with the two contrast bands DIN 18040 asks for (at 0.55 and
    1.4 m), a flat steel roof reaching 200 mm past the open front, and a bench along the back. facing: the open
    front's way, across the shelter's length (default +e, or +n if it's long along e). poster: a rw_posters name lit
    in a case at the far end (the +x end seen from the front) in place of that end's glass. Collision: glass panes,
    metal posts and roof (the bench its own). """
    long_n = abs( n1 - n0 ) >= abs( e1 - e0 )
    facing = facing or ( "+e" if long_n else "+n" )
    F = frame_for( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z0, facing )
    along_e = abs( F.x[0] ) > 0.5
    hx = abs( e1 - e0 ) / 2 if along_e else abs( n1 - n0 ) / 2
    hy = abs( n1 - n0 ) / 2 if along_e else abs( e1 - e0 ) / 2
    H = SHELTER_HEIGHT
    yb, yf = -hy + 1.2, hy - 9.2
    count = max( 1, math.ceil( ( 2 * hx - 2.4 ) / 51.0 ) )
    xs = list( np.linspace( -hx + 1.2, hx - 1.2, count + 1 ) )
    posts = [ ( x, yb ) for x in xs ] + [ ( -hx + 1.2, yf ), ( hx - 1.2, yf ) ]
    for x, y in posts:
        F.box( model, x - 1.2, x + 1.2, y - 1.2, y + 1.2, 0.0, H - 3.5, DARK, skip=( "bottom", "top" ) )
        F.collide( model, x - 1.2, x + 1.2, y - 1.2, y + 1.2, 0.0, H - 3.5, "metal" )
    F.box( model, -hx, hx, -hy, hy, H - 3.5, H, { "default": DARK, "bottom": "rw_steel_grey" } )
    F.collide( model, -hx, hx, -hy, hy, H - 3.5, H, "metal" )
    bands = ( ( 20.0, 23.2 ), ( 53.5, 56.7 ) )

    def pane_x( x0, x1, y ):            # glass across the frame (the back wall)
        for s in ( 1.0, -1.0 ):
            _frect( model, F, "rw_glass", x0, x1, y + s * 0.2, 3.0, H - 5.0, s )
            for b0, b1 in bands:
                _frect( model, F, "rw_white_paint", x0, x1, y + s * 0.23, b0, b1, s )
        F.box( model, x0, x1, y - 0.9, y + 0.9, 0.0, 3.0, DARK, skip=( "bottom", ) )
        F.box( model, x0, x1, y - 0.9, y + 0.9, H - 5.0, H - 3.5, DARK, skip=( "top", ) )

    def pane_y( x, y0, y1 ):            # glass along the frame (an end)
        for s in ( 1.0, -1.0 ):
            _xrect( model, F, "rw_glass", x + s * 0.2, y0, y1, 3.0, H - 5.0, s )
            for b0, b1 in bands:
                _xrect( model, F, "rw_white_paint", x + s * 0.23, y0, y1, b0, b1, s )
        F.box( model, x - 0.9, x + 0.9, y0, y1, 0.0, 3.0, DARK, skip=( "bottom", ) )
        F.box( model, x - 0.9, x + 0.9, y0, y1, H - 5.0, H - 3.5, DARK, skip=( "top", ) )

    for xa, xb in zip( xs, xs[1:] ):
        pane_x( xa + 1.2, xb - 1.2, yb )
    F.collide( model, -hx + 1.2, hx - 1.2, yb - 0.5, yb + 0.5, 0.0, H - 3.5, "glass" )
    for x in ( -hx + 1.2, hx - 1.2 ):
        if poster and x > 0:
            pw = min( 46.7, yf - yb - 6.0 )
            ph = pw / 0.677
            F.box( model, x - 2.2, x + 2.2, yb + 1.2, yf - 1.2, 8.0, min( 8.0 + ph + 4.0, H - 3.5 ), DARK )
            zc = 10.0 + ph / 2
            F.atlas( model, "rw_posters", poster, x + 2.23, ( yb + yf ) / 2, zc, pw, ph, "right" )
            F.atlas( model, "rw_posters", poster, x - 2.23, ( yb + yf ) / 2, zc, pw, ph, "left" )
            F.box( model, x - 0.9, x + 0.9, yb + 1.2, yf - 1.2, 0.0, 8.0, DARK, skip=( "bottom", ) )
            F.collide( model, x - 2.2, x + 2.2, yb, yf, 0.0, H - 3.5, "metal" )
            continue
        pane_y( x, yb + 1.2, yf - 1.2 )
        F.collide( model, x - 0.5, x + 0.5, yb, yf, 0.0, H - 3.5, "glass" )
    length = min( 2 * hx - 16.0, 118.0 )
    if length >= 40.0:
        p = F.p( 0.0, yb + 1.2 + 11.6, 0.0 )
        bench( model, p[0], p[1], z0, facing, length=length )


def kiosk( model, e0, e1, n0, n1, facing, z0=0.0, sign="kiosk" ):
    """ A platform kiosk 2.7 m tall over e0..e1, n0..n1: anthracite steel walls glazed with dark glass above 1 m, the
    serving hatch open in its front over a counter at 1 m, lit shelves of goods behind it and a rack of magazines
    below, the backlit fascia (rw_shopsigns sign, 5:1) above and a flat roof overhanging 150 mm. Metal collision: the
    kiosk, and the counter and rack. """
    F = frame_for( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z0, facing )
    along_e = abs( F.x[0] ) > 0.5
    hx = abs( e1 - e0 ) / 2 if along_e else abs( n1 - n0 ) / 2
    hy = abs( n1 - n0 ) / 2 if along_e else abs( e1 - e0 ) / 2
    wall, top = 86.0, 104.0
    ox = hx - 5.0                                                   # the hatch's half width
    F.box( model, -hx, hx, -hy, hy, 0.0, wall, { "default": DARK, "front": None, "top": None }, skip=( "bottom", ) )
    for x0, x1, z0_, z1_ in ( ( -hx, hx, 0.0, 36.0 ), ( -hx, -ox, 36.0, wall ), ( ox, hx, 36.0, wall ),
                              ( -ox, ox, 84.0, wall ) ):
        _frect( model, F, DARK, x0, x1, hy, z0_, z1_ )
    for s, face in ( ( 1.0, "right" ), ( -1.0, "left" ) ):         # side and back glazing in 1 m bays
        bays = max( 1, round( ( 2 * hy - 8.0 ) / 40.0 ) )
        edges = np.linspace( -hy + 4.0, hy - 4.0, bays + 1 )
        for y0, y1 in zip( edges, edges[1:] ):
            _xrect( model, F, "rw_window_dark", s * ( hx + 0.03 ), y0 + 0.8, y1 - 0.8, 42.0, 80.0, s )
    bays = max( 1, round( ( 2 * hx - 8.0 ) / 40.0 ) )
    edges = np.linspace( -hx + 4.0, hx - 4.0, bays + 1 )
    for x0, x1 in zip( edges, edges[1:] ):
        _frect( model, F, "rw_window_dark", x0 + 0.8, x1 - 0.8, -hy - 0.03, 42.0, 80.0, -1.0 )
    back = hy - 14.0                                                # the hatch's recess
    _frect( model, F, "rw_steel_grey", -ox, ox, back, 39.5, 84.0 )
    _xrect( model, F, DARK, -ox, back, hy, 39.5, 84.0, 1.0 )
    _xrect( model, F, DARK, ox, back, hy, 39.5, 84.0, -1.0 )
    _fpoly( model, F, "rw_lamp_warm", [ ( -ox, back, 84.0 ), ( ox, back, 84.0 ), ( ox, hy, 84.0 ), ( -ox, hy, 84.0 ) ],
            ( 0, 0, -1 ) )
    k = 0
    for z in ( 52.0, 63.0, 74.0 ):
        F.box( model, -ox, ox, back, back + 5.0, z - 1.0, z, "rw_wood", skip=( "back", ) )
        count = max( 2, int( 2 * ox / 7.0 ) )
        for j in range( count ):
            x0 = -ox + 1.0 + j * ( 2 * ox - 2.0 ) / count
            paint = VENDING_GOODS[( k * 5 ) % len( VENDING_GOODS )]
            k += 1
            x1 = x0 + ( 2 * ox - 2.0 ) / count - 1.2
            _frect( model, F, paint, x0, x1, back + 4.0, z, z + 6.5 )
            zt = z + 6.5
            _fpoly( model, F, paint, [ ( x0, back + 0.5, zt ), ( x1, back + 0.5, zt ), ( x1, back + 4.0, zt ),
                                       ( x0, back + 4.0, zt ) ], ( 0, 0, 1 ) )
    F.box( model, -ox, ox, back, hy, 36.0, 39.5, "rw_steel_grey", skip=( "bottom", "back" ) )
    F.box( model, -hx + 3.0, hx - 3.0, hy, hy + 8.0, 36.0, 39.5, "rw_steel_grey", skip=( "back", ) )
    F.box( model, -hx + 8.0, hx - 8.0, hy, hy + 3.0, 6.0, 33.0, "rw_steel_grey", skip=( "back", ) )
    papers = ( "rw_white_paint", "rw_red_paint", "rw_yellow_paint", "rw_train_blue", "rw_white_paint",
               "rw_container_green" )
    count = max( 1, int( ( 2 * hx - 18.0 ) / 8.0 ) )
    for row, z in enumerate( ( 9.0, 21.0 ) ):
        for j in range( count ):
            x = -hx + 9.0 + ( j + 0.5 ) * ( 2 * hx - 18.0 ) / count
            F.quad( model, papers[( j + row * 3 ) % len( papers )], x, hy + 3.03, z + 5.0, 6.6, 9.4 )
    F.box( model, -hx - 1.0, hx + 1.0, -hy - 1.0, hy + 1.0, wall, top, DARK, skip=( "top", ) )
    sh = min( 15.0, ( 2 * hx - 8.0 ) / 5.0 )
    F.atlas( model, "rw_shopsigns", sign, 0.0, hy + 1.03, ( wall + top ) / 2, sh * 5.0, sh, "front" )
    side = min( 15.0, ( 2 * hy - 8.0 ) / 5.0 )
    if side >= 6.0:
        F.atlas( model, "rw_shopsigns", sign, hx + 1.03, 0.0, ( wall + top ) / 2, side * 5.0, side, "right" )
        F.atlas( model, "rw_shopsigns", sign, -hx - 1.03, 0.0, ( wall + top ) / 2, side * 5.0, side, "left" )
    F.box( model, -hx - 6.0, hx + 6.0, -hy - 6.0, hy + 6.0, top, top + 2.0, DARK )
    F.collide( model, -hx - 1.0, hx + 1.0, -hy - 1.0, hy + 1.0, 0.0, top + 2.0, "metal" )
    F.collide( model, -hx + 3.0, hx - 3.0, hy, hy + 8.0, 0.0, 39.5, "metal" )


def hanging_display( model, e, n, z_top, name, along="n", floor_z=0.0, width=118.1 ):
    """ A platform display (rw_displays name, 5:1; 3 m by default) in a 150 mm deep anthracite housing, lit on both
    faces, hung on two rods up to z_top: 450 mm under it, or higher to keep its bottom HEADROOM over floor_z. along:
    the faces look both ways along n or e. No collision. """
    F = _along_frame( e, n, along )
    h = width / aspect( "rw_displays", name )
    hw, hh, d = width / 2 + 1.6, h / 2 + 1.6, 2.95
    bottom = _hang( z_top, 2 * hh, floor_z, 17.7 )
    zc = bottom + hh
    F.box( model, -hw, hw, -d, d, bottom, bottom + 2 * hh, DARK )
    F.atlas( model, "rw_displays", name, 0.0, d + 0.03, zc, width, h, "front" )
    F.atlas( model, "rw_displays", name, 0.0, -d - 0.03, zc, width, h, "back" )
    _rods( model, F, ( -hw + 10.0, hw - 10.0 ), bottom + 2 * hh, z_top )


def hanging_sign( model, e, n, z_top, names, along="n", floor_z=0.0, height=13.8, back_names=None ):
    """ A backlit wayfinding sign (rw_signs) hung from z_top: the names' panels side by side, 350 mm tall, in a
    100 mm deep anthracite light box, read the same from both sides (back_names: different panels on the back, as
    for arrows), its bottom HEADROOM over floor_z at least. along: the faces look along n or e. No collision. """
    F = _along_frame( e, n, along )
    names = [ names ] if isinstance( names, str ) else list( names )
    back = list( back_names ) if back_names else names
    gap, border, d = 0.8, 0.8, 1.95

    def widths( items ):
        return [ height * aspect( "rw_signs", nm ) for nm in items ]

    span = max( sum( widths( names ) ), sum( widths( back ) ) ) + gap * ( max( len( names ), len( back ) ) - 1 )
    hw = span / 2 + border
    bottom = _hang( z_top, height + 2 * border, floor_z, 11.8 )
    zc = bottom + border + height / 2
    F.box( model, -hw, hw, -d, d, bottom, bottom + height + 2 * border, DARK )
    for items, s, face in ( ( names, 1.0, "front" ), ( back, -1.0, "back" ) ):
        ws = widths( items )
        x = -( sum( ws ) + gap * ( len( ws ) - 1 ) ) / 2
        for nm, w in zip( items, ws ):
            F.atlas( model, "rw_signs", nm, s * ( x + w / 2 ), s * ( d + 0.03 ), zc, w, height, face )
            x += w + gap
    _rods( model, F, ( -hw + 6.0, hw - 6.0 ) if hw > 14.0 else ( 0.0, ), bottom + height + 2 * border, z_top )


def clock( model, e, n, z, along="n", z_top=None, radius=12.4 ):
    """ A double-sided platform clock: 630 mm dials (rw_clock, its black bezel drawn in) in a 120 mm deep round
    anthracite housing, hung on a rod up to z_top (default 18 above it). z is the dials' centre; along: the dials
    look both ways along n or e. No collision. """
    F = _along_frame( e, n, along )
    d = 2.36
    rod( model, F.p( 0.0, -d, z ), F.p( 0.0, d, z ), radius, DARK, 24 )
    for s in ( 1.0, -1.0 ):
        disc( model, "rw_clock", F.p( 0.0, s * d, z ), s * F.y, radius, sides=24, round_uv=True )
    top = z + radius
    z_top = top + 18.0 if z_top is None else z_top
    F.box( model, -1.6, 1.6, -1.6, 1.6, top - 0.6, top + 2.0, DARK, skip=( "bottom", ) )
    _rods( model, F, ( 0.0, ), top + 2.0, z_top )


def pendant_lamp( model, e, n, z_top, z ):
    """ A hall pendant: a 560 mm enamelled reflector shade (grey-green outside, white inside) on a rod from z_top, the
    opal globe in its mouth; z is the shade's rim. Returns the light's position, just under the rim. """
    rod( model, ( e, n, z + 12.5 ), ( e, n, z_top - 0.4 ), 0.45, DARK, 6 )
    model.box( ( e - 2.4, n - 2.4, z_top - 0.4 ), ( e + 2.4, n + 2.4, z_top ), DARK, skip=( "+z", ) )
    rod( model, ( e, n, z + 10.5 ), ( e, n, z + 12.5 ), 1.4, DARK, 8, caps=( False, True ) )
    _frustum( model, ( e, n, z + 10.5 ), ( e, n, z ), 2.2, 11.0, "rw_steel", sides=12, inside="rw_white_paint" )
    disc( model, "rw_steel", ( e, n, z + 10.5 ), ( 0, 0, 1 ), 2.2, sides=12 )
    _frustum( model, ( e, n, z + 7.0 ), ( e, n, z + 1.5 ), 3.0, 4.8, "rw_lamp_warm", sides=10 )
    disc( model, "rw_lamp_warm", ( e, n, z + 1.5 ), ( 0, 0, -1 ), 4.8, sides=10 )
    return ( e, n, z - 2.0 )


def lamp_post( model, e, n, height, z0=0.0, along="n" ):
    """ A platform lamp post: a tapered steel mast (140 mm at the foot, 76 mm at the top) on a 180 mm base 350 mm
    tall, carrying a flat LED luminaire (700 x 250 x 100 mm, its length along n or e) whose diffuser faces down at
    height over z0. Metal collision on the mast. Returns the light's position. """
    model.cylinder( ( e, n ), 3.6, z0, z0 + 14.0, { "side": DARK, "top": DARK }, sides=10 )
    _frustum( model, ( e, n, z0 + 14.0 ), ( e, n, z0 + height ), 2.75, 1.5, DARK, sides=10 )
    F = Frame( ( e, n, z0 ), ( 0, 1 ) if along == "n" else ( 1, 0 ) )
    F.box( model, -4.9, 4.9, -13.8, 13.8, height, height + 3.9, { "default": DARK, "bottom": None } )
    _fpoly( model, F, DARK, [ ( -4.9, -13.8, height ), ( 4.9, -13.8, height ), ( 4.9, 13.8, height ),
                              ( -4.9, 13.8, height ) ], ( 0, 0, -1 ) )
    _fpoly( model, F, "rw_lamp_cool", [ ( -3.9, -12.6, height - 0.05 ), ( 3.9, -12.6, height - 0.05 ),
                                        ( 3.9, 12.6, height - 0.05 ), ( -3.9, 12.6, height - 0.05 ) ], ( 0, 0, -1 ) )
    model.collision_box( ( e - 3.6, n - 3.6, z0 ), ( e + 3.6, n + 3.6, z0 + height ), "metal" )
    return ( e, n, z0 + height - 2.0 )


def luggage_cart( model, e, n, along="n", z0=0.0, loaded=True ):
    """ An old platform luggage cart (2.5 x 1.2 m): a plank deck 600 mm up on a grey-green steel frame, four 400 mm
    wheels on solid rubber tyres, the front pair on a turntable with the drawbar lying forward on the ground, tubular
    gates 1 m high at both ends, and (loaded) two crates and three suitcases on it to about 1.15 m. along: "n", "-n",
    "e" or "-e", the way the drawbar points. One wooden box to the gates' height. """
    sign = -1.0 if along.startswith( "-" ) else 1.0
    F = Frame( ( e, n, z0 ), ( 0, sign ) if along.endswith( "n" ) else ( sign, 0 ) )
    hl, hw, deck = 49.2, 23.6, 23.6
    model.grain_paints.add( "rw_wood" )
    F.box( model, -hw, hw, -hl, hl, deck - 1.4, deck, "rw_wood" )
    for xs in ( 1.0, -1.0 ):
        F.box( model, xs * ( hw - 2.0 ), xs * hw, -hl, hl, deck - 5.4, deck - 1.4, "rw_steel", skip=( "top", ) )
    for y in ( -hl + 1.0, 0.0, hl - 1.0 ):
        F.box( model, -hw + 2.0, hw - 2.0, y - 1.0, y + 1.0, deck - 5.4, deck - 1.4, "rw_steel", skip=( "top", ) )
    r = 7.9
    for y in ( -37.0, 33.0 ):
        rod( model, F.p( -16.0, y, r ), F.p( 16.0, y, r ), 0.9, DARK, 4 )
        for xs in ( 1.0, -1.0 ):
            rod( model, F.p( xs * 16.0, y, r ), F.p( xs * 19.1, y, r ), r, "rw_rubber", 8, caps=( True, True ) )
            disc( model, "rw_steel", F.p( xs * 19.15, y, r ), xs * F.x, 4.6, sides=6 )
            F.box( model, xs * 13.0, xs * 15.0, y - 2.0, y + 2.0, r, deck - 5.4, "rw_steel", skip=( "top", ) )
    F.box( model, -14.0, 14.0, 26.0, 40.0, deck - 8.0, deck - 5.4, DARK, skip=( "top", ) )
    rod( model, F.p( 0.0, 38.0, r ), F.p( 0.0, 76.0, 1.5 ), 0.9, "rw_steel", 4 )
    rod( model, F.p( -6.0, 76.0, 1.5 ), F.p( 6.0, 76.0, 1.5 ), 0.9, "rw_steel", 4, caps=( True, True ) )
    for y in ( -hl + 1.0, hl - 1.0 ):
        for xs in ( 1.0, -1.0 ):
            rod( model, F.p( xs * ( hw - 1.0 ), y, deck ), F.p( xs * ( hw - 1.0 ), y, 39.4 ), 0.85, "rw_steel", 4,
                 caps=( False, True ), turn=math.pi / 4 )
        for z in ( 31.5, 39.4 ):
            rod( model, F.p( -hw + 1.0, y, z ), F.p( hw - 1.0, y, z ), 0.85, "rw_steel", 4, turn=math.pi / 4 )
    if loaded:
        F.box( model, -20.0, 2.0, -45.0, -19.0, deck, 40.5, "rw_wood", skip=( "bottom", ) )
        F.box( model, 3.0, 22.7, -46.0, -18.4, deck, deck + 9.8, "rw_steel_grey", skip=( "bottom", ) )
        F.box( model, 5.0, 20.7, -43.0, -21.3, deck + 9.8, deck + 17.7, "rw_red_paint", skip=( "bottom", ) )
        F.box( model, -14.0, 1.7, -10.0, -2.1, deck, deck + 21.7, "rw_train_blue", skip=( "bottom", ) )
        F.box( model, -7.0, 19.0, 4.0, 30.0, deck, deck + 15.7, "rw_wood", skip=( "bottom", ) )
        F.box( model, -19.0, -9.0, 8.0, 36.0, deck, deck + 9.0, "rw_black", skip=( "bottom", ) )
    F.collide( model, -hw, hw, -hl, hl, 0.0, 39.4, "wood" )


# ---------------------------------------------------------------------------------------------------------------------
# Yard and road clutter.

def _line_ends( p0, p1, z0 ):
    """ A run's two ends as ( e, n, z ): each point's own z if it has one, else z0 (default 0). """
    def end( p ):
        z = z0 if z0 is not None else ( p[2] if len( p ) > 2 else 0.0 )
        return np.array( ( p[0], p[1], z ), float )
    return end( p0 ), end( p1 )


class _Run:
    """ A straight run from a to b in plan: t along it, w across it (to its left), z over the ground there. """

    def __init__( self, a, b ):
        self.a = a
        d = ( b - a )[:2]
        self.length = float( np.linalg.norm( d ) )
        self.d = np.array( ( *( d / self.length ), 0.0 ) )
        self.s = np.array( ( -self.d[1], self.d[0], 0.0 ) )
        self.rise = ( b[2] - a[2] ) / self.length
        self.axes = ( self.d, self.s, np.array( ( 0.0, 0.0, 1.0 ) ) )

    def p( self, t, w, z ):
        q = self.a + self.d * t + self.s * w
        q[2] = self.a[2] + self.rise * t + z
        return q

    def quad( self, model, paint, t0, t1, w, z0, z1 ):
        """ A both-sided upright rectangle across t0..t1 at w, z0..z1 over the ground. """
        model.polygon( paint, [ self.p( t0, w, z0 ), self.p( t1, w, z0 ), self.p( t1, w, z1 ), self.p( t0, w, z1 ) ],
                       both_sides=True )

    def bar( self, model, paint, t, w, z0, z1, size, skip_bottom=True ):
        """ An upright bar size ( along, across ) centred on ( t, w ), z0..z1 over the ground. """
        c = self.p( t, w, ( z0 + z1 ) / 2 )
        model.oriented_box( c, self.axes, ( size[0], size[1], z1 - z0 ), { "default": paint,
                                                                           "-z": None if skip_bottom else paint } )

    def collide( self, model, height, thick, surface, z_from=0.0, w=0.0 ):
        low = min( self.a[2], self.a[2] + self.rise * self.length )
        span = abs( self.rise * self.length )
        c = self.p( self.length / 2, w, 0.0 )
        c[2] = low + z_from + ( height - z_from + span ) / 2
        model.oriented_box( c, self.axes, ( self.length, thick, height - z_from + span ), None, surface )


def fence( model, p0, p1, height=79.0, kind="mesh", z0=None, pitch=None, paint=None ):
    """ A security fence from p0 to p1 (( e, n ) or ( e, n, z ) points; z0 sets both ends' ground). kind "mesh": welded
    6/5/6 double-wire panels (2.5 m wide, 5 mm uprights every 50 mm (pitch), pairs of 6 mm wires every 200 mm, the
    uprights' ends standing 30 mm proud) between 60 x 40 mm posts, in anthracite; collision 1 thick, "plastic", so
    rounds pass. kind "palisade": steel W-pales 70 mm wide every 160 mm (pitch) with triple-pointed tops on two angle
    rails, between posts 2.75 m apart, galvanised grey; collision "metal". """
    a, b = _line_ends( p0, p1, z0 )
    run = _Run( a, b )
    L = run.length
    if kind == "mesh":
        paint = paint or DARK
        pitch = pitch or 1.97
        bays = max( 1, math.ceil( L / 100.8 ) )
        posts = np.linspace( 0.0, L, bays + 1 )
        for t in posts:
            run.bar( model, paint, t, 0.0, -0.5, height + 1.6, ( 2.36, 1.57 ) )
        for t0, t1 in zip( posts, posts[1:] ):
            p0_, p1_ = t0 + 1.6, t1 - 1.6
            count = max( 2, int( ( p1_ - p0_ ) / pitch ) + 1 )
            for t in np.linspace( p0_ + 0.5, p1_ - 0.5, count ):
                run.quad( model, paint, t - 0.1, t + 0.1, 0.0, 2.0, height + 1.2 )
            z = 3.0
            while z < height - 0.5:
                for w in ( 0.22, -0.22 ):
                    run.quad( model, paint, p0_, p1_, w, z, z + 0.24 )
                z += 7.87
            for w in ( 0.22, -0.22 ):
                run.quad( model, paint, p0_, p1_, w, height - 0.5, height - 0.26 )
        run.collide( model, height, 1.0, "plastic" )
        return
    paint = paint or "rw_steel_grey"
    pitch = pitch or 6.3
    bays = max( 1, math.ceil( L / 108.3 ) )
    posts = np.linspace( 0.0, L, bays + 1 )
    for t in posts:                                     # 102 x 44 mm joists behind the rails
        run.bar( model, paint, t, -4.93, -0.5, height - 4.0, ( 1.75, 4.0 ) )
    for t0, t1 in zip( posts, posts[1:] ):
        for z in ( 14.0, height - 16.0 ):                   # 50 mm angle rails, the pales bolted to their faces
            c = run.p( ( t0 + t1 ) / 2, -1.95, z )
            model.oriented_box( c, run.axes, ( t1 - t0, 1.97, 1.97 ), paint )
        count = max( 1, int( ( t1 - t0 ) / pitch ) )
        for t in np.linspace( t0 + pitch / 2, t1 - pitch / 2, count ):
            zv = height - 2.4
            run.quad( model, paint, t - 1.38, t + 1.38, -0.9, 1.5, zv )
            for k, apex in ( ( -1, height - 0.7 ), ( 0, height ), ( 1, height - 0.7 ) ):
                c0, c1 = t + k * 0.92 - 0.46, t + k * 0.92 + 0.46
                model.polygon( paint, [ run.p( c0, -0.9, zv ), run.p( c1, -0.9, zv ),
                                        run.p( ( c0 + c1 ) / 2, -0.9, apex ) ], both_sides=True )
    run.collide( model, height, 6.6, "metal", w=-3.75 )


def construction_fence( model, p0, p1, z0=None ):
    """ A mobile construction fence from p0 to p1: galvanised panels 3.5 x 2 m (a 40 mm tube frame round a 100 x 250 mm
    mesh of 4 mm wire) standing in 700 x 220 x 140 mm concrete feet, clamped together at each foot. Collision 1 thick,
    "plastic"; the feet have none (they're a step). """
    a, b = _line_ends( p0, p1, z0 )
    run = _Run( a, b )
    panels = max( 1, math.ceil( run.length / 137.8 ) )
    joints = np.linspace( 0.0, run.length, panels + 1 )
    galv = "rw_steel_grey"
    for t in joints:
        run.bar( model, "rw_concrete", t, 0.0, 0.0, 5.5, ( 8.7, 25.6 ) )
        run.bar( model, galv, t, 0.0, 70.0, 73.5, ( 3.2, 2.4 ), skip_bottom=False )
    for t0, t1 in zip( joints, joints[1:] ):
        u0, u1 = t0 + 1.2, t1 - 1.2
        for t in ( u0, u1 ):
            rod( model, run.p( t, 0.0, 2.0 ), run.p( t, 0.0, 83.5 ), 0.79, galv, 6 )
        for z in ( 5.5, 83.5 ):
            rod( model, run.p( u0, 0.0, z ), run.p( u1, 0.0, z ), 0.79, galv, 4, turn=math.pi / 4 )
        count = max( 2, int( ( u1 - u0 ) / 3.94 ) )
        for t in np.linspace( u0, u1, count + 1 )[1:-1]:
            run.quad( model, galv, t - 0.08, t + 0.08, 0.0, 5.5, 83.5 )
        z = 5.5 + 9.84
        while z < 83.0:
            run.quad( model, galv, u0, u1, 0.12, z - 0.08, z + 0.08 )
            z += 9.84
    run.collide( model, 84.3, 1.0, "plastic" )


EPAL = ( 31.5, 47.24, 5.67 )      # 800 x 1200 x 144 mm
_EPAL_ROWS = ( -20.77, 0.0, 20.77 )                                     # block rows along the length, 145 mm deep
_EPAL_COLS = ( ( -15.75, -11.81 ), ( -2.85, 2.85 ), ( 11.81, 15.75 ) )  # block and bottom board columns across it
_EPAL_DECK = ( ( -15.75, -10.04 ), ( -8.43, -4.49 ), ( -2.85, 2.85 ), ( 4.49, 8.43 ), ( 10.04, 15.75 ) )


def pallet_stack( model, e, n, z0=0.0, layers=6, along="n" ):
    """ A stack of Euro pallets (EPAL, 1200 x 800 x 144 mm), their length along n or e: on each, three bottom boards,
    nine blocks with the fork openings between them, three cross boards and (on the top one) the five deck boards.
    One wooden box. Returns the stack's top. """
    F = Frame( ( e, n, z0 ), ( 0, 1 ) if along == "n" else ( 1, 0 ) )
    model.grain_paints.add( "rw_wood" )
    W, L, H = EPAL[0] / 2, EPAL[1] / 2, EPAL[2]
    for k in range( layers ):
        z = k * H
        top = k == layers - 1
        for x0, x1 in _EPAL_COLS:
            F.box( model, x0, x1, -L, L, z, z + 0.87, "rw_wood", skip=( "bottom", ) )
        for y in _EPAL_ROWS:
            for x0, x1 in _EPAL_COLS:
                F.box( model, x0, x1, y - 2.85, y + 2.85, z + 0.87, z + 3.94, "rw_wood", skip=( "top", "bottom" ) )
        if top:
            for y in _EPAL_ROWS:
                F.box( model, -W, W, y - 2.85, y + 2.85, z + 3.94, z + 4.8, "rw_wood", skip=( "bottom", ) )
            for x0, x1 in _EPAL_DECK:
                F.box( model, x0, x1, -L, L, z + 4.8, z + H, "rw_wood", skip=( "bottom", ) )
        else:
            F.box( model, -W, W, -L, L, z + 3.94, z + H, "rw_wood" )
    F.collide( model, -W, W, -L, L, 0.0, layers * H, "wood" )
    return z0 + layers * H


def crate( model, e, n, z0=0.0, size=( 47.2, 31.5, 31.5 ), along="n", paint="rw_wood" ):
    """ A framed wooden shipping crate, size ( length along n or e, width, height ): boarded faces inside a frame of
    90 x 20 mm battens along every edge, with a diagonal brace on each long side. One wooden box. Returns its top. """
    F = Frame( ( e, n, z0 ), ( 0, 1 ) if along == "n" else ( 1, 0 ) )
    model.grain_paints.add( paint )
    hl, hw, h = size[0] / 2, size[1] / 2, size[2]
    t, b = 0.8, 3.5
    F.box( model, -hw + t, hw - t, -hl + t, hl - t, 0.0, h - t, paint, skip=( "bottom", ) )
    for xs in ( -1, 1 ):                                  # edges along the length
        for z0_, z1_ in ( ( 0.0, b ), ( h - b, h ) ):
            x0, x1 = sorted( ( xs * hw, xs * ( hw - b ) ) )
            F.box( model, x0, x1, -hl, hl, z0_, z1_, paint, skip=( "front", "back" ) )
    for ys in ( -1, 1 ):                                  # edges across, and the corner posts
        y0, y1 = sorted( ( ys * hl, ys * ( hl - b ) ) )
        for z0_, z1_ in ( ( 0.0, b ), ( h - b, h ) ):
            F.box( model, -hw + b, hw - b, y0, y1, z0_, z1_, paint, skip=( "left", "right" ) )
        for xs in ( -1, 1 ):
            x0, x1 = sorted( ( xs * hw, xs * ( hw - b ) ) )
            F.box( model, x0, x1, y0, y1, b, h - b, paint, skip=( "top", "bottom" ) )
    span = math.hypot( 2 * hl - 2 * b, h - 2 * b )
    angle = math.atan2( h - 2 * b, 2 * hl - 2 * b )
    for xs in ( -1, 1 ):
        _obox( model, F, ( xs * ( hw - t / 2 ), 0.0, h / 2 ), ( 0, math.cos( angle ), math.sin( angle ) ),
               ( xs, 0, 0 ), ( span, t + 0.02, b ), paint )
    F.collide( model, -hw, hw, -hl, hl, 0.0, h, "wood" )
    return z0 + h


def forklift( model, e, n, facing="+n", z0=0.0, lift=0.0 ):
    """ A generic 2.5 t counterbalance forklift (2.5 m to the fork face, 1.15 m wide, overhead guard 2.1 m, 1.65 m
    wheelbase, 7.00-12 and 6.00-9 tyres), forks forward along facing, raised by lift. From (e, n) it runs 51 back to
    the counterweight's back and 48 forward to the forks' faces, and the 1070 mm forks reach 42 beyond that.
    Collision: the body to 46, the mast, and the guard's posts and roof (metal); none on the forks. """
    F = frame_for( e, n, z0, facing )
    Y, cw = "rw_yellow_paint", DARK
    F.box( model, -15.0, 15.0, -30.0, 38.0, 6.0, 30.0, Y )
    for xs in ( -1, 1 ):
        x0, x1 = sorted( ( xs * 15.0, xs * 22.6 ) )
        F.box( model, x0, x1, -27.5, 11.5, 9.0, 30.0, Y )
        x0, x1 = sorted( ( xs * 15.0, xs * 23.8 ) )
        F.box( model, x0, x1, 11.5, 40.5, 28.0, 30.5, Y )
    _side_prism( model, F, [ ( -30.0, 22.0 ), ( -30.0, 46.0 ), ( -44.0, 46.0 ), ( -50.5, 40.0 ), ( -51.0, 26.0 ),
                             ( -48.5, 22.0 ) ], -22.6, 22.6, lambda k: cw, cw )
    F.box( model, -12.5, 12.5, -48.0, -30.0, 6.0, 22.0, cw, skip=( "top", ) )
    F.box( model, -20.0, 20.0, -30.0, -8.0, 30.0, 42.0, Y, skip=( "bottom", ) )
    _side_prism( model, F, [ ( 10.0, 30.0 ), ( 24.0, 30.0 ), ( 24.0, 44.0 ), ( 17.0, 50.0 ), ( 10.0, 50.0 ) ],
                 -20.0, 20.0, lambda k: None if k == 0 else Y, Y )
    F.box( model, -9.0, 9.0, -27.0, -11.0, 42.0, 46.0, "rw_black", skip=( "bottom", ) )
    _obox( model, F, ( 0.0, -27.5, 54.0 ), ( 1, 0, 0 ), ( 0, 1, 0.12 ), ( 18.0, 3.0, 16.0 ), "rw_black" )
    rod( model, F.p( 0.0, 17.0, 49.5 ), F.p( 0.0, 10.0, 57.5 ), 1.2, cw, 4 )
    wheel_n = _unit( _world( F, ( 0.0, -0.6, 1.0 ) ) )
    for s in ( 1.0, -1.0 ):
        disc( model, "rw_black", F.p( 0.0, 9.6, 58.0 ) + s * wheel_n * 0.3, s * wheel_n, 6.5, sides=10,
              up=_world( F, ( 0, 1, 0 ) ) )
    for x in ( -20.0, 20.0 ):                                       # the overhead guard
        _fbeam( model, F, ( x, -29.0, 42.0 ), ( x, -29.0, 82.0 ), ( 2.2, 2.2 ), "rw_black" )
        _fbeam( model, F, ( x, 24.0, 30.5 ), ( x, 20.0, 82.0 ), ( 2.2, 2.2 ), "rw_black" )
        F.box( model, x - 1.1, x + 1.1, -30.1, 21.1, 82.0, 84.0, "rw_black" )
        F.box( model, x - 1.6, x + 1.6, 21.6, 23.8, 64.5, 67.5, { "default": DARK, "front": "rw_white_paint" } )
    for y in ( -29.0, -12.0, 3.0, 20.0 ):
        F.box( model, -18.9, 18.9, y - 1.1, y + 1.1, 82.4, 83.6, "rw_black", skip=() )
    rod( model, F.p( 0.0, -27.0, 84.0 ), F.p( 0.0, -27.0, 87.0 ), 1.6, "rw_yellow_paint", 8, caps=( False, True ) )
    for xs in ( -1, 1 ):                                            # the mast
        x0, x1 = sorted( ( xs * 13.0, xs * 16.5 ) )
        F.box( model, x0, x1, 39.5, 43.5, 4.0, 80.0, cw )
        rod( model, F.p( xs * 14.5, 30.0, 26.0 ), F.p( xs * 14.5, 39.5, 40.0 ), 1.2, cw, 4 )
        x0, x1 = sorted( ( xs * 10.0, xs * 12.8 ) )
        F.box( model, x0, x1, 40.5, 43.0, 4.0 + max( 0.0, lift - 6.0 ), 78.0 + max( 0.0, lift - 6.0 ), cw )
    F.box( model, -16.5, 16.5, 39.5, 43.5, 76.0, 80.0, cw )
    F.box( model, -16.5, 16.5, 39.5, 43.5, 36.0, 39.0, cw )
    zc = lift
    F.box( model, -20.0, 20.0, 43.5, 46.0, zc + 4.0, zc + 18.0, cw )
    for x0, x1 in ( ( -20.0, -18.0 ), ( -7.5, -5.5 ), ( 5.5, 7.5 ), ( 18.0, 20.0 ) ):
        F.box( model, x0, x1, 44.0, 46.0, zc + 18.0, zc + 46.0, cw, skip=( "bottom", ) )
    F.box( model, -20.0, 20.0, 44.0, 46.0, zc + 46.0, zc + 48.0, cw )
    for x in ( -11.0, 11.0 ):
        F.box( model, x - 1.95, x + 1.95, 46.0, 47.8, zc, zc + 19.0, cw, skip=( "bottom", ) )
        F.box( model, x - 1.95, x + 1.95, 47.8, 89.8, zc, zc + 1.8, cw, skip=( "back", ) )
    for y, r, x0, x1 in ( ( 26.0, 13.2, 16.3, 23.4 ), ( -39.0, 10.6, 13.5, 19.0 ) ):
        for xs in ( -1, 1 ):
            rod( model, F.p( xs * x0, y, r ), F.p( xs * x1, y, r ), r, "rw_rubber", 10, caps=( True, True ) )
            disc( model, "rw_steel_grey", F.p( xs * ( x1 + 0.05 ), y, r ), xs * F.x, r * 0.6, sides=8 )
    F.collide( model, -22.6, 22.6, -51.0, 39.5, 0.0, 46.0, "metal" )
    F.collide( model, -16.5, 16.5, 39.5, 46.0, 0.0, 80.0, "metal" )
    for x in ( -20.0, 20.0 ):
        F.collide( model, x - 1.1, x + 1.1, -30.1, -27.9, 46.0, 82.0, "metal" )
        F.collide( model, x - 1.1, x + 1.1, 19.0, 23.5, 46.0, 82.0, "metal" )
    F.collide( model, -21.1, 21.1, -30.1, 21.1, 82.0, 84.0, "metal" )


# Road vehicles: half profiles ( a, W, zb, zm, wb, zbelt, wr, zrs, wi, zri, zt ) at depth a behind the front: the
# body's side (W) from its bottom zb to the shoulder zm, the belt line (wb, zbelt) under the side windows, their tops
# (wr, zrs), the roof's edge (wi, zri) and its crown zt. In front of the windscreen the "windows" close up and the
# roof is the bonnet.
HATCH = [   # a generic compact hatchback: 4.28 m long, 1.79 m wide, 1.46 m tall, 2.64 m wheelbase
    ( 0.0, 30.5, 9.5, 26.0, 29.0, 29.5, 26.0, 30.5, 16.0, 31.0, 31.2 ),
    ( 4.0, 34.0, 9.0, 28.0, 33.0, 32.0, 31.0, 33.0, 20.0, 33.6, 33.8 ),
    ( 10.0, 35.2, 8.5, 30.0, 34.0, 33.5, 33.0, 34.3, 22.0, 35.0, 35.2 ),
    ( 46.0, 35.2, 8.0, 30.0, 34.0, 37.5, 33.0, 38.0, 24.0, 38.8, 39.0 ),
    ( 72.0, 35.2, 8.0, 30.0, 33.6, 38.5, 28.8, 54.0, 24.5, 56.2, 56.6 ),
    ( 95.0, 35.2, 8.0, 30.0, 33.6, 39.0, 28.5, 55.0, 24.0, 57.0, 57.3 ),
    ( 128.0, 35.2, 8.0, 30.0, 33.6, 40.0, 28.3, 54.5, 23.8, 56.4, 56.8 ),
    ( 150.0, 35.0, 8.2, 30.0, 33.2, 40.8, 27.6, 53.6, 23.0, 55.4, 55.8 ),     # the roof's end
    ( 162.0, 34.4, 8.6, 30.0, 32.6, 40.5, 30.0, 41.4, 22.6, 42.0, 42.2 ),     # the rear window's foot
    ( 168.7, 32.0, 9.5, 29.0, 31.0, 38.0, 29.6, 38.8, 22.0, 39.2, 39.4 ),     # the tailgate and bumper
]
ESTATE = HATCH[:7] + [   # the same car as an estate: 4.63 m long, 2.69 m wheelbase
    ( 171.0, 35.0, 8.2, 30.0, 33.3, 41.0, 27.8, 54.0, 23.2, 55.8, 56.2 ),
    ( 178.0, 34.4, 8.6, 30.0, 32.6, 40.8, 30.2, 41.6, 22.6, 42.2, 42.4 ),
    ( 182.4, 32.0, 9.5, 29.0, 31.0, 38.0, 29.6, 38.8, 22.0, 39.2, 39.4 ),
]
VAN = [     # a generic panel van: 4.9 m long, 1.9 m wide, 1.99 m tall, 3.0 m wheelbase
    ( 0.0, 33.5, 11.0, 24.0, 33.0, 34.0, 31.0, 36.5, 20.0, 37.3, 37.5 ),
    ( 4.0, 36.5, 10.5, 30.0, 36.0, 38.5, 35.0, 39.3, 22.0, 39.9, 40.1 ),
    ( 12.0, 37.5, 10.0, 33.0, 37.0, 41.0, 36.0, 41.6, 24.0, 42.2, 42.4 ),
    ( 26.0, 37.5, 10.0, 33.0, 37.0, 43.5, 36.0, 44.0, 25.0, 45.0, 45.2 ),
    ( 50.0, 37.5, 10.0, 33.0, 36.6, 44.5, 33.5, 74.0, 30.0, 77.6, 78.0 ),
    ( 190.0, 37.5, 10.5, 33.0, 36.6, 45.0, 34.0, 75.0, 30.0, 78.0, 78.3 ),
    ( 193.1, 36.8, 11.0, 33.0, 36.2, 45.0, 33.5, 74.5, 29.5, 77.0, 77.3 ),
]
CAR_PAINTS = ( "rw_train_grey", "rw_train_white", "rw_train_dark", "rw_train_blue", "rw_train_red" )


def _profile_at( keys, a ):
    cols = list( zip( *keys ) )
    W, zb, zm, wb, zbelt, wr, zrs, wi, zri, zt = ( float( np.interp( a, cols[0], c ) ) for c in cols[1:] )
    return [ ( W, zb ), ( W, zm ), ( wb, zbelt ), ( wr, zrs ), ( wi, zri ), ( 0.0, zt ) ]


def _clean( pts ):
    out = []
    for p in pts:
        if not out or np.linalg.norm( np.subtract( p, out[-1] ) ) > 1e-6:
            out.append( p )
    if len( out ) > 1 and np.linalg.norm( np.subtract( out[0], out[-1] ) ) < 1e-6:
        out.pop()
    return out


def _road_vehicle( model, F, keys, axles, tyre, arch, paint_at, splits=() ):
    """ A car or van body lofted through keys in F (front at y 0, a behind it at y = -a), wheel arches cut round the
    axles (depths) for tyres of radius tyre[0] and width tyre[1] on rims of tyre[2], arches of radius arch.
    paint_at( segment, a0, a1 ) paints each strip (segments 1-4 from the shoulder up; 0 is the lower side). """
    stations = sorted( { k[0] for k in keys } | set( splits ) )
    profiles = { a: _profile_at( keys, a ) for a in stations }
    for a0, a1 in zip( stations, stations[1:] ):
        p0, p1 = profiles[a0], profiles[a1]
        for k in range( 1, 5 ):
            paint = paint_at( k, a0, a1 )
            if not paint:
                continue
            nx, nz = p1[k + 1][1] - p1[k][1] + p0[k + 1][1] - p0[k][1], -( p1[k + 1][0] - p1[k][0] + p0[k + 1][0]
                                                                              - p0[k][0] )
            for xs in ( 1.0, -1.0 ):
                pts = _clean( [ ( xs * p0[k][0], -a0, p0[k][1] ), ( xs * p0[k + 1][0], -a0, p0[k + 1][1] ),
                                ( xs * p1[k + 1][0], -a1, p1[k + 1][1] ), ( xs * p1[k][0], -a1, p1[k][1] ) ] )
                if len( pts ) >= 3:
                    _fpoly( model, F, paint, pts, ( xs * nx, 0, nz ) )
    radius, width, rim = tyre
    zc, steps = radius, 8
    assert all( zc + arch < _profile_at( keys, ac )[1][1] for ac in axles )
    cuts = set( stations )
    for ac in axles:
        cuts |= { ac - arch * math.cos( math.pi * j / steps ) for j in range( steps + 1 ) }
    cuts = sorted( c for c in cuts if keys[0][0] <= c <= keys[-1][0] )

    def bottom( a, mid ):
        for ac in axles:
            if abs( mid - ac ) < arch:
                return zc + math.sqrt( max( 0.0, arch * arch - ( a - ac ) ** 2 ) )
        return _profile_at( keys, a )[0][1]

    for a0, a1 in zip( cuts, cuts[1:] ):
        mid = ( a0 + a1 ) / 2
        paint = paint_at( 0, a0, a1 )
        q0, q1 = _profile_at( keys, a0 ), _profile_at( keys, a1 )
        for xs in ( 1.0, -1.0 ):
            pts = _clean( [ ( xs * q0[0][0], -a0, bottom( a0, mid ) ), ( xs * q1[0][0], -a1, bottom( a1, mid ) ),
                            ( xs * q1[1][0], -a1, q1[1][1] ), ( xs * q0[1][0], -a0, q0[1][1] ) ] )
            _fpoly( model, F, paint, pts, ( xs, 0, 0 ) )
    depth = 8.5
    for ac in axles:
        arc = [ ( ac - arch * math.cos( math.pi * j / steps ), zc + arch * math.sin( math.pi * j / steps ) )
                for j in range( steps + 1 ) ]
        ends = [ ( a, _profile_at( keys, a )[0][1] ) for a in ( ac - arch, ac + arch ) ]
        for xs in ( 1.0, -1.0 ):
            for ( a0, z0 ), ( a1, z1 ) in zip( arc, arc[1:] ):
                w0, w1 = _profile_at( keys, a0 )[0][0], _profile_at( keys, a1 )[0][0]
                _fpoly( model, F, "rw_black", [ ( xs * w0, -a0, z0 ), ( xs * w1, -a1, z1 ),
                                                ( xs * ( w1 - depth ), -a1, z1 ), ( xs * ( w0 - depth ), -a0, z0 ) ],
                        ( 0, ( a0 + a1 ) / 2 - ac, zc - ( z0 + z1 ) / 2 ) )
            for ( a, zb ), toward in zip( ends, ( -1.0, 1.0 ) ):
                w = _profile_at( keys, a )[0][0]
                _fpoly( model, F, "rw_black", [ ( xs * w, -a, zb ), ( xs * w, -a, zc ), ( xs * ( w - depth ), -a, zc ),
                                                ( xs * ( w - depth ), -a, zb ) ], ( 0, toward, 0 ) )
            wall = [ ( xs * ( _profile_at( keys, a )[0][0] - depth ), -a, z ) for a, z in arc ]
            wall += [ ( xs * ( _profile_at( keys, a )[0][0] - depth ), -a, z ) for a, z in reversed( ends ) ]
            _fpoly( model, F, "rw_black", wall, ( xs, 0, 0 ) )
            x1 = _profile_at( keys, ac )[0][0] - 0.7
            rod( model, F.p( xs * ( x1 - width ), -ac, radius ), F.p( xs * x1, -ac, radius ), radius, "rw_rubber", 10,
                 caps=( True, True ) )
            disc( model, "rw_steel_grey", F.p( xs * ( x1 + 0.05 ), -ac, radius ), xs * F.x, rim, sides=10 )
    a_front, a_rear = keys[0][0], keys[-1][0]
    w_floor = min( k[1] for k in keys ) - 0.5
    z_floor = max( k[2] for k in keys )
    _fpoly( model, F, "rw_black", [ ( -w_floor, -a_front - 2.0, z_floor ), ( w_floor, -a_front - 2.0, z_floor ),
                                    ( w_floor, -a_rear + 2.0, z_floor ), ( -w_floor, -a_rear + 2.0, z_floor ) ],
            ( 0, 0, -1 ) )
    for a, toward in ( ( a_front, 1.0 ), ( a_rear, -1.0 ) ):
        _section( model, F, _profile_at( keys, a ), a, toward, paint_at( 0, a, a ) )


def _seam( model, F, keys, a, xs, z0, z1, width=0.4, lift=0.1 ):
    """ A dark panel seam up a road vehicle's side at depth a on side xs, from z0 to z1, over its profile. """
    prof = _profile_at( keys, a )
    for ( xa, za ), ( xb, zb ) in zip( prof, prof[1:] ):
        lo, hi = max( za, z0 ), min( zb, z1 )
        if hi - lo < 1e-3 or zb - za < 1e-3:
            continue
        nx, nz = zb - za, -( xb - xa )
        k = lift / math.hypot( nx, nz )
        xl, xh = ( xa + ( xb - xa ) * ( z - za ) / ( zb - za ) + nx * k for z in ( lo, hi ) )
        _fpoly( model, F, "rw_black", [ ( xs * xl, -a, lo + nz * k ), ( xs * xl, -a - width, lo + nz * k ),
                                        ( xs * xh, -a - width, hi + nz * k ), ( xs * xh, -a, hi + nz * k ) ],
                ( xs * nx, 0, nz ) )


def _vehicle_frame( e, n, along, length, z0 ):
    sign = -1.0 if along.startswith( "-" ) else 1.0
    fwd = ( 0.0, sign ) if along.endswith( "n" ) else ( sign, 0.0 )
    return Frame( ( e + fwd[0] * length / 2, n + fwd[1] * length / 2, z0 ), fwd )


def car( model, e, n, along="+n", paint="rw_train_grey", z0=0.0, kind="hatch" ):
    """ A parked generic modern compact car, kind "hatch" (4.28 m) or "estate" (4.63 m), 1.79 m wide and 1.46 m tall on
    205/55 R16 tyres, its nose towards along ("+n", "-n", "+e", "-e") and (e, n) its footprint's centre. Body paint
    (the rw_train_* colours suit it), dark glass, black trim, white number plates. One metal box. """
    keys = ESTATE if kind == "estate" else HATCH
    L = keys[-1][0]
    F = _vehicle_frame( e, n, along, L, z0 )
    rear_axle = 34.6 + ( 105.7 if kind == "estate" else 103.8 )
    glass = [ ( 4, 46.0, 72.0 ) ]
    sides = [ ( 46.0, 92.0 ), ( 97.0, 128.0 ) ]
    if kind == "estate":
        glass.append( ( 4, 171.0, 178.0 ) )
        sides.append( ( 132.0, 164.0 ) )
    else:
        glass.append( ( 4, 150.0, 162.0 ) )
        sides[1] = ( 97.0, 134.0 )

    def paint_at( k, a0, a1 ):
        mid = ( a0 + a1 ) / 2
        if k == 2:
            if any( s0 <= mid <= s1 for s0, s1 in sides ):
                return "rw_window_dark"
            return "rw_black" if 92.0 <= mid <= 97.0 else paint
        if any( k == g and g0 <= mid <= g1 for g, g0, g1 in glass ):
            return "rw_window_dark"
        return paint

    splits = [ 92.0, 97.0 ] + ( [ 132.0, 164.0 ] if kind == "estate" else [ 134.0 ] )
    _road_vehicle( model, F, keys, ( 34.6, rear_axle ), ( 12.4, 8.1, 8.0 ), 14.5, paint_at, splits )
    for xs in ( -1, 1 ):                                            # lamps, mirrors
        F.quad( model, "rw_steel_grey", xs * 22.0, 0.04, 28.0, 10.0, 3.0 )
        F.quad( model, "rw_red_paint", xs * 26.0, -L - 0.04, 29.5, 7.0, 3.6, "back" )
        x0, x1 = sorted( ( xs * 33.8, xs * 39.8 ) )
        F.box( model, x0, x1, -53.5, -50.0, 39.0, 43.5, { "default": paint, "back": "rw_black" } )
    F.quad( model, "rw_black", 0.0, 0.04, 23.2, 26.0, 4.0 )
    F.quad( model, "rw_black", 0.0, 0.04, 12.0, 34.0, 3.0 )
    F.quad( model, "rw_white_paint", 0.0, 0.06, 17.0, 20.5, 4.3 )
    F.quad( model, "rw_white_paint", 0.0, -L - 0.06, 20.0, 20.5, 4.3, "back" )
    F.quad( model, "rw_black", 0.0, -L - 0.04, 11.8, 40.0, 2.6, "back" )
    F.collide( model, -35.2, 35.2, -L, 0.0, 0.0, 57.3, "metal" )


def van( model, e, n, along="+n", paint="rw_train_white", z0=0.0 ):
    """ A parked generic panel van (4.9 m long, 1.9 m wide, 1.99 m tall, 3 m wheelbase, 215/65 R16 tyres): glazed
    cab, blind load area with a sliding door's seam on each side, two rear doors. Its nose towards along, (e, n) its
    footprint's centre. One metal box. """
    L = VAN[-1][0]
    F = _vehicle_frame( e, n, along, L, z0 )

    def paint_at( k, a0, a1 ):
        mid = ( a0 + a1 ) / 2
        if k == 2 and 26.0 <= mid <= 64.0:
            return "rw_window_dark"
        if k == 4 and 26.0 <= mid <= 50.0:
            return "rw_window_dark"
        return paint

    _road_vehicle( model, F, VAN, ( 37.0, 155.1 ), ( 13.5, 8.5, 8.0 ), 15.5, paint_at, [ 64.0 ] )
    for xs in ( -1, 1 ):
        F.quad( model, "rw_steel_grey", xs * 25.0, 0.04, 31.5, 12.0, 4.0 )
        F.quad( model, "rw_red_paint", xs * 33.0, -L - 0.04, 40.0, 3.6, 16.0, "back" )
        x0, x1 = sorted( ( xs * 36.6, xs * 41.5 ) )
        F.box( model, x0, x1, -30.0, -27.0, 46.0, 56.0, { "default": "rw_black" } )
        for a in ( 68.0, 112.0 ):                                   # the sliding door's seams
            _seam( model, F, VAN, a, xs, 12.0, 73.0 )
    F.quad( model, "rw_black", 0.0, 0.04, 31.0, 36.0, 5.0 )
    F.quad( model, "rw_white_paint", 0.0, 0.06, 18.0, 20.5, 4.3 )
    F.quad( model, "rw_black", 0.0, -L - 0.04, 44.0, 0.4, 62.0, "back" )
    F.quad( model, "rw_white_paint", 0.0, -L - 0.06, 18.0, 20.5, 4.3, "back" )
    F.quad( model, "rw_black", 0.0, -L - 0.04, 12.5, 66.0, 3.0, "back" )
    F.collide( model, -37.5, 37.5, -L, 0.0, 0.0, 78.3, "metal" )


def bollard( model, e, n, z0=0.0, kind="steel" ):
    """ A bollard: "steel" (102 mm tube, 1 m tall, anthracite with a white reflective band and a domed cap) or
    "concrete" (400 mm round, 700 mm tall, chamfered). Collision to its top. """
    if kind == "concrete":
        model.cylinder( ( e, n ), 7.87, z0, z0 + 25.6, { "side": "rw_concrete" }, sides=12 )
        _frustum( model, ( e, n, z0 + 25.6 ), ( e, n, z0 + 27.56 ), 7.87, 5.9, "rw_concrete", sides=12 )
        disc( model, "rw_concrete", ( e, n, z0 + 27.56 ), ( 0, 0, 1 ), 5.9, sides=12 )
        model.collision_box( ( e - 7.87, n - 7.87, z0 ), ( e + 7.87, n + 7.87, z0 + 27.56 ), "default" )
        return
    for z0_, z1_, paint in ( ( 0.0, 31.5, DARK ), ( 31.5, 34.5, "rw_white_paint" ), ( 34.5, 38.6, DARK ) ):
        model.cylinder( ( e, n ), 2.0, z0 + z0_, z0 + z1_, { "side": paint }, sides=10 )
    _frustum( model, ( e, n, z0 + 38.6 ), ( e, n, z0 + 39.4 ), 2.0, 1.2, DARK, sides=10 )
    disc( model, DARK, ( e, n, z0 + 39.4 ), ( 0, 0, 1 ), 1.2, sides=10 )
    model.collision_box( ( e - 2.0, n - 2.0, z0 ), ( e + 2.0, n + 2.0, z0 + 39.4 ), "metal" )


# ---------------------------------------------------------------------------------------------------------------------
# Preview

def _slab( model, paint, e0, e1, n0, n1, z, under=None, depth=0.0 ):
    """ A level floor at z (the preview's ground), with its edge faces down to z - depth. """
    model.polygon( paint, [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ] )
    if depth > 0:
        model.box( ( e0, n0, z - depth ), ( e1, n1, z ), { "default": under or paint, "+z": None, "-z": None } )


def showcase():
    """ [ ( name, model ) ]: every prop, laid out as a short stretch of railway. Tracks A (e 0) and B (e 180, 4.57 m
    apart) joined by a crossover and wired with cantilevers and a portal; A ends at a buffer stop with a locomotive,
    a coach and a control car at it, B has the EMU at a platform (e 246..700, z 0) with the furniture in rows; a
    siding (e -400) holds the wagons, and a paved yard west of it (z 0) the containers and the yard's clutter. """
    out = []

    def prop( name ):
        m = K.Model()
        out.append( ( name, m ) )
        return m

    rz, A, B, S = -30.0, 0.0, 180.0, -400.0
    n0, n1, nx = -3400.0, 420.0, -2900.0
    wire_z = rz + WIRE_HEIGHT
    ground = prop( "ground (preview only)" )
    _slab( ground, "rw_ballast", -560.0, 246.0, n0, n1, rz - 7.0 )
    _slab( ground, "rw_paving", 246.0, 700.0, -1500.0, 300.0, 0.0, "rw_concrete", 37.0 )
    _slab( ground, "rw_ballast", 246.0, 700.0, n0, -1500.0, rz - 7.0 )
    _slab( ground, "rw_ballast", 246.0, 700.0, 300.0, n1, rz - 7.0 )
    _slab( ground, "rw_asphalt", -1750.0, -560.0, -1800.0, n1, 0.0, "rw_concrete", 37.0 )
    _slab( ground, "rw_ballast", -1750.0, -560.0, n0, -1800.0, rz - 7.0 )

    plain = prop( "track (plain, 3 x 96 m)" )
    for e in ( A, B ):
        track( plain, e, n0, nx, rz )
    m = prop( "crossover (1:7.5)" )
    n_end = crossover( m, A, B, nx, +1, rz, radius=5512.0, frog=7.5 )
    for e in ( A, B ):
        track( plain, e, n_end, n1, rz )
    track( plain, S, n0, n1, rz )
    m = prop( "buffer stop" )
    buffer_stop( m, A, n1 - 140.0, -1, rz )
    m = prop( "buffer stop" )
    buffer_stop( m, S, n1 - 140.0, -1, rz )
    m = prop( "ks signal" )
    ks_signal( m, A, -3150.0, rz, -1, side=-1, aspect="green" )
    m = prop( "ks signal" )
    ks_signal( m, B, -3150.0, rz, -1, side=+1, aspect="red" )

    m = prop( "contact lines (2 x 96 m)" )
    supports = ( -3250.0, -1700.0, -150.0 )
    wa = contact_line( m, A, n0 + 60.0, n1 - 40.0, rz, supports )
    wb = contact_line( m, B, n0 + 60.0, n1 - 40.0, rz, supports, first=-1 )
    for k, e_mast in ( ( 0, -130.0 ), ( 2, -130.0 ) ):
        m = prop( "cantilever mast" )
        cantilever_mast( m, e_mast, supports[k], A, rz, stagger=wa[k][1] )
    for k, e_mast in ( ( 0, 330.0 ), ( 2, 620.0 ) ):
        m = prop( "cantilever mast" )
        cantilever_mast( m, e_mast, supports[k], B, rz, stagger=wb[k][1] )
    m = prop( "portal" )
    portal( m, -130.0, 330.0, supports[1], rz, [ ( A, wa[1][1] ), ( B, wb[1][1] ) ] )

    m = prop( "emu (2 cars, doors open east)" )
    emu( m, B, 200.0, +1, rz, platform_side=+1, doors_open=True, wire_z=wire_z )
    m = prop( "loco" )
    n = loco( m, A, 150.0, +1, rz, wire_z=wire_z )
    m = prop( "coach" )
    n = coach( m, A, n - 1.0, +1, rz )
    m = prop( "control car" )
    control_car( m, A, n - 1.0 - COACH_LENGTH, -1, rz )
    m = prop( "container flat (40 + 20 ft)" )
    n = container_flat( m, S, n1 - 170.0, +1, rz,
                        containers=( "40", { "size": "20", "paint": "rw_container_red" } ) )
    m = prop( "open wagon" )
    n = open_wagon( m, S, n - 1.0, +1, rz )
    m = prop( "covered wagon (doors open)" )
    covered_wagon( m, S, n - 1.0, +1, rz, doors_open=True )

    m = prop( "container 40 ft (doors open)" )
    container( m, -760.0, -420.0, 0.0, "40", "n", "rw_container_green", doors_open=True )
    m = prop( "container 20 ft" )
    container( m, -760.0, -900.0, 0.0, "20", "n", "rw_container_blue" )
    m = prop( "container 20 ft" )
    container( m, -760.0, -900.0, 102.0, "20", "n", "rw_container_grey" )
    m = prop( "container 20 ft high cube" )
    container( m, -880.0, -900.0, 0.0, "20", "n", "rw_container_orange", high_cube=True, door_end=-1 )

    canopy = prop( "canopy (preview only)" )
    canopy.box( ( 380.0, -1150.0, 200.0 ), ( 460.0, -350.0, 204.0 ), { "default": DARK, "+z": "rw_steel_grey" } )
    for n in ( -1100.0, -400.0 ):
        canopy.box( ( 416.0, n - 4.0, 0.0 ), ( 424.0, n + 4.0, 200.0 ), DARK, skip=( "-z", "+z" ) )
    rows = [
        ( "bench", lambda m: bench( m, 600.0, -1380.0, facing="-e" ) ),
        ( "bin", lambda m: bin( m, 600.0, -1310.0, facing="-e" ) ),
        ( "ticket machine", lambda m: ticket_machine( m, 600.0, -1250.0, facing="-e" ) ),
        ( "vending machine", lambda m: vending_machine( m, 600.0, -1170.0, facing="-e" ) ),
        ( "timetable case", lambda m: timetable_case( m, 600.0, -1080.0, facing="-e" ) ),
        ( "info pillar", lambda m: info_pillar( m, 600.0, -1010.0, facing="-e" ) ),
        ( "shelter", lambda m: shelter( m, 560.0, 640.0, -940.0, -720.0, facing="-e", poster="poster_alps" ) ),
        ( "kiosk", lambda m: kiosk( m, 540.0, 660.0, -640.0, -480.0, "-e" ) ),
        ( "hanging display", lambda m: hanging_display( m, 420.0, -1050.0, 200.0, "gleis_3_display" ) ),
        ( "hanging sign", lambda m: hanging_sign( m, 420.0, -820.0, 200.0, [ "gleis_3_4", "to_gleis_left" ],
                                                  along="e" ) ),
        ( "clock", lambda m: clock( m, 420.0, -680.0, 125.0, along="n", z_top=200.0 ) ),
        ( "pendant lamp", lambda m: pendant_lamp( m, 420.0, -950.0, 200.0, 150.0 ) ),
        ( "pendant lamp", lambda m: pendant_lamp( m, 420.0, -520.0, 200.0, 150.0 ) ),
        ( "lamp post", lambda m: lamp_post( m, 420.0, -1440.0, 160.0 ) ),
        ( "luggage cart", lambda m: luggage_cart( m, 360.0, -260.0, "n" ) ),
        ( "bench", lambda m: bench( m, 600.0, -300.0, facing="-e" ) ),
        ( "bin", lambda m: bin( m, 600.0, -220.0, facing="-e" ) ),
    ]
    yard = [
        ( "fence mesh (25 m)", lambda m: fence( m, ( -1700.0, -700.0 ), ( -1700.0, 285.0 ), kind="mesh" ) ),
        ( "fence palisade (25 m)", lambda m: fence( m, ( -1700.0, -1750.0 ), ( -1700.0, -760.0 ),
                                                   kind="palisade" ) ),
        ( "construction fence (14 m)", lambda m: construction_fence( m, ( -1550.0, -1700.0 ),
                                                                     ( -1000.0, -1700.0 ) ) ),
        ( "pallet stack (6)", lambda m: pallet_stack( m, -1500.0, -1400.0, layers=6 ) ),
        ( "pallet stack (3)", lambda m: pallet_stack( m, -1450.0, -1400.0, layers=3 ) ),
        ( "pallet stack (2)", lambda m: pallet_stack( m, -1480.0, -1300.0, layers=2, along="e" ) ),
        ( "crate", lambda m: crate( m, -1350.0, -1400.0 ) ),
        ( "crate", lambda m: crate( m, -1350.0, -1400.0, 31.5, size=( 31.5, 23.6, 23.6 ) ) ),
        ( "forklift", lambda m: forklift( m, -1250.0, -1220.0, "-e" ) ),
        ( "forklift (forks up)", lambda m: forklift( m, -1150.0, -1450.0, "+n", lift=40.0 ) ),
        ( "car hatchback", lambda m: car( m, -1000.0, -80.0, "+n", "rw_train_red" ) ),
        ( "car estate", lambda m: car( m, -1090.0, -80.0, "-n", "rw_train_grey", kind="estate" ) ),
        ( "car hatchback", lambda m: car( m, -1180.0, -80.0, "+n", "rw_train_blue" ) ),
        ( "van", lambda m: van( m, -1280.0, -60.0, "+n", "rw_train_white" ) ),
        ( "car estate", lambda m: car( m, -1160.0, -700.0, "+e", "rw_train_dark", kind="estate" ) ),
    ]
    for k in range( 6 ):
        yard.append( ( "bollard steel", lambda m, k=k: bollard( m, -620.0, -1300.0 + 70.0 * k ) ) )
    for k in range( 3 ):
        yard.append( ( "bollard concrete", lambda m, k=k: bollard( m, -700.0 - 60.0 * k, -1560.0,
                                                                   kind="concrete" ) ) )
    for name, build in rows + yard:
        build( prop( name ) )
    return out


SHOWCASE_VIEWS = [   # ( name, eye, target, horizontal field of view )
    ( "overview", ( 1500.0, -3900.0, 1400.0 ), ( -350.0, -1300.0, 0.0 ), 70 ),
    ( "throat", ( 330.0, -3300.0, 60.0 ), ( 60.0, -2300.0, -10.0 ), 75 ),
    ( "signals", ( -260.0, -3340.0, 70.0 ), ( 90.0, -3100.0, 90.0 ), 80 ),
    ( "control_car", ( -230.0, -3000.0, 110.0 ), ( 0.0, -2600.0, 70.0 ), 75 ),
    ( "coach", ( -330.0, -1800.0, 90.0 ), ( 0.0, -1800.0, 80.0 ), 85 ),
    ( "loco", ( -250.0, 400.0, 110.0 ), ( 0.0, -100.0, 70.0 ), 75 ),
    ( "emu", ( 560.0, 380.0, 90.0 ), ( 180.0, -250.0, 80.0 ), 75 ),
    ( "emu_doors", ( 420.0, -620.0, 64.0 ), ( 180.0, -820.0, 60.0 ), 80 ),
    ( "catenary", ( 90.0, -1480.0, 100.0 ), ( 90.0, -1700.0, 230.0 ), 85 ),
    ( "platform", ( 360.0, -1560.0, 70.0 ), ( 560.0, -900.0, 60.0 ), 75 ),
    ( "platform_north", ( 380.0, 250.0, 72.0 ), ( 560.0, -700.0, 90.0 ), 75 ),
    ( "wagons", ( -140.0, 450.0, 230.0 ), ( -400.0, -500.0, 50.0 ), 70 ),
    ( "wagons_side", ( -640.0, -1050.0, 90.0 ), ( -400.0, -1200.0, 80.0 ), 85 ),
    ( "containers", ( -560.0, -100.0, 130.0 ), ( -820.0, -650.0, 50.0 ), 75 ),
    ( "yard", ( -820.0, -1650.0, 130.0 ), ( -1350.0, -1250.0, 30.0 ), 80 ),
    ( "cars", ( -900.0, 200.0, 110.0 ), ( -1150.0, -100.0, 30.0 ), 75 ),
]


def preview( out_dir, views=None ):
    """ Renders the showcase into out_dir (perspective views and a top view) and prints each prop's triangles and
    collision. """
    import railhead_preview as RP

    for paint, colour in ( ( "rw_signs", ( 0.08, 0.17, 0.38 ) ), ( "rw_posters", ( 0.85, 0.82, 0.70 ) ),
                           ( "rw_shopsigns", ( 0.75, 0.15, 0.12 ) ), ( "rw_displays", ( 0.15, 0.30, 0.65 ) ) ):
        RP.STAND_INS.setdefault( paint, colour )
    items = showcase()
    tally = {}
    for name, m in items:
        t = tally.setdefault( name, [ 0, 0, 0, 0 ] )
        t[0] += 1
        t[1] += m.triangle_count()
        t[2] += len( m.boxes )
        t[3] += len( m.hulls )
    print( f"{'prop':34s} {'count':>5s} {'triangles':>10s} {'each':>7s} {'boxes':>6s} {'hulls':>6s}" )
    for name, ( count, tris, boxes, hulls ) in tally.items():
        print( f"{name:34s} {count:5d} {tris:10d} {tris // count:7d} {boxes:6d} {hulls:6d}" )
    total = sum( m.triangle_count() for _, m in items )
    print( f"{'total':34s} {len( items ):5d} {total:10d}" )
    models = [ m for _, m in items ]
    out = Path( out_dir )
    out.mkdir( parents=True, exist_ok=True )
    opaque, glass = RP.triangles( models ), RP.triangles( models, glass=True )
    RP.top_down( opaque, glass, ( -1800.0, 750.0, -3450.0, 470.0 ), 4.0 ).save( out / "top.png" )
    print( f"wrote {out / 'top.png'}" )
    for name, eye, target, fov in SHOWCASE_VIEWS:
        if views and name not in views:
            continue
        RP.perspective( opaque, glass, eye, target, fov=fov ).save( out / f"{name}.png" )
        print( f"wrote {out / name}.png" )


def main( argv=None ):
    parser = argparse.ArgumentParser( description="Railhead's props: renders a showcase of them (writes no assets)." )
    parser.add_argument( "--preview", metavar="DIR", required=True, help="where to write the renders" )
    parser.add_argument( "--views", nargs="*", help="only these views (" + ", ".join(
        v[0] for v in SHOWCASE_VIEWS ) + "); the top view is always written" )
    args = parser.parse_args( argv )
    preview( args.preview, args.views )


if __name__ == "__main__":
    main()
