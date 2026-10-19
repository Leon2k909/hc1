"""
Road-vehicle and lamp detail for railhead_props (props area, round 2): real glazing set into a lofted body (the panes
12 mm inside the skin, a 20 mm black rubber reveal round each opening, so the pillars stand as body-colour bands),
a car's or van's cab interior seen through it, light units with concave chrome reflector bowls under clear lenses,
flush door grips, stalk mirrors, flared arch lips, mesh grilles, steering wheels and made-up German number plates
hashed from where the vehicle stands. Everything here is visual only: no collision.

Coordinates are a railhead_props.Frame's ( x across, y forward, z up ); a lofted body's depth a runs back from its
front, at y = -a. profile_at( a ) gives the right half's cross-section points ( x, z ), bottom to the roof's centre.
"""
import hashlib
import math

import numpy as np

import railhead_props as P

GLASS = "rw_car_glass"          # tinted laminated glass (railhead_prop_materials)
RUBBER = "rw_rubber"
CLOTH = "rw_car_cloth"
TRIM = "rw_car_trim"
CHROME = "rw_lamp_chrome"
LENS = "rw_lamp_lens"
INSET = 0.47                    # the glass 12 mm inside the skin
RIM = 0.8                       # the rubber surround's 20 mm


# ---------------------------------------------------------------------------------------------------------------------
# Plates

PLATE_LETTERS = "ABCDEFGHJKLMNPRSTUVWXYZ"


def plate_for( e, n, district="HW" ):
    """ A made-up plate of the town's district, two letters and up to three digits, the same every build for a
    vehicle standing at ( e, n ) and different from its neighbours'. """
    h = int( hashlib.md5( f"{round( e )},{round( n )}".encode() ).hexdigest(), 16 )
    a, b = PLATE_LETTERS[h % 23], PLATE_LETTERS[( h // 23 ) % 23]
    number = 1 + ( h // 529 ) % 998
    return f"{district} {a}{b} {number}"


# ---------------------------------------------------------------------------------------------------------------------
# Small world-space shapes

def ring( model, paint, centre, normal, r0, r1, sides=16, up=( 0.0, 0.0, 1.0 ) ):
    """ A flat annulus from r0 to r1 round centre, facing normal. """
    c, n = np.asarray( centre, float ), P._unit( normal )
    u = np.asarray( up, float )
    u = P._unit( u - n * np.dot( u, n ) )
    if np.linalg.norm( u ) < 1e-6:
        u = P._unit( np.cross( n, ( 1.0, 0.0, 0.0 ) ) )
    r = np.cross( u, n )
    for k in range( sides ):
        t0, t1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        d0, d1 = math.cos( t0 ) * r + math.sin( t0 ) * u, math.cos( t1 ) * r + math.sin( t1 ) * u
        P.outward( model, paint, [ c + r0 * d0, c + r1 * d0, c + r1 * d1, c + r0 * d1 ], n )


def bowl_lamp( model, centre, normal, r, depth=0.9, sides=16, rim_paint="rw_alu_brushed", bowl=CHROME,
               emitter="rw_train_headlamp", lens=LENS, rim=0.22 ):
    """ A lamp: a concave reflector bowl of radius r sunk depth behind its rim at centre (facing normal), the emitter
    at its foot, a clear lens over it and a thin rim round it. The bowl's inside shows through the lens. """
    c, n = np.asarray( centre, float ), P._unit( normal )
    back = c - n * depth
    P._frustum( model, c, back, r, r * 0.38, bowl, sides, inside=bowl )
    P.disc( model, emitter, back + n * 0.02, n, r * 0.38, sides=sides )
    P.disc( model, lens, c + n * 0.03, n, r, sides=sides )
    if rim:
        ring( model, rim_paint, c + n * 0.035, n, r, r + rim, sides )


def torus( model, paint, centre, axis, R, r, sides=12, tube=6, up=( 0.0, 0.0, 1.0 ) ):
    """ A ring of tube radius r round a circle of radius R about axis: a steering wheel's rim. """
    c, a = np.asarray( centre, float ), P._unit( axis )
    u = np.asarray( up, float )
    u = P._unit( u - a * np.dot( u, a ) )
    v = np.cross( a, u )
    def pt( i, j ):
        t, s = 2 * math.pi * i / sides, 2 * math.pi * j / tube
        radial = math.cos( t ) * u + math.sin( t ) * v
        return c + ( R + r * math.cos( s ) ) * radial + r * math.sin( s ) * a, \
            math.cos( s ) * radial + math.sin( s ) * a
    for i in range( sides ):
        for j in range( tube ):
            ( p0, n0 ), ( p1, n1 ) = pt( i, j ), pt( i + 1, j )
            ( p2, n2 ), ( p3, n3 ) = pt( i + 1, j + 1 ), pt( i, j + 1 )
            P.outward( model, paint, [ p0, p1, p2, p3 ], n0 + n1 + n2 + n3, normals=[ n0, n1, n2, n3 ] )


def lp( F, x, y, z ):
    return F.p( x, y, z )


# ---------------------------------------------------------------------------------------------------------------------
# Glazing set into a lofted body

def _seg_normal( p, q ):
    nx, nz = q[1] - p[1], -( q[0] - p[0] )
    length = math.hypot( nx, nz ) or 1.0
    return nx / length, nz / length


def _inner( prof, k0, k1, inset, rim, shrink_top ):
    """ The glass's edge points ( x, z ) across segments k0..k1 of a cross-section: each point inset along its
    neighbours' mean normal, the first moved rim up the opening and the last down it (unless it's the roof's centre),
    a short opening closing to its middle. """
    pts = [ np.asarray( prof[j], float ) for j in range( k0, k1 + 2 ) ]
    normals = [ np.asarray( _seg_normal( pts[j], pts[j + 1] ) ) for j in range( len( pts ) - 1 ) ]
    out = []
    for j, p in enumerate( pts ):
        ns = [ normals[i] for i in ( j - 1, j ) if 0 <= i < len( normals ) ]
        n = sum( ns ) / len( ns )
        n = n / ( np.linalg.norm( n ) or 1.0 )
        out.append( p - n * inset )
    total = sum( np.linalg.norm( pts[j + 1] - pts[j] ) for j in range( len( pts ) - 1 ) )
    if total < 2.2 * rim:
        mid = sum( out ) / len( out )
        return [ mid.copy() for _ in out ], pts
    t0 = P._unit( np.subtract( out[1], out[0] ) )
    out[0] = out[0] + t0 * rim
    if shrink_top:
        t1 = P._unit( np.subtract( out[-1], out[-2] ) )
        out[-1] = out[-1] - t1 * rim
    else:
        out[-1][0] = 0.0
    return out, pts


def window( model, F, profile_at, k0, k1, a0, a1, glass=GLASS, rubber=RUBBER, inset=INSET, rim=RIM, step=5.0,
            stations=() ):
    """ A pane across cross-section segments k0..k1 from depth a0 to a1, set inset behind the opening the loft left
    (paint_at gave those strips None), with the rubber reveal round it on both sides of the body. A pane reaching the
    roof's centre (x 0) meets its other half there with no rubber. """
    a0r, a1r = a0 + rim, a1 - rim
    if a1r - a0r < 0.5:
        return
    n_steps = max( 1, int( math.ceil( ( a1 - a0 ) / step ) ) )
    S = sorted( { a0, a1, a0r, a1r, *[ a0 + ( a1 - a0 ) * i / n_steps for i in range( 1, n_steps ) ],
                  *[ s for s in stations if a0 < s < a1 ] } )
    centre = abs( profile_at( a0 )[k1 + 1][0] ) < 1e-6
    clamp = lambda a: min( max( a, a0r ), a1r )
    cache = {}

    def at( a ):
        if a not in cache:
            prof = profile_at( a )
            cache[a] = _inner( prof, k0, k1, inset, rim, not centre )
        return cache[a]

    G = [ s for s in S if a0r <= s <= a1r ]
    for xs in ( 1.0, -1.0 ):
        X = lambda p, a: ( xs * p[0], -a, p[1] )
        for ga, gb in zip( G, G[1:] ):
            ia, oa = at( ga )
            ib, ob = at( gb )
            for j in range( len( ia ) - 1 ):
                pts = P._clean( [ X( ia[j], ga ), X( ia[j + 1], ga ), X( ib[j + 1], gb ), X( ib[j], gb ) ] )
                if len( pts ) >= 3:
                    nx, nz = _seg_normal( oa[j], oa[j + 1] )
                    P._fpoly( model, F, glass, pts, ( xs * nx, 0, nz ) )
        # The reveals along the opening's foot and head.
        edges = [ 0 ] + ( [] if centre else [ -1 ] )
        for sa, sb in zip( S, S[1:] ):
            _, oa = at( sa )
            _, ob = at( sb )
            ia, ib = at( clamp( sa ) )[0], at( clamp( sb ) )[0]
            for e in edges:
                seg = ( 0, 1 ) if e == 0 else ( -2, -1 )
                nx, nz = _seg_normal( oa[seg[0]], oa[seg[1]] )
                pts = P._clean( [ X( oa[e], sa ), X( ob[e], sb ), X( ib[e], clamp( sb ) ), X( ia[e], clamp( sa ) ) ] )
                if len( pts ) >= 3:
                    P._fpoly( model, F, rubber, pts, ( xs * nx, 0, nz ) )
        # And up its two ends.
        for a, g in ( ( a0, a0r ), ( a1, a1r ) ):
            _, outer = at( a )
            inner, _ = at( g )
            for j in range( len( outer ) - 1 ):
                nx, nz = _seg_normal( outer[j], outer[j + 1] )
                pts = P._clean( [ X( outer[j], a ), X( outer[j + 1], a ), X( inner[j + 1], g ), X( inner[j], g ) ] )
                if len( pts ) >= 3:
                    P._fpoly( model, F, rubber, pts, ( xs * nx, 0, nz ) )


def skin_x( profile_at, a, z ):
    """ The body's half width at depth a and height z (on the loft's own side), for parts laid on it. """
    prof = profile_at( a )
    for ( xa, za ), ( xb, zb ) in zip( prof, prof[1:] ):
        if za <= z <= zb and zb - za > 1e-6:
            return xa + ( xb - xa ) * ( z - za ) / ( zb - za )
    return prof[0][0]


def door_grip( model, F, profile_at, a, z, paint, length=5.9, height=1.2 ):
    """ A flush 150 x 30 mm pull grip at depth a (its middle), height z, in body colour over its dark finger
    recess, on both sides. """
    for xs in ( 1.0, -1.0 ):
        x = skin_x( profile_at, a, z )
        x0, x1 = sorted( ( xs * ( x - 0.05 ), xs * ( x + 0.04 ) ) )
        F.box( model, x0, x1, -a - length / 2 - 0.3, -a + length / 2 + 0.3, z - height / 2 - 0.35, z + height / 2,
               { "default": "rw_black" } )
        x0, x1 = sorted( ( xs * ( x + 0.04 ), xs * ( x + 0.32 ) ) )
        F.box( model, x0, x1, -a - length / 2, -a + length / 2, z - 0.05, z + height / 2 - 0.05, paint )
        x0, x1 = sorted( ( xs * ( x + 0.04 ), xs * ( x + 0.2 ) ) )
        F.box( model, x0, x1, -a + length / 2 - 1.4, -a + length / 2 - 0.2, z - height / 2 + 0.05, z - 0.05,
               "rw_black" )


def stalk_mirror( model, F, xs, a, z, paint, w=7.1, h=4.7, d=2.6, glass="rw_window_dark", reach=1.2, base_x=33.0 ):
    """ A door mirror on a stalk from the A-pillar's foot: a body-colour housing w x h (across, up), its dark glass
    facing back, on a black triangular sail and a short arm. """
    import railhead_buffer as B
    xi = base_x + reach
    xo = xi + w
    lo = ( min( xs * xi, xs * xo ), -a - d / 2, z - h / 2 )
    hi = ( max( xs * xi, xs * xo ), -a + d / 2, z + h / 2 )
    B.bevel_box( model, F, lo, hi, paint, bevel=0.6 )
    P._fpoly( model, F, glass, [ ( xs * ( xi + 0.5 ), -a - d / 2 - 0.05, z - h / 2 + 0.5 ),
                                 ( xs * ( xo - 0.5 ), -a - d / 2 - 0.05, z - h / 2 + 0.5 ),
                                 ( xs * ( xo - 0.5 ), -a - d / 2 - 0.05, z + h / 2 - 0.5 ),
                                 ( xs * ( xi + 0.5 ), -a - d / 2 - 0.05, z + h / 2 - 0.5 ) ], ( 0, -1, 0 ) )
    P._fpoly( model, F, "rw_black", [ ( xs * ( base_x - 0.4 ), -a + 2.5, z - h / 2 - 0.4 ),
                                      ( xs * ( base_x - 0.4 ), -a - 3.0, z - h / 2 - 0.4 ),
                                      ( xs * ( base_x - 0.4 ), -a - 1.0, z + 0.6 ) ], ( xs, 0, 0 ) )
    P.rod( model, F.p( xs * ( base_x - 0.2 ), -a, z - 1.4 ), F.p( xs * ( xi + 0.6 ), -a, z - 1.0 ), 0.55, "rw_black", 6 )


def arch_lip( model, F, profile_at, ac, zc, arch, paint, width=1.0, flare=0.35, steps=16 ):
    """ A flared lip round a wheel arch cut at depth ac (radius arch about height zc): 25 mm proud of the side,
    following it, its edge turned in to the cut. """
    for xs in ( 1.0, -1.0 ):
        for j in range( steps ):
            t0, t1 = math.pi * j / steps, math.pi * ( j + 1 ) / steps
            pts_in, pts_out = [], []
            for t in ( t0, t1 ):
                a_in, z_in = ac - arch * math.cos( t ), zc + arch * math.sin( t )
                a_out, z_out = ac - ( arch + width ) * math.cos( t ), zc + ( arch + width ) * math.sin( t )
                w_in = skin_x( profile_at, a_in, z_in )
                w_out = skin_x( profile_at, a_out, z_out )
                pts_in.append( ( a_in, z_in, w_in ) )
                pts_out.append( ( a_out, z_out, w_out ) )
            face = [ ( xs * ( pts_in[0][2] + flare ), -pts_in[0][0], pts_in[0][1] ),
                     ( xs * ( pts_in[1][2] + flare ), -pts_in[1][0], pts_in[1][1] ),
                     ( xs * ( pts_out[1][2] + 0.02 ), -pts_out[1][0], pts_out[1][1] ),
                     ( xs * ( pts_out[0][2] + 0.02 ), -pts_out[0][0], pts_out[0][1] ) ]
            P._fpoly( model, F, paint, face, ( xs, 0, 0 ) )
            tm = ( t0 + t1 ) / 2
            edge = [ ( xs * ( pts_in[0][2] + flare ), -pts_in[0][0], pts_in[0][1] ),
                     ( xs * ( pts_in[1][2] + flare ), -pts_in[1][0], pts_in[1][1] ),
                     ( xs * ( pts_in[1][2] - 0.6 ), -pts_in[1][0], pts_in[1][1] ),
                     ( xs * ( pts_in[0][2] - 0.6 ), -pts_in[0][0], pts_in[0][1] ) ]
            P._fpoly( model, F, paint, edge, ( 0, math.cos( tm ), -math.sin( tm ) ) )


def mesh_grille( model, F, x0, x1, z0, z1, y, pitch=1.18, r=0.11, back="rw_black", rods="rw_car_trim", frame=None ):
    """ A lower grille: a dark recess behind a mesh of round rods 30 mm apart, facing +y at y, in a frame. """
    F.quad( model, back, ( x0 + x1 ) / 2, y - 0.6, ( z0 + z1 ) / 2, x1 - x0, z1 - z0 )
    for k in range( 1, int( ( z1 - z0 ) / pitch ) + 1 ):
        z = z0 + k * pitch - pitch / 2
        if z < z1:
            P.rod( model, F.p( x0, y - 0.2, z ), F.p( x1, y - 0.2, z ), r, rods, 4 )
    for k in range( 1, int( ( x1 - x0 ) / pitch ) + 1 ):
        x = x0 + k * pitch - pitch / 2
        if x < x1:
            P.rod( model, F.p( x, y - 0.32, z0 ), F.p( x, y - 0.32, z1 ), r, rods, 4 )
    if frame:
        for ( xa, za ), ( xb, zb ) in ( ( ( x0, z0 ), ( x1, z0 ) ), ( ( x1, z0 ), ( x1, z1 ) ), ( ( x1, z1 ), ( x0, z1 ) ),
                                        ( ( x0, z1 ), ( x0, z0 ) ) ):
            P.rod( model, F.p( xa, y, za ), F.p( xb, y, zb ), 0.3, frame, 6 )


def head_cluster( model, F, xs, x_in, x_out, z0, z1, y, lit=False ):
    """ A front light unit on a car's nose (facing +y at y): a black housing with two chrome reflector bowls under a
    clear lens, an LED daytime strip along its top and an amber indicator bowl at its outer end. """
    w = x_out - x_in
    cx, cz = xs * ( x_in + x_out ) / 2, ( z0 + z1 ) / 2
    F.box( model, min( xs * x_in, xs * x_out ), max( xs * x_in, xs * x_out ), y - 0.2, y + 0.15, z0, z1,
           { "default": "rw_rubber" } )
    r = min( ( z1 - z0 ) * 0.36, w * 0.17 )
    for k, f in enumerate( ( 0.3, 0.62 ) ):
        x = xs * ( x_in + w * f )
        bowl_lamp( model, F.p( x, y + 0.45, cz - 0.3 ), F.y, r, depth=0.75, emitter="rw_train_headlamp" if lit else
                   CHROME, rim_paint="rw_steel_dark" )
    bowl_lamp( model, F.p( xs * ( x_in + w * 0.88 ), y + 0.45, cz - 0.3 ), F.y, r * 0.55, depth=0.4,
               emitter="rw_amber_lens", bowl="rw_amber_lens", rim_paint="rw_steel_dark" )
    F.quad( model, "rw_lamp_cool", cx, y + 0.3, z1 - 0.55, w - 1.2, 0.42 )
    # the lens: a clear cover over the unit, its edges turned back to the housing
    xa, xb = sorted( ( xs * ( x_in + 0.2 ), xs * ( x_out - 0.2 ) ) )
    F.box( model, xa, xb, y + 0.15, y + 0.5, z0 + 0.2, z1 - 0.2, { "default": LENS, "back": "rw_black" } )


# ---------------------------------------------------------------------------------------------------------------------
# Interiors

def car_interior( model, F, a_dash, a_screen_top, a_rear, roof_z, belt_z, half, floor_z=13.0, driver=1.0,
                  bench=True, boot=None ):
    """ A car's interior behind its glass: the floor, door cards, a dashboard under the windscreen with its
    binnacle, a 380 mm steering wheel on the driver's side (driver: +1 or -1 in x), two front seats with headrests,
    a rear bench, the dark headlining, and the boot's floor and cover back to a_rear. """
    x = half - 0.6
    F.box( model, -x, x, -a_rear, -a_dash, floor_z - 0.5, floor_z, { "top": CLOTH }, skip=( "bottom", ) )
    for xs in ( 1.0, -1.0 ):              # the door cards, facing in
        P._fpoly( model, F, TRIM, [ ( xs * x, -a_dash, floor_z ), ( xs * x, -a_rear, floor_z ),
                                    ( xs * x, -a_rear, belt_z - 0.5 ), ( xs * x, -a_dash, belt_z - 0.5 ) ], ( -xs, 0, 0 ) )
        P._fpoly( model, F, CLOTH, [ ( xs * ( x - 0.2 ), -a_dash - 6, belt_z - 4.0 ), ( xs * ( x - 0.2 ), -a_rear + 4, belt_z - 4.0 ),
                                     ( xs * ( x - 1.4 ), -a_rear + 4, belt_z - 2.6 ), ( xs * ( x - 1.4 ), -a_dash - 6, belt_z - 2.6 ) ],
                  ( -xs, 0, 1 ) )
    # The headlining.
    hw = half - 5.0
    P._fpoly( model, F, "rw_car_headlining", [ ( -hw, -a_screen_top, roof_z ), ( hw, -a_screen_top, roof_z ), ( hw, -a_rear + 8, roof_z ),
                                 ( -hw, -a_rear + 8, roof_z ) ], ( 0, 0, -1 ) )
    # The dashboard: a wedge under the windscreen's foot, its top sloping back to the cabin, a dark binnacle.
    prof = [ ( a_dash, belt_z - 1.5 ), ( a_dash + 12.0, belt_z - 0.6 ), ( a_dash + 18.0, belt_z - 3.6 ),
             ( a_dash + 20.0, belt_z - 9.0 ), ( a_dash + 17.0, floor_z + 6.0 ), ( a_dash, floor_z + 6.0 ) ]
    for ( pa, pz ), ( qa, qz ) in zip( prof, prof[1:] ):
        P._fpoly( model, F, TRIM, [ ( -x, -pa, pz ), ( x, -pa, pz ), ( x, -qa, qz ), ( -x, -qa, qz ) ],
                  ( 0, qz - pz, qa - pa ) )
    dx = driver * 14.0
    F.box( model, dx - 5.5, dx + 5.5, -a_dash - 18.5, -a_dash - 13.0, belt_z - 1.0, belt_z + 1.6, TRIM )
    F.quad( model, "rw_cab_screen", 0.0, -a_dash - 18.3, belt_z - 5.5, 7.5, 4.0, "back" )
    # The steering wheel: its rim leaning back 25 degrees, its hub and column.
    wc = np.asarray( F.p( dx, -a_dash - 23.5, belt_z - 4.5 ), float )
    axis = P._unit( -F.y * math.cos( math.radians( 25 ) ) - F.z * math.sin( math.radians( 25 ) ) )
    torus( model, TRIM, wc, axis, 7.1, 0.6, sides=12, tube=6 )
    P.disc( model, TRIM, wc - axis * 0.4, -axis, 2.6, sides=12 )
    for t in ( -90, 180, 0 ):
        tt = math.radians( t )
        u = P._unit( F.z - axis * np.dot( F.z, axis ) )
        v = np.cross( axis, u )
        d = math.cos( tt ) * v + math.sin( tt ) * u
        P.rod( model, wc + d * 2.4, wc + d * 6.6, 0.5, TRIM, 4 )
    P.rod( model, wc + axis * 0.3, np.asarray( F.p( dx, -a_dash - 17.0, belt_z - 7.0 ) ), 1.1, TRIM, 6 )
    # Two front seats and a rear bench.
    import railhead_buffer as B
    seats = [ ( driver * 14.0, a_dash + 36.0 ), ( -driver * 14.0, a_dash + 36.0 ) ]
    for sx, sa in seats:
        B.bevel_box( model, F, ( sx - 9.8, -sa - 9.0, floor_z + 2.0 ), ( sx + 9.8, -sa + 9.8, floor_z + 11.0 ), CLOTH,
                     bevel=1.6 )
        B.bevel_box( model, F, ( sx - 9.4, -sa - 12.5, floor_z + 10.0 ), ( sx + 9.4, -sa - 8.5, floor_z + 32.0 ), CLOTH,
                     bevel=1.5 )
        B.bevel_box( model, F, ( sx - 5.0, -sa - 12.2, floor_z + 33.5 ), ( sx + 5.0, -sa - 8.8, floor_z + 39.0 ), CLOTH,
                     bevel=1.2 )
        for k in ( -2.6, 2.6 ):
            P.rod( model, F.p( sx + k, -sa - 10.5, floor_z + 31.5 ), F.p( sx + k, -sa - 10.5, floor_z + 34.0 ), 0.25,
                   "rw_steel_grey", 4 )
    F.box( model, -3.5, 3.5, -a_dash - 44.0, -a_dash - 20.0, floor_z, floor_z + 10.0, TRIM, skip=( "bottom", ) )
    if bench:
        ba = a_dash + 70.0
        B.bevel_box( model, F, ( -x + 1.5, -ba - 8.0, floor_z + 2.0 ), ( x - 1.5, -ba + 9.0, floor_z + 11.5 ), CLOTH,
                     bevel=1.6 )
        B.bevel_box( model, F, ( -x + 1.5, -ba - 12.0, floor_z + 10.0 ), ( x - 1.5, -ba - 8.0, floor_z + 30.0 ), CLOTH,
                     bevel=1.5 )
        for sx in ( -15.0, 0.0, 15.0 ):
            B.bevel_box( model, F, ( sx - 4.5, -ba - 11.6, floor_z + 31.0 ), ( sx + 4.5, -ba - 8.6, floor_z + 35.5 ),
                         CLOTH, bevel=1.0 )
    if boot is not None:
        b0, bz = boot
        F.box( model, -x, x, -a_rear + 2.0, -b0, floor_z, bz, { "top": CLOTH, "front": CLOTH }, skip=( "bottom", ) )
        F.box( model, -x, x, -a_rear + 2.0, -b0, belt_z, belt_z + 0.6, { "default": TRIM } )


def cab_interior( model, F, a_dash, a_back, floor_z, belt_z, roof_z, half, driver=1.0 ):
    """ A van's cab: dashboard, wheel, two seats and the bulkhead behind them (a dark grey steel wall). """
    car_interior( model, F, a_dash, a_dash + 22.0, a_back, roof_z, belt_z, half, floor_z, driver, bench=False )
    x = half - 0.6
    P._fpoly( model, F, "rw_car_trim", [ ( -x, -a_back, floor_z ), ( x, -a_back, floor_z ), ( x, -a_back, roof_z ),
                                         ( -x, -a_back, roof_z ) ], ( 0, 1, 0 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Wheels

def tyre_sidewall( model, F, ac, xs, x, r_in, r_out, zc, outward=1.0, sides=28, dust_from=None ):
    """ A tyre's sidewall ring at x (frame), from r_in to r_out about the hub at depth ac, height zc: matte rubber,
    a ring of raised lettering at 70 % of its height, and brown dust over its lowest third. """
    def p( rad, t, lift=0.0 ):
        return ( xs * ( x + outward * lift ), -( ac + rad * math.cos( t ) ), zc + rad * math.sin( t ) )
    r_mark0 = r_in + ( r_out - r_in ) * 0.62
    r_mark1 = r_in + ( r_out - r_in ) * 0.76
    for k in range( sides ):
        t0, t1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        low = math.sin( ( t0 + t1 ) / 2 ) < -0.5
        paint = "rw_tyre_dust" if low else "rw_tyre"
        for r0, r1 in ( ( r_in, r_mark0 ), ( r_mark1, r_out ) ):
            P._fpoly( model, F, paint, [ p( r0, t0 ), p( r1, t0 ), p( r1, t1 ), p( r0, t1 ) ], ( outward * xs, 0, 0 ) )
        P._fpoly( model, F, paint, [ p( r_mark0, t0 ), p( r_mark1, t0 ), p( r_mark1, t1 ), p( r_mark0, t1 ) ],
                  ( outward * xs, 0, 0 ) )
        if k % 2 == 0 and not low:      # the raised letters: short blocks along the ring
            for f0, f1 in ( ( 0.1, 0.32 ), ( 0.45, 0.62 ), ( 0.74, 0.9 ) ):
                ta, tb = t0 + ( t1 - t0 ) * f0, t0 + ( t1 - t0 ) * f1
                P._fpoly( model, F, "rw_tyre_mark", [ p( r_mark0 + 0.15, ta, 0.08 ), p( r_mark1 - 0.15, ta, 0.08 ),
                                                       p( r_mark1 - 0.15, tb, 0.08 ), p( r_mark0 + 0.15, tb, 0.08 ) ],
                          ( outward * xs, 0, 0 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Bicycles

def bicycle( model, e, n, heading, z0=0.0, kind="city", paint="rw_train_blue", lean=4.0 ):
    """ A bicycle standing on its wheels at ( e, n ) (the bottom bracket over it), heading (degrees from +e,
    anticlockwise, or "+e"/"-e"/"+n"/"-n") the way it points, leaning lean degrees to its left against a stand: kind
    "city" (step-through frame, mudguards, chain guard, rear rack, upright bars) or "trekking" (diamond frame, rack,
    flat bars). 700C wheels, 1.8 m long. Visual only. """
    if isinstance( heading, str ):
        heading = { "+e": 0.0, "+n": 90.0, "-e": 180.0, "-n": 270.0 }[heading]
    h = math.radians( heading )
    fwd = np.array( ( math.cos( h ), math.sin( h ), 0.0 ) )
    left = np.array( ( -math.sin( h ), math.cos( h ), 0.0 ) )
    tilt = math.radians( lean )
    up = np.array( ( 0.0, 0.0, 1.0 ) ) * math.cos( tilt ) + left * math.sin( tilt )
    side = np.cross( fwd, up )
    o = np.array( ( e, n, z0 ) )
    R = 13.6
    P_ = lambda x, z, y=0.0: o + fwd * x + up * z - side * y
    rear, front, bb = P_( -17.3, R ), P_( 24.7, R ), P_( 0.0, 11.0 )
    seat_top, head_top, head_bot = P_( -5.2, 30.0 ), P_( 16.6, 32.5 ), P_( 18.0, 26.0 )
    tube = lambda a, b, r=0.6, paint_=paint: P.rod( model, a, b, r, paint_, 8 )
    # The frame.
    tube( bb, seat_top, 0.65 )
    tube( bb, head_bot if kind == "city" else head_bot, 0.75 )
    if kind == "city":
        tube( P_( 3.0, 14.0 ), P_( 15.5, 27.0 ), 0.6 )
    else:
        tube( seat_top + up * -1.0, head_top + up * -1.5, 0.6 )
    tube( head_bot, head_top, 0.8 )
    for y in ( -2.0, 2.0 ):
        tube( bb + side * -y * 0.5, rear + side * -y, 0.35 )
        tube( seat_top + side * -y * 0.3, rear + side * -y, 0.35 )
        tube( head_bot + side * -y * 0.3, front + side * -y, 0.42, "rw_steel_grey" )
    # The wheels: rims, tyres, 32 spokes as 16 lines each side, hubs.
    for c in ( rear, front ):
        torus( model, "rw_tyre", c, side, R - 0.7, 0.75, sides=24, tube=5, up=up )
        torus( model, "rw_alu_brushed", c, side, R - 1.8, 0.4, sides=24, tube=4, up=up )
        P.rod( model, c - side * 1.8, c + side * 1.8, 0.8, "rw_steel_grey", 8 )
        for k in range( 16 ):
            t = 2 * math.pi * k / 16
            rim = c + ( math.cos( t ) * fwd + math.sin( t ) * up ) * ( R - 2.0 )
            P.rod( model, c + side * ( 1.4 if k % 2 else -1.4 ), rim, 0.06, "rw_steel_grey", 3 )
    # Saddle and post, stem and bars with grips, cranks, pedals, chainring.
    saddle = seat_top + up * 6.5 + fwd * -1.2
    tube( seat_top, saddle, 0.5, "rw_steel_grey" )
    import railhead_buffer as B
    Fs = P.Frame( saddle, ( fwd[0], fwd[1] ) )
    B.bevel_box( model, Fs, ( -3.4, -5.5, 0.0 ), ( 3.4, 4.5, 2.2 ), "rw_black", 0.8 )
    bar = head_top + up * ( 6.0 if kind == "city" else 3.5 ) + fwd * ( -2.5 if kind == "city" else 2.0 )
    tube( head_top, bar, 0.5, "rw_steel_grey" )
    span = 11.0
    ends = [ bar - side * span + fwd * ( -4.0 if kind == "city" else 0.0 ), bar + side * span + fwd * ( -4.0 if kind == "city" else 0.0 ) ]
    for end in ends:
        tube( bar, end, 0.45, "rw_steel_grey" )
        P.rod( model, end, end + ( end - bar ) / np.linalg.norm( end - bar ) * -4.0, 0.62, "rw_black", 8 )
    for s_ in ( -1, 1 ):
        pedal = bb + fwd * 6.5 * s_ + up * 0.0 + side * 3.2 * s_
        P.rod( model, bb + side * 1.8 * s_, pedal, 0.4, "rw_steel_grey", 6 )
        Fp = P.Frame( pedal + side * 1.6 * s_, ( fwd[0], fwd[1] ) )
        B.bevel_box( model, Fp, ( -1.4, -2.0, -0.4 ), ( 1.4, 2.0, 0.4 ), "rw_black", 0.15 )
    P.disc( model, "rw_steel_grey", bb - side * 2.0, -side, 4.2, sides=20 )
    # Chain (a thin dark loop) and, on the city bike, its guard, mudguards and the rear rack with a basket's frame.
    for zz in ( 4.0, -4.0 ):
        P.rod( model, bb - side * 2.1 + up * zz * 0.95, rear - side * 2.1 + up * zz * 0.45, 0.12, "rw_black", 3 )
    if kind == "city":
        cg = [ bb - side * 2.6 + ( math.cos( math.pi * t ) * fwd + math.sin( math.pi * t ) * up ) * 4.8
               for t in np.linspace( 0.0, 1.0, 7 ) ]
        P.polyline( model, cg + [ rear - side * 2.6 + up * 3.0 ], 0.45, "rw_black", 4 )
        for c, a0, a1 in ( ( rear, 0.15, 0.62 ), ( front, 0.5, 0.95 ) ):
            pts = [ c + ( math.cos( math.pi * t ) * fwd + math.sin( math.pi * t ) * up ) * ( R + 1.0 )
                    for t in np.linspace( a0, a1, 7 ) ]
            P.polyline( model, pts, 0.9, paint, 6 )
    rack = [ rear + up * ( R + 3.0 ) + fwd * dx for dx in ( -7.0, 4.0 ) ]
    for y in ( -2.6, 2.6 ):
        P.rod( model, rack[0] - side * y, rack[1] - side * y, 0.3, "rw_black", 6 )
        P.rod( model, rack[1] - side * y, seat_top - side * y * 0.5 + up * -2.0, 0.25, "rw_black", 6 )
        P.rod( model, rack[0] - side * y, rear - side * y + up * -2.0, 0.25, "rw_black", 6 )
