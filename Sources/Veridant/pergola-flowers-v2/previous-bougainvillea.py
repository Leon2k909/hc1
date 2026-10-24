def bougainvillea( m, at, right, w, h, seed=0, off=2.0 ):
    rng = np.random.default_rng( abs( int( seed ) ) )
    right = unit( right )
    out = np.cross( right, UP )
    count = max( 1, int( w / 30 ) )
    for i in range( count ):
        f = ( i + 0.5 ) / count - 0.5
        s = h * rng.uniform( 0.6, 1.0 )
        c = v( *at ) + right * ( f * w ) - UP * ( s / 2 ) + out * ( off + rng.uniform( 0, 4 ) )
        sheet( m, "vr_foliage", VM.FOLIAGE, VM.FOLIAGE_ATLAS, "flowers", c, right, UP, s, s, 0.0, True )
