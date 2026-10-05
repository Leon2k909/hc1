"""
Railhead's backdrop: Hohenwald, the city round its terminus, everything outside the play area (e +-2200, n -2400..1820),
and the row of tenements that closes the play area's east and west sides across the cab roads.

    python Tools/railhead_backdrop.py --preview <dir> [view ...]      (with flat stand-ins for the station)

railhead_map imports it; this script writes no models or assets itself. Plan inches as map_kit (e east, n north, z up).

- edge_blocks( side ): the play edge, the only model here with collision. A Gruenderzeit block (1880-1910) of five-storey
  tenements facing the cab road, fronts on e = +-2200 from n -1190 to 2050, backs at e +-2700. A lane (n -1400..-1190)
  separates it from railhead_station's bonded warehouse, and its north end turns the corner onto the cross street.
  side 1 is the east row, -1 the west row (built in place, not mirrored, so the shop signs read the right way round).
- north_city(): the Bahnhofsplatz in front of the head building (n 1820..2700) with its tram stop, the hotel and the
  office block facing the station, and the cab roads running on north. Drawn only.
- south_vista(): the line running south out of the station (cutting, retaining walls, a road overbridge at n -3100), the
  allotments, a depot shed, the industry along the line, a small town, the Rotunde (an iron-and-glass exhibition
  rotunda, 107 m across) in its park on the hill over the tunnel, and low farmland and woods beyond. Drawn only.
- skyline(): the rest of the city, beside the edge rows (|e| 2700..) and north of north_city (n 3700..), on a grid of
  streets 2400 apart (blocks 2160 square, carriageways 240), out to its last street at |e| 23220 and n 25000; level
  ground to R0 (24500 as ring_z measures it), hills rising to ~3400 (86 m) by 39500, to the world's edge at 40000.
  - The block behind each edge row (first_block): a carrier's goods shed and yard, a north-light workshop, the
    courtyard the rows' arches look into (two rear houses, lawns, trees) and a row of tenements on the first street.
  - The tramway runs on along the cross street to |e| 13380, lamps line the cab roads and Bahnhofstrasse, and the
    streets near the play area have centre lines.
  - Landmarks: the twin-towered Neo-Gothic minster closing the east cab road's view (spires 76 m), the brick hall
    church closing the west one's (71 m), a Baroque church's onion dome (48 m), a 1970s office tower (104 m), a 1960s
    slab block (47 m), a brewery's chimney (51 m), a water tower (50 m) and two small parish churches (36 m).
  Drawn only.
- models(): the four as { name: Model }, with the railhead paints' material and tile overrides set.

Real figures used:
- A Gruenderzeit tenement: ground floor 4.8 m (190 in) with its shops, upper storeys 3.5 m (138 in, 3.2 m clear), four
  upper storeys and an attic under a mansard (72 and 16 degrees) or a 40-degree roof: eaves 22-27 m (720-860 in), as
  Berlin's building code of 1887 allowed on a wide street. Window axes 2.6-3.0 m apart, windows 1.1-1.25 m wide and
  2.2 m tall, set 15 cm into the wall. Shop windows 2.2-3.2 m tall, fascias 0.7 m.
- A carriage arch (Durchfahrt) 3.5 m wide and 4.2 m high, for a laden cart.
- Trams: standard gauge (1435 mm), grooved rail, overhead wire at 5.5-6.5 m (z 230-260 over the road).
- A road overbridge over electrified track: 5.9 m from rail top to the deck's soffit, 1.0 m parapets.
- Trees: the cloud oaks are 7.7 m (tree_oak_small_a) and 17.9 m (tree_oak_medium_a) tall at scale 1.
- The skyline's blocks are 55 m square (2160 in) between 6.1 m carriageways (240 in, two lanes): the small end of a
  European perimeter block (Barcelona's Eixample's are 113 m, Berlin's 1862 plan's larger still), kept small so the
  streets break up the distant roofs.
- Church towers: Neo-Gothic twin spires 70-100 m (Regensburg's 105 m, the Votivkirche's 99 m); a brick hall church's
  west tower 60-80 m; a Baroque onion tower 40-55 m.
"""
import math
import sys
import zlib
from pathlib import Path

import numpy as np

import map_kit as K

# belltower_detail's cloud foliage (Facepunch's): heights 391.9 and 703.7, the bush 75.
OAK = "models/sbox_props/trees/oak/tree_oak_small_a.vmdl"
OAK_BIG = "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl"
BUSH = "models/sbox_props/shrubs/beech/beech_bush_small.vmdl"

STONE = "default"

# The play area and the station (railhead_station's figures)
EDGE = 2200.0               # the play area's side: the edge row's fronts
BACK = 2700.0               # the edge row's backs
ROW_N0, ROW_N1 = -1190.0, 2050.0
LANE_N0 = -1400.0           # the bonded warehouse's north end (railhead_station.WAREHOUSE)
WAREHOUSE_E1, WAREHOUSE_TOP = 2560.0, 590.0
PLAY_N0, PLAY_N1 = -2400.0, 1820.0
ROAD_Z = -6.0
ROAD_E0, ROAD_E1 = 1500.0, 2000.0       # the cab roads' carriageways (e +-, z -6)
PLATZ_N1 = 2700.0           # the Bahnhofsplatz's north side
CROSS_N0, CROSS_N1 = 2110.0, 2340.0     # the cross street's carriageway (pavements 60 either side)
CITY_N1 = 3700.0            # where north_city hands over to the skyline
WORLD = 24000.0             # the city's extent; the hills go on to 40000

# The line south: kept clear for the lead's tracks (the outer ones curve in from e +-848 to +-600 by n -4600), its
# floor (z -37) the lead's too. Half-widths at n: 1200 at -2400, 1000 at -3500, 700 from -5000 on.
CORRIDOR = ( ( -2400.0, 1200.0 ), ( -3500.0, 1000.0 ), ( -5000.0, 700.0 ) )
BRIDGE_N = -3100.0          # the road overbridge's centre line

# Storeys
GROUND = 190.0              # ground floor, floor to floor
STOREY = 138.0


# ---------------------------------------------------------------------------------------------------------------------
# Dice: every choice is a hash of a key, so a run always builds the same city

def unit( *key ):
    return ( zlib.crc32( "/".join( str( k ) for k in key ).encode() ) & 0xffffffff ) / 4294967296.0


def between( lo, hi, *key ):
    return lo + ( hi - lo ) * unit( *key )


def pick( options, *key ):
    return options[int( unit( *key ) * len( options ) ) % len( options )]


def chance( p, *key ):
    return unit( *key ) < p


def split( length, lo, hi, *key ):
    """ length cut into pieces lo..hi long (the last ones evened out). """
    pieces, left, k = [], length, 0
    while left > hi:
        w = between( lo, hi, *key, k )
        if left - w < lo:
            w = left / 2 if left / 2 >= lo else left - lo
        pieces.append( w )
        left -= w
        k += 1
    pieces.append( left )
    return pieces


def smooth( t ):
    t = min( max( t, 0.0 ), 1.0 )
    return t * t * ( 3 - 2 * t )


# ---------------------------------------------------------------------------------------------------------------------
# Drawing helpers

def facing( model, paint, points, towards, uv=None ):
    """ A polygon turned to face towards (its points' order reversed if they wound the other way). """
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
        uv = None if uv is None else list( uv[:1] ) + list( uv[:0:-1] )
    model.polygon( paint, pts, uv=uv )


def flat( model, paint, e0, e1, n0, n1, z ):
    """ A level quad facing up. """
    if e1 > e0 and n1 > n0:
        model.polygon( paint, [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ] )


def rod( model, p0, p1, size, paint ):
    """ A thin bar from p0 to p1 with no end caps. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    x = K.normalise( p1 - p0 )
    side = np.cross( ( 0.0, 0.0, 1.0 ), x )
    if np.linalg.norm( side ) < 1e-6:
        side = np.cross( ( 1.0, 0.0, 0.0 ), x )
    y = K.normalise( side )
    z = np.cross( x, y )
    model.oriented_box( ( p0 + p1 ) / 2, ( x, y, z ), ( np.linalg.norm( p1 - p0 ), size, size ),
                        { "default": paint, "+x": None, "-x": None } )


def lathe( model, centre, profile, paint, sides=8, turn=0.0, cap=True ):
    """ A round thing: profile ( r, z ) from the bottom up, turned about centre ( e, n ). A last point at r 0 closes the
    top; cap closes a flat top. """
    c = np.array( ( centre[0], centre[1] ) )
    angles = [ turn + 2 * math.pi * k / sides for k in range( sides + 1 ) ]
    for ( ra, za ), ( rb, zb ) in zip( profile, profile[1:] ):
        for a0, a1 in zip( angles, angles[1:] ):
            d0, d1 = np.array( ( math.cos( a0 ), math.sin( a0 ) ) ), np.array( ( math.cos( a1 ), math.sin( a1 ) ) )
            mid = ( d0 + d1 ) / 2
            towards = np.array( ( *( mid * ( zb - za ) ), ra - rb ) )
            if np.linalg.norm( towards ) < 1e-9:
                continue
            pts = [ ( *( c + d0 * ra ), za ), ( *( c + d1 * ra ), za ), ( *( c + d1 * rb ), zb ), ( *( c + d0 * rb ), zb ) ]
            if ra < 1e-6:
                pts = pts[1:]
            elif rb < 1e-6:
                pts = pts[:3]
            facing( model, paint, pts, towards )
    r, z = profile[-1]
    if cap and r > 1e-6:
        model.polygon( paint, [ ( *( c + r * np.array( ( math.cos( a ), math.sin( a ) ) ) ), z ) for a in angles[:-1] ] )


def tri_pair( model, paint, a, b, c, d, towards ):
    """ A quad that needn't be flat, as two triangles. """
    facing( model, paint, [ a, b, c ], towards )
    facing( model, paint, [ a, c, d ], towards )


class Face:
    """ A building's face: origin ( e, n ) is its r = 0 end, out its outward normal (plan, +-e or +-n). r runs to the
    right of someone looking at it, d out of it, z up. """

    def __init__( self, origin, out ):
        self.o = np.array( ( origin[0], origin[1], 0.0 ), float )
        self.D = np.array( ( out[0], out[1], 0.0 ), float )
        self.R = np.array( ( -out[1], out[0], 0.0 ), float )
        self.Z = np.array( ( 0.0, 0.0, 1.0 ) )

    def p( self, r, d, z ):
        return self.o + self.R * r + self.D * d + self.Z * z

    @staticmethod
    def name( v ):
        return "+e" if v[0] > 0.5 else "-e" if v[0] < -0.5 else "+n" if v[1] > 0.5 else "-n"

    def faces( self ):
        return { "+d": self.name( self.D ), "-d": self.name( -self.D ), "+r": self.name( self.R ),
                 "-r": self.name( -self.R ), "+z": "+z", "-z": "-z", "default": "default" }

    def box( self, model, r0, r1, d0, d1, z0, z1, paints, surface=None, skip=( "-d", ) ):
        """ A box in face coordinates; by default its back (against the wall) isn't drawn. """
        names = self.faces()
        if isinstance( paints, dict ):
            paints = { names[k]: v for k, v in paints.items() }
        model.box( self.p( r0, d0, z0 ), self.p( r1, d1, z1 ), paints, surface, tuple( names[k] for k in skip ) )

    def quad( self, model, paint, r0, r1, z0, z1, d=0.0, out=1.0, uv=None ):
        """ An upright quad at d, facing out ( +1 ) or in ( -1 ); uv in the order BL, BR, TR, TL seen from outside. """
        if r1 - r0 < 1e-6 or z1 - z0 < 1e-6:
            return
        pts = [ self.p( r0, d, z0 ), self.p( r1, d, z0 ), self.p( r1, d, z1 ), self.p( r0, d, z1 ) ]
        facing( model, paint, pts, self.D * out, uv )

    def poly( self, model, paint, rz, d=0.0, out=1.0 ):
        facing( model, paint, [ self.p( r, d, z ) for r, z in rz ], self.D * out )

    def side( self, model, paint, r, d0, d1, z0, z1, towards ):
        """ An upright quad across the face at r (a reveal, a box's end), facing +R ( towards 1 ) or -R. """
        pts = [ self.p( r, d0, z0 ), self.p( r, d1, z0 ), self.p( r, d1, z1 ), self.p( r, d0, z1 ) ]
        facing( model, paint, pts, self.R * towards )

    def level( self, model, paint, r0, r1, d0, d1, z, up=1.0 ):
        pts = [ self.p( r0, d0, z ), self.p( r1, d0, z ), self.p( r1, d1, z ), self.p( r0, d1, z ) ]
        facing( model, paint, pts, self.Z * up )

    def prism( self, model, paint, rz, d0, d1 ):
        """ A convex ( r, z ) outline pushed out from d0 to d1: its front and sides (not its back). """
        self.poly( model, paint, rz, d1 )
        pts = list( rz )
        area = sum( a[0] * b[1] - b[0] * a[1] for a, b in zip( pts, pts[1:] + pts[:1] ) )
        sign = 1.0 if area > 0 else -1.0
        for ( ra, za ), ( rb, zb ) in zip( pts, pts[1:] + pts[:1] ):
            towards = self.R * ( zb - za ) * sign - self.Z * ( rb - ra ) * sign
            facing( model, paint, [ self.p( ra, d0, za ), self.p( rb, d0, zb ), self.p( rb, d1, zb ), self.p( ra, d1, za ) ],
                    towards )

    def back( self, depth, length ):
        """ The face on the other side of a building depth deep and length long: r' = length - r there. """
        f = Face( ( 0, 0 ), ( -self.D[0], -self.D[1] ) )
        f.o = self.o + self.R * length - self.D * depth
        return f


def holed_wall( model, face, paint, r0, r1, z0, z1, holes, d=0.0, arches=() ):
    """ A wall r0..r1, z0..z1 at d, with rectangular holes ( r0, r1, z0, z1 ) cut out of it, drawn as upright strips.
    arches ( r0, r1, spring, crown ) are holes up to the crown whose round heads are filled back in. """
    cuts = [ h for h in holes ] + [ ( a[0], a[1], a[4] if len( a ) > 4 else z0, a[3] ) for a in arches ]
    edges = sorted( { r0, r1, *[ min( max( c[0], r0 ), r1 ) for c in cuts ], *[ min( max( c[1], r0 ), r1 ) for c in cuts ] } )
    for a, b in zip( edges, edges[1:] ):
        if b - a < 1e-6:
            continue
        mid = ( a + b ) / 2
        gaps = sorted( ( c[2], c[3] ) for c in cuts if c[0] < mid < c[1] )
        z = z0
        for g0, g1 in gaps:
            if g0 > z:
                face.quad( model, paint, a, b, z, min( g0, z1 ), d )
            z = max( z, g1 )
        if z < z1:
            face.quad( model, paint, a, b, z, z1, d )
    for a in arches:
        ar0, ar1, spring, crown = a[:4]
        rc, rad = ( ar0 + ar1 ) / 2, ( ar1 - ar0 ) / 2
        pts = K.arc( rc, spring, rad, 8, 180, 90 )
        face.poly( model, paint, [ ( ar0, crown ) ] + pts + [ ( rc, crown ) ], d )
        pts = K.arc( rc, spring, rad, 8, 90, 0 )
        face.poly( model, paint, [ ( ar1, crown ), ( rc, crown ) ] + pts, d )


def reveal( model, face, paint, r0, r1, z0, z1, depth, d=0.0, top=True, bottom=True ):
    """ The four sides of a hole in a wall at d, depth deep. """
    face.side( model, paint, r0, d - depth, d, z0, z1, 1.0 )
    face.side( model, paint, r1, d - depth, d, z0, z1, -1.0 )
    if top:
        face.level( model, paint, r0, r1, d - depth, d, z1, -1.0 )
    if bottom:
        face.level( model, paint, r0, r1, d - depth, d, z0, 1.0 )


def window( model, face, r0, r1, z0, z1, frame="trim_white", glass="rw_window_dark", reveal_paint="render_pale",
            depth=6.0, d=0.0, panes="t" ):
    """ A casement window in a hole: its reveal, the glass at the back and the frame's bars just in front of it.
    panes 't' is a mullion and a transom (the usual T), '+' a cross, '|' a mullion, '' none. """
    reveal( model, face, reveal_paint, r0, r1, z0, z1, depth, d )
    back = d - depth
    face.quad( model, glass, r0, r1, z0, z1, back )
    f, bar = back + 0.6, 3.0
    face.quad( model, frame, r0, r0 + bar, z0, z1, f )
    face.quad( model, frame, r1 - bar, r1, z0, z1, f )
    face.quad( model, frame, r0 + bar, r1 - bar, z1 - bar, z1, f )
    face.quad( model, frame, r0 + bar, r1 - bar, z0, z0 + bar, f )
    rc, transom = ( r0 + r1 ) / 2, z0 + ( z1 - z0 ) * 0.72
    if panes in ( "t", "+" , "|" ):
        face.quad( model, frame, rc - 1.5, rc + 1.5, z0 + bar, transom if panes == "t" else z1 - bar, f + 0.2 )
    if panes in ( "t", "+" ):
        face.quad( model, frame, r0 + bar, r1 - bar, transom - 1.5, transom + 1.5, f + 0.2 )


def dress_window( model, face, r0, r1, z0, z1, paint, hood=None, surround=True, sill_paint=None, sill=True ):
    """ A window's stone dressing: a sill 4 proud, a surround 2 proud and a hood over it ('cornice', 'pediment',
    'arch' or None). """
    if sill:
        face.box( model, r0 - 4, r1 + 4, 0, 4, z0 - 5, z0, sill_paint or paint )
    if surround:
        face.box( model, r0 - 6, r0, 0, 2, z0, z1 + 6, paint )
        face.box( model, r1, r1 + 6, 0, 2, z0, z1 + 6, paint )
        face.box( model, r0 - 6, r1 + 6, 0, 2, z1, z1 + 6, paint )
    top = z1 + ( 6 if surround else 0 )
    if hood == "cornice":
        face.box( model, r0 - 10, r1 + 10, 0, 3, top, top + 5, paint )
        face.box( model, r0 - 12, r1 + 12, 0, 5, top + 5, top + 10, paint )
    elif hood == "pediment":
        face.box( model, r0 - 10, r1 + 10, 0, 4, top, top + 4, paint )
        rc = ( r0 + r1 ) / 2
        face.prism( model, paint, [ ( r0 - 10, top + 4 ), ( r1 + 10, top + 4 ), ( rc, top + 20 ) ], 0, 4 )
    elif hood == "arch":
        rc = ( r0 + r1 ) / 2
        face.prism( model, paint, [ ( r0 - 6, top ), ( r1 + 6, top ), ( r1, top + 7 ), ( rc, top + 11 ), ( r0, top + 7 ) ], 0, 3 )


def railing( model, a, b, height=40.0, paint="iron_black", spacing=5.0 ):
    """ A wrought-iron railing from a to b (plan points at its foot): a top rail, a bottom rail and bars. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    rod( model, a + up * height, b + up * height, 1.6, paint )
    rod( model, a + up * 4, b + up * 4, 1.2, paint )
    count = max( 1, int( np.linalg.norm( b - a ) / spacing ) )
    for k in range( count + 1 ):
        p = a + ( b - a ) * k / count
        model.box( p + ( -0.4, -0.4, 0.0 ), p + ( 0.4, 0.4, height ), paint, skip=( "+z", "-z" ) )


# ---------------------------------------------------------------------------------------------------------------------
# Atlases (railhead_materials draws them; while it hasn't, the signs show the whole atlas)

_missing_atlas = set()


def materials():
    try:
        import railhead_materials as RM
        return RM
    except Exception:
        return None


def rect_uv( atlas, name ):
    RM = materials()
    if RM is not None and hasattr( RM, "rect_uv" ):
        try:
            return RM.rect_uv( atlas, name )
        except Exception:
            pass
    _missing_atlas.add( ( atlas, name ) )
    return ( 0.0, 0.0, 1.0, 1.0 )


def atlas_quad( model, face, atlas, name, r0, r1, z0, z1, d ):
    u0, v0, u1, v1 = rect_uv( atlas, name )
    face.quad( model, atlas, r0, r1, z0, z1, d, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# Tenements

WALLS = ( "render_cream", "render_ochre", "render_pale", "render_rose", "render_sage", "render_blue", "render_terracotta",
          "render_cream", "render_ochre", "render_pale" )
SIGNS = ( "baeckerei", "apotheke", "imbiss", "reisebuero", "cafe", "friseur", "kiosk", "buchhandlung", "blumen", "optik",
          "pension", "metzgerei", "pizzeria", "schuhmacher", "schluesseldienst", "getraenke", "tabak" )


class Look:
    """ One house's style, rolled from its key. """

    def __init__( self, key, grand=False ):
        self.key = key
        brick = chance( 0.15, key, "brick" ) and not grand
        self.wall = "brick" if brick else pick( WALLS, key, "wall" )
        self.dressing = "rw_dressed" if brick or grand else \
            pick( ( "rw_dressed", "rw_dressed", "render_pale", "trim_white", "rw_sandstone" ), key, "dress" )
        if self.dressing == self.wall:
            self.dressing = "rw_dressed"
        self.ground_paint = pick( ( "rw_sandstone", "rw_dressed", "rw_sandstone", self.wall ), key, "ground" )
        self.plinth = pick( ( "ashlar_grey", "rw_sandstone", "ashlar_grey" ), key, "plinth" )
        self.reveal = self.dressing if chance( 0.5, key, "reveal" ) or brick else self.wall
        self.frame = pick( ( "trim_white", "trim_white", "trim_white", "trim_brown", "trim_green" ), key, "frame" )
        self.door = pick( ( "planks_dark", "trim_brown", "trim_green", "planks_dark" ), key, "door" )
        self.roof_kind = pick( ( "mansard", "mansard", "pitched" ), key, "roof" )
        self.roof = "slate" if self.roof_kind == "mansard" else pick( ( "roof_tiles", "slate", "roof_tiles" ), key, "tiles" )
        self.ground = between( 186.0, 204.0, key, "g" )
        self.storeys = 4
        self.storey = between( 132.0, 144.0, key, "s" )
        self.attic = pick( ( 16.0, 16.0, 16.0, 62.0 ), key, "attic" )
        self.window = between( 44.0, 50.0, key, "w" )
        self.bay = between( 104.0, 118.0, key, "b" )
        self.margin = 30.0
        self.surrounds = grand or chance( 0.75, key, "sur" )
        self.hoods = [ pick( ( "pediment", "cornice", "arch" ), key, "h1" ), pick( ( "cornice", None, "arch" ), key, "h2" ),
                       pick( ( None, "cornice" ), key, "h3" ), None ]
        self.cornice = between( 18.0, 26.0, key, "c" )
        self.party = "brick" if brick else "render_pale"
        self.lisenes = chance( 0.6, key, "lis" )
        self.bands = chance( 0.5, key, "bands" )
        self.depth = BACK - EDGE
        self.cap = 860.0

    def eave( self ):
        return min( self.ground + self.storeys * self.storey + self.attic, self.cap )


class Unit:
    """ An opening on a ground floor: 'shop', 'door', 'arch' or 'window'. """

    def __init__( self, kind, r0, r1, sign=None, shutter=False ):
        self.kind, self.r0, self.r1, self.sign, self.shutter = kind, r0, r1, sign, shutter


def ground_units( width, look, key, special="door", at=None, shops=True ):
    """ The ground floor: the house door (or the carriage arch) and shops between piers either side of it. """
    m = 28.0
    half = { "door": 28.0, "arch": 68.0, None: 0.0 }[special]
    units = []
    if special:
        c = width * ( at if at is not None else pick( ( 0.3, 0.5, 0.7 ), key, "door" ) )
        c = min( max( c, m + half + 20 ), width - m - half - 20 )
        units.append( Unit( special, c - half, c + half ) )
        spans = [ ( m, c - half - 26 ), ( c + half + 26, width - m ) ]
    else:
        spans = [ ( m, width - m ) ]
    for a, b in spans:
        if b - a < 70:
            continue
        r = a
        for k, w in enumerate( split( b - a, 170.0, 290.0, key, "shops", a ) ):
            p0, p1 = r + 12, r + w - 12
            r += w
            if shops and p1 - p0 >= 120 and not chance( 0.15, key, "flat", a, k ):
                units.append( Unit( "shop", p0, p1, pick( SIGNS, key, "sign", a, k ), chance( 0.22, key, "shut", a, k ) ) )
            elif p1 - p0 >= 120:
                c = ( p0 + p1 ) / 2
                for cc in ( c - 0.25 * ( p1 - p0 ), c + 0.25 * ( p1 - p0 ) ):
                    units.append( Unit( "window", cc - look.window / 2, cc + look.window / 2 ) )
            elif p1 - p0 >= look.window + 10:
                c = ( p0 + p1 ) / 2
                units.append( Unit( "window", c - look.window / 2, c + look.window / 2 ) )
    return units


def shop( model, face, u, g, look, detail ):
    """ A shopfront: steel-framed glazing 10 back, its fascia with the shop's sign, or its roller shutter down. """
    r0, r1, top = u.r0, u.r1, g - 52
    reveal( model, face, look.ground_paint, r0, r1, 16, top, 10 )
    face.box( model, r0 - 6, r1 + 6, 0, 3.5, top + 4, top + 32, "rw_black" )
    sign_w = min( r1 - r0 - 24, 120.0 )
    c = ( r0 + r1 ) / 2
    atlas_quad( model, face, "rw_shopsigns", u.sign, c - sign_w / 2, c + sign_w / 2, top + 18 - sign_w / 10,
                top + 18 + sign_w / 10, 3.6 )
    if u.shutter:
        face.quad( model, "roller_grey", r0, r1, 16, top, -2 )
        face.box( model, r0, r1, -2, 0, top - 10, top, "rw_steel_dark", skip=( "-d", "+z" ) )
        return
    face.quad( model, "rw_steel_dark", r0, r1, 16, 34, -10 )
    face.quad( model, "rw_window_dark", r0, r1, 34, top, -10 )
    f = -9.4
    face.quad( model, "rw_steel_dark", r0, r1, 34, 37, f )
    face.quad( model, "rw_steel_dark", r0, r1, top - 36, top - 33, f )
    face.quad( model, "rw_steel_dark", r0, r0 + 3, 16, top, f )
    face.quad( model, "rw_steel_dark", r1 - 3, r1, 16, top, f )
    if detail == "near":
        door_r = r1 - 48 if ( int( u.r0 ) // 7 ) % 2 else r0 + 8
        face.quad( model, "rw_steel_dark", door_r, door_r + 3, 16, top - 33, f )
        face.quad( model, "rw_steel_dark", door_r + 37, door_r + 40, 16, top - 33, f )
        face.quad( model, "rw_steel_dark", door_r + 3, door_r + 37, 60, 62, f + 0.2 )
        count = max( 1, int( ( r1 - r0 ) / 90 ) )
        for k in range( 1, count ):
            r = r0 + ( r1 - r0 ) * k / count
            if not door_r - 4 < r < door_r + 44:
                face.quad( model, "rw_steel_dark", r - 1.5, r + 1.5, 16, top, f )


def house_door( model, face, u, g, look, detail ):
    """ The house door: a panelled double door 14 into the wall under a fanlight, in a stone surround. """
    r0, r1 = u.r0, u.r1
    top, leaf = g - 36, g - 74
    rc = ( r0 + r1 ) / 2
    reveal( model, face, look.ground_paint, r0, r1, 0, top, 14, bottom=False )
    face.level( model, "rw_sandstone", r0, r1, -14, 0, 6 )
    face.quad( model, "rw_sandstone", r0, r1, 0, 6, 0 )
    face.quad( model, look.door, r0, r1, 6, leaf, -14 )
    face.quad( model, look.frame, r0, r1, leaf, leaf + 5, -13.4 )
    face.quad( model, "rw_window_dark", r0, r1, leaf + 5, top, -14 )
    if detail == "near":
        for a, b in ( ( r0 + 4, rc - 3 ), ( rc + 3, r1 - 4 ) ):
            face.box( model, a, b, -14, -12.8, 18, 52, look.door )
            face.box( model, a, b, -14, -12.8, 62, leaf - 10, look.door )
        face.quad( model, "rw_black", rc - 0.6, rc + 0.6, 6, leaf, -13.6 )
    face.box( model, r0 - 9, r0, 0, 3, 0, top + 9, look.dressing )
    face.box( model, r1, r1 + 9, 0, 3, 0, top + 9, look.dressing )
    face.box( model, r0 - 9, r1 + 9, 0, 3, top, top + 9, look.dressing )
    face.box( model, r0 - 13, r1 + 13, 0, 5, top + 9, top + 14, look.dressing )


def carriage_arch( model, face, u, g, look ):
    """ The Durchfahrt: 3.5 m wide, round-headed, its double gate shut 20 back. """
    r0, r1 = u.r0, u.r1
    rc, rad = ( r0 + r1 ) / 2, ( r1 - r0 ) / 2
    crown = g - 24
    spring = crown - rad
    face.side( model, look.ground_paint, r0, -20, 0, 0, spring, 1.0 )
    face.side( model, look.ground_paint, r1, -20, 0, 0, spring, -1.0 )
    pts = K.arc( rc, spring, rad, 10, 180, 0 )
    for ( ra, za ), ( rb, zb ) in zip( pts, pts[1:] ):
        mr, mz = ( ra + rb ) / 2, ( za + zb ) / 2
        towards = face.R * ( rc - mr ) + face.Z * ( spring - mz )
        facing( model, look.ground_paint, [ face.p( ra, 0, za ), face.p( rb, 0, zb ), face.p( rb, -20, zb ),
                                             face.p( ra, -20, za ) ], towards )
    face.quad( model, "planks_dark", r0, r1, 0, spring, -20 )
    face.poly( model, "planks_dark", pts, -20 )
    face.quad( model, "rw_black", rc - 1.5, rc + 1.5, 0, crown, -19.4 )
    face.quad( model, "iron_black", r0, r1, 70, 73, -19.4 )
    outer = K.arc( rc, spring, rad + 12, 10, 180, 0 )
    for a, b, c, d in zip( pts, pts[1:], outer[1:], outer ):
        face.poly( model, look.dressing, [ a, b, c, d ], 1.5 )
    face.box( model, rc - 9, rc + 9, 0, 4, crown - 8, crown + 12, look.dressing )
    face.level( model, "setts", r0, r1, -20, 0, 0.2 )


def shifted( face, r0 ):
    """ The same face with r 0 moved to r0. """
    f = Face( ( 0, 0 ), ( face.D[0], face.D[1] ) )
    f.o = face.o + face.R * r0
    return f


def bay_centres( width, look ):
    n = max( 2, int( round( ( width - 2 * look.margin ) / look.bay ) ) )
    bay = ( width - 2 * look.margin ) / n
    return [ look.margin + bay * ( k + 0.5 ) for k in range( n ) ], bay


def front( model, face, width, look, key, units, detail="near", balconies=(), oriel=None, ext=( False, False ),
           skip_bays=() ):
    """ A tenement's street front along face, r 0..width: the ground floor's units under a string course, the upper
    storeys' windows, balconies and oriel, and the main cornice. ext extends the courses past an end, round a corner.
    Returns the eave. """
    g, eave, st = look.ground, look.eave(), look.storey
    top_upper = g + look.storeys * st
    near = detail == "near"
    # The ground floor
    holes, arches = [], []
    for u in units:
        if u.kind == "shop":
            holes.append( ( u.r0, u.r1, 16, g - 52 ) )
        elif u.kind == "door":
            holes.append( ( u.r0, u.r1, 0, g - 36 ) )
        elif u.kind == "arch":
            arches.append( ( u.r0, u.r1, g - 24 - ( u.r1 - u.r0 ) / 2, g - 24, 0 ) )
        else:
            holes.append( ( u.r0, u.r1, 60, g - 60 ) )
    holed_wall( model, face, look.ground_paint, 0, width, 0, g - 12, holes, arches=arches )
    for u in units:
        if u.kind == "shop":
            shop( model, face, u, g, look, detail )
        elif u.kind == "door":
            house_door( model, face, u, g, look, detail )
        elif u.kind == "arch":
            carriage_arch( model, face, u, g, look )
        else:
            window( model, face, u.r0, u.r1, 60, g - 60, look.frame, reveal_paint=look.ground_paint, depth=8,
                    panes="+" if near else "" )
            face.box( model, u.r0 - 4, u.r1 + 4, 0, 4, 55, 60, look.dressing )
    r = 0.0
    for a, b in sorted( ( u.r0 - 9, u.r1 + 9 ) for u in units if u.kind in ( "door", "arch" ) ) + [ ( width, width ) ]:
        if a > r:
            face.box( model, r, a, 0, 2.5, 0, 16, look.plinth )
        r = max( r, b )
    ra, rb = ( -6.0 if ext[0] else 0.0 ), ( width + 6.0 if ext[1] else width )
    face.box( model, ra, rb, 0, 6, g - 12, g, look.dressing )
    # The upper storeys
    centres, bay = bay_centres( width, look )
    hw = min( look.window, bay - 34 ) / 2
    holes, wins = [], []
    for s in range( look.storeys ):
        floor = g + s * st
        z0, z1 = floor + 30, floor + 30 + 0.62 * st
        for k, c in enumerate( centres ):
            if k in skip_bays or ( oriel and oriel[0] <= k <= oriel[1] and oriel[2] <= s <= oriel[3] ):
                continue
            french = ( k, s ) in balconies
            zz0 = floor + 4 if french else z0
            holes.append( ( c - hw, c + hw, zz0, z1 ) )
            wins.append( ( c - hw, c + hw, zz0, z1, s, french ) )
    if look.attic >= 56:
        for k, c in enumerate( centres ):
            if k not in skip_bays:
                holes.append( ( c - hw * 0.7, c + hw * 0.7, top_upper + 12, top_upper + 40 ) )
                wins.append( ( c - hw * 0.7, c + hw * 0.7, top_upper + 12, top_upper + 40, 4, False ) )
    holed_wall( model, face, look.wall, 0, width, g, eave, holes )
    for a, b, z0, z1, s, french in wins:
        panes = ( "|" if french or s == 4 else "t" ) if near else ""
        window( model, face, a, b, z0, z1, look.frame, reveal_paint=look.reveal, panes=panes )
        hood = look.hoods[s] if s < 4 else None
        if not near and hood == "pediment":
            hood = "cornice"
        if look.surrounds or hood or not look.bands:
            dress_window( model, face, a, b, z0, z1, look.dressing, hood, look.surrounds and s < 4,
                          sill=not french and not look.bands )
    if look.bands:
        for s in range( look.storeys ):
            z = g + s * st + 30
            gaps = sorted( ( w[0] - 1, w[1] + 1 ) for w in wins if w[4] == s and w[5] )
            r = 0.0
            for a, b in gaps + [ ( width, width ) ]:
                if a > r:
                    face.box( model, r, a, 0, 3, z - 6, z - 1, look.dressing )
                r = max( r, b )
    if look.lisenes:
        face.box( model, 0, 12, 0, 2, g, eave - 36, look.dressing )
        face.box( model, width - 12, width, 0, 2, g, eave - 36, look.dressing )
    # Balconies: a stone slab on two consoles, a wrought-iron railing
    for k, s in balconies:
        if k >= len( centres ):
            continue
        c, floor = centres[k], g + s * st
        b0, b1 = c - hw - 22, c + hw + 22
        face.box( model, b0, b1, 0, 26, floor - 8, floor + 2, look.dressing )
        for rr in ( b0 + 6, b1 - 12 ):
            face.box( model, rr, rr + 6, 0, 20, floor - 34, floor - 8, look.dressing )
        spacing = 5.0 if near else 12.0
        railing( model, face.p( b0 + 1, 25, floor + 2 ), face.p( b1 - 1, 25, floor + 2 ), spacing=spacing )
        railing( model, face.p( b0 + 1, 1, floor + 2 ), face.p( b0 + 1, 24, floor + 2 ), spacing=spacing )
        railing( model, face.p( b1 - 1, 1, floor + 2 ), face.p( b1 - 1, 24, floor + 2 ), spacing=spacing )
    if oriel:
        bay_oriel( model, face, centres, bay, hw, look, oriel, detail )
    # The main cornice: a frieze band, consoles and the corona, zinc-capped
    cd = look.cornice
    face.box( model, -4.0 if ext[0] else 0.0, width + ( 4.0 if ext[1] else 0.0 ), 0, 4, eave - 36, eave - 28, look.dressing )
    if near:
        count = max( 1, int( ( width - 20 ) / 42 ) )
        for k in range( count + 1 ):
            r = 10 + ( width - 20 ) * k / count
            face.box( model, r - 3, r + 3, 0, cd - 4, eave - 26, eave - 10, look.dressing )
    face.box( model, -cd if ext[0] else 0.0, width + ( cd if ext[1] else 0.0 ), 0, cd, eave - 10, eave,
              { "default": look.dressing, "+z": "metal" } )
    return eave


def bay_oriel( model, face, centres, bay, hw, look, oriel, detail ):
    """ An Erker: a box bay 24 deep over bays k0..k1 from storey s0 to s1, on a corbel, a balcony on its top. """
    k0, k1, s0, s1 = oriel
    g, st = look.ground, look.storey
    r0, r1 = centres[k0] - bay / 2 + 8, centres[k1] + bay / 2 - 8
    zb, zt, od = g + s0 * st - 6, g + ( s1 + 1 ) * st - 4, 24.0
    of = Face( ( 0, 0 ), ( face.D[0], face.D[1] ) )
    of.o = face.o + face.D * od
    holes = []
    for s in range( s0, s1 + 1 ):
        z0 = g + s * st + 30
        for k in range( k0, k1 + 1 ):
            holes.append( ( centres[k] - hw, centres[k] + hw, z0, z0 + 0.62 * st ) )
    holed_wall( model, of, look.wall, r0, r1, zb, zt, holes )
    for a, b, z0, z1 in holes:
        window( model, of, a, b, z0, z1, look.frame, reveal_paint=look.reveal, depth=4,
                panes="t" if detail == "near" else "" )
        of.box( model, a - 3, b + 3, 0, 3, z0 - 4, z0, look.dressing )
    face.side( model, look.wall, r0, 0, od, zb, zt, -1.0 )
    face.side( model, look.wall, r1, 0, od, zb, zt, 1.0 )
    for s in range( s0 + 1, s1 + 1 ):
        z = g + s * st
        face.box( model, r0 - 2, r1 + 2, 0, od + 3, z - 3, z + 3, look.dressing )
    face.box( model, r0 - 4, r1 + 4, 0, od + 4, zt, zt + 8, look.dressing )
    facing( model, look.dressing, [ face.p( r0, od, zb ), face.p( r1, od, zb ), face.p( r1, 0, zb - 40 ),
                                    face.p( r0, 0, zb - 40 ) ], face.D - face.Z )
    facing( model, look.dressing, [ face.p( r0, 0, zb - 40 ), face.p( r0, od, zb ), face.p( r0, 0, zb ) ], -face.R )
    facing( model, look.dressing, [ face.p( r1, 0, zb - 40 ), face.p( r1, od, zb ), face.p( r1, 0, zb ) ], face.R )
    spacing = 5.0 if detail == "near" else 12.0
    for a, b in ( ( ( r0 - 3, od + 3 ), ( r1 + 3, od + 3 ) ), ( ( r0 - 3, 1 ), ( r0 - 3, od + 3 ) ),
                  ( ( r1 + 3, 1 ), ( r1 + 3, od + 3 ) ) ):
        railing( model, face.p( a[0], a[1], zt + 8 ), face.p( b[0], b[1], zt + 8 ), spacing=spacing )


def roof_profile( look, depth, eave ):
    """ ( inset from the eave line, height ) up to the ridge. """
    if look.roof_kind == "mansard":
        return [ ( 0.0, eave ), ( 48.7, eave + 150.0 ),
                 ( depth / 2, eave + 150.0 + ( depth / 2 - 48.7 ) * math.tan( math.radians( 16 ) ) ) ]
    return [ ( 0.0, eave ), ( depth / 2, eave + depth / 2 * math.tan( math.radians( 40 ) ) ) ]


def house_roof( model, face, width, depth, eave, look, key, detail, hips=( False, False ), ends=( 0.0, 0.0 ),
                dormers=(), chimneys=True ):
    """ The roof over r 0..width, d -depth..0: a mansard (72 and 16 degrees, slate) or a 40-degree roof. A hipped end
    turns a corner; an unhipped end gets an end wall from height ends[i] up (0 for a party wall, None for none). """
    prof = roof_profile( look, depth, eave )
    upper = look.roof if look.roof_kind != "mansard" or chance( 0.6, key, "zinc" ) else "metal"

    def rs( x ):
        return x if hips[0] else 0.0

    def re( x ):
        return width - x if hips[1] else width

    for k, ( ( x0, z0 ), ( x1, z1 ) ) in enumerate( zip( prof, prof[1:] ) ):
        paint = look.roof if k == 0 else upper
        dz, dx = z1 - z0, x1 - x0
        for dd, sign in ( ( 0.0, 1.0 ), ( depth, -1.0 ) ):
            def d_at( x ):
                return -x if sign > 0 else -( depth - x )
            pts = [ face.p( rs( x0 ), d_at( x0 ), z0 ), face.p( re( x0 ), d_at( x0 ), z0 ),
                    face.p( re( x1 ), d_at( x1 ), z1 ), face.p( rs( x1 ), d_at( x1 ), z1 ) ]
            if re( x1 ) - rs( x1 ) < 1e-6:
                pts = pts[:3]
            facing( model, paint, pts, face.D * sign * dz + face.Z * dx )
        for end, hipped in ( ( 0, hips[0] ), ( 1, hips[1] ) ):
            if not hipped:
                continue
            r_at = ( lambda x: x ) if end == 0 else ( lambda x: width - x )
            pts = [ face.p( r_at( x0 ), -x0, z0 ), face.p( r_at( x0 ), -( depth - x0 ), z0 ),
                    face.p( r_at( x1 ), -( depth - x1 ), z1 ), face.p( r_at( x1 ), -x1, z1 ) ]
            if depth - 2 * x1 < 1e-6:
                pts = pts[:3]
            facing( model, paint, pts, face.R * ( -1 if end == 0 else 1 ) * dz + face.Z * dx )
    for end, hipped in ( ( 0, hips[0] ), ( 1, hips[1] ) ):
        z_from = ends[end]
        if hipped or z_from is None:
            continue
        r = 0.0 if end == 0 else width
        rz = [ ( 0.0, z_from ), ( 0.0, eave ) ] + [ ( -x, z ) for x, z in prof[1:] ] + \
             [ ( -( depth - x ), z ) for x, z in reversed( prof[:-1] ) ] + [ ( -depth, z_from ) ]
        facing( model, look.party, [ face.p( r, d, z ) for d, z in rz ], face.R * ( -1 if end == 0 else 1 ) )
    # Dormers on the front slope
    mansard = look.roof_kind == "mansard"
    slope = math.tan( math.radians( 72 if mansard else 40 ) )
    dfront, ztop = ( -14.0, eave + 128.0 ) if mansard else ( -30.0, eave + 100.0 )
    zf0 = eave - dfront * slope
    dback = -( ztop - eave ) / slope
    for c in dormers:
        ww = look.window * 0.85 + 14
        a, b = c - ww / 2, c + ww / 2
        win = ( c - look.window * 0.38, c + look.window * 0.38, zf0 + 8, ztop - 12 )
        holed_wall( model, face, look.party if mansard else look.wall, a, b, zf0, ztop, [ win ], d=dfront )
        window( model, face, *win, frame=look.frame, reveal_paint=look.party, depth=3, d=dfront,
                panes="|" if detail == "near" else "" )
        for r, towards in ( ( a, -1.0 ), ( b, 1.0 ) ):
            facing( model, "metal", [ face.p( r, dfront, zf0 ), face.p( r, dfront, ztop ), face.p( r, dback, ztop ) ],
                    face.R * towards )
        face.box( model, a - 3, b + 3, dback, dfront + 3, ztop, ztop + 6, "metal", skip=( "-z", "-d" ) )
    if chimneys:
        ridge = prof[-1][1]
        for t in ( 0.28, 0.72 ):
            r = width * t + between( -30, 30, key, "chim", t )
            if hips[0] and r < depth / 2 + 20 or hips[1] and r > width - depth / 2 - 20:
                continue
            face.box( model, r - 12, r + 12, -depth / 2 - 16, -depth / 2 + 16, ridge - 40, ridge + 48, "brick",
                      skip=( "-z", ) )
            face.box( model, r - 14, r + 14, -depth / 2 - 18, -depth / 2 + 18, ridge + 48, ridge + 53,
                      "rw_concrete", skip=() )


def back_wall( model, face, width, depth, eave, look, detail ):
    """ The courtyard side: plain render with its windows drawn flat. """
    back = face.back( depth, width )
    back.quad( model, look.party, 0, width, 0, eave )
    if detail == "far":
        return
    count = max( 2, int( width / 120 ) )
    for s in range( look.storeys ):
        z0 = look.ground + s * look.storey + 30
        for k in range( count ):
            c = width * ( k + 0.5 ) / count
            back.quad( model, "rw_window_dark", c - 20, c + 20, z0, z0 + 76, 0.3 )


def turret( model, face, look, eave, detail, r=16.0, d=-16.0, side=-1.0 ):
    """ A corner turret: an octagon 44 in radius on a corbel, its windows on every storey, a copper helm. """
    c = face.p( r, d, 0 )[:2]
    g, st = look.ground, look.storey
    z0, z1 = g + 6, eave + 40
    model.cylinder( c, 44.0, z0, z1, { "side": look.wall, "top": None, "bottom": None }, sides=8, turn=math.pi / 8 )
    lathe( model, c, [ ( 6.0, z0 - 60 ), ( 30.0, z0 - 30 ), ( 44.0, z0 ) ], look.dressing, sides=8, turn=math.pi / 8,
           cap=False )
    model.cylinder( c, 47.0, eave - 10, eave, look.dressing, sides=8, turn=math.pi / 8 )
    out = np.array( ( face.D[0] + side * face.R[0], face.D[1] + side * face.R[1] ) )
    apothem = 44.0 * math.cos( math.pi / 8 )
    for k in range( 8 ):
        a = math.pi / 8 + math.pi / 4 * ( k + 0.5 )
        n = np.array( ( math.cos( a ), math.sin( a ) ) )
        if np.dot( n, out ) < 0.2:
            continue
        t = np.array( ( -n[1], n[0] ) )
        base = c + n * ( apothem + 0.4 )
        for s in range( look.storeys ):
            wz0 = g + s * st + 30
            wz1 = wz0 + 0.62 * st
            for paint, w, dz, off in ( ( look.dressing, 13.0, 4.0, 0.0 ), ( "rw_window_dark", 9.0, 0.0, 0.5 ) ):
                p = base + n * off
                pts = [ ( *( p - t * w ), wz0 - dz ), ( *( p + t * w ), wz0 - dz ), ( *( p + t * w ), wz1 + dz ),
                        ( *( p - t * w ), wz1 + dz ) ]
                facing( model, paint, pts, ( n[0], n[1], 0.0 ) )
    lathe( model, c, [ ( 47.0, z1 ), ( 47.0, z1 + 8 ), ( 40.0, z1 + 8 ), ( 34.0, z1 + 70 ), ( 40.0, z1 + 110 ),
                       ( 26.0, z1 + 150 ), ( 8.0, z1 + 175 ), ( 5.0, z1 + 210 ), ( 0.0, z1 + 260 ) ],
           "copper", sides=8, turn=math.pi / 8 )


def decorations( width, look, key ):
    """ Which bays get balconies ( bay, storey ), and an oriel ( k0, k1, s0, s1 ) or None. """
    centres, _ = bay_centres( width, look )
    n, km = len( centres ), len( centres ) // 2
    balconies, oriel = set(), None
    if n >= 4 and chance( 0.3, key, "oriel" ):
        oriel = ( km - 1 if n % 2 == 0 else km, km, 0, 2 )
        if n >= 6 and chance( 0.5, key, "obal" ):
            balconies |= { ( 0, 0 ), ( 0, 1 ), ( n - 1, 0 ), ( n - 1, 1 ) }
    elif chance( 0.45, key, "bal" ):
        balconies |= { ( km, s ) for s in ( 0, 1, 2 ) }
        if n % 2 == 0:
            balconies |= { ( km - 1, s ) for s in ( 0, 1, 2 ) }
    elif n >= 4 and chance( 0.35, key, "bal2" ):
        balconies |= { ( 0, 0 ), ( n - 1, 0 ) }
    return balconies, oriel


def plain_side( model, face, width, look, eave, detail ):
    """ A side wall onto a lane: render, a stair window between each pair of storeys, the cornice carried round. """
    g, st = look.ground, look.storey
    holes = []
    for s in range( look.storeys ):
        z0 = g + s * st + st / 2 + 10
        for c in ( width * 0.3, width * 0.7 ):
            holes.append( ( c - 18, c + 18, z0, z0 + 70 ) )
    holed_wall( model, face, look.wall, 0, width, 0, eave, holes )
    for a, b, z0, z1 in holes:
        window( model, face, a, b, z0, z1, look.frame, reveal_paint=look.wall, panes="+" if detail == "near" else "" )
        face.box( model, a - 3, b + 3, 0, 3, z0 - 4, z0, look.dressing )
    face.box( model, 0, width, 0, 2.5, 0, 16, look.plinth )
    face.box( model, 0, width, 0, look.cornice, eave - 10, eave, { "default": look.dressing, "+z": "metal" } )
    face.box( model, 0, width, 0, 4, eave - 36, eave - 28, look.dressing )


def row( model, face, length, key, detail="near", start=None, end=None, arch_at=None, turrets=( False, False ),
         collide=True, depth=None, widths=( 420.0, 780.0 ), shops=True, back=True ):
    """ A row of tenements along face from r 0 to length, depth deep. start / end say what the row's ends are:
    'corner' (a hipped corner house with a side front), 'lane' (a plain side wall), or None (a party wall). arch_at is
    an r where a house gets the carriage arch. Returns the houses ( r0, width, eave ). """
    depth = depth or ( BACK - EDGE )
    pieces = split( length, *widths, key, "widths" )
    houses, r = [], 0.0
    for i, w in enumerate( pieces ):
        hkey = ( key, i )
        look = Look( hkey )
        sub = shifted( face, r )
        first, last = i == 0, i == len( pieces ) - 1
        special, at = "door", None
        if arch_at is not None and r <= arch_at < r + w and w >= 470 and not first and not last:
            special, at = "arch", ( arch_at - r ) / w
        units = ground_units( w, look, hkey, special, at, shops )
        hips = ( first and start == "corner", last and end == "corner" )
        balconies, oriel = decorations( w, look, hkey )
        eave = front( model, sub, w, look, hkey, units, detail, balconies, oriel, hips )
        ends = [ 0.0, 0.0 ]
        if first and start == "lane":
            ends[0] = eave
        if last and end == "lane":
            ends[1] = eave
        centres, _ = bay_centres( w, look )
        clear = 60.0 if look.roof_kind == "mansard" else 130.0
        dormers = [ c for k, c in enumerate( centres )
                    if ( look.roof_kind == "mansard" or k % 2 == 1 )
                    and not ( hips[0] and c < clear + 30 ) and not ( hips[1] and c > w - clear - 30 ) ]
        house_roof( model, sub, w, depth, eave, look, hkey, detail, hips, tuple( ends ), dormers )
        if back:
            back_wall( model, sub, w, depth, eave, look, detail )
        if hips[0] or ( first and start == "lane" ):
            side = Face( ( 0, 0 ), ( -face.R[0], -face.R[1] ) )
            side.o = sub.o - face.D * depth
            if hips[0]:
                side_units = ground_units( depth, look, ( hkey, "side" ), "door", 0.3, shops )
                front( model, side, depth, look, ( hkey, "side" ), side_units, detail )
                if turrets[0]:
                    turret( model, sub, look, eave, detail, 16.0, -16.0, -1.0 )
            else:
                plain_side( model, side, depth, look, eave, detail )
        if hips[1] or ( last and end == "lane" ):
            side = Face( ( 0, 0 ), ( face.R[0], face.R[1] ) )
            side.o = sub.o + face.R * w
            if hips[1]:
                side_units = ground_units( depth, look, ( hkey, "side" ), "door", 0.7, shops )
                front( model, side, depth, look, ( hkey, "side" ), side_units, detail )
                if turrets[1]:
                    turret( model, sub, look, eave, detail, w - 16.0, -16.0, 1.0 )
            else:
                plain_side( model, side, depth, look, eave, detail )
        if collide:
            model.collision_box( sub.p( 0, -depth, ROAD_Z ), sub.p( w, 0, eave ), STONE )
        houses.append( ( r, w, eave ) )
        r += w
    return houses


def lane( model, s ):
    """ The lane between the bonded warehouse and the row, its iron gate shut onto the cab road's pavement. """
    e = lambda x: s * x
    lo, hi = sorted( ( e( EDGE ), e( BACK ) ) )
    flat( model, "setts", lo, hi, LANE_N0, ROW_N0, 0.0 )
    # The wall at its far end, and on from the warehouse's back corner
    model.box( ( e( BACK ), LANE_N0, 0 ), ( e( BACK + 24 ), ROW_N0, 300 ), { "default": "brick", "+z": "rw_concrete" },
               skip=( "-z", ) )
    model.box( ( e( WAREHOUSE_E1 ), LANE_N0 - 24, 0 ), ( e( BACK + 24 ), LANE_N0, 360 ),
               { "default": "brick", "+z": "rw_concrete" }, skip=( "-z", ) )
    flat( model, "gravel", *sorted( ( e( WAREHOUSE_E1 ), e( BACK ) ) ), PLAY_N0, LANE_N0 - 24, 0.0 )
    # The gate: two stone piers and a pair of iron leaves
    for n0, n1 in ( ( LANE_N0, LANE_N0 + 16 ), ( ROW_N0 - 16, ROW_N0 ) ):
        model.box( ( e( EDGE ), n0, 0 ), ( e( EDGE + 16 ), n1, 250 ), "rw_sandstone", skip=( "-z", ) )
        model.box( ( e( EDGE - 2 ), n0 - 2, 250 ), ( e( EDGE + 18 ), n1 + 2, 258 ), "rw_sandstone" )
    mid = ( LANE_N0 + ROW_N0 ) / 2
    for a, b in ( ( LANE_N0 + 16, mid - 1 ), ( mid + 1, ROW_N0 - 16 ) ):
        railing( model, ( e( EDGE + 8 ), a, 2 ), ( e( EDGE + 8 ), b, 2 ), height=216.0, spacing=6.0 )
        rod( model, ( e( EDGE + 8 ), a, 110 ), ( e( EDGE + 8 ), b, 110 ), 1.6, "iron_black" )
    model.collision_box( ( e( EDGE ), LANE_N0, 0 ), ( e( EDGE + 16 ), ROW_N0, 258 ), "metal" )


def edge_blocks( side=1 ):
    """ The play area's side wall: the row of tenements across the cab road, east ( side 1 ) or west ( -1 ). """
    model = K.Model()
    length = ROW_N1 - ROW_N0
    if side > 0:
        face = Face( ( EDGE, ROW_N1 ), ( -1, 0 ) )            # r runs south from the north corner
        row( model, face, length, "east", "near", "corner", "lane", arch_at=ROW_N1 - 300.0, turrets=( True, False ) )
    else:
        face = Face( ( -EDGE, ROW_N0 ), ( 1, 0 ) )            # r runs north from the lane
        row( model, face, length, "west", "near", "lane", "corner", arch_at=300.0 - ROW_N0, turrets=( False, True ) )
    lane( model, 1.0 if side > 0 else -1.0 )
    return configure( model )


# ---------------------------------------------------------------------------------------------------------------------
# Paints

FACADES = ( "rw_facade_cream", "rw_facade_ochre", "rw_facade_grey", "rw_facade_rose" )
RW_TILES = {
    "rw_paving": 160, "rw_paving_warm": 160, "rw_paving_dark": 160, "rw_tactile": 24, "rw_tactile_dots": 24,
    "rw_coping": 48, "rw_line_white": 32, "rw_line_yellow": 32, "rw_hazard": 32, "rw_ballast": 160,
    "rw_ballast_rusty": 160, "rw_ballast_old": 160, "rw_sleeper": 48, "rw_sleeper_wood": 48, "rw_rail": 32,
    "rw_rail_head": 32, "rw_asphalt": 192, "rw_kerb": 48, "rw_concrete": 256, "rw_concrete_dark": 256,
    "rw_terrazzo": 192, "rw_terrazzo_border": 192, "rw_sandstone": 192, "rw_dressed": 96, "rw_dressed_red": 96,
    "rw_steel": 64, "rw_steel_dark": 64, "rw_steel_grey": 64, **{ p: 276 for p in FACADES },
}


def configure( model ):
    """ Point the railhead paints at their materials, with their tile sizes (railhead_materials' if it has them), and
    stand the facade pictures on z 0. Building_textures' paints need nothing. """
    RM = materials()
    for paint in list( model.polygons ):
        if not paint.startswith( "rw_" ):
            continue
        model.material_overrides[paint] = f"materials/railhead/{paint}.vmat"
        tile = None
        if RM is not None:
            for name in ( "tile_units", "tile" ):
                if hasattr( RM, name ):
                    try:
                        tile = float( getattr( RM, name )( paint ) )
                        break
                    except Exception:
                        tile = None
            if tile is None:
                table = getattr( RM, "TILES", None )
                if isinstance( table, dict ) and paint in table:
                    tile = float( table[paint] )
        model.tile_overrides[paint] = tile if tile else float( RW_TILES.get( paint, 64 ) )
    model.anchored_paints = { p for p in model.polygons if p in FACADES }
    model.decal_paints = set()
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Streets and their furniture

POSTERS = ( "poster_alps", "poster_sea", "poster_city", "poster_bike" )         # rw_posters' travel posters


def post( model, c, radius, z0, z1, paint, sides=6, top=True ):
    """ An upright round post (no bottom face). """
    model.cylinder( c, radius, z0, z1, { "side": paint, "top": paint if top else None, "bottom": None }, sides=sides )


def tree( model, path, e, n, z, key, scale=1.0 ):
    """ A cloud tree or bush, turned and sized by its key. """
    s = scale * between( 0.88, 1.12, key, "scale" )
    name = "oak" if path in ( OAK, OAK_BIG ) else "bush"
    model.props.append( dict( path=path, position=( float( e ), float( n ), float( z ) ), yaw=between( 0, 360, key, "yaw" ),
                              scale=( s, s, s ), name=f"{name}_{len( model.props )}" ) )


def island( model, e0, e1, n0, n1, kerbs=(), paint="rw_paving", kerb_w=10.0 ):
    """ A pavement at z 0 over the carriageways' z -6: its top, and a granite kerb along each side in kerbs ('-e', '+e',
    '-n', '+n') with that side's 6-inch face. """
    a0 = e0 + ( kerb_w if "-e" in kerbs else 0 )
    a1 = e1 - ( kerb_w if "+e" in kerbs else 0 )
    b0 = n0 + ( kerb_w if "-n" in kerbs else 0 )
    b1 = n1 - ( kerb_w if "+n" in kerbs else 0 )
    flat( model, paint, a0, a1, b0, b1, 0.0 )
    z0 = ROAD_Z
    if "-e" in kerbs:
        flat( model, "rw_kerb", e0, a0, n0, n1, 0.0 )
        facing( model, "rw_kerb", [ ( e0, n0, z0 ), ( e0, n1, z0 ), ( e0, n1, 0 ), ( e0, n0, 0 ) ], ( -1, 0, 0 ) )
    if "+e" in kerbs:
        flat( model, "rw_kerb", a1, e1, n0, n1, 0.0 )
        facing( model, "rw_kerb", [ ( e1, n0, z0 ), ( e1, n1, z0 ), ( e1, n1, 0 ), ( e1, n0, 0 ) ], ( 1, 0, 0 ) )
    if "-n" in kerbs:
        flat( model, "rw_kerb", a0, a1, n0, b0, 0.0 )
        facing( model, "rw_kerb", [ ( e0, n0, z0 ), ( e1, n0, z0 ), ( e1, n0, 0 ), ( e0, n0, 0 ) ], ( 0, -1, 0 ) )
    if "+n" in kerbs:
        flat( model, "rw_kerb", a0, a1, b1, n1, 0.0 )
        facing( model, "rw_kerb", [ ( e0, n1, z0 ), ( e1, n1, z0 ), ( e1, n1, 0 ), ( e0, n1, 0 ) ], ( 0, 1, 0 ) )


def mark( model, paint, e0, e1, n0, n1 ):
    """ A road marking, a whisker over the carriageway. """
    flat( model, paint, e0, e1, n0, n1, ROAD_Z + 0.05 )


def street_lamp( model, e, n, out, z=0.0 ):
    """ A street lamp: an 8 m steel mast at the kerb, its arm reaching 1.5 m out over the road, the lantern under it,
    its opal diffuser dark by day. """
    post( model, ( e, n ), 5.0, z, z + 36, "rw_steel_grey", sides=6 )
    post( model, ( e, n ), 3.0, z + 36, z + 312, "rw_steel_grey", sides=6 )
    tip = np.array( ( e + out[0] * 60, n + out[1] * 60, z + 318 ) )
    rod( model, ( e, n, z + 306 ), tip, 3.0, "rw_steel_grey" )
    lo, hi = tip - ( 11, 11, 8 ), tip + ( 11, 11, 0 )
    model.box( lo, hi, { "default": "rw_steel_grey", "-z": "rw_opal_glass" } )


def lantern( model, a ):
    """ A four-sided lantern standing on a ( e, n, z ) socket: opal panes widening upwards between iron corner posts,
    a crown ring, a pyramid roof and a finial. The lamps are off by day. """
    e, n, z = a
    lathe( model, ( e, n ), [ ( 1.6, z - 4.0 ), ( 3.6, z ), ( 0.0, z ) ], "iron_black", sides=8, cap=False )
    lo, hi, z0, z1 = 4.4, 6.6, z + 1.0, z + 15.0
    model.box( ( e - lo - 0.6, n - lo - 0.6, z ), ( e + lo + 0.6, n + lo + 0.6, z0 ), "iron_black" )
    corners = [ ( 1, 1 ), ( -1, 1 ), ( -1, -1 ), ( 1, -1 ) ]
    for ( sa, ta ), ( sb, tb ) in zip( corners, corners[1:] + corners[:1] ):
        out = np.array( ( sa + sb, ta + tb, 0.0 ) ) / 2.0
        facing( model, "rw_opal_glass", [ ( e + sa * lo, n + ta * lo, z0 ), ( e + sb * lo, n + tb * lo, z0 ),
                                          ( e + sb * hi, n + tb * hi, z1 ), ( e + sa * hi, n + ta * hi, z1 ) ],
                out + ( 0, 0, -0.15 ) )
    for sa, ta in corners:
        rod( model, ( e + sa * lo, n + ta * lo, z0 ), ( e + sa * hi, n + ta * hi, z1 ), 0.9, "iron_black" )
    model.box( ( e - hi - 0.8, n - hi - 0.8, z1 ), ( e + hi + 0.8, n + hi + 0.8, z1 + 2.0 ), "iron_black" )
    lathe( model, ( e, n ), [ ( ( hi + 1.6 ) * math.sqrt( 2 ), z1 + 2.0 ), ( 2.0, z1 + 10.0 ), ( 1.0, z1 + 11.0 ),
                              ( 1.6, z1 + 12.5 ), ( 0.0, z1 + 15.0 ) ], "iron_black", sides=4, turn=math.pi / 4,
           cap=False )


def platz_lamp( model, e, n ):
    """ A cast-iron candelabrum 4.7 m tall: a fluted shaft on a stepped base, two arms with lanterns. """
    lathe( model, ( e, n ), [ ( 12.0, 0.0 ), ( 12.0, 16.0 ), ( 8.0, 24.0 ), ( 5.0, 40.0 ), ( 3.4, 150.0 ), ( 5.0, 156.0 ),
                              ( 2.6, 164.0 ) ], "iron_black", sides=6, cap=False )
    for s in ( -1.0, 1.0 ):
        a = np.array( ( e + s * 24, n, 166.0 ) )
        rod( model, ( e, n, 152.0 ), a - ( 0, 0, 4.0 ), 2.0, "iron_black" )
        lantern( model, a )


def litfass( model, e, n, key ):
    """ An advertising column (Litfasssaeule): 1.3 m across, posters to 3 m, a cornice and a domed cap. """
    r, sides = 26.0, 10
    post( model, ( e, n ), r + 3, 0, 14, "trim_green", sides=sides )
    for k in range( sides ):
        a0, a1 = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        p0 = ( e + r * math.cos( a0 ), n + r * math.sin( a0 ) )
        p1 = ( e + r * math.cos( a1 ), n + r * math.sin( a1 ) )
        u0, v0, u1, v1 = rect_uv( "rw_posters", pick( POSTERS, key, k // 2 ) )
        half = k % 2
        ua, ub = u0 + ( u1 - u0 ) * half / 2, u0 + ( u1 - u0 ) * ( half + 1 ) / 2
        mid = ( math.cos( ( a0 + a1 ) / 2 ), math.sin( ( a0 + a1 ) / 2 ), 0.0 )
        facing( model, "rw_posters", [ ( *p0, 14.0 ), ( *p1, 14.0 ), ( *p1, 118.0 ), ( *p0, 118.0 ) ], mid,
                uv=[ ( ua, v0 ), ( ub, v0 ), ( ub, v1 ), ( ua, v1 ) ] )
    lathe( model, ( e, n ), [ ( r, 118.0 ), ( r + 4, 120.0 ), ( r + 4, 128.0 ), ( r - 2, 132.0 ), ( r * 0.8, 146.0 ),
                              ( r * 0.4, 156.0 ), ( 3.0, 160.0 ), ( 3.0, 170.0 ), ( 0.0, 176.0 ) ], "trim_green", sides=sides )


def traffic_light( model, e, n, facing_n, lit="red" ):
    """ A traffic signal at a stop line, as German ones are (RiLSA): a galvanised pole 114 mm across and 3.6 m tall, and
    on two clamps on its traffic side a black head of three 200 mm lenses (red over amber over green), its lowest edge
    2.3 m up. Each lens has its visor (Schute), longest over the top, and the head stands in a black backplate with a
    white edge (Kontrastblende). lit: the lens that's on ("red", "amber", "green" or "red_amber"); the others are dark
    tinted glass. """
    d = 1.0 if facing_n > 0 else -1.0
    post( model, ( e, n ), 2.9, 0, 3, "rw_steel_grey", sides=12 )
    post( model, ( e, n ), 2.25, 3, 142, "rw_steel_grey", sides=12, top=False )
    lathe( model, ( e, n ), [ ( 2.5, 142.0 ), ( 2.5, 143.0 ), ( 1.6, 144.6 ), ( 0.0, 145.2 ) ], "rw_steel_grey", sides=12 )
    sec, hw = 10.4, 4.8
    z0 = 90.0
    z1 = z0 + 3 * sec
    back = n + d * 4.3
    front = back + d * 7.0
    model.box( ( e - hw, min( back, front ), z0 ), ( e + hw, max( back, front ), z1 ), "rw_black" )
    for k in ( 1, 2 ):                     # the joints between the sections
        zj = z0 + k * sec
        model.box( ( e - hw - 0.15, min( back, front ) - 0.15, zj - 0.25 ), ( e + hw + 0.15, max( back, front ) + 0.15,
                   zj + 0.25 ), "rw_steel_dark" )
    for zc in ( z0 + 6.0, z1 - 6.0 ):       # the clamps
        post( model, ( e, n ), 2.7, zc - 1.0, zc + 1.0, "rw_black", sides=12 )
        model.box( ( e - 1.3, min( n + d * 2.4, back ), zc - 1.3 ), ( e + 1.3, max( n + d * 2.4, back ), zc + 1.3 ),
                   "rw_black" )
    # The backplate, and its white edge on the face towards the traffic.
    plate = back + d * 1.5
    pw, pz0, pz1, edge = 8.4, z0 - 3.8, z1 + 3.8, 1.4
    model.box( ( e - pw, plate - 0.15, pz0 ), ( e + pw, plate + 0.15, pz1 ), "rw_black" )
    f = plate + d * 0.2
    for e0, e1, za, zb in ( ( -pw, pw, pz0, pz0 + edge ), ( -pw, pw, pz1 - edge, pz1 ), ( -pw, -pw + edge, pz0, pz1 ),
                            ( pw - edge, pw, pz0, pz1 ) ):
        facing( model, "rw_white_paint", [ ( e + e0, f, za ), ( e + e1, f, za ), ( e + e1, f, zb ), ( e + e0, f, zb ) ],
                ( 0, d, 0 ) )
    # The lenses and their visors.
    on = { "red": ( "red", ), "amber": ( "amber", ), "green": ( "green", ), "red_amber": ( "red", "amber" ) }[lit]
    r, rv, sides = 3.94, 4.5, 20
    for k, colour in enumerate( ( "green", "amber", "red" ) ):
        zc = z0 + sec * ( k + 0.5 )
        paint = ( "rw_signal_yellow" if colour == "amber" else f"rw_signal_{colour}" ) if colour in on else \
            f"rw_lens_{colour}"
        ring = [ 2 * math.pi * j / sides for j in range( sides ) ]
        facing( model, "rw_steel_dark", [ ( e + ( r + 0.5 ) * math.cos( t ), front + d * 0.05, zc + ( r + 0.5 ) * math.sin( t ) )
                                          for t in ring ], ( 0, d, 0 ) )
        facing( model, paint, [ ( e + r * math.cos( t ), front + d * 0.3, zc + r * math.sin( t ) ) for t in ring ],
                ( 0, d, 0 ) )
        arc = [ math.radians( -35.0 + 250.0 * j / 14 ) for j in range( 15 ) ]
        reach = lambda t: 3.0 + 4.5 * max( 0.0, math.sin( t ) )
        for ta, tb in zip( arc, arc[1:] ):
            ca, cb = np.array( ( math.cos( ta ), 0, math.sin( ta ) ) ), np.array( ( math.cos( tb ), 0, math.sin( tb ) ) )
            mid = ( ca + cb ) / 2
            for rad, out in ( ( rv, mid ), ( rv - 0.3, -mid ) ):
                pa = np.array( ( e, front, zc ) ) + ca * rad
                pb = np.array( ( e, front, zc ) ) + cb * rad
                facing( model, "rw_black", [ pa, pb, pb + ( 0, d * reach( tb ), 0 ), pa + ( 0, d * reach( ta ), 0 ) ],
                        out )
            c0 = np.array( ( e, front, zc ) )
            facing( model, "rw_black", [ c0 + ca * rv + ( 0, d * reach( ta ), 0 ), c0 + cb * rv + ( 0, d * reach( tb ), 0 ),
                                         c0 + cb * ( rv - 0.3 ) + ( 0, d * reach( tb ), 0 ),
                                         c0 + ca * ( rv - 0.3 ) + ( 0, d * reach( ta ), 0 ) ], ( 0, d, 0 ) )


def bench( model, e0, e1, n, out ):
    """ A park bench along e at n, its back to -out. """
    model.box( ( e0, n - 9, 16 ), ( e1, n + 9, 18 ), "rw_wood" )
    nb = n - out * 9
    model.box( ( e0, min( nb, nb - out * 2 ), 20 ), ( e1, max( nb, nb - out * 2 ), 34 ), "rw_wood" )
    for e in ( e0 + 6, e1 - 8 ):
        model.box( ( e, n - 9, 0 ), ( e + 2, n + 9, 16 ), "iron_black", skip=( "-z", ) )


def bike_stands( model, e0, n, count, step=30.0 ):
    """ A row of steel hoops (Anlehnbuegel), 0.8 m tall, along e. """
    for k in range( count ):
        e = e0 + k * step
        for nn in ( n - 14, n + 14 ):
            rod( model, ( e, nn, 0 ), ( e, nn, 30 ), 1.6, "rw_steel" )
        rod( model, ( e, n - 14, 30 ), ( e, n + 14, 30 ), 1.6, "rw_steel" )


# The cross street: its trams run along it, two tracks 3.0 m apart
TRAM_N = ( 2166.0, 2284.0 )
GAUGE = 56.5
WIRE_Z = 232.0                  # contact wire, 5.9 m over the rails
SPAN_Z = 272.0


def tram_track( model, e0, e1, n ):
    """ Grooved rail laid flush in the street: the heads and their grooves. """
    for s in ( -1.0, 1.0 ):
        c = n + s * ( GAUGE / 2 + 1.3 )
        flat( model, "rw_rail_head", e0, e1, c - 1.3, c + 1.3, ROAD_Z + 0.06 )
        g = n + s * ( GAUGE / 2 - 0.8 )
        flat( model, "rw_black", e0, e1, g - 0.8, g + 0.8, ROAD_Z + 0.06 )


def tram_wires( model, e0, e1, poles ):
    """ The overhead line: span wires between poles either side of the street, the contact wires along the tracks. """
    sides = ( CROSS_N0 - 14.0, CROSS_N1 + 14.0 )
    for e in poles:
        for n in sides:
            post( model, ( e, n ), 5.0, 0.0, 300.0, "rw_steel_grey", sides=6 )
        rod( model, ( e, sides[0], SPAN_Z ), ( e, sides[1], SPAN_Z ), 0.8, "rw_black" )
        for n in TRAM_N:
            rod( model, ( e, n, WIRE_Z ), ( e, n, SPAN_Z ), 0.6, "rw_black" )
    for n in TRAM_N:
        rod( model, ( e0, n, WIRE_Z ), ( e1, n, WIRE_Z ), 0.8, "rw_black" )


def tram_platform( model, e0, e1, n0, n1, edge ):
    """ A tram stop's platform 25 cm over the street (low-floor trams), its kerb at n edge (n0 or n1), a tactile line
    along it, and a glazed shelter. """
    out = 1.0 if edge == n1 else -1.0
    model.box( ( e0, n0, 0.0 ), ( e1, n1, 4.0 ), { "default": "rw_kerb", "+z": None }, skip=( "-z", ) )
    kerb = sorted( ( edge, edge - out * 10 ) )
    tact = sorted( ( edge - out * 22, edge - out * 34 ) )
    flat( model, "rw_kerb", e0, e1, *kerb, 4.0 )
    flat( model, "rw_tactile", e0, e1, *tact, 4.0 )
    inner = sorted( ( edge - out * 10, edge - out * 22 ) )
    flat( model, "rw_paving", e0, e1, *inner, 4.0 )
    rest = sorted( ( edge - out * 34, n0 if out > 0 else n1 ) )
    flat( model, "rw_paving", e0, e1, *rest, 4.0 )
    # The shelter: its back to the platform's far side
    back = n0 + 8 if out > 0 else n1 - 8
    front = back + out * 52
    for c in ( ( e0 + e1 ) / 2 - 260, ( e0 + e1 ) / 2 + 60 ):
        a, b = c, c + 200
        for e in ( a, ( a + b ) / 2, b ):
            for nn in ( back, front ):
                model.box( ( e - 1.5, nn - 1.5, 4 ), ( e + 1.5, nn + 1.5, 98 ), "rw_steel_dark", skip=( "-z", ) )
        model.box( ( a - 6, min( back, front ) - 6, 98 ), ( b + 6, max( back, front ) + 6, 103 ),
                   { "default": "rw_steel_dark", "+z": "rw_glass" } )
        model.polygon( "rw_glass", [ ( a, back, 14 ), ( b, back, 14 ), ( b, back, 92 ), ( a, back, 92 ) ], both_sides=True )
        model.polygon( "rw_glass", [ ( a, back, 14 ), ( a, front - out * 18, 14 ), ( a, front - out * 18, 92 ),
                                     ( a, back, 92 ) ], both_sides=True )
        # an advertising panel at its far end, and the bench
        u0, v0, u1, v1 = rect_uv( "rw_posters", pick( POSTERS, c, "shelter" ) )
        pts = [ ( b, back, 14 ), ( b, front - out * 6, 14 ), ( b, front - out * 6, 90 ), ( b, back, 90 ) ]
        model.box( ( b - 3, min( back, front - out * 6 ), 12 ), ( b + 3, max( back, front - out * 6 ), 92 ), "rw_steel_dark" )
        facing( model, "rw_posters", [ ( b + 3.2, p[1], p[2] ) for p in pts ], ( 1, 0, 0 ),
                uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] if out > 0 else [ ( u1, v0 ), ( u0, v0 ), ( u0, v1 ), ( u1, v1 ) ] )
        bench( model, a + 20, a + 120, back + out * 12, out )


# ---------------------------------------------------------------------------------------------------------------------
# North: the Bahnhofsplatz

SIDE_N0, SIDE_N1 = 3300.0, 3700.0       # the side street behind the hotel (pavements 80, carriageway 3380..3620)
HOTEL = ( 260.0, 1300.0, PLATZ_N1, SIDE_N0 )
KONTOR = ( -1300.0, -260.0, PLATZ_N1, SIDE_N0 )
FOUNTAIN = ( 0.0, 2520.0 )
FURT = 120.0                            # a signalled crossing's width between its two broken lines (3 m)


def isl( model, s, e0, e1, n0, n1, kerbs, paint="rw_paving" ):
    """ island() on the east side ( s 1 ), or mirrored to the west ( -1 ). """
    if s > 0:
        island( model, e0, e1, n0, n1, kerbs, paint )
    else:
        flip = { "-e": "+e", "+e": "-e" }
        island( model, -e1, -e0, n0, n1, tuple( flip.get( k, k ) for k in kerbs ), paint )


def furt( model, e0, e1, n ):
    """ A Fussgaengerfurt across a road at a signal: two broken lines, 0.5 m dashes and 0.2 m gaps, 12 cm wide, FURT
    apart from n. """
    for c in ( n, n + FURT ):
        e = e0 + 4
        while e + 20 <= e1 - 2:
            mark( model, "rw_line_white", e, e + 20, c - 2.5, c + 2.5 )
            e += 28


def dashes( model, e0, e1, n0, n1, along_n=True ):
    """ A centre line: 3 m dashes and 6 m gaps (a built-up area's Leitlinie), 12 cm wide. """
    if along_n:
        c, n = ( e0 + e1 ) / 2, n0
        while n + 60 < n1:
            mark( model, "rw_line_white", c - 2.5, c + 2.5, n, min( n + 120, n1 ) )
            n += 360
    else:
        c, e = ( n0 + n1 ) / 2, e0
        while e + 60 < e1:
            mark( model, "rw_line_white", e, min( e + 120, e1 ), c - 2.5, c + 2.5 )
            e += 360


def north_ground( model ):
    """ The pavements, the carriageways and their markings from the head building to the side street. """
    s0, s1 = SIDE_N0 + 80, SIDE_N1 - 80
    for s in ( 1.0, -1.0 ):
        isl( model, s, 1200, ROAD_E0, PLAY_N1, CROSS_N0, ( "+e", "+n" ) )            # the cab road's station side, on
        isl( model, s, ROAD_E1, EDGE, PLAY_N1, CROSS_N0, ( "-e", "+n" ) )            # its far side, to the corner
        isl( model, s, EDGE, BACK, CROSS_N0 - 60, CROSS_N0, ( "+n", ) )              # the cross street's south side
        isl( model, s, ROAD_E1, BACK, CROSS_N1, s0, ( "-e", "-n", "+n" ) )            # round the north row
        isl( model, s, 180, ROAD_E0, PLATZ_N1, s0, ( "-e", "+e", "+n" ) )             # round the hotel / the office block
        isl( model, s, 180, ROAD_E0, s1, SIDE_N1, ( "-e", "+e", "-n" ) )              # the side street's far side
        isl( model, s, ROAD_E1, BACK, s1, SIDE_N1, ( "-e", "-n" ) )

        def span( a, b ):
            return sorted( ( s * a, s * b ) )

        flat( model, "rw_asphalt", *span( ROAD_E0, ROAD_E1 ), PLAY_N1, SIDE_N1, ROAD_Z )
        flat( model, "rw_asphalt", *span( ROAD_E1, BACK ), CROSS_N0, CROSS_N1, ROAD_Z )
        flat( model, "rw_asphalt", *span( ROAD_E1, BACK ), s0, s1, ROAD_Z )
        flat( model, "rw_asphalt", *span( 180, ROAD_E0 ), s0, s1, ROAD_Z )
        # The cab road's centre line goes on from the lead's (e +-1797..1803), traffic keeping right: northbound on the
        # east half of each road, southbound on the west half.
        c0, c1 = span( 1797, 1803 )
        for n0, n1 in ( ( PLAY_N1, 1940.0 ), ( 2520.0, s0 - 40 ), ( s1 + 40, SIDE_N1 ) ):
            dashes( model, c0, c1, n0, n1 )
        north_bound = ( c1, ROAD_E1 if s > 0 else -ROAD_E0 )
        south_bound = ( ROAD_E0 if s > 0 else -ROAD_E1, c0 )
        mark( model, "rw_line_white", *north_bound, 1948.0, 1960.0 )          # stop lines (0.3 m) before the crossings
        mark( model, "rw_line_white", *south_bound, 2490.0, 2502.0 )
        lo, hi = span( ROAD_E0, ROAD_E1 )
        furt( model, lo, hi, 1972.0 )
        furt( model, lo, hi, 2356.0 )
        dashes( model, *span( ROAD_E1, BACK ), CROSS_N0, CROSS_N1, along_n=False )
        dashes( model, *span( ROAD_E1, BACK ), s0, s1, along_n=False )
        dashes( model, *span( 180, ROAD_E0 ), s0, s1, along_n=False )
    island( model, -1200, 1200, PLAY_N1, CROSS_N0, ( "+n", ), "rw_paving_warm" )                    # the forecourt
    island( model, -ROAD_E0, ROAD_E0, CROSS_N1, PLATZ_N1, ( "-e", "+e", "-n" ), "rw_paving_warm" )   # the Platz
    flat( model, "setts", -ROAD_E0, ROAD_E0, CROSS_N0, CROSS_N1, ROAD_Z )                            # the tram street
    flat( model, "rw_asphalt", -180, 180, PLATZ_N1, SIDE_N1, ROAD_Z )                                # Bahnhofstrasse
    facing( model, "rw_kerb", [ ( -180, PLATZ_N1, ROAD_Z ), ( 180, PLATZ_N1, ROAD_Z ), ( 180, PLATZ_N1, 0 ),
                                ( -180, PLATZ_N1, 0 ) ], ( 0, 1, 0 ) )
    dashes( model, -3, 3, PLATZ_N1 + 40, s0 - 40 )
    dashes( model, -3, 3, s1 + 40, SIDE_N1 )


def tramway( model ):
    """ The trams along the cross street: two tracks, the overhead line, and the stop in front of the station. """
    for n in TRAM_N:
        tram_track( model, -BACK, BACK, n )
    tram_wires( model, -BACK, BACK, ( -2400.0, -1300.0, -480.0, 480.0, 1300.0, 2400.0 ) )
    tram_platform( model, -700.0, 700.0, CROSS_N0 - 60, CROSS_N0, CROSS_N0 )
    tram_platform( model, -700.0, 700.0, CROSS_N1, CROSS_N1 + 60, CROSS_N1 )


def platz( model ):
    """ The Platz's furniture: two rows of trees (the cloud oaks), a fountain, candelabra, benches, bike stands,
    advertising columns, street lamps and the junction's signals. """
    fe, fn = FOUNTAIN
    lathe( model, ( fe, fn ), [ ( 150.0, 0.0 ), ( 150.0, 20.0 ), ( 145.0, 23.0 ), ( 138.0, 23.0 ), ( 138.0, 12.0 ) ],
           "rw_sandstone", sides=16, cap=False )
    model.polygon( "water", [ ( fe + 138 * math.cos( a ), fn + 138 * math.sin( a ), 12.0 )
                              for a in ( 2 * math.pi * k / 16 for k in range( 16 ) ) ] )
    lathe( model, ( fe, fn ), [ ( 22.0, 12.0 ), ( 16.0, 44.0 ), ( 44.0, 62.0 ), ( 46.0, 68.0 ), ( 10.0, 72.0 ),
                                ( 8.0, 112.0 ), ( 24.0, 120.0 ), ( 6.0, 126.0 ), ( 0.0, 140.0 ) ], "rw_sandstone", sides=10 )
    for n in ( 2440.0, 2620.0 ):
        for e in ( 420.0, 680.0, 940.0, 1200.0 ):
            for s in ( 1.0, -1.0 ):
                tree( model, OAK, s * e, n, 0.0, ( "platz", s, e, n ), 1.05 )
                flat( model, "rw_steel_dark", s * e - 30, s * e + 30, n - 30, n + 30, 0.05 )
    for s in ( 1.0, -1.0 ):
        for e, n in ( ( 290.0, 2420.0 ), ( 290.0, 2660.0 ), ( 1340.0, 2420.0 ), ( 1340.0, 2660.0 ), ( 560.0, 1880.0 ),
                      ( 1000.0, 1880.0 ) ):
            platz_lamp( model, s * e, n )
        for e0 in ( 520.0, 1050.0 ):
            e_lo, e_hi = sorted( ( s * e0, s * ( e0 + 90 ) ) )
            bench( model, e_lo, e_hi, 2500.0, 1.0 )
            bench( model, e_lo, e_hi, 2560.0, -1.0 )
        bike_stands( model, 640.0 if s > 0 else -880.0, 1960.0, 9 )
        litfass( model, s * 1350.0, 1960.0, ( "litfass", s ) )
        litfass( model, s * 2110.0, 2760.0 if s > 0 else 3020.0, ( "litfass2", s ) )
        # Signals on the right of the traffic they face
        traffic_light( model, 2012.0 if s > 0 else -1488.0, 1990.0, -1.0, "red" )
        traffic_light( model, 1488.0 if s > 0 else -2012.0, 2470.0, 1.0, "red" )
        for n in ( 2620.0, 3160.0 ):
            street_lamp( model, s * 2016.0, n, ( -s, 0 ) )
        for n in ( 2860.0, 3340.0 ):
            street_lamp( model, s * 1484.0, n, ( s, 0 ) )
        street_lamp( model, s * 196.0, 3000.0, ( -s, 0 ) )


def grand_look( key, **values ):
    look = Look( key, grand=True )
    for k, v in values.items():
        setattr( look, k, v )
    return look


def flat_window( model, face, r0, r1, z0, z1, frame, dressing ):
    """ A window drawn on the wall: its stone surround, the glass and a mullion (for towers and far fronts). """
    face.quad( model, dressing, r0 - 6, r1 + 6, z0 - 6, z1 + 6, 0.4 )
    face.quad( model, "rw_window_dark", r0, r1, z0, z1, 0.8 )
    face.quad( model, frame, ( r0 + r1 ) / 2 - 1.5, ( r0 + r1 ) / 2 + 1.5, z0, z1, 1.0 )


def cross_gable( model, face, r0, r1, eave, height, depth, look ):
    """ A Zwerchgiebel: the front carried up in a gable over r0..r1, its roof running back depth into the main one. """
    rc, half = ( r0 + r1 ) / 2, ( r1 - r0 ) / 2
    top = eave + height
    face.poly( model, look.wall, [ ( r0, eave ), ( r1, eave ), ( rc, top ) ], 0.0 )
    for ( ra, za ), ( rb, zb ), side in ( ( ( r0 - 8, eave - 4 ), ( rc, top + 6 ), -1.0 ),
                                          ( ( rc, top + 6 ), ( r1 + 8, eave - 4 ), 1.0 ) ):
        pts = [ face.p( ra, 8, za ), face.p( rb, 8, zb ), face.p( rb, -depth, zb ), face.p( ra, -depth, za ) ]
        facing( model, look.roof, pts, face.R * side * abs( zb - za ) + face.Z * abs( rb - ra ) )
        facing( model, look.dressing, [ face.p( ra, 8, za ), face.p( rb, 8, zb ), face.p( rb, 0, zb - 8 ),
                                        face.p( ra, 0, za - 8 ) ], face.D - face.Z * 0.5 )
    # Two windows and an oculus, kept inside the gable's slopes
    for c in ( rc - 32, rc + 32 ):
        flat_window( model, face, c - 17, c + 17, eave + 24, eave + 100, look.frame, look.dressing )

    def edge( r ):
        return eave + height * ( 1 - abs( r - rc ) / half )

    assert edge( rc - 55 ) > eave + 106 and edge( rc - 20 ) > eave + 184
    face.quad( model, look.dressing, rc - 20, rc + 20, eave + 144, eave + 184, 0.4 )
    face.quad( model, "rw_window_dark", rc - 13, rc + 13, eave + 151, eave + 177, 0.8 )


def hotel( model ):
    """ The Grand Hotel facing the station: five storeys of cream render over a sandstone ground floor, a mansard, a
    cross gable over the entrance and its marquee, a domed corner pavilion, and its name on the roof. """
    e0, e1, n0, n1 = HOTEL
    look = grand_look( "hotel", wall="render_cream", dressing="rw_sandstone", ground_paint="rw_sandstone",
                       plinth="ashlar_grey", reveal="rw_sandstone", frame="trim_white", roof_kind="mansard", roof="slate",
                       ground=230.0, storeys=5, storey=150.0, attic=16.0, window=52.0, bay=120.0, margin=40.0,
                       surrounds=True, hoods=[ "pediment", "cornice", "cornice", "arch" ], cornice=30.0,
                       party="render_pale", lisenes=True, bands=False, cap=1020.0 )
    eave = look.eave()
    south = Face( ( e0, n0 ), ( 0, -1 ) )
    east = Face( ( e1, n0 ), ( 1, 0 ) )
    north = Face( ( e1, n1 ), ( 0, 1 ) )
    west = Face( ( e0, n1 ), ( -1, 0 ) )
    w, d = e1 - e0, n1 - n0
    units = [ Unit( "shop", 48, 236, "cafe" ), Unit( "shop", 262, 446, "cafe" ), Unit( "door", 478, 562 ),
              Unit( "shop", 594, 778, "reisebuero" ), Unit( "shop", 804, 992, "blumen" ) ]
    front( model, south, w, look, "hotel_s", units, "near", { ( 3, 1 ), ( 4, 1 ) }, None, ( True, True ) )
    front( model, east, d, look, "hotel_e", ground_units( d, look, "hotel_e", "door", 0.72 ), "near", { ( 2, 1 ), ( 3, 1 ) },
           None, ( True, True ) )
    front( model, west, d, look, "hotel_w", ground_units( d, look, "hotel_w", "door", 0.5 ), "mid", (), None, ( True, True ) )
    front( model, north, w, look, "hotel_n", ground_units( w, look, "hotel_n", "door", 0.3, shops=False ), "far", (), None,
           ( True, True ) )
    centres, _ = bay_centres( w, look )
    dormers = [ c for k, c in enumerate( centres ) if k not in ( 3, 4 ) and c < 840 ]
    house_roof( model, south, w, d, eave, look, "hotel", "mid", ( True, True ), ( 0.0, 0.0 ), dormers )
    cross_gable( model, south, 400.0, 640.0, eave, 230.0, d / 2, look )
    # The marquee over the entrance: a steel canopy with the hotel's name on its fascia, hung from the wall on rods
    south.box( model, 456, 584, 0, 110, 206, 224, "rw_steel_dark" )
    atlas_quad( model, south, "rw_shopsigns", "hotel", 474, 566, 208, 222, 110.3 )
    for r in ( 460, 580 ):
        rod( model, south.p( r, 0, 330 ), south.p( r, 106, 224 ), 1.4, "rw_steel_dark" )
    # The corner pavilion over the south-east corner, and its copper dome
    size, high = 170.0, 200.0
    pe0, pn0 = e1 - size, n0
    model.box( ( pe0, pn0, eave ), ( e1, pn0 + size, eave + high ), { "default": look.wall, "+z": None, "-z": None } )
    for f in ( Face( ( pe0, pn0 ), ( 0, -1 ) ), Face( ( e1, pn0 ), ( 1, 0 ) ) ):
        for r in ( 46.0, 124.0 ):
            flat_window( model, f, r - 20, r + 20, eave + 40, eave + 150, look.frame, look.dressing )
        f.box( model, -8, size + 8, 0, 4, eave + 2, eave + 12, look.dressing )
    model.box( ( pe0 - 10, pn0 - 10, eave + high - 10 ), ( e1 + 10, pn0 + size + 10, eave + high + 2 ),
               { "default": look.dressing, "+z": "metal" } )
    c = ( pe0 + size / 2, pn0 + size / 2 )
    z = eave + high + 2
    lathe( model, c, [ ( 78.0, z ), ( 78.0, z + 40 ), ( 72.0, z + 44 ), ( 70.0, z + 70 ), ( 62.0, z + 104 ),
                       ( 46.0, z + 140 ), ( 24.0, z + 164 ), ( 13.0, z + 170 ), ( 13.0, z + 210 ), ( 17.0, z + 214 ),
                       ( 7.0, z + 228 ), ( 3.0, z + 276 ), ( 0.0, z + 300 ) ], "copper", sides=8, turn=math.pi / 8 )
    # The name on the roof: letters on a steel frame over the mansard's front
    sign_r0, sign_r1, base = 130.0, 370.0, eave + 154
    for r in ( sign_r0 + 20, sign_r1 - 20 ):
        rod( model, south.p( r, -62, base ), south.p( r, -62, base + 96 ), 3.0, "rw_steel_dark" )
    atlas_quad( model, south, "rw_shopsigns", "hotel", sign_r0, sign_r1, base + 36, base + 96, -58 )
    south.quad( model, "rw_steel_dark", sign_r0, sign_r1, base + 36, base + 96, -59, out=-1.0 )
    return eave


def kontor_face( model, face, width, z0, floors, top, ground, key, detail ):
    """ One face of the office block: clinker piers every ~1.9 m running up past the parapet into pointed tops, the
    windows in the bays between them, shopfronts under a fascia on the ground floor. floors are the upper storeys'
    floor heights. """
    bays = max( 3, int( round( width / 74.0 ) ) )
    bay = width / bays
    pier = 14.0
    g = 210.0
    holes, wins = [], []
    for f in floors:
        for k in range( bays ):
            a, b = k * bay + pier / 2 + 5, ( k + 1 ) * bay - pier / 2 - 5
            holes.append( ( a, b, f + 34, f + 122 ) )
            wins.append( ( a, b, f + 34, f + 122 ) )
    if ground:
        for k in range( bays ):
            holes.append( ( k * bay + pier / 2, ( k + 1 ) * bay - pier / 2, 14, g - 54 ) )
    holed_wall( model, face, "brick", 0, width, z0, top, holes, d=-6 )
    for a, b, wz0, wz1 in wins:
        window( model, face, a, b, wz0, wz1, "trim_white", reveal_paint="rw_dressed_red", depth=4, d=-6,
                panes="+" if detail == "near" else "|" if detail == "mid" else "" )
    for k in range( bays + 1 ):
        r = k * bay
        face.box( model, r - pier / 2, r + pier / 2, -6, 0, z0, top, "brick", skip=( "-d", "-z" ) )
        face.prism( model, "brick", [ ( r - pier / 2, top ), ( r + pier / 2, top ), ( r, top + 26 ) ], -6, 0 )
    if ground:
        for k in range( bays ):
            a, b = k * bay + pier / 2, ( k + 1 ) * bay - pier / 2
            reveal( model, face, "rw_dressed_red", a, b, 14, g - 54, 8, d=-6 )
            face.quad( model, "rw_window_dark", a, b, 14, g - 54, -14 )
            face.quad( model, "rw_steel_dark", a, b, g - 92, g - 88, -13.4 )
            if detail == "near" and chance( 0.4, key, "sign", k ):
                h = ( b - a - 12 ) / 4
                atlas_quad( model, face, "rw_shopsigns", pick( SIGNS, key, "s", k ), a + 6, b - 6, g - 34 - h / 2,
                            g - 34 + h / 2, -5.6 )
        face.box( model, 0, width, -6, 0, g - 14, g - 6, "rw_dressed_red", skip=( "-d", ) )
    face.box( model, 0, width, -6, -2, top - 6, top, "rw_dressed_red", skip=( "-d", "-z" ) )


def kontorhaus( model ):
    """ The office block across the Platz from the hotel: a 1920s Kontorhaus of clinker brick, six storeys and two
    set back over them, flat roofs behind parapets. """
    e0, e1, n0, n1 = KONTOR
    tiers = ( ( 0.0, 0.0, [ 210.0 + 150.0 * k for k in range( 5 ) ], 960.0 ),
              ( 70.0, 960.0, [ 960.0 ], 1110.0 ), ( 140.0, 1110.0, [ 1110.0 ], 1260.0 ) )
    for inset, z0, floors, z1 in tiers:
        a0, a1, b0, b1 = e0 + inset, e1 - inset, n0 + inset, n1 - inset
        top = z1 + 30
        faces = ( ( Face( ( a0, b0 ), ( 0, -1 ) ), a1 - a0, "s", "near" ), ( Face( ( a1, b0 ), ( 1, 0 ) ), b1 - b0, "e", "mid" ),
                  ( Face( ( a1, b1 ), ( 0, 1 ) ), a1 - a0, "n", "far" ), ( Face( ( a0, b1 ), ( -1, 0 ) ), b1 - b0, "w", "mid" ) )
        for face, width, name, detail in faces:
            kontor_face( model, face, width, z0, floors, top, inset == 0, ( "kontor", name, inset ), detail )
            face.quad( model, "brick", 0, width, z1, top, -12, out=-1.0 )
            face.level( model, "rw_concrete", 0, width, -12, -6, top )
        flat( model, "gravel", a0 + 12, a1 - 12, b0 + 12, b1 - 12, z1 )
        if inset == 140.0:
            for t, u in ( ( 0.3, 0.5 ), ( 0.7, 0.4 ) ):
                e, n = a0 + t * ( a1 - a0 ), b0 + u * ( b1 - b0 )
                model.box( ( e - 40, n - 30, z1 ), ( e + 40, n + 30, z1 + 70 ), { "default": "rw_steel_grey", "-z": None } )


def north_row( model, s ):
    """ The block across the cab road north of the cross street: tenements at e +-2200..2700, n 2400..3300, turned
    round both corners. """
    length = SIDE_N0 - ( CROSS_N1 + 60 )
    if s > 0:
        face = Face( ( EDGE, SIDE_N0 ), ( -1, 0 ) )
        row( model, face, length, "north_e", "mid", "corner", "corner", turrets=( False, True ), collide=False )
    else:
        face = Face( ( -EDGE, CROSS_N1 + 60 ), ( 1, 0 ) )
        row( model, face, length, "north_w", "mid", "corner", "corner", turrets=( True, False ), collide=False )


def north_city():
    """ Beyond the play area's north edge: the Bahnhofsplatz and the streets round it. Drawn only. """
    model = K.Model()
    north_ground( model )
    tramway( model )
    platz( model )
    hotel( model )
    kontorhaus( model )
    for s in ( 1, -1 ):
        north_row( model, s )
    return configure( model )


def models():
    return { "railhead_edge_east": edge_blocks( 1 ), "railhead_north": north_city(), "railhead_south": south_vista(),
             "railhead_skyline": skyline() }


# ---------------------------------------------------------------------------------------------------------------------
# Low-poly buildings, for the line south and the skyline: a box of walls and a roof, nothing more

def _frame( e0, e1, n0, n1, along ):
    """ A building's plan as ( length along its ridge, depth across it ) and a map from ( x along, y across, z ) to plan. """
    if along == "e":
        return e1 - e0, n1 - n0, lambda x, y, z: ( e0 + x, n0 + y, z ), ( 1.0, 0.0 ), ( 0.0, 1.0 )
    return n1 - n0, e1 - e0, lambda x, y, z: ( e1 - y, n0 + x, z ), ( 0.0, 1.0 ), ( -1.0, 0.0 )


def roof( model, e0, e1, n0, n1, eave, paint, kind="gable", along=None, pitch=40.0, end_paint=None, upper=None ):
    """ A roof over the box e0..e1, n0..n1 from eave up. kind: 'gable' (end walls in end_paint), 'hip', 'mansard' (72
    then 16 degrees, upper slopes in upper), 'pyramid', 'flat'. The ridge runs along `along` ('e' or 'n'), by default the
    long side. Returns the ridge's height. """
    if kind == "flat":
        flat( model, paint, e0, e1, n0, n1, eave )
        return eave
    if along is None:
        along = "e" if e1 - e0 >= n1 - n0 else "n"
    length, depth, P, X, Y = _frame( e0, e1, n0, n1, along )
    hd = depth / 2
    X3, Y3 = np.array( ( *X, 0.0 ) ), np.array( ( *Y, 0.0 ) )
    Z3 = np.array( ( 0.0, 0.0, 1.0 ) )
    if kind == "pyramid":
        hd = min( hd, length / 2 )
    if kind == "mansard":
        inset = min( hd, length / 2 ) * 0.3
        rise = inset * math.tan( math.radians( 72 ) )
        lo = [ P( 0, 0, eave ), P( length, 0, eave ), P( length, depth, eave ), P( 0, depth, eave ) ]
        hi = [ P( inset, inset, eave + rise ), P( length - inset, inset, eave + rise ), P( length - inset, depth - inset, eave + rise ),
               P( inset, depth - inset, eave + rise ) ]
        for k, out in enumerate( ( -Y3, X3, Y3, -X3 ) ):
            facing( model, paint, [ lo[k], lo[( k + 1 ) % 4], hi[( k + 1 ) % 4], hi[k] ], out * rise + Z3 * inset )
        return roof( model, *_plan_box( hi ), eave + rise, upper or paint, "hip", along, 16.0 )
    rise = hd * math.tan( math.radians( pitch ) )
    top = eave + rise
    if kind == "gable":
        a, b = 0.0, length
    else:                                                       # hip, pyramid
        a, b = min( hd, length / 2 ), max( length - hd, length / 2 )
    for y0, y1, out in ( ( 0.0, hd, -Y3 ), ( depth, hd, Y3 ) ):
        pts = [ P( 0, y0, eave ), P( length, y0, eave ), P( b, y1, top ), P( a, y1, top ) ]
        if b - a < 1e-6:
            pts = pts[:3]
        facing( model, paint, pts, out * rise + Z3 * hd )
    for x0, x1, out in ( ( 0.0, a, -X3 ), ( length, b, X3 ) ):
        tri = [ P( x0, 0, eave ), P( x0, depth, eave ), P( x1, hd, top ) ]
        if kind == "gable":
            facing( model, end_paint or paint, tri, out )
        else:
            facing( model, paint, tri, out * rise + Z3 * hd )
    return top


def _plan_box( points ):
    e = [ p[0] for p in points ]
    n = [ p[1] for p in points ]
    return min( e ), max( e ), min( n ), max( n )


def mass( model, e0, e1, n0, n1, base, eave, wall, roof_paint="roof_tiles", kind="gable", along=None, pitch=40.0,
          walls=None, upper=None ):
    """ A low-poly building: walls from base (sunk into the ground below it) to eave, under roof(). walls overrides a
    side's paint ( '+e', '-e', '+n', '-n'; None leaves it out). Returns the ridge's height. """
    sides = { "+e": wall, "-e": wall, "+n": wall, "-n": wall, "+z": None, "-z": None }
    sides.update( walls or {} )
    model.box( ( e0, n0, base ), ( e1, n1, eave ), sides )
    return roof( model, e0, e1, n0, n1, eave, roof_paint, kind, along, pitch, end_paint=wall, upper=upper )


def sawtooth( model, e0, e1, n0, n1, base, eave, wall, teeth, rise=110.0, glass="glass", sheet="corrugated" ):
    """ A factory hall's north-light roof: teeth running east-west, each a glazed upright face to the north and a sheet
    slope down to the south (the light without the sun). """
    model.box( ( e0, n0, base ), ( e1, n1, eave ), { "default": wall, "+z": None, "-z": None } )
    step = ( n1 - n0 ) / teeth
    for k in range( teeth ):
        a, b = n0 + k * step, n0 + ( k + 1 ) * step
        facing( model, sheet, [ ( e0, a, eave ), ( e1, a, eave ), ( e1, b, eave + rise ), ( e0, b, eave + rise ) ],
                ( 0, -rise, step ) )
        facing( model, glass, [ ( e0, b, eave ), ( e1, b, eave ), ( e1, b, eave + rise ), ( e0, b, eave + rise ) ], ( 0, 1, 0 ) )
        for e, out in ( ( e0, -1.0 ), ( e1, 1.0 ) ):
            facing( model, wall, [ ( e, a, eave ), ( e, b, eave ), ( e, b, eave + rise ) ], ( out, 0, 0 ) )


def chimney( model, e, n, base, height, r0=80.0, r1=46.0, paint="brick", sides=10 ):
    """ A tapered round brick factory stack with a corbelled cap. """
    lathe( model, ( e, n ), [ ( r0 * 1.15, base ), ( r0 * 1.15, base + 160 ), ( r0, base + 170 ), ( r1, base + height ),
                              ( r1 * 1.18, base + height + 12 ), ( r1 * 1.18, base + height + 40 ), ( r1 * 0.9, base + height + 40 ) ],
           paint, sides=sides, cap=False )
    model.polygon( "rw_black", [ ( e + r1 * 0.9 * math.cos( 2 * math.pi * k / sides ), n + r1 * 0.9 * math.sin( 2 * math.pi * k / sides ),
                                   base + height + 30 ) for k in range( sides ) ] )


def onion_tower( model, e, n, base, square, shaft, paint="render_cream", trim="rw_sandstone", dome="copper" ):
    """ A south German church tower: a square shaft with a clock stage and a copper onion dome, lantern and cross.
    Returns the cross's top. """
    h = square / 2
    model.box( ( e - h, n - h, base ), ( e + h, n + h, base + shaft ), { "default": paint, "-z": None } )
    model.box( ( e - h - 6, n - h - 6, base + shaft ), ( e + h + 6, n + h + 6, base + shaft + 18 ), trim )
    z = base + shaft + 18
    lathe( model, ( e, n ), [ ( h * 0.95, z ), ( h * 0.95, z + 40 ), ( h * 1.12, z + 120 ), ( h * 1.05, z + 190 ),
                              ( h * 0.55, z + 260 ), ( h * 0.22, z + 300 ), ( h * 0.22, z + 360 ), ( h * 0.45, z + 410 ),
                              ( h * 0.32, z + 455 ), ( h * 0.08, z + 480 ), ( 0.0, z + 490 ) ], dome, sides=12 )
    top = z + 490
    rod( model, ( e, n, top ), ( e, n, top + 70 ), 3.0, "iron_black" )
    rod( model, ( e - 16, n, top + 50 ), ( e + 16, n, top + 50 ), 3.0, "iron_black" )
    return top + 70


# ---------------------------------------------------------------------------------------------------------------------
# The land: level city, the line's cutting, the hills south and round the city

CUT_N0 = -4400.0            # the land beside the line starts rising here...
PORTAL_N = -8000.0          # ...to the tunnel portal
PORTAL_Z = 640.0            # the land over the portal
ROTUNDA = ( 0.0, -10400.0 )             # the Rotunde's centre: on the line's axis, over the tunnel
ROTUNDA_R = 2100.0                      # its drum's radius: 107 m across, as Vienna's Rotunde of 1873 (108 m)
ROTUNDA_BASE = PORTAL_Z + 60.0          # the park it stands in, level over the tunnel
WALL_MAX = 250.0            # the cutting's walls stand this high, with a 1:1.25 grass slope above them...
WALL_FULL_N = ( -7000.0, -7800.0 )      # ...until the portal's approach, walled to the top
BED = -37.0                 # the lead's track bed

# Plan e of the land's columns (mirrored for the west), out to the hills
E_COLS = ( 1300, 1500, 1750, 2000, 2200, 2450, 2700, 3000, 3300, 3700, 4100, 4500, 4900, 5400, 5900, 6300, 6800, 7400,
           8100, 8900, 9800, 10800, 12000, 13400, 15000, 16800, 18800, 21000, 23400, 26000, 29000, 32500, 36000, 40000 )


def corridor_half( n ):
    """ Half the width the lead keeps clear for the line at n. """
    if n >= CORRIDOR[0][0]:
        return CORRIDOR[0][1]
    for ( na, wa ), ( nb, wb ) in zip( CORRIDOR, CORRIDOR[1:] ):
        if nb <= n <= na:
            return wa + ( wb - wa ) * ( na - n ) / ( na - nb )
    return CORRIDOR[-1][1]


R0 = 24500.0                # the city's level ground reaches this far out (as ring_z measures it)


def ring_z( e, n ):
    """ The hills round the city: level to R0 out (a rounded square about n 600), rising to ~3400 (86 m) by 39500. """
    r = ( e ** 4 + ( n - 600.0 ) ** 4 ) ** 0.25
    t = smooth( ( r - R0 ) / 15000.0 )
    return 3400.0 * t * ( 1.0 + 0.25 * math.sin( e / 5300.0 + 0.7 ) * math.sin( n / 4700.0 - 0.3 ) )


def south_z( e, n ):
    """ The land south of the station: the city's level to n -4400, a slope up to the hill the line tunnels under at n
    -8000 (640, 16 m), the park on its top level round the Rotunde (ROTUNDA_BASE), and low farmland and woods beyond,
    rolling to ~1300 (33 m), so the cab roads look past the Rotunde into open sky. """
    if n >= CUT_N0:
        z = 0.0
    elif n >= PORTAL_N + 200:
        z = PORTAL_Z * smooth( ( CUT_N0 - n ) / ( CUT_N0 - PORTAL_N - 200 ) )
    else:
        z = PORTAL_Z + ( ROTUNDA_BASE - PORTAL_Z ) * smooth( ( PORTAL_N + 200 - n ) / 600.0 )
        d = math.hypot( e - ROTUNDA[0], n - ROTUNDA[1] )
        k = smooth( ( d - ROTUNDA_R - 900.0 ) / 2500.0 )
        z += k * ( 380.0 * smooth( ( -9000.0 - n ) / 9000.0 )
                   + 160.0 * math.sin( e / 4100.0 + 1.3 ) * math.sin( n / 3300.0 + 0.4 )
                   + 90.0 * math.sin( e / 2300.0 - n / 2900.0 + 2.0 ) )
    if n < CUT_N0 - 600:
        away = smooth( ( abs( e ) - 2500.0 ) / 3000.0 ) * smooth( ( CUT_N0 - 600 - n ) / 1500.0 )
        z += away * 90.0 * math.sin( e / 1900.0 + 0.4 ) * math.cos( n / 2300.0 )
    return z


def land_z( e, n ):
    return max( south_z( e, n ) if n < PLAY_N0 + 1 else 0.0, ring_z( e, n ) )


def wall_top( n, h ):
    """ How high the cutting's wall stands where the land is at h. """
    t = smooth( ( WALL_FULL_N[0] - n ) / ( WALL_FULL_N[0] - WALL_FULL_N[1] ) )
    return min( h, WALL_MAX ) * ( 1 - t ) + h * t


def zip_rows( model, row_a, row_b, paint_of ):
    """ The land between two rows of points ( e, n, z ), each in order of e, as triangles facing up: walked along
    together like a zip, so rows can have different points. """
    i, j = 0, 0
    while i < len( row_a ) - 1 or j < len( row_b ) - 1:
        if j >= len( row_b ) - 1 or ( i < len( row_a ) - 1 and row_a[i + 1][0] <= row_b[j + 1][0] ):
            tri = ( row_a[i], row_a[i + 1], row_b[j] )
            i += 1
        else:
            tri = ( row_a[i], row_b[j + 1], row_b[j] )
            j += 1
        c = np.mean( np.asarray( tri, float ), axis=0 )
        paint = paint_of( c[0], c[1], c[2] )
        if paint:
            facing( model, paint, tri, ( 0, 0, 1 ) )


def dedupe( row ):
    out = []
    for p in row:
        if not out or abs( p[0] - out[-1][0] ) > 0.5 or abs( p[2] - out[-1][2] ) > 0.5:
            out.append( p )
    return out


def flat_mesh( model, e0, e1, n_rows, e_cols, paint_of, z_of=land_z ):
    """ Land over e0..e1 (with the given columns between) at each of n_rows, from z_of. """
    cols = [ e0 ] + [ c for c in e_cols if e0 + 1 < c < e1 - 1 ] + [ e1 ]
    rows = [ [ ( e, n, z_of( e, n ) ) for e in cols ] for n in n_rows ]
    for a, b in zip( rows, rows[1:] ):
        zip_rows( model, a, b, paint_of )


# ---------------------------------------------------------------------------------------------------------------------
# South: the line out of the station, between its cutting walls, under the overbridge and into the hill

DEPOT_E = 1750.0                    # the depot's pit east of the line: its east wall...
DEPOT_N = ( -3460.0, -5460.0 )      # ...and its north and south ends
THROAT_E = 1090.0                   # its north wall starts this far out, the wall west of it splayed back to the cutting's
                                    # edge at the bridge: the lead off track C (railhead_map.depot_lead) runs in beside it
BRIDGE = ( -3300.0, -2900.0 )       # the overbridge's deck, 10.2 m wide: 1.6 m pavements by a 6.35 m carriageway
SOFFIT = 230.0                      # 6.8 m over the rails (5.9 m is the least over the wire's supports)
ROAD_TOP = 318.0                    # a 2.24 m prestressed box girder (span / 24) under its road
ABUT_E = 1300.0                     # the abutments' backs, where the ramps start
RAMP_E = 6100.0                     # where the ramps come down to the street (6.6 %, a city street's steepest)
STRIP_N = -2880.0                   # the lineside strip north of the ramp: the permanent-way yard, the coal yard, gardens
RAIL_HALF = 29.6                    # rail centres either side of a track's centre (1435 mm gauge)
CITY_E = 6500.0                     # the city's blocks beside the slope south of the ramp


def ramp_z( e ):
    a = abs( e )
    if a <= ABUT_E:
        return ROAD_TOP
    return max( 0.0, ROAD_TOP * ( RAMP_E - a ) / ( RAMP_E - ABUT_E ) )


def south_rows( depot ):
    """ The rows of the land beside the line, ( n, edge ): the cutting's edge, out round the depot's pit if depot. """
    ns = [ PLAY_N0, -2650.0, BRIDGE[1], -3100.0, BRIDGE[0] ]
    ns += [ float( n ) for n in np.arange( DEPOT_N[0], DEPOT_N[1] - 1, -200.0 ) ]
    ns += [ float( n ) for n in np.linspace( DEPOT_N[1], PORTAL_N, 14 )[1:] ]
    rows = []
    for n in ns:
        w = corridor_half( n )
        if depot and DEPOT_N[1] <= n <= DEPOT_N[0]:
            if n == DEPOT_N[0]:
                rows.append( ( n, max( w, THROAT_E ) ) )
            rows.append( ( n, DEPOT_E ) )
            if n == DEPOT_N[1]:
                rows.append( ( n, w ) )
        else:
            rows.append( ( n, w ) )
    return rows


def crest_of( n, edge, s=1.0 ):
    """ The cutting's wall top beside a row's edge, the grass slope's crest above it (e out from the line) and the land's
    height there: the slope is 1:1.25, about 39 degrees. """
    h = land_z( s * edge, n )
    top = wall_top( n, h )
    return top, edge + 1.25 * ( h - top ), h


def south_ground( e, n, z ):
    """ What covers the land at plan ( e, n ), south of the play area. """
    a = abs( e )
    if n < PORTAL_N - 1 and math.hypot( e - ROTUNDA[0], n - ROTUNDA[1] ) < ROTUNDA_R + 1600:
        return "lawn"                                                       # the Rotunde's park
    if n < PORTAL_N - 1 or a > 20000:
        if z > 900 or unit( "hill", int( e // 2600 ), int( n // 2100 ) ) < 0.45:
            return "hedge"                                                  # woods
        return pick( ( "lawn", "lawn", "soil", "lawn" ), "field", int( e // 3100 ), int( n // 2300 ) )
    if n < CUT_N0 + 150:
        top, crest, h = crest_of( n, corridor_half( n ), 1.0 if e > 0 else -1.0 )
        if a < crest + 40:
            return "lawn"                                                   # the cutting's grass slopes
    if n > STRIP_N:
        if e > 0:
            return "gravel" if a < 2720 else "rw_concrete" if a < 3680 else "rw_asphalt"
        return "rw_concrete_dark" if a < 2380 else "lawn" if a < 3680 else "rw_asphalt"
    if n > BRIDGE[0] - 1:
        return "rw_asphalt"                                                 # the ramp's street
    if n > CUT_N0:
        if e > 0:
            return "gravel" if a < 2000 else "rw_concrete" if a < 5300 else "rw_asphalt"
        return "lawn" if a < 4300 else "gravel" if a < 6000 else "rw_asphalt"
    if a >= CITY_E and n > -7900:
        return "rw_asphalt"
    if e > 0:
        return "lawn"                                                       # a park by the line, the town's gardens
    return "hedge" if unit( "wood", int( e // 900 ), int( n // 700 ) ) < 0.65 else "lawn"


def south_land( model, s, depot ):
    """ The land beside the line (east s 1, west -1) from n -2400 to the portal, the cutting's walls and their coping.
    Returns the last row, ( e, n, z ) in order of e, for far_land to meet. """
    rows = []
    walls = []
    for n, edge in south_rows( depot ):
        top, crest, h = crest_of( n, edge, s )
        row = [ ( edge, n, top ), ( crest, n, h ) ] + [ ( c, n, land_z( s * c, n ) ) for c in E_COLS if c > crest + 40 ]
        row = [ ( s * e, n, z ) for e, n, z in dedupe( row ) ]
        rows.append( sorted( row ) )
        walls.append( ( edge, n, top ) )
    for a, b in zip( rows, rows[1:] ):
        if abs( a[0][1] - b[0][1] ) > 0.5:                     # not across the depot pit's ends, which are walls
            zip_rows( model, a, b, south_ground )
    # The cutting's walls: concrete like the station's by the yards and round the depot, dressed stone south of the bridge
    pit = depot and ( lambda n: DEPOT_N[1] <= n <= DEPOT_N[0] ) or ( lambda n: False )
    for ( ea, na, ta ), ( eb, nb, tb ) in zip( walls, walls[1:] ):
        if BRIDGE[0] - 1 <= nb and na <= BRIDGE[1] + 1:
            continue                                            # the abutment stands there
        d = ( eb - ea, nb - na )
        towards = ( s * d[1], -d[0], 0.0 )
        stone = na < BRIDGE[0] and not ( pit( na ) and pit( nb ) )
        paint = "ashlar_grey" if stone else "rw_concrete_dark"
        band = 12.0 if stone and min( ta, tb ) > 40 else 0.0
        facing( model, paint, [ ( s * ea, na, BED ), ( s * eb, nb, BED ), ( s * eb, nb, tb - band ), ( s * ea, na, ta - band ) ],
                towards )
        if band:
            facing( model, "rw_concrete", [ ( s * ea, na, ta - band ), ( s * eb, nb, tb - band ), ( s * eb, nb, tb ),
                                            ( s * ea, na, ta ) ], towards )
        elif max( ta, tb ) < 1:
            # The coping along the level ground's edge, as along the station's yard
            along_n = abs( d[1] ) > 1e-6
            ka, kb = ( ea + 14, eb + 14 ) if along_n else ( ea, eb )
            na2, nb2 = ( na, nb ) if along_n else ( na + 14 * math.copysign( 1, d[0] ), nb + 14 * math.copysign( 1, d[0] ) )
            facing( model, "rw_coping", [ ( s * ea, na, 0.25 ), ( s * eb, nb, 0.25 ), ( s * kb, nb2, 0.25 ), ( s * ka, na2, 0.25 ) ],
                    ( 0, 0, 1 ) )
    if depot:
        # The pit's floor, the track bed's level, between the corridor and the pit's east wall, and in the splay north of it
        ns = [ n for n, _ in south_rows( False ) if DEPOT_N[1] <= n <= DEPOT_N[0] ]
        for na, nb in zip( ns, ns[1:] ):
            wa, wb = corridor_half( na ), corridor_half( nb )
            facing( model, "rw_ballast_old", [ ( s * wa, na, BED ), ( s * DEPOT_E, na, BED ), ( s * DEPOT_E, nb, BED ),
                                               ( s * wb, nb, BED ) ], ( 0, 0, 1 ) )
        n0, n1 = BRIDGE[0], DEPOT_N[0]
        facing( model, "rw_ballast_old", [ ( s * corridor_half( n0 ), n0, BED ), ( s * corridor_half( n1 ), n1, BED ),
                                           ( s * THROAT_E, n1, BED ) ], ( 0, 0, 1 ) )
    return rows[-1]


def far_land( model, east_last, west_last ):
    """ The hills from the portal south, across the line, sewn to both sides' last rows. """
    first = dedupe( list( west_last ) + list( east_last ) )
    cols = sorted( set( [ 0.0, 350.0, -350.0, 700.0, -700.0 ] + [ float( c ) for c in E_COLS ] + [ -float( c ) for c in E_COLS ] ) )
    ns = ( -8250, -8550, -8900, -9300, -9800, -10400, -11100, -11900, -12800, -13900, -15200, -16700, -18500, -20500,
           -23000, -26000, -29500, -33500, -37000, -40000 )
    rows = [ first ] + [ [ ( e, float( n ), land_z( e, n ) ) for e in cols ] for n in ns ]
    for a, b in zip( rows, rows[1:] ):
        zip_rows( model, a, b, south_ground )


def fence( model, points, height=48.0, step=120.0, paint="rw_steel_grey" ):
    """ A lineside fence along plan points ( e, n, z ): posts, a top rail and a middle wire. """
    for a, b in zip( points, points[1:] ):
        a, b = np.asarray( a, float ), np.asarray( b, float )
        count = max( 1, int( np.linalg.norm( ( b - a )[:2] ) / step ) )
        for k in range( count ):
            p = a + ( b - a ) * k / count
            rod( model, p, p + ( 0, 0, height ), 2.4, paint )
        for z in ( height - 3, height * 0.5 ):
            rod( model, a + ( 0, 0, z ), b + ( 0, 0, z ), 1.2, paint )
    p = np.asarray( points[-1], float )
    rod( model, p, p + ( 0, 0, height ), 2.4, paint )


def track( model, points, z, bed=True ):
    """ A plain track along plan points: ballast shoulders, and two rails on top (the sleepers are the ballast's
    business at this range). """
    for a, b in zip( points, points[1:] ):
        a, b = np.asarray( a, float ), np.asarray( b, float )
        x = ( b - a ) / np.linalg.norm( b - a )
        y = np.array( ( -x[1], x[0] ) )
        if bed:
            facing( model, "rw_ballast_old", [ ( *( a - y * 60 ), z ), ( *( b - y * 60 ), z ), ( *( b + y * 60 ), z ),
                                               ( *( a + y * 60 ), z ) ], ( 0, 0, 1 ) )
        for side in ( -RAIL_HALF, RAIL_HALF ):
            p0, p1 = a + y * side, b + y * side
            model.beam( ( *p0, z + 4.5 ), ( *p1, z + 4.5 ), ( 2.6, 6.0 ), { "default": "rw_rail", "+z": "rw_rail_head", "-z": None } )


def embedded_siding( model, e, n0, n1 ):
    """ A siding set in concrete, its rail heads flush, as through the goods yard's gate. """
    flat( model, "rw_concrete", e - 60, e + 60, n0, n1, 0.2 )
    for side in ( -RAIL_HALF, RAIL_HALF ):
        flat( model, "rw_rail_head", e + side - 1.3, e + side + 1.3, n0, n1, 0.35 )
        flat( model, "rw_black", e + side + ( 1.3 if side < 0 else -3.3 ), e + side + ( 3.3 if side < 0 else -1.3 ), n0, n1, 0.3 )


def buffer_stop( model, e, n, out ):
    """ A welded rail-built buffer stop facing out (+1 north, -1 south) at plan n, its beam 1.06 m up. """
    back = n - out * 60
    for side in ( -RAIL_HALF, RAIL_HALF ):
        model.beam( ( e + side, back, 0.5 ), ( e + side, n, 40 ), ( 3.0, 5.0 ), "rw_steel_dark" )
    lo_n, hi_n = sorted( ( n, n - out * 10 ) )
    model.box( ( e - 60, lo_n, 30 ), ( e + 60, hi_n, 50 ), { "default": "rw_steel_dark", "+n" if out > 0 else "-n": "rw_red_paint" } )
    for side in ( -RAIL_HALF * 1.2, RAIL_HALF * 1.2 ):
        a, b = sorted( ( n, n + out * 14 ) )
        model.box( ( e + side - 7, a, 34 ), ( e + side + 7, b, 46 ), { "default": "rw_steel_dark", "+n" if out > 0 else "-n": "rw_black" } )


# ---------------------------------------------------------------------------------------------------------------------
# The overbridge and its ramps

def arch_outline( c, half, spring, steps=8 ):
    """ A round-headed opening ( e, z ) from z 0, as a convex polygon. """
    return [ ( c - half, 0.0 ), ( c + half, 0.0 ) ] + [
        ( c + half * math.cos( math.pi * k / steps ), spring + half * math.sin( math.pi * k / steps ) ) for k in range( steps + 1 ) ]


def overbridge( model ):
    """ The road over the line at n -3100: a concrete box girder from abutment to abutment, its ramps walled in brick
    with workshop arches under them, pavements, parapets and lamps. """
    n0, n1 = BRIDGE
    w0, w1 = corridor_half( n1 ), corridor_half( n0 )        # the corridor's half-width at the deck's north and south faces
    model.prism( [ ( -w1, n0 ), ( w1, n0 ), ( w0, n1 ), ( -w0, n1 ) ], SOFFIT, ROAD_TOP,
                 { "side": "rw_concrete", "top": None, "bottom": "rw_concrete" } )
    for s in ( 1.0, -1.0 ):
        outline = [ ( w1, n0 ), ( ABUT_E, n0 ), ( ABUT_E, n1 ), ( w0, n1 ) ]
        if s < 0:
            outline = [ ( -e, n ) for e, n in reversed( outline ) ]
        model.prism( outline, BED, ROAD_TOP, { "side": "rw_concrete", "top": None, "bottom": None } )
        lo_e, hi_e = sorted( ( 0.0, s * ABUT_E ) )
        for n, out in ( ( n0, -1.0 ), ( n1, 1.0 ) ):
            inner = n - out * 12
            a, b = sorted( ( n, inner ) )
            # A drip course along the girder's and abutments' faces
            c, d = sorted( ( n, n + out * 2 ) )
            model.box( ( lo_e, c, ROAD_TOP - 14 ), ( hi_e, d, ROAD_TOP ), "rw_concrete", skip=( "-n" if out > 0 else "+n", ) )
            # The bridge's concrete parapet, 1 m over the pavement, with a steel handrail
            model.box( ( lo_e, a, ROAD_TOP ), ( hi_e, b, ROAD_TOP + 40 ), "rw_concrete", skip=( "-z", "+e", "-e" ) )
            rod( model, ( lo_e, n - out * 6, ROAD_TOP + 44 ), ( hi_e, n - out * 6, ROAD_TOP + 44 ), 2.2, "rw_steel_grey" )
            for e in np.arange( lo_e + 60, hi_e, 240.0 ):
                rod( model, ( e, n - out * 6, ROAD_TOP + 40 ), ( e, n - out * 6, ROAD_TOP + 44 ), 2.0, "rw_steel_grey" )
            # The ramp: brick walls with dressed coping, falling to the street at RAMP_E
            facing( model, "brick", [ ( s * ABUT_E, n, -20 ), ( s * RAMP_E, n, -20 ), ( s * RAMP_E, n, 40 ),
                                      ( s * ABUT_E, n, ROAD_TOP + 40 ) ], ( 0, out, 0 ) )
            facing( model, "brick", [ ( s * ABUT_E, inner, ROAD_TOP + 6 ), ( s * RAMP_E, inner, 6 ), ( s * RAMP_E, inner, 40 ),
                                      ( s * ABUT_E, inner, ROAD_TOP + 40 ) ], ( 0, -out, 0 ) )
            facing( model, "rw_dressed", [ ( s * ABUT_E, n, ROAD_TOP + 40 ), ( s * RAMP_E, n, 40 ), ( s * RAMP_E, inner, 40 ),
                                           ( s * ABUT_E, inner, ROAD_TOP + 40 ) ], ( 0, 0, 1 ) )
            facing( model, "brick", [ ( s * RAMP_E, n, 0 ), ( s * RAMP_E, inner, 0 ), ( s * RAMP_E, inner, 40 ), ( s * RAMP_E, n, 40 ) ],
                    ( s, 0, 0 ) )
            # Three workshop arches each side by the bridge, glazed in green-painted frames
            for c in ( 1520.0, 1780.0, 2040.0 ):
                ring = arch_outline( s * c, 112.0, 118.0 )
                hole = arch_outline( s * c, 98.0, 118.0 )
                facing( model, "rw_dressed", [ ( e, n + out * 0.3, z ) for e, z in ring ], ( 0, out, 0 ) )
                facing( model, "rw_window_dark", [ ( e, n + out * 0.6, z ) for e, z in hole ], ( 0, out, 0 ) )
                c0, c1 = sorted( ( n + out * 0.6, n + out * 1.4 ) )
                model.box( ( s * c - 98, c0, 96 ), ( s * c + 98, c1, 102 ), "trim_green" )
                model.box( ( s * c - 3, c0, 0 ), ( s * c + 3, c1, 96 ), "trim_green" )
    # The road: pavements 6 in over the carriageway, kerbs between
    es = [ -RAMP_E, -ABUT_E, ABUT_E, RAMP_E ]
    for ea, eb in zip( es, es[1:] ):
        za, zb = ramp_z( ea ), ramp_z( eb )
        for p0, p1, dz, paint in ( ( n0 + 12, n0 + 75, 6.0, "rw_paving" ), ( n0 + 75, n1 - 75, 0.0, "rw_asphalt" ),
                                   ( n1 - 75, n1 - 12, 6.0, "rw_paving" ) ):
            facing( model, paint, [ ( ea, p0, za + dz ), ( eb, p0, zb + dz ), ( eb, p1, zb + dz ), ( ea, p1, za + dz ) ], ( 0, 0, 1 ) )
        for p, out in ( ( n0 + 75, 1.0 ), ( n1 - 75, -1.0 ) ):
            facing( model, "rw_kerb", [ ( ea, p, za ), ( eb, p, zb ), ( eb, p, zb + 6 ), ( ea, p, za + 6 ) ], ( 0, out, 0 ) )
        # The centre line, dashed, following the road up and down
        e = ea
        while e + 60 < eb:
            e1 = min( e + 120, eb )
            facing( model, "rw_line_white", [ ( e, -3102.5, ramp_z( e ) + 0.1 ), ( e1, -3102.5, ramp_z( e1 ) + 0.1 ),
                                              ( e1, -3097.5, ramp_z( e1 ) + 0.1 ), ( e, -3097.5, ramp_z( e ) + 0.1 ) ], ( 0, 0, 1 ) )
            e += 360
    for s in ( 1.0, -1.0 ):
        for p0, p1 in ( ( n0 + 12, n0 + 75 ), ( n1 - 75, n1 - 12 ) ):
            facing( model, "rw_kerb", [ ( s * RAMP_E, p0, 0 ), ( s * RAMP_E, p1, 0 ), ( s * RAMP_E, p1, 6 ), ( s * RAMP_E, p0, 6 ) ],
                    ( s, 0, 0 ) )
    # Street lamps on the pavements, staggered
    for k, e in enumerate( ( -5200, -3800, -2400, -900, 400, 1700, 3100, 4500 ) ):
        n, out = ( n1 - 22, ( 0, -1 ) ) if k % 2 == 0 else ( n0 + 22, ( 0, 1 ) )
        street_lamp( model, e, n, out, ramp_z( e ) + 6 )


# ---------------------------------------------------------------------------------------------------------------------
# Beside the line, north of the ramp: the permanent-way yard (east) and a coal merchant's yard and gardens (west)

def stack( model, e0, e1, n0, n1, z0, layers, height, gap, paint ):
    """ Stacked lengths (sleepers, rails) along e, a layer at a time. """
    for k in range( layers ):
        z = z0 + k * ( height + gap )
        model.box( ( e0, n0, z ), ( e1, n1, z + height ), { "default": paint, "-z": None } )


def lineside_east( model ):
    # The siding runs on through the yard's gate to a buffer stop
    embedded_siding( model, SIDING_E_SOUTH, -2840.0, PLAY_N0 - 10 )
    buffer_stop( model, SIDING_E_SOUTH, -2780.0, 1.0 )
    # The Bahnmeisterei: the permanent-way gang's brick workshop, roller doors onto the siding's side
    mass( model, 1560, 1960, -2800, -2480, -10, 230, "brick", "roof_tiles", "gable", along="n", pitch=35.0 )
    for n_a, n_b in ( ( -2560.0, -2680.0 ), ( -2720.0, -2780.0 ) ):
        facing( model, "roller_grey", [ ( 1559.5, n_a, 0 ), ( 1559.5, n_b, 0 ), ( 1559.5, n_b, 170 ), ( 1559.5, n_a, 170 ) ], ( -1, 0, 0 ) )
    for e in ( 1620.0, 1760.0, 1900.0 ):
        for n, out in ( ( -2479.5, 1.0 ), ( -2800.5, -1.0 ) ):
            facing( model, "rw_window_dark", [ ( e - 30, n, 90 ), ( e + 30, n, 90 ), ( e + 30, n, 170 ), ( e - 30, n, 170 ) ], ( 0, out, 0 ) )
    model.box( ( 1960, -2560, -10 ), ( 2140, -2480, 110 ), { "default": "rw_steel_grey", "-z": None } )      # the site cabin
    facing( model, "rw_window_dark", [ ( 2000, -2479.5, 50 ), ( 2100, -2479.5, 50 ), ( 2100, -2479.5, 90 ), ( 2000, -2479.5, 90 ) ], ( 0, 1, 0 ) )
    # Sleepers, rails and a ballast heap
    for k, n in enumerate( ( -2470.0, -2560.0, -2650.0 ) ):
        stack( model, 1410, 1512, n - 50, n, 0.0, 4 + k % 2, 7.0, 3.0, "rw_sleeper" )
    stack( model, 1420, 1520, -2830, -2700, 0.0, 3, 6.0, 4.0, "rw_rail" )
    lathe( model, ( 2380, -2700 ), [ ( 170, 0 ), ( 40, 80 ), ( 0, 84 ) ], "rw_ballast", sides=9 )
    lathe( model, ( 2520, -2560 ), [ ( 110, 0 ), ( 26, 52 ), ( 0, 55 ) ], "rw_ballast_rusty", sides=8 )
    # The fence along the cutting's top
    fence( model, [ ( corridor_half( n ) + 30, n, 0 ) for n in ( PLAY_N0 - 4, BRIDGE[1] + 10 ) ] )
    # A factory beside the yard: north-light sheds and a brick office
    sawtooth( model, 2760, 3640, -2860, -2440, -10, 240, "brick", 3, rise=75.0 )
    mass( model, 2760, 3160, -2520, -2410, -10, 300, "brick", "slate", "hip", pitch=35.0 )
    for e in np.arange( 2800, 3600, 120.0 ):
        facing( model, "rw_window_dark", [ ( e, -2860.5, 100 ), ( e + 70, -2860.5, 100 ), ( e + 70, -2860.5, 200 ), ( e, -2860.5, 200 ) ],
                ( 0, -1, 0 ) )


def lineside_west( model ):
    # The siding runs on into the coal merchant's yard, beside his bunkers
    embedded_siding( model, -SIDING_E_SOUTH, -2840.0, PLAY_N0 - 10 )
    buffer_stop( model, -SIDING_E_SOUTH, -2800.0, 1.0 )
    e0, e1 = -1860.0, -1400.0
    walls = ( -2440.0, -2573.0, -2707.0, -2840.0 )
    model.box( ( e0, walls[-1], -6 ), ( e0 + 16, walls[0], 100 ), { "default": "rw_concrete", "-z": None } )
    for n in walls:
        model.box( ( e0, n - 8, -6 ), ( e1, n + 8, 100 ), { "default": "rw_concrete", "-z": None } )
    for k, ( na, nb ) in enumerate( zip( walls, walls[1:] ) ):
        roof( model, e0 + 16, e1 - 30, nb + 8, na - 8, -6, "rw_black", "hip", along="e", pitch=34.0 + 4 * k )
    # The office and its weighbridge
    mass( model, -2340, -2080, -2610, -2440, -10, 200, "brick", "roof_tiles", "hip", pitch=32.0 )
    for e in ( -2300.0, -2180.0 ):
        facing( model, "rw_window_dark", [ ( e, -2439.5, 80 ), ( e + 60, -2439.5, 80 ), ( e + 60, -2439.5, 160 ), ( e, -2439.5, 160 ) ],
                ( 0, 1, 0 ) )
    flat( model, "rw_steel_dark", -2300, -2000, -2800, -2680, 0.3 )
    fence( model, [ ( -corridor_half( n ) - 30, n, 0 ) for n in ( PLAY_N0 - 4, BRIDGE[1] + 10 ) ] )
    # Two allotment gardens
    for k in range( 2 ):
        allotment( model, -2450.0 - 620 * k, -3050.0 - 620 * k, -2860.0, -2440.0, ( "strip", k ) )


SIDING_E_SOUTH = 1300.0         # railhead_station.SIDING_E


def allotment( model, e0, e1, n0, n1, key ):
    """ A Schrebergarten: a clipped hedge round three sides, a summerhouse, vegetable beds, a fruit tree or two. """
    lo_e, hi_e = sorted( ( e0, e1 ) )
    model.box( ( lo_e, n0, 0 ), ( hi_e, n0 + 16, 44 ), { "default": "hedge", "-z": None } )
    model.box( ( lo_e, n1 - 16, 0 ), ( hi_e, n1, 44 ), { "default": "hedge", "-z": None } )
    far = lo_e if e0 > e1 else hi_e - 16
    model.box( ( far, n0 + 16, 0 ), ( far + 16, n1 - 16, 44 ), { "default": "hedge", "-z": None } )
    # The summerhouse in a back corner
    back = chance( 0.5, *key, "corner" )
    sn = ( n0 + 40, n0 + 150 ) if back else ( n1 - 150, n1 - 40 )
    se = ( far + 30, far + 190 ) if e0 > e1 else ( far - 174, far - 14 )
    paint = pick( ( "planks", "planks_dark", "trim_green", "trim_brown" ), *key, "house" )
    mass( model, se[0], se[1], sn[0], sn[1], -4, 86, paint, pick( ( "roof_tiles", "corrugated", "slate" ), *key, "roof" ),
          "gable", along="e", pitch=24.0 )
    # Beds of vegetables, dug soil between grass paths
    beds = int( between( 3, 5.99, *key, "beds" ) )
    width = ( hi_e - lo_e - 260 ) / beds
    mid0, mid1 = ( n0 + 180, n1 - 40 ) if back else ( n0 + 40, n1 - 180 )
    for b in range( beds ):
        a = lo_e + 130 + b * width
        flat( model, "soil", a + 12, a + width - 12, mid0, mid1, 0.4 )
    # A fruit tree and a currant bush or two
    tree( model, OAK, between( lo_e + 120, hi_e - 120, *key, "tree" ), ( n0 + n1 ) / 2 + between( -60, 60, *key, "tn" ), 0.0,
          ( *key, "tree" ), 0.42 )
    for b in range( int( between( 1, 2.99, *key, "bushes" ) ) ):
        tree( model, BUSH, between( lo_e + 60, hi_e - 60, *key, "bush", b ), n1 - 60 if back else n0 + 60, 0.0, ( *key, "bush", b ), 0.9 )


def allotments_south( model ):
    """ The bigger colony west of the line, south of the ramp: two rows of five gardens. """
    for row, ( n0, n1 ) in enumerate( ( ( -3780.0, -3380.0 ), ( -4240.0, -3840.0 ) ) ):
        for k in range( 5 ):
            e0 = -1150.0 - 620 * k
            allotment( model, e0, e0 - 600, n0, n1, ( "colony", row, k ) )
    # The colony's clubhouse
    mass( model, -4300, -3960, -4330, -4250, -6, 140, "planks_dark", "roof_tiles", "gable", along="e", pitch=30.0 )
    fence( model, [ ( -corridor_half( n ) - 30, n, 0 ) for n in ( BRIDGE[0] - 10, CUT_N0 + 30 ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# City blocks, for the line south and the skyline

GRID_E = tuple( 3900.0 + 2400.0 * k for k in range( 10 ) )     # the north-south streets' centres, both sides of the line
STREET_HALF = 200.0                                             # a 6.1 m carriageway and 2 m pavements


def grid_blocks( a0, a1 ):
    """ The blocks' spans (|e|) between the north-south streets, clipped to a0..a1. """
    out = []
    for c0, c1 in zip( GRID_E, GRID_E[1:] ):
        lo, hi = max( c0 + STREET_HALF, a0 ), min( c1 - STREET_HALF, a1 )
        if hi - lo > 300:
            out.append( ( lo, hi ) )
    return out


def ring_roof( model, e0, e1, n0, n1, eave, paint, inset, rise, top ):
    """ A block's mansard: a steep ring of slope round a flat top (the courtyard's roofs, seen from afar). """
    lo = [ ( e0, n0, eave ), ( e1, n0, eave ), ( e1, n1, eave ), ( e0, n1, eave ) ]
    hi = [ ( e0 + inset, n0 + inset, eave + rise ), ( e1 - inset, n0 + inset, eave + rise ), ( e1 - inset, n1 - inset, eave + rise ),
           ( e0 + inset, n1 - inset, eave + rise ) ]
    for k, out in enumerate( ( ( 0, -1 ), ( 1, 0 ), ( 0, 1 ), ( -1, 0 ) ) ):
        facing( model, paint, [ lo[k], lo[( k + 1 ) % 4], hi[( k + 1 ) % 4], hi[k] ], ( out[0] * rise, out[1] * rise, inset ) )
    if top:
        model.polygon( top, hi )


def ground_range( base_of, e0, e1, n0, n1 ):
    zs = [ base_of( e, n ) for e in ( e0, ( e0 + e1 ) / 2, e1 ) for n in ( n0, ( n0 + n1 ) / 2, n1 ) ]
    return min( zs ), max( zs )


RENDERS = ( "render_cream", "render_ochre", "render_pale", "render_rose", "render_sage", "render_cream", "render_pale" )


def city_house( model, e0, e1, n0, n1, along, key, walls, base_of, storeys=None, corner=False ):
    lo, hi = ground_range( base_of, e0, e1, n0, n1 )
    storeys = storeys or pick( ( 4, 5, 5, 5, 6 ), *key, "storeys" )
    paint = pick( FACADES if walls == "facade" else RENDERS, *key, "wall" )
    eave = hi + storeys * STOREY + 30 if walls != "facade" else ( math.ceil( hi / STOREY ) + storeys ) * STOREY + 24
    kind = "hip" if corner else pick( ( "mansard", "gable", "gable", "mansard" ), *key, "roof" )
    roof_paint = pick( ( "slate", "roof_tiles", "slate" ), *key, "roof paint" ) if kind != "mansard" else "slate"
    mass( model, e0, e1, n0, n1, lo - 40, eave, paint, roof_paint, kind, along, pitch=40.0 if kind != "hip" else 35.0,
          upper="roof_tiles" if chance( 0.3, *key, "upper" ) else "slate" )
    return eave


def city_block( model, e0, e1, n0, n1, key, detail="near", walls="facade", base_of=lambda e, n: 0.0, depth=480.0 ):
    """ A perimeter block of five-storey houses round a courtyard. detail 'near': each house its own height and roof,
    the corners square houses under hipped roofs; 'far': one range of houses a side; 'slab': the whole block as one mass
    under a mansard ring. """
    if detail == "slab":
        lo, hi = ground_range( base_of, e0, e1, n0, n1 )
        storeys = pick( ( 4, 5, 5, 6 ), *key, "storeys" )
        eave = hi + storeys * STOREY + 30
        model.box( ( e0, n0, lo - 40 ), ( e1, n1, eave ), { "default": pick( FACADES if walls == "facade" else RENDERS, *key ),
                                                            "+z": None, "-z": None } )
        ring_roof( model, e0, e1, n0, n1, eave, "slate", 110.0, 300.0, "rw_concrete_dark" )
        return
    d = min( depth, ( e1 - e0 ) / 3, ( n1 - n0 ) / 3 )
    if detail == "far":
        for k, ( a0, a1, b0, b1, along ) in enumerate( ( ( e0, e1, n0, n0 + d, "e" ), ( e0, e1, n1 - d, n1, "e" ),
                                                         ( e0, e0 + d, n0 + d, n1 - d, "n" ), ( e1 - d, e1, n0 + d, n1 - d, "n" ) ) ):
            city_house( model, a0, a1, b0, b1, along, ( *key, k ), walls, base_of )
        return
    corners = ( ( e0, n0 ), ( e1 - d, n0 ), ( e1 - d, n1 - d ), ( e0, n1 - d ) )
    for k, ( a, b ) in enumerate( corners ):
        city_house( model, a, a + d, b, b + d, "e", ( *key, "corner", k ), walls, base_of, corner=True )
    sides = ( ( e0 + d, e1 - d, n0, n0 + d, "e" ), ( e0 + d, e1 - d, n1 - d, n1, "e" ),
              ( e0, e0 + d, n0 + d, n1 - d, "n" ), ( e1 - d, e1, n0 + d, n1 - d, "n" ) )
    for k, ( a0, a1, b0, b1, along ) in enumerate( sides ):
        length = ( a1 - a0 ) if along == "e" else ( b1 - b0 )
        x = 0.0
        for j, w in enumerate( split( length, 380.0, 720.0, *key, "side", k ) ):
            if along == "e":
                city_house( model, a0 + x, a0 + x + w, b0, b1, "e", ( *key, k, j ), walls, base_of )
            else:
                city_house( model, a0, a1, b0 + x, b0 + x + w, "n", ( *key, k, j ), walls, base_of )
            x += w


# ---------------------------------------------------------------------------------------------------------------------
# South of the ramp: the depot, the works, the gasholder; the old village on the hill, the portal, the city's blocks

def depot( model ):
    """ The railcar shed in its pit east of the line: two roads under a slate roof with a glazed lantern. """
    e0, e1, n0, n1 = 1080.0, 1520.0, -5460.0, -4300.0
    eave = BED + 300.0
    mass( model, e0, e1, n0, n1, BED - 4, eave, "brick", "slate", "gable", along="n", pitch=22.0 )
    ridge = eave + ( e1 - e0 ) / 2 * math.tan( math.radians( 22 ) )
    model.box( ( 1250, n0 + 60, ridge - 30 ), ( 1350, n1 - 60, ridge + 26 ), { "default": "glass", "+n": "brick", "-n": "brick",
                                                                              "+z": None, "-z": None } )
    roof( model, 1250, 1350, n0 + 60, n1 - 60, ridge + 26, "slate", "gable", along="n", pitch=22.0, end_paint="brick" )
    # The doors at its north end, open, and tall windows down its sides
    for c in ( 1180.0, 1420.0 ):
        facing( model, "rw_window_dark", [ ( c - 80, n1 + 0.5, BED ), ( c + 80, n1 + 0.5, BED ), ( c + 80, n1 + 0.5, BED + 210 ),
                                           ( c - 80, n1 + 0.5, BED + 210 ) ], ( 0, 1, 0 ) )
        model.box( ( c - 88, n1, BED + 210 ), ( c + 88, n1 + 3, BED + 222 ), "rw_dressed" )
    for n in np.arange( n0 + 80, n1 - 40, 130.0 ):
        for e, out in ( ( e0 - 0.5, -1.0 ), ( e1 + 0.5, 1.0 ) ):
            facing( model, "rw_window_dark", [ ( e, n, BED + 60 ), ( e, n + 70, BED + 60 ), ( e, n + 70, BED + 220 ), ( e, n, BED + 220 ) ],
                    ( out, 0, 0 ) )
    # Its roads, out to the line (the corridor's edge: the lead's tracks are beyond)
    track( model, [ ( 1180.0, n1 - 20 ), ( 1180.0, -3900.0 ), ( 1050.0, -3560.0 ) ], BED + 0.4 )
    track( model, [ ( 1420.0, n1 - 20 ), ( 1420.0, -4020.0 ), ( 1205.0, -3820.0 ) ], BED + 0.45 )
    # A fuel tank and the staff's hut
    model.cylinder( ( 1640, -4700 ), 46.0, BED, BED + 150, { "side": "rw_steel_grey", "top": "rw_steel_grey", "bottom": None }, sides=10 )
    mass( model, 1560, 1720, -4280, -4120, BED - 4, BED + 130, "brick", "roof_tiles", "gable", along="n", pitch=30.0 )


def works( model ):
    """ A machine works beside the line: north-light halls, a boiler house and its chimney, the office on the street. """
    sawtooth( model, 2100, 3480, -4300, -3600, -10, 260, "brick", 5, rise=80.0 )
    sawtooth( model, 3700, 5100, -4360, -3760, -10, 280, "brick", 4, rise=85.0 )
    mass( model, 3700, 5100, -3580, -3400, -10, 3 * STOREY + 40, "brick", "slate", "hip", pitch=38.0 )
    for e in np.arange( 3740, 5060, 110.0 ):
        for z in ( 70.0, 70.0 + STOREY, 70.0 + 2 * STOREY ):
            facing( model, "rw_window_dark", [ ( e, -3399.5, z ), ( e + 50, -3399.5, z ), ( e + 50, -3399.5, z + 85 ), ( e, -3399.5, z + 85 ) ],
                    ( 0, 1, 0 ) )
    mass( model, 3520, 3690, -4420, -4240, -10, 330, "brick", "roof_tiles", "gable", along="n", pitch=35.0 )
    chimney( model, 3605, -4120, -10, 1500 )
    for e in np.arange( 2140, 3460, 120.0 ):
        facing( model, "rw_window_dark", [ ( e, -4300.5, 90 ), ( e + 70, -4300.5, 90 ), ( e + 70, -4300.5, 220 ), ( e, -4300.5, 220 ) ],
                ( 0, -1, 0 ) )


GASHOLDER = ( -5200.0, -4100.0, 690.0 )         # centre and radius


def gasholder( model ):
    """ A column-guided gasholder (35 m across, its bell half up) and its valve house. """
    c, r = GASHOLDER[:2], GASHOLDER[2]
    model.cylinder( c, r, -10, 980, { "side": "rw_steel", "top": None, "bottom": None }, sides=24 )
    lathe( model, c, [ ( r, 980 ), ( r * 0.8, 1040 ), ( r * 0.45, 1080 ), ( 0, 1092 ) ], "rw_steel", sides=24 )
    for k in range( 12 ):
        a = 2 * math.pi * k / 12
        p = np.array( ( c[0] + ( r + 30 ) * math.cos( a ), c[1] + ( r + 30 ) * math.sin( a ) ) )
        model.box( ( p[0] - 9, p[1] - 9, -10 ), ( p[0] + 9, p[1] + 9, 1500 ), { "default": "rw_steel", "-z": None } )
    for z in ( 500.0, 1000.0, 1490.0 ):
        pts = [ ( c[0] + ( r + 30 ) * math.cos( 2 * math.pi * k / 12 ), c[1] + ( r + 30 ) * math.sin( 2 * math.pi * k / 12 ), z )
                for k in range( 13 ) ]
        for a, b in zip( pts, pts[1:] ):
            rod( model, a, b, 10.0, "rw_steel" )
    mass( model, -4400, -4180, -3700, -3540, -10, 160, "brick", "roof_tiles", "hip", pitch=30.0 )


# The old village on the hillside east of the line, now a suburb: its streets ( n, e0, e1 ) and the lane up the hill
VILLAGE_STREETS = ( ( -5800.0, 1950.0, 6250.0 ), ( -6560.0, 2050.0, 6250.0 ), ( -7250.0, 2300.0, 6000.0 ) )
VILLAGE_LANE = ( 4650.0, -7600.0, -5700.0 )
CHURCH = ( 3080.0, 3720.0, -6290.0, -6110.0 )          # the nave; its tower stands at its west end


def drape( model, paint, points, half, lift=5.0 ):
    """ A road strip half wide each side of a plan polyline, laid on the land. """
    for a, b in zip( points, points[1:] ):
        a, b = np.asarray( a, float ), np.asarray( b, float )
        x = ( b - a ) / np.linalg.norm( b - a )
        y = np.array( ( -x[1], x[0] ) ) * half
        za, zb = land_z( *a ) + lift, land_z( *b ) + lift
        facing( model, paint, [ ( *( a - y ), za ), ( *( b - y ), zb ), ( *( b + y ), zb ), ( *( a + y ), za ) ], ( 0, 0, 1 ) )


def village( model ):
    """ Two- and three-storey rendered houses along three streets and a lane, gardens behind, and the parish church
    with its onion-domed tower (a south German village church's). Returns where trees may stand. """
    gardens = []
    for k, ( n, a0, a1 ) in enumerate( VILLAGE_STREETS ):
        drape( model, "rw_asphalt", [ ( e, n ) for e in np.arange( a0, a1 + 1, 300.0 ) ], 70.0 )
        for side in ( -1.0, 1.0 ):
            e = a0 + between( 0, 120, "village", k, side )
            j = 0
            while e < a1 - 200:
                w = between( 240, 420, "village", k, side, j )
                depth = between( 240, 340, "village", k, side, j, "d" )
                n_near = n + side * between( 100, 150, "village", k, side, j, "set" )
                b0, b1 = sorted( ( n_near, n_near + side * depth ) )
                church = CHURCH[0] - 260 < e + w and e < CHURCH[1] + 60 and CHURCH[2] - 120 < b1 and b0 < CHURCH[3] + 120
                lane = abs( e + w / 2 - VILLAGE_LANE[0] ) < w / 2 + 100
                if not church and not lane:
                    lo, hi = ground_range( land_z, e, e + w, b0, b1 )
                    storeys = 2 if chance( 0.7, "village", k, side, j, "s" ) else 3
                    eave = hi + storeys * 120 + 40
                    mass( model, e, e + w, b0, b1, lo - 30, eave, pick( RENDERS, "village", k, side, j ),
                          "roof_tiles" if chance( 0.75, "village", k, side, j, "r" ) else "slate",
                          "hip" if chance( 0.25, "village", k, side, j, "h" ) else "gable", along="e", pitch=42.0 )
                    gardens.append( ( e + w / 2, n_near + side * ( depth + 160 ) ) )
                e += w + between( 60, 220, "village", k, side, j, "gap" )
                j += 1
    # The lane up the hill, houses beside it
    le, ln0, ln1 = VILLAGE_LANE
    drape( model, "rw_asphalt", [ ( le, n ) for n in np.arange( ln0, ln1 + 1, 300.0 ) ], 55.0 )
    for side in ( -1.0, 1.0 ):
        for j, n in enumerate( np.arange( ln0 + 150, ln1 - 100, 470.0 ) ):
            if any( abs( n - s[0] ) < 260 for s in VILLAGE_STREETS ):
                continue
            a0, a1 = sorted( ( le + side * 110, le + side * 380 ) )
            lo, hi = ground_range( land_z, a0, a1, n, n + 300 )
            mass( model, a0, a1, n, n + 300, lo - 30, hi + 2 * 120 + 40, pick( RENDERS, "lane", side, j ), "roof_tiles", "gable",
                  along="n", pitch=42.0 )
    # The church: nave, chancel and the tower at its west end
    e0, e1, n0, n1 = CHURCH
    lo, hi = ground_range( land_z, e0 - 150, e1 + 100, n0, n1 )
    mass( model, e0, e1, n0, n1, lo - 40, hi + 380, "render_pale", "slate", "gable", along="e", pitch=48.0 )
    mass( model, e1, e1 + 110, n0 + 25, n1 - 25, lo - 40, hi + 330, "render_pale", "slate", "hip", along="e", pitch=48.0 )
    for e in np.arange( e0 + 80, e1 - 60, 120.0 ):
        for n, out in ( ( n0 - 0.5, -1.0 ), ( n1 + 0.5, 1.0 ) ):
            facing( model, "rw_window_dark", [ ( e, n, hi + 110 ), ( e + 44, n, hi + 110 ), ( e + 44, n, hi + 300 ), ( e, n, hi + 300 ) ],
                    ( 0, out, 0 ) )
    onion_tower( model, e0 - 75, ( n0 + n1 ) / 2, lo - 40, 150.0, hi - lo + 40 + 760 )
    return gardens


def portal( model ):
    """ The tunnel under the hill: a concrete portal across the whole corridor (its opening e +-660, 8.1 m over the
    bed), a parapet over it, and the first 20 m of the bore going dark. """
    top = land_z( 0.0, PORTAL_N )
    w = corridor_half( PORTAL_N )
    face = Face( ( w, PORTAL_N ), ( 0, 1 ) )                # r runs west from e +w
    o0, o1, oz = w - 660.0, w + 660.0, 290.0
    holed_wall( model, face, "rw_concrete", 0.0, 2 * w, BED, top, [ ( o0, o1, BED, oz ) ] )
    face.box( model, o0 - 24, o1 + 24, 0, 10, oz, oz + 40, "rw_concrete" )
    for r in ( o0 - 24, o1 ):
        face.box( model, r, r + 24, 0, 10, BED, oz, "rw_concrete" )
    face.box( model, -10, 2 * w + 10, -24, 0, top, top + 40, "rw_concrete", skip=( "-z", ) )
    face.box( model, -12, 2 * w + 12, -26, 3, top + 40, top + 46, "rw_dressed" )
    # The bore: lined in concrete, dark further in
    n0, n1 = PORTAL_N - 800.0, PORTAL_N
    for e, out in ( ( -660.0, 1.0 ), ( 660.0, -1.0 ) ):
        facing( model, "rw_concrete_dark", [ ( e, n0, BED ), ( e, n1, BED ), ( e, n1, oz ), ( e, n0, oz ) ], ( out, 0, 0 ) )
    facing( model, "rw_concrete_dark", [ ( -660, n0, oz ), ( 660, n0, oz ), ( 660, n1, oz ), ( -660, n1, oz ) ], ( 0, 0, -1 ) )
    flat( model, "rw_ballast_old", -660, 660, n0, n1, BED + 0.1 )
    facing( model, "rw_black", [ ( -660, n0, BED ), ( 660, n0, BED ), ( 660, n0, oz ), ( -660, n0, oz ) ], ( 0, 1, 0 ) )


# The Rotunde: the trade fair's exhibition rotunda of 1880 on the hill over the tunnel, an iron drum glazed all round,
# in its park. Levels over ROTUNDA_BASE: the sandstone plinth, the arcade of tall arched windows, an entablature, the
# clerestory, the iron frieze and the zinc cornice; a low zinc roof with a glazed ring and a lantern over it.
ROTUNDA_BAYS = 36                       # pilasters round the drum (a bay 9.3 m wide)...
ROTUNDA_LIGHTS = 2                      # ...each of two arched lights under two clerestory windows
ROTUNDA_LEVELS = { "plinth": ( -60.0, 140.0 ), "arcade": ( 140.0, 1250.0 ), "band": ( 1250.0, 1330.0 ),
                   "clerestory": ( 1330.0, 1650.0 ), "frieze": ( 1650.0, 1920.0 ), "cornice": ( 1920.0, 1990.0 ) }
ROTUNDA_ARCH = ( 180.0, 1100.0 )        # the arched lights' sills and springing: 3.8 m wide and 25 m tall
ROTUNDA_LIGHT_W = 150.0
GLAZING, IRON, IRON_PANEL, ZINC = "rw_rotunda_glass", "rw_rotunda_iron", "rw_rotunda_panel", "rw_zinc"


def curved( model, paint, points, centre, towards ):
    """ A polygon on a drum round plan centre, shaded smooth with the drum (its normals radial), facing towards (a plan
    or 3D direction). """
    pts = [ np.asarray( p, float ) for p in points ]
    towards = np.array( ( *towards, 0.0 ) )[:3] if len( towards ) == 2 else np.asarray( towards, float )
    normals = [ K.normalise( np.array( ( p[0] - centre[0], p[1] - centre[1], 0.0 ) ) ) for p in pts ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts, normals = pts[:1] + pts[:0:-1], normals[:1] + normals[:0:-1]
    model.polygon( paint, pts, normals=normals )


def rotunda_light( model, c, p0, along, out, width, z0 ):
    """ One light of the drum: a facet across along from p0 (plan), width wide, facing out; z over z0 (the base). The
    tall arched window, its clerestory window over the band, and its panel of the frieze, all in iron frames. """
    def P( s, z, d=0.0 ):
        return ( p0[0] + along[0] * s + out[0] * d, p0[1] + along[1] * s + out[1] * d, z0 + z )

    def quad( paint, s0, s1, za, zb, d=0.0 ):
        if s1 - s0 > 1e-6 and zb - za > 1e-6:
            curved( model, paint, [ P( s0, za, d ), P( s1, za, d ), P( s1, zb, d ), P( s0, zb, d ) ], c, out )

    def bar( paint, a, b, half, d=1.0 ):
        """ A thin bar between two ( s, z ) points, half wide, standing d proud. """
        a, b = np.asarray( a, float ), np.asarray( b, float )
        x = ( b - a ) / np.linalg.norm( b - a )
        y = np.array( ( -x[1], x[0] ) ) * half
        curved( model, paint, [ P( *( a - y ), d ), P( *( b - y ), d ), P( *( b + y ), d ), P( *( a + y ), d ) ], c, out )

    w0, w1 = ( width - ROTUNDA_LIGHT_W ) / 2, ( width + ROTUNDA_LIGHT_W ) / 2
    mid, r = ( w0 + w1 ) / 2, ( w1 - w0 ) / 2
    thirds = ( w0 + ( w1 - w0 ) / 3, w0 + 2 * ( w1 - w0 ) / 3 )
    sill, spring = ROTUNDA_ARCH
    a0, a1 = ROTUNDA_LEVELS["arcade"]
    quad( IRON, 0.0, w0, a0, a1 )
    quad( IRON, w1, width, a0, a1 )
    quad( IRON, w0, w1, a0, sill )
    arch = [ ( mid + r * math.cos( math.pi * k / 10 ), spring + r * math.sin( math.pi * k / 10 ) ) for k in range( 11 ) ]
    for ( sa, za ), ( sb, zb ) in zip( arch, arch[1:] ):                # the spandrels over the round head
        curved( model, IRON, [ P( sa, za ), P( sb, zb ), P( sb, a1 ), P( sa, a1 ) ], c, out )
    curved( model, GLAZING, [ P( w0, sill ), P( w1, sill ) ] + [ P( s, z ) for s, z in arch ], c, out )
    for s in thirds:                                                    # its tracery: mullions, transoms, a radiating head
        bar( IRON, ( s, sill ), ( s, spring ), 3.0 )
    for z in np.linspace( sill, spring, 6 )[1:]:
        bar( IRON, ( w0, z ), ( w1, z ), 2.5 )
    for s in thirds:
        top = spring + math.sqrt( max( r * r - ( s - mid ) ** 2, 0.0 ) )
        bar( IRON, ( s, spring ), ( mid + ( s - mid ) * 0.4, top - 2.0 ), 2.5 )
    b0, b1 = ROTUNDA_LEVELS["band"]
    quad( IRON, 0.0, width, b0, b1 )
    quad( "rw_dressed", 0.0, width, b0 + 45.0, b0 + 60.0, 1.0 )
    k0, k1 = ROTUNDA_LEVELS["clerestory"]
    g0, g1 = k0 + 30.0, k1 - 30.0
    quad( IRON, 0.0, w0, k0, k1 )
    quad( IRON, w1, width, k0, k1 )
    quad( IRON, w0, w1, k0, g0 )
    quad( IRON, w0, w1, g1, k1 )
    quad( GLAZING, w0, w1, g0, g1 )
    for s in thirds:
        bar( IRON, ( s, g0 ), ( s, g1 ), 3.0 )
    bar( IRON, ( w0, ( g0 + g1 ) / 2 ), ( w1, ( g0 + g1 ) / 2 ), 2.5 )
    f0, f1 = ROTUNDA_LEVELS["frieze"]
    quad( IRON, 0.0, width, f0, f1 )
    i0, i1, j0, j1 = 14.0, width - 14.0, f0 + 28.0, f1 - 28.0          # a panel with its lattice
    quad( IRON_PANEL, i0, i1, j0, j1, 0.5 )
    for a, b in ( ( ( i0, j0 ), ( i1, j1 ) ), ( ( i0, j1 ), ( i1, j0 ) ) ):
        bar( IRON, a, b, 4.0, 1.0 )


def rotunda( model ):
    """ The Rotunde on its plateau over the tunnel, and the oaks of its park. Returns nothing. """
    c = np.array( ROTUNDA, float )
    R, B = ROTUNDA_R, ROTUNDA_BASE
    count = ROTUNDA_BAYS * ROTUNDA_LIGHTS
    for k in range( count ):
        a0, a1 = 2 * math.pi * k / count, 2 * math.pi * ( k + 1 ) / count
        p0 = c + R * np.array( ( math.cos( a0 ), math.sin( a0 ) ) )
        p1 = c + R * np.array( ( math.cos( a1 ), math.sin( a1 ) ) )
        along = ( p1 - p0 ) / np.linalg.norm( p1 - p0 )
        out = np.array( ( along[1], -along[0] ) )
        if np.dot( out, ( p0 + p1 ) / 2 - c ) < 0:
            out = -out
        rotunda_light( model, c, p0, along, out, float( np.linalg.norm( p1 - p0 ) ), B )
        # The plinth, standing proud, and the cornice, overhanging
        q0, q1 = c + ( R + 10 ) * np.array( ( math.cos( a0 ), math.sin( a0 ) ) ), c + ( R + 10 ) * np.array( ( math.cos( a1 ), math.sin( a1 ) ) )
        z0, z1 = ROTUNDA_LEVELS["plinth"]
        curved( model, "rw_dressed", [ ( *q0, B + z0 ), ( *q1, B + z0 ), ( *q1, B + z1 ), ( *q0, B + z1 ) ], c, out )
        facing( model, "rw_dressed", [ ( *p0, B + z1 ), ( *p1, B + z1 ), ( *q1, B + z1 ), ( *q0, B + z1 ) ], ( 0, 0, 1 ) )
        k0, k1 = ROTUNDA_LEVELS["cornice"]
        o0, o1 = c + ( R + 30 ) * np.array( ( math.cos( a0 ), math.sin( a0 ) ) ), c + ( R + 30 ) * np.array( ( math.cos( a1 ), math.sin( a1 ) ) )
        curved( model, ZINC, [ ( *o0, B + k0 ), ( *o1, B + k0 ), ( *o1, B + k1 ), ( *o0, B + k1 ) ], c, out )
        facing( model, ZINC, [ ( *p0, B + k0 ), ( *p1, B + k0 ), ( *o1, B + k0 ), ( *o0, B + k0 ) ], ( 0, 0, -1 ) )
        if k % ROTUNDA_LIGHTS == 0:                                      # a pilaster between two bays
            mid = c + ( R + 10 ) * np.array( ( math.cos( a0 ), math.sin( a0 ) ) )
            radial = np.array( ( math.cos( a0 ), math.sin( a0 ), 0.0 ) )
            tangent = np.array( ( -math.sin( a0 ), math.cos( a0 ), 0.0 ) )
            zp0, zp1 = ROTUNDA_LEVELS["arcade"][0], ROTUNDA_LEVELS["frieze"][1]
            model.oriented_box( ( *mid, B + ( zp0 + zp1 ) / 2 ), ( radial, tangent, ( 0.0, 0.0, 1.0 ) ),
                                ( 20.0, 40.0, zp1 - zp0 ), { "default": IRON, "-x": None } )
    # The roof: a low zinc cone from the cornice and a glazed ring round its middle, under 10 degrees, so from the
    # streets the drum's rim is its skyline (it's 13-16 degrees up from the cab roads).
    top = B + ROTUNDA_LEVELS["cornice"][1]
    rise = math.tan( math.radians( 9.0 ) )
    r1, r2 = 0.62 * R, 0.3 * R
    z1 = top + ( R + 30 - r1 ) * rise
    z2 = z1 + ( r1 - r2 ) * rise
    lathe( model, ROTUNDA, [ ( R + 30, top ), ( r1, z1 ) ], ZINC, sides=count, cap=False )
    lathe( model, ROTUNDA, [ ( r1, z1 ), ( r2, z2 ) ], GLAZING, sides=count, cap=False )
    lathe( model, ROTUNDA, [ ( r2, z2 ), ( 0.0, z2 + r2 * rise ) ], ZINC, sides=count // 2 )
    # The park's oaks round it, thicker on the side towards the station.
    for k in range( 48 ):
        a = 2 * math.pi * ( k + between( -0.3, 0.3, "rotunda", k ) ) / 48
        north = max( 0.0, math.sin( a ) )
        if not chance( 0.55 + 0.4 * north, "rotunda", k, "keep" ):
            continue
        d = R + between( 420.0, 900.0, "rotunda", k, "d" ) + 380.0 * north * unit( "rotunda", k, "row" )
        e, n = c[0] + d * math.cos( a ), c[1] + d * math.sin( a )
        if n > PORTAL_N - 250:
            continue
        big = chance( 0.6, "rotunda", k, "big" )
        tree( model, OAK_BIG if big else OAK, e, n, land_z( e, n ) - 8, ( "rotunda", k ), 1.0 if big else 1.3 )


def ramp_trees( model ):
    """ Big trees at the foot of the overbridge's west ramp, by the line's fence and the allotment colony: from the
    west cab road they stand either side of the Rotunde's lower half, over the goods shed. """
    for k, e in enumerate( ( -1135.0, -1960.0, -2260.0 ) ):             # between the ramp and the gardens' hedges
        n = -3340.0 + between( -8.0, 8.0, "ramp_tree", k )
        tree( model, OAK_BIG, e + between( -20.0, 20.0, "ramp_tree", k, "e" ), n, land_z( e, n ) - 8, ( "ramp_tree", k ),
              between( 1.3, 1.45, "ramp_tree", k, "s" ) )


def south_blocks( model ):
    """ The city's blocks beside the line south of the ramp, out to the hills. """
    for s in ( 1.0, -1.0 ):
        for row, ( n0, n1 ) in enumerate( ( ( -5500.0, -3300.0 ), ( -7900.0, -5900.0 ) ) ):
            for k, ( a0, a1 ) in enumerate( grid_blocks( CITY_E, WORLD ) ):
                lo_e, hi_e = sorted( ( s * a0, s * a1 ) )
                detail = "near" if a0 < 9000 else "far" if a0 < 14000 else "slab"
                city_block( model, lo_e, hi_e, n0 + 20, n1 - 20, ( "south", s, row, k ), detail, "render", land_z )


def south_trees( model, gardens ):
    """ The woods on the west slope, a park beside the line on the east, the village's gardens and the cutting's top. """
    for i, e in enumerate( np.arange( -1100.0, -6400.0, -430.0 ) ):
        for j, n in enumerate( np.arange( -4500.0, -7950.0, -430.0 ) ):
            p = ( e + between( -150, 150, "wood", i, j, "e" ), n + between( -150, 150, "wood", i, j, "n" ) )
            top, crest, h = crest_of( p[1], corridor_half( p[1] ), -1.0 )
            if abs( p[0] ) < crest + 120 or not chance( 0.72, "wood", i, j ):
                continue
            if math.hypot( p[0] - GASHOLDER[0], p[1] - GASHOLDER[1] ) < GASHOLDER[2] + 360:
                continue                                    # the gasholder's yard
            big = chance( 0.45, "wood", i, j, "big" )
            tree( model, OAK_BIG if big else OAK, p[0], p[1], land_z( *p ) - 8, ( "wood", i, j ), 1.0 if big else 1.2 )
    for i, e in enumerate( np.arange( 2100.0, 6300.0, 520.0 ) ):
        for j, n in enumerate( ( -4720.0, -4990.0 ) ):     # between the works' halls and the village's back gardens
            p = ( e + between( -160, 160, "park", i, j, "e" ), n + between( -80, 80, "park", i, j, "n" ) )
            if chance( 0.55, "park", i, j ):
                big = j == 0 and chance( 0.3, "park", i, j, "big" )
                tree( model, OAK_BIG if big else OAK, p[0], p[1], land_z( *p ) - 6, ( "park", i, j ) )
    for k, ( e, n ) in enumerate( gardens ):
        if chance( 0.45, "garden", k ):
            tree( model, OAK, e + between( -80, 80, "garden", k ), n, land_z( e, n ) - 6, ( "garden", k ), 0.8 )
    # Bushes along the top of the east cutting, south of the depot
    for k, n in enumerate( np.arange( -5600.0, -7700.0, -260.0 ) ):
        top, crest, h = crest_of( n, corridor_half( n ), 1.0 )
        e = crest + between( 60, 160, "rim", k )
        tree( model, BUSH, e, n, land_z( e, n ) - 4, ( "rim", k ), 1.4 )


def south_vista():
    """ Everything south of the play area (n < -2400) but the lead's corridor: the land and the cutting's walls, the
    road overbridge at n -3100, the lineside yards, allotments, the depot, the works and gasholder, a small town, the
    tunnel portal at n -8000, the Rotunde in its park over the tunnel, the city's blocks either side and the low land
    beyond. Drawn only. """
    model = K.Model()
    east = south_land( model, 1.0, True )
    west = south_land( model, -1.0, False )
    far_land( model, east, west )
    overbridge( model )
    lineside_east( model )
    lineside_west( model )
    allotments_south( model )
    depot( model )
    works( model )
    gasholder( model )
    gardens = village( model )
    portal( model )
    rotunda( model )
    ramp_trees( model )
    south_blocks( model )
    south_trees( model, gardens )
    return configure( model )


# ---------------------------------------------------------------------------------------------------------------------
# The skyline: the rest of the city, beside the edge rows and north of the side street, out to the hills

STREET_N = tuple( 5900.0 + 2400.0 * k for k in range( 8 ) )     # the east-west streets' centres north of the side street
LOW_N = -520.0                      # the street at n -400's south kerb: the north-south streets rise from there to the seam
LAST_STREET = GRID_E[8] + 120.0     # 23220: the city's last north-south street's far kerb; fields beyond
CITY_LIMIT_N = 25000.0              # the last row of blocks' back
CAB_END = { 1.0: 8300.0 - 120.0, -1.0: 5900.0 - 120.0 }          # where each cab road meets a cross street and ends
DOMPLATZ = ( 180.0, 3780.0, 8420.0, 12980.0 )                   # the minster's square, at the end of the east cab road
KIRCHPLATZ = ( -3780.0, -180.0, 6020.0, 8180.0 )                # the brick church's, at the end of the west cab road
HILL_COLS = ( 23400.0, 26000.0, 29000.0, 32500.0, 36000.0, 40000.0 )   # E_COLS' last six, so the seam at n -2400 matches
HILL_ROWS = ( CITY_LIMIT_N, 26500.0, 29000.0, 32500.0, 36000.0, 40000.0 )


def city_r( e, n ):
    """ The rounded square's radius that ring_z goes by. """
    return ( e ** 4 + ( n - 600.0 ) ** 4 ) ** 0.25


def in_city( e0, e1, n0, n1 ):
    return all( city_r( e, n ) <= R0 for e in ( e0, e1 ) for n in ( n0, n1 ) )


def road_z( n ):
    """ The carriageways' level: -6 like north_city's, rising to the south's level ground (z 0) at the seam. """
    if n >= LOW_N:
        return ROAD_Z
    return ROAD_Z * ( n - PLAY_N0 ) / ( LOW_N - PLAY_N0 )


def e_bands( s, n ):
    """ The north-south carriageways at n on side s, as ranges of |e|: Bahnhofstrasse's half, the cab road (to its end),
    the grid's streets. """
    out = [ ( -1.0, 180.0 ) ]
    if n < CAB_END[s]:
        out.append( ( ROAD_E0, ROAD_E1 ) )
    return out + [ ( c - 120.0, c + 120.0 ) for c in GRID_E[:9] ]


def n_bands( a ):
    """ The east-west carriageways at |e| a, as ranges of n. The street at n -400 starts at the first grid street. """
    out = [ ( LOW_N, -280.0 ) ] if a > GRID_E[0] - 120.0 else []
    out += [ ( CROSS_N0, CROSS_N1 ), ( SIDE_N0 + 80.0, SIDE_N1 - 80.0 ) ]
    return out + [ ( c - 120.0, c + 120.0 ) for c in STREET_N ]


def sky_lines():
    """ The grid's lines: every kerb, the seams with the other models, and the hills' columns and rows. """
    pos = [ 180.0, ROAD_E0, ROAD_E1, BACK ] + [ c + d for c in GRID_E[:9] for d in ( -120.0, 120.0 ) ] + list( HILL_COLS )
    es = sorted( set( pos + [ -p for p in pos ] ) )
    ns = [ PLAY_N0, LOW_N, -280.0, CROSS_N0, CROSS_N1, SIDE_N0 + 80.0, SIDE_N1 - 80.0, SIDE_N1 ]
    ns += [ c + d for c in STREET_N for d in ( -120.0, 120.0 ) ] + list( HILL_ROWS )
    return es, sorted( set( ns ) )


def sky_cell( e0, e1, n0, n1 ):
    """ What fills a cell of the grid: ( 'skip', None ) for another model's, ( 'road', None ), ( 'hills', None ), or
    ( 'island', block ) with the block ( e0, e1, n0, n1 ) between the carriageways round it. """
    em, nm = ( e0 + e1 ) / 2, ( n0 + n1 ) / 2
    s, a = ( 1.0 if em > 0 else -1.0 ), abs( em )
    if a < BACK and nm < SIDE_N1:
        return "skip", None
    if a > LAST_STREET or nm > CITY_LIMIT_N:
        return "hills", None
    if DOMPLATZ[0] < em < DOMPLATZ[1] and DOMPLATZ[2] < nm < DOMPLATZ[3]:
        return "island", DOMPLATZ
    eb, nb = e_bands( s, nm ), n_bands( a )
    if any( lo < a < hi for lo, hi in eb ) or any( lo < nm < hi for lo, hi in nb ):
        return ( "road" if in_city( e0, e1, n0, n1 ) else "hills" ), None
    lo = max( hi for _, hi in eb if hi < a )
    hi = min( lo_ for lo_, _ in eb if lo_ > a )
    b0 = max( [ PLAY_N0 ] + [ top for _, top in nb if top < nm ] )
    b1 = min( [ CITY_LIMIT_N ] + [ bot for bot, _ in nb if bot > nm ] )
    block = ( lo, hi, b0, b1 ) if s > 0 else ( -hi, -lo, b0, b1 )
    return ( "island", block ) if in_city( *block ) else ( "hills", None )


def hill_paint( e, n, z ):
    """ The country round the city, as south_ground paints its far hills: woods on the heights and in patches, fields. """
    if z > 900 or unit( "hill", int( e // 2600 ), int( n // 2100 ) ) < 0.45:
        return "hedge"
    return pick( ( "lawn", "lawn", "soil", "lawn" ), "field", int( e // 3100 ), int( n // 2300 ) )


def kerb_face( model, a, b, za, zb, towards ):
    """ The face from a carriageway's edge ( za, zb under a and b ) up to the pavement or the land at z 0. """
    pts = [ ( a[0], a[1], za ), ( b[0], b[1], zb ), ( b[0], b[1], 0.0 ), ( a[0], a[1], 0.0 ) ]
    pts = [ p for k, p in enumerate( pts ) if not ( k == 3 and abs( za ) < 0.01 ) and not ( k == 2 and abs( zb ) < 0.01 ) ]
    if len( pts ) >= 3:
        facing( model, "rw_kerb", pts, towards )


def near_play( e0, e1, n0, n1 ):
    """ How far a plan rectangle is from the play area. """
    de = max( 0.0, min( abs( e0 ), abs( e1 ) ) - EDGE ) if e0 * e1 > 0 else 0.0
    dn = max( 0.0, n0 - PLAY_N1, PLAY_N0 - n1 )
    return math.hypot( de, dn )


SIDES = ( ( "-e", -1, 0 ), ( "+e", 1, 0 ), ( "-n", 0, -1 ), ( "+n", 0, 1 ) )


def sky_ground( model ):
    """ The city's carriageways (asphalt at road_z) and pavements (the blocks' islands at z 0, kerbed where a carriageway
    runs beside them), and the hills round it from the same grid's lines, so they meet the islands edge to edge.
    Returns the blocks to build on. """
    es, ns = sky_lines()
    cells = { ( i, j ): sky_cell( es[i], es[i + 1], ns[j], ns[j + 1] ) for i in range( len( es ) - 1 ) for j in range( len( ns ) - 1 ) }

    def kind( i, j ):
        return cells.get( ( i, j ), ( "none", None ) )[0]

    blocks = set()
    for ( i, j ), ( what, block ) in cells.items():
        e0, e1, n0, n1 = es[i], es[i + 1], ns[j], ns[j + 1]
        corner = { ( -1, -1 ): ( e0, n0 ), ( 1, -1 ): ( e1, n0 ), ( 1, 1 ): ( e1, n1 ), ( -1, 1 ): ( e0, n1 ) }
        edges = { "-e": ( corner[-1, -1], corner[-1, 1] ), "+e": ( corner[1, -1], corner[1, 1] ),
                  "-n": ( corner[-1, -1], corner[1, -1] ), "+n": ( corner[-1, 1], corner[1, 1] ) }
        if what == "road":
            facing( model, "rw_asphalt", [ ( e0, n0, road_z( n0 ) ), ( e1, n0, road_z( n0 ) ), ( e1, n1, road_z( n1 ) ),
                                           ( e0, n1, road_z( n1 ) ) ], ( 0, 0, 1 ) )
            for side, di, dj in SIDES:
                if kind( i + di, j + dj ) == "hills":       # a street ends at the fields: close it
                    a, b = edges[side]
                    kerb_face( model, a, b, road_z( a[1] ), road_z( b[1] ), ( -di, -dj, 0 ) )
        elif what == "island":
            blocks.add( block )
            near = near_play( e0, e1, n0, n1 ) < 9000
            kerbs = [ side for side, di, dj in SIDES if kind( i + di, j + dj ) == "road" ]
            k = 10.0 if near else 0.0
            a0, a1 = e0 + ( k if "-e" in kerbs else 0 ), e1 - ( k if "+e" in kerbs else 0 )
            b0, b1 = n0 + ( k if "-n" in kerbs else 0 ), n1 - ( k if "+n" in kerbs else 0 )
            flat( model, "rw_paving", a0, a1, b0, b1, 0.0 )
            for side, di, dj in SIDES:
                if side not in kerbs:
                    continue
                a, b = edges[side]
                kerb_face( model, a, b, road_z( a[1] ), road_z( b[1] ), ( di, dj, 0 ) )
                if near:
                    strip = { "-e": ( e0, a0, n0, n1 ), "+e": ( a1, e1, n0, n1 ), "-n": ( a0, a1, n0, b0 ), "+n": ( a0, a1, b1, n1 ) }[side]
                    flat( model, "rw_kerb", *strip, 0.0 )
    rows = [ [ ( e, n, land_z( e, n ) ) for e in es ] for n in ns ]

    def paint_of( e, n, z ):
        i = int( np.searchsorted( es, e ) ) - 1
        j = int( np.searchsorted( ns, n ) ) - 1
        return hill_paint( e, n, z ) if kind( i, j ) == "hills" else None

    for a, b in zip( rows, rows[1:] ):
        zip_rows( model, a, b, paint_of )
    return blocks


def sky_house( model, e0, e1, n0, n1, along, key, storeys=None, corner=False, walls="facade" ):
    return city_house( model, e0, e1, n0, n1, along, key, walls, lambda e, n: 0.0, storeys, corner )


def windows_on( model, face_e=None, face_n=None, span=( 0.0, 0.0 ), z=( 0.0, 0.0 ), step=120.0, width=60.0, out=1.0,
                paint="rw_window_dark", point=0.0 ):
    """ A row of windows on a wall at e face_e (facing out along e) or n face_n (along n), over span, from z[0] to z[1];
    point raises a pointed or round head that much over z[1]. """
    a = span[0] + ( ( span[1] - span[0] ) % step ) / 2 + ( step - width ) / 2
    while a + width <= span[1] + 0.01:
        mid = a + width / 2
        if face_e is not None:
            pts = [ ( face_e, a, z[0] ), ( face_e, a + width, z[0] ), ( face_e, a + width, z[1] ) ]
            pts += [ ( face_e, mid, z[1] + point ) ] if point else []
            pts += [ ( face_e, a, z[1] ) ]
            facing( model, paint, pts, ( out, 0, 0 ) )
        else:
            pts = [ ( a, face_n, z[0] ), ( a + width, face_n, z[0] ), ( a + width, face_n, z[1] ) ]
            pts += [ ( mid, face_n, z[1] + point ) ] if point else []
            pts += [ ( a, face_n, z[1] ) ]
            facing( model, paint, pts, ( 0, out, 0 ) )
        a += step


def first_block( model, s ):
    """ The block behind each edge row, between it and the first grid street (|e| 2700..3780), from the seam at n -2400
    to the cross street. A wall closes the edge's gravel strip; behind it a goods shed (a carrier's, two storeys of brick)
    and its yard, a north-light workshop behind the lane's wall, the courtyard behind the row's backs, crossed by two
    rear houses (Quergebaeude), and a row of tenements on the street. The arches through the rows (east n 1750, west
    n 300) look into the courtyard. """
    def span( a0, a1 ):
        return sorted( ( s * a0, s * a1 ) )

    model.box( ( span( BACK, BACK + 24 )[0], PLAY_N0, 0 ), ( span( BACK, BACK + 24 )[1], LANE_N0 - 24, 300 ),
               { "default": "brick", "+z": "rw_concrete" }, skip=( "-z", ) )
    flat( model, "rw_concrete", *span( BACK + 24, 2900 ), PLAY_N0, LANE_N0 - 24, 0.2 )
    # The goods shed, its loading doors and canopy to the yard
    a0, a1, n0, n1 = 2900.0, 3700.0, PLAY_N0 + 80, -1480.0
    mass( model, *span( a0, a1 ), n0, n1, -20, 420, "brick", "slate", "gable", along="n", pitch=30.0 )
    face = s * ( a0 - 0.5 )
    windows_on( model, face_e=face, span=( n0, n1 ), z=( 250, 370 ), step=140, width=70, out=-s, point=14 )
    windows_on( model, face_e=s * ( a1 + 0.5 ), span=( n0, n1 ), z=( 250, 370 ), step=140, width=70, out=s, point=14 )
    windows_on( model, face_e=face, span=( n0, n1 ), z=( 0, 180 ), step=280, width=150, out=-s, paint="rw_steel_grey" )
    model.box( ( span( a0 - 110, a0 )[0], n0 + 40, 196 ), ( span( a0 - 110, a0 )[1], n1 - 40, 202 ), "rw_steel_grey" )
    # The workshop, and the tenements on the street
    sawtooth( model, *span( BACK + 24, 3220 ), LANE_N0 - 24, ROW_N0 + 20, -20, 290, "brick", 2, rise=70.0 )
    x0, x1 = 3220.0, 3700.0
    sky_house( model, *span( x0, x1 ), LANE_N0 - 24, LANE_N0 + 456, "e", ( "first", s, "c0" ), corner=True )
    sky_house( model, *span( x0, x1 ), ROW_N1 - 480, ROW_N1, "e", ( "first", s, "c1" ), corner=True )
    n = LANE_N0 + 456
    for j, w in enumerate( split( ROW_N1 - 480 - n, 380.0, 720.0, "first", s ) ):
        sky_house( model, *span( x0, x1 ), n, n + w, "n", ( "first", s, j ) )
        n += w
    # The courtyard: setts, two rear houses across it, lawns with a tree each, and its wall and gate on the cross street
    flat( model, "setts", *span( BACK, x0 ), ROW_N0 + 20, ROW_N1 - 20, 0.2 )
    for k, ( q0, q1 ) in enumerate( ( ( -500.0, -260.0 ), ( 900.0, 1140.0 ) ) ):
        city_house( model, *span( BACK, x0 ), q0, q1, "e", ( "rear", s, k ), "render", lambda e, n: 0.0, storeys=4 )
    for k, ( q0, q1 ) in enumerate( ( ( -1050.0, -650.0 ), ( 150.0, 650.0 ), ( 1300.0, 1700.0 ) ) ):
        flat( model, "lawn", *span( 2860, 3160 ), q0, q1, 0.35 )
        tree( model, OAK, s * 3010, ( q0 + q1 ) / 2, 0.0, ( "yard", s, k ), 0.9 )
    model.box( ( span( BACK, x0 )[0], ROW_N1 - 20, 0 ), ( span( BACK, x0 )[1], ROW_N1, 300 ),
               { "default": "brick", "+z": "rw_concrete" }, skip=( "-z", ) )
    g0, g1 = span( 2860, 3060 )
    facing( model, "rw_steel_grey", [ ( g0, ROW_N1 + 0.5, 0 ), ( g1, ROW_N1 + 0.5, 0 ), ( g1, ROW_N1 + 0.5, 260 ), ( g0, ROW_N1 + 0.5, 260 ) ],
            ( 0, 1, 0 ) )


def behind_north_row( model, s ):
    """ The houses between north_city's row (|e| 2200..2700) and the first grid street, back to back between the cross
    street and the side street. """
    for k, ( n0, n1 ) in enumerate( ( ( CROSS_N1 + 60, 2850.0 ), ( 2850.0, SIDE_N0 ) ) ):
        sky_house( model, *sorted( ( s * BACK, s * 3220.0 ) ), n0, n1, "e", ( "nrow", s, k, 0 ) )
        sky_house( model, *sorted( ( s * 3220.0, s * 3700.0 ) ), n0, n1, "e", ( "nrow", s, k, 1 ), corner=True )


def apse( model, c, n, radius, eave, apex, wall, roof_paint, base=-20.0, segments=4 ):
    """ A half-polygonal apse round ( c, n ) on the +n side, its roof up to apex ( the ridge it meets ). """
    pts = [ ( c + radius * math.cos( math.pi * k / segments ), n + radius * math.sin( math.pi * k / segments ) )
            for k in range( segments + 1 ) ]
    for ( pa, pb ) in zip( pts, pts[1:] ):
        mid = ( ( pa[0] + pb[0] ) / 2 - c, ( pa[1] + pb[1] ) / 2 - n, 0.0 )
        facing( model, wall, [ ( *pa, base ), ( *pb, base ), ( *pb, eave ), ( *pa, eave ) ], mid )
        facing( model, roof_paint, [ ( *pa, eave ), ( *pb, eave ), ( c, n, apex ) ], ( mid[0], mid[1], radius ) )


MINSTER = ( 1750.0, 9500.0 )        # its axis (the east cab road's centre line) and west front


def minster( model ):
    """ The minster on the Domplatz, closing the east cab road's view: a Neo-Gothic basilica (1860s-1880s) of red
    sandstone ashlar under slate. Nave 15 m wide and 28 m to its eaves, aisles 7.6 m wide and 15 m high, a transept, an
    apse, flying buttresses, and twin west towers 11 m square: shafts to 48 m, open octagons to 58 m and stone spires
    to 76 m (Regensburg's are 105 m, Vienna's Votivkirche's 99 m). """
    ax, f = MINSTER
    red, slate = "rw_dressed_red", "slate"
    nave, aisle, back = 300.0, 600.0, 12300.0
    clere, low = 1100.0, 600.0
    ridge = clere + nave * math.tan( math.radians( 60 ) )
    front = f + 40.0                                    # the centre bay, set back between the towers
    th, tc = 220.0, 400.0                               # the towers' half width and their centres off the axis
    t1 = f + 2 * th
    cross0, cross1 = 11200.0, 11700.0
    model.box( ( ax - nave, front, -20 ), ( ax + nave, back, clere ), { "default": red, "+z": None, "-z": None, "+n": None } )
    roof( model, ax - nave, ax + nave, front, back, clere, slate, "gable", along="n", pitch=60.0, end_paint=red )
    apse( model, ax, back, nave, clere, ridge, red, slate )
    # Portal and rose window in the centre bay
    facing( model, "rw_window_dark", [ ( ax - 110, front - 0.5, 0 ), ( ax + 110, front - 0.5, 0 ), ( ax + 110, front - 0.5, 290 ),
                                       ( ax, front - 0.5, 410 ), ( ax - 110, front - 0.5, 290 ) ], ( 0, -1, 0 ) )
    facing( model, "rw_window_dark", [ ( ax + 120 * math.cos( a ), front - 0.5, 760 + 120 * math.sin( a ) )
                                       for a in ( 2 * math.pi * k / 12 for k in range( 12 ) ) ], ( 0, -1, 0 ) )
    # The aisles under lean-to roofs, their buttresses with pinnacles and flying buttresses to the clerestory
    for s in ( -1.0, 1.0 ):
        inner, outer = ax + s * nave, ax + s * aisle
        lo, hi = sorted( ( inner, outer ) )
        for n0, n1 in ( ( t1, cross0 ), ( cross1, back ) ):
            skip = { "+z": None, "-z": None, ( "-e" if s > 0 else "+e" ): None }
            if n1 == cross0:
                skip["+n"] = None
            skip["-n"] = None
            model.box( ( lo, n0, -20 ), ( hi, n1, low ), { "default": red, **skip } )
            facing( model, slate, [ ( outer, n0, low ), ( outer, n1, low ), ( inner, n1, 800 ), ( inner, n0, 800 ) ], ( s, 0, 1 ) )
            if n1 == back:
                facing( model, red, [ ( outer, back, low ), ( inner, back, low ), ( inner, back, 800 ) ], ( 0, 1, 0 ) )
            bays = np.arange( n0 + 150, n1 - 100, 300.0 )
            for k, n in enumerate( bays ):
                b0, b1 = sorted( ( outer, outer + s * 60 ) )
                model.box( ( b0, n - 25, -20 ), ( b1, n + 25, 640 ), { "default": red, "-z": None } )
                lathe( model, ( outer + s * 30, n ), [ ( 36.0, 640.0 ), ( 0.0, 780.0 ) ], red, sides=4, turn=math.pi / 4 )
                rod( model, ( outer + s * 30, n, 600 ), ( inner, n, 980 ), 22.0, red )
                if k + 1 < len( bays ):
                    m = ( n + bays[k + 1] ) / 2
                    windows_on( model, face_e=outer + s * 0.5, span=( m - 60, m + 60 ), z=( 140, 470 ), step=120, width=100,
                                out=s, point=50 )
                    windows_on( model, face_e=inner + s * 0.5, span=( m - 60, m + 60 ), z=( 830, 1010 ), step=120, width=100,
                                out=s, point=40 )
    # The transept, its end windows and roses
    model.box( ( ax - 850, cross0, -20 ), ( ax + 850, cross1, clere ), { "default": red, "+z": None, "-z": None } )
    roof( model, ax - 850, ax + 850, cross0, cross1, clere, slate, "gable", along="e",
          pitch=math.degrees( math.atan( ( ridge - clere ) / 250.0 ) ), end_paint=red )
    for s in ( -1.0, 1.0 ):
        e = ax + s * 850.5
        windows_on( model, face_e=e, span=( 11300, 11600 ), z=( 250, 820 ), step=300, width=180, out=s, point=90 )
        facing( model, "rw_window_dark", [ ( e, 11450 + 90 * math.cos( a ), 1260 + 90 * math.sin( a ) )
                                           for a in ( 2 * math.pi * k / 10 for k in range( 10 ) ) ], ( s, 0, 0 ) )
    lathe( model, ( ax, ( cross0 + cross1 ) / 2 ), [ ( 70.0, ridge - 120 ), ( 70.0, ridge + 300 ), ( 0.0, ridge + 900 ) ], "copper",
           sides=8, turn=math.pi / 8 )
    # The west towers
    for s in ( -1.0, 1.0 ):
        c, cn = ax + s * tc, f + th
        model.box( ( c - th, f, -20 ), ( c + th, t1, 1900 ), { "default": red, "-z": None } )
        for de in ( -1.0, 1.0 ):
            for dn in ( -1.0, 1.0 ):
                pe, pn = c + de * ( th - 10 ), cn + dn * ( th - 10 )
                model.box( ( pe - 40, pn - 40, -20 ), ( pe + 40, pn + 40, 1560 ), { "default": red, "-z": None } )
                lathe( model, ( c + de * ( th - 36 ), cn + dn * ( th - 36 ) ), [ ( 46.0, 1900.0 ), ( 46.0, 1990.0 ), ( 0.0, 2260.0 ) ],
                       red, sides=4, turn=math.pi / 4 )
        lathe( model, ( c, cn ), [ ( 190.0, 1900.0 ), ( 190.0, 2300.0 ), ( 206.0, 2300.0 ), ( 206.0, 2330.0 ), ( 196.0, 2330.0 ),
                                   ( 0.0, 3000.0 ) ], red, sides=8, turn=math.pi / 8 )
        rod( model, ( c, cn, 3000 ), ( c, cn, 3080 ), 5.0, "iron_black" )
        rod( model, ( c - 22, cn, 3055 ), ( c + 22, cn, 3055 ), 5.0, "iron_black" )
        windows_on( model, face_n=f - 0.5, span=( c - 60, c + 60 ), z=( 520, 900 ), step=120, width=110, out=-1.0, point=60 )
        for face in ( "n0", "n1", "e" ):
            if face == "e":
                windows_on( model, face_e=c + s * ( th + 0.5 ), span=( cn - 150, cn + 150 ), z=( 1380, 1740 ), step=150, width=80,
                            out=s, point=40 )
            else:
                nn, out = ( f - 0.5, -1.0 ) if face == "n0" else ( t1 + 0.5, 1.0 )
                windows_on( model, face_n=nn, span=( c - 150, c + 150 ), z=( 1380, 1740 ), step=150, width=80, out=out, point=40 )


def domplatz( model, block ):
    """ The minster's square: the minster, a row of canons' houses either side, plane trees in front. """
    minster( model )
    e0, e1, n0, n1 = block
    for k, ( a0, a1, b0, b1 ) in enumerate( ( ( e1 - 560, e1 - 80, 9000.0, n1 - 80 ), ( e0 + 80, e0 + 560, 10200.0, n1 - 80 ) ) ):
        n = b0
        for j, w in enumerate( split( b1 - b0, 420.0, 700.0, "dom", k ) ):
            sky_house( model, a0, a1, n, n + w, "n", ( "dom", k, j ), storeys=pick( ( 3, 4, 4 ), "dom", k, j ) )
            n += w
    for k, e in enumerate( ( 600.0, 1000.0, 2500.0, 2900.0 ) ):
        for j, n in enumerate( ( 8700.0, 9150.0 ) ):
            tree( model, OAK_BIG if j == 0 else OAK, e, n, 0.0, ( "dom", "tree", k, j ), 0.8 if j == 0 else 1.2 )


def brick_church( model, block ):
    """ The church square at the end of the west cab road: a Gothic hall church of brick (north German Backsteingotik)
    with its west tower, 38 m to the eaves of its spire's broach and 71 m to the top, under a copper spire; houses down
    both sides. """
    ax, tn, th = -1750.0, 6400.0, 180.0
    model.box( ( ax - th, tn - th, -20 ), ( ax + th, tn + th, 1500 ), { "default": "brick", "-z": None } )
    lathe( model, ( ax, tn ), [ ( th / math.cos( math.pi / 8 ), 1500.0 ), ( 0.0, 2800.0 ) ], "copper", sides=8, turn=math.pi / 8 )
    rod( model, ( ax, tn, 2800 ), ( ax, tn, 2860 ), 4.0, "iron_black" )
    for out, nn in ( ( -1.0, tn - th - 0.5 ), ( 1.0, tn + th + 0.5 ) ):
        windows_on( model, face_n=nn, span=( ax - 120, ax + 120 ), z=( 1150, 1420 ), step=120, width=70, out=out, point=35 )
    for s in ( -1.0, 1.0 ):
        windows_on( model, face_e=ax + s * ( th + 0.5 ), span=( tn - 120, tn + 120 ), z=( 1150, 1420 ), step=120, width=70, out=s, point=35 )
    windows_on( model, face_n=tn - th - 0.5, span=( ax - 70, ax + 70 ), z=( 0, 330 ), step=140, width=140, out=-1.0, point=60 )
    hw, n0, n1, eave = 420.0, tn + th, 7650.0, 700.0
    ridge = eave + hw * math.tan( math.radians( 55 ) )
    model.box( ( ax - hw, n0, -20 ), ( ax + hw, n1, eave ), { "default": "brick", "+z": None, "-z": None, "+n": None } )
    roof( model, ax - hw, ax + hw, n0, n1, eave, "roof_tiles", "gable", along="n", pitch=55.0, end_paint="brick" )
    apse( model, ax, n1, hw, eave, ridge, "brick", "roof_tiles" )
    for s in ( -1.0, 1.0 ):
        wall = ax + s * hw
        bays = np.arange( n0 + 140, n1 - 60, 270.0 )
        for k, n in enumerate( bays ):
            b0, b1 = sorted( ( wall, wall + s * 50 ) )
            model.box( ( b0, n - 22, -20 ), ( b1, n + 22, 560 ), { "default": "brick", "-z": None } )
            if k + 1 < len( bays ):
                m = ( n + bays[k + 1] ) / 2
                windows_on( model, face_e=wall + s * 0.5, span=( m - 50, m + 50 ), z=( 120, 560 ), step=100, width=84, out=s, point=50 )
    e0, e1, b0, b1 = block
    for k, ( a0, a1 ) in enumerate( ( ( e0 + 80, e0 + 560 ), ( e1 - 560, e1 - 80 ) ) ):
        n = b0 + 80
        for j, w in enumerate( split( b1 - b0 - 160, 420.0, 700.0, "kirch", k ) ):
            sky_house( model, a0, a1, n, n + w, "n", ( "kirch", k, j ) )
            n += w
    for k, ( e, n ) in enumerate( ( ( -2700.0, 6250.0 ), ( -2950.0, 6750.0 ), ( -950.0, 6250.0 ), ( -1050.0, 6750.0 ) ) ):
        tree( model, OAK_BIG, e, n, 0.0, ( "kirch", "tree", k ), 0.75 )


BAROQUE = ( 8820.0, 10980.0, 13220.0, 15380.0 )         # the blocks the other landmarks stand in
OFFICE = ( -10980.0, -8820.0, 10820.0, 12980.0 )
SLAB = ( -6180.0, -4020.0, 3620.0, 5780.0 )
BREWERY = ( 11220.0, 13380.0, 3620.0, 5780.0 )
WATER = ( -15780.0, -13620.0, 15620.0, 17780.0 )
CHAPELS = ( ( 16020.0, 18180.0, 8420.0, 10580.0 ), ( -20580.0, -18420.0, 13220.0, 15380.0 ) )


def row_of_houses( model, e0, e1, n0, n1, key, storeys=None ):
    """ Houses side by side along n between e0 and e1. """
    n = n0
    for j, w in enumerate( split( n1 - n0, 420.0, 700.0, *key ) ):
        sky_house( model, e0, e1, n, n + w, "n", ( *key, j ), storeys=storeys )
        n += w


def baroque_church( model ):
    """ A Baroque parish church (18th century): a rendered nave under tiles, round-headed windows, and its tower's copper
    onion dome and cross 48 m up. """
    e0, e1, n0, n1 = BAROQUE
    onion_tower( model, 9900.0, 13600.0, 0.0, 320.0, 1300.0 )
    mass( model, 9570.0, 10230.0, 13760.0, 14900.0, -20, 750, "render_cream", "roof_tiles", "gable", along="n", pitch=50.0 )
    for s in ( -1.0, 1.0 ):
        windows_on( model, face_e=9900.0 + s * 330.5, span=( 13800.0, 14860.0 ), z=( 260, 560 ), step=190, width=90, out=s, point=30 )
    for k, ( a0, a1 ) in enumerate( ( ( e0 + 80, e0 + 560 ), ( e1 - 560, e1 - 80 ) ) ):
        row_of_houses( model, a0, a1, n0 + 80, n1 - 80, ( "baroque", k ) )
    for k, e in enumerate( ( 9450.0, 10350.0 ) ):
        tree( model, OAK_BIG, e, 13380.0, 0.0, ( "baroque", "tree", k ), 0.8 )


def office_tower( model ):
    """ A 1970s office tower on a podium: 27 storeys of 3.3 m in a dark curtain wall with concrete spandrels and corner
    fins, 99 m to the roof and 104 m to its plant room. """
    e0, e1, n0, n1 = OFFICE[0] + 80, OFFICE[1] - 80, OFFICE[2] + 80, OFFICE[3] - 80
    model.box( ( e0, n0, -20 ), ( e1, n1, 380 ), { "default": "rw_concrete", "-z": None, "+z": "rw_concrete_dark" } )
    for face, out in ( ( n0 - 0.5, -1.0 ), ( n1 + 0.5, 1.0 ) ):
        facing( model, "rw_window_dark", [ ( e0 + 40, face, 40 ), ( e1 - 40, face, 40 ), ( e1 - 40, face, 330 ), ( e0 + 40, face, 330 ) ],
                ( 0, out, 0 ) )
    for face, out in ( ( e0 - 0.5, -1.0 ), ( e1 + 0.5, 1.0 ) ):
        facing( model, "rw_window_dark", [ ( face, n0 + 40, 40 ), ( face, n1 - 40, 40 ), ( face, n1 - 40, 330 ), ( face, n0 + 40, 330 ) ],
                ( out, 0, 0 ) )
    t0, t1, u0, u1, top = -10400.0, -9300.0, 11500.0, 12200.0, 3900.0
    model.box( ( t0, u0, 380 ), ( t1, u1, top ), { "default": "rw_window_dark", "-z": None, "+z": "rw_concrete_dark" } )
    for k in range( 1, 27 ):
        z = 380.0 + 130.0 * k
        model.box( ( t0 - 4, u0 - 4, z - 14 ), ( t1 + 4, u1 + 4, z + 14 ), { "default": "rw_concrete", "+z": None, "-z": None } )
    for e in ( t0, t1 ):
        for n in ( u0, u1 ):
            model.box( ( e - 16, n - 16, 380 ), ( e + 16, n + 16, top + 30 ), { "default": "rw_concrete", "-z": None } )
    model.box( ( t0 + 160, u0 + 120, top ), ( t1 - 160, u1 - 120, top + 200 ), { "default": "rw_concrete", "-z": None } )


def slab_block( model ):
    """ A 1960s slab block among the old houses: 16 storeys of 2.9 m (47 m), concrete with ribbon windows, its shopping
    pavilion on the street, a lawn and trees. """
    e0, e1, n0, n1 = -5550.0, -4650.0, 4500.0, 4900.0
    top = 16 * 114.0 + 60
    model.box( ( e0, n0, -20 ), ( e1, n1, top ), { "default": "rw_concrete", "-z": None, "+z": "rw_concrete_dark" } )
    for k in range( 16 ):
        z = 60.0 + 114.0 * k
        for face, out in ( ( n0 - 0.5, -1.0 ), ( n1 + 0.5, 1.0 ) ):
            facing( model, "rw_window_dark", [ ( e0 + 30, face, z + 28 ), ( e1 - 30, face, z + 28 ), ( e1 - 30, face, z + 84 ),
                                               ( e0 + 30, face, z + 84 ) ], ( 0, out, 0 ) )
    model.box( ( e0 + 300, n0 + 100, top ), ( e0 + 520, n1 - 100, top + 110 ), { "default": "rw_concrete", "-z": None } )
    a0, a1, b0, b1 = -6100.0, -4100.0, 3700.0, 3950.0
    model.box( ( a0, b0, -20 ), ( a1, b1, 200 ), { "default": "rw_concrete", "-z": None, "+z": "rw_concrete_dark" } )
    facing( model, "rw_window_dark", [ ( a0 + 40, b0 - 0.5, 20 ), ( a1 - 40, b0 - 0.5, 20 ), ( a1 - 40, b0 - 0.5, 160 ),
                                       ( a0 + 40, b0 - 0.5, 160 ) ], ( 0, -1, 0 ) )
    model.box( ( a0, b0 - 70, 170 ), ( a1, b0, 180 ), "rw_concrete" )
    flat( model, "lawn", -5560.0, -4100.0, 4020.0, 5700.0, 0.35 )
    row_of_houses( model, -6100.0, -5620.0, 4000.0, 5700.0, ( "slab", "row" ) )
    for k, ( e, n ) in enumerate( ( ( -5300.0, 4200.0 ), ( -4400.0, 4300.0 ), ( -4900.0, 5300.0 ), ( -4350.0, 5450.0 ) ) ):
        tree( model, OAK, e, n, 0.0, ( "slab", "tree", k ), 1.1 )


def brewery( model ):
    """ A brewery of the 1890s in brick: the brewhouse, the malt house with its two kilns' pyramid roofs and cowls, the
    stores, and the boiler house's 51 m chimney. """
    mass( model, 11400.0, 12400.0, 3800.0, 4500.0, -20, 900, "brick", "slate", "gable", along="e", pitch=35.0 )
    windows_on( model, face_n=3799.5, span=( 11400.0, 12400.0 ), z=( 420, 760 ), step=160, width=90, out=-1.0, point=30 )
    mass( model, 12500.0, 13300.0, 3800.0, 5000.0, -20, 1100, "brick", "slate", "hip", pitch=35.0 )
    windows_on( model, face_n=3799.5, span=( 12500.0, 13300.0 ), z=( 300, 1000 ), step=200, width=40, out=-1.0 )
    for k, e in enumerate( ( 12560.0, 12940.0 ) ):
        n = 4250.0
        model.box( ( e, n, 1100 ), ( e + 300, n + 300, 1500 ), { "default": "brick", "-z": None, "+z": None } )
        roof( model, e, e + 300, n, n + 300, 1500, "slate", "pyramid", pitch=55.0 )
        lathe( model, ( e + 150, n + 150 ), [ ( 40.0, 1700.0 ), ( 40.0, 1790.0 ), ( 0.0, 1830.0 ) ], "rw_steel_grey", sides=6 )
    mass( model, 11400.0, 13300.0, 5000.0, 5700.0, -20, 600, "brick", "slate", "gable", along="e", pitch=35.0 )
    flat( model, "rw_concrete", 11300.0, 13300.0, 4500.0, 5000.0, 0.2 )
    chimney( model, 12100.0, 4750.0, 0.0, 2000.0, 90.0, 55.0 )


def water_tower( model ):
    """ A water tower of 1900 in a park: a brick shaft, a sandstone corbel under the rendered tank, a slate cone and a
    copper lantern, 50 m to the top. """
    e0, e1, n0, n1 = WATER
    c = ( -14700.0, 16700.0 )
    flat( model, "lawn", e0 + 80, e1 - 80, n0 + 80, n1 - 80, 0.35 )
    lathe( model, c, [ ( 260.0, -20.0 ), ( 260.0, 1150.0 ) ], "brick", sides=12, cap=False )
    lathe( model, c, [ ( 260.0, 1150.0 ), ( 380.0, 1220.0 ) ], "rw_sandstone", sides=12, cap=False )
    lathe( model, c, [ ( 380.0, 1220.0 ), ( 380.0, 1560.0 ) ], "render_pale", sides=12, cap=False )
    lathe( model, c, [ ( 380.0, 1560.0 ), ( 400.0, 1580.0 ), ( 60.0, 1840.0 ) ], "slate", sides=12, cap=False )
    lathe( model, c, [ ( 60.0, 1840.0 ), ( 60.0, 1900.0 ), ( 0.0, 1960.0 ) ], "copper", sides=8 )
    for k in range( 8 ):
        a = 2 * math.pi * k / 8
        d = np.array( ( math.cos( a ), math.sin( a ) ) )
        side = np.array( ( -d[1], d[0] ) ) * 30
        p = np.array( c ) + d * 381
        facing( model, "rw_window_dark", [ ( *( p - side ), 1300 ), ( *( p + side ), 1300 ), ( *( p + side ), 1460 ), ( *( p - side ), 1460 ) ],
                ( d[0], d[1], 0 ) )
    for k, ( e, n ) in enumerate( ( ( -15300.0, 16000.0 ), ( -14000.0, 16100.0 ), ( -15400.0, 17300.0 ), ( -14100.0, 17400.0 ),
                                    ( -14700.0, 15900.0 ), ( -13900.0, 16800.0 ) ) ):
        tree( model, OAK_BIG if k % 2 else OAK, e, n, 0.0, ( "water", "tree", k ), 1.0 )


def chapel( model, block, key ):
    """ A small parish church in a block's courtyard: a west tower under a slate spire, 36 m, and its nave. The houses
    round it are a far block's. """
    e0, e1, n0, n1 = block
    city_block( model, e0 + 80, e1 - 80, n0 + 80, n1 - 80, key, "far" )
    c, n = ( e0 + e1 ) / 2, ( n0 + n1 ) / 2 - 350
    model.box( ( c - 120, n - 120, -20 ), ( c + 120, n + 120, 900 ), { "default": "render_pale", "-z": None } )
    lathe( model, ( c, n ), [ ( 120 * math.sqrt( 2 ), 900.0 ), ( 0.0, 1420.0 ) ], "slate", sides=4, turn=math.pi / 4 )
    mass( model, c - 200, c + 200, n + 120, n + 800, -20, 520, "render_pale", "roof_tiles", "gable", along="n", pitch=50.0 )


def sky_blocks( model, blocks ):
    """ The buildings on the city's blocks: the landmarks on theirs, perimeter blocks of houses on the rest, in less
    detail the further they are from the play area. """
    for block in sorted( blocks ):
        e0, e1, n0, n1 = block
        s = 1.0 if e0 + e1 > 0 else -1.0
        a0 = min( abs( e0 ), abs( e1 ) )
        if a0 == ROAD_E1 and n1 == CROSS_N0:
            first_block( model, s )
        elif a0 == ROAD_E1 and n0 == CROSS_N1:
            behind_north_row( model, s )
        elif block == DOMPLATZ:
            domplatz( model, block )
        elif block == KIRCHPLATZ:
            brick_church( model, block )
        elif block == BAROQUE:
            baroque_church( model )
        elif block == OFFICE:
            office_tower( model )
        elif block == SLAB:
            slab_block( model )
        elif block == BREWERY:
            brewery( model )
        elif block == WATER:
            water_tower( model )
        elif block in CHAPELS:
            chapel( model, block, ( "chapel", round( e0 ), round( n0 ) ) )
        else:
            c0, c1 = e0 + 80, e1 - 80
            b0 = n0 + ( 60 if n0 == CROSS_N1 else 80 )
            b1 = n1 - ( 60 if n1 == CROSS_N0 else 80 )
            d = near_play( c0, c1, b0, b1 )
            detail = "near" if d < 4500 else "far" if d < 10000 else "slab"
            city_block( model, c0, c1, b0, b1, ( "sky", round( e0 ), round( n0 ) ), detail )
            if detail == "near" and c1 - c0 > 1500 and b1 - b0 > 1500:
                tree( model, OAK_BIG, ( c0 + c1 ) / 2, ( b0 + b1 ) / 2, 0.0, ( "court", round( e0 ), round( n0 ) ), 1.1 )


TRAM_END = GRID_E[4] - 120.0        # 13380: the tramway runs on along the cross street to here (its loop is out of sight)
DASH_END = 9000.0                   # centre lines are painted this far out (beyond, they're under a pixel)


def sky_streets( model ):
    """ The streets' furniture: the tramway on along the cross street, lamps along the cab roads and Bahnhofstrasse,
    and centre lines on the streets near the play area. """
    for s in ( 1.0, -1.0 ):
        e0, e1 = sorted( ( s * BACK, s * TRAM_END ) )
        for n in TRAM_N:
            tram_track( model, e0, e1, n )
        poles = []
        e = 3500.0
        while e < TRAM_END - 200:
            if any( abs( e - c ) < STREET_HALF + 40 for c in GRID_E ):
                e += 300.0
            poles.append( s * e )
            e += 1100.0
        tram_wires( model, e0, e1, poles )
        # Lamps: staggered either side of the cab road to its end, and down Bahnhofstrasse's pavements
        def clear( n ):
            return not any( lo - 30 < n < hi + 30 for lo, hi in n_bands( 0.0 ) )

        for n in np.arange( SIDE_N1 + 60, CAB_END[s] - 200, 540.0 ):
            for e, m, out in ( ( ROAD_E1 + 16, n, -s ), ( ROAD_E0 - 16, n + 270, s ) ):
                if clear( m ):
                    street_lamp( model, s * e, m, ( out, 0 ) )
        for n in np.arange( SIDE_N1 + 300, DASH_END, 900.0 ):
            m = n + ( 0 if s > 0 else 450 )
            if clear( m ):
                street_lamp( model, s * 196.0, m, ( -s, 0 ) )
        # Centre lines between the junctions
        for c, n0 in ( ( ( ROAD_E0 + ROAD_E1 ) / 2, SIDE_N1 ), ( GRID_E[0], -280.0 ), ( GRID_E[1], -280.0 ) ):
            stops = sorted( band for band in n_bands( c ) if band[1] > n0 )
            n_end = CAB_END[s] if c < GRID_E[0] else DASH_END
            n = n0
            for lo, hi in stops + [ ( n_end, n_end ) ]:
                if lo > n:
                    a = s * c
                    dashes( model, a - 3, a + 3, n + 60, min( lo, n_end ) - 60 )
                n = max( n, hi )
                if n >= n_end:
                    break
        for c in ( ( SIDE_N0 + SIDE_N1 ) / 2, STREET_N[0], STREET_N[1], ( LOW_N - 280.0 ) / 2 ):
            a0 = GRID_E[0] + 120.0 if c < 0 else BACK
            stops = sorted( band for band in e_bands( s, c ) if band[1] > a0 )
            a = a0
            for lo, hi in stops + [ ( DASH_END, DASH_END ) ]:
                if lo > a:
                    e0, e1 = sorted( ( s * ( a + 60 ), s * ( min( lo, DASH_END ) - 60 ) ) )
                    dashes( model, e0, e1, c - 3, c + 3, along_n=False )
                a = max( a, hi )
                if a >= DASH_END:
                    break


def skyline():
    """ The rest of the city round the edge rows and north of the side street, its streets and landmarks, and the hills
    round it. Drawn only (no collision, no shadows). """
    model = K.Model()
    blocks = sky_ground( model )
    sky_blocks( model, blocks )
    sky_streets( model )
    return configure( model )


# ---------------------------------------------------------------------------------------------------------------------
# Preview: flat-shaded renders in the scratchpad (railhead_preview's colours, light and fog, a numba z-buffer)

def stand_ins():
    """ The station as boxes, for when railhead_station can't be built. """
    m = K.Model()
    flat( m, "rw_paving", -EDGE, EDGE, PLAY_N0, PLAY_N1, 0.0 )
    for s in ( 1, -1 ):
        lo, hi = sorted( ( s * ROAD_E0, s * ROAD_E1 ) )
        flat( m, "rw_asphalt", lo, hi, -1340.0, PLAY_N1, ROAD_Z + 6.05 )
    m.box( ( -1200, -1340, 0 ), ( 1200, 1300, 700 ), { "default": "rw_sandstone", "+z": "rw_glass_roof" } )
    m.box( ( -1460, 1300, 0 ), ( 1460, 1820, 620 ), { "default": "rw_sandstone", "+z": "slate" } )
    m.box( ( -150, 1600, 0 ), ( 150, 1820, 1100 ), { "default": "rw_sandstone", "+z": "copper" } )
    m.box( ( 2200, -2400, 0 ), ( 2560, LANE_N0, 590 ), "brick" )
    m.box( ( -2560, -2400, 0 ), ( -2200, LANE_N0, 590 ), "brick" )
    return m


def station():
    try:
        import railhead_station as S
        return list( S.build().values() ), "railhead_station"
    except Exception as error:
        print( f"railhead_station didn't build ({error}); using stand-ins" )
        return [ stand_ins() ], "stand-ins"


def prop_shapes( models ):
    """ The props as blobs: a trunk and a crown for a tree, a mound for a bush. """
    m = K.Model()
    for model in models:
        for prop in model.props:
            e, n, z = prop["position"]
            s = prop["scale"]
            if prop["path"] == BUSH:
                lathe( m, ( e, n ), [ ( 72 * s[0], z + 19 * s[2] ), ( 60 * s[0], z + 55 * s[2] ), ( 0.0, z + 75 * s[2] ) ],
                       "pv_leaf", sides=7 )
                continue
            big = prop["path"] == OAK_BIG
            trunk, crown, mid, top = ( 22, 290, 430, 700 ) if big else ( 12, 150, 230, 390 )
            lathe( m, ( e, n ), [ ( trunk * s[0], z ), ( trunk * 0.8 * s[0], z + mid * 0.45 * s[2] ) ], "pv_bark", sides=5 )
            lathe( m, ( e, n ), [ ( crown * 0.3 * s[0], z + mid * 0.35 * s[2] ), ( crown * s[0], z + mid * s[2] ),
                                  ( crown * 0.55 * s[0], z + top * 0.92 * s[2] ), ( 0.0, z + top * s[2] ) ], "pv_leaf",
                   sides=8 )
    return m


def _raster():
    import numba

    @numba.njit
    def raster( image, depth, screen, nearness, colours ):
        height, width = depth.shape
        for t in range( screen.shape[0] ):
            ax, ay = screen[t, 0, 0], screen[t, 0, 1]
            bx, by = screen[t, 1, 0], screen[t, 1, 1]
            cx, cy = screen[t, 2, 0], screen[t, 2, 1]
            area = ( bx - ax ) * ( cy - ay ) - ( by - ay ) * ( cx - ax )
            if abs( area ) < 1e-9:
                continue
            x0 = max( int( math.floor( min( ax, bx, cx ) ) ), 0 )
            x1 = min( int( math.ceil( max( ax, bx, cx ) ) ), width - 1 )
            y0 = max( int( math.floor( min( ay, by, cy ) ) ), 0 )
            y1 = min( int( math.ceil( max( ay, by, cy ) ) ), height - 1 )
            za, zb, zc = nearness[t, 0], nearness[t, 1], nearness[t, 2]
            for y in range( y0, y1 + 1 ):
                py = y + 0.5
                for x in range( x0, x1 + 1 ):
                    px = x + 0.5
                    w0 = ( ( bx - px ) * ( cy - py ) - ( by - py ) * ( cx - px ) ) / area
                    w1 = ( ( cx - px ) * ( ay - py ) - ( cy - py ) * ( ax - px ) ) / area
                    w2 = 1.0 - w0 - w1
                    if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                        z = w0 * za + w1 * zb + w2 * zc
                        if z > depth[y, x]:
                            depth[y, x] = z
                            image[y, x, 0] = colours[t, 0]
                            image[y, x, 1] = colours[t, 1]
                            image[y, x, 2] = colours[t, 2]
    return raster


def render( P, raster, opaque, glass, eye, target, size=( 960, 540 ), fov=80.0, ss=2 ):
    from PIL import Image
    width, height = size[0] * ss, size[1] * ss
    eye, target = np.asarray( eye, float ), np.asarray( target, float )
    forward = K.normalise( target - eye )
    right = K.normalise( np.cross( forward, ( 0.0, 0.0, 1.0 ) ) )
    up = np.cross( right, forward )
    focal = ( width / 2 ) / math.tan( math.radians( fov ) / 2 )
    xs = ( np.arange( width ) + 0.5 - width / 2 ) / focal
    ys = ( height / 2 - np.arange( height ) - 0.5 ) / focal
    rays = forward + xs[None, :, None] * right + ys[:, None, None] * up
    elevation = rays[..., 2] / np.linalg.norm( rays, axis=2 )
    t = np.clip( elevation * 2.5, 0.0, 1.0 )[..., None]
    image = np.ascontiguousarray( P.SKY[0] * ( 1 - t ) + P.SKY[1] * t )
    depth = np.zeros( ( height, width ) )
    s, z, c = P.project( opaque, eye, right, up, forward, focal, width, height )
    raster( image, depth, np.ascontiguousarray( s ), np.ascontiguousarray( z ), np.ascontiguousarray( c ) )
    gimage, gdepth = np.zeros_like( image ), np.zeros_like( depth )
    s, z, c = P.project( glass, eye, right, up, forward, focal, width, height, both_sides=True )
    raster( gimage, gdepth, np.ascontiguousarray( s ), np.ascontiguousarray( z ), np.ascontiguousarray( c ) )
    over = gdepth > depth
    image[over] = image[over] * 0.72 + gimage[over] * 0.28
    picture = Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )
    return picture.resize( size, Image.LANCZOS )


def plan( P, raster, opaque, glass, bounds, scale ):
    from PIL import Image
    e0, e1, n0, n1 = bounds
    width, height = int( ( e1 - e0 ) / scale ), int( ( n1 - n0 ) / scale )
    image = np.tile( np.array( ( 0.12, 0.12, 0.14 ) ), ( height, width, 1 ) )
    depth = np.full( ( height, width ), -1e9 )
    for data in ( opaque, glass ):
        tris, normals, colours = data
        if not len( tris ):
            continue
        keep = ( normals[:, 2] > 0.02 ) & ( tris[:, :, 0].max( axis=1 ) > e0 ) & ( tris[:, :, 0].min( axis=1 ) < e1 ) \
            & ( tris[:, :, 1].max( axis=1 ) > n0 ) & ( tris[:, :, 1].min( axis=1 ) < n1 )
        t = tris[keep]
        screen = np.stack( ( ( t[:, :, 0] - e0 ) / scale, ( n1 - t[:, :, 1] ) / scale ), axis=-1 )
        raster( image, depth, np.ascontiguousarray( screen ), np.ascontiguousarray( t[:, :, 2] ),
                np.ascontiguousarray( colours[keep] ) )
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


# ( name, eye, target, horizontal field of view ), plan inches
VIEWS = [
    ( "cab_east_north", ( 1750, 0, 58 ), ( 1750, 1000, 120 ), 80 ),
    ( "cab_east_south", ( 1750, 0, 58 ), ( 1750, -1000, 40 ), 80 ),
    # The user's screenshot of the Rotunde's view, fitted to the station's arches: 71.5 degrees, 3.3 east of south, 5.3 up
    ( "cab_west_south", ( -1845, 1080, 58 ), ( -1787, 82, 151 ), 71.5 ),
    ( "rotunda_aerial", ( -4500, -3500, 3200 ), ( 0, -9800, 900 ), 60 ),
    ( "cab_east_east", ( 1750, 0, 58 ), ( 2750, 0, 300 ), 80 ),
    ( "cab_east_long", ( 1600, -1250, 58 ), ( 2100, 1800, 200 ), 70 ),
    ( "footbridge_south", ( 0, -280, 294 ), ( 0, -1280, 200 ), 80 ),
    ( "footbridge_north", ( 0, -280, 294 ), ( 0, 720, 400 ), 80 ),
    ( "goods_east_se", ( 1700, -2000, 58 ), ( 2700, -3000, 120 ), 80 ),
    ( "cab_west_north", ( -1750, 0, 58 ), ( -1750, 1000, 120 ), 80 ),
    ( "cab_west_west", ( -1750, 0, 58 ), ( -2750, 0, 300 ), 80 ),
    ( "cab_east_end", ( 1750, 1700, 58 ), ( 1800, 2700, 150 ), 80 ),
    ( "north_corner_nw", ( 1750, 1800, 58 ), ( 900, 2700, 150 ), 80 ),
    ( "throat_south", ( 0, -2300, 30 ), ( 0, -4000, 100 ), 80 ),
    ( "goods_west_sw", ( -1700, -2000, 58 ), ( -2700, -3000, 120 ), 80 ),
    ( "south_high", ( 0, -1500, 1200 ), ( 0, -6000, 300 ), 70 ),
    ( "bridge_deck_south", ( 300, -3150, 380 ), ( 1500, -6500, 300 ), 80 ),
    ( "bridge_deck_west", ( -300, -3150, 380 ), ( -4000, -4200, 200 ), 80 ),
    ( "portal_approach", ( 0, -6200, 30 ), ( 0, -8000, 250 ), 70 ),
    ( "overview", ( 9000, -12000, 6000 ), ( 0, 0, 0 ), 60 ),
    ( "overview_south", ( -6000, -1000, 4000 ), ( 0, -6000, 0 ), 60 ),
    ( "overview_north", ( -7000, 9000, 5000 ), ( 0, 1000, 0 ), 60 ),
    ( "minster_axis", ( 1750, 600, 58 ), ( 1750, 9500, 900 ), 70 ),
    ( "church_axis", ( -1750, 600, 58 ), ( -1750, 6400, 700 ), 70 ),
    ( "roofs_north", ( 0, 1000, 2200 ), ( 0, 9000, 600 ), 80 ),
    ( "roofs_east", ( 2450, 0, 1500 ), ( 9000, 2000, 300 ), 80 ),
    ( "roofs_west", ( -2450, -600, 1500 ), ( -9000, 1500, 300 ), 80 ),
    ( "courtyard_east", ( 2690, 1750, 64 ), ( 3300, 900, 200 ), 90 ),
    ( "courtyard_west", ( -2690, 300, 64 ), ( -3300, -400, 200 ), 90 ),
    ( "seam_se", ( 2600, -2300, 700 ), ( 6000, -2800, 0 ), 80 ),
    ( "city_wide", ( 0, -9000, 14000 ), ( 0, 9000, 0 ), 60 ),
    ( "first_block", ( 2450, -400, 1400 ), ( 3300, -1500, 0 ), 80 ),
    ( "first_block_west", ( -2450, -400, 1400 ), ( -3300, 600, 0 ), 80 ),
]


def preview( out_dir, names=None, station_models=True ):
    import time
    import railhead_preview as P
    out = Path( out_dir )
    out.mkdir( parents=True, exist_ok=True )
    started = time.time()
    built = models()
    print( f"built the backdrop in {time.time() - started:.1f} s" )
    report( built )
    west = edge_blocks( -1 )
    scene = list( built.values() ) + [ west ]
    if station_models:
        stn, source = station()
        print( f"station: {source}" )
        scene += stn
    else:
        scene.append( stand_ins() )
    blobs = prop_shapes( list( built.values() ) + [ west ] )
    P._colours["pv_leaf"] = np.array( ( 0.22, 0.32, 0.14 ) )
    P._colours["pv_bark"] = np.array( ( 0.28, 0.22, 0.16 ) )
    unknown = sorted( { paint for m in scene for paint in m.polygons if np.allclose( P.paint_colour( paint ), ( 1, 0, 1 ) ) } )
    for paint in unknown:
        P._colours[paint] = np.array( ( 0.55, 0.55, 0.52 ) )
    if unknown:
        print( f"no preview colour (drawn grey): {unknown}" )
    scene.append( blobs )
    opaque, glass = P.triangles( scene ), P.triangles( scene, glass=True )
    raster = _raster()
    print( f"{len( opaque[0] )} triangles to draw" )
    for name, eye, target, fov in VIEWS:
        if names and name not in names:
            continue
        started = time.time()
        render( P, raster, opaque, glass, eye, target, fov=fov ).save( out / f"{name}.png" )
        print( f"wrote {name}.png ({time.time() - started:.1f} s)" )
    if not names or "top" in names:
        plan( P, raster, opaque, glass, ( -14000, 14000, -12000, 16000 ), 20 ).save( out / "top_wide.png" )
        plan( P, raster, opaque, glass, ( -3500, 3500, -4500, 4500 ), 6 ).save( out / "top_close.png" )
        print( "wrote top_wide.png, top_close.png" )


def report( built ):
    """ Triangle counts, props, extents, and anything that breaks the play edge's rules. """
    budgets = { "railhead_edge_east": 70000, "railhead_north": 80000, "railhead_south": 80000, "railhead_skyline": 50000 }
    for name, model in built.items():
        lo, hi = model.bounds()
        print( f"{name}: {model.triangle_count()} triangles (budget {budgets.get( name, '-' )}), {len( model.props )} props, "
               f"{len( model.boxes )} boxes, {len( model.hulls )} hulls; e {lo[0]:.0f}..{hi[0]:.0f}, "
               f"n {lo[1]:.0f}..{hi[1]:.0f}, z {lo[2]:.0f}..{hi[2]:.0f}" )
    for name, model in list( built.items() ) + [ ( "railhead_edge_west", edge_blocks( -1 ) ) ]:
        bad = []
        for paint, items in model.polygons.items():
            for points, _ in items:
                for p in points:
                    inside = abs( p[0] ) < EDGE - 0.01 and PLAY_N0 + 0.01 < p[1] < PLAY_N1 - 0.01
                    if not inside:
                        continue
                    if "edge" in name:
                        if ( p[2] <= 120 and abs( p[0] ) < EDGE - 4.01 ) or abs( p[0] ) < EDGE - 30.01:
                            bad.append( ( paint, tuple( np.round( p, 1 ) ) ) )
                    elif p[2] > -40:
                        bad.append( ( paint, tuple( np.round( p, 1 ) ) ) )
        if bad:
            print( f"  {name}: {len( bad )} points break the play edge, e.g. {bad[:4]}" )
    for model in built.values():
        for paint in model.polygons:
            if paint.startswith( "rw_" ) and paint not in model.tile_overrides:
                print( f"  {paint} has no tile override" )
    if _missing_atlas:
        print( f"  atlas rects not found (railhead_materials missing?): {sorted( _missing_atlas )[:6]} ..." )


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--preview" and len( args ) > 1:
        preview( args[1], [ a for a in args[2:] if not a.startswith( "--" ) ] or None, "--stand-ins" not in args )
    else:
        print( __doc__ )
