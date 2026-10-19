"""Railhead's overhead line equipment (DB Re 200), for railhead_props' masts, portals and drops, and its Ks signals'
fittings.

- h_mast: an HEB 200 mast (200 x 200 mm, 15 mm flanges, 9 mm web), hot-dip galvanised, bolted by its base plate to a
  600 x 600 mm cast foundation standing 300 mm out of the ground; its white number plate (250 x 150 mm) 2 m up and the
  yellow lightning warning triangle (200 mm) over it, on the face towards the track, and a cap plate on its top.
- insulator: a composite rod insulator, its silicone sheds alternating large and small between galvanised end
  fittings.
- y_hanger: the Y-shaped stitch wire under a drop's messenger clamp.
- tension_weights: an anchor mast's tensioning: a stack of round cast weights on a guided rod under a wheel and its
  balance lever, the wire's rope running over the wheel.
- signal_dressing: a Ks signal's fittings: the screen's white rim, a ladder up the mast's back, the Sh 1 light pair
  under the screen, a Zs 3 speed indicator box over it, a grey cable box at its foot and the mast's foundation collar.

Everything here is visual: the masts' collision stays railhead_props'.
"""
import math

import numpy as np

GALV = "rw_galvanised"
CONCRETE = "rw_mast_concrete"
DARK = "rw_steel_dark"


def _sign_uv( name ):
    try:
        import railhead_prop_materials as PM
        u0, v0, u1, v1 = PM.rect_uv( name )
    except Exception:
        u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
    return [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]


def _bevel( model, lo, hi, paint, bevel=0.4 ):
    import railhead_buffer as B
    from railhead_props import Frame
    F = Frame( ( 0.0, 0.0, 0.0 ), ( 0.0, 1.0 ) )         # x = -e, y = n
    lo, hi = np.asarray( lo, float ), np.asarray( hi, float )
    a, b = np.minimum( lo, hi ), np.maximum( lo, hi )
    B.bevel_box( model, F, ( -b[0], a[1], a[2] ), ( -a[0], b[1], b[2] ), paint, bevel )


def h_mast( model, e, n, ground, top, toward=None, plate=0 ):
    """ The mast at ( e, n ) from ground to top, its web across the track (along e). toward: the sign of e towards the
    track, for its plates (None: no plates); plate: which number (0 or 1). """
    from railhead_props import rod, quad
    # The foundation: 600 x 600 mm, 300 mm out of the ground, chamfered, with the base plate bolted on it.
    _bevel( model, ( e - 11.8, n - 11.8, ground - 3.0 ), ( e + 11.8, n + 11.8, ground + 11.8 ), CONCRETE, 0.8 )
    z0 = ground + 11.8
    _bevel( model, ( e - 7.9, n - 7.9, z0 ), ( e + 7.9, n + 7.9, z0 + 0.8 ), GALV, 0.15 )
    for dx in ( -6.0, 6.0 ):
        for dy in ( -6.0, 6.0 ):
            p = np.array( ( e + dx, n + dy, z0 + 0.8 ) )
            rod( model, p, p + np.array( ( 0, 0, 0.6 ) ), 0.75, DARK, 6, caps=( False, True ) )
            rod( model, p, p + np.array( ( 0, 0, 1.6 ) ), 0.4, DARK, 6, caps=( False, True ) )
    z0 += 0.8
    # The HEB 200: flanges across n (each 200 wide, 15 thick), the web between them along e... turned so its web runs
    # across the track: flanges face the track.
    for side in ( -1, 1 ):
        model.box( ( e + side * 3.94 - 0.3, n - 3.94, z0 ), ( e + side * 3.94 + 0.3, n + 3.94, top ), GALV, skip=( "-z", ) )
    model.box( ( e - 3.64, n - 0.18, z0 ), ( e + 3.64, n + 0.18, top ), GALV, skip=( "-z", ) )
    # Welded stiffeners at the foot and the cap plate.
    for side in ( -1, 1 ):
        model.box( ( e - 3.64, n + side * 0.18, z0 ), ( e + 3.64, n + side * 3.6, z0 + 0.4 ), GALV, skip=( "-z", ) )
    _bevel( model, ( e - 4.6, n - 4.6, top ), ( e + 4.6, n + 4.6, top + 0.6 ), GALV, 0.1 )
    if toward is not None:
        # The number plate 2 m up and the lightning triangle over it, on the flange facing the track.
        x = e + toward * ( 3.94 + 0.32 )
        centre = np.array( ( x, n, ground + 78.7 ) )
        right = np.array( ( 0.0, toward, 0.0 ) )            # reads left to right seen from the track
        quad( model, "rw_prop_signs", centre, right, ( 0, 0, 1 ), 7.8, 4.7,
              uv=_sign_uv( "mast_plate" if plate % 2 == 0 else "mast_plate_b" ) )
        quad( model, "rw_prop_signs", centre + np.array( ( 0, 0, 9.5 ) ), right, ( 0, 0, 1 ), 7.0, 7.0,
              uv=_sign_uv( "warn_bolt" ) )


def insulator( model, a, b ):
    """ A composite rod insulator along a..b: a glass-fibre core under silicone sheds, alternately 120 and 90 mm
    across, between galvanised end fittings. """
    from railhead_props import rod, _unit
    a, b = np.asarray( a, float ), np.asarray( b, float )
    axis = _unit( b - a )
    length = float( np.linalg.norm( b - a ) )
    end = min( 1.6, length * 0.15 )
    rod( model, a, a + axis * end, 0.9, GALV, 8, caps=( True, False ) )
    rod( model, b - axis * end, b, 0.9, GALV, 8, caps=( False, True ) )
    rod( model, a + axis * end, b - axis * end, 0.6, "rw_rubber", 6 )
    count = max( 3, int( ( length - 2 * end ) / 1.7 ) )
    for k in range( count ):
        t = end + ( length - 2 * end ) * ( k + 0.5 ) / count
        c = a + axis * t
        r = 2.35 if k % 2 == 0 else 1.75
        rod( model, c - axis * 0.18, c + axis * 0.18, r, "rw_rubber", 12, caps=( True, True ) )


def y_hanger( model, e, n, mz, span=60.0 ):
    """ The Y stitch: a stitch wire under the messenger either side of the support, its dropper in the middle. """
    from railhead_props import rod
    for s in ( -1, 1 ):
        rod( model, ( e, n + s * span / 2, mz + 0.6 ), ( e, n, mz - 4.0 ), 0.22, "copper_brown", 4 )
    rod( model, ( e, n, mz - 4.0 ), ( e, n, mz - 8.0 ), 0.2, "copper_brown", 4 )


def tension_weights( model, e, n, ground, top, toward ):
    """ An anchor mast's tension weights on the mast at ( e, n ), on its side away from the track (toward: the sign of
    e towards the track): the wheel and balance lever under the mast's head, the rope down to a stack of 18 round cast
    weights (300 mm across, 50 mm each) on their guide rod, and the rod's foot bracket. """
    from railhead_props import rod, disc
    x = e - toward * 9.0
    zw = top - 16.0
    # The wheel on its bracket.
    rod( model, ( e - toward * 4.2, n, zw ), ( x, n, zw ), 0.9, GALV, 8 )
    rod( model, ( x, n - 1.6, zw ), ( x, n + 1.6, zw ), 9.8, GALV, 20, caps=( True, True ) )
    rod( model, ( x, n - 1.8, zw ), ( x, n + 1.8, zw ), 2.0, DARK, 10, caps=( True, True ) )
    # The stack.
    z1 = ground + 70.0
    for k in range( 18 ):
        zb = z1 - 2.0 * ( k + 1 )
        rod( model, ( x, n, zb + 0.08 ), ( x, n, zb + 1.92 ), 5.9, CONCRETE if k % 6 == 5 else DARK, 16, caps=( True, True ) )
    rod( model, ( x, n, ground + 20.0 ), ( x, n, z1 + 6.0 ), 0.5, GALV, 6 )
    rod( model, ( x + toward * 9.8, n, zw ), ( x + toward * 9.8, n, z1 + 1.0 ), 0.25, GALV, 4 )
    rod( model, ( x - toward * 9.8, n, zw ), ( x - toward * 9.8, n, z1 + 6.0 ), 0.25, GALV, 4 )
    rod( model, ( x - toward * 9.8, n, z1 + 6.0 ), ( x, n, z1 + 6.0 ), 0.3, GALV, 4 )
    # The guide tube's brackets on the mast.
    for z in ( ground + 22.0, z1 + 2.0 ):
        rod( model, ( e - toward * 4.2, n, z ), ( x, n, z ), 0.5, GALV, 6 )


def signal_dressing( model, f, rail_z, ground, top, zc ):
    """ A Ks signal's fittings, in its frame f (y towards the trains it faces, the mast at x 0): the screen's white rim,
    a ladder up the mast's back to a platform behind the screen, the Sh 1 light pair under the screen, a Zs 3 box over
    it, the cable box at its foot and the foundation collar. """
    from railhead_props import rod, disc
    # The rim: a white border standing proud round the screen's black face.
    for x0, x1, z0, z1 in ( ( -11.8, 11.8, zc + 18.6, zc + 19.8 ), ( -11.8, 11.8, zc - 19.8, zc - 18.6 ),
                            ( -11.8, -10.6, zc - 18.6, zc + 18.6 ), ( 10.6, 11.8, zc - 18.6, zc + 18.6 ) ):
        f.box( model, x0, x1, 6.5, 6.9, z0, z1, "rw_white_paint", skip=( "back", ) )
    # The Zs 3 indicator over the screen: a black box with its lit digit.
    f.box( model, -5.2, 5.2, 2.6, 6.2, zc + 20.5, zc + 32.0, "rw_black" )
    f.quad( model, "rw_prop_signs", 0.0, 6.25, zc + 26.2, 4.6, 9.2, uv=_sign_uv( "zs3_6" ) )
    # The Sh 1 pair under the screen: two white lamps on a small black board, dark.
    f.box( model, -6.0, 6.0, 3.2, 6.0, zc - 30.0, zc - 23.0, "rw_black" )
    for x in ( -3.0, 3.0 ):
        disc( model, "rw_window_dark", f.p( x, 6.05, zc - 26.5 ), f.y, 1.4, 12 )
        f.box( model, x - 1.9, x + 1.9, 6.0, 7.8, zc - 24.6, zc - 24.2, "rw_black" )
    # The ladder up the mast's back to the screen, its stiles and rungs, a platform grating behind the screen.
    for x in ( -6.5, 6.5 ):
        rod( model, f.p( x, -7.0, ground + 12.0 ), f.p( x, -7.0, zc - 8.0 ), 0.55, "rw_steel_grey", 6 )
    z = ground + 18.0
    while z < zc - 10.0:
        rod( model, f.p( -6.5, -7.0, z ), f.p( 6.5, -7.0, z ), 0.4, "rw_steel_grey", 6 )
        z += 11.8
    for z in ( ground + 40.0, ground + 100.0 ):
        rod( model, f.p( 0.0, -3.5, z ), f.p( 0.0, -7.0, z ), 0.5, "rw_steel_grey", 6 )
    f.box( model, -12.0, 12.0, -14.0, 2.6, zc - 24.0, zc - 23.0, "rw_steel_grey" )
    # The cable box at its foot and the foundation's collar round the mast.
    f.box( model, 6.0, 16.0, -7.0, 2.0, ground + 5.0, ground + 30.0, { "default": "rw_steel_grey", "top": "rw_steel_dark" } )
    f.box( model, 5.4, 16.6, -7.6, 2.6, ground + 29.6, ground + 31.0, "rw_steel_dark" )
    rod( model, f.p( 0.0, 0.0, ground + 5.0 ), f.p( 0.0, 0.0, ground + 8.5 ), 5.9, CONCRETE, 16, caps=( False, True ) )
