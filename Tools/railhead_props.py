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
  the floor (fence feet) none. Atlas faces get explicit UVs from railhead_materials.rect_uv() (the
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
    """ An atlas entry's ( u0, v0, u1, v1 ) from railhead_materials (the kiosk's from railhead_kiosk_art), or the whole
    texture while it isn't there. """
    try:
        if atlas == "rw_kiosk":
            import railhead_kiosk_art as KA
            return KA.rect_uv( name )
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
    upv = upv - nrm * np.dot( upv, nrm )
    if np.linalg.norm( upv ) < 1e-8:
        # A horizontal disc's normal is parallel to the default up vector.
        # Pick a perpendicular axis or every cap vertex collapses to its centre.
        ref = np.array( ( 0.0, 1.0, 0.0 ) ) if abs( nrm[1] ) < 0.9 else np.array( ( 1.0, 0.0, 0.0 ) )
        upv = ref - nrm * np.dot( ref, nrm )
    upv = _unit( upv )
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
    if kind == "concrete" and 310 < n < 880 and rail_z == -30:
        import railhead_buffer as detail
        detail.bevel_box( model, Frame( ( 0, 0, 0 ), ( 0, 1 ) ),
                          ( -e1, n - width / 2, top - height ), ( -e0, n + width / 2, top ), paint, 0.45 )
        detail.track_fittings( model, e0, e1, n, rail_z, rails )
        detail.sleeper_shoulders( model, e0, e1, n, width, top )
    else:
        model.box( ( e0, n - width / 2, top - height ), ( e1, n + width / 2, top ), paint, skip=( "-z", ) )
        if kind == "concrete" and rail_z == -30 and -1340 < n <= 310 and rails:
            try:
                import railhead_buffer as detail
                detail.track_fittings_lod( model, n, rail_z, rails )
                detail.sleeper_shoulders( model, e0, e1, n, width, top )
            except Exception:
                pass
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
    if sleepers == "concrete" and rail_z == -30.0:
        try:
            import railhead_buffer as detail
            detail.crib_band( model, e, lo, hi, rail_z )
        except Exception as error:
            print( f"railhead_buffer.crib_band failed: {error}" )
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
    import railhead_buffer
    railhead_buffer.buffer_stop( model, e, n, facing, rail_z )


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
    model.cylinder( ( em, n ), 2.76, ground + 5, top - 1, { "side": "rw_steel_grey", "top": "rw_steel_grey" },
                    sides=16 )
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
    # The mast plate's bracket, behind the plate.
    f.box( model, -4.4, 4.4, 2.8, 3.55, rail_z + 69, rail_z + 69 + 23.6, "rw_steel_dark" )
    try:
        import railhead_ohl as OHL
        OHL.signal_dressing( model, f, rail_z, ground, top, zc )
    except Exception as error:
        print( f"railhead_ohl.signal_dressing failed: {error}" )
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


def _h_mast( model, e, n, ground, top, toward=None, plate=0 ):
    """ An HEB 200 mast (200 x 200 mm), its web across the track, on a concrete foundation (railhead_ohl's, with its
    number plate and warning triangle facing toward, the sign of e towards the track; this plain one stands in). """
    try:
        import railhead_ohl as OHL
        OHL.h_mast( model, e, n, ground, top, toward, plate )
        return
    except Exception as error:
        print( f"railhead_ohl.h_mast failed: {error}" )
    model.box( ( e - 12, n - 12, ground - 2 ), ( e + 12, n + 12, ground + 6 ), "rw_concrete", skip=( "-z", ) )
    paint = "rw_steel_grey"
    for side in ( -1, 1 ):
        model.box( ( e + side * 3.95 - 0.3, n - 3.95, ground + 6 ), ( e + side * 3.95 + 0.3, n + 3.95, top ), paint,
                   skip=( "-z", ) )
    model.box( ( e - 3.65, n - 0.2, ground + 6 ), ( e + 3.65, n + 0.2, top ), paint, skip=( "-z", ) )


def _insulator( model, a, b ):
    """ A composite insulator along a..b: a rod with its sheds (railhead_ohl's; this one stands in). """
    try:
        import railhead_ohl as OHL
        OHL.insulator( model, a, b )
        return
    except Exception as error:
        print( f"railhead_ohl.insulator failed: {error}" )
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
    _h_mast( model, e_mast, n, ground, top, toward, int( abs( n ) // 500 ) )
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
    try:
        import railhead_ohl as OHL
        OHL.y_hanger( model, ew, n, mz )
    except Exception:
        pass
    _registration( model, e_track, n, bottom, ew, wz, toward )


def portal( model, e0, e1, n, rail_z, tracks, wire_height=WIRE_HEIGHT, system_height=SYSTEM_HEIGHT, anchor=False ):
    """ A portal across several tracks: HEB masts at e0 and e1 and a 600 mm lattice girder between them over the
    wires, with a drop tube over each track. tracks: e of each track, or ( e, stagger ). anchor: the wires' runs end
    here, so both masts carry tension weights on their outer sides. Metal collision on the masts. """
    ground = rail_z - 7.0
    wz, mz = rail_z + wire_height, rail_z + wire_height + system_height
    zb, zt = mz + 20.0, mz + 44.0
    for e, other in ( ( e0, e1 ), ( e1, e0 ) ):
        toward = 1.0 if other > e else -1.0
        _h_mast( model, e, n, ground, zt, toward, int( abs( n ) // 500 ) )
        if anchor:
            try:
                import railhead_ohl as OHL
                OHL.tension_weights( model, e, n, ground, zt, toward )
            except Exception as error:
                print( f"railhead_ohl.tension_weights failed: {error}" )
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
    # The clamp plate on the roof's steel, its four bolts, and the drop under it.
    model.box( ( e_track - 4, n - 3, z_top - 1.0 ), ( e_track + 4, n + 3, z_top ), "rw_steel_dark" )
    for dx in ( -3.0, 3.0 ):
        for dy in ( -2.0, 2.0 ):
            rod( model, ( e_track + dx, n + dy, z_top - 1.0 ), ( e_track + dx, n + dy, z_top - 1.6 ), 0.45, "rw_steel_grey",
                 6, caps=( False, True ) )
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
    """ A wheelset at depth a: wheels of radius r (their treads on the rails, flanges inside) on their axle
    (railhead_running_gear's, with this simpler one as its stand-in). """
    try:
        import railhead_running_gear as RG
        RG.wheelset( model, F, a, r, discs=False )
        return
    except Exception as error:
        print( f"railhead_running_gear.wheelset failed: {error}" )
    for xs in ( 1.0, -1.0 ):
        rod( model, F.p( xs * 27.8, -a, r ), F.p( xs * 32.1, -a, r ), r, "rw_bogie", 12,
             caps=( False, True ) )
        rod( model, F.p( xs * 26.8, -a, r ), F.p( xs * 27.8, -a, r ), r + 1.1, "rw_bogie", 12,
             caps=( True, False ) )
    rod( model, F.p( -26.8, -a, r ), F.p( 26.8, -a, r ), 3.3, "rw_bogie", 6 )


def _bogie( model, F, a, wheelbase, r, motor=False ):
    """ A two-axle bogie centred at depth a: its wheelsets, side frames with axle boxes and springs outside the wheels,
    and the transom; a traction motor between the axles if motor (railhead_running_gear's H-frame bogie, with this
    simpler one as its stand-in). """
    try:
        import railhead_running_gear as RG
        RG.bogie( model, F, a, wheelbase, r, motor )
        return
    except Exception as error:
        print( f"railhead_running_gear.bogie failed: {error}" )
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
# (or the body paint) with grey belts and roof, glazed saloons, and the reference's operator and class markings.

EMU_CAR = 763.0             # a car from its cab's coupler face (or the gangway's) to its inner end
EMU_W = 56.7
EMU_ROOF = 182.3
EMU_FLOOR = 30.0
EMU_GAP = 14.0              # the gangway between the cars
EMU_SKIRT = 19.0            # the mid-level ends' underframe
EMU_LOW = 13.0              # the lower deck's underside, between the bogies
EMU_CUT = 42.0              # the bogie cut-outs' top
EMU_SIDE_TOP = 158.0        # upright glazed saloon sides, then the rounded shoulder
EMU_UPPER = [ ( EMU_W, EMU_SIDE_TOP ), ( 56.4, 162.0 ), ( 55.5, 166.0 ), ( 53.5, 170.0 ), ( 50.0, 173.0 ),
              ( 44.5, 176.0 ), ( 36.0, 179.0 ), ( 25.0, 180.8 ), ( 12.0, 182.0 ), ( 0.0, EMU_ROOF ) ]
EMU_ROOF_LINE = 166.0       # thin grey roof above the red shoulder
EMU_STRIPE = ( 18.0, 29.0 )
EMU_NOSE = 112.0            # the cab's loft reaches this far behind the coupler face
EMU_WHEELBASE = 98.0        # 2.5 m bogies
EMU_WHEEL = 18.1            # 920 mm wheels
# Along a car, behind its cab's coupler face: the bogies' centres, the doors' openings and the decks.
EMU_BOGIES = ( 175.0, 670.0 )
EMU_DOORS = ( 232.0, 564.0 )                # each opening 64 long, with 32-inch plug-door leaves
EMU_DOOR_TOP = 130.0
EMU_DECKS = ( 296.0, 564.0 )                # the double-deck part
EMU_LOWER_WIN = ( 48.0, 87.0 )              # the lower deck's windows, z
EMU_UPPER_WIN = ( 123.0, 154.0 )            # the upper deck's
EMU_MID_WIN = ( 60.0, 98.0 )                # the mid-level ends'
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
EMU_SCREEN_WRAP = 4                         # the glazing wraps this many arc steps (of 15 degrees) round the corners
EMU_ROOF_PAINT = "rw_emu_roof"              # the roof's light grey, sooted from the wire (railhead_prop_materials)
EMU_SCREEN_GLASS = "rw_emu_screen"          # the windscreen's and display's glossy black glass (railhead_prop_materials)
EMU_CAB_GLASS = "rw_emu_cab_glass"          # the windscreen's tinted glass, the cab behind it (railhead_prop_materials)


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
    """Rounded aperture, recessed glazing and a three-dimensional rubber seal."""
    import railhead_train as T
    T.window(car, xs, d0, d1, z0, z1, car.body)


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
    sd = xs * car.s               # +1 when the car's d runs to the viewer's right
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
            return EMU_ROOF_PAINT if z > EMU_ROOF_LINE else body
        pillar = i in ( n_face, n_face + 1 )             # the A-pillar: the corner's first 30 degrees, in body colour
        if front and EMU_SCREEN[1] < z <= EMU_VISOR:
            # The display's glass over the flat of the face only; the pillars carry on up to the roof.
            return body if pillar or i >= n_face + 2 else EMU_SCREEN_GLASS
        if front and EMU_SCREEN[0] < z <= EMU_SCREEN[1]:
            # The windscreen across the flat of the face, a body-colour A-pillar on the corner's first 30 degrees,
            # then the quarter light round to 45 degrees. Glossy black glass, so it reflects the shed.
            if pillar:
                return body
            return EMU_CAB_GLASS
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

    # The black rubber gaskets round the glass: a 3 in (80 mm) surround under the windscreen and over it, and up both
    # its edges, round the quarter lights, all following the cab's curve (the corners' angle, not a fixed x).
    def x_at( z, where ):
        """ where: ( "flat", inches back from the corner's start ) or ( "arc", degrees round the corner ). """
        W = _emu_width( z )
        f_, rc_ = _emu_face_at( z )
        kind, v = where
        return W - rc_ - v if kind == "flat" else W - rc_ + rc_ * math.sin( math.radians( v ) )

    def strip( paint, wa, wb, z0, z1, off=0.24 ):
        zs_ = sorted( { z0, z1, *[ r[0] for r in EMU_FACE if z0 < r[0] < z1 ] } )
        for xs in ( 1.0, -1.0 ):
            for za, zb in zip( zs_, zs_[1:] ):
                pa = [ ( x_at( za, wa ), za ), ( x_at( za, wb ), za ), ( x_at( zb, wb ), zb ), ( x_at( zb, wa ), zb ) ]
                xm = sum( q[0] for q in pa ) / 4
                _, ( nx, nd ) = _emu_surface( xm, ( za + zb ) / 2 )
                pts = [ on_face( xs * x, z_, off ) for x, z_ in pa ]
                car.poly( paint, pts, ( xs * nx, nd, 0 ) )

    S0, S1 = EMU_SCREEN
    patch( "rw_rubber", -34.6, 34.6, S0 - 1.4, S0 + 1.6, 0.22 )
    patch( "rw_rubber", -31.0, 31.0, S1 - 1.6, S1 + 0.6, 0.22 )
    strip( "rw_rubber", ( "flat", 1.6 ), ( "arc", 2.0 ), S0 - 1.4, S1 + 0.6 )
    strip( "rw_rubber", ( "arc", 28.0 ), ( "arc", 31.0 ), S0 - 1.4, S1 + 0.6 )
    strip( "rw_rubber", ( "arc", 43.5 ), ( "arc", 46.5 ), S0 - 1.4, S1 + 0.6 )
    strip( "rw_rubber", ( "arc", 28.0 ), ( "arc", 46.5 ), S0 - 1.4, S0 + 1.4 )
    strip( "rw_rubber", ( "arc", 28.0 ), ( "arc", 46.5 ), S1 - 1.4, S1 + 0.6 )
    # The display's glass under the visor gets its own thin frame where it meets the pillars.
    strip( "rw_rubber", ( "flat", 1.2 ), ( "arc", 1.5 ), S1, EMU_VISOR - 0.5 )

    # The windscreen's wiper, parked along the glass's foot, its arm's pivot and motor cover.
    car.rod( on_face( 3.0, 101.6, 0.5 ), on_face( -27.0, 102.0, 0.5 ), 0.42, "rw_black", 4 )
    car.rod( on_face( 3.0, 101.6, 0.4 ), on_face( -6.0, 101.8, 0.95 ), 0.55, "rw_black", 4 )
    car.rod( on_face( 3.0, 101.5, 0.3 ), on_face( 3.0, 100.0, 1.6 ), 1.0, "rw_black", 6, caps=( True, True ) )
    _emu_display( car, destination, 159.0 )
    import railhead_vehicle_kit as VK

    def face_frame( x, z, off ):
        """ The world point on the face at ( x, z ) off out of it, and the face's outward normal there. """
        _, ( nx, nd ) = _emu_surface( abs( x ), z )
        p = np.asarray( car.p( *on_face( x, z, off ) ), float )
        normal = car.F.x * ( nx if x >= 0 else -nx ) - car.F.y * car.s * nd
        return p, _unit( normal )

    def face_lamp( x, z, r, emitter, depth=1.1, proud=1.3 ):
        """ A lamp standing proud of the cluster's field: its satin barrel, a 16-sided chrome reflector bowl sunk in
        it, the emitter at its foot and a clear lens over it. """
        base, n = face_frame( x, z, 0.25 )
        rim = base + n * proud
        rod( car.model, base, rim, r + 0.3, "rw_lamp_field", 16 )
        VK.bowl_lamp( car.model, rim, n, r, depth=depth, sides=16, emitter=emitter, rim_paint="rw_steel_dark",
                      rim=0.3 )

    # The top headlight behind the glass's head, in its own housing on the cab's ceiling.
    f147, _ = _emu_surface( 0.0, 147.5 )
    car.box( -5.2, 5.2, f147 + 2.9, f147 + 7.0, 143.0, 151.0, "rw_lamp_field" )
    tl = np.asarray( car.p( 0.0, f147 + 2.85, 147.5 ), float )
    VK.bowl_lamp( car.model, tl, car.F.y * car.s, 3.0, depth=1.2, emitter="rw_train_headlamp",
                  rim_paint="rw_steel_dark", rim=0.5 )
    # The clusters as on a current double-deck unit: a satin grey field 55 x 30 cm in a body-colour bezel, two
    # 170 mm headlights side by side, a 120 mm marker light over the outer one and the red tail light under it.
    for xs in ( 1.0, -1.0 ):
        patch( body, xs * 24.0, xs * 48.6, 77.8, 91.4, 0.18, step=0.6 )
        patch( "rw_rubber", xs * 24.4, xs * 48.2, 78.2, 91.0, 0.22, step=0.6 )
        patch( "rw_lamp_field", xs * 24.8, xs * 47.8, 78.6, 90.6, 0.26, step=0.6 )
        for x in ( 29.6, 37.4 ):
            face_lamp( xs * x, 83.6, 3.35, "rw_train_headlamp" )
        face_lamp( xs * 43.9, 87.3, 2.36, "rw_train_headlamp", depth=0.8, proud=1.0 )
        face_lamp( xs * 43.9, 81.3, 1.3, "rw_train_red", depth=0.5, proud=0.8 )
        # The UIC jumper socket's hinged cover beside the coupler pocket, and its cable gland.
        p0 = on_face( xs * 20.5, 58.0, 0.0 )
        car.box( min( xs * 17.5, xs * 23.5 ), max( xs * 17.5, xs * 23.5 ), p0[1] - 1.6, p0[1] - 0.2, 55.0, 61.5,
                 "rw_steel_dark" )
        car.rod( ( xs * 17.6, p0[1] - 1.5, 61.6 ), ( xs * 23.4, p0[1] - 1.5, 61.6 ), 0.35, "rw_steel_grey", 6 )
    # Grime: road and brake dust thrown up the face over the coupler, and dirty water run down from the
    # windscreen's foot, ragged streaks on the paint (alpha tested).
    def grime( x0, x1, z0, z1, off, down ):
        n_ = max( 1, int( math.ceil( ( x1 - x0 ) / 2.5 ) ) )
        xs_ = [ x0 + ( x1 - x0 ) * j / n_ for j in range( n_ + 1 ) ]
        zs_ = sorted( { z0, z1, *[ r[0] for r in EMU_FACE if z0 < r[0] < z1 ] } )
        for za, zb in zip( zs_, zs_[1:] ):
            for xa, xb in zip( xs_, xs_[1:] ):
                xm = ( xa + xb ) / 2
                _, ( nx, nd ) = _emu_surface( abs( xm ), ( za + zb ) / 2 )
                uv = []
                pts = []
                for x_, z_ in ( ( xa, za ), ( xb, za ), ( xb, zb ), ( xa, zb ) ):
                    px, pd, pz = on_face( x_, z_, off )
                    pts.append( ( px, -car.a( pd ), pz ) )
                    v = ( z_ - z0 ) / ( z1 - z0 )
                    uv.append( ( ( x_ - x0 ) / ( x1 - x0 ) * 2.2, v if down else 1.0 - v ) )
                n_local = car.local( ( nx if xm >= 0 else -nx, nd, 0 ) )
                _fpoly( car.model, car.F, "rw_emu_grime", pts, n_local, uv=uv )

    grime( -33.0, 33.0, 88.0, 98.4, 0.2, True )
    grime( -36.0, 36.0, 52.0, 70.0, 0.2, False )
    for xs in ( 1.0, -1.0 ):
        grime( xs * 33.0, xs * 50.0, 30.5, 46.0, 0.21, False )
    _emu_cab_interior( car )
    # Grilles either side of the coupler pocket, the pocket and the automatic coupler in it.
    for xs in ( 1.0, -1.0 ):
        patch( "rw_black", xs * 13.0, xs * 31.0, 31.0, 51.0 )
        for z in ( 34.0, 38.0, 42.0, 46.0, 49.0 ):
            car.rod( on_face( xs * 14.0, z, 0.7 ), on_face( xs * 30.0, z, 0.7 ), 0.6, "rw_steel_dark", 4 )
    patch( "rw_black", -9.5, 9.5, 22.0, 52.0 )
    f, _ = _emu_surface( 0.0, 38.0 )
    # Cast automatic coupling head: chamfered steel body, two mating fittings,
    # recessed receiver and locking pin. No white square plate.
    outline = _chamfered(-7.6,7.6,31.0,45.0,2.0)
    front = [(x,-3.0,z) for x,z in outline]
    back = [(x*0.88,6.0,38.0+(z-38.0)*0.88) for x,z in outline]
    car.poly("rw_coupler_cast",front,(0,-1,0))
    for k in range(len(front)):
        j=(k+1)%len(front)
        car.poly("rw_coupler_cast",[front[k],back[k],back[j],front[j]],
                 ((front[k][0]+front[j][0])/2,0,(front[k][2]+front[j][2])/2-38))
    car.rod((0,6,38),(0,f,38),3.0,"rw_bogie",16,caps=(True,True))
    car.box(-9.0,9.0,5.0,9.0,29.5,32.0,"rw_steel_dark")
    car.box(-8.5,8.5,-2.5,4.5,45.0,47.2,"rw_coupler_cast")
    # A ring with a deep dark throat on one side, projecting mating cone opposite.
    for x in (-3.6,3.6):
        car.rod((x,-3.2,38),(x,-5.0,38),2.55,"rw_coupler_cast",24,caps=(True,True))
        car.disc("rw_black",(x,-5.05,38),(0,-1,0),1.8,24)
        if x>0:
            car.rod((x,-5.1,38),(x,-7.0,38),1.3,"rw_coupler_cast",16,caps=(True,True))
            car.disc("rw_steel_dark",(x,-7.03,38),(0,-1,0),0.65,16)
    for x in (-5.6,5.6):
        for z in (33.0,43.0):
            car.rod((x,-3.1,z),(x,-3.65,z),0.52,"rw_steel_dark",6,caps=(True,True))
    car.rod((-2,-4.0,32),(2,-4.0,32),0.7,"rw_steel_dark",12,caps=(True,True))
    # Smooth sagging brake hoses with metal unions, rather than angular wire loops.
    for xs in ( 1.0, -1.0 ):
        controls=np.array([(xs*7.0,-2.0,33.0),(xs*15.0,-5.0,10.0),
                           (xs*2.0,-5.0,14.0),(xs*3.0,8.0,30.0)])
        hose=[]
        for k in range(25):
            t=k/24
            hose.append(tuple((1-t)**3*controls[0]+3*(1-t)**2*t*controls[1]+
                              3*(1-t)*t*t*controls[2]+t**3*controls[3]))
        for p, q in zip( hose, hose[1:] ):
            car.rod( p, q, 0.62, "rw_rubber", 10 )
        car.rod(hose[0],hose[2],1.0,"rw_coupler_cast",12,caps=(True,True))
        car.rod(hose[-3],hose[-1],1.0,"rw_coupler_cast",12,caps=(True,True))
    # The obstacle deflector under the nose, raked back, and the cab's underframe behind it.
    car.poly( "rw_train_grey", [ ( -44.0, 18.0, 19.0 ), ( 44.0, 18.0, 19.0 ), ( 40.0, 13.0, 5.0 ),
                                 ( -40.0, 13.0, 5.0 ) ], ( 0, -1, 0.3 ) )
    for x in ( -30.0, -10.0, 10.0, 30.0 ):         # its stiffening ribs
        car.poly( "rw_steel_dark", [ ( x - 0.6, 17.85, 18.4 ), ( x + 0.6, 17.85, 18.4 ), ( x + 0.6, 12.85, 5.6 ),
                                     ( x - 0.6, 12.85, 5.6 ) ], ( 0, -1, 0.3 ) )
    car.poly( "rw_train_dark", [ ( -40.0, 13.0, 5.0 ), ( 40.0, 13.0, 5.0 ), ( 40.0, 30.0, 5.0 ),
                                 ( -40.0, 30.0, 5.0 ) ], ( 0, 0, -1 ) )
    for xs in ( 1.0, -1.0 ):
        car.poly( "rw_train_dark", [ ( xs * 44.0, 18.0, 19.0 ), ( xs * 40.0, 13.0, 5.0 ), ( xs * 40.0, 30.0, 5.0 ),
                                     ( xs * 44.0, 30.0, 19.0 ) ], ( xs, 0, 0 ) )
    car.box( -44.0, 44.0, 30.0, EMU_NOSE, 10.0, 19.0, "rw_bogie", skip=( "top", ) )


def _emu_cab_interior( car ):
    """ The driver's cab behind the tinted windscreen, as it reads from the platform: a full-width dark grey desk with
    two display housings, the driver's seat with its headrest left of centre, a pale grey rear bulkhead with its door,
    pale side walls, a dim ceiling and a dark floor. Visual only; it closes the nose so nothing else shows through. """
    import railhead_buffer as B
    face = lambda z: _emu_face_at( z )[0]
    xw = EMU_W - 4.5
    zf, zc, db = 87.0, 150.5, 98.0
    # Floor, ceiling and the rear bulkhead.
    front = lambda z: [ ( -xw, face( z ) + 15.0 ), ( -30.0, face( z ) + 4.0 ), ( 30.0, face( z ) + 4.0 ),
                        ( xw, face( z ) + 15.0 ), ( xw, db ), ( -xw, db ) ]
    car.poly( "rw_cab_desk", [ ( x, d, zf ) for x, d in front( zf ) ], ( 0, 0, 1 ) )
    car.poly( "rw_cab_ceiling", [ ( x, d, zc ) for x, d in front( zc ) ], ( 0, 0, -1 ) )
    for x0 in ( -32.0, 32.0 ):      # the ceiling's two light panels
        car.poly( "rw_cab_screen", [ ( x0 - 7.0, 62.0, zc - 0.1 ), ( x0 + 7.0, 62.0, zc - 0.1 ), ( x0 + 7.0, 86.0, zc - 0.1 ),
                                     ( x0 - 7.0, 86.0, zc - 0.1 ) ], ( 0, 0, -1 ) )
    car.poly( "rw_cab_wall", [ ( -xw, db, zf ), ( xw, db, zf ), ( xw, db, zc ), ( -xw, db, zc ) ], ( 0, -1, 0 ) )
    car.poly( "rw_steel_grey", [ ( 4.0, db - 0.1, zf ), ( 26.0, db - 0.1, zf ), ( 26.0, db - 0.1, 146.0 ),
                                 ( 4.0, db - 0.1, 146.0 ) ], ( 0, -1, 0 ) )
    car.poly( "rw_emu_screen", [ ( 8.0, db - 0.2, 122.0 ), ( 22.0, db - 0.2, 122.0 ), ( 22.0, db - 0.2, 140.0 ),
                                 ( 8.0, db - 0.2, 140.0 ) ], ( 0, -1, 0 ) )
    car.rod( ( 23.5, db - 0.4, 112.0 ), ( 23.5, db - 2.2, 112.0 ), 0.5, "rw_steel_dark", 6 )
    car.rod( ( 23.5, db - 2.2, 112.0 ), ( 19.5, db - 2.2, 112.0 ), 0.45, "rw_steel_dark", 6 )
    # The side walls, their front edges kept behind the curved nose.
    for xs in ( 1.0, -1.0 ):
        edge = [ ( face( z ) + 15.0, z ) for z in ( zf, 100.0, 112.0, 126.0, 140.0, zc ) ]
        car.poly( "rw_cab_wall", [ ( xs * xw, d, z ) for d, z in edge ] + [ ( xs * xw, db, zc ), ( xs * xw, db, zf ) ],
                  ( -xs, 0, 0 ) )
    # The desk: a full-width console under the windscreen's foot, its top sloping to the driver.
    d0 = face( 112.0 ) + 7.0
    prof = [ ( d0, 96.0 ), ( d0, 108.0 ), ( d0 + 6.0, 111.5 ), ( d0 + 22.0, 108.5 ), ( d0 + 24.0, 104.0 ),
             ( d0 + 21.0, 96.0 ) ]
    xd = EMU_W - 13.0
    for ( pd, pz ), ( qd, qz ) in zip( prof, prof[1:] ):
        car.poly( "rw_cab_desk", [ ( -xd, pd, pz ), ( xd, pd, pz ), ( xd, qd, qz ), ( -xd, qd, qz ) ],
                  ( 0, -( qz - pz ), qd - pd ) )
    for xs in ( 1.0, -1.0 ):
        car.poly( "rw_cab_desk", [ ( xs * xd, d, z ) for d, z in prof ], ( xs, 0, 0 ) )
    # Two display housings on the desk, leaning back towards the driver, their screens lit dimly.
    for xc in ( -22.0, 2.0 ):
        lo = ( xc - 8.0, -car.a( d0 + 9.0 ), 109.5 )
        hi = ( xc + 8.0, -car.a( d0 + 6.0 ), 119.5 )
        B.bevel_box( car.model, car.F, ( lo[0], min( lo[1], hi[1] ), lo[2] ), ( hi[0], max( lo[1], hi[1] ), hi[2] ),
                     "rw_cab_desk", bevel=0.6 )
        car.poly( "rw_cab_screen", [ ( xc - 7.0, d0 + 9.1, 110.5 ), ( xc + 7.0, d0 + 9.1, 110.5 ),
                                     ( xc + 7.0, d0 + 9.1, 118.5 ), ( xc - 7.0, d0 + 9.1, 118.5 ) ], ( 0, 1, 0 ) )
    # The driver's seat: a pedestal, the cushion, the high back and its headrest, the armrests.
    sx, sd = -20.0, d0 + 38.0
    car.rod( ( sx, sd, zf ), ( sx, sd, 101.0 ), 2.2, "rw_steel_dark", 10 )
    for lo, hi, bev in ( ( ( sx - 10.0, sd - 9.0, 101.0 ), ( sx + 10.0, sd + 9.0, 106.0 ), 1.6 ),
                         ( ( sx - 10.0, sd + 8.0, 105.0 ), ( sx + 10.0, sd + 12.0, 131.0 ), 1.6 ),
                         ( ( sx - 5.0, sd + 8.4, 132.0 ), ( sx + 5.0, sd + 11.6, 139.0 ), 1.2 ),
                         ( ( sx - 12.0, sd - 4.0, 109.0 ), ( sx - 10.2, sd + 8.0, 111.0 ), 0.5 ),
                         ( ( sx + 10.2, sd - 4.0, 109.0 ), ( sx + 12.0, sd + 8.0, 111.0 ), 0.5 ) ):
        a_lo, a_hi = -car.a( lo[1] ), -car.a( hi[1] )
        B.bevel_box( car.model, car.F, ( lo[0], min( a_lo, a_hi ), lo[2] ), ( hi[0], max( a_lo, a_hi ), hi[2] ),
                     "rw_cab_seat", bevel=bev )


def _emu_car( car, body, platform_xs, doors_open, cab, destination, roof="ac" ):
    """ One car: its cab (cab True) or its front end at the gangway, two bogies, the mid-level ends, the doors and
    the two decks, windows, roof and collision. platform_xs: the frame x sign of the side whose doors stand open.
    roof: "ac" for an air-conditioning unit over the inner end, else nothing (the pantograph goes there). """
    import railhead_train as T
    F, model = car.F, car.model
    car.body = body
    start = EMU_NOSE if cab else 0.0
    end = EMU_CAR
    zones = [ ( c - EMU_WHEELBASE / 2 - 13.0, c + EMU_WHEELBASE / 2 + 13.0 ) for c in EMU_BOGIES ]
    doors = [ ( d, d + 64.0 ) for d in EMU_DOORS ]
    windows = [(w0, w1, *height) for w0, w1 in ((324.0, 380.0), (390.0, 446.0), (456.0, 512.0))
               for height in (EMU_LOWER_WIN, EMU_UPPER_WIN)]
    windows += [(w0, w1, *EMU_MID_WIN) for w0, w1 in
                (((696.0, 752.0), (124.0, 180.0)) if cab else ((696.0, 752.0), (20.0, 80.0), (88.0, 180.0)))]
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
                                                          ( EMU_STRIPE[1], 146.0, body ),
                                                          ( 146.0, 151.0, "rw_train_white" ),
                                                          ( 151.0, EMU_SIDE_TOP, body ) )
                         if z1 > zb ]
    for xs in ( 1.0, -1.0 ):
        open_side = doors_open and xs == platform_xs
        for d0, d1, zb in pieces:
            gaps = [ ( g0, g1, EMU_FLOOR, EMU_DOOR_TOP ) for g0, g1 in doors ]
            gaps += [(w0 - 1.7, w1 + 1.7, z0 - 1.7, z1 + 1.7) for w0, w1, z0, z1 in windows]
            a0, a1 = car.span( d0, d1 )
            _banded_side( model, F, xs, EMU_W, a0, a1, [ ( max( z0, zb ), z1, p ) for z0, z1, p in bands( zb ) ],
                          [ (*car.span(g0, g1), z0, z1) for g0, g1, z0, z1 in gaps ] )
        for d0, d1 in doors:
            T.doorway(car, xs, d0, d1, open_side)
        # Windows: the lower and upper decks' between the doors, the mid-level ends' over the bogies.
        for w0, w1, z0, z1 in windows:
            _emu_window(car, xs, w0, w1, z0, z1)
        if cab:      # the cab's side window, its front edge leaning with the windscreen
            car.poly( "rw_black", [ ( xs * ( EMU_W + 0.08 ), d, z ) for d, z in
                                    ( ( 62.0, 104.6 ), ( 106.4, 104.6 ), ( 106.4, 145.4 ), ( 80.0, 145.4 ) ) ],
                      ( xs, 0, 0 ) )
            car.poly( "rw_window_dark", [ ( xs * ( EMU_W + 0.16 ), d, z ) for d, z in
                                          ( ( 65.0, 106.0 ), ( 105.0, 106.0 ), ( 105.0, 144.0 ), ( 82.0, 144.0 ) ) ],
                      ( xs, 0, 0 ) )
            # The driver's drop window in the rear half: its aluminium frame, the sash's top rail half way down (it's
            # dropped a hand's width), the grab handle beside it and the rear-view camera's arm over it.
            xw = xs * ( EMU_W + 0.3 )
            for p_, q_ in ( ( ( 86.0, 106.4 ), ( 104.6, 106.4 ) ), ( ( 104.6, 106.4 ), ( 104.6, 143.6 ) ),
                            ( ( 104.6, 143.6 ), ( 86.0, 143.6 ) ), ( ( 86.0, 143.6 ), ( 86.0, 106.4 ) ),
                            ( ( 86.0, 136.0 ), ( 104.6, 136.0 ) ) ):
                car.rod( ( xw, p_[0], p_[1] ), ( xw, q_[0], q_[1] ), 0.32, "rw_alu_brushed", 6 )
            car.rod( ( xs * ( EMU_W + 0.9 ), 108.8, 112.0 ), ( xs * ( EMU_W + 0.9 ), 108.8, 136.0 ), 0.45, "rw_steel_grey", 8 )
            for z_ in ( 112.0, 136.0 ):
                car.rod( ( xs * ( EMU_W + 0.1 ), 108.8, z_ ), ( xs * ( EMU_W + 0.9 ), 108.8, z_ ), 0.35, "rw_steel_grey", 6 )
            car.rod( ( xs * ( EMU_W + 0.2 ), 92.0, 147.5 ), ( xs * ( EMU_W + 5.5 ), 88.0, 147.5 ), 0.6, "rw_black", 8,
                     caps=( False, True ) )
            car.box( min( xs * ( EMU_W + 4.6 ), xs * ( EMU_W + 7.4 ) ), max( xs * ( EMU_W + 4.6 ), xs * ( EMU_W + 7.4 ) ),
                     85.5, 90.0, 145.6, 149.4, "rw_black" )
        T.markings(car, xs, doors)
    T.interior(car)
    T.underframe(car)
    # The roof and the side walls' curve into it, the underside and its steps, the inner end.
    a0, a1 = car.span( start, end )
    _extrude( model, F, EMU_UPPER, a0, a1, lambda k: body if EMU_UPPER[k][1] < EMU_ROOF_LINE else EMU_ROOF_PAINT,
              smooth_from=0 )
    # The underside and the bogie cut-outs' ceilings and end walls: dusty underframe steel, not black, so the cut-outs
    # read as recesses with the bogie in them rather than holes.
    for d0, d1, zb in pieces:
        car.poly( "rw_bogie_brake", [ ( EMU_W, d0, zb ), ( -EMU_W, d0, zb ), ( -EMU_W, d1, zb ), ( EMU_W, d1, zb ) ],
                  ( 0, 0, -1 ) )
    for ( _, d, za ), ( _, _, zb ) in zip( pieces, pieces[1:] ):
        if abs( za - zb ) > 1e-6:
            car.poly( "rw_bogie_brake", [ ( EMU_W, d, za ), ( -EMU_W, d, za ), ( -EMU_W, d, zb ), ( EMU_W, d, zb ) ],
                      ( 0, 1 if za < zb else -1, 0 ) )
    prof = [ ( EMU_W, EMU_SKIRT ) ] + EMU_UPPER
    _section( model, F, prof, car.a( end ), -car.s, body )
    if not cab:
        _section( model, F, prof, car.a( 0.0 ), car.s, body )
    # Air conditioning on the roof: a pod over each mid-level end (the rear car's inner one clear of its pantograph),
    # and a cable duct along the roof between them.
    try:
        import railhead_roof_kit as RK
        pods = ( 160.0, 645.0 ) if roof == "ac" else ( 160.0, 560.0 )
        for d0 in pods:
            RK.ac_pod( car, d0, d0 + 78.7 )
        RK.cable_duct( car, 112.0 if cab else 8.0, 755.0, ( pods[0], pods[0] + 78.7 ), ( pods[1], pods[1] + 78.7 ),
                       pantograph=roof != "ac" )
        avoid = [ ( d, d + 78.7 ) for d in pods ] + ( [] if roof == "ac" else [ ( 590.0, 763.0 ) ] )
        RK.roof_details( car, start, end, cab, avoid )
    except Exception as error:
        print( f"railhead_roof_kit failed: {error}" )
        if roof == "ac":
            car.box( -24.0, 24.0, 640.0, 735.0, EMU_ROOF - 2.0, EMU_ROOF + 7.0, "rw_train_grey", skip=( "bottom", ) )
    if cab:
        try:
            import railhead_roof_kit as RK
            for xs in ( 1.0, -1.0 ):
                RK.cab_door( car, xs )
        except Exception as error:
            print( f"railhead_roof_kit.cab_door failed: {error}" )
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
            car.collide( 0.0, platform_xs * W, p0, p1, EMU_DOOR_TOP, top )


def emu( model, e, n_front, facing, rail_z=-30.0, cars=2, body="rw_train_blue", platform_side=-1, doors_open=False,
         wire_z=None, destinations=( "RE München", "RE München" ) ):
    """ A two-car double-deck EMU (39.1 m over the couplers), a cab at each end, two pairs of 1.6 m sliding plug
    doors a side per car. Livery: body paint with a light grey stripe low down, black window frames and visors, a
    grey roof. Doors are closed by default. platform_side (+1 east, -1 west): the side to open when doors_open is True,
    each into a 1.4 m deep vestibule floored level with the platform (rail_z + 30) under a 2.5 m ceiling.
    wire_z: the contact wire's z, to raise the pantograph on to it; None leaves it down. destinations: the front and
    rear cabs' displays (the letters in EMU_FONT). Metal collision per car, solid when closed, hollowed at open vestibules, and across
    the gangway. cars must be 2. Returns the far coupler's n. """
    if cars != 2:
        raise ValueError( "the double-deck EMU is a two-car unit" )
    import railhead_train as T
    body = {"rw_train_red": T.RED, "rw_train_blue": T.BLUE}.get(body, body)
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
    try:                                                                         # corrugated side and end walls
        import railhead_furniture as FU
        for xs in ( 1.0, -1.0 ):
            FU.corrugated( model, F, "x", xs * ( hw - 0.75 ), xs, -( hl - post ), hl - post, rail_h, height - rail_h,
                           paint, inside=paint if doors_open else None )
        FU.corrugated( model, F, "y", -( hl - 0.75 ), -1.0, -( hw - post ), hw - post, rail_h, height - rail_h, paint,
                       inside=paint if doors_open else None, pitch=9.0 )
    except Exception as error:
        print( f"railhead_furniture.corrugated failed: {error}" )
        for xs in ( 1.0, -1.0 ):                                                 # the side walls, set in 0.75
            F.box( model, xs * ( hw - 0.75 ), xs * ( hw - 2.0 ), hl - post, -( hl - post ), rail_h, height - rail_h,
                   { "default": None, out_x[xs]: paint, out_x[-xs]: paint if doors_open else None } )
        F.box( model, -( hw - post ), hw - post, -( hl - 0.75 ), -( hl - 2.0 ), rail_h, height - rail_h,
               { "default": None, "back": paint, "front": paint if doors_open else None } )
    F.box( model, -hw, hw, -hl, hl, height - 1.5, height, { "default": None, "top": paint,
                                                              "bottom": paint if doors_open else None } )
    import railhead_buffer as B

    def oval( centre, normal, w, h, paint="rw_black", sides=12 ):
        """ A corner fitting's slotted hole: an oval w x h on a face, normal its outward axis ( local ). """
        c = np.asarray( centre, float )
        n = np.asarray( normal, float )
        u = np.array( ( 0.0, 0.0, 1.0 ) ) if abs( n[2] ) < 0.5 else np.array( ( 1.0, 0.0, 0.0 ) )
        v = np.cross( n, u )
        pts = [ tuple( c + n * 0.03 + u * ( h / 2 ) * math.sin( 2 * math.pi * k / sides )
                       + v * ( w / 2 ) * math.cos( 2 * math.pi * k / sides ) ) for k in range( sides ) ]
        _fpoly( model, F, paint, pts, tuple( n ) )

    for xs in ( 1.0, -1.0 ):                                                     # the frame
        for ys in ( 1.0, -1.0 ):
            # The corner posts: pressed channels standing 0.16 proud of the walls' outer flats, a weld down each edge.
            F.box( model, xs * hw, xs * ( hw - post ), ys * hl, ys * ( hl - post ), 4.6, height - 4.6, paint,
                   skip=( "bottom", "top" ) )
            F.box( model, xs * ( hw + 0.16 ), xs * ( hw - 0.6 ), ys * ( hl - 1.2 ), ys * ( hl - 4.8 ), 4.6, height - 4.6,
                   paint, skip=( "bottom", "top" ) )
            for y_ in ( ys * ( hl - post ), ):
                rod( model, F.p( xs * ( hw - 0.75 ), y_, 4.8 ), F.p( xs * ( hw - 0.75 ), y_, height - 4.8 ), 0.14,
                     "rw_steel_dark", 4 )
            # The cast corner fittings, 178 x 162 x 118 mm, 10 mm proud of the posts and rails, a slotted oval hole
            # in each outer face and the top or bottom.
            for c0, c1, vert in ( ( -0.05, 4.65, -1.0 ), ( height - 4.65, height + 0.4, 1.0 ) ):
                x0, x1 = sorted( ( xs * ( hw + 0.4 ), xs * ( hw - 6.4 ) ) )
                y0, y1 = sorted( ( ys * ( hl + 0.4 ), ys * ( hl - 7.0 ) ) )
                B.bevel_box( model, F, ( x0, y0, c0 ), ( x1, y1, c1 ), paint, 0.35, "rw_steel_dark" )
                zc_ = ( c0 + c1 ) / 2
                oval( ( xs * ( hw + 0.4 ), ys * ( hl - 3.3 ), zc_ ), ( xs, 0, 0 ), 4.9, 2.5 )
                oval( ( xs * ( hw - 3.0 ), ys * ( hl + 0.4 ), zc_ ), ( 0, ys, 0 ), 2.5, 2.2 )
                oval( ( xs * ( hw - 3.0 ), ys * ( hl - 3.3 ), c1 if vert > 0 else c0 ), ( 0, 0, vert ), 4.9, 2.5 )
        # The bottom side rail, and the top side rail: a 60 mm square hollow section 6 mm proud of the roof's edge.
        F.box( model, xs * hw, xs * ( hw - 3.0 ), hl - post, -( hl - post ), 0.0, rail_h, paint )
        F.box( model, xs * hw, xs * ( hw - 3.0 ), hl - post, -( hl - post ), height - rail_h, height - 2.36, paint )
        x0, x1 = sorted( ( xs * ( hw + 0.24 ), xs * ( hw - 2.12 ) ) )
        B.bevel_box( model, F, ( x0, -( hl - post ), height - 2.36 ), ( x1, hl - post, height + 0.24 ), paint, 0.2,
                     "rw_steel_dark" )
        # Forklift pockets through the bottom rail of a 20 ft box, 900 mm either side of its middle, and the lashing
        # rings along the rail.
        if str( size ) == "20":
            for yc in ( -35.4, 35.4 ):
                F.box( model, min( xs * ( hw + 0.02 ), xs * ( hw + 0.3 ) ), max( xs * ( hw + 0.02 ), xs * ( hw + 0.3 ) ),
                       yc - 7.6, yc + 7.6, 0.2, 5.6, "rw_steel_dark" )
                F.box( model, min( xs * ( hw + 0.3 ), xs * ( hw + 0.34 ) ), max( xs * ( hw + 0.3 ), xs * ( hw + 0.34 ) ),
                       yc - 7.1, yc + 7.1, 0.5, 5.0, "rw_black" )
        import railhead_vehicle_kit as VK
        for k in range( 4 ):
            yr = -hl + post + 10.0 + k * ( 2 * ( hl - post ) - 20.0 ) / 3
            VK.torus( model, "rw_steel_dark", F.p( xs * ( hw + 0.45 ), yr, rail_h - 1.4 ), F.x, 1.1, 0.2, sides=10,
                      tube=4 )
            F.box( model, min( xs * hw, xs * ( hw + 0.4 ) ), max( xs * hw, xs * ( hw + 0.4 ) ), yr - 0.6, yr + 0.6,
                   rail_h - 0.6, rail_h + 0.2, "rw_steel_dark" )
        # The owner code high on each side at the door end, painted over the corrugation's outer flats.
        yc = door_end * 0 + ( hl - post - 16.0 )
        F.quad( model, "rw_container_code", xs * ( hw - 0.68 ), yc, height - 12.0, 22.0, 3.2, out_x[xs],
                uv=_code_uv( "owner", flip=xs < 0 ) )
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
    for xs in ( 1.0, -1.0 ):
        for k in range( 4 ):
            x = xs * ( 5.0 + 9.5 * k )
            F.box( model, x - 2.6, x + 2.6, hl - 0.2, hl + 0.5, rail_h + 6.0, height - 14.0, paint, skip=( "back", ) )
        for z in ( 14.0, 40.0, 66.0, 92.0 ):
            F.box( model, xs * ( hw - post - 1.5 ), xs * ( hw - post + 0.5 ), hl - 0.2, hl + 1.0, z - 2.0, z + 2.0,
                   "rw_steel_dark", skip=( "back", ) )
    F.quad( model, "rw_black", 0.0, hl - 0.15, height / 2 - 1.0, 0.6, height - 14.0 )
    for x in ( -36.0, -12.0, 12.0, 36.0 ):
        rod( model, F.p( x, hl + 1.2, 3.0 ), F.p( x, hl + 1.2, height - 3.0 ), 0.95, "rw_steel_grey", 6 )
        # Four keepers on each bar: the cam keepers top and bottom, two guides between.
        for z in ( 4.0, height - 4.0 ):
            F.box( model, x - 1.6, x + 1.6, hl - 0.2, hl + 2.4, z - 1.5, z + 1.5, "rw_steel_grey", skip=( "back", ) )
        for z in ( 26.0, height - 30.0 ):
            F.box( model, x - 1.4, x + 1.4, hl + 0.5, hl + 2.3, z - 0.8, z + 0.8, "rw_steel_grey", skip=( "back", ) )
        # The cam handle, its retainer and (on the right door's inner bar) the customs seal's hasp.
        hx = x + ( 7.0 if x > 0 else -7.0 )
        F.box( model, min( x, hx ), max( x, hx ), hl + 1.0, hl + 2.4, 44.0, 46.0, "rw_steel_grey", skip=( "back", ) )
        F.box( model, hx - 0.9, hx + 0.9, hl + 0.5, hl + 2.8, 41.5, 48.5, "rw_steel_dark", skip=( "back", ) )
        if x == 12.0:
            F.box( model, hx + 0.9, hx + 2.6, hl + 1.4, hl + 2.0, 43.6, 46.4, "rw_steel_grey", skip=( "back", ) )
            rod( model, F.p( hx + 2.2, hl + 2.3, 43.0 ), F.p( hx + 2.2, hl + 2.3, 41.0 ), 0.12, "rw_yellow_paint", 4 )
    # The doors' markings: the owner code across the top, the size-type code under it, the CSC plate and the
    # weights panel.
    F.quad( model, "rw_container_code", 12.0, hl + 0.06, height - 4.2, 22.0, 3.2, "front", uv=_code_uv( "owner" ) )
    F.quad( model, "rw_container_code", 26.0, hl + 0.56, height - 19.0, 8.6, 3.1, "front", uv=_code_uv( "type" ) )
    F.quad( model, "rw_container_code", -24.0, hl + 0.56, 62.0, 6.2, 6.2, "front", uv=_code_uv( "csc" ) )
    F.quad( model, "rw_container_code", 26.0, hl + 0.56, 70.0, 9.2, 9.2, "front", uv=_code_uv( "tare" ) )
    F.collide( model, -hw, hw, -hl, hl, 0.0, height, "metal" )


def _code_uv( name, flip=False ):
    """ The container markings' atlas entry, bottom-left, bottom-right, top-right, top-left (flip mirrors it). """
    try:
        import railhead_prop_materials as PM
        uv = PM.code_uv( name )
    except Exception:
        uv = [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ]
    return [ uv[1], uv[0], uv[3], uv[2] ] if flip else uv


# ---------------------------------------------------------------------------------------------------------------------
# Yard clutter the dressing places (the same signatures and the same collision as railhead_dress_detail's).

def skip_bin( model, e, n, facing, z0=0.0, paint="rw_skip_yellow", fill="rw_ballast_old" ):
    """ A builder's set-down skip (Absetzmulde): a tapered box of 5 mm plate, 3.4 m long at its rim and 2.6 m at its
    floor, 1.7 m wide and 1.2 m deep, as railhead_dress_detail's (whose collision box it keeps), with a rolled 60 mm lip
    all round, three pressed U-channel ribs down each long side, the two lifting trunnions (60 mm pins with collars)
    on each side, a drop end hinged at its foot with its chain hooks, small dents, faded RAL 1021 paint rusted at the
    lip and dirty at the foot, and a mound of rubble in it. facing is the way its long side runs. One box of
    collision. """
    import railhead_buffer as B
    if paint in ( "rw_yellow_paint", None ):
        paint = "rw_skip_yellow"
    F = frame_for( e, n, z0, facing )
    top_l, bot_l, w, h = 66.9, 51.2, 33.5, 47.2
    rng = np.random.default_rng( int( abs( e ) * 7 + abs( n ) * 3 ) % 100003 )
    centre = F.p( 0.0, 0.0, h / 2 )

    def wall_pt( side, u, v, inset=0.0 ):
        """ A point on the long wall side (+1/-1) at u (-1..1 along) and v (0..1 up), dented a little. """
        y = u * ( bot_l + ( top_l - bot_l ) * v )
        return ( side * ( w - inset ), y, 2.0 + ( h - 2.0 ) * v )

    # The long walls, a 6 x 4 grid each so they can take dents, outside and in.
    nu, nv = 8, 4
    dents = { ( side, i, j ): rng.normal( 0, 0.22 ) if 0 < i < nu and 0 < j < nv else 0.0
              for side in ( -1, 1 ) for i in range( nu + 1 ) for j in range( nv + 1 ) }
    for side in ( -1, 1 ):
        for i in range( nu ):
            for j in range( nv ):
                corners = [ ( i, j ), ( i + 1, j ), ( i + 1, j + 1 ), ( i, j + 1 ) ]
                outer, inner = [], []
                for ci, cj in corners:
                    x, y, z = wall_pt( side, -1 + 2 * ci / nu, cj / nv )
                    d = dents[( side, ci, cj )]
                    outer.append( F.p( x - side * d, y, z ) )
                    inner.append( F.p( x - side * ( d + 0.2 ), y * 0.997, z ) )
                _fpoly_world( model, paint, outer, F.x * side )
                _fpoly_world( model, paint, inner, -F.x * side )
    # The two ends: sloping plates; the +y one is the drop end, its hinge along its foot.
    for ys in ( -1, 1 ):
        pts = [ F.p( -w, ys * bot_l, 2.0 ), F.p( w, ys * bot_l, 2.0 ), F.p( w, ys * top_l, h ), F.p( -w, ys * top_l, h ) ]
        out = F.y * ys * ( h - 2.0 ) + F.z * ( -( top_l - bot_l ) )
        _fpoly_world( model, paint, pts, out )
        _fpoly_world( model, paint, [ p - ( p - centre ) * 0.02 for p in pts ], -out )
    for z in ( 2.0, ):
        _fpoly_world( model, "rw_steel_dark", [ F.p( -w, -bot_l, z ), F.p( w, -bot_l, z ), F.p( w, bot_l, z ),
                                                F.p( -w, bot_l, z ) ], -F.z )
    # The drop end: its hinge pins along the foot, its shut seams, the two chain hooks at its top corners.
    t = ( top_l - bot_l ) / ( h - 2.0 )
    end_pt = lambda x, z, lift=0.0: F.p( x, bot_l + t * ( z - 2.0 ) + lift, z + lift * -t )
    for x0 in ( -w + 3.0, -6.0, w - 9.0 ):
        rod( model, end_pt( x0, 5.0, 1.2 ), end_pt( x0 + 6.0, 5.0, 1.2 ), 1.1, "rw_steel_dark", 10, caps=( True, True ) )
    for x0, x1, z0_, z1_ in ( ( -w + 1.5, -w + 1.8, 7.0, h - 3.0 ), ( w - 1.8, w - 1.5, 7.0, h - 3.0 ),
                              ( -w + 1.5, w - 1.5, 7.0, 7.3 ) ):
        _fpoly_world( model, "rw_black", [ end_pt( x0, z0_, 0.05 ), end_pt( x1, z0_, 0.05 ), end_pt( x1, z1_, 0.05 ),
                                           end_pt( x0, z1_, 0.05 ) ], F.y + F.z * -t )
    for sx in ( -1, 1 ):
        c = end_pt( sx * ( w - 5.0 ), h - 6.0, 1.5 )
        rod( model, c - F.z * 1.6, c + F.z * 1.6, 0.6, "rw_steel_dark", 6, caps=( True, True ) )
        rod( model, c + F.z * 1.6, c + F.z * 1.6 + F.y * 1.6, 0.6, "rw_steel_dark", 6, caps=( False, True ) )
    # The rolled lip all round the rim: a 60 mm box section, chamfered, its top rubbed to rust.
    lip = 2.36
    for x0, x1, y0, y1 in ( ( -w - 0.6, -w - 0.6 + lip, -top_l - 0.6, top_l + 0.6 ),
                            ( w + 0.6 - lip, w + 0.6, -top_l - 0.6, top_l + 0.6 ),
                            ( -w - 0.6 + lip, w + 0.6 - lip, -top_l - 0.6, -top_l - 0.6 + lip ),
                            ( -w - 0.6 + lip, w + 0.6 - lip, top_l + 0.6 - lip, top_l + 0.6 ) ):
        B.bevel_box( model, F, ( x0, y0, h - lip ), ( x1, y1, h ), paint, 0.5, "rw_wagon_rust" )
    # Three pressed U-channel ribs down each long side, following the wall's taper; the floor's two skids.
    for side in ( -1, 1 ):
        for u in ( -0.5, 0.0, 0.5 ):
            yb, yt = u * bot_l, u * top_l
            for dy0, dy1, paint_ in ( ( -1.7, -1.2, paint ), ( 1.2, 1.7, paint ) ):
                _fpoly_world( model, paint_, [ F.p( side * w, yb + dy0, 2.5 ), F.p( side * w, yb + dy1, 2.5 ),
                                               F.p( side * w, yt + dy1, h - lip ), F.p( side * w, yt + dy0, h - lip ) ],
                              F.x * side )
            _fpoly_world( model, paint, [ F.p( side * ( w + 1.3 ), yb - 1.7, 2.5 ), F.p( side * ( w + 1.3 ), yb + 1.7, 2.5 ),
                                          F.p( side * ( w + 1.3 ), yt + 1.7, h - lip ), F.p( side * ( w + 1.3 ), yt - 1.7, h - lip ) ],
                          F.x * side )
            for dy in ( -1.7, 1.7 ):
                _fpoly_world( model, paint, [ F.p( side * w, yb + dy, 2.5 ), F.p( side * ( w + 1.3 ), yb + dy, 2.5 ),
                                              F.p( side * ( w + 1.3 ), yt + dy, h - lip ), F.p( side * w, yt + dy, h - lip ) ],
                              F.y * ( 1 if dy > 0 else -1 ) )
        # The trunnions: two 60 mm pins with collars each side near the middle, where the skip lorry's chains go.
        for yc in ( -14.0, 14.0 ):
            c = F.p( side * w, yc, h - 15.0 )
            rod( model, c, c + F.x * side * 5.9, 1.18, "rw_steel_dark", 12, caps=( False, True ) )
            rod( model, c + F.x * side * 4.6, c + F.x * side * 5.3, 1.9, "rw_steel_dark", 12, caps=( True, True ) )
            B.bevel_box( model, F, ( min( side * w, side * ( w + 1.0 ) ), yc - 3.5, h - 19.5 ),
                         ( max( side * w, side * ( w + 1.0 ) ), yc + 3.5, h - 10.5 ), paint, 0.3 )
    for x in ( -w + 6.0, w - 6.0 ):
        F.box( model, x - 2.0, x + 2.0, -bot_l, bot_l, 0.0, 2.0, "rw_steel_dark" )
    # The rubble: a mound over the floor, highest off the middle, with broken concrete and brick in it.
    fill_z = h * 0.55
    nx_, ny_ = 6, 10
    hgt = {}
    for i in range( nx_ + 1 ):
        for j in range( ny_ + 1 ):
            u, v = -1 + 2 * i / nx_, -1 + 2 * j / ny_
            mound = 9.0 * ( 1 - u * u ) * ( 1 - 0.6 * v * v ) * ( 0.7 + 0.3 * math.sin( 3.1 * v + 1.3 ) )
            hgt[( i, j )] = fill_z + mound + rng.uniform( -1.2, 1.2 )
    def fill_pt( i, j ):
        z = hgt[( i, j )]
        v = ( z - 2.0 ) / ( h - 2.0 )
        half_l = bot_l + ( top_l - bot_l ) * v - 0.5
        return F.p( ( -1 + 2 * i / nx_ ) * ( w - 0.6 ), ( -1 + 2 * j / ny_ ) * half_l, min( z, h - 1.0 ) )
    for i in range( nx_ ):
        for j in range( ny_ ):
            _fpoly_world( model, fill, [ fill_pt( i, j ), fill_pt( i + 1, j ), fill_pt( i + 1, j + 1 ), fill_pt( i, j + 1 ) ],
                          F.z )
    for k in range( 14 ):
        i, j = rng.integers( 1, nx_ ), rng.integers( 1, ny_ )
        c = fill_pt( i, j ) + F.x * rng.uniform( -3, 3 ) + F.y * rng.uniform( -3, 3 )
        size = rng.uniform( 2.5, 6.0, 3 ) * ( 1.0, 1.0, 0.6 )
        _rubble_chunk( model, c, size, rng, "rw_concrete" if k % 3 else "rw_brick" )
    lo = np.minimum( F.p( -w - 1.2, -top_l - 1, 0 ), F.p( w + 1.2, top_l + 1, h ) )
    hi = np.maximum( F.p( -w - 1.2, -top_l - 1, 0 ), F.p( w + 1.2, top_l + 1, h ) )
    model.collision_box( lo, hi, "metal" )


def _fpoly_world( model, paint, pts, towards ):
    outward( model, paint, [ np.asarray( p, float ) for p in pts ], np.asarray( towards, float ) )


def _rubble_chunk( model, c, size, rng, paint ):
    """ A broken lump: a box with its corners pulled about, tilted. """
    a = rng.uniform( 0, 2 * math.pi )
    ux = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
    uy = np.array( ( -math.sin( a ), math.cos( a ), 0.0 ) )
    uz = _unit( np.array( ( rng.uniform( -0.3, 0.3 ), rng.uniform( -0.3, 0.3 ), 1.0 ) ) )
    corners = {}
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            for sz in ( -1, 1 ):
                j = rng.uniform( 0.7, 1.15, 3 )
                corners[( sx, sy, sz )] = c + ux * sx * size[0] / 2 * j[0] + uy * sy * size[1] / 2 * j[1] \
                    + uz * sz * size[2] / 2 * j[2]
    for axis in range( 3 ):
        for s_ in ( -1, 1 ):
            quad_ = []
            for a_, b_ in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ):
                key = [ 0, 0, 0 ]
                key[axis] = s_
                key[( axis + 1 ) % 3], key[( axis + 2 ) % 3] = a_, b_
                quad_.append( corners[tuple( key )] )
            outward( model, paint, quad_, ( ux, uy, uz )[axis] * s_ )


def bicycle( model, e, n, heading, z0=0.0, kind="city", paint="rw_train_blue" ):
    """ A bicycle leaning on a stand (railhead_vehicle_kit.bicycle): kind "city" or "trekking", heading in degrees
    from +e or "+e"/"-e"/"+n"/"-n". Visual only, no collision. """
    import railhead_vehicle_kit as VK
    VK.bicycle( model, e, n, heading, z0, kind, paint )


def tyre_stack( model, e, n, z0=0.0, count=4, lean=0.0 ):
    """ Old car tyres stacked flat, as railhead_dress_detail's (the same collision box): each about 650 mm across and
    205 mm tall, a lathed tyre with rounded shoulders, its tread cut by two circumferential grooves and 24 sipes, a ring
    of raised lettering on its sidewall, each turned and sized a little differently, the top one dusty and the top one
    of a tall stack lying askew. One box of collision. """
    R0, r_in, h = 12.8, 8.2, 8.07
    rng = np.random.default_rng( int( abs( e ) * 13 + abs( n ) * 7 ) % 100003 )
    sides = 24
    for k in range( count ):
        de = math.sin( k * 2.1 ) * 1.4 + lean * k
        dn = math.cos( k * 1.7 ) * 1.2
        R = R0 * rng.uniform( 0.95, 1.0 )
        za = z0 + k * h
        c = np.array( ( e + de, n + dn, za ) )
        tilt = math.radians( 7.0 ) if ( k == count - 1 and count >= 3 ) else 0.0
        turn = rng.uniform( 0, 2 * math.pi )
        axis_up = np.array( ( math.sin( tilt ) * math.cos( turn ), math.sin( tilt ) * math.sin( turn ), math.cos( tilt ) ) )
        u = _unit( np.cross( axis_up, ( 0.0, 0.0, 1.0 ) ) ) if tilt else np.array( ( 1.0, 0.0, 0.0 ) )
        v = np.cross( axis_up, u )
        base = c + np.array( ( 0.0, 0.0, R * math.sin( tilt ) * 0.5 ) )
        top_paint = "rw_tyre_dust" if k == count - 1 else "rw_tyre"
        # The tyre's half section ( r, z ), outside from the bottom bead round to the top bead, then the hole.
        prof = [ ( r_in + 1.0, 0.0 ), ( R - 2.6, 0.15 ), ( R - 0.9, 0.9 ), ( R - 0.1, h * 0.28 ), ( R, h * 0.5 ),
                 ( R - 0.1, h * 0.72 ), ( R - 0.9, h - 0.9 ), ( R - 2.6, h - 0.15 ), ( r_in + 1.0, h ), ( r_in, h - 1.0 ),
                 ( r_in, 1.0 ) ]
        def P_( r, z, t ):
            return base + ( math.cos( t ) * u + math.sin( t ) * v ) * r + axis_up * z
        for i in range( sides ):
            t0, t1 = turn + 2 * math.pi * i / sides, turn + 2 * math.pi * ( i + 1 ) / sides
            for j in range( len( prof ) ):
                ( ra, za_ ), ( rb, zb_ ) = prof[j], prof[( j + 1 ) % len( prof )]
                mid_z = ( za_ + zb_ ) / 2
                paint = top_paint if mid_z > h * 0.8 else "rw_tyre"
                rad = ( math.cos( ( t0 + t1 ) / 2 ) * u + math.sin( ( t0 + t1 ) / 2 ) * v )
                towards = rad * ( zb_ - za_ ) - axis_up * ( rb - ra )
                outward( model, paint, [ P_( ra, za_, t0 ), P_( rb, zb_, t0 ), P_( rb, zb_, t1 ), P_( ra, za_, t1 ) ],
                         towards )
            # The tread's sipes and two grooves, and the lettering ring on the top sidewall.
            rad = math.cos( t0 ) * u + math.sin( t0 ) * v
            q = P_( R + 0.02, h * 0.5, t0 + 0.5 * ( t1 - t0 ) )
            tang = _unit( -math.sin( t0 ) * u + math.cos( t0 ) * v )
            outward( model, "rw_black", [ q - axis_up * h * 0.26 - tang * 0.14, q - axis_up * h * 0.26 + tang * 0.14,
                                          q + axis_up * h * 0.26 + tang * 0.14, q + axis_up * h * 0.26 - tang * 0.14 ], rad )
            for gz in ( h * 0.38, h * 0.62 ):
                outward( model, "rw_black", [ P_( R + 0.02, gz - 0.13, t0 ), P_( R + 0.02, gz - 0.13, t1 ),
                                              P_( R + 0.02, gz + 0.13, t1 ), P_( R + 0.02, gz + 0.13, t0 ) ], rad )
            if i % 2 == 0:
                for f0, f1 in ( ( 0.1, 0.4 ), ( 0.55, 0.85 ) ):
                    ta, tb = t0 + ( t1 - t0 ) * f0, t0 + ( t1 - t0 ) * f1
                    outward( model, "rw_tyre_mark", [ P_( R - 5.6, h + 0.04, ta ), P_( R - 4.4, h + 0.04, ta ),
                                                      P_( R - 4.4, h + 0.04, tb ), P_( R - 5.6, h + 0.04, tb ) ], axis_up )
    model.collision_box( ( e - R0 - 1.5, n - R0 - 1.5, z0 ), ( e + R0 + 1.5, n + R0 + 1.5, z0 + count * h ), "rubber" )


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
    back 14 degrees, their edges eased (railhead_bench.slat), on anthracite steel frames of 40 mm square tube at each
    end (and the middle of a long one, with its cast armrest). The footprint is 560 mm deep. Wooden collision: the seat
    down to the floor, and the backrest. """
    F = frame_for( e, n, z0, facing )
    c, hl = 2.55, length / 2                                    # c centres the footprint (the backrest leans out)
    width = ( 16.5 - 3 * 0.5 ) / 4
    t = math.radians( 14.0 )
    up, nrm = np.array( ( 0.0, -math.sin( t ), math.cos( t ) ) ), np.array( ( 0.0, math.cos( t ), math.sin( t ) ) )
    base = np.array( ( 0.0, -8.6 + c, 19.0 ) )
    try:
        # Eased slats with their own UVs, one plank of rw_wood to a face, and end grain at their ends.
        import railhead_bench as RBN
        for k in range( 4 ):
            y0 = -8.0 + c + k * ( width + 0.5 )
            RBN.slat( model, F, -hl, hl, ( y0 + width / 2, BENCH_SEAT - 0.65 ), ( 1.0, 0.0 ), ( 0.0, 1.0 ), width, 1.3,
                      slats, index=k )
        for k in range( 3 ):
            centre = base + up * ( 1.75 + k * 4.05 ) - nrm * 0.6
            RBN.slat( model, F, -hl, hl, centre[1:], up[1:], nrm[1:], 3.5, 1.2, slats, index=4 + k )
    except Exception as error:
        print( f"railhead_bench.slat failed: {error}" )
        model.grain_paints.add( slats )
        for k in range( 4 ):
            y0 = -8.0 + c + k * ( width + 0.5 )
            F.box( model, -hl, hl, y0, y0 + width, BENCH_SEAT - 1.3, BENCH_SEAT, slats )
        for k in range( 3 ):
            centre = base + up * ( 1.75 + k * 4.05 ) - nrm * 0.6
            _obox( model, F, centre, ( 1, 0, 0 ), nrm, ( length, 1.2, 3.5 ), slats )
    posts = [ -hl + 7.0, hl - 7.0 ] + ( [ 0.0 ] if length > 70.0 else [] )
    back0, back1 = base - nrm * 2.0 - up * 3.0, base - nrm * 2.0 + up * 11.0
    try:
        import railhead_furniture as FU
        cast = FU.bench_frames
    except Exception:
        cast = None
    for x in ( posts if cast is None else () ):
        _fbeam( model, F, ( x, 6.8 + c, 0.0 ), ( x, 6.8 + c, BENCH_SEAT - 1.3 ), ( 1.6, 1.6 ), frame )
        _fbeam( model, F, ( x, back0[1] + 0.4, BENCH_SEAT - 2.1 ), ( x, 8.4 + c, BENCH_SEAT - 2.1 ), ( 1.4, 1.6 ),
                frame )
        _fbeam( model, F, ( x, -8.4 + c, 0.0 ), ( x, back0[1], back0[2] ), ( 1.6, 1.6 ), frame )
        _fbeam( model, F, ( x, back0[1], back0[2] ), ( x, back1[1], back1[2] ), ( 1.6, 1.6 ), frame )
    try:
        import railhead_furniture as FU
        if cast is not None:
            cast( model, F, posts, c, BENCH_SEAT, frame, ( back0[1], back0[2] ), ( back1[1], back1[2] ) )
        FU.bench_details( model, F, posts, c, BENCH_SEAT, frame, backrest=( base[1], base[2], t ) )
    except Exception as error:
        print( f"railhead_furniture.bench_details failed: {error}" )
    F.collide( model, -hl, hl, -9.4 + c, 8.5 + c, 0.0, BENCH_SEAT, "wood" )
    F.collide( model, -hl, hl, back1[1] - 0.8, -9.4 + c, 0.0, back1[2] + 1.0, "wood" )


def bin( model, e, n, z0=0.0, facing="+e" ):
    """ A platform litter bin's collision: one metal box. The bin itself is station_bin_v2, placed in the scene
    (railhead_bins). railhead_furniture.bin still builds the old one, for comparing. """
    F = frame_for( e, n, z0, facing )
    w, d = 11.8, 5.9
    import railhead_bins
    railhead_bins.record( ( e, n, z0 ), F.y[:2] )
    F.collide( model, -w - 0.4, w + 0.4, -d - 0.4, d + 0.9, 0.0, 39.4, "metal" )


def ticket_machine( model, e, n, z0=0.0, facing="+e" ):
    """ Reference ticket machine: portrait screen, payment column and recessed dispenser. """
    import railhead_ticket_machine
    railhead_ticket_machine.build( model, frame_for( e, n, z0, facing ) )


VENDING = "rw_vending"
BLACK = "rw_vend_cabinet"        # the cabinet's silver-grey powder coat (railhead_prop_materials)
# The machine's goods, a row of four a shelf from the top (rw_vending's entries): crisps, chocolate, biscuits and
# sweets in pillow packs, then 500 ml cans, then more packs and a bottle of water.
VENDING_SLOTS = ( ( "snack_solbite", "snack_cloudos", "snack_zestix", "snack_ridgerun" ),
                  ( "snack_novabar", "snack_chunko", "snack_meltz", "snack_frost" ),
                  ( "snack_crumbly", "snack_jellyjoy", "snack_polar", "snack_knotties" ),
                  ( "drink_fizzup", "drink_citraze", "drink_sparkleaf", "drink_groove" ),
                  ( "snack_mintle", "snack_bubblez", "snack_chocobitz", "drink_hydro" ) )
VENDING_BAG_W = 5.0                                      # the packs' width; their height is their picture's
VENDING_COLUMNS = ( 0.14, 0.38, 0.62, 0.86 )            # the slots' centres across the shelf (railhead_materials')
VENDING_CAN = [ ( 1.36, 0.0 ), ( 1.6, 0.36 ), ( 1.6, 6.2 ), ( 1.34, 6.54 ), ( 1.28, 6.6 ) ]      # ( r, z ) from its foot
VENDING_BOTTLE = [ ( 1.4, 0.0 ), ( 1.55, 0.3 ), ( 1.55, 5.4 ), ( 1.2, 6.2 ), ( 0.62, 6.8 ), ( 0.57, 7.2 ) ]
VENDING_LABEL = ( 1.9, 4.8 )                             # the bottle's label band, z


def _vuv( name ):
    return _rect( VENDING, name )


def _vface( model, F, name, x0, x1, z0, z1, y, toward=1.0 ):
    """ An rw_vending entry on a rectangle across the frame at depth y, facing local y toward, upright. """
    u0, v0, u1, v1 = _vuv( name )
    if toward < 0:
        u0, u1 = u1, u0
    _frect( model, F, VENDING, x0, x1, y, z0, z1, toward, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )


def _vswatch( model, F, name, pts, towards ):
    """ A polygon in one flat rw_vending swatch (the middle of its entry). """
    u0, v0, u1, v1 = _vuv( name )
    c = ( ( u0 + u1 ) / 2, ( v0 + v1 ) / 2 )
    _fpoly( model, F, VENDING, pts, towards, uv=[ c ] * len( pts ) )


def _holed( model, F, paint, x0, x1, z0, z1, y, holes, toward=1.0 ):
    """ A rectangle across the frame at depth y less the rectangular holes ( x0, x1, z0, z1 ) cut out of it. """
    cuts = sorted( { z0, z1, *[ z for _, _, hz0, hz1 in holes for z in ( hz0, hz1 ) if z0 < z < z1 ] } )
    for s0, s1 in zip( cuts, cuts[1:] ):
        mid = ( s0 + s1 ) / 2
        spans = [ ( hx0, hx1 ) for hx0, hx1, hz0, hz1 in holes if hz0 <= mid <= hz1 ]
        for a, b in _subtract( ( x0, x1 ), spans ):
            _frect( model, F, paint, a, b, y, s0, s1, toward )


def _bevel( model, F, paint, x0, x1, z0, z1, y_out, y_in, inset ):
    """ The four sloping sides of an opening x0..x1, z0..z1 in a face at y_out, closing in by inset to y_in. """
    o = [ ( x0, y_out, z0 ), ( x1, y_out, z0 ), ( x1, y_out, z1 ), ( x0, y_out, z1 ) ]
    i = [ ( x0 + inset, y_in, z0 + inset ), ( x1 - inset, y_in, z0 + inset ), ( x1 - inset, y_in, z1 - inset ),
          ( x0 + inset, y_in, z1 - inset ) ]
    for k, towards in enumerate( ( ( 0, 1, 1 ), ( -1, 1, 0 ), ( 0, 1, -1 ), ( 1, 1, 0 ) ) ):
        _fpoly( model, F, paint, [ o[k], o[( k + 1 ) % 4], i[( k + 1 ) % 4], i[k] ], towards )


def _rounded( x0, x1, z0, z1, r, steps=3 ):
    """ A rounded rectangle's outline ( x, z ), counter-clockwise from its bottom edge. """
    pts = []
    for cx, cz, a0 in ( ( x1 - r, z0 + r, -90 ), ( x1 - r, z1 - r, 0 ), ( x0 + r, z1 - r, 90 ), ( x0 + r, z0 + r, 180 ) ):
        for k in range( steps + 1 ):
            a = math.radians( a0 + 90 * k / steps )
            pts.append( ( cx + r * math.cos( a ), cz + r * math.sin( a ) ) )
    return pts


def _vplate( model, F, name, x0, x1, z0, z1, y0, y1, r, edge ):
    """ A plate with rounded corners standing from y0 out to y1, its face an rw_vending entry, its edge in edge. """
    u0, v0, u1, v1 = _vuv( name )
    outline = _rounded( x0, x1, z0, z1, r )
    uv = [ ( u0 + ( x - x0 ) / ( x1 - x0 ) * ( u1 - u0 ), v0 + ( z - z0 ) / ( z1 - z0 ) * ( v1 - v0 ) ) for x, z in outline ]
    _fpoly( model, F, VENDING, [ ( x, y1, z ) for x, z in outline ], ( 0, 1, 0 ), uv=uv )
    for ( xa, za ), ( xb, zb ) in zip( outline, outline[1:] + outline[:1] ):
        nx, nz = zb - za, -( xb - xa )
        _fpoly( model, F, edge, [ ( xa, y0, za ), ( xb, y0, zb ), ( xb, y1, zb ), ( xa, y1, za ) ], ( nx, 0, nz ) )


def _pillow( model, F, name, xc, yc, z0, w, h, t, nx=6, nz=6, seal=0.065 ):
    """ A pillow pack standing on z0: its front bulges t forward of its middle at yc, flat at the crimped seals top and
    bottom and pinched to nothing at its sides; the front is its rw_vending picture, the back plain. """
    u0, v0, u1, v1 = _vuv( name )
    zs0, zs1 = z0 + seal * h, z0 + h - seal * h
    vs0, vs1 = v0 + seal * ( v1 - v0 ), v1 - seal * ( v1 - v0 )

    def surface( a, c ):
        return t * math.sqrt( max( 0.0, 1.0 - a * a ) ) ** 0.8 * math.sqrt( max( 0.0, 1.0 - c ** 4 ) )

    def point( a, c ):
        return ( xc + a * w / 2, yc + surface( a, c ), ( zs0 + zs1 ) / 2 + c * ( zs1 - zs0 ) / 2 )

    def normal( a, c ):
        e = 1e-3
        a0, a1 = max( -1.0, a - e ), min( 1.0, a + e )
        c0, c1 = max( -1.0, c - e ), min( 1.0, c + e )
        dx = np.subtract( point( a1, c ), point( a0, c ) )
        dz = np.subtract( point( a, c1 ), point( a, c0 ) )
        n = np.cross( dz, dx )
        n = n if n[1] >= 0 else -n
        return tuple( _unit( n ) )

    As = [ -1.0 + 2.0 * k / nx for k in range( nx + 1 ) ]
    Cs = [ -1.0 + 2.0 * k / nz for k in range( nz + 1 ) ]
    for i in range( nx ):
        for j in range( nz ):
            corners = [ ( As[i], Cs[j] ), ( As[i + 1], Cs[j] ), ( As[i + 1], Cs[j + 1] ), ( As[i], Cs[j + 1] ) ]
            uv = [ ( u0 + ( a + 1 ) / 2 * ( u1 - u0 ), vs0 + ( c + 1 ) / 2 * ( vs1 - vs0 ) ) for a, c in corners ]
            _fpoly( model, F, VENDING, [ point( a, c ) for a, c in corners ], ( 0, 1, 0 ), uv=uv,
                    normals=[ normal( a, c ) for a, c in corners ] )
    for za, zb, va, vb in ( ( z0, zs0, v0, vs0 ), ( zs1, z0 + h, vs1, v1 ) ):          # the seals
        _frect( model, F, VENDING, xc - w / 2, xc + w / 2, yc, za, zb,
                uv=[ ( u0, va ), ( u1, va ), ( u1, vb ), ( u0, vb ) ] )
    _vswatch( model, F, "cavity_back", [ ( xc - w / 2, yc - 0.02, z0 ), ( xc + w / 2, yc - 0.02, z0 ),
                                         ( xc + w / 2, yc - 0.02, z0 + h ), ( xc - w / 2, yc - 0.02, z0 + h ) ],
              ( 0, -1, 0 ) )


def _vlathe( model, F, xc, yc, z0, profile, paint_at, sides=16, closed=True ):
    """ A round thing standing on z0 round ( xc, yc ): profile ( r, z ) from the bottom up, each band painted by
    paint_at( k ) -> ( entry, labelled ). A labelled band wraps its entry round once, the picture's middle facing the
    front (local +y); the others take the entry's middle colour. Its top is closed with the last band's entry
    unless closed is False. """
    for k in range( len( profile ) - 1 ):
        ( r0, za ), ( r1, zb ) = profile[k], profile[k + 1]
        name, labelled = paint_at( k )
        u0, v0, u1, v1 = _vuv( name )
        slope = ( r0 - r1 ) / max( zb - za, 1e-6 )
        for s in range( sides ):
            t0, t1 = 2 * math.pi * s / sides, 2 * math.pi * ( s + 1 ) / sides
            d0, d1 = ( math.sin( t0 ), math.cos( t0 ) ), ( math.sin( t1 ), math.cos( t1 ) )
            pts = [ ( xc + r0 * d0[0], yc + r0 * d0[1], z0 + za ), ( xc + r0 * d1[0], yc + r0 * d1[1], z0 + za ),
                    ( xc + r1 * d1[0], yc + r1 * d1[1], z0 + zb ), ( xc + r1 * d0[0], yc + r1 * d0[1], z0 + zb ) ]
            nrm = [ _unit( ( d[0], d[1], slope ) ) for d in ( d0, d1, d1, d0 ) ]
            if labelled:
                ua = u0 + ( 0.5 + ( t0 if t0 <= math.pi else t0 - 2 * math.pi ) / ( 2 * math.pi ) ) * ( u1 - u0 )
                ub = ua + ( u1 - u0 ) / sides
                uv = [ ( ua, v0 ), ( ub, v0 ), ( ub, v1 ), ( ua, v1 ) ]
            else:
                uv = [ ( ( u0 + u1 ) / 2, ( v0 + v1 ) / 2 ) ] * 4
            _fpoly( model, F, VENDING, pts, ( ( d0[0] + d1[0] ) / 2, ( d0[1] + d1[1] ) / 2, slope ), uv=uv,
                    normals=nrm )
    if not closed:
        return
    r, z = profile[-1]
    _vswatch( model, F, paint_at( len( profile ) - 2 )[0],
              [ ( xc + r * math.sin( 2 * math.pi * s / sides ), yc + r * math.cos( 2 * math.pi * s / sides ), z0 + z )
                for s in range( sides ) ], ( 0, 0, 1 ) )


def _spiral( model, F, xc, y_front, z_shelf, turns=2.0, pitch=2.3, r=1.85, wire=0.09, steps=8 ):
    """ A vending spiral lying on the shelf: a steel wire coil r round, pitch apart, running back from y_front. """
    pts = []
    for k in range( int( turns * steps ) + 1 ):
        a = 2 * math.pi * k / steps
        pts.append( F.p( xc + r * math.sin( a ), y_front - pitch * k / steps, z_shelf + r + wire - r * math.cos( a ) ) )
    polyline( model, pts, wire, BLACK, 4 )


def vending_machine( model, e, n, z0=0.0, facing="+e" ):
    """ A snack machine (990 x 850 x 1830 mm), a modern black one: its glass door on the left shows five shelves of
    goods in their spirals, four to a shelf with each slot's code (A1 to E4) on the rail under it, lit by an LED strip
    along the top inside the glass; on the right a brushed steel panel holds the touch screen ("select your item"),
    the keypad, the contactless card reader under its LED and the card slot; below the door the pick-up bay with its
    "push" flap under another LED, and thin LED strips light the cabinet's top corners. The goods, screen, keys,
    reader and flap are rw_vending's (Tools/railhead_materials.py). One metal box. """
    F = frame_for( e, n, z0, facing )
    w, back, front, top = 19.5, -16.0, 17.5, 72.0
    yd = front + 0.4                                     # the door's and the control column's faces
    split = 8.45                                         # between the door and the control column
    wx0, wx1, wz0, wz1 = -16.9, 6.8, 20.3, 62.6          # the window (the glass), under the lit name band
    bx0, bx1, bz0, bz1 = -14.6, 5.0, 8.2, 16.7           # the pick-up bay's opening
    frame = 0.6                                          # the bevelled rims round the window and the bay
    yg = yd - 0.9                                        # the glass
    yb = yg - 13.0                                       # the back of the goods' cavity

    # The cabinet, its plinth and the two slabs on its front: the door and the control column.
    F.box( model, -w + 1.0, w - 1.0, back + 1.0, front - 1.0, 0.0, 2.2, "rw_black", skip=( "bottom", ) )
    F.box( model, -w, w, back, front, 2.2, top, { "default": "rw_vending_body", "top": BLACK },
           skip=( "bottom", "front" ) )
    # Its sides and back: two horizontal panel seams, six vent louvres low on the left side, the rear cable gland, a
    # 20 mm chamfered drip edge along the top all round, and four adjustable feet under the plinth's corners.
    for xs in ( -1.0, 1.0 ):
        for z in ( 24.0, 50.0 ):
            _fpoly( model, F, "rw_black", [ ( xs * ( w + 0.02 ), back + 0.6, z - 0.08 ), ( xs * ( w + 0.02 ), front - 0.6, z - 0.08 ),
                                            ( xs * ( w + 0.02 ), front - 0.6, z + 0.08 ), ( xs * ( w + 0.02 ), back + 0.6, z + 0.08 ) ],
                    ( xs, 0, 0 ) )
        _obox( model, F, ( xs * ( w - 0.2 ), ( back + front ) / 2, top - 0.2 ), ( 0, 1, 0 ), ( xs, 0, 1 ),
               ( front - back - 0.4, 0.12, 1.1 ), "rw_steel_grey" )
    _obox( model, F, ( 0.0, back + 0.2, top - 0.2 ), ( 1, 0, 0 ), ( 0, -1, 1 ), ( 2 * w - 0.4, 0.12, 1.1 ), "rw_steel_grey" )
    for k in range( 6 ):
        z = 11.0 + 2.5 * k
        _fpoly( model, F, "rw_black", [ ( -w - 0.02, -8.0, z ), ( -w - 0.02, 7.7, z ), ( -w - 0.02, 7.7, z + 1.2 ),
                                        ( -w - 0.02, -8.0, z + 1.2 ) ], ( -1, 0, 0 ) )
        _obox( model, F, ( -w - 0.25, -0.15, z + 1.15 ), ( 0, 1, 0 ), ( -1, 0, -0.6 ), ( 15.7, 0.5, 0.08 ),
               "rw_vending_body" )
    rod( model, F.p( 12.0, back, 6.0 ), F.p( 12.0, back - 1.0, 6.0 ), 0.75, "rw_black", 8, caps=( False, True ) )
    rod( model, F.p( 12.0, back - 1.0, 6.0 ), F.p( 12.0, back - 1.6, 1.0 ), 0.3, "rw_black", 6 )
    for fx in ( -w + 0.5, w - 0.5 ):
        for fy in ( back + 0.5, front - 0.5 ):
            rod( model, F.p( fx, fy, 0.0 ), F.p( fx, fy, 0.3 ), 0.48, "rw_steel_dark", 10, caps=( False, True ) )
            rod( model, F.p( fx, fy, 0.3 ), F.p( fx, fy, 2.2 ), 0.22, "rw_steel_grey", 6 )
    # Chamfer strips down the cabinet's front corners and along its top front edge: 20 mm, catching the hall's light.
    for x, sx in ( ( -w, -1.0 ), ( w, 1.0 ) ):
        _obox( model, F, ( x - sx * 0.2, front - 0.2, ( 2.2 + top ) / 2 ), ( sx, 1, 0 ), ( -1, sx, 0 ),
               ( 0.12, 1.1, top - 2.2 ), "rw_steel_grey" )
    _obox( model, F, ( 0.0, front - 0.2, top - 0.2 ), ( 1, 0, 0 ), ( 0, 1, 1 ), ( 2 * w, 0.12, 1.1 ), "rw_steel_grey" )
    for x0, x1, z0_, z1_ in ( ( -w, -w + 0.2, 2.2, top ), ( w - 0.2, w, 2.2, top ), ( -w + 0.2, w - 0.2, 2.2, 2.4 ),
                              ( -w + 0.2, w - 0.2, top - 0.4, top ), ( split - 0.1, split + 0.1, 2.4, top - 0.4 ) ):
        _frect( model, F, BLACK, x0, x1, front, z0_, z1_ )         # the cabinet's front round the slabs
    for x0, x1 in ( ( -w + 0.2, split - 0.1 ), ( split + 0.1, w - 0.2 ) ):
        F.box( model, x0, x1, front, yd, 2.4, top - 0.4, { "default": BLACK, "front": None }, skip=( "back", ) )
    _holed( model, F, BLACK, -w + 0.2, split - 0.1, 2.4, top - 0.4, yd,
            [ ( wx0 - frame, wx1 + frame, wz0 - frame, wz1 + frame ), ( bx0, bx1, bz0, bz1 ) ] )
    _frect( model, F, BLACK, split + 0.1, w - 0.2, yd, 2.4, top - 0.4 )
    for x in ( -w + 0.45, w - 0.45 ):                    # the corner LED strips
        _frect( model, F, "rw_lamp_cool", x - 0.09, x + 0.09, yd + 0.01, top - 7.4, top - 1.0 )

    # The window: a bevelled rim down to the glass, and behind it the lit cavity.
    _bevel( model, F, BLACK, wx0 - frame, wx1 + frame, wz0 - frame, wz1 + frame, yd, yg, frame )
    _frect( model, F, "rw_case_glass", wx0, wx1, yg, wz0, wz1 )
    cx0, cx1, cz0, cz1 = wx0 - 0.3, wx1 + 0.3, wz0 - 0.6, wz1 + 0.6
    # The back of the goods' cavity is a white LED panel the window's full height, so the goods glow in daylight.
    _frect( model, F, "rw_vend_backlight", cx0, cx1, yb, cz0, cz1 )
    for x, s in ( ( cx0, 1.0 ), ( cx1, -1.0 ) ):
        u0, v0, u1, v1 = _vuv( "cavity_side" )
        _fpoly( model, F, VENDING, [ ( x, yb, cz0 ), ( x, yg, cz0 ), ( x, yg, cz1 ), ( x, yb, cz1 ) ], ( s, 0, 0 ),
                uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )
    _vswatch( model, F, "cavity_back", [ ( cx0, yb, cz1 ), ( cx1, yb, cz1 ), ( cx1, yg, cz1 ), ( cx0, yg, cz1 ) ],
              ( 0, 0, -1 ) )
    _vswatch( model, F, "cavity_back", [ ( cx0, yb, cz0 ), ( cx1, yb, cz0 ), ( cx1, yg, cz0 ), ( cx0, yg, cz0 ) ],
              ( 0, 0, 1 ) )
    F.box( model, wx0 + 0.8, wx1 - 0.8, yg - 2.0, yg - 1.2, wz1 - 1.5, wz1 - 0.9,
           { "default": "rw_lamp_cool", "back": None, "top": None } )
    for x0, x1 in ( ( wx0 + 0.05, wx0 + 0.3 ), ( wx1 - 0.3, wx1 - 0.05 ) ):      # and down both sides
        _frect( model, F, "rw_lamp_cool", x0, x1, yg - 0.3, wz0 + 0.4, wz1 - 0.4 )

    # The shelves, their label rails and the goods in their spirals.
    width = wx1 - wx0
    for row, names in enumerate( VENDING_SLOTS ):
        zs = 54.6 - 8.2 * row
        F.box( model, cx0, cx1, yb, yg - 0.9, zs - 0.15, zs, BLACK, skip=( "front", "bottom" ) )
        _vface( model, F, f"rail_{'abcde'[row]}", wx0, wx1, zs - 1.2, zs, yg - 0.85 )
        F.box( model, wx0, wx1, yg - 0.9, yg - 0.85, zs - 1.2, zs, "rw_steel_grey", skip=( "front", ) )
        for col, name in enumerate( names ):
            xc = wx0 + VENDING_COLUMNS[col] * width
            _spiral( model, F, xc, yg - 1.3, zs )
            if name == "drink_hydro":
                for depth, sides in ( ( 2.7, 16 ), ( 5.6, 8 ) ):
                    _vlathe( model, F, xc, yg - depth, zs, VENDING_BOTTLE, lambda k: ( "bottle_plastic", False ), sides )
                    _vlathe( model, F, xc, yg - depth, zs, [ ( 0.66, 7.0 ), ( 0.66, 7.75 ) ],
                             lambda k: ( "bottle_cap", False ), sides )
                _vlathe( model, F, xc, yg - 2.7, zs, [ ( 1.565, VENDING_LABEL[0] ), ( 1.565, VENDING_LABEL[1] ) ],
                         lambda k: ( name, True ), closed=False )
            elif name.startswith( "drink_" ):
                for depth, sides in ( ( 2.7, 16 ), ( 5.9, 8 ) ):
                    _vlathe( model, F, xc, yg - depth, zs, VENDING_CAN,
                             lambda k: ( name, True ) if k == 1 else ( "can_lid", False ), sides )
            else:
                bw = VENDING_BAG_W
                bh = bw / aspect( VENDING, name )
                _pillow( model, F, name, xc, yg - 2.9, zs, bw, bh, 0.85 )
                _vface( model, F, name, xc - bw / 2 + 0.2, xc + bw / 2 - 0.2, zs, zs + bh - 0.3, yg - 4.9 )

    # The backlit name band across the top of the face (a made-up vending firm's), in a brushed aluminium frame, and
    # a 60 mm aluminium frame round the door's glass.
    nz0, nz1 = 63.8, 71.0
    F.box( model, -w + 0.7, w - 0.7, yd, yd + 0.35, nz0 - 0.5, nz1 + 0.4, "rw_alu_brushed", skip=( "back", ) )
    try:
        import railhead_prop_materials as PM
        u0, v0, u1, v1 = PM.rect_uv( "vend_band" )
        band_uv = [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]
    except Exception:
        band_uv = None
    _frect( model, F, "rw_vend_band", -w + 1.0, w - 1.0, yd + 0.37, nz0, nz1, uv=band_uv )
    fa = 2.0
    for x0, x1, z0_, z1_ in ( ( wx0 - frame - fa, wx1 + frame + 0.9, wz1 + frame, wz1 + frame + fa ),
                              ( wx0 - frame - fa, wx1 + frame + 0.9, wz0 - frame - fa, wz0 - frame ),
                              ( wx0 - frame - fa, wx0 - frame, wz0 - frame, wz1 + frame ),
                              ( wx1 + frame, wx1 + frame + 0.9, wz0 - frame, wz1 + frame ) ):
        F.box( model, x0, x1, yd, yd + 0.25, z0_, z1_, "rw_alu_brushed", skip=( "back", ) )

    # The control column's brushed steel panel: the screen in its bezel, the keypad, the card reader and the slot.
    yp = yd + 0.15
    _vplate( model, F, "panel", 9.2, 18.0, 24.0, 62.8, yd, yp, 0.5, "rw_steel_grey" )
    F.box( model, 10.4, 16.9, yp - 0.05, yp + 0.2, 48.5, 60.8, BLACK, skip=( "back", ) )
    _vface( model, F, "screen", 10.72, 16.58, 48.82, 60.48, yp + 0.21 )
    keys = ( "1", "2", "3", "4", "5", "6", "7", "8", "9", "x", "0", "ok" )
    for k, key in enumerate( keys ):
        kx, kz = 11.5 + 2.1 * ( k % 3 ), 45.5 - 2.1 * ( k // 3 )
        F.box( model, kx - 0.8, kx + 0.8, yp - 0.05, yp + 0.3, kz - 0.8, kz + 0.8, { "default": BLACK, "front": None },
               skip=( "back", ) )
        _vface( model, F, f"key_{key}", kx - 0.8, kx + 0.8, kz - 0.8, kz + 0.8, yp + 0.3 )
    F.box( model, 10.8, 16.4, yp - 0.05, yp + 0.6, 30.8, 36.2, { "default": BLACK, "front": None }, skip=( "back", ) )
    _vface( model, F, "reader", 10.8, 16.4, 30.8, 36.2, yp + 0.6 )
    _frect( model, F, "rw_lamp_cool", 12.4, 14.8, yp + 0.62, 35.25, 35.55 )
    F.box( model, 11.5, 15.7, yp - 0.05, yp + 0.4, 26.3, 28.5, { "default": BLACK, "front": None }, skip=( "back", ) )
    _holed( model, F, BLACK, 11.5, 15.7, 26.3, 28.5, yp + 0.4, [ ( 12.0, 15.2, 27.25, 27.55 ) ] )
    _vswatch( model, F, "cavity_back", [ ( 12.0, yp, 27.25 ), ( 15.2, yp, 27.25 ), ( 15.2, yp, 27.55 ),
                                         ( 12.0, yp, 27.55 ) ], ( 0, 1, 0 ) )
    for zz, s in ( ( 27.25, 1.0 ), ( 27.55, -1.0 ) ):
        _fpoly( model, F, BLACK, [ ( 12.0, yp, zz ), ( 15.2, yp, zz ), ( 15.2, yp + 0.4, zz ), ( 12.0, yp + 0.4, zz ) ],
                ( 0, 0, s ) )

    # The pick-up bay: a bevelled rim, the recess with its LED along the top, and the flap leaning back into it.
    _bevel( model, F, BLACK, bx0, bx1, bz0, bz1, yd, yd - 0.5, 0.5 )
    fx0, fx1, fz0, fz1 = bx0 + 0.5, bx1 - 0.5, bz0 + 0.5, bz1 - 0.5
    yf0, yf1 = yd - 2.0, yd - 1.4                        # the flap's top and bottom
    for pts, towards in ( ( [ ( fx0, yd - 0.5, fz1 ), ( fx1, yd - 0.5, fz1 ), ( fx1, yf0, fz1 ), ( fx0, yf0, fz1 ) ],
                            ( 0, 0, -1 ) ),
                          ( [ ( fx0, yd - 0.5, fz0 ), ( fx1, yd - 0.5, fz0 ), ( fx1, yf1, fz0 ), ( fx0, yf1, fz0 ) ],
                            ( 0, 0, 1 ) ),
                          ( [ ( fx0, yd - 0.5, fz0 ), ( fx0, yf1, fz0 ), ( fx0, yf0, fz1 ), ( fx0, yd - 0.5, fz1 ) ],
                            ( 1, 0, 0 ) ),
                          ( [ ( fx1, yd - 0.5, fz0 ), ( fx1, yf1, fz0 ), ( fx1, yf0, fz1 ), ( fx1, yd - 0.5, fz1 ) ],
                            ( -1, 0, 0 ) ) ):
        _vswatch( model, F, "cavity_back", pts, towards )
    u0, v0, u1, v1 = _vuv( "flap" )
    _fpoly( model, F, VENDING, [ ( fx0, yf1, fz0 ), ( fx1, yf1, fz0 ), ( fx1, yf0, fz1 ), ( fx0, yf0, fz1 ) ],
            ( 0, 1, 0.1 ), uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )
    _fpoly( model, F, "rw_lamp_cool", [ ( fx0 + 2.0, yd - 0.55, fz1 - 0.01 ), ( fx1 - 2.0, yd - 0.55, fz1 - 0.01 ),
                                        ( fx1 - 2.0, yd - 0.85, fz1 - 0.01 ), ( fx0 + 2.0, yd - 0.85, fz1 - 0.01 ) ],
            ( 0, 0, -1 ) )
    _frect( model, F, "rw_lamp_cool", fx0 + 2.0, fx1 - 2.0, yd - 0.5, fz1 - 0.3, fz1 - 0.02 )
    F.collide( model, -w, w, back, yd + 0.8, 0.0, top, "metal" )


def timetable_case( model, e, n, z0=0.0, facing="+e", two_sided=False ):
    """ A timetable case on two posts: the yellow departures and white arrivals timetables (A1, 594 x 841 mm) side by
    side behind glass, their bottom edges 900 mm up; two_sided shows them on the back too. One metal box. """
    F = frame_for( e, n, z0, facing )
    try:
        import railhead_furniture as FU
        x0, x1, y0, y1, z1 = FU.timetable_case( model, F, two_sided )
        F.collide( model, x0, x1, y0, y1, 0.0, z1, "metal" )
        return
    except Exception as error:
        print( f"railhead_furniture.timetable_case failed: {error}" )
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
    try:
        import railhead_furniture as FU
        FU.info_pillar_head( model, F )
    except Exception as error:
        print( f"railhead_furniture.info_pillar_head failed: {error}" )
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


def platform_batten( model, e, n, z_top, along="n", length=59.0, floor_z=0.0 ):
    """ A surface-mounted LED batten hung under a canopy or a ceiling at z_top, length long along along ("n" or "e"):
    an extruded aluminium body 75 mm wide and 60 mm deep with chamfered edges and end caps, its opal lens along the
    underside, on two suspension wires with their canopies. Returns the light's position (just under the lens) for
    railhead_map's lights. A collision box round it, out of reach. """
    import railhead_furniture as FU
    return FU.platform_batten( model, e, n, z_top, along, length )


def sos_pillar( model, e, n, facing="+e", z0=0.0 ):
    """ A help point column (Notruf / Info, 1.6 m): a slim blue column on a base plate, its head with the "i" and the
    SOS plate, the intercom's speaker grille, a blue information and a red emergency button, the camera dome on top.
    One box of metal collision. """
    import railhead_furniture as FU
    FU.sos_pillar( model, frame_for( e, n, z0, facing ) )


def cable_trough( model, e, n0, n1, z0 ):
    """ A precast concrete cable trough (300 x 200 mm, 1 m lids) along n from n0 to n1 at e, its lids' tops 200 mm
    over z0: run it along a platform wall's foot in the track bed. Visual only (railhead_furniture). """
    import railhead_furniture as FU
    FU.cable_trough( model, e, n0, n1, z0 )


def drain_grate( model, e, n, z0 ):
    """ A cast-iron gully grate (500 x 300 mm) flush at z0: every 20 m in the track bed's cess or a floor. Visual
    only (railhead_furniture). """
    import railhead_furniture as FU
    FU.drain_grate( model, e, n, z0 )


def drum( model, e, n, z0=0.0, paint="rw_drum_blue" ):
    """ A 200 l steel drum (585 x 880 mm) with rolling hoops and bungs; paint rw_drum_blue, _red or _grey. Metal
    collision (railhead_furniture). """
    import railhead_furniture as FU
    FU.drum( model, e, n, z0, paint )


def pallet_jack( model, e, n, along="n", z0=0.0 ):
    """ A hand pallet truck's collision, its forks along along ("n", "e", or signed). The truck itself is pallet_truck_v2, placed in the scene
    (railhead_pallet_trucks). railhead_furniture.pallet_jack still builds the old one, for comparing. """
    import railhead_pallet_trucks
    F = frame_for( e, n, z0, { "n": "+n", "e": "+e", "+n": "+n", "-n": "-n", "+e": "+e", "-e": "-e" }[along] )
    railhead_pallet_trucks.record( ( e, n, z0 ), F.y[:2] )
    F.collide( model, -10.7, 10.7, -9.0, 47.2, 0.0, 14.0, "metal" )


def cable_reel( model, e, n, z0=0.0, d=55.1 ):
    """ A wooden cable reel d across (1.4 m), on its rim, its axis along e. Wood collision (railhead_furniture). """
    import railhead_furniture as FU
    FU.cable_reel( model, e, n, z0, d )


def cone( model, e, n, z0=0.0 ):
    """ A 750 mm traffic cone with white bands. Visual only (railhead_furniture). """
    import railhead_furniture as FU
    FU.cone( model, e, n, z0 )


def bike_rack( model, e, n, along="n", z0=0.0, bays=4 ):
    """ A row of galvanised Sheffield stands, bays of them a metre apart along along from ( e, n ). Visual only
    (railhead_furniture). """
    import railhead_furniture as FU
    FU.bike_rack( model, e, n, along, z0, bays )


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


# The kiosk: a modern station kiosk, anthracite with a light stone counter, after a picture the user sent. Heights from
# its floor; railhead_kiosk_art.py draws its lettering, icons, menu board, poster and goods (the rw_kiosk atlas).
KIOSK_PLINTH = 4.0              # the recessed black plinth's top
KIOSK_COUNTER = 40.0            # the serving counter's top, 1.02 m
KIOSK_OPEN = 86.0               # the serving window's top, where the fascia starts (2.18 m)
KIOSK_FASCIA = 104.0            # the fascia's top, under the roof slab
KIOSK_ROOF = 108.5              # the roof slab's top (2.76 m)
KIOSK_SHELVES = ( 40.0, 51.5, 63.0, 74.5 )
# The bottled drinks, by their rw_kiosk label: ( the liquid's paint, the cap's ); and the two kinds on each shelf.
KIOSK_DRINKS = { "label_0": ( "rw_bottle_water", "rw_train_blue" ), "label_1": ( "rw_bottle_apple", "rw_container_green" ),
                 "label_2": ( "rw_bottle_orange", "rw_yellow_paint" ), "label_3": ( "rw_bottle_cola", "rw_red_paint" ),
                 "label_4": ( "rw_bottle_lemon", "rw_yellow_paint" ), "label_5": ( "rw_bottle_tea", "rw_white_paint" ) }
KIOSK_DRINK_ROWS = ( ( "label_0", "label_1" ), ( "label_2", "label_4" ), ( "label_3", "label_5" ), ( "label_0", "label_3" ) )
# A 0.5 l PET bottle's profile ( r, z ): its label is band 4 (1.7 to 4.7 up), its cap a lathe of its own.
BOTTLE = [ ( 0.0, 0.0 ), ( 1.14, 0.0 ), ( 1.28, 0.2 ), ( 1.32, 0.6 ), ( 1.32, 1.7 ), ( 1.32, 4.7 ), ( 1.3, 5.5 ),
           ( 1.16, 6.2 ), ( 0.86, 6.9 ), ( 0.6, 7.35 ), ( 0.52, 7.6 ), ( 0.6, 7.62 ), ( 0.6, 7.72 ) ]
BOTTLE_CAP = [ ( 0.6, 7.72 ), ( 0.63, 7.74 ), ( 0.63, 8.4 ), ( 0.5, 8.46 ), ( 0.0, 8.46 ) ]
# A pothos leaf's outline, ( along from the stalk, across ), for a leaf 1 long.
LEAF = [ ( 0.0, 0.0 ), ( 0.1, 0.3 ), ( 0.4, 0.48 ), ( 0.72, 0.42 ), ( 0.95, 0.22 ), ( 1.12, 0.0 ), ( 0.95, -0.22 ),
         ( 0.72, -0.42 ), ( 0.4, -0.48 ), ( 0.1, -0.3 ) ]
# The trailing plant's vines, from the pot's base ( x, y forward, z up ): over the counter's front and along it.
VINES = ( ( ( 0.6, 0.8, 4.6 ), ( 1.8, 3.6, 5.8 ), ( 2.4, 6.3, 3.4 ), ( 2.6, 7.0, 0.3 ), ( 2.9, 7.2, -7.0 ), ( 2.6, 7.3, -16.0 ) ),
          ( ( -0.8, 0.9, 4.6 ), ( -2.4, 3.4, 5.4 ), ( -3.6, 6.4, 2.4 ), ( -4.0, 7.0, -1.8 ), ( -4.4, 7.2, -9.5 ) ),
          ( ( 0.0, 1.0, 4.6 ), ( -0.2, 3.8, 6.2 ), ( -0.5, 6.5, 3.6 ), ( -0.6, 7.1, 0.0 ), ( -0.9, 7.3, -5.0 ),
            ( -0.6, 7.4, -12.5 ), ( -1.0, 7.4, -20.0 ) ),
          ( ( 1.4, 0.6, 4.6 ), ( 4.0, 3.0, 5.0 ), ( 5.6, 6.3, 2.4 ), ( 5.9, 7.0, -0.8 ), ( 6.2, 7.1, -6.5 ) ),
          ( ( 1.0, -0.2, 4.6 ), ( 3.4, 0.5, 3.4 ), ( 6.4, 1.6, 0.7 ), ( 9.4, 2.4, 0.45 ), ( 12.0, 3.0, 0.5 ), ( 14.2, 3.4, 0.5 ) ),
          ( ( -0.3, -0.5, 4.6 ), ( -0.7, -1.0, 7.6 ), ( 0.1, -1.6, 10.4 ) ),
          ( ( 0.2, 0.3, 4.6 ), ( -1.4, -0.4, 7.2 ), ( -3.2, -1.6, 8.4 ), ( -4.4, -2.4, 7.6 ) ),
          ( ( 0.9, 0.5, 4.6 ), ( 1.6, 1.4, 7.8 ), ( 1.2, 2.6, 9.6 ) ),
          ( ( -0.6, -0.2, 4.6 ), ( -2.0, 0.6, 6.8 ), ( -3.6, 1.6, 7.0 ) ) )


def _kiosk_uv( name ):
    u0, v0, u1, v1 = _rect( "rw_kiosk", name )
    return [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]


def _kiosk_aspect( name ):
    try:
        import railhead_kiosk_art as KA
        return KA.aspect( name )
    except Exception:
        return 1.0


def _lean( p, a ):
    """ ( x, y, z ) turned about x by a radians, its top going back (towards -y). """
    x, y, z = p
    return ( x, y * math.cos( a ) - z * math.sin( a ), y * math.sin( a ) + z * math.cos( a ) )


def _leaned( F, at, a ):
    """ A function placing points of a thing standing at at ( x, y, z ) in the frame and leaning back by a radians. """
    def place( x, y, z ):
        lx, ly, lz = _lean( ( x, y, z ), a )
        return F.p( at[0] + lx, at[1] + ly, at[2] + lz )
    return place


def _kbox( model, F, place, x0, x1, y0, y1, z0, z1, paints, cover=None, a=0.0 ):
    """ A box in place's space (see _leaned): paints is one paint or { "front", "back", "sides", "top", "bottom" }; cover
    puts rw_kiosk's entry on its front (+y) face. """
    def paint( key ):
        return paints.get( key, paints.get( "default" ) ) if isinstance( paints, dict ) else paints

    c = [ [ [ place( x, y, z ) for z in ( z0, z1 ) ] for y in ( y0, y1 ) ] for x in ( x0, x1 ) ]
    t = lambda v: _lean( v, a )
    faces = { "front": ( [ c[0][1][0], c[1][1][0], c[1][1][1], c[0][1][1] ], t( ( 0, 1, 0 ) ) ),
              "back": ( [ c[1][0][0], c[0][0][0], c[0][0][1], c[1][0][1] ], t( ( 0, -1, 0 ) ) ),
              "right": ( [ c[1][1][0], c[1][0][0], c[1][0][1], c[1][1][1] ], t( ( 1, 0, 0 ) ) ),
              "left": ( [ c[0][0][0], c[0][1][0], c[0][1][1], c[0][0][1] ], t( ( -1, 0, 0 ) ) ),
              "top": ( [ c[0][1][1], c[1][1][1], c[1][0][1], c[0][0][1] ], t( ( 0, 0, 1 ) ) ),
              "bottom": ( [ c[0][0][0], c[1][0][0], c[1][1][0], c[0][1][0] ], t( ( 0, 0, -1 ) ) ) }
    for key, ( pts, towards ) in faces.items():
        p = paint( "sides" if key in ( "left", "right" ) and isinstance( paints, dict ) and "sides" in paints else key )
        if key == "front" and cover:
            outward( model, "rw_kiosk", pts, _world( F, towards ), uv=_kiosk_uv( cover ) )
        elif p:
            outward( model, p, pts, _world( F, towards ) )


def _lathe( model, F, at, profile, paints, sides=10, uv=None ):
    """ A round thing turned about the frame's z through at ( x, y, z ): profile ( r, z ) from the bottom up, paints[k]
    the band from point k to k + 1. uv: { k: rw_kiosk entry } wraps an entry once round band k, its seam at the back,
    reading left to right from the front. Shaded smooth round, and up it where the profile turns less than 40 degrees. """
    def ring( t ):
        return -math.sin( t ) * F.x - math.cos( t ) * F.y

    dirs = [ ring( 2 * math.pi * k / sides ) for k in range( sides + 1 ) ]
    seg = []
    for ( r0, z0 ), ( r1, z1 ) in zip( profile, profile[1:] ):
        length = math.hypot( r1 - r0, z1 - z0 ) or 1.0
        seg.append( ( ( z1 - z0 ) / length, ( r0 - r1 ) / length ) )      # ( outwards, up ) of the band's surface
    o = F.p( *at )
    for k, ( ( r0, z0 ), ( r1, z1 ) ) in enumerate( zip( profile, profile[1:] ) ):
        paint = paints[k]
        if paint is None or ( r0 == 0 and r1 == 0 ):
            continue
        ends = []
        for j, nb in ( ( k - 1, 0 ), ( k + 1, 1 ) ):
            a = seg[k]
            if 0 <= j < len( seg ) and a[0] * seg[j][0] + a[1] * seg[j][1] > math.cos( math.radians( 40 ) ):
                b = seg[j]
                a = ( a[0] + b[0], a[1] + b[1] )
                n = math.hypot( *a )
                a = ( a[0] / n, a[1] / n )
            ends.append( a )
        u0, v0, u1, v1 = _rect( "rw_kiosk", uv[k] ) if uv and k in uv else ( 0, 0, 1, 1 )
        for i in range( sides ):
            d0, d1 = dirs[i], dirs[i + 1]
            pts = [ o + r0 * d0 + z0 * F.z, o + r0 * d1 + z0 * F.z, o + r1 * d1 + z1 * F.z, o + r1 * d0 + z1 * F.z ]
            nrm = [ ends[0][0] * d0 + ends[0][1] * F.z, ends[0][0] * d1 + ends[0][1] * F.z,
                    ends[1][0] * d1 + ends[1][1] * F.z, ends[1][0] * d0 + ends[1][1] * F.z ]
            mid = ( seg[k][0] * ( d0 + d1 ) / 2 + seg[k][1] * F.z )
            if uv and k in uv:
                a0, a1 = u0 + ( u1 - u0 ) * i / sides, u0 + ( u1 - u0 ) * ( i + 1 ) / sides
                outward( model, "rw_kiosk", pts, mid, uv=[ ( a0, v0 ), ( a1, v0 ), ( a1, v1 ), ( a0, v1 ) ], normals=nrm )
            elif r0 == 0 or r1 == 0:
                if r0 == 0:
                    tri, tri_n = [ pts[0], pts[2], pts[3] ], [ nrm[0], nrm[2], nrm[3] ]
                else:
                    tri, tri_n = [ pts[0], pts[1], pts[2] ], [ nrm[0], nrm[1], nrm[2] ]
                outward( model, paint, tri, mid, normals=tri_n )
            else:
                outward( model, paint, pts, mid, normals=nrm )


def _bottle( model, F, x, y, z, label ):
    liquid, cap = KIOSK_DRINKS[label]
    paints = [ liquid ] * ( len( BOTTLE ) - 1 )
    _lathe( model, F, ( x, y, z ), BOTTLE, paints, 10, uv={ 4: label } )
    _lathe( model, F, ( x, y, z ), BOTTLE_CAP, [ cap ] * ( len( BOTTLE_CAP ) - 1 ), 10 )


def _packet( model, F, name, x, y, z, w, h, t, lean ):
    """ A crisp packet standing on its bottom seal at ( x, y, z ), its front towards +y, leaning back lean degrees: a
    foil pillow, flat at the crimped seals, printed with rw_kiosk's name front and back. """
    u0, v0, u1, v1 = _rect( "rw_kiosk", name )
    a = math.radians( lean )
    seal = 0.09 * h

    def depth( fx, fz ):
        across = max( 0.0, 1.0 - ( 2 * fx / w ) ** 2 ) ** 0.5
        along = 0.0 if fz <= seal or fz >= h - seal else math.sin( math.pi * ( fz - seal ) / ( h - 2 * seal ) ) ** 0.6
        return across * ( 0.06 + t / 2 * along )

    def point( fx, fz, s ):
        lx, ly, lz = _lean( ( fx, s * depth( fx, fz ), fz ), a )
        return F.p( x + lx, y + ly, z + lz )

    def normal( fx, fz, s ):
        e = 0.05
        dx = ( depth( min( fx + e, w / 2 ), fz ) - depth( max( fx - e, -w / 2 ), fz ) ) / ( 2 * e )
        dz = ( depth( fx, min( fz + e, h ) ) - depth( fx, max( fz - e, 0.0 ) ) ) / ( 2 * e )
        return _unit( _world( F, _lean( ( -dx, s, -dz ), a ) ) )

    xs = [ -w / 2 + w * i / 6 for i in range( 7 ) ]
    zs = [ 0.0, seal ] + [ seal + ( h - 2 * seal ) * k / 6 for k in range( 1, 6 ) ] + [ h - seal, h ]
    for s in ( 1.0, -1.0 ):
        for i in range( 6 ):
            for j in range( len( zs ) - 1 ):
                corners = [ ( xs[i], zs[j] ), ( xs[i + 1], zs[j] ), ( xs[i + 1], zs[j + 1] ), ( xs[i], zs[j + 1] ) ]
                pts = [ point( cx, cz, s ) for cx, cz in corners ]
                nrm = [ normal( cx, cz, s ) for cx, cz in corners ]
                uv = []
                for cx, cz in corners:
                    fu = ( cx + w / 2 ) / w
                    uv.append( ( u0 + ( u1 - u0 ) * ( fu if s > 0 else 1.0 - fu ), v0 + ( v1 - v0 ) * cz / h ) )
                outward( model, "rw_kiosk", pts, nrm[0] + nrm[1] + nrm[2] + nrm[3], uv=uv, normals=nrm )


def _leaf( model, F, p, along, face, size, paint ):
    """ A pothos leaf from p, its tip along along and its face turned towards face (frame vectors), folded a little at
    the midrib. Drawn from both sides. """
    a = _unit( _world( F, along ) )
    f = _world( F, face )
    across = _unit( np.cross( f, a ) )
    up = np.cross( a, across )
    base = F.p( *p )
    pts = [ base + a * u * size + across * v * size + up * abs( v ) * size * 0.28 for u, v in LEAF ]
    model.polygon( paint, pts, both_sides=True )


def _catmull( points, per=4 ):
    pts = [ points[0] ] + list( points ) + [ points[-1] ]
    out = []
    for k in range( 1, len( pts ) - 2 ):
        p0, p1, p2, p3 = ( np.asarray( q, float ) for q in pts[k - 1:k + 3] )
        for j in range( per ):
            t = j / per
            out.append( 0.5 * ( 2 * p1 + ( -p0 + p2 ) * t + ( 2 * p0 - 5 * p1 + 4 * p2 - p3 ) * t * t
                                + ( -p0 + 3 * p1 - 3 * p2 + p3 ) * t ** 3 ) )
    out.append( np.asarray( points[-1], float ) )
    return out


def _plant( model, F, x, y, z ):
    """ A golden pothos trailing from a white ceramic pot standing at ( x, y, z ): its vines arch out of the pot, over
    the counter's front edge and along it, a heart-shaped leaf every 1.4 in, growing smaller towards the tips. """
    o = F.p( x, y, z )
    _frustum( model, o + 0.0 * F.z, o + 4.4 * F.z, 2.1, 2.6, "rw_pot", sides=16 )
    disc( model, "rw_pot", o + 0.02 * F.z, -F.z, 2.1, sides=16 )
    _frustum( model, o + 3.9 * F.z, o + 4.4 * F.z, 2.38, 2.42, "rw_pot", sides=16, inside="rw_pot" )
    for k in range( 16 ):
        t0, t1 = 2 * math.pi * k / 16, 2 * math.pi * ( k + 1 ) / 16
        d0, d1 = math.cos( t0 ) * F.x + math.sin( t0 ) * F.y, math.cos( t1 ) * F.x + math.sin( t1 ) * F.y
        outward( model, "rw_pot", [ o + 4.4 * F.z + 2.42 * d0, o + 4.4 * F.z + 2.6 * d0, o + 4.4 * F.z + 2.6 * d1,
                                    o + 4.4 * F.z + 2.42 * d1 ], F.z )
    disc( model, "rw_soil", o + 4.0 * F.z, F.z, 2.45, sides=16 )
    def rnd( *key ):
        n = 0
        for kk in key:
            n = ( n * 73856093 ^ ( kk + 1 ) * 19349663 ) & 0xFFFFFF
        return n % 1000 / 1000.0

    for j in range( 7 ):                                # the crown, radiating from the pot
        t = 2 * math.pi * j / 7 + 0.3
        c, sn = math.cos( t ), math.sin( t )
        at = ( x + 0.7 * c, y + 0.7 * sn, z + 4.7 + 0.6 * rnd( j, 1 ) )
        _leaf( model, F, at, ( 0.85 * c, 0.85 * sn, 0.45 + 0.3 * rnd( j, 2 ) ), ( -0.35 * c, -0.35 * sn, 1.0 ), 1.7 + 0.4 * rnd( j, 3 ),
               "rw_leaf_light" if j % 3 == 0 else "rw_leaf" )
    k = 0
    for v, vine in enumerate( VINES ):
        path = _catmull( [ ( x + px, y + py, z + pz ) for px, py, pz in vine ], 5 )
        polyline( model, [ F.p( *q ) for q in path ], 0.08, "rw_leaf", 4 )
        run, total = 0.0, sum( float( np.linalg.norm( q - p ) ) for p, q in zip( path, path[1:] ) )
        next_at = 0.6
        for p, q in zip( path, path[1:] ):
            seg = float( np.linalg.norm( q - p ) )
            while next_at <= run + seg and next_at < total - 0.1:
                at = p + ( q - p ) * ( ( next_at - run ) / seg )
                tangent = ( q - p ) / seg
                side = 1.0 if k % 2 else -1.0
                h, h2, h3 = rnd( v, k, 1 ), rnd( v, k, 2 ), rnd( v, k, 3 )
                sideways = np.cross( tangent, ( 0.0, 0.0, 1.0 ) )
                if float( np.linalg.norm( sideways ) ) < 0.3:
                    sideways = np.array( ( 1.0, 0.0, 0.0 ) )
                sideways = _unit( sideways ) * side
                if tangent[2] < -0.5:                   # hanging: the leaves turn out to the light and droop
                    along = _unit( sideways * 0.75 + np.array( ( 0.4 * ( h2 - 0.5 ), 0.45, -0.35 - 0.3 * h3 ) ) )
                    face = np.array( ( 0.5 * ( h3 - 0.5 ), 1.0, 0.25 + 0.3 * h2 ) )
                else:
                    along = _unit( sideways * 0.8 + tangent * 0.45 + np.array( ( 0.0, 0.0, 0.1 + 0.25 * h2 ) ) )
                    face = np.array( ( 0.3 * side * ( h3 - 0.3 ), 0.25, 1.0 ) )
                size = 1.0 + 0.9 * min( 1.0, ( total - next_at ) / 5.0 ) + 0.3 * h
                _leaf( model, F, at, along, face, size, "rw_leaf_light" if h3 > 0.62 else "rw_leaf" )
                k += 1
                next_at += 0.9 + 0.4 * h
            run += seg


def _card_terminal( model, F, x, y, z ):
    """ The reference's rounded metal terminal, detailed keypad and reader panels. """
    import railhead_card_reader
    railhead_card_reader.build( model, F, x, y, z )


def _frect_place( model, F, place, x0, x1, y, z0, z1, name, a, paint=None ):
    pts = [ place( x0, y, z0 ), place( x1, y, z0 ), place( x1, y, z1 ), place( x0, y, z1 ) ]
    towards = _world( F, _lean( ( 0, 1, 0 ), a ) )
    if name:
        outward( model, "rw_kiosk", pts, towards, uv=_kiosk_uv( name ) )
    else:
        outward( model, paint, pts, towards )


def _pen_cup( model, F, x, y, z ):
    o = F.p( x, y, z )
    _frustum( model, o, o + 3.6 * F.z, 1.15, 1.2, "rw_steel_grey", sides=12, inside=DARK )
    disc( model, DARK, o + 0.4 * F.z, F.z, 1.1, sides=12 )
    for k, ( dx, dy, paint ) in enumerate( ( ( 0.5, 0.2, "rw_train_blue" ), ( -0.4, 0.4, "rw_black" ), ( 0.1, -0.5, "rw_red_paint" ) ) ):
        tip = o + ( dx * 2.6 ) * F.x + ( dy * 2.6 ) * F.y + 6.0 * F.z
        rod( model, o + dx * 0.4 * F.x + dy * 0.4 * F.y + 0.5 * F.z, tip, 0.17, paint, 6, caps=( False, True ) )


def _candy_tray( model, F, x0, x1, y, z, names ):
    """ A counter display of sweet bars at the shelf's front: a sloping cardboard tray, the bars lying in it in shingled
    rows with their wrappers up, a column of each of names across it. """
    a = math.radians( 58 )
    place = _leaned( F, ( 0.0, y, z ), a )
    depth = 7.2
    _kbox( model, F, place, x0, x1, -0.4, 0.0, 0.0, depth, "rw_kiosk_shelf", a=a )
    for xa, side in ( ( x0, -1.0 ), ( x1, 1.0 ) ):
        pts = [ place( xa, 0.0, 0.0 ), place( xa, 0.0, depth ), place( xa, 1.6, depth ), place( xa, 2.2, 0.0 ) ]
        outward( model, "rw_kiosk_shelf", pts, side * F.x )
        outward( model, "rw_kiosk_shelf", pts, -side * F.x )
    lip = [ place( x0, 0.0, 0.0 ), place( x1, 0.0, 0.0 ), place( x1, 2.2, 0.0 ), place( x0, 2.2, 0.0 ) ]
    outward( model, "rw_kiosk_shelf", lip, _world( F, _lean( ( 0, 0, -1 ), a ) ) )
    outward( model, "rw_kiosk_shelf", lip, _world( F, _lean( ( 0, 0, 1 ), a ) ) )
    width = ( x1 - x0 - 0.6 ) / len( names )
    for c, name in enumerate( names ):
        bx0 = x0 + 0.3 + c * width + 0.15
        bx1 = bx0 + width - 0.3
        for r in range( 4 ):
            zb = 0.3 + r * 1.7
            _kbox( model, F, place, bx0, bx1, 0.0, 0.55, zb, zb + 1.65, { "default": "rw_kiosk_shelf" }, cover=None, a=a )
            _frect_place( model, F, place, bx0, bx1, 0.56, zb, zb + 1.65, name, a )


def _kiosk_vitrine( model, F, side, hx, y0, y1, z0, z1, name ):
    """ A lit vitrine on the kiosk's end at x = side * hx, from y0 to y1 and z0 to z1: a brushed aluminium frame
    standing 1.2 proud, a white light box recessed in it and the atlas's picture (name) on it, backlit. """
    face = "right" if side > 0 else "left"
    x = side * hx
    fw = 1.4
    for a, b, c, d in ( ( y0, y1, z0, z0 + fw ), ( y0, y1, z1 - fw, z1 ), ( y0, y0 + fw, z0, z1 ), ( y1 - fw, y1, z0, z1 ) ):
        F.box( model, x, x + side * 1.2, a, b, c, d, "rw_alu_brushed", skip=( "left" if side > 0 else "right", ) )
    _xrect( model, F, "rw_kiosk_fascia", x + side * 0.5, y0 + fw, y1 - fw, z0 + fw, z1 - fw, side )
    w, h = y1 - y0 - 2 * fw - 2.0, z1 - z0 - 2 * fw - 2.0
    aspect = _kiosk_aspect( name )
    if w / h > aspect:
        w = h * aspect
    else:
        h = w / aspect
    F.quad( model, "rw_kiosk_backlit", x + side * 0.56, ( y0 + y1 ) / 2, ( z0 + z1 ) / 2, w, h, face, uv=_kiosk_uv( name ) )
    # Two screw caps in the frame's top rail: it lifts off to change the poster.
    for y in ( y0 + ( y1 - y0 ) * 0.25, y0 + ( y1 - y0 ) * 0.75 ):
        disc( model, "rw_steel_grey", F.p( x + side * 1.22, y, z1 - fw / 2 ), F.x * side, 0.3, sides=8 )


def _kiosk_roof( model, F, x0, x1, y0, y1, z ):
    """ What's on the kiosk's flat roof, seen from the booking hall's gallery: a 60 mm aluminium upstand round the grey
    membrane, its welded seams, a scupper, an air-conditioning condenser (0.9 x 0.6 x 0.5 m) on rubber feet with its fan
    grille and fins, and the galvanised cable tray from it to a roof gland. Visual only. """
    up, t = 2.4, 1.2
    for a, b, c, d in ( ( x0, x1, y0, y0 + t ), ( x0, x1, y1 - t, y1 ), ( x0, x0 + t, y0, y1 ), ( x1 - t, x1, y0, y1 ) ):
        F.box( model, a, b, c, d, z, z + up, "rw_alu_brushed", skip=( "bottom", ) )
    for k in range( 1, 4 ):                             # the membrane's welded seams, 1 m apart
        y = y0 + ( y1 - y0 ) * k / 4
        F.box( model, x0 + t, x1 - t, y - 0.6, y + 0.6, z, z + 0.08, "rw_kiosk_membrane", skip=( "bottom", ) )
    F.box( model, x0 - 1.6, x0, y0 + 6.0, y0 + 9.0, z - 0.5, z + 0.9, "rw_alu_brushed" )        # the scupper
    # The condenser at the back corner, on two rubber-footed rails.
    cx0, cx1, cy0, cy1 = x0 + 6.0, x0 + 41.0, y0 + 4.0, y0 + 28.0
    for yy in ( cy0 + 3.0, cy1 - 3.0 ):
        F.box( model, cx0 - 1.0, cx1 + 1.0, yy - 1.0, yy + 1.0, z, z + 1.6, "rw_rubber", skip=( "bottom", ) )
    zc0, zc1 = z + 1.6, z + 21.3
    F.box( model, cx0, cx1, cy0, cy1, zc0, zc1, { "default": "rw_vend_cabinet", "top": "rw_kiosk_white" },
           skip=( "bottom", ) )
    for k in range( 9 ):                                # the coil's fins behind a grille on the back face
        x = cx0 + 2.0 + ( cx1 - cx0 - 4.0 ) * k / 8
        F.box( model, x - 0.15, x + 0.15, cy0 - 0.3, cy0, zc0 + 2.0, zc1 - 2.0, "rw_steel_dark", skip=( "back", ) )
    xc, zm = cx0 + 13.0, ( zc0 + zc1 ) / 2              # the fan on the front face: a dark throat, rings and a hub
    face = cy1 + 0.02
    disc( model, "rw_black", F.p( xc, face, zm ), F.y, 8.2, sides=24 )
    for r in ( 2.6, 5.0, 7.4, 8.4 ):
        ring = [ F.p( xc + r * math.cos( a_ ), face + 0.3, zm + r * math.sin( a_ ) ) for a_ in np.linspace( 0, math.tau, 25 ) ]
        for p_, q_ in zip( ring, ring[1:] ):
            rod( model, p_, q_, 0.12, "rw_steel_grey", 4 )
    for a_ in np.linspace( 0, math.tau, 9 )[:-1]:
        rod( model, F.p( xc, face + 0.3, zm ), F.p( xc + 8.4 * math.cos( a_ ), face + 0.3, zm + 8.4 * math.sin( a_ ) ),
             0.1, "rw_steel_grey", 4 )
    disc( model, "rw_steel_grey", F.p( xc, face + 0.35, zm ), F.y, 1.4, sides=12 )
    F.box( model, cx1 - 8.0, cx1 - 2.0, cy1, cy1 + 0.4, zc0 + 4.0, zc0 + 12.0, "rw_kiosk_white" )   # its service plate
    # The cable tray from the condenser across the roof to the gland at its middle.
    gx, gy = ( x0 + x1 ) / 2, ( y0 + y1 ) / 2
    F.box( model, cx1, gx + 1.5, cy0 + 9.0, cy0 + 13.0, z + 0.4, z + 2.0, "rw_galvanised", skip=( "bottom", ) )
    F.box( model, gx - 1.5, gx + 1.5, cy0 + 9.0, gy, z + 0.4, z + 2.0, "rw_galvanised", skip=( "bottom", ) )
    rod( model, F.p( gx, gy, z ), F.p( gx, gy, z + 4.0 ), 1.6, "rw_steel_grey", 10, caps=( False, True ) )


def kiosk( model, e0, e1, n0, n1, facing, z0=0.0 ):
    """ A modern station kiosk 2.76 m tall over e0..e1, n0..n1, after the user's reference picture: anthracite steel
    cladding with shadow gaps on a recessed black plinth, a flat roof slab overhanging with warm LED strips under it,
    and a fascia proud of the walls lettered "Kiosk" and "Zeitschriften · Getraenke · Snacks" in white on its front and
    both ends. Its front has a pier with line icons (a newspaper, a bottle, a crisp packet), the serving window and a
    corner pier; the window has a light stone counter on vertical oak slats lit from under it, and behind it lit
    shelves of magazines, sweets, crisps and bottled drinks. On the counter: a trailing pothos in a white pot, a card
    terminal and a pen cup. Its right end (from the front) has a menu board and a framed poster, its left the staff
    door, its back a louvred vent.
    Since 2026-10: a backlit opal fascia (a white light box with the lettering printed dark), a lighter brushed graphite
    cladding, a wider serving window between slimmer piers with a roller shutter's box and guide rails at its head, a
    stainless nosing on the counter, white reveals and ceiling so the shelf lights bounce, and lit poster vitrines on
    both ends. Collision: the kiosk, its counter, fascia and roof slab (metal), unchanged. """
    CLAD, WHITE, STEEL = "rw_kiosk_clad", "rw_kiosk_white", "rw_stainless"
    F = frame_for( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z0, facing )
    along_e = abs( F.x[0] ) > 0.5
    hx = abs( e1 - e0 ) / 2 if along_e else abs( n1 - n0 ) / 2
    hy = abs( n1 - n0 ) / 2 if along_e else abs( e1 - e0 ) / 2
    PL, ZC, ZO, ZF, ZR = KIOSK_PLINTH, KIOSK_COUNTER, KIOSK_OPEN, KIOSK_FASCIA, KIOSK_ROOF
    CL, GAP = 0.4, 0.45                                 # the cladding panels' thickness and the shadow gaps
    xl, xr = -hx + 11.0, hx - 11.0                      # the serving window between the piers
    yb = hy - 30.0                                      # the shelves' back panel
    fp = 1.2                                            # the fascia stands this far proud of the walls

    # The plinth, and the walls' black core behind the cladding.
    F.box( model, -hx + 1.0, hx - 1.0, -hy + 1.0, hy - 1.0, 0.0, PL, "rw_black", skip=( "bottom", "top" ) )
    F.box( model, -hx + CL, hx - CL, -hy + CL, hy - CL, PL, ZO, { "default": "rw_black", "front": None },
           skip=( "bottom", "top" ) )

    def panels( lo, hi, width ):
        count = max( 1, round( ( hi - lo ) / width ) )
        edges = [ lo + ( hi - lo ) * k / count for k in range( count + 1 ) ]
        return [ ( a + ( GAP / 2 if k else 0.0 ), b - ( GAP / 2 if k < count - 1 else 0.0 ) )
                 for k, ( a, b ) in enumerate( zip( edges, edges[1:] ) ) ]

    rows = ( ( PL, ZC - GAP / 2 ), ( ZC + GAP / 2, ZO ) )
    for s in ( 1.0, -1.0 ):                             # the ends' cladding: 24 in panels, split at counter height
        for a, b in panels( -hy, hy - CL, 24.0 ):
            for z_0, z_1 in rows:
                xa, xb = ( hx - CL, hx ) if s > 0 else ( -hx, -hx + CL )
                F.box( model, xa, xb, a, b, z_0, z_1, CLAD, skip=( "top", ) if z_1 >= ZO else () )
    for a, b in panels( -hx + CL, hx - CL, 24.0 ):      # the back's, between the ends
        for z_0, z_1 in rows:
            F.box( model, a, b, -hy, -hy + CL, z_0, z_1, CLAD, skip=( "top", ) if z_1 >= ZO else () )
    for a, b in ( ( -hx, xl ), ( xr, hx ) ):            # the piers: 600 mm panels with 12 mm shadow gaps between
        F.box( model, a + 0.2, b - 0.2, hy - CL - 0.3, hy - CL, PL, ZO, "rw_black", skip=( "top", "bottom" ) )
        for z_0, z_1 in panels( PL, ZO, 24.0 ):
            F.box( model, a, b, hy - CL, hy, z_0, z_1, CLAD, skip=( "top", ) if z_1 >= ZO else () )

    # The pier's icons.
    iw = 7.4
    F.atlas( model, "rw_kiosk", "icons", ( -hx + xl ) / 2, hy + 0.04, 60.0, iw, iw / _kiosk_aspect( "icons" ), "front" )

    # The fascia, the roof slab and its LED strips.
    # The fascia: a white opal light box in a graphite frame.
    F.box( model, -hx - fp, hx + fp, -hy - fp, hy + fp, ZO, ZF, { "default": "rw_kiosk_fascia", "bottom": CLAD,
                                                                  "back": CLAD } )
    for z_a, z_b in ( ( ZO - 0.3, ZO + 1.1 ), ( ZF - 1.1, ZF ) ):
        F.box( model, -hx - fp - 0.35, hx + fp + 0.35, -hy - fp - 0.35, hy + fp + 0.35, z_a, z_b, CLAD )
    for xx in ( -hx - fp - 0.35, hx + fp + 0.35 ):
        for yy in ( -hy - fp - 0.35, hy + fp + 0.35 ):
            F.box( model, xx - 0.9, xx + 0.9, yy - 0.9, yy + 0.9, ZO - 0.3, ZF, CLAD )
    F.box( model, -hx - 7.0, hx + 7.0, -hy - 5.0, hy + 9.0, ZF, ZR, { "default": CLAD, "bottom": WHITE,
                                                                       "top": "rw_kiosk_membrane" } )
    _kiosk_roof( model, F, -hx - 7.0, hx + 7.0, -hy - 5.0, hy + 9.0, ZR )
    for x0_, x1_, y0_, y1_ in ( ( -hx - 4.0, hx + 4.0, hy + 4.4, hy + 5.4 ), ( hx + 3.6, hx + 4.6, -hy - 2.0, hy + 5.4 ),
                                ( -hx - 4.6, -hx - 3.6, -hy - 2.0, hy + 5.4 ) ):
        F.box( model, x0_, x1_, y0_, y1_, ZF - 0.5, ZF, { "default": "rw_steel_grey", "bottom": "rw_lamp_warm" },
               skip=( "top", ) )
    # Lettering: "Kiosk" over the line of goods, on the front and both ends.
    ww, sw = 30.5, 48.0
    wh, sh = ww / _kiosk_aspect( "kiosk_word" ), sw / _kiosk_aspect( "kiosk_sub" )
    for face, x, y in ( ( "front", 0.0, hy + fp + 0.04 ), ( "right", hx + fp + 0.04, 0.0 ), ( "left", -hx - fp - 0.04, 0.0 ) ):
        for name, z, w, h in ( ( "kiosk_word", 97.8, ww, wh ), ( "kiosk_sub", 89.3, sw, sh ) ):
            F.quad( model, "rw_kiosk_ink", x, y, z, w, h, face, uv=_kiosk_uv( name ) )

    # The serving window: its reveals, ceiling (an LED line along its front, downlights over the shelves) and the
    # space behind the counter.
    _xrect( model, F, WHITE, xl, yb, hy, PL, ZO, 1.0 )
    _xrect( model, F, WHITE, xr, yb, hy, PL, ZO, -1.0 )
    _fpoly( model, F, WHITE, [ ( xl, yb, ZO ), ( xr, yb, ZO ), ( xr, hy, ZO ), ( xl, hy, ZO ) ], ( 0, 0, -1 ) )
    # The roller shutter's box across the window's head (the shutter rolled up in it), its bottom bar and pull
    # handles, an LED line under the box, and the guide rails down both reveals.
    F.box( model, xl, xr, hy - 11.0, hy - 1.2, ZO - 6.5, ZO, CLAD, skip=( "top", ) )
    F.box( model, xl, xr, hy - 4.4, hy - 2.0, ZO - 7.4, ZO - 6.5, STEEL, skip=( "top", ) )
    for xh in ( xl + 9.0, xr - 9.0 ):
        F.box( model, xh - 2.0, xh + 2.0, hy - 2.0, hy - 1.4, ZO - 7.3, ZO - 6.7, STEEL )
    F.box( model, xl + 0.6, xr - 0.6, hy - 9.0, hy - 7.8, ZO - 6.9, ZO - 6.5, { "default": "rw_steel_grey",
                                                                               "bottom": "rw_lamp_warm" }, skip=( "top", ) )
    for xg, sg in ( ( xl, 1.0 ), ( xr, -1.0 ) ):
        F.box( model, xg, xg + sg * 1.1, hy - 4.6, hy - 1.8, ZC, ZO - 6.5, STEEL )
        F.box( model, xg + sg * 1.1, xg + sg * 1.25, hy - 3.6, hy - 2.8, ZC, ZO - 6.5, "rw_black", skip=( "top", ) )
    for k in range( 3 ):
        x = xl + ( xr - xl ) * ( k + 0.5 ) / 3
        disc( model, "rw_steel_grey", F.p( x, yb + 13.0, ZO - 0.03 ), -F.z, 1.6, sides=12 )
        disc( model, "rw_lamp_warm", F.p( x, yb + 13.0, ZO - 0.06 ), -F.z, 1.05, sides=12 )
    _fpoly( model, F, "rw_black", [ ( xl, yb, PL ), ( xr, yb, PL ), ( xr, hy - 14.0, PL ), ( xl, hy - 14.0, PL ) ], ( 0, 0, 1 ) )
    _frect( model, F, WHITE, xl, xr, hy - 14.0, PL, ZC - 2.0, -1.0 )

    # The counter: a light stone top on oak slats, an LED strip under its front edge.
    F.box( model, xl - 2.0, xr + 2.0, hy - 14.0, hy + 4.5, ZC - 2.0, ZC, "rw_kiosk_stone" )
    F.box( model, xl - 2.2, xr + 2.2, hy + 4.5, hy + 5.0, ZC - 2.25, ZC + 0.08, STEEL )         # the nosing
    for xe in ( xl - 2.2, xr + 2.0 ):
        F.box( model, xe, xe + 0.2, hy - 14.0, hy + 5.0, ZC - 2.25, ZC + 0.08, STEEL )
    F.box( model, xl, xr, hy + 2.5, hy + 3.5, ZC - 2.4, ZC - 2.0, { "default": "rw_steel_grey", "bottom": "rw_lamp_warm" },
           skip=( "top", ) )
    _frect( model, F, "rw_black", xl, xr, hy - 0.4, PL, ZC - 2.0 )
    count = int( ( xr - xl ) / 2.5 )
    pitch = ( xr - xl ) / count
    for k in range( count ):
        x = xl + pitch * ( k + 0.5 )
        F.box( model, x - 0.9, x + 0.9, hy - 0.4, hy + 0.6, PL + 0.5, ZC - 2.0, "rw_wood", skip=( "back", "top" ) )

    # The shelves: a base cabinet, three bays of wood shelves with an LED strip under each front edge.
    F.box( model, xl, xr, yb, yb + 10.0, PL, KIOSK_SHELVES[0], { "default": CLAD, "top": "rw_wood", "back": None } )
    _frect( model, F, "rw_kiosk_shelf", xl, xr, yb, KIOSK_SHELVES[0], ZO )
    bays = [ ( xl + ( xr - xl ) * k / 3, xl + ( xr - xl ) * ( k + 1 ) / 3 ) for k in range( 3 ) ]
    for k, ( a, b ) in enumerate( bays ):
        if k:
            F.box( model, a - 0.6, a + 0.6, yb, yb + 10.4, KIOSK_SHELVES[0], ZO, "rw_wood", skip=( "back", "top" ) )
        a, b = a + ( 0.6 if k else 0.0 ), b - ( 0.6 if k < 2 else 0.0 )
        for z in KIOSK_SHELVES[1:]:
            F.box( model, a, b, yb, yb + 10.0, z - 1.0, z, "rw_wood", skip=( "back", ) )
            _frect( model, F, "rw_white_paint", a + 0.4, b - 0.4, yb + 10.03, z - 0.85, z - 0.2 )
        for z in KIOSK_SHELVES:
            under = z - 1.0 if z > KIOSK_SHELVES[0] else None
            if under:
                _fpoly( model, F, "rw_lamp_warm", [ ( a, yb + 8.4, under - 0.02 ), ( b, yb + 8.4, under - 0.02 ),
                                                    ( b, yb + 9.0, under - 0.02 ), ( a, yb + 9.0, under - 0.02 ) ], ( 0, 0, -1 ) )
        if k == 0:                                      # magazines, two covers a shelf, leaning on the back
            for row, z in enumerate( KIOSK_SHELVES ):
                for c in range( 2 ):
                    name = f"mag_{( row * 2 + c ) % 8}"
                    mw = 8.3
                    mx = a + ( b - a ) * ( c + 0.5 ) / 2
                    at = ( mx, yb + 3.4, z )
                    lean = math.radians( 13.0 )
                    _kbox( model, F, _leaned( F, at, lean ), -mw / 2, mw / 2, -0.7, 0.0, 0.0, 10.0,
                           { "default": "rw_white_paint", "back": "rw_white_paint" }, cover=name, a=lean )
                F.box( model, a + 0.3, b - 0.3, yb + 3.4, yb + 4.1, z, z + 1.4, "rw_steel_grey", skip=( "bottom", ) )
        elif k == 1:                                    # sweets at the bottom, crisps above
            _candy_tray( model, F, a + 0.6, ( a + b ) / 2 - 0.3, yb + 8.0, KIOSK_SHELVES[0], ( "candy_0", "candy_1" ) )
            _candy_tray( model, F, ( a + b ) / 2 + 0.3, b - 0.6, yb + 8.0, KIOSK_SHELVES[0], ( "candy_2", "candy_3" ) )
            for row, z in enumerate( KIOSK_SHELVES[1:] ):
                for c in range( 3 ):
                    px = a + ( b - a ) * ( c + 0.5 ) / 3
                    _packet( model, F, f"chips_{( row * 3 + c ) % 5}", px, yb + 6.2, z, 6.3, 8.9, 2.6, 9.0 )
        else:                                           # bottled drinks, two kinds a shelf
            for row, z in enumerate( KIOSK_SHELVES ):
                kinds = KIOSK_DRINK_ROWS[row]
                for c in range( 6 ):
                    bx = a + ( b - a ) * ( c + 0.5 ) / 6
                    _bottle( model, F, bx, yb + 6.6, z, kinds[c // 3] )

    # On the counter.
    _plant( model, F, xl + 5.0, hy - 2.0, ZC )
    _card_terminal( model, F, xr - 15.0, hy + 0.2, ZC )
    _pen_cup( model, F, xr - 7.5, hy - 1.5, ZC )

    # The ends: a lit poster vitrine on each (the right one's beside a lit menu board, the left one's beside the staff
    # door).
    _kiosk_vitrine( model, F, 1.0, hx, -hy + 26.0, hy - 5.0, 18.0, 80.0, "poster" )
    _kiosk_vitrine( model, F, 1.0, hx, -hy + 4.0, -hy + 22.0, 46.0, 70.0, "menu" )
    _kiosk_vitrine( model, F, -1.0, hx, -hy + 40.0, hy - 5.0, 18.0, 80.0, "poster" )

    # The left end: the staff door. The back: a louvred vent.
    yd = -hy + 21.0
    F.box( model, -hx - 0.12, -hx + 0.1, yd - 15.5, yd + 15.5, PL + 0.8, 82.5, "rw_black", skip=( "right", ) )
    F.box( model, -hx - 0.3, -hx, yd - 15.0, yd + 15.0, PL + 1.3, 82.0, CLAD, skip=( "right", ) )
    rod( model, F.p( -hx - 0.3, yd + 11.5, 41.0 ), F.p( -hx - 2.2, yd + 11.5, 41.0 ), 0.35, "rw_steel_grey", 8 )
    rod( model, F.p( -hx - 2.2, yd + 11.5, 41.0 ), F.p( -hx - 2.2, yd + 6.5, 41.0 ), 0.35, "rw_steel_grey", 8,
         caps=( False, True ) )
    disc( model, "rw_steel_grey", F.p( -hx - 0.33, yd + 11.5, 37.0 ), -F.x, 0.55, sides=10 )
    for k in range( 7 ):
        z = 70.0 + 1.6 * k
        _obox( model, F, ( 0.0, -hy - 0.5, z ), ( 1, 0, 0 ), ( 0, 1, -0.7 ), ( 18.0, 1.2, 0.15 ), CLAD )
    for x0_, x1_, z0_, z1_ in ( ( -9.8, 9.8, 68.8, 69.4 ), ( -9.8, 9.8, 80.2, 80.8 ), ( -9.8, -9.2, 68.8, 80.8 ),
                                ( 9.2, 9.8, 68.8, 80.8 ) ):
        F.box( model, x0_, x1_, -hy - 0.9, -hy, z0_, z1_, CLAD, skip=( "front", ) )
    _frect( model, F, "rw_black", -9.2, 9.2, -hy - 0.02, 69.4, 80.2, -1.0 )

    # Collision.
    F.collide( model, -hx, hx, -hy, hy, 0.0, ZO, "metal" )
    F.collide( model, xl - 2.0, xr + 2.0, hy, hy + 4.5, ZC - 2.0, ZC, "metal" )
    F.collide( model, -hx - fp, hx + fp, -hy - fp, hy + fp, ZO, ZF, "metal" )
    F.collide( model, -hx - 7.0, hx + 7.0, -hy - 5.0, hy + 9.0, ZF, ZR, "metal" )


def kiosk_lights( e0, e1, n0, n1, facing, z0=0.0, fascia=False ):
    """ The kiosk's own lights for railhead_map: ( position, radius ) of one in its serving window's ceiling over the
    shelves, and a small one under the counter's front edge washing the oak slats, as its LED strip would. fascia: a
    third, warm one just under the fascia's middle, out in front, so the window's head and the counter glow as the
    light box over them would light them. """
    F = frame_for( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z0, facing )
    along_e = abs( F.x[0] ) > 0.5
    hy = abs( n1 - n0 ) / 2 if along_e else abs( e1 - e0 ) / 2
    out = [ ( tuple( float( v ) for v in F.p( 0.0, hy - 14.0, KIOSK_OPEN - 9.0 ) ), 150.0 ),
            ( tuple( float( v ) for v in F.p( -1.0, hy + 3.0, KIOSK_COUNTER - 3.0 ) ), 60.0 ) ]
    if fascia:
        out.append( ( tuple( float( v ) for v in F.p( 0.0, hy + 10.0, KIOSK_OPEN - 4.0 ) ), 90.0 ) )
    return out


def hanging_display( model, e, n, z_top, name, along="n", floor_z=0.0, width=118.1, ceiling=None ):
    """ A platform display (rw_displays name, 5:1; 3 m by default) in a 150 mm deep anthracite housing, lit on both
    faces, hung on two rods up to z_top: 450 mm under it, or higher to keep its bottom HEADROOM over floor_z. along:
    the faces look both ways along n or e. Metal collision on the housing. An optional ceiling(e, n) supplies a
    curved mounting surface: keep the whole housing below it and give each rod its own attachment height. """
    F = _along_frame( e, n, along )
    h = width / aspect( "rw_displays", name )
    hw, hh, d = width / 2 + 1.6, h / 2 + 1.6, 2.95
    limit = z_top
    if ceiling is not None:
        limit = min( limit, *( ceiling( *F.p( x, y, 0.0 )[:2] ) for x in ( -hw, hw ) for y in ( -d, d ) ) )
    bottom = _hang( limit, 2 * hh, floor_z, 17.7 )
    zc = bottom + hh
    F.box( model, -hw, hw, -d, d, bottom, bottom + 2 * hh, DARK )
    F.collide( model, -hw, hw, -d, d, bottom, bottom + 2 * hh, "metal" )
    F.atlas( model, "rw_displays", name, 0.0, d + 0.03, zc, width, h, "front" )
    F.atlas( model, "rw_displays", name, 0.0, -d - 0.03, zc, width, h, "back" )
    for x in ( -hw + 10.0, hw - 10.0 ):
        mount = z_top if ceiling is None else ceiling( *F.p( x, 0.0, 0.0 )[:2] ) + 0.5
        _rods( model, F, ( x, ), bottom + 2 * hh, mount )


def hanging_sign( model, e, n, z_top, names, along="n", floor_z=0.0, height=13.8, back_names=None ):
    """ A backlit wayfinding sign (rw_signs) hung from z_top: the names' panels side by side, 350 mm tall, in a
    100 mm deep anthracite light box, read the same from both sides (back_names: different panels on the back, as
    for arrows), its bottom HEADROOM over floor_z at least. along: the faces look along n or e. Solid housing. """
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
    F.collide( model, -hw, hw, -d, d, bottom, bottom + height + 2 * border, "metal" )
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
    look both ways along n or e. Solid clock housing. """
    F = _along_frame( e, n, along )
    d = 2.36
    F.collide( model, -radius, radius, -d, d, z - radius, z + radius, "metal" )
    rod( model, F.p( 0.0, -d, z ), F.p( 0.0, d, z ), radius, DARK, 24 )
    for s in ( 1.0, -1.0 ):
        disc( model, "rw_clock", F.p( 0.0, s * d, z ), s * F.y, radius, sides=24, round_uv=True )
    top = z + radius
    z_top = top + 18.0 if z_top is None else z_top
    F.box( model, -1.6, 1.6, -1.6, 1.6, top - 0.6, top + 2.0, DARK, skip=( "bottom", ) )
    _rods( model, F, ( 0.0, ), top + 2.0, z_top )


def pendant_lamp( model, e, n, z_top, z, shade_r=11.0, rod_r=0.45 ):
    """ A hall pendant: an enamelled reflector shade shade_r across its mouth (560 mm by default; the booking hall's are
    800-900 mm), grey-green outside and white inside, on a rod_r tube from z_top with its ceiling rose, the opal globe in
    its mouth; z is the shade's rim. Returns the light's position, just under the rim. """
    k = shade_r / 11.0
    rod( model, ( e, n, z + 12.5 * k ), ( e, n, z_top - 0.4 ), rod_r, DARK, 6 if rod_r < 0.8 else 10 )
    rose = max( 2.4, rod_r * 3.0 )
    model.box( ( e - rose, n - rose, z_top - 0.4 ), ( e + rose, n + rose, z_top ), DARK, skip=( "+z", ) )
    rod( model, ( e, n, z + 10.5 * k ), ( e, n, z + 12.5 * k ), 1.4 * k, DARK, 8, caps=( False, True ) )
    _frustum( model, ( e, n, z + 10.5 * k ), ( e, n, z ), 2.2 * k, shade_r, "rw_steel", sides=16 if k > 1.2 else 12,
              inside="rw_white_paint" )
    disc( model, "rw_steel", ( e, n, z + 10.5 * k ), ( 0, 0, 1 ), 2.2 * k, sides=12 )
    _frustum( model, ( e, n, z + 7.0 * k ), ( e, n, z + 1.5 * k ), 3.0 * k, 4.8 * k, "rw_lamp_warm", sides=12 )
    disc( model, "rw_lamp_warm", ( e, n, z + 1.5 * k ), ( 0, 0, -1 ), 4.8 * k, sides=12 )
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
    """The detailed reusable trolley; map placements share its standalone model."""
    import railhead_luggage
    railhead_luggage.emit( model, e, n, along, z0, loaded )


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
    ( 148.0, 35.2, 8.0, 30.0, 33.5, 40.8, 28.8, 55.0, 24.0, 57.0, 57.4 ),
    ( 162.0, 35.0, 8.2, 30.0, 33.3, 41.0, 28.6, 54.8, 23.8, 56.8, 57.1 ),
    ( 171.0, 34.8, 8.5, 30.0, 33.0, 41.0, 28.3, 54.5, 23.6, 56.4, 56.8 ),
    ( 176.0, 34.5, 9.0, 30.0, 32.7, 40.8, 28.8, 50.8, 23.6, 52.2, 52.5 ),
    ( 180.0, 33.8, 9.5, 29.5, 32.1, 40.3, 30.0, 41.5, 23.4, 42.0, 42.2 ),
    ( 182.4, 32.0, 10.0, 27.0, 31.0, 38.8, 29.6, 39.4, 22.8, 39.8, 40.0 ),
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


def _road_vehicle( model, F, keys, axles, tyre, arch, paint_at, splits=(), detailed_wheels=False ):
    """ A car or van body lofted through keys in F (front at y 0, a behind it at y = -a), wheel arches cut round the
    axles (depths) for tyres of radius tyre[0] and width tyre[1] on rims of tyre[2], arches of radius arch.
    paint_at( segment, a0, a1 ) paints each strip (segments 1-4 from the shoulder up; 0 is the lower side). """
    stations = sorted( { k[0] for k in keys } | set( splits ) )
    profiles = { a: _profile_at( keys, a ) for a in stations }
    def body_normal( a, j, xs ):
        profile = _profile_at( keys, a )
        ja, jb = max(1, j - 1), min(5, j + 1)
        across = np.subtract(profile[jb], profile[ja])
        before = _profile_at(keys, max(keys[0][0], a - 0.5))[j]
        after = _profile_at(keys, min(keys[-1][0], a + 0.5))[j]
        lengthwise = np.array((xs * (after[0] - before[0]), -1.0, after[1] - before[1]))
        normal = np.cross(lengthwise, (xs * across[0], 0.0, across[1])) * -xs
        return _unit(normal)
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
                    normals = [ body_normal(a0, k, xs), body_normal(a0, k + 1, xs),
                                body_normal(a1, k + 1, xs), body_normal(a1, k, xs) ] if len(pts) == 4 else None
                    _fpoly( model, F, paint, pts, ( xs * nx, 0, nz ), normals=normals )
    radius, width, rim = tyre
    zc, steps = radius, 16 if detailed_wheels else 8
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
            if detailed_wheels:
                _suv_wheel( model, F, ac, xs )
            else:
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


def car( model, e, n, along="+n", paint="rw_train_grey", z0=0.0, kind="hatch", taxi=False, plate=None ):
    """ A parked generic modern compact car, kind "hatch" (4.28 m) or "estate" (4.63 m), 1.79 m wide and 1.46 m tall on
    205/55 R16 tyres, its nose towards along ("+n", "-n", "+e", "-e") and (e, n) its footprint's centre. Body paint
    (the rw_train_* or rw_car_* colours), real tinted glazing set 12 mm into the body with rubber surrounds and
    body-colour pillars, an interior behind it, flush door grips, stalk mirrors, flared arches, clear-lensed light
    units, a mesh lower grille and made-up number plates (plate, or one hashed from where it stands). One metal box. """
    import railhead_vehicle_kit as VK
    keys = ESTATE if kind == "estate" else HATCH
    # Smooth automotive paint instead of the train's streaked panel texture.
    if paint == "rw_train_white":
        paint = "rw_car_white"
    plate = plate or VK.plate_for( e, n )
    L = keys[-1][0]
    F = _vehicle_frame( e, n, along, L, z0 )
    profile_at = lambda a: _profile_at( keys, a )
    rear_axle = 34.6 + ( 105.7 if kind == "estate" else 103.8 )
    # ( first segment, last segment, a0, a1 ) of each pane: the windscreen, the side glass, the rear glass.
    panes = [ ( 4, 4, 46.0, 72.0 ), ( 2, 2, 46.0, 92.0 ) ]
    if kind == "estate":
        panes += [ ( 2, 2, 97.0, 128.0 ), ( 2, 2, 134.0, 165.0 ), ( 3, 4, 172.0, 178.5 ) ]
    else:
        panes += [ ( 2, 2, 97.0, 134.0 ), ( 4, 4, 150.0, 162.0 ) ]

    def paint_at( k, a0, a1 ):
        mid = ( a0 + a1 ) / 2
        if any( k0 <= k <= k1 and g0 <= mid <= g1 for k0, k1, g0, g1 in panes ):
            return None
        return paint

    splits = [ 92.0, 97.0 ] + ( [ 128.0, 132.0, 134.0, 165.0, 172.0, 178.5 ] if kind == "estate" else [ 134.0 ] )
    _road_vehicle( model, F, keys, ( 34.6, rear_axle ), ( SUV_TYRE, SUV_TYRE_W, SUV_RIM ), 15.6,
                   paint_at, splits, detailed_wheels=True )
    stations = [ k[0] for k in keys ]
    for k0, k1, g0, g1 in panes:
        VK.window( model, F, profile_at, k0, k1, g0, g1, stations=stations )
    VK.car_interior( model, F, 47.0, 72.0, L - 6.0, 54.0, 39.0, 33.6, driver=1.0,
                     boot=( 132.0, 22.0 ) if kind == "estate" else ( 140.0, 24.0 ) )
    # Panel gaps: the doors' cuts, the bonnet's shut lines (across at the cowl and along each wing), the tailgate's.
    for xs in ( -1, 1 ):
        for a in ( 48.0, 95.0, 132.0 ):
            _seam( model, F, keys, a, xs, 13.0, 40.0, width=0.16, lift=0.06 )
        for a0_, a1_ in ( ( 3.0, 12.0 ), ( 12.0, 30.0 ), ( 30.0, 45.0 ) ):
            p0, p1 = profile_at( a0_ )[3], profile_at( a1_ )[3]
            _fpoly( model, F, "rw_black", [ ( xs * ( p0[0] - 0.4 ), -a0_, p0[1] + 0.07 ), ( xs * ( p1[0] - 0.4 ), -a1_, p1[1] + 0.07 ),
                                            ( xs * ( p1[0] - 0.56 ), -a1_, p1[1] + 0.09 ), ( xs * ( p0[0] - 0.56 ), -a0_, p0[1] + 0.09 ) ],
                    ( 0, 0, 1 ) )
        # Flush pull grips, the stalk mirrors, the sill's black step trim.
        for a in ( 84.0, 122.0 ):
            VK.door_grip( model, F, profile_at, a, 36.4, paint )
        VK.stalk_mirror( model, F, xs, 52.0, 41.6, paint, base_x=VK.skin_x( profile_at, 52.0, 39.0 ) - 0.2 )
        F.box( model, min( xs * 34.8, xs * 35.4 ), max( xs * 34.8, xs * 35.4 ), -rear_axle + 15.8, -50.4,
               9.8, 11.4, "rw_black" )
    prof = profile_at( 45.0 )
    _fpoly( model, F, "rw_black", [ ( -prof[4][0] + 1, -45.0, prof[4][1] + 0.1 ), ( prof[4][0] - 1, -45.0, prof[4][1] + 0.1 ),
                                    ( prof[4][0] - 1, -45.4, prof[4][1] + 0.12 ), ( -prof[4][0] + 1, -45.4, prof[4][1] + 0.12 ) ],
            ( 0, 0, 1 ) )
    for ac in ( 34.6, rear_axle ):
        VK.arch_lip( model, F, profile_at, ac, SUV_TYRE, 15.6, paint )
    # A satin chrome strip along the belt, under the side glass.
    belt = [ a for a in sorted( set( stations + [ 50.0, 92.0, 97.0, 128.0, 134.0, 165.0 ] ) ) if 50.0 <= a <= L - 17.0 ]
    for xs in ( -1, 1 ):
        pts = [ F.p( xs * ( profile_at( a )[2][0] + 0.12 ), -a, profile_at( a )[2][1] - 0.3 ) for a in belt ]
        polyline( model, pts, 0.16, "rw_car_chrome", 4 )
    # The nose: clear-lensed light units, the upper grille with its bars, the mesh lower grille.
    for xs in ( -1, 1 ):
        VK.head_cluster( model, F, xs, 16.5, 28.6, 26.0, 29.8, 0.0 )
    F.quad( model, "rw_black", 0.0, 0.04, 23.2, 26.0, 4.0 )
    for z in ( 21.8, 23.2, 24.6 ):
        rod( model, F.p( -13.0, 0.3, z ), F.p( 13.0, 0.3, z ), 0.22, "rw_car_trim", 4 )
    VK.mesh_grille( model, F, -15.0, 15.0, 10.0, 15.2, 0.75, frame="rw_car_trim" )
    _plate( model, F, ( 0.0, 0.85, 17.4 ), ( 1, 0, 0 ), ( 0, 0, 1 ), ( 0, 1, 0 ), plate )
    _plate( model, F, ( 0.0, -L - 0.12, 20.0 ), ( -1, 0, 0 ), ( 0, 0, 1 ), ( 0, -1, 0 ), plate )
    F.quad( model, "rw_black", 0.0, -L - 0.04, 11.8, 40.0, 2.6, "back" )
    # The tail: sealed lamp assemblies with bevelled covers, the tailgate's gaps round them.
    zt = 40.0 if kind == "estate" else 37.0

    def rear_panel( material, x0, x1, z0_, z1_, lift=0.15 ):
        _fpoly( model, F, material, [ ( x0, -L - lift, z0_ ), ( x1, -L - lift, z0_ ), ( x1, -L - lift, z1_ ),
                                      ( x0, -L - lift, z1_ ) ], ( 0, -1, 0.2 ) )

    def cover( material, xa, xb, za, zb, depth, bevel ):
        back = [ ( xa, -L - 0.12, za ), ( xb, -L - 0.12, za ), ( xb, -L - 0.12, zb ), ( xa, -L - 0.12, zb ) ]
        face = [ ( xa + bevel, -L - depth, za + bevel ), ( xb - bevel, -L - depth, za + bevel ),
                 ( xb - bevel, -L - depth, zb - bevel ), ( xa + bevel, -L - depth, zb - bevel ) ]
        _fpoly( model, F, material, face, ( 0, -1, 0 ) )
        for k in range( 4 ):
            j = ( k + 1 ) % 4
            _fpoly( model, F, material, [ back[k], back[j], face[j], face[k] ],
                    ( ( -1, 0, 0 ), ( 0, 0, 1 ), ( 1, 0, 0 ), ( 0, 0, -1 ) )[k] )

    wl = 26.0 if kind == "estate" else 23.5
    for xs in ( -1, 1 ):
        x0, x1 = sorted( ( xs * wl, xs * ( wl + 5.8 ) ) )
        cover( "rw_rubber", x0, x1, zt - 13.0, zt, 0.55, 0.28 )
        cover( "rw_estate_lens_red", x0 + 0.22, x1 - 0.22, zt - 12.7, zt - 0.3, 0.95, 0.35 )
        rear_panel( "rw_estate_lens_dark", x0 + 1.05, x1 - 1.05, zt - 10.7, zt - 2.2, 1.0 )
        for z in ( 30.0, 31.1, 32.2, 34.8, 35.9, 37.0 ):
            rear_panel( "rw_estate_lens_red", x0 + 1.12, x1 - 1.12, z - 40.0 + zt, z - 40.0 + zt + 0.18, 1.05 )
        cover( "rw_estate_lens_red", x0 + 0.8, x1 - 0.8, zt - 7.0, zt - 5.8, 1.12, 0.12 )
        cover( "rw_estate_lens_clear", x0 + 0.8, x1 - 0.8, zt - 11.9, zt - 11.0, 1.13, 0.10 )
        if kind == "estate":
            _seam( model, F, keys, 170.5, xs, 12.0, 42.0, width=0.18 )
        # the tailgate's side gaps, inboard of the lamps
        xg = xs * ( wl - 0.6 )
        rear_panel( "rw_black", min( xg, xg + xs * 0.18 ), max( xg, xg + xs * 0.18 ), 22.5, zt + 1.0, 0.04 )
    rear_panel( "rw_black", -wl + 0.4, wl - 0.4, 22.4, 22.6, 0.04 )
    rear_panel( "rw_black", -9.0, 9.0, 28.0, 32.0, 0.35 )
    rear_panel( "rw_steel_grey", -1.4, 1.4, 34.0, 35.8, 0.35 )
    if kind == "estate":
        # Wiper, roof spoiler and high brake light.
        rod( model, F.p( 0, -179.0, 45.0 ), F.p( 12, -179.0, 45.5 ), 0.28, "rw_black", 6 )
        F.box( model, -27.0, 27.0, -173.5, -169.0, 55.8, 57.2, paint )
        F.quad( model, "rw_red_paint", 0, -173.6, 56.0, 13.0, 0.6, "back" )
    rear_panel( "rw_black", -25.0, 25.0, 11.0, 15.0, 0.30 )
    if taxi:
        # The roof sign: a yellow light box 400 x 120 mm on the roof's middle, "TAXI" on both faces, on its
        # magnetic feet.
        try:
            import railhead_furniture as FU
            FU.taxi_sign( model, F, -L * 0.55, max( k[-1] for k in keys ) )
        except Exception as error:
            print( f"railhead_furniture.taxi_sign failed: {error}" )
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
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.", "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....", "G": ".###.|#...#|#....|#.###|#...#|#...#|.####",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..", "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#", "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..", "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.", "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "5": "#####|#....|####.|....#|....#|#...#|.###.", "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...", "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
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
    """ A wheel at depth ac on side xs: a tyre with rounded shoulders, its matte sidewall carrying a ring of raised
    lettering and brown road dust over its lowest third, on a satin ten-spoke alloy (five twin spokes) with a
    chamfered lip, a centre cap and five lug recesses; the ventilated brake disc and its caliper show between the
    spokes. """
    import railhead_vehicle_kit as VK
    r, w, rim = SUV_TYRE, SUV_TYRE_W, SUV_RIM
    xo, xi = SUV_TRACK + w / 2, SUV_TRACK - w / 2

    def p( x, rad, t ):         # x across, at radius rad and angle t round the hub, in the frame's own coordinates
        return ( xs * x, -( ac + rad * math.cos( t ) ), r + rad * math.sin( t ) )

    rod( model, F.p( xs * ( xi + 0.9 ), -ac, r ), F.p( xs * ( xo - 0.9 ), -ac, r ), r, "rw_tyre", 28 )
    for x0, x1, r1 in ( ( xo - 0.9, xo, r - 1.1 ), ( xi + 0.9, xi, r - 1.1 ) ):
        _frustum( model, F.p( xs * x0, -ac, r ), F.p( xs * x1, -ac, r ), r, r1, "rw_tyre", 28 )
    # The tread's four circumferential grooves.
    for f in ( 0.22, 0.42, 0.58, 0.78 ):
        x = xi + 0.9 + ( w - 1.8 ) * f
        rod( model, F.p( xs * ( x - 0.12 ), -ac, r ), F.p( xs * ( x + 0.12 ), -ac, r ), r + 0.015, "rw_black", 28 )
    VK.tyre_sidewall( model, F, ac, xs, xo, rim + 0.6, r - 1.1, r, outward=1.0 )
    n = 28
    for k in range( n ):            # the rim's chamfered lip and the inner sidewall
        t0, t1 = 2 * math.pi * k / n, 2 * math.pi * ( k + 1 ) / n
        _fpoly( model, F, "rw_wheel_alloy", [ p( xo + 0.02, rim - 0.05, t0 ), p( xo - 0.25, rim + 0.6, t0 ),
                                              p( xo - 0.25, rim + 0.6, t1 ), p( xo + 0.02, rim - 0.05, t1 ) ],
                ( xs, 0, 0 ) )
        _fpoly( model, F, "rw_tyre", [ p( xi, 0.0, t0 ), p( xi, r - 1.1, t0 ), p( xi, r - 1.1, t1 ), p( xi, 0.0, t1 ) ],
                ( -xs, 0, 0 ) )
    disc( model, "rw_black", F.p( xs * ( xo - 3.2 ), -ac, r ), ( xs * F.x ), rim, sides=24 )
    disc( model, "rw_brake_disc", F.p( xs * ( xo - 2.9 ), -ac, r ), ( xs * F.x ), 6.9, sides=24 )
    VK.ring( model, "rw_steel_dark", F.p( xs * ( xo - 2.87 ), -ac, r ), xs * F.x, 3.2, 4.0, sides=16 )
    disc( model, "rw_bogie", F.p( xs * ( xo - 2.85 ), -ac, r ), ( xs * F.x ), 3.2, sides=12 )
    # The caliper, a cast block over the disc's rear top quarter.
    ta, tb = math.radians( 110 ), math.radians( 150 )
    for x0, x1 in ( ( xo - 3.05, xo - 1.75 ), ):
        pts_o = [ p( x1, 5.2, ta ), p( x1, 7.6, ta ), p( x1, 7.6, tb ), p( x1, 5.2, tb ) ]
        _fpoly( model, F, "rw_caliper", pts_o, ( xs, 0, 0 ) )
        for ( ra, tA ), ( rb, tB ) in ( ( ( 7.6, ta ), ( 7.6, tb ) ), ( ( 5.2, ta ), ( 7.6, ta ) ), ( ( 5.2, tb ), ( 7.6, tb ) ) ):
            _fpoly( model, F, "rw_caliper", [ p( x0, ra, tA ), p( x1, ra, tA ), p( x1, rb, tB ), p( x0, rb, tB ) ],
                    ( 0, -math.cos( ( tA + tB ) / 2 ), math.sin( ( tA + tB ) / 2 ) ) )
    for pair in range( 5 ):         # five pairs of spokes, from the hub out to the lip, the hub sunk 0.9
        for side in ( -1, 1 ):
            t = 2 * math.pi * pair / 5 + side * math.radians( 9.0 )
            rh, rl = 2.9, rim - 0.1
            dh, dl = math.radians( 8.0 ), math.radians( 3.4 )
            face = [ p( xo - 0.9, rh, t - dh ), p( xo - 0.15, rl, t - dl ), p( xo - 0.15, rl, t + dl ),
                     p( xo - 0.9, rh, t + dh ) ]
            _fpoly( model, F, "rw_wheel_alloy", face, ( xs, 0, 0 ) )
            for e0, e1 in ( ( 0, 1 ), ( 3, 2 ) ):       # the spokes' sides, back to the barrel
                a_, b_ = face[e0], face[e1]
                c_ = ( a_[0] - xs * 1.4, a_[1], a_[2] )
                d_ = ( b_[0] - xs * 1.4, b_[1], b_[2] )
                _fpoly( model, F, "rw_wheel_alloy_dark", [ a_, b_, d_, c_ ], ( 0, ( a_[1] + b_[1] ) / 2 + ac,
                                                                                 ( a_[2] + b_[2] ) / 2 - r ) )
    disc( model, "rw_wheel_alloy", F.p( xs * ( xo - 0.88 ), -ac, r ), ( xs * F.x ), 3.0, sides=16 )
    disc( model, "rw_car_trim", F.p( xs * ( xo - 0.78 ), -ac, r ), ( xs * F.x ), 1.25, sides=16 )
    for k in range( 5 ):
        t = 2 * math.pi * ( k + 0.5 ) / 5
        disc( model, "rw_black", F.p( *p( xo - 0.84, 2.1, t ) ), ( xs * F.x ), 0.42, sides=8 )
        disc( model, "rw_steel_grey", F.p( *p( xo - 0.9, 2.1, t ) ), ( xs * F.x ), 0.3, sides=6 )


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


def suv( model, e, n, along="+n", paint="rw_car_silver", z0=0.0, plate=None ):
    """ A parked compact crossover SUV (SUV_*), its nose towards along ("+n", "-n", "+e", "-e"), (e, n) its footprint's
    centre. Body paint (the rw_car_* paints), black cladding round the sills and arches, tinted glass in black frames,
    a black honeycomb grille, a slim LED light bar across the nose, boomerang air intakes at its corners lit along
    their edges, wrap-round tail lights joined by a light bar, roof rails, a roof spoiler, dark ten-spoke alloys and
    the town's number plates. Two metal boxes: the body to the belt and the cabin. """
    import railhead_vehicle_kit as VK
    plate = plate or VK.plate_for( e, n )
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
                    return "rw_car_glass", "glass"
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
            return "rw_car_glass", "glass"
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
    # The cabin behind the glass, and the satin chrome round the side glass's daylight opening and along its foot.
    VK.car_interior( model, F, SUV_COWL + 1.0, SUV_ROOF0, L - 10.0, 58.5, 42.0, 33.6, floor_z=15.0, driver=1.0,
                     boot=( 140.0, 26.0 ) )
    dlo = [ a for a in np.linspace( SUV_WINDOWS[0][0] - 0.6, SUV_WINDOWS[-1][1] + 0.6, 30 ) ]
    for xs in ( 1.0, -1.0 ):
        foot = [ F.p( xs * ( _suv_profile( a )[4][0] + 0.14 ), -a, _suv_profile( a )[4][1] - 0.25 ) for a in dlo ]
        head = [ F.p( xs * ( _suv_profile( a )[5][0] + 0.1 ), -a, _suv_profile( a )[5][1] + 0.2 ) for a in dlo ]
        polyline( model, foot, 0.24, "rw_car_chrome", 4 )
        polyline( model, head, 0.2, "rw_car_chrome", 4 )
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
            rod( model, F.p( xs * xr, -a0, z0_ ), F.p( xs * xr, -a1, z1_ ), 0.6, "rw_alu_brushed", 8 )
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

    import railhead_vehicle_kit as VK
    rod( model, F.p( xs * ( xi + 0.9 ), -ac, r ), F.p( xs * ( xo - 0.9 ), -ac, r ), r, "rw_tyre", 28 )
    for x0, x1 in ( ( xo - 0.9, xo ), ( xi + 0.9, xi ) ):
        _frustum( model, F.p( xs * x0, -ac, r ), F.p( xs * x1, -ac, r ), r, r - 1.2, "rw_tyre", 28 )
    VK.tyre_sidewall( model, F, ac, xs, xo + 0.01, rim + 0.5, r - 1.2, r, outward=1.0 )
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


def van( model, e, n, along="+n", paint="rw_car_white", z0=0.0, plate=None ):
    """ A parked large panel van (VAN_*), its nose towards along ("+n", "-n", "+e", "-e"), (e, n) its footprint's
    centre: body paint (the rw_car_* paints), a black bumper and sill band with a silver sill strip, black arch trims,
    the grille's four bars in a dark frame, slim headlights with their running-light strips, fog lamps, black mirrors
    with indicators, a cab door, a sliding door with its rail, glazed rear doors, vertical tail lights, steel wheels and
    the town's number plates. Two metal boxes: the body to the bonnet, and the box behind the windscreen. """
    import railhead_vehicle_kit as VK
    plate = plate or VK.plate_for( e, n )
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
                    return "rw_car_glass", "glass"
                if VAN_WINDOWS[0][0] - 1.0 < mid < VAN_WINDOWS[1][1] + 1.2:
                    return "rw_black", "frame"
            return paint, "body"
        if VAN_COWL < mid < VAN_COWL + 1.6 and k >= 5:
            return "rw_black", "frame"                  # the scuttle under the windscreen
        if VAN_COWL + 1.6 <= mid < VAN_ROOF0 - 0.6:
            if k >= 6:
                return "rw_car_glass", "glass"
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
    # The cab behind the glass: dash, wheel, two seats, the bulkhead behind them.
    VK.cab_interior( model, F, VAN_COWL + 1.5, 103.0, 22.0, 54.0, 90.0, 38.4, driver=1.0 )
    for xs in ( 1.0, -1.0 ):
        # Two swage lines 15 mm deep along the load space: a shadowed step under a raised band.
        for z in ( 28.0, 48.0 ):
            for a0, a1 in ( ( 106.8, 157.2 ), ( 158.4, 229.0 ) ):
                side_patch( paint, xs, [ ( a0, z ), ( a1, z ), ( a1, z + 1.1 ), ( a0, z + 1.1 ) ], 0.6 )
                side_patch( "rw_black", xs, [ ( a0, z - 0.25 ), ( a1, z - 0.25 ), ( a1, z ), ( a0, z ) ], 0.08 )
                for a in ( a0, a1 ):
                    _fpoly( model, F, paint, [ loc( xs * ( _van_side_x( a, z ) + 0.06 ), a, z ),
                                               loc( xs * ( _van_side_x( a, z ) + 0.6 ), a, z ),
                                               loc( xs * ( _van_side_x( a, z ) + 0.6 ), a, z + 1.1 ),
                                               loc( xs * ( _van_side_x( a, z ) + 0.06 ), a, z + 1.1 ) ],
                            ( 0, 1 if a == a0 else -1, 0 ) )
                _fpoly( model, F, paint, [ loc( xs * ( _van_side_x( a0, z + 1.1 ) + 0.06 ), a0, z + 1.1 ),
                                           loc( xs * ( _van_side_x( a1, z + 1.1 ) + 0.06 ), a1, z + 1.1 ),
                                           loc( xs * ( _van_side_x( a1, z + 1.1 ) + 0.6 ), a1, z + 1.1 ),
                                           loc( xs * ( _van_side_x( a0, z + 1.1 ) + 0.6 ), a0, z + 1.1 ) ], ( 0, 0, 1 ) )
        # The sliding door's track: a recessed channel along the rail's line, its shadow under it.
        side_patch( "rw_steel_dark", xs, [ ( 158.6, 62.0 ), ( 226.0, 62.0 ), ( 226.0, 62.5 ), ( 158.6, 62.5 ) ], 0.12 )
        # Black mud flaps behind the rear wheels.
        xf0, xf1 = sorted( ( xs * ( VAN_TRACK - VAN_TYRE_W / 2 ), xs * ( VAN_TRACK + VAN_TYRE_W / 2 + 0.4 ) ) )
        ar = VAN_AXLES[1] + VAN_ARCH + 0.6
        F.box( model, xf0, xf1, -ar - 0.25, -ar, 3.0, 15.0, "rw_rubber" )
    # Roof ribs: 40 mm pressed beads across the load space's roof.
    for a in np.arange( 112.0, 226.0, 14.0 ):
        pts = [ F.p( x, -a, _van_top_z( a, x ) + 0.18 ) for x in np.linspace( -30.0, 30.0, 9 ) ]
        polyline( model, pts, 0.55, paint, 6 )
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
        F.box( model, xs * ( xm + 2.8 ), xs * ( xm + 8.8 ), -71.6, -71.75, 60.4, 69.6, "rw_steel_grey" )
        F.box( model, xs * ( xm + 2.8 ), xs * ( xm + 8.8 ), -71.6, -71.75, 56.4, 59.9, "rw_window_dark" )
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


def bollard( model, e, n, z0=0.0, kind="steel", illuminated=False ):
    """ A bollard: "steel" (102 mm tube, 1 m tall, anthracite with a white reflective band and a domed cap) or
    "concrete" (400 mm round, 700 mm tall, chamfered). Collision to its top. """
    if kind == "concrete":
        model.cylinder( ( e, n ), 7.87, z0, z0 + 25.6, { "side": "rw_concrete" }, sides=12 )
        _frustum( model, ( e, n, z0 + 25.6 ), ( e, n, z0 + 27.56 ), 7.87, 5.9, "rw_concrete", sides=12 )
        disc( model, "rw_concrete", ( e, n, z0 + 27.56 ), ( 0, 0, 1 ), 5.9, sides=12 )
        model.collision_box( ( e - 7.87, n - 7.87, z0 ), ( e + 7.87, n + 7.87, z0 + 27.56 ), "default" )
        return
    # Smooth-shaded continuous tube, with the reflective band at the same height.
    # A shallow rounded shoulder and a solid top close the hollow-looking end.
    sides = 32
    for za, zb, paint in ( ( -0.7, 31.5, DARK ), ( 31.5, 34.5, "lt_bollard_diffuser" if illuminated else "rw_white_paint" ), ( 34.5, 38.2, DARK ) ):
        rod( model, ( e, n, z0 + za ), ( e, n, z0 + zb ), 2.0, paint, sides=sides )
    for za, zb, ra, rb in ( ( 38.2, 38.65, 2.0, 1.88 ), ( 38.65, 39.0, 1.88, 1.58 ),
                            ( 39.0, 39.28, 1.58, 1.12 ), ( 39.28, 39.4, 1.12, 0.58 ) ):
        _frustum( model, ( e, n, z0 + za ), ( e, n, z0 + zb ), ra, rb, DARK, sides=sides )
    disc( model, DARK, ( e, n, z0 + 39.4 ), ( 0, 0, 1 ), 0.58, sides=sides )
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

    m = prop( "emu (2 cars, doors closed)" )
    emu( m, B, 200.0, +1, rz, platform_side=+1, doors_open=False, wire_z=wire_z )
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
    m = prop( "covered wagon (doors closed)" )
    covered_wagon( m, S, n - 1.0, +1, rz, doors_open=False )

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
