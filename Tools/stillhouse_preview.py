"""
Stillhouse's previews: flat-shaded pictures for checking the map without the editor, drawn with the paints' mean
colours (a numpy z-buffer, as Railhead's previews), lit by the scene's sun and sky, with glass and the sea blended over
what's behind them and the scene's fog.

    python Tools/stillhouse_preview.py <out dir> [view ...]     (the structure only; stillhouse_map --preview draws all)

A paint's colour is its texture's mean (Assets/materials/stillhouse/<paint>_color.png, then Railhead's, the building
materials and Belltower's), or a stand-in from STAND_INS while the materials haven't been drawn.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K

ROOT = Path( __file__ ).resolve().parent.parent
MATERIALS = ROOT / "Assets/materials/stillhouse"
RAILHEAD = ROOT / "Assets/materials/railhead"
BUILDINGS = ROOT / "Assets/materials/buildings"
BELLTOWER = ROOT / "Assets/materials/belltower"

SUN_PITCH, SUN_YAW = 27.0, -30.0


def sun_direction():
    """ Towards the sun, plan ( e, n, z ). The light points pitch down, yaw from north towards west. """
    p, y = math.radians( SUN_PITCH ), math.radians( SUN_YAW )
    world = np.array( ( math.cos( p ) * math.cos( y ), math.cos( p ) * math.sin( y ), -math.sin( p ) ) )
    return -np.array( ( -world[1], world[0], world[2] ) )


SUN = sun_direction()
SKY = ( np.array( ( 0.80, 0.84, 0.88 ) ), np.array( ( 0.40, 0.56, 0.80 ) ) )
FOG = np.array( ( 0.70, 0.76, 0.82 ) )
FOG_START, FOG_END, FOG_ALPHA = 4000.0, 80000.0, 0.7     # stillhouse_map's GradientFog

STAND_INS = {
    # Walls and roofs
    "sh_harl": ( 0.86, 0.86, 0.83 ), "sh_harl_shade": ( 0.74, 0.74, 0.71 ), "sh_harl_cream": ( 0.86, 0.82, 0.70 ),
    "sh_harl_mould": ( 0.62, 0.62, 0.60 ), "sh_whitewash": ( 0.80, 0.80, 0.77 ),
    "sh_tar_black": ( 0.07, 0.07, 0.07 ), "sh_rubble": ( 0.45, 0.43, 0.40 ), "sh_granite": ( 0.58, 0.55, 0.53 ),
    "sh_granite_weed": ( 0.22, 0.24, 0.17 ), "sh_slate_roof": ( 0.25, 0.27, 0.30 ), "sh_lead": ( 0.42, 0.44, 0.46 ),
    "sh_corrugated_red": ( 0.45, 0.17, 0.12 ), "sh_corrugated_green": ( 0.20, 0.32, 0.26 ),
    # Floors and ground
    "sh_setts": ( 0.42, 0.41, 0.40 ), "sh_tarmac": ( 0.24, 0.24, 0.25 ), "sh_concrete": ( 0.58, 0.57, 0.54 ),
    "sh_floor_tiles": ( 0.55, 0.25, 0.18 ), "sh_floorboards": ( 0.50, 0.38, 0.25 ), "sh_dunnage": ( 0.20, 0.18, 0.16 ),
    "sh_grating": ( 0.45, 0.46, 0.46 ), "sh_chequer": ( 0.50, 0.51, 0.51 ), "sh_sand": ( 0.76, 0.70, 0.58 ),
    "sh_shingle": ( 0.50, 0.48, 0.45 ), "sh_sand_wet": ( 0.48, 0.42, 0.34 ),
    "sh_wrack": ( 0.24, 0.20, 0.10 ), "sh_grass": ( 0.34, 0.42, 0.20 ), "sh_seabed": ( 0.28, 0.27, 0.22 ), "sh_seabed_deep": ( 0.08, 0.10, 0.09 ),
    "sh_kerb": ( 0.62, 0.60, 0.58 ), "sh_rock": ( 0.30, 0.29, 0.27 ), "sh_rock_weed": ( 0.22, 0.21, 0.15 ),
    # Metals
    "sh_copper_bright": ( 0.80, 0.45, 0.28 ), "sh_copper": ( 0.55, 0.30, 0.18 ), "sh_copper_green": ( 0.32, 0.52, 0.44 ),
    "sh_brass": ( 0.72, 0.58, 0.30 ), "sh_steel": ( 0.55, 0.56, 0.57 ), "sh_steel_green": ( 0.14, 0.30, 0.26 ),
    "sh_rust": ( 0.40, 0.22, 0.12 ), "sh_stainless": ( 0.70, 0.71, 0.72 ),
    # Wood
    "sh_pine": ( 0.62, 0.42, 0.24 ), "sh_cask_oak": ( 0.46, 0.33, 0.21 ), "sh_cask_dark": ( 0.30, 0.21, 0.14 ),
    "sh_hoop": ( 0.18, 0.18, 0.19 ), "sh_timber_tar": ( 0.09, 0.08, 0.07 ), "sh_planks_grey": ( 0.52, 0.50, 0.46 ),
    # Paints
    "sh_paint_door": ( 0.07, 0.25, 0.24 ), "sh_paint_white": ( 0.90, 0.90, 0.88 ), "sh_paint_black": ( 0.05, 0.05, 0.05 ),
    "sh_paint_red": ( 0.62, 0.10, 0.08 ), "sh_paint_yellow": ( 0.88, 0.70, 0.12 ), "sh_paint_orange": ( 0.90, 0.40, 0.08 ),
    "sh_paint_blue": ( 0.12, 0.24, 0.46 ),
    # Boats
    "sh_hull_blue": ( 0.10, 0.20, 0.40 ), "sh_hull_red": ( 0.50, 0.12, 0.09 ), "sh_hull_white": ( 0.85, 0.85, 0.82 ),
    "sh_hull_black": ( 0.06, 0.06, 0.06 ), "sh_deck": ( 0.48, 0.40, 0.30 ),
    # Goods and clutter
    "sh_peat": ( 0.20, 0.13, 0.08 ), "sh_malt": ( 0.72, 0.58, 0.34 ), "sh_sack": ( 0.55, 0.45, 0.30 ),
    "sh_rope": ( 0.62, 0.55, 0.40 ), "sh_net": ( 0.30, 0.45, 0.35 ), "sh_fishbox_blue": ( 0.15, 0.32, 0.62 ),
    "sh_fishbox_orange": ( 0.88, 0.42, 0.10 ), "sh_rubber": ( 0.07, 0.07, 0.07 ), "sh_tile_white": ( 0.88, 0.89, 0.87 ),
    "sh_window_dark": ( 0.10, 0.12, 0.14 ), "sh_canvas": ( 0.36, 0.40, 0.36 ), "sh_lamp_warm": ( 1.0, 0.86, 0.62 ), "sh_fire": ( 1.0, 0.45, 0.12 ),
    "sh_glass": ( 0.60, 0.70, 0.74 ), "sh_glass_dirty": ( 0.50, 0.52, 0.48 ), "sh_sea": ( 0.10, 0.20, 0.24 ),
    # Atlases (their mean is mostly the background)
    "sh_lettering": ( 0.06, 0.06, 0.06 ), "sh_signs": ( 0.85, 0.85, 0.82 ), "sh_cask_head": ( 0.45, 0.33, 0.22 ),
    # The land
    "sh_hill_grass": ( 0.36, 0.42, 0.22 ), "sh_heather": ( 0.30, 0.24, 0.22 ), "sh_bracken": ( 0.55, 0.35, 0.16 ),
    "sh_moor": ( 0.32, 0.29, 0.20 ), "sh_hill_rock": ( 0.40, 0.39, 0.37 ), "sh_field": ( 0.38, 0.50, 0.22 ),
    "sh_far_hills": ( 0.36, 0.38, 0.42 ), "sh_conifer": ( 0.12, 0.18, 0.12 ),
    # Shared with other maps
    "slate": ( 0.28, 0.30, 0.33 ), "corrugated": ( 0.48, 0.50, 0.50 ), "gravel": ( 0.55, 0.53, 0.50 ),
    "iron_black": ( 0.10, 0.10, 0.11 ), "setts": ( 0.45, 0.43, 0.41 ), "planks": ( 0.55, 0.42, 0.28 ),
}
GLOWING = { "sh_lamp_warm", "sh_fire", "rw_lamp_warm", "rw_lamp_cool" }
GLASS_PAINTS = { "sh_glass", "sh_glass_dirty", "rw_glass", "rw_glass_roof" }
SEA_PAINTS = { "sh_sea" }
_colours = {}


def is_glass( paint ):
    return paint in GLASS_PAINTS


def is_sea( paint ):
    return paint in SEA_PAINTS


def paint_colour( paint ):
    if paint not in _colours:
        for path in ( MATERIALS / f"{paint}_color.png", RAILHEAD / f"{paint}_color.png", BUILDINGS / f"{paint}_color.png",
                      BELLTOWER / f"{paint}_color.png" ):
            if path.exists():
                small = Image.open( path ).convert( "RGB" ).resize( ( 32, 32 ) )
                _colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
                break
        else:
            _colours[paint] = np.array( STAND_INS.get( paint, ( 1.0, 0.0, 1.0 ) ), float )
    return _colours[paint]


def triangles( models, glass=False, sea=False ):
    """ ( triangles ( T, 3, 3 ), normals, lit colours ) of the opaque paints, or with glass, of the glass, or with sea,
    of the sea. """
    tris, normals, colours = [], [], []
    for model in models:
        for paint, items in model.polygons.items():
            if is_glass( paint ) != glass or is_sea( paint ) != sea:
                continue
            base = paint_colour( paint )
            for points, normal in items:
                if paint in GLOWING or glass:
                    lit = base
                elif sea:
                    lit = base * 0.9 + SKY[1] * 0.25
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
    fog = ( FOG_ALPHA * np.clip( ( distance - FOG_START ) / ( FOG_END - FOG_START ), 0.0, 1.0 ) ** 1.5 )[:, None]
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


def perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=80.0, sea=None ):
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
    if sea is not None:
        simage, sdepth = np.zeros_like( image ), np.zeros_like( depth )
        rasterise( simage, sdepth, *project( sea, eye, right, up, forward, focal, width, height, both_sides=True ) )
        over = sdepth > depth
        # Clear in the shallows, darker as the bed falls away under it ( nearness is 1 / distance ).
        behind = np.where( over, 1.0 / np.maximum( depth, 1e-9 ) - 1.0 / np.maximum( sdepth, 1e-9 ), 0.0 )
        alpha = np.clip( 0.35 + behind / 400.0, 0.35, 0.85 )[..., None]
        image = np.where( over[..., None], image * ( 1 - alpha ) + simage * alpha, image )
        depth = np.where( over, sdepth, depth )
    gimage, gdepth = np.zeros_like( image ), np.zeros_like( depth )
    rasterise( gimage, gdepth, *project( glass, eye, right, up, forward, focal, width, height, both_sides=True ) )
    over = gdepth > depth
    image[over] = image[over] * 0.72 + gimage[over] * 0.28
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


def top_down( opaque, glass, bounds, scale, cut=None, sea=None ):
    """ Straight down: bounds ( e0, e1, n0, n1 ), scale units a pixel; cut leaves out everything higher. """
    e0, e1, n0, n1 = bounds
    width, height = int( ( e1 - e0 ) / scale ), int( ( n1 - n0 ) / scale )
    image = np.tile( np.array( ( 0.20, 0.22, 0.24 ) ), ( height, width, 1 ) )
    depth = np.full( ( height, width ), -1e9 )
    for data, tint in ( ( opaque, None ), ( sea, ( 0.10, 0.22, 0.27 ) ), ( glass, ( 0.35, 0.55, 0.62 ) ) ):
        if data is None:
            continue
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
    ( "brae", ( -2030, -1000, 64 ), ( -2030, 1400, 120 ), 80 ),
    ( "gate", ( -2060, -100, 64 ), ( -400, -100, 120 ), 80 ),
    ( "yard", ( -1850, 330, 64 ), ( -400, -300, 100 ), 85 ),
    ( "still_house", ( -380, -560, 64 ), ( 300, 200, 160 ), 90 ),
    ( "gallery", ( -330, 350, 112 ), ( 300, -450, 60 ), 90 ),
    ( "tun_room", ( -380, 1050, 112 ), ( 300, 450, 90 ), 90 ),
    ( "mash_house", ( 0, 1540, 112 ), ( 0, 1100, 100 ), 90 ),
    ( "road", ( -2030, 1430, 112 ), ( -400, 1650, 110 ), 80 ),
    ( "cask_yard", ( -1000, 1280, 112 ), ( -420, 900, 80 ), 85 ),
    ( "warehouse", ( -1860, 1000, 112 ), ( -900, 1150, 90 ), 85 ),
    ( "filling_store", ( -380, -620, 64 ), ( 300, -880, 30 ), 90 ),
    ( "pier_store", ( -380, -1000, 14 ), ( 300, -1300, 0 ), 90 ),
    ( "shore_walk", ( -1880, -1250, 14 ), ( -400, -1240, 30 ), 80 ),
    ( "beach", ( -2050, -1600, -90 ), ( 0, -1450, -100 ), 80 ),
    ( "pier", ( 0, -1900, 14 ), ( 0, -1000, 120 ), 80 ),
    ( "site_b", ( 1350, -1720, -95 ), ( 1050, -1350, -60 ), 85 ),
    ( "site_a", ( 840, 1280, 112 ), ( 480, 920, 60 ), 85 ),
    ( "sea_front", ( 0, -3200, 120 ), ( 0, -900, 160 ), 70 ),
    ( "aerial", ( -3600, -4400, 2600 ), ( 0, -100, 0 ), 70 ),
    ( "aerial_north", ( 2800, 3800, 2200 ), ( 0, -300, 100 ), 70 ),
]


TOP_BOUNDS = ( -2700, 2700, -2300, 2100 )


def write_previews( out_dir, models, views=None, top=True ):
    out = Path( out_dir )
    out.mkdir( parents=True, exist_ok=True )
    opaque, glass, sea = triangles( models ), triangles( models, glass=True ), triangles( models, sea=True )
    if top:
        top_down( opaque, glass, TOP_BOUNDS, 5, sea=sea ).save( out / "top.png" )
        top_down( opaque, glass, TOP_BOUNDS, 5, cut=200, sea=sea ).save( out / "top_ground.png" )
        print( f"wrote {out / 'top.png'}" )
    for name, eye, target, fov in VIEWS:
        if views and name not in views:
            continue
        perspective( opaque, glass, eye, target, fov=fov, sea=sea ).save( out / f"{name}.png" )
        print( f"wrote {out / name}.png" )


if __name__ == "__main__":
    import stillhouse_distillery as S

    write_previews( sys.argv[1], list( S.build().values() ), sys.argv[2:] or None )
