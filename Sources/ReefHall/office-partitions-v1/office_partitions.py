"""Reef Hall's control-room office glass walls as one standalone model (Sources/ReefHall/office-partitions-v1, 2026-11-06).

Old (Tools/reefhall_map.py partition()): 4 in square gunmetal posts every 90 in, a flat 6 in bar at the floor, a flat 4 in bar
at 96 in, a 5 in slab on top, 1-sided glass planes, and 4 x 5 in square jambs at the door gaps. New: the same two walls (same
runs, same posts' places, same door gaps, same collision) as a framed glass partition:

  * a floor channel with a steel cap, a transom rail with a glazing gasket, a head channel with a drip lip;
  * slim mullions with steel pressure-cover strips and black glazing gaskets either side;
  * real glass panes (0.8 in thick, with visible edges): frosted below the transom, clear above;
  * door frames at the gaps: steel jambs with a black rebate gasket, a head-height stop and a threshold plate.

Existing materials only (rh_gunmetal, rh_steel, rh_black, rh_glass_office, rh_glass). Drawn in the generator's plan frame, so a
ModelRenderer at world (0,0,0) with no rotation puts it right. Three LODs, no physics.

Run:  python office_partitions.py [--write]
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
HERE = Path( __file__ ).resolve().parent
sys.path.insert( 0, str( HERE.parent / "stairs-v1" ) )
import map_kit as K          # noqa: E402
import reefhall_map as R     # noqa: E402
import stairs as S           # noqa: E402

MODEL_DIR = S.MODEL_DIR
GUN, STEEL, BLACK, FROST, CLEAR = "rh_gunmetal", "rh_steel", "rh_black", "rh_glass_office", "rh_glass"
Z0, Z1 = R.L1, R.OFFICE_TOP
TRANSOM = 96.0
o_e0, o_e1, o_n0, o_n1 = R.OFFICE
RUNS = (                         # ( start, end, gaps ): plan ( e, n ); u runs along the wall, w across it ( run A: u = e, w = n; run B: u = n, w = e )
    ( ( 1880.0, o_n0 ), ( o_e1, o_n0 ), ( ( 120.0, 200.0 ), ), "A" ),
    ( ( o_e1, o_n0 ), ( o_e1, o_n1 ), ( ( 60.0, 130.0 ), ), "B" ),
)
LODS = { 0: dict( beads=True, covers=True, glass_edge=True ), 1: dict( beads=False, covers=True, glass_edge=False ),
         2: dict( beads=False, covers=False, glass_edge=False ) }


class Wall:
    def __init__( self, model, p0, p1, gaps, kind, cfg ):
        self.m, self.p0, self.gaps, self.kind, self.cfg = model, p0, gaps, kind, cfg
        self.length = float( np.hypot( p1[0] - p0[0], p1[1] - p0[1] ) )

    def box( self, u0, u1, w0, w1, z0, z1, paints ):
        if self.kind == "A":
            lo, hi = ( self.p0[0] + u0, self.p0[1] + w0, z0 ), ( self.p0[0] + u1, self.p0[1] + w1, z1 )
        else:
            lo, hi = ( self.p0[0] + w0, self.p0[1] + u0, z0 ), ( self.p0[0] + w1, self.p0[1] + u1, z1 )
        self.m.box( np.array( lo, float ), np.array( hi, float ), paints )

    def segment( self, a, b ):
        cfg = self.cfg
        posts = max( 1, int( np.ceil( ( b - a ) / 90 ) ) )
        us = [ a + ( b - a ) * j / posts for j in range( posts + 1 ) ]
        # rails: floor channel with a steel cap, transom with a gasket, head channel with a lip
        self.box( a, b, -2.4, 2.4, Z0, Z0 + 6.5, GUN )
        self.box( a, b, -2.6, 2.6, Z0 + 6.5, Z0 + 7.0, STEEL )
        self.box( a, b, -2.2, 2.2, Z0 + TRANSOM, Z0 + TRANSOM + 5.0, GUN )
        self.box( a, b, -2.8, 2.8, Z1, Z1 + 1.2, STEEL )
        self.box( a, b, -2.5, 2.5, Z1 + 1.2, Z1 + 6.0, GUN )
        if cfg["beads"]:
            for w in ( -1.0, 1.0 ):
                self.box( a, b, w - 0.35, w + 0.35, Z0 + 7.0, Z0 + 8.2, BLACK )
                self.box( a, b, w - 0.35, w + 0.35, Z0 + TRANSOM - 1.2, Z0 + TRANSOM, BLACK )
                self.box( a, b, w - 0.35, w + 0.35, Z0 + TRANSOM + 5.0, Z0 + TRANSOM + 6.2, BLACK )
                self.box( a, b, w - 0.35, w + 0.35, Z1 - 1.2, Z1, BLACK )
        for j in range( posts ):                                  # the glass: frosted below the transom, clear above
            ua, ub = us[j] + 1.9, us[j + 1] - 1.9
            if j == 0:
                ua = a + 0.3
            if j == posts - 1:
                ub = b - 0.3
            edge = { "default": CLEAR, "+e": CLEAR, "-e": CLEAR } if cfg["glass_edge"] else CLEAR
            self.box( ua, ub, -0.4, 0.4, Z0 + 8.2, Z0 + TRANSOM - 1.2, FROST )
            self.box( ua, ub, -0.4, 0.4, Z0 + TRANSOM + 6.2, Z1 - 1.2, edge )
        for u in us:                                              # mullions: a 3.2 in post, a steel cover strip each side, gaskets beside it
            inner = u in ( us[0], us[-1] )
            half = 1.6
            self.box( max( a, u - half ), min( b, u + half ), -2.0, 2.0, Z0 + 6.5, Z1, GUN )
            if cfg["covers"] and not inner:
                for w in ( -2.0, 2.0 ):
                    self.box( u - 0.9, u + 0.9, w - ( 0.0 if w > 0 else 0.4 ), w + ( 0.4 if w > 0 else 0.0 ), Z0 + 8.2, Z1 - 1.2, STEEL )
            if cfg["beads"] and not inner:
                for s in ( -1, 1 ):
                    for w in ( -1.0, 1.0 ):
                        self.box( u + s * ( half + 0.0 ), u + s * ( half + 0.4 ) if s > 0 else u - half - 0.4, w - 0.35, w + 0.35, Z0 + 8.2, Z0 + TRANSOM - 1.2, BLACK )
                        self.box( u + s * ( half + 0.0 ), u + s * ( half + 0.4 ) if s > 0 else u - half - 0.4, w - 0.35, w + 0.35, Z0 + TRANSOM + 6.2, Z1 - 1.2, BLACK )

    def doors( self ):
        for g0, g1 in self.gaps:
            for u, s in ( ( g0, 1 ), ( g1, -1 ) ):                  # s: the jamb's body lies on the side away from the opening
                self.box( u - 2.5, u + 2.5, -3.0, 3.0, Z0, Z1, STEEL )                  # a 5 in steel jamb, 6 in deep
            self.box( g0, g1, -3.0, 3.0, Z0, Z0 + 0.5, STEEL )          # threshold plate

    def build( self ):
        cuts = [ 0.0 ] + [ x for g in self.gaps for x in g ] + [ self.length ]
        for k in range( 0, len( cuts ), 2 ):
            if cuts[k + 1] - cuts[k] >= 1:
                self.segment( cuts[k], cuts[k + 1] )
        self.doors()


def build_model( lod ):
    m = K.Model()
    for p0, p1, gaps, kind in RUNS:
        Wall( m, p0, p1, gaps, kind, LODS[lod] ).build()
    m.uv_source_name = "office_partitions"
    R.configure( m )
    return m


def build_all( write=False ):
    stats, files, paints, first = {}, [], set(), None
    for lod in ( 0, 1, 2 ):
        model = build_model( lod )
        first = first or model
        paints |= set( model.polygons )
        obj = f"office_partitions_lod{lod}"
        if write:
            MODEL_DIR.mkdir( parents=True, exist_ok=True )
            tris = K.write_obj( MODEL_DIR / f"{obj}.obj", model, obj )
            S.weld_obj( MODEL_DIR / f"{obj}.obj" )
        else:
            tris = S.tri_count( model )
        files.append( f"{obj}.obj" )
        stats[lod] = { "triangles": tris, "degenerate": S.degenerate( model ) }
    if write:
        S.write_vmdl( MODEL_DIR / "office_partitions.vmdl", files, paints, first )
    return stats


if __name__ == "__main__":
    print( build_all( write="--write" in sys.argv ) )
