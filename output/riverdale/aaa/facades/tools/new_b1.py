def b1( m, glass ):
    c0, c1, n0, n1 = CORE
    t = 24.0
    up_door = ( -930.0, -860.0, ROOM_Z + 96, ROOM_Z )
    # The walls' outer faces, and their ends and reveals that would lie in them, are drawn by b1_faces.
    H.wall( m, "e", c0, c1, n1 - t, n1, 0, CORE_TOP, [ ( -60.0, 60.0, 150.0 ) ], paint={ "default": "rv_wall", "+n": None, "-e": None, "+e": None } )
    H.wall( m, "e", c0, c1, n0, n0 + t, 0, CORE_TOP, [ ( -60.0, 60.0, 150.0 ) ], paint={ "default": "rv_wall", "-n": None, "-e": None, "+e": None } )
    for sx in ( -1, 1 ):
        a, b = sorted( ( sx * c1, sx * ( c1 - t ) ) )
        outer = "+e" if sx > 0 else "-e"
        H.wall( m, "n", n0 + t, n1 - t, a, b, 0, CORE_TOP, [ up_door ], paint={ "default": "rv_wall", outer: None, "-n": None, "+n": None } )
    # Upper floor, roof, parapets and their copings.
    box( m, c0 + t, c1 - t, n0 + t, n1 - t, ROOM_Z - 16, ROOM_Z, { "default": "rv_wall", "+z": "rv_floor", "-z": "rv_steel" }, STONE )
    box( m, c0, c1, n0, n1, CORE_TOP - 20, CORE_TOP, { "default": None, "+z": "rv_plinth", "-z": "rv_steel" }, STONE )
    for ( a, b, c, d ), inner in ( ( ( c0, c1, n0, n0 + 10 ), "+n" ), ( ( c0, c1, n1 - 10, n1 ), "-n" ), ( ( c0, c0 + 10, n0, n1 ), "+e" ),
                                   ( ( c1 - 10, c1, n0, n1 ), "-e" ) ):
        box( m, a, b, c, d, CORE_TOP, CORE_TOP + 28, { "default": None, inner: "rv_wall" }, STONE )
        F.coping( m, a, b, c, d, CORE_TOP + 28 )
    # Ground floor lamps in the passage, the upper room's lamps.
    P.ceiling_light( m, "B1 passage", ( 0, -870, ROOM_Z - 20 ), ( 0, 1 ), "cool", 340 )
    P.ceiling_light( m, "B1 room", ( 0, -870, CORE_TOP - 26 ), ( 0, 1 ), "cool", 380 )
    # Each side: the low wing (its roof part of the upper deck), the landing, the stair, railings.
    for sx in ( -1, 1 ):
        f = -sx

        def E( a, b ):
            return tuple( sorted( ( f * a, f * b ) ) )

        box( m, *E( WING[0], WING[1] ), WING[2], WING[3], 0, ROOM_Z, { "default": None, "+z": "rv_floor" }, STONE )
        box( m, *E( B_LANDING[0], B_LANDING[1] ), B_LANDING[2], B_LANDING[3], ROOM_Z - 16, ROOM_Z,
             { "default": "rv_wall", "+z": "rv_floor" }, STONE )
        box( m, *E( B_LANDING[0], B_LANDING[0] + 12 ), B_LANDING[2], B_LANDING[2] + 12, 0, ROOM_Z - 16, "rv_wall", STONE )
        mid = ( B_STAIR[2] + B_STAIR[3] ) / 2
        P.stairs( m, ( f * B_STAIR[0], mid ), ( f * B_STAIR[1], mid ), B_STAIR[3] - B_STAIR[2], 0, ROOM_Z, tread="rv_plinth",
                  side="rv_plinth", solid_under=True, surface=STONE, name=f"B1 stair {sx}" )
        P.railing( m, mirror_pts( [ ( -200, -864 ), ( -200, -840 ), ( -420, -840 ), ( -420, -700 ), ( -160, -700 ) ], f ), ROOM_Z, clip_to=160,
                   name=f"B1 deck rail {sx}" )
        P.railing( m, mirror_pts( [ ( -200, -940 ), ( -160, -940 ) ], f ), ROOM_Z, clip_to=160, name=f"B1 landing rail {sx}" )
    b1_faces( m, up_door )
    # Inside the room: lockers, a table, cases.
    box( m, -120, -40, -1000, -980, ROOM_Z, ROOM_Z + 80, "rv_steel", METAL )
    box( m, 40, 120, -1000, -980, ROOM_Z, ROOM_Z + 80, "rv_steel", METAL )
    box( m, -36, 36, -960, -920, ROOM_Z, ROOM_Z + 30, { "default": "rv_desk", "+z": "rv_dark" }, METAL )
    P.case_stack( m, ( -100, -760 ), ( 1, 0 ), "dark", seed=201 )
    P.case_stack( m, ( 100, -760 ), ( 1, 0 ), "olive", seed=202 )
    # On the roof: an air handling unit, fans and vents showing over the parapet.
    F.roof_unit( m, ( 0, -880 ), ( 1, 0 ), CORE_TOP, ( 140, 72, 54 ) )
    F.roof_fan( m, ( -105, -1000 ), CORE_TOP )
    F.roof_fan( m, ( 105, -760 ), CORE_TOP )
    F.roof_vent( m, ( 110, -1000 ), CORE_TOP )
    F.roof_vent( m, ( -115, -760 ), CORE_TOP )


def b1_faces( m, up_door ):
    """ C1's faces (riverdale_facades): its core a control block in concrete between corner fins, a deep ribbon window
    lighting its room on the north and south, the passage under a canopy, a precast band and the parapet's coping, the
    door from each deck under a canopy; and its wings' faces, the name over a door. """
    c0, c1, n0, n1 = CORE
    t = 24.0
    top = CORE_TOP + 28
    for nf, normal, sgn in ( ( n1, "+n", 1 ), ( n0, "-n", -1 ) ):
        face = F.Face( m, normal, nf, c0, c1, 0, top )
        face.opening( -60, 60, 0, 150 )
        face.later.append( lambda face=face: face.reveal( -60, 60, 0, 150, t, "rv_wall", ( True, True, False, False ) ) )
        face.window( -124, 124, 236, 334, 8.0, pitch=50, transom=304, room="office", lit=True, blind=0.3 )
        face.louvre( -116, -56, 362, 400 )
        face.louvre( 56, 116, 362, 400 )
        face.plinth( wrap=( False, False ) )
        face.band( 344, 8, 2.0, wrap=( False, False ) )
        for a, b in ( ( c0, c0 + 32 ), ( c1 - 32, c1 ) ):
            face.pilaster( a, b, 0, CORE_TOP, 5.0 )
        face.grime_foot()
        face.grime_top( c0, c1, 344, 72 )
        face.later.append( lambda face=face: face.canopy( 0, 150, 158, 40 ) )
        face.finish()
        face.letters( "control_room", 0, 212, 14 )
        face.lamp( f"B1 passage lamp {sgn}", 0, 180, "warm", 320, light=True )
        face.camera( -100, 420, turn=-20 )
        face.sign( "door_sign", 78, 112, 14 )
        P.beacon( m, f"B1 roof beacon {sgn}", ( 140 * sgn, nf - sgn * 6, CORE_TOP + 30 ) )
    for sx in ( -1, 1 ):
        f = -sx

        def U( a, b ):
            return tuple( sorted( ( f * a, f * b ) ) )

        side = "-e" if f > 0 else "+e"
        to_out = ( f > 0, f < 0 )
        # The core's side, over the wing and the landing.
        s = F.Face( m, side, f * c0, n0, n1, 0, top )
        s.exclude( WING[2], WING[3], 0, ROOM_Z )
        s.exclude( B_LANDING[2], B_LANDING[3], ROOM_Z - 16, ROOM_Z )
        s.door( ( up_door[0] + up_door[1] ) / 2, 66, 92, z=ROOM_Z, canopy=28, through=( up_door[0], up_door[1] ) )
        s.later.append( lambda s=s: s.reveal( up_door[0], up_door[1], up_door[3], up_door[2], t, "rv_wall", ( True, True, False, False ), d0=1.5 ) )
        s.window( -1000, -950, 236, 334, 8.0, room="plant" )
        s.window( -800, -730, 236, 334, 8.0, pitch=35, room="office", lit=True, blind=0.45 )
        s.louvre( -1000, -950, 40, 130 )
        s.plinth( wrap=( True, False ) )
        s.band( 344, 8, 2.0, wrap=( True, True ) )
        s.grime_foot()
        s.downpipe( -1026, top - 2 )
        s.finish()
        s.sign( "door_sign", -820, ROOM_Z + 54, 14 )
        s.lamp( f"B1 door lamp {sx}", ( up_door[0] + up_door[1] ) / 2, ROOM_Z + 122, "warm", 300, light=True )
        s.cabinet( -925, 30, 26, 42 )
        s.conduit( [ ( -925, 72 ), ( -925, ROOM_Z - 22 ) ] )
        # The wing: C1 over its door at its end, a louvre and cabinets on its sides, its deck's edge.
        wn = ( WING[2] + WING[3] ) / 2
        we = F.Face( m, side, f * WING[0], WING[2], WING[3], 0, ROOM_Z )
        we.door( wn, 66, 84, double=False, glazed=False, paint="rv_door_yellow" )
        we.plinth()
        we.band( ROOM_Z - 12, 12, 2.0, drip=True )
        we.grime_foot()
        we.finish()
        we.letters( "C1", wn, 148, 64 )
        we.lamp( f"B1 wing lamp {sx}", wn, 102, "warm", 260, light=True )
        wnf = F.Face( m, "+n", WING[3], *U( WING[0], WING[1] ), 0, ROOM_Z )
        wnf.louvre( *U( -390, -300 ), 60, 140 )
        wnf.plinth( wrap=to_out )
        wnf.band( ROOM_Z - 12, 12, 2.0, wrap=to_out, drip=True )
        wnf.grime_foot()
        wnf.finish()
        wnf.cabinet( f * -250, 30, 26, 42, plate="notice" )
        wsf = F.Face( m, "-n", WING[2], *U( WING[0], WING[1] ), 0, ROOM_Z )
        wsf.exclude( *U( B_LANDING[0], B_LANDING[1] ), ROOM_Z - 16, ROOM_Z )
        wsf.plinth( wrap=to_out )
        wsf.band( ROOM_Z - 12, 12, 2.0, wrap=to_out, drip=True )
        wsf.grime_foot()
        wsf.finish()
        wsf.cabinet( f * -380, 30, 24, 40 )
