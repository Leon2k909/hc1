"""Reef Hall's two filter-hall steel stairs as standalone models (Sources/ReefHall/filter-stairs-v1, 2026-11-06).

Old (Tools/reefhall_map.py metal_stair + stair_rail): 26 slats 2 in thick (grate on top) between two big plain blue beams,
and a rail of 2.4 in square posts every 60 in with one 8-sided tube. New: the same flights (same footprints, same 26 risers of
8 in, same collision), as a real open steel stair:

  * two channel stringers (2.5 in web, 12 in deep, a bottom flange turned inwards) following the nose line;
  * grating treads with a gunmetal anti-slip nosing bar, a front edge angle and an under-tread support angle;
  * a post-and-tube handrail (round posts with base plates, a 2 in handrail with domed ends, a midrail, a toe board) on the
    sides the old rail had: both sides of the east flight, the east side only of the north flight.

Existing Reef Hall materials only (rh_grate, rh_gunmetal, rh_steel, rh_steel_blue). Models are drawn in the generator's plan
frame, so a ModelRenderer at world (0,0,0) with no rotation puts them right. Three LODs each, no physics.

Run:  python filter_stairs.py [--write]
"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
HERE = Path( __file__ ).resolve().parent
sys.path.insert( 0, str( HERE.parent / "stairs-v1" ) )
import map_kit as K          # noqa: E402
import riverdale_parts as P  # noqa: E402
import reefhall_map as R     # noqa: E402
import stairs as S           # noqa: E402

MODEL_DIR = S.MODEL_DIR
STEPS, H = 26, 208.0
GRATE, GUN, STEEL, BLUE = "rh_grate", "rh_gunmetal", "rh_steel", "rh_steel_blue"
WEB, DEPTH, LIP_W, LIP_T = 2.5, 12.0, 4.0, 0.8
TREAD_T, GAP = 1.5, 0.4
RAIL_Z, MID_Z, POST_R, RAIL_R, MID_R = 38.0, 20.0, 1.0, 1.0, 0.6
LODS = {
    0: dict( post_every=3, rail_sides=10, post_sides=10, mid=True, angles=True, toe=True, dome=3 ),
    1: dict( post_every=4, rail_sides=8, post_sides=6, mid=True, angles=False, toe=False, dome=0 ),
    2: dict( post_every=8, rail_sides=6, post_sides=4, mid=False, angles=False, toe=False, dome=0 ),
}
FLIGHTS = {                     # name: ( lo, hi, climb, rails on ( lower, higher ) across the flight )
    "filter_stair_a": ( *R.FILTER_STAIRS[0], ( True, True ) ),
    "filter_stair_b": ( *R.FILTER_STAIRS[1], ( False, True ) ),
}


class Flight:
    def __init__( self, name, lo, hi, climb, rails, lod ):
        self.name, self.lod, self.cfg, self.rails = name, lod, LODS[lod], rails
        self.axis = 0 if climb[1] == "e" else 1
        self.other = 1 - self.axis
        self.a0, self.a1 = lo[self.axis], hi[self.axis]
        self.o0, self.o1 = lo[self.other], hi[self.other]
        self.run = ( self.a1 - self.a0 ) / STEPS
        self.h = H / STEPS
        self.m = K.Model()

    def pt( self, a, o, z ):
        return np.array( ( a, o, z ) if self.axis == 0 else ( o, a, z ), float )

    def vec( self, a, o ):
        return np.array( ( a, o, 0.0 ) if self.axis == 0 else ( o, a, 0.0 ), float )

    def A( self, j ):
        return self.a0 + j * self.run

    def zs( self, j ):
        """ The nose line: each tread's top at its front edge, level over the last tread. """
        return min( ( j + 1.0 ) * self.h, H )

    def card( self, paint, pts, towards ):
        P.card( self.m, paint, pts, np.asarray( towards, float ) )

    def box( self, a0, a1, o0, o1, z0, z1, paints ):
        lo, hi = self.pt( a0, o0, z0 ), self.pt( a1, o1, z1 )
        self.m.box( lo, hi, paints )

    # ----- treads -----------------------------------------------------------------------------------------------------
    def treads( self ):
        i0, i1 = self.o0 + WEB, self.o1 - WEB
        for k in range( STEPS ):
            zt = ( k + 1 ) * self.h
            f, b = self.A( k ), self.A( k + 1 )
            self.box( f + 1.2, b - GAP, i0, i1, zt - TREAD_T, zt, { "+z": GRATE, "default": GUN } )
            self.box( f, f + 1.2, i0, i1, zt - 2.4, zt + 0.2, { "+z": GUN, "default": GUN } )         # nosing bar
            if self.cfg["angles"]:
                self.box( f + 1.2, f + 3.2, i0, i1, zt - 3.4, zt - TREAD_T, GUN )                       # under-tread angle
                self.box( f + 1.2, f + 2.0, i0, i1, zt - 3.4, zt - 2.4 + 0.0, GUN )

    # ----- stringers: C-channels along the nose line -------------------------------------------------------------------
    def stringer( self, side ):
        d = 1.0 if side == 0 else -1.0                   # across: towards the flight's middle
        o_out = self.o0 if side == 0 else self.o1
        o_in, o_lip = o_out + d * WEB, o_out + d * ( WEB + LIP_W )
        prof = [ ( o_out, -DEPTH ), ( o_out, 0.0 ), ( o_in, 0.0 ), ( o_in, -DEPTH + LIP_T ), ( o_lip, -DEPTH + LIP_T ), ( o_lip, -DEPTH ) ]
        faces = [ ( 0, 1, -d, 0 ), ( 1, 2, 0, 1 ), ( 2, 3, d, 0 ), ( 3, 4, 0, 1 ), ( 4, 5, d, 0 ), ( 5, 0, 0, -1 ) ]       # edge i->i+1: normal ( across, z )
        j0, j1 = 0.5, float( STEPS )
        js = [ j0 ] + [ float( j ) for j in range( 1, STEPS + 1 ) ]
        for ja, jb in zip( js[:-1], js[1:] ):
            for i, ( ia, ib, na, nz ) in enumerate( faces ):
                ( oa, za ), ( ob, zb ) = prof[ia], prof[ib]
                pts = [ self.pt( self.A( ja ), oa, self.zs( ja ) + za - 1.5 ), self.pt( self.A( jb ), oa, self.zs( jb ) + za - 1.5 ),
                        self.pt( self.A( jb ), ob, self.zs( jb ) + zb - 1.5 ), self.pt( self.A( ja ), ob, self.zs( ja ) + zb - 1.5 ) ]
                self.card( BLUE, pts, self.vec( 0.0, na ) + np.array( ( 0, 0, nz ) ) )
        # the ends: the foot cut square ( towards -a ), the head ( towards +a )
        for j, s in ( ( j0, -1.0 ), ( float( STEPS ), 1.0 ) ):
            outline = [ self.pt( self.A( j ), o, self.zs( j ) + z - 1.5 ) for o, z in prof ]
            self.card( BLUE, outline, s * self.vec( 1.0, 0.0 ) )
            # the outline is concave ( an L ): card() fans it, which is right because the L is star-shaped from its first vertex

    # ----- the handrail --------------------------------------------------------------------------------------------------
    def rail( self, side ):
        cfg = self.cfg
        d = 1.0 if side == 0 else -1.0
        o = ( self.o0 if side == 0 else self.o1 ) + d * ( WEB / 2 )
        js = [ 0.5 ]
        n = cfg["post_every"]
        j = float( n )
        while j < STEPS - 0.5:
            js.append( j )
            j += n
        js.append( 25.5 )
        for j in js:                                                  # posts with a base plate, standing on the stringer's top
            a, z = self.A( j ), self.zs( j ) - 1.5
            p = self.pt( a, o, z )
            P.lathe( self.m, ( p[0], p[1] ), [ ( 2.0, z ), ( 2.0, z + 0.5 ), ( POST_R, z + 0.6 ), ( POST_R, z + RAIL_Z - 1.0 ), ( POST_R + 0.3, z + RAIL_Z - 0.9 ), ( POST_R + 0.3, z + RAIL_Z ) ],
                     STEEL, sides=cfg["post_sides"], cap=STEEL )
        for height, radius, enabled in ( ( RAIL_Z, RAIL_R, True ), ( MID_Z, MID_R, cfg["mid"] ) ):
            if not enabled:
                continue
            for ja, jb in zip( js[:-1], js[1:] ):
                p, q = self.pt( self.A( ja ), o, self.zs( ja ) - 1.5 + height ), self.pt( self.A( jb ), o, self.zs( jb ) - 1.5 + height )
                axis = q - p
                length = float( np.linalg.norm( axis ) )
                axis = axis / length
                prof = [ ( radius, 0.0 ), ( radius, length ) ]
                if cfg["dome"] and height == RAIL_Z:
                    nd = cfg["dome"]
                    if ja == js[0]:
                        prof = [ ( radius * math.cos( math.pi / 2 * i / nd ), -radius * math.sin( math.pi / 2 * i / nd ) ) for i in range( nd, 0, -1 ) ] + prof
                    if jb == js[-1]:
                        prof = prof + [ ( radius * math.cos( math.pi / 2 * i / nd ), length + radius * math.sin( math.pi / 2 * i / nd ) ) for i in range( 1, nd + 1 ) ]
                P.lathe_axis( self.m, p, axis, prof, STEEL, sides=cfg["rail_sides"] )
        if cfg["toe"]:                                                # a toe board along the tread edge between posts
            for ja, jb in zip( js[:-1], js[1:] ):
                o_in = o - d * 0.0
                za, zb = self.zs( ja ) - 1.5, self.zs( jb ) - 1.5
                oa, ob = o_in - d * 0.35, o_in + d * 0.35
                top = [ self.pt( self.A( ja ), oa, za + 4.0 ), self.pt( self.A( jb ), oa, zb + 4.0 ), self.pt( self.A( jb ), ob, zb + 4.0 ), self.pt( self.A( ja ), ob, za + 4.0 ) ]
                self.card( GUN, top, ( 0, 0, 1 ) )
                for oo, nn in ( ( oa, -d ), ( ob, d ) ):
                    self.card( GUN, [ self.pt( self.A( ja ), oo, za + 1.0 ), self.pt( self.A( jb ), oo, zb + 1.0 ), self.pt( self.A( jb ), oo, zb + 4.0 ), self.pt( self.A( ja ), oo, za + 4.0 ) ],
                               self.vec( 0.0, nn ) )

    def build( self ):
        self.treads()
        self.stringer( 0 )
        self.stringer( 1 )
        for side, keep in enumerate( self.rails ):
            if keep:
                self.rail( side )
        R.configure( self.m )
        return self.m


def build_all( write=False ):
    stats = {}
    for name, ( lo, hi, climb, rails ) in FLIGHTS.items():
        files, paints, first = [], set(), None
        stats[name] = {}
        for lod in ( 0, 1, 2 ):
            model = Flight( name, lo, hi, climb, rails, lod ).build()
            first = first or model
            paints |= set( model.polygons )
            obj = f"{name}_lod{lod}"
            if write:
                MODEL_DIR.mkdir( parents=True, exist_ok=True )
                tris = K.write_obj( MODEL_DIR / f"{obj}.obj", model, obj )
                S.weld_obj( MODEL_DIR / f"{obj}.obj" )
            else:
                tris = S.tri_count( model )
            files.append( f"{obj}.obj" )
            stats[name][lod] = { "triangles": tris, "degenerate": S.degenerate( model ) }
        if write:
            S.write_vmdl( MODEL_DIR / f"{name}.vmdl", files, paints, first )
    return stats


if __name__ == "__main__":
    print( build_all( write="--write" in sys.argv ) )
