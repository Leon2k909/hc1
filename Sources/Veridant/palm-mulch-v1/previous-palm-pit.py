import numpy as np
import riverdale_parts as P

def palm_pit( m, base, seed=0 ):
    """ Low, walkable limestone surround with a textured soil bed, for palms in paving. """
    e, n, z = base
    half, width, height = 35.0, 4.5, 3.0
    axes = ( ( 1, 0, 0 ), ( 0, 1, 0 ), ( 0, 0, 1 ) )
    # Separate lengths leave small masonry joints; bevels catch the grazing evening light.
    for ce, cn, sx, sy in ( ( e, n - half + width / 2, half * 2 - .3, width ),
                            ( e, n + half - width / 2, half * 2 - .3, width ),
                            ( e - half + width / 2, n, width, ( half - width ) * 2 - .3 ),
                            ( e + half - width / 2, n, width, ( half - width ) * 2 - .3 ) ):
        P.bevel_box( m, ( ce, cn, z + height / 2 ), axes, ( sx, sy, height ), "vr_stone_light", bevel=.55 )
    rng = np.random.default_rng( 12000 + abs( int( seed ) ) )
    inner, cells = half - width + .2, 6
    heights = rng.uniform( .32, .70, ( cells + 1, cells + 1 ) )
    for i in range( cells ):
        for j in range( cells ):
            points = [ ( e - inner + 2 * inner * x / cells, n - inner + 2 * inner * y / cells, z + heights[x, y] )
                       for x, y in ( ( i, j ), ( i + 1, j ), ( i + 1, j + 1 ), ( i, j + 1 ) ) ]
            m.polygon( "vr_palm_mulch", points )
