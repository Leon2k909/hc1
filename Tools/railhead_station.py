"""
Railhead's structure: the platforms, the track bed, the concourse, the train shed's walls and roof, the head building,
the footbridge, the platform canopies, the cab roads, the goods yards and the signal box. The trains, the track, the
furniture, the lights and the signs are railhead_map's dressing (with railhead_props' models).

Plan inches (e east, n north, z up), as map_kit. The map is mirrored across e = 0: east_half() is built on the east
side and mirrored for the west, centre() is built whole (the head building's hall and facades, the shed's middle
columns, the signal box), and roof() is the east span of the shed's roof.

The figures are a real terminus's:
- 760 mm platforms (rail top 30 under the platform), standard gauge, the platform edge 1.68 m from the track centre.
- The shed: two segmental iron-and-glass spans of 30.5 m on cast-iron columns, springing at 8.4 m, crown 17.8 m, ribs
  every 6.1 m, like the Gruenderzeit sheds of Frankfurt (1888) and Leipzig (1915).
- Stairs of 168 mm risers and 280 mm goings, footbridge clearance 5.3 m over the rails, the overhead conductor rail
  5.0 m over them (contact face at z 167), clear under the footbridge's girders.
- A goods shed on a 1.1 m loading bank (the height of a wagon's floor).
"""
import math

import numpy as np

import map_kit as K
import railhead_masonry as M
import railhead_architecture as A
import railhead_structure_detail as D
import railhead_profiles as P
import railhead_structure_paints as SP

STONE, METAL, SHEET, GLASS, WOOD, DIRT, TILE = "default", "metal", "metal.sheet", "glass", "wood", "dirt", "ceramic"

# Levels
RAIL_Z = -30.0          # rail top: 760 mm platforms
BED_Z = -37.0           # sleeper tops and the walkable ballast
ROAD_Z = -6.0           # the cab roads' carriageways, behind 6-inch kerbs
SPRING_Z = 330.0        # where the shed's spans spring, at the middle columns
CONTACT_Z = 167.0       # the overhead conductor rail's contact face: 5.0 m over the rails
CROWN_Z = 700.0
WALL_TOP = 400.0        # the shed's outer walls (the roof meets their inside face at 399)

# The shed
SHED_E, WALL_IN = 1200.0, 1160.0          # the outer wall's outside and inside faces
SHED_N0, SHED_N1 = -1340.0, 1300.0
RIBS = [ SHED_N0 + 240.0 * k for k in range( 12 ) ]
BAYS = [ ( a + b ) / 2 for a, b in zip( RIBS, RIBS[1:] ) ]
SHED_R, SHED_CZ = 671.5, 28.5             # each span's circle: centre ( +-600, 28.5 )
GUTTER_Z = ( 304.0, 334.0 )               # the valley gutter over the middle columns

# Platforms and track
PLATFORM_N1 = 880.0     # the platforms' north end, where the concourse starts
BUFFER_N = 860.0        # the buffer stops' faces
FLAT_N0 = -1700.0       # the platforms' level ends...
RAMP_N0 = -1780.0       # ...and their ramps reach the ballast here
SOUTH_N = -2400.0       # the play area's south edge
TRACKS = { "A": 236.0, "B": 416.0, "C": 848.0 }        # track centres, east side (Gleis 4, 5, 6; west 3, 2, 1)
PLATFORMS = ( ( 0.0, 170.0, ( "+e", ) ), ( 482.0, 782.0, ( "-e", "+e" ) ), ( 914.0, SHED_E, ( "-e", ) ) )
COPING, RECESS = 20.0, 8.0
CRIB_DROP = 2.5         # the crib ballast under the sleepers' tops (visual only)

# The head building
HEAD_N0, HEAD_N1 = 1300.0, 1820.0
HALL_E = 600.0          # the booking hall's inside half-width
SIDE_E = 640.0          # its side walls' outside
HALL_N0, HALL_N1 = 1340.0, 1780.0
VAULT_R, VAULT_CZ = 1355.7, -675.7        # the hall's vault: springing 540 at +-600, crown 680
OUTER_R, OUTER_CZ = 1532.9, -832.9        # its copper roof: 560 at +-640, crown 700
GALLERY_N0, GALLERY_Z = 1660.0, 200.0
WING_CEILING = 208.0
WING_ROOF = 440.0

# The footbridge
BRIDGE_N0, BRIDGE_N1 = -330.0, -230.0
DECK_Z = 212.0
BRIDGE_ROOF = 292.0
STAIR_RISE, STAIR_TREAD = DECK_Z / 32, 11.0
BRIDGE_STAIRS = ( ( 24.0, 96.0, +1 ), ( 596.0, 668.0, -1 ), ( 1000.0, 1072.0, +1 ) )    # e0, e1, +1 down to the north

# Platform canopies, south of the shed
CANOPY_Z = 200.0
CANOPIES = ( ( 0.0, 150.0, None ), ( 497.0, 767.0, 632.0 ), ( 929.0, SHED_E, 1060.0 ) )   # e0, e1, column line
CANOPY_COLUMNS_N = ( -1420.0, -1620.0 )

# The cab road and the goods yard (east; the west is mirrored)
PAVEMENT_E1, ROAD_E1, FAR_E1 = 1500.0, 2000.0, 2200.0
YARD_N1 = -1340.0
GATE_WALK = ( 1210.0, 1350.0 )
GATE_ROAD = ( 1530.0, 1970.0 )
SIDING_E = 1300.0
BANK = ( 1380.0, 1520.0, -2300.0, -1500.0, 44.0 )        # the rail-side loading bank: e0, e1, n0, n1, top
GOODS = ( 1520.0, 1800.0, -2200.0, -1600.0 )              # the goods shed
ROAD_BANK = ( 1800.0, 1860.0 )
WAREHOUSE = ( 2200.0, 2560.0, SOUTH_N, -1400.0 )

# The signal box (Stellwerk "Hf"), on the centre line in the station throat
BOX = ( -130.0, 130.0, -2180.0, -1900.0 )
BOX_FLOOR = 130.0


# ---------------------------------------------------------------------------------------------------------------------
# Shapes

def shed_z( e ):
    """ The roof's height over plan e (either span). """
    x = min( abs( e ), SHED_E ) - 600.0
    return SHED_CZ + math.sqrt( max( SHED_R * SHED_R - x * x, 0.0 ) )


def shed_rib_z( e ):
    """ The underside of the curved lower chord, whose depth is radial rather than vertical. """
    x = min( abs( e ), SHED_E ) - 600.0
    radius = SHED_R - RIB_BOTTOM[1]
    return SHED_CZ + math.sqrt( max( radius * radius - x * x, 0.0 ) )


def vault_z( e ):
    e = min( abs( e ), HALL_E )
    return VAULT_CZ + math.sqrt( VAULT_R * VAULT_R - e * e )


def outer_z( e ):
    e = min( abs( e ), SIDE_E )
    return OUTER_CZ + math.sqrt( OUTER_R * OUTER_R - e * e )


def gable_top( e ):
    """ The head building's south wall: up over the shed's roof everywhere, and over the hall's roof in the middle. """
    a = abs( e )
    top = shed_z( a ) + 30.0
    if a < SIDE_E:
        top = max( top, outer_z( a ) + 20.0 )
    else:
        top = max( top, 470.0 )
    return top


def unit2( v ):
    v = np.asarray( v, float )[:2]
    return v / np.linalg.norm( v )


def facing( model, paint, points, towards, uv=None ):
    """ A polygon wound to face towards (a plan vector). A paint of None draws nothing. """
    if paint is None:
        return
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
        if uv is not None:
            uv = list( uv[:1] ) + list( uv[:0:-1] )
    model.polygon( paint, pts, uv=uv )


def clock_dial( model, centre, normal, radius, sides=48 ):
    """Round dial geometry with upright UVs, so no texture corners overhang its stone ring."""
    c, n = np.asarray( centre, float ), np.asarray( normal, float )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    right = np.cross( up, n )
    angles = [ 2 * math.pi * k / sides for k in range( sides ) ]
    pts = [ c + radius * ( math.cos( a ) * right + math.sin( a ) * up ) for a in angles ]
    uv = [ ( 0.5 + 0.5 * math.cos( a ), 0.5 + 0.5 * math.sin( a ) ) for a in angles ]
    facing( model, "rw_clock", pts, n, uv=uv )


def tube( model, p0, p1, radius, paint, sides=10, cap=False ):
    """ A round bar from p0 to p1, smooth-shaded. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    axis = K.normalise( p1 - p0 )
    u = K.normalise( np.cross( axis, ( 0, 0, 1 ) ) if abs( axis[2] ) < 0.9 else np.cross( axis, ( 1, 0, 0 ) ) )
    v = np.cross( axis, u )
    dirs = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v for k in range( sides ) ]
    for k in range( sides ):
        a, b = dirs[k], dirs[( k + 1 ) % sides]
        model.polygon( paint, [ p0 + a * radius, p0 + b * radius, p1 + b * radius, p1 + a * radius ], normals=[ a, b, b, a ] )
    if cap:
        facing( model, paint, [ p1 + d * radius for d in dirs ], axis )
        facing( model, paint, [ p0 + d * radius for d in dirs ], -axis )


def luminaire( model, c, along, length=59.0, width=3.0, depth=2.4, paint="rw_steel_grey", lens="rw_lamp_cool" ):
    """ A surface-mounted linear LED luminaire under a ceiling, as stations' are: an aluminium extrusion 1.5 m long,
    75 mm wide and 60 mm deep with chamfered lower edges and end caps, the opal lens a narrow strip bulging from its
    underside. c: the top's centre ( e, n, z ); along: 'e' or 'n'. No collision. """
    c = np.asarray( c, float )
    ax = np.array( ( 1.0, 0.0, 0.0 ) if along == "e" else ( 0.0, 1.0, 0.0 ) )
    ac = np.array( ( 0.0, 1.0, 0.0 ) if along == "e" else ( 1.0, 0.0, 0.0 ) )

    def p( t, x, z ):
        return c + ax * t + ac * x + np.array( ( 0.0, 0.0, z ) )

    hw, ch, L = width / 2, 0.5, length / 2
    lw, bulge = hw - ch - 0.3, 0.18
    prof = [ ( -hw, 0.0 ), ( -hw, -depth + ch ), ( -hw + ch, -depth ), ( -lw, -depth ), ( lw, -depth ),
             ( hw - ch, -depth ), ( hw, -depth + ch ), ( hw, 0.0 ) ]
    for k, ( ( x0, z0 ), ( x1, z1 ) ) in enumerate( zip( prof, prof[1:] ) ):
        if k == 3:
            continue                # the lens's slot
        out = ac * ( x0 + x1 ) / 2 + np.array( ( 0.0, 0.0, ( z0 + z1 ) / 2 + depth / 2 ) )
        facing( model, paint, [ p( -L, x0, z0 ), p( L, x0, z0 ), p( L, x1, z1 ), p( -L, x1, z1 ) ], out )
    xs = [ lw * ( 2 * j / 6 - 1 ) for j in range( 7 ) ]
    for x0, x1 in zip( xs, xs[1:] ):
        z0, z1 = ( -depth - bulge * ( 1 - ( x / lw ) ** 2 ) for x in ( x0, x1 ) )
        facing( model, lens, [ p( -L + 0.6, x0, z0 ), p( L - 0.6, x0, z0 ), p( L - 0.6, x1, z1 ), p( -L + 0.6, x1, z1 ) ],
                ( 0, 0, -1 ) )
    cap = [ ( -hw - 0.1, 0.0 ), ( -hw - 0.1, -depth + ch ), ( -hw + ch, -depth - 0.1 ), ( 0.0, -depth - bulge - 0.05 ),
            ( hw - ch, -depth - 0.1 ), ( hw + 0.1, -depth + ch ), ( hw + 0.1, 0.0 ) ]
    for t, sgn in ( ( -L - 0.3, -1.0 ), ( L + 0.3, 1.0 ) ):
        facing( model, paint, [ p( t, x, z ) for x, z in cap ], ax * sgn )
        for ( x0, z0 ), ( x1, z1 ) in zip( cap, cap[1:] ):
            ta, tb = t - sgn * 0.6, t
            out = ac * ( x0 + x1 ) / 2 + np.array( ( 0.0, 0.0, ( z0 + z1 ) / 2 + depth / 2 ) )
            facing( model, paint, [ p( ta, x0, z0 ), p( tb, x0, z0 ), p( tb, x1, z1 ), p( ta, x1, z1 ) ], out )


def column( model, e, n, z0, z1, radius, paint, surface=METAL, sides=16, base=None, capital=None ):
    """ A round column with an optional square base and capital ( half-width, height, paint ). """
    zs, ze = z0, z1
    if base:
        h, height, bp = base
        model.box( ( e - h, n - h, z0 ), ( e + h, n + h, z0 + height ), { "default": bp, "-z": None }, surface )
        zs = z0 + height
    if capital:
        h, height, cp = capital
        model.box( ( e - h, n - h, z1 - height ), ( e + h, n + h, z1 ), cp, surface )
        ze = z1 - height
    model.cylinder( ( e, n ), radius, zs, ze, { "side": paint, "top": None, "bottom": None }, sides=sides,
                    surface=surface, collide="hull" )


def sloped_wall( model, e0, e1, n_a, n_b, z_floor, top_a, top_b, side, top_paint, surface, ends=True ):
    """ A wall along n from n_a to n_b over e0..e1, standing on z_floor, its top sloping from top_a to top_b (a stair's
    parapet). """
    na, nb = min( n_a, n_b ), max( n_a, n_b )
    ta, tb = ( top_a, top_b ) if n_a <= n_b else ( top_b, top_a )
    for e, out in ( ( e0, -1.0 ), ( e1, 1.0 ) ):
        facing( model, side, [ ( e, na, z_floor ), ( e, nb, z_floor ), ( e, nb, tb ), ( e, na, ta ) ], ( out, 0, 0 ) )
    facing( model, top_paint, [ ( e0, na, ta ), ( e1, na, ta ), ( e1, nb, tb ), ( e0, nb, tb ) ], ( 0, 0, 1 ) )
    if ends:
        facing( model, side, [ ( e0, na, z_floor ), ( e1, na, z_floor ), ( e1, na, ta ), ( e0, na, ta ) ], ( 0, -1, 0 ) )
        facing( model, side, [ ( e0, nb, z_floor ), ( e1, nb, z_floor ), ( e1, nb, tb ), ( e0, nb, tb ) ], ( 0, 1, 0 ) )
    if surface:
        model.hull( [ ( e, n, z ) for e in ( e0, e1 ) for n, z in ( ( na, z_floor ), ( nb, z_floor ), ( na, ta ), ( nb, tb ) ) ],
                    surface )


def sloped_wall_e( model, n0, n1, e_a, e_b, z_floor, top_a, top_b, side, top_paint, surface ):
    """ sloped_wall's twin along e: a wall over n0..n1 from e_a to e_b, its top sloping from top_a to top_b. """
    ea, eb = min( e_a, e_b ), max( e_a, e_b )
    ta, tb = ( top_a, top_b ) if e_a <= e_b else ( top_b, top_a )
    for n, out in ( ( n0, -1.0 ), ( n1, 1.0 ) ):
        facing( model, side, [ ( ea, n, z_floor ), ( eb, n, z_floor ), ( eb, n, tb ), ( ea, n, ta ) ], ( 0, out, 0 ) )
    facing( model, top_paint, [ ( ea, n0, ta ), ( eb, n0, tb ), ( eb, n1, tb ), ( ea, n1, ta ) ], ( 0, 0, 1 ) )
    facing( model, side, [ ( ea, n0, z_floor ), ( ea, n1, z_floor ), ( ea, n1, ta ), ( ea, n0, ta ) ], ( -1, 0, 0 ) )
    if surface:
        model.hull( [ ( e, n, z ) for n in ( n0, n1 ) for e, z in ( ( ea, z_floor ), ( eb, z_floor ), ( ea, ta ), ( eb, tb ) ) ],
                    surface )


def flight( model, axis, start, direction, w0, w1, z0, count, rise, tread, tread_paint, riser_paint, surface=STONE,
            nosing="rw_line_yellow" ):
    """ A straight flight climbing along axis ('n' or 'e') from start at z0, direction +1 or -1, across w0..w1: count
    steps, each a solid block down to z0 for the collision. Draws the treads and risers (the sides are a parapet's or a
    wall's). Returns where it ends. """
    for k in range( count ):
        a = start + direction * k * tread
        b = start + direction * ( k + 1 ) * tread
        lo, hi = min( a, b ), max( a, b )
        top = z0 + ( k + 1 ) * rise
        if axis == "n":
            box_lo, box_hi = ( w0, lo, z0 ), ( w1, hi, top )
            tread_pts = [ ( w0, lo, top ), ( w1, lo, top ), ( w1, hi, top ), ( w0, hi, top ) ]
            riser = [ ( w0, a, top - rise ), ( w1, a, top - rise ), ( w1, a, top ), ( w0, a, top ) ]
            down = ( 0, -direction, 0 )
            nose = ( ( w0, min( a, a + direction * 2 ), top + 0.05 ), ( w1, max( a, a + direction * 2 ), top + 0.05 ) )
        else:
            box_lo, box_hi = ( lo, w0, z0 ), ( hi, w1, top )
            tread_pts = [ ( lo, w0, top ), ( hi, w0, top ), ( hi, w1, top ), ( lo, w1, top ) ]
            riser = [ ( a, w0, top - rise ), ( a, w1, top - rise ), ( a, w1, top ), ( a, w0, top ) ]
            down = ( -direction, 0, 0 )
            nose = ( ( min( a, a + direction * 2 ), w0, top + 0.05 ), ( max( a, a + direction * 2 ), w1, top + 0.05 ) )
        if surface:
            model.collision_box( box_lo, box_hi, surface )
        if tread_paint:
            facing( model, tread_paint, tread_pts, ( 0, 0, 1 ) )
        if riser_paint:
            facing( model, riser_paint, riser, down )
        if nosing:
            n_lo, n_hi = nose
            facing( model, nosing, [ ( n_lo[0], n_lo[1], n_lo[2] ), ( n_hi[0], n_lo[1], n_lo[2] ),
                                      ( n_hi[0], n_hi[1], n_lo[2] ), ( n_lo[0], n_hi[1], n_lo[2] ) ], ( 0, 0, 1 ) )
    return start + direction * count * tread


def pane( glass, model, axis, at, r0, r1, z0, z1, paint="rw_glass", arched=False, collide=True, steps=12 ):
    """ Glass filling an opening of a wall along axis ('e' or 'n'), in the plane across it at at: r0..r1 along the wall,
    z0..z1 (an arch's z1 is its crown). Both faces, in the glass model; its collision (thin glass) in model. """
    rc, rad = ( r0 + r1 ) / 2, ( r1 - r0 ) / 2
    if arched:
        spring = z1 - rad
        outline = [ ( r0, z0 ), ( r1, z0 ) ] + K.arc( rc, spring, rad, steps, 0.0, 180.0 )
    else:
        outline = [ ( r0, z0 ), ( r1, z0 ), ( r1, z1 ), ( r0, z1 ) ]
    pts = [ ( r, at, z ) if axis == "e" else ( at, r, z ) for r, z in outline ]
    towards = ( 0, 1, 0 ) if axis == "e" else ( 1, 0, 0 )
    facing( glass, paint, pts, towards )
    facing( glass, paint, pts, tuple( -np.asarray( towards, float ) ) )
    if collide and model is not None:
        lo = ( r0, at - 0.5, z0 ) if axis == "e" else ( at - 0.5, r0, z0 )
        hi = ( r1, at + 0.5, z1 ) if axis == "e" else ( at + 0.5, r1, z1 )
        model.collision_box( lo, hi, GLASS )


def glazing_bars( model, axis, at, r0, r1, z0, z1, paint, across=1, spring=None, thick=1.5, depth=2.0 ):
    """ Frame bars in an opening: a mullion up the middle (across of them) and a transom at spring. """
    def bar( lo, hi ):
        model.box( lo, hi, paint )
    for k in range( 1, across + 1 ):
        r = r0 + ( r1 - r0 ) * k / ( across + 1 )
        if axis == "e":
            bar( ( r - thick / 2, at - depth / 2, z0 ), ( r + thick / 2, at + depth / 2, z1 ) )
        else:
            bar( ( at - depth / 2, r - thick / 2, z0 ), ( at + depth / 2, r + thick / 2, z1 ) )
    if spring is not None:
        if axis == "e":
            bar( ( r0, at - depth / 2, spring - thick / 2 ), ( r1, at + depth / 2, spring + thick / 2 ) )
        else:
            bar( ( at - depth / 2, r0, spring - thick / 2 ), ( at + depth / 2, r1, spring + thick / 2 ) )


def blind_window( model, axis, at, out, r0, r1, z0, z1, frame="rw_dressed" ):
    """ A dark window on a wall face with no room behind it: the glass a little back from a stone surround. at is the
    wall's outside face, out +1 / -1 the way it faces. """
    def p( r, d, z ):
        return ( r, at + out * d, z ) if axis == "e" else ( at + out * d, r, z )
    towards = ( 0, out, 0 ) if axis == "e" else ( out, 0, 0 )
    facing( model, "rw_window_dark", [ p( r0, 0.2, z0 ), p( r1, 0.2, z0 ), p( r1, 0.2, z1 ), p( r0, 0.2, z1 ) ], towards )
    for lo, hi in ( ( ( r0 - 5, z0 - 6 ), ( r1 + 5, z0 ) ), ( ( r0 - 5, z1 ), ( r1 + 5, z1 + 6 ) ),
                    ( ( r0 - 5, z0 ), ( r0, z1 ) ), ( ( r1, z0 ), ( r1 + 5, z1 ) ) ):
        a, b = p( lo[0], 0, lo[1] ), p( hi[0], 3, hi[1] )
        model.box( np.minimum( a, b ), np.maximum( a, b ), frame )
    mid = ( r0 + r1 ) / 2
    a, b = p( mid - 1, 0.2, z0 ), p( mid + 1, 1.2, z1 )
    model.box( np.minimum( a, b ), np.maximum( a, b ), "rw_steel_dark" )


def railing( model, p0, p1, height=42.0, paint="iron_black", posts=80.0, surface=METAL, bars=0.0 ):
    """ A steel railing from p0 to p1 (plan points on the floor): posts, a top rail and two lower rails, and
    optionally vertical bars every bars inches. Its collision is one thin box. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    length = float( np.linalg.norm( ( p1 - p0 )[:2] ) )
    if length < 1:
        return
    count = max( 1, int( math.ceil( length / posts ) ) )
    for k in range( count + 1 ):
        p = p0 + ( p1 - p0 ) * k / count
        model.box( ( p[0] - 1.25, p[1] - 1.25, p[2] ), ( p[0] + 1.25, p[1] + 1.25, p[2] + height ), paint )
    for zz, size in ( ( height - 1.5, 3.0 ), ( height * 0.55, 1.5 ), ( 6.0, 1.5 ) ):
        model.beam( p0 + ( 0, 0, zz ), p1 + ( 0, 0, zz ), ( size, size ), paint )
    if bars:
        nb = int( length / bars )
        for k in range( 1, nb ):
            p = p0 + ( p1 - p0 ) * k / nb
            model.box( ( p[0] - 0.4, p[1] - 0.4, p[2] + 6 ), ( p[0] + 0.4, p[1] + 0.4, p[2] + height - 1.5 ), paint )
    if surface:
        d = unit2( p1 - p0 )
        side = np.array( ( -d[1], d[0] ) ) * 1.5
        pts = []
        for p in ( p0, p1 ):
            for s in ( -1, 1 ):
                xy = p[:2] + side * s
                pts += [ ( xy[0], xy[1], p[2] ), ( xy[0], xy[1], p[2] + height ) ]
        model.hull( pts, surface )


# ---------------------------------------------------------------------------------------------------------------------
# Platforms, the track bed and the concourse (east half)

STRIP = ( ( 20.0, 30.0, "rw_paving" ), ( 30.0, 33.0, "rw_line_white" ), ( 33.0, 44.0, "rw_paving" ),
          ( 44.0, 56.0, "rw_tactile" ) )


def platform_bands( e0, e1, edges ):
    """ The platform's top across it: the paving, with the white safety line and the tactile strip near each track
    edge (the coping, the first 20, is its own block). """
    cuts = []
    for edge in edges:
        for a, b, paint in STRIP:
            cuts.append( ( e0 + a, e0 + b, paint ) if edge == "-e" else ( e1 - b, e1 - a, paint ) )
    lo = e0 + COPING if "-e" in edges else e0
    hi = e1 - COPING if "+e" in edges else e1
    bands, at = [], lo
    for a, b, paint in sorted( cuts ):
        if a > at + 1e-6:
            bands.append( ( at, a, "rw_paving" ) )
        bands.append( ( a, b, paint ) )
        at = b
    if hi > at + 1e-6:
        bands.append( ( at, hi, "rw_paving" ) )
    return bands


def platform( model, e0, e1, edges ):
    """ A platform: the slab at z 0 from FLAT_N0 to the concourse, its track edges' coping over a recessed face, a
    hazard band at its south end, then a ramp down to the ballast. """
    hazard_n = FLAT_N0 + 12.0
    lo = e0 + COPING if "-e" in edges else e0
    hi = e1 - COPING if "+e" in edges else e1
    for a, b, paint in platform_bands( e0, e1, edges ):
        model.polygon( paint, [ ( a, hazard_n, 0 ), ( b, hazard_n, 0 ), ( b, PLATFORM_N1, 0 ), ( a, PLATFORM_N1, 0 ) ] )
    model.polygon( "rw_hazard", [ ( lo, FLAT_N0, 0 ), ( hi, FLAT_N0, 0 ), ( hi, hazard_n, 0 ), ( lo, hazard_n, 0 ) ] )
    # The ramp, across the whole platform.
    model.polygon( "rw_concrete", [ ( e0, RAMP_N0, BED_Z ), ( e1, RAMP_N0, BED_Z ), ( e1, FLAT_N0, 0 ), ( e0, FLAT_N0, 0 ) ] )
    core_lo = e0 + RECESS if "-e" in edges else e0
    core_hi = e1 - RECESS if "+e" in edges else e1
    model.collision_box( ( core_lo, FLAT_N0, BED_Z - 30 ), ( core_hi, PLATFORM_N1, 0 ), STONE )
    model.hull( [ ( e, n, z ) for e in ( e0, e1 ) for n, z in ( ( FLAT_N0, 0 ), ( FLAT_N0, BED_Z ), ( RAMP_N0, BED_Z ) ) ], STONE )
    for edge in edges:
        out = -1.0 if edge == "-e" else 1.0
        e_edge = e0 if edge == "-e" else e1
        e_face = e_edge - out * RECESS
        e_back = e_edge - out * COPING
        # The coping: a block on the face, overhanging it.
        c_lo, c_hi = min( e_edge, e_back ), max( e_edge, e_back )
        # Precast slabs about 1 m long with their joints.
        A.coping( model, c_lo, c_hi, FLAT_N0, PLATFORM_N1, e_back )
        # The ramp's kerb and handrail on its track side.
        A.ramp_rail( model, e_edge, RAMP_N0, FLAT_N0, BED_Z, 0.0, out )
        r_lo, r_hi = min( e_edge, e_face ), max( e_edge, e_face )
        model.collision_box( ( r_lo, FLAT_N0, -6 ), ( r_hi, PLATFORM_N1, 0 ), STONE )
        facing( model, "rw_concrete_dark", [ ( e_face, FLAT_N0, BED_Z ), ( e_face, PLATFORM_N1, BED_Z ),
                                             ( e_face, PLATFORM_N1, -6 ), ( e_face, FLAT_N0, -6 ) ], ( out, 0, 0 ) )
        # The face's end, under the coping's end, and the ramp's side.
        facing( model, "rw_concrete_dark", [ ( e_face, FLAT_N0, BED_Z ), ( e_edge, FLAT_N0, BED_Z ), ( e_edge, FLAT_N0, -6 ),
                                             ( e_face, FLAT_N0, -6 ) ], ( 0, -1, 0 ) )
        facing( model, "rw_concrete_dark", [ ( e_edge, RAMP_N0, BED_Z ), ( e_edge, FLAT_N0, BED_Z ), ( e_edge, FLAT_N0, 0 ) ],
                ( out, 0, 0 ) )
        # Drainage slots in the face, every 4 m, darker.
        n = FLAT_N0 + 80
        while n < PLATFORM_N1 - 40:
            facing( model, "rw_black", [ ( e_face + out * 0.2, n, BED_Z + 4 ), ( e_face + out * 0.2, n + 10, BED_Z + 4 ),
                                         ( e_face + out * 0.2, n + 10, BED_Z + 7 ), ( e_face + out * 0.2, n, BED_Z + 7 ) ],
                    ( out, 0, 0 ) )
            n += 157.5


def ballast_bands( e0, e1 ):
    """ Ballast across e0..e1: clean ballast within 60 of each track's centre, old ballast between. """
    cuts = sorted( ( max( c - 60, e0 ), min( c + 60, e1 ) ) for c in TRACKS.values() if c + 60 > e0 and c - 60 < e1 )
    bands, at = [], e0
    for a, b in cuts:
        if a > at + 1e-6:
            bands.append( ( at, a, False ) )
        bands.append( ( a, b, True ) )
        at = b
    if e1 > at + 1e-6:
        bands.append( ( at, e1, False ) )
    return bands


def ballast( model, e0, e1, n0, n1 ):
    """ Ballast over a rectangle at BED_Z, with the track bands stained rusty near the buffer stops. """
    for a, b, track in ballast_bands( e0, e1 ):
        if not track:
            model.polygon( "rw_ballast_old", [ ( a, n0, BED_Z ), ( b, n0, BED_Z ), ( b, n1, BED_Z ), ( a, n1, BED_Z ) ] )
            continue
        cuts = [ n0, n1 ] if n1 <= 640 or n0 >= 640 else [ n0, 640.0, n1 ]
        # The crib ballast lies 2.5 under the shoulders (and the sleepers' tops), sloping up to them past the
        # sleepers' ends: visual only, the collision stays at BED_Z.
        c = ( a + b ) / 2
        low = BED_Z - CRIB_DROP
        prof = [ ( a, BED_Z ), ( max( a, c - 52.0 ), low ), ( min( b, c + 52.0 ), low ), ( b, BED_Z ) ]
        for na, nb in zip( cuts, cuts[1:] ):
            paint = "rw_ballast_rusty" if na >= 640 else "rw_ballast"
            for ( ea, za ), ( eb, zb ) in zip( prof, prof[1:] ):
                if eb - ea > 1e-6:
                    model.polygon( paint, [ ( ea, na, za ), ( eb, na, zb ), ( eb, nb, zb ), ( ea, nb, za ) ] )


def track_bed( model ):
    model.collision_box( ( 0, SOUTH_N, BED_Z - 30 ), ( SHED_E, PLATFORM_N1, BED_Z ), DIRT )
    # The trenches between the platforms, then the station throat south of the platforms' ramps.
    for e0, e1 in ( ( 170.0, 482.0 ), ( 782.0, 914.0 ) ):
        ballast( model, e0, e1, RAMP_N0, PLATFORM_N1 )
        facing( model, "rw_concrete_dark", [ ( e0, PLATFORM_N1, BED_Z - CRIB_DROP ), ( e1, PLATFORM_N1, BED_Z - CRIB_DROP ),
                                             ( e1, PLATFORM_N1, 0 ), ( e0, PLATFORM_N1, 0 ) ], ( 0, -1, 0 ) )
    ballast( model, 0.0, SHED_E, SOUTH_N, RAMP_N0 )


def concourse( model ):
    """ The Querbahnsteig across the platforms' heads: terrazzo with darker bands on the ribs' lines. """
    model.collision_box( ( 0, PLATFORM_N1, -60 ), ( SHED_E, HEAD_N0, 0 ), STONE )
    e_bands = [ ( 236.0, 244.0 ), ( 476.0, 484.0 ), ( 716.0, 724.0 ), ( 956.0, 964.0 ) ]
    n_bands = [ ( PLATFORM_N1, PLATFORM_N1 + 16 ), ( 1056.0, 1064.0 ), ( HEAD_N0 - 16, HEAD_N0 ) ]

    def spans( edges, lo, hi ):
        out, at = [], lo
        for a, b in edges:
            out.append( ( at, a, False ) )
            out.append( ( a, b, True ) )
            at = b
        out.append( ( at, hi, False ) )
        return [ s for s in out if s[1] - s[0] > 1e-6 ]

    for ea, eb, e_band in spans( e_bands, 0.0, SHED_E ):
        for na, nb, n_band in spans( n_bands, PLATFORM_N1, HEAD_N0 ):
            paint = "rw_terrazzo_border" if e_band or n_band else "rw_terrazzo"
            model.polygon( paint, [ ( ea, na, 0 ), ( eb, na, 0 ), ( eb, nb, 0 ), ( ea, nb, 0 ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# The shed's outer wall (east)

SHED_PORTALS = ( 940.0, 1180.0 )                    # to the cab road from the concourse
SHED_ARCHES = ( -980.0, -500.0, -20.0, 460.0 )      # to the cab road from the outer platform
SHED_WINDOWS = ( -1220.0, -740.0, 220.0, 700.0 )    # high windows (bay -260 is behind the footbridge)


def outer_wall( model, glass ):
    w = M.Wall( "n", ( SHED_N0, SHED_N1 ), ( WALL_IN, SHED_E ), ( 0.0, WALL_TOP ), "+e" )
    for n in SHED_PORTALS:
        w.add( n, 160, 0, 260, "arch" )
    for n in SHED_ARCHES:
        w.add( n, 120, 0, 210, "arch" )
    for n in SHED_WINDOWS:
        w.add( n, 120, 140, 290, "glass_arch" )
    w.build( model, "rw_sandstone", "rw_sandstone", "rw_dressed", end="rw_dressed" )
    for n in SHED_WINDOWS:
        pane( glass, model, "n", ( WALL_IN + SHED_E ) / 2, n - 60, n + 60, 140, 290, "rw_glass_roof", arched=True )
        glazing_bars( model, "n", ( WALL_IN + SHED_E ) / 2, n - 60, n + 60, 140, 288, "rw_steel", across=2, spring=230 )
        glazing_bars( model, "n", ( WALL_IN + SHED_E ) / 2, n - 60, n + 60, 140, 230, "rw_steel", across=0, spring=185 )
    # The plinth outside and in, the pilasters at the ribs, the cornice and the parapet.
    doors = sorted( [ ( n - 80, n + 80 ) for n in SHED_PORTALS ] + [ ( n - 60, n + 60 ) for n in SHED_ARCHES ] )
    runs, at = [], SHED_N0
    for a, b in doors:
        runs.append( ( at, a ) )
        at = b
    runs.append( ( at, SHED_N1 ) )
    for n in RIBS[:-1]:
        model.box( ( SHED_E, n - 16, 0 ), ( SHED_E + 10, n + 16, 340 ), { "default": "rw_dressed", "-e": None, "-z": None } )
        model.box( ( WALL_IN - 10, n - 16, 0 ), ( WALL_IN, n + 16, 300 ), { "default": "rw_dressed", "+e": None, "-z": None } )
    # Plinth courses, archivolts, imposts, keystones, sills, the inside cornice and the rib corbels' shoes.
    A.arcade( model, WALL_IN, SHED_E, SHED_ARCHES, SHED_PORTALS, SHED_WINDOWS, RIBS, SHED_N0, SHED_N1 )
    model.box( ( SHED_E, SHED_N0, 340 ), ( SHED_E + 14, SHED_N1, 360 ), { "default": "rw_dressed", "-e": None } )
    model.box( ( SHED_E, SHED_N0, 360 ), ( SHED_E + 6, SHED_N1, 364 ), { "default": "rw_dressed", "-e": None } )
    model.box( ( SHED_E - 14, SHED_N0, WALL_TOP ), ( SHED_E, SHED_N1, WALL_TOP + 40 ),
               { "default": "rw_sandstone", "+z": "rw_dressed" }, STONE )
    model.box( ( SHED_E - 16, SHED_N0, WALL_TOP + 40 ), ( SHED_E + 2, SHED_N1, WALL_TOP + 46 ), "rw_dressed" )


# ---------------------------------------------------------------------------------------------------------------------
# The footbridge (east half)

def footbridge( model, glass ):
    n0, n1 = BRIDGE_N0, BRIDGE_N1
    # The deck on two plate girders.
    model.box( ( 0, n0 + 8, DECK_Z - 12 ), ( WALL_IN, n1 - 8, DECK_Z ),
               { "+z": "rw_paving_dark", "-z": "rw_steel_dark", "default": None }, STONE )
    for a, b in ( ( n0, n0 + 8 ), ( n1 - 8, n1 ) ):
        model.box( ( 0, a, DECK_Z - 32 ), ( WALL_IN, b, DECK_Z ), { "default": "rw_steel_dark", "-e": None, "+e": None }, METAL )
    for k in range( int( WALL_IN // 60 ) ):
        e = 30.0 + 60.0 * k
        model.box( ( e - 3, n0 + 8, DECK_Z - 26 ), ( e + 3, n1 - 8, DECK_Z - 12 ), "rw_steel_dark" )
    # Its columns, on the platforms (the centre platform's are between its two stairs: bridge_columns_centre).
    for e in ( 510.0, 755.0, 935.0 ):
        bridge_column_pair( model, e )
    # The sides: a steel panel, then glass, under a flat roof; gaps where the stairs come up.
    gaps = { n1: [ ( a - 6, b + 6 ) for a, b, d in BRIDGE_STAIRS if d > 0 ],
             n0: [ ( a - 6, b + 6 ) for a, b, d in BRIDGE_STAIRS if d < 0 ] }
    for side_n, inward in ( ( n0, 1.0 ), ( n1, -1.0 ) ):
        runs, at = [], 0.0
        for a, b in sorted( gaps[side_n] ):
            runs.append( ( at, a ) )
            at = b
        runs.append( ( at, WALL_IN ) )
        wall_lo, wall_hi = ( side_n, side_n + 4 ) if inward > 0 else ( side_n - 4, side_n )
        for a, b in runs:
            if b - a < 1:
                continue
            # The trim owns the exposed joint from 248..252; keep the panel below it.
            model.box( ( a, wall_lo, DECK_Z ), ( b, wall_hi, 248 ), D.PANEL )
            model.collision_box( ( a, wall_lo, DECK_Z ), ( b, wall_hi, 250 ), SHEET )
            model.box( ( a, wall_lo - 0.5, 248 ), ( b, wall_hi + 0.5, 252 ), "rw_steel_dark" )
            pane( glass, model, "e", ( wall_lo + wall_hi ) / 2, a, b, 252, BRIDGE_ROOF - 2, "rw_glass" )
            # Mullions every 60, seated on the cap. Starting below its top made their
            # side faces coincide with the grey trim and flicker at the stair posts.
            for k in range( int( ( b - a ) // 60 ) + 1 ):
                e = min( a + 60 * k, b - 1.5 )
                model.box( ( e, wall_lo - 0.5, 252 ), ( e + 3, wall_hi + 0.5, BRIDGE_ROOF ),
                           { "default": "rw_steel_dark", "-z": None } )
        # The handrail inside is railhead_architecture.footbridge's: it stops at each stair's opening, turning into
        # the stair's own handrails (bridge_stair), which come up onto the deck to meet it.
        # Outside: the girder as a riveted plate girder, and the panels' cover strips, drip and run-off.
        out = -inward
        D.bridge_girder_outer( model, side_n, out, WALL_IN, [ ( a - 8, b + 8 ) for a, b in gaps[side_n] ], DECK_Z - 32, DECK_Z )
        D.bridge_panel_outer( model, side_n, out, runs, DECK_Z, 248.0, seed=int( abs( side_n ) ) )
    model.box( ( 0, n0 - 6, BRIDGE_ROOF ), ( WALL_IN, n1 + 6, BRIDGE_ROOF + 6 ),
               { "+z": "corrugated", "-z": "corrugated", "default": "rw_steel_dark", "-e": None }, SHEET )
    # The ceiling battens across the bridge, between the I-beams, fixed to the undersides of the two purlins they
    # cross (railhead_architecture.footbridge). Set flush with the roof, they ran through the purlins.
    for k in range( int( WALL_IN // 120 ) ):
        luminaire( model, ( 60.0 + 120.0 * k, ( n0 + n1 ) / 2, BRIDGE_ROOF - A.BRIDGE_PURLIN_D ), "n" )
    A.footbridge( model, n0, n1, BRIDGE_ROOF, DECK_Z, WALL_IN, ( 510.0, 755.0, 935.0 ), BRIDGE_STAIRS, DECK_Z + 36 )
    for e0, e1, down in BRIDGE_STAIRS:
        bridge_stair( model, e0, e1, down )


def bridge_column_pair( model, e ):
    for n in ( BRIDGE_N0 + 4, BRIDGE_N1 - 4 ):
        model.collision_box( ( e - 5, n - 5, 0 ), ( e + 5, n + 5, DECK_Z - 32 ), METAL )
        model.box( ( e - 9, n - 9, 0 ), ( e + 9, n + 9, 3 ), "rw_steel_dark" )
        # A round steel column under the girder's bearing shoe (railhead_ironwork).
        A.round_column( model, e, n, 3.0, 174.0, 5.0, "rw_steel_dark", sides=20 )


def bridge_columns_centre( model ):
    """ The footbridge's columns on the centre platform: at e 0, in the 36 between its two stairs' parapets, so the
    platform's sides beside the stairs stay open to walk along. """
    bridge_column_pair( model, 0.0 )


def bridge_stair( model, e0, e1, down ):
    """ A stair from a platform up to the deck: 16 steps, a landing, 15 more, the deck's edge the 32nd riser. down +1:
    the stair goes down to the north from the deck's north side. """
    rise, tread = STAIR_RISE, STAIR_TREAD
    top_n = BRIDGE_N1 if down > 0 else BRIDGE_N0
    length = 16 * tread + 48 + 15 * tread
    bottom_n = top_n + down * length
    climb = -down
    n = flight( model, "n", bottom_n, climb, e0, e1, 0.0, 16, rise, tread, "rw_paving_dark", "rw_concrete", nosing=None )
    A.stair( model, e0, e1, bottom_n, climb, rise, tread, 0.0, 16, first=True )
    landing_z = 16 * rise
    la, lb = min( n, n + climb * 48 ), max( n, n + climb * 48 )
    model.box( ( e0, la, 0 ), ( e1, lb, landing_z ), { "+z": "rw_paving_dark", "default": None }, STONE )
    n2 = n + climb * 48
    flight( model, "n", n2, climb, e0, e1, landing_z, 15, rise, tread, "rw_paving_dark", "rw_concrete", nosing=None )
    A.stair( model, e0, e1, n2, climb, rise, tread, landing_z, 15, first=False, last=True )
    # The space under the upper flight is solid concrete, closed at the deck end under the girder: open, it was a
    # hollow you could walk into from under the bridge, seen through the flight's undrawn underside.
    na, nb = sorted( ( n2, top_n ) )
    model.collision_box( ( e0, na, 0.0 ), ( e1, nb, landing_z ), STONE )
    facing( model, D.PRECAST, [ ( e0, top_n, 0.0 ), ( e1, top_n, 0.0 ), ( e1, top_n, DECK_Z - 32 ),
                                    ( e0, top_n, DECK_Z - 32 ) ], ( 0, -down, 0 ) )
    # Precast parapets on both sides, 40 over the nosings, with two steel handrails inside.
    proud = 1.0
    for w0, w1 in ( ( e0 - 6, e0 ), ( e1, e1 + 6 ) ):
        sloped_wall( model, w0, w1, bottom_n, n, 0.0, 40.0 + rise, landing_z + 40, D.PRECAST, D.PRECAST, STONE )
        sloped_wall( model, w0, w1, n, n2, 0.0, landing_z + 40, landing_z + 40, D.PRECAST, D.PRECAST, STONE,
                     ends=False )
        sloped_wall( model, w0, w1, n2, top_n, 0.0, landing_z + 40, DECK_Z + 40, D.PRECAST, D.PRECAST, STONE )
        face = w1 if w0 < e0 else w0
        side = 1.0 if w0 < e0 else -1.0
        e_rail = face + side * ( proud + 2.6 )
        segments = ( ( bottom_n, n, 40.0 + rise, landing_z + 40 ), ( n, n2, landing_z + 40, landing_z + 40 ),
                     ( n2, top_n, landing_z + 40, DECK_Z + 40 ) )
        # Two round handrails ( 900 and 700 mm ), on over the deck's edge to the bridge's handrail, which ends at this
        # one; grime streaks run down the panels from their brackets.
        A.stair_rails( model, e_rail, face + side * proud, [ ( bottom_n, 0.0 ), ( n, landing_z ), ( n2, landing_z ),
                                                              ( top_n, DECK_Z ), ( top_n - down * 6.8, DECK_Z ) ],
                       streak=side )
        # 2.4 m precast panels with V joints on both faces (a kick plinth outside), and a chamfered cap.
        out = -side
        face_out = w0 if w0 < e0 else w1
        for na, nb, ta, tb in segments:
            D.precast_panels( model, face_out, out, na, nb, ta, tb, proud=proud, plinth=8.0 )
            D.precast_panels( model, face, side, na, nb, ta, tb, proud=proud )
            D.parapet_cap( model, w0, w1, na, nb, ta, tb, overhang=proud + 1.2 )
    # Its bottom: a yellow line on the platform where the stair starts.
    na, nb = sorted( ( bottom_n, bottom_n - climb * 12 ) )
    model.polygon( "rw_line_yellow", [ ( e0, na, 0.05 ), ( e1, na, 0.05 ), ( e1, nb, 0.05 ), ( e0, nb, 0.05 ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# Platform canopies south of the shed (east half)

def canopies( model ):
    n0, n1 = FLAT_N0, SHED_N0
    for e0, e1, col in CANOPIES:
        model.box( ( e0, n0, CANOPY_Z ), ( e1, n1, CANOPY_Z + 6 ),
                   { "+z": "corrugated", "-z": "rw_steel_grey", "default": "rw_steel_dark", "-e": None if e0 == 0 else "rw_steel_dark" },
                   SHEET )
        # The structure under the sheeting: cantilevers off a spine on the column line, purlins, fascias and gutters.
        spine = col if col is not None else 0.0
        A.canopy_roof( model, e0, e1, spine, CANOPY_Z, n0, n1, [ e1 ] if col is None else [ e0, e1 ] )
        if col is not None:
            A.canopy_spine( model, col, CANOPY_Z, n0, n1 )
            for cn in CANOPY_COLUMNS_N:
                model.collision_box( ( col - 5, cn - 5, 0 ), ( col + 5, cn + 5, CANOPY_Z - 12 ), METAL )
                A.canopy_column( model, col, cn, CANOPY_Z )
        # Lamps under it, in lines along it, one in each bay between the cantilevers. A line that runs along a purlin
        # (the outer canopy's west one) is fixed to its underside; set flush with the sheeting it was inside the purlin.
        purlins = A.canopy_purlins( spine, [ e1 ] if col is None else [ e0, e1 ] )
        for le in ( ( e0 + e1 ) / 2 - 70, ( e0 + e1 ) / 2 + 70 ) if e1 - e0 > 200 else ( ( e0 + e1 ) / 2 + 20, ):
            top = CANOPY_Z - A.CANOPY_PURLIN_D if any( abs( le - r ) < 3.0 for r in purlins ) else CANOPY_Z
            for n in CANOPY_BATTENS_N:
                luminaire( model, ( le, n, top ), "n" )
    return spine


# The canopies' battens' centres along n: one in each bay between the cantilevers (railhead_architecture's
# CANOPY_BEAMS_N, 6 wide), at least 2.5 clear of their flanges, and over railhead_map.CANOPY_LAMPS' lights (n -1626 and
# -1506). Every 120 from n -1626, they ran through the cantilevers at n -1620 and -1520.
CANOPY_BATTENS_N = ( -1656.0, -1570.0, -1484.0, -1382.0 )
BATTEN_HALF = 30.4          # luminaire's half length with its end caps
for _n in CANOPY_BATTENS_N:
    assert all( abs( _n - b ) >= BATTEN_HALF + 3.0 + 2.5 for b in A.CANOPY_BEAMS_N ), _n


# ---------------------------------------------------------------------------------------------------------------------
# The cab road (east)

def cab_road( model, glass ):
    n0, n1 = SHED_N0, HEAD_N1
    ramp_n = SHED_N0 + 40           # the carriageway rises the last 40 to the yard gate
    # Pavement, carriageway and far pavement.
    model.collision_box( ( SHED_E, n0, -60 ), ( PAVEMENT_E1, n1, 0 ), STONE )
    model.collision_box( ( PAVEMENT_E1, ramp_n, -60 ), ( ROAD_E1, n1, ROAD_Z ), STONE )
    model.hull( [ ( e, n, z ) for e in ( PAVEMENT_E1, ROAD_E1 ) for n, z in ( ( n0, 0 ), ( n0, -60 ), ( ramp_n, ROAD_Z ), ( ramp_n, -60 ) ) ], STONE )
    model.collision_box( ( ROAD_E1, n0, -60 ), ( FAR_E1, n1, 0 ), STONE )
    model.polygon( "rw_paving", [ ( SHED_E, n0, 0 ), ( PAVEMENT_E1 - 10, n0, 0 ), ( PAVEMENT_E1 - 10, n1, 0 ), ( SHED_E, n1, 0 ) ] )
    model.polygon( "rw_kerb", [ ( PAVEMENT_E1 - 10, n0, 0 ), ( PAVEMENT_E1, n0, 0 ), ( PAVEMENT_E1, n1, 0 ), ( PAVEMENT_E1 - 10, n1, 0 ) ] )
    model.polygon( "rw_kerb", [ ( ROAD_E1, n0, 0 ), ( ROAD_E1 + 10, n0, 0 ), ( ROAD_E1 + 10, n1, 0 ), ( ROAD_E1, n1, 0 ) ] )
    model.polygon( "rw_paving", [ ( ROAD_E1 + 10, n0, 0 ), ( FAR_E1, n0, 0 ), ( FAR_E1, n1, 0 ), ( ROAD_E1 + 10, n1, 0 ) ] )
    model.polygon( "rw_asphalt", [ ( PAVEMENT_E1, ramp_n, ROAD_Z ), ( ROAD_E1, ramp_n, ROAD_Z ), ( ROAD_E1, n1, ROAD_Z ), ( PAVEMENT_E1, n1, ROAD_Z ) ] )
    model.polygon( "rw_asphalt", [ ( PAVEMENT_E1, n0, 0 ), ( ROAD_E1, n0, 0 ), ( ROAD_E1, ramp_n, ROAD_Z ), ( PAVEMENT_E1, ramp_n, ROAD_Z ) ] )
    for e, out in ( ( PAVEMENT_E1, 1.0 ), ( ROAD_E1, -1.0 ) ):
        facing( model, "rw_kerb", [ ( e, ramp_n, ROAD_Z ), ( e, n1, ROAD_Z ), ( e, n1, 0 ), ( e, ramp_n, 0 ) ], ( out, 0, 0 ) )
        facing( model, "rw_kerb", [ ( e, n0, 0 ), ( e, ramp_n, ROAD_Z ), ( e, ramp_n, 0 ) ], ( out, 0, 0 ) )
    # Road markings, white as StVO's are (yellow is only for roadworks): the taxi lane's line, a dashed centre line
    # (12 cm Schmalstriche, a 3 m dash and a 6 m gap, as in town) and two zebra crossings (50 cm stripes and gaps).
    def mark( paint, e0, e1, na, nb ):
        model.polygon( paint, [ ( e0, na, ROAD_Z + 0.05 ), ( e1, na, ROAD_Z + 0.05 ), ( e1, nb, ROAD_Z + 0.05 ), ( e0, nb, ROAD_Z + 0.05 ) ] )
    mark( "rw_line_white", 1606.6, 1611.4, ramp_n + 60, n1 - 40 )
    n = ramp_n + 80
    while n + 118 < n1:
        mark( "rw_line_white", 1797.6, 1802.4, n, n + 118 )
        n += 354
    for c in ( -20.0, 1200.0 ):
        for k in range( 12 ):
            e = PAVEMENT_E1 + 22 + 40 * k
            mark( "rw_line_white", e, e + 20, c - 70, c + 70 )
    # The glass canopy over the pavement, hung off the wall at every rib.
    out_e = 1432.0
    for n in RIBS[:-1] + [ SHED_N1 - 8 ]:
        nn = min( max( n, n0 + 4 ), SHED_N1 - 4 )
        model.box( ( SHED_E + 10, nn - 3, 206 ), ( out_e, nn + 3, 218 ), "rw_steel_dark" )
        tube( model, ( SHED_E + 10, nn, 300 ), ( out_e - 6, nn, 218 ), 1.0, "rw_steel_dark", sides=6 )
    model.box( ( out_e - 6, n0, 204 ), ( out_e, SHED_N1, 220 ), "rw_steel_dark" )
    model.box( ( SHED_E + 10, n0, 210 ), ( SHED_E + 16, SHED_N1, 220 ), "rw_steel_dark" )
    for k in range( int( ( SHED_N1 - n0 ) // 60 ) + 1 ):
        n = min( n0 + 60 * k, SHED_N1 - 2 )
        model.box( ( SHED_E + 16, n, 214 ), ( out_e - 6, n + 2, 218 ), "rw_steel_dark" )
    # Individual breakable canopy panes are supplied by railhead_canopy.
    # The road's north end, at the edge of the play area: a kerbed island with a hoarding is the map's; here the
    # pavements' end faces.


# ---------------------------------------------------------------------------------------------------------------------
# The goods yard (east)

def goods_yard( model, glass ):
    e0, e1, n0, n1 = SHED_E, FAR_E1, SOUTH_N, YARD_N1
    model.collision_box( ( e0, n0, -60 ), ( e1, n1, 0 ), STONE )
    model.polygon( "rw_concrete", [ ( e0, n0, 0 ), ( 1360.0, n0, 0 ), ( 1360.0, n1, 0 ), ( e0, n1, 0 ) ] )
    model.polygon( "setts", [ ( 1360.0, n0, 0 ), ( e1, n0, 0 ), ( e1, n1, 0 ), ( 1360.0, n1, 0 ) ] )
    # Where the yard (z 0) stands over the throat's ballast: a retaining face, from the platform's ramp south.
    facing( model, "rw_concrete_dark", [ ( e0, n0, BED_Z ), ( e0, RAMP_N0, BED_Z ), ( e0, FLAT_N0, 0 ), ( e0, n0, 0 ) ], ( -1, 0, 0 ) )
    model.polygon( "rw_coping", [ ( e0, n0, 0.05 ), ( e0 + 14, n0, 0.05 ), ( e0 + 14, FLAT_N0, 0.05 ), ( e0, FLAT_N0, 0.05 ) ] )
    # A ramp down to the ballast for the shunters (and the bots), at the yard's south end.
    ra, rb = -2380.0, -2300.0
    model.hull( [ ( e, n, z ) for n in ( ra, rb ) for e, z in ( ( e0, 0 ), ( e0, BED_Z ), ( e0 - 100, BED_Z ) ) ], STONE )
    model.polygon( "rw_concrete", [ ( e0 - 100, ra, BED_Z ), ( e0, ra, 0 ), ( e0, rb, 0 ), ( e0 - 100, rb, BED_Z ) ] )
    for n, out in ( ( ra, -1.0 ), ( rb, 1.0 ) ):
        facing( model, "rw_concrete_dark", [ ( e0 - 100, n, BED_Z ), ( e0, n, BED_Z ), ( e0, n, 0 ) ], ( 0, out, 0 ) )
    # The fence along the yard's west edge, open by the platform's ramp, at a gate and at the ramp.
    for a, b in ( ( n1 - 10, -1500.0 ), ( -1580.0, FLAT_N0 ), ( -1760.0, rb ), ( ra, n0 + 10 ) ):
        railing( model, ( e0 + 4, a, 0 ), ( e0 + 4, b, 0 ), 42.0, "iron_black", bars=6.0 )
    # The yard's north wall to the cab road, with the gates.
    for a, b in ( ( GATE_WALK[1], GATE_ROAD[0] ), ( GATE_ROAD[1], e1 ) ):
        model.box( ( a, n1 - 10, 0 ), ( b, n1, 96 ), { "default": "brick", "+z": None }, STONE )
        model.box( ( a - 1, n1 - 11, 96 ), ( b + 1, n1 + 1, 100 ), "rw_dressed" )
    for e in ( GATE_WALK[0] - 10, GATE_WALK[1], GATE_ROAD[0] - 20, GATE_ROAD[1] ):
        model.box( ( e, n1 - 15, 0 ), ( e + 20, n1 + 5, 116 ), { "default": "brick", "+z": "rw_dressed" }, STONE )
    # The road gate's two leaves, swung open into the yard.
    for e, s in ( ( GATE_ROAD[0] - 10, 1.0 ), ( GATE_ROAD[1] + 10, -1.0 ) ):
        lo_e, hi_e = sorted( ( e, e + s * 4 ) )
        model.box( ( lo_e, n1 - 230, 6 ), ( hi_e, n1 - 20, 10 ), "rw_steel_dark" )
        model.box( ( lo_e, n1 - 230, 86 ), ( hi_e, n1 - 20, 90 ), "rw_steel_dark" )
        for k in range( 22 ):
            nn = n1 - 225 + k * 10
            model.box( ( lo_e + 1, nn, 10 ), ( hi_e - 1, nn + 1, 86 ), "rw_steel_dark" )
        model.collision_box( ( lo_e, n1 - 230, 6 ), ( hi_e, n1 - 20, 90 ), METAL )
    # The south wall, along the play area's edge, with a gate where the siding leaves the yard: shut, the siding running
    # on under it.
    g0, g1 = SIDING_E - 50.0, SIDING_E + 50.0
    for a, b in ( ( e0, g0 - 10 ), ( g1 + 10, e1 ) ):
        model.box( ( a, n0, 0 ), ( b, n0 + 10, 120 ), { "default": "brick", "+z": None }, STONE )
        model.box( ( a - 1, n0 - 1, 120 ), ( b + ( 0 if b == e1 else 1 ), n0 + 11, 124 ), "rw_dressed" )
    for e in ( g0 - 20, g1 ):
        model.box( ( e, n0 - 5, 0 ), ( e + 20, n0 + 15, 132 ), { "default": "brick", "+z": "rw_dressed" }, STONE )
    model.box( ( g0, n0 + 3, 2 ), ( g1, n0 + 7, 6 ), "rw_steel_dark" )
    model.box( ( g0, n0 + 3, 92 ), ( g1, n0 + 7, 96 ), "rw_steel_dark" )
    e = g0 + 3
    while e < g1 - 1:
        model.box( ( e, n0 + 4, 6 ), ( e + 1, n0 + 6, 92 ), "rw_steel_dark" )
        e += 6
    model.collision_box( ( g0, n0 + 2, 0 ), ( g1, n0 + 8, 96 ), METAL )
    loading_bank( model )
    goods_shed( model, glass )
    warehouse( model )


def bank_ramp( model, e0, e1, n_top, n_foot, top ):
    """ A ramp from a bank's top at n_top down to the yard at n_foot. """
    model.hull( [ ( e, n, z ) for e in ( e0, e1 ) for n, z in ( ( n_top, top ), ( n_top, 0 ), ( n_foot, 0 ) ) ], STONE )
    facing( model, "rw_concrete", [ ( e0, n_foot, 0 ), ( e1, n_foot, 0 ), ( e1, n_top, top ), ( e0, n_top, top ) ], ( 0, 0, 1 ) )
    for e, out in ( ( e0, -1.0 ), ( e1, 1.0 ) ):
        facing( model, "brick", [ ( e, n_top, 0 ), ( e, n_foot, 0 ), ( e, n_top, top ) ], ( out, 0, 0 ) )


def loading_bank( model ):
    e0, e1, n0, n1, top = BANK
    model.box( ( e0, n0, 0 ), ( e1, n1, top ), { "+z": "rw_concrete", "default": "brick", "-z": None }, STONE )
    # A steel angle along its rail-side edge, and timber fenders.
    model.box( ( e0 - 1, n0, top - 4 ), ( e0 + 2, n1, top + 0.2 ), "rw_steel_dark" )
    n = n0 + 40
    while n < n1:
        model.box( ( e0 - 4, n, 6 ), ( e0, n + 8, top - 6 ), "rw_sleeper_wood" )
        n += 160
    bank_ramp( model, e0, e1, n1, n1 + 80, top )
    bank_ramp( model, e0, e1, n0, n0 - 80, top )
    # The road-side bank.
    r0, r1 = ROAD_BANK
    g0, g1 = GOODS[2], GOODS[3]
    model.box( ( r0, g0, 0 ), ( r1, g1, top ), { "+z": "rw_concrete", "default": "brick", "-z": None, "-e": None }, STONE )
    model.box( ( r1 - 2, g0, top - 4 ), ( r1 + 1, g1, top + 0.2 ), "rw_steel_dark" )
    bank_ramp( model, r0, r1, g1, g1 + 80, top )
    bank_ramp( model, r0, r1, g0, g0 - 80, top )


GOODS_DOORS = ( -2050.0, -1900.0, -1750.0 )


def goods_shed( model, glass ):
    e0, e1, n0, n1 = GOODS
    floor = BANK[4]
    ridge_e, ridge_z, eave_z = ( e0 + e1 ) / 2, 300.0, 200.0
    over = 60.0
    model.box( ( e0, n0, 0 ), ( e1, n1, floor ), { "+z": "planks_dark", "default": "brick", "-z": None, "-e": None, "+e": None },
               STONE )
    t = 14.0
    for wall_e, out in ( ( e0, "-e" ), ( e1 - t, "+e" ) ):
        w = M.Wall( "n", ( n0, n1 ), ( wall_e, wall_e + t ), ( floor, eave_z ), out )
        for n in GOODS_DOORS:
            w.add( n, 120, floor, 180, "door" )
        w.build( model, "brick", "brick", "rw_dressed", end="brick" )
        # Lintels: steel beams over the doors, and the sliding doors' rails.
        face = wall_e if out == "-e" else wall_e + t
        sgn = -1.0 if out == "-e" else 1.0
        for n in GOODS_DOORS:
            a, b = sorted( ( face, face + sgn * 3 ) )
            model.box( ( a, n - 70, 180 ), ( b, n + 70, 190 ), "rw_steel_dark" )
            # The sliding door, pushed open beside the opening: framed, ledged and braced boards hung from the track.
            a2, b2 = sorted( ( face + sgn * 3, face + sgn * 6 ) )
            D.sliding_door( model, face, sgn, n + 62, n + 182, floor + 2, 178 )
            model.collision_box( ( a2, n + 62, floor + 2 ), ( b2, n + 182, 178 ), WOOD )
        # The doors' top track over the lintels, on brackets at the lintels' ends and between them.
        brackets = [ m + k for m in GOODS_DOORS for k in ( -60.0, 60.0 ) ] + [ GOODS_DOORS[-1] + 150.0 ]
        D.door_track( model, face, sgn, GOODS_DOORS[0] - 66.0, min( GOODS_DOORS[-1] + 190.0, n1 + 20.0 ), 187.0,
                      [ b for b in brackets if b < n1 - 4 ] )
    for wall_n, out in ( ( n1 - t, "+n" ), ( n0, "-n" ) ):
        w = M.Wall( "e", ( e0 + t, e1 - t ), ( wall_n, wall_n + t ), ( floor, eave_z ), out )
        if out == "+n":
            w.add( ridge_e, 64, floor, 140, "door" )
        else:
            w.add( ridge_e, 60, 110, 170, "window" )
        w.build( model, "brick", "brick", "rw_dressed", end=None )
        # The gable over it.
        face_n = wall_n + t if out == "+n" else wall_n
        for nn, towards, paint in ( ( wall_n, -1.0, "brick" ), ( wall_n + t, 1.0, "brick" ) ):
            facing( model, paint, [ ( e0, nn, eave_z ), ( e1, nn, eave_z ), ( ridge_e, nn, ridge_z ) ], ( 0, towards, 0 ) )
        model.hull( [ ( e, n, z ) for n in ( wall_n, wall_n + t ) for e, z in ( ( e0, eave_z ), ( e1, eave_z ), ( ridge_e, ridge_z ) ) ], STONE )
        model.box( ( ridge_e - 40, face_n - ( 0 if out == "+n" else 1 ), 228 ), ( ridge_e + 40, face_n + ( 1 if out == "+n" else 0 ), 256 ),
                   "rw_dressed" )
    # The roof: two tiled slopes overhanging the banks, on timber trusses.
    slope = ( ridge_z - eave_z ) / ( ridge_e - e0 )
    low_z = eave_z - over * slope
    rn0, rn1 = n0 - 24, n1 + 24
    for edge_e in ( e0 - over, e1 + over ):
        pts = [ ( edge_e, rn0, low_z ), ( ridge_e, rn0, ridge_z ), ( ridge_e, rn1, ridge_z ), ( edge_e, rn1, low_z ) ]
        up = np.array( pts[1] ) - np.array( pts[0] )
        out = 1.0 if edge_e > ridge_e else -1.0
        top = [ np.array( p ) + ( 0, 0, 5 ) for p in pts ]
        facing( model, "roof_tiles", top, ( out * slope, 0, 1 ) )
        facing( model, "planks_dark", pts, ( -out * slope, 0, -1 ) )
        facing( model, "planks_dark", [ pts[0], pts[3], top[3], top[0] ], ( out, 0, 0 ) )
        # In the glass model, which the navmesh leaves out: a 24-degree roof would be an island of it.
        glass.hull( [ tuple( p ) for p in pts ] + [ tuple( p ) for p in top ], TILE )
    model.box( ( ridge_e - 6, rn0, ridge_z + 3 ), ( ridge_e + 6, rn1, ridge_z + 9 ), "roof_tiles" )
    n = n0 + 60
    while n < n1 - 30:
        model.box( ( e0 + t, n - 3, eave_z - 8 ), ( e1 - t, n + 3, eave_z ), "planks_dark" )
        model.box( ( ridge_e - 3, n - 3, eave_z ), ( ridge_e + 3, n + 3, ridge_z - 4 ), "planks_dark" )
        for s in ( -1, 1 ):
            model.beam( ( ridge_e + s * ( ridge_e - e0 - t ), n, eave_z ), ( ridge_e, n, ridge_z - 2 ), ( 6.0, 7.0 ), "planks_dark" )
        n += 120
    # Rafter feet, gutters and downpipes, bargeboards and a plinth course.
    A.goods_shed( model, e0, e1, n0, n1, floor, eave_z, ridge_z, over, GOODS_DOORS, t=t )
    # Skylights in the roof's west slope, between the trusses.
    for n in ( -2080.0, -1840.0 ):
        a = e0 + 50
        b = a + 60
        za, zb = eave_z + ( a - e0 ) * slope + 5.2, eave_z + ( b - e0 ) * slope + 5.2
        facing( glass, "rw_glass_roof", [ ( a, n, za ), ( b, n, zb ), ( b, n + 80, zb ), ( a, n + 80, za ) ], ( -slope, 0, 1 ) )


def warehouse( model ):
    """ The bonded warehouse closing the yard's east side: three storeys of brick, its loading doors shut. """
    e0, e1, n0, n1 = WAREHOUSE
    top = 560.0
    model.box( ( e0, n0, 0 ), ( e1, n1, top ), { "default": "brick", "+z": "gravel", "-z": None }, STONE )
    model.box( ( e0 - 6, n0, top ), ( e0, n1, top + 30 ), { "default": "brick", "+z": "rw_dressed" } )
    model.box( ( e0 - 4, n0, 180 ), ( e0, n1, 190 ), "rw_dressed" )
    model.box( ( e0 - 4, n0, 370 ), ( e0, n1, 380 ), "rw_dressed" )
    for k in range( 9 ):
        n = n0 + 70 + k * 115
        if n + 60 > n1:
            break
        if k % 3 == 1:
            facing( model, "roller_grey", [ ( e0 - 0.3, n - 50, 0 ), ( e0 - 0.3, n + 50, 0 ), ( e0 - 0.3, n + 50, 140 ), ( e0 - 0.3, n - 50, 140 ) ], ( -1, 0, 0 ) )
            model.box( ( e0 - 4, n - 56, 140 ), ( e0, n + 56, 148 ), "rw_steel_dark" )
        else:
            blind_window( model, "n", e0, -1.0, n - 30, n + 30, 60, 150 )
        for z in ( 230, 420 ):
            blind_window( model, "n", e0, -1.0, n - 30, n + 30, z, z + 100 )
    # Its north end shows over the yard wall to the cab road.
    for k in range( 3 ):
        e = e0 + 60 + k * 110
        if e + 30 < e1:
            for z in ( 60, 230, 420 ):
                blind_window( model, "e", n1, 1.0, e - 30, e + 30, z, z + 100 )


# ---------------------------------------------------------------------------------------------------------------------
# The head building: the wings and towers (east, mirrored) and the hall's side walls

def head_wing( model, glass ):
    """ The east wing: the Reisezentrum (travel centre) on the ground floor, an upper storey nobody reaches, a flat
    roof, and the corner tower. """
    e0, e1 = SIDE_E, SHED_E
    # The east wall, to the cab road: a door, windows and the upper storey's windows.
    w = M.Wall( "n", ( HALL_N0, HALL_N1 ), ( WALL_IN, SHED_E ), ( 0.0, 470.0 ), "+e" )
    w.add( 1480.0, 100, 0, 200, "arch" )
    for n in ( 1380.0, 1600.0, 1720.0 ):
        w.add( n, 70, 50, 180, "glass_arch" )
    w.build( model, "rw_sandstone", "render_cream", "rw_dressed", end=None )
    for n in ( 1380.0, 1600.0, 1720.0 ):
        pane( glass, model, "n", ( WALL_IN + SHED_E ) / 2, n - 35, n + 35, 50, 180, "rw_glass", arched=True )
        glazing_bars( model, "n", ( WALL_IN + SHED_E ) / 2, n - 35, n + 35, 50, 178, "rw_steel_dark", across=1, spring=145 )
    model.box( ( SHED_E, HEAD_N0, 0 ), ( SHED_E + 3, 1430.0, 36 ), { "default": "rw_dressed_red", "-e": None } )
    model.box( ( SHED_E, 1530.0, 0 ), ( SHED_E + 3, HEAD_N1, 36 ), { "default": "rw_dressed_red", "-e": None } )
    wing_front( model )
    # The room's ceiling, its columns, and the upper floor's slab; the flat roof.
    model.box( ( e0, HALL_N0, WING_CEILING ), ( WALL_IN, HALL_N1, WING_CEILING + 12 ), { "-z": "render_cream", "default": None }, STONE )
    for n in ( 1480.0, 1640.0 ):
        column( model, 900.0, n, 0.0, WING_CEILING, 10.0, "rw_dressed", STONE, base=( 14, 12, "rw_dressed" ),
                capital=( 15, 10, "rw_dressed" ) )
    model.box( ( e0, HEAD_N0, WING_ROOF ), ( SHED_E, HEAD_N1, WING_ROOF + 12 ), { "+z": "gravel", "default": None }, STONE )
    # The corner tower over the wing's north-east corner, with clocks on its four faces and a copper pyramid.
    t0, t1, u0, u1 = 1000.0, SHED_E, 1620.0, HEAD_N1
    tz0, tz1, apex = WING_ROOF + 12, 860.0, 1000.0
    model.box( ( t0, u0, tz0 ), ( t1, u1, tz1 ), { "default": "rw_sandstone", "-z": None, "+z": None }, STONE )
    model.box( ( t0 - 8, u0 - 8, tz1 - 20 ), ( t1 + 8, u1 + 8, tz1 ), "rw_dressed" )
    model.box( ( t0 - 4, u0 - 4, 620 ), ( t1 + 4, u1 + 4, 632 ), "rw_dressed" )
    cx, cy = ( t0 + t1 ) / 2, ( u0 + u1 ) / 2
    for face, out in ( ( "e", 1.0 ), ( "e", -1.0 ), ( "n", 1.0 ), ( "n", -1.0 ) ):
        at = ( t1 if out > 0 else t0 ) if face == "n" else ( u1 if out > 0 else u0 )
        # Belfry louvres, and the clock face in a stone ring.
        for k in range( 3 ):
            r = ( cy if face == "n" else cx ) - 60 + 60 * k
            blind_window( model, face, at, out, r - 18, r + 18, 650, 720, frame="rw_dressed" )
        centre_r = cy if face == "n" else cx
        if face == "n":
            p0, p1 = np.array( ( at, centre_r, 770.0 ) ), np.array( ( at + out * 4, centre_r, 770.0 ) )
        else:
            p0, p1 = np.array( ( centre_r, at, 770.0 ) ), np.array( ( centre_r, at + out * 4, 770.0 ) )
        tube( model, p0, p1, 48.0, "rw_dressed", sides=24, cap=True )
        q = 42.0
        if face == "n":
            clock_dial( model, ( at + out * 4.3, centre_r, 770 ), ( out, 0, 0 ), q )
        else:
            clock_dial( model, ( centre_r, at + out * 4.3, 770 ), ( 0, out, 0 ), q )
    base = [ ( t0 - 8, u0 - 8 ), ( t1 + 8, u0 - 8 ), ( t1 + 8, u1 + 8 ), ( t0 - 8, u1 + 8 ) ]
    for k in range( 4 ):
        a, b = base[k], base[( k + 1 ) % 4]
        mid = ( np.array( a ) + np.array( b ) ) / 2 - ( cx, cy )
        facing( model, "copper", [ ( *a, tz1 ), ( *b, tz1 ), ( cx, cy, apex ) ], ( mid[0], mid[1], 0.5 ) )
    model.hull( [ ( *p, tz1 ) for p in base ] + [ ( cx, cy, apex ) ], SHEET )
    model.box( ( cx - 2, cy - 2, apex - 4 ), ( cx + 2, cy + 2, apex + 40 ), "copper" )


WING_DOOR = ( 1480.0, 100.0, 200.0 )                         # centre, width, crown
WING_LIGHTS = ( 1380.0, 1600.0, 1720.0 )                    # the travel centre's windows: 70 wide, 50..180
WING_UPPER = ( 262.0, 378.0 )                                # the upper storey's windows (60 wide), over the ones below


def wing_front( model ):
    """ The wing's face to the cab road (e SHED_E, facing +e), dressed like the south front: archivolts with imposts
    and keystones on the ground floor's arches, a moulded string course, the upper storey's windows on the ground
    floor's axes in moulded surrounds with hoods and sills, Lisenen between the bays and at the corners, and a
    dentilled main cornice. """
    at = SHED_E
    c, width, crown = WING_DOOR
    A.arch_trim( model, "n", at, 1.0, c, crown - width / 2, width / 2, key=( 16.0, 26.0 ), band=7.0, proud=4.5,
                 impost_w=8.0 )
    for n in WING_LIGHTS:
        A.arch_trim( model, "n", at, 1.0, n, 145.0, 35.0, key=( 10.0, 17.0 ), band=5.0 if n < c else 6.0, proud=4.0,
                     impost_w=8.0, impost=n > c )
    # The string course between the storeys.
    string = [ ( 0.0, 0.0 ), ( 3.5, 0.0 ), ( 3.5, 1.0 ), ( 5.6, 2.6 ), ( 5.6, 8.0 ), ( 4.6, 9.0 ), ( 4.6, 11.0 ), ( 0.0, 12.0 ) ]
    P.straight( model, "n", at, HEAD_N0, HEAD_N1, 210.0, 1.0, string, "rw_dressed" )
    # The upper storey's windows: dark glass behind casement frames, in moulded surrounds.
    z0, z1 = WING_UPPER
    for n in ( WING_LIGHTS[0], c ) + WING_LIGHTS[1:]:
        r0, r1 = n - 30.0, n + 30.0
        facing( model, "rw_window_dark", [ ( at + 0.2, r0, z0 ), ( at + 0.2, r1, z0 ), ( at + 0.2, r1, z1 ), ( at + 0.2, r0, z1 ) ], ( 1, 0, 0 ) )
        transom = z0 + ( z1 - z0 ) * 0.72
        for lo, hi in ( ( ( at + 0.2, n - 1.2, z0 ), ( at + 2.0, n + 1.2, z1 ) ), ( ( at + 0.2, r0, transom - 1.2 ), ( at + 2.0, r1, transom + 1.2 ) ),
                        ( ( at + 0.2, r0, z0 ), ( at + 1.6, r0 + 2.0, z1 ) ), ( ( at + 0.2, r1 - 2.0, z0 ), ( at + 1.6, r1, z1 ) ),
                        ( ( at + 0.2, r0, z0 ), ( at + 1.6, r1, z0 + 2.4 ) ), ( ( at + 0.2, r0, z1 - 2.0 ), ( at + 1.6, r1, z1 ) ) ):
            model.box( lo, hi, "rw_steel_dark" )
        D.window_surround( model, "n", at, 1.0, r0, r1, z0, z1 )
    # Lisenen: at the corners from the plinth, and between the upper storey's bays from the string course.
    for r, width, za in ( ( 1320.0, 28.0, 36.0 ), ( 1795.0, 28.0, 36.0 ), ( 1430.0, 18.0, 222.0 ), ( 1540.0, 24.0, 222.0 ),
                          ( 1660.0, 24.0, 222.0 ) ):
        A.pilaster( model, "n", at, 1.0, r, za, 428.0, width=width, proud=5.0 )
    # The main cornice (the south front's profile) with its dentils, under the parapet.
    P.straight( model, "n", at, HEAD_N0, HEAD_N1, 430.0, 1.0, A.SOUTH_CORNICE, "rw_dressed" )
    D.dentils( model, "n", at, 1.0, HEAD_N0 + 2.0, HEAD_N1 - 2.0, 444.5 )
    model.box( ( at, HEAD_N0, 456.0 ), ( at + 3.0, HEAD_N1, 470.0 ), { "default": "rw_dressed", "-e": None } )


def hall_side( model, glass ):
    """ The hall's east side wall, its stair up to the gallery, and a kiosk. """
    w = M.Wall( "n", ( HALL_N0, HALL_N1 ), ( HALL_E, SIDE_E ), ( 0.0, 560.0 ), "+e" )
    w.add( 1720.0, 90, 0, 180, "arch" )
    for n in ( 1420.0, 1560.0, 1700.0 ):
        w.add( n, 70, 460, 532, "glass_arch" )
    w.build( model, "render_cream", "render_cream", "rw_dressed", end=None )
    lunettes = ( 1420.0, 1560.0, 1700.0 )
    glass_e = ( HALL_E + SIDE_E ) / 2
    for n in lunettes:
        pane( glass, model, "n", glass_e, n - 35, n + 35, 460, 532, "rw_glass_roof", arched=True )
        glazing_bars( model, "n", glass_e, n - 35, n + 35, 460, 530, "rw_steel", across=1, spring=497 )
        # The head's fan of glazing bars, from a small hub on the transom.
        D.radial_bars( model, "n", glass_e, n, 497.0, 34.5, angles=( 30.0, 60.0, 120.0, 150.0 ), paint="rw_steel", hub=4.0 )
        P.arch_band( model, "n", glass_e, 1.0, n, 497.0, 4.0, [ ( -1.0, 0.0 ), ( 1.0, 0.0 ), ( 1.0, 1.5 ), ( -1.0, 1.5 ), ( -1.0, 0.0 ) ],
                     "rw_steel", steps=8 )
    # Over the wing's roof the wall's outside is sandstone, with the lunettes cut through it and a plain archivolt and
    # sill round each.
    face_e, z_lo, z_hi = SIDE_E + 0.2, WING_ROOF + 12, 560.0
    runs = A.run_breaks( HALL_N0, HALL_N1, [ ( n - 35.0, n + 35.0 ) for n in lunettes ] )
    for a, b in runs:
        facing( model, "rw_sandstone", [ ( face_e, a, z_lo ), ( face_e, b, z_lo ), ( face_e, b, z_hi ), ( face_e, a, z_hi ) ], ( 1, 0, 0 ) )
    for n in lunettes:
        facing( model, "rw_sandstone", [ ( face_e, n - 35, z_lo ), ( face_e, n + 35, z_lo ), ( face_e, n + 35, 460.0 ),
                                         ( face_e, n - 35, 460.0 ) ], ( 1, 0, 0 ) )
        arc = K.arc( n, 497.0, 35.0, 16, 180.0, 0.0 )
        for ( r0, z0 ), ( r1, z1 ) in zip( arc, arc[1:] ):
            facing( model, "rw_sandstone", [ ( face_e, r0, z0 ), ( face_e, r1, z1 ), ( face_e, r1, z_hi ), ( face_e, r0, z_hi ) ], ( 1, 0, 0 ) )
        A.arch_trim( model, "n", face_e, 1.0, n, 497.0, 35.0, key=( 9.0, 14.0 ), band=6.0, proud=3.0, impost=False,
                     keystone=False )
        P.straight( model, "n", face_e, n - 42.0, n + 42.0, 460.0, 1.0,
                    [ ( 0.0, -3.0 ), ( 3.2, -3.0 ), ( 3.2, -2.2 ), ( 4.0, -2.2 ), ( 4.0, 0.0 ), ( 0.0, 1.5 ) ], "rw_dressed" )
    # Inside, the dado, pilasters and entablature are railhead_architecture.hall's (drawn whole in the centre).
    # The stair up to the gallery's corner: six steps east along the south wall to a landing in the corner, then the
    # main flight north along the side wall. The space under the main flight is walled in.
    s0, s1 = HALL_E - 60, HALL_E
    m0, m1 = HALL_N0, HALL_N0 + 64                # the landing's and the first flight's width
    rise = GALLERY_Z / 30
    low = 6 * rise
    foot = s0 - 6 * 11.0
    flight( model, "e", foot, 1, m0, m1, 0.0, 6, rise, 11.0, "rw_dressed", "rw_dressed", STONE, nosing=None )
    model.box( ( s0, m0, 0 ), ( s1, m1, low ), { "+z": "rw_dressed", "default": None }, STONE )
    tread = ( GALLERY_N0 - m1 ) / 24
    flight( model, "n", m1, 1, s0, s1, low, 24, rise, tread, "rw_dressed", "rw_dressed", STONE, nosing=None )
    model.collision_box( ( s0, m1, 0 ), ( s1, GALLERY_N0, low ), STONE )
    facing( model, "rw_dressed", [ ( s0, GALLERY_N0, 0 ), ( s1, GALLERY_N0, 0 ), ( s1, GALLERY_N0, GALLERY_Z - 12 ),
                                   ( s0, GALLERY_N0, GALLERY_Z - 12 ) ], ( 0, 1, 0 ) )
    # Parapets: along the first flight's north side, then the main flight's west side.
    sloped_wall_e( model, m1, m1 + 8, foot, s0, 0.0, 40 + rise, 40 + low, "rw_dressed", "rw_dressed", STONE )
    sloped_wall( model, s0 - 8, s0, m1, GALLERY_N0, 0.0, 40 + low, GALLERY_Z + 40, "rw_dressed", "rw_dressed", STONE )
    model.box( ( foot - 6, m1 - 3, 0 ), ( foot + 8, m1 + 11, 40 + rise + 12 ), "rw_dressed", STONE )
    model.box( ( foot - 8, m1 - 5, 40 + rise + 12 ), ( foot + 10, m1 + 13, 40 + rise + 16 ), "rw_dressed" )
    tube( model, ( foot + 8, m1 + 4, 44 + rise ), ( s0 - 4, m1 + 4, 44 + low ), 1.4, "copper", sides=8 )
    tube( model, ( s0 - 4, m1 + 4, 44 + low ), ( s0 - 4, GALLERY_N0, GALLERY_Z + 44 ), 1.4, "copper", sides=8 )
    # Preserve the hall kiosks' established cover volumes. Their finished visuals
    # are added after mirroring, so the western kiosk's lettering reads correctly.
    k0, k1, m0, m1 = 260.0, 340.0, 1480.0, 1560.0
    model.collision_box( ( k0, m0, 0 ), ( k1, m1, 100 ), WOOD )
    model.collision_box( ( k0 - 10, m0 - 10, 100 ), ( k1 + 10, m1 + 10, 114 ), SHEET )


def hall_kiosk(side):
    """Finished hall booth, without changing the existing cover collision."""
    import railhead_props as P
    model = K.Model()
    e0, e1 = (260., 340.) if side > 0 else (-340., -260.)
    P.kiosk(model, e0, e1, 1480., 1560., "-e" if side > 0 else "+e")
    model.boxes.clear()
    model.hulls.clear()
    return model


# ---------------------------------------------------------------------------------------------------------------------
# The head building's middle (centre)

def head_floor( model ):
    model.collision_box( ( -SHED_E, HEAD_N0, -60 ), ( SHED_E, HEAD_N1, 0 ), STONE )
    e_cuts = [ -SHED_E, -360.0, -352.0, -120.0, -112.0, 112.0, 120.0, 352.0, 360.0, SHED_E ]
    n_cuts = [ HEAD_N0, 1450.0, 1458.0, 1560.0, 1568.0, HEAD_N1 ]
    for ea, eb in zip( e_cuts, e_cuts[1:] ):
        for na, nb in zip( n_cuts, n_cuts[1:] ):
            band = ( eb - ea ) < 10 or ( nb - na ) < 10
            paint = "rw_terrazzo_border" if band and abs( ea ) < HALL_E else "rw_terrazzo"
            model.polygon( paint, [ ( ea, na, 0 ), ( eb, na, 0 ), ( eb, nb, 0 ), ( ea, nb, 0 ) ] )


def gable_infill( model, n_out, n_in, z0, e0, e1, top, outside, inside, step=40.0, inside_of=None ):
    """ A wall's upper part, n_out..n_in thick (n_out the outside face), from z0 up to top( e ), in strips. inside_of( e )
    picks the inside paint by where the strip is. """
    count = max( 1, int( math.ceil( ( e1 - e0 ) / step ) ) )
    out_dir = 1.0 if n_out > n_in else -1.0
    for k in range( count ):
        a, b = e0 + ( e1 - e0 ) * k / count, e0 + ( e1 - e0 ) * ( k + 1 ) / count
        ta, tb = top( a ), top( b )
        facing( model, outside, [ ( a, n_out, z0 ), ( b, n_out, z0 ), ( b, n_out, tb ), ( a, n_out, ta ) ], ( 0, out_dir, 0 ) )
        paint = inside_of( ( a + b ) / 2 ) if inside_of else inside
        facing( model, paint, [ ( a, n_in, z0 ), ( b, n_in, z0 ), ( b, n_in, tb ), ( a, n_in, ta ) ], ( 0, -out_dir, 0 ) )
        facing( model, "rw_dressed", [ ( a, n_out, ta ), ( b, n_out, tb ), ( b, n_in, tb ), ( a, n_in, ta ) ], ( 0, 0, 1 ) )
        model.hull( [ ( e, n, z ) for n in ( n_out, n_in ) for e, z in ( ( a, z0 ), ( b, z0 ), ( a, ta ), ( b, tb ) ) ], STONE )
    # These returns are exposed at the side-wall joins; close the full thickness
    # so the hall and shed cannot be seen through the gable's outer edges.
    for e, out in ( ( e0, -1.0 ), ( e1, 1.0 ) ):
        facing( model, outside, [ ( e, n_out, z0 ), ( e, n_in, z0 ), ( e, n_in, top( e ) ),
                                 ( e, n_out, top( e ) ) ], ( out, 0, 0 ) )


FACADE_DOORS = ( ( 0.0, 200.0, 320.0 ), ( -320.0, 160.0, 300.0 ), ( 320.0, 160.0, 300.0 ) )     # centre, width, crown
FACADE_WING_DOORS = ( -900.0, 900.0 )
FACADE_WING_WINDOWS = ( -1060.0, -740.0, 740.0, 1060.0 )
# The wings' doors' and windows' arches end under the wings' ceiling (WING_CEILING), so their heads don't open into
# the ceiling slab, whose edge isn't drawn: the doors' showed the sky through the slab and the empty storey above it.
WING_DOOR_CROWN, WING_WINDOW_CROWN = 200.0, 204.0


def south_facade( model, glass ):
    """ The head building's south wall, which closes the shed's north end: three arched doors from the concourse into
    the booking hall with fanlights over them, doors and windows into the wings, a cornice, the station's name in
    bronze letters, and above it the gable that rises over the shed's two spans and the hall's roof, with two clocks. """
    n_out, n_in = HEAD_N0, HALL_N0
    # Continue behind the cornice up to the gable, including its six-inch ledge.
    w = M.Wall( "e", ( -SHED_E, SHED_E ), ( n_out, n_in ), ( 0.0, 366.0 ), "-n" )
    for c, width, crown in FACADE_DOORS:
        w.add( c, width, 0, crown, "arch" )
    for c in FACADE_WING_DOORS:
        w.add( c, 120, 0, WING_DOOR_CROWN, "arch" )
    for c in FACADE_WING_WINDOWS:
        w.add( c, 90, 50, WING_WINDOW_CROWN, "glass_arch" )
    w.build( model, "rw_sandstone", "render_cream", "rw_dressed", end="rw_sandstone" )
    mid = ( n_out + n_in ) / 2
    for c, width, crown in FACADE_DOORS:
        spring = crown - width / 2
        # Fanlight: a transom at the spring, glass in the arch's head.
        model.box( ( c - width / 2, mid - 3, spring - 8 ), ( c + width / 2, mid + 3, spring ), "rw_steel" )
        model.collision_box( ( c - width / 2, mid - 3, spring - 8 ), ( c + width / 2, mid + 3, spring ), METAL )
        outline = K.arc( c, spring, width / 2, 16, 0.0, 180.0 )
        pts = [ ( r, mid, z ) for r, z in outline ]
        facing( glass, "rw_glass", pts, ( 0, -1, 0 ) )
        facing( glass, "rw_glass", pts, ( 0, 1, 0 ) )
        model.collision_box( ( c - width / 2, mid - 0.5, spring ), ( c + width / 2, mid + 0.5, crown ), GLASS )
        for k in range( 1, 4 ):
            angle = math.radians( 45 * k )
            tube( model, ( c, mid, spring ), ( c + math.cos( angle ) * width / 2, mid, spring + math.sin( angle ) * width / 2 ),
                  1.0, "rw_steel", sides=6 )
        # Its archivolt, imposts and keystone outside are railhead_architecture.south_front's.
    for c in FACADE_WING_WINDOWS:
        pane( glass, model, "e", mid, c - 45, c + 45, 50, WING_WINDOW_CROWN, "rw_glass", arched=True )
        glazing_bars( model, "e", mid, c - 45, c + 45, 50, WING_WINDOW_CROWN - 2, "rw_steel_dark", across=1,
                      spring=WING_WINDOW_CROWN - 45 )
        model.box( ( c - 50, n_out - 4, 42 ), ( c + 50, n_out, 50 ), "rw_dressed" )
    # The wings' upper windows, dark: nobody goes up there.
    for c in ( -1060.0, -900.0, -740.0, 740.0, 900.0, 1060.0 ):
        blind_window( model, "e", n_out, -1.0, c - 32, c + 32, 250, 330 )
    # Plinth, pilasters, the cornice and the band the letters sit on.
    for a, b in ( ( -SHED_E, -1105.0 ), ( -1015.0, -960.0 ), ( -840.0, -785.0 ), ( -695.0, -400.0 ), ( -240.0, -100.0 ),
                  ( 100.0, 240.0 ), ( 400.0, 695.0 ), ( 785.0, 840.0 ), ( 960.0, 1015.0 ), ( 1105.0, SHED_E ) ):
        model.box( ( a, n_out - 3, 0 ), ( b, n_out, 30 ), { "default": "rw_dressed_red", "+n": None, "-z": None } )
    # Pilasters with bases and capitals, the doors' and windows' archivolts and keystones, and the moulded cornice
    # (340..366, 17 proud, with dentils): railhead_architecture.south_front.
    pilasters = [ ( c, 15.0 if abs( c ) in ( 620.0, 470.0, 170.0 ) else 12.0 )
                  for c in ( -988.0, -812.0, -620.0, -470.0, -170.0, 170.0, 470.0, 620.0, 812.0, 988.0 ) ]
    A.south_front( model, n_out, pilasters, FACADE_DOORS, FACADE_WING_DOORS, FACADE_WING_WINDOWS, WING_DOOR_CROWN,
                   WING_WINDOW_CROWN, WALL_IN )
    model.box( ( -580.0, n_out - 3, 372 ), ( 580.0, n_out, 424 ), { "default": "rw_dressed", "+n": None } )
    # The gable over the cornice.
    gable_infill( model, n_out, n_in, 366.0, -SHED_E, SHED_E, gable_top, "rw_sandstone", "render_cream", step=40.0,
                  inside_of=lambda e: "render_cream" if abs( e ) < HALL_E else "rw_sandstone" )
    # Two clocks on the gable, over the spans' crowns' sides, and a round window over the main door.
    for c in ( -800.0, 800.0 ):
        tube( model, ( c, n_out, 560 ), ( c, n_out - 6, 560 ), 66.0, "rw_dressed", sides=28, cap=True )
        q = 55.0
        clock_dial( model, ( c, n_out - 6.3, 560 ), ( 0, -1, 0 ), q )
    tube( model, ( 0, n_out, 530 ), ( 0, n_out - 6, 530 ), 70.0, "rw_dressed", sides=28, cap=False )
    ring = [ ( 60 * math.cos( 2 * math.pi * k / 24 ), n_out - 6.2, 530 + 60 * math.sin( 2 * math.pi * k / 24 ) ) for k in range( 24 ) ]
    facing( model, "rw_window_dark", ring, ( 0, -1, 0 ) )
    for k in range( 6 ):
        a = math.pi * k / 6
        model.beam( ( -60 * math.cos( a ), n_out - 7, 530 - 60 * math.sin( a ) ), ( 60 * math.cos( a ), n_out - 7, 530 + 60 * math.sin( a ) ),
                    ( 2.0, 2.0 ), "rw_steel" )


def north_facade( model, glass ):
    """ The street front, beyond the play area: glazed doors under the gallery and tall arched windows over it. """
    n_in, n_out = HALL_N1, HEAD_N1
    w = M.Wall( "e", ( -SHED_E, SHED_E ), ( n_in, n_out ), ( 0.0, 470.0 ), "+n" )
    doors = ( ( 0.0, 140.0, 170.0 ), ( -320.0, 120.0, 160.0 ), ( 320.0, 120.0, 160.0 ) )
    windows = ( ( 0.0, 200.0, 230.0, 450.0 ), ( -320.0, 140.0, 240.0, 430.0 ), ( 320.0, 140.0, 240.0, 430.0 ) )
    for c, width, top in doors:
        w.add( c, width, 0, top, "glass" )
    for c, width, z0, z1 in windows:
        w.add( c, width, z0, z1, "glass_arch" )
    for c in ( -960.0, -760.0, 760.0, 960.0 ):
        w.add( c, 80, 50, 180, "glass_arch" )
    w.build( model, "rw_sandstone", "render_cream", "rw_dressed", end="rw_sandstone" )
    mid = ( n_in + n_out ) / 2
    for c, width, top in doors:
        pane( glass, model, "e", mid, c - width / 2, c + width / 2, 0, top, "rw_glass" )
    A.north_doors( model, mid, n_in )
    for c, width, z0, z1 in windows:
        pane( glass, model, "e", mid, c - width / 2, c + width / 2, z0, z1, "rw_glass", arched=True )
        glazing_bars( model, "e", mid, c - width / 2, c + width / 2, z0, z1 - 2, "rw_steel", across=3, spring=z1 - width / 2 )
        glazing_bars( model, "e", mid, c - width / 2, c + width / 2, z0, z1 - width / 2, "rw_steel", across=0, spring=( z0 + z1 - width / 2 ) / 2 )
    for c in ( -960.0, -760.0, 760.0, 960.0 ):
        pane( glass, model, "e", mid, c - 40, c + 40, 50, 180, "rw_glass", arched=True )
    for c in ( -1060.0, -900.0, -740.0, 740.0, 900.0, 1060.0 ):
        blind_window( model, "e", n_out, 1.0, c - 32, c + 32, 260, 380 )
    gable_infill( model, n_out, n_in, 470.0, -SIDE_E, SIDE_E, lambda e: outer_z( e ) + 20.0, "rw_sandstone", "render_cream" )


def hall_vault( model ):
    """ The booking hall's shallow barrel vault, with transverse ribs, under a copper roof. """
    n0, n1 = HALL_N0, HALL_N1
    steps = 24
    es = [ -HALL_E + 2 * HALL_E * k / steps for k in range( steps + 1 ) ]
    for a, b in zip( es, es[1:] ):
        za, zb = vault_z( a ), vault_z( b )
        facing( model, "render_cream", [ ( a, n0, za ), ( b, n0, zb ), ( b, n1, zb ), ( a, n1, za ) ], ( 0, 0, -1 ) )
    oes = [ -SIDE_E + 2 * SIDE_E * k / steps for k in range( steps + 1 ) ]
    for a, b in zip( oes, oes[1:] ):
        za, zb = outer_z( a ), outer_z( b )
        facing( model, "copper", [ ( a, HEAD_N0, za ), ( b, HEAD_N0, zb ), ( b, HEAD_N1, zb ), ( a, HEAD_N1, za ) ], ( 0, 0, 1 ) )
        ia, ib = vault_z( min( abs( a ), HALL_E ) ), vault_z( min( abs( b ), HALL_E ) )
        model.hull( [ ( e, n, z ) for n in ( n0, n1 ) for e, z in ( ( a, ia ), ( b, ib ), ( a, za ), ( b, zb ) ) ], STONE )
    # Moulded transverse ribs every 110, framed panels between them, and a bead along the crown.
    A.vault( model, vault_z, VAULT_CZ, [ n0 + 55.0 + 110.0 * k for k in range( 4 ) ] )


def gallery( model ):
    """ The gallery across the hall's north end, on four columns, behind a stone balustrade. """
    n0, n1, z = GALLERY_N0, HALL_N1, GALLERY_Z
    model.box( ( -HALL_E, n0, z - 12 ), ( HALL_E, n1, z ),
               { "+z": "rw_terrazzo", "-z": "render_cream", "-n": "rw_dressed", "default": None }, STONE )
    for c in ( -420.0, -180.0, 180.0, 420.0 ):
        model.collision_box( ( c - 14, n0 + 8 - 14, 0 ), ( c + 14, n0 + 8 + 14, 14 ), STONE )
        model.collision_box( ( c - 16, n0 + 8 - 16, z - 24 ), ( c + 16, n0 + 8 + 16, z - 12 ), STONE )
        model.cylinder( ( c, n0 + 8 ), 10.0, 14.0, z - 24, { "side": None, "top": None, "bottom": None }, sides=16, surface=STONE )
    b0, b1 = n0, n0 + 8
    e0, e1 = -HALL_E + 60, HALL_E - 60
    model.collision_box( ( e0, b0, z ), ( e1, b1, z + 42 ), STONE )
    # Columns, beam, coffers and the balustrade: railhead_architecture's.
    A.gallery( model )


def shed_columns( model ):
    """ The cast-iron columns down the shed's middle, under the valley gutter the two spans spring from. """
    for n in RIBS[:-1]:
        # The collision as it always was: a square base, the shaft and a square capital.
        model.collision_box( ( -14, n - 14, 0 ), ( 14, n + 14, 18 ), METAL )
        model.collision_box( ( -16, n - 16, 226 ), ( 16, n + 16, 238 ), METAL )
        model.cylinder( ( 0.0, n ), 8.0, 18.0, 226.0, { "side": None, "top": None, "bottom": None }, sides=16, surface=METAL )
        A.shed_column( model, n )
    model.box( ( -14, SHED_N0, GUTTER_Z[0] ), ( 14, SHED_N1, GUTTER_Z[1] ), { "default": "rw_steel", "+z": None } )
    A.valley_girder( model, SHED_N0, SHED_N1, RIBS[:-1] )


def canopy_spines( model ):
    """ The centre platform canopy's column line, on the centre line. """
    n0, n1 = FLAT_N0, SHED_N0
    A.canopy_spine( model, 0.0, CANOPY_Z, n0, n1 )
    for cn in CANOPY_COLUMNS_N:
        model.collision_box( ( -5, cn - 5, 0 ), ( 5, cn + 5, CANOPY_Z - 12 ), METAL )
        A.canopy_column( model, 0.0, cn, CANOPY_Z )


# ---------------------------------------------------------------------------------------------------------------------
# The signal box

BOX_STAIR = ( -165.0, 76.0, -1900.0, -1858.0 )        # e0, e1 (the landing from here), n0, n1


def signal_box( model, glass ):
    import railhead_signal_box
    railhead_signal_box.build( model, glass )


# ---------------------------------------------------------------------------------------------------------------------
# The roof (the east span)

ROOF_BANDS = ( ( 14.0, 180.0, "solid" ), ( 180.0, 510.0, "glass" ), ( 510.0, 540.0, "solid" ), ( 540.0, 660.0, "lantern" ),
               ( 660.0, 690.0, "solid" ), ( 690.0, 1020.0, "glass" ), ( 1020.0, WALL_IN, "solid" ) )
RIB_TOP = ( 8.0, 14.0 )         # radial depth under the skin of the top chord's faces
RIB_BOTTOM = ( 40.0, 46.0 )
LANTERN_RISE = 40.0


def roof_facets():
    """ ( e0, e1, kind ) pieces of the east span, no wider than 36. """
    out = []
    for a, b, kind in ROOF_BANDS:
        count = max( 1, int( math.ceil( ( b - a ) / 36.0 ) ) )
        for k in range( count ):
            out.append( ( a + ( b - a ) * k / count, a + ( b - a ) * ( k + 1 ) / count, kind ) )
    return out


def arc_point( theta, depth ):
    """ The east span's arc at angle theta (radians, from +e about its centre), depth under the skin. """
    r = SHED_R - depth
    return 600.0 + r * math.cos( theta ), SHED_CZ + r * math.sin( theta )


def sarking( a ):
    """ The boarding's paint under a solid roof facet starting at e a: blackened by the smoke beside the lantern and
    along the valley gutter, grey-brown elsewhere. """
    return "rhs_sarking_soot" if a < 80.0 or 500.0 <= a < 700.0 else "rhs_sarking"


def rafters( model, a, b, za, zb, paint, spacing=40.0, size=( 3.0, 6.0 ) ):
    """ Rafters ( 3 x 7 in nominal ) under a solid facet's boarding, down the slope from e a to b every spacing along
    the shed, clear of the ribs' top chords. """
    n = SHED_N0 + spacing / 2
    while n < SHED_N1 - 4:
        if all( abs( n - r ) > 9.0 for r in RIBS ):
            model.beam( ( a, n, za - size[1] / 2 - 0.05 ), ( b, n, zb - size[1] / 2 - 0.05 ), size, paint, up=( 0, 0, 1 ) )
        n += spacing


def roof( ):
    """ The east span: the skin (slate on boarding, glass bands, a smoke lantern along the crown), purlins, glazing bars,
    the lattice ribs, the south end's glazed screen and the overhead conductor rails hung from the ribs. Returns
    ( model, glass ). """
    model, glass = K.Model(), K.Model()
    n0, n1 = SHED_N0, SHED_N1
    for a, b, kind in roof_facets():
        za, zb = shed_z( a ), shed_z( b )
        if kind == "solid":
            facing( model, "slate", [ ( a, n0, za + 3 ), ( b, n0, zb + 3 ), ( b, n1, zb + 3 ), ( a, n1, za + 3 ) ], ( 0, 0, 1 ) )
            facing( model, sarking( a ), [ ( a, n0, za ), ( b, n0, zb ), ( b, n1, zb ), ( a, n1, za ) ], ( 0, 0, -1 ) )
            model.hull( [ ( e, n, z ) for n in ( n0, n1 ) for e, z in ( ( a, za ), ( b, zb ), ( a, za + 4 ), ( b, zb + 4 ) ) ], SHEET )
            rafters( model, a, b, za, zb, "rhs_sarking" )
        elif kind == "glass":
            pts = [ ( a, n0, za + 1.5 ), ( b, n0, zb + 1.5 ), ( b, n1, zb + 1.5 ), ( a, n1, za + 1.5 ) ]
            facing( glass, "rw_glass_roof", pts, ( 0, 0, 1 ) )
            facing( glass, "rw_glass_roof", pts, ( 0, 0, -1 ) )
            model.hull( [ ( e, n, z ) for n in ( n0, n1 ) for e, z in ( ( a, za + 1 ), ( b, zb + 1 ), ( a, za + 2 ), ( b, zb + 2 ) ) ], GLASS )
            # Glazing bars down the slope every 40.
            n = n0 + 20
            while n < n1:
                model.beam( ( a, n, za - 0.5 ), ( b, n, zb - 0.5 ), ( 1.5, 2.5 ), "rw_steel", up=( 0, 0, 1 ) )
                n += 40
        else:
            za2, zb2 = za + LANTERN_RISE, zb + LANTERN_RISE
            facing( model, "slate", [ ( a, n0, za2 + 3 ), ( b, n0, zb2 + 3 ), ( b, n1, zb2 + 3 ), ( a, n1, za2 + 3 ) ], ( 0, 0, 1 ) )
            facing( model, "rhs_sarking_soot", [ ( a, n0, za2 ), ( b, n0, zb2 ), ( b, n1, zb2 ), ( a, n1, za2 ) ], ( 0, 0, -1 ) )
            rafters( model, a, b, za2, zb2, "rhs_sarking" )
            model.hull( [ ( e, n, z ) for n in ( n0, n1 ) for e, z in ( ( a, za2 ), ( b, zb2 ), ( a, za2 + 4 ), ( b, zb2 + 4 ) ) ], SHEET )
            for nn, out in ( ( n0, -1.0 ), ( n1, 1.0 ) ):
                facing( model, "rw_steel_dark", [ ( a, nn, za ), ( b, nn, zb ), ( b, nn, zb2 ), ( a, nn, za2 ) ], ( 0, out, 0 ) )
    # The lantern's louvred sides.
    for e, out in ( ( 540.0, -1.0 ), ( 660.0, 1.0 ) ):
        z = shed_z( e )
        facing( model, "rw_steel_dark", [ ( e, n0, z ), ( e, n1, z ), ( e, n1, z + LANTERN_RISE ), ( e, n0, z + LANTERN_RISE ) ], ( out, 0, 0 ) )
        facing( model, "rw_steel_dark", [ ( e, n0, z ), ( e, n1, z ), ( e, n1, z + LANTERN_RISE ), ( e, n0, z + LANTERN_RISE ) ], ( -out, 0, 0 ) )
        for k in range( 1, 4 ):
            zz = z + LANTERN_RISE * k / 4
            model.box( ( e - 3 if out < 0 else e, n0, zz - 1 ), ( e if out < 0 else e + 3, n1, zz + 1 ), "rw_steel_dark" )
        model.hull( [ ( ee, n, zz ) for ee in ( e - 1, e + 1 ) for n in ( n0, n1 ) for zz in ( z, z + LANTERN_RISE ) ], SHEET )
    # Purlins along the shed.
    for e in ( 60.0, 180.0, 300.0, 420.0, 510.0, 540.0, 660.0, 690.0, 780.0, 900.0, 1020.0, 1100.0 ):
        z = shed_z( e )
        model.beam( ( e, n0, z - 4 ), ( e, n1, z - 4 ), ( 5.0, 7.0 ), "rw_steel" )
    # The ribs: lattice girders following the arc, from the valley gutter to the wall's corbel.
    th0 = math.acos( ( 14.0 - 600.0 ) / ( SHED_R - RIB_TOP[0] ) )
    th1 = math.acos( ( WALL_IN - 600.0 ) / ( SHED_R - RIB_BOTTOM[1] ) )
    count = 40
    thetas = [ th0 + ( th1 - th0 ) * k / count for k in range( count + 1 ) ]
    for n in RIBS:
        if n >= SHED_N1:
            continue
        u = 0.0
        for ta, tb in zip( thetas, thetas[1:] ):
            pa_top, pb_top = arc_point( ta, RIB_TOP[1] ), arc_point( tb, RIB_TOP[1] )
            pa_bot, pb_bot = arc_point( ta, RIB_BOTTOM[0] ), arc_point( tb, RIB_BOTTOM[0] )
            if min( pa_bot[0], pb_bot[0] ) < 14.0 or max( pa_top[0], pb_top[0] ) > WALL_IN + 1:
                pass
            for d0, d1 in ( RIB_TOP, RIB_BOTTOM ):
                qa, qb = arc_point( ta, ( d0 + d1 ) / 2 ), arc_point( tb, ( d0 + d1 ) / 2 )
                ea, eb = max( qa[0], 14.0 ), min( qb[0], WALL_IN )
                if eb <= ea:
                    continue
                model.beam( ( qa[0], n, qa[1] ), ( qb[0], n, qb[1] ), ( 10.0, d1 - d0 ), "rw_steel" )
        # The web: real flat lattice bars in an X on both faces (they were a flat texture).
        A.lattice( model, n, thetas, arc_point, ( RIB_TOP[0] + RIB_TOP[1] ) / 2, ( RIB_BOTTOM[0] + RIB_BOTTOM[1] ) / 2,
                   14.0, WALL_IN + 1, gussets=BRIDGE_N1 - 20.0 < n < BUFFER_N + 30.0 )
        if n == SHED_N0:
            A.gable_fascia( model, n, arc_point, th0, th1, -2.0, 12.0 )
        # Hangers from the rib to the conductor rails.
        if n > SHED_N0:
            for c in TRACKS.values():
                theta = math.acos( ( c - 600.0 ) / ( SHED_R - RIB_BOTTOM[1] ) )
                top = SHED_CZ + ( SHED_R - RIB_BOTTOM[1] ) * math.sin( theta )
                if BRIDGE_N0 - 20 < n < BRIDGE_N1 + 20:
                    continue
                model.box( ( c - 0.6, n - 0.6, 178 ), ( c + 0.6, n + 0.6, top ), "rw_steel_dark" )
                model.box( ( c - 2, n - 2, 172.5 ), ( c + 2, n + 2, 180 ), "rw_rubber" )
    # The rigid overhead conductor rails, 5.0 m over the rails (CONTACT_Z), to the buffer stops: under the footbridge's
    # girders (z 180).
    for c in TRACKS.values():
        model.box( ( c - 2, n0, CONTACT_Z + 1.5 ), ( c + 2, BUFFER_N - 20, CONTACT_Z + 5.5 ), "rw_steel_grey" )
        model.box( ( c - 0.5, n0, CONTACT_Z ), ( c + 0.5, BUFFER_N - 20, CONTACT_Z + 1.5 ), "copper_brown" )
    # The glazed screen across the south end, between the arch and a transom at 360.
    sn = n0 + 1.0
    bottom = 360.0
    model.box( ( 14.0, sn - 2, bottom - 14 ), ( WALL_IN, sn + 2, bottom ), "rw_steel" )
    for a, b, kind in roof_facets():
        za, zb = shed_z( a ) - RIB_BOTTOM[1], shed_z( b ) - RIB_BOTTOM[1]
        if za <= bottom + 4 and zb <= bottom + 4:
            continue
        za, zb = max( za, bottom ), max( zb, bottom )
        pts = [ ( a, sn, bottom ), ( b, sn, bottom ), ( b, sn, zb ), ( a, sn, za ) ]
        facing( glass, "rw_glass_roof", pts, ( 0, -1, 0 ) )
        facing( glass, "rw_glass_roof", pts, ( 0, 1, 0 ) )
        model.hull( [ ( e, n, z ) for n in ( sn - 0.5, sn + 0.5 ) for e, z in ( ( a, bottom ), ( b, bottom ), ( a, za ), ( b, zb ) ) ], GLASS )
    e = 60.0
    while e < WALL_IN - 20:
        top = shed_z( e ) - RIB_BOTTOM[1]
        if top > bottom + 10:
            model.box( ( e - 2, sn - 3, bottom ), ( e + 2, sn + 3, top ), "rw_steel" )
        e += 90.0
    for zz in ( 480.0, 600.0 ):
        es = [ e for e in np.linspace( 14.0, WALL_IN, 200 ) if shed_z( e ) - RIB_BOTTOM[1] > zz + 4 ]
        if es:
            model.box( ( es[0], sn - 2.5, zz - 1.5 ), ( es[-1], sn + 2.5, zz + 1.5 ), "rw_steel" )
    return model, glass


# ---------------------------------------------------------------------------------------------------------------------
# Putting it together

def east_half():
    """ ( model, glass ) of everything built on the east side, to be mirrored for the west. """
    model, glass = K.Model(), K.Model()
    for e0, e1, edges in PLATFORMS:
        platform( model, e0, e1, edges )
    track_bed( model )
    concourse( model )
    outer_wall( model, glass )
    footbridge( model, glass )
    canopies( model )
    cab_road( model, glass )
    goods_yard( model, glass )
    head_wing( model, glass )
    hall_side( model, glass )
    return model, glass


def centre():
    """ ( model, glass ) of what's built whole: the head building's middle, the shed's middle columns, the signal box. """
    model, glass = K.Model(), K.Model()
    head_floor( model )
    south_facade( model, glass )
    north_facade( model, glass )
    hall_vault( model )
    gallery( model )
    A.hall( model )
    shed_columns( model )
    bridge_columns_centre( model )
    canopy_spines( model )
    signal_box( model, glass )
    return model, glass


def build():
    """ The structure's models by name: east, west, centre, roof and glass. """
    east, east_glass = east_half()
    west = east.mirrored()
    east.extend(hall_kiosk(1))
    west.extend(hall_kiosk(-1))
    mid, mid_glass = centre()
    span, span_glass = roof()
    roof_model = K.Model().extend( span ).extend( span.mirrored() )
    glass = K.Model().extend( east_glass ).extend( east_glass.mirrored() ).extend( mid_glass ) \
        .extend( span_glass ).extend( span_glass.mirrored() )
    models = M.clean_joins( { "railhead_east": east, "railhead_west": west, "railhead_centre": mid,
                              "railhead_roof": roof_model, "railhead_glass": glass } )
    # Soot and wear zones (the materials' rw_sandstone_soot, rw_steel_soot, rw_lime_dark and rw_brick_dark).
    A.weather( models )
    # The structure's own paints (rhs_*: precast, sarking, the footbridge's panels, the goods shed's doors).
    SP.apply( models )
    return models


if __name__ == "__main__":
    for name, m in build().items():
        b = m.bounds()
        print( f"{name}: {m.triangle_count()} triangles, {len( m.boxes )} boxes, {len( m.hulls )} hulls, "
               f"paints {len( m.polygons )}, bounds {np.round( b[0] ).tolist()}..{np.round( b[1] ).tolist()}" )
