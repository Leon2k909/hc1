"""
Riverdale: a nuclear power station at the foot of snowy mountains, at sunrise after rain. A multiplayer map built by
script like Belltower, Railhead, Lowtide and Boxyard (map_kit's boxes and polygons), dressed after two reference
pictures: the reactor hall round its glowing fuel pool, and the wet yard between the buildings with the containment
dome and the cooling towers behind.

    python Tools/riverdale_map.py [--preview <dir>] [--no-scene] [--art]

Run Tools/riverdale_materials.py and Tools/riverdale_sky.py first. Riverdale Nuclear, its logo, its slogans and every
marking are the map's own. Writes:
- the models, to Assets/models/maps/riverdale/: the ground, the reactor hall (structure, dressing, the pool and its
  water, the control rooms' glass), the yard's middle (B1 and the turbine annex), each side's buildings and props
  (built in place, so their lettering reads the right way), the north lane, the boundary buildings, and the backdrop
  (Tools/riverdale_backdrop.py: the domes, cooling towers, mountains and forest; drawn only);
- the scene, Assets/scenes/maps/Riverdale/riverdale.scene, rewritten whole on every run (change the layout here, not in
  the editor);
- the radar picture, ui/minimaps/minimap_riverdale.png, and with --art a stand-in menu picture, ui/maps/riverdale.png.

Plan coordinates: e east, n north, z up, inches. The play area is e -2300..2300, n -1750..2450, the ground at z 0.
The layout is mirrored across e 0: Red Team spawns at the west end, Blue Team at the east. Three lanes:
- North: the north lane between the reactor hall and the perimeter wall, under a pipe rack, with the west and east
  courts leading into it.
- Middle: the reactor hall (Tools/riverdale_hall.py), entered from the A1 and A2 annexes (west and east), the yard
  (south) and the north lane: the deck round the pool, and the upper level with the control rooms. Bomb site A is the
  hall's east deck, by B2 and the water purification tanks.
- South: the wet yard: the annexes' fronts, B1 in the middle with its stairs up to its upper room, the turbine
  building's annex south of it, containers, barriers and cases. Bomb site B is the east yard.

Every run checks every spawn, objective and cash spot with railhead_map's check_spots, check_reach and
check_retakes_sight, with this map's bounds, and prints what's wrong.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import building_textures as BT
import map_kit as K
import railhead_map as R
import railhead_preview as PV
import riverdale_materials as RM
import riverdale_parts as P
import riverdale_hall as H
import riverdale_facades as F
from riverdale_parts import v, card, box, UP, METAL, STONE

TITLE = "Riverdale"
OUT_DIR = K.ASSETS / "models/maps/riverdale"
RESOURCE_DIR = "models/maps/riverdale"
SECTOR_RESOURCE_DIR = "models/maps/riverdale_sectors"
TREE_SECTOR_COUNT = 8
TREE_SOURCE_NAMES = ( "riverdale_backdrop_trees", "riverdale_backdrop_trees_near" )
TREE_SECTORS = {}  # Generated from the same polygons, normals and UVs as the two unshadowed source models.
SCENE_FILE = K.ASSETS / "scenes/maps/Riverdale/riverdale.scene"
MINIMAP_PATH = "ui/minimaps/minimap_riverdale.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_riverdale.png"
MAP_ART_PATH = "ui/maps/riverdale.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85" )

SUN_PITCH, SUN_YAW = 16.0, 123.0          # riverdale_sky's: 16 degrees up, 33 degrees north of east
SUN_COLOUR = "2.30,1.62,1.05,1"
SKY_MATERIAL = "materials/riverdale/sky/riverdale_sky.vmat"
SKY_EXPOSURE = 1.6
FOG_COLOUR = "0.96,0.84,0.72"
CATCH_FLOOR_Z = -3000

PLAY = ( -2300.0, 2300.0, -1750.0, 2450.0 )
NAV_TOP = 400.0

# The west annex (A1; A2 is its mirror) and the yard's buildings (west coordinates; the east is e -> -e).
ANNEX = ( -1700.0, -1040.0, -620.0, 240.0 )
ANNEX_TOP = 340.0
ANNEX_SOUTH_OPENING = ( -1440.0, -1180.0, 172.0 )
ANNEX_WEST_DOOR = ( -260.0, -140.0, 124.0 )
ANNEX_NORTH_DOOR = ( -1450.0, -1330.0, 124.0 )
CORE = ( -160.0, 160.0, -1040.0, -700.0 )
CORE_TOP = 440.0
ROOM_Z = 192.0
WING = ( -420.0, -160.0, -840.0, -700.0 )
B_LANDING = ( -200.0, -160.0, -940.0, -840.0 )
B_STAIR = ( -470.0, -200.0, -940.0, -864.0 )        # foot e, head e, n0, n1
TURBINE = ( -520.0, 520.0, -1750.0, -1240.0 )
TURBINE_TOP = 360.0
# Each side's turbine building block on the yard's south edge (west coordinates) and its spawn building (B2 west,
# B1 east): a tall part against the boundary with a room upstairs, a low wing, a stair up to the room's door.
TURBINE_SIDE = ( -1700.0, -1300.0, -1750.0, -1250.0 )
SPAWN_TALL = ( -2300.0, -2060.0, -1160.0, -690.0 )
SPAWN_WING = ( -2060.0, -1880.0, -840.0, -690.0 )
SPAWN_LANDING = ( -2060.0, -2020.0, -960.0, -840.0 )
SPAWN_STAIR = ( -1750.0, -2020.0, -960.0, -884.0 )       # foot e, head e, n0, n1
SPAWN_ROOM_Z = 200.0
SPAWN_TOP = 380.0
BOUNDARY_TOP = 360.0
NORTH_WALL_N = 2450.0


# ---------------------------------------------------------------------------------------------------------------------
# Paints

PAINTS = set( RM.all_paints() )


def configure( model ):
    """ rv_ paints are Riverdale's; rw_ (glass, containers) Railhead's; lt_ (the forklift, containers) and bx_ set by
    their own modules or Boxyard's. """
    known = {}
    if R.RM is not None and hasattr( R.RM, "paints" ):
        try:
            known = R.RM.paints()
        except Exception as error:
            print( f"railhead_materials.paints() failed: {error}" )
    for paint in list( model.polygons ):
        if paint.startswith( "rv_" ):
            model.material_overrides[paint] = f"{RM.RESOURCE_DIR}/{paint}.vmat"
            model.tile_overrides[paint] = RM.TILES.get( paint, 64.0 )
            if paint not in PAINTS:
                R.UNKNOWN_PAINTS.add( paint )
        elif paint.startswith( "rw_" ):
            try:
                path = R.RM.material_path( paint )
            except Exception:
                path = f"materials/railhead/{paint}.vmat"
            model.material_overrides[paint] = path
            model.tile_overrides[paint] = float( ( known[paint][1] if paint in known else None ) or 64.0 )
        elif paint.startswith( "bx_" ):
            model.material_overrides[paint] = f"materials/boxyard/{paint}.vmat"
            model.tile_overrides.setdefault( paint, 48.0 )
        elif paint not in model.material_overrides:
            try:
                BT.tile_units( paint )
            except Exception:
                R.UNKNOWN_PAINTS.add( paint )
                model.material_overrides[paint] = f"{RM.RESOURCE_DIR}/rv_wall.vmat"
                model.tile_overrides[paint] = 192.0
    model.anchored_paints = set()
    model.decal_paints = set()
    return model


def mirror_pts( pts, f ):
    return [ ( f * p[0], p[1], *p[2:] ) for p in pts ]


# ---------------------------------------------------------------------------------------------------------------------
# The ground

def ground():
    m = K.Model()
    pieces = [ ( PLAY[0], PLAY[1], PLAY[2], H.N0 - H.WT ), ( PLAY[0], PLAY[1], H.N1 + H.WT, PLAY[3] ),
               ( PLAY[0], H.E0 - H.WT, H.N0 - H.WT, H.N1 + H.WT ), ( H.E1 + H.WT, PLAY[1], H.N0 - H.WT, H.N1 + H.WT ) ]
    for e0, e1, n0, n1 in pieces:
        box( m, e0 - ( 400 if e0 == PLAY[0] else 0 ), e1 + ( 400 if e1 == PLAY[1] else 0 ), n0 - ( 400 if n0 == PLAY[2] else 0 ),
             n1 + ( 400 if n1 == PLAY[3] else 0 ), -24, 0, { "default": None, "+z": "rv_yard" }, STONE )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# A side: the annex (A1 / A2), its court, its yard's props, its spawn strip

def annex( m, sx ):
    f = -sx
    label = "A1" if sx > 0 else "A2"

    def E( a, b ):
        return ( min( f * a, f * b ), max( f * a, f * b ) )

    e0, e1, n0, n1 = ANNEX
    t = 30.0
    so = ANNEX_SOUTH_OPENING
    top = ANNEX_TOP + 30
    west, east = ( "-e", "+e" ) if f > 0 else ( "+e", "-e" )       # the faces towards the spawn and the hall
    # The walls' outer faces (and their ends and reveals, which would lie in them) are drawn by riverdale_facades below.
    H.wall( m, "e", *E( e0, e1 ), n0, n0 + t, 0, ANNEX_TOP, [ ( *E( so[0], so[1] ), so[2] ) ],
            paint={ "default": "rv_wall", "-n": None, "-e": None, "+e": None } )
    H.wall( m, "e", *E( e0, e1 ), n1 - t, n1, 0, ANNEX_TOP, [ ( *E( ANNEX_NORTH_DOOR[0], ANNEX_NORTH_DOOR[1] ), ANNEX_NORTH_DOOR[2] ) ],
            paint={ "default": "rv_wall", "+n": None, "-e": None, "+e": None } )
    H.wall( m, "n", n0, n1, *E( e0, e0 + t ), 0, ANNEX_TOP, [ ANNEX_WEST_DOOR ], paint={ "default": "rv_wall", west: None, "-n": None, "+n": None } )
    H.wall( m, "n", n0, H.N0 - H.WT, *E( e1 - t, e1 ), 0, ANNEX_TOP, paint={ "default": "rv_wall", east: None, "-n": None } )
    box( m, *E( e0, e1 ), n0, n1, ANNEX_TOP - 20, ANNEX_TOP, { "default": None, "+z": "rv_plinth", "-z": "rv_steel" }, STONE )
    for ( a, b, c, d ), inner in ( ( ( e0, e1, n0, n0 + 10 ), { "+n": "rv_wall" } ), ( ( e0, e1, n1 - 10, n1 ), { "-n": "rv_wall" } ),
                                   ( ( e0, e0 + 10, n0, n1 ), { east: "rv_wall" } ),
                                   ( ( e1 - 10, e1, n0, H.N0 - H.WT ), { west: "rv_wall", "+n": "rv_wall" } ) ):
        box( m, *E( a, b ), c, d, ANNEX_TOP, top, { "default": None, **inner }, STONE )
        F.coping( m, *E( a, b ), c, d, top )
    annex_faces( m, sx )
    # Railing round the roof's edge (the reference's yellow guard rail along A1's top).
    P.railing( m, mirror_pts( [ ( e0 + 6, n0 + 6 ), ( e1 - 6, n0 + 6 ), ( e1 - 6, H.N0 - H.WT ) ], f ), top, height=38, post_every=70 )
    # On the roof: two air handling units, exhaust fans, vents and a hatch, showing over the parapet.
    F.roof_unit( m, ( f * -1350, -470 ), ( 1, 0 ), ANNEX_TOP, ( 110, 60, 48 ) )
    F.roof_unit( m, ( f * -1560, -40 ), ( 0, 1 ), ANNEX_TOP, ( 96, 54, 44 ) )
    for e, n in ( ( -1160, -330 ), ( -1180, 60 ), ( -1600, -520 ) ):
        F.roof_fan( m, ( f * e, n ), ANNEX_TOP )
    for e, n in ( ( -1450, -220 ), ( -1300, 150 ), ( -1120, -560 ) ):
        F.roof_vent( m, ( f * e, n ), ANNEX_TOP )
    F.hatch( m, ( f * -1250, 120 ), ANNEX_TOP )
    # Inside: the floor, lamps, pipes overhead.
    box( m, *E( e0 + t, e1 ), n0 + t, n1 - t, 0, 0.15, { "default": None, "+z": "rv_floor" } )
    for k, ( e, n ) in enumerate( ( ( -1500, -420 ), ( -1220, -420 ), ( -1500, 20 ), ( -1220, 20 ) ) ):
        P.ceiling_light( m, f"{label} lamp {k}", ( f * e, n, ANNEX_TOP - 40 ), ( 1, 0 ), "cool", 420 )
    for k, r in enumerate( ( 6.0, 4.0, 4.0 ) ):
        P.pipe( m, mirror_pts( [ ( e0 + t + 4, -560 + k * 18, 330 ), ( e1 - 6, -560 + k * 18, 330 ) ], f ), r, "rv_pipe", 10 )
    P.cable_tray( m, ( f * ( e0 + 40 ), -150, 340 ), ( f * ( e1 - 10 ), -150, 340 ) )
    # Inside props: cases and a low wall of stacked crates that turns the way in towards the hall's door.
    rng = np.random.default_rng( 20 + sx )
    for k, ( e, n ) in enumerate( ( ( -1620, -540 ), ( -1600, -470 ), ( -1110, -540 ), ( -1630, 150 ), ( -1560, 160 ), ( -1110, 170 ),
                                    ( -1350, -250 ), ( -1290, -230 ), ( -1410, -260 ) ) ):
        P.case_stack( m, ( f * e, n ), ( 1, 0.1 * rng.normal() ), "olive" if k % 2 else "dark", seed=k + 40 + ( 0 if sx < 0 else 100 ) )
    # Decon frames by the hall's door: two steel portals.
    for n in ( -60.0, 100.0 ):
        for e in ( -1140.0, -1080.0 ):
            box( m, *E( e - 2, e + 2 ), n - 2, n + 2, 0, 110, "rv_yellow" )
        box( m, *E( -1142, -1078 ), n - 2, n + 2, 108, 112, "rv_yellow" )


def annex_faces( m, sx ):
    """ The annex's outer faces (riverdale_facades): heavy concrete on a darker plinth, corner piers, a precast string
    course under the parapet and its metal coping, windows set in their reveals, the openings' corner guards, and what's
    fixed to the walls. The south face is the reference's A1: the name, the reactor hall sign, louvres, the way in with
    its rolled-up shutter's housing and beacons, and pipes on brackets. """
    f = -sx
    label = "A1" if sx > 0 else "A2"
    e0, e1, n0, n1 = ANNEX
    t = 30.0
    so = ANNEX_SOUTH_OPENING
    top = ANNEX_TOP + 30
    west, east = ( "-e", "+e" ) if f > 0 else ( "+e", "-e" )

    def U( a, b ):
        return tuple( sorted( ( f * a, f * b ) ) )

    def course( face, piers ):
        face.plinth()
        face.band( ANNEX_TOP - 22, 8, 2.0 )
        for a, b in piers:
            face.pilaster( a, b, 0, ANNEX_TOP - 14, 4.0, cap=F.PRECAST )

    # The south face, towards the yard.
    s = F.Face( m, "-n", n0, f * e0, f * e1, 0, top )
    o0, o1 = U( so[0], so[1] )
    s.opening( o0, o1, 0, so[2], guides=True, housing=True )
    s.later.append( lambda: s.reveal( o0, o1, 0, so[2], t, "rv_wall", ( True, True, False, False ) ) )
    s.guard( o0, -1, 72 )
    s.guard( o1, 1, 72 )
    s.louvre( *U( -1555, -1405 ), 203, 313 )
    s.louvre( *U( -1650, -1590 ), 98, 142, blades=8 )
    course( s, [ U( e0, e0 + 34 ), U( e1 - 28, e1 ) ] )
    s.finish()
    s.letters( label, f * -1250, 258, 118 )
    s.letters( "reactor_hall_r" if sx > 0 else "reactor_hall_l", f * -1124, 104, 50 )
    for e in ( so[0], so[1] ):
        u = f * e
        P.beacon( m, f"{label} opening beacon {e}", s.p( u + ( -2 if u == o0 else 2 ), so[2] + 23, 6 ) )
    s.lamp( f"{label} opening lamp", ( o0 + o1 ) / 2, 200, "warm", 360, light=True )
    s.lamp( f"{label} corner lamp", f * -1640, 210, "warm", 300, light=True )
    s.cabinet( f * -1625, 34, 24, 40 )
    s.conduit( [ ( f * -1625, 74 ), ( f * -1625, 84 ), ( f * -1578, 84 ), ( f * -1578, ANNEX_TOP - 24 ) ] )
    s.camera( f * -1600, 300, turn=30 * f )
    s.sign( "caution", f * -1460, 120, 22 )
    for k, r in enumerate( ( 7.0, 5.0 ) ):
        z = 210 + k * 16
        run = mirror_pts( [ ( e0 + 20, n0 - 14 - k * 4, z ), ( e1 + 14 + k * 4, n0 - 14 - k * 4, z ), ( e1 + 14 + k * 4, H.N0 - H.WT, z ) ], f )
        P.pipe( m, run, r, "rv_pipe", 12 )
        F.flanges( m, run[0], run[1], r, every=220.0, start=90.0 )
    for e in np.arange( e0 + 60, e1, 140.0 ):
        box( m, *U( e - 3, e + 3 ), n0 - 22, n0, 200, 204, "rv_steel" )
        box( m, *U( e - 4, e + 4 ), n0 - 1.0, n0, 192, 206, "rv_steel" )
    # The west face, towards the spawn: the way in from it, windows, the unit's number.
    w = F.Face( m, west, f * e0, n0, n1, 0, top )
    d0, d1, dz = ANNEX_WEST_DOOR
    w.opening( d0, d1, 0, dz )
    w.later.append( lambda: w.reveal( d0, d1, 0, dz, t, "rv_wall", ( True, True, False, False ) ) )
    for u in ( d0, d1 ):
        w.guard( u, -1 if u == d0 else 1, 60 )
    w.later.append( lambda: w.canopy( ( d0 + d1 ) / 2, d1 - d0 + 36, dz + 8, 34 ) )
    for a, b, lit in ( ( -540, -480, False ), ( -450, -390, True ), ( 140, 190, False ) ):
        w.window( a, b, 196, 268, 7.0, lit=lit, blind=0.45 if lit else 0.25 )
    w.joint( -80, 24, ANNEX_TOP - 22 )
    course( w, [ ( n0, n0 + 34 ), ( n1 - 34, n1 ) ] )
    w.downpipe( -578, top - 2 )
    w.downpipe( 198, top - 2 )
    w.finish()
    w.letters( label, 60, 232, 90 )
    w.lamp( f"{label} west door lamp", ( d0 + d1 ) / 2, dz + 26, "warm", 300, light=True )
    w.sign( "danger", d0 - 34, 70, 18 )
    w.jbox( d0 - 34, 112 )
    w.conduit( [ ( d0 - 34, 118 ), ( d0 - 34, ANNEX_TOP - 24 ) ] )
    w.camera( -330, 300, turn=-35 )
    w.cabinet( d1 + 40, 30, 26, 46, paint="rv_fc_red", plate="lifering_sign" )
    # The north face, towards the court.
    nf = F.Face( m, "+n", n1, f * e0, f * e1, 0, top )
    nf.corner_trims = ( False, False )
    a0, a1 = U( ANNEX_NORTH_DOOR[0], ANNEX_NORTH_DOOR[1] )
    nf.opening( a0, a1, 0, ANNEX_NORTH_DOOR[2] )
    nf.later.append( lambda: nf.reveal( a0, a1, 0, ANNEX_NORTH_DOOR[2], t, "rv_wall", ( True, True, False, False ) ) )
    for u in ( a0, a1 ):
        nf.guard( u, -1 if u == a0 else 1, 60 )
    nf.later.append( lambda: nf.canopy( ( a0 + a1 ) / 2, a1 - a0 + 36, ANNEX_NORTH_DOOR[2] + 8, 34 ) )
    for a, b, lit in ( ( -1640, -1580, False ), ( -1560, -1500, True ), ( -1250, -1190, False ), ( -1170, -1110, False ) ):
        nf.window( *U( a, b ), 200, 270, 7.0, lit=lit, blind=0.3 )
    nf.plinth( wrap=( f > 0, f < 0 ) )
    nf.band( ANNEX_TOP - 22, 8, 2.0, wrap=( f > 0, f < 0 ) )
    nf.pilaster( *U( e0, e0 + 34 ), 0, ANNEX_TOP - 14, 4.0 )
    nf.downpipe( f * ( e0 + 44 ), top - 2 )
    nf.downpipe( f * ( e1 - 26 ), top - 2 )
    nf.finish()
    nf.lamp( f"{label} north door lamp", ( a0 + a1 ) / 2, ANNEX_NORTH_DOOR[2] + 26, "warm", 280 )
    nf.cabinet( f * -1290, 30, 26, 42 )
    nf.conduit( [ ( f * -1290, 72 ), ( f * -1290, 120 ), ( f * -1270, 140 ), ( f * -1270, ANNEX_TOP - 24 ) ] )
    nf.sign( "notice", f * -1480, 64, 20 )
    # The east face, towards the hall's apron (from the yard to the hall's corner).
    ef = F.Face( m, east, f * e1, n0, H.N0 - H.WT, 0, top )
    ef.louvre( -540, -420, 60, 150 )
    ef.door( -330, 48, 88, paint="rv_fc_door_blue", canopy=28 )
    ef.plinth( wrap=( True, False ) )
    ef.band( ANNEX_TOP - 22, 8, 2.0, wrap=( True, False ) )
    ef.pilaster( n0, n0 + 28, 0, ANNEX_TOP - 14, 4.0 )
    ef.downpipe( -584, top - 2 )
    ef.finish()
    ef.sign( "door_sign", -290, 60, 14 )
    ef.jbox( -290, 112 )
    # From inside, the windows' panes lit by the day.
    wi = F.Face( m, east, f * ( e0 + t ), n0, n1, 0, ANNEX_TOP )
    for a, b in ( ( -540, -480 ), ( -450, -390 ), ( 140, 190 ) ):
        wi.inner_window( a, b, 196, 268 )
    ni = F.Face( m, "-n", n1 - t, f * e0, f * e1, 0, ANNEX_TOP )
    for a, b in ( ( -1640, -1580 ), ( -1560, -1500 ), ( -1250, -1190 ), ( -1170, -1110 ) ):
        ni.inner_window( *U( a, b ), 200, 270 )


def transformer( m, c ):
    """ The court's oil-filled transformer, drawn over its tank box (court() keeps the plinth and tank collision): a
    lid flange and base skids, stiffeners on its ends, two banks of pressed-steel panel radiators on each long side on
    their headers and valved connections, three shedded HV porcelain bushings and four LV ones on the lid, and an oil
    bund round the plinth with gravel in it. Drawn only. """
    ce, cn = c
    # The bund: a low kerb round the plinth, gravel between.
    for a0, a1, b0, b1 in ( ( -92, 92, -72, -66 ), ( -92, 92, 66, 72 ), ( -92, -86, -66, 66 ), ( 86, 92, -66, 66 ) ):
        box( m, ce + a0, ce + a1, cn + b0, cn + b1, 0, 8, "rv_plinth" )
    for a0, a1, b0, b1 in ( ( -86, 86, -66, -50 ), ( -86, 86, 50, 66 ), ( -86, -70, -50, 50 ), ( 70, 86, -50, 50 ) ):
        box( m, ce + a0, ce + a1, cn + b0, cn + b1, 0, 3.5, "rv_gravel" )
    # The tank's lid flange with its bolts' rim, base skids and the ends' stiffeners.
    box( m, ce - 52.5, ce + 52.5, cn - 36.5, cn + 36.5, 98.5, 101.5, "rv_louvre" )
    box( m, ce - 50.5, ce + 50.5, cn - 34.5, cn + 34.5, 101.5, 103.0, "rv_louvre" )
    for sn in ( -1, 1 ):
        box( m, ce - 56, ce + 56, cn + sn * 24 - 4, cn + sn * 24 + 4, 10, 16, "rv_dark" )
    for se in ( -1, 1 ):
        for dn in ( -24.0, 24.0 ):
            box( m, *sorted( ( ce + se * 50, ce + se * 53 ) ), cn + dn - 1.5, cn + dn + 1.5, 16, 97, "rv_louvre" )
        # A lifting lug at each corner.
        for sn in ( -1, 1 ):
            box( m, *sorted( ( ce + se * 50, ce + se * 55 ) ), cn + sn * 30 - 1, cn + sn * 30 + 1, 90, 98, "rv_louvre" )
    # Panel radiators: on each long side two banks of 14 fins 2.2 in apart, standing out from the tank, a top and a
    # bottom header along each bank, joined to the tank by short flanged branches with a valve.
    for sn in ( -1, 1 ):
        n_in, n_out = cn + sn * 35.0, cn + sn * 53.0
        for e0 in ( ce - 39.0, ce + 8.0 ):
            for k in range( 14 ):
                e = e0 + k * 2.2
                box( m, e - 0.3, e + 0.3, *sorted( ( n_in + sn * 3.0, n_out ) ), 22, 90, "rv_louvre" )
            for z in ( 86.0, 26.0 ):
                hdr_n = cn + sn * 41.0
                P.rod( m, v( e0 - 1.5, hdr_n, z ), v( e0 + 13 * 2.2 + 1.5, hdr_n, z ), 1.8, "rv_louvre", 10, caps=True )
                mid = e0 + 6.5 * 2.2
                P.rod( m, v( mid, cn + sn * 34.0, z ), v( mid, hdr_n, z ), 1.6, "rv_louvre", 10, caps=False )
                P.disc_ring( m, v( mid, cn + sn * 34.0, z ), v( mid, cn + sn * 35.2, z ), 3.2, "rv_louvre", 12 )
                P.disc_ring( m, v( mid, cn + sn * 36.6, z ), v( mid, cn + sn * 37.8, z ), 2.6, "rv_dark", 10 )
    # Bushings: three HV ones in a row along the lid, shedded brown porcelain on a flange with a metal cap and stud; four
    # small LV ones on the other side of the lid.
    def bushing( e, n, z0, h, core, shed ):
        prof = [ ( core * 1.9, z0 ), ( core * 1.9, z0 + 2.0 ), ( core, z0 + 2.0 ) ]
        pitch = 3.0 if h > 20 else 2.4
        z = z0 + 3.0
        while z + pitch < z0 + h - 2.0:
            prof += [ ( core, z ), ( shed, z + 0.5 ), ( shed * 0.92, z + 1.1 ), ( core, z + 1.7 ) ]
            z += pitch
        prof += [ ( core, z0 + h - 2.0 ) ]
        P.lathe( m, ( e, n ), prof, "rv_porcelain", 16 )
        P.lathe( m, ( e, n ), [ ( core * 1.15, z0 + h - 2.0 ), ( core * 1.15, z0 + h + 1.0 ), ( core * 0.4, z0 + h + 1.0 ),
                                ( core * 0.4, z0 + h + 4.0 ), ( 0.0, z0 + h + 4.0 ) ], "rv_zinc", 12 )
    for k in range( 3 ):
        bushing( ce - 26 + k * 26, cn - 4, 103.0, 40.0, 2.6, 5.4 )
    for k in range( 4 ):
        bushing( ce - 30 + k * 20, cn - 24, 103.0, 13.0, 1.5, 3.0 )


def court( m, sx ):
    """ The court north of the annex: a transformer, tanks, a pipe rack and cover. """
    f = -sx
    # Transformer: a tank with radiator fins and bushings, on a plinth.
    c = ( f * -1420, 640 )
    box( m, c[0] - 70, c[0] + 70, c[1] - 50, c[1] + 50, 0, 10, "rv_plinth", STONE )
    box( m, c[0] - 50, c[0] + 50, c[1] - 34, c[1] + 34, 10, 100, "rv_louvre", METAL )
    transformer( m, c )
    P.railing( m, mirror_pts( [ ( -1520, 560 ), ( -1320, 560 ), ( -1320, 720 ), ( -1520, 720 ) ], f ), 0, "rv_yellow", height=40,
               closed=True, clip_to=40, name="transformer fence" )
    # A pair of tanks against the hall wall.
    for n in ( 1350.0, 1490.0 ):
        P.tank( m, ( f * -1110, n ), 56, 280, "rv_white", facing=( -f, 0 ) )
    # Pipe rack across the court at 260, from the hall's wall to the annex roof.
    for n in ( 980.0, 1700.0 ):
        for e in ( -1640.0, -1360.0, -1080.0 ):
            box( m, *sorted( ( f * ( e - 5 ), f * ( e + 5 ) ) ), n - 5, n + 5, 0, 270, "rv_steel", METAL )
        P.i_beam( m, ( f * -1650, n, 270 ), ( f * -1040, n, 270 ), 12, 8, "rv_steel" )
    for k, r in enumerate( ( 9.0, 6.0, 6.0, 4.0 ) ):
        n = 990 + k * 30 if k < 2 else 1380 + k * 20
        P.pipe( m, mirror_pts( [ ( -1700, 1000 + k * 26, 288 ), ( -1040, 1000 + k * 26, 288 ) ], f ), r, "rv_pipe", 12, caps=False )
    for k, r in enumerate( ( 8.0, 5.0 ) ):
        P.pipe( m, mirror_pts( [ ( -1660, 1000 + k * 26, 288 ), ( -1660, 1700, 288 ), ( -1660, 2060, 288 ) ], f ), r, "rv_pipe", 12, caps=False )
    # The rack's feet and knee braces, cross beams the pipes rest on in their shoes, flanges, blind flanges on the open
    # ends and sleeves where they go into the hall.
    for n in ( 980.0, 1700.0 ):
        for e in ( -1640.0, -1360.0, -1080.0 ):
            F.base_plate( m, f * e, n, 10.0 )
            for de in ( -1, 1 ):
                if -1650 <= e + de * 40 <= -1040:
                    m.beam( v( f * ( e + de * 5 ), n, 222 ), v( f * ( e + de * 40 ), n, 264 ), ( 2.5, 2.5 ), "rv_steel" )
    for e in ( -1640.0, -1360.0, -1080.0 ):
        P.i_beam( m, ( f * e, 975, 276 ), ( f * e, 1095, 276 ), 8, 6, "rv_steel" )
    for k, r in enumerate( ( 9.0, 6.0, 6.0, 4.0 ) ):
        nn = 1000 + k * 26
        a, b = v( f * -1700, nn, 288 ), v( f * -1040, nn, 288 )
        F.flanges( m, a, b, r, every=220.0, start=100.0 + 30 * k )
        P.disc_ring( m, a - v( f * 1.0, 0, 0 ), a + v( f * 1.5, 0, 0 ), r * 1.35, "rv_steel", 12 )
        P.disc_ring( m, b - v( f * 3.0, 0, 0 ), b, r * 1.3, "rv_steel", 12 )
        for e in ( -1640.0, -1360.0, -1080.0 ):
            F.shoe( m, ( f * e, nn, 288 ), r, ( 1, 0 ) )
    # The transformer's conservator on its brackets, the pipe down to the tank, a cable box and its sign.
    P.rod( m, v( c[0] - 40, c[1] + 20, 154 ), v( c[0] + 40, c[1] + 20, 154 ), 10.0, "rv_steel", 14, caps=True )
    for de in ( -30.0, 30.0 ):
        box( m, c[0] + de - 2, c[0] + de + 2, c[1] + 16, c[1] + 24, 100, 145, "rv_steel" )
    P.pipe( m, [ ( c[0] + 28, c[1] + 20, 146 ), ( c[0] + 28, c[1] + 20, 122 ), ( c[0] + 28, c[1] + 8, 100 ) ], 1.6, "rv_steel", 8, caps=False )
    end = c[0] - f * 50
    box( m, *sorted( ( end, end - f * 7 ) ), c[1] - 20, c[1] + 20, 30, 82, "rv_steel" )
    P.plate( m, "danger", ( end - f * 7, c[1], 66 ), np.cross( UP, v( -f, 0, 0 ) ), 12, off=0.3 )
    P.rod( m, v( end - f * 3.5, c[1], 30 ), v( end - f * 3.5, c[1], 10 ), 2.5, "rv_black", 8 )
    # Cover: barriers and cases.
    P.jersey( m, ( f * -1250, 900 ), ( 1, 0 ) )
    P.jersey( m, ( f * -1500, 1080 ), ( 0, 1 ) )
    P.jersey( m, ( f * -1350, 1560 ), ( 1, 0.2 ) )
    P.jersey( m, ( f * -1250, 1880 ), ( 0, 1 ) )
    for k, ( e, n ) in enumerate( ( ( -1620, 840 ), ( -1180, 420 ), ( -1600, 1560 ), ( -1200, 1980 ), ( -1560, 1940 ) ) ):
        P.case_stack( m, ( f * e, n ), ( 1, 0 ), "olive", seed=60 + k + ( 0 if sx < 0 else 50 ) )
    P.wall_light( m, f"Court lamp {sx} a", ( f * ( H.E0 - H.WT ), 900, 260 ), v( -f, 0, 0 ), "warm", 420 )
    P.wall_light( m, f"Court lamp {sx} b", ( f * ( H.E0 - H.WT ), 1450, 260 ), v( -f, 0, 0 ), "warm", 420 )
    P.wall_light( m, f"Court lamp {sx} c", ( f * ( H.E0 - H.WT ), 1900, 260 ), v( -f, 0, 0 ), "warm", 420 )


def yard_side( m, sx ):
    """ One side of the yard: a container (the east one the reference's red 02, the west one blue 04), grey containers,
    the forklift, the turbine building block with its sign, a pipe bridge from it to the annex, barriers, cases,
    bollards, light masts and floor markings. """
    import lowtide_container as LC
    import lowtide_forklift as LF
    f = -sx
    paint = "rw_container_red" if sx > 0 else "rw_container_blue"
    num = "n02" if sx > 0 else "n04"
    ce, cn = f * -1000, -1180
    LC.build( m, ce, cn, 0, "20", "e", paint, door_end=f )
    # Its number, big on its long sides and on the end towards the yard's middle.
    for sn in ( -1, 1 ):
        out = v( 0, sn, 0 )
        P.letters( m, num, ( ce - f * 40, cn + sn * 48.9, 66 ), np.cross( UP, out ), 44, "light" )
    LC.build( m, f * -760, -1520, 0, "20", "n", "rw_container_grey", door_end=1 )
    LC.build( m, f * -1560, -1080, 0, "20", "n", "rw_container_grey", door_end=-1 )
    LF.build( m, f * -1560, -760, "+e" if f < 0 else "-e" )
    # The turbine building's block on the yard's south edge (turbine_block draws its faces), and big pipes from it
    # over its roof to the spawn building on a gantry, high over the yard's edge: the reference's pipes overhead on
    # its right.
    turbine_block( m, sx )
    g0, g1 = TURBINE_SIDE[3] - 20, TURBINE_SIDE[3] + 90
    for e in ( -1880.0, -2040.0 ):
        for nn in ( g0, g1 ):
            box( m, *sorted( ( f * ( e - 6 ), f * ( e + 6 ) ) ), nn - 6, nn + 6, 0, 380, "rv_steel", METAL )
            F.base_plate( m, f * e, nn, 12.0 )
    for nn in ( g0, g1 ):
        P.i_beam( m, ( f * TURBINE_SIDE[0], nn, 380 ), ( f * SPAWN_TALL[1], nn, 380 ), 14, 8, "rv_steel" )
    for e in np.arange( -2020.0, -1720.0, 75.0 ):
        P.i_beam( m, ( f * e, g0 - 4, 390 ), ( f * e, g1 + 4, 390 ), 6, 6, "rv_steel" )
    face = f * TURBINE_SIDE[1]
    # The three lines leave the wall as one bank: the same exit height and a 46 in centreline standoff, so each elbow
    # has a straight leg either side of it (at 28 in the elbows met and every line read as a closed loop), held at two
    # levels on a steel channel bracketed off the wall, with a clamp band round each line.
    standoff, zin = 46.0, 300.0
    rises = ( -1345, -1302, -1270 )
    for k, ( dn, r, rise ) in enumerate( ( ( 0, 18.0, rises[0] ), ( 40, 13.0, rises[1] ), ( 72, 9.0, rises[2] ) ) ):
        n_ = g0 + 12 + dn
        out = face + f * standoff
        run = [ ( face - f * 10, rise, zin ), ( out, rise, zin ), ( out, rise, 472 ), ( face - f * 90, rise, 472 ),
                ( face - f * 150, n_, 472 ), ( f * TURBINE_SIDE[0], n_, 472 ), ( f * TURBINE_SIDE[0] - f * 60, n_, 394 + r ),
                ( f * SPAWN_TALL[1] - f * 30, n_, 394 + r ), ( f * SPAWN_TALL[1] - f * 30, n_, 300 ) ]
        P.pipe( m, run, r, "rv_pipe", 14, caps=False )
        P.disc_ring( m, v( face - f * 0.5, rise, zin ), v( face + f * 3.0, rise, zin ), r * 1.3, "rv_steel", 14 )
        F.flanges( m, run[5], run[6], r, every=400.0, start=60.0 )
        F.flanges( m, run[7], run[8], r, every=400.0, start=30.0 )
        for z in ( 365.0, 420.0 ):
            # A spacer from the channel to the line's back, and the clamp band round it.
            box( m, *sorted( ( face + f * 25.0, face + f * ( standoff - r + 0.5 ) ) ), rise - 2.5, rise + 2.5, z - 2.5, z + 2.5,
                 "rv_steel" )
            P.disc_ring( m, v( out, rise, z - 1.2 ), v( out, rise, z + 1.2 ), r + 0.7, "rv_steel", 16 )
    for z in ( 365.0, 420.0 ):
        # The channel along the wall behind the bank, on an arm off the wall at each end and one between.
        n0, n1 = rises[0] - 28.0, rises[2] + 20.0
        box( m, *sorted( ( face + f * 19.0, face + f * 25.0 ) ), n0, n1, z - 4.0, z + 4.0, "rv_steel" )
        for na in ( n0 + 3.0, ( rises[0] + rises[1] ) / 2, n1 - 3.0 ):
            box( m, *sorted( ( face + f * 0.5, face + f * 19.0 ), ), na - 2.5, na + 2.5, z - 3.0, z + 3.0, "rv_steel" )
            box( m, *sorted( ( face + f * 0.5, face + f * 2.0 ) ), na - 6.0, na + 6.0, z - 8.0, z + 8.0, "rv_steel" )
    # Barriers.
    for e, n, along in ( ( -1300, -1000, ( 0, 1 ) ), ( -1150, -800, ( 1, 0 ) ), ( -820, -1180, ( 0, 1 ) ), ( -1640, -1350, ( 1, 0 ) ),
                         ( -980, -1460, ( 1, 0.1 ) ), ( -640, -1140, ( 0, 1 ) ), ( -1060, -760, ( 1, -0.3 ) ), ( -1400, -880, ( 1, 0.3 ) ) ):
        P.jersey( m, ( f * e, n ), ( f * along[0], along[1] ) )
    # Cases.
    for k, ( e, n ) in enumerate( ( ( -1520, -680 ), ( -1600, -700 ), ( -1220, -680 ), ( -900, -1300 ), ( -1180, -1330 ), ( -860, -940 ),
                                    ( -760, -1000 ), ( -1250, -1560 ), ( -1680, -1220 ), ( -980, -1660 ), ( -1460, -1180 ) ) ):
        P.case_stack( m, ( f * e, n ), ( 1, 0.05 * k ), "olive" if k % 3 else "dark", seed=80 + k + ( 0 if sx < 0 else 70 ) )
    for e in ( -1455.0, -1165.0 ):
        P.bollard( m, f * e, -642 )
    # Light masts with floodlights.
    for e, n in ( ( -1240, -1700 ), ( -620, -1700 ) ):
        P.cylinder( m, ( f * e, n ), 5, 0, 460, "rv_zinc", 10, surface=METAL )
        box( m, f * e - 30, f * e + 30, n - 4, n + 4, 452, 458, "rv_zinc" )
        for de in ( -22, 0, 22 ):
            P.obox( m, ( f * e + de, n + 6, 446 ), ( 1, 0 ), ( 16, 6, 12 ), "rv_dark" )
            card( m, "rv_lamp_warm", [ v( f * e + de - 7, n + 9.1, 441 ), v( f * e + de + 7, n + 9.1, 441 ), v( f * e + de + 7, n + 9.1, 451 ), v( f * e + de - 7, n + 9.1, 451 ) ], v( 0, 1, 0 ) )
        P.LIGHTS.append( ( f"Yard mast {sx} {e}", ( f * e, n + 60, 420 ), "1.00,0.80,0.55,1", 900, False ) )
    # Floor markings: yellow lane lines and a hatched strip at the annex's opening.
    for e0_, e1_, n0_, n1_ in ( ( -1700, -480, -668, -664 ), ( -1300, -560, -1210, -1206 ), ( -1300, -560, -1226, -1222 ), ( -870, -866, -1700, -1240 ) ):
        a, b = sorted( ( f * e0_, f * e1_ ) )
        box( m, a, b, n0_, n1_, 0, 0.3, { "default": None, "+z": "rv_line_yellow" } )
    a, b = sorted( ( f * -1450, f * -1170 ) )
    box( m, a, b, -660, -636, 0, 0.35, { "default": None, "+z": "rv_hazard" } )


def turbine_block( m, sx ):
    """ The turbine building's block on the yard's south edge (TURBINE_SIDE): a concrete base under blue-grey steel
    cladding, its sign towards the yard's middle over a door, a roller shutter in its loading bay, louvres in the
    cladding, downpipes, and on the roof plant behind the parapet. """
    f = -sx
    t0, t1 = sorted( ( f * TURBINE_SIDE[0], f * TURBINE_SIDE[1] ) )
    n0, n1 = TURBINE_SIDE[2], TURBINE_SIDE[3]
    top, clad = 450.0, 220.0
    yard, spawn = ( "+e", "-e" ) if f > 0 else ( "-e", "+e" )      # the faces towards the yard's middle and the spawn
    box( m, t0, t1, n0, n1, 0, 420, { "default": None, "+z": "rv_plinth" }, STONE )
    for a, b, inner in ( ( t0, t0 + 10, "+e" ), ( t1 - 10, t1, "-e" ) ):
        box( m, a, b, n0, n1, 420, top, { "default": None, inner: "rv_wall" }, STONE )
        F.coping( m, a, b, n0, n1, top )
    box( m, t0, t1, n1 - 10, n1, 420, top, { "default": None, "-n": "rv_wall" }, STONE )
    F.coping( m, t0, t1, n1 - 10, n1, top )
    # The yard face.
    y = F.Face( m, yard, f * TURBINE_SIDE[1], n0, n1, 0, top )
    y.zone( clad, top, F.CLAD, ribs=True )
    y.corner_trims = ( None, True )
    bay0, bay1 = -1636.0, -1474.0
    y.shutter( bay0, bay1, 0, 180 )
    y.guard( bay0, -1, 72 )
    y.guard( bay1, 1, 72 )
    y.door( -1340, 60, 92, double=False, canopy=30, paint="rv_fc_door_blue" )
    y.louvre( -1610, -1450, 290, 380 )
    y.plinth( wrap=( False, True ) )
    y.grime_foot()
    y.downpipe( -1690, top - 2 )
    y.finish()
    y.letters( "turbine_r" if sx > 0 else "turbine_l", -1350, 165, 80 )
    y.lamp( f"Turbine bay lamp {sx}", ( bay0 + bay1 ) / 2, 214, "warm", 380, light=True )
    y.lamp( f"Turbine sign lamp {sx}", -1350, 236, "warm", 320, light=True )
    y.cabinet( -1430, 30, 24, 40 )
    y.conduit( [ ( -1430, 70 ), ( -1430, 104 ), ( -1452, 120 ), ( -1452, clad - 4 ) ] )
    y.camera( -1722, 330, turn=25 )
    y.sign( "danger", -1455, 100, 16 )
    P.beacon( m, f"Turbine block beacon {sx}", y.p( -1262, top + 2.0, -5 ) )
    # The north face, towards the annex.
    nf = F.Face( m, "+n", n1, t0, t1, 0, top )
    nf.zone( clad, top, F.CLAD, ribs=True )
    nf.corner_trims = ( True, True )
    nf.louvre( *sorted( ( f * -1610, f * -1390 ) ), 230, 370 )
    nf.door( f * -1500, 80, 96, double=False, canopy=32 )
    nf.plinth()
    nf.grime_foot()
    nf.downpipe( f * -1680, top - 2 )
    nf.finish()
    nf.lamp( f"Turbine block door lamp {sx}", f * -1500, 126, "warm", 300, light=True )
    nf.cabinet( f * -1420, 30, 26, 42 )
    nf.conduit( [ ( f * -1420, 72 ), ( f * -1420, clad - 4 ) ] )
    nf.sign( "notice", f * -1560, 64, 18 )
    nf.camera( f * -1330, 300, turn=20 * f )
    # The spawn face.
    w = F.Face( m, spawn, f * TURBINE_SIDE[0], n0, n1, 0, top )
    w.zone( clad, top, F.CLAD, ribs=True )
    w.corner_trims = ( None, True )
    w.door( -1460, 66, 92, double=False, canopy=30 )
    w.louvre( -1660, -1540, 280, 360 )
    w.plinth( wrap=( False, True ) )
    w.grime_foot()
    w.downpipe( -1272, top - 2 )
    w.finish()
    w.lamp( f"Turbine block spawn door lamp {sx}", -1460, 122, "warm", 280 )
    w.cabinet( -1540, 30, 26, 44, plate="notice" )
    # On the roof, behind the parapet, under the pipes.
    F.roof_unit( m, ( f * -1530, -1560 ), ( 0, 1 ), 420, ( 120, 64, 50 ) )
    F.roof_fan( m, ( f * -1420, -1660 ), 420 )
    F.roof_fan( m, ( f * -1640, -1380 ), 420 )
    F.roof_vent( m, ( f * -1380, -1480 ), 420 )


def spawn_side( m, sx ):
    """ The spawn strip (west e -2300..-1700): the boundary building's facade, the spawn building (B2 west, B1 east:
    the reference's, a stair up past its stencilled wing to a double door), a guard hut, barriers and lamps. """
    f = -sx

    def E( a, b ):
        return tuple( sorted( ( f * a, f * b ) ) )

    yard = "+e" if f > 0 else "-e"          # the faces towards the yard
    e_face = f * PLAY[0]
    a, b = E( PLAY[0], PLAY[0] - 300 )
    box( m, a, b, PLAY[2], PLAY[3], 0, BOUNDARY_TOP, { "default": "rv_wall", yard: None, "+z": "rv_plinth" }, STONE )
    for n in np.arange( PLAY[2] + 120, PLAY[3] - 60, 300.0 ):
        box( m, *sorted( ( e_face, e_face + f * 14 ) ), n - 22, n + 22, 0, BOUNDARY_TOP + 20, "rv_wall", STONE )
        F.coping( m, *sorted( ( e_face, e_face + f * 14 ) ), n - 22, n + 22, BOUNDARY_TOP + 20, over=1.5 )
    boundary_face( m, sx )
    # The spawn building's tall part: walls, the room's floor and roof. Its outer faces (and the walls' ends and the
    # doors' reveals, which would lie in them) are drawn by spawn_faces.
    t0, t1, tn0, tn1 = SPAWN_TALL
    w = 20.0
    door_a = ( -940.0, -870.0, SPAWN_ROOM_Z + 96, SPAWN_ROOM_Z )
    door_b = ( -800.0, -740.0, SPAWN_ROOM_Z + 96, SPAWN_ROOM_Z )
    H.wall( m, "n", tn0, tn1, *E( t1 - w, t1 ), 0, SPAWN_TOP, [ door_a, door_b ],
            paint={ "default": "rv_wall", yard: None, "-n": None, "+n": None } )
    H.wall( m, "e", *E( t0, t1 ), tn0, tn0 + w, 0, SPAWN_TOP, paint={ "default": "rv_wall", "-n": None, yard: None } )
    H.wall( m, "e", *E( t0, t1 ), tn1 - w, tn1, 0, SPAWN_TOP, paint={ "default": "rv_wall", "+n": None, yard: None } )
    box( m, *E( t0, t1 - w ), tn0 + w, tn1 - w, 0, SPAWN_ROOM_Z - 16, "rv_wall", STONE )
    box( m, *E( t0, t1 - w ), tn0 + w, tn1 - w, SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z, { "default": None, "+z": "rv_floor" }, STONE )
    box( m, *E( t0, t1 ), tn0, tn1, SPAWN_TOP - 18, SPAWN_TOP, { "default": None, "+z": "rv_plinth", "-z": "rv_steel" }, STONE )
    inward = "-e" if f > 0 else "+e"
    for ( a_, b_, c_, d_ ), inner in ( ( ( t0, t1, tn0, tn0 + 10 ), "+n" ), ( ( t0, t1, tn1 - 10, tn1 ), "-n" ),
                                       ( ( t1 - 10, t1, tn0, tn1 ), inward ) ):
        box( m, *E( a_, b_ ), c_, d_, SPAWN_TOP, SPAWN_TOP + 26, { "default": None, inner: "rv_wall" }, STONE )
        F.coping( m, *E( a_, b_ ), c_, d_, SPAWN_TOP + 26 )
    P.ceiling_light( m, f"Spawn room {sx}", ( f * ( t0 + t1 ) / 2, ( tn0 + tn1 ) / 2, SPAWN_TOP - 26 ), ( 0, 1 ), "cool", 380 )
    for k, n in enumerate( ( -1100.0, -1040.0, -980.0 ) ):
        box( m, *E( t0 + 4, t0 + 24 ), n - 26, n + 26, SPAWN_ROOM_Z, SPAWN_ROOM_Z + 80, "rv_steel", METAL )
    P.case_stack( m, ( f * -2200, -760 ), ( 0, 1 ), "dark", seed=150 + sx )
    # The wing (its roof part of the upper deck), the landing and the stair.
    box( m, *E( SPAWN_WING[0], SPAWN_WING[1] ), SPAWN_WING[2], SPAWN_WING[3], 0, SPAWN_ROOM_Z, { "default": None, "+z": "rv_floor" }, STONE )
    box( m, *E( SPAWN_LANDING[0], SPAWN_LANDING[1] ), SPAWN_LANDING[2], SPAWN_LANDING[3], SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z,
         { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    box( m, *E( SPAWN_LANDING[1] - 12, SPAWN_LANDING[1] ), SPAWN_LANDING[2], SPAWN_LANDING[2] + 12, 0, SPAWN_ROOM_Z - 16, "rv_wall", STONE )
    mid = ( SPAWN_STAIR[2] + SPAWN_STAIR[3] ) / 2
    P.stairs( m, ( f * SPAWN_STAIR[0], mid ), ( f * SPAWN_STAIR[1], mid ), SPAWN_STAIR[3] - SPAWN_STAIR[2], 0, SPAWN_ROOM_Z,
              tread="rv_plinth", side="rv_plinth", solid_under=True, surface=STONE, name=f"spawn stair {sx}" )
    P.railing( m, mirror_pts( [ ( SPAWN_LANDING[1], -884 ), ( SPAWN_LANDING[1], -840 ), ( SPAWN_WING[1], -840 ), ( SPAWN_WING[1], -690 ),
                                ( SPAWN_WING[0], -690 ) ], f ), SPAWN_ROOM_Z, clip_to=160, name=f"spawn deck rail {sx}" )
    P.railing( m, mirror_pts( [ ( SPAWN_LANDING[1], -960 ), ( SPAWN_LANDING[0], -960 ) ], f ), SPAWN_ROOM_Z, clip_to=160,
               name=f"spawn landing rail {sx}" )
    spawn_faces( m, sx, door_a, door_b )
    P.beacon( m, f"Spawn beacon {sx}", ( f * t1 - f * 5, tn1 - 10, SPAWN_TOP + 28 ) )
    # Guard hut and barriers.
    he = f * -2120
    box( m, he - 50, he + 50, -1500, -1400, 0, 110, { "default": "rv_white", "+z": "rv_steel" }, METAL )
    guard_hut( m, he, f )
    for e, n, along in ( ( -1880, 650, ( 0, 1 ) ), ( -2050, 900, ( 1, 0 ) ), ( -1950, -1300, ( 1, 0.2 ) ), ( -1800, -1450, ( 0, 1 ) ) ):
        P.jersey( m, ( f * e, n ), along )
    for k, ( e, n ) in enumerate( ( ( -2220, 700 ), ( -2230, 1200 ), ( -1780, 1500 ), ( -2200, 1800 ) ) ):
        P.case_stack( m, ( f * e, n ), ( 0, 1 ), "olive", seed=110 + k + ( 0 if sx < 0 else 30 ) )
    for n in ( -1300.0, 0.0, 1300.0 ):
        e = f * -1760
        P.cylinder( m, ( e, n ), 4, 0, 360, "rv_zinc", 10, surface=METAL )
        P.obox( m, ( e, n, 360 ), ( 1, 0 ), ( 20, 10, 8 ), "rv_dark" )
        card( m, "rv_lamp_warm", [ v( e - 8, n - 4, 355.9 ), v( e + 8, n - 4, 355.9 ), v( e + 8, n + 4, 355.9 ), v( e - 8, n + 4, 355.9 ) ], -UP )
        P.LIGHTS.append( ( f"Spawn mast {sx} {n}", ( e, n, 330 ), "1.00,0.80,0.55,1", 700, False ) )


def boundary_face( m, sx ):
    """ The boundary building's face towards the spawn and the court (riverdale_facades): bays between its piers, each
    with a window upstairs and a door or a louvre at the foot, a plinth, a precast band at the floor, a parapet with its
    coping over the roof's edge, downpipes beside every other pier, and what's fixed to the wall. """
    f = -sx
    yard = "+e" if f > 0 else "-e"
    e_face = f * PLAY[0]
    top = BOUNDARY_TOP + 20
    # The parapet over the roof's edge, drawn only (the roof is clipped).
    box( m, *sorted( ( e_face, e_face - f * 10 ) ), PLAY[2], PLAY[3], BOUNDARY_TOP, top, { "default": "rv_wall", yard: None, "-z": None } )
    F.coping( m, *sorted( ( e_face, e_face - f * 10 ) ), PLAY[2], PLAY[3], top )
    bf = F.Face( m, yard, e_face, PLAY[2], PLAY[3], 0, top )
    bf.exclude( SPAWN_TALL[2], SPAWN_TALL[3], 0, top )
    piers = np.arange( PLAY[2] + 120, PLAY[3] - 60, 300.0 )
    bays = [ ( k, n ) for k, n in enumerate( np.arange( PLAY[2] + 270, PLAY[3] - 200, 300.0 ) )
             if not SPAWN_TALL[2] - 100 < n < SPAWN_TALL[3] + 100 ]
    for k, n in bays:
        lit = k % 4 == 1
        bf.window( n - 75, n + 75, 225, 295, 7.0, pitch=50, room="corridor" if k % 2 else "office", lit=lit,
                   blind=( 0.2, 0.55, 0.0, 0.35 )[k % 4] )
        if k % 3 == 1:
            bf.door( n, 96, 100, canopy=40 )
        else:
            bf.louvre( n - 60, n + 60, 55, 145 )
    bf.plinth()
    bf.band( 186, 8, 2.0 )
    bf.grime_foot()
    bf.grime_top( PLAY[2], PLAY[3], BOUNDARY_TOP + 18, 96 )
    for j, n in enumerate( piers ):
        if j % 2 == 0 and not SPAWN_TALL[2] - 40 < n + 30 < SPAWN_TALL[3] + 10:
            bf.downpipe( n + 30, top - 2 )
    bf.finish()
    for k, n in bays:
        if k % 3 == 1:
            bf.lamp( f"Spawn door lamp {sx} {k}", n, 136, "warm", 360, light=True )
            bf.jbox( n + 70, 112 )
            bf.conduit( [ ( n + 70, 118 ), ( n + 70, 184 ) ] )
            bf.sign( "notice", n - 72, 62, 18 )
        elif k % 2 == 0:
            bf.cabinet( n + 92, 30, 26, 44, plate="danger" if k % 4 == 0 else None )
            bf.conduit( [ ( n + 92, 74 ), ( n + 92, 184 ) ] )
        if k % 4 == 2:
            bf.camera( n + 110, 330, turn=-30 )


def spawn_faces( m, sx, door_a, door_b ):
    """ The spawn building's faces (riverdale_facades): concrete below its room's floor, blue-grey cladding round the
    room, its doors from the deck with their canopies, a ribbon window towards the spawn, louvres and a shutter at the
    foot; and its wing's faces with the building's name over a door. """
    f = -sx
    t0, t1, tn0, tn1 = SPAWN_TALL
    top = SPAWN_TOP + 26
    clad = SPAWN_ROOM_Z + 4
    yard = "+e" if f > 0 else "-e"
    label = "B1" if sx > 0 else "B2"
    trims = ( None, True ) if f > 0 else ( True, None )        # no trim where it meets the boundary building
    to_yard = ( f < 0, f > 0 )                                   # wrap round the corner towards the yard only

    def U( a, b ):
        return tuple( sorted( ( f * a, f * b ) ) )

    # Towards the yard: the doors from the deck, a window, at the foot a louvre and a cabinet.
    y = F.Face( m, yard, f * t1, tn0, tn1, 0, top )
    y.zone( clad, top, F.CLAD, ribs=True )
    y.corner_trims = ( True, True )
    y.exclude( SPAWN_WING[2], SPAWN_WING[3], 0, SPAWN_ROOM_Z )
    y.exclude( SPAWN_LANDING[2], SPAWN_LANDING[3], SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z )
    for d_ in ( door_a, door_b ):
        y.door( ( d_[0] + d_[1] ) / 2, 66 if d_ is door_a else 56, 92, z=SPAWN_ROOM_Z, double=d_ is door_a, canopy=30,
                through=( d_[0], d_[1] ) )
        y.later.append( lambda d_=d_: y.reveal( d_[0], d_[1], d_[3], d_[2], 20.0, "rv_wall", ( True, True, False, False ), d0=1.5 ) )
    y.window( -1130, -1010, 252, 330, 7.0, pitch=40, room="office", lit=True, blind=0.3 )
    y.louvre( -1130, -1010, 50, 150 )
    y.plinth( wrap=( True, False ) )
    y.grime_foot()
    y.downpipe( -1146, top - 2 )
    y.finish()
    y.sign( "door_sign", -985, SPAWN_ROOM_Z + 54, 14 )
    y.lamp( f"Spawn door lamp {sx}", -905, SPAWN_ROOM_Z + 118, "warm", 300, light=True )
    y.lamp( f"Spawn upper lamp {sx}", -770, SPAWN_ROOM_Z + 118, "warm", 280, light=True )
    y.cabinet( -985, 30, 26, 44 )
    y.conduit( [ ( -985, 74 ), ( -985, SPAWN_ROOM_Z - 18 ) ] )
    y.camera( -1140, 372, turn=30 )
    # Towards the spawn: a ribbon window lighting the room, a shutter and a door at the foot.
    nf = F.Face( m, "+n", tn1, f * t0, f * t1, 0, top )
    nf.zone( clad, top, F.CLAD, ribs=True )
    nf.corner_trims = trims
    nf.window( *U( -2272, -2088 ), 238, 322, 8.0, pitch=46, room="office", lit=True, blind=0.35, sill=None )
    nf.shutter( *U( -2272, -2160 ), 0, 140 )
    nf.door( f * -2110, 44, 88, double=False, canopy=26 )
    nf.plinth( wrap=( False, False ) )
    nf.grime_foot()
    nf.downpipe( f * -2286, top - 2 )
    nf.finish()
    nf.sign( "danger", f * -2128, 120, 12 )
    nf.lamp( f"Spawn north lamp {sx}", f * -2216, 160, "warm", 300 )
    # Towards the turbine block.
    s = F.Face( m, "-n", tn0, f * t0, f * t1, 0, top )
    s.zone( clad, top, F.CLAD, ribs=True )
    s.corner_trims = trims
    for a, b in ( ( -2250, -2190 ), ( -2160, -2100 ) ):
        s.window( *U( a, b ), 250, 320, 7.0, room="plant", sill=None )
    s.louvre( *U( -2262, -2162 ), 60, 140 )
    s.plinth( wrap=to_yard )
    s.grime_foot()
    s.downpipe( f * -2076, top - 2 )
    s.finish()
    s.cabinet( f * -2120, 30, 26, 40 )
    # The wing: the building's name over a door towards the yard, a louvre towards the spawn, its deck's edge.
    wn = ( SPAWN_WING[2] + SPAWN_WING[3] ) / 2
    wy = F.Face( m, yard, f * SPAWN_WING[1], SPAWN_WING[2], SPAWN_WING[3], 0, SPAWN_ROOM_Z )
    wy.door( wn, 64, 84, double=False, glazed=False, paint="rv_door_yellow" )
    wy.plinth()
    wy.band( SPAWN_ROOM_Z - 12, 12, 2.0, drip=True )
    wy.grime_foot()
    wy.finish()
    wy.letters( label, wn, 152, 66 )
    wy.lamp( f"Spawn wing lamp {sx}", wn, 100, "warm", 260, light=True )
    wn_ = F.Face( m, "+n", SPAWN_WING[3], *U( SPAWN_WING[0], SPAWN_WING[1] ), 0, SPAWN_ROOM_Z )
    wn_.louvre( *U( -2030, -1950 ), 60, 140 )
    wn_.plinth( wrap=to_yard )
    wn_.band( SPAWN_ROOM_Z - 12, 12, 2.0, wrap=to_yard, drip=True )
    wn_.grime_foot()
    wn_.finish()
    ws = F.Face( m, "-n", SPAWN_WING[2], *U( SPAWN_WING[0], SPAWN_WING[1] ), 0, SPAWN_ROOM_Z )
    ws.exclude( *U( SPAWN_LANDING[0], SPAWN_LANDING[1] ), SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z )
    ws.plinth( wrap=to_yard )
    ws.band( SPAWN_ROOM_Z - 12, 12, 2.0, wrap=to_yard, drip=True )
    ws.grime_foot()
    ws.finish()
    ws.cabinet( f * -1960, 30, 26, 44, plate="notice" )


def guard_hut( m, he, f ):
    """ The guard hut's dressing: a roof overhanging on all sides, a framed window towards the yard, a door, an air
    conditioner on the roof. """
    box( m, he - 56, he + 56, -1506, -1394, 110, 114, { "default": "rv_fc_flashing", "-z": "rv_steel" } )
    yard = "+e" if f > 0 else "-e"
    w = F.Face( m, yard, he + f * 50, -1500, -1400, 0, 110 )
    w.box( -1489, -1411, 46, 94, 0, 0.6, "rv_frame" )
    w.rect( F.room_paint( "office", True ), -1487, -1413, 48, 92, 0.7, uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] )
    w.box( -1491, -1409, 42, 46, 0, 2.5, "rv_steel" )
    n = F.Face( m, "+n", -1400, he - 50, he + 50, 0, 110 )
    P.door( m, n.p( he - f * 20, 0, 0 ), n.right, 36, 82, paint="rv_fc_door_blue", double=False, mount="surface" )
    P.obox( m, ( he, -1450, 122 ), ( 1, 0 ), ( 30, 22, 16 ), { "default": "rv_white", "+z": "rv_fc_flashing" } )
    P.cylinder( m, ( he, -1450 ), 8.0, 130, 130.6, "rv_black", 12, top="rv_black" )


# ---------------------------------------------------------------------------------------------------------------------
# The yard's middle: B1 and the turbine building's annex

def b1( m, glass ):
    c0, c1, n0, n1 = CORE
    t = 24.0
    up_door = ( -930.0, -860.0, ROOM_Z + 96, ROOM_Z )
    # The walls' outer faces, and their ends and reveals that would lie in them, are drawn by b1_faces.
    H.wall( m, "e", c0, c1, n1 - t, n1, 0, CORE_TOP, [ ( -60.0, 60.0, 150.0 ) ], paint={ "default": "rv_wall", "+n": None, "-e": None, "+e": None } )
    H.wall( m, "e", c0, c1, n0, n0 + t, 0, CORE_TOP, [ ( -60.0, 60.0, 150.0 ) ], paint={ "default": "rv_wall", "-n": None, "-e": None, "+e": None } )
    for sx in ( -1, 1 ):
        a, b = sorted( ( sx * c1, sx * ( c1 - t ) ) )
        outer = "+e" if sx > 0 else "-e"
        H.wall( m, "n", n0 + t, n1 - t, a, b, 0, CORE_TOP, [ up_door ], paint={ "default": "rv_wall", outer: None, "-n": None, "+n": None } )
    # Upper floor, roof, parapets and their copings.
    box( m, c0 + t, c1 - t, n0 + t, n1 - t, ROOM_Z - 16, ROOM_Z, { "default": "rv_wall", "+z": "rv_floor", "-z": "rv_steel" }, STONE )
    box( m, c0, c1, n0, n1, CORE_TOP - 20, CORE_TOP, { "default": None, "+z": "rv_plinth", "-z": "rv_steel" }, STONE )
    for ( a, b, c, d ), inner in ( ( ( c0, c1, n0, n0 + 10 ), "+n" ), ( ( c0, c1, n1 - 10, n1 ), "-n" ), ( ( c0, c0 + 10, n0, n1 ), "+e" ),
                                   ( ( c1 - 10, c1, n0, n1 ), "-e" ) ):
        box( m, a, b, c, d, CORE_TOP, CORE_TOP + 28, { "default": None, inner: "rv_wall" }, STONE )
        F.coping( m, a, b, c, d, CORE_TOP + 28 )
    # Ground floor lamps in the passage, the upper room's lamps.
    P.ceiling_light( m, "B1 passage", ( 0, -870, ROOM_Z - 20 ), ( 0, 1 ), "cool", 340 )
    P.ceiling_light( m, "B1 room", ( 0, -870, CORE_TOP - 26 ), ( 0, 1 ), "cool", 380 )
    # Each side: the low wing (its roof part of the upper deck), the landing, the stair, railings.
    for sx in ( -1, 1 ):
        f = -sx

        def E( a, b ):
            return tuple( sorted( ( f * a, f * b ) ) )

        box( m, *E( WING[0], WING[1] ), WING[2], WING[3], 0, ROOM_Z, { "default": None, "+z": "rv_floor" }, STONE )
        box( m, *E( B_LANDING[0], B_LANDING[1] ), B_LANDING[2], B_LANDING[3], ROOM_Z - 16, ROOM_Z,
             { "default": "rv_wall", "+z": "rv_floor" }, STONE )
        box( m, *E( B_LANDING[0], B_LANDING[0] + 12 ), B_LANDING[2], B_LANDING[2] + 12, 0, ROOM_Z - 16, "rv_wall", STONE )
        mid = ( B_STAIR[2] + B_STAIR[3] ) / 2
        P.stairs( m, ( f * B_STAIR[0], mid ), ( f * B_STAIR[1], mid ), B_STAIR[3] - B_STAIR[2], 0, ROOM_Z, tread="rv_plinth",
                  side="rv_plinth", solid_under=True, surface=STONE, name=f"B1 stair {sx}" )
        P.railing( m, mirror_pts( [ ( -200, -864 ), ( -200, -840 ), ( -420, -840 ), ( -420, -700 ), ( -160, -700 ) ], f ), ROOM_Z, clip_to=160,
                   name=f"B1 deck rail {sx}" )
        P.railing( m, mirror_pts( [ ( -200, -940 ), ( -160, -940 ) ], f ), ROOM_Z, clip_to=160, name=f"B1 landing rail {sx}" )
    b1_faces( m, up_door )
    # Inside the room: lockers, a table, cases.
    box( m, -120, -40, -1000, -980, ROOM_Z, ROOM_Z + 80, "rv_steel", METAL )
    box( m, 40, 120, -1000, -980, ROOM_Z, ROOM_Z + 80, "rv_steel", METAL )
    box( m, -36, 36, -960, -920, ROOM_Z, ROOM_Z + 30, { "default": "rv_desk", "+z": "rv_dark" }, METAL )
    P.case_stack( m, ( -100, -760 ), ( 1, 0 ), "dark", seed=201 )
    P.case_stack( m, ( 100, -760 ), ( 1, 0 ), "olive", seed=202 )
    # On the roof: an air handling unit, fans and vents showing over the parapet.
    F.roof_unit( m, ( 0, -880 ), ( 1, 0 ), CORE_TOP, ( 140, 72, 54 ) )
    F.roof_fan( m, ( -105, -1000 ), CORE_TOP )
    F.roof_fan( m, ( 105, -760 ), CORE_TOP )
    F.roof_vent( m, ( 110, -1000 ), CORE_TOP )
    F.roof_vent( m, ( -115, -760 ), CORE_TOP )


def b1_faces( m, up_door ):
    """ C1's faces (riverdale_facades): its core a control block in concrete between corner fins, a deep ribbon window
    lighting its room on the north and south, the passage under a canopy, a precast band and the parapet's coping, the
    door from each deck under a canopy; and its wings' faces, the name over a door. """
    c0, c1, n0, n1 = CORE
    t = 24.0
    top = CORE_TOP + 28
    for nf, normal, sgn in ( ( n1, "+n", 1 ), ( n0, "-n", -1 ) ):
        face = F.Face( m, normal, nf, c0, c1, 0, top )
        face.opening( -60, 60, 0, 150 )
        face.later.append( lambda face=face: face.reveal( -60, 60, 0, 150, t, "rv_wall", ( True, True, False, False ) ) )
        face.window( -124, 124, 236, 334, 8.0, pitch=50, transom=304, room="office", lit=True, blind=0.3 )
        face.louvre( -116, -56, 362, 400 )
        face.louvre( 56, 116, 362, 400 )
        face.plinth( wrap=( False, False ) )
        face.band( 344, 8, 2.0, wrap=( False, False ) )
        for a, b in ( ( c0, c0 + 32 ), ( c1 - 32, c1 ) ):
            face.pilaster( a, b, 0, CORE_TOP, 5.0 )
        face.grime_foot()
        face.grime_top( c0, c1, 344, 72 )
        face.later.append( lambda face=face: face.canopy( 0, 150, 158, 40 ) )
        face.finish()
        face.letters( "control_room", 0, 212, 14 )
        face.lamp( f"B1 passage lamp {sgn}", 0, 180, "warm", 320, light=True )
        face.camera( -100, 420, turn=-20 )
        face.sign( "door_sign", 78, 112, 14 )
        P.beacon( m, f"B1 roof beacon {sgn}", ( 140 * sgn, nf - sgn * 6, CORE_TOP + 30 ) )
    for sx in ( -1, 1 ):
        f = -sx

        def U( a, b ):
            return tuple( sorted( ( f * a, f * b ) ) )

        side = "-e" if f > 0 else "+e"
        to_out = ( f > 0, f < 0 )
        # The core's side, over the wing and the landing.
        s = F.Face( m, side, f * c0, n0, n1, 0, top )
        s.exclude( WING[2], WING[3], 0, ROOM_Z )
        s.exclude( B_LANDING[2], B_LANDING[3], ROOM_Z - 16, ROOM_Z )
        s.door( ( up_door[0] + up_door[1] ) / 2, 66, 92, z=ROOM_Z, canopy=28, through=( up_door[0], up_door[1] ) )
        s.later.append( lambda s=s: s.reveal( up_door[0], up_door[1], up_door[3], up_door[2], t, "rv_wall", ( True, True, False, False ), d0=1.5 ) )
        s.window( -1000, -950, 236, 334, 8.0, room="plant" )
        s.window( -800, -730, 236, 334, 8.0, pitch=35, room="office", lit=True, blind=0.45 )
        s.louvre( -1000, -950, 40, 130 )
        s.plinth( wrap=( True, False ) )
        s.band( 344, 8, 2.0, wrap=( True, True ) )
        s.grime_foot()
        s.downpipe( -1026, top - 2 )
        s.finish()
        s.sign( "door_sign", -820, ROOM_Z + 54, 14 )
        s.lamp( f"B1 door lamp {sx}", ( up_door[0] + up_door[1] ) / 2, ROOM_Z + 122, "warm", 300, light=True )
        s.cabinet( -925, 30, 26, 42 )
        s.conduit( [ ( -925, 72 ), ( -925, ROOM_Z - 22 ) ] )
        # The wing: C1 over its door at its end, a louvre and cabinets on its sides, its deck's edge.
        wn = ( WING[2] + WING[3] ) / 2
        we = F.Face( m, side, f * WING[0], WING[2], WING[3], 0, ROOM_Z )
        we.door( wn, 66, 84, double=False, glazed=False, paint="rv_door_yellow" )
        we.plinth()
        we.band( ROOM_Z - 12, 12, 2.0, drip=True )
        we.grime_foot()
        we.finish()
        we.letters( "C1", wn, 148, 64 )
        we.lamp( f"B1 wing lamp {sx}", wn, 102, "warm", 260, light=True )
        wnf = F.Face( m, "+n", WING[3], *U( WING[0], WING[1] ), 0, ROOM_Z )
        wnf.louvre( *U( -390, -300 ), 60, 140 )
        wnf.plinth( wrap=to_out )
        wnf.band( ROOM_Z - 12, 12, 2.0, wrap=to_out, drip=True )
        wnf.grime_foot()
        wnf.finish()
        wnf.cabinet( f * -250, 30, 26, 42, plate="notice" )
        wsf = F.Face( m, "-n", WING[2], *U( WING[0], WING[1] ), 0, ROOM_Z )
        wsf.exclude( *U( B_LANDING[0], B_LANDING[1] ), ROOM_Z - 16, ROOM_Z )
        wsf.plinth( wrap=to_out )
        wsf.band( ROOM_Z - 12, 12, 2.0, wrap=to_out, drip=True )
        wsf.grime_foot()
        wsf.finish()
        wsf.cabinet( f * -380, 30, 24, 40 )


def generator( m, e0, e1, n0, n1 ):
    """ A diesel generator set on its skid: an acoustic housing (its panels, louvres, radiator grille, control panel,
    silencer and stack: riverdale_facades.genset), a fuel tank under. """
    box( m, e0 - 6, e1 + 6, n0 - 6, n1 + 6, 0, 14, "rv_steel", METAL )
    box( m, e0, e1, n0, n1, 14, 96, { "default": "rv_yellow", "+z": "rv_steel" }, METAL )
    F.genset( m, e0, e1, n0, n1 )
    P.letters( m, "logo_wordmark", ( ( e0 + e1 ) / 2, n0 - 0.4, 52 ), ( 1, 0, 0 ), 16, "dark" )


def turbine_annex( m ):
    """ The turbine building's annex south of C1 (TURBINE), its generators in front: a concrete base under light grey
    cladding, louvre banks and a door with a canopy towards C1, a roller shutter in each side's loading bay, the
    turbine hall's sign on a board, pipes on brackets, plant on the roof. """
    for sx in ( -1, 1 ):
        generator( m, *sorted( ( sx * 130, sx * 320 ) ), -1165, -1065 )
    e0, e1, n0, n1 = TURBINE
    top, clad = TURBINE_TOP + 30, 150.0
    box( m, e0, e1, n0, n1, 0, TURBINE_TOP, { "default": None, "+z": "rv_plinth" }, STONE )
    for ( a, b, c, d ), inner in ( ( ( e0, e1, n1 - 10, n1 ), "-n" ), ( ( e0, e0 + 10, n0, n1 ), "+e" ), ( ( e1 - 10, e1, n0, n1 ), "-e" ) ):
        box( m, a, b, c, d, TURBINE_TOP, top, { "default": None, inner: "rv_wall" }, STONE )
        F.coping( m, a, b, c, d, top )
    for sx in ( -1, 1 ):
        side = "+e" if sx > 0 else "-e"
        s = F.Face( m, side, sx * e1, n0, n1, 0, top )
        s.zone( clad, top, F.CLAD_LIGHT, ribs=True )
        s.corner_trims = ( None, True )
        # A loading bay: a roller shutter under its drum's housing.
        bay0, bay1 = -1636.0, -1484.0
        s.shutter( bay0, bay1, 0, 180 )
        s.guard( bay0, -1, 72 )
        s.guard( bay1, 1, 72 )
        s.door( -1330, 48, 88, double=False, canopy=28 )
        s.louvre( -1720, -1660, 220, 300 )
        s.plinth( wrap=( False, True ) )
        s.grime_foot()
        s.downpipe( -1256, top - 2 )
        s.finish()
        s.letters( "turbine_hall", -1360, 250, 26, board="rv_white", d=2.6 )
        s.lamp( f"Turbine annex bay lamp {sx}", ( bay0 + bay1 ) / 2, 214, "warm", 380, light=True )
        s.lamp( f"Turbine corner lamp {sx}", -1266, 300, "warm", 300, light=True )
        s.cabinet( -1420, 30, 26, 44 )
        s.conduit( [ ( -1420, 74 ), ( -1420, clad - 4 ) ] )
        s.camera( -1700, 340, turn=20 )
        P.beacon( m, f"Turbine beacon {sx}", s.p( -1250, top + 2.0, -5 ) )
    # The north face, towards C1: louvre banks, a door, pipes on brackets, lamps.
    nf = F.Face( m, "+n", n1, e0, e1, 0, top )
    nf.zone( clad, top, F.CLAD_LIGHT, ribs=True )
    nf.corner_trims = ( True, True )
    for e in ( -330.0, 330.0 ):
        nf.louvre( e - 90, e + 90, 190, 310 )
    nf.door( 0, 90, 100, canopy=36 )
    for e in ( -170.0, 170.0 ):
        nf.joint( e, 24, clad - 4 )
    nf.plinth()
    nf.grime_foot()
    for e in ( -500.0, 500.0 ):
        nf.downpipe( e, top - 2 )
    nf.finish()
    nf.letters( "turbine_hall", 0, 192, 18, board="rv_white", d=2.6 )
    nf.lamp( "Turbine door lamp", 0, 134, "warm", 340, light=True )
    nf.cabinet( 120, 30, 26, 44 )
    nf.conduit( [ ( 120, 74 ), ( 120, clad - 4 ) ] )
    nf.cabinet( -120, 30, 26, 44, paint="rv_fc_red", plate="lifering_sign" )
    nf.camera( -470, 340, turn=-30 )
    nf.camera( 470, 340, turn=30 )
    for k, r in enumerate( ( 10.0, 7.0 ) ):
        run = [ ( e0 + 10, n1 + 18 + k * 6, 300 - k * 24 ), ( e1 - 10, n1 + 18 + k * 6, 300 - k * 24 ) ]
        P.pipe( m, run, r, "rv_pipe", 12 )
        F.flanges( m, run[0], run[1], r, every=320.0, start=110.0 )
    for e in np.arange( e0 + 40, e1, 160.0 ):
        box( m, e - 3, e + 3, n1, n1 + 30, 262, 266, "rv_steel" )
        box( m, e - 4, e + 4, n1, n1 + 1.0, 254, 270, "rv_steel" )
    # On the roof.
    F.roof_unit( m, ( -200, -1500 ), ( 1, 0 ), TURBINE_TOP, ( 130, 70, 52 ) )
    F.roof_unit( m, ( 220, -1420 ), ( 1, 0 ), TURBINE_TOP, ( 110, 60, 46 ) )
    for e, n in ( ( -420, -1350 ), ( 420, -1600 ), ( 30, -1640 ) ):
        F.roof_fan( m, ( e, n ), TURBINE_TOP )
    F.hatch( m, ( -40, -1330 ), TURBINE_TOP )


def middle_yard( m ):
    """ The hall's apron and the pipe bridge from the hall to B1. """
    # Pipe bridge: a truss from the hall's south wall to B1's north wall, pipes on it, resting on shoes, sleeved where
    # they go into the walls.
    for e in ( -110.0, -30.0 ):
        P.truss( m, ( e, H.N0 - H.WT - 14, 300 ), ( e, CORE[3], 300 ), 40, "rv_steel", panel=60 )
    slats = np.arange( H.N0 - H.WT - 60, CORE[3], 80.0 )
    for k, ( de, r ) in enumerate( ( ( -95, 9.0 ), ( -70, 6.0 ), ( -50, 6.0 ) ) ):
        P.pipe( m, [ ( de, H.N0 - H.WT + 4, 352 ), ( de, CORE[3] - 4, 352 ) ], r, "rv_pipe", 12, caps=False )
        F.flanges( m, ( de, H.N0 - H.WT, 352 ), ( de, CORE[3], 352 ), r, every=150.0, start=40.0 )
        for n in ( H.N0 - H.WT, CORE[3] ):
            P.disc_ring( m, v( de, n - 1.5, 352 ), v( de, n + 1.5, 352 ), r * 1.35, "rv_steel", 12 )
        for n in slats:
            F.shoe( m, ( de, n, 352 ), r, ( 0, 1 ) )
    for n in slats:
        box( m, -114, -26, n - 2, n + 2, 340, 342, "rv_steel" )
    # Barriers and cases in the apron.
    for e, n, along in ( ( -300, -520, ( 1, 0 ) ), ( 300, -520, ( 1, 0 ) ), ( -560, -400, ( 0, 1 ) ), ( 560, -400, ( 0, 1 ) ) ):
        P.jersey( m, ( e, n ), along )
    for k, ( e, n ) in enumerate( ( ( -150, -330 ), ( 160, -340 ), ( -700, -600 ), ( 700, -600 ) ) ):
        P.case_stack( m, ( e, n ), ( 1, 0 ), "olive" if k % 2 else "dark", seed=300 + k )
    # The hall's south face: its name over the door, the logo high up, lamps and beacons.
    face = H.N0 - H.WT
    out = v( 0, -1, 0 )
    right = np.cross( UP, out )
    P.letters( m, "fuel_handling", ( 0, face, 168 ), right, 18, "dark" )
    P.letters( m, "logo_wordmark", ( 0, face, 900 ), right, 150, "dark" )
    P.wall_light( m, "Hall south door lamp", ( 0, face, 150 ), out, "warm", 380 )
    for e in ( -500.0, 500.0 ):
        P.wall_light( m, f"Hall south lamp {e}", ( e, face, 240 ), out, "warm", 360 )
    for e in ( -1040.0, 1040.0 ):
        P.beacon( m, f"Hall beacon {e}", ( e * 0.98, face - 8, H.ROOF + 40 ), light=False )
    for k, r in enumerate( ( 8.0, 6.0 ) ):
        run = [ ( -1030, face - 16 - k * 14, 420 + k * 20 ), ( 1030, face - 16 - k * 14, 420 + k * 20 ) ]
        P.pipe( m, run, r, "rv_pipe", 12 )
        F.flanges( m, run[0], run[1], r, every=400.0, start=150.0 )
    for e in np.arange( -1000, 1001, 200.0 ):
        box( m, e - 3, e + 3, face - 40, face, 408, 412, "rv_steel" )
    P.louvre( m, ( -620, face, 700 ), right, 260, 160 )
    P.louvre( m, ( 620, face, 700 ), right, 260, 160 )
    # The east-west lanes' floor lines in the middle.
    box( m, -520, 520, -1206, -1202, 0, 0.3, { "default": None, "+z": "rv_line_yellow" } )


def north_lane( m ):
    """ The lane north of the hall: the perimeter wall with a fence on it, the pipe rack along the hall's wall, cover. """
    n = NORTH_WALL_N
    box( m, PLAY[0] - 400, PLAY[1] + 400, n, n + 30, 0, 220, { "default": "rv_wall", "-n": None }, STONE )
    perimeter_face( m )
    for e in np.arange( PLAY[0], PLAY[1] + 1, 120.0 ):
        P.rod( m, ( e, n + 15, 220 ), ( e, n + 15, 300 ), 1.2, "rv_zinc", 6 )
        P.rod( m, ( e, n + 15, 296 ), ( e, n + 5, 304 ), 0.8, "rv_zinc", 4 )
    for z in ( 250.0, 275.0, 300.0 ):
        P.rod( m, ( PLAY[0], n + 15, z ), ( PLAY[1], n + 15, z ), 0.4, "rv_zinc", 4 )
    # Pipe rack along the hall's north wall: portals on base plates with knee braces, pipes on shoes with flanges and
    # valves, a cable tray.
    r0, r1 = H.N1 + H.WT + 10, H.N1 + H.WT + 150
    portals = np.arange( -1000, 1001, 250.0 )
    for e in portals:
        for nn in ( r0, r1 ):
            box( m, e - 5, e + 5, nn - 5, nn + 5, 0, 260, "rv_steel", METAL )
            F.base_plate( m, e, nn, 10.0 )
            for de in ( -1, 1 ):
                if abs( e + de * 40 ) <= 1000:
                    m.beam( v( e + de * 5, nn, 212 ), v( e + de * 40, nn, 248 ), ( 2.5, 2.5 ), "rv_steel" )
        for nn, dn in ( ( r0, 1 ), ( r1, -1 ) ):
            m.beam( v( e, nn + dn * 5, 214 ), v( e, nn + dn * 40, 254 ), ( 2.5, 2.5 ), "rv_steel" )
        P.i_beam( m, ( e, r0 - 6, 260 ), ( e, r1 + 6, 260 ), 12, 8, "rv_steel" )
    for nn in ( r0, r1 ):
        P.i_beam( m, ( -1010, nn, 254 ), ( 1010, nn, 254 ), 12, 8, "rv_steel" )
    for k, ( r, paint ) in enumerate( ( ( 12.0, "rv_pipe" ), ( 9.0, "rv_pipe" ), ( 9.0, "rv_steel" ), ( 6.0, "rv_yellow" ), ( 6.0, "rv_white" ) ) ):
        nn = r0 + 18 + k * 26
        run = [ ( -1700, nn, 266 + r ), ( 1700, nn, 266 + r ) ]
        P.pipe( m, run, r, paint, 12, caps=False )
        F.flanges( m, run[0], run[1], r, every=480.0, start=150.0 + 60 * k, paint=paint )
        for e in portals:
            F.shoe( m, ( e, nn, 266 + r ), r, ( 1, 0 ) )
    for e, k in ( ( -620.0, 3 ), ( 380.0, 1 ), ( 860.0, 2 ) ):
        r = ( 12.0, 9.0, 9.0, 6.0, 6.0 )[k]
        F.valve( m, ( e, r0 + 18 + k * 26, 266 + r ), r, ( 1, 0 ) )
    P.cable_tray( m, ( -1700, r1 + 30, 300 ), ( 1700, r1 + 30, 300 ) )
    for e in portals:
        m.beam( v( e, r1, 260 ), v( e, r1, 298 ), ( 4.0, 4.0 ), "rv_steel" )
        m.beam( v( e, r1 + 2, 296 ), v( e, r1 + 40, 296 ), ( 2.0, 2.0 ), "rv_steel" )
    # Cover: concrete blocks, a generator, cases, barriers.
    mid = ( r1 + n ) / 2
    for e, nn in ( ( -720, mid + 40 ), ( 720, mid + 40 ), ( -240, r1 + 60 ), ( 240, r1 + 60 ), ( 0, n - 90 ) ):
        box( m, e - 30, e + 30, nn - 30, nn + 30, 0, 44, "rv_plinth", STONE )
    generator( m, -140, 140, n - 160 - 70, n - 160 )
    for k, ( e, nn ) in enumerate( ( ( -1260, mid + 30 ), ( 1260, mid + 30 ), ( -500, n - 60 ), ( 500, n - 60 ), ( -1900, n - 100 ), ( 1900, n - 100 ) ) ):
        P.case_stack( m, ( e, nn ), ( 1, 0 ), "olive" if k % 2 else "dark", seed=400 + k )
    for e, nn, along in ( ( -1000, r1 + 40, ( 1, 0 ) ), ( 1000, r1 + 40, ( 1, 0 ) ), ( -1700, mid, ( 0, 1 ) ), ( 1700, mid, ( 0, 1 ) ) ):
        P.jersey( m, ( e, nn ), along )
    for e in ( -1500.0, -500.0, 500.0, 1500.0 ):
        P.wall_light( m, f"Perimeter lamp {e}", ( e, n, 200 ), v( 0, -1, 0 ), "warm", 420 )
    out = v( 0, 1, 0 )
    right = np.cross( UP, out )
    for o in H.NORTH_DOORS:
        e = ( o[0] + o[1] ) / 2
        P.wall_light( m, f"Hall north door lamp {e}", ( e, H.N1 + H.WT, 150 ), out, "warm", 340 )
        P.plate( m, "exit", ( e, H.N1 + H.WT, 140 ), right, 10, off=0.4 )


def perimeter_face( m ):
    """ The perimeter wall's face towards the lane (riverdale_facades): cast panels between piers, expansion joints, a
    darker plinth, a precast coping under the fence, warning signs and cameras. """
    n = NORTH_WALL_N
    f_ = F.Face( m, "-n", n, PLAY[0] - 400, PLAY[1] + 400, 0, 220 )
    piers = np.arange( -2400.0, 2401.0, 480.0 )
    for e in piers:
        f_.pilaster( e - 14, e + 14, 0, 214, 5.0, cap=None )
        if e + 240 < PLAY[1] + 400:
            f_.joint( e + 240, 30, 214 )
    f_.plinth( 30, 3.0, wrap=( False, False ) )
    f_.grime_foot( 30, 3.0 )
    f_.grime_top( PLAY[0] - 400, PLAY[1] + 400, 214, 80 )
    f_.finish()
    F.coping( m, PLAY[0] - 400, PLAY[1] + 400, n, n + 30, 220, over=3.0, paint=F.PRECAST, t=5.0, lip=2.0 )
    for k, e in enumerate( piers[:-1] ):
        if k % 2:
            f_.sign( "danger", e + 120, 118, 20 )
        else:
            f_.camera( e + 40, 196, turn=25 )


def turbine_hall( m ):
    """ The turbine hall: the south boundary, its north face dressed (turbine_hall_face). Solid. """
    e0, e1 = PLAY[0] - 400, PLAY[1] + 400
    n0, n1 = PLAY[2] - 1000, PLAY[2]
    box( m, e0, e1, n0, n1, 0, 960, { "default": "rv_wall", "+n": None, "+z": "rv_plinth" }, STONE )
    piers = [ float( e ) for e in np.arange( PLAY[0], PLAY[1] + 1, 300.0 ) if abs( e ) >= 560 ]
    for e in piers:
        box( m, e - 24, e + 24, n1, n1 + 16, 0, 980, "rv_wall", STONE )
        F.coping( m, e - 24, e + 24, n1, n1 + 16, 980, over=1.5 )
    F.coping( m, e0, e1, n1 - 12, n1, 960 )
    turbine_hall_face( m, piers )


def turbine_hall_face( m, piers ):
    """ The turbine hall's face towards the yard (riverdale_facades): a concrete base and light grey cladding between
    its concrete piers, a clerestory of glazing, louvres high up, doors and roller shutters at the foot, its name on a
    sign board, pipes on brackets off the piers, downpipes. """
    n1 = PLAY[2]
    top = 960.0
    clad = 300.0
    t = F.Face( m, "+n", n1, PLAY[0] - 400, PLAY[1] + 400, 0, top )
    t.zone( clad, top - 20, F.CLAD_LIGHT, ribs=True )
    t.corner_trims = ( None, None )
    # What stands against it: the turbine annex, the turbine blocks, the boundary buildings.
    t.exclude( TURBINE[0], TURBINE[1], 0, TURBINE_TOP + 32 )
    for sx in ( -1, 1 ):
        t.exclude( *sorted( ( -sx * TURBINE_SIDE[0], -sx * TURBINE_SIDE[1] ) ), 0, 452 )
    t.exclude( PLAY[0] - 400, PLAY[0], 0, BOUNDARY_TOP + 22 )
    t.exclude( PLAY[1], PLAY[1] + 400, 0, BOUNDARY_TOP + 22 )
    hidden = lambda a, b: any( lo < b and hi > a for lo, hi in ( ( -1700, -1300 ), ( 1300, 1700 ) ) )
    bays = [ ( p, q ) for p, q in zip( piers, piers[1:] ) if q - p < 301 ]
    ground = { -2150.0: "door", -1850.0: "louvre", -1250.0: "door", -950.0: "shutter", 850.0: "door", 1150.0: "shutter",
               1750.0: "louvre", 2050.0: "door" }
    lamps = { -2150.0: -1900.0, -1250.0: -1100.0, 850.0: 1100.0, 2050.0: 1900.0 }
    for k, ( p, q ) in enumerate( bays ):
        bc = ( p + q ) / 2
        if not hidden( p, q ):
            t.window( p + 40, q - 40, 440, 520, 6.0, pitch=43, room="plant", sill=None )
        if k % 2 == 0:
            t.louvre( bc - 90, bc + 90, 680, 800 )
        kind = ground.get( bc )
        if kind == "door":
            t.door( bc, 72, 96, canopy=40 )
        elif kind == "shutter":
            t.shutter( bc - 100, bc + 100, 0, 240 )
            t.guard( bc - 100, -1, 72 )
            t.guard( bc + 100, 1, 72 )
        elif kind == "louvre":
            t.louvre( bc - 70, bc + 70, 50, 160 )
    # The long bay behind the turbine annex: a clerestory over it, louvres, a louvre and a door either side of it.
    t.window( -740, 640, 440, 520, 6.0, pitch=46, room="plant", sill=None )
    for e in ( -400.0, 0.0, 400.0 ):
        t.louvre( e - 90, e + 90, 680, 800 )
    t.louvre( -720, -580, 50, 150 )
    t.door( 610, 60, 92, double=False, canopy=30 )
    t.plinth( wrap=( False, False ) )
    t.grime_foot()
    t.grime_top( PLAY[0], PLAY[1], top - 20, 96 )
    for e in ( -2000.0, -800.0, 1000.0, 2200.0 ):
        t.downpipe( e + 31, top - 2, scupper=False )
    t.finish()
    for e in ( -1350.0, 1350.0 ):
        t.letters( "turbine_hall", e, 880, 70, board="rv_white", d=2.6 )
    for bc, name in lamps.items():
        t.lamp( f"Turbine hall door lamp {name}", bc, 132, "warm", 380, light=True )
        t.sign( "notice", bc + 52, 64, 18 )
    for bc, kind in ground.items():
        if kind == "louvre":
            t.cabinet( bc + 96, 30, 26, 44 )
            t.conduit( [ ( bc + 96, 74 ), ( bc + 96, clad - 6 ) ] )
        if kind == "shutter":
            t.sign( "danger", bc - 128, 110, 18 )
    for e in ( -2150.0, -950.0, 850.0, 2050.0 ):
        t.camera( e + 110, 330, turn=-25 if e < 0 else 25 )
    # Pipes on brackets off the piers.
    for k, ( r, z ) in enumerate( ( ( 14.0, 600.0 ), ( 10.0, 640.0 ) ) ):
        run = [ ( PLAY[0], n1 + 40, z ), ( PLAY[1], n1 + 40, z ) ]
        P.pipe( m, run, r, "rv_pipe", 12, caps=False )
        F.flanges( m, run[0], run[1], r, every=600.0, start=90.0 + 150 * k )
        for e in piers:
            F.shoe( m, ( e, n1 + 40, z ), r, ( 1, 0 ) )
            box( m, e - 4, e + 4, n1 + 16, n1 + 56, z - r - 10, z - r - 4.2, "rv_steel" )


# ---------------------------------------------------------------------------------------------------------------------
# Lights and probes

def probes():
    return [
        ( "Hall", ( 0, 900, 400 ), ( H.E0, H.E1, H.N0, H.N1, -40, H.TOP ) ),
        ( "Pool", ( 0, 900, -200 ), ( -520, 520, 380, 1420, H.POOL_FLOOR, 0 ) ),
        ( "A1", ( -1370, -190, 150 ), ( -1670, -1070, -590, 210, 0, ANNEX_TOP - 20 ) ),
        ( "A2", ( 1370, -190, 150 ), ( 1070, 1670, -590, 210, 0, ANNEX_TOP - 20 ) ),
        ( "B1 Room", ( 0, -870, 280 ), ( -136, 136, -1016, -724, ROOM_Z, CORE_TOP - 20 ) ),
        ( "West Control", ( -780, 930, 370 ), ( -1000, -560, 660, 1200, H.UPPER, H.CONTROL_TOP ) ),
        ( "East Control", ( 780, 930, 370 ), ( 560, 1000, 660, 1200, H.UPPER, H.CONTROL_TOP ) ),
        ( "Yard", ( 0, -1000, 200 ), ( PLAY[0], PLAY[1], PLAY[2], H.N0 - H.WT, -20, 900 ) ),
        ( "North", ( 0, 2250, 200 ), ( PLAY[0], PLAY[1], H.N1 + H.WT, PLAY[3], -20, 700 ) ),
    ]


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( -2050, -500, 0 ), ( -2050, -250, 0 ), ( -2050, 0, 0 ), ( -2050, 250, 0 ), ( -2050, 480, 0 ), ( -1850, -450, 0 ),
               ( -1850, -200, 0 ), ( -1850, 50, 0 ), ( -1850, 300, 0 ), ( -2200, -400, 0 ), ( -2200, -100, 0 ), ( -2200, 200, 0 ) ]
BLUE_SPAWNS = [ ( -e, n, z ) for e, n, z in RED_SPAWNS ]
BUY_ZONE = ( 1720, 2300, -900, 500, -10, 260 )        # Blue Team's; Red Team's is its mirror

DM_SPAWNS = [ ( 0, 0, 0 ), ( 0, 1700, 0 ), ( -470, 1700, 0 ), ( 470, 1700, 0 ), ( -820, 300, 0 ), ( 640, 930, 0 ),
              ( -930, 1500, H.UPPER ), ( 930, 1260, H.UPPER ), ( 0, 1930, H.UPPER ), ( -780, 930, H.UPPER ), ( 780, 930, H.UPPER ),
              ( -1370, -100, 0 ), ( 1370, -100, 0 ), ( -1370, 1300, 0 ), ( 1370, 800, 0 ), ( -600, 2250, 0 ), ( 600, 2250, 0 ),
              ( -1800, 2250, 0 ), ( 1800, 2250, 0 ), ( 0, -870, ROOM_Z ), ( -300, -770, ROOM_Z ), ( 300, -770, ROOM_Z ),
              ( 0, -500, 0 ), ( -860, -1060, 0 ), ( 860, -1060, 0 ), ( -1380, -1100, 0 ), ( 1380, -1100, 0 ), ( 0, -1150, 0 ),
              ( -1100, -1600, 0 ), ( 1100, -1600, 0 ), ( -1950, -1550, 0 ), ( 1950, -1550, 0 ), ( -2130, -950, SPAWN_ROOM_Z ),
              ( 2130, -950, SPAWN_ROOM_Z ) ]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 520, 1000, 300, 1000, 0 ),
               ( "bombsite_b", "Bomb Site B", 760, 1300, -1620, -960, 0 ) ]

_HALL_ATTACK = [ ( -1400, 800, 0 ), ( -1500, 1000, 0 ), ( -1300, 1150, 0 ), ( -1400, -400, 0 ), ( -1550, -300, 0 ), ( -1250, -300, 0 ) ]
_YARD_ATTACK = [ ( -1100, -1440, 0 ), ( -1150, -1660, 0 ), ( -1300, -720, 0 ), ( -1640, -760, 0 ), ( -1200, -980, 0 ), ( -1400, -1210, 0 ) ]
RETAKES = {
    "bombsite_a": { "planter": [ ( 800, 760, 0 ), ( 680, 400, 0 ) ],
                    "defender": [ ( 820, 1760, 0 ), ( 470, 1600, 0 ), ( 860, 260, 0 ) ],
                    "attacker": list( _HALL_ATTACK ) },
    "bombsite_b": { "planter": [ ( 1000, -1290, 0 ), ( 1150, -1500, 0 ) ],
                    "defender": [ ( 1250, -1080, 0 ), ( 860, -1640, 0 ), ( 1160, -1680, 0 ) ],
                    "attacker": list( _YARD_ATTACK ) },
}

DOMINATION = [ ( "A", ( -1370, -120, 0 ) ), ( "B", ( 0, -500, 0 ) ), ( "C", ( 1370, -120, 0 ) ) ]
HOT_ZONES = [ ( "Pool South", ( 0, 0, 0 ) ), ( "Pool North", ( 0, 1700, 0 ) ), ( "C1", ( 0, -870, ROOM_Z ) ),
              ( "North Lane", ( -370, 2320, 0 ) ), ( "West Court", ( -1370, 900, 0 ) ), ( "East Court", ( 1370, 900, 0 ) ) ]
CASH_POINTS = [ ( "Pool South", ( 0, 0, 0 ), ( 0, -870, ROOM_Z ) ), ( "West Court", ( -1370, 900, 0 ), ( 1370, 900, 0 ) ),
                ( "East Court", ( 1370, 900, 0 ), ( -1370, 900, 0 ) ) ]


def callouts():
    out = [ ( "RED SPAWN", PLAY[0], -1700, PLAY[2], PLAY[3], -10, 600 ), ( "BLUE SPAWN", 1700, PLAY[1], PLAY[2], PLAY[3], -10, 600 ),
            ( "A1", -1700, -1040, -620, 240, -10, 380 ), ( "A2", 1040, 1700, -620, 240, -10, 380 ),
            ( "WEST COURT", -1700, -1040, 240, 2040, -10, 600 ), ( "EAST COURT", 1040, 1700, 240, 2040, -10, 600 ),
            ( "NORTH LANE", -1700, 1700, 2040, PLAY[3], -10, 600 ),
            ( "WEST CONTROL", -1000, -560, 580, 1200, 270, 470 ), ( "EAST CONTROL", 560, 1000, 580, 1200, 270, 470 ),
            ( "WEST WALKWAY", -1000, -640, 1200, 1860, 270, 470 ), ( "EAST WALKWAY", 640, 1000, 1200, 1860, 270, 470 ),
            ( "NORTH WALKWAY", -1000, 1000, 1860, 2000, 270, 470 ),
            ( "POOL SOUTH", -1000, 1000, -200, 380, -40, 270 ), ( "POOL WEST", -1000, -300, 380, 2000, -40, 270 ),
            ( "A SITE", 300, 1000, 380, 1200, -40, 270 ), ( "POOL NORTH", -300, 1000, 1200, 2000, -40, 270 ),
            ( "HALL APRON", -1040, 1040, -700, -240, -10, 500 ), ( "C1", -470, 470, -1040, -700, -10, 190 ),
            ( "C1 ROOM", -160, 160, -1040, -700, 190, 440 ), ( "WEST YARD", -1700, -470, -1750, -620, -10, 600 ),
            ( "B SITE", 470, 1700, -1750, -620, -10, 600 ), ( "TURBINE", -520, 520, -1240, -1040, -10, 600 ),
            ( "B1", 1700, 2300, -1160, -690, 150, 600 ), ( "B2", -2300, -1700, -1160, -690, 150, 600 ) ]
    return out


def all_spots():
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
# The radar picture

MINIMAP_CENTRE = ( 0.0, 350.0 )
MINIMAP_SIZE = 5000.0
MINIMAP_PIXELS = 1024


def write_minimap( models ):
    """ Railhead's radar style: where you can walk grey, low cover darker, buildings clear, a light line round the edges,
    the hall's upper level a lighter grey. North up. """
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "low", "tall", "upper" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    shapes = sorted( R.collision_shapes( models ), key=lambda pts: -float( np.ptp( pts[:, 0] ) * np.ptp( pts[:, 1] ) ) )
    for pts in shapes:
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = R.hull_2d( pts[:, :2] )
        if len( outline ) < 3:
            continue
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if -30 <= z1 <= 18:
            draws["walk"].polygon( screen, fill=255 )
        elif 170 <= z1 <= 300 and z1 - z0 < 40:
            draws["upper"].polygon( screen, fill=255 )
        elif z0 < 72 and z1 > 18:
            draws["low" if z1 < 100 else "tall"].polygon( screen, fill=255 )
    walk, low, tall, upper = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "low", "tall", "upper" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    E, N = np.meshgrid( cols, rows )
    inside = ( E > PLAY[0] ) & ( E < PLAY[1] ) & ( N > PLAY[2] ) & ( N < PLAY[3] )
    pool = np.hypot( E - H.POOL[0], N - H.POOL[1] ) < H.POOL_R
    walk &= inside & ~pool
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[low & inside] = ( 64, 68, 74, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    image[upper & inside] = ( 128, 132, 138, 235 )
    image[pool] = ( 40, 120, 150, 200 )
    shown = ( walk | ( low & inside ) | ( upper & inside ) ) & ~tall
    edge = np.zeros_like( shown )
    edge[1:, :] |= ~shown[:-1, :]
    edge[:-1, :] |= ~shown[1:, :]
    edge[:, 1:] |= ~shown[:, :-1]
    edge[:, :-1] |= ~shown[:, 1:]
    image[shown & edge] = ( 226, 233, 240, 255 )
    MINIMAP_FILE.parent.mkdir( parents=True, exist_ok=True )
    Image.fromarray( image, "RGBA" ).save( MINIMAP_FILE )
    print( f"wrote {MINIMAP_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------
# The scene

CALLOUT_COLOUR = "0.51056,0.70698,0.49653,1"


def plan_box( e0, e1, n0, n1, z0, z1 ):
    return K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) ), ( n1 - n0, e1 - e0, z1 - z0 )


def box_collider( key, scale, trigger=True, static=True, center=( 0, 0, 0 ) ):
    return K.component( ids, "Sandbox.BoxCollider", key, Center=K.vec( center ), ColliderFlags=0, Elasticity=None,
                        Friction=None, IsTrigger=trigger, RollingResistance=None, Scale=K.vec( scale ), Static=static,
                        Surface=None, SurfaceVelocity="0,0,0" )


def ref( go_key, component_key, component_type ):
    return { "_type": "component", "component_id": ids( component_key ), "go": ids( go_key ), "component_type": component_type }


def zone_object( name, key, box_, color, display, components=(), tags="zone" ):
    centre, scale = plan_box( *box_ )
    return K.game_object( ids, name, key, centre, tags=tags, components=[
        *components,
        K.component( ids, "Zone", f"{key}/zone", Color=color, DisplayName=display ),
        box_collider( f"{key}/box", scale ),
    ] )


def spawn_object( name, key, position, team, tags="" ):
    """ A TeamSpawnPoint facing the map's middle. """
    yaw = K.plan_yaw( ( -position[0], ( 150 - position[1] ) * 0.35 ) )
    return K.game_object( ids, name, key, K.to_world( position ), K.yaw_rotation( yaw ), tags=tags, components=[
        K.component( ids, "TeamSpawnPoint", f"{key}/point", Team=team ) ] )


def mode_group( name, key, modes, children, inverse=False ):
    return K.game_object( ids, name, key, components=[
        K.component( ids, "Facepunch.GameModeObject", f"{key}/modes", GameModes=list( modes ), Inverse=inverse ) ],
        children=children )


def cash_point( name, key, cash, extract ):
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


# ( model name, scene name, collide, shadows )
SCENE_MODELS = [
    ( "riverdale_ground", "Ground", True, True ), ( "riverdale_hall", "Reactor Hall", True, True ),
    ( "riverdale_hall_dress", "Reactor Hall Dressing", True, True ), ( "riverdale_pool", "Fuel Pool", False, False ),
    ( "riverdale_water", "Pool Water", False, False ), ( "riverdale_glass", "Glass", True, False ),
    ( "riverdale_middle", "Yard Middle", True, True ), ( "riverdale_west", "West", True, True ), ( "riverdale_east", "East", True, True ),
    ( "riverdale_north", "North Lane", True, True ), ( "riverdale_boundary", "Boundary", True, True ),
    ( "riverdale_backdrop", "Backdrop", False, False ), ( "riverdale_backdrop_near", "Backdrop Near", False, True ),
]
# Models other modules add (riverdale_hall, riverdale_parts, riverdale_backdrop, riverdale_facades, riverdale_yard):
# each may define extra_models() returning [ ( model name, scene name, collide, shadows, model ), ... ]. build() fills it.
EXTRA_SCENE_MODELS = []
EXTRA_MODEL_MODULES = ( "riverdale_hall", "riverdale_parts", "riverdale_backdrop", "riverdale_facades", "riverdale_yard" )


def scene_models():
    return SCENE_MODELS + EXTRA_SCENE_MODELS + [
        ( name, f"{'Near' if '_near_' in name else 'Far'} Forest Sector {name.rsplit( '_', 1 )[-1]}", False, False ) for name in TREE_SECTORS
    ]


def model_object( name, key, model_name, collide=True, shadows=True ):
    directory = SECTOR_RESOURCE_DIR if model_name in TREE_SECTORS else RESOURCE_DIR
    path = f"{directory}/{model_name}.vmdl"
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ),
                   K.component( ids, "Facepunch.RiverdaleGratingStabilizer", f"{key}/stable-grating" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return K.game_object( ids, name, key, components=components )


def probe_object( name, centre, box_ ):
    e0, e1, n0, n1, z0, z1 = box_
    at = K.to_world( centre )
    lo = K.to_world( ( e1, n0, z0 ) ) - at
    hi = K.to_world( ( e0, n1, z1 ) ) - at
    key = f"probe/{name}"
    return K.game_object( ids, f"Probe {name}", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", Bounds={ "Mins": K.vec( lo ), "Maxs": K.vec( hi ) },
                     DelayBetweenUpdates=0.1, Feathering=0.04, FrameInterval=5, MaxDistance=512, Projection="Box",
                     RenderDynamically=True, TintColor="1,1,1,1", UpdateStrategy="OnEnabled", ZFar=8192, ZNear=8 ) ] )


def look_object():
    """ A sunrise grade: ambient occlusion, a warm white balance, a light vignette, bloom for the lamps and the pool. """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.8, Radius=48,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=6400,
                     BlendFactor=0.25, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.16, Roundness=1,
                     Smoothness=1 ),
        # Bloom for the lamps, the pool and the low sun's glare; screen-space reflections for the wet yard and floors.
        K.component( ids, "Sandbox.Bloom", "look/bloom", **{ "__version": 1 }, Mode="Additive", Strength=0.22, Threshold=1.4,
                     Tint="1,0.96,0.9,1" ),
        K.component( ids, "Sandbox.ScreenSpaceReflections", "look/ssr" ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=1.0, MaximumExposure=2.5,
                     Mode="ACES", Rate=1.3 ),
    ] )


# Volumetric haze: ( name, ( e0, e1, n0, n1, z0, z1 ), strength, colour ). The hall's is the reference's blue-grey air
# the lamps and the pool light up; the yard's a light morning haze the low sun shines through.
HAZE = [ ( "Hall Haze", ( H.E0, H.E1, H.N0, H.N1, -40, H.TOP ), 0.24, "0.80,0.88,0.97,1" ),
         ( "Yard Haze", ( PLAY[0], PLAY[1], PLAY[2], H.N0 - H.WT, 0, 900 ), 0.08, "1,0.84,0.66,1" ) ]


def haze_object( name, box_, strength, colour ):
    e0, e1, n0, n1, z0, z1 = box_
    at = K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) )
    half = ( ( n1 - n0 ) / 2, ( e1 - e0 ) / 2, ( z1 - z0 ) / 2 )
    key = f"haze/{name}"
    return K.game_object( ids, name, key, at, components=[
        K.component( ids, "Sandbox.VolumetricFogVolume", f"{key}/volume", Bounds={ "Mins": K.vec( tuple( -h for h in half ) ), "Maxs": K.vec( half ) },
                     FalloffExponent=1, Strength=strength, Color=colour ) ] )


def _lighting_plan():
    """Load the optional source-only lighting plan without a Tools import cycle."""
    path = K.ROOT / "Sources/Riverdale/lighting/riverdale_lighting.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location( "riverdale_lighting", path )
    module = importlib.util.module_from_spec( spec )
    spec.loader.exec_module( module )
    return module


def light_object( entry ):
    """Aim industrial fixtures at the surfaces they illuminate, preserving their locations."""
    name, position, color, radius, shadows = entry[:5]
    extra = entry[5] if len( entry ) > 5 else None
    direction = None
    inner, outer = 35, 70
    if isinstance( extra, dict ) and "spot" in extra:
        direction = extra["spot"]
        inner, outer = extra.get( "inner", inner ), extra.get( "outer", outer )
    elif name.startswith( "High bay " ):
        direction, inner, outer = ( 0, 0, -1 ), 30, 60
        color, radius = "1.25,1.28,1.30,1", 1500
        shadows = name in ( "High bay -250.0 600.0", "High bay 250.0 600.0",
                            "High bay -250.0 1350.0", "High bay 250.0 1350.0" )
    elif name.startswith( ( "A1 lamp ", "A2 lamp ", "Spawn room " ) ) or name in ( "B1 passage", "B1 room" ):
        direction, inner, outer = ( 0, 0, -1 ), 40, 75
        color = "0.95,0.95,0.92,1"
    elif name.startswith( "Control room " ):
        color = "1.55,1.50,1.40,1"
    elif name.startswith( "Control fill " ):
        color, radius = "1.00,0.96,0.90,1", 380
    elif name.startswith( ( "Yard mast ", "Spawn mast " ) ):
        color, radius = "0.80,0.66,0.48,1", radius * 0.8
    elif name.startswith( "Pool " ):
        # The fuel pool's calibrated cyan is intentionally left unchanged.
        pass
    if direction is not None:
        world = K.to_world( direction )
        length = math.sqrt( sum( v * v for v in world ) )
        pitch = math.degrees( math.asin( -world[2] / length ) )
        yaw = math.degrees( math.atan2( world[1], world[0] ) )
        return K.game_object( ids, name, f"light/{name}", K.to_world( position ), K.angles_rotation( pitch, yaw ),
                              tags="light_spot,light", components=[
            K.component( ids, "Sandbox.SpotLight", f"light/{name}/light", Attenuation=1,
                         ConeInner=inner, ConeOuter=outer, FogMode="Enabled", FogStrength=1,
                         LightColor=color, Radius=radius, Shadows=shadows ) ] )
    return K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
        K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
                     LightColor=color, Radius=radius, Shadows=shadows ) ] )


def write_scene( written, light_list, probe_list ):
    # The source tree models stay on disk for the saved lighting bake, but each scene draws the
    # identical polygons in smaller frustum-cullable forest sectors. Fall back to the originals
    # if any sector asset is absent (e.g. a scene-only build before sectors have been published).
    spatial_ready = bool( TREE_SECTORS ) and all( name in written for name in TREE_SECTORS )
    world = K.game_object( ids, "Riverdale", "world", children=[
        model_object( title, f"world/{name}", name, collide, shadows )
        for name, title, collide, shadows in scene_models()
        if name in written and ( ( spatial_ready and name not in TREE_SOURCE_NAMES )
                                 or ( not spatial_ready and name not in TREE_SECTORS ) ) ] )
    light_objects = [ light_object( light ) for light in light_list ]

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

    e0, e1, n0, n1, z0, z1 = BUY_ZONE
    buy_zones = [
        zone_object( "buyzone_t", "buy/t", ( -e1, -e0, n0, n1, z0, z1 ), "1,0.18,0.2,1", "Red Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/t/zone_buy", Team="Terrorist" ) ] ),
        zone_object( "buyzone_ct", "buy/ct", ( e0, e1, n0, n1, z0, z1 ), "0,0.41569,1,1", "Blue Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/ct/zone_buy", Team="CounterTerrorist" ) ] ),
    ]

    callout_objects = []
    for k, c in enumerate( callouts() ):
        name, ce0, ce1, cn0, cn1, cz0, cz1 = c
        callout_objects.append( zone_object( name, f"callout/{k}/{name}", ( ce0, ce1, cn0, cn1, cz0, cz1 ), CALLOUT_COLOUR,
                                             name, [ K.component( ids, "Facepunch.MapLocation", f"callout/{k}/{name}/location" ) ] ) )

    play_centre, play_scale = plan_box( PLAY[0], PLAY[1], PLAY[2], PLAY[3], -300, 1500 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
    clip_objects = []
    for k, ( name, centre, yaw, size ) in enumerate( P.CLIPS ):
        key = f"clip/{k}"
        # The clip's local X follows its segment after yaw_rotation(yaw - 90): plan east maps to world -Y.
        # Length therefore belongs on local X, thickness on Y. Swapping them makes rail clips cross the bars.
        clip_objects.append( K.game_object( ids, f"Player Clip {name} {k}", key, K.to_world( centre ), K.yaw_rotation( yaw - 90.0 ),
                                            tags="playerclip", components=[ box_collider( f"{key}/box", ( size[0], size[1], size[2] ), trigger=False ) ] ) )
    for name, b in ROOF_CLIPS:
        centre, scale = plan_box( *b )
        clip_objects.append( K.game_object( ids, f"Player Clip {name}", f"clip/{name}", centre, tags="playerclip", components=[
            box_collider( f"clip/{name}/box", scale, trigger=False ) ] ) )
    pipe_objects = []
    for k, (centre, direction, radius) in enumerate(P.PIPE_SOLIDS):
        de, dn, dz = direction
        horizontal = math.hypot( de, dn )
        length = math.sqrt( de * de + dn * dn + dz * dz )
        # The box's X axis follows the real pipe, including pitched and upright runs.
        pitch = -math.degrees( math.atan2( dz, horizontal ) )
        yaw = math.degrees( math.atan2( -de, dn ) ) if horizontal > 1e-6 else 0.0
        key = f"pipe/solid/{k}"
        pipe_objects.append( K.game_object( ids, f"Pipe Solid {k}", key, K.to_world( centre ),
                                            K.angles_rotation( pitch, yaw ), tags="solid", components=[
            box_collider( f"{key}/box", ( length + 0.4, radius * 1.8, radius * 1.8 ), trigger=False ) ] ) )
    # Yard Props is drawn-only for accurate weathering and overlays. Its annotated bulky
    # equipment has occupied space, however: physical drums, pallets, bins and reels
    # must stop players as surely as the colliding equipment cases in the main meshes.
    prop_objects = []
    try:
        import riverdale_yard as Y
        for category, name, ( e0, e1, n0, n1 ), height in Y.NOTES:
            if category != "prop" or height < 20 or min( e1 - e0, n1 - n0 ) < 9:
                continue
            key = f"prop/solid/{len(prop_objects)}"
            centre, scale = plan_box( e0, e1, n0, n1, 0, height )
            prop_objects.append( K.game_object( ids, f"Prop Solid {name}", key, centre, tags="solid", components=[
                box_collider( f"{key}/box", scale, trigger=False ) ] ) )
    except ModuleNotFoundError as error:
        if error.name != "riverdale_yard":
            raise
    catch = K.game_object( ids, "Catch Floor", "catch", ( 0, 0, CATCH_FLOOR_Z ), components=[
        box_collider( "catch/box", ( 80000, 80000, 100 ), trigger=False ) ] )

    objective_spots = [
        K.game_object( ids, f"Domination {label}", f"objective/dom/{label}", K.to_world( p ), components=[
            K.component( ids, "Facepunch.ObjectiveSpot", f"objective/dom/{label}/spot", Kind="Domination", Label=label ) ] )
        for label, p in DOMINATION ]
    objective_spots += [
        K.game_object( ids, f"Hot Zone {label}", f"objective/hot/{label}", K.to_world( p ), components=[
            K.component( ids, "Facepunch.ObjectiveSpot", f"objective/hot/{label}/spot", Kind="HotZone", Label=label ) ] )
        for label, p in HOT_ZONES ]
    cash = [ cash_point( name, f"cash/{name}", c, x ) for name, c, x in CASH_POINTS ]

    lighting = _lighting_plan()
    # Reuse captured cubes and baked indirect light after the editor has preserved them.
    # No asset files are created here: prime coordinates the first capture and bake.
    saved_probes = lighting.reflection_probes_object() if lighting is not None else None
    saved_indirect = lighting.indirect_light_object() if lighting is not None else None
    objects = [
        K.game_object( ids, "Scene Information", "info", components=[
            K.component( ids, "Sandbox.SceneInformation", "info/scene", Title=TITLE, Author=None, Changes="",
                         Description="A nuclear power station under snowy mountains at sunrise after rain: the reactor hall "
                                     "round its glowing fuel pool, and the wet yard between the buildings, with the containment "
                                     "domes and cooling towers behind.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 2500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # A sunrise: the sun 16 degrees above the horizon, north of east.
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor=SUN_COLOUR, ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.10,0.12,0.16,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="1,1,1,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.72", StartDistance=2400,
                         EndDistance=75000, FalloffExponent=1.3, Height=12000, VerticalFalloffExponent=1.2 ),
        ] ),
        look_object(),
        world,
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        saved_probes or K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in probe_list ] ),
        K.game_object( ids, "Volumetric Fog", "haze", children=[ haze_object( *h ) for h in HAZE ] ),
        *( [ saved_indirect ] if saved_indirect else [] ),
        mode_group( "Team Spawns", "spawns", ( "Deathmatch", "Gun Game" ), team_spawns, inverse=True ),
        mode_group( "Deathmatch Spawns", "spawns/dm", ( "Deathmatch", "Gun Game" ), dm_spawns ),
        mode_group( "Retakes Spawns", "spawns/retakes", ( "Retakes", ), retakes_spawns ),
        K.game_object( ids, "Bomb Sites", "sites", children=bomb_sites ),
        K.game_object( ids, "Buy Zones", "buy", children=buy_zones ),
        K.game_object( ids, "Callouts", "callouts", children=callout_objects ),
        play_area,
        K.game_object( ids, "Player Clips", "clips", children=clip_objects ),
        K.game_object( ids, "Pipe Solids", "pipe/solids", children=pipe_objects ),
        K.game_object( ids, "Yard Prop Solids", "prop/solids", children=prop_objects ),
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
                "Bounds": { "Mins": K.vec( K.to_world( ( PLAY[1], PLAY[2], -40 ) ) ),
                            "Maxs": K.vec( K.to_world( ( PLAY[0], PLAY[3], NAV_TOP ) ) ) },
            },
        },
        "ResourceVersion": 3,
        "Title": TITLE,
        "Description": None,
        "__references": [],
        "__version": 3,
    }
    SCENE_FILE.parent.mkdir( parents=True, exist_ok=True )
    K.write_text( SCENE_FILE, json.dumps( scene, indent=2 ), newline=None )
    print( f"wrote {SCENE_FILE.relative_to( K.ROOT )}" )


# Roofs nobody should stand on (containers, the annexes, B1's core, the turbine annex): clipped up to 1500.
ROOF_CLIPS = []


def roof_clips():
    out = []
    for sx in ( -1, 1 ):
        f = -sx
        e0, e1 = sorted( ( f * ANNEX[0], f * ANNEX[1] ) )
        out.append( ( f"Annex {sx}", ( e0, e1, ANNEX[2], ANNEX[3], ANNEX_TOP, 1500 ) ) )
        for ce, cn, axis in ( ( -1000, -1180, "e" ), ( -760, -1520, "n" ), ( -1560, -1080, "n" ) ):
            hl = 120.0
            if axis == "n":
                out.append( ( f"Container {sx} {ce}", ( f * ce - 49, f * ce + 49, cn - hl, cn + hl, 102, 1500 ) ) )
            else:
                a, b = sorted( ( f * ce - hl, f * ce + hl ) )
                out.append( ( f"Container {sx} {ce}", ( a, b, cn - 49, cn + 49, 102, 1500 ) ) )
        a, b = sorted( ( f * PLAY[0], f * ( PLAY[0] - 300 ) ) )
        out.append( ( f"Boundary {sx}", ( a, b, PLAY[2], PLAY[3], BOUNDARY_TOP, 1500 ) ) )
        a, b = sorted( ( f * SPAWN_TALL[0], f * SPAWN_TALL[1] ) )
        out.append( ( f"Spawn building {sx}", ( a, b, SPAWN_TALL[2], SPAWN_TALL[3], SPAWN_TOP, 1500 ) ) )
        a, b = sorted( ( f * TURBINE_SIDE[0], f * TURBINE_SIDE[1] ) )
        out.append( ( f"Turbine block {sx}", ( a, b, TURBINE_SIDE[2], TURBINE_SIDE[3], 420, 1500 ) ) )
    out.append( ( "B1 Core", ( CORE[0], CORE[1], CORE[2], CORE[3], CORE_TOP, 1500 ) ) )
    out.append( ( "Turbine Annex", ( TURBINE[0], TURBINE[1], TURBINE[2], TURBINE[3], TURBINE_TOP, 1500 ) ) )
    out.append( ( "Hall", ( H.E0 - H.WT, H.E1 + H.WT, H.N0 - H.WT, H.N1 + H.WT, H.ROOF, 1500 ) ) )
    out.append( ( "Perimeter", ( PLAY[0] - 400, PLAY[1] + 400, NORTH_WALL_N, NORTH_WALL_N + 30, 220, 1500 ) ) )
    out.append( ( "Turbine Hall", ( PLAY[0] - 400, PLAY[1] + 400, PLAY[2] - 1000, PLAY[2], 960, 1500 ) ) )
    return out


# ---------------------------------------------------------------------------------------------------------------------

def partition_trees( source, original_name ):
    """Split drawn-only trees by azimuth without rebuilding any polygon, UV or normal.

    Model bounds then cover roughly 1/8 of the horizon each, so frustum culling can discard
    distant trees hidden behind the player. The original source meshes stay untouched because
    the completed indirect-light and reflection captures were made with that exact geometry.
    """
    assert not source.boxes and not source.hulls, "Only draw-only meshes may be sectorised"
    result = {}
    for k in range( TREE_SECTOR_COUNT ):
        name = f"{original_name}_sector_{k:02d}"
        sector = K.Model()
        sector.uv_source_name = original_name
        sector.material_overrides = source.material_overrides.copy()
        sector.tile_overrides = source.tile_overrides.copy()
        sector.anchored_paints = set( getattr( source, "anchored_paints", () ) )
        sector.decal_paints = set( getattr( source, "decal_paints", () ) )
        sector.grain_paints = set( source.grain_paints )
        result[name] = sector
    names = list( result )
    for paint, polygons in source.polygons.items():
        for index, polygon in enumerate( polygons ):
            points = polygon[0]
            centre = np.mean( points, axis=0 )
            azimuth = math.atan2( float( centre[0] ), float( centre[1] ) ) % ( 2 * math.pi )
            sector_index = min( int( azimuth * TREE_SECTOR_COUNT / ( 2 * math.pi ) ), TREE_SECTOR_COUNT - 1 )
            destination = result[names[sector_index]]
            new_index = len( destination.polygons[paint] )
            destination.polygons[paint].append( polygon )
            key = ( paint, index )
            if key in source.polygon_uvs:
                destination.polygon_uvs[paint, new_index] = source.polygon_uvs[key]
            if key in source.polygon_normals:
                destination.polygon_normals[paint, new_index] = source.polygon_normals[key]
    assert all( not K.is_empty( m ) for m in result.values() ), "Empty forest sector"
    for paint, polygons in source.polygons.items():
        assert sum( len( m.polygons[paint] ) for m in result.values() ) == len( polygons ), paint
    assert sum( len( m.polygon_uvs ) for m in result.values() ) == len( source.polygon_uvs )
    assert sum( len( m.polygon_normals ) for m in result.values() ) == len( source.polygon_normals )
    return result


def build():
    """ Every model by name. """
    P.reset()
    hall, hall_dress, pool, water, glass = H.build()
    middle, west, east, north, boundary = K.Model(), K.Model(), K.Model(), K.Model(), K.Model()
    b1( middle, glass )
    turbine_annex( middle )
    middle_yard( middle )
    for sx, m in ( ( -1, west ), ( 1, east ) ):
        annex( m, sx )
        court( m, sx )
        yard_side( m, sx )
        spawn_side( m, sx )
    north_lane( north )
    turbine_hall( boundary )
    models = {
        "riverdale_ground": ground(), "riverdale_hall": hall, "riverdale_hall_dress": hall_dress, "riverdale_pool": pool,
        "riverdale_water": water, "riverdale_glass": glass, "riverdale_middle": middle, "riverdale_west": west,
        "riverdale_east": east, "riverdale_north": north, "riverdale_boundary": boundary,
    }
    try:
        import riverdale_backdrop as BD
        far, near = BD.build()
        models["riverdale_backdrop"] = far
        models["riverdale_backdrop_near"] = near
    except ImportError:
        pass
    import importlib
    EXTRA_SCENE_MODELS.clear()
    for module_name in EXTRA_MODEL_MODULES:
        try:
            module = importlib.import_module( module_name )
        except ModuleNotFoundError as error:
            if error.name != module_name:
                raise
            continue
        if not hasattr( module, "extra_models" ):
            continue
        for name, title, collide, shadows, model in module.extra_models():
            assert name not in models, f"{module_name} adds {name}, which already exists"
            models[name] = model
            EXTRA_SCENE_MODELS.append( ( name, title, collide, shadows ) )
    for model in models.values():
        configure( model )
    TREE_SECTORS.clear()
    for original in TREE_SOURCE_NAMES:
        if original in models:
            TREE_SECTORS.update( partition_trees( models[original], original ) )
    ROOF_CLIPS[:] = roof_clips()
    return models


def preview_setup():
    """ The flat preview's colours, sun, sky and fog. """
    for paint in RM.all_paints():
        if paint in RM.PAINTED:
            PV._colours[paint] = np.array( RM.PAINTED[paint][0] ) / 255.0
            continue
        for ext in ( "jpg", "png" ):
            path = RM.OUT_DIR / f"{paint}_color.{ext}"
            if path.exists():
                small = Image.open( path ).convert( "RGB" ).resize( ( 64, 32 ) )
                PV._colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
                break
    PV._colours["rv_letters_dark"] = np.array( ( 0.12, 0.12, 0.13 ) )
    PV._colours["rv_letters_light"] = np.array( ( 0.75, 0.75, 0.74 ) )
    PV._colours["rv_pool_water"] = np.array( ( 0.2, 0.75, 0.9 ) )
    p, y = math.radians( SUN_PITCH ), math.radians( SUN_YAW )
    world = np.array( ( math.cos( p ) * math.cos( y ), math.cos( p ) * math.sin( y ), -math.sin( p ) ) )
    PV.SUN = -np.array( ( -world[1], world[0], world[2] ) )
    PV.SKY = ( np.array( ( 0.95, 0.86, 0.76 ) ), np.array( ( 0.45, 0.58, 0.80 ) ) )
    PV.FOG = np.array( ( 0.92, 0.82, 0.72 ) )


VIEWS = ( ( "yard_reference", ( 560, -1010, 170 ), ( 2000, -880, 300 ), 84 ),
          ( "hall_reference", ( -260, -150, 180 ), ( -40, 1400, 470 ), 88 ),
          ( "aerial", ( -2600, -3600, 3400 ), ( 0, 200, 0 ), 60 ),
          ( "north_lane", ( -1900, 2250, 70 ), ( 1000, 2200, 60 ), 75 ),
          ( "upper", ( -930, 1500, 350 ), ( 600, 900, 250 ), 80 ),
          ( "west_yard", ( -560, -1010, 170 ), ( -2000, -880, 300 ), 84 ) )


def write_map_art( models ):
    preview_setup()
    opaque, glass = PV.triangles( models ), PV.triangles( models, glass=True )
    _, eye, target, fov = VIEWS[0]
    image = PV.perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=fov )
    MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
    image.resize( ( 1920, 1080 ), Image.LANCZOS ).convert( "RGB" ).save( MAP_ART_FILE )
    print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", metavar="DIR", help="also write flat views and the reach grid's picture here" )
    parser.add_argument( "--views", nargs="*", help="only these views" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    parser.add_argument( "--no-models", action="store_true", help="don't write the models (checks and previews only)" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture" )
    parser.add_argument( "--stage", metavar="DIR", help="write the models, scene and radar picture under DIR, laid out as Assets, "
                                                        "instead of into Assets (publish them from there)" )
    args = parser.parse_args()
    if args.stage:
        global OUT_DIR, SCENE_FILE, MINIMAP_FILE, MAP_ART_FILE
        stage = Path( args.stage ).resolve()
        OUT_DIR = stage / RESOURCE_DIR
        SCENE_FILE = stage / "scenes/maps/Riverdale/riverdale.scene"
        MINIMAP_FILE = stage / MINIMAP_PATH
        MAP_ART_FILE = stage / MAP_ART_PATH

    missing = [ p for p in RM.all_paints() if not ( RM.OUT_DIR / f"{p}.vmat" ).exists() ]
    if missing:
        print( f"run Tools/riverdale_materials.py first: no material for {', '.join( missing )}" )
    models = build()
    written = set()
    for name, model in models.items():
        if K.is_empty( model ):
            print( f"{name}: empty, not written" )
            continue
        written.add( name )
        if args.no_models:
            continue
        count = K.write_model( OUT_DIR, RESOURCE_DIR, name, model )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
    sector_dir = OUT_DIR.parent / "riverdale_sectors"
    for name, model in TREE_SECTORS.items():
        if not args.no_models:
            count = K.write_model( sector_dir, SECTOR_RESOURCE_DIR, name, model )
            print( f"{name}: {count} triangles (render-only forest sector)" )
        if not args.no_models or ( sector_dir / f"{name}.vmdl" ).exists():
            written.add( name )
    if R.MISSING:
        print( "from railhead_props, left out:" )
        for name, why in sorted( R.MISSING.items() ):
            print( f"  {name}: {why}" )
    if R.UNKNOWN_PAINTS:
        print( f"paints with no material: {', '.join( sorted( R.UNKNOWN_PAINTS ) )}" )
    light_list = H.lights() + list( P.LIGHTS )
    probe_list = probes()
    print( f"{len( light_list )} lights ({sum( 1 for l in light_list if l[4] )} shadowed), {len( probe_list )} probes, "
           f"{len( P.CLIPS ) + len( ROOF_CLIPS )} clips" )

    solid = [ models[name] for name, _, collide, _ in scene_models() if collide and name in models ]
    print( "checking spots:" )
    problems = R.check_spots( R.collision_aabbs( solid ), all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    out = Path( args.preview ) if args.preview else None
    if out:
        out.mkdir( parents=True, exist_ok=True )
    bounds = ( PLAY[0], PLAY[1], PLAY[2], PLAY[3] )
    cut_off = R.check_reach( solid, all_spots(), out / "reach.png" if out else None, bounds=bounds )
    print( f"  {cut_off} spot(s) cut off from the spawns" )
    seen = R.check_retakes_sight( R.Blockers( solid ), RETAKES )
    print( f"  {seen} Retakes pair(s) in sight of each other" )

    if not args.no_scene:
        write_minimap( solid )
        write_scene( written, light_list, probe_list )
    if args.art:
        write_map_art( list( models.values() ) )
    if out:
        preview_setup()
        opaque, glass = PV.triangles( list( models.values() ) ), PV.triangles( list( models.values() ), glass=True )
        for name, eye, target, fov in VIEWS:
            if args.views and name not in args.views:
                continue
            PV.perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=fov ).convert( "RGB" ).save( out / f"{name}.png" )
            print( f"wrote {out / f'{name}.png'}" )


if __name__ == "__main__":
    main()
