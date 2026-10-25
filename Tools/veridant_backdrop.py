"""
Veridant's backdrop, for Tools/veridant_map.py: what's seen round the resort, drawn only (no collision).

- The sea: Lowtide's water shader over the whole bay, 420 in (10.7 m) under the promenade.
- The headland the picture has on its left: a limestone ridge running out west-north-west from the coast south of
  the resort to a point 15 degrees north of west, 70-95 m high, falling to the sea in pale cliffs, scrub on its top,
  stone pines and cypresses, a walled village and its castle on the summit, a town of white houses and lit windows
  along the shore at its foot, and lights on the quay.
- The bay's far shore: low hazy hills out past the yacht, where the picture has them.
- The superyacht at anchor and sailboats round it, small boats off the town.
- The resort's own hillside: villas, terraces and cypresses on the slopes behind (east, north and south), hills
  rising inland.
The land is one heightfield (a land mask, a distance field off it for the cliffs, noise), sampled on a polar grid
round the map; quads wholly under the sea aren't drawn.
"""
import math

import numpy as np
from scipy import ndimage

import map_kit as K
import riverdale_parts as P
import veridant_parts as VP
from riverdale_parts import v, unit, card, box, obox, rod, UP

SEA_Z = -420.0
WORLD = 60000.0
CELL = 300.0

# The headland's crest (plan) and its height (absolute z) along it, and its half-width.
RIDGE = [ ( -2600.0, -6900.0, 600.0, 3200.0 ), ( -6400.0, -5600.0, 2300.0, 2900.0 ), ( -9800.0, -4300.0, 2700.0, 2700.0 ),
          ( -12900.0, -2900.0, 2850.0, 2500.0 ), ( -15600.0, -1000.0, 2650.0, 2200.0 ), ( -17800.0, 1100.0, 2150.0, 1900.0 ),
          ( -19800.0, 3600.0, 1050.0, 1400.0 ), ( -21400.0, 6100.0, -200.0, 700.0 ) ]
FAR_RIDGE = [ ( -34000.0, 44000.0, 300.0, 7000.0 ), ( -46000.0, 33000.0, 650.0, 8000.0 ), ( -58000.0, 19000.0, 500.0, 7000.0 ) ]
VILLAGE = ( -12700.0, -3000.0 )
TOWN = [ ( -15900.0, 1200.0 ), ( -17400.0, 2600.0 ), ( -18800.0, 4100.0 ), ( -20000.0, 5600.0 ) ]
YACHT = ( -9500.0, 5200.0, 0.32 )          # e, n, heading (radians from east): broadside to the resort
PLAY_RECT = ( -1750.0, 2300.0, -1750.0, 1400.0 )


# The mainland's coastline, south to north: land lies to its east (right). Straight past the resort, turning west to
# the south (the headland's root) and north-east to the north.
COAST = [ ( -60000.0, -45000.0 ), ( -12000.0, -9500.0 ), ( -5200.0, -5200.0 ), ( -2600.0, -3200.0 ), ( -1750.0, -2600.0 ),
          ( -1750.0, 2600.0 ), ( -900.0, 4200.0 ), ( 3000.0, 12000.0 ), ( 12000.0, 30000.0 ), ( 20000.0, 60000.0 ) ]


def coast_e( n ):
    """ The coast's e at n (along COAST). """
    n = np.asarray( n, float )
    es = [ e for e, _ in COAST ]
    ns = [ nn for _, nn in COAST ]
    return np.interp( n, ns, es )


def coast_distance( E, N ):
    """ Signed distance to the coastline: positive inland. """
    best = np.full( np.shape( E ), np.inf )
    side = np.zeros( np.shape( E ) )
    for ( e0, n0 ), ( e1, n1 ) in zip( COAST, COAST[1:] ):
        de, dn = e1 - e0, n1 - n0
        L2 = de * de + dn * dn
        t = np.clip( ( ( E - e0 ) * de + ( N - n0 ) * dn ) / L2, 0.0, 1.0 )
        d = np.hypot( E - ( e0 + de * t ), N - ( n0 + dn * t ) )
        cross = de * ( N - n0 ) - dn * ( E - e0 )
        closer = d < best
        best = np.where( closer, d, best )
        side = np.where( closer, cross, side )
    return np.where( side < 0, best, -best )


def fbm( rng, size, octaves=6, base=4 ):
    out = np.zeros( ( size, size ), np.float32 )
    amp, total, cells = 1.0, 0.0, base
    for _ in range( octaves ):
        grid = rng.standard_normal( ( cells + 3, cells + 3 ) ).astype( np.float32 )
        up = ndimage.zoom( grid, ( size + 3 * size / cells ) / ( cells + 3 ), order=3 )
        out += amp * up[:size, :size]
        total += amp
        amp *= 0.5
        cells *= 2
    return out / total


def _hash( ix, iy, seed ):
    h = ( ix * 374761393 + iy * 668265263 + seed * 1442695041 ) & 0xFFFFFFFF
    h = ( ( h ^ ( h >> 13 ) ) * 1274126177 ) & 0xFFFFFFFF
    h = h ^ ( h >> 16 )
    return ( h & 0xFFFF ).astype( np.float64 ) / 32767.5 - 1.0


def vnoise( E, N, scale, seed, turn=0.0 ):
    """ Value noise (-1..1) with features scale across, its lattice turned by turn radians. """
    c, s_ = math.cos( turn ), math.sin( turn )
    x = ( E * c - N * s_ ) / scale
    y = ( E * s_ + N * c ) / scale
    ix, iy = np.floor( x ), np.floor( y )
    fx, fy = x - ix, y - iy
    ix, iy = ix.astype( np.int64 ), iy.astype( np.int64 )
    ux, uy = fx * fx * ( 3 - 2 * fx ), fy * fy * ( 3 - 2 * fy )
    a, b = _hash( ix, iy, seed ), _hash( ix + 1, iy, seed )
    cc, d = _hash( ix, iy + 1, seed ), _hash( ix + 1, iy + 1, seed )
    return a + ( b - a ) * ux + ( cc - a ) * uy + ( a - b - cc + d ) * ux * uy


def vnoise3( E, N, Z, scale, seed ):
    """ Value noise (-1..1) in three dimensions, features scale across. """
    x, y, z = E / scale, N / scale, Z / scale
    ix, iy, iz = np.floor( x ), np.floor( y ), np.floor( z )
    fx, fy, fz = x - ix, y - iy, z - iz
    ix, iy, iz = ix.astype( np.int64 ), iy.astype( np.int64 ), iz.astype( np.int64 )
    ux, uy, uz = fx * fx * ( 3 - 2 * fx ), fy * fy * ( 3 - 2 * fy ), fz * fz * ( 3 - 2 * fz )

    def h( dx, dy, dz ):
        return _hash( ix + dx, iy + dy + ( iz + dz ) * 7919, seed )

    c00 = h( 0, 0, 0 ) + ( h( 1, 0, 0 ) - h( 0, 0, 0 ) ) * ux
    c10 = h( 0, 1, 0 ) + ( h( 1, 1, 0 ) - h( 0, 1, 0 ) ) * ux
    c01 = h( 0, 0, 1 ) + ( h( 1, 0, 1 ) - h( 0, 0, 1 ) ) * ux
    c11 = h( 0, 1, 1 ) + ( h( 1, 1, 1 ) - h( 0, 1, 1 ) ) * ux
    c0 = c00 + ( c10 - c00 ) * uy
    c1 = c01 + ( c11 - c01 ) * uy
    return c0 + ( c1 - c0 ) * uz


def vfbm3( E, N, Z, scale, octaves, seed ):
    E, N, Z = np.asarray( E, float ), np.asarray( N, float ), np.asarray( Z, float )
    total, amp, norm = np.zeros( np.shape( E ) ), 1.0, 0.0
    for o in range( octaves ):
        c, s_ = math.cos( 0.7 * o ), math.sin( 0.7 * o )
        total = total + amp * vnoise3( E * c - N * s_, E * s_ + N * c, Z, scale / 2 ** o, seed + 11 * o )
        norm += amp
        amp *= 0.5
    return total / norm


def vfbm( E, N, scale, octaves, seed, gain=0.5 ):
    E, N = np.asarray( E, float ), np.asarray( N, float )
    total, amp, norm = np.zeros( np.shape( E ) ), 1.0, 0.0
    for o in range( octaves ):
        total = total + amp * vnoise( E, N, scale / 2 ** o, seed + 7 * o, turn=0.61 * o )
        norm += amp
        amp *= gain
    return total / norm


def vridged( E, N, scale, octaves, seed ):
    """ Ridged multifractal (0..1): sharp crests between rounded hollows, each octave weighted by the last, so the
    crests carry the fine detail and the gullies stay smooth. """
    E, N = np.asarray( E, float ), np.asarray( N, float )
    total, amp, norm, w = np.zeros( np.shape( E ) ), 1.0, 0.0, np.ones( np.shape( E ) )
    for o in range( octaves ):
        n = 1.0 - np.abs( vnoise( E, N, scale / 2 ** o, seed + 13 * o, turn=0.83 * o + 0.3 ) )
        n = n * n * w
        w = np.clip( n * 1.8, 0.0, 1.0 )
        total = total + amp * n
        norm += amp
        amp *= 0.55
    return total / norm


def smoothstep01( a, b, x ):
    t = np.clip( ( x - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def rect_distance( E, N, rect ):
    x0, x1, y0, y1 = rect
    dx = np.maximum( np.maximum( x0 - E, E - x1 ), 0.0 )
    dy = np.maximum( np.maximum( y0 - N, N - y1 ), 0.0 )
    return np.hypot( dx, dy )


def ridge_field( E, N, ridge ):
    """ For each point: the distance to the polyline, the ridge height and half-width there (interpolated). """
    best = np.full( E.shape, np.inf )
    height = np.zeros( E.shape )
    half = np.ones( E.shape )
    for ( e0, n0, z0, w0 ), ( e1, n1, z1, w1 ) in zip( ridge, ridge[1:] ):
        de, dn = e1 - e0, n1 - n0
        L2 = de * de + dn * dn
        t = np.clip( ( ( E - e0 ) * de + ( N - n0 ) * dn ) / L2, 0.0, 1.0 )
        d = np.hypot( E - ( e0 + de * t ), N - ( n0 + dn * t ) )
        closer = d < best
        best = np.where( closer, d, best )
        height = np.where( closer, z0 + ( z1 - z0 ) * t, height )
        half = np.where( closer, w0 + ( w1 - w0 ) * t, half )
    return best, height, half


class Land:
    """ The land's height (absolute z) anywhere, from the coastline's and the ridges' distances and noise. """

    def __init__( self, seed=11 ):
        rng = np.random.default_rng( seed )
        size = int( 2 * WORLD / CELL ) + 1
        self.size = size
        self.noise = fbm( rng, size, 7, 6 )
        self.fine = fbm( rng, size, 5, 40 )
        # Ridged noise for the headland's rock: sharp crests and gullies a few hundred feet across, and a finer
        # crag noise for its buttresses and ledges.
        self.ridged = 1.0 - np.abs( fbm( rng, size, 5, 30 ) ) * 2.0
        self.crags = 1.0 - np.abs( fbm( rng, size, 4, 120 ) ) * 2.0

    def sample( self, field, E, N ):
        i = ( np.asarray( E, float ) + WORLD ) / CELL
        j = ( np.asarray( N, float ) + WORLD ) / CELL
        shape = np.shape( i )
        out = ndimage.map_coordinates( field, [ np.ravel( i ), np.ravel( j ) ], order=1, mode="nearest" )
        return out.reshape( shape )

    def parts( self, E, N ):
        E, N = np.asarray( E, float ), np.asarray( N, float )
        d_main = coast_distance( E, N )
        dist_r, ridge_z, ridge_w = ridge_field( E, N, RIDGE )
        dist_f, far_z, far_w = ridge_field( E, N, FAR_RIDGE )
        return d_main, ( dist_r, ridge_z, ridge_w ), ( dist_f, far_z, far_w )

    def at( self, E, N ):
        E, N = np.atleast_1d( np.asarray( E, float ) ), np.atleast_1d( np.asarray( N, float ) )
        noise, fine = self.sample( self.noise, E, N ), self.sample( self.fine, E, N )
        ridged = self.sample( self.ridged, E, N )
        crags = self.sample( self.crags, E, N )
        d_main, ( dist_r, ridge_z, ridge_w ), ( dist_f, far_z, far_w ) = self.parts( E, N )
        # Mainland: a cliff from the sea up to the coast's top (0 by the resort, higher south and north of it), then
        # rising inland into hills.
        coast_top = np.clip( np.maximum( 0, np.abs( N + 200 ) - 3400 ) * 0.22, 0.0, 1800.0 )
        cliff = 1.0 - ( 1.0 - np.clip( d_main / 420.0, 0, 1 ) ) ** 3
        inland = np.maximum( 0.0, d_main - 2500.0 ) * 0.07 + np.maximum( 0.0, d_main - 12000.0 ) * 0.06
        z_main = SEA_Z + ( coast_top - SEA_Z ) * cliff + inland + ( noise * 900 + fine * 120 ) * np.clip( ( d_main - 2000 ) / 6000, 0, 1 )
        # Offshore the shore keeps falling at the cliff's own slope a little way, so the waterline runs smooth across
        # the mesh instead of in steps, then flattens to the sea floor.
        z_main = np.where( d_main > 0, z_main, SEA_Z + np.maximum( 3.0 * d_main, -160.0 ) - np.minimum( -d_main * 0.08, 900.0 ) )
        # The headland: steep sea cliffs, a rounded back to the crest.
        x = np.clip( dist_r / np.maximum( ridge_w, 1.0 ), 0.0, 1.0 )
        prof = ( 1.0 - x ** 2 ) ** 0.45
        edge = np.clip( ( ridge_w - dist_r ) / 260.0, 0.0, 1.0 )
        summit = 420.0 * np.exp( -( ( E - VILLAGE[0] ) ** 2 + ( N - VILLAGE[1] ) ** 2 ) / ( 2 * 1500.0 ** 2 ) )
        z_head = SEA_Z + ( ridge_z + summit - SEA_Z ) * prof * ( 0.25 + 0.75 * edge ) + ( noise * 240 + fine * 100 ) * prof
        # Ribs and gullies down its flanks, crags on the ribs, and the limestone's beds as ledges, from noise fine
        # enough to show at the mesh's spacing.
        inside = dist_r < ridge_w * 1.08
        if np.any( inside ):
            Ei, Ni = E[inside], N[inside]
            pi_ = prof[inside]
            gully = vridged( Ei, Ni, 2600.0, 4, 101 )
            crag = vridged( Ei, Ni, 900.0, 3, 202 )
            lumps = vfbm( Ei, Ni, 520.0, 3, 303 )
            # Rounded limestone bosses (the picture's outcrops), the maquis filling the hollows between them.
            boss = np.maximum( vfbm( Ei, Ni, 1500.0, 3, 707 ), 0.0 )
            # The sea-facing cliffs are more fractured than the smoother hilltop.
            # Keep the village plateau nearly unchanged so its walls and buildings
            # remain seated, while producing silhouette-breaking buttresses below it.
            cliff_face = np.clip( ( 0.94 - pi_ ) / 0.62, 0.0, 1.0 )
            fissures = vridged( Ei, Ni, 720.0, 3, 911 )
            zi = z_head[inside] + ( gully - 0.42 ) * 300.0 * pi_ ** 0.6 + ( crag - 0.42 ) * 150.0 * np.clip( pi_ * 2.5, 0, 1 ) \
                + lumps * 60.0 * pi_ + boss ** 1.2 * 460.0 * np.clip( pi_ * 2.0, 0, 1 ) \
                + ( fissures - 0.42 ) * 165.0 * cliff_face
            band = 150.0
            t = ( zi - SEA_Z ) / band
            ledges = SEA_Z + band * ( np.floor( t ) + smoothstep01( 0.15, 0.85, t - np.floor( t ) ) )
            z_head[inside] = zi + ( ledges - zi ) * 0.26 * cliff_face
        z_head = np.where( dist_r < ridge_w, np.maximum( z_head, SEA_Z + 4 ), SEA_Z - 3.0 * ( dist_r - ridge_w ) )
        xf = np.clip( dist_f / np.maximum( far_w, 1.0 ), 0, 1 )
        z_far = np.where( dist_f < far_w, SEA_Z + ( far_z - SEA_Z ) * ( 1 - xf ** 2 ) ** 0.7 + noise * 300, -1e9 )
        z = np.maximum( np.maximum( z_main, z_head ), z_far )
        # The resort's surroundings: level with its ground at its walls, rising behind them in garden terraces into
        # the hillside, so what shows over the walls from the terraces is slope and trees, not a flat field.
        d_rect = rect_distance( E, N, PLAY_RECT )
        rise = 0.17 * np.maximum( d_rect - 140.0, 0.0 ) + 0.00003 * np.maximum( d_rect - 140.0, 0.0 ) ** 2
        rise = rise + 70.0 * vfbm( E, N, 1400.0, 3, 404 ) * np.clip( ( d_rect - 300.0 ) / 1500.0, 0, 1 )
        step = 54.0
        tr = rise / step
        rise = rise + ( step * ( np.floor( tr ) + smoothstep01( 0.35, 0.65, tr - np.floor( tr ) ) ) - rise ) * 0.6
        near = ( d_main > 0 ) & ( d_rect < 6000.0 )
        z = np.where( near, np.where( d_rect > 0, np.maximum( np.minimum( z, rise + 400.0 ), rise ), 0.0 ), z )
        return z

    def is_land( self, e, n ):
        d_main, ( dist_r, _, ridge_w ), ( dist_f, _, far_w ) = self.parts( np.atleast_1d( e ), np.atleast_1d( n ) )
        return bool( ( d_main > 0 ) | ( dist_r < ridge_w ) | ( dist_f < far_w ) )

    def is_headland( self, e, n ):
        _, ( dist_r, _, ridge_w ), _ = self.parts( np.atleast_1d( e ), np.atleast_1d( n ) )
        return bool( dist_r[0] < ridge_w[0] )


def terrain( m, land, centre=( 75.0, -100.0 ) ):
    """ The land as polar meshes round the map, finer near (every 125 in out to 9000, 720 round) and coarser beyond
    (360 round), shaded smooth from the heightfield's own slopes. Each triangle painted by its slope and distance:
    pale cliff where it's steep (tinted darker far off), scrub on gentle ground, far land beyond 30000. """
    count = 0
    x0, x1, y0, y1 = PLAY_RECT
    rng = np.random.default_rng( 9 )
    for radii, na in ( ( np.linspace( 1400, 9000, 62 ), 540 ), ( np.concatenate( [ [ 9000.0 ], np.geomspace( 9300, WORLD * 0.98, 64 ) ] ), 360 ) ):
        angles = np.linspace( 0, 2 * math.pi, na, endpoint=False )
        cx, cy = centre
        R, A = np.meshgrid( radii, angles, indexing="ij" )
        E = cx + R * np.cos( A )
        N = cy + R * np.sin( A )
        Z = land.at( E.ravel(), N.ravel() ).reshape( E.shape )
        # Under the play area's own ground: sunk out of sight.
        under = ( E > x0 - 20 ) & ( E < x1 + 20 ) & ( N > y0 - 20 ) & ( N < y1 + 20 )
        Z = np.where( under, -60.0, Z )
        own = headland_owns( land, E, N )
        # Smooth normals: the surface's gradient from its neighbours round and out.
        P3 = np.stack( [ E, N, Z ], axis=-1 )
        tr = np.zeros_like( P3 )
        tr[1:-1] = P3[2:] - P3[:-2]
        tr[0] = P3[1] - P3[0]
        tr[-1] = P3[-1] - P3[-2]
        ta = np.roll( P3, -1, axis=1 ) - np.roll( P3, 1, axis=1 )
        nrm = np.cross( tr, ta )
        nrm = nrm * np.where( nrm[..., 2:3] < 0, -1.0, 1.0 )
        nrm = nrm / np.maximum( np.linalg.norm( nrm, axis=-1, keepdims=True ), 1e-9 )
        for i in range( len( radii ) - 1 ):
            for j in range( na ):
                j1 = ( j + 1 ) % na
                corners = ( ( i, j ), ( i, j1 ), ( i + 1, j1 ), ( i + 1, j ) )
                zs = [ Z[c] for c in corners ]
                if max( zs ) < SEA_Z - 6:
                    continue
                if any( own[c] for c in corners ) or all( under[c] for c in corners ):
                    continue
                quad = [ v( E[c], N[c], Z[c] ) for c in corners ]
                normals = [ nrm[c] for c in corners ]
                qn = sum( normals ) / 4
                qn = unit( qn )
                zc = sum( zs ) / 4
                rc = ( radii[i] + radii[i + 1] ) / 2
                if zc < SEA_Z + 30:
                    paint = "vr_rock"
                elif rc < 7000 and zc > -40:
                    # The resort's surroundings: garden terraces, scrub, olive groves' ground; the terrace walls.
                    if qn[2] < 0.8:
                        paint = "vr_stone_dark"
                    else:
                        g = math.sin( E[i, j] / 610.0 + 0.4 ) * math.cos( N[i, j] / 480.0 ) + rng.normal( 0, 0.25 )
                        paint = "vr_garrigue" if g > 0.3 else ( "vr_scrub" if g > -0.45 else "vr_lawn" )
                elif rc > 30000:
                    paint = "vr_far_land"
                elif qn[2] < 0.62:
                    paint = "vr_cliff_far"
                else:
                    paint = "vr_scrub" if ( math.sin( E[i, j] / 900.0 ) * math.cos( N[i, j] / 700.0 ) + rng.normal( 0, 0.3 ) ) > -0.2 else "vr_scrub_dark"
                card( m, paint, quad, sum( normals ), normals=normals )
                count += 1
    return count


def headland_owns( land, E, N ):
    """ Where the headland's own mesh draws instead of the polar one: inside its outline and off the mainland. """
    d_main, ( dist_r, _, ridge_w ), _ = land.parts( E, N )
    return ( dist_r < ridge_w * 1.06 ) & ( d_main < -60.0 )


def rockiness( E, N, slope, Z=None ):
    """ How much of the headland's ground is bare limestone (0..1+): the bosses (where the land bulges), a little
    more on the steepest faces, in patches. """
    boss = vfbm( E, N, 1500.0, 3, 707 )
    # On the flanks the outcrops are sampled in three dimensions, so a patch is as tall as it is wide in the view
    # instead of a streak down the slope.
    if Z is not None:
        boss = 0.45 * boss + 0.75 * vfbm3( E, N, Z * 1.15, 950.0, 3, 808 )
    patch = vfbm( E, N, 700.0, 3, 505 )
    return smoothstep01( 0.02, 0.38, boss ) * 0.78 + smoothstep01( 0.4, 0.8, slope ) * 0.22 + patch * 0.2 + 0.04


def headland( m, land, rows=470, cols=168, veg=None ):
    """ The headland as its own mesh, laid along its crest: rows along the ridge, columns across it out to just past
    its shore on both sides, denser towards the cliffs, so its shoreline follows the outline exactly instead of the
    polar grid's steps. Heights from Land (the same as everywhere else), shaded smooth, painted by slope: pale rock
    on the cliffs, scrub and darker scrub patches where it's gentler. Nothing on the mainland side (the polar mesh has
    it). """
    pts = np.array( [ ( e, n ) for e, n, _, _ in RIDGE ] )
    widths = np.array( [ w for _, _, _, w in RIDGE ] )
    seg = np.hypot( *np.diff( pts, axis=0 ).T )
    along = np.concatenate( [ [ 0.0 ], np.cumsum( seg ) ] )
    # Rows closer together at the root (2.9 times the mean density there), wider towards the far tip.
    u = np.linspace( 0.0, 1.0, rows )
    ts = along[-1] * ( 0.35 * u + 0.65 * u * u )
    cx = np.interp( ts, along, pts[:, 0] )
    cy = np.interp( ts, along, pts[:, 1] )
    w = np.interp( ts, along, widths )
    # Direction along the crest (smoothed) and its left-hand normal.
    dx, dy = np.gradient( cx ), np.gradient( cy )
    dx, dy = ndimage.gaussian_filter1d( dx, 3 ), ndimage.gaussian_filter1d( dy, 3 )
    norm = np.hypot( dx, dy )
    nx, ny = -dy / norm, dx / norm
    x = np.linspace( -1.0, 1.0, cols )
    s_ = np.sign( x ) * np.sin( np.abs( x ) * math.pi / 2 ) * 1.06
    # The tip: the last rows close in to a point, so it rounds off into the sea.
    taper = np.clip( ( along[-1] - ts ) / 1600.0, 0.15, 1.0 ) ** 0.5
    E = cx[:, None] + nx[:, None] * ( s_[None, :] * w[:, None] * taper[:, None] )
    N = cy[:, None] + ny[:, None] * ( s_[None, :] * w[:, None] * taper[:, None] )
    Z = land.at( E.ravel(), N.ravel() ).reshape( E.shape )
    own = headland_owns( land, E, N )
    P3 = np.stack( [ E, N, Z ], axis=-1 )
    tr = np.gradient( P3, axis=0 )
    tc = np.gradient( P3, axis=1 )
    nrm = np.cross( tr, tc )
    nrm = nrm * np.where( nrm[..., 2:3] < 0, -1.0, 1.0 )
    nrm = nrm / np.maximum( np.linalg.norm( nrm, axis=-1, keepdims=True ), 1e-9 )
    # Use broad geological regions instead of choosing an unrelated material
    # on every quad. The original slope threshold mixed flat grey limestone,
    # black maquis and textured cliffs in thin stripes visible from the pool.
    rock = ndimage.gaussian_filter( rockiness( E, N, 1.0 - nrm[..., 2], Z ),
                                    sigma=( 5.0, 4.0 ), mode="nearest" )
    slope = ndimage.gaussian_filter( 1.0 - nrm[..., 2],
                                     sigma=( 5.0, 4.0 ), mode="nearest" )
    tone = vfbm( E, N, 1800.0, 3, 606 )
    count = 0
    for i in range( rows - 1 ):
        for j in range( cols - 1 ):
            corners = ( ( i, j ), ( i, j + 1 ), ( i + 1, j + 1 ), ( i + 1, j ) )
            if not any( own[c] for c in corners ):
                continue
            zs = [ Z[c] for c in corners ]
            if max( zs ) < SEA_Z - 6:
                continue
            quad = [ v( E[c], N[c], Z[c] ) for c in corners ]
            normals = [ nrm[c] for c in corners ]
            zc = sum( zs ) / 4
            rk = sum( rock[c] for c in corners ) / 4
            tn = sum( tone[c] for c in corners ) / 4
            steep = sum( slope[c] for c in corners ) / 4 > 0.37
            if zc < SEA_Z + 30:
                paint = "vr_rock"
            elif steep or rk > 0.57 or ( zc < SEA_Z + 750 + 160 * tn and rk > 0.38 ):
                # A continuous weathered limestone face; the height/normal
                # texture supplies fine variation, the mesh supplies strata.
                paint = "vr_cliff_grey"
            elif rk > 0.39:
                paint = "vr_garrigue"
            else:
                paint = "vr_maquis_dark" if tn < -0.2 else "vr_maquis"
            if veg is not None and rk < 0.5 and zc > SEA_Z + 40:
                veg.append( ( E[i, j], N[i, j], Z[i, j], rk ) )
            card( m, paint, quad, sum( normals ), normals=normals )
            count += 1
    return count


def blob( m, c, r, h, paint, rng, sink=0.3, closed=False ):
    """ A clump of shrubs or a tree's crown seen from far off: a rounded dome on five sides (a ring sunk into the
    slope, a smaller ring partway up, a low apex), its points jittered, shaded round. closed: also its underside, for
    a crown seen from below. c: the ground under its middle. """
    base = v( c[0], c[1], c[2] - r * 0.3 - h * sink * 0.3 )
    rot = rng.uniform( 0, math.pi )
    height = r * 0.3 + h * ( 1.0 - sink * 0.6 )
    ring, mid = [], []
    for k in range( 5 ):
        a = rot + k * 2 * math.pi / 5
        rr = r * rng.uniform( 0.82, 1.12 )
        ring.append( base + v( math.cos( a ) * rr, math.sin( a ) * rr, h * rng.uniform( -0.04, 0.06 ) ) )
        a2 = a + math.pi / 5
        mid.append( base + v( math.cos( a2 ) * rr * 0.74, math.sin( a2 ) * rr * 0.74, height * rng.uniform( 0.58, 0.7 ) ) )
    top = base + v( rng.uniform( -0.1, 0.1 ) * r, rng.uniform( -0.1, 0.1 ) * r, height )
    centre = base + UP * ( height * 0.25 )
    for k in range( 5 ):
        a_, b_ = ring[k], ring[( k + 1 ) % 5]
        m_ = mid[k]
        for tri in ( [ a_, b_, m_ ], [ m_, b_, mid[( k + 1 ) % 5] ], [ m_, mid[( k + 1 ) % 5], top ] ):
            ns = [ unit( p - centre + UP * height * 0.3 ) for p in tri ]
            card( m, paint, tri, sum( ns ), normals=ns )
        if closed:
            tri = [ a_, b_, base - UP * ( h * 0.15 ) ]
            ns = [ unit( p - centre - UP * h * 0.1 ) for p in tri ]
            card( m, paint, tri, sum( ns ), normals=ns )

def umbrella_pine( m, c, h, rng ):
    """ A stone pine on a skyline: a bare leaning trunk and a flat, wide crown. """
    lean = v( rng.normal( 0, 0.12 ), rng.normal( 0, 0.12 ), 1.0 )
    base = v( *c )
    top = base + lean * ( h * 0.72 )
    rod( m, base - UP * 10, top, max( 5.0, h * 0.022 ), "vr_bark", 5 )
    w = h * rng.uniform( 0.42, 0.55 )
    blob( m, ( top[0], top[1], top[2] - h * 0.04 ), w, h * 0.3, "vr_pine_dark", rng, sink=0.0, closed=True )


def cypress( m, c, h, rng ):
    P.lathe( m, ( c[0], c[1] ), [ ( 0.0, c[2] - 6 ), ( h * 0.085, c[2] + h * 0.12 ), ( h * 0.095, c[2] + h * 0.4 ), ( h * 0.06, c[2] + h * 0.78 ),
                                 ( 0.0, c[2] + h ) ], "vr_cypress", 6 )


def vegetation( m, land, spots, rng ):
    """ The headland's maquis: clumps of holm oak, lentisk and pine over its scrubby ground (thick in the gullies,
    thinning onto the rock), stone pines along its skyline. spots: ( e, n, z, rockiness ) from the mesh. """
    count = 0
    for e, n, z, rk in spots:
        density = np.clip( ( 0.5 - rk ) * 1.6, 0.0, 0.95 ) * 0.29
        if rng.random() > density:
            continue
        e += rng.uniform( -30, 30 )
        n += rng.uniform( -30, 30 )
        zz = float( land.at( e, n )[0] )
        r = rng.uniform( 60, 150 ) * ( 1.3 if rk < 0.15 else 1.0 )
        paint = "vr_maquis_dark" if rng.random() < 0.55 else ( "vr_pine_dark" if rng.random() < 0.5 else "vr_maquis" )
        blob( m, ( e, n, zz ), r, r * rng.uniform( 0.7, 1.0 ), paint, rng )
        count += 1
    # Stone pines along the crest, where they stand against the sky.
    pts = np.array( [ ( e, n ) for e, n, _, _ in RIDGE ] )
    seg = np.hypot( *np.diff( pts, axis=0 ).T )
    along = np.concatenate( [ [ 0.0 ], np.cumsum( seg ) ] )
    pines = 0
    for t in np.linspace( 600, along[-1] - 1800, 220 ):
        ce, cn = np.interp( t, along, pts[:, 0] ), np.interp( t, along, pts[:, 1] )
        for _ in range( 2 ):
            e, n = ce + rng.normal( 0, 260 ), cn + rng.normal( 0, 260 )
            if not land.is_headland( e, n ) or math.hypot( e - VILLAGE[0], n - VILLAGE[1] ) < 900:
                continue
            z = float( land.at( e, n )[0] )
            if z < SEA_Z + 800 or rng.random() < 0.35:
                continue
            umbrella_pine( m, ( e, n, z ), rng.uniform( 260, 420 ), rng )
            pines += 1
    return count, pines


def castle( m, land, rng ):
    """ The summit's castle, after the picture: a long pale stone range of three and four storeys along the ridge,
    a square keep at its west end with a parapet, a lower wing stepping down the slope, retaining walls under them,
    windows (some lit). """
    ve, vn = VILLAGE
    d = unit( v( -3100.0, 1400.0, 0 ) )
    s_ = np.cross( UP, d )
    z0 = float( land.at( ve, vn )[0] )

    def block( c, L, W, H, zbase, lit=0.35, paint="vr_castle" ):
        base = v( c[0], c[1], zbase - 120 )
        m.oriented_box( base + UP * ( ( H + 120 ) / 2 ), ( d, s_, UP ), ( L, W, H + 120 ), { "default": paint, "-z": None } )
        m.oriented_box( base + UP * ( H + 120 + 8 ), ( d, s_, UP ), ( L + 8, W + 8, 16 ), { "default": "vr_stone_dark", "-z": None } )
        floors = max( 1, int( H / 100 ) )
        for side, outv in ( ( 0, s_ ), ( 1, -s_ ) ):
            window_grid( m, base + outv * ( W / 2 + 0.5 ) + UP * ( 120 + H * 0.52 ), np.cross( UP, outv ), L * 0.88, H * 0.82,
                         floors, max( 2, int( L / 80 ) ), rng, lit )
        window_grid( m, base + d * ( L / 2 + 0.5 ) + UP * ( 120 + H * 0.52 ), np.cross( UP, d ), W * 0.8, H * 0.82, floors,
                     max( 1, int( W / 90 ) ), rng, lit )

    main = v( ve, vn, 0 ) + d * 120 + s_ * 60
    block( main, 1100, 300, 380, z0 + 40 )
    keep = main + d * ( 1100 / 2 + 60 )
    kz = float( land.at( keep[0], keep[1] )[0] )
    block( keep, 230, 230, 640, max( kz, z0 ) + 40, lit=0.2 )
    for k in range( 9 ):
        f = k / 8 - 0.5
        for sg in ( -1, 1 ):
            q = keep + d * ( f * 230 ) + s_ * ( sg * 115 )
            box( m, q[0] - 10, q[0] + 10, q[1] - 10, q[1] + 10, max( kz, z0 ) + 40 + 640 + 16, max( kz, z0 ) + 40 + 640 + 44, "vr_castle" )
    wing = main - d * ( 1100 / 2 + 260 ) - s_ * 160
    wz = float( land.at( wing[0], wing[1] )[0] )
    block( wing, 560, 240, 240, wz + 20, lit=0.45 )
    # Terraces under the castle: retaining walls along the slope.
    for k, off in enumerate( ( 260.0, 470.0 ) ):
        q = main + s_ * off
        zq = float( land.at( q[0], q[1] )[0] )
        m.oriented_box( q + UP * ( zq + 40 ), ( d, s_, UP ), ( 1300 - k * 200, 24, 200 ), { "default": "vr_castle", "-z": None } )
    # A few cypresses round it.
    for _ in range( 14 ):
        e, n = ve + rng.normal( 0, 600 ), vn + rng.normal( 0, 420 )
        if land.is_headland( e, n ):
            cypress( m, ( e, n, float( land.at( e, n )[0] ) ), rng.uniform( 220, 340 ), rng )


def sea( m ):
    """ The bay: one big water plane (its own model, on Lowtide's water shader), under everything. """
    m.polygon( "vr_sea", [ v( -WORLD, -WORLD, SEA_Z ), v( WORLD, -WORLD, SEA_Z ), v( WORLD, WORLD, SEA_Z ), v( -WORLD, WORLD, SEA_Z ) ], UP )


def near_shore( m ):
    """ The sea wall under the promenade down to the water and the rocks along its foot; the coast either side of
    the play area out to where the heightfield takes over. """
    rng = np.random.default_rng( 5 )
    e = -1750.0
    box( m, e - 40, e, -2600.0, 2600.0, SEA_Z - 60, 0, { "default": None, "-e": "vr_stone_dark", "+z": None } )
    # Riprap along the foot.
    for k in range( 60 ):
        n = rng.uniform( -2550, 2550 )
        VP.boulder( m, ( e - 50 - rng.uniform( 0, 90 ), n, SEA_Z - 10 ), rng.uniform( 30, 70 ), seed=300 + k, squash=0.7, surface=None )


def window_grid( m, centre, right, w, h, rows, cols, rng, lit=0.35, paint_dark="vr_window_dark" ):
    right = unit( right )
    for r_ in range( rows ):
        for c_ in range( cols ):
            x = ( c_ + 0.5 ) / cols - 0.5
            y = ( r_ + 0.5 ) / rows - 0.5
            p = v( *centre ) + right * ( x * w ) + UP * ( y * h )
            P.quad( m, "vr_village_lit" if rng.random() < lit else paint_dark, p, right, UP, w / cols * 0.42, h / rows * 0.5, off=0.6 )


def house( m, c, size, yaw, z, rng, roof="flat", lit=0.4, wall="vr_village" ):
    """ A Mediterranean house: rendered walls, windows (some lit), a flat roof with a parapet or a low tiled hip. """
    L, W, H = size
    d = v( math.cos( yaw ), math.sin( yaw ), 0 )
    s = np.cross( UP, d )
    base = v( c[0], c[1], z - 30 )
    m.oriented_box( base + UP * ( ( H + 30 ) / 2 ), ( d, s, UP ), ( L, W, H + 30 ), { "default": wall, "-z": None } )
    top = z + H
    if roof == "tiles":
        ridge = [ base + d * ( -L / 2 + W / 2 ) + UP * ( H + 30 + W * 0.25 ), base + d * ( L / 2 - W / 2 ) + UP * ( H + 30 + W * 0.25 ) ]
        corners = [ base + d * sx * L / 2 + s * sy * W / 2 + UP * ( H + 30 ) for sx, sy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ]
        card( m, "vr_village_roof", [ corners[0], corners[1], ridge[1], ridge[0] ], -s + UP )
        card( m, "vr_village_roof", [ corners[2], corners[3], ridge[0], ridge[1] ], s + UP )
        card( m, "vr_village_roof", [ corners[1], corners[2], ridge[1] ], d + UP )
        card( m, "vr_village_roof", [ corners[3], corners[0], ridge[0] ], -d + UP )
    floors = max( 1, int( H / 110 ) )
    for side, ( outv, width ) in enumerate( ( ( s, L ), ( -s, L ), ( d, W ), ( -d, W ) ) ):
        right = np.cross( UP, outv )
        cols = max( 1, int( width / 90 ) )
        window_grid( m, base + outv * ( ( W if side < 2 else L ) / 2 ) + UP * ( 30 + H / 2 ), right, width * 0.84, H * 0.86, floors, cols, rng, lit )


def village( m, rng, land ):
    """ The castle on the headland's summit with its village round it, and the town along its north shore. """
    castle( m, land, rng )
    _village_houses( m, rng, land )
    _shore_town( m, rng, land )


def _village_houses( m, rng, land ):
    """ The village round the castle: pale stone houses with tiled roofs, tight on the summit's shoulders. """
    ve, vn = VILLAGE
    placed = 0
    for _ in range( 120 ):
        if placed >= 22:
            break
        a = rng.uniform( 0, 2 * math.pi )
        r = 750 + rng.random() ** 0.8 * 900
        e, n = ve + math.cos( a ) * r * 1.25, vn + math.sin( a ) * r
        if not land.is_headland( e, n ):
            continue
        z = float( land.at( e, n )[0] )
        if z < SEA_Z + 1200:
            continue
        house( m, ( e, n ), ( rng.uniform( 160, 300 ), rng.uniform( 140, 240 ), rng.uniform( 160, 280 ) ), rng.uniform( 0, math.pi ), z, rng,
               "tiles" if rng.random() < 0.7 else "flat", lit=0.35, wall="vr_castle" if rng.random() < 0.6 else "vr_village" )
        placed += 1
    # A few white villas down the flank, where the picture has them.
    for _ in range( 60 ):
        if placed >= 30:
            break
        e, n = rng.uniform( -9000, -6000 ), rng.uniform( -5600, -3800 )
        if not land.is_headland( e, n ):
            continue
        z = float( land.at( e, n )[0] )
        if z < SEA_Z + 600:
            continue
        house( m, ( e, n ), ( rng.uniform( 300, 520 ), rng.uniform( 200, 300 ), rng.uniform( 180, 300 ) ), rng.uniform( -0.4, 0.4 ) + 0.42, z, rng,
               "flat", lit=0.5, wall="vr_render" )
        placed += 1


def _shore_town( m, rng, land ):
    """ The town along the headland's north shore, where the picture's lights are: houses no higher than a few storeys
    up from the quay, and lights along it. """
    for tk, ( te, tn ) in enumerate( TOWN ):
        for k in range( 30 ):
            e = te + rng.normal( 0, 600 )
            n = tn + rng.normal( 0, 420 )
            z = float( land.at( e, n )[0] )
            if z < SEA_Z + 20 or z > SEA_Z + 520:
                continue
            house( m, ( e, n ), ( rng.uniform( 220, 420 ), rng.uniform( 160, 300 ), rng.uniform( 200, 420 ) ), rng.uniform( 0, math.pi ), z, rng,
                   "tiles" if rng.random() < 0.35 else "flat", lit=0.55 )
        for k in range( 6 ):
            e = te + rng.normal( 0, 500 )
            n = tn + rng.normal( 0, 300 )
            z = float( land.at( e, n )[0] )
            if SEA_Z < z < SEA_Z + 200:
                box( m, e - 12, e + 12, n - 12, n + 12, z + 140, z + 160, "vr_village_lit" )


def groves( m, land, rng, count=2600 ):
    """ The resort's surroundings: olive groves in rows on the garden terraces and the hillside, cypress rows along
    the walls and drives, darker clumps of pine and scrub. """
    placed = 0
    for _ in range( count * 4 ):
        if placed >= count:
            break
        e, n = rng.uniform( -1700, 8500 ), rng.uniform( -7500, 7000 )
        d = float( rect_distance( np.array( [ e ] ), np.array( [ n ] ), PLAY_RECT )[0] )
        if d < 260:
            continue
        if coast_distance( np.array( [ e ] ), np.array( [ n ] ) )[0] < 120:
            continue
        # Groves in rows: snap to a grid in patches.
        if math.sin( e / 1100.0 ) * math.cos( n / 900.0 ) > -0.1:
            e, n = round( e / 90.0 ) * 90.0 + rng.normal( 0, 6 ), round( n / 90.0 ) * 90.0 + rng.normal( 0, 6 )
            r, paint = rng.uniform( 34, 52 ), "vr_olive_grove"
        else:
            r, paint = rng.uniform( 50, 110 ), "vr_maquis_dark" if rng.random() < 0.6 else "vr_pine_dark"
        z = float( land.at( e, n )[0] )
        if z < -30:
            continue
        if rng.random() < 0.06:
            cypress( m, ( e, n, z ), rng.uniform( 220, 360 ), rng )
        else:
            blob( m, ( e, n, z ), r, r * rng.uniform( 0.8, 1.05 ), paint, rng )
        placed += 1
    return placed


def trees( m, rng, land, count=1500 ):
    """ Stone pines and cypresses on the headland and the hills behind the resort: a dark crown on a trunk. """
    placed = 0
    for _ in range( count * 6 ):
        if placed >= count:
            break
        r = 3400 + rng.random() ** 0.9 * 26000
        a = rng.uniform( 0, 2 * math.pi )
        e, n = 75 + r * math.cos( a ), -100 + r * math.sin( a )
        if not land.is_land( e, n ) or land.is_headland( e, n ):
            continue
        z = float( land.at( e, n )[0] )
        if z < SEA_Z + 150:
            continue
        # Steep cliff faces stay bare.
        zx = float( land.at( e + 300, n )[0] ) - z
        zy = float( land.at( e, n + 300 )[0] ) - z
        if math.hypot( zx, zy ) > 260:
            continue
        if math.sin( e / 1900.0 + 0.7 ) * math.cos( n / 1500.0 ) + 0.4 * math.sin( ( e - n ) / 700.0 ) < -0.3:
            continue
        if rng.random() < 0.3:
            h = rng.uniform( 300, 520 )
            P.lathe( m, ( e, n ), [ ( 0.0, z ), ( h * 0.09, z + h * 0.15 ), ( h * 0.1, z + h * 0.45 ), ( h * 0.06, z + h * 0.8 ), ( 0.0, z + h ) ],
                     "vr_pine_dark", 6 )
        else:
            h = rng.uniform( 260, 480 )
            P.cylinder( m, ( e, n ), 6, z - 10, z + h * 0.7, "vr_bark", 5 )
            w = h * rng.uniform( 0.45, 0.7 )
            P.lathe( m, ( e, n ), [ ( 0.0, z + h * 0.62 ), ( w * 0.8, z + h * 0.68 ), ( w, z + h * 0.8 ), ( w * 0.7, z + h * 0.94 ), ( 0.0, z + h ) ],
                     "vr_pine_dark" if rng.random() < 0.6 else "vr_scrub", 7 )
        placed += 1
    return placed


def hillside( m, rng, land ):
    """ The resort's surroundings: villas and hotel blocks up the slopes east, north and south of the play area,
    terraced, white and warm, with lit windows; walls and cypress rows. """
    spots = []
    for k in range( 120 ):
        a = rng.uniform( -math.pi * 0.62, math.pi * 0.62 )      # east half-plane, round to the north and south
        r = 3000 + rng.random() ** 0.8 * 7000
        e, n = 75 + r * math.cos( a ), -100 + r * math.sin( a )
        if e < coast_e( np.array( [ n ] ) )[0] + 300:
            continue
        if any( math.hypot( e - se, n - sn ) < 420 for se, sn in spots ):
            continue
        spots.append( ( e, n ) )
        z = float( land.at( e, n )[0] )
        big = rng.random() < 0.25
        size = ( rng.uniform( 500, 900 ), rng.uniform( 300, 420 ), rng.uniform( 280, 480 ) ) if big else \
            ( rng.uniform( 260, 480 ), rng.uniform( 200, 320 ), rng.uniform( 170, 300 ) )
        house( m, ( e, n ), size, rng.uniform( -0.3, 0.3 ) + ( 0 if rng.random() < 0.5 else math.pi / 2 ), z, rng, "flat" if rng.random() < 0.7 else "tiles",
               lit=0.3, wall="vr_render" if rng.random() < 0.6 else "vr_village" )
    return len( spots )


def superyacht( m, at, heading, length=3000.0 ):
    """ A superyacht at anchor, broadside to the resort: a white hull with a raked bow and a sheer line rising to it, a
    dark boot stripe at the waterline, four decks of white superstructure stepping back, each with a black glass band
    and some lit windows, a radar arch and mast, a tender on the aft deck. """
    e, n, _ = at
    d = v( math.cos( heading ), math.sin( heading ), 0 )
    s_ = np.cross( UP, d )
    c = v( e, n, SEA_Z )
    beam = length * 0.155
    stations = np.linspace( -0.5, 0.5, 22 )

    def half_width( t, scale=1.0 ):
        f = t + 0.5
        bow = 0.26
        w = beam / 2 * scale
        if f > 1 - bow:
            w *= max( 0.0, ( 1 - f ) / bow ) ** 0.75
        if f < 0.04:
            w *= 0.92
        return w

    def sheer( t ):
        f = t + 0.5
        return 250.0 + 70.0 * max( 0.0, ( f - 0.6 ) / 0.4 ) ** 1.6

    top = [ ( t * length + ( length * 0.06 * max( 0.0, ( t + 0.5 - 0.85 ) / 0.15 ) ), half_width( t ), sheer( t ) ) for t in stations ]
    wl = [ ( t * length * 0.95, half_width( t, 0.84 ) * ( 0.0 if t + 0.5 > 0.985 else 1.0 ), 0.0 ) for t in stations ]
    for side in ( 1, -1 ):
        for k in range( len( stations ) - 1 ):
            ( x0, w0, z0 ), ( x1, w1, z1 ) = top[k], top[k + 1]
            ( a0, b0, _ ), ( a1, b1, _ ) = wl[k], wl[k + 1]
            p_top0, p_top1 = c + d * x0 + s_ * w0 * side + UP * z0, c + d * x1 + s_ * w1 * side + UP * z1
            p_wl0, p_wl1 = c + d * a0 + s_ * b0 * side, c + d * a1 + s_ * b1 * side
            p_mid0, p_mid1 = p_wl0 + UP * 55, p_wl1 + UP * 55
            out = s_ * side
            card( m, "vr_yacht", [ p_mid0, p_mid1, p_top1, p_top0 ], out )
            card( m, "vr_hull_dark", [ p_wl0, p_wl1, p_mid1, p_mid0 ], out )
    ring = [ c + d * x + s_ * w + UP * z for x, w, z in top ] + [ c + d * x - s_ * w + UP * z for x, w, z in reversed( top ) ]
    card( m, "vr_yacht_trim", ring, UP )
    # The transom.
    ( x0, w0, z0 ), ( a0, b0, _ ) = top[0], wl[0]
    card( m, "vr_yacht", [ c + d * a0 - s_ * b0, c + d * a0 + s_ * b0, c + d * x0 + s_ * w0 + UP * z0, c + d * x0 - s_ * w0 + UP * z0 ], -d )
    # Superstructure: four decks stepping back from the bow, each with a glass band and lit windows.
    decks = ( ( 260, 118, 0.70, 0.90, -0.06 ), ( 378, 104, 0.56, 0.82, -0.10 ), ( 482, 96, 0.42, 0.74, -0.13 ), ( 578, 80, 0.24, 0.62, -0.15 ) )
    for k, ( z0, h, sl, sw, off ) in enumerate( decks ):
        L = length * sl
        W = beam * sw
        cc = c + d * ( length * off ) + UP * ( z0 + h / 2 )
        # Rounded fore end: a box and a half-octagon nose.
        m.oriented_box( cc, ( d, s_, UP ), ( L, W, h ), { "default": "vr_yacht", "-z": None, "+x": None } )
        nose = [ cc + d * ( L / 2 ) + s_ * ( W / 2 * math.cos( a ) ) + d * ( W * 0.35 * math.sin( a ) ) for a in np.linspace( -math.pi / 2, math.pi / 2, 7 ) ]
        for p0, p1 in zip( nose, nose[1:] ):
            card( m, "vr_yacht", [ p0 - UP * h / 2, p1 - UP * h / 2, p1 + UP * h / 2, p0 + UP * h / 2 ], ( p0 + p1 ) / 2 - cc )
        card( m, "vr_yacht", [ n_ + UP * h / 2 for n_ in nose ], UP )
        for sg in ( -1, 1 ):
            band = cc + s_ * ( W / 2 + 0.6 ) * sg + UP * ( h * 0.06 )
            P.quad( m, "vr_yacht_glass", band, d * sg, UP, L * 0.92, h * 0.5, off=0.0 )
            for w_ in range( int( L / 120 ) ):
                if ( w_ * 7 + k * 3 ) % 5 < 2:
                    P.quad( m, "vr_yacht_lit", band + d * ( -L * 0.44 + w_ * 120 + 50 ), d * sg, UP, 80, h * 0.4, off=0.4 )
        # The overhanging deck above it.
        m.oriented_box( cc + UP * ( h / 2 + 4 ) + d * ( 10 ), ( d, s_, UP ), ( L + 40, W + 16, 8 ), "vr_yacht" )
    mast = c + d * ( -length * 0.12 ) + UP * ( decks[-1][0] + decks[-1][1] + 8 )
    P.cylinder( m, ( mast[0], mast[1] ), 10, mast[2], mast[2] + 170, "vr_mast", 8 )
    P.lathe( m, mast + UP * 170, [ ( 26, mast[2] + 170 ), ( 30, mast[2] + 188 ), ( 18, mast[2] + 214 ), ( 0.0, mast[2] + 222 ) ], "vr_yacht", 10 )
    box( m, mast[0] - 4, mast[0] + 4, mast[1] - 4, mast[1] + 4, mast[2] + 222, mast[2] + 262, "vr_beacon_red" )
    # A tender on the aft deck.
    tc = c + d * ( -length * 0.4 ) + UP * 280
    m.oriented_box( tc, ( d, s_, UP ), ( 260, 90, 50 ), "vr_white" )


def sailboat( m, at, heading, length=420.0, rng=None ):
    e, n = at
    d = v( math.cos( heading ), math.sin( heading ), 0 )
    s = np.cross( UP, d )
    c = v( e, n, SEA_Z )
    beam = length * 0.3
    bow = c + d * ( length / 2 ) + UP * 30
    stern_l, stern_r = c - d * ( length / 2 ) - s * ( beam * 0.4 ) + UP * 30, c - d * ( length / 2 ) + s * ( beam * 0.4 ) + UP * 30
    mid_l, mid_r = c - s * ( beam / 2 ) + UP * 30, c + s * ( beam / 2 ) + UP * 30
    keel = c + UP * -10
    for a, b in ( ( stern_l, mid_l ), ( mid_l, bow ), ( bow, mid_r ), ( mid_r, stern_r ), ( stern_r, stern_l ) ):
        card( m, "vr_white", [ a, b, b * v( 1, 1, 0 ) + UP * ( SEA_Z - 5 ), a * v( 1, 1, 0 ) + UP * ( SEA_Z - 5 ) ], ( a + b ) / 2 - c - UP * ( ( a + b )[2] / 2 - c[2] ) )
    card( m, "vr_timber", [ stern_l, mid_l, bow, mid_r, stern_r ], UP )
    mast = c + d * ( length * 0.08 )
    h = length * 1.35
    rod( m, mast + UP * 30, mast + UP * ( 30 + h ), 2.4, "vr_mast", 5 )
    card( m, "vr_sail", [ mast + UP * 46, mast - d * ( length * 0.42 ) + UP * 50, mast + UP * ( 24 + h ) ], s, both=True )
    card( m, "vr_sail", [ mast + UP * ( 20 + h * 0.85 ), bow + UP * 4, mast + d * 6 + UP * 44 ], s, both=True )


def boats( m, rng ):
    for k in range( 9 ):
        a = math.radians( rng.uniform( 12, 52 ) )
        r = rng.uniform( 6500, 22000 )
        e, n = 800 - r * math.cos( a ), -10 + r * math.sin( a )
        sailboat( m, ( e, n ), rng.uniform( 0, 2 * math.pi ), rng.uniform( 320, 560 ), rng )
    # Small motorboats moored off the town.
    for te, tn in TOWN:
        for k in range( 4 ):
            e, n = te + 600 + rng.normal( 0, 300 ), tn + 300 + rng.normal( 0, 300 )
            h = rng.uniform( 0, math.pi )
            obox( m, ( e, n, SEA_Z + 12 ), ( math.cos( h ), math.sin( h ) ), ( rng.uniform( 180, 300 ), 80, 36 ), "vr_white" )


def build(impostors=True):
    """ Three models, none casting shadows: far (the land and the sea wall), props (the castle and village, the
    town, the maquis and the trees, the hillside's villas, the yacht and boats) and sea (the water plane). Split so
    neither OBJ grows past GitHub's 50 MB warning. """
    far, water, props = K.Model(), K.Model(), K.Model()
    rng = np.random.default_rng( 23 )
    land = Land()
    spots = []
    quads = terrain( far, land ) + headland( far, land, veg=spots )
    sea( water )
    near_shore( far )
    village( props, rng, land )
    clumps, pines = vegetation( props, land, spots, rng )
    t = trees( props, rng, land, count=900 )
    g = groves( props, land, rng, count=1600 )
    houses = hillside( props, rng, land )
    print( f"backdrop: {clumps} maquis clumps, {pines} stone pines on the headland, {g} grove trees round the resort" )
    superyacht( props, ( YACHT[0], YACHT[1], 0 ), YACHT[2] )
    boats( props, rng )
    print( f"backdrop: {quads} land quads, {t} trees, {houses} hillside buildings" )
    if impostors:
        from veridant_impostors import replace
        far, props = replace(far, props, land)
        from veridant_inland_vista import replace as replace_inland
        far, props = replace_inland(far, props)
    return far, water, land, props
