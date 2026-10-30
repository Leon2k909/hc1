import numpy as np
from riverdale_parts import unit, v, obox, UP, STONE

def bench( m, c, along, length=72.0, z0=0.0 ):
    """ A stone bench with a teak seat. """
    d = unit( v( along[0], along[1], 0 ) )
    s = np.cross( UP, d )
    b = v( c[0], c[1], z0 )
    for sg in ( -1, 1 ):
        obox( m, b + d * ( length / 2 - 8 ) * sg + UP * 8, d, ( 10, 16, 16 ), "vr_stone" )
    for k in range( 4 ):
        obox( m, b + s * ( -6 + 4 * k ) + UP * 17, d, ( length, 3.4, 2 ), "vr_timber" )
    m.oriented_box( b + UP * 9, ( d, s, UP ), ( length, 18, 18 ), {}, STONE )
