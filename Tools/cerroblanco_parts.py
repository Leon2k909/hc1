"""
Cerro Blanco's building blocks, for Tools/cerroblanco_map.py: its paints, the walls (travertine below, enamelled panels
above), the glazing, stairs, railings and curved walls, and the props (the round boulder planter, the stage, the grand
piano, the red sculptures, the bronze sphere, benches, cafe furniture, banners, the sign).

Everything is in plan coordinates (map_kit's: e east, n north, z up, inches) and goes into map_kit Models. Collision is
given with each piece: boxes and hulls with a surface. Glass panes go into a separate model (the map's glass, tagged
navskip), so callers pass it as `glass`.
"""
import math
import zlib

import numpy as np

import map_kit as K
from map_kit import Model, Wall

METAL, STONE, WOOD, GLASS, DIRT, FABRIC = "metal", "default", "wood", "glass", "dirt", "fabric"

# The museum's own drawn materials (cerroblanco_materials.py), on a 30-inch module, tiling every 120.
TRAV, PANEL, PAVE, HONED = "cb_travertine", "cb_panel", "cb_paving", "cb_honed"
TILED = { TRAV: 120.0, PANEL: 120.0, PAVE: 120.0, HONED: 120.0 }

# Flat paints: ( colour, metalness, roughness ), written as text-only materials by the map script.
PLASTER, WHITE, FRAME, RED, BRONZE = "cb_plaster", "cb_white", "cb_frame", "cb_red", "cb_bronze"
PIANO, CURTAIN, BLACK, STEEL, TEAK = "cb_piano", "cb_curtain", "cb_black", "cb_steel", "cb_teak"
IVORY, FELT, LAMP, GLAZE = "cb_ivory", "cb_felt", "cb_lamp", "cb_glass"
CB_PAINTED = {
    PLASTER: ( ( 236, 233, 226 ), 0.0, 0.85 ),       # the galleries' white walls and ceilings
    WHITE: ( ( 238, 238, 234 ), 0.1, 0.32 ),         # painted steel: columns, canopies, pergolas, railings, sunshades
    FRAME: ( ( 54, 57, 60 ), 0.55, 0.38 ),           # the curtain walls' anodised mullions and door frames
    RED: ( ( 176, 30, 28 ), 0.05, 0.36 ),            # the sculptures' lacquered steel
    BRONZE: ( ( 92, 66, 40 ), 0.9, 0.34 ),           # the garden's sphere
    PIANO: ( ( 12, 12, 13 ), 0.0, 0.06 ),            # a concert grand's lacquer
    CURTAIN: ( ( 36, 36, 40 ), 0.0, 0.95 ),          # the stage's drapes
    BLACK: ( ( 22, 22, 24 ), 0.1, 0.55 ),            # speakers, stage skirts, trusses
    STEEL: ( ( 160, 162, 164 ), 0.85, 0.32 ),        # stainless: handrails, posts, bins
    TEAK: ( ( 132, 92, 58 ), 0.0, 0.55 ),            # benches' and cafe tables' slats
    IVORY: ( ( 236, 230, 214 ), 0.0, 0.3 ),          # the piano's keys
    FELT: ( ( 120, 24, 28 ), 0.0, 0.9 ),
    LAMP: ( ( 255, 246, 226 ), 0.0, 0.4 ),           # light fittings' diffusers
}
LAWN, HEDGE, SOIL, ROCK, GRAVEL = "lawn", "hedge", "soil", "rock", "gravel"

LOWER_TOP = 210.0            # travertine up to here (seven 30-inch courses), the enamelled panels above
OAK = "models/sbox_props/trees/oak"
BEECH = "models/sbox_props/shrubs/beech"
PINE = "models/sbox_props/shrubs/pine"
FOLIAGE = {
    f"{OAK}/tree_oak_small_a.vmdl": ( "facepunch.tree_oak_small_a#288917", ),
    f"{OAK}/tree_oak_medium_a.vmdl": ( "facepunch.tree_oak_medium_a#288916", ),
    f"{OAK}/tree_oak_dry_small_a.vmdl": ( "facepunch.treeoakdrysmalla#288926", ),
    f"{OAK}/tree_oak_dry_medium_a.vmdl": ( "facepunch.treeoakdrymediuma#289352", ),
    f"{BEECH}/beech_bush_small.vmdl": ( "facepunch.beech_bush_small#145429", ),
    f"{BEECH}/beech_bush_medium.vmdl": ( "facepunch.beech_bush_medium#145428", ),
    f"{BEECH}/beech_bush_regular_medium_a.vmdl": ( "facepunch.beech_bush_regular_medium_a#145432", ),
    f"{BEECH}/beech_bush_regular_small.vmdl": ( "facepunch.beech_bush_regular_small#145430", ),
    f"{PINE}/pine_bush_low_a.vmdl": ( "facepunch.pine_bush_low_a#145425", ),
    f"{PINE}/pine_bush_regular_c.vmdl": ( "facepunch.pine_bush_regular_c#145436", ),
    f"{PINE}/pine_shrub_tall_b.vmdl": ( "facepunch.pine_shrub_tall_b#145478", ),
}


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers (as Lowtide's)

def keyed( *key ):
    text = ",".join( f"{float( k ):.1f}" if isinstance( k, ( int, float, np.integer, np.floating ) ) else str( k ) for k in key )
    return zlib.crc32( text.encode() )


def chance( share, *key ):
    return ( keyed( *key ) % 10007 ) / 10007.0 < share


def jitter( scale, *key ):
    """ A steady random number in -scale..scale. """
    return ( ( keyed( *key ) % 20011 ) / 20011.0 * 2 - 1 ) * scale


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


def rod( m, a, b, r, paint, sides=6, caps=False ):
    """ A round bar from a to b (drawn only), shaded smooth. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    axis = K.normalise( b - a )
    side = np.cross( axis, ( 0.0, 0.0, 1.0 ) )
    if np.linalg.norm( side ) < 1e-6:
        side = np.array( ( 1.0, 0.0, 0.0 ) )
    side = K.normalise( side )
    up = np.cross( side, axis )
    ring = [ side * math.cos( 2 * math.pi * k / sides ) + up * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
    for k in range( sides ):
        p, q = ring[k], ring[( k + 1 ) % sides]
        m.polygon( paint, [ a + p * r, a + q * r, b + q * r, b + p * r ], normal=( p + q ) / 2, normals=[ p, q, q, p ] )
    if caps:
        m.polygon( paint, [ b + p * r for p in ring ], normal=axis )
        m.polygon( paint, [ a + p * r for p in reversed( ring ) ], normal=-axis )


def column( m, e, n, z0, z1, r, paint, sides=16, surface=None ):
    """ An upright round column, shaded smooth, with its collision a hull round it. """
    ring = [ np.array( ( math.cos( 2 * math.pi * k / sides ), math.sin( 2 * math.pi * k / sides ), 0.0 ) ) for k in range( sides ) ]
    c = np.array( ( e, n, 0.0 ) )
    for k in range( sides ):
        p, q = ring[k], ring[( k + 1 ) % sides]
        m.polygon( paint, [ c + p * r + ( 0, 0, z0 ), c + q * r + ( 0, 0, z0 ), c + q * r + ( 0, 0, z1 ), c + p * r + ( 0, 0, z1 ) ],
                   normal=( p + q ) / 2, normals=[ p, q, q, p ] )
    if surface:
        m.hull( [ c + p * r + ( 0, 0, z ) for z in ( z0, z1 ) for p in ring[::2] ], surface )


def disc( m, paint, centre, r, z, facing=1.0, sides=24, uv=None ):
    pts = [ ( centre[0] + r * math.cos( 2 * math.pi * k / sides ), centre[1] + r * math.sin( 2 * math.pi * k / sides ), z )
            for k in range( sides ) ]
    if facing < 0:
        pts = pts[::-1]
    m.polygon( paint, pts, normal=( 0, 0, facing ) )


def box_at( m, centre, size, paints, surface=None ):
    c, h = np.asarray( centre, float ), np.asarray( size, float ) / 2
    m.box( c - h, c + h, paints, surface )


def turned( e, n, yaw ):
    """ Plan axes for a piece turned yaw degrees (its own +x is the plan direction at yaw from east). """
    c, s = math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) )
    return np.array( ( c, s, 0.0 ) ), np.array( ( -s, c, 0.0 ) ), np.array( ( 0.0, 0.0, 1.0 ) )


def obox( m, origin, yaw, local, size, paints, surface=None ):
    """ A box at local ( x, y, z ) of a piece at origin turned yaw. """
    x, y, z = turned( 0, 0, yaw )
    centre = np.asarray( origin, float ) + x * local[0] + y * local[1] + z * local[2]
    m.oriented_box( centre, ( x, y, z ), size, paints, surface )


# ---------------------------------------------------------------------------------------------------------------------
# Walls

def facade( m, axis, run, across, outward, z0, z1, openings=(), lower=TRAV, upper=PANEL, inside=PLASTER, reveal=HONED,
            ends=True, split=LOWER_TOP, surface=STONE ):
    """ A straight outside wall: travertine up to split, the enamelled panels above (or one paint, lower == upper).
    openings are ( centre, width, z0, z1, kind ), kind 'door' (open), 'glass' or 'arch'. ends paints the wall's ends
    in its outside paint (a corner), else leaves them undrawn (hidden in another wall). """
    for lo, hi, outside in ( ( z0, min( split, z1 ), lower ), ( max( split, z0 ), z1, upper ) ):
        if hi - lo < 1e-6:
            continue
        w = Wall( axis, run, across, ( lo, hi ), outward )
        for centre, width, oz0, oz1, kind in openings:
            a, b = max( oz0, lo ), min( oz1, hi )
            if b - a > 1e-6:
                w.add( centre, width, a, b, kind )
        w.build( m, outside, inside, reveal, end=outside if ends else None, surface=surface )


def inner_wall( m, axis, run, across, z0, z1, openings=(), paint=PLASTER, reveal=PLASTER, ends=True, surface=STONE ):
    w = Wall( axis, run, across, ( z0, z1 ) )
    for centre, width, oz0, oz1, kind in openings:
        w.add( centre, width, oz0, oz1, kind )
    w.build( m, paint, paint, reveal, end=paint if ends else None, surface=surface )


def glaze( m, glass, axis, d, r0, r1, z0, z1, pitch=60.0, transoms=(), frame=FRAME, depth=5.0, width=2.5, sill=True ):
    """ A curtain wall in an opening: an anodised frame round it, mullions about pitch apart, transoms at the heights
    given, and panes (1.5 thick, colliding as glass) in glass. d is the wall's middle, across it. """
    count = max( 1, int( round( ( r1 - r0 ) / pitch ) ) )
    rs = [ r0 + ( r1 - r0 ) * k / count for k in range( count + 1 ) ]
    zs = [ z0 ] + [ z for z in transoms if z0 < z < z1 ] + [ z1 ]

    def put( ra, rb, za, zb, dd, paint, surface=None ):
        if axis == "e":
            m_ = m if paint != GLAZE else glass
            m_.box( ( ra, d - dd / 2, za ), ( rb, d + dd / 2, zb ), paint, surface )
        else:
            m_ = m if paint != GLAZE else glass
            m_.box( ( d - dd / 2, ra, za ), ( d + dd / 2, rb, zb ), paint, surface )

    for k, r in enumerate( rs ):
        a = r if k > 0 else r
        put( max( r0, r - width / 2 ), min( r1, r + width / 2 ), z0, z1, depth, frame )
    for z in zs:
        put( r0, r1, max( z0, z - width / 2 ), min( z1, z + width / 2 ), depth, frame )
    for ra, rb in zip( rs, rs[1:] ):
        put( ra, rb, z0, z1, 1.5, GLAZE, GLASS )


def door_frame( m, axis, d, centre, width, z1, thickness, frame=FRAME ):
    """ A slim frame lining an open doorway (no leaf: bots can't open doors). """
    r0, r1 = centre - width / 2, centre + width / 2
    t = thickness / 2 + 0.6
    for a, b in ( ( r0, r0 + 2.5 ), ( r1 - 2.5, r1 ) ):
        if axis == "e":
            m.box( ( a, d - t, 0 ), ( b, d + t, z1 ), frame )
        else:
            m.box( ( d - t, a, 0 ), ( d + t, b, z1 ), frame )
    if axis == "e":
        m.box( ( r0, d - t, z1 - 2.5 ), ( r1, d + t, z1 ), frame )
    else:
        m.box( ( d - t, r0, z1 - 2.5 ), ( d + t, r1, z1 ), frame )


def slab( m, e0, e1, n0, n1, z0, z1, holes=(), top=PAVE, bottom=PLASTER, side=HONED, surface=STONE ):
    """ A level slab with rectangular holes ( e0, e1, n0, n1 ) cut through it (stairwells), as rectangles. """
    es = sorted( { e0, e1 } | { h[k] for h in holes for k in ( 0, 1 ) if e0 < h[k] < e1 } )
    ns = sorted( { n0, n1 } | { h[k] for h in holes for k in ( 2, 3 ) if n0 < h[k] < n1 } )

    def inside( e, n ):
        return any( h[0] <= e <= h[1] and h[2] <= n <= h[3] for h in holes )

    for a, b in zip( es, es[1:] ):
        for c, d in zip( ns, ns[1:] ):
            if inside( ( a + b ) / 2, ( c + d ) / 2 ):
                continue
            paints = { "+z": top, "-z": bottom, "default": None }
            for face, at, other in ( ( "-e", a, ( a - 1, ( c + d ) / 2 ) ), ( "+e", b, ( b + 1, ( c + d ) / 2 ) ),
                                     ( "-n", c, ( ( a + b ) / 2, c - 1 ) ), ( "+n", d, ( ( a + b ) / 2, d + 1 ) ) ):
                edge = at in ( e0, e1 ) if face in ( "-e", "+e" ) else at in ( n0, n1 )
                if edge or inside( *other ):
                    paints[face] = side
            m.box( ( a, c, z0 ), ( b, d, z1 ), paints, surface )


def roof( m, e0, e1, n0, n1, z, parapet=30.0, top=GRAVEL, coping=HONED, outside=PANEL, inside=PANEL, thick=16.0,
          ceiling=PLASTER, wall=18.0, surface=STONE ):
    """ A flat roof: its slab (z - thick .. z, ceiling under), gravel over it, and a parapet round it of the façade's
    paint with a honed coping. The parapet stands on the walls (its outside flush with theirs). """
    m.box( ( e0 + wall, n0 + wall, z - thick ), ( e1 - wall, n1 - wall, z ), { "+z": top, "-z": ceiling, "default": None }, surface )
    h = parapet
    for lo, hi, faces in ( ( ( e0, n0 ), ( e1, n0 + wall ), "-n" ), ( ( e0, n1 - wall ), ( e1, n1 ), "+n" ),
                           ( ( e0, n0 + wall ), ( e0 + wall, n1 - wall ), "-e" ), ( ( e1 - wall, n0 + wall ), ( e1, n1 - wall ), "+e" ) ):
        inner = { "-n": "+n", "+n": "-n", "-e": "+e", "+e": "-e" }[faces]
        paints = { faces: outside, inner: inside, "+z": coping, "-z": None, "default": outside }
        m.box( ( lo[0], lo[1], z ), ( hi[0], hi[1], z + h ), paints, surface )
        # The coping's lip, proud of the face.
    for lo, hi in ( ( ( e0 - 2, n0 - 2 ), ( e1 + 2, n0 + wall ) ), ( ( e0 - 2, n1 - wall ), ( e1 + 2, n1 + 2 ) ),
                    ( ( e0 - 2, n0 + wall ), ( e0 + wall, n1 - wall ) ), ( ( e1 - wall, n0 + wall ), ( e1 + 2, n1 - wall ) ) ):
        m.box( ( lo[0], lo[1], z + h ), ( hi[0], hi[1], z + h + 3 ), coping )


# ---------------------------------------------------------------------------------------------------------------------
# Curved walls

def ring( m, centre, r_in, r_out, z0, z1, outer=TRAV, inner=PLASTER, top=HONED, reveal=HONED, a0=0.0, a1=360.0,
          step=7.5, gaps=(), surface=STONE, bottom=None ):
    """ An annular wall round centre, between r_in and r_out, from angle a0 to a1 (degrees, anticlockwise from east).
    gaps are ( angle, width in inches at r_out, gz0, gz1 ): openings through it. Its faces are shaded smooth and its
    UVs run round it (arc length), so the stone's courses follow the curve. """
    ce, cn = centre
    edges = { a0, a1 }
    spans = []
    for angle, width, gz0, gz1 in gaps:
        half = math.degrees( width / 2 / r_out )
        spans.append( ( angle - half, angle + half, gz0, gz1 ) )
        edges |= { angle - half, angle + half }
    count = max( 1, int( math.ceil( ( a1 - a0 ) / step ) ) )
    edges |= { a0 + ( a1 - a0 ) * k / count for k in range( count + 1 ) }
    angles = sorted( a for a in edges if a0 - 1e-6 <= a <= a1 + 1e-6 )

    def solid( mid ):
        """ The wall's solid z intervals at angle mid. """
        cuts = sorted( ( gz0, gz1 ) for s0, s1, gz0, gz1 in spans if s0 - 1e-6 <= mid <= s1 + 1e-6 )
        out, bottom_ = [], z0
        for c0, c1 in cuts + [ ( z1, z1 ) ]:
            if c0 > bottom_ + 1e-6:
                out.append( ( bottom_, min( c0, z1 ) ) )
            bottom_ = max( bottom_, c1 )
        return out

    def unit( a ):
        return np.array( ( math.cos( math.radians( a ) ), math.sin( math.radians( a ) ), 0.0 ) )

    pieces = [ ( a, b, solid( ( a + b ) / 2 ) ) for a, b in zip( angles, angles[1:] ) ]
    for index, ( a, b, intervals ) in enumerate( pieces ):
        ua, ub = unit( a ), unit( b )
        c = np.array( ( ce, cn, 0.0 ) )
        for lo, hi in intervals:
            for r, paint, sign in ( ( r_out, outer, 1.0 ), ( r_in, inner, -1.0 ) ):
                if paint is None:
                    continue
                pts = [ c + ua * r + ( 0, 0, lo ), c + ub * r + ( 0, 0, lo ), c + ub * r + ( 0, 0, hi ), c + ua * r + ( 0, 0, hi ) ]
                uv = [ ( math.radians( a ) * r / 120.0 * sign, lo / 120.0 ), ( math.radians( b ) * r / 120.0 * sign, lo / 120.0 ),
                       ( math.radians( b ) * r / 120.0 * sign, hi / 120.0 ), ( math.radians( a ) * r / 120.0 * sign, hi / 120.0 ) ]
                normals = [ ua * sign, ub * sign, ub * sign, ua * sign ]
                if sign < 0:
                    pts, uv, normals = pts[::-1], uv[::-1], normals[::-1]
                m.polygon( paint, pts, normal=( ua + ub ) * sign, uv=uv if paint in TILED else None, normals=normals )
            for z, face, paint in ( ( hi, 1.0, top if hi >= z1 - 1e-6 else reveal ), ( lo, -1.0, bottom if lo <= z0 + 1e-6 else reveal ) ):
                if paint is None:
                    continue
                pts = [ c + ua * r_in + ( 0, 0, z ), c + ua * r_out + ( 0, 0, z ), c + ub * r_out + ( 0, 0, z ), c + ub * r_in + ( 0, 0, z ) ]
                if face < 0:
                    pts = pts[::-1]
                m.polygon( paint, pts, normal=( 0, 0, face ) )
            # The piece's ends, where its neighbour is open over this height.
            for neighbour, u, facing in ( ( index - 1, ua, -1 ), ( index + 1, ub, 1 ) ):
                open_ = neighbour < 0 or neighbour >= len( pieces )
                if open_:
                    if abs( a0 - 0 ) < 1e-6 and abs( a1 - 360 ) < 1e-6:
                        continue
                    lo2, hi2 = lo, hi
                else:
                    others = pieces[neighbour][2]
                    gaps_here = [ ( lo, hi ) ]
                    for o0, o1 in others:
                        gaps_here = [ g for g0, g1 in gaps_here for g in ( ( g0, min( g1, o0 ) ), ( max( g0, o1 ), g1 ) ) if g[1] - g[0] > 1e-6 ]
                    if not gaps_here:
                        continue
                    lo2, hi2 = gaps_here[0][0], gaps_here[-1][1]
                tangent = np.array( ( -u[1], u[0], 0.0 ) ) * facing
                pts = [ c + u * r_in + ( 0, 0, lo2 ), c + u * r_out + ( 0, 0, lo2 ), c + u * r_out + ( 0, 0, hi2 ), c + u * r_in + ( 0, 0, hi2 ) ]
                card( m, reveal, pts, tangent )
            if surface:
                m.hull( [ c + u * r + ( 0, 0, z ) for u in ( ua, ub ) for r in ( r_in, r_out ) for z in ( lo, hi ) ], surface )


def arc_points( centre, r, a0, a1, step=7.5 ):
    count = max( 1, int( math.ceil( abs( a1 - a0 ) / step ) ) )
    return [ ( centre[0] + r * math.cos( math.radians( a0 + ( a1 - a0 ) * k / count ) ),
               centre[1] + r * math.sin( math.radians( a0 + ( a1 - a0 ) * k / count ) ) ) for k in range( count + 1 ) ]


def curved_glazing( m, glass, centre, r, a0, a1, z0, z1, step=7.5, transoms=(), frame=FRAME ):
    """ Facets of glass round an arc (radius r, the glass's plane), with a mullion at every facet's joint. """
    pts = arc_points( centre, r, a0, a1, step )
    zs = [ z0 ] + list( transoms ) + [ z1 ]
    for k, ( e, n ) in enumerate( pts ):
        m.box( ( e - 1.4, n - 1.4, z0 ), ( e + 1.4, n + 1.4, z1 ), frame )
    for ( ea, na ), ( eb, nb ) in zip( pts, pts[1:] ):
        mid = np.array( ( ( ea + eb ) / 2 - centre[0], ( na + nb ) / 2 - centre[1], 0.0 ) )
        for z in zs:
            m.beam( ( ea, na, z ), ( eb, nb, z ), ( 4.0, 2.5 ), frame )
        along = K.normalise( np.array( ( eb - ea, nb - na, 0.0 ) ) )
        out = K.normalise( mid )
        length = math.hypot( eb - ea, nb - na )
        glass.oriented_box( ( ( ea + eb ) / 2, ( na + nb ) / 2, ( z0 + z1 ) / 2 ), ( along, -out, ( 0, 0, 1 ) ),
                            ( length, 1.5, z1 - z0 ), GLAZE, GLASS )


# ---------------------------------------------------------------------------------------------------------------------
# Stairs and railings

def flight( m, axis, a0, a1, r_top, r_foot, z_top, z_foot, tread=HONED, riser=HONED, side=PLASTER, surface=STONE,
            base=None, max_rise=7.2 ):
    """ A straight flight along axis ('n' or 'e') from its top (r_top, level with z_top) down to its foot (r_foot,
    z_foot), a0..a1 across. The steps are drawn; the collision is one ramp hull along the nosings. """
    rise = z_top - z_foot
    count = max( 1, int( math.ceil( rise / max_rise ) ) )
    step_z = rise / count
    sign = 1.0 if r_foot > r_top else -1.0
    step_r = abs( r_foot - r_top ) / count
    base = z_foot - 12 if base is None else base

    def lohi( ra, rb, z0, z1 ):
        if axis == "n":
            return ( a0, min( ra, rb ), z0 ), ( a1, max( ra, rb ), z1 )
        return ( min( ra, rb ), a0, z0 ), ( max( ra, rb ), a1, z1 )

    plus, minus = ( "+n", "-n" ) if axis == "n" else ( "+e", "-e" )
    front, back = ( plus, minus ) if sign > 0 else ( minus, plus )
    for k in range( count ):
        top = z_top - step_z * k
        ra = r_top + sign * step_r * k
        rb = ra + sign * step_r
        m.box( *lohi( ra, rb, base, top ), { "+z": tread, "default": side, front: riser, back: None, "-z": None } )
    first, last = r_top + sign * step_r, r_foot + sign * step_r
    pts = []
    for a in ( a0, a1 ):
        for r, z in ( ( r_top, z_top ), ( first, z_top ), ( last, z_foot ), ( r_top, base ), ( last, base ) ):
            pts.append( ( a, r, z ) if axis == "n" else ( r, a, z ) )
    m.hull( pts, surface )


def balustrade( m, glass, p0, p1, z0, height=42.0, rail=STEEL, posts=48.0, surface=METAL, solid=None ):
    """ A glass balustrade from p0 to p1 (plan ( e, n )): a stainless top rail, glass between slim posts, and a thin
    collision box its height (in m, so the navmesh sees it). solid paints a low upstand instead of glass. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    length = float( np.linalg.norm( p1 - p0 ) )
    if length < 1:
        return
    along = ( p1 - p0 ) / length
    side = np.array( ( -along[1], along[0], 0.0 ) )
    count = max( 1, int( round( length / posts ) ) )
    for k in range( count + 1 ):
        p = p0 + along * length * k / count
        m.box( ( p[0] - 1.0, p[1] - 1.0, z0 ), ( p[0] + 1.0, p[1] + 1.0, z0 + height - 1 ), rail )
    rod( m, ( *p0, z0 + height ), ( *p1, z0 + height ), 1.1, rail, sides=8 )
    centre = ( ( p0 + p1 ) / 2 )
    if solid:
        m.oriented_box( ( centre[0], centre[1], z0 + 3 ), ( np.append( along, 0 ), side, ( 0, 0, 1 ) ), ( length, 2.0, 6.0 ), solid )
    glass.oriented_box( ( centre[0], centre[1], z0 + 3 + ( height - 6 ) / 2 ), ( np.append( along, 0 ), side, ( 0, 0, 1 ) ),
                        ( length, 0.8, height - 6 ), GLAZE )
    if surface:
        m.oriented_box( ( centre[0], centre[1], z0 + height / 2 ), ( np.append( along, 0 ), side, ( 0, 0, 1 ) ),
                        ( length, 2.0, height ), None, surface )


def rail_along( m, points, z, height=38.0, paint=WHITE, posts=54.0, surface=METAL, bars=True ):
    """ A painted steel railing along a polyline (plan points): posts, a flat top rail, a mid rail and thin bars. """
    pts = [ np.asarray( p, float ) for p in points ]
    for a, b in zip( pts, pts[1:] ):
        length = float( np.linalg.norm( b - a ) )
        if length < 1:
            continue
        along = ( b - a ) / length
        count = max( 1, int( round( length / posts ) ) )
        for k in range( count + 1 ):
            p = a + along * length * k / count
            m.box( ( p[0] - 1.0, p[1] - 1.0, z ), ( p[0] + 1.0, p[1] + 1.0, z + height ), paint )
        m.beam( ( *a, z + height ), ( *b, z + height ), ( 2.5, 1.2 ), paint )
        m.beam( ( *a, z + 4 ), ( *b, z + 4 ), ( 1.2, 1.2 ), paint )
        if bars:
            for k in range( 1, int( length / 5.0 ) ):
                p = a + along * length * k / int( length / 5.0 )
                m.box( ( p[0] - 0.3, p[1] - 0.3, z + 4 ), ( p[0] + 0.3, p[1] + 0.3, z + height ), { "default": paint, "+z": None, "-z": None } )
        if surface:
            side = np.array( ( -along[1], along[0], 0.0 ) )
            m.oriented_box( ( ( a[0] + b[0] ) / 2, ( a[1] + b[1] ) / 2, z + height / 2 ), ( np.append( along, 0 ), side, ( 0, 0, 1 ) ),
                            ( length, 2.0, height ), None, surface )


def sloped_rail( m, a, b, height=36.0, paint=STEEL, posts=50.0, surface=METAL ):
    """ A handrail on posts along a stair, from a to b (points on its treads' line). """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    length = float( np.linalg.norm( b - a ) )
    count = max( 1, int( round( length / posts ) ) )
    for k in range( count + 1 ):
        p = a + ( b - a ) * k / count
        m.box( ( p[0] - 0.9, p[1] - 0.9, p[2] ), ( p[0] + 0.9, p[1] + 0.9, p[2] + height ), paint )
    up = np.array( ( 0.0, 0.0, height ) )
    rod( m, a + up, b + up, 1.0, paint, sides=8 )
    if surface:
        along = K.normalise( b - a )
        level = K.normalise( np.array( ( along[0], along[1], 0.0 ) ) )
        side = np.array( ( -level[1], level[0], 0.0 ) )
        upward = np.cross( along, side )
        if upward[2] < 0:
            side, upward = -side, -upward
        m.oriented_box( ( a + b ) / 2 + upward * height / 2, ( along, side, upward ), ( length, 2.0, height ), None, surface )


# ---------------------------------------------------------------------------------------------------------------------
# Ground

def paving( m, e0, e1, n0, n1, z=0.0, paint=PAVE ):
    """ Paving drawn on the ground (the ground's collision is one box under the whole map). """
    m.polygon( paint, [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ], normal=( 0, 0, 1 ) )


def lawn( m, e0, e1, n0, n1, raise_=5.0, kerb=8.0, kerb_paint=HONED, paint=LAWN ):
    """ A lawn raised inside a honed kerb (so it never fights the paving), its collision a box (a step). The kerb is
    four strips and the grass sits a little under their top, so no two faces share a plane. """
    top = raise_ + 1.5
    m.collision_box( ( e0, n0, 0 ), ( e1, n1, top ), STONE )
    for lo, hi in ( ( ( e0, n0 ), ( e1, n0 + kerb ) ), ( ( e0, n1 - kerb ), ( e1, n1 ) ),
                    ( ( e0, n0 + kerb ), ( e0 + kerb, n1 - kerb ) ), ( ( e1 - kerb, n0 + kerb ), ( e1, n1 - kerb ) ) ):
        m.box( ( lo[0], lo[1], 0 ), ( hi[0], hi[1], top ), { "+z": kerb_paint, "-z": None, "default": kerb_paint } )
    m.polygon( paint, [ ( e0 + kerb, n0 + kerb, top - 0.4 ), ( e1 - kerb, n0 + kerb, top - 0.4 ),
                        ( e1 - kerb, n1 - kerb, top - 0.4 ), ( e0 + kerb, n1 - kerb, top - 0.4 ) ], normal=( 0, 0, 1 ) )


def lawn_poly( m, outline, raise_=5.0, kerb=8.0, kerb_paint=HONED, paint=LAWN ):
    """ A convex lawn bed of any outline (counter-clockwise plan points): a kerb ring round its top and the grass
    inside it, side by side so they never share a plane. """
    pts = np.array( outline, float )
    top = raise_ + 1.5
    m.prism( pts, 0, top, { "side": kerb_paint, "top": None, "bottom": None }, STONE )
    centre = pts.mean( axis=0 )
    inner = [ p + K.normalise( np.append( centre - p, 0 ) )[:2] * kerb * 1.3 for p in pts ]
    count = len( pts )
    for k in range( count ):
        a, b = pts[k], pts[( k + 1 ) % count]
        ia, ib = inner[k], inner[( k + 1 ) % count]
        m.polygon( kerb_paint, [ ( *a, top ), ( *b, top ), ( *ib, top ), ( *ia, top ) ], normal=( 0, 0, 1 ) )
    m.polygon( paint, [ ( *p, top - 0.4 ) for p in inner ], normal=( 0, 0, 1 ) )


def hedge_box( m, e0, e1, n0, n1, height=34.0, z0=0.0, planter=None ):
    """ A clipped hedge (box hedge), in a honed planter if planter is its kerb height. """
    if planter:
        m.box( ( e0 - 6, n0 - 6, z0 ), ( e1 + 6, n1 + 6, z0 + planter ), { "+z": HONED, "-z": None, "default": HONED }, STONE )
        z0 += planter - 2
    m.box( ( e0, n0, z0 ), ( e1, n1, z0 + height ), { "default": HEDGE, "-z": None }, WOOD )


def tree( m, e, n, path=f"{OAK}/tree_oak_medium_a.vmdl", scale=1.0, z=0.0, grate=True, trunk=9.0 ):
    """ A Facepunch cloud tree, in a square steel grate, with a collision box for its trunk. """
    m.props.append( { "path": path, "position": ( e, n, z ), "yaw": float( keyed( "tree", e, n ) % 360 ),
                      "scale": ( scale, scale, scale ) } )
    if grate:
        m.box( ( e - 30, n - 30, z - 1 ), ( e + 30, n + 30, z + 0.4 ), { "+z": BLACK, "default": None } )
    m.collision_box( ( e - trunk * scale, n - trunk * scale, z ), ( e + trunk * scale, n + trunk * scale, z + 160 * scale ), WOOD )


def bush( m, e, n, z=0.0, path=f"{BEECH}/beech_bush_small.vmdl", scale=1.0, yaw=None ):
    m.props.append( { "path": path, "position": ( e, n, z ), "yaw": float( keyed( "bush", e, n ) % 360 ) if yaw is None else yaw,
                      "scale": ( scale, scale, scale ) } )


def boulder( m, centre, size, seed, paint=ROCK, surface=STONE, points=18 ):
    """ A rough stone: the convex hull of points on a squashed, lumpy sphere, shaded flat. size ( e, n, z ) radii;
    centre is the middle of its foot. """
    rng = np.random.default_rng( seed )
    dirs = rng.normal( size=( points, 3 ) )
    dirs /= np.linalg.norm( dirs, axis=1 )[:, None]
    dirs[:, 2] = np.abs( dirs[:, 2] ) * 1.0 - 0.15
    radii = 0.78 + 0.22 * rng.random( points )
    pts = np.asarray( centre, float ) + dirs * np.asarray( size, float ) * radii[:, None]
    pts[:, 2] = np.maximum( pts[:, 2], centre[2] - 4 )
    for face in K.convex_faces( pts ):
        m.polygon( paint, [ pts[i] for i in face ] )
    if surface:
        m.hull( [ tuple( p ) for p in pts ], surface )


# ---------------------------------------------------------------------------------------------------------------------
# Props

def round_planter( m, centre, r, rim_h=22.0, rim_w=14.0, seed=1, tree_path=f"{OAK}/tree_oak_small_a.vmdl" ):
    """ The courtyard's round planter: a honed travertine ring, soil heaped inside it, boulders bedded in the soil and
    low shrubs round a small tree. You can step up onto its rim and the boulders. """
    ring( m, centre, r - rim_w, r, 0, rim_h, outer=HONED, inner=HONED, top=HONED, step=6.0 )
    ce, cn = centre
    # The soil: a low dome of rings, so it isn't a flat plate.
    rings = [ ( r - rim_w, rim_h - 3 ), ( r * 0.7, rim_h + 5 ), ( r * 0.35, rim_h + 10 ), ( 0, rim_h + 12 ) ]
    sides = 36
    for ( ra, za ), ( rb, zb ) in zip( rings, rings[1:] ):
        for k in range( sides ):
            a0, a1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
            pts = [ ( ce + ra * math.cos( a0 ), cn + ra * math.sin( a0 ), za ), ( ce + ra * math.cos( a1 ), cn + ra * math.sin( a1 ), za ),
                    ( ce + rb * math.cos( a1 ), cn + rb * math.sin( a1 ), zb ), ( ce + rb * math.cos( a0 ), cn + rb * math.sin( a0 ), zb ) ]
            if rb < 1e-6:
                pts = pts[:3]
            m.polygon( SOIL, pts )
    m.hull( [ ( ce + ra * math.cos( 2 * math.pi * k / 12 ), cn + ra * math.sin( 2 * math.pi * k / 12 ), z )
              for ra, za in rings[:2] for k in range( 12 ) for z in ( 0, za ) ], DIRT )
    rng = np.random.default_rng( seed )
    for k in range( 7 ):
        a = 2 * math.pi * ( k / 7 + rng.random() * 0.08 )
        rr = ( r - rim_w ) * ( 0.42 + 0.3 * rng.random() )
        size = ( 38 + 26 * rng.random(), 32 + 22 * rng.random(), 30 + 24 * rng.random() )
        boulder( m, ( ce + rr * math.cos( a ), cn + rr * math.sin( a ), rim_h ), size, seed * 100 + k )
    for k in range( 12 ):
        a = 2 * math.pi * ( k + 0.5 ) / 12 + jitter( 0.2, "shrub", k, seed )
        rr = ( r - rim_w ) * ( 0.72 + jitter( 0.1, "rr", k, seed ) )
        path = ( f"{BEECH}/beech_bush_regular_small.vmdl", f"{PINE}/pine_bush_low_a.vmdl", f"{BEECH}/beech_bush_small.vmdl" )[k % 3]
        bush( m, ce + rr * math.cos( a ), cn + rr * math.sin( a ), rim_h - 2, path, 0.8 + 0.3 * ( keyed( k, seed ) % 10 ) / 10 )
    tree( m, ce + 30, cn - 20, tree_path, 1.0, z=rim_h + 8, grate=False )


def sweep( m, paint, path, profile, normals_smooth=True ):
    """ A loft: profile (a closed ring of ( x, y ) offsets) carried along path (( point, side, up, scale ) frames). """
    rings = []
    for point, side, up, scale in path:
        rings.append( [ np.asarray( point, float ) + side * x * scale[0] + up * y * scale[1] for x, y in profile ] )
    count = len( profile )
    for ra, rb, fa, fb in zip( rings, rings[1:], path, path[1:] ):
        ca, cb = np.mean( ra, axis=0 ), np.mean( rb, axis=0 )
        for k in range( count ):
            p0, p1 = ra[k], ra[( k + 1 ) % count]
            q0, q1 = rb[k], rb[( k + 1 ) % count]
            normals = [ K.normalise( p0 - ca ), K.normalise( p1 - ca ), K.normalise( q1 - cb ), K.normalise( q0 - cb ) ]
            card( m, paint, [ p0, p1, q1, q0 ], ( p0 + p1 + q0 + q1 ) / 4 - ( ca + cb ) / 2,
                  normals=normals if normals_smooth else None )
    for ring_, sign in ( ( rings[0], -1 ), ( rings[-1], 1 ) ):
        c = np.mean( ring_, axis=0 )
        other = rings[1] if sign < 0 else rings[-2]
        card( m, paint, ring_, c - np.mean( other, axis=0 ) )


def spire_sculpture( m, e, n, height=330.0, seed=3, paint=RED ):
    """ The plaza's tall red sculpture: a flat steel blade rising from a honed plinth, sweeping up in a long curve and
    twisting a quarter turn as it narrows to a point, like the lacquered steel pieces of the 1990s. """
    box_at( m, ( e, n, 6 ), ( 70, 70, 12 ), { "default": HONED, "-z": None }, STONE )
    profile = [ ( math.cos( 2 * math.pi * k / 14 ), 0.32 * math.sin( 2 * math.pi * k / 14 ) ) for k in range( 14 ) ]
    frames = []
    steps = 22
    for k in range( steps + 1 ):
        t = k / steps
        bend = 70.0 * t * t
        point = np.array( ( e + bend * 0.8, n + bend * 0.6, 12 + height * t ) )
        twist = math.radians( 95 * t )
        side = np.array( ( math.cos( twist ), math.sin( twist ), 0.0 ) )
        up = np.array( ( -math.sin( twist ), math.cos( twist ), 0.0 ) )
        width = 30.0 * ( 1 - t ) ** 0.8 + 1.0
        frames.append( ( point, side, up, ( width, width ) ) )
    sweep( m, paint, frames, profile )
    m.collision_box( ( e - 26, n - 26, 12 ), ( e + 26, n + 26, 12 + height * 0.5 ), METAL )
    m.collision_box( ( e - 10, n - 10, 12 + height * 0.5 ), ( e + 60, n + 50, 12 + height ), METAL )


def folded_sculpture( m, e, n, yaw=0.0, paint=RED, scale=1.0 ):
    """ The second red piece: steel plates folded into a leaning, angular arch, standing on its own feet. """
    pts = [ ( -70, 0, 0 ), ( -40, 10, 140 ), ( 30, -8, 190 ), ( 80, 0, 60 ), ( 70, 6, 0 ) ]
    x, y, z = turned( 0, 0, yaw )
    origin = np.array( ( e, n, 0.0 ) )
    world = [ origin + ( x * p[0] + y * p[1] + z * p[2] ) * scale for p in pts ]
    thick = 9.0 * scale
    width = 56.0 * scale
    for a, b in zip( world, world[1:] ):
        along = K.normalise( b - a )
        side = K.normalise( np.cross( along, z ) ) if abs( along[2] ) < 0.99 else y
        normal = np.cross( side, along )
        corners = [ a - side * width / 2, b - side * width / 2, b + side * width / 2, a + side * width / 2 ]
        for off, facing in ( ( thick / 2, normal ), ( -thick / 2, -normal ) ):
            card( m, paint, [ c + normal * off for c in corners ], facing )
        for s in ( -1, 1 ):
            edge = [ a + side * s * width / 2 - normal * thick / 2, b + side * s * width / 2 - normal * thick / 2,
                     b + side * s * width / 2 + normal * thick / 2, a + side * s * width / 2 + normal * thick / 2 ]
            card( m, paint, edge, side * s )
        m.hull( [ tuple( c + normal * o ) for c in corners for o in ( -thick / 2, thick / 2 ) ], METAL )


def bronze_sphere( m, e, n, r=58.0, plinth=24.0 ):
    """ The garden circle's bronze sphere on a low honed drum. """
    m.cylinder( ( e, n ), r * 0.55, 0, plinth, { "side": HONED, "top": HONED, "bottom": None }, sides=24, surface=STONE )
    c = np.array( ( e, n, plinth + r * 0.95 ) )
    rings, sides = 12, 24
    for i in range( rings ):
        t0, t1 = math.pi * i / rings, math.pi * ( i + 1 ) / rings
        for k in range( sides ):
            p0, p1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
            d = [ np.array( ( math.sin( t ) * math.cos( p ), math.sin( t ) * math.sin( p ), math.cos( t ) ) )
                  for t, p in ( ( t0, p0 ), ( t1, p0 ), ( t1, p1 ), ( t0, p1 ) ) ]
            pts = [ c + v * r for v in d ]
            if i == 0:
                pts, d = [ pts[0], pts[1], pts[2] ], [ d[0], d[1], d[2] ]
            elif i == rings - 1:
                pts, d = [ pts[0], pts[1], pts[3] ], [ d[0], d[1], d[3] ]
            card( m, BRONZE, pts, sum( d ), normals=d )
    m.hull( [ tuple( c + r * np.array( v ) ) for v in ( ( 1, 0, 0 ), ( -1, 0, 0 ), ( 0, 1, 0 ), ( 0, -1, 0 ), ( 0, 0, 1 ), ( 0, 0, -1 ),
                                                       ( .7, .7, 0 ), ( -.7, .7, 0 ), ( .7, -.7, 0 ), ( -.7, -.7, 0 ) ) ], METAL )


def grand_piano( m, e, n, z, yaw ):
    """ A concert grand (about 9 ft) with its lid up on its stick, the keyboard towards yaw + 180. """
    x, y, up = turned( 0, 0, yaw )
    o = np.array( ( e, n, z ) )

    def at( px, py, pz ):
        return o + x * px + y * py + up * pz

    # The case's outline: straight spine on the left (-y), the bentside curving round to the tail (+x).
    outline = [ ( -48, -30 ), ( 60, -30 ), ( 95, -24 ), ( 104, -12 ), ( 98, 2 ), ( 70, 12 ), ( 40, 22 ), ( 10, 30 ), ( -48, 30 ) ]
    rim0, rim1 = 22.0, 34.0
    pts = [ at( px, py, 0 ) for px, py in outline ]
    for a, b in zip( outline, outline[1:] + outline[:1] ):
        card( m, PIANO, [ at( *a, rim0 ), at( *b, rim0 ), at( *b, rim1 ), at( *a, rim1 ) ],
              np.cross( at( *b, 0 ) - at( *a, 0 ), up ) * -1 )
    card( m, PIANO, [ at( px, py, rim1 ) for px, py in outline ], up )
    card( m, PIANO, [ at( px, py, rim0 ) for px, py in outline ], -up )
    # Lid, propped at 45 degrees along the spine side.
    hinge = -30.0
    lid = [ ( px, hinge + ( py - hinge ) * 0.7, rim1 + ( py - hinge ) * 0.7 ) for px, py in outline ]
    card( m, PIANO, [ at( *p ) for p in lid ], -y + up )
    card( m, PIANO, [ at( *p ) for p in lid ], y - up )
    rod( m, at( 70, 20, rim1 ), at( 72, 6, rim1 + 26 ), 0.6, PIANO, sides=4 )
    # Legs and the lyre.
    for px, py in ( ( -40, -24 ), ( -40, 24 ), ( 88, -10 ) ):
        obox( m, at( px, py, 0 ), yaw, ( 0, 0, rim0 / 2 ), ( 5, 5, rim0 ), PIANO )
    obox( m, at( -40, 0, 0 ), yaw, ( 0, 0, 9 ), ( 3, 10, 18 ), PIANO )
    # Keyboard and its cheeks.
    obox( m, at( -56, 0, 0 ), yaw, ( 0, 0, rim0 + 3 ), ( 16, 62, 6 ), PIANO )
    obox( m, at( -58, 0, 0 ), yaw, ( 0, 0, rim0 + 6.2 ), ( 12, 56, 0.6 ), IVORY )
    for k in range( 36 ):
        if k % 7 in ( 2, 6 ):
            continue
        obox( m, at( -55, -27 + k * 1.55, 0 ), yaw, ( 0, 0, rim0 + 7.0 ), ( 6, 0.9, 1.2 ), PIANO )
    # The bench.
    obox( m, at( -82, 0, 0 ), yaw, ( 0, 0, 18 ), ( 14, 30, 3 ), PIANO )
    for px, py in ( ( -88, -12 ), ( -88, 12 ), ( -76, -12 ), ( -76, 12 ) ):
        obox( m, at( px, py, 0 ), yaw, ( 0, 0, 8.5 ), ( 2, 2, 17 ), PIANO )
    m.hull( [ tuple( at( px, py, zz ) ) for px, py in outline for zz in ( 0, rim1 ) ], WOOD )
    m.hull( [ tuple( at( px, py, zz ) ) for px in ( -64, -48 ) for py in ( -31, 31 ) for zz in ( 0, rim0 + 8 ) ], WOOD )


def speaker( m, e, n, z, yaw, tall=True ):
    """ A PA cabinet on a stand (or on the floor as a monitor wedge). """
    x, y, up = turned( 0, 0, yaw )
    o = np.array( ( e, n, z ) )
    if tall:
        rod( m, o, o + up * 58, 1.0, STEEL, sides=6 )
        for k in range( 3 ):
            a = math.radians( yaw + 120 * k )
            rod( m, o + up * 20, o + np.array( ( math.cos( a ) * 22, math.sin( a ) * 22, -20 ) ) + up * 0, 0.7, STEEL, sides=4 )
        obox( m, o, yaw, ( 0, 0, 58 + 18 ), ( 15, 20, 36 ), BLACK, METAL )
        obox( m, o, yaw, ( 7.7, 0, 58 + 18 ), ( 0.4, 17, 32 ), CURTAIN )
        m.collision_box( ( e - 6, n - 6, z ), ( e + 6, n + 6, z + 58 ), METAL )
    else:
        obox( m, o, yaw, ( 0, 0, 7 ), ( 16, 26, 14 ), BLACK, METAL )


def stage( m, e0, e1, n0, n1, height=30.0, front="+e" ):
    """ The courtyard's stage: a platform with a black skirt and a honed edge, steps down at each end of its front,
    a black truss frame over it, and drapes along its back. """
    m.box( ( e0, n0, 0 ), ( e1, n1, height ), { "+z": TEAK, "-z": None, "default": BLACK }, WOOD )
    m.box( ( e0 - 1, n0 - 1, height ), ( e1 + 1, n1 + 1, height + 1.5 ), { "+z": None, "-z": None, "default": STEEL } )
    span = ( n0, n1 ) if front in ( "+e", "-e" ) else ( e0, e1 )
    # Steps down at both ends of the front.
    for end in ( 0, 1 ):
        if front == "+e":
            r0, r1 = ( n0 + 10, n0 + 70 ) if end == 0 else ( n1 - 70, n1 - 10 )
            flight( m, "e", r0, r1, e1, e1 + 4 * 11, height, 0, tread=HONED, riser=BLACK, side=BLACK, base=0 )
        elif front == "-e":
            r0, r1 = ( n0 + 10, n0 + 70 ) if end == 0 else ( n1 - 70, n1 - 10 )
            flight( m, "e", r0, r1, e0, e0 - 4 * 11, height, 0, tread=HONED, riser=BLACK, side=BLACK, base=0 )
        elif front == "+n":
            r0, r1 = ( e0 + 10, e0 + 70 ) if end == 0 else ( e1 - 70, e1 - 10 )
            flight( m, "n", r0, r1, n1, n1 + 4 * 11, height, 0, tread=HONED, riser=BLACK, side=BLACK, base=0 )
        else:
            r0, r1 = ( e0 + 10, e0 + 70 ) if end == 0 else ( e1 - 70, e1 - 10 )
            flight( m, "n", r0, r1, n0, n0 - 4 * 11, height, 0, tread=HONED, riser=BLACK, side=BLACK, base=0 )
    # Truss: four uprights and a box frame over it, drawn as square tubes.
    top = height + 190
    corners = [ ( e0 + 6, n0 + 6 ), ( e1 - 6, n0 + 6 ), ( e1 - 6, n1 - 6 ), ( e0 + 6, n1 - 6 ) ]
    for ce, cn in corners:
        m.box( ( ce - 5, cn - 5, height ), ( ce + 5, cn + 5, top ), BLACK, METAL )
    for ( ae, an ), ( be, bn ) in zip( corners, corners[1:] + corners[:1] ):
        for dz in ( 0.0, -12.0 ):
            m.beam( ( ae, an, top + dz ), ( be, bn, top + dz ), ( 3, 3 ), BLACK )
    # Spotlights hanging off the front truss, and drapes along the back, in folds. Worked in the stage's own axes:
    # r along its front, d across it (towards the audience is +d).
    along_e = front in ( "+n", "-n" )
    sign = 1.0 if front in ( "+e", "+n" ) else -1.0
    r0_, r1_ = ( e0, e1 ) if along_e else ( n0, n1 )
    d_front = ( n1 if sign > 0 else n0 ) if along_e else ( e1 if sign > 0 else e0 )
    d_back = ( n0 if sign > 0 else n1 ) if along_e else ( e0 if sign > 0 else e1 )

    def at( r, d, z ):
        return ( r, d, z ) if along_e else ( d, r, z )

    def lohi( ra, rb, da, db, za, zb ):
        a, b = at( ra, da, za ), at( rb, db, zb )
        return np.minimum( a, b ), np.maximum( a, b )

    fd = d_front - sign * 6
    for k in range( 5 ):
        rr = r0_ + ( r1_ - r0_ ) * ( k + 0.5 ) / 5
        m.box( *lohi( rr - 4, rr + 4, fd - 5, fd + 5, top - 30, top - 18 ), BLACK )
        lens = fd + sign * 5
        m.box( *lohi( rr - 3, rr + 3, lens, lens + sign * 0.2, top - 28, top - 20 ), LAMP )
    bd = d_back + sign * 3
    folds = int( ( r1_ - r0_ - 12 ) / 9 )
    towards = np.array( at( 0, sign, 0 ), float )
    for k in range( folds ):
        ra, rb = r0_ + 6 + k * 9, r0_ + 6 + ( k + 1 ) * 9
        dd = 3.0 if k % 2 else 0.0
        card( m, CURTAIN, [ at( ra, bd + sign * dd, height ), at( rb, bd + sign * ( 3 - dd ), height ),
                            at( rb, bd + sign * ( 3 - dd ), top - 14 ), at( ra, bd + sign * dd, top - 14 ) ], towards, both=True )
    m.collision_box( *lohi( r0_ + 6, r1_ - 6, bd - sign * 2, bd + sign * 5, height, top - 14 ), FABRIC )


def bench( m, e, n, length=96.0, along="e", height=17.0, depth=20.0, teak=True ):
    """ A long honed travertine bench, with a teak seat on it. """
    if along == "e":
        lo, hi = ( e - length / 2, n - depth / 2, 0 ), ( e + length / 2, n + depth / 2, height )
    else:
        lo, hi = ( e - depth / 2, n - length / 2, 0 ), ( e + depth / 2, n + length / 2, height )
    m.box( lo, hi, { "default": HONED, "-z": None }, STONE )
    if teak:
        slats = 5
        for k in range( slats ):
            if along == "e":
                a = n - depth / 2 + 1 + ( depth - 2 ) * k / slats
                m.box( ( e - length / 2 + 4, a + 0.4, height ), ( e + length / 2 - 4, a + ( depth - 2 ) / slats - 0.4, height + 1.6 ), TEAK )
            else:
                a = e - depth / 2 + 1 + ( depth - 2 ) * k / slats
                m.box( ( a + 0.4, n - length / 2 + 4, height ), ( a + ( depth - 2 ) / slats - 0.4, n + length / 2 - 4, height + 1.6 ), TEAK )


def cafe_table( m, e, n, z=0.0, r=14.0 ):
    m.cylinder( ( e, n ), r, z + 28.5, z + 29.5, { "side": STEEL, "top": WHITE, "bottom": STEEL }, sides=20 )
    rod( m, ( e, n, z + 1 ), ( e, n, z + 28.5 ), 1.2, STEEL, sides=6 )
    m.cylinder( ( e, n ), 9, z, z + 1, { "side": STEEL, "top": STEEL, "bottom": None }, sides=12 )
    m.collision_box( ( e - r * 0.7, n - r * 0.7, z ), ( e + r * 0.7, n + r * 0.7, z + 29.5 ), METAL )


def cafe_chair( m, e, n, yaw, z=0.0 ):
    """ A steel bistro chair with a teak seat, its back away from yaw (it faces yaw). """
    obox( m, ( e, n, z ), yaw, ( 0, 0, 17.5 ), ( 16, 16, 1.2 ), TEAK )
    for px, py in ( ( 7, 7 ), ( 7, -7 ), ( -7, 7 ), ( -7, -7 ) ):
        x, y, _ = turned( 0, 0, yaw )
        p = np.array( ( e, n, z ) ) + x * px + y * py
        rod( m, p, p + ( 0, 0, 17 ), 0.5, STEEL, sides=4 )
    x, y, _ = turned( 0, 0, yaw )
    back = np.array( ( e, n, z ) ) - x * 7.5
    for py in ( -7, 7 ):
        rod( m, back + y * py + ( 0, 0, 17 ), back + y * py + ( 0, 0, 33 ) - x * 1.5, 0.5, STEEL, sides=4 )
    obox( m, back + ( 0, 0, 0 ) - x * 1.2, yaw, ( 0, 0, 29 ), ( 1, 15, 5 ), TEAK )
    m.collision_box( ( e - 7, n - 7, z ), ( e + 7, n + 7, z + 18 ), METAL )


def parasol( m, e, n, z=0.0, r=48.0, paint=WHITE ):
    """ A square cafe umbrella, open. """
    rod( m, ( e, n, z ), ( e, n, z + 96 ), 1.2, STEEL, sides=6 )
    apex = np.array( ( e, n, z + 100 ) )
    corners = [ np.array( ( e + sx * r, n + sy * r, z + 84 ) ) for sx, sy in ( ( 1, 1 ), ( -1, 1 ), ( -1, -1 ), ( 1, -1 ) ) ]
    for a, b in zip( corners, corners[1:] + corners[:1] ):
        card( m, paint, [ a, b, apex ], ( a + b ) / 2 - np.array( ( e, n, z + 60 ) ), both=True )
    m.box( ( e - 9, n - 9, z ), ( e + 9, n + 9, z + 3 ), BLACK )


def banner( m, k, centre, z_top, outward, width=64.0, height=192.0, off=14.0, along=None ):
    """ An exhibition banner (cb_banner_k) hung off a façade: two white arms out of the wall, the banner between them on
    a top and a bottom rod. centre is a point on the wall's face, outward the plan direction out of it; the banner hangs
    flat, parallel to the wall, off out of it. """
    out = K.normalise( np.array( ( outward[0], outward[1], 0.0 ) ) )
    side = np.array( ( out[1], -out[0], 0.0 ) ) if along is None else K.normalise( np.array( ( *along, 0.0 ) ) )
    c = np.array( ( centre[0], centre[1], 0.0 ) ) + out * off
    z0, z1 = z_top - height, z_top
    corners = [ c - side * width / 2 + ( 0, 0, z0 ), c + side * width / 2 + ( 0, 0, z0 ), c + side * width / 2 + ( 0, 0, z1 ),
                c - side * width / 2 + ( 0, 0, z1 ) ]
    # Seen from outside, the picture reads left to right: u along -side... flipped so it isn't mirrored.
    uv = [ ( 0.0, 0.0 ), ( 1.0, 0.0 ), ( 1.0, 1.0 ), ( 0.0, 1.0 ) ]
    if np.dot( np.cross( side, ( 0, 0, 1 ) ), out ) > 0:
        corners = [ corners[1], corners[0], corners[3], corners[2] ]
    card( m, f"cb_banner_{k}", corners, out, uv=uv )
    back = [ p - out * 0.3 for p in corners ]
    card( m, f"cb_banner_{k}", back, -out, uv=[ ( 1.0, 0.0 ), ( 0.0, 0.0 ), ( 0.0, 1.0 ), ( 1.0, 1.0 ) ] )
    wall = np.array( ( centre[0], centre[1], 0.0 ) )
    for z in ( z0 - 2, z1 + 2 ):
        rod( m, c - side * ( width / 2 + 2 ) + ( 0, 0, z ), c + side * ( width / 2 + 2 ) + ( 0, 0, z ), 0.9, WHITE, sides=6 )
    for s in ( -1, 1 ):
        for z in ( z0 + 10, z1 - 6 ):
            rod( m, wall + side * s * width * 0.38 + ( 0, 0, z ), c + side * s * width * 0.38 + ( 0, 0, z ), 0.8, WHITE, sides=6 )


def sign_letters( m, centre, z0, width, outward ):
    """ The museum's name in bronze letters (cb_sign, alpha tested, 8:1), standing 1.5 off a wall. """
    out = K.normalise( np.array( ( outward[0], outward[1], 0.0 ) ) )
    side = np.array( ( out[1], -out[0], 0.0 ) )
    c = np.array( ( centre[0], centre[1], 0.0 ) ) + out * 1.5
    h = width / 8
    corners = [ c + side * width / 2 + ( 0, 0, z0 ), c - side * width / 2 + ( 0, 0, z0 ), c - side * width / 2 + ( 0, 0, z0 + h ),
                c + side * width / 2 + ( 0, 0, z0 + h ) ]
    card( m, "cb_sign", corners, out, uv=[ ( 0.0, 0.0 ), ( 1.0, 0.0 ), ( 1.0, 1.0 ), ( 0.0, 1.0 ) ] )


def bollard_light( m, e, n, h=34.0 ):
    m.cylinder( ( e, n ), 3.5, 0, h, { "side": FRAME, "top": FRAME, "bottom": None }, sides=12, surface=METAL )
    m.cylinder( ( e, n ), 3.6, h - 8, h - 2, { "side": LAMP, "top": None, "bottom": None }, sides=12 )


def litter_bin( m, e, n ):
    m.cylinder( ( e, n ), 9, 0, 34, { "side": STEEL, "top": BLACK, "bottom": None }, sides=16, surface=METAL )


def display_plinth( m, e, n, w=26.0, h=40.0, thing=None ):
    """ A white gallery plinth, with something on it (a 'bust': a bronze lump, or a vase). """
    m.box( ( e - w / 2, n - w / 2, 0 ), ( e + w / 2, n + w / 2, h ), { "default": WHITE, "-z": None }, STONE )
    if thing == "vase":
        m.cylinder( ( e, n ), 6, h, h + 14, { "side": RED, "top": BLACK, "bottom": None }, sides=12 )
    elif thing:
        boulder( m, ( e, n, h ), ( 8, 7, 14 ), keyed( "bust", e, n ), paint=BRONZE, surface=None, points=14 )


def gallery_wall( m, e0, e1, n0, n1, h=144.0, art=None ):
    """ A freestanding white display wall (art: hang frames on both long sides). """
    m.box( ( e0, n0, 0 ), ( e1, n1, h ), { "default": PLASTER, "-z": None }, STONE )


def picture( m, centre, z, w, h, facing, paint ):
    """ A framed canvas on a wall. """
    out = K.normalise( np.array( ( facing[0], facing[1], 0.0 ) ) )
    side = np.array( ( out[1], -out[0], 0.0 ) )
    c = np.array( ( centre[0], centre[1], z ) ) + out * 1.0
    m.oriented_box( c + out * 0.6, ( side, out, ( 0, 0, 1 ) ), ( w + 4, 1.4, h + 4 ), BLACK )
    corners = [ c - side * w / 2 + out * 1.35 + ( 0, 0, -h / 2 ), c + side * w / 2 + out * 1.35 + ( 0, 0, -h / 2 ),
                c + side * w / 2 + out * 1.35 + ( 0, 0, h / 2 ), c - side * w / 2 + out * 1.35 + ( 0, 0, h / 2 ) ]
    card( m, paint, corners, out )
