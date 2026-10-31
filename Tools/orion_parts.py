"""
Orion's pieces: what Tools/orion_map.py builds the launch facility from, on map_kit's Model (plan coordinates: e east,
n north, z up, inches). Riverdale's pieces (Tools/riverdale_parts.py: pipes, railings, stairs, cases, lamps, louvres,
doors) are used as they are, painted rv_; repaint() turns their paints into Orion's (RV_PAINTS) before a model is
written. New here:

- Lattice towers (lightning masts, radio masts, floodlight towers, the pylon), drawn as box beams: four legs tapering
  up, X bracing in each panel, struts, platforms with rails, a beacon on top.
- The launch vehicle: a white two-stage rocket turned round its axis (gold band under the fairing, a dark interstage,
  four fins and its engine bells), the mark and ORN down its side; the launch mount it stands on; the two service
  towers either side of it (orange lattice steel, a floor every 8 ft, small work lamps, swing arms to the rocket).
- The radome: a white geodesic sphere on a lattice ring.
- Floodlight poles and their lamp heads; tube lights on walls; flags and banners.
- Equipment cases in rows and stacks, some under a draped tarp; red crates; a lumpy tarped pile.
- Pipes with yellow bands and saddle supports.
- Lettering and signs from Tools/orion_textures.py's atlases.
Light fixtures add point lights to riverdale_parts.LIGHTS, which the scene builds.
"""
import math
from collections import defaultdict

import numpy as np

import map_kit as K
import orion_textures as OT
import riverdale_parts as P
from riverdale_parts import v, unit, card, box, obox, perp, rod, UP, METAL, STONE, SHEET, WOOD, PLASTIC

WARM, WARM_DIM, COOL, RED = P.WARM, P.WARM_DIM, P.COOL, P.RED
FLOOD = "1.00,0.86,0.66,1"
SODIUM = "1.00,0.70,0.40,1"
RED_ROOM = "1.00,0.16,0.10,1"

# Riverdale's paints, as Orion paints them.
RV_PAINTS = {
    "rv_dark": "oa_dark", "rv_black": "oa_black", "rv_steel": "oa_steel", "rv_zinc": "oa_zinc", "rv_frame": "oa_frame",
    "rv_plinth": "oa_wall_dark", "rv_window_dark": "oa_window_dark", "rv_lamp_warm": "oa_lamp_warm",
    "rv_lamp_cool": "oa_lamp_cool", "rv_lamp_cyan": "oa_lamp_cool", "rv_beacon": "oa_beacon", "rv_louvre": "oa_frame",
    "rv_door": "oa_door", "rv_yellow": "oa_yellow", "rv_grating": "oa_grating", "rv_olive": "oa_olive", "rv_case": "oa_case",
    "rv_pipe": "oa_pipe", "rv_white": "oa_white_steel", "rv_ring_orange": "oa_red", "rv_ring_white": "oa_white_steel",
    "rv_rubber": "oa_rubber", "rv_wall": "oa_wall", "rv_hazard": "oa_hazard",
}


def reset():
    P.reset()
    RED_CRATES.clear()


def repaint( model, mapping=RV_PAINTS ):
    """ Renames paints in place, keeping each polygon's authored UVs and normals with it. """
    polygons, uvs, normals = defaultdict( list ), {}, {}
    for paint, items in model.polygons.items():
        target = mapping.get( paint, paint )
        for i, item in enumerate( items ):
            j = len( polygons[target] )
            if ( paint, i ) in model.polygon_uvs:
                uvs[( target, j )] = model.polygon_uvs[( paint, i )]
            if ( paint, i ) in model.polygon_normals:
                normals[( target, j )] = model.polygon_normals[( paint, i )]
            polygons[target].append( item )
    model.polygons, model.polygon_uvs, model.polygon_normals = polygons, uvs, normals
    model.grain_paints = { mapping.get( p, p ) for p in model.grain_paints }
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Atlas quads

def _atlas_quad( m, paint, table, size, name, centre, right, up, h, off ):
    a = OT.aspect( table, name )
    uv = [ OT.atlas_uv( table, size, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    P.quad( m, paint, centre, right, up, h * a, h, uv, off )
    return h * a


def letters( m, name, centre, right, h, tone="dark", up=UP, off=0.4 ):
    """ Lettering or the mark, h tall, on the face whose right is right (it faces cross( right, up )). Returns its
    width. """
    return _atlas_quad( m, f"oa_letters_{tone}", OT.LETTERS, OT.LETTER_ATLAS, name, centre, right, up, h, off )


def plate( m, name, centre, right, h, up=UP, off=0.3, both=False ):
    w = _atlas_quad( m, "oa_plates", OT.PLATES, OT.PLATE_ATLAS, name, centre, right, up, h, off )
    if both:
        _atlas_quad( m, "oa_plates", OT.PLATES, OT.PLATE_ATLAS, name, centre, -unit( right ), up, h, off )
    return w


def screen( m, name, centre, right, h, up=UP, off=0.2 ):
    return _atlas_quad( m, "oa_screens", OT.SCREENS, OT.SCREEN_ATLAS, name, centre, right, up, h, off )


# ---------------------------------------------------------------------------------------------------------------------
# Lattice steel

def beam( m, a, b, t, paint ):
    m.beam( v( *a ), v( *b ), ( t, t ), paint )


def lattice_tower( m, base, height, w0, w1, paint="oa_steel", panel=None, leg=3.0, brace=1.4, platforms=(), name="tower",
                   beacon=True, light=True, cap=None ):
    """ A four-legged lattice mast: legs from a square w0 across at the foot to w1 at the top, X bracing in each panel,
    struts at each panel's top, platforms (heights) with a rail round them, a beacon on top. Drawn only. Returns the top
    centre. """
    c = v( *base )
    panel = panel or max( 40.0, min( 140.0, ( w0 + w1 ) * 0.9 ) )
    count = max( 1, int( round( height / panel ) ) )
    zs = [ height * ( k / count ) ** 0.96 for k in range( count + 1 ) ]

    def corners( z ):
        w = ( w0 + ( w1 - w0 ) * z / height ) / 2
        return [ c + v( sx * w, sy * w, z ) for sx, sy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ]

    for k in range( count ):
        lo, hi = corners( zs[k] ), corners( zs[k + 1] )
        for i in range( 4 ):
            beam( m, lo[i], hi[i], leg, paint )
            j = ( i + 1 ) % 4
            beam( m, lo[i], hi[j], brace, paint )
            beam( m, lo[j], hi[i], brace, paint )
            beam( m, hi[i], hi[j], brace * 1.2, paint )
    for z in platforms:
        w = ( w0 + ( w1 - w0 ) * z / height ) / 2 + 14
        box( m, c[0] - w, c[0] + w, c[1] - w, c[1] + w, c[2] + z - 1.5, c[2] + z, "oa_grating" )
        pts = [ ( c[0] - w, c[1] - w ), ( c[0] + w, c[1] - w ), ( c[0] + w, c[1] + w ), ( c[0] - w, c[1] + w ) ]
        P.railing( m, pts, c[2] + z, paint, height=38, post_every=40, kick=False, closed=True )
    top = c + UP * height
    if cap:
        beam( m, top, top + UP * cap, leg * 0.8, paint )
        top = top + UP * cap
    if beacon:
        P.beacon( m, f"{name} beacon", top, light=light )
    return top


def floodlight_pole( m, name, base, h, facing, heads=4, light=True, radius=1800, shadows=False, paint="oa_steel" ):
    """ A tall tapered pole with a frame of floodlight heads at its top, aimed along facing (plan) and down. """
    c = v( *base )
    P.lathe( m, ( c[0], c[1] ), [ ( 9.0, c[2] ), ( 9.0, c[2] + 12 ), ( 6.5, c[2] + 18 ), ( 4.0, c[2] + h ) ], paint, 10 )
    f = unit( ( facing[0], facing[1], 0 ) )
    s = np.cross( UP, f )
    top = c + UP * h
    beam( m, top - s * ( heads * 9 ) + f * 4, top + s * ( heads * 9 ) + f * 4, 2.5, paint )
    beam( m, top - s * ( heads * 9 ) + f * 4 + UP * 20, top + s * ( heads * 9 ) + f * 4 + UP * 20, 2.5, paint )
    for k in range( heads ):
        for row in ( 0, 1 ):
            q = top + s * ( ( k - ( heads - 1 ) / 2 ) * 18 ) + f * 8 + UP * ( row * 20 + 4 )
            m.oriented_box( q, ( f, s, UP ), ( 6, 14, 12 ), "oa_dark" )
            card( m, "oa_lamp_flood", [ q + f * 3.05 - s * 6 - UP * 5, q + f * 3.05 + s * 6 - UP * 5, q + f * 3.05 + s * 6 + UP * 5,
                                       q + f * 3.05 - s * 6 + UP * 5 ], f )
    if light:
        P.LIGHTS.append( ( name, tuple( top + f * 60 - UP * 40 ), FLOOD, radius, shadows ) )
    return top


def tube_light( m, name, at, out, length=48.0, kind="cool", radius=300, light=True, shadows=False, colour=None ):
    """ A fluorescent batten on a wall facing out: a slim housing and its lit diffuser. """
    out = unit( ( out[0], out[1], 0 ) )
    right = np.cross( UP, out )
    c = v( *at ) + out * 2.5
    obox( m, c, right, ( length, 5, 4 ), "oa_dark" )
    lens = "oa_lamp_cool" if kind == "cool" else "oa_lamp_warm"
    p = c + out * 2.55
    card( m, lens, [ p - right * ( length / 2 - 1.5 ) - UP * 1.6, p + right * ( length / 2 - 1.5 ) - UP * 1.6, p + right * ( length / 2 - 1.5 ) + UP * 1.6,
                     p - right * ( length / 2 - 1.5 ) + UP * 1.6 ], out )
    q = c - UP * 2.05
    card( m, lens, [ q - right * ( length / 2 - 1.5 ) - out * 2, q + right * ( length / 2 - 1.5 ) - out * 2, q + right * ( length / 2 - 1.5 ) + out * 2,
                     q - right * ( length / 2 - 1.5 ) + out * 2 ], -UP )
    if light:
        P.LIGHTS.append( ( name, tuple( c + out * 24 - UP * 8 ), colour or ( COOL if kind == "cool" else WARM ), radius, shadows ) )


def work_lamp( m, at, light_name=None, radius=160 ):
    """ A small caged lamp on the service towers: a lit bulb in a dark cage. """
    c = v( *at )
    box( m, c[0] - 3.5, c[0] + 3.5, c[1] - 3.5, c[1] + 3.5, c[2] - 3.5, c[2] + 3.5, "oa_lamp_warm" )
    if light_name:
        P.LIGHTS.append( ( light_name, tuple( c ), SODIUM, radius, False ) )


# ---------------------------------------------------------------------------------------------------------------------
# The launch vehicle, its mount and service towers

def rocket( m, base, height=1226.0, r=78.0, sides=28, logo_facing=( 0, -1 ) ):
    """ A two-stage launch vehicle standing on base (plan, the bottom of its engine skirt): a flared skirt over four
    engine bells, four swept fins, the white first stage, a dark interstage band, the second stage, a gold band, then the
    payload fairing's ogive. The mark and ORN run down its side towards logo_facing. Returns its axis' top. """
    c = v( *base )
    z0 = c[2]
    H = height
    # The picture's: a long white first stage, a thin dark interstage band, a white ring, a narrow gold band, the white
    # second stage, then a blunt ogive fairing whose tip just reaches the picture's top edge.
    skirt, s1, inter, gold0, band, fairing = 0.05, 0.719, 0.729, 0.770, 0.788, 0.901
    prof = [ ( r * 1.06, z0 ), ( r * 1.06, z0 + H * 0.02 ), ( r, z0 + H * skirt ) ]
    P.lathe( m, ( c[0], c[1] ), prof, "oa_rocket_dark", sides )
    P.lathe( m, ( c[0], c[1] ), [ ( r, z0 + H * skirt ), ( r, z0 + H * s1 ) ], "oa_rocket", sides )
    P.lathe( m, ( c[0], c[1] ), [ ( r, z0 + H * s1 ), ( r, z0 + H * inter ) ], "oa_rocket_dark", sides )
    P.lathe( m, ( c[0], c[1] ), [ ( r, z0 + H * inter ), ( r, z0 + H * gold0 ) ], "oa_rocket", sides )
    P.lathe( m, ( c[0], c[1] ), [ ( r, z0 + H * gold0 ), ( r, z0 + H * band ) ], "oa_gold", sides )
    P.lathe( m, ( c[0], c[1] ), [ ( r * 0.98, z0 + H * band ), ( r * 0.98, z0 + H * fairing ) ], "oa_rocket", sides )
    # The fairing: an ogive to a rounded tip.
    ogive = []
    for k in range( 9 ):
        t = k / 8
        ogive.append( ( r * math.sqrt( max( 0.0, 1 - t * t ) ) * ( 1 - 0.04 * t ), z0 + H * fairing + H * ( 1 - fairing ) * t ) )
    ogive[-1] = ( 0.0, z0 + H )
    P.lathe( m, ( c[0], c[1] ), [ ( r * 0.98, z0 + H * fairing ) ] + ogive[1:], "oa_rocket", sides )
    # Engine bells under the skirt.
    for k in range( 4 ):
        a = math.pi / 4 + k * math.pi / 2
        q = ( c[0] + math.cos( a ) * r * 0.45, c[1] + math.sin( a ) * r * 0.45 )
        P.lathe( m, q, [ ( r * 0.32, z0 - 26 ), ( r * 0.22, z0 - 6 ), ( r * 0.12, z0 + 2 ) ], "oa_nozzle", 12 )
    # Four fins, swept, at the base.
    for k in range( 4 ):
        a = k * math.pi / 2 + math.pi / 4
        d = v( math.cos( a ), math.sin( a ), 0 )
        s = np.cross( UP, d )
        root0, root1 = c + d * r * 0.98 + UP * ( H * 0.012 ), c + d * r * 0.98 + UP * ( H * 0.2 )
        tip0, tip1 = c + d * ( r * 1.9 ) + UP * ( -H * 0.012 ), c + d * ( r * 1.75 ) + UP * ( H * 0.07 )
        th = s * 2.2
        for sg in ( -1, 1 ):
            card( m, "oa_rocket", [ root0 + th * sg, tip0 + th * sg, tip1 + th * sg, root1 + th * sg ], s * sg )
        card( m, "oa_rocket_dark", [ tip0 - th, tip0 + th, tip1 + th, tip1 - th ], d )
        card( m, "oa_rocket", [ tip1 - th, tip1 + th, root1 + th, root1 - th ], UP + d * 0.4 )
        card( m, "oa_rocket_dark", [ root0 - th, root0 + th, tip0 + th, tip0 - th ], -UP )
    # The mark and ORN down the side.
    f = unit( ( logo_facing[0], logo_facing[1], 0 ) )
    right = np.cross( UP, f )
    letters( m, "mark", c + f * ( r + 0.6 ) + UP * ( z0 - c[2] + H * 0.478 ), right, r * 1.2, "dark", off=0.0 )
    letters( m, "orn", c + f * ( r + 0.6 ) + UP * ( z0 - c[2] + H * 0.342 ), right, r * 2.6, "dark", off=0.0 )
    return c + UP * H


def launch_mount( m, centre, top_z, w=520.0, d=520.0, hole=220.0, name="mount" ):
    """ The launch table: a steel deck on four square legs over the flame trench, its middle open under the rocket,
    hold-down arms, cable masts and umbilical boxes, pipes. top_z is its deck's top. """
    c = v( centre[0], centre[1], 0 )
    leg = 60.0
    deck_t = 36.0
    zt = top_z
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            q = c + v( sx * ( w / 2 - leg / 2 ), sy * ( d / 2 - leg / 2 ), 0 )
            box( m, q[0] - leg / 2, q[0] + leg / 2, q[1] - leg / 2, q[1] + leg / 2, 0, zt - deck_t, "oa_steel" )
    # The deck, a ring round the hole.
    h2 = hole / 2
    for e0, e1, n0, n1 in ( ( -w / 2, w / 2, -d / 2, -h2 ), ( -w / 2, w / 2, h2, d / 2 ), ( -w / 2, -h2, -h2, h2 ), ( h2, w / 2, -h2, h2 ) ):
        box( m, c[0] + e0, c[0] + e1, c[1] + n0, c[1] + n1, zt - deck_t, zt, { "default": "oa_steel", "+z": "oa_grating" } )
    P.railing( m, [ ( c[0] - w / 2 + 4, c[1] - d / 2 + 4 ), ( c[0] + w / 2 - 4, c[1] - d / 2 + 4 ), ( c[0] + w / 2 - 4, c[1] + d / 2 - 4 ),
                    ( c[0] - w / 2 + 4, c[1] + d / 2 - 4 ) ], zt, "oa_yellow", height=36, post_every=60, closed=True )
    # Hold-down arms reaching to the rocket's skirt.
    for k in range( 4 ):
        a = math.pi / 4 + k * math.pi / 2
        dvec = v( math.cos( a ), math.sin( a ), 0 )
        beam( m, c + dvec * ( h2 + 30 ) + UP * zt, c + dvec * ( h2 - 10 ) + UP * ( zt + 40 ), 10, "oa_steel" )
    for k, ( sx, sy ) in enumerate( ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ):
        q = c + v( sx * ( w / 2 - 40 ), sy * ( d / 2 - 40 ), zt )
        box( m, q[0] - 14, q[0] + 14, q[1] - 10, q[1] + 10, zt, zt + 40, "oa_dark" )
        work_lamp( m, q + v( 0, 0, 46 ), f"{name} lamp {k}" if k % 2 == 0 else None, 220 )
    # Pipes along the deck's sides.
    for k, r_ in enumerate( ( 9.0, 6.0, 6.0 ) ):
        P.pipe( m, [ ( c[0] - w / 2 - 20, c[1] - d / 2 + 30 + k * 22, zt - deck_t - 20 ), ( c[0] + w / 2 + 20, c[1] - d / 2 + 30 + k * 22, zt - deck_t - 20 ) ],
                r_, "oa_pipe", 10 )


def service_tower( m, base, w, d, h, floor=96.0, paint="oa_orange", name="gantry", lights=6, arms_to=None, cap=None, ledges=(),
                   lamp_radius=340 ):
    """ A launch service tower: a rectangular lattice of steel columns and girders, a floor every floor inches with grating
    and rails, X bracing, small work lamps on the floors (lights of them cast light), swing arms reaching towards
    arms_to (plan point) at a few floors. ledges: ( floor, side 0-3 for -y +y -x +x, depth, width share ) work platforms
    cantilevered off the faces, each with a rail, a lamp casting light on the steel and a brace under it, so the tower's
    outline steps as the picture's do. Drawn only. """
    c = v( *base )
    cols_w = max( 2, int( round( w / 62 ) ) + 1 )
    cols_d = max( 2, int( round( d / 62 ) ) + 1 )
    xs = np.linspace( -w / 2, w / 2, cols_w )
    ys = np.linspace( -d / 2, d / 2, cols_d )
    floors = int( h // floor )
    t = 7.0
    for x in xs:
        for y in ys:
            if 0 < list( xs ).index( x ) < cols_w - 1 and 0 < list( ys ).index( y ) < cols_d - 1:
                continue
            beam( m, c + v( x, y, 0 ), c + v( x, y, h ), t * 1.4, paint )
    # The lift shaft every fixed service structure has: slim and dark, so the sky still shows through most bays, as in
    # the picture (a wide core read as a solid block).
    cw, cd = w * 0.2, d * 0.2
    box( m, c[0] - cw / 2, c[0] + cw / 2, c[1] - cd / 2, c[1] + cd / 2, c[2], c[2] + h - floor, { "default": "oa_dark", "+z": "oa_grating" } )
    rng = np.random.default_rng( int( abs( c[0] ) + abs( c[1] ) ) )
    lit = 0
    for k in range( 1, floors + 1 ):
        z = k * floor
        rim = "oa_orange" if paint == "oa_gantry" else paint
        for x0, x1 in zip( xs, xs[1:] ):
            for y in ( ys[0], ys[-1] ):
                beam( m, c + v( x0, y, z ), c + v( x1, y, z ), t, rim )
                beam( m, c + v( x0, y, z - floor ), c + v( x1, y, z ), t * 0.6, paint )
                beam( m, c + v( x1, y, z - floor ), c + v( x0, y, z ), t * 0.6, paint )
        for y0, y1 in zip( ys, ys[1:] ):
            for x in ( xs[0], xs[-1] ):
                beam( m, c + v( x, y0, z ), c + v( x, y1, z ), t, rim )
                beam( m, c + v( x, y0, z - floor ), c + v( x, y1, z ), t * 0.6, paint )
                beam( m, c + v( x, y1, z - floor ), c + v( x, y0, z ), t * 0.6, paint )
        box( m, c[0] - w / 2, c[0] + w / 2, c[1] - d / 2, c[1] + d / 2, c[2] + z - 2, c[2] + z, "oa_grating" )
        # Work lamps: a handful on each floor's edge (the picture's towers glitter with them), the odd one casting light.
        for j in range( 7 ):
            side = rng.integers( 4 )
            f = rng.uniform( -0.45, 0.45 )
            if side == 0:
                q = c + v( f * w, -d / 2 - 3, z + 30 )
            elif side == 1:
                q = c + v( f * w, d / 2 + 3, z + 30 )
            elif side == 2:
                q = c + v( -w / 2 - 3, f * d, z + 30 )
            else:
                q = c + v( w / 2 + 3, f * d, z + 30 )
            cast = lit < lights and rng.random() < 0.2
            work_lamp( m, q, f"{name} lamp {k}.{j}" if cast else None, lamp_radius )
            lit += int( cast )
    if arms_to is not None:
        target = v( arms_to[0], arms_to[1], 0 )
        for k in ( floors // 4, floors // 2, int( floors * 0.78 ) ):
            z = k * floor + c[2]
            near = c + v( 0, 0, 0 )
            dvec = unit( ( target - near ) * v( 1, 1, 0 ) )
            start = near + dvec * ( min( w, d ) / 2 ) + UP * ( z - c[2] )
            end = target + UP * z - dvec * 80
            s = np.cross( UP, dvec )
            for sg in ( -1, 1 ):
                beam( m, start + s * 14 * sg, end + s * 14 * sg, 5, paint )
                beam( m, start + s * 14 * sg - UP * 30, end + s * 14 * sg - UP * 10, 4, paint )
            box( m, min( start[0], end[0] ) - 2, max( start[0], end[0] ) + 2, min( start[1], end[1] ) - 2, max( start[1], end[1] ) + 2, z - 2, z, "oa_grating" )
    rim = "oa_orange" if paint == "oa_gantry" else paint
    for k, side, depth, share in ledges:
        z = c[2] + k * floor
        half = ( w if side < 2 else d ) * share / 2
        out = ( v( 0, -1, 0 ), v( 0, 1, 0 ), v( -1, 0, 0 ), v( 1, 0, 0 ) )[side]
        along = np.cross( UP, out )
        face = c + out * ( ( d if side < 2 else w ) / 2 ) + UP * ( z - c[2] )
        corners = [ face - along * half, face + along * half, face + along * half + out * depth, face - along * half + out * depth ]
        lo, hi = np.min( corners, 0 ), np.max( corners, 0 )
        box( m, lo[0], hi[0], lo[1], hi[1], z - 2, z, "oa_grating" )
        for sg in ( -1, 1 ):
            beam( m, face + along * half * sg, face + along * half * sg + out * depth, t * 0.8, rim )
            beam( m, face + along * half * sg - UP * floor * 0.6, face + along * half * sg + out * depth * 0.9, t * 0.5, paint )
        beam( m, corners[2], corners[3], t * 0.8, rim )
        rail = [ ( p[0], p[1] ) for p in ( corners[0], corners[3], corners[2], corners[1] ) ]
        P.railing( m, rail, z, "oa_yellow", height=40, post_every=48, kick=False )
        work_lamp( m, face + out * depth * 0.6 + UP * 44, f"{name} ledge lamp {k}.{side}", lamp_radius )
    if cap:
        cap( m, c + UP * h )


def striped_tank( m, base, r, h, sides=20 ):
    """ A tall tank or water tower top painted in red and white bands (the reference's striped top behind the rocket). """
    c = v( *base )
    n = 8
    for k in range( n ):
        P.lathe( m, ( c[0], c[1] ), [ ( r, c[2] + h * k / n ), ( r, c[2] + h * ( k + 1 ) / n ) ], "oa_red" if k % 2 == 0 else "oa_white_steel", sides )
    P.lathe( m, ( c[0], c[1] ), [ ( r, c[2] + h ), ( r * 0.7, c[2] + h + r * 0.4 ), ( 0.0, c[2] + h + r * 0.55 ) ], "oa_red", sides )


# ---------------------------------------------------------------------------------------------------------------------
# The radome

def radome( m, centre, R, base_h, rings=14, sides=36 ):
    """ A geodesic radome: a sphere of radius R whose bottom fifth is cut off, on a ring of lattice legs base_h tall. centre
    is the ground under it. """
    c = v( *centre )
    zc = c[2] + base_h + R * 0.72
    prof = []
    for k in range( rings + 1 ):
        a = -math.asin( 0.72 ) + ( math.pi / 2 + math.asin( 0.72 ) ) * k / rings
        prof.append( ( R * math.cos( a ), zc + R * math.sin( a ) ) )
    prof[-1] = ( 0.0, zc + R )
    P.lathe( m, ( c[0], c[1] ), prof, "oa_radome", sides )
    rb = R * math.cos( math.asin( 0.72 ) )
    zb = zc - R * 0.72
    P.lathe( m, ( c[0], c[1] ), [ ( rb + 6, zb - 8 ), ( rb + 6, zb + 4 ) ], "oa_steel", sides )
    n = 10
    for k in range( n ):
        a0 = 2 * math.pi * k / n
        a1 = 2 * math.pi * ( k + 1 ) / n
        p0 = c + v( math.cos( a0 ) * rb, math.sin( a0 ) * rb, 0 )
        p1 = c + v( math.cos( a1 ) * rb, math.sin( a1 ) * rb, 0 )
        beam( m, p0, p0 + UP * ( zb - c[2] ), 10, "oa_steel" )
        beam( m, p0, p1 + UP * ( zb - c[2] ), 4, "oa_steel" )
        beam( m, p1, p0 + UP * ( zb - c[2] ), 4, "oa_steel" )
        beam( m, p0 + UP * ( zb - c[2] ) * 0.5, p1 + UP * ( zb - c[2] ) * 0.5, 5, "oa_steel" )
    box( m, c[0] - rb * 0.5, c[0] + rb * 0.5, c[1] - rb * 0.5, c[1] + rb * 0.5, c[2], c[2] + base_h * 0.45, "oa_render_grey" )


# ---------------------------------------------------------------------------------------------------------------------
# Cases, crates, tarps

def case( m, c, size, along=( 1, 0 ), paint="rv_olive", z0=0.0, surface=PLASTIC ):
    P.case( m, c, size, along, paint, z0, surface )


PALLET_H = 5.7      # a Euro pallet's height (144 mm)


def pallet( m, centre, along, L, W, z0=0.0, paint="oa_pallet" ):
    """ A wooden pallet under a load, L along `along` by W: five top boards, three rows of blocks, three bottom boards. """
    a = unit( ( along[0], along[1], 0 ) )
    s = np.cross( UP, a )
    c = v( centre[0], centre[1], z0 )
    for k in range( 5 ):
        m.oriented_box( c + s * ( ( k - 2 ) * ( W - W * 0.14 ) / 4 ) + UP * ( PALLET_H - 0.45 ), ( a, s, UP ), ( L, W * 0.14, 0.9 ), paint )
    for i in ( -1, 0, 1 ):
        for j in ( -1, 0, 1 ):
            m.oriented_box( c + a * ( i * ( L - L * 0.12 ) / 2 ) + s * ( j * ( W - W * 0.14 ) / 2 ) + UP * ( PALLET_H / 2 ), ( a, s, UP ),
                            ( L * 0.12, W * 0.14, PALLET_H - 1.8 ), paint )
    for j in ( -1, 0, 1 ):
        m.oriented_box( c + s * ( j * ( W - W * 0.14 ) / 2 ) + UP * 0.45, ( a, s, UP ), ( L, W * 0.14, 0.9 ), paint )


def case_block( m, origin, along, cols, rows, size=( 52, 32, 30 ), layers=1, paint="rv_olive", gap=2.0, tarp=False,
                surface=PLASTIC, seed=0, z0=0.0, pallets=False, tarp_paint="oa_tarp" ):
    """ A block of equal cases, cols along `along` and rows across it, layers high, from origin (its corner, plan),
    optionally under a draped tarp and on pallets. Returns ( length, width, height ). Collision: one box for the
    block. """
    rng = np.random.default_rng( seed )
    a = unit( ( along[0], along[1], 0 ) )
    s = np.cross( UP, a )
    L, W, H = size
    o = v( origin[0], origin[1], 0 )
    total_l, total_w, total_h = cols * ( L + gap ) - gap, rows * ( W + gap ) - gap, layers * H
    if pallets:
        mid = o + a * ( total_l / 2 ) + s * ( total_w / 2 )
        pallet( m, ( mid[0], mid[1] ), a, total_l + 2, total_w + 2, z0 )
        z0 += PALLET_H
    for layer in range( layers ):
        for i in range( cols ):
            for j in range( rows ):
                c = o + a * ( i * ( L + gap ) + L / 2 ) + s * ( j * ( W + gap ) + W / 2 ) + v( *rng.normal( 0, 0.6, 2 ), 0 )
                if tarp and layer == layers - 1:
                    continue
                P.case( m, ( c[0], c[1] ), ( L, W, H ), a, paint, z0 + layer * H, None )
    if tarp:
        drape( m, o + UP * z0, a, total_l, total_w, total_h, seed=seed, paint=tarp_paint )
    base = z0 - ( PALLET_H if pallets else 0.0 )
    tall = total_h + ( PALLET_H if pallets else 0.0 )
    centre = o + a * ( total_l / 2 ) + s * ( total_w / 2 ) + UP * ( base + tall / 2 )
    m.oriented_box( centre, ( a, s, UP ), ( total_l, total_w, tall ), { "default": None }, surface )
    return total_l, total_w, tall


def drape( m, origin, along, L, W, H, sag=4.0, hang=0.62, seed=0, paint="oa_tarp" ):
    """ A tarp pulled over a block L x W x H (origin its corner): a top that sags a little between the ridges of what's
    under it, sides hanging most of the way down with a wavy hem, the corners folded. """
    rng = np.random.default_rng( seed + 7 )
    a = unit( ( along[0], along[1], 0 ) )
    s = np.cross( UP, a )
    o = v( origin[0], origin[1], origin[2] if len( origin ) > 2 else 0.0 )
    nu, nv = max( 4, int( L / 14 ) ), max( 3, int( W / 14 ) )
    top = np.zeros( ( nu + 1, nv + 1 ) )
    for i in range( nu + 1 ):
        for j in range( nv + 1 ):
            u, w_ = i / nu, j / nv
            edge = min( u, 1 - u, w_, 1 - w_ )
            top[i, j] = H + 1.5 - sag * ( 1 - abs( math.cos( u * math.pi * max( 1, round( L / 52 ) ) ) ) ) * min( 1, edge * 6 ) + rng.normal( 0, 0.6 )

    def tp( i, j ):
        return o + a * ( L * i / nu ) + s * ( W * j / nv ) + UP * top[i, j]

    for i in range( nu ):
        for j in range( nv ):
            card( m, paint, [ tp( i, j ), tp( i + 1, j ), tp( i + 1, j + 1 ), tp( i, j + 1 ) ], UP )
    # The sides: from the top's edge down to a wavy hem, pushed out a little.
    hem = H * ( 1 - hang )

    def side( pts_top, out ):
        n = len( pts_top )
        for k in range( n - 1 ):
            p0, p1 = pts_top[k], pts_top[k + 1]
            h0 = hem + 3 * math.sin( k * 1.3 + seed ) + rng.normal( 0, 1 )
            h1 = hem + 3 * math.sin( ( k + 1 ) * 1.3 + seed ) + rng.normal( 0, 1 )
            q0 = v( p0[0], p0[1], o[2] ) + out * 1.8 + UP * h0
            q1 = v( p1[0], p1[1], o[2] ) + out * 1.8 + UP * h1
            card( m, paint, [ q0, q1, p1 + out * 0.6, p0 + out * 0.6 ], out )

    side( [ tp( i, 0 ) for i in range( nu + 1 ) ], -s )
    side( [ tp( i, nv ) for i in range( nu + 1 ) ][::-1], s )
    side( [ tp( 0, j ) for j in range( nv + 1 ) ][::-1], -a )
    side( [ tp( nu, j ) for j in range( nv + 1 ) ], a )
    # Straps round it.
    for f in ( 0.25, 0.75 ):
        i = int( round( f * nu ) )
        pts = [ tp( i, j ) + UP * 0.4 for j in range( nv + 1 ) ]
        for p0, p1 in zip( pts, pts[1:] ):
            card( m, "oa_black", [ p0 - a * 1.2, p0 + a * 1.2, p1 + a * 1.2, p1 - a * 1.2 ], UP )


RED_CRATES = []     # the crates red_crate has placed: ( plan position, heading, size ), for orion_map's write_scene


def red_crate( m, c, along, size=( 40, 30, 34 ), z0=0.0, surface=METAL ):
    """ A red steel transit crate. Only its collision box goes in the merged model. Sources/Orion/red_crate_v2's model draws it, placed by the
    scene, with its latches on the side towards cross( UP, along ). """
    a = unit( ( along[0], along[1], 0 ) )
    L, W, H = size
    obox( m, v( c[0], c[1], z0 + H / 2 ), a, ( L, W, H ), { "default": None }, surface )
    RED_CRATES.append( ( ( c[0], c[1], z0 ), math.degrees( math.atan2( a[1], a[0] ) ), size ) )


def tarp_pile( m, centre, L, W, H, along=( 1, 0 ), seed=3, surface=PLASTIC ):
    """ A heap of gear under a tarp: a lumpy dome, its edges tucked down to the ground, folds and a strap. """
    rng = np.random.default_rng( seed )
    a = unit( ( along[0], along[1], 0 ) )
    s = np.cross( UP, a )
    c = v( centre[0], centre[1], 0 )
    nu, nv = 14, 10
    lumps = [ ( rng.uniform( -0.35, 0.35 ), rng.uniform( -0.3, 0.3 ), rng.uniform( 0.6, 1.0 ), rng.uniform( 0.2, 0.4 ) ) for _ in range( 5 ) ]

    def hgt( u, w_ ):
        z = 0.0
        for lu, lw, lh, lr in lumps:
            d2 = ( ( u - lu ) / lr ) ** 2 + ( ( w_ - lw ) / ( lr * 1.2 ) ) ** 2
            z = max( z, lh * max( 0.0, 1 - d2 ) ** 0.6 )
        edge = min( 0.5 - abs( u ), 0.5 - abs( w_ ) ) * 2
        return H * z * min( 1.0, edge * 3.5 ) + rng.normal( 0, 0.8 )

    grid = [ [ c + a * ( L * ( i / nu - 0.5 ) ) + s * ( W * ( j / nv - 0.5 ) ) + UP * hgt( i / nu - 0.5, j / nv - 0.5 ) for j in range( nv + 1 ) ] for i in range( nu + 1 ) ]
    for i in range( nu ):
        for j in range( nv ):
            card( m, "oa_tarp", [ grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1] ], UP )
    m.oriented_box( c + UP * ( H * 0.4 ), ( a, s, UP ), ( L * 0.8, W * 0.8, H * 0.8 ), { "default": None }, surface )


# ---------------------------------------------------------------------------------------------------------------------
# Pipes

def banded_pipe( m, pts, r, paint="oa_pipe", band="oa_yellow", every=140.0, sides=16, flanges=() ):
    """ A pipe along pts with yellow bands at intervals along its straight runs (a fuel line's colour bands). """
    P.pipe( m, pts, r, paint, sides, caps=True, flanges=flanges )
    raw = [ v( *p ) for p in pts ]
    for p0, p1 in zip( raw, raw[1:] ):
        L = float( np.linalg.norm( p1 - p0 ) )
        if L < r * 6:
            continue
        d = ( p1 - p0 ) / L
        count = max( 1, int( L // every ) )
        for k in range( count ):
            f = ( k + 0.5 ) / count
            q = p0 + d * ( L * f )
            rod( m, q - d * r * 0.25, q + d * r * 0.25, r * 1.04, band, sides, caps=False )


def pipe_saddle( m, at, r, height, along ):
    """ A steel stand holding a pipe up off the ground: two legs, a cross beam and a saddle. """
    c = v( *at )
    a = unit( ( along[0], along[1], 0 ) )
    s = np.cross( UP, a )
    z = c[2]
    for sg in ( -1, 1 ):
        q = c + s * ( r + 4 ) * sg
        beam( m, v( q[0], q[1], z - height ), v( q[0], q[1], z - r ), 4, "oa_steel" )
    beam( m, c + s * ( r + 6 ) - UP * r, c - s * ( r + 6 ) - UP * r, 4, "oa_steel" )


# ---------------------------------------------------------------------------------------------------------------------
# Flags and banners

def flag( m, base, pole_h, facing=( 0, -1 ), size=( 150.0, 90.0 ) ):
    """ A flagpole with Orion's flag flying off it, rippled in three folds, drawn both sides. """
    c = v( *base )
    P.cylinder( m, ( c[0], c[1] ), 2.2, c[2], c[2] + pole_h, "oa_flag_pole", 8 )
    P.lathe( m, ( c[0], c[1] ), [ ( 3.5, c[2] + pole_h ), ( 3.5, c[2] + pole_h + 3 ), ( 0.0, c[2] + pole_h + 5 ) ], "oa_flag_pole", 8 )
    f = unit( ( facing[0], facing[1], 0 ) )
    right = np.cross( UP, f )
    W, H = size
    top = c + UP * ( pole_h - 4 )
    cols = 6
    x0, y0, w, h = OT.PLATES["flag"]
    pts = []
    for k in range( cols + 1 ):
        t = k / cols
        wave = math.sin( t * math.pi * 2.6 ) * 7 * t
        pts.append( ( top + right * ( W * t ) + f * wave, t ) )
    for k in range( cols ):
        ( p0, t0 ), ( p1, t1 ) = pts[k], pts[k + 1]
        quad = [ p0 - UP * H, p1 - UP * H - UP * ( t1 * 3 ), p1 - UP * ( t1 * 3 ), p0 ]
        uv = [ OT.atlas_uv( OT.PLATES, OT.PLATE_ATLAS, "flag", t0, 0 ), OT.atlas_uv( OT.PLATES, OT.PLATE_ATLAS, "flag", t1, 0 ),
               OT.atlas_uv( OT.PLATES, OT.PLATE_ATLAS, "flag", t1, 1 ), OT.atlas_uv( OT.PLATES, OT.PLATE_ATLAS, "flag", t0, 1 ) ]
        m.polygon( "oa_plates", quad, normal=f, uv=uv )
        m.polygon( "oa_plates", quad[::-1], normal=-f, uv=uv[::-1] )


def banner( m, top_centre, facing, w=60.0, h=110.0 ):
    """ A dark hanging banner with the mark, on a short bar. """
    f = unit( ( facing[0], facing[1], 0 ) )
    right = np.cross( UP, f )
    c = v( *top_centre )
    beam( m, c - right * ( w / 2 + 3 ), c + right * ( w / 2 + 3 ), 2.0, "oa_dark" )
    plate( m, "banner", c - UP * ( h / 2 ), right, h, off=0.0, both=True )


# ---------------------------------------------------------------------------------------------------------------------
# Rooms

def desk( m, c, along, w=72.0, d=30.0, h=30.0, monitors=2, screen_names=( "telemetry", "cctv" ), facing_back=False ):
    """ A console desk: a top on two pedestals, monitors on stands, a keyboard. along is its length, the user sits on its
    -side side (cross( UP, along ) points away from them). """
    a = unit( ( along[0], along[1], 0 ) )
    s = np.cross( UP, a )
    cc = v( c[0], c[1], 0 )
    obox( m, cc + UP * ( h - 1 ), a, ( w, d, 2 ), "oa_desk", PLASTIC )
    for sg in ( -1, 1 ):
        obox( m, cc + a * ( sg * ( w / 2 - 9 ) ) + UP * ( ( h - 2 ) / 2 ), a, ( 16, d - 4, h - 2 ), "oa_dark" )
    for k in range( monitors ):
        q = cc + a * ( ( k - ( monitors - 1 ) / 2 ) * ( w / monitors ) ) + s * ( d * 0.25 ) + UP * h
        obox( m, q + UP * 4, a, ( 3, 3, 8 ), "oa_dark" )
        obox( m, q + UP * 15, a, ( w / monitors - 6, 1.6, 14 ), "oa_black" )
        screen( m, screen_names[k % len( screen_names )], q + UP * 15 - s * 0.9, a, 12.5, off=0.0 )
    obox( m, cc - s * ( d * 0.2 ) + UP * ( h + 0.6 ), a, ( 18, 6, 1.2 ), "oa_black" )


def chair( m, c, facing ):
    f = unit( ( facing[0], facing[1], 0 ) )
    s = np.cross( UP, f )
    cc = v( c[0], c[1], 0 )
    P.cylinder( m, ( c[0], c[1] ), 1.5, 2, 18, "oa_dark", 6 )
    obox( m, cc + UP * 19, f, ( 18, 18, 3 ), "oa_chair" )
    obox( m, cc - f * 8 + UP * 30, f, ( 2.5, 17, 20 ), "oa_chair" )
    for k in range( 5 ):
        ang = 2 * math.pi * k / 5
        beam( m, cc + UP * 2, cc + v( math.cos( ang ) * 11, math.sin( ang ) * 11, 1.5 ), 1.6, "oa_dark" )
