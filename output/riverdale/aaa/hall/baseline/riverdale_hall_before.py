"""
Riverdale's reactor hall: the spent fuel building round its pool, built for Tools/riverdale_map.py.

Plan coordinates (map_kit's: e east, n north, z up, inches). The hall is e -1000..1000, n -200..2000 inside its 40 in
walls, its deck at z 0 and its roof's underside at 1000 (51 x 56 x 25 m, deeper than wide, so from its south end the
pool, the blocks and the far wall stand one behind another as in the reference). Built as the reference shows it:
- The pool, 1040 in across (26 m) round (0, 900): a stainless liner 520 in deep (13 m) under water 30 in below the
  deck, fuel racks on its floor, cyan lamps set into its wall, and a yellow railing all round on the coping
  (player-clipped up to the roof: nobody falls in).
- The fuel handling mast standing in the water under the overhead crane's trolley: four yellow columns, bracing and
  pipes, a lit cage round its foot.
- The overhead crane on runway beams along the side walls: two box girders across the hall round the mast with the
  operator's logo and "SWL 125 T", end carriages and a trolley.
- The control rooms: glass-fronted rooms at the upper level (z 288) on the side walls beside the pool's near half, on
  columns over the deck, each reached by a steel stair from the south deck to a landing at its south face. From the
  hall's south end the west one stands upper left, its stair rising away below it.
- B1 and B2: concrete blocks either side of the pool's far half, whose tops are part of the upper level's walkway
  along the side and north walls.
- Water purification tanks on the south-east deck, equipment cases with the logo on the south-west deck.
- The north wall: the logo between "CLEAN ENERGY / A BRIGHTER TOMORROW" and "SAFETY / PEOPLE / PROGRESS", pilasters,
  vertical pipe bundles, doors and lamps along both levels.
Doors: west and east (to the A2/A1 annexes), south (to the yard), and two north (to the north lane).
"""
import math

import numpy as np

import map_kit as K
import riverdale_parts as P
from riverdale_parts import v, card, box, UP, METAL, STONE

# The hall.
E0, E1, N0, N1 = -1000.0, 1000.0, -200.0, 2000.0
WT = 40.0
TOP = 1000.0
ROOF = 1040.0
POOL = ( 0.0, 900.0 )
POOL_R = 520.0
WATER_Z = -30.0
POOL_FLOOR = -520.0
UPPER = 288.0
SLAB = 18.0
CRANE_Z = 830.0
CRANE_N = ( 840.0, 960.0 )
MAST = ( 70.0, 900.0 )

# Openings: ( along from, along to, z top )
WEST_DOOR = ( -40.0, 80.0, 132.0 )          # n, in the west wall (from the annex); east the same
SOUTH_DOOR = ( -96.0, 96.0, 140.0 )          # e
NORTH_DOORS = ( ( -470.0, -350.0, 132.0 ), ( 350.0, 470.0, 132.0 ) )

# The west side's upper level (the east side is its mirror, e -> -e).
STAIR = ( -760.0, -700.0, 160.0, 580.0 )     # e0, e1, foot n, head n
LANDING = ( -1000.0, -560.0, 580.0, 660.0 )
CONTROL = ( -1000.0, -560.0, 660.0, 1200.0 )
WALKWAY = ( -1000.0, -860.0, 1200.0, 1860.0 )
BLOCK = ( -1000.0, -640.0, 1300.0, 1640.0 )
NORTH_WALK = ( -1000.0, 1000.0, 1860.0, 2000.0 )
CONTROL_TOP = 468.0
TANKS = ( ( 600.0, -10.0 ), ( 600.0, 170.0 ) )
TANK_R, TANK_H = 64.0, 400.0


def wall( m, axis, a0, a1, t0, t1, z0, z1, openings=(), paint="rv_wall", surface=STONE ):
    """ A wall running along axis ('e' or 'n') from a0 to a1, t0..t1 thick across, with openings ( b0, b1, top[, bottom] )
    (bottom: a window's sill; without it the opening runs down to z0): split into boxes round them, so the reveals are
    the boxes' own faces. """
    cuts = sorted( { a0, a1 } | { b for o in openings for b in o[:2] if a0 < b < a1 } )
    for b0, b1 in zip( cuts, cuts[1:] ):
        mid = ( b0 + b1 ) / 2
        hole = next( ( o for o in openings if o[0] <= mid <= o[1] ), None )
        spans = [ ( z0, z1 ) ] if hole is None else [ ( hole[2], z1 ) ] + ( [ ( z0, hole[3] ) ] if len( hole ) > 3 else [] )
        for za, zb in spans:
            if zb - za < 0.5:
                continue
            if axis == "e":
                box( m, b0, b1, t0, t1, za, zb, paint, surface )
            else:
                box( m, t0, t1, b0, b1, za, zb, paint, surface )


def ring( c, r, a0, a1, count ):
    return [ v( c[0] + r * math.cos( a ), c[1] + r * math.sin( a ), 0 ) for a in np.linspace( a0, a1, count ) ]


def deck( m, paint="rv_floor" ):
    """ The deck round the pool: wedges from the pool's edge out to the walls (each convex), drawn and solid. """
    c = v( *POOL, 0 )
    segs = 48
    corners = [ v( E1, N1, 0 ), v( E0, N1, 0 ), v( E0, N0, 0 ), v( E1, N0, 0 ) ]

    def hit( a ):
        d = v( math.cos( a ), math.sin( a ), 0 )
        ts = []
        if abs( d[0] ) > 1e-9:
            ts += [ ( E1 - c[0] ) / d[0], ( E0 - c[0] ) / d[0] ]
        if abs( d[1] ) > 1e-9:
            ts += [ ( N1 - c[1] ) / d[1], ( N0 - c[1] ) / d[1] ]
        return c + d * min( t for t in ts if t > 0 )

    for k in range( segs ):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * ( k + 1 ) / segs
        inner0 = c + v( math.cos( a0 ), math.sin( a0 ), 0 ) * POOL_R
        inner1 = c + v( math.cos( a1 ), math.sin( a1 ), 0 ) * POOL_R
        mid = []
        for q in corners:
            ang = math.atan2( q[1] - c[1], q[0] - c[0] ) % ( 2 * math.pi )
            if a0 < ang < a1:
                mid.append( ( ang, q ) )
        outline = [ inner0, hit( a0 ) ] + [ q for _, q in sorted( mid, key=lambda x: x[0] ) ] + [ hit( a1 ), inner1 ]
        card( m, paint, outline, UP )
        m.hull( [ p + UP * z for p in outline for z in ( -24.0, 0.0 ) ], STONE )


def pool( m ):
    """ The pool: liner walls and floor, the coping, cyan lamps in the wall, the fuel racks. Drawn only (the deck and
    the clips keep everyone out). """
    c = v( *POOL, 0 )
    segs = 64
    dirs = [ v( math.cos( 2 * math.pi * k / segs ), math.sin( 2 * math.pi * k / segs ), 0 ) for k in range( segs ) ]
    for k in range( segs ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % segs]
        p0, p1 = c + d0 * POOL_R, c + d1 * POOL_R
        card( m, "rv_liner", [ p0 + UP * POOL_FLOOR, p1 + UP * POOL_FLOOR, p1 + UP * 0, p0 + UP * 0 ], -( d0 + d1 ),
              normals=[ -d0, -d1, -d1, -d0 ] )
        q0, q1 = c + d0 * ( POOL_R + 14 ), c + d1 * ( POOL_R + 14 )
        card( m, "rv_plinth", [ p0 + UP * 3, p1 + UP * 3, q1 + UP * 3, q0 + UP * 3 ], UP )
        card( m, "rv_plinth", [ q0 + UP * 0, q1 + UP * 0, q1 + UP * 3, q0 + UP * 3 ], d0 + d1 )
        card( m, "rv_liner", [ p0 + UP * -2, p1 + UP * -2, p1 + UP * 3, p0 + UP * 3 ], -( d0 + d1 ) )
    card( m, "rv_liner", [ c + d * POOL_R + UP * POOL_FLOOR for d in dirs ], UP )
    # Lamps in the wall a little under the water.
    for k in range( 24 ):
        a = 2 * math.pi * ( k + 0.5 ) / 24
        d = v( math.cos( a ), math.sin( a ), 0 )
        right = np.cross( UP, -d )
        P.quad( m, "rv_lamp_cyan", c + d * ( POOL_R - 0.4 ) + UP * ( WATER_Z - 34 ), right, UP, 34, 8 )
        P.quad( m, "rv_dark", c + d * ( POOL_R - 0.2 ) + UP * ( WATER_Z - 34 ), right, UP, 40, 12 )
    # Fuel racks: modules on legs, their cells glowing.
    rng = np.random.default_rng( 3 )
    for i in range( -3, 4 ):
        for j in range( -3, 4 ):
            e, n = i * 124.0, j * 124.0
            if math.hypot( e, n ) > POOL_R - 110 or ( abs( e - ( MAST[0] - POOL[0] ) ) < 120 and abs( n ) < 120 ):
                continue
            if rng.random() < 0.16:
                continue
            h = 150.0 if rng.random() < 0.7 else 110.0
            lo = v( POOL[0] + e - 52, POOL[1] + n - 52, POOL_FLOOR + 10 )
            hi = v( POOL[0] + e + 52, POOL[1] + n + 52, POOL_FLOOR + 10 + h )
            m.box( lo, hi, { "default": "rv_rack", "-z": None } )
            for sx in ( -1, 1 ):
                for sy in ( -1, 1 ):
                    box( m, POOL[0] + e + sx * 46 - 3, POOL[0] + e + sx * 46 + 3, POOL[1] + n + sy * 46 - 3, POOL[1] + n + sy * 46 + 3,
                         POOL_FLOOR, POOL_FLOOR + 10, "rv_liner" )


def mast( m, solid ):
    """ The fuel handling mast from the pool floor up to the crane's hook block, and its lit cage under the water. """
    c = v( *MAST, 0 )
    top = CRANE_Z - 40
    s = 30.0
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            box( m, c[0] + sx * s - 4, c[0] + sx * s + 4, c[1] + sy * s - 4, c[1] + sy * s + 4, POOL_FLOOR, top, "rv_yellow" )
    for z in np.arange( POOL_FLOOR + 40, top - 20, 110.0 ):
        for a, b in ( ( ( -s, -s ), ( s, -s ) ), ( ( s, -s ), ( s, s ) ), ( ( s, s ), ( -s, s ) ), ( ( -s, s ), ( -s, -s ) ) ):
            P.rod( m, c + v( a[0], a[1], z ), c + v( b[0], b[1], z ), 1.6, "rv_steel", 6 )
            P.rod( m, c + v( a[0], a[1], z ), c + v( b[0], b[1], z + 110 ), 1.0, "rv_steel", 5 )
    for z in ( 110.0, 290.0, 480.0, 680.0 ):
        box( m, c[0] - s - 5, c[0] + s + 5, c[1] - s - 5, c[1] + s + 5, z, z + 14, "rv_yellow" )
    for dx, dy, r in ( ( -12, -10, 4.5 ), ( 12, -10, 4.5 ), ( 0, 12, 6.0 ), ( -18, 14, 2.5 ), ( 18, 14, 2.5 ) ):
        P.rod( m, c + v( dx, dy, POOL_FLOOR + 20 ), c + v( dx, dy, top + 50 ), r, "rv_pipe", 10 )
    P.cylinder( m, c, 22.0, POOL_FLOOR + 20, -80.0, "rv_cyan_glow", 16 )
    for z in np.arange( POOL_FLOOR + 30, -70.0, 36.0 ):
        P.cylinder( m, c, 54.0, z, z + 3, "rv_steel", 20 )
    for k in range( 12 ):
        a = 2 * math.pi * k / 12
        d = v( math.cos( a ), math.sin( a ), 0 )
        P.rod( m, c + d * 54 + UP * ( POOL_FLOOR + 20 ), c + d * 54 + UP * -70, 1.6, "rv_rack", 6 )
    box( m, c[0] - 26, c[0] + 26, c[1] - 18, c[1] + 18, top, top + 30, "rv_yellow" )
    for dx in ( -14, -5, 5, 14 ):
        P.rod( m, c + v( dx, 0, top + 30 ), c + v( dx, 0, CRANE_Z + 70 ), 0.9, "rv_dark", 5 )
    solid.collision_box( c + v( -40, -40, POOL_FLOOR ), c + v( 40, 40, top + 30 ), METAL )


def crane( m ):
    """ The overhead travelling crane: runway beams on corbels along the side walls, two box girders round the mast,
    end carriages, the trolley. """
    for sx in ( -1, 1 ):
        e = sx * ( E1 - 20 )
        P.i_beam( m, ( e, N0 + 10, CRANE_Z - 18 ), ( e, N1 - 10, CRANE_Z - 18 ), 36, 16, "rv_steel" )
        box( m, e - 1.5, e + 1.5, N0 + 10, N1 - 10, CRANE_Z, CRANE_Z + 3, "rv_zinc" )
        for n in np.arange( N0 + 120, N1, 280.0 ):
            a, b = sorted( ( sx * E1, sx * ( E1 - 34 ) ) )
            box( m, a, b, n - 22, n + 22, CRANE_Z - 70, CRANE_Z - 36, "rv_wall" )
    gz = CRANE_Z + 6
    for n in CRANE_N:
        box( m, E0 + 40, E1 - 40, n - 15, n + 15, gz, gz + 64, "rv_yellow" )
        for e in np.arange( E0 + 80, E1 - 40, 80.0 ):
            for sn in ( -1, 1 ):
                box( m, e - 1, e + 1, min( n + sn * 15, n + sn * 16.2 ), max( n + sn * 15, n + sn * 16.2 ), gz + 4, gz + 60, "rv_yellow" )
    for sx in ( -1, 1 ):
        a, b = sorted( ( sx * ( E1 - 40 ), sx * ( E1 - 4 ) ) )
        box( m, a, b, CRANE_N[0] - 50, CRANE_N[1] + 50, gz - 4, gz + 56, "rv_yellow" )
        for n in ( CRANE_N[0] - 30, CRANE_N[1] + 30 ):
            P.cylinder( m, ( sx * ( E1 - 20 ), n ), 10, gz - 10, gz - 2, "rv_dark", 12 )
    # A walkway with a railing along the south girder's outside.
    s0 = CRANE_N[0] - 15
    box( m, E0 + 40, E1 - 40, s0 - 25, s0, gz + 60, gz + 62, "rv_grating" )
    P.railing( m, [ ( E0 + 50, s0 - 25 ), ( E1 - 50, s0 - 25 ) ], gz + 62, "rv_yellow", height=36, post_every=80 )
    # Trolley and hoist over the mast.
    tx = MAST[0]
    box( m, tx - 80, tx + 80, CRANE_N[0] - 20, CRANE_N[1] + 20, gz + 64, gz + 92, "rv_yellow" )
    P.rod( m, ( tx - 60, POOL[1], gz + 78 ), ( tx + 60, POOL[1], gz + 78 ), 20, "rv_steel", 16, caps=True )
    # Lettering on the south girder's south face: the logo and the name, and the safe working load.
    f = s0 - 0.3
    P.letters( m, "logo_wordmark", ( -160, f, gz + 32 ), ( 1, 0, 0 ), 42, "dark" )
    P.letters( m, "swl", ( 720, f, gz + 30 ), ( 1, 0, 0 ), 20, "dark" )
    P.letters( m, "swl", ( -720, f, gz + 30 ), ( 1, 0, 0 ), 20, "dark" )
    f2 = CRANE_N[1] + 15.3
    P.letters( m, "logo_wordmark", ( 160, f2, gz + 32 ), ( -1, 0, 0 ), 42, "dark" )
    for sx in ( -1, 1 ):
        P.beacon( m, f"Crane beacon {sx}", ( sx * ( E1 - 60 ), POOL[1], gz + 56 ), light=False )


def shell( m ):
    """ The walls, the thresholds, the roof and its trusses, the pilasters. """
    wall( m, "e", E0 - WT, E1 + WT, N0 - WT, N0, 0, ROOF, [ SOUTH_DOOR ] )
    wall( m, "e", E0 - WT, E1 + WT, N1, N1 + WT, 0, ROOF, list( NORTH_DOORS ) )
    for sx in ( -1, 1 ):
        e0, e1 = ( E0 - WT, E0 ) if sx < 0 else ( E1, E1 + WT )
        wall( m, "n", N0, N1, e0, e1, 0, ROOF, [ WEST_DOOR ] )
    box( m, SOUTH_DOOR[0], SOUTH_DOOR[1], N0 - WT, N0, -24, 0, { "default": None, "+z": "rv_plinth" }, STONE )
    for o in NORTH_DOORS:
        box( m, o[0], o[1], N1, N1 + WT, -24, 0, { "default": None, "+z": "rv_plinth" }, STONE )
    for e0, e1 in ( ( E0 - WT, E0 ), ( E1, E1 + WT ) ):
        box( m, e0, e1, WEST_DOOR[0], WEST_DOOR[1], -24, 0, { "default": None, "+z": "rv_plinth" }, STONE )
    box( m, E0 - WT, E1 + WT, N0 - WT, N1 + WT, TOP, ROOF, { "default": "rv_wall", "-z": "rv_steel" }, STONE )
    for a, b, c, d in ( ( E0 - WT, E1 + WT, N0 - WT, N0 - WT + 12 ), ( E0 - WT, E1 + WT, N1 + WT - 12, N1 + WT ),
                        ( E0 - WT, E0 - WT + 12, N0 - WT, N1 + WT ), ( E1 + WT - 12, E1 + WT, N0 - WT, N1 + WT ) ):
        box( m, a, b, c, d, ROOF, ROOF + 40, "rv_wall", STONE )
    for e in np.arange( E0 + 125, E1, 250.0 ):
        P.truss( m, ( e, N0 + 4, TOP - 66 ), ( e, N1 - 4, TOP - 66 ), 60, "rv_steel", panel=110 )
    for e in ( -833.0, -500.0, -167.0, 167.0, 500.0, 833.0 ):
        box( m, e - 24, e + 24, N1 - 22, N1, 0, TOP, "rv_wall", STONE )
    for sx in ( -1, 1 ):
        for n, z0 in ( ( -60.0, 0.0 ), ( 400.0, 0.0 ), ( 1250.0, UPPER ), ( 1750.0, UPPER ) ):
            a, b = ( E0, E0 + 22 ) if sx < 0 else ( E1 - 22, E1 )
            box( m, a, b, n - 24, n + 24, z0, TOP, "rv_wall", STONE )
    for a, b, c, d in ( ( E0, E1, N0, N0 + 1 ), ( E0, E1, N1 - 1, N1 ), ( E0, E0 + 1, N0, N1 ), ( E1 - 1, E1, N0, N1 ) ):
        box( m, a, b, c, d, 0, 30, "rv_plinth" )
    for e in np.arange( E0 - WT + 40, E1 + WT, 260.0 ):
        if abs( e ) < 150:
            continue
        box( m, e - 20, e + 20, N0 - WT - 14, N0 - WT, 0, ROOF + 20, "rv_wall", STONE )


def upper_side( m, sx ):
    """ One side's upper level (sx -1 west, 1 east; the constants are the west side's, mirrored by e -> -e for the
    east): the stair, the landing, the control room on its columns, the walkway, the block, railings, lamps. """
    f = -sx

    def E( a, b ):
        return ( min( f * a, f * b ), max( f * a, f * b ) )

    def slab( r ):
        a, b = E( r[0], r[1] )
        box( m, a, b, r[2], r[3], UPPER - SLAB, UPPER, { "default": "rv_wall", "+z": "rv_floor" }, STONE )

    for r in ( LANDING, CONTROL, WALKWAY ):
        slab( r )
    inward = v( f, 0, 0 )
    right = np.cross( UP, inward )
    # The block (B1 west, B2 east), solid to the upper level.
    a, b = E( BLOCK[0], BLOCK[1] )
    box( m, a, b, BLOCK[2], BLOCK[3], 0, UPPER, { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    face = f * BLOCK[1]
    mid_n = ( BLOCK[2] + BLOCK[3] ) / 2
    P.letters( m, "B1" if sx < 0 else "B2", ( face, mid_n, 176 ), right, 104, "dark" )
    P.life_ring( m, ( face, BLOCK[2] + 50, 70 ), inward )
    P.door( m, ( face, BLOCK[3] - 70, 0 ), right, 60, 90, double=False )
    P.wall_light( m, f"Block {sx} lamp", ( face, BLOCK[3] - 70, 104 ), inward, "warm", 260 )
    box( m, *E( BLOCK[1] - 2, BLOCK[1] + 1 ), BLOCK[2], BLOCK[3], UPPER - 14, UPPER, "rv_steel" )
    for n in ( BLOCK[2] + 18, BLOCK[2] + 32 ):
        P.pipe( m, [ ( face + f * 8, n, UPPER - 20 ), ( face + f * 8, n, 40 ), ( face + f * 30, n, 14 ) ], 3.2, "rv_pipe", 10 )
    # The control room: a knee wall and glazing on its pool side and its south side, a door from the landing, a wall and
    # a door to the walkway on its north side, the ceiling.
    c0, c1, cn0, cn1 = CONTROL
    ce = f * c1
    ea, eb = min( ce, ce - 14 * f ), max( ce, ce - 14 * f )
    knee, head = UPPER + 36, UPPER + 150
    box( m, ea, eb, cn0, cn1, UPPER, knee, "rv_wall", STONE )
    box( m, ea, eb, cn0, cn1, head, CONTROL_TOP, "rv_wall", STONE )
    for n in np.arange( cn0 + 2, cn1 + 1, 54.0 ):
        box( m, ea + 4, eb - 4, n - 2, n + 2, knee, head, "rv_frame" )
    box( m, ea - 1.5, eb + 1.5, cn0, cn1, knee - 2, knee + 2, "rv_frame" )
    door_e = ( -680.0, -610.0 )
    sa, sb = cn0, cn0 + 14
    for e0_, e1_ in ( ( c0, door_e[0] ), ( door_e[1], c1 ) ):
        box( m, *E( e0_, e1_ ), sa, sb, UPPER, knee, "rv_wall", STONE )
    box( m, *E( door_e[0], door_e[1] ), sa, sb, UPPER + 96, head, "rv_wall", STONE )
    box( m, *E( c0, c1 ), sa, sb, head, CONTROL_TOP, "rv_wall", STONE )
    for e in np.arange( c0 + 40, c1 - 10, 54.0 ):
        if door_e[0] - 6 < e < door_e[1] + 6:
            continue
        box( m, *E( e - 2, e + 2 ), sa + 4, sb - 4, knee, head, "rv_frame" )
    for e0_, e1_ in ( ( c0, door_e[0] ), ( door_e[1], c1 ) ):
        box( m, *E( e0_, e1_ ), sa - 1.5, sb + 1.5, knee - 2, knee + 2, "rv_frame" )
    wall( m, "e", *E( c0, c1 ), cn1 - 14, cn1, UPPER, CONTROL_TOP, [ ( *E( -970, -890 ), UPPER + 96 ) ] )
    box( m, *E( c0, c1 ), cn0, cn1, CONTROL_TOP - 18, CONTROL_TOP, { "default": "rv_wall", "-z": "rv_steel" }, STONE )
    P.letters( m, "control_room", ( f * ( c0 + c1 ) / 2, cn0 - 0.3, head + 8 ), v( 1, 0, 0 ), 12, "light" )
    P.letters( m, "control_room", ( ce + f * 0.3, ( cn0 + cn1 ) / 2, head + 8 ), np.cross( UP, inward ), 12, "light" )
    for n in ( 760.0, 930.0, 1100.0 ):
        P.ceiling_light( m, f"Control {sx} {n}", ( f * -780, n, CONTROL_TOP - 22 ), ( 0, 1 ), "cool", light=False, size=( 36, 10, 3 ) )
    P.LIGHTS.append( ( f"Control room {sx}", ( f * -780, 930.0, 410.0 ), "1.6,1.8,2.1,1", 520, True ) )
    for n in ( 760.0, 1100.0 ):
        P.LIGHTS.append( ( f"Control fill {sx} {n}", ( f * -780, n, 420.0 ), "1.1,1.25,1.45,1", 360, False ) )
    # Inside: two rows of desks with monitors facing the pool, big screens on the back wall, chairs.
    for row_e in ( -860.0, -690.0 ):
        de = f * row_e
        box( m, de - 14, de + 14, 720, 1140, UPPER, UPPER + 30, "rv_desk", METAL )
        for k, n in enumerate( np.arange( 740, 1130, 48.0 ) ):
            mx = de + f * 6
            P.obox( m, ( mx, n, UPPER + 31 ), ( 0, 1 ), ( 6, 10, 2 ), "rv_dark" )
            P.obox( m, ( mx, n, UPPER + 43 ), ( 0, 1 ), ( 1.5, 22, 14 ), "rv_dark" )
            P.screen( m, ( "schematic", "graphs", "table", "camera" )[( k + int( row_e ) ) % 4], ( mx + f * 0.8, n, UPPER + 43 ), v( 0, f, 0 ), 12 )
            P.obox( m, ( de - f * 26, n, UPPER + 10 ), ( 1, 0 ), ( 18, 18, 20 ), "rv_chair" )
    back = f * c0
    for k, n in enumerate( ( 800.0, 930.0, 1060.0 ) ):
        P.obox( m, ( back + f * 1.5, n, UPPER + 100 ), ( 0, 1 ), ( 3, 110, 62 ), "rv_dark" )
        P.screen( m, ( "schematic", "camera", "graphs" )[k], ( back + f * 3.2, n, UPPER + 100 ), v( 0, f, 0 ), 56 )
    # Columns under the control room and the landing.
    for e, n in ( ( -572.0, 592.0 ), ( -572.0, 860.0 ), ( -572.0, 1188.0 ), ( -830.0, 592.0 ), ( -830.0, 1188.0 ) ):
        box( m, f * e - 12, f * e + 12, n - 12, n + 12, 0, UPPER - SLAB, "rv_wall", STONE )
    for n in np.arange( 1280, 1860, 160.0 ):
        if BLOCK[2] - 20 < n < BLOCK[3] + 20:
            continue
        x0, x1 = f * -1000, f * -870
        for dn in ( -3, 3 ):
            card( m, "rv_steel", [ v( x0, n + dn, UPPER - SLAB - 60 ), v( x0, n + dn, UPPER - SLAB ), v( x1, n + dn, UPPER - SLAB ) ], v( 0, dn, 0 ), both=True )
    # The stair from the south deck up to the landing, rails both sides.
    mid_e = f * ( STAIR[0] + STAIR[1] ) / 2
    P.stairs( m, ( mid_e, STAIR[2] ), ( mid_e, STAIR[3] ), STAIR[1] - STAIR[0], 0, UPPER, name=f"hall stair {sx}" )
    # Railings round the upper level's open edges (clipped well up).
    P.railing( m, mirror( [ ( -1000, 580 ), ( -760, 580 ) ], f ), UPPER, clip_to=180, name=f"landing rail a {sx}" )
    P.railing( m, mirror( [ ( -700, 580 ), ( -560, 580 ), ( -560, 660 ) ], f ), UPPER, clip_to=180, name=f"landing rail b {sx}" )
    P.railing( m, mirror( [ ( -860, 1200 ), ( -860, BLOCK[2] ), ( -640, BLOCK[2] ), ( -640, BLOCK[3] ), ( -860, BLOCK[3] ), ( -860, 1860 ),
                           ( -360, 1860 ) ], f ), UPPER, clip_to=200, name=f"upper rail {sx}" )
    # Lamps: under the walkway, on the side wall over the deck, at the landing.
    for n in ( 1400.0, 1780.0 ):
        P.wall_light( m, f"Deck lamp {sx} {n}", ( f * E0, n, UPPER - SLAB - 34 ), inward, "warm", 380 )
    for n in ( 150.0, 450.0 ):
        P.wall_light( m, f"Side lamp {sx} {n}", ( f * E0, n, 230 ), inward, "warm", 380 )
    P.wall_light( m, f"Landing lamp {sx}", ( f * E0, 620, UPPER + 110 ), inward, "warm", 300 )
    P.life_ring( m, ( f * E0, 300, 64 ), inward )


def mirror( pts, f ):
    return [ ( f * p[0], p[1] ) for p in pts ]


def north_wall( m ):
    """ The north wall's inside: its walkway and railing, doors on both levels, pipes, lamps, the logo and slogans. """
    box( m, NORTH_WALK[0], NORTH_WALK[1], NORTH_WALK[2], NORTH_WALK[3], UPPER - SLAB, UPPER, { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    P.railing( m, [ ( -360, NORTH_WALK[2] ), ( 360, NORTH_WALK[2] ) ], UPPER, clip_to=200, name="north rail" )
    face = N1
    out = v( 0, -1, 0 )
    right = np.cross( UP, out )
    for e in ( -680.0, -330.0, 330.0, 680.0 ):
        P.door( m, ( e, face, UPPER ), right, 72, 90, double=False )
        P.wall_light( m, f"Upper door lamp {e}", ( e, face, UPPER + 110 ), out, "warm", 300 )
    for o in NORTH_DOORS:
        e = ( o[0] + o[1] ) / 2
        P.wall_light( m, f"North door lamp {e}", ( e, face, 150 ), out, "warm", 320 )
    for e in ( -680.0, -200.0, 200.0, 680.0 ):
        P.wall_light( m, f"North deck lamp {e}", ( e, face, UPPER - SLAB - 30 ), out, "warm", 340 )
    # The logo between the slogans, as the reference's far wall.
    P.letters( m, "logo", ( 0, face, 700 ), right, 270, "dark" )
    # Each in its bay between the pilasters (e +-167 and +-500, 48 wide).
    P.letters( m, "clean_energy", ( -333, face, 700 ), right, 165, "dark" )
    P.letters( m, "safety", ( 333, face, 700 ), right, 200, "dark" )
    for e0 in ( -666.0, -928.0, 666.0, 928.0 ):
        for k, ( dx, r ) in enumerate( ( ( -26, 7.0 ), ( -8, 9.0 ), ( 12, 6.0 ), ( 30, 11.0 ) ) ):
            x = e0 + dx
            P.pipe( m, [ ( x, face - 16 - k % 2 * 6, UPPER + 100 ), ( x, face - 16 - k % 2 * 6, TOP - 10 ) ], r, "rv_pipe", 12, caps=False )
        for z in np.arange( UPPER + 160, TOP, 180.0 ):
            box( m, e0 - 40, e0 + 40, face - 32, face, z, z + 3, "rv_steel" )
    for n_off, r in ( ( 10, 4.0 ), ( 22, 5.5 ) ):
        P.pipe( m, [ ( E0 + n_off, N0 + 200, 236 + r ), ( E0 + n_off, N1 - n_off, 236 + r ), ( E1 - n_off, N1 - n_off, 236 + r ),
                     ( E1 - n_off, N0 + 200, 236 + r ) ], r, "rv_pipe", 10 )
    for sx in ( -1, 1 ):
        for n0 in ( 1450.0, 220.0 ):
            for k, ( dx, r ) in enumerate( ( ( 8, 7.0 ), ( 26, 9.0 ), ( 44, 6.0 ) ) ):
                e = sx * ( E1 - dx - 4 )
                z0 = UPPER + 120 if n0 > 1000 else 40
                P.pipe( m, [ ( e, n0 + k * 22, z0 ), ( e, n0 + k * 22, TOP - 10 ) ], r, "rv_pipe", 12, caps=False )
    for e in ( -260.0, 260.0 ):
        P.life_ring( m, ( e, face, 64 ), out )


def deck_props( m, dress ):
    """ The pool's railing and its signs, the tanks, the cases, the floor's gratings and line. """
    c = v( *POOL, 0 )
    pts = ring( c, POOL_R + 10, 0, 2 * math.pi, 49 )[:-1]
    P.railing( m, [ ( p[0], p[1] ) for p in pts ], 3, clip_to=997, closed=True, name="pool rail", post_every=56 )
    for a_deg in ( 255.0, 285.0, 75.0, 180.0, 0.0 ):
        a = math.radians( a_deg )
        d = v( math.cos( a ), math.sin( a ), 0 )
        at = c + d * ( POOL_R + 11.5 ) + UP * 26
        P.plate( m, "caution", at, np.cross( UP, d ), 24, back="rv_yellow" )
    # The water purification tanks on the south-east deck, their name towards the hall's south end.
    for k, ( e, n ) in enumerate( TANKS ):
        P.tank( dress, ( e, n ), TANK_R, TANK_H, "rv_white", facing=( -0.6, -1 ), letters_name="water_purification" if k == 0 else None )
        P.pipe( dress, [ ( e, n, TANK_H + 20 ), ( e, n, TANK_H + 60 ), ( E1 - 30, n, TANK_H + 60 ) ], 6.0, "rv_pipe", 12, flanges=( 0, ) )
        P.pipe( dress, [ ( e + TANK_R * 0.7, n + TANK_R * 0.7, 40 ), ( e + 110, n + 110, 40 ), ( E1 - 20, n + 110, 40 ) ], 4.0, "rv_pipe", 10, flanges=( 0, ) )
    box( dress, 680, 760, 60, 110, 0, 8, "rv_steel", METAL )
    P.cylinder( dress, ( 720, 85 ), 14, 8, 40, "rv_steel", 14, top="rv_steel" )
    rng = np.random.default_rng( 4 )
    for k, ( e, n, kind ) in enumerate( ( ( -620, -60, "dark" ), ( -560, 1500, "olive" ), ( 560, 1500, "olive" ), ( -760, 1740, "dark" ),
                                          ( 760, 1720, "dark" ), ( -300, 1780, "dark" ), ( 300, 1790, "olive" ), ( -880, 420, "olive" ),
                                          ( 880, 440, "dark" ) ) ):
        P.case_stack( dress, ( e, n ), ( 1, 0.15 * rng.normal() ), kind, seed=k + 10 )
    # The foreground cases with the logo, as the reference's, and a clipboard on one.
    for e, n, z in ( ( -420, 110, 0 ), ( -372, 152, 0 ), ( -398, 130, 26 ), ( -472, 80, 0 ), ( 440, -60, 0 ) ):
        P.case( dress, ( e, n ), ( 48, 30, 26 ), ( 1, 0 ), "rv_case", z )
        P.letters( dress, "logo_wordmark", ( e, n - 15.3, z + 13 ), ( 1, 0, 0 ), 9, "light" )
    P.plate( dress, "clipboard", ( -394, 128, 52.2 ), ( 1, 0.25, 0 ), 13, up=( -0.25, 1, 0 ), off=0.05 )
    # Trench gratings across the south deck, and grating panels where the reference's walkway is.
    for e0, e1, n0, n1 in ( ( -420, 420, 300, 324 ), ( -660, -560, -120, 300 ), ( 560, 660, -120, 300 ) ):
        box( m, e0, e1, n0, n1, 0.0, 0.25, { "default": None, "+z": "rv_grating" } )
        box( m, e0 + 3, e1 - 3, n0 + 3, n1 - 3, -0.2, 0.0, { "default": None, "+z": "rv_black" } )
    segs = 64
    for k in range( segs ):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * ( k + 1 ) / segs
        d0, d1 = v( math.cos( a0 ), math.sin( a0 ), 0 ), v( math.cos( a1 ), math.sin( a1 ), 0 )
        q0, q1 = c + d0 * ( POOL_R + 40 ), c + d1 * ( POOL_R + 40 )
        r0, r1 = c + d0 * ( POOL_R + 44 ), c + d1 * ( POOL_R + 44 )
        card( m, "rv_line_yellow", [ q0 + UP * 0.3, q1 + UP * 0.3, r1 + UP * 0.3, r0 + UP * 0.3 ], UP )


HIGH_BAYS = [ ( e, n ) for e in ( -750.0, -250.0, 250.0, 750.0 ) for n in ( 120.0, 600.0, 1350.0, 1780.0 ) ]


def lights():
    """ The hall's own lights besides the fixtures': high bays under the roof, the pool's lamps under the water and its
    glow over it. """
    out = [ ( f"High bay {e} {n}", ( e, n, TOP - 130 ), "1.05,1.18,1.35,1", 1100, False ) for e, n in HIGH_BAYS ]
    c = POOL
    for k in range( 8 ):
        a = 2 * math.pi * ( k + 0.5 ) / 8
        out.append( ( f"Pool lamp {k}", ( c[0] + 420 * math.cos( a ), c[1] + 420 * math.sin( a ), WATER_Z - 70 ), "0.10,0.42,0.52,1", 720, False ) )
    for k in range( 6 ):
        a = 2 * math.pi * k / 6
        out.append( ( f"Pool glow {k}", ( c[0] + 270 * math.cos( a ), c[1] + 270 * math.sin( a ), 70 ), "0.05,0.27,0.38,1", 1050, False ) )
    return out


def high_bays( m ):
    for e, n in HIGH_BAYS:
        P.ceiling_light( m, f"bay {e} {n}", ( e, n, TOP - 84 ), ( 0, 1 ), "cool", light=False, size=( 60, 14, 6 ) )
        P.rod( m, ( e, n, TOP - 81 ), ( e, n, TOP - 66 ), 0.6, "rv_dark", 4 )


def build():
    """ Returns the hall's models: structure (solid), dressing (solid), pool (drawn only), water and glass. """
    hall, dress, pool_m, water, glass = K.Model(), K.Model(), K.Model(), K.Model(), K.Model()
    shell( hall )
    deck( hall )
    for sx in ( -1, 1 ):
        upper_side( hall, sx )
    north_wall( hall )
    crane( hall )
    mast( pool_m, hall )
    pool( pool_m )
    deck_props( hall, dress )
    high_bays( hall )
    c = v( *POOL, 0 )
    segs = 64
    card( water, "rv_pool_water", [ c + v( math.cos( 2 * math.pi * k / segs ), math.sin( 2 * math.pi * k / segs ), 0 ) * POOL_R + UP * WATER_Z
                                    for k in range( segs ) ], UP )
    # The control rooms' glazing: the pool side and the south side.
    for sx in ( -1, 1 ):
        f = -sx
        c0, c1, cn0, cn1 = CONTROL
        ge = f * ( c1 - 7 )
        glass.box( ( ge - 0.5, cn0 + 14, UPPER + 38 ), ( ge + 0.5, cn1, UPPER + 148 ), "rw_glass", "glass" )
        for e0_, e1_ in ( ( c0, -680.0 ), ( -610.0, c1 ) ):
            a, b = sorted( ( f * e0_, f * e1_ ) )
            glass.box( ( a, cn0 + 6.5, UPPER + 38 ), ( b, cn0 + 7.5, UPPER + 148 ), "rw_glass", "glass" )
    return hall, dress, pool_m, water, glass
