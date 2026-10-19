def generator( m, e0, e1, n0, n1 ):
    """ A diesel generator set on its skid: an acoustic housing (its panels, louvres, radiator grille, control panel,
    silencer and stack: riverdale_facades.genset), a fuel tank under. """
    box( m, e0 - 6, e1 + 6, n0 - 6, n1 + 6, 0, 14, "rv_steel", METAL )
    box( m, e0, e1, n0, n1, 14, 96, { "default": "rv_yellow", "+z": "rv_steel" }, METAL )
    F.genset( m, e0, e1, n0, n1 )
    P.letters( m, "logo_wordmark", ( ( e0 + e1 ) / 2, n0 - 0.4, 52 ), ( 1, 0, 0 ), 16, "dark" )


def turbine_annex( m ):
    """ The turbine building's annex south of C1 (TURBINE), its generators in front: a concrete base under light grey
    cladding, louvre banks and a door with a canopy towards C1, a roller shutter in each side's loading bay, the
    turbine hall's sign on a board, pipes on brackets, plant on the roof. """
    for sx in ( -1, 1 ):
        generator( m, *sorted( ( sx * 130, sx * 320 ) ), -1165, -1065 )
    e0, e1, n0, n1 = TURBINE
    top, clad = TURBINE_TOP + 30, 150.0
    box( m, e0, e1, n0, n1, 0, TURBINE_TOP, { "default": None, "+z": "rv_plinth" }, STONE )
    for ( a, b, c, d ), inner in ( ( ( e0, e1, n1 - 10, n1 ), "-n" ), ( ( e0, e0 + 10, n0, n1 ), "+e" ), ( ( e1 - 10, e1, n0, n1 ), "-e" ) ):
        box( m, a, b, c, d, TURBINE_TOP, top, { "default": None, inner: "rv_wall" }, STONE )
        F.coping( m, a, b, c, d, top )
    for sx in ( -1, 1 ):
        side = "+e" if sx > 0 else "-e"
        s = F.Face( m, side, sx * e1, n0, n1, 0, top )
        s.zone( clad, top, F.CLAD_LIGHT, ribs=True )
        s.corner_trims = ( None, True )
        # A loading bay: a roller shutter under its drum's housing.
        bay0, bay1 = -1636.0, -1484.0
        s.shutter( bay0, bay1, 0, 180 )
        s.guard( bay0, -1, 72 )
        s.guard( bay1, 1, 72 )
        s.door( -1330, 48, 88, double=False, canopy=28 )
        s.louvre( -1720, -1660, 220, 300 )
        s.plinth( wrap=( False, True ) )
        s.grime_foot()
        s.downpipe( -1256, top - 2 )
        s.finish()
        s.letters( "turbine_hall", -1360, 250, 26, board="rv_white", d=2.6 )
        s.lamp( f"Turbine annex bay lamp {sx}", ( bay0 + bay1 ) / 2, 214, "warm", 380, light=True )
        s.lamp( f"Turbine corner lamp {sx}", -1266, 300, "warm", 300, light=True )
        s.cabinet( -1420, 30, 26, 44 )
        s.conduit( [ ( -1420, 74 ), ( -1420, clad - 4 ) ] )
        s.camera( -1700, 340, turn=20 )
        P.beacon( m, f"Turbine beacon {sx}", s.p( -1250, top + 2.0, -5 ) )
    # The north face, towards C1: louvre banks, a door, pipes on brackets, lamps.
    nf = F.Face( m, "+n", n1, e0, e1, 0, top )
    nf.zone( clad, top, F.CLAD_LIGHT, ribs=True )
    nf.corner_trims = ( True, True )
    for e in ( -330.0, 330.0 ):
        nf.louvre( e - 90, e + 90, 190, 310 )
    nf.door( 0, 90, 100, canopy=36 )
    for e in ( -170.0, 170.0 ):
        nf.joint( e, 24, clad - 4 )
    nf.plinth()
    nf.grime_foot()
    for e in ( -500.0, 500.0 ):
        nf.downpipe( e, top - 2 )
    nf.finish()
    nf.letters( "turbine_hall", 0, 192, 18, board="rv_white", d=2.6 )
    nf.lamp( "Turbine door lamp", 0, 134, "warm", 340, light=True )
    nf.cabinet( 120, 30, 26, 44 )
    nf.conduit( [ ( 120, 74 ), ( 120, clad - 4 ) ] )
    nf.cabinet( -120, 30, 26, 44, paint="rv_fc_red", plate="lifering_sign" )
    nf.camera( -470, 340, turn=-30 )
    nf.camera( 470, 340, turn=30 )
    for k, r in enumerate( ( 10.0, 7.0 ) ):
        run = [ ( e0 + 10, n1 + 18 + k * 6, 300 - k * 24 ), ( e1 - 10, n1 + 18 + k * 6, 300 - k * 24 ) ]
        P.pipe( m, run, r, "rv_pipe", 12 )
        F.flanges( m, run[0], run[1], r, every=320.0, start=110.0 )
    for e in np.arange( e0 + 40, e1, 160.0 ):
        box( m, e - 3, e + 3, n1, n1 + 30, 262, 266, "rv_steel" )
        box( m, e - 4, e + 4, n1, n1 + 1.0, 254, 270, "rv_steel" )
    # On the roof.
    F.roof_unit( m, ( -200, -1500 ), ( 1, 0 ), TURBINE_TOP, ( 130, 70, 52 ) )
    F.roof_unit( m, ( 220, -1420 ), ( 1, 0 ), TURBINE_TOP, ( 110, 60, 46 ) )
    for e, n in ( ( -420, -1350 ), ( 420, -1600 ), ( 30, -1640 ) ):
        F.roof_fan( m, ( e, n ), TURBINE_TOP )
    F.hatch( m, ( -40, -1330 ), TURBINE_TOP )
