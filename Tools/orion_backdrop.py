"""
Orion's vista, for Tools/orion_map.py: what's seen round the launch facility past the pad, drawn only (no collision, no
shadows), placed from where the reference picture has it (orion_map's reference camera at REF_EYE looks north).

- The land: level round the facility out to its fences, then hills: on the left of the view a hill with a town of
  pale houses up its slopes and a church on its top; behind the pad, valleys and ridges going back to hazy mountains;
  on the right the radome's hill, its retaining walls and terraces with houses on them, the radome on its lattice ring
  and radio masts with red lamps; a road viaduct across the valley left of the pad. One heightfield (Gaussian hills,
  a ridge ring by bearing, value noise) sampled on polar meshes, painted by slope and distance.
- Trees: holm oaks and pines as rounded clumps and cones over the hills, thinning on the steep and the far.
"""
import math

import numpy as np

import map_kit as K
import orion_parts as OP
import riverdale_parts as P
from riverdale_parts import v, unit, card, box, UP
from veridant_backdrop import vnoise, vfbm, vridged, blob

WORLD = 60000.0
CENTRE = ( 300.0, 1200.0 )
FACILITY = ( -2600.0, 3000.0, -2200.0, 3900.0 )       # level ground (the apron and the courts' surroundings)
EYE = ( 0.0, -560.0 )


def at_bearing( bearing, dist ):
    """ The plan point at bearing (degrees east of north) and distance from the reference camera. """
    b = math.radians( bearing )
    return ( EYE[0] + dist * math.sin( b ), EYE[1] + dist * math.cos( b ) )


TOWN_HILL = at_bearing( -27.0, 8800.0 )          # the hill on the left with the town and the church
RADOME_HILL = ( 4480.0, 8400.0 )
RADOME = ( 4480.0, 8440.0 )
MASTS = [ ( 3850.0, 8300.0, 1500.0 ), ( 5540.0, 8460.0, 2100.0 ), ( 6500.0, 8300.0, 900.0 ) ]
TERRACES = at_bearing( 25.0, 5200.0 )            # the cliffs and retaining walls under the radome hill
VIADUCT = ( at_bearing( -12.0, 6200.0 ), at_bearing( 3.0, 6600.0 ) )

HILLS = [  # ( e, n, height, radius )
    ( TOWN_HILL[0], TOWN_HILL[1], 1300.0, 3000.0 ), ( TOWN_HILL[0] - 2600, TOWN_HILL[1] + 1800, 900.0, 2600.0 ),
    ( RADOME_HILL[0], RADOME_HILL[1], 1080.0, 2300.0 ), ( RADOME_HILL[0] + 2400, RADOME_HILL[1] - 900, 820.0, 2200.0 ),
    ( TERRACES[0] + 300, TERRACES[1] + 600, 520.0, 1500.0 ),
    ( -7000.0, 2600.0, 700.0, 2800.0 ), ( 7800.0, 3200.0, 650.0, 3000.0 ), ( -5200.0, -4200.0, 600.0, 3000.0 ),
    ( 6000.0, -4800.0, 650.0, 3200.0 ), ( 0.0, -7000.0, 700.0, 3600.0 ), ( 1500.0, 11000.0, 900.0, 3500.0 ),
    ( -3500.0, 12500.0, 1300.0, 4000.0 ),
]


# The picture's skyline, degrees above the eye by bearing from it (measured along the hills between the masts), and
# round the rest of the horizon a gentle ring of hills.
SKYLINE = ( ( -180.0, 4.5 ), ( -90.0, 5.0 ), ( -40.0, 6.0 ), ( -24.6, 6.1 ), ( -22.7, 5.6 ), ( -19.2, 4.7 ), ( -17.1, 4.3 ),
            ( -11.7, 4.0 ), ( -10.0, 3.4 ), ( -9.5, 3.2 ), ( -6.7, 3.8 ), ( -5.0, 3.9 ), ( -3.9, 4.2 ), ( -2.7, 4.1 ),
            ( -1.0, 3.4 ), ( 0.7, 2.9 ), ( 3.0, 2.8 ), ( 6.4, 2.6 ), ( 12.0, 3.2 ), ( 18.4, 3.8 ), ( 21.4, 4.7 ),
            ( 23.3, 4.3 ), ( 25.2, 4.4 ), ( 29.7, 4.9 ), ( 33.1, 4.9 ), ( 60.0, 5.0 ), ( 90.0, 5.0 ), ( 180.0, 4.5 ) )
EYE_Z = 400.0


def skyline( bearing_deg ):
    keys = np.array( [ b for b, _ in SKYLINE ] )
    return np.interp( ( np.asarray( bearing_deg ) + 180.0 ) % 360.0 - 180.0, keys, np.array( [ e for _, e in SKYLINE ] ) )


def rect_distance( E, N, rect ):
    x0, x1, y0, y1 = rect
    dx = np.maximum( np.maximum( x0 - E, E - x1 ), 0.0 )
    dy = np.maximum( np.maximum( y0 - N, N - y1 ), 0.0 )
    return np.hypot( dx, dy )


def height( E, N ):
    E, N = np.asarray( E, float ), np.asarray( N, float )
    z = np.zeros( np.shape( E ) )
    for he, hn, hh, hr in HILLS:
        d2 = ( ( E - he ) ** 2 + ( N - hn ) ** 2 ) / ( hr * hr )
        z = np.maximum( z, hh * np.exp( -d2 * 1.4 ) )
    # Rolling ground between the hills.
    z = z + 180.0 * ( vfbm( E, N, 4200.0, 4, 31 ) + 0.4 )
    # The far hills: past 15000 the land rises so that, seen from the overlook, its ridges climb to the picture's
    # skyline (SKYLINE) at the far edge, in layers: rounded ridges from smoothed ridged noise, hazier with distance.
    R = np.hypot( E - CENTRE[0], N - CENTRE[1] )
    De = np.hypot( E - EYE[0], N - EYE[1] )
    be = np.degrees( np.arctan2( E - EYE[0], N - EYE[1] ) )
    rise = np.clip( ( R - 15000.0 ) / 17000.0, 0.0, 1.0 )
    rise = rise * rise * ( 3 - 2 * rise )
    ridge = 0.78 + 0.22 * vridged( E, N, 7000.0, 3, 91 ) + 0.06 * vfbm( E, N, 2600.0, 3, 77 )
    target = EYE_Z + De * np.tan( np.radians( skyline( be ) ) )
    z = np.maximum( z, rise * target * ridge )
    # Small-scale relief on the hills.
    z = z + 70.0 * vfbm( E, N, 900.0, 3, 53 ) * np.clip( z / 400.0, 0, 1 )
    # Level round the facility, rising behind its fences.
    d = rect_distance( E, N, FACILITY )
    fade = np.clip( d / 1800.0, 0.0, 1.0 ) ** 1.5
    z = z * fade
    return z


def terrain( m ):
    """ The land as polar meshes round the facility, finer near, coarser far, shaded smooth from the field's slopes, each
    quad painted by its slope and distance. Quads inside the facility (which has its own ground) aren't drawn. """
    rng = np.random.default_rng( 9 )
    spots = []
    x0, x1, y0, y1 = FACILITY
    for radii, na in ( ( np.linspace( 2600, 11000, 70 ), 480 ), ( np.concatenate( [ [ 11000.0 ], np.geomspace( 11400, WORLD * 0.98, 60 ) ] ), 320 ) ):
        angles = np.linspace( 0, 2 * math.pi, na, endpoint=False )
        Rg, A = np.meshgrid( radii, angles, indexing="ij" )
        E = CENTRE[0] + Rg * np.sin( A )
        N = CENTRE[1] + Rg * np.cos( A )
        Z = height( E, N )
        inside = ( E > x0 + 400 ) & ( E < x1 - 400 ) & ( N > y0 + 400 ) & ( N < y1 - 400 )
        Z = np.where( inside, -40.0, Z )
        P3 = np.stack( [ E, N, Z ], axis=-1 )
        tr = np.zeros_like( P3 )
        tr[1:-1] = P3[2:] - P3[:-2]
        tr[0] = P3[1] - P3[0]
        tr[-1] = P3[-1] - P3[-2]
        ta = np.roll( P3, -1, axis=1 ) - np.roll( P3, 1, axis=1 )
        nrm = np.cross( ta, tr )
        nrm = nrm * np.where( nrm[..., 2:3] < 0, -1.0, 1.0 )
        nrm = nrm / np.maximum( np.linalg.norm( nrm, axis=-1, keepdims=True ), 1e-9 )
        for i in range( len( radii ) - 1 ):
            for j in range( na ):
                j1 = ( j + 1 ) % na
                corners = ( ( i, j ), ( i, j1 ), ( i + 1, j1 ), ( i + 1, j ) )
                if all( inside[c] for c in corners ):
                    continue
                quad = [ v( E[c], N[c], Z[c] ) for c in corners ]
                normals = [ nrm[c] for c in corners ]
                qn = unit( sum( normals ) )
                rc = ( radii[i] + radii[i + 1] ) / 2
                zc = sum( Z[c] for c in corners ) / 4
                if rc > 22000:
                    paint = "oa_mountain"
                elif qn[2] < 0.7:
                    paint = "oa_rock" if rc < 12000 else "oa_rock_far"
                elif rc < 12000:
                    pick = math.sin( E[i, j] / 900.0 + 1.3 ) * math.cos( N[i, j] / 760.0 ) + 0.6 * math.sin( ( E[i, j] + N[i, j] ) / 430.0 ) + rng.normal( 0, 0.35 )
                    paint = "oa_tree_far" if pick > -0.35 else ( "oa_scrub" if pick > -0.9 else "oa_hill" )
                    if zc > 60 and qn[2] > 0.8:
                        spots.append( ( float( np.mean( [ q[0] for q in quad ] ) ), float( np.mean( [ q[1] for q in quad ] ) ), zc, rc ) )
                else:
                    paint = "oa_grass_far" if ( math.sin( E[i, j] / 2100.0 ) * math.cos( N[i, j] / 1700.0 ) + rng.normal( 0, 0.3 ) ) > -0.25 else "oa_tree_far"
                card( m, paint, quad, sum( normals ), normals=normals )
    return spots


def trees( m, spots, rng, count=1100 ):
    """ Holm oaks and pines in clumps on the hills: rounded crowns and dark cones, more in the hollows and on the town
    hill's flanks, fewer far off. """
    placed = 0
    for e, n, z, rc in spots:
        density = 0.55 * ( 1.0 - np.clip( ( rc - 4000.0 ) / 9000.0, 0, 0.85 ) )
        if math.sin( e / 1300.0 + 0.4 ) * math.cos( n / 1100.0 ) + 0.5 * math.sin( ( e - n ) / 600.0 ) < -0.35:
            density *= 0.25
        # Thin behind the pad, where the picture looks down a hazy valley.
        bearing = math.degrees( math.atan2( e - EYE[0], n - EYE[1] ) )
        if -14.0 < bearing < 17.0 and math.hypot( e - EYE[0], n - EYE[1] ) < 11000:
            density *= 0.18
        if rng.random() > density:
            continue
        for _ in range( int( rng.integers( 1, 4 ) ) ):
            if placed >= count:
                return placed
            ee, nn = e + rng.uniform( -90, 90 ), n + rng.uniform( -90, 90 )
            zz = float( height( np.array( [ ee ] ), np.array( [ nn ] ) )[0] )
            r = rng.uniform( 40, 85 ) * ( 1.0 + rc / 20000.0 )
            blob( m, ( ee, nn, zz ), r, r * rng.uniform( 0.7, 0.95 ), "oa_tree" if rng.random() < 0.6 else "oa_pine", rng )
            placed += 1
    return placed


def window_grid( m, centre, right, w, h, rows, cols, rng, lit=0.35 ):
    right = unit( right )
    for r_ in range( rows ):
        for c_ in range( cols ):
            x = ( c_ + 0.5 ) / cols - 0.5
            y = ( r_ + 0.5 ) / rows - 0.5
            p = v( *centre ) + right * ( x * w ) + UP * ( y * h )
            P.quad( m, "oa_window_lit" if rng.random() < lit else "oa_window_dark", p, right, UP, w / cols * 0.4, h / rows * 0.48, off=0.6 )


def house( m, c, size, yaw, z, rng, roof="tiles", lit=0.3, wall="oa_render" ):
    """ A hillside house: rendered walls sunk into the slope, windows (some lit), a tiled hip roof or a flat one. """
    L, W, H = size
    d = v( math.cos( yaw ), math.sin( yaw ), 0 )
    s = np.cross( UP, d )
    base = v( c[0], c[1], z - 60 )
    m.oriented_box( base + UP * ( ( H + 60 ) / 2 ), ( d, s, UP ), ( L, W, H + 60 ), { "default": wall, "-z": None } )
    top = H + 60
    if roof == "tiles":
        rise = W * 0.28
        ridge = [ base + d * ( -L / 2 + W / 2 ) + UP * ( top + rise ), base + d * ( L / 2 - W / 2 ) + UP * ( top + rise ) ]
        corners = [ base + d * sx * L / 2 + s * sy * W / 2 + UP * top for sx, sy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ]
        card( m, "oa_roof_tile", [ corners[0], corners[1], ridge[1], ridge[0] ], -s + UP )
        card( m, "oa_roof_tile", [ corners[2], corners[3], ridge[0], ridge[1] ], s + UP )
        card( m, "oa_roof_tile", [ corners[1], corners[2], ridge[1] ], d + UP )
        card( m, "oa_roof_tile", [ corners[3], corners[0], ridge[0] ], -d + UP )
    else:
        m.oriented_box( base + UP * ( top + 6 ), ( d, s, UP ), ( L + 6, W + 6, 12 ), "oa_roof_dark" )
    floors = max( 1, int( H / 110 ) )
    for outv, width, depth in ( ( s, L, W ), ( -s, L, W ), ( d, W, L ), ( -d, W, L ) ):
        right = np.cross( UP, outv )
        window_grid( m, base + outv * ( depth / 2 ) + UP * ( 60 + H / 2 ), right, width * 0.82, H * 0.8, floors, max( 1, int( width / 100 ) ), rng, lit )


WALLS = [ "oa_render", "oa_render", "oa_render_ochre", "oa_render_grey", "oa_render_pink", "oa_stone" ]


def town( m, rng ):
    """ The town on the left hill's slopes (and a church with a tower on its top), and the houses on the terraces under the
    radome hill. """
    count = 0
    te, tn = TOWN_HILL
    for _ in range( 900 ):
        if count >= 170:
            break
        a = rng.uniform( 0, 2 * math.pi )
        r = 400 + rng.random() ** 0.8 * 2400
        e, n = te + math.cos( a ) * r * 1.0, tn + math.sin( a ) * r * 0.8
        if e > te + 1400:
            continue
        # Facing the facility mostly: the slope towards the camera.
        z = float( height( np.array( [ e ] ), np.array( [ n ] ) )[0] )
        if z < 150 or z > 820:      # on the lower slopes, under the hill's crest (the picture's town sits below its skyline)
            continue
        house( m, ( e, n ), ( rng.uniform( 110, 200 ), rng.uniform( 90, 150 ), rng.uniform( 90, 170 ) ), rng.uniform( -0.4, 0.4 ) + ( 0 if rng.random() < 0.6 else math.pi / 2 ),
               z, rng, "tiles" if rng.random() < 0.65 else "flat", lit=0.12, wall=WALLS[int( rng.integers( len( WALLS ) ) )] )
        count += 1
    # The church on the hilltop: a nave and a square tower with a pyramid cap.
    ze = float( height( np.array( [ te ] ), np.array( [ tn ] ) )[0] )
    house( m, ( te, tn ), ( 520, 220, 300 ), 0.3, ze, rng, "tiles", lit=0.0, wall="oa_stone" )
    tw = v( te + 260 * math.cos( 0.3 ), tn + 260 * math.sin( 0.3 ), 0 )
    box( m, tw[0] - 70, tw[0] + 70, tw[1] - 70, tw[1] + 70, ze - 40, ze + 620, "oa_stone" )
    P.lathe( m, ( tw[0], tw[1] ), [ ( 99.0, ze + 620 ), ( 0.0, ze + 820 ) ], "oa_roof_tile", 4 )
    # Terraces under the radome hill: retaining walls stepping up, houses and lamp posts on them.
    ce, cn = TERRACES
    for k in range( 5 ):
        f = k / 4
        we, wn = ce + 400 * k, cn + 380 * k
        z = float( height( np.array( [ we ] ), np.array( [ wn ] ) )[0] )
        L = 2200 - 260 * k
        d = unit( v( 1.0, -0.35, 0 ) )
        s = np.cross( UP, d )
        c = v( we, wn, 0 )
        m.oriented_box( c + UP * ( z - 120 + ( 160 + 60 * f ) / 2 ), ( d, s, UP ), ( L, 40, 160 + 60 * f + 240 ), { "default": "oa_wall_dark", "-z": None } )
        m.oriented_box( c + s * 120 + UP * ( z + 40 + 30 * f ), ( d, s, UP ), ( L, 220, 30 ), { "default": None, "+z": "oa_asphalt" } )
        for j in range( 7 - k ):
            q = c + d * ( ( j - ( 6 - k ) / 2 ) * 300 ) + s * ( 220 + rng.uniform( 0, 120 ) )
            zq = float( height( np.array( [ q[0] ] ), np.array( [ q[1] ] ) )[0] )
            house( m, ( q[0], q[1] ), ( rng.uniform( 140, 230 ), rng.uniform( 110, 160 ), rng.uniform( 110, 190 ) ), math.atan2( d[1], d[0] ), max( zq, z + 40 ), rng,
                   "flat" if rng.random() < 0.6 else "tiles", lit=0.3, wall=WALLS[int( rng.integers( len( WALLS ) ) )] )
            count += 1
        for j in range( 4 ):
            q = c + d * ( ( j - 1.5 ) * 500 ) + s * 40
            P.cylinder( m, ( q[0], q[1] ), 4, z + 40, z + 360, "oa_steel", 6 )
            box( m, q[0] - 8, q[0] + 8, q[1] - 6, q[1] + 6, z + 352, z + 366, "oa_lamp_warm" )
    return count


def radome_hill( m, rng ):
    """ The radome on its lattice ring, buildings beside it, the radio masts with red lamps. """
    re, rn = RADOME
    z = float( height( np.array( [ re ] ), np.array( [ rn ] ) )[0] )
    OP.radome( m, ( re, rn, z ), 340.0, 200.0, 16, 40 )
    for k, ( de, dn, L, W, H ) in enumerate( ( ( -600, -200, 420, 240, 220 ), ( 520, -260, 360, 220, 180 ), ( -200, -520, 300, 200, 160 ) ) ):
        q = ( re + de, rn + dn )
        zq = float( height( np.array( [ q[0] ] ), np.array( [ q[1] ] ) )[0] )
        house( m, q, ( L, W, H ), 0.2, zq, rng, "flat", lit=0.4, wall="oa_render_grey" )
    for k, ( e, n, h ) in enumerate( MASTS ):
        zm = float( height( np.array( [ e ] ), np.array( [ n ] ) )[0] )
        # Only the tall lattice mast carries a red lamp on top (the picture's one red light on the right).
        OP.lattice_tower( m, ( e, n, zm ), h, 70 if k else 26, 20 if k else 10, "oa_steel", platforms=( h * 0.85, ), name=f"Radio mast {k}",
                          light=False, beacon=( k == 1 ) )


def viaduct( m ):
    """ A road viaduct across the valley left of the pad: a deck on tall piers with arches between them. """
    ( a_e, a_n ), ( b_e, b_n ) = VIADUCT
    a, b = v( a_e, a_n, 0 ), v( b_e, b_n, 0 )
    d = unit( b - a )
    s = np.cross( UP, d )
    L = float( np.linalg.norm( b - a ) )
    deck_z = 420.0
    spans = 9
    for k in range( spans + 1 ):
        p = a + d * ( L * k / spans )
        zg = float( height( np.array( [ p[0] ] ), np.array( [ p[1] ] ) )[0] )
        m.oriented_box( p + UP * ( ( zg - 60 + deck_z ) / 2 ), ( d, s, UP ), ( 60, 70, deck_z - zg + 60 ), { "default": "oa_stone", "-z": None } )
    m.oriented_box( ( a + b ) / 2 + UP * ( deck_z + 20 ), ( d, s, UP ), ( L, 90, 40 ), "oa_stone" )
    m.oriented_box( ( a + b ) / 2 + s * 42 + UP * ( deck_z + 48 ), ( d, s, UP ), ( L, 6, 16 ), "oa_stone" )
    m.oriented_box( ( a + b ) / 2 - s * 42 + UP * ( deck_z + 48 ), ( d, s, UP ), ( L, 6, 16 ), "oa_stone" )
    for k in range( spans ):
        p0 = a + d * ( L * k / spans )
        for j in range( 6 ):
            t0, t1 = j / 6, ( j + 1 ) / 6
            z0 = deck_z - 30 - 90 * math.sin( math.pi * t0 )
            z1 = deck_z - 30 - 90 * math.sin( math.pi * t1 )
            q0 = p0 + d * ( L / spans * t0 )
            q1 = p0 + d * ( L / spans * t1 )
            for sg in ( -1, 1 ):
                card( m, "oa_stone", [ q0 + s * 35 * sg + UP * z0, q1 + s * 35 * sg + UP * z1, q1 + s * 35 * sg + UP * deck_z, q0 + s * 35 * sg + UP * deck_z ], s * sg )


def build( m ):
    rng = np.random.default_rng( 21 )
    spots = terrain( m )
    trees( m, spots, rng )
    town( m, rng )
    radome_hill( m, rng )
    viaduct( m )
    return m
