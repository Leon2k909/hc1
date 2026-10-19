"""
Railhead's architectural detail, drawn on the structure's own models by railhead_station: cast-iron shed columns with
moulded bases, capitals and spandrel brackets, the valley girder's flanges, stiffeners and rivets, the platform
canopies' structure (round columns, tapered cantilevers, purlins, fascias, gutters and downpipes), the booking hall's
pilasters, entablature, dado, string course, archivolts and entrance door frames, the gallery's balusters and coffers,
the vault's moulded ribs and panel borders, the shed's arcade mouldings, the rib shoes and lattice bars, the
footbridge's roof beams, fascias, handrails and stiffeners, the stairs' nosings and handrails, and the platforms'
jointed coping and ramp rails.

Everything here is visual: no collision (railhead_station keeps the gameplay collision as it was). Plan inches
( e east, n north, z up ), as map_kit. Sizes are a c.1900 German terminus's (see railhead_station's docstring).
"""
import math
import random

import numpy as np

import railhead_profiles as P
import railhead_structure_detail as D

IRON = "rw_steel"               # the shed's painted cast and wrought iron
IRON_DARK = "rw_steel_dark"
GREY = "rw_steel_grey"
RAIL = IRON_DARK                # handrails: the station's dark grey-green ironwork, not a pale tube
STONE = "rw_dressed"
PLASTER = "render_cream"
BRONZE = "copper_brown"


# ---------------------------------------------------------------------------------------------------------------------
# Shared parts

def spandrel( model, e, n, axis, side, z_foot, z_top, reach, width, paint=IRON, web=True, ring=True, segs=8,
              face_r=0.0 ):
    """ A curved cast bracket in the upright plane through ( e, n ) along axis ('e' or 'n'), reaching out side (+1/-1)
    from face_r (the column's face) to reach, from z_foot up to z_top: a moulded curved rib (vertical where it leaves the
    column, level under the beam), a thin spandrel web filling the corner, a cast ring in the web and a flange plate under
    the beam. width: the rib's thickness across the plane. """
    def pt( r, z, d=0.0 ):
        return np.array( ( e + side * r, n + d, z ) if axis == "e" else ( e + d, n + side * r, z ), float )
    across = np.array( ( 0.0, 1.0, 0.0 ) if axis == "e" else ( 1.0, 0.0, 0.0 ) )
    span_r, span_z = reach - face_r, z_top - z_foot
    curve = []
    for k in range( segs + 1 ):
        t = math.pi / 2 * k / segs
        curve.append( ( face_r + span_r * ( 1 - math.cos( t ) ), z_foot + span_z * math.sin( t ) ) )
    # The rib: a flat bar along the curve, its depth square to the curve.
    depth = 3.0
    for ( r0, z0 ), ( r1, z1 ) in zip( curve, curve[1:] ):
        model.beam( pt( r0, z0 ), pt( r1, z1 ), ( depth, width ), paint, up=across )
    if web:
        # The web: from the curve up to the corner ( face, top ), both faces, a little thinner than the rib.
        corner = ( face_r, z_top - 1.0 )
        for d in ( -width * 0.25, width * 0.25 ):
            for ( r0, z0 ), ( r1, z1 ) in zip( curve, curve[1:] ):
                pts = [ pt( r0, z0, d ), pt( r1, z1, d ), pt( *corner, d ) ]
                towards = across * ( 1 if d > 0 else -1 )
                P._poly( model, paint, pts, towards )
        if ring:
            # A cast ring pierced through the web's middle, as on the shed brackets of the 1880s.
            rc, zc = face_r + span_r * 0.32, z_foot + span_z * 0.66
            rad = min( span_r, span_z ) * 0.16
            ring_pts = [ pt( rc + rad * math.cos( 2 * math.pi * k / 16 ), zc + rad * math.sin( 2 * math.pi * k / 16 ) )
                         for k in range( 17 ) ]
            P.tube_path( model, ring_pts, 0.6, paint, sides=6, cap=False )
    # The flange plate under the beam, bolted up.
    a, b = pt( face_r, z_top - 0.8, -width ), pt( reach + 2, z_top, width )
    model.box( np.minimum( a, b ), np.maximum( a, b ), paint )
    for r in ( reach - 3.0, ( face_r + reach ) / 2 ):
        for d in ( -width * 0.6, width * 0.6 ):
            P.bolt( model, pt( r, z_top - 0.8, d ), ( 0, 0, -1 ), radius=0.4, length=0.3, paint=IRON_DARK, washer=False )


def round_column( model, e, n, z0, z1, radius, paint, sides=20, foot=True, base_plate=None, bolts=True ):
    """ A slender steel column (a canopy's or a footbridge's): a lathe shaft with a foot collar and a cap ring, on a base
    plate ( half-width, thickness ) with four anchor bolts. """
    if base_plate:
        h, t = base_plate
        P.chamfer_box( model, ( e - h, n - h, z0 ), ( e + h, n + h, z0 + t ), paint, chamfer=0.4, skip=( "-z", ) )
        if bolts:
            for de in ( -h + 2.2, h - 2.2 ):
                for dn in ( -h + 2.2, h - 2.2 ):
                    P.bolt( model, ( e + de, n + dn, z0 + t ), ( 0, 0, 1 ), radius=0.55, length=0.45, paint=IRON_DARK )
                    model.cylinder( ( e + de, n + dn ), 0.3, z0 + t + 0.4, z0 + t + 1.4, IRON_DARK, sides=6 )
        z0 += t
    prof = []
    if foot:
        prof += [ ( radius + 1.2, z0 ), ( radius + 1.2, z0 + 3.0 ), ( radius + 0.5, z0 + 4.0 ), ( radius, z0 + 5.0 ) ]
    else:
        prof += [ ( radius, z0 ) ]
    prof += [ ( radius, z1 - 5.0 ), ( radius + 0.6, z1 - 4.0 ), ( radius + 0.6, z1 - 2.0 ), ( radius + 1.2, z1 - 1.0 ),
              ( radius + 1.2, z1 ) ]
    P.lathe( model, ( e, n ), prof, paint, sides=sides, smooth=40.0 )


def downpipe( model, e, n, z_top, z_foot, radius=2.0, paint=GREY, shoe=( 1, 0 ), clamps=60.0, wall=None ):
    """ A round rainwater pipe from z_top down to a shoe at z_foot that turns out along shoe ( plan direction ), with
    clamps every clamps inches (to wall: ( de, dn ) towards the support it's fixed to). """
    s = np.asarray( shoe, float )
    s = s / max( np.linalg.norm( s ), 1e-9 )
    bend = z_foot + 6.0
    pts = [ ( e, n, z_top ), ( e, n, bend + 2.0 ), ( e + s[0] * 2.5, n + s[1] * 2.5, z_foot + 3.0 ),
            ( e + s[0] * 6.0, n + s[1] * 6.0, z_foot + 2.2 ) ]
    P.tube_path( model, pts, radius, paint, sides=12 )
    # Sockets every 2 m, and clamps.
    z = z_top - 8.0
    while z > bend + 10:
        P.lathe( model, ( e, n ), [ ( radius + 0.35, z ), ( radius + 0.35, z + 2.5 ) ], paint, sides=12, caps=( True, True ) )
        if wall is not None:
            w = np.asarray( wall, float )
            a = np.array( ( e, n, z + 0.5 ) )
            b = a + np.array( ( w[0], w[1], 0.0 ) )
            model.beam( a, b, ( 1.2, 0.4 ), IRON_DARK )
        z -= clamps


def run_breaks( r0, r1, gaps, min_len=2.0 ):
    """ The pieces of r0..r1 outside the ( a, b ) gaps. """
    out, at = [], r0
    for a, b in sorted( gaps ):
        if b <= at or a >= r1:
            continue
        if a - at >= min_len:
            out.append( ( at, a ) )
        at = max( at, b )
    if r1 - at >= min_len:
        out.append( ( at, r1 ) )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The shed's middle columns and valley girder (centre)

SHED_COLUMN_R = 8.5                 # 430 mm shaft
CAPITAL_TOP = 300.0                 # the abacus's top, under the girder's bearing plate
GIRDER_Z = ( 304.0, 334.0 )


def shed_column( model, n ):
    """ A cast-iron shed column at ( 0, n ): plinth, moulded base (torus, scotia, fillet), a shaft with a slight entasis,
    a cast band for the sign brackets, then a neck ring, echinus and abacus directly under the valley girder's bearing
    plate, and two curved spandrel brackets springing from the shaft along the girder. """
    # A 760 mm plinth and a 710 mm pedestal: no more than an inch proud of the column's 28 in collision box, so a player
    # brushing past doesn't stand in the casting.
    P.chamfer_box( model, ( -15, n - 15, 0 ), ( 15, n + 15, 6 ), IRON, chamfer=1.2, skip=( "-z", ) )
    P.chamfer_box( model, ( -14.0, n - 14.0, 6 ), ( 14.0, n + 14.0, 11 ), IRON, chamfer=0.8, skip=( "-z", ) )
    r = SHED_COLUMN_R
    base = P.join( [ ( 13.0, 11.0 ) ], P.torus_profile( 13.0, 11.0, 14.5, 1.0, steps=6 ),
                   [ ( 12.0, 14.5 ) ], P.quarter( 12.0, 14.5, 10.4, 17.5, steps=4, convex=False ),
                   [ ( 10.4, 18.5 ), ( 9.6, 18.5 ), ( 9.6, 19.5 ) ], P.quarter( 9.6, 19.5, r, 21.0, steps=3, convex=False ) )
    # The shaft runs up to a capital directly under the girder, as on Frankfurt's and Dresden's shed columns: a long
    # stool between a low capital and the girder read as a second, thinner column standing on the first.
    shaft = [ ( r, 21.0 ), ( r - 0.15, 80.0 ), ( r - 0.35, 150.0 ), ( r - 0.5, 225.0 ) ]
    # A cast band at 226..238, where the sign and lamp brackets clamp on (and where the old capital's collision is).
    band = P.join( [ ( r - 0.5, 225.5 ), ( r + 0.7, 226.5 ) ], P.torus_profile( r + 0.7, 226.5, 229.0, 0.9, steps=4 ),
                   [ ( r + 1.3, 229.5 ), ( r + 1.3, 234.5 ) ], P.torus_profile( r + 0.7, 235.0, 237.5, 0.9, steps=4 ),
                   [ ( r - 0.55, 238.5 ) ] )
    upper = [ ( r - 0.6, 239.0 ), ( r - 0.75, 263.0 ) ]
    neck = P.join( [ ( r - 0.75, 263.5 ), ( r + 0.5, 264.5 ) ], P.torus_profile( r + 0.5, 264.5, 267.0, 0.9, steps=4 ),
                   [ ( r - 0.5, 268.0 ), ( r - 0.5, 272.0 ) ], [ ( r + 0.1, 272.5 ), ( r + 0.1, 273.5 ) ],
                   P.quarter( r - 0.3, 274.0, 13.0, 286.0, steps=6, convex=True ), [ ( 13.0, 286.5 ) ] )
    P.lathe( model, ( 0, n ), P.join( base, shaft, band, upper, neck ), IRON, sides=24, smooth=40.0, caps=( False, True ) )
    # Abacus, a moulded square block in two tiers, then the girder's bearing plate.
    P.chamfer_box( model, ( -15.5, n - 15.5, 286.5 ), ( 15.5, n + 15.5, 291.0 ), IRON, chamfer=0.6 )
    P.chamfer_box( model, ( -14.0, n - 14.0, 291.0 ), ( 14.0, n + 14.0, CAPITAL_TOP ), IRON, chamfer=0.5 )
    P.chamfer_box( model, ( -12.5, n - 16.0, CAPITAL_TOP ), ( 12.5, n + 16.0, GIRDER_Z[0] - 0.3 ), IRON, chamfer=0.3 )
    # The bearing plate's bolts up into the girder's flange, their heads under the plate where it overhangs the abacus.
    for dn in ( -15.2, 15.2 ):
        for de in ( -9.5, 9.5 ):
            P.bolt( model, ( de, n + dn, CAPITAL_TOP ), ( 0, 0, -1 ), radius=0.5, length=0.35, paint=IRON_DARK, washer=False )
    # Curved cast spandrel brackets springing from the shaft below the neck, passing outside the capital, out along
    # the girder's underside.
    for s in ( -1, 1 ):
        spandrel( model, 0.0, n, "n", s, 238.0, GIRDER_Z[0] - 0.3, 44.0, 4.0, IRON, face_r=r - 0.6, segs=10 )
    # The valley gutter drains down the hollow shaft to a cast outlet shoe on the pedestal, spilling into a floor gully.
    P.chamfer_box( model, ( -2.6, n - 15.6, 6.0 ), ( 2.6, n - 9.2, 9.4 ), IRON, chamfer=0.5, skip=( "-z", ) )
    model.box( ( -2.0, n - 16.6, 5.6 ), ( 2.0, n - 15.6, 9.0 ), IRON )
    P.chamfer_box( model, ( -5.0, n - 25.0, 0.0 ), ( 5.0, n - 17.0, 0.35 ), IRON_DARK, chamfer=0.2, skip=( "-z", ) )
    for k in range( 5 ):
        model.box( ( -4.2, n - 24.2 + k * 1.5, 0.35 ), ( 4.2, n - 23.6 + k * 1.5, 0.45 ), "rw_black" )


def valley_girder( model, n0, n1, columns, bridge=( -400.0, 880.0 ) ):
    """ The riveted plate girder the spans spring from: flange angles top and bottom on both faces, T stiffeners every
    60 (clear of the column stools), rivet rows along the web, and denser rows along the flanges near the footbridge. """
    z0, z1 = GIRDER_Z
    for s in ( -1, 1 ):
        lo, hi = sorted( ( s * 14.0, s * 16.6 ) )
        model.box( ( lo, n0, z0 - 0.4 ), ( hi, n1, z0 + 1.8 ), IRON )
        model.box( ( lo, n0, z1 - 1.8 ), ( hi, n1, z1 + 0.3 ), IRON )
        # The angles' upright legs on the web.
        lo2, hi2 = sorted( ( s * 14.0, s * 14.7 ) )
        model.box( ( lo2, n0, z0 + 1.8 ), ( hi2, n1, z0 + 5.5 ), IRON )
        model.box( ( lo2, n0, z1 - 5.5 ), ( hi2, n1, z1 - 1.8 ), IRON )
    n = n0 + 30.0
    while n < n1 - 10:
        if all( abs( n - c ) > 20 for c in columns ):
            for s in ( -1, 1 ):
                lo, hi = sorted( ( s * 14.0, s * 15.0 ) )
                model.box( ( lo, n - 1.5, z0 + 1.8 ), ( hi, n + 1.5, z1 - 1.8 ), IRON )
                lo, hi = sorted( ( s * 14.0, s * 17.2 ) )
                model.box( ( lo, n - 0.5, z0 + 1.8 ), ( hi, n + 0.5, z1 - 1.8 ), IRON )
        n += 60.0
    for s in ( -1, 1 ):
        n = n0 + 4.0
        while n < n1 - 2:
            # Rivets only where anyone is near enough to see them: from the footbridge to the concourse (7.7 m up
            # elsewhere, a row of 0.8 in heads is under a pixel at any distance a player stands from it).
            if not bridge[0] < n < bridge[1]:
                n += 8.0
                continue
            for z in ( z0 + 3.6, z1 - 3.6 ):
                P.rivet( model, ( s * 14.7, n, z ), ( s, 0, 0 ), radius=0.42, height=0.32, paint=IRON )
            if True:
                for z in ( z0 - 0.4, z1 + 0.3 ):
                    P.rivet( model, ( s * 15.3, n, z ), ( 0, 0, -1 if z < z1 else 1 ), radius=0.38, height=0.28, paint=IRON )
            n += 8.0


# ---------------------------------------------------------------------------------------------------------------------
# Platform canopies

CANOPY_BEAMS_N = ( -1696.0, -1620.0, -1520.0, -1420.0, -1344.0 )
SPINE_D = 14.0


def canopy_spine( model, col, z, n0, n1 ):
    """ A platform canopy's spine: an I-beam along the column line under the sheeting (z its underside). """
    model.box( ( col - 5, n0, z - 1.0 ), ( col + 5, n1, z - 0.02 ), IRON_DARK )
    model.box( ( col - 0.6, n0, z - SPINE_D + 1 ), ( col + 0.6, n1, z - 1.0 ), IRON_DARK )
    model.box( ( col - 5, n0, z - SPINE_D ), ( col + 5, n1, z - SPINE_D + 1 ), IRON_DARK )


def canopy_column( model, col, cn, z, sides=( -1, 1 ) ):
    """ A canopy column on the spine: a round steel column on a bolted base plate, a cap plate, cast spandrel brackets
    under the cantilevers, and a downpipe from the spine's box gutter. """
    round_column( model, col, cn, 0.0, z - SPINE_D, 5.5, IRON_DARK, sides=20, base_plate=( 10.0, 1.0 ), foot=False )
    # A two-step cast base ring (14 and 12 in) on the plate.
    ring = P.join( [ ( 7.0, 1.0 ) ], P.torus_profile( 7.0, 1.0, 3.6, 0.6, steps=4 ), [ ( 6.0, 3.8 ) ],
                   P.torus_profile( 6.0, 3.8, 5.8, 0.5, steps=4 ), [ ( 5.5, 6.2 ) ] )
    P.lathe( model, ( col, cn ), ring, IRON_DARK, sides=20, smooth=40.0, caps=( False, False ) )
    P.chamfer_box( model, ( col - 7, cn - 7, z - SPINE_D - 1.2 ), ( col + 7, cn + 7, z - SPINE_D ), IRON_DARK, chamfer=0.3 )
    for s in sides:
        spandrel( model, col, cn, "e", s, z - SPINE_D - 40.0, z - SPINE_D - 0.6, 40.0, 3.0, IRON_DARK, face_r=5.5, segs=7 )
    pe, pn = col + 8.0, cn + 6.5
    downpipe( model, pe, pn, z - 0.5, 0.0, radius=2.0, paint=GREY, shoe=( 1, 0 ), wall=( -2.8, -2.3 ) )


def canopy_roof( model, e0, e1, col, z, n0, n1, eaves ):
    """ A canopy's cantilevers (I-sections tapering from SPINE_D deep at the spine to 6 at the eaves), purlins every 40,
    fascias with drips along the eaves and the south end, and the eave gutters behind them. """
    for nb in CANOPY_BEAMS_N:
        if not n0 - 1 <= nb <= n1 + 1:
            continue
        for eave in eaves:
            s = 1.0 if eave > col else -1.0
            r_tip = eave - s * 2.0
            lo, hi = sorted( ( col, r_tip ) )
            model.box( ( lo, nb - 3, z - 1.0 ), ( hi, nb + 3, z - 0.03 ), IRON_DARK )
            for d in ( -0.5, 0.5 ):
                pts = [ ( col, nb + d, z - 1.0 ), ( r_tip, nb + d, z - 1.0 ), ( r_tip, nb + d, z - 6.0 ),
                        ( col, nb + d, z - SPINE_D ) ]
                P._poly( model, IRON_DARK, pts, ( 0, d, 0 ) )
            model.beam( ( col, nb, z - SPINE_D + 0.5 ), ( r_tip, nb, z - 5.5 ), ( 6.0, 1.0 ), IRON_DARK )
            lo, hi = sorted( ( r_tip, r_tip - s * 0.6 ) )
            model.box( ( lo, nb - 3.2, z - 6.5 ), ( hi, nb + 3.2, z ), IRON_DARK )
    for eave in eaves:
        s = 1.0 if eave > col else -1.0
        r = col + s * 26.0
        while ( r < eave - 8 ) if s > 0 else ( r > eave + 8 ):
            model.box( ( r - 1.5, n0, z - 4.0 ), ( r + 1.5, n1, z - 0.04 ), IRON_DARK )
            r += s * 40.0
        # The fascia along the eave with a drip, and the eave gutter behind its top.
        # It starts at n0, butting the south end's fascia, which wraps the corner (no coplanar faces there).
        lo, hi = sorted( ( eave, eave + s * 2.0 ) )
        model.box( ( lo, n0, z - 8.0 ), ( hi, n1, z + 10.0 ), { "default": IRON_DARK, "+n": None, "-n": None } )
        lo, hi = sorted( ( eave + s * 2.0, eave + s * 3.5 ) )
        model.box( ( lo, n0, z - 8.5 ), ( hi, n1, z - 6.6 ), { "default": IRON_DARK, "-n": None } )
        lo, hi = sorted( ( eave - s * 6.0, eave ) )
        model.box( ( lo, n0, z + 6.0 ), ( hi, n1, z + 10.0 ), { "default": GREY, "+z": None } )
        # A half-round gutter on brackets along the fascia's top, outside it.
        D.half_round_gutter( model, eave + s * 2.0, s, n0, n1, z + 10.0, radius=2.4, paint=GREY )
    # The south end's fascia.
    centre = len( eaves ) == 1
    lo_e = col if centre and col < min( eaves ) else min( e0, e1 ) - 2.8
    hi_e = max( e0, e1 ) + 2.8
    model.box( ( lo_e, n0 - 2.0, z - 8.0 ), ( hi_e, n0, z + 10.0 ), { "default": IRON_DARK, "-e": None if centre else IRON_DARK } )
    model.box( ( lo_e, n0 - 3.5, z - 8.5 ), ( hi_e, n0 - 2.0, z - 6.6 ), { "default": IRON_DARK, "-e": None if centre else IRON_DARK } )


# ---------------------------------------------------------------------------------------------------------------------
# The booking hall: walls, gallery, vault (centre)

HALL_E, HALL_N0, HALL_N1, GALLERY_N0, GALLERY_Z = 600.0, 1340.0, 1780.0, 1660.0, 200.0
ENTABLATURE_Z = 500.0
# ( u proud, v up from ENTABLATURE_Z ): architrave in two fasciae, a frieze, a bed mould, the dentil course (its blocks
# are separate), the corona with its drip and a cyma on top.
ENTABLATURE = [ ( 0.0, 0.0 ), ( 3.0, 0.0 ), ( 3.0, 4.5 ), ( 4.0, 5.0 ), ( 4.0, 9.0 ), ( 4.8, 9.6 ), ( 4.8, 10.8 ),
                ( 3.4, 11.4 ), ( 3.4, 23.0 ) ] + P.ogee( 3.4, 23.0, 6.5, 26.5, steps=4 )[1:] + \
               [ ( 6.5, 30.5 ), ( 13.0, 30.5 ), ( 14.0, 31.0 ), ( 14.0, 35.0 ) ] + P.ogee( 14.0, 35.0, 17.5, 39.0, steps=5 )[1:] + \
               [ ( 17.5, 40.0 ), ( 0.0, 40.0 ) ]
DADO_TOP = 44.0
DADO_CAP = [ ( 0.0, 0.0 ), ( 1.2, 0.0 ), ( 1.2, 0.6 ) ] + P.quarter( 1.2, 0.6, 2.6, 2.4, steps=3, convex=True )[1:] + \
           [ ( 2.6, 3.0 ), ( 1.4, 3.6 ), ( 0.0, 3.6 ) ]
SKIRTING = [ ( 0.0, 0.0 ), ( 1.6, 0.0 ), ( 1.6, 5.0 ), ( 1.0, 6.0 ), ( 0.0, 6.4 ) ]
DADO_FACE = [ ( 0.0, 0.0 ), ( 0.8, 0.0 ), ( 0.8, DADO_TOP ), ( 0.0, DADO_TOP ) ]
STRING = [ ( 0.0, 0.0 ), ( 2.4, 0.0 ), ( 3.6, 1.2 ), ( 3.6, 4.0 ), ( 2.8, 5.0 ), ( 2.8, 5.6 ), ( 0.0, 6.4 ) ]


def wall_mouldings( model, axis, at, out, r0, r1, gaps_dado=(), gaps_string=(), gaps_ent=(), string=True,
                    dado=True, entablature=True, string_z=GALLERY_Z ):
    """ The hall's standard mouldings on one wall face: skirting, a stone dado face with its cap, the string course at
    gallery level and the entablature the vault springs from, each broken at its gaps. """
    if dado:
        for a, b in run_breaks( r0, r1, gaps_dado ):
            P.straight( model, axis, at, a, b, 0.0, out, DADO_FACE, STONE )
            P.straight( model, axis, at + out * 0.8, a, b, 0.0, out, SKIRTING, STONE )
            P.straight( model, axis, at + out * 0.8, a, b, DADO_TOP - 1.2, out, DADO_CAP, STONE )
    if string:
        for a, b in run_breaks( r0, r1, gaps_string ):
            P.straight( model, axis, at, a, b, string_z, out, STRING, STONE )
    if entablature:
        for a, b in run_breaks( r0, r1, gaps_ent ):
            P.straight( model, axis, at, a, b, ENTABLATURE_Z, out, ENTABLATURE, STONE )
            # The dentils under the corona.
            r = a + 4.0
            while r < b - 4.0:
                lo = ( r - 1.6, at, ENTABLATURE_Z + 26.5 ) if axis == "e" else ( at, r - 1.6, ENTABLATURE_Z + 26.5 )
                hi = ( r + 1.6, at + out * 9.8, ENTABLATURE_Z + 30.5 ) if axis == "e" else ( at + out * 9.8, r + 1.6, ENTABLATURE_Z + 30.5 )
                model.box( np.minimum( lo, hi ), np.maximum( lo, hi ), STONE )
                r += 6.0


def pilaster( model, axis, at, out, r, z0, z1, width=28.0, proud=6.0, capital=True ):
    """ A dressed-stone pilaster on a wall face at r: a moulded base, a fluted-looking shaft with a sunk panel and a
    capital block under the entablature. """
    def box( r_lo, r_hi, d0, d1, za, zb, paint=STONE, chamfer=0.6 ):
        if axis == "e":
            lo, hi = ( r_lo, at + out * d0, za ), ( r_hi, at + out * d1, zb )
        else:
            lo, hi = ( at + out * d0, r_lo, za ), ( at + out * d1, r_hi, zb )
        P.chamfer_box( model, np.minimum( lo, hi ), np.maximum( lo, hi ), paint, chamfer=chamfer, skip=( "-z", ) )
    h = width / 2
    box( r - h - 2, r + h + 2, 0, proud + 2, z0, z0 + 10 )
    box( r - h - 1, r + h + 1, 0, proud + 1, z0 + 10, z0 + 13, chamfer=0.8 )
    box( r - h, r + h, 0, proud, z0 + 13, z1 - 14, chamfer=0.8 )
    # A sunk panel's border on the shaft.
    for a, b in ( ( r - h + 4, r - h + 5.2 ), ( r + h - 5.2, r + h - 4 ) ):
        box( a, b, proud, proud + 0.7, z0 + 22, z1 - 26, chamfer=0.2 )
    box( r - h + 4, r + h - 4, proud, proud + 0.7, z0 + 20.8, z0 + 22, chamfer=0.2 )
    box( r - h + 4, r + h - 4, proud, proud + 0.7, z1 - 26, z1 - 24.8, chamfer=0.2 )
    if capital:
        box( r - h - 1, r + h + 1, 0, proud + 1, z1 - 14, z1 - 11, chamfer=0.4 )
        box( r - h + 0.5, r + h - 0.5, 0, proud + 0.2, z1 - 11, z1 - 4, chamfer=0.4 )
        box( r - h - 3, r + h + 3, 0, proud + 3, z1 - 4, z1, chamfer=0.6 )


def arch_trim( model, axis, at, out, centre, spring, radius, impost_w=14.0, key=( 14.0, 24.0 ), band=10.0,
               paint=STONE, proud=4.5, steps=24, impost=True, keystone=True ):
    """ An arch's trim on a wall face: an archivolt band round the intrados, impost blocks at the springing and a
    keystone at the crown. """
    prof = [ ( 0.0, 0.0 ), ( 1.5, 0.0 ), ( 1.5, 1.0 ), ( proud - 1.0, 2.0 ), ( proud - 1.0, band * 0.55 ),
             ( proud - 2.0, band * 0.6 ), ( proud - 2.0, band * 0.8 ), ( proud, band * 0.9 ), ( proud, band ), ( 0.0, band ) ]
    P.arch_band( model, axis, at, out, centre, spring, radius, prof, paint, steps=steps )

    def box( r0, r1, d0, d1, z0, z1, chamfer=0.6 ):
        if axis == "e":
            lo, hi = ( r0, at + out * d0, z0 ), ( r1, at + out * d1, z1 )
        else:
            lo, hi = ( at + out * d0, r0, z0 ), ( at + out * d1, r1, z1 )
        P.chamfer_box( model, np.minimum( lo, hi ), np.maximum( lo, hi ), paint, chamfer=chamfer, skip=( "-z", ) )
    if impost:
        for s in ( -1, 1 ):
            edge = centre + s * radius
            a, b = sorted( ( edge, edge + s * impost_w ) )
            box( a - ( 0 if s > 0 else 0 ), b, 0, proud + 3.0, spring - 8.0, spring - 2.0 )
            box( a, b, 0, proud + 1.5, spring - 2.0, spring, chamfer=0.4 )
    if keystone:
        kw, kh = key
        crown = spring + radius
        # A tapered keystone: wider at the top.
        for d in ( 0.0, ):
            pts_front = [ ( centre - kw * 0.38, crown - 3.0 ), ( centre + kw * 0.38, crown - 3.0 ), ( centre + kw / 2, crown + kh - 3 ),
                          ( centre - kw / 2, crown + kh - 3 ) ]
            outline = [ ( r, z ) for r, z in pts_front ]
        def p3( r, z, d ):
            return np.array( ( r, at + out * d, z ) if axis == "e" else ( at + out * d, r, z ), float )
        front = [ p3( r, z, proud + 1.2 ) for r, z in outline ]
        back = [ p3( r, z, 0.0 ) for r, z in outline ]
        normal = np.array( ( 0, out, 0 ) if axis == "e" else ( out, 0, 0 ), float )
        P._poly( model, paint, front, normal )
        c = np.mean( front, axis=0 )
        for k in range( 4 ):
            j = ( k + 1 ) % 4
            q = [ back[k], back[j], front[j], front[k] ]
            P._poly( model, paint, q, np.mean( q, axis=0 ) - c + normal * 0.0 - ( np.mean( q, axis=0 ) - c ) * 0 )


def hall( model ):
    """ The hall's walls inside (all four, drawn whole here): pilasters, the entablature, a stone dado, the string
    course, and the trims of the south wall's three arches from the concourse. """
    # South wall (inside face n 1340, facing +n): arches at 0 ( 200 wide, crown 320 ) and +-320 ( 160, crown 300 ).
    s_doors = [ ( -100.0, 100.0 ), ( -400.0, -240.0 ), ( 240.0, 400.0 ) ]
    gaps = [ ( a - 1, b + 1 ) for a, b in s_doors ]
    stair = [ ( -600.0, -474.0 ), ( 474.0, 600.0 ) ]            # the gallery stairs' first flights hide the dado
    wall_mouldings( model, "e", HALL_N0, 1.0, -HALL_E, HALL_E, gaps_dado=gaps + stair, gaps_string=gaps )
    for c in ( -170.0, 170.0, -500.0, 500.0 ):
        pilaster( model, "e", HALL_N0, 1.0, c, 0.0 if abs( c ) < 450 else 40.0, ENTABLATURE_Z, proud=8.0 )
    for c, width, crown in ( ( 0.0, 200.0, 320.0 ), ( -320.0, 160.0, 300.0 ), ( 320.0, 160.0, 300.0 ) ):
        arch_trim( model, "e", HALL_N0, 1.0, c, crown - width / 2, width / 2, key=( 16.0, 26.0 ), band=10.0, proud=5.0 )
    # North wall (inside face n 1780, facing -n): doors under the gallery, windows over it.
    n_doors = [ ( -70.0, 70.0 ), ( -380.0, -260.0 ), ( 260.0, 380.0 ) ]
    gaps = [ ( a - 15, b + 15 ) for a, b in n_doors ]
    wall_mouldings( model, "e", HALL_N1, -1.0, -HALL_E, HALL_E, gaps_dado=gaps, gaps_string=[], string=False )
    P.straight( model, "e", HALL_N1, -HALL_E, HALL_E, GALLERY_Z, -1.0, SKIRTING, STONE )
    for c in ( -170.0, 170.0, -490.0, 490.0 ):
        pilaster( model, "e", HALL_N1, -1.0, c, GALLERY_Z, ENTABLATURE_Z, proud=6.0 )
    # The tall windows over the gallery: archivolts with imposts and keystones, and moulded sills.
    for c, width, z0, z1 in ( ( 0.0, 200.0, 230.0, 450.0 ), ( -320.0, 140.0, 240.0, 430.0 ), ( 320.0, 140.0, 240.0, 430.0 ) ):
        arch_trim( model, "e", HALL_N1, -1.0, c, z1 - width / 2, width / 2, key=( 16.0, 24.0 ), band=10.0, proud=4.5,
                   impost_w=12.0 )
        sill = [ ( 0.0, -5.0 ), ( 3.0, -5.0 ), ( 3.0, -4.0 ), ( 4.2, -4.0 ), ( 4.2, -1.2 ), ( 0.0, 0.0 ) ]
        P.straight( model, "e", HALL_N1, c - width / 2 - 8.0, c + width / 2 + 8.0, z0, -1.0, sill, STONE )
    # Side walls (inside faces e +-600): windows at 1420, 1560, 1700 (460..532) break the entablature; the wing's arch
    # at 1720 (0..180) is under the gallery.
    for s in ( -1.0, 1.0 ):
        at = s * HALL_E
        win = [ ( n - 43, n + 43 ) for n in ( 1420.0, 1560.0, 1700.0 ) ]
        wall_mouldings( model, "n", at, -s, HALL_N0, HALL_N1, gaps_dado=[ ( 1340.0, 1675.0 ), ( 1673.0, 1767.0 ) ],
                        gaps_string=[ ( GALLERY_N0 - 2, HALL_N1 + 1 ) ], gaps_ent=win )
        for r in ( 1490.0, 1630.0 ):
            pilaster( model, "n", at, -s, r, 30.0, ENTABLATURE_Z, proud=5.0 )
        for r in ( HALL_N0 + 15.0, HALL_N1 - 15.0 ):
            pilaster( model, "n", at, -s, r, GALLERY_Z if r > GALLERY_N0 else 40.0, ENTABLATURE_Z, width=26.0, proud=4.0 )
        # The windows' surrounds, with the entablature's top course carried round as a hood.
        for n in ( 1420.0, 1560.0, 1700.0 ):
            prof = [ ( 0.0, 0.0 ), ( 1.0, 0.0 ), ( 2.5, 1.2 ), ( 2.5, 4.0 ), ( 3.5, 5.0 ), ( 3.5, 6.0 ), ( 0.0, 6.0 ) ]
            P.arch_band( model, "n", at, -s, n, 497.0, 35.0, prof, STONE, steps=24 )
            for side in ( -1, 1 ):
                a, b = sorted( ( n + side * 35.0, n + side * 41.0 ) )
                lo, hi = ( at - s * 3.5, a, 452.0 ), ( at, b, 497.0 )
                P.chamfer_box( model, np.minimum( lo, hi ), np.maximum( lo, hi ), STONE, chamfer=0.5, skip=( "-z", ) )
            lo, hi = ( at - s * 5.0, n - 43.0, 452.0 ), ( at, n + 43.0, 460.0 )
            P.chamfer_box( model, np.minimum( lo, hi ), np.maximum( lo, hi ), STONE, chamfer=0.8, skip=( "-z", ) )
        # The wing's arch, under the gallery.
        arch_trim( model, "n", at, -s, 1720.0, 135.0, 45.0, key=( 12.0, 12.0 ), band=8.0, proud=4.0, impost_w=10.0 )


# The head building's south front, on the concourse (facing -n): pilasters with bases and capitals, archivolts and
# keystones on its doors and windows, and a moulded cornice with dentils. Profile ( proud, up from 340 ).
SOUTH_CORNICE = [ ( 0.0, 0.0 ), ( 9.0, 0.0 ), ( 9.0, 2.5 ), ( 10.2, 3.5 ), ( 10.2, 8.0 ) ] +                 P.ogee( 10.2, 8.0, 13.0, 12.5, steps=4 )[1:] + [ ( 13.0, 13.0 ), ( 11.0, 13.6 ), ( 11.0, 17.0 ),
                ( 16.0, 18.0 ), ( 16.0, 22.5 ), ( 17.0, 23.2 ), ( 17.0, 26.0 ), ( 0.0, 26.0 ) ]


def south_front( model, n_out, pilasters, doors, wing_doors, wing_windows, wing_door_crown, wing_window_crown, e_max ):
    """ The south front's dressings on its outer face at n_out (facing -n). pilasters: ( centre, half-width ). """
    for c, half in pilasters:
        pilaster( model, "e", n_out, -1.0, c, 30.0, 340.0, width=2 * half, proud=8.0 )
    for c, width, crown in doors:
        arch_trim( model, "e", n_out, -1.0, c, crown - width / 2, width / 2, key=( 20.0, 30.0 ), band=11.0, proud=5.5,
                   impost_w=16.0 )
    for c in wing_doors:
        arch_trim( model, "e", n_out, -1.0, c, wing_door_crown - 60.0, 60.0, key=( 14.0, 22.0 ), band=9.0, proud=4.5,
                   impost_w=14.0 )
    for c in wing_windows:
        arch_trim( model, "e", n_out, -1.0, c, wing_window_crown - 45.0, 45.0, key=( 12.0, 20.0 ), band=8.0, proud=4.0,
                   impost_w=10.0 )
    P.straight( model, "e", n_out, -e_max, e_max, 340.0, -1.0, SOUTH_CORNICE, STONE )
    e = -e_max + 4.0
    while e < e_max - 4.0:
        model.box( ( e - 1.7, n_out - 15.0, 354.5 ), ( e + 1.7, n_out - 10.0, 358.0 ), STONE )
        e += 6.5


def north_doors( model, glass_n, inner_n ):
    """ The street doors' frames (bronze-finished steel, in the glass's plane at glass_n), and dressed jambs and a hood
    on the hall's side (wall face inner_n, facing -n). """
    for c, width, top in ( ( 0.0, 140.0, 170.0 ), ( -320.0, 120.0, 160.0 ), ( 320.0, 120.0, 160.0 ) ):
        a, b = c - width / 2, c + width / 2
        transom = 92.0
        def frame( e0, e1, z0, z1, d=1.6 ):
            model.box( ( e0, glass_n - d, z0 ), ( e1, glass_n + d, z1 ), BRONZE )
        frame( a, a + 4, 0, top )
        frame( b - 4, b, 0, top )
        frame( a, b, top - 4, top )
        frame( a, b, transom - 2.5, transom + 2.5, d=2.0 )
        # Two leaves in the door's lower part, each with stiles, a kick plate and a push bar; mullions in the fanlight.
        mid = c
        frame( mid - 2.5, mid + 2.5, 0, transom )
        for l0, l1 in ( ( a + 4, mid - 2.5 ), ( mid + 2.5, b - 4 ) ):
            frame( l0, l0 + 3.5, 0, transom - 2.5, d=1.3 )
            frame( l1 - 3.5, l1, 0, transom - 2.5, d=1.3 )
            frame( l0, l1, 0, 12.0, d=1.3 )
            frame( l0, l1, 12.0, 13.5, d=1.4 )
            for s in ( -1.0, 1.0 ):
                y = glass_n + s * 4.0
                P.tube_path( model, [ ( l0 + 6, y, 40.0 ), ( l1 - 6, y, 40.0 ) ], 0.6, BRONZE, sides=10 )
                for e in ( l0 + 7, l1 - 7 ):
                    P.tube_path( model, [ ( e, glass_n + s * 1.3, 40.0 ), ( e, y, 40.0 ) ], 0.45, BRONZE, sides=6 )
        k = int( width // 35 )
        for j in range( 1, k ):
            e = a + 4 + ( width - 8 ) * j / k
            frame( e - 1.0, e + 1.0, transom + 2.5, top - 4, d=1.2 )
        model.box( ( a, glass_n - 3, 0 ), ( b, glass_n + 3, 0.6 ), GREY )
        # The hall side's dressed jambs and hood cornice.
        for s in ( -1, 1 ):
            e_in = c + s * width / 2
            lo, hi = sorted( ( e_in, e_in + s * 14.0 ) )
            P.chamfer_box( model, ( lo, inner_n - 10.0, 0.0 ), ( hi, inner_n, top + 2.0 ), STONE, chamfer=1.0, skip=( "-z", ) )
            P.chamfer_box( model, ( lo - 1, inner_n - 11.0, 0.0 ), ( hi + 1, inner_n, 8.0 ), STONE, chamfer=0.8, skip=( "-z", ) )
        hood = [ ( 0.0, 0.0 ), ( 10.5, 0.0 ), ( 11.5, 1.0 ), ( 11.5, 4.0 ) ] + P.ogee( 11.5, 4.0, 14.0, 8.0, steps=4 )[1:] + \
               [ ( 14.0, 10.0 ), ( 0.0, 10.0 ) ]
        P.straight( model, "e", inner_n, a - 18.0, b + 18.0, top + 2.0, -1.0, hood, STONE )


def gallery( model ):
    """ The gallery: moulded columns, a beam front in three steps with dentils, coffered soffit, and a balustrade of
    turned balusters between pedestals on a plinth under a coping. """
    n0, n1, z = GALLERY_N0, HALL_N1, GALLERY_Z
    # Columns at ( c, 1668 ): the collision is a 14-square base, a 10 shaft and a 16-square capital at 176..188.
    for c in ( -420.0, -180.0, 180.0, 420.0 ):
        n = n0 + 8.0
        P.chamfer_box( model, ( c - 15, n - 15, 0 ), ( c + 15, n + 15, 4 ), "rw_dressed_red", chamfer=0.8, skip=( "-z", ) )
        prof = P.join( P.torus_profile( 12.0, 4.0, 7.5, 1.2, steps=6 ), [ ( 11.6, 7.5 ) ],
                       P.quarter( 11.6, 7.5, 10.6, 9.5, steps=3, convex=False ), [ ( 10.6, 10.5 ), ( 10.0, 11.0 ) ],
                       [ ( 10.0, 60.0 ), ( 9.7, 120.0 ), ( 9.3, 168.0 ) ],
                       P.torus_profile( 9.3, 168.0, 170.5, 1.5, steps=4 ), [ ( 9.4, 171.5 ) ],
                       P.quarter( 9.4, 171.5, 13.0, 177.0, steps=4, convex=True ), [ ( 13.0, 177.5 ) ] )
        P.lathe( model, ( c, n ), prof, STONE, sides=24, smooth=40.0, caps=( False, True ) )
        P.chamfer_box( model, ( c - 15, n - 15, 177.5 ), ( c + 15, n + 15, 181.0 ), STONE, chamfer=0.6 )
        P.chamfer_box( model, ( c - 13, n - 13, 181.0 ), ( c + 13, n + 13, 182.0 ), STONE, chamfer=0.3 )
    # The front beam carried on the columns, then the coffers.
    model.box( ( -HALL_E, n0 - 1.0, 182.0 ), ( HALL_E, n0 + 17.0, 188.0 ), { "default": PLASTER, "-n": STONE, "+z": None } )
    for e in ( -510.0, -420.0, -300.0, -180.0, -60.0, 60.0, 180.0, 300.0, 420.0, 510.0 ):
        w = 7.0 if abs( e ) in ( 420.0, 180.0 ) else 5.0
        model.box( ( e - w, n0 + 17.0, 183.0 ), ( e + w, n1, 188.0 ), { "default": PLASTER, "+z": None } )
    for n in ( 1708.0, 1744.0 ):
        model.box( ( -HALL_E, n - 4.0, 183.0 ), ( HALL_E, n + 4.0, 188.0 ), { "default": PLASTER, "+z": None } )
    # The beam front's mouldings, facing -n: fascia, dentils, cyma, under the balustrade's plinth.
    front = [ ( 0.0, 0.0 ), ( 0.6, 0.0 ), ( 0.6, 5.0 ), ( 1.2, 5.6 ), ( 1.2, 6.4 ), ( 0.8, 6.8 ), ( 0.8, 13.0 ),
              ( 1.6, 13.0 ) ] + P.ogee( 1.6, 13.0, 4.5, 17.0, steps=4 )[1:] + [ ( 4.5, 18.0 ), ( 0.0, 18.0 ) ]
    P.straight( model, "e", n0 - 1.0, -HALL_E, HALL_E, 182.0, -1.0, front, STONE )
    e = -HALL_E + 4.0
    while e < HALL_E - 4.0:
        model.box( ( e - 1.4, n0 - 4.2, 190.0 ), ( e + 1.4, n0 - 1.6, 194.6 ), STONE )
        e += 5.5
    # The balustrade: plinth, pedestals, balusters, coping. Its collision is railhead_station's.
    b0, b1 = n0, n0 + 8.0
    e0, e1 = -HALL_E + 60.0, HALL_E - 60.0
    P.chamfer_box( model, ( e0, b0 - 1.0, z ), ( e1, b1 + 1.0, z + 3.5 ), STONE, chamfer=0.6, skip=( "-z", ) )
    P.chamfer_box( model, ( e0, b0 - 0.2, z + 3.5 ), ( e1, b1 + 0.2, z + 5.0 ), STONE, chamfer=0.5, skip=( "-z", ) )
    peds = [ e0 + 6.0 ] + [ -420.0, -300.0, -180.0, -60.0, 60.0, 180.0, 300.0, 420.0 ] + [ e1 - 6.0 ]
    for p in peds:
        P.chamfer_box( model, ( p - 6.0, b0 - 2.0, z ), ( p + 6.0, b1 + 2.0, z + 6.0 ), STONE, chamfer=0.8, skip=( "-z", ) )
        P.chamfer_box( model, ( p - 5.0, b0 - 1.0, z + 6.0 ), ( p + 5.0, b1 + 1.0, z + 40.0 ), STONE, chamfer=1.0, skip=( "-z", ) )
        P.chamfer_box( model, ( p - 6.5, b0 - 2.5, z + 40.0 ), ( p + 6.5, b1 + 2.5, z + 44.0 ), STONE, chamfer=0.8 )
        P.chamfer_box( model, ( p - 5.5, b0 - 1.5, z + 44.0 ), ( p + 5.5, b1 + 1.5, z + 48.0 ), STONE, chamfer=1.0 )
    bal = P.join( [ ( 1.9, z + 8.0 ), ( 1.6, z + 9.0 ), ( 1.6, z + 10.5 ) ], P.quarter( 1.6, z + 10.5, 3.3, z + 16.0, steps=4, convex=True ),
                  [ ( 3.3, z + 18.0 ) ], P.quarter( 3.3, z + 18.0, 1.8, z + 25.0, steps=4, convex=False ),
                  [ ( 1.8, z + 29.0 ), ( 2.3, z + 29.6 ), ( 2.3, z + 30.4 ), ( 1.9, z + 31.0 ) ] )
    gaps = [ ( p - 9.0, p + 9.0 ) for p in peds ]
    for a, b in run_breaks( e0, e1, gaps ):
        count = max( 1, int( round( ( b - a ) / 12.0 ) ) )
        for k in range( count ):
            e = a + ( b - a ) * ( k + 0.5 ) / count
            c = ( e, ( b0 + b1 ) / 2 )
            P.chamfer_box( model, ( e - 2.5, c[1] - 2.5, z + 5.0 ), ( e + 2.5, c[1] + 2.5, z + 8.0 ), STONE, chamfer=0.4, skip=( "-z", ) )
            P.lathe( model, c, bal, STONE, sides=12, smooth=50.0, caps=( False, False ) )
            P.chamfer_box( model, ( e - 2.5, c[1] - 2.5, z + 31.0 ), ( e + 2.5, c[1] + 2.5, z + 34.0 ), STONE, chamfer=0.3 )
        lo, hi = ( a - 3.0, b0 - 1.0, z + 34.0 ), ( b + 3.0, b1 + 1.0, z + 38.0 )
        P.chamfer_box( model, lo, hi, STONE, chamfer=0.6 )
        P.chamfer_box( model, ( a - 3.0, b0 - 0.2, z + 38.0 ), ( b + 3.0, b1 + 0.2, z + 42.0 ), STONE, chamfer=1.2 )


def vault( model, vault_z, vault_cz, ribs_n ):
    """ The vault's moulded ribs (two stacked courses), the panels' borders between them and a bead along the crown. """
    steps = 32
    es = [ -HALL_E + 2 * HALL_E * k / steps for k in range( steps + 1 ) ]

    def inward( e, depth ):
        z = vault_z( e )
        d = np.array( ( -e, vault_cz - z ) )
        d = d / np.linalg.norm( d )
        return np.array( ( e + d[0] * depth, z + d[1] * depth ) )

    for n in ribs_n:
        for a, b in zip( es, es[1:] ):
            for depth, width, thick in ( ( 3.0, 22.0, 6.0 ), ( 8.5, 15.0, 5.0 ), ( 11.6, 9.0, 1.4 ) ):
                pa, pb = inward( a, depth ), inward( b, depth )
                model.beam( ( pa[0], n, pa[1] ), ( pb[0], n, pb[1] ), ( width, thick ), STONE, up=( 0, 0, 1 ) )
    # Panel borders, 10 in from each rib and along the springing.
    borders = []
    for na, nb in zip( ribs_n, ribs_n[1:] ):
        borders += [ na + 21.0, nb - 21.0 ]
    for n in borders:
        for a, b in zip( es, es[1:] ):
            pa, pb = inward( a, 1.0 ), inward( b, 1.0 )
            if abs( a ) > HALL_E - 30 or abs( b ) > HALL_E - 30:
                continue
            model.beam( ( pa[0], n, pa[1] ), ( pb[0], n, pb[1] ), ( 3.0, 2.0 ), STONE, up=( 0, 0, 1 ) )
    for na, nb in zip( ribs_n, ribs_n[1:] ):
        for e in ( -HALL_E + 30.0, HALL_E - 30.0, 0.0 ):
            p = inward( e, 1.0 )
            r = 3.0 if e else 4.0
            model.beam( ( p[0], na + 19.5 if e else na + 11.0, p[1] ), ( p[0], nb - 19.5 if e else nb - 11.0, p[1] ),
                        ( r, 2.0 ), STONE, up=( 0, 0, 1 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The shed's outer wall (east): arcade mouldings, cornice, plinth, rib shoes

def arcade( model, wall_in, wall_out, arches, portals, windows, ribs, n0, n1 ):
    """ Both faces of the shed's outer wall: archivolts, imposts and keystones on every arch, a moulded plinth course, the
    inside cornice between the ribs, sills with drips under the high windows and bearing shoes on the rib corbels. """
    openings = [ ( n, 60.0, 150.0 ) for n in arches ] + [ ( n, 80.0, 180.0 ) for n in portals ]
    for at, out in ( ( wall_in, -1.0 ), ( wall_out, 1.0 ) ):
        for n, rad, spring in openings:
            arch_trim( model, "n", at, out, n, spring, rad, key=( 16.0, 26.0 ), band=11.0, proud=5.0, impost_w=16.0,
                       keystone=( out < 0 ) )
        # The plinth course with a weathered top.
        plinth = [ ( 0.0, 0.0 ), ( 4.2, 0.0 ), ( 4.2, 27.0 ), ( 3.4, 30.0 ), ( 2.2, 31.5 ), ( 2.2, 33.0 ), ( 0.0, 35.0 ) ]
        gaps = [ ( n - rad, n + rad ) for n, rad, _ in openings ]
        for a, b in run_breaks( n0, n1, gaps ):
            P.straight( model, "n", at, a, b, 0.0, out, plinth, "rw_dressed_red" )
        for n in windows:
            sill = [ ( 0.0, -2.0 ), ( 3.5, -2.0 ), ( 3.5, -1.0 ), ( 4.6, -1.0 ), ( 4.6, 0.0 ), ( 0.0, 3.0 ) ]
            P.straight( model, "n", at, n - 66, n + 66, 132.0, out, sill, STONE )
            # A drip groove under the sill's nose, and the dark run-off it leaves on the wall under each end.
            P.straight( model, "n", at, n - 64, n + 64, 129.4, out, [ ( 0.0, 0.0 ), ( 3.2, 0.0 ), ( 3.2, 0.5 ), ( 0.0, 0.5 ) ],
                        "rw_sandstone_soot" )
        # The impost band: the arches' springing carried across the piers between them as a moulded string, at eye
        # level the one line that ties the arcade together (broken at the openings and the windows' sills).
        band = [ ( 0.0, 0.0 ), ( 2.2, 0.0 ), ( 2.2, 0.8 ), ( 3.4, 1.8 ), ( 3.4, 5.2 ) ] + \
               P.ogee( 3.4, 5.2, 1.6, 8.0, steps=3 )[1:] + [ ( 0.0, 8.0 ) ]
        gaps = [ ( n - rad, n + rad ) for n, rad, _ in openings ] + [ ( r - 16.0, r + 16.0 ) for r in ribs ] +                [ ( n - 70.0, n + 70.0 ) for n in windows ]
        rng = random.Random( int( at * 7 + out ) )
        for a, b in run_breaks( n0, n1, gaps, min_len=6.0 ):
            P.straight( model, "n", at, a, b, 142.0, out, band, STONE )
            # Rain and soot run-off under the band's drip, ragged, darkest where it drips longest.
            D.runoff( model, "n", at, out, a + 1.0, b - 1.0, 142.0, rng, density=0.18, short=( 2.0, 7.0 ),
                      long=( 8.0, 22.0 ), long_share=0.18 )
    # The inside cornice in two courses under the roof, broken at the ribs (they bear on corbels there).
    cornice = [ ( 0.0, 0.0 ), ( 2.0, 0.0 ), ( 2.0, 3.0 ) ] + P.ogee( 2.0, 3.0, 6.0, 8.0, steps=4 )[1:] + \
              [ ( 6.0, 12.0 ), ( 7.5, 12.5 ), ( 10.5, 13.0 ), ( 12.0, 14.0 ), ( 12.0, 20.0 ), ( 12.8, 21.0 ), ( 12.8, 24.0 ),
                ( 0.0, 24.0 ) ]
    gaps = [ ( r - 20.0, r + 20.0 ) for r in ribs ]
    rng = random.Random( 316 )
    for a, b in run_breaks( n0, n1, gaps ):
        P.straight( model, "n", wall_in, a, b, 316.0, -1.0, cornice, STONE )
        # The cornice sheds the roof's soot water down the wall under it: streaks of soot from its drip.
        D.runoff( model, "n", wall_in, -1.0, a + 1.0, b - 1.0, 316.0, rng, density=0.12, short=( 6.0, 20.0 ),
                  long=( 24.0, 70.0 ), long_share=0.3 )
    for r in ribs:
        if r < n0 or r >= n1:
            continue
        # The corbel's moulded underside and a cast bearing shoe with four bolts on top.
        P.chamfer_box( model, ( wall_in - 24.0, r - 8.0, 316.0 ), ( wall_in - 0.5, r + 8.0, 322.0 ), IRON, chamfer=0.5 )
        P.chamfer_box( model, ( wall_in - 20.0, r - 6.0, 322.0 ), ( wall_in - 2.0, r + 6.0, 324.0 ), IRON, chamfer=0.4 )
        for de in ( -20.5, -4.0 ):
            for dn in ( -6.5, 6.5 ):
                P.bolt( model, ( wall_in + de, r + dn, 322.0 ), ( 0, 0, 1 ), radius=0.6, length=0.5, paint=IRON_DARK )
        # Capital to the inside pilaster under the corbel.
        prof = [ ( 0.0, 0.0 ), ( 10.0, 0.0 ), ( 11.0, 1.0 ), ( 11.0, 4.0 ) ] + P.quarter( 11.0, 4.0, 22.0, 15.5, steps=5, convex=False )[1:] + \
               [ ( 22.0, 16.0 ), ( 0.0, 16.0 ) ]
        P.straight( model, "n", wall_in, r - 18.0, r + 18.0, 300.0, -1.0, prof, STONE )


# ---------------------------------------------------------------------------------------------------------------------
# The shed's ribs: real lattice bars

def lattice( model, n, thetas, arc_point, top_d, bottom_d, e_min, e_max, half=4.6, gussets=False ):
    """ Flat lattice bars in an X across every panel of a rib between its chords' mid-lines, on both faces. gussets: a
    riveted gusset plate on both faces at every node (the ribs near the players). """
    if gussets:
        for theta in thetas:
            t3 = np.array( ( -math.sin( theta ), 0.0, math.cos( theta ) ) )
            for depth in ( top_d, bottom_d ):
                pe, pz = arc_point( theta, depth )
                if not e_min <= pe <= e_max:
                    continue
                for s in ( -1.0, 1.0 ):
                    c = np.array( ( pe, n + s * 5.2, pz ) )
                    y = np.array( ( 0.0, 1.0, 0.0 ) )
                    model.oriented_box( c, ( t3, y, np.cross( t3, y ) ), ( 8.0, 0.4, 7.0 ), IRON )
                    for k in ( -2.4, 2.4 ):
                        P.rivet( model, c + t3 * k + y * s * 0.2, ( 0, s, 0 ), radius=0.42, height=0.3, paint=IRON )
    for k, ( ta, tb ) in enumerate( zip( thetas, thetas[1:] ) ):
        a_top, b_top = arc_point( ta, top_d ), arc_point( tb, top_d )
        a_bot, b_bot = arc_point( ta, bottom_d ), arc_point( tb, bottom_d )
        if min( a_top[0], b_top[0], a_bot[0], b_bot[0] ) < e_min or max( a_top[0], b_top[0], a_bot[0], b_bot[0] ) > e_max:
            continue
        for d in ( -half, half ):
            for p, q in ( ( a_bot, b_top ), ( a_top, b_bot ) ):
                model.beam( ( p[0], n + d, p[1] ), ( q[0], n + d, q[1] ), ( 2.6, 0.8 ), IRON, up=( 0, 1, 0 ) )
        # A radial batten at every second node.
        if k % 2 == 0:
            for d in ( -half, half ):
                model.beam( ( a_bot[0], n + d, a_bot[1] ), ( a_top[0], n + d, a_top[1] ), ( 3.2, 0.8 ), IRON, up=( 0, 1, 0 ) )


def gable_fascia( model, n, arc_point, theta0, theta1, depth0, depth1, finial=True ):
    """ The end rib's fascia board along the span's outside edge and a turned finial at its crown. """
    steps = 32
    pts = []
    for k in range( steps + 1 ):
        t = theta0 + ( theta1 - theta0 ) * k / steps
        a, b = arc_point( t, depth0 ), arc_point( t, depth1 )
        pts.append( ( a, b ) )
    for ( a0, b0 ), ( a1, b1 ) in zip( pts, pts[1:] ):
        quad = [ ( a0[0], n - 1.5, a0[1] ), ( a1[0], n - 1.5, a1[1] ), ( b1[0], n - 1.5, b1[1] ), ( b0[0], n - 1.5, b0[1] ) ]
        P._poly( model, IRON_DARK, quad, ( 0, -1, 0 ) )
        quad2 = [ ( b0[0], n - 1.5, b0[1] ), ( b1[0], n - 1.5, b1[1] ), ( b1[0], n + 0.2, b1[1] ), ( b0[0], n + 0.2, b0[1] ) ]
        mid = np.array( ( ( b0[0] + b1[0] ) / 2 - 600.0, 0.0, ( b0[1] + b1[1] ) / 2 - 28.5 ) )
        P._poly( model, IRON_DARK, quad2, -mid )
        quad3 = [ ( a0[0], n - 1.5, a0[1] ), ( a1[0], n - 1.5, a1[1] ), ( a1[0], n + 0.2, a1[1] ), ( a0[0], n + 0.2, a0[1] ) ]
        P._poly( model, IRON_DARK, quad3, mid )
    if finial:
        crown = arc_point( math.pi / 2, 0.0 )
        prof = [ ( 3.0, 0.0 ), ( 3.0, 3.0 ), ( 2.0, 4.0 ), ( 1.2, 5.0 ), ( 1.2, 8.0 ) ] + P.quarter( 1.2, 8.0, 3.2, 12.0, steps=3, convex=True )[1:] + \
               P.quarter( 3.2, 12.0, 0.6, 20.0, steps=4, convex=False )[1:] + [ ( 0.0, 24.0 ) ]
        z0 = crown[1] + 40.0 + 3.0
        P.lathe( model, ( crown[0], n - 1.0 ), [ ( r, z0 + z ) for r, z in prof ], IRON_DARK, sides=12, smooth=45.0 )


# ---------------------------------------------------------------------------------------------------------------------
# The footbridge (east half)

def footbridge( model, n0, n1, roof_z, deck_z, wall_in, columns, stairs, rail_z ):
    """ The footbridge's roof structure (I-beams on the mullion lines, two purlins), fascias and gutters along both
    eaves with downpipes at the columns, a round handrail on brackets, and stiffeners on the side panels' inner faces. """
    e = 31.5
    while e < wall_in - 1:
        # An I-beam (on the panels' stiffener lines) across under the roof: flanges and web.
        model.box( ( e - 3.0, n0 - 5.0, roof_z - 1.0 ), ( e + 3.0, n1 + 5.0, roof_z - 0.05 ), IRON_DARK )
        model.box( ( e - 0.5, n0 - 5.0, roof_z - 7.0 ), ( e + 0.5, n1 + 5.0, roof_z - 1.0 ), IRON_DARK )
        model.box( ( e - 3.0, n0 - 5.0, roof_z - 8.0 ), ( e + 3.0, n1 + 5.0, roof_z - 7.0 ), IRON_DARK )
        e += 60.0
    for n in ( n0 + 30.0, n1 - 30.0 ):
        model.box( ( 0.0, n - 1.5, roof_z - 4.0 ), ( wall_in, n + 1.5, roof_z - 0.05 ), IRON_DARK )
    for side_n, out in ( ( n0 - 6.0, -1.0 ), ( n1 + 6.0, 1.0 ) ):
        lo, hi = sorted( ( side_n, side_n + out * 1.5 ) )
        model.box( ( 0.0, lo, roof_z - 4.0 ), ( wall_in, hi, roof_z + 8.0 ), { "default": IRON_DARK, "-e": None } )
        lo, hi = sorted( ( side_n + out * 1.5, side_n + out * 2.2 ) )
        model.box( ( 0.0, lo, roof_z - 4.0 ), ( wall_in, hi, roof_z - 3.0 ), { "default": IRON_DARK, "-e": None } )
        # A half-round gutter outside the fascia.
        g = side_n + out * 4.6
        for k in range( 7 ):
            t0, t1 = math.pi * k / 7, math.pi * ( k + 1 ) / 7
            a = ( g + out * 2.4 * math.cos( t0 ), roof_z + 5.0 - 2.4 * math.sin( t0 ) )
            b = ( g + out * 2.4 * math.cos( t1 ), roof_z + 5.0 - 2.4 * math.sin( t1 ) )
            quad = [ ( 0.0, a[0], a[1] ), ( wall_in, a[0], a[1] ), ( wall_in, b[0], b[1] ), ( 0.0, b[0], b[1] ) ]
            mid = np.array( ( 0.0, ( a[0] + b[0] ) / 2 - g, ( a[1] + b[1] ) / 2 - ( roof_z + 5.0 ) ) )
            P._poly( model, IRON_DARK, quad, mid )
            P._poly( model, IRON_DARK, quad, -mid )
        for c in columns:
            pe = c + 9.0
            downpipe( model, pe, g, roof_z + 3.0, 0.0, radius=1.9, paint=IRON_DARK, shoe=( 0, out ), wall=None )
    # The handrails: a round rail on brackets at the mullions, stopping at the stairs.
    for side_n, inward in ( ( n0, 1.0 ), ( n1, -1.0 ) ):
        rail_n = side_n + inward * 6.8
        face_n = side_n + inward * 4.0
        ends = [ 0.0 ]
        for a, b in sorted( ( a, b ) for a, b, d in stairs if ( d > 0 ) == ( side_n == n1 ) ):
            ends += [ a + 3.6, b - 3.6 ]
        ends.append( wall_in )
        for a, b in zip( ends[::2], ends[1::2] ):
            P.tube_path( model, [ ( a, rail_n, rail_z ), ( b, rail_n, rail_z ) ], 0.85, RAIL, sides=16 )
            e = a + 6.0
            while e < b - 3.0:
                P.tube_path( model, [ ( e, rail_n, rail_z - 0.8 ), ( e, rail_n, rail_z - 3.5 ), ( e, face_n, rail_z - 3.5 ) ],
                             0.4, RAIL, sides=6 )
                lo, hi = sorted( ( face_n, face_n + inward * 0.3 ) )
                model.box( ( e - 1.2, lo, rail_z - 5.5 ), ( e + 1.2, hi, rail_z - 1.5 ), RAIL )
                e += 60.0
        # Stiffeners on the panel's inner face, between the mullions.
        gaps = [ ( a - 8, b + 8 ) for a, b, d in stairs if ( d > 0 ) == ( side_n == n1 ) ]
        e = 31.5
        while e < wall_in - 5:
            if not any( a < e < b for a, b in gaps ):
                lo, hi = sorted( ( face_n, face_n + inward * 1.0 ) )
                model.box( ( e - 1.5, lo, deck_z + 1.0 ), ( e + 1.5, hi, 247.5 ), IRON_DARK )
            e += 60.0


def stair( model, e0, e1, bottom_n, climb, rise, tread, z0, count, first=True, last=False ):
    """ A flight's tread nosings: a dark anti-slip strip proud of each tread's front, with the yellow step marking on the
    flight's first and last treads only. """
    for k in range( count ):
        a = bottom_n + climb * k * tread
        top = z0 + ( k + 1 ) * rise
        lo, hi = sorted( ( a - climb * 0.25, a + climb * 1.8 ) )
        yellow = ( first and k == 0 ) or ( last and k == count - 1 )
        model.box( ( e0 + 0.2, lo, top - 0.9 ), ( e1 - 0.2, hi, top + 0.22 ), "rw_line_yellow" if yellow else "rw_rubber" )


def stair_rails( model, e_rail, face_e, points, heights=( 36.0, 28.0 ), streak=None ):
    """ Two round handrails on a stair parapet's inside (e_rail, the parapet's face at face_e) along the stair's nosing
    line points [ ( n, z ) ], with brackets every 48. streak (the face's outward sign along e): a grime streak down the
    face under each bracket. """
    for h in heights:
        P.tube_path( model, [ ( e_rail, n, z + h ) for n, z in points ], 0.83, RAIL, sides=16 )
    total = 0.0
    segs = list( zip( points, points[1:] ) )
    for ( na, za ), ( nb, zb ) in segs:
        length = math.hypot( nb - na, zb - za )
        k = 0
        while k * 48.0 < length - 6:
            t = ( k * 48.0 + 8.0 ) / length
            if t > 1:
                break
            n, z = na + ( nb - na ) * t, za + ( zb - za ) * t
            for h in heights:
                P.tube_path( model, [ ( e_rail, n, z + h - 0.8 ), ( e_rail, n, z + h - 2.6 ), ( face_e, n, z + h - 2.6 ) ],
                             0.35, RAIL, sides=6 )
                lo, hi = sorted( ( face_e, face_e + ( e_rail - face_e ) * 0.12 ) )
                model.box( ( lo, n - 1.0, z + h - 4.2 ), ( hi, n + 1.0, z + h - 1.0 ), RAIL )
                if streak is not None:
                    D.bracket_streak( model, face_e, streak, n, z + h - 4.2 )
            k += 1


def parapet_cap( model, w0, w1, n_a, n_b, top_a, top_b ):
    """ A smooth precast cap along a sloping parapet's top: 3 in deep, an inch over each face, with a drip lip under
    each overhang and a weathered (stepped) top. """
    c = ( w0 + w1 ) / 2
    half = ( w1 - w0 ) / 2
    model.beam( ( c, n_a, top_a + 1.2 ), ( c, n_b, top_b + 1.2 ), ( ( w1 - w0 ) + 2.0, 3.0 ), "rw_concrete", up=( 0, 0, 1 ) )
    model.beam( ( c, n_a, top_a + 3.0 ), ( c, n_b, top_b + 3.0 ), ( ( w1 - w0 ) + 0.4, 0.6 ), "rw_concrete", up=( 0, 0, 1 ) )
    for s in ( -1.0, 1.0 ):
        e = c + s * ( half + 0.7 )
        model.beam( ( e, n_a, top_a - 0.65 ), ( e, n_b, top_b - 0.65 ), ( 0.6, 0.7 ), "rw_concrete", up=( 0, 0, 1 ) )


def precast_face( model, e_face, out, n_a, n_b, top_a, top_b, z0=0.0, pitch=96.0, paint="rw_concrete_dark" ):
    """ A precast parapet's outer face (at e_face, facing out): dark joints between its 2.4 m panels, the grime line the
    cap's drip leaves under it, and the splash band at its foot. Paint a hair proud of the face, no relief. """
    lo_n, hi_n = sorted( ( n_a, n_b ) )

    def top( n ):
        t = ( n - n_a ) / ( n_b - n_a ) if n_b != n_a else 0.0
        return top_a + ( top_b - top_a ) * t

    d = e_face + out * 0.06
    normal = ( out, 0.0, 0.0 )
    n = lo_n + pitch
    while n < hi_n - 12:
        P._poly( model, paint, [ ( d, n - 0.4, z0 + 0.5 ), ( d, n + 0.4, z0 + 0.5 ), ( d, n + 0.4, top( n + 0.4 ) - 0.4 ),
                                 ( d, n - 0.4, top( n - 0.4 ) - 0.4 ) ], normal )
        n += pitch
    # The grime line under the cap's drip.
    h0, h1 = 0.3, 4.0
    P._poly( model, paint, [ ( d, lo_n + 1.0, top( lo_n + 1.0 ) - h1 ), ( d, hi_n - 1.0, top( hi_n - 1.0 ) - h1 ),
                             ( d, hi_n - 1.0, top( hi_n - 1.0 ) - h0 ), ( d, lo_n + 1.0, top( lo_n + 1.0 ) - h0 ) ], normal )
    # The splash band at its foot.
    P._poly( model, paint, [ ( d, lo_n + 1.0, z0 ), ( d, hi_n - 1.0, z0 ), ( d, hi_n - 1.0, z0 + 5.0 ), ( d, lo_n + 1.0, z0 + 5.0 ) ],
             normal )


# ---------------------------------------------------------------------------------------------------------------------
# Platforms: jointed coping and ramp rails

def coping( model, c_lo, c_hi, n0, n1, back_e, step=39.6, gap=0.4 ):
    """ Precast coping slabs ( c_lo..c_hi across, n0..n1 along ) with joints, their back face against the paving at
    back_e left undrawn. """
    n = n0
    while n < n1 - 0.5:
        b = min( n + step, n1 )
        paints = { "default": "rw_coping", "-z": "rw_concrete_dark", ( "+e" if back_e > c_lo else "-e" ): None }
        model.box( ( c_lo, n, -6.0 ), ( c_hi, b, 0.0 ), paints )
        n = b + gap


def ramp_rail( model, e, n_foot, n_top, z_foot, z_top, out ):
    """ A kerb and a round handrail on posts along a platform ramp's open side at e (the track side, out +1/-1). """
    kerb_e = e - out * 3.0
    model.beam( ( kerb_e, n_foot, z_foot + 2.0 ), ( kerb_e, n_top + 6.0, z_top + 2.0 ), ( 4.0, 4.0 ), "rw_concrete", up=( 0, 0, 1 ) )
    rail_e = e - out * 6.0
    pts = [ ( rail_e, n_foot + 3.0, z_foot + 36.0 + ( z_top - z_foot ) * 3.0 / ( n_top - n_foot ) ),
            ( rail_e, n_top, z_top + 36.0 ), ( rail_e, n_top + 30.0, z_top + 36.0 ) ]
    P.tube_path( model, pts, 0.85, RAIL, sides=16 )
    for n in ( n_foot + 3.0, ( n_foot + n_top ) / 2, n_top, n_top + 30.0 ):
        t = min( max( ( n - n_foot ) / ( n_top - n_foot ), 0.0 ), 1.0 )
        z = z_foot + ( z_top - z_foot ) * t
        P.tube_path( model, [ ( rail_e, n, z ), ( rail_e, n, z + 36.0 ) ], 0.8, RAIL, sides=12 )
        P.chamfer_box( model, ( rail_e - 2.5, n - 2.5, z - 0.1 ), ( rail_e + 2.5, n + 2.5, z + 0.5 ), RAIL, chamfer=0.3, skip=( "-z", ) )


def formwork( model, e_face, out, n_a, n_b, top_a, top_b, z0=0.0, pitch=48.0, lift=48.0, paint="rw_concrete_dark" ):
    """ Board-formed concrete's tell-tales on a wall face at e_face (facing out, +1/-1) from n_a to n_b, its top
    sloping from top_a to top_b: shallow vertical panel joints every pitch, lift joints every lift, and tie-hole plugs. """
    lo_n, hi_n = sorted( ( n_a, n_b ) )

    def top( n ):
        t = ( n - n_a ) / ( n_b - n_a ) if n_b != n_a else 0.0
        return top_a + ( top_b - top_a ) * t

    d0, d1 = sorted( ( e_face, e_face + out * 0.25 ) )
    n = lo_n + pitch
    while n < hi_n - 6:
        model.box( ( d0, n - 0.3, z0 + 1.0 ), ( d1, n + 0.3, top( n ) - 2.5 ), paint )
        n += pitch
    z = z0 + lift
    while z < max( top_a, top_b ) - 4:
        # A lift joint, as far as the wall's top lets it.
        ns = [ m for m in np.linspace( lo_n, hi_n, 64 ) if top( m ) > z + 4 ]
        if ns:
            model.box( ( d0, ns[0] + 1.0, z - 0.3 ), ( d1, ns[-1] - 1.0, z + 0.3 ), paint )
            n = lo_n + pitch / 2
            while n < hi_n:
                for zz in ( z - lift / 2, ):
                    if zz > z0 + 6 and top( n ) > zz + 6:
                        a = np.array( ( e_face, n, zz ) )
                        P.bolt( model, a, ( out, 0, 0 ), radius=0.6, length=0.12, paint=paint, sides=10, washer=False )
                n += pitch
        z += lift


# ---------------------------------------------------------------------------------------------------------------------
# Weathering zones: a paint's faces cut at a height, the upper part repainted (soot, darker lime, dark brick)

def split_by_height( model, paint, z_cut, upper, bounds=None ):
    """ Cuts every polygon of paint at z_cut and repaints the part above it upper. bounds ( e0, e1, n0, n1 ) limits it
    to polygons whose centre is in that plan box. Explicit UVs and smooth normals are cut with them. """
    items = model.polygons.get( paint )
    if not items:
        return
    keep, keep_uv, keep_nrm = [], {}, {}
    up_start = len( model.polygons[upper] )
    added = []

    def clip( pts, uvs, nrms, above ):
        out_p, out_u, out_n = [], [], []
        k = len( pts )
        for i in range( k ):
            a, b = pts[i], pts[( i + 1 ) % k]
            ina = ( a[2] >= z_cut - 1e-6 ) if above else ( a[2] <= z_cut + 1e-6 )
            inb = ( b[2] >= z_cut - 1e-6 ) if above else ( b[2] <= z_cut + 1e-6 )
            if ina:
                out_p.append( a )
                out_u.append( uvs[i] if uvs is not None else None )
                out_n.append( nrms[i] if nrms is not None else None )
            if ina != inb and abs( b[2] - a[2] ) > 1e-9:
                t = ( z_cut - a[2] ) / ( b[2] - a[2] )
                if 1e-6 < t < 1 - 1e-6:
                    out_p.append( a + ( b - a ) * t )
                    out_u.append( tuple( np.asarray( uvs[i] ) + ( np.asarray( uvs[( i + 1 ) % k] ) - np.asarray( uvs[i] ) ) * t )
                                  if uvs is not None else None )
                    out_n.append( np.asarray( nrms[i] ) + ( np.asarray( nrms[( i + 1 ) % k] ) - np.asarray( nrms[i] ) ) * t
                                  if nrms is not None else None )
        return out_p, out_u, out_n

    for i, ( pts, normal ) in enumerate( items ):
        p = [ np.asarray( q, float ) for q in pts ]
        uv = model.polygon_uvs.get( ( paint, i ) )
        nr = model.polygon_normals.get( ( paint, i ) )
        zs = [ q[2] for q in p ]
        centre = np.mean( p, axis=0 )
        inside = bounds is None or ( bounds[0] <= centre[0] <= bounds[1] and bounds[2] <= centre[1] <= bounds[3] )
        if not inside or max( zs ) <= z_cut + 1e-6:
            parts_low, parts_up = [ ( p, uv, nr ) ], []
        elif min( zs ) >= z_cut - 1e-6:
            parts_low, parts_up = [], [ ( p, uv, nr ) ]
        else:
            lo = clip( p, uv, nr, False )
            hi = clip( p, uv, nr, True )
            parts_low = [ ( lo[0], uv and lo[1], nr and lo[2] ) ] if len( lo[0] ) >= 3 else []
            parts_up = [ ( hi[0], uv and hi[1], nr and hi[2] ) ] if len( hi[0] ) >= 3 else []
        for q, u, n in parts_low:
            idx = len( keep )
            keep.append( ( q, normal ) )
            if u is not None:
                keep_uv[idx] = list( u )
            if n is not None:
                keep_nrm[idx] = list( n )
        for q, u, n in parts_up:
            added.append( ( q, normal, u, n ) )
    model.polygons[paint] = keep
    model.polygon_uvs = { k: v for k, v in model.polygon_uvs.items() if k[0] != paint } | { ( paint, i ): v for i, v in keep_uv.items() }
    model.polygon_normals = { k: v for k, v in model.polygon_normals.items() if k[0] != paint } | \
        { ( paint, i ): v for i, v in keep_nrm.items() }
    for q, normal, u, n in added:
        idx = len( model.polygons[upper] )
        model.polygons[upper].append( ( q, normal ) )
        if u is not None:
            model.polygon_uvs[( upper, idx )] = list( u )
        if n is not None:
            model.polygon_normals[( upper, idx )] = list( n )


def repaint( model, paint, upper, bounds=None, z_min=None ):
    """ Every polygon of paint (in bounds, wholly above z_min) repainted upper. """
    split_by_height( model, paint, -1e9 if z_min is None else z_min, upper, bounds )


# ( z cut, ( |e| from, |e| to ), ( n from, n to ) ): sandstone soot zones, each cut at a moulding's underside or top.
SOOT_ZONES = (
    ( 316.0, ( 1150.0, 1180.0 ), ( -1345.0, 1298.0 ) ),     # the shed's outer wall, inside: under the inside cornice
    ( 340.0, ( 1180.0, 1216.0 ), ( -1345.0, 1298.0 ) ),     # its outside face and parapet: under the cab road cornice
    ( 340.0, ( 0.0, 1216.0 ), ( 1295.0, 1345.0 ) ),         # the head building's south front: under its cornice
    ( 440.0, ( 1150.0, 1216.0 ), ( 1345.0, 1825.0 ) ),      # the wings' street sides: over the main cornice
    ( 470.0, ( 0.0, 1216.0 ), ( 1775.0, 1825.0 ) ),         # the street front: its gable
)


def split_below( model, paint, z_cut, lower, bounds=None ):
    """ Cuts every polygon of paint (in bounds) at z_cut and repaints the part below it lower. """
    tmp = "__split_below_tmp"
    split_by_height( model, paint, z_cut, tmp, bounds )
    repaint( model, paint, lower, bounds )
    repaint( model, tmp, paint )
    model.polygons.pop( tmp, None )


def weather( models ):
    """ The soot and wear zones the materials agent's paints are for: soot on the sandstone above 250 and on the ironwork
    high in the shed, darker lime in the hall above the gallery and on its vault, and dark brick in the goods sheds' top
    courses. """
    for name in ( "railhead_east", "railhead_west", "railhead_centre" ):
        m = models.get( name )
        if m is None:
            continue
        # The sandstone's soot starts under a moulding each time, so the change of paint is hidden by its shadow line:
        # inside the shed under the cornice (316), outside it under the cab road cornice (340), the head building's south
        # front under its cornice (340), the wings over their main cornice (440) and the street front at its gable (470).
        for z_cut, ( a, b ), ( n0, n1 ) in SOOT_ZONES:
            for s in ( 1.0, -1.0 ):
                lo, hi = sorted( ( s * a, s * b ) )
                split_by_height( m, "rw_sandstone", z_cut, "rw_sandstone_soot", bounds=( lo, hi, n0, n1 ) )
        split_by_height( m, "rw_sandstone", 440.0, "rw_sandstone_soot" )
        # The hall is kept repainted cream to the entablature; only the lunette band and the vault above it are dulled.
        # Only the springing (the lunette band and the vault's first 24 in) is dulled: the vault's panels stay cream,
        # so the ribs read against a light ground.
        for bounds in ( ( -HALL_E - 1, -548.0, 1335.0, 1785.0 ), ( 548.0, HALL_E + 1, 1335.0, 1785.0 ) ):
            split_by_height( m, "render_cream", ENTABLATURE_Z + 40.0, "rw_lime_dark", bounds=bounds )
        # The plaster's worn band (grime, scuffs and hand marks, anchored at the floor) below 60 in the hall (over its
        # stone dado) and in the wings' rooms.
        for bounds in ( ( -HALL_E - 1, HALL_E + 1, 1335.0, 1785.0 ), ( HALL_E + 1, 1165.0, 1335.0, 1785.0 ),
                        ( -1165.0, -HALL_E - 1, 1335.0, 1785.0 ) ):
            split_below( m, "render_cream", 60.0, "rw_lime_dado", bounds=bounds )
        # Iron: the middle columns, their capitals and brackets stay one paint; the girder over them is the sooted part
        # (its underside is the line where the change sits, in the bracket's shadow).
        if name == "railhead_centre":
            split_by_height( m, "rw_steel", GIRDER_Z[0] - 0.5, "rw_steel_soot", bounds=( -45.0, 45.0, -1400.0, 1320.0 ) )
            for bounds in ( ( -1e9, -45.0, -1e9, 1e9 ), ( 45.0, 1e9, -1e9, 1e9 ), ( -45.0, 45.0, -1e9, -1400.0 ),
                            ( -45.0, 45.0, 1320.0, 1e9 ) ):
                split_by_height( m, "rw_steel", 300.0, "rw_steel_soot", bounds=bounds )
        else:
            split_by_height( m, "rw_steel", 300.0, "rw_steel_soot" )
        for b in ( ( 1500.0, 1820.0, -2220.0, -1580.0 ), ( -1820.0, -1500.0, -2220.0, -1580.0 ) ):
            split_by_height( m, "brick", 172.0, "rw_brick_dark", bounds=b )
    roof = models.get( "railhead_roof" )
    if roof is not None:
        repaint( roof, "rw_steel", "rw_steel_soot" )


# ---------------------------------------------------------------------------------------------------------------------
# The goods sheds

def goods_shed( model, e0, e1, n0, n1, floor, eave_z, ridge_z, over, doors, t=14.0 ):
    """ A goods shed's eaves and walls: exposed rafter feet under the overhangs, half-round gutters with downpipes at the
    corners, bargeboards on the gables, and a dressed plinth course broken at the doors. """
    ridge_e = ( e0 + e1 ) / 2
    slope = ( ridge_z - eave_z ) / ( ridge_e - e0 )
    low_z = eave_z - over * slope
    rn0, rn1 = n0 - 24.0, n1 + 24.0
    for s, wall_e in ( ( -1.0, e0 ), ( 1.0, e1 ) ):
        edge = wall_e + s * over
        # Rafter feet every 24 under the boarding.
        n = rn0 + 6.0
        while n < rn1 - 4:
            a = np.array( ( wall_e, n, eave_z - 0.5 ) )
            b = np.array( ( edge - s * 1.5, n, low_z - 0.5 ) )
            d = ( b - a ) / np.linalg.norm( b - a )
            down = np.cross( d, ( 0, 1, 0 ) ) * ( -s )
            model.beam( a + down * 2.5, b + down * 2.5, ( 5.0, 2.5 ), "planks_dark", up=( 0, 1, 0 ) )
            n += 24.0
        # A fascia board on the rafter ends, the gutter, and downpipes at the corners.
        lo, hi = sorted( ( edge, edge + s * 1.0 ) )
        model.box( ( lo, rn0, low_z - 6.0 ), ( hi, rn1, low_z + 5.0 ), "planks_dark" )
        g = edge + s * 3.6
        gz = low_z - 1.0
        for k in range( 7 ):
            t0, t1 = math.pi * k / 7, math.pi * ( k + 1 ) / 7
            pa = ( g + s * 2.6 * math.cos( t0 ), gz - 2.6 * math.sin( t0 ) )
            pb = ( g + s * 2.6 * math.cos( t1 ), gz - 2.6 * math.sin( t1 ) )
            quad = [ ( pa[0], rn0, pa[1] ), ( pa[0], rn1, pa[1] ), ( pb[0], rn1, pb[1] ), ( pb[0], rn0, pb[1] ) ]
            mid = np.array( ( ( pa[0] + pb[0] ) / 2 - g, 0.0, ( pa[1] + pb[1] ) / 2 - gz ) )
            P._poly( model, "copper_brown", quad, mid )
            P._poly( model, "copper_brown", quad, -mid )
        for nn, sn in ( ( rn0 + 5.0, 1.0 ), ( rn1 - 5.0, -1.0 ) ):
            P.tube_path( model, [ ( g, nn, gz - 1.5 ), ( g, nn, gz - 6.0 ), ( wall_e + s * 3.0, nn, gz - 14.0 ),
                                  ( wall_e + s * 3.0, nn, floor + 6.0 ), ( wall_e + s * 6.5, nn, floor + 1.5 ) ],
                         1.8, "copper_brown", sides=10 )
        # The dressed plinth course on the long wall's outside face, broken at the doors.
        gaps = [ ( d - 61.0, d + 61.0 ) for d in doors ]
        for a, b in run_breaks( n0, n1, gaps ):
            P.straight( model, "n", wall_e, a, b, floor, s, [ ( 0.0, 0.0 ), ( 2.5, 0.0 ), ( 2.5, 9.0 ), ( 1.2, 11.0 ), ( 0.0, 11.5 ) ],
                        "rw_dressed" )
        # Brick pilaster strips (Lisenen) between the door bays and at the corners, and a corbelled brick frieze under
        # the eaves: two stepped courses over a row of projecting headers, broken at the doors' steel lintels.
        door_gaps = [ ( d - 72.0, d + 72.0 ) for d in doors ]
        strips = [ n0 + 9.0, n1 - 9.0 ] + [ ( p + q ) / 2 for p, q in zip( doors, doors[1:] ) ] + \
                 [ ( n0 + doors[0] - 72.0 ) / 2, ( n1 + doors[-1] + 72.0 ) / 2 ]
        for c in strips:
            lo, hi = sorted( ( wall_e, wall_e + s * 2.2 ) )
            P.chamfer_box( model, ( lo, c - 9.0, floor + 11.5 ), ( hi, c + 9.0, eave_z - 18.0 ), "brick", chamfer=0.3, skip=( "-z", ) )
        for a, b in run_breaks( n0, n1, door_gaps ):
            P.straight( model, "n", wall_e, a, b, eave_z - 18.0, s,
                        [ ( 0.0, 0.0 ), ( 1.2, 0.0 ), ( 1.2, 2.7 ), ( 0.0, 2.7 ) ], "brick" )
            P.straight( model, "n", wall_e, a, b, eave_z - 8.0, s,
                        [ ( 0.0, 0.0 ), ( 1.4, 0.0 ), ( 1.4, 2.7 ), ( 2.6, 2.7 ), ( 2.6, 5.4 ), ( 0.0, 5.4 ) ], "brick" )
            r = a + 3.0
            while r < b - 3.0:
                lo, hi = sorted( ( wall_e, wall_e + s * 1.6 ) )
                model.box( ( lo, r - 1.2, eave_z - 13.4 ), ( hi, r + 1.2, eave_z - 10.7 ), "brick" )
                r += 4.8
    # Bargeboards along the gables' verges.
    for nn in ( rn0 - 1.0, rn1 + 1.0 ):
        for s in ( -1.0, 1.0 ):
            edge = ( e0 if s < 0 else e1 ) + s * over
            a = np.array( ( edge, nn, low_z + 5.0 ) )
            b = np.array( ( ridge_e, nn, ridge_z + 5.0 ) )
            d = ( b - a ) / np.linalg.norm( b - a )
            down = -s * np.array( ( d[2], 0.0, -d[0] ) )
            model.beam( a + down * 4.0, b + down * 4.0, ( 10.0, 1.6 ), "planks_dark", up=( 0, 1, 0 ) )
