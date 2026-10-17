"""
Riverdale's reactor hall: the spent fuel building round its pool, built for Tools/riverdale_map.py.

Plan coordinates (map_kit's: e east, n north, z up, inches). The hall is e -1000..1000, n -200..2000 inside its 40 in
walls, its deck at z 0 and its roof's underside at 1000 (51 x 56 x 25 m, deeper than wide, so from its south end the
pool, the blocks and the far wall stand one behind another as in the reference). Built as the reference shows it:
- The pool, 1040 in across (26 m) round (0, 900): a stainless liner 520 in deep (13 m) under water 30 in below the
  deck, fuel racks on its floor, cyan lamps set into its wall, and a yellow railing all round on the coping
  (player-clipped up to the roof: nobody falls in). A skimmer gutter runs under the coping, the transfer canal's gate
  stands in its north wall, a ladder and long-handled tools hang into the water.
- The fuel handling mast standing in the water under the overhead crane's trolley: four yellow angle columns, struts
  and bracing, grating platforms, a ladder, a hose bundle, its machinery head and a lit cage round its foot.
- The overhead crane on runway girders along the side walls, which sit on tapered concrete corbels with their rails,
  clips, end stops and conductor bars: two box girders across the hall round the mast with the operator's logo and
  "SWL 125 T", end trucks on their wheels with drives and buffers, the trolley with its hoist drum, motor, gearbox
  and brake, the hook block on its rope falls, the operator's cab and a festoon of cables.
- The control rooms: glass-fronted rooms at the upper level (z 288) on the side walls beside the pool's near half, on
  steel girders and columns over the deck, each reached by a steel stair from the south deck to a landing at its south
  face. From the hall's south end the west one stands upper left, its stair rising away below it. Inside: two rows of
  consoles facing the glass (keyboards, button panels, monitors on arms, chairs), cabinets and a mimic board set into
  the back wall, a video wall on the north wall, an access floor and a suspended ceiling with light panels.
- B1 and B2: concrete blocks either side of the pool's far half, whose tops are part of the upper level's walkway
  along the side and north walls.
- Water purification tanks on the south-east deck with their manways, nozzles, level gauges, valves, top railings and
  a transfer pump; equipment cases with the logo on the south-west deck.
- The north wall: the logo between "CLEAN ENERGY / A BRIGHTER TOMORROW" and "SAFETY / PEOPLE / PROGRESS", pilasters,
  vertical pipe bundles with flow markers, a supply duct, doors and lamps along both levels.
- The roof: Warren trusses with double-angle chords and gusset plates, purlins, bracing, a galvanised deck, spiral
  supply ducts, sprinkler mains and round LED high bays hung from struts.
- The walls: an epoxy band round their foot (a decontaminable coating), ladder cable trays, conduits, and what a plant
  keeps on its walls: extinguishers, hose cabinets, distribution boards, radiation monitors, eye washes, phones,
  first aid, cameras, horns, exit signs, signs. The floor: safety lines, hatching round the pool and by the doors,
  stencils and drains.
- Outside: a base course, string courses, the parapet's coping, downpipes, and plant on the roof.
Doors: west and east (to the A2/A1 annexes), south (to the yard), and two north (to the north lane).

What's finer than the shapes above is drawn in two more models (extra_models(); both drawn only):
- riverdale_hall_detail casts shadows: the steel (trusses, purlins, the crane, girders under the upper level, trays),
  ducts, the control rooms' furniture and ceilings, the tanks' fittings, the outside's courses, coping, downpipes and
  roof plant.
- riverdale_hall_fine casts none: floor paint and stencils, the epoxy band, signs and labels, conduits, wall equipment,
  keyboards, screens, lamps and nosings.
The collision is the shapes above, as before: where a drawn box became something finer (the control rooms' desks), its
box is kept with collision_box. Below head height nothing new stands more than about 8 in off a wall; anything bigger
is overhead, in the pool, inside an existing collision box (the consoles in the desks', the posts under the stairs) or
flush with a wall (the control rooms' cabinets and mimic board).

Its own materials ride along as EXTRA_PAINTS (flat) and EXTRA_SURFACES (drawn), which riverdale_materials.load_extras
writes with the rest:
    rv_hall_epoxy           epoxy paint on concrete, the walls' lower band (96 in tile)
    rv_hall_ceiling         suspended ceiling: 24 in mineral fibre tiles in a white T-bar grid (48 in tile)
    rv_hall_access          raised access floor: 24 in vinyl-faced panels (48 in tile)
    rv_hall_deck            the roof's galvanised trapezoidal deck seen from below (48 in tile)
    rv_hall_interior        painted plaster: the control rooms' walls (96 in tile)
    rv_hall_roof            the roof's single-ply membrane (192 in tile)
    rv_hall_signs           one atlas (SIGNS): signs, labels, pipe markers, a keyboard, button and meter panels, the
                            mimic board, cabinet doors, grilles, a clock, notice boards, floor stencils
and it uses the map's own: rv_wall_clean for every face indoors (indoor()), rv_galv and rv_stainless, rv_line_yellow (floor
paint worn through, alpha tested) for its lines, hatching and nosings, and rv_grime_foot / rv_grime_top (blended grime)
on its outside.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

import map_kit as K
import riverdale_materials as RM
import riverdale_parts as P
from riverdale_parts import v, card, box, UP, METAL, STONE

# The hall.
E0, E1, N0, N1 = -1000.0, 1000.0, -200.0, 2000.0
WT = 40.0
TOP = 1000.0
ROOF = 1040.0
POOL = ( 0.0, 900.0 )
POOL_R = 520.0
WATER_Z = -30.0
POOL_FLOOR = -520.0
UPPER = 288.0
SLAB = 18.0
CRANE_Z = 830.0
CRANE_N = ( 840.0, 960.0 )
MAST = ( 70.0, 900.0 )

# Openings: ( along from, along to, z top )
WEST_DOOR = ( -40.0, 80.0, 132.0 )          # n, in the west wall (from the annex); east the same
SOUTH_DOOR = ( -96.0, 96.0, 140.0 )          # e
NORTH_DOORS = ( ( -470.0, -350.0, 132.0 ), ( 350.0, 470.0, 132.0 ) )

# The west side's upper level (the east side is its mirror, e -> -e).
STAIR = ( -760.0, -700.0, 160.0, 580.0 )     # e0, e1, foot n, head n
LANDING = ( -1000.0, -560.0, 580.0, 660.0 )
CONTROL = ( -1000.0, -560.0, 660.0, 1200.0 )
WALKWAY = ( -1000.0, -860.0, 1200.0, 1860.0 )
BLOCK = ( -1000.0, -640.0, 1300.0, 1640.0 )
NORTH_WALK = ( -1000.0, 1000.0, 1860.0, 2000.0 )
CONTROL_TOP = 468.0
TANKS = ( ( 600.0, -10.0 ), ( 600.0, 170.0 ) )
TANK_R, TANK_H = 64.0, 400.0

# Detail.
CEILING_Z = UPPER + 156.0                    # the control rooms' suspended ceiling, 12 in under their roof slab
TRUSS_ES = [ float( e ) for e in np.arange( E0 + 125, E1, 250.0 ) ]
TRUSS_BOTTOM, TRUSS_DEPTH = TOP - 66.0, 60.0
CONTROL_COLUMNS = ( ( -572.0, 592.0 ), ( -572.0, 860.0 ), ( -572.0, 1188.0 ), ( -830.0, 592.0 ), ( -830.0, 1188.0 ) )
DECK_TRAY_Z, UPPER_TRAY_Z = 200.0, UPPER + 172.0
NORTH_BUNDLES = ( -928.0, -666.0, 666.0, 928.0 )
SIDE_RISERS = ( 220.0, 1450.0 )              # the side walls' vertical pipe runs (n of their first pipe)
DUCT_ES = ( -500.0, 500.0 )                  # the roof's supply ducts, along n
DUCT_Z, DUCT_R = 958.0, 15.0


# ---------------------------------------------------------------------------------------------------------------------
# Materials

# Flat paints: colour (sRGB), metalness, roughness, self-illumination (as riverdale_materials.PAINTED).
EXTRA_PAINTS = {
    "rv_hall_joint": ( ( 36, 37, 38 ), 0.0, 0.85, 0 ),
    "rv_hall_console": ( ( 172, 174, 172 ), 0.2, 0.42, 0 ),
    "rv_hall_console_dark": ( ( 56, 60, 64 ), 0.3, 0.42, 0 ),
    "rv_hall_worktop": ( ( 52, 54, 56 ), 0.0, 0.34, 0 ),
    "rv_hall_bezel": ( ( 14, 14, 16 ), 0.0, 0.3, 0 ),
    "rv_hall_plastic": ( ( 30, 31, 33 ), 0.0, 0.55, 0 ),
    "rv_hall_plastic_grey": ( ( 124, 126, 128 ), 0.0, 0.5, 0 ),
    "rv_hall_fabric": ( ( 36, 40, 48 ), 0.0, 0.92, 0 ),
    "rv_hall_chrome": ( ( 196, 198, 202 ), 1.0, 0.2, 0 ),
    "rv_hall_red": ( ( 166, 22, 18 ), 0.1, 0.4, 0 ),
    "rv_hall_green": ( ( 20, 118, 64 ), 0.1, 0.45, 0 ),
    "rv_hall_blue": ( ( 28, 66, 134 ), 0.1, 0.45, 0 ),
    "rv_hall_equipment": ( ( 196, 196, 188 ), 0.2, 0.48, 0 ),     # light grey enclosures (RAL 7035)
    "rv_hall_cable": ( ( 22, 22, 24 ), 0.0, 0.7, 0 ),
    "rv_hall_rope": ( ( 92, 94, 96 ), 0.85, 0.45, 0 ),
    "rv_hall_paper": ( ( 228, 226, 218 ), 0.0, 0.85, 0 ),
    "rv_hall_cork": ( ( 150, 112, 70 ), 0.0, 0.9, 0 ),
    "rv_hall_led_green": ( ( 60, 255, 110 ), 0.0, 0.3, 4 ),
    "rv_hall_led_red": ( ( 255, 52, 36 ), 0.0, 0.3, 4 ),
    "rv_hall_led_amber": ( ( 255, 176, 40 ), 0.0, 0.3, 4 ),
    "rv_hall_troffer": ( ( 232, 238, 248 ), 0.0, 0.3, 4 ),
    "rv_hall_exit": ( ( 40, 214, 100 ), 0.0, 0.3, 3 ),
    "rv_hall_emergency": ( ( 255, 244, 222 ), 0.0, 0.3, 3 ),
}


def _tex( seed, n, tile ):
    rng = np.random.default_rng( seed )
    nz, x, z, ppi = RM.field( rng, n, tile )
    return rng, nz, x, z, ppi


def epoxy( seed=301, n=None ):
    """ Epoxy paint on concrete (a decontaminable coating), the walls' lower band: slate grey, glossy, the slab's pores
    showing through as pinholes, roller laps, pale scuffs and a few knocks to bare concrete. 96 in tile. """
    n = n or RM.px( 1024 )
    rng, nz, x, z, ppi = _tex( seed, n, 96.0 )
    c = RM.lin( ( 84, 96, 104 ) )[None, None, :] * ( 1.0 + 0.04 * nz( 2.4, 60, 6 ) + 0.015 * nz( 1.0, 2, 0.2 ) )[..., None]
    lap = np.sin( x * ( 2 * math.pi / 9.0 ) + 1.2 * nz( 2.2, 40, 6 ) )
    c = c * ( 1.0 + 0.012 * lap )[..., None]
    rough = 0.3 + 0.05 * nz( 2.0, 16, 2 ) + 0.03 * lap
    height = 0.004 * nz( 0.8, 0.5, 0.08 )
    pits = RM.smoothstep( 2.9, 3.4, nz( 0.4, 0.5, 0.08 ) )
    c = RM.mix( c, c * 0.55, pits * 0.8 )
    height = height - 0.03 * pits
    cv = RM.BM.Canvas( ( n, n ), ( ppi, ppi ), ( 0.0, 0.0 ), 96.0, ss=1 )
    for _ in range( 14 ):
        cx, cz = rng.uniform( 4, 92 ), rng.uniform( 4, 92 )
        a = rng.normal( 0, 0.5 ) + ( math.pi if rng.random() < 0.5 else 0.0 )
        L = rng.uniform( 1.5, 7 )
        cv.line( [ ( cx, cz ), ( cx + L * math.cos( a ), cz + L * math.sin( a ) * 0.6 ) ], rng.uniform( 0.3, 1.4 ), rng.uniform( 0.2, 0.5 ) )
    scuff = RM.ndimage.gaussian_filter( cv.result(), 1.2, mode="wrap" )
    c = RM.mix( c, RM.lin( ( 140, 148, 152 ) ), scuff * 0.3 )
    rough = rough + 0.35 * scuff
    knock = RM.smoothstep( 2.7, 3.1, nz( 1.6, 3, 0.3 ) )
    bare = RM.lin( ( 128, 128, 124 ) )[None, None, :] * ( 1.0 + 0.06 * nz( 0.6, 0.5, 0.1 ) )[..., None]
    c = RM.mix( c, bare, knock )
    rough = RM.mix( rough, 0.85, knock )
    height = height - 0.02 * knock
    return c, np.clip( rough, 0.05, 1.0 ), height, ppi


def ceiling_tiles( seed=302, n=None ):
    """ A suspended ceiling: 24 in mineral fibre tiles, fissured, set a little above their white T-bar grid (15/16 in),
    two by two in a 48 in tile; one has an old water stain. """
    n = n or RM.px( 1024 )
    rng, nz, x, z, ppi = _tex( seed, n, 48.0 )
    g = 24.0
    d = np.minimum( np.minimum( x % g, g - x % g ), np.minimum( z % g, g - z % g ) )
    bar = RM.smoothstep( 0.52, 0.4, d )
    edge = RM.smoothstep( 1.4, 0.5, d ) * ( 1.0 - bar )
    ti, tj = ( x // g ).astype( int ) % 2, ( z // g ).astype( int ) % 2
    tone = rng.normal( 0, 0.025, ( 2, 2 ) ).astype( np.float32 )[ti, tj]
    fiss = RM.smoothstep( 1.8, 2.5, nz( 0.5, 0.5, 0.06 ) + 0.6 * nz( 1.2, 2.0, 0.1 ) )
    c = RM.lin( ( 222, 222, 214 ) )[None, None, :] * ( 1.0 + tone + 0.02 * nz( 2.2, 20, 2 ) )[..., None]
    c = RM.mix( c, c * 0.7, fiss * 0.55 )
    inside = ( ( x > 24 ) & ( z < 24 ) ).astype( np.float32 )
    stain_d = np.hypot( ( x - 36 ) / 7.0, ( z - 12 ) / 5.0 ) + 0.4 * nz( 1.6, 4, 0.4 )
    stain = RM.smoothstep( 1.0, 0.6, stain_d ) * inside
    ring = RM.smoothstep( 0.2, 0.0, np.abs( stain_d - 0.95 ) ) * inside
    c = RM.mix( c, RM.lin( ( 196, 182, 150 ) ), np.clip( stain * 0.35 + ring * 0.4, 0, 1 ) )
    c = c * ( 1.0 - 0.35 * edge )[..., None]
    c = RM.mix( c, RM.lin( ( 238, 238, 234 ) ), bar )
    height = -0.15 * ( 1.0 - bar ) - 0.03 * fiss
    rough = 0.92 - 0.45 * bar
    return c, rough, height, ppi


def access_floor( seed=303, n=None ):
    """ Raised access floor: 24 in panels in grey anti-static vinyl with a darker fleck, hairline joints, a little
    different panel to panel, scuffed where chairs roll. 48 in tile. """
    n = n or RM.px( 1024 )
    rng, nz, x, z, ppi = _tex( seed, n, 48.0 )
    g = 24.0
    d = np.minimum( np.minimum( x % g, g - x % g ), np.minimum( z % g, g - z % g ) )
    joint = RM.smoothstep( 0.12, 0.04, d )
    ti, tj = ( x // g ).astype( int ) % 2, ( z // g ).astype( int ) % 2
    tone = rng.normal( 0, 0.03, ( 2, 2 ) ).astype( np.float32 )[ti, tj]
    fleck = RM.smoothstep( 1.6, 2.4, nz( 0.4, 0.3, 0.04 ) )
    c = RM.lin( ( 150, 152, 152 ) )[None, None, :] * ( 1.0 + tone + 0.03 * nz( 2.0, 12, 1 ) )[..., None]
    c = RM.mix( c, RM.lin( ( 76, 78, 80 ) ), fleck * 0.7 )
    c = RM.mix( c, RM.lin( ( 40, 40, 40 ) ), joint )
    scuff = RM.smoothstep( 0.8, 2.4, nz( 2.2, 20, 1.5 ) )
    c = RM.mix( c, c * 0.82, scuff * 0.5 )
    rough = 0.48 + 0.06 * nz( 2.0, 10, 1 ) - 0.12 * scuff + 0.3 * joint
    height = -0.06 * joint + 0.002 * nz( 0.8, 0.3, 0.05 )
    return c, np.clip( rough, 0.1, 1.0 ), height, ppi


def roof_deck( seed=304, n=None ):
    """ The roof's underside: galvanised trapezoidal deck, 3 in deep ribs at 12 in centres running up the picture,
    dulled grey with its spangle, darker and grimier in the troughs. 48 in tile. """
    n = n or RM.px( 1024 )
    rng, nz, x, z, ppi = _tex( seed, n, 48.0 )
    p = x % 12.0

    def ramp( a, b ):
        return np.clip( ( p - a ) / ( b - a ), 0.0, 1.0 )

    rib = ramp( 3.5, 5.0 ) - ramp( 9.5, 11.0 )          # 1 on a rib's flange (nearest from below), 0 in a trough
    web = ( ( p > 3.5 ) & ( p < 5.0 ) ) | ( ( p > 9.5 ) & ( p < 11.0 ) )
    spangle = RM.smoothstep( -0.5, 0.5, nz( 0.5, 0.8, 0.15 ) )
    c = RM.lin( ( 132, 136, 138 ) )[None, None, :] * ( 1.0 + 0.06 * spangle + 0.05 * nz( 2.2, 40, 4 ) )[..., None]
    c = c * np.where( web, 0.78, 1.0 )[..., None] * ( 0.8 + 0.2 * rib )[..., None]
    grime = RM.smoothstep( 0.5, 2.0, nz( 2.4, 30, 3 ) ) * ( 1.0 - rib )
    c = RM.mix( c, RM.BM.GRIME, grime * 0.35 )
    rough = 0.5 + 0.08 * spangle + 0.15 * grime
    return c, rough, 3.0 * rib, ppi


def interior_paint( seed=306, n=None ):
    """ The control rooms' walls: eggshell paint on plaster, a warm light grey, a roller's stipple, faint marks.
    96 in tile. """
    n = n or RM.px( 1024 )
    rng, nz, x, z, ppi = _tex( seed, n, 96.0 )
    stipple = nz( 0.9, 0.4, 0.06 )
    c = RM.lin( ( 188, 188, 182 ) )[None, None, :] * ( 1.0 + 0.02 * nz( 2.4, 40, 4 ) + 0.012 * stipple )[..., None]
    marks = RM.smoothstep( 1.8, 2.6, nz( 2.0, 10, 1 ) )
    c = RM.mix( c, c * 0.88, marks * 0.4 )
    rough = 0.72 + 0.04 * nz( 2.0, 10, 1 )
    return c, rough, 0.004 * stipple, ppi


def roof_membrane( seed=308, n=None ):
    """ The roof's top: a grey single-ply membrane welded in 64 in widths (their laps up the picture), dirt washed into
    the laps, ponding stains. 192 in tile. """
    n = n or RM.px( 1024 )
    rng, nz, x, z, ppi = _tex( seed, n, 192.0 )
    lap = RM.smoothstep( 1.2, 0.2, np.abs( x % 64.0 - 2.0 ) )
    c = RM.lin( ( 120, 122, 122 ) )[None, None, :] * ( 1.0 + 0.05 * nz( 2.4, 80, 8 ) + 0.03 * nz( 1.0, 2, 0.3 ) )[..., None]
    pond = RM.smoothstep( 1.2, 2.2, nz( 2.6, 120, 20 ) )
    c = RM.mix( c, c * 0.72, pond * 0.6 )
    c = RM.mix( c, RM.BM.GRIME, lap * 0.4 )
    rough = 0.78 - 0.2 * pond
    return c, rough, 0.08 * lap, ppi


# ---------------------------------------------------------------------------------------------------------------------
# The signs atlas (rv_hall_signs): a shelf-packed sheet, its regions by name, drawn opaque (no alpha), so every sign is
# a plate with its own background.

SIGN_ATLAS = ( 2048, 2048 )
_SIGN_SIZES = [
    ( "mimic", 1024, 512 ), ( "rack", 256, 512 ), ( "pool_rules", 384, 416 ), ( "panel_door", 256, 384 ),
    ( "fire_ext", 256, 320 ), ( "eyewash", 256, 320 ), ( "first_aid", 256, 320 ), ( "hardhat", 384, 320 ),
    ( "rca", 512, 320 ), ( "crane", 384, 320 ), ( "buttons", 512, 256 ), ( "meters", 512, 256 ),
    ( "annunciator", 512, 256 ), ( "whiteboard", 512, 256 ), ( "noticeboard", 512, 256 ), ( "hv_warning", 256, 224 ),
    ( "logo_plate", 512, 192 ), ( "keyboard", 512, 160 ), ( "phone", 128, 160 ), ( "clock", 160, 160 ),
    ( "drain", 160, 160 ), ( "diffuser", 160, 160 ), ( "speaker", 160, 160 ), ( "camera", 160, 160 ),
    ( "papers", 160, 160 ), ( "binders", 352, 160 ), ( "control_plate", 512, 128 ), ( "filter_b1", 384, 128 ),
    ( "filter_b2", 384, 128 ), ( "arm", 512, 128 ), ( "keep_clear", 512, 128 ), ( "no_storage", 512, 128 ),
    ( "walkway", 512, 128 ), ( "hose_label", 256, 128 ), ( "callpoint", 128, 128 ), ( "grille", 256, 128 ),
    ( "vent", 256, 128 ), ( "tk201", 256, 96 ), ( "tk202", 256, 96 ), ( "p201", 256, 96 ), ( "db3", 256, 96 ),
    ( "lcp", 256, 96 ), ( "cam_tag", 256, 96 ), ( "pipe_demin", 512, 64 ), ( "pipe_cool", 512, 64 ),
    ( "pipe_air", 512, 64 ), ( "pipe_fire", 512, 64 ), ( "pipe_waste", 512, 64 ), ( "pipe_hvac", 512, 64 ),
    ( "pipe_n2", 512, 64 ), ( "pipe_power", 512, 64 ), ( "stations", 384, 64 ),
]


def _pack( sizes, width, height ):
    """ Shelves, tallest first. """
    out, x, y, shelf = {}, 0, 0, 0
    for name, w, h in sorted( sizes, key=lambda r: ( -r[2], -r[1] ) ):
        if x + w > width:
            x, y, shelf = 0, y + shelf, 0
        out[name] = ( x, y, w, h )
        x += w
        shelf = max( shelf, h )
    assert y + shelf <= height, "the signs don't fit their atlas"
    return out


SIGNS = _pack( _SIGN_SIZES, *SIGN_ATLAS )

# The mimic board's indicator lamps: ( u right, v up ) in its region, and their colour. The atlas draws a socket for
# each, and the control rooms put a lit lens in each.
MIMIC_LAMPS = ( ( 0.15, 0.78, "green" ), ( 0.27, 0.66, "green" ), ( 0.27, 0.41, "red" ), ( 0.38, 0.75, "green" ),
                ( 0.38, 0.50, "amber" ), ( 0.47, 0.66, "green" ), ( 0.55, 0.75, "green" ), ( 0.55, 0.50, "green" ),
                ( 0.63, 0.41, "amber" ), ( 0.70, 0.75, "green" ), ( 0.70, 0.50, "red" ), ( 0.79, 0.57, "green" ),
                ( 0.86, 0.80, "green" ), ( 0.86, 0.50, "green" ), ( 0.94, 0.25, "amber" ), ( 0.10, 0.13, "green" ) )

_INK = ( 22, 22, 24 )
_WHITE = ( 238, 238, 232 )
_YELLOW = ( 236, 188, 32 )
_RED = ( 176, 26, 22 )
_GREEN = ( 22, 128, 70 )
_BLUE = ( 30, 76, 150 )
_MAGENTA = ( 166, 32, 120 )


def _sub( b, fx, fy, fw, fh ):
    x, y, w, h = b
    return ( x + w * fx, y + h * fy, w * fw, h * fh )


def _rect( d, b, fill=None, outline=None, width=0 ):
    x, y, w, h = b
    d.rectangle( ( x, y, x + w - 1, y + h - 1 ), fill=fill, outline=outline, width=max( 0, int( round( width ) ) ) )


def _ellipse( d, cx, cy, r, fill=None, outline=None, width=0 ):
    d.ellipse( ( cx - r, cy - r, cx + r, cy + r ), fill=fill, outline=outline, width=max( 0, int( round( width ) ) ) )


def _text( d, b, lines, fill, align="center", light=False, track=0.06, pad=0.08 ):
    RM.text_block( d, b, lines, fill=fill, align=align, light=light, track=track, pad=pad )


def _plate( d, b, bg, lines, fg, band=None, band_lines=None, band_fg=_WHITE, border=None ):
    """ A sign: its background, an optional band across the top with its own words, the words, a border. """
    _rect( d, b, bg )
    x, y, w, h = b
    top = 0.0
    if band is not None:
        _rect( d, ( x, y, w, h * 0.3 ), band )
        if band_lines:
            _text( d, ( x, y, w, h * 0.3 ), band_lines, band_fg )
        top = 0.3
    if lines:
        _text( d, ( x, y + h * top, w, h * ( 1 - top ) ), lines, fg )
    if border is not None:
        _rect( d, _sub( b, 0.025, 0.04, 0.95, 0.92 ), None, border, max( 2, h * 0.025 ) )


def _trefoil( d, cx, cy, r, ink, bg ):
    _ellipse( d, cx, cy, r * 0.2, ink )
    for k in range( 3 ):
        a0 = -90 + 120 * k - 30
        d.pieslice( ( cx - r, cy - r, cx + r, cy + r ), a0, a0 + 60, fill=ink )
    _ellipse( d, cx, cy, r * 0.32, bg )
    _ellipse( d, cx, cy, r * 0.2, ink )


def _draw_signs( d, box, rng ):
    """ Every region but the panels'. """
    _plate( d, box( "fire_ext" ), _RED, None, _WHITE )
    x, y, w, h = box( "fire_ext" )
    d.rounded_rectangle( ( x + w * 0.38, y + h * 0.18, x + w * 0.62, y + h * 0.62 ), radius=w * 0.08, fill=_WHITE )
    _rect( d, ( x + w * 0.44, y + h * 0.1, w * 0.12, h * 0.09 ), _WHITE )
    d.line( ( x + w * 0.56, y + h * 0.14, x + w * 0.74, y + h * 0.22, x + w * 0.7, y + h * 0.42 ), fill=_WHITE, width=int( w * 0.04 ) )
    _text( d, ( x, y + h * 0.66, w, h * 0.3 ), [ "FIRE", "EXTINGUISHER" ], _WHITE )
    x, y, w, h = box( "eyewash" )
    _rect( d, ( x, y, w, h ), _GREEN )
    _ellipse( d, x + w * 0.5, y + h * 0.36, w * 0.2, _WHITE )
    d.ellipse( ( x + w * 0.38, y + h * 0.3, x + w * 0.62, y + h * 0.4 ), fill=_GREEN )
    _ellipse( d, x + w * 0.5, y + h * 0.35, w * 0.05, _WHITE )
    for k in range( 3 ):
        d.line( ( x + w * ( 0.38 + 0.12 * k ), y + h * 0.1, x + w * ( 0.42 + 0.08 * k ), y + h * 0.22 ), fill=_WHITE, width=int( w * 0.03 ) )
    _text( d, ( x, y + h * 0.64, w, h * 0.32 ), [ "EMERGENCY", "EYE WASH" ], _WHITE )
    x, y, w, h = box( "first_aid" )
    _rect( d, ( x, y, w, h ), _GREEN )
    _rect( d, ( x + w * 0.42, y + h * 0.12, w * 0.16, h * 0.44 ), _WHITE )
    _rect( d, ( x + w * 0.24, y + h * 0.27, w * 0.52, h * 0.14 ), _WHITE )
    _text( d, ( x, y + h * 0.64, w, h * 0.3 ), [ "FIRST AID" ], _WHITE )
    x, y, w, h = box( "hardhat" )
    _rect( d, ( x, y, w, h ), _WHITE )
    _ellipse( d, x + w * 0.5, y + h * 0.33, h * 0.27, _BLUE )
    d.chord( ( x + w * 0.5 - h * 0.17, y + h * 0.18, x + w * 0.5 + h * 0.17, y + h * 0.5 ), 180, 360, fill=_WHITE )
    _rect( d, ( x + w * 0.5 - h * 0.21, y + h * 0.33, h * 0.42, h * 0.05 ), _WHITE )
    _text( d, ( x, y + h * 0.64, w, h * 0.32 ), [ "HARD HATS AND SAFETY", "GLASSES MUST BE WORN" ], _INK )
    x, y, w, h = box( "rca" )
    _rect( d, ( x, y, w, h ), _YELLOW )
    _rect( d, ( x, y, w, h * 0.24 ), _MAGENTA )
    _text( d, ( x, y, w, h * 0.24 ), [ "CAUTION" ], _YELLOW )
    _trefoil( d, x + w * 0.16, y + h * 0.6, h * 0.24, _MAGENTA, _YELLOW )
    _text( d, ( x + w * 0.3, y + h * 0.28, w * 0.7, h * 0.66 ), [ "RADIOLOGICALLY", "CONTROLLED AREA", "DOSIMETER REQUIRED" ], _INK, "left" )
    x, y, w, h = box( "crane" )
    _rect( d, ( x, y, w, h ), _YELLOW )
    _rect( d, ( x, y, w, h * 0.3 ), _INK )
    _text( d, ( x, y, w, h * 0.3 ), [ "DANGER" ], _YELLOW )
    _text( d, ( x, y + h * 0.32, w, h * 0.64 ), [ "OVERHEAD CRANE", "KEEP CLEAR OF", "SUSPENDED LOADS" ], _INK )
    _rect( d, _sub( ( x, y, w, h ), 0.02, 0.02, 0.96, 0.96 ), None, _INK, h * 0.02 )
    x, y, w, h = box( "hv_warning" )
    _rect( d, ( x, y, w, h ), _WHITE )
    d.polygon( [ ( x + w * 0.5, y + h * 0.05 ), ( x + w * 0.9, y + h * 0.66 ), ( x + w * 0.1, y + h * 0.66 ) ], fill=_INK )
    d.polygon( [ ( x + w * 0.5, y + h * 0.13 ), ( x + w * 0.83, y + h * 0.62 ), ( x + w * 0.17, y + h * 0.62 ) ], fill=_YELLOW )
    d.polygon( [ ( x + w * 0.53, y + h * 0.2 ), ( x + w * 0.42, y + h * 0.42 ), ( x + w * 0.52, y + h * 0.42 ),
                 ( x + w * 0.46, y + h * 0.58 ), ( x + w * 0.6, y + h * 0.36 ), ( x + w * 0.5, y + h * 0.36 ) ], fill=_INK )
    _text( d, ( x, y + h * 0.68, w, h * 0.3 ), [ "DANGER", "HIGH VOLTAGE" ], _INK )
    _plate( d, box( "arm" ), _YELLOW, None, _INK )
    x, y, w, h = box( "arm" )
    _trefoil( d, x + h * 0.55, y + h * 0.5, h * 0.36, _MAGENTA, _YELLOW )
    _text( d, ( x + h * 1.05, y, w - h * 1.1, h ), [ "AREA RADIATION MONITOR", "ARM-04" ], _INK, "left" )
    for name, words, bg, fg in ( ( "keep_clear", "KEEP CLEAR", _YELLOW, _INK ), ( "no_storage", "NO STORAGE", _YELLOW, _INK ),
                                 ( "walkway", "WALKWAY", _GREEN, _WHITE ) ):
        _plate( d, box( name ), bg, [ words ], fg )
    _plate( d, box( "control_plate" ), _BLUE, [ "FUEL POOL CONTROL ROOM", "AUTHORISED PERSONNEL ONLY" ], _WHITE )
    for name, label in ( ( "filter_b1", "B1" ), ( "filter_b2", "B2" ) ):
        x, y, w, h = box( name )
        _rect( d, ( x, y, w, h ), _WHITE )
        _rect( d, ( x, y, w * 0.24, h ), _RED )
        _text( d, ( x, y, w * 0.24, h ), [ label ], _WHITE )
        _text( d, ( x + w * 0.26, y, w * 0.74, h ), [ "FILTER ROOM", "RESTRICTED ENTRY" ], _INK, "left" )
    _plate( d, box( "hose_label" ), _RED, [ "FIRE HOSE REEL" ], _WHITE )
    x, y, w, h = box( "callpoint" )
    _rect( d, ( x, y, w, h ), _RED )
    _rect( d, _sub( ( x, y, w, h ), 0.18, 0.2, 0.64, 0.56 ), _WHITE )
    _text( d, _sub( ( x, y, w, h ), 0.18, 0.2, 0.64, 0.56 ), [ "FIRE" ], _RED )
    for name, lines in ( ( "tk201", [ "TK-201", "DEMIN WATER TANK" ] ), ( "tk202", [ "TK-202", "DEMIN WATER TANK" ] ),
                         ( "p201", [ "P-201", "TRANSFER PUMP" ] ), ( "db3", [ "DB-3", "400 V DISTRIBUTION" ] ),
                         ( "lcp", [ "LCP-07", "LOCAL CONTROL PANEL" ] ), ( "cam_tag", [ "CCTV", "RECORDING" ] ) ):
        x, y, w, h = box( name )
        _rect( d, ( x, y, w, h ), _WHITE )
        _rect( d, _sub( ( x, y, w, h ), 0.02, 0.05, 0.96, 0.9 ), None, _INK, max( 2, h * 0.04 ) )
        _text( d, ( x, y, w, h ), lines, _INK )
    for name, words, bg, fg in ( ( "pipe_demin", "DEMINERALISED WATER", _GREEN, _WHITE ),
                                 ( "pipe_cool", "SPENT FUEL POOL COOLING", _GREEN, _WHITE ),
                                 ( "pipe_air", "INSTRUMENT AIR", _BLUE, _WHITE ), ( "pipe_fire", "FIRE WATER", _RED, _WHITE ),
                                 ( "pipe_waste", "RADWASTE DRAIN", _YELLOW, _INK ), ( "pipe_hvac", "HVAC CHILLED WATER", _GREEN, _WHITE ),
                                 ( "pipe_n2", "NITROGEN", _BLUE, _WHITE ), ( "pipe_power", "ELECTRICAL", ( 210, 104, 26 ), _INK ) ):
        x, y, w, h = box( name )
        _rect( d, ( x, y, w, h ), bg )
        _text( d, ( x, y, w * 0.82, h ), [ words ], fg )
        d.polygon( [ ( x + w * 0.85, y + h * 0.25 ), ( x + w * 0.95, y + h * 0.5 ), ( x + w * 0.85, y + h * 0.75 ) ], fill=fg )
    x, y, w, h = box( "stations" )
    for k in range( 6 ):
        b = ( x + w * k / 6, y, w / 6, h )
        _rect( d, b, ( 26, 26, 28 ) )
        _rect( d, _sub( b, 0.05, 0.1, 0.9, 0.8 ), None, ( 120, 120, 120 ), 2 )
        _text( d, b, [ f"OP {k + 1}" ], _WHITE )
    x, y, w, h = box( "logo_plate" )
    _rect( d, ( x, y, w, h ), _WHITE )
    s = h * 0.8
    cx, base = x + h * 0.55, y + h * 0.5 + s * 0.38
    d.polygon( [ ( cx, base - s * 0.75 ), ( cx + s * 0.44, base ), ( cx - s * 0.44, base ) ], fill=_INK )
    d.polygon( [ ( cx - s * 0.12, base + 1 ), ( cx + s * 0.12, base + 1 ), ( cx, base - s * 0.26 ) ], fill=_WHITE )
    _text( d, ( x + h * 1.05, y, w - h * 1.1, h ), [ "RIVERDALE NUCLEAR", "FUEL HANDLING BUILDING" ], _INK, "left" )
    x, y, w, h = box( "pool_rules" )
    _rect( d, ( x, y, w, h ), _WHITE )
    _rect( d, ( x, y, w, h * 0.16 ), _BLUE )
    _text( d, ( x, y, w, h * 0.16 ), [ "SPENT FUEL POOL", "RULES" ], _WHITE )
    rules = [ "1  NO LOOSE ITEMS OVER THE POOL", "2  TETHER ALL TOOLS", "3  DOSIMETER AT ALL TIMES",
              "4  NO ENTRY PAST THE RAIL", "5  REPORT ANY DROPPED OBJECT", "6  CRANE MOVES: KEEP CLEAR" ]
    for k, line in enumerate( rules ):
        _text( d, ( x, y + h * ( 0.2 + 0.12 * k ), w, h * 0.1 ), [ line ], _INK, "left", pad=0.06 )
    for name in ( "whiteboard", "noticeboard" ):
        x, y, w, h = box( name )
        board = name == "whiteboard"
        _rect( d, ( x, y, w, h ), ( 120, 124, 128 ) )
        _rect( d, _sub( ( x, y, w, h ), 0.02, 0.04, 0.96, 0.92 ), ( 236, 238, 236 ) if board else ( 160, 118, 74 ) )
        if board:
            for k in range( 9 ):
                yy = y + h * ( 0.14 + 0.085 * k )
                col = ( ( 30, 60, 160 ), ( 170, 30, 30 ), ( 30, 30, 30 ) )[k % 3]
                pts = [ ( x + w * ( 0.06 + 0.04 * j ), yy + rng.normal( 0, h * 0.012 ) ) for j in range( int( rng.integers( 6, 20 ) ) ) ]
                d.line( pts, fill=col, width=max( 2, int( h * 0.012 ) ) )
            d.rectangle( ( x + w * 0.62, y + h * 0.18, x + w * 0.9, y + h * 0.5 ), outline=( 30, 60, 160 ), width=max( 2, int( h * 0.01 ) ) )
        else:
            for k in range( 7 ):
                px_, py_ = x + w * rng.uniform( 0.05, 0.75 ), y + h * rng.uniform( 0.08, 0.6 )
                pw, ph = w * rng.uniform( 0.12, 0.2 ), h * rng.uniform( 0.25, 0.35 )
                col = ( _WHITE, ( 244, 232, 120 ), ( 210, 230, 250 ) )[k % 3]
                _rect( d, ( px_, py_, pw, ph ), col )
                for j in range( 5 ):
                    d.line( ( px_ + pw * 0.1, py_ + ph * ( 0.2 + 0.14 * j ), px_ + pw * 0.85, py_ + ph * ( 0.2 + 0.14 * j ) ), fill=( 110, 110, 116 ), width=2 )
                _ellipse( d, px_ + pw * 0.5, py_ + ph * 0.06, h * 0.012, ( 200, 30, 30 ) )


def _draw_panels( d, dh, box, rng ):
    """ The equipment faces: keyboard, buttons, meters, annunciator, mimic, rack, panel door, vents, small things. """
    x, y, w, h = box( "keyboard" )
    _rect( d, ( x, y, w, h ), ( 34, 35, 38 ) )
    u = w / 23.5
    rows = [ [ 1 ] * 13 + [ 2 ], [ 1.5 ] + [ 1 ] * 12 + [ 1.5 ], [ 1.75 ] + [ 1 ] * 11 + [ 2.25 ], [ 2.25 ] + [ 1 ] * 10 + [ 2.75 ],
             [ 1.25, 1.25, 1.25, 6.25, 1.25, 1.25, 1.25, 1.25 ] ]
    rh = h * 0.86 / 6.2
    for j, row in enumerate( [ [ 1 ] + [ 0.5 ] + [ 1 ] * 4 + [ 0.5 ] + [ 1 ] * 4 + [ 0.5 ] + [ 1 ] * 4 ] + rows ):
        cx = x + u * 0.3
        cy = y + h * 0.06 + rh * j * 1.03 + ( rh * 0.25 if j else 0 )
        for k, kw in enumerate( row ):
            if j == 0 and kw == 0.5:
                cx += u * 0.5
                continue
            d.rounded_rectangle( ( cx + u * 0.06, cy, cx + kw * u - u * 0.06, cy + rh * 0.9 ), radius=u * 0.12, fill=( 58, 60, 64 ) )
            dh.rounded_rectangle( ( cx + u * 0.06, cy, cx + kw * u - u * 0.06, cy + rh * 0.9 ), radius=u * 0.12, fill=190 )
            _rect( d, ( cx + u * 0.25, cy + rh * 0.2, u * 0.18, rh * 0.16 ), ( 150, 152, 156 ) )
            cx += kw * u
    for j in range( 5 ):
        for k in range( 4 ):
            cx, cy = x + u * ( 19.2 + k ), y + h * 0.06 + rh * ( j + 1 ) * 1.03 + rh * 0.25
            d.rounded_rectangle( ( cx + u * 0.06, cy, cx + u * 0.94, cy + rh * 0.9 ), radius=u * 0.12, fill=( 58, 60, 64 ) )
            dh.rounded_rectangle( ( cx + u * 0.06, cy, cx + u * 0.94, cy + rh * 0.9 ), radius=u * 0.12, fill=190 )
    b = box( "buttons" )
    x, y, w, h = b
    _rect( d, b, ( 68, 72, 76 ) )
    colours = [ ( 196, 40, 30 ), ( 40, 170, 70 ), ( 232, 190, 40 ), ( 230, 230, 226 ), ( 30, 30, 32 ), ( 40, 90, 190 ) ]
    for j in range( 4 ):
        for i in range( 9 ):
            cx, cy, r = x + w * ( 0.06 + 0.083 * i ), y + h * ( 0.15 + 0.22 * j ), w * 0.022
            _ellipse( d, cx, cy, r * 1.4, ( 150, 152, 154 ) )
            _ellipse( dh, cx, cy, r * 1.4, 170 )
            if rng.random() < 0.18:
                _ellipse( d, cx, cy, r * 1.0, ( 36, 36, 38 ) )
                d.line( ( cx - r * 0.7, cy, cx + r * 0.7, cy ), fill=( 200, 200, 200 ), width=max( 2, int( r * 0.3 ) ) )
            else:
                _ellipse( d, cx, cy, r, colours[int( rng.integers( 0, len( colours ) ) )] )
                _ellipse( dh, cx, cy, r, 220 )
            _rect( d, ( cx - r * 1.5, cy + r * 1.8, r * 3.0, r * 0.9 ), ( 222, 222, 214 ) )
    cx, cy = x + w * 0.88, y + h * 0.5
    _ellipse( d, cx, cy, h * 0.2, _YELLOW )
    _ellipse( d, cx, cy, h * 0.13, ( 190, 30, 24 ) )
    _ellipse( dh, cx, cy, h * 0.13, 240 )
    b = box( "meters" )
    x, y, w, h = b
    _rect( d, b, ( 68, 72, 76 ) )
    for i in range( 6 ):
        mx = x + w * ( 0.04 + 0.1 * i )
        _rect( d, ( mx, y + h * 0.1, w * 0.07, h * 0.7 ), ( 236, 236, 230 ) )
        lvl = rng.uniform( 0.3, 0.85 )
        _rect( d, ( mx + w * 0.02, y + h * ( 0.1 + 0.7 * ( 1 - lvl ) ), w * 0.03, h * 0.7 * lvl ), ( ( 40, 150, 70 ), ( 40, 90, 190 ) )[i % 2] )
        for t in range( 9 ):
            d.line( ( mx + w * 0.055, y + h * ( 0.12 + 0.08 * t ), mx + w * 0.068, y + h * ( 0.12 + 0.08 * t ) ), fill=_INK, width=2 )
        _rect( d, ( mx, y + h * 0.84, w * 0.07, h * 0.08 ), ( 222, 222, 214 ) )
    for i, cx in enumerate( ( x + w * 0.72, x + w * 0.9 ) ):
        cy, r = y + h * 0.42, h * 0.3
        _ellipse( d, cx, cy, r * 1.08, ( 30, 30, 32 ) )
        _ellipse( d, cx, cy, r, ( 238, 238, 232 ) )
        for t in range( 11 ):
            a = math.radians( 225 - 27 * t )
            d.line( ( cx + math.cos( a ) * r * 0.78, cy - math.sin( a ) * r * 0.78, cx + math.cos( a ) * r * 0.92, cy - math.sin( a ) * r * 0.92 ),
                    fill=_INK, width=2 )
        a = math.radians( 225 - 270 * rng.uniform( 0.3, 0.7 ) )
        d.line( ( cx, cy, cx + math.cos( a ) * r * 0.8, cy - math.sin( a ) * r * 0.8 ), fill=( 200, 30, 20 ), width=max( 2, int( r * 0.05 ) ) )
        _rect( d, ( cx - r * 0.6, y + h * 0.8, r * 1.2, h * 0.1 ), ( 222, 222, 214 ) )
    b = box( "annunciator" )
    x, y, w, h = b
    _rect( d, b, ( 40, 42, 44 ) )
    words = [ "POOL LVL", "POOL TEMP", "PUMP TRIP", "FLOW LO", "HX OUT HI", "FILTER DP", "AREA RAD", "CRANE OVLD",
              "VENT FAIL", "DEMIN COND", "SKIM LVL", "GATE SEAL", "AIR PRESS", "FIRE ZONE", "DOOR OPEN", "POWER" ]
    for j in range( 4 ):
        for i in range( 8 ):
            t = ( x + w * ( 0.015 + 0.123 * i ), y + h * ( 0.04 + 0.24 * j ), w * 0.115, h * 0.21 )
            lit = rng.random()
            col = ( 214, 214, 206 ) if lit > 0.2 else ( ( 236, 170, 50 ) if lit > 0.08 else ( 220, 70, 50 ) )
            _rect( d, t, col )
            _text( d, t, words[( i + j * 8 ) % len( words )].split( " " ), _INK, pad=0.12 )
    b = box( "mimic" )
    x, y, w, h = b
    _rect( d, b, ( 196, 198, 192 ) )
    _rect( d, ( x, y, w, h * 0.1 ), ( 50, 58, 70 ) )
    _text( d, ( x, y, w, h * 0.1 ), [ "SPENT FUEL POOL COOLING AND PURIFICATION" ], _WHITE, track=0.1 )

    def P_( u, vv ):
        return ( x + w * u, y + h * ( 1 - vv ) )

    lw = max( 3, int( h * 0.014 ) )
    blue, green = ( 40, 90, 180 ), ( 30, 130, 70 )
    for path, col in ( ( [ ( 0.25, 0.6 ), ( 0.86, 0.6 ) ], blue ), ( [ ( 0.25, 0.35 ), ( 0.86, 0.35 ) ], green ),
                       ( [ ( 0.86, 0.6 ), ( 0.92, 0.6 ), ( 0.92, 0.85 ), ( 0.2, 0.85 ), ( 0.2, 0.7 ) ], blue ),
                       ( [ ( 0.86, 0.35 ), ( 0.92, 0.35 ), ( 0.92, 0.18 ), ( 0.15, 0.18 ), ( 0.15, 0.2 ) ], green ),
                       ( [ ( 0.47, 0.6 ), ( 0.47, 0.35 ) ], _INK ) ):
        d.line( [ P_( *p ) for p in path ], fill=col, width=lw, joint="curve" )
    px0, py0 = P_( 0.05, 0.7 )
    px1, py1 = P_( 0.25, 0.2 )
    _rect( d, ( px0, py0, px1 - px0, py1 - py0 ), ( 120, 170, 210 ) )
    for k in range( 6 ):
        d.line( ( px0 + ( px1 - px0 ) * ( 0.1 + 0.16 * k ), py0 + ( py1 - py0 ) * 0.45, px0 + ( px1 - px0 ) * ( 0.1 + 0.16 * k ), py1 ), fill=( 60, 90, 120 ), width=lw )
    _rect( d, ( px0, py0, px1 - px0, py1 - py0 ), None, _INK, lw )
    for u, vv, kind, label in ( ( 0.38, 0.6, "pump", "P-1" ), ( 0.38, 0.35, "pump", "P-2" ), ( 0.55, 0.6, "hx", "HX-1" ),
                                ( 0.55, 0.35, "hx", "HX-2" ), ( 0.7, 0.6, "filter", "F-1" ), ( 0.7, 0.35, "filter", "D-1" ),
                                ( 0.86, 0.6, "tank", "TK-201" ), ( 0.86, 0.35, "tank", "TK-202" ), ( 0.3, 0.6, "valve", "V1" ),
                                ( 0.3, 0.35, "valve", "V2" ), ( 0.63, 0.6, "valve", "V3" ), ( 0.63, 0.35, "valve", "V4" ) ):
        cx, cy = P_( u, vv )
        r = h * 0.06
        if kind == "pump":
            _ellipse( d, cx, cy, r, ( 230, 230, 226 ), _INK, lw )
            d.polygon( [ ( cx - r * 0.5, cy - r * 0.6 ), ( cx + r * 0.7, cy ), ( cx - r * 0.5, cy + r * 0.6 ) ], fill=_INK )
        elif kind == "hx":
            _ellipse( d, cx, cy, r, ( 230, 230, 226 ), _INK, lw )
            d.line( ( cx - r * 0.8, cy, cx - r * 0.4, cy - r * 0.5, cx, cy + r * 0.5, cx + r * 0.4, cy - r * 0.5, cx + r * 0.8, cy ), fill=_INK, width=lw )
        elif kind == "filter":
            _rect( d, ( cx - r * 0.7, cy - r * 1.1, r * 1.4, r * 2.2 ), ( 230, 230, 226 ), _INK, lw )
            d.line( ( cx - r * 0.7, cy - r * 1.1, cx + r * 0.7, cy + r * 1.1 ), fill=_INK, width=lw )
        elif kind == "tank":
            d.rounded_rectangle( ( cx - r * 0.8, cy - r * 1.4, cx + r * 0.8, cy + r * 1.4 ), radius=r * 0.6, fill=( 230, 230, 226 ), outline=_INK, width=lw )
        else:
            d.polygon( [ ( cx - r * 0.6, cy - r * 0.45 ), ( cx + r * 0.6, cy + r * 0.45 ), ( cx + r * 0.6, cy - r * 0.45 ), ( cx - r * 0.6, cy + r * 0.45 ) ], fill=_INK )
        _text( d, ( cx - r * 1.6, cy + r * 1.2, r * 3.2, r * 0.9 ), [ label ], _INK )
    for u, vv, _ in MIMIC_LAMPS:
        cx, cy = P_( u, vv )
        _ellipse( d, cx, cy, h * 0.022, ( 40, 40, 40 ) )
        _ellipse( dh, cx, cy, h * 0.022, 200 )
    b = box( "rack" )
    x, y, w, h = b
    _rect( d, b, ( 46, 48, 52 ) )
    for j in range( int( h / 6 ) ):
        for i in range( int( w / 6 ) ):
            if 0.08 < i * 6 / w < 0.92 and 0.1 < j * 6 / h < 0.86:
                _ellipse( d, x + i * 6 + 3, y + j * 6 + 3, 1.6, ( 18, 18, 20 ) )
    _rect( d, ( x + w * 0.86, y + h * 0.42, w * 0.05, h * 0.14 ), ( 160, 162, 166 ) )
    for k in range( 6 ):
        _ellipse( d, x + w * ( 0.15 + 0.08 * k ), y + h * 0.06, w * 0.015, ( ( 60, 220, 90 ), ( 240, 170, 40 ) )[k % 4 == 3] )
    _rect( d, ( x + w * 0.1, y + h * 0.9, w * 0.5, h * 0.05 ), _WHITE )
    b = box( "panel_door" )
    x, y, w, h = b
    _rect( d, b, ( 196, 196, 188 ) )
    _rect( d, _sub( b, 0.03, 0.02, 0.94, 0.96 ), None, ( 150, 150, 144 ), 3 )
    _rect( d, ( x + w * 0.25, y + h * 0.06, w * 0.5, h * 0.08 ), _WHITE )
    _text( d, ( x + w * 0.25, y + h * 0.06, w * 0.5, h * 0.08 ), [ "DB-3" ], _INK )
    d.polygon( [ ( x + w * 0.5, y + h * 0.2 ), ( x + w * 0.62, y + h * 0.36 ), ( x + w * 0.38, y + h * 0.36 ) ], fill=_YELLOW, outline=_INK )
    _rect( d, ( x + w * 0.84, y + h * 0.45, w * 0.06, h * 0.1 ), ( 40, 40, 42 ) )
    for fy in ( 0.12, 0.84 ):
        _rect( d, ( x + w * 0.02, y + h * fy, w * 0.04, h * 0.06 ), ( 110, 110, 108 ) )
    for name in ( "vent", "grille" ):
        b = box( name )
        x, y, w, h = b
        _rect( d, b, ( 110, 112, 114 ) if name == "vent" else ( 190, 190, 184 ) )
        count = 10 if name == "vent" else 16
        for k in range( count ):
            yy = y + h * ( 0.1 + 0.8 * k / count )
            _rect( d, ( x + w * 0.06, yy, w * 0.88, h * 0.8 / count * 0.55 ), ( 26, 26, 28 ) )
            _rect( dh, ( x + w * 0.06, yy, w * 0.88, h * 0.8 / count * 0.55 ), 60 )
    b = box( "drain" )
    x, y, w, h = b
    _rect( d, b, ( 150, 152, 154 ) )
    for k in range( 9 ):
        _rect( d, ( x + w * ( 0.1 + 0.09 * k ), y + h * 0.1, w * 0.05, h * 0.8 ), ( 18, 18, 20 ) )
        _rect( dh, ( x + w * ( 0.1 + 0.09 * k ), y + h * 0.1, w * 0.05, h * 0.8 ), 40 )
    b = box( "clock" )
    x, y, w, h = b
    _rect( d, b, ( 30, 30, 32 ) )
    cx, cy, r = x + w / 2, y + h / 2, w * 0.46
    _ellipse( d, cx, cy, r, ( 240, 240, 236 ) )
    for t in range( 60 ):
        a = 2 * math.pi * t / 60
        r0 = r * ( 0.8 if t % 5 == 0 else 0.88 )
        d.line( ( cx + math.sin( a ) * r0, cy - math.cos( a ) * r0, cx + math.sin( a ) * r * 0.94, cy - math.cos( a ) * r * 0.94 ), fill=_INK, width=3 if t % 5 == 0 else 1 )
    for a, L, wd in ( ( math.radians( 310 ), 0.5, 5 ), ( math.radians( 62 ), 0.75, 3 ) ):
        d.line( ( cx, cy, cx + math.sin( a ) * r * L, cy - math.cos( a ) * r * L ), fill=_INK, width=wd )
    d.line( ( cx, cy, cx + math.sin( 2.2 ) * r * 0.8, cy - math.cos( 2.2 ) * r * 0.8 ), fill=( 200, 30, 20 ), width=2 )
    b = box( "diffuser" )
    x, y, w, h = b
    _rect( d, b, ( 232, 232, 228 ) )
    for k in range( 5 ):
        f = 0.08 + 0.08 * k
        _rect( d, _sub( b, f, f, 1 - 2 * f, 1 - 2 * f ), None, ( 160, 160, 156 ) if k % 2 else ( 120, 120, 118 ), 3 )
    _rect( d, _sub( b, 0.46, 0.46, 0.08, 0.08 ), ( 60, 60, 60 ) )
    b = box( "speaker" )
    x, y, w, h = b
    _rect( d, b, ( 232, 232, 228 ) )
    _ellipse( d, x + w / 2, y + h / 2, w * 0.44, ( 214, 214, 210 ) )
    for j in range( 15 ):
        for i in range( 15 ):
            if ( i - 7 ) ** 2 + ( j - 7 ) ** 2 < 42:
                _ellipse( d, x + w * ( 0.5 + ( i - 7 ) * 0.055 ), y + h * ( 0.5 + ( j - 7 ) * 0.055 ), w * 0.014, ( 60, 60, 62 ) )
    b = box( "camera" )
    x, y, w, h = b
    _rect( d, b, ( 210, 210, 206 ) )
    for r, col in ( ( 0.4, ( 30, 30, 32 ) ), ( 0.3, ( 60, 62, 70 ) ), ( 0.2, ( 14, 16, 24 ) ), ( 0.07, ( 120, 140, 180 ) ) ):
        _ellipse( d, x + w * 0.5, y + h * 0.5, w * r, col )
    b = box( "papers" )
    x, y, w, h = b
    _rect( d, b, ( 236, 234, 226 ) )
    _rect( d, ( x + w * 0.1, y + h * 0.08, w * 0.5, h * 0.06 ), ( 40, 60, 120 ) )
    for k in range( 16 ):
        d.line( ( x + w * 0.1, y + h * ( 0.2 + 0.045 * k ), x + w * ( 0.9 if k % 4 else 0.5 ), y + h * ( 0.2 + 0.045 * k ) ), fill=( 110, 110, 116 ), width=2 )
    b = box( "binders" )
    x, y, w, h = b
    cols = [ ( 30, 60, 140 ), ( 160, 30, 30 ), ( 30, 30, 34 ), ( 210, 170, 30 ), ( 30, 110, 60 ), ( 120, 120, 124 ) ]
    for k in range( 11 ):
        bx = x + w * k / 11
        _rect( d, ( bx, y, w / 11 - 2, h ), cols[int( rng.integers( 0, len( cols ) ) )] )
        _rect( d, ( bx + w * 0.012, y + h * 0.12, w / 11 - w * 0.03, h * 0.28 ), _WHITE )
        _ellipse( d, bx + w / 22, y + h * 0.8, w * 0.012, ( 20, 20, 20 ) )
    b = box( "phone" )
    x, y, w, h = b
    _rect( d, b, ( 120, 122, 124 ) )
    _rect( d, _sub( b, 0.1, 0.06, 0.8, 0.22 ), ( 40, 52, 46 ) )
    for j in range( 4 ):
        for i in range( 3 ):
            _rect( d, ( x + w * ( 0.16 + 0.24 * i ), y + h * ( 0.36 + 0.15 * j ), w * 0.18, h * 0.1 ), ( 60, 60, 62 ) )


def sign_atlas():
    """ The rv_hall_signs atlas: colour (linear), roughness, height (in), pixels to the inch (as if a 64 in tile). """
    W, H = RM.px( SIGN_ATLAS[0] ), RM.px( SIGN_ATLAS[1] )
    k = W / SIGN_ATLAS[0]
    img = Image.new( "RGB", ( W, H ), ( 72, 74, 76 ) )
    hgt = Image.new( "L", ( W, H ), 128 )
    d, dh = ImageDraw.Draw( img ), ImageDraw.Draw( hgt )
    rng = np.random.default_rng( 17 )

    def box( name ):
        x, y, w, h = SIGNS[name]
        return ( x * k, y * k, w * k, h * k )

    _draw_signs( d, box, rng )
    _draw_panels( d, dh, box, rng )
    srgb = np.asarray( img, np.float32 )
    colour = RM.T.srgb_to_linear( srgb ).astype( np.float32 )
    lum = srgb.mean( axis=-1 ) / 255.0
    rough = np.clip( 0.62 - 0.22 * lum, 0.3, 0.8 ).astype( np.float32 )
    height = ( np.asarray( hgt, np.float32 ) - 128.0 ) / 128.0 * 0.06
    return colour, rough, height, W / 64.0


EXTRA_SURFACES = {
    "rv_hall_epoxy": ( 96.0, 0.0, lambda: epoxy() ),
    "rv_hall_ceiling": ( 48.0, 0.0, lambda: ceiling_tiles() ),
    "rv_hall_access": ( 48.0, 0.0, lambda: access_floor() ),
    "rv_hall_deck": ( 48.0, 0.6, lambda: roof_deck() ),
    "rv_hall_interior": ( 96.0, 0.0, lambda: interior_paint() ),
    "rv_hall_roof": ( 192.0, 0.0, lambda: roof_membrane() ),
    "rv_hall_signs": ( 64.0, 0.0, lambda: sign_atlas() ),
}


# ---------------------------------------------------------------------------------------------------------------------
# Shapes

def unit( a ):
    return P.unit( a )


def axes_along( x, hint=UP ):
    """ A right-handed frame ( x, y, z ): x along x, z as near hint as it can be, y level where it can be. """
    x = unit( np.asarray( x, float ) )
    hint = np.asarray( hint, float )
    z = hint - np.dot( hint, x ) * x
    if np.linalg.norm( z ) < 1e-6:
        z = np.array( ( 1.0, 0.0, 0.0 ) ) - x[0] * x
        if np.linalg.norm( z ) < 1e-6:
            z = np.array( ( 0.0, 1.0, 0.0 ) ) - x[1] * x
    z = unit( z )
    return x, np.cross( z, x ), z


def bar( m, a, b, w, h, paint, hint=UP ):
    """ A rectangular member from a to b: w across (level where it can be), h toward hint. """
    a, b = v( *a ), v( *b )
    L = float( np.linalg.norm( b - a ) )
    if L < 1e-6:
        return
    x, y, z = axes_along( b - a, hint )
    m.oriented_box( ( a + b ) / 2, ( x, y, z ), ( L, w, h ), paint )


def wide_flange( m, a, b, depth, width, paint, web=0.5, flange=0.75, hint=UP ):
    """ An I-section from a to b, depth toward hint, its flanges width wide. """
    a, b = v( *a ), v( *b )
    L = float( np.linalg.norm( b - a ) )
    if L < 1e-6:
        return
    x, y, z = axes_along( b - a, hint )
    mid = ( a + b ) / 2
    m.oriented_box( mid, ( x, y, z ), ( L, web, depth - 2 * flange ), paint )
    for s in ( -1, 1 ):
        m.oriented_box( mid + z * s * ( depth - flange ) / 2, ( x, y, z ), ( L, width, flange ), paint )


def channel( m, a, b, depth, width, paint, t=0.4, hint=UP, opens=None ):
    """ A C-section from a to b: its web depth toward hint, its flanges width wide toward opens (else its own y). """
    a, b = v( *a ), v( *b )
    L = float( np.linalg.norm( b - a ) )
    if L < 1e-6:
        return
    x, y, z = axes_along( b - a, hint )
    s = 1.0 if opens is None or np.dot( opens, y ) >= 0 else -1.0
    mid = ( a + b ) / 2
    m.oriented_box( mid, ( x, y, z ), ( L, t, depth ), paint )
    for sz in ( -1, 1 ):
        m.oriented_box( mid + y * s * width / 2 + z * sz * ( depth - t ) / 2, ( x, y, z ), ( L, width, t ), paint )


def angle_iron( m, a, b, leg, paint, p, q, t=0.4 ):
    """ An angle from a to b, its corner on the line, its legs leg long toward p and q. """
    a, b = v( *a ), v( *b )
    L = float( np.linalg.norm( b - a ) )
    if L < 1e-6:
        return
    x = unit( b - a )
    mid = ( a + b ) / 2
    p, q = unit( v( *p ) ), unit( v( *q ) )
    for d1, d2 in ( ( p, q ), ( q, p ) ):
        m.oriented_box( mid + d1 * leg / 2 + d2 * t / 2, ( x, d1, np.cross( x, d1 ) ), ( L, leg, t ), paint )


def lathe_on( m, c, axis, profile, paints, sides=16, cap0=None, cap1=None ):
    """ A round thing turned about axis through c: profile [ ( radius, distance along axis ) ], paints one or per band;
    cap0 / cap1 close its first / last ring. """
    c, axis = v( *c ), unit( v( *axis ) )
    u, w = P.perp( axis )
    dirs = [ u * math.cos( 2 * math.pi * k / sides ) + w * math.sin( 2 * math.pi * k / sides ) for k in range( sides ) ]
    for j in range( len( profile ) - 1 ):
        paint = paints[j] if isinstance( paints, ( list, tuple ) ) else paints
        if paint is None:
            continue
        ( r0, t0 ), ( r1, t1 ) = profile[j], profile[j + 1]
        if r0 < 1e-6 and r1 < 1e-6:
            continue
        sl = unit( v( t1 - t0, r0 - r1 ) )
        for k in range( sides ):
            k1 = ( k + 1 ) % sides
            pts = [ c + axis * t0 + dirs[k] * r0, c + axis * t0 + dirs[k1] * r0, c + axis * t1 + dirs[k1] * r1, c + axis * t1 + dirs[k] * r1 ]
            nrm = [ dirs[i] * sl[0] + axis * sl[1] for i in ( k, k1, k1, k ) ]
            if r0 < 1e-6:
                pts, nrm = pts[1:], nrm[1:]
            elif r1 < 1e-6:
                pts, nrm = pts[:3], nrm[:3]
            card( m, paint, pts, sum( nrm ), normals=nrm )
    if cap0 and profile[0][0] > 1e-6:
        r, t = profile[0]
        card( m, cap0, [ c + axis * t + dd * r for dd in dirs ], -axis )
    if cap1 and profile[-1][0] > 1e-6:
        r, t = profile[-1]
        card( m, cap1, [ c + axis * t + dd * r for dd in dirs ], axis )


def disc( m, paint, c, normal, r, sides=16 ):
    c, n = v( *c ), unit( v( *normal ) )
    u, w = P.perp( n )
    card( m, paint, [ c + ( u * math.cos( 2 * math.pi * k / sides ) + w * math.sin( 2 * math.pi * k / sides ) ) * r
                      for k in range( sides ) ], n )


def hoop( m, c, normal, R, r, paint, segs=12, sides=5 ):
    c, n = v( *c ), unit( v( *normal ) )
    u, w = P.perp( n )
    pts = [ c + ( u * math.cos( 2 * math.pi * k / segs ) + w * math.sin( 2 * math.pi * k / segs ) ) * R for k in range( segs ) ]
    for k in range( segs ):
        P.rod( m, pts[k], pts[( k + 1 ) % segs], r, paint, sides )


def handwheel( m, c, axis, R=5.0, paint="rv_hall_red" ):
    """ A valve's handwheel: the rim, three spokes, the hub. """
    c, a = v( *c ), unit( v( *axis ) )
    hoop( m, c, a, R, 0.45, paint, 12, 4 )
    u, w = P.perp( a )
    for k in range( 3 ):
        P.rod( m, c, c + ( u * math.cos( 2 * math.pi * k / 3 ) + w * math.sin( 2 * math.pi * k / 3 ) ) * R, 0.3, paint, 4 )
    P.rod( m, c - a * 0.8, c + a * 0.8, 0.9, paint, 6, caps=True )


def valve( d, fine, c, along, R=5.5, paint="rv_hall_blue", wheel="rv_hall_red" ):
    """ A gate valve on a pipe running along: its body and flanges, the bonnet, the stem and handwheel. """
    c, along = v( *c ), unit( v( *along ) )
    lathe_on( d, c - along * 6, along, [ ( 5.0, 0 ), ( 5.0, 1.2 ), ( 4.2, 1.2 ), ( 5.6, 3.5 ), ( 5.6, 8.5 ), ( 4.2, 10.8 ),
                                         ( 5.0, 10.8 ), ( 5.0, 12 ) ], paint, 12, cap0=paint, cap1=paint )
    P.rod( d, c, c + UP * 13, 2.3, paint, 8, caps=True )
    P.rod( fine, c + UP * 13, c + UP * 18, 0.5, "rv_hall_chrome", 5 )
    handwheel( fine, c + UP * 17, UP, R, wheel )


def atlas_uv( name, s0=0.0, t0=0.0, s1=1.0, t1=1.0 ):
    return [ RM.atlas_uv( SIGNS, SIGN_ATLAS, name, s, t ) for s, t in ( ( s0, t0 ), ( s1, t0 ), ( s1, t1 ), ( s0, t1 ) ) ]


def screen_uv( name ):
    return [ RM.atlas_uv( RM.SCREENS, RM.SCREEN_ATLAS, name, s, t ) for s, t in ( ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ) ]


def sign_w( name, h ):
    return h * RM.aspect( SIGNS, name )


def top_quad( m, paint, centre, up_dir, w, h, uv=None ):
    """ A level quad facing up, its picture's up along up_dir (plan). """
    up_dir = unit( v( up_dir[0], up_dir[1], 0.0 ) )
    P.quad( m, paint, centre, np.cross( up_dir, UP ), up_dir, w, h, uv )


class Face:
    """ A wall's face in plan: s runs along it to the right as you face it, z up, d out from it. """

    def __init__( self, point, out ):
        self.out = unit( v( out[0], out[1], 0.0 ) )
        self.a = np.cross( UP, self.out )
        self.o = v( point[0], point[1], 0.0 )

    def p( self, s, z, d=0.0 ):
        return self.o + self.a * s + UP * z + self.out * d

    def s_of( self, e, n ):
        return float( np.dot( v( e, n, 0.0 ) - self.o, self.a ) )

    def ss( self, pa, pb ):
        return tuple( sorted( ( self.s_of( *pa ), self.s_of( *pb ) ) ) )

    def quad( self, m, paint, s0, s1, z0, z1, d=0.25, uv=None ):
        if s1 < s0:
            s0, s1 = s1, s0
        if s1 - s0 < 1e-6 or z1 - z0 < 1e-6:
            return
        card( m, paint, [ self.p( s0, z0, d ), self.p( s1, z0, d ), self.p( s1, z1, d ), self.p( s0, z1, d ) ], self.out, uv=uv )

    def box( self, m, s0, s1, z0, z1, d0, d1, paint, front=None, back=False ):
        """ A box standing off the face from d0 to d1: its front face front's paint, its back left out. """
        if s1 < s0:
            s0, s1 = s1, s0
        if s1 - s0 < 1e-6 or z1 - z0 < 1e-6 or d1 - d0 < 1e-6:
            return
        centre = self.p( ( s0 + s1 ) / 2, ( z0 + z1 ) / 2, ( d0 + d1 ) / 2 )
        paints = { "default": paint, "-y": front or paint, "+y": paint if back else None }
        m.oriented_box( centre, ( self.a, -self.out, UP ), ( s1 - s0, d1 - d0, z1 - z0 ), paints )


def sign_on( m, face, name, s, z, h, d=0.35 ):
    """ A sign from the atlas on a face, centred at s, z, h tall. """
    w = sign_w( name, h )
    face.quad( m, "rv_hall_signs", s - w / 2, s + w / 2, z - h / 2, z + h / 2, d, atlas_uv( name ) )


def extrude( m, paint, section, a0, a1, axis="n" ):
    """ A prism of the convex section [ ( across, z ) ] running along axis ('n' or 'e') from a0 to a1. """
    def pt( u, a, z ):
        return v( u, a, z ) if axis == "n" else v( a, u, z )

    ax = v( 0, 1, 0 ) if axis == "n" else v( 1, 0, 0 )
    cu, cz = np.mean( [ p[0] for p in section ] ), np.mean( [ p[1] for p in section ] )
    centre = pt( cu, ( a0 + a1 ) / 2, cz )
    card( m, paint, [ pt( u, a0, z ) for u, z in section ], -ax )
    card( m, paint, [ pt( u, a1, z ) for u, z in section ], ax )
    for k in range( len( section ) ):
        ( ua, za ), ( ub, zb ) = section[k], section[( k + 1 ) % len( section )]
        pts = [ pt( ua, a0, za ), pt( ub, a0, zb ), pt( ub, a1, zb ), pt( ua, a1, za ) ]
        card( m, paint, pts, sum( pts ) / 4 - centre )


def door_frame( m, face, s0, s1, top, w=3.0, d=1.2, paint="rv_frame", z0=0.0 ):
    """ A steel frame round an opening in a face: jambs and a head, standing d proud. """
    face.box( m, s0 - w, s0, z0, top + w, 0, d, paint )
    face.box( m, s1, s1 + w, z0, top + w, 0, d, paint )
    face.box( m, s0, s1, top, top + w, 0, d, paint )


def indoor():
    """ The hall's concrete indoors: riverdale_materials' rv_wall_clean (no weather) where it has one, else rv_wall. """
    return "rv_wall_clean" if "rv_wall_clean" in RM.SURFACES else "rv_wall"


# ---------------------------------------------------------------------------------------------------------------------
# What a plant keeps on its walls

def extinguisher( d, fine, face, s, z=30.0 ):
    """ A 9 kg extinguisher on its wall bracket (z its foot), its hose, its sign above. """
    c = face.p( s, 0, 4.2 )
    P.lathe( d, c, [ ( 3.3, z ), ( 3.6, z + 0.8 ), ( 3.6, z + 16.5 ), ( 3.0, z + 18.6 ), ( 1.3, z + 19.8 ), ( 1.0, z + 20.6 ) ],
             "rv_hall_red", 12 )
    head = face.p( s, z + 21.6, 4.2 )
    P.obox( fine, head, face.a, ( 2.4, 2.0, 2.0 ), "rv_dark" )
    bar( fine, head + UP * 1.2 - face.a * 0.6, head + UP * 1.7 + face.a * 3.5, 0.9, 0.35, "rv_dark" )
    P.pipe( fine, [ head + face.a * 1.2, head + face.a * 3.4 - UP * 1.5, face.p( s + 3.9, z + 11, 4.2 ) ], 0.45, "rv_black", 5, caps=False )
    face.box( fine, s - 1.6, s + 1.6, z + 10, z + 15, 0, 0.9, "rv_dark" )
    sign_on( fine, face, "fire_ext", s, z + 34, 10 )


def wall_panel( d, fine, face, s, z0, w=30.0, h=48.0, dep=7.0, tag="db3", door="panel_door", tray=None ):
    """ An enclosure on the wall: its door, its tag above, conduits up to a tray ( z, d ) if there is one. """
    face.box( d, s - w / 2, s + w / 2, z0, z0 + h, 0, dep, "rv_hall_equipment" )
    face.quad( fine, "rv_hall_signs", s - w / 2 + 0.6, s + w / 2 - 0.6, z0 + 0.6, z0 + h - 0.6, dep + 0.05, atlas_uv( door ) )
    sign_on( fine, face, tag, s, z0 + h + 2.6, 3.4 )
    if tray:
        tz, td = tray
        for k in ( -1, 0, 1 ):
            x = s + k * w * 0.3
            P.pipe( fine, [ face.p( x, z0 + h, dep * 0.5 ), face.p( x, z0 + h + 3, 1.4 ), face.p( x, tz - 4, 1.4 ), face.p( x, tz - 1.5, td ) ],
                    0.7, "rv_galv", 6, caps=False )


def radiation_monitor( d, fine, face, s, z ):
    """ An area radiation monitor: its box, display and lamps, an amber beacon on top, its label under. """
    face.box( d, s - 7, s + 7, z, z + 10, 0, 5, "rv_hall_equipment" )
    face.quad( fine, "rv_screens", s - 5.5, s + 1.5, z + 3.5, z + 8, 5.05, screen_uv( "table" ) )
    face.quad( fine, "rv_hall_led_green", s + 3, s + 4.6, z + 6.6, z + 8.2, 5.05 )
    face.quad( fine, "rv_hall_led_amber", s + 3, s + 4.6, z + 3.8, z + 5.4, 5.05 )
    c = face.p( s + 4, 0, 2.5 )
    P.cylinder( fine, c, 1.4, z + 10, z + 13, "rv_hall_led_amber", 8, top="rv_hall_led_amber" )
    sign_on( fine, face, "arm", s, z - 3.2, 4.4 )


def eyewash( d, fine, face, s, z=0.0 ):
    """ A wall-mounted eye wash: its green supply up the wall, the bowl and its two heads, the push plate, its sign. """
    zb = z + 36
    P.pipe( fine, [ face.p( s, z + 6, 1.2 ), face.p( s, zb - 5, 1.2 ), face.p( s, zb - 2, 6.5 ) ], 0.9, "rv_hall_green", 8, caps=False )
    c = face.p( s, 0, 6.5 )
    P.lathe( d, c, [ ( 1.2, zb - 2.5 ), ( 4.8, zb - 0.8 ), ( 5.8, zb + 1.0 ) ], "rv_hall_green", 14, cap="rv_stainless" )
    for k in ( -1, 1 ):
        P.cylinder( fine, c + face.a * 2.2 * k, 0.7, zb + 1.0, zb + 2.6, "rv_hall_chrome", 8, top="rv_hall_chrome" )
    face.box( fine, s + 4.5, s + 7.5, zb - 4, zb + 2, 0.5, 9.5, "rv_hall_green" )
    sign_on( fine, face, "eyewash", s, zb + 20, 12 )


def hose_cabinet( d, fine, face, s, z=30.0 ):
    """ A fire hose reel cabinet set into the wall: a red frame, a glazed door, its label. """
    w, h = 30.0, 32.0
    face.box( d, s - w / 2 - 1.5, s + w / 2 + 1.5, z - 1.5, z + h + 1.5, 0, 1.4, "rv_hall_red" )
    face.quad( fine, "rv_window_dark", s - w / 2 + 1, s + w / 2 - 1, z + 7, z + h - 1, 1.45 )
    face.quad( fine, "rv_hall_signs", s - w / 2 + 1, s + w / 2 - 1, z + 1, z + 6.5, 1.45, atlas_uv( "hose_label" ) )
    face.box( fine, s + w / 2 - 3.5, s + w / 2 - 2.5, z + h / 2 - 3, z + h / 2 + 3, 1.4, 2.4, "rv_hall_chrome" )


def call_point( fine, face, s, z ):
    face.box( fine, s - 2.4, s + 2.4, z - 2.4, z + 2.4, 0, 2.0, "rv_hall_red" )
    face.quad( fine, "rv_hall_signs", s - 2.2, s + 2.2, z - 2.2, z + 2.2, 2.05, atlas_uv( "callpoint" ) )


def wall_phone( d, fine, face, s, z ):
    """ A yellow industrial phone: its box, handset and cord, keypad, and a red lamp that flashes when it rings. """
    face.box( d, s - 4.5, s + 4.5, z - 7, z + 7, 0, 4.5, "rv_door_yellow" )
    bar( fine, face.p( s - 2.6, z - 5.5, 5.3 ), face.p( s - 2.6, z + 5.5, 5.3 ), 1.6, 1.5, "rv_hall_plastic", hint=face.out )
    face.quad( fine, "rv_hall_signs", s + 0.6, s + 3.8, z - 4, z + 1.8, 4.55, atlas_uv( "phone" ) )
    P.pipe( fine, [ face.p( s - 2.6, z - 5.5, 5.0 ), face.p( s - 1.0, z - 9.5, 4.6 ), face.p( s + 1.5, z - 7.5, 4.5 ) ], 0.25, "rv_hall_plastic", 4, caps=False )
    P.cylinder( fine, face.p( s, 0, 2.2 ), 1.3, z + 7, z + 9.5, "rv_hall_led_red", 8, top="rv_hall_led_red" )


def first_aid( d, fine, face, s, z ):
    face.box( d, s - 7, s + 7, z, z + 17, 0, 5, "rv_hall_green" )
    face.quad( fine, "rv_hall_signs", s - 6.4, s + 6.4, z + 0.6, z + 16.4, 5.05, atlas_uv( "first_aid" ) )


def notice_board( d, fine, face, s, z, w=36.0, h=24.0, kind="noticeboard" ):
    face.box( d, s - w / 2, s + w / 2, z, z + h, 0, 1.2, "rv_frame" )
    face.quad( fine, "rv_hall_signs", s - w / 2 + 0.8, s + w / 2 - 0.8, z + 0.8, z + h - 0.8, 1.25, atlas_uv( kind ) )


def camera( d, fine, face, s, z, target ):
    """ A CCTV camera on an arm off the wall, looking at target: its housing and sunshield, its lens. """
    face.box( fine, s - 2.2, s + 2.2, z - 3, z + 3, 0, 0.8, "rv_hall_equipment" )
    end = face.p( s, z, 10 )
    bar( fine, face.p( s, z, 0.8 ), end, 1.4, 1.4, "rv_hall_equipment" )
    look = unit( v( *target ) - end )
    x, y, zz = axes_along( look, UP )
    centre = end - UP * 3.2 + x * 2.5
    bar( fine, end, end - UP * 1.4, 1.2, 1.2, "rv_hall_equipment" )
    d.oriented_box( centre, ( x, y, zz ), ( 10, 4.4, 4.4 ), "rv_hall_equipment" )
    d.oriented_box( centre + zz * 2.6 + x * 1.2, ( x, y, zz ), ( 12.5, 5.6, 0.4 ), "rv_hall_equipment" )
    P.quad( fine, "rv_hall_signs", centre + x * 5.05, y, zz, 4.0, 4.0, atlas_uv( "camera" ) )


def horn( d, fine, face, s, z, target ):
    """ A horn loudspeaker on a bracket, aimed at target. """
    face.box( fine, s - 1.5, s + 1.5, z - 2.5, z + 2.5, 0, 0.8, "rv_hall_equipment" )
    end = face.p( s, z, 6 )
    bar( fine, face.p( s, z, 0.8 ), end, 1.2, 1.2, "rv_hall_equipment" )
    look = unit( v( *target ) - end )
    lathe_on( d, end, look, [ ( 2.4, -2 ), ( 2.4, 0.5 ), ( 1.3, 1.5 ), ( 2.2, 5 ), ( 4.6, 8.5 ), ( 5.2, 9.2 ) ], "rv_hall_equipment", 12,
              cap0="rv_hall_equipment", cap1="rv_dark" )


def exit_sign( d, fine, face, s, z, w=16.0, d0=0.0 ):
    """ An exit sign: its white box, the green sign (rv_plates' exit) and its lit edges. """
    h = w * 192.0 / 512.0
    face.box( d, s - w / 2 - 0.6, s + w / 2 + 0.6, z - h / 2 - 0.6, z + h / 2 + 0.6, d0, d0 + 3.0, "rv_hall_equipment" )
    P.plate( fine, "exit", face.p( s, z, d0 + 3.0 ), face.a, h, off=0.05 )
    card( fine, "rv_hall_exit", [ face.p( s - w / 2, z - h / 2 - 0.65, d0 + 0.4 ), face.p( s + w / 2, z - h / 2 - 0.65, d0 + 0.4 ),
                                  face.p( s + w / 2, z - h / 2 - 0.65, d0 + 2.6 ), face.p( s - w / 2, z - h / 2 - 0.65, d0 + 2.6 ) ], -UP )
    for k in ( -1, 1 ):
        face.quad( fine, "rv_hall_exit", s + k * ( w / 2 + 0.6 ) - 0.3, s + k * ( w / 2 + 0.6 ) + 0.3, z - h / 2, z + h / 2, d0 + 3.05 )


def emergency_light( fine, face, s, z ):
    """ A twin-spot emergency light: its battery box and two heads. """
    face.box( fine, s - 6, s + 6, z - 2.5, z + 2.5, 0, 3.5, "rv_hall_equipment" )
    for k in ( -1, 1 ):
        lathe_on( fine, face.p( s + k * 4, z - 2.8, 3.0 ), unit( face.out - UP * 0.7 + face.a * k * 0.3 ),
                  [ ( 1.1, -1.2 ), ( 1.5, 0 ), ( 1.9, 1.6 ) ], "rv_hall_equipment", 8, cap1="rv_hall_emergency" )


def pipe_marker( fine, name, axis_point, r, out, along=UP, length=None ):
    """ A flow marker on a pipe: a label on its face toward out, running along the pipe (its text reads along it). """
    out3 = unit( v( out[0], out[1], 0.0 ) )
    along = unit( v( *along ) )
    up = np.cross( out3, along )
    h = min( 1.3 * r, 9.0 )
    w = length or sign_w( name, h )
    P.quad( fine, "rv_hall_signs", v( *axis_point ) + out3 * ( r + 0.15 ), along, up, w, h, atlas_uv( name ) )


def wall_item( d, fine, face, kind, s, z0, tray=None, arg=None ):
    """ One of the walls' things, by kind, at s on a face whose floor is z0. """
    if kind == "ext":
        extinguisher( d, fine, face, s, z0 + 30 )
    elif kind == "call":
        call_point( fine, face, s, z0 + 54 )
    elif kind == "panel":
        wall_panel( d, fine, face, s, z0 + 30, tag=arg or "db3", tray=tray )
    elif kind == "phone":
        wall_phone( d, fine, face, s, z0 + 52 )
    elif kind == "arm":
        radiation_monitor( d, fine, face, s, z0 + 86 )
    elif kind == "eyewash":
        eyewash( d, fine, face, s, z0 )
    elif kind == "hose":
        hose_cabinet( d, fine, face, s, z0 + 30 )
    elif kind == "firstaid":
        first_aid( d, fine, face, s, z0 + 54 )
    elif kind == "board":
        notice_board( d, fine, face, s, z0 + 46 )
    elif kind == "rules":
        notice_board( d, fine, face, s, z0 + 40, 26.0, 28.0, "pool_rules" )
    elif kind == "sign":
        name, z, h = arg
        sign_on( fine, face, name, s, z0 + z, h )


def dado( fine, face, s0, s1, z0=0.0, top=54.0 ):
    """ The walls' epoxy band: up to top over the floor at z0, a cove at its foot and a fine line at its top. """
    if s1 - s0 < 1.0:
        return
    face.quad( fine, "rv_hall_epoxy", s0, s1, z0 + 2.5, z0 + top, 0.25 )
    face.quad( fine, "rv_hall_joint", s0, s1, z0 + top, z0 + top + 0.6, 0.3 )
    card( fine, "rv_hall_epoxy", [ face.p( s0, z0 + 0.05, 2.6 ), face.p( s1, z0 + 0.05, 2.6 ), face.p( s1, z0 + 2.5, 0.25 ),
                                   face.p( s0, z0 + 2.5, 0.25 ) ], face.out + UP )


def pilaster_dado( fine, front, out, w, dep, z0=0.0 ):
    """ The epoxy band round a pilaster: front is its front face's centre (plan), out the way it faces. """
    f = Face( front, out )
    dado( fine, f, -w / 2, w / 2, z0 )
    for k in ( -1, 1 ):
        side = Face( f.o + f.a * k * w / 2 - f.out * dep / 2, f.a * k )
        dado( fine, side, -dep / 2, dep / 2, z0 )


def ladder_tray( d, fine, face, s0, s1, z, d0, d1, cables=5, hung=None ):
    """ A ladder cable tray along a face, d0..d1 out, its bed at z: channel rails, rungs, the cables in it, and either
    cantilever brackets off the wall or, with hung (the deck's z), threaded rods and struts from above. """
    if s1 - s0 < 12:
        return
    for dd, sg in ( ( d0, -1 ), ( d1, 1 ) ):
        channel( d, face.p( s0, z + 2, dd ), face.p( s1, z + 2, dd ), 4.0, 1.2, "rv_galv", t=0.25, opens=face.out * -sg )
    for s in np.arange( s0 + 6, s1 - 2, 12.0 ):
        bar( d, face.p( s, z + 0.4, d0 ), face.p( s, z + 0.4, d1 ), 1.0, 0.6, "rv_galv" )
    for k in range( cables ):
        dd = d0 + ( d1 - d0 ) * ( k + 0.5 ) / cables
        P.rod( fine, face.p( s0, z + 1.6, dd ), face.p( s1, z + 1.6, dd ), 0.95 if k % 2 else 0.7, "rv_hall_cable", 6 )
    for s in np.arange( s0 + 10, s1, 72.0 ):
        if hung is None:
            bar( d, face.p( s, z - 0.9, 0 ), face.p( s, z - 0.9, d1 + 1.5 ), 1.6, 1.6, "rv_galv" )
            bar( d, face.p( s, z - 14, 0 ), face.p( s, z - 1.6, d1 * 0.75 ), 1.2, 1.2, "rv_galv" )
        else:
            bar( d, face.p( s, z - 0.9, d0 - 2 ), face.p( s, z - 0.9, d1 + 2 ), 1.6, 1.6, "rv_galv" )
            for dd in ( d0 - 1.2, d1 + 1.2 ):
                P.rod( fine, face.p( s, z - 1.8, dd ), face.p( s, hung, dd ), 0.3, "rv_galv", 4 )


# ---------------------------------------------------------------------------------------------------------------------
# The hall

def wall( m, axis, a0, a1, t0, t1, z0, z1, openings=(), paint="rv_wall", surface=STONE ):
    """ A wall running along axis ('e' or 'n') from a0 to a1, t0..t1 thick across, with openings ( b0, b1, top[, bottom] )
    (bottom: a window's sill; without it the opening runs down to z0): split into boxes round them, so the reveals are
    the boxes' own faces. """
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


def ring( c, r, a0, a1, count ):
    return [ v( c[0] + r * math.cos( a ), c[1] + r * math.sin( a ), 0 ) for a in np.linspace( a0, a1, count ) ]


def deck( m, paint="rv_floor" ):
    """ The deck round the pool: wedges from the pool's edge out to the walls (each convex), drawn and solid. """
    c = v( *POOL, 0 )
    segs = 48
    corners = [ v( E1, N1, 0 ), v( E0, N1, 0 ), v( E0, N0, 0 ), v( E1, N0, 0 ) ]

    def hit( a ):
        d = v( math.cos( a ), math.sin( a ), 0 )
        ts = []
        if abs( d[0] ) > 1e-9:
            ts += [ ( E1 - c[0] ) / d[0], ( E0 - c[0] ) / d[0] ]
        if abs( d[1] ) > 1e-9:
            ts += [ ( N1 - c[1] ) / d[1], ( N0 - c[1] ) / d[1] ]
        return c + d * min( t for t in ts if t > 0 )

    for k in range( segs ):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * ( k + 1 ) / segs
        inner0 = c + v( math.cos( a0 ), math.sin( a0 ), 0 ) * POOL_R
        inner1 = c + v( math.cos( a1 ), math.sin( a1 ), 0 ) * POOL_R
        mid = []
        for q in corners:
            ang = math.atan2( q[1] - c[1], q[0] - c[0] ) % ( 2 * math.pi )
            if a0 < ang < a1:
                mid.append( ( ang, q ) )
        outline = [ inner0, hit( a0 ) ] + [ q for _, q in sorted( mid, key=lambda x: x[0] ) ] + [ hit( a1 ), inner1 ]
        card( m, paint, outline, UP )
        m.hull( [ p + UP * z for p in outline for z in ( -24.0, 0.0 ) ], STONE )


def pool( m ):
    """ The pool: liner walls and floor, the coping, the skimmer gutter under it, cyan lamps in the wall, the fuel
    racks, the transfer canal's gate, a ladder and long-handled tools. Drawn only (the deck and the clips keep everyone
    out). """
    c = v( *POOL, 0 )
    segs = 64
    dirs = [ v( math.cos( 2 * math.pi * k / segs ), math.sin( 2 * math.pi * k / segs ), 0 ) for k in range( segs ) ]
    for k in range( segs ):
        d0, d1 = dirs[k], dirs[( k + 1 ) % segs]
        p0, p1 = c + d0 * POOL_R, c + d1 * POOL_R
        card( m, "rv_liner", [ p0 + UP * POOL_FLOOR, p1 + UP * POOL_FLOOR, p1 + UP * 0, p0 + UP * 0 ], -( d0 + d1 ),
              normals=[ -d0, -d1, -d1, -d0 ] )
        q0, q1 = c + d0 * ( POOL_R + 14 ), c + d1 * ( POOL_R + 14 )
        card( m, "rv_plinth", [ p0 + UP * 3, p1 + UP * 3, q1 + UP * 3, q0 + UP * 3 ], UP )
        card( m, "rv_plinth", [ q0 + UP * 0, q1 + UP * 0, q1 + UP * 3, q0 + UP * 3 ], d0 + d1 )
        card( m, "rv_liner", [ p0 + UP * -2, p1 + UP * -2, p1 + UP * 3, p0 + UP * 3 ], -( d0 + d1 ) )
        # The coping's stainless nosing, and the skimmer gutter: a ledge and its dark slot just under it.
        r0, r1 = c + d0 * ( POOL_R + 14.15 ), c + d1 * ( POOL_R + 14.15 )
        card( m, "rv_stainless", [ r0 + UP * 1.2, r1 + UP * 1.2, r1 + UP * 3.0, r0 + UP * 3.0 ], d0 + d1 )
        g0, g1 = c + d0 * ( POOL_R - 3 ), c + d1 * ( POOL_R - 3 )
        card( m, "rv_stainless", [ p0 + UP * -8, p1 + UP * -8, g1 + UP * -8, g0 + UP * -8 ], UP )
        card( m, "rv_stainless", [ g0 + UP * -10, g1 + UP * -10, g1 + UP * -8, g0 + UP * -8 ], -( d0 + d1 ), normals=[ -d0, -d1, -d1, -d0 ] )
        s0, s1 = c + d0 * ( POOL_R - 0.15 ), c + d1 * ( POOL_R - 0.15 )
        card( m, "rv_black", [ s0 + UP * -7.5, s1 + UP * -7.5, s1 + UP * -3.5, s0 + UP * -3.5 ], -( d0 + d1 ) )
    card( m, "rv_liner", [ c + d * POOL_R + UP * POOL_FLOOR for d in dirs ], UP )
    # Lamps in the wall a little under the water.
    for k in range( 24 ):
        a = 2 * math.pi * ( k + 0.5 ) / 24
        d = v( math.cos( a ), math.sin( a ), 0 )
        right = np.cross( UP, -d )
        P.quad( m, "rv_lamp_cyan", c + d * ( POOL_R - 0.4 ) + UP * ( WATER_Z - 34 ), right, UP, 34, 8 )
        P.quad( m, "rv_dark", c + d * ( POOL_R - 0.2 ) + UP * ( WATER_Z - 34 ), right, UP, 40, 12 )
    # Fuel racks: modules on legs, their cells glowing.
    rng = np.random.default_rng( 3 )
    for i in range( -3, 4 ):
        for j in range( -3, 4 ):
            e, n = i * 124.0, j * 124.0
            if math.hypot( e, n ) > POOL_R - 110 or ( abs( e - ( MAST[0] - POOL[0] ) ) < 120 and abs( n ) < 120 ):
                continue
            if rng.random() < 0.16:
                continue
            h = 150.0 if rng.random() < 0.7 else 110.0
            lo = v( POOL[0] + e - 52, POOL[1] + n - 52, POOL_FLOOR + 10 )
            hi = v( POOL[0] + e + 52, POOL[1] + n + 52, POOL_FLOOR + 10 + h )
            m.box( lo, hi, { "default": "rv_rack", "-z": None } )
            for sx in ( -1, 1 ):
                for sy in ( -1, 1 ):
                    box( m, POOL[0] + e + sx * 46 - 3, POOL[0] + e + sx * 46 + 3, POOL[1] + n + sy * 46 - 3, POOL[1] + n + sy * 46 + 3,
                         POOL_FLOOR, POOL_FLOOR + 10, "rv_liner" )
            # Lifting bails over the module's corners.
            for sx in ( -1, 1 ):
                P.rod( m, ( POOL[0] + e + sx * 40, POOL[1] + n - 20, POOL_FLOOR + 10 + h ), ( POOL[0] + e + sx * 40, POOL[1] + n + 20, POOL_FLOOR + 10 + h ),
                       1.0, "rv_stainless", 5 )
    # The transfer canal's gate in the north wall: guide channels, the gate with its stiffeners and lifting lugs.
    gc = c + v( 0, 1, 0 ) * POOL_R
    for sg in ( -1, 1 ):
        box( m, gc[0] + sg * 36 - 3, gc[0] + sg * 36 + 3, gc[1] - 5, gc[1] + 1, POOL_FLOOR + 40, 3, "rv_stainless" )
    box( m, gc[0] - 33, gc[0] + 33, gc[1] - 3.2, gc[1] + 1, POOL_FLOOR + 60, -6, "rv_liner" )
    for z in np.arange( POOL_FLOOR + 90, -20, 70.0 ):
        box( m, gc[0] - 33, gc[0] + 33, gc[1] - 4.4, gc[1] - 3.2, z, z + 3, "rv_stainless" )
    for sg in ( -1, 1 ):
        box( m, gc[0] + sg * 18 - 2, gc[0] + sg * 18 + 2, gc[1] - 3.6, gc[1] - 1.2, -6, 0, "rv_stainless" )
        hoop( m, ( gc[0] + sg * 18, gc[1] - 2.4, 1.6 ), ( 0, 1, 0 ), 1.8, 0.4, "rv_stainless", 8, 4 )
    # A ladder down into the water, on the west side.
    ld = v( math.cos( math.radians( 200 ) ), math.sin( math.radians( 200 ) ), 0 )
    lt = np.cross( UP, ld )
    for sg in ( -1, 1 ):
        o = lt * 9 * sg
        P.pipe( m, [ c + ld * ( POOL_R + 7 ) + o + UP * 3.2, c + ld * ( POOL_R + 7 ) + o + UP * 32, c + ld * ( POOL_R - 4 ) + o + UP * 32,
                     c + ld * ( POOL_R - 4 ) + o + UP * -220 ], 0.8, "rv_stainless", 8 )
    for z in np.arange( -210.0, 0.0, 12.0 ):
        P.rod( m, c + ld * ( POOL_R - 4 ) - lt * 9 + UP * z, c + ld * ( POOL_R - 4 ) + lt * 9 + UP * z, 0.55, "rv_stainless", 6 )
    # Long-handled tools hung over the coping on the south-east side, their heads deep in the water.
    td = v( math.cos( math.radians( 325 ) ), math.sin( math.radians( 325 ) ), 0 )
    tt = np.cross( UP, td )
    for k, ( dx, depth ) in enumerate( ( ( -6.0, -300.0 ), ( 0.0, -240.0 ), ( 6.0, -330.0 ) ) ):
        top = c + td * ( POOL_R + 8 ) + tt * dx + UP * 40
        low = c + td * ( POOL_R - 16 ) + tt * ( dx * 1.6 ) + UP * depth
        P.rod( m, top, low, 0.6, "rv_stainless", 6 )
        P.obox( m, low - UP * 4, tt, ( 3.5, 3.5, 8 ), "rv_stainless" )
        P.rod( m, top, top - td * 3 + UP * 2, 0.8, "rv_yellow", 5 )


def mast( m, solid ):
    """ The fuel handling mast from the pool floor up to the crane's hook block: four yellow angle columns with struts
    and bracing on each face, grating platforms, a ladder up its south face, the hose bundle in its middle with its
    clamps, the machinery head under the hook (motor, reel, junction box, the yoke), and its lit cage under the water. """
    c = v( *MAST, 0 )
    top = CRANE_Z - 40
    s = 30.0
    for sx in ( -1, 1 ):
        for sy in ( -1, 1 ):
            corner = c + v( sx * ( s + 4 ), sy * ( s + 4 ), 0 )
            angle_iron( m, corner + UP * POOL_FLOOR, corner + UP * top, 8.0, "rv_yellow", ( -sx, 0, 0 ), ( 0, -sy, 0 ), t=0.9 )
    faces = []
    for sx in ( -1, 1 ):
        faces.append( ( c + v( sx * ( s + 3.5 ), -s, 0 ), c + v( sx * ( s + 3.5 ), s, 0 ), v( sx, 0, 0 ) ) )
    for sy in ( -1, 1 ):
        faces.append( ( c + v( -s, sy * ( s + 3.5 ), 0 ), c + v( s, sy * ( s + 3.5 ), 0 ), v( 0, sy, 0 ) ) )
    for z in np.arange( POOL_FLOOR + 40, top - 20, 110.0 ):
        for a, b, nrm in faces:
            bar( m, a + UP * z, b + UP * z, 3.5, 0.6, "rv_yellow", hint=nrm )
            bar( m, a + UP * z, b + UP * ( z + 110 ), 2.4, 0.5, "rv_steel", hint=nrm )
    # Platforms (were solid bands): a channel frame, grating, kick plates.
    for z in ( 110.0, 290.0, 480.0, 680.0 ):
        for sx in ( -1, 1 ):
            box( m, *sorted( ( c[0] + sx * 35, c[0] + sx * 38 ) ), c[1] - 38, c[1] + 38, z, z + 12, "rv_yellow" )
            box( m, c[0] - 35, c[0] + 35, *sorted( ( c[1] + sx * 35, c[1] + sx * 38 ) ), z, z + 12, "rv_yellow" )
        box( m, c[0] - 35, c[0] + 35, c[1] - 35, c[1] + 35, z + 8, z + 8.3, { "default": None, "+z": "rv_grating", "-z": "rv_grating" } )
    P.railing( m, [ ( c[0] - 37, c[1] - 37 ), ( c[0] + 37, c[1] - 37 ), ( c[0] + 37, c[1] + 37 ), ( c[0] - 37, c[1] + 37 ) ], 692.0,
               "rv_yellow", height=36, post_every=40, kick=False, closed=True )
    # The hose bundle and its clamps.
    for dx, dy, r in ( ( -12, -10, 4.5 ), ( 12, -10, 4.5 ), ( 0, 12, 6.0 ), ( -18, 14, 2.5 ), ( 18, 14, 2.5 ) ):
        P.rod( m, c + v( dx, dy, POOL_FLOOR + 20 ), c + v( dx, dy, top + 6 ), r, "rv_pipe", 10 )
    for z in np.arange( -40.0, top - 20, 90.0 ):
        box( m, c[0] - 21, c[0] + 21, c[1] - 15.5, c[1] + 18.5, z, z + 2.2, "rv_steel" )
    # Its foot under the water: the lit core and the cage.
    P.cylinder( m, c, 22.0, POOL_FLOOR + 20, -80.0, "rv_cyan_glow", 16 )
    for z in np.arange( POOL_FLOOR + 30, -70.0, 36.0 ):
        P.cylinder( m, c, 54.0, z, z + 3, "rv_steel", 20 )
    for k in range( 12 ):
        a = 2 * math.pi * k / 12
        d = v( math.cos( a ), math.sin( a ), 0 )
        P.rod( m, c + d * 54 + UP * ( POOL_FLOOR + 20 ), c + d * 54 + UP * -70, 1.6, "rv_rack", 6 )
    # A ladder up the south face from the water.
    ln = c[1] - s - 9
    for sg in ( -1, 1 ):
        P.rod( m, ( c[0] + sg * 9, ln, -20 ), ( c[0] + sg * 9, ln, top ), 0.8, "rv_yellow", 6 )
    for z in np.arange( -12.0, top - 4, 12.0 ):
        P.rod( m, ( c[0] - 9, ln, z ), ( c[0] + 9, ln, z ), 0.5, "rv_yellow", 4 )
    for z in ( 40.0, 200.0, 380.0, 580.0, 760.0 ):
        bar( m, ( c[0] - 9, ln, z ), ( c[0] - 9, c[1] - s - 3.5, z ), 1.2, 1.2, "rv_yellow" )
        bar( m, ( c[0] + 9, ln, z ), ( c[0] + 9, c[1] - s - 3.5, z ), 1.2, 1.2, "rv_yellow" )
    # The machinery head: a deck plate, the hoist yoke, a motor, the cable reel, a junction box, a beacon.
    box( m, c[0] - 31, c[0] + 31, c[1] - 31, c[1] + 31, top, top + 3, "rv_yellow" )
    for sx in ( -1, 1 ):
        box( m, *sorted( ( c[0] + sx * 20, c[0] + sx * 25 ) ), c[1] - 9, c[1] + 9, top + 3, top + 30, "rv_yellow" )
    P.rod( m, ( c[0] - 27, c[1], top + 24 ), ( c[0] + 27, c[1], top + 24 ), 2.6, "rv_hall_chrome", 10, caps=True )
    lathe_on( m, c + v( -12, -16, top + 11 ), ( 0, 1, 0 ), [ ( 3, -2 ), ( 7.5, -1 ), ( 8, 0 ), ( 8, 16 ), ( 7, 17 ), ( 2, 17 ) ], "rv_hall_blue", 12,
              cap0="rv_hall_blue", cap1="rv_hall_blue" )
    lathe_on( m, c + v( 12, -26, top + 16 ), ( 0, 1, 0 ), [ ( 13, 0 ), ( 13, 2 ), ( 9.5, 2 ), ( 9.5, 18 ), ( 13, 18 ), ( 13, 20 ) ],
              [ "rv_yellow", "rv_yellow", "rv_hall_cable", "rv_yellow", "rv_yellow" ], 14, cap0="rv_yellow", cap1="rv_yellow" )
    box( m, c[0] + 8, c[0] + 24, c[1] + 12, c[1] + 22, top + 3, top + 21, "rv_hall_equipment" )
    P.beacon( m, "Mast beacon", ( c[0] - 26, c[1] + 26, top + 3 ), light=False )
    solid.collision_box( c + v( -40, -40, POOL_FLOOR ), c + v( 40, 40, top + 30 ), METAL )


def crane( m, detail=None, fine=None ):
    """ The overhead travelling crane: its runway girders on tapered corbels along the side walls (stiffeners, the
    rail and its clips, end stops, the conductor bars), two box girders round the mast with the logo and "SWL 125 T",
    end trucks on their wheels with drives and buffers, a walkway, the trolley with its hoist (drum, motor, gearbox),
    the hook block on its rope falls, the operator's cab, a festoon of cables and floodlights. Drawn only. """
    d = detail if detail is not None else m
    fn = fine if fine is not None else d
    gz = CRANE_Z + 6
    zc = CRANE_Z - 18
    for sx in ( -1, 1 ):
        e = sx * ( E1 - 20 )
        wide_flange( d, ( e, N0 + 10, zc ), ( e, N1 - 10, zc ), 36, 16, "rv_steel", web=0.75, flange=1.25 )
        for n in np.arange( N0 + 40, N1 - 20, 60.0 ):
            for side in ( -1, 1 ):
                box( d, *sorted( ( e + side * 0.375, e + side * 7.6 ) ), n - 0.4, n + 0.4, zc - 16.75, zc + 16.75, "rv_steel" )
        box( d, e - 2.6, e + 2.6, N0 + 10, N1 - 10, CRANE_Z, CRANE_Z + 0.9, "rv_steel" )
        box( d, e - 0.7, e + 0.7, N0 + 10, N1 - 10, CRANE_Z + 0.9, CRANE_Z + 4.4, "rv_steel" )
        box( d, e - 1.4, e + 1.4, N0 + 10, N1 - 10, CRANE_Z + 4.4, CRANE_Z + 6.0, "rv_stainless" )
        for n in np.arange( N0 + 24, N1 - 10, 48.0 ):
            for side in ( -1, 1 ):
                box( fn, *sorted( ( e + side * 2.6, e + side * 4.8 ) ), n - 1.6, n + 1.6, CRANE_Z, CRANE_Z + 1.4, "rv_dark" )
        for n, sg in ( ( N0 + 16, 1 ), ( N1 - 16, -1 ) ):
            box( d, e - 7, e + 7, n - 6, n + 6, CRANE_Z, CRANE_Z + 18, "rv_yellow" )
            lathe_on( d, ( e, n + sg * 6, CRANE_Z + 11 ), ( 0, sg, 0 ), [ ( 4.5, 0 ), ( 4.5, 7 ), ( 3.6, 8.2 ) ], "rv_rubber", 10, cap1="rv_rubber" )
        # Conductor bars on hangers between the girder and the wall.
        ce = sx * ( E1 - 6 )
        for n in np.arange( N0 + 40, N1 - 20, 60.0 ):
            box( d, *sorted( ( sx * ( E1 - 12 ), sx * ( E1 - 1 ) ) ), n - 0.6, n + 0.6, zc + 6, zc + 8, "rv_steel" )
            box( fn, ce - 0.4, ce + 0.4, n - 0.4, n + 0.4, zc - 6, zc + 6, "rv_steel" )
        for k, z in enumerate( ( zc + 3.0, zc - 0.5, zc - 4.0 ) ):
            box( fn, ce - 0.6 + sx * 0.8, ce + 0.6 + sx * 0.8, N0 + 30, N1 - 30, z - 0.7, z + 0.7, "rv_hall_red" if k == 0 else "rv_hall_plastic_grey" )
        # Corbels: tapered concrete brackets under the girder, a bearing plate on each.
        wall_e, tip_e = sx * E1, sx * ( E1 - 34 )
        zt = CRANE_Z - 36
        for n in np.arange( N0 + 120, N1, 280.0 ):
            extrude( d, indoor(), [ ( wall_e, zt ), ( tip_e, zt ), ( tip_e, zt - 14 ), ( wall_e, zt - 62 ) ], n - 22, n + 22, "n" )
            box( d, *sorted( ( sx * ( E1 - 30 ), sx * ( E1 - 9 ) ) ), n - 12, n + 12, zt - 1.0, zt + 0.4, "rv_steel" )
    # The bridge: box girders with flanges wider than their webs, diaphragm stiffeners outside, the trolley's rails.
    lettered = { ( 0, -1 ): ( ( -262, -58 ), ( -780, -660 ), ( 660, 780 ) ), ( 1, 1 ): ( ( 58, 262 ), ) }
    for gi, n in enumerate( CRANE_N ):
        box( d, E0 + 40, E1 - 40, n - 15, n + 15, gz + 1.5, gz + 62.5, "rv_yellow" )
        box( d, E0 + 40, E1 - 40, n - 17, n + 17, gz, gz + 1.5, "rv_yellow" )
        box( d, E0 + 40, E1 - 40, n - 17, n + 17, gz + 62.5, gz + 64, "rv_yellow" )
        box( d, E0 + 50, E1 - 50, n - 1.4, n + 1.4, gz + 64, gz + 67, "rv_steel" )
        for e in np.arange( E0 + 80, E1 - 40, 80.0 ):
            for sn in ( -1, 1 ):
                if any( a <= e <= b for a, b in lettered.get( ( gi, sn ), () ) ):
                    continue
                box( d, e - 0.5, e + 0.5, *sorted( ( n + sn * 15, n + sn * 16.4 ) ), gz + 1.5, gz + 62.5, "rv_yellow" )
    # End trucks: on their wheels over the runway rails, drives inside, buffers at their ends.
    for sx in ( -1, 1 ):
        a, b = sorted( ( sx * ( E1 - 40 ), sx * ( E1 - 4 ) ) )
        n0_, n1_ = CRANE_N[0] - 50, CRANE_N[1] + 50
        box( d, a, b, n0_, n1_, gz + 10, gz + 60, "rv_yellow" )
        for z0_, z1_ in ( ( gz + 8.5, gz + 10 ), ( gz + 60, gz + 61.5 ) ):
            box( d, a - 1, b + 1, n0_, n1_, z0_, z1_, "rv_yellow" )
        we = sx * ( E1 - 20 )
        for n in ( CRANE_N[0] - 30, CRANE_N[1] + 30 ):
            lathe_on( d, ( we, n, gz + 10 ), ( 1, 0, 0 ), [ ( 11.5, -3.2 ), ( 11.5, -2.0 ), ( 10.0, -2.0 ), ( 10.0, 3.2 ) ], "rv_steel", 16,
                      cap0="rv_steel", cap1="rv_steel" )
        gi_ = sx * ( E1 - 40 )
        box( d, *sorted( ( gi_, gi_ - sx * 12 ) ), POOL[1] - 18, POOL[1] + 18, gz + 14, gz + 40, "rv_hall_blue" )
        lathe_on( d, ( gi_ - sx * 6, POOL[1] + 18, gz + 27 ), ( 0, 1, 0 ), [ ( 2, 0 ), ( 6.5, 0.5 ), ( 7, 1.5 ), ( 7, 18 ), ( 6, 19 ), ( 2, 19 ) ],
                  "rv_hall_blue", 12, cap1="rv_hall_blue" )
        lathe_on( d, ( gi_ - sx * 6, POOL[1] - 18, gz + 27 ), ( 0, -1, 0 ), [ ( 6.5, 0 ), ( 6.5, 2.5 ) ], "rv_dark", 12, cap1="rv_dark" )
        for n, sg in ( ( n0_, -1 ), ( n1_, 1 ) ):
            lathe_on( d, ( sx * ( E1 - 22 ), n, gz + 36 ), ( 0, sg, 0 ), [ ( 5, 0 ), ( 5, 6 ), ( 4, 7.5 ) ], "rv_rubber", 10, cap1="rv_rubber" )
    # A walkway with a railing along the south girder's outside, on brackets.
    s0 = CRANE_N[0] - 15
    box( d, E0 + 40, E1 - 40, s0 - 25, s0, gz + 60, gz + 62, "rv_grating" )
    P.railing( d, [ ( E0 + 50, s0 - 25 ), ( E1 - 50, s0 - 25 ) ], gz + 62, "rv_yellow", height=36, post_every=80 )
    for e in np.arange( E0 + 60, E1 - 40, 80.0 ):
        bar( d, ( e, s0, gz + 59.5 ), ( e, s0 - 25, gz + 59.5 ), 0.6, 2.5, "rv_yellow" )
        bar( d, ( e, s0, gz + 30 ), ( e, s0 - 22, gz + 58.5 ), 0.6, 2.0, "rv_yellow", hint=( 1, 0, 0 ) )
    for e in ( -820.0, 620.0 ):
        box( d, e - 14, e + 14, s0 - 23, s0 - 13, gz + 62, gz + 92, "rv_hall_equipment" )
        P.quad( fn, "rv_hall_signs", ( e, s0 - 23.05, gz + 77 ), ( -1, 0, 0 ), UP, 26, 28, atlas_uv( "panel_door" ) )
    # The trolley: wheels on the girders' rails, its frame, the deck plate, the hoist's drum, gearbox, motor, brake and
    # a cabinet.
    tx = MAST[0]
    tz = gz + 67
    for e_ in ( tx - 62, tx + 62 ):
        for n in CRANE_N:
            lathe_on( d, ( e_, n - 3, tz + 6 ), ( 0, 1, 0 ), [ ( 7.5, 0 ), ( 7.5, 1 ), ( 6, 1 ), ( 6, 6 ) ], "rv_steel", 12, cap0="rv_steel", cap1="rv_steel" )
    for n in CRANE_N:
        box( d, tx - 75, tx + 75, n - 5, n + 5, tz + 4, tz + 16, "rv_yellow" )
    for e_ in ( tx - 75, tx + 75 ):
        box( d, e_ - 4, e_ + 4, CRANE_N[0] - 5, CRANE_N[1] + 5, tz + 4, tz + 16, "rv_yellow" )
    box( d, tx - 75, tx - 44, CRANE_N[0] + 5, CRANE_N[1] - 5, tz + 12, tz + 13, "rv_steel" )
    dc = v( tx - 24, POOL[1], tz + 14 )
    lathe_on( d, dc, ( 1, 0, 0 ), [ ( 15.5, 0 ), ( 15.5, 2.5 ), ( 12, 2.5 ), ( 12, 69.5 ), ( 15.5, 69.5 ), ( 15.5, 72 ) ], "rv_steel", 16,
              cap0="rv_steel", cap1="rv_steel" )
    for k in range( 16 ):
        lathe_on( d, dc + v( 6 + k * 4, 0, 0 ), ( 1, 0, 0 ), [ ( 12, 0 ), ( 12.6, 0.4 ), ( 12.6, 2.6 ), ( 12, 3.0 ) ], "rv_hall_rope", 16 )
    box( d, tx - 44, tx - 25, CRANE_N[0] + 20, POOL[1] + 15, tz + 2, tz + 28, "rv_hall_blue" )
    lathe_on( d, ( tx - 44, CRANE_N[0] + 30, tz + 14 ), ( -1, 0, 0 ), [ ( 3, 0 ), ( 8.5, 0.5 ), ( 9, 1.5 ), ( 9, 23 ), ( 8, 24 ), ( 3, 24 ), ( 3, 26 ) ],
              "rv_hall_blue", 14, cap1="rv_hall_blue" )
    for k in range( 7 ):
        lathe_on( d, ( tx - 47 - k * 3, CRANE_N[0] + 30, tz + 14 ), ( -1, 0, 0 ), [ ( 9, 0 ), ( 9.8, 0.2 ), ( 9.8, 0.9 ), ( 9, 1.1 ) ], "rv_hall_blue", 14 )
    lathe_on( d, ( tx - 44, POOL[1], tz + 14 ), ( -1, 0, 0 ), [ ( 9, 0 ), ( 9, 3 ) ], "rv_dark", 14, cap0="rv_dark", cap1="rv_dark" )
    box( d, tx + 52, tx + 70, CRANE_N[1] - 36, CRANE_N[1] - 8, tz + 13, tz + 27, "rv_hall_equipment" )
    # The hook block on six falls from the drum, and the hook's shackle on the mast's yoke.
    hx, hn = MAST[0], POOL[1]
    hz0, hz1 = gz + 2, gz + 30
    for k in ( -1, 1 ):
        box( d, hx + k * 16, hx + k * 19, hn - 15, hn + 15, hz0, hz1, "rv_yellow" )
    for ex in ( -9.0, 0.0, 9.0 ):
        lathe_on( d, ( hx + ex - 2.2, hn, hz1 - 9 ), ( 1, 0, 0 ), [ ( 11.5, 0 ), ( 11.5, 4.4 ) ], "rv_steel", 14, cap0="rv_steel", cap1="rv_steel" )
        for sn in ( -1, 1 ):
            P.rod( fn, ( hx + ex, hn + sn * 11.8, hz1 - 9 ), ( hx + ex, hn + sn * 11.8, tz + 14 ), 0.55, "rv_hall_rope", 5 )
    P.rod( d, ( hx - 19, hn, hz1 - 9 ), ( hx + 19, hn, hz1 - 9 ), 1.6, "rv_hall_chrome", 8, caps=True )
    box( d, hx - 16, hx + 16, hn - 12, hn + 12, hz0 - 4, hz0, "rv_yellow" )
    P.rod( d, ( hx, hn, hz0 - 4 ), ( hx, hn, CRANE_Z - 6 ), 2.2, "rv_steel", 8 )
    hoop( d, ( hx, hn, CRANE_Z - 11 ), ( 0, 1, 0 ), 5.5, 1.2, "rv_steel", 12, 6 )
    # The operator's cab under the north girder's east end: walls, windows, its hangers and a ladder up.
    cab = Face( ( 0, 958 ), ( 0, -1 ) )
    box( d, 852, 908, 958, 1012, gz - 72, gz - 6, "rv_yellow" )
    box( d, 850, 910, 956, 1014, gz - 74, gz - 72, "rv_steel" )
    box( d, 850, 910, 956, 1014, gz - 6, gz - 4, "rv_steel" )
    cab.quad( fn, "rv_window_dark", 856, 904, gz - 56, gz - 18, 0.15 )
    west = Face( ( 852, 0 ), ( -1, 0 ) )
    west.quad( fn, "rv_window_dark", *west.ss( ( 852, 962 ), ( 852, 1008 ) ), gz - 56, gz - 18, 0.15 )
    for sxx in ( 856.0, 880.0, 904.0 ):
        cab.box( fn, sxx - 1, sxx + 1, gz - 57, gz - 17, 0, 0.6, "rv_steel" )
    for e_ in ( 856.0, 904.0 ):
        box( d, e_ - 1.5, e_ + 1.5, 980 - 1.5, 980 + 1.5, gz - 4, gz, "rv_steel" )
    for z in np.arange( gz - 66, gz + 60, 12.0 ):
        P.rod( fn, ( 912, 1000, z ), ( 912, 1010, z ), 0.5, "rv_yellow", 4 )
    for nn in ( 1000.0, 1010.0 ):
        P.rod( fn, ( 912, nn, gz - 70 ), ( 912, nn, gz + 62 ), 0.7, "rv_yellow", 5 )
    # A festoon: cable loops hanging along the south girder's outside from the east end truck to the trolley.
    pts = []
    xs = list( np.linspace( E1 - 50, tx + 60, 9 ) )
    for a_, b_ in zip( xs, xs[1:] ):
        for t in np.linspace( 0, 1, 7 )[:-1]:
            pts.append( ( a_ + ( b_ - a_ ) * t, gz + 48 - 34 * 4 * t * ( 1 - t ) ) )
    pts.append( ( xs[-1], gz + 48 ) )
    for k, dn in enumerate( ( -19.5, -21.0, -22.5 ) ):
        P.pipe( fn, [ ( e_, s0 + dn, z ) for e_, z in pts ], 0.7, "rv_hall_cable", 5, caps=False, bend=0.5 )
    box( d, tx + 50, E1 - 40, s0 - 23.5, s0 - 18.5, gz + 48, gz + 50, "rv_steel" )
    for e_ in xs:
        box( fn, e_ - 1.5, e_ + 1.5, s0 - 23, s0 - 19, gz + 46, gz + 48, "rv_dark" )
    # Floodlights under the bridge.
    for n in CRANE_N:
        for e_ in ( -700.0, -300.0, 300.0, 700.0 ):
            P.obox( d, ( e_, n, gz - 4 ), ( 1, 0 ), ( 14, 10, 6 ), "rv_dark" )
            P.quad( fn, "rv_lamp_cool", ( e_, n, gz - 7.05 ), ( 1, 0, 0 ), ( 0, -1, 0 ), 12, 8 )
    # Lettering on the south girder's south face: the logo and the name, and the safe working load.
    f = s0 - 0.3
    P.letters( d, "logo_wordmark", ( -160, f, gz + 32 ), ( 1, 0, 0 ), 42, "dark" )
    P.letters( d, "swl", ( 720, f, gz + 30 ), ( 1, 0, 0 ), 20, "dark" )
    P.letters( d, "swl", ( -720, f, gz + 30 ), ( 1, 0, 0 ), 20, "dark" )
    f2 = CRANE_N[1] + 15.3
    P.letters( d, "logo_wordmark", ( 160, f2, gz + 32 ), ( -1, 0, 0 ), 42, "dark" )
    for sx in ( -1, 1 ):
        P.beacon( d, f"Crane beacon {sx}", ( sx * ( E1 - 60 ), POOL[1], gz + 61.5 ), light=False )


def truss( m, e, n0=N0 + 4.0, n1=N1 - 4.0, zb=TRUSS_BOTTOM, depth=TRUSS_DEPTH, panel=110.0 ):
    """ A roof truss along n: double-angle chords (drawn as tees), double-angle webs in a Warren pattern, end posts, a
    gusset plate at every node and a bearing plate at each wall. Drawn only. """
    zt = zb + depth
    box( m, e - 4.0, e + 4.0, n0, n1, zb - 3.0, zb - 2.2, "rv_steel" )
    box( m, e - 0.45, e + 0.45, n0, n1, zb - 2.2, zb + 3.0, "rv_steel" )
    box( m, e - 4.0, e + 4.0, n0, n1, zt + 2.2, zt + 3.0, "rv_steel" )
    box( m, e - 0.45, e + 0.45, n0, n1, zt - 3.0, zt + 2.2, "rv_steel" )
    count = max( 1, int( round( ( n1 - n0 ) / panel ) ) )
    L = n1 - n0
    for i in range( count ):
        a = v( e, n0 + L * i / count, zb + 2.0 )
        b = v( e, n0 + L * ( i + 0.5 ) / count, zt - 2.0 )
        c = v( e, n0 + L * ( i + 1 ) / count, zb + 2.0 )
        for p, q in ( ( a, b ), ( b, c ) ):
            bar( m, p, q, 1.0, 2.6, "rv_steel" )
            bar( m, p, q, 5.0, 0.4, "rv_steel" )
        nb = n0 + L * ( i + 0.5 ) / count
        box( m, e - 0.25, e + 0.25, nb - 7, nb + 7, zt - 7.0, zt - 2.2, "rv_steel" )
    for i in range( count + 1 ):
        nn = n0 + L * i / count
        box( m, e - 0.25, e + 0.25, max( n0, nn - 7 ), min( n1, nn + 7 ), zb + 2.2, zb + 7.0, "rv_steel" )
    for nn, sg in ( ( n0 + 1.5, 1 ), ( n1 - 1.5, -1 ) ):
        box( m, e - 2.5, e + 2.5, nn - 1.5, nn + 1.5, zb - 2.2, zt + 2.2, "rv_steel" )
        box( m, e - 7, e + 7, *sorted( ( nn - sg * 1.5, nn + sg * 10 ) ), zb - 4.6, zb - 3.0, "rv_steel" )


def shell( m, detail=None, fine=None ):
    """ The walls, the thresholds, the roof (its galvanised deck under it, its membrane on top) and its trusses, the
    pilasters. """
    d = detail if detail is not None else m
    IN = indoor()
    wall( m, "e", E0 - WT, E1 + WT, N0 - WT, N0, 0, ROOF, [ SOUTH_DOOR ], paint={ "default": "rv_wall", "+n": IN } )
    wall( m, "e", E0 - WT, E1 + WT, N1, N1 + WT, 0, ROOF, list( NORTH_DOORS ), paint={ "default": "rv_wall", "-n": IN } )
    for sx in ( -1, 1 ):
        e0, e1 = ( E0 - WT, E0 ) if sx < 0 else ( E1, E1 + WT )
        wall( m, "n", N0, N1, e0, e1, 0, ROOF, [ WEST_DOOR ], paint={ "default": "rv_wall", ( "+e" if sx < 0 else "-e" ): IN } )
    box( m, SOUTH_DOOR[0], SOUTH_DOOR[1], N0 - WT, N0, -24, 0, { "default": None, "+z": "rv_plinth" }, STONE )
    for o in NORTH_DOORS:
        box( m, o[0], o[1], N1, N1 + WT, -24, 0, { "default": None, "+z": "rv_plinth" }, STONE )
    for e0, e1 in ( ( E0 - WT, E0 ), ( E1, E1 + WT ) ):
        box( m, e0, e1, WEST_DOOR[0], WEST_DOOR[1], -24, 0, { "default": None, "+z": "rv_plinth" }, STONE )
    box( m, E0 - WT, E1 + WT, N0 - WT, N1 + WT, TOP, ROOF, { "default": "rv_wall", "-z": "rv_hall_deck", "+z": "rv_hall_roof" }, STONE )
    for a, b, c, dd in ( ( E0 - WT, E1 + WT, N0 - WT, N0 - WT + 12 ), ( E0 - WT, E1 + WT, N1 + WT - 12, N1 + WT ),
                         ( E0 - WT, E0 - WT + 12, N0 - WT, N1 + WT ), ( E1 + WT - 12, E1 + WT, N0 - WT, N1 + WT ) ):
        box( m, a, b, c, dd, ROOF, ROOF + 40, "rv_wall", STONE )
    for e in TRUSS_ES:
        truss( d, e )
    for e in ( -833.0, -500.0, -167.0, 167.0, 500.0, 833.0 ):
        box( m, e - 24, e + 24, N1 - 22, N1, 0, TOP, IN, STONE )
    for sx in ( -1, 1 ):
        for n, z0 in ( ( -60.0, 0.0 ), ( 400.0, 0.0 ), ( 1250.0, UPPER ), ( 1750.0, UPPER ) ):
            a, b = ( E0, E0 + 22 ) if sx < 0 else ( E1 - 22, E1 )
            box( m, a, b, n - 24, n + 24, z0, TOP, IN, STONE )
    for e in np.arange( E0 - WT + 40, E1 + WT, 260.0 ):
        if abs( e ) < 150:
            continue
        box( m, e - 20, e + 20, N0 - WT - 14, N0 - WT, 0, ROOF + 20, "rv_wall", STONE )


def upper_side( m, sx, detail=None, fine=None ):
    """ One side's upper level (sx -1 west, 1 east; the constants are the west side's, mirrored by e -> -e for the
    east): the stair, the landing, the control room on its columns, the walkway, the block, railings, lamps. With
    detail and fine, what's finer: the control room's fit-out, the steel under the slabs, the stair's channels and
    nosings, the walkway's edges, the block's faces. """
    d = detail if detail is not None else m
    fn = fine if fine is not None else d
    f = -sx
    IN = indoor()

    def E( a, b ):
        return ( min( f * a, f * b ), max( f * a, f * b ) )

    def slab( r ):
        a, b = E( r[0], r[1] )
        box( m, a, b, r[2], r[3], UPPER - SLAB, UPPER, { "default": IN, "+z": "rv_floor", "-z": "rv_hall_deck" }, STONE )

    for r in ( LANDING, CONTROL, WALKWAY ):
        slab( r )
    inward = v( f, 0, 0 )
    right = np.cross( UP, inward )
    # The block (B1 west, B2 east), solid to the upper level.
    a, b = E( BLOCK[0], BLOCK[1] )
    box( m, a, b, BLOCK[2], BLOCK[3], 0, UPPER, { "default": IN, "+z": "rv_floor" }, STONE )
    face = f * BLOCK[1]
    mid_n = ( BLOCK[2] + BLOCK[3] ) / 2
    P.letters( m, "B1" if sx < 0 else "B2", ( face, mid_n, 176 ), right, 104, "dark" )
    P.life_ring( m, ( face, BLOCK[2] + 50, 70 ), inward )
    # A dummy door on the solid block, so it stands proud of the face (set back into it, the face hid it).
    P.door( m, ( face, BLOCK[3] - 70, 0 ), right, 60, 90, double=False, recess=-1.5 )
    P.wall_light( m, f"Block {sx} lamp", ( face, BLOCK[3] - 70, 104 ), inward, "warm", 260 )
    box( m, *E( BLOCK[1] - 2, BLOCK[1] + 1 ), BLOCK[2], BLOCK[3], UPPER - 14, UPPER, "rv_steel" )
    for n in ( BLOCK[2] + 18, BLOCK[2] + 32 ):
        P.pipe( m, [ ( face + f * 8, n, UPPER - 20 ), ( face + f * 8, n, 40 ), ( face + f * 30, n, 14 ) ], 3.2, "rv_pipe", 10 )
    # The control room: a knee wall and glazing on its pool side and its south side, a door from the landing, a wall and
    # a door to the walkway on its north side, the ceiling.
    c0, c1, cn0, cn1 = CONTROL
    ce = f * c1
    ea, eb = min( ce, ce - 14 * f ), max( ce, ce - 14 * f )
    knee, head = UPPER + 36, UPPER + 150
    box( m, ea, eb, cn0, cn1, UPPER, knee, IN, STONE )
    box( m, ea, eb, cn0, cn1, head, CONTROL_TOP, IN, STONE )
    for n in np.arange( cn0 + 2, cn1 + 1, 54.0 ):
        box( m, ea + 4, eb - 4, n - 2, n + 2, knee, head, "rv_frame" )
    box( m, ea - 1.5, eb + 1.5, cn0, cn1, knee - 2, knee + 2, "rv_frame" )
    door_e = ( -680.0, -610.0 )
    sa, sb = cn0, cn0 + 14
    for e0_, e1_ in ( ( c0, door_e[0] ), ( door_e[1], c1 ) ):
        box( m, *E( e0_, e1_ ), sa, sb, UPPER, knee, IN, STONE )
    box( m, *E( door_e[0], door_e[1] ), sa, sb, UPPER + 96, head, IN, STONE )
    box( m, *E( c0, c1 ), sa, sb, head, CONTROL_TOP, IN, STONE )
    for e in np.arange( c0 + 40, c1 - 10, 54.0 ):
        if door_e[0] - 6 < e < door_e[1] + 6:
            continue
        box( m, *E( e - 2, e + 2 ), sa + 4, sb - 4, knee, head, "rv_frame" )
    for e0_, e1_ in ( ( c0, door_e[0] ), ( door_e[1], c1 ) ):
        box( m, *E( e0_, e1_ ), sa - 1.5, sb + 1.5, knee - 2, knee + 2, "rv_frame" )
    wall( m, "e", *E( c0, c1 ), cn1 - 14, cn1, UPPER, CONTROL_TOP, [ ( *E( -970, -890 ), UPPER + 96 ) ], paint=IN )
    box( m, *E( c0, c1 ), cn0, cn1, CONTROL_TOP - 18, CONTROL_TOP, { "default": IN, "-z": "rv_steel" }, STONE )
    P.letters( m, "control_room", ( f * ( c0 + c1 ) / 2, cn0 - 0.3, head + 8 ), v( 1, 0, 0 ), 12, "light" )
    P.letters( m, "control_room", ( ce + f * 0.3, ( cn0 + cn1 ) / 2, head + 8 ), np.cross( UP, inward ), 12, "light" )
    P.LIGHTS.append( ( f"Control room {sx}", ( f * -780, 930.0, 410.0 ), "1.6,1.8,2.1,1", 520, True ) )
    for n in ( 760.0, 1100.0 ):
        P.LIGHTS.append( ( f"Control fill {sx} {n}", ( f * -780, n, 420.0 ), "1.1,1.25,1.45,1", 360, False ) )
    # The two rows of desks: their boxes (the consoles drawn in them are control_room's).
    for row_e in ( -860.0, -690.0 ):
        de = f * row_e
        m.collision_box( ( de - 14, 720, UPPER ), ( de + 14, 1140, UPPER + 30 ), METAL )
    # Columns under the control room and the landing.
    for e, n in CONTROL_COLUMNS:
        box( m, f * e - 12, f * e + 12, n - 12, n + 12, 0, UPPER - SLAB, IN, STONE )
    for n in np.arange( 1280, 1860, 160.0 ):
        if BLOCK[2] - 20 < n < BLOCK[3] + 20:
            continue
        x0, x1 = f * -1000, f * -870
        for dn in ( -3, 3 ):
            card( m, "rv_steel", [ v( x0, n + dn, UPPER - SLAB - 60 ), v( x0, n + dn, UPPER - SLAB ), v( x1, n + dn, UPPER - SLAB ) ], v( 0, dn, 0 ), both=True )
    # The stair from the south deck up to the landing, rails both sides.
    mid_e = f * ( STAIR[0] + STAIR[1] ) / 2
    P.stairs( m, ( mid_e, STAIR[2] ), ( mid_e, STAIR[3] ), STAIR[1] - STAIR[0], 0, UPPER, name=f"hall stair {sx}" )
    # Railings round the upper level's open edges (clipped well up).
    P.railing( m, mirror( [ ( -1000, 580 ), ( -760, 580 ) ], f ), UPPER, clip_to=180, name=f"landing rail a {sx}" )
    P.railing( m, mirror( [ ( -700, 580 ), ( -560, 580 ), ( -560, 660 ) ], f ), UPPER, clip_to=180, name=f"landing rail b {sx}" )
    P.railing( m, mirror( [ ( -860, 1200 ), ( -860, BLOCK[2] ), ( -640, BLOCK[2] ), ( -640, BLOCK[3] ), ( -860, BLOCK[3] ), ( -860, 1860 ),
                           ( -360, 1860 ) ], f ), UPPER, clip_to=200, name=f"upper rail {sx}" )
    # Lamps: under the walkway, on the side wall over the deck, at the landing.
    for n in ( 1400.0, 1780.0 ):
        P.wall_light( m, f"Deck lamp {sx} {n}", ( f * E0, n, UPPER - SLAB - 34 ), inward, "warm", 380 )
    for n in ( 150.0, 450.0 ):
        P.wall_light( m, f"Side lamp {sx} {n}", ( f * E0, n, 230 ), inward, "warm", 380 )
    P.wall_light( m, f"Landing lamp {sx}", ( f * E0, 620, UPPER + 110 ), inward, "warm", 300 )
    P.life_ring( m, ( f * E0, 300, 64 ), inward )
    control_room( d, fn, sx )
    control_back( d, fn, sx )
    under_upper( d, fn, sx )
    stair_detail( d, fn, sx )
    walkway_detail( d, fn, sx )
    block_detail( d, fn, sx )


def mirror( pts, f ):
    return [ ( f * p[0], p[1] ) for p in pts ]


_PENDING_LIGHTS = []


def console( d, fine, de, f, n0, n1, stations, supervisor=False, seed=0 ):
    """ A console in its desk's box ( de +- 14, n0..n1, 30 tall; drawn things above that are visual only): the operator
    sits on its -f side facing +f, toward the glass. A cabinet under the back of the worktop (knee space in front), end
    and middle pedestals, the worktop and its rubber edge, a sloped turret of button, meter and annunciator panels,
    monitors on arms, keyboards, mice, phones, papers and mugs. """
    z0 = UPPER
    rng = np.random.default_rng( seed )

    def E( off ):
        return de + f * off

    def ebox( m, o0, o1, a, b, za, zb, paints ):
        lo, hi = sorted( ( E( o0 ), E( o1 ) ) )
        box( m, lo, hi, a, b, za, zb, paints )

    zA, zB = z0 + 30, z0 + 40
    ebox( fine, -1.0, 13.0, n0 + 1, n1 - 1, z0, z0 + 3.5, "rv_black" )
    ebox( d, -2.0, 13.5, n0 + 1.6, n1 - 1.6, z0 + 3.5, z0 + 28, { "default": "rv_hall_console", "-z": None } )
    for nn in [ n0, n1 - 1.6 ] + [ n0 + ( n1 - n0 ) * k / 3 - 0.8 for k in ( 1, 2 ) ]:
        ebox( d, -13.5, 14.0, nn, nn + 1.6, z0, z0 + 28, "rv_hall_console_dark" )
    ebox( d, -15.0, 14.0, n0 - 0.5, n1 + 0.5, z0 + 28, z0 + 30, "rv_hall_worktop" )
    edge = Face( ( E( -15.0 ), 0 ), ( -f, 0 ) )
    edge.quad( fine, "rv_rubber", *edge.ss( ( E( -15 ), n0 - 0.5 ), ( E( -15 ), n1 + 0.5 ) ), z0 + 27.9, z0 + 30.1, 0.05 )
    body = Face( ( E( -2.0 ), 0 ), ( -f, 0 ) )
    for k in range( len( stations ) + 1 ):
        nn = n0 + 1.6 + ( n1 - n0 - 3.2 ) * k / len( stations )
        s = body.s_of( E( -2 ), nn )
        body.quad( fine, "rv_hall_joint", s - 0.25, s + 0.25, z0 + 4, z0 + 27.5, 0.05 )
    for k, nc in enumerate( stations ):
        s = body.s_of( E( -2 ), nc )
        body.quad( fine, "rv_hall_signs", s - 9, s + 9, z0 + 5, z0 + 11, 0.05, atlas_uv( "vent" ) )
    # Its back, toward the glass: the panels' seams, louvres low and high, a cable gland plate, the turret's grille.
    rear = Face( ( E( 13.5 ), 0 ), ( f, 0 ) )
    for k in range( len( stations ) + 1 ):
        nn = n0 + 1.6 + ( n1 - n0 - 3.2 ) * k / len( stations )
        s = rear.s_of( E( 13.5 ), nn )
        rear.quad( fine, "rv_hall_joint", s - 0.25, s + 0.25, z0 + 4, z0 + 27.5, 0.05 )
    for k, nc in enumerate( stations ):
        s = rear.s_of( E( 13.5 ), nc )
        rear.quad( fine, "rv_hall_signs", s - 14, s + 14, z0 + 5, z0 + 12, 0.05, atlas_uv( "vent" ) )
        rear.quad( fine, "rv_hall_signs", s - 14, s + 14, z0 + 19, z0 + 26, 0.05, atlas_uv( "vent" ) )
        rear.box( fine, s + 18, s + 26, z0 + 6, z0 + 10, 0, 0.6, "rv_hall_console_dark" )
        top = Face( ( E( 14.0 ), 0 ), ( f, 0 ) )
        top.quad( fine, "rv_hall_signs", s - 16, s + 16, zA + 2.5, zA + 7.5, 0.05, atlas_uv( "grille" ) )
    zA, zB = z0 + 30, z0 + 40
    lo, hi = n0 + 2, n1 - 2
    slope_n = unit( v( -f * 10, 0, 4 ) )
    card( d, "rv_hall_console_dark", [ v( E( 2 ), lo, zA ), v( E( 2 ), hi, zA ), v( E( 6 ), hi, zB ), v( E( 6 ), lo, zB ) ], slope_n )
    card( d, "rv_hall_console_dark", [ v( E( 6 ), lo, zB ), v( E( 6 ), hi, zB ), v( E( 14 ), hi, zB ), v( E( 14 ), lo, zB ) ], UP )
    card( d, "rv_hall_console_dark", [ v( E( 14 ), lo, zA ), v( E( 14 ), hi, zA ), v( E( 14 ), hi, zB ), v( E( 14 ), lo, zB ) ], v( f, 0, 0 ) )
    for nn, sg in ( ( lo, -1 ), ( hi, 1 ) ):
        card( d, "rv_hall_console_dark", [ v( E( 2 ), nn, zA ), v( E( 14 ), nn, zA ), v( E( 14 ), nn, zB ), v( E( 6 ), nn, zB ) ], v( 0, sg, 0 ) )
    panels = ( "buttons", "meters", "annunciator" )
    names = ( "schematic", "graphs", "table", "camera" )
    half = ( n1 - n0 ) / len( stations ) / 2 - 2.5
    for k, nc in enumerate( stations ):
        left, rgt = nc + half * f, nc - half * f
        off = slope_n * 0.06
        card( fine, "rv_hall_signs", [ v( E( 2 ), left, zA ) + off, v( E( 2 ), rgt, zA ) + off, v( E( 6 ), rgt, zB ) + off, v( E( 6 ), left, zB ) + off ],
              slope_n, uv=atlas_uv( panels[( k + seed ) % 3] ) )
        mons = [ ( nc + 12.5, 8.0 ), ( nc - 12.5, 8.0 ) ] if supervisor else [ ( nc, 9.0 ), ( nc + 24.5, 7.0 ), ( nc - 24.5, 7.0 ) ]
        op = v( E( -26 ), nc, z0 + 46 )
        for j, ( mn, mo ) in enumerate( mons ):
            centre = v( E( mo ), mn, z0 + 48.5 )
            look = op - centre
            monitor( d, fine, centre, ( look[0], look[1] ), names[( k + j + seed ) % len( names )], 12.0 )
        span = 12.5 if supervisor else 24.5
        P.rod( fine, ( E( 11.5 ), nc, zB ), ( E( 11.5 ), nc, z0 + 48.5 ), 0.8, "rv_hall_chrome", 6 )
        P.obox( fine, ( E( 11.5 ), nc, zB + 0.3 ), ( 1, 0 ), ( 5, 7, 0.6 ), "rv_hall_plastic" )
        bar( fine, ( E( 11.0 ), nc - span, z0 + 48.5 ), ( E( 11.0 ), nc + span, z0 + 48.5 ), 1.0, 1.0, "rv_hall_plastic" )
        kb = v( E( -7.5 ), nc, z0 + 30.35 )
        P.obox( fine, kb, ( 0, 1 ), ( 17.5, 6.5, 0.7 ), "rv_hall_plastic" )
        top_quad( fine, "rv_hall_signs", kb + UP * 0.37, ( f, 0 ), 17.5, 6.5, atlas_uv( "keyboard" ) )
        P.obox( fine, ( E( -7.5 ), nc - 13 * f, z0 + 30.5 ), ( f, 0 ), ( 4.2, 2.5, 1.0 ), "rv_hall_plastic" )
        if ( k + seed ) % 2 == 0:
            ph = v( E( -4 ), nc + 21 * f, z0 + 31.3 )
            P.obox( fine, ph, ( f, 0 ), ( 8, 7.5, 2.6 ), "rv_hall_plastic_grey" )
            bar( fine, ph + v( -f * 2.3, -3.4, 2.0 ), ph + v( -f * 2.3, 3.4, 2.0 ), 1.6, 1.2, "rv_hall_plastic" )
            top_quad( fine, "rv_hall_signs", ph + v( f * 1.6, 0, 1.32 ), ( f, 0 ), 3.4, 4.2, atlas_uv( "phone" ) )
        else:
            a = rng.normal( 0, 0.25 )
            top_quad( fine, "rv_hall_signs", ( E( -8 ), nc + 21 * f, z0 + 30.07 ), ( f * math.cos( a ), math.sin( a ) ), 8.5, 11, atlas_uv( "papers" ) )
        if rng.random() < 0.6:
            P.lathe( fine, ( E( -3 ), nc - 22 * f ), [ ( 1.5, z0 + 30 ), ( 1.7, z0 + 33.6 ) ], "rv_ring_white", 10, cap="rv_dark" )
    if supervisor:
        P.obox( fine, ( E( 4 ), n0 + 12, z0 + 33 ), ( 0, 1 ), ( 14, 9, 6 ), "rv_hall_signs" )
        top_quad( fine, "rv_hall_signs", ( E( 4 ), n0 + 12, z0 + 36.02 ), ( f, 0 ), 9, 14, atlas_uv( "binders", 0, 0, 0.5, 1 ) )
        P.plate( fine, "clipboard", ( E( -9 ), n1 - 30, z0 + 30.1 ), ( 0, -f, 0 ), 12, up=( f, 0, 0 ), off=0.05 )


def monitor( d, fine, centre, facing, name, sh=12.0 ):
    """ A flat monitor: its screen's centre, the way it faces (plan), the screen sh tall; its bezel and back. """
    out = unit( v( facing[0], facing[1], 0.0 ) )
    right = np.cross( UP, out )
    sw = sh * RM.aspect( RM.SCREENS, name )
    c = v( *centre )
    P.obox( d, c - out * 0.75, right, ( sw + 1.4, 1.5, sh + 1.4 ), "rv_hall_bezel" )
    P.obox( d, c - out * 2.0, right, ( sw * 0.6, 1.2, sh * 0.5 ), "rv_hall_plastic" )
    P.screen( fine, name, c, right, sh, off=0.06 )


def chair( d, at, facing, z0, seed ):
    """ An office chair: five-star base on casters, gas column, seat, tilted back on its spine, armrests. """
    rng = np.random.default_rng( seed )
    yaw = rng.normal( 0, 0.35 )
    fw = unit( v( facing[0], facing[1], 0.0 ) )
    fw = v( fw[0] * math.cos( yaw ) - fw[1] * math.sin( yaw ), fw[0] * math.sin( yaw ) + fw[1] * math.cos( yaw ), 0 )
    side = np.cross( UP, fw )
    c = v( at[0], at[1], 0 ) + fw * rng.normal( 0, 3 ) + side * rng.normal( 0, 3 )
    spin = rng.uniform( 0, 2 * math.pi / 5 )
    for k in range( 5 ):
        a = spin + 2 * math.pi * k / 5
        dk = v( math.cos( a ), math.sin( a ), 0 )
        bar( d, c + dk * 1.5 + UP * ( z0 + 3.2 ), c + dk * 11.5 + UP * ( z0 + 2.2 ), 1.6, 1.1, "rv_hall_plastic" )
        P.cylinder( d, c + dk * 11.5, 1.0, z0, z0 + 1.6, "rv_black", 6, top="rv_black" )
    P.rod( d, c + UP * ( z0 + 3 ), c + UP * ( z0 + 10 ), 1.4, "rv_black", 8 )
    P.rod( d, c + UP * ( z0 + 10 ), c + UP * ( z0 + 15.5 ), 0.9, "rv_hall_chrome", 8 )
    P.obox( d, c + UP * ( z0 + 15.6 ), side, ( 14, 12, 1.0 ), "rv_hall_plastic" )
    P.obox( d, c + UP * ( z0 + 17.6 ), side, ( 19.5, 18.5, 3.2 ), "rv_hall_fabric" )
    t = math.radians( 12 )
    zt = unit( UP * math.cos( t ) - fw * math.sin( t ) )
    d.oriented_box( c - fw * 9.0 + UP * ( z0 + 31 ), ( side, np.cross( zt, side ), zt ), ( 17.5, 2.6, 19 ), "rv_hall_fabric" )
    bar( d, c - fw * 4 + UP * ( z0 + 16.8 ), c - fw * 8.8 + UP * ( z0 + 23 ), 2.4, 0.8, "rv_hall_plastic", hint=fw )
    for sg in ( -1, 1 ):
        b = c + side * sg * 10.3
        bar( d, b + UP * ( z0 + 18.5 ), b - fw * 1 + UP * ( z0 + 25 ), 1.2, 1.0, "rv_hall_plastic" )
        bar( d, b - fw * 5 + UP * ( z0 + 25.6 ), b + fw * 5 + UP * ( z0 + 25.6 ), 2.4, 1.2, "rv_hall_plastic" )


def control_room( d, fine, sx ):
    """ One control room's fit-out (sx -1 west, 1 east; the numbers are the west room's, mirrored by e -> -e): an access
    floor, a suspended ceiling with light panels, diffusers, detectors and sprinkler heads, painted walls on a rubber
    skirting, two rows of consoles facing the glass with chairs, cabinets and a mimic board set into the back wall, a
    video wall and a clock on the north wall, a convector and sill under the pool-side glazing, door frames, an exit
    sign and an extinguisher. """
    f = -sx
    c0, c1, cn0, cn1 = CONTROL
    z0, zc = UPPER, CEILING_Z
    kn, sn, nn = c1 - 14.0, cn0 + 14.0, cn1 - 14.0

    def X( e ):
        return f * e

    back = Face( ( X( c0 ), 0 ), ( f, 0 ) )
    knee = Face( ( X( kn ), 0 ), ( -f, 0 ) )
    south = Face( ( 0, sn ), ( 0, 1 ) )
    north = Face( ( 0, nn ), ( 0, -1 ) )
    door_s, door_n = ( -680.0, -610.0 ), ( -970.0, -890.0 )
    head = UPPER + 150
    # The floor and the ceiling.
    card( fine, "rv_hall_access", [ v( X( c0 ), sn, z0 + 0.12 ), v( X( kn ), sn, z0 + 0.12 ), v( X( kn ), nn, z0 + 0.12 ), v( X( c0 ), nn, z0 + 0.12 ) ], UP )
    card( d, "rv_hall_ceiling", [ v( X( c0 ), sn, zc ), v( X( kn ), sn, zc ), v( X( kn ), nn, zc ), v( X( c0 ), nn, zc ) ], -UP )
    for door, n_a, n_b in ( ( door_n, nn, cn1 ), ( door_s, cn0, sn ) ):
        card( fine, "rv_stainless", [ v( X( door[0] ), n_a, z0 + 0.15 ), v( X( door[1] ), n_a, z0 + 0.15 ), v( X( door[1] ), n_b, z0 + 0.15 ),
                                           v( X( door[0] ), n_b, z0 + 0.15 ) ], UP )
    for e in ( -925.0, -790.0, -655.0 ):
        for n in ( 742.0, 845.0, 948.0, 1051.0, 1140.0 ):
            c = v( X( e ), n, zc - 0.1 )
            P.quad( d, "rv_hall_console", c, ( 1, 0, 0 ), ( 0, -1, 0 ), 25, 49 )
            P.quad( fine, "rv_hall_troffer", c - UP * 0.1, ( 1, 0, 0 ), ( 0, -1, 0 ), 22, 46 )
            for k in ( -1, 1 ):
                P.quad( fine, "rv_hall_console", c - UP * 0.2 + v( k * 5.5, 0, 0 ), ( 1, 0, 0 ), ( 0, -1, 0 ), 0.8, 46 )
    for e, n in ( ( -860.0, 795.0 ), ( -860.0, 1095.0 ), ( -720.0, 795.0 ), ( -720.0, 1095.0 ) ):
        P.quad( fine, "rv_hall_signs", v( X( e ), n, zc - 0.12 ), ( 1, 0, 0 ), ( 0, -1, 0 ), 24, 24, atlas_uv( "diffuser" ) )
    for e, n in ( ( -790.0, 896.0 ), ( -925.0, 1000.0 ), ( -655.0, 700.0 ) ):
        P.lathe( fine, ( X( e ), n ), [ ( 1.0, zc - 1.8 ), ( 2.6, zc - 1.5 ), ( 2.8, zc - 0.4 ), ( 2.8, zc ) ], "rv_hall_equipment", 10 )
        disc( fine, "rv_hall_equipment", ( X( e ), n, zc - 1.8 ), -UP, 1.0, 8 )
    for e in ( -860.0, -720.0 ):
        for n in ( 700.0, 896.0, 1160.0 ):
            P.rod( fine, ( X( e ), n, zc ), ( X( e ), n, zc - 1.2 ), 0.25, "rv_hall_chrome", 4 )
            disc( fine, "rv_hall_chrome", ( X( e ), n, zc - 1.25 ), -UP, 0.8, 6 )
    # Walls: paint above a rubber skirting.
    sk = 4.0
    for face, runs in ( ( back, [ ( ( X( c0 ), sn ), ( X( c0 ), nn ), z0, zc ) ] ),
                        ( north, [ ( ( X( c0 ), nn ), ( X( door_n[0] ), nn ), z0, zc ), ( ( X( door_n[1] ), nn ), ( X( kn ), nn ), z0, zc ),
                                   ( ( X( door_n[0] ), nn ), ( X( door_n[1] ), nn ), z0 + 96, zc ) ] ),
                        ( south, [ ( ( X( c0 ), sn ), ( X( door_s[0] ), sn ), z0, z0 + 36 ), ( ( X( door_s[1] ), sn ), ( X( kn ), sn ), z0, z0 + 36 ),
                                   ( ( X( door_s[0] ), sn ), ( X( door_s[1] ), sn ), z0 + 96, zc ), ( ( X( c0 ), sn ), ( X( kn ), sn ), head, zc ) ] ),
                        ( knee, [ ( ( X( kn ), sn ), ( X( kn ), nn ), z0, z0 + 36 ), ( ( X( kn ), sn ), ( X( kn ), nn ), head, zc ) ] ) ):
        for pa, pb, za, zb in runs:
            s0, s1 = face.ss( pa, pb )
            face.quad( fine, "rv_hall_interior", s0, s1, max( za, z0 + sk ), zb, 0.2 )
            if za == z0:
                face.quad( fine, "rv_rubber", s0, s1, z0, z0 + sk, 0.45 )
    for pa, pb in ( ( ( X( c0 ), sn ), ( X( kn ), sn ) ), ( ( X( c0 ), nn ), ( X( kn ), nn ) ) ):
        card( fine, "rv_hall_console", [ v( pa[0], pa[1], zc - 0.05 ), v( pb[0], pb[1], zc - 0.05 ), v( pb[0], pb[1] + ( 1.2 if pa[1] == sn else -1.2 ), zc - 0.05 ),
                                         v( pa[0], pa[1] + ( 1.2 if pa[1] == sn else -1.2 ), zc - 0.05 ) ], -UP )
    for e_ in ( c0, kn ):
        card( fine, "rv_hall_console", [ v( X( e_ ), sn, zc - 0.05 ), v( X( e_ ), nn, zc - 0.05 ), v( X( e_ ) + f * ( 1.2 if e_ == c0 else -1.2 ), nn, zc - 0.05 ),
                                         v( X( e_ ) + f * ( 1.2 if e_ == c0 else -1.2 ), sn, zc - 0.05 ) ], -UP )
    # Door frames inside, an exit sign over the walkway door and an extinguisher beside it.
    door_frame( fine, north, *north.ss( ( X( door_n[0] ), nn ), ( X( door_n[1] ), nn ) ), z0 + 96, z0=z0 )
    door_frame( fine, south, *south.ss( ( X( door_s[0] ), sn ), ( X( door_s[1] ), sn ) ), z0 + 96, z0=z0 )
    exit_sign( d, fine, north, north.s_of( X( -930 ), nn ), z0 + 106, 14 )
    extinguisher( d, fine, north, north.s_of( X( -872 ), nn ), z0 + 26 )
    # Under the pool-side glazing: a convector with its grille, a sill board; head rails over both glazings.
    s0, s1 = knee.ss( ( X( kn ), sn ), ( X( kn ), nn ) )
    knee.box( d, s0 + 16, s1 - 16, z0 + 4, z0 + 26, 0, 5.5, "rv_hall_equipment" )
    for s in np.arange( s0 + 20, s1 - 50, 42.0 ):
        card( fine, "rv_hall_signs", [ knee.p( s, z0 + 26.04, 0.6 ), knee.p( s + 38, z0 + 26.04, 0.6 ), knee.p( s + 38, z0 + 26.04, 4.9 ),
                                       knee.p( s, z0 + 26.04, 4.9 ) ], UP, uv=atlas_uv( "grille" ) )
    knee.box( d, s0, s1, z0 + 38, z0 + 39.4, -1.5, 7.5, "rv_hall_worktop" )
    ea, eb = sorted( ( X( c1 ), X( kn ) ) )
    box( d, ea + 4, eb - 4, cn0, cn1, head - 2.5, head, "rv_frame" )
    box( d, *sorted( ( X( c0 ), X( c1 ) ) ), cn0 + 4, cn0 + 10, head - 2.5, head, "rv_frame" )
    # Consoles: five operators at the front row, a supervisor's four at the back; their chairs.
    for row_e, count, sup in ( ( -690.0, 6, False ), ( -860.0, 4, True ) ):
        stations = [ 720 + ( 1140 - 720 ) * ( k + 0.5 ) / count for k in range( count ) ]
        console( d, fine, X( row_e ), f, 720.0, 1140.0, stations, supervisor=sup, seed=int( 3 * ( row_e < -800 ) + ( sx > 0 ) ) )
        for k, nc in enumerate( stations ):
            chair( d, ( X( row_e - 27 ), nc ), ( f, 0 ), z0, seed=int( 100 + k + 10 * sup + 50 * ( sx > 0 ) ) )
    # The back wall: cabinets set into it either side of the mimic board.
    s_m0, s_m1 = back.ss( ( X( c0 ), 810.0 ), ( X( c0 ), 1050.0 ) )
    zm0, zm1 = z0 + 24, z0 + 144
    back.box( d, s_m0 - 2, s_m1 + 2, zm0 - 2, zm1 + 2, 0, 2.5, "rv_hall_console_dark" )
    back.quad( fine, "rv_hall_signs", s_m0, s_m1, zm0, zm1, 2.56, atlas_uv( "mimic" ) )
    for u, vv, col in MIMIC_LAMPS:
        s, z = s_m0 + u * ( s_m1 - s_m0 ), zm0 + vv * ( zm1 - zm0 )
        back.quad( fine, f"rv_hall_led_{col}", s - 0.9, s + 0.9, z - 0.9, z + 0.9, 2.62 )
    rng = np.random.default_rng( 40 + sx )
    for bank in ( ( 684.0, 756.0 ), ( 1104.0, 1176.0 ) ):
        b0, b1 = back.ss( ( X( c0 ), bank[0] ), ( X( c0 ), bank[1] ) )
        for k in range( 3 ):
            s0_ = b0 + ( b1 - b0 ) * k / 3
            s1_ = b0 + ( b1 - b0 ) * ( k + 1 ) / 3
            back.box( d, s0_ + 0.2, s1_ - 0.2, z0, z0 + 84, 0, 2.2, "rv_hall_console_dark" )
            back.quad( fine, "rv_hall_signs", s0_ + 1.2, s1_ - 1.2, z0 + 4, z0 + 80, 2.25, atlas_uv( "rack" ) )
            for j in range( 3 ):
                col = ( "green", "green", "amber" )[int( rng.integers( 0, 3 ) )]
                s = s0_ + 4 + j * 2.6
                back.quad( fine, f"rv_hall_led_{col}", s - 0.5, s + 0.5, z0 + 75.5, z0 + 76.5, 2.3 )
        back.box( d, b0 - 1.5, b1 + 1.5, z0 + 84, z0 + 90, 0, 3.0, "rv_hall_console" )
    # The north wall: a video wall of four displays, a clock over it.
    sc = north.s_of( X( -760 ), nn )
    north.box( d, sc - 48, sc + 48, z0 + 45, z0 + 103, 0, 0.8, "rv_hall_console_dark" )
    for dx, dz, name in ( ( -23.6, 14.2, "camera" ), ( 23.6, 14.2, "schematic" ), ( -23.6, -14.2, "graphs" ), ( 23.6, -14.2, "table" ) ):
        zz = z0 + 74 + dz
        north.box( d, sc + dx - 23.3, sc + dx + 23.3, zz - 13.8, zz + 13.8, 0.8, 3.0, "rv_hall_bezel" )
        sw = 25.0 * RM.aspect( RM.SCREENS, name )
        north.quad( fine, "rv_screens", sc + dx - sw / 2, sc + dx + sw / 2, zz - 12.5, zz + 12.5, 3.06, screen_uv( name ) )
    north.box( d, sc - 7.5, sc + 7.5, z0 + 116, z0 + 131, 0, 1.2, "rv_hall_plastic" )
    north.quad( fine, "rv_hall_signs", sc - 7, sc + 7, z0 + 116.5, z0 + 130.5, 1.25, atlas_uv( "clock" ) )
    # Outside: the room's plate over its landing door.
    outside = Face( ( 0, cn0 ), ( 0, -1 ) )
    sign_on( fine, outside, "control_plate", outside.s_of( X( -645 ), cn0 ), z0 + 118, 8 )
    _PENDING_LIGHTS.append( ( f"Control screens {sx}", ( X( -955 ), 930.0, 370.0 ), "0.30,0.42,0.60,1", 240, False ) )


def control_back( d, fine, sx ):
    """ The control room's back wall where the walkway passes it (the room's north wall's outside): an epoxy band, its
    door's frame and plate, a distribution board fed from a cable tray, a notice board, an extinguisher, a galvanised
    supply duct along the top on brackets, and a camera on the corner looking down the walkway. Drawn only: before, the
    walkway saw 440 x 180 in of bare wall. """
    f = -sx
    c0, c1, cn0, cn1 = CONTROL

    def X( e ):
        return f * e

    face = Face( ( 0, cn1 ), ( 0, 1 ) )

    def S( e ):
        return face.s_of( X( e ), cn1 )

    z0 = UPPER
    door = sorted( ( S( -970.0 ), S( -890.0 ) ) )
    wall0, wall1 = sorted( ( S( c0 + 2.0 ), S( c1 - 2.0 ) ) )
    dado( fine, face, wall0, door[0] - 4.0, z0 )
    dado( fine, face, door[1] + 4.0, wall1, z0 )
    door_frame( d, face, door[0], door[1], z0 + 96.0, z0=z0 )
    sign_on( fine, face, "control_plate", ( door[0] + door[1] ) / 2, z0 + 106.0, 7.0 )
    tray = ( z0 + 118.0, 13.0 )
    ladder_tray( d, fine, face, wall0 + 4.0, wall1 - 4.0, tray[0], 2.0, tray[1], cables=4 )
    wall_panel( d, fine, face, S( -760.0 ), z0 + 40.0, tag="db3", tray=tray )
    notice_board( d, fine, face, S( -670.0 ), z0 + 58.0 )
    extinguisher( d, fine, face, S( -850.0 ), z0 + 30.0 )
    # The duct: 16 x 22 in galvanised, its joints' flanges every 48 in, on brackets off the wall, turning into the wall
    # at the room's pool end through a collar.
    dz0, dz1, dd0, dd1 = z0 + 136.0, z0 + 158.0, 3.0, 19.0
    face.box( d, wall0 + 6.0, wall1 - 6.0, dz0, dz1, dd0, dd1, "rv_galv" )
    for s in np.arange( wall0 + 30.0, wall1 - 10.0, 48.0 ):
        face.box( fine, s - 0.6, s + 0.6, dz0 - 0.8, dz1 + 0.8, dd0 - 0.2, dd1 + 0.8, "rv_galv" )
    for s in np.arange( wall0 + 40.0, wall1 - 20.0, 96.0 ):
        bar( d, face.p( s, dz0 - 1.0, 0.0 ), face.p( s, dz0 - 1.0, dd1 + 1.0 ), 1.6, 1.6, "rv_galv" )
        bar( d, face.p( s, dz0 - 14.0, 0.0 ), face.p( s, dz0 - 1.6, dd1 * 0.7 ), 1.2, 1.2, "rv_galv" )
    end = wall0 + 6.0 if f > 0 else wall1 - 6.0
    face.box( fine, end - 1.5, end + 1.5, dz0 - 1.5, dz1 + 1.5, 0.0, dd1 + 1.5, "rv_galv" )
    camera( d, fine, face, wall1 - 10.0 if f > 0 else wall0 + 10.0, z0 + 160.0, ( X( -760.0 ), 1700.0, z0 ) )


def under_upper( d, fine, sx ):
    """ Under one side's upper level: girders on the columns' lines, joists across, the walkway's edge beam; hazard
    wraps, corner guards and caps on the columns. """
    f = -sx

    def X( e ):
        return f * e

    zs = UPPER - SLAB
    for ec in ( -572.0, -830.0 ):
        wide_flange( d, ( X( ec ), LANDING[2], zs - 9 ), ( X( ec ), CONTROL[3], zs - 9 ), 18, 7.5, "rv_steel", web=0.45, flange=0.7 )
    for n in np.arange( LANDING[2] + 30, CONTROL[3] - 10, 60.0 ):
        channel( d, ( X( E0 ), n, zs - 6 ), ( X( -560 ), n, zs - 6 ), 12, 3, "rv_steel", t=0.35 )
    for n0, n1 in ( ( WALKWAY[2], BLOCK[2] ), ( BLOCK[3], WALKWAY[3] ) ):
        wide_flange( d, ( X( -866 ), n0, zs - 6 ), ( X( -866 ), n1, zs - 6 ), 12, 6.5, "rv_steel" )
    for e, n in CONTROL_COLUMNS:
        ce = X( e )
        for out in ( ( 1, 0 ), ( -1, 0 ), ( 0, 1 ), ( 0, -1 ) ):
            face = Face( ( ce + out[0] * 12, n + out[1] * 12 ), out )
            face.quad( fine, "rv_hazard", -12, 12, 0, 40, 0.25 )
        for cx, cy in ( ( 1, 1 ), ( 1, -1 ), ( -1, 1 ), ( -1, -1 ) ):
            p = v( ce + cx * 12.35, n + cy * 12.35, 0 )
            angle_iron( fine, p, p + UP * 48, 3.0, "rv_steel", ( -cx, 0, 0 ), ( 0, -cy, 0 ), t=0.35 )
        box( d, ce - 14, ce + 14, n - 14, n + 14, zs - 20, zs - 18, "rv_steel" )
    # Battens under the soffits, by the lamps.
    for n in ( 640.0, 1010.0 ):
        P.ceiling_light( fine, f"soffit {sx} {n}", ( X( -700 ), n, zs - 14 ), ( 1, 0 ), "cool", light=False, size=( 40, 6, 3 ) )


def stair_detail( d, fine, sx ):
    """ One stair's finish: channel flanges on its strings, yellow nosings on its treads, posts and a beam under it
    (inside its wedge, so drawn only). """
    f = -sx
    mid_e = f * ( STAIR[0] + STAIR[1] ) / 2
    foot, head = v( mid_e, STAIR[2], 0 ), v( mid_e, STAIR[3], 0 )
    width = STAIR[1] - STAIR[0]
    dv = v( 0, 1, 0 )
    s = np.cross( UP, dv ) * ( width / 2 )
    steps = max( 2, int( round( UPPER / 7.5 ) ) )
    rise, going = UPPER / steps, ( STAIR[3] - STAIR[2] ) / steps
    for i in range( steps ):
        p = foot + dv * ( going * i )
        zt = rise * ( i + 1 ) + 0.06
        card( fine, "rv_line_yellow", [ p - s * 0.97 + UP * zt, p + s * 0.97 + UP * zt, p + s * 0.97 + dv * 1.8 + UP * zt,
                                              p - s * 0.97 + dv * 1.8 + UP * zt ], UP )
    for sgn in ( -1, 1 ):
        o = s * sgn * 1.02
        ou = unit( o )
        for a, b in ( ( foot + o, head + o + UP * ( UPPER - 10 ) ), ( foot + o + UP * ( rise + 3 ), head + o + UP * ( UPPER + 3 ) ) ):
            bar( d, a + ou * 1.6, b + ou * 1.6, 3.2, 0.5, "rv_yellow" )
    for n_ in ( 330.0, 470.0 ):
        zb = ( n_ - STAIR[2] ) / ( STAIR[3] - STAIR[2] ) * ( UPPER - 10 ) - 2
        for sgn in ( -1, 1 ):
            e_ = mid_e + sgn * 25
            box( d, e_ - 3, e_ + 3, n_ - 3, n_ + 3, 0, zb, "rv_yellow" )
            box( fine, e_ - 5, e_ + 5, n_ - 5, n_ + 5, 0, 0.8, "rv_steel" )
        bar( d, ( mid_e - 25, n_, zb - 3 ), ( mid_e + 25, n_, zb - 3 ), 3, 6, "rv_yellow" )


def walkway_detail( d, fine, sx ):
    """ One side's upper level edges: steel fascias on the slabs' open edges, nosings on the block's, and a yellow line
    a few inches in from each. """
    f = -sx

    def X( e ):
        return f * e

    zs = UPPER - SLAB
    paint = "rv_line_yellow"

    def line( pa, pb, w=3.0 ):
        a, b = v( pa[0], pa[1], UPPER + 0.15 ), v( pb[0], pb[1], UPPER + 0.15 )
        side = unit( np.cross( UP, b - a ) ) * ( w / 2 )
        card( fine, paint, [ a - side, b - side, b + side, a + side ], UP )

    line( ( X( -866 ), WALKWAY[2] + 6 ), ( X( -866 ), BLOCK[2] - 6 ) )
    line( ( X( -866 ), BLOCK[3] + 6 ), ( X( -866 ), WALKWAY[3] - 6 ) )
    line( ( X( -866 ), BLOCK[2] + 6 ), ( X( -646 ), BLOCK[2] + 6 ) )
    line( ( X( -646 ), BLOCK[2] + 6 ), ( X( -646 ), BLOCK[3] - 6 ) )
    line( ( X( -646 ), BLOCK[3] - 6 ), ( X( -866 ), BLOCK[3] - 6 ) )
    line( ( X( -1000 ), LANDING[2] + 6 ), ( X( -764 ), LANDING[2] + 6 ) )
    line( ( X( -696 ), LANDING[2] + 6 ), ( X( -566 ), LANDING[2] + 6 ) )
    line( ( X( -566 ), LANDING[2] + 6 ), ( X( -566 ), LANDING[3] ) )
    walk = Face( ( X( -860 ), 0 ), ( f, 0 ) )
    for n0, n1 in ( ( WALKWAY[2], BLOCK[2] ), ( BLOCK[3], WALKWAY[3] ) ):
        walk.quad( fine, "rv_steel", *walk.ss( ( X( -860 ), n0 ), ( X( -860 ), n1 ) ), zs, UPPER + 0.5, 0.3 )
    land = Face( ( 0, LANDING[2] ), ( 0, -1 ) )
    land.quad( fine, "rv_steel", *land.ss( ( X( -1000 ), LANDING[2] ), ( X( -560 ), LANDING[2] ) ), zs, UPPER + 0.5, 0.3 )
    lend = Face( ( X( -560 ), 0 ), ( f, 0 ) )
    lend.quad( fine, "rv_steel", *lend.ss( ( X( -560 ), LANDING[2] ), ( X( -560 ), LANDING[3] ) ), zs, UPPER + 0.5, 0.3 )
    blk = Face( ( X( BLOCK[1] ), 0 ), ( f, 0 ) )
    blk.box( fine, *blk.ss( ( X( BLOCK[1] ), BLOCK[2] ), ( X( BLOCK[1] ), BLOCK[3] ) ), UPPER - 3, UPPER + 0.4, 0, 0.6, "rv_steel" )
    for n, out in ( ( BLOCK[2], ( 0, -1 ) ), ( BLOCK[3], ( 0, 1 ) ) ):
        side = Face( ( 0, n ), out )
        side.box( fine, *side.ss( ( X( -860 ), n ), ( X( BLOCK[1] ), n ) ), UPPER - 3, UPPER + 0.4, 0, 0.6, "rv_steel" )


def block_detail( d, fine, sx ):
    """ One block's faces (B1 west, B2 east): the epoxy band, precast panel joints, its door's frame, a filter room
    plate, a radiation monitor, an extinguisher and a camera on its corner. """
    f = -sx

    def X( e ):
        return f * e

    blk = Face( ( X( BLOCK[1] ), 0 ), ( f, 0 ) )
    door_n = ( BLOCK[3] - 100.0, BLOCK[3] - 40.0 )
    s0, s1 = blk.ss( ( X( BLOCK[1] ), BLOCK[2] ), ( X( BLOCK[1] ), BLOCK[3] ) )
    d0, d1 = blk.ss( ( X( BLOCK[1] ), door_n[0] - 4 ), ( X( BLOCK[1] ), door_n[1] + 4 ) )
    dado( fine, blk, s0, d0 )
    dado( fine, blk, d1, s1 )
    for n in ( BLOCK[2] + 84.0, BLOCK[3] - 112.0 ):
        s = blk.s_of( X( BLOCK[1] ), n )
        blk.quad( fine, "rv_hall_joint", s - 0.4, s + 0.4, 56, UPPER - 3, 0.25 )
    for z in ( 116.0, 244.0 ):
        blk.quad( fine, "rv_hall_joint", s0, s1, z - 0.4, z + 0.4, 0.25 )
    plate = "filter_b1" if sx < 0 else "filter_b2"
    sign_on( fine, blk, plate, blk.s_of( X( BLOCK[1] ), BLOCK[3] - 125 ), 62, 7 )
    radiation_monitor( d, fine, blk, blk.s_of( X( BLOCK[1] ), BLOCK[2] + 20 ), 150 )
    extinguisher( d, fine, blk, blk.s_of( X( BLOCK[1] ), BLOCK[3] - 19 ), 30 )
    camera( d, fine, blk, blk.s_of( X( BLOCK[1] ), BLOCK[2] + 6 ), 262, ( 0, 900, 0 ) )
    for n, out in ( ( BLOCK[2], ( 0, -1 ) ), ( BLOCK[3], ( 0, 1 ) ) ):
        side = Face( ( 0, n ), out )
        a, b = side.ss( ( X( BLOCK[0] ), n ), ( X( BLOCK[1] ), n ) )
        dado( fine, side, a, b )
        for z in ( 116.0, 244.0 ):
            side.quad( fine, "rv_hall_joint", a, b, z - 0.4, z + 0.4, 0.25 )


def north_wall( m, detail=None, fine=None ):
    """ The north wall's inside: its walkway and railing, doors on both levels, pipes, lamps, the logo and slogans;
    with detail and fine, the walkway's edge beam, joists, fascia and line, and the pool's name over the deck. """
    d = detail if detail is not None else m
    fn = fine if fine is not None else d
    box( m, NORTH_WALK[0], NORTH_WALK[1], NORTH_WALK[2], NORTH_WALK[3], UPPER - SLAB, UPPER, { "default": indoor(), "+z": "rv_floor", "-z": "rv_hall_deck" }, STONE )
    P.railing( m, [ ( -360, NORTH_WALK[2] ), ( 360, NORTH_WALK[2] ) ], UPPER, clip_to=200, name="north rail" )
    face = N1
    out = v( 0, -1, 0 )
    right = np.cross( UP, out )
    for e in ( -680.0, -330.0, 330.0, 680.0 ):
        # Dummy doors on the solid wall, so they stand proud of it (set back into it, the wall hid them).
        P.door( m, ( e, face, UPPER ), right, 72, 90, double=False, recess=-1.5 )
        P.wall_light( m, f"Upper door lamp {e}", ( e, face, UPPER + 110 ), out, "warm", 300 )
    for o in NORTH_DOORS:
        e = ( o[0] + o[1] ) / 2
        P.wall_light( m, f"North door lamp {e}", ( e, face, 150 ), out, "warm", 320 )
    for e in ( -680.0, -200.0, 200.0, 680.0 ):
        P.wall_light( m, f"North deck lamp {e}", ( e, face, UPPER - SLAB - 30 ), out, "warm", 340 )
    # The logo between the slogans, as the reference's far wall.
    P.letters( m, "logo", ( 0, face, 700 ), right, 270, "dark" )
    # Each in its bay between the pilasters (e +-167 and +-500, 48 wide).
    P.letters( m, "clean_energy", ( -333, face, 700 ), right, 165, "dark" )
    P.letters( m, "safety", ( 333, face, 700 ), right, 200, "dark" )
    for e0 in NORTH_BUNDLES:
        for k, ( dx, r ) in enumerate( ( ( -26, 7.0 ), ( -8, 9.0 ), ( 12, 6.0 ), ( 30, 11.0 ) ) ):
            x = e0 + dx
            P.pipe( m, [ ( x, face - 16 - k % 2 * 6, UPPER + 100 ), ( x, face - 16 - k % 2 * 6, TOP - 10 ) ], r, "rv_pipe", 12, caps=False )
        for z in np.arange( UPPER + 160, TOP, 180.0 ):
            box( m, e0 - 40, e0 + 40, face - 32, face, z, z + 3, "rv_steel" )
    for n_off, r in ( ( 10, 4.0 ), ( 22, 5.5 ) ):
        P.pipe( m, [ ( E0 + n_off, N0 + 200, 236 + r ), ( E0 + n_off, N1 - n_off, 236 + r ), ( E1 - n_off, N1 - n_off, 236 + r ),
                     ( E1 - n_off, N0 + 200, 236 + r ) ], r, "rv_pipe", 10 )
    for sx in ( -1, 1 ):
        for n0 in SIDE_RISERS[::-1]:
            for k, ( dx, r ) in enumerate( ( ( 8, 7.0 ), ( 26, 9.0 ), ( 44, 6.0 ) ) ):
                e = sx * ( E1 - dx - 4 )
                z0 = UPPER + 120 if n0 > 1000 else 40
                P.pipe( m, [ ( e, n0 + k * 22, z0 ), ( e, n0 + k * 22, TOP - 10 ) ], r, "rv_pipe", 12, caps=False )
    for e in ( -260.0, 260.0 ):
        P.life_ring( m, ( e, face, 64 ), out )
    # The walkway's steel: an edge beam, joists to the wall, a fascia; its edge line; the pool's name over the deck.
    zs = UPPER - SLAB
    wide_flange( d, ( E0, NORTH_WALK[2] + 6, zs - 6 ), ( E1, NORTH_WALK[2] + 6, zs - 6 ), 12, 6.5, "rv_steel" )
    for e in np.arange( E0 + 60, E1, 120.0 ):
        channel( d, ( e, NORTH_WALK[2] + 6, zs - 5 ), ( e, N1, zs - 5 ), 10, 2.6, "rv_steel", t=0.35 )
    edge = Face( ( 0, NORTH_WALK[2] ), ( 0, -1 ) )
    edge.quad( fn, "rv_steel", *edge.ss( ( -860, NORTH_WALK[2] ), ( 860, NORTH_WALK[2] ) ), zs, UPPER + 0.5, 0.3 )
    for a, b in ( ( -860.0, 860.0 ), ):
        card( fn, "rv_line_yellow", [ v( a, NORTH_WALK[2] + 4.5, UPPER + 0.15 ), v( b, NORTH_WALK[2] + 4.5, UPPER + 0.15 ),
                                            v( b, NORTH_WALK[2] + 7.5, UPPER + 0.15 ), v( a, NORTH_WALK[2] + 7.5, UPPER + 0.15 ) ], UP )
    P.letters( fn, "pool_level", ( 0, face, 205 ), right, 22, "dark" )


def deck_props( m, dress, detail=None, fine=None ):
    """ The pool's railing and its signs, the tanks, the cases, the floor's gratings and line; with detail and fine,
    the tanks' fittings and the transfer pump on its skid. """
    d = detail if detail is not None else dress
    fn = fine if fine is not None else d
    c = v( *POOL, 0 )
    pts = ring( c, POOL_R + 10, 0, 2 * math.pi, 49 )[:-1]
    P.railing( m, [ ( p[0], p[1] ) for p in pts ], 3, clip_to=997, closed=True, name="pool rail", post_every=56 )
    for a_deg in ( 255.0, 285.0, 75.0, 180.0, 0.0 ):
        a = math.radians( a_deg )
        dd = v( math.cos( a ), math.sin( a ), 0 )
        at = c + dd * ( POOL_R + 11.5 ) + UP * 26
        P.plate( m, "caution", at, np.cross( UP, dd ), 24, back="rv_yellow" )
    # The water purification tanks on the south-east deck, their name towards the hall's south end.
    for k, ( e, n ) in enumerate( TANKS ):
        P.tank( dress, ( e, n ), TANK_R, TANK_H, "rv_white", facing=( -0.6, -1 ), letters_name="water_purification" if k == 0 else None )
        P.pipe( dress, [ ( e, n, TANK_H + 20 ), ( e, n, TANK_H + 60 ), ( E1 - 30, n, TANK_H + 60 ) ], 6.0, "rv_pipe", 12, flanges=( 0, ) )
        P.pipe( dress, [ ( e + TANK_R * 0.7, n + TANK_R * 0.7, 40 ), ( e + 110, n + 110, 40 ), ( E1 - 20, n + 110, 40 ) ], 4.0, "rv_pipe", 10, flanges=( 0, ) )
        if detail is not None:
            tank_fittings( d, fn, k, ( e, n ) )
    box( dress, 680, 760, 60, 110, 0, 8, "rv_steel", METAL )
    if detail is not None:
        pump( d, fn )
    else:
        P.cylinder( dress, ( 720, 85 ), 14, 8, 40, "rv_steel", 14, top="rv_steel" )
    rng = np.random.default_rng( 4 )
    for k, ( e, n, kind ) in enumerate( ( ( -620, -60, "dark" ), ( -560, 1500, "olive" ), ( 560, 1500, "olive" ), ( -760, 1740, "dark" ),
                                          ( 760, 1720, "dark" ), ( -300, 1780, "dark" ), ( 300, 1790, "olive" ), ( -880, 420, "olive" ),
                                          ( 880, 440, "dark" ) ) ):
        P.case_stack( dress, ( e, n ), ( 1, 0.15 * rng.normal() ), kind, seed=k + 10 )
    # The foreground cases with the logo, as the reference's, and a clipboard on one.
    for e, n, z in ( ( -420, 110, 0 ), ( -372, 152, 0 ), ( -398, 130, 26 ), ( -472, 80, 0 ), ( 440, -60, 0 ) ):
        P.case( dress, ( e, n ), ( 48, 30, 26 ), ( 1, 0 ), "rv_case", z )
        P.letters( dress, "logo_wordmark", ( e, n - 15.3, z + 13 ), ( 1, 0, 0 ), 9, "light" )
    P.plate( dress, "clipboard", ( -394, 128, 52.2 ), ( 1, 0.25, 0 ), 13, up=( -0.25, 1, 0 ), off=0.05 )
    # Trench gratings across the south deck, and grating panels where the reference's walkway is.
    for e0, e1, n0, n1 in ( ( -420, 420, 300, 324 ), ( -660, -560, -120, 300 ), ( 560, 660, -120, 300 ) ):
        box( m, e0, e1, n0, n1, 0.0, 0.25, { "default": None, "+z": "rv_grating" } )
        box( m, e0 + 3, e1 - 3, n0 + 3, n1 - 3, -0.2, 0.0, { "default": None, "+z": "rv_black" } )
        if fine is not None:
            for a0, a1, b0, b1 in ( ( e0, e1, n0, n0 + 1.2 ), ( e0, e1, n1 - 1.2, n1 ), ( e0, e0 + 1.2, n0, n1 ), ( e1 - 1.2, e1, n0, n1 ) ):
                box( fine, a0, a1, b0, b1, 0.0, 0.3, { "default": None, "+z": "rv_stainless" } )
    segs = 64
    for k in range( segs ):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * ( k + 1 ) / segs
        d0, d1 = v( math.cos( a0 ), math.sin( a0 ), 0 ), v( math.cos( a1 ), math.sin( a1 ), 0 )
        q0, q1 = c + d0 * ( POOL_R + 40 ), c + d1 * ( POOL_R + 40 )
        r0, r1 = c + d0 * ( POOL_R + 44 ), c + d1 * ( POOL_R + 44 )
        card( m, "rv_line_yellow", [ q0 + UP * 0.3, q1 + UP * 0.3, r1 + UP * 0.3, r0 + UP * 0.3 ], UP )


def tank_fittings( d, fine, k, c ):
    """ What a purification tank has besides riverdale_parts.tank's own fittings (its manway, nozzles, level gauge,
    vent, ladder and head rail): a pressure gauge on a nozzle of its own, the valves on the hall's lines from it (the
    outlet's two and the top line's, with its bracket off the east wall), its nameplate. """
    e, n = c
    r = TANK_R
    ctr = v( e, n, 0 )

    def at( deg ):
        a = math.radians( deg )
        return v( math.cos( a ), math.sin( a ), 0 )

    dd = at( 150 )
    p0 = ctr + dd * ( r - 2 ) + UP * 330
    P.rod( d, p0, p0 + dd * 9, 2.5, "rv_white", 10 )
    lathe_on( d, p0 + dd * 9, dd, [ ( 4.8, 0 ), ( 4.8, 1.8 ) ], "rv_steel", 12, cap0="rv_steel", cap1="rv_steel" )
    g = ctr + dd * ( r + 5 ) + UP * 330
    P.rod( fine, g, g + UP * 6, 0.5, "rv_hall_chrome", 5 )
    gc = g + UP * 9 + dd * 0.5
    lathe_on( d, gc - dd * 1.2, dd, [ ( 3.0, 0 ), ( 3.0, 1.8 ) ], "rv_dark", 14, cap0="rv_dark", cap1="rv_ring_white" )
    tg = np.cross( UP, dd )
    bar( fine, gc + dd * 0.7, gc + dd * 0.7 + unit( tg * 0.6 + UP * 0.8 ) * 2.2, 0.25, 0.1, "rv_hall_red", hint=dd )
    valve( d, fine, ( e + 80, n + 80, 40 ), ( 1, 1, 0 ), 5.0 )
    valve( d, fine, ( e + 240, n + 110, 40 ), ( 1, 0, 0 ), 5.0 )
    valve( d, fine, ( e + 170, n, TANK_H + 60 ), ( 1, 0, 0 ), 6.0 )
    bar( d, ( E1, n, TANK_H + 52 ), ( E1 - 30, n, TANK_H + 52 ), 2.4, 2.4, "rv_steel" )
    dn = at( 215 )
    P.quad( fine, "rv_hall_signs", ctr + dn * ( r + 0.4 ) + UP * 92, np.cross( UP, dn ), UP, sign_w( "tk201", 7 ), 7,
            atlas_uv( "tk201" if k == 0 else "tk202" ) )

def pump( d, fine ):
    """ The transfer pump on its skid between the tanks: the motor with its fins, feet and terminal box, the coupling
    guard, the volute with its discharge up into the first tank's outlet line and its suction down through the skid,
    its nameplate. """
    zc = 20.0
    lathe_on( d, ( 686, 84, zc ), ( 1, 0, 0 ), [ ( 3, 0 ), ( 8, 0 ), ( 9, 1 ), ( 9, 27 ), ( 8, 28 ), ( 3, 28 ), ( 3, 30 ) ], "rv_hall_blue", 16,
              cap0="rv_hall_blue", cap1="rv_hall_blue" )
    for k in range( 8 ):
        lathe_on( d, ( 689 + k * 3, 84, zc ), ( 1, 0, 0 ), [ ( 9, 0 ), ( 9.8, 0.2 ), ( 9.8, 0.9 ), ( 9, 1.1 ) ], "rv_hall_blue", 16 )
    box( d, 688, 712, 76, 92, 8, zc - 7, "rv_hall_blue" )
    box( d, 694, 704, 92, 98, zc + 2, zc + 8, "rv_hall_blue" )
    box( d, 716, 726, 78, 90, zc - 6, zc + 6, "rv_yellow" )
    lathe_on( d, ( 726, 84, zc ), ( 1, 0, 0 ), [ ( 4, 0 ), ( 11, 2 ), ( 11, 9 ), ( 5, 12 ), ( 4.5, 12 ), ( 4.5, 18 ), ( 6, 18 ), ( 6, 19.5 ) ],
              "rv_hall_blue", 16, cap1="rv_hall_blue" )
    P.pipe( d, [ ( 732, 84, zc + 10 ), ( 732, 84, 34 ), ( 732, 97, 40 ) ], 3.0, "rv_pipe", 10, caps=False, flanges=( 0, ) )
    P.pipe( d, [ ( 744, 84, zc ), ( 752, 84, zc ), ( 752, 84, 8 ) ], 4.0, "rv_pipe", 10, caps=False )
    P.quad( fine, "rv_hall_signs", ( 720, 59.6, 4.0 ), ( 1, 0, 0 ), UP, sign_w( "p201", 3.5 ), 3.5, atlas_uv( "p201" ) )


HIGH_BAYS = [ ( e, n ) for e in ( -750.0, -250.0, 250.0, 750.0 ) for n in ( 120.0, 600.0, 1350.0, 1780.0 ) ]


def lights():
    """ The hall's own lights besides the fixtures': high bays under the roof, the pool's lamps under the water and its
    glow over it. """
    out = [ ( f"High bay {e} {n}", ( e, n, TOP - 130 ), "1.05,1.18,1.35,1", 1100, False ) for e, n in HIGH_BAYS ]
    c = POOL
    for k in range( 8 ):
        a = 2 * math.pi * ( k + 0.5 ) / 8
        out.append( ( f"Pool lamp {k}", ( c[0] + 420 * math.cos( a ), c[1] + 420 * math.sin( a ), WATER_Z - 70 ), "0.10,0.42,0.52,1", 720, False ) )
    for k in range( 6 ):
        a = 2 * math.pi * k / 6
        out.append( ( f"Pool glow {k}", ( c[0] + 270 * math.cos( a ), c[1] + 270 * math.sin( a ), 70 ), "0.05,0.27,0.38,1", 1050, False ) )
    return out


def high_bays( m, detail=None, fine=None ):
    """ The round LED high bays: each on a strut between the trusses either side, a pendant, a finned body with its
    driver on top, the lens. """
    d = detail if detail is not None else m
    fn = fine if fine is not None else d
    zs = TRUSS_BOTTOM - 3.8
    zf = TOP - 88.0
    for e, n in HIGH_BAYS:
        bar( d, ( e - 125, n, zs ), ( e + 125, n, zs ), 1.6, 1.6, "rv_galv" )
        P.rod( fn, ( e, n, zs - 0.8 ), ( e, n, zf + 12 ), 0.3, "rv_dark", 4 )
        P.lathe( d, ( e, n ), [ ( 8.6, zf - 0.6 ), ( 9.6, zf ), ( 9.6, zf + 2.5 ), ( 8.5, zf + 6.5 ), ( 3.2, zf + 9 ), ( 3.2, zf + 12 ) ], "rv_dark", 16, cap="rv_dark" )
        for k in range( 16 ):
            a = 2 * math.pi * k / 16
            dk = v( math.cos( a ), math.sin( a ), 0 )
            bar( d, v( e, n, zf + 9.3 ) + dk * 3.6, v( e, n, zf + 4.4 ) + dk * 9.2, 0.25, 2.2, "rv_dark" )
        P.obox( d, ( e, n, zf + 13.6 ), ( 1, 0 ), ( 6, 4, 3.2 ), "rv_dark" )
        disc( fn, "rv_lamp_cool", ( e, n, zf - 0.65 ), -UP, 8.4, 16 )


def roof( d, fine ):
    """ Under the roof: purlins on the trusses, bracing in their top chords' plane and cross frames between them, ties
    along the bottom chords, the two spiral supply ducts with their hangers, drops and diffusers, the sprinkler main and
    branches with their heads, and ladder trays hung along the side walls. """
    zb, zt = TRUSS_BOTTOM, TRUSS_BOTTOM + TRUSS_DEPTH
    for n in np.arange( N0 + 48, N1 - 20, 96.0 ):
        channel( d, ( E0 + 2, n, TOP - 3.5 ), ( E1 - 2, n, TOP - 3.5 ), 7, 2.4, "rv_steel", t=0.3, opens=( 0, 1, 0 ) )
    pairs = list( zip( TRUSS_ES, TRUSS_ES[1:] ) )
    for ea, eb in pairs:
        for na, nb in ( ( N0 + 6, N0 + 226 ), ( 790.0, 1010.0 ), ( N1 - 226, N1 - 6 ) ):
            P.rod( d, ( ea, na, zt ), ( eb, nb, zt ), 0.6, "rv_steel", 5 )
            P.rod( d, ( ea, nb, zt ), ( eb, na, zt ), 0.6, "rv_steel", 5 )
        for n in ( 300.0, 900.0, 1500.0 ):
            P.rod( d, ( ea, n, zb ), ( eb, n, zt ), 0.6, "rv_steel", 5 )
            P.rod( d, ( ea, n, zt ), ( eb, n, zb ), 0.6, "rv_steel", 5 )
    for n in ( 300.0, 900.0, 1500.0 ):
        angle_iron( d, ( E0 + 4, n, zb - 3 ), ( E1 - 4, n, zb - 3 ), 3.0, "rv_steel", ( 0, 1, 0 ), ( 0, 0, 1 ), t=0.35 )
    for e in DUCT_ES:
        P.rod( d, ( e, N0, DUCT_Z ), ( e, N1, DUCT_Z ), DUCT_R, "rv_galv", 16 )
        for n in np.arange( N0 + 100, N1, 120.0 ):
            lathe_on( d, ( e, n, DUCT_Z ), ( 0, 1, 0 ), [ ( DUCT_R + 0.5, -1.2 ), ( DUCT_R + 0.5, 1.2 ) ], "rv_galv", 16 )
            for k in ( -1, 1 ):
                P.rod( fine, ( e + k * DUCT_R * 0.75, n, DUCT_Z + DUCT_R * 0.6 ), ( e + k * DUCT_R * 0.75, n, TOP ), 0.35, "rv_galv", 4 )
        for n in np.arange( N0 + 220, N1 - 100, 360.0 ):
            P.rod( d, ( e, n, DUCT_Z - DUCT_R + 2 ), ( e, n, zb - 1 ), 7.0, "rv_galv", 12 )
            lathe_on( d, ( e, n, zb - 1 ), ( 0, 0, -1 ), [ ( 7, 0 ), ( 7.5, 0.6 ), ( 13, 3 ), ( 13.5, 3.6 ) ], "rv_galv", 16, cap1="rv_dark" )
    main_e = -40.0
    P.rod( d, ( main_e, N0, 984 ), ( main_e, N1, 984 ), 2.4, "rv_hall_red", 10 )
    for n in np.arange( N0 + 72, N1 - 50, 144.0 ):
        P.rod( d, ( E0 + 30, n, 986 ), ( E1 - 30, n, 986 ), 1.0, "rv_hall_red", 6 )
        for e in np.arange( E0 + 90, E1 - 60, 120.0 ):
            if abs( e - main_e ) < 20:
                continue
            P.rod( fine, ( e, n, 985.5 ), ( e, n, 981.5 ), 0.4, "rv_hall_red", 5 )
            disc( fine, "rv_hall_chrome", ( e, n, 981.3 ), -UP, 0.9, 6 )
    for sx in ( -1, 1 ):
        face = Face( ( sx * 960, 0 ), ( -sx, 0 ) )
        ladder_tray( d, fine, face, *face.ss( ( sx * 960, N0 + 20 ), ( sx * 960, N1 - 20 ) ), 948, 18, 42, hung=TOP )


def walls( d, fine ):
    """ The walls inside: the epoxy band round their foot (and round the pilasters), ladder trays with conduits down to
    what's on them, the equipment, exit signs and emergency lights over the doors, door frames, a roller shutter's box
    over the south door, cameras and horns, flow markers on the pipes. """
    zt, zu = DECK_TRAY_Z, UPPER_TRAY_Z
    pool_c = ( POOL[0], POOL[1], 0.0 )
    for sx in ( -1, 1 ):
        f = -sx
        side = Face( ( f * E0, 0 ), ( f, 0 ) )

        def run( n0, n1 ):
            return side.ss( ( f * E0, n0 ), ( f * E0, n1 ) )

        def S( n ):
            return side.s_of( f * E0, n )

        for n0, n1 in ( ( N0, WEST_DOOR[0] ), ( WEST_DOOR[1], BLOCK[2] ), ( BLOCK[3], N1 ) ):
            dado( fine, side, *run( n0, n1 ), 0.0 )
        for n0, n1 in ( ( LANDING[2], LANDING[3] ), ( WALKWAY[2], N1 ) ):
            dado( fine, side, *run( n0, n1 ), UPPER )
        for n, z0 in ( ( -60.0, 0.0 ), ( 400.0, 0.0 ), ( 1250.0, UPPER ), ( 1750.0, UPPER ) ):
            pilaster_dado( fine, ( f * ( E0 + 22 ), n ), ( f, 0 ), 48.0, 22.0, z0 )
        for n0, n1 in ( ( N0 + 40, SIDE_RISERS[0] - 30 ), ( SIDE_RISERS[0] + 80, BLOCK[2] - 10 ), ( BLOCK[3] + 10, N1 - 70 ) ):
            ladder_tray( d, fine, side, *run( n0, n1 ), zt, 24, 42 )
        for n0, n1 in ( ( WALKWAY[2] + 10, SIDE_RISERS[1] - 20 ), ( SIDE_RISERS[1] + 70, N1 - 70 ) ):
            ladder_tray( d, fine, side, *run( n0, n1 ), zu, 24, 42 )
        deck_items = [ ( "ext", -150 ), ( "call", 108 ), ( "panel", 160, "db3" ), ( "phone", 340 ), ( "arm", 470 ), ( "eyewash", 560 ),
                       ( "hose", 700 ), ( "panel", 860, "lcp" ), ( "firstaid", 985 ), ( "ext", 1090 ), ( "board", 1205 ), ( "ext", 1700 ),
                       ( "panel", 1830, "db3" ) ]
        if sx > 0:
            deck_items[0] = ( "ext", -172 )
            deck_items.insert( 1, ( "panel", -110, "lcp" ) )
        for item in deck_items:
            kind, n = item[0], item[1]
            wall_item( d, fine, side, kind, S( n ), 0.0, tray=( zt, 33 ), arg=item[2] if len( item ) > 2 else None )
        for item in ( ( "ext", 600 ), ( "sign", 642, ( "hardhat", 78, 12 ) ), ( "ext", 1300 ), ( "panel", 1395, "db3" ), ( "arm", 1560 ),
                      ( "phone", 1680 ), ( "rules", 1880 ) ):
            kind, n = item[0], item[1]
            wall_item( d, fine, side, kind, S( n ), UPPER, tray=( zu, 33 ), arg=item[2] if len( item ) > 2 else None )
        door_frame( fine, side, *run( WEST_DOOR[0], WEST_DOOR[1] ), WEST_DOOR[2] )
        exit_sign( d, fine, side, S( 20 ), WEST_DOOR[2] + 14, 16 )
        emergency_light( fine, side, S( 110 ), 168 )
        horn( d, fine, side, S( 900 ), 560, ( 0, 900, 300 ) )
        camera( d, fine, side, S( 1960 ), 600, pool_c )
        for k, ( dx, r ) in enumerate( ( ( 8, 7.0 ), ( 26, 9.0 ), ( 44, 6.0 ) ) ):
            e = sx * ( E1 - dx - 4 )
            for n0, zs in ( ( SIDE_RISERS[0], ( 120.0, 520.0 ) ), ( SIDE_RISERS[1], ( 540.0, 860.0 ) ) ):
                for z in zs:
                    pipe_marker( fine, ( "pipe_cool", "pipe_demin", "pipe_hvac" )[k], ( e, n0 + k * 22, z ), r, ( f, 0 ) )
        for n_off, r in ( ( 10, 4.0 ), ( 22, 5.5 ) ):
            for n in ( 380.0, 1100.0, 1760.0 ):
                pipe_marker( fine, "pipe_air" if r < 5 else "pipe_n2", ( f * ( E0 + n_off ), n, 236 + r ), r, ( f, 0 ), along=( 0, f, 0 ) )
    north = Face( ( 0, N1 ), ( 0, -1 ) )
    edges = [ E0, NORTH_DOORS[0][0], NORTH_DOORS[0][1], NORTH_DOORS[1][0], NORTH_DOORS[1][1], E1 ]
    for a, b in zip( edges[0::2], edges[1::2] ):
        dado( fine, north, a, b, 0.0 )
    for a, b in ( ( E0, -719.0 ), ( -641.0, -369.0 ), ( -291.0, 291.0 ), ( 369.0, 641.0 ), ( 719.0, E1 ) ):
        dado( fine, north, a, b, UPPER )
    for e in ( -833.0, -500.0, -167.0, 167.0, 500.0, 833.0 ):
        for z0 in ( 0.0, UPPER ):
            pilaster_dado( fine, ( e, N1 - 22 ), ( 0, -1 ), 48.0, 22.0, z0 )
    ladder_tray( d, fine, north, E0 + 40, E1 - 40, zt, 32, 50 )
    for a, b in ( ( -880.0, -714.0 ), ( -618.0, 618.0 ), ( 714.0, 880.0 ) ):
        ladder_tray( d, fine, north, a, b, zu, 36, 54 )
    for item in ( ( "ext", 545 ), ( "hose", 680 ), ( "panel", 760, "db3" ), ( "arm", 905 ), ( "eyewash", 962 ), ( "ext", -545 ), ( "hose", -680 ),
                  ( "panel", -760, "lcp" ), ( "phone", -905 ), ( "firstaid", -962 ), ( "firstaid", -95 ), ( "board", 95 ), ( "rules", -200 ) ):
        wall_item( d, fine, north, item[0], item[1], 0.0, tray=( zt, 41 ), arg=item[2] if len( item ) > 2 else None )
    for item in ( ( "panel", -230, "db3" ), ( "panel", 230, "lcp" ), ( "ext", -420 ), ( "ext", 420 ), ( "arm", -560 ), ( "arm", 560 ),
                  ( "phone", -880 ), ( "phone", 880 ) ):
        wall_item( d, fine, north, item[0], item[1], UPPER, tray=( zu, 45 ), arg=item[2] if len( item ) > 2 else None )
    for o in NORTH_DOORS:
        door_frame( fine, north, o[0], o[1], o[2] )
        exit_sign( d, fine, north, ( o[0] + o[1] ) / 2, 161, 16 )
        emergency_light( fine, north, o[0] - 20, 168 )
    for e in ( -960.0, 960.0 ):
        camera( d, fine, north, e, 600, pool_c )
    for e in ( -400.0, 400.0 ):
        horn( d, fine, north, e, 620, ( e * 0.5, 900, 200 ) )
    for e0 in NORTH_BUNDLES:
        for k, ( dx, r ) in enumerate( ( ( -26, 7.0 ), ( -8, 9.0 ), ( 12, 6.0 ), ( 30, 11.0 ) ) ):
            for z in ( 560.0, 860.0 ):
                pipe_marker( fine, ( "pipe_cool", "pipe_demin", "pipe_air", "pipe_fire" )[k], ( e0 + dx, N1 - 16 - k % 2 * 6, z ), r, ( 0, -1 ) )
    # A supply duct along the north wall over the slogans, its grilles.
    nd0, nd1, zd0, zd1 = N1 - 70, N1 - 40, 850.0, 898.0
    box( d, E0 + 10, E1 - 10, nd0, nd1, zd0, zd1, { "default": "rv_galv", "+n": None } )
    for e in np.arange( E0 + 120, E1 - 60, 250.0 ):
        P.quad( fine, "rv_hall_signs", ( e, nd0 - 0.05, ( zd0 + zd1 ) / 2 ), ( -1, 0, 0 ), UP, 36, 18, atlas_uv( "grille" ) )
        box( fine, e - 1, e + 1, nd0 - 2, nd1, zd0 - 0.5, zd1 + 0.5, "rv_galv" )
    for e in np.arange( E0 + 60, E1, 120.0 ):
        P.rod( fine, ( e, ( nd0 + nd1 ) / 2, zd1 ), ( e, ( nd0 + nd1 ) / 2, TRUSS_BOTTOM - 3 ), 0.35, "rv_galv", 4 )
    south = Face( ( 0, N0 ), ( 0, 1 ) )
    for a, b in ( ( E0, SOUTH_DOOR[0] ), ( SOUTH_DOOR[1], E1 ) ):
        dado( fine, south, *south.ss( ( a, N0 ), ( b, N0 ) ), 0.0 )
    for a, b in ( ( -960.0, -130.0 ), ( 130.0, 960.0 ) ):
        ladder_tray( d, fine, south, *south.ss( ( a, N0 ), ( b, N0 ) ), zt, 24, 42 )
    for sg in ( -1, 1 ):
        for item in ( ( "ext", 140 ), ( "sign", 205, ( "rca", 100, 22 ) ), ( "sign", 268, ( "hardhat", 100, 20 ) ), ( "panel", 340, "db3" ),
                      ( "arm", 460 ), ( "eyewash", 880 ), ( "sign", 400, ( "crane", 230, 30 ) ) ):
            wall_item( d, fine, south, item[0], south.s_of( sg * item[1], N0 ), 0.0, tray=( zt, 33 ), arg=item[2] if len( item ) > 2 else None )
        camera( d, fine, south, south.s_of( sg * 960, N0 ), 260, pool_c )
        emergency_light( fine, south, south.s_of( sg * 130, N0 ), 172 )
    wall_item( d, fine, south, "phone", south.s_of( -560, N0 ), 0.0 )
    wall_item( d, fine, south, "hose", south.s_of( 560, N0 ), 0.0 )
    s0, s1 = south.ss( ( SOUTH_DOOR[0], N0 ), ( SOUTH_DOOR[1], N0 ) )
    door_frame( fine, south, s0, s1, SOUTH_DOOR[2] )
    south.box( d, s0 - 14, s1 + 14, SOUTH_DOOR[2] + 3, SOUTH_DOOR[2] + 27, 0, 18, "rv_hall_equipment" )
    for s in ( s0 - 4, s1 ):
        south.box( fine, s, s + 4, 0, SOUTH_DOOR[2] + 3, 1.2, 4.5, "rv_galv" )
    exit_sign( d, fine, south, ( s0 + s1 ) / 2, SOUTH_DOOR[2] + 15, 16, d0=18 )


def floor_marks( fine ):
    """ Paint on the deck: a line and hatching round the pool between its coping and the yellow ring, keep-clear boxes
    hatched in front of the doors and the stairs' feet, the walkways in from the doors, a line round the tanks, stencils,
    and floor drains round the pool. """
    paint = "rv_line_yellow"
    c = v( *POOL, 0 )
    segs = 96
    r0, r1 = POOL_R + 16, POOL_R + 20
    for k in range( segs ):
        a0, a1 = 2 * math.pi * k / segs, 2 * math.pi * ( k + 1 ) / segs
        d0, d1 = v( math.cos( a0 ), math.sin( a0 ), 0 ), v( math.cos( a1 ), math.sin( a1 ), 0 )
        card( fine, paint, [ c + d0 * r0 + UP * 0.22, c + d1 * r0 + UP * 0.22, c + d1 * r1 + UP * 0.22, c + d0 * r1 + UP * 0.22 ], UP )
    ra, rb = POOL_R + 20, POOL_R + 40
    count = 280
    da = 18.0 / ( POOL_R + 30 )
    for k in range( count ):
        a = 2 * math.pi * k / count
        u0, u1 = v( math.cos( a ), math.sin( a ), 0 ), v( math.cos( a + da ), math.sin( a + da ), 0 )
        t0, t1 = np.cross( UP, u0 ) * 2.4, np.cross( UP, u1 ) * 2.4
        p0, p1 = c + u0 * ra + UP * 0.21, c + u1 * rb + UP * 0.21
        card( fine, paint, [ p0 - t0, p0 + t0, p1 + t1, p1 - t1 ], UP )

    def strip( a, b, w=3.0 ):
        a, b = v( a[0], a[1], 0.2 ), v( b[0], b[1], 0.2 )
        sd = unit( np.cross( UP, b - a ) ) * ( w / 2 )
        card( fine, paint, [ a - sd, b - sd, b + sd, a + sd ], UP )

    def hatch_box( e0, e1, n0, n1, pitch=14.0, w=3.0 ):
        for a, b in ( ( ( e0, n0 + w / 2 ), ( e1, n0 + w / 2 ) ), ( ( e0, n1 - w / 2 ), ( e1, n1 - w / 2 ) ),
                      ( ( e0 + w / 2, n0 ), ( e0 + w / 2, n1 ) ), ( ( e1 - w / 2, n0 ), ( e1 - w / 2, n1 ) ) ):
            strip( a, b, w )
        i0, i1, j0, j1 = e0 + w, e1 - w, n0 + w, n1 - w
        for k in np.arange( i0 - j1 + pitch / 2, i1 - j0, pitch ):
            ea, eb = max( i0, k + j0 ), min( i1, k + j1 )
            if eb - ea < 2 * w:
                continue
            ea, eb = ea + w * 0.7, eb - w * 0.7
            strip( ( ea, ea - k ), ( eb, eb - k ), w * 1.2 )

    hatch_box( SOUTH_DOOR[0] - 14, SOUTH_DOOR[1] + 14, N0, N0 + 110 )
    for sx in ( -1, 1 ):
        f = -sx
        hatch_box( *sorted( ( f * E0, f * ( E0 + 100 ) ) ), WEST_DOOR[0] - 14, WEST_DOOR[1] + 14 )
        hatch_box( *sorted( ( f * ( STAIR[0] - 10 ), f * ( STAIR[1] + 10 ) ) ), STAIR[2] - 64, STAIR[2] - 4, pitch=12.0 )
        for n in ( WEST_DOOR[0] - 10, WEST_DOOR[1] + 10 ):
            strip( ( f * ( E0 + 100 ), n ), ( f * -680, n ) )
        top_quad( fine, "rv_hall_signs", ( f * -800, ( WEST_DOOR[0] + WEST_DOOR[1] ) / 2, 0.24 ), ( f, 0 ), 48, 12, atlas_uv( "walkway" ) )
        top_quad( fine, "rv_hall_signs", ( f * ( E0 + 55 ), ( WEST_DOOR[0] + WEST_DOOR[1] ) / 2, 0.24 ), ( -f, 0 ), 40, 10, atlas_uv( "keep_clear" ) )
    for o in NORTH_DOORS:
        hatch_box( o[0] - 14, o[1] + 14, N1 - 110, N1 )
        top_quad( fine, "rv_hall_signs", ( ( o[0] + o[1] ) / 2, N1 - 60, 0.24 ), ( 0, 1 ), 40, 10, atlas_uv( "keep_clear" ) )
    top_quad( fine, "rv_hall_signs", ( 0, N0 + 55, 0.24 ), ( 0, -1 ), 44, 11, atlas_uv( "keep_clear" ) )
    for e in ( -62.0, 62.0 ):
        strip( ( e, N0 + 112 ), ( e, 296 ) )
    for n in ( 40.0, 200.0 ):
        top_quad( fine, "rv_hall_signs", ( 0, n, 0.24 ), ( 0, 1 ), 48, 12, atlas_uv( "walkway" ) )
    top_quad( fine, "rv_hall_signs", ( 0, N1 - 70, 0.24 ), ( 0, 1 ), 44, 11, atlas_uv( "no_storage" ) )
    for a, b in ( ( ( 520, -95 ), ( 772, -95 ) ), ( ( 772, -95 ), ( 772, 255 ) ), ( ( 772, 255 ), ( 520, 255 ) ), ( ( 520, 255 ), ( 520, -95 ) ) ):
        strip( a, b )
    for k in range( 8 ):
        a = math.radians( 22.5 + 45 * k )
        p = c + v( math.cos( a ), math.sin( a ), 0 ) * ( POOL_R + 72 )
        top_quad( fine, "rv_stainless", p + UP * 0.22, ( 1, 0 ), 15, 15 )
        top_quad( fine, "rv_hall_signs", p + UP * 0.26, ( 1, 0 ), 12, 12, atlas_uv( "drain" ) )


def exterior( d, fine ):
    """ The hall's outside: a base course and two string courses round its walls, the coping on its parapet and the
    pilasters' caps, downpipes with their hoppers, scuppers and shoes, and plant on its roof (air handlers, exhaust
    fans, vent stacks, a hatch, walkway pads). """
    faces = [ ( Face( ( 0, N0 - WT ), ( 0, -1 ) ), "e", [ SOUTH_DOOR[:2] ], ( -766.0, -246.0, 326.0, 846.0 ) ),
              ( Face( ( 0, N1 + WT ), ( 0, 1 ) ), "e", [ o[:2] for o in NORTH_DOORS ], ( -625.0, -125.0, 125.0, 625.0 ) ),
              ( Face( ( E0 - WT, 0 ), ( -1, 0 ) ), "n", [ WEST_DOOR[:2] ], ( 640.0, 1250.0, 1950.0 ) ),
              ( Face( ( E1 + WT, 0 ), ( 1, 0 ) ), "n", [ WEST_DOOR[:2] ], ( 640.0, 1250.0, 1950.0 ) ) ]
    for face, axis, openings, pipes in faces:
        lo, hi = ( E0 - WT - 1.5, E1 + WT + 1.5 ) if axis == "e" else ( N0 - WT - 1.5, N1 + WT + 1.5 )

        def S( a ):
            return face.s_of( a, face.o[1] ) if axis == "e" else face.s_of( face.o[0], a )

        cuts = [ lo ] + [ x for o in openings for x in o ] + [ hi ]
        for a, b in zip( cuts[0::2], cuts[1::2] ):
            face.box( d, *sorted( ( S( a ), S( b ) ) ), 0, 30, 0, 1.5, "rv_plinth" )
        for z in ( 396.0, 796.0 ):
            face.box( d, *sorted( ( S( lo ), S( hi ) ) ), z, z + 6, 0, 1.2, "rv_plinth" )
        if "rv_grime_foot" in RM.SURFACES:
            # Grime: rain's at the foot (over the base course and the wall above it), and running down under the coping
            # and the string courses. Their UVs: up 0-1, along by 192 in.
            def guv( s0, s1, v0, v1 ):
                return [ ( s0 / 192.0, v0 ), ( s1 / 192.0, v0 ), ( s1 / 192.0, v1 ), ( s0 / 192.0, v1 ) ]

            for a, b in zip( cuts[0::2], cuts[1::2] ):
                s0, s1 = sorted( ( S( a ), S( b ) ) )
                face.quad( fine, "rv_grime_foot", s0, s1, 0, 30, 1.56, uv=guv( s0, s1, 0.0, 30 / 48 ) )
                face.quad( fine, "rv_grime_foot", s0, s1, 30, 48, 0.3, uv=guv( s0, s1, 30 / 48, 1.0 ) )
            s0, s1 = sorted( ( S( lo ), S( hi ) ) )
            for ztop in ( 396.0, 796.0, ROOF + 36.5 ):
                face.quad( fine, "rv_grime_top", s0, s1, ztop - 96, ztop, 0.3, uv=guv( s0, s1, 0.0, 1.0 ) )
        for a in pipes:
            s = S( a )
            face.box( d, s - 5, s + 5, ROOF - 22, ROOF - 6, 1.5, 11, "rv_steel" )
            face.box( fine, s - 3, s + 3, ROOF + 2, ROOF + 8, -0.5, 3.0, "rv_steel" )
            P.pipe( d, [ face.p( s, ROOF - 22, 6.0 ), face.p( s, 10, 6.0 ), face.p( s, 2, 13 ) ], 3.5, "rv_steel", 10, caps=False )
            for z in np.arange( 120.0, ROOF - 40, 160.0 ):
                lathe_on( fine, face.p( s, z, 6.0 ), UP, [ ( 3.9, 0 ), ( 3.9, 1.6 ) ], "rv_steel", 10 )
                face.box( fine, s - 0.6, s + 0.6, z, z + 1.6, 0, 2.6, "rv_steel" )
    for a, b, c0, c1 in ( ( E0 - WT - 1.5, E1 + WT + 1.5, N0 - WT - 1.5, N0 - WT + 13.5 ), ( E0 - WT - 1.5, E1 + WT + 1.5, N1 + WT - 13.5, N1 + WT + 1.5 ),
                          ( E0 - WT - 1.5, E0 - WT + 13.5, N0 - WT - 1.5, N1 + WT + 1.5 ), ( E1 + WT - 13.5, E1 + WT + 1.5, N0 - WT - 1.5, N1 + WT + 1.5 ) ):
        box( d, a, b, c0, c1, ROOF + 40, ROOF + 41.5, "rv_zinc" )
    for face, _, _, _ in faces:
        lo, hi = -1300.0, 1300.0
        face.box( d, lo, hi, ROOF + 36.5, ROOF + 40, 0, 1.5, "rv_zinc" )
    south = faces[0][0]
    for e in np.arange( E0 - WT + 40, E1 + WT, 260.0 ):
        if abs( e ) < 150:
            continue
        box( d, e - 21.5, e + 21.5, N0 - WT - 15.5, N0 - WT, ROOF + 20, ROOF + 21.5, "rv_zinc" )
        if "rv_grime_foot" in RM.SURFACES:
            s = south.s_of( e, N0 - WT )
            uv = [ ( ( s - 20 ) / 192.0, 0.0 ), ( ( s + 20 ) / 192.0, 0.0 ), ( ( s + 20 ) / 192.0, 1.0 ), ( ( s - 20 ) / 192.0, 1.0 ) ]
            south.quad( fine, "rv_grime_foot", s - 20, s + 20, 0, 48, 14.3, uv=uv )
            south.quad( fine, "rv_grime_top", s - 20, s + 20, ROOF + 20 - 96, ROOF + 20, 14.3, uv=uv )
    # Roof plant.
    rz = ROOF
    for sx in ( -1, 1 ):
        ce, cn = sx * 450.0, 1100.0
        box( d, ce - 88, ce + 88, cn - 48, cn + 48, rz, rz + 8, "rv_steel" )
        box( d, ce - 80, ce + 80, cn - 40, cn + 40, rz + 8, rz + 64, "rv_hall_equipment" )
        for k in ( -1, 1 ):
            c = v( ce + k * 40, cn, rz + 64 )
            disc( fine, "rv_dark", c + UP * 0.1, UP, 16, 16 )
            hoop( fine, c + UP * 3, UP, 16, 0.35, "rv_galv", 16, 4 )
        for nn, out in ( ( cn - 40, ( 0, -1 ) ), ( cn + 40, ( 0, 1 ) ) ):
            fc = Face( ( 0, nn ), out )
            for k in range( 3 ):
                s = fc.s_of( ce - 50 + k * 50, nn )
                fc.quad( fine, "rv_louvre", s - 20, s + 20, rz + 18, rz + 50, 0.2 )
        box( d, *sorted( ( ce - sx * 80, ce - sx * 150 ) ), cn - 15, cn + 15, rz + 24, rz + 46, "rv_galv" )
        box( d, *sorted( ( ce - sx * 150, ce - sx * 172 ) ), cn - 15, cn + 15, rz, rz + 46, "rv_galv" )
        for e, n in ( ( sx * 200.0, 300.0 ), ( sx * 700.0, 300.0 ), ( sx * 200.0, 1700.0 ), ( sx * 700.0, 1700.0 ) ):
            box( d, e - 18, e + 18, n - 18, n + 18, rz, rz + 10, "rv_steel" )
            P.lathe( d, ( e, n ), [ ( 12, rz + 10 ), ( 12, rz + 20 ), ( 20, rz + 24 ), ( 19, rz + 30 ), ( 6, rz + 36 ) ], "rv_galv", 16, cap="rv_galv" )
        for n in ( -150.0, 1950.0 ):
            e = sx * 900.0
            P.cylinder( d, ( e, n ), 8, rz, rz + 110, "rv_galv", 12 )
            P.lathe( d, ( e, n ), [ ( 8.5, rz + 110 ), ( 14, rz + 118 ), ( 3, rz + 122 ) ], "rv_galv", 12 )
        for n0, n1 in ( ( 400.0, 1000.0 ), ( 1200.0, 1650.0 ) ):
            box( fine, sx * 450 - 18, sx * 450 + 18, n0, n1, rz, rz + 0.6, "rv_plinth" )
    box( d, -918, -882, 1932, 1968, rz, rz + 18, "rv_steel" )


_DETAIL = []


def build():
    """ Returns the hall's models: structure (solid), dressing (solid), pool (drawn only), water and glass. Its two
    detail models wait for extra_models(). """
    hall, dress, pool_m, water, glass = K.Model(), K.Model(), K.Model(), K.Model(), K.Model()
    detail, fine = K.Model(), K.Model()
    _PENDING_LIGHTS.clear()
    shell( hall, detail, fine )
    deck( hall )
    for sx in ( -1, 1 ):
        upper_side( hall, sx, detail, fine )
    north_wall( hall, detail, fine )
    crane( hall, detail, fine )
    mast( pool_m, hall )
    pool( pool_m )
    deck_props( hall, dress, detail, fine )
    high_bays( hall, detail, fine )
    walls( detail, fine )
    roof( detail, fine )
    floor_marks( fine )
    exterior( detail, fine )
    P.LIGHTS.extend( _PENDING_LIGHTS )
    _PENDING_LIGHTS.clear()
    c = v( *POOL, 0 )
    segs = 64
    card( water, "rv_pool_water", [ c + v( math.cos( 2 * math.pi * k / segs ), math.sin( 2 * math.pi * k / segs ), 0 ) * POOL_R + UP * WATER_Z
                                    for k in range( segs ) ], UP )
    # The control rooms' glazing: the pool side and the south side.
    for sx in ( -1, 1 ):
        f = -sx
        c0, c1, cn0, cn1 = CONTROL
        ge = f * ( c1 - 7 )
        glass.box( ( ge - 0.5, cn0 + 14, UPPER + 38 ), ( ge + 0.5, cn1, UPPER + 148 ), "rw_glass", "glass" )
        for e0_, e1_ in ( ( c0, -680.0 ), ( -610.0, c1 ) ):
            a, b = sorted( ( f * e0_, f * e1_ ) )
            glass.box( ( a, cn0 + 6.5, UPPER + 38 ), ( b, cn0 + 7.5, UPPER + 148 ), "rw_glass", "glass" )
    _DETAIL[:] = [ ( "riverdale_hall_detail", "Reactor Hall Detail", False, True, detail ),
                   ( "riverdale_hall_fine", "Reactor Hall Fine", False, False, fine ) ]
    return hall, dress, pool_m, water, glass


def extra_models():
    """ The hall's detail models, both drawn only: riverdale_hall_detail (casting shadows) and riverdale_hall_fine (not),
    from the last build() (riverdale_map builds the hall before it asks). """
    if not _DETAIL:
        build()
    return list( _DETAIL )
