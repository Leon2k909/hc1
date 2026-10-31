"""
Orion: a rocket launch facility in the hills at golden hour after rain. A multiplayer map built by script like
Riverdale and Riverside (map_kit's boxes and polygons), dressed after the user's reference picture (2026-10-15): the wet
cargo yard seen from a roof overlook, Launch Control 01's tower on the left, B3 Fuel Processing on the right with its
silver fuel lines, the ORION AEROSPACE block and the service tunnel under the launch deck at the back, the rocket on its
pad between two service towers beyond, the OPS Satellite Control box and its flag, the radome on its hill, the town and
the mountains.

    python Tools/orion_map.py [--stage] [--preview <dir>] [--views ...] [--no-scene] [--no-models]

Run Tools/orion_textures.py and Tools/orion_sky.py first. Orion Aerospace, its mark, ORN and every marking are the
map's own. Writes (under output/orion/v2/ with --stage, so a running editor isn't made to recompile anything):
- the models, to Assets/models/maps/orion/: the ground, Launch Control (its tower, balcony, terrace, west walkway and
  the west block), the overlook (the south block whose roof the reference is seen from), the launch deck (the ORION
  block, the mezzanine and undercroft, the service tunnel and its red room), Fuel Processing (B3, the east block, OPS
  and the fuel lines), the yard's props, the spawn courts, the glass, the pad (the rocket, its mount and service towers,
  the lattice masts and floodlights, the pad's machinery; drawn only) and the vista (Tools/orion_backdrop.py: the
  hills, the town, the radome, the mountains; drawn only);
- the scene, Assets/scenes/maps/Orion/orion.scene, rewritten whole on every run (change the layout here, not in the
  editor);
- the radar picture, ui/minimaps/minimap_orion.png.

Plan coordinates: e east, n north, z up, inches. The reference camera (REF_EYE, REF_FOV) stands on the overlook's roof
at the yard's south end, 400 up, looking due north, 75 degrees across: the picture's verticals are parallel, so it's a
level view with its horizon 346 down a 1536 x 1024 frame (a shifted lens; REF_PITCH is the pitched camera that frames
about the same, for previews). What the picture shows was placed from its bearing and height in that view
(Sources/Orion/README.md, Sources/Orion/v2/compare.py). The levels: the yard at 0, the terrace at 64,
the west walkway and the deck-front mezzanine at 144, the deck, the east block's roof and the ORION block's top at 240,
B3's roof at 280, the overlook's roof and Launch Control's balcony at 336. Red Team spawns in the west court behind
Launch Control, Blue Team in the east court behind Fuel Processing. Bomb site A is the launch deck, B the cargo yard.

Every run checks every spawn, objective and cash spot with railhead_map's check_spots, check_reach and
check_retakes_sight, and prints what's wrong.
"""
import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K
import orion_parts as OP
import orion_cable_reel as OCR
import orion_generator as OG
import orion_textures as OT
import railhead_map as R
import railhead_preview as PV
import railhead_props as RP
import riverdale_parts as P
from riverdale_parts import v, unit, card, box, obox, UP, METAL, STONE, PLASTIC

TITLE = "Orion"
ASSETS = K.ASSETS
STAGE = K.ROOT / "output/orion/v2"
RESOURCE_DIR = "models/maps/orion"
MINIMAP_PATH = "ui/minimaps/minimap_orion.png"
MAP_ART_PATH = "ui/maps/orion.png"

ids = K.SceneIds( "8b3f0e52-4c1a-4f7e-9d6a-2b5e71c0a913" )
RP.CONTAINER_SIZES.setdefault( "10", 118.0 )        # a ten-foot container (ISO 1D), for the yard

# The reference picture's camera.
REF_EYE = ( 0.0, -560.0, 400.0 )
REF_PITCH = -9.4
REF_FOV = 75.0
REF_SIZE = ( 1536, 1024 )

SUN_PITCH, SUN_YAW = 8.3, -155.0         # 8.3 degrees up, towards 25 degrees west of north: half behind Launch Control
SUN_COLOUR = "2.1,1.42,0.80,1"
SKY_MATERIAL = "materials/orion/sky/oa_sky.vmat"
FOG_COLOUR = "0.47,0.45,0.47"
CATCH_FLOOR_Z = -3000

PLAY = ( -1350.0, 1450.0, -1150.0, 1420.0 )
NAV_TOP = 460.0

G = 240.0           # the deck, the east block's roof, the ORION block's top
B3_TOP = 280.0
OVER_Z = 336.0      # the overlook's roof and Launch Control's balcony
WALK_Z = 144.0      # the west walkway and the mezzanine along the deck's front
FASCIA_Z = 88.0     # the mezzanine's fascia comes down to here (the arcade's head)
PARAPET_Z = 180.0   # the mezzanine's solid parapet (the picture's deck wall) stands to here
TERRACE_Z = 64.0
LC_TOP = 640.0

# Footprints ( e0, e1, n0, n1 ).
SOUTH = ( -560.0, 900.0, -1000.0, -540.0 )          # the overlook's block
LC = ( -900.0, -316.0, -10.0, 200.0 )               # Launch Control's tower below the balcony
LC_UPPER_E1 = -252.0                                # its upper storeys reach further east
LC_BALCONY = ( -980.0, -222.0, -140.0, -10.0 )
LC_HALL = ( -860.0, -356.0, 30.0, 170.0 )           # the tower's ground-floor hall (at the terrace's level)
LC_ROOM = ( -600.0, -334.0, 14.0, 176.0 )           # the control room behind the open bay (at OVER_Z)
LC_BAY = ( -600.0, -374.0 )                         # the open bay in the south face, e0..e1 (its dark frame runs to -346)
WEST = ( -900.0, -360.0, 200.0, 700.0 )             # the west block (one storey) behind the west walkway
WEST_TOP = 176.0
TERRACE = [ ( -316.0, -250.0 ), ( -120.0, -250.0 ), ( -230.0, 330.0 ), ( -316.0, 330.0 ) ]
WALKWAY = ( -342.0, -258.0, 330.0, 700.0 )          # the west walkway (at WALK_Z)
MEZZ = ( -560.0, -75.0, 700.0, 900.0 )              # the mezzanine along the deck's front (at WALK_Z), the undercroft under it
ORION = ( -75.0, 160.0, 700.0, 900.0 )
DECK = ( -560.0, 600.0, 900.0, 1400.0 )
TUNNEL = ( 180.0, 520.0, 900.0, 1250.0 )
TUNNEL_TOP = 180.0
RED_ROOM = ( 180.0, 520.0, 1250.0, 1400.0 )
DECK_STAIR = ( 440.0, 512.0, 990.0, 1330.0 )        # in the tunnel's east side, up through the deck
B3 = ( 243.0, 1150.0, 57.0, 157.0 )
EAST = ( 560.0, 1150.0, 157.0, 1400.0 )
FUEL_HALL = ( 600.0, 1110.0, 300.0, 1000.0 )
OPS = ( 700.0, 980.0, 720.0, 840.0 )
OPS_TOP = 480.0


# ---------------------------------------------------------------------------------------------------------------------
# Paints

def configure( model ):
    """ oa_ paints are Orion's (Tools/orion_textures.py); rw_ (glass, containers) Railhead's; lt_ (the forklift and
    containers) set by their own modules. """
    known = {}
    if R.RM is not None and hasattr( R.RM, "paints" ):
        try:
            known = R.RM.paints()
        except Exception as error:
            print( f"railhead_materials.paints() failed: {error}" )
    OP.repaint( model )
    painted = set( OT.PAINTED )
    surfaces = set( OT.all_paints() )
    for paint in list( model.polygons ):
        if paint.startswith( "oa_" ):
            model.material_overrides[paint] = f"{OT.RESOURCE_DIR}/{paint}.vmat"
            model.tile_overrides[paint] = OT.TILES.get( paint, 64.0 )
            if paint not in surfaces and paint not in painted:
                R.UNKNOWN_PAINTS.add( paint )
        elif paint.startswith( "rw_" ):
            try:
                path = R.RM.material_path( paint )
            except Exception:
                path = f"materials/railhead/{paint}.vmat"
            model.material_overrides[paint] = path
            model.tile_overrides[paint] = float( ( known[paint][1] if paint in known else None ) or 64.0 )
        elif paint.startswith( "lt_" ) or paint.startswith( "bx_" ):
            pass
        elif paint not in model.material_overrides:
            R.UNKNOWN_PAINTS.add( paint )
            model.material_overrides[paint] = f"{OT.RESOURCE_DIR}/oa_wall.vmat"
            model.tile_overrides[paint] = 236.0
    model.anchored_paints = set()
    model.decal_paints = set()
    return model


def wall( m, axis, a0, a1, t0, t1, z0, z1, openings=(), paint="oa_wall", surface=STONE ):
    """ A wall along axis ('e' or 'n') from a0 to a1, t0..t1 thick, with openings ( b0, b1, top[, bottom] ). """
    cuts = sorted( { a0, a1 } | { b for o in openings for b in o[:2] if a0 < b < a1 } )
    for b0, b1 in zip( cuts, cuts[1:] ):
        mid = ( b0 + b1 ) / 2
        hole = next( ( o for o in openings if o[0] <= mid <= o[1] ), None )
        spans = [ ( z0, z1 ) ] if hole is None else [ ( hole[2], z1 ) ] + ( [ ( z0, hole[3] ) ] if len( hole ) > 3 else [] )
        for za, zb in spans:
            if zb - za < 0.5:
                continue
            if axis == "e":
                box( m, b0, b1, t0, t1, za, zb, paint, surface )
            else:
                box( m, t0, t1, b0, b1, za, zb, paint, surface )


def slab( m, e0, e1, n0, n1, z0, z1, top="oa_deck", side="oa_wall_dark", under="oa_wall_dark", surface=STONE ):
    box( m, e0, e1, n0, n1, z0, z1, { "default": side, "+z": top, "-z": under }, surface )


def floor_line( m, a, b, width=4.0, z=0.12, paint="oa_line_yellow" ):
    """ A painted line on the floor from a to b (plan). """
    a, b = v( a[0], a[1], z ), v( b[0], b[1], z )
    d = unit( b - a )
    s = np.cross( UP, d ) * ( width / 2 )
    card( m, paint, [ a - s, b - s, b + s, a + s ], UP )


def arrow_mark( m, at, heading, size=40.0, z=0.13, paint="oa_line_white" ):
    """ A painted chevron arrow on the floor pointing along heading (plan vector). """
    d = unit( ( heading[0], heading[1], 0 ) )
    s = np.cross( UP, d )
    c = v( at[0], at[1], z )
    w = size * 0.18
    for sg in ( -1, 1 ):
        p0 = c - d * size * 0.3 + s * sg * size * 0.4
        p1 = c + d * size * 0.3
        e = unit( p1 - p0 )
        o = np.cross( UP, e ) * ( w / 2 )
        card( m, paint, [ p0 - o, p1 - o, p1 + o, p0 + o ], UP )


def railing_e( m, e0, e1, n, z, **kw ):
    P.railing( m, [ ( e0, n ), ( e1, n ) ], z, "oa_yellow", height=kw.pop( "height", 42 ), post_every=kw.pop( "post_every", 60 ),
               clip_to=kw.pop( "clip_to", 52 ), name=kw.pop( "name", "rail" ), **kw )


def railing_n( m, n0, n1, e, z, **kw ):
    P.railing( m, [ ( e, n0 ), ( e, n1 ) ], z, "oa_yellow", height=kw.pop( "height", 42 ), post_every=kw.pop( "post_every", 60 ),
               clip_to=kw.pop( "clip_to", 52 ), name=kw.pop( "name", "rail" ), **kw )


def column( m, e, n, z0, z1, w=20.0, paint="oa_wall_dark" ):
    box( m, e - w / 2, e + w / 2, n - w / 2, n + w / 2, z0, z1, paint, STONE )


# ---------------------------------------------------------------------------------------------------------------------
# The ground

def ground():
    m = K.Model()
    e0, e1, n0, n1 = PLAY
    box( m, e0 - 400, e1 + 400, n0 - 400, n1 + 200, -24, 0, { "default": None, "+z": "oa_yard" }, STONE )
    # Perimeter walls round the spawn courts and the south lane: tall concrete with a coping, players clipped over them.
    for a, b, c, d in ( ( e0 - 30, e0, n0, n1 ), ( e1, e1 + 30, n0, n1 ), ( e0, e1, n0 - 30, n0 ) ):
        box( m, a, b, c, d, 0, 300, "oa_wall_dark", STONE )
        box( m, a - 4, b + 4, c - ( 4 if c == n0 - 30 else 0 ), d, 300, 312, "oa_wall_dark" )
    # The west court's north wall, between the west block and the perimeter.
    box( m, e0, WEST[0], WEST[3] - 30, WEST[3], 0, 300, "oa_wall_dark", STONE )
    # The yard's drains: grates along the slabs' low lines.
    for e, n in ( ( -40, 120 ), ( 120, 460 ), ( 330, 300 ), ( -160, 560 ), ( 60, 820 ), ( 380, 760 ), ( -60, -300 ), ( 400, -200 ) ):
        box( m, e - 18, e + 18, n - 6, n + 6, 0.05, 0.25, "oa_grating" )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# The overlook: the south block, its roof the reference's viewpoint

def overlook( m ):
    e0, e1, n0, n1 = SOUTH
    # The block: two storeys of concrete, its roof the overlook.
    wall( m, "e", e0, e1, n1 - 30, n1, 0, OVER_Z - 16, [ ( -300, -180, 120 ), ( 60, 180, 120 ), ( 420, 540, 120 ) ] )
    wall( m, "e", e0, e1, n0, n0 + 30, 0, OVER_Z - 16, [ ( -200, -80, 110 ), ( 600, 720, 110 ) ] )
    wall( m, "n", n0, n1, e0, e0 + 30, 0, OVER_Z - 16 )
    wall( m, "n", n0, n1, e1 - 30, e1, 0, OVER_Z - 16, [ ( -900, -780, 110 ) ] )
    slab( m, e0, e1, n0, n1, OVER_Z - 16, OVER_Z, top="oa_deck", side="oa_wall" )
    slab( m, e0 + 30, e1 - 30, n0 + 30, n1 - 30, 0, 0.2, top="oa_deck", side=None, under=None, surface=None )
    # Inside: a hall with columns, lamps, cases (the ground floor's doors open onto the yard and the south lane).
    for e in np.arange( e0 + 200, e1 - 100, 260 ):
        column( m, e, ( n0 + n1 ) / 2, 0, OVER_Z - 16, 24 )
        OP.tube_light( m, f"Overlook hall lamp {int( e )}", ( e, ( n0 + n1 ) / 2 - 13, 200 ), ( 0, -1 ), 48, "cool", 380 )
    for k, ( e, n ) in enumerate( ( ( -460, -900 ), ( 300, -640 ), ( 760, -900 ) ) ):
        OP.case_block( m, ( e, n ), ( 1, 0 ), 2, 1, ( 48, 30, 28 ), 2, "rv_case", seed=200 + k )
    # The roof: a parapet round it, low at the north edge so the yard shows over it.
    box( m, -440, e1, n1 - 12, n1, OVER_Z, OVER_Z + 40, "oa_wall_dark", STONE )
    box( m, e0, e1, n0, n0 + 12, OVER_Z, OVER_Z + 40, "oa_wall_dark", STONE )
    box( m, e1 - 12, e1, n0, n1, OVER_Z, OVER_Z + 40, "oa_wall_dark", STONE )
    # A railing over the parapet's north edge (the black rail in the picture's bottom-left corner).
    P.railing( m, [ ( -436, n1 - 6 ), ( -150, n1 - 6 ) ], OVER_Z + 40, "oa_dark", height=20, post_every=48, kick=False, clip_to=30,
               name="overlook rail" )
    box( m, e0, e0 + 12, -980, n1, OVER_Z, OVER_Z + 40, "oa_wall_dark", STONE )
    # The roof's clutter: a plant room, vents, a cable tray.
    box( m, 420, 640, -900, -760, OVER_Z, OVER_Z + 110, { "default": "oa_wall", "+z": "oa_wall_dark" }, STONE )
    P.louvre( m, ( 530, -900, OVER_Z + 55 ), ( 1, 0, 0 ), 120, 70 )
    for k, ( e, n ) in enumerate( ( ( -320, -900 ), ( -120, -940 ), ( 160, -920 ) ) ):
        box( m, e - 30, e + 30, n - 30, n + 30, OVER_Z, OVER_Z + 44, { "default": "oa_steel", "+z": "oa_grating" }, METAL )
    P.cable_tray( m, ( e0 + 40, -700, OVER_Z + 4 ), ( 400, -700, OVER_Z + 4 ) )
    # The stair: up the block's west face to the roof's west end.
    P.stairs( m, ( e0 - 50, -530 ), ( e0 - 50, -980 ), 70, 0, OVER_Z, rails=( True, True ), name="overlook stair" )
    slab( m, e0 - 90, e0, -1030, -980, OVER_Z - 16, OVER_Z, top="oa_grating", side="oa_steel", under="oa_steel", surface=METAL )
    railing_n( m, -1030, -980, e0 - 88, OVER_Z, name="overlook landing" )
    railing_e( m, e0 - 90, e0, -1028, OVER_Z, name="overlook landing south" )
    # The north face's dressing (below the camera, for players in the yard): roller doors, lamps, signs, a pipe.
    for k, ( a, b ) in enumerate( ( ( -300, -180 ), ( 60, 180 ), ( 420, 540 ) ) ):
        for j in range( 10 ):
            P.quad( m, "oa_door", ( ( a + b ) / 2, n1 - 3.5, 6 + j * 11.5 ), ( -1, 0, 0 ), UP, b - a - 2, 10.5 )
        P.wall_light( m, f"Overlook door lamp {k}", ( ( a + b ) / 2, n1, 140 ), ( 0, 1 ), "warm", 360 )
        m.collision_box( ( a, n1 - 6, 0 ), ( b, n1 - 2, 120 ), METAL )
    OP.plate( m, "keep_clear", ( 120, n1 + 0.3, 140 ), ( -1, 0, 0 ), 18 )
    P.pipe( m, [ ( e0 + 30, n1 + 14, 280 ), ( e1 - 30, n1 + 14, 280 ) ], 6, "rv_pipe", 10 )


# ---------------------------------------------------------------------------------------------------------------------
# Launch Control: the tower (01), its balcony and control room, the terrace, the west walkway and the west block

def launch_control( m, glass ):
    e0, e1, n0, n1 = LC
    # The tower's lower storeys (to the balcony): a hall at the terrace's level behind thick walls.
    h0, h1, hn0, hn1 = LC_HALL
    wall( m, "e", e0, e1, n0, hn0, 0, OVER_Z - 16, [ ( -560, -480, TERRACE_Z + 100, TERRACE_Z + 10 ) ], paint="oa_wall_dark" )
    wall( m, "e", e0, e1, hn1, n1, 0, OVER_Z - 16 )
    wall( m, "n", hn0, hn1, e0, h0, 0, OVER_Z - 16, [ ( 70, 150, TERRACE_Z + 104, TERRACE_Z ) ] )
    wall( m, "n", hn0, hn1, h1, e1, 0, OVER_Z - 16, [ ( 60, 140, TERRACE_Z + 104, TERRACE_Z ) ], paint="oa_wall_dark" )
    slab( m, h0, h1, hn0, hn1, 0, TERRACE_Z, top="oa_deck" )
    slab( m, e0, LC_UPPER_E1, n0, n1, OVER_Z - 16, OVER_Z, top="oa_deck", side="oa_wall" )
    OP.tube_light( m, "LC hall lamp 1", ( -700, hn1, 250 ), ( 0, -1 ), 48, "cool", 420 )
    OP.tube_light( m, "LC hall lamp 2", ( -480, hn0, 250 ), ( 0, 1 ), 48, "cool", 420 )
    for k, e in enumerate( ( -800, -720 ) ):
        OP.case_block( m, ( e, hn1 - 40 ), ( 1, 0 ), 1, 1, ( 46, 30, 28 ), 2, "rv_olive", seed=300 + k )
    # Steps from the west court up to the hall's west door.
    for k in range( 4 ):
        box( m, e0 - 64 + k * 16, e0, 70, 150, 0, ( k + 1 ) * 16, "oa_wall_dark", STONE )
    # The upper storeys: a shallow front block carrying the sign out to the corner, and behind it, stepped back, the
    # control room behind the open bay at the balcony's level; a tall plain top over both. Stepped so that from the
    # overlook the tower's east side doesn't hide the sky past its corner, as in the picture.
    up0, up1 = e0, LC_UPPER_E1
    fn1 = n0 + 24.0                 # the front block is the south wall alone
    ee = -350.0                     # the rear part's east face: behind the corner's line of sight from the overlook
    b0, b1 = LC_BAY
    # The corner's back edge stops on the line of sight from the overlook through the front corner, and a wedge fills
    # it, so the wall's thickness never shows past the corner (the picture's crisp edge, with the sun beside it).
    back = up1 * ( n0 + 24 - REF_EYE[1] ) / ( n0 - REF_EYE[1] )
    wall( m, "e", up0, back, n0, n0 + 24, OVER_Z, LC_TOP, [ ( b0, b1, 520, OVER_Z ) ] )
    m.prism( [ ( back, n0 ), ( up1, n0 ), ( back, n0 + 24 ) ], OVER_Z, LC_TOP + 30, { "side": "oa_wall", "top": "oa_wall_dark" }, STONE )
    wall( m, "e", ee, back, fn1 - 24, fn1, OVER_Z, LC_TOP )
    if fn1 - 24 > n0 + 24:
        box( m, ee, up1 - 24, n0 + 24, fn1 - 24, OVER_Z, LC_TOP, { "default": None }, STONE )
    wall( m, "n", fn1 - 24, n1, ee - 24, ee, OVER_Z, LC_TOP )
    wall( m, "e", up0, ee, n1 - 24, n1, OVER_Z, LC_TOP )
    wall( m, "n", n0, n1, up0, up0 + 24, OVER_Z, LC_TOP )
    r0 = -600.0
    r1 = ee - 24
    wall( m, "n", n0 + 24, n1 - 24, r0 - 24, r0, OVER_Z, 540 )
    box( m, up0 + 24, r0 - 24, n0 + 24, n1 - 24, OVER_Z, 540, { "default": None }, STONE )
    for z0_, z1_, top, under in ( ( 540, 560, "oa_wall_dark", "oa_interior_dark" ), ( LC_TOP - 12, LC_TOP, "oa_wall_dark", "oa_wall_dark" ) ):
        slab( m, up0, back, n0, fn1, z0_, z1_, top=top, side="oa_wall", under=under )
        slab( m, up0, ee, fn1, n1, z0_, z1_, top=top, side="oa_wall", under=under )
    box( m, up0 - 6, back, n0 - 6, fn1, LC_TOP, LC_TOP + 30, { "default": "oa_wall_dark", "+z": None, "-z": None }, STONE )
    box( m, up0 - 6, ee + 6, fn1, n1 + 6, LC_TOP, LC_TOP + 30, { "default": "oa_wall_dark", "+z": None, "-z": None }, STONE )
    # The control room: lit, with the CCTV wall and a board on its back wall, consoles, lamps.
    slab( m, r0, r1, n0 + 24, n1 - 24, OVER_Z, OVER_Z + 0.2, top="oa_interior_floor", side=None, under=None, surface=None )
    box( m, r0, r1, n1 - 25, n1 - 24, OVER_Z, 520, "oa_interior" )
    box( m, r0, r0 + 1, n0 + 24, n1 - 24, OVER_Z, 520, "oa_interior" )
    box( m, r1 - 1, r1, n0 + 24, n1 - 24, OVER_Z, 520, "oa_interior" )
    box( m, r0, r1, n0 + 24, n1 - 24, 519, 520, { "default": None, "-z": "oa_interior_dark" } )
    for row in range( 3 ):
        for col in range( 3 ):
            OP.screen( m, "cctv" if ( row + col ) % 2 == 0 else "camera", ( r0 + 40 + col * 42, n1 - 25.5, OVER_Z + 70 + row * 30 ),
                       ( 1, 0, 0 ), 26, off=0.0 )
    OP.plate( m, "board", ( r0 + 190, n1 - 25.5, OVER_Z + 110 ), ( 1, 0, 0 ), 50, off=0.0 )
    OP.plate( m, "chart", ( r0 + 1.2, 100, OVER_Z + 100 ), ( 0, 1, 0 ), 40, off=0.0 )
    for k, e in enumerate( ( r0 + 70, r0 + 180 ) ):
        OP.desk( m, ( e, 110 ), ( 1, 0 ), 90, 30, 30, 3, ( "telemetry", "cctv", "status" ) )
        OP.chair( m, ( e - 20, 80 ), ( 0, 1 ) )
        OP.chair( m, ( e + 22, 78 ), ( 0, 1 ) )
    P.ceiling_light( m, "LC control lamp", ( ( r0 + r1 ) / 2, 60, 512 ), ( 1, 0 ), "warm", 700 )
    for k, e in enumerate( ( r0 + 50, r0 + 170 ) ):
        OP.tube_light( m, f"LC control tube {k}", ( e, n1 - 25, 470 ), ( 0, -1 ), 48, "warm", 300, light=( k == 0 ) )
    # The south face: LAUNCH CONTROL and 01 between the bay and the corner, lamps, a fire sign low down.
    face = n0
    right = v( 1, 0, 0 )
    OP.letters( m, "launch_control", ( -293, face - 0.6, 466 ), right, 44, "dark" )
    OP.letters( m, "n01", ( -294, face - 0.6, 406 ), right, 56, "dark" )
    box( m, LC_BAY[1], -346, face - 2.5, face, OVER_Z, 524, "oa_steel" )
    box( m, LC_BAY[0], -346, face - 2.5, face, 506, 524, "oa_steel" )
    for k, ( e, z ) in enumerate( ( ( -322.0, 250.0 ), ( -381.0, 181.0 ) ) ):
        OP.tube_light( m, f"LC face lamp {k}", ( e, face, z ), ( 0, -1 ), 52, "cool", 320, shadows=True, colour="0.3,0.34,0.4,1" )
    OP.plate( m, "fire", ( -340, face - 0.4, 163 ), right, 16 )
    # The south sky on the face (the blue anti-solar sky and the sunlit east half of the overlook's north wall): high,
    # broad and lavender, so it reads neutral after the 5300 K grade.
    P.LIGHTS.append( ( "LC face fill", ( -420, face - 390, 470 ), "3.7,3.6,4.7,1", 1000, False ) )
    OP.plate( m, "warning", ( -470, face - 0.4, 200 ), right, 20 )
    # The balcony: a slab on columns, a railing round it, the stair down to the west court.
    bx0, bx1, bn0, bn1 = LC_BALCONY
    slab( m, bx0, bx1, bn0, bn1, OVER_Z - 16, OVER_Z, top="oa_deck", side="oa_wall_dark", under="oa_wall_dark" )
    for e in ( -900, -620, -340 ):
        column( m, e, bn0 + 12, 0, OVER_Z - 16, 22 )
    railing_e( m, -440, bx1, bn0 + 3, OVER_Z, name="LC balcony" )
    railing_e( m, bx0 + 60, -560, bn0 + 3, OVER_Z, name="LC balcony west" )
    railing_n( m, bn0 + 3, bn1, bx1 - 3, OVER_Z, name="LC balcony east" )
    P.stairs( m, ( bx0 + 30, -640 ), ( bx0 + 30, bn0 ), 60, 0, OVER_Z, name="LC balcony stair" )
    # The walkway from the balcony south to the overlook's roof, along the tower's west side.
    slab( m, -560, -440, -560, bn0, OVER_Z - 16, OVER_Z, top="oa_grating", side="oa_steel", under="oa_steel", surface=METAL )
    railing_n( m, -560, bn0, -558, OVER_Z, name="overlook walk west" )
    railing_n( m, -540, bn0, -442, OVER_Z, name="overlook walk east" )
    for n in ( -480, -330 ):
        column( m, -500, n, 0, OVER_Z - 16, 14, "oa_steel" )
    # The upper overhang: a slab and railing at 540 on the face, reaching past the corner (the picture's top left).
    oz0, oz1, orad = 494.0, 532.0, 36.0
    oc = ( -205.0 - orad, n0 - orad )
    arc = [ ( oc[0] + orad * math.cos( a ), oc[1] + orad * math.sin( a ) ) for a in np.linspace( -math.pi / 2, math.pi / 2, 9 ) ]
    outline = [ ( e0, n0 - 2 * orad ) ] + arc + [ ( e0, n0 ) ]
    m.prism( outline, oz0, oz1, { "side": "oa_wall", "top": "oa_deck", "bottom": "oa_wall_dark" } )
    rail = [ ( e0, n0 - 2 * orad + 3 ) ] + [ ( oc[0] + ( orad - 3 ) * math.cos( a ), oc[1] + ( orad - 3 ) * math.sin( a ) )
                                              for a in np.linspace( -math.pi / 2, math.pi / 2, 7 ) ] + [ ( oc[0], n0 - 1 ) ]
    P.railing( m, rail, oz1, "oa_yellow", height=40, post_every=50, clip_to=None, name="LC top" )
    box( m, e0 + 20, -320, n0 - 6, n0, 560, 620, "oa_window_dark" )
    for e in np.arange( -840, -340, 140 ):
        box( m, e, e + 60, n0 - 6.2, n0 - 6, 566, 614, "oa_window_lit" )
    for e in np.arange( -880, -330, 70 ):
        box( m, e - 2, e + 2, n0 - 7, n0 - 5, 560, 620, "oa_glass_frame" )
    # The terrace: a raised slab east of the tower, its east edge a parapet with a railing; steps down to the yard.
    pts = TERRACE
    m.prism( pts, 0, TERRACE_Z, { "side": "oa_wall_dark", "top": "oa_yard" }, STONE )
    a, b = v( *pts[1], 0 ), v( *pts[2], 0 )
    d = unit( b - a )
    out = np.cross( d, UP )
    gaps = ( ( 0.08, 0.2 ), ( 0.55, 0.66 ) )
    segs = []
    last = 0.0
    for g0, g1 in gaps:
        segs.append( ( last, g0 ) )
        last = g1
    segs.append( ( last, 1.0 ) )
    L = float( np.linalg.norm( b - a ) )
    side = np.cross( UP, d )
    for f0, f1 in segs:
        p0, p1 = a + d * L * f0, a + d * L * f1
        q = ( p0 + p1 ) / 2
        m.oriented_box( q + UP * ( TERRACE_Z + 16 ) - out * 6, ( d, side, UP ), ( L * ( f1 - f0 ), 12, 32 ), "oa_wall_dark", STONE )
        P.railing( m, [ ( p0[0] - out[0] * 6, p0[1] - out[1] * 6 ), ( p1[0] - out[0] * 6, p1[1] - out[1] * 6 ) ], TERRACE_Z + 32, "oa_yellow",
                   height=36, post_every=50, clip_to=40, name="terrace rail" )
    for g0, g1 in gaps:
        p0, p1 = a + d * L * g0, a + d * L * g1
        for k in range( 4 ):
            off = out * ( 7 + k * 14 )
            hgt = TERRACE_Z - ( k + 1 ) * 16
            if hgt <= 0:
                continue
            q = ( p0 + p1 ) / 2 + off
            m.oriented_box( q + UP * ( hgt / 2 ), ( d, side, UP ), ( L * ( g1 - g0 ), 14, hgt ), { "default": "oa_wall_dark", "+z": "oa_deck" }, STONE )
    # The terrace's south steps (towards the overlook).
    for k in range( 4 ):
        box( m, -316, -120, -250 - ( k + 1 ) * 14, -250 - k * 14, 0, TERRACE_Z - ( k + 1 ) * 16 + 0.01, { "default": "oa_wall_dark", "+z": "oa_deck" }, STONE )
    # The terrace's dressing: cases, a crate, a lamp on the tower's east face.
    OP.case_block( m, ( -305, 60 ), ( 0, 1 ), 2, 1, ( 46, 30, 28 ), 1, "rv_case", seed=310 )
    OP.red_crate( m, ( -270, -170 ), ( 1, 0.1 ), z0=TERRACE_Z )
    P.wall_light( m, "Terrace lamp", ( e1, 120, 190 ), ( 1, 0 ), "warm", 380 )
    # The west walkway: stairs up from the terrace's north end, then a deck on posts north to the mezzanine.
    w0, w1, wn0, wn1 = WALKWAY
    P.stairs( m, ( ( w0 + w1 ) / 2 + 30, 210 ), ( ( w0 + w1 ) / 2 + 30, wn0 ), w1 - w0 - 10, TERRACE_Z, WALK_Z, name="walkway stair" )
    slab( m, w0, w1 + 30, wn0, wn0 + 40, WALK_Z - 10, WALK_Z, top="oa_deck" )
    slab( m, w0, w1, wn0, wn1, WALK_Z - 10, WALK_Z, top="oa_deck", side="oa_wall_dark", under="oa_wall_dark" )
    for n in np.arange( wn0 + 40, wn1, 110 ):
        column( m, w0 + 10, n, 0, WALK_Z - 10, 14, "oa_steel" )
        column( m, w1 - 10, n, 0, WALK_Z - 10, 14, "oa_steel" )
    railing_n( m, wn0, wn1, w0 + 3, WALK_Z, name="walkway west" )
    railing_n( m, wn0 + 40, wn1, w1 - 3, WALK_Z, name="walkway east" )
    P.pipe( m, [ ( w1 + 6, wn0 + 40, WALK_Z - 18 ), ( w1 + 6, wn1, WALK_Z - 18 ) ], 5, "rv_pipe", 10 )
    P.pipe( m, [ ( w1 + 18, wn0 + 40, WALK_Z - 18 ), ( w1 + 18, wn1, WALK_Z - 18 ) ], 4, "rv_pipe", 10 )
    # The west block: one tall storey of concrete; on its roof the red container and roof plant.
    we0, we1, wn0_, wn1_ = WEST
    box( m, we0, we1, wn0_, wn1_, 0, WEST_TOP, { "default": "oa_wall", "+z": "oa_wall_dark" }, STONE )
    box( m, we0, we1, wn0_, wn1_, WEST_TOP, WEST_TOP + 20, { "default": "oa_wall_dark", "+z": None, "-z": None } )
    for k, n in enumerate( ( 300, 450, 600 ) ):
        P.door( m, ( we1, n, 0 ), ( 0, 1, 0 ), 70, 96, "rv_door", window=False, double=False )
        P.wall_light( m, f"West block lamp {k}", ( we1, n, 112 ), ( 1, 0 ), "warm", 300 )
    import lowtide_container as LCN
    LCN.build( m, -520, 600, WEST_TOP, "20", "e", "rw_container_red", door_end=1 )
    box( m, -800, -640, 260, 420, WEST_TOP, WEST_TOP + 80, { "default": "oa_steel", "+z": "oa_grating" } )
    P.louvre( m, ( -640, 340, WEST_TOP + 40 ), ( 0, 1, 0 ), 120, 60 )


# ---------------------------------------------------------------------------------------------------------------------
# The launch deck: the ORION block, the mezzanine and undercroft, the service tunnel and the red room

def launch_deck( m ):
    d0, d1, dn0, dn1 = DECK
    t0, t1, tn0, tn1 = TUNNEL
    # The deck's mass: solid west of the tunnel and east of it; the tunnel and the red room hollow under a slab.
    box( m, d0, t0, dn0, dn1, 0, G, { "default": "oa_wall", "-y": "oa_wall_dark", "+z": "oa_deck" }, STONE )
    box( m, t1, d1, dn0, dn1, 0, G, { "default": "oa_wall", "-y": "oa_wall_dark", "+z": "oa_deck" }, STONE )
    box( m, -900, d0, 700, dn1, 0, G, { "default": "oa_wall", "-y": "oa_wall_dark", "+z": "oa_deck" }, STONE )
    s0, s1, sn0, sn1 = DECK_STAIR
    # The slab over the tunnel, open over the deck stair from where it needs headroom.
    for e0_, e1_, n0_, n1_ in ( ( t0, s0 - 8, dn0, dn1 ), ( s1 + 8, t1, dn0, dn1 ), ( s0 - 8, s1 + 8, dn0, 1120 ), ( s0 - 8, s1 + 8, sn1 + 4, dn1 ) ):
        if e1_ > e0_ and n1_ > n0_:
            slab( m, e0_, e1_, n0_, n1_, TUNNEL_TOP, G, top="oa_deck", side="oa_wall", under="oa_wall_dark", surface=None )
            m.collision_box( ( e0_, n0_, TUNNEL_TOP ), ( e1_, n1_, G ), STONE )
    railing_n( m, 1120, sn1 + 4, s0 - 6, G, name="stairwell west" )
    railing_e( m, s0 - 8, s1 + 8, 1120, G, name="stairwell south" )
    # Tunnel walls, floor, ceiling dressing.
    slab( m, t0, t1, tn0, dn1, 0, 0.2, top="oa_deck", side=None, under=None, surface=None )
    box( m, t0, t0 + 1, tn0, dn1, 0, TUNNEL_TOP, "oa_wall_dark" )
    box( m, t1 - 1, t1, tn0, dn1, 0, TUNNEL_TOP, "oa_wall_dark" )
    for k, n in enumerate( np.arange( tn0 + 50, tn1, 90 ) ):
        P.ceiling_light( m, f"Tunnel lamp {k}", ( ( t0 + t1 ) / 2 - 40, n, TUNNEL_TOP - 8 ), ( 1, 0 ), "warm", 240, light=( k % 2 == 0 ) )
    for k, r_ in enumerate( ( 7.0, 5.0, 5.0, 4.0 ) ):
        P.pipe( m, [ ( t0 + 14, tn0, TUNNEL_TOP - 20 - k * 16 ), ( t0 + 14, dn1 - 10, TUNNEL_TOP - 20 - k * 16 ) ], r_, "rv_pipe", 10 )
    P.cable_tray( m, ( t1 - 90, tn0, TUNNEL_TOP - 14 ), ( t1 - 90, dn1 - 20, TUNNEL_TOP - 14 ) )
    for n in np.arange( tn0 + 30, dn1, 160 ):
        box( m, t0, t1, n - 6, n + 6, TUNNEL_TOP - 10, TUNNEL_TOP, "oa_steel" )
    P.quad( m, "oa_hazard", ( t0 + 1.5, tn0 + 6, 90 ), ( 0, 1, 0 ), UP, 10, 180, off=0.2 )
    P.quad( m, "oa_hazard", ( t1 - 1.5, tn0 + 6, 90 ), ( 0, -1, 0 ), UP, 10, 180, off=0.2 )
    OP.letters( m, "service_tunnel", ( ( t0 + t1 ) / 2, dn0 - 0.5, TUNNEL_TOP + 22 ), v( 1, 0, 0 ), 22, "dark" )
    # The stair up to the deck, along the tunnel's east wall.
    P.stairs( m, ( ( s0 + s1 ) / 2, sn0 ), ( ( s0 + s1 ) / 2, sn1 ), s1 - s0 - 4, 0, G, rails=( True, False ), name="deck stair" )
    # The red room: dark concrete lit red round its two doors (the picture's red doorway at the end of the arcade),
    # red crates.
    r0, r1, rn0, rn1 = RED_ROOM
    box( m, r0 + 1, r1 - 1, rn1 - 2, rn1, 0, TUNNEL_TOP, "oa_wall_dark" )
    for k, e in enumerate( ( 260, 360 ) ):
        OP.plate( m, "red_door", ( e, rn1 - 2.5, 50 ), v( 1, 0, 0 ), 100, off=0.0 )
        P.LIGHTS.append( ( f"Red room lamp {k}", ( e, rn1 - 30, 120 ), OP.RED_ROOM, 160, k == 0 ) )
        box( m, e - 30, e + 30, rn1 - 6, rn1 - 2, 140, 146, "oa_red_glow" )
    # The south sky on the ORION block's shaded face, as on Launch Control's: high and lavender, out over the yard.
    P.LIGHTS.append( ( "ORION face fill", ( ( ORION[0] + ORION[1] ) / 2, ORION[2] - 370, 520 ), "11.2,11,13.6,1", 700, False ) )
    OP.red_crate( m, ( 230, 1290 ), ( 1, 0 ), ( 60, 40, 50 ) )
    OP.red_crate( m, ( 300, 1300 ), ( 1, 0.05 ), ( 44, 34, 40 ) )
    OP.red_crate( m, ( 330, 1215 ), ( 0, 1 ), ( 60, 40, 50 ) )
    # The ORION block: its face, the mark and the name, pipes up its west edge, a door.
    o0, o1, on0, on1 = ORION
    box( m, o0, o1, on0, on1, 0, G, { "default": "oa_wall", "+z": "oa_deck" }, STONE )
    OP.letters( m, "mark_wordmark", ( ( o0 + o1 ) / 2, on0 - 0.6, 158 ), v( 1, 0, 0 ), 152, "dark" )
    for k, e in enumerate( ( o0 - 6, o0 - 18 ) ):
        P.pipe( m, [ ( e, on0 - 6, 0 ), ( e, on0 - 6, G - 10 ), ( e, on0 + 30, G + 6 ) ], 4.5 - k, "rv_pipe", 10 )
    P.door( m, ( o0 + 40, on0, 0 ), ( 1, 0, 0 ), 40, 88, "rv_door", window=False, double=False )
    P.wall_light( m, "ORION lamp", ( o0 + 40, on0, 110 ), ( 0, -1 ), "warm", 160 )
    OP.plate( m, "hazmat", ( o1 - 30, on0 - 0.4, 70 ), v( 1, 0, 0 ), 18 )
    # The mezzanine along the deck's front at 144, the undercroft under it. Its front is the picture's deck wall: a deep
    # concrete fascia and a solid parapet reading as one face from the arcade's head to the coping, a low rail on top,
    # a big pipe run along its foot turning up the ORION block's west edge. The walkway comes up through a gap in the
    # parapet. The parapet stands 36 in over the walkway (cover to shoot over), and from the overlook its top hides the
    # mezzanine's floor, as the picture's wall does.
    m0, m1, mn0, mn1 = MEZZ
    slab( m, m0, m1, mn0, mn1, WALK_Z - 12, WALK_Z, top="oa_deck", side="oa_wall", under="oa_wall_dark" )
    box( m, m0, m1, mn0 - 2, mn0 + 10, FASCIA_Z, WALK_Z - 12, "oa_wall_dark", STONE )
    for k, ( a, b ) in enumerate( ( ( m0, WALKWAY[0] ), ( WALKWAY[1], m1 ) ) ):
        box( m, a, b, mn0 - 2, mn0 + 8, WALK_Z, PARAPET_Z, "oa_wall_dark", STONE )
        box( m, a, b, mn0 - 4, mn0 + 10, PARAPET_Z, PARAPET_Z + 4, "oa_wall_dark", STONE )
        railing_e( m, a, b, mn0 + 3, PARAPET_Z + 4, height=18, post_every=72, kick=False, clip_to=48,
                   name=( "mezzanine west", "mezzanine east" )[k] )
    for e in ( -540, -420, -180, -95 ):
        column( m, e, mn0 + 16, 0, FASCIA_Z, 22 )
    for k, ( r_, z, off ) in enumerate( ( ( 9.0, FASCIA_Z + 12, 13 ), ( 5.0, FASCIA_Z + 30, 9 ) ) ):
        P.pipe( m, [ ( m0, mn0 - off, z ), ( m1 - 26 - k * 12, mn0 - off, z ), ( m1 - 26 - k * 12, mn0 - off, G - 30 ) ], r_, "rv_pipe", 12 )
    for e in np.arange( m0 + 60, m1 - 40, 120 ):
        box( m, e - 2, e + 2, mn0 - 24, mn0 - 2, FASCIA_Z + 2, FASCIA_Z + 5, "oa_steel" )
    # The arcade's lamps: warm battens under the mezzanine, lighting its head and the yard in front of it.
    for k, e in enumerate( ( -470, -330, -190 ) ):
        P.ceiling_light( m, f"Arcade lamp {k}", ( e, mn0 + 56, WALK_Z - 20 ), ( 1, 0 ), "warm", 300, light=k != 1, hang=6 )
    # The undercroft's back wall is the deck's south face: doors, lit alcoves, lamps, a poster.
    for k, e in enumerate( ( -500, -380, -250, -130 ) ):
        box( m, e - 30, e + 30, dn0 - 0.1, dn0, 10, 96, "oa_window_lit" if k % 2 else "oa_door" )
        P.wall_light( m, f"Undercroft lamp {k}", ( e, dn0, 112 ), ( 0, -1 ), "cool" if k % 2 else "warm", 220 )
    OP.plate( m, "poster_safety", ( -315, dn0 - 0.4, 60 ), v( 1, 0, 0 ), 36 )
    OP.plate( m, "authorised", ( -200, dn0 - 0.4, 108 ), v( 1, 0, 0 ), 12 )
    # The deck's face over the mezzanine: a lit doorway, cabinets, a pipe run along it, cases stacked against it.
    box( m, -478, -422, dn0 - 0.2, dn0, WALK_Z, WALK_Z + 86, "oa_window_lit" )
    box( m, -484, -416, dn0 - 3, dn0, WALK_Z + 86, WALK_Z + 92, "oa_dark" )
    P.wall_light( m, "Mezzanine door lamp", ( -450, dn0, WALK_Z + 100 ), ( 0, -1 ), "warm", 150 )
    for e in ( -360, -150 ):
        box( m, e - 22, e + 22, dn0 - 16, dn0, WALK_Z, WALK_Z + 72, { "default": "oa_steel", "-y": "oa_dark" }, METAL )
    for k, ( r_, dz ) in enumerate( ( ( 7.0, 0 ), ( 5.0, 18 ) ) ):
        P.pipe( m, [ ( m0, dn0 - 10 - k * 2, WALK_Z + 76 + dz ), ( m1, dn0 - 10 - k * 2, WALK_Z + 76 + dz ) ], r_, "rv_pipe", 10 )
    OP.case_block( m, ( -300, 858 ), ( 1, 0 ), 2, 1, ( 52, 32, 30 ), 2, "rv_case", seed=430, z0=WALK_Z )
    # More stacks along the deck wall, as the picture's row of dark cases there.
    OP.case_block( m, ( -210, 862 ), ( 1, 0 ), 2, 1, ( 50, 32, 30 ), 2, "rv_case", seed=431, z0=WALK_Z )
    OP.case_block( m, ( -112, 866 ), ( 1, 0 ), 1, 1, ( 50, 30, 30 ), 2, "rv_case", seed=432, z0=WALK_Z )
    # Stair from the mezzanine up to the deck, at its west end.
    P.stairs( m, ( -525, mn0 + 50 ), ( -525, dn0 ), 64, WALK_Z, G, name="mezzanine stair" )
    # The deck's south edge railings, and the ORION block's top.
    railing_e( m, -490, o0, dn0 + 3, G, name="deck edge west" )
    railing_e( m, o0, o1, on0 + 3, G, name="ORION top" )
    railing_n( m, on0, dn0, o0 + 3, G, name="ORION top west" )
    railing_n( m, on0, dn0, o1 - 3, G, name="ORION top east" )
    railing_e( m, o1, d1, dn0 + 3, G, name="deck edge east" )
    # The deck's north edge: a fence over the drop to the pad's apron, players clipped well over it.
    P.railing( m, [ ( d0, dn1 - 4 ), ( d1, dn1 - 4 ) ], G, "oa_yellow", height=42, post_every=60, clip_to=600, name="deck north" )
    P.railing( m, [ ( d0 + 4, dn0 ), ( d0 + 4, dn1 ) ], G, "oa_yellow", height=42, post_every=60, clip_to=600, name="deck west" )
    # The deck's dressing: cases and crates for cover (bomb site A), a control shed, vents, pipes.
    OP.case_block( m, ( -330, 1060 ), ( 1, 0 ), 3, 2, ( 52, 32, 30 ), 2, "rv_olive", tarp=True, seed=400, z0=G )
    OP.case_block( m, ( -60, 1210 ), ( 0, 1 ), 2, 1, ( 52, 32, 30 ), 2, "rv_case", seed=401, z0=G )
    OP.red_crate( m, ( 60, 1080 ), ( 1, 0.2 ), ( 60, 40, 50 ), z0=G )
    OP.red_crate( m, ( 110, 1100 ), ( 0.2, 1 ), ( 44, 34, 40 ), z0=G )
    import lowtide_container as LCN
    LCN.build( m, -360, 1290, G, "20", "e", "rw_container_red", door_end=1 )
    for k, ( e, n ) in enumerate( ( ( -520, 1110 ), ( 140, 1330 ), ( 330, 1060 ) ) ):
        OP.case_block( m, ( e, n ), ( 1, 0.1 * k ), 2, 1, ( 48, 30, 28 ), 1 + k % 2, "rv_case" if k % 2 else "rv_olive", seed=410 + k, z0=G )
    box( m, -230, -110, 1290, 1380, G, G + 110, { "default": "oa_steel", "+z": "oa_dark" }, METAL )
    # More clutter on the deck's top (the picture's strip of machinery and cases along it): a generator, cable drums,
    # crates and a run of pipes on stands.
    # Approved standalone generator replaces the plain box; retain its collision.
    OG.collision( m, G )
    # The approved standalone reel replaces both placeholder shells. Its first
    # collision stays here; the second placement obstructed the stair opening.
    OCR.collision( m, G )
    OP.case_block( m, ( -20, 1340 ), ( 1, 0 ), 3, 1, ( 52, 32, 30 ), 2, "rv_olive", tarp=True, seed=420, z0=G )
    OP.case_block( m, ( 520, 1180 ), ( 0, 1 ), 2, 1, ( 48, 30, 28 ), 1, "rv_case", seed=421, z0=G )
    P.door( m, ( -170, 1290, G ), ( 1, 0, 0 ), 40, 84, "rv_door", window=True, double=False )
    P.wall_light( m, "Deck shed lamp", ( -170, 1290, G + 96 ), ( 0, -1 ), "warm", 360 )
    for k, e in enumerate( ( -500, -100, 260 ) ):
        box( m, e - 20, e + 20, 1366, 1390, G, G + 30, { "default": "oa_steel", "+z": "oa_grating" }, METAL )
    for k, r_ in enumerate( ( 10.0, 7.0 ) ):
        OP.banded_pipe( m, [ ( d0 + 30, 1380 - k * 26, G + 22 ), ( d1 - 10, 1380 - k * 26, G + 22 ) ], r_, every=180 )
    for e in np.arange( d0 + 80, d1, 200 ):
        OP.pipe_saddle( m, ( e, 1380, G + 22 ), 10, 22, ( 1, 0 ) )
    # Work lamps along the deck's north fence.
    for k, e in enumerate( ( -400, 0, 400 ) ):
        P.wall_light( m, f"Deck fence lamp {k}", ( e, dn1 - 20, G + 70 ), ( 0, -1 ), "warm", 520 )
        box( m, e - 2, e + 2, dn1 - 22, dn1 - 18, G, G + 70, "oa_steel" )


# ---------------------------------------------------------------------------------------------------------------------
# Fuel Processing: B3, the east block and its hall, OPS, the fuel lines

B3_FACE_BEARING = 144.0     # B3's west face runs this way (degrees east of north) from the block's south-west corner
B3_FACE_LEN = 330.0
B3_WEDGE_E1 = 560.0


def b3_frame():
    """ B3's oblique west face: its north end (the block's south-west corner), the way it runs, and its outward normal.
    The picture sees this face at an angle, its lettering and joints running down towards the camera's right. """
    d = np.array( ( math.sin( math.radians( B3_FACE_BEARING ) ), math.cos( math.radians( B3_FACE_BEARING ) ) ) )
    return np.array( ( B3[0], B3[2] ) ), d, np.array( ( d[1], -d[0] ) )


def b3_point( t, off=0.0, z=0.0 ):
    """ A point t along B3's oblique face from its north end, off out from it, z up. """
    p0, d, out = b3_frame()
    q = p0 + d * t + out * off
    return ( float( q[0] ), float( q[1] ), float( z ) )


def fuel( m, glass ):
    b0, b1, bn0, bn1 = B3
    # B3: a tall block with a wedge on its south-west whose west face meets the yard at an angle; the name, the arrow and
    # the big fuel lines run along that face.
    # Its west side recedes along the reference eye's line of sight through its south-west corner (2 in further, so the
    # face turns away from REF_EYE rather than edge-on): the picture never shows a west face here.
    bw1 = REF_EYE[0] + ( b0 - REF_EYE[0] ) * ( bn1 - REF_EYE[1] ) / ( bn0 - REF_EYE[1] ) + 2.0      # ~284.4
    m.prism( [ ( b0, bn0 ), ( b1, bn0 ), ( b1, bn1 ), ( bw1, bn1 ) ], 0, B3_TOP, { "side": "oa_wall", "top": "oa_deck" }, STONE )
    p0, d, outv = b3_frame()
    p1 = p0 + d * B3_FACE_LEN
    wedge = [ tuple( p0 ), tuple( p1 ), ( B3_WEDGE_E1, float( p1[1] ) ), ( B3_WEDGE_E1, float( p0[1] ) ) ]
    m.prism( wedge, 0, B3_TOP, { "side": "oa_wall", "top": "oa_deck" }, STONE )
    right = v( d[0], d[1], 0 )
    o3 = v( outv[0], outv[1], 0 )
    # The roof's coping along the face, a little proud: dark, weathered and wet (the picture's dark line under the
    # railing), with a lighter top.
    m.oriented_box( v( *b3_point( B3_FACE_LEN / 2, 2.0, B3_TOP - 7 ) ), ( right, -o3, UP ), ( B3_FACE_LEN, 8, 14 ),
                    { "default": "oa_roof_dark", "+z": "oa_deck" } )
    # The roof's railing round B3 and its wedge.
    inward = -outv
    t_corner = ( p0[1] + 3 * inward[1] - ( p1[1] + 3 ) ) / -d[1]
    corner = p0 + d * t_corner + inward * 3
    rail = [ ( bw1 + 3, bn1 ), ( b0 + 3, bn0 + 1 ), ( float( corner[0] ), float( corner[1] ) ),
             ( B3_WEDGE_E1 - 3, float( p1[1] ) + 3 ), ( B3_WEDGE_E1 - 3, bn0 + 3 ), ( b1 - 20, bn0 + 3 ) ]
    P.railing( m, rail, B3_TOP, "oa_yellow", height=42, post_every=60, clip_to=600, name="B3 roof" )
    OP.letters( m, "b3", b3_point( 51, 0.6, 196 ), right, 44, "dark" )
    OP.letters( m, "fuel_processing", b3_point( 66, 0.6, 144 ), right, 50, "dark" )
    P.wall_light( m, "B3 lamp", b3_point( 78, 0, 44 ), outv, "warm", 300 )
    P.LIGHTS.append( ( "B3 face wash", b3_point( 40, 260, 230 ), "2.0,1.7,1.3,1", 1000, False ) )
    # The fuel lines along the face: a big silver line high up with a flanged end (the picture's), a yellow one under it,
    # two smaller lines dropping to the ground and running along its foot; past the face they all turn south to the
    # overlook's north wall.
    end_t = B3_FACE_LEN + 34
    runs = [ ( 124, 50, 232, 24, "oa_pipe", True ), ( 150, 46, 150, 16, "oa_yellow", False ) ]
    for t0, off, z, r, paint, flange in runs:
        a, b = b3_point( t0, off, z ), b3_point( end_t, off, z )
        pts = [ a, b, ( b[0], SOUTH[3] + 2, z ) ]
        if paint == "oa_pipe":
            OP.banded_pipe( m, pts, r, every=150, flanges=( 0, ) if flange else () )
        else:
            P.pipe( m, pts, r, paint, 14, flanges=() )
        for t in np.arange( t0 + 40, end_t, 90 ):
            OP.pipe_saddle( m, b3_point( t, off, z ), r, z, ( d[0], d[1] ) )
        c = v( *b3_point( ( t0 + end_t ) / 2, off, z ) )
        m.oriented_box( c, ( right, -o3, UP ), ( end_t - t0, r * 2, r * 2 ), { "default": None }, METAL )
        m.collision_box( ( b[0] - r, SOUTH[3], z - r ), ( b[0] + r, b[1] + r, z + r ), METAL )
    lows = [ ( 132, 44, 232 - 24, 26, 13, end_t - 14 ), ( 190, 34, 150 - 16, 14, 9, end_t + 40 ) ]
    for t0, off, ztop, z, r, t1 in lows:
        a, b = b3_point( t0, off, ztop ), b3_point( t0, off, z )
        c_ = b3_point( t1, off, z )
        OP.banded_pipe( m, [ a, b, c_, ( c_[0], SOUTH[3] + 2, z ) ], r, every=120 )
        m.collision_box( ( a[0] - r, a[1] - r, z ), ( a[0] + r, a[1] + r, ztop ), METAL )
        m.collision_box( ( c_[0] - r - 4, SOUTH[3], 0 ), ( c_[0] + r + 4, c_[1] + r, z + r ), METAL )
    # The low lines' collision along the face's foot: a kerb you step over or mantle.
    c = v( *b3_point( ( 120 + end_t + 40 ) / 2, 39, 20 ) )
    m.oriented_box( c, ( right, -o3, UP ), ( end_t + 40 - 120, 36, 40 ), { "default": None }, METAL )
    P.wall_light( m, "Fuel line lamp", ( 760, bn0, 60 ), ( 0, -1 ), "warm", 380 )
    # Cases on the wedge's roof along its edge (the picture's big cases right of the railing).
    OP.case_block( m, b3_point( 150, -50 ), ( d[0], d[1] ), 3, 1, ( 60, 36, 38 ), 2, "rv_case", seed=522, z0=B3_TOP )
    # The east block: a hall inside (tanks, pipes), stairs up to its roof, doors to the yard and the east court.
    e0, e1, n0, n1 = EAST
    h0, h1, hn0, hn1 = FUEL_HALL
    wall( m, "n", n0, n1, e0, h0, 0, G - 20, [ ( 420, 520, 120 ), ( 820, 900, 110 ) ] )
    wall( m, "n", n0, n1, h1, e1, 0, G - 20, [ ( 520, 620, 120 ), ( 880, 960, 110 ) ] )
    wall( m, "e", h0, h1, n0, hn0, 0, G - 20 )
    wall( m, "e", h0, h1, hn1, n1, 0, G - 20 )
    for e0_, e1_, n0_, n1_ in ( ( e0, h1 - 90, n0, n1 ), ( h1 - 90, e1, n0, 600 ), ( h1 - 90, e1, 1000, n1 ), ( h1, e1, 600, 1000 ) ):
        slab( m, e0_, e1_, n0_, n1_, G - 20, G, top="oa_deck", side="oa_wall", under="oa_wall_dark", surface=None )
    slab( m, h0, h1, hn0, hn1, 0, 0.2, top="oa_deck", side=None, under=None, surface=None )
    for k, ( e, n ) in enumerate( ( ( 760, 520 ), ( 960, 520 ), ( 760, 780 ), ( 960, 780 ) ) ):
        P.tank( m, ( e, n ), 52, 150, "rv_white", 0, 20, rings=True, ladder=( k % 2 == 0 ), facing=( 0, -1 ) )
        m.collision_box( ( e - 58, n - 58, 0 ), ( e + 58, n + 58, 170 ), METAL )
    for k, n in enumerate( np.arange( hn0 + 60, hn1, 140 ) ):
        P.ceiling_light( m, f"Fuel hall lamp {k}", ( 860, n, G - 30 ), ( 0, 1 ), "cool", 480, light=( k % 2 == 0 ) )
    for k, r_ in enumerate( ( 8.0, 6.0 ) ):
        P.pipe( m, [ ( h0 + 20, hn0 + 30 + k * 20, G - 50 ), ( h1 - 20, hn0 + 30 + k * 20, G - 50 ), ( h1 - 20, hn1 - 30, G - 50 ) ], r_, "rv_pipe", 10 )
    P.stairs( m, ( h1 - 50, 640 ), ( h1 - 50, 960 ), 70, 0, G, rails=( True, False ), name="fuel stair" )
    # The roof slab's collision, open over the stair.
    for e0_, e1_, n0_, n1_ in ( ( e0, h1 - 90, n0, n1 ), ( h1 - 90, e1, n0, 600 ), ( h1 - 90, e1, 1000, n1 ), ( h1 + 0, e1, 600, 1000 ) ):
        m.collision_box( ( e0_, n0_, G - 20 ), ( e1_, n1_, G ), STONE )
    railing_n( m, 600, 960, h1 - 92, G, name="fuel stairwell" )
    railing_e( m, h1 - 92, h1, 600, G, name="fuel stairwell south" )
    OP.case_block( m, ( 640, 340 ), ( 1, 0 ), 2, 1, ( 48, 30, 28 ), 2, "rv_olive", seed=500 )
    OP.case_block( m, ( 900, 360 ), ( 1, 0 ), 1, 2, ( 48, 30, 28 ), 1, "rv_case", seed=501 )
    for k, ( n, dz ) in enumerate( ( ( 470, 120 ), ( 860, 110 ) ) ):
        P.wall_light( m, f"Fuel yard door lamp {k}", ( e0, n, dz + 16 ), ( -1, 0 ), "warm", 320 )
    OP.letters( m, "fuel_small", ( e0 - 0.6, 470, 150 ), v( 0, -1, 0 ), 14, "dark" )
    # The roof: railings along its west edge (over the yard) and the boundary; steps up to B3's roof.
    railing_n( m, n0 + 100, DECK[2], e0 + 3, G, name="east roof west" )
    P.railing( m, [ ( e1 - 4, n0 ), ( e1 - 4, n1 ) ], G, "oa_yellow", height=42, post_every=60, clip_to=600, name="east roof east" )
    P.railing( m, [ ( e0, n1 - 4 ), ( e1, n1 - 4 ) ], G, "oa_yellow", height=42, post_every=60, clip_to=600, name="east roof north" )
    for k in range( 5 ):
        box( m, 800, 900, bn1 + 40 - ( k + 1 ) * 8, bn1 + 40 - k * 8, G, G + ( k + 1 ) * 8, { "default": "oa_wall_dark", "+z": "oa_deck" }, STONE )
    box( m, 560, 800, bn1, bn1 + 16, G, B3_TOP, "oa_wall_dark", STONE )
    box( m, 900, b1, bn1, bn1 + 16, G, B3_TOP, "oa_wall_dark", STONE )
    # The roof's dressing: a grey container on B3's roof, crates, cases, vents, the stairwell's hood.
    import lowtide_container as LCN
    OP.case_block( m, ( 420, 74 ), ( 1, 0 ), 4, 2, ( 60, 34, 36 ), 1, "rv_case", seed=520, z0=B3_TOP )
    OP.case_block( m, ( 700, 80 ), ( 1, 0 ), 2, 1, ( 52, 32, 30 ), 2, "rv_olive", seed=521, z0=B3_TOP )
    OP.case_block( m, ( 660, 470 ), ( 1, 0 ), 3, 1, ( 52, 32, 30 ), 2, "rv_olive", tarp=True, seed=510, z0=G )
    OP.case_block( m, ( 820, 560 ), ( 0, 1 ), 2, 1, ( 52, 32, 30 ), 1, "rv_case", seed=511, z0=G )
    for k, ( e, n ) in enumerate( ( ( 1040, 400 ), ( 1060, 1100 ) ) ):
        box( m, e - 40, e + 40, n - 40, n + 40, G, G + 60, { "default": "oa_steel", "+z": "oa_grating" }, METAL )
    box( m, h1 - 100, h1 + 20, 960, 1020, G, G + 100, { "default": "oa_wall_dark", "+z": "oa_wall_dark" }, STONE )
    # OPS: the satellite control box on the roof, its name and the big window on its south face, lit inside, a flag.
    o0, o1, on0, on1 = OPS
    wall( m, "e", o0, o1, on0, on0 + 16, G, OPS_TOP, [ ( 820, 968, 432, 268 ) ] )
    wall( m, "e", o0, o1, on1 - 16, on1, G, OPS_TOP )
    wall( m, "n", on0, on1, o0, o0 + 16, G, OPS_TOP, [ ( 752, 812, G + 96 ) ] )
    wall( m, "n", on0, on1, o1 - 16, o1, G, OPS_TOP )
    slab( m, o0, o1, on0, on1, OPS_TOP - 14, OPS_TOP, top="oa_wall_dark", side="oa_wall", under="oa_interior_dark" )
    box( m, o0 - 4, o1 + 4, on0 - 4, on1 + 4, OPS_TOP, OPS_TOP + 18, { "default": "oa_wall_dark", "+z": None, "-z": None } )
    P.railing( m, [ ( o0 + 4, on0 + 4 ), ( o1 - 4, on0 + 4 ), ( o1 - 4, on1 - 4 ) ], OPS_TOP + 18, "oa_yellow", height=36, post_every=50 )
    OP.letters( m, "ops", ( 752, on0 - 0.6, 384 ), v( 1, 0, 0 ), 42, "light" )
    OP.letters( m, "satellite_control", ( 752, on0 - 0.6, 332 ), v( 1, 0, 0 ), 38, "light" )
    slab( m, o0 + 16, o1 - 16, on0 + 16, on1 - 16, G, G + 0.2, top="oa_interior_floor", side=None, under=None, surface=None )
    box( m, o0 + 16, o1 - 16, on1 - 17, on1 - 16, G, OPS_TOP - 14, "oa_interior" )
    box( m, o1 - 17, o1 - 16, on0 + 16, on1 - 16, G, OPS_TOP - 14, "oa_interior" )
    OP.plate( m, "whiteboard", ( 900, on1 - 17.5, G + 130 ), v( 1, 0, 0 ), 60, off=0.0 )
    OP.plate( m, "poster_launch", ( 800, on1 - 17.5, G + 140 ), v( 1, 0, 0 ), 54, off=0.0 )
    OP.plate( m, "poster_mission", ( 760, on1 - 17.5, G + 140 ), v( 1, 0, 0 ), 54, off=0.0 )
    OP.screen( m, "orbit", ( o1 - 17.5, 782, G + 130 ), v( 0, -1, 0 ), 26, off=0.0 )
    for k, e in enumerate( ( 800, 900 ) ):
        OP.desk( m, ( e, 796 ), ( 1, 0 ), 84, 30, 30, 2, ( "telemetry", "status" ) )
        OP.chair( m, ( e, 768 ), ( 0, 1 ) )
    P.ceiling_light( m, "OPS lamp 1", ( 820, 790, OPS_TOP - 20 ), ( 1, 0 ), "warm", 560 )
    P.ceiling_light( m, "OPS lamp 2", ( 900, 770, OPS_TOP - 20 ), ( 1, 0 ), "warm", 480 )
    for e in np.arange( 820, 970, 37 ):
        box( m, e - 1.5, e + 1.5, on0 + 6, on0 + 9, 268, 432, "oa_glass_frame" )
    box( m, 820, 968, on0 + 6, on0 + 9, 349, 352, "oa_glass_frame" )
    glass.polygon( "rw_glass", [ v( 820, on0 + 8, 268 ), v( 968, on0 + 8, 268 ), v( 968, on0 + 8, 432 ), v( 820, on0 + 8, 432 ) ], normal=v( 0, -1, 0 ) )
    glass.polygon( "rw_glass", [ v( 968, on0 + 8, 268 ), v( 820, on0 + 8, 268 ), v( 820, on0 + 8, 432 ), v( 968, on0 + 8, 432 ) ], normal=v( 0, 1, 0 ) )
    glass.collision_box( ( 820, on0 + 6, 268 ), ( 968, on0 + 10, 432 ), "glass" )
    OP.flag( m, ( 866, on0 + 20, OPS_TOP + 18 ), 230, ( 0, -1 ), ( 200.0, 120.0 ) )
    P.wall_light( m, "OPS door lamp", ( o0, 782, G + 110 ), ( -1, 0 ), "warm", 300 )


# ---------------------------------------------------------------------------------------------------------------------
# The yard's props (placed from where the picture has them)

def yard_props( m ):
    import lowtide_container as LCN
    import lowtide_forklift as LF
    # Cases, under a tarp and bare, and red crates, where the reference shows them.
    OP.case_block( m, ( -195, 398 ), ( 1, -0.645 ), 3, 2, ( 49, 29, 23 ), 2, "rv_olive", tarp=True, seed=1, pallets=True,
                   tarp_paint="oa_tarp_grey" )
    OP.case_block( m, ( 115, 630 ), ( 1, 0 ), 2, 2, ( 52, 32, 30 ), 2, "rv_case", seed=2, pallets=True )
    OP.case_block( m, ( 370, 545 ), ( 0, 1 ), 2, 1, ( 52, 32, 30 ), 2, "rv_olive", seed=3, pallets=True )
    OP.case_block( m, ( -147, 545 ), ( 1, 0 ), 2, 1, ( 40, 30, 46 ), 1, "rv_olive", seed=4, pallets=True )
    OP.case_block( m, ( 345, 405 ), ( 0, 1 ), 1, 1, ( 52, 32, 30 ), 2, "rv_olive", seed=5, pallets=True )
    OP.case_block( m, ( 95, 180 ), ( 1, 0.15 ), 2, 1, ( 60, 38, 34 ), 2, "rv_olive", seed=6, pallets=True )
    OP.case_block( m, ( -195, -30 ), ( 1, 0.0 ), 3, 1, ( 52, 32, 30 ), 1, "rv_case", seed=7, pallets=True )
    OP.case_block( m, ( 30, 770 ), ( 1, 0 ), 2, 1, ( 48, 30, 28 ), 1, "rv_olive", seed=8, pallets=True )
    OP.case_block( m, ( 230, 760 ), ( 1, 0.1 ), 1, 2, ( 48, 30, 28 ), 1, "rv_case", seed=9, pallets=True )
    OP.red_crate( m, ( 83, 451 ), ( 0.12, 1 ), ( 40, 30, 46 ) )
    OP.red_crate( m, ( 117, 449 ), ( 0.05, 1 ), ( 40, 30, 46 ) )
    OP.case_block( m, ( -17, 581 ), ( 1, 0 ), 1, 1, ( 70, 40, 46 ), 1, "rv_olive", seed=10, pallets=True )
    OP.red_crate( m, ( 400, 690 ), ( 0, 1 ), ( 44, 34, 40 ) )
    OP.red_crate( m, ( 300, 520 ), ( 1, 0 ), ( 36, 28, 32 ) )
    # The red container on the yard's west side.
    LCN.build( m, -185, 165, 0, "10", "e", "rw_container_red", door_end=-1 )
    # The forklift by B3's corner, the tarped pile, a lamp post.
    LF.build( m, 240, 230, "-e" )
    OP.tarp_pile( m, ( 195, 0 ), 110, 80, 78, ( 1, 0.2 ), seed=11 )
    P.cylinder( m, ( 181, 171 ), 2.4, 0, 96, "oa_steel", 8 )
    box( m, 176, 186, 160, 172, 92, 100, "oa_dark" )
    card( m, "oa_lamp_warm", [ v( 177, 161, 91.9 ), v( 185, 161, 91.9 ), v( 185, 171, 91.9 ), v( 177, 171, 91.9 ) ], -UP )
    P.LIGHTS.append( ( "Yard post lamp", ( 181, 166, 84 ), OP.WARM, 420, False ) )
    # Floor markings: bay lines, lanes, arrows.
    for a, b in ( ( ( -230, -100 ), ( -230, 640 ) ), ( ( 470, -60 ), ( 470, 660 ) ), ( ( -230, 640 ), ( 470, 640 ) ), ( ( -60, 120 ), ( 300, 120 ) ),
                  ( ( -40, 420 ), ( 160, 420 ) ), ( ( 160, 420 ), ( 160, 560 ) ),
                  ( ( -150, 820 ), ( 160, 820 ) ), ( ( 190, 880 ), ( 190, 300 ) ), ( ( 510, 880 ), ( 510, 300 ) ) ):
        floor_line( m, a, b, 7.0 )
    for a, b in ( ( ( 300, -100 ), ( 300, 260 ) ), ( ( -230, 300 ), ( 160, 300 ) ), ( ( 20, 640 ), ( 20, 880 ) ), ( ( -100, -200 ), ( 220, -200 ) ),
                  ( ( 560, 300 ), ( 560, 880 ) ), ( ( -230, 120 ), ( -60, 120 ) ) ):
        floor_line( m, a, b, 7.0 )
    # Hatched no-park zones: diagonal stripes in a bordered box.
    for e0, n0, e1, n1 in ( ( 200, 700, 330, 860 ), ( -200, 440, -60, 600 ) ):
        for a, b in ( ( ( e0, n0 ), ( e1, n0 ) ), ( ( e1, n0 ), ( e1, n1 ) ), ( ( e1, n1 ), ( e0, n1 ) ), ( ( e0, n1 ), ( e0, n0 ) ) ):
            floor_line( m, a, b, 5.0 )
        for k in range( 1, int( ( e1 - e0 + n1 - n0 ) / 40 ) ):
            t = k * 40.0
            p0 = ( e0 + min( t, e1 - e0 ), n0 + max( 0.0, t - ( e1 - e0 ) ) )
            p1 = ( e0 + max( 0.0, t - ( n1 - n0 ) ), n0 + min( t, n1 - n0 ) )
            floor_line( m, p0, p1, 4.0 )
    # The apron's diagonal lane lattice (the picture's long yellow diamonds), at z 0.11 under the bay lines.
    def diagonal( c, d, e0=-230.0, e1=470.0, n0=-80.0, n1=640.0 ):
        span = [ -1e9, 1e9 ]
        for o, k, lo, hi in ( ( c, 0, e0, e1 ), ( 0.0, 1, n0, n1 ) ):
            t0, t1 = sorted( ( ( lo - o ) / d[k], ( hi - o ) / d[k] ) )
            span = [ max( span[0], t0 ), min( span[1], t1 ) ]
        if span[1] - span[0] < 60:
            return None
        return ( ( c + d[0] * span[0], d[1] * span[0] ), ( c + d[0] * span[1], d[1] * span[1] ) )
    for bearing, step, phase in ( ( 32.0, 150.0, -122.0 ), ( 118.0, 260.0, 390.0 ) ):
        d = ( math.sin( math.radians( bearing ) ), math.cos( math.radians( bearing ) ) )
        pitch = step / abs( d[1] )
        for k in range( -10, 11 ):
            seg = diagonal( phase + k * pitch, d )
            if seg:
                floor_line( m, seg[0], seg[1], 6.0, z=0.11 )
    for at, hd in ( ( ( 330, 230 ), ( 0, 1 ) ), ( ( 330, 400 ), ( 0, 1 ) ), ( ( 30, 330 ), ( 1, 0 ) ), ( ( -110, 700 ), ( -1, 0 ) ) ):
        arrow_mark( m, at, hd, 46 )
    # Bollards by the tunnel's mouth and B3's corner.
    for e, n in ( ( 175, 880 ), ( 525, 880 ), ( 236, 40 ), ( 274, 150 ) ):
        P.bollard( m, e, n )
    # Floodlights: one on the overlook's east corner, one on the west block's roof.
    OP.floodlight_pole( m, "Yard flood south", ( 860, -580, OVER_Z ), 120, ( -0.7, 1 ), heads=2, radius=1100, shadows=True )


def spawn_courts( m ):
    """ The west court (Red Team) behind Launch Control and the east court (Blue Team) behind Fuel Processing, the south
    lane round the overlook: cover, lamps, containers. """
    import lowtide_container as LCN
    LCN.build( m, -1180, -150, 0, "20", "n", "rw_container_blue", door_end=1 )
    LCN.build( m, -1080, 420, 0, "20", "e", "rw_container_grey", door_end=-1 )
    LCN.build( m, 1300, 300, 0, "20", "n", "rw_container_blue", door_end=1 )
    LCN.build( m, 1250, -500, 0, "20", "e", "rw_container_red", door_end=1 )
    for k, ( e, n ) in enumerate( ( ( -1260, -900 ), ( -980, -960 ), ( -1200, 580 ), ( 1250, 1250 ), ( 1340, -220 ), ( 300, -1080 ), ( -200, -1080 ) ) ):
        OP.case_block( m, ( e, n ), ( 1, 0.05 * k ), 2, 1, ( 52, 32, 30 ), 1 + k % 2, "rv_olive" if k % 2 else "rv_case", seed=600 + k )
    for k, ( e, n, f ) in enumerate( ( ( -1350, -400, ( 1, 0 ) ), ( -1350, 300, ( 1, 0 ) ), ( 1450, 700, ( -1, 0 ) ), ( 1450, 0, ( -1, 0 ) ),
                                       ( 0, -1150, ( 0, 1 ) ), ( 700, -1150, ( 0, 1 ) ) ) ):
        P.wall_light( m, f"Court lamp {k}", ( e, n, 200 ), f, "warm", 520 )
    for n in ( 340, 560 ):
        P.door( m, ( WEST[0], n, 0 ), ( 0, -1, 0 ), 70, 96, "rv_door", window=False, double=False )
    OP.plate( m, "exit", ( -900 - 0.4, 110, 120 ), v( 0, -1, 0 ), 10 )


# ---------------------------------------------------------------------------------------------------------------------
# The pad: what's past the deck's north edge (drawn only)

ROCKET = ( 694.0, 2800.0 )
ROCKET_Z = 240.0
ROCKET_H = 1300.0
ROCKET_R = 66.0


def pad( m ):
    """ The launch pad and the apron between it and the deck, after the picture: the rocket on its mount between the two
    service towers, the lightning masts, the floodlight towers and the pylon west of it, tanks and machinery. """
    rng = np.random.default_rng( 77 )
    box( m, -2000, 2600, 1400, 3600, -24, 0, { "default": None, "+z": "oa_yard" } )
    # The pad: a raised concrete mound with a flame trench running south, the mount on it.
    rc = ROCKET
    box( m, rc[0] - 420, rc[0] + 420, rc[1] - 380, rc[1] + 420, 0, 120, { "default": "oa_wall_dark", "+z": "oa_deck" } )
    box( m, rc[0] - 70, rc[0] + 70, rc[1] - 700, rc[1] - 380, 0, 60, { "default": "oa_wall_dark", "+z": "oa_wall_dark" } )
    OP.launch_mount( m, rc, ROCKET_Z - 10, 420, 420, 200, "Mount" )
    OP.rocket( m, ( rc[0], rc[1], ROCKET_Z ), ROCKET_H, ROCKET_R, 32, ( -0.25, -1 ) )
    # The service towers: the orange one on the west, a taller and wider one on the east with a striped top.
    # Their steel is lit gold in the picture: orange paint (oa_gantry), many work lamps casting light on it, and work
    # platforms stepping out of the faces (most on the outer sides and the south, towards the yard).
    OP.service_tower( m, ( rc[0] - 190, rc[1] + 30, 120 ), 190, 190, 1320, 72, "oa_gantry", "West tower", 12, arms_to=rc,
                      ledges=( ( 3, 2, 60, 0.9 ), ( 4, 0, 40, 0.6 ), ( 7, 2, 44, 0.7 ), ( 9, 0, 36, 0.5 ), ( 12, 2, 50, 0.8 ), ( 15, 0, 40, 0.6 ) ) )
    OP.service_tower( m, ( rc[0] + 210, rc[1] + 60, 120 ), 260, 230, 1290, 72, "oa_gantry", "East tower", 14, arms_to=rc,
                      cap=lambda mm, top: OP.striped_tank( mm, ( top[0] + 40, top[1] + 30, top[2] ), 32, 120 ),
                      ledges=( ( 2, 3, 70, 0.8 ), ( 5, 0, 44, 0.5 ), ( 6, 3, 50, 0.6 ), ( 10, 0, 40, 0.6 ), ( 11, 3, 60, 0.7 ), ( 14, 3, 44, 0.5 ) ) )
    P.cylinder( m, ( rc[0] - 70, rc[1] + 330 ), 60, 120, 1500, "oa_steel", 16 )
    P.lathe( m, ( rc[0] - 70, rc[1] + 330 ), [ ( 60, 1500 ), ( 40, 1530 ), ( 0, 1545 ) ], "oa_steel", 16 )
    # Lightning masts round the pad.
    for k, ( e, n, h ) in enumerate( ( ( 304, 2620, 1100 ), ( 1080, 3150, 1250 ) ) ):
        top = OP.lattice_tower( m, ( e, n, 0 ), h, 70, 24, "oa_steel", platforms=( h * 0.55, ), name=f"Lightning mast {k}", beacon=False )
        P.cylinder( m, ( top[0], top[1] ), 2.0, top[2], top[2] + 120, "oa_steel", 6 )
    # The tall lattice tower behind the deck's west end, the floodlight towers, the pylon with its banner.
    OP.lattice_tower( m, ( -470, 1520, 0 ), 1320, 130, 44, "oa_steel", platforms=( 640, 1000 ), name="Tall mast" )
    OP.floodlight_pole( m, "Pad flood 1", ( -300, 1620, 0 ), 600, ( 0.3, -1 ), heads=2, radius=2200 )
    OP.floodlight_pole( m, "Pad flood 2", ( -70, 1990, 0 ), 470, ( 0.2, -1 ), heads=2, radius=2000 )
    OP.floodlight_pole( m, "Pad flood 3", ( 1500, 2300, 0 ), 560, ( -0.6, 1 ), heads=4, radius=2200 )
    OP.lattice_tower( m, ( -840, 1760, 0 ), 700, 110, 40, "oa_steel", panel=70, name="Pylon", beacon=False )
    for z, w in ( ( 600, 150 ), ( 520, 190 ), ( 440, 150 ) ):
        OP.beam( m, ( -840 - w, 1760, z ), ( -840 + w, 1760, z ), 6, "oa_steel" )
        for sg in ( -1, 1 ):
            P.cylinder( m, ( -840 + sg * ( w - 6 ), 1760 ), 3, z - 26, z, "oa_dark", 6 )
    OP.banner( m, ( -1000, 1700, 460 ), ( 0.4, -1 ), 56, 110 )
    OP.lattice_tower( m, ( -1060, 1660, 0 ), 520, 80, 30, "oa_steel", platforms=( 380, ), name="West mast", beacon=False )
    # Machinery between the deck and the pad: big horizontal tanks on saddles, pipe racks, sheds, a red container, crates.
    for k, ( e, n, L ) in enumerate( ( ( 200, 1700, 420 ), ( 260, 1900, 360 ), ( -200, 2250, 380 ) ) ):
        for x in ( -L / 2 + 30, L / 2 - 30 ):
            box( m, e + x - 16, e + x + 16, n - 50, n + 50, 0, 60, "oa_wall_dark" )
        OP.banded_pipe( m, [ ( e - L / 2, n, 110 ), ( e + L / 2, n, 110 ) ], 56, "oa_white_steel", "oa_red", every=L / 2 )
    for n in np.arange( 1500, 2700, 200 ):
        for e in ( -100, 420 ):
            OP.beam( m, ( e, n, 0 ), ( e, n, 180 ), 8, "oa_steel" )
        OP.beam( m, ( -100, n, 180 ), ( 420, n, 180 ), 8, "oa_steel" )
    for k, r_ in enumerate( ( 14.0, 10.0, 10.0, 7.0 ) ):
        P.pipe( m, [ ( -100, 1500, 190 + k * 26 ), ( 420, 1500, 190 + k * 26 ) ], r_, "rv_pipe", 10 )
        P.pipe( m, [ ( 160 + k * 30, 1500, 190 ), ( 160 + k * 30, 2600, 190 ), ( rc[0] - 300, 2600, 190 ) ], r_, "rv_pipe", 10 )
    import lowtide_container as LCN
    LCN.build( m, -60, 1640, 0, "20", "e", "rw_container_red", door_end=1 )
    LCN.build( m, 1000, 1700, 0, "20", "n", "rw_container_grey", door_end=1 )
    for k, ( e, n ) in enumerate( ( ( -600, 1900 ), ( 1300, 2000 ), ( 520, 2050 ), ( -400, 2600 ) ) ):
        box( m, e - 120, e + 120, n - 80, n + 80, 0, 150, { "default": "oa_wall", "+z": "oa_wall_dark" } )
        box( m, e - 100, e - 40, n - 81, n - 80, 20, 110, "oa_window_lit" if k % 2 else "oa_door" )
        P.wall_light( m, f"Pad shed lamp {k}", ( e, n - 80, 130 ), ( 0, -1 ), "warm", 400, light=( k < 2 ) )
    for k in range( 14 ):
        e, n = rng.uniform( -800, 1700 ), rng.uniform( 1500, 3300 )
        if abs( e - rc[0] ) < 520 and abs( n - rc[1] ) < 520:
            continue
        OP.case_block( m, ( e, n ), ( 1, rng.normal( 0, 0.2 ) ), int( rng.integers( 1, 4 ) ), 1, ( 52, 32, 30 ), int( rng.integers( 1, 3 ) ),
                       "rv_olive" if k % 2 else "rv_case", surface=None, seed=700 + k )
    box( m, -2000, 2600, 3300, 3460, 0, 0.3, { "default": None, "+z": "oa_asphalt" } )
    import orion_backdrop as OB
    for k, ( e0, e1, n0, n1, h ) in enumerate( ( ( 930, 1440, 2360, 2520, 330 ), ( -990, -760, 1640, 1780, 280 ), ( -740, -520, 1700, 1820, 240 ) ) ):
        box( m, e0, e1, n0, n1, 0, h, { "default": "oa_wall", "+z": "oa_wall_dark" } )
        box( m, e0 - 4, e1 + 4, n0 - 4, n1 + 4, h, h + 14, "oa_wall_dark" )
        OB.window_grid( m, ( ( e0 + e1 ) / 2, n0, h * 0.52 ), ( 1, 0, 0 ), ( e1 - e0 ) * 0.86, h * 0.72, max( 1, int( h / 110 ) ),
                        max( 2, int( ( e1 - e0 ) / 70 ) ), rng, lit=0.55 )
        P.wall_light( m, f"Pad block lamp {k}", ( ( e0 + e1 ) / 2, n0, h - 30 ), ( 0, -1 ), "warm", 600, light=( k == 0 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Gameplay spots

RED_SPAWNS = [ ( -1250, -700, 0 ), ( -1150, -700, 0 ), ( -1050, -700, 0 ), ( -1250, -560, 0 ), ( -1150, -560, 0 ), ( -1050, -560, 0 ),
               ( -1250, -420, 0 ), ( -1150, -420, 0 ), ( -1050, -420, 0 ), ( -1250, -280, 0 ), ( -1080, -300, 0 ), ( -1100, -860, 0 ) ]
BLUE_SPAWNS = [ ( 1230, 560, 0 ), ( 1330, 560, 0 ), ( 1230, 680, 0 ), ( 1330, 680, 0 ), ( 1230, 800, 0 ), ( 1330, 800, 0 ),
                ( 1230, 920, 0 ), ( 1330, 920, 0 ), ( 1230, 1040, 0 ), ( 1330, 1040, 0 ), ( 1380, 460, 0 ), ( 1380, 1160, 0 ) ]
DM_SPAWNS = [
    ( -40, 40, 0 ), ( 300, 350, 0 ), ( -50, 650, 0 ), ( 400, 820, 0 ), ( 100, -300, 0 ), ( 220, -250, 0 ), ( -150, -400, 0 ),
    ( 350, 1100, 0 ), ( 300, 1360, 0 ), ( -260, 1150, G ), ( 200, 1200, G ), ( -450, 980, G ), ( 450, 1250, G ),
    ( -260, 0, TERRACE_Z ), ( -300, 500, WALK_Z ), ( -420, 800, WALK_Z ), ( -300, 800, 0 ), ( -450, 760, 0 ),
    ( 650, 420, 0 ), ( 1000, 650, 0 ), ( 760, 960, 0 ), ( 760, 600, G ), ( 1050, 1250, G ), ( 840, 900, G ),
    ( 0, -800, OVER_Z ), ( 400, -700, OVER_Z ), ( -700, -100, OVER_Z ), ( -450, 100, OVER_Z ), ( -700, 100, TERRACE_Z ),
    ( -1100, 100, 0 ), ( 1300, -100, 0 ), ( 0, -1080, 0 ), ( 800, -300, 0 ), ( -1000, -1000, 0 ),
]
BOMB_SITES = [ ( "bombsite_a", "A", -330, 160, 1000, 1360, G ), ( "bombsite_b", "B", -200, 260, 150, 560, 0 ) ]
BUY_ZONE = ( 1180, 1430, 450, 1300, 0, 200 )          # Blue's
RED_BUY_ZONE = ( -1330, -940, -800, -200, 0, 200 )
RETAKES = {
    "a": {
        "planter": [ ( -150, 1150, G ) ],
        "defender": [ ( -450, 1200, G ), ( 120, 1300, G ), ( 380, 1340, 0 ), ( -470, 980, G ) ],
        "attacker": [ ( 860, 650, 0 ), ( 1300, 900, 0 ), ( 1380, 140, 0 ), ( 200, -1080, 0 ), ( 100, -800, 0 ) ],
    },
    "b": {
        "planter": [ ( 50, 330, 0 ) ],
        "defender": [ ( 330, 700, 0 ), ( -120, 600, 0 ), ( 330, 300, 0 ), ( -40, 640, 0 ) ],
        "attacker": [ ( 860, 650, 0 ), ( 1300, 900, 0 ), ( 100, -800, 0 ), ( -1100, 120, 0 ), ( -600, 100, TERRACE_Z ) ],
    },
}
DOMINATION = [ ( "A", ( -250, 60, TERRACE_Z ) ), ( "B", ( 60, 360, 0 ) ), ( "C", ( 860, 650, 0 ) ) ]
HOT_ZONES = [ ( "Cargo Yard", ( 80, 350, 0 ) ), ( "Launch Deck", ( -100, 1150, G ) ), ( "Service Tunnel", ( 350, 1100, 0 ) ),
              ( "Fuel Hall", ( 860, 650, 0 ) ), ( "Terrace", ( -250, 60, TERRACE_Z ) ), ( "Undercroft", ( -330, 800, 0 ) ) ]
CASH_POINTS = [
    ( "Yard", ( 60, 360, 0 ), ( -160, 1240, G ) ),
    ( "Deck", ( -200, 1150, G ), ( 860, 650, 0 ) ),
    ( "Fuel", ( 860, 650, 0 ), ( -250, 60, TERRACE_Z ) ),
]


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


def callouts():
    return [
        ( "Cargo Yard", -230, 560, -540, 700, -10, 220 ),
        ( "ORION", -75, 160, 600, 700, -10, 220 ),
        ( "Service Tunnel", 180, 520, 900, 1250, -10, 180 ),
        ( "Red Room", 180, 520, 1250, 1400, -10, 180 ),
        ( "Launch Deck", -560, 600, 900, 1400, 200, 400 ),
        ( "Undercroft", -560, -75, 700, 900, -10, 130 ),
        ( "Mezzanine", -560, -75, 700, 900, 130, 230 ),
        ( "West Walkway", -342, -258, 330, 700, 120, 230 ),
        ( "Terrace", -316, -120, -260, 330, 40, 150 ),
        ( "Launch Control", -900, -316, -10, 200, 40, 330 ),
        ( "Control Room", -600, -374, -10, 200, 330, 520 ),
        ( "LC Balcony", *LC_BALCONY, 320, 450 ),
        ( "Overlook", -560, 900, -1000, -540, 320, 460 ),
        ( "Overlook Hall", -560, 900, -1000, -540, -10, 320 ),
        ( "B3", 243, 560, 157, 700, -10, 220 ),
        ( "Fuel Lines", 243, 900, -540, 57, -10, 220 ),
        ( "Fuel Hall", 600, 1110, 300, 1000, -10, 210 ),
        ( "East Roof", 560, 1150, 157, 1400, 220, 400 ),
        ( "OPS", *OPS, 230, 470 ),
        ( "West Block", -900, -360, 200, 700, -10, 200 ),
        ( "Red Court", -1350, -900, -1150, 700, -10, 300 ),
        ( "Blue Court", 1150, 1450, 157, 1420, -10, 300 ),
        ( "South Lane", -560, 1450, -1150, -1000, -10, 300 ),
    ]


# ---------------------------------------------------------------------------------------------------------------------
# The radar picture

MINIMAP_CENTRE = ( 50.0, 135.0 )
MINIMAP_SIZE = 3200.0
MINIMAP_PIXELS = 1024


def write_minimap( models, path ):
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
        elif 120 <= z1 <= 345 and z1 - z0 < 70:
            draws["upper"].polygon( screen, fill=255 )
        elif z0 < 72 and z1 > 18:
            draws["low" if z1 < 100 else "tall"].polygon( screen, fill=255 )
    walk, low, tall, upper = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "low", "tall", "upper" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    E, N = np.meshgrid( cols, rows )
    inside = ( E > PLAY[0] ) & ( E < PLAY[1] ) & ( N > PLAY[2] ) & ( N < PLAY[3] )
    walk &= inside
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[low & inside] = ( 64, 68, 74, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    image[upper & inside] = ( 128, 132, 138, 235 )
    shown = ( walk | ( low & inside ) | ( upper & inside ) ) & ~tall
    edge = np.zeros_like( shown )
    edge[1:, :] |= ~shown[:-1, :]
    edge[:-1, :] |= ~shown[1:, :]
    edge[:, 1:] |= ~shown[:, :-1]
    edge[:, :-1] |= ~shown[:, 1:]
    image[shown & edge] = ( 226, 233, 240, 255 )
    path.parent.mkdir( parents=True, exist_ok=True )
    Image.fromarray( image, "RGBA" ).save( path )
    print( f"wrote {path}" )


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


def spawn_object( name, key, position, team, tags="", facing=( 50, 400 ) ):
    """ A TeamSpawnPoint facing the yard. """
    yaw = K.plan_yaw( ( facing[0] - position[0], facing[1] - position[1] ) )
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
    ( "orion_ground", "Ground", True, True ), ( "orion_overlook", "Overlook", True, True ),
    ( "orion_launch_control", "Launch Control", True, True ), ( "orion_launch_deck", "Launch Deck", True, True ),
    ( "orion_fuel", "Fuel Processing", True, True ), ( "orion_props", "Yard Props", True, True ),
    ( "orion_courts", "Spawn Courts", True, True ), ( "orion_glass", "Glass", True, False ),
    ( "orion_pad", "Pad", False, True ), ( "orion_vista", "Vista", False, False ),
]


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return { **K.game_object( ids, name, key, components=components ), "Flags": 32768 }


def look_object():
    """ Golden hour after rain: ambient occlusion, a warm grade, a light vignette, bloom for the low sun, the lamps and the
    wet glare. Screen-space reflections are off: the engine's SSR traces a lobe wider than the material's and keeps
    hits on the floor itself, so it swapped much of the near yard's sky for the slabs' own dark colour (and
    RoughnessCutoff can't be set). The wet-floor probes carry the reflections, stepped down where the floor's mirror
    image meets buildings (WET_FLOORS). """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=1.0, Radius=220,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=5300,
                     BlendFactor=0.5, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.ColorAdjustments", "look/adjust", Brightness=1.0, Contrast=1.0, HueRotate=0, Saturation=1.1 ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.28, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Bloom", "look/bloom", **{ "__version": 1 }, Mode="Additive", Strength=0.36, Threshold=1.05,
                     Tint="1,0.95,0.88,1" ),
        K.component( ids, "Sandbox.ScreenSpaceReflections", "look/ssr", **{ "__enabled": False } ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0.0, ExposureMethod="RGB", MinimumExposure=1.0, MaximumExposure=1.2,
                     Mode="ACES", Rate=1 ),
    ] )


HAZE = [ ( "Yard Haze", ( PLAY[0], PLAY[1], PLAY[2], PLAY[3], 0, 900 ), 0.015, "1,0.88,0.74,1" ),
         ( "Tunnel Haze", ( TUNNEL[0], TUNNEL[1], TUNNEL[2], RED_ROOM[3], 0, TUNNEL_TOP ), 0.25, "1,0.7,0.6,1" ) ]


def haze_object( name, box_, strength, colour ):
    e0, e1, n0, n1, z0, z1 = box_
    at = K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) )
    half = ( ( n1 - n0 ) / 2, ( e1 - e0 ) / 2, ( z1 - z0 ) / 2 )
    key = f"haze/{name}"
    return K.game_object( ids, name, key, at, components=[
        K.component( ids, "Sandbox.VolumetricFogVolume", f"{key}/volume", Bounds={ "Mins": K.vec( tuple( -h for h in half ) ), "Maxs": K.vec( half ) },
                     FalloffExponent=1, Strength=strength, Color=colour ) ] )


# Steam: the picture's vents and the pad's cryogenic boil-off. ( position, rate, rise, size )
STEAM = [ ( ( 330, 2600, 100 ), 14, 80, 3.4 ), ( ( 250, 2700, 160 ), 10, 60, 3.0 ), ( ( 420, 2700, 140 ), 12, 70, 2.6 ), ( ( 520, 2640, 240 ), 10, 60, 2.6 ), ( ( 320, 2760, 120 ), 10, 55, 2.4 ),
          ( ( 470, 2600, 130 ), 8, 50, 1.6 ), ( ( 900, 2640, 260 ), 6, 45, 1.4 ), ( ( 820, 2560, 130 ), 6, 45, 1.4 ),
          ( ( -100, 1380, G + 28 ), 4, 30, 0.7 ), ( ( 260, 1380, G + 28 ), 4, 30, 0.7 ), ( ( 1060, 1100, G + 60 ), 3, 26, 0.6 ) ]


def steam_objects():
    """ Copies of the gun smoke prefab's particle effect, slowed and enlarged into rising steam. """
    source = json.loads( ( ASSETS / "prefabs/weapon_effects/gun_smoke.prefab" ).read_text( encoding="utf-8" ) )
    template = source["RootObject"]["Children"][0]
    out = []
    for k, ( pos, rate, rise, size ) in enumerate( STEAM ):
        node = copy.deepcopy( template )
        key = f"steam/{k}"
        node["__guid"] = ids( key )
        node["Name"] = f"Steam {k + 1}"
        node["Position"] = K.vec( K.to_world( pos ) )
        node["NetworkMode"] = 2
        for i, c in enumerate( node["Components"] ):
            c["__guid"] = ids( f"{key}/c{i}" )
            t = c["__type"]
            if t == "Sandbox.ParticleEffect":
                c["Lifetime"] = 6
                c["MaxParticles"] = 48
                c["PreWarm"] = 4
                c["Damping"] = 0.2
                c["Force"] = False
                c["ConstantMovement"] = { "X": 6, "Y": 10, "Z": rise }
                c["Tint"] = "1,0.97,0.93,1"
                c["Brightness"] = 2.6
                c["Scale"] = { "Type": "Curve", "Evaluation": "Life", "CurveA": [
                    { "x": 0, "y": 22 * size, "in": 0, "out": 0, "mode": "Linear" },
                    { "x": 1, "y": 160 * size, "in": 0, "out": 0, "mode": "Linear" } ] }
                if isinstance( c.get( "Alpha" ), dict ) and len( c["Alpha"].get( "CurveA", [] ) ) > 2:
                    c["Alpha"]["CurveA"][1]["y"] = 0.62
                    c["Alpha"]["CurveA"][2]["y"] = 0.3
            elif t == "Sandbox.ParticleBoxEmitter":
                c["Burst"] = 0
                c["DestroyOnEnd"] = False
                c["Duration"] = 10
                c["Loop"] = True
                c["Rate"] = rate
                c["Size"] = "24,24,10"
            elif t == "Sandbox.ParticleSpriteRenderer":
                c["DepthFeather"] = 30
                c["FogStrength"] = 1
                c["Lighting"] = False
        out.append( node )
    return out


# Reflections: the sky's own compiled cube, as a static probe over the play area (the runtime probe baker faults
# envmap_filtering_cs on this workstation's driver, so nothing is baked at load). The wet yard's puddles mirror the sky
# through it. Screen-space reflections are off (look_object), so where a wet floor's mirror image meets the ORION
# block, the deck front or the tunnel rather than sky, its probe is weaker (WET_FLOORS).
REFLECTION_TEXTURE = "lighting/orion/reflection_sky_v3.vtex"
# The wet floors' own cube: the sky with the low sun's glitter as a band (Tools/orion_sky.py --wet, WET_BAND), so the
# puddles and the wet film show streaks of warm light towards the sun's side, as the picture's floors do.
WET_TEXTURE = None


def install_reflection_texture():
    """ Copies the editor's compiled sky cube (materials/orion/sky/oa_sky_exr_*.generated.vtex_c) to a path named after
    its content (lighting/orion/reflection_sky_<hash>.vtex_c), so a running editor loads a new sky's cube rather than
    the one it has cached under an old name, and points the probes at it; the same for the wet floors' cube
    (oa_sky_wet_exr_*, lighting/orion/reflection_wet_<hash>.vtex_c). Older copies are removed. Returns whether there was
    a sky cube to copy. """
    global REFLECTION_TEXTURE, WET_TEXTURE
    import hashlib

    def install( pattern, prefix ):
        cubes = sorted( ( ASSETS / "materials/orion/sky" ).glob( pattern ), key=lambda p: p.stat().st_mtime )
        if not cubes:
            return None
        data = cubes[-1].read_bytes()
        resource = f"lighting/orion/{prefix}_{hashlib.sha1( data ).hexdigest()[:8]}.vtex"
        target = ASSETS / f"{resource}_c"
        target.parent.mkdir( parents=True, exist_ok=True )
        if not target.exists():
            target.write_bytes( data )
            print( f"copied {cubes[-1].name} to {target.relative_to( K.ROOT )}" )
        for old in target.parent.glob( f"{prefix}_*.vtex_c" ):
            if old != target:
                try:
                    old.unlink()
                except OSError as error:
                    print( f"left {old.name}: {error}" )
        return resource

    sky = install( "oa_sky_exr_*.generated.vtex_c", "reflection_sky" )
    if sky is None:
        return False
    REFLECTION_TEXTURE = sky
    WET_TEXTURE = install( "oa_sky_wet_exr_*.generated.vtex_c", "reflection_wet" )
    if WET_TEXTURE is None:
        print( "no compiled wet cube yet (materials/orion/sky/oa_sky_wet.vmat): the wet floors use the sky's" )
    return True


def probe_objects():
    centre = ( ( PLAY[0] + PLAY[1] ) / 2, ( PLAY[2] + PLAY[3] ) / 2, 200.0 )
    at = K.to_world( centre )
    lo = K.to_world( ( PLAY[1] + 200, PLAY[2] - 200, -100 ) ) - at
    hi = K.to_world( ( PLAY[0] - 200, PLAY[3] + 600, 1200 ) ) - at
    key = "probe/sky"
    return [ { **K.game_object( ids, "Sky Reflection", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", **{ "__version": 1 }, BakedTexture=None,
                     Bounds={ "Mins": K.vec( np.minimum( lo, hi ) ), "Maxs": K.vec( np.maximum( lo, hi ) ) },
                     DelayBetweenUpdates=0.1, Feathering=64, FrameInterval=5, MaxDistance=512, Mode="CustomTexture",
                     MultiBounce=False, Priority=0, Projection="Sphere", RenderExcludeTags="", Resolution="Small",
                     Texture=REFLECTION_TEXTURE, TintColor="1.8,1.8,1.8,1", UpdateStrategy="OnEnabled", ZFar=4096, ZNear=16 ) ] ),
               "NetworkMode": 2 } ] + [ yard_probe( name, b, k ) for name, b, k in WET_FLOORS ]


# The yard steps down northwards: its near part mirrors open sky over the deck; from the slab joint at n 246 its mirror
# image meets the ORION block's face, and from the joint at n 342 the deck front and the undercroft everywhere, so
# those parts get weaker copies (screen-space reflections are off). The boxes overlap 4 in at the joints so no strip
# falls back to the dim global probe. The tunnel mouth mirrors the deck front. The yard tarp's wet top mirrors the
# bright sky towards the sun.
WET_FLOORS = [ ( "Yard", ( -230.0, 560.0, -540.0, 248.0, -20.0, 3.0 ), 4.5 ), ( "Yard Mid", ( -230.0, 560.0, 244.0, 344.0, -20.0, 3.0 ), 3.8 ),
               ( "Yard Far", ( -230.0, 560.0, 340.0, 700.0, -20.0, 3.0 ), 2.5 ), ( "B3 Strip", ( 560.0, 1150.0, -540.0, 157.0, -20.0, 3.0 ), 5.5 ),
               ( "Tunnel Mouth", ( 160.0, 560.0, 700.0, 900.0, -20.0, 3.0 ), 1.3 ), ( "Terrace", ( -316.0, -120.0, -250.0, 330.0, 58.0, 67.0 ), 6 ),
               ( "Deck", ( -560.0, 600.0, 900.0, 1400.0, 220.0, 243.0 ), 3 ), ( "East Roof", ( 560.0, 1150.0, 157.0, 1400.0, 220.0, 243.0 ), 3 ),
               ( "B3 Roof", ( 243.0, 1150.0, -210.0, 157.0, 262.0, 283.0 ), 3 ), ( "Yard Tarp", ( -200.0, -30.0, 310.0, 455.0, 46.0, 57.0 ), 3.5 ) ]


def yard_probe( name="Yard", box_=WET_FLOORS[0][1], strength=18 ):
    """ A wet floor open to the sky: the same cube, much brighter, so its puddles mirror the sky as the picture's do. """
    e0, e1, n0, n1, z0, z1 = box_
    lo_p, hi_p = ( e0, n0, z0 ), ( e1, n1, z1 )
    centre = tuple( ( a + b ) / 2 for a, b in zip( lo_p, hi_p ) )
    at = K.to_world( centre )
    lo = K.to_world( ( hi_p[0], lo_p[1], lo_p[2] ) ) - at
    hi = K.to_world( ( lo_p[0], hi_p[1], hi_p[2] ) ) - at
    key = f"probe/wet/{name}"
    return { **K.game_object( ids, f"{name} Reflection", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", **{ "__version": 1 }, BakedTexture=None,
                     Bounds={ "Mins": K.vec( np.minimum( lo, hi ) ), "Maxs": K.vec( np.maximum( lo, hi ) ) },
                     DelayBetweenUpdates=0.1, Feathering=2, FrameInterval=5, MaxDistance=512, Mode="CustomTexture",
                     MultiBounce=False, Priority=1, Projection="Sphere", RenderExcludeTags="", Resolution="Small",
                     Texture=WET_TEXTURE or REFLECTION_TEXTURE, TintColor=f"{strength},{strength},{strength},1", UpdateStrategy="OnEnabled",
                     ZFar=4096, ZNear=16 ) ] ),
             "NetworkMode": 2 }


RED_CRATE_MODEL = "models/props/orion/red_crate_v2/red_crate.vmdl"
RED_CRATE_SIZE = ( 44.0, 34.0, 40.0 )     # the model's length (its y), width (its x) and height


def red_crate_object( at, heading, size ):
    """ A crate's model where red_crate put its collision box, scaled to that box's size. It has no collider of its own. """
    key = f"world/red_crate/{at[0]:g}/{at[1]:g}"
    x, y, z = size[1] / RED_CRATE_SIZE[1], size[0] / RED_CRATE_SIZE[0], size[2] / RED_CRATE_SIZE[2]
    return K.game_object( ids, "Red crate", key, K.to_world( at ), K.yaw_rotation( heading ), scale=f"{x:.5f},{y:.5f},{z:.5f}", components=[
        K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615,
                     Model=RED_CRATE_MODEL, RenderType="On", Tint="1,1,1,1" ) ] )


def write_scene( written, light_list, path ):
    world = K.game_object( ids, "Orion", "world", children=[
        model_object( title, f"world/{name}", name, collide, shadows )
        for name, title, collide, shadows in SCENE_MODELS if name in written ]
        + ( [ OCR.scene_object(), OG.scene_object() ] if "orion_launch_deck" in written else [] )
        + [ red_crate_object( *placed ) for placed in OP.RED_CRATES ] )
    light_objects = [
        { **K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled",
                         FogStrength=0.12 if radius >= 1000 else 0.5, LightColor=color, Radius=radius, Shadows=shadows ) ] ), "Flags": 32768 }
        for name, position, color, radius, shadows in light_list ]

    team_spawns = [ spawn_object( f"Red Spawn {k + 1}", f"spawn/red/{k}", p, "Terrorist" ) for k, p in enumerate( RED_SPAWNS ) ]
    team_spawns += [ spawn_object( f"Blue Spawn {k + 1}", f"spawn/blue/{k}", p, "CounterTerrorist" ) for k, p in enumerate( BLUE_SPAWNS ) ]
    dm_spawns = [ spawn_object( f"DM Spawn {k + 1}", f"spawn/dm/{k}", p, "Unassigned", tags="deathmatch" )
                  for k, p in enumerate( DM_SPAWNS ) ]
    retakes_spawns = []
    for site, roles in RETAKES.items():
        target = ( -100, 1150 ) if site == "a" else ( 50, 350 )
        for role, points in roles.items():
            team = "CounterTerrorist" if role == "attacker" else "Terrorist"
            retakes_spawns += [ spawn_object( f"{site} {role} {k + 1}", f"spawn/retakes/{site}/{role}/{k}", p, team,
                                              tags=f"retakes,{site},{role}", facing=target ) for k, p in enumerate( points ) ]

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
        zone_object( "buyzone_t", "buy/t", RED_BUY_ZONE, "1,0.18,0.2,1", "Red Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/t/zone_buy", Team="Terrorist" ) ] ),
        zone_object( "buyzone_ct", "buy/ct", BUY_ZONE, "0,0.41569,1,1", "Blue Team Buy Zone",
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
                                            tags="playerclip", components=[ box_collider( f"{key}/box", ( size[0], size[1], size[2] ), trigger=False ) ] ) )
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
                         Description="A rocket launch facility in the hills at golden hour after rain: the wet cargo yard "
                                     "between Launch Control and Fuel Processing, the service tunnel under the launch deck, and the "
                                     "rocket on its pad between its service towers.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 2500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor=SUN_COLOUR, ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.15,0.145,0.145,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="2.6,2.6,2.6,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.82", StartDistance=1400,
                         EndDistance=34000, FalloffExponent=0.85, Height=14000, VerticalFalloffExponent=1.1 ),
        ] ),
        look_object(),
        world,
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Volumetric Fog", "haze", children=[ haze_object( *h ) for h in HAZE ] ),
        K.game_object( ids, "Reflection Probes", "probes", children=probe_objects() ),
        K.game_object( ids, "Steam", "steam", children=steam_objects() ),
        mode_group( "Team Spawns", "spawns", ( "Deathmatch", "Gun Game", "Retakes" ), team_spawns, inverse=True ),
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
    from map_daylight import apply_profile
    apply_profile( scene )
    path.parent.mkdir( parents=True, exist_ok=True )
    K.write_text( path, json.dumps( scene, indent=2 ), newline=None )
    print( f"wrote {path}" )


ROOF_CLIPS = []


def roof_clips():
    """ Roofs and tops nobody should stand on, clipped up to 1500. """
    return [
        ( "LC tower", ( LC[0] - 10, LC_UPPER_E1 + 10, LC[2] - 10, LC[3] + 10, 560, 1500 ) ),
        ( "LC overhang", ( LC[0], -205, LC[2] - 120, LC[2], 540, 1500 ) ),
        ( "West block", ( WEST[0], WEST[1], WEST[2], WEST[3], WEST_TOP, 1500 ) ),
        ( "OPS", ( OPS[0] - 4, OPS[1] + 4, OPS[2] - 4, OPS[3] + 4, OPS_TOP, 1500 ) ),
        ( "Overlook plant", ( 420, 640, -900, -760, OVER_Z + 100, 1500 ) ),
        ( "Perimeter west", ( PLAY[0] - 400, PLAY[0], PLAY[2] - 400, PLAY[3], 290, 1500 ) ),
        ( "Perimeter east", ( PLAY[1], PLAY[1] + 400, PLAY[2] - 400, PLAY[3], 290, 1500 ) ),
        ( "Perimeter south", ( PLAY[0], PLAY[1], PLAY[2] - 400, PLAY[2], 290, 1500 ) ),
        ( "Deck north", ( DECK[0] - 400, EAST[1] + 400, DECK[3], DECK[3] + 400, -100, 1500 ) ),
        ( "West court north", ( PLAY[0], WEST[0], WEST[3], DECK[3], -100, 1500 ) ),
        ( "Deck west filler", ( -900, DECK[0], 700, DECK[3], G, 1500 ) ),
    ]


# ---------------------------------------------------------------------------------------------------------------------

def build():
    """ Every model by name. """
    OP.reset()
    models = { name: K.Model() for name, *_ in SCENE_MODELS }
    m = models
    m["orion_ground"].extend( ground() )
    overlook( m["orion_overlook"] )
    launch_control( m["orion_launch_control"], m["orion_glass"] )
    launch_deck( m["orion_launch_deck"] )
    fuel( m["orion_fuel"], m["orion_glass"] )
    yard_props( m["orion_props"] )
    spawn_courts( m["orion_courts"] )
    pad( m["orion_pad"] )
    try:
        import orion_backdrop as BD
        BD.build( m["orion_vista"] )
    except ImportError:
        pass
    import lowtide_container as LCN
    import lowtide_forklift as LF
    for model in models.values():
        configure( model )
        LF.configure( model )
        LCN.configure( model )
    ROOF_CLIPS[:] = roof_clips()
    return models


def preview_setup():
    """ The flat preview's colours, sun, sky and fog. """
    src = STAGE / "Assets/materials/orion"
    for paint in OT.all_paints():
        if paint in OT.PAINTED:
            PV._colours[paint] = np.array( OT.PAINTED[paint][0] ) / 255.0
            continue
        for folder in ( src, OT.OUT_DIR ):
            path = folder / f"{paint}_color.jpg"
            if path.exists():
                small = Image.open( path ).convert( "RGB" ).resize( ( 64, 32 ) )
                PV._colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
                break
    PV._colours["oa_letters_dark"] = np.array( ( 0.1, 0.1, 0.1 ) )
    PV._colours["oa_letters_light"] = np.array( ( 0.85, 0.85, 0.84 ) )
    PV._colours["oa_plates"] = np.array( ( 0.5, 0.45, 0.4 ) )
    PV._colours["oa_screens"] = np.array( ( 0.3, 0.4, 0.5 ) )
    PV.GLOWING.update( { "oa_lamp_warm", "oa_lamp_cool", "oa_lamp_flood", "oa_beacon", "oa_window_lit", "oa_screens", "oa_red_glow" } )
    p, y = math.radians( SUN_PITCH ), math.radians( SUN_YAW )
    world = np.array( ( math.cos( p ) * math.cos( y ), math.cos( p ) * math.sin( y ), -math.sin( p ) ) )
    PV.SUN = -np.array( ( -world[1], world[0], world[2] ) )
    PV.SKY = ( np.array( ( 0.86, 0.80, 0.74 ) ), np.array( ( 0.40, 0.52, 0.72 ) ) )
    PV.FOG = np.array( ( 0.86, 0.80, 0.74 ) )


def ref_target( eye=REF_EYE, pitch=REF_PITCH, yaw=0.0, dist=1000.0 ):
    p, y = math.radians( pitch ), math.radians( yaw )
    return ( eye[0] + dist * math.cos( p ) * math.sin( y ), eye[1] + dist * math.cos( p ) * math.cos( y ), eye[2] + dist * math.sin( p ) )


VIEWS = ( ( "reference", REF_EYE, ref_target(), REF_FOV ),
          ( "aerial", ( -2600, -3200, 3000 ), ( 200, 700, 0 ), 60 ),
          ( "deck", ( -480, 960, G + 64 ), ( 700, 2400, 600 ), 85 ),
          ( "tunnel", ( 350, 820, 64 ), ( 350, 1400, 60 ), 85 ),
          ( "east_roof", ( 1100, 300, G + 64 ), ( -200, 900, 200 ), 85 ),
          ( "terrace", ( -280, -200, TERRACE_Z + 64 ), ( 200, 800, 100 ), 85 ),
          ( "lc_room", ( -330, -120, OVER_Z + 64 ), ( -560, 160, OVER_Z + 60 ), 85 ) )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--stage", action="store_true", help="write under output/orion/v2/ instead of Assets/" )
    parser.add_argument( "--preview", metavar="DIR", help="also write flat views and the reach grid's picture here" )
    parser.add_argument( "--views", nargs="*", help="only these views" )
    parser.add_argument( "--no-scene", action="store_true" )
    parser.add_argument( "--no-models", action="store_true" )
    args = parser.parse_args()

    root = STAGE / "Assets" if args.stage else ASSETS
    out_dir = root / RESOURCE_DIR
    models = build()
    written = set()
    for name, model in models.items():
        if K.is_empty( model ):
            print( f"{name}: empty, not written" )
            continue
        written.add( name )
        if args.no_models:
            continue
        count = K.write_model( out_dir, RESOURCE_DIR, name, model )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
    if R.UNKNOWN_PAINTS:
        print( f"paints with no material: {', '.join( sorted( R.UNKNOWN_PAINTS ) )}" )
    light_list = list( P.LIGHTS )
    print( f"{len( light_list )} lights ({sum( 1 for l in light_list if l[4] )} shadowed), {len( P.CLIPS ) + len( ROOF_CLIPS )} clips" )

    solid = [ models[name] for name, _, collide, _ in SCENE_MODELS if collide and name in models ]
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
        if not install_reflection_texture():
            print( "no compiled sky cube yet: compile materials/orion/sky/oa_sky.vmat in the editor, then run again" )
        write_minimap( solid, root / MINIMAP_PATH if args.stage else K.asset_file( "ui/minimaps" ) / "minimap_orion.png" )
        write_scene( written, light_list, root / "scenes/maps/Orion/orion.scene" )
    if out:
        preview_setup()
        everything = list( models.values() )
        opaque, glass = PV.triangles( everything ), PV.triangles( everything, glass=True )
        for name, eye, target, fov in VIEWS:
            if args.views and name not in args.views:
                continue
            size = ( 768, 512 ) if name == "reference" else ( 960, 540 )
            PV.perspective( opaque, glass, eye, target, size=size, fov=fov ).convert( "RGB" ).save( out / f"{name}.png" )
            print( f"wrote {out / f'{name}.png'}" )


if __name__ == "__main__":
    main()
