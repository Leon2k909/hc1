"""
Ares: a multiplayer map inside the Ares Facility, an atmosphere-processing plant on Mars, after the user's reference
picture (2026-10-14): the ATMOS PROCESSING column glowing orange through its glass in a dark steel hall ringed with
galleries, a leaning window wall looking out over the red plain to habitat domes, spired towers and two moons, posters
and banners of the facility's slogans, and black hard cases stencilled MARS / BIGGER / CLEANER / BRIGHTER.

    python Tools/ares_map.py [--preview <dir>] [--no-scene] [--scene-only] [--art]

Built by script like Boxyard, Lowtide and Railhead out of map_kit's boxes and polygons, painted with
Tools/ares_materials.py's drawn materials (run that first: `python Tools/ares_materials.py`). Writes:
- the models, to Assets/models/maps/ares/: the structure (ares_hall), the column (ares_reactor), the dressing
  (ares_dressing), the glass (ares_glass, drawn only) and the land outside (ares_backdrop, drawn only);
- the scene, Assets/scenes/maps/Ares/ares.scene, rewritten whole on every run (change the layout here, not in the
  editor);
- the radar picture, ui/minimaps/minimap_ares.png, and with --art a stand-in menu picture, ui/maps/ares.png.

The facility is indoors and pressurised, so the scene's gravity is the game's own: nothing here changes it.

Plan coordinates: e east, n north, z up, in inches (map_kit's). Mirrored across e = 0: Red Team spawns in the west wing
(SECTOR 03), Blue Team in the east wing (HABITAT B). Levels: the floors at z 0, the galleries and mezzanines at
z 208 (G), decks 16 thick.

- The Atmos Hall: e -1100..1100, n -720..720, 720 high. The column stands in its middle on a plinth, with a ring
  catwalk round it at G joined to the side galleries by two bridges. Galleries run round all four sides at G (the
  north one, the observation deck, along the window), over arcades on the floor. A stair in the void beside each side
  gallery joins the floor to G. The north side is a window wall leaning out 14 degrees (LEAN), mullions every 200.
  Under the side galleries are glass-fronted control rooms.
- The wings (SECTOR 03 west, HABITAT B east): e +-1132..+-2000, double height (448), with an L of mezzanine at G along
  their north and inner walls, a stair up the outer wall, and three doors into the hall: the floor's middle door, the
  SECTOR 03 / HABITAT B door onto the side gallery, and the north door onto the observation deck. The team spawns are
  in the wings' south-west (south-east) corner.
- The cargo concourse: n -1400..-752 across the whole width, 320 high, joined to the hall by two doors and to each
  wing by a wide opening. Its middle is kept clear.

The three lanes: north, the observation deck along the window and the wings' north mezzanines; middle, the hall floor
past the column (and the ring and bridges over it); south, the cargo concourse. Bomb site A is the observation deck's
east end, B the cargo bay at the concourse's east end.

Every run checks every spawn, objective and cash spot with railhead_map's check_spots, check_reach and
check_retakes_sight, with this map's bounds, and prints what's wrong.
"""
import argparse
import json
import math
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K
from map_kit import Model
import railhead_map as R
import boxyard_map as BY
import ares_materials as AM
import ares_sky as SKY

TITLE = "Ares"
OUT_DIR = K.ASSETS / "models/maps/ares"
RESOURCE_DIR = "models/maps/ares"
SCENE_FILE = K.ASSETS / "scenes/maps/Ares/ares.scene"
MINIMAP_PATH = "ui/minimaps/minimap_ares.png"
MINIMAP_FILE = K.asset_file( "ui/minimaps" ) / "minimap_ares.png"     # the folder is ui/Minimaps on disk
MAP_ART_PATH = "ui/maps/ares.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "4e8a1c37-92d5-4b6f-a0e3-7c15d9b2f846" )

METAL, STONE, GLASS, PLASTIC, SHEET = "metal", "default", "glass", "plastic", "metal.sheet"
SUN_PITCH, SUN_YAW = SKY.SUN_PITCH, SKY.SUN_YAW
SKY_MATERIAL = SKY.SKY_MATERIAL
# Keep the reactor readable against the Martian exterior when moving between the hall and its windows.
MIN_EXPOSURE, MAX_EXPOSURE = 1.7, 3.35
FOG_COLOUR = "0.59,0.31,0.18"
CATCH_FLOOR_Z = -4000

# Levels and the plan.
G = 208.0                      # the galleries' and mezzanines' tops
DT = 16.0                      # deck thickness
WALL = 32.0
HALL_E = 1100.0                # the hall's side walls' inner faces
HALL_N0, HALL_N1 = -720.0, 720.0
HALL_TOP = 720.0               # the hall's roof's underside
LEAN = 0.25                    # the window wall leans out this much north per inch up (14 degrees)
VOID_E, VOID_N0, VOID_N1 = 880.0, -540.0, 560.0     # the open middle, to the galleries' inner edges
DECK_N1 = HALL_N1 + LEAN * ( G - DT ) - 4.0         # the observation deck's front, just inside the glass
RING_R0, RING_R1 = 170.0, 290.0
BRIDGE_N = 80.0
STAIR_E, STAIR_N = ( 760.0, 880.0 ), ( -470.0, -158.0 )   # the hall's stairs (east; the west is the mirror)
WING_E = 2000.0                # the wings' outer walls' inner faces
WING_TOP = 448.0
MEZ_N = ( 520.0, 720.0 )       # the wings' north mezzanines
MEZ_E = 1352.0                 # the wings' inner mezzanines run from the hall wall (1132) to here
MEZ_INNER_N = ( -480.0, 520.0 )
WING_STAIR_E, WING_STAIR_N = ( 1870.0, 1990.0 ), ( 212.0, 520.0 )
CON_N0, CON_N1 = -1400.0, -752.0
CON_TOP = 320.0

DOOR_H = 176.0                 # floor doors
UPPER_DOOR_H = 144.0           # doors at G
MIDDLE_DOOR = ( -112.0, 112.0 )
SCREEN_E, SCREEN_N = ( 1260.0, 1276.0 ), ( -170.0, 170.0 )    # the blast screens inside the wings' middle doors (abs e)
SECTOR_DOOR = ( -420.0, -260.0 )
NORTH_DOOR = ( 576.0, 704.0 )
HALL_SOUTH_DOORS = ( 324.0, 516.0 )          # abs e, into the concourse
WING_SOUTH_OPENING = ( 1640.0, 1880.0 )      # abs e
WING_OPENING_H = 200.0

PLAY = ( -2000.0, 2000.0, -1400.0, 800.0 )   # e0, e1, n0, n1
NAV_TOP = 430.0                              # over the galleries, under the wings' roofs (448)


# ---------------------------------------------------------------------------------------------------------------------
# Paints

def configure( model ):
    """ Points the ar_ paints at Ares's materials (atlases mapped 1:1 by their own UVs, the rest at their tile). """
    for paint in list( model.polygons ):
        if paint.startswith( "ar_" ):
            model.material_overrides[paint] = f"{AM.RESOURCE_DIR}/{paint}.vmat"
            if paint == "ar_tower":
                model.tile_overrides[paint] = 1536.0
            else:
                model.tile_overrides[paint] = AM.TILES.get( paint, 64.0 )
            if paint not in AM.all_paints():
                R.UNKNOWN_PAINTS.add( paint )
        elif paint.startswith( "bx_" ):
            model.material_overrides[paint] = f"materials/boxyard/{paint}.vmat"
            model.tile_overrides[paint] = 1.0
        else:
            R.UNKNOWN_PAINTS.add( paint )
    model.anchored_paints = set()
    model.decal_paints = set()
    return model


card, rod, Frame = BY.card, BY.rod, BY.Frame
UP = np.array( ( 0.0, 0.0, 1.0 ) )


def keyed( *key ):
    text = ",".join( f"{float( k ):.1f}" if isinstance( k, ( int, float, np.integer, np.floating ) ) else str( k ) for k in key )
    return zlib.crc32( text.encode() )


def lathe_uv( m, base, profile, paint, sides=24, u_repeat=1.0, v_span=None, cap=None, turn=0.0, inward=False,
              arc=None ):
    """ A surface turned about the vertical through base: profile [ ( radius, height ) ] up it, with UVs u round it
    (u_repeat times) and v up the profile (0 at its foot, 1 at its head, or height / v_span). Shaded smooth. arc
    ( a0, a1 ) in degrees turns only part of the way round. inward faces it in (a lining seen from inside). """
    base = np.asarray( base, float )
    a0, a1 = ( 0.0, 360.0 ) if arc is None else arc
    steps = sides if arc is None else max( 2, int( round( sides * ( a1 - a0 ) / 360.0 ) ) )
    angles = [ math.radians( a0 + ( a1 - a0 ) * k / steps ) + turn for k in range( steps + 1 ) ]
    dirs = [ np.array( ( math.cos( a ), math.sin( a ), 0.0 ) ) for a in angles ]
    total = max( 1e-6, profile[-1][1] - profile[0][1] )
    for j in range( len( profile ) - 1 ):
        ( r0, h0 ), ( r1, h1 ) = profile[j], profile[j + 1]
        slope = np.array( ( h1 - h0, r0 - r1 ), float )
        if np.linalg.norm( slope ) < 1e-9:
            continue
        slope /= np.linalg.norm( slope )
        if inward:
            slope = -slope
        v0 = ( h0 - profile[0][1] ) / ( v_span or total )
        v1 = ( h1 - profile[0][1] ) / ( v_span or total )
        for k in range( steps ):
            d0, d1 = dirs[k], dirs[k + 1]
            pts = [ base + d0 * r0 + UP * h0, base + d1 * r0 + UP * h0, base + d1 * r1 + UP * h1, base + d0 * r1 + UP * h1 ]
            u0, u1 = k / steps * u_repeat * ( a1 - a0 ) / 360.0, ( k + 1 ) / steps * u_repeat * ( a1 - a0 ) / 360.0
            uv = [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]
            normals = [ d * slope[0] + UP * slope[1] for d in ( d0, d1, d1, d0 ) ]
            card( m, paint, pts, normals[0] + normals[1], uv=uv, normals=normals )
    if cap:
        r, h = profile[-1]
        if r > 1e-6:
            ring = [ base + d * r + UP * h for d in dirs[:-1] ] if arc is None else None
            if ring:
                card( m, cap, ring, UP if not inward else -UP )


def ring_surface( m, base, r0, r1, z, paint, sides=32, facing=1.0 ):
    """ A flat annulus at z between r0 and r1, facing up (facing 1) or down (-1). """
    base = np.asarray( base, float )
    for k in range( sides ):
        a, b = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        da, db = np.array( ( math.cos( a ), math.sin( a ), 0 ) ), np.array( ( math.cos( b ), math.sin( b ), 0 ) )
        pts = [ base + da * r0 + UP * z, base + db * r0 + UP * z, base + db * r1 + UP * z, base + da * r1 + UP * z ]
        card( m, paint, pts, UP * facing )


def cylinder_hull( m, centre, radius, z0, z1, surface, sides=16 ):
    c = np.asarray( centre, float )
    m.hull( [ ( c[0] + radius * math.cos( 2 * math.pi * k / sides ), c[1] + radius * math.sin( 2 * math.pi * k / sides ), z )
              for k in range( sides ) for z in ( z0, z1 ) ], surface )


def mirror_both( fn ):
    """ Runs fn( m, s ) for s = -1 (west) and +1 (east). """
    def run( m ):
        for s in ( -1, 1 ):
            fn( m, s )
    return run


# ---------------------------------------------------------------------------------------------------------------------
# Building parts

def deck( m, e0, e1, n0, n1, top=G, thick=DT, top_paint="ar_floor", edge="ar_steel", under="ar_steel", surface=METAL ):
    m.box( ( e0, n0, top - thick ), ( e1, n1, top ), { "+z": top_paint, "-z": under, "default": edge }, surface )


def railing( m, a, b, z, lamps=True, collide=True ):
    """ A railing from plan a ( e, n ) to b at floor z: posts about every 60, a black top rail, a brass mid rail and a
    hazard-striped kick plate, with a small warm lamp on every third post. Its collision is the top rail (36..44 up)
    and the kick plate, so you can shoot between the rails. """
    a = np.array( ( a[0], a[1], z ), float )
    b = np.array( ( b[0], b[1], z ), float )
    length = float( np.linalg.norm( b - a ) )
    if length < 4:
        return
    along = ( b - a ) / length
    side = np.cross( UP, along )
    m.beam( a + UP * 41.0, b + UP * 41.0, ( 2.4, 2.6 ), "ar_gunmetal" )
    m.beam( a + UP * 22.0, b + UP * 22.0, ( 1.4, 1.4 ), "ar_brass" )
    m.oriented_box( ( a + b ) / 2 + UP * 3.0, ( along, side, UP ), ( length, 0.6, 6.0 ), "ar_hazard" )
    posts = max( 2, int( round( length / 60.0 ) ) + 1 )
    for k in range( posts ):
        p = a + along * length * k / ( posts - 1 )
        m.oriented_box( p + UP * 20.5, ( along, side, UP ), ( 2.0, 2.0, 41.0 ), "ar_gunmetal" )
        if lamps and k % 3 == 1:
            for sgn in ( -1, 1 ):
                m.oriented_box( p + side * sgn * 1.4 + UP * 34.0, ( along, side, UP ), ( 1.2, 0.8, 2.4 ), "ar_led_warm" )
    if collide:
        m.oriented_box( ( a + b ) / 2 + UP * 40.0, ( along, side, UP ), ( length, 3.0, 8.0 ), { "default": None }, METAL )
        m.oriented_box( ( a + b ) / 2 + UP * 3.0, ( along, side, UP ), ( length, 1.0, 6.0 ), { "default": None }, METAL )


def slope_rail( m, a, b, collide=True ):
    """ A railing up a stair: a and b are plan ( e, n, z ) points on the stair's edge at its foot and its head. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    m.beam( a + UP * 38.0, b + UP * 38.0, ( 2.4, 2.6 ), "ar_gunmetal" )
    m.beam( a + UP * 20.0, b + UP * 20.0, ( 1.4, 1.4 ), "ar_brass" )
    length = float( np.linalg.norm( ( b - a )[:2] ) )
    posts = max( 2, int( round( length / 60.0 ) ) + 1 )
    for k in range( posts ):
        p = a + ( b - a ) * k / ( posts - 1 )
        m.box( p + np.array( ( -1, -1, 0 ) ), p + np.array( ( 1, 1, 38 ) ), "ar_gunmetal" )
    if collide:
        m.beam( a + UP * 40.0, b + UP * 40.0, ( 3.0, 10.0 ), { "default": None }, METAL )


def stair( m, axis, c0, c1, s0, s1, z0, z1, rails=( True, True ) ):
    """ A closed steel stair c0..c1 across, rising from s0 (at z0) to s1 (at z1) along axis 'e' or 'n': grating treads
    with hazard nosings over steel risers, solid sides. Its collision is the ramp under the nosings and the solid
    below it. rails ( low c side, high c side ). """
    rise = z1 - z0
    count = max( 1, int( round( rise / 7.4 ) ) )
    r = rise / count
    run = ( s1 - s0 ) / count
    sgn = 1.0 if s1 > s0 else -1.0

    def P( c, s, z ):
        return np.array( ( s, c, z ) if axis == "e" else ( c, s, z ), float )

    for k in range( count ):
        sa, sb = s0 + run * k, s0 + run * ( k + 1 )
        top = z0 + r * ( k + 1 )
        lo, hi = P( c0, min( sa, sb ), top - 1.5 ), P( c1, max( sa, sb ), top )
        m.box( lo, hi, { "+z": "ar_grating", "default": "ar_steel" } )
        # The nosing at the tread's front edge (its low s end), and the riser under it.
        front = sa
        nlo, nhi = P( c0, front - sgn * 0.0, top - 1.6 ), P( c1, front + sgn * 2.0, top + 0.05 )
        m.box( np.minimum( nlo, nhi ), np.maximum( nlo, nhi ), "ar_hazard" )
        rlo, rhi = P( c0, front, z0 + r * k ), P( c1, front + sgn * 0.8, top - 1.5 )
        m.box( np.minimum( rlo, rhi ), np.maximum( rlo, rhi ), "ar_steel" )
    # The solid sides: a trapezoid each, the stringer's top 3 over the nosings' line.
    for c, towards in ( ( c0, -1.0 ), ( c1, 1.0 ) ):
        pts = [ P( c, s0 - sgn * 0.0, z0 ), P( c, s1, z0 ), P( c, s1, z1 + 3.0 ), P( c, s0, z0 + r + 3.0 ) ]
        normal = np.array( ( 0, towards, 0 ) if axis == "e" else ( towards, 0, 0 ), float )
        card( m, "ar_steel", pts, normal )
        card( m, "ar_steel", [ p - normal * 0.01 for p in pts ], -normal )
    # The ramp: a wedge from the foot's nosing to the head.
    pts = [ P( c, s, z ) for c in ( c0, c1 ) for s, z in ( ( s0, z0 ), ( s1, z0 ), ( s1, z1 ), ( s0, z0 + r * 0.5 ) ) ]
    m.hull( pts, METAL )
    if rails[0]:
        slope_rail( m, P( c0 + 1.5, s0, z0 + r ), P( c0 + 1.5, s1, z1 ) )
    if rails[1]:
        slope_rail( m, P( c1 - 1.5, s0, z0 + r ), P( c1 - 1.5, s1, z1 ) )


def column( m, e, n, z0, z1, size=16.0, paint="ar_steel", band=True ):
    h = size / 2
    m.box( ( e - h, n - h, z0 ), ( e + h, n + h, z1 ), paint, METAL )
    if band:
        m.box( ( e - h - 0.5, n - h - 0.5, z0 ), ( e + h + 0.5, n + h + 0.5, z0 + 30 ), "ar_hazard" )
        m.box( ( e - h - 0.4, n - h - 0.4, z0 + 30 ), ( e + h + 0.4, n + h + 0.4, z0 + 32 ), "ar_brass" )


def wall( m, axis, run, across, z, openings=(), outward=None, outside="ar_wall", inside="ar_wall", reveal="ar_steel",
          surface=STONE ):
    w = K.Wall( axis, run, across, z, outward )
    for centre, width, z0, z1 in openings:
        w.add( centre, width, z0, z1, "door" )
    w.build( m, outside, inside, reveal, end=reveal, surface=surface )
    return w


def door_frame( m, axis, r0, r1, d0, d1, z0, z1, depth=3.0, width=8.0 ):
    """ A steel portal round an opening (r0..r1 along the wall, through d0..d1), standing proud of both faces: jambs,
    a header, and a hazard strip on each jamb's foot. """
    def B( ra, rb, da, db, za, zb, paint ):
        lo = ( ra, da, za ) if axis == "e" else ( da, ra, za )
        hi = ( rb, db, zb ) if axis == "e" else ( db, rb, zb )
        m.box( lo, hi, paint )

    for da, db in ( ( d0 - depth, d0 ), ( d1, d1 + depth ) ):
        B( r0 - width, r0, da, db, z0, z1 + width, "ar_steel" )
        B( r1, r1 + width, da, db, z0, z1 + width, "ar_steel" )
        B( r0, r1, da, db, z1, z1 + width, "ar_steel" )
        B( r0 - width, r0, da - 0.2 if da < d0 else da, db + 0.2 if db > d1 else db, z0, z0 + 24, "ar_hazard" )
        B( r1, r1 + width, da - 0.2 if da < d0 else da, db + 0.2 if db > d1 else db, z0, z0 + 24, "ar_hazard" )


def lit_sign( m, name, centre, facing, width=96.0, height=24.0, depth=3.0 ):
    """ A back-lit sign box: its face (LIT region) facing plan direction facing ( de, dn ), centred at centre. """
    c = np.asarray( centre, float )
    f = K.normalise( ( facing[0], facing[1], 0.0 ) )
    right = np.array( ( -f[1], f[0], 0.0 ) )
    m.oriented_box( c - f * depth / 2, ( -right, f, UP ), ( width + 2, depth, height + 2 ), "ar_bezel" )
    face = c + f * 0.05
    hw, hh = width / 2, height / 2
    pts = [ face - right * hw - UP * hh, face + right * hw - UP * hh, face + right * hw + UP * hh, face - right * hw + UP * hh ]
    uv = [ AM.region_uv( AM.LIT, AM.LIT_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    card( m, "ar_signs_lit", pts, f, uv=uv )


def sign_panel( m, region, centre, facing, width, height, paint="ar_signs", back="ar_steel", depth=1.0 ):
    """ A flat picture from the sign atlas on a thin plate, facing plan direction facing. """
    c = np.asarray( centre, float )
    f = K.normalise( ( facing[0], facing[1], 0.0 ) )
    right = np.array( ( -f[1], f[0], 0.0 ) )
    if back:
        m.oriented_box( c - f * depth / 2, ( -right, f, UP ), ( width + 1, depth, height + 1 ), back )
    face = c + f * 0.05
    hw, hh = width / 2, height / 2
    pts = [ face - right * hw - UP * hh, face + right * hw - UP * hh, face + right * hw + UP * hh, face - right * hw + UP * hh ]
    uv = [ AM.region_uv( AM.SIGN, AM.SIGN_ATLAS, region, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    card( m, paint, pts, f, uv=uv )


def banner( m, region, top_centre, facing, width, height ):
    """ A cloth banner hung from a bar on two cables, its picture on the front, black on the back. """
    c = np.asarray( top_centre, float )
    f = K.normalise( ( facing[0], facing[1], 0.0 ) )
    right = np.array( ( -f[1], f[0], 0.0 ) )
    hw = width / 2
    pts = [ c - right * hw - UP * height, c + right * hw - UP * height, c + right * hw, c - right * hw ]
    uv = [ AM.region_uv( AM.SIGN, AM.SIGN_ATLAS, region, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    card( m, "ar_signs", [ p + f * 0.3 for p in pts ], f, uv=uv )
    card( m, "ar_black", [ p - f * 0.3 for p in pts ], -f )
    m.beam( c - right * ( hw + 3 ), c + right * ( hw + 3 ), ( 1.6, 1.6 ), "ar_gunmetal" )
    m.beam( c - right * ( hw + 2 ) - UP * height, c + right * ( hw + 2 ) - UP * height, ( 1.2, 1.2 ), "ar_gunmetal" )


# ---------------------------------------------------------------------------------------------------------------------
# The hard cases and props

def case( m, e, n, z, heading, size=AM.CASE, front="front_text", side="side_logo", top="top_ribs", collide=True ):
    """ A black hard case (CASE's proportions scaled to size: length, height, depth) on its own UVs, with edge trim and
    latches. """
    L, H, D = size
    F = Frame( e, n, heading, z )
    hl, hd = L / 2, D / 2

    def uv( region, pts_st ):
        return [ AM.region_uv( AM.CRATE, AM.CRATE_ATLAS, region, s, t ) for s, t in pts_st ]

    # The long faces (+y front, -y back).
    F.quad( m, "ar_crate", [ ( hl, hd, 0 ), ( -hl, hd, 0 ), ( -hl, hd, H ), ( hl, hd, H ) ], ( 0, 1, 0 ),
            uv=uv( front, [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] ) )
    F.quad( m, "ar_crate", [ ( -hl, -hd, 0 ), ( hl, -hd, 0 ), ( hl, -hd, H ), ( -hl, -hd, H ) ], ( 0, -1, 0 ),
            uv=uv( "front_plain", [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] ) )
    F.quad( m, "ar_crate", [ ( hl, -hd, 0 ), ( hl, hd, 0 ), ( hl, hd, H ), ( hl, -hd, H ) ], ( 1, 0, 0 ),
            uv=uv( side, [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] ) )
    F.quad( m, "ar_crate", [ ( -hl, hd, 0 ), ( -hl, -hd, 0 ), ( -hl, -hd, H ), ( -hl, hd, H ) ], ( -1, 0, 0 ),
            uv=uv( "end_plain", [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] ) )
    F.quad( m, "ar_crate", [ ( -hl, -hd, H ), ( hl, -hd, H ), ( hl, hd, H ), ( -hl, hd, H ) ], ( 0, 0, 1 ),
            uv=uv( top, [ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] ) )
    # Edge trim on the vertical edges and round the lid's seam, latches on the front.
    t = 1.2
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            F.box( m, sx * hl - t, sx * hl + t, sy * hd - t, sy * hd + t, 0.0, H, "ar_gunmetal" )
    seam = H * 0.72
    F.box( m, -hl - 0.4, hl + 0.4, -hd - 0.4, hd + 0.4, seam - 0.6, seam + 0.6, "ar_gunmetal" )
    for x in ( -L * 0.3, L * 0.3 ):
        F.box( m, x - 1.6, x + 1.6, hd, hd + 1.0, seam - 3.0, seam + 2.0, "ar_brass" )
    if collide:
        F.box( m, -hl, hl, -hd, hd, 0.0, H, surface=PLASTIC )
    return z + H


def case_stack( m, e, n, heading, layers, seed=0, z=0.0, big=False ):
    """ Cases stacked: layers is a list of counts per layer (1 or 2 side by side), each a little turned. """
    L, H, D = AM.CASE if not big else ( 72.0, 45.0, 48.0 )
    for level, count in enumerate( layers ):
        for k in range( count ):
            jitter = ( keyed( "jit", e, n, level, k, seed ) % 9 ) - 4.0
            off = ( k - ( count - 1 ) / 2 ) * ( D + 1.0 )
            F = Frame( e, n, heading )
            p = F.p( 0, off, 0 )
            front = "front_text" if ( keyed( "front", e, n, level, k ) % 3 ) == 0 else "front_plain"
            case( m, p[0], p[1], z + level * H, heading + jitter, ( L, H, D ), front=front,
                  side="side_logo" if k == 0 else "side" )


def pump_unit( m, e, n, heading ):
    """ A pump housing beside the column: a steel box with a hazard band, its pipe rising and bending into the
    column. """
    F = Frame( e, n, heading )
    F.box( m, -36, 36, -28, 28, 0, 64, { "default": "ar_steel", "+z": "ar_grating" }, METAL )
    F.box( m, -36.3, 36.3, -28.3, 28.3, 52, 58, "ar_hazard" )
    F.box( m, -30, -10, -28.5, -28, 20, 44, "ar_screens" )
    for k, x in enumerate( ( -20.0, 20.0 ) ):
        a = F.p( x, 0, 64 )
        b = F.p( x, 0, 150 )
        rod( m, a, b, 6.0, "ar_copper", sides=10 )
        towards = K.normalise( np.array( ( -e, -n, 0.0 ) ) )
        c = b + towards * ( math.hypot( e, n ) - RING_R0 + 4 )
        rod( m, b, c, 6.0, "ar_copper", sides=10 )
        m.box( b - np.array( ( 7, 7, 7 ) ), b + np.array( ( 7, 7, 7 ) ), "ar_gunmetal" )


def console( m, e, n, heading, screen=0, z=0.0 ):
    """ A control desk: a steel body with a sloped screen and a lit keyboard strip, 60 wide. The operator stands on its
    -x side. """
    F = Frame( e, n, heading, z )
    F.box( m, -14, 14, -30, 30, 0, 34, { "default": "ar_steel", "+z": "ar_gunmetal" }, METAL )
    F.box( m, -16, -12, -30, 30, 34, 35.5, "ar_led_cyan" )
    # The screen, leaning back.
    a, b = F.p( 4, -26, 36 ), F.p( 4, 26, 36 )
    c, d = F.p( 14, 26, 64 ), F.p( 14, -26, 64 )
    name = f"screen{screen % 8}"
    uv = [ AM.region_uv( AM.SCREEN, AM.SCREEN_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
    card( m, "ar_screens", [ a, b, c, d ], F.v( -1, 0, 0.36 ), uv=uv )
    F.box( m, 6, 18, -28, 28, 30, 36, "ar_bezel" )
    back = F.v( 1.2, 0, -0.43 )
    card( m, "ar_bezel", [ a + back, b + back, c + back, d + back ], F.v( 1, 0, -0.36 ) )


def pipe_run( m, a, b, r, paint, bracket=120.0 ):
    """ A pipe from a to b (plan points) with a steel bracket and a flange every so often. Drawn only. """
    a, b = np.asarray( a, float ), np.asarray( b, float )
    rod( m, a, b, r, paint, sides=10 )
    length = float( np.linalg.norm( b - a ) )
    along = ( b - a ) / length
    for k in range( 1, int( length // bracket ) + 1 ):
        p = a + along * bracket * k
        half = np.abs( along ) * 1.2 + ( 1 - np.abs( along ) ) * ( r + 1.6 )
        m.box( p - half, p + half, "ar_gunmetal" )


def light_bar( m, e0, e1, n0, n1, z, paint="ar_led" ):
    """ A slim surface luminaire under a ceiling or deck: a steel housing and its lit lens facing down. """
    m.box( ( e0, n0, z ), ( e1, n1, z + 2.5 ), { "default": "ar_gunmetal", "-z": None } )
    m.box( ( e0 + 0.6, n0 + 0.6, z - 0.3 ), ( e1 - 0.6, n1 - 0.6, z ), { "default": paint } )


def wall_lamp( m, e, n, z, facing ):
    """ A small caged bulkhead lamp on a wall, facing plan direction facing. """
    f = np.array( ( facing[0], facing[1], 0.0 ) )
    right = np.array( ( f[1], -f[0], 0.0 ) )
    c = np.array( ( e, n, z ), float )
    m.oriented_box( c + f * 1.5, ( right, f, UP ), ( 10, 3, 6 ), "ar_gunmetal" )
    m.oriented_box( c + f * 3.6, ( right, f, UP ), ( 8, 1.2, 4 ), "ar_led_warm" )


# ---------------------------------------------------------------------------------------------------------------------
# The hall

def window_wall( m, glass ):
    """ The leaning window wall along the hall's north side: mullions every 200 (I-sections 16 wide), transoms at the
    deck, 420 and 640, a head beam under the roof, a sill at the floor, the glass in glass, and its collision. """
    def P( e, z ):
        return np.array( ( e, HALL_N1 + LEAN * z, z ) )

    normal = K.normalise( np.array( ( 0.0, 1.0, -LEAN ) ) )        # out of the glass, north and a little down
    upward = K.normalise( np.array( ( 0.0, LEAN, 1.0 ) ) )
    east = np.array( ( 1.0, 0.0, 0.0 ) )
    xs = np.arange( -HALL_E, HALL_E + 1, 200.0 )
    for x in xs:
        half = 8.0 if abs( abs( x ) - HALL_E ) > 1 else 4.0
        x0 = x if x > -HALL_E else x
        centre = ( P( x, 0 ) + P( x, HALL_TOP ) ) / 2 - normal * 13.0
        if abs( x ) >= HALL_E - 1:
            centre = centre + east * ( -half if x > 0 else half )
        length = float( np.linalg.norm( P( x, HALL_TOP ) - P( x, 0 ) ) )
        m.oriented_box( centre, ( east, normal, upward ), ( 2 * half, 26.0, length ), "ar_gunmetal" )
        # Light strips on the mullions' inner faces at each transom.
        for z in ( G + 40.0, 420.0 + 30.0, 640.0 + 24.0 ):
            p = P( x, z ) - normal * 26.2
            if abs( x ) < HALL_E - 1:
                m.oriented_box( p, ( east, normal, upward ), ( 3.0, 0.6, 22.0 ), "ar_led" )
    for z, depth, height in ( ( 0.0, 30.0, 10.0 ), ( G - DT - 4.0, 18.0, 26.0 ), ( 420.0, 22.0, 10.0 ), ( 640.0, 22.0, 10.0 ),
                              ( HALL_TOP - 8.0, 30.0, 16.0 ) ):
        centre = P( 0.0, z + height / 2 ) - normal * ( depth / 2 + 1.0 )
        m.oriented_box( centre, ( east, normal, upward ), ( 2 * HALL_E, depth, height ), "ar_gunmetal" )
    # The deck's front: a steel fascia under it along the glass.
    for k in range( len( xs ) - 1 ):
        e0, e1 = xs[k] + 8.0, xs[k + 1] - 8.0
        pts = [ P( e0, 0.5 ), P( e1, 0.5 ), P( e1, HALL_TOP - 8 ), P( e0, HALL_TOP - 8 ) ]
        card( glass, "ar_glass", pts, -normal )
    # The glass's collision: one slab in its plane, and the sill.
    centre = ( P( 0, 0 ) + P( 0, HALL_TOP ) ) / 2 + normal * 1.0
    length = float( np.linalg.norm( P( 0, HALL_TOP ) - P( 0, 0 ) ) )
    m.oriented_box( centre, ( east, normal, upward ), ( 2 * HALL_E + 64, 4.0, length ), { "default": None }, GLASS )
    m.box( ( -HALL_E, HALL_N1 - 6, 0 ), ( HALL_E, HALL_N1 + 4, 10 ), "ar_gunmetal", METAL )
    # The cheeks closing the leaning wall against the side walls, and the foundation below it outside.
    for s in ( -1, 1 ):
        e0, e1 = sorted( ( s * HALL_E, s * ( HALL_E + WALL ) ) )
        tri = [ ( HALL_N1, 0.0 ), ( HALL_N1 + LEAN * HALL_TOP + 8, HALL_TOP + 32 ), ( HALL_N1, HALL_TOP + 32 ) ]
        for e, towards in ( ( e0, -1.0 ), ( e1, 1.0 ) ):
            paint = "ar_concrete" if ( e == e0 ) == ( s > 0 ) else "ar_wall"
            card( m, paint, [ ( e, nn, z ) for nn, z in tri ], ( towards, 0, 0 ) )
        n_a, z_a = tri[0]
        n_b, z_b = tri[1]
        card( m, "ar_wall", [ ( e0, n_a, z_a ), ( e1, n_a, z_a ), ( e1, n_b, z_b ), ( e0, n_b, z_b ) ], ( 0, 1, -LEAN ) )
        m.hull( [ ( e, nn, z ) for e in ( e0, e1 ) for nn, z in tri ], STONE )


def hall_walls( m ):
    """ The hall's side walls (dark panels to the deck, light concrete above, steel pilasters), its south wall, and its
    roof with the trusses. """
    for s in ( -1, 1 ):
        e0, e1 = sorted( ( s * HALL_E, s * ( HALL_E + WALL ) ) )
        across = ( e0, e1 )
        out = "+e" if s > 0 else "-e"
        lower = [ ( sum( MIDDLE_DOOR ) / 2, MIDDLE_DOOR[1] - MIDDLE_DOOR[0], 0.0, DOOR_H ) ]
        upper = [ ( sum( SECTOR_DOOR ) / 2, SECTOR_DOOR[1] - SECTOR_DOOR[0], G, G + UPPER_DOOR_H ),
                  ( sum( NORTH_DOOR ) / 2, NORTH_DOOR[1] - NORTH_DOOR[0], G, G + UPPER_DOOR_H ) ]
        # The wall faces the hall on its inner side: outward is towards the wing.
        wall( m, "n", ( HALL_N0 - WALL, HALL_N1 ), across, ( 0.0, G ), lower, outward=out, outside="ar_wall", inside="ar_wall" )
        wall( m, "n", ( HALL_N0 - WALL, HALL_N1 ), across, ( G, HALL_TOP + 32 ), upper, outward=out,
              outside="ar_wall", inside="ar_concrete" )
        for d0, d1, z0, z1 in ( ( *MIDDLE_DOOR, 0.0, DOOR_H ), ( *SECTOR_DOOR, G, G + UPPER_DOOR_H ),
                                ( *NORTH_DOOR, G, G + UPPER_DOOR_H ) ):
            door_frame( m, "n", d0, d1, e0, e1, z0, z1 )
        # Pilasters on the hall side, from the deck to the roof, every 300 or so.
        face = s * HALL_E
        for nn in ( -600.0, -150.0, 300.0 ):
            lo = ( face - s * 10.0, nn - 12, G ) if s > 0 else ( face, nn - 12, G )
            hi = ( face, nn + 12, HALL_TOP ) if s > 0 else ( face + 10.0, nn + 12, HALL_TOP )
            m.box( lo, hi, "ar_steel" )
    # The south wall: the hall's stretch, 752 high, with its two doors into the concourse.
    doors = [ ( s * sum( HALL_SOUTH_DOORS ) / 2, HALL_SOUTH_DOORS[1] - HALL_SOUTH_DOORS[0], 0.0, DOOR_H ) for s in ( -1, 1 ) ]
    wall( m, "e", ( -HALL_E, HALL_E ), ( HALL_N0 - WALL, HALL_N0 ), ( 0.0, HALL_TOP + 32 ), doors, outward="-n",
          outside="ar_wall", inside="ar_wall" )
    for s in ( -1, 1 ):
        r0, r1 = sorted( ( s * HALL_SOUTH_DOORS[0], s * HALL_SOUTH_DOORS[1] ) )
        door_frame( m, "e", r0, r1, HALL_N0 - WALL, HALL_N0, 0.0, DOOR_H )
    # The roof: a slab, and trusses spanning north-south under it.
    roof_n1 = HALL_N1 + LEAN * HALL_TOP + 40
    m.box( ( -HALL_E - WALL, HALL_N0 - WALL, HALL_TOP ), ( HALL_E + WALL, roof_n1, HALL_TOP + 32 ),
           { "-z": "ar_concrete_dark", "+z": "ar_concrete_dark", "default": "ar_steel" }, STONE )
    for e in ( -900.0, -600.0, -300.0, 300.0, 600.0, 900.0 ):
        truss( m, e, HALL_N0, HALL_N1 + LEAN * 640 - 20 )
    # Purlins across the trusses.
    for nn in ( -500.0, -100.0, 300.0, 700.0 ):
        m.box( ( -HALL_E, nn - 5, HALL_TOP - 14 ), ( HALL_E, nn + 5, HALL_TOP ), "ar_steel" )


def truss( m, e, n0, n1, bottom=626.0, top=HALL_TOP ):
    """ A steel roof truss along n: chords and diagonals of I-ish boxes, and linear lights hung under it. """
    m.box( ( e - 7, n0, top - 12 ), ( e + 7, n1, top ), "ar_steel" )
    m.box( ( e - 7, n0, bottom ), ( e + 7, n1, bottom + 12 ), "ar_steel" )
    panels = int( ( n1 - n0 ) // 100 )
    step = ( n1 - n0 ) / panels
    for k in range( panels + 1 ):
        nn = n0 + step * k
        m.box( ( e - 4, nn - 3, bottom + 12 ), ( e + 4, nn + 3, top - 12 ), "ar_steel" )
        if k < panels:
            a = np.array( ( e, nn, bottom + 12 if k % 2 == 0 else top - 12 ) )
            b = np.array( ( e, nn + step, top - 12 if k % 2 == 0 else bottom + 12 ) )
            m.beam( a, b, ( 6, 5 ), "ar_steel" )
    for k in range( panels ):
        if k % 2 == 1:
            nn = n0 + step * ( k + 0.5 )
            light_bar( m, e - 5, e + 5, nn - 44, nn + 44, bottom - 3, "ar_led_warm" )


def galleries( m ):
    """ The galleries round the hall at G: the observation deck along the window, the south gallery, the side
    galleries; their railings, columns and the light bars under them. """
    deck( m, -HALL_E, HALL_E, VOID_N1, DECK_N1 )
    deck( m, -HALL_E, HALL_E, HALL_N0, VOID_N0 )
    for s in ( -1, 1 ):
        e0, e1 = sorted( ( s * VOID_E, s * HALL_E ) )
        deck( m, e0, e1, VOID_N0, VOID_N1 )
    # Railings along the void: the observation deck's edge, the south gallery's, and the side galleries' (with gaps
    # for the stairs' landings and the bridges).
    railing( m, ( -VOID_E, VOID_N1 ), ( VOID_E, VOID_N1 ), G )
    railing( m, ( VOID_E, VOID_N0 ), ( -VOID_E, VOID_N0 ), G )
    for s in ( -1, 1 ):
        e = s * VOID_E
        railing( m, ( e, VOID_N0 ), ( e, STAIR_N[0] ), G )
        railing( m, ( e, STAIR_N[0] ), ( e, STAIR_N[1] ), G, lamps=False )
        railing( m, ( e, BRIDGE_N ), ( e, VOID_N1 ), G )
    # Columns under the galleries' inner edges.
    for e in ( -600.0, -300.0, 300.0, 600.0 ):
        column( m, e, VOID_N1 + 10, 0.0, G - DT )
        column( m, e, VOID_N0 - 10, 0.0, G - DT )
    for s in ( -1, 1 ):
        for nn in ( -340.0, 570.0 ):
            column( m, s * ( VOID_E + 10 ), nn, 0.0, G - DT )
    # Light bars under the decks.
    for e in np.arange( -950.0, 951.0, 190.0 ):
        light_bar( m, e - 40, e + 40, 640 - 4, 640 + 4, G - DT - 2.5 )
        light_bar( m, e - 40, e + 40, -630 - 4, -630 + 4, G - DT - 2.5 )
    for s in ( -1, 1 ):
        for nn in ( -420.0, -200.0, 20.0, 240.0, 460.0 ):
            e = s * 990.0
            light_bar( m, e - 4, e + 4, nn - 40, nn + 40, G - DT - 2.5 )


def ring_and_bridges( m ):
    """ The ring catwalk round the column at G, and the two bridges to the side galleries. """
    sides = 32
    for k in range( sides ):
        a, b = 2 * math.pi * k / sides, 2 * math.pi * ( k + 1 ) / sides
        pts = [ ( RING_R0 * math.cos( a ), RING_R0 * math.sin( a ) ), ( RING_R1 * math.cos( a ), RING_R1 * math.sin( a ) ),
                ( RING_R1 * math.cos( b ), RING_R1 * math.sin( b ) ), ( RING_R0 * math.cos( b ), RING_R0 * math.sin( b ) ) ]
        card( m, "ar_grating", [ ( x, y, G ) for x, y in pts ], UP )
        card( m, "ar_steel", [ ( x, y, G - DT ) for x, y in pts ], -UP )
        ( xa, ya ), ( xb, yb ) = pts[1], pts[2]
        card( m, "ar_steel", [ ( xa, ya, G - DT ), ( xb, yb, G - DT ), ( xb, yb, G ), ( xa, ya, G ) ],
              ( math.cos( ( a + b ) / 2 ), math.sin( ( a + b ) / 2 ), 0 ) )
        m.hull( [ ( x, y, z ) for x, y in pts for z in ( G - DT, G ) ], METAL )
        # The ring's railing, but not where the bridges meet it (east and west).
        mid = ( a + b ) / 2
        if abs( math.sin( mid ) ) * RING_R1 > BRIDGE_N + 6:
            r = RING_R1 - 2.0
            railing( m, ( r * math.cos( a ), r * math.sin( a ) ), ( r * math.cos( b ), r * math.sin( b ) ), G,
                     lamps=( k % 2 == 0 ) )
        # Amber lamps round the ring's edge underneath.
        if k % 2 == 0:
            p = np.array( ( RING_R1 * math.cos( mid ), RING_R1 * math.sin( mid ), G - DT - 1 ) )
            m.box( p - np.array( ( 3, 3, 1.5 ) ), p + np.array( ( 3, 3, 0 ) ), "ar_led_amber" )
    for s in ( -1, 1 ):
        e0, e1 = sorted( ( s * ( RING_R1 - 12 ), s * VOID_E ) )
        m.box( ( e0, -BRIDGE_N, G - DT ), ( e1, BRIDGE_N, G ), { "+z": "ar_grating", "default": "ar_steel" }, METAL )
        # Girders under the bridge, and its railings.
        for nn in ( -BRIDGE_N + 8, BRIDGE_N - 8 ):
            m.box( ( e0, nn - 5, G - DT - 22 ), ( e1, nn + 5, G - DT ), "ar_steel" )
        ra = s * ( RING_R1 + 2 ) * math.cos( math.asin( min( 1.0, BRIDGE_N / RING_R1 ) ) )
        gap_end = math.radians( 360.0 / sides * 2 )            # the ring railing stops 2 segments either side
        for sign_n in ( -1, 1 ):
            nn = sign_n * ( BRIDGE_N - 1.5 )
            # The south railing stops where the stair landing joins the bridge.
            end = s * ( STAIR_E[0] if sign_n < 0 else VOID_E )
            railing( m, ( ra, nn ), ( end, nn ), G )
            corner = ( s * ( RING_R1 - 2 ) * math.cos( gap_end ), sign_n * ( RING_R1 - 2 ) * math.sin( gap_end ) )
            railing( m, corner, ( ra, nn ), G, lamps=False )
        for k in range( 1, 4 ):
            e = s * ( RING_R1 + ( VOID_E - RING_R1 ) * k / 4 )
            light_bar( m, e - 30, e + 30, -4, 4, G - DT - 2.5, "ar_led_warm" )


def hall_stairs( m ):
    for s in ( -1, 1 ):
        c0, c1 = sorted( ( s * STAIR_E[0], s * STAIR_E[1] ) )
        inner_low = s < 0     # the void side is the low c side in the east, the high side in the west
        stair( m, "n", c0, c1, STAIR_N[0], STAIR_N[1], 0.0, G, rails=( s > 0, s < 0 ) )
        # The landing at the head, joining the side gallery and the bridge.
        m.box( ( c0, STAIR_N[1], G - DT ), ( c1, -BRIDGE_N, G ), { "+z": "ar_grating", "default": "ar_steel" }, METAL )
        e_void = s * STAIR_E[0]
        railing( m, ( e_void, STAIR_N[1] ), ( e_void, -BRIDGE_N ), G )


def control_rooms( m, glass ):
    """ A glass-fronted control room under each side gallery (e +-880..1100, n 160..520), its door on its south end,
    consoles along its back wall. """
    n0, n1 = 160.0, 520.0
    for s in ( -1, 1 ):
        front = s * VOID_E
        back = s * HALL_E
        e0, e1 = sorted( ( front, back ) )
        # End walls (the south one with its door).
        wall( m, "e", ( e0, e1 ), ( n1, n1 + 8 ), ( 0.0, G - DT ), outward=None, inside="ar_wall" )
        door_e = s * ( VOID_E + 80 )
        wall( m, "e", ( e0, e1 ), ( n0 - 8, n0 ), ( 0.0, G - DT ), [ ( door_e, 64.0, 0.0, 96.0 ) ], outward=None, inside="ar_wall" )
        # The front: a low wall, glass over it, steel posts.
        fe0, fe1 = sorted( ( front, front - s * 6 ) )
        m.box( ( fe0, n0, 0 ), ( fe1, n1, 36 ), "ar_steel", METAL )
        m.box( ( fe0, n0, 150 ), ( fe1, n1, G - DT ), "ar_steel", METAL )
        for nn in np.linspace( n0, n1, 5 ):
            m.box( ( fe0, nn - 3, 36 ), ( fe1, nn + 3, 150 ), "ar_gunmetal" )
        ge = front - s * 3
        card( glass, "ar_room_glass", [ ( ge, n0, 36 ), ( ge, n1, 36 ), ( ge, n1, 150 ), ( ge, n0, 150 ) ], ( -s, 0, 0 ), both=True )
        m.box( ( min( ge - 1, ge + 1 ), n0, 36 ), ( max( ge - 1, ge + 1 ), n1, 150 ), { "default": None }, GLASS )
        # Consoles along the back wall, facing the glass, and screens on the wall over them.
        for k, nn in enumerate( ( 240.0, 340.0, 440.0 ) ):
            console( m, s * ( HALL_E - 26 ), nn, 0.0 if s > 0 else 180.0, screen=k + ( 0 if s < 0 else 3 ) )
            name = f"screen{( k + 5 ) % 8}"
            face = s * ( HALL_E - 0.5 )
            pts = [ ( face, nn + s * 30, 80 ), ( face, nn - s * 30, 80 ), ( face, nn - s * 30, 130 ), ( face, nn + s * 30, 130 ) ]
            uv = [ AM.region_uv( AM.SCREEN, AM.SCREEN_ATLAS, name, a, b ) for a, b in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]
            card( m, "ar_screens", pts, ( -s, 0, 0 ), uv=uv )
        le0, le1 = sorted( ( s * ( VOID_E + 40 ), s * ( HALL_E - 40 ) ) )
        light_bar( m, le0, le1, 330 - 4, 330 + 4, G - DT - 2.5, "ar_led" )


# ---------------------------------------------------------------------------------------------------------------------
# The column

def reactor( m, glass ):
    """ The ATMOS PROCESSING column, from the floor to the roof: a plinth, a lower and an upper glass chamber of glowing
    plasma round the ring catwalk, the lettered band, a third chamber, a flared lamp ring, and the stack into the roof,
    with copper pipes running up its glass. Its collision is a solid cylinder (RING_R0) and the plinth. """
    o = np.zeros( 3 )
    # The plinth, stepped up 16 (a stair's step), striped round its edge.
    lathe_uv( m, o, [ ( 232.0, 0.0 ), ( 232.0, 16.0 ) ], "ar_hazard", sides=40, u_repeat=60 )
    ring_surface( m, o, RING_R0, 232.0, 16.0, "ar_grating", sides=40 )
    cylinder_hull( m, o, 232.0, 0.0, 16.0, METAL, sides=20 )
    cylinder_hull( m, o, RING_R0, 0.0, HALL_TOP, METAL, sides=20 )

    def chamber( z0, z1, r_glass=140.0, r_core=118.0, posts=12 ):
        lathe_uv( m, o, [ ( r_core, z0 ), ( r_core, z1 ) ], "ar_plasma", sides=32, u_repeat=2.0, v_span=( z1 - z0 ) * 1.4 )
        lathe_uv( m, o, [ ( r_core * 0.55, z0 ), ( r_core * 0.55, z1 ) ], "ar_core", sides=16 )
        lathe_uv( glass, o, [ ( r_glass, z0 ), ( r_glass, z1 ) ], "ar_reactor_glass", sides=40 )
        for k in range( posts ):
            a = 2 * math.pi * ( k + 0.5 ) / posts
            p = np.array( ( ( r_glass + 4 ) * math.cos( a ), ( r_glass + 4 ) * math.sin( a ), 0.0 ) )
            m.beam( p + UP * z0, p + UP * z1, ( 7.0, 5.0 ), "ar_gunmetal", up=( math.cos( a ), math.sin( a ), 0 ) )

    def band( z0, z1, r, paint="ar_steel", lights=False, brass=False ):
        lathe_uv( m, o, [ ( r, z0 ), ( r, z1 ) ], paint, sides=40, u_repeat=6 )
        ring_surface( m, o, 0.0, r, z1, "ar_steel", sides=40 )
        ring_surface( m, o, 0.0, r, z0, "ar_steel", sides=40, facing=-1.0 )
        if brass:
            lathe_uv( m, o, [ ( r + 1.5, z0 + ( z1 - z0 ) * 0.4 ), ( r + 1.5, z0 + ( z1 - z0 ) * 0.6 ) ], "ar_brass", sides=40, u_repeat=6 )
        if lights:
            for k in range( 16 ):
                a = 2 * math.pi * k / 16
                p = np.array( ( ( r + 0.5 ) * math.cos( a ), ( r + 0.5 ) * math.sin( a ), ( z0 + z1 ) / 2 ) )
                d = np.array( ( math.cos( a ), math.sin( a ), 0 ) )
                side = np.array( ( -math.sin( a ), math.cos( a ), 0 ) )
                m.oriented_box( p + d * 0.6, ( d, side, UP ), ( 1.4, 6.0, 3.0 ), "ar_led_amber" )

    band( 16.0, 48.0, 190.0, "ar_steel", lights=True, brass=True )
    chamber( 48.0, 176.0 )
    band( 176.0, G - DT, RING_R0, "ar_steel", lights=True )
    band( G - DT, G + 14, RING_R0 - 4, "ar_gunmetal", brass=True )
    chamber( G + 14, 346.0 )
    band( 346.0, 362.0, 164.0, "ar_steel", brass=True )
    # The lettered band: dark panels round it, ATMOS PROCESSING on four of them.
    lathe_uv( m, o, [ ( 150.0, 362.0 ), ( 150.0, 470.0 ) ], "ar_wall", sides=40, u_repeat=4 )
    for heading in ( 225.0, 45.0, 135.0, 315.0 ):
        a0, a1 = heading - 32.0, heading + 32.0
        steps = 8
        for k in range( steps ):
            t0, t1 = k / steps, ( k + 1 ) / steps
            aa, ab = math.radians( a0 + ( a1 - a0 ) * t0 ), math.radians( a0 + ( a1 - a0 ) * t1 )
            r = 154.0
            pts = [ ( r * math.cos( aa ), r * math.sin( aa ), 372.0 ), ( r * math.cos( ab ), r * math.sin( ab ), 372.0 ),
                    ( r * math.cos( ab ), r * math.sin( ab ), 462.0 ), ( r * math.cos( aa ), r * math.sin( aa ), 462.0 ) ]
            uv = [ AM.region_uv( AM.SIGN, AM.SIGN_ATLAS, "band_atmos", t, v ) for t, v in ( ( t0, 0 ), ( t1, 0 ), ( t1, 1 ), ( t0, 1 ) ) ]
            mid = ( aa + ab ) / 2
            card( m, "ar_signs", pts, ( math.cos( mid ), math.sin( mid ), 0 ), uv=uv )
            # The panel's frame: a lip top and bottom.
        lathe_uv( m, o, [ ( 156.0, 368.0 ), ( 156.0, 372.0 ) ], "ar_gunmetal", sides=40, arc=( a0, a1 ) )
        lathe_uv( m, o, [ ( 156.0, 462.0 ), ( 156.0, 466.0 ) ], "ar_gunmetal", sides=40, arc=( a0, a1 ) )
        for a in ( a0, a1 ):
            p = np.array( ( 154 * math.cos( math.radians( a ) ), 154 * math.sin( math.radians( a ) ), 0 ) )
            m.box( p + np.array( ( -3, -3, 368 ) ), p + np.array( ( 3, 3, 466 ) ), "ar_gunmetal" )
        # Small lamps over the panel.
        for a in ( a0 + 8, heading, a1 - 8 ):
            p = np.array( ( 157 * math.cos( math.radians( a ) ), 157 * math.sin( math.radians( a ) ), 470.0 ) )
            m.box( p - np.array( ( 2.5, 2.5, 1.5 ) ), p + np.array( ( 2.5, 2.5, 1.5 ) ), "ar_led_warm" )
    band( 470.0, 486.0, 160.0, "ar_steel", brass=True )
    chamber( 486.0, 560.0, r_glass=128.0, r_core=104.0, posts=10 )
    # The flared lamp ring.
    lathe_uv( m, o, [ ( 150.0, 560.0 ), ( 224.0, 568.0 ), ( 224.0, 584.0 ), ( 150.0, 600.0 ) ], "ar_steel", sides=48, u_repeat=12 )
    ring_surface( m, o, 0.0, 150.0, 560.0, "ar_steel", sides=40, facing=-1.0 )
    for k in range( 24 ):
        a = 2 * math.pi * k / 24
        p = np.array( ( 208 * math.cos( a ), 208 * math.sin( a ), 566.0 ) )
        m.box( p - np.array( ( 4, 4, 1.2 ) ), p + np.array( ( 4, 4, 0.6 ) ), "ar_led_warm" )
    cylinder_hull( m, o, 224.0, 560.0, 600.0, METAL, sides=20 )
    # The stack into the roof, and four big pipes from the lamp ring to the roof.
    lathe_uv( m, o, [ ( 110.0, 604.0 ), ( 110.0, HALL_TOP ) ], "ar_wall", sides=24, u_repeat=3 )
    for k in range( 4 ):
        a = math.pi / 4 + k * math.pi / 2
        p = np.array( ( 200 * math.cos( a ), 200 * math.sin( a ), 0 ) )
        rod( m, p + UP * 588, p + UP * HALL_TOP, 14.0, "ar_pipe", sides=12 )
        m.box( p + np.array( ( -18, -18, 588 ) ), p + np.array( ( 18, 18, 600 ) ), "ar_gunmetal" )
    # Copper pipes up the glass, through the bands: in pairs between the lettered panels, so none crosses the lettering.
    for k in range( 8 ):
        a = math.radians( 90.0 * ( k // 2 ) + ( -6.0 if k % 2 == 0 else 6.0 ) )
        p = np.array( ( 160 * math.cos( a ), 160 * math.sin( a ), 0 ) )
        rod( m, p + UP * 16, p + UP * 560, 4.5, "ar_copper", sides=8 )
        for z in ( 100.0, 280.0, 420.0, 520.0 ):
            m.box( p + np.array( ( -6, -6, z ) ), p + np.array( ( 6, 6, z + 4 ) ), "ar_gunmetal" )
    # Pumps on the floor round it.
    for k, ( e, n ) in enumerate( ( ( 270.0, 270.0 ), ( -270.0, 270.0 ), ( -270.0, -270.0 ), ( 270.0, -270.0 ) ) ):
        pump_unit( m, e, n, math.degrees( math.atan2( n, e ) ) + 90.0 )
    sign_panel( m, "plate_core", ( 0.0, -233.0, 10.0 ), ( 0, -1 ), 40.0, 10.0, back=None )


# ---------------------------------------------------------------------------------------------------------------------
# The wings

def wings( m, glass ):
    for s in ( -1, 1 ):
        wing( m, glass, s )


def wing( m, glass, s ):
    """ One wing (s -1 west, SECTOR 03; +1 east, HABITAT B). """
    inner, outer = s * ( HALL_E + WALL ), s * WING_E
    e_lo, e_hi = sorted( ( inner, outer ) )
    floor_e = sorted( ( s * HALL_E, s * ( WING_E + WALL ) ) )
    # The floor slab (also under the hall: the hall's is separate).
    # The outer wall, with an airlock hatch drawn on it.
    oe0, oe1 = sorted( ( outer, outer + s * WALL ) )
    wall( m, "n", ( HALL_N0 - WALL, HALL_N1 + WALL ), ( oe0, oe1 ), ( 0.0, WING_TOP + 32 ), outward="+e" if s > 0 else "-e",
          outside="ar_concrete_dark", inside="ar_wall" )
    # The north wall, with windows at the mezzanine.
    windows = [ ( s * e, 120.0, 260.0, 390.0 ) for e in ( 1260.0, 1460.0, 1660.0, 1860.0 ) ]
    w = wall( m, "e", ( e_lo, e_hi ), ( HALL_N1, HALL_N1 + WALL ), ( 0.0, WING_TOP + 32 ), windows, outward="+n",
              outside="ar_concrete_dark", inside="ar_wall" )
    for centre, width, z0, z1 in windows:
        card( glass, "ar_glass", [ ( centre - width / 2, HALL_N1 + 16, z0 ), ( centre + width / 2, HALL_N1 + 16, z0 ),
                                   ( centre + width / 2, HALL_N1 + 16, z1 ), ( centre - width / 2, HALL_N1 + 16, z1 ) ], ( 0, -1, 0 ), both=True )
        m.box( ( centre - width / 2, HALL_N1 + 14, z0 ), ( centre + width / 2, HALL_N1 + 18, z1 ), { "default": None }, GLASS )
        for e in ( centre - width / 2, centre + width / 2 ):
            m.box( ( e - 3, HALL_N1 - 3, z0 - 3 ), ( e + 3, HALL_N1, z1 + 3 ), "ar_gunmetal" )
        m.box( ( centre - width / 2 - 3, HALL_N1 - 3, z0 - 3 ), ( centre + width / 2 + 3, HALL_N1, z0 ), "ar_gunmetal" )
        m.box( ( centre - width / 2 - 3, HALL_N1 - 3, z1 ), ( centre + width / 2 + 3, HALL_N1, z1 + 3 ), "ar_gunmetal" )
    # The south wall, with its wide opening into the concourse.
    o0, o1 = sorted( ( s * WING_SOUTH_OPENING[0], s * WING_SOUTH_OPENING[1] ) )
    wall( m, "e", ( e_lo, e_hi ), ( HALL_N0 - WALL, HALL_N0 ), ( 0.0, WING_TOP + 32 ),
          [ ( ( o0 + o1 ) / 2, o1 - o0, 0.0, WING_OPENING_H ) ], outward="-n", outside="ar_wall", inside="ar_wall" )
    door_frame( m, "e", o0, o1, HALL_N0 - WALL, HALL_N0, 0.0, WING_OPENING_H, width=10.0 )
    # The roof.
    m.box( ( min( e_lo, oe0 ), HALL_N0 - WALL, WING_TOP ), ( max( e_hi, oe1 ), HALL_N1 + WALL, WING_TOP + 32 ),
           { "-z": "ar_wall", "+z": "ar_concrete_dark", "default": "ar_steel" }, STONE )
    for e in ( 1350.0, 1600.0, 1850.0 ):
        m.box( ( s * e - 7, HALL_N0, WING_TOP - 24 ), ( s * e + 7, HALL_N1, WING_TOP ), "ar_steel" )
        for nn in ( -450.0, -50.0, 350.0 ):
            light_bar( m, s * e - 5, s * e + 5, nn - 60, nn + 60, WING_TOP - 27 )
    # The mezzanines: along the north wall, and along the hall wall.
    deck( m, e_lo, e_hi, MEZ_N[0], MEZ_N[1] )
    me0, me1 = sorted( ( inner, s * MEZ_E ) )
    deck( m, me0, me1, MEZ_INNER_N[0], MEZ_N[0] )
    # Their railings.
    stair_c0, stair_c1 = sorted( ( s * WING_STAIR_E[0], s * WING_STAIR_E[1] ) )
    near = s * WING_STAIR_E[0]
    railing( m, ( s * MEZ_E, MEZ_N[0] ), ( near, MEZ_N[0] ), G )
    railing( m, ( s * MEZ_E, MEZ_INNER_N[0] ), ( s * MEZ_E, MEZ_N[0] ), G )
    railing( m, ( inner, MEZ_INNER_N[0] ), ( s * MEZ_E, MEZ_INNER_N[0] ), G )
    # Columns under them.
    for e in ( 1500.0, 1720.0 ):
        column( m, s * e, MEZ_N[0] + 10, 0.0, G - DT )
    for nn in ( -360.0, 220.0 ):
        column( m, s * ( MEZ_E - 10 ), nn, 0.0, G - DT )
    for e in ( 1500.0, 1720.0 ):
        light_bar( m, s * e - 50, s * e + 50, 620 - 4, 620 + 4, G - DT - 2.5 )
    for nn in ( -300.0, 0.0, 300.0 ):
        light_bar( m, s * 1240 - 4, s * 1240 + 4, nn - 50, nn + 50, G - DT - 2.5 )
    # The stair up the outer wall to the north mezzanine.
    stair( m, "n", stair_c0, stair_c1, WING_STAIR_N[0], WING_STAIR_N[1], 0.0, G, rails=( s > 0, s < 0 ) )
    # The airlock hatch on the outer wall: a big sealed door, hazard frame, its sign.
    face = outer - s * 0.5
    hx0, hx1 = -150.0, 30.0
    m.box( ( min( face, face - s * 6 ), hx0 - 16, 0 ), ( max( face, face - s * 6 ), hx1 + 16, 196 ), "ar_hazard" )
    m.box( ( min( face - s * 6, face - s * 9 ), hx0, 0 ), ( max( face - s * 6, face - s * 9 ), hx1, 180 ), "ar_gunmetal" )
    m.box( ( min( face - s * 9, face - s * 10 ), ( hx0 + hx1 ) / 2 - 1, 0 ), ( max( face - s * 9, face - s * 10 ), ( hx0 + hx1 ) / 2 + 1, 180 ), "ar_dark" )
    for z in ( 40.0, 90.0, 140.0 ):
        m.box( ( min( face - s * 9, face - s * 12 ), hx0 + 20, z ), ( max( face - s * 9, face - s * 12 ), hx1 - 20, z + 6 ), "ar_steel" )
    lit_sign( m, "airlock03" if s < 0 else "airlock07", ( face - s * 1.0, ( hx0 + hx1 ) / 2, 220.0 ), ( -s, 0 ), 120.0, 30.0 )
    m.collision_box( ( min( face, face - s * 12 ), hx0 - 16, 0 ), ( max( face, face - s * 12 ), hx1 + 16, 196 ), METAL )
    # The blast screen inside the middle door: a steel partition up to the mezzanine, so nobody sees straight through
    # the door from the hall into the spawn; you turn round it.
    be0, be1 = sorted( ( s * SCREEN_E[0], s * SCREEN_E[1] ) )
    m.box( ( be0, SCREEN_N[0], 0 ), ( be1, SCREEN_N[1], G - DT ), { "default": "ar_wall", "+z": "ar_steel" }, STONE )
    m.box( ( be0 - 0.4, SCREEN_N[0] - 0.4, 0 ), ( be1 + 0.4, SCREEN_N[1] + 0.4, 24 ), "ar_hazard" )
    for nn in SCREEN_N:
        m.box( ( be0 - 3, nn - 4, 0 ), ( be1 + 3, nn + 4, G - DT ), "ar_steel" )
    sign_panel( m, "poster_mars", ( s * ( SCREEN_E[1] + 0.5 ), 0.0, 110.0 ), ( s, 0 ), 120.0, 96.0 )
    sign_panel( m, "logo", ( s * ( SCREEN_E[0] - 0.5 ), 0.0, 110.0 ), ( -s, 0 ), 70.0, 70.0 )
    # The zone marker on the outer wall over the stair, facing the spawn.
    sign_panel( m, "zone_03" if s < 0 else "zone_b", ( outer - s * 1.0, 330.0, 330.0 ), ( -s, 0 ), 220.0, 192.0 )
    # Pipes along the south wall, over the lockers and the opening.
    for k, ( z, r, paint ) in enumerate( ( ( 300.0, 7.0, "ar_pipe" ), ( 322.0, 5.0, "ar_copper" ), ( 342.0, 9.0, "ar_pipe" ) ) ):
        pipe_run( m, ( inner, HALL_N0 + 14 + 22 * k, z ), ( outer, HALL_N0 + 14 + 22 * k, z ), r, paint )
    # Lockers along the south wall's east (west) part.
    for k in range( 7 ):
        e = s * ( 1200.0 + k * 26.0 )
        lo = ( e - 12.5, HALL_N0, 0 )
        hi = ( e + 12.5, HALL_N0 + 22, 84 )
        m.box( lo, hi, { "default": "ar_steel", "+n": "ar_gunmetal" } )
        m.box( ( e - 2, HALL_N0 + 22, 50 ), ( e + 2, HALL_N0 + 23, 56 ), "ar_brass" )
    m.box( ( min( s * 1187, s * 1385 ), HALL_N0, 0 ), ( max( s * 1187, s * 1385 ), HALL_N0 + 22, 84 ), { "default": None }, METAL )
    # Signs: the wing's name over its doors on the hall side, and inside.
    name = "sector03" if s < 0 else "habitatb"
    sign_z = G + UPPER_DOOR_H + 26
    lit_sign( m, name, ( s * ( HALL_E - 1.0 ), sum( SECTOR_DOOR ) / 2, sign_z ), ( -s, 0 ), 128.0, 32.0 )
    lit_sign( m, name, ( s * ( HALL_E - 1.0 ), sum( NORTH_DOOR ) / 2, sign_z ), ( -s, 0 ), 112.0, 28.0 )
    lit_sign( m, "exit", ( s * ( HALL_E + WALL + 1.0 ), sum( SECTOR_DOOR ) / 2, sign_z ), ( s, 0 ), 112.0, 28.0 )
    lit_sign( m, "observation", ( s * ( HALL_E + WALL + 1.0 ), sum( NORTH_DOOR ) / 2, sign_z ), ( s, 0 ), 112.0, 28.0 )
    lit_sign( m, "cargo", ( ( o0 + o1 ) / 2, HALL_N0 + 1.0, WING_OPENING_H + 30 ), ( 0, 1 ), 128.0, 32.0 )
    lit_sign( m, name, ( ( o0 + o1 ) / 2, HALL_N0 - WALL - 1.0, WING_OPENING_H + 30 ), ( 0, -1 ), 128.0, 32.0 )


# ---------------------------------------------------------------------------------------------------------------------
# The cargo concourse

def concourse( m, glass ):
    n_mid = ( CON_N0 + CON_N1 ) / 2
    # The south wall with the big airlock, the end walls, the roof.
    wall( m, "e", ( -WING_E - WALL, WING_E + WALL ), ( CON_N0 - WALL, CON_N0 ), ( 0.0, CON_TOP + 32 ), outward="-n",
          outside="ar_concrete_dark", inside="ar_wall" )
    for s in ( -1, 1 ):
        e0, e1 = sorted( ( s * WING_E, s * ( WING_E + WALL ) ) )
        wall( m, "n", ( CON_N0, HALL_N0 - WALL ), ( e0, e1 ), ( 0.0, CON_TOP + 32 ), outward="+e" if s > 0 else "-e",
              outside="ar_concrete_dark", inside="ar_wall" )
    # The wall between the concourse and the hall and wings, from the concourse side above the doors, is the hall's and
    # the wings' south walls; the stretch of it over the concourse roof is theirs too.
    m.box( ( -WING_E - WALL, CON_N0 - WALL, CON_TOP ), ( WING_E + WALL, HALL_N0 - WALL, CON_TOP + 32 ),
           { "-z": "ar_wall", "+z": "ar_concrete_dark", "default": "ar_steel" }, STONE )
    # Roof beams across it, with lights.
    for e in np.arange( -1800.0, 1801.0, 300.0 ):
        m.box( ( e - 6, CON_N0, CON_TOP - 20 ), ( e + 6, HALL_N0 - WALL, CON_TOP ), "ar_steel" )
    for e in np.arange( -1650.0, 1651.0, 300.0 ):
        for nn in ( -1220.0, -930.0 ):
            light_bar( m, e - 50, e + 50, nn - 5, nn + 5, CON_TOP - 3 )
    # The floor's yellow lane lines.
    for nn in ( CON_N0 + 60, CON_N1 - 60 ):
        BY.line_strip( m, "bx_line_yellow", ( -WING_E + 40, nn ), ( WING_E - 40, nn ), 4.0, 0.05 )
    # Pillars.
    for e in ( -1300.0, -650.0, 650.0, 1300.0 ):
        column( m, e, n_mid, 0.0, CON_TOP - 20, size=28.0 )
    # Pipes along the south and north walls.
    for k, ( z, r, paint ) in enumerate( ( ( 228.0, 8.0, "ar_pipe" ), ( 252.0, 6.0, "ar_copper" ), ( 274.0, 10.0, "ar_pipe" ) ) ):
        pipe_run( m, ( -WING_E, CON_N0 + 16 + 24 * k, z ), ( -190.0, CON_N0 + 16 + 24 * k, z ), r, paint )
        pipe_run( m, ( 190.0, CON_N0 + 16 + 24 * k, z ), ( WING_E, CON_N0 + 16 + 24 * k, z ), r, paint )
    for k, ( z, r, paint ) in enumerate( ( ( 270.0, 7.0, "ar_pipe" ), ( 292.0, 5.0, "ar_copper" ) ) ):
        for s in ( -1, 1 ):
            pipe_run( m, ( s * WING_E, HALL_N0 - WALL - 14 - 20 * k, z ), ( s * 1150.0, HALL_N0 - WALL - 14 - 20 * k, z ), r, paint )
    # The airlock in the south wall's middle.
    face = CON_N0 + 0.5
    m.box( ( -180, face - 0.5, 0 ), ( 180, face + 6, 220 ), "ar_hazard" )
    m.box( ( -160, face + 6, 0 ), ( 160, face + 9, 200 ), "ar_gunmetal" )
    m.box( ( -1, face + 9, 0 ), ( 1, face + 10, 200 ), "ar_dark" )
    for z in ( 50.0, 100.0, 150.0 ):
        m.box( ( -140, face + 9, z ), ( 140, face + 12, z + 6 ), "ar_steel" )
    m.collision_box( ( -180, face - 0.5, 0 ), ( 180, face + 12, 220 ), METAL )
    lit_sign( m, "airlock07", ( 0.0, face + 1.0, 250.0 ), ( 0, 1 ), 128.0, 32.0 )
    # Signs over the doors into the hall, from the concourse side.
    for s in ( -1, 1 ):
        c = s * sum( HALL_SOUTH_DOORS ) / 2
        lit_sign( m, "exit", ( c, HALL_N0 - WALL - 1.0, DOOR_H + 30 ), ( 0, -1 ), 120.0, 30.0 )
    sign_panel( m, "plate_cargo", ( 0.0, HALL_N0 - WALL - 0.5, 260.0 ), ( 0, -1 ), 240.0, 60.0 )
    sign_panel( m, "poster_mars", ( -900.0, CON_N0 + 1.0, 150.0 ), ( 0, 1 ), 120.0, 96.0 )
    sign_panel( m, "poster_mars", ( 900.0, CON_N0 + 1.0, 150.0 ), ( 0, 1 ), 120.0, 96.0 )


# ---------------------------------------------------------------------------------------------------------------------
# Dressing: cases, consoles, signs, banners, lamps

def dressing( m ):
    # Cases on the hall floor.
    for s in ( -1, 1 ):
        case_stack( m, s * 600, 260, 90 + s * 6, [ 2, 1 ], seed=1 )
        case_stack( m, s * 560, -300, s * 4, [ 1, 1 ], seed=2 )
        case_stack( m, s * 420, 440, 0, [ 2 ], seed=3 )
        case_stack( m, s * 760, -40, 90, [ 1 ], seed=4, big=True )
        case_stack( m, s * 440, -480, s * 10, [ 1 ], seed=5 )
        # The arcade along the window.
        case_stack( m, s * 820, 660, 0, [ 2, 1 ], seed=6 )
        case_stack( m, s * 160, 660, s * 3, [ 1 ], seed=7 )
        # The south arcade.
        case_stack( m, s * 760, -640, 0, [ 2, 2, 1 ], seed=8 )
        case_stack( m, s * 180, -650, 0, [ 1 ], seed=9 )
        # On the observation deck, against the glass (the picture's), and on the galleries.
        case_stack( m, s * 760, 728, 0, [ 2, 1 ], seed=10, z=G )
        case_stack( m, s * 300, 735, 0, [ 1 ], seed=11, z=G )
        case_stack( m, s * 1000, 330, 90, [ 2 ], seed=12, z=G )
        case_stack( m, s * 1000, -620, 0, [ 1, 1 ], seed=13, z=G )
        case_stack( m, s * 620, -650, 0, [ 2, 1 ], seed=14, z=G )
        case_stack( m, s * 90, -650, 0, [ 1 ], seed=15, z=G )
        # Consoles near the column.
        console( m, s * 230, -440, 90.0 if s > 0 else 90.0, screen=1 + ( s > 0 ) )
        # The wings.
        case_stack( m, s * 1500, -300, 90, [ 2, 1 ], seed=20 )
        case_stack( m, s * 1460, 260, 0, [ 2, 2 ], seed=21, big=True )
        case_stack( m, s * 1760, 100, s * 8, [ 1 ], seed=22 )
        case_stack( m, s * 1520, -680, 0, [ 1, 1 ], seed=23 )
        case_stack( m, s * 1600, 660, 0, [ 2, 1 ], seed=24, z=G )
        case_stack( m, s * 1250, -300, 90, [ 1 ], seed=25, z=G )
        # The concourse: cases and the cargo pods.
        case_stack( m, s * 900, -830, 0, [ 2, 2, 1 ], seed=30, big=True )
        case_stack( m, s * 950, -1310, 0, [ 2, 1 ], seed=31, big=True )
        case_stack( m, s * 300, -850, 0, [ 1 ], seed=32 )
        case_stack( m, s * 320, -1330, 0, [ 2 ], seed=33 )
        case_stack( m, s * 1420, -1230, 90, [ 2, 2 ], seed=34, big=True )
        case_stack( m, s * 1600, -960, 0, [ 2, 1 ], seed=35 )
        case_stack( m, s * 1250, -900, s * 12, [ 1 ], seed=36 )
        case_stack( m, s * 1800, -1320, 0, [ 1, 1 ], seed=37 )
    # Keep the centre of the concourse clear.
    # The yellow lines on the hall floor: round the column, and along the arcades.
    BY.rectangle_lines( m, "bx_line_yellow", -VOID_E + 30, VOID_E - 30, VOID_N0 + 30, VOID_N1 - 30, 4.0, 0.05 )
    for k in range( 24 ):
        a, b = 2 * math.pi * k / 24, 2 * math.pi * ( k + 1 ) / 24
        BY.line_strip( m, "bx_line_yellow", ( 360 * math.cos( a ), 360 * math.sin( a ) ), ( 360 * math.cos( b ), 360 * math.sin( b ) ), 4.0, 0.05 )
    # Posters, banners and signs (the picture's).
    sign_panel( m, "poster_ares", ( -HALL_E + 1.0, sum( SECTOR_DOOR ) / 2, G + UPPER_DOOR_H + 200 ), ( 1, 0 ), 220.0, 275.0 )
    sign_panel( m, "poster_ares", ( HALL_E - 1.0, 420.0, G + 250 ), ( -1, 0 ), 180.0, 225.0 )
    sign_panel( m, "poster_redplanet", ( HALL_E - 1.0, -330.0, 120.0 ), ( -1, 0 ), 150.0, 56.0 )
    sign_panel( m, "poster_redplanet", ( -HALL_E + 1.0, 330.0, 130.0 ), ( 1, 0 ), 150.0, 56.0 )
    sign_panel( m, "poster_mars", ( 0.0, HALL_N0 + 1.0, G + 200 ), ( 0, 1 ), 200.0, 160.0 )
    banner( m, "banner_humanity", ( -150.0, 620.0, 690.0 ), ( 0, -1 ), 80.0, 240.0 )
    banner( m, "banner_habitat", ( 900.0, 640.0, 690.0 ), ( 0, -1 ), 90.0, 270.0 )
    banner( m, "banner_humanity", ( -HALL_E + 60.0, 120.0, 690.0 ), ( 1, 0 ), 90.0, 270.0 )
    sign_panel( m, "stripe_warning", ( 0.0, -RING_R1 - 4.0, G - DT - 6 ), ( 0, -1 ), 140.0, 19.0, back=None )
    lit_sign( m, "observation", ( 0.0, 600.0, 420.0 ), ( 0, -1 ), 192.0, 48.0 )
    for e in ( -80.0, 80.0 ):
        rod( m, ( e, 598.0, 444.0 ), ( e, 598.0, HALL_TOP ), 0.6, "ar_gunmetal", sides=4 )
    # Lamps on the hall's side walls at the galleries, and at the arcades.
    for s in ( -1, 1 ):
        for nn in ( -540.0, -60.0, 200.0, 470.0 ):
            wall_lamp( m, s * HALL_E, nn, G + 110, ( -s, 0 ) )
        for nn in ( -540.0, -300.0, 620.0 ):
            wall_lamp( m, s * HALL_E, nn, 120.0, ( -s, 0 ) )
    for e in ( -800.0, -400.0, 400.0, 800.0 ):
        wall_lamp( m, e, HALL_N0, G + 110, ( 0, 1 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Floors

def floors( m ):
    """ The floor slabs: one under the hall and the wings, one under the concourse, and the foundation round the
    building down to the ground outside. """
    m.box( ( -WING_E - WALL, HALL_N0 - WALL, -24 ), ( WING_E + WALL, HALL_N1, 0 ), { "+z": "ar_floor", "default": "ar_concrete_dark" }, METAL )
    m.box( ( -WING_E - WALL, CON_N0 - WALL, -24 ), ( WING_E + WALL, HALL_N0 - WALL, 0 ), { "+z": "ar_floor", "default": "ar_concrete_dark" }, METAL )
    # The foundation: the building's plinth outside, down to the plateau, and the cliff face under the window.
    m.box( ( -WING_E - WALL - 40, HALL_N1, -900 ), ( WING_E + WALL + 40, HALL_N1 + WALL + 20, 0 ),
           { "default": "ar_concrete_dark", "+z": "ar_concrete_dark" } )
    for e in np.arange( -1900.0, 1901.0, 380.0 ):
        m.box( ( e - 10, HALL_N1 + WALL + 20, -60 ), ( e + 10, HALL_N1 + WALL + 22, -52 ), "ar_far_light" )


# ---------------------------------------------------------------------------------------------------------------------
# The land outside (drawn only)

def value_noise( rng, size=256 ):
    return rng.standard_normal( ( size, size ) ).astype( np.float32 )


def sample( grid, e, n, scale ):
    from scipy import ndimage
    size = grid.shape[0]
    return ndimage.map_coordinates( grid, [ ( n / scale ) % size, ( e / scale ) % size ], order=3, mode="grid-wrap" )


WORLD_EDGE = 60000.0     # the land's edge, out from the middle
MESAS = ( ( -6500.0, 9000.0, 2200.0, 900.0 ), ( 9500.0, 8000.0, 1800.0, 700.0 ), ( 3000.0, 15500.0, 3000.0, 1300.0 ),
          ( -12500.0, 14000.0, 3500.0, 1500.0 ), ( 14500.0, 16500.0, 3000.0, 1100.0 ), ( -3000.0, 22000.0, 4000.0, 1700.0 ) )


def terrain_height( e, n ):
    """ The land round the facility: the plateau it stands on (just under its floor), a cliff under the window down to
    the plain, broad mesas and a crater on the plain, and a low range of mountains on the far horizon. Smooth, large
    shapes: the picture's land is a wide plain under far ridges, not jagged peaks. """
    rng = np.random.default_rng( 77 )
    g1, g2, g3, g4 = ( value_noise( rng ) for _ in range( 4 ) )
    e, n = np.asarray( e, float ), np.asarray( n, float )
    fbm = ( 0.55 * sample( g1, e, n, 1400.0 ) + 0.3 * sample( g2, e, n, 500.0 ) + 0.15 * sample( g3, e, n, 180.0 ) )
    plateau = -60.0 + 12.0 * fbm

    def plain_at( e_, n_ ):
        return -1150.0 - 250.0 * K_smooth( 2000.0, 16000.0, n_ )

    plain = plain_at( e, n ) + 90.0 * fbm + 30.0 * sample( g4, e, n, 90.0 )
    # The plateau's edge: a cliff north of the window, slopes elsewhere.
    dx = np.maximum( np.abs( e ) - 3200.0, 0.0 )
    ds = np.maximum( -2600.0 - n, 0.0 )
    dn = np.maximum( n - 900.0, 0.0 )
    t = np.maximum( K_smooth( 0.0, 900.0, dn + 160.0 * sample( g2, e, n, 600.0 ) ),
                    K_smooth( 0.0, 5000.0, np.hypot( dx, ds ) ) * 0.8 )
    h = plateau * ( 1 - t ) + plain * t
    # Mesas: flat tops over scarps, the scarp a third of the radius wide, a little talus at the foot.
    for me, mn, r, top in MESAS:
        d = np.hypot( e - me, n - mn ) + 0.12 * r * sample( g2, e, n, r * 0.35 )
        rise = 1.0 - K_smooth( r * 0.66, r, d )
        talus = np.exp( -( ( d - r ) / ( 0.12 * r ) ) ** 2 ) * 0.08
        h = np.maximum( h, plain + top * np.clip( rise + talus, 0, 1 ) + 20.0 * fbm * rise )
    # A crater.
    d = np.hypot( e + 3500.0, n - 12000.0 ) / 1600.0
    h += np.where( d < 1.0, -300.0 * ( 1 - d * d ), 0.0 ) + 180.0 * np.exp( -( ( d - 1.0 ) / 0.22 ) ** 2 )
    # The mountains on the horizon: a low, broad range.
    ridge = np.clip( 1.0 - np.abs( sample( g4, e, n, 9000.0 ) ), 0.0, 1.0 )
    mountains = K_smooth( 22000.0, 40000.0, n ) * ( 1200.0 + 3400.0 * ridge ** 1.6 + 500.0 * sample( g1, e, n, 2500.0 ) )
    # The land rises at the world's edge, so its rim is never seen against the sky.
    rim = 3500.0 * K_smooth( WORLD_EDGE * 0.7, WORLD_EDGE, np.maximum( np.abs( e ), n ) )
    return h + np.maximum( mountains, 0.0 ) + rim


def K_smooth( a, b, x ):
    t = np.clip( ( np.asarray( x, float ) - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


def axis_values( lo, hi, fine, near0, near1, growth=1.08, cap=6000.0 ):
    """ Grid lines from lo to hi: every fine between near0 and near1, growing by growth outside, at most cap apart. """
    vals = list( np.arange( near0, near1 + 1e-6, fine ) )
    step, x = fine, near1
    while x < hi:
        step = min( cap, step * growth )
        x += step
        vals.append( min( x, hi ) )
    step, x = fine, near0
    while x > lo:
        step = min( cap, step * growth )
        x -= step
        vals.insert( 0, max( x, lo ) )
    return np.array( vals )


def terrain( m ):
    """ The land as a grid, fine where the window looks and coarser further out, shaded smooth (a normal per point
    from the heights' slopes), dust on the gentle ground and rock on the steep. """
    # Within 60000 of the middle: the engine leaves out a mesh with a point at 90000 ("ignoring mesh").
    # More detail near the observation wall keeps the exposed Martian cliff from reading as broad facets.
    es = axis_values( -WORLD_EDGE, WORLD_EDGE, 160.0, -8000.0, 8000.0, growth=1.06 )
    ns = axis_values( -40000.0, WORLD_EDGE, 160.0, -3000.0, 14000.0, growth=1.06 )
    E, N = np.meshgrid( es, ns )
    Z = terrain_height( E, N )
    # Under the building, keep the ground below the floor.
    under = ( np.abs( E ) < WING_E + 200 ) & ( N > CON_N0 - 200 ) & ( N < HALL_N1 + 60 )
    Z = np.where( under, np.minimum( Z, -80.0 ), Z )
    dz_de = np.gradient( Z, es, axis=1 )
    dz_dn = np.gradient( Z, ns, axis=0 )
    normals = np.stack( [ -dz_de, -dz_dn, np.ones_like( Z ) ], -1 )
    normals /= np.linalg.norm( normals, axis=-1, keepdims=True )
    P = np.stack( [ E, N, Z ], -1 )
    rows, cols = Z.shape
    count = 0
    for i in range( rows - 1 ):
        for j in range( cols - 1 ):
            quad = ( ( i, j ), ( i, j + 1 ), ( i + 1, j + 1 ), ( i + 1, j ) )
            # Use the smoothed quad slope for the dust/bedrock decision. Material boundaries should follow
            # escarpments instead of revealing each triangulation diagonal against the window.
            up = sum( float( normals[a][2] ) for a in quad ) / 4.0
            paint = "ar_regolith" if up > 0.76 else "ar_rock"
            for tri in ( ( quad[0], quad[1], quad[2] ), ( quad[0], quad[2], quad[3] ) ):
                pts = [ P[a] for a in tri ]
                nrm = np.cross( pts[1] - pts[0], pts[2] - pts[0] )
                ln = np.linalg.norm( nrm )
                if ln < 1e-6:
                    continue
                m.polygon( paint, pts, nrm, normals=[ normals[a] for a in tri ] )
                count += 1
    return count


def boulders( m, count=70 ):
    """ Rocks on the plain below the cliff: lumpy, flattened balls of rock. """
    rng = np.random.default_rng( 91 )
    made = 0
    while made < count:
        e, n = rng.uniform( -6000, 6000 ), rng.uniform( 1500, 7000 )
        z = float( terrain_height( np.array( [ e ] ), np.array( [ n ] ) )[0] )
        r = rng.uniform( 40, 160 ) * ( 1.0 + ( n - 1500 ) / 6000 )
        rings, sides = 7, 12
        squash = rng.uniform( 0.5, 0.8 )
        bumps = rng.uniform( 0.82, 1.16, ( rings + 1, sides ) )
        pts = []
        for a in range( rings + 1 ):
            el = -0.25 * math.pi + 0.75 * math.pi * a / rings
            ring = []
            for b in range( sides ):
                az = 2 * math.pi * b / sides + a * 0.3
                rr = r * bumps[a, b] * math.cos( el )
                ring.append( np.array( ( e + rr * math.cos( az ), n + rr * math.sin( az ), z + r * squash * math.sin( el ) * bumps[a, b] ) ) )
            pts.append( ring )
        centre = np.array( ( e, n, z ) )
        for a in range( rings ):
            for b in range( sides ):
                quad = [ pts[a][b], pts[a][( b + 1 ) % sides], pts[a + 1][( b + 1 ) % sides], pts[a + 1][b] ]
                mid = sum( quad ) / 4
                card( m, "ar_rock", quad, mid - centre )
        card( m, "ar_rock", pts[-1], UP )
        made += 1


def dome( m, e, n, z, r, squash=0.72, lit=True ):
    """ A habitat dome: a concrete footing ring, the lattice dome on it, a crown ring. """
    base = np.array( ( e, n, z ) )
    lathe_uv( m, base, [ ( r * 1.04, -200.0 ), ( r * 1.04, 60.0 ), ( r, 60.0 ) ], "ar_concrete_dark", sides=40, u_repeat=8 )
    steps = 9
    profile = [ ( r * math.cos( math.radians( 90 * k / steps ) ), 60.0 + r * squash * math.sin( math.radians( 90 * k / steps ) ) )
                for k in range( steps + 1 ) ]
    profile[-1] = ( r * 0.08, profile[-1][1] )
    lathe_uv( m, base, profile, "ar_dome" if lit else "ar_dome_frame", sides=40, u_repeat=1.0 )
    lathe_uv( m, base, [ ( r * 0.08, profile[-1][1] ), ( r * 0.08, profile[-1][1] + 20 ) ], "ar_dome_frame", sides=12, cap="ar_dome_frame" )
    for k in range( 8 ):
        a = 2 * math.pi * k / 8
        p = base + np.array( ( r * 1.06 * math.cos( a ), r * 1.06 * math.sin( a ), 64 ) )
        m.box( p - np.array( ( 20, 20, 4 ) ), p + np.array( ( 20, 20, 4 ) ), "ar_far_light" )


def tube( m, a, b, r=70.0 ):
    a, b = np.asarray( a, float ), np.asarray( b, float )
    rod( m, a, b, r, "ar_dome_frame", sides=12 )
    length = np.linalg.norm( b - a )
    for k in range( 1, int( length // 400 ) + 1 ):
        p = a + ( b - a ) * k * 400 / length
        m.box( p - np.array( ( 8, 8, r + 4 ) ), p + np.array( ( 8, 8, r + 8 ) ), "ar_far_light" )


def spire_tower( m, e, n, z, scale=1.0, pinnacles=8 ):
    """ A terraforming tower, the picture's spired kind: a podium, a tapering lit shaft with ribs, a flared gallery,
    a narrower upper shaft, a crown of pinnacles round a tall central spire, buttress fins at its foot. """
    k = scale
    base = np.array( ( e, n, z ) )
    lathe_uv( m, base, [ ( 640 * k, -300 ), ( 640 * k, 150 * k ), ( 520 * k, 170 * k ) ], "ar_tower_dark", sides=24, u_repeat=6 )
    m.polygon( "ar_tower_dark", [ base + np.array( ( 520 * k * math.cos( 2 * math.pi * j / 24 ), 520 * k * math.sin( 2 * math.pi * j / 24 ), 170 * k ) ) for j in range( 24 ) ], UP )
    lathe_uv( m, base, [ ( 400 * k, 170 * k ), ( 300 * k, 1700 * k ) ], "ar_tower", sides=20, u_repeat=10, v_span=1700 * k / 6 )
    lathe_uv( m, base, [ ( 300 * k, 1700 * k ), ( 460 * k, 1760 * k ), ( 460 * k, 1800 * k ), ( 250 * k, 1860 * k ) ], "ar_spire", sides=24, u_repeat=8 )
    lathe_uv( m, base, [ ( 250 * k, 1860 * k ), ( 170 * k, 2800 * k ) ], "ar_tower", sides=16, u_repeat=6, v_span=900 * k / 4 )
    lathe_uv( m, base, [ ( 170 * k, 2800 * k ), ( 260 * k, 2860 * k ), ( 200 * k, 2900 * k ) ], "ar_spire", sides=16, u_repeat=6 )
    lathe_uv( m, base, [ ( 150 * k, 2900 * k ), ( 0.0, 4200 * k ) ], "ar_spire", sides=12, u_repeat=4 )
    for j in range( pinnacles ):
        a = 2 * math.pi * j / pinnacles
        p = base + np.array( ( 220 * k * math.cos( a ), 220 * k * math.sin( a ), 0.0 ) )
        lathe_uv( m, p, [ ( 40 * k, 2880 * k ), ( 0.0, 3350 * k ) ], "ar_spire", sides=6, u_repeat=1 )
        m.box( p + np.array( ( -10 * k, -10 * k, 3330 * k ) ), p + np.array( ( 10 * k, 10 * k, 3370 * k ) ), "ar_far_light" )
        q = base + np.array( ( 360 * k * math.cos( a ), 360 * k * math.sin( a ), 0.0 ) )
        lathe_uv( m, q, [ ( 30 * k, 1790 * k ), ( 0.0, 2200 * k ) ], "ar_spire", sides=6, u_repeat=1 )
    # Buttress fins.
    for j in range( 8 ):
        a = 2 * math.pi * ( j + 0.5 ) / 8
        d = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
        side = np.array( ( -math.sin( a ), math.cos( a ), 0.0 ) )
        pts = [ base + d * 300 * k, base + d * 700 * k, base + d * 330 * k + UP * 1300 * k ]
        for sgn in ( -1, 1 ):
            card( m, "ar_tower_dark", [ p + side * sgn * 18 * k for p in pts ], side * sgn )
        card( m, "ar_tower_dark", [ pts[1] - side * 18 * k, pts[2] - side * 18 * k, pts[2] + side * 18 * k, pts[1] + side * 18 * k ],
              d + UP * 0.3 )
    m.box( base + np.array( ( -14 * k, -14 * k, 4180 * k ) ), base + np.array( ( 14 * k, 14 * k, 4260 * k ) ), "ar_led_red" )


def block( m, e, n, z, w, d, h, heading=0.0 ):
    """ A plant building: lit cladding, a dark roof with a vent. """
    F = Frame( e, n, heading, z - 200 )
    F.box( m, -w / 2, w / 2, -d / 2, d / 2, 0, h + 200, { "default": "ar_tower", "+z": "ar_tower_dark" } )
    F.box( m, -w / 6, w / 6, -d / 6, d / 6, h + 200, h + 260, "ar_tower_dark" )


def backdrop():
    m = Model()
    count = terrain( m )
    boulders( m )
    print( f"backdrop: {count} terrain triangles" )
    th = lambda e, n: float( terrain_height( np.array( [ e ] ), np.array( [ n ] ) )[0] )
    # The domes, as the picture has them below the window: a big one with three small, joined by tubes; another group
    # to the west.
    groups = [ ( 2600.0, 5600.0, 900.0, [ ( 1500.0, 4600.0, 380.0 ), ( 3700.0, 4700.0, 420.0 ), ( 3300.0, 6900.0, 360.0 ) ] ),
               ( -2700.0, 4600.0, 560.0, [ ( -1800.0, 3900.0, 260.0 ), ( -3600.0, 5400.0, 300.0 ) ] ),
               ( 600.0, 9200.0, 650.0, [ ( -200.0, 8600.0, 280.0 ) ] ) ]
    for e, n, r, small in groups:
        z = th( e, n )
        dome( m, e, n, z, r )
        for se, sn, sr in small:
            sz = th( se, sn )
            dome( m, se, sn, sz, sr )
            tube( m, ( e, n, z + 80 ), ( se, sn, sz + 80 ) )
    # Spired towers.
    for e, n, scale, pins in ( ( 4700.0, 8400.0, 1.0, 8 ), ( 3400.0, 9800.0, 0.7, 6 ), ( -900.0, 11500.0, 0.85, 8 ),
                               ( 8200.0, 12500.0, 1.4, 10 ), ( -5200.0, 9000.0, 0.6, 6 ), ( 1500.0, 7400.0, 0.5, 6 ) ):
        spire_tower( m, e, n, th( e, n ), scale, pins )
    # Plant buildings round them.
    for e, n, w, d, h, hd in ( ( 4200.0, 7300.0, 900.0, 500.0, 420.0, 10.0 ), ( 5600.0, 9300.0, 700.0, 700.0, 600.0, -15.0 ),
                               ( 1800.0, 6600.0, 500.0, 300.0, 260.0, 30.0 ), ( -1500.0, 10500.0, 800.0, 400.0, 500.0, 0.0 ),
                               ( 7000.0, 11000.0, 1200.0, 600.0, 800.0, 20.0 ), ( -4200.0, 6200.0, 600.0, 400.0, 300.0, -10.0 ) ):
        block( m, e, n, th( e, n ), w, d, h, hd )
    # A road of lights from the cliff's foot to the domes.
    for k in range( 30 ):
        t = k / 29
        e, n = 400.0 + ( 2200.0 - 400.0 ) * t, 1800.0 + ( 4700.0 - 1800.0 ) * t
        z = th( e, n ) + 10
        m.box( ( e - 12, n - 12, z ), ( e + 12, n + 12, z + 16 ), "ar_far_light" )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Lights and probes

COOL = "2.35,2.55,2.95,1"
WARM = "3.0,2.23,1.48,1"
CORE = "3.8,1.42,0.39,1"
SCREEN_GLOW = "1.1,1.95,2.55,1"


def lights():
    out = []
    # The column's glow (no shadows: it's inside its own glass).
    for k, z in enumerate( ( 110.0, 285.0, 520.0 ) ):
        out.append( ( f"Core {k}", ( 0.0, 0.0, z ), CORE, 1190, False ) )
    # Under the hall's trusses.
    for e in ( -900.0, -600.0, -300.0, 300.0, 600.0, 900.0 ):
        for nn in ( -450.0, -50.0, 350.0, 700.0 ):
            out.append( ( f"Hall {e:g} {nn:g}", ( e, nn, 600.0 ), COOL, 950, abs( e ) == 600.0 and nn in ( -50.0, 350.0 ) ) )
    # The arcades, under the galleries.
    for e in ( -760.0, -380.0, 0.0, 380.0, 760.0 ):
        out.append( ( f"North Arcade {e:g}", ( e, 640.0, 170.0 ), WARM, 420, e == 0.0 ) )
        out.append( ( f"South Arcade {e:g}", ( e, -630.0, 170.0 ), WARM, 420, False ) )
    for s in ( -1, 1 ):
        for nn in ( -400.0, 0.0, 380.0 ):
            out.append( ( f"Side Arcade {s} {nn:g}", ( s * 990.0, nn, 170.0 ), WARM, 400, False ) )
        out.append( ( f"Control Room {s}", ( s * 990.0, 330.0, 160.0 ), COOL, 320, True ) )
        # The two active operator consoles give off a local cool screen glow under the warm reactor.
        out.append( ( f"Operator Console {s}", ( s * 230.0, -440.0, 63.0 ), SCREEN_GLOW, 205, False ) )
        # The galleries: lamps on the walls.
        for nn in ( -480.0, 0.0, 420.0 ):
            out.append( ( f"Gallery {s} {nn:g}", ( s * 1040.0, nn, G + 120 ), WARM, 450, False ) )
        # The wings.
        for e in ( 1350.0, 1600.0, 1850.0 ):
            for nn in ( -450.0, -50.0, 350.0 ):
                out.append( ( f"Wing {s} {e:g} {nn:g}", ( s * e, nn, WING_TOP - 40 ), COOL, 700, nn == -50.0 and e == 1600.0 ) )
        for e in ( 1500.0, 1720.0 ):
            out.append( ( f"Wing Under {s} {e:g}", ( s * e, 620.0, 170.0 ), WARM, 360, False ) )
        out.append( ( f"Airlock {s}", ( s * ( WING_E - 40 ), -60.0, 230.0 ), "1.6,0.7,0.35,1", 300, False ) )
        out.append( ( f"Sector Door {s}", ( s * 1250.0, sum( SECTOR_DOOR ) / 2, G + 110 ), WARM, 380, False ) )
        out.append( ( f"North Door {s}", ( s * 1250.0, 620.0, G + 110 ), WARM, 380, False ) )
    for e in ( -800.0, -400.0, 0.0, 400.0, 800.0 ):
        out.append( ( f"Gallery South {e:g}", ( e, -660.0, G + 140 ), WARM, 520, False ) )
        out.append( ( f"Deck {e:g}", ( e, 690.0, G + 120 ), WARM, 450, False ) )
    # The concourse.
    for e in np.arange( -1650.0, 1651.0, 600.0 ):
        for nn in ( -1220.0, -930.0 ):
            out.append( ( f"Concourse {e:g} {nn:g}", ( float( e ), nn, CON_TOP - 30 ), COOL, 700, nn == -1220.0 and abs( e ) == 1050.0 ) )
    out.append( ( "Concourse Airlock", ( 0.0, CON_N0 + 60, 240.0 ), "1.6,0.7,0.35,1", 320, False ) )
    return out


def probes():
    return [ ( "Hall", ( 0, 0, 300 ), ( -HALL_E, HALL_E, HALL_N0, HALL_N1 + 180, 0, HALL_TOP ) ),
             ( "West Wing", ( -1566, 0, 220 ), ( -WING_E, -HALL_E - WALL, HALL_N0, HALL_N1, 0, WING_TOP ) ),
             ( "East Wing", ( 1566, 0, 220 ), ( HALL_E + WALL, WING_E, HALL_N0, HALL_N1, 0, WING_TOP ) ),
             ( "Concourse", ( 0, -1076, 160 ), ( -WING_E, WING_E, CON_N0, HALL_N0 - WALL, 0, CON_TOP ) ) ]


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( -e, n, 0.0 ) for e in ( 1640.0, 1790.0, 1930.0 ) for n in ( -590.0, -440.0, -150.0, -10.0 ) ]
BLUE_SPAWNS = [ ( -e, n, z ) for e, n, z in RED_SPAWNS ]
BUY_ZONE = ( 1380, 2000, -720, 180, -10, 260 )         # Blue Team's; Red Team's is its mirror

DM_HALF = [ ( 420, -120, 0 ), ( 700, 400, 0 ), ( 400, -620, 0 ), ( 980, -120, 0 ), ( 980, 620, 0 ), ( 560, 640, G ),
            ( 1000, 0, G ), ( 400, -640, G ), ( 1500, -560, 0 ), ( 1600, 600, G ), ( 1250, 100, G ), ( 1300, -1000, 0 ),
            ( 600, -1180, 0 ), ( 1750, -1100, 0 ) ]
DM_SPAWNS = [ p for e, n, z in DM_HALF for p in ( ( e, n, z ), ( -e, n, z ) ) ] + [ ( 0, -560, 0 ), ( 0, 230, G ),
                                                                                   ( 0, -1300, 0 ), ( 0, 650, 0 ) ]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 620, 1100, VOID_N1, DECK_N1, G ),
               ( "bombsite_b", "Bomb Site B", 1150, 1720, -1380, -880, 0 ) ]

_ATTACKERS = [ ( -1640, -590, 0 ), ( -1790, -590, 0 ), ( -1640, -440, 0 ), ( -1790, -440, 0 ), ( -1930, -440, 0 ),
               ( -1930, -590, 0 ) ]
RETAKES = {
    "bombsite_a": { "planter": [ ( 860, 640, G ), ( 700, 620, G ) ],
                    "defender": [ ( 1040, 470, G ), ( 1500, 600, G ), ( 960, 640, 0 ) ],
                    "attacker": list( _ATTACKERS ) },
    "bombsite_b": { "planter": [ ( 1300, -1180, 0 ), ( 1240, -1300, 0 ) ],
                    "defender": [ ( 1680, -1180, 0 ), ( 1560, -850, 0 ), ( 1820, -880, 0 ) ],
                    "attacker": list( _ATTACKERS ) },
}

DOMINATION = [ ( "A", ( -1500, 0, 0 ) ), ( "B", ( 0, -400, 0 ) ), ( "C", ( 1500, 0, 0 ) ) ]
HOT_ZONES = [ ( "Atmos Core", ( 0, -400, 0 ) ), ( "Observation Deck", ( 0, 660, G ) ), ( "Rover Bay", ( 0, -1300, 0 ) ),
              ( "West Gallery", ( -990, -100, G ) ), ( "East Gallery", ( 990, -100, G ) ), ( "Window", ( 0, 640, 0 ) ) ]
# ( name, where the cash is, where it's taken )
CASH_POINTS = [ ( "Observation Deck", ( 0, 660, G ), ( 0, -1300, 0 ) ), ( "Rover Bay", ( 0, -1300, 0 ), ( 0, 660, G ) ),
                ( "Atmos Core", ( 0, -400, 0 ), ( 0, 230, G ) ) ]


def callouts():
    lo, hi, up = ( -10, G - DT ), ( G - DT, 440 ), ( G - DT, 700 )
    out = [
        ( "ATMOS CORE", -VOID_E, VOID_E, VOID_N0, VOID_N1, *lo ),
        ( "REACTOR RING", -RING_R1, RING_R1, -RING_R1, RING_R1, *up ),
        ( "OBSERVATION DECK", -HALL_E, HALL_E, VOID_N1, 900, *up ),
        ( "SOUTH GALLERY", -HALL_E, HALL_E, HALL_N0, VOID_N0, *up ),
        ( "WINDOW", -HALL_E, HALL_E, VOID_N1, HALL_N1, *lo ),
        ( "SOUTH ARCADE", -HALL_E, HALL_E, HALL_N0, VOID_N0, *lo ),
        ( "ROVER BAY", -500, 500, CON_N0, CON_N1, *lo ),
    ]
    for s, side, wing_name in ( ( -1, "WEST", "SECTOR 03" ), ( 1, "EAST", "HABITAT B" ) ):
        def span( a, b ):
            return tuple( sorted( ( s * a, s * b ) ) )
        out += [
            ( f"{side} BRIDGE", *span( RING_R1, VOID_E ), -BRIDGE_N, BRIDGE_N, *up ),
            ( f"{side} GALLERY", *span( VOID_E, HALL_E ), VOID_N0, VOID_N1, *up ),
            ( f"{side} CONTROL", *span( VOID_E, HALL_E ), 160, 520, *lo ),
            ( f"{side} ARCADE", *span( VOID_E, HALL_E ), VOID_N0, 160, *lo ),
            ( wing_name, *span( HALL_E + WALL, WING_E ), HALL_N0, HALL_N1, *lo ),
            ( f"{wing_name} UPPER", *span( HALL_E + WALL, WING_E ), HALL_N0, HALL_N1, *hi ),
            ( "CARGO BAY" if s > 0 else "WEST CONCOURSE", *span( 1150, WING_E ), CON_N0, CON_N1, *lo ),
            ( f"{side} CONCOURSE", *span( 500, 1150 ), CON_N0, CON_N1, *lo ),
        ]
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

MINIMAP_CENTRE = ( 0.0, -300.0 )
MINIMAP_SIZE = 4400.0
MINIMAP_PIXELS = 1024


def write_minimap( models ):
    """ Railhead's radar style for two levels: the floors grey, the galleries and mezzanines a lighter blue-grey over
    them, low cover darker, walls left clear, a light line round the edges. North up. """
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "upper", "low", "tall" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    shapes = sorted( R.collision_shapes( models ), key=lambda pts: -float( np.ptp( pts[:, 0] ) * np.ptp( pts[:, 1] ) ) )
    for pts in shapes:
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = R.hull_2d( pts[:, :2] )
        if len( outline ) < 3:
            continue
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if -30 <= z1 <= 18 or ( z0 < 10 and abs( z1 - G ) < 4 ):          # floors, and the stairs' ramps
            draws["walk"].polygon( screen, fill=255 )
        elif G - 40 <= z0 and z1 <= G + 2 and z1 >= G - 2:
            draws["upper"].polygon( screen, fill=255 )
        elif z0 < 72 and 18 < z1 < 100:
            draws["low"].polygon( screen, fill=255 )
        elif z0 < 100 and z1 >= 100:
            draws["tall"].polygon( screen, fill=255 )
    walk, upper, low, tall = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "upper", "low", "tall" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    E, N = np.meshgrid( cols, rows )
    inside = ( E > PLAY[0] ) & ( E < PLAY[1] ) & ( N > PLAY[2] ) & ( N < HALL_N1 + 60 )
    walk &= inside
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[low & inside] = ( 64, 68, 74, 235 )
    image[upper & inside] = ( 128, 140, 156, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    shown = ( walk | ( low & inside ) | ( upper & inside ) ) & ~tall
    edge = np.zeros_like( shown )
    edge[1:, :] |= ~shown[:-1, :]
    edge[:-1, :] |= ~shown[1:, :]
    edge[:, 1:] |= ~shown[:, :-1]
    edge[:, :-1] |= ~shown[:, 1:]
    image[shown & edge] = ( 226, 233, 240, 255 )
    # The column, in the reactor's orange.
    core = np.hypot( E, N ) < RING_R0
    image[core] = ( 220, 110, 40, 255 )
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


def zone_object( name, key, box, color, display, components=(), tags="zone" ):
    centre, scale = plan_box( *box )
    return K.game_object( ids, name, key, centre, tags=tags, components=[
        *components,
        K.component( ids, "Zone", f"{key}/zone", Color=color, DisplayName=display ),
        box_collider( f"{key}/box", scale ),
    ] )


def spawn_object( name, key, position, team, tags="" ):
    """ A TeamSpawnPoint facing the hall: east from the west wing, west from the east. """
    yaw = K.plan_yaw( ( -position[0], -position[1] * 0.3 ) )
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
    ( "ares_hall", "Structure", True, True ), ( "ares_reactor", "Atmos Column", True, True ),
    ( "ares_dressing", "Dressing", True, True ), ( "ares_glass", "Glass", False, False ),
    ( "ares_backdrop", "Mars", False, True ),
]


def model_object( name, key, model_name, collide=True, shadows=True ):
    path = f"{RESOURCE_DIR}/{model_name}.vmdl"
    components = [ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=path,
                                RenderType="On" if shadows else "Off", Tint="1,1,1,1" ) ]
    if collide:
        components.append( K.component( ids, "Sandbox.ModelCollider", f"{key}/collider", IsTrigger=False, Model=path, Static=True ) )
    return K.game_object( ids, name, key, components=components )


def probe_object( name, centre, box ):
    e0, e1, n0, n1, z0, z1 = box
    at = K.to_world( centre )
    lo = K.to_world( ( e1, n0, z0 ) ) - at
    hi = K.to_world( ( e0, n1, z1 ) ) - at
    key = f"probe/{name}"
    return K.game_object( ids, f"Probe {name}", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", Bounds={ "Mins": K.vec( lo ), "Maxs": K.vec( hi ) },
                     DelayBetweenUpdates=0.1, Feathering=0.04, FrameInterval=5, MaxDistance=512, Projection="Box",
                     RenderDynamically=True, TintColor="1,1,1,1", UpdateStrategy="OnEnabled", ZFar=8192, ZNear=8 ) ] )


def look_object():
    """ The grade: ambient occlusion, a warm white balance, bloom for the column's glow, a vignette, auto exposure. """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.68, Radius=72,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=5800,
                     BlendFactor=0.33, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.Bloom", "look/bloom", **{ "__version": 1 }, Mode="Additive", Strength=0.135, Threshold=2.5,
                     Tint="1,1,1,1" ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.19, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=MIN_EXPOSURE, MaximumExposure=MAX_EXPOSURE,
                     Mode="ACES", Rate=1 ),
    ] )


def write_scene( written, light_list, probe_list ):
    world = K.game_object( ids, "Ares", "world", children=[
        model_object( title, f"world/{name}", name, collide, shadows )
        for name, title, collide, shadows in SCENE_MODELS if name in written ] )
    light_objects = [
        K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
                         LightColor=color, Radius=float( radius ), Shadows=bool( shadows ) ) ] )
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

    play_centre, play_scale = plan_box( PLAY[0], PLAY[1], PLAY[2], PLAY[3], -300, 1000 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
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
                         Description="The Ares Facility's atmosphere-processing hall on Mars: galleries round the glowing "
                                     "ATMOS PROCESSING column, a window wall over the red plain, two spawn wings and a cargo "
                                     "concourse.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # The Martian sun, low in the south-east behind the hall, lighting the plain the window looks over.
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor="1.48,1.06,0.75,1", ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
                         ShadowHardness=0, Shadows=True, SkyColor="0.13,0.083,0.061,1" ),
        ] ),
        K.game_object( ids, "Sky", "sky", tags="skybox", components=[
            K.component( ids, "Sandbox.SkyBox2D", "sky/box", SkyIndirectLighting=True, SkyMaterial=SKY_MATERIAL, Tint="1,1,1,1" ),
        ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color=f"{FOG_COLOUR},0.68", StartDistance=5200,
                         EndDistance=68000, FalloffExponent=1.55, Height=7000, VerticalFalloffExponent=1.3 ),
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

def build():
    hall, glass, column_model, dressed = Model(), Model(), Model(), Model()
    floors( hall )
    window_wall( hall, glass )
    hall_walls( hall )
    galleries( hall )
    ring_and_bridges( hall )
    hall_stairs( hall )
    control_rooms( hall, glass )
    wings( hall, glass )
    concourse( hall, glass )
    reactor( column_model, glass )
    dressing( dressed )
    models = {
        "ares_hall": hall,
        "ares_reactor": column_model,
        "ares_dressing": dressed,
        "ares_glass": glass,
        "ares_backdrop": backdrop(),
    }
    for model in models.values():
        configure( model )
    return models


# The menu picture's view: on the south-east gallery, looking north-west past the column to the window, as the
# reference picture is framed. ( eye, target ) in plan, and the horizontal field of view.
ART_VIEW = ( ( 800.0, -680.0, G + 66 ), ( -200.0, 640.0, G + 40 ), 92.0 )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", metavar="DIR", help="also write the reach grid's picture to this folder" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    parser.add_argument( "--scene-only", action="store_true", help="update lighting and postprocessing using existing models, for fast visual iteration" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture (flat-shaded)" )
    args = parser.parse_args()

    if args.scene_only:
        if args.no_scene or args.preview or args.art:
            parser.error( "--scene-only cannot be combined with model-generation or preview options" )
        available = { name for name, _, _, _ in SCENE_MODELS if ( OUT_DIR / f"{name}.vmdl" ).exists() }
        missing_models = { name for name, _, _, _ in SCENE_MODELS } - available
        if missing_models:
            parser.error( f"build the Ares models first: {', '.join( sorted( missing_models ) )}" )
        write_scene( available, lights(), probes() )
        return

    missing = [ p for p in AM.all_paints() if not ( AM.OUT_DIR / f"{p}.vmat" ).exists() ]
    if missing:
        print( f"run Tools/ares_materials.py first: no material for {', '.join( missing )}" )
    models = build()
    written = set()
    for name, model in models.items():
        if K.is_empty( model ):
            print( f"{name}: empty, not written" )
            continue
        count = K.write_model( OUT_DIR, RESOURCE_DIR, name, model )
        written.add( name )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
    if R.UNKNOWN_PAINTS:
        print( f"paints with no material: {', '.join( sorted( R.UNKNOWN_PAINTS ) )}" )
    light_list = lights()
    probe_list = probes()
    print( f"{len( light_list )} lights ({sum( 1 for l in light_list if l[4] )} with shadows), {len( probe_list )} probes" )

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
        write_minimap( solid )
        write_scene( written, light_list, probe_list )


if __name__ == "__main__":
    main()
