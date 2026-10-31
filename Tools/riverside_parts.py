"""
Riverside's pieces: what Tools/riverside_map.py builds the trailer park from, on map_kit's Model (plan coordinates: e
east, n north, z up, inches).

- Most pieces are built in their own frame (x along, y across, z up from the ground) and dropped into the map turned
  and moved with place( model, origin, yaw ).
- Trailers are 1960s-80s single-wides: 8-12 ft wide, 30-56 ft long, on blocks with skirting, aluminium siding (its UVs
  anchored at the wall's foot, so the texture's mud splash and drip edge land where they belong), little windows lit,
  dark or boarded, a door with steps, a hitch tongue, vents and an antenna on the roof.
- Lettering and signs are quads on rs_lit / rs_signs / rs_paint_*, sized by their atlas region's shape.
- Lights add to LIGHTS ( name, position, "r,g,b,1", radius, shadows ), fires to FIRES ( position, kind ), which the
  scene builds. Railings and fences add player clips to CLIPS like Riverdale's.
"""
import math

import numpy as np

import map_kit as K
import riverdale_parts as RP
import riverside_materials as RM
from riverdale_parts import v, unit, card, box, obox, rod, cylinder, lathe, UP

METAL, STONE, SHEET, WOOD, PLASTIC, DIRT, FABRIC = "metal", "default", "metal.sheet", "wood", "plastic", "dirt", "fabric"

CLIPS = RP.CLIPS        # ( name, centre, yaw, ( length, thickness, height ) )
LIGHTS = []             # ( name, position, "r,g,b,1", radius, shadows )
FIRES = []              # ( name, position, kind ): MapFire objects
SPOTLIGHTS = []         # ( name, position, target, "r,g,b,1", radius, angle )
BURN_DRUMS = []         # ( name, position, variant, yaw ): burn_drum_v2 models the scene places
COOLERS = []            # ( position, yaw ): cooler_v2 models the scene places
TEDDIES = []            # ( position, yaw ): teddy_v2 models the scene places

WARM = "1.00,0.72,0.42,1"
PORCH = "1.00,0.78,0.50,1"
SODIUM = "1.00,0.62,0.30,1"
COOL = "0.75,0.85,1.00,1"
TV = "0.45,0.62,1.00,1"
RED = "1.00,0.16,0.10,1"


def reset():
    RP.reset()
    LIGHTS.clear()
    FIRES.clear()
    SPOTLIGHTS.clear()
    BURN_DRUMS.clear()
    COOLERS.clear()
    TEDDIES.clear()


def light( name, pos, colour, radius, shadows=False, scale=1.0 ):
    r, g, b, a = ( float( x ) for x in colour.split( "," ) )
    LIGHTS.append( ( name, tuple( float( x ) for x in pos ), f"{r * scale:.3f},{g * scale:.3f},{b * scale:.3f},1", radius, shadows ) )


# ---------------------------------------------------------------------------------------------------------------------
# Placing

def place( src, origin, yaw ):
    """ src turned yaw degrees (anticlockwise from above, from +x towards +y) and moved to origin. """
    c, s = math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) )
    R = np.array( ( ( c, -s, 0.0 ), ( s, c, 0.0 ), ( 0.0, 0.0, 1.0 ) ) )
    o = np.asarray( origin, float )
    out = K.Model()
    for paint, items in src.polygons.items():
        for i, ( pts, nrm ) in enumerate( items ):
            j = len( out.polygons[paint] )
            uv = src.polygon_uvs.get( ( paint, i ) )
            if uv is not None:
                out.polygon_uvs[( paint, j )] = uv
            normals = src.polygon_normals.get( ( paint, i ) )
            if normals is not None:
                out.polygon_normals[( paint, j )] = [ R @ np.asarray( n, float ) for n in normals ]
            out.polygons[paint].append( ( [ R @ np.asarray( p, float ) + o for p in pts ], R @ np.asarray( nrm, float ) ) )
    for centre, axes, size, surface in src.boxes:
        out.boxes.append( ( R @ np.asarray( centre, float ) + o, tuple( tuple( R @ np.asarray( a, float ) ) for a in axes ), size, surface ) )
    for pts, surface in src.hulls:
        out.hulls.append( ( [ tuple( R @ np.asarray( p, float ) + o ) for p in pts ], surface ) )
    out.material_overrides.update( src.material_overrides )
    out.tile_overrides.update( src.tile_overrides )
    return out


def local_to_world( p, origin, yaw ):
    c, s = math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) )
    x, y, z = p
    return ( origin[0] + c * x - s * y, origin[1] + s * x + c * y, ( origin[2] if len( origin ) > 2 else 0.0 ) + z )


def yaw_of( d ):
    return math.degrees( math.atan2( d[1], d[0] ) )


# ---------------------------------------------------------------------------------------------------------------------
# Atlas quads

def atlas_quad( m, paint, table, size, name, centre, right, up, h, off=0.3, w=None, flip=False ):
    """ A region of an atlas on a quad h tall (w from its shape unless given), facing cross( right, up ). """
    a = RM.aspect( table, name )
    w = w or h * a
    uv = [ RM.atlas_uv( table, size, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    if flip:
        uv = [ uv[1], uv[0], uv[3], uv[2] ]
    RP.quad( m, paint, centre, right, up, w, h, uv, off )
    return w


def lit( m, name, centre, right, h, up=UP, off=0.3, w=None ):
    return atlas_quad( m, "rs_lit", RM.LIT, RM.LIT_ATLAS, name, centre, right, up, h, off, w )


def sign( m, name, centre, right, h, up=UP, off=0.3, w=None ):
    return atlas_quad( m, "rs_signs", RM.SIGNS, RM.SIGN_ATLAS, name, centre, right, up, h, off, w )


def paint( m, name, centre, right, h, tone="white", up=UP, off=0.25, w=None ):
    return atlas_quad( m, f"rs_paint_{tone}", RM.PAINT, RM.PAINT_ATLAS, name, centre, right, up, h, off, w )


def blood( m, name, centre, right, h, up=UP, off=0.2, w=None ):
    return atlas_quad( m, "rs_blood", RM.PAINT, RM.PAINT_ATLAS, name, centre, right, up, h, off, w )


def anchored_wall( m, paint_name, a, b, z0, z1, towards, base_z=None, tile=96.0, u0=0.0 ):
    """ A wall quad from plan a to b, z0..z1, with UVs anchored: v 0 at base_z (default z0), u along from u0. """
    a, b = v( a[0], a[1], 0 ), v( b[0], b[1], 0 )
    L = float( np.linalg.norm( b - a ) )
    bz = z0 if base_z is None else base_z
    pts = [ a + UP * z0, b + UP * z0, b + UP * z1, a + UP * z1 ]
    uv = [ ( u0, ( z0 - bz ) / tile ), ( u0 + L / tile, ( z0 - bz ) / tile ), ( u0 + L / tile, ( z1 - bz ) / tile ), ( u0, ( z1 - bz ) / tile ) ]
    card( m, paint_name, pts, towards, uv=uv )


# ---------------------------------------------------------------------------------------------------------------------
# Trailers

FLOOR = 30.0                # floor over the ground: blocks and skirting
WALL = 88.0                 # floor to the eaves
WINDOW_STYLES = ( "lit", "lit_b", "tv", "dark", "dark", "boarded", "curtain_dark" )


def window( m, centre, right, w, h, style, seed=0 ):
    """ An aluminium-framed window on a wall facing cross( right, UP ): lit, dark, a TV's flicker, or boarded up. """
    right = unit( right )
    out = np.cross( right, UP )
    c = v( *centre )
    # The frame.
    RP.quad( m, "rs_alu", c, right, UP, w + 3.0, h + 3.0, off=0.35 )
    if style in ( "lit", "lit_b", "tv" ):
        name = { "lit": "trailer_window", "lit_b": "trailer_window_b", "tv": "trailer_window_tv" }[style]
        lit( m, name, c, right, h, off=0.55, w=w )
    else:
        RP.quad( m, "rs_window_dark", c, right, UP, w, h, off=0.55 )
    if style == "boarded":
        rng = np.random.default_rng( seed )
        for k in range( 3 ):
            dz = ( k - 1 ) * h * 0.33 + rng.normal( 0, 1.5 )
            ang = rng.normal( 0, 0.12 )
            r2 = right * math.cos( ang ) + UP * math.sin( ang )
            u2 = unit( np.cross( out, r2 ) )
            RP.quad( m, "rs_plywood", c + UP * dz + out * 0.4, r2, u2, w + 10, h * 0.3, off=0.6 + 0.1 * k )
    # The sill.
    obox( m, c - UP * ( h / 2 + 2.5 ) + out * 1.2, right, ( w + 5, 2.4, 1.2 ), "rs_alu" )


def door( m, centre_foot, right, w=32.0, h=76.0, paint_name="rs_alu", lit_window=False, open_=False ):
    right = unit( right )
    out = np.cross( right, UP )
    c = v( *centre_foot )
    RP.quad( m, "rs_dark", c + UP * ( h / 2 ), right, UP, w + 3, h + 2, off=0.3 )
    if not open_:
        RP.quad( m, paint_name, c + UP * ( h / 2 ), right, UP, w, h, off=0.5 )
        if lit_window:
            lit( m, "trailer_window", c + UP * ( h * 0.72 ), right, h * 0.22, off=0.7, w=w * 0.5 )
        else:
            RP.quad( m, "rs_window_dark", c + UP * ( h * 0.72 ), right, UP, w * 0.5, h * 0.22, off=0.7 )
        obox( m, c + UP * ( h * 0.47 ) + right * ( w * 0.36 ) + out * 1.4, right, ( 1.0, 1.5, 3.5 ), "rs_steel" )


def steps( m, foot, along, width, z_top, paint_name="rs_concrete", surface=STONE, rise=7.5 ):
    """ Steps from the ground up to z_top, their foot's front edge at foot, climbing along. """
    along = unit( ( along[0], along[1], 0 ) )
    side = np.cross( UP, along )
    n = max( 1, int( round( z_top / rise ) ) )
    rise = z_top / n
    going = 10.0
    f = v( foot[0], foot[1], 0 )
    for i in range( n ):
        p0 = f + along * ( going * i )
        z = rise * ( i + 1 )
        depth = going * ( n - i )
        c = p0 + along * ( depth / 2 ) + UP * ( z / 2 )
        obox( m, c, along, ( depth, width, z ), paint_name )
    # Collision: a wedge.
    end = f + along * ( going * n )
    s = side * ( width / 2 )
    m.hull( [ f - s, f + s, end - s, end + s, end - s + UP * z_top, end + s + UP * z_top, f - s + UP * 0.5, f + s + UP * 0.5 ], surface )


def trailer( length=560.0, width=120.0, tint="rs_siding_white", seed=0, door_x=None, door_side=1, porch_light=True,
             lit_share=0.45, boarded_share=0.2, hitch=True, antenna=None, ac=True, end_window=True, styles=None,
             skirt=True, door_lit=None ):
    """ A single-wide in its own frame: x along its length (hitch at -x), y across, z up from the ground. Returns
    ( model, info ) where info has the door's outside point and the porch light's place. """
    rng = np.random.default_rng( seed )
    m = K.Model()
    L, W = length, width
    hx, hy = L / 2, W / 2
    F, T = FLOOR, FLOOR + WALL
    crown = 5.0
    # Skirting.
    if skirt:
        for a, b, towards in ( ( ( -hx + 2, -hy + 2 ), ( hx - 2, -hy + 2 ), ( 0, -1, 0 ) ), ( ( hx - 2, hy - 2 ), ( -hx + 2, hy - 2 ), ( 0, 1, 0 ) ),
                               ( ( hx - 2, -hy + 2 ), ( hx - 2, hy - 2 ), ( 1, 0, 0 ) ), ( ( -hx + 2, hy - 2 ), ( -hx + 2, -hy + 2 ), ( -1, 0, 0 ) ) ):
            anchored_wall( m, "rs_skirt", a, b, 0, F, v( *towards ), base_z=0 )
    # Walls: siding anchored at the floor line.
    corners = [ ( -hx, -hy ), ( hx, -hy ), ( hx, hy ), ( -hx, hy ) ]
    outs = [ v( 0, -1, 0 ), v( 1, 0, 0 ), v( 0, 1, 0 ), v( -1, 0, 0 ) ]
    for k in range( 4 ):
        anchored_wall( m, tint, corners[k], corners[( k + 1 ) % 4], F, T, outs[k], base_z=F - 4, u0=rng.uniform( 0, 4 ) )
    # Gable ends up to the crown.
    for sx in ( -1, 1 ):
        pts = [ v( sx * hx, -hy, T ), v( sx * hx, hy, T ), v( sx * hx, 0, T + crown ) ]
        card( m, tint, pts, v( sx, 0, 0 ), uv=[ ( 0, ( T - F + 4 ) / 96 ), ( W / 96, ( T - F + 4 ) / 96 ), ( W / 192, ( T + crown - F + 4 ) / 96 ) ] )
    # Roof: two shallow pitches, overhanging 2, with a drip edge.
    o = 2.5
    for sy in ( -1, 1 ):
        pts = [ v( -hx - o, sy * ( hy + o ), T - 0.5 ), v( hx + o, sy * ( hy + o ), T - 0.5 ), v( hx + o, 0, T + crown ), v( -hx - o, 0, T + crown ) ]
        card( m, "rs_roof", pts, v( 0, sy * 0.15, 1 ) )
        card( m, "rs_roof", pts, v( 0, 0, -1 ) )
        obox( m, v( 0, sy * ( hy + o ), T - 1.5 ), ( 1, 0, 0 ), ( L + 2 * o, 1.2, 2.5 ), "rs_alu" )
    # Trim band at the eaves and the floor line.
    for sy in ( -1, 1 ):
        obox( m, v( 0, sy * ( hy + 0.4 ), T - 3 ), ( 1, 0, 0 ), ( L, 0.8, 3 ), "rs_alu" )
        obox( m, v( 0, sy * ( hy + 0.4 ), F + 1 ), ( 1, 0, 0 ), ( L, 0.8, 2 ), "rs_alu" )
    # Windows along both sides, the door on door_side.
    door_x = door_x if door_x is not None else ( -hx + L * rng.uniform( 0.28, 0.42 ) )
    info = {}
    for sy in ( -1, 1 ):
        right = v( -sy, 0, 0 )
        n_win = max( 2, int( L / 110 ) )
        xs = np.linspace( -hx + 50, hx - 50, n_win )
        for i, x in enumerate( xs ):
            if sy == door_side and abs( x - door_x ) < 45:
                continue
            roll = rng.random()
            style = styles[( i + ( 0 if sy > 0 else 7 ) ) % len( styles )] if styles else (
                ( "lit" if rng.random() < 0.6 else ( "lit_b" if rng.random() < 0.6 else "tv" ) ) if roll < lit_share else
                "boarded" if roll < lit_share + boarded_share else "dark" )
            wz = F + 46
            ww, wh = ( 30.0, 30.0 ) if rng.random() < 0.7 else ( 44.0, 30.0 )
            window( m, v( x, sy * ( hy ), wz ), right, ww, wh, style, seed=seed * 31 + i )
            if style in ( "lit", "lit_b", "tv" ) and rng.random() < 0.55:
                info.setdefault( "lit_windows", [] ).append( ( v( x, sy * ( hy + 20 ), wz ), style ) )
        if sy == door_side:
            right_d = v( -sy, 0, 0 )
            dl = door_lit if door_lit is not None else rng.random() < 0.5
            door( m, v( door_x, sy * hy, F ), right_d, lit_window=dl, paint_name=( "rs_alu" if rng.random() < 0.5 else "rs_siding_cream" ) )
            steps( m, v( door_x, sy * ( hy + 10 * max( 1, int( round( F / 7.5 ) ) ) ), 0 ), v( 0, -sy, 0 ), 36, F - 1, "rs_concrete" )
            info["door"] = v( door_x, sy * ( hy + 60 ), 0 )
            if porch_light:
                pl = v( door_x + 22, sy * ( hy + 2 ), F + 82 )
                obox( m, pl, ( 1, 0, 0 ), ( 5, 4, 6 ), "rs_porch_light" )
                info["porch_light"] = pl + v( 0, sy * 14, -6 )
    # An end window at +x.
    if end_window:
        style = "lit" if rng.random() < lit_share else "dark"
        window( m, v( hx, 0, F + 48 ), v( 0, 1, 0 ), 50, 26, style, seed=seed * 7 )
    # Hitch tongue at -x.
    if hitch:
        for sy in ( -1, 1 ):
            m.beam( v( -hx, sy * 30, 18 ), v( -hx - 46, 0, 14 ), ( 3, 4 ), "rs_rust" )
        cylinder( m, ( -hx - 44, 0 ), 1.6, 0, 18, "rs_rust", 6 )
        obox( m, v( -hx - 44, 0, 1 ), ( 1, 0, 0 ), ( 8, 8, 2 ), "rs_concrete" )
    # Roof furniture: vents, an AC unit, maybe an antenna.
    for x in rng.uniform( -hx + 40, hx - 40, int( rng.integers( 1, 4 ) ) ):
        obox( m, v( x, rng.uniform( -hy * 0.4, hy * 0.4 ), T + crown + 1 ), ( 1, 0, 0 ), ( 14, 14, 4 ), "rs_alu" )
    if ac and rng.random() < 0.6:
        x = rng.uniform( -hx * 0.5, hx * 0.5 )
        obox( m, v( x, 0, T + crown + 7 ), ( 1, 0, 0 ), ( 34, 30, 13 ), "rs_alu" )
        obox( m, v( x, 0, T + crown + 13.7 ), ( 1, 0, 0 ), ( 26, 22, 0.6 ), "rs_dark" )
    if antenna if antenna is not None else rng.random() < 0.35:
        x = rng.uniform( -hx * 0.6, hx * 0.6 )
        base = v( x, -hy * 0.3, T + crown )
        rod( m, base, base + UP * 70, 0.8, "rs_steel", 6 )
        for k in range( 5 ):
            zz = 50 + k * 4
            L2 = 30 - k * 4
            rod( m, base + UP * zz - v( 0, L2 / 2, 0 ), base + UP * zz + v( 0, L2 / 2, 0 ), 0.4, "rs_steel", 4 )
    # Collision: the body on its blocks, one box.
    m.collision_box( v( -hx, -hy, 0 ), v( hx, hy, T + crown ), SHEET )
    return m, info


def porch_deck( m, x0, x1, y0, depth, z, sy=1, rail=True, roof=True, lights=None, string_lights=True, seed=0 ):
    """ A wooden deck along a trailer's side (local frame), from y0 out depth (sign sy), its floor at z, with a railing,
    an awning on posts and string lights along its edge. """
    rng = np.random.default_rng( seed )
    ya, yb = sorted( ( y0, y0 + sy * depth ) )
    box( m, x0, x1, ya, yb, z - 4, z, { "default": "rs_wood" }, WOOD )
    # Joists and posts under it.
    for x in np.linspace( x0 + 6, x1 - 6, max( 2, int( ( x1 - x0 ) / 70 ) ) ):
        box( m, x - 2, x + 2, ya + 2, ya + 6, 0, z - 4, "rs_wood" )
        box( m, x - 2, x + 2, yb - 6, yb - 2, 0, z - 4, "rs_wood" )
    edge_y = y0 + sy * depth
    posts = list( np.linspace( x0 + 3, x1 - 3, max( 2, int( ( x1 - x0 ) / 96 ) + 1 ) ) )
    if roof:
        rz = z + 86
        for x in posts:
            box( m, x - 2, x + 2, edge_y - 2, edge_y + 2, z, rz, "rs_wood", WOOD )
        # Corrugated awning sloping down out from the wall.
        pts = [ v( x0 - 4, y0, rz + 10 ), v( x1 + 4, y0, rz + 10 ), v( x1 + 4, edge_y + sy * 8, rz ), v( x0 - 4, edge_y + sy * 8, rz ) ]
        card( m, "rs_roof", pts, v( 0, sy * 0.1, 1 ) )
        card( m, "rs_roof", pts, v( 0, 0, -1 ) )
        box( m, x0 - 4, x1 + 4, min( edge_y, edge_y + sy * 8 ), max( edge_y, edge_y + sy * 8 ), rz - 6, rz - 1, "rs_wood" )
        if string_lights:
            string( m, [ v( x0, edge_y + sy * 6, rz - 7 ), v( x1, edge_y + sy * 6, rz - 7 ) ], sag=7, spacing=11, seed=seed )
    # Steps up onto the deck at its +x end.
    n = max( 1, int( round( z / 7.5 ) ) )
    steps( m, ( x1 + 10 * n, y0 + sy * depth * 0.5 ), ( -1, 0 ), 34, z, "rs_wood", WOOD )
    if rail:
        for x in posts:
            box( m, x - 1.5, x + 1.5, edge_y - 1.5, edge_y + 1.5, z, z + 36, "rs_wood" )
        box( m, x0, x1, edge_y - 1.5, edge_y + 1.5, z + 33, z + 36, "rs_wood" )
        for x in np.arange( x0 + 6, x1 - 3, 7 ):
            box( m, x - 0.8, x + 0.8, edge_y - 0.6, edge_y + 0.6, z, z + 33, "rs_wood" )
        m.collision_box( v( x0, edge_y - 1.5, z ), v( x1, edge_y + 1.5, z + 36 ), WOOD )


def string( m, pts, sag=8.0, spacing=12.0, seed=0, dead=0.08, lights_every=None ):
    """ String lights: a sagging wire between points with warm bulbs every spacing, a few dead. """
    rng = np.random.default_rng( seed )
    for a, b in zip( pts, pts[1:] ):
        a, b = v( *a ), v( *b )
        L = float( np.linalg.norm( b - a ) )
        n = max( 2, int( L / spacing ) )
        prev = None
        for i in range( n + 1 ):
            t = i / n
            p = a + ( b - a ) * t - UP * ( 4 * sag * t * ( 1 - t ) )
            if prev is not None:
                rod( m, prev, p, 0.25, "rs_wire", 4 )
            if 0 < i < n:
                z = p[2]
                lathe( m, p, [ ( 0.5, z - 0.3 ), ( 1.2, z - 1.2 ), ( 1.1, z - 2.8 ), ( 0.0, z - 3.4 ) ],
                       "rs_bulb_dead" if rng.random() < dead else "rs_bulb", 6 )
            prev = p


def wire( m, a, b, sag=None, r=0.35, paint_name="rs_wire", segs=10 ):
    a, b = v( *a ), v( *b )
    L = float( np.linalg.norm( ( b - a )[:2] ) )
    sag = sag if sag is not None else L * 0.035
    prev = a
    for i in range( 1, segs + 1 ):
        t = i / segs
        p = a + ( b - a ) * t - UP * ( 4 * sag * t * ( 1 - t ) )
        rod( m, prev, p, r, paint_name, 4 )
        prev = p


def pole( m, base, height=420.0, facing=( 1, 0 ), arms=2, transformer=False, lamp=None, lean=0.0, seed=0 ):
    """ A creosoted utility pole: tapered, crossarms near the top with insulators, maybe a transformer can and a cobra
    head street lamp (lamp: 'sodium' / 'cool' and its arm's direction). Returns the insulator tops (for the wires) and
    the lamp head. """
    rng = np.random.default_rng( seed )
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    f = unit( ( facing[0], facing[1], 0 ) )
    side = np.cross( UP, f )
    tilt = v( *( f * math.sin( math.radians( lean ) ) ) ) + UP * math.cos( math.radians( lean ) )
    top = b + tilt * height
    # The shaft in four tapering stages so it shades round.
    for k in range( 4 ):
        z0, z1 = height * k / 4, height * ( k + 1 ) / 4
        r0, r1 = 6.0 - 1.6 * k / 4, 6.0 - 1.6 * ( k + 1 ) / 4
        lathe_seg( m, b + tilt * z0, b + tilt * z1, r0, r1, "rs_pole" )
    m.hull( [ b + side * 6 + f * 6, b - side * 6 + f * 6, b + side * 6 - f * 6, b - side * 6 - f * 6,
              top + side * 4 + f * 4, top - side * 4 + f * 4, top + side * 4 - f * 4, top - side * 4 - f * 4 ], WOOD )
    taps = []
    for k in range( arms ):
        z = height - 14 - k * 28
        c = b + tilt * z
        L = 96 if k == 0 else 72
        obox( m, c + f * 5, side, ( L, 4, 4.5 ), "rs_pole" )
        for s in ( -0.45, -0.15, 0.15, 0.45 ) if k == 0 else ( -0.4, 0.4 ):
            p = c + f * 5 + side * ( L * s ) + UP * 2.3
            cylinder( m, p, 1.4, p[2], p[2] + 5, "rs_glass", 6, top="rs_glass" )
            taps.append( p + UP * 5 )
        # Braces.
        m.beam( c + f * 5 + side * ( L * 0.3 ), b + tilt * ( z - 22 ) + f * 5, ( 1.4, 1.4 ), "rs_steel" )
        m.beam( c + f * 5 - side * ( L * 0.3 ), b + tilt * ( z - 22 ) + f * 5, ( 1.4, 1.4 ), "rs_steel" )
    if transformer:
        c = b + tilt * ( height - 80 ) - f * 12
        cylinder( m, c, 9, c[2] - 16, c[2] + 16, "rs_steel", 12, top="rs_steel", bottom="rs_steel" )
    head = None
    if lamp:
        kind, direction = lamp
        d = unit( ( direction[0], direction[1], 0 ) )
        a0 = b + tilt * ( height - 70 )
        a1 = a0 + d * 70 + UP * 8
        pipe_arm( m, a0, a1 )
        head = a1 + d * 8
        obox( m, head + UP * 1, d, ( 22, 10, 5 ), "rs_alu" )
        lens = "rs_lamp_sodium" if kind == "sodium" else "rs_lamp_cool"
        card( m, lens, [ head - d * 8 - np.cross( UP, d ) * 4 - UP * 1.6, head + d * 9 - np.cross( UP, d ) * 4 - UP * 1.6,
                         head + d * 9 + np.cross( UP, d ) * 4 - UP * 1.6, head - d * 8 + np.cross( UP, d ) * 4 - UP * 1.6 ], -UP )
    return taps, head


def lathe_seg( m, a, b, r0, r1, paint_name, sides=8 ):
    """ A tapered round segment from a (radius r0) to b (r1), shaded smooth. """
    a, b = v( *a ), v( *b )
    axis = unit( b - a )
    u, w = RP.perp( axis )
    dirs = [ u * math.cos( 2 * math.pi * k / sides ) + w * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
    for k in range( sides ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % sides]
        card( m, paint_name, [ a + d0 * r0, a + d1 * r0, b + d1 * r1, b + d0 * r1 ], d0 + d1, normals=[ d0, d1, d1, d0 ] )


def pipe_arm( m, a, b ):
    a, b = v( *a ), v( *b )
    mid = a + ( b - a ) * 0.5 + UP * 10
    RP.pipe( m, [ a, mid, b ], 1.2, "rs_alu", sides=6, caps=False )


# ---------------------------------------------------------------------------------------------------------------------
# Fences

def chainlink( m, pts, height=72.0, post_every=120.0, z=0.0, gaps=(), collide=True, top_rail=True, barbed=False, name="fence",
               clip_to=None, leaning=() ):
    """ Galvanised chain-link along plan pts: posts, a top rail, mesh both sides (alpha tested). gaps: ( segment index,
    from, to ) runs along a segment left open (a breach or a gate). """
    pts = [ v( p[0], p[1], 0 ) for p in pts ]
    for k in range( len( pts ) - 1 ):
        a, b = pts[k], pts[k + 1]
        d = b - a
        L = float( np.linalg.norm( d ) )
        if L < 1:
            continue
        dn = d / L
        side = np.cross( UP, dn )
        runs = [ ( 0.0, L ) ]
        for gk, g0, g1 in gaps:
            if gk != k:
                continue
            new = []
            for r0, r1 in runs:
                if g1 <= r0 or g0 >= r1:
                    new.append( ( r0, r1 ) )
                    continue
                if g0 > r0:
                    new.append( ( r0, g0 ) )
                if g1 < r1:
                    new.append( ( g1, r1 ) )
            runs = new
        for r0, r1 in runs:
            p0, p1 = a + dn * r0, a + dn * r1
            span = r1 - r0
            card( m, "rs_chainlink", [ p0 + UP * ( z + 2 ), p1 + UP * ( z + 2 ), p1 + UP * ( z + height ), p0 + UP * ( z + height ) ], side, both=True )
            count = max( 1, int( math.ceil( span / post_every ) ) )
            for i in range( count + 1 ):
                p = p0 + dn * ( span * i / count )
                cylinder( m, p, 1.2, z, z + height + 2, "rs_steel", 6, top="rs_steel" )
            if top_rail:
                rod( m, p0 + UP * ( z + height ), p1 + UP * ( z + height ), 0.85, "rs_steel", 6 )
            if barbed:
                for h in ( 4, 8, 12 ):
                    rod( m, p0 + UP * ( z + height + h ) - side * h * 0.5, p1 + UP * ( z + height + h ) - side * h * 0.5, 0.2, "rs_wire", 3 )
            if collide:
                c = ( p0 + p1 ) / 2 + UP * ( z + height / 2 )
                m.oriented_box( c, ( dn, side, UP ), ( span, 2.0, height ), None, METAL )
            if clip_to is not None:
                RP.clip( name, p0, p1, z, clip_to )


def plank_fence( m, pts, height=60.0, z=0.0, collide=True, seed=0, name="plank fence" ):
    """ A weathered privacy fence: posts, two rails and vertical boards, a few missing. """
    rng = np.random.default_rng( seed )
    pts = [ v( p[0], p[1], 0 ) for p in pts ]
    for a, b in zip( pts, pts[1:] ):
        d = b - a
        L = float( np.linalg.norm( d ) )
        dn = d / L
        side = np.cross( UP, dn )
        for t in np.arange( 0, L, 5.75 ):
            if rng.random() < 0.06:
                continue
            p = a + dn * ( t + 2.8 )
            h = height * rng.uniform( 0.94, 1.0 )
            obox( m, p + UP * ( z + h / 2 ), dn, ( 5.4, 0.8, h ), "rs_wood" )
        for zz in ( 14, height - 12 ):
            obox( m, ( a + b ) / 2 + side * 1.4 + UP * ( z + zz ), dn, ( L, 1.6, 3.5 ), "rs_wood" )
        if collide:
            m.oriented_box( ( a + b ) / 2 + UP * ( z + height / 2 ), ( dn, side, UP ), ( L, 3.0, height ), None, WOOD )


# ---------------------------------------------------------------------------------------------------------------------
# Props

def drum( m, c, paint_name="rs_drum_blue", z0=0.0, burning=True, dented=0.0, name="drum" ):
    """ A 55 gallon burn drum (22.5 in across, 34.5 tall): its hull and fire here, its model (Sources/Zombies/burn-drum-v2/) placed by the
    scene. Turned by the golden angle per drum, so no two show the same dents. """
    r, h = 11.25, 34.5
    cc = v( c[0], c[1], 0 )
    dirs = [ v( math.cos( 2 * math.pi * k / 14 ), math.sin( 2 * math.pi * k / 14 ), 0 ) for k in range( 14 ) ]
    m.hull( [ cc + d * r + UP * z for d in dirs for z in ( z0, z0 + h ) ], METAL )
    variant = { "rs_drum_blue": "blue", "rs_drum_red": "red", "rs_rust": "rust" }[paint_name] if burning else "cold"
    BURN_DRUMS.append( ( name, ( c[0], c[1], z0 ), variant, len( BURN_DRUMS ) * 137.5 ) )
    if burning:
        FIRES.append( ( name, ( c[0], c[1], z0 + h * 0.78 ), "drum" ) )


def crate( m, c, size=( 30, 22, 20 ), along=( 1, 0 ), z0=0.0, paint_name="rs_crate", label=True, surface=WOOD ):
    along = unit( ( along[0], along[1], 0 ) )
    side = np.cross( UP, along )
    L, W, H = size
    centre = v( c[0], c[1], z0 + H / 2 )
    obox( m, centre, along, ( L, W, H ), paint_name, surface )
    # Slats and corner boards.
    for s in ( -1, 1 ):
        for k in ( -0.48, 0.48 ):
            obox( m, centre + side * ( W / 2 + 0.3 ) * s + along * ( L * k ), along, ( 2.5, 0.8, H ), "rs_wood" )
        obox( m, centre + side * ( W / 2 + 0.3 ) * s, along, ( L, 0.8, 2.2 ), "rs_wood" )
    if label:
        sign( m, "crate_label", centre + side * ( W / 2 + 0.75 ), right_for( side ), H * 0.45, off=0.0 )


def sandbag_wall( m, a, b, rows=4, z0=0.0, seed=0 ):
    """ Sandbags stacked in a running bond from a to b: each 26 x 14 x 5.5, lumpy. """
    rng = np.random.default_rng( seed )
    a, b = v( a[0], a[1], 0 ), v( b[0], b[1], 0 )
    d = b - a
    L = float( np.linalg.norm( d ) )
    dn = d / L
    side = np.cross( UP, dn )
    for r in range( rows ):
        n = int( L / 24 )
        for i in range( n ):
            t = ( i + ( 0.5 if r % 2 else 0.0 ) + 0.5 ) * L / n
            if t > L - 6:
                continue
            p = a + dn * t + side * rng.normal( 0, 0.8 ) + UP * ( z0 + r * 5.2 + 2.6 )
            yaw = rng.normal( 0, 0.06 )
            al = dn * math.cos( yaw ) + side * math.sin( yaw )
            bag( m, p, al, ( 25 + rng.normal( 0, 1 ), 13.5, 5.6 ) )
    c = ( a + b ) / 2 + UP * ( z0 + rows * 2.6 )
    m.oriented_box( c, ( dn, side, UP ), ( L, 14, rows * 5.2 ), None, FABRIC )


def bag( m, p, along, size ):
    """ A filled sack: a rounded box made from a squashed lathe-like loft. """
    along = unit( along )
    side = np.cross( UP, along )
    L, W, H = size
    rings = []
    for t in np.linspace( -1, 1, 5 ):
        k = math.sqrt( max( 0.0, 1 - ( abs( t ) ** 3 ) ) ) * 0.9 + 0.1
        ring = []
        for j in range( 8 ):
            a = 2 * math.pi * j / 8
            ring.append( p + along * ( t * L / 2 ) + side * ( math.cos( a ) * W / 2 * k ) + UP * ( math.sin( a ) * H / 2 * k ) )
        rings.append( ring )
    for r0, r1 in zip( rings, rings[1:] ):
        for j in range( 8 ):
            j1 = ( j + 1 ) % 8
            q = [ r0[j], r0[j1], r1[j1], r1[j] ]
            card( m, "rs_sandbag", q, sum( q ) / 4 - p )


def cooler( m, c, along=( 1, 0 ), z0=0.0 ):
    """ A big ice chest, open, with SOME THINGS SHOULD STAY FORGOTTEN in marker inside its lid: its collision here, its model
    (Sources/Zombies/cooler-v2/) placed by the scene, with its length along its own x and its open side its own +y. """
    along = unit( ( along[0], along[1], 0 ) )
    L, W, H = 32.0, 17.0, 16.0
    obox( m, v( c[0], c[1], z0 ) + UP * ( H / 2 ), along, ( L, W, H ), None, PLASTIC )
    COOLERS.append( ( ( c[0], c[1], z0 ), K.plan_yaw( along ) ) )


def teddy( c, facing=( 0, -1 ), z0=0.0 ):
    """ A child's teddy bear sat in the mud: its model (Sources/Zombies/teddy-v2/) placed by the scene, facing its own +x. It has no collision. """
    TEDDIES.append( ( ( c[0], c[1], z0 ), K.plan_yaw( facing ) ) )


def tire( m, c, axis=( 1, 0, 0 ), r=13.0, w=8.0, paint_name="rs_rubber" ):
    a = unit( axis )
    p = v( *c )
    rod( m, p - a * ( w / 2 ), p + a * ( w / 2 ), r, paint_name, 12, caps=False )
    u, wv = RP.perp( a )
    for sg in ( -1, 1 ):
        card( m, "rs_dark", [ p + a * ( w / 2 * sg ) + ( u * math.cos( 2 * math.pi * k / 12 ) + wv * math.sin( 2 * math.pi * k / 12 ) ) * r * 0.62
                              for k in range( 12 ) ], a * sg )


def fridge( m, c, facing=( 0, -1 ), z0=0.0, lit_front=True ):
    """ A glass-door drinks fridge, lit from inside. """
    f = unit( ( facing[0], facing[1], 0 ) )
    side = np.cross( UP, f )
    W, D, H = 30.0, 28.0, 72.0
    base = v( c[0], c[1], z0 )
    obox( m, base + UP * ( H / 2 ), side, ( W, D, H ), "rs_fridge", METAL )
    if lit_front:
        lit( m, "fridge", base + f * ( D / 2 ) + UP * ( H * 0.5 ), right_for( f ), H * 0.86, off=0.2, w=W * 0.86 )
        light( "fridge", base + f * ( D / 2 + 12 ) + UP * ( H * 0.6 ), COOL, 90, scale=0.9 )


def right_for( f ):
    """ The right for a quad that faces f (plan): cross( right, UP ) == f. """
    f = unit( ( f[0], f[1], 0 ) )
    return np.cross( UP, f )


def lawn_chair( m, c, facing=( 0, 1 ), z0=0.0, paint_name="rs_lawn_chair", tipped=False ):
    f = unit( ( facing[0], facing[1], 0 ) )
    side = np.cross( UP, f )
    base = v( c[0], c[1], z0 )
    for sx in ( -1, 1 ):
        rod( m, base + side * 10 * sx - f * 8, base + side * 10 * sx + f * 8 + UP * 16, 0.5, "rs_alu", 5 )
        rod( m, base + side * 10 * sx + f * 8, base + side * 10 * sx - f * 6 + UP * 14, 0.5, "rs_alu", 5 )
        rod( m, base + side * 10 * sx - f * 6 + UP * 14, base + side * 10 * sx - f * 12 + UP * 34, 0.5, "rs_alu", 5 )
    card( m, paint_name, [ base - side * 10 - f * 6 + UP * 14, base + side * 10 - f * 6 + UP * 14, base + side * 10 + f * 8 + UP * 15,
                           base - side * 10 + f * 8 + UP * 15 ], UP, both=True )
    card( m, paint_name, [ base - side * 10 - f * 6 + UP * 14, base + side * 10 - f * 6 + UP * 14, base + side * 10 - f * 12 + UP * 34,
                           base - side * 10 - f * 12 + UP * 34 ], f, both=True )


def propane( m, c, z0=0.0 ):
    """ A 100 lb propane cylinder: 15 in across, 48 tall, its collar and valve. """
    cylinder( m, c, 7.5, z0, z0 + 40, "rs_propane", 12, surface=METAL )
    lathe( m, v( c[0], c[1], 0 ), [ ( 7.5, z0 + 40 ), ( 6.2, z0 + 44 ), ( 3.0, z0 + 46 ) ], "rs_propane", 12, cap="rs_propane" )
    cylinder( m, c, 4.2, z0 + 44, z0 + 50, "rs_steel", 10 )


def puddle( m, c, size, seed=0, z=0.25, paint_name="rs_water" ):
    """ Standing water: a flat, ragged pool that mirrors the lights. """
    rng = np.random.default_rng( seed )
    n = 18
    rx, ry = size
    phase = rng.uniform( 0, 2 * math.pi, 3 )
    amp = rng.uniform( 0.08, 0.22, 3 )
    rot = rng.uniform( 0, math.pi )
    pts = []
    for k in range( n ):
        a = 2 * math.pi * k / n
        r = 1.0 + sum( amp[j] * math.sin( ( j + 2 ) * a + phase[j] ) for j in range( 3 ) )
        x, y = math.cos( a ) * rx * r, math.sin( a ) * ry * r
        pts.append( v( c[0] + x * math.cos( rot ) - y * math.sin( rot ), c[1] + x * math.sin( rot ) + y * math.cos( rot ), z ) )
    m.polygon( paint_name, pts[::-1] if np.cross( pts[1] - pts[0], pts[2] - pts[0] )[2] < 0 else pts )


def junk_pile( m, c, seed=0, z0=0.0 ):
    """ A heap by a trailer: tyres, a crate, boards, a bag. """
    rng = np.random.default_rng( seed )
    base = v( c[0], c[1], z0 )
    for k in range( int( rng.integers( 2, 4 ) ) ):
        p = base + v( rng.normal( 0, 12 ), rng.normal( 0, 12 ), 4.2 + k * 0.1 )
        tire( m, p, ( 0, 0, 1 ), r=12.5, w=8 )
    crate( m, base + v( rng.normal( 0, 10 ), rng.normal( 0, 10 ), 0 ), ( 26, 20, 18 ), ( math.cos( rng.uniform( 0, 3 ) ), math.sin( rng.uniform( 0, 3 ) ) ), z0 + 8, label=rng.random() < 0.5 )
    for k in range( 3 ):
        a = rng.uniform( 0, math.pi )
        d = v( math.cos( a ), math.sin( a ), 0 )
        p = base + v( rng.normal( 0, 14 ), rng.normal( 0, 14 ), 1.5 + k )
        obox( m, p, d, ( rng.uniform( 40, 70 ), 5.5, 1.2 ), "rs_wood" )
    m.collision_box( base - v( 22, 22, 0 ), base + v( 22, 22, 26 ), WOOD )


# ---------------------------------------------------------------------------------------------------------------------
# Vehicles

def pickup( seed=3, wrecked=True ):
    """ A 1980s full-size pickup in its own frame (x forward, nose at +x), rusted out, flat tyres, windows smashed.
    About 210 long, 78 wide. Unused: the user had it taken out of Riverside (2026-10-15). """
    m = K.Model()
    rng = np.random.default_rng( seed )
    paint_ = "rs_truck_blue" if seed % 2 else "rs_truck"
    sink = 2.5 if wrecked else 0.0
    zc = 18 - sink
    # The bed and cab sides, the hood, the cab.
    box( m, -105, -20, -38, 38, zc, zc + 26, { "default": paint_, "+z": None }, METAL )
    box( m, -103, -22, -36, 36, zc + 4, zc + 5, "rs_rust" )
    box( m, -20, 30, -39, 39, zc, zc + 30, paint_, METAL )
    m.polygon( "rs_glass", [ v( -18, -36, zc + 30 ), v( 28, -36, zc + 30 ), v( 22, -32, zc + 52 ), v( -14, -32, zc + 52 ) ] )
    box( m, -18, 22, -34, 34, zc + 30, zc + 54, { "default": paint_, "+x": None, "-y": None, "+y": None }, METAL )
    # Windscreen and side windows: dark glass, the windscreen crazed (a dark quad, a lighter star).
    card( m, "rs_window_dark", [ v( 22, -32, zc + 31 ), v( 22, 32, zc + 31 ), v( 14, 30, zc + 52 ), v( 14, -30, zc + 52 ) ], v( 1, 0, 0.6 ) )
    for sy in ( -1, 1 ):
        card( m, "rs_window_dark" if not wrecked or sy > 0 else "rs_dark",
              [ v( -16, sy * 34, zc + 31 ), v( 20, sy * 34, zc + 31 ), v( 14, sy * 32, zc + 51 ), v( -14, sy * 32, zc + 51 ) ], v( 0, sy, 0 ) )
    box( m, 30, 100, -38, 38, zc, zc + 24, { "default": paint_ }, METAL )
    box( m, 100, 104, -36, 36, zc + 4, zc + 20, "rs_alu" )
    # Grille and lamps.
    box( m, 104, 105, -30, 30, zc + 8, zc + 18, "rs_dark" )
    for sy in ( -1, 1 ):
        box( m, 104, 105.5, sy * 30 - 4, sy * 30 + 4, zc + 10, zc + 16, "rs_alu" )
    # Bumpers.
    box( m, 104, 110, -40, 40, zc - 2, zc + 4, "rs_steel" )
    box( m, -111, -105, -40, 40, zc - 2, zc + 4, "rs_steel" )
    # Wheels: flat, the front one off.
    for x in ( 70, -70 ):
        for sy in ( -1, 1 ):
            if wrecked and x > 0 and sy < 0:
                continue
            tire( m, v( x, sy * 34, 14 - ( 4 if wrecked else 0 ) ), ( 0, 1, 0 ), r=14 - ( 3 if wrecked else 0 ), w=10 )
    if wrecked:
        # The front left corner on blocks of wood, rust holes, a door hanging open.
        crate( m, v( 70, -30, 0 ), ( 18, 14, 10 ), ( 1, 0 ), 0, label=False )
        m.beam( v( 20, -39, zc + 2 ), v( 6, -66, zc + 2 ), ( 1.5, 1.5 ), "rs_rust" )
        card( m, paint_, [ v( 20, -39, zc ), v( 4, -70, zc ), v( 4, -70, zc + 30 ), v( 20, -39, zc + 30 ) ], v( -1, -0.5, 0 ), both=True )
        for k in range( 6 ):
            p = v( rng.uniform( -100, 95 ), rng.choice( [ -39.2, 39.2 ] ), zc + rng.uniform( 3, 22 ) )
            RP.quad( m, "rs_rust", p, v( 1, 0, 0 ), UP, rng.uniform( 6, 14 ), rng.uniform( 4, 9 ), off=0.0 ) if p[1] < 0 else \
                RP.quad( m, "rs_rust", p, v( -1, 0, 0 ), UP, rng.uniform( 6, 14 ), rng.uniform( 4, 9 ), off=0.0 )
    m.collision_box( v( -111, -40, 0 ), v( 110, 40, zc + 30 ), METAL )
    m.collision_box( v( -18, -34, zc + 30 ), v( 22, 34, zc + 54 ), METAL )
    return m


def rv( seed=5 ):
    """ A 1970s travel trailer in its own frame (x along, front at +x): white fibreglass, rounded front, a red stripe,
    windows boarded, a bloody handprint by the door, a ladder up the back. 320 long, 96 wide, 118 tall. """
    m = K.Model()
    rng = np.random.default_rng( seed )
    L, W = 320.0, 96.0
    hx, hy = L / 2, W / 2
    F, T = 26.0, 118.0
    # Body with rounded vertical corners at the front: a loft of sections along x.
    prof = []
    for k in range( 9 ):
        a = math.pi / 2 * k / 8
        prof.append( ( math.sin( a ), math.cos( a ) ) )
    # Sides.
    for sy in ( -1, 1 ):
        anchored_wall( m, "rs_siding_white", ( -hx, sy * hy ), ( hx - 18, sy * hy ), F, T - 8, v( 0, sy, 0 ), base_z=F - 4 )
        # The roof's rounded edge.
        for k in range( 4 ):
            a0, a1 = math.pi / 2 * k / 4, math.pi / 2 * ( k + 1 ) / 4
            p0 = ( sy * ( hy - 8 + 8 * math.cos( a0 ) ), T - 8 + 8 * math.sin( a0 ) )
            p1 = ( sy * ( hy - 8 + 8 * math.cos( a1 ) ), T - 8 + 8 * math.sin( a1 ) )
            card( m, "rs_siding_white", [ v( -hx, p0[0], p0[1] ), v( hx - 18, p0[0], p0[1] ), v( hx - 18, p1[0], p1[1] ), v( -hx, p1[0], p1[1] ) ],
                  v( 0, sy * math.cos( ( a0 + a1 ) / 2 ), math.sin( ( a0 + a1 ) / 2 ) ),
                  uv=[ ( 0, 0.9 + k * 0.02 ), ( 3.2, 0.9 + k * 0.02 ), ( 3.2, 0.92 + k * 0.02 ), ( 0, 0.92 + k * 0.02 ) ] )
    box( m, -hx, hx - 18, -hy + 8, hy - 8, T - 1, T, "rs_siding_white" )
    # The rounded front: a quarter-round in plan each side, raked back.
    for sy in ( -1, 1 ):
        for k in range( 6 ):
            a0, a1 = math.pi / 2 * k / 6, math.pi / 2 * ( k + 1 ) / 6
            q = [ v( hx - 18 + 18 * math.sin( a0 ), sy * ( hy - 18 + 18 * math.cos( a0 ) ), F ), v( hx - 18 + 18 * math.sin( a1 ), sy * ( hy - 18 + 18 * math.cos( a1 ) ), F ),
                  v( hx - 26 + 18 * math.sin( a1 ), sy * ( hy - 18 + 18 * math.cos( a1 ) ), T - 4 ), v( hx - 26 + 18 * math.sin( a0 ), sy * ( hy - 18 + 18 * math.cos( a0 ) ), T - 4 ) ]
            mid = ( a0 + a1 ) / 2
            card( m, "rs_siding_white", q, v( math.sin( mid ), sy * math.cos( mid ), 0.2 ), uv=[ ( k * 0.1, 0.0 ), ( k * 0.1 + 0.1, 0.0 ), ( k * 0.1 + 0.1, 0.95 ), ( k * 0.1, 0.95 ) ] )
    card( m, "rs_siding_white", [ v( hx, -hy + 18, F ), v( hx, hy - 18, F ), v( hx - 8, hy - 18, T - 4 ), v( hx - 8, -hy + 18, T - 4 ) ], v( 1, 0, 0.15 ),
          uv=[ ( 0, 0 ), ( 0.6, 0 ), ( 0.6, 0.95 ), ( 0, 0.95 ) ] )
    card( m, "rs_siding_white", [ v( hx - 8, -hy + 18, T - 4 ), v( hx - 8, hy - 18, T - 4 ), v( hx - 18, hy - 18, T ), v( hx - 18, -hy + 18, T ) ], v( 0.5, 0, 1 ) )
    for sy in ( -1, 1 ):
        card( m, "rs_siding_white", [ v( hx - 18, sy * ( hy - 18 ), T - 4 ), v( hx - 8, sy * ( hy - 18 ), T - 4 ), v( hx - 18, sy * ( hy - 18 ), T ) ], v( 0.3, sy, 0.8 ) )
    fc = v( hx - 4, 0, F + 52 )
    RP.quad( m, "rs_alu", fc, v( 0, 1, 0 ), unit( v( -0.15, 0, 1 ) ), 50, 30, off=0.3 )
    RP.quad( m, "rs_window_dark", fc, v( 0, 1, 0 ), unit( v( -0.15, 0, 1 ) ), 46, 26, off=0.45 )
    for k in range( 3 ):
        ang = rng.normal( 0, 0.1 )
        r2 = v( 0, math.cos( ang ), math.sin( ang ) )
        RP.quad( m, "rs_plywood", fc + UP * ( ( k - 1 ) * 9 ), r2, unit( np.cross( v( 1, 0, 0.15 ), r2 ) ), 60, 9, off=0.7 + 0.1 * k )
    # Back wall.
    anchored_wall( m, "rs_siding_white", ( -hx, hy ), ( -hx, -hy ), F, T, v( -1, 0, 0 ), base_z=F - 4 )
    # Under the floor: dark, with the axle.
    box( m, -hx + 4, hx - 10, -hy + 4, hy - 4, 10, F, "rs_dark" )
    for sy in ( -1, 1 ):
        tire( m, v( -20, sy * ( hy - 4 ), 13 ), ( 0, 1, 0 ), r=13, w=8 )
        box( m, -42, 2, sy * hy - 1 if sy > 0 else -hy, sy * hy if sy > 0 else -hy + 1, 22, 30, "rs_alu" )
    # The stripe: a red band with a thin second line, on both sides and round the front.
    for sy in ( -1, 1 ):
        right = v( -1, 0, 0 ) if sy > 0 else v( 1, 0, 0 )
        RP.quad( m, "rs_red_stripe", v( -18, sy * hy, F + 34 ), right, UP, L - 36, 4.5, off=0.3 )
        RP.quad( m, "rs_red_stripe", v( -18, sy * hy, F + 29 ), right, UP, L - 36, 1.4, off=0.3 )
    # Windows boarded with plywood, one with a broken pane; the door; the handprint and smears.
    for sy in ( -1, 1 ):
        right = v( -1, 0, 0 ) if sy > 0 else v( 1, 0, 0 )
        for x, wv, hv in ( ( 100, 46, 28 ), ( 20, 30, 26 ), ( -90, 48, 28 ) ):
            c = v( x, sy * hy, F + 58 )
            RP.quad( m, "rs_alu", c, right, UP, wv + 3, hv + 3, off=0.35 )
            RP.quad( m, "rs_window_dark", c, right, UP, wv, hv, off=0.5 )
            for k in range( 3 ):
                ang = rng.normal( 0, 0.1 )
                r2 = right * math.cos( ang ) + UP * math.sin( ang )
                u2 = unit( np.cross( np.cross( right, UP ), r2 ) )
                RP.quad( m, "rs_plywood", c + UP * ( ( k - 1 ) * hv * 0.34 ), r2, u2, wv + 14, hv * 0.32, off=0.7 + 0.1 * k )
    door( m, v( -40, -hy, F ), v( 1, 0, 0 ), w=26, h=72, paint_name="rs_siding_white" )
    blood( m, "hand", v( 60, -hy, F + 50 ), v( 1, 0, 0 ), 22, off=0.9 )
    blood( m, "smear", v( 30, -hy, F + 40 ), v( 1, 0, 0 ), 18, off=0.85 )
    blood( m, "hand", v( 120, hy, F + 48 ), v( -1, 0, 0 ), 20, off=0.9 )
    blood( m, "hand", v( -110, hy, F + 54 ), v( -1, 0, 0 ), 26, off=0.95 )
    blood( m, "smear", v( -70, hy, F + 40 ), v( -1, 0, 0 ), 22, off=0.9 )
    blood( m, "splatter", v( -130, hy, F + 30 ), v( -1, 0, 0 ), 30, off=0.85 )
    # A ladder up the back to the roof, a spare wheel, the tongue at the front.
    for sy in ( -1, 1 ):
        rod( m, v( -hx - 3, sy * 9, F ), v( -hx - 3, sy * 9, T + 4 ), 0.6, "rs_alu", 6 )
    for zz in np.arange( F + 10, T, 11 ):
        rod( m, v( -hx - 3, -9, zz ), v( -hx - 3, 9, zz ), 0.45, "rs_alu", 5 )
    tire( m, v( -hx - 6, 30, 50 ), ( 1, 0, 0 ), r=13, w=7 )
    for sy in ( -1, 1 ):
        m.beam( v( hx - 6, sy * 26, 16 ), v( hx + 40, 0, 14 ), ( 3, 4 ), "rs_rust" )
    cylinder( m, ( hx + 38, 0 ), 1.6, 0, 16, "rs_rust", 6 )
    # A propane pair on the tongue.
    for sy in ( -1, 1 ):
        cylinder( m, ( hx + 12, sy * 9 ), 6, 18, 36, "rs_propane", 10, top="rs_propane" )
    m.collision_box( v( -hx, -hy, 0 ), v( hx, hy, T ), SHEET )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Signs and towers

def park_sign( m, base, facing, scale=1.0, height=None ):
    """ RIVERSIDE TRAILER PARK: a roadside sign on two steel posts: the top board with its red neon script and bulb
    letters, the GOOD TIMES / BIGGER TOMORROW marquee under it, and a plywood board between the posts with STILL HERE
    sprayed on it. Faces facing (plan). """
    f = unit( ( facing[0], facing[1], 0 ) )
    right = right_for( f )
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    s = scale
    W = 270 * s
    top_h = W / RM.aspect( RM.LIT, "park_sign" )
    mq_w = 210 * s
    mq_h = mq_w / RM.aspect( RM.LIT, "marquee" )
    z_top = height if height else 500 * s
    z_board = z_top - top_h
    z_mq = z_board - 14 * s - mq_h
    # Posts: steel pipes from the ground to the top board.
    for sx in ( -1, 1 ):
        p = b + right * ( sx * W * 0.32 )
        cylinder( m, p, 4.5 * s, b[2], b[2] + z_top - 6, "rs_steel", 10, surface=METAL )
        cylinder( m, p, 9 * s, b[2], b[2] + 8, "rs_concrete", 10, top="rs_concrete" )
    # The top board's box, its faces lit both ways (the back shows the sign's grey back).
    depth = 14 * s
    centre = b + UP * ( z_board + top_h / 2 )
    obox( m, centre, right, ( W + 8, depth, top_h + 8 ), "rs_dark", METAL )
    lit( m, "park_sign", centre + f * ( depth / 2 ), right, top_h, off=0.4, w=W )
    sign( m, "sign_back", centre - f * ( depth / 2 ), -right, top_h, off=0.4, w=W )
    # Bulbs round the top board's edge.
    for k in range( 34 ):
        t = k / 33
        for zz in ( b[2] + z_board - 2, b[2] + z_board + top_h + 2 ):
            p = v( b[0], b[1], zz ) + right * ( ( t - 0.5 ) * ( W + 4 ) ) + f * ( depth / 2 + 1 )
            lathe( m, p, [ ( 1.2, zz - 1.5 ), ( 1.6, zz ), ( 1.2, zz + 1.5 ), ( 0.0, zz + 2.0 ) ], "rs_bulb" if k % 9 else "rs_bulb_dead", 6 )
    # The marquee: a lit panel in a steel frame, hung under the board.
    mc = b + UP * ( z_mq + mq_h / 2 )
    obox( m, mc, right, ( mq_w + 8, 10 * s, mq_h + 8 ), "rs_steel", METAL )
    lit( m, "marquee", mc + f * ( 5 * s ), right, mq_h, off=0.4, w=mq_w )
    sign( m, "sign_back", mc - f * ( 5 * s ), -right, mq_h, off=0.4, w=mq_w )
    for sx in ( -1, 1 ):
        m.beam( b + right * ( sx * mq_w * 0.42 ) + UP * ( z_board - 2 ), b + right * ( sx * mq_w * 0.42 ) + UP * ( z_mq + mq_h + 2 ), ( 1.2, 1.2 ), "rs_steel" )
    # The plywood board between the posts, and the graffiti on it.
    pw, ph = W * 0.62, 70 * s
    pc = b + UP * ( z_mq - 26 * s - ph / 2 ) + f * 4
    obox( m, pc, right, ( pw, 1.5, ph ), "rs_plywood", WOOD )
    paint( m, "still_here", pc + f * 0.8, right, ph * 0.86, tone="red", off=0.0 )
    # Its lights: the neon's red glow and the bulbs' warm one, shining on the trailers below.
    light( "sign neon", centre + f * 50, RED, 420, scale=2.2 )
    light( "sign bulbs", centre + f * 60 - UP * ( top_h * 0.25 ), WARM, 520, shadows=True, scale=2.4 )
    light( "sign marquee", mc + f * 40, COOL, 260, scale=1.2 )
    m.collision_box( b - right * ( W * 0.34 ) - f * 6, b + right * ( W * 0.34 ) + f * 6 + UP * 40, METAL )


def neon_sign( m, base, facing, height=360.0, name="no_place" ):
    """ A neon box sign on a steel post: NO PLACE BETTER. """
    f = unit( ( facing[0], facing[1], 0 ) )
    right = right_for( f )
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    sh = 120.0
    sw = sh * RM.aspect( RM.LIT, name )
    cylinder( m, b, 4.0, b[2], b[2] + height, "rs_steel", 10, surface=METAL )
    centre = b + UP * ( height + sh / 2 - 10 )
    obox( m, centre, right, ( sw + 6, 10, sh + 6 ), "rs_dark", METAL )
    lit( m, name, centre + f * 5, right, sh, off=0.3, w=sw )
    lit( m, name, centre - f * 5, -right, sh, off=0.3, w=sw )
    light( f"{name} glow", centre + f * 40, RED, 500, scale=2.6 )
    light( f"{name} glow back", centre - f * 40, RED, 300, scale=1.4 )


def speed_sign( m, base, facing, z_bottom=78.0 ):
    f = unit( ( facing[0], facing[1], 0 ) )
    right = right_for( f )
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    obox( m, b + UP * ( z_bottom / 2 + 16 ), right, ( 2.5, 2.5, z_bottom + 32 ), "rs_steel", METAL )
    c = b + UP * ( z_bottom + 15 ) + f * 1.5
    sign( m, "speed", c, right, 30, off=0.2 )
    sign( m, "sign_back", c - f * 0.2, -right, 30, off=0.0 )


def water_tower( m, base, facing=( -1, -1 ) ):
    """ A steel water tower: four splayed legs braced in tiers, a riser, a cylindrical tank with a conical roof and a
    finial, a catwalk with a railing, and RIVERSIDE STICKS TOGETHER painted across the tank. """
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    r_tank, z0, z1 = 210.0, 1100.0, 1330.0
    f = unit( ( facing[0], facing[1], 0 ) )
    legs = []
    for k in range( 4 ):
        a = math.pi / 4 + k * math.pi / 2
        foot = b + v( math.cos( a ), math.sin( a ), 0 ) * 230
        head = b + v( math.cos( a ), math.sin( a ), 0 ) * 150 + UP * z0
        lathe_seg( m, foot, head, 7.0, 6.0, "rs_tank", 8 )
        legs.append( ( foot, head ) )
    for tier in np.linspace( 0.15, 0.85, 4 ):
        pts = [ fo + ( he - fo ) * tier for fo, he in legs ]
        for k in range( 4 ):
            m.beam( pts[k], pts[( k + 1 ) % 4], ( 3, 3 ), "rs_tank" )
            nt = min( 1.0, tier + 0.233 )
            nxt = [ fo + ( he - fo ) * nt for fo, he in legs ]
            rod( m, pts[k], nxt[( k + 1 ) % 4], 0.8, "rs_tank", 4 )
    bz = b[2]
    cylinder( m, b, 18, bz, bz + z0, "rs_tank", 10 )
    cylinder( m, b, r_tank, bz + z0, bz + z1, "rs_tank", 28, bottom="rs_tank" )
    lathe( m, b, [ ( r_tank + 2, bz + z1 ), ( r_tank * 0.55, bz + z1 + 70 ), ( 18, bz + z1 + 110 ), ( 0, bz + z1 + 112 ) ], "rs_tank", 28 )
    cylinder( m, b, 6, bz + z1 + 110, bz + z1 + 140, "rs_tank", 8, top="rs_tank" )
    # The catwalk round the tank's foot.
    zc = bz + z0 + 4
    ring_out = r_tank + 34
    lathe( m, b, [ ( r_tank, zc ), ( ring_out, zc ) ], "rs_steel", 28 )
    for k in range( 28 ):
        a0, a1 = 2 * math.pi * k / 28, 2 * math.pi * ( k + 1 ) / 28
        p0 = v( b[0], b[1], zc ) + v( math.cos( a0 ), math.sin( a0 ), 0 ) * ring_out
        p1 = v( b[0], b[1], zc ) + v( math.cos( a1 ), math.sin( a1 ), 0 ) * ring_out
        rod( m, p0 + UP * 40, p1 + UP * 40, 1.0, "rs_steel", 5 )
        rod( m, p0, p0 + UP * 40, 0.9, "rs_steel", 5 )
    # Rust streaks down the tank (dark quads), the lettering facing the park.
    right = right_for( f )
    c = b + f * ( r_tank + 0.6 ) + UP * ( ( z0 + z1 ) / 2 )
    paint( m, "sticks", c, right, ( z1 - z0 ) * 0.8, tone="white", off=0.0 )
    # Floodlights on the catwalk lighting the lettering, and the aviation beacon on its finial.
    for sx in ( -1, 1 ):
        lamp = v( b[0], b[1], zc ) + f * ( r_tank + 26 ) + right * ( sx * r_tank * 0.45 ) + UP * 6
        obox( m, lamp, right, ( 10, 8, 7 ), "rs_dark" )
        card( m, "rs_lamp_sodium", [ lamp + f * -4.2 + right * -4 + UP * 2.5, lamp + f * -4.2 + right * 4 + UP * 2.5,
                                     lamp + f * -4.2 + right * 4 - UP * 2.5, lamp + f * -4.2 + right * -4 - UP * 2.5 ], -f )
    light( "water tower flood", c + f * 180 - UP * 70, SODIUM, 900, scale=4.0 )
    beacon = v( b[0], b[1], bz + z1 + 142 )
    cylinder( m, beacon, 3.5, beacon[2], beacon[2] + 6, "rs_drum_red", 8, top="rs_drum_red" )
    light( "water tower beacon", beacon + UP * 10, RED, 260, scale=2.0 )
    m.collision_box( b - v( 20, 20, 0 ), b + v( 20, 20, z0 ), METAL )


LAMP_LENS = ( 10.2, 8.0 )      # the searchlight's lens: how far along its aim from the head, its radius


def guard_tower( m, base, facing=( 0, -1 ), deck=520.0, aim=None ):
    """ A timber watchtower somebody put up after it started: four poles, X bracing, a plywood cab with a corrugated
    roof, a ladder, and a searchlight sweeping the park, pointed at aim (else straight out along facing). Returns the lamp
    head's centre; its lens is LAMP_LENS[0] along the aim from there, LAMP_LENS[1] in radius. """
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    f = unit( ( facing[0], facing[1], 0 ) )
    side = np.cross( UP, f )
    half_foot, half_top = 70.0, 46.0
    corners = []
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            foot = b + side * ( sx * half_foot ) + f * ( sy * half_foot )
            head = b + side * ( sx * half_top ) + f * ( sy * half_top ) + UP * ( deck + 90 )
            lathe_seg( m, foot, head, 5.5, 4.5, "rs_pole", 8 )
            corners.append( ( foot, head ) )
    order = [ 0, 1, 3, 2 ]
    for tier in ( 0.0, 0.35, 0.7 ):
        for k in range( 4 ):
            a, bb = corners[order[k]], corners[order[( k + 1 ) % 4]]
            p0 = a[0] + ( a[1] - a[0] ) * tier
            p1 = bb[0] + ( bb[1] - bb[0] ) * ( tier + 0.3 )
            m.beam( p0, p1, ( 2.5, 5.5 ), "rs_wood" )
    # The deck and the cab: plywood half walls, open above, posts, a corrugated roof.
    deck_c = b + UP * deck
    obox( m, deck_c, side, ( half_top * 2 + 24, half_top * 2 + 24, 6 ), "rs_wood", WOOD )
    hw = half_top + 12
    for k, d in enumerate( ( f, side, -f, -side ) ):
        r = np.cross( d, UP )
        c = deck_c + d * hw + UP * 22
        obox( m, c, r, ( hw * 2, 1.5, 44 ), "rs_plywood" )
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            p = deck_c + side * ( sx * hw ) + f * ( sy * hw )
            obox( m, p + UP * 50, side, ( 4, 4, 100 ), "rs_wood" )
    roof_c = deck_c + UP * 104
    pts = [ roof_c + side * ( -hw - 10 ) + f * ( -hw - 10 ) + UP * 8, roof_c + side * ( hw + 10 ) + f * ( -hw - 10 ) + UP * 8,
            roof_c + side * ( hw + 10 ) + f * ( hw + 10 ), roof_c + side * ( -hw - 10 ) + f * ( hw + 10 ) ]
    card( m, "rs_roof", pts, UP + f * 0.1 )
    card( m, "rs_roof", pts, -UP )
    # The ladder up one side.
    lb = b - f * ( half_foot + 18 )
    for sx in ( -1, 1 ):
        rod( m, lb + side * ( sx * 9 ), lb + side * ( sx * 9 ) + UP * deck - f * -20 + f * 0, 1.2, "rs_wood", 5 )
    for zz in np.arange( 12, deck, 12 ):
        p = lb + UP * zz + f * ( 20 * zz / deck )
        rod( m, p - side * 9, p + side * 9, 0.9, "rs_wood", 5 )
    # The searchlight on the rail, aimed down the park.
    sl = deck_c + f * ( hw - 6 ) + UP * 52
    cylinder( m, sl, 2.5, sl[2] - 10, sl[2], "rs_steel", 8 )
    head = sl + UP * 6
    a = unit( v( *aim ) - head ) if aim is not None else f
    a_side, a_up = RP.perp( a )
    rod( m, sl + UP * 2, head, 1.5, "rs_steel", 6 )
    rod( m, head - a * 8, head + a * 10, 9, "rs_dark", 12, caps=True )
    card( m, "rs_lamp_search", [ head + a * LAMP_LENS[0] + ( a_side * math.cos( 2 * math.pi * k / 12 ) + a_up * math.sin( 2 * math.pi * k / 12 ) ) * LAMP_LENS[1]
                                 for k in range( 12 ) ], a )
    m.collision_box( b - v( half_foot, half_foot, 0 ), b + v( half_foot, half_foot, 40 ), WOOD )
    return head


def beam_cone( m, lens, target, lens_radius=8.0, half_angle=4.5, outer_angle=7.5, overshoot=1.5, sides=24 ):
    """ A searchlight's beam from a lens of lens_radius at lens towards target, as the closed proxy hc1_light_beam.shader
    marches through (rs_beam): a truncated cone with outward normals, from the lens to overshoot times the way to the
    target (the scene's depth ends the light where it lands). The light spreads at half_angle (where it falls to 1/e^2)
    from a virtual source behind the lens, so it leaves the lens lens_radius wide; the proxy is outer_angle wide, past
    where any light shows. Drawn only: put it in a model with no shadows or collision. Returns the cone for the material:
    ( apex, axis, start, end ) in plan space, start and end along the axis from the apex. """
    lens, t = v( *lens ), v( *target )
    d = unit( t - lens )
    start = lens_radius / math.tan( math.radians( half_angle ) )
    apex = lens - d * start
    end = start + overshoot * float( np.linalg.norm( t - lens ) )
    u, w = RP.perp( d )
    r0 = start * math.tan( math.radians( outer_angle ) )
    r1 = end * math.tan( math.radians( outer_angle ) )
    p0, p1 = apex + d * start, apex + d * end
    rims = []
    for k in range( sides ):
        a = 2 * math.pi * k / sides
        e = u * math.cos( a ) + w * math.sin( a )
        # The side's outward normal leans back towards the apex by the cone's angle.
        n = unit( e * math.cos( math.radians( outer_angle ) ) - d * math.sin( math.radians( outer_angle ) ) )
        rims.append( ( p0 + e * r0, p1 + e * r1, n ) )
    for k in range( sides ):
        ( a0, b0, n0 ), ( a1, b1, n1 ) = rims[k], rims[( k + 1 ) % sides]
        m.polygon( "rs_beam", [ a0, a1, b1, b0 ], normal=n0 + n1, uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ], normals=[ n0, n1, n1, n0 ] )
    m.polygon( "rs_beam", [ r[0] for r in reversed( rims ) ], normal=-d )
    m.polygon( "rs_beam", [ r[1] for r in rims ], normal=d )
    return apex, d, start, end


# ---------------------------------------------------------------------------------------------------------------------
# Trees

def pine( m, base, height=700.0, seed=0, crown_share=0.35, lod=0 ):
    """ A slash pine: a tall straight trunk, bare below, a rounded crown of needle tufts on crooked limbs at the top.
    lod 1 is the far version: fewer, bigger tufts. """
    rng = np.random.default_rng( seed )
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    lean = v( rng.normal( 0, 0.02 ), rng.normal( 0, 0.02 ), 1 )
    lean = unit( lean )
    top = b + lean * height
    r0 = height / 70
    lathe_seg( m, b, b + lean * height * 0.5, r0, r0 * 0.7, "rs_pine_bark", 7 if lod == 0 else 5 )
    lathe_seg( m, b + lean * height * 0.5, top, r0 * 0.7, r0 * 0.25, "rs_pine_bark", 7 if lod == 0 else 5 )
    crown_base = height * ( 1 - crown_share )
    limbs = int( rng.integers( 5, 8 ) ) if lod == 0 else 4
    tufts = []
    for k in range( limbs ):
        a = rng.uniform( 0, 2 * math.pi )
        hz = rng.uniform( crown_base, height * 0.97 )
        reach = ( height - hz ) * rng.uniform( 0.25, 0.5 ) + height * 0.05
        start = b + lean * hz
        end = start + v( math.cos( a ), math.sin( a ), 0 ) * reach + UP * rng.uniform( 0.1, 0.4 ) * reach
        if lod == 0:
            rod( m, start, end, r0 * 0.25, "rs_pine_bark", 4 )
        tufts.append( end )
    tufts.append( top )
    for p in tufts:
        size = height * rng.uniform( 0.13, 0.19 ) * ( 1.3 if lod else 1.0 )
        cards = 3 if lod == 0 else 2
        for j in range( cards ):
            a = rng.uniform( 0, math.pi ) + j * math.pi / cards
            r = v( math.cos( a ), math.sin( a ), 0 )
            tilt = rng.normal( 0, 0.3 )
            up = unit( UP + v( -math.sin( a ), math.cos( a ), 0 ) * tilt )
            c = p + UP * size * 0.15
            uv = [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ]
            pts = [ c - r * size / 2 - up * size / 2, c + r * size / 2 - up * size / 2, c + r * size / 2 + up * size / 2, c - r * size / 2 + up * size / 2 ]
            m.polygon( "rs_pine_needles", pts, uv=uv, both_sides=True )
        # A flat-ish tuft card to fill the crown seen from below.
        if lod == 0:
            a = rng.uniform( 0, math.pi )
            r = v( math.cos( a ), math.sin( a ), 0 )
            s2 = np.cross( UP, r )
            pts = [ p - r * size / 2 - s2 * size / 2, p + r * size / 2 - s2 * size / 2, p + r * size / 2 + s2 * size / 2, p - r * size / 2 + s2 * size / 2 ]
            m.polygon( "rs_pine_needles", pts, uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ], both_sides=True )


def palm( m, base, height=420.0, seed=0, lod=0 ):
    """ A cabbage palm: a slightly bent trunk rough with old leaf bases, a crown of fan fronds arching out, a few dead
    ones hanging brown. """
    rng = np.random.default_rng( seed )
    b = v( base[0], base[1], base[2] if len( base ) > 2 else 0.0 )
    bend = v( rng.normal( 0, 0.12 ), rng.normal( 0, 0.12 ), 0 )
    prev = b
    segs = 5
    for k in range( 1, segs + 1 ):
        t = k / segs
        p = b + UP * ( height * t ) + bend * height * t * t
        lathe_seg( m, prev, p, 7.5 - 1.0 * ( k - 1 ) / segs, 7.5 - 1.0 * k / segs, "rs_palm_trunk", 8 if lod == 0 else 5 )
        prev = p
    top = prev
    fronds = 16 if lod == 0 else 9
    for k in range( fronds ):
        a = 2 * math.pi * k / fronds + rng.normal( 0, 0.15 )
        d = v( math.cos( a ), math.sin( a ), 0 )
        droop = rng.uniform( -0.25, 0.6 )
        stem = height * rng.uniform( 0.16, 0.24 )
        tip = top + d * stem + UP * ( stem * ( 0.6 - droop ) )
        rod( m, top, tip, 0.9, "rs_palm_trunk", 4 ) if lod == 0 else None
        size = height * rng.uniform( 0.28, 0.36 )
        out_dir = unit( d * math.cos( droop ) - UP * math.sin( droop ) * 0.7 + UP * 0.25 )
        side = np.cross( UP, d )
        c = tip + out_dir * size * 0.42
        pts = [ tip - side * size * 0.5, tip + side * size * 0.5, c + out_dir * size * 0.5 + side * size * 0.5, c + out_dir * size * 0.5 - side * size * 0.5 ]
        m.polygon( "rs_palm_frond", pts, uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ], both_sides=True )
    for k in range( 3 if lod == 0 else 0 ):
        a = rng.uniform( 0, 2 * math.pi )
        d = v( math.cos( a ), math.sin( a ), 0 )
        side = np.cross( UP, d )
        p0 = top + d * 6 - UP * 6
        pts = [ p0 - side * 18, p0 + side * 18, p0 + side * 14 - UP * 60 + d * 10, p0 - side * 14 - UP * 60 + d * 10 ]
        m.polygon( "rs_palm_dead", pts, uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ], both_sides=True )
    return top


def far_trees( m, centre, radius, z0, height, count=48, seed=0 ):
    """ A ring of tree-line cards: the forest's crowns against the sky far off, each card a stretch of the band. """
    rng = np.random.default_rng( seed )
    c = v( centre[0], centre[1], 0 )
    for k in range( count ):
        a0 = 2 * math.pi * k / count + rng.normal( 0, 0.01 )
        a1 = 2 * math.pi * ( k + 1.15 ) / count
        r = radius * rng.uniform( 0.96, 1.04 )
        p0 = c + v( math.cos( a0 ), math.sin( a0 ), 0 ) * r
        p1 = c + v( math.cos( a1 ), math.sin( a1 ), 0 ) * r
        h = height * rng.uniform( 0.8, 1.2 )
        u0 = rng.uniform( 0, 0.5 )
        pts = [ p0 + UP * z0, p1 + UP * z0, p1 + UP * ( z0 + h ), p0 + UP * ( z0 + h ) ]
        m.polygon( "rs_pine_far", pts, uv=[ ( u0, 0 ), ( u0 + 0.5, 0 ), ( u0 + 0.5, 1 ), ( u0, 1 ) ], both_sides=True )
