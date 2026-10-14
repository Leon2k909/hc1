"""
Riverdale's pieces: what Tools/riverdale_map.py builds the plant from, on map_kit's Model (plan coordinates: e east,
n north, z up, inches).

- Pipes are polylines swept round with bends at their corners (bend radius 1.5 x the pipe's), shaded smooth.
- Railings are posts, two rails and a kick plate, drawn only; each run adds player clips (CLIPS) the scene builds, so
  nobody walks or jumps through them and bullets pass.
- Stairs are steps drawn over one wedge hull, the same slope the navmesh walks.
- Lettering, the logo and signs are quads on rv_letters_* / rv_plates, sized by their atlas region's shape.
- Light fixtures draw a housing and a lit lens and add a point light to LIGHTS, which the scene builds.
"""
import math

import numpy as np

import map_kit as K
import riverdale_materials as RM

METAL, STONE, SHEET, WOOD, PLASTIC = "metal", "default", "metal.sheet", "wood", "plastic"
UP = np.array( ( 0.0, 0.0, 1.0 ) )

CLIPS = []      # ( name, centre (plan), yaw degrees, ( length, thickness, height ) ): player clips
LIGHTS = []     # ( name, position (plan), "r,g,b,1", radius, shadows )

WARM = "1.00,0.74,0.46,1"
WARM_DIM = "0.80,0.58,0.36,1"
COOL = "0.72,0.82,0.95,1"
CYAN = "0.20,0.82,1.00,1"
RED = "1.00,0.12,0.08,1"


def reset():
    CLIPS.clear()
    LIGHTS.clear()


def v( *p ):
    return np.asarray( p, float )


def unit( a ):
    a = np.asarray( a, float )
    n = np.linalg.norm( a )
    return a / n if n > 1e-12 else a


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


def box( m, e0, e1, n0, n1, z0, z1, paints, surface=None, skip=() ):
    m.box( ( e0, n0, z0 ), ( e1, n1, z1 ), paints, surface, skip )


def obox( m, centre, right, size, paints, surface=None ):
    """ A box turned in plan: right is its own x (level), size ( along x, along y, up ). """
    right = unit( ( right[0], right[1], 0.0 ) )
    side = np.cross( UP, right )
    m.oriented_box( centre, ( right, side, UP ), size, paints, surface )


def perp( axis ):
    axis = unit( axis )
    side = np.cross( axis, UP )
    if np.linalg.norm( side ) < 1e-6:
        side = np.array( ( 1.0, 0.0, 0.0 ) )
    side = unit( side )
    return side, np.cross( side, axis )


def rod( m, a, b, r, paint, sides=8, caps=False ):
    a, b = v( *a ), v( *b )
    axis = b - a
    if np.linalg.norm( axis ) < 1e-6:
        return
    u, w = perp( axis )
    dirs = [ u * math.cos( 2 * math.pi * k / sides ) + w * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
    for k in range( sides ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % sides]
        card( m, paint, [ a + d0 * r, a + d1 * r, b + d1 * r, b + d0 * r ], d0 + d1, normals=[ d0, d1, d1, d0 ] )
    if caps:
        card( m, paint, [ b + d * r for d in dirs ], axis )
        card( m, paint, [ a + d * r for d in dirs ], -axis )


def _bend_path( pts, radius, steps=4 ):
    """ The polyline with each corner replaced by an arc of this radius (clipped to half each leg). """
    pts = [ v( *p ) for p in pts ]
    if len( pts ) < 3:
        return pts
    out = [ pts[0] ]
    for k in range( 1, len( pts ) - 1 ):
        a, b, c = pts[k - 1], pts[k], pts[k + 1]
        d0, d1 = unit( b - a ), unit( c - b )
        cos = float( np.clip( np.dot( d0, d1 ), -1, 1 ) )
        if cos > 0.9995:
            out.append( b )
            continue
        theta = math.acos( cos )
        t = min( radius * math.tan( theta / 2 ), np.linalg.norm( b - a ) / 2, np.linalg.norm( c - b ) / 2 )
        p0, p1 = b - d0 * t, b + d1 * t
        for s in range( steps + 1 ):
            f = s / steps
            # A quadratic Bezier through the corner is close enough to the arc for a pipe's bend.
            q = ( 1 - f ) ** 2 * p0 + 2 * ( 1 - f ) * f * b + f * f * p1
            out.append( q )
    out.append( pts[-1] )
    return out


def pipe( m, pts, r, paint="rv_pipe", sides=10, caps=True, bend=1.5, flanges=() ):
    """ A pipe along the polyline pts, bent round its corners, shaded smooth. flanges: indices of points where a flange
    ring sits (0 and -1 for its ends). """
    path = _bend_path( pts, r * bend )
    if len( path ) < 2:
        return
    tangents = []
    for k in range( len( path ) ):
        a = path[max( 0, k - 1 )]
        b = path[min( len( path ) - 1, k + 1 )]
        tangents.append( unit( b - a ) )
    u, _ = perp( tangents[0] )
    frames = []
    for t in tangents:
        u = unit( u - np.dot( u, t ) * t )
        if np.linalg.norm( u ) < 1e-6:
            u, _ = perp( t )
        frames.append( ( u, np.cross( t, u ) ) )
    rings = []
    for p, ( u, w ) in zip( path, frames ):
        dirs = [ u * math.cos( 2 * math.pi * k / sides ) + w * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
        rings.append( ( p, dirs ) )
    for ( pa, da ), ( pb, db ) in zip( rings, rings[1:] ):
        if np.linalg.norm( pb - pa ) < 1e-6:
            continue
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            card( m, paint, [ pa + da[k] * r, pa + da[k1] * r, pb + db[k1] * r, pb + db[k] * r ], da[k] + da[k1] + db[k] + db[k1],
                  normals=[ da[k], da[k1], db[k1], db[k] ] )
    if caps:
        p, d = rings[0]
        card( m, paint, [ p + x * r for x in d ], -tangents[0] )
        p, d = rings[-1]
        card( m, paint, [ p + x * r for x in d ], tangents[-1] )
    raw = [ v( *p ) for p in pts ]
    for i in flanges:
        i = i if i >= 0 else len( raw ) + i
        a = raw[i]
        t = unit( raw[min( i + 1, len( raw ) - 1 )] - raw[max( i - 1, 0 )] )
        disc_ring( m, a - t * 1.0, a + t * 1.0, r * 1.35, paint, sides )


def disc_ring( m, a, b, r, paint, sides=10 ):
    rod( m, a, b, r, paint, sides, caps=True )


def cylinder( m, c, r, z0, z1, paint, sides=16, top=None, bottom=None, surface=None, collide="hull" ):
    """ An upright cylinder shaded smooth round its side; top and bottom paints (None for open). """
    c = v( c[0], c[1], 0.0 )
    dirs = [ v( math.cos( 2 * math.pi * k / sides ), math.sin( 2 * math.pi * k / sides ), 0.0 ) for k in range( sides ) ]
    for k in range( sides ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % sides]
        a0, a1 = c + d0 * r, c + d1 * r
        card( m, paint, [ a0 + UP * z0, a1 + UP * z0, a1 + UP * z1, a0 + UP * z1 ], d0 + d1, normals=[ d0, d1, d1, d0 ] )
    if top:
        card( m, top, [ c + d * r + UP * z1 for d in dirs ], UP )
    if bottom:
        card( m, bottom, [ c + d * r + UP * z0 for d in dirs ], -UP )
    if surface:
        pts = [ c + d * r + UP * z for d in dirs for z in ( z0, z1 ) ]
        if collide == "hull":
            m.hull( pts, surface )
        elif collide == "box":
            m.collision_box( c + v( -r, -r, z0 ), c + v( r, r, z1 ), surface )


def lathe( m, c, profile, paints, sides=20, cap=None, surface=None ):
    """ A round thing turned about the vertical through c: profile [ ( radius, z ) ] upwards; paints one or per band. """
    c = v( c[0], c[1], 0.0 )
    dirs = [ v( math.cos( 2 * math.pi * k / sides ), math.sin( 2 * math.pi * k / sides ), 0.0 ) for k in range( sides ) ]
    for j in range( len( profile ) - 1 ):
        paint = paints[j] if isinstance( paints, ( list, tuple ) ) else paints
        if paint is None:
            continue
        ( r0, z0 ), ( r1, z1 ) = profile[j], profile[j + 1]
        slope = unit( ( z1 - z0, r0 - r1 ) )
        if np.linalg.norm( slope ) < 1e-9:
            continue
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            pts = [ c + dirs[k] * r0 + UP * z0, c + dirs[k1] * r0 + UP * z0, c + dirs[k1] * r1 + UP * z1, c + dirs[k] * r1 + UP * z1 ]
            nrm = [ dirs[i] * slope[0] + UP * slope[1] for i in ( k, k1, k1, k ) ]
            if r0 < 1e-6 and r1 < 1e-6:
                continue
            if r0 < 1e-6:
                pts, nrm = pts[1:], nrm[1:]
            elif r1 < 1e-6:
                pts, nrm = pts[:3], nrm[:3]
            card( m, paint, pts, sum( nrm ), normals=nrm )
    if cap and profile[-1][0] > 1e-6:
        r, z = profile[-1]
        card( m, cap, [ c + d * r + UP * z for d in dirs ], UP )
    if surface:
        pts = [ c + d * r + UP * z for r, z in profile for d in dirs ]
        m.hull( pts, surface )


# ---------------------------------------------------------------------------------------------------------------------
# Railings and stairs

def clip( name, a, b, z0, z1, thick=4.0 ):
    """ A player clip along a railing from a to b (plan), z0 up to z1. """
    a, b = v( a[0], a[1], 0 ), v( b[0], b[1], 0 )
    L = float( np.linalg.norm( b - a ) )
    if L < 1:
        return
    mid = ( a + b ) / 2
    yaw = math.degrees( math.atan2( b[1] - a[1], b[0] - a[0] ) )
    CLIPS.append( ( name, ( float( mid[0] ), float( mid[1] ), ( z0 + z1 ) / 2 ), yaw, ( L, thick, z1 - z0 ) ) )


def railing( m, pts, z, paint="rv_yellow", height=42.0, post_every=60.0, kick=True, clip_to=None, closed=False, name="rail",
             posts=True, slope=None ):
    """ A guard rail along plan pts at floor height z (or slope: a z per point, for stairs): square posts, a top rail and
    a mid rail, a kick plate. clip_to: the clip's top (None for none). """
    pts = [ v( p[0], p[1], 0.0 ) for p in pts ]
    if closed:
        pts = pts + [ pts[0] ]
    zs = slope if slope is not None else [ z ] * len( pts )
    if closed and slope is None:
        zs = zs + [ z ]
    for k in range( len( pts ) - 1 ):
        a, b = pts[k], pts[k + 1]
        za, zb = zs[k], zs[k + 1]
        d = b - a
        L = float( np.linalg.norm( d ) )
        if L < 1:
            continue
        A, B = a + UP * za, b + UP * zb
        rod( m, A + UP * height, B + UP * height, 0.95, paint, 8 )
        rod( m, A + UP * height * 0.5, B + UP * height * 0.5, 0.8, paint, 6 )
        if kick:
            side = unit( np.cross( UP, d ) ) * 0.12
            card( m, paint, [ A + side, B + side, B + side + UP * 4, A + side + UP * 4 ], side, both=True )
        if posts:
            count = max( 1, int( math.ceil( L / post_every ) ) )
            for i in range( count + ( 1 if k == len( pts ) - 2 and not closed else 0 ) ):
                f = i / count
                p = a + d * f
                zp = za + ( zb - za ) * f
                box( m, p[0] - 1.0, p[0] + 1.0, p[1] - 1.0, p[1] + 1.0, zp, zp + height, paint )
        if clip_to is not None:
            clip( name, a, b, min( za, zb ), max( za, zb ) + clip_to )


def stairs( m, foot, head, width, z0, z1, tread="rv_grating", side="rv_yellow", rails=( True, True ), rail_paint="rv_yellow",
            surface=METAL, solid_under=False, under_paint="rv_plinth", name="stair" ):
    """ A straight flight from foot (plan, its bottom nosing's centre) to head (the top nosing's centre), width across:
    steps of about 7.5 in, steel strings each side, hand rails. One wedge hull carries walking. """
    foot, head = v( foot[0], foot[1], 0 ), v( head[0], head[1], 0 )
    along = head - foot
    run = float( np.linalg.norm( along ) )
    d = along / run
    s = np.cross( UP, d ) * ( width / 2 )
    steps = max( 2, int( round( ( z1 - z0 ) / 7.5 ) ) )
    rise, going = ( z1 - z0 ) / steps, run / steps
    for i in range( steps ):
        p = foot + d * ( going * i )
        q = p + d * going
        zt = z0 + rise * ( i + 1 )
        top = [ p - s + UP * zt, q - s + UP * zt, q + s + UP * zt, p + s + UP * zt ]
        card( m, tread, top, UP )
        card( m, tread, [ x - UP * 1.5 for x in top ], -UP )
        card( m, side, [ p - s + UP * ( zt - 1.5 ), p + s + UP * ( zt - 1.5 ), p + s + UP * zt, p - s + UP * zt ], -d )
        if solid_under:
            card( m, under_paint, [ p - s + UP * ( zt - rise ), p + s + UP * ( zt - rise ), p + s + UP * ( zt - 1.5 ), p - s + UP * ( zt - 1.5 ) ], -d )
    # Strings: plates under each side from the foot to the head.
    for sgn in ( -1, 1 ):
        o = s * sgn * 1.02
        bot0, bot1 = foot + o + UP * ( z0 - 0 ), head + o + UP * ( z1 - 10 )
        top0, top1 = foot + o + UP * ( z0 + rise + 3 ), head + o + UP * ( z1 + 3 )
        if solid_under:
            card( m, under_paint, [ foot + o + UP * z0, head + o + UP * z0, head + o + UP * ( z1 + 3 ), foot + o + UP * ( z0 + rise + 3 ) ], o, both=False )
        else:
            card( m, side, [ bot0, bot1, top1, top0 ], o, both=True )
    if solid_under:
        card( m, under_paint, [ head - s + UP * z0, head + s + UP * z0, head + s + UP * z1, head - s + UP * z1 ], d )
    # Rails.
    for sgn, want in zip( ( -1, 1 ), rails ):
        if not want:
            continue
        o = s * sgn * 0.98
        rp = [ foot + o, head + o ]
        railing( m, rp, 0, rail_paint, height=36.0, post_every=48.0, kick=False, slope=[ z0 + rise, z1 ], clip_to=48, name=f"{name} rail" )
    # Collision: a wedge from the foot's nosing (at z0) to the head (z1), solid down to z0.
    lo = [ foot - s - d * 2 + UP * z0, foot + s - d * 2 + UP * z0, head - s + UP * z0, head + s + UP * z0 ]
    hi = [ head - s + d * 1 + UP * z1, head + s + d * 1 + UP * z1, foot - s - d * 2 + UP * ( z0 + 0.5 ), foot + s - d * 2 + UP * ( z0 + 0.5 ) ]
    m.hull( lo + hi + [ head - s + d + UP * z0, head + s + d + UP * z0 ], surface )
    return rise


# ---------------------------------------------------------------------------------------------------------------------
# Props

def tank( m, c, r, h, paint="rv_white", z0=0.0, sides=24, rings=True, ladder=True, letters_name=None, facing=None,
          surface=METAL ):
    """ An upright tank: a cylinder on a plinth with a dished head, girth seams, a ladder and a nozzle. """
    cylinder( m, c, r + 4, z0, z0 + 8, "rv_plinth", sides, top="rv_plinth" )
    cylinder( m, c, r, z0 + 8, z0 + h, paint, sides, surface=surface )
    head = [ ( r, z0 + h ), ( r * 0.92, z0 + h + r * 0.12 ), ( r * 0.62, z0 + h + r * 0.22 ), ( r * 0.25, z0 + h + r * 0.27 ), ( 0.0, z0 + h + r * 0.28 ) ]
    lathe( m, c, head, paint, sides )
    if rings:
        for zz in np.arange( z0 + 8 + 72, z0 + h - 10, 72 ):
            cylinder( m, c, r + 0.6, zz, zz + 1.2, "rv_steel", sides )
    if ladder:
        d = unit( facing if facing is not None else ( 1, 0 ) )
        d = v( d[0], d[1], 0 )
        sd = np.cross( UP, d )
        base = v( c[0], c[1], 0 ) + d * ( r + 7 )
        for sg in ( -1, 1 ):
            rod( m, base + sd * 9 * sg + UP * ( z0 + 8 ), base + sd * 9 * sg + UP * ( z0 + h + r * 0.15 ), 0.8, "rv_steel", 6 )
        for zz in np.arange( z0 + 20, z0 + h, 12 ):
            rod( m, base - sd * 9 + UP * zz, base + sd * 9 + UP * zz, 0.5, "rv_steel", 5 )
        for zz in np.arange( z0 + 90, z0 + h, 40 ):
            # The cage's hoops.
            for k in range( 6 ):
                a0, a1 = math.pi * k / 6, math.pi * ( k + 1 ) / 6
                p0 = base + d * ( 14 * math.sin( a0 ) ) + sd * ( -14 * math.cos( a0 ) ) + UP * zz
                p1 = base + d * ( 14 * math.sin( a1 ) ) + sd * ( -14 * math.cos( a1 ) ) + UP * zz
                rod( m, p0, p1, 0.4, "rv_steel", 4 )
    if letters_name and facing is not None:
        f = unit( facing )
        out = v( f[0], f[1], 0 )
        right = np.cross( UP, out )
        rot = math.radians( 35 )
        out2 = unit( out * math.cos( rot ) + right * math.sin( rot ) )
        centre = v( c[0], c[1], 0 ) + out2 * ( r + 0.3 ) + UP * ( z0 + h * 0.55 )
        letters( m, letters_name, centre, np.cross( UP, out2 ), r * 1.0, "dark" )


def jersey( m, centre, along, length=118.0, paint="rv_plinth", surface=STONE ):
    """ A precast concrete barrier: the F-shape, 32 in tall, 24 in at the foot and 9.5 at the top. """
    along = unit( ( along[0], along[1], 0.0 ) )
    side = np.cross( UP, along )
    c = v( centre[0], centre[1], 0.0 )
    prof = [ ( 12.0, 0.0 ), ( 12.0, 3.0 ), ( 8.5, 10.0 ), ( 4.75, 32.0 ) ]
    full = prof + [ ( -x, z ) for x, z in reversed( prof ) ]
    half = length / 2
    a, b = c - along * half, c + along * half
    for k in range( len( full ) - 1 ):
        ( x0, z0 ), ( x1, z1 ) = full[k], full[k + 1]
        p0, p1 = side * x0 + UP * z0, side * x1 + UP * z1
        n = unit( np.cross( p1 - p0, along ) )
        if np.dot( n, ( p0 + p1 ) / 2 - UP * 16 ) < 0:
            n = -n
        card( m, paint, [ a + p0, b + p0, b + p1, a + p1 ], n )
    for end, sg in ( ( a, -1 ), ( b, 1 ) ):
        card( m, paint, [ end + side * x + UP * z for x, z in full ], along * sg )
    pts = [ a + side * x + UP * z for x, z in full ] + [ b + side * x + UP * z for x, z in full ]
    m.hull( pts, surface )


def case( m, c, size, along=( 1, 0 ), paint="rv_olive", z0=0.0, surface=PLASTIC, lid_open=False ):
    """ A moulded equipment case: body, a lid seam band, latches and handles, corner bumpers. size ( L, W, H ). """
    along = unit( ( along[0], along[1], 0.0 ) )
    side = np.cross( UP, along )
    L, W, H = size
    centre = v( c[0], c[1], z0 + H / 2 )
    obox( m, centre, along, ( L, W, H ), { "default": paint, "-z": None }, surface )
    seam = H * 0.72
    for sgn in ( -1, 1 ):
        p = v( c[0], c[1], 0 ) + side * ( W / 2 + 0.25 ) * sgn
        card( m, "rv_dark", [ p - along * L / 2 + UP * ( z0 + seam - 0.5 ), p + along * L / 2 + UP * ( z0 + seam - 0.5 ),
                              p + along * L / 2 + UP * ( z0 + seam + 0.5 ), p - along * L / 2 + UP * ( z0 + seam + 0.5 ) ], side * sgn )
        for f in ( -0.3, 0.3 ):
            q = p + along * L * f + side * 0.4 * sgn
            obox( m, q + UP * ( z0 + seam ), along, ( 3.2, 1.2, 4.0 ), "rv_dark" )
        h = p + side * 1.2 * sgn
        rod( m, h - along * 4 + UP * ( z0 + H * 0.45 ), h + along * 4 + UP * ( z0 + H * 0.45 ), 0.6, "rv_dark", 6 )
    for sgn in ( -1, 1 ):
        p = v( c[0], c[1], 0 ) + along * ( L / 2 + 0.25 ) * sgn
        rod( m, p - side * 3 + UP * ( z0 + H * 0.55 ), p + side * 3 + UP * ( z0 + H * 0.55 ), 0.6, "rv_dark", 6 )
    for sa in ( -1, 1 ):
        for sb in ( -1, 1 ):
            q = v( c[0], c[1], 0 ) + along * ( L / 2 - 1.5 ) * sa + side * ( W / 2 - 1.5 ) * sb
            obox( m, q + UP * ( z0 + 1.5 ), along, ( 3.4, 3.4, 3.0 ), "rv_black" )
            obox( m, q + UP * ( z0 + H - 1.5 ), along, ( 3.4, 3.4, 3.0 ), "rv_black" )


def case_stack( m, c, along, kind="olive", seed=0 ):
    """ Two or three cases stacked, slightly askew. Returns the stack's height. """
    rng = np.random.default_rng( seed )
    along = unit( ( along[0], along[1], 0 ) )
    z = 0.0
    paint = "rv_olive" if kind == "olive" else "rv_case"
    sizes = [ ( 48, 30, 26 ), ( 44, 28, 22 ), ( 36, 24, 18 ) ]
    count = int( rng.integers( 1, 4 ) )
    for i in range( count ):
        L, W, H = sizes[min( i, 2 )]
        yaw = rng.normal( 0, 0.06 )
        a = v( along[0] * math.cos( yaw ) - along[1] * math.sin( yaw ), along[0] * math.sin( yaw ) + along[1] * math.cos( yaw ), 0 )
        off = rng.normal( 0, 1.5, 2 )
        case( m, ( c[0] + off[0], c[1] + off[1] ), ( L, W, H ), a, paint, z )
        z += H
    return z


def quad( m, paint, centre, right, up, w, h, uv=None, off=0.0 ):
    right, up = unit( right ), unit( up )
    out = np.cross( right, up )
    c = v( *centre ) + out * off
    pts = [ c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2 ]
    m.polygon( paint, pts, normal=out, uv=uv )


def letters( m, name, centre, right, h, tone="dark", up=UP, off=0.4 ):
    """ Lettering or the logo from rv_letters' atlas, h tall, on the face whose right is right (it faces cross( right,
    up )). """
    a = RM.aspect( RM.LETTERS, name )
    uv = [ RM.atlas_uv( RM.LETTERS, RM.LETTER_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    quad( m, f"rv_letters_{tone}", centre, right, up, h * a, h, uv, off )


def plate( m, name, centre, right, h, up=UP, off=0.3, back=None ):
    a = RM.aspect( RM.PLATES, name )
    uv = [ RM.atlas_uv( RM.PLATES, RM.PLATE_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    quad( m, "rv_plates", centre, right, up, h * a, h, uv, off )
    if back:
        right_, up_ = unit( right ), unit( up )
        quad( m, back, centre, -right_, up_, h * a, h, None, off - 0.1 )


def screen( m, name, centre, right, h, up=UP, off=0.2 ):
    a = RM.aspect( RM.SCREENS, name )
    uv = [ RM.atlas_uv( RM.SCREENS, RM.SCREEN_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    quad( m, "rv_screens", centre, right, up, h * a, h, uv, off )


def wall_light( m, name, at, out, kind="warm", radius=320, shadows=False, light=True, size=( 20, 7, 5 ) ):
    """ A wall pack on a wall facing out (plan): a dark housing, its lens on the underside and front lit, and a point
    light a little out from it. """
    out = unit( ( out[0], out[1], 0.0 ) )
    right = np.cross( UP, out )
    L, D, H = size
    c = v( *at ) + out * ( D / 2 )
    obox( m, c, right, ( L, D, H ), "rv_dark" )
    lens = { "warm": "rv_lamp_warm", "cool": "rv_lamp_cool", "cyan": "rv_lamp_cyan", "red": "rv_beacon" }[kind]
    p = c - UP * ( H / 2 + 0.05 )
    card( m, lens, [ p - right * ( L / 2 - 1 ) - out * ( D / 2 - 1 ), p + right * ( L / 2 - 1 ) - out * ( D / 2 - 1 ),
                     p + right * ( L / 2 - 1 ) + out * ( D / 2 - 0.5 ), p - right * ( L / 2 - 1 ) + out * ( D / 2 - 0.5 ) ], -UP )
    f = c + out * ( D / 2 + 0.05 )
    card( m, lens, [ f - right * ( L / 2 - 1 ) - UP * ( H / 2 - 1 ), f + right * ( L / 2 - 1 ) - UP * ( H / 2 - 1 ),
                     f + right * ( L / 2 - 1 ) - UP * ( H / 2 - 2.5 ), f - right * ( L / 2 - 1 ) - UP * ( H / 2 - 2.5 ) ], out )
    if light:
        colour = { "warm": WARM, "cool": COOL, "cyan": CYAN, "red": RED }[kind]
        LIGHTS.append( ( name, tuple( c + out * 14 - UP * 10 ), colour, radius, shadows ) )


def ceiling_light( m, name, at, along=( 1, 0 ), kind="cool", radius=900, shadows=False, size=( 48, 10, 4 ), light=True ):
    """ A high-bay batten hanging under a ceiling: housing and a lit underside. """
    along = unit( ( along[0], along[1], 0 ) )
    side = np.cross( UP, along )
    c = v( *at )
    L, W, H = size
    obox( m, c, along, ( L, W, H ), "rv_dark" )
    lens = "rv_lamp_cool" if kind == "cool" else "rv_lamp_warm"
    p = c - UP * ( H / 2 + 0.05 )
    card( m, lens, [ p - along * ( L / 2 - 1.5 ) - side * ( W / 2 - 1.5 ), p + along * ( L / 2 - 1.5 ) - side * ( W / 2 - 1.5 ),
                     p + along * ( L / 2 - 1.5 ) + side * ( W / 2 - 1.5 ), p - along * ( L / 2 - 1.5 ) + side * ( W / 2 - 1.5 ) ], -UP )
    if light:
        LIGHTS.append( ( name, tuple( c - UP * 30 ), COOL if kind == "cool" else WARM, radius, shadows ) )


def beacon( m, name, at, light=True ):
    c = v( *at )
    cylinder( m, c, 2.6, c[2], c[2] + 2, "rv_dark", 8, top=None )
    lathe( m, c, [ ( 2.2, c[2] + 2 ), ( 2.2, c[2] + 5 ), ( 1.4, c[2] + 6.5 ), ( 0.0, c[2] + 7 ) ], "rv_beacon", 10 )
    if light:
        LIGHTS.append( ( name, tuple( c + UP * 8 ), RED, 90, False ) )


def louvre( m, centre, right, w, h, depth=6.0, blades=None, frame="rv_frame", blade="rv_louvre" ):
    """ A louvred vent set into a wall face: a frame and slanted blades in front of a dark void. """
    right = unit( right )
    out = np.cross( right, UP )
    c = v( *centre )
    quad( m, "rv_black", c - out * depth, right, UP, w, h )
    for sg in ( -1, 1 ):
        p = c + right * ( w / 2 ) * sg
        card( m, frame, [ p - UP * h / 2, p - UP * h / 2 - out * depth, p + UP * h / 2 - out * depth, p + UP * h / 2 ], -right * sg )
        p = c + UP * ( h / 2 ) * sg
        card( m, frame, [ p - right * w / 2, p - right * w / 2 - out * depth, p + right * w / 2 - out * depth, p + right * w / 2 ], -UP * sg )
    n = blades or max( 4, int( h / 4.5 ) )
    pitch = h / n
    for i in range( n ):
        zc = -h / 2 + pitch * ( i + 0.5 )
        top = c + UP * ( zc + pitch * 0.55 ) - out * 1.0
        bot = c + UP * ( zc - pitch * 0.45 ) + out * 0.2 - out * ( depth * 0.5 )
        card( m, blade, [ bot - right * w / 2, bot + right * w / 2, top + right * w / 2, top - right * w / 2 ], out + UP * 0.6 )
    # Frame face.
    t = 2.5
    for sg in ( -1, 1 ):
        quad( m, frame, c + right * ( w / 2 + t / 2 ) * sg, right, UP, t, h + 2 * t, off=0.3 )
        quad( m, frame, c + UP * ( h / 2 + t / 2 ) * sg, right, UP, w, t, off=0.3 )


def door( m, centre, right, w=96.0, h=96.0, paint="rv_door", frame="rv_frame", window=True, double=True, recess=4.0 ):
    """ A steel door (double or single) set back in its opening, centre at its foot. Drawn only. """
    right = unit( right )
    out = np.cross( right, UP )
    c = v( *centre ) - out * recess
    leaves = 2 if double else 1
    lw = w / leaves
    for i in range( leaves ):
        lc = c + right * ( -w / 2 + lw * ( i + 0.5 ) ) + UP * ( h / 2 )
        quad( m, paint, lc, right, UP, lw - 0.6, h - 0.6 )
        if window:
            quad( m, "rv_window_dark", lc + UP * h * 0.22 + out * 0.15, right, UP, lw * 0.36, h * 0.24 )
        push = lc - UP * h * 0.02 + right * ( lw * 0.32 * ( 1 if i == 0 and double else -1 ) ) + out * 0.8
        obox( m, push, right, ( 1.2, 1.4, 10.0 ), "rv_zinc" )
    for sg in ( -1, 1 ):
        quad( m, frame, c + right * ( w / 2 + 1.5 ) * sg + UP * ( h / 2 ), right, UP, 3.0, h, off=0.2 )
    quad( m, frame, c + UP * ( h + 1.5 ), right, UP, w + 6, 3.0, off=0.2 )
    # Reveals back to the wall face.
    for sg in ( -1, 1 ):
        p = c + right * ( w / 2 + 3 ) * sg
        card( m, "rv_plinth", [ p, p + out * recess, p + out * recess + UP * ( h + 3 ), p + UP * ( h + 3 ) ], -right * sg )
    p = c + UP * ( h + 3 )
    card( m, "rv_plinth", [ p - right * ( w / 2 + 3 ), p + right * ( w / 2 + 3 ), p + right * ( w / 2 + 3 ) + out * recess, p - right * ( w / 2 + 3 ) + out * recess ], -UP )


def bollard( m, e, n, h=40.0 ):
    cylinder( m, ( e, n ), 3.5, 0, h, "rv_yellow", 10, top="rv_yellow", surface=METAL )
    for zz in ( h - 10, h - 6 ):
        cylinder( m, ( e, n ), 3.6, zz, zz + 1.5, "rv_black", 10 )


def life_ring( m, at, out ):
    """ A life ring in its holder on a wall facing out. """
    out = unit( ( out[0], out[1], 0 ) )
    right = np.cross( UP, out )
    c = v( *at ) + out * 3
    R, r = 11.0, 2.4
    n = 16
    for k in range( n ):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * ( k + 1 ) / n
        paint = "rv_ring_orange" if ( k // 2 ) % 2 == 0 else "rv_ring_white"
        p0 = c + ( right * math.cos( a0 ) + UP * math.sin( a0 ) ) * R
        p1 = c + ( right * math.cos( a1 ) + UP * math.sin( a1 ) ) * R
        rod( m, p0, p1, r, paint, 6 )
    obox( m, c - out * 2 + UP * 12, right, ( 6, 3, 3 ), "rv_frame" )


def truss( m, a, b, depth, paint="rv_steel", chord=3.0, web=1.5, up=UP, panel=None ):
    """ A flat Warren truss from a to b, depth in direction up: two chords and zig-zag webs. Drawn only. """
    a, b = v( *a ), v( *b )
    up = unit( up )
    L = float( np.linalg.norm( b - a ) )
    d = ( b - a ) / L
    m.beam( a, b, ( chord * 2, chord * 2 ), paint )
    m.beam( a + up * depth, b + up * depth, ( chord * 2, chord * 2 ), paint )
    p = panel or depth
    count = max( 1, int( round( L / p ) ) )
    for i in range( count ):
        p0 = a + d * ( L * i / count )
        p1 = a + d * ( L * ( i + 0.5 ) / count ) + up * depth
        p2 = a + d * ( L * ( i + 1 ) / count )
        m.beam( p0, p1, ( web * 2, web * 2 ), paint )
        m.beam( p1, p2, ( web * 2, web * 2 ), paint )


def i_beam( m, a, b, h, w, paint="rv_steel", web=0.8, flange=1.0, surface=None ):
    """ An I-section from a to b (level or not), h deep (vertical when level), w wide. """
    a, b = v( *a ), v( *b )
    d = unit( b - a )
    side = unit( np.cross( UP, d ) ) if abs( d[2] ) < 0.99 else v( 1, 0, 0 )
    upv = np.cross( d, side )
    L = float( np.linalg.norm( b - a ) )
    mid = ( a + b ) / 2
    m.oriented_box( mid, ( d, side, upv ), ( L, web, h - 2 * flange ), paint, surface )
    m.oriented_box( mid + upv * ( h / 2 - flange / 2 ), ( d, side, upv ), ( L, w, flange ), paint )
    m.oriented_box( mid - upv * ( h / 2 - flange / 2 ), ( d, side, upv ), ( L, w, flange ), paint )


def cable_tray( m, a, b, w=18.0, paint="rv_zinc" ):
    a, b = v( *a ), v( *b )
    d = unit( b - a )
    side = unit( np.cross( UP, d ) )
    card( m, paint, [ a - side * w / 2, b - side * w / 2, b + side * w / 2, a + side * w / 2 ], UP, both=True )
    for sg in ( -1, 1 ):
        o = side * ( w / 2 ) * sg
        card( m, paint, [ a + o, b + o, b + o + UP * 4, a + o + UP * 4 ], o, both=True )
    # Cables in it.
    for k in range( 4 ):
        o = side * ( -w / 2 + w * ( k + 0.5 ) / 4 )
        rod( m, a + o + UP * 1.2, b + o + UP * 1.2, 1.0, "rv_black", 5 )
