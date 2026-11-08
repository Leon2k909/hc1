"""Reef Hall's two curved Rotunda flights as standalone models (Sources/ReefHall/rotunda-stairs-v1, 2026-11-06).

The old flights (Tools/reefhall_map.py round_stair() + sloped_arc_railing()) were 26 plain wedge blocks each (the floor
material on top, the dark wall material on every side), a flat 0.15 in brass strip lying on each tread, and a rail of
2.4 in square gunmetal posts with one 8-sided tube and two thin bars between them. The new flight is the same closed-string
stair as the approved straight lobby/control stairs (Sources/ReefHall/stairs-v1), bent round the Rotunda: same band
(r 480..600), same angles, same 26 risers of 8 in, same collision (the generator keeps its step hulls and rail hulls):

  * wedge treads in the floor's own slate finish, one slab per tread, with a 0.6 in chamfered nosing that overhangs a
    recessed riser by 1 in and a brass anti-slip strip let into the tread;
  * two 4 in kerbs (closed strings) that spiral up with the flight; the faces you see from the Rotunda floor and from
    under the balcony have a gunmetal plinth, a recessed concrete panel and a gunmetal stringer band; the outer kerb stops
    where the old outer rail stopped, 4 steps below the top, where the flight opens onto the balcony;
  * a closed end wall at the head, with a plinth and two reveals;
  * the approved glass balustrade of the straight stairs (stainless base shoe, 12 mm glass bays, round posts with collar
    and cup, glass clamps with screws, a 2 in round handrail with splice rings and domed ends) wound on the helix:
    full length on the inner side (r 482), 22 steps on the outer side (r 598), like the old rails.

Existing Reef Hall materials only (rh_floor, rh_wall_dark, rh_gunmetal, rh_brass, rh_steel, rh_black, rh_glass).

The models are drawn in the generator's plan frame round the Rotunda's centre (the origin), so a ModelRenderer at world
( 0, 0, 0 ) with no rotation puts them right. Two models, one per flight ( the NW flight is the NE one mirrored ), each with
three LODs and no physics.

Run:  python rotunda_stairs.py [--write]    without --write it only builds and counts.
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
import stairs as S           # noqa: E402  ( the straight stairs: constants, LOD settings, OBJ and vmdl writers )

MODEL_DIR = S.MODEL_DIR
STEPS, H = 26, 208.0
KERB, UNDERCUT, LIP, CHAMFER, PLINTH, BAND, RECESS = S.KERB, S.UNDERCUT, S.LIP, S.CHAMFER, S.PLINTH, S.BAND, S.RECESS
RAIL_DZ, RAIL_R = S.RAIL_DZ, S.RAIL_R
GLASS_T, GLASS_GAP, GLASS_Z0, GLASS_Z1, SHOE_Z, CLAMP_DZ = S.GLASS_T, S.GLASS_GAP, S.GLASS_Z0, S.GLASS_Z1, S.SHOE_Z, S.CLAMP_DZ
LODS = S.LODS
FLOOR, WALL, GUN, BRASS, STEEL, GLASS, BLACK = S.FLOOR, S.WALL, S.GUN, S.BRASS, S.STEEL, S.GLASS, S.BLACK
UP = S.UP
OPEN = 22                                  # the outer rail and kerb stop here, 4 steps under the top (the old outer rail did)
RAIL_STEP = { 0: 1, 1: 2, 2: 3 }           # steps per handrail chord
SHOE_STEP = { 0: 1, 1: 1, 2: 2 }

FLIGHTS = { "rotunda_stair_ne": R.STAIRS[0], "rotunda_stair_nw": R.STAIRS[1] }      # ( foot, top ) angles in degrees


def v3( x, y, z ):
    return np.array( ( x, y, z ), float )


class Spiral:
    def __init__( self, name, a_foot, a_top, lod ):
        self.name, self.a_foot, self.a_top, self.lod, self.cfg = name, a_foot, a_top, lod, LODS[lod]
        self.r0, self.r1 = R.STAIR_BAND
        self.rm = 0.5 * ( self.r0 + self.r1 )
        self.da = ( a_top - a_foot ) / STEPS                   # degrees per step, signed
        self.s = 1.0 if a_top > a_foot else -1.0
        self.h = H / STEPS
        self.m = K.Model()

    # ----- the helix --------------------------------------------------------------------------------------------------
    def ang( self, u ):
        return math.radians( self.a_foot + u * self.da )

    def at( self, u, r, z ):
        """ The point at step parameter u (a step's nose is at an integer), radius r, absolute height z. """
        a = self.ang( u )
        return v3( r * math.cos( a ), r * math.sin( a ), z )

    def nose( self, u ):
        """ The nose line: through every tread's nose, h at the foot, rising with the flight. """
        return ( u + 1.0 ) * self.h

    def on( self, u, r, dz=0.0 ):
        return self.at( u, r, self.nose( u ) + dz )

    def rad( self, u ):
        a = self.ang( u )
        return v3( math.cos( a ), math.sin( a ), 0.0 )

    def tang( self, u ):
        a = self.ang( u )
        return self.s * v3( -math.sin( a ), math.cos( a ), 0.0 )

    def u_of( self, inches, r ):
        """ A length along the arc at radius r, in steps. """
        return inches / ( r * math.radians( abs( self.da ) ) )

    def card( self, paint, pts, towards, uv=None ):
        P.card( self.m, paint, pts, np.asarray( towards, float ), uv=uv )

    # ----- treads, risers, noses, brass strips ------------------------------------------------------------------------
    def treads( self ):
        h, cfg, rm = self.h, self.cfg, self.rm
        ri = self.r0 + KERB
        du, uc = self.u_of( UNDERCUT, rm ), self.u_of( CHAMFER, rm )
        rstep = math.radians( abs( self.da ) )
        for k in range( STEPS ):
            zt, zp = ( k + 1 ) * h, k * h
            ro = self.r1 if k >= OPEN else self.r1 - KERB
            u_end = k + 1 + du if k < STEPS - 1 else float( STEPS )
            v0 = 0.03 + ( ( k * 0.0371 ) % 0.40 )              # a window of the 2 x 2 tile picture with no joint in it
            uvf = lambda u, r, k=k, v0=v0: ( 0.03 + ( r - ri ) / 384.0, v0 + abs( u - k ) * rstep * r / 384.0 )     # noqa: E731
            tg = self.tang( k )
            if cfg["nose"]:
                ua = k + uc
                top = [ self.at( ua, ri, zt ), self.at( ua, ro, zt ), self.at( u_end, ro, zt ), self.at( u_end, ri, zt ) ]
                uvs = [ uvf( ua, ri ), uvf( ua, ro ), uvf( u_end, ro ), uvf( u_end, ri ) ]
                self.card( FLOOR, top, UP, uvs )
                cham = [ self.at( k, ri, zt - CHAMFER ), self.at( k, ro, zt - CHAMFER ), self.at( ua, ro, zt ), self.at( ua, ri, zt ) ]
                self.card( FLOOR, cham, -tg + UP, [ uvf( k, ri ), uvf( k, ro ), uvf( ua, ro ), uvf( ua, ri ) ] )
                front = [ self.at( k, ri, zt - LIP ), self.at( k, ro, zt - LIP ), self.at( k, ro, zt - CHAMFER ), self.at( k, ri, zt - CHAMFER ) ]
                self.card( FLOOR, front, -tg, [ uvf( k + 0.02 * 0, r ) for r in ( ri, ro, ro, ri ) ] )
                kd = k + du
                under = [ self.at( k, ri, zt - LIP ), self.at( k, ro, zt - LIP ), self.at( kd, ro, zt - LIP ), self.at( kd, ri, zt - LIP ) ]
                self.card( WALL, under, -UP )
                riser = [ self.at( kd, ri, zp ), self.at( kd, ro, zp ), self.at( kd, ro, zt - LIP ), self.at( kd, ri, zt - LIP ) ]
                self.card( WALL, riser, -self.tang( kd ) )
            else:
                top = [ self.at( k, ri, zt ), self.at( k, ro, zt ), self.at( u_end, ro, zt ), self.at( u_end, ri, zt ) ]
                self.card( FLOOR, top, UP, [ uvf( p, r ) for p, r in ( ( k, ri ), ( k, ro ), ( u_end, ro ), ( u_end, ri ) ) ] )
                riser = [ self.at( k, ri, zp ), self.at( k, ro, zp ), self.at( k, ro, zt ), self.at( k, ri, zt ) ]
                self.card( WALL, riser, -tg )
            if cfg["brass"]:
                ua, ub = k + self.u_of( 0.9, rm ), k + self.u_of( 3.0, rm )
                ue = self.u_of( 0.25, rm )
                x0, x1, bz = ri + 1.0, ro - 1.0, zt + 0.2
                self.card( BRASS, [ self.at( ua, x0, zt ), self.at( ua, x1, zt ), self.at( ua + ue, x1, bz ), self.at( ua + ue, x0, bz ) ], -tg + UP )
                self.card( BRASS, [ self.at( ua + ue, x0, bz ), self.at( ua + ue, x1, bz ), self.at( ub - ue, x1, bz ), self.at( ub - ue, x0, bz ) ], UP )
                self.card( BRASS, [ self.at( ub - ue, x0, bz ), self.at( ub - ue, x1, bz ), self.at( ub, x1, zt ), self.at( ub, x0, zt ) ], tg + UP )

    # ----- the kerbs (closed strings) ---------------------------------------------------------------------------------
    def kerb( self, inner ):
        h = self.h
        ra, rb = ( self.r0, self.r0 + KERB ) if inner else ( self.r1 - KERB, self.r1 )
        rf = rb if inner else ra                               # the face that looks at the treads
        toward = 1.0 if inner else -1.0                        # ... and the way it looks, along the radius
        u_end = STEPS - 1 if inner else OPEN
        for u in range( u_end ):
            self.card( GUN, [ self.at( u, ra, self.nose( u ) ), self.at( u + 1, ra, self.nose( u + 1 ) ),
                              self.at( u + 1, rb, self.nose( u + 1 ) ), self.at( u, rb, self.nose( u ) ) ], UP )
        if inner:
            self.card( GUN, [ self.at( STEPS - 1, ra, H ), self.at( STEPS, ra, H ), self.at( STEPS, rb, H ), self.at( STEPS - 1, rb, H ) ], UP )
        self.card( GUN, [ self.at( 0, ra, 0 ), self.at( 0, rb, 0 ), self.at( 0, rb, h ), self.at( 0, ra, h ) ], -self.tang( 0 ) )
        du = self.u_of( UNDERCUT, self.rm )
        for u in range( u_end ):
            zt = ( u + 1 ) * h
            face = [ self.at( u, rf, zt ), self.at( u + 1 + du, rf, zt ), self.at( u + 1 + du, rf, zt + h ), self.at( u + 1, rf, zt + h ) ]
            self.card( WALL, face, toward * self.rad( u + 0.5 ) )

    # ----- the outer faces: plinth, recessed panel, stringer band ------------------------------------------------------
    def sides( self, inner ):
        h = self.h
        out = -1.0 if inner else 1.0                           # the face looks to the Rotunda's centre (inner) or away from it
        Rf = self.r0 if inner else self.r1
        Rr = Rf - out * RECESS
        last = STEPS if inner else OPEN
        zk = lambda u: min( ( u + 1.0 ) * h, H )               # noqa: E731  the kerb top: the nose line, flat over the top step
        for u in range( last ):
            zA, zB = zk( u ), zk( u + 1 )
            o = out * self.rad( u + 0.5 )
            if u == 0:
                self.card( GUN, [ self.at( 0, Rf, 0 ), self.at( 1, Rf, 0 ), self.at( 1, Rf, zB ), self.at( 0, Rf, zA ) ], o )
                continue
            self.card( GUN, [ self.at( u, Rf, 0 ), self.at( u + 1, Rf, 0 ), self.at( u + 1, Rf, PLINTH ), self.at( u, Rf, PLINTH ) ], o )
            self.card( GUN, [ self.at( u, Rr, PLINTH ), self.at( u, Rf, PLINTH ), self.at( u + 1, Rf, PLINTH ), self.at( u + 1, Rr, PLINTH ) ], UP )
            self.card( WALL, [ self.at( u, Rr, PLINTH ), self.at( u + 1, Rr, PLINTH ), self.at( u + 1, Rr, zB - BAND ), self.at( u, Rr, zA - BAND ) ], o )
            self.card( GUN, [ self.at( u, Rf, zA - BAND ), self.at( u + 1, Rf, zB - BAND ), self.at( u + 1, Rf, zB ), self.at( u, Rf, zA ) ], o )
            self.card( GUN, [ self.at( u, Rr, zA - BAND ), self.at( u + 1, Rr, zB - BAND ), self.at( u + 1, Rf, zB - BAND ), self.at( u, Rf, zA - BAND ) ], -UP )
        if not inner:
            # past the outer kerb the treads run out to the edge: each step's flank, a plinth under a plain wall; the recess ends in a cap
            zc = zk( OPEN )
            self.card( WALL, [ self.at( OPEN, Rr, PLINTH ), self.at( OPEN, Rf, PLINTH ), self.at( OPEN, Rf, zc ), self.at( OPEN, Rr, zc ) ], -self.tang( OPEN ) )
            for k in range( OPEN, STEPS ):
                zt = ( k + 1 ) * h
                o = self.rad( k + 0.5 )
                self.card( GUN, [ self.at( k, Rf, 0 ), self.at( k + 1, Rf, 0 ), self.at( k + 1, Rf, PLINTH ), self.at( k, Rf, PLINTH ) ], o )
                self.card( WALL, [ self.at( k, Rf, PLINTH ), self.at( k + 1, Rf, PLINTH ), self.at( k + 1, Rf, zt ), self.at( k, Rf, zt ) ], o )

    # ----- the end wall at the head of the flight ---------------------------------------------------------------------
    def end_wall( self ):
        U, tg, r0, r1 = float( STEPS ), self.tang( STEPS ), self.r0, self.r1
        self.card( GUN, [ self.at( U, r0, 0 ), self.at( U, r1, 0 ), self.at( U, r1, PLINTH ), self.at( U, r0, PLINTH ) ], tg )
        edges = [ r0 ]
        if self.cfg["reveals"]:
            for c in ( self.rm - 25.0, self.rm + 25.0 ):
                edges += [ c - 0.5, c + 0.5 ]
        edges.append( r1 )
        for i in range( 0, len( edges ), 2 ):
            self.card( WALL, [ self.at( U, edges[i], PLINTH ), self.at( U, edges[i + 1], PLINTH ), self.at( U, edges[i + 1], H ), self.at( U, edges[i], H ) ], tg )
        if self.cfg["reveals"]:
            ub = U - self.u_of( RECESS, self.rm )
            for c in ( self.rm - 25.0, self.rm + 25.0 ):
                a, b = c - 0.5, c + 0.5
                self.card( WALL, [ self.at( ub, a, PLINTH ), self.at( ub, b, PLINTH ), self.at( ub, b, H ), self.at( ub, a, H ) ], tg )
                for x, s in ( ( a, 1.0 ), ( b, -1.0 ) ):
                    self.card( WALL, [ self.at( ub, x, PLINTH ), self.at( U, x, PLINTH ), self.at( U, x, H ), self.at( ub, x, H ) ], s * self.rad( U ) )
                self.card( WALL, [ self.at( ub, a, PLINTH ), self.at( ub, b, PLINTH ), self.at( U, b, PLINTH ), self.at( U, a, PLINTH ) ], UP )

    # ----- the balustrade ---------------------------------------------------------------------------------------------
    def balustrade( self, rc, u_lo, u_hi ):
        cfg, h, lod = self.cfg, self.h, self.lod
        step_len = rc * math.radians( abs( self.da ) )               # horizontal length of one step along the rail
        slope = h / step_len
        run = ( u_hi - u_lo ) * step_len
        bays = max( 3, int( round( math.hypot( run, ( u_hi - u_lo ) * h ) / 44.9 ) ) )
        us = [ u_lo + j * ( u_hi - u_lo ) / bays for j in range( bays + 1 ) ]
        bay_u = ( u_hi - u_lo ) / bays
        # the base shoe, wound on the helix: sampled every SHOE_STEP steps
        if cfg["shoe"] == "full":
            prof = [ ( -1.7, 0.0 ), ( -1.7, 2.7 ), ( -1.35, SHOE_Z ), ( -0.38, SHOE_Z ), ( -0.38, S.GLASS_Z0 ), ( 0.38, S.GLASS_Z0 ),
                     ( 0.38, SHOE_Z ), ( 1.35, SHOE_Z ), ( 1.7, 2.7 ), ( 1.7, 0.0 ) ]
            kinds = [ ( STEEL, ( -1, 0 ) ), ( STEEL, ( -0.7, 0.7 ) ), ( STEEL, ( 0, 1 ) ), ( BLACK, ( 1, 0 ) ), ( BLACK, ( 0, 1 ) ),
                      ( BLACK, ( -1, 0 ) ), ( STEEL, ( 0, 1 ) ), ( STEEL, ( 0.7, 0.7 ) ), ( STEEL, ( 1, 0 ) ) ]
            blocks = [ [ prof[0], prof[1], prof[2], prof[3], ( -0.38, 0.0 ) ], [ ( -0.38, 0.0 ), prof[4], prof[5], ( 0.38, 0.0 ) ],
                       [ ( 0.38, 0.0 ), prof[6], prof[7], prof[8], prof[9] ] ]
        else:
            prof = [ ( -1.7, 0.0 ), ( -1.7, SHOE_Z ), ( 1.7, SHOE_Z ), ( 1.7, 0.0 ) ]
            kinds = [ ( STEEL, ( -1, 0 ) ), ( STEEL, ( 0, 1 ) ), ( STEEL, ( 1, 0 ) ) ]
            blocks = [ prof ]
        n_seg = max( 1, int( round( ( u_hi - u_lo ) / SHOE_STEP[lod] ) ) )
        seg = [ u_lo + j * ( u_hi - u_lo ) / n_seg for j in range( n_seg + 1 ) ]
        for ua, ub in zip( seg[:-1], seg[1:] ):
            um = 0.5 * ( ua + ub )
            for ( a, b ), ( paint, n ) in zip( zip( prof[:-1], prof[1:] ), kinds ):
                self.card( paint, [ self.on( ua, rc + a[0], a[1] ), self.on( ub, rc + a[0], a[1] ), self.on( ub, rc + b[0], b[1] ),
                                    self.on( ua, rc + b[0], b[1] ) ], n[0] * self.rad( um ) + v3( 0, 0, n[1] ) )
        for u, s in ( ( u_lo, -1.0 ), ( u_hi, 1.0 ) ):
            for blk in blocks:
                self.card( STEEL, [ self.on( u, rc + x, z ) for x, z in blk ], s * self.tang( u ) )
        # the glass: one flat panel per bay between two posts, its ends on the arc pushed out by half the chord's sag
        t = GLASS_T / 2
        gap = self.u_of( GLASS_GAP, rc )
        sag = rc * ( 1.0 - math.cos( 0.5 * bay_u * math.radians( abs( self.da ) ) ) )
        for j in range( bays ):
            ua, ub = us[j] + gap, us[j + 1] - gap
            rg = rc + sag / 2
            for s in ( 1.0, -1.0 ):
                self.card( GLASS, [ self.on( ua, rg + s * t, GLASS_Z0 ), self.on( ub, rg + s * t, GLASS_Z0 ), self.on( ub, rg + s * t, GLASS_Z1 ),
                                    self.on( ua, rg + s * t, GLASS_Z1 ) ], s * self.rad( 0.5 * ( ua + ub ) ) )
            self.card( GLASS, [ self.on( ua, rg - t, GLASS_Z1 ), self.on( ua, rg + t, GLASS_Z1 ), self.on( ub, rg + t, GLASS_Z1 ),
                                self.on( ub, rg - t, GLASS_Z1 ) ], UP )
            for u, s in ( ( ua, -1.0 ), ( ub, 1.0 ) ):
                self.card( GLASS, [ self.on( u, rg - t, GLASS_Z0 ), self.on( u, rg + t, GLASS_Z0 ), self.on( u, rg + t, GLASS_Z1 ),
                                    self.on( u, rg - t, GLASS_Z1 ) ], s * self.tang( u ) )
        # the posts stand upright; their base is cut down 1.5 slopes so the collar meets the sloped shoe all round
        sk = 1.5 * slope
        top = RAIL_DZ - 0.8
        if lod == 2:
            post = [ ( 0.9, SHOE_Z - sk ), ( 0.9, top - 0.2 ), ( 1.2, top ) ]
        else:
            post = [ ( 1.5, SHOE_Z - sk ), ( 1.5, SHOE_Z + sk + 0.5 ), ( 0.95, SHOE_Z + sk + 0.8 ), ( 0.9, SHOE_Z + sk + 1.0 ),
                     ( 0.9, top - 1.5 ), ( 1.2, top - 1.1 ), ( 1.2, top ) ]
        for u in us:
            p = self.at( u, rc, 0.0 )
            P.lathe( self.m, ( p[0], p[1] ), [ ( rad, self.nose( u ) + dz ) for rad, dz in post ], STEEL, sides=cfg["post_sides"], cap=STEEL )
        # the glass clamps: plates that follow the glass's edge up the slope
        if cfg["clamps"]:
            plate = self.u_of( 2.0, rc )
            for j, u in enumerate( us ):
                lo, hi = -plate, plate                          # a plate spans both glass edges at a joint
                if j == 0:
                    lo = -self.u_of( 0.9, rc )                  # the first and last posts have a panel on one side only
                if j == bays:
                    hi = self.u_of( 0.9, rc )
                for s in ( 1.0, -1.0 ):
                    for dz in CLAMP_DZ:
                        x0, x1 = rc + s * ( GLASS_T / 2 ), rc + s * ( GLASS_T / 2 + 0.3 )
                        ua, ub = u + lo, u + hi
                        hh = 3.6
                        self.card( STEEL, [ self.on( ua, x1, dz ), self.on( ub, x1, dz ), self.on( ub, x1, dz + hh ), self.on( ua, x1, dz + hh ) ],
                                   s * self.rad( u ) )
                        self.card( STEEL, [ self.on( ua, x0, dz + hh ), self.on( ua, x1, dz + hh ), self.on( ub, x1, dz + hh ), self.on( ub, x0, dz + hh ) ], UP )
                        self.card( STEEL, [ self.on( ua, x0, dz ), self.on( ua, x1, dz ), self.on( ub, x1, dz ), self.on( ub, x0, dz ) ], -UP )
                        for uu, ss in ( ( ua, -1.0 ), ( ub, 1.0 ) ):
                            self.card( STEEL, [ self.on( uu, x0, dz ), self.on( uu, x1, dz ), self.on( uu, x1, dz + hh ), self.on( uu, x0, dz + hh ) ],
                                       ss * self.tang( uu ) )
                        if cfg["screws"]:
                            um = u + 0.5 * ( lo + hi )
                            P.lathe_axis( self.m, self.on( um, x1, dz + 1.8 ), s * self.rad( um ), [ ( 0.34, 0.0 ), ( 0.34, 0.12 ) ],
                                          STEEL, sides=6, cap=STEEL )
        # the handrail: round tube chords along the helix, domed at both ends, a splice ring at every second post
        sides_n = cfg["rail_sides"]
        n_chord = max( 1, int( round( ( u_hi - u_lo ) / RAIL_STEP[lod] ) ) )
        ch = [ u_lo + j * ( u_hi - u_lo ) / n_chord for j in range( n_chord + 1 ) ]
        pts = [ self.on( u, rc, RAIL_DZ ) for u in ch ]
        for j in range( n_chord ):
            axis = pts[j + 1] - pts[j]
            length = float( np.linalg.norm( axis ) )
            axis = axis / length
            prof = [ ( RAIL_R, 0.0 ), ( RAIL_R, length ) ]
            if cfg["dome"]:
                n = cfg["dome"]
                if j == 0:
                    head = [ ( RAIL_R * math.cos( math.pi / 2 * i / n ), -RAIL_R * math.sin( math.pi / 2 * i / n ) ) for i in range( n, -1, -1 ) ]
                    prof = [ ( max( rr, 0.0 ), tt ) for rr, tt in head ][:-1] + prof
                if j == n_chord - 1:
                    tail = [ ( RAIL_R * math.cos( math.pi / 2 * i / n ), length + RAIL_R * math.sin( math.pi / 2 * i / n ) ) for i in range( 0, n + 1 ) ]
                    prof = prof + [ ( max( rr, 0.0 ), tt ) for rr, tt in tail ][1:]
            P.lathe_axis( self.m, pts[j], axis, prof, STEEL, sides=sides_n )
            if not cfg["dome"] and ( j == 0 or j == n_chord - 1 ):
                e1, e2 = P.perp( axis )
                at_end = pts[j] if j == 0 else pts[j + 1]
                ring = [ at_end + e1 * RAIL_R * math.cos( 2 * math.pi * i / sides_n ) + e2 * RAIL_R * math.sin( 2 * math.pi * i / sides_n ) for i in range( sides_n ) ]
                self.card( STEEL, ring, -axis if j == 0 else axis )
        if cfg["ring"]:
            for j in range( 2, bays, 2 ):
                c = self.on( us[j], rc, RAIL_DZ )
                ahead = self.on( us[j] + 0.02, rc, RAIL_DZ ) - self.on( us[j] - 0.02, rc, RAIL_DZ )
                ahead = ahead / np.linalg.norm( ahead )
                P.lathe_axis( self.m, c, ahead, [ ( RAIL_R, -0.5 ), ( RAIL_R + 0.16, -0.34 ), ( RAIL_R + 0.16, 0.34 ), ( RAIL_R, 0.5 ) ],
                              STEEL, sides=sides_n )

    def build( self ):
        self.treads()
        self.kerb( True )
        self.kerb( False )
        self.sides( True )
        self.sides( False )
        self.end_wall()
        edge = 0.28                                              # the rails start and stop 3 in inside the ends, like the straight ones
        self.balustrade( self.r0 + 2.0, edge, STEPS - 1 - edge )
        self.balustrade( self.r1 - 2.0, edge, OPEN - edge )
        m = self.m
        m.uv_source_name = self.name                             # one UV origin for all three LODs, so the textures don't shift when they switch
        R.configure( m )
        return m


def build_all( write=False, names=None ):
    stats = {}
    for name, ( foot, top ) in FLIGHTS.items():
        if names and name not in names:
            continue
        files, paints, first = [], set(), None
        stats[name] = {}
        for lod in ( 0, 1, 2 ):
            model = Spiral( name, foot, top, lod ).build()
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
