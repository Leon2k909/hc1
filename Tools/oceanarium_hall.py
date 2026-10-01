"""
The aquarium hall at the heart of hc1's Oceanarium map: my_project's aquarium (Tools/aquarium_core.py reads it) with
what the map changes, written as a few models. Tools/oceanarium_map.py builds the map round it and writes it through
this module.

What changes from my_project's hall:
- The forecourt (Vorplatz) and its planters are left out: the map has its own outside. The airlock's inner doors come
  out, so the entrance is an open doorway 132 wide and 150 high, with the glass kept in the fanlight over it.
- The corridor (Gang) opens into the East Lobby: the last stretch of wall on each side (from e 935 north, 955 south) is
  rebuilt 32 thick with a doorway (68 wide, 112 high) at e 1018. The end wall and its tank stay, with a skin on their
  lobby side.
- The ocean tunnel runs on through the tank to its back wall (118 longer: everything of the tube past s 390 moves on,
  and the stretched pieces keep their textures' scale), with a rib and two lamps added to keep the spacing. Then a
  vestibule takes it to the Kelp Hall's east wall. The two rocks and the corals that stood where the tube now runs are
  gone, the sand is cut round it, and the tank's backdrop has a hole for it.
- Lights outside the doorway are left out.

Coordinates are map_kit's plan ( e east, n north, z up ), and the hall stays at my_project's world coordinates: the touch
pool's water shader works in world space. The tunnel has its own frame: s along it from the rotunda, lat to its right
looking along s.

Its models: oceanarium_hall (the rotunda, corridor, ceilings and the hall's collision), _gallery (the entrance side),
_pool (the touch pool), _ocean (the ocean tank, tunnel and vestibule) and _glow (water, glass, lamps and signs: parts
my_project draws without shadows). Each is an OBJ written with shared vertices, whose materials are the aquarium's own
(Tools/oceanarium_assets.py copies them). Their paints are "core_<part key>", as oceanarium_assets names them.
"""
import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

import aquarium_core as A
import map_kit as K
import oceanarium_assets as OA

RESOURCE_DIR = "models/maps/oceanarium"

# The ocean tunnel's frame.
TUNNEL_START = np.array( ( -332.4, 207.7 ) )
TUNNEL_DIR = K.normalise( ( -0.84805, 0.52992 ) )
TUNNEL_RIGHT = np.array( ( TUNNEL_DIR[1], -TUNNEL_DIR[0] ) )
TUNNEL_CUT = 390.0          # everything of the tube past this moves on by TUNNEL_SHIFT
TUNNEL_SHIFT = 118.0
TUNNEL_END = 520.0          # its new end: the tank's back wall
RIB_COPY = 94.0             # the ribs' spacing: the rib at 303 is copied to 397
LAMP_COPIES = ( 58.0, 116.0 )   # the lamps' spacing: the lamp at 341 is copied to 399 and 457
# The tube's outline seen end on ( lat, z ), its right half: the kerb, then the ribs' outer edge.
TUBE_HOLE = [ ( 82, 0 ), ( 82, 16 ), ( 80, 16 ), ( 80, 60 ), ( 78, 76 ), ( 73, 90 ), ( 66, 104 ), ( 56, 116 ),
              ( 44, 126 ), ( 30, 133 ), ( 15, 138 ), ( 0, 140 ) ]
# The glass's inner face, from where it starts to curve in.
TUBE_GLASS = [ ( 78, 60 ), ( 77, 75 ), ( 72, 90 ), ( 65, 103 ), ( 55, 115 ), ( 43, 125 ), ( 30, 132 ), ( 15, 136 ),
               ( 0, 138 ) ]

# The vestibule from the tank's back wall to the Kelp Hall.
BACK_WALL = 8.0             # the tank's back wall: s 520..528
VESTIBULE_HALF = 96.0       # half its width inside
VESTIBULE_SIDE = 16.0
VESTIBULE_HEIGHT = 160.0
VESTIBULE_ROOF = 16.0
KELP_EAST = -960.0          # the Kelp Hall's east wall's outer face (e), where the vestibule ends
MOUTH_RETURN = 16.0         # how far the Kelp Hall's wall comes in past the vestibule's sides, each side

# The corridor's end.
CORRIDOR_SIDE = ( 120.0, 152.0 )    # its rebuilt walls' n (north; the south one mirrors it)
CORRIDOR_FROM = { 1: 935.0, -1: 955.0 }   # where they start (e), north and south: the reef tank's window ends at 955
CORRIDOR_EAST = 1092.0      # the outer face of the end wall's skin
CORRIDOR_DOOR = ( 1018.0, 68.0, 112.0 )   # centre (e), width and height of the doorway on each side
LOBBY_HEIGHT = 288.0        # the East Lobby's ceiling, which the corridor's outside walls reach
LOBBY_PAINT = "core_limestone"

# Outside the doorway (plan n): colliders wholly beyond the facade, and lights beyond the forecourt's edge, go.
FACADE_N = -541.0
LIGHTS_FROM_N = -560.0

GLOW_GROUP = "glow"


# ---------------------------------------------------------------------------------------------------------------------
# Pieces

@dataclass
class Piece:
    """ One of the hall's polygons in plan coordinates, counter-clockwise seen from its front (map_kit's rule). """
    group: str
    part: str
    points: np.ndarray      # ( n, 3 )
    normals: np.ndarray     # ( n, 3 ) one per corner
    uvs: np.ndarray         # ( n, 2 ), v down the picture, as my_project has them


def plan_of( p ):
    """ World ( x north, y west, z ) to plan ( e, n, z ), for any array of points or vectors. """
    p = np.asarray( p, float )
    return np.stack( ( -p[..., 1], p[..., 0], p[..., 2] ), -1 )


def world_of( p ):
    p = np.asarray( p, float )
    return np.stack( ( p[..., 1], -p[..., 0], p[..., 2] ), -1 )


def tunnel_local( p ):
    """ Plan points to the tunnel's ( s, lat, z ). """
    p = np.asarray( p, float )
    q = p[..., :2] - TUNNEL_START
    return np.stack( ( q @ TUNNEL_DIR, q @ TUNNEL_RIGHT, p[..., 2] ), -1 )


def tunnel_plan( l ):
    l = np.asarray( l, float )
    flat = TUNNEL_START + l[..., :1] * TUNNEL_DIR + l[..., 1:2] * TUNNEL_RIGHT
    return np.concatenate( ( flat, l[..., 2:3] ), -1 )


def tunnel_axes():
    """ The tunnel frame as right-handed box axes: x along it, y to its left, z up. """
    x = np.array( ( *TUNNEL_DIR, 0.0 ) )
    return ( x, np.array( ( -TUNNEL_DIR[1], TUNNEL_DIR[0], 0.0 ) ), np.array( ( 0.0, 0.0, 1.0 ) ) )


def newell( points ):
    a = points[1:-1] - points[0]
    b = points[2:] - points[0]
    return np.cross( a, b ).sum( axis=0 )


def make_piece( group, part, points, normals, uvs, facing=None ):
    """ A piece wound to face its normals (or facing), or None if it has no area. """
    points = np.asarray( points, float )
    if len( points ) < 3:
        return None
    area = newell( points )
    if np.linalg.norm( area ) < 1e-6:
        return None
    facing = np.asarray( normals, float ).mean( axis=0 ) if facing is None else np.asarray( facing, float )
    if np.dot( area, facing ) < 0:
        order = [ 0 ] + list( range( len( points ) - 1, 0, -1 ) )
        points, normals, uvs = points[order], np.asarray( normals )[order], np.asarray( uvs )[order]
    return Piece( group, part, points, np.asarray( normals, float ), np.asarray( uvs, float ) )


def moved( piece, points, uvs=None, group=None ):
    return Piece( group or piece.group, piece.part, np.asarray( points, float ), piece.normals,
                  piece.uvs if uvs is None else uvs )


def clip( piece, f ):
    """ The piece cut to where f ( a linear function of plan points ) is at least 0, or None. """
    values = f( piece.points )
    if ( values >= -1e-9 ).all():
        return piece
    if ( values <= 1e-9 ).all():
        return None
    pts, nrm, uvs = [], [], []
    count = len( values )
    for i in range( count ):
        j = ( i + 1 ) % count
        a, b = values[i], values[j]
        if a >= 0:
            pts.append( piece.points[i] ), nrm.append( piece.normals[i] ), uvs.append( piece.uvs[i] )
        if ( a >= 0 ) != ( b >= 0 ):
            t = a / ( a - b )
            pts.append( piece.points[i] + t * ( piece.points[j] - piece.points[i] ) )
            nrm.append( piece.normals[i] + t * ( piece.normals[j] - piece.normals[i] ) )
            uvs.append( piece.uvs[i] + t * ( piece.uvs[j] - piece.uvs[i] ) )
    keep = [ k for k in range( len( pts ) ) if np.linalg.norm( pts[k] - pts[k - 1] ) > 1e-6 ]
    if len( keep ) < 3:
        return None
    return Piece( piece.group, piece.part, np.array( [ pts[k] for k in keep ] ), np.array( [ nrm[k] for k in keep ] ),
                  np.array( [ uvs[k] for k in keep ] ) )


def affine_uvs( source_points, source_uvs, points ):
    """ UVs for points, from the affine map that best fits source_points to source_uvs. """
    a = np.column_stack( ( source_points, np.ones( len( source_points ) ) ) )
    m, *_ = np.linalg.lstsq( a, source_uvs, rcond=None )
    return np.column_stack( ( points, np.ones( len( points ) ) ) ) @ m


def kit_model( parts ):
    """ A map_kit model that knows the core paints' materials and tiles. """
    model = K.Model()
    for paint, ( material, tile ) in OA.core_paints( parts ).items():
        model.material_overrides[paint] = material
        model.tile_overrides[paint] = tile
    return model


def pieces_of( model, group ):
    """ A map_kit model's polygons as pieces, with its world-scale UVs (turned to v down). """
    out = []
    offset = K.uv_offset( group )
    for paint, items in model.polygons.items():
        part = paint[len( "core_" ):]
        for index, ( points, normal ) in enumerate( items ):
            wn = K.to_world( normal )
            uvs = model.polygon_uvs.get( ( paint, index ) ) or [
                K.face_uv( K.to_world( p ), wn, paint, offset, model.tile_overrides.get( paint ) ) for p in points ]
            uvs = np.array( [ ( u, -v ) for u, v in uvs ] )
            out.append( Piece( group, part, np.array( points ), np.tile( normal, ( len( points ), 1 ) ), uvs ) )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The hall

class Hall:
    """ The edited hall: pieces, the collision (a map_kit model's boxes and hulls), lights and spots in plan. """

    def __init__( self ):
        source = A.read()
        self.parts = source.parts
        self.ambient, self.exposure = source.ambient, source.exposure
        self.pieces = []
        for p in source.polys:
            if p.group == "Vorplatz":
                continue
            piece = make_piece( p.group, p.part, plan_of( p.points ), plan_of( p.normals ), p.uvs.copy() )
            if piece is not None:
                self.pieces.append( piece )
        self.collision = K.Model()
        for c in source.colliders:
            self.add_collider( c )
        self.lights = [ ( plan_of( pos ), radius, colour ) for pos, radius, colour in source.lights
                        if plan_of( pos )[1] >= LIGHTS_FROM_N ]
        self.spots = [ ( plan_of( s[0] ), *s[1:] ) for s in source.spots if plan_of( s[0] )[1] >= LIGHTS_FROM_N ]
        self.open_doorway()
        self.open_corridor()
        self.extend_tunnel()
        self.build_vestibule()

    # Collision -------------------------------------------------------------------------------------------------------

    SURFACES = {
        "Glasbecken": "glass", "Panoramaglas": "glass", "Tunnelglas": "glass",
        "Runde Pflanzenbank": "wood", "Besucherbank": "wood", "Deko-Fass": "wood", "Empfangstresen Holz": "wood",
        "Wegweiser Holz": "wood", "Souvenirregal": "wood",
        "Infosäule Metall": "metal", "Absperrpfosten Metall": "metal", "Wartesitze": "metal",
        "Reinigungswagen": "metal", "Snackautomat": "metal", "Schließfächer Metall": "metal",
        "Wegweiser Schilder": "metal", "Prospektständer": "metal",
        "Wasserspender": "plastic", "Warnschild": "plastic",
    }
    DROPPED = { "Steinboden", "Eingangstür Glas" }  # the map lays its own floor; the doors come out

    def add_collider( self, c ):
        """ my_project's box collider in the collision, with its material's surface (stone is "default", as all the
        maps' masonry is), unless it's dropped or wholly outside the facade. """
        if c.name in self.DROPPED:
            return
        corners = plan_of( A.collider_corners( c ) )
        if corners[:, 1].max() < FACADE_N:
            return
        a = math.radians( c.yaw )
        axes = ( ( -math.sin( a ), math.cos( a ), 0.0 ), ( -math.cos( a ), -math.sin( a ), 0.0 ), ( 0.0, 0.0, 1.0 ) )
        surface = self.SURFACES.get( c.name, "default" )
        self.collision.boxes.append( ( plan_of( c.centre ), axes, 2 * c.half, surface, c.name ) )

    def replace_box( self, name, near, lo=None, hi=None ):
        """ Takes out the collider called name whose centre is within 2 of near (plan e, n); with lo and hi, puts an
        axis-aligned box there instead, with its surface. """
        for i, box in enumerate( self.collision.boxes ):
            if len( box ) == 5 and box[4] == name and np.linalg.norm( np.asarray( box[0][:2] ) - near ) < 2.0:
                del self.collision.boxes[i]
                if lo is not None:
                    self.collision.collision_box( lo, hi, box[3] )
                return
        raise KeyError( ( name, near ) )

    def collision_model( self ):
        """ The collision as a map_kit model (its boxes without the names). """
        model = K.Model()
        model.boxes = [ b[:4] for b in self.collision.boxes ]
        model.hulls = list( self.collision.hulls )
        return model

    # The entrance ----------------------------------------------------------------------------------------------------

    def open_doorway( self ):
        """ The airlock's inner doors come out: their leaves, handles and sill. The glass stays in the fanlight. """
        out = []
        for piece in self.pieces:
            if piece.group == "Windfang":
                p = piece.points
                in_line = p[:, 1].min() >= -541.0 and p[:, 1].max() <= -534.0
                if in_line and piece.part in ( "metal", "steel" ):
                    leaf = np.abs( p[:, 0] ).max() <= 66.5 and p[:, 2].min() < 150.0
                    sill = np.abs( p[:, 0] ).max() <= 70.5 and p[:, 2].max() <= 1.01
                    if leaf or sill:
                        continue
                if in_line and piece.part == "glass" and p[:, 2].min() < 1.0 and p[:, 2].max() > 150.0:
                    piece = clip( clip( piece, lambda q: q[:, 2] - 154.0 ), lambda q: 172.0 - q[:, 2] )
                    if piece is None:
                        continue
            out.append( piece )
        self.pieces = out
        self.collision.collision_box( ( -70, -540, 150 ), ( 70, -537, 175 ), "metal" )   # the transom and fanlight

    # The corridor's end ------------------------------------------------------------------------------------------------

    def open_corridor( self ):
        n0, n1 = CORRIDOR_SIDE
        self.pieces = [ p for p in self.pieces
                        if not ( p.group == "Gang" and p.part in ( "navy", "stone_dark" ) and p.points[:, 0].min() >= 930.0
                                 and np.allclose( np.abs( p.points[:, 1] ), 120.0, atol=0.6 ) ) ]
        self.replace_box( "Wand Stein", ( 729.0, 128.0 ), ( 382, 120, 0 ), ( CORRIDOR_FROM[1], 136, 250 ) )
        self.replace_box( "Wand Stein", ( 729.0, -128.0 ), ( 382, -136, 0 ), ( CORRIDOR_FROM[-1], -120, 250 ) )
        model = kit_model( self.parts )
        centre, width, height = CORRIDOR_DOOR
        for side in ( 1, -1 ):
            across = ( side * n0, side * n1 )
            outward = "+n" if side > 0 else "-n"
            run = ( CORRIDOR_FROM[side], CORRIDOR_EAST )
            for z, inside in ( ( ( 0.0, 10.0 ), "core_stone_dark" ), ( ( 10.0, LOBBY_HEIGHT ), "core_navy" ) ):
                wall = K.Wall( "e", run, across, z, outward )
                wall.add( centre, width, 0.0, height, "door" )
                wall.build( model, LOBBY_PAINT, inside, "core_limestone", end=None, surface="default" )
        # The end wall's skin on the lobby side, and the corridor's roof (its ceiling is at 250).
        model.box( ( 1076, -n0, 0 ), ( CORRIDOR_EAST, n0, LOBBY_HEIGHT ), { "+e": LOBBY_PAINT }, "default" )
        model.collision_box( ( 382, -n1, 250 ), ( CORRIDOR_EAST, n1, 360 ), "default" )
        self.add_model( model, "Gang" )

    def add_model( self, model, group ):
        self.pieces.extend( pieces_of( model, group ) )
        self.collision.boxes.extend( model.boxes )
        self.collision.hulls.extend( model.hulls )

    # The tunnel ------------------------------------------------------------------------------------------------------

    def extend_tunnel( self ):
        out = []
        rib, lamps = [], []
        for piece in self.pieces:
            if piece.group not in ( "Tunnel", "Tunnelglas" ):
                out.append( piece )
                continue
            local = tunnel_local( piece.points )
            s0, s1 = local[:, 0].min(), local[:, 0].max()
            if piece.group == "Tunnelglas" and s0 >= 399.0:
                continue                    # the old end pane
            if piece.part in ( "stone_dark", "led" ) and s0 >= 393.0:
                continue                    # the kerb across the old end, and its light strip
            if piece.part == "metal" and s0 >= 302.5 and s1 <= 308.5:
                rib.append( piece )
            if piece.part in ( "metal", "led" ) and s0 >= 340.0 and s1 <= 353.5:
                lamps.append( piece )
            shift = local[:, 0] >= TUNNEL_CUT
            if not shift.any():
                out.append( piece )
                continue
            new = local.copy()
            new[shift, 0] += TUNNEL_SHIFT
            uvs = piece.uvs if shift.all() else affine_uvs( local, piece.uvs, new )
            out.append( moved( piece, tunnel_plan( new ), uvs ) )
        assert len( rib ) == 72 and len( lamps ) == 4, ( len( rib ), len( lamps ) )
        for piece in rib:
            out.append( moved( piece, piece.points + RIB_COPY * np.array( ( *TUNNEL_DIR, 0.0 ) ) ) )
        for step in LAMP_COPIES:
            for piece in lamps:
                out.append( moved( piece, piece.points + step * np.array( ( *TUNNEL_DIR, 0.0 ) ) ) )
        self.pieces = out

        # The kerbs' new ends, where the cross kerb was: inner face, top and end, each side.
        end = TUNNEL_END
        start = TUNNEL_CUT + 4.0 + TUNNEL_SHIFT     # the inner faces ran to 394
        model = kit_model( self.parts )
        for side in ( 1, -1 ):
            inner, outer = side * 72.0, side * 82.0
            middle = np.array( ( *( -side * TUNNEL_RIGHT ), 0.0 ) )
            for quad, towards in (
                    ( [ ( start, inner, 0 ), ( end, inner, 0 ), ( end, inner, 16 ), ( start, inner, 16 ) ], middle ),
                    ( [ ( start, inner, 16 ), ( end, inner, 16 ), ( end, outer, 16 ), ( start, outer, 16 ) ],
                      np.array( ( 0.0, 0.0, 1.0 ) ) ),
                    ( [ ( end, inner, 0 ), ( end, outer, 0 ), ( end, outer, 16 ), ( end, inner, 16 ) ],
                      np.array( ( *TUNNEL_DIR, 0.0 ) ) ) ):
                self._facing( model, "core_stone_dark", tunnel_plan( np.array( quad, float ) ), towards )
        self.add_model( model, "Tunnel" )

        # Its collision: the glass along the whole length (the boxes stood to 402, with a pane across the end), and the
        # arch of the glass overhead, so nothing thrown leaves through the top.
        self.collision.boxes = [ b for b in self.collision.boxes if not ( len( b ) == 5 and b[4] == "Tunnelglas" ) ]
        axes = tunnel_axes()
        for side in ( 1, -1 ):
            centre = tunnel_plan( np.array( ( TUNNEL_END / 2, side * 78.0, 70.0 ) ) )
            self.collision.boxes.append( ( centre, axes, np.array( ( TUNNEL_END, 12.0, 140.0 ) ), "glass", "Tunnelglas" ) )
            for ( la, za ), ( lb, zb ) in zip( TUBE_GLASS, TUBE_GLASS[1:] ):
                d = np.array( ( lb - la, zb - za ), float )
                out_dir = K.normalise( ( d[1], -d[0] ) ) * 4.0      # away from the tube's axis
                ring = [ ( la, za ), ( lb, zb ), ( lb + out_dir[0], zb + out_dir[1] ), ( la + out_dir[0], za + out_dir[1] ) ]
                points = [ ( s, side * l, z ) for s in ( 0.0, TUNNEL_END ) for l, z in ring ]
                self.collision.hull( tunnel_plan( np.array( points ) ), "glass" )

        # The tank round the extended tube.
        self.cut_sand()
        self.clear_tube()
        self.backdrop_hole()
        self.lights = [ ( tunnel_plan( tunnel_local( pos ) + ( TUNNEL_SHIFT, 0, 0 ) )
                          if TUNNEL_CUT <= tunnel_local( pos )[0] <= 410.0 and abs( tunnel_local( pos )[1] ) < 100.0
                          and pos[2] < 150.0 else pos, radius, colour ) for pos, radius, colour in self.lights ]
        self.lights.append( ( tunnel_plan( np.array( ( 450.0, 0.0, 112.0 ) ) ), 230.0, ( 0.3, 0.62, 1.0 ) ) )

    def cut_sand( self ):
        """ The sand cut round the tube, where it now runs. """
        cut, edge = TUNNEL_CUT, 82.0
        s = lambda q: tunnel_local( q )[:, 0]
        lat = lambda q: tunnel_local( q )[:, 1]
        out = []
        for piece in self.pieces:
            if piece.part != "sand":
                out.append( piece )
                continue
            for keep in ( [ lambda q: cut - s( q ) ],
                          [ lambda q: s( q ) - cut, lambda q: lat( q ) - edge ],
                          [ lambda q: s( q ) - cut, lambda q: -edge - lat( q ) ] ):
                part = piece
                for f in keep:
                    part = clip( part, f ) if part is not None else None
                if part is not None:
                    out.append( part )
        self.pieces = out

    def clear_tube( self ):
        """ Takes out the rocks and corals with any corner where the tube now runs (each a whole connected piece). """
        def inside( points ):
            s, lat, z = tunnel_local( points ).T
            arch = np.where( z <= 60.0, np.abs( lat ) < 92.0, ( lat / 92.0 ) ** 2 + ( ( z - 60.0 ) / 88.0 ) ** 2 < 1.0 )
            return ( s > TUNNEL_CUT ) & ( s < TUNNEL_END + 10.0 ) & ( z < 150.0 ) & arch

        candidates = [ i for i, p in enumerate( self.pieces )
                       if p.group == "Ozeanbecken" and p.part in ( "rock_sea", "coral" ) ]
        parent = { i: i for i in candidates }

        def find( i ):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        owner = {}
        for i in candidates:
            for v in np.round( self.pieces[i].points, 2 ):
                key = ( self.pieces[i].part, *v )
                if key in owner:
                    parent[find( i )] = find( owner[key] )
                else:
                    owner[key] = i
        groups = defaultdict( list )
        for i in candidates:
            groups[find( i )].append( i )
        drop = set()
        for members in groups.values():
            if any( inside( self.pieces[i].points ).any() for i in members ):
                assert len( members ) < 400, len( members )    # only small rocks and corals are in the way
                drop.update( members )
        self.cleared = len( drop )
        self.pieces = [ p for i, p in enumerate( self.pieces ) if i not in drop ]

    def backdrop_hole( self ):
        """ The tank's back wall (its painted ocean, at s 520) in bands round a hole for the tube. """
        index = [ i for i, p in enumerate( self.pieces ) if p.part == "ocean"
                  and np.allclose( tunnel_local( p.points )[:, 0], TUNNEL_END, atol=1.0 ) ]
        assert len( index ) == 1, index
        source = self.pieces.pop( index[0] )
        local = tunnel_local( source.points )
        half = np.abs( local[:, 1] ).max()
        z0, z1 = local[:, 2].min(), local[:, 2].max()
        facing = -np.array( ( *TUNNEL_DIR, 0.0 ) )
        profile = [ ( l, max( z, z0 ) ) for l, z in TUBE_HOLE ]
        quads = []
        for side in ( 1, -1 ):
            for ( la, za ), ( lb, zb ) in zip( profile, profile[1:] ):
                if zb - za > 1e-6:
                    quads.append( [ ( side * la, za ), ( side * half, za ), ( side * half, zb ), ( side * lb, zb ) ] )
        top = profile[-1][1]
        quads.append( [ ( -half, top ), ( half, top ), ( half, z1 ), ( -half, z1 ) ] )
        for quad in quads:
            points = tunnel_plan( np.array( [ ( TUNNEL_END, l, z ) for l, z in quad ] ) )
            uvs = affine_uvs( local[:, 1:], source.uvs, np.array( quad, float ) )
            piece = make_piece( source.group, source.part, points, np.tile( facing, ( 4, 1 ) ), uvs, facing )
            if piece is not None:
                self.pieces.append( piece )

    # The vestibule ---------------------------------------------------------------------------------------------------

    @staticmethod
    def kelp_s( lat ):
        """ The s where the Kelp Hall's east wall crosses the line lat. """
        return ( KELP_EAST - TUNNEL_START[0] - lat * TUNNEL_RIGHT[0] ) / TUNNEL_DIR[0]

    def mouth( self ):
        """ The doorway the vestibule needs in the Kelp Hall's east wall: plan n from, to, and its height. """
        n = [ tunnel_plan( np.array( ( self.kelp_s( l ), l, 0.0 ) ) )[1] for l in ( -VESTIBULE_HALF, VESTIBULE_HALF ) ]
        return ( min( n ) + MOUTH_RETURN, max( n ) - MOUTH_RETURN, VESTIBULE_HEIGHT )

    def build_vestibule( self ):
        model = kit_model( self.parts )
        s0, s1 = TUNNEL_END, TUNNEL_END + BACK_WALL
        half, side_w, height = VESTIBULE_HALF, VESTIBULE_SIDE, VESTIBULE_HEIGHT
        along = np.array( ( *TUNNEL_DIR, 0.0 ) )

        def at( s, lat, z ):
            return tunnel_plan( np.array( ( s, lat, z ), float ) )

        # The back wall's face into the vestibule, the hole's sides, and its collision, in bands round the hole.
        for side in ( 1, -1 ):
            for ( la, za ), ( lb, zb ) in zip( TUBE_HOLE, TUBE_HOLE[1:] ):
                if zb - za > 1e-6:
                    band = [ ( side * la, za ), ( side * half, za ), ( side * half, zb ), ( side * lb, zb ) ]
                    face = [ at( s1, l, z ) for l, z in band ]
                    self._facing( model, "core_navy", face, along )
                    model.hull( [ at( s, l, z ) for s in ( s0, s1 ) for l, z in band ], "default" )
                reveal = [ at( s0, side * la, za ), at( s1, side * la, za ), at( s1, side * lb, zb ), at( s0, side * lb, zb ) ]
                inward = np.array( ( *( -side * TUNNEL_RIGHT * ( la + lb ) / 2 ), -( za + zb ) / 2 + 70.0 ) )
                self._facing( model, "core_navy", reveal, inward )
        top = TUBE_HOLE[-1][1]
        band =[ at( s1, -half, top ), at( s1, half, top ), at( s1, half, height ), at( s1, -half, height ) ]
        self._facing( model, "core_navy", band, along )
        model.hull( [ at( s, l, z ) for s in ( s0, s1 ) for l in ( -half, half ) for z in ( top, height + VESTIBULE_ROOF ) ],
                    "default" )

        # Its sides (skirting, then wall), floor and ceiling, up to the Kelp Hall's wall.
        def outline( l0, l1, s_start ):
            return [ tunnel_plan( np.array( ( s, l, 0.0 ) ) )[:2] for s, l in
                     ( ( s_start, l0 ), ( self.kelp_s( l0 ), l0 ), ( self.kelp_s( l1 ), l1 ), ( s_start, l1 ) ) ]

        def ccw( points ):
            pts = [ np.asarray( p, float ) for p in points ]
            area = sum( a[0] * b[1] - b[0] * a[1] for a, b in zip( pts, pts[1:] + pts[:1] ) )
            return pts if area > 0 else pts[::-1]

        for side in ( 1, -1 ):
            wall = ccw( outline( side * half, side * ( half + side_w ), s1 ) )
            model.prism( wall, 0.0, 10.0, { "side": "core_stone_dark" }, "default" )
            model.prism( wall, 10.0, height + VESTIBULE_ROOF, { "side": "core_navy" }, "default" )
        inside = ccw( outline( -half, half, s0 ) )
        model.polygon( "core_floor_tunnel", [ ( *p, 0.0 ) for p in inside ], ( 0, 0, 1 ) )
        roof = ccw( outline( -half - side_w, half + side_w, s1 ) )
        model.prism( roof, height, height + VESTIBULE_ROOF, { "bottom": "core_ceiling" }, "default" )
        self.add_model( model, "Tunnel" )
        mid = ( s1 + self.kelp_s( 0.0 ) ) / 2
        self.lights.append( ( at( mid, 0.0, 140.0 ), 300.0, ( 0.55, 0.75, 1.0 ) ) )

    @staticmethod
    def _facing( model, paint, points, towards ):
        points = [ np.asarray( p, float ) for p in points ]
        normal = newell( np.array( points ) )
        if np.linalg.norm( normal ) < 1e-6:
            return
        if np.dot( normal, towards ) < 0:
            points = points[:1] + points[:0:-1]
        model.polygon( paint, points )

    # Writing ---------------------------------------------------------------------------------------------------------

    CHUNKS = {
        "oceanarium_gallery": ( "Galerie", "Eingang", "Windfang", "Empfang", "Schließfächer" ),
        "oceanarium_pool": ( "Streichelbecken", ),
        "oceanarium_ocean": ( "Ozeanbecken", "Tunnel", "Tunnelglas" ),
    }
    MAIN = "oceanarium_hall"
    GLOW = "oceanarium_glow"

    def chunk_of( self, piece ):
        if not self.parts[piece.part].shadows:
            return self.GLOW
        for name, groups in self.CHUNKS.items():
            if piece.group in groups:
                return name
        return self.MAIN

    def write( self, out_dir ):
        """ The hall's models. Returns [ ( model name, casts shadows, has the collision, triangles ) ]. """
        chunks = defaultdict( list )
        for piece in self.pieces:
            chunks[self.chunk_of( piece )].append( piece )
        materials = OA.core_paints( self.parts )
        written = []
        for name in sorted( chunks ):
            triangles = write_pieces( out_dir / f"{name}.obj", chunks[name], name )
            stand_in = K.Model()
            for paint in sorted( { OA.paint( p.part ) for p in chunks[name] } ):
                stand_in.polygons[paint] = []
                stand_in.material_overrides[paint] = materials[paint][0]
            collide = name == self.MAIN
            if collide:
                stand_in.boxes = self.collision_model().boxes
                stand_in.hulls = self.collision_model().hulls
            old_hulls = set( out_dir.glob( f"{name}_hulls_*.obj" ) )
            hulls = K.write_vmdl( out_dir / f"{name}.vmdl", RESOURCE_DIR, name, stand_in )
            for stale in old_hulls - hulls:
                stale.unlink()
                stale.with_name( f"{stale.name}.meta" ).unlink( missing_ok=True )
            written.append( ( name, name != self.GLOW, collide, triangles ) )
        return written


def write_pieces( path, pieces, name ):
    """ An OBJ with shared vertices, normals and UVs (the hall is too big to repeat them per polygon), and its .mtl.
    Returns the triangle count. """
    path.parent.mkdir( parents=True, exist_ok=True )
    index = [ {}, {}, {} ]
    lists = [ [], [], [] ]
    faces = defaultdict( list )

    def ref( kind, key, text ):
        found = index[kind].get( key )
        if found is None:
            found = index[kind][key] = len( lists[kind] ) + 1
            lists[kind].append( text )
        return found

    for piece in pieces:
        world = world_of( piece.points )
        normals = world_of( piece.normals )
        normals = normals / np.maximum( np.linalg.norm( normals, axis=1 ), 1e-9 )[:, None]
        corners = []
        for p, n, ( u, v ) in zip( world, normals, piece.uvs ):
            pv = ( round( p[1], 3 ), round( p[2], 3 ), round( p[0], 3 ) )
            nv = ( round( n[1], 4 ), round( n[2], 4 ), round( n[0], 4 ) )
            tv = ( round( float( u ), 5 ), round( 1.0 - float( v ), 5 ) )
            corners.append( ( ref( 0, pv, "v {:.3f} {:.3f} {:.3f}".format( *pv ) ),
                              ref( 1, tv, "vt {:.5f} {:.5f}".format( *tv ) ),
                              ref( 2, nv, "vn {:.4f} {:.4f} {:.4f}".format( *nv ) ) ) )
        for k in range( 1, len( corners ) - 1 ):
            faces[OA.paint( piece.part )].append( "f " + " ".join( f"{a}/{b}/{c}" for a, b, c in
                                                                    ( corners[0], corners[k], corners[k + 1] ) ) )
    lines = [ "# Tools/oceanarium_hall.py", f"mtllib {path.stem}.mtl", f"o {path.stem}" ] + lists[0] + lists[1] + lists[2]
    for paint in sorted( faces ):
        lines.append( f"usemtl {paint}" )
        lines.extend( faces[paint] )
    K.write_text( path, "\n".join( lines ) + "\n" )
    K.write_text( path.with_suffix( ".mtl" ), "".join( f"newmtl {paint}\nKd 1 1 1\nd 1\n" for paint in sorted( faces ) ) )
    return sum( len( f ) for f in faces.values() )
