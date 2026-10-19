"""
Cerro Blanco's fit-out, for Tools/cerroblanco_map.py: what makes the museum look open and used, not built. The map
script records its walls, stairs, plinths and pictures as it builds them (Log.recording), and this module dresses the
rooms they make:

- the galleries' walls: the shows' paintings and drawings (cerroblanco_art.py's sheets) hung in the clear runs of
  wall between doors, windows and stairs, each in its frame with its label, a wall text at each show's start;
- their ceilings: lighting tracks with spot heads turned to the walls, linear air diffusers, smoke detectors, cameras;
- their doors: exit signs over the ones out, room plates beside them; an extinguisher and a return grille per room;
- benches and glass vitrines (with collision, kept clear of every spawn, objective, stair and doorway);
- the lobby: banners hung in the rotunda, queue stanchions, screens on the desk, wayfinding totems;
- the cafe: the espresso machine and grinder, a pastry case, pendant lights, the menu board, cups on the tables;
- outside: wall lights by the doors, wayfinding totems, the opening hours, cameras, downpipes, the roofs' plant
  (air-handling units, vents and hatches), bike hoops and three flagpoles on the forecourt.

Everything is in plan coordinates (map_kit's e, n, z inches). build( log ) returns two models: cerroblanco_fitout
(what you can bump into, with collision) and cerroblanco_fitout_fine (drawn only). Its paints are cbf_ ones: flat
paints written here (write_materials) and the drawn sheets in materials/cerroblanco/fitout/.
"""
import contextlib
import inspect
import json
import math
from pathlib import Path

import numpy as np

import map_kit as K
from map_kit import Model
import cerroblanco_parts as P

RESOURCE = "materials/cerroblanco/fitout"
LAYOUT_FILE = K.ASSETS / RESOURCE / "layout.json"
QUALITY = "materials/cerroblanco/quality-v1"
QUALITY_PAINTS = ( "cb_honed", "cb_paving", "cb_travertine", "cb_panel", "cb_frame", "cb_steel", "cb_plaster", "cb_white",
                   "cb_red", "cb_teak" )

# The fit-out's flat paints: ( colour, metalness, roughness ).
FLAT = {
    "cbf_track": ( ( 24, 24, 26 ), 0.6, 0.42 ),          # black anodised lighting tracks and spot heads
    "cbf_bronze": ( ( 66, 52, 40 ), 0.8, 0.45 ),         # dark bronze wall lights and totem frames
    "cbf_leather": ( ( 38, 32, 30 ), 0.0, 0.5 ),         # the benches' black leather
    "cbf_canvas": ( ( 234, 232, 226 ), 0.0, 0.85 ),      # a gallery-wrapped canvas's edges
    "cbf_oak": ( ( 148, 110, 72 ), 0.0, 0.48 ),          # oak frames
    "cbf_gilt": ( ( 176, 138, 70 ), 0.9, 0.36 ),         # gilded frames
    "cbf_chrome": ( ( 206, 208, 210 ), 1.0, 0.14 ),      # stanchions, the espresso machine's groups
    "cbf_belt": ( ( 22, 22, 26 ), 0.0, 0.6 ),            # the stanchions' belts
    "cbf_screen": ( ( 10, 12, 16 ), 0.0, 0.08 ),         # screens, off
    "cbf_plastic": ( ( 232, 232, 228 ), 0.0, 0.5 ),      # smoke detectors, cameras' domes, cups
    "cbf_grille": ( ( 54, 56, 58 ), 0.3, 0.6 ),          # diffusers and return grilles
    "cbf_hvac": ( ( 168, 172, 174 ), 0.75, 0.42 ),       # the air-handling units' galvanised casings
    "cbf_pipe": ( ( 196, 196, 192 ), 0.0, 0.62 ),        # roof vents, downpipes (painted to the panels)
    "cbf_clay": ( ( 176, 100, 64 ), 0.0, 0.7 ),          # pottery in the vitrines
    "cbf_pastry": ( ( 196, 140, 76 ), 0.0, 0.7 ),        # pan dulce in the case
    "cbf_flag": ( ( 22, 52, 92 ), 0.0, 0.85 ),           # the flags (the museum's blue)
    "cbf_flag_light": ( ( 238, 232, 218 ), 0.0, 0.85 ),
    "cbf_label": ( ( 246, 245, 241 ), 0.0, 0.7 ),
    "cbf_blind": ( ( 232, 230, 224 ), 0.0, 0.9 ),         # roller blinds behind the upper windows
    "cbf_terracotta": ( ( 168, 92, 60 ), 0.0, 0.85 ),     # the agaves' pots
    "cbf_agave": ( ( 92, 120, 112 ), 0.0, 0.6 ),          # agave leaves: a waxy blue-green
    "cbf_mobile_red": ( ( 178, 34, 28 ), 0.1, 0.4 ),       # the rotunda's mobile
    "cbf_mobile_black": ( ( 20, 20, 22 ), 0.1, 0.4 ),
    "cbf_mobile_yellow": ( ( 222, 172, 40 ), 0.1, 0.4 ),
}
# Drawn or self-lit: their vmats are cerroblanco_art's, or written below.
DRAWN = { "cbf_art": "cb_art", "cbf_walltext": "cb_walltext", "cbf_signs": "cb_signs", "cbf_exit": "cb_exit",
          "cbf_letters": "cb_letters" }
LENS = "cbf_lens"                                       # a lamp's lit diffuser: self-lit warm white
GLASS = "cb_glass"                                      # the museum's own low-e glass (cerroblanco_map writes it)

METAL, STONE, WOOD = P.METAL, P.STONE, P.WOOD


# ---------------------------------------------------------------------------------------------------------------------
# What the map script built

class Log:
    """ The map script's walls, stairs and furniture, recorded as it builds them, by the arguments it gave. """

    def __init__( self ):
        self.walls, self.flights, self.pictures, self.gallery_walls = [], [], [], []
        self.plinths, self.benches, self.balustrades, self.tables, self.columns = [], [], [], [], []
        self.upstairs_walls, self.upstairs_plinths = [], []

    @contextlib.contextmanager
    def recording( self, C ):
        originals = []

        def wrap( module, name, store ):
            fn = getattr( module, name )
            signature = inspect.signature( fn )

            def call( *args, **kwargs ):
                bound = signature.bind( *args, **kwargs )
                bound.apply_defaults()
                store.append( { k: v for k, v in bound.arguments.items() if k not in ( "m", "g", "glass", "c", "d" ) } )
                return fn( *args, **kwargs )

            setattr( module, name, call )
            originals.append( ( module, name, fn ) )

        wrap( C, "wall", self.walls )
        wrap( C, "column", self.columns )
        wrap( C, "upstairs_wall", self.upstairs_walls )
        wrap( C, "upstairs_plinth", self.upstairs_plinths )
        for name, store in ( ( "flight", self.flights ), ( "picture", self.pictures ), ( "gallery_wall", self.gallery_walls ),
                             ( "display_plinth", self.plinths ), ( "bench", self.benches ), ( "balustrade", self.balustrades ),
                             ( "cafe_table", self.tables ) ):
            wrap( P, name, store )
        try:
            yield self
        finally:
            for module, name, fn in reversed( originals ):
                setattr( module, name, fn )


class Room:
    """ A room: its plan rectangle inside its walls, its floor and ceiling, the show hung in it and its plate. """

    def __init__( self, key, plate, show, rect, floor, ceiling, pool, scale=1.0, holes=(), low=() ):
        self.key, self.plate, self.show = key, plate, show
        self.e0, self.e1, self.n0, self.n1 = rect
        self.floor, self.ceiling = floor, ceiling
        self.pool = list( pool )
        self.scale = scale
        self.holes = list( holes )          # rectangles open in the ceiling (stairwells): no fittings over them
        self.low = list( low )              # rectangles where the ceiling is lower (under a mezzanine): no tracks
        self.low_ceiling = 164.0            # the ceiling there (the mezzanine's underside)

    def contains( self, e, n, z ):
        return self.e0 - 0.5 <= e <= self.e1 + 0.5 and self.n0 - 0.5 <= n <= self.n1 + 0.5 and self.floor - 1 <= z <= self.ceiling + 1


def rooms( C ):
    F1, LOW, HIGH = C.FLOOR1, C.SLAB, C.ROOF - 16
    portraits = [ "rostro_rebozo", "rostro_maestro", "rostro_hermana", "rostro_sombrero" ]
    seas = [ "marea_punta", "marea_violeta", "marea_barcas", "marea_ola" ]
    land = [ "tierra_mesa", "tierra_magueyes", "tierra_roja", "tierra_camino" ]
    drawings = [ "forma_vacio", "forma_torso" ]
    fields = [ "campo_4", "campo_7" ]
    return [
        Room( "sala_1", "room_sala_1", "rostros", ( -1108, -668, -142, 1492 ), 0, LOW, portraits + fields[:1],
              holes=[ ( -1108, -1030, 400, 700 ) ] ),
        Room( "sala_2", "room_sala_2", None, ( -1108, -668, -142, 1492 ), F1, HIGH, portraits[2:] + drawings + portraits[:2] ),
        Room( "sala_3", "room_sala_3", None, ( -668, -218, 1068, 1492 ), 0, LOW, fields + portraits[1:3] ),
        Room( "sala_4", "room_sala_4", None, ( -668, -218, 1068, 1492 ), F1, HIGH, drawings + fields ),
        Room( "cafe", "room_cafeteria", None, ( 498, 1000, 0, 697 ), 0, C.CAFE_TOP, [ "tierra_camino", "marea_barcas" ] ),
        Room( "glass_room", "room_sala_6", None, ( 498, 1000, 0, C.CAFE_UP - 18 ), F1, HIGH, fields ),
        Room( "sala_5", "room_sala_5", "mareas", ( 1018, 2042, 0, 697 ), 0, LOW, seas + [ "tierra_mesa" ],
              holes=[ ( 1964, 2042, 300, 600 ) ] ),
        Room( "sala_6", "room_sala_6", None, ( 1018, 2042, 0, 697 ), F1, HIGH, seas[::-1] + fields ),
        Room( "sala_7", "room_sala_7", "forma", ( 498, 1382, -982, -18 ), 0, HIGH, drawings + fields, scale=1.25,
              low=[ ( 1220, 1382, -982, -18 ) ] ),
        Room( "sala_8", "room_sala_8", "tierra", ( -1012, 462, -2132, -1018 ), 0, C.SG_ROOF - 16, land + seas[:2],
              scale=1.2 ),
    ]


# ---------------------------------------------------------------------------------------------------------------------
# Geometry helpers

UP = np.array( ( 0.0, 0.0, 1.0 ) )


def unit( v ):
    v = np.asarray( v, float )
    return v / max( float( np.linalg.norm( v ) ), 1e-12 )


def frame_axes( out ):
    """ For something hung on a wall facing out: side (a right-handed box's x, the viewer's left), the viewer's right
    and up. """
    out = unit( ( out[0], out[1], 0.0 ) )
    side = np.cross( out, UP )
    return side, -side, UP


class Face:
    """ One face of a wall: the plane across = d, facing out (a plan unit vector along the axis across the wall), its
    run along the wall, and the openings ( r0, r1, z0, z1 ) through it. """

    def __init__( self, axis, d, out, run, z0, z1, openings ):
        self.axis, self.d = axis, d
        self.out = np.array( ( out[0], out[1], 0.0 ) )
        self.run = run
        self.z0, self.z1 = z0, z1
        self.openings = openings

    def point( self, r, z, off=0.0 ):
        base = np.array( ( r, self.d, z ) if self.axis == "e" else ( self.d, r, z ), float )
        return base + self.out * off

    def along( self ):
        return np.array( ( 1.0, 0.0, 0.0 ) if self.axis == "e" else ( 0.0, 1.0, 0.0 ) )


def faces_of( record ):
    """ Both faces of a recorded wall, with its openings in run coordinates. """
    axis, run, across = record["axis"], record["run"], record["across"]
    openings = [ ( c - w / 2, c + w / 2, a, b ) for c, w, a, b in list( record["doors"] ) + list( record["windows"] ) ]
    lo, hi = min( across ), max( across )
    out_lo = ( 0.0, -1.0 ) if axis == "e" else ( -1.0, 0.0 )
    out_hi = ( 0.0, 1.0 ) if axis == "e" else ( 1.0, 0.0 )
    return [ Face( axis, lo, out_lo, tuple( sorted( run ) ), record["z0"], record["z1"], openings ),
             Face( axis, hi, out_hi, tuple( sorted( run ) ), record["z0"], record["z1"], openings ) ]


def free_runs( lo, hi, blocked ):
    """ The parts of lo..hi not in any blocked ( a, b ). """
    here, out = lo, []
    for a, b in sorted( blocked ):
        if b <= here:
            continue
        if a > here:
            out.append( ( here, min( a, hi ) ) )
        here = max( here, b )
        if here >= hi:
            break
    if here < hi:
        out.append( ( here, hi ) )
    return [ ( a, b ) for a, b in out if b - a > 1 ]


def box_from( m, lo, hi, paint, surface=None ):
    m.box( lo, hi, paint, surface )


def lathe( m, paint, centre, profile, sides=16, axis=( 0.0, 0.0, 1.0 ), cap_top=True ):
    """ A surface of revolution about axis through centre: profile is ( radius, height ) from the bottom up. """
    c = np.asarray( centre, float )
    a = unit( axis )
    ref = np.array( ( 1.0, 0.0, 0.0 ) ) if abs( a[0] ) < 0.9 else np.array( ( 0.0, 1.0, 0.0 ) )
    u = unit( np.cross( a, ref ) )
    v = np.cross( a, u )
    rings = []
    for r, h in profile:
        rings.append( [ c + a * h + ( u * math.cos( 2 * math.pi * k / sides ) + v * math.sin( 2 * math.pi * k / sides ) ) * r
                        for k in range( sides ) ] )
    for ( r0, h0 ), ( r1, h1 ), ra, rb in zip( profile, profile[1:], rings, rings[1:] ):
        for k in range( sides ):
            p, q = ra[k], ra[( k + 1 ) % sides]
            s, t = rb[k], rb[( k + 1 ) % sides]
            if r0 < 1e-6 and r1 < 1e-6:
                continue
            na = unit( p - c - a * h0 ) if r0 > 1e-6 else unit( s - c - a * h1 )
            nb = unit( q - c - a * h0 ) if r0 > 1e-6 else unit( t - c - a * h1 )
            slope = ( r0 - r1 ) / max( abs( h1 - h0 ), 1e-6 )
            na, nb = unit( na + a * slope ), unit( nb + a * slope )
            pts = [ p, q, t, s ] if r0 > 1e-6 else [ p, t, s ]
            if r1 < 1e-6:
                pts = [ p, q, t ]
            m.polygon( paint, pts, normal=( na + nb ) / 2 )
    if cap_top and profile[-1][0] > 1e-6:
        m.polygon( paint, rings[-1], normal=a )


def cylinder_between( m, paint, a, b, r, sides=10, caps=True ):
    P.rod( m, a, b, r, paint, sides=sides, caps=caps )


# ---------------------------------------------------------------------------------------------------------------------
# Hanging the shows

class Hanger:
    """ Hangs works and texts on faces, keeping a list of what's taken so nothing overlaps. """

    def __init__( self, layout, fine ):
        self.layout = layout
        self.fine = fine
        self.used = {}                       # face key -> [ ( r0, r1, z0, z1 ) ]
        self.count = 0
        self.lights = []                     # ( name, plan position, plan target, radius ): a spot on each work

    def free( self, face, r0, r1, z0, z1 ):
        key = ( face.axis, round( face.d, 2 ), tuple( face.out.round( 2 ) ) )
        return all( r1 <= a or r0 >= b or z1 <= c or z0 >= d for a, b, c, d in self.used.get( key, [] ) )

    def take( self, face, r0, r1, z0, z1 ):
        key = ( face.axis, round( face.d, 2 ), tuple( face.out.round( 2 ) ) )
        self.used.setdefault( key, [] ).append( ( r0, r1, z0, z1 ) )

    def work( self, face, r, z, key, height, style ):
        """ A work centred at run r, height z: its canvas (or paper under glass) in its frame, the label to its right. """
        art = self.layout["art"][key]
        h = height
        w = h * art["aspect"]
        m = self.fine
        out = face.out
        side, right, up = frame_axes( out )
        u0, v0, u1, v1 = art["uv"]
        depth = 1.75 if style == "wrap" else 1.25
        centre = face.point( r, z, 0.0 )
        # The canvas's front, depth off the wall.
        c = centre + out * depth
        corners = [ c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2 ]
        P.card( m, "cbf_art", corners, out, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )
        if style == "wrap":
            m.oriented_box( centre + out * depth / 2, ( side, out, up ), ( w, depth, h ), { "default": "cbf_canvas", "+y": None, "-y": None } )
        else:
            paint = { "black": P.BLACK, "oak": "cbf_oak", "gilt": "cbf_gilt" }[style]
            fw, fd = ( 2.4, depth + 0.6 ) if style != "gilt" else ( 3.4, depth + 1.0 )
            for s in ( -1, 1 ):
                m.oriented_box( centre + right * s * ( w / 2 + fw / 2 ) + out * fd / 2, ( side, out, up ), ( fw, fd, h + 2 * fw ), paint )
                m.oriented_box( centre + up * s * ( h / 2 + fw / 2 ) + out * fd / 2, ( side, out, up ), ( w, fd, fw ), paint )
            if style == "gilt":
                for s in ( -1, 1 ):
                    m.oriented_box( centre + right * s * ( w / 2 + 0.5 ) + out * ( fd - 0.2 ), ( side, out, up ), ( 1.0, 0.6, h + 1.0 ), "cbf_oak" )
                    m.oriented_box( centre + up * s * ( h / 2 + 0.5 ) + out * ( fd - 0.2 ), ( side, out, up ), ( w + 1.0, 0.6, 1.0 ), "cbf_oak" )
            m.oriented_box( centre + out * depth / 2, ( side, out, up ), ( w, depth, h ), { "default": P.BLACK, "+y": None, "-y": None } )
        # The label: a card to the right, its top level with the work's lower third.
        lw, lh = 6.4, 4.48
        uv = self.layout["signs"][f"label_{key}"]
        frame_w = w / 2 + ( 3.4 if style == "gilt" else 2.4 if style != "wrap" else 0 )
        lc = face.point( r, z, 0.0 ) + right * ( frame_w + 7 + lw / 2 ) + up * ( -h / 6 - lh / 2 ) + out * 0.35
        if z - h / 6 - lh < face.z0 + 30:
            lc = face.point( r, z, 0.0 ) + right * ( frame_w + 7 + lw / 2 ) + out * 0.35
        m.oriented_box( lc - out * 0.15, ( side, out, up ), ( lw, 0.3, lh ), "cbf_label" )
        corners = [ lc - right * lw / 2 - up * lh / 2 + out * 0.01, lc + right * lw / 2 - up * lh / 2 + out * 0.01,
                    lc + right * lw / 2 + up * lh / 2 + out * 0.01, lc - right * lw / 2 + up * lh / 2 + out * 0.01 ]
        P.card( m, "cbf_signs", corners, out, uv=[ ( uv[0], uv[1] ), ( uv[2], uv[1] ), ( uv[2], uv[3] ), ( uv[0], uv[3] ) ] )
        self.count += 1
        self.light( face, r, z, h, f"Art {self.count:02d}" )
        return w + 2 * ( 3.4 if style == "gilt" else 2.4 ) + 7 + lw

    def light( self, face, r, z, h, name ):
        """ A spot on the ceiling above a work, out from the wall, aimed at the work's middle: the fitting drawn, the
        light listed for the scene. None over a stairwell. """
        room = self.current_room
        out = face.out
        p = face.point( r, 0.0, 56.0 )
        if in_rects( p[0], p[1], room.holes, margin=12 ):
            return
        ceiling = room.low_ceiling if in_rects( p[0], p[1], room.low ) else room.ceiling
        at = face.point( r, ceiling - 1.4, 0.0 ) + out * min( 64.0, 0.55 * ( ceiling - z ) )
        target = face.point( r, z, 0.0 ) + out * 2.0
        spot_head( self.fine, at, target - at + UP * 3.4 )
        self.lights.append( ( name, tuple( at - UP * 6 ), tuple( target ), float( min( 340.0, np.linalg.norm( target - at ) * 1.6 ) ) ) )

    def walltext( self, face, r, z, show, width ):
        """ A show's wall text in grey vinyl letters, width across, centred at run r, height z. """
        rect = self.layout["walltext"][show]["title"]
        aspect = ( rect[2] - rect[0] ) / ( rect[3] - rect[1] )
        h = width / aspect
        out = face.out
        side, right, up = frame_axes( out )
        c = face.point( r, z, 0.12 )
        corners = [ c - right * width / 2 - up * h / 2, c + right * width / 2 - up * h / 2, c + right * width / 2 + up * h / 2,
                    c - right * width / 2 + up * h / 2 ]
        P.card( self.fine, "cbf_walltext", corners, out, uv=[ ( rect[0], rect[1] ), ( rect[2], rect[1] ), ( rect[2], rect[3] ),
                                                              ( rect[0], rect[3] ) ] )
        return h


def sign_card( m, layout_uv, centre, out, width, height, off=0.0, back=None, depth=0.25 ):
    """ A sign's printed face (cbf_signs at layout_uv) on a plate depth thick, facing out. """
    side, right, up = frame_axes( out )
    out3 = unit( ( out[0], out[1], 0.0 ) )
    c = np.asarray( centre, float ) + out3 * off
    if back:
        m.oriented_box( c - out3 * depth / 2, ( side, out3, up ), ( width, depth, height ), back )
    u0, v0, u1, v1 = layout_uv
    corners = [ c - right * width / 2 - up * height / 2 + out3 * 0.02, c + right * width / 2 - up * height / 2 + out3 * 0.02,
                c + right * width / 2 + up * height / 2 + out3 * 0.02, c - right * width / 2 + up * height / 2 + out3 * 0.02 ]
    P.card( m, "cbf_signs", corners, out3, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )


# ---------------------------------------------------------------------------------------------------------------------
# Galleries

def room_faces( room, walls ):
    """ Every wall face that bounds this room on its floor: the part of it inside the room's rectangle, facing in. """
    out = []
    for record in walls:
        for f in faces_of( record ):
            probe_z = room.floor + 60
            if not ( f.z0 - 1 <= probe_z <= f.z1 + 1 ):
                continue
            r0, r1 = f.run
            if f.axis == "e":
                lo, hi = max( r0, room.e0 ), min( r1, room.e1 )
            else:
                lo, hi = max( r0, room.n0 ), min( r1, room.n1 )
            if hi - lo < 24:
                continue
            p = f.point( ( lo + hi ) / 2, probe_z, 12.0 )
            if not room.contains( p[0], p[1], p[2] ):
                continue
            f.run = ( lo, hi )
            out.append( f )
    return out


def blocked_on( face, room, log, band ):
    """ The runs of a face that can't take a work: openings in the band (and a margin), stairs along it, pictures
    already on it, the room's corners. """
    z_lo, z_hi = band
    blocked = []
    for a, b, oz0, oz1 in face.openings:
        if oz1 > z_lo - 6 and oz0 < z_hi + 6:
            blocked.append( ( a - 20, b + 20 ) )
    for f in log.flights:
        if f["axis"] == "n":
            fe0, fe1 = sorted( ( f["a0"], f["a1"] ) )
            fn0, fn1 = sorted( ( f["r_top"], f["r_foot"] ) )
        else:
            fn0, fn1 = sorted( ( f["a0"], f["a1"] ) )
            fe0, fe1 = sorted( ( f["r_top"], f["r_foot"] ) )
        near = ( face.axis == "n" and min( abs( face.d - fe0 ), abs( face.d - fe1 ) ) < 30 ) or \
               ( face.axis == "e" and min( abs( face.d - fn0 ), abs( face.d - fn1 ) ) < 30 )
        if near and min( f["z_top"], f["z_foot"] ) < z_hi and max( f["z_top"], f["z_foot"] ) + 60 > z_lo:
            blocked.append( ( fn0 - 40, fn1 + 120 ) if face.axis == "n" else ( fe0 - 40, fe1 + 120 ) )
    for p in log.pictures:
        e, n = p["centre"]
        if ( face.axis == "e" and abs( n - face.d ) < 4 ) or ( face.axis == "n" and abs( e - face.d ) < 4 ):
            r = e if face.axis == "e" else n
            blocked.append( ( r - p["w"] / 2 - 30, r + p["w"] / 2 - 30 + 60 ) )
    # Balustrades along a face (a stairwell's edge, a mezzanine's): nothing hung over them.
    for b in log.balustrades:
        ( e0, n0 ), ( e1, n1 ) = b["p0"], b["p1"]
        if face.axis == "n" and abs( e0 - e1 ) < 1 and abs( e0 - face.d ) < 40:
            blocked.append( ( min( n0, n1 ) - 30, max( n0, n1 ) + 30 ) )
        if face.axis == "e" and abs( n0 - n1 ) < 1 and abs( n0 - face.d ) < 40:
            blocked.append( ( min( e0, e1 ) - 30, max( e0, e1 ) + 30 ) )
    lo, hi = face.run
    blocked += [ ( lo - 1, lo + 30 ), ( hi - 30, hi + 1 ) ]
    return blocked


STYLES = { "portrait": [ "gilt", "black", "oak", "black" ], "sea": [ "oak", "black", "oak", "wrap" ],
           "plateau": [ "black", "wrap", "black", "oak" ], "drawing": [ "black" ], "field": [ "wrap" ] }
HEIGHTS = { "portrait": 40.0, "sea": 34.0, "plateau": 38.0, "drawing": 32.0, "field": 56.0 }


def display_walls( log, C ):
    """ The freestanding display walls (the ground floors' and the upper floors'), as wall records with no openings,
    so works can hang down both their long sides. """
    out = []
    for g, z0 in [ ( g, 0.0 ) for g in log.gallery_walls ] + [ ( g, C.FLOOR1 ) for g in log.upstairs_walls ]:
        e0, e1, n0, n1 = g["e0"], g["e1"], g["n0"], g["n1"]
        along_e = ( e1 - e0 ) >= ( n1 - n0 )
        out.append( { "axis": "e" if along_e else "n", "run": ( e0, e1 ) if along_e else ( n0, n1 ),
                      "across": ( n0, n1 ) if along_e else ( e0, e1 ), "outward": None, "z0": z0, "z1": z0 + g["h"],
                      "doors": [], "windows": [] } )
    return out


def hang_room( hanger, room, log, walls, stats ):
    faces = room_faces( room, walls )
    hanger.current_room = room
    if not faces:
        return
    ceiling_room = room.ceiling - room.floor
    centre_z = room.floor + min( 66.0, 0.42 * ceiling_room )
    band = ( room.floor + 20, room.floor + min( 150.0, ceiling_room - 12 ) )
    pool = list( room.pool )
    k = 0
    # The show's wall text first, on the longest free run of the room.
    if room.show:
        best = None
        for f in faces:
            for a, b in free_runs( *f.run, blocked_on( f, room, log, band ) ):
                if best is None or b - a > best[2] - best[1]:
                    best = ( f, a, b )
        if best and best[2] - best[1] > 150:
            f, a, b = best
            width = min( 120.0, ( b - a ) - 40 )
            r = ( a + b ) / 2
            h = hanger.walltext( f, r, room.floor + 78, room.show, width )
            for side in ( -0.3, 0.3 ):
                hanger.light( f, r + side * width, room.floor + 78, h, f"Wall text {room.show} {'left' if side < 0 else 'right'}" )
            hanger.take( f, r - width / 2 - 24, r + width / 2 + 24, room.floor + 78 - h / 2, room.floor + 78 + h / 2 )
            stats["walltexts"] += 1
    for f in sorted( faces, key=lambda f: ( f.axis, f.d ) ):
        for a, b in free_runs( *f.run, blocked_on( f, room, log, band ) ):
            r = a + 14
            while r < b - 14 and pool:
                key = pool[k % len( pool )]
                art = hanger.layout["art"][key]
                kind = art["kind"]
                h = HEIGHTS[kind] * room.scale
                h = min( h, ( band[1] - band[0] ) * 0.8 )
                style = STYLES[kind][k % len( STYLES[kind] )]
                w = h * art["aspect"]
                span = w + ( 6.8 if style == "gilt" else 4.8 ) + 7 + 6.4
                z = max( centre_z, room.floor + h / 2 + 30 )
                if z + h / 2 > f.z1 - 10:
                    h = max( 20.0, ( f.z1 - 10 - room.floor - 30 ) )
                    w = h * art["aspect"]
                    span = w + ( 6.8 if style == "gilt" else 4.8 ) + 7 + 6.4
                    z = room.floor + 30 + h / 2
                if r + span > b - 10:
                    break
                c = r + w / 2 + 3
                if hanger.free( f, c - w / 2 - 30, c + w / 2 + 30, z - h / 2, z + h / 2 ):
                    hanger.work( f, c, z, key, h, style )
                    hanger.take( f, c - w / 2 - 10, c + w / 2 + 24, z - h / 2, z + h / 2 )
                    stats["works"] += 1
                    k += 1
                r += span + max( 30.0, 0.25 * w + 24 )


# ---------------------------------------------------------------------------------------------------------------------
# Ceilings and walls: services

def in_rects( e, n, rects, margin=0.0 ):
    return any( r[0] - margin <= e <= r[1] + margin and r[2] - margin <= n <= r[3] + margin for r in rects )


def spot_head( m, at, aim ):
    """ A track spot: a stem down from the track, a yoke, the can aimed along aim, its lens lit. """
    at = np.asarray( at, float )
    aim = unit( aim )
    P.rod( m, at, at - UP * 2.6, 0.32, "cbf_track", sides=6 )
    pivot = at - UP * 3.4
    m.box( pivot - ( 1.1, 1.1, 0.5 ), pivot + ( 1.1, 1.1, 0.8 ), "cbf_track" )
    back = pivot - aim * 2.2
    front = pivot + aim * 3.6
    P.rod( m, back, front, 1.7, "cbf_track", sides=10, caps=True )
    lens_disc( m, front + aim * 0.02, aim, 1.35 )


def lens_disc( m, centre, normal, r, sides=10, paint=LENS ):
    normal = unit( normal )
    ref = np.array( ( 0.0, 0.0, 1.0 ) ) if abs( normal[2] ) < 0.9 else np.array( ( 1.0, 0.0, 0.0 ) )
    u = unit( np.cross( normal, ref ) )
    v = np.cross( normal, u )
    pts = [ centre + ( u * math.cos( 2 * math.pi * k / sides ) + v * math.sin( 2 * math.pi * k / sides ) ) * r for k in range( sides ) ]
    m.polygon( paint, pts, normal=normal )


def ceiling_services( m, room, stats, seed ):
    """ Lighting tracks along the room's length with spot heads turned to the long walls, linear diffusers near them,
    smoke detectors down the middle and a camera's dome in a corner. """
    e0, e1, n0, n1 = room.e0, room.e1, room.n0, room.n1
    z = room.ceiling
    along_e = ( e1 - e0 ) >= ( n1 - n0 )
    length = ( e1 - e0 ) if along_e else ( n1 - n0 )
    width = ( n1 - n0 ) if along_e else ( e1 - e0 )
    a0, a1 = ( e0, e1 ) if along_e else ( n0, n1 )
    b0, b1 = ( n0, n1 ) if along_e else ( e0, e1 )
    count = max( 2, min( 4, int( round( width / 160 ) ) ) )
    inset = min( 78.0, width / ( count + 1 ) )
    offsets = list( np.linspace( b0 + inset, b1 - inset, count ) )

    def plan( a, b, h ):
        return np.array( ( a, b, h ) if along_e else ( b, a, h ) )

    blocked = room.holes + room.low
    for j, b in enumerate( offsets ):
        segs, here, step = [], None, 12.0
        for a in np.arange( a0 + 36, a1 - 36 + 0.1, step ):
            p = plan( a, b, z )
            ok = not in_rects( p[0], p[1], blocked, margin=24 )
            if ok and here is None:
                here = a
            if not ok and here is not None:
                segs.append( ( here, a - step ) )
                here = None
        if here is not None:
            segs.append( ( here, a1 - 36 ) )
        wall_side = -1 if b - b0 < b1 - b else 1
        for s0, s1 in segs:
            if s1 - s0 < 48:
                continue
            lo, hi = plan( s0, b - 0.8, z - 1.4 ), plan( s1, b + 0.8, z )
            m.box( np.minimum( lo, hi ), np.maximum( lo, hi ), "cbf_track" )
            stats["tracks"] += 1
            for k, a in enumerate( np.arange( s0 + 24, s1 - 12, 60.0 ) ):
                side = wall_side if j in ( 0, len( offsets ) - 1 ) else ( 1 if k % 2 else -1 )
                toward = np.array( ( 0.0, side, 0.0 ) if along_e else ( side, 0.0, 0.0 ) )
                aim = unit( toward * math.cos( math.radians( 38 ) ) - UP * math.sin( math.radians( 38 ) ) )
                spot_head( m, plan( a, b, z - 1.4 ), aim )
                stats["spots"] += 1
    # Linear diffusers along both long walls, and the smoke detectors down the middle.
    for b in ( b0 + 30, b1 - 30 ):
        for a in np.arange( a0 + 90, a1 - 90, 190.0 ):
            p = plan( a, b, z )
            if in_rects( p[0], p[1], blocked, margin=40 ):
                continue
            lo, hi = plan( a - 30, b - 1.8, z - 0.06 ), plan( a + 30, b + 1.8, z - 0.06 )
            m.polygon( "cbf_grille", [ ( lo[0], lo[1], z - 0.06 ), ( hi[0], lo[1], z - 0.06 ), ( hi[0], hi[1], z - 0.06 ), ( lo[0], hi[1], z - 0.06 ) ],
                       normal=( 0, 0, -1 ) )
            stats["diffusers"] += 1
    mid = ( b0 + b1 ) / 2 + ( 40 if count % 2 else 0 )
    for a in np.arange( a0 + 150, a1 - 100, 300.0 ):
        p = plan( a, mid, z )
        if in_rects( p[0], p[1], blocked, margin=30 ):
            continue
        m.cylinder( ( p[0], p[1] ), 2.6, z - 1.1, z, { "side": "cbf_plastic", "bottom": "cbf_plastic", "top": None }, sides=12 )
        lens_disc( m, np.array( ( p[0] + 1.2, p[1], z - 1.12 ) ), ( 0, 0, -1 ), 0.22, sides=6, paint="cbf_track" )
        stats["detectors"] += 1
    corner = plan( a0 + 14, b0 + 14, z )
    if not in_rects( corner[0], corner[1], blocked, margin=10 ):
        lathe( m, "cbf_screen", ( corner[0], corner[1], z - 4.6 ), [ ( 0.0, 0.0 ), ( 2.4, 0.6 ), ( 3.4, 2.4 ), ( 3.6, 3.6 ) ], sides=14, cap_top=False )
        m.cylinder( ( corner[0], corner[1] ), 4.2, z - 1.0, z, { "side": "cbf_plastic", "bottom": "cbf_plastic", "top": None }, sides=14 )
        stats["cameras"] += 1


def door_fittings( m, room, faces, layout, stats, outdoors ):
    """ Over each door out of the building an exit sign; beside each doorway the room's plate; an extinguisher and a
    return grille on the room's longest face. """
    plate = layout["signs"].get( room.plate )
    for f in faces:
        side, right, up = frame_axes( f.out )
        for a, b, z0, z1 in f.openings:
            if z0 > room.floor + 10 or z1 - z0 < 90 or not ( f.run[0] - 1 <= ( a + b ) / 2 <= f.run[1] + 1 ):
                continue
            mid = ( a + b ) / 2
            beyond = f.point( mid, room.floor + 60, -40.0 )
            if outdoors( beyond ):
                c = f.point( mid, z1 + 9.0, 1.0 )
                m.oriented_box( c, ( side, f.out, up ), ( 14.0, 2.0, 7.0 ), { "default": "cbf_track", "+y": None } )
                face_c = c + f.out * 1.01
                corners = [ face_c - right * 7.0 - up * 3.5, face_c + right * 7.0 - up * 3.5, face_c + right * 7.0 + up * 3.5,
                            face_c - right * 7.0 + up * 3.5 ]
                P.card( m, "cbf_exit", corners, f.out, uv=[ ( 0.0, 0.0 ), ( 1.0, 0.0 ), ( 1.0, 1.0 ), ( 0.0, 1.0 ) ] )
                stats["exits"] += 1
            if plate:
                # The room's plate beside the doorway, on its right as you face the wall from inside.
                r = b + 14.0 if np.dot( right, f.along() ) > 0 else a - 14.0
                if f.run[0] + 8 <= r <= f.run[1] - 8 and all( not ( oa - 8 < r < ob + 8 ) for oa, ob, oz0, oz1 in f.openings if oz0 < room.floor + 70 ):
                    sign_card( m, plate, f.point( r, room.floor + 64, 0.0 ), f.out, 12.0, 3.0, off=0.35, back=P.WHITE )
                    stats["plates"] += 1
    if faces:
        f = max( faces, key=lambda f: f.run[1] - f.run[0] )
        side, right, up = frame_axes( f.out )
        r = f.run[0] + 40
        for a, b, z0, z1 in f.openings:
            if a - 40 < r < b + 40:
                r = b + 46
        if r < f.run[1] - 30:
            base = f.point( r, room.floor + 44, 0.0 )
            m.oriented_box( base + f.out * 0.6, ( side, f.out, up ), ( 4.0, 1.2, 6.0 ), "cbf_track" )
            body = base + f.out * 4.4
            P.rod( m, body - UP * 8, body + UP * 8, 3.1, P.RED, sides=12, caps=True )
            P.rod( m, body + UP * 8, body + UP * 10.5, 1.1, P.BLACK, sides=8, caps=True )
            P.rod( m, body + UP * 9 + right * 1.0, body + right * 3.6 - UP * 4, 0.45, P.BLACK, sides=6 )
            stats["extinguishers"] += 1
        r2 = ( f.run[0] + f.run[1] ) / 2
        clear = all( not ( a - 30 < r2 < b + 30 ) for a, b, z0, z1 in f.openings if z0 < room.floor + 30 )
        if clear:
            c = f.point( r2, room.floor + 9.0, 0.05 )
            m.oriented_box( c, ( side, f.out, up ), ( 28.0, 0.25, 10.0 ), "cbf_grille" )
            for k in range( 6 ):
                m.oriented_box( c + up * ( -4 + 1.6 * k ) + f.out * 0.3, ( side, f.out, up ), ( 26.0, 0.4, 0.5 ), "cbf_hvac" )
            stats["grilles"] += 1


# ---------------------------------------------------------------------------------------------------------------------
# Furniture with collision

def clear_of( e, n, z, half, log, spots, extra=(), gap=60.0 ):
    """ Whether a footprint ( e, n ) +- half is clear of every spot, stair, plinth, gallery wall, column, table and other
    piece by gap. """
    x0, x1, y0, y1 = e - half[0], e + half[0], n - half[1], n + half[1]

    def near( ra ):
        return not ( x1 + gap < ra[0] or x0 - gap > ra[1] or y1 + gap < ra[2] or y0 - gap > ra[3] )

    for _, p in spots:
        if abs( p[2] - z ) < 60 and near( ( p[0] - 16, p[0] + 16, p[1] - 16, p[1] + 16 ) ):
            return False
    for f in log.flights:
        if f["axis"] == "n":
            r = ( min( f["a0"], f["a1"] ), max( f["a0"], f["a1"] ), min( f["r_top"], f["r_foot"] ) - 60, max( f["r_top"], f["r_foot"] ) + 60 )
        else:
            r = ( min( f["r_top"], f["r_foot"] ) - 60, max( f["r_top"], f["r_foot"] ) + 60, min( f["a0"], f["a1"] ), max( f["a0"], f["a1"] ) )
        if near( r ):
            return False
    for p in log.plinths:
        w = p["w"]
        if abs( z ) < 30 and near( ( p["e"] - w / 2, p["e"] + w / 2, p["n"] - w / 2, p["n"] + w / 2 ) ):
            return False
    for p in log.upstairs_plinths:
        if z > 100 and near( ( p["e"] - 13, p["e"] + 13, p["n"] - 13, p["n"] + 13 ) ):
            return False
    for g in log.gallery_walls:
        if abs( z ) < 30 and near( ( g["e0"], g["e1"], g["n0"], g["n1"] ) ):
            return False
    for g in log.upstairs_walls:
        if z > 100 and near( ( g["e0"], g["e1"], g["n0"], g["n1"] ) ):
            return False
    for c in log.columns:
        if c["z0"] <= z + 10 <= c["z1"] and near( ( c["e"] - c["r"], c["e"] + c["r"], c["n"] - c["r"], c["n"] + c["r"] ) ):
            return False
    for t in log.tables:
        if near( ( t["e"] - 30, t["e"] + 30, t["n"] - 30, t["n"] + 30 ) ):
            return False
    for r in extra:
        if near( r ):
            return False
    return True


def blocked( aabbs, at, half, height, z=0.0 ):
    """ Whether a footprint at ( e, n ) +- half, height tall, runs into the map's own collision (its floor aside). """
    lo = np.array( ( at[0] - half[0], at[1] - half[1], z + 1.0 ) )
    hi = np.array( ( at[0] + half[0], at[1] + half[1], z + height ) )
    return any( np.all( a[0] < hi ) and np.all( a[1] > lo ) for a in aabbs )


def gallery_bench( m, e, n, z, along_e, length=72.0 ):
    """ A gallery bench: a black leather pad on a brushed steel frame, as museums seat their rooms. """
    hl, hd = length / 2, 9.0
    lo, hi = ( e - hl, n - hd ), ( e + hl, n + hd )
    if not along_e:
        lo, hi = ( e - hd, n - hl ), ( e + hd, n + hl )
    m.box( ( lo[0] + 0.5, lo[1] + 0.5, z + 15.0 ), ( hi[0] - 0.5, hi[1] - 0.5, z + 18.0 ), { "default": "cbf_leather" } )
    for s in ( -1, 1 ):
        if along_e:
            a = e + s * ( hl - 5 )
            m.box( ( a - 1, lo[1] + 1.5, z ), ( a + 1, hi[1] - 1.5, z + 15.0 ), P.STEEL )
        else:
            a = n + s * ( hl - 5 )
            m.box( ( lo[0] + 1.5, a - 1, z ), ( hi[0] - 1.5, a + 1, z + 15.0 ), P.STEEL )
    m.collision_box( ( lo[0], lo[1], z ), ( hi[0], hi[1], z + 18.0 ), METAL )


def vitrine( m, e, n, z, along_e, seed ):
    """ A vitrine: a white base, a glass hood (drawn only: shots go through it), three pieces of pottery inside. """
    rng = np.random.default_rng( seed )
    hl, hd = ( 22.0, 13.0 ) if along_e else ( 13.0, 22.0 )
    m.box( ( e - hl, n - hd, z ), ( e + hl, n + hd, z + 34.0 ), { "default": P.WHITE, "-z": None } )
    m.box( ( e - hl + 1.5, n - hd + 1.5, z ), ( e + hl - 1.5, n + hd - 1.5, z + 3.0 ), { "default": P.BLACK, "-z": None, "+z": None } )
    m.collision_box( ( e - hl, n - hd, z ), ( e + hl, n + hd, z + 34.0 ), STONE )
    top = z + 34.0
    m.box( ( e - hl + 0.3, n - hd + 0.3, top ), ( e + hl - 0.3, n + hd - 0.3, top + 20.0 ), { "default": GLASS, "-z": None } )
    for k in range( 3 ):
        x = e + ( k - 1 ) * hl * 0.55 if along_e else e
        y = n if along_e else n + ( k - 1 ) * hd * 0.55
        h = rng.uniform( 5, 11 )
        r = rng.uniform( 2.2, 3.8 )
        profile = [ ( 0.0, 0.0 ), ( r * 0.55, 0.0 ), ( r, h * 0.35 ), ( r * 0.9, h * 0.6 ), ( r * 0.45, h * 0.85 ), ( r * 0.55, h ) ]
        lathe( m, "cbf_clay" if k != 1 else P.BRONZE, ( x, y, top + 0.05 ), profile, sides=14, cap_top=False )


def stanchions( m, points, z ):
    """ Queue posts (chrome, weighted bases) with black belts between them. """
    for p in points:
        m.cylinder( p, 6.0, z, z + 1.0, { "side": "cbf_chrome", "top": "cbf_chrome", "bottom": None }, sides=16 )
        P.rod( m, ( p[0], p[1], z + 1 ), ( p[0], p[1], z + 37.5 ), 1.1, "cbf_chrome", sides=10, caps=True )
        m.cylinder( p, 1.5, z + 37.5, z + 39.0, { "side": "cbf_track", "top": "cbf_track", "bottom": None }, sides=10 )
    for a, b in zip( points, points[1:] ):
        a3, b3 = np.array( ( a[0], a[1], z + 35.2 ) ), np.array( ( b[0], b[1], z + 35.2 ) )
        d = unit( b3 - a3 )
        m.beam( a3 + d * 1.2, b3 - d * 1.2, ( 0.12, 2.0 ), "cbf_belt" )


def totem( m, layout, centre, facing, front, back=None, z=0.0, collide=True ):
    """ A wayfinding totem: a slim bronze-framed panel 84 high, a sign each side. """
    out = unit( ( facing[0], facing[1], 0.0 ) )
    side, right, up = frame_axes( out )
    c = np.array( ( centre[0], centre[1], z ) )
    m.oriented_box( c + up * 42, ( side, out, up ), ( 26.0, 4.0, 84.0 ), "cbf_bronze" )
    m.oriented_box( c + up * 1, ( side, out, up ), ( 30.0, 10.0, 2.0 ), "cbf_bronze" )
    for o, key in ( ( out, front ), ( -out, back or front ) ):
        sign_card( m, layout["signs"][key], c + up * 70 + o * 2.0, o, 24.0, 4.5, off=0.02 )
        sign_card( m, layout["signs"]["plate_logo"], c + up * 30 + o * 2.0, o, 22.0, 9.6, off=0.02 )
    if collide:
        m.oriented_box( c + up * 42, ( side, out, up ), ( 26.0, 4.0, 84.0 ), {}, METAL )


# ---------------------------------------------------------------------------------------------------------------------
# The lobby and the cafe

def lobby( m, solid, layout, C, stats ):
    cx, cy = C.ROTUNDA
    # Two exhibition banners hung from the hall's ceiling ring on cables, either side of the desk.
    for k, a in ( ( 1, 30.0 ), ( 3, 150.0 ) ):
        p = ( cx + 300 * math.cos( math.radians( a ) ), cy + 300 * math.sin( math.radians( a ) ) )
        out = ( -math.cos( math.radians( a ) ), -math.sin( math.radians( a ) ) )
        P.banner( m, k, p, 300.0, out, width=56.0, height=170.0, off=0.0, hangers=36.0 )
    # The queue lane to the desk's open side, and the screens on it.
    lane = [ ( cx - 130 + 30 * k, cy - 92 ) for k in range( 4 ) ] + [ ( cx - 40, cy - 140 ) ]
    stanchions( m, lane, 0.0 )
    stanchions( m, [ ( cx - 130 + 30 * k, cy - 140 ) for k in range( 3 ) ], 0.0 )
    for a in ( 230.0, 300.0 ):
        p = np.array( ( cx + 60 * math.cos( math.radians( a ) ), cy + 60 * math.sin( math.radians( a ) ), 42.0 ) )
        out = unit( ( math.cos( math.radians( a ) ), math.sin( math.radians( a ) ), 0.0 ) )
        side, right, up = frame_axes( out )
        m.oriented_box( p + up * 0.6, ( side, out, up ), ( 7.0, 5.0, 1.2 ), "cbf_track" )
        P.rod( m, p + up * 1.2, p + up * 6.5, 0.6, "cbf_track", sides=6 )
        m.oriented_box( p + up * 12.5 + out * 0.6, ( side, out, up ), ( 19.0, 1.2, 12.0 ), { "default": "cbf_track", "-y": "cbf_screen" } )
    stats["lobby"] = 1


def cafe( m, layout, C, log, stats ):
    """ The counter's machines and case, the pendant lights over it, the menu board on the wall behind, cups on the
    tables. The counter is 540..700 along n 600..630, its top at 42. """
    top = 42.0
    # The espresso machine.
    e, n = 575.0, 615.0
    m.box( ( e - 13, n - 9, top ), ( e + 13, n + 9, top + 17 ), { "default": P.STEEL, "-z": None } )
    m.box( ( e - 13.4, n - 9.4, top + 17 ), ( e + 13.4, n + 9.4, top + 18.5 ), "cbf_track" )
    for k in range( 2 ):
        g = np.array( ( e - 6 + 12 * k, n - 9.6, top + 11 ) )
        P.rod( m, g, g - ( 0, 2.6, 0 ), 1.5, "cbf_chrome", sides=10, caps=True )
        P.rod( m, g - ( 0, 2.6, 0.5 ), g - ( 0, 6.5, 0.5 ), 0.5, P.BLACK, sides=6 )
    for k in range( 4 ):
        lathe( m, "cbf_plastic", ( e - 9 + 6 * k, n + 2, top + 18.5 ), [ ( 0.0, 0.0 ), ( 1.5, 0.0 ), ( 1.9, 3.0 ), ( 1.6, 3.2 ) ], sides=10, cap_top=False )
    # The grinder, the pastry case.
    lathe( m, P.BLACK, ( 600.0, 616.0, top ), [ ( 0.0, 0.0 ), ( 3.4, 0.0 ), ( 3.0, 9.0 ), ( 1.5, 10.0 ) ], sides=12 )
    lathe( m, "cbf_screen", ( 600.0, 616.0, top + 10.0 ), [ ( 1.5, 0.0 ), ( 3.6, 5.5 ), ( 3.8, 6.0 ) ], sides=12 )
    e0, e1 = 628.0, 682.0
    m.box( ( e0, 604, top ), ( e1, 626, top + 1.5 ), "cbf_track" )
    m.box( ( e0, 604, top + 1.5 ), ( e1, 626, top + 14 ), { "default": GLASS, "-z": None } )
    rng = np.random.default_rng( 5 )
    for k in range( 9 ):
        x = e0 + 6 + ( e1 - e0 - 12 ) * ( k % 5 ) / 4 + rng.uniform( -1.5, 1.5 )
        y = 609 + 8 * ( k // 5 ) + rng.uniform( -1, 1 )
        lathe( m, "cbf_pastry", ( x, y, top + 1.6 ), [ ( 0.0, 0.0 ), ( 2.4, 0.0 ), ( 2.6, 1.2 ), ( 1.6, 2.4 ), ( 0.0, 2.7 ) ], sides=10, cap_top=False )
    # Pendant lights over the counter.
    for e in ( 560.0, 620.0, 680.0 ):
        p = np.array( ( e, 615.0, C.CAFE_TOP ) )
        P.rod( m, p, p - UP * 44, 0.18, "cbf_track", sides=4 )
        lathe( m, "cbf_track", p - UP * 56, [ ( 6.5, 0.0 ), ( 5.8, 3.0 ), ( 2.4, 10.0 ), ( 0.6, 12.0 ) ], sides=16 )
        lens_disc( m, p - UP * 55.9, ( 0, 0, -1 ), 5.4, sides=16 )
    # The menu board, hung from the ceiling on two rods over the back of the counter, facing the customers.
    menu = layout["signs"]["menu"]
    sign_card( m, menu, ( 620.0, 650.0, 112.0 ), ( 0.0, -1.0 ), 58.0, 17.3, off=0.0, back="cbf_track", depth=1.2 )
    for e in ( 598.0, 642.0 ):
        P.rod( m, ( e, 650.6, 120.6 ), ( e, 650.6, C.CAFE_TOP ), 0.2, "cbf_track", sides=4 )
    # Cups and saucers on the tables.
    for t in log.tables:
        for k in range( 2 ):
            a = math.radians( 70 + 160 * k )
            p = ( t["e"] + 6 * math.cos( a ), t["n"] + 6 * math.sin( a ), 29.5 )
            m.cylinder( p[:2], 2.6, 29.5, 29.8, { "side": "cbf_plastic", "top": "cbf_plastic", "bottom": None }, sides=12 )
            lathe( m, "cbf_plastic", ( p[0], p[1], 29.8 ), [ ( 0.0, 0.0 ), ( 1.2, 0.0 ), ( 1.6, 2.4 ), ( 1.7, 2.6 ) ], sides=10, cap_top=False )
    stats["cafe"] = 1


# ---------------------------------------------------------------------------------------------------------------------
# Outside

def wall_light( m, centre, out ):
    """ A slim bronze wall light, washing up and down the wall. """
    side, right, up = frame_axes( out )
    o = unit( ( out[0], out[1], 0.0 ) )
    c = np.asarray( centre, float ) + o * 2.2
    m.oriented_box( c, ( side, o, up ), ( 4.4, 4.4, 13.0 ), "cbf_bronze" )
    for s in ( -1, 1 ):
        m.oriented_box( c + up * s * 6.6, ( side, o, up ), ( 3.0, 3.0, 0.3 ), LENS )


def camera( m, at, out ):
    """ A security camera on a wall bracket, looking out and down. """
    o = unit( ( out[0], out[1], 0.0 ) )
    side, right, up = frame_axes( o )
    at = np.asarray( at, float )
    m.oriented_box( at + o * 0.4, ( side, o, up ), ( 4.0, 0.8, 5.0 ), P.WHITE )
    P.rod( m, at + o * 0.8, at + o * 6.0, 0.7, P.WHITE, sides=6 )
    look = unit( o * 0.85 - up * 0.5 )
    body = at + o * 7.0 - up * 1.5
    P.rod( m, body - look * 4.5, body + look * 4.5, 2.0, P.WHITE, sides=8, caps=True )
    lens_disc( m, body + look * 4.52, look, 1.2, sides=8, paint="cbf_screen" )


def roof_plant( m, e0, e1, n0, n1, z, seed ):
    """ Air-handling units set back from the parapets, vents, a hatch: what a gallery's roof carries. """
    rng = np.random.default_rng( seed )
    count = 1 if ( e1 - e0 ) * ( n1 - n0 ) < 250000 else 2
    placed = []
    for k in range( count ):
        for attempt in range( 20 ):
            along_e = ( e1 - e0 ) > ( n1 - n0 )
            L, W = ( 120.0, 60.0 ) if along_e else ( 60.0, 120.0 )
            e = rng.uniform( e0 + 90 + L / 2, e1 - 90 - L / 2 )
            n = rng.uniform( n0 + 90 + W / 2, n1 - 90 - W / 2 )
            if all( abs( e - pe ) > ( L + 60 ) or abs( n - pn ) > ( W + 60 ) for pe, pn in placed ):
                break
        placed.append( ( e, n ) )
        h = 48.0
        m.box( ( e - L / 2, n - W / 2, z ), ( e + L / 2, n + W / 2, z + 4 ), "cbf_track" )
        m.box( ( e - L / 2 + 2, n - W / 2 + 2, z + 4 ), ( e + L / 2 - 2, n + W / 2 - 2, z + h ), { "default": "cbf_hvac", "-z": None } )
        # Louvres down its long sides, fans on top.
        for s in ( -1, 1 ):
            for j in range( 7 ):
                zz = z + 12 + 4.5 * j
                if along_e:
                    m.box( ( e - L / 4, n + s * ( W / 2 - 1.6 ) - 0.4, zz ), ( e + L / 4, n + s * ( W / 2 - 1.6 ) + 0.4, zz + 1.6 ), "cbf_grille" )
                else:
                    m.box( ( e + s * ( L / 2 - 1.6 ) - 0.4, n - W / 4, zz ), ( e + s * ( L / 2 - 1.6 ) + 0.4, n + W / 4, zz + 1.6 ), "cbf_grille" )
        for j in range( 2 ):
            fc = ( e + ( j - 0.5 ) * L * 0.45, n ) if along_e else ( e, n + ( j - 0.5 ) * W * 0.45 )
            m.cylinder( fc, 17.0, z + h, z + h + 3, { "side": "cbf_hvac", "top": None, "bottom": None }, sides=20 )
            P.disc( m, "cbf_grille", fc, 16.6, z + h + 2.0, sides=20 )
            for b in range( 5 ):
                a = 2 * math.pi * b / 5 + j
                P.rod( m, ( fc[0], fc[1], z + h + 2.2 ), ( fc[0] + 15 * math.cos( a ), fc[1] + 15 * math.sin( a ), z + h + 2.2 ), 0.4, "cbf_hvac", sides=4 )
        # A duct down into the roof.
        dx, dy = ( e - L / 2 - 14, n ) if along_e else ( e, n - W / 2 - 14 )
        m.box( ( dx - 9, dy - 9, z ), ( dx + 9, dy + 9, z + 30 ), { "default": "cbf_hvac", "-z": None } )
    for k in range( 3 ):
        e = rng.uniform( e0 + 60, e1 - 60 )
        n = rng.uniform( n0 + 60, n1 - 60 )
        if any( abs( e - pe ) < 110 and abs( n - pn ) < 110 for pe, pn in placed ):
            continue
        m.cylinder( ( e, n ), 3.0, z, z + 22, { "side": "cbf_pipe", "top": None, "bottom": None }, sides=10 )
        lathe( m, "cbf_pipe", ( e, n, z + 22 ), [ ( 6.0, 0.0 ), ( 6.0, 1.0 ), ( 0.0, 4.0 ) ], sides=10, cap_top=False )
    he, hn = e0 + 70, n0 + 70
    m.box( ( he - 18, hn - 18, z ), ( he + 18, hn + 18, z + 10 ), { "default": "cbf_hvac", "-z": None } )


def downpipe( m, e, n, z_top, out ):
    """ A scupper through the parapet and its square downpipe to the ground, bracketed every 60. """
    o = unit( ( out[0], out[1], 0.0 ) )
    side, right, up = frame_axes( o )
    top = np.array( ( e, n, z_top ) )
    m.oriented_box( top + o * 2.0 + up * 4, ( side, o, up ), ( 8.0, 4.0, 5.0 ), "cbf_pipe" )
    m.oriented_box( top + o * 3.5 - up * 6, ( side, o, up ), ( 9.0, 5.0, 14.0 ), "cbf_pipe" )
    m.oriented_box( np.array( ( e, n, ( z_top - 13 ) / 2 + 6 ) ) + o * 3.0, ( side, o, up ), ( 4.0, 3.0, z_top - 13 - 6 ), "cbf_pipe" )
    m.oriented_box( np.array( ( e, n, 3.0 ) ) + o * 5.0, ( side, o, up ), ( 4.0, 7.0, 3.0 ), "cbf_pipe" )
    for zz in np.arange( 60.0, z_top - 20, 60.0 ):
        m.oriented_box( np.array( ( e, n, zz ) ) + o * 2.0, ( side, o, up ), ( 6.0, 4.0, 1.0 ), "cbf_track" )


def flagpole( m, solid, e, n, k, height=360.0 ):
    """ A flagpole on a honed base with its gilt finial, flying one of the museum's shows as a vertical banner flag
    (cb_banner_k, the façade banners' art) from an outrigger arm at its top, in soft folds in the still air. The flag
    runs west of its pole, so the forecourt, north of it, reads it the right way round; from the south it's mirrored, as
    a printed flag is. (Plain coloured bands read as a country's flag: these are the museum's own.) """
    P.column( solid, e, n, 0.0, 6.0, 9.0, P.HONED, sides=16, surface=STONE )
    P.disc( solid, P.HONED, ( e, n ), 9.0, 6.0, sides=16 )        # P.column draws only its sides: the base's top
    P.column( m, e, n, 6.0, height, 2.2, "cbf_chrome", sides=12 )
    solid.collision_box( ( e - 3, n - 3, 6.0 ), ( e + 3, n + 3, 96.0 ), METAL )
    lathe( m, "cbf_gilt", ( e, n, height ), [ ( 0.0, 0.0 ), ( 2.6, 1.0 ), ( 2.8, 3.0 ), ( 0.0, 5.6 ) ], sides=12, cap_top=False )
    out = np.array( ( -1.0, 0.0, 0.0 ) )
    perp = np.cross( UP, out )
    flag_w, flag_h = 36.0, 108.0
    arm_z = height - 10.0
    # The outrigger: a slim bar out from a collar on the pole, its far end tipped with a cap.
    P.column( m, e, n, arm_z - 2.0, arm_z + 2.0, 2.9, "cbf_chrome", sides=12 )
    base = np.array( ( e, n, arm_z ) )
    P.rod( m, base, base + out * ( flag_w + 3.0 ), 0.75, "cbf_chrome", sides=8, caps=True )
    top = base + out * 2.6 - UP * 0.9
    cols, rows = 16, 16                                   # six columns to the finer fold's wave (8 gave it three)
    pts, uvs = {}, {}
    for i in range( cols + 1 ):
        for j in range( rows + 1 ):
            u, v = i / cols, j / rows
            # Held straight along the arm, the cloth falls in a few soft vertical folds that open towards its foot.
            fold = ( 1.4 * math.sin( u * math.pi * 2.5 + 0.9 * k ) + 0.5 * math.sin( u * math.pi * 5.3 + 2.1 * k ) ) * ( 0.15 + 0.85 * v ) * min( 1.0, u * 6.0 )
            gather = 1.0 - 0.05 * v                       # the foot draws in a little as the folds deepen
            pts[i, j] = top + out * ( u * flag_w * gather ) + perp * fold - UP * ( v * flag_h + 1.2 * math.sin( u * math.pi ) * v )
            uvs[i, j] = ( u, 1.0 - v )
    # Shaded smooth across the facets (flat, neighbouring ones turned up to 32 degrees apart: hard stripes, not soft
    # folds). Each side gets its own normals, towards the forecourt (+n) and away from it: both_sides keeps only a face's.
    normals = { ( i, j ): unit( np.cross( pts[min( i + 1, cols ), j] - pts[max( i - 1, 0 ), j],
                                          pts[i, max( j - 1, 0 )] - pts[i, min( j + 1, rows )] ) )
                for i in range( cols + 1 ) for j in range( rows + 1 ) }
    for i in range( cols ):
        for j in range( rows ):
            quad = [ ( i, j + 1 ), ( i + 1, j + 1 ), ( i + 1, j ), ( i, j ) ]
            back = quad[:1] + quad[:0:-1]
            m.polygon( f"cb_banner_{k % 4}", [ pts[q] for q in quad ], uv=[ uvs[q] for q in quad ], normals=[ normals[q] for q in quad ] )
            m.polygon( f"cb_banner_{k % 4}", [ pts[q] for q in back ], uv=[ uvs[q] for q in back ], normals=[ -normals[q] for q in back ] )


def exterior( fine, solid, layout, C, log, rooms_list, stats, spots, aabbs ):
    def indoors( p ):
        return any( r.contains( p[0], p[1], p[2] ) for r in rooms_list ) or \
               math.hypot( p[0] - C.ROTUNDA[0], p[1] - C.ROTUNDA[1] ) < C.ROT_IN

    # Wall lights either side of every outside door at ground level.
    for record in log.walls:
        for f in faces_of( record ):
            side, right, up = frame_axes( f.out )
            for a, b, z0, z1 in f.openings:
                if z0 > 10 or z1 - z0 < 90:
                    continue
                mid = ( a + b ) / 2
                if indoors( f.point( mid, 60, 30.0 ) ) or not indoors( f.point( mid, 60, -30.0 ) ):
                    continue
                for r in ( a - 16, b + 16 ):
                    if f.run[0] + 6 < r < f.run[1] - 6:
                        wall_light( fine, f.point( r, 100.0, 0.0 ), f.out )
                        stats["wall_lights"] += 1
    # The rotunda's main doors (north, onto the forecourt): the opening hours either side.
    cx, cy = C.ROTUNDA
    for s in ( -1, 1 ):
        p = np.array( ( cx + s * 80.0, cy + C.ROT_OUT + 0.2, 60.0 ) )
        a = math.atan2( p[1] - cy, p[0] - cx )
        p = np.array( ( cx + ( C.ROT_OUT + 0.3 ) * math.cos( a ), cy + ( C.ROT_OUT + 0.3 ) * math.sin( a ), 60.0 ) )
        sign_card( fine, layout["signs"]["plate_hours" if s < 0 else "plate_rules"], p, ( math.cos( a ), math.sin( a ) ), 22.0, 9.6,
                   off=0.25, back="cbf_bronze", depth=0.4 )
    # Wayfinding totems against the buildings' walls, where the courtyard's routes meet, clear of the lanes.
    for at, facing, front, back in ( ( ( 466.0, 120.0 ), ( -1, 0 ), "way_cafe", "way_salas" ),
                                     ( ( 430.0, -988.0 ), ( 0, 1 ), "way_este", "way_norte" ),
                                     ( ( -760.0, -172.0 ), ( 0, -1 ), "way_oeste", "way_sur" ) ):
        half = ( 15.0, 5.0 ) if facing[0] == 0 else ( 5.0, 15.0 )
        if not clear_of( at[0], at[1], 0.0, half, log, spots, extra=(), gap=30.0 ) or blocked( aabbs, at, half, 84.0 ):
            print( f"  totem at {at} left out: not clear" )
            continue
        totem( fine, layout, at, facing, front, back, collide=False )
        solid.collision_box( ( at[0] - half[0], at[1] - half[1], 0 ), ( at[0] + half[0], at[1] + half[1], 84 ), METAL )
        stats["totems"] += 1
    # Cameras high on the buildings' corners.
    for at, out in ( ( ( -1126.0, -160.0, 200.0 ), ( -1, -1 ) ), ( ( 2060.0, 715.0, 200.0 ), ( 1, 1 ) ), ( ( 480.0, -1000.0, 200.0 ), ( 1, -1 ) ),
                     ( ( -1030.0, -2150.0, 190.0 ), ( -1, -1 ) ), ( ( 1400.0, -1000.0, 200.0 ), ( 1, -1 ) ), ( ( -1126.0, 1510.0, 200.0 ), ( -1, 1 ) ) ):
        camera( fine, at, out )
        stats["cameras_out"] += 1
    # The roofs' plant.
    for k, ( e0, e1, n0, n1, z ) in enumerate( ( ( -1108, -668, -142, 1492, C.ROOF ), ( -668, -218, 1068, 1492, C.ROOF ),
                                                 ( 1018, 2042, 0, 697, C.ROOF ), ( 498, 1382, -982, -18, C.ROOF ),
                                                 ( -1012, 462, -2132, -1018, C.SG_ROOF ) ) ):
        roof_plant( fine, e0, e1, n0, n1, z, 40 + k )
        stats["roofs"] += 1
    # Downpipes on the galleries' outer corners.
    for e, n, z, out in ( ( -1129.0, 60.0, C.ROOF, ( -1, 0 ) ), ( -1129.0, 1300.0, C.ROOF, ( -1, 0 ) ), ( 2063.0, 100.0, C.ROOF, ( 1, 0 ) ),
                          ( 2063.0, 600.0, C.ROOF, ( 1, 0 ) ), ( 1403.0, -900.0, C.ROOF, ( 1, 0 ) ), ( -1033.0, -1900.0, C.SG_ROOF, ( -1, 0 ) ),
                          ( 483.0, -1100.0, C.SG_ROOF, ( 1, 0 ) ) ):
        downpipe( fine, e, n, z, out )
        stats["downpipes"] += 1
    # Bike hoops on the forecourt by the car park, and the three flags.
    for k in range( 6 ):
        e, n = 880.0 + 32 * k, 1640.0
        pts = [ ( e, n, 0.0 ) ] + [ ( e, n + 9 - 9 * math.cos( math.pi * j / 8 ), 26 + 9 * math.sin( math.pi * j / 8 ) ) for j in range( 9 ) ] + \
              [ ( e, n + 18, 0.0 ) ]
        for a, b in zip( pts, pts[1:] ):
            P.rod( fine, a, b, 1.0, P.STEEL, sides=6 )
    for k, e in enumerate( ( 420.0, 500.0, 580.0 ) ):
        flagpole( fine, solid, e, 2330.0, k )
    stats["flags"] = 3


# ---------------------------------------------------------------------------------------------------------------------
# More outside: the galleries' names, blinds, the rotunda's mobile, agaves in pots, pole lights

def lettering( m, layout, key, centre, z0, width, outward ):
    """ A gallery's name in grey letters (cbf_letters, alpha tested, 8:1) standing 1 off a wall. """
    out = unit( ( outward[0], outward[1], 0.0 ) )
    side, right, up = frame_axes( out )
    c = np.array( ( centre[0], centre[1], z0 ) ) + out * 1.0
    h = width / 8
    u0, v0, u1, v1 = layout["letters"][key]
    corners = [ c - right * width / 2, c + right * width / 2, c + right * width / 2 + up * h, c - right * width / 2 + up * h ]
    P.card( m, "cbf_letters", corners, out, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )


def blinds( m, log, stats ):
    """ Roller blinds behind some of the upper windows, part way down: the panes no longer all read as the same dark
    glass from outside. """
    for record in log.walls:
        if not record["outward"]:
            continue
        axis, across = record["axis"], record["across"]
        d = sum( across ) / 2
        sign = 1 if record["outward"][0] == "+" else -1
        inner = d - sign * 3.0
        for c, w, z0, z1 in record["windows"]:
            if z0 < 196 or not P.chance( 0.5, "blind", axis, c, z0 ):
                continue
            share = 0.25 + 0.5 * ( P.keyed( "blind-share", c, z0 ) % 1000 ) / 1000
            bottom = z1 - ( z1 - z0 ) * share
            lo = ( c - w / 2 + 1.5, inner - 0.15, bottom ) if axis == "e" else ( inner - 0.15, c - w / 2 + 1.5, bottom )
            hi = ( c + w / 2 - 1.5, inner + 0.15, z1 - 1 ) if axis == "e" else ( inner + 0.15, c + w / 2 - 1.5, z1 - 1 )
            m.box( lo, hi, "cbf_blind" )
            lo2 = ( lo[0], lo[1] - 0.3, bottom - 1.2 ) if axis == "e" else ( lo[0] - 0.3, lo[1], bottom - 1.2 )
            hi2 = ( hi[0], hi[1] + 0.3, bottom ) if axis == "e" else ( hi[0] + 0.3, hi[1], bottom )
            m.box( lo2, hi2, "cbf_track" )
            stats["blinds"] = stats.get( "blinds", 0 ) + 1


def mobile( m, C ):
    """ A hanging mobile in the rotunda's clerestory, after the mid-century ones: steel wires and arms, flat discs in red,
    black and yellow, balanced, high over the hall. """
    cx, cy = C.ROTUNDA
    top = C.ROT_UP_TOP - 18
    rng = np.random.default_rng( 9 )

    def arm( at, length, turn, depth ):
        a = np.array( ( math.cos( turn ), math.sin( turn ), 0.0 ) )
        left, right = at - a * length * 0.35, at + a * length * 0.65
        P.rod( m, left, right, 0.35, "cbf_mobile_black", sides=5 )
        # The heavy end: a disc; the light end: another arm or a disc.
        for end, weight in ( ( left, 1 ), ( right, 0 ) ):
            drop = end - UP * rng.uniform( 10, 22 )
            P.rod( m, end, drop, 0.12, "cbf_track", sides=4 )
            if depth > 0 and weight == 0:
                arm( drop, length * 0.72, turn + rng.uniform( 1.2, 2.2 ), depth - 1 )
            else:
                r = rng.uniform( 9, 22 )
                n = unit( ( math.cos( turn + 1.3 ), math.sin( turn + 1.3 ), rng.uniform( -0.15, 0.15 ) ) )
                paint = ( "cbf_mobile_red", "cbf_mobile_black", "cbf_mobile_yellow" )[int( rng.integers( 3 ) )]
                centre = drop - UP * r
                ref = np.array( ( 0.0, 0.0, 1.0 ) )
                u = unit( np.cross( n, ref ) )
                v = np.cross( n, u )
                pts = [ centre + ( u * math.cos( 2 * math.pi * k / 18 ) * 1.0 + v * math.sin( 2 * math.pi * k / 18 ) * 0.82 ) * r for k in range( 18 ) ]
                m.polygon( paint, pts, normal=n, both_sides=True )

    anchor = np.array( ( cx, cy, top ) )
    P.rod( m, anchor, anchor - UP * 24, 0.15, "cbf_track", sides=4 )
    arm( anchor - UP * 24, 150.0, 0.4, 3 )


def potted_agave( m, solid, e, n, z, seed, size=1.0 ):
    """ An agave in a tall terracotta pot: a rosette of thick pointed blue-green leaves. """
    rng = np.random.default_rng( seed )
    r = 15.0 * size
    lathe( m, "cbf_terracotta", ( e, n, z ), [ ( 0.0, 0.0 ), ( r * 0.75, 0.0 ), ( r, 22 * size ), ( r * 1.06, 24 * size ), ( r * 0.98, 25 * size ) ], sides=18 )
    P.disc( m, "soil", ( e, n ), r * 0.95, z + 23 * size, sides=18 )
    solid.hull( [ ( e + r * math.cos( 2 * math.pi * k / 8 ), n + r * math.sin( 2 * math.pi * k / 8 ), zz ) for zz in ( z, z + 25 * size ) for k in range( 8 ) ], STONE )
    base = np.array( ( e, n, z + 23 * size ) )
    for k in range( 16 ):
        a = 2 * math.pi * k / 16 + rng.uniform( -0.12, 0.12 )
        rise = math.radians( 25 + 55 * ( k % 3 ) / 2 + rng.uniform( -6, 6 ) )
        L = size * rng.uniform( 26, 38 ) * ( 0.7 if k % 3 == 2 else 1.0 )
        d = np.array( ( math.cos( a ) * math.cos( rise ), math.sin( a ) * math.cos( rise ), math.sin( rise ) ) )
        side = unit( np.cross( d, UP ) )
        w = 3.2 * size
        root = base + d * 2
        mid = base + d * L * 0.45 + side * 0 + UP * L * 0.04
        tip = base + d * L - UP * L * 0.08 * ( 1 - math.sin( rise ) )
        n_up = unit( np.cross( side, d ) )
        for s_ in ( -1, 1 ):
            m.polygon( "cbf_agave", [ root + side * w * s_ * 0.6, mid + side * w * s_, mid + n_up * w * 0.5 ], normal=n_up + side * s_ * 0.3 )
            m.polygon( "cbf_agave", [ mid + side * w * s_, tip, mid + n_up * w * 0.5 ], normal=n_up + side * s_ * 0.3 )
            m.polygon( "cbf_agave", [ root + side * w * s_ * 0.6, mid + side * w * s_, tip ], normal=-n_up )


def pole_light( m, solid, e, n, height=150.0 ):
    """ A slim pole light: a bronze square pole, its head a flat box with a lens underneath. """
    m.box( ( e - 2, n - 2, 0 ), ( e + 2, n + 2, height ), "cbf_bronze" )
    m.box( ( e - 9, n - 3, height ), ( e + 3, n + 3, height + 3 ), "cbf_bronze" )
    m.polygon( LENS, [ ( e - 8.5, n + 2.5, height - 0.02 ), ( e + 2.5, n + 2.5, height - 0.02 ), ( e + 2.5, n - 2.5, height - 0.02 ),
                       ( e - 8.5, n - 2.5, height - 0.02 ) ], normal=( 0, 0, -1 ) )
    solid.collision_box( ( e - 2, n - 2, 0 ), ( e + 2, n + 2, height ), METAL )


def outside_more( fine, solid, layout, C, log, stats, spots, aabbs ):
    lettering( fine, layout, "oeste", ( -800.0, -160.0 ), 168.0, 220.0, ( 0, -1 ) )
    lettering( fine, layout, "norte", ( 1300.0, 715.0 ), 145.0, 220.0, ( 0, 1 ) )
    lettering( fine, layout, "este", ( 640.0, -1000.0 ), 145.0, 200.0, ( 0, -1 ) )
    blinds( fine, log, stats )
    mobile( fine, C )
    cx, cy = C.ROTUNDA
    for k, ( e, n ) in enumerate( ( ( cx - 112.0, cy + C.ROT_OUT + 32 ), ( cx + 112.0, cy + C.ROT_OUT + 32 ),
                                    ( 1180.0, 745.0 ), ( 1420.0, 745.0 ), ( 1960.0, 760.0 ), ( -205.0, -2178.0 ), ( 5.0, -2178.0 ) ) ):
        half = ( 18.0, 18.0 )
        if not clear_of( e, n, 0.0, half, log, spots, gap=24.0 ) or blocked( aabbs, ( e, n ), half, 30.0 ):
            print( f"  agave at {( e, n )} left out: not clear" )
            continue
        potted_agave( fine, solid, e, n, 0.0, 700 + k, size=1.0 + 0.15 * ( k % 2 ) )
        stats["agaves"] = stats.get( "agaves", 0 ) + 1
    for e in ( 700.0, 1060.0, 1420.0, 1780.0, 2140.0 ):
        n = 1088.0
        if not clear_of( e, n, 0.0, ( 3.0, 3.0 ), log, spots, gap=24.0 ) or blocked( aabbs, ( e, n ), ( 3.0, 3.0 ), 150.0 ):
            print( f"  pole light at {( e, n )} left out: not clear" )
            continue
        pole_light( fine, solid, e, n )
        stats["poles"] = stats.get( "poles", 0 ) + 1


# ---------------------------------------------------------------------------------------------------------------------
# Building it

def load_layout():
    return json.loads( LAYOUT_FILE.read_text( encoding="utf-8" ) )


def build( log, C, spots, base_models ):
    layout = load_layout()
    fine, solid = Model(), Model()
    stats = { k: 0 for k in ( "works", "walltexts", "tracks", "spots", "diffusers", "detectors", "cameras", "exits", "plates",
                              "extinguishers", "grilles", "benches", "vitrines", "wall_lights", "totems", "cameras_out", "roofs",
                              "downpipes" ) }
    all_rooms = rooms( C )
    hanger = Hanger( layout, fine )
    import railhead_map as R
    aabbs = R.collision_aabbs( base_models )

    def outdoors( p ):
        if math.hypot( p[0] - C.ROTUNDA[0], p[1] - C.ROTUNDA[1] ) < C.ROT_IN:
            return False
        return not any( r.contains( p[0], p[1], p[2] ) for r in all_rooms )

    hanging = log.walls + display_walls( log, C )
    for k, room in enumerate( all_rooms ):
        hang_room( hanger, room, log, hanging, stats )
        ceiling_services( fine, room, stats, k )
        door_fittings( fine, room, room_faces( room, log.walls ), layout, stats, outdoors )
    # Benches down the middle of the bigger rooms, vitrines along the upper floors' walls.
    placed = []
    for k, room in enumerate( all_rooms ):
        if room.key in ( "cafe", "glass_room" ):
            continue
        along_e = ( room.e1 - room.e0 ) >= ( room.n1 - room.n0 )
        length = max( room.e1 - room.e0, room.n1 - room.n0 )
        candidates = []
        for t in ( 0.3, 0.5, 0.7 ):
            e = room.e0 + ( room.e1 - room.e0 ) * ( t if along_e else 0.5 )
            n = room.n0 + ( room.n1 - room.n0 ) * ( 0.5 if along_e else t )
            candidates.append( ( e, n ) )
        count = 0
        for e, n in candidates:
            half = ( 36.0, 9.0 ) if along_e else ( 9.0, 36.0 )
            if length < 400 or count >= ( 2 if length > 900 else 1 ):
                break
            if clear_of( e, n, room.floor, half, log, spots, extra=placed, gap=70.0 ) and not blocked( aabbs, ( e, n ), ( half[0] + 30, half[1] + 30 ), 72.0, room.floor ):
                gallery_bench( solid, e, n, room.floor, along_e )
                placed.append( ( e - half[0], e + half[0], n - half[1], n + half[1] ) )
                stats["benches"] += 1
                count += 1
        if room.floor > 100 and room.key in ( "sala_2", "sala_4", "sala_6" ):
            # Vitrines 30 off the room's long walls.
            for t in ( 0.25, 0.75 ):
                for wall_off in ( 34.0, -34.0 ):
                    if along_e:
                        e = room.e0 + ( room.e1 - room.e0 ) * t
                        n = ( room.n0 + wall_off ) if wall_off > 0 else ( room.n1 + wall_off )
                    else:
                        n = room.n0 + ( room.n1 - room.n0 ) * t
                        e = ( room.e0 + wall_off ) if wall_off > 0 else ( room.e1 + wall_off )
                    half = ( 22.0, 13.0 ) if along_e else ( 13.0, 22.0 )
                    if clear_of( e, n, room.floor, half, log, spots, extra=placed, gap=56.0 ) and not blocked( aabbs, ( e, n ), ( half[0] + 12, half[1] + 12 ), 60.0, room.floor ):
                        vitrine( solid, e, n, room.floor, along_e, 100 + len( placed ) )
                        placed.append( ( e - half[0], e + half[0], n - half[1], n + half[1] ) )
                        stats["vitrines"] += 1
                        break
    lobby( fine, solid, layout, C, stats )
    cafe( fine, layout, C, log, stats )
    exterior( fine, solid, layout, C, log, all_rooms, stats, spots, aabbs )
    outside_more( fine, solid, layout, C, log, stats, spots, aabbs )
    for model in ( fine, solid ):
        for paint in list( model.polygons ):
            if paint.startswith( "cbf_" ):
                if paint in DRAWN:
                    model.material_overrides[paint] = f"{RESOURCE}/{DRAWN[paint]}.vmat"
                else:
                    model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
                model.tile_overrides[paint] = 64.0
    stats["art_lights"] = len( hanger.lights )
    fine.spot_lights = hanger.lights
    print( "fit-out: " + ", ".join( f"{v} {k}" for k, v in stats.items() if v ) )
    return { "cerroblanco_fitout": solid, "cerroblanco_fitout_fine": fine }


def point_quality( model ):
    """ After cerroblanco_map.configure: the museum's own paints at their quality-v1 materials, as the detail models'. """
    for paint in model.polygons:
        if paint in QUALITY_PAINTS:
            model.material_overrides[paint] = f"{QUALITY}/{paint}.vmat"


def write_materials( out_assets=K.ASSETS ):
    """ The fit-out's flat paints and its lit lens, as text vmats, beside cerroblanco_art's sheets. """
    import railhead_materials as RM
    out = out_assets / RESOURCE
    out.mkdir( parents=True, exist_ok=True )
    for name, ( colour, metal, rough ) in FLAT.items():
        text = RM.painted_vmat( name, colour, metal, rough ).replace( "Tools/railhead_materials.py", "Tools/cerroblanco_fitout.py" )
        K.write_text( out / f"{name}.vmat", text )
    K.write_text( out / f"{LENS}.vmat", "\n".join( [
        "// Tools/cerroblanco_fitout.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"', '    F_SELF_ILLUM "1"',
        '    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"', '    g_flSelfIllumBrightness "3.5"',
        '    g_flSelfIllumAlbedoFactor "1.0"', '    g_vSelfIllumTint "[1.000000 0.920000 0.780000 0.000000]"',
        '    g_flRoughnessScaleFactor "1"', '    g_flMetalness "0"', '    TextureColor "materials/default/default_color.tga"',
        '    TextureNormal "materials/default/default_normal.tga"', '    TextureRoughness "[0.350000 0.350000 0.350000 0.000000]"',
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"', '    g_vColorTint "[1.000000 0.960000 0.880000 1.000000]"',
        '    g_flModelTintAmount "1.0"', "}" ] ) + "\n" )
