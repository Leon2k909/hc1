"""
Railhead's small dressing details, for railhead_map's layout functions: the things a working Hauptbahnhof has on its
walls, floors and kerbs that the props module has no function for yet.

Everything here is visual only (no collision) unless a function says otherwise: City-Light poster cases on walls, a
wall bracket lamp, fire extinguishers, road gullies and manhole covers, a taxi rank post, the goods yard's concrete
apron, its cast-iron drain channel, painted bay lines and a hatched no-parking box, an open inspection chamber with
traffic cones round it, stacked tyres, a skip, cable drums and a strapped pallet of bricks (the last few with one
simple collision box each, as solid objects players can stand behind).

Plan coordinates as map_kit's: e east, n north, z up, inches. Facing is the way an object's front looks: "+e", "-e",
"+n" or "-n". Real sizes: a City-Light case is 1190 x 1750 mm, a road gully grate 300 x 500 mm, a manhole cover 600 mm,
a car tyre 650 mm across and 205 mm wide, a builder's skip 3.4 x 1.7 x 1.2 m, a cable drum 1.2 m across.
"""
import math

import numpy as np

METAL, STONE, WOOD = "metal", "default", "wood"

DIRS = { "+e": ( 1.0, 0.0, 0.0 ), "-e": ( -1.0, 0.0, 0.0 ), "+n": ( 0.0, 1.0, 0.0 ), "-n": ( 0.0, -1.0, 0.0 ) }


# ---------------------------------------------------------------------------------------------------------------------
# Shapes

def _unit( v ):
    v = np.asarray( v, float )
    length = np.linalg.norm( v )
    return v / length if length > 1e-12 else v


def _ring_axes( axis ):
    axis = _unit( axis )
    helper = np.array( ( 0.0, 0.0, 1.0 ) ) if abs( axis[2] ) < 0.9 else np.array( ( 1.0, 0.0, 0.0 ) )
    u = _unit( np.cross( axis, helper ) )
    return u, np.cross( axis, u )


def _face( model, paint, points, towards, normals=None, uv=None ):
    """ A polygon whose winding is turned so its normal looks towards towards. """
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.dot( normal, towards ) < 0:
        pts = pts[::-1]
        normals = normals[::-1] if normals is not None else None
        uv = uv[::-1] if uv is not None else None
    model.polygon( paint, pts, normals=normals, uv=uv )


def rod( model, a, b, r, paint, sides=8, caps=( False, False ) ):
    a, b = np.asarray( a, float ), np.asarray( b, float )
    if np.linalg.norm( b - a ) < 1e-6:
        return
    u, v = _ring_axes( b - a )
    dirs = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v for k in range( sides ) ]
    for k in range( sides ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % sides]
        _face( model, paint, [ a + r * d0, a + r * d1, b + r * d1, b + r * d0 ], d0 + d1, normals=[ d0, d1, d1, d0 ] )
    axis = _unit( b - a )
    if caps[0]:
        _face( model, paint, [ a + r * d for d in dirs ], -axis )
    if caps[1]:
        _face( model, paint, [ b + r * d for d in dirs ], axis )


def frustum( model, a, b, r0, r1, paint, sides=16, inside=None ):
    """ A round taper, shaded smooth and open at both ends; inside paints its inner face too. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    axis = _unit( b - a )
    length = np.linalg.norm( b - a )
    u, v = _ring_axes( b - a )
    dirs = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v for k in range( sides ) ]
    slope = ( r0 - r1 ) / length
    for k in range( sides ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % sides]
        n0, n1 = _unit( d0 + slope * axis ), _unit( d1 + slope * axis )
        pts = [ a + r0 * d0, a + r0 * d1, b + r1 * d1, b + r1 * d0 ]
        _face( model, paint, pts, n0 + n1, normals=[ n0, n1, n1, n0 ] )
        if inside:
            _face( model, inside, pts, -( n0 + n1 ), normals=[ -n0, -n1, -n1, -n0 ] )


def disc( model, paint, centre, normal, r, sides=16 ):
    c, nrm = np.asarray( centre, float ), _unit( normal )
    u, v = _ring_axes( nrm )
    _face( model, paint, [ c + r * ( math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v )
                           for k in range( sides ) ], nrm )


def annulus( model, paint, centre, r0, r1, z, sides=24 ):
    """ A flat ring facing up at height z. """
    for k in range( sides ):
        t0, t1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        p = [ ( centre[0] + r * math.cos( t ), centre[1] + r * math.sin( t ), z ) for r, t in
              ( ( r0, t0 ), ( r1, t0 ), ( r1, t1 ), ( r0, t1 ) ) ]
        _face( model, paint, p, ( 0, 0, 1 ) )


def ring( model, centre, r_out, r_in, z0, z1, paint, sides=24, top=None ):
    """ A round ring standing on z0: outer and inner walls and a top annulus (a tyre, a manhole frame). """
    c = np.array( ( centre[0], centre[1] ), float )
    for k in range( sides ):
        t0, t1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        d0, d1 = np.array( ( math.cos( t0 ), math.sin( t0 ), 0.0 ) ), np.array( ( math.cos( t1 ), math.sin( t1 ), 0.0 ) )
        for r, sign in ( ( r_out, 1.0 ), ( r_in, -1.0 ) ):
            if r <= 0:
                continue
            a0, a1 = np.r_[ c + r * d0[:2], z0 ], np.r_[ c + r * d1[:2], z0 ]
            b0, b1 = np.r_[ c + r * d0[:2], z1 ], np.r_[ c + r * d1[:2], z1 ]
            _face( model, paint, [ a0, a1, b1, b0 ], sign * ( d0 + d1 ), normals=[ sign * d0, sign * d1, sign * d1, sign * d0 ] )
    annulus( model, top or paint, centre, max( r_in, 0.0 ), r_out, z1, sides )


class Frame:
    """ A local frame on the floor: x across the front (to the right as you face it), y out of the front, z up. """

    def __init__( self, e, n, z, facing ):
        self.o = np.array( ( e, n, z ), float )
        self.y = np.array( DIRS[facing] )
        self.z = np.array( ( 0.0, 0.0, 1.0 ) )
        self.x = np.cross( self.z, self.y )      # to the right of someone looking at the front

    def p( self, x, y, z ):
        return self.o + self.x * x + self.y * y + self.z * z

    def box( self, model, x0, x1, y0, y1, z0, z1, paint, skip=() ):
        """ An axis-aligned box in this frame (the frames here are always plan-aligned). """
        a, b = self.p( x0, y0, z0 ), self.p( x1, y1, z1 )
        model.box( np.minimum( a, b ), np.maximum( a, b ), paint, skip=skip )

    def quad( self, model, paint, x0, x1, y, z0, z1, uv=None ):
        """ A rectangle in the plane y, facing +y. """
        pts = [ self.p( x0, y, z0 ), self.p( x1, y, z0 ), self.p( x1, y, z1 ), self.p( x0, y, z1 ) ]
        model.polygon( paint, pts, normal=self.y, uv=uv )


def _atlas_uv( atlas, name ):
    try:
        import railhead_materials as RM
        u0, v0, u1, v1 = ( float( x ) for x in RM.rect_uv( atlas, name ) )
        return [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]
    except Exception:
        return None


# ---------------------------------------------------------------------------------------------------------------------
# On walls

CITY_LIGHT = ( 46.85, 68.9 )      # 1190 x 1750 mm, the poster's visible area


def city_light( model, e, n, facing, poster, bottom=40.0, atlas="rw_posters", depth=3.2 ):
    """ A wall-mounted City-Light case: an anodised aluminium frame 60 mm round the poster, 80 mm deep, with a
    glazed front, the poster behind the glass and a thin opal light line round its inside edge. (e, n) is on the
    wall's face; facing is the way the poster looks. No collision. Returns the light position just in front of it. """
    w, h = CITY_LIGHT
    F = Frame( e, n, bottom, facing )
    b = 2.4
    hw = w / 2 + b
    # The case's back box and its four frame members, chamfered by a second, slightly smaller face on the front.
    F.box( model, -hw, hw, 0.0, depth - 0.8, -b, h + b, "rw_steel_grey" )
    for x0, x1, z0, z1 in ( ( -hw, hw, -b, 0.0 ), ( -hw, hw, h, h + b ), ( -hw, -w / 2, 0.0, h ), ( w / 2, hw, 0.0, h ) ):
        F.box( model, x0 + 0.3, x1 - 0.3, depth - 0.8, depth, z0 + 0.3, z1 - 0.3, "rw_steel" )
    # The light line round the poster's edge, behind the glass.
    for x0, x1, z0, z1 in ( ( -w / 2, w / 2, 0.0, 0.35 ), ( -w / 2, w / 2, h - 0.35, h ),
                            ( -w / 2, -w / 2 + 0.35, 0.0, h ), ( w / 2 - 0.35, w / 2, 0.0, h ) ):
        F.quad( model, "rw_lamp_cool", x0, x1, depth - 0.75, z0, z1 )
    F.quad( model, atlas, -w / 2 + 0.35, w / 2 - 0.35, depth - 0.78, 0.35, h - 0.35, uv=_atlas_uv( atlas, poster ) )
    F.quad( model, "rw_glass", -w / 2, w / 2, depth - 0.3, 0.0, h )
    # A lock on the frame's side and a cable gland under it.
    F.box( model, hw - 0.1, hw + 0.3, 1.0, 2.0, h * 0.45, h * 0.45 + 1.6, "rw_steel_dark" )
    rod( model, F.p( hw - 3.0, 1.0, -b ), F.p( hw - 3.0, 1.0, -b - 2.0 ), 0.35, "rw_black", 6 )
    return tuple( F.p( 0.0, 14.0, h / 2 ) )


def bracket_lamp( model, e, n, z, facing, arm=16.0 ):
    """ A wall bracket lamp of about 1900: a cast backplate, a scrolled arm out from the wall and an opal globe in a
    gallery under it, its centre arm out from the wall at height z. The globe is dress_globe, a third of the battens'
    glow, so the lamp reads as a globe on a dark arm rather than a white dot. No collision. Returns the globe's
    centre. """
    register( model, "dress_globe" )
    F = Frame( e, n, z, facing )
    F.box( model, -3.0, 3.0, 0.0, 0.9, 3.5, 14.5, "rw_steel_dark" )
    F.box( model, -2.1, 2.1, 0.9, 1.4, 4.6, 13.4, "rw_steel_dark" )
    pts = [ F.p( 0.0, 1.3, 11.0 ), F.p( 0.0, arm * 0.45, 14.5 ), F.p( 0.0, arm * 0.85, 12.5 ), F.p( 0.0, arm, 8.0 ) ]
    for a, b in zip( pts, pts[1:] ):
        rod( model, a, b, 0.8, "rw_steel_dark", 10 )
    rod( model, F.p( 0.0, 1.3, 6.0 ), F.p( 0.0, arm * 0.55, 11.6 ), 0.55, "rw_steel_dark", 8 )
    # A small scroll under the arm's root.
    rod( model, F.p( 0.0, 1.3, 6.0 ), F.p( 0.0, 3.2, 4.0 ), 0.5, "rw_steel_dark", 8, caps=( False, True ) )
    centre = F.p( 0.0, arm, 0.0 )
    rod( model, centre + ( 0, 0, 5.0 ), centre + ( 0, 0, 8.0 ), 1.6, "rw_steel_dark", 12, caps=( True, True ) )
    frustum( model, centre + ( 0, 0, 5.0 ), centre + ( 0, 0, 3.6 ), 1.6, 3.0, "rw_steel_dark", 12 )
    # The globe: a sphere of stacked bands.
    r, bands = 4.2, 6
    for k in range( bands ):
        t0, t1 = math.pi * k / bands, math.pi * ( k + 1 ) / bands
        z0, z1 = r * math.cos( t0 ), r * math.cos( t1 )
        r0, r1 = max( r * math.sin( t0 ), 0.01 ), max( r * math.sin( t1 ), 0.01 )
        frustum( model, centre + ( 0, 0, z0 - 0.6 ), centre + ( 0, 0, z1 - 0.6 ), min( r0, 3.0 ) if k == 0 else r0, r1,
                 "dress_globe", 14 )
    return tuple( centre - ( 0, 0, 0.6 ) )


def extinguisher( model, e, n, facing, z0=0.0 ):
    """ A 6 kg powder extinguisher on its wall bracket, 1.1 m to its handle, with the red-and-white fire sign over
    it. (e, n) on the wall's face. No collision. """
    F = Frame( e, n, z0, facing )
    F.box( model, -2.4, 2.4, 0.0, 0.5, 22.0, 30.0, "rw_steel_dark" )
    c = F.p( 0.0, 3.8, 0.0 )
    model.cylinder( ( c[0], c[1] ), 3.15, z0 + 18.0, z0 + 37.0, { "side": "rw_red_paint", "top": "rw_red_paint" },
                    sides=14, collide=None )
    frustum( model, c + ( 0, 0, 37.0 ), c + ( 0, 0, 39.0 ), 3.15, 1.2, "rw_red_paint", 14 )
    rod( model, c + ( 0, 0, 39.0 ), c + ( 0, 0, 41.0 ), 0.7, "rw_steel", 8, caps=( False, True ) )
    rod( model, c + ( 0, 0, 41.0 ), c + F.y * 3.5 + ( 0, 0, 41.5 ), 0.4, "rw_black", 6 )
    # The hose down its side.
    hose = [ c + F.x * 3.0 + ( 0, 0, 39.0 ), c + F.x * 3.6 + ( 0, 0, 30.0 ), c + F.x * 3.4 + ( 0, 0, 22.0 ) ]
    for a, b in zip( hose, hose[1:] ):
        rod( model, a, b, 0.5, "rw_black", 6 )
    # Its label band, and the sign over it: a red square plate, white flame pictogram stood for by a white panel.
    model.cylinder( ( c[0], c[1] ), 3.2, z0 + 24.0, z0 + 31.0, { "side": "rw_white_paint" }, sides=14, collide=None )
    F.box( model, -4.7, 4.7, 0.0, 0.25, 52.0, 61.4, "rw_red_paint" )
    F.quad( model, "rw_white_paint", -2.0, 2.0, 0.27, 54.5, 59.0 )


# ---------------------------------------------------------------------------------------------------------------------
# On the ground (each lying a hair proud of the surface under it)

def gully( model, e, n, z, along="n" ):
    """ A road gully grate in the kerb's gutter: a cast frame round 300 x 500 mm of bars across the flow. """
    w, l = ( 5.9, 9.85 )
    if along == "e":
        lo, hi = ( e - l - 1.2, n - w - 1.2 ), ( e + l + 1.2, n + w + 1.2 )
    else:
        lo, hi = ( e - w - 1.2, n - l - 1.2 ), ( e + w + 1.2, n + l + 1.2 )
    model.box( ( lo[0], lo[1], z ), ( hi[0], hi[1], z + 0.2 ), { "default": "rw_steel_dark", "-z": None } )
    model.polygon( "rw_black", [ ( lo[0] + 1.2, lo[1] + 1.2, z + 0.21 ), ( hi[0] - 1.2, lo[1] + 1.2, z + 0.21 ),
                                 ( hi[0] - 1.2, hi[1] - 1.2, z + 0.21 ), ( lo[0] + 1.2, hi[1] - 1.2, z + 0.21 ) ] )
    count = 9
    for k in range( count ):
        f = -l + ( 2 * l ) * ( k + 0.5 ) / count
        if along == "e":
            model.box( ( e + f - 0.45, n - w, z ), ( e + f + 0.45, n + w, z + 0.28 ), "rw_steel_dark", skip=( "-z", ) )
        else:
            model.box( ( e - w, n + f - 0.45, z ), ( e + w, n + f + 0.45, z + 0.28 ), "rw_steel_dark", skip=( "-z", ) )


def manhole( model, e, n, z, r=11.8 ):
    """ A round D400 manhole cover (600 mm clear) in its square cast frame, with raised rings and two pick holes. """
    s = r + 3.2
    model.box( ( e - s, n - s, z ), ( e + s, n + s, z + 0.18 ), { "default": "rw_steel_dark", "-z": None } )
    disc( model, "rw_steel", ( e, n, z + 0.24 ), ( 0, 0, 1 ), r, 32 )
    for rr in ( r * 0.35, r * 0.62, r * 0.9 ):
        ring( model, ( e, n ), rr + 0.35, rr - 0.35, z + 0.24, z + 0.42, "rw_steel_dark", 32 )
    for sx in ( -1, 1 ):
        model.polygon( "rw_black", [ ( e + sx * r * 0.75 - 0.9, n - 0.35, z + 0.25 ), ( e + sx * r * 0.75 + 0.9, n - 0.35, z + 0.25 ),
                                     ( e + sx * r * 0.75 + 0.9, n + 0.35, z + 0.25 ), ( e + sx * r * 0.75 - 0.9, n + 0.35, z + 0.25 ) ] )


def floor_patch( model, paint, e0, e1, n0, n1, z, lift=0.2 ):
    model.polygon( paint, [ ( e0, n0, z + lift ), ( e1, n0, z + lift ), ( e1, n1, z + lift ), ( e0, n1, z + lift ) ] )


def apron( model, e0, e1, n0, n1, z, bay=192.0 ):
    """ A cast concrete apron 0.3 proud of the setts: its slabs, saw-cut joints every bay, and a darker edge strip
    where the setts meet it. """
    lift = 0.3
    model.box( ( e0, n0, z ), ( e1, n1, z + lift ), { "default": "rw_concrete", "-z": None } )
    n = n0 + bay
    while n < n1 - 10:
        model.polygon( "rw_black", [ ( e0 + 1, n - 0.25, z + lift + 0.03 ), ( e1 - 1, n - 0.25, z + lift + 0.03 ),
                                     ( e1 - 1, n + 0.25, z + lift + 0.03 ), ( e0 + 1, n + 0.25, z + lift + 0.03 ) ] )
        n += bay
    return z + lift


def drain_channel( model, e, n0, n1, z, width=7.9 ):
    """ A cast-iron slot drain along n: a 200 mm grating of bars across it in a steel angle frame, a black void
    beneath. """
    hw = width / 2
    model.box( ( e - hw - 1.0, n0, z ), ( e + hw + 1.0, n1, z + 0.2 ), { "default": "rw_steel_dark", "-z": None } )
    model.polygon( "rw_black", [ ( e - hw, n0 + 1, z + 0.22 ), ( e + hw, n0 + 1, z + 0.22 ), ( e + hw, n1 - 1, z + 0.22 ),
                                 ( e - hw, n1 - 1, z + 0.22 ) ] )
    n = n0 + 1.6
    while n < n1 - 1.6:
        model.box( ( e - hw, n - 0.4, z ), ( e + hw, n + 0.4, z + 0.32 ), "rw_steel_dark", skip=( "-z", "-e", "+e" ) )
        n += 1.8
    # A grating section's joint every metre.
    n = n0 + 39.4
    while n < n1 - 4:
        model.box( ( e - hw, n - 0.6, z ), ( e + hw, n + 0.6, z + 0.36 ), "rw_steel", skip=( "-z", ) )
        n += 39.4


def line( model, paint, a, b, width, z ):
    """ A painted road line from a to b ( plan points ). """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    d = _unit( np.r_[ b - a, 0.0 ] )[:2]
    side = np.array( ( -d[1], d[0] ) ) * width / 2
    pts = [ a - side, b - side, b + side, a + side ]
    _face( model, paint, [ ( p[0], p[1], z ) for p in pts ], ( 0, 0, 1 ) )


def _clip( poly, e0, e1, n0, n1 ):
    """ Sutherland-Hodgman: a convex plan polygon clipped to a rectangle. """
    def cut( points, inside, cross ):
        out = []
        for k, p in enumerate( points ):
            q = points[( k + 1 ) % len( points )]
            if inside( p ):
                out.append( p )
                if not inside( q ):
                    out.append( cross( p, q ) )
            elif inside( q ):
                out.append( cross( p, q ) )
        return out

    def at_e( x ):
        return lambda p, q: ( x, p[1] + ( q[1] - p[1] ) * ( x - p[0] ) / ( q[0] - p[0] ) )

    def at_n( y ):
        return lambda p, q: ( p[0] + ( q[0] - p[0] ) * ( y - p[1] ) / ( q[1] - p[1] ), y )

    for inside, cross in ( ( lambda p: p[0] >= e0, at_e( e0 ) ), ( lambda p: p[0] <= e1, at_e( e1 ) ),
                           ( lambda p: p[1] >= n0, at_n( n0 ) ), ( lambda p: p[1] <= n1, at_n( n1 ) ) ):
        poly = cut( poly, inside, cross )
        if not poly:
            return []
    return poly


def hatched_box( model, e0, e1, n0, n1, z, paint="rw_line_yellow", border=4.7, stripe=5.9, pitch=19.7 ):
    """ A painted no-parking box (Sperrflaeche): a border line and diagonal stripes at 45 degrees. """
    for a, b in ( ( ( e0, n0 + border / 2 ), ( e1, n0 + border / 2 ) ), ( ( e0, n1 - border / 2 ), ( e1, n1 - border / 2 ) ),
                  ( ( e0 + border / 2, n0 + border ), ( e0 + border / 2, n1 - border ) ),
                  ( ( e1 - border / 2, n0 + border ), ( e1 - border / 2, n1 - border ) ) ):
        line( model, paint, a, b, border, z )
    span = ( e1 - e0 ) + ( n1 - n0 )
    k = 0.0
    s = stripe / math.sqrt( 2 )
    while k < span:
        c = e0 - ( n1 - n0 ) + k
        poly = [ ( c - s, n0 ), ( c + s, n0 ), ( c + s + ( n1 - n0 ), n1 ), ( c - s + ( n1 - n0 ), n1 ) ]
        clipped = _clip( poly, e0 + border, e1 - border, n0 + border, n1 - border )
        if len( clipped ) >= 3:
            _face( model, paint, [ ( p[0], p[1], z ) for p in clipped ], ( 0, 0, 1 ) )
        k += pitch


# ---------------------------------------------------------------------------------------------------------------------
# Standing things

def taxi_post( model, e, n, facing, z0=0.0 ):
    """ The taxi rank's sign: a galvanised 60 mm post 2.6 m tall with the "Taxi" plate (600 x 300 mm) at its top,
    reading both ways along the kerb. One thin collision box for the post. """
    F = Frame( e, n, z0, facing )
    model.cylinder( ( e, n ), 1.2, z0, z0 + 102.0, { "side": "rw_steel", "top": "rw_steel" }, sides=10, collide=None )
    disc( model, "rw_steel", ( e, n, z0 + 102.0 ), ( 0, 0, 1 ), 1.2, 10 )
    F.box( model, -12.2, 12.2, -0.6, 0.6, 86.0, 98.6, "rw_white_paint" )
    uv = _atlas_uv( "rw_signs", "taxi" )
    for sign in ( 1.0, -1.0 ):
        G = Frame( e, n, z0, facing if sign > 0 else { "+e": "-e", "-e": "+e", "+n": "-n", "-n": "+n" }[facing] )
        G.quad( model, "rw_signs", -11.8, 11.8, 0.62, 86.4, 98.2, uv=uv )
    # Clamps.
    for z in ( 88.0, 96.5 ):
        rod( model, ( e, n, z0 + z ), ( e, n, z0 + z + 1.0 ), 1.55, "rw_steel", 10, caps=( True, True ) )
    model.collision_box( ( e - 1.2, n - 1.2, z0 ), ( e + 1.2, n + 1.2, z0 + 102.0 ), METAL )


def cone( model, e, n, z0=0.0, tipped=False, heading=0.6 ):
    """ A 500 mm traffic cone: a red frustum with two white reflective bands on a black square base. tipped: knocked
    over, lying on its side with its tip towards heading (radians in plan). No collision. """
    if tipped:
        d = np.array( ( math.cos( heading ), math.sin( heading ), 0.0 ) )
        base = np.array( ( e, n, z0 + 7.0 ) )
        # The base plate on its edge, then the body sloping down to its tip resting on the ground.
        rod( model, base - d * 1.2, base, 9.9, "rw_rubber", 4, caps=( True, True ) )
        tip = base + d * 18.5 + np.array( ( 0.0, 0.0, -5.6 ) )
        ax = _unit( tip - base )
        bands = ( ( 0.0, 5.8, "rw_red_paint" ), ( 5.8, 8.8, "rw_white_paint" ), ( 8.8, 11.8, "rw_red_paint" ),
                  ( 11.8, 14.3, "rw_white_paint" ), ( 14.3, 18.5, "rw_red_paint" ) )
        r = lambda t: 5.0 - t * ( 5.0 - 1.1 ) / 18.5
        for ta, tb, paint in bands:
            frustum( model, base + ax * ta, base + ax * tb, r( ta ), r( tb ), paint, 14 )
        disc( model, "rw_red_paint", base + ax * 18.5, ax, 1.1, 10 )
        return
    model.box( ( e - 7.0, n - 7.0, z0 ), ( e + 7.0, n + 7.0, z0 + 1.2 ), { "default": "rw_rubber", "-z": None } )
    bands = ( ( 1.2, 7.0, "rw_red_paint" ), ( 7.0, 10.0, "rw_white_paint" ), ( 10.0, 13.0, "rw_red_paint" ),
              ( 13.0, 15.5, "rw_white_paint" ), ( 15.5, 19.7, "rw_red_paint" ) )
    r = lambda z: 5.0 - ( z - 1.2 ) * ( 5.0 - 1.1 ) / ( 19.7 - 1.2 )
    for za, zb, paint in bands:
        frustum( model, ( e, n, z0 + za ), ( e, n, z0 + zb ), r( za ), r( zb ), paint, 14 )
    disc( model, "rw_red_paint", ( e, n, z0 + 19.7 ), ( 0, 0, 1 ), 1.1, 10 )


def open_chamber( model, e, n, z, along="n" ):
    """ An inspection chamber opened for work: the 600 mm cover lifted off and lying beside its frame, the black
    shaft with its step irons, four cones round it. No collision: the hole is drawn as a dark floor. """
    r = 11.8
    s = r + 3.2
    model.box( ( e - s, n - s, z ), ( e + s, n + s, z + 0.18 ), { "default": "rw_steel_dark", "-z": None } )
    disc( model, "rw_black", ( e, n, z + 0.2 ), ( 0, 0, 1 ), r, 32 )
    ring( model, ( e, n ), r + 0.3, r, z - 14.0, z + 0.2, "rw_concrete_dark", 32, top="rw_steel_dark" )
    for k in range( 3 ):
        zz = z - 4.0 - 4.0 * k
        model.box( ( e - 4.0, n + r - 1.6, zz ), ( e + 4.0, n + r - 0.6, zz + 0.6 ), "rw_steel" )
    # The cover, lying beside it on its frame side.
    off = ( r * 2.4, 4.0 ) if along == "n" else ( 4.0, r * 2.4 )
    c = ( e + off[0], n + off[1] )
    disc( model, "rw_steel", ( c[0], c[1], z + 1.4 ), ( 0, 0, 1 ), r, 32 )
    ring( model, c, r, 0.0, z, z + 1.4, "rw_steel_dark", 32, top="rw_steel" )
    for dx, dy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ):
        cone( model, e + dx * 24.0 + off[0] * 0.4, n + dy * 24.0 + off[1] * 0.4, z, )


def tyre_stack( model, e, n, z0=0.0, count=4, lean=0.0 ):
    """ Old car tyres stacked flat: each 650 mm across, 205 mm tall, its 16-inch hole open. One box of collision. """
    R, r_in, h = 12.8, 8.2, 8.07
    register( model, "dress_tyre" )
    for k in range( count ):
        de = math.sin( k * 2.1 ) * 1.4 + lean * k
        dn = math.cos( k * 1.7 ) * 1.2
        za, zb = z0 + k * h, z0 + ( k + 1 ) * h
        c = np.array( ( e + de, n + dn ) )
        # The sidewalls: rounded in from the tread to the bead, so the tyre reads as a tyre, not a drum.
        bead = r_in + 1.1
        for z_s, z_m in ( ( za, za + h * 0.3 ), ( zb, zb - h * 0.3 ) ):
            frustum( model, ( c[0], c[1], z_s ), ( c[0], c[1], z_m ), R - 2.8, R - 0.2, "dress_tyre", 32 )
            annulus( model, "dress_tyre", c, bead, R - 2.8, z_s, 32 )
        # The bead's lip into the hole, and the hole's inside.
        ring( model, c, bead, r_in, za, zb, "dress_tyre", 32 )
        # The tread band, its grooves cut across it every 1/16 of a turn.
        model.cylinder( ( c[0], c[1] ), R - 0.2, za + h * 0.3, zb - h * 0.3, { "side": "dress_tyre", "top": None, "bottom": None },
                        sides=32, collide=None )
        for j in range( 16 ):
            t = 2 * math.pi * ( j + 0.25 * k ) / 16
            d = np.array( ( math.cos( t ), math.sin( t ), 0.0 ) )
            q = np.array( ( c[0], c[1], ( za + zb ) / 2 ) ) + d * ( R - 0.15 )
            tang = np.array( ( -d[1], d[0], 0.0 ) )
            for zz in ( -h * 0.18, h * 0.18 ):
                a = q + ( 0, 0, zz ) - tang * 1.6
                b = q + ( 0, 0, zz ) + tang * 1.6
                _face( model, "rw_black", [ a - ( 0, 0, 0.45 ), b - ( 0, 0, 0.45 ), b + ( 0, 0, 0.45 ), a + ( 0, 0, 0.45 ) ], d )
    model.collision_box( ( e - R - 1.5, n - R - 1.5, z0 ), ( e + R + 1.5, n + R + 1.5, z0 + count * h ), "rubber" )


def skip_bin( model, e, n, facing, z0=0.0, paint="rw_yellow_paint", fill="rw_ballast_old" ):
    """ A builder's skip (6 m3): a tapered steel box 3.4 m long at its rim, 2.6 m at its floor, 1.7 m wide and
    1.2 m deep, its ribs, lifting lugs and chain pins, half full of rubble. facing is the way its long side runs.
    One box of collision. """
    F = Frame( e, n, z0, facing )
    top_l, bot_l, w, h = 66.9, 51.2, 33.5, 47.2
    lugs = 2.0
    # The four walls (outer faces), as quads between floor and rim.
    corners_bot = [ ( -w, -bot_l ), ( w, -bot_l ), ( w, bot_l ), ( -w, bot_l ) ]
    corners_top = [ ( -w, -top_l ), ( w, -top_l ), ( w, top_l ), ( -w, top_l ) ]
    centre = F.p( 0.0, 0.0, h / 2 )
    for k in range( 4 ):
        a0, a1 = corners_bot[k], corners_bot[( k + 1 ) % 4]
        b0, b1 = corners_top[k], corners_top[( k + 1 ) % 4]
        pts = [ F.p( a0[0], a0[1], 2.0 ), F.p( a1[0], a1[1], 2.0 ), F.p( b1[0], b1[1], h ), F.p( b0[0], b0[1], h ) ]
        mid = sum( pts ) / 4
        _face( model, paint, pts, mid - centre )
        _face( model, paint, [ p - ( p - centre ) * 0.03 for p in pts ], centre - mid )
    # The rim, the floor skids and the fill.
    for y0, y1 in ( ( -top_l - 0.8, top_l + 0.8 ), ):
        F.box( model, -w - 0.8, w + 0.8, y0, y1, h - 1.6, h, paint, skip=( "-z", ) )
    for x in ( -w + 6.0, w - 6.0 ):
        F.box( model, x - 2.0, x + 2.0, -bot_l, bot_l, 0.0, 2.0, "rw_steel_dark" )
    fill_z = h * 0.55
    model.polygon( fill, [ F.p( -w + 1.0, -bot_l - 6.0, fill_z ), F.p( w - 1.0, -bot_l - 6.0, fill_z ),
                           F.p( w - 1.0, bot_l + 6.0, fill_z + 4.0 ), F.p( -w + 1.0, bot_l + 6.0, fill_z + 4.0 ) ],
                   normal=( 0, 0, 1 ) )
    # Ribs down the long sides, and the lifting lugs at the ends.
    for y in ( -30.0, -10.0, 10.0, 30.0 ):
        F.box( model, w, w + 1.2, y - 1.2, y + 1.2, 2.0, h - 1.6, paint )
        F.box( model, -w - 1.2, -w, y - 1.2, y + 1.2, 2.0, h - 1.6, paint )
    for sy in ( -1, 1 ):
        for sx in ( -1, 1 ):
            c = F.p( sx * ( w - 8.0 ), sy * ( top_l + lugs ), h - 10.0 )
            rod( model, c - F.x * 2.5, c + F.x * 2.5, 1.6, "rw_steel_dark", 10, caps=( True, True ) )
    lo = np.minimum( F.p( -w - 1.2, -top_l - 1, 0 ), F.p( w + 1.2, top_l + 1, h ) )
    hi = np.maximum( F.p( -w - 1.2, -top_l - 1, 0 ), F.p( w + 1.2, top_l + 1, h ) )
    model.collision_box( lo, hi, METAL )


def cable_drum( model, e, n, z0=0.0, axis="e", r=23.6, width=27.6, core=11.0, paint="rw_wood", cable="rw_black" ):
    """ A wooden cable drum standing on its flanges (1.2 m across), the black cable wound on its barrel, the flange
    planks' bolts. axis is the way its axle runs. One box of collision. """
    d = np.array( DIRS["+" + axis] )
    c = np.array( ( e, n, z0 + r ) )
    t = 1.6
    for s in ( -1, 1 ):
        a, b = c + d * s * ( width / 2 ), c + d * s * ( width / 2 + t )
        rod( model, a, b, r, paint, 20, caps=( True, True ) )
        # Bolt heads on the flange.
        u, v = _ring_axes( d )
        for k in range( 6 ):
            q = b + d * s * 0.05 + ( math.cos( k * math.pi / 3 ) * u + math.sin( k * math.pi / 3 ) * v ) * ( r * 0.55 )
            disc( model, "rw_steel_dark", q, d * s, 0.6, 6 )
        disc( model, "rw_steel_dark", b + d * s * 0.06, d * s, 3.0, 12 )
    rod( model, c - d * width / 2, c + d * width / 2, r * 0.72, cable, 20 )
    hi = np.abs( d ) * ( width / 2 + t ) + ( 1 - np.abs( d ) ) * r
    model.collision_box( c - hi, c + hi, WOOD )


def brick_pallet( model, e, n, z0=0.0, along="n", paint="rw_dressed_red" ):
    """ A strapped pallet of new facing bricks (1.2 x 1.0 m, 0.9 m of bricks on a pallet), shrink-banded twice each
    way. One box of collision. """
    F = Frame( e, n, z0, "+" + ( "n" if along == "n" else "e" ) )
    hx, hy = 19.7, 23.6
    # Pallet: top boards and three blocks.
    for y in ( -hy + 2.0, 0.0, hy - 2.0 ):
        F.box( model, -hx, hx, y - 2.0, y + 2.0, 0.0, 3.8, "rw_wood" )
    for k in range( 7 ):
        x = -hx + 2.4 + k * ( 2 * hx - 4.8 ) / 6
        F.box( model, x - 2.4, x + 2.4, -hy, hy, 3.8, 4.7, "rw_wood" )
    # The bricks, in courses with a dark line between each.
    zb, zt = 4.7, 4.7 + 35.4
    F.box( model, -hx + 0.4, hx - 0.4, -hy + 0.4, hy - 0.4, zb, zt, paint, skip=( "-z", ) )
    for k in range( 1, 13 ):
        z = zb + k * ( zt - zb ) / 13
        F.box( model, -hx + 0.35, hx - 0.35, -hy + 0.35, hy - 0.35, z - 0.12, z + 0.12, "rw_concrete_dark",
               skip=( "-z", "+z" ) )
    for x in ( -hx * 0.5, hx * 0.5 ):
        F.box( model, x - 0.6, x + 0.6, -hy + 0.25, hy - 0.25, zb - 0.2, zt + 0.15, "rw_black", skip=( "-z", ) )
    for y in ( -hy * 0.5, hy * 0.5 ):
        F.box( model, -hx + 0.25, hx - 0.25, y - 0.6, y + 0.6, zb - 0.2, zt + 0.15, "rw_black", skip=( "-z", ) )
    lo = np.minimum( F.p( -hx, -hy, 0 ), F.p( hx, hy, zt ) )
    hi = np.maximum( F.p( -hx, -hy, 0 ), F.p( hx, hy, zt ) )
    model.collision_box( lo, hi, STONE )


def cycle_stand( model, e, n, facing, z0=0.0 ):
    """ A stainless Anlehnbuegel: a 48 mm tube bent into an inverted U, 800 mm wide and 900 mm tall, set 100 mm into
    the paving, with a crossbar at 350 mm for a child's bike. facing is the way a bike stands against it (its plane
    is across facing). No collision (it's a tube a player steps past). """
    F = Frame( e, n, z0, facing )
    r, hw, h, bend = 0.95, 15.75, 35.4, 6.0
    pts = [ F.p( -hw, 0.0, 0.0 ), F.p( -hw, 0.0, h - bend ) ]
    for k in range( 1, 7 ):
        t = math.pi / 2 * k / 6
        pts.append( F.p( -hw + bend * ( 1 - math.cos( t ) ), 0.0, h - bend + bend * math.sin( t ) ) )
    for k in range( 0, 7 ):
        t = math.pi / 2 * k / 6
        pts.append( F.p( hw - bend + bend * math.sin( t ), 0.0, h - bend * ( 1 - math.cos( t ) ) ) )
    pts.append( F.p( hw, 0.0, 0.0 ) )
    for a, b in zip( pts, pts[1:] ):
        if np.linalg.norm( b - a ) > 1e-6:
            rod( model, a, b, r, "rw_steel", 10 )
    rod( model, F.p( -hw, 0.0, 13.8 ), F.p( hw, 0.0, 13.8 ), 0.75, "rw_steel", 8 )
    for x in ( -hw, hw ):
        disc( model, "rw_steel_dark", F.p( x, 0.0, 0.05 ), ( 0, 0, 1 ), 2.2, 10 )


# ---------------------------------------------------------------------------------------------------------------------
WEAR_PAINT = "rw_rubber"       # rough and nearly black: the hazard band's black stripes (wear uses the dress_ paints)
SEAL_PAINT = "dress_bitumen"   # sealing bitumen: dark grey with the asphalt's own grain, never rubber-black


# Road wear: sealed cracks, patch repairs and oil drips, as thin polygons on the asphalt (its texture no longer bakes
# them, so they don't repeat with its tile)

def sealed_crack( model, rng, start, heading, length, z, width=1.0, wander=0.06, step=14.0 ):
    """ A settlement crack routed out and sealed with hot bitumen: a dark grey band about 25 mm wide (+-15 %) that runs
    nearly straight along a heading (radians in plan) for length inches, turning at most 0.25 rad off it; a long one
    sometimes forks. """
    register( model, SEAL_PAINT )
    p = np.asarray( start, float )
    angle = heading
    pts = [ p.copy() ]
    travelled = 0.0
    while travelled < length:
        angle += rng.normal( 0.0, wander )
        angle = heading + max( -0.25, min( 0.25, angle - heading ) )
        p = p + step * np.array( ( math.cos( angle ), math.sin( angle ) ) )
        pts.append( p.copy() )
        travelled += step
    for a, b in zip( pts, pts[1:] ):
        w = width * rng.uniform( 0.85, 1.15 )
        line( model, SEAL_PAINT, a, b, w, z )
        # A round joint at each bend, so the band has no notches.
        disc( model, SEAL_PAINT, ( b[0], b[1], z + 0.002 ), ( 0, 0, 1 ), w / 2, 6 )
    if length > 300 and len( pts ) > 3 and rng.random() < 0.4:
        k = int( rng.integers( 1, len( pts ) - 1 ) )
        sealed_crack( model, rng, pts[k], heading + rng.choice( ( -0.5, 0.5 ) ), length * 0.3, z, width * 0.8, wander, step )


def patch_repair( model, rng, e0, e1, n0, n1, z, seal=1.2 ):
    """ A rectangle of newer asphalt cut in and rolled flat over a trench: one shade darker than the road (its binder
    not yet greyed by the sun) with its texture shifted, so its grain doesn't line up with the road's, its straight
    saw-cut edges sealed with a 30 mm bitumen band. """
    register( model, "dress_asphalt_fresh", SEAL_PAINT )
    off = rng.uniform( 0.0, 1.0, 2 )
    tile = 192.0
    pts = [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ]
    uv = [ ( e / tile + off[0], n / tile + off[1] ) for e, n, _ in pts ]
    model.polygon( "dress_asphalt_fresh", pts, normal=( 0, 0, 1 ), uv=uv )
    for a, b in ( ( ( e0, n0 ), ( e1, n0 ) ), ( ( e1, n0 ), ( e1, n1 ) ), ( ( e1, n1 ), ( e0, n1 ) ), ( ( e0, n1 ), ( e0, n0 ) ) ):
        line( model, SEAL_PAINT, a, b, seal * rng.uniform( 0.9, 1.1 ), z + 0.01 )


def oil_drips( model, rng, e, n, z, spread=( 10.0, 22.0 ), count=7, ground="asphalt" ):
    """ Oil and coolant drips where a car stands: a few small irregular spots round a centre, soaked in (the ground's
    own texture, darker and a little glossy), each with a fainter rim so its edge is soft. """
    core, halo = OIL_PAINTS[ground][:2]
    register( model, core, halo )
    for _ in range( count ):
        c = ( e + rng.normal( 0.0, spread[0] ), n + rng.normal( 0.0, spread[1] ) )
        r = rng.uniform( 0.9, 3.4 )
        sides = 9
        shape = [ ( rng.uniform( 0.6, 1.25 ), rng.uniform( 0.8, 1.3 ) ) for _ in range( sides ) ]
        for paint, k, lift in ( ( halo, 1.5, 0.0 ), ( core, 1.0, 0.004 ) ):
            pts = []
            for j, ( rr, squash ) in enumerate( shape ):
                t = 2 * math.pi * j / sides
                pts.append( ( c[0] + k * r * rr * math.cos( t ), c[1] + k * r * rr * math.sin( t ) * squash, z + lift ) )
            _face( model, paint, pts, ( 0, 0, 1 ) )


# The oil stains' paints on each ground: ( core, halo at 0.7 of the core's strength, fringe at 0.35 ).
OIL_PAINTS = { "asphalt": ( "dress_oil_stain", "dress_oil_halo", "dress_oil_fringe" ),
               "concrete": ( "dress_oil_concrete", "dress_oil_concrete_halo", "dress_oil_concrete_fringe" ),
               "setts": ( "dress_oil_setts", "dress_oil_setts_halo", "dress_oil_setts_fringe" ) }


# ---------------------------------------------------------------------------------------------------------------------
# The dressing's own materials: tinted copies of railhead_materials' textures (no new pictures), as vmats under
# materials/railhead/dress/. ensure_materials( root ) writes them under root (a stage laid out as Assets, or Assets
# itself at integration); register( model ) points a model's dress_ paints at them.

DRESS_DIR = "materials/railhead/dress"
# paint: ( the rw_ material whose textures it reuses, colour tint, roughness scale (an exponent: under 1 is rougher) )
DRESS_MATERIALS = {
    # The gutters' dust band and the asphalt showing through worn paint: barely darker than the road, faintly polished.
    # (The lanes' wheel paths are rw_asphalt's own, baked into its tile: railhead_materials.ASPHALT_WHEEL_PATHS.)
    "dress_asphalt_track": ( "rw_asphalt", ( 0.93, 0.93, 0.94 ), 1.05 ),
    # A patch of newer asphalt: one shade darker than the road, its binder not yet greyed by the sun.
    "dress_asphalt_fresh": ( "rw_asphalt", ( 0.80, 0.80, 0.82 ), 1.1 ),
    # Sealing bitumen over cracks and a patch's cut edges: dark grey with the asphalt's grain, not rubber-black.
    "dress_bitumen": ( "rw_asphalt", ( 0.42, 0.42, 0.44 ), 1.2 ),
    # Road paint worn by traffic: greyed and dulled.
    "dress_line_worn": ( "rw_line_white", ( 0.80, 0.79, 0.76 ), 0.85 ),
    # Chalk on the loading bank's face.
    "dress_chalk": ( "rw_line_white", ( 0.92, 0.91, 0.88 ), 0.6 ),
    # Spilt oil and coolant soaked into the ground: darker than it, a little glossy, never black, in three steps (the
    # core, a halo at 0.7 of its strength and a fringe at 0.35) so a stain's edge is soft. On asphalt, concrete, setts.
    "dress_oil_stain": ( "rw_asphalt", ( 0.60, 0.58, 0.56 ), 1.4 ),
    "dress_oil_halo": ( "rw_asphalt", ( 0.72, 0.71, 0.69 ), 1.25 ),
    "dress_oil_fringe": ( "rw_asphalt", ( 0.86, 0.85, 0.84 ), 1.1 ),
    "dress_oil_concrete": ( "rw_concrete", ( 0.60, 0.58, 0.56 ), 1.4 ),
    "dress_oil_concrete_halo": ( "rw_concrete", ( 0.72, 0.71, 0.69 ), 1.25 ),
    "dress_oil_concrete_fringe": ( "rw_concrete", ( 0.86, 0.85, 0.84 ), 1.1 ),
    "dress_oil_setts": ( "rw_setts", ( 0.60, 0.58, 0.56 ), 1.4 ),
    "dress_oil_setts_halo": ( "rw_setts", ( 0.72, 0.71, 0.69 ), 1.25 ),
    "dress_oil_setts_fringe": ( "rw_setts", ( 0.86, 0.85, 0.84 ), 1.1 ),
    # The gutters' grime: dust, leaf litter and oil washed against the kerb (and the loading bank's foot).
    "dress_gutter": ( "rw_asphalt", ( 0.62, 0.59, 0.55 ), 0.85 ),
    "dress_grime_setts": ( "rw_setts", ( 0.66, 0.63, 0.59 ), 0.85 ),
    "dress_grime_concrete": ( "rw_concrete", ( 0.70, 0.67, 0.62 ), 0.85 ),
    # Paving polished along the lines people walk: the same stone, its roughness lower.
    "dress_paving_polished": ( "rw_paving", ( 1.0, 1.0, 1.0 ), 1.6 ),
    "dress_paving_dark_polished": ( "rw_paving_dark", ( 1.0, 1.0, 1.0 ), 1.6 ),
    # Trodden chewing gum: flat grey-black spots.
    "dress_gum": ( "rw_asphalt", ( 0.40, 0.39, 0.38 ), 1.0 ),
    # Old tyres: grey with road dust, their rubber's grain from the asphalt's (rw_rubber is near black and smooth).
    "dress_tyre": ( "rw_asphalt", ( 0.36, 0.36, 0.37 ), 0.9 ),
    # A bracket lamp's opal globe: warm and lit, but a third of the battens' glow, so at 3 m it reads as a globe on its
    # arm, not a white dot burnt into the plaster.
    "dress_globe": ( "rw_lamp_warm", ( 0.95, 0.88, 0.78 ), 1.0, { "g_flSelfIllumBrightness": "2.00" } ),
}


def _base_vmat( paint, root=None ):
    """ The text of the rw_ vmat paint: from root (a stage being written, laid out as Assets) if it has it, else
    Assets. """
    from pathlib import Path
    assets = Path( __file__ ).resolve().parents[1] / "Assets"
    for base in ( ( Path( root ), ) if root else () ) + ( assets, ):
        path = base / f"materials/railhead/{paint}.vmat"
        if path.exists():
            return path.read_text()
    return None


def ensure_materials( root ):
    """ Writes the dress_ vmats under root/materials/railhead/dress/. Returns the paths written. """
    import re
    from pathlib import Path
    out = Path( root ) / DRESS_DIR
    out.mkdir( parents=True, exist_ok=True )
    written = []
    for paint, ( base, tint, rough, *more ) in DRESS_MATERIALS.items():
        text = _base_vmat( base, root )
        if text is None:
            continue
        text = text.replace( "// Tools/railhead_materials.py", f"// Tools/railhead_dress_detail.py ({base}, tinted)" )
        text = re.sub( r'g_vColorTint "[^"]*"', f'g_vColorTint "[{tint[0]:.3f} {tint[1]:.3f} {tint[2]:.3f} 1.0]"', text )
        text = re.sub( r'g_flRoughnessScaleFactor "[^"]*"', f'g_flRoughnessScaleFactor "{rough:g}"', text )
        for key, value in ( more[0] if more else {} ).items():
            text = re.sub( rf'{key} "[^"]*"', f'{key} "{value}"', text )
        path = out / f"{paint}.vmat"
        if not path.exists() or path.read_text() != text:
            path.write_text( text )
        written.append( path )
    return written


def register( model, *paints ):
    """ Points the dress_ paints at their vmats, with their base material's tile size. """
    try:
        import railhead_materials as RM
        known = RM.paints()
    except Exception:
        known = {}
    for paint in paints or DRESS_MATERIALS:
        base = DRESS_MATERIALS[paint][0]
        model.material_overrides[paint] = f"{DRESS_DIR}/{paint}.vmat"
        model.tile_overrides[paint] = float( known[base][1] ) if base in known else 192.0


# ---------------------------------------------------------------------------------------------------------------------
# Road and yard markings, wear at a distance

def wheel_tracks( model, rng, e_centre, n0, n1, z, gauge=59.0, width=11.0 ):
    """ A lane's two wheel paths as two straight continuous strips 280 mm wide, 1.5 m apart, from n0 to n1: barely
    darker than the road and faintly polished, low in contrast. Not placed while rw_asphalt bakes its own
    (railhead_materials.ASPHALT_WHEEL_PATHS): a lane would get four tracks. """
    register( model, "dress_asphalt_track" )
    for side in ( -1.0, 1.0 ):
        c0 = e_centre + side * gauge / 2
        pts = [ ( c0 - width / 2, n0, z ), ( c0 + width / 2, n0, z ), ( c0 + width / 2, n1, z ), ( c0 - width / 2, n1, z ) ]
        _face( model, "dress_asphalt_track", pts, ( 0, 0, 1 ) )


def worn_marking( model, rng, e0, e1, n0, n1, z, count=6, paint="dress_asphalt_track" ):
    """ Paint worn off a road marking where wheels cross it: irregular grey spots of asphalt showing through, lying a
    hair over the marking. """
    register( model, paint )
    for _ in range( count ):
        c = ( rng.uniform( e0, e1 ), rng.uniform( n0, n1 ) )
        r = rng.uniform( 0.8, 3.2 )
        pts = []
        for k in range( 8 ):
            t = 2 * math.pi * k / 8
            rr = r * rng.uniform( 0.5, 1.3 )
            pts.append( ( min( max( c[0] + rr * math.cos( t ), e0 ), e1 ), min( max( c[1] + rr * math.sin( t ) * 1.6, n0 ), n1 ), z ) )
        _face( model, paint, pts, ( 0, 0, 1 ) )


# A stroke font for road lettering and stencils: each glyph's strokes in a unit cell, x right, y up.
GLYPHS = {
    "T": ( ( ( 0, 1 ), ( 1, 1 ) ), ( ( 0.5, 1 ), ( 0.5, 0 ) ) ),
    "A": ( ( ( 0, 0 ), ( 0.5, 1 ) ), ( ( 0.5, 1 ), ( 1, 0 ) ), ( ( 0.22, 0.4 ), ( 0.78, 0.4 ) ) ),
    "X": ( ( ( 0, 0 ), ( 1, 1 ) ), ( ( 0, 1 ), ( 1, 0 ) ) ),
    "I": ( ( ( 0.5, 0 ), ( 0.5, 1 ) ), ),
    "1": ( ( ( 0.55, 0 ), ( 0.55, 1 ) ), ( ( 0.2, 0.75 ), ( 0.55, 1 ) ) ),
    "2": ( ( ( 0, 1 ), ( 1, 1 ) ), ( ( 1, 1 ), ( 1, 0.5 ) ), ( ( 1, 0.5 ), ( 0, 0.5 ) ), ( ( 0, 0.5 ), ( 0, 0 ) ), ( ( 0, 0 ), ( 1, 0 ) ) ),
    "3": ( ( ( 0, 1 ), ( 1, 1 ) ), ( ( 1, 1 ), ( 1, 0 ) ), ( ( 1, 0 ), ( 0, 0 ) ), ( ( 0.25, 0.5 ), ( 1, 0.5 ) ) ),
    "4": ( ( ( 0, 1 ), ( 0, 0.45 ) ), ( ( 0, 0.45 ), ( 1, 0.45 ) ), ( ( 0.75, 1 ), ( 0.75, 0 ) ) ),
    "5": ( ( ( 1, 1 ), ( 0, 1 ) ), ( ( 0, 1 ), ( 0, 0.5 ) ), ( ( 0, 0.5 ), ( 1, 0.5 ) ), ( ( 1, 0.5 ), ( 1, 0 ) ), ( ( 1, 0 ), ( 0, 0 ) ) ),
    "6": ( ( ( 1, 1 ), ( 0, 1 ) ), ( ( 0, 1 ), ( 0, 0 ) ), ( ( 0, 0 ), ( 1, 0 ) ), ( ( 1, 0 ), ( 1, 0.5 ) ), ( ( 1, 0.5 ), ( 0, 0.5 ) ) ),
    "7": ( ( ( 0, 1 ), ( 1, 1 ) ), ( ( 1, 1 ), ( 0.35, 0 ) ) ),
    "8": ( ( ( 0, 0 ), ( 1, 0 ) ), ( ( 1, 0 ), ( 1, 1 ) ), ( ( 1, 1 ), ( 0, 1 ) ), ( ( 0, 1 ), ( 0, 0 ) ), ( ( 0, 0.5 ), ( 1, 0.5 ) ) ),
}


def stroke_text( model, paint, text, origin, right, up, height, width, stroke, gap=None, rng=None ):
    """ text in the stroke font on a plane: origin is the first glyph's lower left corner, right and up unit vectors
    in the plane (the text's normal is right x up), each glyph width by height, strokes stroke wide. With an rng, the
    strokes' widths waver a little, as painted or chalked by hand. """
    o, r, u = ( np.asarray( v, float ) for v in ( origin, right, up ) )
    normal = np.cross( r, u )
    gap = width * 0.35 if gap is None else gap
    x = 0.0
    for ch in text:
        for ( x0, y0 ), ( x1, y1 ) in GLYPHS.get( ch, () ):
            a = o + r * ( x + x0 * width ) + u * ( y0 * height )
            b = o + r * ( x + x1 * width ) + u * ( y1 * height )
            d = _unit( b - a )
            w = stroke * ( rng.uniform( 0.85, 1.15 ) if rng is not None else 1.0 )
            a, b = a - d * w / 2, b + d * w / 2
            side = _unit( np.cross( normal, d ) ) * w / 2
            _face( model, paint, [ a - side, b - side, b + side, a + side ], normal )
        x += width + gap


def hazard_band( model, a, b, z, width=3.9, dash=11.8 ):
    """ A yellow-and-black painted hazard band from plan point a to b. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    line( model, "rw_line_yellow", a, b, width, z )
    d = _unit( np.r_[ b - a, 0.0 ] )[:2]
    length = float( np.linalg.norm( b - a ) )
    t = dash * 0.5
    while t + dash < length:
        line( model, WEAR_PAINT, a + d * t, a + d * ( t + dash ), width * 0.98, z + 0.01 )
        t += 2 * dash


def oil_stain( model, rng, e, n, z, size=( 18.0, 30.0 ), count=5, ground="concrete" ):
    """ An old oil and coolant stain soaked into the ground where a forklift or lorry stands: a few overlapping blotches,
    the largest in the middle, each in three steps (a darker, slightly glossy core of the ground's own texture, a halo
    at 0.7 of its strength, a fringe at 0.35), so the stain fades out at its edge instead of ending as a black disc;
    and drips round it. ground: 'concrete', 'setts' or 'asphalt'. """
    paints = OIL_PAINTS[ground]
    register( model, *paints )
    blobs = []
    for k in range( count ):
        c = ( e + rng.normal( 0.0, size[0] * 0.3 ), n + rng.normal( 0.0, size[1] * 0.3 ) )
        r = 1.5 * size[0] * ( 0.55 if k == 0 else rng.uniform( 0.2, 0.4 ) )
        sides = 16
        jitter = rng.uniform( 0.85, 1.15, sides )
        squash = size[1] / size[0] * rng.uniform( 0.75, 1.0 )
        blobs.append( ( c, r, jitter, squash ) )
    # All the fringes first, then the halos, then the cores, so no blotch's soft edge lies over another's core.
    for step, ( paint, scale ) in enumerate( zip( reversed( paints ), ( 1.55, 1.25, 1.0 ) ) ):
        for c, r, jitter, squash in blobs:
            sides = len( jitter )
            pts = []
            for j in range( sides ):
                t = 2 * math.pi * j / sides
                rr = r * scale * ( 0.5 * jitter[j] + 0.25 * jitter[j - 1] + 0.25 * jitter[( j + 1 ) % sides] )
                pts.append( ( c[0] + rr * math.cos( t ), c[1] + rr * math.sin( t ) * squash, z + 0.004 * step ) )
            _face( model, paint, pts, ( 0, 0, 1 ) )
    oil_drips( model, rng, e, n, z + 0.04, spread=( size[0] * 0.6, size[1] * 0.6 ), count=6, ground=ground )


# ---------------------------------------------------------------------------------------------------------------------
# Walls: notice frames, conduit

def notice_board( model, e, n, facing, entry, bottom=50.0, size=( 23.4, 33.1 ), atlas="rw_posters" ):
    """ A DIN A1 (594 x 841 mm) aluminium snap frame on a wall: a 25 mm frame round a notice under an anti-glare
    sheet, its four screws. (e, n) on the wall's face. No collision. """
    w, h = size
    F = Frame( e, n, bottom, facing )
    b = 1.0
    F.box( model, -w / 2 - b, w / 2 + b, 0.0, 0.5, -b, h + b, "rw_steel_grey" )
    for x0, x1, z0, z1 in ( ( -w / 2 - b, w / 2 + b, -b, 0.0 ), ( -w / 2 - b, w / 2 + b, h, h + b ),
                            ( -w / 2 - b, -w / 2, 0.0, h ), ( w / 2, w / 2 + b, 0.0, h ) ):
        F.box( model, x0 + 0.15, x1 - 0.15, 0.5, 0.9, z0 + 0.15, z1 - 0.15, "rw_steel" )
    F.quad( model, atlas, -w / 2, w / 2, 0.55, 0.0, h, uv=_atlas_uv( atlas, entry ) )
    F.quad( model, "rw_glass", -w / 2, w / 2, 0.7, 0.0, h )
    for x, z in ( ( -w / 2 - 0.5, -0.5 ), ( w / 2 + 0.5, -0.5 ), ( -w / 2 - 0.5, h + 0.5 ), ( w / 2 + 0.5, h + 0.5 ) ):
        disc( model, "rw_steel_dark", F.p( x, 0.92, z ), F.y, 0.22, 6 )


def conduit( model, points, r=1.0, paint="rw_steel", clip_every=31.5, out=None ):
    """ A galvanised steel conduit through points ( e, n, z ), a rounded joint at each corner, and with out (the
    wall's outward normal) a saddle clip every clip_every along it. No collision. """
    pts = [ np.asarray( p, float ) for p in points ]
    for a, b in zip( pts, pts[1:] ):
        rod( model, a, b, r, paint, 8 )
    for p in pts[1:-1]:
        rod( model, p - ( 0, 0, r * 0.3 ), p + ( 0, 0, r * 0.3 ), r * 1.15, paint, 8, caps=( True, True ) )
    if out is None:
        return
    out = _unit( out )
    for a, b in zip( pts, pts[1:] ):
        d = b - a
        length = float( np.linalg.norm( d ) )
        k = clip_every / 2
        while k < length:
            c = a + d * ( k / length )
            along = _unit( d )
            rod( model, c - along * 0.45, c + along * 0.45, r * 1.12, "rw_steel_dark", 8 )
            side = _unit( np.cross( out, along ) )
            for s in ( -1, 1 ):
                q = c - out * ( r * 0.85 ) + side * s * ( r + 0.7 )
                rod( model, q - along * 0.45, q + along * 0.45, 0.3, "rw_steel_dark", 4 )
            k += clip_every


def junction_box( model, e, n, z, facing, size=( 6.3, 6.3, 3.5 ) ):
    """ A grey cast junction box (160 x 160 x 90 mm) with its lid's four screws. (e, n) on the wall; z its centre. """
    w, h, d = size
    F = Frame( e, n, z - h / 2, facing )
    F.box( model, -w / 2, w / 2, 0.0, d - 0.4, 0.0, h, "rw_steel_grey" )
    F.box( model, -w / 2 + 0.2, w / 2 - 0.2, d - 0.4, d, 0.2, h - 0.2, "rw_steel_grey" )
    for x in ( -w / 2 + 0.7, w / 2 - 0.7 ):
        for zz in ( 0.7, h - 0.7 ):
            disc( model, "rw_steel", F.p( x, d + 0.02, zz ), F.y, 0.2, 6 )


# ---------------------------------------------------------------------------------------------------------------------
# Standing: an advertising column

def litfass_column( model, e, n, posters=( "poster_city", "poster_sea", "poster_alps" ), z0=0.0 ):
    """ A Litfass column: a cast iron plinth 1.2 m across, a pasted drum 1.1 m across and 2.6 m high, then a moulded
    cornice and a ribbed dome with a finial, 3.6 m to the top. Posters pasted round the drum on plain paper. One box
    of collision (a solid object). """
    R, sides = 21.7, 40
    base_r, base_h = 23.6, 12.0
    drum0, drum1 = z0 + base_h, z0 + base_h + 102.0
    model.cylinder( ( e, n ), base_r, z0, z0 + base_h - 2.0, { "side": "rw_steel_dark", "top": "rw_steel_dark", "bottom": None },
                    sides=sides, collide=None )
    frustum( model, ( e, n, z0 + base_h - 2.0 ), ( e, n, drum0 ), base_r, R + 0.6, "rw_steel_dark", sides )
    model.cylinder( ( e, n ), R, drum0, drum1, { "side": "rw_white_paint", "top": None, "bottom": None }, sides=sides,
                    collide=None )
    arc = 2 * math.pi / len( posters )
    for k, poster in enumerate( posters ):
        uv = _atlas_uv( "rw_posters", poster )
        if uv is None:
            continue
        ( u0, v0 ), ( u1, _ ), ( _, v1 ), _ = uv
        width_rad = min( arc * 0.86, 46.85 * 1.15 / R )
        start = k * arc + 0.3
        steps = 8
        # The poster's height from the width it gets, so it keeps its proportions.
        height = 68.9 * ( width_rad * R ) / 46.85
        za, zb = drum0 + 14.0, drum0 + 14.0 + height
        for j in range( steps ):
            t0 = start + width_rad * j / steps
            t1 = start + width_rad * ( j + 1 ) / steps
            d0 = np.array( ( math.cos( t0 ), math.sin( t0 ), 0.0 ) )
            d1 = np.array( ( math.cos( t1 ), math.sin( t1 ), 0.0 ) )
            c = np.array( ( e, n, 0.0 ) )
            r = R + 0.08
            pts = [ c + d0 * r + ( 0, 0, za ), c + d1 * r + ( 0, 0, za ), c + d1 * r + ( 0, 0, zb ), c + d0 * r + ( 0, 0, zb ) ]
            # Seen from outside, the angle grows to the viewer's right.
            ua = u0 + ( u1 - u0 ) * j / steps
            ub = u0 + ( u1 - u0 ) * ( j + 1 ) / steps
            _face( model, "rw_posters", pts, d0 + d1, normals=[ d0, d1, d1, d0 ], uv=[ ( ua, v0 ), ( ub, v0 ), ( ub, v1 ), ( ua, v1 ) ] )
    # Cornice, dome and finial.
    frustum( model, ( e, n, drum1 ), ( e, n, drum1 + 3.0 ), R + 0.4, R + 3.2, "rw_steel_dark", sides )
    model.cylinder( ( e, n ), R + 3.2, drum1 + 3.0, drum1 + 7.0, { "side": "rw_steel_dark", "bottom": "rw_steel_dark", "top": None },
                    sides=sides, collide=None )
    frustum( model, ( e, n, drum1 + 7.0 ), ( e, n, drum1 + 9.0 ), R + 3.2, R + 1.0, "rw_steel_dark", sides )
    prev_r, prev_z = R + 1.0, drum1 + 9.0
    for k in range( 1, 7 ):
        t = k / 6 * math.pi / 2
        rr, zz = ( R + 1.0 ) * math.cos( t ), drum1 + 9.0 + 14.0 * math.sin( t )
        frustum( model, ( e, n, prev_z ), ( e, n, zz ), prev_r, max( rr, 1.2 ), "rw_steel_dark", sides )
        prev_r, prev_z = max( rr, 1.2 ), zz
    for k in range( 8 ):       # the dome's ribs
        t = 2 * math.pi * k / 8
        d = np.array( ( math.cos( t ), math.sin( t ), 0.0 ) )
        pts = [ np.array( ( e, n, 0.0 ) ) + d * ( R + 1.0 ) * math.cos( a / 6 * math.pi / 2 ) * 1.02 +
                np.array( ( 0, 0, drum1 + 9.0 + 14.0 * math.sin( a / 6 * math.pi / 2 ) ) ) for a in range( 7 ) ]
        for a, b in zip( pts, pts[1:] ):
            rod( model, a, b, 0.5, "rw_steel_dark", 5 )
    rod( model, ( e, n, prev_z ), ( e, n, prev_z + 6.0 ), 1.0, "rw_steel_dark", 8, caps=( False, True ) )
    rod( model, ( e, n, prev_z + 6.0 ), ( e, n, prev_z + 8.0 ), 1.8, "rw_steel_dark", 8, caps=( True, True ) )
    model.collision_box( ( e - R, n - R, z0 ), ( e + R, n + R, drum1 + 23.0 ), "metal" )


# ---------------------------------------------------------------------------------------------------------------------
# Light fittings

def handrail_led( model, a, b, r=0.32 ):
    """ An LED line under a stair's handrail, from a to b: a thin opal strip in a dark channel. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    rod( model, a + ( 0, 0, 0.35 ), b + ( 0, 0, 0.35 ), r * 1.6, "rw_steel_dark", 6 )
    rod( model, a, b, r, "rw_lamp_cool", 6 )


def scaled_into( target, source, centre, k ):
    """ Every polygon of source, scaled by k about centre (normals unchanged), added to target. """
    c = np.asarray( centre, float )
    for paint, items in source.polygons.items():
        base = len( target.polygons[paint] )
        for i, ( points, normal ) in enumerate( items ):
            target.polygons[paint].append( ( [ c + ( np.asarray( p, float ) - c ) * k for p in points ], normal ) )
            if ( paint, i ) in source.polygon_uvs:
                target.polygon_uvs[( paint, base + i )] = source.polygon_uvs[( paint, i )]
            if ( paint, i ) in source.polygon_normals:
                target.polygon_normals[( paint, base + i )] = source.polygon_normals[( paint, i )]
    target.material_overrides.update( source.material_overrides )
    target.tile_overrides.update( source.tile_overrides )


# ---------------------------------------------------------------------------------------------------------------------
# Floor wear: polished walking lines and trodden gum

def polished_band( model, base, e0, e1, n0, n1, z, model_name, lift=0.03 ):
    """ A band of the floor's own stone (base: "rw_paving" or "rw_paving_dark") polished by feet, laid a hair over it:
    its UVs are worked out as map_kit gives the floor's own in the station model model_name, so the joints line up and
    only the stone's sheen changes. """
    import map_kit as K
    paint = { "rw_paving": "dress_paving_polished", "rw_paving_dark": "dress_paving_dark_polished" }[base]
    register( model, paint )
    tile = model.tile_overrides[paint]
    offset = K.uv_offset( model_name )
    pts = [ ( e0, n0, z + lift ), ( e1, n0, z + lift ), ( e1, n1, z + lift ), ( e0, n1, z + lift ) ]
    wn = K.to_world( ( 0.0, 0.0, 1.0 ) )
    uv = [ K.face_uv( K.to_world( p ), wn, base, offset, tile ) for p in pts ]
    model.polygon( paint, pts, normal=( 0, 0, 1 ), uv=uv )


def gum_spots( model, rng, e0, e1, n0, n1, z, count, avoid=() ):
    """ Trodden chewing gum: count flat grey-black spots 10-25 mm across scattered over a floor, thicker towards its
    middle; avoid is a list of ( e0, e1, n0, n1 ) to leave clear. """
    register( model, "dress_gum" )
    placed = 0
    tries = 0
    while placed < count and tries < count * 4:
        tries += 1
        e = rng.triangular( e0, ( e0 + e1 ) / 2, e1 )
        n = rng.uniform( n0, n1 )
        if any( a <= e <= b and c <= n <= d for a, b, c, d in avoid ):
            continue
        r = rng.uniform( 0.2, 0.5 )
        pts = []
        for k in range( 6 ):
            a = 2 * math.pi * k / 6 + rng.uniform( 0, 0.4 )
            rr = r * rng.uniform( 0.75, 1.2 )
            pts.append( ( e + rr * math.cos( a ), n + rr * math.sin( a ), z + 0.04 ) )
        _face( model, "dress_gum", pts, ( 0, 0, 1 ) )
        placed += 1


# ---------------------------------------------------------------------------------------------------------------------
# Platform smoking zones, wall signs, road works

def smoking_zone( model, e0, e1, n0, n1, z, corner=( 1, 1 ) ):
    """ A platform's smoking area (Raucherbereich), as on every DB platform: a 100 mm yellow line round a rectangle
    on the paving, and a stainless ashtray pillar 1 m tall standing at one corner just inside it (corner: which, +1/-1
    in e and n). The pillar is one thin collision box; the paint has none. """
    w = 4.0
    lift = z + 0.06
    for a, b in ( ( ( e0, n0 + w / 2 ), ( e1, n0 + w / 2 ) ), ( ( e0, n1 - w / 2 ), ( e1, n1 - w / 2 ) ),
                  ( ( e0 + w / 2, n0 + w ), ( e0 + w / 2, n1 - w ) ), ( ( e1 - w / 2, n0 + w ), ( e1 - w / 2, n1 - w ) ) ):
        line( model, "rw_line_yellow", a, b, w, lift )
    ce = ( e1 - 9.0 ) if corner[0] > 0 else ( e0 + 9.0 )
    cn = ( n1 - 9.0 ) if corner[1] > 0 else ( n0 + 9.0 )
    ashtray_pillar( model, ce, cn, z )


def ashtray_pillar( model, e, n, z0=0.0, r=4.0, height=40.0 ):
    """ A brushed stainless ash column (a Standascher): a 200 mm tube on a round foot plate, a perforated top tray and
    a dark ring of slots round its head where the ash goes in. One collision box. """
    c = ( e, n )
    model.cylinder( c, r + 1.6, z0, z0 + 0.6, { "side": "rw_steel", "top": "rw_steel" }, sides=20, collide=None )
    model.cylinder( c, r, z0 + 0.6, z0 + height - 5.0, { "side": "rw_steel" }, sides=20, collide=None )
    # The slots' ring and the head over it.
    model.cylinder( c, r - 0.15, z0 + height - 5.0, z0 + height - 2.8, { "side": "rw_black" }, sides=20, collide=None )
    model.cylinder( c, r + 0.2, z0 + height - 2.8, z0 + height, { "side": "rw_steel", "top": "rw_steel" }, sides=20,
                    collide=None )
    annulus( model, "rw_steel_dark", c, r - 1.4, r - 0.4, z0 + height + 0.02, 20 )
    disc( model, "rw_black", ( e, n, z0 + height + 0.03 ), ( 0, 0, 1 ), r - 1.4, 20 )
    # A yellow band round it, matching the zone's line, and a door's seam down its front.
    model.cylinder( c, r + 0.05, z0 + height - 12.0, z0 + height - 9.5, { "side": "rw_line_yellow" }, sides=20,
                    collide=None )
    model.collision_box( ( e - r, n - r, z0 ), ( e + r, n + r, z0 + height ), METAL )


def wall_sign( model, e, n, facing, entries, widths, bottom, height, atlas="rw_signs", depth=1.2, min_width=0.0 ):
    """ A single-sided sign on a wall or a glazing's mullions: an aluminium tray depth deep with its entries side by
    side on the face, 25 mm frame round them, on two stand-off brackets. (e, n) on the wall's face, facing the way it
    reads; bottom is z. No collision. """
    F = Frame( e, n, bottom, facing )
    total = sum( widths ) + 1.2 * ( len( widths ) - 1 )
    hw = max( total, min_width ) / 2 + 1.0
    for x in ( -hw * 0.6, hw * 0.6 ):
        F.box( model, x - 0.5, x + 0.5, 0.0, 0.8, height * 0.3, height * 0.7, "rw_steel_dark" )
    F.box( model, -hw, hw, 0.8, 0.8 + depth, -1.0, height + 1.0, "rw_steel_grey" )
    at = -total / 2
    for name, w in zip( entries, widths ):
        F.quad( model, atlas, at, at + w, 0.85 + depth, 0.0, height, uv=_atlas_uv( atlas, name ) )
        at += w + 1.2


def road_barrier( model, e, n, along="e", length=39.4, z0=0.0 ):
    """ A red-and-white road works barrier (Absperrschranke), 1 m long, its 250 mm board 1 m up on two posts in yellow
    weighted feet. along: the way the board runs ('e' or 'n'). No collision. """
    F = Frame( e, n, z0, "+n" if along == "e" else "+e" )
    hl = length / 2
    for x in ( -hl + 3.0, hl - 3.0 ):
        F.box( model, x - 7.0, x + 7.0, -4.0, 4.0, 0.0, 2.4, "rw_yellow_paint" )
        F.box( model, x - 0.7, x + 0.7, -0.7, 0.7, 2.4, 39.4, "rw_steel" )
    # The board in red and white blocks, a quarter of its length each, both faces.
    k = 6
    for j in range( k ):
        x0, x1 = -hl + length * j / k, -hl + length * ( j + 1 ) / k
        F.box( model, x0, x1, -0.4, 0.4, 29.5, 39.4, "rw_red_paint" if j % 2 == 0 else "rw_white_paint" )



def loudspeaker( model, e, n, z, facing, tilt=0.35 ):
    """ A platform PA loudspeaker: a light grey cabinet 300 x 200 x 160 mm on a short swivel arm, angled down at the
    platform (tilt radians), its dark grille on the front. (e, n) where the arm meets its support; no collision. """
    F = Frame( e, n, z, facing )
    rod( model, F.p( 0.0, 0.0, 0.0 ), F.p( 0.0, 3.2, 0.0 ), 0.45, "rw_steel_dark", 8, caps=( False, True ) )
    c = F.p( 0.0, 6.4, -0.6 )
    d = F.y * math.cos( tilt ) - np.array( ( 0.0, 0.0, 1.0 ) ) * math.sin( tilt )      # the cabinet's front
    up = np.cross( d, F.x )
    hw, hh, hd = 5.9, 3.9, 3.15
    corners = lambda sx, sy, sz: c + F.x * sx * hw + up * sy * hh + d * sz * hd
    faces = ( ( d, [ ( -1, -1, 1 ), ( 1, -1, 1 ), ( 1, 1, 1 ), ( -1, 1, 1 ) ], "rw_steel_grey" ),
              ( -d, [ ( 1, -1, -1 ), ( -1, -1, -1 ), ( -1, 1, -1 ), ( 1, 1, -1 ) ], "rw_steel_grey" ),
              ( up, [ ( -1, 1, 1 ), ( 1, 1, 1 ), ( 1, 1, -1 ), ( -1, 1, -1 ) ], "rw_steel_grey" ),
              ( -up, [ ( -1, -1, -1 ), ( 1, -1, -1 ), ( 1, -1, 1 ), ( -1, -1, 1 ) ], "rw_steel_grey" ),
              ( F.x, [ ( 1, -1, 1 ), ( 1, -1, -1 ), ( 1, 1, -1 ), ( 1, 1, 1 ) ], "rw_steel_grey" ),
              ( -F.x, [ ( -1, -1, -1 ), ( -1, -1, 1 ), ( -1, 1, 1 ), ( -1, 1, -1 ) ], "rw_steel_grey" ) )
    for normal, pts, paint in faces:
        _face( model, paint, [ corners( *p ) for p in pts ], normal )
    # The grille, a hair proud of the front, inside a 12 mm rim.
    g = [ c + F.x * sx * ( hw - 0.5 ) + up * sy * ( hh - 0.5 ) + d * ( hd + 0.04 ) for sx, sy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ]
    _face( model, "rw_steel_dark", g, d )


def column_kit( model, e, n, r=8.0, speakers=True, cable_side="+n" ):
    """ What a shed column carries on a DB platform: the PA loudspeakers either side under its sign band, facing the
    platform's two edges, their cable in a galvanised conduit up the column's side from a junction box at 2.4 m. No
    collision. """
    s = 1.0 if cable_side == "+n" else -1.0
    # The conduit and its saddle clips, up the column's face from the box to the band.
    conduit( model, [ ( e, n + s * ( r + 0.9 ), 96.0 ), ( e, n + s * ( r + 0.6 ), 224.0 ) ], r=0.7, clip_every=30.0,
             out=( 0.0, s, 0.0 ) )
    junction_box( model, e, n + s * ( r + 0.2 ), 92.0, cable_side, size=( 5.5, 6.3, 3.0 ) )
    if speakers:
        for facing, sx in ( ( "+e", 1.0 ), ( "-e", -1.0 ) ):
            loudspeaker( model, e + sx * ( r - 0.3 ), n, 214.0, facing )
