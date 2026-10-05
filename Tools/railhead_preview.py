"""
Railhead's previews: flat-shaded pictures for checking the map without the editor, drawn with the paints' mean colours
(a numpy z-buffer, as Belltower's and Reef Hall's previews), lit by the scene's sun and sky, with glass blended over
what's behind it and the scene's fog.

    python Tools/railhead_preview.py <out dir> [view ...]       (the structure only; railhead_map --preview draws all)

A paint's colour is its texture's mean (Assets/materials/railhead/<paint>_color.png, or Belltower's building
materials), or a stand-in from STAND_INS while the materials haven't been drawn.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K

ROOT = Path( __file__ ).resolve().parent.parent
MATERIALS = ROOT / "Assets/materials/railhead"
BUILDINGS = ROOT / "Assets/materials/buildings"
BELLTOWER = ROOT / "Assets/materials/belltower"

SUN_PITCH, SUN_YAW = 38.0, -15.0


def sun_direction():
    """ Towards the sun, plan ( e, n, z ). The light points pitch down, yaw from north towards west. """
    p, y = math.radians( SUN_PITCH ), math.radians( SUN_YAW )
    world = np.array( ( math.cos( p ) * math.cos( y ), math.cos( p ) * math.sin( y ), -math.sin( p ) ) )
    return -np.array( ( -world[1], world[0], world[2] ) )


SUN = sun_direction()
SKY = ( np.array( ( 0.80, 0.85, 0.90 ) ), np.array( ( 0.38, 0.55, 0.82 ) ) )
FOG = np.array( ( 0.72, 0.78, 0.86 ) )

STAND_INS = {
    "rw_paving": ( 0.62, 0.60, 0.56 ), "rw_paving_warm": ( 0.66, 0.60, 0.52 ), "rw_paving_dark": ( 0.40, 0.40, 0.40 ),
    "rw_tactile": ( 0.80, 0.80, 0.78 ), "rw_tactile_dots": ( 0.80, 0.80, 0.78 ), "rw_coping": ( 0.78, 0.77, 0.72 ),
    "rw_line_white": ( 0.92, 0.92, 0.90 ), "rw_line_yellow": ( 0.90, 0.75, 0.15 ), "rw_hazard": ( 0.80, 0.65, 0.12 ),
    "rw_ballast": ( 0.48, 0.46, 0.43 ), "rw_ballast_rusty": ( 0.45, 0.36, 0.28 ), "rw_ballast_old": ( 0.38, 0.35, 0.31 ),
    "rw_sleeper": ( 0.55, 0.54, 0.52 ), "rw_sleeper_wood": ( 0.30, 0.24, 0.18 ), "rw_rail": ( 0.36, 0.26, 0.20 ),
    "rw_rail_head": ( 0.70, 0.70, 0.72 ), "rw_asphalt": ( 0.26, 0.26, 0.27 ), "rw_kerb": ( 0.70, 0.69, 0.66 ),
    "rw_concrete": ( 0.62, 0.61, 0.58 ), "rw_concrete_dark": ( 0.42, 0.41, 0.39 ), "rw_terrazzo": ( 0.76, 0.72, 0.64 ),
    "rw_terrazzo_border": ( 0.45, 0.30, 0.25 ), "rw_sandstone": ( 0.78, 0.64, 0.48 ), "rw_dressed": ( 0.82, 0.72, 0.58 ),
    "rw_dressed_red": ( 0.58, 0.32, 0.25 ), "rw_steel": ( 0.32, 0.40, 0.38 ), "rw_steel_dark": ( 0.18, 0.20, 0.21 ),
    "rw_steel_grey": ( 0.50, 0.52, 0.54 ), "rw_lattice": ( 0.30, 0.38, 0.36 ), "rw_window_dark": ( 0.12, 0.15, 0.18 ),
    "rw_glass": ( 0.60, 0.72, 0.78 ), "rw_glass_roof": ( 0.70, 0.78, 0.80 ), "rw_black": ( 0.05, 0.05, 0.05 ),
    "rw_white_paint": ( 0.90, 0.90, 0.88 ), "rw_yellow_paint": ( 0.90, 0.72, 0.10 ), "rw_red_paint": ( 0.70, 0.12, 0.10 ),
    "rw_wood": ( 0.50, 0.36, 0.22 ), "rw_rubber": ( 0.08, 0.08, 0.08 ), "rw_lamp_warm": ( 1.0, 0.90, 0.70 ),
    "rw_lamp_cool": ( 0.90, 0.95, 1.0 ), "rw_clock": ( 0.92, 0.92, 0.88 ), "rw_bogie": ( 0.16, 0.16, 0.16 ),
    "rw_train_red": ( 0.65, 0.12, 0.12 ), "rw_train_blue": ( 0.15, 0.25, 0.50 ), "rw_train_white": ( 0.88, 0.88, 0.86 ),
    "rw_train_grey": ( 0.55, 0.56, 0.58 ), "rw_train_dark": ( 0.15, 0.15, 0.16 ), "rw_train_yellow": ( 0.85, 0.70, 0.15 ),
    "rw_wagon_rust": ( 0.42, 0.24, 0.15 ), "rw_wagon_grey": ( 0.45, 0.46, 0.45 ),
    "rw_container_blue": ( 0.15, 0.30, 0.55 ), "rw_container_red": ( 0.60, 0.15, 0.12 ),
    "rw_container_green": ( 0.20, 0.42, 0.25 ), "rw_container_orange": ( 0.80, 0.42, 0.12 ),
    "rw_container_grey": ( 0.55, 0.56, 0.56 ), "rw_facade_cream": ( 0.85, 0.78, 0.64 ),
    "rw_facade_ochre": ( 0.80, 0.62, 0.36 ), "rw_facade_grey": ( 0.62, 0.62, 0.60 ), "rw_facade_rose": ( 0.78, 0.58, 0.54 ),
    "rw_signal_red": ( 1.0, 0.2, 0.15 ), "rw_signal_green": ( 0.3, 1.0, 0.5 ), "rw_signal_yellow": ( 1.0, 0.8, 0.2 ),
    "brick": ( 0.55, 0.30, 0.22 ), "corrugated": ( 0.48, 0.50, 0.50 ), "slate": ( 0.28, 0.30, 0.33 ),
    "roof_tiles": ( 0.62, 0.30, 0.20 ), "copper": ( 0.36, 0.58, 0.50 ), "copper_brown": ( 0.38, 0.24, 0.16 ),
    "planks": ( 0.55, 0.42, 0.28 ), "planks_dark": ( 0.32, 0.24, 0.17 ), "setts": ( 0.45, 0.43, 0.41 ),
    "gravel": ( 0.55, 0.53, 0.50 ), "render_cream": ( 0.88, 0.82, 0.70 ), "trim_white": ( 0.90, 0.89, 0.85 ),
    "iron_black": ( 0.10, 0.10, 0.11 ), "roller_grey": ( 0.52, 0.53, 0.54 ),
}
GLOWING = { "rw_lamp_warm", "rw_lamp_cool", "rw_signal_red", "rw_signal_green", "rw_signal_yellow", "rw_displays" }
_colours = {}


def is_glass( paint ):
    return paint in ( "rw_glass", "rw_glass_roof" )


def paint_colour( paint ):
    if paint not in _colours:
        for path in ( MATERIALS / f"{paint}_color.png", BUILDINGS / f"{paint}_color.png", BELLTOWER / f"{paint}_color.png" ):
            if path.exists():
                small = Image.open( path ).convert( "RGB" ).resize( ( 32, 32 ) )
                _colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
                break
        else:
            colour = STAND_INS.get( paint, ( 1.0, 0.0, 1.0 ) )
            try:                    # the car paints are flat colours with no texture (railhead_materials.PAINTED)
                import railhead_materials as RM
                if paint in RM.PAINTED:
                    colour = tuple( c / 255.0 for c in RM.PAINTED[paint][0] )
            except Exception:
                pass
            _colours[paint] = np.array( colour, float )
    return _colours[paint]


def triangles( models, glass=False ):
    """ ( triangles ( T, 3, 3 ), normals, lit colours ) of the opaque paints, or with glass, of the glass. """
    tris, normals, colours = [], [], []
    for model in models:
        for paint, items in model.polygons.items():
            if is_glass( paint ) != glass:
                continue
            base = paint_colour( paint )
            for points, normal in items:
                if paint in GLOWING or glass:
                    lit = base
                else:
                    sky = 0.42 + 0.18 * normal[2]
                    lit = base * ( sky + 0.62 * max( 0.0, float( np.dot( normal, SUN ) ) ) )
                for k in range( 1, len( points ) - 1 ):
                    tris.append( ( points[0], points[k], points[k + 1] ) )
                    normals.append( normal )
                    colours.append( lit )
    return np.array( tris, float ).reshape( -1, 3, 3 ), np.array( normals, float ).reshape( -1, 3 ), \
        np.array( colours, float ).reshape( -1, 3 )


def rasterise( image, depth, screen, nearness, colours ):
    height, width = depth.shape
    lo = np.floor( screen.min( axis=1 ) ).astype( int )
    hi = np.ceil( screen.max( axis=1 ) ).astype( int )
    for t in range( len( screen ) ):
        x0, y0 = max( lo[t, 0], 0 ), max( lo[t, 1], 0 )
        x1, y1 = min( hi[t, 0], width - 1 ), min( hi[t, 1], height - 1 )
        if x1 < x0 or y1 < y0:
            continue
        ( ax, ay ), ( bx, by ), ( cx, cy ) = screen[t]
        area = ( bx - ax ) * ( cy - ay ) - ( by - ay ) * ( cx - ax )
        if abs( area ) < 1e-9:
            continue
        xs = np.arange( x0, x1 + 1 ) + 0.5
        ys = ( np.arange( y0, y1 + 1 ) + 0.5 )[:, None]
        w0 = ( ( bx - xs ) * ( cy - ys ) - ( by - ys ) * ( cx - xs ) ) / area
        w1 = ( ( cx - xs ) * ( ay - ys ) - ( cy - ys ) * ( ax - xs ) ) / area
        w2 = 1.0 - w0 - w1
        inside = ( w0 >= -1e-6 ) & ( w1 >= -1e-6 ) & ( w2 >= -1e-6 )
        if not inside.any():
            continue
        za, zb, zc = nearness[t]
        z = w0 * za + w1 * zb + w2 * zc
        region = depth[y0:y1 + 1, x0:x1 + 1]
        nearer = inside & ( z > region )
        region[nearer] = z[nearer]
        image[y0:y1 + 1, x0:x1 + 1][nearer] = colours[t]


def clip_near( tri, near ):
    points = []
    for k in range( 3 ):
        a, b = tri[k], tri[( k + 1 ) % 3]
        if a[2] >= near:
            points.append( a )
        if ( a[2] >= near ) != ( b[2] >= near ):
            points.append( a + ( near - a[2] ) / ( b[2] - a[2] ) * ( b - a ) )
    return [ np.array( ( points[0], points[k], points[k + 1] ) ) for k in range( 1, len( points ) - 1 ) ]


def project( data, eye, right, up, forward, focal, width, height, both_sides=False ):
    """ Triangles in screen space ( T, 3, 2 ), their nearness and colours, fogged. """
    tris, normals, colours = data
    if not len( tris ):
        return np.zeros( ( 0, 3, 2 ) ), np.zeros( ( 0, 3 ) ), np.zeros( ( 0, 3 ) )
    near = 2.0
    rel = tris - eye
    cam = np.stack( ( rel @ right, rel @ up, rel @ forward ), axis=-1 )
    keep = cam[:, :, 2].max( axis=1 ) > near
    if not both_sides:
        keep &= np.einsum( "ij,ij->i", normals, eye - tris[:, 0] ) > 0
    cam, cols = cam[keep], colours[keep]
    distance = np.linalg.norm( cam.mean( axis=1 ), axis=1 )
    fog = ( 0.75 * np.clip( ( distance - 3000.0 ) / 92000.0, 0.0, 1.0 ) ** 1.5 )[:, None]
    cols = cols * ( 1 - fog ) + FOG * fog
    whole = ( cam[:, :, 2] >= near ).all( axis=1 )
    pieces, piece_colours = [ cam[whole] ], [ cols[whole] ]
    for tri, col in zip( cam[~whole], cols[~whole] ):
        for part in clip_near( tri, near ):
            pieces.append( part[None] )
            piece_colours.append( col[None] )
    cam, cols = np.concatenate( pieces ), np.concatenate( piece_colours )
    screen = np.stack( ( width / 2 + focal * cam[:, :, 0] / cam[:, :, 2], height / 2 - focal * cam[:, :, 1] / cam[:, :, 2] ),
                       axis=-1 )
    on = ( ( screen[:, :, 0].max( axis=1 ) >= 0 ) & ( screen[:, :, 0].min( axis=1 ) < width )
           & ( screen[:, :, 1].max( axis=1 ) >= 0 ) & ( screen[:, :, 1].min( axis=1 ) < height ) )
    return screen[on], 1.0 / cam[on][:, :, 2], cols[on]


def perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=80.0 ):
    width, height = size
    eye, target = np.asarray( eye, float ), np.asarray( target, float )
    forward = K.normalise( target - eye )
    right = K.normalise( np.cross( forward, ( 0.0, 0.0, 1.0 ) ) )
    up = np.cross( right, forward )
    focal = ( width / 2 ) / math.tan( math.radians( fov ) / 2 )
    xs = ( np.arange( width ) + 0.5 - width / 2 ) / focal
    ys = ( height / 2 - np.arange( height ) - 0.5 ) / focal
    rays = forward + xs[None, :, None] * right + ys[:, None, None] * up
    elevation = rays[..., 2] / np.linalg.norm( rays, axis=2 )
    t = np.clip( elevation * 2.5, 0.0, 1.0 )[..., None]
    image = SKY[0] * ( 1 - t ) + SKY[1] * t
    depth = np.zeros( ( height, width ) )
    rasterise( image, depth, *project( opaque, eye, right, up, forward, focal, width, height ) )
    gimage, gdepth = np.zeros_like( image ), np.zeros_like( depth )
    rasterise( gimage, gdepth, *project( glass, eye, right, up, forward, focal, width, height, both_sides=True ) )
    over = gdepth > depth
    image[over] = image[over] * 0.72 + gimage[over] * 0.28
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


def top_down( opaque, glass, bounds, scale, cut=None ):
    """ Straight down: bounds ( e0, e1, n0, n1 ), scale units a pixel; cut leaves out everything higher. """
    e0, e1, n0, n1 = bounds
    width, height = int( ( e1 - e0 ) / scale ), int( ( n1 - n0 ) / scale )
    image = np.tile( np.array( ( 0.20, 0.22, 0.24 ) ), ( height, width, 1 ) )
    depth = np.full( ( height, width ), -1e9 )
    for data, tint in ( ( opaque, None ), ( glass, ( 0.35, 0.55, 0.62 ) ) ):
        tris, normals, colours = data
        if not len( tris ):
            continue
        keep = ( np.abs( normals[:, 2] ) > 0.02 if tint else normals[:, 2] > 0.02 ) \
            & ( tris[:, :, 0].max( axis=1 ) > e0 ) & ( tris[:, :, 0].min( axis=1 ) < e1 ) \
            & ( tris[:, :, 1].max( axis=1 ) > n0 ) & ( tris[:, :, 1].min( axis=1 ) < n1 )
        if cut is not None:
            keep &= tris[:, :, 2].max( axis=1 ) <= cut
        t = tris[keep]
        cols = colours[keep] if tint is None else np.tile( tint, ( len( t ), 1 ) )
        screen = np.stack( ( ( t[:, :, 0] - e0 ) / scale, ( n1 - t[:, :, 1] ) / scale ), axis=-1 )
        rasterise( image, depth, screen, t[:, :, 2], cols )
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


# ( name, eye, target, horizontal field of view ), plan inches
VIEWS = [
    ( "concourse", ( -420, 1180, 64 ), ( 300, -400, 80 ), 85 ),
    ( "platform_b", ( 650, -1000, 64 ), ( 600, 1300, 220 ), 80 ),
    ( "platform_c_north", ( 1060, 700, 64 ), ( 1060, -1500, 120 ), 80 ),
    ( "booking_hall", ( -500, 1720, 264 ), ( 300, 1350, 120 ), 90 ),
    ( "hall_floor", ( 0, 1380, 64 ), ( 0, 1800, 300 ), 90 ),
    ( "footbridge", ( -1100, -280, 276 ), ( 1100, -280, 260 ), 80 ),
    ( "cab_road", ( 1750, -1200, 58 ), ( 1700, 1400, 150 ), 80 ),
    ( "goods_yard", ( 2050, -2300, 64 ), ( 1450, -1500, 80 ), 85 ),
    ( "throat", ( 300, -2350, 30 ), ( -50, -1300, 140 ), 80 ),
    ( "signal_box", ( -20, -2000, 194 ), ( 0, -1300, 160 ), 90 ),
    ( "corridor_south", ( 100, -2300, 40 ), ( 0, -8000, 60 ), 70 ),
    ( "depot_lead", ( 500, -2350, 120 ), ( 1100, -3700, -20 ), 75 ),
    ( "aerial", ( -3600, -4200, 2600 ), ( 0, -200, 0 ), 70 ),
    ( "aerial_north", ( 2800, 3600, 2200 ), ( 0, -300, 100 ), 70 ),
]


def write_previews( out_dir, models, views=None, top=True ):
    out = Path( out_dir )
    out.mkdir( parents=True, exist_ok=True )
    opaque, glass = triangles( models ), triangles( models, glass=True )
    if top:
        top_down( opaque, glass, ( -2700, 2700, -2500, 1900 ), 5 ).save( out / "top.png" )
        top_down( opaque, glass, ( -2700, 2700, -2500, 1900 ), 5, cut=170 ).save( out / "top_ground.png" )
        print( f"wrote {out / 'top.png'}" )
    for name, eye, target, fov in VIEWS:
        if views and name not in views:
            continue
        perspective( opaque, glass, eye, target, fov=fov ).save( out / f"{name}.png" )
        print( f"wrote {out / name}.png" )


if __name__ == "__main__":
    import railhead_station as S

    write_previews( sys.argv[1], list( S.build().values() ), sys.argv[2:] or None )
