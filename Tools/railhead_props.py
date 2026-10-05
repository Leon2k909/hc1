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
# The EMU: a two-car double-deck regional unit in the manner of Germany's double-deck EMUs (Bombardier's Twindexx,
# Stadler's KISS): two 19.4 m cars on their own bogies, a cab at each end of the unit, 2.88 m wide and 4.63 m tall.
# Each car has mid-level ends over its bogies and two decks between them; the doors are at the double-deck part's
# ends, their floor 760 mm over the rail, level with the platforms. The livery is the regional trains' usual one, red
# (or the body paint) with a light grey stripe low down and a grey roof, without any operator's name or logo.

EMU_CAR = 763.0             # a car from its cab's coupler face (or the gangway's) to its inner end
EMU_W = 56.7
EMU_ROOF = 182.3
EMU_FLOOR = 30.0
EMU_GAP = 14.0              # the gangway between the cars
EMU_SKIRT = 19.0            # the mid-level ends' underframe
EMU_LOW = 13.0              # the lower deck's underside, between the bogies
EMU_CUT = 42.0              # the bogie cut-outs' top
EMU_SIDE_TOP = 146.0        # the side wall is upright to here, then curves into the roof
EMU_UPPER = [ ( EMU_W, EMU_SIDE_TOP ), ( 56.4, 152.0 ), ( 55.5, 158.0 ), ( 53.5, 164.0 ), ( 50.0, 169.0 ),
              ( 44.5, 174.0 ), ( 36.0, 178.0 ), ( 25.0, 180.8 ), ( 12.0, 182.0 ), ( 0.0, EMU_ROOF ) ]
EMU_ROOF_LINE = 164.0       # red below it, grey roof above
EMU_STRIPE = ( 19.0, 24.0 )
EMU_NOSE = 112.0            # the cab's loft reaches this far behind the coupler face
EMU_WHEELBASE = 98.0        # 2.5 m bogies
EMU_WHEEL = 18.1            # 920 mm wheels
# Along a car, behind its cab's coupler face: the bogies' centres, the doors' openings and the decks.
EMU_BOGIES = ( 175.0, 670.0 )
EMU_DOORS = ( 245.0, 548.0 )                # each opening 51 long
EMU_DECKS = ( 296.0, 548.0 )                # the double-deck part
EMU_LOWER_WIN = ( 38.0, 76.0 )              # the lower deck's windows, z
EMU_UPPER_WIN = ( 108.0, 144.0 )            # the upper deck's
EMU_MID_WIN = ( 66.0, 104.0 )               # the mid-level ends'
# The cab: ( z, the face's depth behind the coupler face on the centre line, its corners' radius in plan ). The face
# is near upright to the windscreen's foot (z 100), the windscreen leans back 21 degrees to its top (152) under a black
# visor (to 166) carrying the destination display, and the roof rounds down to it.
EMU_FACE = [ ( 19.0, 20.0, 20.0 ), ( 24.0, 19.0, 20.0 ), ( 30.0, 18.0, 20.0 ), ( 52.0, 17.5, 21.0 ),
             ( 62.0, 17.6, 21.0 ), ( 78.0, 18.5, 22.0 ), ( 90.0, 20.0, 22.0 ), ( 97.0, 21.3, 22.0 ),
             ( 100.0, 22.0, 22.0 ), ( 112.0, 26.5, 23.0 ), ( 126.0, 32.0, 24.0 ), ( 140.0, 37.5, 25.0 ),
             ( 152.0, 42.5, 26.0 ), ( 158.0, 45.5, 27.0 ), ( 166.0, 51.0, 28.0 ), ( 172.0, 57.0, 28.0 ),
             ( 177.0, 66.0, 28.0 ), ( 180.5, 78.0, 28.0 ), ( EMU_ROOF, 100.0, 0.0 ) ]
EMU_FACE_X = ( 0.0, 9.5, 13.0, 22.0, 31.0 )  # stations across the flat of the face (grilles, coupler pocket, display)
EMU_ARC_STEPS = 6
EMU_SCREEN = ( 100.0, 152.0 )               # the windscreen's foot and top
EMU_VISOR = 166.0
EMU_BULGE = 3.0             # the face bows forward this much at its middle, in plan
EMU_SCREEN_WRAP = 5                         # the windscreen wraps this many arc steps (of 15 degrees) round the corners


def _emu_width( z ):
    """ The body's half width at height z. """
    if z <= EMU_SIDE_TOP:
        return EMU_W
    zs = [ p[1] for p in EMU_UPPER ]
    return float( np.interp( z, zs, [ p[0] for p in EMU_UPPER ] ) )


def _emu_face_at( z ):
    """ ( depth, corner radius ) of the cab's face at height z. """
    zs = [ r[0] for r in EMU_FACE ]
    f = float( np.interp( z, zs, [ r[1] for r in EMU_FACE ] ) )
    rc = float( np.interp( z, zs, [ r[2] for r in EMU_FACE ] ) )
    return f, max( 0.0, min( rc, _emu_width( z ) - 1e-3, EMU_NOSE - 2.0 - f - EMU_BULGE ) )


def _emu_surface( x, z ):
    """ The cab's surface at ( |x|, z ): its depth and its outward normal in plan, ( nx, nd ) with nd < 0 forward. """
    W = _emu_width( z )
    f, rc = _emu_face_at( z )
    flat = W - rc
    x = abs( x )
    if x <= flat or rc <= 0.0:
        slope = 2.0 * EMU_BULGE * x / ( flat * flat ) if flat > 1e-6 else 0.0
        k = math.hypot( slope, 1.0 )
        return f + _emu_bow( x, flat ), ( slope / k, -1.0 / k )
    s = min( ( x - flat ) / rc, 1.0 )
    c = math.sqrt( max( 0.0, 1.0 - s * s ) )
    return f + EMU_BULGE + rc * ( 1.0 - c ), ( s, -c )


def _emu_bow( x, flat ):
    """ How far back the face is at x, behind its middle: a parabola reaching EMU_BULGE where its corners start. """
    return EMU_BULGE * ( min( x, flat ) / flat ) ** 2 if flat > 1e-6 else EMU_BULGE


class _Car:
    """ One car's own depths d, from its cab's coupler face (or its front gangway) back, in a vehicle frame: s +1 if
    the car's front faces the frame's +y, -1 if it faces back; a0, the frame depth of its d = 0. """

    def __init__( self, model, F, a0, s ):
        self.model, self.F, self.a0, self.s = model, F, a0, s

    def a( self, d ):
        return self.a0 + self.s * d

    def p( self, x, d, z ):
        return self.F.p( x, -self.a( d ), z )

    def local( self, v ):
        """ A direction ( x, along d, z ) as the frame's ( x, y, z ). """
        return ( v[0], -self.s * v[1], v[2] )

    def poly( self, paint, pts, towards, normals=None ):
        _fpoly( self.model, self.F, paint, [ ( x, -self.a( d ), z ) for x, d, z in pts ], self.local( towards ),
                normals=None if normals is None else [ self.local( n ) for n in normals ] )

    def span( self, d0, d1 ):
        """ The frame depths of d0..d1, low first. """
        return tuple( sorted( ( self.a( d0 ), self.a( d1 ) ) ) )

    def box( self, x0, x1, d0, d1, z0, z1, paints, skip=() ):
        a0, a1 = self.span( d0, d1 )
        self.F.box( self.model, x0, x1, -a0, -a1, z0, z1, paints, skip=skip )

    def collide( self, x0, x1, d0, d1, z0, z1, surface="metal" ):
        a0, a1 = self.span( d0, d1 )
        self.F.collide( self.model, x0, x1, -a0, -a1, z0, z1, surface )

    def rod( self, p, q, r, paint, sides=6, caps=( False, False ) ):
        rod( self.model, self.p( *p ), self.p( *q ), r, paint, sides, caps=caps )

    def disc( self, paint, c, normal, r, sides=12 ):
        disc( self.model, paint, self.p( *c ), self.F.x * normal[0] - self.F.y * self.s * normal[1]
              + self.F.z * normal[2], r, sides=sides )


def _chamfered( d0, d1, z0, z1, c ):
    """ A rectangle's outline in ( d, z ) with its corners cut back c, for windows' rounded corners. """
    return [ ( d0 + c, z0 ), ( d1 - c, z0 ), ( d1, z0 + c ), ( d1, z1 - c ), ( d1 - c, z1 ), ( d0 + c, z1 ),
             ( d0, z1 - c ), ( d0, z0 + c ) ]


def _emu_window( car, xs, d0, d1, z0, z1, frame=1.4 ):
    """ A tinted window in a black rubber frame, on the side at xs, d0..d1 along the car, z0..z1. """
    x = xs * EMU_W
    car.poly( "rw_black", [ ( x + xs * 0.08, d, z ) for d, z in _chamfered( d0 - frame, d1 + frame, z0 - frame,
                                                                             z1 + frame, 4.0 ) ], ( xs, 0, 0 ) )
    car.poly( "rw_window_dark", [ ( x + xs * 0.16, d, z ) for d, z in _chamfered( d0, d1, z0, z1, 3.2 ) ],
              ( xs, 0, 0 ) )


def _emu_ring( car, paint, xs, d, z, r0, r1, sides=14 ):
    """ A flat ring on the side at xs, centred on ( d, z ): the bicycle pictogram's wheels. """
    x = xs * ( EMU_W + 0.12 )
    for k in range( sides ):
        t0, t1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        car.poly( paint, [ ( x, d + r0 * math.cos( t0 ), z + r0 * math.sin( t0 ) ),
                           ( x, d + r1 * math.cos( t0 ), z + r1 * math.sin( t0 ) ),
                           ( x, d + r1 * math.cos( t1 ), z + r1 * math.sin( t1 ) ),
                           ( x, d + r0 * math.cos( t1 ), z + r0 * math.sin( t1 ) ) ], ( xs, 0, 0 ) )


def _emu_stroke( car, paint, xs, p, q, w ):
    """ A flat stroke w wide on the side at xs from p to q, each ( d, z ). """
    x = xs * ( EMU_W + 0.12 )
    dd, dz = q[0] - p[0], q[1] - p[1]
    length = math.hypot( dd, dz ) or 1.0
    nd, nz = -dz / length * w / 2, dd / length * w / 2
    car.poly( paint, [ ( x, p[0] + nd, p[1] + nz ), ( x, q[0] + nd, q[1] + nz ), ( x, q[0] - nd, q[1] - nz ),
                       ( x, p[0] - nd, p[1] - nz ) ], ( xs, 0, 0 ) )


def _emu_bicycle( car, xs, d, z ):
    """ The white bicycle pictogram beside a door, 16 long, centred on ( d, z ); it reads forwards on either side. """
    sd = -xs * car.s              # +1 when the car's d runs to the viewer's right
    k = lambda u, v: ( d + sd * u, z + v )
    for u in ( -4.6, 4.6 ):
        _emu_ring( car, "rw_white_paint", xs, d + sd * u, z - 1.6, 2.6, 3.4 )
    for p, q in ( ( ( -4.6, -1.6 ), ( -1.0, 2.6 ) ), ( ( -1.0, 2.6 ), ( 3.2, 2.6 ) ), ( ( 3.2, 2.6 ), ( 4.6, -1.6 ) ),
                  ( ( -4.6, -1.6 ), ( 0.2, -1.6 ) ), ( ( 0.2, -1.6 ), ( 3.2, 2.6 ) ), ( ( -1.6, 3.8 ), ( 0.2, -1.6 ) ),
                  ( ( 2.6, 4.2 ), ( 3.4, 2.4 ) ) ):
        _emu_stroke( car, "rw_white_paint", xs, k( *p ), k( *q ), 0.9 )
    _emu_stroke( car, "rw_white_paint", xs, k( -2.8, 3.8 ), k( -0.4, 3.8 ), 1.0 )
    _emu_stroke( car, "rw_white_paint", xs, k( 2.0, 4.4 ), k( 4.0, 4.4 ), 0.9 )


# A 5 x 8 dot-matrix font for the destination displays: rows top to bottom, the last for descenders.
EMU_FONT = {
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#|.....", "E": "#####|#....|#....|####.|#....|#....|#####|.....",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#|.....", "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#|.....",
    "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#|.....", "S": ".####|#....|#....|.###.|....#|....#|####.|.....",
    "ü": ".#.#.|.....|#...#|#...#|#...#|#..##|.##.#|.....", "n": ".....|.....|#.##.|##..#|#...#|#...#|#...#|.....",
    "c": ".....|.....|.###.|#....|#....|#...#|.###.|.....", "h": "#....|#....|#.##.|##..#|#...#|#...#|#...#|.....",
    "e": ".....|.....|.###.|#...#|#####|#....|.###.|.....", "b": "#....|#....|#.##.|##..#|#...#|#...#|####.|.....",
    "f": "..##.|.#..#|.#...|###..|.#...|.#...|.#...|.....", "r": ".....|.....|#.##.|##..#|#....|#....|#....|.....",
    "g": ".....|.....|.####|#...#|#...#|.####|....#|.###.", "u": ".....|.....|#...#|#...#|#...#|#..##|.##.#|.....",
    "d": "....#|....#|.##.#|#..##|#...#|#...#|.####|.....", "t": ".#...|.#...|###..|.#...|.#...|.#..#|..##.|.....",
    "a": ".....|.....|.###.|....#|.####|#...#|.####|.....", "l": ".##..|..#..|..#..|..#..|..#..|..#..|.###.|.....",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.|.....", "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.|.....",
    " ": ".....|.....|.....|.....|.....|.....|.....|.....",
}


def _emu_display( car, text, z_mid, pitch=0.62 ):
    """ The destination in amber LEDs on the visor, centred on the cab's centre line at z_mid, each dot laid on the
    leaning face. """
    cols = 6 * len( text ) - 1
    x0 = -cols * pitch / 2
    sd = car.s                    # +1 when x runs to the viewer's right, facing the cab
    dot = pitch * 0.38
    for i, ch in enumerate( text ):
        rows = EMU_FONT.get( ch, EMU_FONT[" "] ).split( "|" )
        for r, row in enumerate( rows ):
            for c, on in enumerate( row ):
                if on != "#":
                    continue
                x = sd * ( x0 + ( 6 * i + c + 0.5 ) * pitch )
                z = z_mid + ( 3.5 - r ) * pitch
                f, _ = _emu_surface( x, z )
                f2, _ = _emu_surface( x, z + 1.0 )
                lean = ( f2 - f )             # how far the face goes back per unit up
                pts = []
                for dx, dz in ( ( -dot, -dot ), ( dot, -dot ), ( dot, dot ), ( -dot, dot ) ):
                    pts.append( ( x + dx, f - 0.12 + lean * dz, z + dz ) )
                car.poly( "rw_lamp_warm", pts, ( 0, -1, lean ) )


def _emu_cab( car, body, destination ):
    """ The cab: the nose lofted from slices of the face (EMU_FACE), smooth shaded, with its windscreen, visor and
    display, headlight clusters, grilles, coupler and obstacle deflector. """
    zs = sorted( { r[0] for r in EMU_FACE } )
    grid = []
    for z in zs:
        W = _emu_width( z )
        f, rc = _emu_face_at( z )
        flat = W - rc
        row = [ ( min( x, flat ), f + _emu_bow( x, flat ), z ) for x in EMU_FACE_X ]
        row += [ ( flat + rc * math.sin( t ), f + EMU_BULGE + rc * ( 1.0 - math.cos( t ) ), z )
                 for t in [ math.pi / 2 * k / EMU_ARC_STEPS for k in range( 0, EMU_ARC_STEPS + 1 ) ] ]
        row.append( ( W, EMU_NOSE, z ) )
        grid.append( row )
    n_face = len( EMU_FACE_X )

    def normal_at( k, i ):
        g = grid
        ka, kb = max( k - 1, 0 ), min( k + 1, len( g ) - 1 )
        ia, ib = max( i - 1, 0 ), min( i + 1, len( g[k] ) - 1 )
        tu = np.subtract( g[k][ib], g[k][ia] )
        tv = np.subtract( g[kb][i], g[ka][i] )
        if np.linalg.norm( tu ) < 1e-6:            # a degenerate row (the crown): go round the next row down
            tu = np.subtract( g[ka][ib], g[ka][ia] )
        n = np.cross( tu, tv )                      # outward: forward on the face, out on the sides
        length = np.linalg.norm( n )
        if length < 1e-9:
            return ( 0.0, -1.0, 0.0 )
        n = n / length
        return ( float( n[0] ), float( n[1] ), float( n[2] ) )

    normals = [ [ normal_at( k, i ) for i in range( len( grid[k] ) ) ] for k in range( len( grid ) ) ]

    def paint_of( k, i ):
        z = ( zs[k] + zs[k + 1] ) / 2
        front = i < n_face - 1 + EMU_SCREEN_WRAP
        if z > EMU_VISOR or ( z > EMU_ROOF_LINE and i >= n_face - 1 ):
            return "rw_train_grey" if z > EMU_ROOF_LINE else body
        if front and EMU_SCREEN[1] < z <= EMU_VISOR:
            return "rw_black"
        if front and EMU_SCREEN[0] < z <= EMU_SCREEN[1]:
            return "rw_window_dark"
        if front and 97.0 < z <= EMU_SCREEN[0]:
            return "rw_black"
        if EMU_STRIPE[0] <= z <= EMU_STRIPE[1]:
            return "rw_train_white"
        return body

    for k in range( len( grid ) - 1 ):
        for i in range( len( grid[k] ) - 1 ):
            paint = paint_of( k, i )
            for xs in ( 1.0, -1.0 ):
                quad = [ ( k, i ), ( k, i + 1 ), ( k + 1, i + 1 ), ( k + 1, i ) ]
                pts = [ ( xs * grid[a][b][0], grid[a][b][1], grid[a][b][2] ) for a, b in quad ]
                ns = [ ( xs * normals[a][b][0], normals[a][b][1], normals[a][b][2] ) for a, b in quad ]
                if np.linalg.norm( np.subtract( pts[0], pts[1] ) ) < 1e-6 and \
                        np.linalg.norm( np.subtract( pts[2], pts[3] ) ) < 1e-6:
                    continue
                mid = np.mean( [ np.array( n ) for n in ns ], axis=0 )
                car.poly( paint, pts, tuple( mid ), normals=ns )
    bottom = grid[0]
    outline = [ ( x, d, zs[0] ) for x, d, _ in bottom ] + [ ( -x, d, zs[0] ) for x, d, _ in reversed( bottom ) ]
    car.poly( "rw_bogie", [ p for j, p in enumerate( outline ) if j == 0 or
                            np.linalg.norm( np.subtract( p, outline[j - 1] ) ) > 1e-6 ], ( 0, 0, -1 ) )

    def on_face( x, z, off ):
        f, ( nx, nd ) = _emu_surface( x, z )
        return ( x + ( nx if x >= 0 else -nx ) * off, f + nd * off, z )

    def patch( paint, x0, x1, z0, z1, off=0.12, step=2.5 ):
        """ A panel laid on the face from x0 to x1 (either sign), z0 to z1, in strips that follow its curve. """
        n = max( 1, int( math.ceil( abs( x1 - x0 ) / step ) ) )
        xs_ = [ x0 + ( x1 - x0 ) * j / n for j in range( n + 1 ) ]
        zs_ = sorted( { z0, z1, *[ r[0] for r in EMU_FACE if z0 < r[0] < z1 ] } )
        for za, zb in zip( zs_, zs_[1:] ):
            for xa, xb in zip( xs_, xs_[1:] ):
                xm = ( xa + xb ) / 2
                _, ( nx, nd ) = _emu_surface( xm, ( za + zb ) / 2 )
                car.poly( paint, [ on_face( xa, za, off ), on_face( xb, za, off ), on_face( xb, zb, off ),
                                   on_face( xa, zb, off ) ], ( nx if xm >= 0 else -nx, nd, 0 ) )

    # The windscreen's wiper, the top headlight behind the glass's head and the destination display.
    car.rod( on_face( 3.0, 101.5, 0.5 ), on_face( -25.0, 131.0, 0.5 ), 0.45, "rw_black", 4 )
    car.rod( on_face( 3.0, 101.5, 0.3 ), on_face( 3.0, 100.0, 1.6 ), 1.0, "rw_black", 6, caps=( True, True ) )
    f, _ = _emu_surface( 0.0, 147.5 )
    car.disc( "rw_lamp_cool", ( 0.0, f - 0.2, 147.5 ), ( 0, -1, 0.35 ), 2.0, 12 )
    _emu_display( car, destination, 159.0 )
    # Headlight clusters: a black housing round the corner with two LED headlights and a red tail light in each.
    for xs in ( 1.0, -1.0 ):
        patch( "rw_black", xs * 24.0, xs * 49.0, 77.5, 91.5, 0.15 )
        for x, r, paint in ( ( 29.5, 3.8, "rw_lamp_cool" ), ( 38.5, 3.5, "rw_lamp_cool" ),
                             ( 46.5, 1.8, "rw_signal_red" ) ):
            _, ( nx, nd ) = _emu_surface( x, 84.5 )
            car.disc( "rw_steel_grey", on_face( xs * x, 84.5, 0.3 ), ( xs * nx, nd, 0 ), r + 0.7, 14 )
            car.disc( paint, on_face( xs * x, 84.5, 0.45 ), ( xs * nx, nd, 0 ), r, 14 )
    # Grilles either side of the coupler pocket, the pocket and the automatic coupler in it.
    for xs in ( 1.0, -1.0 ):
        patch( "rw_black", xs * 13.0, xs * 31.0, 31.0, 51.0 )
        for z in ( 34.0, 38.0, 42.0, 46.0, 49.0 ):
            car.rod( on_face( xs * 14.0, z, 0.7 ), on_face( xs * 30.0, z, 0.7 ), 0.6, "rw_steel_dark", 4 )
    patch( "rw_black", -9.5, 9.5, 22.0, 52.0 )
    f, _ = _emu_surface( 0.0, 38.0 )
    car.box( -6.5, 6.5, 1.0, 7.0, 32.0, 44.0, "rw_steel_dark" )
    car.box( -4.5, 4.5, 0.0, 1.0, 34.0, 42.0, "rw_steel_grey" )
    car.box( -1.6, 1.6, -0.2, 0.0, 36.5, 39.5, "rw_black" )
    car.rod( ( 0.0, 7.0, 38.0 ), ( 0.0, f, 38.0 ), 2.6, "rw_bogie", 8 )
    # The obstacle deflector under the nose, raked back, and the cab's underframe behind it.
    car.poly( "rw_train_dark", [ ( -44.0, 18.0, 19.0 ), ( 44.0, 18.0, 19.0 ), ( 40.0, 13.0, 5.0 ),
                                 ( -40.0, 13.0, 5.0 ) ], ( 0, -1, 0.3 ) )
    car.poly( "rw_train_dark", [ ( -40.0, 13.0, 5.0 ), ( 40.0, 13.0, 5.0 ), ( 40.0, 30.0, 5.0 ),
                                 ( -40.0, 30.0, 5.0 ) ], ( 0, 0, -1 ) )
    for xs in ( 1.0, -1.0 ):
        car.poly( "rw_train_dark", [ ( xs * 44.0, 18.0, 19.0 ), ( xs * 40.0, 13.0, 5.0 ), ( xs * 40.0, 30.0, 5.0 ),
                                     ( xs * 44.0, 30.0, 19.0 ) ], ( xs, 0, 0 ) )
    car.box( -44.0, 44.0, 30.0, EMU_NOSE, 10.0, 19.0, "rw_bogie", skip=( "top", ) )


def _emu_car( car, body, platform_xs, doors_open, cab, destination, roof="ac" ):
    """ One car: its cab (cab True) or its front end at the gangway, two bogies, the mid-level ends, the doors and
    the two decks, windows, roof and collision. platform_xs: the frame x sign of the side whose doors stand open.
    roof: "ac" for an air-conditioning unit over the inner end, else nothing (the pantograph goes there). """
    F, model = car.F, car.model
    start = EMU_NOSE if cab else 0.0
    end = EMU_CAR
    zones = [ ( c - EMU_WHEELBASE / 2 - 13.0, c + EMU_WHEELBASE / 2 + 13.0 ) for c in EMU_BOGIES ]
    doors = [ ( d, d + 51.0 ) for d in EMU_DOORS ]
    for c in EMU_BOGIES:
        _bogie( model, F, car.a( c ), EMU_WHEELBASE, EMU_WHEEL, cab and c == EMU_BOGIES[0] )
    if cab:
        _emu_cab( car, body, destination )

    def bottom_at( d ):
        if any( z0 <= d <= z1 for z0, z1 in zones ):
            return EMU_CUT
        if EMU_DECKS[0] <= d <= EMU_DECKS[1]:
            return EMU_LOW
        return EMU_SKIRT

    cuts = sorted( { start, end, *[ v for z in zones + doors for v in z if start < v < end ] } )
    pieces = [ ( c0, c1, bottom_at( ( c0 + c1 ) / 2 ) ) for c0, c1 in zip( cuts, cuts[1:] ) ]
    bands = lambda zb: [ ( z0, z1, p ) for z0, z1, p in ( ( EMU_LOW, EMU_STRIPE[0], "rw_train_dark" ),
                                                          ( EMU_STRIPE[0], EMU_STRIPE[1], "rw_train_white" ),
                                                          ( EMU_STRIPE[1], EMU_SIDE_TOP, body ) )
                         if z1 > zb ]
    for xs in ( 1.0, -1.0 ):
        open_side = doors_open and xs == platform_xs
        for d0, d1, zb in pieces:
            gaps = [ ( d0 - 1, d1 + 1, EMU_FLOOR, 108.0 ) for g0, g1 in doors if g0 <= ( d0 + d1 ) / 2 <= g1 ]
            a0, a1 = car.span( d0, d1 )
            _banded_side( model, F, xs, EMU_W, a0, a1, [ ( max( z0, zb ), z1, p ) for z0, z1, p in bands( zb ) ],
                          [ ( a0 - 1, a1 + 1, z0, z1 ) for _, _, z0, z1 in gaps ] )
        for d0, d1 in doors:
            a0, a1 = car.span( d0, d1 )
            if open_side:
                _emu_vestibule( model, F, xs, a0, a1 )
            else:
                _emu_door( model, F, xs, a0, a1 )
        # Windows: the lower and upper decks' between the doors, the mid-level ends' over the bogies.
        for w0, w1 in ( ( 324.0, 384.0 ), ( 392.0, 452.0 ), ( 460.0, 520.0 ) ):
            _emu_window( car, xs, w0, w1, *EMU_LOWER_WIN )
            _emu_window( car, xs, w0, w1, *EMU_UPPER_WIN )
        for w0, w1 in ( ( 630.0, 690.0 ), ( 698.0, 752.0 ) ) + ( ( ( 124.0, 194.0 ), ) if cab else
                                                                   ( ( 20.0, 80.0 ), ( 88.0, 194.0 ) ) ):
            _emu_window( car, xs, w0, w1, *EMU_MID_WIN )
        if cab:      # the cab's side window, its front edge leaning with the windscreen
            car.poly( "rw_black", [ ( xs * ( EMU_W + 0.08 ), d, z ) for d, z in
                                    ( ( 62.0, 104.6 ), ( 106.4, 104.6 ), ( 106.4, 145.4 ), ( 80.0, 145.4 ) ) ],
                      ( xs, 0, 0 ) )
            car.poly( "rw_window_dark", [ ( xs * ( EMU_W + 0.16 ), d, z ) for d, z in
                                          ( ( 65.0, 106.0 ), ( 105.0, 106.0 ), ( 105.0, 144.0 ), ( 82.0, 144.0 ) ) ],
                      ( xs, 0, 0 ) )
        _emu_bicycle( car, xs, 208.0, 84.0 )
    # The roof and the side walls' curve into it, the underside and its steps, the inner end.
    a0, a1 = car.span( start, end )
    _extrude( model, F, EMU_UPPER, a0, a1, lambda k: body if EMU_UPPER[k][1] < EMU_ROOF_LINE else "rw_train_grey",
              smooth_from=0 )
    for d0, d1, zb in pieces:
        car.poly( "rw_bogie", [ ( EMU_W, d0, zb ), ( -EMU_W, d0, zb ), ( -EMU_W, d1, zb ), ( EMU_W, d1, zb ) ],
                  ( 0, 0, -1 ) )
    for ( _, d, za ), ( _, _, zb ) in zip( pieces, pieces[1:] ):
        if abs( za - zb ) > 1e-6:
            car.poly( "rw_bogie", [ ( EMU_W, d, za ), ( -EMU_W, d, za ), ( -EMU_W, d, zb ), ( EMU_W, d, zb ) ],
                      ( 0, 1 if za < zb else -1, 0 ) )
    prof = [ ( EMU_W, EMU_SKIRT ) ] + EMU_UPPER
    _section( model, F, prof, car.a( end ), -car.s, body )
    if not cab:
        _section( model, F, prof, car.a( 0.0 ), car.s, body )
    # Air conditioning on the roof over the inner end.
    if roof == "ac":
        car.box( -24.0, 24.0, 640.0, 735.0, EMU_ROOF - 2.0, EMU_ROOF + 7.0, "rw_train_grey", skip=( "bottom", ) )
        for g in range( 6 ):
            car.box( -20.0, 20.0, 648.0 + 14.0 * g, 652.0 + 14.0 * g, EMU_ROOF + 7.0, EMU_ROOF + 7.6, "rw_steel_dark",
                     skip=( "bottom", ) )
    # Collision: the cab stepped back with its windscreen, the body solid, hollowed at the open vestibules.
    W, top = EMU_W, EMU_ROOF
    if cab:
        for d0, z0, z1, half in ( ( 18.0, -7.0, 98.0, W - 4.0 ), ( 30.0, 98.0, 140.0, W - 5.0 ),
                                  ( 44.0, 140.0, 172.0, W - 12.0 ), ( 64.0, 172.0, top, W - 20.0 ) ):
            car.collide( -half, half, d0, start, z0, z1 )
    lo, hi = start, end
    open_doors = doors if doors_open else []
    if not open_doors:
        car.collide( -W, W, lo, hi, -7.0, top )
        return
    car.collide( 0.0, -platform_xs * W, lo, hi, -7.0, top )
    edges = [ lo ] + [ v for d in open_doors for v in d ] + [ hi ]
    for k in range( len( edges ) - 1 ):
        p0, p1 = edges[k], edges[k + 1]
        if k % 2 == 0:
            car.collide( 0.0, platform_xs * W, p0, p1, -7.0, top )
        else:
            car.collide( 0.0, platform_xs * W, p0, p1, -7.0, EMU_FLOOR )
            car.collide( 0.0, platform_xs * W, p0, p1, 108.0, top )


def emu( model, e, n_front, facing, rail_z=-30.0, cars=2, body="rw_train_blue", platform_side=-1, doors_open=True,
         wire_z=None, destinations=( "RE München", "RE München" ) ):
    """ A two-car double-deck EMU (39.1 m over the couplers), a cab at each end, two pairs of 1.3 m sliding plug
    doors a side per car. Livery: body paint with a light grey stripe low down, black window frames and visors, a
    grey roof. platform_side (+1 east, -1 west): the side whose doors stand open (doors_open), each into a 1.4 m deep
    vestibule floored level with the platform (rail_z + 30) under a 2 m ceiling; the other side's stay shut.
    wire_z: the contact wire's z, to raise the pantograph on to it; None leaves it down. destinations: the front and
    rear cabs' displays (the letters in EMU_FONT). Metal collision per car, hollowed at the open vestibules, and across
    the gangway. cars must be 2. Returns the far coupler's n. """
    if cars != 2:
        raise ValueError( "the double-deck EMU is a two-car unit" )
    F = vehicle_frame( e, n_front, facing, rail_z )
    xs_open = platform_side * F.x[0]
    total = 2 * EMU_CAR + EMU_GAP
    front = _Car( model, F, 0.0, 1 )
    rear = _Car( model, F, total, -1 )
    _emu_car( front, body, xs_open, doors_open, True, destinations[0] )
    _emu_car( rear, body, xs_open, doors_open, True, destinations[1], roof="pantograph" )
    F.box( model, -40, 40, -EMU_CAR, -( EMU_CAR + EMU_GAP ), 30.0, 168.0, "rw_rubber", skip=( "bottom", ) )
    F.collide( model, -40, 40, -EMU_CAR, -( EMU_CAR + EMU_GAP ), -7.0, 168.0, "metal" )
    _pantograph( model, F, total - 690.0, EMU_ROOF - 1.5, None if wire_z is None else wire_z - rail_z )
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


def _suitcase( model, F, x0, x1, y0, y1, z0, h, paint, trim=DARK, upright=False ):
    """ A hard suitcase on the deck: its shell inset 0.5 round a lid seam, two straps round it, corner guards and a
    carry handle on its top (lying flat) or its end face (stood upright, on the +y end). """
    F.box( model, x0, x1, y0, y1, z0, z0 + h, paint, skip=( "bottom", ) )
    seam = z0 + h * 0.55 if not upright else None
    if seam is not None:
        F.box( model, x0 - 0.25, x1 + 0.25, y0 - 0.25, y1 + 0.25, seam - 0.35, seam + 0.35, trim, skip=( "bottom", ) )
    else:
        xm = ( x0 + x1 ) / 2
        F.box( model, xm - 0.35, xm + 0.35, y0 - 0.25, y1 + 0.25, z0, z0 + h + 0.25, trim, skip=( "bottom", ) )
    long_x = ( x1 - x0 ) >= ( y1 - y0 )
    for f in ( 0.25, 0.75 ):
        if long_x:
            x = x0 + ( x1 - x0 ) * f
            F.box( model, x - 0.8, x + 0.8, y0 - 0.3, y1 + 0.3, z0, z0 + h + 0.3, "rw_black", skip=( "bottom", ) )
        else:
            y = y0 + ( y1 - y0 ) * f
            F.box( model, x0 - 0.3, x1 + 0.3, y - 0.8, y + 0.8, z0, z0 + h + 0.3, "rw_black", skip=( "bottom", ) )
    for cx in ( x0, x1 ):
        for cy in ( y0, y1 ):
            F.box( model, cx - 0.9, cx + 0.9, cy - 0.9, cy + 0.9, z0, z0 + 1.6, "rw_steel_grey", skip=( "bottom", ) )
    if upright:
        xm, zt = ( x0 + x1 ) / 2, z0 + h
        for dx in ( -2.4, 2.4 ):
            rod( model, F.p( xm + dx, ( y0 + y1 ) / 2, zt ), F.p( xm + dx, ( y0 + y1 ) / 2, zt + 1.6 ), 0.4, "rw_black",
                 6 )
        rod( model, F.p( xm - 2.6, ( y0 + y1 ) / 2, zt + 1.6 ), F.p( xm + 2.6, ( y0 + y1 ) / 2, zt + 1.6 ), 0.55,
             "rw_black", 8, caps=( True, True ) )
    else:
        zt, ym = z0 + h, ( y0 + y1 ) / 2
        xm = ( x0 + x1 ) / 2
        a0, a1 = F.p( xm - 2.6, ym, zt + 1.4 ), F.p( xm + 2.6, ym, zt + 1.4 )
        for q in ( a0, a1 ):
            rod( model, q - np.array( ( 0, 0, 1.4 ) ), q, 0.4, "rw_black", 6 )
        rod( model, a0, a1, 0.55, "rw_black", 8, caps=( True, True ) )


def _crate( model, F, x0, x1, y0, y1, z0, z1 ):
    """ A slatted wooden crate: its boards, with battens proud of each side at the corners and across the middle. """
    model.grain_paints.add( "rw_wood" )
    F.box( model, x0 + 0.6, x1 - 0.6, y0 + 0.6, y1 - 0.6, z0, z1 - 0.6, "rw_wood", skip=( "bottom", ) )
    F.box( model, x0 + 0.6, x1 - 0.6, y0 + 0.6, y1 - 0.6, z1 - 0.6, z1, "rw_wood", skip=( "bottom", ) )
    b = 1.6
    for cx in ( x0, x1 - b ):
        for cy in ( y0, y1 - b ):
            F.box( model, cx, cx + b, cy, cy + b, z0, z1, "rw_wood", skip=( "bottom", ) )
    for z in ( z0 + 0.4, z1 - 2.0, ( z0 + z1 ) / 2 - 0.8 ):
        F.box( model, x0, x1, y0, y0 + 0.6, z, z + 1.6, "rw_wood" )
        F.box( model, x0, x1, y1 - 0.6, y1, z, z + 1.6, "rw_wood" )
        F.box( model, x0, x0 + 0.6, y0, y1, z, z + 1.6, "rw_wood" )
        F.box( model, x1 - 0.6, x1, y0, y1, z, z + 1.6, "rw_wood" )
    # Board gaps: dark lines between the slats on the long faces.
    for k in range( 1, 4 ):
        z = z0 + ( z1 - z0 ) * k / 4
        F.box( model, x0 + 0.5, x1 - 0.5, y0 + 0.5, y1 - 0.5, z - 0.15, z + 0.15, "rw_black", skip=( "top", "bottom" ) )


def luggage_cart( model, e, n, along="n", z0=0.0, loaded=True ):
    """ An old platform luggage cart (2.5 x 1.2 m): a deck of planks 600 mm up on a grey-green steel frame, four
    400 mm wheels with solid rubber tyres on pressed-steel rims, the front pair on a turntable with the drawbar's fork
    and towing eye lying forward on the ground, tubular gates 1 m high at both ends with corner gussets, and (loaded)
    two slatted crates, three strapped suitcases and a kit bag on it to about 1.15 m. along: "n", "-n", "e" or "-e",
    the way the drawbar points. One wooden box to the gates' height. """
    sign = -1.0 if along.startswith( "-" ) else 1.0
    F = Frame( ( e, n, z0 ), ( 0, sign ) if along.endswith( "n" ) else ( sign, 0 ) )
    hl, hw, deck = 49.2, 23.6, 23.6
    model.grain_paints.add( "rw_wood" )
    # The deck: eight planks along the cart with narrow gaps over a dark bed.
    F.box( model, -hw + 1.0, hw - 1.0, -hl + 1.0, hl - 1.0, deck - 1.6, deck - 1.4, DARK, skip=( "bottom", ) )
    planks = 8
    pw = 2 * hw / planks
    for k in range( planks ):
        x0 = -hw + k * pw + ( 0.15 if k else 0.0 )
        x1 = -hw + ( k + 1 ) * pw - ( 0.15 if k < planks - 1 else 0.0 )
        F.box( model, x0, x1, -hl, hl, deck - 1.4, deck, "rw_wood" )
    for y in ( -hl + 4.0, hl - 4.0 ):
        for xs in ( 1.0, -1.0 ):
            disc( model, "rw_steel_dark", F.p( xs * ( hw - 6.0 ), y, deck + 0.02 ), F.z, 0.45, sides=6 )
    # The frame: channel side rails with a lip, cross members.
    for xs in ( 1.0, -1.0 ):
        F.box( model, xs * ( hw - 2.0 ), xs * hw, -hl, hl, deck - 5.4, deck - 1.4, "rw_steel", skip=( "top", ) )
        F.box( model, xs * ( hw - 3.2 ), xs * ( hw - 2.0 ), -hl, hl, deck - 5.4, deck - 4.6, "rw_steel", skip=( "top", ) )
    for y in ( -hl + 1.0, -hl / 2, 0.0, hl / 2, hl - 1.0 ):
        F.box( model, -hw + 2.0, hw - 2.0, y - 1.0, y + 1.0, deck - 5.4, deck - 1.4, "rw_steel", skip=( "top", ) )
    # Wheels: a 20-sided rubber tyre, a stepped steel rim, a hub boss and its axle nut.
    r = 7.9
    for y in ( -37.0, 33.0 ):
        rod( model, F.p( -16.0, y, r ), F.p( 16.0, y, r ), 0.9, DARK, 8 )
        for xs in ( 1.0, -1.0 ):
            rod( model, F.p( xs * 16.0, y, r ), F.p( xs * 19.1, y, r ), r, "rw_rubber", 20 )
            rod( model, F.p( xs * 16.0, y, r ), F.p( xs * 19.1, y, r ), r - 2.2, "rw_steel", 20 )
            disc( model, "rw_rubber", F.p( xs * 19.1, y, r ), xs * F.x, r, sides=20 )
            disc( model, "rw_rubber", F.p( xs * 16.0, y, r ), -xs * F.x, r, sides=20 )
            disc( model, "rw_steel", F.p( xs * 19.12, y, r ), xs * F.x, r - 2.3, sides=20 )
            rod( model, F.p( xs * 19.1, y, r ), F.p( xs * 19.9, y, r ), 2.6, "rw_steel", 16, caps=( False, True ) )
            rod( model, F.p( xs * 19.9, y, r ), F.p( xs * 20.6, y, r ), 1.0, "rw_steel_dark", 6, caps=( False, True ) )
            # The fork: two plates either side of the wheel down from the frame.
            for dx in ( 15.0, 13.4 ):
                F.box( model, xs * dx - 0.4, xs * dx + 0.4, y - 2.4, y + 2.4, r, deck - 5.4, "rw_steel",
                       skip=( "top", ) )
            F.box( model, xs * 15.0 - 0.4, xs * 20.0, y - 2.4, y + 2.4, r + 8.4, r + 9.2, "rw_steel" )
    # The turntable and the drawbar: a fork off the axle to a towing eye on the ground.
    rod( model, F.p( 0.0, 33.0, deck - 8.0 ), F.p( 0.0, 33.0, deck - 5.4 ), 9.0, DARK, 16, caps=( True, False ) )
    rod( model, F.p( 0.0, 33.0, deck - 8.6 ), F.p( 0.0, 33.0, deck - 8.0 ), 10.0, "rw_steel", 16,
         caps=( True, True ) )
    for xs in ( 1.0, -1.0 ):
        rod( model, F.p( xs * 8.0, 33.0, r ), F.p( xs * 1.2, 50.0, 4.6 ), 0.8, "rw_steel", 6, caps=( True, False ) )
    rod( model, F.p( 0.0, 50.0, 4.6 ), F.p( 0.0, 73.0, 1.6 ), 0.9, "rw_steel", 8 )
    rod( model, F.p( -1.6, 49.0, 4.7 ), F.p( 1.6, 49.0, 4.7 ), 1.2, "rw_steel", 8, caps=( True, True ) )
    eye = F.p( 0.0, 76.0, 1.4 )
    for k in range( 10 ):
        t0, t1 = 2 * math.pi * k / 10, 2 * math.pi * ( k + 1 ) / 10
        rod( model, eye + 2.6 * ( math.cos( t0 ) * F.x + math.sin( t0 ) * F.y ),
             eye + 2.6 * ( math.cos( t1 ) * F.x + math.sin( t1 ) * F.y ), 0.6, "rw_steel", 6 )
    # The gates: posts, two rails and a gusset at each corner.
    for y in ( -hl + 1.0, hl - 1.0 ):
        for xs in ( 1.0, -1.0 ):
            rod( model, F.p( xs * ( hw - 1.0 ), y, deck ), F.p( xs * ( hw - 1.0 ), y, 39.4 ), 0.85, "rw_steel", 8,
                 caps=( False, True ) )
            F.box( model, xs * ( hw - 4.0 ), xs * ( hw - 1.0 ), y - 0.15, y + 0.15, deck, deck + 3.0, "rw_steel" )
        for z in ( 31.5, 39.4 ):
            rod( model, F.p( -hw + 1.0, y, z ), F.p( hw - 1.0, y, z ), 0.85, "rw_steel", 8 )
        for x in ( -hw / 3, hw / 3 ):
            rod( model, F.p( x, y, deck ), F.p( x, y, 31.5 ), 0.5, "rw_steel", 6 )
    if loaded:
        _crate( model, F, -20.0, 2.0, -45.0, -19.0, deck, 40.5 )
        _suitcase( model, F, 3.0, 22.7, -46.0, -18.4, deck, 9.8, "rw_steel_grey" )
        _suitcase( model, F, 5.0, 20.7, -43.0, -21.3, deck + 9.8, 7.4, "rw_red_paint" )
        _suitcase( model, F, -14.0, 1.7, -10.0, -2.1, deck, 21.7, "rw_train_blue", upright=True )
        _crate( model, F, -7.0, 19.0, 4.0, 30.0, deck, deck + 15.7 )
        _suitcase( model, F, -19.0, -9.0, 8.0, 36.0, deck, 9.0, "rw_black", trim="rw_steel_dark" )
        # A canvas kit bag lying across the front of the deck, drawn tight at both ends.
        rod( model, F.p( -18.0, 40.0, deck + 3.9 ), F.p( 6.0, 41.0, deck + 3.9 ), 3.9, "rw_container_green", 12,
             caps=( True, True ), cap_paint="rw_rubber" )
        rod( model, F.p( -7.0, 40.5, deck + 8.2 ), F.p( -3.0, 40.6, deck + 8.2 ), 0.5, "rw_black", 6 )
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


# ---------------------------------------------------------------------------------------------------------------------
# A compact crossover SUV, as a modern one is: 4.47 m long, 1.81 m wide, 1.61 m tall, a 2.64 m wheelbase on 235/50 R19
# tyres. Its body is lofted through cross-sections (_suv_profile) along a, the depth behind its front bumper's face,
# shaded smooth within each part. No maker's name or badge: the grille is plain and the plates are the town's (HW).

SUV_L = 176.0
SUV_W = 35.6                # half its width over the body
SUV_AXLES = ( 37.0, 141.0 )
SUV_TYRE, SUV_TYRE_W, SUV_RIM = 14.1, 9.25, 9.5   # 235/50 R19
SUV_TRACK = 30.6            # the tyres' centre lines off the car's
SUV_ARCH = 15.6             # the arches' radius, with 3.0 of black flare round them
SUV_COWL, SUV_ROOF0, SUV_ROOF1, SUV_GLASS1 = 49.0, 79.0, 153.0, 164.0   # the windscreen's foot and top, the roof's
#                                                                         end and the rear window's foot
SUV_PLAN = [ ( 0.0, 30.6 ), ( 1.0, 32.2 ), ( 2.5, 33.6 ), ( 5.0, 34.7 ), ( 9.0, 35.3 ), ( 16.0, 35.6 ),
             ( 160.0, 35.6 ), ( 167.0, 35.2 ), ( 171.0, 34.5 ), ( 174.0, 33.3 ), ( 176.0, 31.2 ) ]
SUV_BOTTOM = [ ( 0.0, 12.5 ), ( 8.0, 10.2 ), ( 24.0, 8.8 ), ( 152.0, 8.8 ), ( 168.0, 10.5 ), ( 176.0, 13.0 ) ]
SUV_TOP = [ ( 0.0, 29.6 ), ( 0.8, 31.2 ), ( 1.8, 32.4 ), ( 3.2, 33.4 ), ( 6.0, 34.5 ), ( 10.0, 35.6 ), ( 30.0, 38.6 ),
            ( SUV_COWL, 40.5 ), ( SUV_ROOF0, 61.0 ), ( 98.0, 63.2 ), ( 122.0, 62.8 ), ( 142.0, 61.2 ),
            ( SUV_ROOF1, 59.6 ), ( SUV_GLASS1, 46.2 ), ( 172.0, 34.4 ), ( 174.0, 31.8 ), ( SUV_L, 30.6 ) ]
SUV_BELT = [ ( 0.0, 32.6 ), ( 10.0, 34.6 ), ( 48.0, 39.7 ), ( 52.0, 40.7 ), ( 100.0, 42.5 ), ( 145.0, 44.8 ),
             ( 153.0, 45.4 ) ]
SUV_STATIONS = [ 0.0, 0.4, 0.8, 1.3, 1.8, 2.5, 3.2, 4.2, 5.0, 6.0, 7.0, 9.0, 12.0, 16.0, 21.0, 30.0, 40.0, SUV_COWL, 50.5, 52.5, 56.0,
                 61.0, 66.0, 71.0, 75.0, SUV_ROOF0, 84.0, 90.0, 95.5, 99.5, 106.0, 113.0, 120.0, 127.0, 133.5,
                 137.0, 145.0, 149.0, 151.5, SUV_ROOF1, 155.0, 157.5, 160.0, 162.0, SUV_GLASS1, 166.0, 168.0, 170.0,
                 172.0, 173.2, 174.0, 175.0, 175.6, SUV_L ]
SUV_WINDOWS = ( ( 53.5, 95.5 ), ( 99.5, 133.5 ), ( 137.0, 151.0 ) )      # side glass along a: the doors' and the
#                                                                          rear quarter's; black pillars between
# A 5 x 7 plate font (rows top to bottom), narrow like the German plates' own.
PLATE_FONT = {
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#", "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.", "3": "####.|....#|....#|.###.|....#|....#|####.",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.", "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "L": "#....|#....|#....|#....|#....|#....|#####", "-": ".....|.....|.....|.###.|.....|.....|.....",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}


def _interp( table, a ):
    return float( np.interp( a, [ t[0] for t in table ], [ t[1] for t in table ] ) )


def _suv_profile( a ):
    """ The right half of the body's cross-section at depth a, bottom to the roof's (or bonnet's, or tailgate's)
    centre: the sill's tuck, the cladding's top, the widest line, the shoulder crease, the belt, then four points over
    the top. """
    W = _interp( SUV_PLAN, a )
    zb, zt = _interp( SUV_BOTTOM, a ), _interp( SUV_TOP, a )
    belt = min( _interp( SUV_BELT, a ), zt - 1.2 )
    sh = min( 36.6, belt - 1.5 )
    mx = min( 31.5, sh - 1.5 )
    lo = min( 17.0, mx - 1.0 )
    xb = W - 2.4
    side = [ ( W - 2.2, zb ), ( W - 0.5, lo ), ( W, mx ), ( W - 0.9, sh ), ( xb, belt ) ]

    def bonnet():               # across a bonnet or tailgate, from the fender line up to the centre
        d = zt - belt
        return [ ( xb - 3.2, belt + 0.5 * d ), ( xb - 6.5, belt + 0.78 * d ), ( min( 20.0, xb - 9.0 ), belt + 0.93 * d ),
                 ( 10.0, zt - 0.06 ), ( 0.0, zt ) ]

    def cabin():                # the window's top, its black frame's, the roof's side and its crown
        return [ ( 30.4, zt - 4.0 ), ( 29.7, zt - 3.0 ), ( 28.0, zt - 1.4 ), ( 16.0, zt - 0.3 ), ( 0.0, zt ) ]

    def blend( p, q, t ):
        t = t * t * ( 3 - 2 * t )
        return [ ( pa[0] + ( qa[0] - pa[0] ) * t, pa[1] + ( qa[1] - pa[1] ) * t ) for pa, qa in zip( p, q ) ]

    if a <= SUV_COWL:
        top = bonnet()
    elif a < SUV_ROOF0:
        top = blend( bonnet(), cabin(), ( a - SUV_COWL ) / ( SUV_ROOF0 - SUV_COWL ) )
    elif a <= SUV_ROOF1:
        top = cabin()
    elif a < SUV_GLASS1:
        top = blend( cabin(), bonnet(), ( a - SUV_ROOF1 ) / ( SUV_GLASS1 - SUV_ROOF1 ) )
    else:
        top = bonnet()
    return side + top


def _suv_side_x( a, z ):
    """ The body side's x at height z (up to the belt) at depth a. """
    prof = _suv_profile( a )[:5]
    if z <= prof[0][1]:
        return prof[0][0]
    for ( x0, z0 ), ( x1, z1 ) in zip( prof, prof[1:] ):
        if z0 <= z <= z1:
            return x0 + ( x1 - x0 ) * ( z - z0 ) / max( z1 - z0, 1e-6 )
    return prof[4][0]


def _suv_top_z( a, x ):
    """ The top surface's z at |x| (inside the belt) at depth a. """
    prof = _suv_profile( a )[4:]
    x = abs( x )
    for ( x0, z0 ), ( x1, z1 ) in zip( prof, prof[1:] ):
        if x1 <= x <= x0:
            return z0 + ( z1 - z0 ) * ( x0 - x ) / max( x0 - x1, 1e-6 )
    return prof[0][1]


class _Smooth:
    """ Polygons gathered with their part's name, then drawn with a normal per corner averaged over the faces that meet
    there in the same part, so each part shades smooth and the edges between parts stay crisp. Points are the
    vehicle frame's ( x, -a, z ). """

    def __init__( self ):
        self.faces = []
        self.acc = {}

    @staticmethod
    def key( p, part ):
        return ( round( p[0], 3 ), round( p[1], 3 ), round( p[2], 3 ), part )

    def add( self, paint, part, pts, hint ):
        pts = _clean( [ tuple( float( c ) for c in p ) for p in pts ] )
        if len( pts ) < 3:
            return
        n = np.zeros( 3 )
        for k in range( 1, len( pts ) - 1 ):
            n += np.cross( np.subtract( pts[k], pts[0] ), np.subtract( pts[k + 1], pts[0] ) )
        if np.linalg.norm( n ) < 1e-9:
            return
        if np.dot( n, hint ) < 0:
            n = -n
        self.faces.append( ( paint, part, pts, n ) )
        for p in pts:
            k = self.key( p, part )
            self.acc[k] = self.acc.get( k, np.zeros( 3 ) ) + n

    def draw( self, model, F ):
        for paint, part, pts, n in self.faces:
            normals = []
            for p in pts:
                v = self.acc[self.key( p, part )]
                length = np.linalg.norm( v )
                normals.append( tuple( v / length ) if length > 1e-9 else tuple( n / np.linalg.norm( n ) ) )
            _fpoly( model, F, paint, pts, tuple( n ), normals=normals )


def _road_body( model, F, profile, side_x, base_stations, axles, tyre, arch, inner_half, L, body_paint, paint_of,
                wheel, band="rw_rubber", flare=3.0, flare_lift=0.7 ):
    """ A road vehicle's body lofted through profile( a ) (its right half, bottom to the top's centre, the same number
    of points at every a; point 1 is the black band's top and point 2 the side's widest line, over the wheel arches) at
    base_stations plus the arches' cuts, front at a 0 and tail at L. paint_of( segment, a ) gives ( paint, part ): each
    part shades smooth. Wheel arches of radius arch round the axles (depths) for wheels of radius tyre, with black
    liners reaching inner_half in and flares flare wide standing flare_lift proud; the band paints the lower side below point 1.
    side_x( a, z ) is the side's x at height z. wheel( ac, xs ) draws each wheel. Flat end faces close the body. """
    S = _Smooth()
    loc = lambda x, a, z: ( x, -a, z )
    steps = 10
    stations = sorted( set( base_stations ) | { ac - arch * math.cos( math.pi * j / steps )
                                               for ac in axles for j in range( steps + 1 ) } )
    profiles = { a: profile( a ) for a in stations }

    def in_arch( a ):
        return any( abs( a - ac ) < arch - 1e-6 for ac in axles )

    def arch_z( a ):
        ac = min( axles, key=lambda c: abs( a - c ) )
        return tyre + math.sqrt( max( 0.0, arch ** 2 - ( a - ac ) ** 2 ) )

    # The body's skin, both sides.
    for a0, a1 in zip( stations, stations[1:] ):
        p0, p1 = profiles[a0], profiles[a1]
        mid = ( a0 + a1 ) / 2
        arched = in_arch( mid )
        for k in range( len( p0 ) - 1 ):
            if arched and k <= 1:
                continue
            pnt, part = paint_of( k, mid )
            for xs in ( 1.0, -1.0 ):
                dx = ( p0[k + 1][0] - p0[k][0] + p1[k + 1][0] - p1[k][0] )
                dz = ( p0[k + 1][1] - p0[k][1] + p1[k + 1][1] - p1[k][1] )
                S.add( pnt, part, [ loc( xs * p0[k][0], a0, p0[k][1] ), loc( xs * p0[k + 1][0], a0, p0[k + 1][1] ),
                                    loc( xs * p1[k + 1][0], a1, p1[k + 1][1] ), loc( xs * p1[k][0], a1, p1[k][1] ) ],
                       ( xs * dz, 0.0, -dx ) )
        if arched:          # round the wheel arches: the side from the arch's edge up to the widest line
            for xs in ( 1.0, -1.0 ):
                z0a, z1a = arch_z( a0 ), arch_z( a1 )
                lo0, lo1 = p0[1][1], p1[1][1]
                pts = [ loc( xs * side_x( a0, max( z0a, lo0 ) ), a0, max( z0a, lo0 ) ),
                        loc( xs * side_x( a1, max( z1a, lo1 ) ), a1, max( z1a, lo1 ) ),
                        loc( xs * p1[2][0], a1, p1[2][1] ), loc( xs * p0[2][0], a0, p0[2][1] ) ]
                S.add( body_paint, "body", pts, ( xs, 0, 0 ) )
                if z0a < lo0 or z1a < lo1:
                    S.add( band, "clad", [ loc( xs * side_x( a0, min( z0a, lo0 ) ), a0, min( z0a, lo0 ) ),
                                                  loc( xs * side_x( a1, min( z1a, lo1 ) ), a1, min( z1a, lo1 ) ),
                                                  loc( xs * p1[1][0], a1, lo1 ), loc( xs * p0[1][0], a0, lo0 ) ],
                           ( xs, 0, 0 ) )
    # The nose and tail: flat faces of the end sections.
    for a, toward in ( ( 0.0, 1.0 ), ( L, -1.0 ) ):
        prof = profiles[a]
        pts = [ loc( x, a, z ) for x, z in prof ] + [ loc( -x, a, z ) for x, z in reversed( prof ) if x > 0 ]
        S.add( body_paint, "cap%d" % int( a ), pts, ( 0, toward, 0 ) )
    S.draw( model, F )

    # The underside, the arches' liners and flares, and the wheels.
    for a0, a1 in zip( stations, stations[1:] ):
        p0, p1 = profiles[a0], profiles[a1]
        half = lambda p: inner_half if in_arch( ( a0 + a1 ) / 2 ) else p[0][0]
        _fpoly( model, F, "rw_black", [ loc( -half( p0 ), a0, p0[0][1] ), loc( half( p0 ), a0, p0[0][1] ),
                                        loc( half( p1 ), a1, p1[0][1] ), loc( -half( p1 ), a1, p1[0][1] ) ],
                ( 0, 0, -1 ) )
    for ac in axles:
        arc = [ ( ac - arch * math.cos( math.pi * j / steps ), math.pi - math.pi * j / steps )
                for j in range( steps + 1 ) ]
        for xs in ( 1.0, -1.0 ):
            for ( a0, t0 ), ( a1, t1 ) in zip( arc, arc[1:] ):
                z0_, z1_ = tyre + arch * math.sin( t0 ), tyre + arch * math.sin( t1 )
                xo0, xo1 = side_x( a0, z0_ ), side_x( a1, z1_ )
                _fpoly( model, F, band, [ loc( xs * xo0, a0, z0_ ), loc( xs * xo1, a1, z1_ ),
                                                 loc( xs * ( xo1 - 11.0 ), a1, z1_ ),
                                                 loc( xs * ( xo0 - 11.0 ), a0, z0_ ) ],
                        ( 0, ( a0 + a1 ) / 2 - ac, tyre - ( z0_ + z1_ ) / 2 ) )
                # The flare: a black band round the arch, standing proud, with its inner edge.
                ro = arch + flare
                pts = []
                for t, rad in ( ( t0, arch ), ( t0, ro ), ( t1, ro ), ( t1, arch ) ):
                    aa, zz = ac + rad * math.cos( t ), tyre + rad * math.sin( t )
                    pts.append( loc( xs * ( side_x( aa, zz ) + flare_lift ), aa, zz ) )
                _fpoly( model, F, band, pts, ( xs, 0, 0 ) )
                edge = []
                for t, lift in ( ( t0, 0.0 ), ( t0, flare_lift ), ( t1, flare_lift ), ( t1, 0.0 ) ):
                    aa, zz = ac + arch * math.cos( t ), tyre + arch * math.sin( t )
                    edge.append( loc( xs * ( side_x( aa, zz ) + lift ), aa, zz ) )
                _fpoly( model, F, band, edge, ( 0, ( a0 + a1 ) / 2 - ac, tyre - ( z0_ + z1_ ) / 2 ) )
            wall = [ loc( xs * ( side_x( a, z ) - 11.0 ), a, z ) for a, z in
                     [ ( ac + arch * math.cos( t ), tyre + arch * math.sin( t ) ) for _, t in arc ] ]
            _fpoly( model, F, "rw_black", wall, ( xs, 0, 0 ) )
            wheel( ac, xs )


def _suv_wheel( model, F, ac, xs ):
    """ A wheel at depth ac on side xs: a 235/50 R19 tyre with rounded shoulders on a dark ten-spoke alloy (five pairs),
    the brake disc behind it. """
    r, w, rim = SUV_TYRE, SUV_TYRE_W, SUV_RIM
    xo, xi = SUV_TRACK + w / 2, SUV_TRACK - w / 2

    def p( x, rad, t ):         # x across, at radius rad and angle t round the hub, in the frame's own coordinates
        return ( xs * x, -( ac + rad * math.cos( t ) ), r + rad * math.sin( t ) )

    rod( model, F.p( xs * ( xi + 0.9 ), -ac, r ), F.p( xs * ( xo - 0.9 ), -ac, r ), r, "rw_rubber", 28 )
    for x0, x1, r1 in ( ( xo - 0.9, xo, r - 1.1 ), ( xi + 0.9, xi, r - 1.1 ) ):
        _frustum( model, F.p( xs * x0, -ac, r ), F.p( xs * x1, -ac, r ), r, r1, "rw_rubber", 28 )
    n = 28
    for k in range( n ):            # the sidewalls, the rim's lip and the barrel's back
        t0, t1 = 2 * math.pi * k / n, 2 * math.pi * ( k + 1 ) / n
        for x, r0, r1, paint, out in ( ( xo, rim + 0.6, r - 1.1, "rw_rubber", 1 ), ( xo + 0.02, rim, rim + 0.6,
                                                                                    "rw_steel_dark", 1 ),
                                       ( xi, 0.0, r - 1.1, "rw_rubber", -1 ) ):
            _fpoly( model, F, paint, [ p( x, r0, t0 ), p( x, r1, t0 ), p( x, r1, t1 ), p( x, r0, t1 ) ],
                    ( out * xs, 0, 0 ) )
    disc( model, "rw_black", F.p( xs * ( xo - 3.2 ), -ac, r ), ( xs * F.x ), rim, sides=24 )
    disc( model, "rw_steel_grey", F.p( xs * ( xo - 2.9 ), -ac, r ), ( xs * F.x ), 6.9, sides=24 )
    disc( model, "rw_bogie", F.p( xs * ( xo - 2.85 ), -ac, r ), ( xs * F.x ), 3.4, sides=12 )
    for pair in range( 5 ):         # five pairs of spokes, from the hub out to the lip, the hub sunk 0.9
        for side in ( -1, 1 ):
            t = 2 * math.pi * pair / 5 + side * math.radians( 9.0 )
            rh, rl = 2.9, rim - 0.1
            dh, dl = math.radians( 8.0 ), math.radians( 3.4 )
            pts = [ p( xo - 0.9, rh, t - dh ), p( xo - 0.15, rl, t - dl ), p( xo - 0.15, rl, t + dl ),
                    p( xo - 0.9, rh, t + dh ) ]
            _fpoly( model, F, "rw_steel_dark", pts, ( xs, 0, 0 ) )
    disc( model, "rw_steel_dark", F.p( xs * ( xo - 0.88 ), -ac, r ), ( xs * F.x ), 3.0, sides=16 )
    disc( model, "rw_steel_grey", F.p( xs * ( xo - 0.8 ), -ac, r ), ( xs * F.x ), 1.2, sides=12 )
    for k in range( 5 ):
        t = 2 * math.pi * ( k + 0.5 ) / 5
        disc( model, "rw_steel_grey", F.p( *p( xo - 0.82, 2.1, t ) ), ( xs * F.x ), 0.38, sides=6 )


def _plate( model, F, centre, right, up, facing, text ):
    """ A German number plate, 520 x 110 mm: white, the blue band with its ring of stars and D on the left, the text
    in black in the plate font. centre, right (the reader's), up and facing in the vehicle frame's coordinates (which
    are left-handed, so facing is given rather than worked out). """
    c, r, u = np.asarray( centre, float ), _unit( right ), _unit( up )
    face = _unit( facing )
    P = lambda x, y, lift: tuple( c + r * x + u * y + face * lift )
    W, H = 10.24, 2.17
    _fpoly( model, F, "rw_black", [ P( -W - 0.25, -H - 0.25, 0 ), P( W + 0.25, -H - 0.25, 0 ), P( W + 0.25, H + 0.25, 0 ),
                                    P( -W - 0.25, H + 0.25, 0 ) ], tuple( face ) )
    _fpoly( model, F, "rw_white_paint", [ P( -W, -H, 0.05 ), P( W, -H, 0.05 ), P( W, H, 0.05 ), P( -W, H, 0.05 ) ],
            tuple( face ) )
    band = 1.58
    _fpoly( model, F, "rw_train_blue", [ P( -W, -H, 0.08 ), P( -W + band, -H, 0.08 ), P( -W + band, H, 0.08 ),
                                         P( -W, H, 0.08 ) ], tuple( face ) )
    for k in range( 12 ):
        t = 2 * math.pi * k / 12
        x, y = -W + band / 2 + 0.42 * math.cos( t ), 0.9 + 0.42 * math.sin( t )
        _fpoly( model, F, "rw_yellow_paint", [ P( x - 0.06, y - 0.06, 0.1 ), P( x + 0.06, y - 0.06, 0.1 ),
                                               P( x + 0.06, y + 0.06, 0.1 ), P( x - 0.06, y + 0.06, 0.1 ) ],
                tuple( face ) )

    def write( s, x0, y0, px, py, paint, lift ):
        for i, ch in enumerate( s ):
            rows = PLATE_FONT.get( ch, PLATE_FONT[" "] ).split( "|" )
            for rr, row in enumerate( rows ):
                c0 = None
                for cc, on in enumerate( row + "." ):
                    if on == "#" and c0 is None:
                        c0 = cc
                    elif on != "#" and c0 is not None:
                        xa, xb = x0 + ( 6 * i + c0 ) * px, x0 + ( 6 * i + cc ) * px
                        ya, yb = y0 - ( rr + 1 ) * py, y0 - rr * py
                        _fpoly( model, F, paint, [ P( xa, ya, lift ), P( xb, ya, lift ), P( xb, yb, lift ),
                                                   P( xa, yb, lift ) ], tuple( face ) )
                        c0 = None

    write( "D", -W + band / 2 - 0.45, -0.25, 0.18, 0.22, "rw_white_paint", 0.11 )
    px, py = 0.34, 0.46
    width = ( 6 * len( text ) - 1 ) * px
    x0 = -W + band + ( 2 * W - band - width ) / 2
    write( text, x0, 7 * py / 2, px, py, "rw_black", 0.1 )


def suv( model, e, n, along="+n", paint="rw_car_grey", z0=0.0, plate="HW K 318" ):
    """ A parked compact crossover SUV (SUV_*), its nose towards along ("+n", "-n", "+e", "-e"), (e, n) its footprint's
    centre. Body paint (the rw_car_* paints), black cladding round the sills and arches, tinted glass in black frames,
    a black honeycomb grille, a slim LED light bar across the nose, boomerang air intakes at its corners lit along
    their edges, wrap-round tail lights joined by a light bar, roof rails, a roof spoiler, dark ten-spoke alloys and
    the town's number plates. Two metal boxes: the body to the belt and the cabin. """
    L = SUV_L
    F = _vehicle_frame( e, n, along, L, z0 )
    loc = lambda x, a, z: ( x, -a, z )
    axles = SUV_AXLES
    def paint_of( k, mid ):
        if k == 0:
            return "rw_rubber", "clad"
        if k <= 3:
            return paint, "body"
        if k == 4:
            if SUV_COWL < mid < SUV_ROOF1 + 0.5:
                if any( w0 <= mid <= w1 for w0, w1 in SUV_WINDOWS ):
                    return "rw_window_dark", "glass"
                if mid > SUV_WINDOWS[0][0]:
                    return "rw_black", "frame"
            return paint, "body"
        if k == 5:
            if SUV_COWL < mid < SUV_GLASS1 - 0.5:     # the A pillars and the window frames
                return "rw_black", "frame"
            return paint, "body"
        if SUV_COWL < mid < SUV_COWL + 1.5:
            return "rw_black", "frame"
        if SUV_COWL + 1.5 <= mid < SUV_ROOF0 or SUV_ROOF1 + 1.0 < mid < SUV_GLASS1 - 0.5:
            return "rw_window_dark", "glass"
        if k == 6 and SUV_ROOF1 <= mid <= SUV_ROOF1 + 1.0:
            return "rw_black", "frame"
        return paint, "body"

    _road_body( model, F, _suv_profile, _suv_side_x, SUV_STATIONS, axles, SUV_TYRE, SUV_ARCH,
                SUV_TRACK - SUV_TYRE_W / 2 - 0.5, L, paint, paint_of, lambda ac, xs: _suv_wheel( model, F, ac, xs ) )

    def side_patch( pnt, xs, pts, lift=0.06 ):
        """ A flat patch on the side, its corners ( a, z ), lift off the skin. """
        _fpoly( model, F, pnt, [ loc( xs * ( _suv_side_x( a, z ) + lift ), a, z ) for a, z in pts ], ( xs, 0, 0 ) )

    def seam( xs, line, width=0.32 ):
        """ A panel gap along a line of ( a, z ) on the side. """
        for ( a0, z0_ ), ( a1, z1_ ) in zip( line, line[1:] ):
            dl = math.hypot( a1 - a0, z1_ - z0_ ) or 1.0
            na, nz = -( z1_ - z0_ ) / dl * width / 2, ( a1 - a0 ) / dl * width / 2
            side_patch( "rw_black", xs, [ ( a0 - na, z0_ - nz ), ( a1 - na, z1_ - nz ), ( a1 + na, z1_ + nz ),
                                          ( a0 + na, z0_ + nz ) ], 0.05 )

    belt = lambda a: _suv_profile( a )[4][1]
    for xs in ( 1.0, -1.0 ):
        # Door gaps: the front door's front edge behind the front arch, the B pillar's, the rear door's rear edge
        # round the rear arch; the fuel filler on the right.
        seam( xs, [ ( 55.0, 17.2 ), ( 54.2, 31.5 ), ( 53.4, belt( 53.4 ) - 0.3 ) ] )
        seam( xs, [ ( 97.5, 17.2 ), ( 97.5, belt( 97.5 ) - 0.3 ) ] )
        rear = [ ( 141.0 + 19.4 * math.cos( math.radians( t ) ), SUV_TYRE + 19.4 * math.sin( math.radians( t ) ) )
                 for t in range( 172, 96, -12 ) ]
        seam( xs, [ ( 121.6, 17.2 ) ] + rear + [ ( 138.4, belt( 138.4 ) - 0.3 ) ] )
        if xs > 0:
            seam( xs, [ ( 147.0, 38.0 ), ( 152.5, 38.0 ), ( 152.5, 42.5 ), ( 147.0, 42.5 ), ( 147.0, 38.0 ) ], 0.24 )
        # Flush door handles on the shoulder, and the mirrors on the doors at the A pillar's foot.
        for a0 in ( 80.0, 120.5 ):
            side_patch( "rw_black", xs, [ ( a0 - 0.4, 37.1 ), ( a0 + 6.4, 37.1 ), ( a0 + 6.4, 38.9 ),
                                          ( a0 - 0.4, 38.9 ) ], 0.08 )
            x0 = _suv_side_x( a0 + 3.0, 38.0 )
            F.box( model, xs * ( x0 + 0.1 ), xs * ( x0 + 0.75 ), -a0, -( a0 + 6.0 ), 37.35, 38.65, paint )
        xm = _suv_side_x( 56.0, 42.0 )
        F.box( model, xs * ( xm - 0.6 ), xs * ( xm + 1.6 ), -53.0, -58.4, 40.6, 43.6, "rw_rubber" )
        F.box( model, xs * ( xm + 1.0 ), xs * ( xm + 5.8 ), -54.2, -58.4, 41.0, 45.2, { "default": paint,
                                                                                         "back": "rw_black",
                                                                                         "bottom": "rw_black" } )
        F.box( model, xs * ( xm + 1.4 ), xs * ( xm + 5.4 ), -58.4, -58.55, 41.4, 44.8, "rw_steel_grey" )
        # The tail lights wrapping round onto the sides.
        side_patch( "rw_red_paint", xs, [ ( 165.5, 37.4 ), ( 173.2, 36.6 ), ( 173.2, 39.4 ), ( 166.5, 40.2 ) ], 0.08 )
        side_patch( "rw_black", xs, [ ( 165.0, 37.0 ), ( 173.4, 36.2 ), ( 173.4, 39.8 ), ( 166.0, 40.6 ) ], 0.05 )
        # Roof rails on their feet.
        xr = 23.6
        pts = [ ( a, _suv_top_z( a, xr ) + 2.0 ) for a in np.linspace( 86.0, 150.0, 9 ) ]
        for ( a0, z0_ ), ( a1, z1_ ) in zip( pts, pts[1:] ):
            rod( model, F.p( xs * xr, -a0, z0_ ), F.p( xs * xr, -a1, z1_ ), 0.75, "rw_black", 6 )
        for a in ( 87.0, 118.0, 149.0 ):
            z = _suv_top_z( a, xr )
            F.box( model, xs * ( xr - 0.7 ), xs * ( xr + 0.7 ), -( a - 1.6 ), -( a + 1.6 ), z - 0.2, z + 2.2,
                   "rw_black" )

    # The roof spoiler over the rear window, with the high brake light under its edge, and the shark-fin aerial.
    zs = _suv_top_z( SUV_ROOF1 - 2.0, 0.0 )
    _fpoly( model, F, paint, [ loc( -26.0, SUV_ROOF1 - 3.0, zs + 0.05 ), loc( 26.0, SUV_ROOF1 - 3.0, zs + 0.05 ),
                               loc( 26.0, SUV_ROOF1 + 3.4, zs - 1.0 ), loc( -26.0, SUV_ROOF1 + 3.4, zs - 1.0 ) ],
            ( 0, -0.2, 1 ) )
    _fpoly( model, F, "rw_black", [ loc( -26.0, SUV_ROOF1 + 3.4, zs - 1.0 ), loc( 26.0, SUV_ROOF1 + 3.4, zs - 1.0 ),
                                    loc( 26.0, SUV_ROOF1 + 3.4, zs - 2.3 ), loc( -26.0, SUV_ROOF1 + 3.4, zs - 2.3 ) ],
            ( 0, -1, 0 ) )
    _fpoly( model, F, "rw_red_paint", [ loc( -9.0, SUV_ROOF1 + 3.45, zs - 1.3 ), loc( 9.0, SUV_ROOF1 + 3.45, zs - 1.3 ),
                                        loc( 9.0, SUV_ROOF1 + 3.45, zs - 2.0 ), loc( -9.0, SUV_ROOF1 + 3.45, zs - 2.0 ) ],
            ( 0, -1, 0 ) )
    za = _suv_top_z( 147.0, 0.0 )
    fin = [ ( 144.0, za - 0.1 ), ( 150.5, za - 0.4 ), ( 149.2, za + 2.4 ), ( 147.6, za + 2.6 ) ]
    for xs in ( 1.0, -1.0 ):
        _fpoly( model, F, "rw_black", [ loc( xs * ( 0.9 if z < za + 1 else 0.3 ), a, z ) for a, z in fin ],
                ( xs, 0, 0 ) )
    _fpoly( model, F, "rw_black", [ loc( -0.3, 149.2, za + 2.4 ), loc( 0.3, 149.2, za + 2.4 ), loc( 0.3, 147.6, za + 2.6 ),
                                    loc( -0.3, 147.6, za + 2.6 ) ], ( 0, 0, 1 ) )
    _fpoly( model, F, "rw_black", [ loc( -0.9, 144.0, za - 0.1 ), loc( 0.9, 144.0, za - 0.1 ), loc( 0.3, 147.6, za + 2.6 ),
                                    loc( -0.3, 147.6, za + 2.6 ) ], ( 0, 1, 0.5 ) )
    _fpoly( model, F, "rw_black", [ loc( -0.3, 149.2, za + 2.4 ), loc( 0.3, 149.2, za + 2.4 ), loc( 0.9, 150.5, za - 0.4 ),
                                    loc( -0.9, 150.5, za - 0.4 ) ], ( 0, -1, 0.5 ) )

    # Wipers: two on the windscreen's foot, one on the rear window.
    for x0, x1 in ( ( 2.0, -21.0 ), ( 25.0, 3.0 ) ):
        pa = [ ( x, SUV_COWL + 1.2 + ( 4.5 if x == x1 else 0.0 ) ) for x in ( x0, x1 ) ]
        p = [ F.p( x, -a, _suv_top_z( a, x ) + 0.35 ) for x, a in pa ]
        rod( model, p[0], p[1], 0.32, "rw_black", 4 )
    p0, p1 = ( 0.0, SUV_GLASS1 - 0.6 ), ( -13.0, SUV_GLASS1 - 4.5 )
    rod( model, F.p( p0[0], -p0[1], _suv_top_z( p0[1], 0.0 ) + 0.35 ),
         F.p( p1[0], -p1[1], _suv_top_z( p1[1], 13.0 ) + 0.35 ), 0.3, "rw_black", 4 )

    # The nose, on its face at a 0 (y = +lift): the lower bumper, the honeycomb grille with the plate on it, the light
    # bar under the bonnet's edge with the headlights' dark glass under its ends, and the boomerang intakes.
    def face( pnt, pts, lift ):
        _fpoly( model, F, pnt, [ ( x, lift, z ) for x, z in pts ], ( 0, 1, 0 ) )

    fx = lambda z: _suv_side_x( 0.0, z ) if z <= _suv_profile( 0.0 )[4][1] else _suv_profile( 0.0 )[4][0]
    face( "rw_rubber", [ ( -fx( 12.5 ), 12.5 ), ( fx( 12.5 ), 12.5 ), ( fx( 15.2 ) - 0.2, 15.2 ),
                         ( -fx( 15.2 ) + 0.2, 15.2 ) ], 0.06 )
    face( "rw_steel_grey", [ ( -15.0, 12.8 ), ( 15.0, 12.8 ), ( 14.5, 14.2 ), ( -14.5, 14.2 ) ], 0.12 )
    gz0, gz1, gw0, gw1 = 15.0, 28.9, 19.2, 21.8             # the grille, from the skid plate to the lamps' band
    face( "rw_black", [ ( -gw0 - 0.7, gz0 - 0.5 ), ( gw0 + 0.7, gz0 - 0.5 ), ( gw1 + 0.7, gz1 + 0.5 ),
                        ( -gw1 - 0.7, gz1 + 0.5 ) ], 0.08 )
    face( "rw_steel_dark", [ ( -gw0, gz0 ), ( gw0, gz0 ), ( gw1, gz1 ), ( -gw1, gz1 ) ], 0.14 )
    for row in range( 12 ):                 # honeycomb cells, 3 across, pointy side up
        z = gz0 + 0.95 + row * 1.15
        for col in range( -9, 10 ):
            x = col * 2.48 + ( 1.24 if row % 2 else 0.0 )
            half = gw0 + ( gw1 - gw0 ) * ( z - gz0 ) / ( gz1 - gz0 )
            if abs( x ) > half - 1.3 or z > gz1 - 0.9:
                continue
            face( "rw_black", [ ( x + 1.08 * math.cos( math.radians( 30 + 60 * k ) ),
                                  z + 0.84 * math.sin( math.radians( 30 + 60 * k ) ) ) for k in range( 6 ) ], 0.24 )
    _plate( model, F, ( 0.0, 0.42, 18.3 ), ( 1, 0, 0 ), ( 0, 0, 1 ), ( 0, 1, 0 ), plate )

    def nose( x, z, lift ):
        """ The point at ( x, z ) on the face, or above it on the sloping fascia under the bonnet's edge, lift off it,
        in the frame's own coordinates. """
        if z <= _suv_top_z( 0.0, x ):
            return ( x, lift, z )
        lo, hi = 0.0, 12.0
        for _ in range( 30 ):
            m = ( lo + hi ) / 2
            if _suv_top_z( m, x ) < z:
                lo = m
            else:
                hi = m
        return ( x, -( lo + hi ) / 2 + lift, z + 0.5 * lift )

    def nose_patch( pnt, x0, x1, z0, z1, lift, step=2.0 ):
        n = max( 1, int( math.ceil( abs( x1 - x0 ) / step ) ) )
        xs_ = [ x0 + ( x1 - x0 ) * j / n for j in range( n + 1 ) ]
        for xa, xb in zip( xs_, xs_[1:] ):
            _fpoly( model, F, pnt, [ nose( xa, z0, lift ), nose( xb, z0, lift ), nose( xb, z1, lift ),
                                     nose( xa, z1, lift ) ], ( 0, 1, 0.4 ) )

    nose_patch( "rw_black", -27.4, 27.4, 29.0, 32.5, 0.06 )         # the lamps' black band under the bonnet's edge
    nose_patch( "rw_lamp_cool", -26.6, 26.6, 31.55, 31.95, 0.14 )  # the light bar
    for xs in ( 1.0, -1.0 ):
        nose_patch( "rw_window_dark", xs * 18.0, xs * 27.0, 29.4, 31.2, 0.1 )
        nose_patch( "rw_steel_grey", xs * 22.6, xs * 25.8, 29.75, 30.85, 0.14 )
        for pts in ( [ ( 21.8, 26.1 ), ( fx( 26.1 ) - 1.1, 26.1 ), ( fx( 27.9 ) - 1.0, 27.9 ), ( 21.8, 27.9 ) ],
                     [ ( fx( 18.7 ) - 3.4, 18.7 ), ( fx( 18.7 ) - 1.5, 18.7 ), ( fx( 26.1 ) - 1.1, 26.1 ),
                       ( fx( 26.1 ) - 3.0, 26.1 ) ],
                     [ ( 23.6, 15.6 ), ( fx( 15.6 ) - 1.6, 15.6 ), ( fx( 18.7 ) - 1.5, 18.7 ), ( 23.6, 18.7 ) ] ):
            face( "rw_black", [ ( xs * x, z ) for x, z in pts ], 0.1 )
        xe = lambda z: fx( z ) - 2.0
        face( "rw_lamp_cool", [ ( xs * ( xe( 19.6 ) - 0.15 ), 19.6 ), ( xs * ( xe( 19.6 ) + 0.2 ), 19.6 ),
                                ( xs * ( xe( 27.3 ) + 0.2 ), 27.3 ), ( xs * ( xe( 27.3 ) - 0.15 ), 27.3 ) ], 0.14 )
        face( "rw_lamp_cool", [ ( xs * 23.0, 27.0 ), ( xs * ( xe( 27.3 ) + 0.2 ), 27.0 ),
                                ( xs * ( xe( 27.35 ) + 0.2 ), 27.35 ), ( xs * 23.0, 27.35 ) ], 0.14 )
        face( "rw_steel_grey", [ ( xs * 24.4, 20.0 ), ( xs * 26.4, 20.0 ), ( xs * 26.4, 21.4 ), ( xs * 24.4, 21.4 ) ],
              0.13 )

    # The tail: the black diffuser with its skid strip and reflectors on the bumper's face, the tailgate's light bar
    # and lamps, and the plate on the tailgate's lower panel.
    def back( pnt, pts, lift ):
        _fpoly( model, F, pnt, [ ( x, -L - lift, z ) for x, z in pts ], ( 0, -1, 0 ) )

    bx = lambda z: _suv_side_x( L, z )
    back( "rw_rubber", [ ( -bx( 13.0 ), 13.0 ), ( bx( 13.0 ), 13.0 ), ( bx( 19.5 ) - 0.2, 19.5 ),
                         ( -bx( 19.5 ) + 0.2, 19.5 ) ], 0.06 )
    back( "rw_steel_grey", [ ( -16.0, 13.5 ), ( 16.0, 13.5 ), ( 15.4, 14.9 ), ( -15.4, 14.9 ) ], 0.12 )
    for xs in ( 1.0, -1.0 ):
        back( "rw_red_paint", [ ( xs * 23.5, 17.4 ), ( xs * 27.5, 17.4 ), ( xs * 27.5, 18.4 ), ( xs * 23.5, 18.4 ) ],
              0.12 )

    def hatch( x, z, lift ):
        """ The point on the tailgate at ( x, z ), lift off it, found along a, in the frame's own coordinates. """
        lo, hi = SUV_GLASS1 - 2.0, L
        for _ in range( 30 ):
            m = ( lo + hi ) / 2
            if _suv_top_z( m, x ) > z:
                lo = m
            else:
                hi = m
        a = ( lo + hi ) / 2
        return ( x, -( a + lift ), z + 0.35 * lift )

    def tail( pnt, pts, lift, n=6 ):
        """ A lamp or panel on the tailgate from corner ( x0, z0 ) to ( x1, z1 ), in strips that follow it. """
        ( x0, z0_ ), ( x1, z1_ ) = pts
        xs_ = list( np.linspace( x0, x1, n + 1 ) )
        for xa, xb in zip( xs_, xs_[1:] ):
            _fpoly( model, F, pnt, [ hatch( xa, z0_, lift ), hatch( xb, z0_, lift ), hatch( xb, z1_, lift ),
                                     hatch( xa, z1_, lift ) ], ( 0, -1, 0.6 ) )

    for xs in ( 1.0, -1.0 ):
        tail( "rw_black", ( ( xs * 15.5, 37.0 ), ( xs * 31.0, 40.6 ) ), 0.06 )
        tail( "rw_red_paint", ( ( xs * 17.0, 37.6 ), ( xs * 30.6, 40.0 ) ), 0.12 )
    tail( "rw_red_paint", ( ( -15.5, 39.0 ), ( 15.5, 39.6 ) ), 0.1, 8 )
    zp = 35.4
    up = np.subtract( hatch( 0.0, zp + 1.0, 0.0 ), hatch( 0.0, zp - 1.0, 0.0 ) )
    _plate( model, F, hatch( 0.0, zp, 0.3 ), ( -1, 0, 0 ), tuple( up ), ( 0, -up[2], up[1] ), plate )

    # Collision: the body to the belt, and the cabin.
    F.collide( model, -SUV_W, SUV_W, -L, 0.0, 0.0, 40.5, "metal" )
    F.collide( model, -30.0, 30.0, -( SUV_ROOF1 + 2.0 ), -( SUV_COWL + 2.0 ), 40.5, 63.2, "metal" )


# A large panel van, as Europe's current ones are: 5.99 m long, 2.04 m wide and 2.36 m tall on a 3.64 m wheelbase,
# 205/75 R16C tyres on steel wheels. A short bonnet under a steep windscreen, the grille leaning back between slim
# headlights, a black bumper, a black band along the sills, a cab door with its quarter light, a sliding side door and
# two rear doors. Lofted like the SUV (_road_body); no maker's badge.

VAN_L = 235.7
VAN_W = 40.2
VAN_AXLES = ( 40.0, 183.3 )
VAN_TYRE, VAN_TYRE_W, VAN_RIM = 14.05, 8.1, 8.0
VAN_TRACK = 34.1
VAN_ARCH = 16.4
VAN_COWL, VAN_ROOF0 = 31.0, 71.0        # the windscreen's foot and top
VAN_PLAN = [ ( 0.0, 36.0 ), ( 1.0, 37.9 ), ( 2.5, 39.0 ), ( 5.0, 39.8 ), ( 9.0, 40.2 ), ( 231.0, 40.2 ), ( 233.5, 39.7 ),
             ( 235.0, 38.6 ), ( VAN_L, 37.2 ) ]
VAN_BOTTOM = [ ( 0.0, 12.5 ), ( 10.0, 11.5 ), ( 28.0, 10.8 ), ( 215.0, 10.8 ), ( 230.0, 12.0 ), ( VAN_L, 13.0 ) ]
VAN_TOP = [ ( 0.0, 27.0 ), ( 1.2, 29.5 ), ( 2.6, 33.0 ), ( 4.2, 36.6 ), ( 5.6, 39.3 ), ( 7.0, 41.0 ), ( 12.0, 42.4 ),
            ( 24.0, 45.6 ), ( VAN_COWL, 47.6 ), ( VAN_ROOF0, 89.6 ), ( 78.0, 92.2 ), ( 120.0, 92.7 ), ( 232.0, 92.7 ),
            ( VAN_L, 92.2 ) ]
VAN_BELT = [ ( 0.0, 25.8 ), ( 7.0, 39.6 ), ( VAN_COWL, 47.0 ), ( 60.0, 52.5 ), ( 72.0, 54.6 ), ( VAN_L, 56.0 ) ]
VAN_WINDOWS = ( ( 41.0, 63.6 ), ( 65.4, 100.8 ) )        # the cab's quarter light and door glass, along a
VAN_STATIONS = [ 0.0, 0.4, 0.8, 1.2, 1.8, 2.6, 3.4, 4.2, 4.9, 5.6, 6.3, 7.0, 8.5, 10.0, 12.0, 16.0, 20.0, 24.0, 28.0,
                 VAN_COWL, 32.6, 36.0, 41.0, 46.0, 51.0, 56.0, 61.0, 63.6, 65.4, 68.0, 70.2, VAN_ROOF0, 74.0, 78.0,
                 84.0, 92.0, 100.8, 102.0, 106.0, 120.0, 140.0, 160.0, 200.0, 215.0, 225.0, 229.0, 231.0, 232.5,
                 233.5, 234.3, 235.0, 235.4, VAN_L ]


def _van_profile( a ):
    """ The right half of the van's cross-section at depth a, bottom to the top's centre: the sill's tuck, the black
    band's top, the side's crease (its widest line), the belt, then five points over the top (the fascia, the bonnet,
    the windscreen or the roof). """
    W = _interp( VAN_PLAN, a )
    zb, zt = _interp( VAN_BOTTOM, a ), _interp( VAN_TOP, a )
    belt = min( _interp( VAN_BELT, a ), zt - 1.2 )
    crease = min( 52.0, belt - 1.0 )
    lo = min( 26.0, crease - 1.0 )
    side = [ ( W - 2.0, zb ), ( W - 0.3, lo ), ( W, crease ), ( W - 0.5, belt ) ]

    def bonnet():
        d = zt - belt
        return [ ( W - 3.2, belt + 0.5 * d ), ( W - 7.0, belt + 0.8 * d ), ( min( 24.0, W - 11.0 ), belt + 0.94 * d ),
                 ( 12.0, zt - 0.05 ), ( 0.0, zt ) ]

    def cabin():                # the roof's side from the windows' top, its rounded edge and its crown
        return [ ( W - 2.2, zt - 7.5 ), ( W - 4.2, zt - 2.6 ), ( W - 7.6, zt - 0.8 ), ( 16.0, zt - 0.1 ), ( 0.0, zt ) ]

    if a <= VAN_COWL:
        top = bonnet()
    elif a < VAN_ROOF0:
        t = ( a - VAN_COWL ) / ( VAN_ROOF0 - VAN_COWL )
        t = t * t * ( 3 - 2 * t )
        top = [ ( p[0] + ( q[0] - p[0] ) * t, p[1] + ( q[1] - p[1] ) * t ) for p, q in zip( bonnet(), cabin() ) ]
    else:
        top = cabin()
    return side + top


def _van_side_x( a, z ):
    """ The van's side's x at height z (up to the roof's edge, or the fascia's) at depth a. """
    prof = _van_profile( a )[:5]
    if z <= prof[0][1]:
        return prof[0][0]
    for ( x0, z0 ), ( x1, z1 ) in zip( prof, prof[1:] ):
        if z0 <= z <= z1:
            return x0 + ( x1 - x0 ) * ( z - z0 ) / max( z1 - z0, 1e-6 )
    return prof[4][0]


def _van_top_z( a, x ):
    """ The top surface's z at |x| (inside the belt) at depth a. """
    prof = _van_profile( a )[3:]
    x = abs( x )
    for ( x0, z0 ), ( x1, z1 ) in zip( prof, prof[1:] ):
        if x1 <= x <= x0:
            return z0 + ( z1 - z0 ) * ( x0 - x ) / max( x0 - x1, 1e-6 )
    return prof[0][1]


def _van_wheel( model, F, ac, xs ):
    """ A wheel at depth ac on side xs: a 205/75 R16C tyre on a silver steel wheel, its dished centre with six nuts,
    six round vents and a black hub cap. """
    r, w, rim = VAN_TYRE, VAN_TYRE_W, VAN_RIM
    xo, xi = VAN_TRACK + w / 2, VAN_TRACK - w / 2

    def p( x, rad, t ):
        return ( xs * x, -( ac + rad * math.cos( t ) ), r + rad * math.sin( t ) )

    rod( model, F.p( xs * ( xi + 0.9 ), -ac, r ), F.p( xs * ( xo - 0.9 ), -ac, r ), r, "rw_rubber", 28 )
    for x0, x1 in ( ( xo - 0.9, xo ), ( xi + 0.9, xi ) ):
        _frustum( model, F.p( xs * x0, -ac, r ), F.p( xs * x1, -ac, r ), r, r - 1.2, "rw_rubber", 28 )
    n = 28
    for k in range( n ):
        t0, t1 = 2 * math.pi * k / n, 2 * math.pi * ( k + 1 ) / n
        for x, r0, r1, paint, out in ( ( xo, rim + 0.5, r - 1.2, "rw_rubber", 1 ), ( xo + 0.02, rim - 0.1, rim + 0.5,
                                                                                   "rw_steel_grey", 1 ),
                                       ( xo - 0.7, 5.6, rim - 0.1, "rw_steel_grey", 1 ),     # the rim's well
                                       ( xi, 0.0, r - 1.2, "rw_rubber", -1 ) ):
            _fpoly( model, F, paint, [ p( x, r0, t0 ), p( x, r1, t0 ), p( x, r1, t1 ), p( x, r0, t1 ) ],
                    ( out * xs, 0, 0 ) )
    _frustum( model, F.p( xs * ( xo - 0.7 ), -ac, r ), F.p( xs * ( xo - 1.6 ), -ac, r ), 5.6, 4.2, "rw_steel_grey", 20 )
    disc( model, "rw_steel_grey", F.p( xs * ( xo - 1.6 ), -ac, r ), ( xs * F.x ), 4.2, sides=20 )
    for k in range( 6 ):
        t = 2 * math.pi * ( k + 0.5 ) / 6
        disc( model, "rw_black", F.p( *p( xo - 0.68, 6.6, t ) ), ( xs * F.x ), 0.75, sides=10 )
        t = 2 * math.pi * k / 6
        disc( model, "rw_steel_dark", F.p( *p( xo - 1.58, 2.9, t ) ), ( xs * F.x ), 0.42, sides=6 )
    disc( model, "rw_black", F.p( xs * ( xo - 1.55 ), -ac, r ), ( xs * F.x ), 1.9, sides=14 )


def van( model, e, n, along="+n", paint="rw_car_white", z0=0.0, plate="HW L 418" ):
    """ A parked large panel van (VAN_*), its nose towards along ("+n", "-n", "+e", "-e"), (e, n) its footprint's
    centre: body paint (the rw_car_* paints), a black bumper and sill band with a silver sill strip, black arch trims,
    the grille's four bars in a dark frame, slim headlights with their running-light strips, fog lamps, black mirrors
    with indicators, a cab door, a sliding door with its rail, glazed rear doors, vertical tail lights, steel wheels and
    the town's number plates. Two metal boxes: the body to the bonnet, and the box behind the windscreen. """
    L = VAN_L
    F = _vehicle_frame( e, n, along, L, z0 )
    loc = lambda x, a, z: ( x, -a, z )

    def paint_of( k, mid ):
        if k == 0:
            return "rw_rubber", "band"
        if k <= 2:
            return paint, "body"
        if k == 3:
            if VAN_COWL + 2.0 < mid < VAN_ROOF0 + 32.0:
                if any( w0 <= mid <= w1 for w0, w1 in VAN_WINDOWS ):
                    return "rw_window_dark", "glass"
                if VAN_WINDOWS[0][0] - 1.0 < mid < VAN_WINDOWS[1][1] + 1.2:
                    return "rw_black", "frame"
            return paint, "body"
        if VAN_COWL < mid < VAN_COWL + 1.6 and k >= 5:
            return "rw_black", "frame"                  # the scuttle under the windscreen
        if VAN_COWL + 1.6 <= mid < VAN_ROOF0 - 0.6:
            if k >= 6:
                return "rw_window_dark", "glass"
            if k == 5:
                return "rw_black", "frame"              # the windscreen's black border
        if VAN_ROOF0 - 0.6 <= mid < VAN_ROOF0 + 0.8 and k >= 5:
            return "rw_black", "frame"
        return paint, "body"

    _road_body( model, F, _van_profile, _van_side_x, VAN_STATIONS, VAN_AXLES, VAN_TYRE, VAN_ARCH,
                VAN_TRACK - VAN_TYRE_W / 2 - 0.5, L, paint, paint_of, lambda ac, xs: _van_wheel( model, F, ac, xs ),
                flare=2.0, flare_lift=0.5 )

    def side_patch( pnt, xs, pts, lift=0.06 ):
        _fpoly( model, F, pnt, [ loc( xs * ( _van_side_x( a, z ) + lift ), a, z ) for a, z in pts ], ( xs, 0, 0 ) )

    def seam( xs, line, width=0.32 ):
        for ( a0, z0_ ), ( a1, z1_ ) in zip( line, line[1:] ):
            dl = math.hypot( a1 - a0, z1_ - z0_ ) or 1.0
            na, nz = -( z1_ - z0_ ) / dl * width / 2, ( a1 - a0 ) / dl * width / 2
            side_patch( "rw_black", xs, [ ( a0 - na, z0_ - nz ), ( a1 - na, z1_ - nz ), ( a1 + na, z1_ + nz ),
                                          ( a0 + na, z0_ + nz ) ], 0.05 )

    belt = lambda a: _van_profile( a )[3][1]
    top_side = 84.6                             # where the doors end under the roof's rounded edge
    for xs in ( 1.0, -1.0 ):
        # The cab door, the sliding door and its rail behind it, the handles, the silver sill strip.
        seam( xs, [ ( 66.6, 26.2 ), ( 65.6, belt( 65.6 ) - 0.2 ) ] )
        seam( xs, [ ( 103.0, 26.2 ), ( 103.0, top_side ) ] )
        for a in ( 106.2, 157.8 ):
            seam( xs, [ ( a, 26.2 ), ( a, top_side ) ] )
        seam( xs, [ ( 106.2, top_side ), ( 157.8, top_side ) ] )
        side_patch( "rw_black", xs, [ ( 158.6, 60.6 ), ( 226.0, 60.6 ), ( 226.0, 62.0 ), ( 158.6, 62.0 ) ], 0.1 )
        side_patch( "rw_steel_grey", xs, [ ( 60.5, 12.4 ), ( 162.0, 12.4 ), ( 162.0, 14.6 ), ( 60.5, 14.6 ) ], 0.15 )
        for a0 in ( 95.6, 108.2 ):
            x0 = _van_side_x( a0 + 1.8, 57.5 )
            F.box( model, xs * ( x0 + 0.05 ), xs * ( x0 + 0.7 ), -a0, -( a0 + 3.8 ), 56.6, 58.5, "rw_black" )
        # The mirror: an arm off the door's front corner and a tall black housing, its glass facing back and an
        # indicator in its outer face.
        xm = _van_side_x( 69.0, 57.0 )
        F.box( model, xs * ( xm - 0.6 ), xs * ( xm + 3.0 ), -66.8, -70.8, 55.0, 58.2, "rw_black" )
        F.box( model, xs * ( xm + 2.4 ), xs * ( xm + 9.2 ), -66.2, -71.6, 55.6, 70.4, "rw_black" )
        F.box( model, xs * ( xm + 2.8 ), xs * ( xm + 8.8 ), -71.6, -71.75, 56.4, 69.6, "rw_steel_grey" )
        F.box( model, xs * ( xm + 9.2 ), xs * ( xm + 9.3 ), -69.0, -71.4, 56.8, 58.8, "rw_yellow_paint" )
        # The tail lights' ends round the rear corners.
        for a0, a1 in ( ( 233.4, 234.3 ), ( 234.3, 235.0 ), ( 235.0, 235.4 ) ):
            for z0_, z1_ in ( ( 41.6, 52.0 ), ( 52.0, 56.0 ), ( 56.0, 60.2 ) ):
                side_patch( "rw_red_paint", xs, [ ( a0, z0_ ), ( a1, z0_ ), ( a1, z1_ ), ( a0, z1_ ) ], 0.12 )

    # Wipers on the windscreen's foot, the roof aerial.
    for x0, x1 in ( ( 3.0, -24.0 ), ( 31.0, 5.0 ) ):
        pa = [ ( x0, VAN_COWL + 2.4 ), ( x1, VAN_COWL + 8.5 ) ]
        rod( model, *[ F.p( x, -a, _van_top_z( a, x ) + 0.4 ) for x, a in pa ], 0.34, "rw_black", 4 )
    za = _van_top_z( 77.0, 10.0 )
    rod( model, F.p( -10.0, -77.0, za ), F.p( -10.0, -86.0, za + 14.0 ), 0.22, "rw_black", 4 )
    disc( model, "rw_black", F.p( -10.0, -77.0, za + 0.05 ), F.z, 1.2, sides=8 )

    # The nose: the bumper's face at a 0, and the grille and headlights on the fascia leaning back above it.
    def face( pnt, pts, lift ):
        _fpoly( model, F, pnt, [ ( x, lift, z ) for x, z in pts ], ( 0, 1, 0 ) )

    def nose( x, z, lift ):
        """ The point at ( x, z ) on the bumper's face, or up on the fascia, lift off it, in the frame's own
        coordinates. """
        if z <= _van_top_z( 0.0, x ):
            return ( x, lift, z )
        lo, hi = 0.0, 9.0
        for _ in range( 30 ):
            m = ( lo + hi ) / 2
            if _van_top_z( m, x ) < z:
                lo = m
            else:
                hi = m
        return ( x, -( lo + hi ) / 2 + lift, z + 0.45 * lift )

    def fascia( pnt, x0, x1, zlo, zhi, lift, step=1.5 ):
        """ A panel on the fascia from x0 to x1 between the heights zlo( x ) and zhi( x ), in strips. """
        n_ = max( 1, int( math.ceil( abs( x1 - x0 ) / step ) ) )
        xs_ = [ x0 + ( x1 - x0 ) * j / n_ for j in range( n_ + 1 ) ]
        for xa, xb in zip( xs_, xs_[1:] ):
            _fpoly( model, F, pnt, [ nose( xa, zlo( xa ), lift ), nose( xb, zlo( xb ), lift ),
                                     nose( xb, zhi( xb ), lift ), nose( xa, zhi( xa ), lift ) ], ( 0, 1, 0.5 ) )

    fx = lambda z: _van_side_x( 0.0, z )
    face( "rw_rubber", [ ( -fx( 12.5 ), 12.5 ), ( fx( 12.5 ), 12.5 ), ( fx( 25.6 ) - 0.2, 25.6 ),
                         ( -fx( 25.6 ) + 0.2, 25.6 ) ], 0.06 )
    face( "rw_black", [ ( -13.0, 13.6 ), ( 13.0, 13.6 ), ( 13.8, 18.0 ), ( -13.8, 18.0 ) ], 0.12 )
    for z in ( 14.8, 16.3 ):
        face( "rw_rubber", [ ( -12.8, z ), ( 12.8, z ), ( 12.8, z + 0.5 ), ( -12.8, z + 0.5 ) ], 0.18 )
    _plate( model, F, ( 0.0, 0.42, 21.5 ), ( 1, 0, 0 ), ( 0, 0, 1 ), ( 0, 1, 0 ), plate )
    for xs in ( 1.0, -1.0 ):
        face( "rw_black", [ ( xs * 24.6, 14.2 ), ( xs * 31.0, 14.2 ), ( xs * 31.4, 19.4 ), ( xs * 24.2, 19.4 ) ], 0.12 )
        disc( model, "rw_steel_grey", F.p( xs * 27.6, 0.2, 16.8 ), F.y, 1.55, sides=14 )
        disc( model, "rw_white_paint", F.p( xs * 27.6, 0.25, 16.8 ), F.y, 1.0, sides=14 )
    # The grille: four bars in a dark frame, leaning back with the fascia.
    gz0, gz1 = 27.6, 39.8
    gw = lambda z: 17.0 + 2.6 * ( z - gz0 ) / ( gz1 - gz0 )
    fascia( "rw_steel_dark", -gw( gz1 ), gw( gz1 ), lambda x: gz0 if abs( x ) <= gw( gz0 ) else
            gz0 + ( abs( x ) - gw( gz0 ) ) / 2.6 * ( gz1 - gz0 ), lambda x: gz1, 0.08 )
    gi = lambda z: gw( z ) - 1.0
    fascia( "rw_black", -gi( gz1 - 1.0 ), gi( gz1 - 1.0 ), lambda x: gz0 + 1.0 if abs( x ) <= gi( gz0 + 1.0 ) else
            gz0 + 1.0 + ( abs( x ) - gi( gz0 + 1.0 ) ) / 2.6 * ( gz1 - gz0 ), lambda x: gz1 - 1.0, 0.14 )
    for zb_ in ( 29.7, 32.2, 34.7, 37.2 ):
        half = gi( zb_ ) - 0.2
        fascia( "rw_steel_dark", -half, half, lambda x, zb_=zb_: zb_, lambda x, zb_=zb_: zb_ + 1.25, 0.32 )
    # The headlights: slim, rising to the corners, the running-light strip along their top and down their inner end.
    for xs in ( 1.0, -1.0 ):
        x0, x1 = 20.2, 36.9
        lo_ = lambda x: 32.0 + 3.0 * ( abs( x ) - x0 ) / ( x1 - x0 )
        hi_ = lambda x: 39.9 + 1.0 * ( abs( x ) - x0 ) / ( x1 - x0 )
        fascia( "rw_black", xs * ( x0 - 0.4 ), xs * ( x1 + 0.3 ), lambda x: lo_( x ) - 0.4, lambda x: hi_( x ) + 0.35,
                0.08 )
        fascia( "rw_window_dark", xs * x0, xs * x1, lo_, hi_, 0.14 )
        for c in ( 24.6, 30.4 ):
            fascia( "rw_steel_grey", xs * ( c - 2.2 ), xs * ( c + 2.2 ), lambda x: lo_( x ) + 1.2,
                    lambda x: hi_( x ) - 1.6, 0.2, 0.85 )
        fascia( "rw_lamp_cool", xs * ( x0 + 0.6 ), xs * ( x1 - 0.4 ), lambda x: hi_( x ) - 0.85,
                lambda x: hi_( x ) - 0.4, 0.24 )
        fascia( "rw_lamp_cool", xs * ( x0 + 0.6 ), xs * ( x0 + 1.05 ), lambda x: lo_( x ) + 0.4,
                lambda x: hi_( x ) - 0.4, 0.24, 0.45 )
    fascia( "rw_black", -33.0, 33.0, lambda x: 40.55, lambda x: 40.85, 0.06, 3.0 )     # the bonnet's shut line

    # The tail: the black bumper with its step and the plate, two doors with their glass, the lamps at the corners
    # and the high brake light.
    def back( pnt, pts, lift ):
        _fpoly( model, F, pnt, [ ( x, -L - lift, z ) for x, z in pts ], ( 0, -1, 0 ) )

    bx = lambda z: _van_side_x( L, z )
    zr = _van_top_z( L, 0.0 )
    back( "rw_rubber", [ ( -bx( 13.0 ), 13.0 ), ( bx( 13.0 ), 13.0 ), ( bx( 24.4 ) - 0.2, 24.4 ),
                         ( -bx( 24.4 ) + 0.2, 24.4 ) ], 0.06 )
    F.box( model, -18.0, 18.0, -L, -( L + 2.6 ), 22.6, 24.2, { "default": "rw_steel_grey", "bottom": "rw_black" } )
    _plate( model, F, ( 0.0, -L - 0.42, 17.6 ), ( -1, 0, 0 ), ( 0, 0, 1 ), ( 0, -1, 0 ), plate )
    for xs in ( 1.0, -1.0 ):
        back( "rw_black", [ ( xs * 30.6, 27.6 ), ( xs * 35.6, 27.6 ), ( xs * 35.6, 60.8 ), ( xs * 30.6, 60.8 ) ], 0.06 )
        for z0_, z1_, lamp in ( ( 28.2, 35.6, "rw_white_paint" ), ( 35.6, 41.6, "rw_yellow_paint" ),
                                ( 41.6, 60.2, "rw_red_paint" ) ):
            back( lamp, [ ( xs * 31.1, z0_ ), ( xs * 35.1, z0_ ), ( xs * 35.1, z1_ ), ( xs * 31.1, z1_ ) ], 0.12 )
        back( "rw_black", [ ( xs * 3.0, 62.5 ), ( xs * 27.5, 62.5 ), ( xs * 27.5, 85.5 ), ( xs * 3.0, 85.5 ) ], 0.06 )
        back( "rw_window_dark", [ ( xs * 3.8, 63.3 ), ( xs * 26.7, 63.3 ), ( xs * 26.7, 84.7 ), ( xs * 3.8, 84.7 ) ],
              0.1 )
    back( "rw_black", [ ( -0.18, 24.6 ), ( 0.18, 24.6 ), ( 0.18, zr - 3.0 ), ( -0.18, zr - 3.0 ) ], 0.08 )
    back( "rw_black", [ ( -bx( 24.6 ) + 1.0, 24.6 ), ( bx( 24.6 ) - 1.0, 24.6 ), ( bx( 25.0 ) - 1.0, 25.0 ),
                        ( -bx( 25.0 ) + 1.0, 25.0 ) ], 0.08 )
    F.box( model, -7.4, -2.0, -L, -( L + 0.7 ), 54.2, 56.0, "rw_black" )
    back( "rw_red_paint", [ ( -8.0, zr - 2.6 ), ( 8.0, zr - 2.6 ), ( 8.0, zr - 1.4 ), ( -8.0, zr - 1.4 ) ], 0.1 )

    # Collision: the body to the bonnet's height, and the box behind the windscreen.
    F.collide( model, -VAN_W, VAN_W, -L, 0.0, 0.0, 47.6, "metal" )
    F.collide( model, -VAN_W + 1.0, VAN_W - 1.0, -L, -52.0, 47.6, 92.7, "metal" )


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
        ( "van", lambda m: van( m, -1280.0, -60.0, "+n", "rw_car_white" ) ),
        ( "suv", lambda m: suv( m, -1380.0, -80.0, "+n", "rw_car_grey" ) ),
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
