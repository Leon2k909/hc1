"""
Cerro Blanco: a multiplayer map. The Museo Cerro Blanco, a made-up modern art museum on a white hill above a Mexican
town, built round a courtyard: travertine below and white enamelled panels above, a glass rotunda for its entrance hall,
long galleries either side and a stage in the courtyard under the trees.

    python Tools/cerroblanco_map.py [--preview <dir>] [--no-scene] [--art] [--views <dir>]

Built by script like Lowtide and Railhead, out of map_kit's boxes and polygons, with the pieces in
cerroblanco_parts.py and the museum's own drawn materials from cerroblanco_materials.py (travertine, enamelled panels,
paving, honed stone, the exhibition banners and the sign). Cars come from railhead_props through railhead_map's `use`.
Writes:
- the models, to Assets/models/maps/cerroblanco/: the buildings, the grounds (paving, lawns, walls), the dressing
  (furniture, sculptures, the stage), the glass, the canopies, and the backdrop (the hills and the town below, drawn only);
- the scene, Assets/scenes/maps/CerroBlanco/cerroblanco.scene, rewritten whole on every run (change the layout here,
  not in the editor);
- the cb_ flat paints and cb_glass, Assets/materials/cerroblanco/*.vmat (the drawn ones are cerroblanco_materials');
- the radar picture, ui/minimaps/minimap_cerroblanco.png, and with --art a stand-in menu picture, ui/maps/cerroblanco.png.

Plan coordinates: e east, n north, z up, in inches (map_kit's). Red Team spawns on the forecourt at the north, by the
car park and the museum's sign; Blue Team on the south plaza, past the South Gallery's portico and its red sculptures.

The lanes:
- West: the West Garden's lawns, the West Gallery (two storeys, a stair inside), the garden circle round its bronze
  sphere (bomb site B), and the south-west lawns.
- Middle: the rotunda (the entrance hall), the courtyard with its round boulder planter, the stage with its grand piano,
  the cafe tables, then the South Gallery and its portico.
- East: the promenade, the cafe (its roof is a terrace, up a stair from the courtyard), the North Gallery (two
  storeys), the East Hall with its mezzanine (bomb site A), the covered walkway and the east terrace, and the east lawns.

Every run checks every spawn, objective and cash spot as Lowtide's script does (railhead_map's check_spots,
check_reach and check_retakes_sight), and prints what's wrong. The navmesh stops at NAV_TOP (300), over the first floors
(180) and under the galleries' roofs (344).
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K
from map_kit import Model
import railhead_map as R
import railhead_preview as PV
import cerroblanco_parts as P
import cerroblanco_materials as CM

TITLE = "Cerro Blanco"
OUT_DIR = K.ASSETS / "models/maps/cerroblanco"
RESOURCE_DIR = "models/maps/cerroblanco"
SCENE_FILE = K.ASSETS / "scenes/maps/CerroBlanco/cerroblanco.scene"
MAT_DIR = K.ASSETS / "materials/cerroblanco"
MINIMAP_PATH = "ui/minimaps/minimap_cerroblanco.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_cerroblanco.png"     # the folder is ui/Minimaps on disk
MAP_ART_PATH = "ui/maps/cerroblanco.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "7d2e9b41-3c58-4a6f-b1e0-5f93c8a2d714" )

METAL, STONE, WOOD, GLASS, DIRT, FABRIC = P.METAL, P.STONE, P.WOOD, P.GLASS, P.DIRT, P.FABRIC
TRAV, PANEL, PAVE, HONED = P.TRAV, P.PANEL, P.PAVE, P.HONED
PLASTER, WHITE, FRAME, RED, BLACK, STEEL, TEAK, LAMP = P.PLASTER, P.WHITE, P.FRAME, P.RED, P.BLACK, P.STEEL, P.TEAK, P.LAMP
LAWN, HEDGE, SOIL, ROCK, GRAVEL = P.LAWN, P.HEDGE, P.SOIL, P.ROCK, P.GRAVEL

# Belltower's clear summer afternoon: the same sky, sun and haze.
SUN_PITCH, SUN_YAW = 34.0, -63.0
SKY_MATERIAL = "materials/belltower/sky/belltower_sky.vmat"
SKY_EXPOSURE = 2
FOG_COLOUR = "0.351,0.594,1.048"
CATCH_FLOOR_Z = -3000

PLAY = ( -2560.0, 2520.0, -3250.0, 3080.0 )         # e0, e1, n0, n1
NAV_TOP = 300.0

ROOF = 360.0           # the two-storey galleries' roofs (the West and North Galleries, the East Hall)
FLOOR1 = 180.0         # their first floors (slabs 164..180), and the cafe's roof terrace
SLAB = 164.0
SG_ROOF = 330.0        # the South Gallery: one tall storey
CAFE_TOP = SLAB
DOOR_H = 124.0

ROTUNDA = ( 313.0, 1200.0 )
ROT_IN, ROT_OUT = 375.0, 393.0
GARDEN = ( -1743.0, -1359.0 )    # the garden circle's middle (bomb site B)
GARDEN_R = 560.0                 # its hedge's outside

# Footprints ( e0, e1, n0, n1 ), outside faces.
WG_A = ( -1126.0, -650.0, -160.0, 1510.0 )
WG_B = ( -650.0, -200.0, 1050.0, 1510.0 )
CAFE = ( 480.0, 1000.0, 0.0, 715.0 )
NG = ( 1000.0, 2060.0, -18.0, 715.0 )
EH = ( 480.0, 1400.0, -1000.0, 0.0 )
SG = ( -1030.0, 480.0, -2150.0, -1000.0 )
CAR_PARK = ( 1000.0, 2400.0, 1700.0, 2500.0 )
ROT_SQUARE = ( ROTUNDA[0] - ROT_OUT, ROTUNDA[0] + ROT_OUT, ROTUNDA[1] - ROT_OUT, ROTUNDA[1] + ROT_OUT )
GARDEN_SQUARE = ( GARDEN[0] - GARDEN_R, GARDEN[0] + GARDEN_R, GARDEN[1] - GARDEN_R, GARDEN[1] + GARDEN_R )


# ---------------------------------------------------------------------------------------------------------------------
# Paints

def write_materials():
    """ The drawn materials (if they're missing), the flat cb_ paints and the glass. """
    if CM.missing( CM.OUT_DIR ):
        CM.main( [] )
    MAT_DIR.mkdir( parents=True, exist_ok=True )
    import railhead_materials as RM
    for name, ( colour, metal, rough ) in P.CB_PAINTED.items():
        text = RM.painted_vmat( name, colour, metal, rough ).replace( "Tools/railhead_materials.py", "Tools/cerroblanco_map.py" )
        K.write_text( MAT_DIR / f"{name}.vmat", text )
    glass = ( K.ASSETS / "materials/railhead/rw_glass.vmat" ).read_text( encoding="utf-8" )
    lines = [ "// Tools/cerroblanco_map.py, from materials/railhead/rw_glass.vmat" if line.startswith( "//" ) else line
              for line in glass.splitlines() ]
    K.write_text( MAT_DIR / f"{P.GLAZE}.vmat", "\n".join( lines ) + "\n" )


def configure( model ):
    """ Points the cb_ paints at their materials, then the rest as Railhead's script does (rw_ and building_textures'). """
    for paint in model.polygons:
        if paint.startswith( "cb_" ):
            model.material_overrides[paint] = f"materials/cerroblanco/{paint}.vmat"
            model.tile_overrides[paint] = P.TILED.get( paint, 64.0 )
    R.configure( model )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Walls, roofs and floors

def door( c, w=100.0, z0=0.0, h=DOOR_H ):
    return ( c, w, z0, z0 + h )


def glass( c, w, z0=20.0, z1=190.0 ):
    return ( c, w, z0, z1 )


def upper( c, w=120.0, z0=230.0, z1=330.0 ):
    return ( c, w, z0, z1 )


def lohi( axis, run, across, z0, z1 ):
    if axis == "e":
        return ( run[0], min( across ), z0 ), ( run[1], max( across ), z1 )
    return ( min( across ), run[0], z0 ), ( max( across ), run[1], z1 )


def door_frame( m, axis, d, c, w, z0, z1, thickness ):
    """ A slim anodised frame lining an open doorway (no leaf: bots can't open doors), and its threshold. """
    r0, r1 = c - w / 2, c + w / 2
    t = thickness / 2 + 0.6
    for a, b in ( ( r0, r0 + 2.5 ), ( r1 - 2.5, r1 ) ):
        m.box( *lohi( axis, ( a, b ), ( d - t, d + t ), z0, z1 ), FRAME )
    m.box( *lohi( axis, ( r0, r1 ), ( d - t, d + t ), z1 - 2.5, z1 ), FRAME )
    if z0 > 1:
        lo, hi = lohi( axis, ( r0, r1 ), ( d - thickness / 2, d + thickness / 2 ), z0, z0 )
        m.polygon( HONED, [ ( lo[0], lo[1], z0 + 0.05 ), ( hi[0], lo[1], z0 + 0.05 ), ( hi[0], hi[1], z0 + 0.05 ),
                            ( lo[0], hi[1], z0 + 0.05 ) ], normal=( 0, 0, 1 ) )


def wall( m, g, axis, run, across, outward, z0=0.0, z1=ROOF, doors=(), windows=(), ends=True, lower=TRAV, upper_=PANEL,
          inside=PLASTER, split=P.LOWER_TOP, parapet=False ):
    """ A wall with open doorways and glazed windows: doors and windows are ( centre, width, z0, z1 ). outward None is an
    inside wall (inside paint both sides). parapet puts the roof's parapet on it (z1 .. z1 + 30). """
    openings = [ ( c, w, a, b, "door" ) for c, w, a, b in doors ] + [ ( c, w, a, b, "window" ) for c, w, a, b in windows ]
    if outward:
        P.facade( m, axis, run, across, outward, z0, z1, openings, lower, upper_, inside, ends=ends, split=split )
    else:
        P.inner_wall( m, axis, run, across, z0, z1, openings, paint=inside, ends=ends )
    d = sum( across ) / 2
    thick = abs( across[1] - across[0] )
    for c, w, a, b in windows:
        transoms = ( a + ( b - a ) * 0.64, ) if b - a > 150 else ()
        P.glaze( m, g, axis, d, c - w / 2, c + w / 2, a, b, transoms=transoms )
    for c, w, a, b in doors:
        door_frame( m, axis, d, c, w, a, b, thick )
    if parapet:
        parapet_on( m, axis, run, across, outward, z1 )


def parapet_on( m, axis, run, across, outward, z, h=30.0 ):
    """ The roof's parapet along a wall: enamelled panel both sides, a honed coping with a lip proud of the façade. """
    m.box( *lohi( axis, run, across, z, z + h ), { "default": PANEL, "+z": HONED, "-z": None }, STONE )
    a, b = min( across ), max( across )
    if outward in ( "-n", "-e" ):
        a -= 2.5
    elif outward in ( "+n", "+e" ):
        b += 2.5
    m.box( *lohi( axis, ( run[0] - 2.5, run[1] + 2.5 ), ( a, b ), z + h, z + h + 3 ), HONED )


def roof_slab( m, e0, e1, n0, n1, z, thick=16.0 ):
    m.box( ( e0, n0, z - thick ), ( e1, n1, z ), { "+z": GRAVEL, "-z": PLASTER, "default": None }, STONE )


def floor( m, e0, e1, n0, n1, z=0.0, paint=HONED ):
    m.polygon( paint, [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ], normal=( 0, 0, 1 ) )


def face( m, paint, lo, hi, facing ):
    """ One face of a box, drawn on its own (an end left open by the wall pieces). """
    m.box( lo, hi, { "default": None, facing: paint } )


def column( m, e, n, z0, z1, r=9.0, paint=WHITE, surface=STONE ):
    P.column( m, e, n, z0, z1, r, paint, surface=surface )


# ---------------------------------------------------------------------------------------------------------------------
# The West Gallery: two storeys, L-shaped, round the courtyard's north-west corner

def west_gallery( m, g, d ):
    wall( m, g, "e", ( -1126, -650 ), ( -160, -142 ), "-n", doors=[ door( -890 ) ],
          windows=[ glass( -1030, 120 ), glass( -750, 120 ), upper( -1010 ), upper( -770 ) ], parapet=True )
    wall( m, g, "n", ( -142, 1492 ), ( -1126, -1108 ), "-e", doors=[ door( 200 ), door( 1300 ) ],
          windows=[ glass( 500, 160 ), glass( 800, 160 ), glass( 1030, 140 ),
                    upper( 0 ), upper( 350 ), upper( 650 ), upper( 950 ), upper( 1250 ) ], ends=False, parapet=True )
    wall( m, g, "e", ( -1126, -200 ), ( 1492, 1510 ), "+n", doors=[ door( -650 ) ],
          windows=[ glass( -950, 200 ), glass( -400, 200 ), upper( -1000 ), upper( -800 ), upper( -500 ), upper( -330 ) ],
          parapet=True )
    wall( m, g, "n", ( -142, 1050 ), ( -668, -650 ), "+e", doors=[ door( 100 ), door( 650 ) ],
          windows=[ glass( 380, 300 ), glass( 880, 200 ), upper( 100 ), upper( 380 ), upper( 880 ) ], ends=False, parapet=True )
    wall( m, g, "e", ( -650, -200 ), ( 1050, 1068 ), "-n", windows=[ glass( -300, 120 ), upper( -560 ), upper( -300 ) ],
          parapet=True )
    wall( m, g, "n", ( 1068, 1492 ), ( -218, -200 ), "+e", doors=[ door( 1300 ) ],
          windows=[ glass( 1150, 120 ), upper( 1150 ), upper( 1400 ) ], ends=False, parapet=True )
    # The inside corner of the L, where the east wall meets the north wing's south wall.
    m.box( ( -668, 1050, 0 ), ( -650, 1068, ROOF ), { "default": None, "-e": PLASTER, "+n": PLASTER, "+z": GRAVEL }, STONE )
    parapet_on( m, "e", ( -668, -650 ), ( 1050, 1068 ), None, ROOF )
    floor( m, *WG_A )
    floor( m, *WG_B )
    P.slab( m, -1108, -668, -142, 1492, SLAB, FLOOR1, holes=[ ( -1108, -1030, 400, 700 ) ], top=HONED )
    P.slab( m, -668, -218, 1068, 1492, SLAB, FLOOR1, top=HONED )
    roof_slab( m, -1108, -668, -142, 1492, ROOF )
    roof_slab( m, -668, -218, 1068, 1492, ROOF )
    # The stair up the west wall, and the stairwell's glass balustrade.
    P.flight( m, "n", -1108, -1036, 700, 400, FLOOR1, 0 )
    P.sloped_rail( m, ( -1037, 412, 7.2 ), ( -1037, 690, FLOOR1 ) )
    P.balustrade( m, g, ( -1030, 400 ), ( -1030, 700 ), FLOOR1 )
    P.balustrade( m, g, ( -1108, 400 ), ( -1030, 400 ), FLOOR1 )
    # The galleries inside: white display walls and plinths, the pictures on them.
    for e0, e1, n0, n1, k in ( ( -960, -940, 860, 1180, 0 ), ( -820, -800, 120, 420, 1 ), ( -560, -300, 1260, 1280, 2 ) ):
        P.gallery_wall( d, e0, e1, n0, n1, h=130 )
        long_e = e1 - e0 > n1 - n0
        mid = ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2 )
        for s in ( -1, 1 ):
            if long_e:
                P.picture( d, ( mid[0], n1 if s > 0 else n0 ), 78, 70, 52, ( 0, s ), f"cb_banner_{( k + s ) % 4}" )
            else:
                P.picture( d, ( e1 if s > 0 else e0, mid[1] ), 78, 52, 70, ( s, 0 ), f"cb_banner_{( k + s + 2 ) % 4}" )
    for e, n, thing in ( ( -880, 650, "vase" ), ( -780, 980, True ), ( -900, 1350, "vase" ), ( -420, 1150, True ),
                         ( -880, -40, True ) ):
        P.display_plinth( d, e, n, thing=thing )
    for e0, e1, n0, n1 in ( ( -980, -960, 900, 1250 ), ( -560, -300, 1180, 1200 ) ):
        upstairs_wall( d, e0, e1, n0, n1 )
    for e, n in ( ( -820, 300 ), ( -820, 1060 ), ( -400, 1300 ) ):
        upstairs_plinth( d, e, n )


def upstairs_wall( m, e0, e1, n0, n1, h=120.0 ):
    m.box( ( e0, n0, FLOOR1 ), ( e1, n1, FLOOR1 + h ), { "default": PLASTER, "-z": None }, STONE )


def upstairs_plinth( m, e, n, w=26.0, h=40.0 ):
    m.box( ( e - w / 2, n - w / 2, FLOOR1 ), ( e + w / 2, n + w / 2, FLOOR1 + h ), { "default": WHITE, "-z": None }, STONE )
    P.boulder( m, ( e, n, FLOOR1 + h ), ( 8, 7, 14 ), P.keyed( "bust", e, n ), paint=P.BRONZE, surface=None, points=14 )


# ---------------------------------------------------------------------------------------------------------------------
# The rotunda: the entrance hall, a drum of travertine with a band of glass under its panelled top

def rotunda( m, g, d ):
    c = ROTUNDA
    gaps = [ ( a, 110.0, 0.0, DOOR_H + 6 ) for a in ( 0.0, 90.0, 180.0, 270.0 ) ]
    P.ring( m, c, ROT_IN, ROT_OUT, 0, 220, outer=TRAV, inner=PLASTER, top=HONED, gaps=gaps )
    P.curved_glazing( m, g, c, ( ROT_IN + ROT_OUT ) / 2, 0, 360, 220, 290, transoms=( 255.0, ) )
    P.ring( m, c, ROT_IN, ROT_OUT, 290, 352, outer=PANEL, inner=PLASTER, top=HONED, bottom=HONED )
    P.ring( m, c, ROT_IN + 4, ROT_OUT + 2, 352, 380, outer=PANEL, inner=PANEL, top=HONED, bottom=None )
    m.cylinder( c, ROT_IN + 1, 336, 352, { "side": None, "top": GRAVEL, "bottom": PLASTER }, sides=48, surface=STONE )
    # The oculus' light, a ring of downlights round it and a lantern over it.
    P.disc( m, LAMP, ( c[0], c[1] ), 70, 335.5, facing=-1.0, sides=32 )
    m.cylinder( c, 76, 352, 368, { "side": FRAME, "top": P.GLAZE, "bottom": None }, sides=32 )
    for k in range( 16 ):
        a = 2 * math.pi * ( k + 0.5 ) / 16
        P.disc( m, LAMP, ( c[0] + 250 * math.cos( a ), c[1] + 250 * math.sin( a ) ), 5, 335.5, facing=-1.0, sides=10 )
    # Door frames in the drum's four openings.
    for a in ( 0.0, 90.0, 180.0, 270.0 ):
        u = np.array( ( math.cos( math.radians( a ) ), math.sin( math.radians( a ) ) ) )
        side = np.array( ( -u[1], u[0] ) )
        for s in ( -1, 1 ):
            p = np.array( c ) + u * ( ROT_IN + ROT_OUT ) / 2 + side * s * 54
            m.box( ( p[0] - 2.5, p[1] - 2.5, 0 ), ( p[0] + 2.5, p[1] + 2.5, DOOR_H + 6 ), FRAME )
    # The floor, and the round reception desk with the plinths round it.
    P.disc( m, HONED, c, ROT_OUT, 0.0, sides=48 )
    P.ring( d, c, 54, 66, 0, 42, outer=WHITE, inner=WHITE, top=TEAK, a0=200.0, a1=520.0, step=10.0 )
    for k, a in enumerate( ( 45.0, 135.0, 225.0, 315.0 ) ):
        p = ( c[0] + 230 * math.cos( math.radians( a ) ), c[1] + 230 * math.sin( math.radians( a ) ) )
        P.display_plinth( d, *p, w=34, h=44, thing="vase" if k % 2 else True )
    for k, a in enumerate( ( 20.0, 160.0 ) ):
        p = ( c[0] + 300 * math.cos( math.radians( a ) ), c[1] + 300 * math.sin( math.radians( a ) ) )
        P.bench( d, *p, length=80, along="n" )


# ---------------------------------------------------------------------------------------------------------------------
# The east block: the cafe (its roof a terrace), the North Gallery, the East Hall (bomb site A)

def east_block( m, g, d ):
    # The cafe, one storey, with the roof terrace over it.
    wall( m, g, "n", ( 0, 697 ), ( 480, 498 ), "-e", 0, CAFE_TOP, doors=[ door( 200, 120 ) ], ends=False )
    wall( m, g, "e", ( 480, 1000 ), ( 697, 715 ), "+n", 0, CAFE_TOP, doors=[ door( 740 ) ],
          windows=[ glass( 600, 160, 20, 140 ), glass( 880, 160, 20, 140 ) ] )
    floor( m, *CAFE )
    P.slab( m, 480, 1000, 0, 715, SLAB, FLOOR1, top=PAVE )
    P.balustrade( m, g, ( 482, 0 ), ( 482, 640 ), FLOOR1 )
    P.balustrade( m, g, ( 480, 713 ), ( 1000, 713 ), FLOOR1 )
    # Its stair up from the courtyard, beside its west wall.
    P.flight( m, "n", 420, 480, 640, 340, FLOOR1, 0, side=TRAV )
    m.box( ( 420, 640, 0 ), ( 480, 715, FLOOR1 ), { "+z": HONED, "-z": None, "default": TRAV, "+e": None }, STONE )
    P.sloped_rail( m, ( 421, 352, 7.2 ), ( 421, 630, FLOOR1 ) )
    P.balustrade( m, g, ( 420, 640 ), ( 420, 715 ), FLOOR1 )
    P.balustrade( m, g, ( 420, 713 ), ( 480, 713 ), FLOOR1 )
    # Inside the cafe: its counter along the north wall and tables.
    m.box( ( 540, 600, 0 ), ( 700, 630, 42 ), { "default": WHITE, "+z": HONED, "-z": None }, STONE )
    for e, n in ( ( 620, 220 ), ( 800, 160 ), ( 860, 420 ), ( 640, 440 ) ):
        P.cafe_table( d, e, n )
        for k in range( 3 ):
            a = 120 * k + 30
            P.cafe_chair( d, e + 24 * math.cos( math.radians( a ) ), n + 24 * math.sin( math.radians( a ) ), a + 180 )

    # The wall between the cafe and the East Hall: plaster below the terrace, the hall's panelled front above it.
    wall( m, g, "e", ( 498, 1000 ), ( -18, 0 ), "+n", doors=[ door( 740 ) ], windows=[ upper( 620 ), upper( 880 ) ],
          ends=False, lower=PLASTER, split=FLOOR1, parapet=True )
    # The North Gallery's west wall: plaster into the cafe, panels over the terrace, a door onto it.
    wall( m, g, "n", ( 0, 697 ), ( 1000, 1018 ), "-e", doors=[ door( 350 ), door( 500, 100, FLOOR1, 120 ) ],
          windows=[ upper( 200 ) ], ends=False, lower=PLASTER, split=FLOOR1, parapet=True )

    # The North Gallery.
    wall( m, g, "e", ( 1000, 2060 ), ( 697, 715 ), "+n", doors=[ door( 1300 ), door( 1800 ) ],
          windows=[ glass( 1550, 200 ), upper( 1200 ), upper( 1550 ), upper( 1900 ) ], parapet=True )
    wall( m, g, "n", ( 0, 697 ), ( 2042, 2060 ), "+e", doors=[ door( 200 ) ], windows=[ glass( 450, 160 ), upper( 300 ),
                                                                                       upper( 550 ) ], ends=False, parapet=True )
    wall( m, g, "e", ( 1000, 1400 ), ( -18, 0 ), None, doors=[ door( 1200 ), door( 1300, 100, FLOOR1, 120 ) ], ends=False )
    wall( m, g, "e", ( 1400, 2060 ), ( -18, 0 ), "-n", doors=[ door( 1500 ), door( 1900 ) ],
          windows=[ glass( 1700, 200 ), upper( 1500 ), upper( 1700 ), upper( 1900 ) ], parapet=True )
    parapet_on( m, "e", ( 1000, 1400 ), ( -18, 0 ), None, ROOF )
    floor( m, *NG )
    P.slab( m, 1018, 2042, 0, 697, SLAB, FLOOR1, holes=[ ( 1964, 2042, 300, 600 ) ], top=HONED )
    roof_slab( m, 1018, 2042, 0, 697, ROOF )
    P.flight( m, "n", 1964, 2042, 600, 300, FLOOR1, 0 )
    P.sloped_rail( m, ( 1965, 312, 7.2 ), ( 1965, 590, FLOOR1 ) )
    P.balustrade( m, g, ( 1962, 300 ), ( 1962, 600 ), FLOOR1 )
    P.balustrade( m, g, ( 1962, 300 ), ( 2042, 300 ), FLOOR1 )
    for e0, e1, n0, n1 in ( ( 1300, 1320, 160, 520 ), ( 1640, 1660, 160, 520 ) ):
        P.gallery_wall( d, e0, e1, n0, n1, h=130 )
        for s in ( -1, 1 ):
            P.picture( d, ( e1 if s > 0 else e0, ( n0 + n1 ) / 2 ), 78, 52, 70, ( s, 0 ), f"cb_banner_{( e0 // 20 + s ) % 4}" )
        upstairs_wall( d, e0 + 120, e1 + 120, n0 + 40, n1 - 40 )
    for e, n, thing in ( ( 1150, 350, True ), ( 1480, 120, "vase" ), ( 1480, 580, True ), ( 1820, 350, "vase" ) ):
        P.display_plinth( d, e, n, thing=thing )
    for e, n in ( ( 1200, 150 ), ( 1550, 600 ), ( 1850, 150 ) ):
        upstairs_plinth( d, e, n )

    # The East Hall: tall, open to its roof but for the mezzanine along its east side.
    wall( m, g, "e", ( 480, 1400 ), ( -1000, -982 ), "-n", doors=[ door( 640 ) ],
          windows=[ glass( 900, 240 ), glass( 1200, 160 ), upper( 900 ), upper( 1300 ) ], parapet=True )
    wall( m, g, "n", ( -982, 0 ), ( 480, 498 ), "-e", doors=[ door( -500 ), door( -200 ) ],
          windows=[ glass( -800, 160 ), upper( -650 ), upper( -350 ) ], parapet=True )
    wall( m, g, "n", ( -982, -18 ), ( 1382, 1400 ), "+e", doors=[ door( -500 ), door( -800 ) ],
          windows=[ glass( -250, 160 ), upper( -650 ), upper( -350 ) ], ends=False, parapet=True )
    floor( m, *EH )
    roof_slab( m, 498, 1382, -982, -18, ROOF )
    P.slab( m, 1220, 1382, -982, -18, SLAB, FLOOR1, top=HONED )
    for n in ( -860.0, -620.0, -140.0 ):
        column( m, 1229, n, 0, SLAB, r=8 )
    P.flight( m, "n", 1160, 1220, -330, -630, FLOOR1, 0 )
    m.box( ( 1160, -330, 0 ), ( 1220, -250, FLOOR1 ), { "+z": HONED, "-z": None, "default": PLASTER, "+e": None }, STONE )
    P.sloped_rail( m, ( 1161, -618, 7.2 ), ( 1161, -340, FLOOR1 ) )
    P.balustrade( m, g, ( 1160, -330 ), ( 1160, -250 ), FLOOR1 )
    P.balustrade( m, g, ( 1160, -250 ), ( 1220, -250 ), FLOOR1 )
    P.balustrade( m, g, ( 1222, -982 ), ( 1222, -332 ), FLOOR1 )
    P.balustrade( m, g, ( 1222, -248 ), ( 1222, -18 ), FLOOR1 )
    # Its exhibition: two freestanding walls, plinths and a red piece, for cover round the bomb site.
    for e0, e1, n0, n1 in ( ( 640, 900, -560, -540 ), ( 960, 980, -420, -120 ) ):
        P.gallery_wall( d, e0, e1, n0, n1, h=140 )
    P.picture( d, ( 770, -540 ), 82, 90, 64, ( 0, 1 ), "cb_banner_1" )
    P.picture( d, ( 770, -560 ), 82, 90, 64, ( 0, -1 ), "cb_banner_3" )
    P.picture( d, ( 980, -270 ), 82, 64, 90, ( 1, 0 ), "cb_banner_2" )
    for e, n, thing in ( ( 620, -800, True ), ( 1100, -820, "vase" ), ( 700, -300, "vase" ), ( 1100, -150, True ) ):
        P.display_plinth( d, e, n, w=30, thing=thing )
    P.folded_sculpture( d, 860, -820, yaw=20.0, scale=0.75 )
    for e, n in ( ( 1300, -800 ), ( 1300, -150 ) ):
        upstairs_plinth( d, e, n )


# ---------------------------------------------------------------------------------------------------------------------
# The South Gallery and its portico

def south_gallery( m, g, d, c ):
    wall( m, g, "e", ( -1030, 480 ), ( -1018, -1000 ), "+n", 0, SG_ROOF, doors=[ door( -100, 120 ), door( 300 ) ],
          windows=[ glass( -560, 360 ), glass( 120, 200 ) ], parapet=True )
    wall( m, g, "e", ( -1030, 480 ), ( -2150, -2132 ), "-n", 0, SG_ROOF, doors=[ door( -600 ), door( -100, 120 ), door( 250 ) ],
          windows=[ glass( -850, 260, 20, 230 ), glass( -350, 300, 20, 230 ), glass( 75, 150, 20, 230 ),
                    glass( 390, 110, 20, 230 ) ], parapet=True )
    wall( m, g, "n", ( -2132, -1018 ), ( -1030, -1012 ), "-e", 0, SG_ROOF, doors=[ door( -1300 ), door( -1700 ) ],
          windows=[ glass( -1500, 160 ) ], ends=False, parapet=True )
    wall( m, g, "n", ( -2132, -1018 ), ( 462, 480 ), "+e", 0, SG_ROOF, doors=[ door( -1500 ) ],
          windows=[ glass( -1250, 160 ), glass( -1800, 160 ) ], ends=False, parapet=True )
    floor( m, *SG )
    roof_slab( m, -1012, 462, -2132, -1018, SG_ROOF )
    # Skylights' light in the ceiling.
    for e in ( -800.0, -400.0, 0.0, 300.0 ):
        P.disc( m, LAMP, ( e, -1575 ), 40, SG_ROOF - 16.5, facing=-1.0, sides=20 )
    # The galleries: long display walls across it, plinths and the pictures.
    for e0, e1, n0, n1 in ( ( -780, -760, -1900, -1560 ), ( -400, -380, -1560, -1200 ), ( 60, 80, -1900, -1560 ),
                            ( -260, 40, -1780, -1760 ) ):
        P.gallery_wall( d, e0, e1, n0, n1, h=150 )
        long_e = e1 - e0 > n1 - n0
        for s in ( -1, 1 ):
            k = int( abs( e0 ) // 40 + s ) % 4
            if long_e:
                P.picture( d, ( ( e0 + e1 ) / 2, n1 if s > 0 else n0 ), 84, 100, 72, ( 0, s ), f"cb_banner_{k}" )
            else:
                P.picture( d, ( e1 if s > 0 else e0, ( n0 + n1 ) / 2 ), 84, 72, 100, ( s, 0 ), f"cb_banner_{k}" )
    for e, n, thing in ( ( -900, -1250, True ), ( -560, -1400, "vase" ), ( -150, -1400, True ), ( 250, -1300, "vase" ),
                         ( 300, -1900, True ), ( -560, -1950, "vase" ) ):
        P.display_plinth( d, e, n, w=30, thing=thing )
    P.bronze_sphere( d, -200, -1230, r=40, plinth=30 )

    # The portico along its south front: slim white columns under a deep louvred sunshade.
    for k in range( 10 ):
        e = -1000 + k * 160
        column( m, e, -2380, 0, 256, r=9 )
    top, bottom = 272.0, 256.0
    c.box( ( -1060, -2420, bottom ), ( 510, -2400, top ), WHITE )
    c.box( ( -1060, -2400, bottom ), ( -1040, -2150, top ), WHITE )
    c.box( ( 490, -2400, bottom ), ( 510, -2150, top ), WHITE )
    c.box( ( -1060, -2170, bottom ), ( 510, -2150, top ), WHITE )
    for k in range( 1, 87 ):
        e = -1060 + k * 18
        c.box( ( e - 1, -2400, bottom + 2 ), ( e + 1, -2170, top - 1 ), WHITE )
    c.collision_box( ( -1060, -2420, bottom ), ( 510, -2150, top ), METAL )
    for k in range( 9 ):
        P.disc( c, LAMP, ( -920 + k * 160, -2285 ), 6, bottom - 0.5, facing=-1.0, sides=10 )


# ---------------------------------------------------------------------------------------------------------------------
# The grounds: paving everywhere but under the buildings, lawns, the gardens, the perimeter

def pave_around( m, rect, holes, z=0.0, paint=PAVE ):
    """ Paving over rect, less the holes, in rectangles. """
    e0, e1, n0, n1 = rect
    es = sorted( { e0, e1 } | { h[k] for h in holes for k in ( 0, 1 ) if e0 < h[k] < e1 } )
    ns = sorted( { n0, n1 } | { h[k] for h in holes for k in ( 2, 3 ) if n0 < h[k] < n1 } )
    for a, b in zip( es, es[1:] ):
        for c, d in zip( ns, ns[1:] ):
            me, mn = ( a + b ) / 2, ( c + d ) / 2
            if any( h[0] <= me <= h[1] and h[2] <= mn <= h[3] for h in holes ):
                continue
            floor( m, a, b, c, d, z, paint )


def square_round( m, square, centre, r, paint, z=0.0, step=7.5 ):
    """ Paving between a square and the circle inside it, in fans (the 45 degree rays meet the corners). """
    e0, e1, n0, n1 = square
    half = ( e1 - e0 ) / 2
    ce, cn = centre
    count = int( round( 360 / step ) )

    def on_square( a ):
        u = np.array( ( math.cos( a ), math.sin( a ) ) )
        t = half / max( abs( u[0] ), abs( u[1] ) )
        return ( ce + u[0] * t, cn + u[1] * t )

    for k in range( count ):
        a0, a1 = 2 * math.pi * k / count, 2 * math.pi * ( k + 1 ) / count
        p0 = ( ce + r * math.cos( a0 ), cn + r * math.sin( a0 ) )
        p1 = ( ce + r * math.cos( a1 ), cn + r * math.sin( a1 ) )
        s0, s1 = on_square( a0 ), on_square( a1 )
        P.card( m, paint, [ ( *p0, z ), ( *s0, z ), ( *s1, z ), ( *p1, z ) ], ( 0, 0, 1 ) )


def annulus( m, centre, r0, r1, z, paint, a0=0.0, a1=360.0, step=7.5 ):
    pts0, pts1 = P.arc_points( centre, r0, a0, a1, step ), P.arc_points( centre, r1, a0, a1, step )
    for k in range( len( pts0 ) - 1 ):
        quad = [ ( *pts0[k], z ), ( *pts1[k], z ), ( *pts1[k + 1], z ), ( *pts0[k + 1], z ) ]
        if r0 < 1e-6:
            quad = [ quad[0], quad[1], quad[2] ]
        P.card( m, paint, quad, ( 0, 0, 1 ) )


def garden_circle( m, d ):
    """ Bomb site B: a hedged circle round the bronze sphere, lawns in its quarters, gravel and paths. """
    c = GARDEN
    gaps = [ ( a, 110.0, 0.0, 60.0 ) for a in ( 0.0, 90.0, 180.0, 270.0 ) ]
    P.ring( m, c, GARDEN_R - 40, GARDEN_R, 0, 44, outer=HEDGE, inner=HEDGE, top=HEDGE, reveal=HEDGE, gaps=gaps, surface=WOOD,
            step=6.0 )
    square_round( m, GARDEN_SQUARE, c, GARDEN_R - 20, PAVE )
    annulus( m, c, 0, GARDEN_R - 20, 0.0, GRAVEL, step=6.0 )
    # The lawn's quarters, between the paths.
    for k in range( 4 ):
        a0 = 90 * k + 12.0
        annulus( m, c, 196, 466, 1.0, LAWN, a0, a0 + 66.0, step=6.0 )
        P.ring( m, c, 466, 474, 0, 3, outer=HONED, inner=HONED, top=HONED, a0=a0, a1=a0 + 66.0, step=6.0, surface=None )
        P.ring( m, c, 188, 196, 0, 3, outer=HONED, inner=HONED, top=HONED, a0=a0, a1=a0 + 66.0, step=6.0, surface=None )
    for a in ( 0.0, 90.0, 180.0, 270.0 ):
        u = np.array( ( math.cos( math.radians( a ) ), math.sin( math.radians( a ) ) ) )
        side = np.array( ( -u[1], u[0] ) )
        corners = [ np.array( c ) + u * r + side * s * 52 for r, s in ( ( 180, -1 ), ( GARDEN_R - 20, -1 ), ( GARDEN_R - 20, 1 ), ( 180, 1 ) ) ]
        P.card( m, PAVE, [ ( *p, 1.4 ) for p in corners ], ( 0, 0, 1 ) )
    annulus( m, c, 0, 188, 1.6, PAVE, step=6.0 )
    P.bronze_sphere( d, c[0], c[1] )
    # Low boulders and benches in the quarters, for cover round the site.
    for k, ( a, r, size ) in enumerate( ( ( 45, 320, ( 34, 26, 28 ) ), ( 140, 300, ( 30, 30, 34 ) ), ( 228, 340, ( 38, 28, 30 ) ),
                                         ( 312, 290, ( 26, 24, 26 ) ), ( 70, 400, ( 22, 20, 20 ) ), ( 200, 410, ( 24, 22, 22 ) ) ) ):
        p = ( c[0] + r * math.cos( math.radians( a ) ), c[1] + r * math.sin( math.radians( a ) ), 1.0 )
        P.boulder( d, p, size, 700 + k )
    for a in ( 22.5, 112.5, 202.5, 292.5 ):
        p = ( c[0] + 240 * math.cos( math.radians( a ) ), c[1] + 240 * math.sin( math.radians( a ) ) )
        along = "e" if abs( math.cos( math.radians( a ) ) ) < 0.75 else "n"
        P.bench( d, *p, length=72, along=along )
    for a in ( 45.0, 135.0, 225.0, 315.0 ):
        p = ( c[0] + 620 * math.cos( math.radians( a ) ), c[1] + 620 * math.sin( math.radians( a ) ) )
        if PLAY[0] + 80 < p[0] < PLAY[1] - 80:
            P.tree( d, *p, f"{P.OAK}/tree_oak_medium_a.vmdl", 0.9 )


def courtyard( m, d ):
    """ The courtyard: the round boulder planter, the stage with its piano, hedges in planters, trees, benches and the
    cafe's tables. """
    P.round_planter( d, ( -80, -350 ), 270, seed=4 )
    P.stage( d, -630, -370, 830, 1030, front="-n" )
    P.grand_piano( d, -500, 930, 30, 180.0 )
    P.speaker( d, -610, 800, 0, -90.0 )
    P.speaker( d, -390, 800, 0, -90.0 )
    P.speaker( d, -560, 1000, 30, -90.0, tall=False )
    for e0, e1, n0, n1 in ( ( -620, -420, -900, -860 ), ( -620, -580, -900, -700 ), ( 280, 440, -900, -860 ),
                            ( 400, 440, -900, -700 ), ( -560, -200, 380, 420 ), ( 100, 340, 380, 420 ) ):
        P.hedge_box( d, e0, e1, n0, n1, height=30, planter=16 )
    for e, n in ( ( -500, -560 ), ( 300, -560 ), ( -500, 600 ), ( 200, 620 ) ):
        P.tree( d, e, n, f"{P.OAK}/tree_oak_medium_a.vmdl", 1.0 )
    for e, n, along in ( ( -250, -800, "e" ), ( 100, -800, "e" ), ( -420, 150, "n" ), ( -280, 520, "e" ), ( 220, 520, "e" ) ):
        P.bench( d, e, n, length=90, along=along )
    for e, n in ( ( 260, 110 ), ( 380, 130 ), ( 270, 260 ), ( 390, 290 ) ):
        P.cafe_table( d, e, n )
        for k in range( 2 ):
            a = 180 * k + 20
            P.cafe_chair( d, e + 24 * math.cos( math.radians( a ) ), n + 24 * math.sin( math.radians( a ) ), a + 180 )
        P.parasol( d, e, n, r=44 )
    for e, n in ( ( -600, -150 ), ( 430, -150 ), ( -600, 780 ), ( 430, 760 ) ):
        P.bollard_light( d, e, n )
    for e, n in ( ( -150, 50 ), ( 380, -650 ) ):
        P.litter_bin( d, e, n )


def west_walk( m, d, c ):
    """ The pergola between the West Gallery and the South Gallery: white posts, beams and slats overhead. """
    for e in ( -1100.0, -676.0 ):
        for n in np.linspace( -980, -190, 6 ):
            column( d, e, n, 0, 118, r=5, surface=STONE )
    for n in np.linspace( -980, -190, 6 ):
        c.box( ( -1110, n - 2.5, 118 ), ( -666, n + 2.5, 128 ), WHITE )
    for e in ( -1100.0, -676.0 ):
        c.box( ( e - 3, -990, 128 ), ( e + 3, -180, 136 ), WHITE )
    for e in np.arange( -1080, -680, 20 ):
        c.box( ( e - 1, -990, 136 ), ( e + 1, -180, 138 ), WHITE )
    for n, along in ( ( -720, "n" ), ( -420, "n" ) ):
        P.bench( d, -1060, n, length=96, along=along )
        P.bench( d, -716, n, length=96, along=along )


def grounds( m, d, c ):
    holes = [ WG_A, WG_B, CAFE, NG, EH, SG, ROT_SQUARE, GARDEN_SQUARE, CAR_PARK ]
    pave_around( m, ( PLAY[0], PLAY[1], PLAY[2], PLAY[3] ), holes )
    square_round( m, ROT_SQUARE, ROTUNDA, ROT_OUT, PAVE )
    m.collision_box( ( PLAY[0] - 600, PLAY[2] - 600, -24 ), ( PLAY[1] + 600, PLAY[3] + 600, 0 ), STONE )
    garden_circle( m, d )
    courtyard( m, d )
    west_walk( m, d, c )

    # The west garden: lawns, trees, hedges.
    for e0, e1 in ( ( -2480, -1900 ), ( -1800, -1220 ) ):
        for n0, n1 in ( ( -700, -100 ), ( 0, 600 ), ( 700, 1430 ) ):
            P.lawn( m, e0, e1, n0, n1 )
    for e, n, s in ( ( -2300, -500, 1.0 ), ( -2050, -250, 0.9 ), ( -1600, -450, 1.0 ), ( -1350, -200, 0.8 ), ( -2250, 200, 1.1 ),
                     ( -2000, 450, 0.9 ), ( -1550, 150, 1.0 ), ( -1350, 450, 0.9 ), ( -2300, 900, 1.0 ), ( -2050, 1250, 1.1 ),
                     ( -1600, 1000, 1.0 ), ( -1350, 1300, 0.9 ) ):
        P.tree( d, e, n, f"{P.OAK}/tree_oak_medium_a.vmdl", s, z=6.5, grate=False )
    for e0, e1, n0, n1 in ( ( -2400, -2100, -360, -330 ), ( -1700, -1500, 280, 310 ), ( -2200, -1980, 1050, 1080 ),
                            ( -1720, -1690, 760, 1000 ), ( -2400, -2370, 350, 560 ) ):
        P.hedge_box( d, e0, e1, n0, n1, height=38, z0=6.5 )
    for e, n, along in ( ( -1850, -40, "e" ), ( -1850, 650, "e" ), ( -1170, 900, "n" ), ( -1170, -400, "n" ) ):
        P.bench( d, e, n, length=80, along=along )

    # The south-west lawns.
    for e0, e1, n0, n1 in ( ( -2480, -1900, -2340, -2010 ), ( -1800, -1300, -2340, -2010 ) ):
        P.lawn( m, e0, e1, n0, n1 )
    for e, n in ( ( -2300, -2200 ), ( -2000, -2100 ), ( -1600, -2250 ), ( -1400, -2100 ) ):
        P.tree( d, e, n, f"{P.OAK}/tree_oak_medium_a.vmdl", 1.0, z=6.5, grate=False )
    P.hedge_box( d, -1760, -1500, -2140, -2110, height=38, z0=6.5 )

    # The south plaza: the red sculptures, planters, benches.
    P.spire_sculpture( d, -300, -2650 )
    P.folded_sculpture( d, 400, -2620, yaw=-15.0 )
    for e0, e1, n0, n1 in ( ( -1200, -900, -2750, -2600 ), ( 900, 1200, -2750, -2600 ), ( -1500, -1300, -3050, -2900 ),
                            ( 1300, 1500, -3050, -2900 ) ):
        m.box( ( e0, n0, 0 ), ( e1, n1, 30 ), { "+z": None, "-z": None, "default": TRAV }, STONE )
        m.polygon( SOIL, [ ( e0 + 6, n0 + 6, 26 ), ( e1 - 6, n0 + 6, 26 ), ( e1 - 6, n1 - 6, 26 ), ( e0 + 6, n1 - 6, 26 ) ],
                   normal=( 0, 0, 1 ) )
        m.box( ( e0, n0, 30 ), ( e1, n0 + 6, 32 ), HONED )
        m.box( ( e0, n1 - 6, 30 ), ( e1, n1, 32 ), HONED )
        m.box( ( e0, n0 + 6, 30 ), ( e0 + 6, n1 - 6, 32 ), HONED )
        m.box( ( e1 - 6, n0 + 6, 30 ), ( e1, n1 - 6, 32 ), HONED )
        P.tree( d, ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, f"{P.OAK}/tree_oak_small_a.vmdl", 1.0, z=26, grate=False )
        for k in range( 3 ):
            P.bush( d, e0 + ( e1 - e0 ) * ( k + 0.5 ) / 3, n0 + 30, 26, f"{P.BEECH}/beech_bush_regular_small.vmdl", 0.8 )
    for e, n in ( ( -700, -2700 ), ( 0, -2700 ), ( 700, -2700 ) ):
        P.bench( d, e, n, length=110, along="e" )
    for e in np.linspace( -1000, 450, 6 ):
        P.bollard_light( d, e, -2470 )

    # The east: the lawn by the South Gallery, the terrace, the covered walkway, the strip, the promenade and garden.
    for e0, e1, n0, n1 in ( ( 620, 1300, -2320, -1320 ), ( 1440, 2420, -2320, -1720 ), ( 1440, 2420, -1620, -1320 ) ):
        P.lawn( m, e0, e1, n0, n1 )
    for e, n in ( ( 800, -2100 ), ( 1100, -1800 ), ( 800, -1500 ), ( 1700, -2050 ), ( 2150, -1900 ), ( 1800, -1450 ),
                  ( 2250, -1480 ) ):
        P.tree( d, e, n, f"{P.OAK}/tree_oak_medium_a.vmdl", 1.0, z=6.5, grate=False )
    P.hedge_box( d, 950, 1250, -1600, -1570, height=38, z0=6.5 )
    P.hedge_box( d, 1600, 1630, -2250, -1900, height=38, z0=6.5 )
    for e0, e1, n0, n1 in ( ( 1800, 2000, -900, -840 ), ( 2200, 2400, -500, -440 ), ( 1800, 1860, -400, -150 ),
                            ( 2250, 2310, -1100, -900 ) ):
        P.hedge_box( d, e0, e1, n0, n1, height=30, planter=18 )
    for e, n in ( ( 1950, -300 ), ( 2350, -800 ) ):
        P.tree( d, e, n, f"{P.OAK}/tree_oak_small_a.vmdl", 1.0 )
    for e, n, along in ( ( 2050, -700, "e" ), ( 2300, -250, "n" ), ( 1950, -1050, "e" ) ):
        P.bench( d, e, n, length=90, along=along )
    covered_walkway( m, d, c )
    for e0, e1, n0, n1 in ( ( 2150, 2210, 100, 360 ), ( 2350, 2410, 380, 640 ) ):
        P.hedge_box( d, e0, e1, n0, n1, height=30, planter=18 )
    P.tree( d, 2300, 200, f"{P.OAK}/tree_oak_small_a.vmdl", 1.0 )
    for e in ( 900.0, 1250.0, 1600.0, 1950.0, 2300.0 ):
        P.tree( d, e, 900, f"{P.OAK}/tree_oak_medium_a.vmdl", 0.95 )
        P.bench( d, e + 140, 1040, length=90, along="e" )
    for e0, e1 in ( ( 1150, 1700 ), ( 1850, 2450 ) ):
        P.lawn( m, e0, e1, 1160, 1450 )
    for e, n in ( ( 1300, 1300 ), ( 1550, 1350 ), ( 2000, 1280 ), ( 2300, 1350 ) ):
        P.tree( d, e, n, f"{P.OAK}/tree_oak_medium_a.vmdl", 1.0, z=6.5, grate=False )
    P.hedge_box( d, 1350, 1500, 1200, 1230, height=38, z0=6.5 )
    P.hedge_box( d, 2050, 2250, 1380, 1410, height=38, z0=6.5 )

    forecourt( m, d )
    perimeter( m )


def covered_walkway( m, d, c ):
    """ A flat white canopy on slim columns along the East Hall's east wall, from the North Gallery to the lawns. """
    for n in np.arange( -1170, -20, 190 ):
        column( m, 1625, n, 0, 200, r=6 )
    c.box( ( 1400, -1190, 200 ), ( 1640, -18, 210 ), { "default": WHITE, "-z": WHITE, "+z": GRAVEL } )
    c.collision_box( ( 1400, -1190, 200 ), ( 1640, -18, 210 ), METAL )
    for n in np.arange( -1100, -60, 160 ):
        P.disc( c, LAMP, ( 1520, n ), 6, 199.5, facing=-1.0, sides=10 )


def forecourt( m, d ):
    """ The forecourt: the museum's sign on its low wall, planters, the car park, the spawn's edge. """
    m.box( ( -900, 2280, 0 ), ( 300, 2310, 120 ), { "default": TRAV, "+z": HONED, "-z": None }, STONE )
    P.sign_letters( m, ( -300, 2310 ), 40, 900, ( 0, 1 ) )
    P.sign_letters( m, ( -300, 2280 ), 40, 900, ( 0, -1 ) )
    for e0, e1, n0, n1 in ( ( -1600, -1000, 1800, 1860 ), ( -1600, -1540, 1860, 2200 ), ( 500, 800, 1900, 1960 ),
                            ( -2300, -1900, 2400, 2460 ), ( 300, 700, 2600, 2650 ) ):
        P.hedge_box( d, e0, e1, n0, n1, height=30, planter=18 )
    for e, n in ( ( -1300, 2050 ), ( -2100, 2200 ), ( -2100, 1750 ), ( 650, 2200 ), ( -400, 1900 ), ( -800, 2600 ),
                  ( 900, 2700 ), ( -1800, 2800 ) ):
        P.tree( d, e, n, f"{P.OAK}/tree_oak_medium_a.vmdl", 1.0 )
    for e, n, along in ( ( -800, 2200, "e" ), ( 200, 2200, "e" ), ( -1900, 2050, "n" ) ):
        P.bench( d, e, n, length=96, along=along )
    # The car park: asphalt, bays, kerbs, cars.
    e0, e1, n0, n1 = CAR_PARK
    floor( m, e0, e1, n0, n1, 0.0, "rw_asphalt" )
    for row_n, facing in ( ( n0 + 20, "+n" ), ( n1 - 20, "-n" ) ):
        for k in range( 13 ):
            e = e0 + 60 + k * 100
            if row_n < ( n0 + n1 ) / 2:
                m.polygon( "rw_line_white", [ ( e - 2, n0 + 4, 0.3 ), ( e + 2, n0 + 4, 0.3 ), ( e + 2, n0 + 200, 0.3 ),
                                               ( e - 2, n0 + 200, 0.3 ) ], normal=( 0, 0, 1 ) )
            else:
                m.polygon( "rw_line_white", [ ( e - 2, n1 - 200, 0.3 ), ( e + 2, n1 - 200, 0.3 ), ( e + 2, n1 - 4, 0.3 ),
                                               ( e - 2, n1 - 4, 0.3 ) ], normal=( 0, 0, 1 ) )
    for lo, hi in ( ( ( e0, n0 ), ( e1, n0 + 6 ) ), ( ( e0, n1 - 6 ), ( e1, n1 ) ), ( ( e1 - 6, n0 ), ( e1, n1 ) ) ):
        m.box( ( lo[0], lo[1], 0 ), ( hi[0], hi[1], 5 ), { "default": "rw_kerb", "-z": None } )
    m.box( ( e0, ( n0 + n1 ) / 2 - 40, 0 ), ( e1 - 200, ( n0 + n1 ) / 2 + 40, 6 ), { "default": HONED, "-z": None }, STONE )
    for k, e in enumerate( np.linspace( e0 + 300, e1 - 400, 4 ) ):
        P.tree( d, e, ( n0 + n1 ) / 2, f"{P.OAK}/tree_oak_small_a.vmdl", 0.9, z=6, grate=False )
    cars = [ ( "car", 1110, n0 + 100, "+n", "rw_car_white", {} ), ( "suv", 1310, n0 + 105, "+n", "rw_car_grey", { "plate": "HK 3148" } ),
             ( "car", 1610, n0 + 100, "+n", "rw_car_red", {} ), ( "car", 1910, n0 + 100, "+n", "rw_car_silver", {} ),
             ( "van", 2210, n0 + 120, "+n", "rw_car_white", { "plate": "WD 4813" } ), ( "car", 1210, n1 - 100, "-n", "rw_car_blue", {} ),
             ( "car", 1510, n1 - 100, "-n", "rw_car_black", {} ), ( "suv", 2010, n1 - 105, "-n", "rw_car_white", { "plate": "KL 1384" } ) ]
    for name, e, n, along, paint, kw in cars:
        R.use( name, d, e, n, along, paint, **kw )


def perimeter( m ):
    """ A travertine wall round the play, 96 high, with a coping. """
    e0, e1, n0, n1 = PLAY
    t = 18.0
    pieces = [ ( ( e0, n0 - t ), ( e1, n0 ) ), ( ( e0, n1 ), ( e1, n1 + t ) ), ( ( e0 - t, n0 - t ), ( e0, n1 + t ) ),
               ( ( e1, n0 - t ), ( e1 + t, n1 + t ) ) ]
    for lo, hi in pieces:
        m.box( ( lo[0], lo[1], 0 ), ( hi[0], hi[1], 96 ), { "default": TRAV, "+z": None, "-z": None }, STONE )
        m.box( ( lo[0] - 2, lo[1] - 2, 96 ), ( hi[0] + 2, hi[1] + 2, 100 ), HONED )


# ---------------------------------------------------------------------------------------------------------------------
# The backdrop: the hill falling away to the south and west, the town on its slopes, the sierra beyond

def terrain_z( e, n ):
    """ The land outside the play: level with it at its edge, rising to the north and east, falling to the south and
    west towards the town and the valley. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    de = np.maximum( 0, np.maximum( PLAY[0] - e, e - PLAY[1] ) )
    dn = np.maximum( 0, np.maximum( PLAY[2] - n, n - PLAY[3] ) )
    dist = np.hypot( de, dn )
    bearing = np.arctan2( n - 0, e - 0 )
    slope = 0.18 * np.sin( bearing ) + 0.06 * np.cos( bearing )
    swell = 260 * np.sin( e / 2300.0 ) * np.cos( n / 1900.0 ) + 140 * np.sin( ( e + n ) / 1100.0 )
    far = np.clip( ( dist - 9000 ) / 6000, 0, 1 )
    z = slope * dist + swell * np.clip( dist / 1500, 0, 1 ) + far * 2200
    return np.where( dist < 1, 0.0, z * np.clip( dist / 600, 0, 1 ) )


def backdrop():
    m = Model()
    es = sorted( set( np.arange( PLAY[0], -20000, -500 ).tolist() + np.linspace( PLAY[0], PLAY[1], 11 ).tolist()
                      + np.arange( PLAY[1], 20000, 500 ).tolist() ) )
    ns = sorted( set( np.arange( PLAY[2], -20000, -500 ).tolist() + np.linspace( PLAY[2], PLAY[3], 13 ).tolist()
                      + np.arange( PLAY[3], 20000, 500 ).tolist() ) )
    E, N = np.meshgrid( es, ns, indexing="ij" )
    Z = terrain_z( E, N )
    for i in range( len( es ) - 1 ):
        for j in range( len( ns ) - 1 ):
            me, mn = ( es[i] + es[i + 1] ) / 2, ( ns[j] + ns[j + 1] ) / 2
            if PLAY[0] <= me <= PLAY[1] and PLAY[2] <= mn <= PLAY[3]:
                continue
            quad = [ ( es[i], ns[j], Z[i, j] ), ( es[i + 1], ns[j], Z[i + 1, j] ), ( es[i + 1], ns[j + 1], Z[i + 1, j + 1] ),
                     ( es[i], ns[j + 1], Z[i, j + 1] ) ]
            z = float( np.mean( [ q[2] for q in quad ] ) )
            dist = math.hypot( max( 0, PLAY[0] - me, me - PLAY[1] ), max( 0, PLAY[2] - mn, mn - PLAY[3] ) )
            paint = LAWN if dist < 1200 else ( SOIL if ( z > 900 or P.chance( 0.25, "tb", i, j ) ) else "lawn" )
            if z > 1500:
                paint = ROCK
            m.polygon( paint, quad[:3] )
            m.polygon( paint, [ quad[0], quad[2], quad[3] ] )
    # The white town on the slopes below: houses with tiled roofs, among the trees.
    rng = np.random.default_rng( 7 )
    placed = 0
    while placed < 170:
        e, n = rng.uniform( -14000, 14000 ), rng.uniform( -14000, 14000 )
        de = max( 0, PLAY[0] - e, e - PLAY[1] )
        dn = max( 0, PLAY[2] - n, n - PLAY[3] )
        dist = math.hypot( de, dn )
        if dist < 1400 or dist > 9000 or ( n > 0 and rng.random() < 0.7 ):
            continue
        z = float( terrain_z( e, n ) )
        w, l, h = rng.uniform( 260, 520 ), rng.uniform( 300, 700 ), rng.uniform( 150, 320 )
        yaw = rng.choice( ( 0.0, 90.0 ) ) + rng.uniform( -12, 12 )
        paint = ( "whitewash", "render_pale", "render_cream", "whitewash", "render_ochre", "render_rose" )[placed % 6]
        house( m, e, n, z - 60, w, l, h, yaw, paint )
        placed += 1
    for k in range( 260 ):
        e, n = rng.uniform( -9000, 9000 ), rng.uniform( -9000, 9000 )
        dist = math.hypot( max( 0, PLAY[0] - e, e - PLAY[1] ), max( 0, PLAY[2] - n, n - PLAY[3] ) )
        if 500 < dist < 6000:
            z = float( terrain_z( e, n ) )
            m.props.append( { "path": f"{P.OAK}/tree_oak_medium_a.vmdl" if k % 3 else f"{P.OAK}/tree_oak_dry_medium_a.vmdl",
                              "position": ( e, n, z - 10 ), "yaw": float( rng.uniform( 0, 360 ) ),
                              "scale": ( 1.2, 1.2, 1.2 ), "name": "Backdrop Tree" } )
    return m


def house( m, e, n, z0, w, l, h, yaw, paint ):
    """ A plain rendered house with a low hipped tiled roof (no collision: it's backdrop). """
    x, y, _ = P.turned( 0, 0, yaw )
    o = np.array( ( e, n, z0 ) )

    def at( a, b, c ):
        return o + x * a + y * b + np.array( ( 0, 0, c ) )

    m.oriented_box( at( 0, 0, h / 2 ), ( x, y, ( 0, 0, 1 ) ), ( w, l, h ), { "default": paint, "-z": None } )
    eave = 18
    corners = [ at( sx * ( w / 2 + eave ), sy * ( l / 2 + eave ), h ) for sx, sy in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ]
    rise = min( w, l ) * 0.22
    ridge = [ at( 0, -( l - w ) / 2 if l > w else 0, h + rise ), at( 0, ( l - w ) / 2 if l > w else 0, h + rise ) ]
    centre = at( 0, 0, h )
    P.card( m, "roof_tiles", [ corners[0], corners[1], ridge[0] ], ( corners[0] + corners[1] ) / 2 - centre + ( 0, 0, 60 ) )
    P.card( m, "roof_tiles", [ corners[2], corners[3], ridge[1] ], ( corners[2] + corners[3] ) / 2 - centre + ( 0, 0, 60 ) )
    P.card( m, "roof_tiles", [ corners[1], corners[2], ridge[1], ridge[0] ], ( corners[1] + corners[2] ) / 2 - centre + ( 0, 0, 60 ) )
    P.card( m, "roof_tiles", [ corners[3], corners[0], ridge[0], ridge[1] ], ( corners[3] + corners[0] ) / 2 - centre + ( 0, 0, 60 ) )
    P.card( m, "roof_tiles", corners, ( 0, 0, -1 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Lights and reflection probes

WARM = "1.6,1.3,0.95,1"
COOL = "1.0,1.12,1.3,1"
NEUTRAL = "1.35,1.3,1.22,1"


def lights():
    out = []
    for k, ( e, n ) in enumerate( ( ( -890, 100 ), ( -890, 600 ), ( -890, 1150 ), ( -430, 1280 ) ) ):
        out.append( ( f"West Gallery Ground {k + 1}", ( e, n, 150 ), NEUTRAL, 380, k == 1 ) )
        out.append( ( f"West Gallery Upper {k + 1}", ( e, n, 330 ), NEUTRAL, 360, False ) )
    out.append( ( "Rotunda", ( ROTUNDA[0], ROTUNDA[1], 300 ), NEUTRAL, 560, True ) )
    out.append( ( "Rotunda Low", ( ROTUNDA[0], ROTUNDA[1], 120 ), WARM, 300, False ) )
    out.append( ( "Cafe", ( 740, 360, 140 ), WARM, 380, True ) )
    for k, ( e, n ) in enumerate( ( ( 1250, 350 ), ( 1800, 350 ) ) ):
        out.append( ( f"North Gallery Ground {k + 1}", ( e, n, 150 ), NEUTRAL, 420, k == 0 ) )
        out.append( ( f"North Gallery Upper {k + 1}", ( e, n, 330 ), NEUTRAL, 420, False ) )
    for k, ( e, n ) in enumerate( ( ( 800, -700 ), ( 800, -250 ), ( 1300, -500 ) ) ):
        out.append( ( f"East Hall {k + 1}", ( e, n, 320 ), NEUTRAL, 520, k == 0 ) )
    for k, e in enumerate( ( -800.0, -350.0, 100.0 ) ):
        out.append( ( f"South Gallery {k + 1}", ( e, -1575, 290 ), NEUTRAL, 560, k == 1 ) )
    for k, e in enumerate( ( -700.0, -100.0, 400.0 ) ):
        out.append( ( f"Portico {k + 1}", ( e, -2285, 230 ), WARM, 300, False ) )
    out.append( ( "Covered Walkway", ( 1520, -600, 180 ), WARM, 320, False ) )
    return out


# ( name, centre, the box they cover e0, e1, n0, n1, z0, z1 )
PROBES = [
    ( "West Gallery", ( -880, 650, 150 ), ( -1108, -668, -142, 1492, 0, 344 ) ),
    ( "West Gallery North", ( -430, 1280, 150 ), ( -668, -218, 1068, 1492, 0, 344 ) ),
    ( "Rotunda", ( ROTUNDA[0], ROTUNDA[1], 150 ), ( ROTUNDA[0] - 375, ROTUNDA[0] + 375, ROTUNDA[1] - 375, ROTUNDA[1] + 375, 0, 336 ) ),
    ( "Cafe", ( 740, 350, 80 ), ( 498, 1000, 0, 697, 0, 164 ) ),
    ( "North Gallery", ( 1530, 350, 150 ), ( 1018, 2042, 0, 697, 0, 344 ) ),
    ( "East Hall", ( 940, -500, 150 ), ( 498, 1382, -982, -18, 0, 344 ) ),
    ( "South Gallery", ( -275, -1575, 150 ), ( -1012, 462, -2132, -1018, 0, 314 ) ),
    ( "Courtyard", ( -80, 0, 150 ), ( -650, 480, -1000, 1050, -10, 500 ) ),
    ( "Portico", ( -275, -2285, 120 ), ( -1060, 510, -2420, -2150, -10, 272 ) ),
]


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( float( e ), float( n ), 0.0 ) for e in ( -500, -250, 0, 250, 500, 750 ) for n in ( 2800, 2950 ) ]
BLUE_SPAWNS = [ ( float( e ), float( n ), 0.0 ) for e in ( -500, -250, 0, 250, 500, 750 ) for n in ( -2850, -3000 ) ]
RED_BUY = ( -700, 950, 2650, 3080, -10, 260 )
BLUE_BUY = ( -700, 950, -3150, -2650, -10, 260 )

DM_SPAWNS = [
    ( -880, 1000, FLOOR1 ), ( -880, 300, 0 ), ( -400, 1300, 0 ), ( -430, 1300, FLOOR1 ), ( ROTUNDA[0], ROTUNDA[1] + 140, 0 ),
    ( 740, 400, 0 ), ( 750, 400, FLOOR1 ), ( 1500, 200, FLOOR1 ), ( 1150, 550, 0 ), ( 1850, 600, 0 ), ( 700, -900, 0 ),
    ( 1300, -700, FLOOR1 ), ( 1520, -600, 0 ), ( 2100, -200, 0 ), ( 2300, 400, 0 ), ( 1500, 1000, 0 ), ( 2300, 1000, 0 ),
    ( -300, 0, 0 ), ( 300, -700, 0 ), ( -300, -700, 0 ), ( -900, -600, 0 ), ( -1600, -1100, 0 ), ( -2400, -1700, 0 ),
    ( -2000, 650, 0 ), ( -1500, 1450, 0 ), ( -2400, -1000, 0 ), ( -600, -1400, 0 ), ( 200, -1900, 0 ), ( -1300, -2450, 0 ),
    ( 1000, -1250, 0 ), ( 2300, -2380, 0 ), ( -1500, 2600, 0 ), ( 1800, 2700, 0 ), ( -200, 1700, 0 ),
]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 560, 1080, -900, -150, 0 ),
               ( "bombsite_b", "Bomb Site B", -2000, -1490, -1610, -1110, 0 ) ]

# Retakes: the planter and the defenders are Red Team (Terrorist), the attackers Blue Team (CounterTerrorist).
RETAKES = {
    "bombsite_a": { "planter": [ ( 700, -700, 0 ), ( 1000, -300, 0 ) ],
                    "defender": [ ( 1300, -600, FLOOR1 ), ( 900, 300, 0 ), ( 1500, 400, 0 ), ( 750, 450, FLOOR1 ) ],
                    "attacker": [ ( -900, -600, 0 ), ( -1500, 650, 0 ), ( -800, 1200, 0 ), ( -1300, -2450, 0 ),
                                  ( 300, -2700, 0 ) ] },
    "bombsite_b": { "planter": [ ( -1743, -1150, 1.6 ), ( -1540, -1360, 1.6 ) ],
                    "defender": [ ( -2400, -1000, 0 ), ( -1600, -740, 0 ), ( -880, -1500, 0 ), ( -2300, -1960, 0 ) ],
                    "attacker": [ ( 900, -1250, 0 ), ( 1500, -600, 0 ), ( 1150, 550, 0 ), ( -880, 1000, 0 ),
                                  ( 2000, -1100, 0 ) ] },
}

DOMINATION = [ ( "A", ( ROTUNDA[0], ROTUNDA[1] - 120, 0 ) ), ( "B", ( 100, 220, 0 ) ), ( "C", ( -150, -1480, 0 ) ) ]
HOT_ZONES = [ ( "Rotunda", ( ROTUNDA[0], ROTUNDA[1] - 120, 0 ) ), ( "Courtyard", ( 100, 220, 0 ) ),
              ( "South Gallery", ( -150, -1480, 0 ) ), ( "Garden Circle", ( GARDEN[0], GARDEN[1] + 110, 1.6 ) ),
              ( "North Gallery", ( 1500, 400, 0 ) ), ( "East Terrace", ( 2000, -600, 0 ) ) ]
# Cash Grab: ( name, the cash, where it's taken ). The cash sits 8 over the floor and the extraction point 32.
CASH_POINTS = [ ( "Rotunda", ( ROTUNDA[0], ROTUNDA[1] - 120, 0 ), ( GARDEN[0], GARDEN[1] + 110, 1.6 ) ),
                ( "West Garden", ( -1650, 650, 0 ), ( 1500, 400, 0 ) ),
                ( "East Terrace", ( 2000, -600, 0 ), ( -880, 1200, 0 ) ) ]

UP = ( 170, 420 )


def callouts():
    return [
        ( "FORECOURT", -2560, 1000, 1510, 3080, -10, 400 ), ( "CAR PARK", 1000, 2520, 1600, 3080, -10, 400 ),
        ( "ROTUNDA", ROT_SQUARE[0], ROT_SQUARE[1], ROT_SQUARE[2], ROT_SQUARE[3], -10, 340 ),
        ( "WEST GALLERY", -1126, -200, -160, 1510, -10, UP[0] ), ( "WEST GALLERY UPPER", -1126, -200, -160, 1510, *UP ),
        ( "WEST GARDEN", -2560, -1126, -778, 1510, -10, 400 ), ( "B SITE", GARDEN_SQUARE[0], GARDEN_SQUARE[1],
                                                                 GARDEN_SQUARE[2], GARDEN_SQUARE[3], -10, 400 ),
        ( "WEST WALK", -1126, -650, -1000, -160, -10, 400 ), ( "SOUTH-WEST LAWNS", -2560, -1030, -2400, -1919, -10, 400 ),
        ( "COURTYARD", -650, 480, -1000, 1050, -10, 400 ), ( "STAGE", -650, -350, 780, 1050, -10, 400 ),
        ( "CAFE", 480, 1000, 0, 715, -10, UP[0] ), ( "TERRACE", 420, 1000, 0, 715, *UP ),
        ( "NORTH GALLERY", 1000, 2060, -18, 715, -10, UP[0] ), ( "NORTH GALLERY UPPER", 1000, 2060, -18, 715, *UP ),
        ( "A SITE", 480, 1220, -1000, 0, -10, 400 ), ( "MEZZANINE", 1220, 1400, -1000, 0, *UP ),
        ( "A HALL", 1220, 1400, -1000, 0, -10, UP[0] ),
        ( "PROMENADE", 480, 2520, 715, 1100, -10, 400 ), ( "EAST GARDEN", 1100, 2520, 1100, 1510, -10, 400 ),
        ( "EAST STRIP", 2060, 2520, -18, 715, -10, 400 ), ( "WALKWAY", 1400, 1640, -1190, -18, -10, 400 ),
        ( "EAST TERRACE", 1640, 2520, -1190, -18, -10, 400 ), ( "EAST LAWNS", 480, 2520, -2400, -1190, -10, 400 ),
        ( "SOUTH GALLERY", -1030, 480, -2150, -1000, -10, 400 ), ( "PORTICO", -1100, 560, -2440, -2150, -10, 400 ),
        ( "PLAZA", -2560, 2520, -3250, -2440, -10, 400 ), ( "PASSAGE", -200, -50, 1050, 1510, -10, 400 ),
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


# ---------------------------------------------------------------------------------------------------------------------
# The radar picture

MINIMAP_CENTRE = ( -20.0, -85.0 )
MINIMAP_SIZE = 6700.0
MINIMAP_PIXELS = 1024


def write_minimap( models ):
    """ Railhead's radar style: where you can walk (grey), low cover darker, walls and buildings left clear, a light line
    round the edges. North up. """
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "low", "tall" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    for pts in R.collision_shapes( models ):
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = R.hull_2d( pts[:, :2] )
        if len( outline ) < 3:
            continue
        centre = outline.mean( axis=0 )
        if not ( PLAY[0] - 50 <= centre[0] <= PLAY[1] + 50 and PLAY[2] - 50 <= centre[1] <= PLAY[3] + 50 ):
            continue
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if z1 > 250 and z0 > 100:
            continue
        if -24 <= z1 <= 18:
            draws["walk"].polygon( screen, fill=255 )
        elif z0 < 72 and z1 > 18:
            draws["low" if z1 < 100 else "tall"].polygon( screen, fill=255 )
    walk, low, tall = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "low", "tall" ) )
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[low] = ( 64, 68, 74, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    shown = ( walk | low ) & ~tall
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
# The scene (as Lowtide's)

CALLOUT_COLOUR = "0.51056,0.70698,0.49653,1"


def plan_box( e0, e1, n0, n1, z0, z1 ):
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
    """ A TeamSpawnPoint facing the museum's middle (the courtyard). """
    yaw = K.plan_yaw( ( -position[0] * 0.5, -position[1] ) )
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
    ( "cerroblanco_buildings", "Buildings", True, True ), ( "cerroblanco_grounds", "Grounds", True, True ),
    ( "cerroblanco_dressing", "Dressing", True, True ), ( "cerroblanco_glass", "Glass", True, False ),
    ( "cerroblanco_canopies", "Canopies", True, True ), ( "cerroblanco_backdrop", "Backdrop", False, True ),
]
NAV_SKIP = { "cerroblanco_glass", "cerroblanco_canopies" }
PROP_PACKAGES = { **R.PROP_PACKAGES, **P.FOLIAGE }


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    tags = "navskip" if model_name in NAV_SKIP else ""
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return K.game_object( ids, name, key, components=components, tags=tags )


def probe_object( name, centre, box ):
    e0, e1, n0, n1, z0, z1 = box
    at = K.to_world( centre )
    lo = K.to_world( ( e1, n0, z0 ) ) - at
    hi = K.to_world( ( e0, n1, z1 ) ) - at
    key = f"probe/{name}"
    return K.game_object( ids, f"Probe {name}", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", Bounds={ "Mins": K.vec( lo ), "Maxs": K.vec( hi ) },
                     DelayBetweenUpdates=0.1, Feathering=0.04, FrameInterval=5, MaxDistance=512, Projection="Box",
                     RenderDynamically=True, TintColor="1,1,1,1", UpdateStrategy="OnEnabled", ZFar=4096, ZNear=8 ) ] )


def look_object():
    """ Belltower's grade: ambient occlusion, a warm white balance, a light vignette, the outdoor exposure. """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.6, Radius=96,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=6100,
                     BlendFactor=0.4, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.2, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=SKY_EXPOSURE, MaximumExposure=3,
                     Mode="ACES", Rate=1 ),
    ] )


def write_scene( written, light_list, props ):
    foliage = []
    for index, prop in enumerate( props ):
        key = f"foliage/{index}"
        foliage.append( K.game_object( ids, prop.get( "name", "Tree" ), key, K.to_world( prop["position"] ),
                                       K.yaw_rotation( prop.get( "yaw", 0.0 ) ), scale=K.vec( prop.get( "scale", ( 1, 1, 1 ) ) ),
                                       components=[ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model=prop["path"],
                                                                 RenderType="On", Tint="1,1,1,1" ) ] ) )
    world = K.game_object( ids, "Cerro Blanco", "world", children=[
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

    play_centre, play_scale = plan_box( PLAY[0], PLAY[1], PLAY[2], PLAY[3], -300, 1000 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
    # Player clips over the perimeter wall, all the way round.
    e0, e1, n0, n1 = PLAY
    clips = [ ( "South", ( e0 - 18, e1 + 18, n0 - 18, n0, 96, 1600 ) ), ( "North", ( e0 - 18, e1 + 18, n1, n1 + 18, 96, 1600 ) ),
              ( "West", ( e0 - 18, e0, n0, n1, 96, 1600 ) ), ( "East", ( e1, e1 + 18, n0, n1, 96, 1600 ) ) ]
    clip_objects = []
    for name, box in clips:
        centre, scale = plan_box( *box )
        clip_objects.append( K.game_object( ids, f"Player Clip {name}", f"clip/{name}", centre, tags="playerclip", components=[
            box_collider( f"clip/{name}/box", scale, trigger=False ) ] ) )
    catch = K.game_object( ids, "Catch Floor", "catch", ( 0, 0, CATCH_FLOOR_Z ), components=[
        box_collider( "catch/box", ( 60000, 60000, 100 ), trigger=False ) ] )

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
                         Description="A modern art museum on a white hill: travertine galleries round a courtyard with a "
                                     "stage, a glass rotunda, a garden circle and a portico with red sculptures.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor="1.32,1.06,0.76,1", ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.42,0.48,0.58,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="1,1,1,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.75", StartDistance=3000,
                         EndDistance=60000, FalloffExponent=1.5, Height=9000, VerticalFalloffExponent=1.2 ),
        ] ),
        look_object(),
        world,
        K.game_object( ids, "Trees", "foliage", children=foliage ),
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in PROBES ] ),
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
    references = sorted( { reference for prop in props for reference in PROP_PACKAGES.get( prop["path"], () ) } )
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
                "AgentHeight": 64, "AgentRadius": 16, "AgentStepSize": 18, "AgentMaxSlope": 40, "ExcludedBodies": "zone,navskip",
                "IncludedBodies": "", "DeferGeneration": False, "CustomBounds": True,
                "Bounds": { "Mins": K.vec( K.to_world( ( PLAY[1], PLAY[2], -40 ) ) ),
                            "Maxs": K.vec( K.to_world( ( PLAY[0], PLAY[3], NAV_TOP ) ) ) },
            },
        },
        "ResourceVersion": 3,
        "Title": TITLE,
        "Description": None,
        "__references": references,
        "__version": 3,
    }
    SCENE_FILE.parent.mkdir( parents=True, exist_ok=True )
    K.write_text( SCENE_FILE, json.dumps( scene, indent=2 ), newline=None )
    print( f"wrote {SCENE_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------

# The exhibition's banners down the façades: ( k, wall point, outward, top, height )
BANNERS = [
    ( 0, ( -650, 250 ), ( 1, 0 ), 345, 150 ), ( 1, ( -650, 550 ), ( 1, 0 ), 345, 150 ), ( 2, ( -650, 720 ), ( 1, 0 ), 345, 150 ),
    ( 3, ( 480, -500 ), ( -1, 0 ), 340, 190 ), ( 0, ( 480, -200 ), ( -1, 0 ), 340, 190 ),
    ( 1, ( -800, -1000 ), ( 0, 1 ), 318, 150 ), ( 2, ( -320, -1000 ), ( 0, 1 ), 318, 150 ), ( 3, ( 380, -1000 ), ( 0, 1 ), 318, 160 ),
    ( 2, ( 1375, 715 ), ( 0, 1 ), 345, 150 ), ( 3, ( 1725, 715 ), ( 0, 1 ), 345, 150 ),
    ( 0, ( 1100, -1000 ), ( 0, -1 ), 345, 190 ), ( 1, ( -1126, 1150 ), ( -1, 0 ), 345, 150 ),
    ( 2, ( -800, -2150 ), ( 0, -1 ), 318, 70 ), ( 1, ( 250, -2150 ), ( 0, -1 ), 318, 70 ),
]


def banners( m ):
    for k, at, out, top, height in BANNERS:
        P.banner( m, k, at, top, out, width=64 if height > 100 else 120, height=height )


def build():
    """ Every model by name. """
    buildings, glass_, dressing, canopies, ground = Model(), Model(), Model(), Model(), Model()
    west_gallery( buildings, glass_, dressing )
    rotunda( buildings, glass_, dressing )
    east_block( buildings, glass_, dressing )
    south_gallery( buildings, glass_, dressing, canopies )
    grounds( ground, dressing, canopies )
    banners( buildings )
    models = {
        "cerroblanco_buildings": buildings,
        "cerroblanco_grounds": ground,
        "cerroblanco_dressing": dressing,
        "cerroblanco_glass": glass_,
        "cerroblanco_canopies": canopies,
        "cerroblanco_backdrop": backdrop(),
    }
    for model in models.values():
        configure( model )
    return models


def preview_colours():
    """ The preview renderer's colours for the cb_ paints: the drawn ones' mean colour, the flat ones' own. """
    PV.is_glass = lambda p: p in ( "rw_glass", "rw_glass_roof", P.GLAZE )
    PV.GLOWING.add( LAMP )
    PV._colours[P.GLAZE] = np.array( ( 0.42, 0.55, 0.62 ) )
    for paint, png in ( ( TRAV, "travertine" ), ( PANEL, "panel" ), ( PAVE, "paving" ), ( HONED, "honed" ), ( "cb_sign", "sign" ) ):
        PV._colours[paint] = np.asarray( Image.open( CM.OUT_DIR / f"{png}_color.png" ).convert( "RGB" ), float ).mean( axis=( 0, 1 ) ) / 255.0
    for k in range( 4 ):
        PV._colours[f"cb_banner_{k}"] = np.asarray( Image.open( CM.OUT_DIR / f"banner_{k}_color.png" ).convert( "RGB" ),
                                                    float ).mean( axis=( 0, 1 ) ) / 255.0
    for paint, ( colour, _, _ ) in P.CB_PAINTED.items():
        PV._colours[paint] = np.array( colour ) / 255.0


# ( name, eye, target, fov ): views to compare with the references.
VIEWS = [
    ( "courtyard", ( 200, -780, 70 ), ( -250, 400, 60 ), 80 ),
    ( "courtyard_high", ( 600, -1100, 700 ), ( -250, 300, 0 ), 70 ),
    ( "stage", ( 0, 300, 70 ), ( -500, 950, 80 ), 75 ),
    ( "portico", ( 800, -2900, 80 ), ( -400, -2300, 150 ), 75 ),
    ( "south_gallery", ( -1200, -2700, 160 ), ( 200, -2250, 120 ), 70 ),
    ( "rotunda", ( 900, 2300, 120 ), ( ROTUNDA[0], ROTUNDA[1], 200 ), 70 ),
    ( "garden_circle", ( -1100, -700, 260 ), ( GARDEN[0], GARDEN[1], 0 ), 75 ),
    ( "east_terrace", ( 2400, -1150, 80 ), ( 1300, -100, 120 ), 75 ),
    ( "terrace", ( 500, 650, 250 ), ( 900, 100, 220 ), 75 ),
    ( "aerial", ( 1800, -4800, 3200 ), ( -200, 0, 0 ), 60 ),
]


def render_views( models, out, names=None ):
    preview_colours()
    opaque, glass_ = PV.triangles( models ), PV.triangles( models, glass=True )
    for name, eye, target, fov in VIEWS:
        if names and name not in names:
            continue
        PV.perspective( opaque, glass_, eye, target, size=( 960, 540 ), fov=fov ).save( out / f"{name}.png" )
        print( f"wrote {out / name}.png" )


def write_map_art( models ):
    """ The menus' picture, a stand-in until there's an in-engine capture: the courtyard from over the South Gallery's
    roof, 1920 x 1080. """
    preview_colours()
    opaque, glass_ = PV.triangles( models ), PV.triangles( models, glass=True )
    image = PV.perspective( opaque, glass_, ( 500, -1250, 620 ), ( -250, 400, 0 ), size=( 960, 540 ), fov=70 )
    MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
    image.resize( ( 1920, 1080 ), Image.LANCZOS ).convert( "RGB" ).save( MAP_ART_FILE )
    print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", metavar="DIR", help="also write the reach grid's picture to this folder" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture" )
    parser.add_argument( "--views", metavar="DIR", help="render the comparison views (VIEWS) to this folder" )
    parser.add_argument( "--only", nargs="*", help="with --views, just these" )
    args = parser.parse_args()

    write_materials()
    models = build()
    written = set()
    for name, model in models.items():
        if K.is_empty( model ):
            print( f"{name}: empty, not written" )
            continue
        count = K.write_model( OUT_DIR, RESOURCE_DIR, name, model )
        written.add( name )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
    if R.MISSING:
        print( "from railhead_props, left out:" )
        for name, why in sorted( R.MISSING.items() ):
            print( f"  {name}: {why}" )
    if R.UNKNOWN_PAINTS:
        print( f"paints with no material: {', '.join( sorted( R.UNKNOWN_PAINTS ) )}" )
    light_list = lights()
    print( f"{len( light_list )} lights" )

    solid_names = [ name for name, _, collide, _ in SCENE_MODELS if collide and name in models ]
    solid = [ models[name] for name in solid_names ]
    print( "checking spots:" )
    problems = R.check_spots( R.collision_aabbs( solid ), all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    out = Path( args.preview ) if args.preview else None
    if out:
        out.mkdir( parents=True, exist_ok=True )
    walked = [ models[name] for name in solid_names if name not in NAV_SKIP ]
    bounds = ( PLAY[0], PLAY[1], PLAY[2], PLAY[3] + 8 )
    cut_off = R.check_reach( walked, all_spots(), out / "reach.png" if out else None, bounds=bounds )
    print( f"  {cut_off} spot(s) cut off from the spawns" )
    seen = R.check_retakes_sight( R.Blockers( solid ), RETAKES )
    print( f"  {seen} Retakes pair(s) in sight of each other" )

    props = [ prop for model in models.values() for prop in model.props ]
    if not args.no_scene:
        write_minimap( solid )
        write_scene( written, light_list, props )
    if args.art:
        write_map_art( list( models.values() ) )
    if args.views:
        views = Path( args.views )
        views.mkdir( parents=True, exist_ok=True )
        render_views( list( models.values() ), views, args.only )


if __name__ == "__main__":
    main()
