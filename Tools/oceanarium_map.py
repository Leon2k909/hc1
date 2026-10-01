"""
Oceanarium, a multiplayer map: my_project's aquarium hall (Tools/oceanarium_hall.py) in the middle of a bigger building,
built round it by script out of boxes and polygons with Tools/map_kit.py, the way Belltower is (Tools/belltower_map.py
lends its props, its checks and its pictures). Collision is the same boxes, so what you see is what stops players, bots
and bullets.

    python Tools/oceanarium_map.py [--preview <dir>] [--no-scene]

The user asked for a big map for 10-12 players, built out from my_project's aquarium, with many rooms, each with
several ways out, and a few headglitch spots: cover a player can just see and shoot over, 50-54 high against an eye at
64.

The building (e -1474..1474, n -580..1474) stands between the spawn yards: Red Team (Team.Terrorist) west, Blue Team
(Team.CounterTerrorist) east. Three lanes join them:

- North, the back of house: five rooms in a row with two doors between each, staggered so no line runs through all of
  them. The Stores, the Filter Hall (a catwalk along its back wall), the Labs (rows of benches), the Pump Room (bomb site
  A, with a raised platform) and the Workshop.
- Middle: the Kelp Hall (a raised gallery along its west wall, and a kelp tank), the aquarium's ocean tunnel through to
  its rotunda, the corridor, and the East Lobby, which wraps round the corridor's end.
- South: the Gift Shop, the Cloakroom, the Ticket Hall and the Café along the front. Outside them are the forecourt with
  its fountain, the West Court, the East Garden with its raised terrace (bomb site B), and the promenade along the sea.

The Reef Hall (a raised walkway and an octagonal tank) joins the lobby to the Pump Room and the Workshop.

Headglitch spots:
- the parapets of the Kelp Hall's gallery, the Reef Hall's walkway, the Filter Hall's catwalk and the Pump Room's
  platform;
- the counters (Gift Shop, Cloakroom, Ticket Hall, Café, the lobby's desk), the lab benches and the display cases;
- the planters, the crates, the cars, the hedges and the terrace's walls.

- Writes the hall's models (oceanarium_hall.py's) and its own to Assets/models/maps/oceanarium/:
  - oceanarium_rooms: the building round the hall, with its collision;
  - oceanarium_outside: the yards, the courts, the garden and the promenade;
  - their _glow halves: lamps, water surfaces and glass, which cast no shadows;
  - oceanarium_vista: the sea and the town round the site, with no collision and no shadows.
  It also writes the scene, Assets/scenes/maps/Oceanarium/oceanarium.scene, whole on every run (edit the layout here,
  not in the editor), and the radar picture, Assets/ui/minimaps/minimap_oceanarium.png.
- Every run checks every spawn, objective and cash point: room for a player and a floor under it (Belltower's
  check_spots), and a way to walk there from Red Team's spawn (check_reach, a 2.5D grid that stands in for the navmesh).
  It prints what's wrong.
- Plan coordinates are map_kit's ( e east, n north, z up ). The hall keeps my_project's coordinates, with the rotunda's
  middle at 0, 0.
- Walls are 16 thick inside and 24 outside, doorways 96 wide and 120 high (the loading doors 160 by 144), stairs 8 up.
  Every room has a ceiling (240-320), and over everything is the roof at 344..360, which nothing reaches.
- --preview writes a top-down picture, views from head height and reach.png to <dir>, flat-shaded in the paints' mean
  colours, for checking without the editor. If Assets/ui/maps/oceanarium.png (the menus' picture) doesn't exist, it
  writes the aerial view there as a stand-in.
"""
import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

import aquarium_core as A
import belltower_detail as Detail
import belltower_map as BM
import building_textures as BT
import map_kit as K
import oceanarium_assets as OA
import oceanarium_hall as H
from map_kit import Model, Wall

TITLE = "Oceanarium"
OUT_DIR = K.ASSETS / "models" / "maps" / "oceanarium"
RESOURCE_DIR = H.RESOURCE_DIR
SCENE_FILE = K.ASSETS / "scenes" / "maps" / "Oceanarium" / "oceanarium.scene"
MINIMAP_FILE = K.ASSETS / "ui" / "minimaps" / "minimap_oceanarium.png"
MINIMAP_PATH = "ui/minimaps/minimap_oceanarium.png"
MAP_ART_FILE = K.ASSETS / "ui" / "maps" / "oceanarium.png"
MAP_ART_PATH = "ui/maps/oceanarium.png"
ids = K.SceneIds( "5b0b19c7-c8d7-4389-817f-ec9fde48c94d" )

STONE, WOOD, TILE, METAL, SHEET, FABRIC, DIRT, GRASS, GLASS, WATER = (
    BM.STONE, BM.WOOD, BM.TILE, BM.METAL, BM.SHEET, BM.FABRIC, BM.DIRT, BM.GRASS, BM.GLASS, BM.WATER )

C = OA.paint        # an aquarium part's paint: C( "navy" ) is "core_navy"
DARK = C( "stone_dark" )

WARM = "1,0.86,0.66,1"
COOL = "0.85,0.92,1,1"
BLUE = "0.55,0.75,1,1"

# ---------------------------------------------------------------------------------------------------------------------
# Layout (plan inches)

OUTER = ( -1474.0, 1474.0, -580.0, 1474.0 )     # the building's outer faces: e0, e1, n0, n1
SITE = ( -2024.0, 2024.0, -1224.0, 1474.0 )     # the map, to its walls' outer faces and the sea wall
YARD = ( 1474.0, 2000.0 )                       # the east spawn yard (e); the west one mirrors it
COURT = ( -1100.0, -580.0 )                     # the forecourt, the West Court and the East Garden (n)
PROMENADE = ( -1200.0, -1100.0 )
SEA_WALL = -1224.0
WALL_TOP = 344.0        # the inner walls, and the rooms' ceilings' collision, reach the roof
ROOF_TOP = 360.0
SKIRTING = 12.0
DOOR = ( 96.0, 120.0 )
LOADING = ( 160.0, 144.0 )
CEILING_LIGHT_SPACING = 320.0


@dataclass
class Room:
    name: str
    e0: float
    e1: float
    n0: float
    n1: float
    floor: str
    walls: str
    ceiling: float
    light: str
    surface: str = STONE


ROOMS = {
    "gift": Room( "Gift Shop", -1450, -576, -556, -30, "floorboards", C( "plaster" ), 240, WARM, WOOD ),
    "kelp": Room( "Kelp Hall", -1450, -976, -14, 950, C( "floor_gang" ), C( "navy" ), 320, BLUE ),
    "stores": Room( "Stores", -1450, -1166, 966, 1450, "concrete", "whitewash", 288, COOL ),
    "filter": Room( "Filter Hall", -1150, -408, 966, 1450, "concrete", C( "concrete" ), 320, COOL ),
    "labs": Room( "Labs", -392, 392, 966, 1450, "quarry_tiles", "whitewash", 240, COOL, TILE ),
    "pump": Room( "Pump Room", 408, 1150, 966, 1450, "concrete", C( "concrete" ), 288, COOL ),
    "workshop": Room( "Workshop", 1166, 1450, 966, 1450, "concrete", "whitewash", 288, WARM ),
    "cloak": Room( "Cloakroom", -560, -232, -556, -390, C( "floor_gang" ), C( "plaster" ), 240, WARM ),
    "ticket": Room( "Ticket Hall", 232, 560, -556, -390, C( "floor_gang" ), C( "plaster" ), 240, WARM ),
    "cafe": Room( "Café", 576, 1450, -556, -276, "quarry_tiles", C( "plaster" ), 256, WARM, TILE ),
    "lobby": Room( "East Lobby", 976, 1450, -260, 260, C( "floor_gang" ), C( "limestone" ), H.LOBBY_HEIGHT, WARM ),
    "reef": Room( "Reef Hall", 536, 1450, 276, 950, C( "floor_tunnel" ), C( "navy" ), 320, BLUE ),
}


def room_rects( key ):
    """ A room's floor as rectangles ( e0, e1, n0, n1 ): the lobby's leaves out the corridor's end, which is the hall's. """
    r = ROOMS[key]
    if key == "lobby":
        side = H.CORRIDOR_SIDE[1]
        return [ ( r.e0, r.e1, r.n0, -side ), ( r.e0, r.e1, side, r.n1 ), ( H.CORRIDOR_EAST, r.e1, -side, side ) ]
    return [ ( r.e0, r.e1, r.n0, r.n1 ) ]


def wall_paint( room ):
    return ROOMS[room].walls if room else None


# The outer walls: ( axis, across, outward, segments ( r0, r1, the room inside ), doors ( centre, width, height ) ).
# The west and east walls run the building's whole length, so their ends are its corners.
OUTER_WALLS = [
    ( "n", ( -1474, -1450 ), "-e", [ ( -580, -22, "gift" ), ( -22, 958, "kelp" ), ( 958, 1474, "stores" ) ],
      [ ( -300, *DOOR ), ( 90, *DOOR ), ( 880, *DOOR ), ( 1200, *LOADING ) ] ),
    ( "n", ( 1450, 1474 ), "+e", [ ( -580, -268, "cafe" ), ( -268, 268, "lobby" ), ( 268, 958, "reef" ),
                                   ( 958, 1474, "workshop" ) ],
      [ ( -420, *DOOR ), ( 0, 128, 128 ), ( 600, *DOOR ), ( 1200, *LOADING ) ] ),
    # The front. The hall's entrance stands 16 behind it, through the porch (e 0).
    ( "e", ( -580, -556 ), "-n", [ ( -1450, -568, "gift" ), ( -568, -224, "cloak" ), ( -224, 224, None ),
                                   ( 224, 568, "ticket" ), ( 568, 1450, "cafe" ) ],
      [ ( -1200, *DOOR ), ( -800, *DOOR ), ( -400, 80, 120 ), ( 0, 140, 175 ), ( 400, 80, 120 ), ( 800, *DOOR ),
        ( 1100, *DOOR ) ] ),
    ( "e", ( 1450, 1474 ), "+n", [ ( -1450, -1158, "stores" ), ( -1158, -400, "filter" ), ( -400, 400, "labs" ),
                                   ( 400, 1158, "pump" ), ( 1158, 1450, "workshop" ) ], [] ),
]
# Outside paint, and what the inside gets, in bands up the wall: a plinth, the wall, and a dark band round the roof.
OUTER_BANDS = [ ( ( 0.0, SKIRTING ), DARK, "skirting" ), ( ( SKIRTING, 24.0 ), DARK, "room" ),
                ( ( 24.0, WALL_TOP ), C( "limestone" ), "room" ), ( ( WALL_TOP, ROOF_TOP ), DARK, None ) ]

# The inner walls: ( axis, across, pieces ( r0, r1, the room on the low side (south or west), the high side's, doors
# (centres) ) ). None is no room: the space round the hall that nobody goes into. "mouth" is the tunnel's way in.
INNER_WALLS = [
    ( "e", ( 950, 966 ), [ ( -1450, -1158, "kelp", "stores", [ -1300 ] ), ( -1158, -968, "kelp", "filter", [ -1060 ] ),
                           ( -968, -400, None, "filter", [] ), ( -400, 400, None, "labs", [] ),
                           ( 400, 528, None, "pump", [] ), ( 528, 1158, "reef", "pump", [ 700 ] ),
                           ( 1158, 1450, "reef", "workshop", [ 1300 ] ) ] ),
    ( "n", ( -1166, -1150 ), [ ( 958, 1450, "stores", "filter", [ 1040, 1290 ] ) ] ),
    ( "n", ( -408, -392 ), [ ( 958, 1450, "filter", "labs", [ 1130, 1280 ] ) ] ),
    ( "n", ( 392, 408 ), [ ( 958, 1450, "labs", "pump", [ 1040, 1300 ] ) ] ),
    ( "n", ( 1150, 1166 ), [ ( 958, 1450, "pump", "workshop", [ 1100, 1230 ] ) ] ),
    ( "n", ( -976, -960 ), [ ( -22, 958, "kelp", None, [ "mouth" ] ) ] ),
    ( "e", ( -30, -14 ), [ ( -1450, -968, "gift", "kelp", [ -1350, -1080 ] ), ( -968, -568, "gift", None, [] ) ] ),
    ( "n", ( -576, -560 ), [ ( -556, -382, "gift", "cloak", [ -470 ] ), ( -382, -22, "gift", None, [] ) ] ),
    ( "e", ( -390, -374 ), [ ( -568, -224, "cloak", None, [] ), ( 224, 568, "ticket", None, [] ) ] ),
    ( "n", ( -232, -216 ), [ ( -556, -382, "cloak", None, [] ) ] ),
    ( "n", ( 216, 232 ), [ ( -556, -382, None, "ticket", [] ) ] ),
    ( "n", ( 560, 576 ), [ ( -556, -382, "ticket", "cafe", [ -470 ] ), ( -382, -268, None, "cafe", [] ) ] ),
    ( "e", ( -276, -260 ), [ ( 568, 968, "cafe", None, [] ), ( 968, 1450, "cafe", "lobby", [ 1250 ] ) ] ),
    ( "n", ( 960, 976 ), [ ( -268, -152, None, "lobby", [] ), ( 152, 268, None, "lobby", [] ) ] ),
    ( "e", ( 260, 276 ), [ ( 528, 968, None, "reef", [] ), ( 968, 1450, "lobby", "reef", [ 1250 ] ) ] ),
    ( "n", ( 520, 536 ), [ ( 268, 958, None, "reef", [] ) ] ),
]


# ---------------------------------------------------------------------------------------------------------------------
# Walls

def collide_wall( model, axis, run, across, z, outward, openings ):
    """ A wall's collision, as one wall from z0 to z1 with its doorways (its paint goes in bands, with none). """
    scratch = Model()
    wall = Wall( axis, run, across, z, outward )
    for centre, width, height in openings:
        wall.add( centre, width, 0.0, height, "door" )
    wall.build( scratch, "x", "x", "x", surface=STONE )
    model.boxes.extend( scratch.boxes )


def threshold( model, axis, across, centre, width, paint=DARK ):
    """ The floor through a doorway, across the wall's thickness. """
    d0, d1 = across
    if axis == "e":
        BM.rect( model, paint, centre - width / 2, centre + width / 2, d0, d1, 0.0 )
    else:
        BM.rect( model, paint, d0, d1, centre - width / 2, centre + width / 2, 0.0 )


def outer_walls( model ):
    for axis, across, outward, segments, doors in OUTER_WALLS:
        for r0, r1, room in segments:
            mine = [ d for d in doors if r0 < d[0] < r1 ]
            for centre, width, _ in mine:
                assert r0 <= centre - width / 2 and centre + width / 2 <= r1, ( axis, across, centre )
            for z, outside, inside in OUTER_BANDS:
                wall = Wall( axis, ( r0, r1 ), across, z, outward )
                for centre, width, height in mine:
                    wall.add( centre, width, 0.0, height, "door" )
                paint = None if room is None or inside is None else ( DARK if inside == "skirting" else wall_paint( room ) )
                wall.build( model, outside, paint, DARK, end=None, surface=None )
        collide_wall( model, axis, ( segments[0][0], segments[-1][1] ), across, ( 0.0, ROOF_TOP ), outward, doors )
        for centre, width, _ in doors:
            threshold( model, axis, across, centre, width )
    # The building's corners: the west and east walls' ends.
    for e0, e1 in ( ( OUTER[0], OUTER[0] + 24 ), ( OUTER[1] - 24, OUTER[1] ) ):
        for n, towards in ( ( OUTER[2], -1.0 ), ( OUTER[3], 1.0 ) ):
            for ( z0, z1 ), outside, _ in OUTER_BANDS:
                BM.facing( model, outside, [ ( e0, n, z0 ), ( e1, n, z0 ), ( e1, n, z1 ), ( e0, n, z1 ) ], ( 0, towards, 0 ) )


def inner_walls( model, mouth ):
    for axis, across, pieces in INNER_WALLS:
        outward = "+n" if axis == "e" else "+e"
        for r0, r1, low, high, doors in pieces:
            openings = [ mouth if d == "mouth" else ( d, *DOOR ) for d in doors ]
            for z, skirting in ( ( ( 0.0, SKIRTING ), True ), ( ( SKIRTING, WALL_TOP ), False ) ):
                wall = Wall( axis, ( r0, r1 ), across, z, outward )
                for centre, width, height in openings:
                    wall.add( centre, width, 0.0, height, "door" )
                low_paint = ( DARK if skirting else wall_paint( low ) ) if low else None
                high_paint = ( DARK if skirting else wall_paint( high ) ) if high else None
                wall.build( model, high_paint, low_paint, DARK, end=None, surface=None )
            collide_wall( model, axis, ( r0, r1 ), across, ( 0.0, WALL_TOP ), outward, openings )
            for centre, width, _ in openings:
                threshold( model, axis, across, centre, width, C( "floor_tunnel" ) if ( centre, width ) == mouth[:2] else DARK )


def porch( model ):
    """ The 16 between the front wall's doorway (e 0) and the hall's entrance: lined in dark stone, with a ceiling at the
    doorway's head. Either side, up to the cloakroom and the ticket hall, is solid. """
    for e, towards in ( ( -70.0, 1.0 ), ( 70.0, -1.0 ) ):
        BM.facing( model, DARK, [ ( e, -556, 0 ), ( e, -540, 0 ), ( e, -540, 175 ), ( e, -556, 175 ) ], ( towards, 0, 0 ) )
    model.polygon( C( "ceiling" ), [ ( -70, -540, 175 ), ( 70, -540, 175 ), ( 70, -556, 175 ), ( -70, -556, 175 ) ] )
    BM.rect( model, C( "paving" ), -70, 70, -556, -540, 0.0 )
    model.collision_box( ( -70, -556, 175 ), ( 70, -540, WALL_TOP ), STONE )
    for s in ( -1, 1 ):
        model.collision_box( ( s * 110, -556, 0 ), ( s * 216, -496, WALL_TOP ), STONE )
        model.collision_box( ( s * 70, -556, 0 ), ( s * 110, -541, WALL_TOP ), STONE )


def roof( model ):
    """ The roof over everything, from the walls' tops: nothing reaches it, so it's only drawn from above. """
    e0, e1, n0, n1 = OUTER
    BM.rect( model, "concrete", e0, e1, n0, n1, ROOF_TOP )
    model.collision_box( ( e0 + 24, n0 + 24, WALL_TOP ), ( e1 - 24, n1 - 24, ROOF_TOP ), STONE )
    for e, n in ( ( -1100, 1200 ), ( -300, 1250 ), ( 600, 1200 ), ( 1200, 700 ), ( -1200, 400 ), ( 900, -400 ) ):
        model.box( ( e - 40, n - 30, ROOF_TOP ), ( e + 40, n + 30, ROOF_TOP + 36 ), { "default": C( "metal" ), "-z": None } )


# ---------------------------------------------------------------------------------------------------------------------
# Rooms: floors, ceilings and lights

def rooms( model, lights ):
    for key, r in ROOMS.items():
        for e0, e1, n0, n1 in room_rects( key ):
            BM.rect( model, r.floor, e0, e1, n0, n1, 0.0 )
            h = r.ceiling
            model.polygon( C( "ceiling" ), [ ( e0, n1, h ), ( e1, n1, h ), ( e1, n0, h ), ( e0, n0, h ) ] )
            model.collision_box( ( e0, n0, h ), ( e1, n1, WALL_TOP ), STONE )
        cols = max( 1, round( ( r.e1 - r.e0 ) / CEILING_LIGHT_SPACING ) )
        rows = max( 1, round( ( r.n1 - r.n0 ) / CEILING_LIGHT_SPACING ) )
        step_e, step_n = ( r.e1 - r.e0 ) / cols, ( r.n1 - r.n0 ) / rows
        radius = max( 420.0, 1.4 * max( step_e, step_n ) )
        for i in range( cols ):
            for j in range( rows ):
                e, n = r.e0 + ( i + 0.5 ) * step_e, r.n0 + ( j + 0.5 ) * step_n
                lamp( model, e, n, r.ceiling )
                lights.append( BM.light( f"{r.name} {i * rows + j + 1}", ( e, n, r.ceiling - 30 ), r.light, radius ) )


def lamp( model, e, n, z ):
    """ A ceiling light: a glowing panel. """
    model.polygon( C( "lamp" ), [ ( e - 30, n + 8, z - 0.5 ), ( e + 30, n + 8, z - 0.5 ), ( e + 30, n - 8, z - 0.5 ),
                                  ( e - 30, n - 8, z - 0.5 ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# Furnishings

# Columns of the coral atlas (u), in its top half: the green kelp and the sea grass. Its v runs down the picture, the
# OBJ's up, so the plants' feet are at v 0.5 and their tips at 1.
KELP_UV = ( ( 0.125, 0.25 ), ( 0.25, 0.375 ) )


def kelp( model, centre, z, height, width, seed ):
    """ A plant in a tank: two crossed cards of the coral atlas, drawn from both sides. """
    rng = np.random.default_rng( seed )
    u0, u1 = KELP_UV[seed % 2]
    a = rng.uniform( 0, math.pi )
    c = np.asarray( centre, float )
    for turn in ( 0.0, math.pi / 2 ):
        d = np.array( ( math.cos( a + turn ), math.sin( a + turn ) ) ) * width / 2
        model.polygon( C( "coral" ), [ ( *( c - d ), z ), ( *( c + d ), z ), ( *( c + d ), z + height ), ( *( c - d ), z + height ) ],
                       both_sides=True, uv=[ ( u0, 0.5 ), ( u1, 0.5 ), ( u1, 1.0 ), ( u0, 1.0 ) ] )


def counter( model, e0, e1, n0, n1, height=52.0, top=None, front=None ):
    """ A counter or a desk, solid to the floor: a headglitch at 50-54. """
    model.box( ( e0, n0, 0 ), ( e1, n1, height - 3 ), front or C( "cream" ), WOOD )
    model.box( ( e0 - 1.5, n0 - 1.5, height - 3 ), ( e1 + 1.5, n1 + 1.5, height ), top or C( "wood" ), WOOD )


def shelf( model, e0, e1, n0, n1, height, rng ):
    """ A shop's shelf unit with goods on it. Low ones (52) are headglitches; tall ones (160) stand against walls. """
    model.box( ( e0, n0, 0 ), ( e1, n1, height ), C( "wood" ), WOOD )
    goods = ( C( "snack_coral" ), C( "snack_gold" ), C( "cream" ), C( "locker" ) )
    long_e = e1 - e0 > n1 - n0
    length = max( e1 - e0, n1 - n0 )
    count = int( length // 18 )
    for k in range( count ):
        a0 = ( e0 if long_e else n0 ) + 3 + k * ( length - 6 ) / count
        a1 = a0 + ( length - 6 ) / count - 3
        w = float( rng.uniform( 7, 13 ) )
        h = float( rng.uniform( 6, 12 ) )
        paint = goods[int( rng.integers( 0, 3 ) )]
        if height < 100:
            mid = ( n0 + n1 ) / 2 if long_e else ( e0 + e1 ) / 2
            lo = ( a0, mid - w / 2, height ) if long_e else ( mid - w / 2, a0, height )
            hi = ( a1, mid + w / 2, height + h ) if long_e else ( mid + w / 2, a1, height + h )
            model.box( lo, hi, { "default": paint, "-z": None } )
        else:
            # Rows of goods on the open face (the one away from the wall), standing proud of it.
            for z in ( 30, 70, 110 ):
                if long_e:
                    face_n = n0 if n1 > -60 else n1
                    lo, hi = ( a0, face_n - 2, z ), ( a1, face_n + 2, z + h + 6 )
                else:
                    face_e = e0 if e1 > 0 else e1
                    lo, hi = ( face_e - 2, a0, z ), ( face_e + 2, a1, z + h + 6 )
                model.box( lo, hi, { "default": paint, "-z": None } )


def planter( model, e0, e1, n0, n1, height=52.0, seed=0, z=0.0 ):
    """ A concrete planter with bushes: a headglitch (the bushes don't stop anything). """
    model.box( ( e0, n0, z ), ( e1, n1, z + height ), { "default": C( "concrete" ), "+z": C( "soil" ) }, STONE )
    height += z
    width = min( e1 - e0, n1 - n0 )
    count = max( 1, round( max( e1 - e0, n1 - n0 ) / width ) )
    for k in range( count ):
        t = ( k + 0.5 ) / count
        at = ( e0 + ( e1 - e0 ) * t, ( n0 + n1 ) / 2, height + width * 0.3 ) if e1 - e0 >= n1 - n0 else \
            ( ( e0 + e1 ) / 2, n0 + ( n1 - n0 ) * t, height + width * 0.3 )
        Detail.shrub( model, at, width * 0.45, 0.7, seed + k )


def bistro( model, centre, z=0.0 ):
    """ A café table (collision: a post to its top) and two chairs facing each other across it. """
    Detail.bistro_table( model, centre, z )
    model.cylinder( centre, 14, z, z + 29, {}, sides=8, surface=METAL )
    for side, yaw in ( ( -1, 0.0 ), ( 1, 180.0 ) ):
        Detail.bistro_chair( model, ( centre[0] + side * 24, centre[1] ), yaw, z )


def rect_tank( model, e0, e1, n0, n1, lights, name, seed ):
    """ A free-standing tank: a dark base with sand on it, glass to 232, a steel rim, and kelp. """
    model.box( ( e0, n0, 0 ), ( e1, n1, 24 ), { "+z": C( "sand" ), "default": DARK }, STONE )
    model.box( ( e0, n0, 24 ), ( e1, n1, 232 ), { "default": C( "glass" ), "+z": None, "-z": None } )
    model.box( ( e0 - 2, n0 - 2, 232 ), ( e1 + 2, n1 + 2, 248 ), C( "metal" ) )
    model.collision_box( ( e0, n0, 24 ), ( e1, n1, 248 ), GLASS )
    model.polygon( C( "surface" ), [ ( e0, n1, 220 ), ( e1, n1, 220 ), ( e1, n0, 220 ), ( e0, n0, 220 ) ] )
    rng = np.random.default_rng( seed )
    for k in range( int( ( e1 - e0 ) * ( n1 - n0 ) / 5000 ) ):
        at = ( rng.uniform( e0 + 14, e1 - 14 ), rng.uniform( n0 + 14, n1 - 14 ) )
        kelp( model, at, 24, rng.uniform( 120, 190 ), rng.uniform( 30, 44 ), seed + k )
    lights.append( BM.light( f"{name} Tank", ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, 200 ), BLUE, 320 ) )


def round_tank( model, centre, radius, lights, name, seed ):
    """ An octagonal tank, as rect_tank, with a rock in it. """
    model.cylinder( centre, radius, 0, 24, { "side": DARK, "top": C( "sand" ) }, sides=8, surface=STONE )
    model.cylinder( centre, radius - 1, 24, 240, { "side": C( "glass" ) }, sides=8 )
    model.cylinder( centre, radius, 24, 256, {}, sides=8, surface=GLASS )
    model.cylinder( centre, radius + 2, 240, 256, { "side": C( "metal" ), "bottom": C( "metal" ) }, sides=8 )
    rim = [ ( centre[0] + ( radius - 1 ) * math.cos( k * math.pi / 4 ), centre[1] + ( radius - 1 ) * math.sin( k * math.pi / 4 ), 228 )
            for k in range( 8 ) ]
    BM.facing( model, C( "surface" ), rim, ( 0, 0, -1 ) )
    BM.blob( model, ( centre[0] + 20, centre[1] - 10, 50 ), 60, C( "rock_sea" ), squash=0.8, seed=seed )
    rng = np.random.default_rng( seed )
    for k in range( 9 ):
        a = rng.uniform( 0, 2 * math.pi )
        d = rng.uniform( 70, radius - 24 )
        kelp( model, ( centre[0] + d * math.cos( a ), centre[1] + d * math.sin( a ) ), 24, rng.uniform( 110, 180 ),
              rng.uniform( 30, 42 ), seed + k )
    lights.append( BM.light( f"{name} Tank", ( centre[0], centre[1], 210 ), BLUE, 360 ) )


def kelp_hall( model, lights ):
    # The gallery along the west wall, 64 up, its parapet a headglitch over the hall.
    model.box( ( -1450, 280, 0 ), ( -1340, 680, 64 ), { "+z": C( "floor_gang" ), "default": DARK }, STONE )
    model.box( ( -1350, 280, 64 ), ( -1340, 680, 114 ), { "+z": C( "metal" ), "default": C( "navy" ) }, STONE )
    for n0, n1 in ( ( 280, 290 ), ( 670, 680 ) ):
        model.box( ( -1386, n0, 64 ), ( -1350, n1, 114 ), { "+z": C( "metal" ), "default": C( "navy" ) }, STONE )
    BM.stair( model, ( -1450, 184 ), ( -1386, 280 ), 0, 64, "+n", C( "limestone" ), DARK, STONE )
    BM.stair( model, ( -1450, 680 ), ( -1386, 776 ), 0, 64, "-n", C( "limestone" ), DARK, STONE )
    rect_tank( model, -1250, -1110, 300, 640, lights, "Kelp Hall", 11 )
    for k, ( e, n ) in enumerate( ( ( -1180, 180 ), ( -1180, 760 ), ( -1040, 230 ) ) ):
        planter( model, e - 28, e + 28, n - 28, n + 28, seed=20 + k )


def gift_shop( model ):
    rng = np.random.default_rng( 3 )
    for e0 in ( -1280, -980 ):
        for n0, n1 in ( ( -250, -106 ), ( -470, -326 ) ):
            shelf( model, e0, e0 + 24, n0, n1, 52, rng )
    counter( model, -720, -680, -300, -160 )
    shelf( model, -1290, -1140, -62, -30, 160, rng )
    shelf( model, -1100, -900, -556, -524, 160, rng )


def cloakroom( model ):
    counter( model, -500, -360, -500, -480 )
    # The lockers along the north wall: a door picture each on their front.
    e0, e1, n0, n1, height = -480, -260, -410, -390, 160
    model.box( ( e0, n0, 0 ), ( e1, n1, height ), C( "metal" ), METAL )
    count = round( ( e1 - e0 ) / 55 )
    width = ( e1 - e0 ) / count
    for k in range( count ):
        a, b = e0 + k * width + 1, e0 + ( k + 1 ) * width - 1
        for z0, z1 in ( ( 4, 80 ), ( 82, height - 4 ) ):
            model.polygon( C( "locker" ), [ ( a, n0 - 0.3, z0 ), ( b, n0 - 0.3, z0 ), ( b, n0 - 0.3, z1 ), ( a, n0 - 0.3, z1 ) ],
                           uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] )


def ticket_hall( model ):
    # The ticket counter, its windows open over it.
    counter( model, 232, 470, -470, -450, 50 )
    for e in ( 292, 352, 412, 468 ):
        model.box( ( e - 2, -462, 50 ), ( e + 2, -458, 120 ), C( "metal" ), METAL )
    model.box( ( 232, -470, 120 ), ( 470, -450, 128 ), C( "metal" ), METAL )
    model.box( ( 300, -462, 128 ), ( 440, -458, 148 ), { "default": C( "metal" ), "-n": C( "lamp" ) } )


def cafe( model ):
    counter( model, 700, 1000, -380, -360 )
    model.box( ( 700, -292, 0 ), ( 1000, -276, 90 ), { "default": C( "wood" ), "-n": C( "cream" ) }, WOOD )
    for c in ( ( 650, -480 ), ( 1000, -500 ), ( 1230, -490 ), ( 1360, -330 ) ):
        bistro( model, c )
    planter( model, 1150, 1300, -420, -400, seed=40 )


def lobby( model ):
    counter( model, 1200, 1260, -80, 80 )
    BM.bench( model, ( 1340, 236 ), 0.0 )
    BM.bench( model, ( 1340, -236 ), 180.0 )


def reef_hall( model, lights ):
    # The walkway along the west wall, 64 up, its parapet a headglitch over the hall.
    model.box( ( 536, 400, 0 ), ( 656, 800, 64 ), { "+z": C( "floor_tunnel" ), "default": C( "navy" ) }, STONE )
    model.box( ( 646, 400, 64 ), ( 656, 800, 114 ), { "+z": C( "metal" ), "default": C( "navy" ) }, STONE )
    BM.stair( model, ( 536, 304 ), ( 600, 400 ), 0, 64, "+n", C( "limestone" ), DARK, STONE )
    BM.stair( model, ( 536, 800 ), ( 600, 896 ), 0, 64, "-n", C( "limestone" ), DARK, STONE )
    round_tank( model, ( 950, 613 ), 150, lights, "Reef Hall", 31 )
    for e, n in ( ( 1250, 420 ), ( 1250, 820 ) ):
        model.box( ( e - 40, n - 20, 0 ), ( e + 40, n + 20, 40 ), C( "wood" ), WOOD )
        model.box( ( e - 40, n - 20, 40 ), ( e + 40, n + 20, 52 ), { "default": C( "glass" ), "-z": None } )
        model.collision_box( ( e - 40, n - 20, 40 ), ( e + 40, n + 20, 52 ), WOOD )
        model.box( ( e - 12, n - 6, 40 ), ( e + 12, n + 6, 46 ), C( "snack_coral" ) )


def stores( model ):
    for centre, stack in ( ( ( -1390, 1020 ), True ), ( ( -1240, 1400 ), False ), ( ( -1380, 1410 ), True ),
                           ( ( -1300, 1180 ), False ) ):
        top = BM.crate( model, centre, 52.0, 0.0 )
        if stack:
            BM.crate( model, centre, 40.0, 12.0, top )
    for at in ( ( -1420, 1300 ), ( -1424, 1272 ) ):
        BM.barrel( model, at )


def filter_hall( model ):
    # The catwalk along the back wall, 96 up on posts, with a railing: a headglitch over the hall.
    model.box( ( -1150, 1350, 88 ), ( -408, 1450, 96 ), C( "steel" ), METAL )
    for e in range( -1110, -420, 140 ):
        model.box( ( e - 3, 1353, 0 ), ( e + 3, 1359, 88 ), C( "metal" ), METAL )
    BM.stair( model, ( -1080, 1218 ), ( -1016, 1350 ), 0, 96, "+n", C( "steel" ), C( "metal" ), METAL )
    BM.stair( model, ( -550, 1218 ), ( -486, 1350 ), 0, 96, "+n", C( "steel" ), C( "metal" ), METAL )
    for e0, e1 in ( ( -1150, -1080 ), ( -1016, -550 ), ( -486, -408 ) ):
        model.box( ( e0, 1350, 96 ), ( e1, 1356, 148 ), C( "metal" ), METAL )
    # The filters, with their pipes up into the ceiling.
    for e in ( -870, -660 ):
        model.cylinder( ( e, 1110 ), 70, 0, 200, { "side": C( "steel" ), "top": C( "metal" ) }, sides=16, surface=METAL )
        model.cylinder( ( e, 1110 ), 12, 200, 320, { "side": C( "metal" ) }, sides=8 )
        model.beam( ( e + 60, 1150, 150 ), ( e + 60, 1340, 150 ), ( 10, 10 ), C( "metal" ) )


def labs( model ):
    rng = np.random.default_rng( 7 )
    for sx in ( -1, 1 ):
        e0, e1 = sorted( ( sx * 100, sx * 300 ) )
        for n in ( 1080, 1210, 1340 ):
            model.box( ( e0, n - 24, 0 ), ( e1, n + 24, 52 ), { "+z": C( "steel" ), "default": "trim_white" }, METAL )
            # A monitor and a box or two on the bench.
            e = float( rng.uniform( e0 + 20, e1 - 40 ) )
            model.box( ( e, n - 4, 52 ), ( e + 22, n, 66 ), { "default": C( "black" ), "-n": C( "screens" ), "-z": None } )
            model.box( ( e + 40, n - 10, 52 ), ( e + 56, n + 6, 60 ), { "default": C( "cream" ), "-z": None } )
        h0, h1 = sorted( ( sx * 120, sx * 280 ) )
        model.box( ( h0, 1420, 0 ), ( h1, 1450, 200 ), { "default": C( "steel" ), "-n": "trim_white" }, METAL )
        model.box( ( h0 + 8, 1419, 60 ), ( h1 - 8, 1420, 150 ), C( "glass" ) )


def pump_room( model ):
    # The platform in the north-east corner, 48 up, its parapets a headglitch over the room (bomb site A).
    model.box( ( 920, 1300, 0 ), ( 1150, 1450, 48 ), { "+z": C( "steel" ), "default": C( "concrete" ) }, STONE )
    BM.stair( model, ( 854, 1300 ), ( 920, 1364 ), 0, 48, "+e", C( "steel" ), C( "metal" ), METAL )
    model.box( ( 920, 1364, 48 ), ( 926, 1450, 100 ), C( "metal" ), METAL )
    model.box( ( 926, 1300, 48 ), ( 1150, 1306, 100 ), C( "metal" ), METAL )
    for centre in ( ( 650, 1390 ), ( 790, 1410 ) ):
        model.cylinder( centre, 40, 0, 100, { "side": C( "steel" ), "top": C( "metal" ) }, sides=12, surface=METAL )
        model.cylinder( centre, 10, 100, 288, { "side": C( "metal" ) }, sides=8 )
    model.box( ( 970, 1140, 0 ), ( 1030, 1160, 160 ), { "default": C( "metal" ), "-n": C( "screens" ) }, METAL )
    for centre in ( ( 520, 1400 ), ( 546, 1424 ), ( 518, 1430 ) ):
        model.cylinder( centre, 12, 0, 36, { "side": "iron_green", "top": "iron_green" }, sides=12, surface=METAL )


def workshop( model ):
    model.box( ( 1180, 1416, 0 ), ( 1440, 1450, 36 ), { "+z": "planks", "default": C( "metal" ) }, WOOD )
    model.box( ( 1250, 1320, 0 ), ( 1350, 1360, 52 ), { "+z": "planks", "default": C( "metal" ) }, WOOD )
    BM.crate( model, ( 1420, 1010 ), 52.0, 5.0 )
    BM.crate( model, ( 1200, 1100 ), 44.0, -10.0 )


def build_rooms( parts, lights, mouth ):
    model = H.kit_model( parts )
    outer_walls( model )
    inner_walls( model, mouth )
    porch( model )
    rooms( model, lights )
    kelp_hall( model, lights )
    gift_shop( model )
    cloakroom( model )
    ticket_hall( model )
    cafe( model )
    lobby( model )
    reef_hall( model, lights )
    stores( model )
    filter_hall( model )
    labs( model )
    pump_room( model )
    workshop( model )
    roof( model )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Outside

TERRACE = ( 800.0, 1300.0, -1100.0, -750.0 )    # bomb site B: e0, e1, n0, n1
TERRACE_Z = 32.0


def car( model, centre, yaw, paint ):
    """ A small car, 170 long, 57 high: its bonnet and boot are headglitches. """
    p = BM.Place( ( centre[0], centre[1], 0 ), yaw )
    p.box( model, ( -85, -34, 12 ), ( 85, 34, 38 ), paint )
    p.box( model, ( -40, -30, 38 ), ( 32, 30, 57 ), { "default": "glass", "+z": paint } )
    for x in ( -55, 55 ):
        for s in ( -1, 1 ):
            BM.axle( model, p.at( ( x, s * 30, 12 ) ), p.y, 12, 8, { "side": "iron_black", "end": "roller_grey" } )
    p.box( model, ( -85, -34, 0 ), ( 85, 34, 38 ), None, SHEET )
    p.box( model, ( -40, -30, 38 ), ( 32, 30, 57 ), None, SHEET )


def bus( model, centre, yaw ):
    p = BM.Place( ( centre[0], centre[1], 0 ), yaw )
    p.box( model, ( -210, -50, 16 ), ( 210, 50, 124 ), { "default": "trim_red", "+z": "roller_grey" }, SHEET )
    for s in ( -1, 1 ):
        p.box( model, ( -190, s * 50 - 0.5, 70 ), ( 170, s * 50 + 0.5, 108 ), "glass" )
        for x in ( -140, 140 ):
            BM.axle( model, p.at( ( x, s * 44, 18 ) ), p.y, 18, 12, { "side": "iron_black", "end": "roller_grey" } )
    p.box( model, ( 209.5, -44, 60 ), ( 210.5, 44, 110 ), "glass" )
    p.box( model, ( -210, -50, 0 ), ( 210, 50, 16 ), None, SHEET )


def container( model, centre, yaw, paint="corrugated" ):
    p = BM.Place( ( centre[0], centre[1], 0 ), yaw )
    p.box( model, ( -120, -48, 0 ), ( 120, 48, 102 ), { "default": paint, "+x": "roller_grey" }, METAL )


def food_truck( model, centre, yaw ):
    """ A food truck with its hatch open along its +y side. """
    p = BM.Place( ( centre[0], centre[1], 0 ), yaw )
    p.box( model, ( -100, -40, 16 ), ( 100, 40, 110 ), { "default": "trim_white", "+z": "roller_grey" }, SHEET )
    p.box( model, ( 30, -38, 30 ), ( 100, 38, 80 ), { "default": "trim_blue", "+x": "glass" } )
    p.box( model, ( -80, 39, 56 ), ( 10, 41, 92 ), C( "black" ) )
    p.box( model, ( -84, 40, 54 ), ( 14, 52, 57 ), C( "metal" ) )
    p.box( model, ( -84, 40, 92 ), ( 14, 64, 95 ), "canvas_red" )
    for x in ( -60, 60 ):
        for s in ( -1, 1 ):
            BM.axle( model, p.at( ( x, s * 36, 16 ) ), p.y, 16, 10, { "side": "iron_black", "end": "roller_grey" } )
    p.box( model, ( -100, -40, 0 ), ( 100, 40, 16 ), None, SHEET )


def fountain( model, centre ):
    BM.ring( model, centre, 104, 120, 0, 32, 16, { "outside": "ashlar_grey", "inside": "ashlar_grey", "top": "ashlar" }, STONE )
    rim = [ ( centre[0] + 104 * math.cos( math.pi / 16 + k * math.pi / 8 ), centre[1] + 104 * math.sin( math.pi / 16 + k * math.pi / 8 ),
              22.0 ) for k in range( 16 ) ]
    model.polygon( "water", rim )
    model.cylinder( centre, 14, 0, 62, { "side": "ashlar", "top": "ashlar" }, sides=10, surface=STONE )
    model.cylinder( centre, 40, 62, 72, { "side": "ashlar_grey", "bottom": "ashlar_grey" }, sides=16, surface=STONE )
    model.cylinder( centre, 36, 70, 70.5, { "top": "water" }, sides=16 )


def terrace( model, rng ):
    """ Bomb site B: a raised terrace in the East Garden, its walls headglitches, with steps on every side. """
    e0, e1, n0, n1 = TERRACE
    z = TERRACE_Z
    model.box( ( e0, n0, 0 ), ( e1, n1, z ), { "+z": "flagstones", "default": "ashlar" }, STONE )
    BM.stair( model, ( 1000, n1 ), ( 1100, n1 + 34 ), 0, z, "-n", "ashlar_grey", "ashlar", STONE )
    BM.stair( model, ( 1000, n0 - 34 ), ( 1100, n0 ), 0, z, "+n", "ashlar_grey", "ashlar", STONE )
    BM.stair( model, ( e0 - 34, -950 ), ( e0, -870 ), 0, z, "+e", "ashlar_grey", "ashlar", STONE )
    BM.stair( model, ( e1, -950 ), ( e1 + 34, -870 ), 0, z, "-e", "ashlar_grey", "ashlar", STONE )
    top = z + 52
    for a, b in ( ( e0, 1000 ), ( 1100, e1 ) ):
        BM.low_wall( model, a, b, n1 - 12, n1, z, top, "ashlar", "ashlar_grey" )
        BM.low_wall( model, a, b, n0, n0 + 12, z, top, "ashlar", "ashlar_grey" )
    for a, b in ( ( n0 + 12, -950 ), ( -870, n1 - 12 ) ):
        BM.low_wall( model, e0, e0 + 12, a, b, z, top, "ashlar", "ashlar_grey" )
        BM.low_wall( model, e1 - 12, e1, a, b, z, top, "ashlar", "ashlar_grey" )
    for c in ( ( 900, -820 ), ( 1200, -830 ), ( 1200, -1045 ) ):
        bistro( model, c, z )
    BM.crate( model, ( 880, -1040 ), 52.0, 12.0, z )
    planter( model, 1040, 1100, -1000, -940, seed=60, z=z )


def ground( model ):
    BM.rect( model, C( "paving" ), -600, 600, COURT[0], OUTER[2], 0.0 )
    BM.rect( model, "flagstones", -2000, -600, COURT[0], OUTER[2], 0.0 )
    BM.area( model, 600, 2000, COURT[0], OUTER[2], 0.0, "lawn", [
        ( 600, 1680, -650, -610, "gravel" ), ( 1680, 1760, COURT[0], -604, "gravel" ),
        ( 600, 800, -950, -870, "gravel" ), ( 1300, 1680, -950, -870, "gravel" ), ( 1000, 1100, -750, -610, "gravel" ) ] )
    BM.rect( model, "planks", -2000, 2000, PROMENADE[0], PROMENADE[1], 0.0 )
    BM.rect( model, "ashlar_grey", -2000, 2000, SEA_WALL, PROMENADE[0], 0.0 )
    for e0, e1 in ( ( -YARD[1], -YARD[0] ), YARD ):
        BM.rect( model, "concrete", e0, e1, OUTER[2], OUTER[3] - 24, 0.0 )
    BM.facing( model, "ashlar_grey", [ ( -2024, SEA_WALL, -60 ), ( 2024, SEA_WALL, -60 ), ( 2024, SEA_WALL, 0 ),
                                       ( -2024, SEA_WALL, 0 ) ], ( 0, -1, 0 ) )


def site_walls( model ):
    # The walls round the yards and courts, 200 high, and the yards' fences (160) with gates onto the courts.
    for s in ( -1, 1 ):
        e0, e1 = sorted( ( s * 2000, s * 2024 ) )
        model.box( ( e0, SEA_WALL, 0 ), ( e1, OUTER[3], 200 ), { "default": "brick", "+z": "ashlar_grey" }, STONE )
        e0, e1 = sorted( ( s * OUTER[1], s * 2000 ) )
        model.box( ( e0, OUTER[3] - 24, 0 ), ( e1, OUTER[3], 200 ), { "default": "brick", "+z": "ashlar_grey" }, STONE )
        run = tuple( sorted( ( s * YARD[0], s * YARD[1] ) ) )
        gate = tuple( sorted( ( s * 1640, s * 1800 ) ) )
        BM.wall_run( model, "e", run, ( -604, -580 ), 0, 160, [ gate ], paint="brick", cap="ashlar_grey" )
    # The railing along the sea.
    for e in range( -2000, 2001, 100 ):
        model.box( ( e - 1.5, -1205.5, 0 ), ( e + 1.5, -1202.5, 42 ), "iron_black" )
    model.box( ( -2000, -1206, 39 ), ( 2000, -1202, 42 ), "iron_black" )
    model.box( ( -2000, -1205, 18 ), ( 2000, -1203, 20 ), "iron_black" )
    model.collision_box( ( -2000, -1206, 0 ), ( 2000, -1202, 42 ), METAL )


def courts( model, lights, rng ):
    fountain( model, ( 0, -850 ) )
    for e in ( -330, 330 ):
        for n in ( -700, -1000 ):
            planter( model, e - 32, e + 32, n - 32, n + 32, seed=int( abs( 7 * e + n ) ) )
    for e, n in ( ( -560, -640 ), ( 560, -640 ), ( -560, -1060 ), ( 560, -1060 ) ):
        BM.lamp_post( model, ( e, n ) )
        lights.append( BM.light( f"Lamp {e} {n}", ( e, n, 140 ), WARM, 380 ) )
    BM.lorry( model, ( -1150, -850 ), 0.0, "trim_blue" )
    food_truck( model, ( -850, -1040 ), 0.0 )
    for k, ( e, n ) in enumerate( ( ( -1880, -700 ), ( -1880, -1040 ), ( -400, -1050 ), ( 1880, -700 ), ( 1450, -700 ),
                                    ( 1880, -1040 ), ( 680, -1040 ) ) ):
        BM.tree( model, ( e, n ), 0.0, 300 + 40 * ( k % 3 ), 120, 300 + k )
    BM.hedge( model, 610, 640, -1060, -960, 0, 52 )
    BM.hedge( model, 610, 640, -860, -680, 0, 52 )
    BM.hedge( model, 1400, 1640, -1060, -1030, 0, 52 )
    BM.hedge( model, 1420, 1650, -780, -750, 0, 52 )
    for e in ( -1500, -700, 700, 1500 ):
        BM.bench( model, ( e, -1125 ), 0.0 )
    terrace( model, rng )


def yards( model ):
    # Red Team's yard (west): cars and a coach. Blue Team's (east): shipping containers.
    car( model, ( -1620, 1000 ), 90.0, "trim_red" )
    car( model, ( -1560, 1180 ), 80.0, "trim_green" )
    bus( model, ( -1690, 1350 ), 0.0 )
    car( model, ( -1880, -420 ), 0.0, "trim_white" )
    container( model, ( 1620, 1060 ), 0.0 )
    container( model, ( 1790, 1360 ), 0.0, "roller_green" )
    container( model, ( 1880, 1000 ), 90.0 )
    container( model, ( 1880, -420 ), 0.0, "roller_green" )
    # Crates in front of each door onto the yards, so nobody in a doorway sees straight into the spawns. One crate of
    # each pair is a headglitch (52), the other has one on top (96).
    for s, doors in ( ( -1, ( -300, 90, 820 ) ), ( 1, ( -420, 0, 600 ) ) ):
        for k, n in enumerate( doors ):
            low, high = ( n - 27, n + 27 ) if k % 2 else ( n + 27, n - 27 )
            BM.crate( model, ( s * 1575, low ), 52.0, 3.0 * s, 0.0 )
            top = BM.crate( model, ( s * 1575, high ), 52.0, -2.0 * s, 0.0 )
            BM.crate( model, ( s * 1577, high ), 44.0, 9.0 * s, top )


def build_outside( parts, lights ):
    model = H.kit_model( parts )
    rng = np.random.default_rng( 5 )
    ground( model )
    site_walls( model )
    courts( model, lights, rng )
    yards( model )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# The vista: the sea to the south, and the town round the site. Drawn only.

def build_vista():
    model = Model()
    reach = 40000.0
    BM.rect( model, "water", -reach, reach, -reach, SEA_WALL, -40.0 )
    BM.facing( model, "ashlar_grey", [ ( -reach, SEA_WALL, -60 ), ( -2024, SEA_WALL, -60 ), ( -2024, SEA_WALL, 0 ),
                                       ( -reach, SEA_WALL, 0 ) ], ( 0, -1, 0 ) )
    BM.facing( model, "ashlar_grey", [ ( 2024, SEA_WALL, -60 ), ( reach, SEA_WALL, -60 ), ( reach, SEA_WALL, 0 ),
                                       ( 2024, SEA_WALL, 0 ) ], ( 0, -1, 0 ) )
    BM.rect( model, "concrete", -6000, -2024, SEA_WALL, 6000, 0.0 )
    BM.rect( model, "concrete", 2024, 6000, SEA_WALL, 6000, 0.0 )
    BM.rect( model, "concrete", -2024, 2024, OUTER[3], 6000, 0.0 )
    BM.rect( model, "lawn", -reach, -6000, SEA_WALL, reach, 0.0 )
    BM.rect( model, "lawn", 6000, reach, SEA_WALL, reach, 0.0 )
    BM.rect( model, "lawn", -6000, 6000, 6000, reach, 0.0 )
    # Blocks of the town, in rows along streets: none closer than 400 to the site's walls.
    rng = np.random.default_rng( 9 )
    renders = ( "render_cream", "render_ochre", "render_rose", "render_pale", "render_blue", "render_sage", "whitewash" )
    blocks = []
    for e in np.arange( -5600, 5601, 700 ):
        for n in np.arange( -900, 5601, 700 ):
            if abs( e ) < 2024 + 400 + 300 and n < OUTER[3] + 400 + 300:
                continue
            blocks.append( ( float( e ), float( n ) ) )
    for e, n in blocks:
        w, d = rng.uniform( 380, 560 ), rng.uniform( 380, 560 )
        h = rng.uniform( 260, 900 ) if abs( e ) + n < 7000 else rng.uniform( 400, 1400 )
        paint = renders[int( rng.integers( 0, len( renders ) ) )]
        model.box( ( e - w / 2, n - d / 2, 0 ), ( e + w / 2, n + d / 2, h ), { "default": paint, "+z": "slate", "-z": None } )
        # Rows of windows, as dark bands.
        for z in np.arange( 120, h - 60, 110 ):
            for face, ( lo, hi ) in ( ( "-n", ( ( e - w / 2 + 30, n - d / 2 - 1, z ), ( e + w / 2 - 30, n - d / 2, z + 50 ) ) ),
                                      ( "+e", ( ( e + w / 2, n - d / 2 + 30, z ), ( e + w / 2 + 1, n + d / 2 - 30, z + 50 ) ) ),
                                      ( "-e", ( ( e - w / 2 - 1, n - d / 2 + 30, z ), ( e - w / 2, n + d / 2 - 30, z + 50 ) ) ) ):
                model.box( lo, hi, { face: "glass" } )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Floors' collision: one layer under everything, 16 thick, with each area's surface (footsteps and impacts go by it)

FLOOR_AREAS = [
    ( *SITE, STONE ),
    ( 600, 2000, COURT[0], -604, GRASS ),
    ( -2000, 2000, PROMENADE[0], PROMENADE[1], WOOD ),
    *[ ( *rect, r.surface ) for key, r in ROOMS.items() if r.surface != STONE for rect in room_rects( key ) ],
]


def floor_collision( model, areas ):
    """ Boxes under the floor ( z -16..0 ), cut where the areas' edges are and merged where they can be. Later areas win. """
    es = sorted( { v for a in areas for v in a[:2] } )
    ns = sorted( { v for a in areas for v in a[2:4] } )
    open_boxes = {}     # ( e0, e1, surface ) -> n0

    def close( key, n1 ):
        e0, e1, surface = key
        model.collision_box( ( e0, open_boxes.pop( key ), -16.0 ), ( e1, n1, 0.0 ), surface )

    for na, nb in zip( ns, ns[1:] ):
        runs = []
        for ea, eb in zip( es, es[1:] ):
            ce, cn = ( ea + eb ) / 2, ( na + nb ) / 2
            surface = None
            for a in areas:
                if a[0] <= ce <= a[1] and a[2] <= cn <= a[3]:
                    surface = a[4]
            if runs and runs[-1][2] == surface and runs[-1][1] == ea:
                runs[-1] = ( runs[-1][0], eb, surface )
            elif surface:
                runs.append( ( ea, eb, surface ) )
        row = set( runs )
        for key in [ k for k in open_boxes if k not in row ]:
            close( key, na )
        for key in row:
            open_boxes.setdefault( key, na )
    for key in list( open_boxes ):
        close( key, ns[-1] )


# ---------------------------------------------------------------------------------------------------------------------

def split_glow( model, parts ):
    """ Takes the polygons in paints that cast no shadows (my_project draws its water, glass and lamps that way) out of
    model into a model of their own. """
    glow = Model()
    glow.material_overrides = dict( model.material_overrides )
    glow.tile_overrides = dict( model.tile_overrides )
    for paint in list( model.polygons ):
        if not paint.startswith( "core_" ) or parts[paint[len( "core_" ):]].shadows:
            continue
        items = model.polygons.pop( paint )
        for index in range( len( items ) ):
            if ( paint, index ) in model.polygon_uvs:
                glow.polygon_uvs[( paint, index )] = model.polygon_uvs.pop( ( paint, index ) )
            if ( paint, index ) in model.polygon_normals:
                glow.polygon_normals[( paint, index )] = model.polygon_normals.pop( ( paint, index ) )
        glow.polygons[paint] = items
    return glow


# ---------------------------------------------------------------------------------------------------------------------
# Walking (Belltower's check_reach, without its ramps): a 2.5D grid of the collision's level tops, kept 16 from anything
# in the way as the navmesh keeps its agents, joined where neighbouring floors are within a step. Floors over 340 (the
# ceilings' and the roof's tops) don't count.

REACH_CELL = BM.REACH_CELL
REACH_BOUNDS = ( -2040.0, 2040.0, -1240.0, 1490.0 )    # e0, e1, n0, n1
REACH_RADIUS, REACH_STEP, REACH_HEAD = BM.REACH_RADIUS, BM.REACH_STEP, BM.REACH_HEAD
REACH_TOP = 340.0


def reach_cells( outline, grow, size ):
    """ BM.reach_cells on this map's grid. """
    saved = BM.REACH_BOUNDS
    BM.REACH_BOUNDS = REACH_BOUNDS
    try:
        return BM.reach_cells( outline, grow, size )
    finally:
        BM.REACH_BOUNDS = saved


def check_reach( models, spots, picture=None ):
    """ Every spot must be on the area Red Team's spawn is on. Prints the ones that aren't and returns how many, and the
    walkable cells of that area: { cell: ( lowest, highest floor ) }. picture writes the grid: green walkable, blue
    upstairs, red and orange cut off. """
    e0, e1, n0, n1 = REACH_BOUNDS
    cols, rows = int( ( e1 - e0 ) / REACH_CELL ), int( ( n1 - n0 ) / REACH_CELL )
    in_way = [ [] for _ in range( cols * rows ) ]
    floors = [ [] for _ in range( cols * rows ) ]

    def add( points, top, level ):
        z0, z1 = float( points[:, 2].min() ), float( points[:, 2].max() )
        for c in reach_cells( BM.hull_2d( points[:, :2] ), REACH_RADIUS, ( cols, rows ) ):
            in_way[c].append( ( z0, z1 ) )
        if level and z1 <= REACH_TOP:
            for c in reach_cells( BM.hull_2d( top[:, :2] ), 0.0, ( cols, rows ) ):
                floors[c].append( z1 )

    for model in models:
        for centre, axes, size, _ in model.boxes:
            ax = np.array( axes, float )
            half = np.asarray( size, float ) / 2
            corners = np.array( [ np.asarray( centre, float ) + ax[0] * a * half[0] + ax[1] * b * half[1] + ax[2] * c * half[2]
                                  for a in ( -1, 1 ) for b in ( -1, 1 ) for c in ( -1, 1 ) ] )
            add( corners, corners[corners[:, 2] > corners[:, 2].max() - 1e-3],
                 any( abs( abs( a[2] ) - 1 ) < 1e-6 for a in ax ) )
        for points, _ in model.hulls:
            p = np.array( points, float )
            add( p, p[p[:, 2] > p[:, 2].max() - 1e-3], len( np.unique( np.round( p[:, 2], 3 ) ) ) == 2 )

    node_z, node_cell, by_cell = [], [], {}
    for c in range( cols * rows ):
        for z in sorted( set( round( z, 2 ) for z in floors[c] ) ):
            if not any( lo < z + REACH_HEAD and hi > z + REACH_STEP for lo, hi in in_way[c] ):
                by_cell.setdefault( c, [] ).append( len( node_z ) )
                node_z.append( z )
                node_cell.append( c )
    parent = list( range( len( node_z ) ) )

    def root( a ):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for k, c in enumerate( node_cell ):
        i, j = divmod( c, rows )
        for other in by_cell.get( ( i + 1 ) * rows + j, () ) if i + 1 < cols else ():
            if abs( node_z[other] - node_z[k] ) <= REACH_STEP:
                parent[root( k )] = root( other )
        for other in by_cell.get( c + 1, () ) if j + 1 < rows else ():
            if abs( node_z[other] - node_z[k] ) <= REACH_STEP:
                parent[root( k )] = root( other )
    sizes = {}
    for k in range( len( node_z ) ):
        sizes[root( k )] = sizes.get( root( k ), 0 ) + 1

    def nearest( e, n, z, within=5 ):
        i0, j0 = int( ( e - e0 ) / REACH_CELL ), int( ( n - n0 ) / REACH_CELL )
        near = [ ( math.hypot( di, dj ), k ) for di in range( -within, within + 1 ) for dj in range( -within, within + 1 )
                 for k in by_cell.get( ( i0 + di ) * rows + j0 + dj, () ) if abs( node_z[k] - z ) <= 20 ]
        return min( near )[1] if near else None

    start = nearest( *RED_SPAWNS[0] )
    main_area = root( start )

    problems = 0
    for name, ( e, n, z ) in spots:
        k = nearest( e, n, z )
        if k is None:
            print( f"  {name} at {e:g},{n:g},{z:g}: nowhere to stand within 40" )
            problems += 1
        elif root( k ) != main_area:
            print( f"  {name} at {e:g},{n:g},{z:g}: cut off, on an area of {sizes[root( k )]} cells" )
            problems += 1

    walk = {}
    for k, c in enumerate( node_cell ):
        if root( k ) == main_area:
            lo, hi = walk.get( c, ( node_z[k], node_z[k] ) )
            walk[c] = ( min( lo, node_z[k] ), max( hi, node_z[k] ) )

    if picture:
        image = np.zeros( ( rows, cols, 3 ), np.uint8 )
        for k, c in enumerate( node_cell ):
            i, j = divmod( c, rows )
            upstairs = node_z[k] > 30
            joined = root( k ) == main_area
            colour = ( ( 90, 140, 240 ) if joined else ( 240, 120, 40 ) ) if upstairs else ( ( 90, 200, 90 ) if joined else ( 220, 60, 60 ) )
            image[rows - 1 - j, i] = np.maximum( image[rows - 1 - j, i], colour )
        Image.fromarray( image ).resize( ( cols * 2, rows * 2 ), Image.NEAREST ).save( picture )
        print( f"wrote {picture}" )
    return problems, walk


# ---------------------------------------------------------------------------------------------------------------------
# The radar picture

MINIMAP_CENTRE = ( 0.0, 125.0 )      # plan ( e, n ) at the picture's centre: the Minimap Renderer's position
MINIMAP_SIZE = 4200.0
MINIMAP_PIXELS = 1024


def write_minimap( aabbs, walk ):
    """ Where you can walk (grey, upper floors lighter), low cover (darker), walls and tall things left clear, and a
    light line round the edges. North is up. """
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    e0, e1, n0, n1 = REACH_BOUNDS
    cols, rows = int( ( e1 - e0 ) / REACH_CELL ), int( ( n1 - n0 ) / REACH_CELL )
    on = np.zeros( ( cols, rows ), bool )
    low_z = np.zeros( ( cols, rows ) )
    high_z = np.zeros( ( cols, rows ) )
    for c, ( lo, hi ) in walk.items():
        i, j = divmod( c, rows )
        on[i, j], low_z[i, j], high_z[i, j] = True, lo, hi
    # Grown by two cells (the 16 the grid keeps from walls), each grown cell taking a walkable neighbour's levels.
    grown, grown_low, grown_high = on.copy(), low_z.copy(), high_z.copy()
    for di in range( -2, 3 ):
        for dj in range( -2, 3 ):
            shifted = np.roll( np.roll( on, di, 0 ), dj, 1 )
            take = shifted & ~grown
            grown_low[take] = np.roll( np.roll( low_z, di, 0 ), dj, 1 )[take]
            grown_high[take] = np.roll( np.roll( high_z, di, 0 ), dj, 1 )[take]
            grown |= shifted
    xs = left + ( np.arange( px ) + 0.5 ) * scale
    ys = top - ( np.arange( px ) + 0.5 ) * scale
    gi = np.clip( ( ( xs - e0 ) / REACH_CELL ).astype( int ), 0, cols - 1 )
    gj = np.clip( ( ( ys - n0 ) / REACH_CELL ).astype( int ), 0, rows - 1 )
    inside_x = ( xs >= e0 ) & ( xs < e1 )
    inside_y = ( ys >= n0 ) & ( ys < n1 )
    walkable = grown[gi[None, :], gj[:, None]] & inside_x[None, :] & inside_y[:, None]
    level = grown_low[gi[None, :], gj[:, None]]
    upper = grown_high[gi[None, :], gj[:, None]] > 30
    low = np.zeros( ( px, px ), bool )
    tall = np.zeros( ( px, px ), bool )
    for lo, hi in aabbs:
        j0, j1 = max( int( math.floor( ( lo[0] - left ) / scale ) ), 0 ), min( int( math.ceil( ( hi[0] - left ) / scale ) ) - 1, px - 1 )
        i0, i1 = max( int( math.floor( ( top - hi[1] ) / scale ) ), 0 ), min( int( math.ceil( ( top - lo[1] ) / scale ) ) - 1, px - 1 )
        if j1 < j0 or i1 < i0:
            continue
        cell = ( slice( i0, i1 + 1 ), slice( j0, j1 + 1 ) )
        f = level[cell]
        blocks = ( lo[2] < f + 72 ) & ( hi[2] > f + 18 )
        low[cell] |= blocks & ( hi[2] < f + 100 )
        tall[cell] |= blocks & ( hi[2] >= f + 100 )
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walkable] = ( 95, 96, 100, 235 )
    image[walkable & upper] = ( 122, 125, 131, 235 )
    image[low & walkable] = ( 66, 68, 71, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    shown = ( walkable | ( low & walkable ) ) & ~tall
    edge = np.zeros_like( shown )
    edge[1:, :] |= ~shown[:-1, :]
    edge[:-1, :] |= ~shown[1:, :]
    edge[:, 1:] |= ~shown[:, :-1]
    edge[:, :-1] |= ~shown[:, 1:]
    image[shown & edge] = ( 226, 231, 239, 255 )
    MINIMAP_FILE.parent.mkdir( parents=True, exist_ok=True )
    Image.fromarray( image, "RGBA" ).save( MINIMAP_FILE )
    print( f"wrote {MINIMAP_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------
# Previews: Belltower's flat-shaded pictures, with the aquarium's parts in their materials' mean colours

_part_colours = {}


def part_colour( part ):
    """ An aquarium part's mean colour (0..1): its colour map's, times its tint (my_project's white.vmat is the tint). """
    if part.key not in _part_colours:
        colour = np.ones( 3 )
        for root in ( K.ASSETS, A.MY_PROJECT / "Assets" ):
            vmat = root / part.material
            if vmat.exists():
                m = re.search( r'TextureColor "([^"]+)"', vmat.read_text( encoding="utf-8", errors="ignore" ) )
                if m and ( root / m.group( 1 ) ).exists():
                    small = Image.open( root / m.group( 1 ) ).convert( "RGB" ).resize( ( 16, 16 ) )
                    colour = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
                break
        _part_colours[part.key] = colour * np.array( part.tint )
    return _part_colours[part.key]


def shade( base, normal, glow ):
    return base if glow else base * ( 0.4 + 0.6 * max( 0.0, float( np.dot( normal, BM.SUN ) ) ) )


def triangles( models, hall ):
    tris, normals, colours = [], [], []

    def add( points, normal, colour ):
        for k in range( 1, len( points ) - 1 ):
            tris.append( ( points[0], points[k], points[k + 1] ) )
            normals.append( normal )
            colours.append( colour )

    for model in models:
        for paint, items in model.polygons.items():
            part = hall.parts.get( paint[len( "core_" ):] ) if paint.startswith( "core_" ) else None
            base = part_colour( part ) if part else BM.paint_colour( paint )
            for points, normal in items:
                add( points, normal, shade( base, normal, part is not None and not part.shadows ) )
    for piece in hall.pieces:
        part = hall.parts[piece.part]
        normal = H.newell( piece.points )
        length = np.linalg.norm( normal )
        if length < 1e-9:
            continue
        normal = normal / length
        add( list( piece.points ), normal, shade( part_colour( part ), normal, not part.shadows ) )
    return np.array( tris, float ), np.array( normals, float ), np.array( colours, float )


# ( name, eye, target, horizontal field of view )
VIEWS = [
    ( "forecourt", ( 0, -1150, 64 ), ( 0, -500, 160 ), 80 ),
    ( "west_court", ( -560, -1000, 64 ), ( -1900, -650, 60 ), 80 ),
    ( "east_garden", ( 640, -700, 64 ), ( 1200, -1000, 40 ), 80 ),
    ( "red_yard", ( -1900, -350, 64 ), ( -1500, 700, 80 ), 80 ),
    ( "blue_yard", ( 1900, -350, 64 ), ( 1500, 700, 80 ), 80 ),
    ( "kelp_hall", ( -1000, 40, 64 ), ( -1400, 640, 60 ), 85 ),
    ( "kelp_gallery", ( -1420, 300, 128 ), ( -1000, 800, 60 ), 85 ),
    ( "gift_shop", ( -620, -90, 64 ), ( -1300, -450, 40 ), 85 ),
    ( "filter_hall", ( -440, 1000, 64 ), ( -1100, 1400, 70 ), 85 ),
    ( "labs", ( 0, 990, 64 ), ( 0, 1440, 60 ), 85 ),
    ( "pump_room", ( 450, 1000, 64 ), ( 1100, 1400, 40 ), 85 ),
    ( "reef_hall", ( 1420, 300, 64 ), ( 700, 800, 60 ), 85 ),
    ( "cafe", ( 1420, -520, 64 ), ( 650, -330, 40 ), 85 ),
    ( "lobby", ( 1420, 0, 64 ), ( 980, 0, 60 ), 85 ),
    ( "rotunda", ( 0, -460, 64 ), ( 0, 300, 120 ), 85 ),
    ( "tunnel", ( -380, 240, 64 ), ( -900, 570, 64 ), 85 ),
    ( "aerial", ( -3200, -3600, 2600 ), ( 0, 150, 0 ), 70 ),
]


def write_previews( out_dir, models, vista, hall ):
    out_dir = Path( out_dir )
    out_dir.mkdir( parents=True, exist_ok=True )
    tris, normals, colours = triangles( models, hall )
    # From above without the roof, the ceilings or anything else over 280.
    under = tris[:, :, 2].min( axis=1 ) <= 280
    BM.top_down( tris[under], normals[under], colours[under], ( -2100, 2100, -1300, 1550 ), 2.5 ).save( out_dir / "top.png" )
    print( f"wrote {out_dir / 'top.png'}" )
    vt, vn, vc = triangles( [ vista ], hall ) if vista.polygons else ( np.zeros( ( 0, 3, 3 ) ), np.zeros( ( 0, 3 ) ), np.zeros( ( 0, 3 ) ) )
    vt, vn, vc = vt[:, :, :], vn, vc
    whole = np.concatenate( ( tris, vt ) ), np.concatenate( ( normals, vn ) ), np.concatenate( ( colours, vc ) )
    for name, eye, target, fov in VIEWS:
        BM.perspective( *whole, eye, target, fov=fov ).save( out_dir / f"{name}.png" )
        print( f"wrote {out_dir / name}.png" )
    if not MAP_ART_FILE.exists():
        # A stand-in for the menus' map picture until one is captured in the engine.
        name, eye, target, fov = VIEWS[-1]
        MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
        BM.perspective( *whole, eye, target, size=( 1920, 1080 ), fov=fov ).save( MAP_ART_FILE )
        print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( e, n, 0 ) for e in ( -1900, -1780, -1660 ) for n in ( -200, 100, 400, 700 ) ]
BLUE_SPAWNS = [ ( -e, n, z ) for e, n, z in RED_SPAWNS ]

DM_SPAWNS = [
    # Outside
    ( -1700, -800, 0 ), ( -1100, -700, 0 ), ( -200, -1000, 0 ), ( 0, -1150, 0 ), ( 1600, -950, 0 ), ( 700, -950, 0 ),
    ( 1800, -1150, 0 ), ( -1800, -1150, 0 ), ( -1800, 1000, 0 ), ( 1700, 1250, 0 ),
    # The rooms
    ( -1100, 100, 0 ), ( -1300, 870, 0 ), ( -1100, -420, 0 ), ( -300, -470, 0 ), ( 500, -500, 0 ), ( 800, -480, 0 ),
    ( 1350, 0, 0 ), ( 1250, 700, 0 ), ( 600, 600, 64 ), ( -1300, 1300, 0 ), ( -750, 1250, 0 ), ( -800, 1400, 96 ),
    ( 0, 1150, 0 ), ( 600, 1150, 0 ), ( 1050, 1400, 48 ), ( 1300, 1100, 0 ),
    # The hall
    ( 0, -150, 0 ), ( 850, 0, 0 ), ( -586, 366, 0 ),
]

# Retakes: the planter and the defenders are Red Team (Terrorist), the attackers Blue Team (CounterTerrorist).
RETAKES = {
    "bombsite_a": { "planter": [ ( 760, 1250, 0 ), ( 980, 1200, 0 ) ],
                    "defender": [ ( 500, 1100, 0 ), ( 1080, 1380, 48 ), ( 1300, 1100, 0 ), ( 0, 1200, 0 ) ],
                    "attacker": [ ( 1300, 600, 0 ), ( 1300, -150, 0 ), ( 1700, 1200, 0 ), ( 1700, 800, 0 ), ( 700, 700, 0 ) ] },
    "bombsite_b": { "planter": [ ( 1000, -900, TERRACE_Z ), ( 1150, -1000, TERRACE_Z ) ],
                    "defender": [ ( 560, -850, 0 ), ( 1400, -700, 0 ), ( 0, -700, 0 ), ( 1000, -400, 0 ) ],
                    "attacker": [ ( 1700, 400, 0 ), ( 1700, -200, 0 ), ( 1350, -50, 0 ), ( 1600, -1000, 0 ), ( 300, -1150, 0 ) ] },
}

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 408, 1150, 966, 1450, 0 ),
               ( "bombsite_b", "Bomb Site B", *TERRACE, TERRACE_Z ) ]

DOMINATION = [ ( "A", ( -1250, 100, 0 ) ), ( "B", ( 60, -150, 0 ) ), ( "C", ( 1300, 600, 0 ) ) ]
HOT_ZONES = [ ( "Kelp Hall", ( -1250, 100, 0 ) ), ( "Rotunda", ( 60, -150, 0 ) ), ( "Reef Hall", ( 1300, 600, 0 ) ),
              ( "Filter Hall", ( -780, 1260, 0 ) ), ( "Labs", ( 0, 1145, 0 ) ), ( "Pump Room", ( 800, 1220, 0 ) ),
              ( "Café", ( 850, -440, 0 ) ), ( "Gift Shop", ( -1120, -300, 0 ) ), ( "Forecourt", ( 0, -680, 0 ) ) ]
# Cash Grab: ( name, the cash, where it's taken ).
CASH_POINTS = [ ( "Labs", ( 0, 1145, 0 ), ( 0, -1150, 0 ) ),
                ( "Forecourt", ( -300, -850, 0 ), ( 0, 1400, 0 ) ),
                ( "Rotunda", ( 60, -150, 0 ), ( -1400, -900, 0 ) ) ]

# Callouts for the location readout: ( name, e0, e1, n0, n1, z0, z1 ).
CALLOUTS = [
    *[ ( ( "A SITE" if key == "pump" else r.name.upper() ), r.e0 - 8, r.e1 + 8, r.n0 - 8, r.n1 + 8, -40, WALL_TOP )
       for key, r in ROOMS.items() ],
    ( "ROTUNDA", -410, 410, -556, 420, -40, 340 ),
    ( "CORRIDOR", 410, 976, -152, 152, -40, 260 ),
    ( "TUNNEL", -960, -410, 117, 760, -40, 200 ),
    ( "FORECOURT", -600, 600, COURT[0], OUTER[2], -40, 400 ),
    ( "WEST COURT", -2000, -600, COURT[0], -604, -40, 400 ),
    ( "EAST GARDEN", 600, 2000, COURT[0], -604, -40, 400 ),
    ( "B SITE", TERRACE[0] - 34, TERRACE[1] + 34, TERRACE[2] - 34, TERRACE[3] + 34, -40, 400 ),
    ( "PROMENADE", -2000, 2000, SEA_WALL, COURT[0], -40, 400 ),
    ( "RED SPAWN", -YARD[1], -YARD[0], -604, OUTER[3], -40, 400 ),
    ( "BLUE SPAWN", YARD[0], YARD[1], -604, OUTER[3], -40, 400 ),
]

# Reflection probes: ( name, e0, e1, n0, n1, z0, z1, priority ). The rooms and the hall's parts over the one outside.
PROBES = [
    *[ ( r.name, r.e0, r.e1, r.n0, r.n1, 0, r.ceiling, 1 ) for r in ROOMS.values() ],
    ( "Rotunda", -410, 410, -560, 420, -10, 330, 1 ),
    ( "Corridor", 390, 1065, -125, 125, -10, 250, 1 ),
    ( "Tunnel", -761.6, -242.4, 117.7, 509.7, -10, 170, 1 ),
    ( "Outside", SITE[0], SITE[1], SITE[2], SITE[3], -60, 1200, 0 ),
]


def check_spots( models, spots ):
    """ Belltower's check_spots, but with each shape as it is rather than its bounding box: the tunnel's walls run
    diagonally, so their boxes covered its floor. Every spot needs room for a player (32 x 32 x 72 over it, sampled)
    and a floor within 2 under it. Prints what's wrong and returns how many problems there were. """
    from scipy.spatial import Delaunay
    shapes = []     # ( lo, hi, inside( points ) -> bool array )
    for model in models:
        for centre, axes, size, _ in model.boxes:
            c, ax, half = np.asarray( centre, float ), np.array( axes, float ), np.asarray( size, float ) / 2
            reach = np.abs( ax ).T @ half
            shapes.append( ( c - reach, c + reach,
                             lambda p, c=c, ax=ax, half=half: np.all( np.abs( ( p - c ) @ ax.T ) < half - 1e-3, axis=1 ) ) )
        for points, _ in model.hulls:
            p = np.array( points, float )
            shapes.append( ( p.min( axis=0 ), p.max( axis=0 ), lambda q, p=p: Delaunay( p ).find_simplex( q ) >= 0 ) )
    lo = np.array( [ s[0] for s in shapes ] )
    hi = np.array( [ s[1] for s in shapes ] )
    grid = np.array( [ ( x, y, z ) for x in np.linspace( -15, 15, 5 ) for y in np.linspace( -15, 15, 5 )
                       for z in np.linspace( 2, 71, 10 ) ] )
    problems = 0
    for name, ( e, n, z ) in spots:
        spot = np.array( ( e, n, z ) )
        body = spot + grid
        near = np.nonzero( np.all( ( lo < body.max( axis=0 ) ) & ( hi > body.min( axis=0 ) ), axis=1 ) )[0]
        blocking = [ k for k in near if shapes[k][2]( body ).any() ]
        if blocking:
            k = blocking[0]
            print( f"  {name} at {e:g},{n:g},{z:g}: blocked by {np.round( lo[k] ).tolist()}..{np.round( hi[k] ).tolist()}" )
            problems += 1
        under = np.array( [ ( e, n, z - 0.25 ), ( e, n, z - 1.75 ) ] )
        below = np.nonzero( np.all( ( lo <= under[1] ) & ( hi >= under[0] ), axis=1 ) )[0]
        if not any( shapes[k][2]( under ).any() for k in below ):
            print( f"  {name} at {e:g},{n:g},{z:g}: no floor under it" )
            problems += 1
    return problems


def all_spots():
    """ Every spot a player can be put at, named, for check_spots. """
    spots = [ ( f"red spawn {k}", p ) for k, p in enumerate( RED_SPAWNS ) ]
    spots += [ ( f"blue spawn {k}", p ) for k, p in enumerate( BLUE_SPAWNS ) ]
    spots += [ ( f"dm spawn {k}", p ) for k, p in enumerate( DM_SPAWNS ) ]
    spots += [ ( f"retakes {site} {role} {k}", p ) for site, roles in RETAKES.items() for role, points in roles.items()
               for k, p in enumerate( points ) ]
    spots += [ ( f"domination {name}", p ) for name, p in DOMINATION ]
    spots += [ ( f"hot zone {name}", p ) for name, p in HOT_ZONES ]
    spots += [ ( f"cash {name}", p ) for name, p, _ in CASH_POINTS ]
    spots += [ ( f"cash {name} extract", p ) for name, _, p in CASH_POINTS ]
    return spots


# ---------------------------------------------------------------------------------------------------------------------
# The scene (as Belltower's, with this map's ids)

CALLOUT_COLOUR = "0.51056,0.70698,0.49653,1"


def plan_box( e0, e1, n0, n1, z0, z1 ):
    """ A plan box as a world centre and a BoxCollider scale ( north, west, up ). """
    return K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) ), ( n1 - n0, e1 - e0, z1 - z0 )


def box_collider( key, scale, trigger=True, static=True, center=( 0, 0, 0 ) ):
    return K.component( ids, "Sandbox.BoxCollider", key, Center=K.vec( center ), ColliderFlags=0, Elasticity=None,
                        Friction=None, IsTrigger=trigger, RollingResistance=None, Scale=K.vec( scale ), Static=static,
                        Surface=None, SurfaceVelocity="0,0,0" )


def ref( go_key, component_key, component_type ):
    return { "_type": "component", "component_id": ids( component_key ), "go": ids( go_key ), "component_type": component_type }


def zone_object( name, key, box, color, display, components=(), tags="zone" ):
    centre, scale = plan_box( *box )
    return K.game_object( ids, name, key, centre, tags=tags, components=[
        *components,
        K.component( ids, "Zone", f"{key}/zone", Color=color, DisplayName=display ),
        box_collider( f"{key}/box", scale ),
    ] )


def spawn_object( name, key, position, team, tags="" ):
    """ A TeamSpawnPoint facing the building's middle ( 0, 450 ). """
    yaw = K.plan_yaw( ( -position[0], 450 - position[1] ) )
    return K.game_object( ids, name, key, K.to_world( position ), K.yaw_rotation( yaw ), tags=tags, components=[
        K.component( ids, "TeamSpawnPoint", f"{key}/point", Team=team ) ] )


def mode_group( name, key, modes, children, inverse=False ):
    return K.game_object( ids, name, key, components=[
        K.component( ids, "Facepunch.GameModeObject", f"{key}/modes", GameModes=list( modes ), Inverse=inverse ) ],
        children=children )


def cash_point( name, key, cash, extract ):
    """ Cash Grab's cash point at cash (floor, plan) and its extraction point at extract, as Belltower's are made. """
    at = K.to_world( ( cash[0], cash[1], cash[2] + 8 ) )
    local = K.to_world( ( extract[0], extract[1], extract[2] + 32 ) ) - at
    panel = K.game_object( ids, "Object", f"{key}/extract/panel", ( 0, 0, -31.8333797 ), "0,-0.707106829,0,0.707106829",
                           components=[
                               { **K.component( ids, "Sandbox.WorldPanel", f"{key}/extract/panel/world", HorizontalAlign="Center",
                                                InteractionRange=1000, LookAtCamera=False, PanelSize="1500,1500",
                                                RenderOptions={ "GameLayer": True, "OverlayLayer": False, "BloomLayer": False,
                                                                "AfterUILayer": False },
                                                RenderScale=1, VerticalAlign="Center" ), "__enabled": False },
                               K.component( ids, "Facepunch.UI.GameModes.CashGrab.ExtractPointWorldPanel", f"{key}/extract/panel/ui" ),
                           ] )
    extract_object = { **K.game_object( ids, f"Extract {name}", f"{key}/extract", local, components=[
        K.component( ids, "Facepunch.ExtractionPoint", f"{key}/extract/point", CashPoint=ref( key, f"{key}/point", "CashPoint" ),
                     Trigger=ref( f"{key}/extract", f"{key}/extract/box", "BoxCollider" ),
                     WorldPanel=ref( f"{key}/extract/panel", f"{key}/extract/panel/world", "WorldPanel" ) ),
        box_collider( f"{key}/extract/box", ( 50, 50, 50 ), static=False ),
    ], children=[ panel ] ), "NetworkMode": 1 }
    return { **K.game_object( ids, f"Cash Grab ({name})", key, at, components=[
        K.component( ids, "Facepunch.CashPoint", f"{key}/point",
                     Extracts=[ ref( f"{key}/extract", f"{key}/extract/point", "ExtractionPoint" ) ],
                     Resource="weapons/special/cash_bag/cash_bag.equip", State="Inactive" ),
    ], children=[ extract_object ] ), "NetworkMode": 1 }


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return K.game_object( ids, name, key, components=components )


def colour_text( colour ):
    return ",".join( f"{c:g}" for c in colour ) + ",1"


def probe_object( name, box, priority ):
    e0, e1, n0, n1, z0, z1 = box
    centre, scale = plan_box( e0, e1, n0, n1, z0, z1 )
    half = np.asarray( scale, float ) / 2
    key = f"probe/{name}"
    return K.game_object( ids, f"Reflections ({name})", key, centre, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", __version=1, BakedTexture=None,
                     Bounds={ "Mins": K.vec( -half ), "Maxs": K.vec( half ) }, DelayBetweenUpdates=4, Feathering=0.02,
                     FrameInterval=5, MaxDistance=700, Mode="Realtime", MultiBounce=True, Priority=priority,
                     Projection="Sphere", RenderExcludeTags="", Resolution="Medium",
                     Texture="textures/cubemaps/default2.vtex", TintColor="1,1,1,1", UpdateStrategy="OnEnabled",
                     ZFar=4096, ZNear=16 ) ] )


def write_scene( hall, lights, written, models ):
    foliage = []
    for region, model in models:
        for index, prop in enumerate( model.props ):
            key = f"foliage/{region}/{index}"
            foliage.append( K.game_object( ids, prop["name"], key, K.to_world( prop["position"] ),
                K.yaw_rotation( prop["yaw"] ), scale=K.vec( prop["scale"] ), components=[
                    K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model=prop["path"],
                                 RenderType="On", Tint="1,1,1,1" ) ] ) )
    building = K.game_object( ids, "Oceanarium", "building", children=[
        model_object( name.replace( "oceanarium_", "" ).replace( "_", " " ).title(), f"building/{name}", name, collide, shadows )
        for name, shadows, collide in written ] )

    light_objects = [
        K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
                         LightColor=color, Radius=radius, Shadows=shadows ) ] )
        for name, position, color, radius, shadows in lights ]
    light_objects += [
        K.game_object( ids, f"Hall Light {k + 1}", f"hall_light/{k}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"hall_light/{k}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
                         LightColor=colour_text( colour ), Radius=radius, Shadows=False ) ] )
        for k, ( position, radius, colour ) in enumerate( hall.lights ) ]
    light_objects += [
        K.game_object( ids, f"Hall Spot {k + 1}", f"hall_spot/{k}", K.to_world( position ), K.angles_rotation( pitch, yaw ),
                       tags="light_spot,light", components=[
                           K.component( ids, "Sandbox.SpotLight", f"hall_spot/{k}/light", Attenuation=1, ConeInner=inner,
                                        ConeOuter=outer, Contribution="Diffuse, Specular, Transmissive", Cookie=None,
                                        FogMode="Enabled", FogStrength=1, LightColor=colour_text( colour ), Radius=radius,
                                        ShadowBias=0.0005, ShadowHardness=0, Shadows=shadows ) ] )
        for k, ( position, pitch, yaw, radius, inner, outer, colour, shadows ) in enumerate( hall.spots ) ]

    team_spawns = [ spawn_object( f"Red Spawn {k + 1}", f"spawn/red/{k}", p, "Terrorist" ) for k, p in enumerate( RED_SPAWNS ) ]
    team_spawns += [ spawn_object( f"Blue Spawn {k + 1}", f"spawn/blue/{k}", p, "CounterTerrorist" ) for k, p in enumerate( BLUE_SPAWNS ) ]
    dm_spawns = [ spawn_object( f"DM Spawn {k + 1}", f"spawn/dm/{k}", p, "Unassigned", tags="deathmatch" )
                  for k, p in enumerate( DM_SPAWNS ) ]
    retakes_spawns = []
    for site, roles in RETAKES.items():
        for role, points in roles.items():
            team = "CounterTerrorist" if role == "attacker" else "Terrorist"
            retakes_spawns += [ spawn_object( f"{site} {role} {k + 1}", f"spawn/retakes/{site}/{role}/{k}", p, team,
                                              tags=f"retakes,{site},{role}" ) for k, p in enumerate( points ) ]

    bomb_sites = []
    for index, ( name, display, e0, e1, n0, n1, z ) in enumerate( BOMB_SITES ):
        key = f"site/{name}"
        centre, scale = plan_box( e0, e1, n0, n1, z, z )
        bomb_sites.append( K.game_object( ids, name, key, centre, tags="zone,bombsite", components=[
            K.component( ids, "BombSite", f"{key}/site", DamageFalloffDistance=1750, Index=index, MaxBombDamage=500 ),
            K.component( ids, "Zone", f"{key}/zone", Color="1,0,0,1", DisplayName=display ),
            box_collider( f"{key}/box", ( scale[0], scale[1], 156 ), static=False, center=( 0, 0, 78 ) ),
        ] ) )

    buy_zones = [
        zone_object( "buyzone_t", "buy/t", ( -YARD[1], -YARD[0], OUTER[2], OUTER[3] - 24, 0, 266 ), "1,0.18,0.2,1",
                     "Red Team Buy Zone", [ K.component( ids, "Facepunch.BuyZone", "buy/t/zone_buy", Team="Terrorist" ) ] ),
        zone_object( "buyzone_ct", "buy/ct", ( YARD[0], YARD[1], OUTER[2], OUTER[3] - 24, 0, 266 ), "0,0.41569,1,1",
                     "Blue Team Buy Zone", [ K.component( ids, "Facepunch.BuyZone", "buy/ct/zone_buy", Team="CounterTerrorist" ) ] ),
    ]

    callouts = [ zone_object( name, f"callout/{name}", ( e0, e1, n0, n1, z0, z1 ), CALLOUT_COLOUR, name,
                              [ K.component( ids, "Facepunch.MapLocation", f"callout/{name}/location" ) ] )
                 for name, e0, e1, n0, n1, z0, z1 in CALLOUTS ]

    play_centre, play_scale = plan_box( SITE[0] - 16, SITE[1] + 16, SITE[2] - 16, SITE[3] + 26, -300, 1300 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
    # Over the sea railing, so nobody jumps into the sea, and over the site's walls; far below, a floor that catches
    # whatever is thrown out over them.
    clips = []
    for name, box in ( ( "Sea", ( SITE[0], SITE[1], SEA_WALL, -1200, 0, 400 ) ),
                       ( "West Wall", ( SITE[0], -2000, SEA_WALL, SITE[3], 200, 400 ) ),
                       ( "East Wall", ( 2000, SITE[1], SEA_WALL, SITE[3], 200, 400 ) ),
                       ( "North Wall", ( SITE[0], SITE[1], OUTER[3] - 24, SITE[3], 200, 400 ) ) ):
        centre, scale = plan_box( *box )
        clips.append( K.game_object( ids, f"Player Clip ({name})", f"clip/{name}", centre, tags="playerclip", components=[
            box_collider( f"clip/{name}/box", scale, trigger=False ) ] ) )
    catch = K.game_object( ids, "Catch Floor", "catch", ( 200, 0, -3100 ), components=[
        box_collider( "catch/box", ( 30000, 30000, 100 ), trigger=False ) ] )

    objective_spots = [
        K.game_object( ids, f"Domination {label}", f"objective/dom/{label}", K.to_world( p ), components=[
            K.component( ids, "Facepunch.ObjectiveSpot", f"objective/dom/{label}/spot", Kind="Domination", Label=label ) ] )
        for label, p in DOMINATION ]
    objective_spots += [
        K.game_object( ids, f"Hot Zone {label}", f"objective/hot/{label}", K.to_world( p ), components=[
            K.component( ids, "Facepunch.ObjectiveSpot", f"objective/hot/{label}/spot", Kind="HotZone", Label=label ) ] )
        for label, p in HOT_ZONES ]

    cash = [ cash_point( name, f"cash/{name}", c, x ) for name, c, x in CASH_POINTS ]
    probes = [ probe_object( name, box[:6], box[6] ) for name, *box in PROBES ]

    objects = [
        K.game_object( ids, "Scene Information", "info", components=[
            K.component( ids, "Sandbox.SceneInformation", "info/scene", Title=TITLE, Author=None, Changes="",
                         Description="An aquarium on the seafront: the rotunda and its ocean tunnel in the middle, halls, "
                                     "shops and the back of house round it, and the courts and the garden outside.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( 48, -55 ), tags="light_directional,light", components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=False, FogMode="Enabled", FogStrength=1,
                         LightColor="1,0.93,0.8,1", ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.38,0.45,0.55,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial="materials/sky/atmosphere_sky.vmat",
                         Tint="1,1,1,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color="0.7,0.78,0.86,0.6", StartDistance=2500,
                         EndDistance=42000, FalloffExponent=1.3, Height=3000, VerticalFalloffExponent=1.2 ),
        ] ),
        K.game_object( ids, "Ambient Light", "ambient", components=[
            K.component( ids, "Sandbox.AmbientLight", "ambient/light", Color=",".join( f"{c:g}" for c in hall.ambient ) ),
        ] ),
        building,
        K.game_object( ids, "Trees and planting", "foliage", children=foliage ),
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflections", "probes", children=probes ),
        # Free-for-all modes spawn at every active spawn point, so the yards' team spawns are left out of them.
        mode_group( "Team Spawns", "spawns", ( "Deathmatch", "Gun Game" ), team_spawns, inverse=True ),
        mode_group( "Deathmatch Spawns", "spawns/dm", ( "Deathmatch", "Gun Game" ), dm_spawns ),
        mode_group( "Retakes Spawns", "spawns/retakes", ( "Retakes", ), retakes_spawns ),
        K.game_object( ids, "Bomb Sites", "sites", children=bomb_sites ),
        K.game_object( ids, "Buy Zones", "buy", children=buy_zones ),
        K.game_object( ids, "Callouts", "callouts", children=callouts ),
        play_area,
        K.game_object( ids, "Player Clips", "clips", children=clips ),
        catch,
        K.game_object( ids, "Objective Spots", "objectives", children=objective_spots ),
        mode_group( "Cash Grab", "cash", ( "Cash Grab", ), cash ),
        K.prefab_instance( ids, "prefabs/game_modes/team_deathmatch.prefab" ),
        K.prefab_instance( ids, "prefabs/game_modes/bomb_defusal.prefab" ),
        K.prefab_instance( ids, "scenes/maps/defusemap_01/game_setup.prefab" ),
    ]

    scene = {
        "__guid": ids( "scene" ),
        "GameObjects": objects,
        "SceneProperties": {
            "NetworkInterpolation": True,
            "PhysicsMode": "Physics3D",
            "TimeScale": 1,
            "WantsSystemScene": True,
            "Metadata": {
                "Title": TITLE, "Image": MAP_ART_PATH, "IsVisibleInMenu": "True",
                "GameModes": "prefabs/game_modes/team_deathmatch.prefab, prefabs/game_modes/bomb_defusal.prefab",
            },
            "NavMesh": {
                "Enabled": True, "IncludeStaticBodies": True, "IncludeKeyframedBodies": True, "EditorAutoUpdate": True,
                "AgentHeight": 64, "AgentRadius": 16, "AgentStepSize": 18, "AgentMaxSlope": 40, "ExcludedBodies": "zone",
                "IncludedBodies": "", "DeferGeneration": False, "CustomBounds": True,
                # Up to 340, under the rooms' ceilings' tops and the roof.
                "Bounds": { "Mins": K.vec( K.to_world( ( SITE[1] + 40, SITE[2] - 40, -150 ) ) ),
                            "Maxs": K.vec( K.to_world( ( SITE[0] - 40, SITE[3] + 64, REACH_TOP ) ) ) },
            },
        },
        "ResourceVersion": 3,
        "Title": TITLE,
        "Description": None,
        "__references": [ "facepunch.beech_bush_small#145429", "facepunch.tree_oak_medium_a#288916",
                          "facepunch.tree_oak_small_a#288917" ],
        "__version": 3,
    }
    SCENE_FILE.parent.mkdir( parents=True, exist_ok=True )
    K.write_text( SCENE_FILE, json.dumps( scene, indent=2 ), newline=None )
    print( f"wrote {SCENE_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", help="also write a top-down picture and views from head height to this folder" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    args = parser.parse_args()

    hall = H.Hall()
    lights = []
    n0, n1, height = hall.mouth()
    mouth = ( ( n0 + n1 ) / 2, n1 - n0, height )
    rooms_model = build_rooms( hall.parts, lights, mouth )
    floor_collision( rooms_model, FLOOR_AREAS )
    outside = build_outside( hall.parts, lights )
    vista = build_vista()
    for model in ( rooms_model, outside, vista ):
        model.grain_paints.update( ( "planks", "planks_dark" ) )
    rooms_glow = split_glow( rooms_model, hall.parts )
    outside_glow = split_glow( outside, hall.parts )

    OUT_DIR.mkdir( parents=True, exist_ok=True )
    written = []
    for name, shadows, collide, count in hall.write( OUT_DIR ):
        print( f"{name}: {count} triangles" )
        written.append( ( name, shadows, collide ) )
    for name, model, shadows, collide in ( ( "oceanarium_rooms", rooms_model, True, True ),
                                           ( "oceanarium_rooms_glow", rooms_glow, False, False ),
                                           ( "oceanarium_outside", outside, True, True ),
                                           ( "oceanarium_outside_glow", outside_glow, False, False ),
                                           ( "oceanarium_vista", vista, False, False ) ):
        if not model.polygons:
            continue
        count = K.write_model( OUT_DIR, RESOURCE_DIR, name, model )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
        written.append( ( name, shadows, collide ) )
    core = OA.core_paints( hall.parts )
    painted = { paint for model in ( rooms_model, rooms_glow, outside, outside_glow, vista ) for paint in model.polygons }
    missing = sorted( p for p in painted if p not in core and not ( BT.OUT_DIR / f"{p}_color.png" ).exists() )
    if missing:
        print( f"paints with no material: {', '.join( missing )}" )

    solid = [ hall.collision_model(), rooms_model, outside ]
    aabbs = BM.collision_aabbs( solid )
    print( "checking spots:" )
    problems = check_spots( solid, all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    if args.preview:
        Path( args.preview ).mkdir( parents=True, exist_ok=True )
    cut_off, walk = check_reach( solid, all_spots(), Path( args.preview ) / "reach.png" if args.preview else None )
    print( f"  {cut_off} spot(s) cut off from the spawns" )

    if not args.no_scene:
        write_minimap( aabbs, walk )
        write_scene( hall, lights, written, [ ( "rooms", rooms_model ), ( "outside", outside ) ] )
    if args.preview:
        write_previews( args.preview, [ rooms_model, rooms_glow, outside, outside_glow ], vista, hall )


if __name__ == "__main__":
    main()
