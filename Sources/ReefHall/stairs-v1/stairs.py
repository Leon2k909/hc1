"""Reef Hall's straight stairs as standalone models (Sources/ReefHall/stairs-v1, 2026-11-06).

The old stairs (Tools/reefhall_map.py stair() + stair_rail()) were a stack of 26 plain boxes per flight, each with a
flat 0.15 in brass strip lying on its tread, and a stair rail of square 2.4 in posts under one 8-sided tube. The new
flight is a closed-string stair with the same footprint, tread heights and run, and the same collision (the generator
keeps its collision-only boxes and rail hulls):

  * treads in the floor's own slate finish, each one slab with no joint across it, a 0.6 in chamfered nosing that
    overhangs a recessed riser by 1 in (a shadow line under every nose), and a brass anti-slip strip let into the tread;
  * two 4 in kerbs (the closed strings) that rise with the stair: the sloped top carries the balustrade, the outer face has a
    gunmetal plinth, a recessed concrete panel and a gunmetal stringer band;
  * a closed end wall at the head with a plinth and two vertical reveals;
  * the balustrade of the approved lobby balcony (Sources/ReefHall/lobby-rail-v1), laid on the slope: a stainless base shoe,
    12 mm glass panels, round posts with a base collar and a cup under the rail, two glass clamps per post and side, and a
    round 2 in handrail with splice rings and domed ends.

Two variants: `lobby_stair` (280 x 180 in, a rail each side; the south flight is the same model, moved) and
`control_stair` (286 x 130 in, a rail on the lower-n side only, like the old one).

Existing Reef Hall materials only (rh_floor, rh_wall_dark, rh_gunmetal, rh_brass, rh_steel, rh_black, rh_glass): no new
textures, no new materials.

The model's frame: origin at the flight's foot (centre of its width, on the floor), x across (plan n), y up the flight
(plan -e: both flights climb west), z up. build( turn=True ) turns it into the generator's plan frame as the rail did, so a
ModelRenderer at map_kit.to_world( ( e_foot, n_centre, 0 ) ) with no rotation puts it right.

Run:  python stairs.py [--write]       without --write it only builds and counts; with it, writes
Assets/models/props/reefhall/stairs_v1/ (OBJ per LOD and the vmdl files)
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

HERE = Path( __file__ ).resolve().parent
MODEL_DIR = ROOT / "Assets/models/props/reefhall/stairs_v1"
MODEL_RES = "models/props/reefhall/stairs_v1"

H, STEPS = 208.0, 26             # R.L1 and the generator's 8 in risers
KERB = 4.0                       # the closed strings' width
UNDERCUT = 1.0                   # the nose overhangs its riser by this much
LIP = 1.4                        # the nose's thickness
CHAMFER = 0.6
PLINTH = 4.0
BAND = 9.0                       # the stringer band's depth under the kerb top
RECESS = 0.5
RAIL_DZ = 33.0                   # handrail centre above the nose line: its top is at 34, the old rail hull's top (kept as collision)
RAIL_R = 1.0
GLASS_T, GLASS_GAP = 0.5, 1.2
GLASS_Z0, GLASS_Z1 = 2.6, 29.0   # the glass stands in the shoe's slot (floor at 2.6) and ends 3 in under the rail
SHOE_Z = 3.3
CLAMP_DZ = ( 8.0, 22.0 )
LOD_THRESHOLDS = { 0: 0.0, 1: 24.0, 2: 70.0 }     # about 19 in per unit: 456 in (11.6 m) and 1330 in (33.8 m) from the model's centre
LODS = {
    0: dict( post_sides=8, rail_sides=12, dome=4, clamps=True, screws=True, ring=True, nose=True, brass=True, shoe="full", reveals=True ),
    1: dict( post_sides=6, rail_sides=8, dome=2, clamps=True, screws=False, ring=True, nose=True, brass=True, shoe="full", reveals=True ),
    2: dict( post_sides=6, rail_sides=6, dome=0, clamps=False, screws=False, ring=False, nose=False, brass=False, shoe="simple", reveals=False ),
}
VARIANTS = {
    "lobby_stair": dict( L=280.0, W=180.0, rails=( True, True ) ),
    "control_stair": dict( L=286.0, W=130.0, rails=( True, False ) ),     # rails = ( -x side, +x side ): -x is the lower n
}

FLOOR, WALL, GUN, BRASS = "rh_floor", "rh_wall_dark", "rh_gunmetal", "rh_brass"
STEEL, GLASS, BLACK = "rh_steel", "rh_glass", "rh_black"
UP = np.array( ( 0.0, 0.0, 1.0 ) )


def v3( x, y, z ):
    return np.array( ( x, y, z ), float )


def turn_to_plan( model ):
    """ A quarter turn about the vertical axis, ( x, y, z ) -> ( -y, x, z ): the drawing's y (up the flight, west) becomes
    plan -e and its x (across) becomes plan n, so after map_kit.to_world ( n, -e, z ) the model's world x is across the
    flight and its world y is up it. A rotation: winding and normals stay outward (same as lobby-rail-v1). """
    def turn( v ):
        return np.array( ( -v[1], v[0], v[2] ), float )
    for paint, items in list( model.polygons.items() ):
        model.polygons[paint] = [ ( [ turn( p ) for p in points ], turn( normal ) ) for points, normal in items ]
    model.polygon_normals = { key: [ turn( n ) for n in normals ] for key, normals in model.polygon_normals.items() }


class Flight:
    def __init__( self, name, L, W, rails, lod ):
        self.name, self.L, self.W, self.rails, self.lod, self.cfg = name, L, W, rails, lod, LODS[lod]
        self.r, self.h = L / STEPS, H / STEPS
        self.slope = self.h / self.r
        self.xo, self.xi = W / 2, W / 2 - KERB
        self.m = K.Model()

    def card( self, paint, pts, towards, uv=None ):
        P.card( self.m, paint, pts, np.asarray( towards, float ), uv=uv )

    def k( self, y ):
        """ The nose line: through every nosing, h at the foot, rising with the stair. """
        return self.h + y * self.slope

    # ----- treads, risers, noses, brass strips -----------------------------------------------------------------------
    def treads( self ):
        r, h, xi, cfg = self.r, self.h, self.xi, self.cfg
        for k in range( STEPS ):
            zt, y0, z_prev = ( k + 1 ) * h, k * r, k * h
            y_end = ( k + 1 ) * r + UNDERCUT if k < STEPS - 1 else self.L
            v0 = 0.03 + ( ( k * 0.0371 ) % 0.40 )                 # a window of the 2 x 2 tile picture with no joint in it
            uvf = lambda x, y, v0=v0, y0=y0: ( 0.03 + ( x + xi ) / 384.0, v0 + ( y - y0 ) / 384.0 )          # noqa: E731
            if cfg["nose"]:
                ya = y0 + CHAMFER
                top = [ v3( -xi, ya, zt ), v3( xi, ya, zt ), v3( xi, y_end, zt ), v3( -xi, y_end, zt ) ]
                self.card( FLOOR, top, UP, [ uvf( p[0], p[1] ) for p in top ] )
                cham = [ v3( -xi, y0, zt - CHAMFER ), v3( xi, y0, zt - CHAMFER ), v3( xi, ya, zt ), v3( -xi, ya, zt ) ]
                self.card( FLOOR, cham, v3( 0, -1, 1 ), [ uvf( p[0], p[1] ) for p in cham ] )
                front = [ v3( -xi, y0, zt - LIP ), v3( xi, y0, zt - LIP ), v3( xi, y0, zt - CHAMFER ), v3( -xi, y0, zt - CHAMFER ) ]
                self.card( FLOOR, front, v3( 0, -1, 0 ), [ uvf( p[0], y0 + 0.02 * ( p[2] - zt ) ) for p in front ] )
                under = [ v3( -xi, y0, zt - LIP ), v3( xi, y0, zt - LIP ), v3( xi, y0 + UNDERCUT, zt - LIP ), v3( -xi, y0 + UNDERCUT, zt - LIP ) ]
                self.card( WALL, under, -UP )
                riser = [ v3( -xi, y0 + UNDERCUT, z_prev ), v3( xi, y0 + UNDERCUT, z_prev ), v3( xi, y0 + UNDERCUT, zt - LIP ),
                          v3( -xi, y0 + UNDERCUT, zt - LIP ) ]
            else:
                top = [ v3( -xi, y0, zt ), v3( xi, y0, zt ), v3( xi, y_end, zt ), v3( -xi, y_end, zt ) ]
                self.card( FLOOR, top, UP, [ uvf( p[0], p[1] ) for p in top ] )
                riser = [ v3( -xi, y0, z_prev ), v3( xi, y0, z_prev ), v3( xi, y0, zt ), v3( -xi, y0, zt ) ]
            self.card( WALL, riser, v3( 0, -1, 0 ) )
            if cfg["brass"]:
                a, b, bz = y0 + 0.9, y0 + 3.0, zt + 0.2
                x0, x1 = -xi + 1.0, xi - 1.0
                self.card( BRASS, [ v3( x0, a, zt ), v3( x1, a, zt ), v3( x1, a + 0.25, bz ), v3( x0, a + 0.25, bz ) ], v3( 0, -1, 1 ) )
                self.card( BRASS, [ v3( x0, a + 0.25, bz ), v3( x1, a + 0.25, bz ), v3( x1, b - 0.25, bz ), v3( x0, b - 0.25, bz ) ], UP )
                self.card( BRASS, [ v3( x0, b - 0.25, bz ), v3( x1, b - 0.25, bz ), v3( x1, b, zt ), v3( x0, b, zt ) ], v3( 0, 1, 1 ) )
                # (the strip's two 0.2 in end faces are left open: they are the width of a pencil line and sit 1 in from the kerbs)

    # ----- the kerbs (closed strings) ---------------------------------------------------------------------------------
    def kerbs( self ):
        r, h, L, xi, xo = self.r, self.h, self.L, self.xi, self.xo
        yk = L - r
        for sx in ( -1.0, 1.0 ):
            a, b = sx * xi, sx * xo
            self.card( GUN, [ v3( a, 0, h ), v3( b, 0, h ), v3( b, yk, H ), v3( a, yk, H ) ], UP )
            self.card( GUN, [ v3( a, yk, H ), v3( b, yk, H ), v3( b, L, H ), v3( a, L, H ) ], UP )
            self.card( GUN, [ v3( a, 0, 0 ), v3( b, 0, 0 ), v3( b, 0, h ), v3( a, 0, h ) ], v3( 0, -1, 0 ) )
            for k in range( STEPS - 1 ):
                zt, y0, y1 = ( k + 1 ) * h, k * r, ( k + 1 ) * r
                face = [ v3( a, y0, zt ), v3( a, y1 + UNDERCUT, zt ), v3( a, y1 + UNDERCUT, zt + h ), v3( a, y1, zt + h ) ]
                self.card( WALL, face, v3( -sx, 0, 0 ) )

    # ----- the outer faces: plinth, recessed panel, stringer band -----------------------------------------------------
    def sides( self ):
        r, h, L, xo, slope = self.r, self.h, self.L, self.xo, self.slope
        yk = L - r
        ya = ( PLINTH + BAND - h ) / slope                  # where the band's lower edge meets the plinth's top
        for sx in ( -1.0, 1.0 ):
            x0, x1 = sx * xo, sx * ( xo - RECESS )
            out = v3( sx, 0, 0 )
            self.card( GUN, [ v3( x0, 0, 0 ), v3( x0, L, 0 ), v3( x0, L, PLINTH ), v3( x0, 0, PLINTH ) ], out )
            self.card( GUN, [ v3( x1, ya, PLINTH ), v3( x0, ya, PLINTH ), v3( x0, L, PLINTH ), v3( x1, L, PLINTH ) ], UP )
            self.card( WALL, [ v3( x1, ya, PLINTH ), v3( x1, L, PLINTH ), v3( x1, L, H - BAND ), v3( x1, yk, H - BAND ) ], out )
            self.card( GUN, [ v3( x1, ya, PLINTH ), v3( x0, ya, PLINTH ), v3( x0, yk, H - BAND ), v3( x1, yk, H - BAND ) ], v3( 0, slope, -1 ) )
            self.card( GUN, [ v3( x1, yk, H - BAND ), v3( x0, yk, H - BAND ), v3( x0, L, H - BAND ), v3( x1, L, H - BAND ) ], -UP )
            self.card( GUN, [ v3( x0, 0, PLINTH ), v3( x0, ya, PLINTH ), v3( x0, yk, H - BAND ), v3( x0, yk, H ), v3( x0, 0, h ) ], out )
            self.card( GUN, [ v3( x0, yk, H - BAND ), v3( x0, L, H - BAND ), v3( x0, L, H ), v3( x0, yk, H ) ], out )

    # ----- the end wall at the head of the flight -----------------------------------------------------------------------
    def end_wall( self ):
        L, xo, out = self.L, self.xo, v3( 0, 1, 0 )
        self.card( GUN, [ v3( -xo, L, 0 ), v3( xo, L, 0 ), v3( xo, L, PLINTH ), v3( -xo, L, PLINTH ) ], out )
        edges = [ -xo ]
        if self.cfg["reveals"]:
            for c in ( -30.0, 30.0 ):
                edges += [ c - 0.5, c + 0.5 ]
        edges.append( xo )
        for i in range( 0, len( edges ), 2 ):
            self.card( WALL, [ v3( edges[i], L, PLINTH ), v3( edges[i + 1], L, PLINTH ), v3( edges[i + 1], L, H ), v3( edges[i], L, H ) ], out )
        if self.cfg["reveals"]:
            for c in ( -30.0, 30.0 ):
                a, b = c - 0.5, c + 0.5
                self.card( WALL, [ v3( a, L - RECESS, PLINTH ), v3( b, L - RECESS, PLINTH ), v3( b, L - RECESS, H ), v3( a, L - RECESS, H ) ], out )
                for x, s in ( ( a, 1.0 ), ( b, -1.0 ) ):
                    self.card( WALL, [ v3( x, L - RECESS, PLINTH ), v3( x, L, PLINTH ), v3( x, L, H ), v3( x, L - RECESS, H ) ], v3( s, 0, 0 ) )
                self.card( WALL, [ v3( a, L - RECESS, PLINTH ), v3( b, L - RECESS, PLINTH ), v3( b, L, PLINTH ), v3( a, L, PLINTH ) ], UP )

    # ----- the balustrade -------------------------------------------------------------------------------------------------
    def balustrade( self, sx ):
        cfg, slope, k = self.cfg, self.slope, self.k
        xc = sx * ( self.xo - 2.0 )                       # the old rail's line: 2 in inside the flight's edge
        Ly = self.L - self.r                              # it runs up to the top step's nose
        bays = max( 3, int( round( Ly / 44.9 ) ) )        # about 55 in along the slope: the balcony's bay is 60
        ys = [ 3.0 + j * ( Ly - 6.0 ) / bays for j in range( bays + 1 ) ]
        # the base shoe, sheared onto the slope
        if cfg["shoe"] == "full":
            prof = [ ( -1.7, 0.0 ), ( -1.7, 2.7 ), ( -1.35, SHOE_Z ), ( -0.38, SHOE_Z ), ( -0.38, GLASS_Z0 ), ( 0.38, GLASS_Z0 ),
                     ( 0.38, SHOE_Z ), ( 1.35, SHOE_Z ), ( 1.7, 2.7 ), ( 1.7, 0.0 ) ]
            kinds = [ ( STEEL, ( -1, 0 ) ), ( STEEL, ( -0.7, 0.7 ) ), ( STEEL, ( 0, 1 ) ), ( BLACK, ( 1, 0 ) ), ( BLACK, ( 0, 1 ) ),
                      ( BLACK, ( -1, 0 ) ), ( STEEL, ( 0, 1 ) ), ( STEEL, ( 0.7, 0.7 ) ), ( STEEL, ( 1, 0 ) ) ]
            blocks = [ [ prof[0], prof[1], prof[2], prof[3], ( -0.38, 0.0 ) ], [ ( -0.38, 0.0 ), prof[4], prof[5], ( 0.38, 0.0 ) ],
                       [ ( 0.38, 0.0 ), prof[6], prof[7], prof[8], prof[9] ] ]
        else:
            prof = [ ( -1.7, 0.0 ), ( -1.7, SHOE_Z ), ( 1.7, SHOE_Z ), ( 1.7, 0.0 ) ]
            kinds = [ ( STEEL, ( -1, 0 ) ), ( STEEL, ( 0, 1 ) ), ( STEEL, ( 1, 0 ) ) ]
            blocks = [ prof ]
        for ( a, b ), ( paint, n ) in zip( zip( prof[:-1], prof[1:] ), kinds ):
            self.card( paint, [ v3( xc + a[0], 0.0, k( 0.0 ) + a[1] ), v3( xc + a[0], Ly, k( Ly ) + a[1] ),
                                v3( xc + b[0], Ly, k( Ly ) + b[1] ), v3( xc + b[0], 0.0, k( 0.0 ) + b[1] ) ], v3( n[0], 0.0, n[1] ) )
        for y, s in ( ( 0.0, -1.0 ), ( Ly, 1.0 ) ):
            for blk in blocks:
                self.card( STEEL, [ v3( xc + x, y, k( y ) + z ) for x, z in blk ], v3( 0.0, s, 0.0 ) )
        # the glass: one panel per bay, a parallelogram with the slope
        t = GLASS_T / 2
        for j in range( bays ):
            a, b = ys[j] + GLASS_GAP, ys[j + 1] - GLASS_GAP
            za0, zb0, za1, zb1 = k( a ) + GLASS_Z0, k( b ) + GLASS_Z0, k( a ) + GLASS_Z1, k( b ) + GLASS_Z1
            for s in ( 1.0, -1.0 ):
                self.card( GLASS, [ v3( xc + s * t, a, za0 ), v3( xc + s * t, b, zb0 ), v3( xc + s * t, b, zb1 ), v3( xc + s * t, a, za1 ) ], v3( s, 0, 0 ) )
            self.card( GLASS, [ v3( xc - t, a, za1 ), v3( xc + t, a, za1 ), v3( xc + t, b, zb1 ), v3( xc - t, b, zb1 ) ], UP )
            for y, s, z0, z1 in ( ( a, -1.0, za0, za1 ), ( b, 1.0, zb0, zb1 ) ):
                self.card( GLASS, [ v3( xc - t, y, z0 ), v3( xc + t, y, z0 ), v3( xc + t, y, z1 ), v3( xc - t, y, z1 ) ], v3( 0.0, s, 0.0 ) )
        # the posts stand upright; their base is cut down 1.5 slopes so the collar meets the sloped shoe all round
        sk = 1.5 * slope
        top = RAIL_DZ - 0.8
        if self.lod == 2:
            post = [ ( 0.9, SHOE_Z - sk ), ( 0.9, top - 0.2 ), ( 1.2, top ) ]
        else:
            post = [ ( 1.5, SHOE_Z - sk ), ( 1.5, SHOE_Z + sk + 0.5 ), ( 0.95, SHOE_Z + sk + 0.8 ), ( 0.9, SHOE_Z + sk + 1.0 ),
                     ( 0.9, top - 1.5 ), ( 1.2, top - 1.1 ), ( 1.2, top ) ]
        for y in ys:
            P.lathe( self.m, ( xc, y ), [ ( rad, k( y ) + dz ) for rad, dz in post ], STEEL, sides=cfg["post_sides"], cap=STEEL )
        # the glass clamps: plates that follow the glass's edge up the slope
        if cfg["clamps"]:
            for j, y in enumerate( ys ):
                lo, hi = -2.0, 2.0                        # a plate spans both glass edges at a joint
                if j == 0:
                    lo = -0.9                             # the first and last posts have a panel on one side only
                if j == bays:
                    hi = 0.9
                for s in ( 1.0, -1.0 ):
                    for dz in CLAMP_DZ:
                        x0, x1 = xc + s * ( GLASS_T / 2 ), xc + s * ( GLASS_T / 2 + 0.3 )
                        ya, yb = y + lo, y + hi
                        za, zb = k( ya ) + dz, k( yb ) + dz
                        hh = 3.6
                        self.card( STEEL, [ v3( x1, ya, za ), v3( x1, yb, zb ), v3( x1, yb, zb + hh ), v3( x1, ya, za + hh ) ], v3( s, 0, 0 ) )
                        self.card( STEEL, [ v3( x0, ya, za + hh ), v3( x1, ya, za + hh ), v3( x1, yb, zb + hh ), v3( x0, yb, zb + hh ) ], UP )
                        self.card( STEEL, [ v3( x0, ya, za ), v3( x1, ya, za ), v3( x1, yb, zb ), v3( x0, yb, zb ) ], -UP )
                        for yy, ss, zz in ( ( ya, -1.0, za ), ( yb, 1.0, zb ) ):
                            self.card( STEEL, [ v3( x0, yy, zz ), v3( x1, yy, zz ), v3( x1, yy, zz + hh ), v3( x0, yy, zz + hh ) ], v3( 0, ss, 0 ) )
                        if cfg["screws"]:
                            ym = y + ( lo + hi ) / 2      # one cap-head screw on each plate, in its middle
                            P.lathe_axis( self.m, ( x1, ym, k( ym ) + dz + 1.8 ), ( s, 0.0, 0.0 ), [ ( 0.34, 0.0 ), ( 0.34, 0.12 ) ],
                                          STEEL, sides=6, cap=STEEL )
        # the handrail: a round tube along the slope, domed at both ends, with a splice ring every two bays
        axis = v3( 0.0, 1.0, slope )
        axis = axis / np.linalg.norm( axis )
        length = Ly * math.sqrt( 1 + slope * slope )
        start = v3( xc, 0.0, k( 0.0 ) + RAIL_DZ )
        sides = cfg["rail_sides"]
        prof = [ ( RAIL_R, 0.0 ), ( RAIL_R, length ) ]
        if cfg["dome"]:
            n = cfg["dome"]
            head = [ ( RAIL_R * math.cos( math.pi / 2 * i / n ), -RAIL_R * math.sin( math.pi / 2 * i / n ) ) for i in range( n, -1, -1 ) ]
            tail = [ ( RAIL_R * math.cos( math.pi / 2 * i / n ), length + RAIL_R * math.sin( math.pi / 2 * i / n ) ) for i in range( 0, n + 1 ) ]
            prof = [ ( max( rr, 0.0 ), tt ) for rr, tt in head ][:-1] + prof + [ ( max( rr, 0.0 ), tt ) for rr, tt in tail ][1:]
        P.lathe_axis( self.m, start, axis, prof, STEEL, sides=sides )
        if not cfg["dome"]:
            e1, e2 = P.perp( axis )
            ring0 = [ start + e1 * RAIL_R * math.cos( 2 * math.pi * i / sides ) + e2 * RAIL_R * math.sin( 2 * math.pi * i / sides )
                      for i in range( sides ) ]
            self.card( STEEL, ring0, -axis )
            self.card( STEEL, [ p + axis * length for p in ring0 ], axis )
        if cfg["ring"]:
            for j in range( 2, bays, 2 ):
                c = v3( xc, ys[j], k( ys[j] ) + RAIL_DZ )
                P.lathe_axis( self.m, c, axis, [ ( RAIL_R, -0.5 ), ( RAIL_R + 0.16, -0.34 ), ( RAIL_R + 0.16, 0.34 ), ( RAIL_R, 0.5 ) ],
                              STEEL, sides=sides )

    def build( self, turn=True ):
        self.treads()
        self.kerbs()
        self.sides()
        self.end_wall()
        for rail, sx in zip( self.rails, ( -1.0, 1.0 ) ):
            if rail:
                self.balustrade( sx )
        m = self.m
        m.uv_source_name = self.name          # one UV origin for all three LODs, so the textures don't shift when they switch
        if turn:
            turn_to_plan( m )
        R.configure( m )
        return m


# ---------------------------------------------------------------------------------------------------------------------

def weld_obj( path ):
    """ K.write_obj gives every polygon its own vertex records; the lobby's OBJ (the BEFORE) shares them. Merge identical
    position, UV and normal records so the two count the same way. """
    lines = Path( path ).read_text().split( "\n" )
    tables = { "v": {}, "vt": {}, "vn": {} }
    keep = { "v": [], "vt": [], "vn": [] }
    remap = { "v": {}, "vt": {}, "vn": {} }
    counts = { "v": 0, "vt": 0, "vn": 0 }
    heads, body = [], []
    for line in lines:
        tag = line.split( " ", 1 )[0]
        if tag in tables:
            counts[tag] += 1
            if line not in tables[tag]:
                tables[tag][line] = len( tables[tag] ) + 1
                keep[tag].append( line )
            remap[tag][counts[tag]] = tables[tag][line]
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


def write_vmdl( path, files, paints, model ):
    """ A model with one render mesh per LOD, and no physics (the generator's own collision stays). """
    remaps = ",\n".join( f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{model.material_overrides[p]}" }}' for p in sorted( paints ) )
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{MODEL_RES}/{f}" import_translation = [ 0.0, 0.0, 0.0 ] '
        'import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" '
        'align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] } }'
        for i, f in enumerate( files ) )
    groups = ",\n".join( f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {LOD_THRESHOLDS[i]:.1f} meshes = [ "lod{i}" ] }}'
                         for i in range( len( files ) ) )
    text = ( "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
             "// Generated by Sources/ReefHall/stairs-v1/stairs.py\n"
             "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
             "\t\t\t{\n\t\t\t\t_class = \"MaterialGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n"
             "\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n"
             + remaps + "\n\t\t\t\t\t\t]\n\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n\t\t\t\t\t},\n"
             "\t\t\t\t]\n\t\t\t},\n"
             "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + meshes + "\n\t\t\t\t]\n\t\t\t},\n"
             "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + groups + "\n\t\t\t\t]\n\t\t\t},\n"
             "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n" )
    K.write_text( path, text )


def tri_count( model ):
    return sum( len( p ) - 2 for polys in model.polygons.values() for p, _ in polys )


def degenerate( model, eps=1e-6 ):
    """ Triangles of (almost) no area: the fan triangulation of a polygon with a repeated corner makes them. """
    bad = 0
    for polys in model.polygons.values():
        for pts, _ in polys:
            for i in range( 1, len( pts ) - 1 ):
                if np.linalg.norm( np.cross( pts[i] - pts[0], pts[i + 1] - pts[0] ) ) < eps:
                    bad += 1
    return bad


def build_all( write=False, names=None ):
    stats = {}
    for name, spec in VARIANTS.items():
        if names and name not in names:
            continue
        files, paints, first = [], set(), None
        stats[name] = {}
        for lod in ( 0, 1, 2 ):
            model = Flight( name, lod=lod, **spec ).build()
            first = first or model
            paints |= set( model.polygons )
            obj = f"{name}_lod{lod}"
            if write:
                MODEL_DIR.mkdir( parents=True, exist_ok=True )
                tris = K.write_obj( MODEL_DIR / f"{obj}.obj", model, obj )
                weld_obj( MODEL_DIR / f"{obj}.obj" )
            else:
                tris = tri_count( model )
            files.append( f"{obj}.obj" )
            stats[name][lod] = { "triangles": tris, "degenerate": degenerate( model ) }
        if write:
            write_vmdl( MODEL_DIR / f"{name}.vmdl", files, paints, first )
    return stats


if __name__ == "__main__":
    print( build_all( write="--write" in sys.argv ) )
