"""A quick software preview of the desk model, for checking geometry offline (winding, normals, proportions).

This is NOT the review picture: the before/after evidence is captured from the real editor viewport (see README). It draws
the K.Model's triangles with flat Lambert shading and a painter's sort, and culls the faces that look away from the
camera, so a face wound the wrong way shows up as a hole.

    python preview.py <lod> <name> <view> [<view> ...]      views: public, staff, far, top, end, monitor, keys
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import desk as D  # noqa: E402

COLOURS = {
    "rd_precast": ( 150, 154, 160 ), "rd_top": ( 56, 60, 70 ), "rh_black": ( 18, 19, 22 ), "rh_gunmetal": ( 86, 92, 104 ),
    "rh_steel": ( 110, 118, 132 ), "rh_led_warm": ( 255, 190, 110 ), "rh_screen_data": ( 70, 200, 190 ), "rh_pad_dark": ( 40, 42, 46 ),
    "rh_monitor_graphite": ( 77, 82, 87 ), "rh_monitor_trim": ( 43, 48, 54 ), "rh_monitor_recess": ( 11, 13, 15 ),
    "rh_monitor_aluminium": ( 173, 178, 184 ), "rh_monitor_label": ( 94, 102, 107 ), "rh_monitor_ink": ( 31, 36, 38 ),
    "rh_console_bezel": ( 26, 31, 33 ), "rh_console_edge": ( 74, 84, 87 ), "rh_console_keys": ( 153, 161, 158 ),
    "rh_console_status": ( 38, 107, 79 ),
}

VIEWS = {
    # name: ( eye, target, fov ), eye and target as D.pt( angle, radius, height ) round the tank's centre
    "public": ( D.pt( -12, 330, 64 ), D.pt( 0, 250, 30 ), 75 ),
    "public2": ( D.pt( -42, 340, 60 ), D.pt( -30, 235, 40 ), 80 ),
    "staff": ( D.pt( 8, 130, 62 ), D.pt( 0, 228, 50 ), 75 ),
    "far": ( D.pt( -38, 700, 64 ), D.pt( 0, 235, 30 ), 55 ),
    "top": ( D.pt( 0, 500, 640 ), D.pt( 0, 232, 0 ), 70 ),
    "end": ( D.pt( 80, 300, 40 ), D.pt( 62, 232, 28 ), 70 ),
    "back": ( D.pt( 10, 290, 58 ), D.pt( 0, 232, 52 ), 60 ),
    "monitor": ( D.pt( 0, 176, 60 ), D.pt( 0, 224, 48 ), 62 ),
    "keys": ( D.pt( 0, 192, 56 ), D.pt( 0, 222, 44 ), 50 ),
    "low": ( D.pt( -8, 300, 18 ), D.pt( 0, 250, 14 ), 70 ),
}


def camera_basis( eye, target ):
    f = target - eye
    f = f / np.linalg.norm( f )
    r = np.cross( f, np.array( ( 0.0, 0.0, 1.0 ) ) )
    r = r / np.linalg.norm( r )
    u = np.cross( r, f )
    return f, r, u


def render( model, view, size=( 1100, 700 ), shade=True ):
    """ A z-buffered render: perspective-correct depth and normals, Lambert plus a sky term, back faces culled. """
    eye, target, fov = VIEWS[view]
    f, r, u = camera_basis( eye, target )
    w, h = size
    focal = ( w / 2 ) / math.tan( math.radians( fov ) / 2 )
    zbuf = np.full( ( h, w ), 1e18 )
    img = np.zeros( ( h, w, 3 ), float )
    img[:] = ( 120, 150, 170 )
    sky = np.array( ( 0.3, 0.2, 0.9 ) )
    sky = sky / np.linalg.norm( sky )
    count = 0
    for paint, polys in model.polygons.items():
        col = np.array( COLOURS.get( paint, ( 200, 0, 200 ) ), float )
        for index, ( pts, normal ) in enumerate( polys ):
            smooth = model.polygon_normals.get( ( paint, index ) )
            for k in range( 1, len( pts ) - 1 ):
                tri = [ pts[0], pts[k], pts[k + 1] ]
                n_geo = np.cross( tri[1] - tri[0], tri[2] - tri[0] )
                ln = np.linalg.norm( n_geo )
                if ln < 1e-9:
                    continue
                n_geo = n_geo / ln
                if float( np.dot( n_geo, ( tri[0] + tri[1] + tri[2] ) / 3 - eye ) ) > 0:
                    continue
                nv = [ n_geo ] * 3 if smooth is None else [ smooth[0], smooth[k], smooth[k + 1] ]
                cam = [ p - eye for p in tri ]
                z = np.array( [ float( np.dot( c, f ) ) for c in cam ] )
                if z.min() < 2.0:
                    continue
                sx = np.array( [ w / 2 + focal * float( np.dot( c, r ) ) / zz for c, zz in zip( cam, z ) ] )
                sy = np.array( [ h / 2 - focal * float( np.dot( c, u ) ) / zz for c, zz in zip( cam, z ) ] )
                x0, x1 = int( max( 0, math.floor( sx.min() ) ) ), int( min( w - 1, math.ceil( sx.max() ) ) )
                y0, y1 = int( max( 0, math.floor( sy.min() ) ) ), int( min( h - 1, math.ceil( sy.max() ) ) )
                if x1 < x0 or y1 < y0:
                    continue
                den = ( sy[1] - sy[2] ) * ( sx[0] - sx[2] ) + ( sx[2] - sx[1] ) * ( sy[0] - sy[2] )
                if abs( den ) < 1e-9:
                    continue
                X, Y = np.meshgrid( np.arange( x0, x1 + 1 ) + 0.5, np.arange( y0, y1 + 1 ) + 0.5 )
                l0 = ( ( sy[1] - sy[2] ) * ( X - sx[2] ) + ( sx[2] - sx[1] ) * ( Y - sy[2] ) ) / den
                l1 = ( ( sy[2] - sy[0] ) * ( X - sx[2] ) + ( sx[0] - sx[2] ) * ( Y - sy[2] ) ) / den
                l2 = 1 - l0 - l1
                inside = ( l0 >= -1e-6 ) & ( l1 >= -1e-6 ) & ( l2 >= -1e-6 )
                if not inside.any():
                    continue
                iz = l0 / z[0] + l1 / z[1] + l2 / z[2]
                depth = 1.0 / np.maximum( iz, 1e-12 )
                win = inside & ( depth < zbuf[y0:y1 + 1, x0:x1 + 1] )
                if not win.any():
                    continue
                p0, p1, p2 = ( l0 / z[0] ) * depth, ( l1 / z[1] ) * depth, ( l2 / z[2] ) * depth
                nn = p0[..., None] * nv[0] + p1[..., None] * nv[1] + p2[..., None] * nv[2]
                nn = nn / np.maximum( np.linalg.norm( nn, axis=-1, keepdims=True ), 1e-9 )
                pos = p0[..., None] * tri[0] + p1[..., None] * tri[1] + p2[..., None] * tri[2]
                vd = eye - pos
                vd = vd / np.maximum( np.linalg.norm( vd, axis=-1, keepdims=True ), 1e-9 )
                lam = 0.22 + 0.5 * np.clip( ( nn * vd ).sum( -1 ), 0, 1 ) + 0.35 * np.clip( ( nn * sky ).sum( -1 ), 0, 1 )
                colour = np.clip( col * lam[..., None], 0, 255 ) if shade else col
                sub = img[y0:y1 + 1, x0:x1 + 1]
                sub[win] = colour[win]
                zbuf[y0:y1 + 1, x0:x1 + 1][win] = depth[win]
                count += 1
    return Image.fromarray( img.astype( np.uint8 ) ), 0, count


if __name__ == "__main__":
    lod = int( sys.argv[1] )
    name = sys.argv[2]
    model = D.Desk( lod ).build()
    out = Path( name )
    for view in sys.argv[3:]:
        img, back, n = render( model, view )
        path = out.parent / f"{out.stem}_{view}.png"
        img.save( path )
        print( view, "triangles drawn", n, "red (facing away):", back, "->", path )
