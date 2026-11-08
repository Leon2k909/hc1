"""A quick software preview of a stair model, for checking geometry offline (winding, normals, proportions, holes).

This is NOT the review picture: the before/after evidence is captured from the real editor viewport (see README). It draws
the K.Model's triangles with flat Lambert shading, a z-buffer and back-face culling, so a face wound the wrong way shows up
as a hole. Glass is blended over what is behind it.

    python preview.py <variant> <lod> <out-stem> <view> [<view> ...]
views: foot, side, top, head, nose, rail, under, lowrail
The model's frame: origin at the foot's centre, x across, y up the flight, z up from the floor.
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import stairs as S  # noqa: E402

COLOURS = { "rh_floor": ( 130, 140, 156 ), "rh_wall_dark": ( 96, 102, 114 ), "rh_gunmetal": ( 74, 82, 96 ), "rh_brass": ( 214, 170, 76 ),
            "rh_steel": ( 176, 182, 192 ), "rh_black": ( 22, 23, 26 ), "rh_glass": ( 150, 205, 225 ) }
VIEWS = {
    # name: ( eye, target, fov )
    "foot": ( np.array( ( 30.0, -170.0, 64.0 ) ), np.array( ( 0.0, 120.0, 110.0 ) ), 70 ),
    "side": ( np.array( ( -330.0, 120.0, 90.0 ) ), np.array( ( 0.0, 140.0, 90.0 ) ), 55 ),
    "top": ( np.array( ( 0.0, 140.0, 520.0 ) ), np.array( ( 0.0, 140.0, 0.0 ) ), 60 ),
    "head": ( np.array( ( 60.0, 420.0, 250.0 ) ), np.array( ( 0.0, 200.0, 120.0 ) ), 70 ),
    "nose": ( np.array( ( 24.0, -26.0, 22.0 ) ), np.array( ( 0.0, 30.0, 14.0 ) ), 60 ),
    "rail": ( np.array( ( 30.0, 60.0, 110.0 ) ), np.array( ( -80.0, 130.0, 80.0 ) ), 62 ),
    "under": ( np.array( ( 0.0, -140.0, 6.0 ) ), np.array( ( 0.0, 100.0, 70.0 ) ), 75 ),
    "lowrail": ( np.array( ( -40.0, -30.0, 40.0 ) ), np.array( ( -86.0, 20.0, 30.0 ) ), 60 ),
}


def camera_basis( eye, target ):
    f = target - eye
    f = f / np.linalg.norm( f )
    r = np.cross( f, np.array( ( 0.0, 0.0, 1.0 ) ) )
    if np.linalg.norm( r ) < 1e-6:
        r = np.array( ( 1.0, 0.0, 0.0 ) )
    r = r / np.linalg.norm( r )
    u = np.cross( r, f )
    return f, r, u


def render( model, view, size=( 1100, 700 ) ):
    eye, target, fov = VIEWS[view]
    f, r, u = camera_basis( eye, target )
    w, h = size
    focal = ( w / 2 ) / math.tan( math.radians( fov ) / 2 )
    zbuf = np.full( ( h, w ), 1e18 )
    img = np.zeros( ( h, w, 3 ), float )
    img[:] = ( 118, 128, 140 )
    sky = np.array( ( 0.3, 0.2, 0.9 ) )
    sky = sky / np.linalg.norm( sky )
    count = 0
    order = sorted( model.polygons, key=lambda p: p == "rh_glass" )          # glass last
    for paint in order:
        polys = model.polygons[paint]
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
                if z.min() < 1.0:
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
                colour = np.clip( col * lam[..., None], 0, 255 )
                sub = img[y0:y1 + 1, x0:x1 + 1]
                if paint == "rh_glass":
                    sub[win] = 0.62 * sub[win] + 0.38 * colour[win]            # see-through: no depth write
                else:
                    sub[win] = colour[win]
                    zbuf[y0:y1 + 1, x0:x1 + 1][win] = depth[win]
                count += 1
    return Image.fromarray( img.astype( np.uint8 ) ), count


if __name__ == "__main__":
    variant, lod, stem = sys.argv[1], int( sys.argv[2] ), Path( sys.argv[3] )
    model = S.Flight( variant, lod=lod, **S.VARIANTS[variant] ).build( turn=False )          # the drawing's own frame (x across, y up)
    stem.parent.mkdir( parents=True, exist_ok=True )
    for view in sys.argv[4:]:
        img, n = render( model, view )
        path = stem.parent / f"{stem.name}_{view}.png"
        img.save( path )
        print( view, "triangles drawn", n, "->", path )
