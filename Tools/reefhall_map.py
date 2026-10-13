"""
Reef Hall, a multiplayer map: a public aquarium after hours, built by script out of boxes and polygons with
Tools/map_kit.py and painted with Tools/reefhall_materials.py's materials. Its rooms follow the five reference pictures
the user gave (2026-10-01): the rotunda round its central tank, the entrance lobby, the control room behind the big
panoramic tank, the filter hall and the glass tunnel. Collision is the same boxes and hulls, so what you see is what
stops players, bots and bullets.

    python Tools/reefhall_map.py [--preview <dir>] [--no-scene]

Red Team (Team.Terrorist) spawns in the lobby (west), Blue Team (Team.CounterTerrorist) in the control room (east).
Three lanes run between them:

- Middle: the West and East Galleries (corridors lined with small tanks) into the Rotunda, round its central tank. The
  Rotunda's ring balcony (L1, z 208) is reached by two curved stairs and by the upper galleries, the bridges from the
  lobby's and the control room's upper floors.
- North: the Filter Hall, with its two glass filter columns, the catwalk along its north tank wall and the mezzanine in
  its south-east corner. Bomb site A is its east half.
- South: the Tunnel Hall, a glass barrel vault under a tank, with the sunken aisle (z -40) between raised side aisles.
  Bomb site B is its east half.
- Between: the Rotunda's north and south passages, and the service corridors (NW, SW, NE, SE) from the lobby and the
  control room to the halls.

- Writes the models to Assets/models/maps/reefhall/ (one per room, and the tanks' insides, which have no collision),
  the tanks' glass materials to Assets/materials/reefhall/rh_tank_glass_<tank>.vmat (each tank's water falls off from its
  own surface), the scene to Assets/scenes/maps/ReefHall/reefhall.scene and the radar picture to
  Assets/ui/minimaps/minimap_reefhall.png. The scene is written whole every run: edit the layout here, not in the editor.
- Every run checks each spawn, objective and cash point against the collision (room for a player, a floor under it, and
  a way to walk there from both spawns), as Tools/belltower_map.py does, and that no Retakes Red spawn can see a Blue
  one (railhead_map's check_retakes_sight).
- Plan coordinates: e east, n north, z up, in inches (map_kit's docstring has the world axes). The ground floor is z 0,
  the upper floors (L1) are at z 208, the tunnel's aisle at -40.
- Tank glass is 8 thick with the "glass" surface (3 penetrable), so it stops bullets and players, and bots can't see
  through it (the map model isn't tagged glass). Railings' glass panels are 1 thick, so rounds go through them.
- Doorways have no doors: bots can't open them. The lobby's glass entrance doors are shut for good, with a closed
  gallery behind them that's only there to be seen through the glass.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import building_textures as BT
import map_kit as K
import reefhall_materials as RM
from map_kit import Model, normalise

TITLE = "Reef Hall"
OUT_DIR = K.ASSETS / "models" / "maps" / "reefhall"
RESOURCE_DIR = "models/maps/reefhall"
SCENE_FILE = K.ASSETS / "scenes" / "maps" / "ReefHall" / "reefhall.scene"
MINIMAP_FILE = K.ASSETS / "ui" / "minimaps" / "minimap_reefhall.png"
MINIMAP_PATH = "ui/minimaps/minimap_reefhall.png"
MAP_ART_FILE = K.ASSETS / "ui" / "maps" / "reefhall.png"
MAP_ART_PATH = "ui/maps/reefhall.png"
ids = K.SceneIds( "3b7c19e2-6d4a-4f85-9c21-a8e05f4d7b93" )

# Surfaces (s&box's core .surface files)
STONE, METAL, SHEET, GLASS, WOOD, FABRIC, TILE = "default", "metal", "metal.sheet", "glass", "wood", "fabric", "ceramic"

# Levels
L1 = 208.0          # the upper floors' top
SLAB = 12.0
CORRIDOR_H = 180.0  # a corridor's ceiling
NAVE_Z = -40.0      # the tunnel's sunken aisle

# The tanks: name -> ( water surface z, how deep its light falls off, the longest path through it )
TANKS = {
    "rotunda": ( 540.0, 600.0, 520.0 ),
    "rotunda_ring": ( 540.0, 450.0, 200.0 ),
    "alcove": ( 190.0, 240.0, 120.0 ),
    "gallery": ( 175.0, 240.0, 140.0 ),
    "aisle": ( 220.0, 260.0, 220.0 ),
    "lobby": ( 610.0, 650.0, 260.0 ),
    "lobby_column": ( 320.0, 400.0, 260.0 ),
    "control": ( 470.0, 600.0, 700.0 ),
    "filter": ( 420.0, 450.0, 260.0 ),
    "filter_column": ( 370.0, 350.0, 280.0 ),
    "tunnel": ( 780.0, 800.0, 700.0 ),
    "display": ( 120.0, 150.0, 90.0 ),
}


def tank_paint( tank ):
    return f"rh_tank_glass_{tank}"


def configure( model ):
    """ Reef Hall's own materials, at their own tile sizes. """
    for paint, ( _, units ) in RM.paints().items():
        model.material_overrides[paint] = RM.material_path( paint )
        model.tile_overrides[paint] = units
    for tank in TANKS:
        model.material_overrides[tank_paint( tank )] = RM.material_path( tank_paint( tank ) )
        model.tile_overrides[tank_paint( tank )] = 64.0
    model.grain_paints.update( ( "rh_pipe", "rh_pipe_dark", "rh_kelp" ) )


BT.DECALS.update( RM.DECALS )


def write_tank_materials():
    for tank, ( surface, deep, longest ) in TANKS.items():
        text = RM.tank_glass_vmat( surface_z=surface, deep_range=deep, max_water=longest,
                                   shafts=0.8 if tank in ( "rotunda", "control", "tunnel", "lobby" ) else 0.5 )
        K.write_text( RM.OUT_DIR / f"{tank_paint( tank )}.vmat", text )


# ---------------------------------------------------------------------------------------------------------------------
# Drawing helpers

def unit2( v ):
    v = np.asarray( v, float )[:2]
    return v / np.linalg.norm( v )


def polar( angle_deg, r, centre=( 0.0, 0.0 ) ):
    a = math.radians( angle_deg )
    return np.array( ( centre[0] + r * math.cos( a ), centre[1] + r * math.sin( a ) ) )


def facing( model, paint, points, towards ):
    """ A polygon wound to face towards (a plan vector). A paint of None draws nothing. """
    if paint is None:
        return
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
    model.polygon( paint, pts )


def quad_hull( model, points, surface ):
    model.hull( [ tuple( p ) for p in points ], surface )


class Frame:
    """ A local frame on the plan: u along, w across (towards the front), z up. """

    def __init__( self, origin, along, front=None ):
        self.o = np.asarray( origin, float )[:2]
        self.d = unit2( along )
        self.f = unit2( front ) if front is not None else np.array( ( -self.d[1], self.d[0] ) )

    def p( self, u, w, z ):
        xy = self.o + self.d * u + self.f * w
        return np.array( ( xy[0], xy[1], z ) )

    def vec( self, du, dw, dz ):
        xy = self.d * du + self.f * dw
        return np.array( ( xy[0], xy[1], dz ) )


ROLE_DIRS = { "right": ( 1, 0, 0 ), "left": ( -1, 0, 0 ), "front": ( 0, 1, 0 ), "back": ( 0, -1, 0 ),
              "top": ( 0, 0, 1 ), "bottom": ( 0, 0, -1 ) }


def fbox( model, fr, u0, u1, w0, w1, z0, z1, paints, surface=None, skip=() ):
    """ A box in a frame: paints one paint or { role: paint } with 'default' (roles: front +w, back -w, left -u,
    right +u, top, bottom). """
    if u1 - u0 < 1e-6 or w1 - w0 < 1e-6 or z1 - z0 < 1e-6:
        return
    c = lambda a, b, z: fr.p( a, b, z )
    faces = {
        "right": [ c( u1, w0, z0 ), c( u1, w1, z0 ), c( u1, w1, z1 ), c( u1, w0, z1 ) ],
        "left": [ c( u0, w0, z0 ), c( u0, w1, z0 ), c( u0, w1, z1 ), c( u0, w0, z1 ) ],
        "front": [ c( u0, w1, z0 ), c( u1, w1, z0 ), c( u1, w1, z1 ), c( u0, w1, z1 ) ],
        "back": [ c( u0, w0, z0 ), c( u1, w0, z0 ), c( u1, w0, z1 ), c( u0, w0, z1 ) ],
        "top": [ c( u0, w0, z1 ), c( u1, w0, z1 ), c( u1, w1, z1 ), c( u0, w1, z1 ) ],
        "bottom": [ c( u0, w0, z0 ), c( u1, w0, z0 ), c( u1, w1, z0 ), c( u0, w1, z0 ) ],
    }
    for role, pts in faces.items():
        if role in skip:
            continue
        paint = paints.get( role, paints.get( "default" ) ) if isinstance( paints, dict ) else paints
        if paint:
            facing( model, paint, pts, fr.vec( *ROLE_DIRS[role] ) )
    if surface:
        x = np.array( ( *fr.d, 0.0 ) )
        z = np.array( ( 0.0, 0.0, 1.0 ) )
        y = np.cross( z, x )
        centre = fr.p( ( u0 + u1 ) / 2, ( w0 + w1 ) / 2, ( z0 + z1 ) / 2 )
        model.boxes.append( ( centre, ( tuple( x ), tuple( y ), tuple( z ) ), np.array( ( u1 - u0, w1 - w0, z1 - z0 ) ),
                              surface ) )


def seg_arch( u0, u1, crown, rise, steps ):
    """ Points ( u, z ) along a segmental arch from u0 to u1 whose crown is at crown, rise above its springs. """
    s = ( u1 - u0 ) / 2
    radius = ( s * s + rise * rise ) / ( 2 * rise )
    cz = crown - radius
    mid = ( u0 + u1 ) / 2
    half = math.asin( s / radius )
    return [ ( mid + radius * math.sin( -half + 2 * half * k / steps ), cz + radius * math.cos( -half + 2 * half * k / steps ) )
             for k in range( steps + 1 ) ]


class Hole:
    """ An opening in a frame wall: u0..u1, z0..z1. rise > 0 gives it a segmental arch head (its crown at z1). glass is a
    tank's name: a pane of its glass in the opening, set back glass_w from the front. frame paints a steel surround. """

    def __init__( self, u0, u1, z0, z1, rise=0.0, glass=None, glass_w=-6.0, frame=None, sill=None ):
        self.u0, self.u1, self.z0, self.z1, self.rise = u0, u1, z0, z1, rise
        self.glass, self.glass_w, self.frame, self.sill = glass, glass_w, frame, sill

    @property
    def spring( self ):
        return self.z1 - self.rise


def fwall( model, fr, u0, u1, thick, z0, z1, holes, paints, surface=STONE, ends=True, top=True ):
    """ A straight wall in a frame from u0 to u1, its front face at w 0 and its back at -thick, with holes. paints
    { 'front', 'back', 'edge' } (edge: the reveals, the top and the ends). """
    front, back = paints.get( "front" ), paints.get( "back" )
    edge = paints.get( "edge", front )
    holes = sorted( holes, key=lambda h: h.u0 )
    w0, w1 = -thick, 0.0
    cuts = [ u0 ] + [ x for h in holes for x in ( h.u0, h.u1 ) ] + [ u1 ]
    roles = { "front": front, "back": back, "top": edge if top else None, "bottom": None,
              "left": None, "right": None }
    for k in range( 0, len( cuts ), 2 ):
        a, b = cuts[k], cuts[k + 1]
        sides = dict( roles )
        if ends and abs( a - u0 ) < 1e-6:
            sides["left"] = edge
        if ends and abs( b - u1 ) < 1e-6:
            sides["right"] = edge
        fbox( model, fr, a, b, w0, w1, z0, z1, sides, surface )
    for h in holes:
        if h.z0 > z0:
            fbox( model, fr, h.u0, h.u1, w0, w1, z0, h.z0, { "front": front, "back": back, "top": h.sill or edge }, surface )
        if h.z1 < z1:
            fbox( model, fr, h.u0, h.u1, w0, w1, h.z1, z1, { "front": front, "back": back, "top": edge if top else None,
                                                                  "bottom": None if h.rise else edge }, surface )
        head = h.spring
        for u, d in ( ( h.u0, ( 1, 0, 0 ) ), ( h.u1, ( -1, 0, 0 ) ) ):
            facing( model, edge, [ fr.p( u, w0, h.z0 ), fr.p( u, w1, h.z0 ), fr.p( u, w1, head ), fr.p( u, w0, head ) ],
                    fr.vec( *d ) )
        if h.rise:
            pts = seg_arch( h.u0, h.u1, h.z1, h.rise, 10 )
            for ( ua, za ), ( ub, zb ) in zip( pts, pts[1:] ):
                for w, d in ( ( w1, 1 ), ( w0, -1 ) ):
                    poly = [ fr.p( ua, w, za ), fr.p( ub, w, zb ), fr.p( ub, w, h.z1 ), fr.p( ua, w, h.z1 ) ]
                    if za < h.z1 - 0.01 or zb < h.z1 - 0.01:
                        facing( model, front if d > 0 else back, poly, fr.vec( 0, d, 0 ) )
                soffit = [ fr.p( ua, w0, za ), fr.p( ub, w0, zb ), fr.p( ub, w1, zb ), fr.p( ua, w1, za ) ]
                mid_u, mid_z = ( ua + ub ) / 2, ( za + zb ) / 2
                facing( model, edge, soffit, fr.vec( ( h.u0 + h.u1 ) / 2 - mid_u, 0, ( h.z1 - h.rise * 3 ) - mid_z ) )
                if surface and ( za < h.z1 - 0.5 or zb < h.z1 - 0.5 ):
                    quad_hull( model, [ fr.p( ua, w, za ) for w in ( w0, w1 ) ] + [ fr.p( ub, w, zb ) for w in ( w0, w1 ) ]
                               + [ fr.p( u, w, h.z1 ) for u in ( ua, ub ) for w in ( w0, w1 ) ], surface )
        if h.frame:
            surround( model, fr, h, w1, h.frame )
        if h.glass:
            pane( model, fr, h.u0, h.u1, h.z0, head if not h.rise else h.z1, h.glass, h.glass_w, h.rise )


def surround( model, fr, h, w_face, paint, width=7.0, proud=2.5 ):
    """ A steel frame round a hole, standing proud of the wall's front. """
    w0, w1 = w_face - 0.01, w_face + proud
    top = h.spring
    fbox( model, fr, h.u0 - width, h.u0, w0, w1, h.z0, top + ( 0 if h.rise else width ), paint )
    fbox( model, fr, h.u1, h.u1 + width, w0, w1, h.z0, top + ( 0 if h.rise else width ), paint )
    if not h.rise:
        fbox( model, fr, h.u0, h.u1, w0, w1, h.z1, h.z1 + width, paint )
        if h.glass:
            fbox( model, fr, h.u0 - width, h.u1 + width, w0, w1 + 1.5, h.z0 - width, h.z0, paint )
    else:
        pts = seg_arch( h.u0, h.u1, h.z1, h.rise, 10 )
        mid = ( h.u0 + h.u1 ) / 2
        cz = h.z1 - ( ( ( h.u1 - h.u0 ) / 2 ) ** 2 + h.rise ** 2 ) / ( 2 * h.rise )
        for ( ua, za ), ( ub, zb ) in zip( pts, pts[1:] ):
            def out( u, z ):
                v = np.array( ( u - mid, z - cz ) )
                v /= np.linalg.norm( v )
                return u + v[0] * width, z + v[1] * width
            oa, ob = out( ua, za ), out( ub, zb )
            for w, d in ( ( w1, 1 ), ):
                facing( model, paint, [ fr.p( ua, w, za ), fr.p( ub, w, zb ), fr.p( ob[0], w, ob[1] ), fr.p( oa[0], w, oa[1] ) ],
                        fr.vec( 0, d, 0 ) )
            facing( model, paint, [ fr.p( oa[0], w0, oa[1] ), fr.p( ob[0], w0, ob[1] ), fr.p( ob[0], w1, ob[1] ), fr.p( oa[0], w1, oa[1] ) ],
                    fr.vec( ( oa[0] + ob[0] ) / 2 - mid, 0, ( oa[1] + ob[1] ) / 2 - cz ) )


def pane( model, fr, u0, u1, z0, z1, tank, w=-6.0, rise=0.0, thick=8.0, surface=GLASS ):
    """ A tank's glass in a frame, facing the front (the room), with its collision ( thick, behind its face ). """
    paint = tank_paint( tank ) if tank in TANKS else tank
    if rise:
        pts = seg_arch( u0, u1, z1, rise, 10 )
        outline = [ fr.p( u0, w, z0 ), fr.p( u1, w, z0 ) ] + [ fr.p( u, w, z ) for u, z in reversed( pts ) ]
        facing( model, paint, outline, fr.vec( 0, 1, 0 ) )
        fbox( model, fr, u0, u1, w - thick, w, z0, z1 - rise, None, surface )
        for ( ua, za ), ( ub, zb ) in zip( pts, pts[1:] ):
            quad_hull( model, [ fr.p( ua, ww, z ) for ww in ( w - thick, w ) for z in ( z1 - rise, za ) ]
                       + [ fr.p( ub, ww, z ) for ww in ( w - thick, w ) for z in ( z1 - rise, zb ) ], surface )
    else:
        facing( model, paint, [ fr.p( u0, w, z0 ), fr.p( u1, w, z0 ), fr.p( u1, w, z1 ), fr.p( u0, w, z1 ) ], fr.vec( 0, 1, 0 ) )
        fbox( model, fr, u0, u1, w - thick, w, z0, z1, None, surface )


# The water the animals swim in (Code/Maps/TankFauna.cs), and what stands in it, kept as the inside model's props:
# plan points, mirrored with the rest of the room, and written into the scene as one TankFauna per tank.

def water_box( model, fr, u0, u1, w0, w1, z0, z1, hole=None ):
    """ A box of water in a frame. hole: ( radius, plan point on its axis ), a glass tube along the frame's u. """
    model.props.append( { "fauna": "box", "position": tuple( fr.p( ( u0 + u1 ) / 2, ( w0 + w1 ) / 2, ( z0 + z1 ) / 2 ) ),
                          "along": tuple( fr.d ), "size": ( u1 - u0, w1 - w0, z1 - z0 ),
                          "hole": None if hole is None else ( hole[0], tuple( np.asarray( hole[1], float ) ) ) } )


def water_cylinder( model, centre, radius, z0, z1 ):
    model.props.append( { "fauna": "cylinder", "position": ( centre[0], centre[1], ( z0 + z1 ) / 2 ), "along": ( 1.0, 0.0 ),
                          "size": ( 2 * radius, 2 * radius, z1 - z0 ), "hole": None } )


def obstacle( model, base, radius, height, taper ):
    """ Something standing in the water: radius at its foot, narrowing by taper (a share) to its top; a negative
    taper widens it (kelp). """
    model.props.append( { "fauna": "obstacle", "position": tuple( np.asarray( base, float ) ), "radius": radius,
                          "height": height, "taper": taper } )


def polygon_counts( model ):
    """ How many polygons each paint has, to find what a builder adds (`fit_obstacle`). """
    return { paint: len( items ) for paint, items in model.polygons.items() }


def fit_obstacle( model, before, axis=None, margin=0.6 ):
    """ The obstacle for everything drawn since `before` (polygon_counts): the narrowest upright frustum round it, on
    an axis through `axis` (plan x y; else the middle of what was drawn), that holds every corner of it. A frustum is
    convex, so it holds the polygons too: no fish's reach can then reach into a rock, a coral or a kelp leaf. """
    points = [ p for paint, items in model.polygons.items() for pts, _ in items[before.get( paint, 0 ):] for p in pts ]
    if not points:
        return
    p = np.asarray( points, float )
    if axis is None:
        axis = ( ( p[:, 0].min() + p[:, 0].max() ) / 2, ( p[:, 1].min() + p[:, 1].max() ) / 2 )
    z0, z1 = float( p[:, 2].min() ), float( p[:, 2].max() )
    height = max( z1 - z0, 0.5 )
    d = np.hypot( p[:, 0] - axis[0], p[:, 1] - axis[1] )
    zf = ( p[:, 2] - z0 ) / height
    best = None
    for taper in np.linspace( -2.0, 0.9, 59 ):
        radius = float( np.max( d / ( 1 - taper * zf ) ) )
        volume = radius * radius * ( 1 - taper + taper * taper / 3 )
        if best is None or volume < best[0]:
            best = ( volume, radius, taper )
    _, radius, taper = best
    # The margin all round: a frustum grown by it sideways (its taper's share of the larger radius) and over its top
    grown = radius + margin
    taper = 1 - ( radius * ( 1 - taper ) + margin ) / grown
    obstacle( model, ( axis[0], axis[1], z0 - margin ), grown, height + 2 * margin, float( taper ) )


def tank_box( inside, fr, u0, u1, w0, w1, z0, z1, rng, floor_z=None, back="rh_tankback", decor="reef" ):
    """ A tank's insides behind a window (w0 < w1, w1 at the glass): its walls facing in, a sand floor, rock and coral.
    Drawn only (the glass holds everyone out). """
    floor_z = z0 if floor_z is None else floor_z
    c = fr.p
    facing( inside, back, [ c( u0, w0, z0 ), c( u1, w0, z0 ), c( u1, w0, z1 ), c( u0, w0, z1 ) ], fr.vec( 0, 1, 0 ) )
    facing( inside, back, [ c( u0, w0, z0 ), c( u0, w1, z0 ), c( u0, w1, z1 ), c( u0, w0, z1 ) ], fr.vec( 1, 0, 0 ) )
    facing( inside, back, [ c( u1, w0, z0 ), c( u1, w1, z0 ), c( u1, w1, z1 ), c( u1, w0, z1 ) ], fr.vec( -1, 0, 0 ) )
    facing( inside, back, [ c( u0, w0, z1 ), c( u1, w0, z1 ), c( u1, w1, z1 ), c( u0, w1, z1 ) ], fr.vec( 0, 0, -1 ) )
    facing( inside, "rh_sand", [ c( u0, w0, floor_z ), c( u1, w0, floor_z ), c( u1, w1, floor_z ), c( u0, w1, floor_z ) ],
            fr.vec( 0, 0, 1 ) )
    if floor_z > z0 + 0.5:
        facing( inside, "rh_sand", [ c( u0, w1, z0 ), c( u1, w1, z0 ), c( u1, w1, floor_z ), c( u0, w1, floor_z ) ], fr.vec( 0, 1, 0 ) )
    width, depth, height = u1 - u0, w1 - w0, z1 - floor_z
    water_box( inside, fr, u0 + 2, u1 - 2, w0 + 2, w1 - 2, floor_z + 2, z1 - 10 )
    if decor is None:
        return
    # A rock bank along the back, coral and kelp in front of it.
    count = max( 2, int( width / 70 ) )
    for k in range( count ):
        u = u0 + width * ( k + 0.5 ) / count + rng.uniform( -18, 18 )
        r = min( depth * 0.42, rng.uniform( 26, 44 ) * ( 0.7 + 0.6 * min( height / 300, 1 ) ) )
        rock( inside, c( u, w0 + r * 0.7, floor_z ), r, min( height * rng.uniform( 0.35, 0.75 ), r * 2.6 ), rng )
    # A big enough tank gets a rock arch across its middle, as most show tanks have.
    if width >= 300 and height >= 200 and depth >= 120:
        span = min( width * 0.45, 380 )
        mid_u = u0 + width * rng.uniform( 0.35, 0.65 )
        thick = min( 40, depth * 0.18 )
        rock_arch( inside, c( mid_u - span / 2, w0 + depth * 0.4, floor_z ), c( mid_u + span / 2, w0 + depth * 0.4, floor_z ),
                   min( height * 0.6, span * 0.7 ), thick, rng )
    scale = min( 1.0, height / 120 + 0.4 )
    for k in range( max( 1, int( width / 40 ) ) ):
        u = u0 + rng.uniform( 0.08, 0.92 ) * width
        w = w0 + rng.uniform( 0.35, 0.75 ) * depth
        coral( inside, c( u, w, floor_z ), rng.uniform( 9, 18 ) * scale, rng )
    # In front, near the glass: low coral and sea grass, so the reef starts right behind the pane.
    for k in range( max( 1, int( width / 60 ) ) ):
        u = u0 + rng.uniform( 0.05, 0.95 ) * width
        coral( inside, c( u, w1 - min( 30, depth * 0.2 ), floor_z ), rng.uniform( 6, 11 ) * scale, rng )
    for k in range( max( 1, int( width / 50 ) ) ):
        u = u0 + rng.uniform( 0.05, 0.95 ) * width
        sea_grass( inside, c( u, w0 + rng.uniform( 0.55, 0.85 ) * depth, floor_z ), rng, height=min( 34, height * 0.25 ) )
    if height > 90:
        for k in range( max( 1, int( width / 90 ) ) ):
            u = u0 + rng.uniform( 0.05, 0.95 ) * width
            kelp( inside, c( u, w0 + rng.uniform( 0.15, 0.5 ) * depth, floor_z ), height * rng.uniform( 0.55, 0.9 ), rng )


def lump( model, centre, rx, ry, rz, paint, rng, segments=16, rings=9, wobble=0.11, flat_bottom=True, crag=0.0 ):
    """ A lumpy ellipsoid (a rock, a coral head), smooth-shaded, cut flat at its base. The lumps are a few smooth waves
    over the surface, so it reads as a worn stone, not a crumpled one; crag adds finer ridges and pits (reef rock).
    The normals come from the bent surface itself, so the pits catch the light. """
    c = np.asarray( centre, float )
    waves = [ ( normalise( rng.standard_normal( 3 ) ) * rng.uniform( 1.5, 4.0 ), rng.uniform( 0, 2 * math.pi ), rng.uniform( 0.5, 1.0 ) )
              for _ in range( 5 ) ]
    total = sum( w for _, _, w in waves )
    fine = [ ( normalise( rng.standard_normal( 3 ) ) * rng.uniform( 6.0, 12.0 ), rng.uniform( 0, 2 * math.pi ), rng.uniform( 0.5, 1.0 ) )
             for _ in range( 6 ) ] if crag else []
    fine_total = sum( w for _, _, w in fine ) or 1.0
    lo = math.pi / 2 if flat_bottom else math.pi

    def direction( i, j ):
        polar_ = lo * i / rings
        az = 2 * math.pi * j / segments + 0.37 * i
        return np.array( ( math.sin( polar_ ) * math.cos( az ), math.sin( polar_ ) * math.sin( az ), math.cos( polar_ ) ) )

    def at( i, j ):
        d = direction( i, j )
        s = 1.0 + wobble * sum( w * math.sin( float( np.dot( f, d ) ) + ph ) for f, ph, w in waves ) / total * 1.6
        if fine:
            s += crag * sum( w * math.sin( float( np.dot( f, d ) ) + ph ) for f, ph, w in fine ) / fine_total * 1.6
        return c + np.array( ( rx * d[0], ry * d[1], rz * d[2] ) ) * s

    grid = [ [ at( i, j ) for j in range( segments ) ] for i in range( rings + 1 ) ]

    def normal_at( i, j ):
        if i == 0:
            return np.array( ( 0.0, 0.0, 1.0 ) )
        a = grid[min( i + 1, rings )][j] - grid[i - 1][j]
        b = grid[i][( j + 1 ) % segments] - grid[i][( j - 1 ) % segments]
        n = np.cross( a, b )
        if np.dot( n, grid[i][j] - c ) < 0:
            n = -n
        length = np.linalg.norm( n )
        return n / length if length > 1e-9 else normalise( grid[i][j] - c )

    normals_ = [ [ normal_at( i, j ) for j in range( segments ) ] for i in range( rings + 1 ) ]
    for i in range( rings ):
        for j in range( segments ):
            j1 = ( j + 1 ) % segments
            p0, p1, p2, p3 = grid[i][j], grid[i + 1][j], grid[i + 1][j1], grid[i][j1]
            n0, n1, n2, n3 = normals_[i][j], normals_[i + 1][j], normals_[i + 1][j1], normals_[i][j1]
            pts, normals = ( [ p0, p1, p2 ], [ n0, n1, n2 ] ) if i == 0 else ( [ p0, p1, p2, p3 ], [ n0, n1, n2, n3 ] )
            normal = np.zeros( 3 )
            for k in range( 1, len( pts ) - 1 ):
                normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
            if np.dot( normal, np.mean( pts, axis=0 ) - c ) < 0:
                pts, normals = pts[:1] + pts[:0:-1], normals[:1] + normals[:0:-1]
            model.polygon( paint, pts, normals=normals )


def rotate( v, axis, angle ):
    """ v turned by angle (radians) about axis (Rodrigues). """
    v, k = np.asarray( v, float ), normalise( np.asarray( axis, float ) )
    return v * math.cos( angle ) + np.cross( k, v ) * math.sin( angle ) + k * np.dot( k, v ) * ( 1 - math.cos( angle ) )


def rock( model, base, r, height, rng, paint="rh_rock", corals=True ):
    """ A reef rock: a few craggy masses heaped on each other, wider below, with boulders round its foot and coral
    growing on its ledges, as the live rock in a show tank is. """
    rng = np.random.default_rng( int( rng.integers( 1 << 30 ) ) )
    b = np.asarray( base, float )
    before = polygon_counts( model )
    z = b[2]
    level = 0
    ledges = []
    while z < b[2] + height - 4 and level < 5:
        frac = ( z - b[2] ) / max( height, 1 )
        rr = r * ( 1.0 - 0.5 * frac ) * rng.uniform( 0.85, 1.1 )
        rz = min( rr * rng.uniform( 0.8, 1.3 ), b[2] + height - z + rr * 0.3 )
        off = rng.uniform( -0.25, 0.25, 2 ) * r * ( 1.0 - 0.5 * frac )
        ry = rr * rng.uniform( 0.7, 1.0 )
        centre = ( b[0] + off[0], b[1] + off[1], z - rz * 0.3 )
        lump( model, centre, rr, ry, rz, paint, rng, segments=14, rings=8, wobble=0.16, crag=0.07 )
        ledges.append( ( np.asarray( centre ), rr, ry, rz ) )
        z += rz * 0.72
        level += 1
    for k in range( int( rng.integers( 1, 4 ) ) ):
        a = rng.uniform( 0, 2 * math.pi )
        d = r * rng.uniform( 0.8, 1.15 )
        br = r * rng.uniform( 0.28, 0.45 )
        lump( model, ( b[0] + math.cos( a ) * d, b[1] + math.sin( a ) * d, b[2] - br * 0.2 ), br, br * rng.uniform( 0.7, 1.0 ),
              br * rng.uniform( 0.6, 0.9 ), paint, rng, segments=9, rings=5, wobble=0.15, crag=0.06 )
    if corals:
        # The upper ledges only: lower down the colonies hide behind the rock in front.
        for centre, rx, ry, rz in ledges[-2:]:
            for k in range( int( rng.integers( 0, 3 ) ) ):
                th, ph = rng.uniform( 0.0, 0.7 ), rng.uniform( 0, 2 * math.pi )
                p = centre + np.array( ( rx * math.sin( th ) * math.cos( ph ), ry * math.sin( th ) * math.sin( ph ), rz * math.cos( th ) ) ) * 0.82
                coral( model, p, rng.uniform( 6, 12 ) * min( 1.2, max( 0.6, r / 36 ) ), rng )
    fit_obstacle( model, before, ( b[0], b[1] ) )
    return ledges


def rock_arch( model, a, b, height, thick, rng, paint="rh_rock" ):
    """ A natural rock arch from foot a to foot b ( points on the sand ): craggy masses along a half ellipse, heavier at
    the legs, with coral on its back. Fish swim through under it. """
    rng = np.random.default_rng( int( rng.integers( 1 << 30 ) ) )
    a, b = np.asarray( a, float ), np.asarray( b, float )
    mid, half = ( a + b ) / 2, ( b - a ) / 2
    arc = math.pi * ( np.linalg.norm( half[:2] ) + height ) / 2
    n = max( 10, int( arc / ( thick * 0.4 ) ) )
    for i in range( n + 1 ):
        t = math.pi * i / n
        p = mid - half * math.cos( t ) + np.array( ( 0.0, 0.0, height * math.sin( t ) ) )
        leg = 1.0 - math.sin( t )
        rr = thick * ( 0.8 + 0.5 * leg ) * rng.uniform( 0.9, 1.1 )
        foot = i in ( 0, n )
        centre = p - np.array( ( 0, 0, rr * 0.35 ) ) if foot else p
        before = polygon_counts( model )
        lump( model, centre, rr, rr * rng.uniform( 0.8, 1.0 ), rr * rng.uniform( 0.85, 1.1 ), paint, rng, segments=13,
              rings=8, wobble=0.18, crag=0.08, flat_bottom=foot )
        if not foot and rng.random() < 0.4:
            ph = rng.uniform( 0, 2 * math.pi )
            top = p + np.array( ( math.cos( ph ) * rr * 0.4, math.sin( ph ) * rr * 0.4, rr * 0.85 ) )
            coral( model, top, rng.uniform( 6, 11 ), rng )
        fit_obstacle( model, before, ( p[0], p[1] ) )
    for foot in ( a, b ):
        rock( model, foot, thick * 1.3, thick * 1.6, rng, paint )


CORALS = ( "rh_coral_pink", "rh_coral_orange", "rh_coral_yellow", "rh_coral_purple", "rh_coral_green", "rh_coral_white" )
CORAL_KINDS = ( ( "brain", 0.2 ), ( "staghorn", 0.22 ), ( "table", 0.1 ), ( "fan", 0.16 ), ( "soft", 0.2 ), ( "tubes", 0.12 ) )


def branch( model, p, d, length, radius, depth, paint, rng, plane=None ):
    """ A coral branch and its forks, thinning towards the tips. plane: a normal the forks stay square to (a fan). """
    end = p + d * length
    tube( model, p, end, radius, paint, sides=4, cap=False, radius1=radius * 0.78 )
    if depth == 0:
        return
    for k in range( int( rng.integers( 2, 4 ) ) ):
        if plane is None:
            axis = normalise( np.cross( d, rng.standard_normal( 3 ) ) )
            nd = rotate( d, axis, math.radians( rng.uniform( 22, 42 ) ) )
            nd = normalise( nd + np.array( ( 0, 0, 0.25 ) ) )
        else:
            nd = rotate( d, plane, math.radians( rng.uniform( 18, 40 ) * ( 1 if k % 2 else -1 ) ) )
        branch( model, end, nd, length * rng.uniform( 0.62, 0.8 ), radius * 0.78, depth - 1, paint, rng, plane )


def coral( model, base, size, rng, kind=None ):
    """ A coral colony on the sand or a rock: a brain coral's dome, staghorn, a table, a sea fan, soft coral or tube
    sponges, each in one of the colony colours. """
    rng = np.random.default_rng( int( rng.integers( 1 << 30 ) ) )
    b = np.asarray( base, float )
    before = polygon_counts( model )
    paint = CORALS[rng.integers( len( CORALS ) )]
    if kind is None:
        names, weights = zip( *CORAL_KINDS )
        kind = names[rng.choice( len( names ), p=np.asarray( weights ) / sum( weights ) )]
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    if kind == "brain":
        lump( model, b - ( 0, 0, size * 0.15 ), size * 1.1, size * rng.uniform( 0.85, 1.05 ), size * rng.uniform( 0.6, 0.8 ), paint, rng,
              segments=12, rings=6, wobble=0.1, crag=0.03 )
    elif kind == "staghorn":
        for k in range( int( rng.integers( 2, 5 ) ) ):
            d = normalise( up + np.array( ( *rng.uniform( -0.5, 0.5, 2 ), 0.0 ) ) )
            branch( model, b - ( 0, 0, 1 ), d, size * rng.uniform( 0.7, 1.0 ), size * 0.13, 2, paint, rng )
    elif kind == "table":
        top = b + ( 0, 0, size * rng.uniform( 0.6, 0.9 ) )
        tube( model, b - ( 0, 0, 1 ), top, size * 0.16, paint, sides=7, radius1=size * 0.22 )
        lump( model, top, size * 1.7, size * rng.uniform( 1.4, 1.7 ), size * 0.16, paint, rng, segments=14, rings=4, wobble=0.12,
              flat_bottom=False )
    elif kind == "fan":
        paint = ( "rh_coral_purple", "rh_coral_orange", "rh_coral_yellow", "rh_coral_pink" )[rng.integers( 4 )]
        a = rng.uniform( 0, math.pi )
        plane = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
        for k in range( 3 ):
            d = rotate( up, plane, math.radians( ( k - 1 ) * 28 ) )
            branch( model, b - ( 0, 0, 1 ), d, size * 0.9, size * 0.07, 2, paint, rng, plane )
    elif kind == "soft":
        for k in range( int( rng.integers( 6, 10 ) ) ):
            d = normalise( up + np.array( ( *rng.uniform( -0.8, 0.8, 2 ), 0.0 ) ) )
            r = size * rng.uniform( 0.1, 0.16 )
            tip = b + d * size * rng.uniform( 0.5, 1.1 )
            tube( model, b - ( 0, 0, 1 ), tip, r * 0.8, paint, sides=6, radius1=r )
            lump( model, tip, r * 1.4, r * 1.4, r * 1.2, paint, rng, segments=5, rings=3, wobble=0.05, flat_bottom=False )
    else:
        for k in range( int( rng.integers( 3, 7 ) ) ):
            off = np.array( ( *rng.uniform( -0.5, 0.5, 2 ), 0.0 ) ) * size
            d = normalise( up + np.array( ( *rng.uniform( -0.2, 0.2, 2 ), 0.0 ) ) )
            r = size * rng.uniform( 0.16, 0.26 )
            tube( model, b + off - ( 0, 0, 1 ), b + off + d * size * rng.uniform( 1.0, 2.2 ), r * 0.9, paint, sides=8, cap=True, radius1=r )
    fit_obstacle( model, before, ( b[0], b[1] ) )


def tube( model, p0, p1, radius, paint, sides=10, cap=False, radius1=None ):
    """ A round bar from p0 to p1 (a pipe, a rail, a coral branch), smooth-shaded. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    axis = normalise( p1 - p0 )
    u = normalise( np.cross( axis, ( 0, 0, 1 ) ) if abs( axis[2] ) < 0.9 else np.cross( axis, ( 1, 0, 0 ) ) )
    v = np.cross( axis, u )
    r1 = radius if radius1 is None else radius1
    dirs = [ math.cos( 2 * math.pi * k / sides ) * u + math.sin( 2 * math.pi * k / sides ) * v for k in range( sides ) ]
    for k in range( sides ):
        a, b = dirs[k], dirs[( k + 1 ) % sides]
        pts = [ p0 + a * radius, p0 + b * radius, p1 + b * r1, p1 + a * r1 ]
        model.polygon( paint, pts, normals=[ a, b, b, a ] )
    if cap:
        facing( model, paint, [ p1 + d * r1 for d in dirs ], axis )
        facing( model, paint, [ p0 + d * radius for d in dirs ], -axis )


# A kelp leaf's outline in its texture's space: u across the frond strip, v along it (base to tip).
LEAF = ( ( 0.5, 0.0 ), ( 0.92, 0.18 ), ( 1.0, 0.55 ), ( 0.82, 0.85 ), ( 0.5, 1.0 ), ( 0.18, 0.85 ), ( 0.0, 0.55 ), ( 0.08, 0.18 ) )


def kelp( model, base, height, rng, blades=3 ):
    """ Giant kelp: a few stipes rising in a slow curve from one holdfast, each with leaves along it on alternate sides,
    angled up and drooping at their tips, and a long blade at the top. The leaves are alpha-tested, both sides. """
    rng = np.random.default_rng( int( rng.integers( 1 << 30 ) ) )
    b = np.asarray( base, float )
    before = polygon_counts( model )
    lump( model, b, 7, 6, 4, "rh_coral_green", rng, segments=8, rings=4, wobble=0.2 )
    up = np.array( ( 0.0, 0.0, 1.0 ) )
    for s in range( max( 2, blades ) ):
        h = height * rng.uniform( 0.7, 1.0 )
        lean = np.array( ( *rng.uniform( -0.12, 0.12, 2 ), 0.0 ) )
        a = rng.uniform( 0, 2 * math.pi )
        sway = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
        ph = rng.uniform( 0, 2 * math.pi )
        root = b + np.array( ( *rng.uniform( -3, 3, 2 ), 0.0 ) )
        segs = max( 5, int( h / 36 ) )
        pts = [ root + lean * ( h * i / segs ) + up * ( h * i / segs ) + sway * math.sin( i * 0.8 + ph ) * 5 for i in range( segs + 1 ) ]
        for i in range( segs ):
            tube( model, pts[i], pts[i + 1], 1.1, "rh_coral_green", sides=4 )
        spacing = rng.uniform( 17, 23 )
        t = rng.uniform( 6, 14 )
        side = 1.0
        while t < h - 24:
            k = min( int( t / h * segs ), segs - 1 )
            f = t / h * segs - k
            p = pts[k] * ( 1 - f ) + pts[k + 1] * f
            stem = normalise( pts[k + 1] - pts[k] )
            out = normalise( np.cross( stem, ( 0.0, 0.0, 1.0 ) + rng.standard_normal( 3 ) * 0.3 ) ) * side
            leaf( model, p, normalise( out * 0.75 + stem * 0.9 ), rng.uniform( 26, 40 ) * ( 0.6 + 0.4 * math.sin( math.pi * t / h ) + 0.2 ),
                  rng.uniform( 7, 10 ), rng )
            side = -side
            t += spacing
        leaf( model, pts[-1], normalise( pts[-1] - pts[-2] + sway * 0.3 ), rng.uniform( 40, 60 ), rng.uniform( 8, 11 ), rng )
    # Its stipes lean and its leaves reach out, so it widens upwards: the frustum fitted round it does too.
    fit_obstacle( model, before, ( b[0], b[1] ) )


def leaf( model, base, along, length, width, rng ):
    """ One kelp leaf from base along a direction, its tip drooping a little. """
    across = normalise( np.cross( along, ( 0.0, 0.0, 1.0 ) ) if abs( along[2] ) < 0.98 else np.array( ( 1.0, 0.0, 0.0 ) ) )
    across = rotate( across, along, rng.uniform( -0.6, 0.6 ) )
    droop = rng.uniform( 0.05, 0.18 ) * length
    pts = [ base + along * v * length + across * ( u - 0.5 ) * width - np.array( ( 0.0, 0.0, droop * v * v ) ) for u, v in LEAF ]
    model.polygon( "rh_kelp", pts, both_sides=True, uv=[ ( u, v ) for u, v in LEAF ] )


def sea_grass( model, base, rng, count=None, height=None ):
    """ A tuft of sea grass on the sand: thin blades fanning out and bending over. """
    b = np.asarray( base, float )
    count = count or int( rng.integers( 6, 12 ) )
    height = height or rng.uniform( 16, 34 )
    before = polygon_counts( model )
    for k in range( count ):
        a = rng.uniform( 0, 2 * math.pi )
        d = np.array( ( math.cos( a ), math.sin( a ), 0.0 ) )
        h = height * rng.uniform( 0.6, 1.0 )
        lean = rng.uniform( 0.15, 0.5 )
        w = rng.uniform( 1.6, 2.6 )
        across = np.array( ( -d[1], d[0], 0.0 ) )
        mid = b + d * lean * h * 0.3 + np.array( ( 0, 0, h * 0.55 ) )
        tip = b + d * lean * h + np.array( ( 0, 0, h * 0.9 ) )
        model.polygon( "rh_kelp", [ b - across * w, b + across * w, mid + across * w * 0.8, mid - across * w * 0.8 ], both_sides=True,
                       uv=[ ( 0.1, 0.0 ), ( 0.9, 0.0 ), ( 0.85, 0.55 ), ( 0.15, 0.55 ) ] )
        model.polygon( "rh_kelp", [ mid - across * w * 0.8, mid + across * w * 0.8, tip ], both_sides=True,
                       uv=[ ( 0.15, 0.55 ), ( 0.85, 0.55 ), ( 0.5, 1.0 ) ] )
    fit_obstacle( model, before, ( b[0], b[1] ) )


def railing( model, p0, p1, z, height=42.0, glass=True, post_every=60.0, rail="rh_steel", collide=True ):
    """ A balcony railing from p0 to p1 (plan): steel posts, a round handrail and glass panels. Players can't pass it;
    rounds go through the glass. """
    p0, p1 = np.asarray( p0, float )[:2], np.asarray( p1, float )[:2]
    length = np.linalg.norm( p1 - p0 )
    if length < 1:
        return
    fr = Frame( p0, p1 - p0 )
    count = max( 1, int( math.ceil( length / post_every ) ) )
    for k in range( count + 1 ):
        u = length * k / count
        fbox( model, fr, u - 1.25, u + 1.25, -1.25, 1.25, z, z + height - 2, "rh_gunmetal" )
    tube( model, fr.p( -1, 0, z + height ), fr.p( length + 1, 0, z + height ), 1.6, rail, sides=8 )
    if glass:
        for k in range( count ):
            a, b = length * k / count + 2.5, length * ( k + 1 ) / count - 2.5
            facing( model, "rh_glass", [ fr.p( a, 0, z + 4 ), fr.p( b, 0, z + 4 ), fr.p( b, 0, z + height - 4 ), fr.p( a, 0, z + height - 4 ) ],
                    fr.vec( 0, 1, 0 ) )
            facing( model, "rh_glass", [ fr.p( a, 0, z + 4 ), fr.p( b, 0, z + 4 ), fr.p( b, 0, z + height - 4 ), fr.p( a, 0, z + height - 4 ) ],
                    fr.vec( 0, -1, 0 ) )
    else:
        for zz in ( z + 14, z + 28 ):
            tube( model, fr.p( 0, 0, zz ), fr.p( length, 0, zz ), 0.8, "rh_gunmetal", sides=6 )
    if collide:
        fbox( model, fr, 0, length, -1.5, 1.5, z, z + 4, None, METAL )
        fbox( model, fr, 0, length, -0.5, 0.5, z + 4, z + height - 4, None, GLASS if glass else METAL )
        fbox( model, fr, 0, length, -1.6, 1.6, z + height - 4, z + height + 1.6, None, METAL )


def stair( model, lo, hi, z0, z1, climb, tread="rh_floor", side="rh_wall", surface=STONE, nosing="rh_brass" ):
    """ A straight flight over the plan rectangle lo..hi ( e, n ), climbing towards climb ('+e', '-e', '+n', '-n') from
    z0 to z1 in risers of about 8: each step a solid box down to z0, with a brass nosing strip. """
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
        if nosing:
            edge = s0 if climb[0] == "+" else s1
            nlo, nhi = list( blo ), list( bhi )
            nlo[axis], nhi[axis] = ( edge, edge + 2.0 ) if climb[0] == "+" else ( edge - 2.0, edge )
            model.box( ( nlo[0], nlo[1], z0 + rise * ( k + 1 ) ), ( nhi[0], nhi[1], z0 + rise * ( k + 1 ) + 0.15 ), nosing )


def metal_stair( model, lo, hi, z0, z1, climb, surface=METAL ):
    """ An open steel stair: grating treads between two stringers, its collision a smooth ramp of steps. """
    steps = max( 1, round( ( z1 - z0 ) / 8 ) )
    rise = ( z1 - z0 ) / steps
    axis = 0 if climb[1] == "e" else 1
    other = 1 - axis
    a0, a1 = lo[axis], hi[axis]
    run = ( a1 - a0 ) / steps
    for k in range( steps ):
        s0, s1 = ( a0 + k * run, a0 + ( k + 1 ) * run ) if climb[0] == "+" else ( a1 - ( k + 1 ) * run, a1 - k * run )
        blo, bhi = list( lo ), list( hi )
        blo[axis], bhi[axis] = s0, s1
        top = z0 + rise * ( k + 1 )
        model.box( ( blo[0], blo[1], top - 2 ), ( bhi[0], bhi[1], top ), { "+z": "rh_grate", "default": "rh_gunmetal" } )
        model.collision_box( ( blo[0], blo[1], z0 ), ( bhi[0], bhi[1], top ), surface )
    for side in ( lo[other], hi[other] ):
        p_lo, p_hi = [ 0.0, 0.0 ], [ 0.0, 0.0 ]
        p_lo[axis], p_hi[axis] = ( a0, a1 ) if climb[0] == "+" else ( a1, a0 )
        p_lo[other] = p_hi[other] = side
        bottom = np.array( ( *p_lo, z0 + rise * 0.5 - 6 ) )
        top_ = np.array( ( *p_hi, z1 - 6 ) )
        model.beam( bottom, top_, ( 2.5, 12.0 ), "rh_steel_blue" )
        railing( model, bottom + ( 0, 0, 6 ), top_ + ( 0, 0, 6 ), 0, glass=False, collide=False ) if False else None
    return steps


def stair_rail( model, lo, hi, z0, z1, climb, sides=( True, True ), glass=False ):
    """ Handrails along a straight flight's sides, sloping with it. """
    axis = 0 if climb[1] == "e" else 1
    other = 1 - axis
    a0, a1 = ( lo[axis], hi[axis] ) if climb[0] == "+" else ( hi[axis], lo[axis] )
    for keep, side in zip( sides, ( lo[other], hi[other] ) ):
        if not keep:
            continue
        p0, p1 = [ 0.0, 0.0, z0 ], [ 0.0, 0.0, z1 ]
        p0[axis], p1[axis] = a0, a1
        p0[other] = p1[other] = side
        p0, p1 = np.array( p0 ), np.array( p1 )
        length = np.linalg.norm( ( p1 - p0 )[:2] )
        count = max( 1, int( length / 60 ) )
        for k in range( count + 1 ):
            t = k / count
            p = p0 + ( p1 - p0 ) * t
            model.box( ( p[0] - 1.2, p[1] - 1.2, p[2] ), ( p[0] + 1.2, p[1] + 1.2, p[2] + 38 ), "rh_gunmetal" )
        tube( model, p0 + ( 0, 0, 40 ), p1 + ( 0, 0, 40 ), 1.6, "rh_steel", sides=8 )
        fr = Frame( p0, ( p1 - p0 )[:2] )
        hull = []
        for t, p in ( ( 0, p0 ), ( 1, p1 ) ):
            for w in ( -1.6, 1.6 ):
                xy = p[:2] + fr.f * w
                hull += [ ( xy[0], xy[1], p[2] ), ( xy[0], xy[1], p[2] + 42 ) ]
        model.hull( hull, METAL )


def skip_cases( rng, stacks=1, tall=0 ):
    """ Reef Hall's padded transport cases came out on 2026-10-12 (the user: "they look awful"). A stack of them drew
    one of its room's random numbers, and a tall one two, so this draws the same: everything after it in the room
    comes out as it did. """
    for _ in range( stacks + tall ):
        rng.uniform( -1, 1 )


def downlight_rings( model, centre, z, radius=7.0 ):
    """ A recessed round downlight in a ceiling: a gunmetal ring round a glowing disc. """
    c = np.asarray( centre, float )
    ring = [ ( c[0] + radius * math.cos( 2 * math.pi * k / 12 ), c[1] + radius * math.sin( 2 * math.pi * k / 12 ), z - 0.2 )
             for k in range( 12 ) ]
    facing( model, "rh_led_warm", ring, ( 0, 0, -1 ) )
    outer = [ ( c[0] + ( radius + 2.5 ) * math.cos( 2 * math.pi * k / 12 ), c[1] + ( radius + 2.5 ) * math.sin( 2 * math.pi * k / 12 ), z - 0.1 )
              for k in range( 12 ) ]
    facing( model, "rh_gunmetal", outer, ( 0, 0, -1 ) )


def drain( model, e0, e1, n0, n1, z=0.0 ):
    """ A trench drain: a steel grating flush with the floor in a gunmetal edge. """
    model.box( ( e0 - 2, n0 - 2, z - 0.4 ), ( e1 + 2, n1 + 2, z + 0.06 ), { "+z": "rh_gunmetal", "default": None } )
    model.box( ( e0, n0, z - 0.4 ), ( e1, n1, z + 0.12 ), { "+z": "rh_grate", "default": None } )


def decal( model, paint, e0, e1, n0, n1, z ):
    """ A floor picture laid once across the rectangle, just over the floor. """
    model.polygon( paint, [ ( e0, n0, z + 0.08 ), ( e1, n0, z + 0.08 ), ( e1, n1, z + 0.08 ), ( e0, n1, z + 0.08 ) ] )


def bench( model, centre, yaw, length=96.0, z=0.0 ):
    fr = Frame( centre, ( math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) ) ) )
    fbox( model, fr, -length / 2, length / 2, -9, 9, z + 15, z + 18, "rh_laminate", WOOD )
    for u in ( -length / 2 + 8, length / 2 - 8 ):
        fbox( model, fr, u - 2, u + 2, -8, 8, z, z + 15, "rh_gunmetal", METAL )


def lectern( model, centre, yaw, z=0.0, screen="rh_screen_map" ):
    """ An information stand: a gunmetal post with a sloping lit panel. """
    fr = Frame( centre, ( math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) ) ) )
    fbox( model, fr, -8, 8, -5, 5, z, z + 34, "rh_gunmetal", METAL )
    fbox( model, fr, -12, 12, -9, 9, z, z + 2, "rh_gunmetal" )
    top = [ fr.p( -14, 6, z + 34 ), fr.p( 14, 6, z + 34 ), fr.p( 14, -8, z + 44 ), fr.p( -14, -8, z + 44 ) ]
    facing( model, screen, top, fr.vec( 0, 0.6, 0.8 ) )
    fbox( model, fr, -15, 15, -9, 7, z + 32, z + 34, "rh_gunmetal" )


def display_case( model, centre, size=( 40, 40 ), z=0.0, tank_name="display", rng=None, inside=None ):
    """ A small glass display tank on a plinth: a precast concrete base, a glass box with sand, coral and rock in it. """
    e, n = centre[:2]
    sx, sy = size
    model.box( ( e - sx / 2, n - sy / 2, z ), ( e + sx / 2, n + sy / 2, z + 30 ), { "default": "rh_smooth", "+z": "rh_black" }, METAL )
    top = z + 30
    h = 34
    paint = tank_paint( tank_name )
    for face in ( "+e", "-e", "+n", "-n", "+z" ):
        model.box( ( e - sx / 2 + 1, n - sy / 2 + 1, top ), ( e + sx / 2 - 1, n + sy / 2 - 1, top + h ), { face: paint, "default": None } )
    model.collision_box( ( e - sx / 2 + 1, n - sy / 2 + 1, top ), ( e + sx / 2 - 1, n + sy / 2 - 1, top + h ), GLASS )
    target = inside if inside is not None else model
    model.box( ( e - sx / 2 + 1, n - sy / 2 + 1, top + h - 0.3 ), ( e + sx / 2 - 1, n + sy / 2 - 1, top + h + 1.2 ), { "+z": "rh_gunmetal", "default": "rh_gunmetal" } )
    facing( target, "rh_sand", [ ( e - sx / 2 + 2, n - sy / 2 + 2, top + 4 ), ( e + sx / 2 - 2, n - sy / 2 + 2, top + 4 ),
                                 ( e + sx / 2 - 2, n + sy / 2 - 2, top + 4 ), ( e - sx / 2 + 2, n + sy / 2 - 2, top + 4 ) ], ( 0, 0, 1 ) )
    if rng is not None:
        rock( target, ( e - sx * 0.15, n + sy * 0.1, top + 4 ), min( sx, sy ) * 0.22, h * 0.55, rng )
        coral( target, ( e + sx * 0.2, n - sy * 0.15, top + 4 ), min( sx, sy ) * 0.13, rng )


def pipe_run( model, points, radius, paint="rh_pipe", flange_every=144.0, supports=None ):
    """ A pipe along a polyline (plan points with z), with flanges and elbows' collars, smooth-shaded. """
    pts = [ np.asarray( p, float ) for p in points ]
    for a, b in zip( pts, pts[1:] ):
        tube( model, a, b, radius, paint, sides=12 )
        length = np.linalg.norm( b - a )
        count = int( length / flange_every )
        for k in range( 1, count + 1 ):
            c = a + ( b - a ) * ( k / ( count + 1 ) )
            d = normalise( b - a )
            tube( model, c - d * 1.5, c + d * 1.5, radius * 1.32, "rh_steel", sides=12, cap=True )
    for p in pts[1:-1]:
        lump( model, p, radius * 1.05, radius * 1.05, radius * 1.05, paint, np.random.default_rng( 3 ), segments=10, rings=5,
              wobble=0.0, flat_bottom=False )


def light( name, position, color="1,0.84,0.64,1", radius=420.0, shadows=False ):
    """ A point light for the scene ( plan position ). Warm by default (the halls' downlights). """
    return ( name, tuple( float( c ) for c in position ), color, radius, shadows )


COOL = "1.3,2.2,2.8,1"        # the tanks' lamps: bright, as show tanks are lit from above
SPILL = "0.22,0.5,0.75,1"     # a tank's light through its window, falling into the room
WARM = "1,0.84,0.64,1"        # downlights


# ---------------------------------------------------------------------------------------------------------------------
# Round things: the rotunda's walls, floors and stairs

def sector( model, paint, r0, r1, a0, a1, z, up=True, steps=None ):
    """ A flat annular sector at z (angles in degrees), facing up or down, in pieces of at most 4 degrees. """
    steps = steps or max( 1, int( math.ceil( abs( a1 - a0 ) / 4.0 ) ) )
    for k in range( steps ):
        a, b = a0 + ( a1 - a0 ) * k / steps, a0 + ( a1 - a0 ) * ( k + 1 ) / steps
        pts = [ ( *polar( a, r0 ), z ), ( *polar( b, r0 ), z ), ( *polar( b, r1 ), z ), ( *polar( a, r1 ), z ) ]
        if r0 < 0.01:
            pts = pts[1:]
        facing( model, paint, pts, ( 0, 0, 1 if up else -1 ) )


def drum( model, paint, r, a0, a1, z0, z1, inward=True, steps=None, smooth=True ):
    """ A cylinder's face (angles in degrees), facing in or out, smooth-shaded. """
    steps = steps or max( 1, int( math.ceil( abs( a1 - a0 ) / 4.0 ) ) )
    for k in range( steps ):
        a, b = a0 + ( a1 - a0 ) * k / steps, a0 + ( a1 - a0 ) * ( k + 1 ) / steps
        pa, pb = polar( a, r ), polar( b, r )
        pts = [ np.array( ( *pa, z0 ) ), np.array( ( *pb, z0 ) ), np.array( ( *pb, z1 ) ), np.array( ( *pa, z1 ) ) ]
        sign = -1 if inward else 1
        na = np.array( ( *( pa / r ), 0.0 ) ) * sign
        nb = np.array( ( *( pb / r ), 0.0 ) ) * sign
        normal = np.cross( pts[1] - pts[0], pts[3] - pts[0] )
        if np.dot( normal, na + nb ) < 0:
            pts = [ pts[1], pts[0], pts[3], pts[2] ]
            na, nb = nb, na
        model.polygon( paint, pts, normals=[ na, nb, nb, na ] if smooth else None )


def ngon( r, sides=32 ):
    """ A circumscribing polygon of radius r (its flats at r), counter-clockwise. """
    rr = r / math.cos( math.pi / sides )
    return [ ( rr * math.cos( 2 * math.pi * ( k + 0.5 ) / sides ), rr * math.sin( 2 * math.pi * ( k + 0.5 ) / sides ) )
             for k in range( sides ) ]


def chord_frame( angle, half, r ):
    """ The frame of a straight wall piece on the chord of r from angle - half to angle + half, its front facing the
    centre: u 0 at the first end. Returns ( frame, length, the chord's distance from the centre ). """
    p0, p1 = polar( angle - half, r ), polar( angle + half, r )
    return Frame( p0, p1 - p0, -polar( angle, 1.0 ) ), float( np.linalg.norm( p1 - p0 ) ), r * math.cos( math.radians( half ) )


def arc_wall( model, r_in, r_out, a0, a1, z0, z1, paints, surface=STONE ):
    """ A round wall from angle a0 to a1 in straight pieces of at most 4 degrees, its face towards the centre. """
    if a1 - a0 < 1e-3:
        return
    steps = max( 1, int( math.ceil( ( a1 - a0 ) / 4.0 ) ) )
    for k in range( steps ):
        a, b = a0 + ( a1 - a0 ) * k / steps, a0 + ( a1 - a0 ) * ( k + 1 ) / steps
        fr, length, d = chord_frame( ( a + b ) / 2, ( b - a ) / 2, r_in )
        fbox( model, fr, -0.6, length + 0.6, -( r_out - d + 1.0 ), 0, z0, z1,
              { "front": paints["front"], "top": paints.get( "edge" ), "bottom": None, "left": None, "right": None,
                "back": paints.get( "back" ) }, surface )


def round_stair( model, r0, r1, a_foot, a_top, z0, z1, tread="rh_floor", side="rh_wall_dark", nosing="rh_brass" ):
    """ A curved flight in the band r0..r1 from angle a_foot (at z0) to a_top (z1): solid steps, each a hull. """
    steps = max( 1, round( ( z1 - z0 ) / 8 ) )
    rise = ( z1 - z0 ) / steps
    sign = 1 if a_top > a_foot else -1
    for k in range( steps ):
        a = a_foot + ( a_top - a_foot ) * k / steps
        b = a_foot + ( a_top - a_foot ) * ( k + 1 ) / steps
        top = z0 + rise * ( k + 1 )
        sector( model, tread, r0, r1, a, b, top, steps=1 )
        down = polar( a - sign * 90, 1.0 )
        pa0, pa1 = polar( a, r0 ), polar( a, r1 )
        facing( model, side, [ ( *pa0, top - rise ), ( *pa1, top - rise ), ( *pa1, top ), ( *pa0, top ) ], ( *down, 0 ) )
        # The sides face out of the step: the inner one towards the centre, the outer one away from it.
        lo_a, hi_a = min( a, b ), max( a, b )
        drum( model, side, r0, lo_a, hi_a, z0, top, inward=True, steps=1, smooth=False )
        drum( model, side, r1, lo_a, hi_a, z0, top, inward=False, steps=1, smooth=False )
        if nosing:
            na = a + ( b - a ) * 0.1
            facing( model, nosing, [ ( *polar( a, r0 ), top + 0.15 ), ( *polar( na, r0 ), top + 0.15 ),
                                     ( *polar( na, r1 ), top + 0.15 ), ( *polar( a, r1 ), top + 0.15 ) ], ( 0, 0, 1 ) )
        model.hull( [ ( *polar( x, r ), z ) for x in ( a, b ) for r in ( r0, r1 ) for z in ( z0, top ) ], STONE )
    # The last step's end, facing up the flight, down to the floor.
    pb0, pb1 = polar( a_top, r0 ), polar( a_top, r1 )
    facing( model, side, [ ( *pb0, z0 ), ( *pb1, z0 ), ( *pb1, z1 ), ( *pb0, z1 ) ], ( *polar( a_top + sign * 90, 1.0 ), 0 ) )


def arc_railing( model, r, a0, a1, z, glass=True, piece=8.0, collide=True ):
    """ A railing round an arc, in straight pieces. """
    if a1 - a0 < 0.2:
        return
    steps = max( 1, int( math.ceil( ( a1 - a0 ) / piece ) ) )
    for k in range( steps ):
        a, b = a0 + ( a1 - a0 ) * k / steps, a0 + ( a1 - a0 ) * ( k + 1 ) / steps
        railing( model, polar( a, r ), polar( b, r ), z, glass=glass, collide=collide )


def sloped_arc_railing( model, r, a_foot, a_top, z0, z1, piece=6.0 ):
    """ A handrail along a curved flight, rising with it. """
    steps = max( 1, int( math.ceil( abs( a_top - a_foot ) / piece ) ) )
    for k in range( steps + 1 ):
        a = a_foot + ( a_top - a_foot ) * k / steps
        z = z0 + ( z1 - z0 ) * k / steps
        p = polar( a, r )
        model.box( ( p[0] - 1.2, p[1] - 1.2, z ), ( p[0] + 1.2, p[1] + 1.2, z + 38 ), "rh_gunmetal" )
    for k in range( steps ):
        a, b = a_foot + ( a_top - a_foot ) * k / steps, a_foot + ( a_top - a_foot ) * ( k + 1 ) / steps
        za, zb = z0 + ( z1 - z0 ) * k / steps, z0 + ( z1 - z0 ) * ( k + 1 ) / steps
        pa, pb = polar( a, r ), polar( b, r )
        tube( model, ( *pa, za + 40 ), ( *pb, zb + 40 ), 1.6, "rh_steel", sides=8 )
        for zz in ( 14, 27 ):
            tube( model, ( *pa, za + zz ), ( *pb, zb + zz ), 0.8, "rh_gunmetal", sides=6 )
        fr = Frame( pa, pb - pa )
        model.hull( [ ( *( p + fr.f * w ), z ) for p, zz in ( ( pa, za ), ( pb, zb ) ) for w in ( -1.6, 1.6 ) for z in ( zz, zz + 42 ) ],
                    METAL )


# ---------------------------------------------------------------------------------------------------------------------
# The Rotunda (reference 5): a round hall round a tank that runs from its floor to its ceiling, with a ring balcony

R_TANK, R_PLINTH, R_BALCONY, R_WALL, R_WALL_OUT = 260.0, 280.0, 600.0, 850.0, 880.0
ROTUNDA_TOP = 560.0
EXITS = ( 0.0, 90.0, 180.0, 270.0 )              # the ground floor's openings (E, N, W, S)
EXIT_HALF = 8.0
ALCOVES = ( 45.0, 135.0, 225.0, 315.0 )          # the ground floor's wall tanks
ALCOVE_HALF = 10.0
UPPER = tuple( 22.5 + 45 * k for k in range( 8 ) )   # the balcony's wall tanks
UPPER_HALF = 9.0
STAIRS = ( ( 82.0, 47.5 ), ( 98.0, 132.5 ) )      # ( foot, top ) angles: NE and NW
STAIR_BAND = ( 480.0, 600.0 )
CORRIDOR = 110.0      # half the width of every corridor


def rotunda( model, inside, lights, rng ):
    wall_paints = { "front": "rh_wall", "edge": "rh_wall", "back": None }
    # Floor and ceiling.
    sector( model, "rh_floor", R_PLINTH, R_WALL + 2, 0, 360, 0.0 )
    model.prism( ngon( R_WALL_OUT + 5 ), -12, 0, {}, STONE )
    sector( model, "rh_ceiling", 300, R_WALL + 2, 0, 360, ROTUNDA_TOP, up=False )
    model.prism( ngon( R_WALL_OUT + 5 ), ROTUNDA_TOP, ROTUNDA_TOP + 20, {}, STONE )
    # The coffer over the tank: a glowing ring round its steel rim.
    drum( model, "rh_gunmetal", 300, 0, 360, ROTUNDA_TOP, ROTUNDA_TOP + 40, inward=True )
    sector( model, "rh_frosted_lit", 262, 300, 0, 360, ROTUNDA_TOP + 40, up=False )
    drum( model, "rh_gunmetal", 262, 0, 360, 520, ROTUNDA_TOP + 40, inward=False )

    # The walls: straight pieces at the openings and the tanks' windows, round between them.
    pieces = [ ( a, EXIT_HALF, "exit" ) for a in EXITS ] + [ ( a, ALCOVE_HALF, "alcove" ) for a in ALCOVES ] \
        + [ ( a, UPPER_HALF, "upper" ) for a in UPPER ]
    pieces.sort()
    for k, ( a, half, kind ) in enumerate( pieces ):
        nxt = pieces[( k + 1 ) % len( pieces )]
        b_start = nxt[0] - nxt[1] + ( 360 if k == len( pieces ) - 1 else 0 )
        arc_wall( model, R_WALL, R_WALL_OUT, a + half, b_start, 0, ROTUNDA_TOP, wall_paints )
        fr, length, d = chord_frame( a, half, R_WALL )
        thick = R_WALL_OUT + 2 - d
        mid = length / 2
        if kind == "exit":
            holes = [ Hole( mid - CORRIDOR, mid + CORRIDOR, 0, CORRIDOR_H, frame="rh_gunmetal" ) ]
            if a in ( 0.0, 180.0 ):
                fwall( model, fr, 0, length, thick, 0, L1 - SLAB, holes, wall_paints, ends=False, top=False )
                fwall( model, fr, 0, length, thick, L1 - SLAB, ROTUNDA_TOP,
                       [ Hole( mid - CORRIDOR, mid + CORRIDOR, L1, L1 + CORRIDOR_H, frame="rh_gunmetal", sill="rh_floor" ) ],
                       wall_paints, ends=False )
            else:
                fwall( model, fr, 0, length, thick, 0, ROTUNDA_TOP, holes, wall_paints, ends=False )
        elif kind == "alcove":
            h = Hole( 26, length - 26, 40, 168, rise=18, glass="alcove", frame="rh_gunmetal", sill="rh_sand" )
            fwall( model, fr, 0, length, thick, 0, ROTUNDA_TOP, [ h ], wall_paints, ends=False )
            tank_box( inside, fr, 10, length - 10, -thick - 130, -thick, 20, 200, rng, floor_z=46 )
            lights.append( light( f"Rotunda alcove {int( a )}", fr.p( mid, -thick - 60, 185 ), COOL, 260 ) )
        else:
            h = Hole( 24, length - 24, 240, 500, rise=30, glass="rotunda_ring", frame="rh_gunmetal", sill="rh_sand" )
            fwall( model, fr, 0, length, thick, 0, ROTUNDA_TOP, [ h ], wall_paints, ends=False )
            tank_box( inside, fr, 8, length - 8, -thick - 170, -thick, 220, 540, rng, floor_z=246 )
            lights.append( light( f"Rotunda tank {a:g}", fr.p( mid, -thick - 80, 520 ), COOL, 380 ) )

    # The central tank: a plinth, the glass drum, steel rims, and the reef inside.
    model.cylinder( ( 0, 0 ), R_PLINTH, 0, 36, { "side": "rh_wall_dark", "top": "rh_steel" }, sides=48, surface=STONE )
    drum( model, tank_paint( "rotunda" ), R_TANK, 0, 360, 36, 520, inward=False, steps=72, smooth=True )
    model.prism( ngon( R_TANK, 48 ), 36, 520, {}, GLASS )
    for z0, z1 in ( ( 36, 44 ), ( 512, 520 ) ):
        drum( model, "rh_steel", R_TANK + 3, 0, 360, z0, z1, inward=False, steps=48 )
        sector( model, "rh_steel", R_TANK, R_TANK + 3, 0, 360, z1 )
        sector( model, "rh_steel", R_TANK, R_TANK + 3, 0, 360, z0, up=False )
    for k in range( 12 ):
        # The glass's joints: thin steel strips up the drum.
        a = 15 + 30 * k
        fr, length, d = chord_frame( a, 0.35, R_TANK + 0.8 )
        fbox( model, fr, 0, length, -0.8, 0.6, 44, 512, "rh_steel" )
    sector( inside, "rh_sand", 0, R_TANK - 0.5, 0, 360, 44 )
    lamp_lid( inside, ( 0, 0 ), R_TANK, 540 )
    drum( inside, "rh_steel_blue", 34, 0, 360, 44, 540, inward=False, steps=16 )
    water_cylinder( inside, ( 0, 0 ), R_TANK - 3, 44, 530 )
    obstacle( inside, ( 0, 0, 44 ), 35, 500, 0.0 )
    rock( inside, ( 0, 0, 44 ), 135, 360, rng )
    for k in range( 7 ):
        a = rng.uniform( 0, 360 )
        rock( inside, ( *polar( a, rng.uniform( 150, 205 ) ), 44 ), rng.uniform( 30, 46 ), rng.uniform( 50, 110 ), rng )
    for k in range( 26 ):
        coral( inside, ( *polar( rng.uniform( 0, 360 ), rng.uniform( 120, 235 ) ), 44 ), rng.uniform( 10, 20 ), rng )
    for k in range( 14 ):
        sea_grass( inside, ( *polar( rng.uniform( 0, 360 ), rng.uniform( 200, 245 ) ), 44 ), rng )
    for k in range( 9 ):
        kelp( inside, ( *polar( rng.uniform( 0, 360 ), rng.uniform( 140, 225 ) ), 44 ), rng.uniform( 250, 420 ), rng )
    for k in range( 6 ):
        lights.append( light( f"Rotunda tank glow {k}", ( *polar( 30 + 60 * k, 330 ), 300 ), COOL, 420 ) )
    # Six steel columns round the drum, from the floor to the coffer, over every other glass joint, as the
    # reference's tank stands in its ring of columns.
    for k in range( 6 ):
        a = math.radians( 15 + 60 * k )
        out = ( math.cos( a ), math.sin( a ) )
        fr = Frame( ( out[0] * 276, out[1] * 276 ), ( -out[1], out[0] ), out )
        fbox( model, fr, -13, 13, -13, 13, 0, ROTUNDA_TOP, { "default": "rh_steel", "top": None }, METAL )
        for z0, z1 in ( ( 0, 10 ), ( ROTUNDA_TOP - 14, ROTUNDA_TOP ), ( L1 - 8, L1 ) ):
            fbox( model, fr, -15, 15, -15, 15, z0, z1, { "default": "rh_gunmetal", "top": None, "bottom": None } )

    # The balcony ring, its fascia and railing, and the soffit's downlights.
    sector( model, "rh_floor", R_BALCONY, R_WALL + 2, 0, 360, L1 )
    sector( model, "rh_ceiling", R_BALCONY, R_WALL + 2, 0, 360, L1 - SLAB, up=False )
    for k in range( 90 ):
        a, b = 4 * k, 4 * ( k + 1 )
        model.hull( [ ( *polar( x, r ), z ) for x in ( a, b ) for r in ( R_BALCONY, R_WALL + 2 ) for z in ( L1 - SLAB, L1 ) ], STONE )
    drum( model, "rh_gunmetal", R_BALCONY - 1.5, 0, 360, L1 - SLAB - 4, L1 + 1.5, inward=False, steps=90 )
    drum( model, "rh_led_cool", R_BALCONY - 1.6, 0, 360, L1 - SLAB - 2, L1 - SLAB + 0.5, inward=False, steps=90 )
    sector( model, "rh_gunmetal", R_BALCONY - 1.5, R_BALCONY, 0, 360, L1 + 1.5 )
    sector( model, "rh_gunmetal", R_BALCONY - 1.5, R_BALCONY, 0, 360, L1 - SLAB - 4, up=False )
    gaps = []
    for foot, top in STAIRS:
        span = ( top - foot ) * 3 / 26
        gaps.append( tuple( sorted( ( top - span - 1.0 * np.sign( span ), top ) ) ) )
    edges = sorted( [ 0.0 ] + [ x for g in gaps for x in g ] + [ 360.0 ] )
    for k in range( 0, len( edges ), 2 ):
        arc_railing( model, R_BALCONY + 2, edges[k], edges[k + 1], L1 )
    for k in range( 30 ):
        downlight_rings( model, polar( 6 + 12 * k, 725 ), L1 - SLAB )
    for k in range( 12 ):
        a = 15 + 30 * k
        lights.append( light( f"Rotunda under balcony {k}", ( *polar( a, 725 ), 180 ), WARM, 300 ) )
        lights.append( light( f"Rotunda balcony {k}", ( *polar( a, 740 ), 520 ), WARM, 380 ) )

    # The curved stairs to the balcony.
    for foot, top in STAIRS:
        round_stair( model, *STAIR_BAND, foot, top, 0, L1 )
        sloped_arc_railing( model, STAIR_BAND[0] + 2, foot, top, 0, L1 )
        span = ( top - foot ) * 4 / 26
        sloped_arc_railing( model, STAIR_BAND[1] - 2, foot, top - span, 0, L1 * 22 / 26 )

    # The floor: the emblem, benches facing the tank, display tanks for cover, information stands.
    decal( model, "rh_emblem", -130, 130, -560, -300, 0.0 )
    for a in ( 205.0, 335.0 ):
        bench( model, polar( a, 420 ), a + 90 )
    for a in ( 160.0, 200.0, 340.0, 20.0 ):
        display_case( model, polar( a, 430 ), ( 44, 44 ), tank_name="display", rng=rng, inside=inside )
    for a in ( 250.0, 290.0 ):
        lectern( model, polar( a, 360 ), a + 90 )



# ---------------------------------------------------------------------------------------------------------------------
# Mirroring, and rectangular rooms

def mirror_model( model, flip_e=False, flip_n=False, paint_map=None ):
    """ A copy turned over east to west (flip_e), north to south (flip_n) or both (a half turn). A single flip
    reverses every polygon's order so it still faces out, as Model.mirrored does. paint_map repaints. """
    paint_map = paint_map or {}
    flip = np.array( ( -1.0 if flip_e else 1.0, -1.0 if flip_n else 1.0, 1.0 ) )
    turn = flip_e != flip_n
    out = Model()
    out.material_overrides = dict( model.material_overrides )
    out.tile_overrides = dict( model.tile_overrides )
    out.grain_paints = set( model.grain_paints )
    for paint, items in model.polygons.items():
        target = paint_map.get( paint, paint )
        for index, ( points, normal ) in enumerate( items ):
            pts = [ p * flip for p in points ]
            uv = model.polygon_uvs.get( ( paint, index ) )
            normals = model.polygon_normals.get( ( paint, index ) )
            if normals is not None:
                normals = [ n * flip for n in normals ]
            if turn:
                pts = pts[:1] + pts[:0:-1]
                uv = None if uv is None else uv[:1] + uv[:0:-1]
                normals = None if normals is None else normals[:1] + normals[:0:-1]
            key = ( target, len( out.polygons[target] ) )
            if uv is not None:
                out.polygon_uvs[key] = uv
            if normals is not None:
                out.polygon_normals[key] = normals
            out.polygons[target].append( ( pts, normal * flip ) )
    for centre, axes, size, surface in model.boxes:
        a0, a1, a2 = ( np.asarray( a, float ) * flip for a in axes )
        if turn:
            a1 = -a1
        out.boxes.append( ( np.asarray( centre, float ) * flip, ( tuple( a0 ), tuple( a1 ), tuple( a2 ) ), size, surface ) )
    for points, surface in model.hulls:
        out.hulls.append( ( [ tuple( np.asarray( p, float ) * flip ) for p in points ], surface ) )
    for prop in model.props:
        assert "fauna" in prop
        mirrored = { **prop, "position": tuple( np.asarray( prop["position"], float ) * flip ),
                     "along": tuple( np.asarray( prop.get( "along", ( 1.0, 0.0 ) ), float ) * flip[:2] ) }
        if prop.get( "hole" ):
            mirrored["hole"] = ( prop["hole"][0], tuple( np.asarray( prop["hole"][1], float ) * flip ) )
        out.props.append( mirrored )
    return out


def mirror_lights( lights, flip_e, flip_n, suffix ):
    flip = np.array( ( -1.0 if flip_e else 1.0, -1.0 if flip_n else 1.0, 1.0 ) )
    return [ ( f"{name} {suffix}", tuple( np.asarray( pos ) * flip ), colour, radius, shadows )
             for name, pos, colour, radius, shadows in lights ]


def build_mirrored( builder, rng, flips, paint_maps=None ):
    """ Runs builder( model, inside, lights, rng ) once and adds its mirror images: flips is a list of
    ( flip_e, flip_n, suffix ). Returns the three lists' worth. """
    model, inside, lights = Model(), Model(), []
    _sconces.clear()
    builder( model, inside, lights, rng )
    lights += _sconces
    _sconces.clear()
    out_m, out_i, out_l = Model(), Model(), list( lights )
    out_m.extend( model )
    out_i.extend( inside )
    for k, ( fe, fn, suffix ) in enumerate( flips ):
        pm = ( paint_maps or {} ).get( suffix )
        out_m.extend( mirror_model( model, fe, fn, pm ) )
        out_i.extend( mirror_model( inside, fe, fn, pm ) )
        out_l += mirror_lights( lights, fe, fn, suffix )
    return out_m, out_i, out_l


WALL = { "front": "rh_wall", "edge": "rh_wall", "back": None }
WALL_DARK = { "front": "rh_wall_dark", "edge": "rh_wall_dark", "back": None }
SERVICE = { "front": "rh_smooth", "edge": "rh_smooth", "back": None }


def side_frame( rect, side ):
    """ The frame of a rectangle's side wall, its front facing into the rectangle: ( frame, the plan coordinate at
    u 0, its length ). u runs east on the north and south sides, north on the east and west ones. """
    e0, e1, n0, n1 = rect
    if side == "n":
        return Frame( ( e0, n1 ), ( 1, 0 ), ( 0, -1 ) ), e0, e1 - e0
    if side == "s":
        return Frame( ( e0, n0 ), ( 1, 0 ), ( 0, 1 ) ), e0, e1 - e0
    if side == "e":
        return Frame( ( e1, n0 ), ( 0, 1 ), ( -1, 0 ) ), n0, n1 - n0
    return Frame( ( e0, n0 ), ( 0, 1 ), ( 1, 0 ) ), n0, n1 - n0


def shifted( h, base ):
    return Hole( h.u0 - base, h.u1 - base, h.z0, h.z1, h.rise, h.glass, h.glass_w, h.frame, h.sill )


def side_wall( model, rect, side, z0, z1, holes=(), paints=WALL, thick=20.0, span=None, top=False, surface=STONE ):
    """ A rectangle's side wall from z0 to z1, holes given in plan coordinates along it. span limits it ( plan ). """
    fr, base, length = side_frame( rect, side )
    u0, u1 = ( 0.0, length ) if span is None else ( span[0] - base, span[1] - base )
    fwall( model, fr, u0, u1, thick, z0, z1, [ shifted( h, base ) for h in holes ], paints, surface, ends=False, top=top )
    return fr, base


def window_tank( inside, lights, rect, side, h, rng, depth, name, thick=20.0, extra=12.0, top=None, bottom=None,
                 decor="reef", light_r=None ):
    """ A tank's insides behind a window ( a Hole in plan coordinates ) in a rectangle's side wall, and its lamp. """
    fr, base, _ = side_frame( rect, side )
    u0, u1 = h.u0 - base - extra, h.u1 - base + extra
    z_top = h.z1 + 30 if top is None else top
    z_bottom = h.z0 - 30 if bottom is None else bottom
    tank_box( inside, fr, u0, u1, -thick - depth, -thick, z_bottom, z_top, rng, floor_z=h.z0 + 6, decor=decor )
    # A wide tank has a lamp over each half, as a show tank has a row of them over its length.
    lamps = 1 if u1 - u0 < 400 else 2
    for k in range( lamps ):
        u = u0 + ( u1 - u0 ) * ( k + 0.5 ) / lamps
        lights.append( light( name if lamps == 1 else f"{name} {k}", fr.p( u, -thick - depth * 0.45, z_top - 14 ), COOL,
                              light_r or max( 180.0, min( 520.0, ( u1 - u0 ) / lamps * 0.8 + depth ) ) ) )
    # The tank's light coming out through the glass into the room: a soft blue wash on the floor and the facing wall.
    if h.u1 - h.u0 >= 120:
        lights.append( light( f"{name} spill", fr.p( ( u0 + u1 ) / 2, 70, ( h.z0 + h.z1 ) / 2 ), SPILL,
                              min( 480.0, 220.0 + ( h.u1 - h.u0 ) * 0.5 ) ) )
    return fr, base


def floor_rect( model, e0, e1, n0, n1, z, paint="rh_floor", thick=SLAB, under=None, edge=None, surface=STONE ):
    model.box( ( e0, n0, z - thick ), ( e1, n1, z ), { "+z": paint, "-z": under, "default": edge }, surface )


def ceiling_rect( model, e0, e1, n0, n1, z, paint="rh_ceiling", thick=20.0 ):
    model.box( ( e0, n0, z ), ( e1, n1, z + thick ), { "-z": paint, "default": None }, STONE )


def slab_rect( model, e0, e1, n0, n1, z_top, thick=SLAB, fascia=( ), led=True ):
    """ An upper floor: floor on top, ceiling under, and a gunmetal fascia (with a cool LED strip under it) on the
    sides listed in fascia ( 'n', 's', 'e', 'w' ): the ones facing a void. """
    model.box( ( e0, n0, z_top - thick ), ( e1, n1, z_top ), { "+z": "rh_floor", "-z": "rh_ceiling", "default": None }, STONE )
    rect = ( e0, e1, n0, n1 )
    for side in fascia:
        fr, base, length = side_frame( rect, side )
        fbox( model, fr, -0.5, length + 0.5, -2.0, 0.0, z_top - thick - 4, z_top + 1.5,
              { "back": "rh_gunmetal", "top": "rh_gunmetal", "bottom": "rh_gunmetal", "default": None } )
        if led:
            facing( model, "rh_led_cool", [ fr.p( -0.5, -2.05, z_top - thick - 3.5 ), fr.p( length + 0.5, -2.05, z_top - thick - 3.5 ),
                                            fr.p( length + 0.5, -2.05, z_top - thick - 1.0 ), fr.p( -0.5, -2.05, z_top - thick - 1.0 ) ],
                    fr.vec( 0, -1, 0 ) )


def downlight_line( model, p0, p1, z, every=110.0 ):
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    count = max( 1, int( np.linalg.norm( p1 - p0 ) / every ) )
    for k in range( count ):
        downlight_rings( model, p0 + ( p1 - p0 ) * ( k + 0.5 ) / count, z )


SCONCE = "1.15,0.78,0.5,1"     # a wall light's wash on its wall
_sconces = []                   # the wall lights the room being built has placed ( build_mirrored collects them )


def sconce( model, fr, u, z, w=0.0 ):
    """ A wall light: a small gunmetal box with a warm glowing face, on a frame wall's front, and a small unshadowed
    light just off it, so it washes the wall above and below as the references' do. """
    fbox( model, fr, u - 3.5, u + 3.5, w, w + 3.0, z, z + 16, { "default": "rh_gunmetal", "front": "rh_led_warm" } )
    _sconces.append( light( "Wall light", fr.p( u, w + 8.0, z + 8 ), SCONCE, 130.0 ) )


def baseboard( model, fr, u0, u1, w=0.0, height=6.0 ):
    fbox( model, fr, u0, u1, w, w + 1.0, 0.0, height, { "default": "rh_gunmetal", "back": None, "bottom": None } )


def line_strip( model, e0, e1, n0, n1, z=0.0, paint="rh_line" ):
    model.polygon( paint, [ ( e0, n0, z + 0.15 ), ( e1, n0, z + 0.15 ), ( e1, n1, z + 0.15 ), ( e0, n1, z + 0.15 ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# The galleries: the middle lane between the lobby and the control room and the Rotunda, on two floors

ROT_CHORD_IN = R_WALL * math.cos( math.radians( EXIT_HALF ) )      # the rotunda's exits' inner face
ROT_CHORD_OUT = R_WALL_OUT + 2.0                                     # and its back
LOBBY_FACE = -1720.0       # the lobby's east wall's front ( its back at -1700 )
CONTROL_FACE = 1720.0      # the control room's west wall's front


def gallery_west( model, inside, lights, rng ):
    """ The West Gallery: e -1700 to the rotunda, 220 wide, a corridor on the ground floor and one over it, lined
    with small tanks. The East Gallery is its mirror image. """
    e0, e1 = LOBBY_FACE + 20, -ROT_CHORD_OUT
    rect = ( e0, e1, -CORRIDOR, CORRIDOR )
    floor_rect( model, LOBBY_FACE, -ROT_CHORD_IN, -CORRIDOR, CORRIDOR, 0.0 )
    model.box( ( e0, -CORRIDOR, CORRIDOR_H ), ( e1, CORRIDOR, L1 ), { "-z": "rh_ceiling", "+z": "rh_floor", "default": None }, STONE )
    ceiling_rect( model, e0, e1, -CORRIDOR, CORRIDOR, L1 + CORRIDOR_H )
    centres = ( -1580.0, -1380.0, -1180.0 )
    for side in ( "n", "s" ):
        low = [ Hole( c - 76, c + 76, 34, 150, rise=16, glass="gallery", frame="rh_gunmetal", sill="rh_gunmetal" ) for c in centres ]
        high = [ Hole( c - 76, c + 76, L1 + 34, L1 + 150, rise=16, glass="gallery", frame="rh_gunmetal", sill="rh_gunmetal" )
                 for c in centres ]
        fr, base = side_wall( model, rect, side, 0, L1 - SLAB, low )
        side_wall( model, rect, side, L1 - SLAB, L1 + CORRIDOR_H, high )
        for k, ( a, b ) in enumerate( zip( low, high ) ):
            window_tank( inside, lights, rect, side, a, rng, 96, f"West Gallery tank {side}{k}", top=L1 - SLAB - 8, bottom=0 )
            window_tank( inside, lights, rect, side, b, rng, 96, f"West Gallery upper tank {side}{k}", top=L1 + CORRIDOR_H - 8,
                         bottom=L1 - SLAB + 4 )
        for z0 in ( 0.0, L1 ):
            baseboard( model, fr, 0, e1 - e0 ) if z0 == 0 else fbox( model, fr, 0, e1 - e0, 0, 1.0, L1, L1 + 6,
                                                                       { "default": "rh_gunmetal", "back": None, "bottom": None } )
            for u in ( 20.0, 220.0, 420.0, 620.0, e1 - e0 - 20 ):
                sconce( model, fr, u, z0 + 112 )
    for z in ( CORRIDOR_H, L1 + CORRIDOR_H ):
        downlight_line( model, ( e0, 0 ), ( e1, 0 ), z, every=100 )
        for e in ( -1560.0, -1290.0, -1020.0 ):
            lights.append( light( f"West Gallery {int( z )} {int( e )}", ( e, 0, z - 20 ), WARM, 300 ) )
    # Cover: a display case mid-way on the ground floor; a bench and a display case upstairs.
    display_case( model, ( -1290, 0 ), ( 44, 44 ), tank_name="display", rng=rng, inside=inside )
    skip_cases( rng )
    drain( model, -1470, -1460, -100, 100 )
    bench( model, ( -1480, -92 ), 0.0, z=L1 )
    display_case( model, ( -1100, 70 ), ( 40, 40 ), z=L1, tank_name="display", rng=rng, inside=inside )


def rotunda_north( model, inside, lights, rng ):
    """ The Rotunda's north passage to the Filter Hall, a tank either side. The south passage is its mirror image. """
    n0, n1 = ROT_CHORD_OUT, 1080.0
    rect = ( -CORRIDOR, CORRIDOR, n0, n1 )
    floor_rect( model, -CORRIDOR, CORRIDOR, ROT_CHORD_IN, 1100.0, 0.0 )
    ceiling_rect( model, -CORRIDOR, CORRIDOR, n0, n1, CORRIDOR_H )
    for side in ( "e", "w" ):
        h = Hole( 920, 1040, 32, 150, rise=14, glass="gallery", frame="rh_gunmetal", sill="rh_gunmetal" )
        fr, base = side_wall( model, rect, side, 0, CORRIDOR_H, [ h ] )
        window_tank( inside, lights, rect, side, h, rng, 96, f"North Passage tank {side}", top=CORRIDOR_H - 6, bottom=0 )
        baseboard( model, fr, 0, n1 - n0 )
        sconce( model, fr, 18, 112 )
        sconce( model, fr, n1 - n0 - 18, 112 )
    downlight_line( model, ( 0, n0 ), ( 0, n1 ), CORRIDOR_H, every=100 )
    lights.append( light( "North Passage", ( 0, 980, 160 ), WARM, 260 ) )
    drain( model, -100, 100, 1000, 1010 )


def service_northwest( model, inside, lights, rng ):
    """ The north-west service corridor: east out of the lobby ( A ), then north into the Filter Hall ( B ). The other
    three are its mirror images. """
    a = ( LOBBY_FACE + 20, -1120.0, 500.0, 720.0 )
    b = ( -1120.0, -900.0, 500.0, 1080.0 )
    floor_rect( model, LOBBY_FACE, -1120.0, 500.0, 720.0, 0.0 )
    floor_rect( model, -1120.0, -900.0, 500.0, 1100.0, 0.0 )
    ceiling_rect( model, a[0], a[1], a[2], a[3], CORRIDOR_H )
    ceiling_rect( model, b[0], b[1], b[2], b[3], CORRIDOR_H )
    whole = ( a[0], b[1], 500.0, 720.0 )
    fs, _ = side_wall( model, whole, "s", 0, CORRIDOR_H, paints=SERVICE )
    fn, _ = side_wall( model, a, "n", 0, CORRIDOR_H, paints=SERVICE )
    fw, _ = side_wall( model, b, "w", 0, CORRIDOR_H, paints=SERVICE, span=( 720.0, 1080.0 ) )
    fe, _ = side_wall( model, b, "e", 0, CORRIDOR_H, paints=SERVICE )
    for fr, u0, u1 in ( ( fs, 0, b[1] - a[0] ), ( fn, 0, a[1] - a[0] ), ( fw, 220, 580 ), ( fe, 0, 580 ) ):
        baseboard( model, fr, u0, u1, height=8 )
    # Yellow lines along the walls, and the pipes the service corridors carry.
    line_strip( model, a[0] + 10, b[1] - 16, 512, 515 )
    line_strip( model, a[0] + 10, a[1] + 12, 705, 708 )
    line_strip( model, -1108, -1105, 708, 1080 )
    line_strip( model, -915, -912, 515, 1080 )
    pipe_run( model, [ ( -1690, 514, CORRIDOR_H ), ( -1690, 514, 150 ), ( -918, 514, 150 ), ( -918, 1050, 150 ), ( -918, 1050, CORRIDOR_H ) ], 5.5 )
    pipe_run( model, [ ( -1676, 528, CORRIDOR_H ), ( -1676, 528, 162 ), ( -932, 528, 162 ), ( -932, 1036, 162 ), ( -932, 1036, CORRIDOR_H ) ], 3.5, paint="rh_pipe_dark" )
    for e in ( -1600.0, -1300.0, -1000.0 ):
        fbox( model, Frame( ( e, 500 ), ( 1, 0 ), ( 0, 1 ) ), -2, 2, 0, 34, 140, 144, "rh_gunmetal" )
    skip_cases( rng )
    for e in ( -1640.0, -1400.0, -1180.0 ):
        downlight_rings( model, ( e, 610 ), CORRIDOR_H )
    for n in ( 640.0, 800.0, 960.0 ):
        downlight_rings( model, ( -1010, n ), CORRIDOR_H )
    lights.append( light( "Service NW A", ( -1430, 610, 160 ), WARM, 300 ) )
    lights.append( light( "Service NW corner", ( -1010, 610, 160 ), WARM, 240 ) )
    lights.append( light( "Service NW B", ( -1010, 920, 160 ), WARM, 260 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The Lobby (reference 4, Red Team's spawn): a three-storey atrium with a ring balcony, twin stairs, the reception desk
# round a cylinder tank, a round coral display, a whale skeleton overhead and tanks on every wall

LOBBY = ( -2900.0, LOBBY_FACE, -1000.0, 1000.0 )
LOBBY_TOP = 620.0
LOBBY_VOID = ( -2720.0, -1880.0, -820.0, 820.0 )
LOBBY_STAIR = ( -2720.0, -2440.0, 420.0, 600.0 )      # the north flight, climbing west; the south one mirrors it
LOBBY_TANK = ( -2420.0, 0.0 )
LOBBY_DISPLAY = ( -1980.0, 0.0 )


# The entrance doors on the west wall, behind Red Team's spawn (2026-10-08, after the user's picture): three closed pairs
# of glass doors in dark anodised frames, each in an anthracite portal in a wall of slate-grey cladding panels, with
# bronze planters between them. Each pair's glass carries a frosted film (reefhall_materials.film: two wavy lines across
# both leaves, a jellyfish on the right one), and through it there's a dim gallery with tanks, which nobody can reach.
DOOR_S = 1.25                                  # the film's picture is drawn for a 95" leaf: these are 119" ( 3 m )
DOOR_PAIRS = ( -197.5, 0.0, 197.5 )           # the pairs' middles ( plan n )
DOOR_HALF = 51.0 * DOOR_S                     # the opening's half width
DOOR_TOP = 100.0 * DOOR_S                     # the opening's head
DOOR_PORTAL = 6.0 * DOOR_S                    # the anthracite band round it
DOOR_GALLERY = ( -3200.0, -2920.0, -400.0, 400.0 )
DOOR_GALLERY_TOP = 180.0


def uv_quad( model, paint, points, uvs, towards, both_sides=False ):
    """ A polygon with its own uvs ( one per point ), wound to face towards: the points and uvs turn round together. """
    pts = [ np.asarray( p, float ) for p in points ]
    uvs = [ tuple( map( float, t ) ) for t in uvs ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts, uvs = pts[:1] + pts[:0:-1], uvs[:1] + uvs[:0:-1]
    model.polygon( paint, pts, uv=uvs, both_sides=both_sides )


def door_pair( model, fr, c ):
    """ A closed pair of glass doors in a wall opening at u c ( c +- DOOR_HALF, up to DOOR_TOP ), its front the frame's
    front: the fixed frame, two leaves ( stiles 4.5" and rails 6", scaled ), the glass and its film, the pull bars on
    the meeting stiles, the closer's cover and the threshold. The leaves' frames are drawn only: one glass box holds
    the opening ( rounds go through it into the gallery, whose walls stop them ). """
    S = DOOR_S
    half, top = DOOR_HALF, DOOR_TOP
    gap, g_out = RM.FILM_GAP * S, RM.FILM_W / 2 * S          # the glass's inner and outer edges, out from c
    g_z0, g_z1 = 6.5 * S, ( 6.5 + RM.FILM_H ) * S
    leaf_in, leaf_out = 0.125 * S, 48.0 * S
    leaf_z1 = 95.5 * S
    lw0, lw1 = -7.0, -5.0                                     # the leaves' back and front
    frame = { "default": "rh_anodised" }
    # The fixed frame: the jambs and the head.
    fbox( model, fr, c - half, c - leaf_out, -12.0, -2.0, 0.0, top, frame, skip=( "bottom", ) )
    fbox( model, fr, c + leaf_out, c + half, -12.0, -2.0, 0.0, top, frame, skip=( "bottom", ) )
    fbox( model, fr, c - leaf_out, c + leaf_out, -12.0, -2.0, leaf_z1, top, frame, skip=( "top", ) )
    fbox( model, fr, c - half, c + half, lw0, lw1, 0.0, top, None, GLASS )
    # The threshold, and the closer's cover on the head.
    fbox( model, fr, c - half, c + half, -20.0, 0.0, -0.5, 0.35, { "top": "rh_stainless", "default": None } )
    fbox( model, fr, c - 13 * S, c + 13 * S, -2.0, -1.2, leaf_z1 + 0.6, leaf_z1 + 2.6, "rh_stainless", skip=( "back", ) )
    for s in ( -1, 1 ):
        def span( a, b ):
            return c + min( s * a, s * b ), c + max( s * a, s * b )
        for a, b in ( ( leaf_in, gap ), ( g_out, leaf_out ) ):
            fbox( model, fr, *span( a, b ), lw0, lw1, 0.5, leaf_z1, frame )
        u0, u1 = span( gap, g_out )
        fbox( model, fr, u0, u1, lw0, lw1, 0.5, g_z0, frame, skip=( "left", "right" ) )
        fbox( model, fr, u0, u1, lw0, lw1, g_z1, leaf_z1, frame, skip=( "left", "right" ) )
        # The glass, and the film on its lobby side: one picture across the pair, each leaf its share of it.
        gw = ( lw0 + lw1 ) / 2
        quad = lambda w: [ fr.p( u0, w, g_z0 ), fr.p( u1, w, g_z0 ), fr.p( u1, w, g_z1 ), fr.p( u0, w, g_z1 ) ]
        facing( model, "rh_glass", quad( gw ), fr.vec( 0, 1, 0 ) )
        x = lambda u: ( u - c + g_out ) / ( 2 * g_out )
        uv_quad( model, "rh_film", quad( gw + 0.08 ), [ ( x( u0 ), 0 ), ( x( u1 ), 0 ), ( x( u1 ), 1 ), ( x( u0 ), 1 ) ],
                 fr.vec( 0, 1, 0 ) )
        # The pull bar on the meeting stile, on two standoffs.
        u = c + s * 4.4 * S
        bar_w = lw1 + 3.0
        tube( model, fr.p( u, bar_w, 26.0 ), fr.p( u, bar_w, 66.0 ), 1.0, "rh_stainless", sides=12, cap=True )
        for z in ( 29.5, 62.5 ):
            tube( model, fr.p( u, lw1, z ), fr.p( u, bar_w, z ), 0.55, "rh_stainless", sides=8 )
    # The portal: an anthracite band round the opening, a little proud of the cladding.
    for a, b in ( ( c - half - DOOR_PORTAL, c - half ), ( c + half, c + half + DOOR_PORTAL ) ):
        fbox( model, fr, a, b, 0.0, 1.5, 0.0, top + DOOR_PORTAL, "rh_portal", skip=( "back", "bottom" ) )
    fbox( model, fr, c - half, c + half, 0.0, 1.5, top, top + DOOR_PORTAL, "rh_portal", skip=( "back", "left", "right" ) )


def clad( model, fr, u0, u1, z0, z1, rng, width=56.0 ):
    """ Cladding panels across u0..u1, z0..z1 on a frame wall's front, as near width wide as divides it, with shadow
    gaps between them ( the wall behind is painted dark ). Drawn only. """
    count = max( 1, round( ( u1 - u0 ) / width ) )
    for k in range( count ):
        a, b = u0 + ( u1 - u0 ) * k / count, u0 + ( u1 - u0 ) * ( k + 1 ) / count
        paint = "rh_panel" if rng.random() < 0.6 else "rh_panel_b"
        fbox( model, fr, a + 0.15, b - 0.15, 0.0, 0.75, z0 + 0.15, z1 - 0.15, paint, skip=( "back", ) )


def bronze_planter( model, centre, z=0.0, width=17.5 * DOOR_S, height=37.0 * DOOR_S, foot=0.8 ):
    """ A tall square planter tapering to its foot ( foot: its width there, a share of the top's ), bronze, with a
    rolled lip and soil a little under it. Returns the soil's height. """
    e, n = centre[:2]
    t, b, z1 = width / 2, width / 2 * foot, z + height
    corners = lambda r, zz: [ ( e - r, n - r, zz ), ( e + r, n - r, zz ), ( e + r, n + r, zz ), ( e - r, n + r, zz ) ]
    low, high = corners( b, z ), corners( t, z1 - 1.2 )
    for k in range( 4 ):
        quad = [ low[k], low[( k + 1 ) % 4], high[( k + 1 ) % 4], high[k] ]
        mid = np.mean( quad, axis=0 )
        facing( model, "rh_bronze", quad, ( mid[0] - e, mid[1] - n, 0 ) )
    model.box( ( e - t - 0.35, n - t - 0.35, z1 - 1.2 ), ( e + t + 0.35, n + t + 0.35, z1 ), { "default": "rh_bronze", "-z": None } )
    soil = z1 - 1.8
    model.box( ( e - t + 0.6, n - t + 0.6, soil - 1 ), ( e + t - 0.6, n + t - 0.6, soil ), { "+z": "rh_soil", "default": None } )
    for k in range( 4 ):
        inner = corners( t - 0.6, soil ) + corners( t - 0.6, z1 + 0.01 )
        quad = [ inner[k], inner[( k + 1 ) % 4], inner[4 + ( k + 1 ) % 4], inner[4 + k] ]
        mid = np.mean( quad, axis=0 )
        facing( model, "rh_bronze", quad, ( e - mid[0], n - mid[1], 0 ) )
    model.hull( low + corners( t + 0.35, z1 ), METAL )
    return soil


def dracaena( model, base, rng, scale=1.0, leaves=24 ):
    """ A potted dracaena: strap leaves out of a crown, the young ones upright and the old ones arching out and down,
    each channelled along its midrib and drawn from both sides ( rh_leaf: u across, v from base to tip ). Drawn only. """
    base = np.asarray( base, float )
    crown = base + ( 0, 0, 2.5 * scale )
    for k in range( leaves ):
        age = k / ( leaves - 1 )                                # 0: the youngest, at the middle
        az = k * 2.39996 + rng.uniform( -0.2, 0.2 )
        rise = math.radians( rng.uniform( 72, 84 ) - 48 * age )
        droop = math.radians( rng.uniform( 18, 34 ) + 40 * age )
        length = scale * rng.uniform( 15.0, 19.0 ) * ( 1.08 - 0.25 * age )
        width = scale * rng.uniform( 1.7, 2.2 )
        twist = rng.uniform( -0.35, 0.35 )
        side0 = np.array( ( -math.sin( az ), math.cos( az ), 0.0 ) )
        start = crown + np.array( ( math.cos( az ), math.sin( az ), 0.0 ) ) * rng.uniform( 0.2, 1.0 ) * scale \
            + ( 0, 0, rng.uniform( 0, 2.5 ) * scale * ( 1 - age ) )
        steps = 8
        mids, lefts, rights = [], [], []
        p = start.copy()
        for i in range( steps + 1 ):
            t = i / steps
            el = rise - droop * t ** 1.4
            d = np.array( ( math.cos( el ) * math.cos( az ), math.cos( el ) * math.sin( az ), math.sin( el ) ) )
            up = np.cross( d, side0 )
            ang = twist * t
            side = side0 * math.cos( ang ) + up * math.sin( ang )
            up = np.cross( d, side )
            w = width * ( 1 - t ) ** 0.55 * ( 0.32 + 0.68 * min( 1.0, t / 0.3 ) ) / 2
            mids.append( p.copy() )
            lefts.append( p - side * w + up * w * 0.35 )
            rights.append( p + side * w + up * w * 0.35 )
            if i < steps:
                t_mid = ( i + 0.5 ) / steps
                el_mid = rise - droop * t_mid ** 1.4
                p = p + np.array( ( math.cos( el_mid ) * math.cos( az ), math.cos( el_mid ) * math.sin( az ),
                                    math.sin( el_mid ) ) ) * length / steps
        for i in range( steps ):
            v0, v1 = i / steps, ( i + 1 ) / steps
            for edge, u_edge in ( ( lefts, 0.0 ), ( rights, 1.0 ) ):
                if i == steps - 1:
                    pts, uvs = [ mids[i], mids[i + 1], edge[i] ], [ ( 0.5, v0 ), ( 0.5, v1 ), ( u_edge, v0 ) ]
                else:
                    pts = [ mids[i], mids[i + 1], edge[i + 1], edge[i] ]
                    uvs = [ ( 0.5, v0 ), ( 0.5, v1 ), ( u_edge, v1 ), ( u_edge, v0 ) ]
                model.polygon( "rh_leaf", pts, uv=uvs, both_sides=True )


def door_gallery( model, inside, lights, rng ):
    """ The dim gallery behind the entrance doors' glass: tanks in its walls, columns and raised planters, as the
    user's picture shows through the doors. Closed: nobody gets in, so it has no spots, and the navmesh stops short. """
    e0, e1, n0, n1 = DOOR_GALLERY
    top = DOOR_GALLERY_TOP
    floor_rect( model, e0, e1, n0, n1, 0.0 )
    ceiling_rect( model, e0, e1, n0, n1, top, paint="rh_black", thick=16.0 )
    dark = { "front": "rh_wall_dark", "edge": "rh_gunmetal", "back": None }
    tank = lambda a, b: Hole( a, b, 22, 150, glass="gallery", frame="rh_gunmetal", sill="rh_gunmetal" )
    # A tank left of each pair's middle, and one more by the north end, which the north pair shows from the lobby.
    back = [ tank( c - 160, c - 40 ) for c in DOOR_PAIRS ] + [ tank( 250, 370 ) ]
    sides = [ tank( -3160, -3010 ) ]
    side_wall( model, DOOR_GALLERY, "w", 0, top, back, paints=dark )
    for k, h in enumerate( back ):
        window_tank( inside, lights, DOOR_GALLERY, "w", h, rng, 120, f"Door gallery tank {k}", top=top, bottom=0 )
    for side in ( "n", "s" ):
        side_wall( model, DOOR_GALLERY, side, 0, top, sides, paints=dark )
        window_tank( inside, lights, DOOR_GALLERY, side, sides[0], rng, 110, f"Door gallery {side} tank", top=top, bottom=0 )
    for c in DOOR_PAIRS:
        # A dark column, and a raised concrete planter with a dracaena behind the right leaf.
        model.box( ( -3088, c - 8, 0 ), ( -3072, c + 8, top ), { "default": "rh_gunmetal", "+z": None, "-z": None }, STONE )
        pe, pn = -3150.0, c + 62.0
        model.box( ( pe - 22, pn - 22, 0 ), ( pe + 22, pn + 22, 30 ), { "default": "rh_smooth", "+z": "rh_soil" }, STONE )
        dracaena( model, ( pe, pn, 30 ), rng, scale=1.2, leaves=22 )
        downlight_rings( model, ( pe, pn ), top )
        lights.append( light( f"Door gallery planter {int( c )}", ( pe + 10, pn, top - 16 ), "0.6,0.74,0.92,1", 150 ) )
        lights.append( light( f"Door gallery wash {int( c )}", ( -3040, c + 20, 120 ), "0.22,0.48,0.72,1", 240 ) )
    for c in ( -300.0, 0.0, 300.0 ):
        downlight_rings( model, ( -3000, c ), top )
    lights.append( light( "Door gallery fill", ( -3020, 0, 150 ), "0.3,0.55,0.8,1", 360 ) )


def banner( model, fr, u0, u1, z0, z1, paint, w=0.0 ):
    """ A cloth banner hanging on a rod a little off a wall's front. """
    facing( model, paint, [ fr.p( u0, w + 3.0, z0 ), fr.p( u1, w + 3.0, z0 ), fr.p( u1, w + 3.0, z1 ), fr.p( u0, w + 3.0, z1 ) ],
            fr.vec( 0, 1, 0 ) )
    facing( model, "rh_pad_dark", [ fr.p( u0, w + 2.9, z0 ), fr.p( u1, w + 2.9, z0 ), fr.p( u1, w + 2.9, z1 ), fr.p( u0, w + 2.9, z1 ) ],
            fr.vec( 0, -1, 0 ) )
    tube( model, fr.p( u0 - 6, w + 3.0, z1 + 1.5 ), fr.p( u1 + 6, w + 3.0, z1 + 1.5 ), 1.4, "rh_brass", sides=8, cap=True )
    for u in ( u0 - 3, u1 + 3 ):
        fbox( model, fr, u - 1, u + 1, w, w + 3.0, z1, z1 + 3.5, "rh_gunmetal" )


def mullions( model, fr, u0, u1, z0, z1, count, width=10.0 ):
    """ Upright gunmetal bars across a window's front, splitting it into count panes. """
    for k in range( 1, count ):
        u = u0 + ( u1 - u0 ) * k / count
        fbox( model, fr, u - width / 2, u + width / 2, -7.0, 1.5, z0, z1, "rh_gunmetal", skip=( "back", ) )


def lobby_north( model, inside, lights, rng ):
    """ The lobby's north half (n > 0): its north wall, balcony, stair and the things beside them. The south half is
    its mirror image (the jellyfish banner where the manta hangs). """
    e0, e1, n0, n1 = LOBBY
    v_e0, v_e1, v_n0, v_n1 = LOBBY_VOID
    # The north wall: two arched windows under the balcony, two tall ones over it with a banner on the pier between.
    low = [ Hole( -2650, -2410, 30, 170, rise=24, glass="lobby", frame="rh_gunmetal", sill="rh_gunmetal" ),
            Hole( -2190, -1950, 30, 170, rise=24, glass="lobby", frame="rh_gunmetal", sill="rh_gunmetal" ) ]
    high = [ Hole( -2700, -2390, L1 + 20, 600, glass="lobby", frame="rh_gunmetal", sill="rh_gunmetal" ),
             Hole( -2230, -1920, L1 + 20, 600, glass="lobby", frame="rh_gunmetal", sill="rh_gunmetal" ) ]
    fr, base = side_wall( model, LOBBY, "n", 0, L1 - SLAB, low )
    side_wall( model, LOBBY, "n", L1 - SLAB, LOBBY_TOP, high )
    for k, h in enumerate( low ):
        window_tank( inside, lights, LOBBY, "n", h, rng, 120, f"Lobby low tank {k}", top=L1 - SLAB - 8, bottom=0 )
    for k, h in enumerate( high ):
        window_tank( inside, lights, LOBBY, "n", h, rng, 240, f"Lobby tank {k}", top=LOBBY_TOP, bottom=L1 - SLAB + 4 )
        mullions( model, fr, h.u0 - base, h.u1 - base, h.z0, h.z1, 2 )
    banner( model, fr, -2360 - base, -2260 - base, 330, 560, "rh_banner_manta" )
    baseboard( model, fr, 0, e1 - e0 )
    fbox( model, fr, 0, e1 - e0, 0, 1.0, L1, L1 + 6, { "default": "rh_gunmetal", "back": None, "bottom": None } )
    for u in ( -2780.0, -2300.0, -1820.0 ):
        sconce( model, fr, u - base, 110 )
    for u in ( -2780.0, -1820.0 ):
        sconce( model, fr, u - base, L1 + 120 )

    # The balcony along the north wall, its fascia and railing over the void.
    model.box( ( e0, v_n1, L1 - SLAB ), ( e1, n1, L1 ), { "+z": "rh_floor", "-z": "rh_ceiling", "default": None }, STONE )
    fr_s, _, _ = side_frame( ( v_e0, v_e1, v_n1, n1 ), "s" )
    fascia( model, fr_s, 0, v_e1 - v_e0 )
    railing( model, ( v_e0, v_n1 + 2 ), ( v_e1, v_n1 + 2 ), L1 )
    downlight_line( model, ( e0 + 90, 910 ), ( e1 - 80, 910 ), L1 - SLAB, every=120 )
    for e in ( -2500.0, -2100.0 ):
        lights.append( light( f"Lobby north under balcony {int( e )}", ( e, 910, 180 ), WARM, 300 ) )
        lights.append( light( f"Lobby north balcony {int( e )}", ( e, 910, 420 ), WARM, 380 ) )
    for e in ( -2810.0, -1800.0 ):
        for n in ( 350.0, 700.0 ):
            lights.append( light( f"Lobby side {int( e )} {int( n )}", ( e, n, 180 ), WARM, 300 ) )

    # The north flight: up the void's west side to the west balcony.
    s_e0, s_e1, s_n0, s_n1 = LOBBY_STAIR
    stair( model, ( s_e0, s_n0 ), ( s_e1, s_n1 ), 0.0, L1, "-e", side="rh_wall_dark" )
    stair_rail( model, ( s_e0, s_n0 + 2 ), ( s_e1, s_n1 - 2 ), 0.0, L1, "-e" )

    # Things on the floor: a display case and a drain; a bench and a display case upstairs.
    skip_cases( rng, stacks=2 )
    display_case( model, ( -2060, 330 ), ( 44, 44 ), tank_name="display", rng=rng, inside=inside )
    drain( model, -2400, -1900, 375, 385 )
    bench( model, ( -2300, 972 ), 0.0, z=L1 )
    display_case( model, ( -2850, 760 ), ( 40, 40 ), z=L1, tank_name="display", rng=rng, inside=inside )


def fascia( model, fr, u0, u1, z_top=L1, thick=SLAB, led=True ):
    """ The gunmetal edge of an upper floor over a void, on the side of a frame wall's ( inward ) frame: its face looks
    out ( -w ), with a cool LED strip under it. """
    fbox( model, fr, u0 - 0.5, u1 + 0.5, -2.0, 0.0, z_top - thick - 4, z_top + 1.5,
          { "back": "rh_gunmetal", "top": "rh_gunmetal", "bottom": "rh_gunmetal", "default": None } )
    if led:
        facing( model, "rh_led_cool", [ fr.p( u0 - 0.5, -2.05, z_top - thick - 3.5 ), fr.p( u1 + 0.5, -2.05, z_top - thick - 3.5 ),
                                        fr.p( u1 + 0.5, -2.05, z_top - thick - 1.0 ), fr.p( u0 - 0.5, -2.05, z_top - thick - 1.0 ) ],
                fr.vec( 0, -1, 0 ) )


def whale( model, centre, z, length=640.0 ):
    """ A whale's skeleton hung over the atrium on cables: vertebrae, a skull with its long jaws, ribs, flippers and
    the tail's bones, along the plan's n. """
    c = np.asarray( centre, float )
    rng = np.random.default_rng( 41 )

    def spine( t ):      # t from -1 ( tail ) to 1 ( head )
        return np.array( ( c[0], c[1] + t * length / 2, z + 24 * math.sin( t * 2.2 + 0.4 ) - 10 * t ) )

    count = 30
    for k in range( count ):
        t = -1 + 2 * k / ( count - 1 ) * 0.86
        r = 5 + 7 * math.sin( ( t + 1 ) / 1.86 * math.pi ) ** 0.7
        lump( model, spine( t ), r, r * 0.8, r * 0.95, "rh_bone", rng, segments=9, rings=5, wobble=0.04, flat_bottom=False )
        if k % 2 == 0:
            tube( model, spine( t ), spine( t ) + ( 0, 0, r * 1.8 ), r * 0.25, "rh_bone", sides=6, cap=True )
    head = spine( 0.86 ) + ( 0, length * 0.06, 0 )
    lump( model, head + ( 0, 30, 4 ), 34, 70, 22, "rh_bone", rng, segments=14, rings=7, wobble=0.05, flat_bottom=False )
    for side in ( -1, 1 ):
        pts = [ head + ( side * 26, -10, -10 ), head + ( side * 40, 50, -22 ), head + ( side * 34, 110, -26 ), head + ( side * 14, 168, -18 ) ]
        for a, b in zip( pts, pts[1:] ):
            tube( model, a, b, 5.0, "rh_bone", sides=8 )
            lump( model, b, 5.2, 5.2, 5.2, "rh_bone", rng, segments=8, rings=4, wobble=0.0, flat_bottom=False )
    for k in range( 12 ):
        t = 0.62 - k * 0.075
        p = spine( t )
        reach = 70 - abs( k - 4 ) * 4.5
        for side in ( -1, 1 ):
            pts = [ p, p + ( side * reach * 0.6, 0, -8 ), p + ( side * reach, -6, -reach * 0.6 ), p + ( side * reach * 0.8, -10, -reach * 1.1 ) ]
            for a, b in zip( pts, pts[1:] ):
                tube( model, a, b, 2.6, "rh_bone", sides=6 )
    for side in ( -1, 1 ):
        root = spine( 0.45 ) + ( side * 40, 0, -40 )
        tube( model, spine( 0.45 ), root, 4, "rh_bone", sides=6 )
        lump( model, root + ( side * 50, -10, -20 ), 55, 16, 6, "rh_bone", rng, segments=10, rings=5, wobble=0.06, flat_bottom=False )
    tail = spine( -1.0 )
    lump( model, tail + ( 0, -24, 0 ), 70, 22, 5, "rh_bone", rng, segments=12, rings=5, wobble=0.05, flat_bottom=False )
    for t in ( -0.7, -0.05, 0.6 ):
        p = spine( t )
        for side in ( -1, 1 ):
            tube( model, p + ( side * 4, 0, 6 ), ( p[0] + side * 30, p[1], LOBBY_TOP ), 0.45, "rh_steel", sides=5 )


def lobby( model, inside, lights, rng ):
    e0, e1, n0, n1 = LOBBY
    v_e0, v_e1, v_n0, v_n1 = LOBBY_VOID
    floor_rect( model, e0, e1, n0, n1, 0.0 )
    ceiling_rect( model, e0, e1, n0, n1, LOBBY_TOP )

    # The east wall: the galleries' openings, the service corridors', and two high tanks.
    door = lambda a, b, z0=0.0, z1=CORRIDOR_H, sill=None: Hole( a, b, z0, z1, frame="rh_gunmetal", sill=sill )
    fr, base = side_wall( model, LOBBY, "e", 0, L1 - SLAB, [ door( -720, -500 ), door( -CORRIDOR, CORRIDOR ), door( 500, 720 ) ] )
    high = [ Hole( -800, -250, 440, 590, glass="lobby", frame="rh_gunmetal", sill="rh_gunmetal" ),
             Hole( 250, 800, 440, 590, glass="lobby", frame="rh_gunmetal", sill="rh_gunmetal" ) ]
    side_wall( model, LOBBY, "e", L1 - SLAB, LOBBY_TOP, [ door( -CORRIDOR, CORRIDOR, L1, L1 + CORRIDOR_H, "rh_floor" ) ] + high )
    for k, h in enumerate( high ):
        window_tank( inside, lights, LOBBY, "e", h, rng, 200, f"Lobby east tank {k}", top=LOBBY_TOP, bottom=410 )
        mullions( model, fr, h.u0 - base, h.u1 - base, h.z0, h.z1, 3 )
    baseboard( model, fr, 0, n1 - n0 )
    for n in ( -880.0, -300.0, 300.0, 880.0 ):
        sconce( model, fr, n - base, 110 )

    # The west wall: the glass entrance doors behind the spawn, in a wall of cladding panels, with the gallery behind
    # them, and three tall tanks over the balcony.
    openings = [ Hole( c - DOOR_HALF, c + DOOR_HALF, 0.0, DOOR_TOP ) for c in DOOR_PAIRS ]
    fr, base = side_wall( model, LOBBY, "w", 0, L1 - SLAB, openings, paints={ "front": "rh_portal", "edge": "rh_portal", "back": None } )
    high = [ Hole( a, b, L1 + 20, 600, glass="lobby", frame="rh_gunmetal", sill="rh_gunmetal" )
             for a, b in ( ( -700, -250 ), ( -170, 170 ), ( 250, 700 ) ) ]
    side_wall( model, LOBBY, "w", L1 - SLAB, LOBBY_TOP, high )
    for k, h in enumerate( high ):
        window_tank( inside, lights, LOBBY, "w", h, rng, 240, f"Lobby west tank {k}", top=LOBBY_TOP, bottom=L1 - SLAB + 4 )
        mullions( model, fr, h.u0 - base, h.u1 - base, h.z0, h.z1, 2 )
    portals = [ ( c - base - DOOR_HALF - DOOR_PORTAL, c - base + DOOR_HALF + DOOR_PORTAL ) for c in DOOR_PAIRS ]
    joint = DOOR_TOP + DOOR_PORTAL
    clad_rng, door_rng = np.random.default_rng( 7 ), np.random.default_rng( 11 )
    edges = [ 0.0 ] + [ x for p in portals for x in p ] + [ n1 - n0 ]
    for a, b in zip( edges[::2], edges[1::2] ):
        clad( model, fr, a, b, 3.0, joint, clad_rng )
        clad( model, fr, a, b, joint, L1 - SLAB, clad_rng )
        fbox( model, fr, a, b, 0.0, 0.4, 0.0, 3.0, "rh_portal", skip=( "back", "bottom" ) )
    for k, ( a, b ) in enumerate( portals ):
        clad( model, fr, a, b, joint, L1 - SLAB, clad_rng, width=( b - a ) / 2 )
        c = DOOR_PAIRS[k] - base
        door_pair( model, fr, c )
        downlight_rings( model, fr.p( c, 16, 0 )[:2], L1 - SLAB )
        lights.append( light( f"Lobby door {k}", fr.p( c, 15, L1 - SLAB - 12 ), WARM, 190 ) )
    for c0, c1 in zip( DOOR_PAIRS, DOOR_PAIRS[1:] ):
        n = ( c0 + c1 ) / 2
        soil = bronze_planter( model, fr.p( n - base, 3.5 + 17.5 * DOOR_S / 2, 0 ) )
        dracaena( model, fr.p( n - base, 3.5 + 17.5 * DOOR_S / 2, soil ), door_rng, scale=1.5, leaves=30 )
    for n in ( -600.0, 600.0 ):
        sconce( model, fr, n - base, 110, w=0.75 )
    door_gallery( model, inside, lights, door_rng )

    # The west and east balconies (the north and south ones come with the halves) and the railings round the void.
    for be0, be1, side in ( ( e0, v_e0, "e" ), ( v_e1, e1, "w" ) ):
        model.box( ( be0, v_n0, L1 - SLAB ), ( be1, v_n1, L1 ), { "+z": "rh_floor", "-z": "rh_ceiling", "default": None }, STONE )
        fr_b, base_b, _ = side_frame( ( be0, be1, v_n0, v_n1 ), side )
        fascia( model, fr_b, 0, v_n1 - v_n0 )
    for a, b in ( ( v_n0, -LOBBY_STAIR[3] ), ( -LOBBY_STAIR[2], LOBBY_STAIR[2] ), ( LOBBY_STAIR[3], v_n1 ) ):
        railing( model, ( v_e0 - 2, a ), ( v_e0 - 2, b ), L1 )
    railing( model, ( v_e1 + 2, v_n0 ), ( v_e1 + 2, v_n1 ), L1 )
    for e in ( -2810.0, -1800.0 ):
        downlight_line( model, ( e, v_n0 ), ( e, v_n1 ), L1 - SLAB, every=120 )
        for n in ( -600.0, 0.0, 600.0 ):
            lights.append( light( f"Lobby balcony {int( e )} {int( n )}", ( e, n, 420 ), WARM, 380 ) )
        lights.append( light( f"Lobby under balcony {int( e )}", ( e, 0, 180 ), WARM, 300 ) )

    # The reception: a cylinder tank under a lit halo, the curved desk round its east side.
    tc = np.array( LOBBY_TANK )
    model.cylinder( tc, 136, 0, 30, { "side": "rh_wall_dark", "top": "rh_steel" }, sides=40, surface=STONE )
    for k in range( 60 ):
        a, b = 6 * k, 6 * ( k + 1 )
        pa, pb = tc + polar( a, 120 ), tc + polar( b, 120 )
        na, nb = np.array( ( *polar( a, 1 ), 0.0 ) ), np.array( ( *polar( b, 1 ), 0.0 ) )
        model.polygon( tank_paint( "lobby_column" ), [ ( *pa, 30 ), ( *pb, 30 ), ( *pb, 300 ), ( *pa, 300 ) ], normals=[ na, nb, nb, na ] )
        for z0_, z1_ in ( ( 30, 36 ), ( 294, 300 ) ):
            qa, qb = tc + polar( a, 122.5 ), tc + polar( b, 122.5 )
            model.polygon( "rh_steel", [ ( *qa, z0_ ), ( *qb, z0_ ), ( *qb, z1_ ), ( *qa, z1_ ) ], normals=[ na, nb, nb, na ] )
    model.prism( [ tuple( tc + p ) for p in ngon( 120, 32 ) ], 30, 300, {}, GLASS )
    model.prism( [ tuple( tc + p ) for p in ngon( 124, 32 ) ], 300, 312, { "side": "rh_steel", "top": "rh_gunmetal", "bottom": "rh_steel" } )
    facing( inside, "rh_sand", [ ( *( tc + p ), 30.5 ) for p in ngon( 119, 32 ) ], ( 0, 0, 1 ) )
    lamp_lid( inside, tc, 119, 299 )
    water_cylinder( inside, tc, 117, 30.5, 296 )
    rock( inside, ( *( tc + ( -20, 10 ) ), 30.5 ), 62, 150, rng )
    for k in range( 6 ):
        coral( inside, ( *( tc + polar( rng.uniform( 0, 360 ), rng.uniform( 60, 100 ) ) ), 30.5 ), rng.uniform( 9, 15 ), rng )
    for k in range( 4 ):
        kelp( inside, ( *( tc + polar( rng.uniform( 0, 360 ), rng.uniform( 70, 105 ) ) ), 30.5 ), rng.uniform( 180, 240 ), rng )
    lights.append( light( "Lobby cylinder tank", ( *tc, 270 ), COOL, 300 ) )
    # The halo: a ceiling ring hung over the reception, lit round its edge.
    halo = lambda r: [ tuple( tc + p ) for p in ngon( r, 48 ) ]
    model.prism( halo( 270 ), 336, 366, { "side": "rh_gunmetal", "top": "rh_gunmetal", "bottom": None } )
    for k in range( 48 ):
        a, b = 7.5 * k, 7.5 * ( k + 1 )
        facing( model, "rh_ceiling", [ ( *( tc + polar( a, 132 ) ), 336 ), ( *( tc + polar( b, 132 ) ), 336 ),
                                       ( *( tc + polar( b, 262 ) ), 336 ), ( *( tc + polar( a, 262 ) ), 336 ) ], ( 0, 0, -1 ) )
        facing( model, "rh_led_warm", [ ( *( tc + polar( a, 262 ) ), 335.9 ), ( *( tc + polar( b, 262 ) ), 335.9 ),
                                        ( *( tc + polar( b, 271 ) ), 335.9 ), ( *( tc + polar( a, 271 ) ), 335.9 ) ], ( 0, 0, -1 ) )
        facing( model, "rh_gunmetal", [ ( *( tc + polar( a, 132 ) ), 336 ), ( *( tc + polar( b, 132 ) ), 336 ),
                                        ( *( tc + polar( b, 132 ) ), 366 ), ( *( tc + polar( a, 132 ) ), 366 ) ], ( *-polar( ( a + b ) / 2, 1 ), 0 ) )
    for a in ( 100.0, 150.0, 210.0, 260.0 ):
        p = tc + polar( a, 200 )
        tube( model, ( *p, 366 ), ( *p, LOBBY_TOP ), 0.8, "rh_steel", sides=6 )
    lights.append( light( "Lobby halo", ( *( tc + ( 140, 0 ) ), 320 ), WARM, 360 ) )
    # The desk: a curved counter, laminate top, a precast concrete front with a warm strip, screens facing the staff.
    d0, d1, da, db = 212.0, 250.0, -62.0, 62.0
    steps = 16
    for k in range( steps ):
        a, b = da + ( db - da ) * k / steps, da + ( db - da ) * ( k + 1 ) / steps
        pa0, pb0, pa1, pb1 = tc + polar( a, d0 ), tc + polar( b, d0 ), tc + polar( a, d1 ), tc + polar( b, d1 )
        facing( model, "rh_laminate", [ ( *pa0, 42 ), ( *pb0, 42 ), ( *pb1, 42 ), ( *pa1, 42 ) ], ( 0, 0, 1 ) )
        out = np.array( ( *polar( ( a + b ) / 2, 1 ), 0.0 ) )
        facing( model, "rh_smooth", [ ( *pa1, 0 ), ( *pb1, 0 ), ( *pb1, 42 ), ( *pa1, 42 ) ], out )
        facing( model, "rh_smooth", [ ( *pa0, 0 ), ( *pb0, 0 ), ( *pb0, 42 ), ( *pa0, 42 ) ], -out )
        qa, qb = tc + polar( a, d1 + 0.2 ), tc + polar( b, d1 + 0.2 )
        facing( model, "rh_led_warm", [ ( *qa, 5 ), ( *qb, 5 ), ( *qb, 8 ), ( *qa, 8 ) ], out )
        model.hull( [ ( *p, z ) for p in ( pa0, pb0, pa1, pb1 ) for z in ( 0, 42 ) ], WOOD )
    for a in ( da, db ):
        pa0, pa1 = tc + polar( a, d0 ), tc + polar( a, d1 )
        side = np.array( ( *polar( a + ( 90 if a > 0 else -90 ), 1 ), 0.0 ) )
        facing( model, "rh_smooth", [ ( *pa0, 0 ), ( *pa1, 0 ), ( *pa1, 42 ), ( *pa0, 42 ) ], side )
    for a in ( -32.0, 0.0, 32.0 ):
        p = tc + polar( a, 228 )
        fr_m = Frame( p, polar( a + 90, 1 ), -polar( a, 1 ) )
        fbox( model, fr_m, -11, 11, -1.5, 1.5, 47, 62, { "default": "rh_black", "front": "rh_screen_data" } )
        fbox( model, fr_m, -2, 2, -3, 0, 42, 48, "rh_gunmetal" )

    # The round coral display: a plinth, a glass ring and a reef mound rising out of its open top.
    dc = np.array( LOBBY_DISPLAY )
    model.prism( [ tuple( dc + p ) for p in ngon( 92, 32 ) ], 0, 34, { "side": "rh_gunmetal", "top": "rh_steel" }, STONE )
    for k in range( 48 ):
        a, b = 7.5 * k, 7.5 * ( k + 1 )
        pa, pb = dc + polar( a, 88 ), dc + polar( b, 88 )
        na, nb = np.array( ( *polar( a, 1 ), 0.0 ) ), np.array( ( *polar( b, 1 ), 0.0 ) )
        model.polygon( tank_paint( "display" ), [ ( *pa, 34 ), ( *pb, 34 ), ( *pb, 70 ), ( *pa, 70 ) ], normals=[ na, nb, nb, na ] )
        qa, qb = dc + polar( a, 92.6 ), dc + polar( b, 92.6 )
        model.polygon( "rh_led_warm", [ ( *qa, 6 ), ( *qb, 6 ), ( *qb, 9 ), ( *qa, 9 ) ], normals=[ na, nb, nb, na ] )
    for k in range( 48 ):
        a, b = 7.5 * k, 7.5 * ( k + 1 )
        facing( model, "rh_steel", [ ( *( dc + polar( a, 87.5 ) ), 75 ), ( *( dc + polar( b, 87.5 ) ), 75 ),
                                     ( *( dc + polar( b, 93 ) ), 75 ), ( *( dc + polar( a, 93 ) ), 75 ) ], ( 0, 0, 1 ) )
        facing( model, "rh_steel", [ ( *( dc + polar( a, 93 ) ), 70 ), ( *( dc + polar( b, 93 ) ), 70 ),
                                     ( *( dc + polar( b, 93 ) ), 75 ), ( *( dc + polar( a, 93 ) ), 75 ) ], ( *polar( ( a + b ) / 2, 1 ), 0 ) )
    model.prism( [ tuple( dc + p ) for p in ngon( 88, 32 ) ], 34, 75, {}, STONE )
    facing( inside, "rh_sand", [ ( *( dc + p ), 34.5 ) for p in ngon( 87.5, 32 ) ], ( 0, 0, 1 ) )
    for k in range( 48 ):
        a, b = 7.5 * k, 7.5 * ( k + 1 )
        facing( model, "rh_brass", [ ( *( dc + polar( a, 124 ) ), 0.12 ), ( *( dc + polar( b, 124 ) ), 0.12 ),
                                     ( *( dc + polar( b, 129 ) ), 0.12 ), ( *( dc + polar( a, 129 ) ), 0.12 ) ], ( 0, 0, 1 ) )
    rock( model, ( *dc, 34.5 ), 62, 100, rng )
    model.hull( [ ( *( dc + p ), z ) for p in ngon( 58, 12 ) for z in ( 75, 128 ) ], STONE )
    # Coral grows over the mound (on its surface: about 34.5 + 100 ( 1 - ( r / 62 )^2 ) high) and round its foot.
    for k in range( 24 ):
        r = rng.uniform( 14, 58 )
        coral( model, ( *( dc + polar( rng.uniform( 0, 360 ), r ) ), 34.5 + 92 * ( 1 - ( r / 62 ) ** 2 ) ),
               rng.uniform( 6, 12 ), rng )
    for k in range( 14 ):
        coral( model, ( *( dc + polar( rng.uniform( 0, 360 ), rng.uniform( 66, 82 ) ) ), 75 ), rng.uniform( 5, 9 ), rng )

    # The whale, and the atrium's light.
    whale( model, ( -2300, 0 ), 475 )
    for e in ( -2560.0, -2060.0 ):
        lights.append( light( f"Lobby atrium {int( e )}", ( e, 0, 560 ), WARM, 640 ) )
    for e in range( -2820, -1720, 160 ):
        for n in ( -480.0, 0.0, 480.0 ):
            downlight_rings( model, ( e + 20, n ), LOBBY_TOP )

    m, i, l = build_mirrored( lobby_north, rng, [ ( False, True, "south" ) ],
                              { "south": { "rh_banner_manta": "rh_banner_jelly" } } )
    model.extend( m )
    inside.extend( i )
    lights += l


# ---------------------------------------------------------------------------------------------------------------------
# The Control Room (reference 2, Blue Team's spawn): a dark hall in front of the panoramic tank, consoles facing the
# glass, an upper floor along its west and north walls with the glass-walled office

CONTROL = ( CONTROL_FACE, 2900.0, -900.0, 900.0 )
CONTROL_TOP = 440.0
CONTROL_SLAB = ( CONTROL_FACE, 2380.0, 560.0, 900.0 )      # the north upper floor
CONTROL_WALK = ( CONTROL_FACE, 1880.0, -CORRIDOR, 560.0 )  # the walkway from the upper gallery
CONTROL_STAIR = ( 2380.0, 2666.0, 770.0, 900.0 )           # climbing west
OFFICE = ( CONTROL_FACE, 2250.0, 720.0, 900.0 )
OFFICE_TOP = 380.0
PANORAMA_DEPTH = 580.0


def console( model, centre, length, yaw=0.0, z=0.0 ):
    """ An operator's console: a gunmetal desk with a sloping lit panel, and a row of screens on stands behind it,
    facing +w ( the operator stands on the -w side ). """
    fr = Frame( centre[:2], ( math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) ) ) )
    h = length / 2
    fbox( model, fr, -h, h, -16, 16, z, z + 30, { "default": "rh_steel", "top": "rh_black" }, METAL )
    fbox( model, fr, -h - 2, h + 2, -18, -16, z + 2, z + 26, "rh_black" )
    facing( model, "rh_led_cool", [ fr.p( -h, -18.05, z + 3 ), fr.p( h, -18.05, z + 3 ), fr.p( h, -18.05, z + 5 ), fr.p( -h, -18.05, z + 5 ) ],
            fr.vec( 0, -1, 0 ) )
    panel = [ fr.p( -h + 4, -15, z + 30.2 ), fr.p( h - 4, -15, z + 30.2 ), fr.p( h - 4, 4, z + 36 ), fr.p( -h + 4, 4, z + 36 ) ]
    facing( model, "rh_screen_data", panel, fr.vec( 0, -0.3, 1 ) )
    fbox( model, fr, -h, h, 4, 16, z + 30, z + 36, "rh_gunmetal" )
    count = max( 1, int( length / 44 ) )
    for k in range( count ):
        u = -h + length * ( k + 0.5 ) / count
        fbox( model, fr, u - 2, u + 2, 8, 11, z + 36, z + 44, "rh_gunmetal" )
        fbox( model, fr, u - 19, u + 19, 9, 11, z + 44, z + 66, { "default": "rh_steel", "back": "rh_screen_map" if k % 2 else "rh_screen_data" } )
    model.boxes.append( ( fr.p( 0, 0, z + 33 ), ( ( *fr.d, 0.0 ), ( *fr.f, 0.0 ), ( 0.0, 0.0, 1.0 ) ), np.array( ( length + 4, 36, 66 ) ), METAL ) )


def server_rack( model, fr, u0, u1, z=0.0, height=84.0, depth=30.0 ):
    """ A row of server racks against a frame wall's front: black cabinets with rows of small lights. """
    count = max( 1, int( ( u1 - u0 ) / 26 ) )
    width = ( u1 - u0 ) / count
    for k in range( count ):
        a, b = u0 + k * width + 0.6, u0 + ( k + 1 ) * width - 0.6
        fbox( model, fr, a, b, 0, depth, z, z + height, { "default": "rh_black", "back": None, "top": "rh_gunmetal" } )
        for row in range( 6 ):
            zz = z + 10 + row * 12
            paint = "rh_led_cool" if ( k + row ) % 3 else "rh_led_warm"
            facing( model, paint, [ fr.p( a + 3, depth + 0.05, zz ), fr.p( a + 7, depth + 0.05, zz ), fr.p( a + 7, depth + 0.05, zz + 1.2 ),
                                    fr.p( a + 3, depth + 0.05, zz + 1.2 ) ], fr.vec( 0, 1, 0 ) )
    fbox( model, fr, u0, u1, 0, depth, z, z + height, None, METAL )


def partition( model, p0, p1, z0, z1, gaps=() ):
    """ An office's glass wall from p0 to p1 ( plan ), frosted glass in a gunmetal frame, with door gaps ( u ranges
    along it ). The glass is 1 thick, so rounds go through. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    length = float( np.linalg.norm( p1 - p0 ) )
    fr = Frame( p0, p1 - p0 )
    cuts = [ 0.0 ] + [ x for g in gaps for x in g ] + [ length ]
    for k in range( 0, len( cuts ), 2 ):
        a, b = cuts[k], cuts[k + 1]
        if b - a < 1:
            continue
        posts = max( 1, int( math.ceil( ( b - a ) / 90 ) ) )
        for j in range( posts + 1 ):
            u = a + ( b - a ) * j / posts
            fbox( model, fr, max( a, u - 2 ), min( b, u + 2 ), -2, 2, z0, z1, "rh_gunmetal", METAL )
        for zz in ( z0, z0 + 96 ):
            fbox( model, fr, a, b, -2, 2, zz, zz + 4 if zz > z0 else zz + 6, "rh_gunmetal" )
        for w, d in ( ( 0.5, 1 ), ( -0.5, -1 ) ):
            facing( model, "rh_glass_office", [ fr.p( a, w, z0 + 6 ), fr.p( b, w, z0 + 6 ), fr.p( b, w, z0 + 96 ), fr.p( a, w, z0 + 96 ) ],
                    fr.vec( 0, d, 0 ) )
            facing( model, "rh_glass", [ fr.p( a, w, z0 + 100 ), fr.p( b, w, z0 + 100 ), fr.p( b, w, z1 ), fr.p( a, w, z1 ) ],
                    fr.vec( 0, d, 0 ) )
        fbox( model, fr, a, b, -0.5, 0.5, z0 + 6, z1, None, GLASS )
    fbox( model, fr, 0, length, -2.5, 2.5, z1, z1 + 6, "rh_gunmetal" )
    for a, b in gaps:
        for u in ( a, b ):
            fbox( model, fr, u - 2, u + 2, -2.5, 2.5, z0, z1, "rh_gunmetal", METAL )


def desk( model, centre, yaw, z=0.0 ):
    """ An office desk: a laminate top on gunmetal legs, two screens and a chair. """
    fr = Frame( centre[:2], ( math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) ) ) )
    fbox( model, fr, -36, 36, -16, 16, z + 28, z + 30, "rh_laminate", WOOD )
    for u in ( -33, 33 ):
        fbox( model, fr, u - 2, u + 2, -14, 14, z, z + 28, "rh_gunmetal" )
    fbox( model, fr, -31, 31, 10, 12, z + 6, z + 28, "rh_gunmetal" )
    for u in ( -13, 13 ):
        fbox( model, fr, u - 1.5, u + 1.5, 8, 10, z + 30, z + 36, "rh_gunmetal" )
        fbox( model, fr, u - 12, u + 12, 8, 9.5, z + 36, z + 51, { "default": "rh_black", "back": "rh_screen_data" } )
    fbox( model, fr, -9, 9, -34, -18, z + 16, z + 19, "rh_pad_dark" )
    fbox( model, fr, -9, 9, -36, -33, z + 19, z + 36, "rh_pad_dark" )
    fbox( model, fr, -1.5, 1.5, -27.5, -24.5, z, z + 16, "rh_gunmetal" )


def control_room( model, inside, lights, rng ):
    e0, e1, n0, n1 = CONTROL
    floor_rect( model, e0, e1, n0, n1, 0.0 )
    ceiling_rect( model, e0, e1, n0, n1, CONTROL_TOP )

    # The west wall: the galleries' and the service corridors' openings, as on the lobby's east wall.
    door = lambda a, b, z0=0.0, z1=CORRIDOR_H, sill=None: Hole( a, b, z0, z1, frame="rh_gunmetal", sill=sill )
    fr, base = side_wall( model, CONTROL, "w", 0, L1 - SLAB, [ door( -720, -500 ), door( -CORRIDOR, CORRIDOR ), door( 500, 720 ) ],
                          paints=WALL_DARK )
    side_wall( model, CONTROL, "w", L1 - SLAB, CONTROL_TOP, [ door( -CORRIDOR, CORRIDOR, L1, L1 + CORRIDOR_H, "rh_floor" ) ], paints=WALL_DARK )
    baseboard( model, fr, 0, n1 - n0 )
    for n in ( -820.0, -300.0, 300.0 ):
        sconce( model, fr, n - base, 110 )

    # The panoramic window: four tall panes between thick concrete pillars, into the big tank with its rock arch.
    pillar = 64.0
    width = ( 1520.0 - 3 * pillar ) / 4
    starts = [ -760 + k * ( width + pillar ) for k in range( 4 ) ]
    panes = [ Hole( a, a + width, 36, 404, glass="control", frame="rh_gunmetal", sill="rh_gunmetal" ) for a in starts ]
    fr, base = side_wall( model, CONTROL, "e", 0, CONTROL_TOP, panes, paints=WALL_DARK )
    tank_box( inside, fr, -790 - base, 790 - base, -20 - PANORAMA_DEPTH, -20, -40, 460, rng, floor_z=26 )
    concrete = { "default": "rh_wall", "back": None, "top": None, "bottom": None }
    for a in starts[1:]:
        u = a - pillar / 2 - base
        fbox( model, fr, u - pillar / 2, u + pillar / 2, 0.0, 34.0, 0.0, CONTROL_TOP, concrete, STONE )
        fbox( model, fr, u - pillar / 2 - 1, u + pillar / 2 + 1, 0.0, 35.0, 0.0, 8.0, { "default": "rh_gunmetal", "back": None, "bottom": None } )
        sconce( model, fr, u, 236, w=34.0 )
    # The window's head: a concrete beam over the glass, the coffer's east side.
    fbox( model, fr, -790 - base, 790 - base, 0.0, 34.0, 404.0, CONTROL_TOP, dict( concrete, bottom="rh_wall" ), STONE )
    baseboard( model, fr, 0, 140 )
    baseboard( model, fr, n1 - n0 - 140, n1 - n0 )
    arch_e = e1 + 20 + PANORAMA_DEPTH * 0.6
    rock_arch( inside, ( arch_e, -60, 26 ), ( arch_e, 360, 26 ), 330, 44, rng )
    for n in ( -600.0, -380.0, 560.0, 700.0 ):
        rock( inside, ( arch_e + rng.uniform( -60, 80 ), n, 26 ), rng.uniform( 50, 80 ), rng.uniform( 120, 300 ), rng )
    for k in range( 24 ):
        coral( inside, ( rng.uniform( e1 + 60, e1 + 420 ), rng.uniform( -720, 720 ), 26 ), rng.uniform( 10, 20 ), rng )
    for k in range( 16 ):
        sea_grass( inside, ( rng.uniform( e1 + 50, e1 + 300 ), rng.uniform( -740, 740 ), 26 ), rng )
    for k in range( 12 ):
        kelp( inside, ( rng.uniform( e1 + 200, e1 + 560 ), rng.uniform( -760, 760 ), 26 ), rng.uniform( 250, 400 ), rng )
    for n in ( -560.0, -190.0, 190.0, 560.0 ):
        lights.append( light( f"Panorama tank {int( n )}", ( e1 + 20 + PANORAMA_DEPTH * 0.45, n, 430 ), COOL, 620 ) )
        lights.append( light( f"Panorama spill {int( n )}", ( e1 - 90, n, 200 ), SPILL, 520 ) )

    # The south wall: two arched tank windows.
    holes = [ Hole( a, b, 30, 230, rise=30, glass="gallery", frame="rh_gunmetal", sill="rh_gunmetal" ) for a, b in ( ( 1900, 2200 ), ( 2400, 2700 ) ) ]
    fr, base = side_wall( model, CONTROL, "s", 0, CONTROL_TOP, holes, paints=WALL_DARK )
    for k, h in enumerate( holes ):
        window_tank( inside, lights, CONTROL, "s", h, rng, 120, f"Control south tank {k}", top=260, bottom=0 )
    baseboard( model, fr, 0, e1 - e0 )
    for e in ( 1800.0, 2300.0, 2800.0 ):
        sconce( model, fr, e - base, 200 )

    # The north wall: server racks under the upper floor, the office's window into a tank over it.
    office_window = Hole( 1800, 2150, 250, 360, glass="gallery", frame="rh_gunmetal", sill="rh_gunmetal" )
    fr, base = side_wall( model, CONTROL, "n", 0, L1 - SLAB, [], paints=WALL_DARK )
    side_wall( model, CONTROL, "n", L1 - SLAB, CONTROL_TOP, [ office_window ], paints=WALL_DARK )
    window_tank( inside, lights, CONTROL, "n", office_window, rng, 110, "Control office tank", top=OFFICE_TOP + 10, bottom=L1 )
    server_rack( model, fr, 1960 - base, 2300 - base )
    baseboard( model, fr, 0, 1960 - base )
    baseboard( model, fr, 2300 - base, e1 - e0 )
    fbox( model, fr, 2250 - base, e1 - e0, 0, 1.0, L1, L1 + 6, { "default": "rh_gunmetal", "back": None, "bottom": None } )
    sconce( model, fr, 2800 - base, 300 )

    # The upper floor: the north slab and the walkway, their fascias over the hall, railings, and the stair.
    for lo_e, hi_e, lo_n, hi_n in ( CONTROL_SLAB, CONTROL_WALK ):
        model.box( ( lo_e, lo_n, L1 - SLAB ), ( hi_e, hi_n, L1 ), { "+z": "rh_floor", "-z": "rh_ceiling", "default": None }, STONE )
    fr_s, _, _ = side_frame( CONTROL_SLAB, "s" )
    fascia( model, fr_s, 1880 - e0, CONTROL_SLAB[1] - e0 )
    fr_e, _, _ = side_frame( CONTROL_SLAB, "e" )
    fascia( model, fr_e, 0, CONTROL_STAIR[2] - CONTROL_SLAB[2] )
    fr_w, _, _ = side_frame( CONTROL_WALK, "e" )
    fascia( model, fr_w, 0, 560 + CORRIDOR )
    fr_ws, _, _ = side_frame( CONTROL_WALK, "s" )
    fascia( model, fr_ws, 0, 1880 - e0 )
    railing( model, ( 1880, 562 ), ( 2378, 562 ), L1 )
    railing( model, ( 2378, 562 ), ( 2378, CONTROL_STAIR[2] ), L1 )
    railing( model, ( 1878, -CORRIDOR + 2 ), ( 1878, 562 ), L1 )
    railing( model, ( e0, -CORRIDOR + 2 ), ( 1878, -CORRIDOR + 2 ), L1 )
    s_e0, s_e1, s_n0, s_n1 = CONTROL_STAIR
    stair( model, ( s_e0, s_n0 ), ( s_e1, s_n1 ), 0.0, L1, "-e", side="rh_wall_dark" )
    stair_rail( model, ( s_e0, s_n0 + 2 ), ( s_e1, s_n1 - 2 ), 0.0, L1, "-e", sides=( True, False ) )
    for e in ( 1800.0, 2100.0 ):
        downlight_line( model, ( e, 600 ), ( e, 860 ), L1 - SLAB, every=110 )
    downlight_line( model, ( 1800, -60 ), ( 1800, 500 ), L1 - SLAB, every=110 )
    for e, n in ( ( 1800, 0 ), ( 1800, 400 ), ( 2050, 700 ), ( 2300, 700 ) ):
        lights.append( light( f"Control under floor {e} {n}", ( e, n, 170 ), WARM, 260 ) )

    # The office: glass walls, a lower ceiling with a light strip, desks.
    o_e0, o_e1, o_n0, o_n1 = OFFICE
    partition( model, ( 1880, o_n0 ), ( o_e1, o_n0 ), L1, OFFICE_TOP, gaps=( ( 120, 200 ), ) )
    partition( model, ( o_e1, o_n0 ), ( o_e1, o_n1 ), L1, OFFICE_TOP, gaps=( ( 60, 130 ), ) )
    model.box( ( o_e0, o_n0, OFFICE_TOP ), ( o_e1 + 2.5, o_n1, OFFICE_TOP + 12 ),
               { "-z": "rh_ceiling", "+z": "rh_gunmetal", "+e": "rh_gunmetal", "-n": "rh_gunmetal", "default": None }, STONE )
    for e in ( 1820.0, 1980.0, 2140.0 ):
        model.polygon( "rh_led_warm", [ ( e - 50, 805, OFFICE_TOP - 0.2 ), ( e - 50, 815, OFFICE_TOP - 0.2 ),
                                        ( e + 50, 815, OFFICE_TOP - 0.2 ), ( e + 50, 805, OFFICE_TOP - 0.2 ) ] )
    desk( model, ( 1960, 780 ), 180.0, z=L1 )
    desk( model, ( 2150, 860 ), 0.0, z=L1 )
    lights.append( light( "Control office", ( 1990, 810, 350 ), WARM, 300 ) )
    skip_cases( rng )

    # The hall: consoles facing the glass, beams with light strips.
    for n in ( -260.0, 260.0 ):
        console( model, ( 2600, n ), 280, 90.0 + 180.0 )
    console( model, ( 2220, 0 ), 180, 90.0 + 180.0 )
    # The ceiling: a deep concrete coffer over the hall, a warm light cove round its edge, downlights in the soffits.
    ce0, ce1, cn0, cn1 = 1950.0, 2866.0, -850.0, 520.0
    soffit = { "default": "rh_wall", "+z": None }
    for lo, hi in ( ( ( e0, n0, 396 ), ( e1, cn0, CONTROL_TOP ) ), ( ( e0, cn1, 396 ), ( e1, n1, CONTROL_TOP ) ),
                    ( ( e0, cn0, 396 ), ( ce0, cn1, CONTROL_TOP ) ) ):
        model.box( lo, hi, soffit, STONE )
    cove = [ ( ( ce0, cn0 ), ( ce1, cn0 ), ( 0, 1 ) ), ( ( ce1, cn1 ), ( ce0, cn1 ), ( 0, -1 ) ), ( ( ce0, cn1 ), ( ce0, cn0 ), ( 1, 0 ) ) ]
    for ( a, b, d ) in cove:
        off = ( d[0] * 0.25, d[1] * 0.25 )
        facing( model, "rh_led_warm", [ ( a[0] + off[0], a[1] + off[1], 397 ), ( b[0] + off[0], b[1] + off[1], 397 ),
                                        ( b[0] + off[0], b[1] + off[1], 400 ), ( a[0] + off[0], a[1] + off[1], 400 ) ], ( *d, 0 ) )
    downlight_line( model, ( ce0, -875 ), ( ce1, -875 ), 396, every=150 )
    downlight_line( model, ( 2400, 545 ), ( ce1, 545 ), 396, every=150 )
    downlight_line( model, ( 1925, -800 ), ( 1925, 500 ), 396, every=150 )
    skip_cases( rng )
    display_case( model, ( 2060, 300 ), ( 44, 44 ), tank_name="display", rng=rng, inside=inside )
    drain( model, 2690, 2706, -760, 760 )
    drain( model, 1950, 2690, -146, -130 )
    for e in ( 2000.0, 2400.0, 2750.0 ):
        for n in ( -500.0, 0.0, 500.0 ):
            if e < 2400 and n > 400:
                continue
            lights.append( light( f"Control hall {int( e )} {int( n )}", ( e, n, 380 ), WARM, 560 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The Filter Hall (reference 3, bomb site A): the life-support hall north of the Rotunda, two glass filter columns,
# steel catwalks round its north and east walls and a mezzanine in its south-east corner

FILTER = ( -1150.0, 1150.0, 1100.0, 1850.0 )
FILTER_TOP = 440.0
FILTER_COLUMNS = ( ( -380.0, 1420.0 ), ( 380.0, 1420.0 ) )


def climbable_pipe_objects():
    """ Physical/use volumes for the four decorative risers beside the glass filters. """
    objects = []
    for column, ( e, n ) in enumerate( FILTER_COLUMNS ):
        for side in ( -1, 1 ):
            key = f"pipe/filter/{column}/{side}"
            height, radius = FILTER_TOP - 90.0, 15.0
            objects.append( K.game_object( ids, f"Filter {column + 1} climbable pipe {side}", key,
                K.to_world( ( e + side * 122.0, n + 98.0, 90.0 ) ), tags="climbable_pipe", components=[
                    K.component( ids, "Facepunch.ClimbablePipe", f"{key}/climb", Height=height, Radius=radius,
                                 ClimbSpeed=90.0, CollarScale=1.32 ),
                    K.component( ids, "Sandbox.CapsuleCollider", f"{key}/collider", Start=K.vec( ( 0, 0, radius ) ),
                                 End=K.vec( ( 0, 0, height - radius ) ), Radius=radius, Static=True, IsTrigger=False,
                                 Surface="surfaces/metal.surface" ),
                ] ) )
    return K.game_object( ids, "Climbable Pipes", "climbable-pipes", children=objects )
CATWALK = ( -1150.0, 1150.0, 1670.0, 1850.0 )
EAST_WALK = ( 970.0, 1150.0, 1300.0, 1670.0 )
MEZZANINE = ( 586.0, 1150.0, 1100.0, 1300.0 )
FILTER_STAIRS = ( ( ( 300.0, 1110.0 ), ( 586.0, 1250.0 ), "+e" ), ( ( -1150.0, 1384.0 ), ( -1030.0, 1670.0 ), "+n" ) )


def grating_slab( model, rect, z_top=L1, thick=SLAB ):
    """ A steel catwalk's deck: grating on top, gunmetal under and on its edges. """
    e0, e1, n0, n1 = rect
    model.box( ( e0, n0, z_top - thick ), ( e1, n1, z_top ), { "+z": "rh_grate", "-z": "rh_gunmetal", "default": None }, METAL )


def filter_column( model, inside, lights, centre, rng, name ):
    """ A sand filter: a steel base, a glass drum of water over layers of sand and gravel, a steel cap and the pipes up
    to the ceiling, hazard lines round its base. """
    c = np.asarray( centre, float )
    model.box( ( c[0] - 150, c[1] - 130, 0 ), ( c[0] + 150, c[1] + 130, 90 ), { "default": "rh_wall", "+z": "rh_gunmetal" }, STONE )
    model.box( ( c[0] - 152, c[1] - 132, 84 ), ( c[0] + 152, c[1] + 132, 90 ), { "default": "rh_gunmetal", "-z": None, "+z": None } )
    for k in range( 4 ):
        # The base's bolted access panels.
        fr = Frame( ( c[0] - 100 + k * 66, c[1] - 130 ), ( 1, 0 ), ( 0, -1 ) )
        fbox( model, fr, -24, 24, 0, 0.8, 18, 66, { "default": "rh_gunmetal", "back": None } )
    line_strip( model, c[0] - 170, c[0] + 170, c[1] - 152, c[1] - 148 )
    line_strip( model, c[0] - 170, c[0] + 170, c[1] + 148, c[1] + 152 )
    line_strip( model, c[0] - 172, c[0] - 168, c[1] - 148, c[1] + 148 )
    line_strip( model, c[0] + 168, c[0] + 172, c[1] - 148, c[1] + 148 )
    paint = tank_paint( "filter_column" )
    for k in range( 64 ):
        a, b = 5.625 * k, 5.625 * ( k + 1 )
        pa, pb = c + polar( a, 100 ), c + polar( b, 100 )
        na, nb = np.array( ( *polar( a, 1 ), 0.0 ) ), np.array( ( *polar( b, 1 ), 0.0 ) )
        model.polygon( paint, [ ( *pa, 90 ), ( *pb, 90 ), ( *pb, 400 ), ( *pa, 400 ) ], normals=[ na, nb, nb, na ] )
        for z0, z1 in ( ( 90, 98 ), ( 240, 244 ), ( 392, 400 ) ):
            qa, qb = c + polar( a, 102.5 ), c + polar( b, 102.5 )
            model.polygon( "rh_steel", [ ( *qa, z0 ), ( *qb, z0 ), ( *qb, z1 ), ( *qa, z1 ) ], normals=[ na, nb, nb, na ] )
    model.prism( [ tuple( c + p ) for p in ngon( 100, 32 ) ], 90, 400, {}, GLASS )
    for a in range( 0, 360, 45 ):
        # Upright steel straps holding the drum.
        fr, length, d = chord_frame( a + 22.5, 0.9, 101.5 )
        fbox( model, fr, 0, length, -3.0, -0.5, 98, 392, { "default": "rh_steel", "front": None } )
    # Inside: gravel, then sand, the water over them; the collector pipe up the middle.
    for z, r, col in ( ( 130, 99, "rh_rock" ), ( 175, 99, "rh_sand" ) ):
        facing( inside, col, [ ( *( c + p ), z ) for p in ngon( r, 32 ) ], ( 0, 0, 1 ) )
    for k in range( 32 ):
        a, b = 11.25 * k, 11.25 * ( k + 1 )
        pa, pb = c + polar( a, 99.2 ), c + polar( b, 99.2 )
        na, nb = -np.array( ( *polar( a, 1 ), 0.0 ) ), -np.array( ( *polar( b, 1 ), 0.0 ) )
        inside.polygon( "rh_rock", [ ( *pa, 90 ), ( *pa, 130 ), ( *pb, 130 ), ( *pb, 90 ) ], normals=[ na, na, nb, nb ] )
        inside.polygon( "rh_sand", [ ( *pa, 130 ), ( *pa, 175 ), ( *pb, 175 ), ( *pb, 130 ) ], normals=[ na, na, nb, nb ] )
    lamp_lid( inside, c, 99, 399 )
    tube( inside, ( *c, 175 ), ( *c, 400 ), 14, "rh_steel_blue", sides=14 )
    for k in range( 6 ):
        a = 60 * k + 15
        tube( inside, ( *( c + polar( a, 14 ) ), 330 ), ( *( c + polar( a, 70 ) ), 318 ), 3, "rh_steel_blue", sides=8, cap=True )
    # The cap: a steel housing over the drum's top edge (open under it, so the lid shows through the glass), a
    # second tier, and the heavy main pipe from it into the ceiling.
    model.cylinder( c, 108, 378, 414, { "side": "rh_steel", "top": "rh_gunmetal" }, sides=32, surface=METAL )
    for z0, z1 in ( ( 378, 382 ), ( 410, 414 ) ):
        model.cylinder( c, 110.5, z0, z1, { "side": "rh_gunmetal", "top": "rh_gunmetal", "bottom": "rh_gunmetal" }, sides=32 )
    model.cylinder( c, 74, 414, 426, { "side": "rh_steel", "top": "rh_steel" }, sides=24 )
    tube( model, ( *c, 426 ), ( *c, FILTER_TOP ), 30, "rh_pipe", sides=16 )
    tube( model, ( *c, 426 ), ( *c, 431 ), 36, "rh_steel", sides=16, cap=True )
    # The heavy pipework round it, as the reference's filters have: two risers off the base's back corners up to the
    # ceiling, and the inlet and outlet out of its ends, turning down into the floor (their collision a box each).
    for side in ( -1, 1 ):
        x = c[0] + side * 122
        pipe_run( model, [ ( x, c[1] + 98, 90 ), ( x, c[1] + 98, FILTER_TOP ) ], 15, flange_every=110.0 )
        tube( model, ( x, c[1] + 98, 90 ), ( x, c[1] + 98, 96 ), 21, "rh_steel", sides=14, cap=True )
        x0, x1, y = c[0] + side * 150, c[0] + side * 206, c[1] - 60
        pipe_run( model, [ ( x0, y, 54 ), ( x1, y, 54 ), ( x1, y, 0 ) ], 12, flange_every=40.0 )
        tube( model, ( x0, y, 54 ), ( x0 + side * 3, y, 54 ), 17, "rh_steel", sides=14, cap=True )
        tube( model, ( x1, y, 0 ), ( x1, y, 4 ), 18, "rh_steel", sides=14, cap=True )
        model.box( ( min( x0, x1 + side * 14 ), y - 14, 0 ), ( max( x0, x1 + side * 14 ), y + 14, 68 ), { "default": None }, METAL )
    lights.append( light( name, ( *c, 300 ), COOL, 340 ) )


def lamp_lid( inside, centre, r, z, ring=False ):
    """ A round tank's lid seen from under the water: dark, with a ring of lamps round its edge (a disc of light read as
    a white plate through the glass). """
    c = np.asarray( centre, float )[:2]
    facing( inside, "rh_tankback", [ ( *( c + p ), z ) for p in ngon( r, 32 ) ], ( 0, 0, -1 ) )
    if not ring:
        return
    for k in range( 32 ):
        a, b = 11.25 * k, 11.25 * ( k + 1 )
        facing( inside, "rh_led_cool", [ ( *( c + polar( a, r * 0.78 ) ), z - 0.3 ), ( *( c + polar( b, r * 0.78 ) ), z - 0.3 ),
                                         ( *( c + polar( b, r * 0.84 ) ), z - 0.3 ), ( *( c + polar( a, r * 0.84 ) ), z - 0.3 ) ], ( 0, 0, -1 ) )


def pump( model, centre, yaw=0.0 ):
    """ A circulation pump on a plinth: a blue motor, the volute and its pipe stubs. """
    fr = Frame( centre[:2], ( math.cos( math.radians( yaw ) ), math.sin( math.radians( yaw ) ) ) )
    fbox( model, fr, -34, 34, -18, 18, 0, 8, "rh_gunmetal", METAL )
    tube( model, fr.p( -30, 0, 26 ), fr.p( 8, 0, 26 ), 16, "rh_steel_blue", sides=16, cap=True )
    tube( model, fr.p( 8, 0, 26 ), fr.p( 26, 0, 26 ), 20, "rh_pipe", sides=16, cap=True )
    tube( model, fr.p( 18, 0, 46 ), fr.p( 18, 0, 70 ), 7, "rh_pipe", sides=12, cap=True )
    tube( model, fr.p( 26, 0, 26 ), fr.p( 40, 0, 26 ), 7, "rh_pipe", sides=12, cap=True )
    fbox( model, fr, -34, 40, -21, 21, 8, 48, None, METAL )


def filter_hall( model, inside, lights, rng ):
    e0, e1, n0, n1 = FILTER
    floor_rect( model, e0, e1, n0, n1, 0.0 )
    ceiling_rect( model, e0, e1, n0, n1, FILTER_TOP )

    # The south wall: the service corridors and the Rotunda's north passage.
    door = lambda a, b: Hole( a, b, 0, CORRIDOR_H, frame="rh_gunmetal" )
    fr, base = side_wall( model, FILTER, "s", 0, FILTER_TOP, [ door( -1120, -900 ), door( -CORRIDOR, CORRIDOR ), door( 900, 1120 ) ],
                          paints=SERVICE )
    for a, b in ( ( e0, -1120 ), ( -900, -CORRIDOR ), ( CORRIDOR, 900 ), ( 1120, e1 ) ):
        baseboard( model, fr, a - base, b - base, height=8 )
    # Concrete pilasters with wall lights between the doors, and wall lights under the mezzanine, as the reference
    # hall's walls have.
    for e, lit in ( ( -700.0, True ), ( -400.0, False ), ( 200.0, True ) ):
        pilaster( model, fr, e - base, FILTER_TOP, light=lit )
    for e in ( 760.0, 1000.0 ):
        sconce( model, fr, e - base, 110 )

    # The north wall: two windows under the catwalk and a long one over it, all into one tank.
    low = [ Hole( a, b, 30, 170, glass="filter", frame="rh_gunmetal", sill="rh_gunmetal" ) for a, b in ( ( -700, -300 ), ( 300, 700 ) ) ]
    high = Hole( -900, 900, 230, 420, glass="filter", frame="rh_gunmetal", sill="rh_gunmetal" )
    fr, base = side_wall( model, FILTER, "n", 0, L1 - SLAB, low, paints=SERVICE )
    side_wall( model, FILTER, "n", L1 - SLAB, FILTER_TOP, [ high ], paints=SERVICE )
    tank_box( inside, fr, -930 - base, 930 - base, -20 - 230, -20, 0, FILTER_TOP + 20, rng, floor_z=36 )
    mullions( model, fr, high.u0 - base, high.u1 - base, high.z0, high.z1, 6 )
    for e in ( -620.0, 0.0, 620.0 ):
        lights.append( light( f"Filter tank {int( e )}", ( e, 2000, 400 ), COOL, 420 ) )
    baseboard( model, fr, 0, e1 - e0, height=8 )

    # The side walls: a ground window on the west, one over the east walkway.
    west = Hole( 1150, 1350, 30, 170, rise=16, glass="gallery", frame="rh_gunmetal", sill="rh_gunmetal" )
    fr, base = side_wall( model, FILTER, "w", 0, FILTER_TOP, [ west ], paints=SERVICE )
    window_tank( inside, lights, FILTER, "w", west, rng, 120, "Filter west tank", top=200, bottom=0 )
    baseboard( model, fr, 0, n1 - n0, height=8 )
    east = Hole( 1350, 1600, L1 + 20, 400, glass="filter", frame="rh_gunmetal", sill="rh_gunmetal" )
    fr, base = side_wall( model, FILTER, "e", 0, L1 - SLAB, [], paints=SERVICE )
    side_wall( model, FILTER, "e", L1 - SLAB, FILTER_TOP, [ east ], paints=SERVICE )
    window_tank( inside, lights, FILTER, "e", east, rng, 120, "Filter east tank", top=FILTER_TOP, bottom=L1 )
    baseboard( model, fr, 0, n1 - n0, height=8 )

    # The catwalks and the mezzanine, their edges, railings and stairs.
    for rect in ( CATWALK, EAST_WALK, MEZZANINE ):
        grating_slab( model, rect )
    fascia( model, side_frame( CATWALK, "s" )[0], 0, 967.5 - e0, led=False )
    fascia( model, side_frame( EAST_WALK, "w" )[0], 0, 370, led=False )
    fascia( model, side_frame( MEZZANINE, "n" )[0], 0, 967.5 - 586, led=False )
    fascia( model, side_frame( MEZZANINE, "w" )[0], 150, 199, led=False )
    railing( model, ( -1030, 1672 ), ( 970, 1672 ), L1, glass=False )
    railing( model, ( 972, 1300 ), ( 972, 1672 ), L1, glass=False )
    railing( model, ( 586, 1298 ), ( 972, 1298 ), L1, glass=False )
    railing( model, ( 588, 1250 ), ( 588, 1298 ), L1, glass=False )
    for lo, hi, climb in FILTER_STAIRS:
        metal_stair( model, lo, hi, 0.0, L1, climb )
        stair_rail( model, ( lo[0] + ( 0 if climb[1] == "e" else 2 ), lo[1] + ( 2 if climb[1] == "e" else 0 ) ),
                    ( hi[0] - ( 0 if climb[1] == "e" else 2 ), hi[1] - ( 2 if climb[1] == "e" else 0 ) ), 0.0, L1, climb,
                    sides=( True, True ) if climb[1] == "e" else ( False, True ) )
    for e in range( -1000, 1000, 160 ):
        downlight_rings( model, ( e + 80, 1760 ), L1 - SLAB )

    # The filter columns, pumps, the pipes overhead, and cover.
    for k, c in enumerate( FILTER_COLUMNS ):
        filter_column( model, inside, lights, c, rng, f"Filter column {k}" )
    for n, r, paint in ( ( 1200.0, 14.0, "rh_pipe" ), ( 1236.0, 9.0, "rh_pipe_dark" ), ( 1600.0, 14.0, "rh_pipe" ) ):
        pipe_run( model, [ ( e0 + 20, n, FILTER_TOP ), ( e0 + 20, n, FILTER_TOP - 30 ), ( e1 - 20, n, FILTER_TOP - 30 ),
                           ( e1 - 20, n, FILTER_TOP ) ], r, paint=paint )
    for e in range( -1000, 1001, 250 ):
        for n in ( 1200.0, 1600.0 ):
            fbox( model, Frame( ( e, n ), ( 1, 0 ) ), -2, 2, -14, 14, FILTER_TOP - 41, FILTER_TOP, "rh_gunmetal" )
    pump( model, ( -380, 1610 ), 0.0 )
    pump( model, ( 380, 1610 ), 180.0 )
    pump( model, ( -760, 1220 ), 90.0 )
    skip_cases( rng, stacks=2, tall=1 )
    drain( model, -1000, 1000, 1640, 1650 )
    line_strip( model, -1130, 1130, 1652, 1655 )
    for n in ( 1290.0, 1560.0 ):
        downlight_line( model, ( -1000, n ), ( 1000, n ), FILTER_TOP - 0.1, every=160 )
    for e in ( -900.0, -450.0, 0.0, 450.0, 900.0 ):
        lights.append( light( f"Filter hall {int( e )}", ( e, 1440, 400 ), WARM, 560 ) )
    for e in ( -760.0, 0.0, 760.0 ):
        lights.append( light( f"Filter under catwalk {int( e )}", ( e, 1760, 170 ), WARM, 280 ) )
    # Over the catwalk.
    downlight_line( model, ( -1000, 1760 ), ( 900, 1760 ), FILTER_TOP - 0.1, every=190 )
    for e in ( -800.0, -270.0, 270.0, 800.0 ):
        lights.append( light( f"Filter catwalk {int( e )}", ( e, 1760, 420 ), WARM, 380 ) )
    lights.append( light( "Filter mezzanine", ( 870, 1200, 400 ), WARM, 300 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The Tunnel Hall (reference 1, bomb site B): a glass barrel vault under a tank, between low side aisles

TUNNEL = ( -1150.0, 1150.0, -1900.0, -1100.0 )
TUNNEL_N = -1500.0             # the vault's axis
TUNNEL_R = 200.0
TUNNEL_SPRING = 200.0
TUNNEL_TOP = 760.0             # the tank's top over it
NAVE = ( -1700.0, -1300.0 )
NAVE_STEPS = 50.0              # the steps down from each aisle into the nave
PIERS = tuple( -960.0 + 192.0 * k for k in range( 11 ) )
PORTAL_W = 26.0                # a portal's jambs
PORTAL_D = 18.0                # how far it stands out of its wall


def portal( model, fr, u0, u1, height, ceiling ):
    """ A concrete box frame round a doorway in a frame wall, standing out of it to the ceiling, as the reference's
    tunnel openings are framed, with a wall light on each jamb. """
    concrete = { "default": "rh_wall", "back": None, "top": None, "bottom": None }
    for a, b in ( ( u0 - PORTAL_W, u0 ), ( u1, u1 + PORTAL_W ) ):
        fbox( model, fr, a, b, 0.0, PORTAL_D, 0.0, ceiling, concrete, STONE )
        fbox( model, fr, a - 1.0, b + 1.0, 0.0, PORTAL_D + 1.0, 0.0, 8.0, { "default": "rh_gunmetal", "back": None, "bottom": None } )
        sconce( model, fr, ( a + b ) / 2, 112, w=PORTAL_D )
    fbox( model, fr, u0, u1, 0.0, PORTAL_D, height, ceiling, dict( concrete, bottom="rh_wall", left=None, right=None ), STONE )


def pilaster( model, fr, u, ceiling, light=False ):
    """ A concrete pilaster between two windows on a frame wall's front, on a gunmetal plinth. """
    fbox( model, fr, u - 17, u + 17, 0.0, 12.0, 0.0, ceiling, { "default": "rh_wall", "back": None, "top": None, "bottom": None }, STONE )
    fbox( model, fr, u - 18, u + 18, 0.0, 13.0, 0.0, 8.0, { "default": "rh_gunmetal", "back": None, "bottom": None } )
    if light:
        sconce( model, fr, u, 112, w=12.0 )


def aisle_tank( inside, lights, fr, u0, u1, depth, rng, name, thick=20.0 ):
    """ The tank behind a run of the tunnel's side windows ( u0..u1 in the wall's frame ), with its lamps over it and
    its light falling out through the glass. """
    tank_box( inside, fr, u0, u1, -thick - depth, -thick, 0.0, 228.0, rng, floor_z=26.0 )
    lamps = max( 1, round( ( u1 - u0 ) / 420 ) )
    for k in range( lamps ):
        u = u0 + ( u1 - u0 ) * ( k + 0.5 ) / lamps
        lights.append( light( f"{name} {k}", fr.p( u, -thick - depth * 0.45, 214 ), COOL, 380 ) )
        lights.append( light( f"{name} {k} spill", fr.p( u, 70, 100 ), SPILL, 360 ) )


def tunnel_hall( model, inside, lights, rng ):
    e0, e1, n0, n1 = TUNNEL
    s0, s1 = NAVE
    # Floors: the aisles at 0, the nave at -40 with steps down at its edges.
    floor_rect( model, e0, e1, s1, n1, 0.0 )
    floor_rect( model, e0, e1, n0, s0, 0.0 )
    floor_rect( model, e0, e1, s0 + NAVE_STEPS, s1 - NAVE_STEPS, NAVE_Z )
    stair( model, ( e0, s1 - NAVE_STEPS ), ( e1, s1 ), NAVE_Z, 0.0, "+n", side="rh_wall_dark" )
    stair( model, ( e0, s0 ), ( e1, s0 + NAVE_STEPS ), NAVE_Z, 0.0, "-n", side="rh_wall_dark" )
    # The aisles' ceilings and the beams the vault springs from, on piers.
    for a, b in ( ( s1, n1 ), ( n0, s0 ) ):
        model.box( ( e0, a, TUNNEL_SPRING ), ( e1, b, TUNNEL_SPRING + 20 ), { "-z": "rh_ceiling", "default": None }, STONE )
    for edge, side in ( ( s1, 1 ), ( s0, -1 ) ):
        lo, hi = ( edge, edge + 30 ) if side > 0 else ( edge - 30, edge )
        model.box( ( e0, lo, TUNNEL_SPRING - 22 ), ( e1, hi, TUNNEL_SPRING ), { "default": "rh_gunmetal", "+z": None }, METAL )
        face = lo - 0.05 if side > 0 else hi + 0.05
        facing( model, "rh_led_cool", [ ( e0, face, TUNNEL_SPRING - 20 ), ( e1, face, TUNNEL_SPRING - 20 ),
                                        ( e1, face, TUNNEL_SPRING - 16 ), ( e0, face, TUNNEL_SPRING - 16 ) ], ( 0, -side, 0 ) )
        for e in PIERS:
            model.box( ( e - 15, lo, 0 ), ( e + 15, hi, TUNNEL_SPRING - 22 ), { "default": "rh_wall", "-z": None, "+z": None }, STONE )
            model.box( ( e - 17, lo - 2 if side > 0 else lo, 0 ), ( e + 17, hi if side > 0 else hi + 2, 8 ),
                       { "default": "rh_gunmetal", "-z": None } )
            # A wall light on the pier's face towards the nave, as on the reference's piers.
            nave_face = lo if side > 0 else hi
            sconce( model, Frame( ( e, nave_face ), ( 1, 0 ), ( 0, -side ) ), 0.0, 104 )
        for e in range( -1056, 1057, 192 ):
            downlight_rings( model, ( e, edge + 100 * side ), TUNNEL_SPRING )
            if ( e + 1056 ) % 384 == 0:
                lights.append( light( f"Tunnel aisle {side} {e}", ( e, edge + 100 * side, 180 ), WARM, 300 ) )

    # The vault: glass in pieces of 5 degrees between steel ribs at the piers, its collision a shell of hulls.
    paint = tank_paint( "tunnel" )
    steps = 36
    for k in range( steps ):
        a, b = 180.0 * k / steps, 180.0 * ( k + 1 ) / steps
        ca, sa, cb, sb = math.cos( math.radians( a ) ), math.sin( math.radians( a ) ), math.cos( math.radians( b ) ), math.sin( math.radians( b ) )
        pa = lambda r, e: ( e, TUNNEL_N + r * ca, TUNNEL_SPRING + r * sa )
        pb = lambda r, e: ( e, TUNNEL_N + r * cb, TUNNEL_SPRING + r * sb )
        na, nb = np.array( ( 0, -ca, -sa ) ), np.array( ( 0, -cb, -sb ) )
        model.polygon( paint, [ pa( TUNNEL_R, e0 ), pa( TUNNEL_R, e1 ), pb( TUNNEL_R, e1 ), pb( TUNNEL_R, e0 ) ], normals=[ na, na, nb, nb ] )
        model.hull( [ f( r, e ) for f in ( pa, pb ) for r in ( TUNNEL_R, TUNNEL_R + 8 ) for e in ( e0, e1 ) ], GLASS )
        # Every other pier carries a heavy gunmetal arch, as the reference's vault has; the rest light steel ribs.
        for j, e in enumerate( PIERS + ( e0 + 3, e1 - 3 ) ):
            main = j < len( PIERS ) and j % 2 == 0
            w = 3.0 if j >= len( PIERS ) else 11.0 if main else 2.5
            rib = "rh_gunmetal" if main else "rh_steel"
            for r0, r1 in ( ( TUNNEL_R - ( 16 if main else 5 ), TUNNEL_R - 0.4 ), ):
                facing( model, rib, [ ( e - w, TUNNEL_N + r0 * ca, TUNNEL_SPRING + r0 * sa ), ( e - w, TUNNEL_N + r0 * cb, TUNNEL_SPRING + r0 * sb ),
                                             ( e + w, TUNNEL_N + r0 * cb, TUNNEL_SPRING + r0 * sb ), ( e + w, TUNNEL_N + r0 * ca, TUNNEL_SPRING + r0 * sa ) ],
                        na + nb )
                for s in ( -1, 1 ):
                    facing( model, rib, [ ( e + s * w, TUNNEL_N + r0 * ca, TUNNEL_SPRING + r0 * sa ), ( e + s * w, TUNNEL_N + r1 * ca, TUNNEL_SPRING + r1 * sa ),
                                                 ( e + s * w, TUNNEL_N + r1 * cb, TUNNEL_SPRING + r1 * sb ), ( e + s * w, TUNNEL_N + r0 * cb, TUNNEL_SPRING + r0 * sb ) ],
                            ( s, 0, 0 ) )
    # Small warm lamps set into the heavy arches' undersides.
    for e in PIERS[::2]:
        for ang in ( 32.0, 62.0, 118.0, 148.0 ):
            r = TUNNEL_R - 16.3
            corners = [ ( e + du, TUNNEL_N + r * math.cos( math.radians( ang + da ) ), TUNNEL_SPRING + r * math.sin( math.radians( ang + da ) ) )
                        for du, da in ( ( -4, -1.6 ), ( 4, -1.6 ), ( 4, 1.6 ), ( -4, 1.6 ) ) ]
            facing( model, "rh_led_warm", corners, ( 0, -math.cos( math.radians( ang ) ), -math.sin( math.radians( ang ) ) ) )
    for e in range( -1056, 1057, 192 ):
        lights.append( light( f"Tunnel vault {e}", ( e, TUNNEL_N, 360 ), COOL, 330 ) )

    # The tank over and round the vault: its walls and lid face in, sand over the aisles' ceilings, rock and coral.
    for n, d in ( ( n0, 1 ), ( n1, -1 ) ):
        facing( inside, "rh_tankback", [ ( e0, n, TUNNEL_SPRING ), ( e1, n, TUNNEL_SPRING ), ( e1, n, TUNNEL_TOP ), ( e0, n, TUNNEL_TOP ) ], ( 0, d, 0 ) )
    facing( inside, "rh_tankback", [ ( e0, n0, TUNNEL_TOP ), ( e1, n0, TUNNEL_TOP ), ( e1, n1, TUNNEL_TOP ), ( e0, n1, TUNNEL_TOP ) ], ( 0, 0, -1 ) )
    for a, b, side in ( ( n0, s0 - 7, -1 ), ( s1 + 7, n1, 1 ) ):
        facing( inside, "rh_sand", [ ( e0, a, 220 ), ( e1, a, 220 ), ( e1, b, 220 ), ( e0, b, 220 ) ], ( 0, 0, 1 ) )
        edge = s0 if side < 0 else s1
        facing( inside, "rh_sand", [ ( e0, edge, TUNNEL_SPRING ), ( e1, edge, TUNNEL_SPRING ), ( e1, edge + 7 * side, 220 ), ( e0, edge + 7 * side, 220 ) ],
                ( 0, -side, 1 ) )
        mid = ( a + b ) / 2
        for k in range( 16 ):
            e = e0 + 70 + k * ( e1 - e0 - 140 ) / 15 + rng.uniform( -30, 30 )
            rock( inside, ( e, mid + rng.uniform( -20, 20 ), 220 ), rng.uniform( 35, 60 ), rng.uniform( 90, 400 ), rng )
        arch_e = rng.uniform( e0 + 0.3 * ( e1 - e0 ), e1 - 0.3 * ( e1 - e0 ) )
        rock_arch( inside, ( arch_e - 190, mid, 220 ), ( arch_e + 190, mid, 220 ), 240, 34, rng )
        for k in range( 34 ):
            coral( inside, ( rng.uniform( e0 + 40, e1 - 40 ), rng.uniform( a + 20, b - 20 ), 220 ), rng.uniform( 10, 20 ), rng )
        for k in range( 20 ):
            sea_grass( inside, ( rng.uniform( e0 + 40, e1 - 40 ), rng.uniform( a + 15, b - 15 ), 220 ), rng )
        for k in range( 18 ):
            kelp( inside, ( rng.uniform( e0 + 40, e1 - 40 ), rng.uniform( a + 30, b - 30 ), 220 ), rng.uniform( 250, 500 ), rng )
    water_box( inside, Frame( ( 0, 0 ), ( 1, 0 ) ), e0 + 2, e1 - 2, n0 + 2, n1 - 2, 222, TUNNEL_TOP - 10,
               hole=( TUNNEL_R + 8, ( 0, TUNNEL_N, TUNNEL_SPRING ) ) )
    for e in range( -900, 901, 450 ):
        for n in ( -1800.0, -1200.0 ):
            lights.append( light( f"Tunnel tank {e} {int( n )}", ( e, n, 700 ), COOL, 520 ) )

    # The end walls: the tunnel's glass end, into the tanks beyond; tank back above the aisles' ceilings.
    for side in ( "w", "e" ):
        lower = Hole( s0, s1, 0, TUNNEL_SPRING, glass="tunnel", sill="rh_gunmetal" )
        upper = Hole( s0, s1, TUNNEL_SPRING, TUNNEL_SPRING + TUNNEL_R, rise=TUNNEL_R, glass="tunnel" )
        fr, base = side_wall( model, TUNNEL, side, NAVE_Z, TUNNEL_SPRING, [ lower ], paints=WALL_DARK )
        side_wall( model, TUNNEL, side, TUNNEL_SPRING, TUNNEL_TOP, [ upper ], paints={ "front": "rh_tankback", "edge": "rh_gunmetal", "back": None } )
        surround( model, fr, Hole( s0 - base, s1 - base, 0, TUNNEL_SPRING + TUNNEL_R, rise=TUNNEL_R ), 0.0, "rh_gunmetal" )
        u0, u1 = n0 - base, n1 - base
        tank_box( inside, fr, u0, u1, -20 - 230, -20, NAVE_Z, TUNNEL_TOP, rng, floor_z=-4 )
        lights.append( light( f"Tunnel end tank {side}", fr.p( ( u0 + u1 ) / 2, -130, 640 ), COOL, 480 ) )
        baseboard( model, fr, n1 - base - ( n1 - s1 ), u1 )
        baseboard( model, fr, 0, s0 - base )

    # The side walls are glass, as the reference's are: a tall window into the reef in every bay between the piers,
    # from a low sill to the aisle's ceiling, with a concrete pilaster across from each pier. The north wall's
    # doorways (the service corridors and the Rotunda's south passage) are concrete portals, the reference's side
    # openings.
    bays = [ ( a + 24, b - 24 ) for a, b in zip( ( e0, ) + PIERS, PIERS + ( e1, ) ) ]
    window = lambda a, b: Hole( a, b, 20, 184, glass="aisle", frame="rh_gunmetal", sill="rh_gunmetal" )
    doors = ( ( -1120.0, -900.0 ), ( -CORRIDOR, CORRIDOR ), ( 900.0, 1120.0 ) )
    clear = lambda a, b: all( b < d0 - PORTAL_W - 10 or a > d1 + PORTAL_W + 10 for d0, d1 in doors )
    north = [ window( a, b ) for a, b in bays if clear( a, b ) ]
    fr, base = side_wall( model, TUNNEL, "n", 0, TUNNEL_SPRING, [ Hole( a, b, 0, CORRIDOR_H ) for a, b in doors ] + north,
                          paints=WALL_DARK )
    for a, b in ( ( e0, -1120 ), ( -900, -CORRIDOR ), ( CORRIDOR, 900 ), ( 1120, e1 ) ):
        baseboard( model, fr, a - base, b - base )
    for k, ( a, b ) in enumerate( doors ):
        portal( model, fr, a - base, b - base, CORRIDOR_H, TUNNEL_SPRING )
    for e in PIERS:
        if clear( e - 17, e + 17 ):
            pilaster( model, fr, e - base, TUNNEL_SPRING, light=( e // 192 ) % 2 == 0 )
    # The tanks behind the north windows: one each side of the Rotunda's passage, clear of the corridors' walls.
    for a, b, tag in ( ( -870.0, -140.0, "w" ), ( 140.0, 870.0, "e" ) ):
        aisle_tank( inside, lights, fr, a - base, b - base, 170.0, rng, f"Tunnel north tank {tag}" )
    south = [ window( a, b ) for a, b in bays ]
    fr, base = side_wall( model, TUNNEL, "s", 0, TUNNEL_SPRING, south, paints=WALL_DARK )
    baseboard( model, fr, 0, e1 - e0 )
    for e in PIERS:
        pilaster( model, fr, e - base, TUNNEL_SPRING, light=( e // 192 ) % 2 == 0 )
    aisle_tank( inside, lights, fr, 4.0, e1 - e0 - 4.0, 220.0, rng, "Tunnel south tank" )

    # The nave's floor emblem, and cover along it and in the aisles.
    decal( model, "rh_emblem", -130, 130, -1630, -1370, NAVE_Z )
    drain( model, -1000, -160, -1504, -1496, NAVE_Z )
    drain( model, 160, 1000, -1504, -1496, NAVE_Z )
    for e in ( -560.0, 560.0 ):
        bench( model, ( e, -1500 ), 0.0, z=NAVE_Z )
    for e in ( -820.0, 820.0 ):
        display_case( model, ( e, -1500 ), ( 44, 44 ), z=NAVE_Z, tank_name="display", rng=rng, inside=inside )
    skip_cases( rng, stacks=3 )
    display_case( model, ( 400, -1820 ), ( 40, 40 ), tank_name="display", rng=rng, inside=inside )
    lectern( model, ( -400, -1180 ), 180.0 )


# ---------------------------------------------------------------------------------------------------------------------
# The rooms: each a model with collision and one of its tanks' insides, drawn only. ( name, builder, mirror images )

ROOMS = [
    ( "rotunda", rotunda, [] ),
    ( "galleries", gallery_west, [ ( True, False, "east" ) ] ),
    ( "passages", rotunda_north, [ ( False, True, "south" ) ] ),
    ( "service", service_northwest, [ ( True, False, "NE" ), ( False, True, "SW" ), ( True, True, "SE" ) ] ),
    ( "lobby", lobby, [] ),
    ( "control", control_room, [] ),
    ( "filter", filter_hall, [] ),
    ( "tunnel", tunnel_hall, [] ),
]


def build_rooms():
    """ [ ( name, model, insides ) ] and every light, each room with its own steady random numbers. """
    rooms, lights = [], []
    for k, ( name, builder, flips ) in enumerate( ROOMS ):
        model, inside, room_lights = build_mirrored( builder, np.random.default_rng( 1000 + k ), flips )
        for m in ( model, inside ):
            configure( m )
        rooms.append( ( name, model, inside ) )
        lights += room_lights
    seen = {}
    named = []
    for name, position, colour, radius, shadows in lights:
        seen[name] = seen.get( name, 0 ) + 1
        named.append( ( name if seen[name] == 1 else f"{name} {seen[name]}", position, colour, radius, shadows ) )
    return rooms, named


# ---------------------------------------------------------------------------------------------------------------------
# Checks, as Tools/belltower_map.py makes them

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


# Walking: a 2.5D grid of the level tops of the collision, kept REACH_RADIUS from anything in the way as the navmesh
# keeps its agents, with headroom for a crouch, and joined where neighbouring floors are within a step. It stands in
# for the navmesh while the editor is busy, and finds the places nobody can walk to.

REACH_CELL = 8.0
REACH_BOUNDS = ( -2920.0, 2920.0, -1920.0, 1872.0 )    # e0, e1, n0, n1
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
    if len( outline ) == 0:
        return np.zeros( 0, int )
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
    """ Every spot must be on the largest walkable area (the one both spawns are on). Prints the ones that aren't and
    returns how many; picture writes the grid: green walkable, blue upstairs, red and orange cut off. """
    e0, e1, n0, n1 = REACH_BOUNDS
    cols, rows = int( ( e1 - e0 ) / REACH_CELL ), int( ( n1 - n0 ) / REACH_CELL )
    in_way = [ [] for _ in range( cols * rows ) ]
    floors = [ [] for _ in range( cols * rows ) ]

    def add( points, top, level ):
        z0, z1 = float( points[:, 2].min() ), float( points[:, 2].max() )
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
# The radar picture

MINIMAP_CENTRE = ( 0.0, -25.0 )      # plan ( e, n ) at the picture's centre: the Minimap Renderer's position
MINIMAP_SIZE = 6000.0
MINIMAP_PIXELS = 1024


def floor_level( e, n ):
    """ The ground floor's walking level: 0, and the Tunnel Hall's sunken aisle. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    s0, s1 = NAVE
    nave = ( np.abs( e ) <= TUNNEL[1] ) & ( n > s0 + NAVE_STEPS ) & ( n < s1 - NAVE_STEPS )
    steps = ( np.abs( e ) <= TUNNEL[1] ) & ( ( ( n >= s0 ) & ( n <= s0 + NAVE_STEPS ) ) | ( ( n >= s1 - NAVE_STEPS ) & ( n <= s1 ) ) )
    z = np.where( nave, NAVE_Z, 0.0 )
    return np.where( steps, NAVE_Z / 2, z )


def collision_shapes( models ):
    """ Every collision shape's corner points ( k, 3 ), in plan. """
    for model in models:
        for centre, axes, size, _ in model.boxes:
            ax = np.array( axes, float )
            half = np.asarray( size, float ) / 2
            yield np.array( [ np.asarray( centre, float ) + ax[0] * a * half[0] + ax[1] * b * half[1] + ax[2] * c * half[2]
                              for a in ( -1, 1 ) for b in ( -1, 1 ) for c in ( -1, 1 ) ] )
        for points, _ in model.hulls:
            yield np.array( points, float )


def write_minimap( models ):
    """ The ground floor, drawn from the collision's own outlines: where you can walk (grey, the tunnel's sunken aisle
    a little bluer), low cover (darker), walls and tanks left clear, and a light line round the edges. North is up. """
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "low", "tall" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    for pts in collision_shapes( models ):
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = hull_2d( pts[:, :2] )
        if len( outline ) < 3 or outline[:, 0].mean() < -2925:     # the closed gallery behind the lobby's doors
            continue
        f = float( floor_level( *outline.mean( axis=0 ) ) )
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if f - 24 <= z1 <= f + 18:
            draws["walk"].polygon( screen, fill=255 )
        elif z0 < f + 72 and z1 > f + 18:
            draws["low" if z1 < f + 100 else "tall"].polygon( screen, fill=255 )
    walk, low, tall = ( np.asarray( masks[k] ) > 127 for k in ( "walk", "low", "tall" ) )
    cols = left + ( np.arange( px ) + 0.5 ) * scale
    rows = top - ( np.arange( px ) + 0.5 ) * scale
    level = floor_level( *np.meshgrid( cols, rows ) )
    image = np.zeros( ( px, px, 4 ), np.uint8 )
    image[walk] = ( 95, 98, 104, 235 )
    image[walk & ( level < -1 )] = ( 84, 90, 98, 235 )
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
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( e, n, 0 ) for e in ( -2850, -2770, -2690 ) for n in ( -300, -100, 100, 300 ) ]
BLUE_SPAWNS = [ ( e, n, 0 ) for e in ( 2760, 2840 ) for n in ( -600, -400, -200, 200, 400, 600 ) ]

DM_WEST = [ ( -2300, 700, 0 ), ( -2300, -700, 0 ), ( -1800, 450, 0 ), ( -2800, 900, L1 ), ( -1500, 0, 0 ), ( -1300, 0, L1 ),
            ( -1430, 610, 0 ), ( -1010, 900, 0 ), ( -700, 1300, 0 ), ( -600, 1760, L1 ), ( -600, -1200, 0 ), ( -400, -1500, NAVE_Z ),
            ( -560, -1810, 0 ) ]
DM_SPAWNS = DM_WEST + [ ( 1430, -610, 0 ), ( 1010, -900, 0 ), ( 700, 1500, 0 ), ( 950, 1200, L1 ), ( 600, -1800, 0 ),
                        ( 1500, 0, 0 ), ( 1300, 0, L1 ), ( 2200, -600, 0 ), ( 2300, 640, L1 ), ( 2200, 700, 0 ),
                        ( 520, -300, 0 ), ( -520, 300, 0 ), ( 0, -700, L1 ), ( 0, 990, 0 ), ( 0, -990, 0 ) ]

# Retakes: the planter and the defenders are Red Team (Terrorist), the attackers Blue Team (CounterTerrorist).
RETAKES = {
    "bombsite_a": { "planter": [ ( 700, 1300, 0 ), ( 800, 1460, 0 ) ],
                    "defender": [ ( 300, 1760, L1 ), ( 1060, 1500, L1 ), ( 950, 1200, L1 ), ( 0, 1500, 0 ) ],
                    "attacker": [ ( -1430, 610, 0 ), ( 1430, 610, 0 ), ( 1400, 50, 0 ), ( -1400, 50, 0 ), ( 520, -300, 0 ) ] },
    "bombsite_b": { "planter": [ ( 850, -1440, NAVE_Z ), ( 400, -1580, NAVE_Z ) ],
                    "defender": [ ( 900, -1200, 0 ), ( 300, -1800, 0 ), ( 1050, -1580, NAVE_Z ), ( 500, -1180, 0 ) ],
                    "attacker": [ ( -1430, -610, 0 ), ( 1430, -610, 0 ), ( 1400, -50, 0 ), ( -1400, -50, 0 ), ( 520, 300, 0 ) ] },
}

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 150, 1130, 1120, 1660, 0 ),
               ( "bombsite_b", "Bomb Site B", 150, 1130, -1880, -1120, NAVE_Z ) ]

DOMINATION = [ ( "A", ( -1300, 70, 0 ) ), ( "B", ( 0, -620, 0 ) ), ( "C", ( 1300, 70, 0 ) ) ]
HOT_ZONES = [ ( "Rotunda", ( 0, -620, 0 ) ), ( "Filter Hall", ( 0, 1500, 0 ) ), ( "Tunnel", ( 0, -1420, NAVE_Z ) ),
              ( "Rotunda Balcony", ( 0, 720, L1 ) ), ( "West Gallery", ( -1300, 70, 0 ) ), ( "East Gallery", ( 1300, 70, 0 ) ) ]
# Cash Grab: ( name, the cash, where it's taken ). The cash sits 8 over the floor and the extraction point 32.
CASH_POINTS = [ ( "Filter Hall", ( 0, 1500, 0 ), ( 0, -1420, NAVE_Z ) ),
                ( "Tunnel", ( 0, -1420, NAVE_Z ), ( 0, 1500, 0 ) ),
                ( "Rotunda", ( 0, -620, 0 ), ( 0, 720, L1 ) ) ]

# Callouts for the location readout: ( name, e0, e1, n0, n1[, z0, z1] ), z -60..150 when left out.
UP = ( 150, 460 )
CALLOUTS = [
    ( "LOBBY", -2900, -1720, -1000, 1000, -60, 150 ), ( "LOBBY BALCONY", -2900, -1720, -1000, 1000, *UP ),
    ( "CONTROL ROOM", 1720, 2900, -900, 900, -60, 150 ), ( "CONTROL WALKWAY", 1720, 2900, -900, 900, *UP ),
    ( "OFFICE", 1720, 2250, 720, 900, *UP ),
    ( "WEST GALLERY", -1720, -850, -110, 110, -60, 150 ), ( "WEST UPPER GALLERY", -1720, -850, -110, 110, *UP ),
    ( "EAST GALLERY", 850, 1720, -110, 110, -60, 150 ), ( "EAST UPPER GALLERY", 850, 1720, -110, 110, *UP ),
    ( "ROTUNDA", -850, 850, -850, 850, -60, 150 ), ( "ROTUNDA BALCONY", -850, 850, -850, 850, *UP ),
    ( "NORTH PASSAGE", -110, 110, 850, 1100 ), ( "SOUTH PASSAGE", -110, 110, -1100, -850 ),
    ( "NORTH-WEST SERVICE", -1720, -900, 500, 1100 ), ( "NORTH-EAST SERVICE", 900, 1720, 500, 1100 ),
    ( "SOUTH-WEST SERVICE", -1720, -900, -1100, -500 ), ( "SOUTH-EAST SERVICE", 900, 1720, -1100, -500 ),
    ( "FILTER HALL", -1150, 150, 1100, 1850, -60, 150 ), ( "A SITE", 150, 1150, 1100, 1850, -60, 150 ),
    ( "CATWALK", -1150, 1150, 1670, 1850, *UP ), ( "MEZZANINE", 586, 1150, 1100, 1670, *UP ),
    ( "TUNNEL", -1150, 150, -1900, -1100, -100, 150 ), ( "B SITE", 150, 1150, -1900, -1100, -100, 150 ),
]

# Reflection probes: ( name, centre, the box they cover e0, e1, n0, n1, z0, z1 ). Each renders its room once.
PROBES = [
    ( "Lobby", ( -2310, 0, 160 ), ( -2900, -1720, -1000, 1000, 0, 620 ) ),
    ( "Rotunda", ( 0, -560, 150 ), ( -850, 850, -850, 850, 0, 560 ) ),
    ( "Control Room", ( 2300, -300, 150 ), ( 1720, 2900, -900, 900, 0, 440 ) ),
    ( "Filter Hall", ( 0, 1250, 150 ), ( -1150, 1150, 1100, 1850, 0, 440 ) ),
    ( "Tunnel Hall", ( 0, -1500, 100 ), ( -1150, 1150, -1900, -1100, NAVE_Z, 400 ) ),
    ( "West Gallery", ( -1300, 0, 100 ), ( -1720, -850, -110, 110, 0, 388 ) ),
    ( "East Gallery", ( 1300, 0, 100 ), ( 850, 1720, -110, 110, 0, 388 ) ),
    ( "North Passage", ( 0, 980, 90 ), ( -110, 110, 850, 1100, 0, 180 ) ),
    ( "South Passage", ( 0, -980, 90 ), ( -110, 110, -1100, -850, 0, 180 ) ),
    ( "North-West Service", ( -1300, 610, 90 ), ( -1720, -900, 500, 1100, 0, 180 ) ),
    ( "North-East Service", ( 1300, 610, 90 ), ( 900, 1720, 500, 1100, 0, 180 ) ),
    ( "South-West Service", ( -1300, -610, 90 ), ( -1720, -900, -1100, -500, 0, 180 ) ),
    ( "South-East Service", ( 1300, -610, 90 ), ( 900, 1720, -1100, -500, 0, 180 ) ),
    ( "Lobby Door Gallery", ( -3060, 0, 90 ), ( -3200, -2920, -400, 400, 0, 180 ) ),
]


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
    """ A TeamSpawnPoint facing the map's middle. """
    yaw = K.plan_yaw( ( -position[0], -position[1] * 0.35 ) )
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


def probe_object( name, centre, box ):
    """ An EnvmapProbe that renders its room once, when it's enabled (box projected onto the room). """
    e0, e1, n0, n1, z0, z1 = box
    at = K.to_world( centre )
    lo = K.to_world( ( e1, n0, z0 ) ) - at
    hi = K.to_world( ( e0, n1, z1 ) ) - at
    key = f"probe/{name}"
    return K.game_object( ids, f"Probe {name}", key, at, components=[
        K.component( ids, "Sandbox.EnvmapProbe", f"{key}/probe", Bounds={ "Mins": K.vec( lo ), "Maxs": K.vec( hi ) },
                     DelayBetweenUpdates=0.1, Feathering=0.04, FrameInterval=5, MaxDistance=512, Projection="Box",
                     RenderDynamically=True, TintColor="1,1,1,1", UpdateStrategy="OnEnabled", ZFar=4096, ZNear=8 ) ] )


FAUNA = "models/maps/reefhall/fauna"

# What lives in each tank, by its size. Each entry is ( species, how many ): a group's count is the whole group (a pair
# is 2), a solo species' how many lone fish. Neighbouring tanks of a size take the variants in turn, so no two beside
# each other hold the same mix. All of them are Indo-Pacific reef species, so every tank is a plausible reef community:
# the clownfish and Banggai cardinals near the rocks, mandarins on the sand, the tangs, angels and idols grazing along the
# reef, the chromis, sergeant majors and fusiliers schooling over it, and the sharks and mantas in the open water of the
# biggest tanks. Every tank gets fish: where none of its mix fits, the first small fish that does.
FAUNA_SMALL = [
    [ ( "clownfish", 2 ), ( "banggai", 6 ), ( "chromis", 10 ) ],
    [ ( "mandarin", 1 ), ( "clownfish", 2 ), ( "chromis", 12 ) ],
    [ ( "lionfish", 1 ), ( "banggai", 5 ), ( "mandarin", 1 ) ],
    [ ( "copperband", 1 ), ( "chromis", 10 ), ( "clownfish", 2 ) ],
    [ ( "banggai", 7 ), ( "mandarin", 2 ), ( "yellow_tang", 3 ) ],
    [ ( "puffer", 1 ), ( "clownfish", 2 ), ( "chromis", 8 ) ],
]
FAUNA_MID = [
    [ ( "yellow_tang", 5 ), ( "moorish_idol", 2 ), ( "chromis", 14 ), ( "clownfish", 2 ) ],
    [ ( "blue_tang", 4 ), ( "regal_angel", 1 ), ( "copperband", 1 ), ( "sergeant_major", 10 ) ],
    [ ( "yellow_tang", 4 ), ( "blue_tang", 3 ), ( "puffer", 1 ), ( "banggai", 6 ) ],
    [ ( "moorish_idol", 2 ), ( "regal_angel", 1 ), ( "lionfish", 1 ), ( "chromis", 16 ) ],
    [ ( "sergeant_major", 12 ), ( "copperband", 1 ), ( "clownfish", 2 ), ( "mandarin", 1 ) ],
]
FAUNA_BIG = [
    [ ( "fusilier", 22 ), ( "yellow_tang", 7 ), ( "blue_tang", 5 ), ( "moorish_idol", 2 ), ( "puffer", 1 ) ],
    [ ( "sergeant_major", 18 ), ( "fusilier", 16 ), ( "regal_angel", 2 ), ( "lionfish", 1 ), ( "chromis", 18 ) ],
    [ ( "blue_tang", 6 ), ( "yellow_tang", 6 ), ( "copperband", 2 ), ( "moorish_idol", 2 ), ( "sergeant_major", 14 ) ],
]
FAUNA_HUGE = [
    [ ( "reef_shark", 2 ), ( "fusilier", 30 ), ( "sergeant_major", 20 ), ( "yellow_tang", 8 ), ( "blue_tang", 6 ),
      ( "moorish_idol", 2 ), ( "puffer", 2 ), ( "regal_angel", 1 ) ],
    [ ( "reef_shark", 2 ), ( "manta_ray", 1 ), ( "fusilier", 34 ), ( "sergeant_major", 22 ), ( "yellow_tang", 8 ),
      ( "blue_tang", 7 ), ( "moorish_idol", 2 ), ( "puffer", 2 ), ( "chromis", 20 ) ],
    [ ( "reef_shark", 2 ), ( "manta_ray", 2 ), ( "fusilier", 36 ), ( "sergeant_major", 24 ), ( "yellow_tang", 8 ),
      ( "blue_tang", 8 ), ( "moorish_idol", 2 ), ( "regal_angel", 2 ), ( "puffer", 1 ) ],
]
FAUNA_FALLBACK = [ "clownfish", "mandarin", "banggai", "chromis" ]
# The least share of a tank's water (in the species' own depth band) where a body, or a group with its room, finds
# open water to swim to: below it the group shrinks, then the species is left out.
FAUNA_ROOM = 0.06


def fauna_sizes():
    """ Each model's reach and length (written by Tools/reefhall_fauna.py) with its behaviour (its SPECIES table). """
    import reefhall_fauna as F
    sizes = json.loads( ( Path( __file__ ).parent.parent / "Assets" / FAUNA / "fauna_species.json" ).read_text() )
    keys = ( "speed", "turn", "response", "climb", "bank", "low", "high", "above", "rocks", "home", "pause", "pausemin",
             "pausemax", "group", "spread" )
    out = {}
    for name, spec in F.SPECIES.items():
        out[name] = dict( sizes[name], **{ k: spec[k] for k in keys } )
        out[name].update( scalemin=spec["scale"][0], scalemax=spec["scale"][1], beat=spec["swim"]["beat"],
                          fin=spec["swim"]["fin"], ray=1 if spec.get( "ray" ) else 0 )
    return out


def fauna_room( spec, count ):
    """ The room TankFauna gives one of a species, or its group's leader (TankFauna.SpawnGroup): ( reach, up, and the
    spare room it wants round a destination, sideways and up ). """
    reach, up, length = spec["reach"] * spec["scalemax"], spec["up"] * spec["scalemax"], spec["length"]
    if spec["group"] == "solo" or count == 1:
        soft = min( max( length * spec["scalemax"] * 0.8, 2 ), 40 )
        return reach, up, soft * 0.6, soft * 0.3
    spacing = length * spec["scalemax"] * max( spec["spread"], 0.6 )
    radius = spacing * 0.5 if spec["group"] == "pair" else spacing * 0.55 * count ** ( 1 / 3 )
    soft = min( max( length * 1.5 + radius * 0.3, 3 ), 40 )
    return reach + radius * 0.7, up + radius * 0.35, soft * 0.6, soft * 0.3


def free_share( prop, obstacles, reach, up, band=( 0.0, 1.0 ), above=0.0, spare=( 0.0, 0.0 ), samples=4000, seed=1 ):
    """ The share of the water, within a depth band (shares of its height) and no higher than `above` over the sand,
    where a body of this reach (plus `spare` from the walls) is clear of the water's edges, the glass tube and the
    rocks, as TankFauna.TryPickGoal finds it. """
    rng = np.random.default_rng( seed )
    half = np.asarray( prop["size"], float ) / 2
    floor = -half[2]
    lo = max( floor + band[0] * 2 * half[2], floor + up )
    hi = min( floor + band[1] * 2 * half[2], half[2] - up )
    if above > 0:
        hi = min( hi, floor + above )
    if hi < lo:
        return 0.0
    p = rng.uniform( ( -half[0], -half[1], lo ), ( half[0], half[1], hi ), ( samples, 3 ) )
    wall, wall_up = reach + spare[0], up + spare[1]
    ok = np.abs( p[:, 2] ) <= half[2] - wall_up
    water = np.ones( samples, bool )
    if prop["fauna"] == "cylinder":
        ok &= np.hypot( p[:, 0], p[:, 1] ) <= half[0] - wall
        water = np.hypot( p[:, 0], p[:, 1] ) <= half[0]
    else:
        ok &= ( np.abs( p[:, 0] ) <= half[0] - wall ) & ( np.abs( p[:, 1] ) <= half[1] - wall )
    if prop["hole"]:
        centre = np.asarray( prop["position"], float )
        along = np.asarray( prop["along"], float )
        d = np.asarray( prop["hole"][1], float ) - centre
        hy, hz = np.dot( d[:2], ( -along[1], along[0] ) ), d[2]
        ok &= np.hypot( p[:, 1] - hy, p[:, 2] - hz ) >= prop["hole"][0] + reach
    for x, y, z, radius, height, taper in obstacles:
        within = ( p[:, 2] >= z - up ) & ( p[:, 2] <= z + height + up )
        t = np.clip( ( p[:, 2] - z ) / max( height, 1 ), 0, 1 )
        ok &= ~( within & ( np.hypot( p[:, 0] - x, p[:, 1] - y ) < radius * ( 1 - taper * t ) + reach ) )
    return float( ok.sum() / max( 1, water.sum() ) )


def fits( prop, obstacles, spec, count ):
    reach, up, spare, spare_up = fauna_room( spec, count )
    return free_share( prop, obstacles, reach, up, ( spec["low"], spec["high"] ), spec["above"], ( spare, spare_up ) ) >= FAUNA_ROOM


def fauna_class( prop ):
    """ small, mid, big or huge: which list of mixes a tank takes. """
    size = prop["size"]
    across = min( size[0], size[1] )
    volume = math.pi * ( size[0] / 2 ) ** 2 * size[2] if prop["fauna"] == "cylinder" else float( np.prod( size ) )
    if across >= 500 or ( prop["fauna"] == "cylinder" and across >= 450 ):
        return "huge"
    if volume >= 3.5e7:
        return "big"
    if volume >= 5.5e6:
        return "mid"
    return "small"


def fauna_volumes( rooms ):
    """ Each tank's water, with the rocks, coral and kelp standing in it and what lives there:
    [ ( room, prop, obstacles (local x y z radius height taper), [ ( species, count ) ] ) ]. Obstacles go to the water
    their foot is in. A species goes in only where it finds room (`fits`); a group too big for its tank gets smaller. """
    sizes = fauna_sizes()
    variants = { "small": FAUNA_SMALL, "mid": FAUNA_MID, "big": FAUNA_BIG, "huge": FAUNA_HUGE }
    turn = { key: 0 for key in variants }
    out = []
    for name, _, inside in rooms:
        volumes = [ prop for prop in inside.props if prop["fauna"] in ( "box", "cylinder" ) ]
        obstacles = [ prop for prop in inside.props if prop["fauna"] == "obstacle" ]
        for prop in volumes:
            centre = np.asarray( prop["position"], float )
            along = np.asarray( prop["along"], float )
            left = np.array( ( -along[1], along[0] ) )
            size = np.asarray( prop["size"], float )

            def local( point ):
                d = np.asarray( point, float ) - centre
                return np.array( ( np.dot( d[:2], along ), np.dot( d[:2], left ), d[2] ) )

            mine = []
            for ob in obstacles:
                q = local( ob["position"] )
                if prop["fauna"] == "cylinder":
                    inside_it = math.hypot( q[0], q[1] ) <= size[0] / 2 + 2
                else:
                    inside_it = abs( q[0] ) <= size[0] / 2 + 2 and abs( q[1] ) <= size[1] / 2 + 2
                if inside_it and -size[2] / 2 - 40 <= q[2] <= size[2] / 2:
                    mine.append( ( *q, ob["radius"], ob["height"], ob["taper"] ) )

            kind = fauna_class( prop )
            mix = variants[kind][turn[kind] % len( variants[kind] )]
            turn[kind] += 1
            groups = []
            for species, count in mix:
                spec = sizes[species]
                grouped = spec["group"] not in ( "solo", "pair" )
                while grouped and count > 3 and not fits( prop, mine, spec, count ):
                    count -= 1
                if spec["group"] == "pair" and not fits( prop, mine, spec, count ):
                    count = 1
                if fits( prop, mine, spec, 1 if spec["group"] == "solo" else count ):
                    groups.append( ( species, count ) )
            if not groups:
                for species in FAUNA_FALLBACK:
                    if fits( prop, mine, sizes[species], 1 ):
                        groups.append( ( species, 1 ) )
                        break
            if not groups:
                raise SystemExit( f"no fish fit the {name} tank at {np.round( centre )}" )
            out.append( ( name, prop, mine, groups ) )
    return out


def fauna_spec( spec, species, count ):
    """ A TankFauna group entry: "model=... key=value ...". One fish of a group species lives as a lone one. """
    keys = ( "count", "group", "reach", "up", "length", "scalemin", "scalemax", "speed", "turn", "response", "climb", "bank",
             "low", "high", "above", "rocks", "home", "pause", "pausemin", "pausemax", "spread", "beat", "fin", "ray" )
    values = dict( spec, count=count )
    if count == 1:
        values["group"] = "solo"
    text = " ".join( f"{key}={values[key]}" if isinstance( values[key], str ) else f"{key}={float( values[key] ):g}"
                     for key in keys )
    return f"model={FAUNA}/{species}.vmdl {text}"


def fauna_objects( rooms ):
    sizes = fauna_sizes()
    objects = []
    totals = {}
    allocation = fauna_volumes( rooms )
    for k, ( name, prop, obstacles, groups ) in enumerate( allocation ):
        key = f"fauna/{name}/{k}"
        centre = np.asarray( prop["position"], float )
        along = np.asarray( prop["along"], float )
        hole_radius, hole_centre = 0.0, ( 0.0, 0.0, 0.0 )
        if prop["hole"]:
            hole_radius = prop["hole"][0]
            d = np.asarray( prop["hole"][1], float ) - centre
            hole_centre = ( float( np.dot( d[:2], along ) ), float( np.dot( d[:2], ( -along[1], along[0] ) ) ), float( d[2] ) )
        text = ";".join( " ".join( f"{v:.1f}" if j < 3 else f"{v:.2f}" for j, v in enumerate( ob ) ) for ob in obstacles )
        for species, count in groups:
            totals[species] = totals.get( species, 0 ) + count
        obj = K.game_object( ids, f"{name.title()} Fauna {k}", key, K.to_world( centre ),
                             rotation=K.yaw_rotation( K.plan_yaw( along ) ), components=[
            K.component( ids, "Facepunch.TankFauna", f"{key}/fauna",
                         Shape="Cylinder" if prop["fauna"] == "cylinder" else "Box",
                         Size=K.vec( prop["size"] ), HoleRadius=round( hole_radius, 2 ), HoleCentre=K.vec( hole_centre ),
                         Obstacles=text, Groups=[ fauna_spec( sizes[s], s, c ) for s, c in groups ],
                         Seed=7000 + k, FarDistance=3000 ) ] )
        obj["NetworkMode"] = 0
        objects.append( obj )
    print( f"fauna: {len( allocation )} tanks, {sum( totals.values() )} animals: "
           + ", ".join( f"{totals[s]} {s}" for s in sorted( totals ) ) )
    return objects


def write_scene( rooms, lights ):
    # A room with no tanks gets no tanks model (`map_kit.write_model` writes none: an empty one hung the editor).
    building = K.game_object( ids, "Aquarium", "aquarium", children=[
        child for name, _, inside in rooms for child in (
            model_object( name.title(), f"aquarium/{name}", f"reefhall_{name}" ),
            *( [] if K.is_empty( inside ) else [ model_object( f"{name.title()} Tanks", f"aquarium/{name}/tanks",
                                                               f"reefhall_{name}_tanks", collide=False, shadows=False ) ] ) ) ] )
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
        zone_object( "buyzone_t", "buy/t", ( LOBBY[0], LOBBY[1], LOBBY[2], LOBBY[3], 0, 420 ), "1,0.18,0.2,1", "Red Team Buy Zone",
                     [ K.component( ids, "Facepunch.BuyZone", "buy/t/zone_buy", Team="Terrorist" ) ] ),
        zone_object( "buyzone_ct", "buy/ct", ( CONTROL[0], CONTROL[1], CONTROL[2], CONTROL[3], 0, 420 ), "0,0.41569,1,1",
                     "Blue Team Buy Zone", [ K.component( ids, "Facepunch.BuyZone", "buy/ct/zone_buy", Team="CounterTerrorist" ) ] ),
    ]

    callouts = []
    for c in CALLOUTS:
        name, e0, e1, n0, n1 = c[:5]
        z0, z1 = c[5:7] if len( c ) > 5 else ( -60, 150 )
        callouts.append( zone_object( name, f"callout/{name}", ( e0, e1, n0, n1, z0, z1 ), CALLOUT_COLOUR, name,
                                      [ K.component( ids, "Facepunch.MapLocation", f"callout/{name}/location" ) ] ) )

    play_centre, play_scale = plan_box( -2940, 2940, -1940, 1890, -120, 800 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )

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
                         Description="A public aquarium after hours: the lobby and the control room at either end, the "
                                     "rotunda round its great tank between them, the filter hall and the glass tunnel.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # Indoors: no sun or sky. A faint cool ambient under the lamps, as the tanks' glow fills the rooms.
        K.game_object( ids, "Ambient", "ambient", components=[
            K.component( ids, "Sandbox.AmbientLight", "ambient/light", Color="0.06,0.095,0.14,1" ) ] ),
        K.game_object( ids, "Fog", "fog", components=[
            K.component( ids, "Sandbox.GradientFog", "fog/gradient", Color="0.05,0.09,0.12,0.25", StartDistance=1200,
                         EndDistance=9000, FalloffExponent=1.4, Height=1200, VerticalFalloffExponent=1.0 ),
        ] ),
        building,
        climbable_pipe_objects(),
        K.game_object( ids, "Fauna", "fauna", children=fauna_objects( rooms ) ),
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in PROBES ] ),
        mode_group( "Team Spawns", "spawns", ( "Deathmatch", "Gun Game" ), team_spawns, inverse=True ),
        mode_group( "Deathmatch Spawns", "spawns/dm", ( "Deathmatch", "Gun Game" ), dm_spawns ),
        mode_group( "Retakes Spawns", "spawns/retakes", ( "Retakes", ), retakes_spawns ),
        K.game_object( ids, "Bomb Sites", "sites", children=bomb_sites ),
        K.game_object( ids, "Buy Zones", "buy", children=buy_zones ),
        K.game_object( ids, "Callouts", "callouts", children=callouts ),
        play_area,
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
                "Bounds": { "Mins": K.vec( K.to_world( ( 2940, -1940, -100 ) ) ),
                            "Maxs": K.vec( K.to_world( ( -2940, 1890, 700 ) ) ) },
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


# ---------------------------------------------------------------------------------------------------------------------

VIEWS = [
    ( "lobby", ( -2860, -500, 64 ), ( -1800, 300, 260 ), 90 ),
    ( "lobby_doors", ( -2600, 120, 70 ), ( -2900, -20, 80 ), 75 ),
    ( "lobby_balcony", ( -1800, 900, 272 ), ( -2700, -300, 200 ), 90 ),
    ( "west_gallery", ( -1690, 0, 64 ), ( -800, 0, 80 ), 80 ),
    ( "rotunda", ( -780, -200, 64 ), ( 0, 0, 260 ), 90 ),
    ( "rotunda_balcony", ( 700, -300, 272 ), ( -300, 300, 260 ), 90 ),
    ( "filter", ( 0, 1140, 64 ), ( 0, 1800, 200 ), 90 ),
    ( "filter_catwalk", ( -1000, 1760, 272 ), ( 900, 1300, 150 ), 90 ),
    ( "tunnel", ( -1100, -1500, 24 ), ( 1100, -1500, 200 ), 90 ),
    ( "control", ( 1900, -500, 64 ), ( 2900, 100, 220 ), 90 ),
]


def write_previews( out_dir, rooms ):
    out = Path( out_dir )
    out.mkdir( parents=True, exist_ok=True )
    models = [ m for _, model, inside in rooms for m in ( model, inside ) ]
    bounds = ( -3000, 3000, -2150, 2150 )
    top_down( models, bounds, 5, cut=190 ).save( out / "top_ground.png" )
    top_down( models, bounds, 5, cut=430 ).save( out / "top_upper.png" )
    opaque, glass = triangles( models ), triangles( models, glass=True )
    for name, eye, target, fov in VIEWS:
        perspective( opaque, glass, eye, target, fov=fov ).save( out / f"{name}.png" )
    print( f"wrote previews to {out}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", help="also write top-down pictures and views from head height to this folder" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    args = parser.parse_args()

    rooms, lights = build_rooms()
    write_tank_materials()
    known = set( RM.paints() ) | { tank_paint( t ) for t in TANKS }
    missing = sorted( { p for _, m, i in rooms for model in ( m, i ) for p in model.polygons } - known )
    if missing:
        print( f"paints with no material: {', '.join( missing )}" )
    for name, model, inside in rooms:
        count = K.write_model( OUT_DIR, RESOURCE_DIR, f"reefhall_{name}", model )
        tanks = K.write_model( OUT_DIR, RESOURCE_DIR, f"reefhall_{name}_tanks", inside )
        print( f"reefhall_{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls; its tanks {tanks}" )
    print( f"{len( lights )} lights" )

    solid = [ model for _, model, _ in rooms ]
    aabbs = collision_aabbs( solid )
    print( "checking spots:" )
    problems = check_spots( aabbs, all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    if args.preview:
        Path( args.preview ).mkdir( parents=True, exist_ok=True )
    cut_off = check_reach( solid, all_spots(), Path( args.preview ) / "reach.png" if args.preview else None )
    print( f"  {cut_off} spot(s) cut off from the spawns" )
    import railhead_map as R
    seen = R.check_retakes_sight( R.Blockers( solid ), RETAKES )
    print( f"  {seen} Retakes pair(s) in sight of each other" )

    if not args.no_scene:
        write_minimap( solid )
        write_scene( rooms, lights )
    if args.preview:
        write_previews( args.preview, rooms )

# ---------------------------------------------------------------------------------------------------------------------
# Previews: flat-shaded pictures for checking without the editor. Indoors there's no sun: faces are lit from the eye
# (a headlamp), self-lit paints glow, and tank glass tints what's behind it by the water between, as the shader does.

_paint_colours = {}


def paint_colour( paint ):
    if paint not in _paint_colours:
        path = RM.OUT_DIR / f"{paint}_color.png"
        if paint.startswith( "rh_tank_glass" ):
            _paint_colours[paint] = np.array( ( 0.05, 0.35, 0.45 ) )
        elif paint in ( "rh_glass", "rh_glass_office" ):
            _paint_colours[paint] = np.array( ( 0.75, 0.85, 0.88 ) )
        elif path.exists():
            small = Image.open( path ).convert( "RGB" ).resize( ( 32, 32 ) )
            _paint_colours[paint] = np.asarray( small, float ).reshape( -1, 3 ).mean( axis=0 ) / 255.0
        else:
            _paint_colours[paint] = np.array( ( 1.0, 0.0, 1.0 ) )
    return _paint_colours[paint]


def is_glass( paint ):
    return paint.startswith( "rh_tank_glass" ) or paint in ( "rh_glass", "rh_glass_office" )


def triangles( models, glass=False ):
    """ ( triangles ( T, 3, 3 ), normals, colours, self-lit ) of the opaque paints, or with glass, of the tank glass. """
    tris, normals, colours, glow = [], [], [], []
    for model in models:
        for paint, items in model.polygons.items():
            if glass != paint.startswith( "rh_tank_glass" ) or ( not glass and is_glass( paint ) ):
                continue
            base = paint_colour( paint )
            lit = paint in RM.ILLUM
            for points, normal in items:
                for k in range( 1, len( points ) - 1 ):
                    tris.append( ( points[0], points[k], points[k + 1] ) )
                    normals.append( normal )
                    colours.append( base )
                    glow.append( lit )
    return ( np.array( tris, float ).reshape( -1, 3, 3 ), np.array( normals, float ).reshape( -1, 3 ),
             np.array( colours, float ).reshape( -1, 3 ), np.array( glow, bool ) )


def rasterise( image, depth, screen, nearness, colours ):
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
    points = []
    for k in range( 3 ):
        a, b = tri[k], tri[( k + 1 ) % 3]
        if a[2] >= near:
            points.append( a )
        if ( a[2] >= near ) != ( b[2] >= near ):
            points.append( a + ( near - a[2] ) / ( b[2] - a[2] ) * ( b - a ) )
    return [ np.array( ( points[0], points[k], points[k + 1] ) ) for k in range( 1, len( points ) - 1 ) ]


def perspective( opaque, glass, eye, target, size=( 960, 540 ), fov=80.0 ):
    width, height = size
    eye, target = np.asarray( eye, float ), np.asarray( target, float )
    forward = normalise( target - eye )
    right = normalise( np.cross( forward, ( 0.0, 0.0, 1.0 ) ) )
    up = np.cross( right, forward )
    focal = ( width / 2 ) / math.tan( math.radians( fov ) / 2 )
    near = 2.0

    def draw( data, image, depth, shaded=True ):
        tris, normals, cols, glow = data
        if not len( tris ):
            return
        centres = tris.mean( axis=1 ) - eye
        facing_eye = np.einsum( "ij,ij->i", normals, eye - tris[:, 0] ) > 0
        cam = np.stack( ( ( tris - eye ) @ right, ( tris - eye ) @ up, ( tris - eye ) @ forward ), axis=-1 )
        keep = facing_eye & ( cam[:, :, 2].max( axis=1 ) > near )
        cam, c, g, n, rc = cam[keep], cols[keep], glow[keep], normals[keep], centres[keep]
        dist = np.maximum( np.linalg.norm( rc, axis=1 ), 1.0 )
        shade = 0.3 + 0.7 * np.abs( np.einsum( "ij,ij->i", n, -rc / dist[:, None] ) )
        shade *= 0.8 + 0.2 * n[:, 2]
        shade *= np.clip( 1.6 - dist / 2200.0, 0.45, 1.0 )
        lit = np.where( g[:, None], np.minimum( c * 1.5 + 0.2, 1.0 ), c * shade[:, None] ) if shaded else c
        whole = ( cam[:, :, 2] >= near ).all( axis=1 )
        pieces, pc = [ cam[whole] ], [ lit[whole] ]
        for tri, col in zip( cam[~whole], lit[~whole] ):
            for part in clip_near( tri, near ):
                pieces.append( part[None] )
                pc.append( col[None] )
        cam, lit = np.concatenate( pieces ), np.concatenate( pc )
        screen = np.stack( ( width / 2 + focal * cam[:, :, 0] / cam[:, :, 2], height / 2 - focal * cam[:, :, 1] / cam[:, :, 2] ),
                           axis=-1 )
        on = ( ( screen[:, :, 0].max( axis=1 ) >= 0 ) & ( screen[:, :, 0].min( axis=1 ) < width )
               & ( screen[:, :, 1].max( axis=1 ) >= 0 ) & ( screen[:, :, 1].min( axis=1 ) < height ) )
        rasterise( image, depth, screen[on], 1.0 / cam[on][:, :, 2], lit[on] )

    image = np.tile( np.array( ( 0.02, 0.03, 0.04 ) ), ( height, width, 1 ) )
    depth = np.zeros( ( height, width ) )
    draw( opaque, image, depth )
    gimage, gdepth = np.zeros_like( image ), np.zeros_like( depth )
    draw( glass, gimage, gdepth, shaded=False )
    over = gdepth > depth
    if over.any():
        # The view ray's length per unit of depth, to turn depths into the water's path.
        xs = ( np.arange( width ) + 0.5 - width / 2 ) / focal
        ys = ( height / 2 - np.arange( height ) - 0.5 ) / focal
        stretch = np.sqrt( 1 + xs[None, :] ** 2 + ys[:, None] ** 2 )
        behind = np.where( depth > 0, 1.0 / np.maximum( depth, 1e-9 ), 1e5 )
        water = np.clip( ( behind - 1.0 / np.maximum( gdepth, 1e-9 ) ) * stretch, 0, 800 )[..., None]
        transmit = np.exp( -np.array( ( 0.0072, 0.0031, 0.0023 ) ) * water )
        medium = np.array( ( 0.03, 0.20, 0.30 ) )
        tinted = ( image * 1.3 ) * transmit + medium * ( 1 - transmit ) + 0.025
        image[over] = tinted[over]
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


def top_down( models, bounds, scale, cut=None ):
    """ Straight down: bounds ( e0, e1, n0, n1 ), scale units a pixel; cut leaves out everything higher. """
    tris, normals, colours, glow = triangles( models )
    gt, gn, gc, gg = triangles( models, glass=True )
    tris, normals = np.concatenate( ( tris, gt ) ), np.concatenate( ( normals, gn ) )
    colours = np.concatenate( ( colours, np.tile( ( 0.1, 0.45, 0.55 ), ( len( gt ), 1 ) ) ) )
    e0, e1, n0, n1 = bounds
    width, height = int( ( e1 - e0 ) / scale ), int( ( n1 - n0 ) / scale )
    image = np.tile( np.array( ( 0.06, 0.07, 0.08 ) ), ( height, width, 1 ) )
    depth = np.full( ( height, width ), -1e9 )
    keep = ( normals[:, 2] > 0.02 ) & ( tris[:, :, 0].max( axis=1 ) > e0 ) & ( tris[:, :, 0].min( axis=1 ) < e1 ) \
        & ( tris[:, :, 1].max( axis=1 ) > n0 ) & ( tris[:, :, 1].min( axis=1 ) < n1 )
    if cut is not None:
        keep &= tris[:, :, 2].max( axis=1 ) <= cut
    t = tris[keep]
    shade = np.clip( 0.6 + t[:, :, 2].mean( axis=1 ) / 900.0, 0.45, 1.25 )[:, None]
    screen = np.stack( ( ( t[:, :, 0] - e0 ) / scale, ( n1 - t[:, :, 1] ) / scale ), axis=-1 )
    rasterise( image, depth, screen, t[:, :, 2], np.clip( colours[keep] * shade, 0, 1 ) )
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


if __name__ == "__main__":
    main()
