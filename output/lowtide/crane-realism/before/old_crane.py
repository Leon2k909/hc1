import numpy as np
from map_kit import Model
METAL="metal"
HARBOUR_Z=-144
class CRANE:
    PANELS="lt_crane_red_panels"
def quay_crane( m, s, e ):
    """ A level-luffing quay crane on its rails: a portal you can walk under (200 clear), the machinery house and cab,
    and the lattice jib reaching out over the harbour. Collision on the legs and their bogies. """
    e = s * e
    n0, n1 = -1565.0, -1385.0
    paint = "lt_crane_red"
    for de in ( -70.0, 70.0 ):
        for n in ( n0, n1 ):
            m.box( ( e + de - 30, n - 9, 0.0 ), ( e + de + 30, n + 9, 22.0 ), "lt_steel", METAL )
            m.box( ( e + de - 8, n - 8, 22.0 ), ( e + de + 8, n + 8, 200.0 ), paint, METAL )
            for k in range( 1, 5 ):
                z = 22 + 178 * k / 5
                m.box( ( e + de - 9, n - 9, z - 1.5 ), ( e + de + 9, n + 9, z + 1.5 ), paint )
    for n in ( n0, n1 ):
        m.box( ( e - 82, n - 10, 200 ), ( e + 82, n + 10, 228 ), paint )
        m.beam( ( e - 70, n, 30 ), ( e + 70, n, 190 ), ( 4.0, 4.0 ), paint )
    for de in ( -70.0, 70.0 ):
        m.box( ( e + de - 10, n0 - 10, 200 ), ( e + de + 10, n1 + 10, 228 ), paint )
        m.beam( ( e + de, n0, 40 ), ( e + de, n1, 190 ), ( 4.0, 4.0 ), paint )
    m.collision_box( ( e - 82, n0 - 10, 200 ), ( e + 82, n1 + 10, 228 ), METAL )
    # The slewing house with its cab looking out over the water, and the A-frame.
    m.cylinder( ( e, ( n0 + n1 ) / 2 ), 60, 228, 240, { "side": "lt_steel", "top": "lt_steel" }, sides=16 )
    m.box( ( e - 60, n0 + 10, 240 ), ( e + 60, n1 - 10, 340 ), { "default": CRANE.PANELS, "+z": "lt_steel" } )
    m.box( ( e - 30, n0 - 30, 250 ), ( e + 30, n0 + 10, 320 ), { "default": paint, "-n": "rw_window_dark", "-e": "rw_window_dark",
                                                                "+e": "rw_window_dark" } )
    for de in ( -40.0, 40.0 ):
        m.beam( ( e + de, n0 + 40, 340 ), ( e + de * 0.3, ( n0 + n1 ) / 2, 560 ), ( 8.0, 8.0 ), paint )
        m.beam( ( e + de, n1 - 20, 340 ), ( e + de * 0.3, ( n0 + n1 ) / 2, 560 ), ( 8.0, 8.0 ), paint )
    # The jib: two lattice chords out to the south and up, then its nose.
    root, tip = np.array( ( e, n0 + 30, 340.0 ) ), np.array( ( e, n0 - 1050, 860.0 ) )
    for de in ( -14.0, 14.0 ):
        m.beam( root + ( de, 0, 0 ), tip + ( de * 0.4, 0, 0 ), ( 5.0, 5.0 ), paint )
        m.beam( root + ( de, 0, -26 ), tip + ( de * 0.4, 0, -10 ), ( 5.0, 5.0 ), paint )
    for k in range( 12 ):
        a = root + ( tip - root ) * k / 12
        b = root + ( tip - root ) * ( k + 1 ) / 12
        drop = lambda p, f: p + np.array( ( 0, 0, -26 + 16 * f ) )
        m.beam( a, drop( b, ( k + 1 ) / 12 ), ( 2.5, 2.5 ), paint )
    m.beam( np.array( ( e, ( n0 + n1 ) / 2, 560.0 ) ), tip + ( 0, 0, 10 ), ( 3.0, 3.0 ), "lt_steel" )
    m.box( tip - ( 8, 20, 30 ), tip + ( 8, 20, 6 ), paint )
    rod( m, tip - ( 0, 10, 30 ), ( e, n0 - 1040, HARBOUR_Z + 120 ), 0.8, "lt_steel", sides=4 )
    # The counterweight, on a beam back from the A-frame's head.
    head = np.array( ( e, ( n0 + n1 ) / 2, 560.0 ) )
    for de in ( -10.0, 10.0 ):
        m.beam( head + ( de, 0, 0 ), ( e + de, n1 + 40, 520.0 ), ( 6.0, 6.0 ), paint )
    m.box( ( e - 30, n1 + 10, 470 ), ( e + 30, n1 + 70, 530 ), "rw_concrete_dark" )


