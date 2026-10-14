"""
Railhead: a multiplayer map. Hohenwald Hauptbahnhof (Hohenwald Hbf, a made-up city), a German terminus at 14:03 on an
October afternoon: the iron-and-glass train shed over six tracks and four platforms, the sandstone head building with
its booking hall, a cab road down each side, the station throat with its signal box, and the goods yards beyond.

    python Tools/railhead_map.py [--preview <dir> [view ...]] [--no-scene] [--backdrop] [--art]

Built from four scripts, as Belltower's and Reef Hall's are built from theirs:
- Tools/railhead_station.py: the structure (the shed, its roof, the head building, the platforms, the footbridge,
  the canopies, the cab roads' arcades, the goods yards' sheds, the signal box).
- Tools/railhead_props.py: the track and its equipment, the trains and wagons, containers, furniture and clutter.
- Tools/railhead_backdrop.py: the city round it: the tenements along the play's edge (east, mirrored for the west),
  the forecourt and the streets to the north, the railway running south, and the skyline.
- Tools/railhead_materials.py: the rw_ paints and their atlases (signs, displays, posters, shop signs, lettering).
This script puts them together, dresses the station (where every train, sign, bench and lamp goes), and writes:
- the models, to Assets/models/maps/railhead/;
- the scene, Assets/scenes/maps/Railhead/railhead.scene, rewritten whole on every run (change the layout here, not
  in the editor);
- the radar picture, ui/minimaps/minimap_railhead.png, and with --preview and --art a stand-in menu picture,
  ui/maps/railhead.png, from the aerial preview.

Plan coordinates: e east, n north, z up, in inches (map_kit's). The station is mirrored across e = 0: Red Team spawns
on the west cab road, Blue Team on the east. The play area is e -2200..2200, n -2400..1820.

The three lanes:
- North: the concourse (Querbahnsteig) across the platforms' heads, and the booking hall behind it. Bomb site A is
  the concourse's east end.
- Middle: the platforms under the shed, crossed by the footbridge, with trains standing at Gleis 1, 3, 4 and 6.
- South: the platform ends under their canopies, the throat round the signal box, and the goods yards. Bomb site B is
  in the east goods yard.

Every run checks every spawn, objective and cash spot: room for a player and a floor under it (`check_spots`), a walk
to it from the spawns (`check_reach`, a 2.5D grid of the collision's walkable tops that stands in for the navmesh), and
that no Retakes Red spawn can see a Blue one (`check_retakes_sight`). With --preview it also writes flat-shaded views
(railhead_preview's) and the reach grid's picture to that folder.

The navmesh: its bounds stop at NAV_TOP (420), over the footbridge's deck (212), the highest floor anyone walks on, and
under the shed's roofs (554-744). The canopies' glass and the goods sheds' 24-degree roofs are in railhead_glass, whose
object is tagged navskip, which the NavMesh's ExcludedBodies leaves out: on their own they'd be islands of navmesh. The
reach check walks the same collision (NAV_SKIP's models are left out of it). What's still an island under NAV_TOP
(the trains' and platform canopies' roofs, the footbridge's roof, the wings' upper storeys, the kiosks' and shelters'
tops) can't be reached from the floors, and bots check their paths before they set off.
"""
import argparse
import importlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import building_textures as BT
import map_kit as K
from map_kit import Model
import railhead_preview as PV
import railhead_station as S

TITLE = "Railhead"
OUT_DIR = K.ASSETS / "models/maps/railhead"
RESOURCE_DIR = "models/maps/railhead"
SCENE_FILE = K.ASSETS / "scenes/maps/Railhead/railhead.scene"
MINIMAP_PATH = "ui/minimaps/minimap_railhead.png"
MINIMAP_FILE = K.ASSETS / MINIMAP_PATH
MAP_ART_PATH = "ui/maps/railhead.png"
MAP_ART_FILE = K.ASSETS / MAP_ART_PATH

ids = K.SceneIds( "8e4a2c71-3f9b-4d16-a5e2-7c0b9d3f6a18" )

METAL, STONE, WOOD, GLASS = "metal", "default", "wood", "glass"


def optional( name ):
    """ A helper module, or None if it won't import (it's still being written, say): the map is then built with
    stand-ins for what it would have added. """
    try:
        return importlib.import_module( name )
    except Exception as error:
        print( f"{name} isn't usable ({type( error ).__name__}: {error}); using stand-ins" )
        return None


RM = optional( "railhead_materials" )
P = optional( "railhead_props" )
RB = optional( "railhead_backdrop" )

# The sky (Tools/railhead_sky.py) and the light: 14:03 summer time on 3 October at 48 N, 11 E.
SUN_PITCH, SUN_YAW = 38.0, -15.0
SKY_MATERIAL = "materials/railhead/sky/railhead_sky.vmat"
SKY_EXPOSURE = 2.0
FOG_COLOUR = "0.351,0.594,1.048"
CATCH_FLOOR_Z = -3000

PLAY = ( -2200.0, 2200.0, -2400.0, 1820.0 )         # e0, e1, n0, n1
# The navmesh stops at NAV_TOP, under the roofs (the shed's, the hall's and the wings', 554-744 up), which would
# otherwise be islands of it. The highest floor is the footbridge's deck at 212.
NAV_TOP = 420.0
# Models whose collision the navmesh leaves out (their objects are tagged navskip): the station's glass, whose only
# collision is what nobody can get onto and the navmesh would make islands of: the cab roads' flat glass canopies and
# the goods sheds' roofs.
NAV_SKIP = { "railhead_glass" }
RAIL_Z, BED_Z, ROAD_Z = S.RAIL_Z, S.BED_Z, S.ROAD_Z

# Track centres and Gleis numbers: west C 1, west B 2, west A 3, east A 4, east B 5, east C 6.
TRACK_A, TRACK_B, TRACK_C = S.TRACKS["A"], S.TRACKS["B"], S.TRACKS["C"]
GLEIS = { ( -1, "C" ): 1, ( -1, "B" ): 2, ( -1, "A" ): 3, ( 1, "A" ): 4, ( 1, "B" ): 5, ( 1, "C" ): 6 }
# Keep the train definitions in the builder so they can be restored without re-authoring them.
# IDs are west_inner, west_outer, east_inner and east_outer.
HIDDEN_TRAINS = { "west_outer", "east_inner", "east_outer" }
BUFFER_N = 740.0                # the buffer stops' faces: they reach 140 behind, to the trench's end wall at 880
PORTAL_N = getattr( RB, "PORTAL_N", -8000.0 )     # the tunnel portal the corridor ends at (railhead_backdrop's)
SOUTH_END = PORTAL_N - 780.0    # where the drawn track ends: 20 m into the bore, where it's gone dark
CURVE = ( -2400.0, -4600.0, 600.0 )      # track C bends in from 848 to 600 between these n


# ---------------------------------------------------------------------------------------------------------------------
# Using railhead_props, with stand-ins for what isn't there yet

MISSING = {}
UNKNOWN_PAINTS = set()

# Stand-in sizes: ( width, height, length ) of rolling stock, ( width, depth, height, paint, surface ) of furniture.
VEHICLES = { "emu": ( 113.4, 182.3, None ), "loco": ( 118.0, 169.0, 772.0 ), "coach": ( 111.0, 160.0, 1039.0 ),
             "control_car": ( 111.0, 160.0, 1039.0 ), "covered_wagon": ( 112.0, 160.0, 620.0 ),
             "open_wagon": ( 115.0, 100.0, 553.0 ), "container_flat": ( 115.0, 150.0, 777.0 ) }
FURNITURE = { "bench": ( 70, 20, 34, "rw_wood", WOOD ), "bin": ( 16, 16, 36, "rw_steel_grey", METAL ),
              "ticket_machine": ( 30, 24, 72, "rw_steel_grey", METAL ), "vending_machine": ( 40, 32, 74, "rw_steel_dark", METAL ),
              "info_pillar": ( 20, 20, 90, "rw_steel_dark", METAL ), "timetable_case": ( 50, 8, 80, "rw_steel_dark", METAL ),
              "car": ( 70, 180, 58, "rw_train_grey", METAL ),
              "suv": ( 71, 176, 63, "rw_car_grey", METAL ),
              "van": ( 81, 236, 93, "rw_car_white", METAL ), "crate": ( 40, 40, 40, "rw_wood", WOOD ),
              "bollard": ( 8, 8, 36, "rw_steel_dark", METAL ), "luggage_cart": ( 40, 80, 36, "rw_steel", METAL ),
              "pallet_stack": ( 48, 40, 40, "rw_wood", WOOD ) }


def use( name, target, *args, stand_in=None, **kw ):
    """ railhead_props' <name>( model, *args, **kw ) into target, through a model of its own so a failure adds
    nothing. When it isn't there or fails, stand_in( target ) does instead (if given), and it's reported. """
    fn = getattr( P, name, None ) if P is not None else None
    if fn is None:
        MISSING.setdefault( name, "not in railhead_props" )
    else:
        temp = Model()
        try:
            result = fn( temp, *args, **kw )
        except Exception as error:
            MISSING.setdefault( name, f"{type( error ).__name__}: {error}" )
        else:
            # Only track detail and overhead fittings may deliberately omit player collision.
            if name not in { "rail", "track", "crossover", "contact_line", "roof_drop" } and not ( temp.boxes or temp.hulls ):
                raise ValueError( f"{name} generated no collision" )
            target.extend( temp )
            return result
    return stand_in( target ) if stand_in else None


def vehicle_stand_in( kind, e, n_front, facing, rail_z, body, length=None ):
    def build( model ):
        w, h, l = VEHICLES[kind]
        far = n_front - facing * ( length or l )
        lo, hi = sorted( ( n_front, far ) )
        model.box( ( e - w / 2, lo, rail_z + 12 ), ( e + w / 2, hi, rail_z + h ), body )
        model.collision_box( ( e - w / 2, lo, rail_z - 7 ), ( e + w / 2, hi, rail_z + h ), METAL )
        return far
    return build


def furniture_stand_in( kind, e, n, facing="+n", z0=0.0 ):
    def build( model ):
        w, d, h, paint, surface = FURNITURE[kind]
        if facing in ( "+e", "-e" ):
            w, d = d, w
        model.box( ( e - w / 2, n - d / 2, z0 ), ( e + w / 2, n + d / 2, z0 + h ), paint, surface )
    return build


def put( kind, model, e, n, facing="+n", *args, **kw ):
    """ A piece of furniture whose front faces facing ( "+e", "-e", "+n", "-n" ). """
    return use( kind, model, e, n, *args, facing=facing, stand_in=furniture_stand_in( kind, e, n, facing ), **kw )


def atlas_rect( atlas, name ):
    """ ( u0, v0, u1, v1 ) of an atlas entry, or None while railhead_materials hasn't got it. """
    try:
        return tuple( float( x ) for x in RM.rect_uv( atlas, name ) )
    except Exception:
        return None


def atlas_aspect( atlas, name ):
    """ An atlas entry's width over its height: from its pixel rectangle, else railhead_props' table, else 1. """
    try:
        x0, y0, x1, y1 = getattr( RM, atlas[3:].upper() + "_RECTS" )[name]
        return ( x1 - x0 ) / ( y1 - y0 )
    except Exception:
        pass
    try:
        return float( P.aspect( atlas, name ) )
    except Exception:
        return 1.0


def atlas_quad( model, atlas, name, centre, right, up, w, h ):
    """ An atlas entry on a w x h rectangle facing cross( right, up ), reading the right way round from in front. """
    rect = atlas_rect( atlas, name ) or ( 0.0, 0.0, 1.0, 1.0 )
    u0, v0, u1, v1 = rect
    c = np.asarray( centre, float )
    r = np.asarray( right, float ) / np.linalg.norm( right ) * w / 2
    u = np.asarray( up, float ) / np.linalg.norm( up ) * h / 2
    model.polygon( atlas, [ c - r - u, c + r - u, c + r + u, c - r + u ], uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )


NORMALS = { "+e": ( 1.0, 0.0, 0.0 ), "-e": ( -1.0, 0.0, 0.0 ), "+n": ( 0.0, 1.0, 0.0 ), "-n": ( 0.0, -1.0, 0.0 ) }


def board( model, atlas, entries, e, n, bottom, height, along, z_top=None, frame="rw_steel_dark", depth=4.0 ):
    """ A double-sided board of atlas entries side by side, its faces' normals along ±along ("n" or "e"), bottom over
    the floor, height tall; hung on two rods up to z_top if given. Solid board with separate supports. """
    widths = [ height * atlas_aspect( atlas, name ) for name in entries ]
    total = sum( widths ) + 2.0 * ( len( entries ) - 1 )
    across = np.array( ( 1.0, 0.0, 0.0 ) ) if along == "n" else np.array( ( 0.0, 1.0, 0.0 ) )
    normal = np.array( ( 0.0, 1.0, 0.0 ) ) if along == "n" else np.array( ( 1.0, 0.0, 0.0 ) )
    c = np.array( ( e, n, bottom + height / 2 ) )
    half = across * ( total / 2 + 2 ) + normal * depth / 2
    lo, hi = np.minimum( c - half, c + half ), np.maximum( c - half, c + half )
    model.box( lo - ( 0, 0, height / 2 + 2 ), hi + ( 0, 0, height / 2 + 2 ), frame )
    model.collision_box( lo - ( 0, 0, height / 2 + 2 ), hi + ( 0, 0, height / 2 + 2 ), METAL )
    for side in ( 1.0, -1.0 ):
        at = -total / 2
        for name, w in zip( entries, widths ):
            # Seen from this side, right is across turned the way the face looks.
            right = across * side if along == "n" else -across * side
            atlas_quad( model, atlas, name, c + across * ( at + w / 2 ) + normal * side * ( depth / 2 + 0.05 ),
                        right, ( 0, 0, 1 ), w, height )
            at += w + 2.0
    if z_top is not None and z_top > bottom + height + 4:
        for k in ( -1, 1 ):
            p = c + across * k * total * 0.35
            model.box( ( p[0] - 0.6, p[1] - 0.6, bottom + height + 2 ), ( p[0] + 0.6, p[1] + 0.6, z_top ), "rw_steel_dark" )
            model.collision_box( ( p[0] - 0.6, p[1] - 0.6, bottom + height + 2 ), ( p[0] + 0.6, p[1] + 0.6, z_top ), METAL )


def hanging_display( model, e, n, z_top, name, along="n", bottom=110.0 ):
    # A level display must clear the rib across its full width, including the sloping ends of the shed.
    use( "hanging_display", model, e, n, z_top, name, along,
         ceiling=lambda at_e, at_n: S.shed_rib_z( at_e ),
         stand_in=lambda m: board( m, "rw_displays", [ name ], e, n, bottom, 26.0 if name != "departures" else 100.0,
                                   along, z_top ) )


def hanging_sign( model, e, n, z_top, names, along="n", bottom=120.0 ):
    use( "hanging_sign", model, e, n, z_top, list( names ), along,
         stand_in=lambda m: board( m, "rw_signs", list( names ), e, n, bottom, 18.0, along, z_top ) )


def clock( model, e, n, z, along="n" ):
    def stand_in( m ):
        normal = np.array( NORMALS["+" + along] )
        m.cylinder( ( e, n ), 1.2, z + 16, z + 40, "rw_steel_dark", sides=6 )
        for side in ( 1, -1 ):
            q = 15.0
            c = np.array( ( e, n, z ) ) + normal * side * 2.2
            right = np.cross( normal * side, ( 0, 0, 1 ) ) * -1
            pts = [ c - right * q - ( 0, 0, q ), c + right * q - ( 0, 0, q ), c + right * q + ( 0, 0, q ),
                    c - right * q + ( 0, 0, q ) ]
            m.polygon( "rw_clock", pts, normal=normal * side )
        lo = np.array( ( e, n, z ) ) - np.abs( normal ) * 2 - np.abs( np.cross( normal, ( 0, 0, 1 ) ) ) * 16 - ( 0, 0, 16 )
        hi = np.array( ( e, n, z ) ) + np.abs( normal ) * 2 + np.abs( np.cross( normal, ( 0, 0, 1 ) ) ) * 16 + ( 0, 0, 16 )
        m.box( lo, hi, { "default": "rw_steel_dark", f"+{'enz'.index( along ) and 'n' or 'e'}": None,
                         f"-{'enz'.index( along ) and 'n' or 'e'}": None } )
    use( "clock", model, e, n, z, along, stand_in=stand_in )


# ---------------------------------------------------------------------------------------------------------------------
# Paints

GLASS_PAINTS = ( "rw_glass", "rw_glass_roof", "rw_emu_glass", "rw_signal_box_glass" )

def configure( model ):
    """ Points every rw_ paint at its material with its tile size (railhead_materials' paints(), else the backdrop's
    table, else 64), and marks the grain, anchored and decal paints. building_textures' paints need nothing; any other
    paint is reported and drawn as rw_concrete. """
    known = {}
    if RM is not None and hasattr( RM, "paints" ):
        try:
            known = RM.paints()
        except Exception as error:
            print( f"railhead_materials.paints() failed: {error}" )
    tiles = getattr( RB, "RW_TILES", {} ) if RB is not None else {}
    for paint in list( model.polygons ):
        if paint.startswith( "rw_" ):
            try:
                path = RM.material_path( paint )
            except Exception:
                path = f"materials/railhead/{paint}.vmat"
            model.material_overrides[paint] = path
            tile = known[paint][1] if paint in known else tiles.get( paint )
            model.tile_overrides[paint] = float( tile or 64.0 )
            if known and paint not in known:
                UNKNOWN_PAINTS.add( paint )
        elif paint not in model.material_overrides:
            try:
                BT.tile_units( paint )
            except Exception:
                UNKNOWN_PAINTS.add( paint )
                model.material_overrides[paint] = "materials/railhead/rw_concrete.vmat"
                model.tile_overrides[paint] = 64.0
    grain = set( getattr( RM, "GRAIN", () ) ) | set( getattr( P, "GRAIN", () ) )
    anchored = set( getattr( RM, "ANCHORED", () ) ) | set( getattr( RB, "FACADES", () ) )
    decals = set( getattr( RM, "DECALS", () ) ) | { "rw_clock" }
    model.grain_paints |= { p for p in model.polygons if p in grain }
    model.anchored_paints = { p for p in model.polygons if p in anchored }
    model.decal_paints = { p for p in model.polygons if p in decals }
    import railhead_masonry
    railhead_masonry.align_uvs( model )
    return model


def split_paints( model, paints ):
    """ Takes these paints' polygons out of model into a model of their own (the glass, drawn with no shadows). """
    out = Model()
    for paint in [ p for p in model.polygons if p in paints ]:
        items = model.polygons.pop( paint )
        for i in range( len( items ) ):
            if ( paint, i ) in model.polygon_uvs:
                out.polygon_uvs[( paint, i )] = model.polygon_uvs.pop( ( paint, i ) )
            if ( paint, i ) in model.polygon_normals:
                out.polygon_normals[( paint, i )] = model.polygon_normals.pop( ( paint, i ) )
        out.polygons[paint] = items
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The track: drawn only (the trench floors and the throat's ballast are the station's collision)

def c_track_e( n ):
    """ Track C's centre at n: straight at 848 to the play's south edge, then easing in to 600 in the corridor. """
    n0, n1, e1 = CURVE
    if n >= n0:
        return TRACK_C
    if n <= n1:
        return e1
    t = ( n0 - n ) / ( n0 - n1 )
    return TRACK_C + ( e1 - TRACK_C ) * ( 1 - math.cos( math.pi * t ) ) / 2


def curved_track( model, s, n0, n1 ):
    """ Track C (side s) from n0 south to n1 along its bend: rails on a path, sleepers square to it. """
    def frame( n ):
        """ The track's centre at n and its unit vectors along it (north) and across it (to the right, looking
        north). """
        dedn = s * ( c_track_e( n + 1 ) - c_track_e( n - 1 ) ) / 2
        along = np.array( ( dedn, 1.0 ) ) / math.hypot( dedn, 1.0 )
        return np.array( ( s * c_track_e( n ), n ) ), along, np.array( ( along[1], -along[0] ) )

    ns = np.arange( n0, n1 - 1, -48.0 )
    for side in ( -1, 1 ):
        path = []
        for n in ns:
            centre, _, across = frame( n )
            path.append( tuple( centre + across * side * 29.6 ) )
        def stand_in( m, path=path ):
            for a, b in zip( path, path[1:] ):
                m.beam( ( a[0], a[1], RAIL_Z - 3.4 ), ( b[0], b[1], RAIL_Z - 3.4 ), ( 3.0, 6.8 ), "rw_rail" )
        use( "rail", model, path, RAIL_Z, stand_in=stand_in )
    for n in np.arange( n0 - 12, n1, -23.6 ):
        centre, along, across = frame( n )
        model.oriented_box( ( centre[0], centre[1], RAIL_Z - 6.8 - 4.35 ), ( ( *across, 0 ), ( *along, 0 ), ( 0, 0, 1 ) ),
                            ( 102.4, 11.8, 8.7 ), "rw_sleeper" )


def corridor_half( n ):
    """ The rail corridor's half width south of the play area (railhead_backdrop's CORRIDOR), as its ballast bed. """
    points = getattr( RB, "CORRIDOR", ( ( -2400.0, 1200.0 ), ( -3500.0, 1000.0 ), ( -5000.0, 700.0 ) ) )
    ns = [ p[0] for p in points ][::-1]
    hs = [ p[1] for p in points ][::-1]
    return float( np.interp( n, ns, hs ) )


def track_model():
    """ All six tracks from their buffer stops to the corridor, the two crossovers in the throat, and the corridor's
    ballast past the play's edge. """
    m = Model()
    for s in ( 1, -1 ):
        a, b = s * TRACK_A, s * TRACK_B
        # The crossover leaves A heading south and joins B; the west one starts further south, so the two sides differ.
        start = -1900.0 if s > 0 else -2150.0
        probe = Model()
        end = use( "crossover", probe, a, b, start, -1, RAIL_Z, stand_in=lambda m_: None )
        if end is None:
            end = start
        else:
            m.extend( probe )
        for e in ( a, b ):
            n_top = 880.0
            use( "track", m, e, n_top, start, RAIL_Z, stand_in=lambda m_, e=e: plain_rails( m_, e, n_top, start ) )
            use( "track", m, e, end, SOUTH_END, RAIL_Z, stand_in=lambda m_, e=e: plain_rails( m_, e, end, SOUTH_END ) )
        c = s * TRACK_C
        use( "track", m, c, 880.0, CURVE[0], RAIL_Z, stand_in=lambda m_: plain_rails( m_, c, 880.0, CURVE[0] ) )
        curved_track( m, s, CURVE[0], CURVE[1] )
        use( "track", m, s * CURVE[2], CURVE[1], SOUTH_END, RAIL_Z,
             stand_in=lambda m_: plain_rails( m_, s * CURVE[2], CURVE[1], SOUTH_END ) )
    depot_lead( m )
    # The corridor's ballast, past the play's south edge, to the portal (the bore has its own floor).
    ns = np.linspace( PLAY[2], PORTAL_N, 24 )
    for n0, n1 in zip( ns, ns[1:] ):
        h0, h1 = corridor_half( n0 ), corridor_half( n1 )
        m.polygon( "rw_ballast", [ ( -h0, n0, BED_Z ), ( -h1, n1, BED_Z ), ( h1, n1, BED_Z ), ( h0, n0, BED_Z ) ], normal=( 0, 0, 1 ) )
    return m


# The railcar depot's road (railhead_backdrop's depot()) ends at the corridor's edge heading north-west; its lead
# leaves track C (east) here and joins it there, tangent to both.
DEPOT_LEAD = ( -2600.0, ( 1050.0, -3560.0 ), ( 130.0, -340.0 ) )     # leaves C at n; the road's end and its heading


def depot_lead( model ):
    """ The lead from east track C into the depot: a cubic curve tangent to C where it leaves and to the depot road
    where it joins, turning ~24 degrees (a ~60 m radius, as depot sidings have). Its rails start where they've cleared
    C's (they'd be the turnout's shared stock rails before that), and its sleepers only where C's don't reach. """
    if RB is None or not hasattr( RB, "depot" ):
        return
    n_j, end, heading = DEPOT_LEAD
    p0 = np.array( ( c_track_e( n_j ), n_j ) )
    t0 = np.array( ( c_track_e( n_j - 1 ) - c_track_e( n_j + 1 ), -2.0 ) )
    t0 /= np.linalg.norm( t0 )
    p3 = np.array( end )
    t3 = np.array( heading ) / np.linalg.norm( heading )
    reach = 0.35 * np.linalg.norm( p3 - p0 )
    p1, p2 = p0 + t0 * reach, p3 - t3 * reach
    ts = np.linspace( 0.0, 1.0, 40 )
    curve = [ ( 1 - t ) ** 3 * p0 + 3 * ( 1 - t ) ** 2 * t * p1 + 3 * ( 1 - t ) * t ** 2 * p2 + t ** 3 * p3 for t in ts ]
    off = [ q[0] - c_track_e( q[1] ) for q in curve ]
    start = next( i for i, d in enumerate( off ) if d >= 4.0 )
    for side in ( -1, 1 ):
        rail_path = []
        for i, q in enumerate( curve ):
            a, b = curve[max( i - 1, 0 )], curve[min( i + 1, len( curve ) - 1 )]
            along = ( b - a ) / np.linalg.norm( b - a )
            rail_path.append( tuple( q + np.array( ( along[1], -along[0] ) ) * side * 29.6 ) )
        rail_path = rail_path[max( start - 1, 0 ):]
        def stand_in( m, rail_path=rail_path ):
            for a, b in zip( rail_path, rail_path[1:] ):
                m.beam( ( a[0], a[1], RAIL_Z - 3.4 ), ( b[0], b[1], RAIL_Z - 3.4 ), ( 3.0, 6.8 ), "rw_rail" )
        use( "rail", model, rail_path, RAIL_Z, stand_in=stand_in )
    # Sleepers every 23.6 along the curve, cut back where C's own sleepers (+-51.2 round its centre) are under them.
    length = sum( np.linalg.norm( b - a ) for a, b in zip( curve, curve[1:] ) )
    for k in range( int( length / 23.6 ) ):
        s_at, i = ( k + 0.5 ) * 23.6, 0
        while i < len( curve ) - 2 and s_at > np.linalg.norm( curve[i + 1] - curve[i] ):
            s_at -= np.linalg.norm( curve[i + 1] - curve[i] )
            i += 1
        a, b = curve[i], curve[i + 1]
        along = ( b - a ) / np.linalg.norm( b - a )
        centre = a + along * s_at
        across = np.array( ( along[1], -along[0] ) )          # to the right, looking along: east to west, heading south
        clear = c_track_e( centre[1] ) + 51.2 + 1.5 + 5.9 * abs( along[0] )   # the cut end's far corner stays clear too
        lo, hi = -51.2, 51.2
        if abs( across[0] ) > 1e-6:                            # cut back the end that reaches over C, east of `clear`
            t_clear = ( clear - centre[0] ) / across[0]
            if across[0] < 0:
                hi = min( hi, t_clear )
            else:
                lo = max( lo, t_clear )
        if hi - lo < 8.0:
            continue
        mid = centre + across * ( lo + hi ) / 2
        model.oriented_box( ( mid[0], mid[1], RAIL_Z - 6.8 - 4.35 ), ( ( *across, 0 ), ( *along, 0 ), ( 0, 0, 1 ) ),
                            ( hi - lo, 11.8, 8.7 ), "rw_sleeper" )


def plain_rails( model, e, n0, n1 ):
    lo, hi = sorted( ( n0, n1 ) )
    for side in ( -1, 1 ):
        model.box( ( e + side * 29.6 - 1.4, lo, RAIL_Z - 6.8 ), ( e + side * 29.6 + 1.4, hi, RAIL_Z ), "rw_rail" )
    n = hi - 12
    while n > lo:
        model.box( ( e - 51.2, n - 5.9, RAIL_Z - 15.5 ), ( e + 51.2, n + 5.9, RAIL_Z - 6.8 ), "rw_sleeper" )
        n -= 23.6


# ---------------------------------------------------------------------------------------------------------------------
# The overhead line south of the shed (the shed's own tracks have the station's overhead conductor rails at
# CONTACT_Z), signals and buffer stops

WIRE_Z = S.CONTACT_Z                       # 167: the contact wire over the shed's rails, 197 over the rail
WIRE_HEIGHT = WIRE_Z - RAIL_Z
# The portal by the overbridge stands 60 clear of its deck (n -3300..-2900, its soffit at 230 under the girder's ~258).
SUPPORTS = ( -1340.0, -1830.0, -2390.0, -2840.0, -3450.0, -4000.0, -4550.0, -5100.0, -5650.0, -6200.0, -6750.0, -7300.0,
             -7850.0 )


def catenary( m, s ):
    a, b, c = s * TRACK_A, s * TRACK_B, s * TRACK_C
    for e in ( a, b ):
        use( "contact_line", m, e, SUPPORTS[0], PORTAL_N - 300, RAIL_Z, list( SUPPORTS ), wire_height=WIRE_HEIGHT,
             first=1 if e == a else -1 )
    use( "contact_line", m, c, SUPPORTS[0], CURVE[0], RAIL_Z, list( SUPPORTS[:3] ), wire_height=WIRE_HEIGHT )
    # Round the bend, the contact wire follows the track's centre, held at each corridor portal.
    pts = [ ( s * c_track_e( n ), n, WIRE_Z ) for n in np.arange( CURVE[0], PORTAL_N - 301, -60.0 ) ]
    for p, q in zip( pts, pts[1:] ):
        m.beam( p, q, ( 0.5, 0.5 ), "copper_brown" )
        m.beam( ( p[0], p[1], WIRE_Z + 50 ), ( q[0], q[1], WIRE_Z + 50 ), ( 0.4, 0.4 ), "copper_brown" )
    # Where the wire meets the shed's gable it hangs from the roof's last rib.
    for e in ( a, b, c ):
        use( "roof_drop", m, e, SUPPORTS[0], S.shed_z( abs( e ) ) - 46, RAIL_Z, wire_height=WIRE_HEIGHT )
    # Portals over the throat, their masts clear of the platforms' ends and the signal box.
    for n in SUPPORTS[1:3]:
        use( "portal", m, s * 130, s * 990, n, RAIL_Z, [ a, b, c ], wire_height=WIRE_HEIGHT )
    for n in SUPPORTS[3:]:
        # Past n -5000 the cutting's walls close in to 700: the outer mast stands just inside them.
        reach = min( c_track_e( n ) + 142, corridor_half( n ) - 16 )
        use( "portal", m, s * 130, s * reach, n, RAIL_Z, [ a, b, s * c_track_e( n ) ], wire_height=WIRE_HEIGHT )


def signals( m, s ):
    """ Exit signals at the platforms' ends, screens north to the trains standing in the shed, and entry signals far
    down the corridor. Gleis 4's (east A) shows green: the 14:08 is about to leave. Each mast stands outside its
    track, away from the next one. """
    exits = ( ( TRACK_A, +1, "green" if s > 0 else "red" ), ( TRACK_B, -1, "red" ), ( TRACK_C, -1, "red" ) )
    for e, side, aspect in exits:
        use( "ks_signal", m, s * e, -1800.0, RAIL_Z, +1, side * s, aspect )
    for e, side in ( ( TRACK_A, +1 ), ( TRACK_B, -1 ), ( CURVE[2], -1 ) ):
        use( "ks_signal", m, s * e, -4800.0, RAIL_Z, -1, -side * s, "yellow" if e == TRACK_A else "red" )


# ---------------------------------------------------------------------------------------------------------------------
# Dressing one side (s = 1 east, -1 west). Built per side rather than mirrored, so signs and trains read right.

def trains( m, s ):
    train_side = "east" if s > 0 else "west"
    body = "rw_train_blue" if s > 0 else "rw_train_red"
    a, c = s * TRACK_A, s * TRACK_C
    # The double-deck units: the 14:05 to München at Gleis 3, the 14:08 to Nürnberg at Gleis 4 (the departures).
    to = "RE Nürnberg" if s > 0 else "RE München"
    if f"{train_side}_inner" not in HIDDEN_TRAINS:
        use( "emu", m, a, 720.0, +1, RAIL_Z, cars=2, body=body, platform_side=-s, doors_open=False,
             wire_z=WIRE_Z, destinations=( to, to ),
             stand_in=vehicle_stand_in( "emu", a, 720.0, 1, RAIL_Z, body, length=1540.0 ) )
    # The outer tracks use the same rounded double-deck passenger cab as the reference train.
    # All passenger doors are closed, with solid collision across the former vestibules.
    if f"{train_side}_outer" not in HIDDEN_TRAINS:
        use( "emu", m, c, 720.0, +1, RAIL_Z, cars=2, body=body, platform_side=s, doors_open=False,
             wire_z=WIRE_Z, destinations=( to, to ),
             stand_in=vehicle_stand_in( "emu", c, 720.0, 1, RAIL_Z, body, length=1540.0 ) )
    for e in ( TRACK_A, TRACK_B, TRACK_C ):
        use( "buffer_stop", m, s * e, BUFFER_N, -1, RAIL_Z,
             stand_in=lambda m_, e=e: m_.box( ( s * e - 50, BUFFER_N, RAIL_Z - 7 ), ( s * e + 50, BUFFER_N + 140, RAIL_Z + 54 ),
                                               "rw_red_paint", METAL ) )


def yard( m, s ):
    """ The goods yard: a siding embedded in the paving along the loading bank with a wagon on it, containers, a
    pallets and crates. Bomb site B is the east yard's south-east corner, among the containers. """
    e_siding = s * S.SIDING_E
    use( "track", m, e_siding, -2400.0, -1480.0, 0.0, None, True )
    use( "buffer_stop", m, e_siding, -1620.0, -1, 0.0 )
    if s > 0:
        use( "covered_wagon", m, e_siding, -1640.0, +1, 0.0, stand_in=vehicle_stand_in( "covered_wagon", e_siding, -1640.0, 1, 0.0, "rw_wagon_rust" ) )
    else:
        use( "open_wagon", m, e_siding, -1640.0, +1, 0.0, stand_in=vehicle_stand_in( "open_wagon", e_siding, -1640.0, 1, 0.0, "rw_wagon_rust" ) )
    # Containers: a 40 ft pair stacked against the warehouse, a 20 ft across the yard.
    paints = ( "rw_container_blue", "rw_container_grey" ) if s > 0 else ( "rw_container_red", "rw_container_green" )
    for k, paint in enumerate( paints ):
        container( m, s * 2138.0, -2140.0, 102.0 * k, "40", "n", paint )
    container( m, s * 2019.0, -1712.0, 0.0, "20", "e", "rw_container_orange" )
    for e, n, layers in ( ( 1890.0, -2300.0, 3 ), ( 1960.0, -1560.0, 2 ) ):
        use( "pallet_stack", m, s * e, n, 0.0, layers, stand_in=furniture_stand_in( "pallet_stack", s * e, n ) )
    for e, n in ( ( 2160.0, -1460.0 ), ( 2160.0, -1418.0 ) ):
        use( "crate", m, s * e, n, 0.0, stand_in=furniture_stand_in( "crate", s * e, n ) )
    # Bollards either side of the road gate.
    for e in ( S.GATE_ROAD[0] - 14, S.GATE_ROAD[1] + 14 ):
        use( "bollard", m, s * e, S.YARD_N1 - 20, stand_in=furniture_stand_in( "bollard", s * e, S.YARD_N1 - 20 ) )


def container( m, e, n, z0, size, axis, paint ):
    length = { "20": 238.5, "40": 480.0 }[size]
    def stand_in( model ):
        w, l = ( 96.0, length ) if axis == "n" else ( length, 96.0 )
        model.box( ( e - w / 2, n - l / 2, z0 ), ( e + w / 2, n + l / 2, z0 + 102 ), paint, METAL )
    use( "container", m, e, n, z0, size, axis, paint, stand_in=stand_in )


def throat( m, s ):
    # Relay huts beside the throat, and a stack of old wooden sleepers waiting to go.
    e0, e1 = sorted( ( s * 1090.0, s * 1170.0 ) )
    m.box( ( e0, -2100.0, BED_Z ), ( e1, -1980.0, BED_Z + 100 ), { "default": "rw_concrete", "+z": "rw_concrete_dark" }, STONE )
    m.box( ( e0 - 4, -2104.0, BED_Z + 100 ), ( e1 + 4, -1976.0, BED_Z + 106 ), "rw_concrete_dark" )
    door_e = e0 if s > 0 else e1
    m.box( ( door_e - 0.5, -2060.0, BED_Z + 4 ), ( door_e + 0.5, -2024.0, BED_Z + 82 ), "rw_steel_grey" )
    e0, e1 = sorted( ( s * 580.0, s * 682.0 ) )
    for k in range( 4 ):
        m.box( ( e0, -2330.0 + ( k % 2 ) * 4, BED_Z + 6.3 * k ), ( e1, -2270.0 + ( k % 2 ) * 4, BED_Z + 6.3 * ( k + 1 ) ),
               "rw_sleeper_wood" )
    m.collision_box( ( e0, -2330.0, BED_Z ), ( e1, -2266.0, BED_Z + 25.2 ), WOOD )


# The kiosks: ( name, e0, e1, n0, n1, facing ), each lit by a light of its own in its serving window.
KIOSKS = [ ( "West", -800.0, -700.0, 1000.0, 1080.0, "-n" ), ( "East", 700.0, 800.0, 1000.0, 1080.0, "-n" ),
           ( "Centre", -50.0, 50.0, 640.0, 760.0, "-n" ) ]


def kiosk( m, spec ):
    _, e0, e1, n0, n1, facing = spec
    use( "kiosk", m, e0, e1, n0, n1, facing,
         stand_in=lambda m_: m_.box( ( min( e0, e1 ), min( n0, n1 ), 0 ), ( max( e0, e1 ), max( n0, n1 ), 110 ),
                                     "rw_steel_dark", METAL ) )


def concourse( m, s ):
    # The departure board over the concourse, hung from the rib at n 1060.
    hanging_display( m, s * 300.0, 1060.0, S.shed_z( 300.0 ) - 46, "departures", "n", bottom=230.0 )
    kiosk( m, KIOSKS[1 if s > 0 else 0] )
    put( "ticket_machine", m, s * 1145.0, 1060.0, "-e" if s > 0 else "+e" )
    put( "ticket_machine", m, s * 1145.0, 1100.0, "-e" if s > 0 else "+e" )
    for e in ( 560.0, 1100.0 ):
        put( "bench", m, s * e, 1280.0, "-n" )
    put( "bin", m, s * 622.0, 1284.0, "-n" )        # clear of the bench's end, its slots towards the concourse
    # Luggage trolleys are shared model instances added by write_scene().
    # Platform signs over the platforms' heads, hung from the rib at n 820.
    island, outer = ( "gleis_5_6", "gleis_6" ) if s > 0 else ( "gleis_1_2", "gleis_3" if False else "gleis_1" )
    hanging_sign( m, s * 632.0, 820.0, S.shed_z( 632.0 ) - 46, [ island ], "n", bottom=150.0 )
    hanging_sign( m, s * 1037.0, 820.0, S.shed_z( 1037.0 ) - 46, [ outer ], "n", bottom=150.0 )
    # Ausgang over the portals to the cab road.
    hanging_sign( m, s * 1080.0, 1060.0, S.shed_z( 1080.0 ) - 46, [ "ausgang_ost" if s > 0 else "ausgang_west" ], "e",
                  bottom=180.0 )


def platforms( m, s ):
    island = s * 632.0
    outer = s * 1057.0
    a_gleis, b_gleis, c_gleis = ( GLEIS[( s, k )] for k in "ABC" )
    for n in ( 700.0, 100.0, -1000.0 ):
        put( "bench", m, island - 12, n, "-e" )
        put( "bench", m, island + 12, n, "+e" )
        put( "bin", m, island, n + 60 )
    put( "timetable_case", m, island, 460.0, "+n", two_sided=True )
    # Platform displays, hung from the ribs at n 340 and -1100: each track's on its own edge.
    for n in ( 340.0, -1100.0 ):
        rib_z = lambda e: S.shed_z( abs( e ) ) - 46
        hanging_display( m, s * 557.0, n, rib_z( 557.0 ), f"gleis_{b_gleis}_display", "n" )
        hanging_display( m, s * 707.0, n, rib_z( 707.0 ), f"gleis_{c_gleis}_display", "n" )
        hanging_display( m, s * 85.0, n, rib_z( 85.0 ), f"gleis_{a_gleis}_display", "n" )
        hanging_display( m, outer, n, rib_z( 1057.0 ), f"gleis_{c_gleis}_display", "n" )
    # Sector letters along the platforms, A at the head.
    for letter, n in zip( "abcde", ( 820.0, 340.0, -140.0, -620.0, -1100.0 ) ):
        for e in ( island, s * 1037.0 ):
            hanging_sign( m, e, n + 60, S.shed_z( abs( e ) ) - 46, [ f"sector_{letter}" ], "n", bottom=170.0 )
    for e in ( island, s * 1060.0 ):
        hanging_sign( m, e, -1550.0, S.CANOPY_Z - 12, [ "sector_f" ], "n", bottom=150.0 )
    put( "vending_machine", m, s * 1138.0, 300.0, "-e" if s > 0 else "+e" )
    put( "ticket_machine", m, s * 1145.0, 700.0, "-e" if s > 0 else "+e" )
    use( "shelter", m, *sorted( ( s * 540.0, s * 600.0 ) ), -1590.0, -1450.0,
         stand_in=lambda m_: m_.box( ( min( s * 540, s * 600 ), -1590.0, 0 ), ( max( s * 540, s * 600 ), -1450.0, 96 ), "rw_steel_dark", GLASS ) )
    # The station's name under the canopies, facing the tracks.
    for e in ( island, s * 1080.0 ):
        board( m, "rw_signs", [ "station_name" ], e, -1520.0, 150.0, 20.0, "e", z_top=S.CANOPY_Z - 12 )
    # "Keep off the tracks" plates at the platforms' ends, facing whoever comes up the ramps.
    for e in ( island, s * 1037.0, s * 90.0 ):
        warn_plate( m, e, -1690.0 )
    # The platform trolley uses the same reusable asset as the concourse carts.


def warn_plate( m, e, n ):
    m.cylinder( ( e, n ), 1.2, 0, 66, "rw_steel_grey", sides=6 )
    atlas_quad( m, "rw_signs", "warn_gleise", ( e, n - 1.4, 56 ), ( 1, 0, 0 ), ( 0, 0, 1 ), 30.0, 10.0 )
    m.box( ( e - 15.5, n - 1.3, 50.5 ), ( e + 15.5, n - 0.3, 61.5 ), "rw_white_paint" )
    m.collision_box( ( e - 1.2, n - 1.2, 0 ), ( e + 1.2, n + 1.2, 66 ), METAL )
    m.collision_box( ( e - 15.5, n - 1.4, 50.5 ), ( e + 15.5, n - 0.3, 61.5 ), METAL )


def head_building( m, s ):
    # The booking hall's benches, back to back, and the wings: the travel centre's counter west, lockers east.
    for n in ( 1420.0, 1600.0 ):
        put( "bench", m, s * 430.0, n - 12, "-n" )      # 12 each side, so the backrests don't meet
        put( "bench", m, s * 430.0, n + 12, "+n" )
    e0, e1 = sorted( ( s * 1120.0, s * 1160.0 ) )
    if s < 0:
        m.box( ( e0, 1570.0, 0 ), ( e1, 1750.0, 40 ), { "default": "rw_wood", "+z": "rw_terrazzo_border" }, WOOD )
        m.box( ( e0, 1570.0, 40 ), ( e1, 1750.0, 42 ), "rw_steel_dark" )
        hanging_sign( m, -1000.0, 1660.0, S.WING_CEILING, [ "fahrkarten" ], "e", bottom=110.0 )
    else:
        for k in range( 4 ):
            n0 = 1570.0 + 45 * k
            m.box( ( e0, n0, 0 ), ( e1, n0 + 44, 86 ), { "default": "rw_steel_grey", "+e": None }, METAL )
        hanging_sign( m, 1000.0, 1660.0, S.WING_CEILING, [ "schliessfaecher" ], "e", bottom=110.0 )
    # Well inside the wing's door, so its rod runs up out of sight behind the arch's head.
    hanging_sign( m, s * 900.0, 1420.0, S.WING_CEILING, [ "info" ], "n", bottom=120.0 )


ROAD_VEHICLES_ENABLED = False  # Keep the placements and models for future restoration.


def cab_road_vehicles( m, s ):
    """ Taxis waiting at the head building's end of the cab road, nose to the station, cars parked further down, and
    street lamps along the far pavement. """
    for n in ( 600.0, 820.0, 1040.0 ):
        use( "car", m, s * 1555.0, n, "+n", "rw_train_white", ROAD_Z, "estate",
             stand_in=furniture_stand_in( "car", s * 1555.0, n, z0=ROAD_Z ) )
    use( "suv", m, s * 1555.0, -900.0, "+n", "rw_car_grey", ROAD_Z,
         stand_in=furniture_stand_in( "suv", s * 1555.0, -900.0, z0=ROAD_Z ) )
    use( "car", m, s * 1555.0, 1300.0, "+n", "rw_car_blue" if s > 0 else "rw_car_red", ROAD_Z, "estate",
         stand_in=furniture_stand_in( "car", s * 1555.0, 1300.0, z0=ROAD_Z ) )
    use( "van", m, s * 1940.0, -900.0, "-n", "rw_car_white", ROAD_Z,
         stand_in=furniture_stand_in( "van", s * 1940.0, -900.0, z0=ROAD_Z ) )
def cab_road( m, s ):
    if ROAD_VEHICLES_ENABLED:
        cab_road_vehicles( m, s )
    for n in ( -1000.0, -400.0, 200.0, 800.0, 1400.0 ):
        use( "lamp_post", m, s * 2100.0, n, 236.0,
             stand_in=lambda m_, n=n: m_.cylinder( ( s * 2100.0, n ), 2.5, 0, 236, "rw_steel_dark", sides=8, surface=METAL ) )


def dress_side( s ):
    m = Model()
    trains( m, s )
    catenary( m, s )
    signals( m, s )
    yard( m, s )
    throat( m, s )
    concourse( m, s )
    platforms( m, s )
    head_building( m, s )
    cab_road( m, s )
    return m


def dress_centre():
    m = Model()
    use( "info_pillar", m, 0.0, 940.0, stand_in=furniture_stand_in( "info_pillar", 0.0, 940.0 ) )
    hanging_sign( m, 0.0, 900.0, S.GUTTER_Z[0], [ "gleis_3_4" ], "n", bottom=150.0 )
    clock( m, 0.0, 1110.0, 240.0, "n" )
    kiosk( m, KIOSKS[2] )
    for n in ( 460.0, -500.0 ):
        put( "bench", m, -12.0, n, "-e" )
        put( "bench", m, 12.0, n, "+e" )
    for letter, n in zip( "abcde", ( 940.0, 460.0, -20.0, -500.0, -980.0 ) ):
        hanging_sign( m, 0.0, n, S.GUTTER_Z[0], [ f"sector_{letter}" ], "n", bottom=170.0 )
    board( m, "rw_signs", [ "station_name" ], 0.0, -1520.0, 150.0, 20.0, "e", z_top=S.CANOPY_Z - 12 )
    put( "info_pillar", m, 0.0, 1500.0 )
    # The station's name in bronze letters on the band over the doors, HOHENWALD HAUPTBAHNHOF on one line (the
    # quads' own margins make the word space), and the year on the gable.
    h = 44.0
    words = [ ( name, h * atlas_aspect( "rw_lettering", name ) ) for name in ( "hohenwald", "hauptbahnhof" ) ]
    gap = 6.0
    e = -( sum( w for _, w in words ) + gap ) / 2
    for name, w in words:
        atlas_quad( m, "rw_lettering", name, ( e + w / 2, S.HEAD_N0 - 3.2, 398.0 ), ( 1, 0, 0 ), ( 0, 0, 1 ), w, h )
        e += w + gap
    year_h = 22.0
    atlas_quad( m, "rw_lettering", "year", ( 0.0, S.HEAD_N0 - 0.4, 442.0 ), ( 1, 0, 0 ), ( 0, 0, 1 ),
                year_h * atlas_aspect( "rw_lettering", "year" ), year_h )
    # The signal box's name board.
    atlas_quad( m, "rw_posters", "stellwerk_hf", ( -50.0, S.BOX[3] + 0.6, S.BOX_FLOOR + 22 ), ( -1, 0, 0 ), ( 0, 0, 1 ), 48.0, 16.0 )
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Lights: ( name, position, colour, radius, shadows )

WARM = "1.6,1.3,0.95,1"
COOL = "1.1,1.2,1.35,1"


def lights():
    out = []
    for k, e in enumerate( ( -1000, -600, -200, 200, 600, 1000 ) ):
        out.append( ( f"Concourse {k + 1}", ( e, 1090, 300 ), WARM, 500, False ) )
    for k, ( e, n ) in enumerate( ( e, n ) for e in ( -400, 0, 400 ) for n in ( 1440, 1620 ) ):
        out.append( ( f"Booking Hall {k + 1}", ( e, n, 380 ), WARM, 520, k == 2 ) )
    for e in ( -300, 300 ):
        out.append( ( f"Gallery {'West' if e < 0 else 'East'}", ( e, 1720, 330 ), WARM, 300, False ) )
    for s, side in ( ( -1, "West" ), ( 1, "East" ) ):
        for k, ( e, n ) in enumerate( ( e, n ) for e in ( 780, 1020 ) for n in ( 1420, 1700 ) ):
            out.append( ( f"{side} Wing {k + 1}", ( s * e, n, 190 ), WARM, 320, False ) )
        for k, n in enumerate( ( -2050, -1900, -1750 ) ):
            out.append( ( f"{side} Goods Shed {k + 1}", ( s * 1660, n, 200 ), WARM, 300, False ) )
        for k, n in enumerate( ( -1450, -1600 ) ):
            for e, name in ( ( 75, "Centre" ), ( 632, "Island" ), ( 1064, "Outer" ) ):
                if e == 75 and s < 0:
                    continue
                out.append( ( f"{side} {name} Canopy {k + 1}", ( 0 if e == 75 else s * e, n, 190 ), WARM, 300, False ) )
    for k, ( e, n ) in enumerate( ( e, n ) for e in ( -1037, -632, 0, 632, 1037 ) for n in ( 820, 340, -140, -620, -1100 ) ):
        out.append( ( f"Platform {k + 1}", ( e, n, 260 ), WARM, 360, False ) )
    import railhead_signal_box as SIGNAL_BOX
    out.extend( SIGNAL_BOX.lights() )
    for e in ( -TRACK_C, -TRACK_B, -TRACK_A, TRACK_A, TRACK_B, TRACK_C ):
        out.append( ( f"Buffer {e:g}", ( e, BUFFER_N + 6.5, RAIL_Z + 63.5 ), "1.1,0.009,0.003,1", 32, False ) )
    for s in ( -1, 1 ):
        out.append( ( f"Buffer Siding {s}", ( s * S.SIDING_E, -1613.5, 63.5 ), "1.1,0.009,0.003,1", 32, False ) )
    if P is not None and hasattr( P, "kiosk_lights" ):
        for name, *spec in KIOSKS:
            for k, ( position, radius ) in enumerate( P.kiosk_lights( *spec ) ):
                out.append( ( f"Kiosk {name}{' Counter' if k else ''}", position, WARM, radius, False ) )
    if P is not None:
        import railhead_ticket_machine as TM
        for sign, side in ((-1, "West"), (1, "East")):
            for n in (700, 1060, 1100):
                frame = P.frame_for(sign * 1145, n, 0, "-e" if sign == 1 else "+e")
                for k, (position, radius) in enumerate(TM.lights(frame)):
                    out.append((f"Ticket {side} {n} lamp {k + 1}", position, "0.8,0.65,0.475,1", radius, False))
        import railhead_train as EMU
        for sign, side in ((-1, "West"), (1, "East")):
            for track, e, platform_side in (("inner", TRACK_A, -sign), ("outer", TRACK_C, sign)):
                if f"{side.lower()}_{track}" in HIDDEN_TRAINS:
                    continue
                for name, position, color, radius in EMU.lights(sign * e, 720, 1, RAIL_Z, platform_side):
                    out.append((f"Train {side} {track} {name}", position, color, radius, False))
    return out


# Reflection probes: ( name, centre, the box they cover e0, e1, n0, n1, z0, z1 ).
PROBES = [
    ( "Concourse", ( 0, 1090, 160 ), ( -1160, 1160, 880, 1300, 0, 700 ) ),
    ( "Shed West", ( -600, -230, 150 ), ( -1160, 0, -1340, 880, -37, 700 ) ),
    ( "Shed East", ( 600, -230, 150 ), ( 0, 1160, -1340, 880, -37, 700 ) ),
    ( "Track Ends West", ( -600, 610, 80 ), ( -1160, 0, 300, 880, -37, 240 ) ),
    ( "Track Ends East", ( 600, 610, 80 ), ( 0, 1160, 300, 880, -37, 240 ) ),
    ( "Booking Hall", ( 0, 1520, 160 ), ( -600, 600, 1340, 1780, 0, 680 ) ),
    ( "West Wing", ( -900, 1560, 100 ), ( -1160, -660, 1340, 1780, 0, 208 ) ),
    ( "East Wing", ( 900, 1560, 100 ), ( 660, 1160, 1340, 1780, 0, 208 ) ),
    ( "West Goods Shed", ( -1660, -1900, 120 ), ( -1800, -1520, -2200, -1600, 44, 300 ) ),
    ( "East Goods Shed", ( 1660, -1900, 120 ), ( 1520, 1800, -2200, -1600, 44, 300 ) ),
    ( "Signal Box", ( 0, -2040, 200 ), ( -130, 130, -2180, -1900, 130, 300 ) ),
]


# ---------------------------------------------------------------------------------------------------------------------
# Where things go in the scene (plan; z is the floor under them)

RED_SPAWNS = [ ( -e, n, ROAD_Z ) for e in ( 1640, 1860 ) for n in ( -450, -270, -90, 90, 270, 450 ) ]
BLUE_SPAWNS = [ ( -e, n, z ) for e, n, z in RED_SPAWNS ]
BUY_ZONE = ( 1500, 2200, -800, 800, -10, 260 )

DM_HALF = [ ( 400, 960, 0 ), ( 1000, 1220, 0 ), ( 150, 1420, 0 ), ( 300, 1720, S.GALLERY_Z ), ( 800, 1560, 0 ),
            ( 1080, 1720, 0 ), ( 632, 250, 0 ), ( 632, -850, 0 ), ( 1080, -600, 0 ), ( 1080, 600, 0 ),
            ( 400, -280, S.DECK_Z ), ( 600, -2200, BED_Z ), ( 1000, -1900, BED_Z ), ( 1950, -1450, 0 ),
            ( 1700, -2340, 0 ), ( 1750, 1300, ROAD_Z ), ( 1750, -1100, ROAD_Z ) ]
DM_SPAWNS = [ p for e, n, z in DM_HALF for p in ( ( e, n, z ), ( -e, n, z ) ) ] + [ ( 0, -900, 0 ), ( 0, -1500, 0 ) ]

# ( name, display name, e0, e1, n0, n1, floor )
BOMB_SITES = [ ( "bombsite_a", "Bomb Site A", 760, 1150, 900, 1280, 0 ),
               ( "bombsite_b", "Bomb Site B", 1870, 2190, -2300, -1620, 0 ) ]

# Retakes: the planter and the defenders are Red Team (Terrorist), the attackers Blue Team (CounterTerrorist).
RETAKES = {
    "bombsite_a": { "planter": [ ( 950, 1100, 0 ), ( 1000, 960, 0 ) ],
                    "defender": [ ( 180, 1600, 0 ), ( 820, 1560, 0 ), ( 480, 960, 0 ), ( 1080, 600, 0 ) ],
                    "attacker": [ ( -1037, -600, 0 ), ( -632, -900, 0 ), ( 1750, -1100, ROAD_Z ), ( 632, -850, 0 ),
                                  ( -1750, -600, ROAD_Z ) ] },
    "bombsite_b": { "planter": [ ( 2000, -1900, 0 ), ( 2050, -2200, 0 ) ],
                    "defender": [ ( 2050, -1500, 0 ), ( 1580, -1740, S.BANK[4] ), ( 1500, -2140, S.BANK[4] ),
                                  ( 1740, -2220, 0 ) ],
                    "attacker": [ ( 1750, 200, ROAD_Z ), ( 1750, 450, ROAD_Z ), ( 1640, 300, ROAD_Z ), ( -600, -2200, BED_Z ),
                                  ( 1037, -400, 0 ) ] },
}

DOMINATION = [ ( "A", ( -1037, 420, 0 ) ), ( "B", ( 0, -980, 0 ) ), ( "C", ( 1037, 420, 0 ) ) ]
HOT_ZONES = [ ( "Concourse", ( 0, 1160, 0 ) ), ( "Booking Hall", ( 0, 1560, 0 ) ), ( "Centre Platform", ( 0, -740, 0 ) ),
              ( "Signal Box", ( 0, -1820, BED_Z ) ), ( "West Yard", ( -1960, -1880, 0 ) ), ( "East Yard", ( 1960, -1880, 0 ) ) ]
# Cash Grab: ( name, the cash, where it's taken ). The cash sits 8 over the floor and the extraction point 32.
CASH_POINTS = [ ( "Booking Hall", ( 0, 1600, 0 ), ( 0, -1820, BED_Z ) ),
                ( "West Yard", ( -1960, -1880, 0 ), ( 1037, 420, 0 ) ),
                ( "East Yard", ( 1960, -1880, 0 ), ( -1037, 420, 0 ) ) ]

# Callouts for the location readout: ( name, e0, e1, n0, n1[, z0, z1] ), z -60..190 when left out. Mirrored pairs
# are listed east first; no two overlap.
UP = ( 190, 420 )


def callouts():
    out = [ ( "CONCOURSE", -1160, 760, 880, 1300, -60, 400 ), ( "A SITE", 760, 1160, 880, 1300, -60, 400 ),
            ( "BOOKING HALL", -600, 600, 1300, 1820, -60, 190 ), ( "GALLERY", -600, 600, 1300, 1820, *UP ),
            ( "CENTRE PLATFORM", -170, 170, -1780, 880, -10, 150 ), ( "FOOTBRIDGE", -1200, 1200, -340, -220, 150, 420 ),
            ( "SIGNAL BOX", -130, 130, -2400, -1780, -60, 420 ) ]
    for s, side in ( ( 1, "EAST" ), ( -1, "WEST" ) ):
        def box( name, e0, e1, *rest ):
            a, b = sorted( ( s * e0, s * e1 ) )
            return ( name, a, b, *rest )
        out += [
            box( f"{side} CAB ROAD", 1500, 2200, -1340, 1820, -60, 400 ),
            box( f"{side} ARCADE", 1200, 1500, -1340, 1820, -60, 400 ),
            box( f"{side} WING", 600, 1200, 1300, 1820, -60, 420 ),
            box( f"GLEIS {GLEIS[( s, 'B' )]}-{GLEIS[( s, 'C' )]}", 482, 782, -1780, 880, -10, 150 ),
            box( f"GLEIS {GLEIS[( s, 'C' )]}", 914, 1200, -1780, 880, -10, 150 ),
            box( f"{side} TRACKS", 170, 482, -1780, 880, -60, 150 ),
            box( f"{side} OUTER TRACK", 782, 914, -1780, 880, -60, 150 ),
            box( f"{side} THROAT", 130, 1200, -2400, -1780, -60, 420 ),
        ]
        if s > 0:
            out += [ ( "EAST YARD", 1200, 1870, -2400, -1340, -60, 420 ), ( "B SITE", 1870, 2200, -2400, -1600, -60, 420 ),
                     ( "YARD GATE", 1870, 2200, -1600, -1340, -60, 420 ) ]
        else:
            out += [ ( "WEST YARD", -2200, -1200, -2400, -1340, -60, 420 ) ]
    # The footbridge's callout crosses the platforms' boxes only above theirs (150 up).
    return out


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
# Checks (as Reef Hall's, with sloped hulls: the platforms' ramps and the stairs)

def collision_aabbs( models ):
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
    """ Every spot needs room for a player (32 x 32 x 72 over it) and a floor within 2 under it. Rotated shapes and
    hulls count by their bounding boxes, so this errs on the tight side. """
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


REACH_CELL = 8.0
REACH_BOUNDS = ( -2200.0, 2200.0, -2400.0, 1824.0 )    # e0, e1, n0, n1
REACH_RADIUS, REACH_STEP, REACH_HEAD = 16.0, 18.0, 64.0
WALKABLE = 0.766                                         # cos 40 degrees: the navmesh's steepest walkable slope


def hull_2d( points ):
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


def grid_shape( bounds=REACH_BOUNDS ):
    e0, e1, n0, n1 = bounds
    return int( ( e1 - e0 ) / REACH_CELL ), int( ( n1 - n0 ) / REACH_CELL )


def reach_cells( outline, grow, size, bounds=REACH_BOUNDS ):
    """ The cells ( i, j ) whose centres are in a convex outline grown by grow, and their centres. """
    cols, rows = size
    e0, _, n0, _ = bounds
    if len( outline ) < 3:
        return np.zeros( 0, int ), np.zeros( 0, int ), np.zeros( 0 ), np.zeros( 0 )
    lo, hi = outline.min( axis=0 ) - grow, outline.max( axis=0 ) + grow
    i0, i1 = max( int( math.floor( ( lo[0] - e0 ) / REACH_CELL ) ), 0 ), min( int( math.ceil( ( hi[0] - e0 ) / REACH_CELL ) ), cols - 1 )
    j0, j1 = max( int( math.floor( ( lo[1] - n0 ) / REACH_CELL ) ), 0 ), min( int( math.ceil( ( hi[1] - n0 ) / REACH_CELL ) ), rows - 1 )
    if i1 < i0 or j1 < j0:
        return np.zeros( 0, int ), np.zeros( 0, int ), np.zeros( 0 ), np.zeros( 0 )
    xs = e0 + ( np.arange( i0, i1 + 1 ) + 0.5 ) * REACH_CELL
    ys = n0 + ( np.arange( j0, j1 + 1 ) + 0.5 ) * REACH_CELL
    gx, gy = np.meshgrid( xs, ys, indexing="ij" )
    inside = np.ones( gx.shape, bool )
    for k in range( len( outline ) ):
        a, b = outline[k], outline[( k + 1 ) % len( outline )]
        length = math.hypot( *( b - a ) )
        if length > 1e-9:
            inside &= ( gx - a[0] ) * ( b[1] - a[1] ) / length - ( gy - a[1] ) * ( b[0] - a[0] ) / length <= grow + 1e-6
    ii, jj = np.nonzero( inside )
    return ii + i0, jj + j0, gx[ii, jj], gy[ii, jj]


def top_planes( points ):
    """ The upward-facing planes of a point set's convex hull: ( normals ( k, 3 ), offsets ( k ) ), n . p + d = 0. """
    from scipy.spatial import ConvexHull
    try:
        hull = ConvexHull( points )
    except Exception:
        return None
    eq = hull.equations
    up = eq[:, 2] > 0.05
    return eq[up, :3], eq[up, 3]


def shapes( models ):
    """ Every collision shape as ( corner points ( k, 3 ), surface, is_box_level ). """
    for model in models:
        for centre, axes, size, surface in model.boxes:
            ax = np.array( axes, float )
            half = np.asarray( size, float ) / 2
            corners = np.array( [ np.asarray( centre, float ) + ax[0] * a * half[0] + ax[1] * b * half[1] + ax[2] * c * half[2]
                                  for a in ( -1, 1 ) for b in ( -1, 1 ) for c in ( -1, 1 ) ] )
            yield corners, surface, any( abs( abs( a[2] ) - 1 ) < 1e-6 for a in ax )
        for points, surface in model.hulls:
            yield np.array( points, float ), surface, False


def check_reach( models, spots, picture=None, bounds=REACH_BOUNDS ):
    """ Every spot must be on the largest walkable area. Prints the ones that aren't and returns how many; picture
    writes the grid: green walkable, blue upstairs, red and orange cut off. Hulls stand on their top faces: where the
    face over a cell is 40 degrees or less from level it's a floor there, at its height. bounds ( e0, e1, n0, n1 ) is
    the grid's extent (another map's checks pass their own). """
    e0, e1, n0, n1 = bounds
    cols, rows = grid_shape( bounds )
    in_way = {}
    floors = {}

    for pts, _, level in shapes( models ):
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = hull_2d( pts[:, :2] )
        planes = None if level else top_planes( pts )
        # A hull whose only upward faces are level (a prism) is a box as far as walking goes. A wedge (a ramp) has
        # two heights as well, so it's the faces that tell.
        flat = level or ( planes is not None and np.all( planes[0][:, 2] > 0.9999 ) )
        if flat:
            ii, jj, _, _ = reach_cells( outline, REACH_RADIUS, ( cols, rows ), bounds )
            for c in ( ii * rows + jj ).tolist():
                in_way.setdefault( c, [] ).append( ( z0, z1 ) )
            top = pts[pts[:, 2] > z1 - 1e-3]
            ii, jj, _, _ = reach_cells( hull_2d( top[:, :2] ), 0.0, ( cols, rows ), bounds )
            for c in ( ii * rows + jj ).tolist():
                floors.setdefault( c, [] ).append( z1 )
            continue
        if planes is None:
            continue
        normals, offsets = planes
        ii, jj, gx, gy = reach_cells( outline, REACH_RADIUS, ( cols, rows ), bounds )
        if len( ii ) == 0:
            continue
        heights = -( normals[None, :, 0] * gx[:, None] + normals[None, :, 1] * gy[:, None] + offsets[None, :] ) / normals[None, :, 2]
        k = np.argmin( heights, axis=1 )
        top = np.clip( heights[np.arange( len( k ) ), k], z0, z1 )
        for c, t in zip( ( ii * rows + jj ).tolist(), top.tolist() ):
            in_way.setdefault( c, [] ).append( ( z0, t ) )
        ii2, jj2, gx2, gy2 = reach_cells( outline, 0.0, ( cols, rows ), bounds )
        if len( ii2 ) == 0:
            continue
        heights = -( normals[None, :, 0] * gx2[:, None] + normals[None, :, 1] * gy2[:, None] + offsets[None, :] ) / normals[None, :, 2]
        k = np.argmin( heights, axis=1 )
        top = heights[np.arange( len( k ) ), k]
        walk = normals[k, 2] >= WALKABLE
        for c, t, w in zip( ( ii2 * rows + jj2 ).tolist(), top.tolist(), walk.tolist() ):
            if w:
                floors.setdefault( c, [] ).append( min( max( t, z0 ), z1 ) )

    node_z, node_cell, by_cell = [], [], {}
    for c, zs in floors.items():
        for z in sorted( set( round( z, 2 ) for z in zs ) ):
            # A floor's own shape reaches z: only what rises past a step over it, or hangs within a crouch, is in the way.
            if not any( lo < z + REACH_HEAD and hi > z + REACH_STEP for lo, hi in in_way.get( c, () ) ):
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
    if not sizes:
        print( "  nowhere to walk at all" )
        return len( spots )
    main_area = max( sizes, key=sizes.get )
    check_reach.last = ( node_z, node_cell, [ root( k ) for k in range( len( node_z ) ) ], sizes, rows, main_area )

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


class Blockers:
    """ The collision as boxes (centre, axes, half sizes) and hulls (planes), for line-of-sight tests. Glass and
    anything see-through-ish (mesh fences, fabric) doesn't block. """

    def __init__( self, models, ignore=( GLASS, "plastic", "fabric" ) ):
        self.boxes, self.hulls = [], []
        for model in models:
            for centre, axes, size, surface in model.boxes:
                if surface in ignore:
                    continue
                self.boxes.append( ( np.asarray( centre, float ), np.asarray( axes, float ), np.asarray( size, float ) / 2 ) )
            for points, surface in model.hulls:
                if surface in ignore:
                    continue
                from scipy.spatial import ConvexHull
                pts = np.asarray( points, float )
                try:
                    eq = ConvexHull( pts ).equations
                except Exception:
                    continue
                self.hulls.append( ( pts.min( axis=0 ), pts.max( axis=0 ), eq ) )
        if self.boxes:
            self.c = np.array( [ b[0] for b in self.boxes ] )
            self.ax = np.array( [ b[1] for b in self.boxes ] )
            self.h = np.array( [ b[2] for b in self.boxes ] )

    def blocked( self, a, b ):
        a, b = np.asarray( a, float ), np.asarray( b, float )
        d = b - a
        if self.boxes:
            # Each box in its own frame: the slab test along the segment, t in [0, 1].
            rel = np.einsum( "kij,kj->ki", self.ax, a[None, :] - self.c )
            dir_ = np.einsum( "kij,j->ki", self.ax, d )
            with np.errstate( divide="ignore", invalid="ignore" ):
                t0 = ( -self.h - rel ) / dir_
                t1 = ( self.h - rel ) / dir_
            tmin = np.where( np.abs( dir_ ) < 1e-12, np.where( np.abs( rel ) <= self.h, -np.inf, np.inf ), np.minimum( t0, t1 ) )
            tmax = np.where( np.abs( dir_ ) < 1e-12, np.where( np.abs( rel ) <= self.h, np.inf, -np.inf ), np.maximum( t0, t1 ) )
            enter, leave = tmin.max( axis=1 ), tmax.min( axis=1 )
            if np.any( ( enter <= leave ) & ( leave >= 0.0 ) & ( enter <= 1.0 ) ):
                return True
        lo_seg, hi_seg = np.minimum( a, b ), np.maximum( a, b )
        for lo, hi, eq in self.hulls:
            if np.any( hi < lo_seg ) or np.any( lo > hi_seg ):
                continue
            t_in, t_out = 0.0, 1.0
            ok = True
            for nx, ny, nz, off in eq:
                num = -( nx * a[0] + ny * a[1] + nz * a[2] + off )
                den = nx * d[0] + ny * d[1] + nz * d[2]
                if abs( den ) < 1e-12:
                    if num < 0:
                        ok = False
                        break
                    continue
                t = num / den
                if den < 0:
                    t_in = max( t_in, t )
                else:
                    t_out = min( t_out, t )
                if t_in > t_out:
                    ok = False
                    break
            if ok:
                return True
        return False


def check_retakes_sight( blockers, retakes=None ):
    """ No Retakes Red spawn (planter or defender) may see a Blue one (attacker): eye to eye, standing (64 up) or
    crouched (46), both ways. Returns how many pairs can. retakes: another map's table (RETAKES by default). """
    problems = 0
    for site, roles in ( retakes or RETAKES ).items():
        reds = roles["planter"] + roles["defender"]
        for r in reds:
            for b in roles["attacker"]:
                seen = any( not blockers.blocked( ( r[0], r[1], r[2] + hr ), ( b[0], b[1], b[2] + hb ) )
                            for hr in ( 64, 46 ) for hb in ( 64, 46 ) )
                if seen:
                    print( f"  {site}: red {r} can see blue {b}" )
                    problems += 1
    return problems


# ---------------------------------------------------------------------------------------------------------------------
# The radar picture

MINIMAP_CENTRE = ( 0.0, -290.0 )
MINIMAP_SIZE = 4800.0
MINIMAP_PIXELS = 1024


def floor_level( e, n ):
    """ The ground's walking level: 0, the track trenches and the throat at the ballast (-37), the carriageways (-6)
    and the loading banks (44). """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    a = np.abs( e )
    z = np.zeros( np.broadcast( e, n ).shape )
    trench = ( ( ( a >= 170 ) & ( a <= 482 ) ) | ( ( a >= 782 ) & ( a <= 914 ) ) ) & ( n >= -1780 ) & ( n <= 880 )
    z = np.where( trench | ( ( n < -1780 ) & ( a < 1200 ) ), BED_Z, z )
    z = np.where( ( a >= 1500 ) & ( a <= 2000 ) & ( n >= -1340 ) & ( n <= 1820 ), ROAD_Z, z )
    z = np.where( ( a >= 1380 ) & ( a <= 1800 ) & ( n >= -2300 ) & ( n <= -1500 ), S.BANK[4], z )
    return z


def collision_shapes( models ):
    for pts, _, _ in shapes( models ):
        yield pts


def write_minimap( models ):
    """ The ground floor, drawn from the collision's own outlines: where you can walk (grey, the trenches and the
    throat a little bluer), low cover (darker), walls and trains left clear, a light line round the edges. North up. """
    from PIL import ImageDraw
    px = MINIMAP_PIXELS
    scale = MINIMAP_SIZE / px
    left, top = MINIMAP_CENTRE[0] - MINIMAP_SIZE / 2, MINIMAP_CENTRE[1] + MINIMAP_SIZE / 2
    masks = { kind: Image.new( "L", ( px, px ), 0 ) for kind in ( "walk", "low", "tall" ) }
    draws = { kind: ImageDraw.Draw( image ) for kind, image in masks.items() }
    for pts in collision_shapes( models ):
        z0, z1 = float( pts[:, 2].min() ), float( pts[:, 2].max() )
        outline = hull_2d( pts[:, :2] )
        if len( outline ) < 3:
            continue
        centre = outline.mean( axis=0 )
        if not ( PLAY[0] - 50 <= centre[0] <= PLAY[1] + 50 and PLAY[2] - 50 <= centre[1] <= PLAY[3] + 50 ):
            continue
        f = float( floor_level( *centre ) )
        screen = [ ( ( e - left ) / scale, ( top - n ) / scale ) for e, n in outline ]
        if z1 > f + 250 and z0 > f + 100:
            continue                                 # roofs, the footbridge's deck seen from under it, signs
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
    image[walk & ( level < -10 )] = ( 84, 90, 98, 235 )
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
    """ A TeamSpawnPoint facing the map's middle line (the team spawns face across the cab road towards the shed). """
    yaw = K.plan_yaw( ( -position[0], -position[1] * 0.35 ) )
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
                     DelayBetweenUpdates=0.1, Feathering=0.04, FrameInterval=5,
                     MaxDistance=1024 if name.startswith( "Track Ends" ) else 512,
                     Priority=2 if name.startswith( "Track Ends" ) else 0, Projection="Box",
                     RenderDynamically=True, TintColor="1,1,1,1", UpdateStrategy="OnEnabled", ZFar=4096, ZNear=8 ) ] )


def look_object():
    """ The grade, as Belltower's: ambient occlusion, a warm white balance, a light vignette, and the outdoor
    exposure the materials and the sky are made for (2 to 3). """
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


# ( model name, scene name, collide, shadows )
SCENE_MODELS = [
    ( "railhead_centre", "Station Centre", True, True ), ( "railhead_east", "Station East", True, True ),
    ( "railhead_west", "Station West", True, True ), ( "railhead_roof", "Shed Roof", True, True ),
    ( "railhead_glass", "Station Glass", True, False ), ( "railhead_track", "Track", False, True ),
    ( "railhead_dress_centre", "Dressing Centre", True, True ), ( "railhead_dress_east", "Dressing East", True, True ),
    ( "railhead_dress_west", "Dressing West", True, True ), ( "railhead_dress_glass", "Dressing Glass", False, False ),
    ( "railhead_edge_east", "City East", True, True ), ( "railhead_edge_west", "City West", True, True ),
    ( "railhead_north", "City North", False, True ), ( "railhead_south", "Railway South", False, False ),
    ( "railhead_skyline", "Skyline", False, False ),
]


def write_scene( written, light_list, props ):
    foliage = []
    for index, prop in enumerate( props ):
        key = f"foliage/{index}"
        foliage.append( K.game_object( ids, prop.get( "name", "Tree" ), key, K.to_world( prop["position"] ),
                                       K.yaw_rotation( prop.get( "yaw", 0.0 ) ), scale=K.vec( prop.get( "scale", ( 1, 1, 1 ) ) ),
                                       components=[ K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model=prop["path"],
                                                                 RenderType="On", Tint="1,1,1,1" ) ] ) )
    station = K.game_object( ids, "Station", "station", children=[
        model_object( title, f"station/{name}", name, collide, shadows )
        for name, title, collide, shadows in SCENE_MODELS if name in written ] )
    import railhead_canopy
    station["Children"].append( railhead_canopy.scene_group() )
    import railhead_luggage
    station["Children"].append( railhead_luggage.scene_group() )
    import railhead_signal_frame
    station["Children"].append( railhead_signal_frame.scene_group() )
    light_objects = [
        K.game_object( ids, name, f"light/{name}", K.to_world( position ), tags="light_point,light", components=[
            K.component( ids, "Sandbox.PointLight", f"light/{name}/light", Attenuation=1,
                         FogMode="Disabled" if name.startswith(("Ticket ", "Train ", "Buffer ", "Signal Box ")) else "Enabled",
                         FogStrength=0 if name.startswith(("Ticket ", "Train ", "Buffer ", "Signal Box ")) else 1,
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
        name, ce0, ce1, cn0, cn1 = c[:5]
        cz0, cz1 = c[5:7] if len( c ) > 5 else ( -60, 190 )
        callout_objects.append( zone_object( name, f"callout/{k}/{name}", ( ce0, ce1, cn0, cn1, cz0, cz1 ), CALLOUT_COLOUR,
                                             name, [ K.component( ids, "Facepunch.MapLocation", f"callout/{k}/{name}/location" ) ] ) )

    play_centre, play_scale = plan_box( PLAY[0], PLAY[1], PLAY[2], PLAY[3], -100, 800 )
    play_area = K.game_object( ids, "Play Area", "play", play_centre, tags="zone", components=[
        K.component( ids, "Zone", "play/zone", Color="1,1,1,1", DisplayName=None ),
        K.component( ids, "Facepunch.PlayArea", "play/area", Zone=ref( "play", "play/zone", "Zone" ) ),
        box_collider( "play/box", play_scale ),
    ] )
    # Player clips where the map is open: across the throat at the play's south edge, and over the cab roads' north
    # ends, where the streets go on into the city. Far below, a floor that catches anything thrown out.
    clips = [ ( "South", ( PLAY[0], PLAY[1], PLAY[2] - 10, PLAY[2], -60, 1200 ) ),
              ( "North East", ( 1200, PLAY[1], PLAY[3] - 10, PLAY[3], -60, 1200 ) ),
              ( "North West", ( PLAY[0], -1200, PLAY[3] - 10, PLAY[3], -60, 1200 ) ) ]
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
                         Description="A city's terminus on an autumn afternoon: the iron-and-glass train shed over six "
                                     "tracks, the booking hall, the cab roads either side, the station throat and the "
                                     "goods yards.",
                         Group=None, SceneTags="", Version=None ),
            K.component( ids, "Facepunch.MapInformation", "info/map", Image=MAP_ART_PATH, IsVisibleInMenu=True ),
            K.component( ids, "Facepunch.MapSpawnSettings", "info/spawns", UseMapSpawnPoints=False, AllowNavMeshSpawns=False ),
        ] ),
        K.game_object( ids, "Minimap Renderer", "minimap", K.to_world( ( MINIMAP_CENTRE[0], MINIMAP_CENTRE[1], 1500 ) ), components=[
            K.component( ids, "Facepunch.MinimapRenderer", "minimap/renderer", CurrentMinimapPath=MINIMAP_PATH,
                         ExportResolution=f"{MINIMAP_PIXELS},{MINIMAP_PIXELS}", Size=int( MINIMAP_SIZE ) ),
        ] ),
        # The early-afternoon sun from the south-south-west, 38 degrees up: through the shed's glass it lays the
        # roof's ribs across the platforms, and it lights the head building's south face from the platforms' side.
        K.game_object( ids, "Sun", "sun", ( 0, 0, 3000 ), K.angles_rotation( SUN_PITCH, SUN_YAW ), tags="light_directional,light",
                       components=[
            K.component( ids, "Sandbox.DirectionalLight", "sun/light", ContactShadows=True, FogMode="Enabled", FogStrength=1,
                         LightColor="1.32,1.08,0.82,1", ShadowBias=0.0005, ShadowCascadeCount=4, ShadowCascadeSplitRatio=0.91,
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
        station,
        K.game_object( ids, "Trees", "foliage", children=foliage ),
        K.game_object( ids, "Lights", "lights", children=light_objects ),
        K.game_object( ids, "Reflection Probes", "probes", children=[ probe_object( *p ) for p in PROBES ] ),
        # Free-for-all modes spawn at every active spawn point, so the team spawns are left out of them.
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
                "Bounds": { "Mins": K.vec( K.to_world( ( PLAY[1], PLAY[2], -100 ) ) ),
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


# The cloud packages the backdrop's trees come from (Belltower's), for the scene's references.
PROP_PACKAGES = {
    "models/sbox_props/trees/oak/tree_oak_small_a.vmdl": ( "facepunch.tree_oak_small_a#288917", ),
    "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl": ( "facepunch.tree_oak_medium_a#288916", ),
    "models/sbox_props/shrubs/beech/beech_bush_small.vmdl": ( "facepunch.beech_bush_small#145429", ),
}


# ---------------------------------------------------------------------------------------------------------------------

def build():
    """ Every model by name. """
    station = S.build()
    import railhead_canopy
    station["railhead_canopy_pane"] = railhead_canopy.pane_model()
    models = dict( station )
    models["railhead_track"] = track_model()
    import railhead_buffer
    railhead_buffer.ballast_detail( models["railhead_track"] )
    east, west, centre = dress_side( 1 ), dress_side( -1 ), dress_centre()
    glass = Model()
    for m in ( east, west, centre ):
        glass.extend( split_paints( m, GLASS_PAINTS ) )
    models["railhead_dress_east"], models["railhead_dress_west"] = east, west
    models["railhead_dress_centre"], models["railhead_dress_glass"] = centre, glass
    if RB is not None:
        try:
            backdrop = RB.models()
        except Exception as error:
            print( f"railhead_backdrop.models() failed ({type( error ).__name__}: {error}); no city" )
            backdrop = {}
        for name, model in backdrop.items():
            if hasattr( RB, "configure" ):
                RB.configure( model )
            models[name] = model
        # The west row is built in place, in its own colours, so its shop signs read the right way round.
        if "railhead_edge_east" in models and hasattr( RB, "edge_blocks" ):
            try:
                models["railhead_edge_west"] = RB.edge_blocks( -1 )
            except Exception as error:
                print( f"railhead_backdrop.edge_blocks( -1 ) failed ({type( error ).__name__}: {error}); no west row" )
    for model in models.values():
        configure( model )
    return models


def write_map_art( models ):
    """ The menus' picture, a stand-in until there's an in-engine capture: the preview's aerial view, 1920 x 1080. """
    opaque, glass = PV.triangles( models ), PV.triangles( models, glass=True )
    image = PV.perspective( opaque, glass, ( 2600, -3600, 2300 ), ( 0, 200, 0 ), size=( 960, 540 ), fov=60 )
    MAP_ART_FILE.parent.mkdir( parents=True, exist_ok=True )
    image.resize( ( 1920, 1080 ), Image.LANCZOS ).convert( "RGB" ).save( MAP_ART_FILE )
    print( f"wrote {MAP_ART_FILE.relative_to( K.ROOT )}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", nargs="+", metavar=( "DIR", "VIEW" ),
                         help="also write views (all, or those named) and the reach grid to this folder" )
    parser.add_argument( "--no-scene", action="store_true", help="write the models only, not the scene or the radar picture" )
    parser.add_argument( "--backdrop", action="store_true", help="put the city in the previews too (slow)" )
    parser.add_argument( "--art", action="store_true", help="write the menus' stand-in picture from the preview" )
    args = parser.parse_args()

    kiosk_art = optional( "railhead_kiosk_art" )
    if kiosk_art is not None and kiosk_art.missing():
        kiosk_art.write()
    import railhead_card_reader
    if railhead_card_reader.missing():
        railhead_card_reader.write()
    import railhead_ticket_machine
    if railhead_ticket_machine.missing():
        railhead_ticket_machine.write()
    import railhead_train
    if railhead_train.missing():
        railhead_train.write()
    import railhead_signal_box
    if railhead_signal_box.missing():
        railhead_signal_box.write_materials()
    import railhead_buffer
    if railhead_buffer.missing():
        railhead_buffer.write()
    import railhead_luggage
    if railhead_luggage.missing():
        railhead_luggage.write()
    import railhead_signal_frame
    if railhead_signal_frame.missing():
        railhead_signal_frame.write()
    if RM is not None and RM.vending_missing():
        RM.write_texture( "vending", RM.OUT_DIR )
    models = build()
    written = set()
    for name, model in models.items():
        if K.is_empty( model ):
            print( f"{name}: empty, not written" )
            continue
        count = K.write_model( OUT_DIR, RESOURCE_DIR, name, model )
        written.add( name )
        print( f"{name}: {count} triangles, {len( model.boxes )} boxes, {len( model.hulls )} hulls" )
    if MISSING:
        print( "from railhead_props, stood in for:" )
        for name, why in sorted( MISSING.items() ):
            print( f"  {name}: {why}" )
    if UNKNOWN_PAINTS:
        print( f"paints with no material: {', '.join( sorted( UNKNOWN_PAINTS ) )}" )
    light_list = lights()
    print( f"{len( light_list )} lights" )

    solid_names = [ name for name, _, collide, _ in SCENE_MODELS if collide and name in models ]
    solid = [ models[name] for name in solid_names ]
    trolley_collisions = railhead_luggage.placed_collisions()
    solid.append( trolley_collisions )
    frame_collisions = railhead_signal_frame.placed_collisions()
    solid.append( frame_collisions )
    print( "checking spots:" )
    problems = check_spots( collision_aabbs( solid ), all_spots() )
    print( f"  {problems} problem(s) in {len( all_spots() )} spots" )
    out = Path( args.preview[0] ) if args.preview else None
    if out:
        out.mkdir( parents=True, exist_ok=True )
    walked = [ models[name] for name in solid_names if name not in NAV_SKIP ]
    walked.append( trolley_collisions )
    walked.append( frame_collisions )
    cut_off = check_reach( walked, all_spots(), out / "reach.png" if out else None )
    print( f"  {cut_off} spot(s) cut off from the spawns" )
    seen = check_retakes_sight( Blockers( solid ) )
    print( f"  {seen} Retakes pair(s) in sight of each other" )

    props = [ prop for model in models.values() for prop in model.props ]
    if not args.no_scene:
        write_minimap( solid )
        write_scene( written, light_list, props )
    preview_names = [ n for n in models if n not in ( "railhead_north", "railhead_south", "railhead_skyline" ) or args.backdrop ]
    if out:
        PV.write_previews( out, [ models[n] for n in preview_names ], views=args.preview[1:] or None )
    if args.art:
        write_map_art( [ models[n] for n in preview_names ] )


if __name__ == "__main__":
    main()
