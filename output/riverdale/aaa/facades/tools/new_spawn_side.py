def spawn_side( m, sx ):
    """ The spawn strip (west e -2300..-1700): the boundary building's facade, the spawn building (B2 west, B1 east:
    the reference's, a stair up past its stencilled wing to a double door), a guard hut, barriers and lamps. """
    f = -sx

    def E( a, b ):
        return tuple( sorted( ( f * a, f * b ) ) )

    yard = "+e" if f > 0 else "-e"          # the faces towards the yard
    e_face = f * PLAY[0]
    a, b = E( PLAY[0], PLAY[0] - 300 )
    box( m, a, b, PLAY[2], PLAY[3], 0, BOUNDARY_TOP, { "default": "rv_wall", yard: None, "+z": "rv_plinth" }, STONE )
    for n in np.arange( PLAY[2] + 120, PLAY[3] - 60, 300.0 ):
        box( m, *sorted( ( e_face, e_face + f * 14 ) ), n - 22, n + 22, 0, BOUNDARY_TOP + 20, "rv_wall", STONE )
        F.coping( m, *sorted( ( e_face, e_face + f * 14 ) ), n - 22, n + 22, BOUNDARY_TOP + 20, over=1.5 )
    boundary_face( m, sx )
    # The spawn building's tall part: walls, the room's floor and roof. Its outer faces (and the walls' ends and the
    # doors' reveals, which would lie in them) are drawn by spawn_faces.
    t0, t1, tn0, tn1 = SPAWN_TALL
    w = 20.0
    door_a = ( -940.0, -870.0, SPAWN_ROOM_Z + 96, SPAWN_ROOM_Z )
    door_b = ( -800.0, -740.0, SPAWN_ROOM_Z + 96, SPAWN_ROOM_Z )
    H.wall( m, "n", tn0, tn1, *E( t1 - w, t1 ), 0, SPAWN_TOP, [ door_a, door_b ],
            paint={ "default": "rv_wall", yard: None, "-n": None, "+n": None } )
    H.wall( m, "e", *E( t0, t1 ), tn0, tn0 + w, 0, SPAWN_TOP, paint={ "default": "rv_wall", "-n": None, yard: None } )
    H.wall( m, "e", *E( t0, t1 ), tn1 - w, tn1, 0, SPAWN_TOP, paint={ "default": "rv_wall", "+n": None, yard: None } )
    box( m, *E( t0, t1 - w ), tn0 + w, tn1 - w, 0, SPAWN_ROOM_Z - 16, "rv_wall", STONE )
    box( m, *E( t0, t1 - w ), tn0 + w, tn1 - w, SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z, { "default": None, "+z": "rv_floor" }, STONE )
    box( m, *E( t0, t1 ), tn0, tn1, SPAWN_TOP - 18, SPAWN_TOP, { "default": None, "+z": "rv_plinth", "-z": "rv_steel" }, STONE )
    inward = "-e" if f > 0 else "+e"
    for ( a_, b_, c_, d_ ), inner in ( ( ( t0, t1, tn0, tn0 + 10 ), "+n" ), ( ( t0, t1, tn1 - 10, tn1 ), "-n" ),
                                       ( ( t1 - 10, t1, tn0, tn1 ), inward ) ):
        box( m, *E( a_, b_ ), c_, d_, SPAWN_TOP, SPAWN_TOP + 26, { "default": None, inner: "rv_wall" }, STONE )
        F.coping( m, *E( a_, b_ ), c_, d_, SPAWN_TOP + 26 )
    P.ceiling_light( m, f"Spawn room {sx}", ( f * ( t0 + t1 ) / 2, ( tn0 + tn1 ) / 2, SPAWN_TOP - 26 ), ( 0, 1 ), "cool", 380 )
    for k, n in enumerate( ( -1100.0, -1040.0, -980.0 ) ):
        box( m, *E( t0 + 4, t0 + 24 ), n - 26, n + 26, SPAWN_ROOM_Z, SPAWN_ROOM_Z + 80, "rv_steel", METAL )
    P.case_stack( m, ( f * -2200, -760 ), ( 0, 1 ), "dark", seed=150 + sx )
    # The wing (its roof part of the upper deck), the landing and the stair.
    box( m, *E( SPAWN_WING[0], SPAWN_WING[1] ), SPAWN_WING[2], SPAWN_WING[3], 0, SPAWN_ROOM_Z, { "default": None, "+z": "rv_floor" }, STONE )
    box( m, *E( SPAWN_LANDING[0], SPAWN_LANDING[1] ), SPAWN_LANDING[2], SPAWN_LANDING[3], SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z,
         { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    box( m, *E( SPAWN_LANDING[1] - 12, SPAWN_LANDING[1] ), SPAWN_LANDING[2], SPAWN_LANDING[2] + 12, 0, SPAWN_ROOM_Z - 16, "rv_wall", STONE )
    mid = ( SPAWN_STAIR[2] + SPAWN_STAIR[3] ) / 2
    P.stairs( m, ( f * SPAWN_STAIR[0], mid ), ( f * SPAWN_STAIR[1], mid ), SPAWN_STAIR[3] - SPAWN_STAIR[2], 0, SPAWN_ROOM_Z,
              tread="rv_plinth", side="rv_plinth", solid_under=True, surface=STONE, name=f"spawn stair {sx}" )
    P.railing( m, mirror_pts( [ ( SPAWN_LANDING[1], -884 ), ( SPAWN_LANDING[1], -840 ), ( SPAWN_WING[1], -840 ), ( SPAWN_WING[1], -690 ),
                                ( SPAWN_WING[0], -690 ) ], f ), SPAWN_ROOM_Z, clip_to=160, name=f"spawn deck rail {sx}" )
    P.railing( m, mirror_pts( [ ( SPAWN_LANDING[1], -960 ), ( SPAWN_LANDING[0], -960 ) ], f ), SPAWN_ROOM_Z, clip_to=160,
               name=f"spawn landing rail {sx}" )
    spawn_faces( m, sx, door_a, door_b )
    P.beacon( m, f"Spawn beacon {sx}", ( f * t1 - f * 5, tn1 - 10, SPAWN_TOP + 28 ) )
    # Guard hut and barriers.
    he = f * -2120
    box( m, he - 50, he + 50, -1500, -1400, 0, 110, { "default": "rv_white", "+z": "rv_steel" }, METAL )
    guard_hut( m, he, f )
    for e, n, along in ( ( -1880, 650, ( 0, 1 ) ), ( -2050, 900, ( 1, 0 ) ), ( -1950, -1300, ( 1, 0.2 ) ), ( -1800, -1450, ( 0, 1 ) ) ):
        P.jersey( m, ( f * e, n ), along )
    for k, ( e, n ) in enumerate( ( ( -2220, 700 ), ( -2230, 1200 ), ( -1780, 1500 ), ( -2200, 1800 ) ) ):
        P.case_stack( m, ( f * e, n ), ( 0, 1 ), "olive", seed=110 + k + ( 0 if sx < 0 else 30 ) )
    for n in ( -1300.0, 0.0, 1300.0 ):
        e = f * -1760
        P.cylinder( m, ( e, n ), 4, 0, 360, "rv_zinc", 10, surface=METAL )
        P.obox( m, ( e, n, 360 ), ( 1, 0 ), ( 20, 10, 8 ), "rv_dark" )
        card( m, "rv_lamp_warm", [ v( e - 8, n - 4, 355.9 ), v( e + 8, n - 4, 355.9 ), v( e + 8, n + 4, 355.9 ), v( e - 8, n + 4, 355.9 ) ], -UP )
        P.LIGHTS.append( ( f"Spawn mast {sx} {n}", ( e, n, 330 ), "1.00,0.80,0.55,1", 700, False ) )


def boundary_face( m, sx ):
    """ The boundary building's face towards the spawn and the court (riverdale_facades): bays between its piers, each
    with a window upstairs and a door or a louvre at the foot, a plinth, a precast band at the floor, a parapet with its
    coping over the roof's edge, downpipes beside every other pier, and what's fixed to the wall. """
    f = -sx
    yard = "+e" if f > 0 else "-e"
    e_face = f * PLAY[0]
    top = BOUNDARY_TOP + 20
    # The parapet over the roof's edge, drawn only (the roof is clipped).
    box( m, *sorted( ( e_face, e_face - f * 10 ) ), PLAY[2], PLAY[3], BOUNDARY_TOP, top, { "default": "rv_wall", yard: None, "-z": None } )
    F.coping( m, *sorted( ( e_face, e_face - f * 10 ) ), PLAY[2], PLAY[3], top )
    bf = F.Face( m, yard, e_face, PLAY[2], PLAY[3], 0, top )
    bf.exclude( SPAWN_TALL[2], SPAWN_TALL[3], 0, top )
    piers = np.arange( PLAY[2] + 120, PLAY[3] - 60, 300.0 )
    bays = [ ( k, n ) for k, n in enumerate( np.arange( PLAY[2] + 270, PLAY[3] - 200, 300.0 ) )
             if not SPAWN_TALL[2] - 100 < n < SPAWN_TALL[3] + 100 ]
    for k, n in bays:
        lit = k % 4 == 1
        bf.window( n - 75, n + 75, 225, 295, 7.0, pitch=50, room="corridor" if k % 2 else "office", lit=lit,
                   blind=( 0.2, 0.55, 0.0, 0.35 )[k % 4] )
        if k % 3 == 1:
            bf.door( n, 96, 100, canopy=40 )
        else:
            bf.louvre( n - 60, n + 60, 55, 145 )
    bf.plinth()
    bf.band( 186, 8, 2.0 )
    bf.grime_foot()
    bf.grime_top( PLAY[2], PLAY[3], BOUNDARY_TOP + 18, 96 )
    for j, n in enumerate( piers ):
        if j % 2 == 0 and not SPAWN_TALL[2] - 40 < n + 30 < SPAWN_TALL[3] + 10:
            bf.downpipe( n + 30, top - 2 )
    bf.finish()
    for k, n in bays:
        if k % 3 == 1:
            bf.lamp( f"Spawn door lamp {sx} {k}", n, 136, "warm", 360, light=True )
            bf.jbox( n + 70, 112 )
            bf.conduit( [ ( n + 70, 118 ), ( n + 70, 184 ) ] )
            bf.sign( "notice", n - 72, 62, 18 )
        elif k % 2 == 0:
            bf.cabinet( n + 92, 30, 26, 44, plate="danger" if k % 4 == 0 else None )
            bf.conduit( [ ( n + 92, 74 ), ( n + 92, 184 ) ] )
        if k % 4 == 2:
            bf.camera( n + 110, 330, turn=-30 )


def spawn_faces( m, sx, door_a, door_b ):
    """ The spawn building's faces (riverdale_facades): concrete below its room's floor, blue-grey cladding round the
    room, its doors from the deck with their canopies, a ribbon window towards the spawn, louvres and a shutter at the
    foot; and its wing's faces with the building's name over a door. """
    f = -sx
    t0, t1, tn0, tn1 = SPAWN_TALL
    top = SPAWN_TOP + 26
    clad = SPAWN_ROOM_Z + 4
    yard = "+e" if f > 0 else "-e"
    label = "B1" if sx > 0 else "B2"
    trims = ( None, True ) if f > 0 else ( True, None )        # no trim where it meets the boundary building
    to_yard = ( f < 0, f > 0 )                                   # wrap round the corner towards the yard only

    def U( a, b ):
        return tuple( sorted( ( f * a, f * b ) ) )

    # Towards the yard: the doors from the deck, a window, at the foot a louvre and a cabinet.
    y = F.Face( m, yard, f * t1, tn0, tn1, 0, top )
    y.zone( clad, top, F.CLAD, ribs=True )
    y.corner_trims = ( True, True )
    y.exclude( SPAWN_WING[2], SPAWN_WING[3], 0, SPAWN_ROOM_Z )
    y.exclude( SPAWN_LANDING[2], SPAWN_LANDING[3], SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z )
    for d_ in ( door_a, door_b ):
        y.door( ( d_[0] + d_[1] ) / 2, 66 if d_ is door_a else 56, 92, z=SPAWN_ROOM_Z, double=d_ is door_a, canopy=30,
                through=( d_[0], d_[1] ) )
        y.later.append( lambda d_=d_: y.reveal( d_[0], d_[1], d_[3], d_[2], 20.0, "rv_wall", ( True, True, False, False ), d0=1.5 ) )
    y.window( -1130, -1010, 252, 330, 7.0, pitch=40, room="office", lit=True, blind=0.3 )
    y.louvre( -1130, -1010, 50, 150 )
    y.plinth( wrap=( True, False ) )
    y.grime_foot()
    y.downpipe( -1146, top - 2 )
    y.finish()
    y.sign( "door_sign", -985, SPAWN_ROOM_Z + 54, 14 )
    y.lamp( f"Spawn door lamp {sx}", -905, SPAWN_ROOM_Z + 118, "warm", 300, light=True )
    y.lamp( f"Spawn upper lamp {sx}", -770, SPAWN_ROOM_Z + 118, "warm", 280, light=True )
    y.cabinet( -985, 30, 26, 44 )
    y.conduit( [ ( -985, 74 ), ( -985, SPAWN_ROOM_Z - 18 ) ] )
    y.camera( -1140, 372, turn=30 )
    # Towards the spawn: a ribbon window lighting the room, a shutter and a door at the foot.
    nf = F.Face( m, "+n", tn1, f * t0, f * t1, 0, top )
    nf.zone( clad, top, F.CLAD, ribs=True )
    nf.corner_trims = trims
    nf.window( *U( -2272, -2088 ), 238, 322, 8.0, pitch=46, room="office", lit=True, blind=0.35, sill=None )
    nf.shutter( *U( -2272, -2160 ), 0, 140 )
    nf.door( f * -2110, 44, 88, double=False, canopy=26 )
    nf.plinth( wrap=( False, False ) )
    nf.grime_foot()
    nf.downpipe( f * -2286, top - 2 )
    nf.finish()
    nf.sign( "danger", f * -2128, 120, 12 )
    nf.lamp( f"Spawn north lamp {sx}", f * -2216, 160, "warm", 300 )
    # Towards the turbine block.
    s = F.Face( m, "-n", tn0, f * t0, f * t1, 0, top )
    s.zone( clad, top, F.CLAD, ribs=True )
    s.corner_trims = trims
    for a, b in ( ( -2250, -2190 ), ( -2160, -2100 ) ):
        s.window( *U( a, b ), 250, 320, 7.0, room="plant", sill=None )
    s.louvre( *U( -2262, -2162 ), 60, 140 )
    s.plinth( wrap=to_yard )
    s.grime_foot()
    s.downpipe( f * -2076, top - 2 )
    s.finish()
    s.cabinet( f * -2120, 30, 26, 40 )
    # The wing: the building's name over a door towards the yard, a louvre towards the spawn, its deck's edge.
    wn = ( SPAWN_WING[2] + SPAWN_WING[3] ) / 2
    wy = F.Face( m, yard, f * SPAWN_WING[1], SPAWN_WING[2], SPAWN_WING[3], 0, SPAWN_ROOM_Z )
    wy.door( wn, 64, 84, double=False, glazed=False, paint="rv_door_yellow" )
    wy.plinth()
    wy.band( SPAWN_ROOM_Z - 12, 12, 2.0, drip=True )
    wy.grime_foot()
    wy.finish()
    wy.letters( label, wn, 152, 66 )
    wy.lamp( f"Spawn wing lamp {sx}", wn, 100, "warm", 260, light=True )
    wn_ = F.Face( m, "+n", SPAWN_WING[3], *U( SPAWN_WING[0], SPAWN_WING[1] ), 0, SPAWN_ROOM_Z )
    wn_.louvre( *U( -2030, -1950 ), 60, 140 )
    wn_.plinth( wrap=to_yard )
    wn_.band( SPAWN_ROOM_Z - 12, 12, 2.0, wrap=to_yard, drip=True )
    wn_.grime_foot()
    wn_.finish()
    ws = F.Face( m, "-n", SPAWN_WING[2], *U( SPAWN_WING[0], SPAWN_WING[1] ), 0, SPAWN_ROOM_Z )
    ws.exclude( *U( SPAWN_LANDING[0], SPAWN_LANDING[1] ), SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z )
    ws.plinth( wrap=to_yard )
    ws.band( SPAWN_ROOM_Z - 12, 12, 2.0, wrap=to_yard, drip=True )
    ws.grime_foot()
    ws.finish()
    ws.cabinet( f * -1960, 30, 26, 44, plate="notice" )


def guard_hut( m, he, f ):
    """ The guard hut's dressing: a roof overhanging on all sides, a framed window towards the yard, a door, an air
    conditioner on the roof. """
    box( m, he - 56, he + 56, -1506, -1394, 110, 114, { "default": "rv_fc_flashing", "-z": "rv_steel" } )
    yard = "+e" if f > 0 else "-e"
    w = F.Face( m, yard, he + f * 50, -1500, -1400, 0, 110 )
    w.box( -1489, -1411, 46, 94, 0, 0.6, "rv_frame" )
    w.rect( F.room_paint( "office", True ), -1487, -1413, 48, 92, 0.7, uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] )
    w.box( -1491, -1409, 42, 46, 0, 2.5, "rv_steel" )
    n = F.Face( m, "+n", -1400, he - 50, he + 50, 0, 110 )
    P.door( m, n.p( he - f * 20, 0, 0 ), n.right, 36, 82, paint="rv_fc_door_blue", double=False, mount="surface" )
    P.obox( m, ( he, -1450, 122 ), ( 1, 0 ), ( 30, 22, 16 ), { "default": "rv_white", "+z": "rv_fc_flashing" } )
    P.cylinder( m, ( he, -1450 ), 8.0, 130, 130.6, "rv_black", 12, top="rv_black" )
