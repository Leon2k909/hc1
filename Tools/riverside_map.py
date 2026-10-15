"""
Riverside: a Florida trailer park on a river at night, overrun. A Zombies map built by script like Riverdale and the
other maps (map_kit's boxes and polygons), dressed after the user's reference picture: from the entrance pad you look
down a muddy lane past the RIVERSIDE TRAILER PARK sign and a trailer strung with lights to the LUCKY STOP, with burning
drums, a wrecked pickup, a boarded-up camper, a guard tower's searchlight, a water tower and a full moon over the pines.

    python Tools/riverside_map.py [--preview <dir>] [--views name ...] [--no-scene] [--no-models] [--art]

Run Tools/riverside_materials.py and Tools/riverside_sky.py first. Riverside Trailer Park, the Lucky Stop and every
sign and slogan are the map's own. Writes:
- the models, to Assets/models/maps/riverside/: the ground (the pad, the terrace, the park's flats, the levee, the
  ramps, the retaining walls of railroad ties, the river and the woods' floor), the lowland's trailers, the levee's
  trailers, the store, the pad's dressing, the park's dressing (signs, poles and wires, drums, vehicles, props), the
  fence, the trees, and the backdrop (the far woods and the water tower; drawn only);
- the scene, Assets/scenes/maps/Riverside/riverside.scene, rewritten whole on every run (change the layout here, not in
  the editor). It lists only the Zombies mode and is marked ZombiesOnly (MapInformation), so the Zombies picker offers
  it and the multiplayer playlists, Quick Play, Ranked and the map vote don't;
- the radar picture, ui/minimaps/minimap_riverside.png, and with --art a stand-in menu picture, ui/maps/riverside.png.

Plan coordinates: e east, n north, z up, inches. Levels:
- The pad (z 96): the entrance, the park office and the dog run, e -1000..1500, n -1300..0. Players spawn here.
- The terrace (z 96): the pad's north-west end, e -1000..-220, n 0..600: the porch trailer and the park's sign.
- The flats (z 0): the park itself, reached down the south ramp (e -220..40, n 0..330). The Lucky Stop stands at the
  ramp's foot.
- The levee (z 96): along the river, e 640..1500, n 0..3500, joined to the pad, with the north ramp and the stairs by
  the store down to the flats. So the high ground and the flats make a loop to run zombies round.
The reference picture's view is REF_EYE, on the pad by the dog run's gate, looking north down the ramp: the layout puts
each thing it shows where that view sees it (the bearing and distance from the picture, roughly, since it's a painting).
Zombies come in through gaps in the perimeter fence (ZombieSpawnPoint); the buy stations stand where the map puts them
(ZombiesStationSpot): the weapon crate in the store, the workbench by the office, wall weapons on walls.
"""
import argparse
import json
import math
import platform
from pathlib import Path


def _no_wmi( *args, **kwargs ):
    raise OSError( "WMI query skipped" )


platform._wmi_query = _no_wmi       # see riverside_materials: WMI can hang scipy's import

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import map_kit as K  # noqa: E402
import railhead_map as R  # noqa: E402
import railhead_preview as PV  # noqa: E402
import riverside_materials as RM  # noqa: E402
import riverside_parts as P  # noqa: E402
import riverdale_parts as RP  # noqa: E402
from riverdale_parts import v, card, box, obox, rod, UP  # noqa: E402

TITLE = "Riverside"
OUT_DIR = K.ASSETS / "models/maps/riverside"
RESOURCE_DIR = "models/maps/riverside"
SCENE_FILE = K.ASSETS / "scenes/maps/Riverside/riverside.scene"
MINIMAP_PATH = "ui/minimaps/minimap_riverside.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_riverside.png"
MAP_ART_PATH = "ui/maps/riverside.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH
ZOMBIES_MODE = "prefabs/game_modes/zombies.prefab"

ids = K.SceneIds( "8b6f2d14-3c9e-4a57-b0d1-6e2f9a4c7b31" )

# The moon: riverside_sky's MOON (3 degrees west of north, 15 up). Its light comes in steeper than the disc sits, so the
# park's ground catches it (35 degrees), from the same bearing.
MOON_PITCH, MOON_YAW = 35.0, -3.0
MOON_COLOUR = "0.20,0.25,0.36,1"
SKY_MATERIAL = "materials/riverside/sky/riverside_sky.vmat"
FOG_COLOUR = "0.050,0.062,0.085"
CATCH_FLOOR_Z = -3000
DIRT = "dirt"

HIGH = 96.0
PLAY = ( -2200.0, 1500.0, -1300.0, 3500.0 )
PAD = ( -1000.0, 1500.0, -1300.0, 0.0 )
TERRACE = ( -1000.0, -220.0, 0.0, 600.0 )
LEVEE = ( 640.0, 1500.0, 0.0, 3500.0 )
FLATS = ( -2200.0, 640.0, 0.0, 3500.0 )
RAMP_S = ( -220.0, 40.0, 0.0, 330.0 )               # e0, e1, n0 (top, z HIGH), n1 (foot, z 0)
RAMP_N = ( 300.0, 640.0, 3020.0, 3320.0 )           # e0 (foot, z 0), e1 (top, z HIGH), n0, n1
STAIRS_E = ( 470.0, 640.0, 1050.0, 1130.0 )           # foot e, top e, n0, n1
NAV_TOP = 280.0

# The store: Lucky Stop at the ramp's foot, its porch facing south up the ramp; its shed east of it.
STORE = ( 70.0, 370.0, 640.0, 1000.0 )
STORE_FLOOR = 20.0
STORE_TOP = 150.0
PORCH_N0 = 520.0
SHED = ( 370.0, 640.0, 500.0, 1000.0 )
SHED_TOP = 132.0
STORE_DOOR = ( 200.0, 270.0 )                       # e0, e1 in the front wall
STORE_DOOR_TOP = 96.0

# The reference picture's camera: a player standing on the watch deck by the dog run's gate, looking 1.5 degrees east
# of north and 7 down, 80 degrees across. The picture's eye is about twice a standing player's over the ground (it sees
# over the camper's roof), so the deck lifts the player 60: their eye is 124 over the pad, where the picture's is.
DECK = ( 12.0, 108.0, -493.0, -397.0, 60.0 )      # the watch deck on the pad: e0, e1, n0, n1, its floor over the pad
REF_EYE = ( 60.0, -420.0, HIGH + DECK[4] + 64.0 )
REF_YAW, REF_PITCH, REF_FOV = 1.5, -7.0, 80.0
REF_TARGET = ( REF_EYE[0] + 1000 * math.sin( math.radians( REF_YAW ) ), REF_EYE[1] + 1000 * math.cos( math.radians( REF_YAW ) ),
               REF_EYE[2] + 1000 * math.tan( math.radians( REF_PITCH ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Paints

PAINTS = set( RM.all_paints() )


def configure( model ):
    for paint in list( model.polygons ):
        if paint.startswith( "rs_" ):
            model.material_overrides[paint] = f"{RM.RESOURCE_DIR}/{paint}.vmat"
            base = paint
            for prefix in ( "rs_siding", "rs_boards" ):
                if paint.startswith( prefix ):
                    base = prefix
            model.tile_overrides[paint] = RM.TILES.get( base, 64.0 )
            if paint not in PAINTS:
                R.UNKNOWN_PAINTS.add( paint )
        elif paint not in model.material_overrides:
            R.UNKNOWN_PAINTS.add( paint )
            model.material_overrides[paint] = f"{RM.RESOURCE_DIR}/rs_dark.vmat"
            model.tile_overrides[paint] = 64.0
    model.anchored_paints = set()
    model.decal_paints = set()
    return model


def place_into( m, part, origin, yaw ):
    m.extend( P.place( part, origin, yaw ) )


def ground_z( e, n ):
    """ The walking height at a plan point (ramps aside). """
    if PAD[0] <= e <= PAD[1] and n <= PAD[3]:
        return HIGH
    if TERRACE[0] <= e <= TERRACE[1] and n <= TERRACE[3]:
        return HIGH
    if e >= LEVEE[0]:
        return HIGH
    return 0.0


# ---------------------------------------------------------------------------------------------------------------------
# Ground

def ground():
    """ The pad, the terrace, the flats, the levee, the ramps and stairs, the retaining walls of railroad ties, the land
    outside the fence (the woods' floor, the county road, the levee's back slope down to the river), and the river. """
    m = K.Model()
    # The flats: one slab, its top at z 0, mud everywhere (the yards' grass goes over it as patches).
    box( m, FLATS[0] - 2400, FLATS[1], FLATS[2], FLATS[3] + 2600, -60, 0, { "default": None, "+z": "rs_mud" }, DIRT )
    # The high ground: the pad, the terrace and the levee, with tie walls where they drop to the flats.
    box( m, PAD[0], PAD[1], PAD[2], PAD[3], -60, HIGH, { "default": None, "+z": "rs_mud", "+n": "rs_ties" }, DIRT )
    box( m, *TERRACE, -60, HIGH, { "default": None, "+z": "rs_yard", "+n": "rs_ties", "+e": "rs_ties", "-e": "rs_ties" }, DIRT )
    box( m, LEVEE[0], LEVEE[1], LEVEE[2], LEVEE[3] + 2600, -60, HIGH, { "default": None, "+z": "rs_yard", "-e": "rs_ties" }, DIRT )
    # Outside: the high woods south-west of the pad, the county road south of the gate.
    box( m, FLATS[0] - 2400, PAD[0], -3600, 150, -60, HIGH, { "default": None, "+z": "rs_yard", "+n": "rs_ties" }, DIRT )
    box( m, PAD[0], PAD[1], -3600, PAD[2], -60, HIGH, { "default": None, "+z": "rs_gravel" }, DIRT )
    # The levee's back slope down to the river's edge (e 1500 -> 1760), the river (z 14), its far bank.
    le1, ln1 = LEVEE[1], LEVEE[3]
    rn = ln1 - 100      # where the high ground swings east round the park's north end, the water tower's knoll
    slope = [ v( le1, -3600, HIGH ), v( le1, rn, HIGH ), v( le1 + 260, rn, 6 ), v( le1 + 260, -3600, 6 ) ]
    card( m, "rs_yard", slope, v( 1, 0, 1 ) )
    m.hull( slope + [ p - UP * 120 for p in slope ], DIRT )
    card( m, "rs_water", [ v( le1 + 200, -3600, 14 ), v( le1 + 1600, -3600, 14 ), v( le1 + 1600, rn, 14 ), v( le1 + 200, rn, 14 ) ], UP )
    card( m, "rs_mud", [ v( le1 + 200, -3600, -20 ), v( le1 + 1600, -3600, -20 ), v( le1 + 1600, rn, -20 ), v( le1 + 200, rn, -20 ) ], UP )
    box( m, le1, le1 + 1900, rn, ln1 + 2600, -60, HIGH, { "default": None, "+z": "rs_yard", "-n": "rs_mud" }, DIRT )
    far_bank = [ v( le1 + 1500, -3600, 4 ), v( le1 + 1500, rn, 4 ), v( le1 + 1900, rn, 60 ), v( le1 + 1900, -3600, 60 ) ]
    card( m, "rs_yard", far_bank, v( -1, 0, 1 ) )
    box( m, le1 + 1900, le1 + 6000, -3600, ln1 + 2600, -60, 60, { "default": None, "+z": "rs_yard" } )
    # The south ramp: a slope of mud from the pad down to the flats, its east side held by ties (its west side is the
    # terrace's wall).
    re0, re1, rn0, rn1 = RAMP_S
    top = [ v( re0, rn0, HIGH ), v( re1, rn0, HIGH ), v( re1, rn1, 0 ), v( re0, rn1, 0 ) ]
    card( m, "rs_mud", top, v( 0, 0.3, 1 ) )
    m.hull( top + [ v( re0, rn0, 0 ), v( re1, rn0, 0 ) ], DIRT )
    card( m, "rs_ties", [ v( re1, rn0, 0 ), v( re1, rn1, 0 ), v( re1, rn0, HIGH ) ], v( 1, 0, 0 ) )
    # The north ramp: down from the levee westwards to the flats.
    ne0, ne1, nn0, nn1 = RAMP_N
    top = [ v( ne0, nn0, 0 ), v( ne1, nn0, HIGH ), v( ne1, nn1, HIGH ), v( ne0, nn1, 0 ) ]
    card( m, "rs_mud", top, v( -0.3, 0, 1 ) )
    m.hull( top + [ v( ne1, nn0, 0 ), v( ne1, nn1, 0 ) ], DIRT )
    for n in ( nn0, nn1 ):
        sgn = -1 if n == nn0 else 1
        card( m, "rs_ties", [ v( ne0, n, 0 ), v( ne1, n, 0 ), v( ne1, n, HIGH ) ], v( 0, sgn, 0 ) )
    # The stairs by the store: timber steps up the levee's wall.
    se0, se1, sn0, sn1 = STAIRS_E
    RP.stairs( m, ( se0, ( sn0 + sn1 ) / 2 ), ( se1, ( sn0 + sn1 ) / 2 ), sn1 - sn0, 0, HIGH, tread="rs_wood", side="rs_wood",
               rails=( True, True ), rail_paint="rs_wood", surface="wood", solid_under=True, under_paint="rs_wood", name="levee stair" )
    # Caps along the walls' tops: a row of ties laid flat.
    box( m, RAMP_S[1], LEVEE[0], PAD[3] - 10, PAD[3], HIGH, HIGH + 2, "rs_ties" )
    box( m, TERRACE[0], TERRACE[1], TERRACE[3] - 10, TERRACE[3], HIGH, HIGH + 2, "rs_ties" )
    box( m, TERRACE[1] - 10, TERRACE[1], TERRACE[2], TERRACE[3], HIGH, HIGH + 2, "rs_ties" )
    box( m, LEVEE[0], LEVEE[0] + 10, LEVEE[2], RAMP_N[2], HIGH, HIGH + 2, "rs_ties" )
    box( m, LEVEE[0], LEVEE[0] + 10, RAMP_N[3], LEVEE[3], HIGH, HIGH + 2, "rs_ties" )
    return m


# The lanes: the main lane from the ramp down the park to its north end, the cross lane, the west lane, the north lane
# and the lane under the terrace.
LANES = [
    [ ( -90, -200 ), ( -90, 330 ), ( -130, 700 ), ( -260, 1300 ), ( -420, 2000 ), ( -560, 2800 ), ( -600, 3500 ) ],
    [ ( -2200, 2080 ), ( -900, 2060 ), ( -436, 2050 ), ( 640, 2040 ) ],
    [ ( -1560, 160 ), ( -1560, 1200 ), ( -1600, 3400 ) ],
    [ ( -2200, 3170 ), ( -1600, 3170 ), ( -580, 3150 ), ( 300, 3170 ) ],
    [ ( -1560, 760 ), ( -800, 740 ), ( -150, 720 ) ],
]
LANE_WIDTH = 300.0


def lane_points( step ):
    out = []
    for lane in LANES:
        for a, b in zip( lane, lane[1:] ):
            a, b = np.array( a, float ), np.array( b, float )
            L = float( np.linalg.norm( b - a ) )
            for t in np.arange( 0, L, step ):
                out.append( tuple( a + ( b - a ) * t / L ) )
    return out


def near_lane( e, n, dist ):
    p = np.array( ( e, n ), float )
    for lane in LANES:
        for a, b in zip( lane, lane[1:] ):
            a, b = np.array( a, float ), np.array( b, float )
            d = b - a
            t = np.clip( np.dot( p - a, d ) / np.dot( d, d ), 0, 1 )
            if np.linalg.norm( p - ( a + d * t ) ) < dist:
                return True
    return False


def patches( m ):
    """ The look of the ground: grass in the yards (ragged patches over the mud), puddles in the lanes that mirror the
    lights, a gravel path on the levee. Drawn only. """
    rng = np.random.default_rng( 7 )
    for _ in range( 160 ):
        e = rng.uniform( FLATS[0] + 40, FLATS[1] - 40 )
        n = rng.uniform( FLATS[2] + 40, FLATS[3] - 40 )
        if near_lane( e, n, 230 ) or ground_z( e, n ) > 0 or ( STORE[0] - 60 < e < SHED[1] and n < STORE[3] + 40 ):
            continue
        blob_patch( m, "rs_yard", ( e, n ), rng.uniform( 60, 220 ), 0.15, int( rng.integers( 0, 1 << 30 ) ) )
    for k, ( e, n ) in enumerate( lane_points( 150 ) ):
        if rng.random() < 0.55:
            continue
        pe, pn = e + rng.normal( 0, 50 ), n + rng.normal( 0, 50 )
        if RAMP_S[0] - 20 < pe < RAMP_S[1] + 20 and RAMP_S[2] - 20 < pn < RAMP_S[3] + 20:
            continue
        P.puddle( m, ( pe, pn ), ( rng.uniform( 25, 90 ), rng.uniform( 18, 50 ) ), seed=k, z=ground_z( pe, pn ) + 0.25 )
    # The puddles the picture shows: on the pad in front of the camera, at the ramp's foot and in front of the store.
    for c, s in ( ( ( 30, -250 ), ( 70, 34 ) ), ( ( 110, -60 ), ( 90, 40 ) ), ( ( -40, -40 ), ( 60, 26 ) ), ( ( -30, 420 ), ( 120, 60 ) ),
                  ( ( 110, 300 ), ( 90, 40 ) ), ( ( -110, 600 ), ( 100, 45 ) ), ( ( -140, 900 ), ( 80, 40 ) ), ( ( -260, 1320 ), ( 110, 55 ) ) ):
        P.puddle( m, c, s, seed=abs( int( c[0] * 7 + c[1] ) ), z=ground_z( *c ) + 0.3 )
    # The levee's path.
    for n in range( int( LEVEE[2] ) + 100, int( LEVEE[3] ), 200 ):
        blob_patch( m, "rs_mud", ( 1000 + rng.normal( 0, 30 ), n ), 120, HIGH + 0.15, int( n ) )


def blob_patch( m, paint_name, c, r, z, seed ):
    rng = np.random.default_rng( seed )
    n = 14
    phase = rng.uniform( 0, 2 * math.pi, 3 )
    amp = rng.uniform( 0.1, 0.3, 3 )
    sx, sy = rng.uniform( 0.6, 1.4 ), rng.uniform( 0.6, 1.4 )
    pts = []
    for k in range( n ):
        a = 2 * math.pi * k / n
        rr = r * ( 1 + sum( amp[j] * math.sin( ( j + 2 ) * a + phase[j] ) for j in range( 3 ) ) )
        pts.append( v( c[0] + math.cos( a ) * rr * sx, c[1] + math.sin( a ) * rr * sy, z ) )
    m.polygon( paint_name, pts )


# ---------------------------------------------------------------------------------------------------------------------
# Trailers

# ( name, centre ( e, n ), yaw, length, width, tint, door side, seed, extra ). Yaw turns a trailer's own x (hitch at -x)
# anticlockwise from east.
LOW_TRAILERS = [
    ( "T2", ( -820, 1050 ), 0.0, 420, 110, "rs_siding_teal", -1, 12, "" ),
    ( "T3", ( -950, 2480 ), 104.0, 540, 120, "rs_siding_white", -1, 13, "porch_small" ),
    ( "T5", ( 300, 1300 ), 0.0, 480, 120, "rs_siding_green", -1, 15, "" ),
    ( "T6", ( 260, 1600 ), 0.0, 520, 120, "rs_siding_salmon", -1, 16, "porch_small" ),
    ( "T7", ( 200, 2350 ), 0.0, 500, 110, "rs_siding_white", -1, 17, "" ),
    ( "T8", ( -1250, 1200 ), 90.0, 520, 120, "rs_siding_grey", 1, 18, "" ),
    ( "T9", ( -1250, 2550 ), 90.0, 560, 120, "rs_siding_blue", 1, 19, "" ),
    ( "T10", ( -1960, 900 ), 0.0, 420, 110, "rs_siding_white", 1, 20, "" ),
    ( "T11", ( -1960, 1450 ), 0.0, 460, 120, "rs_siding_cream", 1, 21, "" ),
    ( "T12", ( -1960, 2400 ), 0.0, 440, 110, "rs_siding_tan", 1, 22, "" ),
    ( "T13", ( -1960, 2830 ), 0.0, 380, 110, "rs_siding_teal", 1, 23, "" ),
    ( "T14", ( -1150, 3380 ), 0.0, 480, 110, "rs_siding_grey", -1, 24, "" ),
    ( "T17", ( -1960, 450 ), 0.0, 380, 110, "rs_siding_salmon", 1, 25, "" ),
    ( "T18", ( -1220, 450 ), 0.0, 320, 100, "rs_siding_tan", 1, 26, "" ),
    ( "T red", ( -880, 2300 ), 12.0, 500, 120, "rs_siding_salmon", -1, 27, "porch_small" ),
    ( "T19", ( -760, 1500 ), 8.0, 460, 110, "rs_siding_cream", -1, 29, "" ),
]
# The porch trailer and the one behind it, on the terrace (z HIGH).
TERRACE_TRAILERS = [
    ( "T1 porch", ( -543, 160 ), 210.0, 560, 120, "rs_siding_cream", 1, 11, "porch" ),
    ( "T15", ( -900, 380 ), 90.0, 300, 110, "rs_siding_white", -1, 28, "" ),
]
LEVEE_TRAILERS = [
    ( "L1 ladder", ( 737, 747 ), 90.0, 600, 120, "rs_siding_white", -1, 31, "ladder" ),
    ( "L2", ( 1110, 1300 ), 0.0, 600, 120, "rs_siding_cream", -1, 32, "" ),
    ( "L3", ( 1130, 1700 ), 0.0, 620, 120, "rs_siding_grey", -1, 33, "" ),
    ( "L4", ( 1100, 2100 ), 0.0, 560, 110, "rs_siding_teal", -1, 34, "" ),
    ( "L5", ( 1130, 2500 ), 0.0, 600, 120, "rs_siding_tan", -1, 35, "" ),
    ( "L6", ( 1110, 2900 ), 0.0, 560, 110, "rs_siding_white", -1, 36, "" ),
]
BURNT = ( "TB burning", ( 140, 2650 ), 0.0, 460, 110 )
RAISED = 96.0           # the raised trailer's stilts


def build_trailer( name, L, W, tint, side, seed, extra ):
    part, info = P.trailer( L, W, tint, seed=seed, door_side=side, lit_share=0.6, boarded_share=0.15 )
    if extra in ( "porch", "porch_small" ):
        y0 = side * W / 2
        depth = 100 if extra == "porch" else 70
        x0, x1 = ( -L * 0.35, L * 0.1 ) if extra == "porch" else ( -L * 0.3, -L * 0.02 )
        P.porch_deck( part, x0, x1, y0, depth, P.FLOOR - 2, sy=side, string_lights=( extra == "porch" ), seed=seed )
        if extra == "porch":
            # Lawn chairs, a cooler and a propane bottle on the porch.
            P.lawn_chair( part, ( x0 + 60, y0 + side * 50 ), ( 0, side ), P.FLOOR - 2 )
            P.lawn_chair( part, ( x0 + 110, y0 + side * 55 ), ( 0.3, side ), P.FLOOR - 2, paint_name="rs_drum_red" )
            P.propane( part, ( x1 - 20, y0 + side * 20 ), P.FLOOR - 2 )
            info["string"] = ( x0, x1, y0 + side * depth )
    if extra == "ladder":
        # Raised on timber stilts against floods: 6x6 posts X-braced along each side, a landing on posts and a stair up to
        # its door. SAFE / HIGHER / STRONGER and an arrow sprayed on its hitch end, a ladder from the ground to its roof.
        lift = RAISED
        part = P.place( part, ( 0, 0, lift ), 0.0 )
        for key in ( "porch_light", "door" ):
            if key in info:
                info[key] = info[key] + UP * lift
        info["lit_windows"] = [ ( q + UP * lift, style ) for q, style in info.get( "lit_windows", [] ) ]
        hx, hy = L / 2, W / 2
        xs = np.linspace( -hx + 24, hx - 24, 6 )
        for y in ( -hy + 10, hy - 10 ):
            for x in xs:
                box( part, x - 2.75, x + 2.75, y - 2.75, y + 2.75, 0, lift, "rs_wood" )
                box( part, x - 8, x + 8, y - 8, y + 8, 0, 3, "rs_concrete" )
                part.collision_box( v( x - 3, y - 3, 0 ), v( x + 3, y + 3, lift ), "wood" )
            for a, b in zip( xs, xs[1:] ):
                part.beam( v( a, y, 8 ), v( b, y, lift - 8 ), ( 1.5, 5.5 ), "rs_wood", up=( 0, 1, 0 ) )
                part.beam( v( a, y, lift - 8 ), v( b, y, 8 ), ( 1.5, 5.5 ), "rs_wood", up=( 0, 1, 0 ) )
            box( part, -hx + 10, hx - 10, y - 2, y + 2, lift - 8, lift, "rs_wood" )
        for x in xs:
            box( part, x - 2, x + 2, -hy + 10, hy - 10, lift - 6, lift, "rs_wood" )
        door_x = info["door"][0]
        y0, y1 = sorted( ( side * ( hy + 4 ), side * ( hy + 50 ) ) )
        box( part, door_x - 24, door_x + 24, y0, y1, lift - 4, lift, { "default": "rs_wood" }, "wood" )
        for px_ in ( door_x - 21, door_x + 21 ):
            for py_ in ( y0 + 3, y1 - 3 ):
                box( part, px_ - 2.5, px_ + 2.5, py_ - 2.5, py_ + 2.5, 0, lift - 4, "rs_wood" )
        RP.stairs( part, ( door_x + 23 + 128, side * ( hy + 30 ) ), ( door_x + 23, side * ( hy + 30 ) ), 36, 0, lift, tread="rs_wood",
                   side="rs_wood", rails=( True, True ), rail_paint="rs_wood", surface="wood", name="stilt stair" )
        P.paint( part, "safe_higher", v( -hx, -12, lift + P.FLOOR + 50 ), v( 0, -1, 0 ), 76, tone="white", off=0.6 )
        foot = v( -hx - 40, 40, 0 )
        topp = v( -hx - 2, 40, lift + P.FLOOR + P.WALL + 6 )
        for dy in ( -9, 9 ):
            rod( part, foot + v( 0, dy, 0 ), topp + v( 0, dy, 0 ), 0.8, "rs_alu", 6 )
        rungs = int( ( topp[2] - foot[2] ) / 12 )
        for k in range( 1, rungs + 1 ):
            p = foot + ( topp - foot ) * ( k / ( rungs + 1 ) )
            rod( part, p + v( 0, -9, 0 ), p + v( 0, 9, 0 ), 0.55, "rs_alu", 5 )
        # Junk up on its roof: a tarp and a lawn chair, someone's lookout.
        roof = lift + P.FLOOR + P.WALL
        P.lawn_chair( part, ( -hx + 80, 0 ), ( -1, 0 ), roof + 5 )
        box( part, -hx + 120, -hx + 200, -40, 40, roof + 4, roof + 7, "rs_tarp_blue" )
    return part, info


def trailers( low, terrace, high ):
    for group, model, z in ( ( LOW_TRAILERS, low, 0.0 ), ( TERRACE_TRAILERS, terrace, HIGH ), ( LEVEE_TRAILERS, high, HIGH ) ):
        for name, c, yaw, L, W, tint, side, seed, extra in group:
            part, info = build_trailer( name, L, W, tint, side, seed, extra )
            place_into( model, part, ( c[0], c[1], z ), yaw )
            add_trailer_lights( name, ( c[0], c[1], z ), yaw, info )
    # The burning trailer: charred, smeared, a fire in it and a smoke column.
    name, c, yaw, L, W = BURNT
    part, info = P.trailer( L, W, "rs_siding_burnt", seed=41, door_side=-1, porch_light=False, lit_share=0.0, boarded_share=0.0,
                            antenna=False, ac=False )
    # Soot blown up the walls from its windows.
    for sy in ( -1, 1 ):
        for k in range( 4 ):
            x = -L / 2 + 50 + k * ( L - 100 ) / 3
            P.paint( part, "smear", v( x, sy * ( W / 2 ), P.FLOOR + 74 ), v( -sy, 0, 0 ), 34, tone="dark", off=0.8 )
    place_into( low, part, ( c[0], c[1], 0.0 ), yaw )
    P.FIRES.append( ( "burning trailer", ( c[0] - 60, c[1], P.FLOOR + P.WALL - 10 ), "big" ) )
    P.FIRES.append( ( "burning trailer 2", ( c[0] + 120, c[1] + 20, P.FLOOR + 30 ), "medium" ) )


def add_trailer_lights( name, origin, yaw, info ):
    if "porch_light" in info:
        p = P.local_to_world( info["porch_light"], origin, yaw )
        P.light( f"{name} porch", p, P.PORCH, 300 if "string" in info else 240, shadows="string" in info, scale=1.6 )
    for k, ( pos, style ) in enumerate( info.get( "lit_windows", [] )[:2] ):
        p = P.local_to_world( pos, origin, yaw )
        P.light( f"{name} window {k}", p, P.TV if style == "tv" else P.WARM, 170, scale=1.0 if style == "tv" else 1.2 )
    if "string" in info:
        x0, x1, y = info["string"]
        for k, t in enumerate( ( 0.15, 0.5, 0.85 ) ):
            q = P.local_to_world( ( x0 + ( x1 - x0 ) * t, y, P.FLOOR + 70 ), origin, yaw )
            P.light( f"{name} string {k}", q, P.WARM, 230, scale=1.4 )


# ---------------------------------------------------------------------------------------------------------------------
# The Lucky Stop

def store( m ):
    """ A clapboard bait-and-beer store on blocks: a porch with a roof, its sign on the porch roof, a door and windows lit
    from inside, posters, an ice machine and a drinks fridge on the porch, sandbags and crates; inside, shelves, a counter
    and fridges. Its shed east of it, with the graffiti on its front. """
    e0, e1, n0, n1 = STORE
    F, T = STORE_FLOOR, STORE_TOP
    wt = 6.0
    # Floor on blocks.
    box( m, e0, e1, n0, n1, 0, F, { "default": "rs_concrete", "+z": "rs_wood" }, "wood" )
    d0, d1 = STORE_DOOR

    def wall_box( a0, a1, b0, b1, z0, z1 ):
        box( m, a0, a1, b0, b1, z0, z1, { "default": "rs_boards_dark", "+z": "rs_dark", "-z": None }, "wood" )
    # The front wall split round the door, the sides and the back.
    wall_box( e0, d0, n0, n0 + wt, F, T )
    wall_box( d1, e1, n0, n0 + wt, F, T )
    wall_box( d0, d1, n0, n0 + wt, STORE_DOOR_TOP, T )
    wall_box( e0, e0 + wt, n0, n1, F, T )
    wall_box( e0, e1, n1 - wt, n1, F, T )
    wall_box( e1 - wt, e1, n0, n1, F, T )
    # Roof: a flat roof sloping back, corrugated, and a false front parapet.
    pts = [ v( e0 - 8, n0 - 2, T + 14 ), v( e1 + 8, n0 - 2, T + 14 ), v( e1 + 8, n1 + 8, T + 4 ), v( e0 - 8, n1 + 8, T + 4 ) ]
    card( m, "rs_roof", pts, UP )
    card( m, "rs_roof", [ v( e0, n0, T ), v( e1, n0, T ), v( e1, n1, T ), v( e0, n1, T ) ], -UP )
    box( m, e0 - 8, e1 + 8, n0 - 4, n0, T, T + 34, "rs_boards_dark", "wood" )
    box( m, e0 - 8, e1 + 8, n0 - 6, n0 - 4, T + 32, T + 36, "rs_dark" )
    # Porch: deck, posts, a roof sloping forward, steps up.
    box( m, e0 - 10, e1 + 10, PORCH_N0, n0, 0, F, { "default": "rs_concrete", "+z": "rs_wood" }, "wood" )
    eave = F + 130
    for e in np.linspace( e0 - 6, e1 + 6, 4 ):
        box( m, e - 2.5, e + 2.5, PORCH_N0 + 2, PORCH_N0 + 7, F, eave, "rs_wood", "wood" )
    pr = [ v( e0 - 14, PORCH_N0 - 10, eave ), v( e1 + 14, PORCH_N0 - 10, eave ), v( e1 + 14, n0, eave + 14 ), v( e0 - 14, n0, eave + 14 ) ]
    card( m, "rs_roof", pr, v( 0, -0.15, 1 ) )
    card( m, "rs_roof", pr, -UP )
    box( m, e0 - 14, e1 + 14, PORCH_N0 - 10, PORCH_N0 - 4, eave - 6, eave + 1, "rs_wood" )
    P.steps( m, ( ( d0 + d1 ) / 2, PORCH_N0 - 30 ), ( 0, 1 ), 90, F - 0.5, "rs_wood", "wood", rise=7 )
    # The LUCKY STOP sign standing on the porch roof's front edge, backlit, with gooseneck lamps over it.
    r = P.right_for( ( 0, -1 ) )
    sw = 160.0
    sh = sw / RM.aspect( RM.LIT, "lucky_stop" )
    sc = v( ( e0 + e1 ) / 2, PORCH_N0 - 6, eave + 30 + sh / 2 )
    obox( m, sc, ( 1, 0, 0 ), ( sw + 8, 8, sh + 8 ), "rs_dark", "metal" )
    P.lit( m, "lucky_stop", sc + v( 0, -4, 0 ), r, sh, off=0.4, w=sw )
    P.sign( m, "sign_back", sc + v( 0, 4, 0 ), -r, sh, off=0.4, w=sw )
    for k in range( 3 ):
        lp = sc + v( -sw * 0.35 + k * sw * 0.35, -14, sh / 2 + 6 )
        obox( m, lp, ( 1, 0, 0 ), ( 8, 6, 3 ), "rs_dark" )
        card( m, "rs_lamp_warm", [ lp + v( -3.5, -2.5, -1.6 ), lp + v( 3.5, -2.5, -1.6 ), lp + v( 3.5, 2.5, -1.6 ), lp + v( -3.5, 2.5, -1.6 ) ], -UP )
        rod( m, lp + v( 0, 3, 0 ), lp + v( 0, 12, -2 ), 0.6, "rs_steel", 5 )
    for sx in ( -1, 1 ):
        # Steel legs from the porch roof up to the sign, braced back.
        foot = v( sc[0] + sx * sw * 0.4, PORCH_N0 - 6, eave )
        m.beam( foot, foot + UP * ( sc[2] - sh / 2 - eave ), ( 2.0, 2.0 ), "rs_steel" )
        m.beam( foot + UP * ( sc[2] - sh / 2 - eave - 4 ), v( foot[0], PORCH_N0 + 30, eave + 4 ), ( 1.5, 1.5 ), "rs_steel" )
    P.light( "store sign", sc + v( 0, -60, 10 ), P.WARM, 420, shadows=True, scale=2.2 )
    # The front: windows lit from inside, the OPEN and COLD BEER neon, posters, the door's frame.
    front = n0 - 0.2
    for cx, ww in ( ( ( d1 + e1 ) / 2, min( 70.0, e1 - d1 - 24 ) ), ( ( e0 + d0 ) / 2, min( 90.0, d0 - e0 - 30 ) ) ):
        wc = v( cx, front, F + 62 )
        RP.quad( m, "rs_dark", wc, r, UP, ww + 6, 58, off=0.2 )
        P.lit( m, "window", wc, r, 52, off=0.4, w=ww )
        if cx > d1:
            P.lit( m, "open", wc + v( -ww * 0.2, 0, 14 ), r, 12, off=0.7 )
            P.lit( m, "beer", wc + v( ww * 0.18, 0, -14 ), r, 10, off=0.7 )
    for k, ( name, e, z ) in enumerate( ( ( "poster_lotto", e0 + 14, F + 100 ), ( "poster_ice", d0 - 14, F + 100 ), ( "poster_bait", e1 - 22, F + 32 ),
                                          ( "poster_propane", d1 + 12, F + 100 ) ) ):
        P.sign( m, name, v( e, front, z ), r, 22, off=0.5 )
    RP.quad( m, "rs_dark", v( ( d0 + d1 ) / 2, front, ( F + STORE_DOOR_TOP ) / 2 ), r, UP, d1 - d0 + 6, STORE_DOOR_TOP - F + 3, off=0.1 )
    # Inside: the threshold, shelves of goods, the counter, fridges along the east wall, two fluorescent fittings.
    box( m, d0 - 1, d1 + 1, n0, n0 + wt, F - 0.5, F, "rs_steel" )
    for row_e in ( 140, 270 ):
        for k in range( 2 ):
            sn = n0 + 90 + k * 110
            box( m, row_e - 18, row_e + 18, sn, sn + 70, F, F + 56, { "default": "rs_wood" }, "wood" )
            for zz in ( F + 18, F + 38, F + 56 ):
                P.lit( m, "window", v( row_e - 18.3, sn + 35, zz - 7 ), P.right_for( ( -1, 0 ) ), 12, off=0.0, w=68 )
                P.lit( m, "window", v( row_e + 18.3, sn + 35, zz - 7 ), P.right_for( ( 1, 0 ) ), 12, off=0.0, w=68 )
    box( m, e0 + 10, e0 + 120, n1 - 80, n1 - 50, F, F + 40, { "default": "rs_wood", "+z": "rs_concrete" }, "wood" )
    obox( m, v( e0 + 50, n1 - 65, F + 46 ), ( 1, 0, 0 ), ( 16, 12, 12 ), "rs_dark" )
    for k in range( 3 ):
        P.fridge( m, ( e1 - wt - 16, n0 + 120 + k * 34 ), ( -1, 0 ), F )
    for k, ( fx, fn ) in enumerate( ( ( 150, n0 + 120 ), ( 280, n0 + 250 ) ) ):
        obox( m, v( fx, fn, T - 3 ), ( 0, 1, 0 ), ( 48, 8, 3 ), "rs_dark" )
        card( m, "rs_lamp_cool", [ v( fx - 3, fn - 23, T - 4.6 ), v( fx + 3, fn - 23, T - 4.6 ), v( fx + 3, fn + 23, T - 4.6 ), v( fx - 3, fn + 23, T - 4.6 ) ], -UP )
        P.light( f"store inside {k}", ( fx, fn, T - 30 ), P.COOL, 300, shadows=k == 0, scale=1.4 )
    # On the porch: the ice machine, a drinks fridge, sandbags at the east end, crates, a burning drum by the steps.
    ice_c = v( d0 - 40, n0 - 18, F )
    obox( m, ice_c + UP * 30, ( 1, 0, 0 ), ( 38, 30, 60 ), "rs_fridge", "metal" )
    P.lit( m, "vending", ice_c + v( 0, -15.2, 30 ), r, 52, off=0.0, w=36 )
    P.light( "ice machine", ice_c + v( 0, -40, 40 ), P.COOL, 140, scale=0.9 )
    P.fridge( m, ( e0 + 26, PORCH_N0 + 40 ), ( 0, -1 ), F )
    P.sandbag_wall( m, ( e1 - 70, PORCH_N0 + 10 ), ( e1 + 8, PORCH_N0 + 10 ), rows=5, z0=F, seed=3 )
    P.sandbag_wall( m, ( e1 + 30, PORCH_N0 - 30 ), ( e1 + 30, PORCH_N0 + 70 ), rows=4, z0=0, seed=4 )
    P.crate( m, ( e0 - 40, PORCH_N0 - 30 ), ( 30, 22, 20 ), ( 1, 0.2 ), 0 )
    P.crate( m, ( e0 - 40, PORCH_N0 - 30 ), ( 26, 20, 18 ), ( 1, -0.1 ), 20 )
    P.crate( m, ( d1 + 40, PORCH_N0 + 30 ), ( 30, 22, 20 ), ( 1, 0 ), F )
    P.drum( m, ( d0 - 30, PORCH_N0 - 60 ), "rs_rust", name="store drum" )
    P.light( "store porch", ( ( e0 + e1 ) / 2, PORCH_N0 + 40, F + 96 ), P.PORCH, 340, shadows=True, scale=1.8 )
    obox( m, v( d1 + 20, n0 - 3, F + 96 ), ( 1, 0, 0 ), ( 8, 6, 5 ), "rs_porch_light" )
    # The shed: plywood walls, a lean-to roof, its front sprayed FUEL FOOD GUNS A BETTER TOMORROW?
    se0, se1, sn0, sn1 = SHED
    box( m, se0, se1, sn0, sn1, 0, SHED_TOP, { "default": "rs_plywood", "+z": None }, "wood" )
    pts = [ v( se0 - 6, sn0 - 8, SHED_TOP + 16 ), v( se1 + 8, sn0 - 8, SHED_TOP ), v( se1 + 8, sn1 + 4, SHED_TOP ), v( se0 - 6, sn1 + 4, SHED_TOP + 16 ) ]
    card( m, "rs_roof", pts, UP )
    P.paint( m, "fuel_food", v( ( se0 + se1 ) / 2 + 6, sn0 - 0.2, 70 ), P.right_for( ( 0, -1 ) ), 124, tone="white", off=0.4 )
    P.paint( m, "x_mark", v( se1 - 30, sn0 - 0.2, 100 ), P.right_for( ( 0, -1 ) ), 26, tone="red", off=0.5 )
    P.light( "shed lamp", ( se0 + 40, sn0 - 40, 120 ), P.SODIUM, 300, scale=1.6 )
    obox( m, v( se0 + 40, sn0 - 3, 124 ), ( 1, 0, 0 ), ( 12, 6, 5 ), "rs_dark" )
    card( m, "rs_lamp_sodium", [ v( se0 + 34, sn0 - 6, 121.4 ), v( se0 + 46, sn0 - 6, 121.4 ), v( se0 + 46, sn0, 121.4 ), v( se0 + 34, sn0, 121.4 ) ], -UP )


# ---------------------------------------------------------------------------------------------------------------------
# The pad: the office, the gate, the dog run, the camper

def watch_deck( m, gz ):
    """ A timber deck the survivors built on the pad to watch the lane from: 6x6 posts, joists and boards 5 ft up, a rail
    round its sides and back, sandbags along its front, steps up its back. A player standing on it sees the park as the
    picture does (REF_EYE). """
    e0, e1, n0, n1, h = DECK
    top = gz + h
    for e in ( e0 + 3, e1 - 3 ):
        for n in ( n0 + 3, n1 - 3 ):
            box( m, e - 2.75, e + 2.75, n - 2.75, n + 2.75, gz, top - 4, "rs_wood" )
            box( m, e - 7, e + 7, n - 7, n + 7, gz, gz + 2, "rs_concrete" )
    for e in np.linspace( e0 + 2, e1 - 2, 5 ):
        box( m, e - 0.75, e + 0.75, n0, n1, top - 10, top - 4, "rs_wood" )
    for k, n in enumerate( np.arange( n0, n1, 5.6 ) ):
        box( m, e0 - 1, e1 + 1 + ( 1.5 if k % 3 == 0 else 0 ), n + 0.2, n + 5.4, top - 4, top, "rs_wood" )
    m.collision_box( v( e0, n0, gz ), v( e1, n1, top ), "wood" )
    # X braces under it on its sides.
    for e in ( e0 + 3, e1 - 3 ):
        m.beam( v( e, n0 + 4, gz + 6 ), v( e, n1 - 4, top - 12 ), ( 1.5, 5.5 ), "rs_wood", up=( 1, 0, 0 ) )
        m.beam( v( e, n1 - 4, gz + 6 ), v( e, n0 + 4, top - 12 ), ( 1.5, 5.5 ), "rs_wood", up=( 1, 0, 0 ) )
    # Rails on the two sides and the back, open over the steps; the front has sandbags, below the view.
    RP.railing( m, [ ( e0 + 2, n1 - 2 ), ( e0 + 2, n0 + 2 ), ( ( e0 + e1 ) / 2 - 20, n0 + 2 ) ], top, "rs_wood", height=38,
                post_every=46, kick=False, clip_to=48, name="deck rail" )
    RP.railing( m, [ ( ( e0 + e1 ) / 2 + 20, n0 + 2 ), ( e1 - 2, n0 + 2 ), ( e1 - 2, n1 - 2 ) ], top, "rs_wood", height=38,
                post_every=46, kick=False, clip_to=48, name="deck rail" )
    P.sandbag_wall( m, ( e0 + 4, n1 - 7 ), ( e1 - 4, n1 - 7 ), rows=2, z0=top, seed=21 )
    RP.stairs( m, ( ( e0 + e1 ) / 2, n0 - 80 ), ( ( e0 + e1 ) / 2, n0 ), 38, gz, top, tread="rs_wood", side="rs_wood",
               rails=( True, True ), rail_paint="rs_wood", surface="wood", name="deck stair" )


def lantern( m, at ):
    """ A battery camping lantern left on the ground, lit: a dark base, a frosted globe, a cap and a wire handle. """
    c = v( *at )
    RP.cylinder( m, c, 3.2, c[2], c[2] + 2.5, "rs_dark", 10, top="rs_dark" )
    RP.cylinder( m, c, 2.6, c[2] + 2.5, c[2] + 8.5, "rs_lantern", 10 )
    RP.cylinder( m, c, 3.0, c[2] + 8.5, c[2] + 10, "rs_dark", 10, top="rs_dark" )
    rod( m, c + v( -2.4, 0, 10 ), c + v( 0, 0, 14 ), 0.25, "rs_steel", 4 )
    rod( m, c + v( 0, 0, 14 ), c + v( 2.4, 0, 10 ), 0.25, "rs_steel", 4 )
    P.light( "lantern", c + UP * 9, P.WARM, 280, shadows=True, scale=1.4 )

OFFICE = ( "office", ( -640, -640 ), 0.0, 480, 120 )
# The dog run's fence: a pen west of the camera, its gate on the east side with the cooler in it.
DOG_RUN = [ ( -300, -120 ), ( -40, -195 ), ( 0, -40 ), ( -300, -40 ), ( -300, -120 ) ]
DOG_GATE = ( 1, 5, 50 )


def pad( m ):
    gz = HIGH
    name, c, yaw, L, W = OFFICE
    part, info = P.trailer( L, W, "rs_siding_white", seed=51, door_side=1, lit_share=0.8, boarded_share=0.0, door_lit=True )
    door_x = info["door"][0]
    P.lit( part, "office", v( door_x, W / 2 + 0.5, P.FLOOR + 92 ), P.right_for( ( 0, 1 ) ), 14, off=0.5 )
    P.sign( part, "office_rules", v( door_x + 70, W / 2, P.FLOOR + 50 ), P.right_for( ( 0, 1 ) ), 30, off=0.6 )
    P.porch_deck( part, door_x - 80, door_x + 80, W / 2, 80, P.FLOOR - 2, sy=1, string_lights=False, seed=3 )
    place_into( m, part, ( c[0], c[1], gz ), yaw )
    add_trailer_lights( name, ( c[0], c[1], gz ), yaw, info )
    P.light( "office sign", ( c[0] + door_x, c[1] + W / 2 + 40, gz + 110 ), P.COOL, 220, scale=1.2 )
    # The dog run: chain-link, its gate open, the cooler in the gap, the sign on the panel by it, a teddy in the mud.
    P.chainlink( m, DOG_RUN, 44, 110, z=gz, gaps=[ DOG_GATE ], name="dog run" )
    a0, b0 = np.array( DOG_RUN[0], float ), np.array( DOG_RUN[1], float )
    d0 = ( b0 - a0 ) / np.linalg.norm( b0 - a0 )
    at = b0 - d0 * 48
    P.sign( m, "people_too", v( at[0], at[1], gz + 26 ), P.right_for( ( d0[1], -d0[0] ) ), 26, off=1.6 )
    a, b = np.array( DOG_RUN[1], float ), np.array( DOG_RUN[2], float )
    d = ( b - a ) / np.linalg.norm( b - a )
    out = ( d[1], -d[0] )
    gate = a + d * ( DOG_GATE[1] + DOG_GATE[2] ) / 2
    P.cooler( m, ( gate[0] + out[0] * 10, gate[1] + out[1] * 10 ), ( -d[0], -d[1] ), gz, lid_open=True )
    P.teddy( m, ( -24, -215 ), ( 0.45, -0.9 ), gz, scale=1.0 )
    lantern( m, ( -50, -205, gz ) )
    # The gate leaf swung open into the run.
    hinge = a + d * DOG_GATE[1]
    leaf = hinge + np.array( ( -0.85, 0.53 ) ) * ( DOG_GATE[2] - DOG_GATE[1] - 4 )
    P.chainlink( m, [ tuple( hinge ), tuple( leaf ) ], 42, 60, z=gz, top_rail=True, collide=False, name="dog gate" )
    P.speed_sign( m, ( -85, -30, gz ), ( 0.4, -1 ) )
    watch_deck( m, gz )
    # The camper on the pad's east side, its front to the store, its west side (the handprints) to the camera.
    place_into( m, P.rv(), ( 276, -298, gz ), 100.0 )
    # Junk round the pad: a trash pile, propane bottles, the burning drum in front of the camera, more drums.
    P.junk_pile( m, ( -420, -260 ), seed=5, z0=gz )
    P.drum( m, ( 48, -18 ), "rs_drum_blue", z0=gz, name="pad drum" )
    P.drum( m, ( 82, -34 ), "rs_rust", z0=gz, burning=False )
    P.drum( m, ( 120, -540 ), "rs_drum_red", z0=gz, name="gate drum" )
    P.drum( m, ( -880, -140 ), "rs_rust", z0=gz, burning=False )
    for k in range( 3 ):
        P.propane( m, ( -380 + k * 18, -560 ), gz )
    P.crate( m, ( 140, -80 ), ( 30, 24, 22 ), ( 1, 0.3 ), gz )
    P.tire( m, ( 172, -110, gz + 4.2 ), ( 0, 0, 1 ), r=12.5, w=8 )
    # The gate across the county road, shut and chained, the fence either side.
    P.chainlink( m, [ ( PAD[0], PAD[2] + 6 ), ( -220, PAD[2] + 6 ) ], 84, 120, z=gz, barbed=True, name="south fence" )
    P.chainlink( m, [ ( 220, PAD[2] + 6 ), ( PAD[1], PAD[2] + 6 ) ], 84, 120, z=gz, barbed=True, name="south fence" )
    P.chainlink( m, [ ( -220, PAD[2] + 10 ), ( 220, PAD[2] + 10 ) ], 80, 220, z=gz, barbed=True, name="gate" )
    P.sign( m, "no_trespass", v( 0, PAD[2] + 12, gz + 50 ), P.right_for( ( 0, 1 ) ), 22, off=0.6 )


# ---------------------------------------------------------------------------------------------------------------------
# The dressing round the lanes

POLES_WEST = [ ( -110, -5, HIGH ), ( -255, 520, HIGH ), ( -340, 1050, 0 ), ( -500, 1720, 0 ), ( -660, 2330, 0 ), ( -750, 2880, 0 ) ]
POLES_EAST = [ ( 230, 1060, 0 ), ( 30, 1300, 0 ), ( -60, 1820, 0 ) ]
DRUMS = [ ( ( 20, 600, 0 ), "rs_drum_blue" ), ( ( -260, 1020, 0 ), "rs_rust" ), ( ( 120, 1400, 0 ), "rs_drum_red" ),
          ( ( -520, 1880, 0 ), "rs_drum_blue" ), ( ( 420, 2520, 0 ), "rs_rust" ), ( ( -1300, 1700, 0 ), "rs_drum_red" ),
          ( ( -1720, 2560, 0 ), "rs_rust" ), ( ( -230, 3040, 0 ), "rs_drum_blue" ), ( ( -600, 520, HIGH ), "rs_rust" ) ]
SIGN = ( ( -393, 415, HIGH ), ( 0.5, -0.866 ) )
NO_PLACE = ( ( -60, 1150, 0 ), ( 0.05, -1.0 ) )
PICKUP = ( ( -300, 1000, 0 ), -15.0 )
TOWER = ( ( -530, 1600, 0 ), ( 0.3, -1.0 ) )
SEARCH_TARGET = ( -1100, 900, 0 )
SEARCH_HEAD = []
WATER_TOWER = ( ( 1688, 3600, HIGH ), ( -0.4, -1.0 ) )


def dressing( m ):
    # The park's sign on the terrace behind the porch trailer, facing the entrance; the neon on its pole down the lane.
    P.park_sign( m, SIGN[0], SIGN[1], scale=0.7, height=370 )
    P.neon_sign( m, NO_PLACE[0], NO_PLACE[1] )
    place_into( m, P.pickup( seed=3, wrecked=True ), PICKUP[0], PICKUP[1] )
    for k, ( c, paint_name ) in enumerate( DRUMS ):
        P.drum( m, c[:2], paint_name, z0=c[2], name=f"drum {k}" )
    # Utility poles along the lane and wires between them.
    taps_w = []
    for k, c in enumerate( POLES_WEST ):
        lamp = ( "sodium", ( 1, 0.15 ) ) if k in ( 2, 4 ) else None
        taps, head = P.pole( m, c, 430, facing=( 1, 0.1 ), arms=2, transformer=k in ( 1, 3 ), lamp=lamp, seed=k )
        taps_w.append( taps )
        if head is not None:
            P.light( f"lane lamp {k}", head - UP * 10, P.SODIUM, 720, shadows=k == 2, scale=2.0 )
    for a, b in zip( taps_w, taps_w[1:] ):
        for i in range( min( len( a ), len( b ), 4 ) ):
            P.wire( m, a[i], b[i] )
    taps_e = []
    for k, c in enumerate( POLES_EAST ):
        lamp = ( "sodium", ( -1, -0.3 ) ) if k < 2 else None
        taps, head = P.pole( m, c, 400, facing=( -1, 0 ), arms=1, transformer=k == 0, lamp=lamp, seed=10 + k )
        taps_e.append( taps )
        if head is not None:
            P.light( f"store lamp {k}", head - UP * 10, P.SODIUM, 700, shadows=k == 0, scale=2.1 )
    for a, b in zip( taps_e, taps_e[1:] ):
        for i in range( min( len( a ), len( b ) ) ):
            P.wire( m, a[i], b[i] )
    # Across the lane to the store's pole, and service drops down to the store and trailers.
    P.wire( m, taps_w[1][0], taps_e[0][0] )
    P.wire( m, taps_w[1][2], taps_e[0][1] )
    P.wire( m, taps_e[0][1], ( 220, STORE[3] - 2, STORE_TOP + 10 ) )
    P.wire( m, taps_w[2][1], ( -650, 1060, 115 ) )
    P.wire( m, taps_w[3][1], ( -620, 1480, 115 ) )
    P.wire( m, taps_e[1][1], ( 60, 1320, 115 ) )
    # The guard tower's searchlight, aimed down the lane towards the entrance.
    head = P.guard_tower( m, TOWER[0], TOWER[1] )
    P.light( "guard tower cab", ( TOWER[0][0], TOWER[0][1], 520 + 70 ), P.WARM, 200, scale=1.4 )
    P.SPOTLIGHTS.append( ( "searchlight", tuple( float( x ) for x in head ), SEARCH_TARGET, "1.6,1.6,1.7,1", 3200, 6.0 ) )
    SEARCH_HEAD[:] = [ float( x ) for x in head ]
    # Wrecks of the night: lawn chairs, junk, blood on the mud.
    P.lawn_chair( m, ( -420, 1060 ), ( 0.7, 0.7 ) )
    P.junk_pile( m, ( -1380, 860 ), seed=8 )
    P.junk_pile( m, ( 560, 2330 ), seed=9 )
    P.junk_pile( m, ( -1700, 2100 ), seed=10 )
    for c, s in ( ( ( 30, -200, HIGH ), 40 ), ( ( 10, 380, 0 ), 50 ), ( ( -180, 1260, 0 ), 60 ), ( ( -500, 2020, 0 ), 50 ) ):
        P.blood( m, "splatter", v( c[0], c[1], c[2] + 0.45 ), v( 1, 0, 0 ), s, up=v( 0, 1, 0 ), off=0.0 )
    P.blood( m, "trail", v( -40, -160, HIGH + 0.45 ), v( 1, 0, 0 ), 110, up=v( 0.3, 1, 0 ), off=0.0 )
    P.blood( m, "trail", v( -80, 560, 0.45 ), v( 1, 0, 0 ), 120, up=v( -0.2, 1, 0 ), off=0.0 )
    # Plank fences between yards, sandbags and crates across the north lane.
    P.plank_fence( m, [ ( -1400, 960 ), ( -1400, 1460 ) ], seed=1 )
    P.plank_fence( m, [ ( -1080, 2250 ), ( -1080, 2700 ) ], seed=2 )
    P.sandbag_wall( m, ( 120, 3050 ), ( 260, 3090 ), rows=4, seed=7 )
    for k in range( 4 ):
        P.crate( m, ( -380 + k * 34, 3230 + ( k % 2 ) * 20 ), ( 30, 24, 22 ), ( 1, 0.1 * k ), 0 )


def perimeter( m ):
    """ The park's fence: chain-link with barbed wire round the flats and along the levee, its gaps where the zombies
    came through (left open to the eye, closed to players by a clip). """
    w, e, n = PLAY[0] + 10, PLAY[1] - 10, PLAY[3] - 10
    s = 150.0
    west_gaps, north_gaps, levee_gaps, east_gaps = [ ( 860, 980 ), ( 1760, 1880 ), ( 2760, 2880 ) ], [ ( 640, 760 ), ( 1740, 1860 ), ( 2580, 2680 ) ], \
        [ ( 400, 520 ) ], [ ( 820, 940 ), ( 1660, 1780 ), ( 2450, 2560 ), ( 3250, 3370 ) ]
    P.chainlink( m, [ ( w, s + 5 ), ( w, n ) ], 84, 120, barbed=True, gaps=[ ( 0, a, b ) for a, b in west_gaps ], clip_to=1000, name="west fence" )
    P.chainlink( m, [ ( w, n ), ( LEVEE[0], n ) ], 84, 120, barbed=True, gaps=[ ( 0, a, b ) for a, b in north_gaps ], clip_to=1000, name="north fence" )
    P.chainlink( m, [ ( LEVEE[0], n ), ( e, n ) ], 84, 120, z=HIGH, barbed=True, gaps=[ ( 0, a, b ) for a, b in levee_gaps ], clip_to=1000,
                 name="north levee fence" )
    P.chainlink( m, [ ( e, n ), ( e, PAD[2] + 6 ) ], 84, 120, z=HIGH, barbed=True, gaps=[ ( 0, a, b ) for a, b in east_gaps ], clip_to=1000,
                 name="east fence" )
    P.chainlink( m, [ ( w, s + 5 ), ( PAD[0], s + 5 ) ], 84, 120, barbed=True, clip_to=1000, name="south flats fence" )
    P.chainlink( m, [ ( PAD[0] + 6, s ), ( PAD[0] + 6, PAD[2] + 6 ) ], 84, 120, z=HIGH, barbed=True, clip_to=1000, name="pad west fence" )
    # Clips over the gaps: the fence's own clips skip them, so close them for players.
    for a, b in west_gaps:
        RP.clip( "breach", ( w, s + 5 + a ), ( w, s + 5 + b ), 0, 1000 )
    for a, b in north_gaps:
        RP.clip( "breach", ( w + a, n ), ( w + b, n ), 0, 1000 )
    for a, b in levee_gaps:
        RP.clip( "breach", ( LEVEE[0] + a, n ), ( LEVEE[0] + b, n ), HIGH, 1000 )
    for a, b in east_gaps:
        RP.clip( "breach", ( e, n - a ), ( e, n - b ), HIGH, 1000 )
    RP.clip( "gate", ( PAD[0], PAD[2] + 6 ), ( PAD[1], PAD[2] + 6 ), HIGH, 1000 )


# Zombie spawn points: just inside each gap in the fence, and the corners.
ZOMBIE_SPAWNS = [
    ( -2120, 1075, 0 ), ( -2120, 1970, 0 ), ( -2120, 2975, 0 ), ( -1500, 3420, 0 ), ( -400, 3420, 0 ), ( 440, 3420, 0 ),
    ( 1100, 3420, HIGH ), ( 1420, 2620, HIGH ), ( 1420, 1830, HIGH ), ( 1420, 1040, HIGH ), ( 1420, 240, HIGH ),
    ( 1380, -1150, HIGH ), ( -880, -1180, HIGH ), ( -2100, 260, 0 ), ( -1100, 300, 0 ), ( 520, 260, 0 ),
]
PLAYER_SPAWNS = [ ( -360, -900, HIGH ), ( -200, -980, HIGH ), ( -40, -940, HIGH ), ( 120, -980, HIGH ), ( -300, -760, HIGH ),
                  ( -120, -800, HIGH ), ( 60, -700, HIGH ), ( 260, -820, HIGH ) ]
# ( kind, order, position, facing ): where the buy stations stand.
STATION_SPOTS = [
    ( "WeaponCrate", 0, ( 250, STORE[3] - 30, STORE_FLOOR ), ( 0, -1 ) ),
    ( "Workbench", 0, ( -340, -640, HIGH ), ( 1, 0 ) ),
    ( "WallWeapon", 0, ( -490, -574, HIGH ), ( 0, 1 ) ),
    ( "WallWeapon", 1, ( 560, SHED[2] - 6, 0 ), ( 0, -1 ) ),
    ( "WallWeapon", 2, ( 1000, 1225, HIGH ), ( 0, -1 ) ),
    ( "AmmoBox", 0, ( -160, -300, HIGH ), ( 1, 0 ) ),
    ( "AmmoBox", 1, ( 1040, 1500, HIGH ), ( 0, -1 ) ),
]


# ---------------------------------------------------------------------------------------------------------------------
# Trees and the backdrop

def trees( near, far ):
    """ Slash pines and cabbage palms round the park: a few in the yards, a wood outside the fence, a far tree line. """
    rng = np.random.default_rng( 61 )
    inside = [ ( -1700, 1700 ), ( -1350, 3000 ), ( -1500, 560 ), ( -1800, 3250 ), ( 1300, 1500 ), ( 1350, 2300 ), ( 900, 3200 ),
               ( -720, 2950 ), ( 60, 3060 ) ]
    for k, ( e, n ) in enumerate( inside ):
        z = ground_z( e, n )
        if rng.random() < 0.75:
            P.palm( near, ( e, n, z ), rng.uniform( 300, 460 ), seed=k )
            near.collision_box( v( e - 8, n - 8, z ), v( e + 8, n + 8, z + 200 ), "wood" )
        else:
            P.pine( near, ( e, n, z ), rng.uniform( 650, 900 ), seed=k )
            near.collision_box( v( e - 10, n - 10, z ), v( e + 10, n + 10, z + 300 ), "wood" )
    # The wood outside: a band west, north and south-west, denser further out; palms among them.
    placed = 0
    for _ in range( 900 ):
        side = rng.random()
        if side < 0.4:
            e, n = rng.uniform( PLAY[0] - 2400, PLAY[0] - 120 ), rng.uniform( -1500, PLAY[3] + 2400 )
        elif side < 0.8:
            e, n = rng.uniform( PLAY[0] - 2400, LEVEE[1] + 200 ), rng.uniform( PLAY[3] + 120, PLAY[3] + 2400 )
        else:
            e, n = rng.uniform( PLAY[0] - 2400, PAD[0] - 120 ), rng.uniform( -3400, 30 )
        z = 0.0
        if ( n < 150 and e < PAD[0] ) or ( n > PLAY[3] and e > LEVEE[0] ):
            z = HIGH
        if e > LEVEE[1] - 60 or ( abs( e - WATER_TOWER[0][0] ) < 350 and abs( n - WATER_TOWER[0][1] ) < 350 ):
            continue
        d_out = max( PLAY[0] - e, n - PLAY[3], -n - 1300, 0 )
        lod = 0 if d_out < 900 else 1
        target = near if lod == 0 else far
        if rng.random() < 0.18:
            P.palm( target, ( e, n, z ), rng.uniform( 320, 520 ), seed=1000 + placed, lod=lod )
        else:
            P.pine( target, ( e, n, z ), rng.uniform( 550, 900 ), seed=1000 + placed, lod=lod )
        placed += 1
    # Across the river: the far bank's wood, then the tree line all round.
    for k in range( 220 ):
        e, n = rng.uniform( LEVEE[1] + 1950, LEVEE[1] + 4500 ), rng.uniform( -3000, PLAY[3] + 2600 )
        if rng.random() < 0.25:
            P.palm( far, ( e, n, 60 ), rng.uniform( 350, 520 ), seed=3000 + k, lod=1 )
        else:
            P.pine( far, ( e, n, 60 ), rng.uniform( 700, 1100 ), seed=3000 + k, lod=1 )
    P.far_trees( far, ( -300, 1100 ), 7600, -20, 1500, count=64, seed=5 )
    P.far_trees( far, ( -300, 1100 ), 9800, -20, 2100, count=72, seed=6 )
    # The woods' floor out to the tree line.
    box( far, -12000, 12000, -12000, 14000, -80, -40, { "default": None, "+z": "rs_yard" } )


def backdrop( m ):
    P.water_tower( m, WATER_TOWER[0], WATER_TOWER[1] )
    # A far-off fire across the river: a glow and smoke above the trees.
    P.FIRES.append( ( "far fire", ( LEVEE[1] + 3200, 2600, 80 ), "far" ) )


# ---------------------------------------------------------------------------------------------------------------------
# Spots and checks

def all_spots():
    spots = [ ( f"player spawn {k}", p ) for k, p in enumerate( PLAYER_SPAWNS ) ]
    spots += [ ( f"zombie spawn {k}", p ) for k, p in enumerate( ZOMBIE_SPAWNS ) ]
    spots += [ ( f"station {kind} {order}", pos ) for kind, order, pos, _ in STATION_SPOTS if kind not in ( "WallWeapon", ) ]
    return spots


# ---------------------------------------------------------------------------------------------------------------------
# The radar picture

MINIMAP_CENTRE = ( -350.0, 1100.0 )
MINIMAP_SIZE = 5200.0
MINIMAP_PIXELS = 1024


def write_minimap( models ):
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "high", "tall", "low" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    shapes = sorted( R.collision_shapes( models ), key=lambda pts: -float( np.ptp( pts[:, 0] ) * np.ptp( pts[:, 1] ) ) )
    for pts in shapes:
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = R.hull_2d( pts[:, :2] )
        if len( outline ) < 3:
            continue
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if -70 <= z1 <= 12:
            draws["walk"].polygon( screen, fill=255 )
        elif HIGH - 10 <= z1 <= HIGH + 12 and z1 - z0 > 40:
            draws["high"].polygon( screen, fill=255 )
        elif z1 - z0 > 60 and z1 > 100:
            draws["tall"].polygon( screen, fill=255 )
        elif z1 > 12:
            draws["low"].polygon( screen, fill=255 )
    walk, high, tall, low = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "high", "tall", "low" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    E, N = np.meshgrid( cols, rows )
    inside = ( E > PLAY[0] ) & ( E < PLAY[1] ) & ( N > PLAY[2] ) & ( N < PLAY[3] )
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk & inside] = ( 92, 86, 78, 235 )
    image[high & inside] = ( 118, 114, 104, 235 )
    image[low & inside] = ( 64, 62, 58, 235 )
    image[tall & inside] = ( 0, 0, 0, 0 )
    shown = ( ( walk | high | low ) & inside ) & ~tall
    edge = np.zeros_like( shown )
    edge[1:, :] |= ~shown[:-1, :]
    edge[:-1, :] |= ~shown[1:, :]
    edge[:, 1:] |= ~shown[:, :-1]
    edge[:, :-1] |= ~shown[:, 1:]
    image[shown & edge] = ( 230, 224, 214, 255 )
    MINIMAP_FILE.parent.mkdir( parents=True, exist_ok=True )
    RM.save_image( Image.fromarray( image, "RGBA" ), MINIMAP_FILE )
    print( f"wrote {MINIMAP_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------
# The scene

def box_collider( key, scale, trigger=True, static=True, center=( 0, 0, 0 ) ):
    return K.component( ids, "Sandbox.BoxCollider", key, Center=K.vec( center ), ColliderFlags=0, Elasticity=None,
                        Friction=None, IsTrigger=trigger, RollingResistance=None, Scale=K.vec( scale ), Static=static,
                        Surface=None, SurfaceVelocity="0,0,0" )


def plan_box( e0, e1, n0, n1, z0, z1 ):
    centre = K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) )
    return centre, ( n1 - n0, e1 - e0, z1 - z0 )


def ref( go_key, component_key, component_type ):
    return { "_type": "component", "component_id": ids( component_key ), "go": ids( go_key ), "component_type": component_type }


# ( model name, scene name, collide, shadows )
SCENE_MODELS = [
    ( "riverside_ground", "Ground", True, True ), ( "riverside_patches", "Ground Patches", False, False ),
    ( "riverside_low", "Lowland Trailers", True, True ), ( "riverside_terrace", "Terrace Trailers", True, True ),
    ( "riverside_levee", "Levee Trailers", True, True ), ( "riverside_store", "Lucky Stop", True, True ),
    ( "riverside_pad", "Pad", True, True ), ( "riverside_dressing", "Dressing", True, True ),
    ( "riverside_fence", "Fence", True, True ), ( "riverside_trees", "Trees", True, True ),
    ( "riverside_far", "Far Woods", False, False ), ( "riverside_backdrop", "Backdrop", False, True ),
]


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return K.game_object( ids, name, key, components=components )


# MapFire settings per kind: width, flame height, flames a second, smoke a second, smoke size, smoke life, shade, embers,
# light radius, brightness, shadows.
FIRE_KINDS = {
    "drum": ( 18, 44, 22, 1.2, 70, 6, 0.24, 6, 380, 2.8, False ),
    "big": ( 160, 120, 40, 6, 640, 18, 0.34, 14, 1100, 4.0, True ),
    "medium": ( 80, 60, 24, 2.5, 300, 12, 0.3, 8, 520, 2.6, False ),
    "far": ( 600, 260, 20, 3, 1400, 18, 0.12, 0, 2400, 5.0, False ),
}


def fire_object( name, key, position, kind ):
    w, h, fps, sps, size, life, shade, eps, radius, bright, shadows = FIRE_KINDS[kind]
    return K.game_object( ids, name, key, K.to_world( position ), components=[
        K.component( ids, "Facepunch.MapFire", f"{key}/fire", Width=w, FlameHeight=h, FlamesPerSecond=fps, SmokePerSecond=sps,
                     SmokeSize=size, SmokeLife=life, SmokeShade=shade, EmbersPerSecond=eps, LightRadius=radius, LightBrightness=bright,
                     LightShadows=shadows, DetailDistance=2500 ) ] )


def look_object():
    """ A moonlit night: the warm lamps and fires bloom, the shadows go blue-teal, a vignette. """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.8, Radius=90,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=7400,
                     BlendFactor=0.35, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.38, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Bloom", "look/bloom", **{ "__version": 1 }, Mode="Additive", Strength=0.35, Threshold=1.1,
                     Tint="1,0.95,0.9,1" ),
        K.component( ids, "Sandbox.ScreenSpaceReflections", "look/ssr" ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=1.5, MaximumExposure=3.5,
                     Mode="ACES", Rate=1 ),
    ] )


HAZE = [ ( "Park Haze", ( PLAY[0] - 600, PLAY[1] + 600, PLAY[2] - 600, PLAY[3] + 600, -60, 1400 ), 0.32, "0.62,0.70,0.85,1" ) ]


def haze_object( name, box_, strength, colour ):
    e0, e1, n0, n1, z0, z1 = box_
    at = K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) )
    half = ( ( n1 - n0 ) / 2, ( e1 - e0 ) / 2, ( z1 - z0 ) / 2 )
    key = f"haze/{name}"
    return K.game_object( ids, name, key, at, components=[
        K.component( ids, "Sandbox.VolumetricFogVolume", f"{key}/volume", Bounds={ "Mins": K.vec( tuple( -h for h in half ) ), "Maxs": K.vec( half ) },
                     FalloffExponent=1, Strength=strength, Color=colour ) ] )


PROBES = [ ( "Store", ( 220, 820, 80 ), ( 70, 370, 640, 1000, 20, 150 ) ), ( "Plaza", ( 0, 300, 100 ), ( -700, 700, -200, 1000, -10, 400 ) ) ]


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


def spot_light_object( name, key, position, target, colour, radius, angle ):
    p = np.asarray( position, float )
    t = np.asarray( target, float )
    d = t - p
    yaw = K.plan_yaw( ( d[0], d[1] ) )
    pitch = math.degrees( math.atan2( -d[2], float( np.linalg.norm( d[:2] ) ) ) )
    return K.game_object( ids, name, key, K.to_world( position ), K.angles_rotation( pitch, yaw ), tags="light_spot,light", components=[
        K.component( ids, "Sandbox.SpotLight", f"{key}/light", Attenuation=1, ConeInner=angle * 0.6, ConeOuter=angle, FogMode="Enabled",
                     FogStrength=1.0, LightColor=colour, Radius=radius, Shadows=True ) ] )


def write_scene( written ):
    world = K.game_object( ids, "Riverside", "world", children=[
        model_object( title, f"world/{name}", name, collide, shadows )
        for name, title, collide, shadows in SCENE_MODELS if name in written ] )
    light_objects = [
        K.game_object( ids, f"{name} {k}", f"light/{k}/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{k}/{name}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
                         LightColor=color, Radius=radius, Shadows=shadows ) ] )
        for k, ( name, position, color, radius, shadows ) in enumerate( P.LIGHTS ) ]
    light_objects += [ spot_light_object( name, f"spot/{k}", pos, target, colour, radius, angle )
                       for k, ( name, pos, target, colour, radius, angle ) in enumerate( P.SPOTLIGHTS ) ]
    fires = [ fire_object( f"Fire {name}", f"fire/{k}", pos, kind ) for k, ( name, pos, kind ) in enumerate( P.FIRES ) ]

    spawns = []
    for k, p in enumerate( PLAYER_SPAWNS ):
        spawns.append( K.game_object( ids, f"Spawn {k + 1}", f"spawn/{k}", K.to_world( p ), K.yaw_rotation( K.plan_yaw( ( 0.05, 1 ) ) ), components=[
            K.component( ids, "TeamSpawnPoint", f"spawn/{k}/point", Team="CounterTerrorist" ) ] ) )
    zombie_spawns = [ K.game_object( ids, f"Zombie Spawn {k + 1}", f"zspawn/{k}", K.to_world( p ), components=[
        K.component( ids, "Facepunch.ZombieSpawnPoint", f"zspawn/{k}/point" ) ] ) for k, p in enumerate( ZOMBIE_SPAWNS ) ]
    station_spots = []
    for k, ( kind, order, pos, facing ) in enumerate( STATION_SPOTS ):
        station_spots.append( K.game_object( ids, f"Station {kind} {order}", f"station/{k}", K.to_world( pos ), K.yaw_rotation( K.plan_yaw( facing ) ),
                                             components=[ K.component( ids, "Facepunch.ZombiesStationSpot", f"station/{k}/spot", Kind=kind, Order=order ) ] ) )

    play_centre, play_scale = plan_box( PLAY[0], PLAY[1], PLAY[2], PLAY[3], -300, 1500 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
    clip_objects = []
    for k, ( name, centre, yaw, size ) in enumerate( RP.CLIPS ):
        key = f"clip/{k}"
        clip_objects.append( K.game_object( ids, f"Player Clip {name} {k}", key, K.to_world( centre ), K.yaw_rotation( yaw - 90.0 ),
                                            tags="playerclip", components=[ box_collider( f"{key}/box", ( size[1], size[0], size[2] ), trigger=False ) ] ) )
    catch = K.game_object( ids, "Catch Floor", "catch", ( 0, 0, CATCH_FLOOR_Z ), components=[
        box_collider( "catch/box", ( 80000, 80000, 100 ), trigger=False ) ] )
    moon_dir = ( -math.sin( math.radians( MOON_YAW ) ), -math.cos( math.radians( MOON_YAW ) ) )

    objects = [
        K.game_object( ids, "Scene Information", "info", components=[
            K.component( ids, "Sandbox.SceneInformation", "info/scene", Title=TITLE, Author=None, Changes="",
                         Description="A Florida trailer park on a river at night, overrun: the Riverside Trailer Park's muddy lanes "
                                     "under a full moon, the Lucky Stop store, burning drums and a guard tower's searchlight. Zombies only.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True, ZombiesOnly=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 2500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        K.game_object( ids, "Moon", "sun", ( 0, 0, 3000 ), K.angles_rotation( MOON_PITCH, K.plan_yaw( moon_dir ) ),
                       tags="light_directional,light", components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor=MOON_COLOUR, ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.035,0.045,0.07,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="3.4,3.4,3.7,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.85", StartDistance=600,
                         EndDistance=12000, FalloffExponent=1.1, Height=3000, VerticalFalloffExponent=1.4 ),
        ] ),
        K.game_object( ids, "Wind", "wind", components=[
            K.component( ids, "Facepunch.WorldWind", "wind/wind", Velocity="0.45,-0.75,0", GustStrength=0.4 ) ] ),
        look_object(),
        world,
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Fires", "fires", children=fires ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in PROBES ] ),
        K.game_object( ids, "Volumetric Fog", "haze", children=[ haze_object( *h ) for h in HAZE ] ),
        K.game_object( ids, "Player Spawns", "spawns", children=spawns ),
        K.game_object( ids, "Zombie Spawns", "zspawns", children=zombie_spawns ),
        K.game_object( ids, "Station Spots", "stations", children=station_spots ),
        play_area,
        K.game_object( ids, "Player Clips", "clips", children=clip_objects ),
        catch,
        K.prefab_instance( ids, ZOMBIES_MODE ),
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
            "Metadata": { "Title": TITLE, "Image": MAP_ART_PATH, "IsVisibleInMenu": "True", "ZombiesOnly": "True", "GameModes": ZOMBIES_MODE },
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
    print( f"wrote {SCENE_FILE.relative_to( K.ROOT )}: {len( P.LIGHTS )} lights ({sum( 1 for l in P.LIGHTS if l[4] )} shadowed), "
           f"{len( P.SPOTLIGHTS )} spots, {len( P.FIRES )} fires, {len( RP.CLIPS )} clips" )


# ---------------------------------------------------------------------------------------------------------------------

def build():
    P.reset()
    ground_m = ground()
    patch_m = K.Model()
    patches( patch_m )
    low, terrace, high, store_m, pad_m, dress, fence, near, far, back = ( K.Model() for _ in range( 10 ) )
    trailers( low, terrace, high )
    store( store_m )
    pad( pad_m )
    dressing( dress )
    P.beam_cone( patch_m, SEARCH_HEAD, SEARCH_TARGET, half_angle=4.5 )
    perimeter( fence )
    trees( near, far )
    backdrop( back )
    models = { "riverside_ground": ground_m, "riverside_patches": patch_m, "riverside_low": low, "riverside_terrace": terrace,
               "riverside_levee": high, "riverside_store": store_m, "riverside_pad": pad_m, "riverside_dressing": dress,
               "riverside_fence": fence, "riverside_trees": near, "riverside_far": far, "riverside_backdrop": back }
    for model in models.values():
        configure( model )
    return models


# The preview's night: everything lit by the moon and a dim sky, a third as bright as the preview's daylight, and what
# glows drawn as it is.
GLOW = { "rs_lit": ( 0.95, 0.78, 0.5 ), "rs_bulb": ( 1.0, 0.85, 0.55 ), "rs_lamp_warm": ( 1.0, 0.8, 0.5 ), "rs_lamp_sodium": ( 1.0, 0.65, 0.3 ),
         "rs_lamp_cool": ( 0.85, 0.9, 1.0 ), "rs_lamp_search": ( 1.0, 1.0, 1.0 ), "rs_ember": ( 1.0, 0.45, 0.1 ), "rs_porch_light": ( 1.0, 0.85, 0.6 ) }
NIGHT = 0.3


def preview_setup():
    PV._colours.clear()
    for paint in RM.all_paints():
        if paint in RM.PAINTED:
            PV._colours[paint] = np.array( RM.PAINTED[paint][0][:3], float ) / 255.0
            continue
        base = paint
        for prefix in ( "rs_siding", "rs_boards" ):
            if paint.startswith( prefix ):
                base = prefix
        for name in ( f"{base}_color.png", f"{base}_color.jpg" ):
            path = RM.OUT_DIR / name
            if path.exists():
                small = Image.open( path ).convert( "RGB" ).resize( ( 64, 32 ) )
                PV._colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
                break
        else:
            PV._colours[paint] = np.array( ( 0.5, 0.5, 0.5 ) )
    for name, tint in { **RM.SIDING_TINTS, **RM.BOARD_TINTS }.items():
        PV._colours[name] = PV._colours.get( name, np.array( ( 0.6, 0.6, 0.6 ) ) ) * np.array( tint ) / 255.0
    PV._colours["rs_paint_red"] = np.array( ( 0.5, 0.05, 0.04 ) )
    PV._colours["rs_paint_white"] = np.array( ( 0.85, 0.85, 0.83 ) )
    PV._colours["rs_blood"] = np.array( ( 0.25, 0.02, 0.02 ) )
    for paint, colour in GLOW.items():
        PV._colours[paint] = np.array( colour ) / NIGHT
        PV.GLOWING.add( paint )
    p, y = math.radians( MOON_PITCH ), math.radians( MOON_YAW )
    PV.SUN = np.array( ( math.sin( y ) * math.cos( p ), math.cos( y ) * math.cos( p ), math.sin( p ) ) )
    PV.SKY = ( np.array( ( 0.10, 0.12, 0.17 ) ), np.array( ( 0.03, 0.04, 0.08 ) ) )
    PV.FOG = np.array( ( 0.05, 0.06, 0.09 ) )


def night_triangles( models, glass=False ):
    tris, normals, colours = PV.triangles( models, glass )
    return tris, normals, np.clip( colours * NIGHT, 0, 1 )


VIEWS = ( ( "reference", REF_EYE, REF_TARGET, REF_FOV ),
          ( "aerial", ( -3200, -3200, 3800 ), ( -300, 1200, 0 ), 60 ),
          ( "store", ( -250, 150, 70 ), ( 220, 600, 80 ), 80 ),
          ( "levee", ( 1000, 300, 170 ), ( 900, 2400, 120 ), 80 ),
          ( "north", ( -560, 3300, 70 ), ( -200, 1500, 100 ), 80 ),
          ( "west", ( -1560, 600, 70 ), ( -1560, 2800, 80 ), 80 ) )


def write_map_art( models ):
    preview_setup()
    shown = [ m for m in models ]
    opaque, glass = night_triangles( shown ), night_triangles( shown, glass=True )
    _, eye, target, fov = VIEWS[0]
    image = PV.perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=fov )
    MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
    RM.save_image( image.resize( ( 1920, 1080 ), Image.LANCZOS ).convert( "RGB" ), MAP_ART_FILE )
    print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", metavar="DIR", help="also write flat views and the reach grid's picture here" )
    parser.add_argument( "--views", nargs="*", help="only these views" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    parser.add_argument( "--no-models", action="store_true", help="don't write the models (checks and previews only)" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture" )
    args = parser.parse_args()

    missing = [ p for p in RM.all_paints() if not ( RM.OUT_DIR / f"{p}.vmat" ).exists() ]
    if missing:
        print( f"run Tools/riverside_materials.py first: no material for {', '.join( missing[:12] )}{'...' if len( missing ) > 12 else ''}" )
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
    if R.UNKNOWN_PAINTS:
        print( f"paints with no material: {', '.join( sorted( R.UNKNOWN_PAINTS ) )}" )

    solid = [ models[name] for name, _, collide, _ in SCENE_MODELS if collide and name in models ]
    print( "checking spots:" )
    problems = R.check_spots( R.collision_aabbs( solid ), all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    out = Path( args.preview ) if args.preview else None
    if out:
        out.mkdir( parents=True, exist_ok=True )
    cut_off = R.check_reach( solid, all_spots(), out / "reach.png" if out else None, bounds=( PLAY[0], PLAY[1], PLAY[2], PLAY[3] ) )
    print( f"  {cut_off} spot(s) cut off from the spawns" )

    if not args.no_scene:
        write_minimap( solid )
        write_scene( written )
    if args.art:
        write_map_art( [ m for name, m in models.items() if name != "riverside_far" ] )
    if out:
        preview_setup()
        shown = [ m for name, m in models.items() if name != "riverside_far" ]
        opaque, glass = night_triangles( shown ), night_triangles( shown, glass=True )
        for name, eye, target, fov in VIEWS:
            if args.views and name not in args.views:
                continue
            PV.perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=fov ).convert( "RGB" ).save( out / f"{name}.png" )
            print( f"wrote {out / f'{name}.png'}" )


if __name__ == "__main__":
    main()
