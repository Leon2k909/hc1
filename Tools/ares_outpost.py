"""Ares' drawn exterior colony: insulated habitats, pressure links and industrial atmosphere-processing skids.

Called by ares_map.backdrop(); positions are the existing colony's plan coordinates, in inches. There is no
collision or gameplay content. Materials are the scoped `outpost` group in ares_materials.py.
"""
import math

import numpy as np

from boxyard_map import Frame, card, lathe, rod

UP = np.array( ( 0.0, 0.0, 1.0 ) )
SHELL, METAL, DARK = "ar_ext_shell", "ar_ext_metal", "ar_ext_dark"
BASE, MARK, GLASS, LAMP, SIGNS = "ar_ext_base", "ar_ext_ochre", "ar_ext_glazing", "ar_ext_lamp", "ar_ext_signs"


def base_height( height, e, n, radius ):
    angles = np.arange( 12 ) * ( 2 * math.pi / 12 )
    return float( np.max( height( e + radius * np.cos( angles ), n + radius * np.sin( angles ) ) ) ) + 8.0


def ring( m, centre, radius, z, thickness=4.0, paint=METAL, sides=40 ):
    """A closed rectangular-section hoop; used for pressure flanges and maintenance deck edges."""
    t = thickness / 2
    lathe( m, centre, UP, [ ( radius - t, z - t ), ( radius + t, z - t ), ( radius + t, z + t ),
                          ( radius - t, z + t ), ( radius - t, z - t ) ], paint, sides=sides )


def footing( m, e, n, z, radius ):
    lathe( m, ( e, n, z ), UP, [ ( radius * 1.06, -140 ), ( radius * 1.06, -5 ),
                               ( radius * 1.03, 10 ), ( 0, 10 ) ], BASE, sides=40 )


def label( m, F, x0, x1, y, z0, z1, slot ):
    # Four independently mapped signs, with the writing upright and unmirrored on a south-facing wall.
    u0, u1 = slot / 4, ( slot + 1 ) / 4
    F.quad( m, SIGNS, [ ( x0, y, z0 ), ( x1, y, z0 ), ( x1, y, z1 ), ( x0, y, z1 ) ], ( 0, -1, 0 ),
            uv=[ ( u0, 0 ), ( u1, 0 ), ( u1, 1 ), ( u0, 1 ) ] )


def airlock( m, F, width=150.0, depth=260.0 ):
    """A bevel-edged pressure vestibule, a human-sized hatch, landing and grab rails."""
    half = width / 2
    section = [ ( -half + 18, 10 ), ( half - 18, 10 ), ( half, 28 ), ( half, 120 ),
                ( half - 24, 144 ), ( -half + 24, 144 ), ( -half, 120 ), ( -half, 28 ) ]
    for i, ( x0, z0 ) in enumerate( section ):
        x1, z1 = section[( i + 1 ) % len( section )]
        pts = [ F.p( x0, 20, z0 ), F.p( x0, -depth, z0 ), F.p( x1, -depth, z1 ), F.p( x1, 20, z1 ) ]
        card( m, SHELL, pts, F.v( ( x0 + x1 ) / 2, 0, ( z0 + z1 ) / 2 - 75 ) )
    F.quad( m, SHELL, [ ( x, -depth, z ) for x, z in section ], ( 0, -1, 0 ) )
    F.box( m, -32, 32, -depth - 3, -depth, 24, 116, MARK )
    hatch = [ ( -24, 30 ), ( 24, 30 ), ( 28, 36 ), ( 28, 101 ), ( 20, 110 ),
              ( -20, 110 ), ( -28, 101 ), ( -28, 36 ) ]
    F.quad( m, DARK, [ ( x, -depth - 3.2, z ) for x, z in hatch ], ( 0, -1, 0 ) )
    F.box( m, -13, 13, -depth - 4, -depth - 3.3, 82, 100, GLASS )
    F.rod( m, ( 17, -depth - 7, 53 ), ( 17, -depth - 7, 69 ), 1.7, METAL )
    F.box( m, -31, 31, -depth - 9, -depth + 2, 120, 131, DARK )
    F.box( m, -22, 22, -depth - 9.5, -depth - 9, 123, 126, LAMP )
    F.box( m, -half - 14, half + 14, -depth - 104, -depth + 5, 8, 21, METAL )
    F.box( m, -45, 45, -depth - 135, -depth - 104, -7, 7, BASE )
    for x in ( -half - 10, half + 10 ):
        for y in ( -depth - 96, -depth - 18 ):
            F.box( m, x - 9, x + 9, y - 9, y + 9, -110, 8, BASE )
            F.rod( m, ( x, y, 21 ), ( x, y, 62 ), 1.6, METAL )
        F.rod( m, ( x, -depth - 96, 62 ), ( x, -depth - 18, 62 ), 1.6, METAL )
    label( m, F, 35, half - 5, -depth - .3, 46, 83, 1 )


def radiator( m, height, e, n, width=640.0, depth=250.0 ):
    """A pitched bank of dark heat-rejection panels on a visible supporting frame."""
    z = base_height( height, e, n, width * .5 )
    right = np.array( ( 1.0, 0.0, 0.0 ) )
    along = np.array( ( 0.0, math.cos( .42 ), math.sin( .42 ) ) )
    normal = np.cross( right, along )
    centre = np.array( ( e, n, z + 110 ) )
    m.oriented_box( centre, ( right, along, normal ), ( width, depth, 9 ), METAL )
    m.oriented_box( centre + normal * 5, ( right, along, normal ), ( width - 14, depth - 14, 2 ), DARK )
    for x in np.linspace( -width / 2 + 12, width / 2 - 12, max( 4, int( width // 70 ) ) ):
        a, b = centre + right * x - along * ( depth / 2 ), centre + right * x + along * ( depth / 2 )
        rod( m, a + normal * 7, b + normal * 7, 2.0, METAL, sides=4 )
    for x in ( -.4 * width, .4 * width ):
        for y in ( -.35 * depth, .35 * depth ):
            top = centre + right * x + along * y - normal * 6
            floor = float( height( np.array( [ top[0] ] ), np.array( [ top[1] ] ) )[0] )
            m.box( ( top[0] - 14, top[1] - 14, floor - 6 ), ( top[0] + 14, top[1] + 14, floor + 10 ), BASE )
            m.beam( ( top[0], top[1], floor + 9 ), top, ( 6, 6 ), METAL )


def habitat( m, height, e, n, r ):
    z = base_height( height, e, n, r * 1.05 )
    base = np.array( ( e, n, z ) )
    footing( m, e, n, z, r )
    lathe( m, base, UP, [ ( r * 1.015, 10 ), ( r * 1.015, 62 ), ( r, 72 ) ], METAL, sides=48 )
    ring( m, base, r * 1.017, 54, 7, MARK, sides=48 )
    sides, rows, squash = 48, 10, .57
    elevations = np.linspace( 0, math.radians( 84 ), rows + 1 )

    def point( a, t, extra=0.0 ):
        return base + np.array( ( ( r + extra ) * math.cos( t ) * math.cos( a ),
                                 ( r + extra ) * math.cos( t ) * math.sin( a ),
                                 72 + ( r * squash + extra ) * math.sin( t ) ) )

    def normal( a, t ):
        v = np.array( ( math.cos( t ) * math.cos( a ), math.cos( t ) * math.sin( a ), math.sin( t ) / squash ) )
        return v / np.linalg.norm( v )

    for j in range( rows ):
        for k in range( sides ):
            a0, a1 = k / sides * 2 * math.pi, ( k + 1 ) / sides * 2 * math.pi
            t0, t1 = elevations[j], elevations[j + 1]
            params = [ ( a0, t0 ), ( a1, t0 ), ( a1, t1 ), ( a0, t1 ) ]
            glazing = j == 1 and math.sin( ( a0 + a1 ) / 2 ) < -.1 and k % 8 in ( 2, 3, 4 )
            paint = GLASS if glazing else SHELL
            # Proper physical scale rather than stretching a whole bright atlas around every dome.
            uv = [ ( a * r / 192, t * r / 192 ) for a, t in params ]
            normals = [ normal( a, t ) for a, t in params ]
            card( m, paint, [ point( a, t ) for a, t in params ], sum( normals ), uv=uv, normals=normals )
    # The pressure shell's real meridian ribs and horizontal joints remain legible from the observation deck.
    for a in np.arange( 12 ) * ( 2 * math.pi / 12 ):
        for t0, t1 in zip( elevations[:-1], elevations[1:] ):
            rod( m, point( a, t0, 3 ), point( a, t1, 3 ), 2.8, METAL, sides=4 )
    for t in ( elevations[1], elevations[2], elevations[5] ):
        ring( m, base, r * math.cos( t ) + 2, 72 + r * squash * math.sin( t ), 4.0, METAL, sides=48 )
    top = 72 + r * squash * math.sin( elevations[-1] )
    lathe( m, base, UP, [ ( r * .108, top - 2 ), ( r * .108, top + 11 ), ( r * .075, top + 24 ), ( 0, top + 24 ) ],
           METAL, sides=24 )
    F = Frame( e, n - r + 15, 0, z )
    airlock( m, F, width=150 if r > 500 else 125, depth=240 if r > 500 else 185 )
    label( m, Frame( e, n - r * 1.016, 0, z ), -105, -35, -1, 17, 47, 0 )
    return ( e, n, z, r )


def pressure_link( m, height, a, b ):
    ea, na, za, ra = a
    eb, nb, zb, rb = b
    direction = np.array( ( eb - ea, nb - na, 0.0 ) )
    direction /= np.linalg.norm( direction )
    start = np.array( ( ea, na, za + 115 ) ) + direction * ( ra - 20 )
    end = np.array( ( eb, nb, zb + 115 ) ) - direction * ( rb - 20 )
    axis = end - start
    length = np.linalg.norm( axis )
    if np.dot( axis, direction ) < 10:
        return
    axis /= length
    lathe( m, start, axis, [ ( 54, 0 ), ( 54, length ) ], SHELL, sides=20 )
    for d in np.linspace( 0, length, max( 2, int( length // 110 ) + 1 ) ):
        lathe( m, start, axis, [ ( 56, max( 0, d - 3 ) ), ( 56, min( length, d + 3 ) ) ], METAL, sides=20 )
    for t in ( .25, .75 ):
        top = start + ( end - start ) * t - UP * 53
        floor = float( height( np.array( [ top[0] ] ), np.array( [ top[1] ] ) )[0] )
        if top[2] > floor + 8:
            m.box( ( top[0] - 22, top[1] - 22, floor - 15 ), ( top[0] + 22, top[1] + 22, floor + 10 ), BASE )
            m.beam( ( top[0], top[1], floor + 8 ), top, ( 12, 12 ), METAL )


def deck( m, base, radius, z ):
    lathe( m, base, UP, [ ( radius, z ), ( radius, z + 10 ), ( radius - 75, z + 10 ),
                         ( radius - 75, z ), ( radius, z ) ], METAL, sides=32 )
    count = 20
    for i in range( count ):
        a = i * 2 * math.pi / count
        p = base + np.array( ( ( radius - 8 ) * math.cos( a ), ( radius - 8 ) * math.sin( a ), z + 10 ) )
        rod( m, p, p + UP * 42, 1.7, MARK, sides=4 )
        for h in ( 22, 42 ):
            b = ( i + 1 ) * 2 * math.pi / count
            q = base + np.array( ( ( radius - 8 ) * math.cos( b ), ( radius - 8 ) * math.sin( b ), z + 10 + h ) )
            rod( m, p + UP * h, q, 1.5, METAL, sides=4 )


def processing_plant( m, height, e, n, scale=1.0 ):
    """Pressure vessels, access decks, plumbing and a small communications mast on a service pad."""
    k = scale
    z = base_height( height, e, n, 720 * k )
    base = np.array( ( e, n, z ) )
    footing( m, e, n, z, 720 * k )
    profile = [ ( 105 * k, 120 * k ), ( 148 * k, 230 * k ), ( 148 * k, 1550 * k ),
                ( 137 * k, 1720 * k ), ( 105 * k, 1810 * k ), ( 0, 1850 * k ) ]
    lathe( m, base, UP, profile, SHELL, sides=40 )
    for h in ( 310, 550, 1020, 1450 ):
        ring( m, base, 150 * k, h * k, 8 * k, METAL )
    for h in ( 470, 1390 ):
        lathe( m, base, UP, [ ( 149 * k, h * k ), ( 149 * k, ( h + 26 ) * k ) ], MARK, sides=40 )
    for h in ( 720, 1520 ):
        deck( m, base, 240 * k, h * k )
        for a in np.arange( 4 ) * ( math.pi / 2 ):
            d = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
            m.beam( base + d * 147 * k + UP * ( h - 100 ) * k,
                    base + d * 231 * k + UP * h * k, ( 6 * k, 6 * k ), METAL )
    for i in range( 6 ):
        a = i * 2 * math.pi / 6
        d = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
        p = base + d * 176 * k
        rod( m, p + UP * 230 * k, p + UP * 1720 * k, 10 * k, METAL, sides=8 )
        if i < 4:
            q = base + d * 220 * k
            m.beam( q + UP * 20 * k, p + UP * 270 * k, ( 22 * k, 22 * k ), DARK )
    # Two smaller vessels on each processing skid, with continuous welded bands instead of tiny city windows.
    for dx, dy, h in ( ( -370, 90, 1100 ), ( 370, 150, 830 ) ):
        p = base + np.array( ( dx * k, dy * k, 0 ) )
        lathe( m, p, UP, [ ( 80 * k, 40 * k ), ( 92 * k, 110 * k ), ( 92 * k, ( h - 80 ) * k ),
                           ( 63 * k, h * k ), ( 0, ( h + 30 ) * k ) ], METAL, sides=28 )
        for h2 in ( 180, 450, 690 ):
            if h2 < h - 50:
                ring( m, p, 94 * k, h2 * k, 7 * k, SHELL, sides=28 )
        rod( m, p + UP * h * k, p + UP * ( h + 100 ) * k, 14 * k, DARK, sides=8 )
        rod( m, p + UP * 170 * k, base + UP * 170 * k, 20 * k, MARK, sides=12 )
    # A maintenance ladder faces the facility, with standard human-scale rung spacing.
    ladder_y = -205 * k
    for x in ( -15, 15 ):
        rod( m, base + np.array( ( x, ladder_y, 50 * k ) ), base + np.array( ( x, ladder_y, 1590 * k ) ), 2.0, METAL )
    for h in np.arange( 65 * k, 1590 * k, 12 ):
        rod( m, base + np.array( ( -15, ladder_y, h ) ), base + np.array( ( 15, ladder_y, h ) ), 1.7, METAL, sides=4 )
    # Roof instrument mast and a restrained obstruction lamp.
    mast = base + UP * 1840 * k
    rod( m, mast, mast + UP * 320 * k, 4 * k, METAL, sides=8 )
    for h in ( 205, 275 ):
        rod( m, mast + np.array( ( -50 * k, 0, h * k ) ), mast + np.array( ( 50 * k, 0, h * k ) ), 2 * k, METAL )
    m.box( mast + np.array( ( -7, -7, 315 * k ) ), mast + np.array( ( 7, 7, 326 * k ) ), LAMP )
    # A low equipment/control enclosure at the front of the skid.
    F = Frame( e, n - 410 * k, 0, z + 15 )
    F.box( m, -240 * k, 240 * k, -110 * k, 100 * k, 0, 220 * k, SHELL )
    F.box( m, -246 * k, 246 * k, -116 * k, 106 * k, 220 * k, 231 * k, DARK )
    label( m, F, -196 * k, 196 * k, -110 * k - .5, 96 * k, 192 * k, 2 )
    for x in ( -180, 0, 180 ):
        F.box( m, ( x - 45 ) * k, ( x + 45 ) * k, -116 * k, -111 * k, 22 * k, 65 * k, DARK )
    return ( e, n, z, 720 * k )


def service_building( m, height, e, n, w, d, h, heading ):
    h = min( h, 350 )
    z = base_height( height, e, n, math.hypot( w, d ) / 2 )
    F = Frame( e, n, heading, z )
    F.box( m, -w / 2 - 26, w / 2 + 26, -d / 2 - 26, d / 2 + 26, -110, 12, BASE )
    # Folded metal shoulders and recessed end panels give these modular blocks an actual construction system.
    section = [ ( -w / 2 + 28, 12 ), ( w / 2 - 28, 12 ), ( w / 2, 40 ), ( w / 2, h - 34 ),
                ( w / 2 - 34, h ), ( -w / 2 + 34, h ), ( -w / 2, h - 34 ), ( -w / 2, 40 ) ]
    for i, ( x0, z0 ) in enumerate( section ):
        x1, z1 = section[( i + 1 ) % len( section )]
        pts = [ F.p( x0, d / 2, z0 ), F.p( x0, -d / 2, z0 ), F.p( x1, -d / 2, z1 ), F.p( x1, d / 2, z1 ) ]
        card( m, SHELL, pts, F.v( ( x0 + x1 ) / 2, 0, ( z0 + z1 ) / 2 - h / 2 ) )
    for y, outward in ( ( -d / 2, -1 ), ( d / 2, 1 ) ):
        F.quad( m, SHELL, [ ( x, y, zz ) for x, zz in section ], ( 0, outward, 0 ) )
    F.box( m, -w / 2, w / 2, -d / 2 - 4, -d / 2, 40, 52, MARK )
    for x in np.arange( -w / 2 + 65, w / 2 - 20, 150 ):
        F.box( m, x - 3, x + 3, -d / 2 - 5, -d / 2, 62, h - 30, METAL )
        if x > 20:
            F.box( m, x + 14, min( x + 110, w / 2 - 15 ), -d / 2 - 3, -d / 2 - .5, 130, 168, DARK )
            F.box( m, x + 20, min( x + 104, w / 2 - 20 ), -d / 2 - 3.2, -d / 2 - 3, 137, 163, GLASS )
    F.box( m, -w / 2 + 30, -w / 2 + 100, -d / 2 - 8, -d / 2, 12, 112, DARK )
    F.box( m, -w / 2 + 38, -w / 2 + 92, -d / 2 - 9, -d / 2 - 8, 17, 106, MARK )
    label( m, F, -w / 2 + 126, -w / 2 + 310, -d / 2 - .5, h - 88, h - 40, 3 )
    # Rooftop heat exchangers with visible fins, manifold and service cable runs.
    for x in ( -w * .22, w * .22 ):
        F.box( m, x - 72, x + 72, -d * .22, d * .22, h, h + 65, METAL )
        for y in np.arange( -d * .2, d * .2, 22 ):
            F.box( m, x - 65, x + 65, y - 3, y + 3, h + 65, h + 72, DARK )
    F.rod( m, ( -w * .39, d * .37, h + 25 ), ( w * .39, d * .37, h + 25 ), 12, MARK, sides=10 )
    for x in ( -w * .39, w * .39 ):
        F.rod( m, ( x, d * .37, 30 ), ( x, d * .37, h + 25 ), 12, METAL, sides=10 )


def populate( m, height ):
    groups = [ ( 2600., 5600., 900., [ ( 1500., 4600., 380. ), ( 3700., 4700., 420. ), ( 3300., 6900., 360. ) ] ),
               ( -2700., 4600., 560., [ ( -1800., 3900., 260. ), ( -3600., 5400., 300. ) ] ),
               ( 600., 9200., 650., [ ( -200., 8600., 280. ) ] ) ]
    for e, n, r, small in groups:
        main = habitat( m, height, e, n, r )
        for se, sn, sr in small:
            child = habitat( m, height, se, sn, sr )
            pressure_link( m, height, main, child )
        radiator( m, height, e - r * 1.35, n + r * .5, width=r * .95, depth=r * .3 )
    for e, n, scale in ( ( 4700., 8400., 1.0 ), ( 3400., 9800., .7 ), ( -900., 11500., .85 ),
                         ( 8200., 12500., 1.4 ), ( -5200., 9000., .6 ), ( 1500., 7400., .5 ) ):
        processing_plant( m, height, e, n, scale )
    for args in ( ( 4200., 7300., 900., 500., 420., 10. ), ( 5600., 9300., 700., 700., 600., -15. ),
                  ( 1800., 6600., 500., 300., 260., 30. ), ( -1500., 10500., 800., 400., 500., 0. ),
                  ( 7000., 11000., 1200., 600., 800., 20. ), ( -4200., 6200., 600., 400., 300., -10. ) ):
        service_building( m, height, *args )
    # Low, shielded route markers replace the large floating white cubes.
    for t in np.linspace( 0, 1, 18 ):
        e, n = 400 + 1800 * t, 2500 + 1700 * t
        z = float( height( np.array( [ e ] ), np.array( [ n ] ) )[0] )
        m.box( ( e - 6, n - 6, z - 5 ), ( e + 6, n + 6, z + 22 ), DARK )
        m.box( ( e - 4, n - 6.3, z + 14 ), ( e + 4, n - 6, z + 18 ), LAMP )
