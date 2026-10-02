"""
Belltower, a multiplayer map: a hill town's market square, built by script out of boxes and polygons with
Tools/map_kit.py and painted with Tools/building_textures.py's materials. Collision is the same boxes (plus convex hulls
for roofs and round things), so what you see is what stops players, bots and bullets.

    python Tools/belltower_map.py [--preview <dir>] [--no-scene]

The town is mirror-symmetric about its north-south centre line. Red Team (Team.Terrorist) spawns on the west road, inside
the town wall, and Blue Team (Team.CounterTerrorist) on the east one. Three lanes run between them:

- North: Market Street, long and open, with market stalls, a lorry and the market cross in the middle. Bomb site A is
  at its east end.
- Middle: West Street and East Street, through the square with its fountain. The Town Hall stands on the square's north
  side: a loggia at the front, a passage under the belltower through to Market Street, side rooms with stairs, and the
  council hall upstairs, whose balcony overlooks the square and whose windows look out over Market Street.
- South: the terrace walk, and below it (48 lower) the gardens: plots divided by low walls and hedges, sheds, wells and
  an orchard. Bomb site B is in the east gardens.

Between the lanes: an alley at each corner, the Bakery (west) and the Dairy (its mirror, east) with their yards, the
Inn (west) and the Tavern (east) with their beer gardens, the churchyards, and the church, whose doors open onto the
square, the churchyards and the terrace.

- Writes the models to Assets/models/maps/belltower/ (<name>.obj/.mtl, their collision hulls and <name>.vmdl): the
  centre, the west half and the east half, and through Tools/belltower_vista.py the land round the town (the hill
  falling away to fields, woods, farms and hills, painted by Tools/belltower_vista_paint.py, drawn only: no collision,
  no shadows). Also the scene to Assets/scenes/maps/Belltower/belltower.scene (spawns for every
  mode, the bomb sites, buy zones, callouts, Cash Grab's points, the Domination and Hot Zone spots, light) and the radar
  picture to Assets/ui/minimaps/minimap_belltower.png. The scene is written whole every run: edit the layout here, not
  in the editor.
- Every run checks each spawn, objective and cash point (all_spots) against the collision: room for a player, a floor
  under it, and a way to walk there from the spawn roads (check_reach, a stand-in for the navmesh). It prints what's
  wrong.
- Plan coordinates: e east, n north, z up, in inches (map_kit's docstring has the world axes). The town's streets are at
  z 0 and the gardens at -48.
- Houses nobody goes into are one collision box each, with their fronts drawn over it: windows glazed or shuttered, doors
  shut, shops behind rolling shutters. The Town Hall, the church, the Bakery, the Dairy, the Inn and the Tavern are open,
  through doorways (no doors: bots can't open them).
- Roofs are 42 degrees, steeper than the navmesh's 40, and every attic is filled with the roof's hull, so the navmesh
  finds no floor up there. Stairs are 8 up and 11 along with room at both ends; doorways 56-64 wide.
- The west half is built and the east half is its mirror (Model.mirrored), repainted from warm colours to cool ones
  (EAST_PAINTS), so each side of the town reads as its team's.
- --preview writes a top-down picture and a few views from head height to <dir>, drawn with the paints' mean colours,
  for checking without the editor. If Assets/ui/maps/belltower.png (the menus' picture of the map) doesn't exist, it
  writes the aerial view there as a stand-in.
"""
import argparse
import json
import math
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import building_textures as BT
import map_kit as K
import belltower_detail as Detail
import belltower_vista as Vista
import belltower_vista_props as VistaProps
from map_kit import Model, Wall, arc, normalise

TITLE = "Belltower"
OUT_DIR = K.ASSETS / "models" / "maps" / "belltower"
RESOURCE_DIR = "models/maps/belltower"
SCENE_FILE = K.ASSETS / "scenes" / "maps" / "Belltower" / "belltower.scene"
MINIMAP_FILE = K.ASSETS / "ui" / "minimaps" / "minimap_belltower.png"
MINIMAP_PATH = "ui/minimaps/minimap_belltower.png"
MAP_ART_FILE = K.ASSETS / "ui" / "maps" / "belltower.png"
MAP_ART_PATH = "ui/maps/belltower.png"
ids = K.SceneIds( "8e1f6a3c-52d4-4b7e-a0c9-3f7d2b6e1a58" )

# Surfaces (s&box's core .surface files)
STONE, WOOD, TILE, METAL, SHEET, FABRIC, DIRT, GRASS, GLASS, WATER = (
    "default", "wood", "ceramic", "metal", "metal.sheet", "fabric", "dirt", "grass", "glass", "water" )

# ---------------------------------------------------------------------------------------------------------------------
# Layout (plan inches). The west half; the east is its mirror.

ROAD = ( -2300, -1850 )          # the west spawn road, e
TOWN_WALL = ( -2380, -2300 )     # the west town wall, e
NORTH_ROW = ( 1450, 1800 )       # the houses along Market Street's north side, n
MARKET = ( 1100, 1450 )          # Market Street, n
MID = ( -100, 350 )              # West Street, n
SQUARE = ( -650, 650, -400, 550 )
TERRACE = ( -1000, -900 )        # the terrace walk, n
GARDENS = ( -1450, -1000 )       # n, at GARDEN_Z
GARDEN_Z = -48
SOUTH_EDGE = -1466               # the south parapet's outer face
ALLEY = ( -1400, -1250 )         # the alleys, e
RAMP = ( -1200, -1000 )          # where the spawn roads go down to the gardens' level, n

ROOF_PITCH = 42.0                # steeper than the navmesh's 40 degrees
GROUND_STOREY = 130              # a house's first floor
STOREY = 120                     # and every floor above it

# The fronts' pictures (Tools/belltower_fronts.py): shutter paints to their louvres, awning canvases to their cloth, and
# the shops' names (belltower_fronts.SIGNS' indexes). 0 is the café's, 2 the Bakery's and 5 the Inn's; the other houses'
# shops take SHOP_NAMES in turn (_shops counts them). The east's mirror repaints each west name to one of its own.
LOUVRES = { "shutter_green": "green", "shutter_red": "red", "shutter_brown": "brown", "shutter_blue": "blue" }
# Painted window surrounds (cornici), by a house's render: a pale band round a coloured house's windows, grey stone
# round a pale one's. Three houses in four have them (solid_house), each window with a hood over its head (dress).
SURROUNDS = { "render_rose": "render_cream", "render_ochre": "render_cream", "render_terracotta": "render_cream",
              "render_sage": "render_white", "render_blue": "render_white", "render_cream": "ashlar_grey",
              "render_pale": "ashlar_grey", "render_white": "ashlar_grey" }
AWNING_KEYS = { "canvas_red": "red", "canvas_green": "green", "canvas_blue": "blue" }
SHOP_NAMES = ( 1, 3, 4, 6, 7, 8, 9 )
EAST_SIGNS = { 0: 10, 1: 11, 2: 14, 3: 13, 4: 19, 5: 12, 6: 16, 7: 15, 8: 17, 9: 18 }
_shops = [ 0 ]

# West paints to east ones: warm colours on Red Team's side, cool ones on Blue Team's.
EAST_PAINTS = {
    "render_rose": "render_blue", "render_terracotta": "render_sage", "render_ochre": "render_pale",
    "render_cream": "render_white", "shutter_red": "shutter_blue", "trim_red": "trim_blue",
    "canvas_red": "canvas_blue", "shutter_brown": "shutter_green", "parasol_red": "parasol_blue",
    "louvre_red": "louvre_blue", "louvre_pair_red": "louvre_pair_blue",
    "louvre_brown": "louvre_green", "louvre_pair_brown": "louvre_pair_green",
    "awning_red": "awning_blue", "awning_green": "awning_navy", "valance_red": "valance_blue",
    "valance_green": "valance_navy", "banner_red": "banner_blue", "door_c": "door_d", "door_f": "door_g", "door_g": "door_f",
    "window_a": "window_c", "window_c": "window_a", "window_b": "window_d", "window_d": "window_b",
    "shopfront_a": "shopfront_c", "shopfront_c": "shopfront_a",
    "ghost_0": "ghost_2", "ghost_1": "ghost_3",
    **{ f"sign_{w}": f"sign_{e}" for w, e in EAST_SIGNS.items() },
    **{ f"letters_{w}": f"letters_{e}" for w, e in EAST_SIGNS.items() },
    **{ f"plaque_{k}": f"plaque_{k + 3}" for k in range( 3 ) },
    "insegna_0": "insegna_1",
}


# ---------------------------------------------------------------------------------------------------------------------
# Small shapes

def facing( model, paint, points, towards ):
    """ A polygon wound to face towards (a plan vector). """
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
    model.polygon( paint, pts )


def rect( model, paint, e0, e1, n0, n1, z ):
    """ A level rectangle facing up. """
    model.polygon( paint, [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ] )


def ring( model, centre, r_in, r_out, z0, z1, sides, paints, surface=None, turn=None ):
    """ A hollow upright prism (a basin's or a well's wall): outside and inside faces, the top between them, and a
    collision box along each side. paints { 'outside', 'inside', 'top' }. """
    turn = math.pi / sides if turn is None else turn
    c = np.asarray( centre, float )

    def at( r, k ):
        a = turn + 2 * math.pi * k / sides
        return c + r * np.array( ( math.cos( a ), math.sin( a ) ) )

    for k in range( sides ):
        o0, o1, i0, i1 = at( r_out, k ), at( r_out, k + 1 ), at( r_in, k ), at( r_in, k + 1 )
        mid = ( o0 + o1 ) / 2 - c
        out = np.array( ( mid[0], mid[1], 0.0 ) )
        facing( model, paints["outside"], [ ( *o0, z0 ), ( *o1, z0 ), ( *o1, z1 ), ( *o0, z1 ) ], out )
        facing( model, paints["inside"], [ ( *i0, z0 ), ( *i1, z0 ), ( *i1, z1 ), ( *i0, z1 ) ], -out )
        facing( model, paints["top"], [ ( *o0, z1 ), ( *o1, z1 ), ( *i1, z1 ), ( *i0, z1 ) ], ( 0, 0, 1 ) )
        if surface:
            along = np.array( ( *( o1 - o0 ), 0.0 ) )
            length = np.linalg.norm( along )
            x_axis = along / length
            y_axis = -out / np.linalg.norm( out )
            z_axis = np.cross( x_axis, y_axis )
            if z_axis[2] < 0:
                y_axis = -y_axis
                z_axis = -z_axis
            centre3 = np.array( ( *( ( o0 + o1 + i0 + i1 ) / 4 ), ( z0 + z1 ) / 2 ) )
            model.boxes.append( ( centre3, ( tuple( x_axis ), tuple( y_axis ), tuple( z_axis ) ),
                                  np.array( ( length, r_out - r_in, z1 - z0 ) ), surface ) )


def blob( model, centre, radius, paint, squash=0.8, segments=9, rings=5, seed=0 ):
    """ A lumpy ball (a tree's crown), no collision. """
    if paint == "hedge" or (paint == "canvas_red" and radius <= 14):
        Detail.shrub( model, centre, radius, squash, seed )
        return
    rng = np.random.default_rng( seed )
    c = np.asarray( centre, float )
    wobble = 1.0 + 0.12 * rng.standard_normal( ( rings + 1, segments ) )
    wobble[0, :] = wobble[0, 0]
    wobble[-1, :] = wobble[-1, 0]

    def at( i, j ):
        polar = math.pi * i / rings
        azimuth = 2 * math.pi * j / segments + 0.3 * i
        r = radius * wobble[i, j % segments]
        return c + np.array( ( r * math.sin( polar ) * math.cos( azimuth ), r * math.sin( polar ) * math.sin( azimuth ),
                               r * squash * math.cos( polar ) ) )

    for i in range( rings ):
        for j in range( segments ):
            pts = [ at( i, j ), at( i + 1, j ), at( i + 1, j + 1 ), at( i, j + 1 ) ]
            if i == 0:
                pts = [ pts[0], pts[1], pts[2] ]
            elif i == rings - 1:
                pts = [ pts[0], pts[1], pts[3] ]
            mid = np.mean( pts, axis=0 ) - c
            facing( model, paint, pts, mid )


def axle( model, centre, axis, radius, width, paints, sides=10, surface=None ):
    """ A cylinder lying along axis (a wheel, a barrel on its side): paints { 'side', 'end' }. """
    c = np.asarray( centre, float )
    a = normalise( axis )
    u = normalise( np.cross( a, ( 0, 0, 1 ) ) if abs( a[2] ) < 0.9 else np.cross( a, ( 1, 0, 0 ) ) )
    v = np.cross( a, u )
    ends = ( c - a * width / 2, c + a * width / 2 )
    rim = [ [ e + radius * ( math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v )
              for k in range( sides ) ] for e in ends ]
    for k in range( sides ):
        q = [ rim[0][k], rim[0][( k + 1 ) % sides], rim[1][( k + 1 ) % sides], rim[1][k] ]
        facing( model, paints["side"], q, np.mean( q, axis=0 ) - c )
    facing( model, paints["end"], rim[0], -a )
    facing( model, paints["end"], rim[1], a )
    if surface:
        model.hull( [ p for r in rim for p in r ], surface )


def cone( model, centre, radius, z0, z1, paint, sides=8, surface=None, turn=None ):
    """ A pointed roof (a kiosk's, a finial). """
    c = np.asarray( centre, float )
    turn = math.pi / sides if turn is None else turn
    base = [ np.array( ( *( c + radius * np.array( ( math.cos( turn + 2 * math.pi * k / sides ),
                                                    math.sin( turn + 2 * math.pi * k / sides ) ) ) ), z0 ) )
             for k in range( sides ) ]
    apex = np.array( ( *c, z1 ) )
    for k in range( sides ):
        tri = [ base[k], base[( k + 1 ) % sides], apex ]
        mid = np.mean( tri, axis=0 )
        facing( model, paint, tri, np.array( ( mid[0] - c[0], mid[1] - c[1], radius * 0.5 ) ) )
    facing( model, paint, base, ( 0, 0, -1 ) )
    if surface:
        model.hull( [ tuple( p ) for p in base ] + [ tuple( apex ) ], surface )


def pyramid( model, e0, e1, n0, n1, z0, z1, paint, surface=None ):
    """ A four-sided pointed roof (the belltower's). """
    apex = np.array( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z1 ) )
    corners = [ np.array( p ) for p in ( ( e0, n0, z0 ), ( e1, n0, z0 ), ( e1, n1, z0 ), ( e0, n1, z0 ) ) ]
    for k in range( 4 ):
        tri = [ corners[k], corners[( k + 1 ) % 4], apex ]
        mid = np.mean( tri, axis=0 )
        facing( model, paint, tri, np.array( ( mid[0] - apex[0], mid[1] - apex[1], 1.0 ) ) )
    facing( model, paint, corners, ( 0, 0, -1 ) )
    if surface:
        model.hull( [ tuple( p ) for p in corners ] + [ tuple( apex ) ], surface )


def stair( model, lo, hi, z0, z1, climb, tread, side, surface=WOOD ):
    """ A straight flight over the plan rectangle lo..hi ( e, n ), climbing towards climb ('+e', '-e', '+n', '-n') from
    z0 to z1 in risers of about 8: each step a solid box down to z0. """
    steps = max( 1, round( ( z1 - z0 ) / 8 ) )
    rise = ( z1 - z0 ) / steps
    axis = 0 if climb[1] == "e" else 1
    a0, a1 = lo[axis], hi[axis]
    run = ( a1 - a0 ) / steps
    for k in range( steps ):
        s0, s1 = ( a0 + k * run, a0 + ( k + 1 ) * run ) if climb[0] == "+" else ( a1 - ( k + 1 ) * run, a1 - k * run )
        blo, bhi = list( lo ), list( hi )
        blo[axis], bhi[axis] = s0, s1
        model.box( ( blo[0], blo[1], z0 ), ( bhi[0], bhi[1], z0 + rise * ( k + 1 ) ), { "+z": tread, "default": side }, surface )


# ---------------------------------------------------------------------------------------------------------------------
# Roofs

def gable_roof( model, e0, e1, n0, n1, eave, ridge_axis, tiles, gable, over=14.0, ends_over=( 14.0, 14.0 ),
                thick=5.0, soffit="planks_dark", trim="trim_brown", pitch=ROOF_PITCH, hull=STONE, slab_surface=None,
                gables=( True, True ), cap=True, gutter=None ):
    """ A gable roof over e0..e1 x n0..n1 with its ridge along ridge_axis ('e' or 'n') and its eaves at z eave on the long
    sides, overhanging by over there and by ends_over past the gable ends ( low end, high end ). gable paints the gable
    ends' triangles (None leaves one out, as gables does). hull fills the roof's space with a collision hull (no attic
    floor for the navmesh); slab_surface gives the slabs their own collision instead, for a roof seen from inside.
    gutter paints a gutter along each eave, under the tiles' edge (downpipe() meets it). Returns the ridge height. """
    t = math.tan( math.radians( pitch ) )
    if ridge_axis == "e":
        along, across = np.array( ( 1.0, 0.0, 0.0 ) ), np.array( ( 0.0, 1.0, 0.0 ) )
        a0, a1, c0, c1 = e0, e1, n0, n1
    else:
        along, across = np.array( ( 0.0, 1.0, 0.0 ) ), np.array( ( 1.0, 0.0, 0.0 ) )
        a0, a1, c0, c1 = n0, n1, e0, e1
    half = ( c1 - c0 ) / 2
    mid = ( c0 + c1 ) / 2
    ridge = eave + half * t

    def point( a, c, z ):
        return along * a + across * c + np.array( ( 0.0, 0.0, z ) )

    length = ( a1 + ends_over[1] ) - ( a0 - ends_over[0] )
    a_mid = ( ( a1 + ends_over[1] ) + ( a0 - ends_over[0] ) ) / 2
    for side in ( -1, 1 ):
        low = point( a_mid, mid + side * ( half + over ), eave - over * t )
        high = point( a_mid, mid, ridge )
        y_axis = normalise( high - low )
        x_axis = along.copy()
        z_axis = np.cross( x_axis, y_axis )
        if z_axis[2] < 0:
            x_axis = -x_axis
            z_axis = -z_axis
        centre = ( low + high ) / 2 - z_axis * thick / 2
        model.oriented_box( centre, ( x_axis, y_axis, z_axis ), ( length, np.linalg.norm( high - low ), thick ),
                            { "+z": tiles, "-z": soffit, "default": trim }, slab_surface )
    if cap:
        model.beam( point( a0 - ends_over[0], mid, ridge + 1.5 ), point( a1 + ends_over[1], mid, ridge + 1.5 ), ( 9, 6 ), tiles )
    for a, towards, draw in ( ( a0, -along, gables[0] ), ( a1, along, gables[1] ) ):
        if gable and draw:
            facing( model, gable, [ point( a, c0, eave ), point( a, c1, eave ), point( a, mid, ridge ) ], towards )
    if hull:
        pts = [ point( a, c, z ) for a in ( a0, a1 ) for c, z in ( ( c0, eave ), ( c1, eave ), ( mid, ridge ) ) ]
        model.hull( [ tuple( p ) for p in pts ], hull )
    if gutter:
        # Gutters hang just inside the tiles' edge and under it, the length of the eaves.
        for side in ( -1, 1 ):
            g0 = point( a0 - ends_over[0] + 1, mid + side * ( half + over - 1.2 ), eave - over * t - 4.0 )
            g1 = point( a1 + ends_over[1] - 1, mid + side * ( half + over - 1.2 ), eave - over * t - 4.0 )
            axle( model, ( g0 + g1 ) / 2, along, 2.4, float( np.linalg.norm( g1 - g0 ) ), { "side": gutter, "end": gutter },
                  sides=8 )
    return ridge


# ---------------------------------------------------------------------------------------------------------------------
# Walls' openings: glass, frames, shutters, doors and shopfronts

def wall_out( wall ):
    """ The wall's outer face ( d ), which way out is along d ( +1 / -1 ) and the outward plan vector. """
    d, sign = wall.outer()
    out = np.zeros( 3 )
    out[1 if wall.axis == "e" else 0] = sign
    return d, sign, out


def outline( o, steps=10 ):
    """ ( r, z ) round an opening, counter-clockwise from its bottom left seen from its high-d side. """
    if o.arched:
        return [ ( o.r0, o.z0 ), ( o.r1, o.z0 ) ] + arc( ( o.r0 + o.r1 ) / 2, o.spring, o.radius, steps, 0.0, 180.0 )
    return [ ( o.r0, o.z0 ), ( o.r1, o.z0 ), ( o.r1, o.z1 ), ( o.r0, o.z1 ) ]


def slab_at( model, wall, r0, r1, depth0, depth1, z0, z1, paint, surface=None ):
    """ A box on the wall: along r0..r1, from depth0 to depth1 out of its outer face (negative: into the wall). """
    d, sign, _ = wall_out( wall )
    lo, hi = wall.lo_hi( r0, r1, d + sign * depth0, d + sign * depth1, z0, z1 )
    model.box( lo, hi, paint, surface )


def pane( model, wall, o, paint, depth ):
    """ The opening filled flush at depth into the wall. """
    d, sign, out = wall_out( wall )
    facing( model, paint, [ wall.point( r, d - sign * depth, z ) for r, z in outline( o ) ], out )


def frame( model, wall, o, paint, depth, bar=3.0, thick=3.0, mullion=True, head=True, foot=True ):
    """ A window or door frame in the plane depth into the wall: sides, head and foot, and a cross for glazing. """
    top = o.spring if o.arched else o.z1
    d0, d1 = -depth - thick / 2, -depth + thick / 2
    slab_at( model, wall, o.r0, o.r0 + bar, d0, d1, o.z0, top, paint )
    slab_at( model, wall, o.r1 - bar, o.r1, d0, d1, o.z0, top, paint )
    if foot:
        slab_at( model, wall, o.r0 + bar, o.r1 - bar, d0, d1, o.z0, o.z0 + bar, paint )
    if head and not o.arched:
        slab_at( model, wall, o.r0 + bar, o.r1 - bar, d0, d1, o.z1 - bar, o.z1, paint )
    if mullion:
        rc = ( o.r0 + o.r1 ) / 2
        slab_at( model, wall, rc - bar / 2, rc + bar / 2, d0 + 0.5, d1 - 0.5, o.z0 + bar, top - ( 0 if o.arched else bar ), paint )
        zt = o.z0 + 0.62 * ( top - o.z0 )
        slab_at( model, wall, o.r0 + bar, o.r1 - bar, d0 + 0.5, d1 - 0.5, zt - bar / 2, zt + bar / 2, paint )


def room_beside( wall, r0, r1 ):
    """ Is the wall clear of other openings from r0 to r1, and within its run? """
    if r0 < wall.run[0] + 4 or r1 > wall.run[1] - 4:
        return False
    return not any( o.r0 < r1 + 4 and o.r1 > r0 - 4 for o in wall.openings if not ( o.r0 >= r0 and o.r1 <= r1 ) )


def keyed( *key ):
    """ A steady hash of key (numbers to a tenth), for choices that mustn't draw on the shared rng: every draw from it
    would move every house's choices after it. """
    text = ",".join( f"{float( k ):.1f}" if isinstance( k, ( int, float, np.integer, np.floating ) ) else str( k )
                     for k in key )
    return zlib.crc32( text.encode() )


def pick( options, *key ):
    return options[keyed( *key ) % len( options )]


def chance( share, *key ):
    return ( keyed( *key ) % 10007 ) / 10007.0 < share


def card( model, paint, points, towards, uv=None, both=False ):
    """ A polygon wound to face towards, as facing() winds it, with uv (one ( u, v ) a point, kept with its point when
    the winding turns) and its back drawn too if both. """
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
        if uv is not None:
            uv = list( uv[:1] ) + list( uv[:0:-1] )
    model.polygon( paint, pts, both_sides=both, uv=uv )


def r_right( wall ):
    """ +1 where r runs to the right of someone looking at the wall's outer face, -1 where it runs to their left. """
    return 1.0 if wall.outward in ( "-n", "+e" ) else -1.0


def picture( model, wall, r0, r1, z0, z1, depth, paint, crop=None, both=False ):
    """ A picture on the wall over r0..r1, z0..z1, depth out of its outer face (negative: into it), facing out. crop
    ( u0, u1, v0, v1 ) shows that part of a decal paint's picture, the right way round from in front (a mirrored half
    shows it mirrored, so no lettering); without it the whole picture is stretched across (map_kit's decals). """
    d, sign, out = wall_out( wall )
    pts = [ wall.point( r0, d + sign * depth, z0 ), wall.point( r1, d + sign * depth, z0 ),
            wall.point( r1, d + sign * depth, z1 ), wall.point( r0, d + sign * depth, z1 ) ]
    uv = None
    if crop is not None:
        u0, u1, v0, v1 = crop
        if r_right( wall ) < 0:
            u0, u1 = u1, u0
        uv = [ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ]
    card( model, paint, pts, out, uv, both )


def shutters_open( model, wall, o, paint ):
    """ A pair of louvred shutters folded back flat against the wall either side of a window, where there's room: a leaf
    a side, or a wide window's leaves folded side by side. """
    width = ( o.r1 - o.r0 ) / 2
    left, right = ( o.r0 - 2 - width, o.r0 - 2 ), ( o.r1 + 2, o.r1 + 2 + width )
    if not ( room_beside( wall, *left ) and room_beside( wall, *right ) ):
        return False
    louvre = LOUVRES.get( paint )
    leaves = max( 1, round( width / 24 ) )
    for r0, r1 in ( left, right ):
        if louvre and leaves == 1:
            slab_at( model, wall, r0, r1, 0.0, 2.0, o.z0, o.z1, { wall.outward: f"louvre_{louvre}", "default": paint } )
            continue
        slab_at( model, wall, r0, r1, 0.0, 2.0, o.z0, o.z1, { "default": paint } )
        if louvre:
            step = ( r1 - r0 ) / leaves
            for k in range( leaves ):
                picture( model, wall, r0 + k * step + 0.15, r0 + ( k + 1 ) * step - 0.15, o.z0, o.z1, 2.05,
                         f"louvre_{louvre}" )
    return True


def dress( model, wall, style, rng ):
    """ Fill and trim a wall's openings. style: 'trim', 'shutter', 'sill', 'door', 'roller', 'awning' (canvas paint or
    None), 'sign', 'surround' (paint or None), 'names' (a list of belltower_fronts.SIGNS' names for its shops' signs,
    used up in turn), and 'solid' (True for a house nobody goes into: every opening is closed, and its glass shows the
    rooms behind it). """
    trim, shutter = style["trim"], style.get( "shutter" )
    solid = style.get( "solid" )
    louvre = LOUVRES.get( shutter )
    for o in wall.openings:
        kind = o.kind
        width = o.r1 - o.r0
        rc = ( o.r0 + o.r1 ) / 2
        key = ( wall.outward, wall.across[0], rc, o.z0 )
        if kind in ( "glass", "glass_arch" ):
            closed = solid and shutter and not o.arched and rng.random() < 0.22
            if closed:
                slab_at( model, wall, o.r0, o.r1, -5.0, -3.0, o.z0, o.z1,
                         { wall.outward: f"louvre_pair_{louvre}", "default": shutter } if louvre else shutter )
            else:
                room = solid and not o.arched and not style.get( "glass_surface" )
                pane( model, wall, o, f"window_{pick( 'abcd', *key )}" if room else "glass", 5.0 )
                frame( model, wall, o, trim, 4.0 )
                if style.get( "glass_surface" ):
                    # In a building people go into, the pane stops shots too.
                    slab_at( model, wall, o.r0, o.r1, -6.0, -4.0, o.z0, o.z1, None, style["glass_surface"] )
                if room and o.z0 > 120 and o.z1 - o.z0 < 80 and chance( 0.35, "box", *key ):
                    window_box( model, wall, o, key )
            if o.z0 > 20 and not o.arched:
                slab_at( model, wall, o.r0 - 3, o.r1 + 3, -0.5, 3.0, o.z0 - 4, o.z0, style.get( "sill", "ashlar" ) )
            if not closed and shutter and not o.arched and style.get( "shutters", True ) and rng.random() < 0.8:
                shutters_open( model, wall, o, shutter )
        elif kind == "window":
            frame( model, wall, o, trim, 1.5, mullion=False )
            if o.z0 > 20:
                slab_at( model, wall, o.r0 - 3, o.r1 + 3, -0.5, 3.0, o.z0 - 4, o.z0, style.get( "sill", "ashlar" ) )
            if shutter and style.get( "shutters", True ):
                shutters_open( model, wall, o, shutter )
        elif kind == "shut":
            slab_at( model, wall, o.r0, o.r1, -8.0, -6.0, o.z0, o.z1, style.get( "door", "planks_dark" ) )
            frame( model, wall, o, trim, 5.0, mullion=False, foot=False )
            if solid and 40 <= width <= 60:
                # A pair of panelled street doors inside the frame, over a stone step.
                picture( model, wall, o.r0 + 3, o.r1 - 3, o.z0, o.z1 - 3, -5.95, f"door_{pick( 'abcde', 'door', *key )}" )
                slab_at( model, wall, o.r0 - 3, o.r1 + 3, -6.0, 4.0, 0.0, 1.5, "ashlar" )
                if chance( 0.6, "lantern", *key ):
                    # A lantern on a bracket beside it, on whichever side has room, else over it.
                    side = pick( ( -1, 1 ), "lantern_side", *key )
                    for r, z_top in ( ( rc + side * ( width / 2 + 12 ), o.z1 + 14 ), ( rc - side * ( width / 2 + 12 ), o.z1 + 14 ),
                                      ( rc, o.z1 + 32 ) ):
                        if wall_lantern( model, wall, r, z_top, but=o ):
                            break
                if chance( 0.4, "pots", *key ):
                    # Potted bushes beside it, as people keep at their front doors: a pair, or one.
                    sides = ( -1, 1 ) if chance( 0.5, "pair", *key ) else ( pick( ( -1, 1 ), "pot_side", *key ), )
                    for side in sides:
                        door_pot( model, wall, rc + side * ( width / 2 + 15 ), ( *key, side ) )
            elif width < 70:
                slab_at( model, wall, o.r0 + width * 0.25, o.r1 - width * 0.25, -6.0, -5.0, o.z0 + 38, o.z0 + 40, "iron_black" )
        elif kind == "door":
            frame( model, wall, o, trim, 1.5, mullion=False, foot=False )
        elif kind == "shop":
            roller = style.get( "roller", "roller_grey" )
            glazed = rng.random() < 0.4
            if glazed:
                if solid:
                    # The shop behind its window: the middle of belltower_fronts' shopfront, as wide as the glass.
                    span = min( 1.0, width / 112.0 )
                    picture( model, wall, o.r0, o.r1, o.z0, o.z1, -6.0, f"shopfront_{pick( 'abc', 'shop', *key )}",
                             crop=( 0.5 - span / 2, 0.5 + span / 2, 0.0, 1.0 ) )
                else:
                    pane( model, wall, o, "glass", 6.0 )
                frame( model, wall, o, trim, 5.0, bar=4.0 )
                slab_at( model, wall, o.r0, o.r1, -6.0, -1.0, o.z0, o.z0 + 24, trim )
            else:
                pane( model, wall, o, roller, 4.0 )
                slab_at( model, wall, o.r0, o.r1, -4.0, 4.0, o.z1 - 12, o.z1, "iron_black" )
            name = shop_name( style, glazed, key )
            canvas = style.get( "awning" )
            sign = style.get( "sign", trim )
            o.awning = bool( canvas )
            if canvas:
                awning( model, wall, o.r0 - 6, o.r1 + 6, o.z1 + 34, 54, canvas, name )
            elif name is not None:
                # The shop's painted board over its window, belltower_fronts' 120 x 22 at most.
                bw = min( width + 8, 120.0 )
                bh = bw * 22 / 120
                zc = o.z1 + 17
                slab_at( model, wall, rc - bw / 2, rc + bw / 2, 0.0, 2.5, zc - bh / 2, zc + bh / 2,
                         { wall.outward: f"sign_{name}", "default": sign } )
            elif chance( 0.5, "fascia", *key ):
                # A shut shop's board, its name painted out.
                slab_at( model, wall, o.r0 - 4, o.r1 + 4, 0.0, 2.5, o.z1 + 6, o.z1 + 28, { "default": sign } )
        if style.get( "surround" ) and kind in ( "glass", "window" ) and not o.arched:
            band = 5.0
            paint = style["surround"]
            slab_at( model, wall, o.r0 - band, o.r0, 0.0, 1.5, o.z0, o.z1 + band, paint )
            slab_at( model, wall, o.r1, o.r1 + band, 0.0, 1.5, o.z0, o.z1 + band, paint )
            slab_at( model, wall, o.r0, o.r1, 0.0, 1.5, o.z1, o.z1 + band, paint )
            # Its hood: a little cornice over the head, which throws a line of shadow, where it clears the eaves and
            # the openings beside it.
            if o.z1 + band + 4.5 <= wall.z[1] and room_beside( wall, o.r0 - band - 2, o.r1 + band + 2 ):
                slab_at( model, wall, o.r0 - band - 2, o.r1 + band + 2, 0.0, 3.0, o.z1 + band, o.z1 + band + 2.5, paint )


def shop_name( style, glazed, key ):
    """ Which of belltower_fronts.SIGNS a shop's sign shows: the style's own names first, then the town's in turn. A shut
    shop may have lost its name (None). """
    names = style.get( "names" )
    if names:
        return names.pop( 0 )
    if not ( glazed or chance( 0.6, "name", *key ) ):
        return None
    name = SHOP_NAMES[_shops[0] % len( SHOP_NAMES )]
    _shops[0] += 1
    return name


def door_pot( model, wall, r, key ):
    """ A terracotta pot with a clipped bush, against the wall at r beside a street door, where there's room. Its
    collision is a box the pot's size. """
    if not room_beside( wall, r - 11, r + 11 ):
        return False
    d, sign, _ = wall_out( wall )
    c = wall.point( r, d + sign * 12, 0.0 )
    Detail.lathe( model, c[:2], 0.0, [ ( 7.0, 0.0 ), ( 9.0, 15.0 ), ( 10.2, 15.5 ), ( 10.2, 18.0 ), ( 9.2, 18.0 ), ( 9.0, 16.5 ) ],
                  "clay_pot", sides=14 )
    soil = [ np.array( ( c[0] + 9.0 * math.cos( t ), c[1] + 9.0 * math.sin( t ), 16.5 ) )
             for t in np.linspace( 0.0, 2 * math.pi, 14, endpoint=False ) ]
    Detail.outward( model, "soil", soil, ( 0, 0, 1 ) )
    size = 10.0 + keyed( "pot_size", *key ) % 5
    Detail.shrub( model, ( c[0], c[1], 17.0 + size * 0.6 ), size, squash=0.9, seed=keyed( "pot", *key ) )
    model.collision_box( ( c[0] - 9, c[1] - 9, 0 ), ( c[0] + 9, c[1] + 9, 18 ), TILE )
    return True


def window_box( model, wall, o, key ):
    """ A window box of geraniums on two iron brackets under an upper window, some of it trailing over the front. Cards
    of belltower_fronts' planting, no collision. """
    d, sign, _ = wall_out( wall )
    rc = ( o.r0 + o.r1 ) / 2
    r0, r1, z0 = rc - 20, rc + 20, o.z0
    slab_at( model, wall, r0, r1, 3.0, 10.0, z0 - 8, z0 + 2, { "+z": "soil", "default": "planks_dark" } )
    for r in ( r0 + 4, r1 - 5 ):
        slab_at( model, wall, r, r + 1, 0.0, 9.0, z0 - 9, z0 - 8, "iron_black" )
        model.beam( wall.point( r + 0.5, d + sign * 0.5, z0 - 18 ), wall.point( r + 0.5, d + sign * 8.5, z0 - 8.5 ), ( 1, 1 ),
                    "iron_black" )
    back, front = pick( ( ( "red", "pink" ), ( "pink", "red" ), ( "red", "red" ) ), "flowers", *key )
    picture( model, wall, r0 + 1, r1 - 1, z0 + 1, z0 + 17, 5.5, f"geranium_{back}" )
    picture( model, wall, r0 + 1, r1 - 1, z0 - 1, z0 + 15, 8.0, f"geranium_{front}" )
    picture( model, wall, r0 + 1, r1 - 1, z0 - 17.5, z0 + 2.5, 10.3, "trailing" )


def awning( model, wall, r0, r1, z, reach, paint, name=None ):
    """ A canvas awning off the wall from z, sloping down and out by reach, with side cheeks and a scalloped valance
    along its front carrying the shop's name (name: belltower_fronts.SIGNS' index) in cut-out letters. No collision. """
    d, sign, out = wall_out( wall )
    key = AWNING_KEYS.get( paint )
    canvas, flap = ( f"awning_{key}", f"valance_{key}" ) if key else ( paint, paint )
    drop = reach * 0.45
    slope = math.hypot( reach, drop )
    length = r1 - r0
    front = d + sign * reach
    top = z - drop
    # The canvas: belltower_fronts' 48 x 48 tile, x along the front and y up the slope from the front edge.
    p = [ wall.point( r0, d, z ), wall.point( r1, d, z ), wall.point( r1, front, top ), wall.point( r0, front, top ) ]
    uv = [ ( 0.0, slope / 48 ), ( length / 48, slope / 48 ), ( length / 48, 0.0 ), ( 0.0, 0.0 ) ] if key else None
    card( model, canvas, p, out + np.array( ( 0, 0, 2.0 ) ), uv, both=True )
    for r, side in ( ( r0, -1 ), ( r1, 1 ) ):
        along = np.zeros( 3 )
        along[0 if wall.axis == "e" else 1] = side
        card( model, canvas, [ wall.point( r, d, z ), wall.point( r, front, top ), wall.point( r, front, top - 12 ) ], along,
              both=True )
    # The valance, 48 x 12 a repeat.
    v = [ wall.point( r0, front, top - 12 ), wall.point( r1, front, top - 12 ), wall.point( r1, front, top ),
          wall.point( r0, front, top ) ]
    card( model, flap, v, out, [ ( 0.0, 0.0 ), ( length / 48, 0.0 ), ( length / 48, 1.0 ), ( 0.0, 1.0 ) ] if key else None,
          both=True )
    if name is not None and key:
        lw = min( length - 4, 117.0 )
        lh = lw * 10 / 130
        rc, zc, f = ( r0 + r1 ) / 2, top - 4.6, front + sign * 0.25
        facing( model, f"letters_{name}", [ wall.point( rc - lw / 2, f, zc - lh / 2 ), wall.point( rc + lw / 2, f, zc - lh / 2 ),
                                             wall.point( rc + lw / 2, f, zc + lh / 2 ), wall.point( rc - lw / 2, f, zc + lh / 2 ) ],
                out )


def balcony( model, wall, r0, r1, z, reach=30.0, rail="iron_black", slab="ashlar", key=None ):
    """ A balcony on the wall at floor height z: a stone slab on two stepped corbels and a wrought-iron railing (a cut-out
    card of belltower_fronts' railing) with its handrail and corner posts, sometimes with a bougainvillea over it
    (key: the window's, for the choice). No collision: it's out of reach. """
    d, sign, out = wall_out( wall )
    slab_at( model, wall, r0, r1, 0.0, reach, z - 7, z, slab )
    for r in ( r0 + 5, r1 - 13 ):
        slab_at( model, wall, r, r + 8, 0.0, reach - 8, z - 13, z - 7, slab )
        slab_at( model, wall, r + 1, r + 7, 0.0, reach - 18, z - 19, z - 13, slab )
    f = reach - 1.0
    a, b = r0 + 1, r1 - 1
    rails = [ ( [ wall.point( a, d + sign * f, z ), wall.point( b, d + sign * f, z ), wall.point( b, d + sign * f, z + 36 ),
                  wall.point( a, d + sign * f, z + 36 ) ], out, b - a ) ]
    for r, side in ( ( a, -1 ), ( b, 1 ) ):
        along = np.zeros( 3 )
        along[0 if wall.axis == "e" else 1] = side
        rails.append( ( [ wall.point( r, d + sign * 0.5, z ), wall.point( r, d + sign * f, z ), wall.point( r, d + sign * f, z + 36 ),
                          wall.point( r, d + sign * 0.5, z + 36 ) ], along, f - 0.5 ) )
    for pts, towards, span in rails:
        card( model, "railing", pts, towards, [ ( 0.0, 0.0 ), ( span / 36, 0.0 ), ( span / 36, 1.0 ), ( 0.0, 1.0 ) ], both=True )
    slab_at( model, wall, a - 0.75, b + 0.75, f - 0.9, f + 0.9, z + 34.5, z + 36.5, rail )
    for r in ( a, b ):
        slab_at( model, wall, r - 0.9, r + 0.9, 0.0, f + 0.9, z + 34.5, z + 36.5, rail )
        slab_at( model, wall, r - 0.75, r + 0.75, f - 0.75, f + 0.75, z, z + 34.5, rail )
    if key is not None and chance( 0.3, "bougainvillea", *key ):
        lo, hi = ( a, a + 44 ) if chance( 0.5, "side", *key ) else ( b - 44, b )
        picture( model, wall, lo, hi, z - 14, z + 34, f + 1.2, "bougainvillea" )


def downpipe( model, wall, r, eave, paint, over=14.0 ):
    """ A rainwater pipe down the wall at r from the gutter under the eaves (gable_roof's, over out) to the ground: a
    swan neck under the cornice, a bracket a storey. Drawn only. """
    d, sign, _ = wall_out( wall )
    t = math.tan( math.radians( ROOF_PITCH ) )
    stand, top = 4.0, eave - 26.0
    out_g, z_g = over - 1.2, eave - over * t - 4.0
    base = wall.point( r, d + sign * stand, 0.0 )
    model.cylinder( base[:2], 1.6, 0.0, top, { "side": paint, "top": paint, "bottom": paint }, sides=8 )
    model.cylinder( base[:2], 2.1, 0.0, 10.0, { "side": paint, "top": paint, "bottom": paint }, sides=8 )
    model.beam( wall.point( r, d + sign * stand, top - 1.0 ), wall.point( r, d + sign * out_g, z_g - 3.5 ), ( 3.0, 3.0 ), paint )
    model.beam( wall.point( r, d + sign * out_g, z_g - 3.5 ), wall.point( r, d + sign * out_g, z_g ), ( 3.0, 3.0 ), paint )
    for zb in np.arange( 70.0, top - 10.0, 110.0 ):
        slab_at( model, wall, r - 2.2, r + 2.2, 0.0, stand + 2.0, zb, zb + 1.2, "iron_black" )


def keep_clear( o ):
    """ The wall round an opening that dress() and solid_house() may put things on, as ( r0, r1, z0, z1 ) boxes: a
    window's folded shutters, sill and window box, a balcony's slab, railing and corbels, a shop's board or awning, a
    door's frame. """
    width, rc = o.r1 - o.r0, ( o.r0 + o.r1 ) / 2
    if o.kind in ( "glass", "glass_arch", "window" ):
        boxes = [ ( o.r0 - width / 2 - 3, o.r1 + width / 2 + 3, o.z0 - 6, o.z1 + 4 ) ]
        if o.z0 > 120 and o.z1 - o.z0 < 80:
            boxes.append( ( rc - 21, rc + 21, o.z0 - 20, o.z0 ) )
        if o.z1 - o.z0 > 85:
            boxes += [ ( rc - 35, rc + 35, o.z0 - 8, o.z0 + 37 ), ( rc - 30, rc + 30, o.z0 - 20, o.z0 ) ]
        return boxes
    if o.kind == "shop":
        # Up to its awning's top, or its board's (dress() notes which it got; until then, the awning).
        return [ ( o.r0 - 9, o.r1 + 9, o.z0 - 4, o.z1 + ( 44 if getattr( o, "awning", True ) else 30 ) ) ]
    return [ ( o.r0 - 4, o.r1 + 4, o.z0 - 4, o.z1 + 4 ) ]


def fixture_room( wall, r0, r1, z0, z1, but=None ):
    """ Is the wall clear for a fixture over r0..r1, z0..z1: inside its run by 12 (downpipes come down its ends), clear of
    its openings' keep_clear() and of the fixtures already on it (wall.fixtures)? but: the opening it goes with. """
    if r0 < wall.run[0] + 12 or r1 > wall.run[1] - 12:
        return False
    for o in wall.openings:
        if o is not but and any( a < r1 and b > r0 and c < z1 and d > z0 for a, b, c, d in keep_clear( o ) ):
            return False
    return not any( a < r1 + 2 and b > r0 - 2 and c < z1 and d > z0 for a, b, c, d in getattr( wall, "fixtures", () ) )


def wall_lantern( model, wall, r, z_top, but=None, reach=15.0, scale=0.8 ):
    """ A lantern hanging from a wrought-iron bracket on the wall at r: a back plate, an arm reach out at z_top with a
    brace and a scroll under it, a finial on its end and the lantern (belltower_detail's, scale 0.8) on a hook near it.
    Only where fixture_room() finds the wall clear; it's then noted in wall.fixtures. Drawn only. """
    box = ( r - 6, r + 6, z_top - 22, z_top + 3 )
    if not fixture_room( wall, *box, but=but ):
        return False
    wall.fixtures = list( getattr( wall, "fixtures", () ) ) + [ box ]
    d, sign, out = wall_out( wall )

    def at( depth, z ):
        return wall.point( r, d + sign * depth, z )
    slab_at( model, wall, r - 2.5, r + 2.5, 0.0, 1.0, z_top - 10, z_top + 3, "iron_black" )
    model.beam( at( 1.0, z_top ), at( reach, z_top ), ( 1.2, 1.2 ), "iron_black" )
    model.beam( at( 1.0, z_top - 8 ), at( 9.0, z_top ), ( 0.9, 0.9 ), "iron_black" )
    Detail.hoop( model, at( 4.6, z_top - 3.4 ), out, ( 0, 0, 1.0 ), 2.4, 0.35, "iron_black" )
    Detail.ball( model, at( reach + 0.6, z_top ), 0.9, "iron_black", rings=4, segments=8 )
    hook = at( reach - 2.0, z_top )
    Detail.rod( model, hook, hook - ( 0, 0, 1.2 ), 0.3, "iron_black", sides=6 )
    Detail.hanging_lantern( model, hook - ( 0, 0, 1.2 ), yaw=math.degrees( math.atan2( out[1], out[0] ) ), scale=scale )
    return True


PLAQUE = ( 24.0, 9.0 )      # belltower_fronts' street plaques, w x h


def street_plaque( model, wall, end, paint ):
    """ A street's name on a marble plaque an inch proud of the wall (paint: one of belltower_fronts' plaque pictures),
    as near the wall's corner at end (0: its run's low end, 1: its high end) as fixture_room() allows: just under the
    first floor's string course, else just over it (over a shop's board), else over a shop's awning. It's then noted in
    wall.fixtures. Drawn only. """
    w, h = PLAQUE
    for inset in ( 14.0, 24.0, 34.0, 44.0, 54.0, 64.0 ):
        r0 = wall.run[0] + inset if end == 0 else wall.run[1] - inset - w
        for z0 in ( 110.0, 134.0, 148.0 ):
            if fixture_room( wall, r0, r0 + w, z0, z0 + h ):
                wall.fixtures = list( getattr( wall, "fixtures", () ) ) + [ ( r0, r0 + w, z0, z0 + h ) ]
                slab_at( model, wall, r0, r0 + w, 0.0, 1.0, z0, z0 + h, { wall.outward: paint, "default": "ashlar" } )
                return True
    return False


def ghost_sign( model, wall, r0, r1, z0, paint ):
    """ An old sign painted on the render over r0..r1 from z0 (paint: one of belltower_fronts' ghost pictures, 4 : 1),
    a hair proud of the wall so it doesn't flicker into it. The wall must be clear there (fixture_room()); it's then
    noted in wall.fixtures. Drawn only. """
    z1 = z0 + ( r1 - r0 ) / 4
    assert fixture_room( wall, r0, r1, z0, z1 ), ( "no room for", paint, wall.outward, r0, z0 )
    wall.fixtures = list( getattr( wall, "fixtures", () ) ) + [ ( r0, r1, z0, z1 ) ]
    picture( model, wall, r0, r1, z0, z1, 0.25, paint )


IVY = ( 48.0, 96.0 )        # belltower_fronts' ivy patches, w x h


def ivy( model, wall, rc, z0, scale, paint="ivy_climb", out=3.2, key=() ):
    """ A patch of ivy on the wall centred on rc, scale times belltower_fronts' 48 x 96 (paint: ivy_climb, rooted at z0,
    or ivy_hang, coming over the wall's top at z0), out from its face: in front of a plinth or a coping. Only where
    fixture_room() finds the wall clear; it's then noted in wall.fixtures. key picks which way round it shows. Drawn
    only. """
    w, h = IVY[0] * scale, IVY[1] * scale
    z_lo, z_hi = ( z0, z0 + h ) if paint == "ivy_climb" else ( z0 - h, z0 )
    box = ( rc - w / 2, rc + w / 2, z_lo, z_hi )
    if not fixture_room( wall, *box ):
        return False
    wall.fixtures = list( getattr( wall, "fixtures", () ) ) + [ box ]
    crop = ( 1.0, 0.0, 0.0, 1.0 ) if chance( 0.5, "ivy_flip", *key ) else ( 0.0, 1.0, 0.0, 1.0 )
    picture( model, wall, box[0], box[1], z_lo, z_hi, out, paint, crop=crop )
    return True


def climb_ivy( model, wall, scale, key, z0=0.0, out=3.2 ):
    """ A patch of ivy climbing the wall from z0 (ivy()) where it's clear: beside a door if there's room there, else at
    whichever clear spot key picks. Returns whether there was room anywhere. """
    w, h = IVY[0] * scale, IVY[1] * scale
    clear = [ float( rc ) for rc in np.arange( wall.run[0] + 12 + w / 2, wall.run[1] - 12 - w / 2 + 1e-6, 4.0 )
              if fixture_room( wall, rc - w / 2, rc + w / 2, z0, z0 + h ) ]
    if not clear:
        return False
    doors = [ o for o in wall.openings if o.kind in ( "shut", "door" ) ]
    by_door = [ rc for rc in clear if any( min( abs( rc - w / 2 - o.r1 ), abs( o.r0 - rc - w / 2 ) ) < 14 for o in doors ) ]
    return ivy( model, wall, pick( by_door or clear, "ivy_spot", *key ), z0, scale, "ivy_climb", out, key )


def wall_top_ivy( model, axis, run, across, outward, z0, z1, gaps, key, every=150.0, share=0.5, piers=True ):
    """ Ivy hanging over a garden wall's top (wall_run's, z0..z1) down its outward face, here and there along it: a
    patch at each step of every where chance() says so, clear of its gaps and their piers (piers: wall_run's, 18 wide
    and capped 2 wider, either side of each gap), its longest stems ending above the wall's foot. """
    wall = Wall( axis, run, across, ( z0, z1 ), outward )
    for g0, g1 in gaps:
        wall.add( ( g0 + g1 ) / 2, g1 - g0 + ( 36 if piers else 0 ), z0, z1 + 30, "gap" )
    longest = ( z1 - z0 ) / ( 0.85 * IVY[1] )
    for k, rc in enumerate( np.arange( run[0] + every / 2, run[1], every ) ):
        at = key + ( k, )
        if chance( share, "hang", *at ):
            rc += pick( ( -24, -12, 0, 12, 24 ), "hang_shift", *at )
            scale = min( pick( ( 0.9, 1.0, 1.15 ), "hang_scale", *at ), longest )
            ivy( model, wall, rc, z1 + 0.5, scale, "ivy_hang", 2.4, at )


def bands( model, wall, levels, paint, skip=() ):
    """ String courses: a thin stone band along the wall at each level, broken for openings that cross it. """
    for z in levels:
        cuts = sorted( ( o.r0, o.r1 ) for o in wall.openings if o.z0 < z + 6 and o.z1 > z )
        r = wall.run[0]
        for c0, c1 in cuts + [ ( wall.run[1], wall.run[1] ) ]:
            if c0 > r + 1:
                slab_at( model, wall, r, c0, 0.0, 2.0, z, z + 6, paint )
            r = max( r, c1 )


# ---------------------------------------------------------------------------------------------------------------------
# Houses nobody goes into

FACE_AXIS = { "+n": "e", "-n": "e", "+e": "n", "-e": "n" }


def face_wall( e0, e1, n0, n1, face, z0, z1, thick=12.0, run=None, corners=False ):
    """ The Wall for one side of a box, its outside facing face. run limits it (a front partly hidden). An e side's
    wall stops thick short of the corners (the n sides' walls fill them) unless corners is set. """
    if face in ( "+n", "-n" ):
        across = ( n1 - thick, n1 ) if face == "+n" else ( n0, n0 + thick )
        return Wall( "e", run or ( e0, e1 ), across, ( z0, z1 ), face )
    across = ( e1 - thick, e1 ) if face == "+e" else ( e0, e0 + thick )
    return Wall( "n", run or ( ( n0, n1 ) if corners else ( n0 + thick, n1 - thick ) ), across, ( z0, z1 ), face )


def side_of( box, face ):
    """ A box's side: the plane it's in, and its run ( r0, r1 ) along e (for '+n' / '-n') or n. """
    e0, e1, n0, n1 = box[:4]
    if face in ( "+n", "-n" ):
        return ( n1 if face == "+n" else n0 ), ( e0, e1 )
    return ( e1 if face == "+e" else e0 ), ( n0, n1 )


def exposure( box, face, blocks ):
    """ The parts of a house's side that show: [ ( r0, r1, z0 ) ] along its run, each from z0 (the top of whatever stands
    against it there: 0 where nothing does) up to the house's eaves. box and blocks are ( e0, e1, n0, n1, height ). """
    plane, run = side_of( box, face )
    opposite = { "+n": "-n", "-n": "+n", "+e": "-e", "-e": "+e" }[face]
    covers = []
    for block in blocks:
        edge, r = side_of( block, opposite )
        lo, hi = max( r[0], run[0] ), min( r[1], run[1] )
        if abs( edge - plane ) < 1 and hi - lo > 1:
            covers.append( ( lo, hi, block[4] ) )
    cuts = sorted( { *run } | { c for lo, hi, _ in covers for c in ( lo, hi ) } )
    pieces = []
    for a, b in zip( cuts, cuts[1:] ):
        mid = ( a + b ) / 2
        z0 = max( [ h for lo, hi, h in covers if lo <= mid <= hi ], default=0.0 )
        if z0 >= box[4] - 0.5:
            continue
        if pieces and abs( pieces[-1][1] - a ) < 1e-6 and pieces[-1][2] == z0:
            pieces[-1] = ( pieces[-1][0], b, z0 )
        else:
            pieces.append( ( a, b, z0 ) )
    return pieces


def shows_at( pieces, r, z ):
    """ Does the side show at r (along its run) at height z? """
    return any( a - 1 <= r <= b + 1 and z0 <= z for a, b, z0 in pieces )


def floors_of( eave ):
    """ The upper floors' heights for a house whose eaves are at eave. """
    levels = []
    z = GROUND_STOREY
    while z + 34 + 72 + 16 <= eave:
        levels.append( z )
        z += STOREY
    return levels


def subtract( span, cut ):
    """ The parts of span ( a, b ) outside cut ( c0, c1 ) (None: all of it). """
    a, b = span
    if cut is None or cut[1] <= a or cut[0] >= b:
        return [ span ]
    return [ p for p in ( ( a, cut[0] ), ( cut[1], b ) ) if p[1] - p[0] > 1 ]


def solid_house( model, e0, e1, n0, n1, eave, render, faces, ridge, rng, blocks, roof="roof_tiles", trim="trim_white",
                 shutter="shutter_green", sign="trim_red", awning_paint=None, surround=None,
                 ends_over=( 14.0, 14.0 ), gables=( True, True ), balconies=0.25, plinth="ashlar_grey", names=(),
                 plaques=() ):
    """ A house nobody goes into: one collision box up to its eaves and its roof's hull, with the fronts in faces drawn
    over it. faces maps a face ('+n', '-n', '+e', '-e') to ( ground, run ): ground is a letter a bay along the ground
    floor ('s' shop, 'd' door, 'w' window, 'g' garage, '-' blank), the upper floors get a window a bay; run limits the
    front to part of the side (None for all of it). Whatever else of its sides shows over its neighbours (blocks, as
    ( e0, e1, n0, n1, height )) is plain render. names: belltower_fronts.SIGNS' names for its shops, in turn. plaques:
    ( face, end, paint ) street plaques on its fronts' corners (street_plaque). """
    box = ( e0, e1, n0, n1, eave )
    model.collision_box( ( e0, n0, 0 ), ( e1, n1, eave ), STONE )
    if surround is None and chance( 0.75, "surround", e0, n0 ):
        surround = SURROUNDS.get( render )
    style = { "trim": trim, "shutter": shutter, "sill": "ashlar", "door": "planks_dark", "sign": sign,
              "awning": awning_paint, "surround": surround, "solid": True, "names": list( names ) }
    gutter = "copper_brown" if chance( 0.55, "gutter", e0, n0 ) else "metal"
    levels = floors_of( eave )
    shown = { face: exposure( box, face, blocks ) for face in ( "+n", "-n", "+e", "-e" ) }

    def returned( face, r0, r1, z, depth ):
        """ A band along an n side runs on round the corner by its depth where the e side beside it shows at z. """
        if face in ( "+e", "-e" ):
            return r0, r1
        corner_n = n1 if face == "+n" else n0
        return ( r0 - depth if abs( r0 - e0 ) < 1e-6 and shows_at( shown["-e"], corner_n, z ) else r0,
                 r1 + depth if abs( r1 - e1 ) < 1e-6 and shows_at( shown["+e"], corner_n, z ) else r1 )

    def plinth_along( wall ):
        r0, r1 = returned( wall.outward, *wall.run, 0, 2.5 )
        cuts = sorted( ( o.r0, o.r1 ) for o in wall.openings if o.z0 < 24 )
        r = r0
        for c0, c1 in cuts + [ ( r1, r1 ) ]:
            if c0 > r + 1:
                slab_at( model, wall, r, c0, 0.0, 2.5, 0, 24, plinth )
            r = max( r, c1 )

    def cornice_along( wall ):
        slab_at( model, wall, *returned( wall.outward, *wall.run, eave - 12, 7.0 ), 0.0, 7.0, eave - 12, eave, trim )

    fronts, front_walls = {}, {}
    for face, ( ground, run ) in faces.items():
        wall = face_wall( e0, e1, n0, n1, face, 0, eave, run=run, corners=True )
        fronts[face] = wall.run
        front_walls[face] = wall
        r0, r1 = wall.run
        bays = len( ground )
        bay = ( r1 - r0 ) / bays
        balcony_bays = []
        for k, letter in enumerate( ground ):
            rc = r0 + bay * ( k + 0.5 )
            if letter == "s":
                wall.add( rc, min( bay - 20, 132 ), 0, 104, "shop" )
            elif letter == "d":
                wall.add( rc, 48, 0, 94, "shut" )
            elif letter == "g":
                wall.add( rc, min( bay - 16, 110 ), 0, 100, "shop" )
            elif letter == "w":
                wall.add( rc, 44, 34, 104, "glass" )
            for z in levels:
                if letter == "-" and ( k % 2 ):
                    continue
                # Not over a shop: its awning or board is in the way.
                if rng.random() < balconies and bay >= 80 and not ( letter in "sg" and z == levels[0] ):
                    wall.add( rc, 44, z, z + 92, "glass" )
                    balcony_bays.append( ( rc, z ) )
                else:
                    wall.add( rc, 42, z + 34, z + 106, "glass" )
        end = render if face in ( "+n", "-n" ) else None
        wall.build( model, render, None, render, end, surface=None )
        dress( model, wall, style, rng )
        for rc, z in balcony_bays:
            balcony( model, wall, rc - 34, rc + 34, z, key=( wall.outward, wall.across[0], rc, z ) )
        plinth_along( wall )
        bands( model, wall, [ z - 6 for z in levels ], "ashlar" )
        cornice_along( wall )
    for face, end, paint in plaques:
        assert street_plaque( model, front_walls[face], end, paint ), ( "no room for", paint, "on", e0, n0, face )
    # Ivy up some of its fronts from the pavement, by a door where it can be. Few have room for it between their
    # shutters. The north row's backs look out over the hill, where nobody sees them.
    for face, wall in front_walls.items():
        if not ( face == "+n" and n1 >= NORTH_ROW[1] ) and chance( 0.75, "ivy", e0, n0, face ):
            climb_ivy( model, wall, pick( ( 1.0, 1.15, 1.3 ), "ivy_scale", e0, n0, face ), ( e0, n0, face ) )
    # The rest of the sides that show, plain. The n sides' walls fill the corners.
    for face, pieces in shown.items():
        for a, b, z0 in pieces:
            for c, d in subtract( ( a, b ), fronts.get( face ) ):
                wall = face_wall( e0, e1, n0, n1, face, z0, eave, run=( c, d ) )
                wall.build( model, render, None, render, render if face in ( "+n", "-n" ) else None, surface=None )
                if z0 <= 0:
                    plinth_along( wall )
                cornice_along( wall )
    # A downpipe from the gutter on each eaves side that shows down to the street, at one end, clear of the openings.
    for face in ( ( "+n", "-n" ) if ridge == "e" else ( "+e", "-e" ) ):
        lo, hi = ( e0, e1 ) if face in ( "+n", "-n" ) else ( n0, n1 )
        ends = ( lo + 5.0, hi - 5.0 ) if chance( 0.5, "pipe", e0, n0, face ) else ( hi - 5.0, lo + 5.0 )
        for r in ends:
            openings = front_walls[face].openings if face in front_walls else ()
            if shows_at( shown[face], r, 0 ) and not any( o.r0 - 12 < r < o.r1 + 12 for o in openings ):
                downpipe( model, face_wall( e0, e1, n0, n1, face, 0, eave, corners=True ), r, eave, gutter )
                break
    return gable_roof( model, e0, e1, n0, n1, eave, ridge, roof, render, ends_over=ends_over, gables=gables, gutter=gutter )


# ---------------------------------------------------------------------------------------------------------------------
# Buildings people go into

class Place:
    """ A local frame for props: origin ( e, n, z ), turned yaw degrees counter-clockwise seen from above, so its x runs
    along ( cos yaw, sin yaw ) in plan. """

    def __init__( self, origin, yaw=0.0 ):
        self.o = np.asarray( origin, float )
        a = math.radians( yaw )
        self.x = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
        self.y = np.array( ( -math.sin( a ), math.cos( a ), 0.0 ) )
        self.z = np.array( ( 0.0, 0.0, 1.0 ) )

    def at( self, p ):
        return self.o + self.x * p[0] + self.y * p[1] + self.z * p[2]

    def box( self, model, lo, hi, paints, surface=None ):
        """ A box from lo to hi in local coordinates. Faces are named along the frame: '+x', '-x', '+y', '-y', '+z',
        '-z'. """
        lo, hi = np.asarray( lo, float ), np.asarray( hi, float )
        model.oriented_box( self.at( ( lo + hi ) / 2 ), ( self.x, self.y, self.z ), hi - lo, paints, surface )

    def beam( self, model, p0, p1, size, paint, surface=None ):
        model.beam( self.at( p0 ), self.at( p1 ), size, paint, surface )


def shell( model, e0, e1, n0, n1, z0, z1, openings, paints, thick=12.0, surface=STONE, hidden=() ):
    """ The outer walls of a building people go into, from z0 to z1. openings { face: [ ( centre, width, z0, z1, kind ) ] };
    paints { 'outside', 'inside', 'reveal', 'sill' }; hidden lists faces against a neighbour, whose outside isn't drawn.
    Returns { face: Wall } for dressing. """
    walls = {}
    for face in ( "+n", "-n", "+e", "-e" ):
        wall = face_wall( e0, e1, n0, n1, face, z0, z1, thick )
        for opening in openings.get( face, () ):
            wall.add( *opening )
        outside = None if face in hidden else paints["outside"]
        end = paints["outside"] if face in ( "+n", "-n" ) else None
        wall.build( model, outside, paints["inside"], paints["reveal"], end, surface, paints.get( "sill" ) )
        walls[face] = wall
    return walls


def inner_wall( model, axis, run, across, z, openings, paint, reveal=None, surface=STONE ):
    wall = Wall( axis, run, across, z )
    for opening in openings:
        wall.add( *opening )
    wall.build( model, paint, paint, reveal or paint, paint, surface )
    return wall


def around_holes( e0, e1, n0, n1, holes ):
    """ The rectangle e0..e1 x n0..n1 less rectangular holes ( e0, e1, n0, n1 ), as rows of rectangles. """
    es = sorted( { e0, e1 } | { h[k] for h in holes for k in ( 0, 1 ) if e0 < h[k] < e1 } )
    ns = sorted( { n0, n1 } | { h[k] for h in holes for k in ( 2, 3 ) if n0 < h[k] < n1 } )
    pieces = []
    for na, nb in zip( ns, ns[1:] ):
        run = None
        for ea, eb in zip( es, es[1:] ):
            ce, cn = ( ea + eb ) / 2, ( na + nb ) / 2
            if any( h[0] <= ce <= h[1] and h[2] <= cn <= h[3] for h in holes ):
                if run:
                    pieces.append( ( run[0], run[1], na, nb ) )
                    run = None
            else:
                run = ( run[0], eb ) if run else ( ea, eb )
        if run:
            pieces.append( ( run[0], run[1], na, nb ) )
    return pieces


def floor_slab( model, e0, e1, n0, n1, z0, z1, holes, paints, surface=WOOD ):
    """ A floor from z0 to z1 over e0..e1 x n0..n1, with rectangular holes ( e0, e1, n0, n1 ) left out (stairwells), as
    rows of boxes. """
    for a0, a1, b0, b1 in around_holes( e0, e1, n0, n1, holes ):
        model.box( ( a0, b0, z0 ), ( a1, b1, z1 ), paints, surface )


def ceiling( model, e0, e1, n0, n1, z, paint, beams=None, beam_paint="planks_dark", holes=() ):
    """ A ceiling seen from below at z (paint None: only its beams), with beams across it every beams[1] along
    beams[0] ('e' or 'n'), both broken over holes ( e0, e1, n0, n1 ) (stairwells). """
    if paint:
        for a0, a1, b0, b1 in around_holes( e0, e1, n0, n1, holes ):
            facing( model, paint, [ ( a0, b0, z ), ( a1, b0, z ), ( a1, b1, z ), ( a0, b1, z ) ], ( 0, 0, -1 ) )
    if beams:
        axis, step = beams
        for c in np.arange( ( e0 if axis == "e" else n0 ) + step / 2, e1 if axis == "e" else n1, step ):
            # A beam at c, 10 wide, across the ceiling: its pieces between the holes it crosses.
            lo, hi = ( n0, n1 ) if axis == "e" else ( e0, e1 )
            cuts = sorted( ( h[2], h[3] ) if axis == "e" else ( h[0], h[1] ) for h in holes
                           if ( h[0] < c + 5 and h[1] > c - 5 if axis == "e" else h[2] < c + 5 and h[3] > c - 5 ) )
            r = lo
            for c0, c1 in cuts + [ ( hi, hi ) ]:
                if c0 > r + 1:
                    if axis == "e":
                        model.box( ( c - 5, r, z - 10 ), ( c + 5, c0, z ), beam_paint )
                    else:
                        model.box( ( r, c - 5, z - 10 ), ( c0, c + 5, z ), beam_paint )
                r = max( r, c1 )


def floor( model, e0, e1, n0, n1, paint, z=1.0 ):
    """ A floor's finish, drawn 1 over the ground under it (the ground's collision is what's walked on). """
    rect( model, paint, e0, e1, n0, n1, z )


def courses( model, wall, z0, z1, proud, paint ):
    """ A band along the wall's face from z0 to z1 standing out by proud, broken where openings cross it. """
    cuts = sorted( ( o.r0, o.r1 ) for o in wall.openings if o.z0 < z1 and o.z1 > z0 )
    r = wall.run[0]
    for c0, c1 in cuts + [ ( wall.run[1], wall.run[1] ) ]:
        if c0 > r + 1:
            slab_at( model, wall, r, c0, 0.0, proud, z0, z1, paint )
        r = max( r, c1 )


def quoins( model, wall, z0, z1, paint, width=24.0, proud=2.0 ):
    """ Stone strips up both ends of the wall's face. """
    slab_at( model, wall, wall.run[0], wall.run[0] + width, 0.0, proud, z0, z1, paint )
    slab_at( model, wall, wall.run[1] - width, wall.run[1], 0.0, proud, z0, z1, paint )


def light( name, position, color="1,0.86,0.66,1", radius=420.0, shadows=False ):
    """ A point light for the scene ( plan position ). """
    return ( name, position, color, radius, shadows )


# ---------------------------------------------------------------------------------------------------------------------
# The Town Hall (centre)

HALL_FLOOR = 168.0        # the council hall's floor
HALL_EAVE = 348.0


def town_hall( model, lights ):
    """ On the square's north side: a loggia of five arches, the passage under the belltower through to Market Street,
    a room with a stair each side, and the council hall over all of it with a balcony onto the square. """
    e0, e1, n0, n1 = -450.0, 450.0, 550.0, 1100.0
    T = 16.0
    GF, FL, CEIL = 160.0, HALL_FLOOR, 340.0
    paints = { "outside": "render_cream", "inside": "whitewash", "reveal": "ashlar", "sill": "ashlar" }
    south = [ ( e, 110, 0, 150, "arch" ) for e in ( -320, -160, 0, 160, 320 ) ]
    south += [ ( e, 56, FL, FL + 104, "door" ) for e in ( -160, 0, 160 ) ]
    south += [ ( e, 60, FL + 36, FL + 132, "window" ) for e in ( -330, 330 ) ]
    north = [ ( 0, 140, 0, 150, "arch" ), ( -260, 56, 0, 100, "door" ), ( 260, 56, 0, 100, "door" ) ]
    north += [ ( e, 44, 40, 112, "window" ) for e in ( -390, -150, 150, 390 ) ]
    north += [ ( e, 54, FL + 36, FL + 132, "window" ) for e in ( -385, -275, -165, -55, 55, 165, 275, 385 ) ]
    walls = shell( model, e0, e1, n0, n1, 0, HALL_EAVE, { "-n": south, "+n": north }, paints, T )
    style = { "trim": "trim_white", "shutter": None, "sill": "ashlar", "surround": None }
    rng = np.random.default_rng( 7 )
    for face, wall in walls.items():
        dress( model, wall, style, rng )
        courses( model, wall, 0, 30, 3.0, "ashlar" )
        courses( model, wall, GF, FL, 4.0, "ashlar" )
        slab_at( model, wall, wall.run[0], wall.run[1], 0.0, 9.0, HALL_EAVE - 16, HALL_EAVE, "ashlar" )
        if face in ( "+n", "-n" ):
            quoins( model, wall, 30, HALL_EAVE - 16, "ashlar" )
            for o in wall.openings:
                if o.kind == "window" and o.z0 > 100:
                    # Pediments over the hall's windows.
                    slab_at( model, wall, o.r0 - 8, o.r1 + 8, 0.0, 5.0, o.z1 + 6, o.z1 + 16, "ashlar" )
                    slab_at( model, wall, o.r0 - 5, o.r1 + 5, 0.0, 3.0, o.z0 - 8, o.z0, "ashlar" )

    # The balcony over the middle arches, on corbels over the piers.
    model.box( ( -240, 506, GF ), ( 240, n0, FL ), { "+z": "flagstones", "default": "ashlar" }, STONE )
    model.box( ( -240, 506, FL ), ( 240, 514, FL + 36 ), "ashlar", STONE )
    model.box( ( -240, 514, FL ), ( -232, n0, FL + 36 ), "ashlar", STONE )
    model.box( ( 232, 514, FL ), ( 240, n0, FL + 36 ), "ashlar", STONE )
    model.box( ( -242, 504, FL + 36 ), ( 242, 516, FL + 40 ), "ashlar" )
    for e in ( -240, -80, 80, 240 ):
        model.box( ( e - 8, 516, GF - 34 ), ( e + 8, n0, GF ), "ashlar" )

    # Inside, the ground floor: the loggia, the passage and the two rooms.
    floor( model, e0, e1, n0, 700, "flagstones" )
    floor( model, -70, 70, 700, n1, "setts" )
    floor( model, e0, -70, 700, n1, "quarry_tiles" )
    floor( model, 70, e1, 700, n1, "quarry_tiles" )
    inner_wall( model, "e", ( e0 + T, e1 - T ), ( 700, 712 ), ( 0, GF ),
                [ ( 0, 140, 0, 150, "arch" ), ( -260, 56, 0, 100, "door" ), ( 260, 56, 0, 100, "door" ) ], "whitewash", "ashlar" )
    for side in ( -1, 1 ):
        across = ( -82, -70 ) if side < 0 else ( 70, 82 )
        inner_wall( model, "n", ( 712, n1 - T ), across, ( 0, GF ), [ ( 1000, 56, 0, 100, "door" ) ], "whitewash", "ashlar" )
    # The tower stands on four piers: in the passage's walls downstairs, and free in the council hall.
    for se in ( -1, 1 ):
        for pn in ( ( 715, 755 ), ( 895, 935 ) ):
            ea, eb = sorted( ( se * 66, se * 110 ) )
            model.box( ( ea, pn[0], 0 ), ( eb, pn[1], GF ), { "default": "ashlar", "+z": None, "-z": None }, STONE )
            ea, eb = sorted( ( se * 70, se * 110 ) )
            model.box( ( ea, pn[0], FL ), ( eb, pn[1], CEIL ), { "default": "ashlar", "+z": None, "-z": None }, STONE )
    holes = []
    for side in ( -1, 1 ):
        ea, eb = sorted( ( side * ( e1 - T ), side * ( e1 - T - 60 ) ) )
        holes.append( ( ea, eb, 760, 991 ) )
        stair( model, ( ea, 760 ), ( eb, 991 ), 0, FL, "+n", "planks", "planks_dark" )
        # A rail round the stairwell upstairs.
        ra, rb = sorted( ( side * ( e1 - T - 60 ), side * ( e1 - T - 66 ) ) )
        model.box( ( ra, 754, FL ), ( rb, 991, FL + 36 ), "planks_dark", WOOD )
        model.box( ( min( ea, ra ), 754, FL ), ( max( eb, rb ), 760, FL + 36 ), "planks_dark", WOOD )
    floor_slab( model, e0 + T, e1 - T, n0 + T, n1 - T, GF, FL, holes, { "+z": "floorboards", "-z": "planks_dark", "default": "planks_dark" } )
    ceiling( model, e0 + T, e1 - T, 712, n1 - T, GF, None, ( "e", 110 ), holes=holes )
    ceiling( model, e0 + T, e1 - T, n0 + T, 700, GF, None, ( "e", 110 ) )
    # The rooms' furniture: a clerk's desk and cabinets.
    for side in ( -1, 1 ):
        ea, eb = sorted( ( side * 330, side * 250 ) )
        model.box( ( ea, 820, 0 ), ( eb, 860, 30 ), { "+z": "planks", "default": "planks_dark" }, WOOD )
        ea, eb = sorted( ( side * 300, side * 350 ) )
        model.box( ( ea, 1060, 0 ), ( eb, n1 - T, 78 ), "planks_dark", WOOD )
        # A bench against each end of the loggia.
        ea, eb = sorted( ( side * ( e1 - T ), side * ( e1 - T - 22 ) ) )
        model.box( ( ea, 590, 0 ), ( eb, 690, 18 ), "planks_dark", WOOD )

    # The council hall: its table round the Hot Zone, bookcases, and a timber ceiling.
    model.box( ( -60, 790, FL ), ( 60, 860, FL + 30 ), { "+z": "planks", "default": "planks_dark" }, WOOD )
    for side in ( -1, 1 ):
        ea, eb = sorted( ( side * ( e1 - T ), side * ( e1 - T - 22 ) ) )
        model.box( ( ea, 600, FL ), ( eb, 700, FL + 96 ), "planks_dark", WOOD )
        ea, eb = sorted( ( side * 200, side * 330 ) )
        model.box( ( ea, 640, FL ), ( eb, 660, FL + 18 ), "planks_dark", WOOD )
        model.box( ( ea, 960, FL ), ( eb, 980, FL + 18 ), "planks_dark", WOOD )
    model.box( ( e0 + T, n0 + T, CEIL ), ( e1 - T, n1 - T, HALL_EAVE ), { "-z": "planks_dark", "default": None }, STONE )
    for e in np.arange( -380, 381, 95 ):
        model.box( ( e - 6, n0 + T, CEIL - 12 ), ( e + 6, n1 - T, CEIL ), "planks_dark" )
    ridge = gable_roof( model, e0, e1, n0, n1, HALL_EAVE, "e", "roof_tiles", paints["outside"], over=18, ends_over=( 12, 12 ) )

    # The belltower, from the roof: shaft, clock, belfry and a copper spire.
    model.box( ( -110, 715, CEIL ), ( 110, 935, 780 ), { "+z": "flagstones", "-z": None, "default": "ashlar" }, STONE )
    for face, centre, axis in ( ( "-n", ( 0, 715 ), ( 1, 0 ) ), ( "+n", ( 0, 935 ), ( -1, 0 ) ),
                                ( "-e", ( -110, 825 ), ( 0, -1 ) ), ( "+e", ( 110, 825 ), ( 0, 1 ) ) ):
        out = np.array( ( axis[1], -axis[0], 0.0 ) )
        along = np.array( ( axis[0], axis[1], 0.0 ) )
        c = np.array( ( *centre, 690.0 ) )
        for half, depth, paint in ( ( 52, 1.0, "ashlar_grey" ), ( 40, 2.0, "clock" ) ):
            pts = [ c + out * depth + along * sa * half + np.array( ( 0, 0, sz * half ) ) for sa, sz in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ) ]
            facing( model, paint, pts, out )
            if paint == "ashlar_grey":
                # The surround's edges.
                for k in range( 4 ):
                    a, b = pts[k], pts[( k + 1 ) % 4]
                    facing( model, paint, [ a, b, b - out * depth, a - out * depth ], ( a + b ) / 2 - c )
    model.box( ( -116, 709, 770 ), ( 116, 941, 782 ), "ashlar" )
    belfry = { "outside": "ashlar", "inside": "ashlar", "reveal": "ashlar", "sill": "ashlar" }
    for face, wall in ( ( "-n", Wall( "e", ( -110, 110 ), ( 715, 735 ), ( 782, 900 ), "-n" ) ),
                        ( "+n", Wall( "e", ( -110, 110 ), ( 915, 935 ), ( 782, 900 ), "+n" ) ),
                        ( "-e", Wall( "n", ( 735, 915 ), ( -110, -90 ), ( 782, 900 ), "-e" ) ),
                        ( "+e", Wall( "n", ( 735, 915 ), ( 90, 110 ), ( 782, 900 ), "+e" ) ) ):
        wall.add( 0 if face in ( "-n", "+n" ) else 825, 120, 800, 882, "arch" )
        wall.build( model, belfry["outside"], belfry["inside"], belfry["reveal"], belfry["outside"], STONE )
    model.box( ( -118, 707, 900 ), ( 118, 943, 912 ), "ashlar", STONE )
    pyramid( model, -124, 124, 701, 949, 912, 1100, "copper", STONE )
    model.beam( ( 0, 825, 1100 ), ( 0, 825, 1170 ), ( 4, 4 ), "iron_black" )
    blob( model, ( 0, 825, 1128 ), 9, "copper", squash=1.0, segments=8, rings=4, seed=3 )
    model.beam( ( -16, 825, 1150 ), ( 16, 825, 1150 ), ( 3, 3 ), "iron_black" )
    # The bell on its yoke.
    model.box( ( -90, 819, 872 ), ( 90, 831, 884 ), "planks_dark" )
    model.cylinder( ( 0, 825 ), 30, 812, 846, { "side": "copper", "bottom": "iron_black", "top": "copper" }, sides=14 )
    cone( model, ( 0, 825 ), 30, 846, 872, "copper", sides=14 )

    lights.append( light( "Town Hall Loggia", ( 0, 630, 130 ) ) )
    lights.append( light( "Town Hall West Room", ( -260, 900, 130 ) ) )
    lights.append( light( "Town Hall East Room", ( 260, 900, 130 ) ) )
    lights.append( light( "Council Hall West", ( -250, 825, 300 ), radius=520 ) )
    lights.append( light( "Council Hall East", ( 250, 825, 300 ), radius=520 ) )
    return ridge


# ---------------------------------------------------------------------------------------------------------------------
# The church (centre)

def church( model, lights ):
    """ South of the square: a nave with its front door on the square, a side door onto each churchyard and two doors
    behind the altar onto the terrace. Pews, the chancel step, the altar and the pulpit are cover. """
    e0, e1, n0, n1 = -170.0, 170.0, -900.0, -400.0
    T, EAVE = 20.0, 300.0
    paints = { "outside": "ashlar", "inside": "whitewash", "reveal": "ashlar", "sill": "ashlar" }
    openings = {
        "+n": [ ( 0, 96, 0, 160, "arch" ), ( 0, 70, 190, 290, "glass_arch" ), ( -110, 30, 110, 230, "glass_arch" ),
                ( 110, 30, 110, 230, "glass_arch" ) ],
        "-n": [ ( -110, 60, 0, 120, "arch" ), ( 110, 60, 0, 120, "arch" ), ( 0, 80, 150, 290, "glass_arch" ) ],
        "-e": [ ( -650, 60, 0, 120, "arch" ) ] + [ ( n, 36, 110, 240, "glass_arch" ) for n in ( -480, -560, -740, -820 ) ],
        "+e": [ ( -650, 60, 0, 120, "arch" ) ] + [ ( n, 36, 110, 240, "glass_arch" ) for n in ( -480, -560, -740, -820 ) ],
    }
    walls = shell( model, e0, e1, n0, n1, 0, EAVE, openings, paints, T )
    style = { "trim": "iron_black", "shutter": None, "sill": "ashlar", "glass_surface": GLASS }
    rng = np.random.default_rng( 11 )
    for face, wall in walls.items():
        dress( model, wall, style, rng )
        courses( model, wall, 0, 24, 4.0, "ashlar_grey" )
        slab_at( model, wall, wall.run[0], wall.run[1], 0.0, 8.0, EAVE - 12, EAVE, "ashlar_grey" )
        if face in ( "-e", "+e" ):
            # Buttresses between the windows.
            for n in ( -440, -520, -600, -700, -780, -860 ):
                slab_at( model, wall, n - 12, n + 12, 0.0, 30.0, 0, 200, "ashlar", STONE )
                slab_at( model, wall, n - 12, n + 12, 0.0, 16.0, 200, 240, "ashlar", STONE )
                wall.fixtures = list( getattr( wall, "fixtures", () ) ) + [ ( n - 12, n + 12, 0, 240 ) ]
            # Ivy at the foot of some of the bays between them, under the windows, in front of the plinth's courses.
            for o in wall.openings:
                if o.kind == "glass_arch" and chance( 0.5, "church_ivy", face, o.r0 ):
                    ivy( model, wall, ( o.r0 + o.r1 ) / 2, 0, 0.92, "ivy_climb", 4.6, ( "church", face, o.r0 ) )
    # Hoods over the doors.
    for face, wall in walls.items():
        for o in wall.openings:
            if o.kind == "arch":
                slab_at( model, wall, o.r0 - 10, o.r1 + 10, 0.0, 6.0, o.z1 + 4, o.z1 + 14, "ashlar_grey" )
    ridge = gable_roof( model, e0, e1, n0, n1, EAVE, "n", "slate", "ashlar", over=16, ends_over=( 10, 10 ) )
    # A bell-cote with a cross on the front gable.
    model.box( ( -26, -416, ridge - 14 ), ( 26, -400, ridge + 44 ), "ashlar" )
    model.box( ( -30, -420, ridge + 44 ), ( 30, -396, ridge + 52 ), "ashlar_grey" )
    model.beam( ( 0, -408, ridge + 52 ), ( 0, -408, ridge + 104 ), ( 6, 6 ), "iron_black" )
    model.beam( ( -16, -408, ridge + 88 ), ( 16, -408, ridge + 88 ), ( 6, 6 ), "iron_black" )

    floor( model, e0, e1, n0, n1, "flagstones" )
    ceiling( model, e0 + T, e1 - T, n0 + T, n1 - T, EAVE, "planks_dark", ( "n", 80 ) )
    # The chancel: a step, the altar and the pulpit.
    model.box( ( e0 + T, n0 + T, 0 ), ( e1 - T, -800, 8 ), { "+z": "ashlar", "default": "ashlar_grey" }, STONE )
    model.box( ( -54, -862, 8 ), ( 54, -828, 46 ), { "+z": "canvas_plain", "default": "ashlar" }, STONE )
    model.cylinder( ( 124, -772 ), 20, 0, 58, { "side": "planks_dark", "top": "planks" }, sides=8, surface=WOOD )
    # Pews, facing the altar, with an aisle down the middle and across at the side doors.
    for n in ( -440, -484, -528, -572, -700, -744 ):
        for ea, eb in ( ( e0 + T + 10, -40 ), ( 40, e1 - T - 10 ) ):
            model.box( ( ea, n - 18, 0 ), ( eb, n, 18 ), { "+z": "planks", "default": "planks_dark" }, WOOD )
            model.box( ( ea, n - 3, 18 ), ( eb, n, 38 ), "planks_dark", WOOD )
    lights.append( light( "Church Nave", ( 0, -560, 220 ), "0.95,0.88,0.75,1", 520 ) )
    lights.append( light( "Church Chancel", ( 0, -800, 200 ), "1,0.83,0.6,1", 380 ) )
    return ridge


# ---------------------------------------------------------------------------------------------------------------------
# Round things in the middle, built whole: the fountain, the market cross and the garden well

FOUNTAIN = ( 0.0, 130.0 )
MARKET_CROSS = ( 0.0, 1275.0 )
GARDEN_WELL = ( 0.0, -1225.0 )


def fountain( model ):
    stone = { "outside": "ashlar", "inside": "ashlar", "top": "ashlar_grey" }
    ring( model, FOUNTAIN, 96, 114, 0, 30, 12, stone, STONE )
    model.cylinder( FOUNTAIN, 96, 21, 22, { "top": "water" }, sides=12, turn=math.pi / 12 )
    model.cylinder( FOUNTAIN, 26, 0, 72, { "side": "ashlar", "top": "ashlar" }, sides=10, surface=STONE )
    model.cylinder( FOUNTAIN, 54, 72, 84, { "side": "ashlar_grey", "bottom": "ashlar", "top": "ashlar" }, sides=12, surface=STONE )
    model.cylinder( FOUNTAIN, 46, 84, 84.5, { "top": "water" }, sides=12 )
    model.cylinder( FOUNTAIN, 9, 84, 126, { "side": "ashlar" }, sides=8 )
    blob( model, ( *FOUNTAIN, 134 ), 12, "ashlar_grey", squash=1.0, segments=8, rings=4, seed=5 )


def market_cross( model ):
    for r, z0, z1 in ( ( 100, 0, 12 ), ( 80, 12, 24 ), ( 60, 24, 36 ) ):
        model.cylinder( MARKET_CROSS, r, z0, z1, { "side": "ashlar_grey", "top": "ashlar" }, sides=8, surface=STONE, turn=math.pi / 8 )
    model.cylinder( MARKET_CROSS, 13, 36, 200, { "side": "ashlar" }, sides=8, surface=STONE, turn=math.pi / 8 )
    e, n = MARKET_CROSS
    model.box( ( e - 18, n - 18, 200 ), ( e + 18, n + 18, 212 ), "ashlar_grey" )
    model.beam( ( e, n, 212 ), ( e, n, 266 ), ( 8, 8 ), "ashlar" )
    model.beam( ( e - 20, n, 244 ), ( e + 20, n, 244 ), ( 8, 8 ), "ashlar" )


def garden_well( model ):
    e, n = GARDEN_WELL
    z = GARDEN_Z
    ring( model, GARDEN_WELL, 30, 42, z, z + 34, 10, { "outside": "rubble", "inside": "rubble", "top": "ashlar_grey" }, STONE )
    model.cylinder( GARDEN_WELL, 30, z + 8, z + 9, { "top": "water" }, sides=10, turn=math.pi / 10 )
    for se in ( -1, 1 ):
        model.box( ( e + se * 38 - 4, n - 4, z + 34 ), ( e + se * 38 + 4, n + 4, z + 116 ), "planks_dark", WOOD )
    model.beam( ( e - 44, n, z + 106 ), ( e + 44, n, z + 106 ), ( 6, 6 ), "planks_dark" )
    axle( model, ( e, n, z + 96 ), ( 1, 0, 0 ), 6, 50, { "side": "planks", "end": "planks_dark" } )
    gable_roof( model, e - 50, e + 50, n - 26, n + 26, z + 112, "e", "roof_tiles", "planks_dark", over=6, ends_over=( 4, 4 ),
                thick=3, hull=None, cap=False )


def build_centre( lights ):
    model = Model()
    town_hall( model, lights )
    church( model, lights )
    fountain( model )
    market_cross( model )
    garden_well( model )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Props

def crate( model, centre, size=40.0, yaw=0.0, z=0.0, paint="planks" ):
    p = Place( ( centre[0], centre[1], z ), yaw )
    h = size / 2
    p.box( model, ( -h, -h, 0 ), ( h, h, size ), None, WOOD )
    Detail.crate( model, p, size, paint )
    return z + size


def crates( model, centre, yaw, rng, z=0.0 ):
    """ A small stack: two or three crates and maybe one on top. """
    p = Place( ( centre[0], centre[1], z ), yaw )
    tops = []
    for k in range( int( rng.integers( 2, 4 ) ) ):
        size = float( rng.choice( ( 36.0, 40.0, 44.0 ) ) )
        at = p.at( ( k * 46.0, rng.uniform( -4, 4 ), 0 ) )
        tops.append( ( at, crate( model, at, size, yaw + rng.uniform( -8, 8 ), z ) ) )
    if rng.random() < 0.6:
        at, top = tops[0]
        crate( model, at, 32.0, yaw + rng.uniform( -20, 20 ), top )


def barrel( model, centre, z=0.0, r=13.0, h=36.0 ):
    model.cylinder( centre, r, z, z + h, {}, sides=10, surface=WOOD )
    Detail.barrel( model, centre, z, r, h )


def barrels( model, centre, count, rng, z=0.0 ):
    for k in range( count ):
        a = rng.uniform( 0, 2 * math.pi )
        d = 0 if k == 0 else 27.0
        barrel( model, ( centre[0] + d * math.cos( a + k * 2.1 ), centre[1] + d * math.sin( a + k * 2.1 ) ), z )


def sacks( model, centre, yaw, count, z=0.0 ):
    p = Place( ( centre[0], centre[1], z ), yaw )
    for k in range( count ):
        row, level = k % 3, k // 3
        p.box( model, ( row * 22 - 22 + level * 6, -14, level * 14 ), ( row * 22 - 2 + level * 6, 14, level * 14 + 14 ),
               "canvas_plain", FABRIC if level == 0 else None )


def cart( model, centre, yaw, z=0.0, load="sacks" ):
    """ A two-wheeled hand cart, 120 long, its shafts on the ground ahead. """
    p = Place( ( centre[0], centre[1], z ), yaw )
    p.box( model, ( -60, -32, 26 ), ( 60, 32, 32 ), "planks" )
    for s in ( -1, 1 ):
        p.box( model, ( -60, s * 32 - 3, 32 ), ( 60, s * 32, 48 ), "planks_dark" )
    p.box( model, ( -60, -32, 32 ), ( -57, 32, 48 ), "planks_dark" )
    p.box( model, ( 57, -32, 32 ), ( 60, 32, 48 ), "planks_dark" )
    for s in ( -1, 1 ):
        Detail.wheel( model, p, s, axle )
        p.beam( model, ( 50, s * 22, 28 ), ( 140, s * 22, 4 ), ( 4, 4 ), "planks_dark" )
    p.box( model, ( -60, -41, 0 ), ( 60, 41, 48 ), None, WOOD )
    if load == "sacks":
        for k, ( x, y ) in enumerate( ( ( -30, -12 ), ( 0, -12 ), ( 30, -12 ), ( -15, 12 ), ( 15, 12 ) ) ):
            p.box( model, ( x - 14, y - 11, 32 ), ( x + 14, y + 11, 46 ), "canvas_plain" )
    elif load == "crates":
        crate( model, p.at( ( -25, 0, 0 ) ), 36, yaw + 5, z + 32 )
        crate( model, p.at( ( 22, 2, 0 ) ), 32, yaw - 7, z + 32 )


def crate_counter( model, p, w, d, top ):
    """ A stall's counter as market traders build one: two tiers of slatted crates on a pallet, under a board top, from
    -w to w along local x, -d to d along y and up to top. Drawn only: the stall's own box is the cover. """
    pallet = 6.0
    p.box( model, ( -w + 1, -d + 1, pallet ), ( w - 1, d - 1, top - 1 ), "planks_dark" )
    p.box( model, ( -w, -d, pallet - 1.5 ), ( w, d, pallet ), "planks" )
    for x in ( -w + 4, 0.0, w - 4 ):
        p.box( model, ( x - 4, -d, 0 ), ( x + 4, d, pallet - 1.5 ), "planks_dark" )
    p.box( model, ( -w - 1, -d - 1, top - 1 ), ( w + 1, d + 1, top ), "planks" )
    tier = ( top - 1 - pallet ) / 2

    def crates_along( axis, side, half, count ):
        """ count crates' ends across a face: axis 0 faces local x, 1 faces y; side -1 or 1; half the face's half-length. """
        span = 2 * half / count
        for row in range( 2 ):
            z0 = pallet + row * tier
            for k in range( count ):
                a0, a1 = -half + k * span + 0.6, -half + ( k + 1 ) * span - 0.6
                for b in range( 3 ):
                    za, zb = z0 + 0.5 + b * ( tier - 1 ) / 3 + 0.35, z0 + 0.5 + ( b + 1 ) * ( tier - 1 ) / 3 - 0.35
                    out = ( w if axis == 0 else d ) * side
                    lo, hi = [ 0.0, 0.0, za ], [ 0.0, 0.0, zb ]
                    lo[axis], hi[axis] = out - side * 1.0, out
                    lo[1 - axis], hi[1 - axis] = a0 + 1.6, a1 - 1.6
                    p.box( model, np.minimum( lo, hi ), np.maximum( lo, hi ), "planks" )
                for a in ( a0, a1 - 1.6 ):
                    lo, hi = [ 0.0, 0.0, z0 + 0.4 ], [ 0.0, 0.0, z0 + tier - 0.4 ]
                    lo[axis], hi[axis] = out - side * 1.0, out + side * 0.4
                    lo[1 - axis], hi[1 - axis] = a, a + 1.6
                    p.box( model, np.minimum( lo, hi ), np.maximum( lo, hi ), "planks_dark" )

    for side in ( -1, 1 ):
        crates_along( 1, side, w, 4 )
        crates_along( 0, side, d, 2 )


def stall( model, centre, yaw, canvas, rng, width=120.0, depth=64.0 ):
    """ A market stall, its front along local +y: a counter of crates with four crates of produce on it, four posts
    and a canvas roof. """
    p = Place( ( centre[0], centre[1], 0 ), yaw )
    w, d = width / 2, depth / 2
    p.box( model, ( -w, -d, 0 ), ( w, d, 32 ), None, WOOD )
    crate_counter( model, p, w, d, 32.0 )
    # The draws the stall's goods always took, so everything placed after it stays where it was.
    goods = np.random.default_rng( [ int( rng.integers( 0, 5 ) ) * 1000 + int( rng.integers( 0, 1000 ) ) for _ in range( 4 ) ] )
    kinds = list( goods.permutation( list( Detail.PRODUCE ) ) )
    for k in range( 4 ):
        x = -w + 16 + k * ( width - 32 ) / 3
        Detail.produce_crate( model, p.at( ( x, d - 14, 0 ) )[:2], yaw + goods.uniform( -4, 4 ), kinds[k], goods, z=32.0 )
    for sx in ( -1, 1 ):
        for sy, top in ( ( -1, 106 ), ( 1, 92 ) ):
            p.box( model, ( sx * w - 2, sy * d - 2, 32 ), ( sx * w + 2, sy * d + 2, top ), "planks_dark" )
    roof = [ p.at( ( -w - 8, -d - 8, 108 ) ), p.at( ( w + 8, -d - 8, 108 ) ), p.at( ( w + 8, d + 14, 90 ) ),
             p.at( ( -w - 8, d + 14, 90 ) ) ]
    facing( model, canvas, roof, ( 0, 0, 1 ) )
    facing( model, canvas, roof, ( 0, 0, -1 ) )
    front = [ p.at( ( -w - 8, d + 14, 90 ) ), p.at( ( w + 8, d + 14, 90 ) ), p.at( ( w + 8, d + 14, 80 ) ), p.at( ( -w - 8, d + 14, 80 ) ) ]
    facing( model, canvas, front, p.y )
    facing( model, canvas, front, -p.y )


def lorry( model, centre, yaw, cab="trim_red" ):
    """ A small flatbed lorry with a canvas tilt, its cab along local +x. Collision: the cab and the body. """
    p = Place( ( centre[0], centre[1], 0 ), yaw )
    p.box( model, ( -150, -44, 20 ), ( 150, 44, 30 ), "iron_black" )
    p.box( model, ( -150, -48, 30 ), ( 50, 48, 50 ), "planks_dark", METAL )
    p.box( model, ( -150, -48, 50 ), ( 50, 48, 128 ), { "default": "canvas_green", "-z": None }, FABRIC )
    for x in ( -120, -60, 0, 40 ):
        p.box( model, ( x - 2, -49, 50 ), ( x + 2, 49, 129 ), "iron_black" )
    p.box( model, ( 58, -44, 30 ), ( 150, 44, 80 ), cab, SHEET )
    p.box( model, ( 58, -42, 80 ), ( 118, 42, 112 ), { "default": cab, "+x": "glass" }, SHEET )
    p.box( model, ( 119, -40, 82 ), ( 119.5, 40, 108 ), "glass" )
    for s in ( -1, 1 ):
        p.box( model, ( 70, s * 44 - s * 0.5 - 0.5, 84 ), ( 110, s * 44 + s * 0.5 - 0.5, 106 ), "glass" )
    p.box( model, ( 150, -46, 26 ), ( 156, 46, 42 ), "iron_black" )
    for x in ( -100, 110 ):
        for s in ( -1, 1 ):
            axle( model, p.at( ( x, s * 40, 20 ) ), p.y, 20, 12, { "side": "iron_black", "end": "roller_grey" }, sides=12 )
    p.box( model, ( -150, -48, 0 ), ( 50, 48, 20 ), None, METAL )
    p.box( model, ( 58, -46, 0 ), ( 150, 46, 30 ), None, METAL )


def tree( model, centre, z, height, spread, seed, leaves="hedge", trunk_r=9.0, solid=True, coarse=False ):
    """ A trunk (collision, unless solid is False) and a crown of a few lumpy balls (none). coarse draws it with fewer
    faces, for the trees out in the vista. """
    model.cylinder( centre, trunk_r, z, z + height * 0.62, {}, sides=5 if coarse else 7,
                    surface=WOOD if solid else None )
    Detail.tree( model, centre, z, height, spread, seed, coarse )


def lamp_post( model, centre, z=0.0 ):
    """ A cast-iron street lamp (belltower_detail's street_lamp) over a plain base and shaft to collide with. """
    model.cylinder( centre, 6, z, z + 18, {}, sides=8, surface=METAL )
    model.cylinder( centre, 3, z + 18, z + 128, {}, sides=6, surface=METAL )
    Detail.street_lamp( model, centre, z )


def bench( model, centre, yaw, length=84.0, z=0.0 ):
    p = Place( ( centre[0], centre[1], z ), yaw )
    l = length / 2
    p.box( model, ( -l, -9, 14 ), ( l, 9, 18 ), "planks" )
    p.box( model, ( -l, 7, 18 ), ( l, 9, 34 ), "planks" )
    for x in ( -l + 6, l - 6 ):
        p.box( model, ( x - 2, -8, 0 ), ( x + 2, 8, 14 ), "iron_black" )
    p.box( model, ( -l, -9, 0 ), ( l, 9, 18 ), None, WOOD )


def planter( model, centre, z=0.0, size=40.0, seed=0 ):
    e, n = centre
    h = size / 2
    model.box( ( e - h, n - h, z ), ( e + h, n + h, z + 28 ), { "default": "ashlar", "+z": "soil" }, STONE )
    blob( model, ( e, n, z + 44 ), h * 0.9, "hedge", squash=0.8, segments=8, rings=4, seed=seed )


def low_wall( model, e0, e1, n0, n1, z0, z1, paint="rubble", cap="ashlar_grey" ):
    """ A garden or yard wall with a coping. """
    model.box( ( e0, n0, z0 ), ( e1, n1, z1 - 4 ), paint, STONE )
    model.box( ( e0 - 1.5, n0 - 1.5, z1 - 4 ), ( e1 + 1.5, n1 + 1.5, z1 ), cap, STONE )


def pier( model, centre, z0, height, size=18.0 ):
    """ A gate pier with a ball on top. """
    e, n = centre
    h = size / 2
    model.box( ( e - h, n - h, z0 ), ( e + h, n + h, z0 + height ), "ashlar", STONE )
    model.box( ( e - h - 2, n - h - 2, z0 + height ), ( e + h + 2, n + h + 2, z0 + height + 4 ), "ashlar_grey", STONE )
    blob( model, ( e, n, z0 + height + 11 ), 7, "ashlar_grey", squash=1.0, segments=8, rings=4, seed=abs( int( e * 7 + n ) ) )


def wall_run( model, axis, run, across, z0, z1, gaps, piers=True, paint="rubble", cap="ashlar_grey", pier_height=None ):
    """ A wall along axis ('e' or 'n') over run, broken by gaps ( r0, r1 ), with piers either side of each. The wall
    runs on into its piers' middles, so its ends are hidden. """
    inset = 9.0 if piers else 0.0
    r = run[0]
    pieces = []
    for g0, g1 in sorted( gaps ) + [ ( run[1], run[1] ) ]:
        if g0 > r:
            pieces.append( ( r, g0 - ( inset if g0 < run[1] else 0.0 ) ) )
        r = max( r, g1 + inset )
    for r0, r1 in pieces:
        if axis == "e":
            low_wall( model, r0, r1, across[0], across[1], z0, z1, paint, cap )
        else:
            low_wall( model, across[0], across[1], r0, r1, z0, z1, paint, cap )
    if piers:
        mid = ( across[0] + across[1] ) / 2
        for g0, g1 in gaps:
            for r in ( g0 - 9, g1 + 9 ):
                pier( model, ( r, mid ) if axis == "e" else ( mid, r ), z0, pier_height or ( z1 - z0 ) + 20 )


def hedge( model, e0, e1, n0, n1, z0, height ):
    model.collision_box( ( e0, n0, z0 ), ( e1, n1, z0 + height ), GRASS )
    along_e = e1 - e0 > n1 - n0
    length = max( e1-e0, n1-n0 )
    count = max( 1, math.ceil( length / max( height*.65, 16 ) ) )
    for i in range( count ):
        at = ((e0 + (i+.5)*length/count) if along_e else (e0+e1)/2,
              (n0+n1)/2 if along_e else n0 + (i+.5)*length/count, z0 + height*.52)
        Detail.shrub( model, at, max( 12, height*.48 ), 1, abs(int(e0+n0+i*31)) )


def area( model, e0, e1, n0, n1, z, base, overlays=() ):
    """ The ground over a rectangle in base paint, with overlays ( e0, e1, n0, n1, paint ) laid over it (the last wins),
    as rows of polygons that don't overlap. """
    es = sorted( { e0, e1 } | { v for o in overlays for v in o[:2] if e0 < v < e1 } )
    ns = sorted( { n0, n1 } | { v for o in overlays for v in o[2:4] if n0 < v < n1 } )
    for na, nb in zip( ns, ns[1:] ):
        run, run_paint = None, None
        for ea, eb in zip( es, es[1:] ):
            ce, cn = ( ea + eb ) / 2, ( na + nb ) / 2
            paint = base
            for o in overlays:
                if o[0] <= ce <= o[1] and o[2] <= cn <= o[3]:
                    paint = o[4]
            if run and paint == run_paint:
                run = ( run[0], eb )
            else:
                if run and run_paint:
                    rect( model, run_paint, run[0], run[1], na, nb, z )
                run, run_paint = ( ea, eb ), paint
        if run and run_paint:
            rect( model, run_paint, run[0], run[1], na, nb, z )


# ---------------------------------------------------------------------------------------------------------------------
# The west half's houses nobody goes into

# ( e0, e1, n0, n1, eave, render, faces { face: ( ground floor bays, run ) }, ridge, extras ). Whatever else of a
# house's sides shows over its neighbours is drawn plain (exposure).
HOUSES = [
    # Market Street's north side, facing south onto it, their backs to the drop.
    ( -1850, -1560, 1450, 1800, 300, "render_ochre", { "-n": ( "sws", None ), "-e": ( "wdw", None ), "+n": ( "ww", None ) },
      "e", { "plaques": ( ( "-n", 0, "plaque_6" ), ) } ),
    ( -1560, -1330, 1450, 1800, 262, "render_rose", { "-n": ( "sd", None ), "+n": ( "ww", None ) }, "n",
      { "awning": "canvas_red" } ),
    ( -1330, -1060, 1450, 1800, 336, "render_cream", { "-n": ( "sws", None ), "+n": ( "w-w", None ) }, "e", {} ),
    ( -1060, -820, 1450, 1800, 290, "render_terracotta", { "-n": ( "ds", None ), "+n": ( "ww", None ) }, "e",
      { "awning": "canvas_green" } ),
    ( -820, -560, 1450, 1800, 318, "render_white", { "-n": ( "sws", None ), "+n": ( "w-w", None ) }, "e",
      { "shutter": "shutter_brown" } ),
    ( -560, -300, 1450, 1800, 276, "render_rose", { "-n": ( "wds", None ), "+n": ( "ww", None ) }, "n",
      { "awning": "canvas_red" } ),
    # The stone bank facing the market cross, whole with its mirror.
    ( -300, 0, 1450, 1800, 344, "ashlar", { "-n": ( "wdw", None ), "+n": ( "ww", None ) }, "e",
      { "trim": "trim_white", "shutter": "shutter_green", "ends_over": ( 14, 0 ), "gables": ( True, False ),
        "balconies": 0.0, "surround": "ashlar_grey" } ),
    # The block between the spawn road and the north alley.
    ( -1850, -1400, 850, 1100, 316, "render_terracotta", { "+n": ( "sws", None ), "-e": ( "wdw", None ), "+e": ( "wdw", None ) },
      "e", { "awning": "canvas_green", "plaques": ( ( "+e", 1, "plaque_1" ), ) } ),
    ( -1850, -1400, 600, 850, 276, "render_cream", { "-e": ( "wdw", None ), "+e": ( "wdw", None ) }, "e", {} ),
    ( -1850, -1400, 350, 600, 300, "render_rose", { "-n": ( "sws", None ), "-e": ( "wdw", None ), "+e": ( "wdw", None ) },
      "e", { "plaques": ( ( "-n", 0, "plaque_0" ), ( "-e", 0, "plaque_7" ) ) } ),
    # Between the spawn road and the south alley.
    ( -1850, -1400, -350, -100, 310, "render_cream", { "+n": ( "sws", None ), "-e": ( "wdw", None ), "+e": ( "ww", None ) },
      "e", { "awning": "canvas_red", "plaques": ( ( "+e", 1, "plaque_2" ), ) } ),
    ( -1850, -1400, -650, -350, 270, "render_ochre", { "-e": ( "wdww", None ), "+e": ( "wdw", None ) }, "e", {} ),
    ( -1850, -1400, -900, -650, 296, "render_rose", { "-n": ( "wdw", None ), "-e": ( "ww", None ), "+e": ( "wdw", None ) },
      "e", { "plaques": ( ( "-n", 0, "plaque_8" ), ) } ),
    # Beside the Bakery and the Town Hall, facing Market Street.
    ( -850, -650, 700, 1100, 310, "render_rose", { "+n": ( "sd", None ) }, "n", {} ),
    ( -650, -450, 700, 1100, 290, "render_ochre", { "+n": ( "ws", None ) }, "n", { "awning": "canvas_red" } ),
    # The square's north-west corner, its side onto the Bakery's yard.
    ( -850, -650, 350, 700, 300, "render_terracotta", { "-n": ( "ds", None ), "+e": ( "sw", ( 350, 550 ) ), "-e": ( "-w-", None ) },
      "n", { "awning": "canvas_green" } ),
    ( -650, -450, 550, 700, 280, "render_cream", { "-n": ( "ws", None ) }, "e",
      { "awning": "canvas_red", "plaques": ( ( "-n", 0, "plaque_9" ), ) } ),
    # The square's south-west corner: a café's shopfronts onto the square (the churchyard wall meets its south bay).
    ( -800, -650, -450, -100, 300, "render_terracotta", { "+n": ( "ds", None ), "+e": ( "-ss", None ), "-n": ( "w", None ) },
      "n", { "awning": "canvas_red", "names": ( 0, 0, 0 ) } ),
]

# The buildings people go into, and the walls, that the houses stand against: ( e0, e1, n0, n1, height ), west half.
OPEN_BUILDINGS = [
    ( -450, 450, 550, 1100, HALL_EAVE ),        # the Town Hall (whole)
    ( -170, 170, -900, -400, 300 ),             # the church (whole)
    ( -1250, -850, 700, 1100, 276 ),            # the Bakery
    ( -1250, -800, -450, -100, 276 ),           # the Inn
]
WALLS = [
    ( -1250, -850, 350, 362, 96 ), ( -1250, -1238, 362, 700, 96 ),                                       # the Bakery's yard
    ( -1250, -650, -900, -888, 90 ), ( -1250, -1238, -888, -450, 90 ), ( -662, -650, -888, -450, 90 ),  # the beer garden
    ( -650, -170, -410, -400, 40 ), ( -650, -170, -900, -890, 40 ),                                     # the churchyard
    ( TOWN_WALL[0], TOWN_WALL[1], SOUTH_EDGE, 1880, 240 ), ( TOWN_WALL[0], ROAD[1], 1800, 1880, 240 ),  # the town walls
]


def blocks():
    """ Everything a house can stand against, both halves. """
    west = [ h[:5] for h in HOUSES ] + OPEN_BUILDINGS + WALLS
    return west + [ ( -e1, -e0, n0, n1, height ) for e0, e1, n0, n1, height in west ]


def west_houses( model, rng ):
    shutters = [ "shutter_red", "shutter_brown", "shutter_green" ]
    trims = [ "trim_white", "trim_brown", "trim_white", "trim_red" ]
    against = blocks()
    for e0, e1, n0, n1, eave, render, faces, ridge, extras in HOUSES:
        solid_house( model, e0, e1, n0, n1, eave, render, faces, ridge, rng, against,
                     trim=extras.get( "trim", trims[int( rng.integers( 0, len( trims ) ) )] ),
                     shutter=extras.get( "shutter", shutters[int( rng.integers( 0, len( shutters ) ) )] ),
                     sign=extras.get( "sign", "trim_green" ), awning_paint=extras.get( "awning" ),
                     surround=extras.get( "surround" ), ends_over=extras.get( "ends_over", ( 14.0, 14.0 ) ),
                     gables=extras.get( "gables", ( True, True ) ), balconies=extras.get( "balconies", 0.25 ),
                     names=extras.get( "names", () ), plaques=extras.get( "plaques", () ) )
        if rng.random() < 0.6:
            # A chimney on the ridge.
            if ridge == "e":
                ce, cn = e0 + ( e1 - e0 ) * rng.uniform( 0.2, 0.8 ), ( n0 + n1 ) / 2
            else:
                ce, cn = ( e0 + e1 ) / 2, n0 + ( n1 - n0 ) * rng.uniform( 0.25, 0.75 )
            top = eave + min( e1 - e0, n1 - n0 ) / 2 * math.tan( math.radians( ROOF_PITCH ) ) + 44
            model.box( ( ce - 14, cn - 12, eave ), ( ce + 14, cn + 12, top ), { "default": "brick", "+z": "iron_black" } )
            model.box( ( ce - 16, cn - 14, top - 8 ), ( ce + 16, cn + 14, top - 4 ), "ashlar_grey" )


# ---------------------------------------------------------------------------------------------------------------------
# The Bakery and its yard (west; its mirror is the Dairy)

def bakery( model, lights, rng ):
    e0, e1, n0, n1 = -1250.0, -850.0, 700.0, 1100.0
    T, GF, EAVE = 12.0, 150.0, 276.0
    paints = { "outside": "render_ochre", "inside": "whitewash", "reveal": "render_ochre", "sill": "ashlar" }
    openings = {
        "+n": [ ( -1050, 60, 0, 104, "door" ), ( -1170, 96, 30, 112, "window" ), ( -930, 96, 30, 112, "window" ),
                ( -1170, 46, 184, 254, "glass" ), ( -1050, 46, 184, 254, "glass" ), ( -930, 46, 184, 254, "glass" ) ],
        "-n": [ ( -1050, 60, 0, 104, "door" ), ( -1170, 50, 40, 112, "window" ), ( -1170, 46, 184, 254, "glass" ),
                ( -930, 46, 184, 254, "glass" ) ],
        "-e": [ ( 800, 56, 0, 104, "door" ), ( 1000, 50, 40, 112, "window" ), ( 800, 46, 184, 254, "glass" ),
                ( 1000, 46, 184, 254, "glass" ) ],
    }
    walls = shell( model, e0, e1, n0, n1, 0, EAVE, openings, paints, T, hidden=( "+e", ) )
    style = { "trim": "trim_brown", "shutter": "shutter_red", "sill": "ashlar", "solid": True }
    for face, wall in walls.items():
        if face == "+e":
            continue
        dress( model, wall, style, rng )
        courses( model, wall, 0, 20, 2.5, "ashlar_grey" )
        slab_at( model, wall, wall.run[0], wall.run[1], 0.0, 7.0, EAVE - 12, EAVE, "trim_white" )
    # An old sign for the bread and pasta between the upper windows over the yard, seen over its wall from West Street.
    ghost_sign( model, walls["-n"], -1106, -994, 201, "ghost_1" )
    climb_ivy( model, walls["-n"], 1.3, ( "bakery", "-n" ) )
    # The shop sign over the door and the upper floor, which nobody goes into.
    slab_at( model, walls["+n"], -1105, -995, 0.0, 3.0, 119.9, 140.1, { walls["+n"].outward: "sign_2", "default": "trim_red" } )
    model.collision_box( ( e0 + T, n0 + T, GF ), ( e1 - T, n1 - T, EAVE ), STONE )
    ceiling( model, e0 + T, e1 - T, n0 + T, n1 - T, GF, "planks", ( "e", 70 ) )
    gable_roof( model, e0, e1, n0, n1, EAVE, "e", "roof_tiles", paints["outside"], gutter="copper_brown" )
    floor( model, e0, e1, n0, n1, "quarry_tiles" )
    inner_wall( model, "e", ( e0 + T, e1 - T ), ( 894, 906 ), ( 0, GF ), [ ( -1150, 64, 0, 104, "door" ) ], "whitewash" )
    # The shop: its counter and shelves.
    model.box( ( -1100, 960, 0 ), ( -960, 996, 40 ), { "+z": "planks", "default": "planks_dark" }, WOOD )
    model.box( ( e1 - T - 24, 920, 0 ), ( e1 - T, 1080, 96 ), "planks_dark", WOOD )
    for z in ( 30, 60 ):
        model.box( ( e1 - T - 26, 922, z ), ( e1 - T - 24, 1078, z + 3 ), "planks" )
    # The bakehouse: the oven and its chimney, the kneading table and flour sacks.
    model.box( ( -980, 730, 0 ), ( e1 - T, 870, 64 ), "brick", STONE )
    axle( model, ( -921, 800, 64 ), ( 0, 1, 0 ), 55, 136, { "side": "brick", "end": "brick" }, sides=14 )
    model.collision_box( ( -980, 730, 64 ), ( e1 - T, 870, 110 ), STONE )
    facing( model, "iron_black", [ ( -980.5, 780, 18 ), ( -980.5, 820, 18 ), ( -980.5, 820, 48 ), ( -980.5, 780, 48 ) ], ( -1, 0, 0 ) )
    model.box( ( -905, 780, 110 ), ( -875, 820, 430 ), { "default": "brick", "+z": "iron_black" }, STONE )
    model.box( ( -1110, 790, 0 ), ( -1030, 840, 34 ), { "+z": "planks", "default": "planks_dark" }, WOOD )
    sacks( model, ( -1215, 730 ), 0, 7 )
    lights.append( light( "Bakery Shop", ( -1050, 1000, 120 ) ) )
    lights.append( light( "Bakehouse", ( -1080, 800, 120 ), "1,0.72,0.45,1", 380 ) )

    # The yard: walls onto West Street and the alley, a cart and the woodpile.
    wall_run( model, "e", ( -1250, -850 ), ( 350, 362 ), 0, 96, [ ( -1105, -995 ) ] )
    wall_run( model, "n", ( 362, 700 ), ( -1250, -1238 ), 0, 96, [ ( 490, 560 ) ] )
    # Ivy from the yard over its walls, onto West Street and the alley.
    wall_top_ivy( model, "e", ( -1250, -850 ), ( 350, 362 ), "-n", 0, 96, [ ( -1105, -995 ) ], ( "yard", "-n" ), share=0.7 )
    wall_top_ivy( model, "n", ( 362, 700 ), ( -1250, -1238 ), "-e", 0, 96, [ ( 490, 560 ) ], ( "yard", "-e" ), share=0.6 )
    cart( model, ( -1150, 470 ), 98, load="sacks" )
    model.box( ( -1236, 664, 0 ), ( -1130, 698, 42 ), { "default": "planks_dark", "+z": "planks" }, WOOD )
    for k in range( 6 ):
        axle( model, ( -1183, 681, 6 + k * 6.5 ), ( 1, 0, 0 ), 5, 104, { "side": "planks_dark", "end": "planks" }, sides=6 )
    barrel( model, ( -876, 676 ), r=15, h=40 )
    crates( model, ( -900, 400 ), 92, rng )


# ---------------------------------------------------------------------------------------------------------------------
# The Inn and its beer garden (west; its mirror is the Tavern)

def inn( model, lights, rng ):
    e0, e1, n0, n1 = -1250.0, -800.0, -450.0, -100.0
    T, GF, FL, CEIL, EAVE = 12.0, 140.0, 148.0, 268.0, 276.0
    paints = { "outside": "render_rose", "inside": "whitewash", "reveal": "render_rose", "sill": "ashlar" }
    openings = {
        "+n": [ ( -1020, 60, 0, 104, "door" ), ( -1170, 60, 36, 106, "window" ), ( -880, 60, 36, 106, "window" ),
                ( -1170, 50, FL + 36, FL + 106, "window" ), ( -1020, 50, FL + 36, FL + 106, "window" ),
                ( -880, 50, FL + 36, FL + 106, "window" ) ],
        "-n": [ ( -1100, 60, 0, 104, "door" ), ( -960, 50, 36, 106, "window" ), ( -1170, 50, FL + 36, FL + 106, "window" ),
                ( -960, 50, FL + 36, FL + 106, "window" ) ],
        "-e": [ ( -330, 56, 0, 104, "door" ), ( -200, 44, 40, 106, "window" ), ( -275, 44, FL + 36, FL + 106, "window" ) ],
    }
    walls = shell( model, e0, e1, n0, n1, 0, EAVE, openings, paints, T, hidden=( "+e", ) )
    style = { "trim": "trim_brown", "shutter": "shutter_brown", "sill": "ashlar" }
    for face, wall in walls.items():
        if face == "+e":
            continue
        dress( model, wall, style, rng )
        courses( model, wall, 0, 20, 2.5, "ashlar_grey" )
        courses( model, wall, GF, FL, 2.0, "trim_white" )
        slab_at( model, wall, wall.run[0], wall.run[1], 0.0, 7.0, EAVE - 12, EAVE, "trim_white" )
    floor( model, e0, e1, n0, n1, "floorboards" )
    # Upstairs, over the taproom, reached by a stair along the east wall.
    stair_lo, stair_hi = ( e1 - T - 60, -395 ), ( e1 - T, -186 )
    stair( model, stair_lo, stair_hi, 0, FL, "+n", "planks", "planks_dark" )
    floor_slab( model, e0 + T, e1 - T, n0 + T, n1 - T, GF, FL, [ ( stair_lo[0], stair_hi[0], stair_lo[1], stair_hi[1] ) ],
                { "+z": "floorboards", "-z": "planks", "default": "planks_dark" } )
    model.box( ( stair_lo[0] - 6, stair_lo[1] - 6, FL ), ( stair_lo[0], stair_hi[1], FL + 36 ), "planks_dark", WOOD )
    model.box( ( stair_lo[0] - 6, stair_lo[1] - 6, FL ), ( stair_hi[0], stair_lo[1], FL + 36 ), "planks_dark", WOOD )
    model.box( ( e0 + T, n0 + T, CEIL ), ( e1 - T, n1 - T, EAVE ), { "-z": "planks", "default": None }, STONE )
    ceiling( model, e0 + T, e1 - T, n0 + T, n1 - T, GF, None, ( "e", 75 ),
             holes=[ ( stair_lo[0], stair_hi[0], stair_lo[1], stair_hi[1] ) ] )
    ceiling( model, e0 + T, e1 - T, n0 + T, n1 - T, CEIL, None, ( "e", 75 ) )
    # Its east gable stands over the café's roof.
    gable_roof( model, e0, e1, n0, n1, EAVE, "e", "roof_tiles", paints["outside"], ends_over=( 14, 0 ), gutter="metal" )
    model.box( ( -830, -300, EAVE ), ( -806, -250, 470 ), { "default": "brick", "+z": "iron_black" } )
    # The taproom: the bar, its shelf of bottles, tables and barrels.
    model.box( ( -960, -370, 0 ), ( -920, -180, 42 ), { "+z": "planks", "default": "planks_dark" }, WOOD )
    for k in range( 5 ):
        model.cylinder( ( -950 + ( k % 2 ) * 20, -350 + k * 36 ), 3, 42, 54, { "side": "glass", "top": "iron_black" }, sides=6 )
    for centre in ( ( -1150, -400 ), ( -1150, -230 ) ):
        model.cylinder( centre, 24, 0, 30, { "side": "planks_dark", "top": "planks" }, sides=10, surface=WOOD )
        for a in range( 3 ):
            ang = a * 2.1 + 0.4
            model.cylinder( ( centre[0] + 36 * math.cos( ang ), centre[1] + 36 * math.sin( ang ) ), 8, 0, 18,
                            { "side": "planks_dark", "top": "planks" }, sides=6 )
    barrels( model, ( -842, -140 ), 2, rng )
    # Upstairs: beds, a wardrobe and a table.
    for ea in ( -1230, -1120 ):
        model.box( ( ea, -430, FL ), ( ea + 42, -350, FL + 20 ), { "+z": "canvas_plain", "default": "planks_dark" }, WOOD )
        model.box( ( ea, -438, FL ), ( ea + 42, -430, FL + 40 ), "planks_dark", WOOD )
    model.box( ( e0 + T, -250, FL ), ( e0 + T + 24, -190, FL + 88 ), "planks_dark", WOOD )
    model.box( ( -1050, -300, FL ), ( -1000, -260, FL + 30 ), { "+z": "planks", "default": "planks_dark" }, WOOD )
    # The inn's sign (belltower_fronts' insegna) hanging from a wrought-iron bracket, and lanterns either side of its door.
    model.box( ( -1114, -100, 180 ), ( -1106, -99, 206 ), "iron_black" )
    model.beam( ( -1110, -99, 200 ), ( -1110, -56, 200 ), ( 1.6, 1.6 ), "iron_black" )
    model.beam( ( -1110, -99, 182 ), ( -1110, -78, 200 ), ( 1.2, 1.2 ), "iron_black" )
    Detail.hoop( model, ( -1110, -91, 194 ), ( 0, 1.0, 0 ), ( 0, 0, 1.0 ), 3.0, 0.4, "iron_black" )
    Detail.ball( model, ( -1110, -55.2, 200 ), 1.1, "iron_black", rings=4, segments=8 )
    for n in ( -93, -69 ):
        Detail.rod( model, ( -1110, n, 199.2 ), ( -1110, n, 187.8 ), 0.3, "iron_black", sides=6 )
    model.box( ( -1110.6, -96, 166 ), ( -1109.4, -66, 188 ), { "+e": "insegna_0", "-e": "insegna_0", "default": "planks_dark" } )
    door = next( o for o in walls["+n"].openings if o.kind == "door" )
    for r in ( door.r0 - 12, door.r1 + 12 ):
        wall_lantern( model, walls["+n"], r, door.z1 + 14, but=door )
    # An old sign for its kitchen up its side wall, over the alley.
    ghost_sign( model, walls["-e"], -226, -126, 198, "ghost_0" )
    climb_ivy( model, walls["-n"], 1.3, ( "inn", "-n" ) )
    lights.append( light( "Inn Taproom", ( -1040, -280, 110 ) ) )
    lights.append( light( "Inn Upstairs", ( -1030, -280, 240 ), radius=360 ) )

    # The beer garden: walls with gates to the terrace, the alley and the churchyard, the pergola, tables and a tree.
    wall_run( model, "e", ( -1250, -650 ), ( -900, -888 ), 0, 90, [ ( -1010, -930 ) ] )
    wall_run( model, "n", ( -888, -450 ), ( -1250, -1238 ), 0, 90, [ ( -720, -650 ) ] )
    wall_run( model, "n", ( -888, -450 ), ( -662, -650 ), 0, 90, [ ( -830, -760 ) ] )
    # Ivy from the garden over its walls, onto the terrace, the alley and the churchyard.
    wall_top_ivy( model, "e", ( -1250, -650 ), ( -900, -888 ), "-n", 0, 90, [ ( -1010, -930 ) ], ( "beer", "-n" ) )
    wall_top_ivy( model, "n", ( -888, -450 ), ( -1250, -1238 ), "-e", 0, 90, [ ( -720, -650 ) ], ( "beer", "-e" ) )
    wall_top_ivy( model, "n", ( -888, -450 ), ( -662, -650 ), "+e", 0, 90, [ ( -830, -760 ) ], ( "beer", "+e" ) )
    for e in ( -1180, -1080, -980 ):
        for n in ( -560, -680 ):
            model.cylinder( ( e, n ), 5, 0, 104, { "side": "planks_dark" }, sides=6, surface=WOOD )
    for n in ( -560, -680 ):
        model.box( ( -1196, n - 4, 104 ), ( -964, n + 4, 112 ), "planks_dark" )
    for e in np.arange( -1190, -965, 32 ):
        model.box( ( e - 2, -700, 112 ), ( e + 2, -540, 116 ), "planks_dark" )
    for k, e in enumerate( ( -1150, -1050 ) ):
        blob( model, ( e, -620, 122 ), 60, "hedge", squash=0.25, segments=8, rings=4, seed=40 + k )
    for centre in ( ( -1130, -620 ), ( -1030, -620 ), ( -800, -600 ), ( -800, -780 ), ( -1110, -830 ) ):
        picnic_table( model, centre, 90 )
    tree( model, ( -730, -530 ), 0, 300, 110, seed=21 )
    barrels( model, ( -1010, -500 ), 3, rng )
    crates( model, ( -1215, -870 ), 90, rng )


def picnic_table( model, centre, yaw, z=0.0 ):
    p = Place( ( centre[0], centre[1], z ), yaw )
    p.box( model, ( -42, -16, 27 ), ( 42, 16, 30 ), "planks" )
    for s in ( -1, 1 ):
        p.box( model, ( -42, s * 30 - 6, 15 ), ( 42, s * 30 + 6, 18 ), "planks" )
        p.box( model, ( s * 32 - 2, -34, 0 ), ( s * 32 + 2, 34, 27 ), "planks_dark" )
    p.box( model, ( -42, -36, 0 ), ( 42, 36, 30 ), None, WOOD )


# ---------------------------------------------------------------------------------------------------------------------
# The west churchyard, the terrace and the gardens

def churchyard( model, rng ):
    wall_run( model, "e", ( -650, -170 ), ( -410, -400 ), 0, 40, [ ( -450, -370 ) ], pier_height=64 )
    wall_run( model, "e", ( -650, -170 ), ( -900, -890 ), 0, 40, [ ( -450, -370 ) ], pier_height=64 )
    stones = [ ( e, n ) for e in ( -610, -570, -530 ) for n in ( -470, -530, -590, -870 ) ] + \
             [ ( e, n ) for e in ( -330, -290, -250 ) for n in ( -470, -530, -590 ) ]
    for k, ( e, n ) in enumerate( stones ):
        if rng.random() < 0.18:
            continue
        lean = rng.uniform( -5, 5 )
        p = Place( ( e + rng.uniform( -6, 6 ), n + rng.uniform( -6, 6 ), 0 ), 90 + lean )
        if rng.random() < 0.3:
            p.box( model, ( -3, -3, 0 ), ( 3, 3, 40 ), "ashlar_grey", STONE )
            p.box( model, ( -3, -12, 26 ), ( 3, 12, 32 ), "ashlar_grey" )
        else:
            height = rng.uniform( 24, 34 )
            p.box( model, ( -3, -11, 0 ), ( 3, 11, height ), "ashlar_grey", STONE )
    for centre in ( ( -560, -700 ), ( -290, -770 ) ):
        e, n = centre
        model.box( ( e - 22, n - 42, 0 ), ( e + 22, n + 42, 30 ), "ashlar", STONE )
        model.box( ( e - 25, n - 45, 30 ), ( e + 25, n + 45, 34 ), "ashlar_grey", STONE )
    tree( model, ( -620, -640 ), 0, 190, 70, seed=33, trunk_r=11 )
    bench( model, ( -190, -820 ), -90, 50 )


TERRACE_STAIRS = [ ( -1130, -1070 ), ( -90, 0 ) ]     # the stairs down to the gardens, e (the middle one whole with its mirror)
STAIR_FOOT = -1066                                     # where they reach the gardens, n


def terrace( model, rng ):
    """ The terrace walk along the south block's back, its parapet over the gardens and the stairs down. """
    gaps = TERRACE_STAIRS
    r = -1850.0
    for g0, g1 in gaps + [ ( 0, 0 ) ]:
        if g0 > r:
            model.box( ( r, -1000, GARDEN_Z ), ( g0, -988, 28 ), { "default": "rubble", "+n": "ashlar" }, STONE )
            model.box( ( r - 1.5, -1001.5, 28 ), ( g0 + ( 1.5 if g0 < 0 else 0 ), -986.5, 32 ), "ashlar_grey", STONE )
        r = g1
    for ea, eb in gaps:
        stair( model, ( ea, STAIR_FOOT ), ( eb, -1000 ), GARDEN_Z, 0, "+n", "ashlar", "ashlar_grey", STONE )
        for cheek in ( ( ea - 12, ea ), ( eb, eb + 12 ) ):
            if cheek[1] > 0:
                continue
            model.box( ( cheek[0], STAIR_FOOT, GARDEN_Z ), ( cheek[1], -1000, 6 ), { "default": "rubble", "+z": "ashlar_grey" }, STONE )
    # Ivy over the parapet, down the drop into the gardens: its gaps are the stairs and their cheeks.
    wall_top_ivy( model, "e", ( ROAD[1], gaps[-1][0] ), ( TERRACE[0], TERRACE[0] + 12 ), "-n", GARDEN_Z, 32,
                  [ ( ea - 12, eb + 12 ) for ea, eb in gaps[:-1] ], ( "terrace", ), every=130.0, share=0.55, piers=False )
    for e in ( -1640, -1340, -820, -420 ):
        bench( model, ( e, -965 ), 0, 80 )
    for e in ( -1500, -900, -300 ):
        lamp_post( model, ( e, -915 ) )


def gardens( model, rng ):
    z = GARDEN_Z
    # Low walls at the plots' ends, broken for the main path; hedges round the parterre.
    for e in ( -1450, -750 ):
        low_wall( model, e - 12, e, -1450, -1290, z, z + 40 )
        low_wall( model, e - 12, e, -1170, -1080, z, z + 40 )
    hedge( model, -262, -250, -1450, -1290, z, 70 )
    hedge( model, -262, -250, -1170, -1080, z, 70 )
    for n0, n1 in ( ( -1400, -1290 ), ( -1180, -1090 ) ):
        # The parterre's beds, each in a low box hedge.
        for ea, eb in ( ( -210, -110 ), ):
            hedge( model, ea, eb, n0, n0 + 10, z, 22 )
            hedge( model, ea, eb, n1 - 10, n1, z, 22 )
            hedge( model, ea, ea + 10, n0 + 10, n1 - 10, z, 22 )
            hedge( model, eb - 10, eb, n0 + 10, n1 - 10, z, 22 )
            for k in range( 6 ):
                blob( model, ( rng.uniform( ea + 20, eb - 20 ), rng.uniform( n0 + 20, n1 - 20 ), z + 8 ), 10,
                      "canvas_red" if k % 2 else "hedge", squash=0.6, segments=6, rings=3, seed=int( rng.integers( 0, 9999 ) ) )
    # Vegetable beds, a shed and a scarecrow in the west plot; more beds and the potting shed further in.
    for ea, eb in ( ( -1700, -1480 ), ( -720, -460 ) ):
        for n in ( -1420, -1370, -1320 ):
            model.box( ( ea, n - 15, z ), ( eb, n + 15, z + 10 ), { "+z": "soil", "default": "planks_dark" }, DIRT )
            for e in np.arange( ea + 14, eb - 10, 26 ):
                blob( model, ( e + rng.uniform( -4, 4 ), n + rng.uniform( -4, 4 ), z + 16 ), 8, "hedge", squash=0.6,
                      segments=6, rings=3, seed=int( rng.integers( 0, 9999 ) ) )
    shed( model, -1840, -1720, -1440, -1340, z, "+n", rng )
    shed( model, -420, -300, -1440, -1360, z, "+n", rng )
    shed( model, -1440, -1380, -1090, -1030, z, "+e", rng, small=True )
    p = Place( ( -1590, -1345, z ), 0 )
    p.beam( model, ( 0, 0, 0 ), ( 0, 0, 74 ), ( 3, 3 ), "planks_dark" )
    p.beam( model, ( -24, 0, 56 ), ( 24, 0, 56 ), ( 3, 3 ), "planks_dark" )
    p.box( model, ( -12, -6, 30 ), ( 12, 6, 60 ), "canvas_green" )
    blob( model, p.at( ( 0, 0, 68 ) ), 7, "canvas_plain", squash=1.1, segments=6, rings=4, seed=4 )
    cone( model, p.at( ( 0, 0, 0 ) )[:2], 12, z + 73, z + 84, "canvas_plain", sides=8 )
    # The orchard, and its well.
    k = 0
    for e in ( -1380, -1290, -1200, -1000, -910, -820 ):
        for n in ( -1400, -1320, -1150 ):
            if ( e, n ) in ( ( -1380, -1150 ), ):
                continue
            k += 1
            tree( model, ( e + rng.uniform( -10, 10 ), n + rng.uniform( -10, 10 ) ), z, rng.uniform( 120, 150 ),
                  rng.uniform( 42, 56 ), seed=100 + k, trunk_r=6 )
    ring( model, ( -1100, -1365 ), 22, 32, z, z + 32, 10, { "outside": "rubble", "inside": "rubble", "top": "ashlar_grey" }, STONE )
    model.cylinder( ( -1100, -1365 ), 22, z + 6, z + 7, { "top": "water" }, sides=10, turn=math.pi / 10 )
    # The woodpile and compost bins by the garden wall; a wheelbarrow; a gazebo among the flower beds.
    model.box( ( -1840, -1170, z ), ( -1740, -1140, z + 40 ), { "default": "planks_dark", "+z": "planks" }, WOOD )
    for ea in ( -1700, -1640 ):
        model.box( ( ea, -1080, z ), ( ea + 50, -1030, z + 36 ), { "default": "planks", "+z": "soil" }, WOOD )
    p = Place( ( -1520, -1180, z ), 20 )
    p.box( model, ( -20, -14, 12 ), ( 20, 14, 26 ), "iron_green" )
    axle( model, p.at( ( 26, 0, 8 ) ), p.y, 8, 4, { "side": "iron_black", "end": "iron_black" }, sides=8 )
    p.beam( model, ( -20, -10, 22 ), ( -48, -12, 30 ), ( 2.5, 2.5 ), "planks_dark" )
    p.beam( model, ( -20, 10, 22 ), ( -48, 12, 30 ), ( 2.5, 2.5 ), "planks_dark" )
    for k in range( 6 ):
        a = 2 * math.pi * k / 6
        model.cylinder( ( -500 + 56 * math.cos( a ), -1130 + 56 * math.sin( a ) ), 4, z, z + 96, { "side": "iron_green" },
                        sides=6, surface=METAL )
    cone( model, ( -500, -1130 ), 72, z + 96, z + 150, "copper", sides=6, turn=0.0 )
    bench( model, ( -500, -1160 ), 0, 60, z )
    for e, n in ( ( -650, -1160 ), ( -350, -1160 ) ):
        model.box( ( e - 60, n - 18, z ), ( e + 60, n + 18, z + 14 ), { "+z": "soil", "default": "ashlar_grey" }, STONE )
        for k in range( 8 ):
            blob( model, ( e - 50 + k * 14, n + rng.uniform( -8, 8 ), z + 20 ), 8, "canvas_red" if k % 3 == 0 else "hedge",
                  squash=0.7, segments=6, rings=3, seed=int( rng.integers( 0, 9999 ) ) )


def shed( model, e0, e1, n0, n1, z, door, rng, small=False ):
    """ A plank shed with a lean-to roof of corrugated iron, shut. One collision box. """
    height = 84 if small else 100
    model.box( ( e0, n0, z ), ( e1, n1, z + height ), "planks", WOOD )
    wall = face_wall( e0, e1, n0, n1, door, z, z + height, 2.0 )
    r0, r1 = wall.run
    rc = ( r0 + r1 ) / 2
    slab_at( model, wall, rc - 20, rc + 20, 0.0, 1.5, z, z + 76, "planks_dark" )
    slab_at( model, wall, rc + 12, rc + 16, 1.5, 2.5, z + 36, z + 40, "iron_black" )
    rise = 16
    model.oriented_box( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z + height + rise / 2 + 2 ),
                        ( ( 1, 0, 0 ), normalise( ( 0, 1, -rise / ( n1 - n0 + 16 ) ) ),
                          np.cross( ( 1, 0, 0 ), normalise( ( 0, 1, -rise / ( n1 - n0 + 16 ) ) ) ) ),
                        ( e1 - e0 + 12, math.hypot( n1 - n0 + 16, rise ), 3 ), { "+z": "corrugated", "default": "iron_black" } )


# ---------------------------------------------------------------------------------------------------------------------
# The west town wall, its gate and the parapets round the edge

def town_walls( model ):
    wall = Wall( "n", ( SOUTH_EDGE, 1880 ), TOWN_WALL, ( -500, 240 ), "-e" )
    wall.add( 0, 160, 0, 200, "arch" )
    wall.build( model, "rubble", "rubble", "ashlar", "rubble", STONE )
    rect( model, "ashlar_grey", TOWN_WALL[0], TOWN_WALL[1], SOUTH_EDGE, 1800, 240 )
    # The blocked gate: a studded leaf in the arch.
    model.box( ( -2346, -80, 0 ), ( -2334, 80, 200 ), "planks_dark", WOOD )
    for z in ( 30, 100, 170 ):
        model.box( ( -2334, -78, z ), ( -2333, 78, z + 5 ), "iron_black" )
    # Gate towers either side.
    for n0, n1 in ( ( -230, -110 ), ( 110, 230 ) ):
        model.box( ( -2410, n0, -500 ), ( -2280, n1, 330 ), { "default": "rubble", "+z": "ashlar_grey" }, STONE )
        model.box( ( -2414, n0 - 4, 318 ), ( -2276, n1 + 4, 330 ), "ashlar_grey" )
        for k in range( 3 ):
            ce = -2410 + 20 + k * 45
            model.box( ( ce - 12, n0 - 4, 330 ), ( ce + 12, n0 + 12, 362 ), "rubble", STONE )
            model.box( ( ce - 12, n1 - 12, 330 ), ( ce + 12, n1 + 4, 362 ), "rubble", STONE )
        for nn in ( n0 + 36, n1 - 36 ):
            model.box( ( -2410, nn - 12, 360 - 30 ), ( -2398, nn + 12, 362 ), "rubble", STONE )
            model.box( ( -2292, nn - 12, 330 ), ( -2280, nn + 12, 362 ), "rubble", STONE )
        # The town's banner over the road (belltower_fronts' 36 x 72, half as big again), hung flat from an iron rod
        # on two brackets. The east's is blue (EAST_PAINTS).
        face, nc, top = TOWN_WALL[1] + 20, ( n0 + n1 ) / 2, 252.0
        for nb in ( nc - 24, nc + 24 ):
            model.box( ( face, nb - 2, top - 6 ), ( face + 0.8, nb + 2, top + 3 ), "iron_black" )
            model.beam( ( face + 0.8, nb, top ), ( face + 5.0, nb, top ), ( 1.0, 1.0 ), "iron_black" )
        model.beam( ( face + 4.5, nc - 30, top ), ( face + 4.5, nc + 30, top ), ( 1.2, 1.2 ), "iron_black" )
        for nb in ( nc - 30.8, nc + 30.8 ):
            Detail.ball( model, ( face + 4.5, nb, top ), 1.2, "iron_black", rings=4, segments=8 )
        facing( model, "banner_red", [ ( face + 4.0, nc - 27, top - 108 ), ( face + 4.0, nc + 27, top - 108 ),
                                       ( face + 4.0, nc + 27, top - 0.5 ), ( face + 4.0, nc - 27, top - 0.5 ) ], ( 1, 0, 0 ) )
    # Ivy up the wall's inner face over the road, now and then, where the road is level along the patch: north of the
    # ramp down to the gardens, and between it and the south parapet. Clear of the gate's towers and the trough.
    inner = Wall( "n", ( SOUTH_EDGE, 1800 ), TOWN_WALL, ( GARDEN_Z, 240 ), "+e" )
    level = ( ( GARDENS[0] + 4, RAMP[0] - 4 ), ( RAMP[1] + 4, 1800 ) )
    kept_off = ( ( -245, 245 ), ( 320, 440 ) )
    for k, n in enumerate( ( -1380, -1270, -900, -700, -500, 500, 700, 900, 1100, 1300, 1500, 1700 ) ):
        if not chance( 0.6, "wall_ivy", k ):
            continue
        n += pick( ( -40, -20, 0, 20, 40 ), "wall_ivy_shift", k )
        scale = pick( ( 1.5, 1.75, 2.0 ), "wall_ivy_scale", k )
        side = pick( ( -1, 1 ), "wall_ivy_side", k )
        pair = chance( 0.5, "wall_ivy_pair", k )
        # Its span along the wall, with the smaller patch beside it if it gets one.
        lo, hi = n - IVY[0] * scale / 2, n + IVY[0] * scale / 2
        if pair:
            lo, hi = min( lo, n - IVY[0] * scale * 1.05 ), max( hi, n + IVY[0] * scale * 1.05 )
        if not any( a <= lo and hi <= b for a, b in level ) or any( a < hi and lo < b for a, b in kept_off ):
            continue
        z0 = float( floor_level( TOWN_WALL[1] + 1, n ) )
        if ivy( model, inner, n, z0, scale, "ivy_climb", 1.2, ( "wall", k ) ) and pair:
            # A second, smaller patch overlapping its side, a little further out.
            first = inner.fixtures.pop()
            ivy( model, inner, n + side * IVY[0] * scale * 0.7, z0, scale * 0.7, "ivy_climb", 1.9, ( "wall", k, "b" ) )
            inner.fixtures.append( first )
    # Merlons along the walls' outer edges.
    for n in np.arange( SOUTH_EDGE + 30, 1860, 70 ):
        if -250 < n < 250:
            continue
        model.box( ( -2380, n - 20, 240 ), ( -2366, n + 20, 274 ), "rubble", STONE )
    model.box( ( -2380, 1800, -500 ), ( ROAD[1], 1880, 240 ), { "default": "rubble", "+z": "ashlar_grey" }, STONE )
    for e in np.arange( -2330, ROAD[1] - 10, 70 ):
        model.box( ( e - 20, 1866, 240 ), ( e + 20, 1880, 274 ), "rubble", STONE )
    # The north row stands on the hill's edge.
    model.box( ( ROAD[1], 1788, -500 ), ( 0, 1800, 0 ), { "default": "rubble", "+z": None, "-n": None, "+e": None }, STONE )
    # The south parapet over the drop.
    model.box( ( -2380, SOUTH_EDGE, -500 ), ( 0, -1450, -12 ), { "default": "rubble", "+z": None, "+e": None }, STONE )
    model.box( ( -2382, SOUTH_EDGE - 2, -12 ), ( 0, -1448, -6 ), { "default": "ashlar_grey", "+e": None }, STONE )
    # The wall between the road's ramp and the gardens.
    model.box( ( ROAD[1] - 12, RAMP[0], GARDEN_Z ), ( ROAD[1], RAMP[1], 28 ), "rubble", STONE )
    model.box( ( ROAD[1] - 13.5, RAMP[0] - 1.5, 28 ), ( ROAD[1] + 1.5, RAMP[1], 32 ), "ashlar_grey", STONE )


# ---------------------------------------------------------------------------------------------------------------------
# The west half's ground: paving, the gardens and the road's ramp, and the collision under them

def ground( model ):
    rect( model, "setts", ROAD[0], ROAD[1], TERRACE[0], NORTH_ROW[1], 0 )
    rect( model, "setts", ROAD[1], 0, MARKET[0], MARKET[1], 0 )
    rect( model, "setts", ROAD[1], SQUARE[0], MID[0], MID[1], 0 )
    rect( model, "flagstones", SQUARE[0], 0, SQUARE[2], SQUARE[3], 0 )
    rect( model, "flagstones", ROAD[1], 0, TERRACE[0], TERRACE[1], 0 )
    rect( model, "setts", ALLEY[0], ALLEY[1], MID[1], MARKET[0], 0 )
    rect( model, "setts", ALLEY[0], ALLEY[1], TERRACE[1], MID[0], 0 )
    rect( model, "setts", -1250, -850, 350, 700, 0 )
    rect( model, "gravel", -1250, -650, -900, -450, 0 )
    area( model, -650, -170, -900, -400, 0, "lawn", [ ( -450, -370, -900, -400, "gravel" ), ( -370, -170, -680, -620, "gravel" ),
                                                      ( -650, -450, -830, -760, "gravel" ) ] )
    # The gardens, 48 down.
    area( model, ROAD[1], 0, GARDENS[0], GARDENS[1], GARDEN_Z, "lawn", [
        ( ROAD[1], -1450, -1450, -1260, "soil" ), ( -750, -250, -1450, -1260, "soil" ),
        ( ROAD[1], 0, -1260, -1200, "gravel" ), ( -1130, -1070, -1200, -1000, "gravel" ), ( -90, 0, -1200, -1000, "gravel" ),
        ( -210, -110, -1390, -1300, "soil" ), ( -210, -110, -1170, -1100, "soil" ) ] )
    rect( model, "setts", ROAD[0], ROAD[1], GARDENS[0], RAMP[0], GARDEN_Z )
    model.polygon( "setts", [ ( ROAD[0], RAMP[0], GARDEN_Z ), ( ROAD[1], RAMP[0], GARDEN_Z ), ( ROAD[1], RAMP[1], 0 ),
                              ( ROAD[0], RAMP[1], 0 ) ] )
    # Kerbs along the streets' edges aren't drawn; the collision under it all:
    model.collision_box( ( TOWN_WALL[0], TERRACE[0], -64 ), ( 0, NORTH_ROW[1], 0 ), STONE )
    model.collision_box( ( ROAD[1], SOUTH_EDGE, GARDEN_Z - 64 ), ( 0, GARDENS[1], GARDEN_Z ), DIRT )
    model.collision_box( ( TOWN_WALL[0], SOUTH_EDGE, GARDEN_Z - 64 ), ( ROAD[1], RAMP[0], GARDEN_Z ), STONE )
    model.hull( [ ( e, n, z ) for e in ROAD for n, z in ( ( RAMP[0], GARDEN_Z ), ( RAMP[1], 0 ), ( RAMP[0], GARDEN_Z - 64 ),
                                                              ( RAMP[1], GARDEN_Z - 64 ) ) ], STONE )


# ---------------------------------------------------------------------------------------------------------------------
# Street furniture

# Wires strung across the streets under the eaves, each with a dish lamp hung at its middle: ( e, n0, n1, z ), the
# wire's ends on the house fronts at n0 (facing +n) and n1 (facing -n), clear of their windows and cornices.
CABLES = ( ( -1700, MARKET[0], MARKET[1], 252 ), ( -1110, MARKET[0], MARKET[1], 252 ), ( -545, MARKET[0], MARKET[1], 252 ),
           ( -1700, MID[0], MID[1], 252 ), ( -730, MID[0], MID[1], 252 ) )


def street_cables( model ):
    """ CABLES: each wire's ends on wall plates with eye bolts, pulled down 12 to the dish lamp at its middle. Drawn
    only. """
    for e, n0, n1, z in CABLES:
        mid = np.array( ( e, ( n0 + n1 ) / 2, z - 12.0 ) )
        for n, out in ( ( n0, 1.0 ), ( n1, -1.0 ) ):
            model.box( ( e - 2.5, min( n, n + out ), z - 4 ), ( e + 2.5, max( n, n + out ), z + 4 ), "iron_black" )
            eye = np.array( ( e, n + out * 3.2, z ) )
            Detail.rod( model, ( e, n + out, z ), eye, 0.35, "iron_black", sides=6 )
            Detail.hoop( model, eye + ( 0, out * 0.9, 0 ), ( 0, 1.0, 0 ), ( 0, 0, 1.0 ), 0.9, 0.25, "iron_black", segments=8 )
            Detail.wire( model, eye + ( 0, out * 1.8, 0 ), mid, 1.5 )
        Detail.dish_lamp( model, mid )


def street_props( model, rng ):
    # Market Street's stalls, the lorry, crates and barrels.
    for e, canvas in ( ( -1700, "canvas_red" ), ( -1540, "canvas_plain" ), ( -1180, "canvas_green" ), ( -1020, "canvas_red" ),
                       ( -620, "canvas_plain" ), ( -460, "canvas_green" ) ):
        stall( model, ( e, 1410 ), 180, canvas, rng )
    for e, canvas in ( ( -1600, "canvas_green" ), ( -1180, "canvas_red" ), ( -560, "canvas_plain" ) ):
        stall( model, ( e, 1140 ), 0, canvas, rng )
    lorry( model, ( -900, 1290 ), 8 )
    crates( model, ( -1370, 1180 ), 10, rng )
    crates( model, ( -770, 1400 ), 180, rng )
    barrels( model, ( -1840 + 30, 1300 ), 3, rng )
    barrels( model, ( -260, 1160 ), 2, rng )
    for e in ( -1450, -760, -330 ):
        lamp_post( model, ( e, 1122 ) )
    # West Street.
    cart( model, ( -1620, 300 ), 176, load="crates" )
    model.box( ( -1500, -88, 0 ), ( -1410, -58, 30 ), { "default": "ashlar_grey", "+z": "water" }, STONE )
    for centre in ( ( -1780, 330 ), ( -1180, 330 ), ( -870, -80 ) ):
        planter( model, centre, seed=abs( int( centre[0] * 7 + centre[1] ) ) )
    crates( model, ( -800, 320 ), 0, rng )
    barrels( model, ( -1815, -55 ), 2, rng )
    for e in ( -1600, -940 ):
        lamp_post( model, ( e, -80 ) )
    for e in ( -1450, -850 ):
        lamp_post( model, ( e, 330 ) )
    # The alleys: crates, barrels and washing lines.
    crates( model, ( -1375, 470 ), 90, rng )
    barrels( model, ( -1355, 700 ), 2, rng )
    crates( model, ( -1375, -450 ), 90, rng )
    barrels( model, ( -1295, -590 ), 3, rng )
    for n in ( 640, 760, -260, -560 ):
        model.beam( ( ALLEY[0], n, 190 ), ( ALLEY[1], n, 186 ), ( 1, 1 ), "iron_black" )
        for k in range( 3 ):
            e = ALLEY[0] + 24 + k * 44 + rng.uniform( -6, 6 )
            paint = ( "canvas_plain", "canvas_red", "canvas_green" )[int( rng.integers( 0, 3 ) )]
            sheet = [ ( e, n, 188 ), ( e + 30, n, 188 ), ( e + 30, n, 140 + rng.uniform( 0, 20 ) ), ( e, n, 150 ) ]
            facing( model, paint, sheet, ( 0, 1, 0 ) )
            facing( model, paint, sheet, ( 0, -1, 0 ) )
    # The square: the café's tables and chairs under parasols, benches round the fountain, trees and lamps.
    for k, centre in enumerate( ( ( -600, -330 ), ( -520, -250 ), ( -600, -170 ), ( -520, -90 ) ) ):
        cafe = np.random.default_rng( 70 + k )
        top = Detail.bistro_table( model, centre )
        model.cylinder( centre, 13.8, 0, top, {}, sides=8, surface=METAL )
        Detail.parasol( model, centre, 84, 104, 52, turn=cafe.uniform( 0, math.pi / 4 ), pole_from=top )
        for a in ( 0.5, 2.6, 4.7 ):
            a += cafe.uniform( -0.25, 0.25 )
            e, n = centre[0] + 24 * math.cos( a ), centre[1] + 24 * math.sin( a )
            # Pulled out and turned a little, as they're left.
            Detail.bistro_chair( model, ( e, n ), math.degrees( a ) + 180 + cafe.uniform( -12, 12 ) )
    for yaw, centre in ( ( 90, ( -150, 130 ) ), ( 45, ( -110, 240 ) ), ( 135, ( -110, 20 ) ) ):
        bench( model, centre, yaw, 70 )
    tree( model, ( -560, 450 ), 0, 330, 120, seed=11, trunk_r=12 )
    for centre in ( ( -420, 330 ), ( -420, -150 ) ):
        lamp_post( model, centre )
    # The spawn road: a cart, crates, barrels and a trough.
    cart( model, ( -2160, 1330 ), 96, load="sacks" )
    crates( model, ( -2240, 690 ), 90, rng )
    crates( model, ( -2240, -560 ), 90, rng )
    barrels( model, ( -1890, 1060 ), 3, rng )
    barrels( model, ( -1890, -870 ), 2, rng )
    model.box( ( -2290, 330, 0 ), ( -2260, 430, 30 ), { "default": "ashlar_grey", "+z": "water" }, STONE )
    for n in ( -800, -350, 450, 1000, 1550 ):
        lamp_post( model, ( -1870, n ) )
    # Menu boards on the pavement: the café's onto the square, the Bakery's and the Inn's by their doors.
    Detail.sandwich_board( model, ( -628, -218 ), 0, "chalkboard_a" )
    Detail.sandwich_board( model, ( -1000, 1124 ), 90, "chalkboard_b" )
    Detail.sandwich_board( model, ( -972, -84 ), 90, "chalkboard_a" )
    street_cables( model )


def build_west( lights, rng ):
    _shops[0] = 0
    model = Model()
    ground( model )
    town_walls( model )
    west_houses( model, rng )
    bakery( model, lights, rng )
    inn( model, lights, rng )
    churchyard( model, rng )
    terrace( model, rng )
    gardens( model, rng )
    street_props( model, rng )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# The land beyond the town is Tools/belltower_vista.py's (its shape and model) and Tools/belltower_vista_paint.py's
# (its textures). Drawn only: no collision (nobody can get out there) and no shadows.

TOWN_RECT = ( TOWN_WALL[0], -TOWN_WALL[0], SOUTH_EDGE, NORTH_ROW[1] )    # e0, e1, n0, n1


# ---------------------------------------------------------------------------------------------------------------------
# Lights, and checking the spots against the collision

def mirrored_lights( lights ):
    """ The west half's lights for the east half: across the centre line, named for the east's buildings. """
    names = ( ( "Bakehouse", "Dairy Workroom" ), ( "Bakery", "Dairy" ), ( "Inn", "Tavern" ) )
    out = []
    for name, position, color, radius, shadows in lights:
        for old, new in names:
            if name.startswith( old ):
                name = new + name[len( old ):]
                break
        out.append( ( name, ( -position[0], position[1], position[2] ), color, radius, shadows ) )
    return out


def collision_aabbs( models ):
    """ Every collision shape's bounding box ( lo, hi ), in plan. """
    out = []
    for model in models:
        for centre, axes, size, _ in model.boxes:
            half = np.abs( np.asarray( axes, float ) ).T @ ( np.asarray( size, float ) / 2 )
            out.append( ( np.asarray( centre, float ) - half, np.asarray( centre, float ) + half ) )
        for points, _ in model.hulls:
            pts = np.asarray( points, float )
            out.append( ( pts.min( axis=0 ), pts.max( axis=0 ) ) )
    return out


def check_spots( aabbs, spots ):
    """ Every spot needs room for a player (32 x 32 x 72 over it) and a floor within 2 under it. Prints what's wrong
    and returns how many problems there were. Rotated shapes count by their bounding boxes, so this errs on the tight
    side. """
    lo = np.array( [ a[0] for a in aabbs ] )
    hi = np.array( [ a[1] for a in aabbs ] )
    problems = 0
    for name, ( e, n, z ) in spots:
        box_lo, box_hi = np.array( ( e - 16, n - 16, z + 1 ) ), np.array( ( e + 16, n + 16, z + 72 ) )
        blocked = np.all( ( lo < box_hi ) & ( hi > box_lo ), axis=1 )
        floor_under = ( ( lo[:, 0] <= e ) & ( hi[:, 0] >= e ) & ( lo[:, 1] <= n ) & ( hi[:, 1] >= n )
                        & ( hi[:, 2] >= z - 2 ) & ( hi[:, 2] <= z + 0.5 ) )
        if blocked.any():
            k = int( np.argmax( blocked ) )
            print( f"  {name} at {e:g},{n:g},{z:g}: blocked by {np.round( lo[k] ).tolist()}..{np.round( hi[k] ).tolist()}" )
            problems += 1
        if not floor_under.any():
            print( f"  {name} at {e:g},{n:g},{z:g}: no floor under it" )
            problems += 1
    return problems


# Walking: a 2.5D grid of the level tops of the collision (the floors), kept REACH_RADIUS from anything in the way, as the
# navmesh keeps its agents, with headroom for a crouch and joined where neighbouring floors are within a step. It stands
# in for the navmesh when the editor isn't free: it finds the areas nobody can walk to.

REACH_CELL = 8.0
REACH_BOUNDS = ( TOWN_WALL[0] - 20, -TOWN_WALL[0] + 20, SOUTH_EDGE - 14, NORTH_ROW[1] + 40 )    # e0, e1, n0, n1
REACH_RADIUS, REACH_STEP, REACH_HEAD = 16.0, 18.0, 64.0


def hull_2d( points ):
    """ The convex hull of plan points, counter-clockwise ( k, 2 ). """
    pts = sorted( set( ( round( float( x ), 4 ), round( float( y ), 4 ) ) for x, y in points ) )
    if len( pts ) < 3:
        return np.array( pts )

    def turn( o, a, b ):
        return ( a[0] - o[0] ) * ( b[1] - o[1] ) - ( a[1] - o[1] ) * ( b[0] - o[0] )
    lower, upper = [], []
    for p in pts:
        while len( lower ) >= 2 and turn( lower[-2], lower[-1], p ) <= 0:
            lower.pop()
        lower.append( p )
    for p in reversed( pts ):
        while len( upper ) >= 2 and turn( upper[-2], upper[-1], p ) <= 0:
            upper.pop()
        upper.append( p )
    return np.array( lower[:-1] + upper[:-1] )


def reach_cells( outline, grow, size ):
    """ The flat indices ( i * rows + j ) of the grid cells whose centres are in a convex outline grown by grow. """
    cols, rows = size
    e0, _, n0, _ = REACH_BOUNDS
    lo, hi = outline.min( axis=0 ) - grow, outline.max( axis=0 ) + grow
    i0, i1 = max( int( math.floor( ( lo[0] - e0 ) / REACH_CELL ) ), 0 ), min( int( math.ceil( ( hi[0] - e0 ) / REACH_CELL ) ), cols - 1 )
    j0, j1 = max( int( math.floor( ( lo[1] - n0 ) / REACH_CELL ) ), 0 ), min( int( math.ceil( ( hi[1] - n0 ) / REACH_CELL ) ), rows - 1 )
    if i1 < i0 or j1 < j0:
        return np.zeros( 0, int )
    xs = e0 + ( np.arange( i0, i1 + 1 ) + 0.5 ) * REACH_CELL
    ys = n0 + ( np.arange( j0, j1 + 1 ) + 0.5 ) * REACH_CELL
    gx, gy = np.meshgrid( xs, ys, indexing="ij" )
    inside = np.ones( gx.shape, bool )
    for k in range( len( outline ) if len( outline ) >= 3 else 0 ):
        a, b = outline[k], outline[( k + 1 ) % len( outline )]
        length = math.hypot( *( b - a ) )
        if length > 1e-9:
            inside &= ( gx - a[0] ) * ( b[1] - a[1] ) / length - ( gy - a[1] ) * ( b[0] - a[0] ) / length <= grow + 1e-6
    ii, jj = np.nonzero( inside )
    return ( ii + i0 ) * rows + ( jj + j0 )


def check_reach( models, spots, picture=None ):
    """ Every spot must be on the largest walkable area (the one both spawn roads are on). Prints the ones that aren't
    and returns how many; picture writes the grid: green walkable, blue upstairs, red and orange cut off. """
    e0, e1, n0, n1 = REACH_BOUNDS
    cols, rows = int( ( e1 - e0 ) / REACH_CELL ), int( ( n1 - n0 ) / REACH_CELL )
    in_way = [ [] for _ in range( cols * rows ) ]    # ( bottom, top ) of every shape within REACH_RADIUS
    floors = [ [] for _ in range( cols * rows ) ]    # tops of the level shapes over the cell

    def add( points, top, level ):
        z0, z1 = float( points[:, 2].min() ), float( points[:, 2].max() )
        if not level and z1 <= 1 and z0 <= GARDEN_Z - 60:
            return    # the spawn roads' ramps: floor (added below), never in the way
        for c in reach_cells( hull_2d( points[:, :2] ), REACH_RADIUS, ( cols, rows ) ):
            in_way[c].append( ( z0, z1 ) )
        if level:
            for c in reach_cells( hull_2d( top[:, :2] ), 0.0, ( cols, rows ) ):
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
    for i in range( cols ):
        e = e0 + ( i + 0.5 ) * REACH_CELL
        if -ROAD[1] <= abs( e ) <= -ROAD[0]:
            for j in range( rows ):
                n = n0 + ( j + 0.5 ) * REACH_CELL
                if RAMP[0] <= n <= RAMP[1]:
                    floors[i * rows + j].append( float( floor_level( e, n ) ) )

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
    main_area = max( sizes, key=sizes.get )

    problems = 0
    for name, ( e, n, z ) in spots:
        i0, j0 = int( ( e - e0 ) / REACH_CELL ), int( ( n - n0 ) / REACH_CELL )
        near = [ ( math.hypot( di, dj ), k ) for di in range( -5, 6 ) for dj in range( -5, 6 )
                 for k in by_cell.get( ( i0 + di ) * rows + j0 + dj, () ) if abs( node_z[k] - z ) <= 20 ]
        if not near:
            print( f"  {name} at {e:g},{n:g},{z:g}: nowhere to stand within 40" )
            problems += 1
        elif root( min( near )[1] ) != main_area:
            print( f"  {name} at {e:g},{n:g},{z:g}: cut off, on an area of {sizes[root( min( near )[1] )]} cells" )
            problems += 1

    if picture:
        image = np.zeros( ( rows, cols, 3 ), np.uint8 )
        for k, c in enumerate( node_cell ):
            i, j = divmod( c, rows )
            upstairs = node_z[k] > 100
            joined = root( k ) == main_area
            colour = ( ( 90, 140, 240 ) if joined else ( 240, 120, 40 ) ) if upstairs else ( ( 90, 200, 90 ) if joined else ( 220, 60, 60 ) )
            image[rows - 1 - j, i] = np.maximum( image[rows - 1 - j, i], colour )
        Image.fromarray( image ).resize( ( cols * 2, rows * 2 ), Image.NEAREST ).save( picture )
        print( f"wrote {picture}" )
    return problems


# ---------------------------------------------------------------------------------------------------------------------
# Previews: flat-shaded pictures drawn with the paints' mean colours (a numpy z-buffer), for checking without the editor

SUN = normalise( ( -0.739, -0.376, 0.559 ) )     # towards the scene's sun (SUN_PITCH 34, SUN_YAW -63), plan
SKY = ( np.array( ( 0.80, 0.85, 0.90 ) ), np.array( ( 0.40, 0.57, 0.82 ) ) )     # horizon, zenith
FOG = np.array( ( 0.72, 0.78, 0.86 ) )
_paint_colours = {}

# ( name, eye, target, horizontal field of view )
VIEWS = [
    ( "west_road", ( -2150, 500, 64 ), ( -1100, 1300, 60 ), 80 ),
    ( "square", ( -380, -330, 64 ), ( 0, 800, 260 ), 80 ),
    ( "terrace", ( -700, -950, 64 ), ( -300, -1450, -60 ), 80 ),
    ( "gardens", ( -640, -1230, 16 ), ( 0, -650, 150 ), 80 ),
    ( "council_hall", ( -380, 620, 232 ), ( 300, 1000, 200 ), 90 ),
    ( "market_street", ( -150, 1300, 64 ), ( -2000, 1275, 60 ), 80 ),
    ( "west_street", ( -1800, 125, 64 ), ( 1800, 125, 64 ), 80 ),
    ( "south_vista", ( 0, -1300, 16 ), ( 0, -9000, -1800 ), 80 ),
    ( "aerial", ( -3500, -3500, 2500 ), ( 0, 200, 0 ), 70 ),
]


def paint_colour( paint ):
    """ A paint's mean colour (0..1), from its texture (Belltower's own, where it has one). """
    if paint not in _paint_colours:
        path = Detail.material_colour_file( paint, K.ASSETS )
        if path is None or not path.exists():
            path = BT.OUT_DIR / f"{paint}_color.png"
        if path.exists():
            small = Image.open( path ).convert( "RGB" ).resize( ( 32, 32 ) )
            _paint_colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
        else:
            _paint_colours[paint] = np.array( ( 1.0, 0.0, 1.0 ) )
    return _paint_colours[paint]


def triangles( models ):
    """ Every polygon as triangles ( T, 3, 3 ), with their normals ( T, 3 ) and sunlit colours ( T, 3 ). """
    tris, normals, colours = [], [], []
    for model in models:
        for paint, items in model.polygons.items():
            base = paint_colour( paint )
            for points, normal in items:
                lit = base * ( 0.4 + 0.6 * max( 0.0, float( np.dot( normal, SUN ) ) ) )
                for k in range( 1, len( points ) - 1 ):
                    tris.append( ( points[0], points[k], points[k + 1] ) )
                    normals.append( normal )
                    colours.append( lit )
    return np.array( tris, float ), np.array( normals, float ), np.array( colours, float )


def rasterise( image, depth, screen, nearness, colours ):
    """ Draw triangles into image ( H, W, 3 ) over a depth buffer where larger is nearer: screen ( T, 3, 2 ) in
    pixels, nearness ( T, 3 ) (1 / depth, or height from above), colours ( T, 3 ). """
    height, width = depth.shape
    lo = np.floor( screen.min( axis=1 ) ).astype( int )
    hi = np.ceil( screen.max( axis=1 ) ).astype( int )
    for t in range( len( screen ) ):
        x0, y0 = max( lo[t, 0], 0 ), max( lo[t, 1], 0 )
        x1, y1 = min( hi[t, 0], width - 1 ), min( hi[t, 1], height - 1 )
        if x1 < x0 or y1 < y0:
            continue
        ( ax, ay ), ( bx, by ), ( cx, cy ) = screen[t]
        area = ( bx - ax ) * ( cy - ay ) - ( by - ay ) * ( cx - ax )
        if abs( area ) < 1e-9:
            continue
        xs = np.arange( x0, x1 + 1 ) + 0.5
        ys = ( np.arange( y0, y1 + 1 ) + 0.5 )[:, None]
        w0 = ( ( bx - xs ) * ( cy - ys ) - ( by - ys ) * ( cx - xs ) ) / area
        w1 = ( ( cx - xs ) * ( ay - ys ) - ( cy - ys ) * ( ax - xs ) ) / area
        w2 = 1.0 - w0 - w1
        inside = ( w0 >= -1e-6 ) & ( w1 >= -1e-6 ) & ( w2 >= -1e-6 )
        if not inside.any():
            continue
        za, zb, zc = nearness[t]
        z = w0 * za + w1 * zb + w2 * zc
        region = depth[y0:y1 + 1, x0:x1 + 1]
        nearer = inside & ( z > region )
        region[nearer] = z[nearer]
        image[y0:y1 + 1, x0:x1 + 1][nearer] = colours[t]


def clip_near( tri, near ):
    """ The part of a triangle ( 3, 3 ) in camera space in front of the near plane, as triangles. """
    points = []
    for k in range( 3 ):
        a, b = tri[k], tri[( k + 1 ) % 3]
        if a[2] >= near:
            points.append( a )
        if ( a[2] >= near ) != ( b[2] >= near ):
            points.append( a + ( near - a[2] ) / ( b[2] - a[2] ) * ( b - a ) )
    return [ np.array( ( points[0], points[k], points[k + 1] ) ) for k in range( 1, len( points ) - 1 ) ]


def perspective( tris, normals, colours, eye, target, size=( 960, 540 ), fov=80.0 ):
    """ A view from eye towards target (plan), fov degrees across, with the sky behind and fog as the scene's. """
    width, height = size
    eye, target = np.asarray( eye, float ), np.asarray( target, float )
    forward = normalise( target - eye )
    right = normalise( np.cross( forward, ( 0.0, 0.0, 1.0 ) ) )
    up = np.cross( right, forward )
    focal = ( width / 2 ) / math.tan( math.radians( fov ) / 2 )
    xs = ( np.arange( width ) + 0.5 - width / 2 ) / focal
    ys = ( height / 2 - np.arange( height ) - 0.5 ) / focal
    rays = forward + xs[None, :, None] * right + ys[:, None, None] * up
    elevation = rays[..., 2] / np.linalg.norm( rays, axis=2 )
    t = np.clip( elevation * 2.5, 0.0, 1.0 )[..., None]
    image = SKY[0] * ( 1 - t ) + SKY[1] * t
    depth = np.zeros( ( height, width ) )

    near = 2.0
    rel = tris - eye
    cam = np.stack( ( rel @ right, rel @ up, rel @ forward ), axis=-1 )
    keep = ( np.einsum( "ij,ij->i", normals, eye - tris[:, 0] ) > 0 ) & ( cam[:, :, 2].max( axis=1 ) > near )
    cam, cols = cam[keep], colours[keep]
    distance = np.linalg.norm( cam.mean( axis=1 ), axis=1 )
    fog = ( 0.75 * np.clip( ( distance - 2500.0 ) / 39500.0, 0.0, 1.0 ) ** 1.3 )[:, None]
    cols = cols * ( 1 - fog ) + FOG * fog
    whole = ( cam[:, :, 2] >= near ).all( axis=1 )
    pieces, piece_colours = [ cam[whole] ], [ cols[whole] ]
    for tri, col in zip( cam[~whole], cols[~whole] ):
        for part in clip_near( tri, near ):
            pieces.append( part[None] )
            piece_colours.append( col[None] )
    cam, cols = np.concatenate( pieces ), np.concatenate( piece_colours )
    screen = np.stack( ( width / 2 + focal * cam[:, :, 0] / cam[:, :, 2], height / 2 - focal * cam[:, :, 1] / cam[:, :, 2] ),
                       axis=-1 )
    on = ( ( screen[:, :, 0].max( axis=1 ) >= 0 ) & ( screen[:, :, 0].min( axis=1 ) < width )
           & ( screen[:, :, 1].max( axis=1 ) >= 0 ) & ( screen[:, :, 1].min( axis=1 ) < height ) )
    rasterise( image, depth, screen[on], 1.0 / cam[on][:, :, 2], cols[on] )
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


def top_down( tris, normals, colours, bounds, scale ):
    """ The town from straight above: bounds ( e0, e1, n0, n1 ), scale units a pixel. """
    e0, e1, n0, n1 = bounds
    width, height = int( ( e1 - e0 ) / scale ), int( ( n1 - n0 ) / scale )
    image = np.tile( np.array( ( 0.22, 0.24, 0.27 ) ), ( height, width, 1 ) )
    depth = np.full( ( height, width ), -1e9 )
    keep = ( normals[:, 2] > 0.02 ) & ( tris[:, :, 0].max( axis=1 ) > e0 ) & ( tris[:, :, 0].min( axis=1 ) < e1 ) \
        & ( tris[:, :, 1].max( axis=1 ) > n0 ) & ( tris[:, :, 1].min( axis=1 ) < n1 )
    t = tris[keep]
    screen = np.stack( ( ( t[:, :, 0] - e0 ) / scale, ( n1 - t[:, :, 1] ) / scale ), axis=-1 )
    rasterise( image, depth, screen, t[:, :, 2], colours[keep] )
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


def write_previews( out_dir, town ):
    out_dir = Path( out_dir )
    out_dir.mkdir( parents=True, exist_ok=True )
    tris, normals, colours = triangles( town )
    top_down( tris, normals, colours, ( -2600, 2600, -1650, 2050 ), 2.5 ).save( out_dir / "top.png" )
    print( f"wrote {out_dir / 'top.png'}" )
    for name, eye, target, fov in VIEWS:
        perspective( tris, normals, colours, eye, target, fov=fov ).save( out_dir / f"{name}.png" )
        print( f"wrote {out_dir / name}.png" )
    if not MAP_ART_FILE.exists():
        # A stand-in for the menus' map picture until one is captured in the engine.
        name, eye, target, fov = VIEWS[-1]
        MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
        perspective( tris, normals, colours, eye, target, size=( 1920, 1080 ), fov=fov ).save( MAP_ART_FILE )
        print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


# ---------------------------------------------------------------------------------------------------------------------
# The radar picture

MINIMAP_CENTRE = ( 0.0, 207.0 )      # plan ( e, n ) at the picture's centre: the Minimap Renderer's position
MINIMAP_SIZE = 5000.0
MINIMAP_PIXELS = 1024


def floor_level( e, n ):
    """ The walking level at plan points: the streets' 0, the gardens' -48, and the spawn roads' ramps and the terrace
    stairs between them. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    z = np.where( n < TERRACE[0], float( GARDEN_Z ), 0.0 )
    ramp = GARDEN_Z * np.clip( ( RAMP[1] - n ) / ( RAMP[1] - RAMP[0] ), 0.0, 1.0 )
    z = np.where( ( np.abs( e ) >= -ROAD[1] ) & ( n < RAMP[1] ), ramp, z )
    for ea, eb in TERRACE_STAIRS:
        for a, b in ( ( ea, eb ), ( -eb, -ea ) ):
            on = ( e >= a ) & ( e <= b ) & ( n >= STAIR_FOOT ) & ( n < TERRACE[0] )
            z = np.where( on, GARDEN_Z * ( TERRACE[0] - n ) / ( TERRACE[0] - STAIR_FOOT ), z )
    return z


def write_minimap( aabbs ):
    """ Where you can walk (grey, the gardens a touch darker), low cover (darker), buildings and high walls left
    clear, and a light line round the edges. North is up. """
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    grid_e, grid_n = np.meshgrid( cols, rows )
    level = floor_level( grid_e, grid_n )
    walk = np.zeros( ( px, px ), bool )
    low = np.zeros( ( px, px ), bool )
    tall = np.zeros( ( px, px ), bool )
    for lo, hi in aabbs:
        j0, j1 = max( int( math.floor( ( lo[0] - left ) / scale ) ), 0 ), min( int( math.ceil( ( hi[0] - left ) / scale ) ) - 1, px - 1 )
        i0, i1 = max( int( math.floor( ( top - hi[1] ) / scale ) ), 0 ), min( int( math.ceil( ( top - lo[1] ) / scale ) ) - 1, px - 1 )
        if j1 < j0 or i1 < i0:
            continue
        cell = ( slice( i0, i1 + 1 ), slice( j0, j1 + 1 ) )
        f = level[cell]
        walk[cell] |= ( hi[2] >= f - 6 ) & ( hi[2] <= f + 18 )
        if hi[2] <= 1 and lo[2] <= GARDEN_Z - 60:
            continue    # the ground under the streets and gardens, and the ramps: floor, never in the way
        blocks = ( lo[2] < f + 72 ) & ( hi[2] > f + 18 )
        low[cell] |= blocks & ( hi[2] < f + 100 )
        tall[cell] |= blocks & ( hi[2] >= f + 100 )
    ramps = ( np.abs( grid_e ) >= -ROAD[1] ) & ( np.abs( grid_e ) <= -ROAD[0] ) & ( grid_n >= RAMP[0] ) & ( grid_n <= RAMP[1] )
    walk |= ramps
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 96, 100, 235 )
    image[walk & ( grid_n < TERRACE[0] )] = ( 87, 90, 94, 235 )
    image[low] = ( 66, 68, 71, 235 )
    image[tall] = ( 0, 0, 0, 0 )
    shown = ( walk | low ) & ~tall
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
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( e, n, 0 ) for e in ( -2180, -2040, -1920 ) for n in ( -500, -150, 150, 500 ) ]
BLUE_SPAWNS = [ ( -e, n, z ) for e, n, z in RED_SPAWNS ]

DM_WEST = [ ( -2100, 900, 0 ), ( -2100, -600, 0 ), ( -1600, 1275, 0 ), ( -600, 1275, 0 ), ( -1300, 950, 0 ), ( -1000, 560, 0 ),
            ( -1150, 1040, 0 ), ( -1100, 200, 0 ), ( -300, 420, 0 ), ( -1040, -200, 0 ), ( -900, -700, 0 ), ( -420, -650, 0 ),
            ( -1100, -1240, GARDEN_Z ), ( -1600, -1230, GARDEN_Z ), ( -600, -950, 0 ) ]
DM_SPAWNS = DM_WEST + [ ( -e, n, z ) for e, n, z in DM_WEST ] + [ ( -250, 800, HALL_FLOOR ), ( 250, 800, HALL_FLOOR ),
                                                                  ( 0, -640, 0 ) ]

# Retakes: the planter and the defenders are Red Team (Terrorist), the attackers Blue Team (CounterTerrorist).
RETAKES = {
    "bombsite_a": { "planter": [ ( 1450, 1275, 0 ), ( 1500, 1350, 0 ) ],
                    "defender": [ ( 1150, 1040, 0 ), ( 1300, 950, 0 ), ( 300, 1350, 0 ), ( 1680, 1250, 0 ) ],
                    "attacker": [ ( 1600, 100, 0 ), ( 1750, 250, 0 ), ( 1550, 20, 0 ), ( 450, 200, 0 ), ( 450, 0, 0 ) ] },
    "bombsite_b": { "planter": [ ( 1050, -1235, GARDEN_Z ), ( 1150, -1300, GARDEN_Z ) ],
                    "defender": [ ( 900, -700, 0 ), ( 600, -950, 0 ), ( 1200, -950, 0 ), ( 1600, -1230, GARDEN_Z ) ],
                    "attacker": [ ( 2100, 900, 0 ), ( 1950, 1250, 0 ), ( 1200, 1300, 0 ), ( 600, 1275, 0 ), ( 2000, 700, 0 ) ] },
}

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 1250, 1750, 1100, 1450, 0 ),
               ( "bombsite_b", "Bomb Site B", 750, 1450, -1450, -1000, GARDEN_Z ) ]

DOMINATION = [ ( "A", ( -1200, 125, 0 ) ), ( "B", ( 0, -170, 0 ) ), ( "C", ( 1200, 125, 0 ) ) ]
HOT_ZONES = [ ( "Market", ( 0, 1150, 0 ) ), ( "Council Hall", ( 0, 700, HALL_FLOOR ) ), ( "Square", ( 0, -170, 0 ) ),
              ( "Gardens", ( 0, -1300, GARDEN_Z ) ), ( "West Street", ( -1200, 125, 0 ) ), ( "East Street", ( 1200, 125, 0 ) ) ]
# Cash Grab: ( name, the cash, where it's taken ). The cash sits 8 over the floor and the extraction point 32.
CASH_POINTS = [ ( "Market", ( 0, 1150, 0 ), ( 0, -1380, GARDEN_Z ) ),
                ( "Gardens", ( 0, -1300, GARDEN_Z ), ( 0, 1400, 0 ) ),
                ( "Square", ( 0, -170, 0 ), ( 0, 900, HALL_FLOOR ) ) ]

# Callouts for the location readout: ( name, e0, e1, n0, n1[, z0, z1] ), z -60..150 when left out. East ones come from
# EAST_CALLOUTS' mirror of the west's.
WEST_CALLOUTS = [
    ( "WEST MARKET", -1850, -300, 1100, 1450 ),
    ( "BAKERY ALLEY", -1400, -1250, 350, 1100 ), ( "INN ALLEY", -1400, -1250, -900, -100 ),
    ( "BAKERY", -1250, -850, 700, 1100 ), ( "BAKERY YARD", -1250, -850, 350, 700 ),
    ( "WEST STREET", -1850, -650, -100, 350 ), ( "INN", -1250, -800, -450, -100, -60, 300 ),
    ( "BEER GARDEN", -1250, -650, -900, -450 ), ( "WEST CHURCHYARD", -650, -170, -900, -400 ),
    ( "WEST GARDENS", -1850, -250, -1466, -1000, -120, 40 ),
]
EAST_NAMES = { "WEST MARKET": "EAST MARKET", "BAKERY ALLEY": "DAIRY ALLEY", "INN ALLEY": "TAVERN ALLEY", "BAKERY": "DAIRY",
               "BAKERY YARD": "DAIRY YARD", "WEST STREET": "EAST STREET", "INN": "TAVERN", "BEER GARDEN": "TAVERN GARDEN",
               "WEST CHURCHYARD": "EAST CHURCHYARD", "WEST GARDENS": "EAST GARDENS" }
CALLOUTS = [
    ( "RED SPAWN", -2380, -1850, -1000, 1800, -60, 150 ), ( "WEST RAMP", -2380, -1850, -1466, -1000, -120, 150 ),
    ( "BLUE SPAWN", 1850, 2380, -1000, 1800, -60, 150 ), ( "EAST RAMP", 1850, 2380, -1466, -1000, -120, 150 ),
    ( "MARKET CROSS", -300, 300, 1100, 1450 ),
    ( "TOWN HALL", -450, 450, 560, 1100, -60, 150 ), ( "COUNCIL HALL", -450, 450, 560, 1100, 150, 360 ),
    ( "BALCONY", -240, 240, 500, 560, 150, 360 ), ( "SQUARE", -650, 650, -400, 550 ),
    ( "CHURCH", -170, 170, -900, -400, -60, 360 ), ( "TERRACE", -1850, 1850, -1000, -900, -40, 150 ),
    ( "WELL", -250, 250, -1466, -1000, -120, 40 ),
    # The east's own: A site takes Market Street's east end, B site the east gardens' far end.
    ( "EAST MARKET", 300, 1250, 1100, 1450 ), ( "A SITE", 1250, 1850, 1100, 1450 ),
    ( "EAST GARDENS", 250, 750, -1466, -1000, -120, 40 ), ( "B SITE", 750, 1850, -1466, -1000, -120, 40 ),
] + WEST_CALLOUTS + [ ( EAST_NAMES[c[0]], -c[2], -c[1], *c[3:] ) for c in WEST_CALLOUTS
                      if EAST_NAMES[c[0]] not in ( "EAST MARKET", "EAST GARDENS" ) ]


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
# The scene

CALLOUT_COLOUR = "0.51056,0.70698,0.49653,1"


def plan_box( e0, e1, n0, n1, z0, z1 ):
    """ A plan box as a world centre and a BoxCollider scale ( north, west, up ). """
    return K.to_world( ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, ( z0 + z1 ) / 2 ) ), ( n1 - n0, e1 - e0, z1 - z0 )


def box_collider( key, scale, trigger=True, static=True, center=( 0, 0, 0 ) ):
    return K.component( ids, "Sandbox.BoxCollider", key, Center=K.vec( center ), ColliderFlags=0, Elasticity=None,
                        Friction=None, IsTrigger=trigger, RollingResistance=None, Scale=K.vec( scale ), Static=static,
                        Surface=None, SurfaceVelocity="0,0,0" )


def ref( go_key, component_key, component_type ):
    """ A scene reference to a component. """
    return { "_type": "component", "component_id": ids( component_key ), "go": ids( go_key ), "component_type": component_type }


def zone_object( name, key, box, color, display, components=(), tags="zone" ):
    """ A trigger box with a Zone (a callout, a buy zone, the play area) and any other components. """
    centre, scale = plan_box( *box )
    return K.game_object( ids, name, key, centre, tags=tags, components=[
        *components,
        K.component( ids, "Zone", f"{key}/zone", Color=color, DisplayName=display ),
        box_collider( f"{key}/box", scale ),
    ] )


def spawn_object( name, key, position, team, tags="" ):
    """ A TeamSpawnPoint facing the town's middle ( 0, 200 ). """
    yaw = K.plan_yaw( ( -position[0], 200 - position[1] ) )
    return K.game_object( ids, name, key, K.to_world( position ), K.yaw_rotation( yaw ), tags=tags, components=[
        K.component( ids, "TeamSpawnPoint", f"{key}/point", Team=team ) ] )


def mode_group( name, key, modes, children, inverse=False ):
    """ Objects that only exist in these modes (GameModeObject, by the modes' titles), or with inverse, in every mode
    but these. """
    return K.game_object( ids, name, key, components=[
        K.component( ids, "Facepunch.GameModeObject", f"{key}/modes", GameModes=list( modes ), Inverse=inverse ) ],
        children=children )


def cash_point( name, key, cash, extract ):
    """ Cash Grab's cash point at cash (floor, plan) and its extraction point at extract, as Refinery's are made. """
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


# The sun (write_scene), and towards it in plan for the previews' shading (SUN).
SUN_PITCH, SUN_YAW = 34.0, -63.0

# The sky (Tools/belltower_sky.py) and the exposure it's made for (its DESIGN_EXPOSURE). The fog is drawn over the sky
# too (sky.shader takes the gradient fog), so its colour is the sky's 2 degrees up (belltower_sky.reference_sky), which
# hazes the vista's hills into the horizon instead of greying the sky.
SKY_MATERIAL = "materials/belltower/sky/belltower_sky.vmat"
SKY_EXPOSURE = 2
FOG_COLOUR = "0.351,0.594,1.048"


def look_object():
    """ The map's grade, an infinite post-process volume over the player camera's own effects. Only the effects the camera
    doesn't use for gameplay go in it (a volume's effect replaces the camera's of the same type): ambient occlusion for
    the contact shadow in corners, under eaves and round the cobbles, a warm white balance, and a light vignette.

    And the exposure. The player camera's auto exposure runs from 1 to 2, and in a sunlit street it sits at 1, where the
    sunlit plaster comes out a dull mid-grey and the sky dark. The materials and the sky (belltower_sky.DESIGN_EXPOSURE)
    are made for 2, a bright summer day's: the town's auto exposure runs from 2 to 3, so the shade of the church and the
    houses can open up a little. """
    return K.game_object( ids, "Look", "look", components=[
        K.component( ids, "Sandbox.PostProcessVolume", "look/volume", BlendDistance=50, BlendWeight=1, EditorPreview=True,
                     Priority=0, SceneVolume={ "Type": "Infinite", "Sphere": { "Center": "0,0,0", "Radius": 10 },
                                               "Box": { "Mins": "-50,-50,-50", "Maxs": "50,50,50" },
                                               "Capsule": { "CenterA": "0,0,10", "CenterB": "0,0,90", "Radius": 10 } } ),
        K.component( ids, "Sandbox.AmbientOcclusion", "look/ao", **{ "__version": 1 }, FalloffRange=1, Intensity=0.6, Radius=96,
                     ThinCompensation=5 ),
        K.component( ids, "Sandbox.ColorGrading", "look/grade", GradingMethod="TemperatureControl", ColorTempK=5900,
                     BlendFactor=0.45, ColorSpace="None", LookupTexture=None ),
        K.component( ids, "Sandbox.Vignette", "look/vignette", Center="0.5,0.5", Color="0,0,0,1", Intensity=0.22, Roundness=1,
                     Smoothness=1 ),
        K.component( ids, "Sandbox.Tonemapping", "look/tonemap", **{ "__version": 3 }, AutoExposureEnabled=True,
                     ExposureCompensation=0, ExposureMethod="RGB", MinimumExposure=SKY_EXPOSURE, MaximumExposure=3,
                     Mode="ACES", Rate=1 ),
    ] )


# Under the lowest land, so nothing thrown over the walls falls for ever.
CATCH_FLOOR_Z = -6500


def write_scene( lights, models ):
    foliage = []
    for region, model in models:
        for index, prop in enumerate( model.props ):
            key = f"foliage/{region}/{index}"
            foliage.append( K.game_object( ids, prop["name"], key, K.to_world( prop["position"] ),
                K.yaw_rotation( prop["yaw"] ), scale=K.vec( prop["scale"] ), components=[
                    K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model=prop["path"],
                                 RenderType="On", Tint="1,1,1,1" ) ] ) )
    town = K.game_object( ids, "Town", "town", children=[
        model_object( "Centre", "town/centre", "belltower_centre" ),
        model_object( "West Half", "town/west", "belltower_west" ),
        model_object( "East Half", "town/east", "belltower_east" ),
        model_object( "Vista", "town/vista", "belltower_vista", collide=False, shadows=False ),
        model_object( "Vista Props", "town/vista_props", VistaProps.NAME, collide=False, shadows=False ),
    ] )
    light_objects = [
        K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1, FogMode="Enabled", FogStrength=1,
                         LightColor=color, Radius=radius, Shadows=shadows ) ] )
        for name, position, color, radius, shadows in lights ]

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
        zone_object( "buyzone_t", "buy/t", ( ROAD[0], ROAD[1], -800, 1000, 0, 266 ), "1,0.18,0.2,1", "Red Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/t/zone_buy", Team="Terrorist" ) ] ),
        zone_object( "buyzone_ct", "buy/ct", ( -ROAD[1], -ROAD[0], -800, 1000, 0, 266 ), "0,0.41569,1,1", "Blue Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/ct/zone_buy", Team="CounterTerrorist" ) ] ),
    ]

    callouts = []
    for c in CALLOUTS:
        name, e0, e1, n0, n1 = c[:5]
        z0, z1 = c[5:7] if len( c ) > 5 else ( -60, 150 )
        callouts.append( zone_object( name, f"callout/{name}", ( e0, e1, n0, n1, z0, z1 ), CALLOUT_COLOUR, name,
                                      [ K.component( ids, "Facepunch.MapLocation", f"callout/{name}/location" ) ] ) )

    play_centre, play_scale = plan_box( TOWN_RECT[0] - 20, TOWN_RECT[1] + 20, 207 - 1700, 207 + 1700, -300, 1300 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
    # Over the south parapet, so nobody jumps down the drop; and far below, a floor that catches whatever is thrown
    # out over the walls.
    clip_centre, clip_scale = plan_box( TOWN_RECT[0], TOWN_RECT[1], SOUTH_EDGE, SOUTH_EDGE + 10, -12, 400 )
    clip = K.game_object( ids, "Player Clip", "clip", clip_centre, tags="playerclip", components=[
        box_collider( "clip/box", clip_scale, trigger=False ) ] )
    catch = K.game_object( ids, "Catch Floor", "catch", ( 200, 0, CATCH_FLOOR_Z ), components=[
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

    objects = [
        K.game_object( ids, "Scene Information", "info", components=[
            K.component( ids, "Sandbox.SceneInformation", "info/scene", Title=TITLE, Author=None, Changes="",
                         Description="A hill town's market square: three lanes between the spawn roads, the Town Hall "
                                     "and its belltower, the church, and the gardens below the terrace.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # A late-afternoon sun from the west-south-west, 34 degrees up: it lights Market Street's north row and the west
        # faces, and throws long shadows across the streets, as the light does in a hill town before evening.
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
                         EndDistance=95000, FalloffExponent=1.5, Height=9000, VerticalFalloffExponent=1.2 ),
        ] ),
        look_object(),
        town,
        K.game_object( ids, "Trees and planting", "foliage", children=foliage ),
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        # Free-for-all modes spawn at every active spawn point, so the spawn roads' team spawns are left out of them.
        mode_group( "Team Spawns", "spawns", ( "Deathmatch", "Gun Game" ), team_spawns, inverse=True ),
        mode_group( "Deathmatch Spawns", "spawns/dm", ( "Deathmatch", "Gun Game" ), dm_spawns ),
        mode_group( "Retakes Spawns", "spawns/retakes", ( "Retakes", ), retakes_spawns ),
        K.game_object( ids, "Bomb Sites", "sites", children=bomb_sites ),
        K.game_object( ids, "Buy Zones", "buy", children=buy_zones ),
        K.game_object( ids, "Callouts", "callouts", children=callouts ),
        play_area,
        clip,
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
                "Bounds": { "Mins": K.vec( K.to_world( ( TOWN_RECT[1] + 40, SOUTH_EDGE - 84, -150 ) ) ),
                            "Maxs": K.vec( K.to_world( ( TOWN_RECT[0] - 40, 1950, 1250 ) ) ) },
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

    centre_lights, west_lights = [], []
    centre = build_centre( centre_lights )
    west = build_west( west_lights, np.random.default_rng( 2024 ) )
    east = west.mirrored( EAST_PAINTS )
    models = [("centre", centre), ("west", west), ("east", east)]
    for name, model in models:
        Detail.configure( model, render=( name != "vista" ) )
    lights = centre_lights + west_lights + mirrored_lights( west_lights )

    for name, model in ( ( "belltower_centre", centre ), ( "belltower_west", west ), ( "belltower_east", east ) ):
        count = K.write_model( OUT_DIR, RESOURCE_DIR, name, model )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
    # The land round the town: Tools/belltower_vista.py's shape, painted by Tools/belltower_vista_paint.py.
    count, lowest = Vista.write_land( OUT_DIR, RESOURCE_DIR )
    print( f"{Vista.LAND_NAME}: {count} triangles, lowest at {lowest:.0f}" )
    # Its buildings and trees (Tools/belltower_vista_props.py). The painter grounds them: their yards, roads and shadows.
    print( f"{VistaProps.NAME}: {VistaProps.write( OUT_DIR, RESOURCE_DIR )} triangles" )
    assert lowest > CATCH_FLOOR_Z, "the land goes below the catch floor"
    painted = { paint for model in ( centre, west, east ) for paint in model.polygons }
    missing = sorted( p for p in painted if p not in Detail.MATERIALS and not ( BT.OUT_DIR / f"{p}_color.png" ).exists() )
    if missing:
        print( f"paints with no material: {', '.join( missing )}" )

    aabbs = collision_aabbs( [ centre, west, east ] )
    print( "checking spots:" )
    problems = check_spots( aabbs, all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    if args.preview:
        Path( args.preview ).mkdir( parents=True, exist_ok=True )
    cut_off = check_reach( [ centre, west, east ], all_spots(), Path( args.preview ) / "reach.png" if args.preview else None )
    print( f"  {cut_off} spot(s) cut off from the spawns" )

    if not args.no_scene:
        write_minimap( aabbs )
        write_scene( lights, models )
    if args.preview:
        write_previews( args.preview, [ centre, west, east ] )
        Vista.write_land_previews( Path( args.preview ) / "vista" )


if __name__ == "__main__":
    main()
