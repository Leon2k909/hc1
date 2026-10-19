def middle_yard( m ):
    """ The hall's apron and the pipe bridge from the hall to B1. """
    # Pipe bridge: a truss from the hall's south wall to B1's north wall, pipes on it, resting on shoes, sleeved where
    # they go into the walls.
    for e in ( -110.0, -30.0 ):
        P.truss( m, ( e, H.N0 - H.WT - 14, 300 ), ( e, CORE[3], 300 ), 40, "rv_steel", panel=60 )
    slats = np.arange( H.N0 - H.WT - 60, CORE[3], 80.0 )
    for k, ( de, r ) in enumerate( ( ( -95, 9.0 ), ( -70, 6.0 ), ( -50, 6.0 ) ) ):
        P.pipe( m, [ ( de, H.N0 - H.WT + 4, 352 ), ( de, CORE[3] - 4, 352 ) ], r, "rv_pipe", 12, caps=False )
        F.flanges( m, ( de, H.N0 - H.WT, 352 ), ( de, CORE[3], 352 ), r, every=150.0, start=40.0 )
        for n in ( H.N0 - H.WT, CORE[3] ):
            P.disc_ring( m, v( de, n - 1.5, 352 ), v( de, n + 1.5, 352 ), r * 1.35, "rv_steel", 12 )
        for n in slats:
            F.shoe( m, ( de, n, 352 ), r, ( 0, 1 ) )
    for n in slats:
        box( m, -114, -26, n - 2, n + 2, 340, 342, "rv_steel" )
    # Barriers and cases in the apron.
    for e, n, along in ( ( -300, -520, ( 1, 0 ) ), ( 300, -520, ( 1, 0 ) ), ( -560, -400, ( 0, 1 ) ), ( 560, -400, ( 0, 1 ) ) ):
        P.jersey( m, ( e, n ), along )
    for k, ( e, n ) in enumerate( ( ( -150, -330 ), ( 160, -340 ), ( -700, -600 ), ( 700, -600 ) ) ):
        P.case_stack( m, ( e, n ), ( 1, 0 ), "olive" if k % 2 else "dark", seed=300 + k )
    # The hall's south face: its name over the door, the logo high up, lamps and beacons.
    face = H.N0 - H.WT
    out = v( 0, -1, 0 )
    right = np.cross( UP, out )
    P.letters( m, "fuel_handling", ( 0, face, 168 ), right, 18, "dark" )
    P.letters( m, "logo_wordmark", ( 0, face, 900 ), right, 150, "dark" )
    P.wall_light( m, "Hall south door lamp", ( 0, face, 150 ), out, "warm", 380 )
    for e in ( -500.0, 500.0 ):
        P.wall_light( m, f"Hall south lamp {e}", ( e, face, 240 ), out, "warm", 360 )
    for e in ( -1040.0, 1040.0 ):
        P.beacon( m, f"Hall beacon {e}", ( e * 0.98, face - 8, H.ROOF + 40 ), light=False )
    for k, r in enumerate( ( 8.0, 6.0 ) ):
        run = [ ( -1030, face - 16 - k * 14, 420 + k * 20 ), ( 1030, face - 16 - k * 14, 420 + k * 20 ) ]
        P.pipe( m, run, r, "rv_pipe", 12 )
        F.flanges( m, run[0], run[1], r, every=400.0, start=150.0 )
    for e in np.arange( -1000, 1001, 200.0 ):
        box( m, e - 3, e + 3, face - 40, face, 408, 412, "rv_steel" )
    P.louvre( m, ( -620, face, 700 ), right, 260, 160 )
    P.louvre( m, ( 620, face, 700 ), right, 260, 160 )
    # The east-west lanes' floor lines in the middle.
    box( m, -520, 520, -1206, -1202, 0, 0.3, { "default": None, "+z": "rv_line_yellow" } )


def north_lane( m ):
    """ The lane north of the hall: the perimeter wall with a fence on it, the pipe rack along the hall's wall, cover. """
    n = NORTH_WALL_N
    box( m, PLAY[0] - 400, PLAY[1] + 400, n, n + 30, 0, 220, { "default": "rv_wall", "-n": None }, STONE )
    perimeter_face( m )
    for e in np.arange( PLAY[0], PLAY[1] + 1, 120.0 ):
        P.rod( m, ( e, n + 15, 220 ), ( e, n + 15, 300 ), 1.2, "rv_zinc", 6 )
        P.rod( m, ( e, n + 15, 296 ), ( e, n + 5, 304 ), 0.8, "rv_zinc", 4 )
    for z in ( 250.0, 275.0, 300.0 ):
        P.rod( m, ( PLAY[0], n + 15, z ), ( PLAY[1], n + 15, z ), 0.4, "rv_zinc", 4 )
    # Pipe rack along the hall's north wall: portals on base plates with knee braces, pipes on shoes with flanges and
    # valves, a cable tray.
    r0, r1 = H.N1 + H.WT + 10, H.N1 + H.WT + 150
    portals = np.arange( -1000, 1001, 250.0 )
    for e in portals:
        for nn in ( r0, r1 ):
            box( m, e - 5, e + 5, nn - 5, nn + 5, 0, 260, "rv_steel", METAL )
            F.base_plate( m, e, nn, 10.0 )
            for de in ( -1, 1 ):
                if abs( e + de * 40 ) <= 1000:
                    m.beam( v( e + de * 5, nn, 212 ), v( e + de * 40, nn, 248 ), ( 2.5, 2.5 ), "rv_steel" )
        for nn, dn in ( ( r0, 1 ), ( r1, -1 ) ):
            m.beam( v( e, nn + dn * 5, 214 ), v( e, nn + dn * 40, 254 ), ( 2.5, 2.5 ), "rv_steel" )
        P.i_beam( m, ( e, r0 - 6, 260 ), ( e, r1 + 6, 260 ), 12, 8, "rv_steel" )
    for nn in ( r0, r1 ):
        P.i_beam( m, ( -1010, nn, 254 ), ( 1010, nn, 254 ), 12, 8, "rv_steel" )
    for k, ( r, paint ) in enumerate( ( ( 12.0, "rv_pipe" ), ( 9.0, "rv_pipe" ), ( 9.0, "rv_steel" ), ( 6.0, "rv_yellow" ), ( 6.0, "rv_white" ) ) ):
        nn = r0 + 18 + k * 26
        run = [ ( -1700, nn, 266 + r ), ( 1700, nn, 266 + r ) ]
        P.pipe( m, run, r, paint, 12, caps=False )
        F.flanges( m, run[0], run[1], r, every=480.0, start=150.0 + 60 * k, paint=paint )
        for e in portals:
            F.shoe( m, ( e, nn, 266 + r ), r, ( 1, 0 ) )
    for e, k in ( ( -620.0, 3 ), ( 380.0, 1 ), ( 860.0, 2 ) ):
        r = ( 12.0, 9.0, 9.0, 6.0, 6.0 )[k]
        F.valve( m, ( e, r0 + 18 + k * 26, 266 + r ), r, ( 1, 0 ) )
    P.cable_tray( m, ( -1700, r1 + 30, 300 ), ( 1700, r1 + 30, 300 ) )
    for e in portals:
        m.beam( v( e, r1, 260 ), v( e, r1, 298 ), ( 4.0, 4.0 ), "rv_steel" )
        m.beam( v( e, r1 + 2, 296 ), v( e, r1 + 40, 296 ), ( 2.0, 2.0 ), "rv_steel" )
    # Cover: concrete blocks, a generator, cases, barriers.
    mid = ( r1 + n ) / 2
    for e, nn in ( ( -720, mid + 40 ), ( 720, mid + 40 ), ( -240, r1 + 60 ), ( 240, r1 + 60 ), ( 0, n - 90 ) ):
        box( m, e - 30, e + 30, nn - 30, nn + 30, 0, 44, "rv_plinth", STONE )
    generator( m, -140, 140, n - 160 - 70, n - 160 )
    for k, ( e, nn ) in enumerate( ( ( -1260, mid + 30 ), ( 1260, mid + 30 ), ( -500, n - 60 ), ( 500, n - 60 ), ( -1900, n - 100 ), ( 1900, n - 100 ) ) ):
        P.case_stack( m, ( e, nn ), ( 1, 0 ), "olive" if k % 2 else "dark", seed=400 + k )
    for e, nn, along in ( ( -1000, r1 + 40, ( 1, 0 ) ), ( 1000, r1 + 40, ( 1, 0 ) ), ( -1700, mid, ( 0, 1 ) ), ( 1700, mid, ( 0, 1 ) ) ):
        P.jersey( m, ( e, nn ), along )
    for e in ( -1500.0, -500.0, 500.0, 1500.0 ):
        P.wall_light( m, f"Perimeter lamp {e}", ( e, n, 200 ), v( 0, -1, 0 ), "warm", 420 )
    out = v( 0, 1, 0 )
    right = np.cross( UP, out )
    for o in H.NORTH_DOORS:
        e = ( o[0] + o[1] ) / 2
        P.wall_light( m, f"Hall north door lamp {e}", ( e, H.N1 + H.WT, 150 ), out, "warm", 340 )
        P.plate( m, "exit", ( e, H.N1 + H.WT, 140 ), right, 10, off=0.4 )


def perimeter_face( m ):
    """ The perimeter wall's face towards the lane (riverdale_facades): cast panels between piers, expansion joints, a
    darker plinth, a precast coping under the fence, warning signs and cameras. """
    n = NORTH_WALL_N
    f_ = F.Face( m, "-n", n, PLAY[0] - 400, PLAY[1] + 400, 0, 220 )
    piers = np.arange( -2400.0, 2401.0, 480.0 )
    for e in piers:
        f_.pilaster( e - 14, e + 14, 0, 214, 5.0, cap=None )
        if e + 240 < PLAY[1] + 400:
            f_.joint( e + 240, 30, 214 )
    f_.plinth( 30, 3.0, wrap=( False, False ) )
    f_.grime_foot( 30, 3.0 )
    f_.grime_top( PLAY[0] - 400, PLAY[1] + 400, 214, 80 )
    f_.finish()
    F.coping( m, PLAY[0] - 400, PLAY[1] + 400, n, n + 30, 220, over=3.0, paint=F.PRECAST, t=5.0, lip=2.0 )
    for k, e in enumerate( piers[:-1] ):
        if k % 2:
            f_.sign( "danger", e + 120, 118, 20 )
        else:
            f_.camera( e + 40, 196, turn=25 )


def turbine_hall( m ):
    """ The turbine hall: the south boundary, its north face dressed (turbine_hall_face). Solid. """
    e0, e1 = PLAY[0] - 400, PLAY[1] + 400
    n0, n1 = PLAY[2] - 1000, PLAY[2]
    box( m, e0, e1, n0, n1, 0, 960, { "default": "rv_wall", "+n": None, "+z": "rv_plinth" }, STONE )
    piers = [ float( e ) for e in np.arange( PLAY[0], PLAY[1] + 1, 300.0 ) if abs( e ) >= 560 ]
    for e in piers:
        box( m, e - 24, e + 24, n1, n1 + 16, 0, 980, "rv_wall", STONE )
        F.coping( m, e - 24, e + 24, n1, n1 + 16, 980, over=1.5 )
    F.coping( m, e0, e1, n1 - 12, n1, 960 )
    turbine_hall_face( m, piers )


def turbine_hall_face( m, piers ):
    """ The turbine hall's face towards the yard (riverdale_facades): a concrete base and light grey cladding between
    its concrete piers, a clerestory of glazing, louvres high up, doors and roller shutters at the foot, its name on a
    sign board, pipes on brackets off the piers, downpipes. """
    n1 = PLAY[2]
    top = 960.0
    clad = 300.0
    t = F.Face( m, "+n", n1, PLAY[0] - 400, PLAY[1] + 400, 0, top )
    t.zone( clad, top - 20, F.CLAD_LIGHT, ribs=True )
    t.corner_trims = ( None, None )
    # What stands against it: the turbine annex, the turbine blocks, the boundary buildings.
    t.exclude( TURBINE[0], TURBINE[1], 0, TURBINE_TOP + 32 )
    for sx in ( -1, 1 ):
        t.exclude( *sorted( ( -sx * TURBINE_SIDE[0], -sx * TURBINE_SIDE[1] ) ), 0, 452 )
    t.exclude( PLAY[0] - 400, PLAY[0], 0, BOUNDARY_TOP + 22 )
    t.exclude( PLAY[1], PLAY[1] + 400, 0, BOUNDARY_TOP + 22 )
    hidden = lambda a, b: any( lo < b and hi > a for lo, hi in ( ( -1700, -1300 ), ( 1300, 1700 ) ) )
    bays = [ ( p, q ) for p, q in zip( piers, piers[1:] ) if q - p < 301 ]
    ground = { -2150.0: "door", -1850.0: "louvre", -1250.0: "door", -950.0: "shutter", 850.0: "door", 1150.0: "shutter",
               1750.0: "louvre", 2050.0: "door" }
    lamps = { -2150.0: -1900.0, -1250.0: -1100.0, 850.0: 1100.0, 2050.0: 1900.0 }
    for k, ( p, q ) in enumerate( bays ):
        bc = ( p + q ) / 2
        if not hidden( p, q ):
            t.window( p + 40, q - 40, 440, 520, 6.0, pitch=43, room="plant", sill=None )
        if k % 2 == 0:
            t.louvre( bc - 90, bc + 90, 680, 800 )
        kind = ground.get( bc )
        if kind == "door":
            t.door( bc, 72, 96, canopy=40 )
        elif kind == "shutter":
            t.shutter( bc - 100, bc + 100, 0, 240 )
            t.guard( bc - 100, -1, 72 )
            t.guard( bc + 100, 1, 72 )
        elif kind == "louvre":
            t.louvre( bc - 70, bc + 70, 50, 160 )
    # The long bay behind the turbine annex: a clerestory over it, louvres, a louvre and a door either side of it.
    t.window( -740, 640, 440, 520, 6.0, pitch=46, room="plant", sill=None )
    for e in ( -400.0, 0.0, 400.0 ):
        t.louvre( e - 90, e + 90, 680, 800 )
    t.louvre( -720, -580, 50, 150 )
    t.door( 610, 60, 92, double=False, canopy=30 )
    t.plinth( wrap=( False, False ) )
    t.grime_foot()
    t.grime_top( PLAY[0], PLAY[1], top - 20, 96 )
    for e in ( -2000.0, -800.0, 1000.0, 2200.0 ):
        t.downpipe( e + 31, top - 2, scupper=False )
    t.finish()
    for e in ( -1350.0, 1350.0 ):
        t.letters( "turbine_hall", e, 880, 70, board="rv_white", d=2.6 )
    for bc, name in lamps.items():
        t.lamp( f"Turbine hall door lamp {name}", bc, 132, "warm", 380, light=True )
        t.sign( "notice", bc + 52, 64, 18 )
    for bc, kind in ground.items():
        if kind == "louvre":
            t.cabinet( bc + 96, 30, 26, 44 )
            t.conduit( [ ( bc + 96, 74 ), ( bc + 96, clad - 6 ) ] )
        if kind == "shutter":
            t.sign( "danger", bc - 128, 110, 18 )
    for e in ( -2150.0, -950.0, 850.0, 2050.0 ):
        t.camera( e + 110, 330, turn=-25 if e < 0 else 25 )
    # Pipes on brackets off the piers.
    for k, ( r, z ) in enumerate( ( ( 14.0, 600.0 ), ( 10.0, 640.0 ) ) ):
        run = [ ( PLAY[0], n1 + 40, z ), ( PLAY[1], n1 + 40, z ) ]
        P.pipe( m, run, r, "rv_pipe", 12, caps=False )
        F.flanges( m, run[0], run[1], r, every=600.0, start=90.0 + 150 * k )
        for e in piers:
            F.shoe( m, ( e, n1 + 40, z ), r, ( 1, 0 ) )
            box( m, e - 4, e + 4, n1 + 16, n1 + 56, z - r - 10, z - r - 4.2, "rv_steel" )
