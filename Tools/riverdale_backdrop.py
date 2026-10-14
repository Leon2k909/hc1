"""
Riverdale's backdrop, for Tools/riverdale_map.py: what's seen round the plant, drawn only (no collision).

- The containment domes: UNIT 1 east of the play area at (4400, -1700), UNIT 2 west (mirrored), each a 2200 in (56 m) concrete cylinder
  with a shallow dome, a steel ring at its spring line with red beacons, the logo and the name on the face towards the
  yard and a red UNIT banner beside them, pipes and a stair tower up its side, a vent stack, and auxiliary buildings
  round its foot with a walkway on top.
- Four hyperbolic cooling towers, 115-120 m tall, far off to the north-east and north-west, where the east yard's
  and the west yard's views find them over the annexes (the reference's two, left of the dome).
- A tower crane east of the plant, left of the near cooling tower from the east yard, as the reference has it; office
  and service blocks round the plant.
- Forested hills round the site and jagged snowy mountains beyond (a heightfield ring: forest low down, rock on the
  steep faces, snow above a ragged snow line), and pine trees (three stacked cones on a trunk) on the hills.
Returns two models: far (no shadows: domes, towers, mountains, forest) and near (shadows: the crane, blocks).
"""
import math

import numpy as np
from scipy import ndimage

import map_kit as K
import riverdale_parts as P
from riverdale_parts import v, card, box, UP

DOME_R, DOME_WALL, DOME_RISE = 1100.0, 1400.0, 760.0
DOME_E, DOME_N = 4400.0, -1150.0                 # UNIT 1 (UNIT 2 at -DOME_E): over the yard's end, clear of B1
TOWERS = ( ( 10300.0, 4160.0, 4700.0 ), ( 14240.0, 2150.0, 4500.0 ) )     # east; the west ones are mirrored
CRANE = ( 4000.0, 1000.0 )                    # left of the near cooling tower from the east yard
CLEAR = ( -2800.0, 2800.0, -2900.0, 2500.0 )     # no trees or hills in the plant


def fbm( rng, size, octaves=6, base=4 ):
    """ Periodic-ish value noise on size x size, -1..1-ish, from octaves of upsampled random grids. """
    out = np.zeros( ( size, size ), np.float32 )
    amp, total = 1.0, 0.0
    cells = base
    for _ in range( octaves ):
        grid = rng.standard_normal( ( cells + 3, cells + 3 ) ).astype( np.float32 )
        up = ndimage.zoom( grid, ( size + 3 * size / cells ) / ( cells + 3 ), order=3 )
        out += amp * up[:size, :size]
        total += amp
        amp *= 0.5
        cells *= 2
    return out / total


# ---------------------------------------------------------------------------------------------------------------------
# Containment domes

def dome( m, sx, near ):
    """ One unit's containment building (sx 1 east UNIT 1, -1 west UNIT 2). """
    c = v( sx * DOME_E, DOME_N, 0 )
    unit = "unit1" if sx > 0 else "unit2"
    segs = 72
    P.cylinder( m, c, DOME_R, 0, DOME_WALL, "rv_wall", segs )
    profile = [ ( DOME_R * math.cos( a ), DOME_WALL + DOME_RISE * math.sin( a ) ) for a in np.linspace( 0, math.pi / 2, 10 ) ]
    profile[-1] = ( 0.0, DOME_WALL + DOME_RISE )
    P.lathe( m, c, profile, "rv_wall", segs )
    # Ring girder and its walkway at the spring line, a lower band.
    P.cylinder( m, c, DOME_R + 14, DOME_WALL - 26, DOME_WALL + 6, "rv_steel", segs, top="rv_steel", bottom="rv_steel" )
    P.cylinder( m, c, DOME_R + 4, 340, 380, "rv_plinth", segs )
    for k in range( 16 ):
        a = 2 * math.pi * k / 16
        d = v( math.cos( a ), math.sin( a ), 0 )
        P.beacon( m, f"dome beacon {sx} {k}", c + d * ( DOME_R + 10 ) + UP * ( DOME_WALL + 6 ), light=False )
    # The face towards the yard: the logo and the name, and the red banner to their right as the yard sees it.
    to_yard = P.unit( v( 600 * sx - c[0], -1010 - c[1], 0 ) )
    base_a = math.atan2( to_yard[1], to_yard[0] )
    for name, da, z, h, kind in ( ( "logo", 0.0, 1150.0, 300.0, "dark" ), ( "wordmark", 0.0, 920.0, 150.0, "dark" ) ):
        a = base_a + da
        d = v( math.cos( a ), math.sin( a ), 0 )
        P.letters( m, name, c + d * ( DOME_R + 0.6 ) + UP * z, np.cross( UP, d ), h, kind )
    a = base_a + math.radians( 17 )
    d = v( math.cos( a ), math.sin( a ), 0 )
    P.plate( m, unit, c + d * ( DOME_R + 1.0 ) + UP * 1010, np.cross( UP, d ), 420 )
    # Pipes and a stair tower up the side, an equipment hatch.
    for k, ( da, r ) in enumerate( ( ( 0.42, 14.0 ), ( 0.46, 10.0 ), ( 0.5, 10.0 ), ( -0.45, 12.0 ) ) ):
        a = base_a + da * ( 1 if sx > 0 else -1 )
        d = v( math.cos( a ), math.sin( a ), 0 )
        P.pipe( m, [ c + d * ( DOME_R + 24 + r ) + UP * 0, c + d * ( DOME_R + 24 + r ) + UP * ( DOME_WALL - 40 ) ], r, "rv_pipe", 10, caps=False )
    a = base_a - 0.62 * ( 1 if sx > 0 else -1 )
    d = v( math.cos( a ), math.sin( a ), 0 )
    st = c + d * ( DOME_R + 80 )
    P.obox( m, st + UP * ( DOME_WALL / 2 ), np.cross( UP, d ), ( 120, 110, DOME_WALL ), "rv_wall" )
    P.obox( m, st + UP * ( DOME_WALL + 20 ), np.cross( UP, d ), ( 130, 120, 40 ), "rv_steel" )
    a = base_a + 0.22 * ( 1 if sx > 0 else -1 )
    d = v( math.cos( a ), math.sin( a ), 0 )
    hatch = c + d * ( DOME_R + 2 ) + UP * 260
    P.rod( m, hatch - d * 6, hatch + d * 18, 130, "rv_steel", 24, caps=True )
    # The vent stack beside it.
    sc = c + v( 0, 1, 0 ) * ( DOME_R + 700 ) + v( sx, 0, 0 ) * 500
    P.lathe( m, sc, [ ( 140, 0 ), ( 120, 2400 ), ( 118, 2600 ) ], "rv_wall", 24, cap="rv_dark" )
    for z in ( 800.0, 1600.0, 2380.0 ):
        P.cylinder( m, sc, 150 if z < 2000 else 132, z, z + 20, "rv_steel", 24, top="rv_steel" )
    for k in range( 4 ):
        P.beacon( m, f"stack beacon {sx} {k}", sc + v( math.cos( k * math.pi / 2 ), math.sin( k * math.pi / 2 ), 0 ) * 120 + UP * 2600, light=False )
    # Auxiliary buildings round its foot, towards the play area: a block with a walkway and crates on top, a door, lamps.
    fx = sx * ( DOME_E - DOME_R - 420 )
    for n0, n1, h in ( ( DOME_N - 900, DOME_N - 200, 420 ), ( DOME_N - 200, DOME_N + 500, 520 ), ( DOME_N + 500, DOME_N + 1300, 380 ) ):
        a_, b_ = sorted( ( fx - sx * 260, fx + sx * 260 ) )
        box( near, a_, b_, n0, n1, 0, h, "rv_wall" )
        P.railing( near, [ ( fx - sx * 255, n0 + 5 ), ( fx - sx * 255, n1 - 5 ) ], h, height=40, post_every=80 )
        out = v( -sx, 0, 0 )
        right = np.cross( UP, out )
        face = fx - sx * 260
        P.door( near, ( face, ( n0 + n1 ) / 2, 0 ), right, 110, 130 )
        P.wall_light( near, f"Aux lamp {sx} {n0}", ( face, ( n0 + n1 ) / 2, 160 ), out, "warm", 1, light=False )
        for k in range( 3 ):
            P.case( near, ( fx - sx * 200, n0 + 120 + k * 150 ), ( 60, 40, 34 ), ( 0, 1 ), "rv_olive", h )
        P.louvre( near, ( face, ( n0 + n1 ) / 2 + 200, h - 120 ), right, 160, 100 )
    # A pipe bridge from the plant's boundary out to the auxiliary buildings, above the spawn's roofs.
    for nn in ( DOME_N + 700, DOME_N + 760 ):
        P.truss( near, ( sx * 2600, nn, 470 ), ( fx - sx * 260, nn, 470 ), 50, "rv_steel", panel=80 )
    for k, r in enumerate( ( 14.0, 10.0, 8.0 ) ):
        P.pipe( near, [ ( sx * 2600, DOME_N + 712 + k * 22, 520 + r ), ( fx - sx * 260, DOME_N + 712 + k * 22, 520 + r ) ], r, "rv_pipe", 10, caps=False )


# ---------------------------------------------------------------------------------------------------------------------
# Cooling towers

def cooling_tower( m, e, n, h ):
    """ A natural draught cooling tower: the hyperboloid shell on its ring of raking columns, the basin's wall. """
    r_base, r_throat, r_top = h * 0.36, h * 0.215, h * 0.235
    z_throat = h * 0.78
    a = r_throat
    zs = list( np.linspace( 0.055 * h, h, 18 ) )
    prof = []
    for z in zs:
        if z <= z_throat:
            t = ( z_throat - z ) / ( z_throat - 0.055 * h )
            r = a * math.sqrt( 1 + ( ( r_base / a ) ** 2 - 1 ) * t * t )
        else:
            t = ( z - z_throat ) / ( h - z_throat )
            r = a * math.sqrt( 1 + ( ( r_top / a ) ** 2 - 1 ) * t * t )
        prof.append( ( r, z ) )
    P.lathe( m, ( e, n ), prof, "rv_wall", 56 )
    # The inside's top rim, seen over the lip from far off.
    P.lathe( m, ( e, n ), [ ( r_top, h ), ( r_top - 30, h ) ], "rv_wall", 56 )
    # Raking columns under the shell, dark in its shadow.
    z0 = 0.055 * h
    rb = prof[0][0]
    for k in range( 40 ):
        a0 = 2 * math.pi * k / 40
        for s in ( -1, 1 ):
            a1 = a0 + s * 2 * math.pi / 80
            p0 = v( e + rb * math.cos( a0 ), n + rb * math.sin( a0 ), z0 )
            p1 = v( e + ( rb + 30 ) * math.cos( a1 ), n + ( rb + 30 ) * math.sin( a1 ), 0 )
            P.rod( m, p0, p1, 18, "rv_plinth", 5 )
    P.cylinder( m, ( e, n ), rb + 80, 0, 60, "rv_plinth", 56, top="rv_plinth" )
    P.lathe( m, ( e, n ), [ ( rb - 10, z0 ), ( 10, z0 ) ], "rv_black", 24 )


# ---------------------------------------------------------------------------------------------------------------------
# Terrain: forested hills and snowy mountains

def terrain( m, rng ):
    """ A polar heightfield ring from the hills round the site out to the mountains. """
    na, nr = 288, 62
    radii = np.concatenate( [ np.linspace( 3600, 20000, 18 ), np.geomspace( 21000, 90000, nr - 18 ) ] )
    angles = np.linspace( 0, 2 * math.pi, na, endpoint=False )
    size = 256
    n1 = fbm( rng, size, 6, 6 )
    # Ridges blurred round the ring, so a peak is a massif a few segments wide rather than a one-segment spike.
    ridge = ndimage.gaussian_filter( 1.0 - np.abs( fbm( rng, size, 6, 8 ) * 2.2 ), ( 1.0, 3.0 ), mode="wrap" )
    snow_noise = fbm( rng, size, 4, 8 )

    def sample( field, a, r ):
        u = ( a / ( 2 * math.pi ) ) * ( size - 1 )
        w = min( size - 1, ( r / 90000.0 ) ** 0.6 * ( size - 1 ) )
        return float( ndimage.map_coordinates( field, [ [ w ], [ u ] ], order=1, mode="wrap" )[0] )

    H = np.zeros( ( nr, na ) )
    for i, r in enumerate( radii ):
        for j, a in enumerate( angles ):
            hill = 0.5 + 0.5 * sample( n1, a, r )
            if r < 20000:
                t = ( r - 3600 ) / 16400
                H[i, j] = ( 120 + 1600 * t ) * ( 0.4 + hill )
            else:
                t = min( 1.0, ( r - 20000 ) / 26000 )
                peak = max( 0.0, sample( ridge, a, r ) ) ** 1.6
                H[i, j] = 1900 + t * ( 6000 * hill + 13000 * peak )
                # Fall off beyond the main range so the far ring reads as a horizon.
                if r > 60000:
                    H[i, j] *= max( 0.45, 1.0 - ( r - 60000 ) / 60000 )
    pts = [ [ v( r * math.sin( a ), r * math.cos( a ), H[i, j] ) for j, a in enumerate( angles ) ] for i, r in enumerate( radii ) ]
    for i in range( nr - 1 ):
        for j in range( na ):
            j1 = ( j + 1 ) % na
            quad = [ pts[i][j], pts[i][j1], pts[i + 1][j1], pts[i + 1][j] ]
            # One paint per quad, from its middle and its mean slope: painted per triangle, the snow on each peak
            # came out as a row of white teeth along the grid's diagonals.
            qn = np.cross( quad[2] - quad[0], quad[3] - quad[1] )
            qn = P.unit( -qn if qn[2] < 0 else qn )
            zc = sum( p[2] for p in quad ) / 4
            rc = ( radii[i] + radii[i + 1] ) / 2
            snowline = 7600 + 1400 * sample( snow_noise, angles[j], rc )
            steep = qn[2] < 0.62
            if zc > snowline and not ( steep and zc < snowline + 1600 ):
                paint = "rv_snow"
            elif steep and rc > 18000:
                paint = "rv_rock_far" if rc > 40000 else "rv_rock"
            elif rc < 21000:
                paint = "rv_forest"
            else:
                paint = "rv_pine_far" if zc < 5200 else "rv_rock_far"
            for tri in ( ( quad[0], quad[1], quad[2] ), ( quad[0], quad[2], quad[3] ) ):
                nrm = np.cross( tri[1] - tri[0], tri[2] - tri[0] )
                if nrm[2] < 0:
                    nrm = -nrm
                card( m, paint, list( tri ), P.unit( nrm ) )
    return radii, angles, H


def height_at( radii, angles, H, e, n ):
    r = math.hypot( e, n )
    a = math.atan2( e, n ) % ( 2 * math.pi )
    if r < radii[0]:
        return 0.0
    i = int( np.clip( np.searchsorted( radii, r ) - 1, 0, len( radii ) - 2 ) )
    ti = ( r - radii[i] ) / ( radii[i + 1] - radii[i] )
    da = angles[1] - angles[0]
    j = int( a / da ) % len( angles )
    tj = ( a - j * da ) / da
    j1 = ( j + 1 ) % len( angles )
    h0 = H[i, j] * ( 1 - tj ) + H[i, j1] * tj
    h1 = H[i + 1, j] * ( 1 - tj ) + H[i + 1, j1] * tj
    return h0 * ( 1 - ti ) + h1 * ti


def pine( m, base, h, paint ):
    """ A conifer: a short trunk and three stacked cones. """
    e, n, z = base
    P.cylinder( m, ( e, n ), h * 0.025, z, z + h * 0.2, "rv_dark", 5 )
    for k, ( r, z0, z1 ) in enumerate( ( ( 0.30, 0.12, 0.55 ), ( 0.23, 0.38, 0.8 ), ( 0.15, 0.62, 1.0 ) ) ):
        sides = 7
        c = v( e, n, z + h * z0 )
        top = v( e, n, z + h * z1 )
        ring = [ c + v( math.cos( 2 * math.pi * s / sides + k ), math.sin( 2 * math.pi * s / sides + k ), 0 ) * ( r * h ) for s in range( sides ) ]
        for s in range( sides ):
            a, b = ring[s], ring[( s + 1 ) % sides]
            out = ( a + b ) / 2 - c
            nrm = [ P.unit( a - c + UP * ( r * h * 0.6 ) ), P.unit( b - c + UP * ( r * h * 0.6 ) ), UP ]
            card( m, paint, [ a, b, top ], out + UP * ( r * h * 0.5 ), normals=nrm )
        card( m, paint, ring, -UP )


def forest( m, rng, radii, angles, H ):
    count = 0
    for _ in range( 9000 ):
        # The woods start past the domes: close behind the plant's walls a pine is a black spike over the roofline.
        r = 6000 + ( rng.random() ** 0.8 ) * 12000
        a = rng.random() * 2 * math.pi
        e, n = r * math.sin( a ), r * math.cos( a )
        if CLEAR[0] < e < CLEAR[1] and CLEAR[2] < n < CLEAR[3]:
            continue
        # Keep the domes, towers and their yards clear.
        if any( math.hypot( e - sx * DOME_E, n - DOME_N ) < DOME_R + 1700 for sx in ( -1, 1 ) ):
            continue
        if any( math.hypot( e - sx * te, n - tn ) < th * 0.5 for te, tn, th in TOWERS for sx in ( -1, 1 ) ):
            continue
        if math.hypot( e - CRANE[0], n - CRANE[1] ) < 300:
            continue
        # Thicker in groves: thin out by a low-frequency pattern.
        if math.sin( e / 2100.0 + 1.3 ) * math.cos( n / 1700.0 ) + 0.3 * math.sin( ( e + n ) / 900.0 ) < -0.25:
            continue
        z = height_at( radii, angles, H, e, n ) - 30
        h = rng.uniform( 420, 820 ) * ( 1.0 if r < 9000 else 1.4 )
        pine( m, ( e, n, z ), h, "rv_pine" if r < 9000 else "rv_pine_far" )
        count += 1
        if count >= 2600:
            break
    return count


def ground( m ):
    """ Flat ground round the play area out to where the hills begin: the plant's yards near, grass beyond. """
    # A ring round the play area, whose own ground (riverdale_map.ground) runs 400 past its edges: a slab under it
    # would cap the fuel pool, whose water is at -30.
    e0, e1, n0, n1 = -2600, 2600, -2050, 2750
    for a, b, c, d in ( ( -6000, 6000, -6000, n0 ), ( -6000, 6000, n1, 6000 ), ( -6000, e0, n0, n1 ), ( e1, 6000, n0, n1 ) ):
        box( m, a, b, c, d, -30, -24, { "default": None, "+z": "rv_gravel" } )
    for e0, e1, n0, n1 in ( ( -40000, -6000, -40000, 40000 ), ( 6000, 40000, -40000, 40000 ), ( -6000, 6000, -40000, -6000 ),
                            ( -6000, 6000, 6000, 40000 ) ):
        box( m, e0, e1, n0, n1, -40, -34, { "default": None, "+z": "rv_grass" } )


# ---------------------------------------------------------------------------------------------------------------------
# The tower crane and service blocks

def tower_crane( m ):
    e, n = CRANE
    h = 2300.0
    s = 48.0
    for k, ( a, b ) in enumerate( ( ( ( -s, -s ), ( s, -s ) ), ( ( s, -s ), ( s, s ) ), ( ( s, s ), ( -s, s ) ), ( ( -s, s ), ( -s, -s ) ) ) ):
        for z in np.arange( 0, h, 96.0 ):
            P.rod( m, ( e + a[0], n + a[1], z ), ( e + b[0], n + b[1], z + 96 ), 1.6, "rv_yellow", 4 )
    for a in ( ( -s, -s ), ( s, -s ), ( s, s ), ( -s, s ) ):
        P.rod( m, ( e + a[0], n + a[1], 0 ), ( e + a[0], n + a[1], h ), 3.0, "rv_yellow", 5 )
    box( m, e - 60, e + 60, n - 60, n + 60, h, h + 60, "rv_yellow" )
    box( m, e + 40, e + 110, n - 50, n + 30, h - 70, h, { "default": "rv_white", "-n": "rv_window_dark" } )
    # Jib towards the west-south-west and counter-jib, a peak with tie bars.
    jib = v( -1, -0.25, 0 )
    jib = jib / np.linalg.norm( jib )
    P.truss( m, ( e, n, h + 60 ), ( e + jib[0] * 2600, n + jib[1] * 2600, h + 60 ), 60, "rv_yellow", panel=110, up=UP )
    P.truss( m, ( e, n, h + 60 ), ( e - jib[0] * 900, n - jib[1] * 900, h + 60 ), 50, "rv_yellow", panel=110, up=UP )
    box( m, e - jib[0] * 820 - 60, e - jib[0] * 820 + 60, n - jib[1] * 820 - 60, n - jib[1] * 820 + 60, h - 40, h + 60, "rv_plinth" )
    P.rod( m, ( e, n, h + 60 ), ( e, n, h + 460 ), 6, "rv_yellow", 6 )
    P.rod( m, ( e, n, h + 460 ), ( e + jib[0] * 1800, n + jib[1] * 1800, h + 120 ), 1.5, "rv_dark", 4 )
    P.rod( m, ( e, n, h + 460 ), ( e - jib[0] * 860, n - jib[1] * 860, h + 110 ), 1.5, "rv_dark", 4 )
    hook = v( e + jib[0] * 1500, n + jib[1] * 1500, h + 60 )
    P.rod( m, hook, hook - UP * 900, 0.8, "rv_dark", 4 )
    box( m, hook[0] - 10, hook[0] + 10, hook[1] - 10, hook[1] + 10, hook[2] - 940, hook[2] - 900, "rv_yellow" )


def blocks( m, rng ):
    """ Service and office blocks round the plant's edge, beyond the play area. """
    spots = [ ( -3600, 3200, 900, 600, 520 ), ( 3700, 3300, 700, 500, 600 ), ( -1500, 3300, 1200, 400, 420 ), ( 1600, 3300, 1000, 400, 460 ),
              ( -3400, -3700, 900, 900, 700 ), ( 3500, -3800, 900, 900, 700 ), ( 0, -3600, 2600, 800, 1100 ), ( -4200, 2200, 500, 900, 380 ),
              ( 4200, 2200, 500, 900, 380 ) ]
    for k, ( e, n, w, d, h ) in enumerate( spots ):
        box( m, e - w / 2, e + w / 2, n - d / 2, n + d / 2, 0, h, { "default": "rv_wall", "+z": "rv_steel" } )
        # Strip windows round it.
        for z in np.arange( 140, h - 60, 130.0 ):
            for side, ( c, right, ww ) in enumerate( ( ( v( e, n - d / 2, z ), v( 1, 0, 0 ), w ), ( v( e, n + d / 2, z ), v( -1, 0, 0 ), w ),
                                                       ( v( e - w / 2, n, z ), v( 0, -1, 0 ), d ), ( v( e + w / 2, n, z ), v( 0, 1, 0 ), d ) ) ):
                lit = rng.random() < 0.2
                P.quad( m, "rv_window_lit" if lit else "rv_window_dark", c, right, UP, ww * 0.86, 46, off=0.5 )
        P.railing( m, [ ( e - w / 2 + 6, n - d / 2 + 6 ), ( e + w / 2 - 6, n - d / 2 + 6 ), ( e + w / 2 - 6, n + d / 2 - 6 ), ( e - w / 2 + 6, n + d / 2 - 6 ) ],
                   h, height=40, post_every=120, closed=True, kick=False )
    # A turbine hall roof line south: louvres high on it.
    return len( spots )


def build():
    far, near = K.Model(), K.Model()
    rng = np.random.default_rng( 17 )
    for sx in ( -1, 1 ):
        dome( far, sx, near )
        for e, n, h in TOWERS:
            cooling_tower( far, sx * e, n, h )
    radii, angles, H = terrain( far, rng )
    trees = forest( far, rng, radii, angles, H )
    ground( far )
    tower_crane( near )
    blocks( near, rng )
    print( f"backdrop: {trees} pines" )
    return far, near
