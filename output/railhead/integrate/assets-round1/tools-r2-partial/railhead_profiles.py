"""
Railhead's shape helpers for architectural detail: turned (lathe) solids, profiled mouldings swept along straight runs,
plan polylines and arcs, bolts, chamfered blocks and curved brackets. Everything here is drawn only: no collision.

Plan inches (e east, n north, z up), as map_kit. A moulding's profile is a list of ( u, v ) points: u how far it stands
proud of the face it runs along, v up (or out from an arch's centre). It's walked from the face at the bottom, out, up
and back to the face at the top, so the material is on the walker's left; the v's must not fall along the walk (the end
caps are cut in slices against the face). A lathe profile is ( r, z ) from the bottom up, the axis on the walker's left.
UVs are explicit and continuous: along the run and round the profile, in tiles of `tile` inches.
"""
import math

import numpy as np

import map_kit as K


def _unit( v ):
    v = np.asarray( v, float )
    n = np.linalg.norm( v )
    return v / n if n > 1e-12 else v


def _poly( model, paint, pts, towards, uv=None, normals=None ):
    """ A polygon wound to face towards; uv and normals follow its points. """
    pts = [ np.asarray( p, float ) for p in pts ]
    # Drop repeated points (a slice that ends on the face).
    keep = [ 0 ]
    for k in range( 1, len( pts ) ):
        if np.linalg.norm( pts[k] - pts[keep[-1]] ) > 1e-6:
            keep.append( k )
    if len( keep ) > 1 and np.linalg.norm( pts[keep[-1]] - pts[keep[0]] ) < 1e-6:
        keep.pop()
    if len( keep ) < 3:
        return
    pts = [ pts[k] for k in keep ]
    uv = [ uv[k] for k in keep ] if uv is not None else None
    normals = [ normals[k] for k in keep ] if normals is not None else None
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
        if uv is not None:
            uv = uv[:1] + uv[:0:-1]
        if normals is not None:
            normals = normals[:1] + normals[:0:-1]
    model.polygon( paint, pts, uv=uv, normals=normals )


# ---------------------------------------------------------------------------------------------------------------------
# Turned solids

def lathe( model, centre, profile, paint, sides=24, smooth=50.0, caps=( True, True ), tile=96.0, turn=0.0 ):
    """ A solid of revolution about the upright axis through centre ( e, n ): profile [ ( r, z ) ] from the bottom up.
    Neighbouring profile edges closer than smooth degrees are shaded as one curve. caps: discs at the bottom and the
    top where their radius isn't 0. """
    ce, cn = float( centre[0] ), float( centre[1] )
    prof = [ ( float( r ), float( z ) ) for r, z in profile ]
    edges = list( zip( prof, prof[1:] ) )
    # Each edge's outward normal in ( r, z ).
    en = []
    for ( r0, z0 ), ( r1, z1 ) in edges:
        dr, dz = r1 - r0, z1 - z0
        length = math.hypot( dr, dz )
        en.append( ( dz / length, -dr / length ) if length > 1e-9 else ( 1.0, 0.0 ) )
    cos_s = math.cos( math.radians( smooth ) )

    def vertex_normal( j, at_start ):
        own = en[j]
        other = j - 1 if at_start else j + 1
        if 0 <= other < len( en ):
            o = en[other]
            if own[0] * o[0] + own[1] * o[1] > cos_s:
                return _unit( ( own[0] + o[0], own[1] + o[1] ) )
        return own

    angles = [ turn + 2 * math.pi * k / sides for k in range( sides + 1 ) ]
    dirs = [ np.array( ( math.cos( a ), math.sin( a ), 0.0 ) ) for a in angles ]
    for j, ( ( r0, z0 ), ( r1, z1 ) ) in enumerate( edges ):
        if abs( r1 - r0 ) < 1e-9 and abs( z1 - z0 ) < 1e-9:
            continue
        n0, n1 = vertex_normal( j, True ), vertex_normal( j, False )
        for k in range( sides ):
            a, b = dirs[k], dirs[k + 1]
            p = [ np.array( ( ce, cn, z0 ) ) + a * r0, np.array( ( ce, cn, z0 ) ) + b * r0,
                  np.array( ( ce, cn, z1 ) ) + b * r1, np.array( ( ce, cn, z1 ) ) + a * r1 ]
            nn = [ a * n0[0] + np.array( ( 0, 0, n0[1] ) ), b * n0[0] + np.array( ( 0, 0, n0[1] ) ),
                   b * n1[0] + np.array( ( 0, 0, n1[1] ) ), a * n1[0] + np.array( ( 0, 0, n1[1] ) ) ]
            mid_n = ( a + b ) / 2 * ( en[j][0] ) + np.array( ( 0, 0, en[j][1] ) )
            ru = max( r0, r1, 1.0 )
            uv = [ ( angles[k] * ru / tile, z0 / tile ), ( angles[k + 1] * ru / tile, z0 / tile ),
                   ( angles[k + 1] * ru / tile, z1 / tile ), ( angles[k] * ru / tile, z1 / tile ) ]
            _poly( model, paint, p, mid_n, uv=uv, normals=nn )
    for ( r, z ), on, down in ( ( prof[0], caps[0], True ), ( prof[-1], caps[1], False ) ):
        if on and r > 1e-6:
            pts = [ ( ce + r * d[0], cn + r * d[1], z ) for d in dirs[:-1] ]
            uv = [ ( ( p[0] - ce ) / tile, ( p[1] - cn ) / tile ) for p in pts ]
            _poly( model, paint, pts, ( 0, 0, -1 if down else 1 ), uv=uv )


def torus_profile( r_in, z0, z1, bulge, steps=6 ):
    """ ( r, z ) points of a half-round ring from ( r_in, z0 ) out round to ( r_in, z1 ), bulge out from r_in. """
    zc, half = ( z0 + z1 ) / 2, ( z1 - z0 ) / 2
    return [ ( r_in + bulge * math.sin( math.pi * k / steps ), zc - half * math.cos( math.pi * k / steps ) )
             for k in range( steps + 1 ) ]


def ogee( r0, z0, r1, z1, steps=6 ):
    """ An S-curve from ( r0, z0 ) to ( r1, z1 ): a cyma, eased in and out. """
    return [ ( r0 + ( r1 - r0 ) * ( 0.5 - 0.5 * math.cos( math.pi * k / steps ) ), z0 + ( z1 - z0 ) * k / steps )
             for k in range( steps + 1 ) ]


def quarter( r0, z0, r1, z1, steps=4, convex=True ):
    """ A quarter curve from ( r0, z0 ) to ( r1, z1 ): convex bulges outwards (an echinus or ovolo), else hollow (a
    cavetto or scotia). """
    out = []
    for k in range( steps + 1 ):
        t = math.pi / 2 * k / steps
        if convex:
            out.append( ( r0 + ( r1 - r0 ) * math.sin( t ), z0 + ( z1 - z0 ) * ( 1 - math.cos( t ) ) ) )
        else:
            out.append( ( r0 + ( r1 - r0 ) * ( 1 - math.cos( t ) ), z0 + ( z1 - z0 ) * math.sin( t ) ) )
    return out


def join( *parts ):
    """ Profiles joined end to end, dropping the repeated point at each joint. """
    out = []
    for part in parts:
        for p in part:
            if not out or math.hypot( p[0] - out[-1][0], p[1] - out[-1][1] ) > 1e-6:
                out.append( ( float( p[0] ), float( p[1] ) ) )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Swept mouldings

def sweep( model, points, us, vs, profile, paint, caps=( True, True ), tile=96.0, smooth_path=False ):
    """ profile swept through points (3D), its u along us[i] and its v along vs[i] at each point (the frames, already
    scaled for mitres). """
    P = [ np.asarray( p, float ) for p in points ]
    U = [ np.asarray( u, float ) for u in us ]
    V = [ np.asarray( v, float ) for v in vs ]
    prof = [ ( float( u ), float( v ) ) for u, v in profile ]
    along = [ 0.0 ]
    for a, b in zip( P, P[1:] ):
        along.append( along[-1] + float( np.linalg.norm( b - a ) ) )
    round_ = [ 0.0 ]
    for ( u0, v0 ), ( u1, v1 ) in zip( prof, prof[1:] ):
        round_.append( round_[-1] + math.hypot( u1 - u0, v1 - v0 ) )

    def at( i, j ):
        return P[i] + U[i] * prof[j][0] + V[i] * prof[j][1]

    for j in range( len( prof ) - 1 ):
        ( u0, v0 ), ( u1, v1 ) = prof[j], prof[j + 1]
        du, dv = u1 - u0, v1 - v0
        if math.hypot( du, dv ) < 1e-9:
            continue
        for i in range( len( P ) - 1 ):
            uu, vv = _unit( U[i] + U[i + 1] ), _unit( V[i] + V[i + 1] )
            towards = uu * dv - vv * du
            pts = [ at( i, j ), at( i + 1, j ), at( i + 1, j + 1 ), at( i, j + 1 ) ]
            uv = [ ( along[i] / tile, round_[j] / tile ), ( along[i + 1] / tile, round_[j] / tile ),
                   ( along[i + 1] / tile, round_[j + 1] / tile ), ( along[i] / tile, round_[j + 1] / tile ) ]
            normals = None
            if smooth_path:
                normals = [ _unit( _unit( U[k] ) * dv - _unit( V[k] ) * du ) for k in ( i, i + 1, i + 1, i ) ]
            _poly( model, paint, pts, towards, uv=uv, normals=normals )
    # End caps, in slices against the face.
    for end, on in ( ( 0, caps[0] ), ( len( P ) - 1, caps[1] ) ):
        if not on:
            continue
        other = 1 if end == 0 else len( P ) - 2
        out_dir = _unit( P[end] - P[other] )
        for ( u0, v0 ), ( u1, v1 ) in zip( prof, prof[1:] ):
            if v1 - v0 < 1e-6 or ( u0 < 1e-6 and u1 < 1e-6 ):
                continue
            q = [ ( 0.0, v0 ), ( u0, v0 ), ( u1, v1 ), ( 0.0, v1 ) ]
            pts = [ P[end] + U[end] * a + V[end] * b for a, b in q ]
            uv = [ ( a / tile, b / tile ) for a, b in q ]
            _poly( model, paint, pts, out_dir, uv=uv )


def run( model, path, z, profile, paint, side=1.0, closed=False, caps=( True, True ), tile=96.0 ):
    """ A horizontal moulding along a plan polyline path [ ( e, n ) ] standing on z, proud of the face the path runs
    along: towards the path's right ( side 1 ) or left ( -1 ), mitred at the corners. """
    pts = [ np.array( ( float( e ), float( n ) ) ) for e, n in path ]
    if closed:
        pts = pts + [ pts[0] ]
    seg_dir = [ _unit( b - a ) for a, b in zip( pts, pts[1:] ) ]
    seg_out = [ np.array( ( d[1], -d[0] ) ) * side for d in seg_dir ]
    us = []
    for i in range( len( pts ) ):
        if closed and ( i == 0 or i == len( pts ) - 1 ):
            a, b = seg_out[-1], seg_out[0]
        elif i == 0:
            a = b = seg_out[0]
        elif i == len( pts ) - 1:
            a = b = seg_out[-1]
        else:
            a, b = seg_out[i - 1], seg_out[i]
        m = _unit( a + b )
        c = float( np.dot( m, a ) )
        us.append( np.array( ( *( m / max( c, 0.2 ) ), 0.0 ) ) )
    points = [ ( p[0], p[1], z ) for p in pts ]
    vs = [ ( 0.0, 0.0, 1.0 ) ] * len( pts )
    sweep( model, points, us, vs, profile, paint, caps=( False, False ) if closed else caps, tile=tile )


def straight( model, axis, at, r0, r1, z, out, profile, paint, caps=( True, True ), tile=96.0 ):
    """ A horizontal moulding on a wall face at plan coordinate at, running along axis ('e' or 'n') from r0 to r1,
    standing proud towards out (+1 or -1 across the axis). """
    if axis == "e":
        path = [ ( r0, at ), ( r1, at ) ]
        side = -out           # walking +e, the right is -n
    else:
        path = [ ( at, r0 ), ( at, r1 ) ]
        side = out            # walking +n, the right is +e
    if r1 < r0:
        path, side = path[::-1], side
    run( model, path, z, profile, paint, side=side, caps=caps, tile=tile )


def raked( model, axis, at, out, p0, p1, profile, paint, caps=( True, True ), tile=96.0 ):
    """ A moulding on a wall face (plan coordinate at, facing out across axis) along a sloping line from p0 to p1,
    each ( run, z ): a stair's string or a raked dado. Its v is up the face (vertical), not square to the slope. """
    def pt( r, z ):
        return ( r, at, z ) if axis == "e" else ( at, r, z )
    u = ( 0.0, out, 0.0 ) if axis == "e" else ( out, 0.0, 0.0 )
    sweep( model, [ pt( *p0 ), pt( *p1 ) ], [ u, u ], [ ( 0, 0, 1 ), ( 0, 0, 1 ) ], profile, paint, caps=caps, tile=tile )


def arch_band( model, axis, at, out, centre_r, spring, radius, profile, paint, steps=24, start=180.0, end=0.0,
               caps=( True, True ), tile=96.0 ):
    """ A moulding round an arch on a wall face (plan coordinate at, facing out across axis), the arch's centre
    ( centre_r, spring ) and intrados radius: profile ( u proud, v out from the intrados ). """
    def pt( r, z ):
        return np.array( ( r, at, z ) if axis == "e" else ( at, r, z ), float )
    u = np.array( ( 0.0, out, 0.0 ) if axis == "e" else ( out, 0.0, 0.0 ) )
    points, us, vs = [], [], []
    for k in range( steps + 1 ):
        t = math.radians( start + ( end - start ) * k / steps )
        c, s = math.cos( t ), math.sin( t )
        points.append( pt( centre_r + radius * c, spring + radius * s ) )
        us.append( u )
        vs.append( pt( c, s ) - pt( 0, 0 ) )
    sweep( model, points, us, vs, profile, paint, caps=caps, tile=tile, smooth_path=True )


def curve_band( model, points, ups, out, profile, paint, caps=( True, True ), tile=96.0 ):
    """ A moulding along any curve on a face: points (3D), ups the profile's v at each, out its u (the face's normal). """
    sweep( model, points, [ out ] * len( points ), ups, profile, paint, caps=caps, tile=tile, smooth_path=True )


# ---------------------------------------------------------------------------------------------------------------------
# Small parts

def bolt( model, p, direction, radius=0.45, length=0.35, paint="rw_steel_dark", sides=6, washer=True ):
    """ A hex bolt head (and a washer) on a face at p, standing out along direction. """
    p, d = np.asarray( p, float ), _unit( direction )
    side = _unit( np.cross( d, ( 0, 0, 1 ) ) if abs( d[2] ) < 0.9 else np.cross( d, ( 1, 0, 0 ) ) )
    up = np.cross( d, side )

    def ring( c, r, n ):
        return [ c + r * ( math.cos( 2 * math.pi * k / n ) * side + math.sin( 2 * math.pi * k / n ) * up ) for k in range( n ) ]

    base = p
    if washer:
        a, b = ring( p, radius * 1.45, 8 ), ring( p + d * 0.08, radius * 1.45, 8 )
        for k in range( 8 ):
            _poly( model, paint, [ a[k], a[( k + 1 ) % 8], b[( k + 1 ) % 8], b[k] ], ( a[k] + a[( k + 1 ) % 8] ) / 2 - p )
        _poly( model, paint, b, d )
        base = p + d * 0.08
    a, b = ring( base, radius, sides ), ring( base + d * length, radius, sides )
    for k in range( sides ):
        _poly( model, paint, [ a[k], a[( k + 1 ) % sides], b[( k + 1 ) % sides], b[k] ], ( a[k] + a[( k + 1 ) % sides] ) / 2 - base )
    _poly( model, paint, b, d )


def rivet( model, p, direction, radius=0.4, height=0.3, paint="rw_steel", sides=6 ):
    """ A snap-head rivet: a low dome (a cone and a cap) on a face. """
    p, d = np.asarray( p, float ), _unit( direction )
    side = _unit( np.cross( d, ( 0, 0, 1 ) ) if abs( d[2] ) < 0.9 else np.cross( d, ( 1, 0, 0 ) ) )
    up = np.cross( d, side )
    rim = [ p + radius * ( math.cos( 2 * math.pi * k / sides ) * side + math.sin( 2 * math.pi * k / sides ) * up ) for k in range( sides ) ]
    top = [ p + d * height * 0.75 + 0.55 * radius * ( math.cos( 2 * math.pi * k / sides ) * side + math.sin( 2 * math.pi * k / sides ) * up ) for k in range( sides ) ]
    for k in range( sides ):
        _poly( model, paint, [ rim[k], rim[( k + 1 ) % sides], top[( k + 1 ) % sides], top[k] ], ( rim[k] + rim[( k + 1 ) % sides] ) / 2 - p + d * 0.3 )
    _poly( model, paint, top, d )


def chamfer_box( model, lo, hi, paint, chamfer=1.0, skip=() ):
    """ A box whose upright edges and top edges are chamfered: an octagonal prism with a bevelled top. skip: '-z' to
    leave its bottom open. """
    lo, hi = np.minimum( lo, hi ).astype( float ), np.maximum( lo, hi ).astype( float )
    c = min( chamfer, ( hi[0] - lo[0] ) / 3, ( hi[1] - lo[1] ) / 3, ( hi[2] - lo[2] ) / 2 )
    e0, n0, z0 = lo
    e1, n1, z1 = hi

    def octagon( inset, z ):
        a = c + inset
        return [ ( e0 + a, n0 + inset, z ), ( e1 - a, n0 + inset, z ), ( e1 - inset, n0 + a, z ), ( e1 - inset, n1 - a, z ),
                 ( e1 - a, n1 - inset, z ), ( e0 + a, n1 - inset, z ), ( e0 + inset, n1 - a, z ), ( e0 + inset, n0 + a, z ) ]

    bottom, mid, top = octagon( 0.0, z0 ), octagon( 0.0, z1 - c ), octagon( c, z1 )
    centre = np.array( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) )
    for k in range( 8 ):
        a, b = k, ( k + 1 ) % 8
        q = [ bottom[a], bottom[b], mid[b], mid[a] ]
        _poly( model, paint, q, np.mean( q, axis=0 ) - centre * ( 1, 1, 0 ) - np.array( ( 0, 0, np.mean( q, axis=0 )[2] ) ) )
        q2 = [ mid[a], mid[b], top[b], top[a] ]
        m2 = np.mean( q2, axis=0 )
        _poly( model, paint, q2, ( m2[0] - centre[0], m2[1] - centre[1], c * 2 ) )
    _poly( model, paint, top, ( 0, 0, 1 ) )
    if "-z" not in skip:
        _poly( model, paint, bottom, ( 0, 0, -1 ) )


def plate( model, points, thick, normal, paint ):
    """ A flat plate: the outline ( convex points in a plane ) extruded thick along normal, both faces and edges. """
    n = _unit( normal )
    a = [ np.asarray( p, float ) for p in points ]
    b = [ p + n * thick for p in a ]
    _poly( model, paint, b, n )
    _poly( model, paint, a, -n )
    centre = np.mean( a, axis=0 )
    for k in range( len( a ) ):
        j = ( k + 1 ) % len( a )
        _poly( model, paint, [ a[k], a[j], b[j], b[k] ], ( a[k] + a[j] ) / 2 - centre )


def tube_path( model, points, radius, paint, sides=10, cap=True ):
    """ A round bar along a polyline, mitred at its bends, smooth-shaded. """
    P = [ np.asarray( p, float ) for p in points ]
    if len( P ) < 2:
        return
    tangents = []
    for i in range( len( P ) ):
        if i == 0:
            t = _unit( P[1] - P[0] )
        elif i == len( P ) - 1:
            t = _unit( P[-1] - P[-2] )
        else:
            t = _unit( _unit( P[i] - P[i - 1] ) + _unit( P[i + 1] - P[i] ) )
        tangents.append( t )
    ref = np.array( ( 0.0, 0.0, 1.0 ) ) if abs( tangents[0][2] ) < 0.9 else np.array( ( 1.0, 0.0, 0.0 ) )
    rings = []
    u = _unit( np.cross( tangents[0], ref ) )
    for i, t in enumerate( tangents ):
        # Parallel transport of the ring's frame.
        u = _unit( u - np.dot( u, t ) * t )
        v = np.cross( t, u )
        scale = 1.0
        if 0 < i < len( P ) - 1:
            seg = _unit( P[i] - P[i - 1] )
            scale = 1.0 / max( float( np.dot( seg, t ) ), 0.3 )
        dirs = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v for k in range( sides ) ]
        # Stretch the ring in the bend's plane so the mitre keeps the bar's width.
        ring = []
        for d in dirs:
            if scale != 1.0:
                seg = _unit( P[i] - P[i - 1] )
                bend = _unit( seg - np.dot( seg, t ) * t ) if np.linalg.norm( seg - np.dot( seg, t ) * t ) > 1e-9 else u
                along_bend = np.dot( d, bend )
                d = d + bend * along_bend * ( scale - 1.0 )
            ring.append( d )
        rings.append( ( ring, dirs ) )
    for i in range( len( P ) - 1 ):
        ( ra, da ), ( rb, db ) = rings[i], rings[i + 1]
        for k in range( sides ):
            j = ( k + 1 ) % sides
            pts = [ P[i] + ra[k] * radius, P[i] + ra[j] * radius, P[i + 1] + rb[j] * radius, P[i + 1] + rb[k] * radius ]
            _poly( model, paint, pts, ( da[k] + da[j] ) / 2, normals=[ da[k], da[j], db[j], db[k] ] )
    if cap:
        for i, sgn in ( ( 0, -1.0 ), ( len( P ) - 1, 1.0 ) ):
            ring = rings[i][0]
            _poly( model, paint, [ P[i] + d * radius for d in ring ], tangents[i] * sgn )
