def spa( m, g ):
    """ The spa along the north edge: closed, its south face over the terraces dressed with windows, its west face
    over the garden terrace. """
    e0, e1, n0, n1 = SPA
    solid( m, e0, e1, n0, n1, 0, SPA_TOP, { "default": "vr_stone", "+n": None, "-z": None } )
    solid( m, e0 - 6, e1 + 6, n0 - 6, n1 + 6, SPA_TOP, SPA_TOP + 14, "vr_stone_dark" )
    rng = np.random.default_rng( 3 )
    for e in np.arange( e0 + 100, e1 - 60, 160.0 ):
        for z0, z1 in ( ( 250, 360 ), ):
            box( m, e - 50, e + 50, n0 - 1.2, n0 - 0.4, z0, z1, "vr_window_lit" if rng.random() < 0.4 else "vr_window_dark" )
            box( m, e - 54, e + 54, n0 - 2.5, n0, z0 - 4, z0, "vr_stone_light" )
    for n in np.arange( n0 + 80, n1 - 40, 160.0 ):
        box( m, e0 - 1.2, e0 - 0.4, n - 50, n + 50, 200, 330, "vr_window_lit" if rng.random() < 0.5 else "vr_window_dark" )
    P.letters( m, "spa", ( 700.0, n0, 330.0 ), ( 1, 0, 0 ), 26, "dark" )
    for e in ( 100.0, 500.0, 900.0 ):
        P.wall_washer( m, f"Spa lamp {e}", ( e, n0, L2 + 70 ), ( 0, -1 ), 240 )
    P.wall_washer( m, "Spa west lamp", ( e0, 880.0, L1 + 80 ), ( -1, 0 ), 240 )
