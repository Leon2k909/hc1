import veridant_map as V
from veridant_map import *

def pool( m, water ):
    p0, p1, n0, n1 = POOL
    k = 12.0
    kz = POOL_KERB
    for a, b, c, d in ( ( p0, p1, n0, n0 + k ), ( p0, p1, n1 - k, n1 ), ( p0, p0 + k, n0 + k, n1 - k ), ( p1 - k, p1, n0 + k, n1 - k ) ):
        solid( m, a, b, c, d, 0, kz - 1.5, { "default": "vr_stone_dark", "+z": None } )
        solid( m, a - 1.2, b + 1.2, c - 1.2, d + 1.2, kz - 1.5, kz, "vr_stone_dark" )
    # The LED strip in the shadow under the kerb's lip, all round outside.
    for a, b, out in ( ( ( p0 - 0.6, n0 - 0.6 ), ( p1 + 0.6, n0 - 0.6 ), ( 0, -1 ) ), ( ( p0 - 0.6, n1 + 0.6 ), ( p1 + 0.6, n1 + 0.6 ), ( 0, 1 ) ),
                       ( ( p0 - 0.6, n0 ), ( p0 - 0.6, n1 ), ( -1, 0 ) ), ( ( p1 + 0.6, n0 ), ( p1 + 0.6, n1 ), ( 1, 0 ) ) ):
        P.led( m, ( a[0], a[1], kz - 2.3 ), ( b[0], b[1], kz - 2.3 ), v( out[0], out[1], 0 ), 1.0 )
    floor( m, p0 + k, p1 - k, n0 + k, n1 - k, 0.2, "vr_black" )
    card( water, "vr_pool", [ v( p0 + k, n0 + k, WATER_Z ), v( p1 - k, n0 + k, WATER_Z ), v( p1 - k, n1 - k, WATER_Z ), v( p0 + k, n1 - k, WATER_Z ) ], UP )
    # The boulder in the middle and a lower one behind it with the water welling over it.
    P.boulder( m, ( 10.0, -40.0, 0.0 ), 46, seed=3, squash=0.62, paint="vr_rock_dark" )
    # A light under the water on the boulder, as in the picture.
    P.LIGHTS.append( ( "Pool light", ( 70.0, -60.0, WATER_Z - 4.0 ), P.WARM, 150, False ) )
    P.boulder( m, ( -55.0, 22.0, 0.0 ), 26, seed=4, squash=0.5, paint="vr_rock_dark" )
    for k_, n in enumerate( ( -70.0, 50.0 ) ):
        P.wall_washer( m, f"Pool kerb light {k_}", ( p1, n, 8.0 ), ( 1, 0 ), 160, light=( k_ == 0 ), size=( 5.0, 3.0 ), rise=8 )
