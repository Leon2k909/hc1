"""Railhead's double-deck EMU: its roof equipment and cab doors, for railhead_props._emu_car.

A car here is railhead_props._Car: its own depths d from its cab's coupler face (or front gangway) back, x across,
z up from the rails' top. All of it is visual; the car's collision is its body's.

- ac_pod: a roof-mounted air-conditioning unit, 2.0 x 1.2 m and 0.4 m tall, sunk into the roof's crown so it stands
  ~250 mm proud: a rounded light-grey casing with a seam, two condenser fans under round grilles on top, louvred
  intakes along its sides, lifting eyes and bolted feet.
- cable_duct: the roof's cable duct, a slim covered trough along the roof off the centre line, with joint straps
  every 1.2 m, stepping round the pods (and the pantograph's base on the rear car).
- cab_door: the cab's side door round the cab's side window: its seam, a recessed handle, a grab rail each side and a
  hung step under it.
"""
import math

import numpy as np

CASING = "rw_train_grey"
DARK = "rw_steel_dark"
GREY = "rw_steel_grey"


def _y( car, d ):
    return -car.a( d )


def _bevel( car, x0, x1, d0, d1, z0, z1, paint, bevel=0.6, edge=None ):
    import railhead_buffer as B
    y0, y1 = sorted( ( _y( car, d0 ), _y( car, d1 ) ) )
    B.bevel_box( car.model, car.F, ( min( x0, x1 ), y0, z0 ), ( max( x0, x1 ), y1, z1 ), paint, bevel, edge )


def ac_pod( car, d0, d1 ):
    """ An air-conditioning pod over d0..d1, centred on the roof. """
    import railhead_props as P
    roof = P.EMU_ROOF
    hw = 23.5
    z0, z1 = roof - 6.0, roof + 9.8
    dm = ( d0 + d1 ) / 2
    _bevel( car, -hw, hw, d0, d1, z0, z1, CASING, 2.2 )
    # The lid's seam and its edge trim.
    _bevel( car, -hw - 0.15, hw + 0.15, d0 - 0.15, d1 + 0.15, z1 - 3.2, z1 - 2.8, DARK, 0.1 )
    # Two condenser fans under round grilles, each a dark well with a hub, bars across it and a rim.
    for dc in ( dm - 18.5, dm + 18.5 ):
        c = car.p( 0.0, dc, z1 + 0.02 )
        P.disc( car.model, DARK, c, car.F.z, 10.2, sides=28 )
        P.rod( car.model, c, c + car.F.z * 0.55, 10.8, GREY, 28 )
        P.rod( car.model, c + car.F.z * 0.1, c + car.F.z * 0.7, 2.2, GREY, 12, caps=( False, True ) )
        for k in range( 6 ):
            t = k * math.pi / 6
            u = car.F.x * math.cos( t ) + car.F.y * math.sin( t )
            P.rod( car.model, c - u * 10.2 + car.F.z * 0.45, c + u * 10.2 + car.F.z * 0.45, 0.18, GREY, 4 )
        for r in ( 4.4, 7.2 ):
            ring = [ c + ( car.F.x * math.cos( 2 * math.pi * k / 20 ) + car.F.y * math.sin( 2 * math.pi * k / 20 ) ) * r
                     + car.F.z * 0.45 for k in range( 21 ) ]
            for a, b in zip( ring, ring[1:] ):
                P.rod( car.model, a, b, 0.16, GREY, 4 )
    # Louvred intakes along both sides.
    for xs in ( 1.0, -1.0 ):
        x = xs * ( hw + 0.02 )
        for da, db in ( ( d0 + 6.0, dm - 4.0 ), ( dm + 4.0, d1 - 6.0 ) ):
            car.poly( DARK, [ ( x, da, roof + 1.0 ), ( x, db, roof + 1.0 ), ( x, db, roof + 6.0 ), ( x, da, roof + 6.0 ) ],
                      ( xs, 0, 0 ) )
            for k in range( 6 ):
                z = roof + 1.4 + 0.8 * k
                p = car.p( x + xs * 0.25, da, z )
                q = car.p( x + xs * 0.25, db, z )
                P.rod( car.model, p, q, 0.2, CASING, 4 )
        # Bolted feet onto the roof and a lifting eye at each end.
        for dd in ( d0 + 8.0, d1 - 8.0 ):
            _bevel( car, xs * ( hw - 1.0 ), xs * ( hw + 2.4 ), dd - 3.0, dd + 3.0, roof - 2.5, roof - 0.9, DARK, 0.2 )
    for dd in ( d0 + 3.0, d1 - 3.0 ):
        P.rod( car.model, car.p( -1.6, dd, z1 ), car.p( -1.6, dd, z1 + 1.6 ), 0.35, GREY, 6 )
        P.rod( car.model, car.p( 1.6, dd, z1 ), car.p( 1.6, dd, z1 + 1.6 ), 0.35, GREY, 6 )
        P.rod( car.model, car.p( -1.6, dd, z1 + 1.6 ), car.p( 1.6, dd, z1 + 1.6 ), 0.35, GREY, 6 )


def cable_duct( car, d0, d1, *avoid, pantograph=False ):
    """ The roof's cable duct along x +14 from d0 to d1, broken where avoid's ( d0, d1 ) spans are (it runs under the
    pods' feet there), and with the pantograph's high-voltage cable on insulators on the rear car. """
    import railhead_props as P
    x0, x1 = 11.0, 17.0
    roof = P.EMU_ROOF
    z_at = lambda x: float( np.interp( x, [ 0.0, 12.0, 25.0 ], [ roof, 182.0, 180.8 ] ) )
    z0 = z_at( x1 ) - 0.4
    spans = [ ( d0, d1 ) ]
    for a, b in avoid:
        out = []
        for lo, hi in spans:
            out += [ ( lo, min( hi, a - 2.0 ) ), ( max( lo, b + 2.0 ), hi ) ]
        spans = [ ( lo, hi ) for lo, hi in out if hi - lo > 6.0 ]
    for lo, hi in spans:
        _bevel( car, x0, x1, lo, hi, z0, z0 + 3.0, CASING, 0.35 )
        d = lo + 24.0
        while d < hi - 6.0:
            _bevel( car, x0 - 0.25, x1 + 0.25, d - 0.8, d + 0.8, z0 - 0.1, z0 + 3.25, DARK, 0.1 )
            d += 47.0
    if pantograph:
        # The high-voltage cable from the pantograph's base along the roof to the roof bushing, on post insulators.
        za = roof + 4.5
        pts = [ ( -6.0, 700.0, za ), ( -6.0, 660.0, za ), ( -6.0, 600.0, za ) ]
        for x, d, z in pts:
            P.rod( car.model, car.p( x, d, roof - 0.5 ), car.p( x, d, z - 0.6 ), 1.0, "rw_rubber", 10, caps=( False, True ) )
            for k in range( 4 ):
                zz = roof + 0.6 + k * 0.85
                P.rod( car.model, car.p( x, d, zz ), car.p( x, d, zz + 0.3 ), 1.45, "rw_rubber", 10, caps=( True, True ) )
        P.rod( car.model, car.p( *pts[0] ), car.p( *pts[-1] ), 0.55, GREY, 6 )
        P.rod( car.model, car.p( -6.0, 600.0, za ), car.p( -6.0, 594.0, roof ), 0.55, GREY, 6 )


def cab_door( car, xs ):
    """ The cab's side door on side xs, round its side window: a 3 mm seam (a dark line), a recessed handle, a grab
    rail each side on stand-offs, and a hung step under the sill. """
    import railhead_props as P
    import railhead_train as T
    W = P.EMU_W
    d0, d1, z0, z1 = 59.0, 109.0, 21.0, 150.0
    x = xs * ( W + 0.1 )
    seam = 0.3
    # Its leading edge leans back with the windscreen above the waist, where the cab's side curves into the nose.
    lean_z, d_top = 118.0, 74.0
    for a, b, c, e in ( ( d0, d0 + seam, z0, lean_z ), ( d1 - seam, d1, z0, z1 ), ( d_top, d1, z1 - seam, z1 ) ):
        T._face( car, xs, x, a, b, c, e, "dark" )
    car.poly( "rw_black", [ ( x, d0, lean_z ), ( x, d0 + seam, lean_z ), ( x, d_top + seam, z1 ), ( x, d_top, z1 ) ],
              ( xs, 0, 0 ) )
    # The handle in its dished recess under the window, at the trailing edge.
    T._face( car, xs, x + xs * 0.02, d1 - 9.0, d1 - 3.0, 92.0, 96.0, "dark", radius=1.4 )
    P.rod( car.model, car.p( xs * ( W + 0.2 ), d1 - 8.0, 94.0 ), car.p( xs * ( W + 0.2 ), d1 - 4.0, 94.0 ), 0.45,
           GREY, 8, caps=( True, True ) )
    # Grab rails either side of the door, on stand-offs.
    for d in ( d0 - 4.0, d1 + 4.0 ):
        a, b = car.p( xs * ( W + 2.3 ), d, 38.0 ), car.p( xs * ( W + 2.3 ), d, 128.0 )
        P.rod( car.model, a, b, 0.62, GREY, 10, caps=( True, True ) )
        for z in ( 42.0, 85.0, 124.0 ):
            P.rod( car.model, car.p( xs * W, d, z ), car.p( xs * ( W + 2.3 ), d, z ), 0.4, GREY, 6 )
    # The step: a ribbed plate hung below the sill on two brackets.
    _bevel( car, xs * ( W - 8.0 ), xs * ( W + 2.0 ), d0 + 4.0, d1 - 4.0, 11.0, 12.4, GREY, 0.2, DARK )
    for d in ( d0 + 6.0, d1 - 6.0 ):
        _bevel( car, xs * ( W - 4.0 ), xs * ( W - 2.4 ), d - 0.8, d + 0.8, 12.4, 19.5, DARK, 0.15 )
    for k in range( 5 ):
        d = d0 + 8.0 + k * ( d1 - d0 - 16.0 ) / 4
        _bevel( car, xs * ( W - 7.0 ), xs * ( W + 1.5 ), d - 0.3, d + 0.3, 12.4, 12.65, DARK, 0.05 )


def roof_details( car, d0, d1, cab=False, avoid=() ):
    """ What breaks up the roof seen from the footbridge: the rain gutters along both shoulders (a dark drip line), the
    roof sheets' welded seams across it every 1.5 m (skipping avoid's ( d0, d1 ) spans, the pods and pantograph), and
    on a cab car two GSM-R fin antennas and a whip just behind the cab, on bolted bases. Visual only. """
    import railhead_props as P
    prof = P.EMU_UPPER
    xs_, zs_ = [ p[0] for p in prof ][::-1], [ p[1] for p in prof ][::-1]
    z_at = lambda x: float( np.interp( abs( x ), xs_, zs_ ) )
    # The gutters: a drip strip standing proud of the shoulder.
    for s in ( 1.0, -1.0 ):
        P.rod( car.model, car.p( s * 53.9, d0 + 2.0, 170.0 ), car.p( s * 53.9, d1 - 2.0, 170.0 ), 0.55, DARK, 5 )
    # The sheets' seams across the roof's crown, as raised weld beads.
    xs = np.linspace( -40.0, 40.0, 11 )
    d = d0 + 30.0
    while d < d1 - 10.0:
        if not any( a - 4.0 < d < b + 4.0 for a, b in avoid ):
            pts = [ car.p( x, d, z_at( x ) + 0.12 ) for x in xs ]
            P.polyline( car.model, pts, 0.16, DARK, 4 )
        d += 59.0
    if cab:
        roof = P.EMU_ROOF
        for x, dd in ( ( -8.0, 128.0 ), ( 8.0, 140.0 ) ):
            _bevel( car, x - 2.6, x + 2.6, dd - 4.0, dd + 4.0, roof - 0.6, roof + 0.4, GREY, 0.2 )
            # A swept-back fin: a thin blade, its leading edge raked.
            y0, y1 = _y( car, dd - 3.0 ), _y( car, dd + 3.0 )
            lead, trail = ( y0, y1 ) if car.s > 0 else ( y1, y0 )
            F = car.F
            pts = [ F.p( x, lead, roof + 0.4 ), F.p( x, trail, roof + 0.4 ), F.p( x, trail, roof + 4.6 ),
                    F.p( x, trail + ( lead - trail ) * 0.35, roof + 4.6 ) ]
            for side in ( 1.0, -1.0 ):
                q = [ p + F.x * side * 0.35 for p in pts ]
                P.outward( car.model, "rw_black", q, F.x * side )
            P.outward( car.model, "rw_black", [ pts[2] + F.x * 0.35, pts[3] + F.x * 0.35, pts[3] - F.x * 0.35,
                                                pts[2] - F.x * 0.35 ], F.z )
        P.rod( car.model, car.p( 0.0, 150.0, roof - 0.2 ), car.p( 0.0, 150.0, roof + 1.0 ), 1.2, GREY, 10,
               caps=( False, True ) )
        P.rod( car.model, car.p( 0.0, 150.0, roof + 1.0 ), car.p( 0.0, 150.0, roof + 16.0 ), 0.18, "rw_black", 5,
               caps=( False, True ) )
