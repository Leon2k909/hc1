"""Railhead's running gear: wheelsets and two-axle bogies for every rail vehicle railhead_props builds.

railhead_props._wheelset and _bogie call these. A frame F is a railhead_props.Frame (vehicle_frame): x across, y along
the vehicle (a point a behind its front at y = -a), z up from the rails' top. Everything here is visual: the vehicles'
collision is their bodies'.

The bogie is a welded H-frame bogie of the kind under Germany's regional double-deck cars and coaches: side frames
dropped between the axles (a fish belly) and raised over the axle boxes, two primary coil springs over each axle box,
an air spring on each side frame's middle carrying the body, a box-section transom with two brake-disc calipers per
axle, yaw dampers, and wheelsets with dished webs, hubs, and two ventilated brake discs per axle (none on a motor
bogie's powered axles, whose discs are on the wheels).
"""
import math

import numpy as np

STEEL = "rw_bogie_dust"     # the bogie's painted steel under brake and ballast dust: grey-brown (railhead_prop_materials)
LOW = "rw_bogie_brake"      # the lowest, dirtiest parts: axle boxes, wheel webs, springs
DARK = "rw_steel_dark"
MACHINED = "rw_steel_grey"  # brake discs' and axles' bright faces
BRIGHT = "rw_tyre_bright"   # the wheels' turned treads and tyre faces
DAMPER = "rw_damper_grey"   # the dampers' light grey bodies
RUBBER = "rw_rubber"


def _p( F, x, y, z ):
    return F.p( x, y, z )


def wheelset( model, F, a, r, discs=True ):
    """ A wheelset at depth a: wheels of radius r on their treads, flanges inside, dished webs and hubs, the axle,
    and two ventilated brake discs between the wheels (discs False: none). """
    from railhead_props import rod, disc
    y = -a
    for xs in ( 1.0, -1.0 ):
        # The tread (conical, a touch smaller outside), the flange inside it, the rim's inner face.
        rod( model, _p( F, xs * 27.8, y, r ), _p( F, xs * 32.3, y, r ), r, BRIGHT, 24, caps=( False, False ) )
        rod( model, _p( F, xs * 26.9, y, r ), _p( F, xs * 27.8, y, r ), r + 1.1, LOW, 24, caps=( True, False ) )
        # The flange's rim, worn bright where it rubs the rail's gauge face.
        rod( model, _p( F, xs * 27.0, y, r ), _p( F, xs * 27.7, y, r ), r + 1.15, BRIGHT, 24 )
        # The web is dished in from the rim to the hub on the outer face, and the hub stands proud.
        # The tyre's outer face is turned bright on the lathe; the web inside it is dark and dusty.
        # A 50 mm turned ring round the tyre's outer face, the dished web inside it brake-dust dark.
        disc( model, BRIGHT, _p( F, xs * 32.3, y, r ), F.x * xs, r, sides=24 )
        rod( model, _p( F, xs * 32.3, y, r ), _p( F, xs * 32.45, y, r ), r - 2.0, LOW, 24, caps=( False, True ) )
        rod( model, _p( F, xs * 32.3, y, r ), _p( F, xs * 33.4, y, r ), 4.6, DARK, 12, caps=( False, True ) )
        rod( model, _p( F, xs * 26.9, y, r ), _p( F, xs * 25.4, y, r ), 5.0, LOW, 12, caps=( False, False ) )
    rod( model, _p( F, -25.4, y, r ), _p( F, 25.4, y, r ), 3.3, MACHINED, 10 )
    if discs:
        for xs in ( 1.0, -1.0 ):
            x0, x1 = xs * 9.2, xs * 13.6
            rod( model, _p( F, x0, y, r ), _p( F, x1, y, r ), 12.6, MACHINED, 24, caps=( True, True ) )
            # The ventilation gap round the disc's rim reads as a dark band, the hub flange darker.
            rod( model, _p( F, xs * 11.2, y, r ), _p( F, xs * 11.6, y, r ), 12.75, DARK, 24 )
            rod( model, _p( F, xs * 8.2, y, r ), _p( F, x0, y, r ), 5.5, LOW, 12, caps=( True, False ) )


def _prism( model, F, x_in, x_out, stations, paint ):
    """ A plate girder along y: stations ( y, z_low, z_high ), increasing in y, extruded from x_in to x_out (either
    order), all faces drawn but the ends' if they're thin. """
    from railhead_props import _fpoly
    xs = 1.0 if x_out > x_in else -1.0
    for x, toward in ( ( x_out, xs ), ( x_in, -xs ) ):
        for ( ya, la, ha ), ( yb, lb, hb ) in zip( stations, stations[1:] ):
            _fpoly( model, F, paint, [ ( x, ya, la ), ( x, yb, lb ), ( x, yb, hb ), ( x, ya, ha ) ], ( toward, 0, 0 ) )
    for ( ya, la, ha ), ( yb, lb, hb ) in zip( stations, stations[1:] ):
        dy = yb - ya
        up = ( 0.0, -( hb - ha ), dy )
        down = ( 0.0, ( lb - la ), -dy )
        _fpoly( model, F, paint, [ ( x_in, ya, ha ), ( x_out, ya, ha ), ( x_out, yb, hb ), ( x_in, yb, hb ) ], up )
        _fpoly( model, F, paint, [ ( x_in, ya, la ), ( x_out, ya, la ), ( x_out, yb, lb ), ( x_in, yb, lb ) ], down )
    for ( y, lo, hi ), toward in ( ( stations[0], -1.0 ), ( stations[-1], 1.0 ) ):
        _fpoly( model, F, paint, [ ( x_in, y, lo ), ( x_out, y, lo ), ( x_out, y, hi ), ( x_in, y, hi ) ],
                ( 0, toward, 0 ) )


def coil_spring( model, F, x, y, z0, z1, radius=2.4, wire=0.5, turns=4.5, steps=30, paint=LOW ):
    """ A coil spring standing from z0 to z1 at ( x, y ), with flattened end coils. """
    from railhead_props import rod
    pts = []
    for k in range( steps + 1 ):
        t = k / steps
        ang = 2 * math.pi * turns * t
        # The end coils are closed: the pitch eases to nothing at both ends.
        h = t - 0.06 * math.sin( 2 * math.pi * t )
        pts.append( _p( F, x + radius * math.cos( ang ), y + radius * math.sin( ang ), z0 + wire + ( z1 - z0 - 2 * wire ) * h ) )
    for p, q in zip( pts, pts[1:] ):
        rod( model, p, q, wire, paint, 5 )


def bogie( model, F, a, wheelbase, r, motor=False ):
    """ A two-axle H-frame bogie centred at depth a (see the module's docstring). Its side frames sit outside the
    wheels at x +-33.5..38.5; on a motor bogie a traction motor hangs between the axles and the axles have no discs. """
    from railhead_props import rod, disc
    half = wheelbase / 2
    for k in ( -1, 1 ):
        wheelset( model, F, a + k * half, r, discs=not motor )
    yc = -a
    reach = half + r * 0.72
    for xs in ( 1.0, -1.0 ):
        xi, xo = xs * 33.6, xs * 38.4
        # The side frame: raised over the axle boxes, dropped (a fish belly) between them for the air spring.
        z_hi, z_lo = r + 15.0, r + 9.0          # over the axle boxes
        m_hi, m_lo = r + 10.5, r + 0.5          # between
        stations = [ ( -reach, z_lo + 1.5, z_hi - 2.0 ), ( -half - 5.0, z_lo, z_hi ), ( -half + 6.0, z_lo, z_hi ),
                     ( -half + 15.0, m_lo, m_hi ), ( half - 15.0, m_lo, m_hi ), ( half - 6.0, z_lo, z_hi ),
                     ( half + 5.0, z_lo, z_hi ), ( reach, z_lo + 1.5, z_hi - 2.0 ) ]
        _prism( model, F, xi, xo, [ ( yc + yy, lo, hi ) for yy, lo, hi in stations ], STEEL )
        # Stiffening ribs on the outer web.
        for yy in ( -half + 10.5, -6.0, 6.0, half - 10.5 ):
            F.box( model, xo, xo + xs * 0.5, yc + yy - 0.4, yc + yy + 0.4, m_lo + 0.6, m_hi - 0.6, STEEL,
                   skip=( "left" if xs > 0 else "right", ) )
        for k in ( -1, 1 ):
            ya = yc + k * half
            # The axle box: a cylinder outside the wheel, a cover with six bolts, the arm to the frame.
            rod( model, _p( F, xs * 33.4, ya, r ), _p( F, xs * 39.6, ya, r ), 5.0, LOW, 16, caps=( False, True ) )
            rod( model, _p( F, xs * 39.6, ya, r ), _p( F, xs * 40.4, ya, r ), 3.8, MACHINED, 16, caps=( False, True ) )
            for j in range( 6 ):
                t = j * math.pi / 3
                rod( model, _p( F, xs * 40.4, ya + 3.0 * math.cos( t ), r + 3.0 * math.sin( t ) ),
                     _p( F, xs * 40.8, ya + 3.0 * math.cos( t ), r + 3.0 * math.sin( t ) ), 0.38, DARK, 6,
                     caps=( False, True ) )
            F.box( model, xi, xo, ya - 8.5, ya + 8.5, r + 3.5, r + 5.5, STEEL )
            # Two primary coil springs on the arm, fore and aft of the axle, under the frame.
            for dy in ( -5.6, 5.6 ):
                coil_spring( model, F, xs * 36.0, ya + dy, r + 5.5, z_lo, 2.3, 0.55, 4.0, 28 )
            # A vertical damper beside the inner spring: a 40 mm light grey body on its dark rod and eyes.
            rod( model, _p( F, xs * 39.2, ya - k * 9.5, r + 1.0 ), _p( F, xs * 39.2, ya - k * 9.5, r + 3.0 ), 0.45,
                 DARK, 6, caps=( True, True ) )
            rod( model, _p( F, xs * 39.2, ya - k * 9.5, r + 3.0 ), _p( F, xs * 39.2, ya - k * 9.5, z_hi - 1.0 ), 0.8,
                 DAMPER, 10, caps=( True, True ) )
        # The air spring on the frame's middle: a rubber bellows under a steel top plate, the body's bolster on it.
        c = _p( F, xs * 36.0, yc, m_hi )
        rod( model, c, c + F.z * 1.2, 6.2, STEEL, 16, caps=( False, True ) )
        rod( model, c + F.z * 1.2, c + F.z * 4.2, 7.4, RUBBER, 20 )
        rod( model, c + F.z * 4.2, c + F.z * 7.0, 6.8, RUBBER, 20 )
        rod( model, c + F.z * 7.0, c + F.z * 8.0, 7.0, DARK, 16, caps=( False, True ) )
        # The yaw damper from the frame's end towards the body, along it.
        p0, p1 = _p( F, xs * 40.6, yc - half + 4.0, z_hi - 2.0 ), _p( F, xs * 40.6, yc - 8.0, m_hi + 6.0 )
        rod( model, p0, p0 + ( p1 - p0 ) * 0.62, 1.3, DAMPER, 10, caps=( True, True ) )
        rod( model, p0 + ( p1 - p0 ) * 0.6, p1, 0.55, MACHINED, 6, caps=( False, True ) )
    # The transom: two box sections between the side frames, with the calipers hung from them.
    for yy in ( -7.5, 4.5 ):
        F.box( model, -33.6, 33.6, yc + yy, yc + yy + 3.0, r + 1.0, r + 8.5, STEEL )
    if motor:
        F.box( model, -20.0, 20.0, yc - half + r + 2.0, yc - 4.0, r - 5.0, r + 9.0, STEEL )
        rod( model, _p( F, -14.0, yc - half + r + 6.0, r ), _p( F, 14.0, yc - half + r + 6.0, r ), 7.5, STEEL, 14,
             caps=( True, True ) )
    else:
        for k in ( -1, 1 ):
            ya = yc + k * half
            for xs in ( 1.0, -1.0 ):
                # The caliper astride the disc's rim, on a bracket from the transom.
                y_cal = ya - k * 12.0
                F.box( model, xs * 9.0, xs * 13.8, y_cal - 1.8, y_cal + 1.8, r + 8.0, r + 13.0, DARK )
                F.box( model, xs * 10.4, xs * 12.4, min( y_cal, yc + ( 3.0 if k > 0 else -6.0 ) ),
                       max( y_cal, yc + ( 3.0 if k > 0 else -6.0 ) ), r + 9.5, r + 11.0, STEEL )
