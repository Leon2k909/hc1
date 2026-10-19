"""Railhead's street and platform furniture and yard clutter, for railhead_props (whose functions of the same names
call these) and for railhead_map's placements.

Frames are railhead_props.Frame: x to the right of someone facing the thing's front, y towards its front, z up from
its foot. Sizes are real ones, in inches:

- bin: today's platform recycling bin, a three-bay stainless unit 1.0 x 0.42 x 1.0 m on a recessed plinth, a slot in
  each bay under one sloped hood, the bays' doors and locks, colour-coded pictogram plates (blue paper, yellow
  packaging, grey the rest) and an ashtray on the hood.
- bench_details: the cast end frames' foot plates with four bolts each, and the middle armrest of a long bench.
- timetable_case: an Aushangfahrplan case, silver anodised aluminium, 40 mm frame, 60 mm deep, glazed, under a sloped
  rain cap, on two posts.
- info_pillar_head: the help point's backlit opal head and its red SOS plate.
- cable_trough, drain_grate: the concrete cable trough along a platform wall's foot (300 x 200 mm, 1 m lids) and a
  cast-iron gully grate in the track bed or a floor.
- drum, pallet_jack, cable_reel, cone, bike_rack: a 200 l steel drum, a hand pallet truck, a cable reel, a 750 mm
  traffic cone and a row of Sheffield bike stands.

Collision: only where a new solid object needs it, one simple box (drums, reels, the bin keeps its old box).
"""
import math

import numpy as np

STEEL = "rw_stainless"
ALU = "rw_alu_brushed"
DARK = "rw_steel_dark"
GREY = "rw_steel_grey"
GALV = "rw_galvanised"


def _sign_uv( name ):
    try:
        import railhead_prop_materials as PM
        u0, v0, u1, v1 = PM.rect_uv( name )
    except Exception:
        u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
    return [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]


def _bevel( model, F, lo, hi, paint, bevel=0.4, edge=None ):
    import railhead_buffer as B
    lo, hi = np.asarray( lo, float ), np.asarray( hi, float )
    B.bevel_box( model, F, np.minimum( lo, hi ), np.maximum( lo, hi ), paint, bevel, edge )


# ---------------------------------------------------------------------------------------------------------------------
# Platform furniture

BIN_W, BIN_D, BIN_H = 19.7, 8.3, 39.4      # half width, half depth, height


def bin( model, F ):
    """ The three-bay recycling bin in frame F (its front towards +y). Visual only: railhead_props.bin keeps its old
    collision box. """
    import railhead_props as P
    w, d = BIN_W, BIN_D
    F.box( model, -w + 1.2, w - 1.2, -d + 1.2, d - 1.2, 0.0, 2.2, DARK, skip=( "bottom", ) )
    gap = 0.5
    bw = ( 2 * w - 2 * gap ) / 3
    top = 33.6
    for k, plate in enumerate( ( "bin_paper", "bin_pack", "bin_rest" ) ):
        x0 = -w + k * ( bw + gap )
        x1 = x0 + bw
        xm = ( x0 + x1 ) / 2
        _bevel( model, F, ( x0, -d, 2.2 ), ( x1, d, top ), STEEL, 0.55 )
        # The bay's door: a seam inset round its front, a lock, the slot under the hood with its rubber flap.
        for a, b, c, e in ( ( x0 + 1.0, x0 + 1.18, 4.0, 27.0 ), ( x1 - 1.18, x1 - 1.0, 4.0, 27.0 ),
                            ( x0 + 1.0, x1 - 1.0, 4.0, 4.18 ), ( x0 + 1.0, x1 - 1.0, 26.82, 27.0 ) ):
            P._frect( model, F, "rw_black", a, b, d + 0.02, c, e )
        P.disc( model, DARK, F.p( xm, d + 0.04, 24.6 ), F.y, 0.55, sides=10 )
        P._frect( model, F, "rw_black", x0 + 1.6, x1 - 1.6, d + 0.03, 29.0, 31.8 )
        P._frect( model, F, "rw_rubber", x0 + 1.6, x1 - 1.6, d + 0.05, 30.9, 31.8 )
        # The pictogram plate in its colour.
        P._frect( model, F, "rw_prop_signs", xm - 3.6, xm + 3.6, d + 0.05, 14.0, 21.2, uv=_sign_uv( plate ) )
    # The hood over all three bays, sloping down to the front with a drip, and the ashtray on it.
    P._side_prism( model, F, [ ( -d - 0.4, top ), ( d + 1.3, top ), ( d + 1.3, top + 1.4 ), ( -d - 0.4, top + 5.2 ) ],
                   -w - 0.4, w + 0.4, lambda k: STEEL, STEEL )
    c = F.p( 0.0, -d + 2.4, top + 4.6 )
    P.rod( model, c, c + F.z * 1.4, 2.6, STEEL, 16, caps=( False, True ) )
    P.disc( model, DARK, c + F.z * 1.42, F.z, 2.1, sides=16 )


def bench_details( model, F, posts, c, seat, frame ):
    """ A bench's end frames' foot plates (200 x 100 mm, four bolts each) at both feet of each post, and its middle
    armrest if it has a middle post (x 0). posts: the frames' x; c: the footprint's centring; seat: the seat's top. """
    import railhead_props as P
    for x in posts:
        for y in ( 6.8 + c, -8.4 + c ):
            _bevel( model, F, ( x - 2.0, y - 3.9, 0.0 ), ( x + 2.0, y + 3.9, 0.45 ), frame, 0.12 )
            for dx in ( -1.35, 1.35 ):
                for dy in ( -3.0, 3.0 ):
                    P.rod( model, F.p( x + dx, y + dy, 0.45 ), F.p( x + dx, y + dy, 0.75 ), 0.32, GREY, 6,
                           caps=( False, True ) )
        if abs( x ) < 1e-6:
            # The armrest: a cast bow from the seat's front edge back to the backrest, splitting the seat in two.
            pts = [ ( 0.0, 7.6 + c, seat ), ( 0.0, 7.8 + c, seat + 6.2 ), ( 0.0, 6.0 + c, seat + 8.6 ),
                    ( 0.0, -2.0 + c, seat + 8.8 ), ( 0.0, -7.6 + c, seat + 7.2 ) ]
            for a, b in zip( pts, pts[1:] ):
                P._fbeam( model, F, a, b, ( 1.6, 1.3 ), frame )


def bench_frames( model, F, posts, c, seat, frame, back0, back1 ):
    """ A bench's cast aluminium end frames, one at each post's x: a front leg tapering from its foot, the seat
    bearer, a raked rear leg up to the backrest's foot and the backrest's upright, each a solid casting 25 mm thick
    with its edges softened, in the frame's powder coat. back0, back1: the backrest's foot and top ( y, z ). """
    import railhead_props as P
    fy, ry = 6.8 + c, -8.4 + c
    pieces = [
        [ ( fy - 1.3, 0.0 ), ( fy + 1.3, 0.0 ), ( fy + 0.8, seat - 1.3 ), ( fy - 0.8, seat - 1.3 ) ],
        [ ( back0[0] + 0.4, seat - 3.4 ), ( fy + 1.6, seat - 2.6 ), ( fy + 1.6, seat - 1.3 ), ( back0[0] + 0.4, seat - 1.3 ) ],
        [ ( ry - 1.2, 0.0 ), ( ry + 1.2, 0.0 ), ( back0[0] + 0.8, back0[1] ), ( back0[0] - 0.8, back0[1] ) ],
        [ ( back0[0] - 0.8, back0[1] ), ( back0[0] + 0.8, back0[1] ), ( back1[0] + 0.7, back1[1] ), ( back1[0] - 0.7, back1[1] ) ],
    ]
    for x in posts:
        for prof in pieces:
            # _side_prism wants a convex profile, counter-clockwise or not.
            P._side_prism( model, F, prof, x - 0.5, x + 0.5, lambda k: frame, frame )


def timetable_case( model, F, two_sided=False ):
    """ The timetable case in frame F: the yellow departures and white arrivals sheets (A1) side by side, 900 mm up,
    behind glass in a silver anodised aluminium frame 40 mm wide and 60 mm deep, under a sloped rain cap, on two posts.
    Returns its collision's ( x0, x1, y0, y1, z1 ) for the caller. """
    import railhead_props as P
    pw, ph, gap, border = 23.4, 33.1, 1.6, 1.6
    hw, d = pw + gap / 2 + border, 1.2
    zb = 33.8
    zt = zb + ph + 2 * border
    zc = zb + border + ph / 2
    F.box( model, -hw, hw, -d, d, zb, zt, ALU )
    sides = [ ( 1.0, "front" ) ] + ( [ ( -1.0, "back" ) ] if two_sided else [] )
    for s, face in sides:
        F.atlas( model, "rw_posters", "timetable_dep", -s * ( pw + gap ) / 2, s * ( d + 0.03 ), zc, pw, ph, face )
        F.atlas( model, "rw_posters", "timetable_arr", s * ( pw + gap ) / 2, s * ( d + 0.03 ), zc, pw, ph, face )
        # The divider between the sheets, and the glass 30 mm in front of them in the frame's deep reveal.
        P._frect( model, F, ALU, -gap / 2, gap / 2, s * ( d + 0.05 ), zb + border, zt - border, s )
        P._frect( model, F, "rw_case_glass", -hw + border, hw - border, s * ( d + 1.2 ), zb + border, zt - border, s )
        y0, y1 = sorted( ( s * d, s * ( d + 1.55 ) ) )
        for x0, x1, z0_, z1_ in ( ( -hw, hw, zb, zb + border ), ( -hw, hw, zt - border, zt ),
                                  ( -hw, -hw + border, zb + border, zt - border ),
                                  ( hw - border, hw, zb + border, zt - border ) ):
            _bevel( model, F, ( x0, y0, z0_ ), ( x1, y1, z1_ ), ALU, 0.18 )
        # The lock in the frame's bottom rail.
        P.disc( model, DARK, F.p( hw - 4.0, s * ( d + 1.57 ), zb + border / 2 ), F.y * s, 0.4, sides=10 )
    for x in ( -hw - 1.3, hw + 1.3 ):
        F.box( model, x - 1.3, x + 1.3, -1.3, 1.3, 0.0, zt + 1.5, ALU, skip=( "bottom", "top" ) )
        _bevel( model, F, ( x - 2.6, -2.6, 0.0 ), ( x + 2.6, 2.6, 0.5 ), ALU, 0.1 )
    # The rain cap: a sloped aluminium hood over the frame, with a drip at its edges.
    cap_d = d + 2.4
    prof = [ ( -cap_d, zt + 1.2 ), ( cap_d, zt + 1.2 ), ( cap_d, zt + 1.9 ), ( 0.0, zt + 3.0 ), ( -cap_d, zt + 1.9 ) ]
    P._side_prism( model, F, prof, -hw - 3.0, hw + 3.0, lambda k: ALU, ALU )
    return ( -hw - 3.0, hw + 3.0, -cap_d, cap_d, zt + 3.0 )


def info_pillar_head( model, F ):
    """ The help point's head (84 to 100.4 up): a backlit opal light box in an aluminium frame, and the red SOS plate
    over the intercom. The caller draws the "i" signs on it. """
    import railhead_props as P
    F.box( model, -8.3, 8.3, -5.9, 5.9, 84.0, 100.4, { "default": "rw_kiosk_fascia", "top": ALU, "bottom": ALU } )
    for z0, z1 in ( ( 83.6, 84.6 ), ( 99.8, 100.8 ) ):
        _bevel( model, F, ( -8.6, -6.2, z0 ), ( 8.6, 6.2, z1 ), ALU, 0.2 )
    P._frect( model, F, "rw_prop_signs", -2.4, 2.4, 5.45, 61.0, 65.8, uv=_sign_uv( "sos" ) )


# ---------------------------------------------------------------------------------------------------------------------
# Track side

def cable_trough( model, e, n0, n1, z0 ):
    """ A precast concrete cable trough along n from n0 to n1 at e (its centre), its lids' tops at z0 + 7.9: 300 mm
    wide, 200 mm deep, lids 1 m long with a lifting slot, a few stencilled. Concrete collision, one box. """
    lo, hi = sorted( ( n0, n1 ) )
    hw, h = 5.9, 7.9
    # The trough's walls (their outer faces show above the ballast) and the lids on them.
    model.box( ( e - hw, lo, z0 ), ( e + hw, hi, z0 + h - 0.8 ), "rw_mast_concrete", skip=( "-z", "+z" ) )
    count = max( 1, int( round( ( hi - lo ) / 39.4 ) ) )
    step = ( hi - lo ) / count
    for k in range( count ):
        a, b = lo + k * step + 0.2, lo + ( k + 1 ) * step - 0.2
        paint = ( "rw_concrete", "rw_mast_concrete", "rw_concrete_dark" )[ ( k * 7 ) % 3 ]
        model.box( ( e - hw - 0.2, a, z0 + h - 0.8 ), ( e + hw + 0.2, b, z0 + h ), paint, skip=( "-z", ) )
        # The lifting slot.
        m = ( a + b ) / 2
        model.polygon( "rw_black", [ ( e - 0.4, m - 2.0, z0 + h + 0.01 ), ( e + 0.4, m - 2.0, z0 + h + 0.01 ),
                                     ( e + 0.4, m + 2.0, z0 + h + 0.01 ), ( e - 0.4, m + 2.0, z0 + h + 0.01 ) ] )
        if k % 5 == 2:
            uv = _sign_uv( "trough_mark" )
            model.polygon( "rw_prop_signs", [ ( e - 4.6, a + 4.0, z0 + h + 0.02 ), ( e + 4.6, a + 4.0, z0 + h + 0.02 ),
                                               ( e + 4.6, a + 7.0, z0 + h + 0.02 ), ( e - 4.6, a + 7.0, z0 + h + 0.02 ) ],
                           uv=[ uv[0], uv[1], uv[2], uv[3] ] )
    model.collision_box( ( e - hw - 0.2, lo, z0 ), ( e + hw + 0.2, hi, z0 + h ), "default" )


def drain_grate( model, e, n, z0 ):
    """ A cast-iron gully grate (500 x 300 mm) set flush at z0 in its frame, nine bars across, the dark sump under. """
    hw, hl = 5.9, 9.8
    z = z0 + 0.04
    model.box( ( e - hw - 1.2, n - hl - 1.2, z0 - 0.4 ), ( e + hw + 1.2, n + hl + 1.2, z ), DARK, skip=( "-z", ) )
    model.polygon( "rw_black", [ ( e - hw, n - hl, z + 0.01 ), ( e + hw, n - hl, z + 0.01 ), ( e + hw, n + hl, z + 0.01 ),
                                 ( e - hw, n + hl, z + 0.01 ) ] )
    for k in range( 9 ):
        y = n - hl + ( k + 0.5 ) * 2 * hl / 9
        model.box( ( e - hw, y - 0.45, z - 0.2 ), ( e + hw, y + 0.45, z + 0.15 ), DARK, skip=( "-z", ) )
    model.box( ( e - 0.4, n - hl, z - 0.2 ), ( e + 0.4, n + hl, z + 0.12 ), DARK, skip=( "-z", ) )
    # A collision box under the floor, so it sits in the map's lists like any other fitting; nothing stands on it.
    model.collision_box( ( e - hw - 1.2, n - hl - 1.2, z0 - 4.0 ), ( e + hw + 1.2, n + hl + 1.2, z0 ), "metal" )


# ---------------------------------------------------------------------------------------------------------------------
# Yard clutter

def drum( model, e, n, z0, paint="rw_drum_blue" ):
    """ A 200 l steel drum (585 mm across, 880 mm tall) standing at ( e, n ): its body with two rolling hoops and the
    chime rims, the lid with its two bungs. Metal collision. """
    import railhead_props as P
    r, h = 11.5, 34.6
    c = np.array( ( e, n, z0 ) )
    z = np.array( ( 0.0, 0.0, 1.0 ) )
    P.rod( model, c + z * 0.5, c + z * ( h - 0.5 ), r, paint, 20 )
    for zz in ( 0.0, h - 0.5 ):                     # the chimes
        P.rod( model, c + z * zz, c + z * ( zz + 0.5 ), r + 0.12, paint, 20 )
    for zz in ( h / 3, 2 * h / 3 ):                  # the rolling hoops
        P.rod( model, c + z * ( zz - 0.45 ), c + z * ( zz + 0.45 ), r + 0.4, paint, 20 )
    P.disc( model, paint, c + z * ( h - 0.35 ), z, r - 0.15, sides=20 )
    for dx, rb in ( ( 6.0, 1.3 ), ( -6.5, 0.8 ) ):
        b = c + np.array( ( dx, 0.0, h - 0.35 ) )
        P.rod( model, b, b + z * 0.35, rb, GREY, 10, caps=( False, True ) )
    model.collision_box( ( e - r, n - r, z0 ), ( e + r, n + r, z0 + h ), "metal" )


def pallet_jack( model, e, n, along="n", z0=0.0 ):
    """ A hand pallet truck lying idle: two forks 1150 mm long and 160 mm wide, 540 mm over them, lowered (85 mm), the
    hydraulic unit with its steering wheels at the back and the tiller standing up. Visual only. """
    import railhead_props as P
    F = P.frame_for( e, n, z0, { "n": "+n", "e": "+e", "+n": "+n", "-n": "-n", "+e": "+e", "-e": "-e" }[along] )
    for x in ( -7.5, 7.5 ):
        F.box( model, x - 3.15, x + 3.15, -2.0, 45.3, 0.0, 3.35, "rw_red_paint", skip=( "bottom", ) )
        F.box( model, x - 3.15, x + 3.15, 45.3, 47.2, 0.0, 2.2, "rw_red_paint", skip=( "bottom", ) )   # the tapered tip
        for y in ( 41.0, ):                                                                      # the load rollers
            P.rod( model, F.p( x - 2.0, y, 1.2 ), F.p( x + 2.0, y, 1.2 ), 1.2, "rw_rubber", 10 )
    F.box( model, -10.7, 10.7, -6.0, -2.0, 0.0, 5.0, "rw_red_paint", skip=( "bottom", ) )
    # The pump: a cylinder upright, the chassis plate over the wheels and the tiller.
    P.rod( model, F.p( 0.0, -4.0, 3.0 ), F.p( 0.0, -4.0, 14.0 ), 2.6, "rw_red_paint", 14, caps=( False, True ) )
    for x in ( -3.2, 3.2 ):
        P.rod( model, F.p( x - 1.0, -6.5, 3.6 ), F.p( x + 1.0, -6.5, 3.6 ), 3.6, "rw_rubber", 14, caps=( True, True ) )
    a = F.p( 0.0, -4.0, 14.0 )
    b = F.p( 0.0, -9.0, 46.0 )
    P.rod( model, a, b, 0.9, "rw_red_paint", 8 )
    for x0, x1 in ( ( -5.5, 5.5 ), ):
        P.rod( model, F.p( x0, -9.2, 47.0 ), F.p( x1, -9.2, 47.0 ), 0.75, "rw_black", 8, caps=( True, True ) )
    for x in ( -5.5, 5.5 ):
        P.rod( model, b, F.p( x, -9.2, 47.0 ), 0.6, "rw_red_paint", 6 )
    F.collide( model, -10.7, 10.7, -9.0, 47.2, 0.0, 14.0, "metal" )


def cable_reel( model, e, n, z0, d=55.1 ):
    """ A wooden cable reel (d across its flanges, 760 mm between them) on its rim, its axis along e: two plank
    flanges with their bolts, the drum and the black cable wound on it. Wood collision. """
    import railhead_props as P
    r = d / 2
    c = np.array( ( e, n, z0 + r ) )
    x = np.array( ( 1.0, 0.0, 0.0 ) )
    half = 15.0
    for s in ( -1.0, 1.0 ):
        P.rod( model, c + x * s * half, c + x * s * ( half + 1.8 ), r, "rw_wood", 24, caps=( True, True ) )
        for k in range( 6 ):
            t = k * math.pi / 3
            p = c + x * s * ( half + 1.8 ) + np.array( ( 0.0, math.cos( t ), math.sin( t ) ) ) * ( r * 0.55 )
            P.rod( model, p, p + x * s * 0.4, 0.5, GREY, 6, caps=( False, True ) )
        P.rod( model, c + x * s * ( half + 1.8 ), c + x * s * ( half + 2.4 ), 3.0, GREY, 12, caps=( False, True ) )
    P.rod( model, c - x * half, c + x * half, r * 0.78, "rw_rubber", 24 )
    model.collision_box( ( e - half - 2.4, n - r, z0 ), ( e + half + 2.4, n + r, z0 + d ), "wood" )


def cone( model, e, n, z0 ):
    """ A 750 mm traffic cone: a black square base 380 mm across, the orange cone with two white reflective bands.
    Visual only. """
    import railhead_props as P
    F = P.frame_for( e, n, z0, "+n" )
    _bevel( model, F, ( -7.5, -7.5, 0.0 ), ( 7.5, 7.5, 1.4 ), "rw_black", 0.6 )
    rings = [ ( 1.4, 6.0 ), ( 10.0, 5.0 ), ( 12.0, 4.75 ), ( 17.0, 4.15 ), ( 19.0, 3.9 ), ( 28.3, 1.6 ), ( 29.5, 1.1 ) ]
    paints = [ "rw_cone_orange", "rw_reflective", "rw_cone_orange", "rw_reflective", "rw_cone_orange", "rw_cone_orange" ]
    for ( za, ra ), ( zb, rb ), paint in zip( rings, rings[1:], paints ):
        P._frustum( model, F.p( 0, 0, za ), F.p( 0, 0, zb ), ra, rb, paint, sides=18 )
    P.disc( model, "rw_cone_orange", F.p( 0, 0, 29.5 ), F.z, 1.1, sides=18 )
    F.collide( model, -5.0, 5.0, -5.0, 5.0, 0.0, 29.5, "plastic" )


def bike_rack( model, e, n, along="n", z0=0.0, bays=4 ):
    """ A row of Sheffield stands along along ("n" or "e") from ( e, n ): bays galvanised 48 mm tube hoops, 800 mm
    tall and 700 mm long, a metre apart, each across the row, set in the ground. Visual only. """
    import railhead_props as P
    row = np.array( ( 0.0, 1.0, 0.0 ) ) if along in ( "n", "+n", "-n" ) else np.array( ( 1.0, 0.0, 0.0 ) )
    across = np.array( ( row[1], row[0], 0.0 ) )
    base = np.array( ( e, n, z0 ) )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    for k in range( bays ):
        o = base + row * 39.4 * k
        pts = [ o - across * 13.8 - up * 0.5, o - across * 13.8 + up * 21.7 ]
        pts += [ o - across * 13.8 * math.cos( j / 10 * math.pi ) + up * ( 21.7 + 9.8 * math.sin( j / 10 * math.pi ) )
                 for j in range( 1, 10 ) ]
        pts += [ o + across * 13.8 + up * 21.7, o + across * 13.8 - up * 0.5 ]
        P.polyline( model, pts, 0.95, GALV, 10 )
    # One box round the row of hoops.
    ends = [ base - across * 14.8, base + across * 14.8 + row * 39.4 * ( bays - 1 ) ]
    lo = np.minimum( *ends ) - row * 1.0
    hi = np.maximum( *ends ) + row * 1.0 + up * 31.5
    model.collision_box( lo, hi, "metal" )


# ---------------------------------------------------------------------------------------------------------------------
# Vehicles' and containers' details, lights, help points

def corrugated( model, F, axis, at, out, a0, a1, z0, z1, paint, inside=None, pitch=10.9, depth=1.4 ):
    """ A trapezoidal corrugated steel wall in frame F: on the plane x = at (axis "x", running along y from a0 to a1)
    or y = at (axis "y", running along x), its outer flats facing out (the sign along that axis), pressed in depth
    every pitch: an ISO container's side wall (278 mm pitch, 36 mm deep). inside: a paint for its inner face (flat),
    or None. """
    import railhead_props as P
    span = a1 - a0
    count = max( 1, int( round( span / pitch ) ) )
    pitch = span / count
    flat_o, slope = 0.27 * pitch, 0.22 * pitch
    def pt( u, d, z ):
        return ( at - out * d, u, z ) if axis == "x" else ( u, at - out * d, z )
    normal_out = ( out, 0, 0 ) if axis == "x" else ( 0, out, 0 )
    for k in range( count ):
        u = a0 + k * pitch
        stations = [ ( u, 0.0 ), ( u + flat_o, 0.0 ), ( u + flat_o + slope, depth ),
                     ( u + pitch - slope, depth ), ( u + pitch, 0.0 ) ]
        for ( ua, da ), ( ub, db ) in zip( stations, stations[1:] ):
            # The face's normal: out, tipped along u where it slopes.
            du, dd = ub - ua, db - da
            tip = dd / du if abs( du ) > 1e-6 else 0.0
            towards = ( out, tip, 0 ) if axis == "x" else ( tip, out, 0 )
            P._fpoly( model, F, paint, [ pt( ua, da, z0 ), pt( ub, db, z0 ), pt( ub, db, z1 ), pt( ua, da, z1 ) ],
                      towards )
    if inside:
        back = depth + 0.6
        P._fpoly( model, F, inside, [ pt( a0, back, z0 ), pt( a1, back, z0 ), pt( a1, back, z1 ), pt( a0, back, z1 ) ],
                  tuple( -v for v in normal_out ) )


def taxi_sign( model, F, y, roof ):
    """ A taxi's roof sign on a car's frame F at depth y, the roof's top at roof. """
    import railhead_props as P
    z0 = roof - 0.3
    for x in ( -5.0, 5.0 ):
        P.rod( model, F.p( x, y, z0 ), F.p( x, y, z0 + 0.6 ), 1.4, "rw_black", 10, caps=( False, True ) )
    _bevel( model, F, ( -7.9, y - 2.4, z0 + 0.6 ), ( 7.9, y + 2.4, z0 + 5.1 ), "rw_taxi_sign", 0.5 )
    for s_, face in ( ( 1.0, "front" ), ( -1.0, "back" ) ):
        F.quad( model, "rw_prop_signs", 0.0, y + s_ * 2.43, z0 + 2.85, 14.2, 3.4, face, uv=_sign_uv( "taxi" ) )


def platform_batten( model, e, n, z_top, along="n", length=59.0 ):
    """ See railhead_props.platform_batten. """
    import railhead_props as P
    F = P.frame_for( e, n, 0.0, "+e" if along in ( "n", "+n", "-n" ) else "+n" )
    hl = length / 2
    zb = z_top - 14.0                 # the batten hangs 350 mm under its fixing
    # The body: a chamfered aluminium extrusion, the opal lens along its underside, the end caps.
    prof = [ ( -1.48, zb ), ( 1.48, zb ), ( 1.48, zb + 1.6 ), ( 1.0, zb + 2.36 ), ( -1.0, zb + 2.36 ), ( -1.48, zb + 1.6 ) ]
    # _side_prism takes a profile in ( y, z ): the batten runs along the frame's x.
    P._side_prism( model, F, prof, -hl, hl, lambda k: ALU, ALU )
    _fp = [ ( -hl + 1.2, -1.15, zb - 0.03 ), ( hl - 1.2, -1.15, zb - 0.03 ), ( hl - 1.2, 1.15, zb - 0.03 ),
            ( -hl + 1.2, 1.15, zb - 0.03 ) ]
    P._fpoly( model, F, "rw_lamp_cool", _fp, ( 0, 0, -1 ) )
    for x in ( -hl - 0.15, hl + 0.15 ):
        _bevel( model, F, ( x - 0.4, -1.6, zb - 0.1 ), ( x + 0.4, 1.6, zb + 2.45 ), DARK, 0.15 )
    # The suspension wires and their ceiling canopies.
    for x in ( -hl + 6.0, hl - 6.0 ):
        P.rod( model, F.p( x, 0.0, zb + 2.36 ), F.p( x, 0.0, z_top - 0.8 ), 0.08, GREY, 4 )
        P.rod( model, F.p( x, 0.0, z_top - 0.8 ), F.p( x, 0.0, z_top ), 1.1, ALU, 12, caps=( True, False ) )
    F.collide( model, -hl - 0.6, hl + 0.6, -1.6, 1.6, zb - 0.2, zb + 2.5, "metal" )
    return tuple( float( v ) for v in F.p( 0.0, 0.0, zb - 3.0 ) )


def sos_pillar( model, F ):
    """ See railhead_props.sos_pillar. In frame F, its front towards +y. """
    import railhead_props as P
    BLUE = "rw_train_blue"
    _bevel( model, F, ( -7.0, -6.0, 0.0 ), ( 7.0, 6.0, 0.6 ), GREY, 0.15 )
    _bevel( model, F, ( -4.7, -3.9, 0.6 ), ( 4.7, 3.9, 48.0 ), BLUE, 0.6 )
    # The head: a backlit opal box with the "i" and the SOS plate under it on the front.
    F.box( model, -5.3, 5.3, -4.5, 4.5, 48.0, 62.0, { "default": "rw_kiosk_fascia", "top": ALU, "bottom": ALU } )
    for z0, z1 in ( ( 47.6, 48.6 ), ( 61.5, 62.6 ) ):
        _bevel( model, F, ( -5.6, -4.8, z0 ), ( 5.6, 4.8, z1 ), ALU, 0.2 )
    for face, y, w in ( ( "front", 4.53, 8.0 ), ( "back", -4.53, 8.0 ) ):
        F.quad( model, "rw_prop_signs", 0.0, y, 55.0, w, w, face, uv=_sign_uv( "info_head" ) )
    P._frect( model, F, "rw_prop_signs", -2.6, 2.6, 3.93, 40.0, 45.2, uv=_sign_uv( "sos" ) )
    # The intercom: a speaker grille, the two buttons in their rings, the camera dome.
    for k in range( 5 ):
        P._frect( model, F, "rw_black", -2.2, 2.2, 3.93, 34.0 + 0.9 * k, 34.4 + 0.9 * k )
    for x, paint in ( ( -1.8, BLUE ), ( 1.8, "rw_red_paint" ) ):
        P.rod( model, F.p( x, 3.9, 29.0 ), F.p( x, 4.3, 29.0 ), 1.1, ALU, 14, caps=( False, True ) )
        P.disc( model, paint, F.p( x, 4.32, 29.0 ), F.y, 0.8, sides=14 )
    c = F.p( 0.0, 0.0, 62.6 )
    P.rod( model, c, c + F.z * 0.6, 2.2, DARK, 14, caps=( False, True ) )
    P.disc( model, "rw_black", c + F.z * 0.62, F.z, 1.6, sides=14 )
    F.collide( model, -5.6, 5.6, -4.8, 4.8, 0.0, 62.6, "metal" )
