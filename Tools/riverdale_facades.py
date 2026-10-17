"""
Riverdale's building faces: the kit Tools/riverdale_map.py dresses the yard's buildings with (the A1 and A2 annexes, the
spawn buildings B1 and B2 and the boundary building behind them, C1 and its wings, the turbine annex and turbine blocks,
the generators, the turbine hall and the north lane's wall and pipe rack), and the materials it brings.

A building's collision stays the boxes riverdale_map builds. Their outer faces aren't drawn (painted None) and a Face
draws each in their place, the way a nuclear plant's reinforced concrete and steel-clad buildings look:
- its materials in bands up the wall: a darker concrete plinth at the foot, the cast concrete, precast string courses,
  and profiled steel cladding (its ribs drawn as geometry, 12 in apart and 1.5 in deep) over a drip flashing, with trims
  round its openings and at its corners;
- openings cut through the drawn face, so what's set into them shows: windows set back in their reveals (frames,
  mullions, glass, precast sills; lit ones with their blinds part down), doors (riverdale_parts.door) with thresholds
  and canopies, louvres (riverdale_parts.louvre), roller shutters with their slats, guides and drum housings, expansion
  joints, and the openings people walk through;
- what's fixed to it: pilasters, downpipes from the parapets' scuppers, conduit and junction boxes, cabinets, cameras.
Copings on the parapets, rooftop plant, pipe flanges and shoes, and the generator sets are here too.

Everything here is drawn only. Below head height (110 in) nothing stands more than 6 in off a wall, so nobody walks
into it (a player's capsule keeps 16 in off the wall); canopies, shutter housings and cameras are above that.

Plan coordinates: e east, n north, z up, inches. A Face's points are ( u, z, d ): u the plan coordinate along it (e on
a north or south face, n on an east or west face), z up, d out from its plane.

Its materials (EXTRA_PAINTS, EXTRA_SURFACES) are written by Tools/riverdale_materials.py with the rest:
    python Tools/riverdale_materials.py rv_fc_clad rv_fc_clad_light rv_fc_precast rv_fc_blinds painted [--out <dir>]
"""
import math

import numpy as np
from scipy import ndimage

import map_kit as K
import riverdale_materials as RM
import riverdale_parts as P
from riverdale_parts import v, card, box, unit, UP

# ---------------------------------------------------------------------------------------------------------------------
# Materials

EXTRA_PAINTS = {
    "rv_fc_glass": ( ( 34, 44, 52 ), 0.4, 0.08, 0 ),            # coated glazing: dark, reflective
    "rv_fc_frosted": ( ( 196, 210, 222 ), 0.0, 0.4, 1.0 ),      # daylight through a window, seen from inside
    "rv_fc_flashing": ( ( 112, 118, 124 ), 0.65, 0.38, 0 ),     # coated steel flashings, copings and trims
    "rv_fc_shutter": ( ( 150, 154, 154 ), 0.6, 0.42, 0 ),       # galvanised roller shutter slats
    "rv_fc_seal": ( ( 24, 24, 25 ), 0.0, 0.75, 0 ),             # joint sealant, shadow gaps
    "rv_fc_cabinet": ( ( 176, 178, 172 ), 0.2, 0.45, 0 ),       # light grey electrical cabinets and boxes
    "rv_fc_red": ( ( 168, 30, 26 ), 0.1, 0.45, 0 ),             # fire equipment
    "rv_fc_door_blue": ( ( 48, 82, 112 ), 0.25, 0.45, 0 ),      # painted steel doors
}


def cladding( seed, colour, tile=192.0, n=None ):
    """ Painted profiled steel sheet (the ribs are geometry): the paint a little mottled and chalked by the weather,
    rain streaks running down from the laps, a horizontal end lap once a tile. """
    n = n or RM.px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = RM.field( rng, n, tile )
    c = RM.lin( colour )[None, None, :] * ( 1.0 + 0.035 * nz( 2.6, 120, 10 ) + 0.012 * nz( 0.8, 1.0, 0.1 ) )[..., None]
    chalk = RM.smoothstep( 0.2, 2.2, nz( 2.4, 60, 6 ) )
    c = RM.mix( c, c * 1.12 + 0.02, chalk[..., None] * 0.35 )
    # Rain streaks: narrow, long, from scattered sources and the lap.
    src = ( rng.random( ( n, n ) ) < 0.00025 ).astype( np.float32 )
    lap = np.abs( ( z % tile ) - tile ) < 0.6
    src = np.maximum( src, lap * ( rng.random( ( n, n ) ) < 0.03 ) )
    src = ndimage.gaussian_filter( src, ( 0.4, 0.9 ), mode="wrap" ) * 5
    runs = np.clip( RM.runs_down( src, ppi, 70.0 ) * 3.0, 0, 1 ) * RM.smoothstep( -1.0, 1.0, nz( 1.4, 40, 4 ) )
    c = RM.mix( c, c * 0.74, runs[..., None] * 0.6 )
    # The end lap: a fine shadow line under a light edge.
    zt = z % tile
    edge = np.exp( -( ( zt - 0.35 ) / 0.25 ) ** 2 )
    shade = np.exp( -( ( zt - tile + 0.2 ) / 0.3 ) ** 2 )
    c *= ( 1.0 + 0.12 * edge - 0.3 * shade )[..., None]
    r = 0.46 + 0.05 * nz( 2.0, 20, 2 ) + 0.12 * runs + 0.06 * chalk
    h = 0.004 * nz( 1.0, 1, 0.1 ) + 0.03 * edge
    return np.clip( c, 0.0, 1.0 ), np.clip( r, 0.2, 0.9 ), h, ppi


def precast( seed=611, colour=( 166, 164, 158 ), tile=96.0, n=None ):
    """ Precast concrete: smooth from its steel mould, fine blowholes, a little patchy, weathered darker underneath. """
    n = n or RM.px( 1024 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = RM.field( rng, n, tile )
    c = RM.lin( colour )[None, None, :] * ( 1.0 + 0.04 * nz( 2.6, 60, 6 ) + 0.02 * nz( 1.2, 4, 0.4 ) )[..., None]
    pits = RM.smoothstep( 2.7, 3.2, nz( 0.4, 0.4, 0.06 ) )
    c = RM.mix( c, c * 0.5, pits[..., None] )
    src = ( rng.random( ( n, n ) ) < 0.00012 ).astype( np.float32 )
    src = ndimage.gaussian_filter( src, ( 0.5, 1.4 ), mode="wrap" ) * 4
    runs = np.clip( RM.runs_down( src, ppi, 30.0 ) * 4.0, 0, 1 )
    c = RM.mix( c, c * 0.78, runs[..., None] * 0.5 )
    r = np.clip( 0.78 + 0.05 * nz( 2.0, 10, 1 ) - 0.06 * runs, 0.4, 1.0 )
    h = 0.02 * nz( 1.4, 6, 0.3 ) - 0.06 * pits
    return c, r, h, ppi


def blinds( seed=621, tile=24.0, n=None ):
    """ Venetian blinds seen from outside: off-white slats an inch apart, each shaded across its curve, a few out of
    line. """
    n = n or RM.px( 256 )
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = RM.field( rng, n, tile )
    slat = ( z % 1.0 )
    shade = 0.78 + 0.3 * np.sin( slat * math.pi ) ** 0.6
    gap = RM.smoothstep( 0.9, 0.97, slat )
    c = RM.lin( ( 214, 210, 198 ) )[None, None, :] * ( shade * ( 1.0 - 0.75 * gap ) )[..., None]
    c *= ( 1.0 + 0.04 * nz( 2.0, 12, 1 ) )[..., None]
    r = np.full( ( n, n ), 0.55, np.float32 )
    h = 0.04 * np.sin( slat * math.pi ) - 0.05 * gap
    return c, r, h, ppi


EXTRA_SURFACES = {
    "rv_fc_clad": ( 192.0, 0.0, lambda: cladding( 601, ( 78, 92, 106 ) ) ),          # blue-grey cladding
    "rv_fc_clad_light": ( 192.0, 0.0, lambda: cladding( 602, ( 188, 190, 186 ) ) ),  # light grey cladding
    "rv_fc_precast": ( 96.0, 0.0, lambda: precast() ),
    "rv_fc_blinds": ( 24.0, 0.0, lambda: blinds() ),
}

CLAD, CLAD_LIGHT, PRECAST, FLASH = "rv_fc_clad", "rv_fc_clad_light", "rv_fc_precast", "rv_fc_flashing"
SAME = object()
HEAD = 110.0         # below this, nothing stands more than WALL_REACH off a wall
WALL_REACH = 6.0


def room_paint( room, lit=False ):
    """ riverdale_materials' room behind glass (an office, a plant room, a corridor, on Belltower's window shader), or
    plain glass if it hasn't one. """
    rooms = getattr( RM, "ROOMS", {} )
    if room and room in rooms:
        return f"rv_window_{room}{'_lit' if lit else ''}"
    return "rv_window_lit" if lit else "rv_fc_glass"


def has_surface( name ):
    return name in getattr( RM, "SURFACES", {} )


# ---------------------------------------------------------------------------------------------------------------------
# A building's face

class Face:
    """ One flat outer face of a building: normal '+e', '-e', '+n' or '-n', its plane at c, running u0..u1 along it and
    z0..z1 up, drawn in paint (zone() puts other bands on it). Openings and fittings are added, then finish() draws it:
    the plane round the holes, the cladding's ribs, then everything that waited for the holes to be known. """

    def __init__( self, m, normal, c, u0, u1, z0, z1, paint="rv_wall" ):
        self.m = m
        self.axis = normal[1]
        self.s = 1.0 if normal[0] == "+" else -1.0
        self.front = normal
        self.back = ( "-" if self.s > 0 else "+" ) + self.axis
        self.c = float( c )
        self.u0, self.u1 = sorted( ( float( u0 ), float( u1 ) ) )
        self.z0, self.z1 = float( z0 ), float( z1 )
        self.out = v( self.s, 0, 0 ) if self.axis == "e" else v( 0, self.s, 0 )
        self.right = np.cross( UP, self.out )
        self.uvec = v( 0, 1, 0 ) if self.axis == "e" else v( 1, 0, 0 )
        self.ends = ( "-n", "+n" ) if self.axis == "e" else ( "-e", "+e" )
        self.zones = [ ( self.z0, self.z1, paint, False ) ]
        self.holes = []          # ( u0, u1, z0, z1, trim )
        self.later = []
        self.corner_trims = ( False, False )

    # Points and simple shapes -----------------------------------------------------------------------------------------

    def p( self, u, z, d=0.0 ):
        if self.axis == "e":
            return v( self.c + self.s * d, u, z )
        return v( u, self.c + self.s * d, z )

    def paints( self, front, top=SAME, bottom=SAME, ends=SAME, back=None ):
        """ A box's paints by what they are to the face: its front, top, bottom, ends (along u) and back. """
        def pick( x ):
            return front if x is SAME else x
        return { "default": front, "+z": pick( top ), "-z": pick( bottom ), self.ends[0]: pick( ends ), self.ends[1]: pick( ends ),
                 self.back: back }

    def box( self, u0, u1, z0, z1, d0, d1, paint, back=False ):
        """ A box standing out of the face (d0..d1 out), its back not drawn unless back. """
        paints = dict( paint ) if isinstance( paint, dict ) else self.paints( paint )
        if not back:
            paints[self.back] = None
        self.m.box( self.p( u0, z0, d0 ), self.p( u1, z1, d1 ), paints )

    def rect( self, paint, u0, u1, z0, z1, d=0.0, uv=None ):
        if u1 - u0 < 1e-3 or z1 - z0 < 1e-3:
            return
        if uv is not None and np.dot( self.right, self.uvec ) < 0:
            uv = [ uv[1], uv[0], uv[3], uv[2] ]
        card( self.m, paint, [ self.p( u0, z0, d ), self.p( u1, z0, d ), self.p( u1, z1, d ), self.p( u0, z1, d ) ], self.out,
              uv=uv )

    def rect_in( self, paint, u0, u1, z0, z1, d=0.0 ):
        """ A rectangle facing into the building. """
        if u1 - u0 < 1e-3 or z1 - z0 < 1e-3:
            return
        card( self.m, paint, [ self.p( u0, z0, d ), self.p( u1, z0, d ), self.p( u1, z1, d ), self.p( u0, z1, d ) ], -self.out )

    def reveal( self, u0, u1, z0, z1, depth, paint, sides=( True, True, True, True ), d0=0.0 ):
        """ The sides of a hole from d0 in back to depth: left (u0), right (u1), bottom, top. """
        p = self.p
        a, b = -d0, -depth
        if sides[0]:
            card( self.m, paint, [ p( u0, z0, a ), p( u0, z1, a ), p( u0, z1, b ), p( u0, z0, b ) ], self.uvec )
        if sides[1]:
            card( self.m, paint, [ p( u1, z0, a ), p( u1, z0, b ), p( u1, z1, b ), p( u1, z1, a ) ], -self.uvec )
        if sides[2]:
            card( self.m, paint, [ p( u0, z0, a ), p( u0, z0, b ), p( u1, z0, b ), p( u1, z0, a ) ], UP )
        if sides[3]:
            card( self.m, paint, [ p( u0, z1, a ), p( u1, z1, a ), p( u1, z1, b ), p( u0, z1, b ) ], -UP )

    # Zones, holes and what's free of them ------------------------------------------------------------------------------

    def zone( self, z0, z1, paint, ribs=False ):
        """ A band of the face in another material (the last one given wins where they overlap); ribs for profiled
        cladding. """
        self.zones.append( ( max( self.z0, z0 ), min( self.z1, z1 ), paint, ribs ) )

    def segments( self ):
        """ ( z0, z1, paint, ribs ) up the face, the zones resolved. """
        cuts = sorted( { z for zone in self.zones for z in zone[:2] } )
        out = []
        for a, b in zip( cuts, cuts[1:] ):
            if b - a < 1e-6:
                continue
            mid = ( a + b ) / 2
            zone = [ z for z in self.zones if z[0] <= mid <= z[1] ][-1]
            if out and out[-1][2:] == zone[2:] and abs( out[-1][1] - a ) < 1e-6:
                out[-1] = ( out[-1][0], b, *zone[2:] )
            else:
                out.append( ( a, b, *zone[2:] ) )
        return out

    def paint_at( self, z ):
        return [ zone for zone in self.zones if zone[0] <= z <= zone[1] ][-1][2]

    def ribbed_at( self, z0, z1 ):
        return any( ribs and a < z1 and b > z0 for a, b, _, ribs in self.segments() )

    def hole( self, u0, u1, z0, z1, trim=True ):
        """ A hole in the drawn face (the box behind still collides): what's set into it is drawn by its feature. """
        self.holes.append( ( min( u0, u1 ), max( u0, u1 ), z0, z1, trim ) )

    def exclude( self, u0, u1, z0, z1 ):
        """ A part of the face something else covers (another building against it): not drawn, nothing set in it. """
        self.hole( u0, u1, z0, z1, trim=False )

    @staticmethod
    def gaps( a0, a1, blocks, least=0.25 ):
        out, at = [], a0
        for b0, b1 in sorted( blocks ):
            if b1 <= at or b0 >= a1:
                continue
            if b0 > at:
                out.append( ( at, b0 ) )
            at = max( at, b1 )
        if at < a1:
            out.append( ( at, a1 ) )
        return [ ( x, y ) for x, y in out if y - x > least ]

    def free_u( self, ua, ub, za, zb, pad=0.0 ):
        """ The stretches of ua..ub clear of every hole that reaches into za..zb. """
        return self.gaps( ua, ub, [ ( h[0] - pad, h[1] + pad ) for h in self.holes if h[2] - pad < zb and h[3] + pad > za ] )

    def free_z( self, za, zb, ua, ub, pad=0.0 ):
        return self.gaps( za, zb, [ ( h[2] - pad, h[3] + pad ) for h in self.holes if h[0] - pad < ub and h[1] + pad > ua ] )

    # Drawing the face -------------------------------------------------------------------------------------------------

    def plane( self, paint, ua, ub, za, zb, d=0.0 ):
        """ The face's plane over ua..ub, za..zb, round the holes. """
        hs = [ h for h in self.holes if h[0] < ub and h[1] > ua and h[2] < zb and h[3] > za ]
        zs = sorted( { za, zb } | { min( max( h[k], za ), zb ) for h in hs for k in ( 2, 3 ) } )
        for a, b in zip( zs, zs[1:] ):
            if b - a < 1e-6:
                continue
            mid = ( a + b ) / 2
            for u0, u1 in self.gaps( ua, ub, [ ( h[0], h[1] ) for h in hs if h[2] < mid < h[3] ], least=1e-3 ):
                self.rect( paint, u0, u1, a, b, d )

    def ribs( self, za, zb, paint, pitch=12.0, crest=3.0, web=2.0, depth=1.5 ):
        """ Trapezoidal sheeting's ribs over za..zb, on world-aligned centres, stopping 3 in short of holes (their trims
        cover the ends). """
        half = crest / 2 + web
        start = math.ceil( ( self.u0 + half + 3.5 ) / pitch ) * pitch
        for uc in np.arange( start, self.u1 - half - 3.5 + 1e-6, pitch ):
            for a, b in self.free_z( za, zb, uc - half, uc + half, pad=3.0 ):
                self.rib( uc, a, b, paint, crest, web, depth )

    def rib( self, uc, za, zb, paint, crest=3.0, web=2.0, depth=1.5 ):
        p = self.p
        c0, c1 = uc - crest / 2, uc + crest / 2
        w0, w1 = c0 - web, c1 + web
        card( self.m, paint, [ p( c0, za, depth ), p( c1, za, depth ), p( c1, zb, depth ), p( c0, zb, depth ) ], self.out )
        card( self.m, paint, [ p( w0, za, 0 ), p( c0, za, depth ), p( c0, zb, depth ), p( w0, zb, 0 ) ],
              self.out * web - self.uvec * depth )
        card( self.m, paint, [ p( c1, za, depth ), p( w1, za, 0 ), p( w1, zb, 0 ), p( c1, zb, depth ) ],
              self.out * web + self.uvec * depth )
        for z, sg in ( ( za, -1 ), ( zb, 1 ) ):
            card( self.m, paint, [ p( w0, z, 0 ), p( c0, z, depth ), p( c1, z, depth ), p( w1, z, 0 ) ], UP * sg )

    def ledge( self, a, b, z0, z1, d, paint, slope=1.2, ends=True ):
        """ A run standing d out from z0 to z1, its top weathered back to the wall. """
        z1s = z1 - slope
        self.box( a, b, z0, z1s, 0, d, self.paints( paint, top=None, bottom=None if z0 <= self.z0 else paint ) )
        p = self.p
        card( self.m, paint, [ p( a, z1s, d ), p( b, z1s, d ), p( b, z1, 0 ), p( a, z1, 0 ) ], self.out * slope + UP * d )
        if ends:
            card( self.m, paint, [ p( a, z1s, 0 ), p( a, z1, 0 ), p( a, z1s, d ) ], -self.uvec )
            card( self.m, paint, [ p( b, z1s, 0 ), p( b, z1s, d ), p( b, z1, 0 ) ], self.uvec )

    def drip( self, a, b, z, d=2.8, paint=FLASH ):
        """ A drip flashing across a ledge or the foot of cladding: sloped top, front lip and underside. """
        p = self.p
        card( self.m, paint, [ p( a, z, d ), p( b, z, d ), p( b, z + 2.5, 0 ), p( a, z + 2.5, 0 ) ], self.out * 2.5 + UP * d )
        card( self.m, paint, [ p( a, z - 1.2, d ), p( b, z - 1.2, d ), p( b, z, d ), p( a, z, d ) ], self.out )
        card( self.m, paint, [ p( a, z - 1.2, 0 ), p( b, z - 1.2, 0 ), p( b, z - 1.2, d ), p( a, z - 1.2, d ) ], -UP )
        for u, sg in ( ( a, -1 ), ( b, 1 ) ):
            card( self.m, paint, [ p( u, z - 1.2, 0 ), p( u, z - 1.2, d ), p( u, z, d ), p( u, z + 2.5, 0 ) ], self.uvec * sg )

    def trim( self, u0, u1, z0, z1, w=3.0, d=2.2, paint=FLASH, bottom=True ):
        """ A flashing frame round a hole in cladding. """
        self.box( u0 - w, u0, z0 - ( w if bottom else 0 ), z1 + w, 0, d, paint )
        self.box( u1, u1 + w, z0 - ( w if bottom else 0 ), z1 + w, 0, d, paint )
        self.box( u0, u1, z1, z1 + w, 0, d, paint )
        if bottom:
            self.box( u0, u1, z0 - w, z0, 0, d, paint )

    def finish( self ):
        segs = self.segments()
        for za, zb, paint, ribs in segs:
            self.plane( paint, self.u0, self.u1, za, zb )
        for k, ( za, zb, paint, ribs ) in enumerate( segs ):
            if not ribs:
                continue
            self.ribs( za, zb, paint )
            # Flashings where cladding starts over concrete, and a cap strip where it stops under it.
            if za > self.z0 + 0.5:
                for a, b in self.free_u( self.u0 - 3, self.u1 + 3, za - 2, za + 3 ):
                    self.drip( a, b, za )
            if zb < self.z1 - 0.5:
                for a, b in self.free_u( self.u0 - 3, self.u1 + 3, zb - 3, zb ):
                    self.box( a, b, zb - 3, zb, 0, 2.4, FLASH )
            for side, u in enumerate( ( self.u0, self.u1 ) ):
                if self.corner_trims[side] is None:
                    continue
                ext = 2.4 if self.corner_trims[side] else 0.0
                a, b = ( u - ext, u + 3.5 ) if side == 0 else ( u - 3.5, u + ext )
                for z0, z1 in self.free_z( za, zb, a, b ):
                    self.box( a, b, z0, z1, 0, 2.4, FLASH )
        for h in self.holes:
            if h[4] and self.ribbed_at( h[2], h[3] ):
                self.trim( h[0], h[1], h[2], h[3], bottom=h[2] > self.z0 + 0.5 )
        for draw in self.later:
            draw()

    # Features ---------------------------------------------------------------------------------------------------------

    def grime_top( self, u0, u1, z, h=96.0, d=0.15, broken=True ):
        """ riverdale_materials' dirt running down h from a ledge at z (rv_grime_top, 96 in of it a tile), clear of the
        holes under it. """
        if not has_surface( "rv_grime_top" ):
            return

        def draw():
            spans = self.free_u( u0, u1, z - h, z ) if broken else [ ( u0, u1 ) ]
            for a, b in spans:
                uv = [ ( a / 192.0, 1.0 - h / 96.0 ), ( b / 192.0, 1.0 - h / 96.0 ), ( b / 192.0, 1.0 ), ( a / 192.0, 1.0 ) ]
                self.rect( "rv_grime_top", a, b, z - h, z, d, uv=uv )
        self.later.append( draw )

    def grime_foot( self, plinth=24.0, pd=2.0, d=0.15 ):
        """ riverdale_materials' splashback and wet dirt at the wall's foot (rv_grime_foot, 48 in tall): over the plinth's
        front, then the wall above it. """
        if not has_surface( "rv_grime_foot" ):
            return

        def draw():
            for za, zb, dd in ( ( self.z0, self.z0 + plinth - 1.2, pd + d ), ( self.z0 + plinth, self.z0 + 48.0, d ) ):
                if zb - za < 1:
                    continue
                for a, b in self.free_u( self.u0, self.u1, za, zb ):
                    v0, v1 = ( za - self.z0 ) / 48.0, ( zb - self.z0 ) / 48.0
                    self.rect( "rv_grime_foot", a, b, za, zb, dd, uv=[ ( a / 192.0, v0 ), ( b / 192.0, v0 ), ( b / 192.0, v1 ), ( a / 192.0, v1 ) ] )
        self.later.append( draw )

    def plinth( self, h=24.0, d=2.0, paint="rv_plinth", wrap=( True, True ) ):
        """ A darker concrete base standing d out, its top weathered; wrap: run on round the face's ends by d, to meet
        the next face's. """
        def draw():
            ua = self.u0 - ( d if wrap[0] else 0.0 )
            ub = self.u1 + ( d if wrap[1] else 0.0 )
            for a, b in self.free_u( ua, ub, self.z0, self.z0 + h ):
                self.ledge( a, b, self.z0, self.z0 + h, d, paint )
        self.later.append( draw )

    def band( self, z, h=8.0, d=2.0, paint=PRECAST, wrap=( True, True ), drip=False ):
        """ A precast string course from z up to z + h, broken by the holes it meets. """
        def draw():
            ua = self.u0 - ( d if wrap[0] else 0.0 )
            ub = self.u1 + ( d if wrap[1] else 0.0 )
            for a, b in self.free_u( ua, ub, z, z + h ):
                self.ledge( a, b, z, z + h, d, paint )
                if drip:
                    self.box( a, b, z - 0.6, z, d - 0.6, d, paint )
        self.later.append( draw )

    def joint( self, u, za=None, zb=None, w=1.0, depth=1.2 ):
        """ An expansion joint: a groove w wide, its sealant at the back. """
        za = self.z0 if za is None else za
        zb = self.z1 if zb is None else zb
        self.hole( u - w / 2, u + w / 2, za, zb, trim=False )

        def draw():
            self.reveal( u - w / 2, u + w / 2, za, zb, depth, self.paint_at( ( za + zb ) / 2 ),
                         ( True, True, za > self.z0 + 0.5, zb < self.z1 - 0.5 ) )
            self.rect( "rv_fc_seal", u - w / 2, u + w / 2, za, zb, -depth )
        self.later.append( draw )

    def pilaster( self, u0, u1, za, zb, d=4.0, paint="rv_wall", cap=PRECAST ):
        def draw():
            self.box( u0, u1, za, zb, 0, d, self.paints( paint, bottom=None if za <= self.z0 else paint ) )
            if cap:
                self.ledge( u0 - 0.6, u1 + 0.6, zb, zb + 3, d + 0.6, cap, slope=1.6 )
        self.later.append( draw )

    def window( self, u0, u1, z0, z1, depth=6.0, pitch=None, transom=None, room="office", reveal=None,
                frame="rv_frame", sill=PRECAST, lit=False, blind=0.0, head=False, streaks=True ):
        """ A window set back depth in its reveals: a frame, mullions every pitch, a transom, its glass with a room
        behind it (room: riverdale_materials' office, plant or corridor; lit, its lights on), blinds blind of the way
        down, a precast sill standing 2 in out with dirt streaked down from it, and a head band if head. """
        self.hole( u0, u1, z0, z1 )

        def draw():
            ribbed = self.ribbed_at( z0, z1 )
            rp = reveal or ( FLASH if ribbed else self.paint_at( ( z0 + z1 ) / 2 ) )
            has_sill = sill and not ribbed
            self.reveal( u0, u1, z0, z1, depth, rp, ( True, True, not has_sill, True ) )
            fw, fd = 2.0, 3.0
            back = -depth
            self.box( u0, u0 + fw, z0, z1, back, back + fd, frame )
            self.box( u1 - fw, u1, z0, z1, back, back + fd, frame )
            self.box( u0 + fw, u1 - fw, z0, z0 + fw, back, back + fd, frame )
            self.box( u0 + fw, u1 - fw, z1 - fw, z1, back, back + fd, frame )
            count = max( 1, int( round( ( u1 - u0 ) / pitch ) ) ) if pitch else 1
            for k in range( 1, count ):
                u = u0 + ( u1 - u0 ) * k / count
                self.box( u - 0.9, u + 0.9, z0 + fw, z1 - fw, back, back + fd, frame )
            if transom:
                self.box( u0 + fw, u1 - fw, transom - 0.9, transom + 0.9, back, back + fd, frame )
            gd = back + 1.4
            paint = room_paint( room, lit )
            self.rect( paint, u0 + fw, u1 - fw, z0 + fw, z1 - fw, gd,
                       uv=list( getattr( RM, "ROOM_UVS", [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] ) ) if paint.startswith( "rv_window_" ) and paint not in ( "rv_window_lit", "rv_window_dark" ) else None )
            if blind > 0:
                zb = z1 - fw - ( z1 - z0 - 2 * fw ) * blind
                self.rect( "rv_fc_blinds", u0 + fw, u1 - fw, zb, z1 - fw, gd + 0.15 )
            if has_sill:
                self.ledge( u0 - 2.5, u1 + 2.5, z0 - 3.0, z0 + 0.0, 2.0, sill, slope=0.8 )
                self.box( u0, u1, z0 - 0.01, z0, -depth, 0, { "default": None, "+z": sill } )
                if streaks:
                    self.grime_top( u0 - 2, u1 + 2, z0 - 3.0, 54.0 )
            if head and not ribbed:
                self.ledge( u0 - 4, u1 + 4, z1, z1 + 5, 1.5, PRECAST, slope=1.0 )
        self.later.append( draw )

    def door( self, uc, w=72.0, h=92.0, z=None, paint="rv_door", double=None, glazed=True, canopy=0.0, through=None,
              sign=None ):
        """ A steel door (riverdale_parts.door) and a canopy over it canopy deep. through: the opening ( u0, u1 ) it
        stands in, which the model's wall boxes leave (riverdale_parts.door stands it open, swung in, for players to go
        through); without it the door is mounted on the solid wall's face, on a flat panel where the wall is clad. """
        z = self.z0 if z is None else z
        double = w > 60 if double is None else double
        if through:
            self.hole( through[0], through[1], z, z + h + 4.0, trim=False )
        elif self.ribbed_at( z, z + h + 3 ):
            self.hole( uc - w / 2 - 4, uc + w / 2 + 4, z, z + h + 4 )
            self.later.insert( 0, lambda: self.rect( self.paint_at( z ), uc - w / 2 - 4, uc + w / 2 + 4, z, z + h + 4, 0.0 ) )

        def draw():
            P.door( self.m, self.p( uc, z, 0 ), self.right, w, h, paint=paint, window=glazed, double=double,
                    mount="recessed" if through else "surface", sign=sign )
            if canopy:
                self.canopy( uc, w + 30, z + h + 14, canopy )
        self.later.append( draw )

    def inner_window( self, u0, u1, z0, z1, pitch=None ):
        """ A window seen from inside (on a Face standing for a wall's inner side, not finished): its frame and a pane
        lit by the day. """
        fw = 2.0
        self.box( u0 - fw, u0, z0 - fw, z1 + fw, 0, 1.2, "rv_frame" )
        self.box( u1, u1 + fw, z0 - fw, z1 + fw, 0, 1.2, "rv_frame" )
        self.box( u0, u1, z0 - fw, z0, 0, 1.2, "rv_frame" )
        self.box( u0, u1, z1, z1 + fw, 0, 1.2, "rv_frame" )
        count = max( 1, int( round( ( u1 - u0 ) / pitch ) ) ) if pitch else 1
        for k in range( 1, count ):
            u = u0 + ( u1 - u0 ) * k / count
            self.box( u - 0.9, u + 0.9, z0, z1, 0, 1.2, "rv_frame" )
        self.rect( "rv_fc_frosted", u0, u1, z0, z1, 0.3 )
        self.ledge( u0 - fw - 1, u1 + fw + 1, z0 - fw - 1.5, z0 - fw, 2.5, "rv_plinth", slope=0.3 )

    def louvre( self, u0, u1, z0, z1, depth=6.0, blades=None ):
        self.hole( u0, u1, z0, z1 )
        self.later.append( lambda: P.louvre( self.m, self.p( ( u0 + u1 ) / 2, ( z0 + z1 ) / 2, 0 ), self.right, u1 - u0, z1 - z0,
                                             depth, blades, mount="recessed" ) )

    def opening( self, u0, u1, z0, z1, guides=False, housing=False ):
        """ An opening people go through (the boxes beside it draw its reveals). guides: a roller shutter's channels and
        its drum's housing over it, the shutter rolled up. """
        self.hole( u0, u1, z0, z1, trim=False )
        if guides or housing:
            def draw():
                if guides:
                    for a, b in ( ( u0, u0 + 3.0 ), ( u1 - 3.0, u1 ) ):
                        self.box( a, b, z0, z1, -9.0, -2.0, FLASH )
                if housing:
                    self.housing( u0, u1, z1 )
            self.later.append( draw )

    def housing( self, u0, u1, z, h=22.0, d=13.0, paint="rv_fc_shutter" ):
        """ A roller shutter's drum housing over an opening, its motor at one end. """
        self.box( u0 - 6, u1 + 6, z, z + h, 0, d, self.paints( paint, top=FLASH ) )
        self.box( u0 - 6, u1 + 6, z + h - 0.01, z + h + 1.0, 0, d + 0.8, FLASH )
        P.rod( self.m, self.p( u1 + 6, z + h * 0.45, d * 0.5 ), self.p( u1 + 15, z + h * 0.45, d * 0.5 ), 4.2, "rv_steel", 10, caps=True )
        self.box( u1 + 6, u1 + 13, z + h * 0.45 - 9, z + h * 0.45 - 3, 0, 6, "rv_fc_cabinet" )

    def shutter( self, u0, u1, z0, z1, depth=8.0, paint="rv_fc_shutter", housing=True ):
        """ A closed roller shutter set back in its opening: slats 3 in deep-ridged, a bottom bar with hazard stripes,
        guide channels each side, and the drum's housing over it. """
        self.hole( u0, u1, z0, z1 )

        def draw():
            rp = FLASH if self.ribbed_at( z0, z1 ) else self.paint_at( ( z0 + z1 ) / 2 )
            self.reveal( u0, u1, z0, z1, depth + 3, rp, ( True, True, False, True ) )
            back = -depth
            g = 3.5
            for a, b in ( ( u0, u0 + g ), ( u1 - g, u1 ) ):
                self.box( a, b, z0, z1, back - 2, back + 2.5, FLASH )
            pitch = 3.0
            zs = np.arange( z0 + 5.0, z1, pitch )
            p = self.p
            for zb in zs:
                zt = min( zb + pitch, z1 )
                card( self.m, paint, [ p( u0 + g, zb, back + 1.1 ), p( u1 - g, zb, back + 1.1 ), p( u1 - g, zt, back + 0.3 ),
                                       p( u0 + g, zt, back + 0.3 ) ], self.out + UP * 0.25 )
                card( self.m, paint, [ p( u0 + g, zt, back + 0.3 ), p( u1 - g, zt, back + 0.3 ), p( u1 - g, zt, back + 1.1 ),
                                       p( u0 + g, zt, back + 1.1 ) ], -UP )
            self.box( u0 + g, u1 - g, z0, z0 + 5.0, back, back + 2.2, { "default": FLASH, self.front: "rv_hazard" } )
            self.box( u0 + g, u1 - g, z0, z0 + 0.8, back + 2.2, back + 2.6, "rv_rubber" )
            if housing:
                self.housing( u0, u1, z1 )
        self.later.append( draw )

    def canopy( self, uc, w, z, depth=36.0, lamp=True ):
        """ A steel canopy over a door: a deck with its fascia, hung from the wall on two ties, a lit lens under it. """
        self.box( uc - w / 2, uc + w / 2, z, z + 7, 0, depth, self.paints( "rv_steel", top=FLASH ) )
        self.box( uc - w / 2 - 0.3, uc + w / 2 + 0.3, z + 6, z + 8, depth - 1.5, depth + 0.3, FLASH )
        for sg in ( -1, 1 ):
            u = uc + sg * ( w / 2 - 5 )
            P.rod( self.m, self.p( u, z + 7, depth - 3 ), self.p( u, z + 46, 0.6 ), 0.7, "rv_steel", 6 )
            self.box( u - 2, u + 2, z + 42, z + 50, 0, 0.8, "rv_steel" )
        if lamp:
            p = self.p
            card( self.m, "rv_lamp_warm", [ p( uc - 8, z - 0.05, depth * 0.45 - 2 ), p( uc + 8, z - 0.05, depth * 0.45 - 2 ),
                                            p( uc + 8, z - 0.05, depth * 0.45 + 2 ), p( uc - 8, z - 0.05, depth * 0.45 + 2 ) ], -UP )

    def downpipe( self, u, ztop, zbot=None, d=3.6, r=2.3, paint=FLASH, scupper=True ):
        """ A downpipe from a scupper through the parapet and its hopper to a shoe at the foot, bracketed to the wall. """
        zbot = self.z0 if zbot is None else zbot

        def draw():
            hz = ztop - 12
            if scupper:
                self.box( u - 3.5, u + 3.5, ztop - 4.5, ztop - 1.5, 0, 6.5, paint )
            lathe_hopper( self.m, self.p( u, 0, d ), hz - 10, hz, r, paint )
            P.pipe( self.m, [ self.p( u, hz - 10, d ), self.p( u, zbot + 9, d ), self.p( u, zbot + 2.5, d + 5.5 ) ], r, paint, 8,
                    caps=True, bend=2.0 )
            for z in np.arange( hz - 34, zbot + 24, -72.0 ):
                P.disc_ring( self.m, self.p( u, z - 0.7, d ), self.p( u, z + 0.7, d ), r + 0.45, paint, 8 )
                self.box( u - 0.7, u + 0.7, z - 0.7, z + 0.7, 0, d - r + 0.2, paint )
        self.later.append( draw )

    def conduit( self, pts, d=1.4, r=0.55, paint="rv_zinc", saddles=40.0 ):
        """ Surface conduit along ( u, z ) points, with saddles. """
        pts = [ ( float( u ), float( z ) ) for u, z in pts ]
        P.pipe( self.m, [ self.p( u, z, d ) for u, z in pts ], r, paint, 6, caps=False, bend=3.0 )
        for ( ua, za ), ( ub, zb ) in zip( pts, pts[1:] ):
            L = math.hypot( ub - ua, zb - za )
            for t in np.arange( 6.0, L - 4.0, saddles ):
                u, z = ua + ( ub - ua ) * t / L, za + ( zb - za ) * t / L
                if abs( zb - za ) > abs( ub - ua ):
                    self.box( u - r - 0.4, u + r + 0.4, z - 0.6, z + 0.6, 0, d + r + 0.25, "rv_zinc" )
                else:
                    self.box( u - 0.6, u + 0.6, z - r - 0.4, z + r + 0.4, 0, d + r + 0.25, "rv_zinc" )

    def jbox( self, u, z, w=9.0, h=11.0, depth=3.6, paint="rv_fc_cabinet" ):
        """ A junction box: body, its lid's rim and a gland under it. """
        self.box( u - w / 2, u + w / 2, z - h / 2, z + h / 2, 0, depth, paint )
        self.box( u - w / 2 - 0.3, u + w / 2 + 0.3, z - h / 2 - 0.3, z + h / 2 + 0.3, depth - 0.6, depth, paint )
        P.rod( self.m, self.p( u, z - h / 2 - 1.8, depth / 2 ), self.p( u, z - h / 2, depth / 2 ), 0.9, "rv_black", 6 )

    def cabinet( self, u, z0, w=26.0, h=40.0, depth=5.5, paint="rv_fc_cabinet", plate="danger" ):
        """ A wall-hung electrical cabinet: two doors, a handle, a vent, a sign. """
        self.box( u - w / 2, u + w / 2, z0, z0 + h, 0, depth, paint )
        self.box( u - w / 2 - 0.5, u + w / 2 + 0.5, z0 + h, z0 + h + 1.2, 0, depth + 0.8, paint )
        self.rect( "rv_fc_seal", u - 0.25, u + 0.25, z0 + 1, z0 + h - 1, depth + 0.03 )
        for sg in ( -1, 1 ):
            self.box( u + sg * 2.0 - 0.5, u + sg * 2.0 + 0.5, z0 + h * 0.45, z0 + h * 0.55, depth, depth + 0.9, "rv_dark" )
        for k in range( 5 ):
            zz = z0 + 4 + k * 1.4
            self.rect( "rv_fc_seal", u - w / 2 + 3, u - 3, zz, zz + 0.6, depth + 0.03 )
        if plate:
            P.plate( self.m, plate, self.p( u + w / 4, z0 + h * 0.75, depth ), self.right, 5.0, off=0.05 )
        P.rod( self.m, self.p( u, z0, depth / 2 ), self.p( u, z0 - 14, depth / 2 ), 1.0, "rv_zinc", 6 )

    def camera( self, u, z, tilt=22.0, turn=0.0 ):
        """ A CCTV camera on a wall bracket, looking out and down (turn: along the wall, degrees). """
        p = self.p
        self.box( u - 3, u + 3, z - 4, z + 4, 0, 1.0, "rv_fc_cabinet" )
        tip = p( u, z, 11 )
        P.rod( self.m, p( u, z, 1 ), tip, 0.9, "rv_fc_cabinet", 6 )
        a, t = math.radians( turn ), math.radians( tilt )
        look = unit( self.out * math.cos( a ) + self.uvec * math.sin( a ) )
        x = unit( look * math.cos( t ) - UP * math.sin( t ) )
        y = unit( np.cross( UP, x ) )
        zz = np.cross( x, y )
        body = tip + x * 3.0 - UP * 3.2
        self.m.oriented_box( body, ( x, y, zz ), ( 11, 4.4, 4.4 ), "rv_fc_cabinet" )
        self.m.oriented_box( body + zz * 2.6 + x * 1.0, ( x, y, zz ), ( 13, 5.6, 0.6 ), "rv_fc_cabinet" )
        card( self.m, "rv_black", [ body + x * 5.55 + y * s1 * 1.6 + zz * s2 * 1.6 for s1, s2 in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ], x )

    def lamp( self, name, u, z, kind="warm", radius=320, light=False ):
        P.wall_light( self.m, name, self.p( u, z, 0 ), self.out, kind, radius, light=light )

    def sign( self, name, u, z, h, d=0.35 ):
        P.plate( self.m, name, self.p( u, z, 0 ), self.right, h, off=d )

    def letters( self, name, u, z, h, tone="dark", d=0.4, board=None, pad=0.18 ):
        """ Lettering; board: a flat sign panel behind it (paint), for lettering on cladding. """
        if board:
            w = h * RM.aspect( RM.LETTERS, name )
            self.box( u - w / 2 - h * pad, u + w / 2 + h * pad, z - h / 2 - h * pad * 0.6, z + h / 2 + h * pad * 0.6, 0, d, board )
            d += 0.25
        P.letters( self.m, name, self.p( u, z, 0 ), self.right, h, tone, off=d )

    def guard( self, u, side, z1=60.0 ):
        """ A hazard-striped steel angle on an opening's jamb at u (side -1: the opening runs on from u to higher u,
        +1: to lower u), one leg on the face and one on the reveal. """
        w = 5.0
        paint = { "default": "rv_yellow", self.front: "rv_hazard" }
        if side < 0:
            self.box( u - w, u, self.z0, z1, 0, 0.35, paint )
            self.box( u, u + 0.35, self.z0, z1, -w, 0.35, "rv_hazard" )
        else:
            self.box( u, u + w, self.z0, z1, 0, 0.35, paint )
            self.box( u - 0.35, u, self.z0, z1, -w, 0.35, "rv_hazard" )


def lathe_hopper( m, at, z0, z1, r, paint ):
    """ A downpipe's hopper head: a box-like funnel narrowing to the pipe (lathed, 8 sides). """
    P.lathe( m, ( at[0], at[1] ), [ ( r + 0.2, z0 ), ( r + 0.2, z0 + 2 ), ( r + 3.6, z1 - 3 ), ( r + 3.8, z1 ) ], paint, 8, cap="rv_black" )


# ---------------------------------------------------------------------------------------------------------------------
# Parapets, roofs and their plant

def coping( m, e0, e1, n0, n1, z, over=3.0, paint=FLASH, t=2.0, lip=3.0 ):
    """ A metal coping on a parapet's top ( e0..e1, n0..n1 at z ): a cap over each side by over, its drip lips hanging
    lip below. """
    box( m, e0 - over, e1 + over, n0 - over, n1 + over, z, z + t, paint )
    for a, b, c, d in ( ( e0 - over, e1 + over, n0 - over, n0 - over + 0.3 ), ( e0 - over, e1 + over, n1 + over - 0.3, n1 + over ),
                        ( e0 - over, e0 - over + 0.3, n0 - over, n1 + over ), ( e1 + over - 0.3, e1 + over, n0 - over, n1 + over ) ):
        box( m, a, b, c, d, z - lip, z, paint )


def roof_unit( m, c, along, z, size=( 96.0, 54.0, 44.0 ), fans=2 ):
    """ An air handling unit on its curb: a casing with access panels and louvres, its fans on top. """
    along = unit( ( along[0], along[1], 0.0 ) )
    side = np.cross( UP, along )
    L, W, H = size
    base = v( c[0], c[1], z )
    P.obox( m, base + UP * 4, along, ( L + 8, W + 8, 8 ), "rv_steel" )
    P.obox( m, base + UP * ( 8 + H / 2 ), along, ( L, W, H ), { "default": "rv_white", "+z": "rv_fc_flashing" } )
    for sg in ( -1, 1 ):
        face = base + side * ( W / 2 + 0.05 ) * sg
        for k in range( 3 ):
            a = -L / 2 + L * ( k + 0.5 ) / 3
            seam = face + along * ( a + L / 6 - 0.3 )
            if k < 2:
                card( m, "rv_fc_seal", [ seam + UP * 9, seam + along * 0.6 + UP * 9, seam + along * 0.6 + UP * ( 8 + H - 1 ),
                                         seam + UP * ( 8 + H - 1 ) ], side * sg )
        for j in range( 9 ):
            zz = 14 + j * 2.6
            q = face + along * ( -L / 2 + 6 )
            card( m, "rv_louvre", [ q + UP * zz, q + along * ( L / 3 - 6 ) + UP * zz, q + along * ( L / 3 - 6 ) + UP * ( zz + 1.4 ),
                                    q + UP * ( zz + 1.4 ) ], side * sg + UP * 0.3 )
    for k in range( fans ):
        f = base + along * ( -L / 2 + L * ( k + 0.5 ) / fans ) + UP * ( 8 + H )
        cylinder_at( m, f, min( W, L / fans ) * 0.36, z + 8 + H, z + 8 + H + 6, "rv_steel", top="rv_black" )
        cylinder_at( m, f, 4.0, z + 8 + H, z + 8 + H + 7, "rv_dark", top="rv_dark" )
    # A duct down into the roof.
    d = base - along * ( L / 2 - 14 ) - side * ( W / 2 + 10 )
    P.obox( m, d + UP * 14, along, ( 18, 16, 28 ), "rv_fc_flashing" )


def cylinder_at( m, c, r, z0, z1, paint, top=None, sides=16 ):
    P.cylinder( m, ( c[0], c[1] ), r, z0, z1, paint, sides, top=top )


def roof_fan( m, c, z, r=13.0 ):
    """ A mushroom exhaust fan on its upstand. """
    P.cylinder( m, ( c[0], c[1] ), r * 0.8, z, z + 10, "rv_steel", 14 )
    P.lathe( m, ( c[0], c[1] ), [ ( r * 0.62, z + 10 ), ( r * 0.62, z + 16 ), ( r * 1.05, z + 17 ), ( r * 1.05, z + 20 ),
                                  ( r * 0.8, z + 24 ), ( 0.0, z + 26 ) ], [ "rv_louvre", "rv_fc_flashing", "rv_fc_flashing",
                                                                            "rv_fc_flashing", "rv_fc_flashing" ], 14 )


def roof_vent( m, c, z, r=3.0, h=30.0 ):
    """ A vent pipe with a rain cap. """
    P.cylinder( m, ( c[0], c[1] ), r, z, z + h, "rv_steel", 8 )
    P.lathe( m, ( c[0], c[1] ), [ ( r * 2.2, z + h + 2 ), ( r * 2.2, z + h + 3 ), ( 0.0, z + h + 6 ) ], "rv_steel", 8 )
    for k in range( 3 ):
        a = 2 * math.pi * k / 3
        q = v( c[0] + math.cos( a ) * r * 0.8, c[1] + math.sin( a ) * r * 0.8, 0 )
        P.rod( m, q + UP * ( z + h ), q + UP * ( z + h + 2.2 ), 0.3, "rv_steel", 4 )


def hatch( m, c, z, along=( 1, 0 ) ):
    """ A roof access hatch on its upstand. """
    P.obox( m, v( c[0], c[1], z + 7 ), along, ( 40, 34, 14 ), "rv_plinth" )
    P.obox( m, v( c[0], c[1], z + 15 ), along, ( 44, 38, 2.5 ), "rv_fc_flashing" )


# ---------------------------------------------------------------------------------------------------------------------
# Pipes

def flanges( m, a, b, r, every=240.0, paint="rv_pipe", sides=10, start=None ):
    """ Flange pairs along a straight pipe from a to b, every so often. """
    a, b = v( *a ), v( *b )
    L = float( np.linalg.norm( b - a ) )
    d = ( b - a ) / L
    for t in np.arange( start if start is not None else every / 2, L - 10, every ):
        P.disc_ring( m, a + d * ( t - 1.3 ), a + d * ( t + 1.3 ), r * 1.32, paint, sides )


def shoe( m, at, r, along, paint="rv_steel" ):
    """ A pipe shoe under a pipe where it rests on a beam: a T welded under it. """
    at = v( *at )
    P.obox( m, at - UP * ( r + 2.0 ), along, ( 10.0, 1.2, 4.0 ), paint )
    P.obox( m, at - UP * ( r + 4.2 ), along, ( 10.0, 6.0, 0.8 ), paint )


def valve( m, at, r, along, paint="rv_steel", wheel="rv_yellow" ):
    """ A gate valve in a line: its body, the bonnet and stem up, the handwheel on top. """
    along = unit( ( along[0], along[1], 0.0 ) )
    at = v( *at )
    P.rod( m, at - along * r * 1.1, at + along * r * 1.1, r * 1.4, paint, 10, caps=True )
    P.rod( m, at, at + UP * r * 2.6, r * 0.55, paint, 8, caps=True )
    P.rod( m, at + UP * r * 2.6, at + UP * r * 4.2, 0.6, "rv_zinc", 6 )
    c = at + UP * r * 4.2
    side = np.cross( UP, along )
    R = r * 1.6 + 3
    for k in range( 10 ):
        a0, a1 = 2 * math.pi * k / 10, 2 * math.pi * ( k + 1 ) / 10
        P.rod( m, c + along * R * math.cos( a0 ) + side * R * math.sin( a0 ), c + along * R * math.cos( a1 ) + side * R * math.sin( a1 ),
               0.6, wheel, 5 )
    for k in range( 3 ):
        a = 2 * math.pi * k / 3
        P.rod( m, c, c + along * R * math.cos( a ) + side * R * math.sin( a ), 0.4, wheel, 4 )


def bracing( m, a, b, h, paint="rv_steel", w=3.0 ):
    """ An X of angles between two columns' feet a and b (plan), from 30 in up to h. """
    a, b = v( a[0], a[1], 0 ), v( b[0], b[1], 0 )
    m.beam( a + UP * 30, b + UP * h, ( w, w ), paint )
    m.beam( b + UP * 30, a + UP * h, ( w, w ), paint )


def base_plate( m, e, n, size=10.0, paint="rv_plinth" ):
    """ A column's grout pad and base plate with its anchor nuts. """
    box( m, e - size / 2 - 4, e + size / 2 + 4, n - size / 2 - 4, n + size / 2 + 4, 0, 2.5, { "default": paint, "-z": None } )
    box( m, e - size / 2 - 2, e + size / 2 + 2, n - size / 2 - 2, n + size / 2 + 2, 2.5, 3.5, { "default": "rv_steel", "-z": None } )
    for se in ( -1, 1 ):
        for sn in ( -1, 1 ):
            P.cylinder( m, ( e + se * ( size / 2 + 0.8 ), n + sn * ( size / 2 + 0.8 ) ), 0.8, 3.5, 5.0, "rv_zinc", 6, top="rv_zinc" )


# ---------------------------------------------------------------------------------------------------------------------
# A diesel generator set

def genset( m, e0, e1, n0, n1, z0=14.0, z1=96.0 ):
    """ The dressing of a generator set's acoustic housing ( e0..e1, n0..n1, z0..z1: riverdale_map's box, which
    collides): door panels with their hinges and handles, intake louvres, the radiator grille at its east end, the
    control panel and fuel filler at its west end, lifting eyes, and the exhaust silencer and stack on top. Nothing
    stands more than 1.5 in off the housing below its roof. """
    L = e1 - e0
    for face_n, sg in ( ( n0, -1 ), ( n1, 1 ) ):
        f = Face( m, "+n" if sg > 0 else "-n", face_n, e0, e1, z0, z1 )
        panels = max( 2, int( round( L / 46 ) ) )
        width = L / panels
        for k in range( panels ):
            a, b = e0 + width * k + 1.0, e0 + width * ( k + 1 ) - 1.0
            f.box( a, b, z0 + 4, z1 - 4, 0, 0.5, "rv_yellow" )
            f.rect( "rv_fc_seal", a - 0.6, a + 0.0, z0 + 4, z1 - 4, 0.2 )
            for zz in ( z0 + 14, z1 - 14 ):
                f.box( a + 0.5, a + 2.0, zz - 3, zz + 3, 0.5, 1.4, "rv_steel" )
            f.box( b - 4.5, b - 2.5, ( z0 + z1 ) / 2 - 4, ( z0 + z1 ) / 2 + 4, 0.5, 1.5, "rv_dark" )
            # An intake louvre in the panel's top half.
            lz0, lz1 = z1 - 32, z1 - 10
            f.box( a + 5, b - 7, lz0, lz1, 0.5, 1.4, { "default": "rv_steel", f.front: None } )
            f.rect( "rv_black", a + 6, b - 8, lz0 + 1, lz1 - 1, 0.6 )
            for zz in np.arange( lz0 + 1.6, lz1 - 1, 2.4 ):
                p = f.p
                card( m, "rv_louvre", [ p( a + 6, zz, 1.3 ), p( b - 8, zz, 1.3 ), p( b - 8, zz + 1.8, 0.7 ), p( a + 6, zz + 1.8, 0.7 ) ],
                      f.out + UP * 0.5 )
    # The east end: the radiator's grille.
    f = Face( m, "+e", e1, n0, n1, z0, z1 )
    f.box( n0 + 6, n1 - 6, z0 + 8, z1 - 8, 0, 1.0, { "default": "rv_steel", f.front: None } )
    f.rect( "rv_black", n0 + 7, n1 - 7, z0 + 9, z1 - 9, 0.4 )
    for nn in np.arange( n0 + 9, n1 - 8, 3.0 ):
        f.box( nn - 0.4, nn + 0.4, z0 + 9, z1 - 9, 0.4, 1.0, "rv_steel" )
    # The west end: control panel, filler, an emergency stop.
    f = Face( m, "-e", e0, n0, n1, z0, z1 )
    nc = ( n0 + n1 ) / 2
    f.box( nc - 14, nc + 6, z0 + 38, z0 + 66, 0, 1.4, "rv_fc_cabinet" )
    f.rect( "rv_screens", nc - 10, nc - 1, z0 + 52, z0 + 60, 1.45,
            uv=[ RM.atlas_uv( RM.SCREENS, RM.SCREEN_ATLAS, "panel", s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ] )
    f.box( nc + 1, nc + 4, z0 + 44, z0 + 47, 1.4, 2.0, "rv_fc_red" )
    f.box( nc + 12, nc + 18, z0 + 18, z0 + 24, 0, 1.2, "rv_steel" )
    f.sign( "danger", nc + 15, z0 + 34, 6, d=0.1 )
    # Lifting eyes at the roof's corners.
    for e in ( e0 + 6, e1 - 6 ):
        for n in ( n0 + 6, n1 - 6 ):
            P.rod( m, ( e, n, z1 ), ( e, n, z1 + 3 ), 1.2, "rv_steel", 6 )
    # The silencer on its saddles, the stack and its rain cap.
    nc = ( n0 + n1 ) / 2
    a, b = v( e0 + 18, nc, z1 + 12 ), v( e1 - 34, nc, z1 + 12 )
    P.rod( m, a, b, 8.5, "rv_steel", 12, caps=True )
    for e in ( e0 + 26, e1 - 44 ):
        box( m, e - 2, e + 2, nc - 7, nc + 7, z1, z1 + 6, "rv_steel" )
    P.pipe( m, [ ( e1 - 34, nc, z1 + 12 ), ( e1 - 22, nc, z1 + 12 ), ( e1 - 22, nc, z1 + 64 ) ], 3.6, "rv_steel", 8, caps=False, bend=2.0 )
    P.disc_ring( m, v( e1 - 22, nc, z1 + 40 ), v( e1 - 22, nc, z1 + 41.5 ), 5.0, "rv_steel", 8 )
    P.lathe( m, ( e1 - 22, nc ), [ ( 3.7, z1 + 64 ), ( 3.7, z1 + 68 ) ], "rv_dark", 8 )
    card( m, "rv_steel", [ v( e1 - 26, nc - 4, z1 + 68 ), v( e1 - 18, nc - 4, z1 + 70.5 ), v( e1 - 18, nc + 4, z1 + 70.5 ),
                           v( e1 - 26, nc + 4, z1 + 68 ) ], UP )
