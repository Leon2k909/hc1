import numpy as np
from ares_map import rod

def pipe_run( m, a, b, r, paint, bracket=120.0 ):
    """ A pipe from a to b (plan points) with a steel bracket and a flange every so often. Drawn only. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    rod( m, a, b, r, paint, sides=10 )
    length = float( np.linalg.norm( b - a ) )
    along = ( b - a ) / length
    for k in range( 1, int( length // bracket ) + 1 ):
        p = a + along * bracket * k
        half = np.abs( along ) * 1.2 + ( 1 - np.abs( along ) ) * ( r + 1.6 )
        m.box( p - half, p + half, "ar_gunmetal" )
