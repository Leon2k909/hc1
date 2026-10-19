""" Renders the forecourt flags (cerroblanco_fitout.flagpole) textured, from the forecourt (north) and from the south,
with the OBJ's UV convention (v = 0 at the image's foot) and backface culling, to check the picture reads right. """
import sys, math
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert( 0, str( ROOT / "Tools" ) )
import map_kit as K
import cerroblanco_fitout as F
fine, solid = K.Model(), K.Model()
for k, e in enumerate( ( 420.0, 500.0, 580.0 ) ):
    F.flagpole( fine, solid, e, 2330.0, k )
tex = { k: np.asarray( Image.open( ROOT / f"Assets/materials/cerroblanco/banner_{k}_color.png" ).convert( "RGB" ), float ) / 255 for k in range( 3 ) }
tris = []
for model in ( fine, solid ):
    for paint, items in model.polygons.items():
        for index, ( points, normal ) in enumerate( items ):
            uv = model.polygon_uvs.get( ( paint, index ) )
            for j in range( 1, len( points ) - 1 ):
                t = [ 0, j, j + 1 ]
                vn = model.polygon_normals.get( ( paint, index ) )
                tris.append( ( paint, [ np.asarray( points[q], float ) for q in t ], [ uv[q] for q in t ] if uv else None, np.asarray( normal, float ), [ np.asarray( vn[q] ) for q in t ] if vn else None ) )
def render( eye, target, fov, size, out ):
    W, H = size
    eye, target = np.array( eye, float ), np.array( target, float )
    fwd = target - eye; fwd /= np.linalg.norm( fwd )
    right = np.cross( fwd, ( 0, 0, 1 ) ); right /= np.linalg.norm( right )
    up = np.cross( right, fwd )
    f = ( W / 2 ) / math.tan( math.radians( fov ) / 2 )
    img = np.ones( ( H, W, 3 ) ) * np.array( ( .55, .7, .85 ) )
    zb = np.full( ( H, W ), np.inf )
    for paint, pts, uv, normal, vns in tris:
        # backface culling: the polygon's own normal must face the eye
        if np.dot( normal, eye - pts[0] ) <= 0:
            continue
        P = []
        for p in pts:
            d = p - eye
            z = np.dot( d, fwd )
            if z < 1: break
            P.append( ( W / 2 + f * np.dot( d, right ) / z, H / 2 - f * np.dot( d, up ) / z, z ) )
        if len( P ) < 3: continue
        P = np.array( P )
        x0, x1 = int( max( 0, P[:, 0].min() ) ), int( min( W - 1, P[:, 0].max() + 1 ) )
        y0, y1 = int( max( 0, P[:, 1].min() ) ), int( min( H - 1, P[:, 1].max() + 1 ) )
        if x0 > x1 or y0 > y1: continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        a, b, c = P[0], P[1], P[2]
        den = ( b[1] - c[1] ) * ( a[0] - c[0] ) + ( c[0] - b[0] ) * ( a[1] - c[1] )
        if abs( den ) < 1e-9: continue
        w0 = ( ( b[1] - c[1] ) * ( xs - c[0] ) + ( c[0] - b[0] ) * ( ys - c[1] ) ) / den
        w1 = ( ( c[1] - a[1] ) * ( xs - c[0] ) + ( a[0] - c[0] ) * ( ys - c[1] ) ) / den
        w2 = 1 - w0 - w1
        inside = ( w0 >= 0 ) & ( w1 >= 0 ) & ( w2 >= 0 )
        if not inside.any(): continue
        iz = w0 / a[2] + w1 / b[2] + w2 / c[2]
        z = 1 / np.maximum( iz, 1e-9 )
        m = inside & ( z < zb[y0:y1 + 1, x0:x1 + 1] )
        if not m.any(): continue
        sun = np.array( ( .5, .55, .67 ) ); sun /= np.linalg.norm( sun )
        if vns:
            nn = ( w0[..., None] * vns[0] / a[2] + w1[..., None] * vns[1] / b[2] + w2[..., None] * vns[2] / c[2] ) * z[..., None]
            nn /= np.linalg.norm( nn, axis=-1, keepdims=True )
            shade = ( .35 + .65 * np.clip( nn @ sun, 0, 1 ) )[..., None]
        else:
            shade = .35 + .65 * max( 0, float( np.dot( normal, sun ) ) )
        if uv and paint.startswith( "cb_banner_" ):
            t = tex[int( paint[-1] )]
            u = ( w0 * uv[0][0] / a[2] + w1 * uv[1][0] / b[2] + w2 * uv[2][0] / c[2] ) * z
            v = ( w0 * uv[0][1] / a[2] + w1 * uv[1][1] / b[2] + w2 * uv[2][1] / c[2] ) * z
            px = np.clip( ( u * t.shape[1] ).astype( int ), 0, t.shape[1] - 1 )
            py = np.clip( ( ( 1 - v ) * t.shape[0] ).astype( int ), 0, t.shape[0] - 1 )
            col = t[py, px] * shade
        else:
            col = np.broadcast_to( np.array( ( .8, .8, .82 ) ) * shade, ( *m.shape, 3 ) ) if np.ndim( shade ) == 0 else np.array( ( .8, .8, .82 ) ) * shade
        sub = img[y0:y1 + 1, x0:x1 + 1]
        sub[m] = col[m]
        zb[y0:y1 + 1, x0:x1 + 1][m] = z[m]
    Image.fromarray( ( np.clip( img, 0, 1 ) * 255 ).astype( np.uint8 ) ).save( out )
render( ( 500, 2700, 260 ), ( 500, 2330, 300 ), 45, ( 640, 480 ), HERE / "flags_from_north_smooth.png" )
render( ( 500, 1960, 260 ), ( 500, 2330, 300 ), 45, ( 640, 480 ), HERE / "flags_from_south_smooth.png" )
render( ( 470, 2345, 356 ), ( 476, 2330, 345 ), 50, ( 480, 480 ), HERE / "flag_top_close.png" )
render( ( 520, 2360, 30 ), ( 500, 2330, 2 ), 50, ( 480, 480 ), HERE / "flag_base_close.png" )
for t in range( 3 ):
    Image.fromarray( ( tex[t] * 255 ).astype( np.uint8 ) ).resize( ( 128, 384 ) ).save( HERE / f"banner_{t}_texture.png" )
print( "ok" )
