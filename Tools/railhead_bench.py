"""Railhead's platform bench in detail, for railhead_props.bench and railhead_furniture.bench_details.

- slat: a hardwood slat (the seat's or the backrest's), its four long edges eased round (7 mm), cut square at its ends.
  rw_wood is a scan of planks with dark gaps between them, so each face of a slat takes one plank of it, its grain
  along the slat, and the cut ends show end grain (rw_wood_end). Mapped the old way (rw_wood's world projection), a
  slat crossed a gap and showed a black line along it and across its end.
- armrest: the middle armrest of a long bench: one smooth casting from a foot plate on the front slat, up, over in a
  hand rest and back down into the backrest, its section a rounded square that widens where the hand rests and flares
  into the foot. It was four square bars meeting at angles, with a gap at the bend.

Frames are railhead_props.Frame: x along the bench, y towards its front, z up from the floor. Inches.
"""
import math
import zlib

import numpy as np

# The columns of rw_wood_color.png (2048 px across) between its planks' dark gaps, 18 px clear of where each gap
# wanders (measured down the picture: the gaps move about 5 px either way).
PLANKS = ( ( 26, 225 ), ( 276, 470 ), ( 521, 692 ), ( 740, 914 ), ( 965, 1124 ), ( 1172, 1334 ), ( 1382, 1565 ),
           ( 1612, 1785 ), ( 1833, 2005 ) )
PICTURE = 2048.0
PX_PER_INCH = 45.0          # rw_wood's own is 64, at which a seat slat's broad face (3.6") is wider than any plank
END = "rw_wood_end"         # the cut ends' end grain (railhead_prop_materials)
END_TILE = 8.0              # inches the end grain picture covers
EASE = 0.28                 # the slats' edge radius, about 7 mm
EASE_STEPS = 4              # facets on each eased edge


def _profile( hw, ht, r, steps=EASE_STEPS ):
    """ A rounded rectangle's outline anticlockwise, from the +s side: points ( s, t ) and their normals. """
    points, normals = [], []
    for cs, ct, a0 in ( ( 1, 1, 0.0 ), ( -1, 1, 90.0 ), ( -1, -1, 180.0 ), ( 1, -1, 270.0 ) ):
        for k in range( steps + 1 ):
            a = math.radians( a0 + 90.0 * k / steps )
            d = ( math.cos( a ), math.sin( a ) )
            points.append( ( cs * ( hw - r ) + r * d[0], ct * ( ht - r ) + r * d[1] ) )
            normals.append( d )
    return points, normals


def _runs( groups ):
    """ The outline's segments split into runs of one group each, in order round it: [ ( group, [ indices ] ) ]. """
    count = len( groups )
    start = next( i for i in range( count ) if groups[i] != groups[i - 1] )
    runs = []
    for step in range( count ):
        i = ( start + step ) % count
        if runs and runs[-1][0] == groups[i]:
            runs[-1][1].append( i )
        else:
            runs.append( ( groups[i], [ i ] ) )
    return runs


def _seed( F, *values ):
    key = ",".join( f"{v:.1f}" for v in ( *F.o, *F.y, *values ) )
    return zlib.crc32( key.encode() )


def slat( model, F, x0, x1, centre, across, through, width, thick, paint="rw_wood", index=0 ):
    """ A slat from x0 to x1 along the frame: its section's centre at ( y, z ) = centre, width along across and its
    thickness along through (unit ( y, z ) directions, through towards its broad face that shows: the seat's top, the
    backrest's front). index varies its planks between a bench's slats. """
    import railhead_props as P
    rng = np.random.default_rng( _seed( F, x0, x1, index ) )
    hw, ht = width / 2, thick / 2
    r = min( EASE, 0.45 * min( hw, ht ) )
    points, normals = _profile( hw, ht, r )
    count = len( points )
    a, b = np.asarray( across, float ), np.asarray( through, float )
    c = np.asarray( centre, float )

    def local( x, s, t ):
        yz = c + s * a + t * b
        return ( x, float( yz[0] ), float( yz[1] ) )

    def direction( s, t ):
        yz = s * a + t * b
        return ( 0.0, float( yz[0] ), float( yz[1] ) )

    # Each segment's group: the face of the slat its middle faces (the eased edges split at 45 degrees).
    seg_normal = [ np.add( normals[i], normals[( i + 1 ) % count] ) for i in range( count ) ]
    groups = [ ( "s", 1 if n[0] > 0 else -1 ) if abs( n[0] ) > abs( n[1] ) else ( "t", 1 if n[1] > 0 else -1 )
               for n in seg_normal ]
    v_offset = float( rng.uniform( 0.0, 1.0 ) )
    v0, v1 = x0 * PX_PER_INCH / PICTURE + v_offset, x1 * PX_PER_INCH / PICTURE + v_offset
    for group, indices in _runs( groups ):
        lengths = [ math.dist( points[i], points[( i + 1 ) % count] ) for i in indices ]
        run = sum( lengths )
        # A plank wide enough for the run at the slat's scale, else the widest, the run squeezed into it.
        fits = [ p for p in PLANKS if p[1] - p[0] >= run * PX_PER_INCH ] or [ max( PLANKS, key=lambda p: p[1] - p[0] ) ]
        lo, hi = fits[int( rng.integers( len( fits ) ) )]
        scale = min( PX_PER_INCH, ( hi - lo ) / run )
        middle = ( lo + hi ) / 2
        position = 0.0
        for i, length in zip( indices, lengths ):
            j = ( i + 1 ) % count
            ua = ( middle + ( position - run / 2 ) * scale ) / PICTURE
            ub = ( middle + ( position + length - run / 2 ) * scale ) / PICTURE
            position += length
            pa, pb = points[i], points[j]
            na, nb = direction( *normals[i] ), direction( *normals[j] )
            P._fpoly( model, F, paint, [ local( x0, *pa ), local( x1, *pa ), local( x1, *pb ), local( x0, *pb ) ],
                      direction( *seg_normal[i] ), uv=[ ( ua, v0 ), ( ua, v1 ), ( ub, v1 ), ( ub, v0 ) ],
                      normals=[ na, na, nb, nb ] )
    # The sawn ends, in end grain.
    for x, out in ( ( x0, -1.0 ), ( x1, 1.0 ) ):
        ou, ov = rng.uniform( 0.0, 1.0, 2 )
        P._fpoly( model, F, END, [ local( x, s, t ) for s, t in points ], ( out, 0.0, 0.0 ),
                  uv=[ ( float( ou + s / END_TILE ), float( ov + t / END_TILE ) ) for s, t in points ] )


# ---------------------------------------------------------------------------------------------------------------------
# The middle armrest

ARM_SIDES = 16              # facets round the casting's section
ARM_SAMPLES = 3             # rings per span of its spline
ARM_SQUARENESS = 4.0        # the section's superellipse exponent: 2 round, higher squarer


def _spline( points, per ):
    """ A centripetal Catmull-Rom curve through points, per samples a span, the last point included. """
    P = [ np.asarray( p, float ) for p in points ]
    P = [ 2 * P[0] - P[1] ] + P + [ 2 * P[-1] - P[-2] ]
    out = []
    for i in range( 1, len( P ) - 2 ):
        p0, p1, p2, p3 = P[i - 1:i + 3]
        t0 = 0.0
        t1 = t0 + max( np.linalg.norm( p1 - p0 ), 1e-6 ) ** 0.5
        t2 = t1 + max( np.linalg.norm( p2 - p1 ), 1e-6 ) ** 0.5
        t3 = t2 + max( np.linalg.norm( p3 - p2 ), 1e-6 ) ** 0.5
        for k in range( per ):
            t = t1 + ( t2 - t1 ) * k / per
            a1 = ( t1 - t ) / ( t1 - t0 ) * p0 + ( t - t0 ) / ( t1 - t0 ) * p1
            a2 = ( t2 - t ) / ( t2 - t1 ) * p1 + ( t - t1 ) / ( t2 - t1 ) * p2
            a3 = ( t3 - t ) / ( t3 - t2 ) * p2 + ( t - t2 ) / ( t3 - t2 ) * p3
            b1 = ( t2 - t ) / ( t2 - t0 ) * a1 + ( t - t0 ) / ( t2 - t0 ) * a2
            b2 = ( t3 - t ) / ( t3 - t1 ) * a2 + ( t - t1 ) / ( t3 - t1 ) * a3
            out.append( ( t2 - t ) / ( t2 - t1 ) * b1 + ( t - t1 ) / ( t2 - t1 ) * b2 )
    out.append( P[-2] )
    return out


def _smooth( e0, e1, x ):
    t = min( max( ( x - e0 ) / ( e1 - e0 ), 0.0 ), 1.0 )
    return t * t * ( 3 - 2 * t )


def _section( half_x, half_n ):
    """ The section's outline: ( x, n ) offsets and their normals, a superellipse half_x by half_n. """
    e = ARM_SQUARENESS
    out = []
    for k in range( ARM_SIDES ):
        a = 2 * math.pi * ( k + 0.5 ) / ARM_SIDES
        c, s = math.cos( a ), math.sin( a )
        x = half_x * math.copysign( abs( c ) ** ( 2 / e ), c )
        n = half_n * math.copysign( abs( s ) ** ( 2 / e ), s )
        g = np.array( ( math.copysign( abs( x / half_x ) ** ( e - 1 ), x ) / half_x,
                        math.copysign( abs( n / half_n ) ** ( e - 1 ), n ) / half_n ) )
        out.append( ( x, n, g / max( np.linalg.norm( g ), 1e-9 ) ) )
    return out


def armrest( model, F, c, seat, paint, backrest ):
    """ The middle armrest at x 0. c: the bench's footprint centring (railhead_props.bench's); seat: the slats' top;
    backrest: ( y, z, tilt ): the backrest's front face runs up from ( y, z ), leaning back by tilt (radians). """
    import railhead_buffer as B
    import railhead_props as P
    by, bz, tilt = backrest
    foot_y = 6.85 + c
    # The foot plate on the front slat's flat top (the slat runs 4.75..8.5 forward of c, eased 0.28 at its edges).
    B.bevel_box( model, F, ( -1.45, 5.4 + c, seat - 0.02 ), ( 1.45, 8.15 + c, seat + 0.2 ), paint, 0.08 )
    # Where it meets the backrest: 0.7 into the slat (1.2 thick) at seat + 6.7, out of sight inside it.
    z_end = seat + 6.7
    y_end = by - math.sin( tilt ) * ( z_end - bz ) / math.cos( tilt ) - 0.7 / math.cos( tilt )
    path = _spline( [ ( foot_y, seat + 0.05 ), ( foot_y + 0.08, seat + 2.6 ), ( foot_y - 0.1, seat + 5.1 ),
                      ( foot_y - 0.85, seat + 7.25 ), ( foot_y - 2.6, seat + 8.55 ), ( foot_y - 5.3, seat + 9.0 ),
                      ( foot_y - 8.6, seat + 8.85 ), ( foot_y - 11.8, seat + 8.25 ), ( foot_y - 14.3, seat + 7.45 ),
                      ( ( foot_y - 14.3 + y_end ) / 2, ( seat + 7.45 + z_end ) / 2 + 0.1 ), ( y_end, z_end ) ],
                    ARM_SAMPLES )
    lengths = [ 0.0 ]
    for p, q in zip( path, path[1:] ):
        lengths.append( lengths[-1] + float( np.linalg.norm( q - p ) ) )
    total = lengths[-1]
    rings = []
    for k, ( p, along ) in enumerate( zip( path, lengths ) ):
        tangent = path[min( k + 1, len( path ) - 1 )] - path[max( k - 1, 0 )]
        tangent = tangent / np.linalg.norm( tangent )
        out = np.array( ( -tangent[1], tangent[0] ) )          # in the bench's ( y, z ) plane, across the path
        u = along / total
        flare = max( 0.0, 1.0 - along / 1.3 ) ** 2              # into the foot
        grip = _smooth( 0.28, 0.45, u ) * ( 1.0 - _smooth( 0.78, 0.92, u ) )   # the hand rest over the top
        half_x = 0.72 + 0.24 * grip + 0.42 * flare
        half_n = 0.6 - 0.07 * grip + 0.36 * flare
        ring = []
        for x, n, g in _section( half_x, half_n ):
            yz = p + out * n
            normal = ( g[0], float( out[0] * g[1] ), float( out[1] * g[1] ) )
            ring.append( ( ( x, float( yz[0] ), float( yz[1] ) ), normal ) )
        rings.append( ring )
    for ra, rb in zip( rings, rings[1:] ):
        for k in range( ARM_SIDES ):
            j = ( k + 1 ) % ARM_SIDES
            corners = [ ra[k], rb[k], rb[j], ra[j] ]
            towards = np.sum( [ n for _, n in corners ], axis=0 )
            P._fpoly( model, F, paint, [ q for q, _ in corners ], tuple( towards ), normals=[ n for _, n in corners ] )
    # The end in the backrest, capped though it's out of sight.
    end = path[-1] - path[-2]
    P._fpoly( model, F, paint, [ q for q, _ in rings[-1] ], ( 0.0, float( end[0] ), float( end[1] ) ) )
