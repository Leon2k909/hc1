"""Reef Hall reception desk v1: a rebuild of the lobby's curved counter as a standalone model.

The old desk (Tools/reefhall_map.py, lobby(), "The desk: ...") is 16 flat facets round a 124 degree arc: a laminate top,
a plain slab of rh_smooth for a front with a 3 inch LED band stuck on it, and three black boxes for monitors. This builds
the same desk, in the same footprint (radius 212-250 from the lobby tank's centre, -62..62 degrees, 42 inch top), with:

  * ten precast concrete panels, each in 4 smooth steps, with V-joints between them and a recessed plinth;
  * a dark top 1.9 in thick with a rounded edge and a 1 in overhang, and a shadow reveal under it;
  * the warm LED band (same rh_led_warm material, same 3 in height) moved down onto the plinth recess, under the overhang;
  * three monitors, keyboards and mice, all reused from the map's approved models (see "the monitors" below).

The model is built in plan inches round the tank's centre (its origin), floor at z 0, so the scene object sits at the
tank's world position (0, 2420, 0) with no rotation. Draw only: the old collision hulls stay in the lobby model.

    python desk.py build            writes Assets/models/props/reefhall/reception_desk_v1/*.obj, .mtl, .vmdl and two .vmat
    python desk.py stats            triangle counts per LOD
    python desk.py parts            triangles added by each part, per LOD

No new texture files. rd_precast and rd_top (this model's two materials, Assets/materials/reefhall/reception_desk_v1/) point
at the project's existing concrete_wall_009 scan (Poly Haven, CC0; already used by Spillway and Collider) at its true scale:
the photograph covers 1.805 m, so 28.8 px/in at its native 2048 px. Everything else is the map's existing materials:
rh_black, rh_gunmetal, rh_steel, rh_led_warm, rh_screen_data, rh_pad_dark and the control room's rh_console_* / rh_monitor_*.
"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
import map_kit as K          # noqa: E402
import riverdale_parts as P  # noqa: E402
import reefhall_map as R     # noqa: E402
import reefhall_monitors as MON   # noqa: E402  the approved control-room monitor
import reefhall_consoles as CON   # noqa: E402  its materials

HERE = Path( __file__ ).resolve().parent
MAT_DIR = ROOT / "Assets/materials/reefhall/reception_desk_v1"
MODEL_DIR = ROOT / "Assets/models/props/reefhall/reception_desk_v1"
MODEL_RES = "models/props/reefhall/reception_desk_v1"
MAT_RES = "materials/reefhall/reception_desk_v1"

# The old desk's footprint (the collision hulls in the lobby model are these wedges, and stay)
TC = np.array( R.LOBBY_TANK )          # plan (e, n) of the lobby tank's centre: this model's origin
R_IN, R_OUT = 212.0, 250.0
A_MIN, A_MAX = -62.0, 62.0
Z_TOP = 42.0

PANELS = 10
PANEL_A = ( A_MAX - A_MIN ) / PANELS    # 12.4 degrees: 54 in of front at the outer face, 46 in at the inner
Z_KICK = 7.0        # the dark plinth's top (the concrete starts here)
LED_Z0, LED_Z1 = 2.4, 5.4    # the LED band on the plinth: 3 in, the old band's height
KICK = 0.7          # how far the plinth is set back
Z_BODY = 39.4       # the concrete's top
T_TOP = 1.9         # the top slab's thickness
OVER = 1.0          # its overhang past the concrete (on both faces)
BN = 0.5            # its edge's radius
REVEAL = 1.4        # the shadow reveal under the top: how far back it is set
GROOVE = 0.5        # a joint's half width and depth
SCAN_IN = 1805 / 25.4   # the existing concrete_wall_009 photograph covers 1.805 m = 71.06 in (Tools/collider_finish.py)
TILE = SCAN_IN          # inches one UV unit of the precast covers: one tile of the scan, so the vmat's TexCoordScale is 1
TOP_TILE = SCAN_IN      # the same for the top
PRECAST_TINT = ( 0.94, 1.01, 1.13 )    # the scan is a warm grey (161, 153, 140): this brings it to the map's cool grey (rh_smooth: 155, 157, 159)
TOP_TINT = ( 0.36, 0.40, 0.48 )        # the same stone, darkened for the top

# LOD settings: steps per panel, edge segments, detail level
LODS = {
    0: dict( steps=4, round_edge=3, detail=2 ),
    1: dict( steps=2, round_edge=1, detail=1 ),
    2: dict( steps=1, round_edge=1, detail=0 ),
}
LOD_THRESHOLDS = { 0: 0.0, 1: 20.0, 2: 60.0 }    # about 19 in per unit at 1920x1080 / 90 degrees: 380 in (9.7 m) and 1140 in (29 m)

MON_A = ( -32.0, 0.0, 32.0 )     # the old monitors' angles
MON_R = 232.0                    # the middle of the monitor's foot (the old monitors stood at 228)
MON_SCALE = 0.62                 # the control-room monitor is a 45 inch wall display: carried over at this scale it is a 26 inch one
MON_W0 = 10.85                   # the middle of the foot, in the monitor's own depth
MON_FOOT = 36.3                  # the foot's underside, in the monitor's own height
KB_R = 222.0                     # the keyboard's middle: it sits between the operator and the monitor
KB_SCALE = 0.85                  # the console's operator keyboard is 21.6 in wide: 18.4 in here


# ---------------------------------------------------------------------------------------------------------------------
# Small helpers

def rad( a ):
    return math.radians( a )


def pol( a, r ):
    return np.array( ( r * math.cos( rad( a ) ), r * math.sin( rad( a ) ) ) )


def pt( a, r, z ):
    p = pol( a, r )
    return np.array( ( p[0], p[1], z ) )


def radial( a ):
    return np.array( ( math.cos( rad( a ) ), math.sin( rad( a ) ), 0.0 ) )


def tangent( a ):
    return np.array( ( -math.sin( rad( a ) ), math.cos( rad( a ) ), 0.0 ) )


def nrz( a, n ):
    """ A section normal ( along the radius, up ) at angle a, in plan space. """
    return radial( a ) * n[0] + np.array( ( 0.0, 0.0, n[1] ) )


def span( a0, a1, steps ):
    return [ a0 + ( a1 - a0 ) * i / steps for i in range( steps + 1 ) ]


def rng_variants( n, seed=20261106 ):
    """ A different window onto the precast tile for each panel (offset, and a quarter turn or a flip), so ten panels cast
    from one picture don't repeat each other's marks. """
    g = np.random.default_rng( seed )
    return [ dict( ou=float( g.uniform( 0, 1 ) ), ov=float( g.uniform( 0, 1 ) ), swap=bool( g.integers( 0, 2 ) ),
                   flip=bool( g.integers( 0, 2 ) ) ) for _ in range( n ) ]


VARIANTS = rng_variants( PANELS )


MON_PROFILE = ( ( 9.65, ( -19.35, 19.35, 42.65, 65.95 ), 0.7 ), ( 10.15, ( -19.25, 19.25, 42.75, 65.85 ), 0.8 ),
                ( 11.25, ( -18.9, 18.9, 43.1, 65.5 ), 1.0 ), ( 12.25, ( -18.0, 18.0, 44.0, 64.6 ), 1.15 ),
                ( 12.60, ( -17.0, 17.0, 45.0, 63.8 ), 0.8 ), ( 12.60, ( -16.7, 16.7, 45.3, 63.5 ), 0.5 ) )     # the shell's rings, from MON.build


def vent_slot( m, cell, opening, depth, back ):
    """ A recessed rectangular slot in the shell's back, with its surround, walls and floor ( MON's hole(), but four corners not
    twelve: at 0.62 scale its 0.1 in rounding is under a millimetre ). """
    a, b, lo, hi = cell
    oa, ob, olo, ohi = opening
    f = ( 0, 1, 0 )
    m.face( MON.SHELL, [ ( a, depth, lo ), ( b, depth, lo ), ( ob, depth, olo ), ( oa, depth, olo ) ], f )
    m.face( MON.SHELL, [ ( b, depth, lo ), ( b, depth, hi ), ( ob, depth, ohi ), ( ob, depth, olo ) ], f )
    m.face( MON.SHELL, [ ( b, depth, hi ), ( a, depth, hi ), ( oa, depth, ohi ), ( ob, depth, ohi ) ], f )
    m.face( MON.SHELL, [ ( a, depth, hi ), ( a, depth, lo ), ( oa, depth, olo ), ( oa, depth, ohi ) ], f )
    cu, cz = ( oa + ob ) / 2, ( olo + ohi ) / 2
    ring = [ ( oa, olo ), ( ob, olo ), ( ob, ohi ), ( oa, ohi ) ]
    for i in range( 4 ):
        ( x, y ), ( xx, yy ) = ring[i], ring[( i + 1 ) % 4]
        m.face( MON.TRIM, [ ( x, depth, y ), ( xx, depth, yy ), ( xx, back, yy ), ( x, back, y ) ], ( cu - ( x + xx ) / 2, 0, cz - ( y + yy ) / 2 ) )
    m.face( MON.DARK, [ ( x, back, y ) for x, y in ring ], f )


def monitor_full( model, fr ):
    """ The approved monitor ( MON.build, the moulded charcoal one ) for the desk: the same bezel, rounded shell, slotted vents,
    port bay, VESA plate with its screws, tilt barrel, foot and spine, at the same numbers. What is left out is what 0.62 scale
    turns to dust: the two cables, the three plugs, the service label's bars and the rubber under the foot. The slots and
    screws and the barrel use fewer sides. """
    m = MON.MonitorMesh( model, fr, 0.0, 0.0 )
    m.solid( ( -19.4, 19.4, 42.6, 66 ), 8.8, 9.6, 0.65, MON.TRIM, bevel=0.10 )
    m.loft( [ [ ( x, d, y ) for x, y in MON.rounded_rect( bounds, r ) ] for d, bounds, r in MON_PROFILE ], MON.SHELL )
    outer = MON.rounded_rect( ( -16.7, 16.7, 45.3, 63.5 ), 0.5 )
    inner = [ ( max( -16.2, min( 16.2, x ) ), max( 45.8, min( 63.0, y ) ) ) for x, y in outer ]
    for i, p in enumerate( outer ):
        j = ( i + 1 ) % len( outer )
        m.face( MON.SHELL, [ ( p[0], 12.6, p[1] ), ( outer[j][0], 12.6, outer[j][1] ), ( inner[j][0], 12.6, inner[j][1] ),
                             ( inner[i][0], 12.6, inner[i][1] ) ], ( 0, 1, 0 ) )
    vents = [ ( -14.8, -4.9, 59.5, 62.7 ), ( 4.9, 14.8, 59.5, 62.7 ) ]
    port = ( -9.0, 9.0, 45.8, 48.4 )
    m.panel( ( -16.2, 16.2, 45.8, 63.0 ), 12.6, MON.SHELL, vents + [ port ] )
    for a, b, lo, hi in vents:
        for row in range( 5 ):
            z0, z1 = lo + ( hi - lo ) * row / 5, lo + ( hi - lo ) * ( row + 1 ) / 5
            mid = ( z0 + z1 ) / 2
            vent_slot( m, ( a, b, z0, z1 ), ( a + 0.15, b - 0.15, mid - 0.10, mid + 0.10 ), 12.6, 12.38 )
    vent_slot( m, port, ( -8.5, 8.5, 45.85, 48.1 ), 12.6, 11.7 )
    m.solid( ( -3.5, 3.5, 49.8, 56.8 ), 12.62, 13.05, 0.40, MON.TRIM, bevel=0.09 )
    for x in ( -2.85, 2.85 ):
        for zz in ( 50.45, 56.15 ):
            R.tube( model, m.point( ( x, 13.02, zz ) ), m.point( ( x, 13.085, zz ) ), 0.19, MON.TRIM, sides=8, cap=True )
    R.tube( model, m.point( ( -1.65, 13.55, 53.3 ) ), m.point( ( 1.65, 13.55, 53.3 ) ), 0.72, MON.TRIM, sides=10, cap=True )
    m.solid( ( -7, 7, 6, 15.7 ), 36.5, 37.1, 0.85, MON.TRIM, axis="z", bevel=0.14 )
    m.solid( ( -1.5, 1.5, 37.05, 53.5 ), 13.0, 14.3, 0.24, MON.TRIM, bevel=0.10 )
    m.rect( ( -0.65, 0.65, 37.25, 49.2 ), 14.31, MON.DARK )          # the spine's cable channel
    m.rect( ( 9.8, 14.6, 46.0, 47.4 ), 12.64, MON.LABEL )            # the service sticker, without its type and barcode


def monitor_stepped( model, fr ):
    """ The middle distance: the bezel and the body as two boxes, the foot and the spine. """
    R.fbox( model, fr, -19.4, 19.4, 8.8, 9.6, 42.6, 66.0, MON.TRIM )
    R.fbox( model, fr, -17.6, 17.6, 9.6, 12.6, 44.0, 64.6, MON.SHELL )
    R.fbox( model, fr, -7, 7, 6, 15.7, 36.3, 37.1, MON.TRIM, skip=( "bottom", ) )
    R.fbox( model, fr, -1.5, 1.5, 12.6, 14.3, 37.1, 53.5, MON.TRIM )


def monitor_boxes( model, fr ):
    """ The far version: the head as one box, and the foot. """
    R.fbox( model, fr, -19.4, 19.4, 8.8, 13.0, 42.6, 66.0, MON.TRIM )
    R.fbox( model, fr, -7, 7, 6, 15.7, 36.3, 37.1, MON.TRIM, skip=( "bottom", ) )


class Desk:
    def __init__( self, lod ):
        self.lod = lod
        self.cfg = LODS[lod]
        self.m = K.Model()
        self.per = self.cfg["steps"]
        n = PANELS * self.per
        self.angles = span( A_MIN, A_MAX, n )            # every step
        self.coarse = span( A_MIN, A_MAX, PANELS )       # one per panel: for what is hidden or flat

    # ----- drawing ---------------------------------------------------------------------------------------------
    def quad( self, paint, pts, towards=None, normals=None, uv=None ):
        if towards is None:
            towards = sum( normals )
        P.card( self.m, paint, pts, towards, uv=uv, normals=normals )

    def poly( self, paint, pts, towards, uv=None ):
        P.card( self.m, paint, pts, towards, uv=uv )

    # ----- the precast front --------------------------------------------------------------------------------
    def precast_uv( self, k, s, z, side ):
        """ UV of panel k at arc length s along the face from its start and height z: u to the viewer's right. """
        v = VARIANTS[k]
        u0 = ( s if side > 0 else -s ) / TILE
        v0 = ( z - Z_KICK ) / TILE
        if v["swap"]:
            u0, v0 = v0, u0
        if v["flip"]:
            u0 = -u0
        return ( u0 + v["ou"], v0 + v["ov"] )

    def panels( self, side ):
        """ side +1: the public (outer) face; -1: the staff (inner) face. """
        R_ = R_OUT if side > 0 else R_IN
        z0, z1 = Z_KICK, Z_BODY
        half = math.degrees( GROOVE / R_ )
        for k in range( PANELS ):
            a0 = A_MIN + k * PANEL_A
            a1 = a0 + PANEL_A
            lo = a0 + ( half if k > 0 else 0.0 )
            hi = a1 - ( half if k < PANELS - 1 else 0.0 )
            ang = span( lo, hi, self.per )
            for a, b in zip( ang[:-1], ang[1:] ):
                sa, sb = R_ * rad( a - a0 ), R_ * rad( b - a0 )
                n_a, n_b = side * radial( a ), side * radial( b )
                self.quad( "rd_precast", [ pt( a, R_, z0 ), pt( b, R_, z0 ), pt( b, R_, z1 ), pt( a, R_, z1 ) ],
                           normals=[ n_a, n_b, n_b, n_a ],
                           uv=[ self.precast_uv( k, sa, z0, side ), self.precast_uv( k, sb, z0, side ),
                                self.precast_uv( k, sb, z1, side ), self.precast_uv( k, sa, z1, side ) ] )
            if k > 0:
                # the V-joint before this panel: two flanks down to the joint's line
                Rb = R_ - side * GROOVE
                aj = a0
                for sgn, a_face in ( ( 1, aj - half ), ( -1, aj + half ) ):
                    p0, p1 = pt( a_face, R_, z0 ), pt( aj, Rb, z0 )
                    q1, q0 = pt( aj, Rb, z1 ), pt( a_face, R_, z1 )
                    d = p1 - p0
                    n = np.cross( d, np.array( ( 0.0, 0.0, 1.0 ) ) )
                    n = n / np.linalg.norm( n )
                    # a flank faces into the joint: towards the other flank's side and out
                    want = side * radial( aj ) * 0.6 + tangent( aj ) * sgn * 0.8
                    if np.dot( n, want ) < 0:
                        n = -n
                    uv = [ self.precast_uv( k if sgn < 0 else k - 1, R_ * rad( a - ( a0 if sgn < 0 else a0 - PANEL_A ) ), z, side )
                           for a, z in ( ( a_face, z0 ), ( aj, z0 ), ( aj, z1 ), ( a_face, z1 ) ) ]
                    self.quad( "rd_precast", [ p0, p1, q1, q0 ], towards=n, uv=uv )

    def kick_and_reveal( self, side ):
        R_ = R_OUT if side > 0 else R_IN
        ang = self.coarse if self.lod == 2 else self.angles
        Rk = R_ - side * KICK
        for a, b in zip( ang[:-1], ang[1:] ):
            n_a, n_b = side * radial( a ), side * radial( b )
            # the recessed plinth plate (dark)
            self.quad( "rh_black", [ pt( a, Rk, 0.0 ), pt( b, Rk, 0.0 ), pt( b, Rk, Z_KICK ), pt( a, Rk, Z_KICK ) ],
                       normals=[ n_a, n_b, n_b, n_a ] )
        for a, b in zip( self.coarse[:-1], self.coarse[1:] ):
            # the concrete's underside over the kick (a low viewer sees it), the reveal band under the top and the
            # ledge it sits on: these hide under the overhang, so one quad to a panel
            down = np.array( ( 0.0, 0.0, -1.0 ) )
            self.quad( "rh_black", [ pt( a, Rk, Z_KICK ), pt( b, Rk, Z_KICK ), pt( b, R_, Z_KICK ), pt( a, R_, Z_KICK ) ], towards=down )
            Rr = R_ - side * REVEAL
            n_a, n_b = side * radial( a ), side * radial( b )
            self.quad( "rh_black", [ pt( a, Rr, Z_BODY ), pt( b, Rr, Z_BODY ), pt( b, Rr, Z_TOP - T_TOP ), pt( a, Rr, Z_TOP - T_TOP ) ],
                       normals=[ n_a, n_b, n_b, n_a ] )
            self.quad( "rh_black", [ pt( a, Rr, Z_BODY ), pt( b, Rr, Z_BODY ), pt( b, R_, Z_BODY ), pt( a, R_, Z_BODY ) ],
                       towards=np.array( ( 0.0, 0.0, 1.0 ) ) )

    def led( self ):
        """ The warm LED band: 3 in tall like the old one (z 5-8 on the face), low on the recessed plinth (z 2.4-5.4), set back
        0.7 in under the overhang so it still shows from standing height. The first version was a 1.3 in line at z 5.1-6.4:
        the floor's reflection of so thin a line broke into separate blobs (iteration 1, output/model-trial-20261106/reefhall/
        iteration1), where the old band gave one continuous glow. """
        Rk = R_OUT - KICK + 0.1
        for a, b in zip( self.angles[:-1], self.angles[1:] ):
            n_a, n_b = radial( a ), radial( b )
            self.quad( "rh_led_warm", [ pt( a, Rk, LED_Z0 ), pt( b, Rk, LED_Z0 ), pt( b, Rk, LED_Z1 ), pt( a, Rk, LED_Z1 ) ], normals=[ n_a, n_b, n_b, n_a ] )

    # ----- the top ---------------------------------------------------------------------------------------------
    def top_edges( self ):
        """ The slab's section as ( ( r0, z0 ), ( r1, z1 ), ( n0 ), ( n1 ), kind ) edges, the outer side then the inner. """
        edges = []
        n = self.cfg["round_edge"]
        for side in ( 1, -1 ):
            rc = ( R_OUT + OVER - BN ) if side > 0 else ( R_IN - OVER + BN )
            r_edge = ( R_OUT + OVER ) if side > 0 else ( R_IN - OVER )
            prev = ( rc, Z_TOP )
            prev_n = ( 0.0, 1.0 )
            for i in range( 1, n + 1 ):
                phi = 90.0 * i / n
                cur = ( rc + side * BN * math.sin( rad( phi ) ), ( Z_TOP - BN ) + BN * math.cos( rad( phi ) ) )
                cur_n = ( side * math.sin( rad( phi ) ), math.cos( rad( phi ) ) )
                edges.append( ( prev, cur, prev_n, cur_n, "edge", side ) )
                prev, prev_n = cur, cur_n
            low = ( r_edge, Z_TOP - T_TOP )
            edges.append( ( prev, low, ( side * 1.0, 0.0 ), ( side * 1.0, 0.0 ), "edge", side ) )
            back = ( ( R_OUT - REVEAL ) if side > 0 else ( R_IN + REVEAL ), Z_TOP - T_TOP )
            edges.append( ( low, back, ( 0.0, -1.0 ), ( 0.0, -1.0 ), "under", side ) )
        return edges

    def top( self ):
        # the flat top
        r_a, r_b = R_IN - OVER + BN, R_OUT + OVER - BN
        for a, b in zip( self.angles[:-1], self.angles[1:] ):
            up = np.array( ( 0.0, 0.0, 1.0 ) )
            pa, pb = pol( a, r_a ), pol( b, r_a )
            qa, qb = pol( a, r_b ), pol( b, r_b )
            uv = lambda p: ( p[0] / TOP_TILE, p[1] / TOP_TILE )
            self.quad( "rd_top", [ ( *pa, Z_TOP ), ( *pb, Z_TOP ), ( *qb, Z_TOP ), ( *qa, Z_TOP ) ], towards=up,
                       uv=[ uv( pa ), uv( pb ), uv( qb ), uv( qa ) ] )
        # its edges, rounded
        for ( r0, z0 ), ( r1, z1 ), n0, n1, kind, side in self.top_edges():
            ang = self.angles if kind == "edge" else self.coarse
            for a, b in zip( ang[:-1], ang[1:] ):
                pts = [ pt( a, r0, z0 ), pt( b, r0, z0 ), pt( b, r1, z1 ), pt( a, r1, z1 ) ]
                nrm = [ nrz( a, n0 ), nrz( b, n0 ), nrz( b, n1 ), nrz( a, n1 ) ]
                s_a, s_b = r0 * rad( a - A_MIN ) / TOP_TILE, r0 * rad( b - A_MIN ) / TOP_TILE
                v0, v1 = z0 / TOP_TILE, z1 / TOP_TILE
                self.quad( "rd_top", pts, normals=nrm, uv=[ ( s_a, v0 ), ( s_b, v0 ), ( s_b, v1 ), ( s_a, v1 ) ] )

    def section_polygon( self ):
        """ The slab's section, all the way round, as ( r, z ) points. """
        n = self.cfg["round_edge"]
        out = []
        for side in ( 1, -1 ):
            rc = ( R_OUT + OVER - BN ) if side > 0 else ( R_IN - OVER + BN )
            pts = [ ( rc, Z_TOP ) ]
            for i in range( 1, n + 1 ):
                phi = 90.0 * i / n
                pts.append( ( rc + side * BN * math.sin( rad( phi ) ), ( Z_TOP - BN ) + BN * math.cos( rad( phi ) ) ) )
            r_edge = ( R_OUT + OVER ) if side > 0 else ( R_IN - OVER )
            pts.append( ( r_edge, Z_TOP - T_TOP ) )
            if side < 0:
                pts.reverse()
            out.append( pts )
        # outer side top->down, then the inner side bottom->top
        return out[0] + out[1]

    def ends( self ):
        sec = self.section_polygon()
        # the body's end: its stepped outline, ear-clipped
        body = [ ( R_IN + KICK, 0.0 ), ( R_OUT - KICK, 0.0 ), ( R_OUT - KICK, Z_KICK ), ( R_OUT, Z_KICK ), ( R_OUT, Z_BODY ),
                 ( R_OUT - REVEAL, Z_BODY ), ( R_OUT - REVEAL, Z_TOP - T_TOP ), ( R_IN + REVEAL, Z_TOP - T_TOP ),
                 ( R_IN + REVEAL, Z_BODY ), ( R_IN, Z_BODY ), ( R_IN, Z_KICK ), ( R_IN + KICK, Z_KICK ) ]
        for a, away in ( ( A_MIN, -1 ), ( A_MAX, 1 ) ):
            toward = tangent( a ) * away
            P._cap( self.m, "rd_top", [ pt( a, r, z ) for r, z in sec ], sec, toward )
            # the body's end takes the precast tile, planar
            pts3 = [ pt( a, r, z ) for r, z in body ]
            P._cap( self.m, "rd_precast", pts3, body, toward )
        # UVs for the body's end are the writer's world-scale ones (tile_overrides): the end is small and plain

    # ----- the monitors, keyboards and the rest -------------------------------------------------------------
    # Nothing here is drawn from scratch. The monitor is the control room's approved one (Tools/reefhall_monitors.py: rounded
    # shell, slotted vents, port bay, VESA plate, foot, cables, service label), built unchanged in its own frame and carried
    # onto the desk at 0.62 scale (a 26 inch display); its finishes are the console's own materials. The keyboard is the
    # console operator's (13 x 4 individual keys on a dark plate, with a front lip and a space bar) at 0.85 scale, and the mouse,
    # mat and cable grommet are the upper-office workstation's. The glass is the old desk's rh_screen_data.

    def placer( self, a, r, scale, w0, z0, z_world ):
        """ Maps a part's own frame ( u to the operator's right, w away from the operator, z up ) onto the desk at angle a:
        the point ( 0, w0, z0 ) lands on the top, z_world, at radius r. Returns position and direction functions. """
        along = np.array( ( math.sin( rad( a ) ), -math.cos( rad( a ) ), 0.0 ) )     # the operator looks outward along the radius
        out = radial( a )
        up = np.array( ( 0.0, 0.0, 1.0 ) )
        o = pol( a, r )

        def pos( p ):
            q = scale * ( along * p[0] + out * ( p[1] - w0 ) + up * ( p[2] - z0 ) )
            return np.array( ( o[0] + q[0], o[1] + q[1], z_world + q[2] ) )

        def vec( n ):
            return along * n[0] + out * n[1] + up * n[2]

        return pos, vec

    def carry( self, scratch, pos, vec ):
        """ Copies a scratch model's polygons into the desk through a placer: positions mapped, directions turned, winding kept
        ( a turn and a uniform scale don't flip it ), UVs and smooth normals carried. """
        for paint, polys in scratch.polygons.items():
            for i, ( pts, n ) in enumerate( polys ):
                ns = scratch.polygon_normals.get( ( paint, i ) )
                uv = scratch.polygon_uvs.get( ( paint, i ) )
                self.m.polygon( paint, [ pos( p ) for p in pts ], vec( n ), uv=uv,
                                normals=[ vec( x ) for x in ns ] if ns is not None else None )

    def monitor( self, a ):
        """ One monitor at angle a: it faces the staff, so players on the public side see its back. """
        d = self.cfg["detail"]
        scratch = K.Model()
        fr = R.Frame( ( 0.0, 0.0 ), ( 1.0, 0.0 ) )          # the console's frame: u right, w away from the operator, z up
        if d >= 2:
            monitor_full( scratch, fr )
        elif d == 1:
            monitor_stepped( scratch, fr )
        else:
            monitor_boxes( scratch, fr )
        if d >= 1:
            R.fbox( scratch, fr, 16.8, 17.15, 8.70, 8.74, 43.25, 43.5, "rh_console_status" )      # its status light
        pos, vec = self.placer( a, MON_R, MON_SCALE, MON_W0, MON_FOOT, Z_TOP )
        self.carry( scratch, pos, vec )
        # the glass over the bezel's window (the console draws its LCD atlas here; the old desk's rh_screen_data does for us)
        z0, z1 = 44.3, 64.775
        glass = [ pos( ( -18.2, 8.74, z0 ) ), pos( ( 18.2, 8.74, z0 ) ), pos( ( 18.2, 8.74, z1 ) ), pos( ( -18.2, 8.74, z1 ) ) ]
        P.card( self.m, "rh_screen_data", glass, vec( ( 0.0, -1.0, 0.0 ) ), uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] )
        self.keyboard( a )
        if d >= 2:
            # a cable grommet in the top behind the foot (the office workstation's)
            c2 = pos( ( 6.5, 20.0, MON_FOOT ) )
            P.torus( self.m, ( c2[0], c2[1], Z_TOP + 0.05 ), ( 0, 0, 1 ), 1.25, 0.22, "rh_steel", seg=14, sides=5 )
            P.cylinder( self.m, c2[:2], 1.2, Z_TOP, Z_TOP + 0.05, "rh_black", sides=14, top="rh_black" )

    def keyboard( self, a ):
        d = self.cfg["detail"]
        scratch = K.Model()
        fr = R.Frame( ( 0.0, 0.0 ), ( 1.0, 0.0 ) )
        bezel, edge, keys = "rh_console_bezel", "rh_console_edge", "rh_console_keys"
        # the console's numbers, with its desk surface at z 0: plate to 0.6, keys to 1.02, front lip to 0.85, space bar to 1.2
        R.fbox( scratch, fr, -10.8, 10.8, -14, -5, 0.0, 0.6, bezel, skip=( "bottom", ) )
        if d >= 2:
            R.fbox( scratch, fr, -10.5, 10.5, -14, -12.2, 0.6, 0.85, edge, skip=( "bottom", ) )
            for row in range( 4 ):
                for col in range( 13 ):
                    u = -9.75 + col * 1.5 + ( 0.22 if row % 2 else 0.0 )
                    w = -11.6 + row * 1.5
                    R.fbox( scratch, fr, u, u + 1.25, w, w + 1.18, 0.6, 1.02, keys, skip=( "bottom", ) )
            R.fbox( scratch, fr, -4, 4, -13.2, -12.0, 0.85, 1.2, keys, skip=( "bottom", ) )
        elif d == 1:
            R.fbox( scratch, fr, -10.5, 10.5, -14, -12.2, 0.6, 0.85, edge, skip=( "bottom", ) )
            R.facing( scratch, keys, [ fr.p( -9.8, -11.6, 1.0 ), fr.p( 9.8 + 0.22, -11.6, 1.0 ), fr.p( 9.8 + 0.22, -5.9, 1.0 ),
                                       fr.p( -9.8, -5.9, 1.0 ) ], ( 0, 0, 1 ) )
        pos, vec = self.placer( a, KB_R, KB_SCALE, -9.5, 0.0, Z_TOP )
        self.carry( scratch, pos, vec )
        if d >= 1:
            # the mouse on its mat, to the keyboard's right (the office workstation's, world sizes)
            ax = ( vec( ( 1, 0, 0 ) ), vec( ( 0, 1, 0 ) ), vec( ( 0, 0, 1 ) ) )
            mc = pos( ( 15.6, -9.5, 0.0 ) )
            P.bevel_box( self.m, mc + np.array( ( 0.0, 0.0, 0.075 ) ), ax, ( 9.0, 10.0, 0.15 ), "rh_pad_dark", bevel=0.06 if d >= 2 else 0.0 )
            P.bevel_box( self.m, mc + np.array( ( 0.0, 0.0, 0.15 + 0.6 ) ), ax, ( 2.8, 4.7, 1.2 ), "rh_black", bevel=0.55 if d >= 2 else 0.0 )
            if d >= 2:
                P.bevel_box( self.m, mc + ax[1] * 0.8 + np.array( ( 0.0, 0.0, 0.15 + 1.2 + 0.02 ) ), ax, ( 0.15, 1.5, 0.15 ), "rh_steel", bevel=0.06 )

    # ----- everything ------------------------------------------------------------------------------------------
    def build( self ):
        for side in ( 1, -1 ):
            self.panels( side )
            self.kick_and_reveal( side )
        self.led()
        self.top()
        self.ends()
        for a in MON_A:
            self.monitor( a )
        self.finish()
        return self.m

    def finish( self ):
        m = self.m
        R.configure( m )
        CON.configure( m )          # the console's own and the monitor's finishes, at their own tile sizes
        m.material_overrides.update( {
            "rd_precast": f"{MAT_RES}/rd_precast.vmat",
            "rd_top": f"{MAT_RES}/rd_top.vmat",
        } )
        m.tile_overrides.update( { "rd_precast": TILE, "rd_top": TOP_TILE } )


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def weld_obj( path ):
    """ K.write_obj gives every polygon its own vertex records; the lobby's OBJ (the BEFORE) shares them. Merge identical
    position, UV and normal records (each in its own index space, as OBJ allows) so the two count the same way. """
    lines = Path( path ).read_text().split( "\n" )
    heads, tables, faces = [], { "v": {}, "vt": {}, "vn": {} }, []
    keep = { "v": [], "vt": [], "vn": [] }
    remap = { "v": {}, "vt": {}, "vn": {} }
    counts = { "v": 0, "vt": 0, "vn": 0 }
    body = []
    for line in lines:
        tag = line.split( " ", 1 )[0]
        if tag in tables:
            counts[tag] += 1
            rec = line
            if rec not in tables[tag]:
                tables[tag][rec] = len( tables[tag] ) + 1
                keep[tag].append( rec )
            remap[tag][counts[tag]] = tables[tag][rec]
        elif tag == "f":
            body.append( ( "f", line ) )
        elif tag == "usemtl":
            body.append( ( "m", line ) )
        elif line and tag in ( "#", "mtllib", "o" ):
            heads.append( line )
    out = list( heads ) + keep["v"] + keep["vt"] + keep["vn"]
    for kind, line in body:
        if kind == "m":
            out.append( line )
            continue
        toks = []
        for tok in line.split()[1:]:
            a, b, c = ( int( x ) for x in tok.split( "/" ) )
            toks.append( f"{remap['v'][a]}/{remap['vt'][b]}/{remap['vn'][c]}" )
        out.append( "f " + " ".join( toks ) )
    Path( path ).write_bytes( ( "\n".join( out ) + "\n" ).encode() )


def write_vmdl( path, name, files, paints, model ):
    """ A model with one render mesh per LOD, and no physics (the lobby's own hulls stay). """
    remaps = ",\n".join( f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{model.material_overrides[p]}" }}' for p in sorted( paints ) )
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{MODEL_RES}/{f}" import_translation = [ 0.0, 0.0, 0.0 ] '
        'import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" '
        'align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] } }'
        for i, f in enumerate( files ) )
    groups = ",\n".join( f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {LOD_THRESHOLDS[i]:.1f} meshes = [ "lod{i}" ] }}'
                         for i in range( len( files ) ) )
    text = ( "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
             "// Generated by Sources/ReefHall/reception-desk-v1/desk.py\n"
             "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
             "\t\t\t{\n\t\t\t\t_class = \"MaterialGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n"
             "\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n"
             + remaps + "\n\t\t\t\t\t\t]\n\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n\t\t\t\t\t},\n"
             "\t\t\t\t]\n\t\t\t},\n"
             "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + meshes + "\n\t\t\t\t]\n\t\t\t},\n"
             "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + groups + "\n\t\t\t\t]\n\t\t\t},\n"
             "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n" )
    K.write_text( path, text )


def write_materials():
    """ The two materials. Both read the existing concrete_wall_009 scan set (colour and roughness from Spillway's scans folder,
    the OpenGL normal Collider already converted): no new texture files. The panels are tinted to Reef Hall's cool grey; the top
    is the same stone darkened, and glossier. """
    scan = "materials/spillway/scans/concrete_wall_009_{}_2k.jpg"
    normal = "materials/collider/finish-v1/concrete_wall_009_nor_gl_2k.jpg"

    def vmat( tint, rough ):
        lines = [ "// Sources/ReefHall/reception-desk-v1/desk.py: the existing concrete_wall_009 scan, at its true scale",
                  '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"',
                  f'    TextureColor "{scan.format( "diff" )}"',
                  f'    TextureNormal "{normal}"',
                  f'    TextureRoughness "{scan.format( "rough" )}"',
                  '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
                  '    g_flMetalness "0.0"',
                  f'    g_flRoughnessScaleFactor "{rough}"',
                  '    g_vTexCoordScale "[1.0 1.0]"',
                  f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"',
                  '    g_flModelTintAmount "1"', "}", "" ]
        return "\n".join( lines )

    MAT_DIR.mkdir( parents=True, exist_ok=True )
    K.write_text( MAT_DIR / "rd_precast.vmat", vmat( PRECAST_TINT, 0.85 ) )
    K.write_text( MAT_DIR / "rd_top.vmat", vmat( TOP_TINT, 0.55 ) )


def tri_count( model ):
    return sum( len( p ) - 2 for polys in model.polygons.values() for p, _ in polys )


def build_all( write=True ):
    stats = {}
    files, models = [], []
    all_paints = set()
    if write:
        write_materials()
    for lod in ( 0, 1, 2 ):
        desk = Desk( lod )
        model = desk.build()
        models.append( model )
        all_paints |= set( model.polygons )
        name = f"reception_desk_lod{lod}"
        if write:
            MODEL_DIR.mkdir( parents=True, exist_ok=True )
            tris = K.write_obj( MODEL_DIR / f"{name}.obj", model, name )
            weld_obj( MODEL_DIR / f"{name}.obj" )
        else:
            tris = tri_count( model )
        files.append( f"{name}.obj" )
        stats[lod] = tris
    if write:
        write_vmdl( MODEL_DIR / "reception_desk.vmdl", "reception_desk", files, all_paints, models[0] )
    return stats


def part_counts():
    """ Triangles each part adds, per LOD. """
    out = {}
    for lod in ( 0, 1, 2 ):
        d = Desk( lod )
        row, last = {}, 0
        steps = ( ( "panels", lambda: [ d.panels( s ) for s in ( 1, -1 ) ] ),
                  ( "plinth, reveal", lambda: [ d.kick_and_reveal( s ) for s in ( 1, -1 ) ] ),
                  ( "led", d.led ), ( "top", d.top ), ( "ends", d.ends ),
                  ( "monitors + keyboards", lambda: [ d.monitor( a ) for a in MON_A ] ) )
        for name, fn in steps:
            fn()
            now = tri_count( d.m )
            row[name] = now - last
            last = now
        kb = Desk( lod )
        for a in MON_A:
            kb.keyboard( a )
        row["of which keyboards, mice"] = tri_count( kb.m )
        row["total"] = last
        out[lod] = row
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len( sys.argv ) > 1 else "stats"
    if cmd == "parts":
        for lod, row in part_counts().items():
            print( lod, row )
    else:
        print( build_all( write=( cmd == "build" ) ) )
