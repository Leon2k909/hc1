import numpy as np
from veridant_parts import box, v, led

def counter_shelves( m, lo, hi, z0, face="+e" ):
    """ A back bar: dark shelves with lit bottles drawn as small blocks. """
    e0, n0 = lo
    e1, n1 = hi
    box( m, e0, e1, n0, n1, z0, z0 + 90, "vr_timber_dark" )
    outv = { "+e": v( 1, 0, 0 ), "-e": v( -1, 0, 0 ), "+n": v( 0, 1, 0 ), "-n": v( 0, -1, 0 ) }[face]
    rng = np.random.default_rng( int( abs( e0 * 7 + n0 * 3 ) ) % 1000 )
    for z in ( 40.0, 58.0, 76.0 ):
        if face in ( "+e", "-e" ):
            x = e1 if face == "+e" else e0
            led( m, ( x + outv[0] * 0.2, n0 + 3, z - 0.5 ), ( x + outv[0] * 0.2, n1 - 3, z - 0.5 ), outv, 0.6, "vr_led_soft" )
            n = n0 + 5
            while n < n1 - 5:
                hh = rng.uniform( 7, 12 )
                box( m, x + outv[0] * 0.5 - 1.5, x + outv[0] * 0.5 + 1.5, n, n + 2.6, z, z + hh, "vr_brass" if rng.random() < 0.4 else "vr_yacht_glass" )
                n += rng.uniform( 3.5, 6 )
        else:
            y = n1 if face == "+n" else n0
            led( m, ( e0 + 3, y + outv[1] * 0.2, z - 0.5 ), ( e1 - 3, y + outv[1] * 0.2, z - 0.5 ), outv, 0.6, "vr_led_soft" )
