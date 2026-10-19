"""
Railhead structure, round 2: the details the art director asked for after round 1, all visual (no collision):

- the footbridge's side girders as riveted plate girders (flange angles, stiffener angles, rivet rows) and its side
  panels with cover strips, a drip and run-off streaks;
- precast stair parapets with real V joints, a chamfered cap and a kick plinth;
- the goods sheds' sliding doors (framed, ledged and braced boards on roller hangers from a top track);
- the head building wings' cab-road facades (archivolts, Lisenen, window surrounds, a dentilled cornice);
- streaky soot run-off on the shed's arcade.

Plan inches (e east, n north, z up), as map_kit; called from railhead_station and railhead_architecture.
"""
import math
import random

import numpy as np

import railhead_profiles as P

IRON = "rw_steel"
IRON_DARK = "rw_steel_dark"
STONE = "rw_dressed"
PANEL = "rhs_bridge_panel"
PRECAST = "rhs_precast"
GRIME = "rhs_grime"
DOOR = "rhs_door_green"


def _runs( r0, r1, gaps, min_len=2.0 ):
    out, at = [], r0
    for a, b in sorted( gaps ):
        if b <= at or a >= r1:
            continue
        if a - at >= min_len:
            out.append( ( at, a ) )
        at = max( at, b )
    if r1 - at >= min_len:
        out.append( ( at, r1 ) )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The footbridge's outer faces

def bridge_girder_outer( model, n_face, out, e_max, gaps, z0, z1, stiff_first=31.5, stiff_pitch=60.0, pitch=4.0 ):
    """ A plate girder's outside face at n_face (facing out along n), its web z0..z1, from e 0 to e_max broken at the
    stair gaps: 4 in flange angles top and bottom (an outstanding leg and a leg on the web), stiffener angles every
    stiff_pitch, and rivet rows along the flanges' web legs (pitch) and the bottom leg's underside. """
    def box( e0, e1, d0, d1, za, zb, paint=IRON_DARK, skip_back=True ):
        a, b = sorted( ( n_face + out * d0, n_face + out * d1 ) )
        paints = { "default": paint }
        if skip_back and d0 == 0.0:
            paints[ "-n" if out > 0 else "+n" ] = None
        model.box( ( e0, a, za ), ( e1, b, zb ), paints )

    leg, web = 4.0, 0.7
    for a, b in _runs( 0.0, e_max, gaps ):
        box( a, b, 0.0, leg, z0, z0 + web )                 # bottom flange angle: outstanding leg
        box( a, b, 0.0, web, z0 + web, z0 + 4.0 )           # ... and its leg on the web
        box( a, b, 0.0, web, z1 - 4.0, z1 - web )           # top flange angle
        box( a, b, 0.0, leg, z1 - web, z1 )
        stiffs = []
        e = stiff_first
        while e < e_max:
            if a + 3.0 < e < b - 3.0:
                stiffs.append( e )
            e += stiff_pitch
        for e in stiffs:
            box( e - 1.6, e + 1.6, 0.0, 0.5, z0 + 4.0, z1 - 4.0 )           # the angle's leg on the web
            box( e - 0.25, e + 0.25, web, 3.2, z0 + web, z1 - web )        # its outstanding leg
            for zz in np.arange( z0 + 7.0, z1 - 5.0, 4.0 ):
                P.rivet( model, ( e - 1.0, n_face + out * 0.5, zz ), ( 0, out, 0 ), radius=0.42, height=0.3, paint=IRON_DARK )
        # Rivets along both web legs and under the bottom leg, clear of the stiffeners.
        e = a + 2.0
        while e < b - 1.5:
            if all( abs( e - s ) > 2.2 for s in stiffs ):
                for zz in ( z0 + 2.35, z1 - 2.35 ):
                    P.rivet( model, ( e, n_face + out * web, zz ), ( 0, out, 0 ), radius=0.45, height=0.32, paint=IRON_DARK )
                if int( round( ( e - a ) / pitch ) ) % 2 == 0:
                    P.rivet( model, ( e, n_face + out * 2.6, z0 ), ( 0, 0, -1 ), radius=0.45, height=0.3, paint=IRON_DARK )
            e += pitch


def bridge_panel_outer( model, n_face, out, runs, z0, z1, seed=0 ):
    """ The footbridge's side panels' outside face at n_face (facing out), z0..z1, over runs [ ( a, b ) ]: cover strips
    on the panel joints at the mullions (every 60 from each run's start), a drip under the trim at z1, and dark run-off
    streaks under the drip. """
    rng = random.Random( seed )
    normal = ( 0.0, out, 0.0 )
    for a, b in runs:
        if b - a < 1:
            continue
        joints = []
        for k in range( int( ( b - a ) // 60 ) + 1 ):
            joints.append( min( a + 60 * k, b - 1.5 ) + 1.5 )
        for e in joints:
            lo, hi = sorted( ( n_face, n_face + out * 0.4 ) )
            model.box( ( max( a, e - 1.0 ), lo, z0 ), ( min( b, e + 1.0 ), hi, z1 - 1.5 ),
                       { "default": PANEL, ( "-n" if out > 0 else "+n" ): None } )
        lo, hi = sorted( ( n_face, n_face + out * 1.5 ) )
        model.box( ( a, lo, z1 - 1.5 ), ( b, hi, z1 ), { "default": IRON_DARK, ( "-n" if out > 0 else "+n" ): None } )
        # Run-off: where the drip lets go, thin dark streaks down the panel, more of them near the joints.
        d = n_face + out * 0.05
        for p, q in zip( joints, joints[1:] ):
            for _ in range( rng.randint( 1, 3 ) ):
                c = rng.uniform( p + 3.0, q - 3.0 )
                w = rng.uniform( 0.5, 1.8 )
                length = rng.uniform( 5.0, 20.0 )
                top = z1 - 1.5
                P._poly( model, "rw_steel_soot", [ ( c - w / 2, d, top ), ( c + w / 2, d, top ), ( c + w * 0.15, d, top - length ),
                                                   ( c - w * 0.15, d, top - length ) ], normal )


# ---------------------------------------------------------------------------------------------------------------------
# Precast stair parapets

def precast_panels( model, e_face, out, n_a, n_b, top_a, top_b, z0=0.0, pitch=96.0, proud=1.0, groove=0.75,
                    top_gap=1.0, plinth=0.0, paint=PRECAST ):
    """ 2.4 m precast panels on a parapet face at e_face (facing out along e) from n_a to n_b, the face's top sloping
    from top_a to top_b: each panel stands proud, its joint edges chamfered into V joints groove wide each side, its
    top edge chamfered under the cap. plinth > 0 starts the panels over a kick plinth that high. """
    lo_n, hi_n = sorted( ( n_a, n_b ) )

    def top( n ):
        t = ( n - n_a ) / ( n_b - n_a ) if n_b != n_a else 0.0
        return top_a + ( top_b - top_a ) * t - top_gap

    def p( d, n, z ):
        return ( e_face + out * d, n, z )

    joints = [ lo_n ]
    n = lo_n + pitch
    while n < hi_n - 30.0:
        joints.append( n )
        n += pitch
    joints.append( hi_n )
    c = groove
    zb = z0 + plinth
    for a, b in zip( joints, joints[1:] ):
        if b - a < 4 * c:
            continue
        ft_a, ft_b = top( a + c ) - c, top( b - c ) - c
        P._poly( model, paint, [ p( proud, a + c, zb ), p( proud, b - c, zb ), p( proud, b - c, ft_b ), p( proud, a + c, ft_a ) ],
                 ( out, 0, 0 ) )
        P._poly( model, paint, [ p( 0, a, zb ), p( proud, a + c, zb ), p( proud, a + c, ft_a ), p( 0, a, top( a ) ) ],
                 ( out * c, -proud, 0 ) )
        P._poly( model, paint, [ p( proud, b - c, zb ), p( 0, b, zb ), p( 0, b, top( b ) ), p( proud, b - c, ft_b ) ],
                 ( out * c, proud, 0 ) )
        P._poly( model, paint, [ p( proud, a + c, ft_a ), p( proud, b - c, ft_b ), p( 0, b, top( b ) ), p( 0, a, top( a ) ) ],
                 ( out * c, 0, proud ) )
    if plinth > 0:
        prof = [ ( 0.0, 0.0 ), ( proud + 0.6, 0.0 ), ( proud + 0.6, plinth - 0.8 ), ( proud, plinth ), ( 0.0, plinth ) ]
        P.straight( model, "n", e_face, lo_n, hi_n, z0, out, prof, paint )


def parapet_cap( model, w0, w1, n_a, n_b, top_a, top_b, overhang=2.0, paint=PRECAST ):
    """ A precast cap on a sloping parapet (w0..w1 across, its top from top_a at n_a to top_b at n_b): 3 in deep,
    overhang past each face, its lower outer edges chamfered and its top weathered to a ridge. """
    c = ( w0 + w1 ) / 2
    W = ( w1 - w0 ) / 2 + overhang
    ch = min( 1.6, overhang - 0.2 )
    section = [ ( -W + ch, -0.4 ), ( W - ch, -0.4 ), ( W, -0.4 + ch ), ( W, 2.5 ), ( 0.0, 3.0 ), ( -W, 2.5 ), ( -W, -0.4 + ch ) ]
    k = len( section )
    for i in range( k ):
        j = ( i + 1 ) % k
        ( ui, vi ), ( uj, vj ) = section[i], section[j]
        quad = [ ( c + ui, n_a, top_a + vi ), ( c + uj, n_a, top_a + vj ), ( c + uj, n_b, top_b + vj ), ( c + ui, n_b, top_b + vi ) ]
        towards = ( ( ui + uj ) / 2, 0.0, ( vi + vj ) / 2 - 1.2 )
        P._poly( model, paint, quad, towards )
    for n, top, s in ( ( n_a, top_a, -1.0 ), ( n_b, top_b, 1.0 ) ):
        P._poly( model, paint, [ ( c + u, n, top + v ) for u, v in section ], ( 0, s * ( 1 if n_b > n_a else -1 ), 0 ) )


def bracket_streak( model, face_e, side, n, z, paint=GRIME ):
    """ A rust-and-grime streak running down a parapet face (at face_e, facing side along e) from a handrail bracket's
    plate at ( n, z ). """
    d = face_e + side * 0.06
    P._poly( model, paint, [ ( d, n - 0.75, z ), ( d, n + 0.75, z ), ( d, n + 0.25, z - 12.0 ), ( d, n - 0.25, z - 12.0 ) ],
             ( side, 0, 0 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The goods sheds' sliding doors

def sliding_door( model, face, sgn, n0, n1, z0, z1, board=5.0, gap=0.3 ):
    """ A framed, ledged and braced door leaf on a wall face (face e, outward sgn), n0..n1, z0..z1, its back 3 in off
    the wall: tongue-and-groove boards in fir green, a steel angle frame, a ledge and two braces, a steel kick plate,
    a pull handle and two roller hangers up to the track (track()). """
    def d( x ):
        return face + sgn * x

    def box( r0, r1, x0, x1, za, zb, paint ):
        a, b = sorted( ( d( x0 ), d( x1 ) ) )
        model.box( ( a, r0, za ), ( b, r1, zb ), paint )

    width = n1 - n0
    count = max( 1, int( round( width / ( board + gap ) ) ) )
    step = width / count
    for k in range( count ):
        r0 = n0 + k * step + ( gap / 2 if k else 0.0 )
        r1 = n0 + ( k + 1 ) * step - ( gap / 2 if k < count - 1 else 0.0 )
        box( r0, r1, 3.6, 5.8, z0 + 1.0, z1 - 1.0, DOOR )
    # A dark backing in the board gaps.
    box( n0 + 0.5, n1 - 0.5, 3.4, 3.6, z0 + 1.0, z1 - 1.0, "rw_steel_soot" )
    # The frame: steel angle round the leaf, and a ledge across the middle.
    for r0, r1, za, zb in ( ( n0, n1, z1 - 2.5, z1 ), ( n0, n1, z0, z0 + 2.5 ), ( n0, n0 + 2.5, z0, z1 ), ( n1 - 2.5, n1, z0, z1 ) ):
        box( r0, r1, 3.4, 6.4, za, zb, IRON_DARK )
    zm = ( z0 + z1 ) / 2
    box( n0 + 2.5, n1 - 2.5, 5.8, 6.8, zm - 2.5, zm + 2.5, DOOR )
    # Two braces, rising towards the hanging side (the leaf's closing edge is n0).
    for za, zb in ( ( z0 + 3.0, zm - 2.5 ), ( zm + 2.5, z1 - 3.0 ) ):
        model.beam( ( d( 6.3 ), n0 + 4.0, za + 2.0 ), ( d( 6.3 ), n1 - 4.0, zb - 2.0 ), ( 4.5, 1.0 ), DOOR, up=( 1, 0, 0 ) )
    # A 900 mm steel kick plate over the boards' foot.
    box( n0 + 2.5, n1 - 2.5, 5.8, 6.2, z0 + 2.5, z0 + 36.0, "rw_steel_soot" )
    # A pull handle on the closing edge.
    P.tube_path( model, [ ( d( 6.2 ), n0 + 6.0, zm - 14.0 ), ( d( 8.5 ), n0 + 6.0, zm - 12.0 ), ( d( 8.5 ), n0 + 6.0, zm + 12.0 ),
                          ( d( 6.2 ), n0 + 6.0, zm + 14.0 ) ], 0.55, IRON_DARK, sides=8 )
    # Roller hangers: a strap up from the top rail to a wheel in the track.
    for r in ( n0 + 16.0, n1 - 16.0 ):
        box( r - 2.0, r + 2.0, 6.4, 7.0, z1 - 10.0, z1 + 11.0, IRON_DARK )
        for k in range( 2 ):
            P.bolt( model, ( d( 7.0 ), r, z1 - 7.0 + 4.0 * k ), ( sgn, 0, 0 ), radius=0.5, length=0.3, paint=IRON_DARK, washer=False )
        a, b = sorted( ( d( 4.0 ), d( 6.4 ) ) )
        # The wheel, its axle along e.
        c = np.array( ( ( a + b ) / 2, r, z1 + 10.5 ) )
        pts0, pts1 = [], []
        for k in range( 12 ):
            t = 2 * math.pi * k / 12
            off = np.array( ( 0.0, 2.2 * math.cos( t ), 2.2 * math.sin( t ) ) )
            pts0.append( c + off + ( -1.2, 0, 0 ) )
            pts1.append( c + off + ( 1.2, 0, 0 ) )
        for k in range( 12 ):
            j = ( k + 1 ) % 12
            P._poly( model, IRON_DARK, [ pts0[k], pts0[j], pts1[j], pts1[k] ], ( pts0[k] + pts0[j] ) / 2 - c - ( -1.2, 0, 0 ) )
        P._poly( model, IRON_DARK, pts0, ( -1, 0, 0 ) )
        P._poly( model, IRON_DARK, pts1, ( 1, 0, 0 ) )


def door_track( model, face, sgn, n0, n1, z, brackets ):
    """ The doors' top track along a wall (face e, outward sgn) from n0 to n1: a 3 x 4 in steel channel, its lips
    down, its underside at z, on brackets bolted to the lintels and the wall at the n positions given. """
    def d( x ):
        return face + sgn * x

    def box( r0, r1, x0, x1, za, zb, paint=IRON_DARK ):
        a, b = sorted( ( d( x0 ), d( x1 ) ) )
        model.box( ( a, r0, za ), ( b, r1, zb ), paint )

    box( n0, n1, 3.3, 7.7, z + 3.4, z + 4.0 )            # the channel's web, on top
    box( n0, n1, 3.3, 3.8, z, z + 3.4 )                  # its flanges
    box( n0, n1, 7.2, 7.7, z, z + 3.4 )
    box( n0, n0 + 0.5, 3.3, 7.7, z, z + 3.4 )            # end stops
    box( n1 - 0.5, n1, 3.3, 7.7, z, z + 3.4 )
    for r in brackets:
        box( r - 1.5, r + 1.5, 0.0, 3.3, z + 2.0, z + 4.0 )
        box( r - 1.5, r + 1.5, 0.0, 0.5, z - 2.0, z + 6.0 )
        P.bolt( model, ( d( 0.5 ), r, z + 4.8 ), ( sgn, 0, 0 ), radius=0.5, length=0.3, paint=IRON_DARK, washer=False )


# ---------------------------------------------------------------------------------------------------------------------
# The shed's arcade: soot run-off

def runoff( model, axis, at, out, r0, r1, z, rng, paint="rw_sandstone_soot", density=0.12, short=( 3.0, 9.0 ),
            long=( 10.0, 30.0 ), long_share=0.25 ):
    """ Dark run-off under a moulding on a wall face (at, facing out across axis) from r0 to r1, hanging from z: a
    ragged band of drips of varied width and length, a hair proud of the face. """
    d = at + out * 0.05

    def p( r, zz ):
        return ( r, d, zz ) if axis == "e" else ( d, r, zz )
    normal = ( 0.0, out, 0.0 ) if axis == "e" else ( out, 0.0, 0.0 )
    r = r0
    while r < r1 - 1.0:
        w = min( rng.uniform( 1.5, 1.0 / density ), r1 - r )
        lo, hi = ( long if rng.random() < long_share else short )
        h = rng.uniform( lo, hi )
        taper = rng.uniform( 0.2, 0.6 )
        m = r + w / 2
        P._poly( model, paint, [ p( r, z ), p( r + w, z ), p( m + w * taper / 2, z - h ), p( m - w * taper / 2, z - h ) ], normal )
        r += w + rng.uniform( 0.5, 6.0 )


# ---------------------------------------------------------------------------------------------------------------------
# The wings' facades to the cab roads

def window_surround( model, axis, at, out, r0, r1, z0, z1, paint=STONE ):
    """ A moulded window surround on a wall face: an architrave band round the opening with ears at the head, a
    sill with a drip on two consoles, and a cornice hood over it. """
    def box( a, b, d0, d1, za, zb, chamfer=0.4 ):
        if axis == "n":
            lo, hi = ( at + out * d0, a, za ), ( at + out * d1, b, zb )
        else:
            lo, hi = ( a, at + out * d0, za ), ( b, at + out * d1, zb )
        P.chamfer_box( model, np.minimum( lo, hi ), np.maximum( lo, hi ), paint, chamfer=chamfer, skip=( "-z", ) )
    bw = 6.0
    # The architrave: jambs and head, stepped in two fasciae.
    box( r0 - bw, r0 - 1.0, 0.0, 2.2, z0, z1 + bw )
    box( r1 + 1.0, r1 + bw, 0.0, 2.2, z0, z1 + bw )
    box( r0 - bw, r1 + bw, 0.0, 2.2, z1 + 1.0, z1 + bw )
    box( r0 - 1.0, r0, 0.0, 1.2, z0, z1 + 1.0, chamfer=0.2 )
    box( r1, r1 + 1.0, 0.0, 1.2, z0, z1 + 1.0, chamfer=0.2 )
    box( r0 - 1.0, r1 + 1.0, 0.0, 1.2, z1, z1 + 1.0, chamfer=0.2 )
    # Ears at the head's corners.
    box( r0 - bw - 2.5, r0 - bw + 0.5, 0.0, 2.2, z1 - 4.0, z1 + bw )
    box( r1 + bw - 0.5, r1 + bw + 2.5, 0.0, 2.2, z1 - 4.0, z1 + bw )
    # The hood: a frieze and a small cornice.
    prof = [ ( 0.0, 0.0 ), ( 2.2, 0.0 ), ( 2.2, 5.0 ), ( 3.0, 5.6 ), ( 3.0, 6.6 ) ] + P.ogee( 3.0, 6.6, 5.2, 9.0, steps=3 )[1:] + \
           [ ( 5.2, 10.4 ), ( 0.0, 11.0 ) ]
    P.straight( model, axis, at, r0 - bw - 4.0, r1 + bw + 4.0, z1 + bw, out, prof, paint )
    # The sill, with a drip groove, on two small consoles.
    sill = [ ( 0.0, -3.0 ), ( 3.6, -3.0 ), ( 3.6, -2.2 ), ( 4.4, -2.2 ), ( 4.4, 0.0 ), ( 0.0, 1.6 ) ]
    P.straight( model, axis, at, r0 - bw - 3.0, r1 + bw + 3.0, z0, out, sill, paint )
    for r in ( r0 - bw / 2 - 1.0, r1 + bw / 2 + 1.0 ):
        box( r - 2.0, r + 2.0, 0.0, 3.0, z0 - 9.0, z0 - 3.0, chamfer=0.6 )


def dentils( model, axis, at, out, r0, r1, z, proud=( 10.0, 15.0 ), size=( 3.4, 3.5 ), pitch=6.5, paint=STONE ):
    """ A dentil course: blocks under a cornice's corona. """
    r = r0 + pitch / 2
    while r < r1 - pitch / 2 + 0.01:
        a, b = r - size[0] / 2, r + size[0] / 2
        d0, d1 = at + out * proud[0], at + out * proud[1]
        lo, hi = ( ( min( d0, d1 ), a, z ), ( max( d0, d1 ), b, z + size[1] ) ) if axis == "n" else \
                 ( ( a, min( d0, d1 ), z ), ( b, max( d0, d1 ), z + size[1] ) )
        model.box( lo, hi, paint )
        r += pitch


def radial_bars( model, axis, at, centre, spring, radius, angles=( 45.0, 135.0 ), paint=IRON, thick=1.2, depth=1.8,
                 hub=0.0 ):
    """ Glazing bars fanning out from an arched light's centre ( centre, spring ) to its arc. """
    for a in angles:
        t = math.radians( a )
        r0, z0 = centre + hub * math.cos( t ), spring + hub * math.sin( t )
        r1, z1 = centre + radius * math.cos( t ), spring + radius * math.sin( t )
        if axis == "n":
            model.beam( ( at, r0, z0 ), ( at, r1, z1 ), ( thick, depth ), paint, up=( 1, 0, 0 ) )
        else:
            model.beam( ( r0, at, z0 ), ( r1, at, z1 ), ( thick, depth ), paint, up=( 0, 1, 0 ) )


def half_round_gutter( model, edge_e, out, n0, n1, z_top, radius=2.4, paint="rw_steel_grey", brackets=36.0 ):
    """ A half-round gutter along n beside an eave's edge at edge_e (outside it towards out along e), its rim at z_top,
    on hoop brackets every brackets inches. """
    g = edge_e + out * ( radius + 0.4 )
    for k in range( 7 ):
        t0, t1 = math.pi * k / 7, math.pi * ( k + 1 ) / 7
        a = ( g + out * radius * math.cos( t0 ), z_top - radius * math.sin( t0 ) )
        b = ( g + out * radius * math.cos( t1 ), z_top - radius * math.sin( t1 ) )
        quad = [ ( a[0], n0, a[1] ), ( a[0], n1, a[1] ), ( b[0], n1, b[1] ), ( b[0], n0, b[1] ) ]
        mid = np.array( ( ( a[0] + b[0] ) / 2 - g, 0.0, ( a[1] + b[1] ) / 2 - z_top ) )
        P._poly( model, paint, quad, mid )
        P._poly( model, paint, quad, -mid )
    # A bead along the outer rim, and the hoops.
    lo, hi = sorted( ( g + out * radius, g + out * ( radius + 0.5 ) ) )
    model.box( ( lo, n0, z_top - 0.5 ), ( hi, n1, z_top + 0.2 ), paint )
    n = n0 + brackets / 2
    while n < n1:
        pts = [ ( g + out * radius * math.cos( math.pi * k / 6 ), n, z_top - radius * math.sin( math.pi * k / 6 ) - 0.3 )
                for k in range( 7 ) ]
        pts = [ ( edge_e, n, z_top - 0.3 ) ] + pts[::-1]
        P.tube_path( model, pts, 0.25, IRON_DARK, sides=4, cap=False )
        n += brackets
