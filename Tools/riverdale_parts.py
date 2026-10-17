"""
Riverdale's pieces: what Tools/riverdale_map.py builds the plant from, on map_kit's Model (plan coordinates: e east,
n north, z up, inches). Tools/orion_map.py, spillway_map.py, riverside_map.py and veridant_map.py use them too, so the
upgraded pieces stick to paints those maps already know (rv_dark, rv_black, rv_zinc, rv_steel, ...); only the new
helpers bring paints of their own (EXTRA_PAINTS, EXTRA_SURFACES).

Every piece is drawn at a real thing's size, its edges eased and shaded the way a real one's are; what it collides with
(map_kit boxes and hulls, and the player clips in CLIPS) is the same simple shape it always was. Detail is drawn only.

Building blocks:
- extrude( a, b, profile ): a section (x across, y up) swept straight from a to b. Short edges (chamfers, fillets) shade
  as the faces either side of them, small angles shade smooth; its ends are cut square or by any plane.
- bevel_box / bobox: a box with its twelve edges chamfered and shaded round (44 triangles).
- tube: a round bar along a polyline, bent round its corners (circular arcs), shaded smooth; lathe_axis: a turned shape
  about any axis; torus.
- _solid / _facing / _depth / _drawn_face: what this model's own collision (or drawn faces) says about a point. Doors and louvres set on a solid wall
  are mounted on its face (they used to be drawn inside it); fixtures and lettering drawn facing into a wall are turned
  round to face out of it.

The pieces:
- Pipes: tubes with bends at their corners (bend radius 1.5 x the pipe's), lap bands on aluminium jacketing (rv_pipe)
  where it meets an elbow and every 60 in on the big ones, weld-neck flange pairs where asked, and on request T shoes under it
  (supports) and gate valves along it (valves).
- Railings: a round top rail and mid rail bent round the corners, round posts on base plates with a fitting under the
  top rail, a kick plate; drawn only. Each run adds player clips (CLIPS) the scene builds, so nobody walks or jumps
  through them and bullets pass.
- Stairs: channel stringers, grating treads with angle nosings (or concrete steps with galvanised nosings and
  an anti-slip strip), drawn over one wedge hull, the same slope the navmesh walks.
- Jersey barriers: the F-shape, precast (rv_precast), chamfered top and ends with chipped arrises, two drain scuppers at
  the foot and two lifting slots through the top.
- Cases: moulded rounded shells, a ribbed base, the lid's seam, black corner bumpers, recessed latches, fold-down end
  handles, an ID card; lid_open opens the lid back on its hinge over the foam.
- Tanks: a plinth, the shell, a torispherical head, stiffening rings, anchor chairs, a manway, nozzles with blind
  flanges, an outlet with a gate valve, a level gauge, a vent and roof nozzle, a caged ladder and a rail on the head.
- Doors: a steel frame, an architrave on the wall face, leaves with a vision lite in a glazing bead, hinges, a lever
  and lock, a kick plate, an overhead closer, a number plate (or an atlas sign), a threshold. In a through opening of
  this model's own wall they stand open, swung in (players walk through those); on a solid wall they're surface mounted.
- Louvres: drainable blades (a drip in front, an upturned back) in a channel frame, mullions on wide ones, bird screen.
- Light fixtures (wall packs, high-bay battens, beacons) add a point light to LIGHTS, which the scene builds. Wall packs
  are die-cast bodies with fins, a sloped lens and a wire guard, fed by a conduit; battens hang on wires from whatever is
  above them in the same model; beacons have a fresnel dome in a wire guard on a base plate.
- Bollards (a domed steel pipe with two reflective bands on an anchored plate), life rings (a torus with its grab line,
  on a hook), Warren trusses of double-angle chords and angle webs on gusset plates, I-sections with root fillets, and
  ladder-type cable trays with rungs and cables.
- Lettering, the logo and signs are quads on rv_letters_* / rv_plates, sized by their atlas region's shape; signs
  (plate) stand off the wall on an aluminium edge.

New helpers (drawn only unless a surface is passed): drum (205 l steel drum), pallet (Euro pallet), cable_reel,
extinguisher (in a cabinet), electrical_box, conduit, ladder, manhole, drain_grate, cone, hose_reel, cctv, sign_post.
"""
import math
import zlib

import numpy as np

import map_kit as K
import riverdale_materials as RM

METAL, STONE, SHEET, WOOD, PLASTIC = "metal", "default", "metal.sheet", "wood", "plastic"
UP = np.array( ( 0.0, 0.0, 1.0 ) )

CLIPS = []      # ( name, centre (plan), yaw degrees, ( length, thickness, height ) ): player clips
LIGHTS = []     # ( name, position (plan), "r,g,b,1", radius, shadows )
PIPE_SOLIDS = []  # ( centre (plan), vector (plan), radius ): static collision for reachable utility pipes

WARM = "1.00,0.74,0.46,1"
WARM_DIM = "0.80,0.58,0.36,1"
COOL = "0.72,0.82,0.95,1"
CYAN = "0.20,0.82,1.00,1"
RED = "1.00,0.12,0.08,1"

# Materials this module brings; riverdale_materials.load_extras merges them. Flat paints: colour (sRGB), metalness,
# roughness, self-illumination.
EXTRA_PAINTS = {
    "rv_red": ( ( 172, 24, 20 ), 0.15, 0.38, 0 ),
    "rv_enclosure": ( ( 196, 198, 192 ), 0.2, 0.45, 0 ),
    "rv_iron": ( ( 46, 44, 42 ), 0.7, 0.55, 0 ),
    "rv_rope": ( ( 214, 202, 160 ), 0.0, 0.85, 0 ),
}
# Textured surfaces: ( tile inches, metalness, fn ), fn() as riverdale_materials.SURFACES' functions.
EXTRA_SURFACES = {
    "rv_precast": ( 64.0, 0.0, lambda: precast_concrete() ),
    "rv_pallet_wood": ( 48.0, 0.0, lambda: pallet_wood() ),
    "rv_drum_blue": ( 48.0, 0.15, lambda: drum_paint( 103, ( 30, 66, 132 ) ) ),
    "rv_drum_red": ( 48.0, 0.15, lambda: drum_paint( 104, ( 150, 34, 26 ) ) ),
}


def reset():
    CLIPS.clear()
    LIGHTS.clear()
    PIPE_SOLIDS.clear()


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
            q = ( 1 - f ) ** 2 * p0 + 2 * ( 1 - f ) * f * b + f * f * p1
            out.append( q )
    out.append( pts[-1] )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Building blocks

def _same( a, b, eps=1e-6 ):
    return float( np.linalg.norm( np.asarray( a, float ) - np.asarray( b, float ) ) ) < eps


def _face( m, paint, pts, nrm=None, uv=None, both=False, towards=None ):
    """ One polygon, coincident points dropped, wound to face towards (else its normals' mean); nrm, one per point,
    shades it smooth where they differ. """
    keep_p, keep_n, keep_uv = [], [], []
    for k, p in enumerate( pts ):
        p = np.asarray( p, float )
        if keep_p and _same( p, keep_p[-1] ):
            continue
        keep_p.append( p )
        keep_n.append( None if nrm is None else np.asarray( nrm[k], float ) )
        keep_uv.append( None if uv is None else uv[k] )
    while len( keep_p ) > 1 and _same( keep_p[0], keep_p[-1] ):
        keep_p.pop()
        keep_n.pop()
        keep_uv.pop()
    if len( keep_p ) < 3:
        return
    if towards is None:
        towards = sum( keep_n )
    smooth = None
    if nrm is not None:
        ref = unit( keep_n[0] )
        if any( float( np.dot( unit( n ), ref ) ) < 0.9998 for n in keep_n ):
            smooth = keep_n
    card( m, paint, keep_p, towards, uv=None if uv is None else keep_uv, both=both, normals=smooth )


def _area2( prof ):
    n = len( prof )
    return sum( prof[k][0] * prof[( k + 1 ) % n][1] - prof[( k + 1 ) % n][0] * prof[k][1] for k in range( n ) ) / 2


def _unit2( a ):
    n = float( np.linalg.norm( a ) )
    return a / n if n > 1e-12 else a


def _edge_normals( prof, closed=True, smooth=30.0, chamfer=0.0 ):
    """ For each edge of a 2D section, its outward normal at its start and at its end. An edge shorter than chamfer takes
    its neighbours' normals at its ends (so it shades as a rounded edge between them); two longer edges meeting at less
    than smooth degrees share their mean there; any other corner is hard. An open section's normals point right of its
    direction. """
    P = [ np.asarray( p, float ) for p in prof ]
    n = len( P )
    ccw = _area2( P ) >= 0 if closed else True
    E = n if closed else n - 1
    flat, length = [], []
    for e in range( E ):
        d = P[( e + 1 ) % n] - P[e]
        L = float( np.linalg.norm( d ) )
        length.append( L )
        if L < 1e-9:
            flat.append( None )
            continue
        nn = np.array( ( d[1], -d[0] ) ) / L
        flat.append( nn if ccw else -nn )
    for e in range( E ):
        if flat[e] is None:
            flat[e] = next( ( f for f in flat if f is not None ), np.array( ( 0.0, 1.0 ) ) )
    cos_s = math.cos( math.radians( smooth ) ) if smooth else 2.0
    small = [ L < chamfer for L in length ]

    def at_end( e, other ):
        if other is None:
            return flat[e]
        if small[e] and not small[other]:
            return flat[other]
        if small[e] and small[other]:
            return _unit2( flat[e] + flat[other] )
        if small[other]:
            return flat[e]
        if float( np.dot( flat[e], flat[other] ) ) > cos_s:
            return _unit2( flat[e] + flat[other] )
        return flat[e]

    out = []
    for e in range( E ):
        prev = ( e - 1 ) % E if ( closed or e > 0 ) else None
        nxt = ( e + 1 ) % E if ( closed or e < E - 1 ) else None
        out.append( ( at_end( e, prev ), at_end( e, nxt ) ) )
    return out


def _convex( poly ):
    n = len( poly )
    sign = 0
    for k in range( n ):
        a, b, c = poly[k - 1], poly[k], poly[( k + 1 ) % n]
        cr = ( b[0] - a[0] ) * ( c[1] - b[1] ) - ( b[1] - a[1] ) * ( c[0] - b[0] )
        if abs( cr ) < 1e-9:
            continue
        s = 1 if cr > 0 else -1
        if sign and s != sign:
            return False
        sign = s
    return True


def _triangulate( poly ):
    """ Ear clipping of a simple polygon (2D points): index triples. """
    pts = [ np.asarray( p, float ) for p in poly ]
    n = len( pts )
    if n < 3:
        return []
    sign = 1.0 if _area2( pts ) >= 0 else -1.0

    def cross( o, a, b ):
        return ( ( a[0] - o[0] ) * ( b[1] - o[1] ) - ( a[1] - o[1] ) * ( b[0] - o[0] ) ) * sign

    idx = list( range( n ) )
    tris = []
    guard = 0
    while len( idx ) > 3 and guard < 4 * n * n:
        guard += 1
        clipped = False
        for i in range( len( idx ) ):
            a, b, c = idx[i - 1], idx[i], idx[( i + 1 ) % len( idx )]
            if cross( pts[a], pts[b], pts[c] ) <= 1e-12:
                continue
            inside = False
            for j in idx:
                if j in ( a, b, c ):
                    continue
                p = pts[j]
                if cross( pts[a], pts[b], p ) > -1e-9 and cross( pts[b], pts[c], p ) > -1e-9 and cross( pts[c], pts[a], p ) > -1e-9:
                    inside = True
                    break
            if not inside:
                tris.append( ( a, b, c ) )
                idx.pop( i )
                clipped = True
                break
        if not clipped:
            # Collinear leftovers: drop a flat vertex (it adds no area).
            for i in range( len( idx ) ):
                a, b, c = idx[i - 1], idx[i], idx[( i + 1 ) % len( idx )]
                if abs( cross( pts[a], pts[b], pts[c] ) ) <= 1e-9:
                    idx.pop( i )
                    break
            else:
                break
    if len( idx ) == 3:
        tris.append( tuple( idx ) )
    return tris


def _cap( m, paint, pts3, prof2, towards ):
    """ Closes a ring of points (the 3D image of the section prof2) facing towards: one polygon if it's convex, else
    triangles. """
    P, Q = [], []
    for p3, p2 in zip( pts3, prof2 ):
        if P and _same( p3, P[-1] ):
            continue
        P.append( np.asarray( p3, float ) )
        Q.append( p2 )
    while len( P ) > 2 and _same( P[0], P[-1] ):
        P.pop()
        Q.pop()
    if len( P ) < 3:
        return
    if _convex( Q ):
        card( m, paint, P, towards )
        return
    for i, j, k in _triangulate( Q ):
        card( m, paint, [ P[i], P[j], P[k] ], towards )


def _loft( m, rings, paints, normals, closed=True, both=False, uvfn=None ):
    """ Quads between consecutive rings of points (each the same count). paints: one paint or ( ring, edge ) -> paint
    (None leaves the face out). normals: per ring, per edge, ( normal at its start, at its end ). uvfn( points ) gives a
    quad explicit UVs. """
    n = len( rings[0] )
    edges = range( n ) if closed else range( n - 1 )
    for j in range( len( rings ) - 1 ):
        A, B = rings[j], rings[j + 1]
        for e in edges:
            paint = paints( j, e ) if callable( paints ) else paints
            if paint is None:
                continue
            k = ( e + 1 ) % n
            pts = [ A[e], A[k], B[k], B[e] ]
            nr = [ normals[j][e][0], normals[j][e][1], normals[j + 1][e][1], normals[j + 1][e][0] ]
            _face( m, paint, pts, nr, None if uvfn is None else uvfn( pts ), both=both )


def extrude( m, a, b, profile, paint, up=None, caps=True, smooth=30.0, chamfer=0.0, skip=(), cap_paint=None,
             cut_a=None, cut_b=None, closed=True, both=False ):
    """ A section swept straight from a to b. profile: ( x, y ) points, x to the right looking from a to b and y towards
    up (made square to the axis); either winding. paint: one paint or ( 0, edge ) -> paint; skip: edges left out. Caps
    close the ends (non-convex sections are triangulated); cut_a / cut_b: ( point, normal ) planes the ends are cut by
    instead of square. An open section (closed False) is a bent sheet, both drawn on both sides. """
    a, b = v( *a ), v( *b )
    if np.linalg.norm( b - a ) < 1e-6:
        return
    d = unit( b - a )
    u = UP if up is None else unit( up )
    u = u - d * float( np.dot( u, d ) )
    if np.linalg.norm( u ) < 1e-6:
        u = perp( d )[1]
    u = unit( u )
    s = np.cross( d, u )
    sec = [ s * x + u * y for x, y in profile ]

    def ring( origin, cut ):
        if cut is None:
            return [ origin + p for p in sec ]
        q, nn = v( *cut[0] ), unit( cut[1] )
        den = float( np.dot( d, nn ) )
        return [ a + p + d * ( float( np.dot( q - a - p, nn ) ) / den ) for p in sec ]

    ra, rb = ring( a, cut_a ), ring( b, cut_b )
    en = _edge_normals( profile, closed, smooth, chamfer )
    N = [ ( s * n0[0] + u * n0[1], s * n1[0] + u * n1[1] ) for n0, n1 in en ]
    if callable( paint ):
        paints = paint
    else:
        paints = ( lambda j, e: None if e in skip else paint )
    _loft( m, [ ra, rb ], paints, [ N, N ], closed=closed, both=both )
    if caps and closed:
        cp = cap_paint or ( None if callable( paint ) else paint )
        if cp:
            _cap( m, cp, ra, profile, -d )
            _cap( m, cp, rb, profile, d )


def bevel_box( m, centre, axes, size, paints, bevel=0.5, surface=None, skip=() ):
    """ A box with its twelve edges chamfered by bevel and shaded as the faces either side, so they catch the light like
    a rounded edge. axes: its own x, y and z (orthonormal); size along each. paints: one or { '+x', '-x', '+y', '-y',
    '+z', '-z', 'default' }; a face painted None or in skip is left out. surface adds the plain box to the collision. """
    X, Y, Z = ( unit( a ) for a in axes )
    hx, hy, hz = ( float( s ) / 2 for s in size )
    C = v( *centre )
    if surface:
        m.oriented_box( C, ( X, Y, Z ), size, { "default": None }, surface )

    def paint_of( face ):
        if face in skip:
            return None
        return paints.get( face, paints.get( "default" ) ) if isinstance( paints, dict ) else paints

    c = min( float( bevel ), 0.45 * 2 * min( hx, hy, hz ) )
    if c < 1e-3:
        _box3( m, C, ( X, Y, Z ), size, { f: paint_of( f ) for f in ( "+x", "-x", "+y", "-y", "+z", "-z" ) } )
        return
    octo = [ ( hy, -hz + c ), ( hy, hz - c ), ( hy - c, hz ), ( -hy + c, hz ), ( -hy, hz - c ), ( -hy, -hz + c ), ( -hy + c, -hz ),
             ( hy - c, -hz ) ]
    inset = [ ( hy - c, -hz + c ), ( hy - c, hz - c ), ( hy - c, hz - c ), ( -hy + c, hz - c ), ( -hy + c, hz - c ), ( -hy + c, -hz + c ),
              ( -hy + c, -hz + c ), ( hy - c, -hz + c ) ]
    big = { 0: "+y", 2: "+z", 4: "-y", 6: "-z" }
    fn = { 0: Y, 2: Z, 4: -Y, 6: -Z }
    edge_paint = []
    for e in range( 8 ):
        if e in big:
            edge_paint.append( paint_of( big[e] ) )
        else:
            edge_paint.append( paint_of( big[e - 1] ) or paint_of( big[( e + 1 ) % 8] ) )
    mid = [ ( fn[e], fn[e] ) if e in big else ( fn[e - 1], fn[( e + 1 ) % 8] ) for e in range( 8 ) ]

    def ring( x, prof ):
        return [ C + X * x + Y * py + Z * pz for py, pz in prof ]

    rings = [ ring( -hx, inset ), ring( -hx + c, octo ), ring( hx - c, octo ), ring( hx, inset ) ]
    normals = [ [ ( -X, -X ) ] * 8, mid, mid, [ ( X, X ) ] * 8 ]
    _loft( m, rings, lambda j, e: edge_paint[e], normals )
    for face, r, towards in ( ( "-x", rings[0], -X ), ( "+x", rings[3], X ) ):
        p = paint_of( face )
        if p:
            _cap( m, p, r, inset, towards )


def bobox( m, centre, right, size, paints, bevel=0.5, surface=None, skip=() ):
    """ bevel_box turned in plan like obox: right its own x (level), size ( along x, along y, up ). """
    X = unit( ( right[0], right[1], 0.0 ) )
    bevel_box( m, centre, ( X, np.cross( UP, X ), UP ), size, paints, bevel, surface, skip )


def _box3( m, centre, axes, size, paints ):
    """ m.oriented_box (drawn only), its axes made right-handed first: map_kit winds a box's faces for right-handed axes,
    so a left-handed set ( right, out, up ) would face them all inwards. """
    X, Y, Z = ( unit( a ) for a in axes )
    if float( np.dot( np.cross( X, Y ), Z ) ) < 0:
        Y = -Y
        if isinstance( paints, dict ):
            paints = { { "+y": "-y", "-y": "+y" }.get( k, k ): p for k, p in paints.items() }
    m.oriented_box( centre, ( X, Y, Z ), size, paints )


def lathe_axis( m, c, axis, profile, paints, sides=12, cap=None, turn=0.0 ):
    """ A round thing turned about axis through c: profile [ ( radius, t ) ] along the axis, outside on its right (up
    the axis, then in across the top); paints one or per band (None leaves a band out); cap closes the last ring. """
    c = v( *c )
    axis = unit( axis )
    e1, e2 = perp( axis )
    dirs = [ e1 * math.cos( turn + 2 * math.pi * k / sides ) + e2 * math.sin( turn + 2 * math.pi * k / sides ) for k in range( sides ) ]
    for j in range( len( profile ) - 1 ):
        paint = paints[j] if isinstance( paints, ( list, tuple ) ) else paints
        if paint is None:
            continue
        ( r0, t0 ), ( r1, t1 ) = profile[j], profile[j + 1]
        sl = np.array( ( t1 - t0, r0 - r1 ) )
        L = float( np.linalg.norm( sl ) )
        if L < 1e-9 or ( r0 < 1e-6 and r1 < 1e-6 ):
            continue
        sl /= L
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            pts = [ c + dirs[k] * r0 + axis * t0, c + dirs[k1] * r0 + axis * t0, c + dirs[k1] * r1 + axis * t1, c + dirs[k] * r1 + axis * t1 ]
            nrm = [ dirs[i] * sl[0] + axis * sl[1] for i in ( k, k1, k1, k ) ]
            _face( m, paint, pts, nrm )
    if cap and profile[-1][0] > 1e-6:
        r, t = profile[-1]
        card( m, cap, [ c + d * r + axis * t for d in dirs ], axis if profile[-1][1] >= profile[0][1] else -axis )


def torus( m, c, axis, R, r, paints, seg=16, sides=8, a0=0.0, a1=None, basis=None ):
    """ A ring of radius R round axis through c, its tube r: paints one or segment -> paint. a0..a1 (radians) draws an
    arc of it, from basis[0] (default perp( axis )) towards basis[1]. """
    c = v( *c )
    axis = unit( axis )
    e1, e2 = basis if basis is not None else perp( axis )
    e1, e2 = unit( e1 ), unit( e2 )
    full = a1 is None
    a1 = a0 + 2 * math.pi if full else a1
    phis = [ 2 * math.pi * k / sides for k in range( sides ) ]

    def ring( th ):
        rho = e1 * math.cos( th ) + e2 * math.sin( th )
        dirs = [ rho * math.cos( f ) + axis * math.sin( f ) for f in phis ]
        return [ c + rho * R + d * r for d in dirs ], dirs

    rings = [ ring( a0 + ( a1 - a0 ) * i / seg ) for i in range( seg + 1 ) ]
    for i in range( seg ):
        paint = paints( i ) if callable( paints ) else paints
        if paint is None:
            continue
        ( pa, da ), ( pb, db ) = rings[i], rings[i + 1]
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            _face( m, paint, [ pa[k], pa[k1], pb[k1], pb[k] ], [ da[k], da[k1], db[k1], db[k] ] )


def _dedupe( pts ):
    out = []
    for p in pts:
        p = v( *p )
        if not out or not _same( p, out[-1], 1e-4 ):
            out.append( p )
    return out


def _bend_points( pts, radius, closed=False, max_step=20.0 ):
    """ The polyline with each corner turned on a circular arc of this radius (clipped to half each leg), a point every
    max_step degrees at most. Closed: a loop, its first point not repeated. """
    pts = _dedupe( pts )
    if closed and len( pts ) > 2 and _same( pts[0], pts[-1], 1e-4 ):
        pts = pts[:-1]
    n = len( pts )
    if n < 2 or ( not closed and n < 3 ):
        return pts
    corners = range( n ) if closed else range( 1, n - 1 )
    out = [] if closed else [ pts[0] ]
    for k in corners:
        a, b, c = pts[k - 1], pts[k], pts[( k + 1 ) % n]
        d0, d1 = unit( b - a ), unit( c - b )
        cos = float( np.clip( np.dot( d0, d1 ), -1, 1 ) )
        if cos > 0.9995:
            out.append( b )
            continue
        theta = math.acos( cos )
        t = min( radius * math.tan( theta / 2 ), np.linalg.norm( b - a ) / 2, np.linalg.norm( c - b ) / 2 )
        p0, p1 = b - d0 * t, b + d1 * t
        steps = max( 2, int( math.ceil( math.degrees( theta ) / max_step ) ) )
        w = math.cos( theta / 2 )
        for s in range( steps + 1 ):
            f = s / steps
            # A rational quadratic through the corner: a true circular arc.
            q = ( ( 1 - f ) ** 2 * p0 + 2 * w * ( 1 - f ) * f * b + f * f * p1 ) / ( ( 1 - f ) ** 2 + 2 * w * ( 1 - f ) * f + f * f )
            out.append( q )
    if not closed:
        out.append( pts[-1] )
    return _dedupe( out )


def _sweep( m, path, r, paint, sides=8, closed=False, caps=True ):
    """ A round tube along path (its points used as they are), shaded smooth; the frame is carried along without
    twisting. Returns ( point, tangent ) along it. """
    P = _dedupe( path )
    n = len( P )
    if n < 2:
        return []
    T = []
    for k in range( n ):
        if closed:
            t = unit( unit( P[k] - P[k - 1] ) + unit( P[( k + 1 ) % n] - P[k] ) )
        elif k == 0:
            t = unit( P[1] - P[0] )
        elif k == n - 1:
            t = unit( P[-1] - P[-2] )
        else:
            t = unit( unit( P[k] - P[k - 1] ) + unit( P[k + 1] - P[k] ) )
        T.append( t )
    u, _ = perp( T[0] )
    rings = []
    for p, t in zip( P, T ):
        u = u - float( np.dot( u, t ) ) * t
        if np.linalg.norm( u ) < 1e-6:
            u, _ = perp( t )
        u = unit( u )
        w = np.cross( t, u )
        rings.append( [ u * math.cos( 2 * math.pi * i / sides ) + w * math.sin( 2 * math.pi * i / sides ) for i in range( sides ) ] )
    seq = list( range( n ) ) + ( [ 0 ] if closed else [] )
    for ia, ib in zip( seq, seq[1:] ):
        pa, pb, da, db = P[ia], P[ib], rings[ia], rings[ib]
        for i in range( sides ):
            i1 = ( i + 1 ) % sides
            _face( m, paint, [ pa + da[i] * r, pa + da[i1] * r, pb + db[i1] * r, pb + db[i] * r ], [ da[i], da[i1], db[i1], db[i] ] )
    if caps and not closed:
        card( m, paint, [ P[0] + d * r for d in rings[0] ], -T[0] )
        card( m, paint, [ P[-1] + d * r for d in rings[-1] ], T[-1] )
    return list( zip( P, T ) )


def tube( m, pts, r, paint, sides=8, bend_radius=None, closed=False, caps=True ):
    """ A round bar along pts, bent round its corners on arcs of bend_radius (default 1.5 x r), shaded smooth. """
    return _sweep( m, _bend_points( pts, bend_radius if bend_radius is not None else r * 1.5, closed ), r, paint, sides,
                   closed, caps )


def _along( path, pos ):
    """ The point and direction pos along a polyline: pos in ( 0, 1 ) is a share of its length, else inches. """
    P = [ v( *p ) for p in path ]
    lengths = [ float( np.linalg.norm( b - a ) ) for a, b in zip( P, P[1:] ) ]
    total = sum( lengths )
    s = pos * total if 0 < pos < 1 else pos
    s = min( max( s, 0.0 ), total )
    for a, b, L in zip( P, P[1:], lengths ):
        if L > 1e-9 and s <= L:
            return a + ( b - a ) * ( s / L ), unit( b - a )
        s -= L
    return P[-1], unit( P[-1] - P[-2] )


# ---------------------------------------------------------------------------------------------------------------------
# What this model's own collision says about a point

def _solid( m, p, pad=0.0 ):
    """ Whether p is inside one of the model's collision boxes or hulls. """
    p = np.asarray( p, float )
    for c, axes, size, _ in m.boxes:
        d = p - np.asarray( c, float )
        if all( abs( float( np.dot( d, a ) ) ) <= float( s ) / 2 + pad for a, s in zip( axes, size ) ):
            return True
    for pts, _ in m.hulls:
        pts = np.asarray( pts, float )
        if np.any( p < pts.min( axis=0 ) - pad ) or np.any( p > pts.max( axis=0 ) + pad ):
            continue
        try:
            from scipy.spatial import Delaunay
            if Delaunay( pts ).find_simplex( p ) >= 0:
                return True
        except Exception:
            continue
    return False


def _facing( m, at, out, right=None ):
    """ out turned round if it points into this model's solid with open air behind (a fixture drawn facing into its
    wall), with right turned too so lettering still reads. Returns ( out, right ). """
    at = v( *at )
    if _solid( m, at + out * 1.5 ) and not _solid( m, at - out * 1.5 ):
        return -out, ( None if right is None else -right )
    return out, right


def _depth( m, p, out, limit=48.0 ):
    """ How thick this model's wall is behind p (going in, against out), or None if there's none there. """
    p = v( *p )
    if not _solid( m, p - out * 0.5 ):
        return None
    k = 0.5
    while k < limit:
        k += 1.0
        if not _solid( m, p - out * k ):
            return k
    return limit


_FACES = {}


def _drawn_face( m, p, out, tol=0.6 ):
    """ Whether this model draws a face looking out (along out) in the plane through p, around p: a wall that has no
    collision here (drawn only, or solid in another model). """
    entry = _FACES.get( id( m ) )
    if entry is None or entry["model"] is not m:
        entry = { "model": m, "seen": {}, "rows": [] }
        _FACES[id( m )] = entry
    for paint, items in m.polygons.items():
        start = entry["seen"].get( paint, 0 )
        for points, normal in items[start:]:
            arr = np.asarray( points, float )
            entry["rows"].append( ( *normal, *arr[0], *arr.min( axis=0 ), *arr.max( axis=0 ) ) )
        entry["seen"][paint] = len( items )
    if not entry["rows"]:
        return False
    if not isinstance( entry.get( "array" ), np.ndarray ) or len( entry["array"] ) != len( entry["rows"] ):
        entry["array"] = np.asarray( entry["rows"], float )
    a = entry["array"]
    p = np.asarray( p, float )
    facing = a[:, 0:3] @ out > 0.99
    dist = np.abs( np.einsum( "ij,ij->i", a[:, 0:3], p[None, :] - a[:, 3:6] ) )
    inside = np.all( ( a[:, 6:9] - tol <= p[None, :] ) & ( p[None, :] <= a[:, 9:12] + tol ), axis=1 )
    return bool( np.any( facing & ( dist < tol ) & inside ) )


_CEILINGS = {}


def _ceiling_above( m, p, limit=160.0 ):
    """ How far above p the nearest downward-facing face of this model is (within limit), or None. """
    entry = _CEILINGS.get( id( m ) )
    if entry is None or entry["model"] is not m:
        entry = { "model": m, "seen": {}, "boxes": [] }
        _CEILINGS[id( m )] = entry
    for paint, items in m.polygons.items():
        start = entry["seen"].get( paint, 0 )
        for points, normal in items[start:]:
            if normal[2] < -0.5:
                arr = np.asarray( points, float )
                lo, hi = arr.min( axis=0 ), arr.max( axis=0 )
                entry["boxes"].append( ( lo[0], hi[0], lo[1], hi[1], lo[2] ) )
        entry["seen"][paint] = len( items )
    if not entry["boxes"]:
        return None
    b = np.asarray( entry["boxes"] )
    hit = ( b[:, 0] - 0.5 <= p[0] ) & ( p[0] <= b[:, 1] + 0.5 ) & ( b[:, 2] - 0.5 <= p[1] ) & ( p[1] <= b[:, 3] + 0.5 ) \
        & ( b[:, 4] > p[2] + 0.2 ) & ( b[:, 4] < p[2] + limit )
    if not hit.any():
        return None
    return float( b[hit, 4].min() - p[2] )


# ---------------------------------------------------------------------------------------------------------------------
# Upright shapes

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
# Pipes

def _flange_pair( m, p, t, r, paint, sides=12 ):
    """ Two weld-neck flanges bolted face to face at p on a pipe of radius r running along t. """
    R = r * 1.45 + 1.0
    hub = r * 1.1 + 0.3
    prof = [ ( r + 0.03, -3.0 ), ( hub, -1.3 ), ( R, -1.3 ), ( R, -0.14 ), ( R - 0.3, -0.14 ), ( R - 0.3, 0.14 ), ( R, 0.14 ), ( R, 1.3 ),
             ( hub, 1.3 ), ( r + 0.03, 3.0 ) ]
    lathe_axis( m, p, t, prof, paint, sides )


def _valve( m, p, t, r, paint="rv_steel", wheel="rv_yellow", stem=None ):
    """ A gate valve on a pipe of radius r at p (pipe along t): its flanged body, bonnet and yoke, the stem and a
    handwheel. stem: which way the bonnet points (default up, or level across a vertical pipe). """
    t = unit( t )
    if stem is None:
        stem = UP if abs( float( np.dot( t, UP ) ) ) < 0.7 else perp( t )[0]
    stem = unit( stem - t * float( np.dot( stem, t ) ) )
    L = max( 8.0, r * 4.0 )
    Rf = r * 1.45 + 1.0
    body = r * 1.35 + 0.4
    prof = [ ( r + 0.02, -L / 2 ), ( Rf, -L / 2 ), ( Rf, -L / 2 + 1.2 ), ( r * 1.15, -L / 2 + 1.2 ), ( body, -L / 4 ), ( body, L / 4 ),
             ( r * 1.15, L / 2 - 1.2 ), ( Rf, L / 2 - 1.2 ), ( Rf, L / 2 ), ( r + 0.02, L / 2 ) ]
    lathe_axis( m, p, t, prof, paint, 12 )
    b0 = p + stem * ( body * 0.8 )
    b1 = b0 + stem * ( r * 1.6 + 2.0 )
    bl = r * 1.6 + 2.0
    lathe_axis( m, b0, stem, [ ( r * 0.95 + 0.3, 0.0 ), ( r * 0.95 + 0.3, 1.0 ), ( r * 0.7 + 0.3, 1.6 ), ( r * 0.7 + 0.3, bl ), ( r * 0.9 + 0.3, bl ) ],
                paint, 10, cap=paint )
    s2 = np.cross( stem, t )
    top = b1 + stem * ( r * 0.9 + 3.0 )
    for sg in ( -1, 1 ):
        rod( m, b1 + s2 * ( sg * ( r * 0.55 + 0.4 ) ), top + s2 * ( sg * 0.8 ), 0.35, paint, 6 )
    rod( m, b1, top + stem * 1.4, 0.32, "rv_zinc", 6 )
    wr = r * 1.4 + 2.2
    torus( m, top + stem * 1.0, stem, wr, 0.45, wheel, seg=14, sides=4 )
    for k in range( 3 ):
        a = 2 * math.pi * k / 3
        d = t * math.cos( a ) + s2 * math.sin( a )
        rod( m, top + stem * 1.0, top + stem * 1.0 + d * wr, 0.3, wheel, 5 )


def _shoe( m, p, t, r, h, paint ):
    """ A T shoe under a pipe (p on its axis, running level along t): a web and base plate h deep, and a U-bolt over it. """
    t = unit( v( t[0], t[1], 0.0 ) )
    side = np.cross( UP, t )
    bottom = p - UP * r
    obox( m, bottom - UP * ( h / 2 ), t, ( 9.0, 0.5, h ), paint )
    obox( m, bottom - UP * ( h - 0.25 ), t, ( 10.0, 2 * r * 0.8 + 2.0, 0.5 ), { "default": paint, "-z": None } )
    rb = r + 0.35
    torus( m, p, t, rb, 0.28, paint, seg=8, sides=4, a0=0.0, a1=math.pi, basis=( side, UP ) )
    for sg in ( -1, 1 ):
        rod( m, p + side * ( sg * rb ), p + side * ( sg * rb ) - UP * ( r + 1.0 ), 0.28, paint, 4 )


def pipe( m, pts, r, paint="rv_pipe", sides=10, caps=True, bend=1.5, flanges=(), bands=None, supports=None, valves=(),
          shoe=6.0 ):
    """ A pipe along the polyline pts, bent round its corners on arcs of bend x r, shaded smooth. flanges: indices of
    points where a flange pair sits (0 and -1 for its ends). Aluminium jacketing (rv_pipe, r >= 2.5) gets a raised lap
    band where it meets an elbow, and from r 4 up every bands inches (default 60). supports: a spacing (inches) or positions along it
    for T shoes shoe deep under its level runs; valves: positions along it for gate valves (a position in ( 0, 1 ) is a
    share of its length, else inches from its start). Flanges, bands, shoes and valves are drawn in rv_steel on
    jacketing, else in the pipe's paint. """
    raw = _dedupe( pts )
    if len( raw ) < 2:
        return
    path = _bend_points( raw, r * bend, max_step=15.0 )
    _sweep( m, path, r, paint, sides, caps=caps )
    # Pipe sweeps only draw triangles. For the playable parts of the plant, record a solid
    # proxy per physical straight run so the FPS character and projectiles cannot pass
    # through large pipes. Thin conduit/wiring stays visual; high/backdrop services stay
    # visual too. Proxies are separate scene BoxColliders, leaving the baked GI meshes alone.
    if r >= 3.0:
        for a, b in zip( raw, raw[1:] ):
            a, b = v( *a ), v( *b )
            d = b - a
            if np.linalg.norm( d ) < 4.0:
                continue
            lo, hi = np.minimum( a, b ) - r, np.maximum( a, b ) + r
            if lo[0] > 2320 or hi[0] < -2320 or lo[1] > 2470 or hi[1] < -1770 or lo[2] > 410 or hi[2] < -20:
                continue
            PIPE_SOLIDS.append( ( tuple( ( a + b ) / 2 ), tuple( d ), float( r ) ) )
    jacket = paint == "rv_pipe"
    trim = "rv_steel" if jacket else paint
    if bands is None:
        bands = ( 60.0 if r >= 4 else -1.0 ) if jacket and r >= 2.5 else 0.0
    if bands:
        # Lap bands on the straight legs: at both ends, where the gored elbow's jacket overlaps, and every bands inches.
        for a, b in zip( path, path[1:] ):
            L = float( np.linalg.norm( b - a ) )
            if L < 8.0:
                continue
            d = ( b - a ) / L
            spots = [ 0.9, L - 0.9 ] + ( list( np.arange( bands, L - bands * 0.4, bands ) ) if bands > 0 else [] )
            for s in spots:
                q = a + d * s
                _sweep( m, [ q - d * 0.7, q + d * 0.7 ], r + 0.2, paint, sides, caps=False )
    for i in flanges:
        i = i if i >= 0 else len( raw ) + i
        t = unit( raw[min( i + 1, len( raw ) - 1 )] - raw[max( i - 1, 0 )] )
        _flange_pair( m, raw[i] + t * ( 3.0 if i == 0 else -3.0 if i == len( raw ) - 1 else 0.0 ), t, r, trim, sides )
    for pos in valves:
        q, t = _along( path, pos )
        _valve( m, q, t, r, trim )
    if supports:
        spots = []
        if isinstance( supports, ( int, float ) ):
            for a, b in zip( path, path[1:] ):
                L = float( np.linalg.norm( b - a ) )
                d = ( b - a ) / max( L, 1e-9 )
                if L < supports * 0.5 or abs( d[2] ) > 0.05:
                    continue
                for s in np.arange( supports * 0.5, L, supports ):
                    spots.append( ( a + d * s, d ) )
        else:
            for pos in supports:
                q, d = _along( path, pos )
                if abs( d[2] ) < 0.05:
                    spots.append( ( q, d ) )
        for q, d in spots:
            _shoe( m, q, d, r, shoe, trim )


def disc_ring( m, a, b, r, paint, sides=10 ):
    rod( m, a, b, r, paint, sides, caps=True )


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


RAIL_TOP, RAIL_MID, RAIL_POST = 0.95, 0.8, 0.95      # 1.9 in and 1.6 in tube, as a galvanised or painted handrail


def railing( m, pts, z, paint="rv_yellow", height=42.0, post_every=60.0, kick=True, clip_to=None, closed=False, name="rail",
             posts=True, slope=None ):
    """ A guard rail along plan pts at floor height z (or slope: a z per point, for stairs): a round top rail and mid
    rail bent round the corners, round posts on base plates with a fitting under the top rail, a kick plate. clip_to:
    the clip's top (None for none). """
    pts = [ v( p[0], p[1], 0.0 ) for p in pts ]
    if closed:
        pts = pts + [ pts[0] ]
    zs = slope if slope is not None else [ z ] * len( pts )
    if closed and slope is None:
        zs = zs + [ z ]
    loop = closed and slope is None
    tops = [ p + UP * ( zz + height ) for p, zz in zip( pts, zs ) ]
    mids = [ p + UP * ( zz + height * 0.5 ) for p, zz in zip( pts, zs ) ]
    if loop:
        tops, mids = tops[:-1], mids[:-1]
    tube( m, tops, RAIL_TOP, paint, 8, bend_radius=3.0, closed=loop )
    tube( m, mids, RAIL_MID, paint, 6, bend_radius=3.0, closed=loop )
    for k in range( len( pts ) - 1 ):
        a, b = pts[k], pts[k + 1]
        za, zb = zs[k], zs[k + 1]
        d = b - a
        L = float( np.linalg.norm( d ) )
        if L < 1:
            continue
        if kick:
            A, B = a + UP * ( za + 0.25 ), b + UP * ( zb + 0.25 )
            extrude( m, A, B, [ ( -0.12, 0.0 ), ( 0.12, 0.0 ), ( 0.12, 3.75 ), ( -0.12, 3.75 ) ], paint, up=UP, skip=( 0, ), smooth=0 )
        if posts:
            count = max( 1, int( math.ceil( L / post_every ) ) )
            for i in range( count + ( 1 if k == len( pts ) - 2 and not closed else 0 ) ):
                f = i / count
                p = a + d * f
                zp = za + ( zb - za ) * f
                _post( m, p + UP * zp, height, paint, unit( d ) )
        if clip_to is not None:
            clip( name, a, b, min( za, zb ), max( za, zb ) + clip_to )


def _post( m, foot, height, paint, along ):
    """ A round railing post from foot up under the top rail: a base plate and a fitting round the rail. """
    top = foot + UP * ( height - RAIL_TOP * 0.6 )
    rod( m, foot + UP * 0.4, top, RAIL_POST, paint, 8 )
    obox( m, foot + UP * 0.2, along, ( 4.5, 4.5, 0.4 ), { "default": paint, "-z": None } )
    lathe_axis( m, foot + UP * ( height - 3.4 ), UP, [ ( RAIL_POST, 0.0 ), ( RAIL_POST + 0.32, 0.4 ), ( RAIL_POST + 0.32, 2.6 ) ], paint, 6 )


def stairs( m, foot, head, width, z0, z1, tread="rv_grating", side="rv_yellow", rails=( True, True ), rail_paint="rv_yellow",
            surface=METAL, solid_under=False, under_paint="rv_plinth", name="stair" ):
    """ A straight flight from foot (plan, its bottom nosing's centre) to head (the top nosing's centre), width across:
    steps of about 7.5 in, hand rails. Steel: channel stringers, grating treads with an angle nosing and a back bar,
    base plates. Concrete (solid_under): the steps, their faces and sides, galvanised nosings with an anti-slip
    strip. One wedge hull carries walking. """
    foot, head = v( foot[0], foot[1], 0 ), v( head[0], head[1], 0 )
    along = head - foot
    run = float( np.linalg.norm( along ) )
    d = along / run
    sh = np.cross( UP, d )
    s = sh * ( width / 2 )
    steps = max( 2, int( round( ( z1 - z0 ) / 7.5 ) ) )
    rise, going = ( z1 - z0 ) / steps, run / steps
    for i in range( steps ):
        p = foot + d * ( going * i )
        q = p + d * going
        zt = z0 + rise * ( i + 1 )
        top = [ p - s + UP * zt, q - s + UP * zt, q + s + UP * zt, p + s + UP * zt ]
        if solid_under:
            card( m, tread, top, UP )
            card( m, side, [ p - s + UP * ( zt - 1.5 ), p + s + UP * ( zt - 1.5 ), p + s + UP * zt, p - s + UP * zt ], -d )
            card( m, under_paint, [ p - s + UP * ( zt - rise ), p + s + UP * ( zt - rise ), p + s + UP * ( zt - 1.5 ), p - s + UP * ( zt - 1.5 ) ], -d )
            # A galvanised nosing angle on the step's edge, its anti-slip insert.
            w = width - 3.0
            extrude( m, p - sh * ( w / 2 ) + UP * zt, p + sh * ( w / 2 ) + UP * zt,
                     [ ( -0.06, 0.08 ), ( -0.06, -1.5 ), ( 0.06, -1.5 ), ( 0.06, -0.04 ), ( 1.7, -0.04 ), ( 1.7, 0.08 ) ],
                     "rv_zinc", up=UP, smooth=0, caps=True )
            card( m, "rv_yellow", [ p + d * 0.35 - sh * ( w / 2 - 1 ) + UP * ( zt + 0.1 ), p + d * 1.35 - sh * ( w / 2 - 1 ) + UP * ( zt + 0.1 ),
                                    p + d * 1.35 + sh * ( w / 2 - 1 ) + UP * ( zt + 0.1 ), p + d * 0.35 + sh * ( w / 2 - 1 ) + UP * ( zt + 0.1 ) ], UP )
        else:
            # The grating panel (seen through from above and below), its nosing bar, back bar and end plates.
            grid = [ p + d * 1.6 - s + UP * zt, q - s + UP * zt, q + s + UP * zt, p + d * 1.6 + s + UP * zt ]
            card( m, tread, grid, UP )
            card( m, tread, [ x - UP * 1.25 for x in grid ], -UP )
            w = width - 0.4
            extrude( m, p - sh * ( w / 2 ) + UP * zt, p + sh * ( w / 2 ) + UP * zt,
                     [ ( 0.0, 0.0 ), ( 0.0, -1.9 ), ( 0.25, -1.9 ), ( 0.25, -0.25 ), ( 1.6, -0.25 ), ( 1.6, 0.0 ) ], side, up=UP, smooth=0 )
            obox( m, q - d * 0.15 + UP * ( zt - 0.62 ), sh, ( w, 0.3, 1.24 ), { "default": "rv_steel", "+z": None } )
    if solid_under:
        # The steps' sides: concrete from the foot up to the head.
        for sgn in ( -1, 1 ):
            o = s * sgn * 1.02
            card( m, under_paint, [ foot + o + UP * z0, head + o + UP * z0, head + o + UP * ( z1 + 3 ), foot + o + UP * ( z0 + rise + 3 ) ], o, both=False )
        card( m, under_paint, [ head - s + UP * z0, head + s + UP * z0, head + s + UP * z1, head - s + UP * z1 ], d )
    else:
        # Channel stringers, toes out, cut plumb at the foot and the head; base plates at the foot.
        D = 10.0
        top_rise = ( z1 + 3 ) - ( z0 + rise + 3 )
        axis = unit( along + UP * top_rise )
        for sgn in ( -1, 1 ):
            o = sh * ( sgn * ( width / 2 + 0.15 ) )
            A = foot + o + UP * ( z0 + rise + 3 )
            B = head + o + UP * ( z1 + 3 )
            # x across is to the right of the axis (-sh): outward is x = -sgn.
            prof = [ ( 0.0, 0.0 ), ( 2.6, 0.0 ), ( 2.6, -0.45 ), ( 0.3, -0.45 ), ( 0.3, -D + 0.45 ), ( 2.6, -D + 0.45 ), ( 2.6, -D ), ( 0.0, -D ) ]
            prof = [ ( -sgn * x, y ) for x, y in prof ]
            extrude( m, A - axis * 30, B + axis * 30, prof, side, up=UP, smooth=0, chamfer=0.6, cut_a=( A, d ), cut_b=( B, d ) )
            bobox( m, foot + o + sh * ( sgn * 1.3 ) + d * 2.5 + UP * ( z0 + 0.25 ), d, ( 7.0, 4.6, 0.5 ), "rv_steel", 0.12, skip=( "-z", ) )
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


def ladder( m, foot, top_z, out, width=18.0, paint="rv_yellow", cage=True, standoff=7.0, extend=42.0, rung_every=12.0 ):
    """ A fixed steel ladder: foot is the middle of its foot (plan and floor z), out points from the wall to the climber,
    standoff how far its rails stand off the wall. Flat side rails, round rungs, stand-off brackets every 8 ft, the
    rails carried extend over top_z and turned back to the wall, and a cage from 7 ft up when cage and it's over 10 ft. """
    foot = v( *foot )
    out = unit( v( out[0], out[1], 0.0 ) )
    side = np.cross( UP, out )
    z0 = foot[2]
    base = v( foot[0], foot[1], 0.0 )
    for sg in ( -1, 1 ):
        r0 = base + side * ( sg * width / 2 )
        bobox( m, r0 + UP * ( ( z0 + top_z + extend * 0.6 ) / 2 ), side, ( 0.4, 2.5, top_z + extend * 0.6 - z0 ), paint, 0.1 )
        # Over the top: the rail goes on up, then back to the wall in a gooseneck.
        tube( m, [ r0 + UP * ( top_z + extend * 0.6 ), r0 + UP * ( top_z + extend ), r0 - out * ( standoff - 0.5 ) + UP * ( top_z + extend ),
                   r0 - out * ( standoff - 0.5 ) + UP * ( top_z + extend - 8 ) ], 0.75, paint, 6, bend_radius=3.0 )
        for z in np.arange( z0 + 30, top_z, 96.0 ):
            obox( m, r0 - out * ( standoff / 2 ) + UP * z, out, ( standoff, 0.4, 2.5 ), paint )
    for z in np.arange( z0 + rung_every, top_z + 0.1, rung_every ):
        rod( m, base - side * ( width / 2 ) + UP * z, base + side * ( width / 2 ) + UP * z, 0.5, paint, 6 )
    if cage and top_z - z0 > 120:
        R = 14.0
        centre = base + out * ( R - 1.0 )
        zs = list( np.arange( z0 + 84, top_z + extend - 4, 40.0 ) )
        for z in zs:
            hoop = [ base - side * ( width / 2 ) + UP * z ]
            for k in range( 9 ):
                a = math.pi * k / 8
                hoop.append( centre - side * ( R * math.cos( a ) ) + out * ( R * math.sin( a ) ) + UP * z )
            hoop.append( base + side * ( width / 2 ) + UP * z )
            _sweep( m, hoop, 0.35, paint, 4, caps=False )
        if zs:
            for k in ( 1, 3, 4, 5, 7 ):
                a = math.pi * k / 8
                p = centre - side * ( R * math.cos( a ) ) + out * ( R * math.sin( a ) )
                obox( m, p + UP * ( ( zs[0] + zs[-1] ) / 2 ), np.cross( UP, unit( p - centre ) ), ( 0.3, 1.8, zs[-1] - zs[0] + 2 ), paint )


_fixed_ladder = ladder


# ---------------------------------------------------------------------------------------------------------------------
# Props

def tank( m, c, r, h, paint="rv_white", z0=0.0, sides=24, rings=True, ladder=True, letters_name=None, facing=None,
          surface=METAL ):
    """ An upright tank: a cylinder on a plinth with a torispherical head, stiffening rings, anchor chairs, a manway,
    nozzles, a level gauge, a vent, a caged ladder with a rail on the head. """
    C = v( c[0], c[1], 0.0 )
    lathe( m, c, [ ( r + 4, z0 ), ( r + 4, z0 + 7.2 ), ( r + 3.2, z0 + 8 ), ( r, z0 + 8 ) ], "rv_plinth", sides )
    cylinder( m, c, r, z0 + 8, z0 + h, paint, sides, surface=surface )
    top = z0 + h
    head = [ ( r, top ), ( r * 0.985, top + r * 0.05 ), ( r * 0.94, top + r * 0.105 ), ( r * 0.84, top + r * 0.16 ), ( r * 0.66, top + r * 0.21 ),
             ( r * 0.44, top + r * 0.25 ), ( r * 0.22, top + r * 0.272 ), ( 0.0, top + r * 0.28 ) ]
    lathe( m, c, head, paint, sides )

    def head_z( rr ):
        for ( ra, za ), ( rb, zb ) in zip( head, head[1:] ):
            if rb <= rr <= ra:
                return za + ( zb - za ) * ( ra - rr ) / max( ra - rb, 1e-9 )
        return top

    if rings:
        for zz in np.arange( z0 + 8 + 72, z0 + h - 10, 72 ):
            lathe( m, c, [ ( r, zz - 0.55 ), ( r + 1.8, zz - 0.35 ), ( r + 1.8, zz + 0.35 ), ( r, zz + 0.55 ) ], "rv_steel", sides )
    f = unit( facing if facing is not None else ( 1, 0 ) )
    f = v( f[0], f[1], 0.0 )
    base_ang = math.atan2( f[1], f[0] )

    def radial( deg ):
        a = base_ang + math.radians( deg )
        return v( math.cos( a ), math.sin( a ), 0.0 )

    # Anchor chairs round the foot: two gussets and a cap plate over each bolt.
    for k in range( 6 ):
        d = radial( 30 + 60 * k )
        sd = np.cross( UP, d )
        for sg in ( -1, 1 ):
            obox( m, C + d * ( r + 1.6 ) + sd * ( sg * 2.2 ) + UP * ( z0 + 12 ), d, ( 3.2, 0.5, 8.0 ), paint )
        obox( m, C + d * ( r + 1.8 ) + UP * ( z0 + 16.25 ), d, ( 3.6, 5.4, 0.5 ), paint )
    # A manway low on the shell, two nozzles with blind flanges, an outlet with a gate valve.
    trim = "rv_steel"

    def nozzle( deg, z, rn, length, cover=True ):
        d = radial( deg )
        p0 = C + d * ( r - 1.0 ) + UP * z
        R = rn * 1.45 + 1.0
        prof = [ ( rn, 0.0 ), ( rn, length - 1.4 ), ( R, length - 1.4 ), ( R, length ) ]
        if cover:
            prof += [ ( R, length + 1.1 ), ( R * 0.9, length + 1.3 ), ( 0.0, length + 1.3 ) ]
        lathe_axis( m, p0, d, prof, [ paint ] + [ trim ] * ( len( prof ) - 2 ), 12 if rn < 8 else 16 )
        return p0 + d * length, d

    end, d = nozzle( -75, z0 + 30, 11.0, 10.0 )
    sd = np.cross( UP, d )
    for sg in ( -1, 1 ):
        rod( m, end + d * 1.3 + sd * ( sg * 4.0 ) + UP * 4.0, end + d * 3.2 + sd * ( sg * 4.0 ) + UP * 4.0, 0.4, "rv_zinc", 6 )
    rod( m, end + d * 3.2 - sd * 4.0 + UP * 4.0, end + d * 3.2 + sd * 4.0 + UP * 4.0, 0.4, "rv_zinc", 6 )
    nozzle( 105, z0 + h * 0.72, 3.5, 8.0 )
    end, d = nozzle( -112, z0 + 18, 4.0, 7.0, cover=False )
    pipe( m, [ end, end + d * 16.0, v( *( end + d * 16.0 )[:2], z0 - 2.0 ) ], 4.0, trim, 12, caps=False, bands=0 )
    _valve( m, end + d * 6.5, d, 4.0, trim )
    # A level gauge: a sight column on two branches off the shell.
    d = radial( -42 )
    g = C + d * ( r + 5.0 )
    lo_z, hi_z = z0 + 26, z0 + h - 24
    rod( m, g + UP * ( lo_z - 4 ), g + UP * ( hi_z + 4 ), 1.0, "rv_zinc", 8, caps=True )
    rod( m, g + UP * ( lo_z + 6 ), g + UP * ( hi_z - 6 ), 1.05, "rv_ring_orange", 8 )
    for z in ( lo_z, hi_z ):
        rod( m, C + d * ( r - 0.5 ) + UP * z, g + UP * z, 0.8, "rv_zinc", 6 )
        lathe_axis( m, C + d * ( r + 2.2 ) + UP * z, d, [ ( 0.8, -0.4 ), ( 1.9, -0.4 ), ( 1.9, 0.4 ), ( 0.8, 0.4 ) ], trim, 8 )
    # On the head: a vent with its gooseneck, a roof nozzle.
    vd = radial( 150 )
    vp = C + vd * ( r * 0.35 )
    vz = head_z( r * 0.35 )
    tube( m, [ vp + UP * ( vz - 2 ), vp + UP * ( vz + 14 ), vp + vd * 7 + UP * ( vz + 14 ), vp + vd * 7 + UP * ( vz + 6 ) ], 2.2, trim, 10, bend_radius=3.2 )
    rp = C + radial( -150 ) * ( r * 0.4 )
    rz = head_z( r * 0.4 )
    lathe_axis( m, rp + UP * ( rz - 2 ), UP, [ ( 5.0, 0.0 ), ( 5.0, 6.0 ), ( 8.2, 6.0 ), ( 8.2, 7.4 ), ( 7.6, 7.6 ), ( 0.0, 7.6 ) ],
                [ paint, trim, trim, trim, trim ], 14 )
    if ladder:
        LD = 7.0
        foot = C + f * ( r + LD ) + UP * z0
        ladder_top = top + r * 0.05
        _fixed_ladder( m, foot, ladder_top, f, 18.0, "rv_steel", True, LD, 36.0 )
        # A rail on the head either side of the ladder's exit.
        for sg in ( -1, 1 ):
            arc = []
            for k in range( 4 ):
                a = math.radians( sg * ( 14 + 12 * k ) )
                dd = f * math.cos( a ) + np.cross( UP, f ) * math.sin( a )
                arc.append( ( C + dd * ( r - 5.0 ), head_z( r - 5.0 ) ) )
            railing( m, [ p for p, _ in arc ], 0.0, "rv_steel", height=42.0, post_every=40.0, kick=False, slope=[ z for _, z in arc ] )
    if letters_name and facing is not None:
        out = v( f[0], f[1], 0 )
        right = np.cross( UP, out )
        rot = math.radians( 35 )
        out2 = unit( out * math.cos( rot ) + right * math.sin( rot ) )
        centre = v( c[0], c[1], 0 ) + out2 * ( r + 0.3 ) + UP * ( z0 + h * 0.55 )
        letters( m, letters_name, centre, np.cross( UP, out2 ), r * 1.0, "dark" )


# The F-shape's half section ( across, up ): 32 in tall, 24 in at the foot, 9.5 at the top; the collision is its hull.
JERSEY = [ ( 12.0, 0.0 ), ( 12.0, 3.0 ), ( 8.5, 10.0 ), ( 4.75, 32.0 ) ]


def _jersey_section( ch_l, ch_r ):
    """ The F-shape's section ( x across, z up ), counter-clockwise from its left foot, its top arrises chamfered ch_l and
    ch_r, a point in the middle of its top. """
    def slope_x( z ):
        return 8.5 - ( z - 10.0 ) * ( 3.75 / 22.0 )

    return [ ( -12.0, 0.0 ), ( 12.0, 0.0 ), ( 12.0, 3.0 ), ( 8.5, 10.0 ), ( slope_x( 32.0 - ch_r ), 32.0 - ch_r ), ( 4.75 - ch_r * 0.95, 32.0 ),
             ( 0.0, 32.0 ), ( -( 4.75 - ch_l * 0.95 ), 32.0 ), ( -slope_x( 32.0 - ch_l ), 32.0 - ch_l ), ( -8.5, 10.0 ), ( -12.0, 3.0 ) ]


def _clip_half( poly, z, keep_below ):
    """ A polygon clipped to z' <= z (keep_below) or z' >= z (Sutherland-Hodgman on one line). """
    out = []
    n = len( poly )
    for k in range( n ):
        a, b = poly[k], poly[( k + 1 ) % n]
        ina = a[1] <= z + 1e-9 if keep_below else a[1] >= z - 1e-9
        inb = b[1] <= z + 1e-9 if keep_below else b[1] >= z - 1e-9
        if ina:
            out.append( a )
        if ina != inb:
            f = ( z - a[1] ) / ( b[1] - a[1] )
            out.append( ( a[0] + ( b[0] - a[0] ) * f, z ) )
    return out


def _inset( poly, dist, keep=() ):
    """ A counter-clockwise polygon moved in by dist, the edges in keep left where they are: each point where its two
    edges' moved lines meet. """
    n = len( poly )
    P = [ np.asarray( p, float ) for p in poly ]
    lines = []
    for e in range( n ):
        a, b = P[e], P[( e + 1 ) % n]
        d = _unit2( b - a )
        inward = np.array( ( -d[1], d[0] ) )
        lines.append( ( a + inward * ( 0.0 if e in keep else dist ), d ) )
    out = []
    for k in range( n ):
        ( p1, d1 ), ( p2, d2 ) = lines[k - 1], lines[k]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs( den ) < 1e-9:
            out.append( tuple( p2 ) )
            continue
        w = p2 - p1
        t = ( w[0] * d2[1] - w[1] * d2[0] ) / den
        out.append( tuple( p1 + d1 * t ) )
    return out


def jersey( m, centre, along, length=118.0, paint="rv_precast", surface=STONE, seed=None ):
    """ A precast concrete barrier: the F-shape, 32 in tall, 24 in at the foot and 9.5 at the top, its top arrises and
    ends chamfered and chipped, two drain scuppers at the foot and two lifting slots through the top. Its collision is
    the plain F-shape's hull. """
    along = unit( ( along[0], along[1], 0.0 ) )
    side = np.cross( UP, along )
    c = v( centre[0], centre[1], 0.0 )
    half = length / 2
    a, b = c - along * half, c + along * half
    full = JERSEY + [ ( -x, z ) for x, z in reversed( JERSEY ) ]
    m.hull( [ a + side * x + UP * z for x, z in full ] + [ b + side * x + UP * z for x, z in full ], surface )
    if seed is None:
        seed = zlib.crc32( f"{c[0]:.1f},{c[1]:.1f}".encode() )
    rng = np.random.default_rng( seed )
    ce = 1.0
    # Gaps through it: ( x0, x1, z0, z1 ).
    gaps = []
    if length >= 70:
        for sg in ( -1, 1 ):
            x = sg * length * 0.24
            gaps.append( ( x - 8.0, x + 8.0, 0.0, 4.0 ) )
    if length >= 60:
        for sg in ( -1, 1 ):
            x = sg * ( half - 19.0 )
            gaps.append( ( x - 2.5, x + 2.5, 23.0, 26.5 ) )
    xs = { -half, half, -half + ce, half - ce }
    xs |= { g[0] for g in gaps } | { g[1] for g in gaps }
    xs |= set( np.linspace( -half + ce, half - ce, max( 2, int( length / 11 ) ) ) )
    xs = sorted( xs )
    jitter = { x: ( float( rng.uniform( 0.55, 1.6 ) ), float( rng.uniform( 0.55, 1.6 ) ) ) for x in xs }
    for x in ( -half, half, -half + ce, half - ce ):
        jitter[x] = ( 1.0, 1.0 )
    u_off = float( rng.uniform( 0, 64 ) )

    def to3( x, q ):
        return c + along * x + side * q[0] + UP * q[1]

    def uvfn( pts ):
        out = []
        for p in pts:
            rel = p - c
            px, pz = float( np.dot( rel, side ) ), float( rel[2] )
            out.append( ( ( float( np.dot( rel, along ) ) + u_off ) / 64.0, ( pz + max( 0.0, 4.75 - abs( px ) ) ) / 64.0 ) )
        return out

    def normals3( sec ):
        en = _edge_normals( sec, True, smooth=20.0, chamfer=2.6 )
        return [ ( side * n0[0] + UP * n0[1], side * n1[0] + UP * n1[1] ) for n0, n1 in en ]

    def drawn( sec ):
        return lambda j, e: None if ( abs( sec[e][1] ) < 1e-6 and abs( sec[( e + 1 ) % len( sec )][1] ) < 1e-6 ) else paint

    def pieces( sec, x0, x1 ):
        """ The section's parts in the segment x0..x1, cut round any gap there, and the gaps' bands. """
        bands = [ ( g[2], g[3] ) for g in gaps if g[0] - 1e-6 <= ( x0 + x1 ) / 2 <= g[1] + 1e-6 ]
        out = [ sec ]
        for z0, z1 in bands:
            nxt = []
            for p in out:
                below = _clip_half( p, z0, True ) if z0 > 1e-6 else []
                above = _clip_half( p, z1, False )
                nxt += [ q for q in ( below, above ) if len( q ) >= 3 and abs( _area2( q ) ) > 1e-6 ]
            out = nxt
        return out, bands

    for x0, x1 in zip( xs, xs[1:] ):
        if x0 < -half + ce - 1e-6 or x1 > half - ce + 1e-6:
            # The end's chamfer: from the end face (the section moved in) to the full section.
            end_x, in_x = ( x0, x1 ) if x0 < -half + ce - 1e-6 else ( x1, x0 )
            sec = _jersey_section( 1.0, 1.0 )
            ins = _inset( sec, ce, keep=( 0, ) )
            ring_end, ring_in = [ to3( end_x, q ) for q in ins ], [ to3( in_x, q ) for q in sec ]
            ax = along * ( -1.0 if end_x < 0 else 1.0 )
            N = normals3( sec )
            rings = [ ring_end, ring_in ] if end_x < in_x else [ ring_in, ring_end ]
            nn = [ [ ( ax, ax ) ] * len( sec ), N ] if end_x < in_x else [ N, [ ( ax, ax ) ] * len( sec ) ]
            _loft( m, rings, drawn( sec ), nn )
            _cap( m, paint, ring_end, ins, ax )
            continue
        parts0, _ = pieces( _jersey_section( *jitter[x0] ), x0, x1 )
        parts1, _ = pieces( _jersey_section( *jitter[x1] ), x0, x1 )
        for p0, p1 in zip( parts0, parts1 ):
            if len( p0 ) != len( p1 ):
                continue
            _loft( m, [ [ to3( x0, q ) for q in p0 ], [ to3( x1, q ) for q in p1 ] ], drawn( p0 ), [ normals3( p0 ), normals3( p1 ) ],
                   uvfn=uvfn if paint == "rv_precast" else None )
    # The gaps' end walls: the section's band at each end of a gap, facing into it.
    for g0, g1, z0, z1 in gaps:
        band = _clip_half( _clip_half( _jersey_section( 1.0, 1.0 ), z1, True ), z0, False )
        if len( band ) < 3:
            continue
        for x, towards in ( ( g0, along ), ( g1, -along ) ):
            _cap( m, paint, [ to3( x, q ) for q in band ], band, towards )


def _chamfer_rect( hx, hy, r ):
    """ A rectangle ( x, y ) counter-clockwise with its corners cut r: eight points, from the +x side's low corner. """
    return [ ( hx, -hy + r ), ( hx, hy - r ), ( hx - r, hy ), ( -hx + r, hy ), ( -hx, hy - r ), ( -hx, -hy + r ), ( -hx + r, -hy ), ( hx - r, -hy ) ]


def case( m, c, size, along=( 1, 0 ), paint="rv_olive", z0=0.0, surface=PLASTIC, lid_open=False ):
    """ A moulded equipment case: a rounded shell with a rib round its base, the lid's seam, black corner bumpers,
    recessed latches, fold-down end handles and an ID card. size ( L, W, H ). lid_open stands the lid open on its
    hinge over the foam. Collides as its box. """
    along = unit( ( along[0], along[1], 0.0 ) )
    side = np.cross( UP, along )
    L, W, H = size
    centre = v( c[0], c[1], z0 + H / 2 )
    obox( m, centre, along, ( L, W, H ), { "default": None }, surface )
    o = v( c[0], c[1], z0 )
    r = min( 2.4, 0.11 * min( L, W ) )
    hb = H * 0.7
    g = 0.55
    sec = _chamfer_rect( L / 2, W / 2, r )
    en = _edge_normals( sec, True, smooth=50, chamfer=r * 1.6 )
    sideN = [ ( along * a[0] + side * a[1], along * b[0] + side * b[1] ) for a, b in en ]
    upN, dnN = [ ( UP, UP ) ] * 8, [ ( -UP, -UP ) ] * 8
    corner = lambda e: e % 2 == 1                                           # noqa: E731

    def ring( off, z ):
        rr = max( 0.2, r + off * 0.6 )
        return [ o + along * x + side * y + UP * z for x, y in _chamfer_rect( L / 2 + off, W / 2 + off, rr ) ]

    def run( spec, paints, xf=None ):
        rings = [ ring( off, z ) for off, z, _ in spec ]
        normals = [ n for _, _, n in spec ]
        if xf:
            rings = [ [ xf( p ) for p in rg ] for rg in rings ]
            normals = [ [ ( xf( n0, True ), xf( n1, True ) ) for n0, n1 in nn ] for nn in normals ]
        _loft( m, rings, paints, normals )
        return rings

    mid = hb * 0.5
    base = [ ( -0.35, 0.0, dnN ), ( 0.0, 0.45, sideN ), ( 0.0, 2.6, sideN ), ( 0.0, mid - 0.9, sideN ), ( 0.3, mid - 0.55, sideN ),
             ( 0.3, mid + 0.55, sideN ), ( 0.0, mid + 0.9, sideN ), ( 0.0, hb - 0.45, sideN ), ( -0.3, hb, upN ) ]
    run( base, lambda j, e: "rv_black" if ( j in ( 0, 1 ) and corner( e ) ) else paint )
    if lid_open:
        # Open: the base's inside wall and the foam in it.
        inner = [ ( -0.3, hb, upN ), ( -0.7, hb, upN ) ]
        run( inner, "rv_black" )
        card( m, "rv_black", ring( -0.7, hb - 0.8 ), UP )
        rg = ring( -0.7, hb )
        rgd = ring( -0.7, hb - 0.8 )
        for k in range( 8 ):
            k1 = ( k + 1 ) % 8
            card( m, "rv_black", [ rg[k], rg[k1], rgd[k1], rgd[k] ], -( sideN[k][0] + sideN[k][1] ) )
        hinge = o - side * ( W / 2 ) + UP * ( hb + g * 0.5 )
        ang = math.radians( -105 )

        def xf( p, is_dir=False ):
            q = np.asarray( p, float ) - ( 0 if is_dir else hinge )
            ka = float( np.dot( q, along ) )
            ks, kz = float( np.dot( q, side ) ), float( q[2] )
            ns = ks * math.cos( ang ) - kz * math.sin( ang )
            nz = ks * math.sin( ang ) + kz * math.cos( ang )
            out = along * ka + side * ns + UP * nz
            return out if is_dir else out + hinge
    else:
        xf = None
        run( [ ( -0.3, hb, upN ), ( -0.55, hb, upN ) ], "rv_black" )
        run( [ ( -0.55, hb, sideN ), ( -0.55, hb + g, sideN ) ], "rv_black" )
    lid = [ ( -0.55, hb + g, dnN ), ( -0.3, hb + g, dnN ), ( 0.0, hb + g + 0.45, sideN ), ( 0.0, H - 2.2, sideN ), ( 0.0, H - 0.8, sideN ),
            ( -0.8, H, upN ) ]
    rings = run( lid, lambda j, e: "rv_black" if j == 0 or ( j >= 3 and corner( e ) ) else paint, xf )
    top_towards = UP if xf is None else xf( UP, True )
    _cap( m, paint, rings[-1], _chamfer_rect( L / 2 - 0.8, W / 2 - 0.8, max( 0.2, r - 0.48 ) ), top_towards )
    if xf is not None:
        _cap( m, "rv_black", rings[0], _chamfer_rect( L / 2 - 0.55, W / 2 - 0.55, max( 0.2, r - 0.33 ) ), xf( -UP, True ) )
    # Latches on the long sides, in pockets across the seam.
    xs_ = ( -L * 0.28, L * 0.28 ) if L >= 40 else ( 0.0, )
    for sg in ( -1, 1 ):
        n_ = side * sg
        for x in xs_:
            if lid_open and sg < 0:
                continue
            p = o + along * x + n_ * ( W / 2 ) + UP * hb
            card( m, "rv_black", [ p - along * 1.9 - UP * 3.6 + n_ * 0.02, p + along * 1.9 - UP * 3.6 + n_ * 0.02, p + along * 1.9 + n_ * 0.02,
                                   p - along * 1.9 + n_ * 0.02 ], n_ )
            bevel_box( m, p + n_ * 0.35 - UP * 1.5, ( along, n_, UP ), ( 2.7, 0.7, 3.8 ), "rv_dark", 0.18, skip=( "-y", ) )
            rod( m, p + n_ * 0.45 - along * 1.6 - UP * 3.2, p + n_ * 0.45 + along * 1.6 - UP * 3.2, 0.3, "rv_zinc", 6 )
    # Fold-down handles on the ends.
    for sg in ( -1, 1 ):
        n_ = along * sg
        p = o + n_ * ( L / 2 ) + UP * ( hb - 2.0 )
        for sy in ( -1, 1 ):
            obox( m, p + n_ * 0.4 + side * ( sy * 3.4 ), n_, ( 0.8, 1.2, 1.4 ), "rv_black" )
            rod( m, p + n_ * 0.7 + side * ( sy * 3.4 ), p + n_ * 1.0 + side * ( sy * 3.4 ) - UP * 2.4, 0.3, "rv_black", 5 )
        rod( m, p + n_ * 1.0 - side * 3.6 - UP * 2.4, p + n_ * 1.0 + side * 3.6 - UP * 2.4, 0.55, "rv_black", 6 )
    # The ID card on its holder.
    p = o - side * ( W / 2 + 0.03 ) + along * ( L * 0.18 ) + UP * ( hb * 0.78 )
    card( m, "rv_ring_white", [ p - along * 2.2 - UP * 1.3, p + along * 2.2 - UP * 1.3, p + along * 2.2 + UP * 1.3, p - along * 2.2 + UP * 1.3 ], -side )


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
    up )). Turned round to read from outside if that face looks into this model's solid. """
    right = unit( right )
    if abs( float( np.dot( unit( up ), UP ) ) ) > 0.99:
        _, flipped = _facing( m, centre, np.cross( right, unit( up ) ), right )
        right = flipped
    a = RM.aspect( RM.LETTERS, name )
    uv = [ RM.atlas_uv( RM.LETTERS, RM.LETTER_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    quad( m, f"rv_letters_{tone}", centre, right, up, h * a, h, uv, off )


def plate( m, name, centre, right, h, up=UP, off=0.3, back=None, edge=0.25 ):
    """ A sign from rv_plates' atlas, h tall, standing off its face by off on an aluminium edge edge deep (none if off
    leaves no room); back paints its other side. """
    a = RM.aspect( RM.PLATES, name )
    uv = [ RM.atlas_uv( RM.PLATES, RM.PLATE_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    quad( m, "rv_plates", centre, right, up, h * a, h, uv, off )
    right_, up_ = unit( right ), unit( up )
    out = np.cross( right_, up_ )
    if back:
        quad( m, back, centre, -right_, up_, h * a, h, None, off - 0.1 )
    edge = min( edge, off - 0.05 )
    if not back and edge > 0.04:
        cc = v( *centre ) + out * off
        w2, h2 = h * a / 2, h / 2
        corners = [ cc - right_ * w2 - up_ * h2, cc + right_ * w2 - up_ * h2, cc + right_ * w2 + up_ * h2, cc - right_ * w2 + up_ * h2 ]
        for k in range( 4 ):
            p, q = corners[k], corners[( k + 1 ) % 4]
            towards = unit( ( p + q ) / 2 - cc )
            card( m, "rv_zinc", [ p, q, q - out * edge, p - out * edge ], towards )


def screen( m, name, centre, right, h, up=UP, off=0.2 ):
    a = RM.aspect( RM.SCREENS, name )
    uv = [ RM.atlas_uv( RM.SCREENS, RM.SCREEN_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    quad( m, "rv_screens", centre, right, up, h * a, h, uv, off )


# ---------------------------------------------------------------------------------------------------------------------
# Light fixtures

LENS = { "warm": "rv_lamp_warm", "cool": "rv_lamp_cool", "cyan": "rv_lamp_cyan", "red": "rv_beacon" }
LAMP_COLOUR = { "warm": WARM, "cool": COOL, "cyan": CYAN, "red": RED }


def wall_light( m, name, at, out, kind="warm", radius=320, shadows=False, light=True, size=( 20, 7, 5 ) ):
    """ An LED wall pack on a wall facing out (plan): a die-cast body with cooling fins on its back, its front sloping
    in to a lit lens on the underside, a wire guard, a conduit up into a junction box, a point light a little out from
    it. Turned round if out points into this model's wall. """
    out = unit( ( out[0], out[1], 0.0 ) )
    at = v( *at )
    out, _ = _facing( m, at, out )
    right = np.cross( UP, out )
    L, D, H = size
    c = at + out * ( D / 2 )
    lens = LENS[kind]
    bevel_box( m, at + out * 0.2, ( right, out, UP ), ( L + 1.6, 0.4, H + 1.6 ), "rv_dark", 0.12, skip=( "-y", ) )
    prof = [ ( 0.4, -H / 2 + 0.6 ), ( 0.4, H / 2 ), ( D - 1.1, H / 2 ), ( D - 0.35, H / 2 - 0.6 ), ( D, H / 2 - 1.5 ), ( D, -H / 2 + 1.9 ),
             ( D * 0.5, -H / 2 ), ( 0.9, -H / 2 ) ]
    extrude( m, at - right * ( L / 2 ), at + right * ( L / 2 ), [ ( x, z ) for x, z in prof ],
             lambda j, e: lens if e == 5 else "rv_dark", up=UP, smooth=25, chamfer=1.2, cap_paint="rv_dark" )
    for k in range( 5 ):
        x = -L / 2 + L * ( k + 0.5 ) / 5
        obox( m, at + right * x + out * ( D * 0.42 ) + UP * ( H / 2 + 0.45 ), right, ( 0.25, D - 2.2, 0.9 ), "rv_dark" )
    # The wire guard round the lens.
    def P( o, z, x=0.0 ):
        return at + out * o + UP * z + right * x

    lens_a, lens_b = np.array( ( D, -H / 2 + 1.9 ) ), np.array( ( D * 0.5, -H / 2 ) )
    nrm = _unit2( np.array( ( lens_b[1] - lens_a[1], -( lens_b[0] - lens_a[0] ) ) ) )
    if float( np.dot( nrm, np.array( ( 1.0, -1.0 ) ) ) ) < 0:
        nrm = -nrm
    for f in ( 0.25, 0.75 ):
        q = lens_a + ( lens_b - lens_a ) * f + nrm * 0.7
        rod( m, P( q[0], q[1], -L / 2 + 1.2 ), P( q[0], q[1], L / 2 - 1.2 ), 0.16, "rv_dark", 4 )
    for x in ( -L / 2 + 1.5, 0.0, L / 2 - 1.5 ):
        q0, q1, q2 = lens_a + nrm * 0.1 + ( lens_a - lens_b ) * 0.08, lens_a + ( lens_b - lens_a ) * 0.5 + nrm * 0.75, lens_b + nrm * 0.1
        rod( m, P( q0[0], q0[1], x ), P( q1[0], q1[1], x ), 0.16, "rv_dark", 4 )
        rod( m, P( q1[0], q1[1], x ), P( q2[0], q2[1], x ), 0.16, "rv_dark", 4 )
    # Fed from above: a conduit up the wall into a junction box.
    cx = -L / 2 + 2.2
    rod( m, P( 1.1, H / 2, cx ), P( 1.1, H / 2 + 6.5, cx ), 0.45, "rv_zinc", 6 )
    bevel_box( m, P( 1.2, H / 2 + 8.0, cx ), ( right, out, UP ), ( 3.2, 2.0, 3.2 ), "rv_dark", 0.2, skip=( "-y", ) )
    if light:
        LIGHTS.append( ( name, tuple( c + out * 14 - UP * 10 ), LAMP_COLOUR[kind], radius, shadows ) )


def ceiling_light( m, name, at, along=( 1, 0 ), kind="cool", radius=900, shadows=False, size=( 48, 10, 4 ), light=True, hang=None ):
    """ An LED high-bay batten hanging under a ceiling: an extruded body with fins on its back, a lit lens underneath,
    two wires up to whatever is above it in this model (or hang inches, else 18). """
    along = unit( ( along[0], along[1], 0 ) )
    side = np.cross( UP, along )
    c = v( *at )
    L, W, H = size
    fins = 3 if W >= 8 else 2
    prof = [ ( -W / 2, -H / 2 ), ( W / 2, -H / 2 ), ( W / 2, -H / 2 + H * 0.45 ), ( W / 2 - 0.8, H / 2 ) ]
    for x in np.linspace( W / 2 - 2.0, -W / 2 + 2.0, fins ):
        prof += [ ( x + 0.2, H / 2 ), ( x + 0.2, H / 2 + 1.0 ), ( x - 0.2, H / 2 + 1.0 ), ( x - 0.2, H / 2 ) ]
    prof += [ ( -W / 2 + 0.8, H / 2 ), ( -W / 2, -H / 2 + H * 0.45 ) ]
    extrude( m, c - along * ( L / 2 ), c + along * ( L / 2 ), prof, "rv_dark", up=UP, smooth=20, chamfer=0.9 )
    lens = "rv_lamp_cool" if kind == "cool" else "rv_lamp_warm"
    p = c - UP * ( H / 2 + 0.05 )
    card( m, lens, [ p - along * ( L / 2 - 1.5 ) - side * ( W / 2 - 1.5 ), p + along * ( L / 2 - 1.5 ) - side * ( W / 2 - 1.5 ),
                     p + along * ( L / 2 - 1.5 ) + side * ( W / 2 - 1.5 ), p - along * ( L / 2 - 1.5 ) + side * ( W / 2 - 1.5 ) ], -UP )
    for f in ( -0.32, 0.32 ):
        q = c + along * ( L * f ) + UP * ( H / 2 + 1.0 )
        reach = hang if hang is not None else _ceiling_above( m, q )
        length = reach if reach is not None else 18.0
        rod( m, q - UP * 0.6, q + UP * 1.0, 0.32, "rv_zinc", 6 )
        rod( m, q + UP * 1.0, q + UP * length, 0.1, "rv_zinc", 4 )
        if reach is not None:
            rod( m, q + UP * ( length - 0.6 ), q + UP * length, 1.0, "rv_zinc", 6, caps=True )
    if light:
        LIGHTS.append( ( name, tuple( c - UP * 30 ), COOL if kind == "cool" else WARM, radius, shadows ) )


def beacon( m, name, at, light=True ):
    """ A rotating beacon: a fresnel-ribbed red dome on its base in a wire guard, on a base plate. """
    c = v( *at )
    z = c[2]
    obox( m, c + UP * 0.2, ( 1, 0 ), ( 6.2, 6.2, 0.4 ), { "default": "rv_dark", "-z": None } )
    lathe( m, c, [ ( 2.9, z + 0.4 ), ( 2.9, z + 0.9 ), ( 2.6, z + 1.25 ), ( 2.6, z + 2.1 ), ( 2.3, z + 2.35 ) ], "rv_dark", 10 )
    lathe( m, c, [ ( 2.3, z + 2.35 ), ( 2.25, z + 3.15 ), ( 2.12, z + 3.35 ), ( 2.2, z + 4.15 ), ( 2.05, z + 4.35 ), ( 2.1, z + 5.1 ),
                   ( 1.8, z + 6.1 ), ( 1.1, z + 6.85 ), ( 0.0, z + 7.1 ) ], "rv_beacon", 10 )
    for k in range( 2 ):
        a = math.pi / 2 * k + math.pi / 4
        d = v( math.cos( a ), math.sin( a ), 0.0 )
        bow = [ c + d * ( 2.75 * math.cos( t ) ) + UP * ( 2.3 + 5.4 * math.sin( t ) ) for t in np.linspace( 0, math.pi, 7 ) ]
        _sweep( m, bow, 0.14, "rv_dark", 3, caps=False )
    torus( m, c + UP * 4.8, UP, 2.62, 0.14, "rv_dark", seg=8, sides=3 )
    if light:
        LIGHTS.append( ( name, tuple( c + UP * 8 ), RED, 90, False ) )


# ---------------------------------------------------------------------------------------------------------------------
# Openings: louvres and doors

def louvre( m, centre, right, w, h, depth=6.0, blades=None, frame="rv_frame", blade="rv_louvre", mount="auto" ):
    """ A louvred vent: drainable blades (front edge low, a drip in front and an upturned back) in a channel frame,
    mullions every 4 ft on wide ones, a dark bird screen behind. Set into an opening ('recessed', a void depth deep), or
    on a solid wall's face ('surface', its frame 4 in proud); 'auto' asks this model's collision, then whether it draws
    a wall face there. """
    right = unit( right )
    out = np.cross( right, UP )
    c = v( *centre )
    out, right = _facing( m, c, out, right )
    if mount == "auto":
        mount = "surface" if ( _solid( m, c - out * 1.5 ) or _drawn_face( m, c, out ) ) else "recessed"
    n = blades or max( 4, int( h / 4.5 ) )
    pitch = h / n
    axes = ( right, out, UP )

    def P( x, o, z ):
        return c + right * x + out * o + UP * z

    t = 2.5
    if mount == "surface":
        D = 4.0
        quad( m, "rv_black", P( 0, 0.06, 0 ), right, UP, w, h )
        o_front, o_back = D - 0.6, 0.5
        for sg in ( -1, 1 ):
            bevel_box( m, P( sg * ( w / 2 + t / 2 ), D / 2, 0 ), axes, ( t, D, h + 2 * t ), frame, 0.3, skip=( "-y", ) )
            bevel_box( m, P( 0, D / 2, sg * ( h / 2 + t / 2 ) ), axes, ( w, D, t ), frame, 0.3, skip=( "-y", ) )
    else:
        quad( m, "rv_black", c - out * depth, right, UP, w, h )
        for sg in ( -1, 1 ):
            p = c + right * ( w / 2 ) * sg
            card( m, frame, [ p - UP * h / 2, p - UP * h / 2 - out * depth, p + UP * h / 2 - out * depth, p + UP * h / 2 ], -right * sg )
            p = c + UP * ( h / 2 ) * sg
            card( m, frame, [ p - right * w / 2, p - right * w / 2 - out * depth, p + right * w / 2 - out * depth, p + right * w / 2 ], -UP * sg )
        o_front, o_back = -0.4, -depth * 0.75
        for sg in ( -1, 1 ):
            bevel_box( m, P( sg * ( w / 2 + t / 2 ), 0.3, 0 ), axes, ( t, 0.6, h + 2 * t ), frame, 0.15, skip=( "-y", ) )
            bevel_box( m, P( 0, 0.3, sg * ( h / 2 + t / 2 ) ), axes, ( w, 0.6, t ), frame, 0.15, skip=( "-y", ) )
    if w > 72:
        count = int( round( w / 48.0 ) )
        for i in range( 1, count ):
            x = -w / 2 + w * i / count
            bevel_box( m, P( x, ( o_front + o_back ) / 2 + 0.2, 0 ), axes, ( 2.0, o_front - o_back + 0.6, h ), frame, 0.25 )
    drip, lip = min( 0.6, pitch * 0.15 ), min( 0.5, pitch * 0.12 )
    for i in range( n ):
        zc = -h / 2 + pitch * ( i + 0.5 )
        zf, zb = zc - pitch * 0.42, zc + pitch * 0.42
        prof = [ ( o_front, zf - drip ), ( o_front, zf ), ( o_back, zb ), ( o_back, zb + lip ) ]
        Lp = [ P( -w / 2, o, z ) for o, z in prof ]
        Rp = [ P( w / 2, o, z ) for o, z in prof ]
        for k in range( 3 ):
            card( m, blade, [ Lp[k], Rp[k], Rp[k + 1], Lp[k + 1] ], out + UP, both=True )


def _leaf( m, hinge, along, front, lw, h, paint, window, hardware, open_, sign, big ):
    """ One door leaf from its hinge edge (hinge: the bottom of that edge on the leaf's front face), along to its lock
    edge, front its face's normal: the slab, a vision lite in a glazing bead, a kick plate, hinges, a lever and lock (or
    a pull on a big door), an overhead closer, a number plate or a sign. """
    def P( x, y, z ):
        return hinge + along * x + front * y + UP * z

    bevel_box( m, P( lw / 2, -0.875, h / 2 ), ( along, front, UP ), ( lw, 1.75, h ), paint, 0.12 )
    if window:
        lite_w, lite_h = min( lw * 0.28, 9.0 ), min( 24.0, h * 0.26 )
        cz = h * 0.68
        quad( m, "rv_window_dark", P( lw / 2, 0.03, cz ), along, UP, lite_w, lite_h )
        for x, z, sx, sz in ( ( lw / 2, cz - lite_h / 2 - 0.35, lite_w + 1.4, 0.7 ), ( lw / 2, cz + lite_h / 2 + 0.35, lite_w + 1.4, 0.7 ),
                              ( lw / 2 - lite_w / 2 - 0.35, cz, 0.7, lite_h ), ( lw / 2 + lite_w / 2 + 0.35, cz, 0.7, lite_h ) ):
            _box3( m, P( x, 0.18, z ), ( along, front, UP ), ( sx, 0.36, sz ), { "default": paint, "-y": None } )
    _box3( m, P( lw / 2, 0.04, 5.6 ), ( along, front, UP ), ( lw - 1.6, 0.08, 10.0 ), { "default": hardware, "-y": None } )
    for z in ( 9.0, h / 2 + 2.0, h - 11.0 ):
        rod( m, P( -0.05, 0.25, z ), P( -0.05, 0.25, z + 4.5 ), 0.32, hardware, 6, caps=True )
    if big:
        for z in ( h * 0.36, h * 0.36 + 22.0 ):
            rod( m, P( lw - 4.0, 0.0, z ), P( lw - 4.0, 2.4, z ), 0.35, hardware, 6 )
        rod( m, P( lw - 4.0, 2.4, h * 0.36 - 0.6 ), P( lw - 4.0, 2.4, h * 0.36 + 22.6 ), 0.6, hardware, 8, caps=True )
    else:
        esc = P( lw - 3.0, 0.0, 40.0 )
        _box3( m, esc + front * 0.12, ( along, front, UP ), ( 1.8, 0.24, 7.0 ), { "default": hardware, "-y": None } )
        tube( m, [ esc + front * 0.2 + UP * 1.6, esc + front * 2.0 + UP * 1.6, esc + front * 2.0 - along * 4.4 + UP * 1.6 ], 0.36,
              hardware, 6, bend_radius=0.8 )
        rod( m, esc - UP * 2.2, esc - UP * 2.2 + front * 0.45, 0.5, hardware, 8, caps=True )
    if not open_:
        body = P( 6.5, 1.0, h - 3.2 )
        bevel_box( m, body, ( along, front, UP ), ( 10.5, 2.0, 2.4 ), "rv_dark", 0.3 )
        elbow = P( 15.5, 2.4, h - 2.2 )
        rod( m, P( 10.5, 2.0, h - 3.0 ), elbow, 0.28, "rv_dark", 5 )
        rod( m, elbow, P( 13.0, 1.0, h + 1.0 ), 0.28, "rv_dark", 5 )
    if sign:
        plate( m, sign, P( lw / 2, 0.0, min( 60.0, h * 0.62 ) ), np.cross( UP, front ), 10.0, off=0.12, edge=0.0 )
    elif sign is None:
        _box3( m, P( lw / 2, 0.04, min( 62.0, h * 0.64 ) ), ( along, front, UP ), ( 5.0, 0.08, 1.8 ), { "default": hardware, "-y": None } )


def door( m, centre, right, w=96.0, h=96.0, paint="rv_door", frame="rv_frame", window=True, double=True, recess=4.0,
          mount="auto", sign=None, hardware="rv_zinc" ):
    """ A steel door (double or single), centre at the foot of the wall face, right along the wall. A steel frame and
    an architrave on the wall face, leaves with a vision lite, hinges, lever and lock, kick plate, closer, a number plate
    (or sign: an rv_plates atlas name; False for none), a threshold. Drawn only.

    Set back recess in its opening ('recessed'), or on a solid wall's face ('surface'); 'auto' asks this model's
    collision, then whether it draws a wall face there. In a through opening of this model's own wall the leaves stand open, swung in, since players walk through
    those; where the wall isn't in this model it stays shut with reveals back to the wall face. """
    right = unit( right )
    out = np.cross( right, UP )
    base = v( *centre )
    out, right = _facing( m, base + UP * ( h / 2 ), out, right )
    mid = base + UP * ( h / 2 )
    if mount == "auto":
        mount = "surface" if ( _solid( m, mid - out * 1.5 ) or _drawn_face( m, mid, out ) ) else "recessed"
    wall = _depth( m, base + right * ( w / 2 + 6 ) + UP * ( h / 2 ), out ) if mount == "recessed" else None
    open_ = mount == "recessed" and wall is not None
    fw = 2.0
    leaves = 2 if double else 1
    lw = w / leaves - 0.25
    big = h >= 120
    axes = ( right, out, UP )

    def P( x, o, z ):
        return base + right * x + out * o + UP * z

    if mount == "surface":
        o_leaf = 1.95                       # the leaves' front face
        f0, f1 = 0.0, 3.0                   # the frame, out from the wall
        skip = ( "-y", )
    else:
        o_leaf = -recess
        f0, f1 = -recess - 2.0, -recess + 2.5
        skip = ()
    fc, fd = ( f0 + f1 ) / 2, f1 - f0
    for sg in ( -1, 1 ):
        bevel_box( m, P( sg * ( w / 2 + fw / 2 ), fc, ( h + fw ) / 2 ), axes, ( fw, fd, h + fw ), frame, 0.25, skip=skip )
    bevel_box( m, P( 0, fc, h + fw / 2 ), axes, ( w + 2 * fw, fd, fw ), frame, 0.25, skip=skip )
    if mount == "recessed":
        for sg in ( -1, 1 ):
            bevel_box( m, P( sg * ( w / 2 + fw + 1.5 ), 0.3, ( h + fw + 3 ) / 2 ), axes, ( 3.0, 0.6, h + fw + 3 ), frame, 0.2, skip=( "-y", ) )
        bevel_box( m, P( 0, 0.3, h + fw + 1.5 ), axes, ( w + 2 * fw + 6, 0.6, 3.0 ), frame, 0.2, skip=( "-y", ) )
        _box3( m, P( 0, f0 + fd / 2 + 0.5, 0.22 ), axes, ( w + 2 * fw, fd + 1.0, 0.44 ), { "default": hardware, "-z": None } )
        if wall is None:
            # Reveals back to the wall face.
            for sg in ( -1, 1 ):
                p = base - out * recess + right * ( w / 2 + 3 ) * sg
                card( m, "rv_plinth", [ p, p + out * recess, p + out * recess + UP * ( h + 3 ), p + UP * ( h + 3 ) ], -right * sg )
            p = base - out * recess + UP * ( h + 3 )
            card( m, "rv_plinth", [ p - right * ( w / 2 + 3 ), p + right * ( w / 2 + 3 ), p + right * ( w / 2 + 3 ) + out * recess,
                                    p - right * ( w / 2 + 3 ) + out * recess ], -UP )
    else:
        _box3( m, P( 0, 2.0, 0.22 ), axes, ( w + 2 * fw + 2, 4.0, 0.44 ), { "default": hardware, "-z": None } )
    for i in range( leaves ):
        left = i == 0
        along = right if left else -right
        hx = -w / 2 + 0.12 if left else w / 2 - 0.12
        if open_:
            # Swung in through 90 degrees about the hinge: it now runs back into the room beside its jamb.
            hinge = P( hx, o_leaf - 1.75, 0.4 )
            _leaf( m, hinge + along * 1.75, -out, along, lw, h - 0.6, paint, window, hardware, True, False, big )
        else:
            _leaf( m, P( hx, o_leaf, 0.4 ), along, out, lw, h - 0.6, paint, window, hardware, False, sign if left else False, big )
    if double and not open_:
        _box3( m, P( 0, o_leaf + 0.15, h / 2 ), axes, ( 1.5, 0.3, h - 1.0 ), { "default": paint, "-y": None } )


# ---------------------------------------------------------------------------------------------------------------------
# Small things

def bollard( m, e, n, h=40.0 ):
    """ A steel bollard: a concrete-filled pipe with a domed cap and two reflective bands, on an anchored base plate.
    Collides as the plain cylinder it always was. """
    c0 = v( e, n, 0.0 )
    dirs = [ v( math.cos( 2 * math.pi * k / 10 ), math.sin( 2 * math.pi * k / 10 ), 0.0 ) for k in range( 10 ) ]
    m.hull( [ c0 + d * 3.5 + UP * z for d in dirs for z in ( 0.0, h ) ], METAL )
    bevel_box( m, c0 + UP * 0.375, ( ( 1, 0, 0 ), ( 0, 1, 0 ), UP ), ( 10.0, 10.0, 0.75 ), "rv_zinc", 0.15, skip=( "-z", ) )
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            q = c0 + v( sx * 3.6, sy * 3.6, 0.75 )
            rod( m, q, q + UP * 0.55, 0.45, "rv_zinc", 6, caps=True )
            rod( m, q, q + UP * 1.0, 0.22, "rv_zinc", 5, caps=True )
    w, y, R = "rv_ring_white", "rv_yellow", 3.3
    prof = [ ( R, 0.75 ), ( R, h - 13.5 ), ( R + 0.03, h - 13.5 ), ( R + 0.03, h - 10.5 ), ( R, h - 10.5 ), ( R, h - 7.5 ), ( R + 0.03, h - 7.5 ),
             ( R + 0.03, h - 4.5 ), ( R, h - 4.5 ), ( R, h - 2.2 ), ( R * 0.93, h - 0.9 ), ( R * 0.7, h - 0.15 ), ( R * 0.3, h + 0.05 ), ( 0.0, h + 0.1 ) ]
    paints = [ y, y, w, y, y, y, w, y, y, y, y, y, y ]
    lathe( m, ( e, n ), prof, paints, 12 )


def life_ring( m, at, out, sign=False ):
    """ A life ring hung on its hook on a wall facing out: an orange ring with four white bands and its grab line
    festooned round it; sign puts the life ring sign over it. """
    out = unit( ( out[0], out[1], 0 ) )
    at = v( *at )
    out, _ = _facing( m, at, out )
    right = np.cross( UP, out )
    c = at + out * 3
    R, r = 11.0, 2.4
    torus( m, c, out, R, r, lambda i: "rv_ring_orange" if ( i // 2 ) % 2 == 0 else "rv_ring_white", seg=16, sides=8, basis=( right, UP ) )
    # The grab line: fixed at four points, hanging in loops between.
    for k in range( 4 ):
        a0, a1 = math.pi / 4 + math.pi / 2 * k, math.pi / 4 + math.pi / 2 * ( k + 1 )
        pts = []
        for f in np.linspace( 0, 1, 7 ):
            a = a0 + ( a1 - a0 ) * f
            sag = 1.6 * math.sin( math.pi * f )
            rho = right * math.cos( a ) + UP * math.sin( a )
            pts.append( c + rho * ( R + r + 0.35 + sag ) - UP * ( sag * 0.6 ) )
        _sweep( m, pts, 0.32, "rv_rope", 5, caps=False )
    # The hook: a plate on the wall, a bar out through the ring's hole, turned up at its tip.
    bevel_box( m, at + out * 0.2 + UP * 10.5, ( right, out, UP ), ( 4.0, 0.4, 5.0 ), "rv_frame", 0.1, skip=( "-y", ) )
    tube( m, [ at + out * 0.4 + UP * 9.0, at + out * 5.6 + UP * 9.0, at + out * 5.6 + UP * 11.0 ], 0.45, "rv_frame", 6, bend_radius=0.8 )
    if sign:
        plate( m, "lifering_sign", at + UP * ( R + 16 ), right, 10.0, off=0.3 )


def truss( m, a, b, depth, paint="rv_steel", chord=3.0, web=1.5, up=UP, panel=None ):
    """ A flat Warren truss from a to b, depth in direction up: chords of two angles back to back (outstanding legs flat
    on the outside), angle webs zig-zagging between them on gusset plates. Drawn only. """
    a, b = v( *a ), v( *b )
    up = unit( up )
    L = float( np.linalg.norm( b - a ) )
    d = ( b - a ) / L
    upn = unit( up - d * float( np.dot( up, d ) ) )
    g = 0.5
    t = max( 0.3, chord * 0.12 )
    lh = chord * 1.1
    for line, flat_top in ( ( 0.0, False ), ( depth, True ) ):
        for sg in ( -1, 1 ):
            ys, yf = ( -chord, chord ) if flat_top else ( chord, -chord )
            if flat_top:
                prof = [ ( g, ys ), ( g + t, ys ), ( g + t, yf - t ), ( g + lh, yf - t ), ( g + lh, yf ), ( g, yf ) ]
            else:
                prof = [ ( g, ys ), ( g, yf ), ( g + lh, yf ), ( g + lh, yf + t ), ( g + t, yf + t ), ( g + t, ys ) ]
            prof = [ ( sg * x, y ) for x, y in prof ]
            extrude( m, a + upn * line, b + upn * line, prof, paint, up=upn, smooth=0 )
    p = panel or depth
    count = max( 1, int( round( L / p ) ) )
    side = np.cross( d, upn )
    wl = web * 2.0
    tw = max( 0.25, web * 0.17 )
    web_prof = [ ( x, y + g * 0.9 ) for x, y in ( ( -wl / 2, 0.0 ), ( wl / 2, 0.0 ), ( wl / 2, tw ), ( -wl / 2 + tw, tw ), ( -wl / 2 + tw, wl ),
                                                   ( -wl / 2, wl ) ) ]
    for i in range( count ):
        p0 = a + d * ( L * i / count )
        p1 = a + d * ( L * ( i + 0.5 ) / count ) + upn * depth
        p2 = a + d * ( L * ( i + 1 ) / count )
        for q0, q1 in ( ( p0, p1 ), ( p1, p2 ) ):
            wa = unit( q1 - q0 )
            extrude( m, q0 + wa * chord * 0.6, q1 - wa * chord * 0.6, web_prof, paint, up=side, smooth=0 )
    gw = min( p * 0.3, 14.0 )
    for i in range( count + 1 ):
        q = a + d * ( L * i / count )
        _box3( m, q + upn * ( chord * 1.4 ), ( d, side, upn ), ( gw, g * 1.8, chord * 2.4 ), paint )
        if i < count:
            q = a + d * ( L * ( i + 0.5 ) / count ) + upn * depth
            _box3( m, q - upn * ( chord * 1.4 ), ( d, side, upn ), ( gw, g * 1.8, chord * 2.4 ), paint )


def i_beam( m, a, b, h, w, paint="rv_steel", web=0.8, flange=1.0, surface=None ):
    """ An I-section from a to b (level or not), h deep (vertical when level), w wide, with root fillets. surface makes
    its web solid, as before. """
    a, b = v( *a ), v( *b )
    d = unit( b - a )
    side = unit( np.cross( UP, d ) ) if abs( d[2] ) < 0.99 else v( 1, 0, 0 )
    upv = np.cross( d, side )
    L = float( np.linalg.norm( b - a ) )
    mid = ( a + b ) / 2
    if surface:
        m.oriented_box( mid, ( d, side, upv ), ( L, web, h - 2 * flange ), { "default": None }, surface )
    k = min( 0.5, flange * 0.6, ( w - web ) / 4 )
    hw, hh, ht = w / 2, h / 2, web / 2
    prof = [ ( -hw, -hh ), ( hw, -hh ), ( hw, -hh + flange ), ( ht + k, -hh + flange ), ( ht, -hh + flange + k ), ( ht, hh - flange - k ),
             ( ht + k, hh - flange ), ( hw, hh - flange ), ( hw, hh ), ( -hw, hh ), ( -hw, hh - flange ), ( -ht - k, hh - flange ),
             ( -ht, hh - flange - k ), ( -ht, -hh + flange + k ), ( -ht - k, -hh + flange ), ( -hw, -hh + flange ) ]
    extrude( m, a, b, prof, paint, up=upv, smooth=0, chamfer=k * 1.5 )


def cable_tray( m, a, b, w=18.0, paint="rv_zinc" ):
    """ A ladder-type cable tray from a to b (its floor), w wide: channel side rails 4 in deep, rungs every 12 in,
    cables laid on them. """
    a, b = v( *a ), v( *b )
    d = unit( b - a )
    side = unit( np.cross( UP, d ) )
    L = float( np.linalg.norm( b - a ) )
    for sg in ( -1, 1 ):
        prof = [ ( 0.1, 0.0 ), ( 0.1, 4.0 ), ( -1.2, 4.0 ), ( -1.2, 3.85 ), ( -0.05, 3.85 ), ( -0.05, 0.15 ), ( -1.2, 0.15 ), ( -1.2, 0.0 ) ]
        # extrude's x runs right of the tray (-side): this rail's outside is towards side * sg.
        prof = [ ( -sg * ( w / 2 + x ), y ) for x, y in prof ]
        extrude( m, a, b, prof, paint, up=UP, smooth=0 )
    for s in np.arange( 6.0, L, 12.0 ):
        _box3( m, a + d * s + UP * 0.3, ( d, side, UP ), ( 1.0, w - 0.4, 0.6 ), paint )
    rng = np.random.default_rng( zlib.crc32( f"{a[0]:.0f},{a[1]:.0f},{b[0]:.0f}".encode() ) )
    x = -w / 2 + 1.6
    while x < w / 2 - 1.6:
        rr = float( rng.uniform( 0.5, 1.15 ) )
        rod( m, a + side * ( x + rr ) + UP * ( 0.6 + rr ), b + side * ( x + rr ) + UP * ( 0.6 + rr ), rr, "rv_black", 5 )
        x += 2 * rr + float( rng.uniform( 0.1, 0.6 ) )


# ---------------------------------------------------------------------------------------------------------------------
# New helpers: dressing to place anywhere (drawn only unless surface is given)

def drum( m, c, z0=0.0, paint="rv_drum_blue", surface=None ):
    """ A 205 l (55 gal) tight-head steel drum: 22.5 in across, 34.8 in tall, rolled chimes, two rolling hoops, a
    recessed lid with its two bungs. paint: rv_drum_blue or rv_drum_red (this module's), or any. """
    C = v( c[0], c[1], 0.0 )
    z = z0
    prof = [ ( 11.0, z ), ( 11.35, z + 0.35 ), ( 11.35, z + 0.9 ), ( 11.1, z + 1.3 ), ( 11.1, z + 10.9 ), ( 11.5, z + 11.3 ), ( 11.5, z + 12.0 ),
             ( 11.1, z + 12.4 ), ( 11.1, z + 22.4 ), ( 11.5, z + 22.8 ), ( 11.5, z + 23.5 ), ( 11.1, z + 23.9 ), ( 11.1, z + 33.5 ),
             ( 11.4, z + 33.9 ), ( 11.4, z + 34.6 ), ( 11.1, z + 34.8 ), ( 10.85, z + 34.6 ), ( 10.85, z + 34.1 ), ( 0.0, z + 34.1 ) ]
    lathe( m, c, prof, paint, 14 )
    for dx, dy, rb in ( ( 6.6, 0.0, 1.25 ), ( -6.6, 1.2, 0.65 ) ):
        q = C + v( dx, dy, z + 34.1 )
        lathe( m, ( q[0], q[1] ), [ ( rb, z + 34.1 ), ( rb, z + 34.5 ), ( rb * 0.8, z + 34.6 ) ], "rv_zinc", 6, cap="rv_zinc" )
    if surface:
        m.hull( [ C + v( math.cos( 2 * math.pi * k / 14 ) * 11.4, math.sin( 2 * math.pi * k / 14 ) * 11.4, zz ) for k in range( 14 )
                  for zz in ( z, z + 34.8 ) ], surface )


def pallet( m, c, along=( 1, 0 ), z0=0.0, paint="rv_pallet_wood", surface=None, seed=0 ):
    """ A Euro pallet (1200 x 800 x 144 mm): three bottom boards, nine blocks, three cross boards and five top boards
    along it, each a little out of true. """
    X = unit( ( along[0], along[1], 0.0 ) )
    Y = np.cross( UP, X )
    o = v( c[0], c[1], z0 )
    Lx, Wy, t, blk = 47.24, 31.5, 0.87, 3.07
    rng = np.random.default_rng( seed )
    m.grain_paints.add( paint )

    def board( x, y, z, sx, sy, sz ):
        j = rng.normal( 0, 0.08, 2 )
        yaw = float( rng.normal( 0, 0.004 ) )
        Xr = X * math.cos( yaw ) + Y * math.sin( yaw )
        obox( m, o + X * ( x + j[0] ) + Y * ( y + j[1] ) + UP * ( z + sz / 2 ), Xr, ( sx, sy, sz ), paint )

    rows = ( ( -Wy / 2 + 1.97, 3.94 ), ( 0.0, 5.71 ), ( Wy / 2 - 1.97, 3.94 ) )
    for y, wd in rows:
        board( 0.0, y, 0.0, Lx, wd, t )
    for x in ( -Lx / 2 + 2.855, 0.0, Lx / 2 - 2.855 ):
        for y, wd in rows:
            board( x, y, t, 5.71, wd, blk )
        board( x, 0.0, t + blk, 5.71, Wy, t )
    for y, wd in ( ( -12.895, 5.71 ), ( -6.45, 3.94 ), ( 0.0, 5.71 ), ( 6.45, 3.94 ), ( 12.895, 5.71 ) ):
        board( 0.0, y, 2 * t + blk, Lx, wd, t )
    if surface:
        obox( m, o + UP * ( ( 3 * t + blk ) / 2 ), X, ( Lx, Wy, 3 * t + blk ), { "default": None }, surface )


def cable_reel( m, c, along=( 1, 0 ), size=( 40.0, 30.0 ), z0=0.0, paint="rv_pallet_wood", cable="rv_rubber", surface=None ):
    """ A wooden cable drum standing on its flanges (size: across, wide): plywood flanges, the barrel wound with cable
    and its loose end, tie rods through. along is its axle. """
    D, W = size
    R = D / 2
    X = unit( ( along[0], along[1], 0.0 ) )
    Y = np.cross( UP, X )
    centre = v( c[0], c[1], z0 + R )
    for sg in ( -1, 1 ):
        lathe_axis( m, centre + X * ( sg * ( W / 2 - 0.8 ) ), X * sg,
                    [ ( 2.0, -0.8 ), ( R - 0.6, -0.8 ), ( R, -0.35 ), ( R, 0.35 ), ( R - 0.6, 0.8 ), ( 2.0, 0.8 ), ( 2.0, -0.8 ) ], paint, 24 )
    rc = R * 0.78
    wb = W / 2 - 1.6
    prof = [ ( rc - ( 0.35 if k % 2 else 0.0 ), -wb + 2 * wb * k / 6 ) for k in range( 7 ) ]
    lathe_axis( m, centre, X, prof, cable, 14 )
    for k in range( 4 ):
        a = math.pi / 4 + math.pi / 2 * k
        q = centre + ( Y * math.cos( a ) + UP * math.sin( a ) ) * ( R * 0.55 )
        rod( m, q - X * ( W / 2 + 0.6 ), q + X * ( W / 2 + 0.6 ), 0.4, "rv_zinc", 6, caps=True )
    end = centre + Y * rc * 0.2 + UP * rc
    tube( m, [ end, end + Y * 6 + UP * 1.5, end + Y * 14 - UP * ( R * 0.6 ), v( end[0], end[1], z0 ) + Y * 20 + UP * 0.6,
               v( end[0], end[1], z0 ) + Y * 34 + X * 4 + UP * 0.6 ], 0.6, cable, 6, bend_radius=4.0 )
    if surface:
        m.hull( [ centre + X * ( sg * W / 2 ) + ( Y * math.cos( 2 * math.pi * k / 12 ) + UP * math.sin( 2 * math.pi * k / 12 ) ) * R
                  for sg in ( -1, 1 ) for k in range( 12 ) ], surface )


def extinguisher( m, at, out, cabinet=True, paint="rv_red" ):
    """ A 6 kg powder extinguisher on a wall at at (the wall's face, at the floor) facing out: a red body with its
    label band, a valve head with lever, gauge and hose, on a bracket or in a red steel cabinet with a glazed door. """
    out = unit( ( out[0], out[1], 0.0 ) )
    at = v( *at )
    out, _ = _facing( m, at + UP * 36, out )
    right = np.cross( UP, out )
    zb = 24.0 if cabinet else 32.0
    E = at + out * 4.2 + UP * zb
    prof = [ ( 2.4, 0.0 ), ( 2.95, 0.5 ), ( 3.0, 1.0 ), ( 3.0, 5.0 ), ( 3.03, 5.0 ), ( 3.03, 11.0 ), ( 3.0, 11.0 ), ( 3.0, 15.0 ), ( 2.85, 16.4 ),
             ( 2.2, 17.4 ), ( 1.2, 17.9 ), ( 0.85, 18.0 ), ( 0.85, 18.8 ), ( 0.0, 18.8 ) ]
    bands = [ paint ] * 3 + [ paint, "rv_ring_white" ] + [ paint ] * 8
    lathe( m, ( E[0], E[1] ), [ ( r_, z + E[2] ) for r_, z in prof ], bands, 12 )
    head = E + UP * 19.6
    bevel_box( m, head, ( right, out, UP ), ( 2.6, 1.6, 1.6 ), "rv_dark", 0.2 )
    tube( m, [ head + UP * 0.8 - right * 0.6, head + UP * 2.2 + right * 1.6, head + UP * 1.6 + right * 4.2 ], 0.3, "rv_zinc", 4, bend_radius=1.0 )
    rod( m, head + out * 0.8 + right * 0.6, head + out * 1.2 + right * 0.6, 0.65, "rv_zinc", 8, caps=True )
    tube( m, [ head - right * 1.3, head - right * 2.6 - UP * 1.5, E - right * 3.4 + out * 1.0 + UP * 8.0, E - right * 3.4 + out * 1.6 + UP * 3.0 ],
          0.4, "rv_black", 6, bend_radius=1.6 )
    rod( m, E - right * 3.4 + out * 1.6 + UP * 3.0, E - right * 3.4 + out * 1.6 + UP * 0.4, 0.6, "rv_black", 6, caps=True )
    if cabinet:
        Wc, Dc, Hc = 12.0, 8.5, 27.0
        cb = at + UP * ( zb - 2.0 )
        axes = ( right, out, UP )

        def C( x, o, z ):
            return cb + right * x + out * o + UP * z

        bevel_box( m, C( 0, 0.15, Hc / 2 ), axes, ( Wc, 0.3, Hc ), paint, 0.1, skip=( "-y", ) )
        for sg in ( -1, 1 ):
            bevel_box( m, C( sg * ( Wc / 2 - 0.25 ), Dc / 2, Hc / 2 ), axes, ( 0.5, Dc, Hc ), paint, 0.15 )
            bevel_box( m, C( 0, Dc / 2, Hc / 2 + sg * ( Hc / 2 - 0.25 ) ), axes, ( Wc, Dc, 0.5 ), paint, 0.15 )
            bevel_box( m, C( sg * ( Wc / 2 - 0.9 ), Dc + 0.3, Hc / 2 ), axes, ( 1.8, 0.6, Hc ), paint, 0.15 )
            bevel_box( m, C( 0, Dc + 0.3, Hc / 2 + sg * ( Hc / 2 - 0.9 ) ), axes, ( Wc - 3.6, 0.6, 1.8 ), paint, 0.15 )
        quad( m, "rw_glass", C( 0, Dc + 0.1, Hc / 2 ), right, UP, Wc - 3.4, Hc - 3.4 )
        quad( m, "rw_glass", C( 0, Dc + 0.1, Hc / 2 ), -right, UP, Wc - 3.4, Hc - 3.4 )
        rod( m, C( Wc / 2 - 1.2, Dc + 0.6, Hc / 2 - 2 ), C( Wc / 2 - 1.2, Dc + 1.6, Hc / 2 - 2 ), 0.35, "rv_zinc", 6, caps=True )
    else:
        bevel_box( m, at + out * 0.3 + UP * ( zb + 12 ), ( right, out, UP ), ( 3.0, 0.6, 6.0 ), "rv_dark", 0.15, skip=( "-y", ) )
        rod( m, at + out * 0.6 + UP * ( zb + 13 ), E + UP * 13 - out * 2.6, 0.4, "rv_dark", 6 )


def electrical_box( m, at, out, size=( 16.0, 8.0, 20.0 ), paint="rv_enclosure", label=True, conduits=2 ):
    """ A wall-mounted steel enclosure, at its back's middle on the wall facing out: its door's gap, two hinges, a
    quarter-turn handle, a warning label, conduits down out of its bottom. """
    out = unit( ( out[0], out[1], 0.0 ) )
    at = v( *at )
    out, _ = _facing( m, at, out )
    right = np.cross( UP, out )
    W, D, H = size
    axes = ( right, out, UP )
    bevel_box( m, at + out * ( D / 2 ), axes, ( W, D, H ), paint, 0.35, skip=( "-y", ) )
    f = at + out * ( D + 0.02 )
    for x0, z0_, x1, z1 in ( ( -W / 2 + 0.7, -H / 2 + 0.7, W / 2 - 0.7, -H / 2 + 0.85 ), ( -W / 2 + 0.7, H / 2 - 0.85, W / 2 - 0.7, H / 2 - 0.7 ),
                             ( -W / 2 + 0.7, -H / 2 + 0.7, -W / 2 + 0.85, H / 2 - 0.7 ), ( W / 2 - 0.85, -H / 2 + 0.7, W / 2 - 0.7, H / 2 - 0.7 ) ):
        card( m, "rv_dark", [ f + right * x0 + UP * z0_, f + right * x1 + UP * z0_, f + right * x1 + UP * z1, f + right * x0 + UP * z1 ], out )
    for z in ( -H / 2 + 3.5, H / 2 - 3.5 ):
        rod( m, f + right * ( -W / 2 + 0.3 ) + UP * ( z - 1.2 ), f + right * ( -W / 2 + 0.3 ) + UP * ( z + 1.2 ), 0.3, "rv_dark", 6, caps=True )
    hp = f + right * ( W / 2 - 2.2 )
    lathe_axis( m, hp, out, [ ( 0.9, 0.0 ), ( 0.9, 0.4 ), ( 0.7, 0.55 ), ( 0.0, 0.55 ) ], "rv_dark", 8 )
    bevel_box( m, hp + out * 0.9, ( right, out, UP ), ( 0.5, 0.8, 2.4 ), "rv_dark", 0.12 )
    if label:
        plate( m, "danger", f + UP * ( H / 2 - 4.0 ), right, 3.4, off=0.05, edge=0.0 )
    for k in range( conduits ):
        x = -W / 2 + W * ( k + 1 ) / ( conduits + 1 )
        p = at + right * x + out * ( D * 0.4 ) - UP * ( H / 2 )
        lathe_axis( m, p - UP * 1.4, UP, [ ( 0.85, 0.0 ), ( 0.85, 1.4 ) ], "rv_zinc", 8 )
        # Down, then back into the wall through an elbow.
        tube( m, [ p - UP * 1.4, p - UP * ( 6.0 + 2.5 * k ), at + right * x - UP * ( H / 2 + 6.0 + 2.5 * k ) - out * 0.5 ], 0.6, "rv_zinc", 6,
              bend_radius=2.4, caps=False )


def conduit( m, pts, r=0.6, paint="rv_zinc", clamps=30.0, wall=None, sides=6 ):
    """ A conduit run along pts, bent on arcs of 4 x r (3 in at least), couplings every 10 ft; with wall (the way from it
    to the wall it's fixed to) a one-hole strap every clamps inches. """
    path = _bend_points( pts, max( 3.0, 4 * r ), max_step=22.5 )
    _sweep( m, path, r, paint, sides )
    for a, b in zip( path, path[1:] ):
        L = float( np.linalg.norm( b - a ) )
        if L < 6.0:
            continue
        d = ( b - a ) / L
        for s in np.arange( 60.0, L - 6.0, 120.0 ):
            q = a + d * s
            _sweep( m, [ q - d * 0.7, q + d * 0.7 ], r + 0.14, paint, sides, caps=False )
        if wall is not None:
            wv = unit( v( *wall ) - d * float( np.dot( v( *wall ), d ) ) )
            for s in np.arange( clamps * 0.5, L, clamps ):
                q = a + d * s
                torus( m, q, d, r + 0.12, 0.12, paint, seg=6, sides=3, a0=0.0, a1=math.pi, basis=( np.cross( d, wv ), -wv ) )
                _box3( m, q + wv * ( r - 0.06 ) + np.cross( d, wv ) * ( r + 0.9 ), ( d, wv, np.cross( d, wv ) ), ( 0.8, 0.12, 1.8 ), paint )


def manhole( m, c, r=12.0, z=0.0, paint="rv_iron" ):
    """ A cast-iron manhole cover flush in the ground at c: its frame, raised rings and ribs, two pick holes. """
    C = v( c[0], c[1], z )
    lathe( m, ( C[0], C[1] ), [ ( r + 2.6, z + 0.02 ), ( r + 2.4, z + 0.18 ), ( r + 0.15, z + 0.18 ), ( r + 0.05, z + 0.06 ) ], paint, 20 )
    rings = [ ( r, z + 0.06 ) ]
    for k in range( 4 ):
        r0 = r * ( 0.86 - 0.2 * k )
        rings += [ ( r0 + 0.35, z + 0.08 ), ( r0 + 0.2, z + 0.24 ), ( r0 - 0.2, z + 0.24 ), ( r0 - 0.35, z + 0.08 ) ]
    rings += [ ( 0.0, z + 0.08 ) ]
    lathe( m, ( C[0], C[1] ), rings, paint, 20 )
    for k in range( 8 ):
        a = math.pi / 4 * k + math.pi / 8
        d = v( math.cos( a ), math.sin( a ), 0.0 )
        obox( m, C + d * ( r * 0.5 ) + UP * 0.16, d, ( r * 0.75, 0.4, 0.16 ), { "default": paint, "-z": None } )
    for sg in ( -1, 1 ):
        p = C + v( sg * r * 0.7, 0.0, 0.25 )
        card( m, "rv_black", [ p + v( -0.9, -0.35, 0 ), p + v( 0.9, -0.35, 0 ), p + v( 0.9, 0.35, 0 ), p + v( -0.9, 0.35, 0 ) ], UP )


def drain_grate( m, c, along=( 1, 0 ), length=24.0, width=12.0, z=0.0, paint="rv_iron" ):
    """ A gully grate flush in the ground at c: a frame, bars along it over the dark gully. """
    X = unit( ( along[0], along[1], 0.0 ) )
    Y = np.cross( UP, X )
    C = v( c[0], c[1], z )
    card( m, "rv_black", [ C - X * length / 2 - Y * width / 2 + UP * 0.03, C + X * length / 2 - Y * width / 2 + UP * 0.03,
                           C + X * length / 2 + Y * width / 2 + UP * 0.03, C - X * length / 2 + Y * width / 2 + UP * 0.03 ], UP )
    for sx in ( -1, 1 ):
        obox( m, C + X * ( sx * ( length / 2 + 0.6 ) ) + UP * 0.09, Y, ( width + 2.4, 1.2, 0.18 ), { "default": paint, "-z": None } )
    for sy in ( -1, 1 ):
        obox( m, C + Y * ( sy * ( width / 2 + 0.6 ) ) + UP * 0.09, X, ( length, 1.2, 0.18 ), { "default": paint, "-z": None } )
    count = int( width / 1.25 )
    for k in range( count ):
        y = -width / 2 + width * ( k + 0.5 ) / count
        obox( m, C + Y * y + UP * 0.08, X, ( length, 0.45, 0.16 ), { "default": paint, "-z": None } )
    for x in ( -length / 4, length / 4 ):
        obox( m, C + X * x + UP * 0.07, Y, ( 0.5, width, 0.14 ), { "default": paint, "-z": None } )


def cone( m, c, z0=0.0, h=28.0, paint="rv_ring_orange", band="rv_ring_white" ):
    """ A 28 in traffic cone: a square black base, the orange body with two reflective sleeves. """
    C = v( c[0], c[1], z0 )
    bevel_box( m, C + UP * 0.6, ( ( 1, 0, 0 ), ( 0, 1, 0 ), UP ), ( 14.0, 14.0, 1.2 ), "rv_black", 0.3, skip=( "-z", ) )
    def rad( z ):
        return 4.6 - ( 4.6 - 1.05 ) * ( z - 1.2 ) / ( h - 1.6 )

    zs = [ 1.2, h * 0.42, h * 0.42, h * 0.57, h * 0.57, h * 0.66, h * 0.66, h * 0.79, h * 0.79, h - 0.4 ]
    prof = [ ( 4.9, 1.2 ) ] + [ ( rad( z ) + ( 0.04 if k in ( 2, 3, 6, 7 ) else 0.0 ), z ) for k, z in enumerate( zs ) ] + [ ( 0.9, h ), ( 0.0, h ) ]
    paints = [ paint ] * ( len( prof ) - 1 )
    for k in ( 3, 7 ):
        paints[k] = band
    lathe( m, ( C[0], C[1] ), [ ( r_, z + z0 ) for r_, z in prof ], paints, 12 )


def hose_reel( m, at, out, paint="rv_red", hose="rv_red" ):
    """ A wall-mounted swinging fire hose reel at at (the wall's face, at the reel's middle) facing out: a bracket and
    pivot, the drum with its hose wound on, the nozzle hanging from it. """
    out = unit( ( out[0], out[1], 0.0 ) )
    at = v( *at )
    out, _ = _facing( m, at, out )
    right = np.cross( UP, out )
    bevel_box( m, at + out * 0.3, ( right, out, UP ), ( 6.0, 0.6, 14.0 ), paint, 0.2, skip=( "-y", ) )
    rod( m, at + out * 0.6 + UP * 5.0, at + out * 4.5 + UP * 5.0, 0.6, paint, 8 )
    rod( m, at + out * 4.5 + UP * 6.0, at + out * 4.5 - UP * 6.0, 0.7, "rv_zinc", 8, caps=True )
    hub = at + out * 10.5
    rod( m, at + out * 4.5, hub, 0.8, paint, 8 )
    R, W = 11.0, 6.0
    for sg in ( -1, 1 ):
        lathe_axis( m, hub + right * ( sg * W / 2 ), right * sg, [ ( 1.2, -0.15 ), ( R, -0.15 ), ( R, 0.15 ), ( 1.2, 0.15 ) ], paint, 14 )
    prof = [ ( 7.6 + ( 0.0 if k % 2 == 0 else 0.55 ), -W / 2 + 0.3 + ( W - 0.6 ) * k / 8 ) for k in range( 9 ) ]
    lathe_axis( m, hub, right, prof, hose, 14 )
    tip = hub + out * 2.0 - UP * 8.4
    tube( m, [ hub + out * 7.6 + UP * 1.0, hub + out * 9.5 - UP * 4.0, tip + out * 1.2 - UP * 3.0 ], 0.55, hose, 6, bend_radius=2.5 )
    rod( m, tip + out * 1.2 - UP * 3.0, tip + out * 1.2 - UP * 8.0, 0.7, "rv_black", 8, caps=True )


def cctv( m, at, out, paint="rv_enclosure", tilt=20.0 ):
    """ A bullet CCTV camera on a wall at at facing out: a base plate, an arm out to a ball joint, the housing tilted
    tilt degrees down with its sun shield and dark glass. """
    out = unit( ( out[0], out[1], 0.0 ) )
    at = v( *at )
    out, _ = _facing( m, at, out )
    right = np.cross( UP, out )
    bevel_box( m, at + out * 0.3, ( right, out, UP ), ( 3.2, 0.6, 4.4 ), paint, 0.2, skip=( "-y", ) )
    joint = at + out * 5.0 + UP * 1.0
    tube( m, [ at + out * 0.6, at + out * 3.0, joint ], 0.6, paint, 8, bend_radius=1.2 )
    lathe_axis( m, joint - UP * 1.0, UP, [ ( 0.0, 0.0 ), ( 0.75, 0.25 ), ( 1.0, 1.0 ), ( 0.75, 1.75 ), ( 0.0, 2.0 ) ], paint, 8 )
    ta = math.radians( tilt )
    axis = unit( out * math.cos( ta ) - UP * math.sin( ta ) )
    body0 = joint + UP * 1.6 - axis * 3.0
    lathe_axis( m, body0, axis, [ ( 0.0, -0.4 ), ( 1.4, 0.0 ), ( 1.8, 0.8 ), ( 1.8, 8.0 ), ( 1.95, 8.2 ), ( 1.95, 8.9 ), ( 1.5, 9.0 ) ], paint, 12 )
    lathe_axis( m, body0 + axis * 9.0, axis, [ ( 1.5, 0.0 ), ( 0.0, 0.0 ) ], "rv_window_dark", 12 )
    up2 = unit( np.cross( right, axis ) )
    shield = []
    for k in range( 7 ):
        a = math.pi * k / 6
        shield.append( right * ( 2.35 * math.cos( a ) ) + up2 * ( 2.35 * math.sin( a ) ) )
    for k in range( 6 ):
        p0, p1 = shield[k], shield[k + 1]
        a0, a1 = body0 + axis * 0.5, body0 + axis * 10.3
        card( m, paint, [ a0 + p0, a0 + p1, a1 + p1, a1 + p0 ], ( p0 + p1 ), both=True )


def sign_post( m, c, face, name=None, h=84.0, sign_h=18.0, paint="rv_zinc", z0=0.0 ):
    """ A galvanised sign post at c on a base plate, a sign at its top facing face: an rv_plates atlas sign (name), or a
    blank white panel; clamped to the post. """
    C = v( c[0], c[1], z0 )
    face = unit( ( face[0], face[1], 0.0 ) )
    right = np.cross( UP, face )
    rod( m, C, C + UP * h, 1.2, paint, 8 )
    lathe( m, ( C[0], C[1] ), [ ( 1.2, z0 + h ), ( 0.6, z0 + h + 0.4 ), ( 0.0, z0 + h + 0.5 ) ], paint, 8 )
    bevel_box( m, C + UP * 0.25, ( right, face, UP ), ( 7.0, 7.0, 0.5 ), paint, 0.15, skip=( "-z", ) )
    sc = C + face * 1.5 + UP * ( h - sign_h / 2 - 2.0 )
    if name and name in RM.PLATES:
        w = sign_h * RM.aspect( RM.PLATES, name )
        plate( m, name, sc, right, sign_h, off=0.1, back=paint )
    else:
        w = sign_h * 1.4
        quad( m, "rv_ring_white", sc + face * 0.1, right, UP, w, sign_h )
        quad( m, paint, sc, -right, UP, w, sign_h )
    for z in ( sign_h * 0.3, -sign_h * 0.3 ):
        torus( m, C + UP * ( h - sign_h / 2 - 2.0 + z ), UP, 1.5, 0.25, paint, seg=8, sides=4 )
    rod( m, sc - face * 0.05 - UP * ( sign_h * 0.45 ), sc - face * 0.05 + UP * ( sign_h * 0.45 ), 0.35, paint, 4 )
    del w


# ---------------------------------------------------------------------------------------------------------------------
# This module's textured surfaces (riverdale_materials draws them: python Tools/riverdale_materials.py <name>)

def precast_concrete( seed=101, n=None ):
    """ Precast barrier concrete, 64 in square, laid on a barrier with v up from its foot: smooth steel-form face, fine
    mottling and bug holes, faint form lines, scuffs low down from bumpers and a dirty splash band at its foot. """
    n = n or RM.px( 1024 )
    tile = 64.0
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = RM.field( rng, n, tile )
    cure, mid, grit = nz( 2.6, 60, 6 ), nz( 1.8, 8, 0.8 ), nz( 0.6, 0.4, 0.08 )
    colour = RM.lin( ( 168, 166, 160 ) )[None, None, :] * ( 1.0 + 0.05 * cure + 0.03 * mid + 0.03 * grit )[..., None]
    colour *= ( 1.0 + 0.02 * nz( 3.0, 64, 16 )[..., None] * np.array( [ 0.6, 0.2, -0.6 ], np.float32 ) )
    rough = 0.78 + 0.05 * mid
    height = 0.015 * mid + 0.01 * grit
    # Bug holes: small voids, more near the top where air rose in the form.
    pits = RM.smoothstep( 2.7, 3.2, nz( 0.4, 0.45, 0.08 ) ) * ( 0.6 + 0.4 * RM.smoothstep( 10, 30, z ) )
    colour = RM.mix( colour, colour * 0.42, pits[..., None] )
    height -= 0.06 * pits
    # Faint lines where the form's sheets met.
    form = np.exp( -( np.minimum( x % 32.0, 32.0 - x % 32.0 ) / 0.12 ) ** 2 ) * 0.5
    colour *= ( 1.0 - 0.06 * form )[..., None]
    # Aggregate showing through the cement skin: fine light and dark specks.
    speck = nz( 0.5, 0.25, 0.05 )
    colour *= ( 1.0 + 0.10 * RM.smoothstep( 2.0, 2.8, speck ) - 0.10 * RM.smoothstep( -2.0, -2.8, speck ) )[..., None]
    # Bumper scuffs low on the face: thin black rubber strokes, and pale scrapes where the skin wore through.
    cv = RM.BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    sc = RM.BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), tile, ss=1 )
    for k in range( 22 ):
        cx, cz = rng.uniform( 0, tile ), rng.uniform( 2, 16 )
        L = rng.uniform( 3, 18 )
        tilt = rng.normal( 0, 0.05 )
        pts = [ ( cx + L * t, cz + L * t * tilt + rng.normal( 0, 0.08 ) ) for t in np.linspace( 0, 1, 8 ) ]
        ( cv if k % 3 else sc ).line( pts, rng.uniform( 0.12, 0.5 ), rng.uniform( 0.3, 0.8 ) )
    scuff = RM.ndimage.gaussian_filter( cv.result(), 0.6, mode="wrap" )
    scrape = RM.ndimage.gaussian_filter( sc.result(), 0.6, mode="wrap" ) * RM.smoothstep( -0.5, 1.0, nz( 1.0, 1.0, 0.1 ) )
    colour = RM.mix( colour, RM.lin( ( 34, 32, 30 ) ), scuff[..., None] * 0.5 )
    colour = RM.mix( colour, RM.lin( ( 206, 200, 188 ) ), scrape[..., None] * 0.45 )
    # The splash band at the foot, and rain runs down from the top.
    splash = RM.smoothstep( 7.0, 0.5, z ) * ( 0.6 + 0.4 * RM.smoothstep( -1.0, 1.2, nz( 1.8, 6, 0.6 ) ) )
    colour = RM.mix( colour, colour * RM.lin( ( 120, 104, 84 ) ) * 3.0, splash[..., None] * 0.55 )
    src = np.zeros_like( x )
    src[( z > 33.0 ) & ( z < 34.0 )] = 1.0
    src *= RM.smoothstep( 0.4, 1.6, nz( 1.6, 4, 0.6 ) )
    runs = np.clip( RM.runs_down( src, ppi, 14.0 ) * 3.0, 0, 1 ) * ( z < 34.0 )
    colour = RM.mix( colour, colour * 0.78, runs[..., None] * 0.5 )
    rough = np.clip( rough - 0.08 * splash + 0.08 * pits - 0.15 * scuff + 0.05 * scrape, 0.3, 1.0 )
    return colour, rough, height, ppi


def pallet_wood( seed=102, n=None ):
    """ Weathered rough-sawn pine for pallets and drums, 48 in square, its grain running up the picture (map_kit's
    grain paints lay it along each board): grain lines, the odd knot, saw marks across, grey where it weathered. """
    n = n or RM.px( 1024 )
    tile = 48.0
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = RM.field( rng, n, tile )
    streak = RM.ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 40, 0.8 ), mode="wrap" )
    streak /= streak.std() + 1e-6
    # Growth rings cut through: narrow dark latewood lines, wandering as the saw met them.
    warp = RM.ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ), ( 6.0 * ppi, 0.6 * ppi ), mode="wrap" )
    warp /= warp.std() + 1e-6
    phase = x * 1.1 + 1.6 * warp + 0.15 * streak
    rings = np.abs( np.sin( phase ) )
    late = RM.smoothstep( 0.80, 0.97, rings )
    colour = RM.lin( ( 164, 132, 92 ) )[None, None, :] * ( 1.0 + 0.07 * streak + 0.06 * nz( 2.2, 30, 3 ) - 0.22 * late )[..., None]
    # Knots: dark ovals with grain swirling round.
    for _ in range( 5 ):
        kx, kz = rng.uniform( 0, tile ), rng.uniform( 0, tile )
        r = rng.uniform( 0.4, 0.9 )
        dx = np.minimum( np.abs( x - kx ), tile - np.abs( x - kx ) )
        dz = np.minimum( np.abs( z - kz ), tile - np.abs( z - kz ) )
        d = np.sqrt( ( dx / r ) ** 2 + ( dz / ( r * 1.6 ) ) ** 2 )
        colour = RM.mix( colour, RM.lin( ( 70, 46, 28 ) ), RM.smoothstep( 1.2, 0.7, d )[..., None] * 0.85 )
    saw = 0.5 + 0.5 * np.sin( z * 6.0 + 0.6 * nz( 1.4, 2, 0.4 ) )
    weather = RM.smoothstep( 0.0, 2.0, nz( 2.4, 30, 3 ) )
    grey = RM.lin( ( 132, 128, 120 ) )[None, None, :]
    colour = RM.mix( colour, grey * ( 1.0 + 0.1 * streak )[..., None], weather[..., None] * 0.45 )
    colour *= ( 1.0 - 0.05 * saw )[..., None]
    rough = np.clip( 0.82 + 0.06 * streak * 0.3 + 0.08 * weather, 0.5, 1.0 )
    height = 0.02 * streak + 0.008 * saw + 0.012 * late
    return colour, rough, height, ppi


def drum_paint( seed, base, n=None ):
    """ A steel drum's paint, 48 in square: mottled enamel, chips, rust spots and the drips running down from them, and
    scuffed patches where it was rolled and dragged. Nothing in it depends on height: a lathed drum's UVs are planar,
    shifted per model. """
    n = n or RM.px( 512 )
    tile = 48.0
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = RM.field( rng, n, tile )
    colour = RM.lin( base )[None, None, :] * ( 1.0 + 0.06 * nz( 2.4, 20, 2 ) + 0.03 * nz( 0.8, 0.8, 0.1 ) )[..., None]
    rough = 0.42 + 0.06 * nz( 2.0, 8, 1 )
    height = 0.004 * nz( 1.0, 1, 0.1 )
    chips = RM.smoothstep( 2.2, 2.6, nz( 1.4, 3, 0.15 ) + 0.4 * nz( 0.8, 0.5, 0.08 ) )
    colour = RM.mix( colour, RM.lin( ( 70, 70, 72 ) ), chips[..., None] )
    rust = RM.smoothstep( 2.4, 2.9, nz( 1.6, 2, 0.2 ) )
    colour = RM.mix( colour, RM.BM.RUST, rust[..., None] * 0.85 )
    src = RM.smoothstep( 2.6, 3.0, nz( 1.2, 1.5, 0.3 ) ).astype( np.float32 )
    drips = np.clip( RM.runs_down( src, ppi, 10.0 ) * 4.0, 0, 1 )
    colour = RM.mix( colour, RM.BM.RUST_STAIN, drips[..., None] * 0.45 )
    scuff = RM.smoothstep( 1.2, 2.2, nz( 2.0, 10, 1 ) ) * RM.smoothstep( 0.2, 1.6, nz( 1.6, 2, 0.2 ) )
    colour = RM.mix( colour, RM.lin( ( 92, 90, 88 ) ), scuff[..., None] * 0.7 )
    rough = np.clip( rough + 0.3 * rust + 0.15 * chips + 0.2 * scuff, 0.2, 1.0 )
    height -= 0.01 * chips
    return colour, rough, height, ppi
