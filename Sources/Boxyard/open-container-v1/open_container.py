"""Boxyard open containers: detail model (Sources/Boxyard/open-container-v1, 2026-11-06).

Adds to the six open containers, on top of the generator's own drawing (nothing is removed, collision untouched):
  * corrugated inner walls: trapezoid ribs on both side walls and the front wall, ribbed ceiling bows, bottom and top rails;
  * plywood floor: cross-member lines, screw rows, and four lashing rings per side (plate + D-ring);
  * door leaves: pressed rib panels with a frame on both faces, and three hinge barrels with pins on each post.
Existing materials only (bx_container_inside atlas, bx_galv). Built in the generator's plan frame, so a ModelRenderer at
world (0,0,0) with no rotation puts it right. Three LODs, no physics.

Run:  python open_container.py [--write]
"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
sys.path.insert( 0, str( ROOT / "Sources/ReefHall/stairs-v1" ) )
import map_kit as K            # noqa: E402
import boxyard_map as B        # noqa: E402
import boxyard_materials as BM  # noqa: E402
import stairs as S             # noqa: E402

S.MODEL_RES = "models/props/boxyard/open_container_v1"
S.MODEL_DIR = ROOT / "Assets/models/props/boxyard/open_container_v1"
MODEL_DIR = S.MODEL_DIR
INS, GALV = "bx_container_inside", "bx_galv"
LODS = { 0: dict( step=1, screws=True, rings=True, hinges=True ), 1: dict( step=2, screws=False, rings=True, hinges=True ),
         2: dict( step=4, screws=False, rings=False, hinges=False ) }


def wall_uv( name="wall", s=0.5, t=0.5 ):
    return B.inside_uv( name, s, t )


class Detail:
    def __init__( self, m, F, leaves, cfg ):
        self.m, self.F, self.leaves, self.cfg = m, F, leaves, cfg
        self.zf, self.zc = BM.FLOOR, B.CEILING
        self.xi, self.yi = B.INSIDE_X, B.INSIDE_Y

    def q( self, pts, towards, region="wall" ):
        u = wall_uv( region )
        self.F.quad( self.m, INS, pts, towards, uv=[ u ] * len( pts ) )

    def world_quad( self, paint, pts, towards, uv ):
        from boxyard_map import card
        w = [ self.F.p( *p ) for p in pts ]
        card( self.m, paint, w, self.F.v( *towards ), uv=[ uv ] * len( w ) )

    def rib_x( self, y, sigma, x, w0=2.6, w1=1.5, h=0.9, z0=None, z1=None ):
        """ A trapezoid rib on a side wall (inner face at y = sigma * yi) running up the wall at x. """
        z0 = self.zf + 0.4 if z0 is None else z0
        z1 = self.zc - 0.4 if z1 is None else z1
        yo, yt = y, y - sigma * h
        a = [ ( x - w0, yo, -1.0 ), ( x - w1, yt, 0.0 ), ( x + w1, yt, 1.0 ), ( x + w0, yo, 9.0 ) ]
        for ( xa, ya, _ ), ( xb, yb, sx ) in zip( a[:-1], a[1:] ):
            sx = { 0.0: -0.7 if xb < x else 0.0, 1.0: 0.0, 9.0: 0.7 }[sx] if False else ( 0.0 if ya == yb else ( -0.7 if xb < x else 0.7 ) )
            self.q( [ ( xa, ya, z0 ), ( xb, yb, z0 ), ( xb, yb, z1 ), ( xa, ya, z1 ) ], ( sx, -sigma, 0.0 ) )

    def walls( self ):
        step = 10.0 * self.cfg["step"]
        n = int( ( 2 * self.xi - 14.0 ) / step )
        xs = [ -self.xi + 8.0 + k * step for k in range( n + 1 ) ]
        for sigma in ( -1, 1 ):
            for x in xs:
                self.rib_x( sigma * self.yi, sigma, x )
        # the front (closed) end wall: ribs across it, facing the door
        ys = [ -self.yi + 6.0 + k * step for k in range( int( ( 2 * self.yi - 12.0 ) / step ) + 1 ) ]
        for y in ys:
            xo, xt = -self.xi, -self.xi + 0.9
            for ( ya, xa ), ( yb, xb ) in ( ( ( y - 2.6, xo ), ( y - 1.5, xt ) ), ( ( y - 1.5, xt ), ( y + 1.5, xt ) ), ( ( y + 1.5, xt ), ( y + 2.6, xo ) ) ):
                self.q( [ ( xa, ya, self.zf + 0.4 ), ( xb, yb, self.zf + 0.4 ), ( xb, yb, self.zc - 0.4 ), ( xa, ya, self.zc - 0.4 ) ], ( 1.0, 0.0, 0.0 ) )
        for sigma in ( -1, 1 ):          # bottom rail (a galvanised angle) and top rail along each wall
            y0, y1 = sorted( ( sigma * self.yi, sigma * ( self.yi - 1.6 ) ) )
            self.F.box( self.m, -self.xi, self.xi, y0, y1, self.zf, self.zf + 3.4, { "default": GALV } )
            self.F.box( self.m, -self.xi, self.xi, y0, y1, self.zc - 2.6, self.zc, { "default": GALV } )

    def ceiling( self ):
        step = 24.0 * self.cfg["step"]
        for k in range( int( ( 2 * self.xi - 10.0 ) / step ) + 1 ):
            x = -self.xi + 6.0 + k * step
            self.F.box( self.m, x - 1.6, x + 1.6, -self.yi, self.yi, self.zc - 1.5, self.zc, { "default": GALV } )

    def extras( self ):
        F, m, zf, zc, xi, yi = self.F, self.m, self.zf, self.zc, self.xi, self.yi
        step = 8.0 * self.cfg["step"]
        # ceiling corrugation: shallow trapezoid ribs running the length, between the bows
        y = -yi + 5.0
        while y < yi - 4.0:
            for xa, xb in ( ( -xi + 2.0, xi - 2.0 ), ):
                pts = [ ( y - 2.2, zc ), ( y - 1.2, zc - 0.7 ), ( y + 1.2, zc - 0.7 ), ( y + 2.2, zc ) ]
                for ( ya, za ), ( yb, zb ) in zip( pts[:-1], pts[1:] ):
                    self.q( [ ( xa, ya, za ), ( xb, ya, za ), ( xb, yb, zb ), ( xa, yb, zb ) ], ( 0.0, 0.5 * ( 1 if yb < ya else -1 ) if za != zb else 0.0, -1.0 ) )
            y += step
        # door sill: a steel tread plate across the opening, and corner castings at the four inside corners of the door frame
        F.box( m, xi - 4.5, xi + 1.2, -B.DOOR_Y, B.DOOR_Y, zf, zf + 0.9, { "default": GALV } )
        for sy in ( -1, 1 ):
            for z0, z1 in ( ( zf, zf + 5.5 ), ( zc - 5.5, zc ) ):
                y0, y1 = sorted( ( sy * ( B.DOOR_Y + 1.0 ), sy * ( yi - 0.4 ) ) )
                F.box( m, xi - 5.0, xi + 0.4, y0, y1, z0, z1, { "default": GALV } )
        # door gasket: a dark strip down both posts and along the header on the frame's inner face
        if self.cfg["rings"]:
            for sy in ( -1, 1 ):
                F.box( m, xi - 0.9, xi + 0.3, sy * B.DOOR_Y - 0.5, sy * B.DOOR_Y + 0.5, BM.DOOR_SILL, BM.DOOR_HEADER, { "default": GALV } )
            F.box( m, xi - 0.9, xi + 0.3, -B.DOOR_Y, B.DOOR_Y, BM.DOOR_HEADER - 0.5, BM.DOOR_HEADER + 0.5, { "default": GALV } )
            # two louvred vents high on the rear of each side wall
            for sy in ( -1, 1 ):
                for x in ( -xi + 16.0, -xi + 34.0 ):
                    yw = sy * yi
                    for k in range( 4 ):
                        z = zc - 9.0 + k * 1.8
                        y0, y1 = sorted( ( yw, yw - sy * 1.1 ) )
                        F.box( m, x - 3.5, x + 3.5, y0, y1, z, z + 0.7, { "default": GALV } )

    def floor( self ):
        zf = self.zf
        for k in range( int( ( 2 * self.xi - 6.0 ) / 12.0 ) + 1 ):          # cross-member lines under the plywood: raised seams
            x = -self.xi + 3.0 + k * 12.0
            self.F.box( self.m, x - 0.35, x + 0.35, -self.yi + 2.0, self.yi - 2.0, zf, zf + 0.12, { "default": GALV } )
            if self.cfg["screws"]:
                for y in ( -self.yi + 5.5, -self.yi + 7.5, self.yi - 7.5, self.yi - 5.5 ):
                    self.F.box( self.m, x - 1.2, x - 0.4, y - 0.4, y + 0.4, zf, zf + 0.15, { "default": GALV } )
        if self.cfg["rings"]:
            for sigma in ( -1, 1 ):
                for x in ( -self.xi + 22.0, -self.xi + 78.0, self.xi - 78.0, self.xi - 22.0 ):
                    yw = sigma * ( self.yi - 1.6 )
                    self.F.box( self.m, x - 2.2, x + 2.2, min( yw, yw - sigma * 0.6 ), max( yw, yw - sigma * 0.6 ), self.zf + 8.0, self.zf + 12.0, { "default": GALV } )
                    c = ( x, yw - sigma * 0.6, self.zf + 10.0 )
                    for a in range( 6 ):
                        t0, t1 = math.pi * a / 6 + 0.0, math.pi * ( a + 1 ) / 6
                        p0 = ( x + 2.0 * math.cos( t0 ), c[1] - sigma * 1.8 * math.sin( t0 ), c[2] + 0.2 * 0 )
                        p1 = ( x + 2.0 * math.cos( t1 ), c[1] - sigma * 1.8 * math.sin( t1 ), c[2] )
                        self.F.rod( self.m, p0, p1, 0.35, GALV, sides=5 )

    def leaf( self, sigma, alpha ):
        t = math.radians( alpha )
        hinge = np.array( ( B.HL + 0.5, sigma * 41.5 ) )
        d = np.array( ( math.sin( t ), -sigma * math.cos( t ) ) )
        nv = np.array( ( math.cos( t ), sigma * math.sin( t ) ) )
        zs, zh = BM.DOOR_SILL, BM.DOOR_HEADER
        a0, a1, thick = 0.5, 41.1, 1.6

        def P( a, b, z ):
            xy = hinge + a * d - b * nv
            return ( xy[0], xy[1], z )
        h = 0.8

        def prism( a_lo, a_hi, z0, z1, b0, bp, bev, paint, uv ):
            """ A bevelled bar standing proud of the leaf: base rect at b0, top rect inset by bev at bp. """
            base = [ ( a_lo, z0 ), ( a_hi, z0 ), ( a_hi, z1 ), ( a_lo, z1 ) ]
            top = [ ( a_lo + bev, z0 + bev ), ( a_hi - bev, z0 + bev ), ( a_hi - bev, z1 - bev ), ( a_lo + bev, z1 - bev ) ]
            for i in range( 4 ):
                j = ( i + 1 ) % 4
                quad = [ P( *base[i][:1], b0, base[i][1] ), P( base[j][0], b0, base[j][1] ), P( top[j][0], bp, top[j][1] ), P( top[i][0], bp, top[i][1] ) ]
                mid = np.mean( [ q for q in quad ], axis=0 )
                cen = np.array( P( ( a_lo + a_hi ) / 2, ( b0 + bp ) / 2, ( z0 + z1 ) / 2 ) )
                self.world_quad( paint, quad, mid - cen, uv )
            self.world_quad( paint, [ P( top[0][0], bp, top[0][1] ), P( top[1][0], bp, top[1][1] ), P( top[2][0], bp, top[2][1] ), P( top[3][0], bp, top[3][1] ) ],
                             np.array( ( nvv[0], nvv[1], 0.0 ) ), uv )
        for side, b0, s_dir in ( ( "in", thick, 1.0 ), ( "out", 0.0, -1.0 ) ):
            bp = b0 + s_dir * h
            nvv = -nv if side == "in" else nv
            paint = INS if side == "in" else self.paint
            uv = wall_uv( "doors" ) if side == "in" else B.doors_uv( 0.0, 50.0 )
            mid_z = ( zs + zh ) / 2
            for z0, z1 in ( ( zs + 0.8, zs + 4.6 ), ( zh - 4.6, zh - 0.8 ), ( mid_z - 1.8, mid_z + 1.8 ) ):
                prism( a0 + 0.6, a1 - 0.6, z0, z1, b0, bp, 0.8, paint, uv )
            for a_ in ( a0 + 0.6, a1 - 4.4 ):
                prism( a_, a_ + 3.8, zs + 0.8, zh - 0.8, b0, bp, 0.8, paint, uv )
            ra = a0 + 8.0
            while ra < a1 - 8.0:
                for z0, z1 in ( ( zs + 6.0, mid_z - 3.0 ), ( mid_z + 3.0, zh - 6.0 ) ):
                    prism( ra - 1.5, ra + 1.5, z0, z1, b0, bp, 0.9, paint, uv )
                ra += 4.6 * self.cfg["step"]
        if self.cfg["hinges"]:
            hp = self.F.p( hinge[0], hinge[1], 0.0 )
            for z in ( zs + 8.0, ( zs + zh ) / 2, zh - 12.0 ):
                self.m.cylinder( ( hp[0], hp[1] ), 1.5, z - 3.5, z + 3.5, { "side": GALV, "top": GALV, "bottom": GALV }, sides=8 )

    def build( self ):
        self.walls()
        self.ceiling()
        self.floor()
        self.extras()
        for sigma, alpha in zip( ( -1, 1 ), self.leaves ):
            self.leaf( sigma, alpha )


def build_model( lod ):
    m = K.Model()
    for name, e, n, heading, colour, is_open, on_top, leaves in B.CONTAINERS:
        if not is_open:
            continue
        F = B.Frame( e, n, heading )
        d = Detail( m, F, leaves, LODS[lod] )
        d.paint = B.paint_for( colour, e, n )
        d.build()
    m.uv_source_name = "open_container"
    B.configure( m )
    return m


def build_all( write=False ):
    stats, files, paints, first = {}, [], set(), None
    for lod in ( 0, 1, 2 ):
        model = build_model( lod )
        first = first or model
        paints |= set( model.polygons )
        obj = f"open_container_lod{lod}"
        if write:
            MODEL_DIR.mkdir( parents=True, exist_ok=True )
            tris = K.write_obj( MODEL_DIR / f"{obj}.obj", model, obj )
            S.weld_obj( MODEL_DIR / f"{obj}.obj" )
        else:
            tris = S.tri_count( model )
        files.append( f"{obj}.obj" )
        stats[lod] = { "triangles": tris, "degenerate": S.degenerate( model ) }
    if write:
        S.write_vmdl( MODEL_DIR / "open_container.vmdl", files, paints, first )
    return stats


if __name__ == "__main__":
    print( build_all( write="--write" in sys.argv ) )
