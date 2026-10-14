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

Plan coordinates: e east, n north, z up, inches. The play area is e -2300..2300, n -1750..2050, the ground at z 0.
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
from riverdale_parts import v, card, box, UP, METAL, STONE

TITLE = "Riverdale"
OUT_DIR = K.ASSETS / "models/maps/riverdale"
RESOURCE_DIR = "models/maps/riverdale"
SCENE_FILE = K.ASSETS / "scenes/maps/Riverdale/riverdale.scene"
MINIMAP_PATH = "ui/minimaps/minimap_riverdale.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_riverdale.png"
MAP_ART_PATH = "ui/maps/riverdale.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "5f1c9a72-8e34-4b6d-a2c7-91e0d4b36f85" )

SUN_PITCH, SUN_YAW = 16.0, 123.0          # riverdale_sky's: 16 degrees up, 33 degrees north of east
SUN_COLOUR = "1.55,1.02,0.58,1"
SKY_MATERIAL = "materials/riverdale/sky/riverdale_sky.vmat"
SKY_EXPOSURE = 1.6
FOG_COLOUR = "1.02,0.86,0.70"
CATCH_FLOOR_Z = -3000

PLAY = ( -2300.0, 2300.0, -1750.0, 2050.0 )
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
SPAWN_STAIR = ( -1790.0, -2020.0, -960.0, -884.0 )       # foot e, head e, n0, n1
SPAWN_ROOM_Z = 200.0
SPAWN_TOP = 380.0
BOUNDARY_TOP = 360.0
NORTH_WALL_N = 2050.0


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
    H.wall( m, "e", *E( e0, e1 ), n0, n0 + t, 0, ANNEX_TOP, [ ( *E( so[0], so[1] ), so[2] ) ] )
    H.wall( m, "e", *E( e0, e1 ), n1 - t, n1, 0, ANNEX_TOP, [ ( *E( ANNEX_NORTH_DOOR[0], ANNEX_NORTH_DOOR[1] ), ANNEX_NORTH_DOOR[2] ) ] )
    H.wall( m, "n", n0, n1, *E( e0, e0 + t ), 0, ANNEX_TOP, [ ANNEX_WEST_DOOR ] )
    H.wall( m, "n", n0, H.N0 - H.WT, *E( e1 - t, e1 ), 0, ANNEX_TOP )
    box( m, *E( e0, e1 ), n0, n1, ANNEX_TOP - 20, ANNEX_TOP, { "default": "rv_wall", "-z": "rv_steel" }, STONE )
    for a, b, c, d in ( ( e0, e1, n0, n0 + 10 ), ( e0, e1, n1 - 10, n1 ), ( e0, e0 + 10, n0, n1 ), ( e1 - 10, e1, n0, H.N0 - H.WT ) ):
        box( m, *E( a, b ), c, d, ANNEX_TOP, ANNEX_TOP + 30, "rv_wall", STONE )
    # Railing round the roof's edge (the reference's yellow guard rail along A1's top).
    P.railing( m, mirror_pts( [ ( e0 + 6, n0 + 6 ), ( e1 - 6, n0 + 6 ), ( e1 - 6, H.N0 - H.WT ) ], f ), ANNEX_TOP + 30, height=38, post_every=70 )
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
    # The south face: the name, a louvre, the sign, hazard stripes, beacons, lamps, pipes.
    face = n0
    out = v( 0, -1, 0 )
    right = np.cross( UP, out )
    P.letters( m, label, ( f * -1250, face, 258 ), right, 118, "dark" )
    P.louvre( m, ( f * -1480, face, 258 ), right, 150, 110 )
    P.louvre( m, ( f * -1640, face, 120 ), right, 60, 44, blades=8 )
    sign = "reactor_hall_r" if sx > 0 else "reactor_hall_l"
    P.letters( m, sign, ( f * -1112, face, 104 ), right, 50, "dark" )
    for e in ( so[0], so[1] ):
        side = -1 if e == so[0] else 1
        P.quad( m, "rv_hazard", ( f * ( e - side * 8 ), face - 0.4, 95 ), right, UP, 14, 190, off=0.0 )
        P.beacon( m, f"{label} opening beacon {e}", ( f * ( e - side * 14 ), face - 3, 178 ) )
    P.wall_light( m, f"{label} opening lamp", ( f * ( so[0] + so[1] ) / 2, face, 186 ), out, "warm", 360 )
    P.wall_light( m, f"{label} corner lamp", ( f * -1640, face, 210 ), out, "warm", 300 )
    for k, r in enumerate( ( 7.0, 5.0 ) ):
        z = 210 + k * 16
        P.pipe( m, mirror_pts( [ ( e0 + 20, face - 14 - k * 4, z ), ( e1 + 14 + k * 4, face - 14 - k * 4, z ), ( e1 + 14 + k * 4, H.N0 - H.WT, z ) ], f ),
                r, "rv_pipe", 12 )
    for e in np.arange( e0 + 60, e1, 140.0 ):
        box( m, *E( e - 3, e + 3 ), face - 22, face, 200, 204, "rv_steel" )
    # The west face (spawn side): a door, a lamp and a stencilled unit number.
    wface = f * e0
    wout = v( -f, 0, 0 )
    wright = np.cross( UP, wout )
    P.wall_light( m, f"{label} west door lamp", ( wface, -200, 140 ), wout, "warm", 300 )
    P.letters( m, label, ( wface, 60, 232 ), wright, 90, "dark" )
    P.plate( m, "danger", ( wface, -200, 165 ), wright, 18, off=0.4 )


def court( m, sx ):
    """ The court north of the annex: a transformer, tanks, a pipe rack and cover. """
    f = -sx
    # Transformer: a tank with radiator fins and bushings, on a plinth.
    c = ( f * -1420, 640 )
    box( m, c[0] - 70, c[0] + 70, c[1] - 50, c[1] + 50, 0, 10, "rv_plinth", STONE )
    box( m, c[0] - 50, c[0] + 50, c[1] - 34, c[1] + 34, 10, 100, "rv_steel", METAL )
    for k in range( 9 ):
        e = c[0] - 44 + k * 11
        for sn in ( -1, 1 ):
            box( m, e - 1.5, e + 1.5, c[1] + sn * 34, c[1] + sn * 50, 18, 92, "rv_steel" )
    for k in range( 3 ):
        e = c[0] - 26 + k * 26
        P.cylinder( m, ( e, c[1] ), 4.5, 100, 140, "rv_ring_white", 10, top="rv_dark" )
    P.railing( m, mirror_pts( [ ( -1520, 560 ), ( -1320, 560 ), ( -1320, 720 ), ( -1520, 720 ) ], f ), 0, "rv_yellow", height=40,
               closed=True, clip_to=40, name="transformer fence" )
    # A pair of tanks against the hall wall.
    for n in ( 1150.0, 1290.0 ):
        P.tank( m, ( f * -1110, n ), 56, 280, "rv_white", facing=( -f, 0 ) )
    # Pipe rack across the court at 260, from the hall's wall to the annex roof.
    for n in ( 980.0, 1450.0 ):
        for e in ( -1640.0, -1360.0, -1080.0 ):
            box( m, *sorted( ( f * ( e - 5 ), f * ( e + 5 ) ) ), n - 5, n + 5, 0, 270, "rv_steel", METAL )
        P.i_beam( m, ( f * -1650, n, 270 ), ( f * -1040, n, 270 ), 12, 8, "rv_steel" )
    for k, r in enumerate( ( 9.0, 6.0, 6.0, 4.0 ) ):
        n = 990 + k * 30 if k < 2 else 1380 + k * 20
        P.pipe( m, mirror_pts( [ ( -1700, 1000 + k * 26, 288 ), ( -1040, 1000 + k * 26, 288 ) ], f ), r, "rv_pipe", 12, caps=False )
    for k, r in enumerate( ( 8.0, 5.0 ) ):
        P.pipe( m, mirror_pts( [ ( -1660, 1000 + k * 26, 288 ), ( -1660, 1430 + k * 0, 288 ), ( -1660, 1660, 288 ) ], f ), r, "rv_pipe", 12, caps=False )
    # Cover: barriers and cases.
    P.jersey( m, ( f * -1250, 900 ), ( 1, 0 ) )
    P.jersey( m, ( f * -1500, 1080 ), ( 0, 1 ) )
    P.jersey( m, ( f * -1350, 1500 ), ( 1, 0.2 ) )
    for k, ( e, n ) in enumerate( ( ( -1620, 840 ), ( -1180, 420 ), ( -1600, 1560 ), ( -1200, 1580 ) ) ):
        P.case_stack( m, ( f * e, n ), ( 1, 0 ), "olive", seed=60 + k + ( 0 if sx < 0 else 50 ) )
    P.wall_light( m, f"Court lamp {sx} a", ( f * ( H.E0 - H.WT ), 900, 260 ), v( -f, 0, 0 ), "warm", 420 )
    P.wall_light( m, f"Court lamp {sx} b", ( f * ( H.E0 - H.WT ), 1450, 260 ), v( -f, 0, 0 ), "warm", 420 )


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
    # The turbine building's block on the yard's south edge, its sign towards the yard's middle, a loading bay.
    t0, t1 = sorted( ( f * TURBINE_SIDE[0], f * TURBINE_SIDE[1] ) )
    box( m, t0, t1, TURBINE_SIDE[2], TURBINE_SIDE[3], 0, 420, "rv_wall", STONE )
    for a, b in ( ( t0, t0 + 10 ), ( t1 - 10, t1 ) ):
        box( m, a, b, TURBINE_SIDE[2], TURBINE_SIDE[3], 420, 450, "rv_wall", STONE )
    box( m, t0, t1, TURBINE_SIDE[3] - 10, TURBINE_SIDE[3], 420, 450, "rv_wall", STONE )
    face = f * TURBINE_SIDE[1]
    out = v( f, 0, 0 )
    right = np.cross( UP, out )
    P.letters( m, "turbine_r" if sx > 0 else "turbine_l", ( face, -1350, 150 ), right, 80, "dark" )
    bay0, bay1 = -1640.0, -1470.0
    for k in range( 18 ):
        P.quad( m, "rv_louvre", ( face, ( bay0 + bay1 ) / 2, 5 + k * 10 ), right, UP, bay1 - bay0 - 4, 9, off=0.6 )
    P.quad( m, "rv_hazard", ( face, bay0 - 7, 90 ), right, UP, 12, 180, off=0.4 )
    P.quad( m, "rv_hazard", ( face, bay1 + 7, 90 ), right, UP, 12, 180, off=0.4 )
    P.wall_light( m, f"Turbine bay lamp {sx}", ( face, ( bay0 + bay1 ) / 2, 200 ), out, "warm", 380 )
    P.wall_light( m, f"Turbine sign lamp {sx}", ( face, -1290, 240 ), out, "warm", 320 )
    P.beacon( m, f"Turbine block beacon {sx}", ( face + f * 6, -1262, 450 ) )
    nface = TURBINE_SIDE[3]
    nout = v( 0, 1, 0 )
    nright = np.cross( UP, nout )
    P.louvre( m, ( f * -1500, nface, 300 ), nright, 220, 140 )
    P.door( m, ( f * -1500, nface, 0 ), nright, 80, 96, double=False )
    P.wall_light( m, f"Turbine block door lamp {sx}", ( f * -1500, nface, 122 ), nout, "warm", 300 )
    # Big pipes from the block up over the yard to the annex, on a truss: the reference's pipe gantry.
    for e in ( -1640.0, -1360.0 ):
        P.truss( m, ( f * e, TURBINE_SIDE[3], 330 ), ( f * e, ANNEX[2], 330 ), 44, "rv_steel", panel=70 )
    for n in np.arange( TURBINE_SIDE[3] + 20, ANNEX[2], 90.0 ):
        a, b = sorted( ( f * -1660, f * -1340 ) )
        box( m, a, b, n - 2, n + 2, 372, 376, "rv_steel" )
    for k, ( e, r ) in enumerate( ( ( -1610, 16.0 ), ( -1560, 12.0 ), ( -1515, 12.0 ), ( -1470, 8.0 ), ( -1430, 8.0 ) ) ):
        P.pipe( m, [ ( f * e, TURBINE_SIDE[3] - 60, 376 + r ), ( f * e, ANNEX[2] + 10, 376 + r ) ], r, "rv_pipe", 14, caps=False )
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


def spawn_side( m, sx ):
    """ The spawn strip (west e -2300..-1700): the boundary building's facade, the spawn building (B2 west, B1 east:
    the reference's, a stair up past its stencilled wing to a double door), a guard hut, barriers and lamps. """
    f = -sx

    def E( a, b ):
        return tuple( sorted( ( f * a, f * b ) ) )

    e_face = f * PLAY[0]
    a, b = E( PLAY[0], PLAY[0] - 300 )
    box( m, a, b, PLAY[2], PLAY[3], 0, BOUNDARY_TOP, "rv_wall", STONE )
    out = v( f, 0, 0 )
    right = np.cross( UP, out )
    for n in np.arange( PLAY[2] + 120, PLAY[3] - 60, 300.0 ):
        box( m, *sorted( ( e_face, e_face + f * 14 ) ), n - 22, n + 22, 0, BOUNDARY_TOP + 20, "rv_wall", STONE )
    for k, n in enumerate( np.arange( PLAY[2] + 270, PLAY[3] - 200, 300.0 ) ):
        if SPAWN_TALL[2] - 100 < n < SPAWN_TALL[3] + 100:
            continue
        lit = k % 4 == 1
        P.quad( m, "rv_window_lit" if lit else "rv_window_dark", ( e_face, n, 260 ), right, UP, 150, 70, off=0.3 )
        P.quad( m, "rv_frame", ( e_face, n, 222 ), right, UP, 160, 6, off=0.5 )
        if k % 3 == 1:
            P.door( m, ( e_face, n, 0 ), right, 96, 100 )
            P.wall_light( m, f"Spawn door lamp {sx} {k}", ( e_face, n, 130 ), out, "warm", 360 )
        else:
            P.louvre( m, ( e_face, n, 100 ), right, 120, 90 )
    # The spawn building's tall part: walls, the room's floor and roof, a strip window on its north face.
    t0, t1, tn0, tn1 = SPAWN_TALL
    w = 20.0
    door_a = ( -940.0, -870.0, SPAWN_ROOM_Z + 96, SPAWN_ROOM_Z )
    door_b = ( -800.0, -740.0, SPAWN_ROOM_Z + 96, SPAWN_ROOM_Z )
    H.wall( m, "n", tn0, tn1, *E( t1 - w, t1 ), 0, SPAWN_TOP, [ door_a, door_b ] )
    H.wall( m, "e", *E( t0, t1 ), tn0, tn0 + w, 0, SPAWN_TOP )
    H.wall( m, "e", *E( t0, t1 ), tn1 - w, tn1, 0, SPAWN_TOP )
    box( m, *E( t0, t1 - w ), tn0 + w, tn1 - w, 0, SPAWN_ROOM_Z - 16, "rv_wall", STONE )
    box( m, *E( t0, t1 - w ), tn0 + w, tn1 - w, SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z, { "default": None, "+z": "rv_floor" } )
    box( m, *E( t0, t1 ), tn0, tn1, SPAWN_TOP - 18, SPAWN_TOP, { "default": "rv_wall", "-z": "rv_steel" }, STONE )
    for a_, b_, c_, d_ in ( ( t0, t1, tn0, tn0 + 10 ), ( t0, t1, tn1 - 10, tn1 ), ( t1 - 10, t1, tn0, tn1 ) ):
        box( m, *E( a_, b_ ), c_, d_, SPAWN_TOP, SPAWN_TOP + 26, "rv_wall", STONE )
    nout = v( 0, 1, 0 )
    nright = np.cross( UP, nout )
    box( m, *E( t0 + 30, t1 - 30 ), tn1, tn1 + 3, 236, 240, "rv_frame" )
    box( m, *E( t0 + 30, t1 - 30 ), tn1, tn1 + 3, 320, 324, "rv_frame" )
    P.quad( m, "rv_window_lit", ( f * ( t0 + t1 ) / 2, tn1, 280 ), nright, UP, abs( t1 - t0 ) - 60, 80, off=0.3 )
    P.ceiling_light( m, f"Spawn room {sx}", ( f * ( t0 + t1 ) / 2, ( tn0 + tn1 ) / 2, SPAWN_TOP - 26 ), ( 0, 1 ), "cool", 380 )
    for k, n in enumerate( ( -1100.0, -1040.0, -980.0 ) ):
        box( m, *E( t0 + 4, t0 + 24 ), n - 26, n + 26, SPAWN_ROOM_Z, SPAWN_ROOM_Z + 80, "rv_steel", METAL )
    P.case_stack( m, ( f * -2200, -760 ), ( 0, 1 ), "dark", seed=150 + sx )
    # The wing (its roof part of the upper deck), the landing and the stair.
    box( m, *E( SPAWN_WING[0], SPAWN_WING[1] ), SPAWN_WING[2], SPAWN_WING[3], 0, SPAWN_ROOM_Z, { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    box( m, *E( SPAWN_LANDING[0], SPAWN_LANDING[1] ), SPAWN_LANDING[2], SPAWN_LANDING[3], SPAWN_ROOM_Z - 16, SPAWN_ROOM_Z,
         { "default": "rv_wall", "+z": "rv_floor" }, STONE )
    box( m, *E( SPAWN_LANDING[1] - 12, SPAWN_LANDING[1] ), SPAWN_LANDING[2], SPAWN_LANDING[2] + 12, 0, SPAWN_ROOM_Z - 16, "rv_wall", STONE )
    mid = ( SPAWN_STAIR[2] + SPAWN_STAIR[3] ) / 2
    P.stairs( m, ( f * SPAWN_STAIR[0], mid ), ( f * SPAWN_STAIR[1], mid ), SPAWN_STAIR[3] - SPAWN_STAIR[2], 0, SPAWN_ROOM_Z,
              tread="rv_plinth", side="rv_plinth", solid_under=True, surface=STONE, name=f"spawn stair {sx}" )
    label = "B1" if sx > 0 else "B2"
    wface = f * SPAWN_WING[1]
    wout = v( -f, 0, 0 )
    wright = np.cross( UP, wout )
    wn = ( SPAWN_WING[2] + SPAWN_WING[3] ) / 2
    P.letters( m, label, ( wface, wn, 140 ), wright, 84, "dark" )
    P.door( m, ( wface, wn, 0 ), wright, 64, 84, paint="rv_door_yellow", double=False, window=False )
    P.quad( m, "rv_hazard", ( wface, wn - 40, 45 ), wright, UP, 8, 90, off=0.5 )
    P.quad( m, "rv_hazard", ( wface, wn + 40, 45 ), wright, UP, 8, 90, off=0.5 )
    P.wall_light( m, f"Spawn wing lamp {sx}", ( wface, wn, 100 ), wout, "warm", 260 )
    P.railing( m, mirror_pts( [ ( SPAWN_LANDING[1], -884 ), ( SPAWN_LANDING[1], -840 ), ( SPAWN_WING[1], -840 ), ( SPAWN_WING[1], -690 ),
                                ( SPAWN_WING[0], -690 ) ], f ), SPAWN_ROOM_Z, clip_to=160, name=f"spawn deck rail {sx}" )
    P.railing( m, mirror_pts( [ ( SPAWN_LANDING[1], -960 ), ( SPAWN_LANDING[0], -960 ) ], f ), SPAWN_ROOM_Z, clip_to=160,
               name=f"spawn landing rail {sx}" )
    dface = f * ( t1 )
    for d_ in ( door_a, door_b ):
        P.door( m, ( dface, ( d_[0] + d_[1] ) / 2, SPAWN_ROOM_Z ), wright, 66 if d_ is door_a else 56, 92, double=d_ is door_a )
    P.plate( m, "door_sign", ( dface, -985, SPAWN_ROOM_Z + 54 ), wright, 22, off=0.4 )
    P.wall_light( m, f"Spawn door lamp {sx}", ( dface, -905, SPAWN_ROOM_Z + 112 ), wout, "warm", 300 )
    P.wall_light( m, f"Spawn upper lamp {sx}", ( dface, -770, SPAWN_ROOM_Z + 112 ), wout, "warm", 280 )
    P.beacon( m, f"Spawn beacon {sx}", ( f * t1 + f * 4, tn1 - 10, SPAWN_TOP + 26 ) )
    # Crates and cases on the deck, as the reference's along its walkway.
    P.case_stack( m, ( f * -1960, -720 ), ( 1, 0 ), "olive", seed=160 + sx )
    # Guard hut and barriers.
    he = f * -2120
    box( m, he - 50, he + 50, -1500, -1400, 0, 110, { "default": "rv_white", "+z": "rv_steel" }, METAL )
    P.quad( m, "rv_window_dark", ( he + f * 50, -1450, 70 ), v( 0, f, 0 ), UP, 70, 40, off=0.3 )
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


# ---------------------------------------------------------------------------------------------------------------------
# The yard's middle: B1 and the turbine building's annex

def b1( m, glass ):
    c0, c1, n0, n1 = CORE
    t = 24.0
    up_door = ( -930.0, -860.0, ROOM_Z + 96, ROOM_Z )
    H.wall( m, "e", c0, c1, n1 - t, n1, 0, CORE_TOP, [ ( -60.0, 60.0, 150.0 ) ] )
    H.wall( m, "e", c0, c1, n0, n0 + t, 0, CORE_TOP, [ ( -60.0, 60.0, 150.0 ) ] )
    for sx in ( -1, 1 ):
        a, b = sorted( ( sx * c1, sx * ( c1 - t ) ) )
        H.wall( m, "n", n0 + t, n1 - t, a, b, 0, CORE_TOP, [ up_door ] )
    # Upper floor, roof, parapet, windows on the north and south faces.
    box( m, c0 + t, c1 - t, n0 + t, n1 - t, ROOM_Z - 16, ROOM_Z, { "default": "rv_wall", "+z": "rv_floor", "-z": "rv_steel" }, STONE )
    box( m, c0, c1, n0, n1, CORE_TOP - 20, CORE_TOP, { "default": "rv_wall", "-z": "rv_steel" }, STONE )
    for a, b, c, d in ( ( c0, c1, n0, n0 + 10 ), ( c0, c1, n1 - 10, n1 ), ( c0, c0 + 10, n0, n1 ), ( c1 - 10, c1, n0, n1 ) ):
        box( m, a, b, c, d, CORE_TOP, CORE_TOP + 28, "rv_wall", STONE )
    # Ground floor lamps in the passage, the upper room's lamps.
    P.ceiling_light( m, "B1 passage", ( 0, -870, ROOM_Z - 20 ), ( 0, 1 ), "cool", 340 )
    P.ceiling_light( m, "B1 room", ( 0, -870, CORE_TOP - 26 ), ( 0, 1 ), "cool", 380 )
    for nf, sgn in ( ( n1, 1 ), ( n0, -1 ) ):
        fz = nf
        out = v( 0, sgn, 0 )
        right = np.cross( UP, out )
        # A strip window on the face: frames and a lit pane (the room behind is drawn only through its doors).
        box( m, -122, 122, min( fz, fz + sgn * 3 ), max( fz, fz + sgn * 3 ), 236, 240, "rv_frame" )
        box( m, -122, 122, min( fz, fz + sgn * 3 ), max( fz, fz + sgn * 3 ), 330, 334, "rv_frame" )
        for e in np.arange( -120, 121, 60.0 ):
            box( m, e - 2, e + 2, min( fz, fz + sgn * 3 ), max( fz, fz + sgn * 3 ), 240, 330, "rv_frame" )
        P.quad( m, "rv_window_lit", ( 0, fz, 285 ), right, UP, 240, 90, off=0.4 )
        P.wall_light( m, f"B1 passage lamp {sgn}", ( 0, fz, 168 ), out, "warm", 320 )
        P.beacon( m, f"B1 roof beacon {sgn}", ( 140 * sgn, fz - sgn * 6, CORE_TOP + 28 ) )
    # Each side: the low wing (its roof part of the upper deck), the landing, the stair, railings, the door.
    for sx in ( -1, 1 ):
        f = -sx

        def E( a, b ):
            return tuple( sorted( ( f * a, f * b ) ) )

        box( m, *E( WING[0], WING[1] ), WING[2], WING[3], 0, ROOM_Z, { "default": "rv_wall", "+z": "rv_floor" }, STONE )
        box( m, *E( B_LANDING[0], B_LANDING[1] ), B_LANDING[2], B_LANDING[3], ROOM_Z - 16, ROOM_Z,
             { "default": "rv_wall", "+z": "rv_floor" }, STONE )
        box( m, *E( B_LANDING[0], B_LANDING[0] + 12 ), B_LANDING[2], B_LANDING[2] + 12, 0, ROOM_Z - 16, "rv_wall", STONE )
        mid = ( B_STAIR[2] + B_STAIR[3] ) / 2
        P.stairs( m, ( f * B_STAIR[0], mid ), ( f * B_STAIR[1], mid ), B_STAIR[3] - B_STAIR[2], 0, ROOM_Z, tread="rv_plinth",
                  side="rv_plinth", solid_under=True, surface=STONE, name=f"B1 stair {sx}" )
        wface = f * WING[0]
        out = v( -f, 0, 0 )
        right = np.cross( UP, out )
        P.letters( m, "C1", ( wface, ( WING[2] + WING[3] ) / 2, 138 ), right, 86, "dark" )
        P.door( m, ( wface, ( WING[2] + WING[3] ) / 2, 0 ), right, 66, 84, paint="rv_door_yellow", double=False, window=False )
        P.quad( m, "rv_hazard", ( wface, ( WING[2] + WING[3] ) / 2 - 42, 45 ), right, UP, 8, 90, off=0.5 )
        P.quad( m, "rv_hazard", ( wface, ( WING[2] + WING[3] ) / 2 + 42, 45 ), right, UP, 8, 90, off=0.5 )
        P.wall_light( m, f"B1 wing lamp {sx}", ( wface, ( WING[2] + WING[3] ) / 2, 104 ), out, "warm", 260 )
        P.railing( m, mirror_pts( [ ( -200, -864 ), ( -200, -840 ), ( -420, -840 ), ( -420, -700 ), ( -160, -700 ) ], f ), ROOM_Z, clip_to=160,
                   name=f"B1 deck rail {sx}" )
        P.railing( m, mirror_pts( [ ( -200, -940 ), ( -160, -940 ) ], f ), ROOM_Z, clip_to=160, name=f"B1 landing rail {sx}" )
        # The upper door into the core and its placard, as the reference's.
        dface = f * c0
        P.door( m, ( dface, ( up_door[0] + up_door[1] ) / 2, ROOM_Z ), right, 66, 92 )
        P.plate( m, "door_sign", ( dface, -820, ROOM_Z + 54 ), right, 22, off=0.4 )
        P.wall_light( m, f"B1 door lamp {sx}", ( dface, ( up_door[0] + up_door[1] ) / 2, ROOM_Z + 112 ), out, "warm", 300 )
    # Inside the room: lockers, a table, cases.
    box( m, -120, -40, -1000, -980, ROOM_Z, ROOM_Z + 80, "rv_steel", METAL )
    box( m, 40, 120, -1000, -980, ROOM_Z, ROOM_Z + 80, "rv_steel", METAL )
    box( m, -36, 36, -960, -920, ROOM_Z, ROOM_Z + 30, { "default": "rv_desk", "+z": "rv_dark" }, METAL )
    P.case_stack( m, ( -100, -760 ), ( 1, 0 ), "dark", seed=201 )
    P.case_stack( m, ( 100, -760 ), ( 1, 0 ), "olive", seed=202 )


def turbine_annex( m ):
    e0, e1, n0, n1 = TURBINE
    box( m, e0, e1, n0, n1, 0, TURBINE_TOP, "rv_wall", STONE )
    for a, b, c, d in ( ( e0, e1, n1 - 10, n1 ), ( e0, e0 + 10, n0, n1 ), ( e1 - 10, e1, n0, n1 ) ):
        box( m, a, b, c, d, TURBINE_TOP, TURBINE_TOP + 30, "rv_wall", STONE )
    for sx in ( -1, 1 ):
        face = sx * e1
        out = v( sx, 0, 0 )
        right = np.cross( UP, out )
        P.letters( m, "turbine_hall", ( face, -1360, 250 ), right, 26, "dark" )
        # A loading bay: a recess with a lit back and a closed roller door.
        bay0, bay1, depth = -1640.0, -1480.0, 60.0
        a, b = sorted( ( face, face - sx * depth ) )
        P.wall_light( m, f"Turbine bay lamp {sx}", ( face, ( bay0 + bay1 ) / 2, 200 ), out, "warm", 380 )
        P.quad( m, "rv_hazard", ( face, bay0 - 7, 90 ), right, UP, 12, 180, off=0.4 )
        P.quad( m, "rv_hazard", ( face, bay1 + 7, 90 ), right, UP, 12, 180, off=0.4 )
        for k in range( 18 ):
            P.quad( m, "rv_louvre", ( face, ( bay0 + bay1 ) / 2, 5 + k * 10 ), right, UP, bay1 - bay0 - 4, 9, off=0.6 )
        P.wall_light( m, f"Turbine corner lamp {sx}", ( face, -1280, 250 ), out, "warm", 300 )
        P.beacon( m, f"Turbine beacon {sx}", ( face + sx * 6, -1250, TURBINE_TOP + 30 ) )
    # The north face: louvres, a door, pipes, lamps.
    out = v( 0, 1, 0 )
    right = np.cross( UP, out )
    for e in ( -330.0, 330.0 ):
        P.louvre( m, ( e, n1, 250 ), right, 180, 120 )
    P.door( m, ( 0, n1, 0 ), right, 90, 100 )
    P.wall_light( m, "Turbine door lamp", ( 0, n1, 128 ), out, "warm", 340 )
    for k, r in enumerate( ( 10.0, 7.0 ) ):
        P.pipe( m, [ ( e0 + 10, n1 + 18 + k * 6, 300 - k * 24 ), ( e1 - 10, n1 + 18 + k * 6, 300 - k * 24 ) ], r, "rv_pipe", 12 )
    for e in np.arange( e0 + 40, e1, 160.0 ):
        box( m, e - 3, e + 3, n1, n1 + 30, 262, 266, "rv_steel" )


def middle_yard( m ):
    """ The hall's apron and the pipe bridge from the hall to B1. """
    # Pipe bridge: a truss from the hall's south wall to B1's north wall, pipes on it.
    for e in ( -110.0, -30.0 ):
        P.truss( m, ( e, H.N0 - H.WT - 14, 300 ), ( e, CORE[3], 300 ), 40, "rv_steel", panel=60 )
    for k, ( de, r ) in enumerate( ( ( -95, 9.0 ), ( -70, 6.0 ), ( -50, 6.0 ) ) ):
        P.pipe( m, [ ( de, H.N0 - H.WT - 14, 352 ), ( de, CORE[3] - 4, 352 ) ], r, "rv_pipe", 12, caps=False )
    for n in np.arange( H.N0 - H.WT - 60, CORE[3], 80.0 ):
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
        P.pipe( m, [ ( -1030, face - 16 - k * 14, 420 + k * 20 ), ( 1030, face - 16 - k * 14, 420 + k * 20 ) ], r, "rv_pipe", 12 )
    for e in np.arange( -1000, 1001, 200.0 ):
        box( m, e - 3, e + 3, face - 40, face, 408, 412, "rv_steel" )
    P.louvre( m, ( -620, face, 700 ), right, 260, 160 )
    P.louvre( m, ( 620, face, 700 ), right, 260, 160 )
    # The east-west lanes' floor lines in the middle.
    box( m, -520, 520, -1206, -1202, 0, 0.3, { "default": None, "+z": "rv_line_yellow" } )


def north_lane( m ):
    """ The lane north of the hall: the perimeter wall with a fence on it, the pipe rack along the hall's wall, cover. """
    n = NORTH_WALL_N
    box( m, PLAY[0] - 400, PLAY[1] + 400, n, n + 30, 0, 220, "rv_wall", STONE )
    box( m, PLAY[0] - 400, PLAY[1] + 400, n - 3, n, 0, 30, "rv_plinth" )
    for e in np.arange( PLAY[0], PLAY[1] + 1, 120.0 ):
        P.rod( m, ( e, n + 15, 220 ), ( e, n + 15, 300 ), 1.2, "rv_zinc", 6 )
        P.rod( m, ( e, n + 15, 296 ), ( e, n + 5, 304 ), 0.8, "rv_zinc", 4 )
    for z in ( 250.0, 275.0, 300.0 ):
        P.rod( m, ( PLAY[0], n + 15, z ), ( PLAY[1], n + 15, z ), 0.4, "rv_zinc", 4 )
    # Pipe rack along the hall's north wall.
    r0, r1 = H.N1 + H.WT + 10, H.N1 + H.WT + 150
    for e in np.arange( -1000, 1001, 250.0 ):
        for nn in ( r0, r1 ):
            box( m, e - 5, e + 5, nn - 5, nn + 5, 0, 260, "rv_steel", METAL )
        P.i_beam( m, ( e, r0 - 6, 260 ), ( e, r1 + 6, 260 ), 12, 8, "rv_steel" )
    for nn in ( r0, r1 ):
        P.i_beam( m, ( -1010, nn, 254 ), ( 1010, nn, 254 ), 12, 8, "rv_steel" )
    for k, r in enumerate( ( 12.0, 9.0, 9.0, 6.0, 6.0 ) ):
        nn = r0 + 18 + k * 26
        P.pipe( m, [ ( -1700, nn, 266 + r ), ( 1700, nn, 266 + r ) ], r, "rv_pipe", 12, caps=False )
    P.cable_tray( m, ( -1700, r1 + 30, 300 ), ( 1700, r1 + 30, 300 ) )
    # Cover: concrete blocks, a generator, cases, barriers.
    for e, nn in ( ( -720, 1880 ), ( 720, 1880 ), ( -240, 1760 ), ( 240, 1760 ), ( 0, 1960 ) ):
        box( m, e - 30, e + 30, nn - 30, nn + 30, 0, 44, "rv_plinth", STONE )
    box( m, -140, 140, 1890, 1960, 0, 84, { "default": "rv_steel", "+z": "rv_steel" }, METAL )
    P.letters( m, "logo_wordmark", ( 0, 1889.6, 50 ), ( 1, 0, 0 ), 20, "light" )
    P.pipe( m, [ ( 110, 1940, 84 ), ( 110, 1940, 150 ) ], 4, "rv_steel", 8 )
    for k, ( e, nn ) in enumerate( ( ( -1260, 1880 ), ( 1260, 1880 ), ( -500, 1990 ), ( 500, 1990 ), ( -1900, 1950 ), ( 1900, 1950 ) ) ):
        P.case_stack( m, ( e, nn ), ( 1, 0 ), "olive" if k % 2 else "dark", seed=400 + k )
    for e, nn, along in ( ( -1000, 1780, ( 1, 0 ) ), ( 1000, 1780, ( 1, 0 ) ), ( -1700, 1820, ( 0, 1 ) ), ( 1700, 1820, ( 0, 1 ) ) ):
        P.jersey( m, ( e, nn ), along )
    for e in ( -1500.0, -500.0, 500.0, 1500.0 ):
        P.wall_light( m, f"Perimeter lamp {e}", ( e, n, 200 ), v( 0, -1, 0 ), "warm", 420 )
    out = v( 0, 1, 0 )
    right = np.cross( UP, out )
    for o in H.NORTH_DOORS:
        e = ( o[0] + o[1] ) / 2
        P.wall_light( m, f"Hall north door lamp {e}", ( e, H.N1 + H.WT, 150 ), out, "warm", 340 )
        P.plate( m, "exit", ( e, H.N1 + H.WT, 140 ), right, 10, off=0.4 )


def turbine_hall( m ):
    """ The turbine hall: the south boundary, its north face dressed. Solid. """
    e0, e1 = PLAY[0] - 400, PLAY[1] + 400
    n0, n1 = PLAY[2] - 1000, PLAY[2]
    box( m, e0, e1, n0, n1, 0, 960, "rv_wall", STONE )
    out = v( 0, 1, 0 )
    right = np.cross( UP, out )
    for e in np.arange( PLAY[0], PLAY[1] + 1, 300.0 ):
        if abs( e ) < 560:
            continue
        box( m, e - 24, e + 24, n1, n1 + 16, 0, 980, "rv_wall", STONE )
    for e in np.arange( PLAY[0] + 150, PLAY[1], 300.0 ):
        if abs( e ) < 600:
            continue
        P.louvre( m, ( e, n1, 760 ), right, 200, 140 )
        P.quad( m, "rv_window_dark", ( e, n1, 480 ), right, UP, 200, 160, off=0.3 )
    P.letters( m, "turbine_hall", ( -1350, n1, 880 ), right, 70, "dark" )
    P.letters( m, "turbine_hall", ( 1350, n1, 880 ), right, 70, "dark" )
    for e in ( -1900.0, 1900.0, -1100.0, 1100.0 ):
        P.door( m, ( e, n1, 0 ), right, 150, 180, double=True )
        P.wall_light( m, f"Turbine hall door lamp {e}", ( e, n1, 200 ), out, "warm", 380 )
    for k, r in enumerate( ( 14.0, 10.0 ) ):
        P.pipe( m, [ ( PLAY[0], n1 + 24 + k * 8, 600 + k * 30 ), ( PLAY[1], n1 + 24 + k * 8, 600 + k * 30 ) ], r, "rv_pipe", 12, caps=False )


# ---------------------------------------------------------------------------------------------------------------------
# Lights and probes

def probes():
    return [
        ( "Hall", ( 0, 700, 400 ), ( H.E0, H.E1, H.N0, H.N1, -40, H.TOP ) ),
        ( "Pool", ( 0, 700, -200 ), ( -500, 500, 200, 1200, H.POOL_FLOOR, 0 ) ),
        ( "A1", ( -1370, -190, 150 ), ( -1670, -1070, -590, 210, 0, ANNEX_TOP - 20 ) ),
        ( "A2", ( 1370, -190, 150 ), ( 1070, 1670, -590, 210, 0, ANNEX_TOP - 20 ) ),
        ( "B1 Room", ( 0, -870, 280 ), ( -136, 136, -1016, -724, ROOM_Z, CORE_TOP - 20 ) ),
        ( "West Control", ( -890, 0, 360 ), ( -1000, -780, -200, 200, H.UPPER, 440 ) ),
        ( "East Control", ( 890, 0, 360 ), ( 780, 1000, -200, 200, H.UPPER, 440 ) ),
        ( "Yard", ( 0, -1000, 200 ), ( PLAY[0], PLAY[1], PLAY[2], H.N0 - H.WT, -20, 900 ) ),
        ( "North", ( 0, 1850, 200 ), ( PLAY[0], PLAY[1], H.N1 + H.WT, PLAY[3], -20, 700 ) ),
    ]


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( -2050, -500, 0 ), ( -2050, -250, 0 ), ( -2050, 0, 0 ), ( -2050, 250, 0 ), ( -2050, 480, 0 ), ( -1850, -450, 0 ),
               ( -1850, -200, 0 ), ( -1850, 50, 0 ), ( -1850, 300, 0 ), ( -2200, -400, 0 ), ( -2200, -100, 0 ), ( -2200, 200, 0 ) ]
BLUE_SPAWNS = [ ( -e, n, z ) for e, n, z in RED_SPAWNS ]
BUY_ZONE = ( 1720, 2300, -900, 500, -10, 260 )        # Blue Team's; Red Team's is its mirror

DM_SPAWNS = [ ( 0, 0, 0 ), ( 0, 1400, 0 ), ( -560, 1200, 0 ), ( 560, 1200, 0 ), ( -800, 200, 0 ), ( 590, 760, 0 ),
              ( -930, 900, H.UPPER ), ( 930, 500, H.UPPER ), ( 0, 1530, H.UPPER ), ( -890, -100, H.UPPER ), ( 890, 100, H.UPPER ),
              ( -1370, -100, 0 ), ( 1370, -100, 0 ), ( -1370, 1300, 0 ), ( 1370, 800, 0 ), ( -600, 1850, 0 ), ( 600, 1850, 0 ),
              ( -1800, 1850, 0 ), ( 1800, 1850, 0 ), ( 0, -870, ROOM_Z ), ( -300, -770, ROOM_Z ), ( 300, -770, ROOM_Z ),
              ( 0, -500, 0 ), ( -860, -1060, 0 ), ( 860, -1060, 0 ), ( -1380, -1100, 0 ), ( 1380, -1100, 0 ), ( 0, -1150, 0 ),
              ( -1100, -1600, 0 ), ( 1100, -1600, 0 ), ( -1950, -1550, 0 ), ( 1950, -1550, 0 ), ( -2130, -950, SPAWN_ROOM_Z ),
              ( 2130, -950, SPAWN_ROOM_Z ) ]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 460, 1000, 300, 1100, 0 ),
               ( "bombsite_b", "Bomb Site B", 760, 1300, -1620, -960, 0 ) ]

_HALL_ATTACK = [ ( -1400, 800, 0 ), ( -1500, 1000, 0 ), ( -1300, 1100, 0 ), ( -1400, -400, 0 ), ( -1550, -300, 0 ), ( -1250, -100, 0 ) ]
_YARD_ATTACK = [ ( -1100, -1560, 0 ), ( -1000, -1640, 0 ), ( -1500, -1440, 0 ), ( -1300, -720, 0 ), ( -1700, -900, 0 ), ( -1560, -1300, 0 ) ]
RETAKES = {
    "bombsite_a": { "planter": [ ( 840, 470, 0 ), ( 560, 1060, 0 ) ],
                    "defender": [ ( 900, 1250, 0 ), ( 470, 1320, 0 ), ( 850, 150, 0 ) ],
                    "attacker": list( _HALL_ATTACK ) },
    "bombsite_b": { "planter": [ ( 1000, -1290, 0 ), ( 1150, -1500, 0 ) ],
                    "defender": [ ( 1250, -1080, 0 ), ( 860, -1640, 0 ), ( 1160, -1680, 0 ) ],
                    "attacker": list( _YARD_ATTACK ) },
}

DOMINATION = [ ( "A", ( -1370, -120, 0 ) ), ( "B", ( 0, -500, 0 ) ), ( "C", ( 1370, -120, 0 ) ) ]
HOT_ZONES = [ ( "Pool South", ( 0, 0, 0 ) ), ( "Pool North", ( 0, 1400, 0 ) ), ( "C1", ( 0, -870, ROOM_Z ) ),
              ( "North Lane", ( 0, 1850, 0 ) ), ( "West Court", ( -1370, 900, 0 ) ), ( "East Court", ( 1370, 900, 0 ) ) ]
CASH_POINTS = [ ( "Pool South", ( 0, 0, 0 ), ( 0, -870, ROOM_Z ) ), ( "West Court", ( -1370, 900, 0 ), ( 1370, 900, 0 ) ),
                ( "East Court", ( 1370, 900, 0 ), ( -1370, 900, 0 ) ) ]


def callouts():
    out = [ ( "RED SPAWN", PLAY[0], -1700, PLAY[2], PLAY[3], -10, 600 ), ( "BLUE SPAWN", 1700, PLAY[1], PLAY[2], PLAY[3], -10, 600 ),
            ( "A1", -1700, -1040, -620, 240, -10, 380 ), ( "A2", 1040, 1700, -620, 240, -10, 380 ),
            ( "WEST COURT", -1700, -1040, 240, 1640, -10, 600 ), ( "EAST COURT", 1040, 1700, 240, 1640, -10, 600 ),
            ( "NORTH LANE", -1700, 1700, 1640, PLAY[3], -10, 600 ),
            ( "WEST CONTROL", -1000, -700, -200, 200, 270, 460 ), ( "EAST CONTROL", 700, 1000, -200, 200, 270, 460 ),
            ( "WEST WALKWAY", -1000, -640, 200, 1460, 270, 460 ), ( "EAST WALKWAY", 640, 1000, 200, 1460, 270, 460 ),
            ( "NORTH WALKWAY", -1000, 1000, 1460, 1600, 270, 460 ),
            ( "POOL SOUTH", -1000, 1000, -200, 450, -40, 270 ), ( "POOL WEST", -1000, -300, 450, 1600, -40, 270 ),
            ( "A SITE", 300, 1000, 300, 1600, -40, 270 ), ( "POOL NORTH", -300, 300, 1100, 1600, -40, 270 ),
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

MINIMAP_CENTRE = ( 0.0, 150.0 )
MINIMAP_SIZE = 4900.0
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


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
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
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.7, Radius=110,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=6200,
                     BlendFactor=0.4, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.26, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=1.0, MaximumExposure=4,
                     Mode="ACES", Rate=1 ),
    ] )


def write_scene( written, light_list, probe_list ):
    world = K.game_object( ids, "Riverdale", "world", children=[
        model_object( title, f"world/{name}", name, collide, shadows )
        for name, title, collide, shadows in SCENE_MODELS if name in written ] )
    light_objects = [
        K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
                         LightColor=color, Radius=radius, Shadows=shadows ) ] )
        for name, position, color, radius, shadows in light_list ]

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
        clip_objects.append( K.game_object( ids, f"Player Clip {name} {k}", key, K.to_world( centre ), K.yaw_rotation( yaw - 90.0 ),
                                            tags="playerclip", components=[ box_collider( f"{key}/box", ( size[1], size[0], size[2] ), trigger=False ) ] ) )
    for name, b in ROOF_CLIPS:
        centre, scale = plan_box( *b )
        clip_objects.append( K.game_object( ids, f"Player Clip {name}", f"clip/{name}", centre, tags="playerclip", components=[
            box_collider( f"clip/{name}/box", scale, trigger=False ) ] ) )
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
        # A sunrise: the sun 12 degrees up in the east-north-east, golden.
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor=SUN_COLOUR, ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.40,0.44,0.54,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="1,1,1,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.7", StartDistance=3000,
                         EndDistance=90000, FalloffExponent=1.3, Height=12000, VerticalFalloffExponent=1.2 ),
        ] ),
        look_object(),
        world,
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in probe_list ] ),
        mode_group( "Team Spawns", "spawns", ( "Deathmatch", "Gun Game" ), team_spawns, inverse=True ),
        mode_group( "Deathmatch Spawns", "spawns/dm", ( "Deathmatch", "Gun Game" ), dm_spawns ),
        mode_group( "Retakes Spawns", "spawns/retakes", ( "Retakes", ), retakes_spawns ),
        K.game_object( ids, "Bomb Sites", "sites", children=bomb_sites ),
        K.game_object( ids, "Buy Zones", "buy", children=buy_zones ),
        K.game_object( ids, "Callouts", "callouts", children=callout_objects ),
        play_area,
        K.game_object( ids, "Player Clips", "clips", children=clip_objects ),
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
                out.append( ( f"