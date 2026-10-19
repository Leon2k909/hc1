"""
Veridant: a Mediterranean cliffside resort at sunset after rain. A multiplayer map built by script like Belltower,
Railhead, Lowtide and Riverdale (map_kit's boxes and polygons), after the user's reference picture (2026-10-15): the
wet courtyard round its dark reflecting pool and boulder, the travertine resort round it (the operations building
with its pergola, ivy and SECURE / EXPLORE / CONTROL banner on the left, the gallery lounge and the colonnaded cafe
with its roof terrace behind the pool, the VERIDANT RESORT pylon, an uplit olive and the grand stair with its LED
nosings on the right, the stone pine and a furled umbrella on the upper terrace), black and olive military cases
about the courtyard, and the bay beyond: the sun on the horizon, a superyacht, sailboats and the cliffed headland
with its hilltop village. Veridant Resort, its three-wave mark and every marking are the map's own.

    python Tools/veridant_map.py [--preview <dir>] [--views name ...] [--no-scene] [--no-models] [--art]

Run Tools/veridant_materials.py and Tools/veridant_sky.py first. Writes:
- the models, to Assets/models/maps/veridant/: the ground, the buildings, the dressing, the foliage, the glass, the
  pool's water, the sea and the backdrop (Tools/veridant_backdrop.py: the headland, village, town, yacht, boats and
  the hillside; drawn only);
- the scene, Assets/scenes/maps/Veridant/veridant.scene, rewritten whole on every run (change the layout here, not in
  the editor);
- the radar picture, ui/minimaps/minimap_veridant.png, and with --art a stand-in menu picture, ui/maps/veridant.png.

Plan coordinates: e east, n north, z up, inches. The play area is e -1750..1900, n -1350..1000. Three levels: the
ground (z 0), the roof terraces (128: the cafe's roof, the garden terrace and the north terrace, the operations
building's balcony and first floor, the lounge's gallery) and the east terrace (192). Red Team
spawns on the seafront promenade at the west end, Blue Team in the entrance forecourt at the east. Three lanes:
- North: the promenade's stair up to the garden terrace, steps up to the north terrace (bomb site A, with the stone
  pine, the bar and the umbrella), across the head of the grand stair to the east terrace and down to the forecourt.
- Middle: through the cafe (or over its roof) into the courtyard round the pool, then through the colonnade under the
  east terrace to the forecourt; the grand stair and the reception's inner stair climb from the courtyard to the
  north terrace, a stair to the operations balcony.
- South: the gardens south of the operations building (bomb site B among the olive groves at their east end) to the
  east plaza, or through the operations building's hall and up its stair to the lobby and the balcony.

Every run checks every spawn, objective and cash spot with railhead_map's check_spots, check_reach and
check_retakes_sight, with this map's bounds, and prints what's wrong.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K
import railhead_map as R
import railhead_preview as PV
import veridant_materials as VM
import veridant_parts as P
from riverdale_parts import v, unit, card, box, obox, rod, UP

STONE, METAL, WOOD, PLASTIC, GLASS, FABRIC = "default", "metal", "wood", "plastic", "glass", "fabric"

TITLE = "Veridant"
OUT_DIR = K.ASSETS / "models/maps/veridant"
RESOURCE_DIR = "models/maps/veridant"
SCENE_FILE = K.ASSETS / "scenes/maps/Veridant/veridant.scene"
MINIMAP_PATH = "ui/minimaps/minimap_veridant.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_veridant.png"
MAP_ART_PATH = "ui/maps/veridant.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "d5ecbe1a-6aac-4ce1-af7c-cd9dfbcda091" )

SUN_PITCH, SUN_YAW = 3.4, -113.4                     # veridant_sky's: on the horizon, 23 degrees north of west
SUN_COLOUR = "1.70,0.78,0.36,1"
SKY_MATERIAL = "materials/veridant/sky/veridant_sky.vmat"
FOG_COLOUR = "0.72,0.69,0.73"
CATCH_FLOOR_Z = -1400

# Levels.
L0, L1, L2 = 0.0, 128.0, 192.0
T = 16.0            # walls
SLAB = 16.0

PLAY = ( -1750.0, 1900.0, -1350.0, 1000.0 )
GROUND = ( -1750.0, 2300.0, -1750.0, 1400.0 )
NAV_TOP = 330.0
SEA_WALL = -1750.0

LOUNGE = ( -720.0, -200.0, -560.0, -180.0 )
LOUNGE_TOP = 272.0
CAFE = ( -720.0, -200.0, -180.0, 200.0 )
CAFE_FRONT = -260.0                     # the cafe's shopfront, set back under the terrace's edge: the colonnade
GARDEN = ( -720.0, -200.0, 200.0, 1000.0 )
NORTH = ( -200.0, 220.0, 200.0, 760.0 )          # the north terrace (128) on its block, the reception inside it
ROOM = ( -184.0, 204.0, 216.0, 560.0 )
ROOM_TOP = 112.0
ROOM_DOOR = ( 140.0, 200.0, 100.0 )      # in the block's south face: right of the pylon from the courtyard
INNER_STAIR = ( -184.0, -84.0, 260.0, 447.0 )   # e0, e1, foot n, head n: against the reception's west wall
STAIRWELL = ( -184.0, -78.0, 300.0, 447.0 )
SPA = ( -200.0, 1200.0, 760.0, 1000.0 )
SPA_TOP = 400.0
OPS = ( -200.0, 760.0, -700.0, -320.0 )
OPS_FACE = -420.0                        # the upper floors' north face; the balcony runs n -420..-320 on the podium
OPS_TOP = 400.0
LOBBY = ( 140.0, 744.0, -684.0, -436.0 )  # the first floor's open part
OPS_STAIR = ( 420.0, 607.0, -684.0, -624.0 )   # foot e, head e, n0, n1: the hall's stair up to the lobby
COURT = ( -200.0, 760.0, -320.0, 200.0 )
APRON = ( 316.0, 760.0, 200.0, 280.0 )
POOL = ( -125.0, 125.0, -165.0, 65.0 )
POOL_KERB = 18.0
WATER_Z = 13.0
DECK = ( -200.0, 560.0, -320.0, -200.0, 16.0 )
PYLON = ( 110.0, 140.0, 96.0, 196.0, 170.0 )
PLANTER = ( 220.0, 316.0, 202.0, 276.0 )
STAIR = ( 220.0, 380.0, 280.0, 467.0 )   # e0, e1, foot n, head n: the grand stair, up to the north terrace (128)
EAST_A = ( 760.0, 1200.0, -420.0, 280.0 )
EAST_B = ( 380.0, 1200.0, 280.0, 760.0 )
SLOT_TOP = ( 220.0, 380.0, 467.0, 760.0 )   # the stair's head, at 128
EAST_STEPS = ( 284.0, 380.0, 620.0, 740.0 )  # foot e, head e, n0, n1: the north terrace (128) up to the east terrace (192)
TUNNEL = ( 760.0, 1200.0, -260.0, -140.0 )
TUNNEL_TOP = 176.0
PLAZA = ( 760.0, 1200.0, -700.0, -420.0 )
FORE = ( 1200.0, 1900.0, -700.0, 1000.0 )
FORE_STAIR = ( 1486.0, 1200.0, 380.0, 540.0 )   # foot e, head e, n0, n1
BALCONY_STAIR = ( 650.0, 760.0, -420.0, -320.0 )  # foot e, head e, n0, n1: the balcony (128) up to the east terrace
COURT_STAIR = ( 660.0, 473.0, -316.0, -256.0 )   # foot e, head e, n0, n1: the courtyard up to the balcony's landing
COURT_LANDING = ( 380.0, 473.0, -320.0, -256.0 )
PROM_STAIR = ( -840.0, -720.0, 340.0, 527.0 )    # e0, e1, foot n, head n: the promenade up to the garden terrace
PROM_LANDING = ( -840.0, -720.0, 527.0, 640.0 )
PROM = ( -1750.0, -720.0, -1350.0, 1000.0 )
GARDEN_S = ( -720.0, 1900.0, -1350.0, -700.0 )

# The reference picture's camera: on the east terrace behind its glass, looking west over the courtyard.
HERO = ( ( 801.0, -40.0, 256.0 ), 90.0, -9.6, 74.0 )    # eye (plan), yaw (world: 90 is west), pitch, horizontal fov


# ---------------------------------------------------------------------------------------------------------------------
# Paints

PAINTS = set( VM.all_paints() )
GLASS_PAINTS = { "vr_glass", "vr_glass_clear" }
UNKNOWN = set()


def configure( model ):
    for paint in list( model.polygons ):
        if paint.startswith( "vr_" ):
            model.material_overrides[paint] = f"{VM.RESOURCE_DIR}/{paint}.vmat"
            model.tile_overrides[paint] = VM.TILES.get( paint, 64.0 )
            if paint not in PAINTS:
                UNKNOWN.add( paint )
        else:
            UNKNOWN.add( paint )
            model.material_overrides[paint] = f"{VM.RESOURCE_DIR}/vr_stone.vmat"
            model.tile_overrides[paint] = 192.0
    model.grain_paints = { p for p in model.polygons if p in ( "vr_timber", "vr_timber_dark" ) }
    model.anchored_paints = { p for p in model.polygons if p in ( "vr_stone", "vr_stone_dark" ) }
    model.decal_paints = set()
    return model


def floor( m, e0, e1, n0, n1, z, paint="vr_paving" ):
    if e1 - e0 > 0.1 and n1 - n0 > 0.1:
        card( m, paint, [ v( e0, n0, z ), v( e1, n0, z ), v( e1, n1, z ), v( e0, n1, z ) ], UP )


def ceiling( m, e0, e1, n0, n1, z, paint="vr_ceiling" ):
    if e1 - e0 > 0.1 and n1 - n0 > 0.1:
        card( m, paint, [ v( e0, n0, z ), v( e1, n0, z ), v( e1, n1, z ), v( e0, n1, z ) ], -UP )


def solid( m, e0, e1, n0, n1, z0, z1, paints="vr_stone", surface=STONE ):
    box( m, e0, e1, n0, n1, z0, z1, paints, surface )


def wall( m, axis, run, across, z, outward, openings=(), outside="vr_stone", inside="vr_concrete", reveal="vr_stone_dark",
          end=None, surface=STONE ):
    """ map_kit's Wall: openings ( centre, width, z0, z1 ). """
    w = K.Wall( axis, run, across, z, outward )
    for c, width, z0, z1 in openings:
        w.add( c, width, z0, z1, "door" if z0 <= z[0] + 0.5 else "window" )
    w.build( m, outside, inside, reveal, end, surface )
    return w


def glazing( m, g, axis, at, r0, r1, z0, z1, out, mullion=46.0, transom=None, frame="vr_steel", pane="vr_glass" ):
    """ A glazed wall in an opening: steel mullions and frame in the model, the panes and their collision in the
    glass model g. axis: the wall runs along 'e' or 'n'; at: its face's position across; out: +1 / -1. """
    def pt( r, z, d=0.0 ):
        return v( r, at + d * out, z ) if axis == "e" else v( at + d * out, r, z )
    outv = v( 0, out, 0 ) if axis == "e" else v( out, 0, 0 )
    count = max( 1, int( round( ( r1 - r0 ) / mullion ) ) )
    for i in range( count + 1 ):
        r = r0 + ( r1 - r0 ) * i / count
        a, b = pt( r - 1.0, z0, -1.5 ), pt( r + 1.0, z1, 1.5 )
        lo, hi = np.minimum( a, b ), np.maximum( a, b )
        box( m, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], frame )
    for z in ( z0, z1 ) + ( ( transom, ) if transom else () ):
        a, b = pt( r0, z - 1.0, -1.5 ), pt( r1, z + 1.0, 1.5 )
        lo, hi = np.minimum( a, b ), np.maximum( a, b )
        box( m, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], frame )
    for sg in ( -1, 1 ):
        card( g, pane, [ pt( r0, z0, 0.3 * sg ), pt( r1, z0, 0.3 * sg ), pt( r1, z1, 0.3 * sg ), pt( r0, z1, 0.3 * sg ) ], outv * sg )
    a, b = pt( r0, z0, -0.5 ), pt( r1, z1, 0.5 )
    lo, hi = np.minimum( a, b ), np.maximum( a, b )
    g.collision_box( lo, hi, GLASS )


# ---------------------------------------------------------------------------------------------------------------------
# The ground: paving, the promenade, the gardens, the forecourt

def ground():
    m = K.Model()
    e0, e1, n0, n1 = GROUND
    m.collision_box( ( e0, n0, -24 ), ( e1, n1, 0 ), STONE )
    # The courtyard: wet granite slabs round the pool, the raised deck along its south side.
    c0, c1, cn0, cn1 = COURT
    de0, de1, dn0, dn1, dz = DECK
    p0, p1, pn0, pn1 = POOL
    floor( m, c0, p0, dn1, cn1, L0 )
    floor( m, p1, c1, dn1, cn1, L0 )
    floor( m, p0, p1, dn1, pn0, L0 )
    floor( m, p0, p1, pn1, cn1, L0 )
    floor( m, de1, c1, cn0, dn1, L0 )
    floor( m, *APRON, L0 )
    floor( m, *PROM, L0 )
    floor( m, *PLAZA, L0 )
    floor( m, *FORE, L0 )
    floor( m, TUNNEL[0], TUNNEL[1], TUNNEL[2], TUNNEL[3], L0 )
    # The gardens: lawn with gravel paths (the paths drawn over it a hair higher).
    g0, g1, gn0, gn1 = GARDEN_S
    floor( m, g0, g1, gn0, gn1, L0, "vr_lawn" )
    floor( m, LOUNGE[0], LOUNGE[1], gn1, LOUNGE[2], L0, "vr_lawn" )
    for a, b, c, d in ( ( g0, g1, -880.0, -820.0 ), ( -40.0, 20.0, gn0, gn1 ), ( 560.0, 620.0, gn0, gn1 ), ( 1240.0, 1300.0, gn0, gn1 ),
                        ( g0, g1, -1220.0, -1170.0 ) ):
        floor( m, a, b, c, d, L0 + 0.15, "vr_gravel" )
    # Beyond the play area, round to the backdrop: paving east, north and south.
    for a, b, c, d in ( ( PLAY[1], e1, n0, n1 ), ( e0, PLAY[1], n0, PLAY[2] ), ( e0, PLAY[1], PLAY[3], n1 ) ):
        floor( m, a, b, c, d, L0, "vr_gravel" )
    # Linear drains across the courtyard, the picture's diagonal ones in the foreground.
    for a, b in ( ( ( 380, -150 ), ( 700, 150 ) ), ( ( 300, -60 ), ( 520, 140 ) ), ( ( -180, 130 ), ( 60, 140 ) ), ( ( 560, -300 ), ( 740, -120 ) ) ):
        P.drain( m, a, b, L0 )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# The lounge: a gallery bar on two floors, timber fins below and glass above

def lounge( m, g ):
    e0, e1, n0, n1 = LOUNGE
    top = LOUNGE_TOP
    # Walls: ground floor 0..112, upper floor 128..256, the slab between 112..128, roof 256..272.
    wall( m, "n", ( n0, n1 ), ( e1 - T, e1 ), ( 0, 112 ), "+e", [ ( -250.0, 100.0, 0, 96 ), ( -490.0, 60.0, 0, 96 ) ] )
    wall( m, "n", ( n0, n1 ), ( e1 - T, e1 ), ( 112, top ), "+e", [ ( -370.0, 60.0, 128, 224 ), ( -258.0, 124.0, 136, 246 ) ] )
    wall( m, "n", ( n0, n1 ), ( e0, e0 + T ), ( 0, top ), "-e", [ ( -390.0, 60.0, 0, 96 ), ( -270.0, 120.0, 140, 236 ), ( -470.0, 120.0, 140, 236 ) ] )
    wall( m, "e", ( e0, e1 ), ( n0, n0 + T ), ( 0, top ), "-n", [ ( -470.0, 60.0, 0, 96 ), ( -330.0, 140.0, 140, 236 ), ( -600.0, 140.0, 140, 236 ) ] )
    wall( m, "e", ( e0, e1 ), ( n1 - T, n1 ), ( 112, top ), "+n", [ ( -270.0, 60.0, 128, 224 ), ( -460.0, 220.0, 138, 240 ) ] )
    wall( m, "e", ( e0, e1 ), ( n1 - T, n1 ), ( 0, 112 ), None, [ ( -430.0, 60.0, 0, 96 ) ] )
    solid( m, e0 + T, e1 - T, n0 + T, n1 - T, 112, 128, { "default": None, "+z": "vr_floor", "-z": "vr_ceiling" } )
    floor( m, e0 + T, e1 - T, n0 + T, n1 - T, L0, "vr_floor" )
    # Roof: a slab with a deep dark overhang all round.
    solid( m, e0 - 24, e1 + 24, n0 - 24, n1 + 24, top - 16, top, { "default": "vr_dark", "-z": "vr_soffit" } )
    ceiling( m, e0 + T, e1 - T, n0 + T, n1 - T, top - 16.1 )
    # The east face's glazing upstairs (the gallery seen from the courtyard), the fins downstairs.
    glazing( m, g, "n", e1 - T / 2, -316.0, -200.0, 136, 246, 1, mullion=40 )
    # Keep the timber slats and lit backing entirely outside the courtyard door's clear opening.
    # Checking slat centres alone leaves the edge slats projecting into the doorway.
    door_lo, door_hi = -300.0, -200.0
    for n in np.arange( -316.0, -196.0, 7.0 ):
        if n + 4.0 > door_lo and n - 4.0 < door_hi:
            continue
        obox( m, ( e1 + 4, n, 56 ), ( 0, 1 ), ( 2.2, 8.0, 112 ), "vr_timber" )
    for a, b in ( ( -320.0, door_lo ), ( door_hi, -196.0 ) ):
        box( m, e1 + 0.1, e1 + 0.6, a, b, 2, 108, "vr_window_lit" )
    # The other faces' windows glazed.
    for axis, at, r0, r1, z0, z1, out in ( ( "n", e0 - 0.5, -330.0, -210.0, 140, 236, -1 ), ( "n", e0 - 0.5, -530.0, -410.0, 140, 236, -1 ),
                                           ( "e", n0 - 0.5, -400.0, -260.0, 140, 236, -1 ), ( "e", n0 - 0.5, -670.0, -530.0, 140, 236, -1 ),
                                           ( "e", n1 + 0.5, -570.0, -350.0, 138, 240, 1 ) ):
        glazing( m, g, axis, at, r0, r1, z0, z1, out )
    # Inside, ground floor: a bar along the west wall, sofas, low tables, warm downlights.
    P.bar_counter( m, ( e0 + 70, -520.0 ), ( e0 + 100, -300.0 ), L0, front="+e" )
    P.counter_shelves( m, ( e0 + T, -520.0 ), ( e0 + T + 12, -300.0 ), L0, face="+e" )
    for k, ( e, n, f ) in enumerate( ( ( -480, -300, ( 0, 1 ) ), ( -480, -470, ( 0, 1 ) ), ( -330, -460, ( -1, 0 ) ) ) ):
        P.sofa( m, ( e, n ), f, 84, L0 )
    for e, n in ( ( -420, -390 ), ( -580, -390 ) ):
        P.cylinder( m, ( e, n ), 16, 0, 16, "vr_stone_dark", 14, top="vr_stone_dark" )
    for k, ( e, n ) in enumerate( ( ( -600, -300 ), ( -420, -300 ), ( -600, -460 ), ( -420, -460 ), ( -300, -380 ) ) ):
        P.downlight( m, f"Lounge downlight {k}", ( e, n, 112 ), 260 )
    # Upstairs: the gallery: sofas facing the sea and the courtyard, paintings, a rug, lamps.
    floor( m, -640.0, -300.0, -500.0, -260.0, L1 + 0.2, "vr_rug" )
    P.sofa( m, ( -380, -300 ), ( 0, -1 ), 96, L1 )
    P.sofa( m, ( -560, -300 ), ( 0, -1 ), 96, L1 )
    P.sofa( m, ( -470, -470 ), ( 0, 1 ), 120, L1 )
    P.art( m, "art_1", ( -560, n0 + T + 0.2, 196 ), ( -1, 0, 0 ), 52 )
    P.art( m, "art_2", ( -360, n0 + T + 0.2, 196 ), ( -1, 0, 0 ), 52 )
    P.art( m, "art_3", ( e1 - T - 0.2, -460, 196 ), ( 0, -1, 0 ), 44 )
    P.art( m, "art_5", ( e0 + T + 0.2, -470, 192 ), ( 0, 1, 0 ), 50 )
    for k, ( e, n ) in enumerate( ( ( -600, -260 ), ( -380, -260 ), ( -600, -470 ), ( -380, -470 ) ) ):
        P.downlight( m, f"Gallery downlight {k}", ( e, n, top - 16 ), 300, shadows=( k == 0 ) )
    P.wall_washer( m, "Lounge door lamp", ( e1, -250.0, 104.0 ), ( 1, 0 ), 220 )


# ---------------------------------------------------------------------------------------------------------------------
# The cafe and its colonnade, the roof terrace over it

def cafe( m, g ):
    e0, e1, n0, n1 = CAFE
    f = CAFE_FRONT
    # Shopfront wall (thin piers between glass) set back under the terrace's edge.
    wall( m, "n", ( n0, n1 ), ( f - T, f ), ( 0, 112 ), "+e", [ ( -100.0, 64.0, 0, 96 ), ( 80.0, 64.0, 0, 96 ), ( 0.0, 96.0, 8, 104 ),
                                                                ( -150.0, 32.0, 8, 104 ), ( 150.0, 64.0, 8, 104 ) ] )
    for a, b in ( ( -48.0, 48.0 ), ( -166.0, -134.0 ), ( 118.0, 182.0 ) ):
        glazing( m, g, "n", f + 0.2, a, b, 8, 104, 1, mullion=48 )
    wall( m, "n", ( n0, n1 ), ( e0, e0 + T ), ( 0, 112 ), "-e", [ ( -80.0, 60.0, 0, 96 ), ( 100.0, 60.0, 0, 96 ), ( 10.0, 80.0, 30, 96 ) ] )
    glazing( m, g, "n", e0 - 0.3, -30.0, 50.0, 30, 96, -1 )
    wall( m, "e", ( e0 + T, f - T ), ( n0, n0 + T ), ( 0, 112 ), None, [ ( -430.0, 60.0, 0, 96 ) ] )
    wall( m, "e", ( e0 + T, f - T ), ( n1 - T, n1 ), ( 0, 112 ), None )
    floor( m, e0 + T, f - T, n0 + T, n1 - T, L0, "vr_floor" )
    # The slab: the cafe's ceiling and the terrace's floor, out to the colonnade's edge.
    solid( m, e0, e1, n0, n1, 112, 128, { "default": "vr_concrete", "+z": "vr_paving", "-z": "vr_ceiling", "+e": "vr_dark" } )
    ceiling( m, f, e1, n0, n1, 111.9, "vr_soffit" )
    # The colonnade's piers along its edge.
    for n in ( -170.0, -60.0, 50.0, 160.0 ):
        solid( m, e1 - 18, e1 - 2, n - 9, n + 9, 0, 112, "vr_stone" )
        P.wall_washer( m, f"Colonnade lamp {n}", ( e1 - 2, n, 80.0 ), ( 1, 0 ), 180, size=( 6.0, 4.0 ), rise=-10 )
    floor( m, f, e1, n0, n1, L0 + 0.1, "vr_floor" )
    # Inside: the counter and its back bar, tables, pendant lights, the olive in its planter by the glass.
    P.bar_counter( m, ( e0 + 90, -120.0 ), ( e0 + 120, 120.0 ), L0, front="+e" )
    P.counter_shelves( m, ( e0 + T, -120.0 ), ( e0 + T + 12, 120.0 ), L0, face="+e" )
    for k, ( e, n ) in enumerate( ( ( -520, -100 ), ( -520, 40 ), ( -400, -120 ), ( -400, 20 ), ( -400, 140 ), ( -520, 150 ) ) ):
        P.cafe_table( m, ( e, n ), L0, 2 + k % 2, seed=k )
    for k, ( e, n ) in enumerate( ( ( -560, -80 ), ( -560, 80 ), ( -400, -60 ), ( -400, 100 ) ) ):
        P.downlight( m, f"Cafe light {k}", ( e, n, 112 ), 280, shadows=( k == 1 ) )
    # The olive in a bed of black cubes in the colonnade (the picture's, between the doors).
    for k, ( e, n ) in enumerate( ( ( -236, 4 ), ( -236, 36 ), ( -214, 4 ), ( -214, 36 ) ) ):
        box( m, e - 10, e + 10, n - 15, n + 15, 0, 22, { "default": "vr_case_black", "+z": "vr_soil" }, PLASTIC )
    P.olive( m, ( -226, 20, 22 ), 96, seed=7, spread=0.8 )
    P.uplight( m, "Colonnade olive uplight", ( -222, 20, 22.1 ), 200 )


def roof_terrace( m, g, foliage ):
    """ On the cafe's roof (128): the kiosk with its lamps, loungers, the glass balustrade along its edge. The garden
    terrace north of it at the same level, on a solid podium, with the flag, olives in planters and the steps up to
    the north terrace. """
    e0, e1, n0, n1 = CAFE
    # The kiosk: a stone block with two lamps over its door, a dark cabinet beside it.
    k0, k1, kn0, kn1 = -460.0, -320.0, -90.0, 70.0
    solid( m, k0, k1, kn0, kn1, L1, L1 + 84, "vr_stone" )
    solid( m, k0 - 4, k1 + 4, kn0 - 4, kn1 + 4, L1 + 84, L1 + 90, "vr_stone_dark" )
    for n in ( -50.0, 30.0 ):
        P.wall_washer( m, f"Kiosk lamp {n}", ( k1, n, L1 + 70 ), ( 1, 0 ), 220, size=( 7.0, 4.0 ), rise=-14 )
    box( m, k1 - 0.5, k1 + 0.2, -32, 12, L1, L1 + 76, "vr_dark" )
    solid( m, -300.0, -270.0, 100.0, 160.0, L1, L1 + 60, { "default": "vr_dark", "+z": "vr_steel" }, METAL )
    for k, n in enumerate( ( -150.0, -110.0 ) ):
        P.lounger( m, ( -560, n ), ( 1, 0 ), L1 )
    # The balustrade along the colonnade's edge and the sea side.
    P.glass_rail( m, [ ( e1 - 1, n0 + 2 ), ( e1 - 1, n1 ) ], L1, name="cafe terrace rail" )
    P.glass_rail( m, [ ( e0 + 2, n0 + 2 ), ( e0 + 2, n1 ) ], L1, name="cafe sea rail" )
    # The garden terrace: lawn and paving on its podium, its edges.
    ga0, ga1, gn0, gn1 = GARDEN
    solid( m, ga0, ga1, gn0, gn1, 0, L1, { "default": "vr_stone", "+z": None, "+e": None, "-n": None } )
    floor( m, ga0, ga1, gn0, gn1, L1, "vr_paving" )
    floor( m, -620.0, -320.0, 300.0, 520.0, L1 + 0.15, "vr_lawn" )
    floor( m, -620.0, -380.0, 640.0, 900.0, L1 + 0.15, "vr_lawn" )
    P.glass_rail( m, [ ( ga0 + 2, gn0 ), ( ga0 + 2, PROM_LANDING[2] ) ], L1, name="garden sea rail a" )
    P.glass_rail( m, [ ( ga0 + 2, PROM_LANDING[3] ), ( ga0 + 2, gn1 - 2 ), ( ga1, gn1 - 2 ) ], L1, name="garden sea rail b" )
    # Planters with olives, the flag, loungers, a pergola over a table.
    for k, ( e, n, h ) in enumerate( ( ( -660, 330, 90 ), ( -660, 560, 85 ), ( -470, 740, 95 ), ( -260, 940, 90 ) ) ):
        P.planter( m, ( e - 30, n - 30 ), ( e + 30, n + 30 ), L1, L1 + 24 )
        P.olive( foliage, ( e, n, L1 + 20 ), h, seed=30 + k )
    P.flag( m, ( -514, 413 ), 200, z0=L1, along=( 0, 1 ) )
    for n in ( 340.0, 400.0, 460.0 ):
        P.lounger( m, ( -440, n ), ( -1, 0 ), L1 )
    P.cafe_table( m, ( -520, 800 ), L1, 3, seed=40 )
    P.cafe_table( m, ( -330, 820 ), L1, 2, seed=41 )
    P.shrubs( foliage, ( -620, 300 ), ( -560, 520 ), L1, seed=42, kind="rosemary", h=22 )
    for k, ( e, n ) in enumerate( ( ( -600, 260 ), ( -320, 600 ), ( -600, 960 ) ) ):
        P.lantern_post( m, f"Garden lantern {k}", ( e, n, L1 ), 96, radius=320 )


# ---------------------------------------------------------------------------------------------------------------------
# The operations building: hall, lobby, balcony, banner, pergola

def ops( m, g, foliage ):
    e0, e1, n0, n1 = OPS
    face = OPS_FACE
    # Ground floor (the hall) 0..112 under the whole footprint, its doors.
    wall( m, "e", ( e0, e1 ), ( n1 - T, n1 ), ( 0, 112 ), "+n", [ ( 320.0, 80.0, 0, 100 ), ( 60.0, 120.0, 30, 96 ), ( 620.0, 100.0, 30, 96 ) ] )
    wall( m, "e", ( e0, e1 ), ( n0, n0 + T ), ( 0, 112 ), "-n", [ ( 100.0, 80.0, 0, 100 ), ( 560.0, 80.0, 0, 100 ), ( 330.0, 120.0, 30, 96 ) ] )
    wall( m, "n", ( n0 + T, n1 - T ), ( e1 - T, e1 ), ( 0, 112 ), "+e", [ ( -600.0, 80.0, 0, 100 ) ] )
    wall( m, "n", ( n0 + T, n1 - T ), ( e0, e0 + T ), ( 0, 112 ), None, [ ( -490.0, 60.0, 0, 96 ) ] )
    floor( m, e0 + T, e1 - T, n0 + T, n1 - T, L0, "vr_floor" )
    for axis, at, r0, r1, out in ( ( "e", n1 + 0.4, 0.0, 120.0, 1 ), ( "e", n1 + 0.4, 570.0, 670.0, 1 ), ( "e", n0 - 0.4, 270.0, 390.0, -1 ) ):
        glazing( m, g, axis, at, r0, r1, 30, 96, out )
    # The slab over the hall: the balcony's floor in front of the upper floors, the lobby's floor behind (with the
    # stairwell over the hall's stair).
    s0, s1, sn0, sn1 = OPS_STAIR
    solid( m, e0, e1, face, n1, 112, L1, { "default": "vr_stone", "+z": None, "-z": "vr_ceiling", "-n": None } )
    floor( m, e0, e1, face, n1, L1, "vr_paving" )
    for a, b, c, d in ( ( e0, e1, n0, sn0 ), ( e0, s0, sn0, sn1 ), ( s1, e1, sn0, sn1 ), ( e0, e1, sn1, face ) ):
        solid( m, a, b, c, d, 112, L1, { "default": None, "-z": "vr_ceiling", "+z": "vr_floor" }, STONE )
    # The hall's stair up to the lobby.
    P.stone_stair( m, ( s0, ( sn0 + sn1 ) / 2 ), ( s1, ( sn0 + sn1 ) / 2 ), sn1 - sn0, L0, L1, sides=( False, True ), name="ops stair" )
    P.glass_rail( m, [ ( s0, sn1 + 2 ), ( s1, sn1 + 2 ) ], 0, slope=[ L0 + 7, L1 ], clip_to=48, name="ops stair rail" )
    P.steel_rail( m, [ ( s0 - 1, sn0 ), ( s0 - 1, sn1 + 1 ), ( s1, sn1 + 1 ) ], L1, name="ops stairwell rail", style="rails" )
    # Upper floors: the lobby's floor (128..256) and the closed second floor (256..400), the roof.
    wall( m, "e", ( e0, e1 ), ( face - T, face ), ( L1, OPS_TOP ), "+n",
          [ ( 230.0, 140.0, L1 + 4, 248 ), ( 510.0, 100.0, L1, L1 + 100 ), ( 660.0, 120.0, L1 + 8, 248 ), ( -120.0, 100.0, 286, 374 ),
            ( 340.0, 100.0, 286, 374 ), ( 600.0, 100.0, 286, 374 ) ] )
    wall( m, "e", ( e0, e1 ), ( n0, n0 + T ), ( L1, OPS_TOP ), "-n", [ ( 120.0, 140.0, 150, 236 ), ( 520.0, 140.0, 150, 236 ), ( 120.0, 140.0, 286, 374 ),
                                                                       ( 520.0, 140.0, 286, 374 ) ] )
    wall( m, "n", ( n0 + T, face - T ), ( e1 - T, e1 ), ( L1, OPS_TOP ), "+e", [ ( -560.0, 140.0, 150, 236 ), ( -560.0, 140.0, 286, 374 ) ] )
    wall( m, "n", ( n0 + T, LOUNGE[2] ), ( e0, e0 + T ), ( L1, OPS_TOP ), "-e" )
    wall( m, "n", ( LOUNGE[2], face - T ), ( e0, e0 + T ), ( LOUNGE_TOP, OPS_TOP ), "-e" )
    solid( m, e0 + T, e1 - T, n0 + T, face - T, 256 - 16, 256, { "default": None, "-z": "vr_ceiling", "+z": None } )
    solid( m, e0 - 6, e1 + 6, n0 - 6, face + 6, OPS_TOP, OPS_TOP + 16, { "default": "vr_stone_dark", "-z": "vr_soffit" } )
    for a, b, c, d in ( ( e0 - 6, e1 + 6, n0 - 6, n0 + 4 ), ( e0 - 6, e1 + 6, face - 4, face + 6 ), ( e0 - 6, e0 + 4, n0 - 6, face + 6 ),
                        ( e1 - 4, e1 + 6, n0 - 6, face + 6 ) ):
        solid( m, a, b, c, d, OPS_TOP + 16, OPS_TOP + 30, "vr_stone_dark" )
    # The closed west part of the first floor: a blank inner wall with the lobby east of it.
    wall( m, "n", ( n0 + T, face - T ), ( LOBBY[0] - T, LOBBY[0] ), ( L1, 240 ), None )
    ceiling( m, LOBBY[0], e1 - T, n0 + T, face - T, 239.9 )
    # Glazing: the lobby's big window and door on the balcony, its side windows, the upper floor.
    glazing( m, g, "e", face + 0.4, 160.0, 300.0, L1 + 4, 248, 1, transom=220 )
    glazing( m, g, "e", face + 0.4, 600.0, 720.0, L1 + 8, 248, 1, transom=220 )
    for r in ( -120.0, 340.0, 600.0 ):
        glazing( m, g, "e", face + 0.4, r - 50, r + 50, 286, 374, 1 )
        box( m, r - 50, r + 50, face - T - 2, face - T - 1, 286, 374, "vr_window_lit" if r > 0 else "vr_window_dark" )
    for r in ( 120.0, 520.0 ):
        for z0, z1 in ( ( 150, 236 ), ( 286, 374 ) ):
            glazing( m, g, "e", n0 - 0.4, r - 70, r + 70, z0, z1, -1 )
            box( m, r - 70, r + 70, n0 + T + 1, n0 + T + 2, z0, z1, "vr_window_dark" )
    for z0, z1 in ( ( 150, 236 ), ( 286, 374 ) ):
        glazing( m, g, "n", e1 + 0.4, -630.0, -490.0, z0, z1, 1 )
    # The lobby inside: a reception desk, sofas, cases, the lit back wall, lamps.
    P.bar_counter( m, ( 380.0, -560.0 ), ( 520.0, -530.0 ), L1, front="+n" )
    box( m, LOBBY[0] + 1, LOBBY[0] + 1.6, -650, -460, L1 + 10, 230, "vr_window_lit" )
    P.sofa( m, ( 240, -500 ), ( 1, 0 ), 84, L1 )
    P.sofa( m, ( 660, -500 ), ( -1, 0 ), 84, L1 )
    P.case_stack( m, ( 300, -640 ), ( 1, 0 ), "vr_case_olive", seed=91, z0=L1 )
    P.art( m, "art_4", ( LOBBY[0] + 2, -560, 186 ), ( 0, -1, 0 ), 44 )
    for k, ( e, n ) in enumerate( ( ( 260, -520 ), ( 460, -520 ), ( 660, -520 ), ( 460, -640 ) ) ):
        P.downlight( m, f"Lobby downlight {k}", ( e, n, 240 ), 300, shadows=( k == 1 ) )
    # The hall below: reception, columns, cases, lamps.
    for e in ( 100.0, 340.0, 580.0 ):
        P.cylinder( m, ( e, -510 ), 14, 0, 112, "vr_stone", 16, surface=STONE )
    P.bar_counter( m, ( -60.0, -560.0 ), ( 100.0, -530.0 ), L0, front="+n" )
    for k, ( e, n ) in enumerate( ( ( 200, -420 ), ( 640, -420 ), ( 0, -640 ), ( 460, -380 ) ) ):
        P.case_stack( m, ( e, n ), ( 1, 0.1 * k ), "vr_case_black" if k % 2 else "vr_case_olive", seed=95 + k )
    for k, ( e, n ) in enumerate( ( ( -100, -420 ), ( 220, -420 ), ( 540, -420 ), ( -100, -620 ), ( 220, -620 ), ( 540, -620 ) ) ):
        P.downlight( m, f"Hall downlight {k}", ( e, n, 112 ), 300, shadows=( k == 1 ) )
    # The balcony: its railing over the courtyard, the banner and lamps on the face, the lounge's door at its end.
    P.steel_rail( m, [ ( COURT_LANDING[1], n1 - 2 ), ( BALCONY_STAIR[0], n1 - 2 ) ], L1, name="balcony rail e", style="rails" )
    P.steel_rail( m, [ ( e0, n1 - 2 ), ( COURT_LANDING[0], n1 - 2 ) ], L1, name="balcony rail w", style="rails" )
    P.banner( m, ( 10.0, face + 2, 392.0 ), ( -1, 0, 0 ), 200 )
    for e in ( -150.0, 120.0, 400.0 ):
        P.wall_washer( m, f"Balcony lamp {e}", ( e, face, L1 + 20 ), ( 0, 1 ), 240, rise=20 )
    for e in ( 70.0, 380.0, 700.0 ):
        P.wall_washer( m, f"Podium lamp {e}", ( e, n1, 92.0 ), ( 0, 1 ), 260, size=( 10.0, 5.0 ), rise=-30 )
    # The pergola on the roof: dark timber beams on steel posts reaching out over the balcony, ivy hanging off it.
    pz = OPS_TOP + 30
    for e in np.arange( e0 + 10, e1 + 1, 120.0 ):
        box( m, e - 3, e + 3, face - 40, face - 34, pz, pz + 90, "vr_steel" )
    for n in ( face - 37, face + 40 ):
        box( m, e0 - 10, e1 + 10, n - 4, n + 4, pz + 90, pz + 102, "vr_timber_dark" )
    for e in np.arange( e0, e1 + 1, 24.0 ):
        box( m, e - 1.5, e + 1.5, face - 60, face + 60, pz + 102, pz + 108, "vr_timber_dark" )
    for e in np.arange( e0 + 10, e1 + 1, 240.0 ):
        rod( m, ( e, face + 40, pz + 90 ), ( e, face, OPS_TOP + 16 ), 1.6, "vr_steel", 6 )
    P.ivy( foliage, ( 120.0, face + 2, OPS_TOP + 14 ), ( -1, 0, 0 ), 220, 150, seed=3 )
    P.ivy( foliage, ( -150.0, face + 2, OPS_TOP + 14 ), ( -1, 0, 0 ), 120, 200, seed=4 )
    P.ivy( foliage, ( 560.0, face + 2, OPS_TOP + 14 ), ( -1, 0, 0 ), 180, 120, seed=5 )
    for e in np.arange( e0 + 20, e1, 50.0 ):
        P.ivy( foliage, ( e, face + 44, pz + 100 ), ( -1, 0, 0 ), 50, 150 + 60 * math.sin( e / 37.0 ), seed=int( e ) + 900, off=0.0 )
    # Planters along the balcony's edge with ivy spilling over the podium wall.
    for e in ( -100.0, 150.0 ):
        P.planter( m, ( e - 40, n1 - 30 ), ( e + 40, n1 - 4 ), L1, L1 + 20 )
        P.shrubs( foliage, ( e - 36, n1 - 26 ), ( e + 36, n1 - 8 ), L1 + 16, seed=int( e ), h=22 )
        P.ivy( foliage, ( e, n1 + 0.5, L1 + 18 ), ( 1, 0, 0 ), 70, 90, seed=int( e ) + 7, off=1.0 )
    # The balcony stair up to the east terrace, and the courtyard's stair up to its landing.
    a, b, c, d = BALCONY_STAIR
    P.stone_stair( m, ( a, ( c + d ) / 2 ), ( b, ( c + d ) / 2 ), d - c, L1, L2, sides=( False, True ), name="balcony stair" )
    P.steel_rail( m, [ ( a, d - 1 ), ( b, d - 1 ) ], 0, slope=[ L1 + 7, L2 ], clip_to=48, name="balcony stair rail", style="rails" )
    a, b, c, d = COURT_STAIR
    P.stone_stair( m, ( a, ( c + d ) / 2 ), ( b, ( c + d ) / 2 ), d - c, L0, L1, sides=( True, False ), name="court stair" )
    la, lb, lc, ld = COURT_LANDING
    solid( m, la, lb, lc, ld, 0, L1, { "default": "vr_stone", "+z": "vr_paving", "-n": None } )
    P.steel_rail( m, [ ( a, d + 1 ), ( b, d + 1 ) ], 0, slope=[ L0 + 7, L1 ], clip_to=48, name="court stair rail", style="rails" )
    P.steel_rail( m, [ ( lb, ld + 1 ), ( la, ld + 1 ), ( la, lc ) ], L1, name="court landing rail", style="rails" )


# ---------------------------------------------------------------------------------------------------------------------
# The north block: the reception and its stair, the north terrace on top

def north_block( m, g, foliage ):
    e0, e1, n0, n1 = NORTH
    r0, r1, rn0, rn1 = ROOM
    de0, de1, dz = ROOM_DOOR
    # The reception's walls in the block, the solid north part, the slab with the stairwell: the terrace at 128, level
    # with the garden terrace west of it.
    wall( m, "e", ( e0, e1 ), ( n0, rn0 ), ( 0, ROOM_TOP ), "-n", [ ( ( de0 + de1 ) / 2, de1 - de0, 0, dz ) ] )
    solid( m, e0, r0, rn0, rn1, 0, ROOM_TOP, { "default": "vr_concrete", "-e": None } )
    solid( m, r1, e1, rn0, rn1, 0, ROOM_TOP, { "default": "vr_concrete", "+e": "vr_stone" } )
    solid( m, e0, e1, rn1, n1, 0, ROOM_TOP, { "default": "vr_concrete", "+e": "vr_stone", "-e": None, "+n": None } )
    s0, s1, sn0, sn1 = STAIRWELL
    for a, b, c, d, hide in ( ( e0, e1, n0, sn0, () ), ( e0, s0, sn0, sn1, ( "-e", ) ), ( s1, e1, sn0, sn1, () ), ( e0, e1, sn1, n1, ( "+n", ) ) ):
        if b - a > 0.5:
            paints = { "default": "vr_stone", "+z": None, "-z": "vr_ceiling", "+n": None }
            for f in hide:
                paints[f] = None
            if a <= e0:
                paints["-e"] = None
            solid( m, a, b, c, d, ROOM_TOP, L1, paints )
            floor( m, a, b, c, d, L1, "vr_paving" )
    # The stair's head (the slot between the north block and the east terrace), at 128 too.
    solid( m, *SLOT_TOP, 0, L1, { "default": None } )
    floor( m, *SLOT_TOP, L1, "vr_paving" )
    floor( m, r0, r1, rn0, rn1, L0, "vr_floor" )
    i0, i1, ifn, ihn = INNER_STAIR
    P.stone_stair( m, ( ( i0 + i1 ) / 2, ifn ), ( ( i0 + i1 ) / 2, ihn ), i1 - i0, L0, L1, sides=( True, False ), name="reception stair" )
    P.steel_rail( m, [ ( i1 + 1, ifn ), ( i1 + 1, ihn ) ], 0, slope=[ L0 + 7, L1 ], clip_to=48, name="reception stair rail", style="rails" )
    P.glass_rail( m, [ ( s0 + 1, sn1 ), ( s0 + 1, sn0 - 1 ), ( s1 + 1, sn0 - 1 ), ( s1 + 1, sn1 ) ], L1, name="stairwell rail" )
    # The reception: a desk, a sofa, the mark on the wall, lamps.
    P.bar_counter( m, ( 30.0, 420.0 ), ( 170.0, 450.0 ), L0, front="-n" )
    P.sofa( m, ( 60, 270 ), ( 0, 1 ), 84 )
    P.letters( m, "logo", ( 100.0, rn1 - 0.2, 80.0 ), ( -1, 0, 0 ), 30, "dark" )
    P.letters( m, "reception", ( 100.0, rn1 - 0.2, 58.0 ), ( -1, 0, 0 ), 8, "dark" )
    for k, ( e, n ) in enumerate( ( ( 0, 300 ), ( 150, 300 ), ( 150, 480 ), ( -40, 500 ) ) ):
        P.downlight( m, f"Reception downlight {k}", ( e, n, ROOM_TOP ), 260, shadows=( k == 1 ) )
    P.wall_washer( m, "Reception door lamp", ( ( de0 + de1 ) / 2, n0, dz + 8 ), ( 0, -1 ), 130 )
    # The north terrace: glass along the courtyard and down the stair, the bar against the spa, the umbrella, the
    # stone pine, the steps up to the east terrace.
    P.glass_rail( m, [ ( e0, n0 + 2 ), ( e1 - 1, n0 + 2 ), ( e1 - 1, STAIR[3] ) ], L1, name="north terrace rail" )
    P.bar_counter( m, ( 60.0, 712.0 ), ( 260.0, 740.0 ), L1, front="-n" )
    for k, e in enumerate( ( 90.0, 140.0, 190.0, 240.0 ) ):
        P.cylinder( m, ( e, 690 ), 6, L1, L1 + 28, "vr_steel", 10, top="vr_timber_dark" )
    P.umbrella_closed( m, ( 30.0, 470.0 ), 182, z0=L1 )
    P.cafe_table( m, ( 110, 380 ), L1, 3, seed=51 )
    P.planter( m, ( -60.0, 610.0 ), ( 60.0, 740.0 ), L1, L1 + 24 )
    P.stone_pine( foliage, ( 0.0, 676.0, L1 + 20 ), 360, crown_r=240, seed=8, lean=( 30.0, -40.0 ) )
    P.shrubs( foliage, ( -56, 614 ), ( 56, 736 ), L1 + 20, seed=9, kind="grass", h=24 )
    P.case_stack( m, ( 170, 540 ), ( 0, 1 ), "vr_case_olive", seed=52, z0=L1 )
    P.hard_case( m, ( 150, 290 ), ( 44, 26, 22 ), ( 1, 0.15 ), "vr_case_black", L1, seed=53 )
    for k, ( e, n ) in enumerate( ( ( -20, 300 ), ( 130, 650 ), ( 300, 520 ) ) ):
        P.lantern_post( m, f"North terrace lantern {k}", ( e, n, L1 ), 96, radius=360 )
    a, b, c, d = EAST_STEPS
    P.stone_stair( m, ( a, ( c + d ) / 2 ), ( b, ( c + d ) / 2 ), d - c, L1, L2, sides=( True, True ), name="east steps" )
    P.glass_rail( m, [ ( a, c - 2 ), ( b, c - 2 ) ], 0, slope=[ L1 + 7, L2 ], clip_to=48, name="east steps rail s" )
    P.glass_rail( m, [ ( a, d + 2 ), ( b, d + 2 ) ], 0, slope=[ L1 + 7, L2 ], clip_to=48, name="east steps rail n" )


# ---------------------------------------------------------------------------------------------------------------------
# The courtyard: the pool, the deck, the pylon, the planter, the grand stair

def pool( m, water ):
    p0, p1, n0, n1 = POOL
    k = 12.0
    kz = POOL_KERB
    for a, b, c, d in ( ( p0, p1, n0, n0 + k ), ( p0, p1, n1 - k, n1 ), ( p0, p0 + k, n0 + k, n1 - k ), ( p1 - k, p1, n0 + k, n1 - k ) ):
        solid( m, a, b, c, d, 0, kz - 1.5, { "default": "vr_stone_dark", "+z": None } )
        solid( m, a - 1.2, b + 1.2, c - 1.2, d + 1.2, kz - 1.5, kz, "vr_stone_dark" )
    # The LED strip in the shadow under the kerb's lip, all round outside.
    for a, b, out in ( ( ( p0 - 0.6, n0 - 0.6 ), ( p1 + 0.6, n0 - 0.6 ), ( 0, -1 ) ), ( ( p0 - 0.6, n1 + 0.6 ), ( p1 + 0.6, n1 + 0.6 ), ( 0, 1 ) ),
                       ( ( p0 - 0.6, n0 ), ( p0 - 0.6, n1 ), ( -1, 0 ) ), ( ( p1 + 0.6, n0 ), ( p1 + 0.6, n1 ), ( 1, 0 ) ) ):
        P.led( m, ( a[0], a[1], kz - 2.3 ), ( b[0], b[1], kz - 2.3 ), v( out[0], out[1], 0 ), 1.0 )
    floor( m, p0 + k, p1 - k, n0 + k, n1 - k, 0.2, "vr_black" )
    card( water, "vr_pool", [ v( p0 + k, n0 + k, WATER_Z ), v( p1 - k, n0 + k, WATER_Z ), v( p1 - k, n1 - k, WATER_Z ), v( p0 + k, n1 - k, WATER_Z ) ], UP )
    # The boulder in the middle and a lower one behind it with the water welling over it.
    P.boulder( m, ( 10.0, -40.0, 0.0 ), 46, seed=3, squash=0.62, paint="vr_rock_dark" )
    # A light under the water on the boulder, as in the picture.
    P.LIGHTS.append( ( "Pool light", ( 70.0, -60.0, WATER_Z - 4.0 ), P.WARM, 150, False ) )
    P.boulder( m, ( -55.0, 22.0, 0.0 ), 26, seed=4, squash=0.5, paint="vr_rock_dark" )
    for k_, n in enumerate( ( -70.0, 50.0 ) ):
        P.wall_washer( m, f"Pool kerb light {k_}", ( p1, n, 8.0 ), ( 1, 0 ), 160, light=( k_ == 0 ), size=( 5.0, 3.0 ), rise=8 )


def courtyard( m, foliage ):
    de0, de1, dn0, dn1, dz = DECK
    # The raised deck along the south side: 16 in up (one step), its lit nosing.
    solid( m, de0, de1, dn0, dn1, 0, dz - 1.5, { "default": "vr_stone", "+z": None, "-z": None, "-n": None, "-e": None } )
    solid( m, de0, de1 + 1.2, dn0, dn1 + 1.2, dz - 1.5, dz, { "default": "vr_stone_light", "-z": "vr_stone_light" } )
    floor( m, de0, de1, dn0, dn1, dz + 0.02, "vr_paving" )
    P.led( m, ( de0, dn1 + 0.5, dz - 2.6 ), ( de1, dn1 + 0.5, dz - 2.6 ), v( 0, 1, 0 ), 1.2 )
    P.led( m, ( de1 + 0.5, dn0, dz - 2.6 ), ( de1 + 0.5, dn1, dz - 2.6 ), v( 1, 0, 0 ), 1.2 )
    # The pylon.
    e0, e1, n0, n1, h = PYLON
    P.pylon( m, ( e0, n0 ), ( e1, n1 ), 0, h, "+e" )
    # The planter at the grand stair's foot with its uplit olive.
    a, b, c, d = PLANTER
    P.planter( m, ( a, c ), ( b, d ), 0, 46, sides=( "-e", ) )
    P.olive( foliage, ( ( a + b ) / 2 + 4, ( c + d ) / 2, 42 ), 180, seed=11, spread=1.0, cards=15, leaf_scale=0.72 )
    P.shrubs( foliage, ( a + 8, c + 8 ), ( b - 8, d - 8 ), 42, seed=12, kind="shrub", h=20 )
    P.uplight( m, "Planter olive uplight", ( ( a + b ) / 2 + 10, ( c + d ) / 2 - 10, 42.2 ), 190 )
    for k, n in enumerate( ( 220.0, 258.0 ) ):
        P.wall_washer( m, f"Planter step light {k}", ( b, n, 12.0 ), ( 1, 0 ), 120, size=( 7.0, 3.0 ), rise=-6, light=( k == 0 ) )
    # The grand stair, its lights in the north block's face beside the steps.
    e0, e1, fn, hn = STAIR
    P.stone_stair( m, ( ( e0 + e1 ) / 2, fn ), ( ( e0 + e1 ) / 2, hn ), e1 - e0, L0, L1, sides=( False, False ), name="grand stair" )
    steps = int( round( L1 / 7.4 ) )
    for i in range( 1, steps, 3 ):
        n = fn + ( hn - fn ) * ( i + 0.5 ) / steps
        z = L1 * ( i + 1 ) / steps + 9
        P.step_light( m, f"Grand stair light {i}", ( e0, n, z ), ( 1, 0 ), light=( i % 6 == 1 ) )
        P.step_light( m, f"Grand stair light east {i}", ( e1, n, z ), ( -1, 0 ), light=False )
    # The cases about the courtyard, as the picture has them.
    for k, e in enumerate( ( 20.0, 76.0, 132.0 ) ):
        P.hard_case( m, ( e, -232.0 ), ( 50, 32, 28 ), ( 1, 0.03 * ( k - 1 ) ), "vr_case_black" if k % 2 else "vr_case_olive", dz, seed=60 + k )
    P.case_stack( m, ( 195, 30 ), ( 0.1, 1 ), "vr_case_black", ( ( 44, 30, 28 ), ( 40, 28, 24 ) ), seed=64 )
    P.hard_case( m, ( 290, -110 ), ( 52, 34, 22 ), ( 1, -0.2 ), "vr_case_olive", 0, seed=65 )
    P.case_stack( m, ( 300, -262 ), ( 1, 0 ), "vr_case_black", ( ( 60, 40, 34 ), ( 52, 36, 26 ) ), seed=66, z0=dz )
    P.hard_case( m, ( 210, -270 ), ( 56, 36, 30 ), ( 0.2, 1 ), "vr_case_olive", dz, seed=67 )
    P.hard_case( m, ( -168, -120 ), ( 46, 28, 24 ), ( 0, 1 ), "vr_case_black", 0, seed=68 )
    P.case_stack( m, ( -165, 110 ), ( 0, 1 ), "vr_case_olive", ( ( 46, 28, 24 ), ), seed=69 )
    P.case_stack( m, ( 640, 120 ), ( 1, 0.2 ), "vr_case_black", ( ( 50, 32, 28 ), ( 44, 30, 22 ) ), seed=70 )
    # Wall washers along the courtyard's walls.
    P.wall_washer( m, "Court lamp east a", ( EAST_A[0], -80.0, 30.0 ), ( -1, 0 ), 260, rise=-10 )
    P.wall_washer( m, "Court lamp east b", ( EAST_A[0], 140.0, 30.0 ), ( -1, 0 ), 260, rise=-10 )
    P.wall_washer( m, "Apron lamp", ( 620.0, EAST_B[2], 30.0 ), ( 0, -1 ), 240, rise=-10 )
    P.wall_washer( m, "North face lamp", ( 60.0, NORTH[2], 60.0 ), ( 0, -1 ), 220 )


def resort_finish( m, foliage ):
    """Close-range architecture and planting, kept separate from the structural building mesh.

    The model is part of the colliding Dressing object. Only the roof pergola's
    posts need explicit hulls; wall trims, slatted soffits and leaf cards are
    visual detail. In particular, nothing crosses the lounge or cafe door cuts.
    """
    # Warm teak slats under the cafe's overhanging terrace. Each bay is recessed
    # behind the colonnade piers; the street-side portal remains 100 in clear.
    for n in np.arange( -158.0, 151.0, 18.0 ):
        box( m, CAFE_FRONT + 5.0, CAFE[1] - 22.0, n - 1.7, n + 1.7,
             105.2, 109.8, "vr_timber_dark" )
    # Fine black reveal lines and raised stone end caps give the upper facade
    # depth without adding opaque faces across its existing glazed openings.
    face = OPS_FACE
    for e in ( 56.0, 186.0, 458.0, 738.0 ):
        box( m, e - 2.6, e + 2.6, face + 1.0, face + 3.2,
             268.0, 386.0, "vr_stone_dark" )
        box( m, e - 1.1, e + 1.1, face + 3.3, face + 3.9,
             271.0, 383.0, "vr_steel" )
    for z in ( 265.0, 391.0 ):
        box( m, OPS[0] + 4, OPS[1] - 4, face + 1.2, face + 3.4,
             z - 1.6, z + 1.6, "vr_stone_dark" )
    # An actual rooftop shade structure over the west cafe's terrace, instead
    # of another featureless slab. It is open on all sides and clear above head height.
    pe0, pe1, pn0, pn1 = -680.0, -520.0, 88.0, 177.0
    top = 254.0
    for e in ( pe0, pe1 ):
        for n in ( pn0, pn1 ):
            box( m, e - 3.0, e + 3.0, n - 3.0, n + 3.0,
                 L1, top - 12.0, "vr_steel" )
            m.collision_box( ( e - 3, n - 3, L1 ), ( e + 3, n + 3, top - 12 ), METAL )
            box( m, e - 5.0, e + 5.0, n - 5.0, n + 5.0,
                 top - 17.0, top - 11.0, "vr_steel" )
    for n in ( pn0, pn1 ):
        box( m, pe0 - 8, pe1 + 8, n - 4, n + 4, top - 11, top - 2, "vr_timber_dark" )
    for e in np.arange( pe0 + 2, pe1, 14.0 ):
        box( m, e - 2.2, e + 2.2, pn0 - 6, pn1 + 6,
             top - 2, top + 4.0, "vr_timber_dark" )
    # Planters, climbers and warm practical lights soften the otherwise hard
    # resort geometry. Foliage stays above/along walls, clear of player routes.
    P.planter( m, ( -631.0, 129.0 ), ( -597.0, 163.0 ), L1, L1 + 21.0 )
    P.shrubs( foliage, ( -625.0, 135.0 ), ( -603.0, 157.0 ), L1 + 18.0,
              seed=810, kind="rosemary", h=25.0, count=5 )
    P.ivy( foliage, ( -592.0, 177.5, top + 2.0 ), ( 1, 0, 0 ), 88.0, 66.0,
           seed=811, off=2.6 )
    P.wall_washer( m, "Cafe rooftop pergola lamp", ( -598.0, 177.0, top - 18.0 ),
                   ( 0, -1 ), radius=190, size=( 13.0, 3.5 ), rise=-19.0 )
    # Coastal foliage grows along the retaining wall, away from the tunnel
    # opening at n=-260..-140 and away from the grand stair approach.
    P.shrubs( foliage, ( 740.0, 34.0 ), ( 753.0, 148.0 ), 0.0,
              seed=812, kind="rosemary", h=25.0, count=10 )
    P.ivy( foliage, ( 759.0, 74.0, 177.0 ), ( 0, -1, 0 ), 94.0, 66.0,
           seed=813, off=3.0 )


# ---------------------------------------------------------------------------------------------------------------------
# The east terrace (192) with the colonnade under it, the forecourt and the plaza

def east_terrace( m, g, foliage ):
    a0, a1, an0, an1 = EAST_A
    b0, b1, bn0, bn1 = EAST_B
    t0, t1, tn0, tn1 = TUNNEL
    # The podium: retaining walls round solid fill, the colonnade's passage through it.
    def faces( paint, shown, top=None, bottom=None ):
        out = { f: ( paint if f in shown else None ) for f in ( "+e", "-e", "+n", "-n" ) }
        out["+z"], out["-z"] = top, bottom
        return out

    # The fill under the terrace (0..176) in blocks, each showing only its outer faces; the slab on top (176..192)
    # with the paving and a dark coping edge where it shows.
    blocks = [ ( ( a0, a1, an0, tn0 ), ( "-e", "+e", "-n", "+n" ), ( "-e", "+e", "-n" ) ),
               ( ( a0, a1, tn1, an1 ), ( "-e", "+e", "-n" ), ( "-e", "+e" ) ),
               ( ( b0, a0, bn0, bn1 ), ( "-e", "-n" ), ( "-e", "-n" ) ),
               ( ( a0, b1, bn0, bn1 ), ( "+e", ), ( "+e", ) ) ]
    for ( e0, e1, n0, n1 ), fill_faces, slab_faces in blocks:
        solid( m, e0, e1, n0, n1, 0, L2 - SLAB, faces( "vr_stone", fill_faces ) )
        solid( m, e0, e1, n0, n1, L2 - SLAB, L2, faces( "vr_stone_dark", slab_faces, top=None ) )
        floor( m, e0, e1, n0, n1, L2, "vr_paving" )
    solid( m, a0, a1, tn0, tn1, L2 - SLAB, L2, faces( "vr_stone_dark", ( "-e", "+e" ), top=None ) )
    floor( m, a0, a1, tn0, tn1, L2, "vr_paving" )
    ceiling( m, t0, t1, tn0, tn1, TUNNEL_TOP - 0.1, "vr_concrete" )
    for k, e in enumerate( ( 840.0, 980.0, 1120.0 ) ):
        P.downlight( m, f"Colonnade downlight {k}", ( e, ( tn0 + tn1 ) / 2, TUNNEL_TOP - 0.2 ), 260 )
    for n in ( tn0, tn1 ):
        P.wall_washer( m, f"Colonnade mouth lamp {n}", ( a0, n + ( 12 if n == tn0 else -12 ), 120.0 ), ( -1, 0 ), 200, light=False )
    # The edge over the courtyard: black steel railing with a tarp thrown over it at the picture's corner, glass on.
    P.steel_rail( m, [ ( a0 + 2, an0 ), ( a0 + 2, -45.0 ) ], L2, name="east terrace steel rail", style="tube" )
    P.tarp_over( m, ( a0 + 2, -146.0 ), ( a0 + 2, -52.0 ), L2 + 42, ( -1, 0 ), drop_out=30, drop_in=27, seed=2, rail=1.5 )
    P.glass_rail( m, [ ( a0 + 2, -45.0 ), ( a0 + 2, an1 - 2 ), ( STAIR[1] + 1, an1 - 2 ), ( STAIR[1] + 1, EAST_STEPS[2] ) ], L2,
                  name="east terrace glass rail", cap=False )
    P.glass_rail( m, [ ( STAIR[1] + 1, EAST_STEPS[3] ), ( STAIR[1] + 1, EAST_B[3] - 2 ) ], L2, name="east terrace north rail" )
    # The far edges: east over the forecourt (gap at its stair), south over the plaza.
    fe, fh, fn0, fn1 = FORE_STAIR
    P.glass_rail( m, [ ( a1 - 2, an0 + 2 ), ( a1 - 2, fn0 ) ], L2, name="east edge rail a" )
    P.glass_rail( m, [ ( a1 - 2, fn1 ), ( a1 - 2, bn1 - 2 ) ], L2, name="east edge rail b" )
    P.glass_rail( m, [ ( BALCONY_STAIR[1], an0 + 2 ), ( a1 - 2, an0 + 2 ) ], L2, name="south edge rail" )
    # On top: cases (the picture's foreground), loungers, planters, lanterns.
    P.case_stack( m, ( 860, -330 ), ( 1, 0 ), "vr_case_black", ( ( 62, 40, 36 ), ( 54, 36, 28 ) ), seed=80, z0=L2 )
    P.hard_case( m, ( 860, -250 ), ( 60, 40, 34 ), ( 1, 0.1 ), "vr_case_black", L2, seed=81 )
    P.hard_case( m, ( 940, -380 ), ( 56, 36, 30 ), ( 0, 1 ), "vr_case_olive", L2, seed=82 )
    P.case_stack( m, ( 1100, 160 ), ( 0, 1 ), "vr_case_olive", seed=83, z0=L2 )
    P.case_stack( m, ( 640, 620 ), ( 1, 0 ), "vr_case_black", seed=84, z0=L2 )
    for k, n in enumerate( ( -100.0, 0.0, 100.0 ) ):
        P.lounger( m, ( 1060, n ), ( -1, 0 ), L2 )
    for k, ( e, n ) in enumerate( ( ( 1150, -380 ), ( 1150, 700 ), ( 560, 720 ) ) ):
        P.planter( m, ( e - 30, n - 30 ), ( e + 30, n + 30 ), L2, L2 + 26 )
        P.olive( foliage, ( e, n, L2 + 22 ), 120, seed=85 + k )
    for k, ( e, n ) in enumerate( ( ( 1140, -200 ), ( 1140, 300 ), ( 820, 500 ), ( 1000, 700 ) ) ):
        P.lantern_post( m, f"East terrace lantern {k}", ( e, n, L2 ), 96, radius=380 )
    P.lantern_post( m, "East terrace lantern near", ( 930.0, -150.0, L2 ), 96, radius=300 )
    # The forecourt stair up from the east.
    P.stone_stair( m, ( fe, ( fn0 + fn1 ) / 2 ), ( fh, ( fn0 + fn1 ) / 2 ), fn1 - fn0, L0, L2, sides=( True, True ), name="forecourt stair" )
    P.glass_rail( m, [ ( fe, fn0 - 2 ), ( fh, fn0 - 2 ) ], 0, slope=[ L0 + 7, L2 ], clip_to=48, name="forecourt stair rail s" )
    P.glass_rail( m, [ ( fe, fn1 + 2 ), ( fh, fn1 + 2 ) ], 0, slope=[ L0 + 7, L2 ], clip_to=48, name="forecourt stair rail n" )
    # Lamps on the east face and the plaza face.
    for n in ( -300.0, 100.0, 650.0 ):
        P.wall_washer( m, f"Forecourt wall lamp {n}", ( a1, n, 60.0 ), ( 1, 0 ), 280, rise=-10 )
    for e in ( 860.0, 1100.0 ):
        P.wall_washer( m, f"Plaza wall lamp {e}", ( e, an0, 60.0 ), ( 0, -1 ), 280, rise=-10 )
    P.letters( m, "logo", ( a1, -10.0, 120.0 ), ( 0, -1, 0 ), 50, "light" )
    P.letters( m, "veridant", ( a1, -10.0, 80.0 ), ( 0, -1, 0 ), 22, "light" )


def spa( m, g ):
    """ The spa along the north edge: closed, its south face over the terraces dressed with windows, its west face
    over the garden terrace. """
    e0, e1, n0, n1 = SPA
    solid( m, e0, e1, n0, n1, 0, SPA_TOP, { "default": "vr_stone", "+n": None, "-z": None } )
    solid( m, e0 - 6, e1 + 6, n0 - 6, n1 + 6, SPA_TOP, SPA_TOP + 14, "vr_stone_dark" )
    rng = np.random.default_rng( 3 )
    for e in np.arange( e0 + 100, e1 - 60, 160.0 ):
        for z0, z1 in ( ( 250, 360 ), ):
            box( m, e - 50, e + 50, n0 - 1.2, n0 - 0.4, z0, z1, "vr_window_lit" if rng.random() < 0.4 else "vr_window_dark" )
            box( m, e - 54, e + 54, n0 - 2.5, n0, z0 - 4, z0, "vr_stone_light" )
    for n in np.arange( n0 + 80, n1 - 40, 160.0 ):
        box( m, e0 - 1.2, e0 - 0.4, n - 50, n + 50, 200, 330, "vr_window_lit" if rng.random() < 0.5 else "vr_window_dark" )
    P.letters( m, "spa", ( 700.0, n0, 330.0 ), ( 1, 0, 0 ), 26, "dark" )
    for e in ( 100.0, 500.0, 900.0 ):
        P.wall_washer( m, f"Spa lamp {e}", ( e, n0, L2 + 70 ), ( 0, -1 ), 240 )
    P.wall_washer( m, "Spa west lamp", ( e0, 880.0, L1 + 80 ), ( -1, 0 ), 240 )


# ---------------------------------------------------------------------------------------------------------------------
# The promenade, the gardens, the forecourt, the boundaries

def promenade( m, foliage ):
    e0, e1, n0, n1 = PROM
    # The sea wall's balustrade: stone posts and a capping rail, clipped high.
    for n in np.arange( n0, n1 + 1, 60.0 ):
        box( m, SEA_WALL, SEA_WALL + 8, n - 4, n + 4, 0, 36, "vr_stone_light", STONE )
    box( m, SEA_WALL - 1, SEA_WALL + 9, n0, n1, 36, 41, "vr_stone_light", STONE )
    box( m, SEA_WALL, SEA_WALL + 8, n0, n1, 0, 6, "vr_stone_light", STONE )
    P.clip( "sea wall", ( SEA_WALL + 4, n0 ), ( SEA_WALL + 4, n1 ), 0, 1000, thick=8 )
    # Palms in two rows, lamp posts between, benches.
    rng = np.random.default_rng( 17 )
    for k, n in enumerate( np.arange( n0 + 120, n1, 300.0 ) ):
        P.palm( foliage, ( -1640.0 + rng.normal( 0, 8 ), n, 0 ), rng.uniform( 270, 350 ), seed=100 + k, lean=( rng.normal( 0, 30 ), rng.normal( 0, 30 ) ) )
        m.collision_box( ( -1652, n - 12, 0 ), ( -1628, n + 12, 300 ), WOOD )
        P.lantern_post( m, f"Promenade lamp {k}", ( -1690.0, n + 150, 0 ), 140, radius=480 )
        if k % 2 == 0:
            P.bench( m, ( -1600, n + 150 ), ( 0, 1 ), 72 )
    for k, n in enumerate( np.arange( n0 + 270, n1, 420.0 ) ):
        if 300 < n < 700:
            continue
        P.palm( foliage, ( -900.0, n, 0 ), rng.uniform( 290, 370 ), seed=200 + k, lean=( rng.normal( 0, 40 ), rng.normal( 0, 40 ) ) )
        m.collision_box( ( -912, n - 12, 0 ), ( -888, n + 12, 300 ), WOOD )
    # Cover: cases, a kiosk cart, planters.
    for k, ( e, n ) in enumerate( ( ( -1300, -800 ), ( -1150, -600 ), ( -1450, 650 ), ( -1180, 560 ), ( -1000, -1100 ), ( -1450, 850 ),
                                    ( -1000, 860 ) ) ):
        P.case_stack( m, ( e, n ), ( rng.normal( 0, 0.3 ), 1 ), "vr_case_black" if k % 2 else "vr_case_olive", seed=110 + k )
    for k, ( e, n ) in enumerate( ( ( -1100, -150 ), ( -1100, 250 ), ( -1300, -1150 ) ) ):
        P.planter( m, ( e - 40, n - 40 ), ( e + 40, n + 40 ), 0, 30 )
        P.olive( foliage, ( e, n, 26 ), 130, seed=120 + k )
    # The promenade stair up to the garden terrace, against its west face, and its landing.
    a, b, fn, hn = PROM_STAIR
    P.stone_stair( m, ( ( a + b ) / 2, fn ), ( ( a + b ) / 2, hn ), b - a, L0, L1, sides=( False, True ), name="promenade stair" )
    P.glass_rail( m, [ ( a - 1, fn ), ( a - 1, hn ) ], 0, slope=[ L0 + 7, L1 ], clip_to=48, name="promenade stair rail" )
    la, lb, ln0, ln1 = PROM_LANDING
    solid( m, la, lb, ln0, ln1, 0, L1, { "default": "vr_stone", "+z": "vr_paving", "+e": None } )
    P.glass_rail( m, [ ( la - 1, ln0 ), ( la - 1, ln1 + 1 ), ( lb, ln1 + 1 ) ], L1, name="promenade landing rail" )
    P.wall_washer( m, "Promenade stair lamp", ( GARDEN[0], 470.0, 60.0 ), ( -1, 0 ), 240 )
    P.letters( m, "terrace", ( GARDEN[0], 700.0, 90.0 ), ( 0, -1, 0 ), 16, "light" )
    # Boundaries: the north wall and gate, the cafe's and lounge's lamps over the promenade.
    solid( m, e0, e1, n1, n1 + 24, 0, 120, "vr_stone" )
    P.clip( "promenade north", ( e0, n1 + 12 ), ( e1, n1 + 12 ), 0, 1000, thick=24 )
    for n in ( -400.0, -80.0, 100.0 ):
        P.wall_washer( m, f"West face lamp {n}", ( CAFE[0] if n > -180 else LOUNGE[0], n, 100.0 ), ( -1, 0 ), 280, rise=-20 )


def gardens( m, foliage ):
    """ The gardens south of the operations building: olive groves in gravel beds, box hedges, a stone wall along
    the south edge with cypresses behind, a pergola, cases. Bomb site B at their east end. """
    g0, g1, n0, n1 = GARDEN_S
    rng = np.random.default_rng( 31 )
    # The south wall.
    solid( m, PLAY[0], PLAY[1], n0 - 24, n0, 0, 110, "vr_stone" )
    P.clip( "south wall", ( PLAY[0], n0 - 12 ), ( PLAY[1], n0 - 12 ), 0, 1000, thick=24 )
    # Box hedges along the paths (low cover), olive groves.
    for a, b, c, d in ( ( -680, -60, -980, -940 ), ( 40, 96, -980, -940 ), ( 344, 520, -980, -940 ), ( 660, 1180, -980, -940 ), ( -680, -60, -1110, -1070 ),
                        ( 660, 1200, -1110, -1070 ), ( 1340, 1860, -980, -940 ), ( 1340, 1860, -1110, -1070 ) ):
        box( m, a, b, c, d, 0, 36, "vr_hedge", FABRIC )
    for k in range( 28 ):
        e = rng.uniform( g0 + 60, g1 - 60 )
        n = rng.uniform( n0 + 60, n1 - 60 )
        if -900 < n < -800 or -1240 < n < -1150:
            continue
        if any( a - 20 < e < b + 20 and c - 20 < n < d + 20 for a, b, c, d in ( ( -40, 20, n0, n1 ), ( 560, 620, n0, n1 ), ( 1240, 1300, n0, n1 ) ) ):
            continue
        P.olive( foliage, ( e, n, 0 ), rng.uniform( 150, 230 ), seed=300 + k, spread=1.2 )
        m.collision_box( ( e - 7, n - 7, 0 ), ( e + 7, n + 7, 110 ), WOOD )
    # A stone pavilion in the middle of the gardens, open north and south, closed east and west: it breaks the long
    # look along them.
    pv0, pv1, pn0, pn1 = 120.0, 320.0, -1180.0, -940.0
    wall( m, "n", ( pn0, pn1 ), ( pv0, pv0 + T ), ( 0, 140 ), "-e", outside="vr_stone", inside="vr_stone" )
    wall( m, "n", ( pn0, pn1 ), ( pv1 - T, pv1 ), ( 0, 140 ), "+e", outside="vr_stone", inside="vr_stone" )
    for nn, out in ( ( pn0, "-n" ), ( pn1 - T, "+n" ) ):
        wall( m, "e", ( pv0 + T, pv1 - T ), ( nn, nn + T ), ( 0, 140 ), out, [ ( ( pv0 + pv1 ) / 2, 90.0, 0, 110 ) ], outside="vr_stone", inside="vr_stone" )
    solid( m, pv0 - 10, pv1 + 10, pn0 - 10, pn1 + 10, 140, 152, { "default": "vr_stone_dark", "-z": "vr_soffit" } )
    floor( m, pv0 + T, pv1 - T, pn0 + T, pn1 - T, 0.2, "vr_floor" )
    P.cafe_table( m, ( ( pv0 + pv1 ) / 2, ( pn0 + pn1 ) / 2 ), 0, 3, seed=35 )
    P.downlight( m, "Pavilion light", ( ( pv0 + pv1 ) / 2, ( pn0 + pn1 ) / 2, 140 ), 280 )
    for nn in ( pn0, pn1 ):
        P.wall_washer( m, f"Pavilion lamp {nn}", ( ( pv0 + pv1 ) / 2 + 60, nn, 100.0 ), ( 0, 1 if nn > pn0 else -1 ), 220 )
    ROOF_EXTRA.append( ( "Pavilion", ( pv0 - 10, pv1 + 10, pn0 - 10, pn1 + 10, 140, 1500 ) ) )
    # Tall clipped hedges: solid cover.
    for a, b, c, d in ( ( -600, -380, -900, -870 ), ( -260, -60, -900, -870 ), ( 1240, 1300, -1300, -1140 ), ( 1240, 1300, -1000, -840 ),
                        ( -560, -520, -1320, -1240 ) ):
        box( m, a, b, c, d, 0, 92, "vr_hedge", STONE )
    # A pergola with a table under it in the west part.
    for e in ( -560.0, -360.0 ):
        for n in ( -1300.0, -1180.0 ):
            box( m, e - 4, e + 4, n - 4, n + 4, 0, 110, "vr_timber_dark", WOOD )
    for n in ( -1300.0, -1180.0 ):
        box( m, -570, -350, n - 4, n + 4, 110, 118, "vr_timber_dark" )
    for e in np.arange( -568, -350, 16.0 ):
        box( m, e - 1.5, e + 1.5, -1310, -1170, 118, 122, "vr_timber_dark" )
    P.bougainvillea( foliage, ( -460.0, -1176.0, 120.0 ), ( 1, 0, 0 ), 200, 60, seed=5 )
    P.cafe_table( m, ( -460, -1240 ), 0, 4, seed=33 )
    # Cover on site B and round it.
    for k, ( e, n ) in enumerate( ( ( 600, -1020 ), ( 780, -900 ), ( 900, -1150 ), ( 480, -1200 ), ( 1000, -860 ), ( 700, -1250 ) ) ):
        P.case_stack( m, ( e, n ), ( 1, rng.normal( 0, 0.3 ) ), "vr_case_olive" if k % 2 else "vr_case_black", seed=320 + k )
    for k, ( e, n ) in enumerate( ( ( -400, -1020 ), ( 200, -1250 ), ( 1500, -1020 ), ( 1700, -1250 ), ( -200, -820 ) ) ):
        P.case_stack( m, ( e, n ), ( 1, 0 ), "vr_case_black", seed=340 + k )
    for k, ( e, n ) in enumerate( ( ( -300, -760 ), ( 300, -760 ), ( 900, -760 ), ( 1500, -800 ), ( -600, -1300 ), ( 1100, -1300 ) ) ):
        P.lantern_post( m, f"Garden lamp {k}", ( e, n, 0 ), 120, radius=460 )


def forecourt( m, foliage ):
    """ The entrance forecourt (Blue Team's spawn) and the plaza: palms in planters, a fountain, the boundary wall
    with its closed gates, cases. """
    f0, f1, n0, n1 = FORE
    rng = np.random.default_rng( 41 )
    solid( m, PLAY[1], PLAY[1] + 24, PLAY[2], PLAY[3], 0, 120, "vr_stone" )
    P.clip( "east wall", ( PLAY[1] + 12, PLAY[2] ), ( PLAY[1] + 12, PLAY[3] ), 0, 1000, thick=24 )
    solid( m, f0, f1, n1, n1 + 24, 0, 120, "vr_stone" )
    P.clip( "forecourt north", ( f0, n1 + 12 ), ( f1, n1 + 12 ), 0, 1000, thick=24 )
    # The gates in the east wall: dark steel leaves, closed, lamps either side.
    for n in ( -300.0, 500.0 ):
        box( m, PLAY[1] - 1, PLAY[1], n - 90, n + 90, 0, 110, "vr_steel" )
        for sn in ( -1, 1 ):
            box( m, PLAY[1] - 14, PLAY[1] + 24, n + sn * 100 - 14, n + sn * 100 + 14, 0, 150, "vr_stone_dark", STONE )
            P.lantern_post( m, f"Gate lamp {n} {sn}", ( PLAY[1] - 6, n + sn * 100, 150 ), 30, radius=360 )
    # The fountain: a round basin with a stone bowl, water in it.
    c = ( 1600.0, 150.0 )
    P.cylinder( m, c, 90, 0, 20, "vr_stone_dark", 32, top=None, surface=STONE )
    P.cylinder( m, c, 84, 0.2, 14, "vr_black", 32, top="vr_black" )
    P.lathe( m, c, [ ( 10, 14 ), ( 10, 46 ), ( 34, 52 ), ( 30, 58 ), ( 0, 56 ) ], "vr_stone", 20 )
    for k in range( 8 ):
        a = 2 * math.pi * k / 8
        P.uplight( m, f"Fountain light {k}", ( c[0] + 76 * math.cos( a ), c[1] + 76 * math.sin( a ), 14 ), 160, light=( k % 4 == 0 ) )
    # Palms in square planters, cases, benches.
    for k, ( e, n ) in enumerate( ( ( 1350, -560 ), ( 1350, 820 ), ( 1800, -560 ), ( 1800, 820 ), ( 1350, 140 ) ) ):
        P.planter( m, ( e - 36, n - 36 ), ( e + 36, n + 36 ), 0, 28 )
        P.palm( foliage, ( e, n, 24 ), rng.uniform( 300, 380 ), seed=400 + k, lean=( rng.normal( 0, 30 ), rng.normal( 0, 30 ) ) )
    for k, ( e, n ) in enumerate( ( ( 1500, -200 ), ( 1700, 450 ), ( 1450, 650 ), ( 1250, -620 ), ( 1050, -560 ), ( 900, -640 ) ) ):
        P.case_stack( m, ( e, n ), ( 1, rng.normal( 0, 0.2 ) ), "vr_case_black" if k % 2 else "vr_case_olive", seed=420 + k )
    for k, ( e, n ) in enumerate( ( ( 1500, -640 ), ( 1500, 950 ), ( 1820, 150 ) ) ):
        P.lantern_post( m, f"Forecourt lamp {k}", ( e, n, 0 ), 140, radius=520 )


# ---------------------------------------------------------------------------------------------------------------------
# Probes and haze

def probes():
    return [
        ( "Courtyard", ( 280, -60, 200 ), ( COURT[0], COURT[1], COURT[2], APRON[3], -10, 500 ) ),
        ( "Cafe", ( -480, 10, 60 ), ( CAFE[0], CAFE_FRONT, CAFE[2], CAFE[3], 0, 112 ) ),
        ( "Lounge Down", ( -460, -380, 60 ), ( LOUNGE[0], LOUNGE[1], LOUNGE[2], LOUNGE[3], 0, 112 ) ),
        ( "Lounge Up", ( -460, -380, 190 ), ( LOUNGE[0], LOUNGE[1], LOUNGE[2], LOUNGE[3], 128, 256 ) ),
        ( "Hall", ( 280, -510, 60 ), ( OPS[0], OPS[1], OPS[2], OPS[3], 0, 112 ) ),
        ( "Lobby", ( 440, -560, 190 ), ( LOBBY[0], LOBBY[1], LOBBY[2], LOBBY[3], 128, 240 ) ),
        ( "Reception", ( 60, 380, 60 ), ( ROOM[0], ROOM[1], ROOM[2], ROOM[3], 0, ROOM_TOP ) ),
        ( "Colonnade", ( 980, -200, 90 ), ( TUNNEL[0], TUNNEL[1], TUNNEL[2], TUNNEL[3], 0, TUNNEL_TOP ) ),
        ( "Outside", ( 0, -150, 400 ), ( -40000, 40000, -40000, 40000, -500, 9000 ) ),
    ]


HAZE = [ ( "Bay Haze", ( -6000, 6000, -6000, 6000, -420, 1400 ), 0.05, "1,0.78,0.62,1" ) ]


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( e, n, 0 ) for e in ( -1500, -1340, -1180 ) for n in ( -300, -100, 100, 300 ) ]
BLUE_SPAWNS = [ ( e, n, 0 ) for e in ( 1580, 1720, 1840 ) for n in ( -420, -260, 360, 620 ) ]
RED_BUY = ( -1750, -950, -700, 700, -10, 260 )
BLUE_BUY = ( 1250, 1900, -700, 900, -10, 260 )

DM_SPAWNS = [ ( -1200, -900, 0 ), ( -1400, 650, 0 ), ( -1000, 100, 0 ), ( -480, -40, 0 ), ( -560, 90, 0 ), ( -450, -400, 0 ),
              ( -540, -260, L1 ), ( -560, 50, L1 ), ( -560, 700, L1 ), ( -400, 900, L1 ), ( 0, 300, 0 ), ( 100, 480, 0 ),
              ( -140, 640, L1 ), ( 100, 330, L1 ), ( 240, 580, L1 ), ( 640, 520, L2 ), ( 1000, -200, L2 ), ( 1000, 400, L2 ),
              ( -160, 170, 0 ), ( 400, 40, 0 ), ( 620, -100, 0 ), ( 160, -280, DECK[4] ), ( 0, -440, 0 ), ( 450, -460, 0 ),
              ( 300, -560, L1 ), ( 600, -380, L1 ), ( -100, -380, L1 ), ( 960, -200, 0 ), ( 980, -560, 0 ), ( 1450, 0, 0 ),
              ( 1700, 760, 0 ), ( 1650, -560, 0 ), ( -440, -1000, 0 ), ( 450, -1150, 0 ), ( 1000, -1000, 0 ), ( 1600, -1200, 0 ) ]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", -200, 380, 480, 760, L1 ),
               ( "bombsite_b", "Bomb Site B", 380, 1100, -1300, -780, L0 ) ]

RETAKES = {
    "bombsite_a": { "planter": [ ( -150, 560, L1 ), ( 130, 600, L1 ) ],
                    "defender": [ ( -560, 500, L1 ), ( -400, 880, L1 ), ( 100, 330, L1 ) ],
                    "attacker": [ ( 1600, -300, 0 ), ( 1700, 500, 0 ), ( 980, -200, 0 ), ( 300, -600, 0 ), ( 1450, -560, 0 ), ( 1550, 800, 0 ) ] },
    "bombsite_b": { "planter": [ ( 700, -1020, 0 ), ( 820, -1230, 0 ) ],
                    "defender": [ ( 1050, -1250, 0 ), ( 500, -1250, 0 ), ( 950, -850, 0 ) ],
                    "attacker": [ ( -1000, -200, 0 ), ( -1100, 0, 0 ), ( 100, 400, 0 ), ( 980, -200, 0 ), ( 400, -100, 0 ), ( -480, 0, 0 ) ] },
}

DOMINATION = [ ( "A", ( -480, -40, 0 ) ), ( "B", ( 400, -80, 0 ) ), ( "C", ( 1000, 100, L2 ) ) ]
HOT_ZONES = [ ( "Cafe", ( -480, -40, 0 ) ), ( "Courtyard", ( 400, -80, 0 ) ), ( "North Terrace", ( 120, 500, L1 ) ),
              ( "Gardens", ( 220, -990, 0 ) ), ( "Gallery", ( -460, -380, L1 ) ), ( "East Terrace", ( 1000, 100, L2 ) ) ]
CASH_POINTS = [ ( "Courtyard", ( 400, -80, 0 ), ( 120, 500, L1 ) ), ( "Gardens", ( 220, -990, 0 ), ( -460, -380, L1 ) ),
                ( "Terrace", ( 120, 500, L1 ), ( 220, -990, 0 ) ) ]


def callouts():
    return [ ( "PROMENADE", PROM[0], PROM[1], PROM[2], PROM[3], -10, 600 ), ( "FORECOURT", FORE[0], FORE[1], FORE[2], FORE[3], -10, 600 ),
             ( "CAFE", CAFE[0], CAFE[1], CAFE[2], CAFE[3], -10, 120 ), ( "CAFE TERRACE", CAFE[0], CAFE[1], CAFE[2], CAFE[3], 120, 400 ),
             ( "GARDEN TERRACE", GARDEN[0], GARDEN[1], GARDEN[2], GARDEN[3], 100, 400 ), ( "LOUNGE", LOUNGE[0], LOUNGE[1], LOUNGE[2], LOUNGE[3], -10, 120 ),
             ( "GALLERY", LOUNGE[0], LOUNGE[1], LOUNGE[2], LOUNGE[3], 120, 280 ), ( "HALL", OPS[0], OPS[1], OPS[2], OPS[3], -10, 120 ),
             ( "LOBBY", LOBBY[0], LOBBY[1], LOBBY[2], LOBBY[3], 120, 260 ), ( "BALCONY", OPS[0], OPS[1], OPS_FACE, OPS[3], 120, 400 ),
             ( "POOL", COURT[0], COURT[1], COURT[2], COURT[3], -10, 120 ), ( "STAIRS", STAIR[0], APRON[1], APRON[2], STAIR[3], -10, 130 ),
             ( "RECEPTION", NORTH[0], NORTH[1], NORTH[2], NORTH[3], -10, 120 ), ( "A SITE", NORTH[0], SLOT_TOP[1], NORTH[2], NORTH[3], 120, 600 ),
             ( "EAST TERRACE", EAST_A[0], EAST_A[1], EAST_A[2], EAST_B[3], 180, 600 ), ( "COLONNADE", TUNNEL[0], TUNNEL[1], TUNNEL[2], TUNNEL[3], -10, 180 ),
             ( "PLAZA", PLAZA[0], PLAZA[1], PLAZA[2], PLAZA[3], -10, 400 ), ( "B SITE", 380, 1100, -1350, -700, -10, 400 ),
             ( "GARDENS", GARDEN_S[0], 380, GARDEN_S[2], GARDEN_S[3], -10, 400 ), ( "EAST GARDENS", 1100, GARDEN_S[1], GARDEN_S[2], GARDEN_S[3], -10, 400 ) ]


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

MINIMAP_CENTRE = ( 75.0, -175.0 )
MINIMAP_SIZE = 3900.0
MINIMAP_PIXELS = 1024


def write_minimap( models ):
    """ Railhead's radar style: where you can walk grey, low cover darker, buildings clear, the terraces lighter, a
    light line round the edges, the pool blue. North up. """
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
        elif 110 <= z1 <= 200 and z1 - z0 > 100:
            draws["upper"].polygon( screen, fill=255 )
        elif z0 < 72 and z1 > 18:
            draws["low" if z1 < 100 else "tall"].polygon( screen, fill=255 )
    walk, low, tall, upper = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "low", "tall", "upper" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    E, N = np.meshgrid( cols, rows )
    inside = ( E > PLAY[0] ) & ( E < PLAY[1] ) & ( N > PLAY[2] ) & ( N < PLAY[3] )
    pool = ( E > POOL[0] ) & ( E < POOL[1] ) & ( N > POOL[2] ) & ( N < POOL[3] )
    walk &= inside
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[upper & inside] = ( 128, 132, 138, 235 )
    image[low & inside] = ( 64, 68, 74, 235 )
    image[tall & ~upper] = ( 0, 0, 0, 0 )
    image[pool] = ( 40, 92, 110, 220 )
    shown = ( walk | ( low & inside ) | ( upper & inside ) ) & ~( tall & ~upper )
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
    """ A TeamSpawnPoint facing the map's middle (the courtyard). """
    yaw = K.plan_yaw( ( 250 - position[0], ( -100 - position[1] ) * 0.5 ) )
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
    ( "veridant_ground", "Ground", True, True ), ( "veridant_buildings", "Buildings", True, True ),
    ( "veridant_dress", "Dressing", True, True ), ( "veridant_foliage", "Foliage", False, True ),
    ( "veridant_glass", "Glass", True, False ), ( "veridant_water", "Pool Water", False, False ),
    ( "veridant_sea", "Sea", False, False ), ( "veridant_backdrop", "Backdrop", False, False ),
    ( "veridant_backdrop_props", "Backdrop Props", False, False ),
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
    far = name == "Outside"
    return K.game_object( ids, f"Probe {name}", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", Bounds={ "Mins": K.vec( lo ), "Maxs": K.vec( hi ) },
                     DelayBetweenUpdates=0.1, Feathering=0.04, FrameInterval=5, MaxDistance=512, Projection="Box",
                     RenderDynamically=True, TintColor="1,1,1,1", UpdateStrategy="OnEnabled", ZFar=60000 if far else 8192,
                     ZNear=8, **( { "Priority": 0 } if far else { "Priority": 1 } ) ) ] )


def look_object():
    """ A sunset look: ambient occlusion, a light vignette, bloom for the lamps and the sun's glare, screen-space
    reflections for the wet paving and the glass, and the exposure held at 2.1-2.4, which veridant_sky is baked for. """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.8, Radius=110,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.2, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Bloom", "look/bloom", **{ "__version": 1 }, Mode="Additive", Strength=0.22, Threshold=1.5,
                     Tint="1,0.94,0.86,1" ),
        K.component( ids, "Sandbox.ScreenSpaceReflections", "look/ssr" ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=2.1, MaximumExposure=2.4,
                     Mode="ACES", Rate=1 ),
    ] )


def haze_object( name, box_, strength, colour ):
    e0, e1, n0, n1, z0, z1 = box_
    at = K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) )
    half = ( ( n1 - n0 ) / 2, ( e1 - e0 ) / 2, ( z1 - z0 ) / 2 )
    key = f"haze/{name}"
    return K.game_object( ids, name, key, at, components=[
        K.component( ids, "Sandbox.VolumetricFogVolume", f"{key}/volume", Bounds={ "Mins": K.vec( tuple( -h for h in half ) ), "Maxs": K.vec( half ) },
                     FalloffExponent=1, Strength=strength, Color=colour ) ] )


ROOF_CLIPS = []
ROOF_EXTRA = []


def roof_clips():
    return [ ( "Lounge", ( LOUNGE[0] - 24, LOUNGE[1] + 24, LOUNGE[2] - 24, LOUNGE[3] + 24, LOUNGE_TOP - 16, 1500 ) ),
             ( "Ops", ( OPS[0], OPS[1], OPS[2], OPS_FACE, OPS_TOP, 1500 ) ),
             ( "Spa", ( SPA[0], SPA[1], SPA[2], SPA[3], SPA_TOP, 1500 ) ),
             ( "Kiosk", ( -464.0, -316.0, -94.0, 74.0, L1 + 84, 1500 ) ),
             ( "Pylon", ( PYLON[0], PYLON[1], PYLON[2], PYLON[3], PYLON[4] - 4, 1500 ) ),
             ( "Promenade north", ( PROM[0], PROM[1], PROM[3], PROM[3] + 24, 120, 1500 ) ) ] + list( ROOF_EXTRA )


def write_scene( written, light_list, probe_list ):
    world = K.game_object( ids, "Veridant", "world", children=[
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

    buy_zones = [
        zone_object( "buyzone_t", "buy/t", RED_BUY, "1,0.18,0.2,1", "Red Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/t/zone_buy", Team="Terrorist" ) ] ),
        zone_object( "buyzone_ct", "buy/ct", BLUE_BUY, "0,0.41569,1,1", "Blue Team Buy Zone",
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
    # A clip's box runs along its rail: rotated to the rail's heading, its length on its own x (checked in the engine on
    # 2026-10-15: with the length on y, as Riverdale and Riverside write it, the box lay across the rail instead).
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
                         Description="A Mediterranean cliffside resort at sunset after rain: a wet courtyard round its "
                                     "reflecting pool, travertine terraces, a colonnaded cafe and a gallery lounge, and the "
                                     "bay beyond with a superyacht and a hilltop village on the headland.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 2500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # The sun on the horizon, 23 degrees north of west: deep orange, raking across the courtyard.
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor=SUN_COLOUR, ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.42,0.40,0.50,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            # The sky reads about a fifth darker in the engine than veridant_sky's own preview (the fog over it):
            # brought back up here rather than in the bake.
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="1.32,1.32,1.32,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.74", StartDistance=2500,
                         EndDistance=48000, FalloffExponent=1.0, Height=9000, VerticalFalloffExponent=1.2 ),
        ] ),
        look_object(),
        world,
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in probe_list ] ),
        K.game_object( ids, "Volumetric Fog", "haze", children=[ haze_object( *h ) for h in HAZE ] ),
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
    from map_daylight import apply_profile
    apply_profile( scene )
    SCENE_FILE.parent.mkdir( parents=True, exist_ok=True )
    K.write_text( SCENE_FILE, json.dumps( scene, indent=2 ), newline=None )
    print( f"wrote {SCENE_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------

def build( backdrop=True ):
    """ Every model by name. """
    P.reset()
    ROOF_EXTRA.clear()
    ground_m = ground()
    buildings, dress, foliage, glass, water = K.Model(), K.Model(), K.Model(), K.Model(), K.Model()
    lounge( buildings, glass )
    cafe( buildings, glass )
    roof_terrace( dress, glass, foliage )
    ops( buildings, glass, foliage )
    north_block( buildings, glass, foliage )
    pool( dress, water )
    courtyard( dress, foliage )
    resort_finish( dress, foliage )
    east_terrace( buildings, glass, foliage )
    spa( buildings, glass )
    promenade( dress, foliage )
    gardens( dress, foliage )
    forecourt( dress, foliage )
    models = { "veridant_ground": ground_m, "veridant_buildings": buildings, "veridant_dress": dress, "veridant_foliage": foliage,
               "veridant_glass": glass, "veridant_water": water }
    if backdrop:
        import veridant_backdrop as BD
        far, sea, _, props = BD.build()
        models["veridant_backdrop"] = far
        models["veridant_backdrop_props"] = props
        models["veridant_sea"] = sea
    for model in models.values():
        configure( model )
    ROOF_CLIPS[:] = roof_clips()
    return models


def preview_setup():
    """ The flat preview's colours, sun, sky and fog. """
    PV.is_glass = lambda paint: paint in GLASS_PAINTS
    for paint in VM.all_paints():
        if paint in VM.PAINTED:
            PV._colours[paint] = np.array( VM.PAINTED[paint][0] ) / 255.0
            continue
        for ext in ( "jpg", "png" ):
            path = VM.OUT_DIR / f"{paint}_color.{ext}"
            if path.exists():
                small = Image.open( path ).convert( "RGB" ).resize( ( 64, 32 ) )
                PV._colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
                break
    PV._colours["vr_letters_dark"] = np.array( ( 0.05, 0.05, 0.05 ) )
    PV._colours["vr_letters_light"] = np.array( ( 0.85, 0.85, 0.83 ) )
    PV._colours["vr_sea"] = np.array( ( 0.20, 0.22, 0.28 ) )
    PV._colours["vr_pool"] = np.array( ( 0.10, 0.11, 0.13 ) )
    PV._colours["vr_foliage"] = np.array( ( 0.30, 0.36, 0.24 ) )
    PV._colours["vr_print"] = np.array( ( 0.20, 0.20, 0.22 ) )
    PV._colours["vr_cliff_far"] = PV._colours.get( "vr_cliff", np.array( ( 0.6, 0.6, 0.6 ) ) ) * 0.54
    PV._colours["vr_glass"] = np.array( ( 0.45, 0.52, 0.56 ) )
    PV._colours["vr_glass_clear"] = np.array( ( 0.55, 0.62, 0.66 ) )
    PV.GLOWING = { "vr_led", "vr_led_soft", "vr_lamp", "vr_bulb", "vr_window_lit", "vr_village_lit", "vr_yacht_lit", "vr_beacon_red" }
    p, y = math.radians( SUN_PITCH ), math.radians( SUN_YAW )
    world = np.array( ( math.cos( p ) * math.cos( y ), math.cos( p ) * math.sin( y ), -math.sin( p ) ) )
    PV.SUN = -np.array( ( -world[1], world[0], world[2] ) )
    PV.SKY = ( np.array( ( 0.95, 0.72, 0.58 ) ), np.array( ( 0.40, 0.42, 0.56 ) ) )
    PV.FOG = np.array( ( 0.90, 0.72, 0.62 ) )


def hero_target():
    eye, yaw, pitch, _ = HERO
    # Plan: world yaw 90 (west) is plan -e.
    yr, pr = math.radians( yaw ), math.radians( pitch )
    world = v( math.cos( pr ) * math.cos( yr ), math.cos( pr ) * math.sin( yr ), math.sin( pr ) )
    plan = v( -world[1], world[0], world[2] )
    return v( *eye ) + plan * 1000


VIEWS = ( ( "reference", HERO[0], tuple( hero_target() ), HERO[3] ),
          ( "aerial", ( 2600.0, -3600.0, 3200.0 ), ( -100.0, -100.0, 0.0 ), 60 ),
          ( "promenade", ( -1500.0, -900.0, 64.0 ), ( -1300.0, 600.0, 120.0 ), 80 ),
          ( "north_terrace", ( 300.0, 300.0, 256.0 ), ( -200.0, 700.0, 260.0 ), 80 ),
          ( "gardens", ( 1600.0, -1000.0, 64.0 ), ( 0.0, -1000.0, 80.0 ), 80 ),
          ( "forecourt", ( 1800.0, -500.0, 64.0 ), ( 1200.0, 300.0, 150.0 ), 80 ),
          ( "courtyard", ( -150.0, -250.0, 80.0 ), ( 600.0, 200.0, 100.0 ), 80 ),
          ( "red_spawn", ( -1450.0, 0.0, 64.0 ), ( -3200.0, -2600.0, 260.0 ), 90 ),
          ( "sea", ( -1650.0, 200.0, 100.0 ), ( -6000.0, 1200.0, 40.0 ), 80 ) )


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
    parser.add_argument( "--no-backdrop", action="store_true", help="leave the backdrop out (quicker checks)" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture" )
    args = parser.parse_args()

    missing = [ p for p in VM.all_paints() if not ( VM.OUT_DIR / f"{p}.vmat" ).exists() ]
    if missing:
        print( f"run Tools/veridant_materials.py first: no material for {', '.join( missing )}" )
    models = build( not args.no_backdrop )
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
    if args.no_backdrop:
        written |= { "veridant_backdrop", "veridant_backdrop_props", "veridant_sea" }
    if UNKNOWN:
        print( f"paints with no material: {', '.join( sorted( UNKNOWN ) )}" )
    light_list = list( P.LIGHTS )
    probe_list = probes()
    print( f"{len( light_list )} lights ({sum( 1 for l in light_list if l[4] )} shadowed), {len( probe_list )} probes, "
           f"{len( P.CLIPS ) + len( ROOF_CLIPS )} clips" )

    solid_models = [ models[name] for name, _, collide, _ in SCENE_MODELS if collide and name in models ]
    print( "checking spots:" )
    problems = R.check_spots( R.collision_aabbs( solid_models ), all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    out = Path( args.preview ) if args.preview else None
    if out:
        out.mkdir( parents=True, exist_ok=True )
    bounds = ( PLAY[0], PLAY[1], PLAY[2], PLAY[3] )
    cut_off = R.check_reach( solid_models, all_spots(), out / "reach.png" if out else None, bounds=bounds )
    print( f"  {cut_off} spot(s) cut off from the spawns" )
    seen = R.check_retakes_sight( R.Blockers( solid_models ), RETAKES )
    print( f"  {seen} Retakes pair(s) in sight of each other" )

    if not args.no_scene:
        write_minimap( solid_models )
        write_scene( written, light_list, probe_list )
    if args.art:
        write_map_art( list( models.values() ) )
    if out:
        preview_setup()
        opaque, glass = PV.triangles( list( models.values() ) ), PV.triangles( list( models.values() ), glass=True )
        for name, eye, target, fov in VIEWS:
            if args.views and name not in args.views:
                continue
            size = ( 1152, 768 ) if name == "reference" else ( 960, 540 )
            PV.perspective( opaque, glass, eye, target, size=size, fov=fov ).convert( "RGB" ).save( out / f"{name}.png" )
            print( f"wrote {out / f'{name}.png'}" )


if __name__ == "__main__":
    main()
