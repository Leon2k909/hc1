"""
Stillhouse's backdrop: Camas Ròin, a made-up village round a whisky distillery on a Hebridean sea loch, at 15:00 on
3 October. It's everything outside the play area (e -2200..2200, n -1980..1900): the terraces that close its east and
west sides, the shore's rocky points, the hill behind, the villages along the shore road, the seabed, the sea, and
across the loch the far shore, the mountains, the islet with its tower house and the lighthouse.

    python Tools/stillhouse_backdrop.py                                (builds and reports the models, checks the edges)
    python Tools/stillhouse_backdrop.py --preview <dir> [view ...]     (with a greybox of the distillery's footprints)

stillhouse_map imports it; this script writes no models or assets itself. Plan inches as map_kit (e east, n north,
z up); 1 m = 39.37. It needs numpy and scipy (cKDTree, for the nearest points on the coast and the paths). numba
compiles the ground's cutter if it's there (without it the cutter runs in Python, a lot slower) and the previews'
rasteriser. models() takes about 10 s.

- edge_blocks( side ): the play edge, the only model here with collision. A terrace of harled 1.5-storey cottages up
  each brae, fronts on e = side x 2150 from the seawall (n -1350) to the brae's dyke (n 1600) and a byre on to n 1960,
  backs at side x 2500, each cottage stepping with brae_z. Below the terrace the bay's rocky point (e side x 2150..2900,
  n -1350..-2050) ends the beach. side 1 is the east terrace, -1 the west; each is built in place in its own colours,
  never mirrored.
- land(): drawn only. One ground mesh, a balanced quadtree with 48-inch cells by the play area, the shore, the roads
  and the buildings and coarser with the distance, from the shore to the loch's heads and LAND_CUT inland, with holes
  where the play area's own models are. Its paints are fields over it (sh_field, sh_grass, sh_hill_grass, sh_bracken,
  sh_heather, sh_moor, sh_hill_rock, sh_conifer, and on the shore sh_shingle, sh_sand_wet, sh_wrack, sh_rock and
  sh_rock_weed), and its triangles are cut where the fields cross 0, so the paints meet along smooth lines. On it: the
  crofts' long strips up the hill, each inside drystone dykes, under the head dyke; the shore road through both
  villages and round the back of the distillery, the single-track hill road past the farm, the farm's track and the
  lighthouse's, as ribbons; the bridge over the burn, the telegraph poles up the hill road, the lochan's dam; a spruce
  plantation, peat banks, rocks on the hill and the shore, sycamores in the gardens (cloud tree props); and the
  villages along the shore road, east and west, with the inn, the kirk in its graveyard and the farm up the hill.
- seabed(): drawn only. The loch's bed from under the beach (n -1760, z -190) down to -300 at the pier head, -500 by
  n -3000 and about -1500 out in the loch, on under the far shore's skirt; sh_seabed while the water over it is under
  ~60 deep (SHORE_DEPTH, its line wandering), then sh_seabed_deep.
- sea(): sh_sea at SEA_Z, the loch in quads from ~2000 across by the beach to 33000 far out, inside a 64-sided polygon
  of REACH; and up the hill the lochan, the water over the dam's spillway and the burn, in the same paint.
- far(): drawn only. A polar mesh from 22000 out to 95000 over the far side of the loch (650 m across) and past its
  heads, in forced perspective: real size inside 32000, and further out each point is drawn for one further off (3 km
  at 42000, 28 km at 95000) at the size it would look from there. The far shore's low hills rise from its waterline and
  the mountains stand behind them, in sh_hill_grass, sh_heather, sh_bracken and sh_hill_rock near and sh_far_hills
  past ~44000; past the loch's heads this shore's hills run on beside a strath, the far mesh meeting the land's exactly
  along far_side 0. With it: the islet 600 m out to the south-east and its ruined tower house; the lighthouse on the
  west headland, its yard and the keepers' cottages; the far shore's two townships, eleven crofthouses (most with a
  byre) at their real size. The long low island out in the loch's mouth is drawn only if a player could see it
  (far_island_seen), and none can.
- models(): the five as { name: Model } (the east edge only: the lead builds edge_blocks( -1 ) itself), configured.

Real figures used:
- A Hebridean cottage (the 19th-century fishing and distillery villages of the southern isles): walls 0.6-0.7 m thick
  in rubble, harled and limewashed, with black-painted margins round the windows and doors and a black base course;
  1.5 storeys, eaves ~3.1 m over the floor, rooms in the roof lit by wallhead dormers or roof lights; slate roofs
  45-50 degrees (47 here: steeper than the mantle's and the navmesh's limits); a stack on each gable with two to four
  clay cans; sash windows ~0.8 x 1.3 m, six panes over six; frontages 7-11 m, depth ~6.6 m with a rear outshot.
- The tide: springs rise and fall ~3.5 m on this coast, so the wrack and barnacle zone reaches ~2 m over the water at
  mid tide (SEA_Z + 70).
- Hills: the in-bye land rises gently from the raised beach; the moor behind tops out at 125-175 m about a kilometre
  inland, with the next ridge behind. Across the loch the far shore rises ~30 m from the water, and behind it the hills
  and mountains climb in perspective: tops of 120 m 4 km off, 500 m 10 km off and 800 m 15 km off (1.8-3 degrees up).
- A tower house: 10 x 8 m, ~15 m to the wallhead, roofless.
- A small lighthouse: a 12 m tower with its lantern and gallery, single-storey keepers' cottages beside it.
- A crofthouse: 10 x 5.6 m, slated, with a stack on each gable; its byre 7.6 x 4.6 m.
- Telegraph poles 7.6 m tall, 50-58 m apart. Sitka spruce in a plantation ~14 m tall. Drystone dykes 1.2 m high.
"""
import math
import sys
import time
import zlib
from pathlib import Path

import numpy as np

import map_kit as K

# Facepunch's cloud foliage: heights 391.9 and 703.7 at scale 1, the bush 75.
OAK = "models/sbox_props/trees/oak/tree_oak_small_a.vmdl"
OAK_BIG = "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl"
BUSH = "models/sbox_props/shrubs/beech/beech_bush_small.vmdl"

STONE = "default"           # rock and rubble: masonry for the bullets and the sounds

# Levels (DESIGN.md)
SEA_Z = -195.0
ROAD, YARD, WALK = 48.0, 0.0, -50.0
BEACH_N0, BEACH_N1 = -1760.0, -1350.0           # the beach: z -190 at its foot, -150 at the seawall
BEACH_FOOT, BEACH_TOP = -190.0, -150.0
SHORE_N = -1800.0                               # the water's edge on the beach

# The play area and the edges
PLAY_E, PLAY_N0, PLAY_N1 = 2200.0, -1980.0, 1900.0
FRONT, BACK = 2150.0, 2500.0                    # the terraces' fronts and backs ( x side )
TERRACE_N0, TERRACE_N1 = -1350.0, 1600.0        # from the seawall's parapet to the brae's dyke
TERRACE_END = 1960.0                            # the byre carries the edge on past the play area's north side
ROCK_E1, ROCK_N0, ROCK_N1 = 2900.0, -2050.0, -1350.0
LAND_N = 1850.0                                 # the land model starts north of this
REACH = 95000.0                                 # the sea's and the land's extent (the camera's far clip is 100000)

# Cottage figures
PITCH = 47.0                # slate roofs: over 45.6 degrees a slope isn't something to stand on
MAIN = 260.0                # the main block's depth, front to back
WALL = 18.0                 # the depth of the window reveals
STEP = 6.0                  # the door sill over the ground at the door
EAVES = 122.0               # floor to eaves
PLINTH = 12.0               # the black base course's top over the floor
WEED_Z = SEA_Z + 70.0       # the top of the wrack on the shore rocks

# Paint tiles, as DESIGN.md gives them: used until stillhouse_materials says otherwise
TILES = {
    "sh_harl": 256, "sh_harl_shade": 256, "sh_harl_cream": 256, "sh_harl_mould": 256, "sh_whitewash": 192,
    "sh_tar_black": 128, "sh_rubble": 192, "sh_granite": 160, "sh_granite_weed": 160,
    "sh_slate_roof": 128, "sh_lead": 96, "sh_corrugated_red": 64, "sh_corrugated_green": 64,
    "sh_setts": 96, "sh_tarmac": 256, "sh_concrete": 192, "sh_floor_tiles": 64, "sh_floorboards": 128,
    "sh_dunnage": 192, "sh_grating": 48, "sh_chequer": 48, "sh_shingle": 128, "sh_sand": 192, "sh_sand_wet": 192,
    "sh_wrack": 128, "sh_grass": 192, "sh_seabed": 256, "sh_seabed_deep": 512, "sh_kerb": 64, "sh_rock": 256,
    "sh_rock_weed": 256,
    "sh_copper_bright": 64, "sh_copper": 96, "sh_copper_green": 96, "sh_brass": 48, "sh_steel": 96,
    "sh_steel_green": 96, "sh_rust": 96, "sh_stainless": 128,
    "sh_pine": 128, "sh_cask_oak": 64, "sh_cask_dark": 64, "sh_hoop": 32, "sh_timber_tar": 128, "sh_planks_grey": 128,
    "sh_deck": 128,
    "sh_paint_door": 64, "sh_paint_white": 64, "sh_paint_black": 64, "sh_paint_red": 64, "sh_paint_yellow": 64,
    "sh_paint_orange": 64, "sh_paint_blue": 64,
    "sh_hull_blue": 128, "sh_hull_red": 128, "sh_hull_white": 128, "sh_hull_black": 128,
    "sh_peat": 48, "sh_malt": 64, "sh_sack": 64, "sh_rope": 16, "sh_net": 64, "sh_fishbox_blue": 32,
    "sh_fishbox_orange": 32, "sh_rubber": 64, "sh_tile_white": 48, "sh_window_dark": 64, "sh_canvas": 64,
    "sh_lamp_warm": 64, "sh_fire": 64, "sh_glass": 64, "sh_glass_dirty": 64,
    "sh_sea": 768,
    "sh_lettering": 64, "sh_signs": 64, "sh_cask_head": 64,
    "sh_hill_grass": 512, "sh_heather": 512, "sh_bracken": 512, "sh_moor": 512, "sh_hill_rock": 512, "sh_field": 512,
    "sh_conifer": 512, "sh_far_hills": 2048,
}
GRAIN = { "sh_floorboards", "sh_pine", "sh_cask_oak", "sh_cask_dark", "sh_timber_tar", "sh_planks_grey", "sh_deck",
          "sh_rope" }


# ---------------------------------------------------------------------------------------------------------------------
# Dice: every choice is a hash of a key, so a run always builds the same village

def unit( *key ):
    return ( zlib.crc32( "/".join( str( k ) for k in key ).encode() ) & 0xffffffff ) / 4294967296.0


def between( lo, hi, *key ):
    return lo + ( hi - lo ) * unit( *key )


def pick( options, *key ):
    return options[int( unit( *key ) * len( options ) ) % len( options )]


def chance( p, *key ):
    return unit( *key ) < p


def smooth( t ):
    t = min( max( t, 0.0 ), 1.0 )
    return t * t * ( 3 - 2 * t )


def lerp( a, b, t ):
    return a + ( b - a ) * t


def noise2( e, n, scale, key ):
    """ Smooth value noise in -1..1 over cells `scale` across. """
    x, y = e / scale, n / scale
    x0, y0 = math.floor( x ), math.floor( y )
    fx, fy = smooth( x - x0 ), smooth( y - y0 )
    v = [ [ unit( key, x0 + i, y0 + j ) * 2 - 1 for j in ( 0, 1 ) ] for i in ( 0, 1 ) ]
    return lerp( lerp( v[0][0], v[1][0], fx ), lerp( v[0][1], v[1][1], fx ), fy )


def fractal( e, n, scale, key, octaves=3 ):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range( octaves ):
        total += amp * noise2( e, n, scale / 2 ** o, f"{key}{o}" )
        norm += amp
        amp *= 0.5
    return total / norm


# ---------------------------------------------------------------------------------------------------------------------
# Levels

def brae_z( n ):
    """ The brae's ground (DESIGN.md), carried on level at 48 behind its dyke and at -50 down to the seawall. """
    if n >= 880:
        return ROAD
    if n >= 400:
        return ROAD * ( n - 400 ) / 480
    if n >= -600:
        return YARD
    if n >= -1120:
        return WALK * ( -600 - n ) / 520
    return WALK


def beach_z( n ):
    t = min( max( ( -1350.0 - n ) / 410.0, 0.0 ), 1.0 )
    return BEACH_TOP + ( BEACH_FOOT - BEACH_TOP ) * t


# ---------------------------------------------------------------------------------------------------------------------
# Materials

def materials():
    """ stillhouse_materials, if it's there yet. """
    try:
        import stillhouse_materials as SM
        return SM
    except Exception:
        return None


def sm_tiles( SM ):
    """ { paint: tile } from SM's paints() or tile_units(), whichever it has. """
    table = {}
    for name in ( "paints", "tile_units" ):
        fn = getattr( SM, name, None )
        if not callable( fn ):
            continue
        try:
            got = fn()
        except TypeError:
            continue
        except Exception:
            continue
        if isinstance( got, dict ):
            for paint, value in got.items():
                try:
                    table.setdefault( paint, float( value[1] if isinstance( value, ( tuple, list ) ) else value ) )
                except Exception:
                    pass
    return table


def configure( model ):
    """ Point every sh_ paint at its material with its tile (stillhouse_materials' if it's there, else DESIGN.md's),
    and mark the grain paints. building_textures' paints (clay_pot) need nothing. """
    SM = materials()
    table = sm_tiles( SM ) if SM is not None else {}
    grain = set( getattr( SM, "GRAIN", GRAIN ) ) if SM is not None else set( GRAIN )
    for paint in list( model.polygons ):
        if not paint.startswith( "sh_" ):
            continue
        path = None
        if SM is not None and callable( getattr( SM, "material_path", None ) ):
            try:
                path = SM.material_path( paint )
            except Exception:
                path = None
        model.material_overrides[paint] = path or f"materials/stillhouse/{paint}.vmat"
        tile = table.get( paint )
        if tile is None and SM is not None and callable( getattr( SM, "tile_units", None ) ):
            try:
                tile = float( SM.tile_units( paint ) )
            except Exception:
                tile = None
        model.tile_overrides[paint] = float( tile or TILES.get( paint, 128 ) )
    model.grain_paints = { p for p in model.polygons if p in grain }
    model.anchored_paints = set()
    model.decal_paints = set()
    return model


# ---------------------------------------------------------------------------------------------------------------------
# Drawing helpers

def facing( model, paint, points, towards, uv=None ):
    """ A polygon turned to face towards (its points' order reversed if they wound the other way). """
    pts = [ np.asarray( p, float ) for p in points ]
    normal = np.zeros( 3 )
    for k in range( 1, len( pts ) - 1 ):
        normal += np.cross( pts[k] - pts[0], pts[k + 1] - pts[0] )
    if np.linalg.norm( normal ) < 1e-9:
        return
    if np.dot( normal, towards ) < 0:
        pts = pts[:1] + pts[:0:-1]
        uv = None if uv is None else list( uv[:1] ) + list( uv[:0:-1] )
    model.polygon( paint, pts, uv=uv )


def flat( model, paint, e0, e1, n0, n1, z ):
    if e1 > e0 and n1 > n0:
        model.polygon( paint, [ ( e0, n0, z ), ( e1, n0, z ), ( e1, n1, z ), ( e0, n1, z ) ] )


def lathe( model, centre, profile, paint, sides=8, turn=0.0, cap=True ):
    """ A round thing: profile ( r, z ) from the bottom up, turned about centre ( e, n ). """
    c = np.array( ( centre[0], centre[1] ) )
    angles = [ turn + 2 * math.pi * k / sides for k in range( sides + 1 ) ]
    for ( ra, za ), ( rb, zb ) in zip( profile, profile[1:] ):
        for a0, a1 in zip( angles, angles[1:] ):
            d0, d1 = np.array( ( math.cos( a0 ), math.sin( a0 ) ) ), np.array( ( math.cos( a1 ), math.sin( a1 ) ) )
            mid = ( d0 + d1 ) / 2
            towards = np.array( ( *( mid * ( zb - za ) ), ra - rb ) )
            if np.linalg.norm( towards ) < 1e-9:
                continue
            pts = [ ( *( c + d0 * ra ), za ), ( *( c + d1 * ra ), za ), ( *( c + d1 * rb ), zb ), ( *( c + d0 * rb ), zb ) ]
            if ra < 1e-6:
                pts = pts[1:]
            elif rb < 1e-6:
                pts = pts[:3]
            facing( model, paint, pts, towards )
    r, z = profile[-1]
    if cap and r > 1e-6:
        model.polygon( paint, [ ( *( c + r * np.array( ( math.cos( a ), math.sin( a ) ) ) ), z ) for a in angles[:-1] ] )


def rod( model, p0, p1, size, paint ):
    """ A thin square bar from p0 to p1 with no end caps. """
    p0, p1 = np.asarray( p0, float ), np.asarray( p1, float )
    x = K.normalise( p1 - p0 )
    side = np.cross( ( 0.0, 0.0, 1.0 ), x )
    if np.linalg.norm( side ) < 1e-6:
        side = np.cross( ( 1.0, 0.0, 0.0 ), x )
    y = K.normalise( side )
    z = np.cross( x, y )
    model.oriented_box( ( p0 + p1 ) / 2, ( x, y, z ), ( np.linalg.norm( p1 - p0 ), size, size ),
                        { "default": paint, "+x": None, "-x": None } )


def split_z( points, z ):
    """ A convex polygon cut by the level z: ( the part below, the part above ), either possibly empty. """
    below, above = [], []
    n = len( points )
    for k in range( n ):
        a, b = np.asarray( points[k], float ), np.asarray( points[( k + 1 ) % n], float )
        ( below if a[2] <= z else above ).append( a )
        if ( a[2] - z ) * ( b[2] - z ) < 0:
            p = a + ( z - a[2] ) / ( b[2] - a[2] ) * ( b - a )
            below.append( p )
            above.append( p )
    return ( below if len( below ) >= 3 else [] ), ( above if len( above ) >= 3 else [] )


def rock_paint( z ):
    return "sh_rock_weed" if z < WEED_Z else "sh_rock"


def rock( model, centre, size, key, collide=True, chamfer=0.28, cap=30.0, top=None, paints=None, clamp=None,
          n_max=None, lean=None, turn=0.0, dip=( 0.0, 0.0 ) ):
    """ A block of shore rock: a box size ( e, n, z ) about centre, turned turn degrees about the vertical, with its
    corners and edges knocked off by its key (at most cap inches, and as much again by its jitter), drawn as its convex
    hull (wrack below WEED_Z) and with that hull for collision. lean ( e, n ) is its lean per inch of height (random if
    None). n_max keeps every point at or south of it; clamp ( side, e[, k, z[, t, n]] ) keeps every point at side x e
    or further out, or behind a face leaning back k per inch over the level z and turned t per inch of n from n; top
    cuts it off at that height over its centre, sloping dip ( e, n ) per inch. Returns its points. """
    c, s = np.asarray( centre, float ), np.asarray( size, float ) / 2
    pts = []
    for i, sx in enumerate( ( -1, 1 ) ):
        for j, sy in enumerate( ( -1, 1 ) ):
            for k, sz in enumerate( ( -1, 1 ) ):
                corner = np.array( ( sx, sy, sz ), float )
                cut = min( chamfer * between( 0.5, 1.4, key, i, j, k, "cut" ) * float( s.min() ), cap )
                for axis in range( 3 ):
                    p = corner * s
                    p[axis] -= corner[axis] * cut
                    for ax in range( 3 ):
                        p[ax] -= corner[ax] * min( between( 0.0, 0.14, key, i, j, k, axis, ax ) * s[ax], 0.6 * cap )
                    pts.append( p )
    pts = np.array( pts )
    if turn:
        ca, sa = math.cos( math.radians( turn ) ), math.sin( math.radians( turn ) )
        pts[:, :2] = pts[:, :2] @ np.array( ( ( ca, sa ), ( -sa, ca ) ) )
    pts += c
    if lean is None:
        lean = ( between( -0.18, 0.18, key, "le" ), between( -0.18, 0.18, key, "ln" ) )
    pts[:, 0] += ( pts[:, 2] - c[2] ) * lean[0]
    pts[:, 1] += ( pts[:, 2] - c[2] ) * lean[1]
    if n_max is not None:
        pts[:, 1] = np.minimum( pts[:, 1], n_max )
    if clamp is not None:
        side, e = clamp[0], clamp[1]
        k, z0 = ( clamp[2], clamp[3] ) if len( clamp ) > 2 else ( 0.0, 0.0 )
        turn_n, n0 = ( clamp[4], clamp[5] ) if len( clamp ) > 4 else ( 0.0, 0.0 )
        pts[:, 0] = side * np.maximum( side * pts[:, 0], e + k * ( pts[:, 2] - z0 ) + turn_n * ( pts[:, 1] - n0 ) )
    if top is not None:
        pts[:, 2] = np.minimum( pts[:, 2], top + dip[0] * ( pts[:, 0] - c[0] ) + dip[1] * ( pts[:, 1] - c[1] ) )
    pts = np.unique( np.round( pts, 2 ), axis=0 )
    for face in K.convex_faces( pts ):
        poly = [ pts[i] for i in face ]
        below, above = split_z( poly, WEED_Z )
        for part, paint in ( ( below, ( paints or {} ).get( "low", "sh_rock_weed" ) ),
                             ( above, ( paints or {} ).get( "high", "sh_rock" ) ) ):
            if part:
                model.polygon( paint, part )
    if collide:
        model.hull( [ tuple( p ) for p in pts ], STONE )
    return pts


# ---------------------------------------------------------------------------------------------------------------------
# Faces and openings

class Face:
    """ A face of a building: origin ( e, n ) is its r = 0 point, out its outward normal in plan. r runs to the right of
    someone looking at it, d out of it, z up. """

    def __init__( self, origin, out ):
        self.o = np.array( ( origin[0], origin[1], 0.0 ), float )
        self.D = np.array( ( out[0], out[1], 0.0 ), float )
        self.R = np.array( ( -out[1], out[0], 0.0 ), float )
        self.Z = np.array( ( 0.0, 0.0, 1.0 ) )

    def p( self, r, d, z ):
        return self.o + self.R * r + self.D * d + self.Z * z

    def quad( self, model, paint, r0, r1, z0, z1, d=0.0, out=1.0 ):
        if r1 - r0 < 1e-6 or z1 - z0 < 1e-6:
            return
        facing( model, paint, [ self.p( r0, d, z0 ), self.p( r1, d, z0 ), self.p( r1, d, z1 ), self.p( r0, d, z1 ) ],
                self.D * out )

    def poly( self, model, paint, rz, d=0.0, out=1.0 ):
        facing( model, paint, [ self.p( r, d, z ) for r, z in rz ], self.D * out )

    def across( self, model, paint, r, dz, towards ):
        """ A polygon across the face at r, its points ( d, z ), facing +R ( towards 1 ) or -R. """
        facing( model, paint, [ self.p( r, d, z ) for d, z in dz ], self.R * towards )

    def side( self, model, paint, r, d0, d1, z0, z1, towards ):
        self.across( model, paint, r, [ ( d0, z0 ), ( d1, z0 ), ( d1, z1 ), ( d0, z1 ) ], towards )

    def level( self, model, paint, r0, r1, d0, d1, z, up=1.0 ):
        facing( model, paint, [ self.p( r0, d0, z ), self.p( r1, d0, z ), self.p( r1, d1, z ), self.p( r0, d1, z ) ],
                self.Z * up )

    def box( self, model, r0, r1, d0, d1, z0, z1, paint, back=False ):
        """ A box standing out of the face from d0 to d1; its back isn't drawn unless back. """
        self.quad( model, paint, r0, r1, z0, z1, d1 )
        if back:
            self.quad( model, paint, r0, r1, z0, z1, d0, -1.0 )
        self.side( model, paint, r0, d0, d1, z0, z1, -1.0 )
        self.side( model, paint, r1, d0, d1, z0, z1, 1.0 )
        self.level( model, paint, r0, r1, d0, d1, z1, 1.0 )
        self.level( model, paint, r0, r1, d0, d1, z0, -1.0 )

    def slope( self, model, paint, r0, r1, d0, z0, d1, z1, towards_d ):
        """ A roof plane between the level lines ( d0, z0 ) and ( d1, z1 ), r0..r1, facing up and towards_d. """
        facing( model, paint, [ self.p( r0, d0, z0 ), self.p( r1, d0, z0 ), self.p( r1, d1, z1 ), self.p( r0, d1, z1 ) ],
                self.D * towards_d + self.Z )


def holed_wall( model, face, paint, r0, r1, z0, z1, holes, d=0.0 ):
    """ A wall r0..r1, z0..z1 at d with rectangular holes ( r0, r1, z0, z1 ) cut out of it, as upright strips. """
    edges = sorted( { r0, r1, *[ min( max( h[0], r0 ), r1 ) for h in holes ], *[ min( max( h[1], r0 ), r1 ) for h in holes ] } )
    for a, b in zip( edges, edges[1:] ):
        if b - a < 1e-6:
            continue
        mid = ( a + b ) / 2
        gaps = sorted( ( h[2], h[3] ) for h in holes if h[0] < mid < h[1] )
        z = z0
        for g0, g1 in gaps:
            if g0 > z:
                face.quad( model, paint, a, b, z, min( g0, z1 ), d )
            z = max( z, g1 )
        if z < z1:
            face.quad( model, paint, a, b, z, z1, d )


def reveal( model, face, paint, r0, r1, z0, z1, depth, d=0.0, top=True, bottom=True ):
    """ The sides of a hole in a wall at d, depth deep. """
    face.side( model, paint, r0, d - depth, d, z0, z1, 1.0 )
    face.side( model, paint, r1, d - depth, d, z0, z1, -1.0 )
    if top:
        face.level( model, paint, r0, r1, d - depth, d, z1, -1.0 )
    if bottom:
        face.level( model, paint, r0, r1, d - depth, d, z0, 1.0 )


def sash_window( model, face, r0, r1, z0, z1, look, depth=WALL, margin=6.0, d=0.0 ):
    """ A sash and case window deep in a harled wall: its painted margin and sill, the reveal, the glass and the sashes
    (six panes over six, or two over two). """
    m, paint = margin, look["margin"]
    face.quad( model, paint, r0 - m, r0, z0, z1 + m, d )
    face.quad( model, paint, r1, r1 + m, z0, z1 + m, d )
    face.quad( model, paint, r0, r1, z1, z1 + m, d )
    face.box( model, r0 - m - 1.5, r1 + m + 1.5, d, d + 2.0, z0 - m, z0, paint )
    reveal( model, face, look["harl"], r0, r1, z0, z1, depth, d )
    back = d - depth
    face.quad( model, "sh_window_dark", r0, r1, z0, z1, back )
    f, bar, frame = back + 0.8, 2.5, "sh_paint_white"
    face.quad( model, frame, r0, r0 + bar, z0, z1, f )
    face.quad( model, frame, r1 - bar, r1, z0, z1, f )
    face.quad( model, frame, r0 + bar, r1 - bar, z1 - bar, z1, f )
    face.quad( model, frame, r0 + bar, r1 - bar, z0, z0 + bar * 1.4, f )
    mid = ( z0 + z1 ) / 2
    face.quad( model, frame, r0 + bar, r1 - bar, mid - 1.2, mid + 1.2, f + 0.3 )
    if look.get( "panes", 6 ) == 6:
        for t in ( 1 / 3, 2 / 3 ):
            rc = r0 + ( r1 - r0 ) * t
            face.quad( model, frame, rc - 0.6, rc + 0.6, z0 + bar, z1 - bar, f + 0.5 )
        for zc in ( ( z0 + mid ) / 2, ( mid + z1 ) / 2 ):
            face.quad( model, frame, r0 + bar, r1 - bar, zc - 0.6, zc + 0.6, f + 0.5 )
    else:
        rc = ( r0 + r1 ) / 2
        face.quad( model, frame, rc - 0.7, rc + 0.7, z0 + bar, z1 - bar, f + 0.5 )


# ---------------------------------------------------------------------------------------------------------------------
# The terraces: harled cottages up each brae

T47 = math.tan( math.radians( PITCH ) )
RIDGE_D = -MAIN / 2                     # the ridge over the main block's middle
DEPTH = BACK - FRONT                    # 350: the outshot's back wall is the terrace's back
OUT_DROP = 30.0                         # the outshot's lean-to meets the back wall this far under the main eaves
OUT_RISE = math.tan( math.radians( 20.0 ) )
WIN_W, WIN_SILL, WIN_HEAD = 32.0, 30.0, 80.0            # 0.8 m wide, 1.27 m tall, over the floor
DOOR_W, DOOR_H, FAN = 36.0, 80.0, 14.0
MARGIN = 6.0
DORMER_HW, DORMER_RISE = 25.0, 40.0     # a wallhead dormer's half width, and its eaves over the main eaves
BYRE_EAVES = 106.0

# Each terrace from the seawall north: ( width, slots south to north, harl, door, margin, roof, panes, cans ). On the
# brae's ramps the door is the slot furthest uphill (north), so the floor sits a step over the ground at the door.
TERRACES = {
    1: ( ( 320, "wdw", "sh_harl", "sh_paint_blue", "sh_tar_black", "wallhead", 6, 3 ),
         ( 330, "wwd", "sh_harl", "sh_paint_door", "sh_tar_black", "lights", 6, 2 ),
         ( 360, "wdw", "sh_harl_cream", "sh_paint_red", "sh_tar_black", "plain", 2, 4 ),
         ( 420, "wdww", "sh_harl", "sh_paint_black", "sh_tar_black", "wallhead", 6, 3 ),
         ( 300, "dw", "sh_harl_shade", "sh_paint_yellow", "sh_tar_black", "lights", 2, 2 ),
         ( 320, "wwd", "sh_harl", "sh_paint_door", "sh_paint_blue", "wallhead", 6, 3 ),
         ( 330, "wwd", "sh_harl_cream", "sh_paint_blue", "sh_tar_black", "plain", 6, 2 ),
         ( 290, "wd", "sh_harl", "sh_paint_red", "sh_tar_black", "lights", 6, 3 ),
         ( 280, "dw", "sh_harl", "sh_paint_door", "sh_tar_black", "wallhead", 2, 2 ) ),
    -1: ( ( 300, "wdw", "sh_harl_cream", "sh_paint_red", "sh_tar_black", "plain", 6, 2 ),
          ( 360, "wwd", "sh_harl", "sh_paint_yellow", "sh_tar_black", "wallhead", 6, 3 ),
          ( 330, "dww", "sh_harl", "sh_paint_door", "sh_paint_door", "lights", 2, 4 ),
          ( 380, "wdww", "sh_harl_shade", "sh_paint_blue", "sh_tar_black", "wallhead", 6, 3 ),
          ( 340, "wdw", "sh_harl", "sh_paint_red", "sh_tar_black", "plain", 6, 2 ),
          ( 300, "wwd", "sh_harl_mould", "sh_paint_black", "sh_tar_black", "lights", 2, 3 ),
          ( 360, "wwd", "sh_harl", "sh_paint_door", "sh_tar_black", "wallhead", 6, 2 ),
          ( 300, "dw", "sh_harl_cream", "sh_paint_blue", "sh_paint_red", "plain", 6, 4 ),
          ( 280, "wd", "sh_harl", "sh_paint_yellow", "sh_tar_black", "lights", 2, 3 ) ),
}
# The byre that carries each terrace on to TERRACE_END: unharled rubble, a tin roof on the east, slates on the west
BYRES = { 1: "sh_corrugated_red", -1: "sh_slate_roof" }


def profile( eave, over=0.0 ):
    """ A unit's roof line at its party walls, front to back ( d, z ): the main roof's two slopes, then the outshot's
    lean-to; over carries it out over the front eaves. Every unit's is the same shape, so a step between two is the
    same band all the way back. """
    return [ ( over, eave - over * T47 ), ( RIDGE_D, eave - RIDGE_D * T47 ), ( -MAIN, eave ), ( -MAIN, eave - OUT_DROP ),
             ( -DEPTH, eave - OUT_DROP - ( DEPTH - MAIN ) * OUT_RISE ) ]


def terrace_plan( side ):
    """ The terrace's units from the seawall north, the byre last, with their levels. """
    units, n = [], TERRACE_N0
    rows = [ dict( zip( ( "width", "slots", "harl", "door", "margin", "roof", "panes", "cans" ), row ) )
             for row in TERRACES[side] ]
    rows.append( dict( width=TERRACE_END - TERRACE_N1, slots="vdv", harl="sh_rubble", door="sh_timber_tar",
                       margin="sh_rubble", roof=BYRES[side], panes=0, cans=0, byre=True ) )
    for i, u in enumerate( rows ):
        u = dict( u, index=i, byre=u.get( "byre", False ), n0=n, n1=n + u["width"] )
        n = u["n1"]
        grounds = [ brae_z( x ) for x in np.linspace( u["n0"], u["n1"], 9 ) ]
        k = len( u["slots"] )
        u["slot_n"] = [ u["n0"] + u["width"] * ( j + 0.5 ) / k for j in range( k ) ]
        doors = [ x for x, c in zip( u["slot_n"], u["slots"] ) if c == "d" ]
        u["ground_lo"], u["ground_hi"] = min( grounds ), max( grounds )
        if u["byre"]:
            u["floor"] = u["ground_hi"] + 2.0
            u["eave"] = u["floor"] + BYRE_EAVES
        else:
            u["floor"] = max( brae_z( doors[0] ) + STEP, u["ground_hi"] - 10.0 )
            u["eave"] = max( u["floor"] + EAVES + between( -5.0, 6.0, "eaves", side, i ), u["ground_hi"] + 104.0 )
        u["ridge"] = u["eave"] - RIDGE_D * T47
        u["bottom"] = u["ground_lo"] - 30.0
        units.append( u )
    return units


def rspan( side, na, nb ):
    """ Plan n to the terrace face's r ( r = -side x n ), as an ordered pair. """
    a, b = -side * na, -side * nb
    return min( a, b ), max( a, b )


def roof_point( face, r, d, eave, lift=0.0 ):
    """ A point on a unit's front roof slope ( d <= 0 ), lifted off it along its normal. """
    normal = ( face.D * T47 + face.Z ) / math.hypot( T47, 1.0 )
    return face.p( r, d, eave - d * T47 ) + normal * lift


def skew( model, face, r, a, b, paint, width=10.0, thick=4.0, inset=0.0 ):
    """ A coping along a gable's raking edge from a ( d, z ) to b, on the wall at r (moved inset along R). """
    pa, pb = face.p( r + inset, a[0], a[1] ), face.p( r + inset, b[0], b[1] )
    x = K.normalise( pb - pa )
    y = face.R.copy()
    z = np.cross( x, y )
    if z[2] < 0:
        y, z = -y, -z
    model.oriented_box( ( pa + pb ) / 2 + z * ( thick / 2 ), ( x, y, z ), ( float( np.linalg.norm( pb - pa ) ), width, thick ),
                        { "default": paint, "-z": None } )


def front_door( model, face, r0, r1, look, floor, ground ):
    """ A panelled door in a 10-deep reveal with a fanlight over it, painted margins round both down to the ground and
    a granite step in the reveal's foot. """
    m, top = MARGIN, floor + DOOR_H + FAN
    face.quad( model, look["margin"], r0 - m, r0, ground - 4.0, top + m )
    face.quad( model, look["margin"], r1, r1 + m, ground - 4.0, top + m )
    face.quad( model, look["margin"], r0, r1, top, top + m )
    reveal( model, face, look["harl"], r0, r1, floor, top, 10.0, bottom=False )
    face.level( model, "sh_granite", r0, r1, -10.0, 0.0, floor )
    face.quad( model, "sh_granite", r0, r1, ground - 4.0, floor )
    leaf, d = look["door"], -10.0
    face.quad( model, leaf, r0, r1, floor, floor + DOOR_H, d )
    # Four panels' mouldings, a letter plate and a knob
    for z0, z1 in ( ( floor + 8, floor + 38 ), ( floor + 46, floor + 74 ) ):
        for a, b in ( ( r0 + 4, ( r0 + r1 ) / 2 - 2 ), ( ( r0 + r1 ) / 2 + 2, r1 - 4 ) ):
            face.box( model, a, b, d, d + 0.8, z0, z1, leaf )
    face.box( model, ( r0 + r1 ) / 2 - 5, ( r0 + r1 ) / 2 + 5, d, d + 0.6, floor + 41, floor + 43.5, "sh_brass" )
    knob = r0 + 5 if look.get( "hinge_left", False ) else r1 - 5
    face.box( model, knob - 1.2, knob + 1.2, d, d + 2.2, floor + 39, floor + 41.4, "sh_brass" )
    # The transom and the fanlight's glass and bars
    face.quad( model, "sh_paint_white", r0, r1, floor + DOOR_H, floor + DOOR_H + 2.0, d + 0.4 )
    face.quad( model, "sh_window_dark", r0, r1, floor + DOOR_H + 2.0, top, d )
    for t in ( 0.25, 0.5, 0.75 ):
        rc = r0 + ( r1 - r0 ) * t
        face.quad( model, "sh_paint_white", rc - 0.6, rc + 0.6, floor + DOOR_H + 2.0, top, d + 0.4 )


def dormer( model, face, rc, eave, look ):
    """ A wallhead dormer at rc: its harled front rising out of the front wall through the eaves with a sash in it, a
    slated gablet over it and harled cheeks back to the main roof. Returns its collision points. """
    hw, over = DORMER_HW, 4.0
    de = eave + DORMER_RISE
    dr = de + hw * T47
    c = DORMER_RISE / T47
    harl = look["harl"]
    win = ( rc - 14.0, rc + 14.0, eave - 14.0, eave + 28.0 )
    holed_wall( model, face, harl, rc - hw, rc + hw, eave, de, [ ( win[0] - 5, win[1] + 5, win[2] - 5, win[3] + 5 ) ] )
    face.poly( model, harl, [ ( rc - hw, de ), ( rc + hw, de ), ( rc, dr ) ] )
    sash_window( model, face, *win, look, depth=10.0, margin=5.0 )
    for s in ( -1.0, 1.0 ):
        face.across( model, harl, rc + s * hw, [ ( 0.0, eave ), ( 0.0, de ), ( -c, de ) ], s )
        slope = [ face.p( rc + s * ( hw + over ), over, de - over * T47 ), face.p( rc + s * ( hw + over ), over - c, de - over * T47 ),
                  face.p( rc, -hw - c, dr ), face.p( rc, over, dr ) ]
        facing( model, "sh_slate_roof", slope, face.R * s * T47 + face.Z )
    # The lead ridge over the gablet
    rod( model, face.p( rc, over, dr + 1.0 ), face.p( rc, -hw - c, dr + 1.0 ), 3.0, "sh_lead" )
    return [ tuple( face.p( rc + s * hw, 0.0, z ) ) for s in ( -1, 1 ) for z in ( eave, de ) ] + \
           [ tuple( face.p( rc + s * hw, -c, de ) ) for s in ( -1, 1 ) ] + [ tuple( face.p( rc, 0.0, dr ) ), tuple( face.p( rc, -hw - c, dr ) ) ]


def roof_light( model, face, rc, eave ):
    """ A cast-iron roof light set in the front slope. """
    a, b = -44.0, -62.0
    corners = lambda r0, r1, d0, d1, lift: [ roof_point( face, r0, d0, eave, lift ), roof_point( face, r1, d0, eave, lift ),
                                             roof_point( face, r1, d1, eave, lift ), roof_point( face, r0, d1, eave, lift ) ]
    up = face.D * T47 + face.Z
    facing( model, "sh_paint_black", corners( rc - 13, rc + 13, a + 2.0, b - 2.0, 1.2 ), up )
    facing( model, "sh_window_dark", corners( rc - 10, rc + 10, a, b, 1.8 ), up )
    facing( model, "sh_paint_black", corners( rc - 0.8, rc + 0.8, a, b, 2.0 ), up )


def stack( model, face, r_lo, r_hi, base, top, cans, key, harl ):
    """ A gable stack straddling the ridge from r_lo to r_hi, harled, with a projecting cope and its clay cans. """
    d0, d1 = RIDGE_D - 32.0, RIDGE_D + 32.0
    lo, hi = face.p( r_lo, d0, base ), face.p( r_hi, d1, top )
    model.box( np.minimum( lo, hi ), np.maximum( lo, hi ), { "default": harl, "-z": None }, surface=STONE )
    c0, c1 = face.p( r_lo - 2.5, d0 - 2.5, top ), face.p( r_hi + 2.5, d1 + 2.5, top + 4.0 )
    model.box( np.minimum( c0, c1 ), np.maximum( c0, c1 ), "sh_granite" )
    rm = ( r_lo + r_hi ) / 2
    for j in range( cans ):
        dc = RIDGE_D + ( j - ( cans - 1 ) / 2 ) * 15.0
        c = face.p( rm, dc, top + 4.0 )
        h = between( 14.0, 22.0, key, "can", j )
        lathe( model, ( c[0], c[1] ), [ ( 5.6, c[2] ), ( 5.0, c[2] + h * 0.6 ), ( 4.2, c[2] + h - 1.5 ), ( 4.8, c[2] + h ) ],
               "clay_pot", sides=6, cap=False )
        model.polygon( "sh_tar_black", [ ( *( np.array( ( c[0], c[1] ) ) + 4.2 * np.array( ( math.cos( a ), math.sin( a ) ) ) ),
                                           c[2] + h - 2.0 ) for a in np.linspace( 0, 2 * math.pi, 7 )[:-1] ] )


def band( model, face, r, low, high, towards, paint ):
    """ The face of the higher unit's party wall standing over the lower one's roof: between the two roof lines, piece by
    piece, facing towards ( a plan vector ). Returns the skew's run along the higher line. """
    for ( da, la ), ( db, lb ), ( _, ha ), ( _, hb ) in zip( low, low[1:], high, high[1:] ):
        if abs( da - db ) < 1e-6:
            continue
        if ha - la < 0.5 and hb - lb < 0.5:
            continue
        facing( model, paint, [ face.p( r, da, la ), face.p( r, db, lb ), face.p( r, db, hb ), face.p( r, da, ha ) ], towards )


def gable_skews( model, face, r, eave, towards, paint="sh_granite", over=5.0 ):
    """ The copings along both raking edges of a gable or a stepped party wall at r, set out towards ( +-1 along R ). """
    ridge = eave - RIDGE_D * T47
    skew( model, face, r, ( over, eave - over * T47 ), ( RIDGE_D, ridge ), paint, inset=towards * 1.5 )
    skew( model, face, r, ( RIDGE_D, ridge ), ( -MAIN - over, eave - over * T47 ), paint, inset=towards * 1.5 )


def end_gable( model, face, side, u, n, towards, bottom, paint, look=None ):
    """ A terrace's end wall at n, from bottom up, facing towards ( +-1 along R ); with look, an attic window in its apex. """
    r, eave, ridge = -side * n, u["eave"], u["ridge"]
    face.across( model, paint, r, [ ( 0.0, bottom ), ( 0.0, eave ), ( -MAIN, eave ), ( -MAIN, bottom ) ], towards )
    lz = eave - OUT_DROP
    zb = lz - ( DEPTH - MAIN ) * OUT_RISE
    face.across( model, paint, r, [ ( -MAIN, bottom ), ( -MAIN, lz ), ( -DEPTH, zb ), ( -DEPTH, bottom ) ], towards )
    if look is None:
        face.across( model, paint, r, [ ( 0.0, eave ), ( RIDGE_D, ridge ), ( -MAIN, eave ) ], towards )
        return
    h, za, zt = 18.0, eave + 25.0, eave + 79.0

    def roof( d ):
        return eave + ( -d if d > RIDGE_D else d + MAIN ) * T47

    da, db = RIDGE_D + h, RIDGE_D - h
    face.across( model, paint, r, [ ( 0.0, eave ), ( da, roof( da ) ), ( da, eave ) ], towards )
    face.across( model, paint, r, [ ( db, eave ), ( db, roof( db ) ), ( -MAIN, eave ) ], towards )
    face.across( model, paint, r, [ ( da, eave ), ( da, za ), ( db, za ), ( db, eave ) ], towards )
    face.across( model, paint, r, [ ( da, zt ), ( da, roof( da ) ), ( RIDGE_D, ridge ), ( db, roof( db ) ), ( db, zt ) ],
                 towards )
    gable = Face( face.p( r, 0.0, 0.0 )[:2], ( face.R * towards )[:2] )
    k = float( np.dot( face.D, gable.R ) )
    ra, rb = sorted( ( k * ( RIDGE_D - 13.0 ), k * ( RIDGE_D + 13.0 ) ) )
    sash_window( model, gable, ra, rb, za + 5.0, zt - 5.0, look, depth=12.0, margin=5.0 )


def cottage( model, side, u, face ):
    """ One harled cottage of the terrace: its front with its windows and door, dormers or roof lights, the slated roof
    with its rones, downpipe and ridge, the back and its outshot; a collision box to its eaves and the roof's hull. """
    s = side
    r0, r1 = rspan( s, u["n0"], u["n1"] )
    eave, floor, ridge, bottom = u["eave"], u["floor"], u["ridge"], u["bottom"]
    look = dict( harl=u["harl"], margin=u["margin"], door=u["door"], panes=u["panes"] )
    key = ( "cottage", s, u["index"] )
    T, over = T47, 5.0
    eave_z = eave - over * T
    holes, wins = [], []
    for n, c in zip( u["slot_n"], u["slots"] ):
        rc = -s * n
        if c == "w":
            wins.append( rc )
            a, b = rc - WIN_W / 2, rc + WIN_W / 2
            holes.append( ( a - MARGIN, b + MARGIN, floor + WIN_SILL - MARGIN, floor + WIN_HEAD + MARGIN ) )
            sash_window( model, face, a, b, floor + WIN_SILL, floor + WIN_HEAD, look )
        elif c == "d":
            g = brae_z( n )
            a, b = rc - DOOR_W / 2, rc + DOOR_W / 2
            holes.append( ( a - MARGIN, b + MARGIN, g - 4.0, floor + DOOR_H + FAN + MARGIN ) )
            front_door( model, face, a, b, dict( look, hinge_left=chance( 0.5, *key, "hinge" ) ), floor, g )
    chosen = sorted( wins if len( wins ) <= 2 else [ wins[0], wins[-1] ] )
    dormers = chosen if u["roof"] == "wallhead" else []
    for rc in dormers:
        holes.append( ( rc - 19.0, rc + 19.0, eave - 19.0, eave + 33.0 ) )
    holed_wall( model, face, "sh_tar_black", r0, r1, bottom, floor + PLINTH, holes )
    holed_wall( model, face, u["harl"], r0, r1, floor + PLINTH, eave, holes )

    # The front slope, cut round the dormers
    hw, o = DORMER_HW, 4.0
    c = DORMER_RISE / T
    de, dr = eave + DORMER_RISE, eave + DORMER_RISE + hw * T
    up = face.D * T + face.Z
    x = r0
    for rc in dormers:
        face.slope( model, "sh_slate_roof", x, rc - hw - o, over, eave_z, RIDGE_D, ridge, 1.0 )
        x = rc + hw + o
        for sgn in ( -1.0, 1.0 ):
            xa, xb = rc + sgn * hw, rc + sgn * ( hw + o )
            facing( model, "sh_slate_roof", [ face.p( xb, o - c, de - o * T ), face.p( rc, -hw - c, dr ),
                                              face.p( rc, RIDGE_D, ridge ), face.p( xb, RIDGE_D, ridge ) ], up )
            facing( model, "sh_slate_roof", [ face.p( xa, over, eave_z ), face.p( xb, over, eave_z ),
                                              face.p( xb, o - c, de - o * T ), face.p( xa, -c, de ) ], up )
        model.hull( dormer( model, face, rc, eave, look ), STONE )
    face.slope( model, "sh_slate_roof", x, r1, over, eave_z, RIDGE_D, ridge, 1.0 )
    if u["roof"] == "lights":
        for rc in chosen:
            roof_light( model, face, rc, eave )

    # Rones and the soffit under the eaves, broken by the dormers; a downpipe at the end furthest from the openings
    x, spans = r0, []
    for rc in dormers:
        spans.append( ( x, rc - hw ) )
        x = rc + hw
    spans.append( ( x, r1 ) )
    for a, b in spans:
        if b - a < 1.0:
            continue
        face.box( model, a, b, over - 1.0, over + 5.0, eave - 11.0, eave_z - 0.3, "sh_paint_black" )
        facing( model, "sh_tar_black", [ face.p( a, 0.0, eave - 0.6 ), face.p( b, 0.0, eave - 0.6 ),
                                         face.p( b, over, eave_z - 0.6 ), face.p( a, over, eave_z - 0.6 ) ], -face.Z )

    def clearance( r ):
        return min( [ min( abs( r - h[0] ), abs( r - h[1] ) ) for h in holes ] + [ 999.0 ] )

    rp = max( ( r0 + 9.0, r1 - 9.0 ), key=clearance )
    g = brae_z( -s * rp )
    rod( model, face.p( rp, 7.0, eave - 9.0 ), face.p( rp, 7.0, g + 8.0 ), 3.0, "sh_paint_black" )
    face.box( model, rp - 2.5, rp + 2.5, 3.0, 11.0, g + 1.0, g + 8.0, "sh_paint_black" )
    rod( model, face.p( r0, RIDGE_D, ridge + 1.0 ), face.p( r1, RIDGE_D, ridge + 1.0 ), 4.0, "sh_lead" )

    # The back: the rear slope, the main block's wall over the outshot, its lean-to and its back wall
    face.slope( model, "sh_slate_roof", r0, r1, RIDGE_D, ridge, -MAIN - over, eave_z, -1.0 )
    lz = eave - OUT_DROP
    zb = lz - ( DEPTH - MAIN ) * OUT_RISE
    face.quad( model, u["harl"], r0, r1, lz, eave, -MAIN, -1.0 )
    face.slope( model, "sh_slate_roof", r0, r1, -MAIN, lz, -DEPTH - over, zb - over * OUT_RISE, -1.0 )
    face.quad( model, u["harl"], r0, r1, bottom, zb, -DEPTH, -1.0 )
    if chance( 0.7, *key, "back" ):
        rb = between( r0 + 40.0, r1 - 40.0, *key, "backwin" )
        face.quad( model, "sh_window_dark", rb - 14.0, rb + 14.0, floor + 34.0, floor + 74.0, -DEPTH - 0.5, -1.0 )

    model.collision_box( face.p( r0, 0.0, bottom ), face.p( r1, -MAIN, eave ), STONE )
    model.collision_box( face.p( r0, -MAIN, bottom ), face.p( r1, -DEPTH, lz ), STONE )
    model.hull( [ face.p( r, d, z ) for r in ( r0, r1 ) for d, z in ( ( 0.0, eave ), ( RIDGE_D, ridge ), ( -MAIN, eave ) ) ],
                STONE )


def byre( model, side, u, face ):
    """ The old byre at the brae's head: unharled rubble under a tin roof (slates on the west), a boarded door in a
    timber lintel and slit vents. """
    s = side
    r0, r1 = rspan( s, u["n0"], u["n1"] )
    eave, floor, ridge, bottom = u["eave"], u["floor"], u["ridge"], u["bottom"]
    T, over = T47, 6.0
    eave_z = eave - over * T
    holes = []
    for n, c in zip( u["slot_n"], u["slots"] ):
        rc = -s * n
        if c == "d":
            g = brae_z( n )
            a, b, top = rc - 27.0, rc + 27.0, g + 86.0
            holes.append( ( a, b, g - 4.0, top ) )
            face.box( model, a - 9.0, b + 9.0, -2.0, 2.0, top, top + 8.0, "sh_timber_tar" )
            reveal( model, face, "sh_rubble", a, b, g, top, 8.0, bottom=False )
            face.quad( model, "sh_timber_tar", a, b, g - 4.0, top, -8.0 )
            for zl in ( g + 12.0, g + 42.0, g + 72.0 ):
                face.box( model, a + 2.0, b - 2.0, -8.0, -6.5, zl, zl + 6.0, "sh_timber_tar" )
            face.box( model, b - 9.0, b - 6.0, -6.5, -5.0, g + 40.0, g + 46.0, "sh_paint_black" )
        else:
            for k, dz in enumerate( ( 44.0, ) ):
                a, b = rc - 3.0, rc + 3.0
                holes.append( ( a, b, floor + dz, floor + dz + 24.0 ) )
                reveal( model, face, "sh_rubble", a, b, floor + dz, floor + dz + 24.0, 14.0 )
                face.quad( model, "sh_window_dark", a, b, floor + dz, floor + dz + 24.0, -14.0 )
    holed_wall( model, face, "sh_rubble", r0, r1, bottom, eave, holes )
    roof = u["roof"]
    face.slope( model, roof, r0, r1, over, eave_z, RIDGE_D, ridge, 1.0 )
    face.slope( model, roof, r0, r1, RIDGE_D, ridge, -MAIN - over, eave_z, -1.0 )
    facing( model, "sh_timber_tar", [ face.p( r0, 0.0, eave - 0.6 ), face.p( r1, 0.0, eave - 0.6 ),
                                      face.p( r1, over, eave_z - 0.6 ), face.p( r0, over, eave_z - 0.6 ) ], -face.Z )
    rod( model, face.p( r0, RIDGE_D, ridge + 1.0 ), face.p( r1, RIDGE_D, ridge + 1.0 ), 4.0,
         "sh_lead" if roof == "sh_slate_roof" else roof )
    lz = eave - OUT_DROP
    zb = lz - ( DEPTH - MAIN ) * OUT_RISE
    face.quad( model, "sh_rubble", r0, r1, lz, eave, -MAIN, -1.0 )
    face.slope( model, roof, r0, r1, -MAIN, lz, -DEPTH - over, zb - over * OUT_RISE, -1.0 )
    face.quad( model, "sh_rubble", r0, r1, bottom, zb, -DEPTH, -1.0 )
    model.collision_box( face.p( r0, 0.0, bottom ), face.p( r1, -MAIN, eave ), STONE )
    model.collision_box( face.p( r0, -MAIN, bottom ), face.p( r1, -DEPTH, lz ), STONE )
    model.hull( [ face.p( r, d, z ) for r in ( r0, r1 ) for d, z in ( ( 0.0, eave ), ( RIDGE_D, ridge ), ( -MAIN, eave ) ) ],
                STONE )


def terrace( model, side ):
    """ The whole terrace up one side's brae: its units, the stepped party walls with their skews and stacks, and its
    end gables. Returns the units. """
    s = side
    face = Face( ( s * FRONT, 0.0 ), ( -s, 0.0 ) )
    units = terrace_plan( s )
    for u in units:
        ( byre if u["byre"] else cottage )( model, s, u, face )
    for a, b in zip( units, units[1:] ):
        r = -s * a["n1"]
        if abs( a["eave"] - b["eave"] ) > 0.5:
            hi, lo, way = ( a, b, -s ) if a["eave"] > b["eave"] else ( b, a, s )
            band( model, face, r, profile( lo["eave"], 5.0 ), profile( hi["eave"], 5.0 ), face.R * way,
                  "sh_rubble" if hi["byre"] else hi["harl"] )
            if hi["eave"] - lo["eave"] > 3.0 and not hi["byre"]:
                gable_skews( model, face, r, hi["eave"], way )
        if not a["byre"]:
            top = max( a["ridge"], b["ridge"] if not b["byre"] else a["ridge"] ) + 46.0
            stack( model, face, r - 14.0, r + 14.0, min( a["ridge"], b["ridge"] ) - 30.0, top, a["cans"],
                   ( "stack", s, a["index"] ), a["harl"] )
    first, last = units[0], units[-1]
    look = dict( harl=first["harl"], margin=first["margin"], door=first["door"], panes=first["panes"] )
    end_gable( model, face, s, first, TERRACE_N0, s, -320.0, first["harl"], look )
    gable_skews( model, face, -s * TERRACE_N0, first["eave"], s )
    r = -s * TERRACE_N0
    stack( model, face, *sorted( ( r, r - s * 28.0 ) ), first["ridge"] - 30.0, first["ridge"] + 46.0, 3,
           ( "stack", s, "south" ), first["harl"] )
    model.collision_box( ( s * FRONT, TERRACE_N0, -420.0 ), ( s * BACK, TERRACE_N0 + 120.0, first["bottom"] + 1.0 ), STONE )
    end_gable( model, face, s, last, TERRACE_END, -s, last["bottom"], "sh_rubble" )
    gable_skews( model, face, -s * TERRACE_END, last["eave"], -s, paint="sh_timber_tar", over=6.0 )
    return units


# ---------------------------------------------------------------------------------------------------------------------
# The rocky points that end the beach

# The rocky point. The barrier's blocks along the beach keep their beach faces at |e| >= FRONT at the floor, leaning
# back above it too steeply to stand on, with their tops LEDGE or more over anything a player can stand on in front of
# them (a mantle reaches 94); the crag stands over the seawall's parapet; the rest lie out in the loch behind them.
LEDGE = 100.0


def seabed_floor( n ):
    """ What a player could stand on south of the seawall: the beach, then the bed falling to -300 at n -2100. """
    if n >= BEACH_N0:
        return beach_z( n )
    return BEACH_FOOT - ( BEACH_N0 - n ) * 110.0 / 340.0


def crest( n ):
    """ The barrier's tops along the beach, falling towards the loch. """
    return float( np.interp( n, ( -2160, -1900, -1760, -1600, -1470 ), ( -64, -46, -32, -10, 14 ) ) )


# The crag's blocks: ( out from FRONT, to, n from, to, top, turn, dip out, dip n, face lean, face turn ). A face turned
# t per inch of n is held at FRONT at the block's north end (the seawall's) and leans back from the parapet's level.
CRAG = (
    ( -60, 160, -1490, -1300, 122, 4, -0.10, 0.06, 0.06, -0.12 ),
    ( 60, 320, -1470, -1300, 112, -7, 0.15, 0.25, 0.10, 0.0 ),
    ( -60, 110, -1610, -1460, 64, 8, -0.15, 0.32, 0.18, -0.20 ),
    ( 180, 420, -1580, -1330, 82, 12, 0.32, 0.25, 0.10, 0.0 ),
    ( 110, 280, -1650, -1520, 30, -15, 0.25, 0.30, 0.10, 0.0 ),
)
PARAPET = -10.0                 # the seawall's parapet, the highest thing a player stands on by the crag


def rocky_point( model, side ):
    """ The bay's rocky point on one side: the crag against the seawall's end and the terrace's gable, the barrier of
    leaning slabs along the beach stepping down into the loch, and the reef of tilted blocks behind them out into the
    loch, wrack below the tide line. Every block collides. Returns their points. """
    s, out = side, []
    for k, ( e0, e1, n0, n1, top, turn, dip_out, dip_n, lean, face ) in enumerate( CRAG ):
        key = ( "crag", s, k )
        lo = -420.0
        centre = ( s * ( FRONT + ( e0 + e1 ) / 2 ), ( n0 + n1 ) / 2, ( lo + top + 60 ) / 2 )
        out.append( rock( model, centre, ( e1 - e0, n1 - n0, top + 60 - lo ), key, top=top, turn=s * turn,
                          dip=( s * dip_out, dip_n ), n_max=TERRACE_N0 - 2.0, lean=( 0.0, 0.0 ), cap=36.0,
                          clamp=( s, FRONT, lean, PARAPET, face, min( n1, TERRACE_N0 - 2.0 ) ) ) )
    n, k = -2170.0, 0
    while n < -1470:
        # Jointed slabs: each face turned its own way in plan and leaning back its own amount, each top tilted the
        # other way from the last's, so the skyline is a saw and the face a run of facets.
        key = ( "barrier", s, k )
        n0, n1 = n, min( n + between( 60, 125, *key, "len" ), -1440.0 )
        half = ( n1 - n0 ) / 2
        floor = max( seabed_floor( q ) for q in np.linspace( n0 - 25, n1 + 25, 9 ) )
        lowest = min( seabed_floor( q ) for q in np.linspace( n0 - 25, n1 + 25, 9 ) )
        tilt = ( 1 if k % 2 else -1 ) * between( 0.2, 0.5, *key, "dipn" )
        top = max( crest( n0 + half ) + between( -6, 24, *key, "top" ), floor + LEDGE + 45 + abs( tilt ) * half )
        depth = between( 170, 330, *key, "depth" )
        turn_n = between( -0.32, 0.32, *key, "face" )
        e_face = FRONT + between( 0, 4, *key, "off" ) + abs( turn_n ) * half
        lo = -430.0
        centre = ( s * ( FRONT - 80 + ( depth + 80 ) / 2 ), n0 + half, ( lo + top + 80 ) / 2 )
        out.append( rock( model, centre, ( depth + 80, n1 - n0, top + 80 - lo ), key, top=top,
                          turn=between( -10, 10, *key, "turn" ),
                          dip=( -s * between( 0.12, 0.35, *key, "dipe" ), tilt ),
                          clamp=( s, e_face, between( 0.12, 0.30, *key, "k" ), lowest, turn_n, n0 + half ),
                          lean=( 0.0, 0.0 ), n_max=TERRACE_N0 - 2.0 ) )
        if n1 >= -1440.0:
            break
        n, k = n1 - between( 30, 46, *key, "lap" ), k + 1
    # The reef: a tongue of tilted blocks running out south-east from the crag, awash at its end.
    root, tip = np.array( ( FRONT + 260, -1520 ) ), np.array( ( FRONT + 1150, -2330 ) )
    axis = tip - root
    length = float( np.linalg.norm( axis ) )
    along, across = axis / length, np.array( ( axis[1], -axis[0] ) ) / length
    k = 0
    for i in range( 9 ):
        for j in range( -2, 3 ):
            key = ( "reef", s, i, j )
            u = ( i + 0.5 + between( -0.3, 0.3, *key, "u" ) ) / 9
            width = 520 * ( 1 - u ) + 200 * u
            v = ( j + between( -0.35, 0.35, *key, "v" ) ) / 4.4
            if abs( v ) > 0.5 or not chance( 0.8, *key ):
                continue
            e, n = root + along * u * length + across * v * width
            size = ( between( 150, 290, *key, "a" ) * ( 1.1 - 0.4 * u ), between( 110, 230, *key, "b" ) * ( 1.1 - 0.4 * u ) )
            top = lerp( 55, -235, u ) + between( -25, 25, *key, "top" ) - 60 * abs( v )
            lo = top - between( 160, 240, *key, "lo" )
            out.append( rock( model, ( s * e, n, ( lo + top + 50 ) / 2 ), ( size[0], size[1], top + 50 - lo ), key,
                              top=top, turn=between( -40, 40, *key, "turn" ),
                              dip=( between( -0.45, 0.45, *key, "de" ), between( -0.45, 0.2, *key, "dn" ) ),
                              clamp=( s, FRONT + 120 ), n_max=TERRACE_N0 - 30.0 ) )
            k += 1
    return out


def edge_blocks( side ):
    """ One side's play edge, with collision: the terrace up its brae and the rocky point below it. """
    model = K.Model()
    terrace( model, side )
    rocky_point( model, side )
    return configure( model )


# ---------------------------------------------------------------------------------------------------------------------
# Fields of noise, and paths

def _hash01( ix, iy, seed ):
    h = ( ix * 374761393 + iy * 668265263 + seed * 2246822519 ) & 0xffffffff
    h = ( ( h ^ ( h >> 13 ) ) * 1274126177 ) & 0xffffffff
    return ( h ^ ( h >> 16 ) ) / 4294967296.0


def vnoise( e, n, scale, key ):
    """ Smooth value noise in -1..1 for arrays, its lattice turned by the key so no two fields line up. """
    seed = zlib.crc32( str( key ).encode() ) & 0xffff
    turn = ( seed % 628 ) / 100.0
    e, n = np.asarray( e, float ), np.asarray( n, float )
    x = ( e * math.cos( turn ) - n * math.sin( turn ) ) / scale
    y = ( e * math.sin( turn ) + n * math.cos( turn ) ) / scale
    x0, y0 = np.floor( x ), np.floor( y )
    fx, fy = x - x0, y - y0
    fx, fy = fx * fx * ( 3 - 2 * fx ), fy * fy * ( 3 - 2 * fy )
    ix, iy = x0.astype( np.int64 ), y0.astype( np.int64 )
    a, b = _hash01( ix, iy, seed ), _hash01( ix + 1, iy, seed )
    c, d = _hash01( ix, iy + 1, seed ), _hash01( ix + 1, iy + 1, seed )
    return ( ( a + ( b - a ) * fx ) * ( 1 - fy ) + ( c + ( d - c ) * fx ) * fy ) * 2 - 1


def vfractal( e, n, scale, key, octaves=3 ):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range( octaves ):
        total = total + amp * vnoise( e, n, scale / 2 ** o, f"{key}{o}" )
        norm += amp
        amp *= 0.5
    return total / norm


def sstep( t ):
    t = np.clip( t, 0.0, 1.0 )
    return t * t * ( 3 - 2 * t )


class Route:
    """ A polyline in plan, resampled every step inches, with a k-d tree over the samples: the distance to it, how far
    along it the nearest point is and which side of it a point lies (+1 to the left of its direction). """

    def __init__( self, points, step=10.0 ):
        from scipy.spatial import cKDTree
        pts = np.asarray( points, float )[:, :2]
        keep = np.concatenate( ( [ True ], np.linalg.norm( np.diff( pts, axis=0 ), axis=1 ) > 1e-6 ) )
        pts = pts[keep]
        s = np.concatenate( ( [ 0.0 ], np.cumsum( np.linalg.norm( np.diff( pts, axis=0 ), axis=1 ) ) ) )
        self.length = float( s[-1] )
        self.s = np.linspace( 0.0, self.length, max( 2, int( math.ceil( self.length / step ) ) + 1 ) )
        self.xy = np.stack( ( np.interp( self.s, s, pts[:, 0] ), np.interp( self.s, s, pts[:, 1] ) ), axis=1 )
        tangent = np.gradient( self.xy, axis=0 )
        self.tangent = tangent / np.maximum( np.linalg.norm( tangent, axis=1 ), 1e-9 )[:, None]
        # The tree holds every stride-th sample (about every 80 inches): far points search a long thin cloud slowly
        self.stride = max( 1, int( round( 80.0 / step ) ) )
        self.tree = cKDTree( self.xy[::self.stride] )
        self.lo, self.hi = self.xy.min( axis=0 ), self.xy.max( axis=0 )

    def query( self, e, n ):
        """ ( distance, arc length, side ) for each point: exact against the two segments beside the nearest sample. """
        shape = np.shape( e )
        p = np.stack( ( np.ravel( np.asarray( e, float ) ), np.ravel( np.asarray( n, float ) ) ), axis=1 )
        if not len( p ):
            return np.zeros( shape ), np.zeros( shape ), np.ones( shape )
        _, k = self.tree.query( p, workers=-1 )
        k = k * self.stride
        # The nearest sample in the coarse sample's neighbourhood
        near = np.full( len( p ), np.inf )
        found = k.copy()
        last = len( self.xy ) - 1
        for off in range( -self.stride, self.stride + 1 ):
            kk = np.clip( k + off, 0, last )
            d2 = ( ( p - self.xy[kk] ) ** 2 ).sum( 1 )
            better = d2 < near
            near = np.where( better, d2, near )
            found = np.where( better, kk, found )
        k = found
        best = np.full( len( p ), np.inf )
        along = np.zeros( len( p ) )
        for a_off in ( -1, 0 ):
            a = np.clip( k + a_off, 0, len( self.xy ) - 2 )
            pa, pb = self.xy[a], self.xy[a + 1]
            ab = pb - pa
            t = np.clip( ( ( p - pa ) * ab ).sum( 1 ) / np.maximum( ( ab * ab ).sum( 1 ), 1e-12 ), 0.0, 1.0 )
            d = np.linalg.norm( p - ( pa + t[:, None] * ab ), axis=1 )
            better = d < best
            best = np.where( better, d, best )
            along = np.where( better, self.s[a] + t * ( self.s[a + 1] - self.s[a] ), along )
        tan = self.tangent[k]
        rel = p - self.xy[k]
        side = np.where( tan[:, 0] * rel[:, 1] - tan[:, 1] * rel[:, 0] >= 0, 1.0, -1.0 )
        return best.reshape( shape ), along.reshape( shape ), side.reshape( shape )

    def near( self, e, n, reach ):
        """ Which points lie within reach of the path's bounding box (a cheap first cut before query). """
        e, n = np.asarray( e, float ), np.asarray( n, float )
        return ( e > self.lo[0] - reach ) & ( e < self.hi[0] + reach ) & ( n > self.lo[1] - reach ) & ( n < self.hi[1] + reach )

    def at( self, s ):
        s = np.clip( np.asarray( s, float ), 0.0, self.length )
        return np.stack( ( np.interp( s, self.s, self.xy[:, 0] ), np.interp( s, self.s, self.xy[:, 1] ) ), axis=-1 )

    def direction( self, s ):
        s = np.clip( np.asarray( s, float ), 0.0, self.length )
        t = np.stack( ( np.interp( s, self.s, self.tangent[:, 0] ), np.interp( s, self.s, self.tangent[:, 1] ) ), axis=-1 )
        return t / np.maximum( np.linalg.norm( t, axis=-1, keepdims=True ), 1e-9 )

    def left( self, s ):
        """ The unit normal to the left of the path's direction at s. """
        t = self.direction( s )
        return np.stack( ( -t[..., 1], t[..., 0] ), axis=-1 )


def smooth_path( points, step=150.0 ):
    """ A path through its points as a Catmull-Rom curve sampled about every step inches ( P, 2 ). """
    pts = np.asarray( points, float )
    pts = np.vstack( ( 2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2] ) )
    out = []
    for i in range( 1, len( pts ) - 2 ):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        count = max( 2, int( np.linalg.norm( p2 - p1 ) / step ) )
        for t in np.arange( count ) / count:
            out.append( 0.5 * ( 2 * p1 + ( p2 - p0 ) * t + ( 2 * p0 - 5 * p1 + 4 * p2 - p3 ) * t * t
                                + ( 3 * p1 - p0 - 3 * p2 + p3 ) * t ** 3 ) )
    out.append( pts[-2] )
    return np.array( out )


# ---------------------------------------------------------------------------------------------------------------------
# The coast and the lie of the land

# The bay's shore, west to east ( e, n ), at the beach's foot (z -190): straight across the play area, the rocky points'
# roots, the village shores curving south to the headlands (the lighthouse's in the south-west, the one off the islet
# in the south-east), then the loch's north shore running on to the loch's heads.
COAST = (
    ( -98000, -6200 ), ( -60000, -6500 ), ( -40000, -7600 ), ( -26000, -8800 ), ( -20000, -10200 ), ( -17500, -11500 ),
    ( -16300, -12200 ), ( -15500, -12100 ), ( -14900, -11500 ), ( -13800, -10000 ), ( -12500, -8200 ), ( -11000, -6400 ),
    ( -9500, -4900 ), ( -8000, -3700 ), ( -6500, -2750 ), ( -5000, -2050 ), ( -4100, -1780 ), ( -3500, -1690 ),
    ( -3000, -1700 ), ( -2500, -1760 ), ( 2500, -1760 ), ( 3000, -1700 ), ( 3600, -1690 ), ( 4200, -1760 ),
    ( 5000, -1950 ), ( 6500, -2550 ), ( 8000, -3400 ), ( 9500, -4600 ), ( 11000, -6100 ), ( 12300, -7600 ),
    ( 13300, -8900 ), ( 14200, -9200 ), ( 16000, -8800 ), ( 20000, -7600 ), ( 30000, -6000 ), ( 45000, -5200 ),
    ( 60000, -4500 ), ( 98000, -3800 ),
)
COAST_E = np.array( [ p[0] for p in COAST ], float )
COAST_N = np.array( [ p[1] for p in COAST ], float )
CENTRE_E = 2500.0               # the coast keeps the beach's line to here, so the play area's edges stay true


def coast_n( e ):
    """ The shore's n at each e: the table, wandering a little away from the play area. """
    e = np.asarray( e, float )
    n = np.interp( e, COAST_E, COAST_N )
    away = np.clip( ( np.abs( e ) - CENTRE_E ) / 1500.0, 0.0, 1.0 )
    return n + away * ( 90.0 * np.sin( e / 830.0 + 1.3 ) + 55.0 * np.sin( e / 290.0 + 0.4 ) + 25.0 * np.sin( e / 113.0 ) )


def coast_points():
    es = [ np.arange( a, b, 20.0 if max( abs( a ), abs( b ) ) < 30000 else 60.0 ) for a, b in zip( COAST_E[:-1], COAST_E[1:] ) ]
    es = np.concatenate( es + [ COAST_E[-1:] ] )
    return np.stack( ( es, coast_n( es ) ), axis=1 )


# Across the loch: the far shore's waterline. The west part runs from the west loch head (where it meets this shore)
# along the far side and down the west side of the loch's mouth; the east part up the mouth's east side and along to
# the east loch head. Between them the mouth opens south to the sea, with a long low island far out in it.
FAR_WEST = ( ( -75000, -6400 ), ( -74000, -12000 ), ( -68000, -20000 ), ( -55000, -25500 ), ( -50000, -26500 ),
             ( -35000, -24500 ), ( -22000, -25500 ), ( -10000, -24000 ), ( 0, -25000 ), ( 8000, -24500 ),
             ( 14000, -26500 ), ( 17500, -29500 ), ( 19500, -36000 ), ( 20500, -52000 ), ( 20000, -100000 ) )
FAR_EAST = ( ( 43000, -100000 ), ( 44000, -52000 ), ( 45500, -36000 ), ( 48500, -30500 ), ( 55000, -28500 ),
             ( 65000, -27000 ), ( 72000, -22000 ), ( 76000, -12000 ), ( 77000, -4200 ) )
FAR_ISLAND = ( 31000.0, -74000.0, 6500.0, 2600.0 )        # centre e, n, half length (e), half width (n)
ISLET = ( 16700.0, -16700.0, 1200.0, 800.0 )               # centre e, n, half length (e), half width (n)
SIGHT = 100000.0                                           # the camera's far clip: nothing past it is drawn


def sea_depth( s ):
    """ How far the seabed lies under the beach's foot, s inches out from the shore: -300 at the pier head, -500 by
    n -3000, about -1500 out in the loch. """
    s = np.maximum( np.asarray( s, float ), 0.0 )
    return np.where( s <= 300.0, s / 3.0, 100.0 + 1200.0 * ( 1.0 - np.exp( -( s - 300.0 ) / 4800.0 ) ) )


# The land's rise with its distance from the shore: the beach, the raised beach's shelf the villages stand on, the in-bye
# land, then the moor up to the ridge 125-175 m over the loch about a kilometre inland (the knolls give the tops), a dip
# and the next ridge behind.
HILL_D = ( 0, 30, 120, 200, 600, 1500, 3610, 4760, 7760, 11760, 17760, 25760, 35760, 43760, 52000, 70000, 120000 )
HILL_Z = ( -190, -170, -105, -52, -40, 0, 48, 80, 240, 600, 1250, 2300, 3600, 5000, 4700, 5300, 6000 )


def hills( e, n, d ):
    """ The hills: the rise inland, broad swells, rounded knolls on the tops, and hummocks that soften further up, where
    the mesh is coarse and they would only make spikes. """
    d = np.maximum( np.asarray( d, float ), 0.0 )
    z = np.interp( d, HILL_D, HILL_Z )
    inland = np.clip( ( d - 900.0 ) / 3000.0, 0.0, 1.0 )
    out = np.maximum( d - 900.0, 0.0 )
    soft = 0.35 + 0.65 * ( 1.0 - sstep( ( d - 6000.0 ) / 8000.0 ) )
    lumps = vfractal( e, n, 3200.0, "lumps", 3 ) * np.minimum( 25.0 + 0.016 * out, 420.0 ) * soft
    broad = vfractal( e, n, 9000.0, "broad", 2 ) * np.minimum( 0.03 * out, 900.0 )
    swell = vfractal( e, n, 14000.0, "swell", 2 ) * 0.035 * np.maximum( d - 2500.0, 0.0 )
    k = np.maximum( vfractal( e, n, 7000.0, "knolls", 2 ) - 0.12, 0.0 )
    knolls = 2000.0 * np.tanh( k * k * 0.3 * np.maximum( d - 4000.0, 0.0 ) / 2000.0 )
    return z + inland * ( 1600.0 * np.tanh( ( lumps + broad + swell ) / 1600.0 ) + knolls )


def brae_levels( n ):
    """ brae_z for arrays. """
    return np.interp( n, ( -1350, -1120, -600, 400, 880, 1960 ), ( WALK, WALK, YARD, YARD, ROAD, ROAD ) )


def seabed_floors( n ):
    """ seabed_floor for arrays. """
    n = np.asarray( n, float )
    return np.where( n >= BEACH_N0, BEACH_TOP + ( BEACH_FOOT - BEACH_TOP ) * np.clip( ( -1350.0 - n ) / 410.0, 0, 1 ),
                     BEACH_FOOT - ( BEACH_N0 - n ) * 110.0 / 340.0 )


# The roads: the shore road through both villages and round the back of the distillery, the hill road up past the farm,
# the farm's track. ( points, half width, paint )
SHORE_ROAD = ( ( -13500, -8600 ), ( -11000, -5900 ), ( -8600, -3800 ), ( -6600, -2450 ), ( -5000, -1700 ), ( -3800, -1420 ),
               ( -2950, -1300 ), ( -2700, -900 ), ( -2700, 400 ), ( -2900, 1500 ), ( -2800, 1950 ), ( -2450, 2070 ),
               ( 0, 2070 ), ( 2450, 2070 ), ( 2800, 1950 ), ( 2900, 1500 ), ( 2700, 400 ), ( 2700, -900 ), ( 2950, -1300 ),
               ( 3800, -1400 ), ( 5000, -1650 ), ( 6600, -2250 ), ( 8400, -3250 ), ( 10500, -4900 ), ( 12500, -6900 ) )
HILL_ROAD = ( ( 600, 2070 ), ( 700, 3200 ), ( 300, 4400 ), ( 900, 5600 ), ( 600, 7000 ), ( 1500, 8600 ), ( 1100, 10500 ),
              ( 2300, 12800 ), ( 1700, 15500 ), ( 3000, 19000 ), ( 2400, 23000 ), ( 3800, 28000 ), ( 3200, 34000 ),
              ( 4600, 41000 ), ( 4200, 48000 ) )
FARM_TRACK = ( ( 640, 3600 ), ( 1500, 4300 ), ( 2300, 4980 ), ( 2620, 5160 ) )
LIGHT_TRACK = ( ( -13500, -8600 ), ( -14450, -10150 ), ( -15150, -11150 ), ( -15560, -11520 ) )
ROAD_HALF = 70.0                # a single-track road, 3.6 m
TRACK_HALF = 45.0
SHOULDER = 120.0                # the ground eases into a road's level over this
# The burn: from the lochan over its dam down past the east village to the shore. The lochan: centre e, n, half sizes.
BURN = ( ( 4600, 10200 ), ( 4600, 9700 ), ( 4520, 8400 ), ( 4300, 6500 ), ( 4100, 5000 ), ( 4250, 3600 ), ( 4000, 2300 ),
         ( 4300, 900 ), ( 4650, -400 ), ( 4950, -1400 ), ( 5150, -2300 ) )
BURN_DEPTH = 24.0
LOCHAN = ( 4600.0, 10400.0, 1200.0, 600.0 )
DAM_N = 9810.0                  # the dam's upstream face; its toe is 110 further south
FARM = ( 2600.0, 5400.0 )
KIRK = ( 7400.0, -1150.0 )
LIGHTHOUSE = ( -15700.0, -11750.0 )
PLANTATION = ( ( -9600, 9200 ), ( -4300, 8400 ), ( -3800, 14200 ), ( -8800, 15600 ) )
LAND_CUT = 56000.0              # the land past this far inland is behind the ridge


# ---------------------------------------------------------------------------------------------------------------------
# The world: the coast, the roads, the burn, the buildings' pads, and the ground's height everywhere

class World:
    """ Everything the land, the seabed and the far shore are shaped from, worked out once (world()). """


_WORLD = []
HEAD_RAY = 60000.0               # how far past the loch's heads the far shore's paths run on, straight


def world():
    if not _WORLD:
        _WORLD.append( build_world() )
    return _WORLD[0]


def far_side( W, e, n ):
    """ How far into the far shore's land each point is ( > 0 on the far land, < 0 in the loch ), the nearer of its two
    parts. """
    best = np.full( np.shape( e ), -np.inf )
    for route in ( W.far_west, W.far_east ):
        dist, _, side = route.query( e, n )
        best = np.maximum( best, -side * dist )
    return best


def ellipse_out( e, n, shape ):
    """ About how far outside an ellipse ( centre e, n, half sizes ) each point is (negative inside). """
    ce, cn, a, b = shape
    r = np.sqrt( ( ( np.asarray( e ) - ce ) / a ) ** 2 + ( ( np.asarray( n ) - cn ) / b ) ** 2 )
    return ( r - 1.0 ) * min( a, b ), r


def shoal( out ):
    """ The bed round an island or under the far shore: SEA_Z - 30 at its waterline, falling off out into the loch, and
    on down under the land so it never shows through. """
    out = np.asarray( out, float )
    return np.where( out >= 0, SEA_Z - 30.0 - sea_depth( out * 1.2 ), SEA_Z - 40.0 + out * 0.3 )


def base_height( W, e, n, d ):
    """ The lie of the land before anything is built on it: the hills on this shore, the loch's bed (rising to the far
    shore, the islet and the far island). d is the distance from this shore, + on the land. """
    land = hills( e, n, d )
    sea = BEACH_FOOT - sea_depth( np.maximum( -d, 0.0 ) )
    sea = np.maximum( sea, shoal( -far_side( W, e, n ) ) )
    for shape in ( ISLET, FAR_ISLAND ):
        sea = np.maximum( sea, shoal( ellipse_out( e, n, shape )[0] ) )
    return np.where( d >= 0, land, sea )


def ground( W, e, n, upto=99, info=None ):
    """ The ground's height at each point, in stages: 1 the lie of the land, 2 the rocky points, 3 the braes' levels
    carried round the terraces' backs and the play area's north side, 4 the lochan, 5 the roads, 6 the buildings' pads,
    7 the burn. info (a dict) gets the coast distance and the roads' weights. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    dist, _, side = W.coast.query( e, n )
    d = dist * side
    z = base_height( W, e, n, d )
    ae = np.abs( e )
    if upto >= 2:
        rocky = ( ae < 2600 ) & ( n < TERRACE_N0 )
        z = np.where( rocky, np.minimum( z, seabed_floors( np.maximum( n, -2100.0 ) ) + 1.5 * np.maximum( ae - 2160.0, 0.0 ) ), z )
    if upto >= 3:
        north = n >= TERRACE_N0
        wn = 1.0 - sstep( np.maximum( np.maximum( ae - 2900.0, n - 1930.0 ), 0.0 ) / 750.0 )
        ws = ( 1.0 - sstep( np.maximum( ae - 2900.0, 0.0 ) / 750.0 ) ) * ( 1.0 - sstep( ( TERRACE_N0 - n ) / 150.0 ) ) \
            * sstep( ( ae - 2350.0 ) / 150.0 )
        w = np.where( north, wn, ws )
        z = z + ( brae_levels( np.minimum( n, 1960.0 ) ) - 2.0 - z ) * w
    if upto >= 4 and getattr( W, "lochan_level", None ) is not None:
        _, r = ellipse_out( e, n, LOCHAN )
        level = W.lochan_level
        bed = level - 4.0 - 60.0 * ( 1.0 - np.minimum( r, 1.0 ) ** 2 )
        shore = level + 6.0 + ( r - 1.0 ) * 150.0
        z = np.where( r < 1.0, bed, np.where( r < 2.2, shore + ( z - shore ) * sstep( ( r - 1.0 ) / 1.2 ), z ) )
    road_w = np.zeros( np.shape( e ) )
    if upto >= 5:
        for road in W.roads:
            near = road.route.near( e, n, road.half + SHOULDER + 10.0 )
            if not near.any():
                continue
            dist_r, along, _ = road.route.query( e[near], n[near] )
            level = np.interp( along, road.s, road.z )
            w = 1.0 - sstep( ( dist_r - road.half ) / SHOULDER )
            z[near] = z[near] + ( level - z[near] ) * w
            road_w[near] = np.maximum( road_w[near], w )
    if upto >= 6:
        for pad in W.pads:
            near = ( np.abs( e - pad["centre"][0] ) < pad["reach"] ) & ( np.abs( n - pad["centre"][1] ) < pad["reach"] )
            if not near.any():
                continue
            rel = np.stack( ( e[near] - pad["centre"][0], n[near] - pad["centre"][1] ), axis=1 )
            x, y = np.abs( rel @ pad["axis"] ), np.abs( rel @ pad["across"] )
            outside = np.hypot( np.maximum( x - pad["half"][0], 0.0 ), np.maximum( y - pad["half"][1], 0.0 ) )
            w = ( 1.0 - sstep( ( outside - pad["margin"] ) / pad["blend"] ) ) * ( 1.0 - road_w[near] )
            z[near] = z[near] + ( pad["level"] - z[near] ) * w
    if upto >= 7 and getattr( W, "burn_bed", None ) is not None:
        near = W.burn.near( e, n, 1200.0 )
        if near.any():
            dist_b, along, _ = W.burn.query( e[near], n[near] )
            bed = np.interp( along, W.burn_s, W.burn_bed )
            z[near] = np.minimum( z[near], bed + np.maximum( dist_b - 30.0, 0.0 ) * 0.6 )
    if info is not None:
        info["d"] = d
        info["road"] = road_w
    return z


class Road:
    def __init__( self, points, half, paint, step=140.0 ):
        self.route = Route( smooth_path( points, step ), 10.0 )
        self.half, self.paint = half, paint
        self.s = self.z = None


def road_profile( W, road ):
    """ The road's level along it: the ground under it (with the roads before it), smoothed over 600. """
    s = np.arange( 0.0, road.route.length + 50.0, 50.0 )
    s[-1] = road.route.length
    p = road.route.at( s )
    z = ground( W, p[:, 0], p[:, 1], upto=5 )
    window = 13
    padded = np.pad( z, window // 2, mode="edge" )
    road.s, road.z = s, np.convolve( padded, np.ones( window ) / window, mode="valid" )


def head_ray( path, at_start, length=HEAD_RAY ):
    """ A far shore's path carried on straight past the loch's head, its start's tangent back (at_start) or its end's on,
    so far_side has no seam along the line through the head: past a path's end the side would flip across it. """
    p = np.asarray( path, float )
    if at_start:
        t = p[1] - p[0]
        return np.vstack( ( p[0] - t / np.linalg.norm( t ) * length, p ) )
    t = p[-1] - p[-2]
    return np.vstack( ( p, p[-1] + t / np.linalg.norm( t ) * length ) )


def build_world():
    started = time.time()
    W = World()
    W.coast = Route( coast_points(), 10.0 )
    W.croft = Route( smooth_path( CROFT_LINE, 200.0 ), 20.0 )
    W.far_west = Route( head_ray( smooth_path( FAR_WEST, 800.0 ), at_start=True ), 40.0 )
    W.far_east = Route( head_ray( smooth_path( FAR_EAST, 800.0 ), at_start=False ), 40.0 )
    W.roads, W.pads, W.lochan_level, W.burn_bed = [], [], None, None
    W.lochan_level = float( ground( W, np.array( [ LOCHAN[0] ] ), np.array( [ LOCHAN[1] ] ), upto=3 )[0] ) - 15.0
    for points, half, paint in ( ( SHORE_ROAD, ROAD_HALF, "sh_tarmac" ), ( HILL_ROAD, ROAD_HALF, "sh_tarmac" ),
                                 ( FARM_TRACK, TRACK_HALF, "sh_shingle" ), ( LIGHT_TRACK, TRACK_HALF, "sh_shingle" ) ):
        road = Road( points, half, paint )
        road_profile( W, road )
        W.roads.append( road )
    W.burn = Route( smooth_path( BURN, 120.0 ), 10.0 )
    W.buildings = village_plan( W )
    W.pads = [ b["pad"] for b in W.buildings if b.get( "pad" ) ]
    s = np.arange( 0.0, W.burn.length + 20.0, 20.0 )
    s[-1] = W.burn.length
    p = W.burn.at( s )
    z = ground( W, p[:, 0], p[:, 1], upto=6 ) - BURN_DEPTH
    _, r = ellipse_out( p[:, 0], p[:, 1], LOCHAN )
    z = np.where( r < 1.05, np.minimum( z, W.lochan_level - 40.0 ), z )
    W.burn_bed = np.minimum.accumulate( z )
    W.burn_s = s
    W.crofts = croft_plan( W )
    W.built_in = time.time() - started
    return W


def pad( centre, axis, half, level, margin=60.0, blend=190.0 ):
    """ A building's level ground: an oriented rectangle ( half sizes along axis and across it ) held at level, easing
    back into the land over blend beyond margin. """
    axis = np.asarray( axis, float ) / np.linalg.norm( axis )
    return dict( centre=np.asarray( centre, float ), axis=axis, across=np.array( ( -axis[1], axis[0] ) ),
                 half=np.asarray( half, float ), level=float( level ), margin=margin, blend=blend,
                 reach=float( np.hypot( *half ) + margin + blend ) )


# ---------------------------------------------------------------------------------------------------------------------
# Where the village's buildings stand

HOUSE_HARLS = ( "sh_harl", "sh_harl", "sh_harl_cream", "sh_harl", "sh_harl_shade", "sh_harl", "sh_harl_mould",
                "sh_harl_cream", "sh_harl" )
HOUSE_DOORS = ( "sh_paint_door", "sh_paint_blue", "sh_paint_red", "sh_paint_yellow", "sh_paint_black", "sh_paint_door",
                "sh_paint_blue", "sh_paint_red" )
HOUSE_MARGINS = ( "sh_tar_black", "sh_tar_black", "sh_tar_black", "sh_paint_blue", "sh_tar_black", "sh_paint_door",
                  "sh_tar_black", "sh_paint_red" )
INN_E = -4300.0                 # the inn takes the first row west of this along the west village's road
VILLAGE_E = ( 3080.0, 11200.0 ) # the villages' houses along the shore road, |e| from, to
OUTSHOT = 130.0                 # a lean-to's depth behind a house
GRAVEYARD = ( 1100.0, 800.0 )   # the kirk's walled graveyard, centred on it


def house_look( key, kind="house" ):
    return dict( harl=pick( HOUSE_HARLS, *key, "harl" ), door=pick( HOUSE_DOORS, *key, "door" ),
                 margin=pick( HOUSE_MARGINS, *key, "margin" ), panes=pick( ( 6, 6, 2 ), *key, "panes" ),
                 roof=pick( ( "wallhead", "plain", "lights", "plain", "wallhead" ), *key, "roof" ),
                 cans=pick( ( 2, 3, 3, 4 ), *key, "cans" ), kind=kind )


def building( kind, centre, out, width, depth, level, key, look=None, storeys=1.5, margin=60.0, blend=190.0, **extra ):
    """ A building's plan: its centre, which way its front faces (out), its width along the front and depth, the
    ground level its pad holds and its floor 6 over that. """
    out = np.asarray( out, float ) / np.linalg.norm( out )
    axis = np.array( ( -out[1], out[0] ) )
    b = dict( kind=kind, centre=np.asarray( centre, float ), out=out, axis=axis, width=float( width ),
              depth=float( depth ), floor=float( level ) + 6.0, level=float( level ), key=key,
              look=look or house_look( key, kind ), storeys=storeys, **extra )
    b["pad"] = pad( centre, axis, ( width / 2, depth / 2 ), level, margin, blend )
    return b


def footprint_level( W, centre, out, width, depth ):
    """ The ground over a footprint (with the roads): its mean, its highest and its lowest. """
    out = np.asarray( out, float ) / np.linalg.norm( out )
    axis = np.array( ( -out[1], out[0] ) )
    pts = np.array( [ np.asarray( centre, float ) + axis * a * width / 2 + out * b * depth / 2
                      for a in ( -1, -0.5, 0, 0.5, 1 ) for b in ( -1, 0, 1 ) ] )
    z = ground( W, pts[:, 0], pts[:, 1], upto=5 )
    return float( z.mean() ), float( z.max() ), float( z.min() )


def clear_of( W, centre, half, built ):
    """ Whether a footprint ( centre, a radius ) keeps clear of the burn, the other buildings and the terraces. """
    dist, _, _ = W.burn.query( np.array( [ centre[0] ] ), np.array( [ centre[1] ] ) )
    if dist[0] < half + 230.0:
        return False
    if abs( centre[0] ) < BACK + half + 80.0 and centre[1] > -1500.0:
        return False
    for b in built:
        if np.linalg.norm( b["centre"] - centre ) < half + b.get( "clear", 0.5 * math.hypot( b["width"], b["depth"] ) ) + 40.0:
            return False
    return True


def landward( W, a, b ):
    """ The unit normal to the chord a-b on the land's side (away from the coast). """
    t = ( b - a ) / np.linalg.norm( b - a )
    left = np.array( ( -t[1], t[0] ) )
    mid = ( a + b ) / 2
    probe = mid + left * 400.0
    dp, _, sp = W.coast.query( np.array( [ probe[0], mid[0] ] ), np.array( [ probe[1], mid[1] ] ) )
    return left if dp[0] * sp[0] > dp[1] * sp[1] else -left


def village_rows( W, built ):
    """ The cottages and houses in rows along the shore road's landward side through both villages, facing the road
    and the loch beyond it, with the inn in the west village. """
    road = W.roads[0].route
    for side in ( 1, -1 ):
        inside = ( side * road.xy[:, 0] >= VILLAGE_E[0] ) & ( side * road.xy[:, 0] <= VILLAGE_E[1] ) & ( road.xy[:, 1] < 0 )
        s_lo, s_hi = float( road.s[inside].min() ), float( road.s[inside].max() )
        way = 1.0 if side > 0 else -1.0         # out from the play area along the road
        s = s_lo if side > 0 else s_hi
        k = 0
        inn_done = False
        while ( s < s_hi - 300 ) if side > 0 else ( s > s_lo + 300 ):
            key = ( "row", side, k )
            k += 1
            inn = side < 0 and not inn_done and float( road.at( s )[0] ) < INN_E
            count = 1 if inn else pick( ( 1, 2, 2, 3, 3, 4, 2 ), *key, "count" )
            widths = [ 560.0 ] if inn else [ between( 290, 420, *key, j, "w" ) for j in range( count ) ]
            total = sum( widths )
            a, b = road.at( s ), road.at( s + way * total )
            if np.linalg.norm( b - a ) < 0.5 * total:
                break
            t = ( b - a ) / np.linalg.norm( b - a )
            left = landward( W, a, b )
            setback = ROAD_HALF + between( 70, 140, *key, "set" )
            # Keep the row's front clear of the road where it bends away from the chord
            front = np.array( [ a + ( b - a ) * f + left * setback for f in np.linspace( 0, 1, 7 ) ] )
            fd, _, _ = road.query( front[:, 0], front[:, 1] )
            setback += max( 0.0, ROAD_HALF + 50.0 - float( fd.min() ) )
            depth = 300.0 if inn else MAIN
            x, row = 0.0, []
            for j, width in enumerate( widths ):
                row.append( ( ( "house", side, k, j ), a + t * ( x + width / 2 ) + left * ( setback + depth / 2 ), width ) )
                x += width
            ok = all( clear_of( W, c, 0.5 * math.hypot( w, depth ), built ) for _, c, w in row )
            if ok:
                for hkey, centre, width in row:
                    mean, high, low = footprint_level( W, centre, -left, width, depth )
                    level = max( mean, high - 30.0 )
                    if inn:
                        look = dict( house_look( hkey, "inn" ), harl="sh_harl", door="sh_paint_black",
                                     margin="sh_tar_black", roof="wallhead", cans=4, panes=6 )
                        built.append( building( "inn", centre, -left, width, depth, level, hkey, look, storeys=2.0,
                                                margin=150.0 ) )
                        inn_done = True
                    else:
                        built.append( building( "house", centre, -left, width, depth, level, hkey,
                                                storeys=2.0 if chance( 0.3, *hkey, "storeys" ) else 1.5,
                                                outshot=chance( 0.5, *hkey, "outshot" ), margin=150.0 ) )
            s += way * ( total + ( between( 110, 420, *key, "gap" ) if ok else 160.0 ) )


def village_plan( W ):
    """ The buildings outside the play area: the villages' rows, the kirk above the east village, the farm up the hill
    and the lighthouse with its keepers' cottages on the west headland. Yards are pads with nothing built on them. """
    built = []
    # The kirk above the east village, its long sides north and south, in its graveyard
    mean, high, low = footprint_level( W, KIRK, ( 0.0, -1.0 ), 710.0, 394.0 )
    built.append( building( "kirk", KIRK, ( 0.0, -1.0 ), 710.0, 394.0, mean, ( "kirk", ), storeys=1.0,
                            look=dict( harl="sh_whitewash", door="sh_paint_door", margin="sh_tar_black", panes=2,
                                       roof="plain", cans=0, kind="kirk" ), margin=420.0, blend=260.0,
                            clear=0.5 * math.hypot( *GRAVEYARD ) ) )
    village_rows( W, built )
    # The farm: the farmhouse looking down the hill, the steading round its yard behind, the hay shed beside
    fe, fn = FARM
    farm_level, _, _ = footprint_level( W, ( fe + 300.0, fn + 300.0 ), ( 0.0, -1.0 ), 1200.0, 1000.0 )
    built.append( building( "farmhouse", FARM, ( 0.0, -1.0 ), 440.0, 300.0, farm_level, ( "farm", "house" ),
                            storeys=2.0, look=dict( house_look( ( "farm", ), "farmhouse" ), harl="sh_harl", roof="plain",
                                                    door="sh_paint_door" ), margin=150.0 ) )
    built.append( building( "yard", ( fe + 300.0, fn + 400.0 ), ( 0.0, -1.0 ), 900.0, 460.0, farm_level,
                            ( "farm", "yard" ), margin=40.0, blend=220.0, paint="sh_shingle" ) )
    for name, centre, out, width, depth, roof in (
            ( "north", ( fe + 200.0, fn + 735.0 ), ( 0.0, -1.0 ), 700.0, 210.0, "sh_slate_roof" ),
            ( "east", ( fe + 835.0, fn + 380.0 ), ( -1.0, 0.0 ), 440.0, 210.0, "sh_corrugated_red" ),
            ( "west", ( fe - 300.0, fn + 420.0 ), ( 1.0, 0.0 ), 360.0, 200.0, "sh_corrugated_green" ) ):
        built.append( building( "range", centre, out, width, depth, farm_level, ( "farm", name ), storeys=1.0,
                                look=dict( harl="sh_rubble", door="sh_timber_tar", margin="sh_rubble", panes=0,
                                           roof=roof, cans=0, kind="range" ), margin=100.0 ) )
    built.append( building( "barn", ( fe + 1220.0, fn + 50.0 ), ( -1.0, 0.0 ), 600.0, 360.0, farm_level, ( "farm", "barn" ),
                            storeys=1.0, look=dict( harl="sh_steel_green", door="sh_steel_green", margin="sh_rust",
                                                    panes=0, roof="sh_corrugated_green", cans=0, kind="barn" ),
                            margin=100.0 ) )
    # The lighthouse and its keepers' cottages, on the west headland
    le, ln = LIGHTHOUSE
    _, high, _ = footprint_level( W, LIGHTHOUSE, ( 0.0, -1.0 ), 160.0, 160.0 )
    built.append( building( "lighthouse", LIGHTHOUSE, ( 0.0, -1.0 ), 160.0, 160.0, high, ( "lighthouse", ), storeys=1.0,
                            look=dict( harl="sh_whitewash", door="sh_paint_black", margin="sh_paint_yellow", panes=2,
                                       roof="plain", cans=0, kind="lighthouse" ), margin=90.0, blend=160.0 ) )
    centre = ( le - 380.0, ln + 380.0 )
    mean, high, _ = footprint_level( W, centre, ( 0.6, -0.8 ), 620.0, 280.0 )
    built.append( building( "keepers", centre, ( 0.6, -0.8 ), 620.0, 280.0, max( mean, high - 30.0 ), ( "keepers", ),
                            storeys=1.0, look=dict( harl="sh_whitewash", door="sh_paint_black", margin="sh_paint_yellow",
                                                    panes=2, roof="plain", cans=3, kind="keepers" ), margin=150.0 ) )
    return built


# ---------------------------------------------------------------------------------------------------------------------
# The ground's mesh: a balanced quadtree over the land and the loch's bed, fine by the play area, the shore, the roads,
# the burn and the buildings, and wherever the hills are rough enough to show it, coarse far off.

GRID = 98304.0                  # the tree's half size: 4096 of the finest cells across
LEVELS = 12                     # the finest cells are 48 across
TOP = 4                         # the tree starts from cells 12288 across
LATTICE = 8193                  # vertices lie on a 24-inch lattice, 8193 points a side
# The grid's lines at the holes' edges (all on the finest cells' lines) are moved onto the play area's own lines.
WARP_E = ( ( -98304.0, -2496.0, -2160.0, 2160.0, 2496.0, 98304.0 ), ( -98304.0, -2500.0, -2150.0, 2150.0, 2500.0, 98304.0 ) )
WARP_N = ( ( -98304.0, -1776.0, -1344.0, 1872.0, 1968.0, 98304.0 ), ( -98304.0, -1760.0, -1350.0, 1850.0, 1960.0, 98304.0 ) )
# What the play area's own models fill, in the grid's units: the play area from the beach's foot to the land's edge,
# and the terraces up the braes.
HOLES = ( ( -2160.0, -1776.0, 2160.0, 1872.0 ), ( -2496.0, -1344.0, -2160.0, 1968.0 ), ( 2160.0, -1344.0, 2496.0, 1968.0 ) )
COARSE = 0.06                   # the largest a cell may be, against its distance from the play area
FINE = 0.02                     # by the shore, the roads, the burn, the lochan and the buildings
ROUGH = 0.012                   # the smallest a cell gets for the hills' shape
ERROR = 0.005                   # how far the cells may stray from the hills, against the distance
DEEP = 0.1                      # the loch's bed where the water's too deep to see it
DEEP_OUT = 400.0                # ... which is this far out from the shore


def warp( gx, gy ):
    return np.interp( gx, *WARP_E ), np.interp( gy, *WARP_N )


def unwarp( e, n ):
    return np.interp( e, WARP_E[1], WARP_E[0] ), np.interp( n, WARP_N[1], WARP_N[0] )


def cell_size( level ):
    return 2.0 * GRID / 2 ** level


def code( level, i, j ):
    return np.asarray( i, np.int64 ) * ( 1 << level ) + np.asarray( j, np.int64 )


def decode( level, c ):
    return c >> level, c & ( ( 1 << level ) - 1 )


def vkey( x, y ):
    return np.asarray( x, np.int64 ) * LATTICE + np.asarray( y, np.int64 )


def play_distance( e, n ):
    """ How far each point lies outside the play area (0 inside it). """
    de = np.maximum( np.abs( e ) - PLAY_E, 0.0 )
    dn = np.maximum( np.maximum( PLAY_N0 - n, n - PLAY_N1 ), 0.0 )
    return np.hypot( de, dn )


def hole_state( level, i, j ):
    """ For cells: ( inside a hole, straddling a hole's edge ). """
    size = cell_size( level )
    x0, y0 = -GRID + i * size, -GRID + j * size
    x1, y1 = x0 + size, y0 + size
    inside, touch = np.zeros( len( i ), bool ), np.zeros( len( i ), bool )
    for hx0, hy0, hx1, hy1 in HOLES:
        touch |= ( x0 < hx1 ) & ( x1 > hx0 ) & ( y0 < hy1 ) & ( y1 > hy0 )
        inside |= ( x0 >= hx0 ) & ( x1 <= hx1 ) & ( y0 >= hy0 ) & ( y1 <= hy1 )
    return inside, touch & ~inside


def cell_frame( W, level, i, j ):
    """ The cells' centres in the world, their reach (0.71 of their size), distance from the play area (to their
    nearest point), coast distance and how far into the far shore they are. """
    size = cell_size( level )
    e, n = warp( -GRID + ( i + 0.5 ) * size, -GRID + ( j + 0.5 ) * size )
    reach = np.full( np.shape( e ), 0.71 * size )
    r = np.maximum( play_distance( e, n ) - reach, 0.0 )
    dist, _, side = W.coast.query( e, n )
    return e, n, reach, r, dist * side, far_side( W, e, n )


def cell_dropped( W, level, i, j, frame=None ):
    """ Cells nothing is drawn in: in a hole, past the far clip, behind the ridge, or all under the far shore. """
    e, n, reach, r, d, far = frame if frame is not None else cell_frame( W, level, i, j )
    inside, _ = hole_state( level, i, j )
    return inside | ( r > SIGHT ) | ( d - reach > LAND_CUT ) | ( far - reach > 0 )


def fine_zone( W, e, n, reach ):
    """ Which cells come within reach of the shore, a road, the burn, the lochan's shore or a building's pad. """
    dist, _, _ = W.coast.query( e, n )
    near = dist < 300.0 + reach
    top = float( reach.max() ) if len( reach ) else 0.0
    for route, width in [ ( road.route, road.half + 150.0 ) for road in W.roads ] + [ ( W.burn, 150.0 ) ]:
        m = route.near( e, n, width + top )
        if m.any():
            dr, _, _ = route.query( e[m], n[m] )
            near[m] |= dr < width + reach[m]
    out, _ = ellipse_out( e, n, LOCHAN )
    near |= np.abs( out ) < 200.0 + reach
    for p in W.pads:
        near |= np.hypot( e - p["centre"][0], n - p["centre"][1] ) < p["reach"] + reach
    return near


def roughness( W, level, i, j ):
    """ How far the hills stray from a flat cell through its corners: the most at its centre and edges' midpoints. """
    size = cell_size( level )
    f = np.array( ( 0.0, 1.0, 1.0, 0.0, 0.5, 0.5, 1.0, 0.5, 0.0 ) )
    g = np.array( ( 0.0, 0.0, 1.0, 1.0, 0.5, 0.0, 0.5, 1.0, 0.5 ) )
    gx = -GRID + ( i[:, None] + f[None, :] ) * size
    gy = -GRID + ( j[:, None] + g[None, :] ) * size
    e, n = warp( gx, gy )
    z = ground( W, e.ravel(), n.ravel(), upto=3 ).reshape( e.shape )
    c = z[:, :4]
    guess = np.stack( ( c.mean( axis=1 ), ( c[:, 0] + c[:, 1] ) / 2, ( c[:, 1] + c[:, 2] ) / 2, ( c[:, 2] + c[:, 3] ) / 2,
                        ( c[:, 3] + c[:, 0] ) / 2 ), axis=1 )
    return np.abs( z[:, 4:] - guess ).max( axis=1 )


def cell_split( W, level, i, j ):
    """ Which cells split: those straddling a hole's edge, larger than their distance allows, in a fine zone and larger
    than it allows there, or straying from the hills' shape more than their distance allows. """
    size = cell_size( level )
    frame = cell_frame( W, level, i, j )
    e, n, reach, r, d, far = frame
    dropped = cell_dropped( W, level, i, j, frame )
    _, straddle = hole_state( level, i, j )
    biggest = np.clip( COARSE * r, 48.0, 4096.0 )
    biggest = np.where( d < -DEEP_OUT - reach, np.clip( DEEP * r, 192.0, 4096.0 ), biggest )
    split = size > biggest * 1.0001
    fine = ( size > np.maximum( 48.0, FINE * r ) * 1.0001 ) & ~split & ~dropped
    if fine.any():
        idx = np.flatnonzero( fine )
        split[idx[fine_zone( W, e[idx], n[idx], reach[idx] )]] = True
    rough = ~split & ~dropped & ( d + reach > -200.0 ) & ( size > np.maximum( 48.0, ROUGH * r ) * 1.0001 )
    if rough.any():
        idx = np.flatnonzero( rough )
        split[idx[roughness( W, level, i[idx], j[idx] ) > np.maximum( 3.0, ERROR * r[idx] )]] = True
    return ( split & ~dropped ) | straddle


class Mesh:
    """ The ground's triangles: vertices ( V, 3 ) on the lattice ( keys ), their normals, the triangles ( T, 3 ), and
    the tree (each level's split cells and leaves) for draping things on it. """


def build_tree( W ):
    split = { L: np.arange( 1 << ( 2 * L ), dtype=np.int64 ) for L in range( TOP ) }
    cells = np.arange( 1 << ( 2 * TOP ), dtype=np.int64 )
    for L in range( TOP, LEVELS + 1 ):
        i, j = decode( L, cells )
        s = cell_split( W, L, i, j ) if L < LEVELS else np.zeros( len( cells ), bool )
        split[L] = np.sort( cells[s] )
        si, sj = i[s] * 2, j[s] * 2
        cells = np.concatenate( [ code( L + 1, si + a, sj + b ) for a in ( 0, 1 ) for b in ( 0, 1 ) ] )
    # 2:1 balance: a split cell's edge neighbours must all exist, so their parents are split
    for L in range( LEVELS - 1, TOP, -1 ):
        i, j = decode( L, split[L] )
        ni, nj = np.concatenate( ( i - 1, i + 1, i, i ) ), np.concatenate( ( j, j, j - 1, j + 1 ) )
        ok = ( ni >= 0 ) & ( ni < ( 1 << L ) ) & ( nj >= 0 ) & ( nj < ( 1 << L ) )
        split[L - 1] = np.union1d( split[L - 1], code( L - 1, ni[ok] // 2, nj[ok] // 2 ) )
    leaves = {}
    for L in range( TOP, LEVELS + 1 ):
        if L == TOP:
            children = np.arange( 1 << ( 2 * TOP ), dtype=np.int64 )
        else:
            pi, pj = decode( L - 1, split[L - 1] )
            children = np.concatenate( [ code( L, pi * 2 + a, pj * 2 + b ) for a in ( 0, 1 ) for b in ( 0, 1 ) ] )
        leaves[L] = np.setdiff1d( children, split[L] )
    return split, leaves


def has_split( split, level, i, j ):
    """ Whether the cells at ( i, j ) of a level exist and are split. """
    ok = ( i >= 0 ) & ( i < ( 1 << level ) ) & ( j >= 0 ) & ( j < ( 1 << level ) )
    found = np.zeros( len( i ), bool )
    if level in split and len( split[level] ):
        c = code( level, np.where( ok, i, 0 ), np.where( ok, j, 0 ) )
        pos = np.clip( np.searchsorted( split[level], c ), 0, len( split[level] ) - 1 )
        found = ok & ( split[level][pos] == c )
    return found


def leaf_keys( level, i, j ):
    """ The lattice keys of cells' corners ( 00, 10, 11, 01 ), edges' midpoints ( bottom, right, top, left ) and centres. """
    step = 1 << ( 13 - level )
    h = step >> 1
    x, y = i * step, j * step
    corners = ( vkey( x, y ), vkey( x + step, y ), vkey( x + step, y + step ), vkey( x, y + step ) )
    mids = ( vkey( x + h, y ), vkey( x + step, y + h ), vkey( x + h, y + step ), vkey( x, y + h ) )
    return corners, mids, vkey( x + h, y + h )


def lattice_points( keys ):
    """ World ( e, n ) of lattice keys. """
    x, y = keys // LATTICE, keys % LATTICE
    return warp( -GRID + 24.0 * x, -GRID + 24.0 * y )


def build_mesh( W ):
    """ The ground's mesh over everything the tree keeps, with each vertex at the ground's height. """
    started = time.time()
    split, leaves = build_tree( W )
    M = Mesh()
    M.split, M.leaves, M.kept, M.diag, M.mids = split, leaves, {}, {}, {}
    parts = []
    for L in range( TOP, LEVELS + 1 ):
        i, j = decode( L, leaves[L] )
        kept = ~cell_dropped( W, L, i, j )
        mids = np.stack( [ has_split( split, L, i + a, j + b ) for a, b in ( ( 0, -1 ), ( 1, 0 ), ( 0, 1 ), ( -1, 0 ) ) ], 1 )
        M.kept[L], M.mids[L] = kept, mids
        parts.append( ( L, i, j, kept, mids ) )
    # Heights: every corner, midpoint and centre the kept leaves use
    keys = []
    for L, i, j, kept, mids in parts:
        corners, edge, centre = leaf_keys( L, i[kept], j[kept] )
        keys += list( corners ) + [ centre ] + [ m[mids[kept][:, k]] for k, m in enumerate( edge ) ]
    keys = np.unique( np.concatenate( keys ) )
    e, n = lattice_points( keys )
    z = ground( W, e, n )
    M.keys, M.xyz = keys, np.stack( ( e, n, z ), axis=1 )

    def index( k ):
        return np.searchsorted( keys, k )

    tris = []
    for L, i, j, kept, mids in parts:
        corners, edge, centre = leaf_keys( L, i, j )
        c = [ index( k[kept] ) for k in corners ]
        mid = mids[kept]
        plain = ~mid.any( axis=1 )
        zc = z[index( centre[kept] )]
        z00, z10, z11, z01 = ( z[k] for k in c )
        diag = np.abs( zc - ( z00 + z11 ) / 2 ) <= np.abs( zc - ( z10 + z01 ) / 2 )
        full_diag = np.zeros( len( i ), bool )
        full_diag[np.flatnonzero( kept )] = diag
        M.diag[L] = full_diag
        a, b = plain & diag, plain & ~diag
        tris += [ np.stack( ( c[0][a], c[1][a], c[2][a] ), 1 ), np.stack( ( c[0][a], c[2][a], c[3][a] ), 1 ),
                  np.stack( ( c[0][b], c[1][b], c[3][b] ), 1 ), np.stack( ( c[1][b], c[2][b], c[3][b] ), 1 ) ]
        fan = ~plain
        if fan.any():
            cc = index( centre[kept][fan] )
            for side in range( 4 ):
                p, q = c[side][fan], c[( side + 1 ) % 4][fan]
                has = mid[fan][:, side]
                m = np.zeros( len( p ), np.int64 )
                m[has] = index( edge[side][kept][fan][has] )
                tris += [ np.stack( ( cc[~has], p[~has], q[~has] ), 1 ), np.stack( ( cc[has], p[has], m[has] ), 1 ),
                          np.stack( ( cc[has], m[has], q[has] ), 1 ) ]
    T = np.concatenate( [ t for t in tris if len( t ) ] ).astype( np.int64 )
    # Area-weighted smooth normals
    P = M.xyz
    face = np.cross( P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]] )
    normal = np.zeros_like( P )
    for k in range( 3 ):
        np.add.at( normal, T[:, k], face )
    M.normal = normal / np.maximum( np.linalg.norm( normal, axis=1 ), 1e-9 )[:, None]
    M.tri, M.face = T, face / np.maximum( np.linalg.norm( face, axis=1 ), 1e-9 )[:, None]
    M.built_in = time.time() - started
    return M


_MESH = []


def mesh():
    if not _MESH:
        _MESH.append( build_mesh( world() ) )
    return _MESH[0]


def drape( e, n, M=None ):
    """ The height of the ground's mesh (as drawn, between its vertices) at each point; the ground's own height where
    the mesh draws nothing. """
    M = M or mesh()
    W = world()
    e, n = np.atleast_1d( np.asarray( e, float ) ), np.atleast_1d( np.asarray( n, float ) )
    gx, gy = unwarp( e, n )
    out = np.full( len( e ), np.nan )
    todo = np.ones( len( e ), bool )
    for L in range( LEVELS, TOP - 1, -1 ):
        if not todo.any():
            break
        size = cell_size( L )
        i = np.clip( np.floor( ( gx + GRID ) / size ).astype( np.int64 ), 0, ( 1 << L ) - 1 )
        j = np.clip( np.floor( ( gy + GRID ) / size ).astype( np.int64 ), 0, ( 1 << L ) - 1 )
        c = code( L, i, j )
        leaf = M.leaves[L]
        pos = np.clip( np.searchsorted( leaf, c ), 0, max( len( leaf ) - 1, 0 ) )
        hit = todo & ( len( leaf ) > 0 ) & ( leaf[pos] == c ) if len( leaf ) else np.zeros( len( e ), bool )
        if not hit.any():
            continue
        todo &= ~hit
        idx = np.flatnonzero( hit )
        p = pos[idx]
        kept = M.kept[L][p]
        idx, p = idx[kept], p[kept]
        if not len( idx ):
            continue
        fx = ( gx[idx] + GRID ) / size - i[idx]
        fy = ( gy[idx] + GRID ) / size - j[idx]
        corners, edge, centre = leaf_keys( L, i[idx], j[idx] )

        def height( k ):
            q = np.clip( np.searchsorted( M.keys, k ), 0, len( M.keys ) - 1 )
            return M.xyz[q, 2]

        z00, z10, z11, z01 = ( height( k ) for k in corners )
        mids = M.mids[L][p]
        plain = ~mids.any( axis=1 )
        diag = M.diag[L][p]
        # Two triangles split along the diagonal chosen for the cell
        za = np.where( fy <= fx, z00 + fx * ( z10 - z00 ) + fy * ( z11 - z10 ), z00 + fy * ( z01 - z00 ) + fx * ( z11 - z01 ) )
        zb = np.where( fx + fy <= 1.0, z00 + fx * ( z10 - z00 ) + fy * ( z01 - z00 ),
                       z11 + ( 1 - fx ) * ( z01 - z11 ) + ( 1 - fy ) * ( z10 - z11 ) )
        z = np.where( diag, za, zb )
        if ( ~plain ).any():
            # A fan about the centre: the quarter the point is in, halved where that edge has its midpoint
            zc = height( centre )
            u, v = fx - 0.5, fy - 0.5
            side = np.where( np.abs( u ) >= np.abs( v ), np.where( u >= 0, 1, 3 ), np.where( v >= 0, 2, 0 ) )
            cz = np.stack( ( z00, z10, z11, z01 ), 1 )
            mz = np.stack( [ height( k ) for k in edge ], 1 )
            rows = np.arange( len( idx ) )
            A, B = cz[rows, side], cz[rows, ( side + 1 ) % 4]
            Mz = mz[rows, side]
            has = mids[rows, side]
            # Along the edge: t from A to B; across: s from the edge (0) to the centre (1)
            t = np.select( [ side == 0, side == 1, side == 2 ], [ fx, fy, 1 - fx ], 1 - fy )
            s = np.select( [ side == 0, side == 1, side == 2 ], [ fy, 1 - fx, 1 - fy ], fx ) * 2.0
            # The triangle's own linear surface: the edge at s = 0 and the centre at s = 1, with t scaled about the middle
            tt = np.clip( 0.5 + ( t - 0.5 ) / np.maximum( 1 - s, 1e-6 ), 0.0, 1.0 )
            edge_at = np.where( has, np.where( tt <= 0.5, A + ( Mz - A ) * tt * 2, Mz + ( B - Mz ) * ( tt - 0.5 ) * 2 ),
                                A + ( B - A ) * tt )
            fan_z = edge_at + ( zc - edge_at ) * np.clip( s, 0.0, 1.0 )
            z = np.where( plain, z, fan_z )
        out[idx] = z
    missing = np.isnan( out )
    if missing.any():
        out[missing] = ground( W, e[missing], n[missing] )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The crofts: long strips of in-bye land running up the hill behind the villages and the distillery, each one walled,
# under the head dyke

# The line the strips are laid out from: the coast's, smoothed, bowed out to the loch so its normals spread inland
CROFT_LINE = ( ( -14000, -10200 ), ( -12500, -8200 ), ( -11000, -6400 ), ( -9500, -4900 ), ( -8000, -3700 ),
               ( -6500, -2750 ), ( -5000, -2050 ), ( -3500, -1720 ), ( -2000, -1650 ), ( 0, -1650 ), ( 2000, -1650 ),
               ( 3500, -1720 ), ( 5000, -1950 ), ( 6500, -2550 ), ( 8000, -3400 ), ( 9500, -4600 ), ( 11000, -6100 ),
               ( 12300, -7600 ), ( 14000, -9100 ) )
CROFT_E = 11500.0               # the strips run this far each way
CROFT_HEAD = 9000.0             # the head dyke's distance up from the line, give or take HEAD_WANDER
HEAD_WANDER = 1500.0
CROFT_FOOT = ( 3950.0, 1100.0 ) # the strips' feet behind the distillery ( |e| under 3600 ) and the villages ( over 4200 )
FIELD_PAINTS = ( "sh_field", ) * 12 + ( "sh_grass", ) * 5 + ( "sh_hill_grass", ) * 2 + ( "sh_moor", )

WET_TOP = SEA_Z + 14.0          # the wet sand and gravel at the water's edge
SHINGLE_TOP = -95.0             # the shingle bank's top, where the grass starts
SHORE_BAND = 600.0              # the shore's paints don't reach further inland than this
SHORE_DEPTH = 60.0              # the seabed is light under this much water, and dark under more


class Crofts:
    """ The strips: their edges along the croft line ( u ); for each one its foot and head (v, the distance up from the
    line), the v of its dykes from foot to head ( breaks ) and what fills the land between them ( fill: a paint, or None
    where a steading or a wood stands in it ). """


def croft_frame( W, e, n ):
    """ ( u, v ): how far along the croft line each point is, and how far up from it. """
    dist, along, side = W.croft.query( np.asarray( e, float ), np.asarray( n, float ) )
    return along, dist * side


def obstacle_boxes( W ):
    """ The ( u0, u1, v0, v1, steading ) boxes the fields keep out of: the buildings with their plots and the kirk's
    graveyard ( steading true ), the plantation and the lochan. """
    boxes = []
    for b in W.buildings:
        if b["kind"] == "kirk":
            hx, hy = GRAVEYARD[0] / 2 + 60.0, GRAVEYARD[1] / 2 + 60.0
        else:
            hx, hy = b["width"] / 2 + 200.0, b["depth"] / 2 + 200.0
        pts = np.array( [ b["centre"] + b["axis"] * a * hx + b["out"] * c * hy
                          for a in np.linspace( -1, 1, 5 ) for c in np.linspace( -1, 1, 5 ) ] )
        boxes.append( ( pts, True ) )
    boxes.append( ( np.array( PLANTATION, float ), False ) )
    t = np.linspace( 0, 2 * math.pi, 24, endpoint=False )
    boxes.append( ( np.stack( ( LOCHAN[0] + 1.4 * LOCHAN[2] * np.cos( t ), LOCHAN[1] + 1.4 * LOCHAN[3] * np.sin( t ) ),
                              axis=1 ), False ) )
    out = []
    for pts, steading in boxes:
        u, v = croft_frame( W, pts[:, 0], pts[:, 1] )
        out.append( ( float( u.min() ), float( u.max() ), float( v.min() ), float( v.max() ), steading ) )
    return out


def croft_plan( W ):
    line = W.croft
    inside = np.abs( line.xy[:, 0] ) <= CROFT_E
    u, u_end = float( line.s[inside].min() ), float( line.s[inside].max() )
    edges, k = [ u ], 0
    while u < u_end - 300.0:
        u = min( u + between( 600.0, 1100.0, "croft", k ), u_end )
        edges.append( u )
        k += 1
    C = Crofts()
    C.edges = np.array( edges )
    mid = ( C.edges[:-1] + C.edges[1:] ) / 2
    ae = np.abs( line.at( mid )[:, 0] )
    C.start = np.interp( ae, ( 3600.0, 4200.0 ), CROFT_FOOT )
    C.head = CROFT_HEAD + HEAD_WANDER * vnoise( mid, np.zeros_like( mid ), 5000.0, "head" )
    # Keep the fields off the steadings, the kirk, the wood and the lochan: start a strip above one near its foot; take
    # the head dyke up round a steading near it, or end the strip under a wood or the lochan; else leave a gap round it
    gaps = [ [] for _ in mid ]
    obstacles = obstacle_boxes( W )
    for u0, u1, v0, v1, steading in obstacles:
        for j in np.flatnonzero( ( C.edges[1:] > u0 ) & ( C.edges[:-1] < u1 ) ):
            if v1 < C.start[j] or v0 > C.head[j]:
                continue
            if v0 < C.start[j] + 1500.0:
                C.start[j] = max( C.start[j], v1 + 100.0 )
            elif v1 > C.head[j] - 1500.0 and steading:
                C.head[j] = max( C.head[j], v1 + 500.0 )
            elif v1 > C.head[j] - 1500.0:
                C.head[j] = min( C.head[j], v0 - 100.0 )
    for u0, u1, v0, v1, steading in obstacles:
        for j in np.flatnonzero( ( C.edges[1:] > u0 ) & ( C.edges[:-1] < u1 ) ):
            if v1 > C.start[j] and v0 < C.head[j]:
                gaps[j].append( ( v0 - 100.0, v1 + 100.0 ) )
    C.breaks, C.fill = [], []
    for j in range( len( mid ) ):
        if C.head[j] - C.start[j] < 800.0:
            C.breaks.append( np.array( [ C.start[j], C.start[j] ] ) )
            C.fill.append( [ None ] )
            continue
        merged = []
        for g0, g1 in sorted( gaps[j] ):
            if merged and g0 <= merged[-1][1] + 300.0:
                merged[-1][1] = max( merged[-1][1], g1 )
            else:
                merged.append( [ g0, g1 ] )
        gaps[j] = [ ( max( g0, C.start[j] ), min( g1, C.head[j] ) ) for g0, g1 in merged ]
        cuts = [ ( C.start[j], "field" ) ]
        for g0, g1 in gaps[j]:
            cuts += [ ( g0, None ), ( g1, "field" ) ]
        span = C.head[j] - C.start[j]
        if span > 4000.0 and not gaps[j] and chance( 0.6, "croft", j, "cross" ):
            cuts.append( ( C.start[j] + span * between( 0.4, 0.6, "croft", j, "at" ), "field" ) )
        cuts.sort( key=lambda c: c[0] )
        breaks = [ c[0] for c in cuts ] + [ C.head[j] ]
        fill = [ pick( FIELD_PAINTS, "croft", j, i ) if c[1] else None for i, c in enumerate( cuts ) ]
        C.breaks.append( np.array( breaks ) )
        C.fill.append( fill )
    return C


def strip_of( C, u ):
    k = np.searchsorted( C.edges, u, side="right" ) - 1
    return np.where( ( k >= 0 ) & ( k < len( C.start ) ), k, -1 )


def field_of( C, u, v ):
    """ Which field each point is in ( 32 x strip + the interval ), or -1, and the field's paint. """
    k = strip_of( C, u )
    ids = np.full( len( u ), -1, np.int64 )
    paint = np.full( len( u ), None, dtype=object )
    for j in np.unique( k[k >= 0] ):
        m = np.flatnonzero( k == j )
        i = np.searchsorted( C.breaks[j], v[m], side="right" ) - 1
        ok = ( i >= 0 ) & ( i < len( C.fill[j] ) )
        fills = np.array( C.fill[j] + [ None ], dtype=object )[np.where( ok, i, len( C.fill[j] ) )]
        ok &= np.array( [ x is not None for x in fills ], bool )
        ids[m[ok]] = 32 * j + i[ok]
        paint[m[ok]] = fills[ok]
    return ids, paint


def in_bye( C, u, v ):
    """ Whether points are on the in-bye land: within the strips' run and under their head dyke. """
    k = strip_of( C, u )
    head = np.where( k >= 0, C.head[np.clip( k, 0, len( C.head ) - 1 )], -1e9 )
    return ( k >= 0 ) & ( v <= head )


def inside_convex( e, n, corners ):
    """ How far inside a convex polygon each point is ( < 0 outside ); its corners in order, either way round. """
    q = np.asarray( corners, float )
    nxt = np.roll( q, -1, axis=0 )
    sign = 1.0 if ( q[:, 0] * nxt[:, 1] - nxt[:, 0] * q[:, 1] ).sum() > 0 else -1.0
    best = np.full( np.shape( e ), np.inf )
    for a, b in zip( q, nxt ):
        t = ( b - a ) / np.linalg.norm( b - a )
        best = np.minimum( best, sign * ( t[0] * ( n - a[1] ) - t[1] * ( e - a[0] ) ) )
    return best


def rect_inside( e, n, centre, axis, half ):
    """ How far inside an oriented rectangle each point is ( < 0 outside ). """
    across = np.array( ( -axis[1], axis[0] ) )
    re, rn = e - centre[0], n - centre[1]
    return -np.maximum( np.abs( re * axis[0] + rn * axis[1] ) - half[0], np.abs( re * across[0] + rn * across[1] ) - half[1] )


# ---------------------------------------------------------------------------------------------------------------------
# The ground's paints. Each choice is a field over the ground, >= 0 where it holds, worked out at the mesh's points;
# triangles are cut where a field crosses 0, so the paints meet along smooth lines rather than the triangles' edges.

FIELDS = ( "heather", "bracken", "bog", "crag", "near_grass", "plantation", "lochan", "lochan_shore", "burn", "plot",
           "yard", "shore", "wet", "wrack", "rocky", "weed", "light" )
A_E, A_N, A_Z, A_U, A_V, A_D, A_NX, A_NY, A_NZ = range( 9 )
A_F = 9
FIELD = { name: A_F + i for i, name in enumerate( FIELDS ) }


def slope_of( nz ):
    nz = np.clip( nz, 0.05, 1.0 )
    return np.sqrt( 1.0 - nz * nz ) / nz


def ground_fields( W, e, n, z, nz, d, point=True ):
    """ Every paint field at the points: an ( N, len( FIELDS ) ) array. point adds the rocky points either side of the
    beach (not on the far shore). """
    slope = slope_of( nz )
    out = np.zeros( ( len( e ), len( FIELDS ) ) )

    def put( name, value ):
        out[:, FIELDS.index( name )] = value

    # The open hill: heather further in, bracken on the lower slopes, bog on the flats, rock where it's steep or bare
    heather = vfractal( e, n, 6500.0, "heather", 2 ) - ( 0.3 - 0.6 * np.clip( ( d - 9000.0 ) / 16000.0, 0.0, 1.0 ) )
    put( "heather", np.minimum( heather, ( d - 6000.0 ) / 3000.0 ) )
    bracken = vfractal( e, n, 3800.0, "bracken", 2 ) - 0.13
    put( "bracken", np.minimum.reduce( [ bracken, ( 14000.0 - d ) / 3000.0, ( d - 2000.0 ) / 1000.0, ( slope - 0.08 ) * 4.0,
                                         ( 0.75 - slope ) * 2.0 ] ) )
    bog = vfractal( e, n, 5200.0, "bog", 2 ) - 0.12
    put( "bog", np.minimum.reduce( [ bog, ( 0.11 - slope ) * 5.0, ( d - 9000.0 ) / 2000.0 ] ) )
    bare = np.clip( ( d - 5000.0 ) / 25000.0, 0.0, 1.0 )
    crag = vfractal( e, n, 1400.0, "crag", 2 ) - ( 0.47 - 0.1 * bare )
    steep = np.minimum( ( slope - 0.62 ) * 2.0, vfractal( e, n, 900.0, "steep", 2 ) + 0.1 )
    put( "crag", np.maximum( steep, np.minimum( crag, ( d - 3000.0 ) / 1000.0 ) ) )
    put( "near_grass", np.minimum.reduce( [ ( 1500.0 - d ) / 300.0, d / 100.0, ( 0.6 - slope ) * 2.0 ] ) )
    # The wood, the lochan and the burn
    put( "plantation", inside_convex( e, n, PLANTATION ) / 100.0 )
    _, r = ellipse_out( e, n, LOCHAN )
    put( "lochan", 1.0 - r )
    put( "lochan_shore", 1.12 - r )
    burn = np.full( len( e ), -10.0 )
    near = W.burn.near( e, n, 400.0 )
    if near.any():
        dist, _, _ = W.burn.query( e[near], n[near] )
        burn[near] = ( 42.0 - dist ) / 42.0
    put( "burn", burn )
    # The buildings' plots (grass), the farmyard (gravel)
    plot = np.full( len( e ), -1e4 )
    yard = np.full( len( e ), -1e4 )
    for b in W.buildings:
        if b["kind"] == "yard":
            yard = np.maximum( yard, rect_inside( e, n, b["centre"], b["axis"], ( b["width"] / 2, b["depth"] / 2 ) ) )
            continue
        half = ( GRAVEYARD[0] / 2, GRAVEYARD[1] / 2 ) if b["kind"] == "kirk" else ( b["width"] / 2 + 150.0, b["depth"] / 2 + 150.0 )
        plot = np.maximum( plot, rect_inside( e, n, b["centre"], b["axis"], half ) )
    put( "plot", plot / 50.0 )
    put( "yard", yard / 50.0 )
    # The shore: wet gravel at the water's edge, the wrack's strand line, the shingle bank, rock where it's rocky
    put( "shore", np.minimum( ( SHORE_BAND - d ) / 100.0, ( SHINGLE_TOP - z ) / 10.0 ) )
    put( "wet", ( WET_TOP - z ) / 5.0 )
    put( "wrack", np.minimum( vfractal( e, n, 420.0, "strand", 2 ) + 0.1, ( WET_TOP + 16.0 - z ) / 5.0 ) )
    headland = np.clip( ( np.abs( e ) - 9000.0 ) / 4000.0, 0.0, 1.0 )
    skerry = vfractal( e, n, 700.0, "skerry", 3 ) - ( 0.32 - 0.4 * headland )
    rocky = np.minimum.reduce( [ ( 500.0 - d ) / 100.0, -z / 20.0, np.maximum( ( slope - 0.6 ) * 4.0, skerry ) ] )
    if point:
        rocky = np.maximum( rocky, np.minimum( ( 2900.0 - np.abs( e ) ) / 50.0, ( TERRACE_N0 - n ) / 50.0 ) )
    put( "rocky", rocky )
    put( "weed", ( WEED_Z - z ) / 10.0 )
    # Under the water: light sand and weed in the shallows, dark mud deeper
    put( "light", ( SHORE_DEPTH + 15.0 * vnoise( e, n, 500.0, "bed" ) - ( SEA_Z - z ) ) / 10.0 )
    return out


def land_paint( W, C, a ):
    """ The land's paint at points given as attribute rows ( u, v, d, the fields ... ). """
    f = lambda name: a[:, FIELD[name]] >= 0.0     # noqa: E731
    paint = np.full( len( a ), "sh_hill_grass", dtype=object )
    paint[f( "bracken" )] = "sh_bracken"
    paint[f( "heather" )] = "sh_heather"
    paint[f( "bog" )] = "sh_moor"
    paint[f( "crag" )] = "sh_hill_rock"
    u, v = a[:, A_U], a[:, A_V]
    paint[( in_bye( C, u, v ) | f( "near_grass" ) ) & ( a[:, FIELD["crag"]] < 0.6 )] = "sh_grass"
    ids, fills = field_of( C, u, v )
    paint[ids >= 0] = fills[ids >= 0]
    paint[f( "plantation" )] = "sh_conifer"
    paint[f( "lochan_shore" )] = "sh_shingle"
    paint[f( "lochan" )] = "sh_seabed"
    paint[f( "burn" )] = "sh_shingle"
    paint[f( "plot" )] = "sh_grass"
    paint[f( "yard" )] = "sh_shingle"
    shore = f( "shore" )
    paint[shore] = "sh_shingle"
    paint[shore & f( "wrack" )] = "sh_wrack"
    paint[shore & f( "wet" )] = "sh_sand_wet"
    rocky = f( "rocky" )
    paint[rocky] = np.where( f( "weed" )[rocky], "sh_rock_weed", "sh_rock" )
    return paint


def seabed_paint( a ):
    return np.where( a[:, FIELD["light"]] >= 0.0, "sh_seabed", "sh_seabed_deep" ).astype( object )


# ---------------------------------------------------------------------------------------------------------------------
# The ground's polygons: the mesh's triangles, cut along the paints' lines and the fields' dykes, each piece painted by
# its middle. A triangle whose pieces all come out the same paint is kept whole.

_TILES = {}
_KERNEL = []
_GROUND = []


def paint_tile( paint ):
    """ A paint's tile, as configure() will give it, for the UVs a polygon brings with it. """
    if not _TILES:
        SM = materials()
        _TILES[None] = ( SM, sm_tiles( SM ) if SM is not None else {} )
    if paint not in _TILES:
        SM, table = _TILES[None]
        tile = table.get( paint )
        if tile is None and SM is not None and callable( getattr( SM, "tile_units", None ) ):
            try:
                tile = float( SM.tile_units( paint ) )
            except Exception:
                tile = None
        _TILES[paint] = float( tile or TILES.get( paint, 128 ) )
    return _TILES[paint]


def _cut_pieces( corner_vals, line_start, line_count, line_attr, line_value, out_bary, out_len, out_owner ):
    """ Cuts triangles along lines, each where an attribute takes a value. corner_vals ( T, 3, A ): the attributes at
    each triangle's corners; triangle t's lines are line_attr / line_value [ line_start[t] : + line_count[t] ]. Writes
    the pieces as barycentric points of their triangle ( out_bary ( P, V, 3 ), out_len, out_owner ) and returns how many,
    or -1 if they didn't fit. Compiled with numba when it's there. """
    S = 64
    V = out_bary.shape[1]
    polys = np.zeros( ( S, V, 3 ) )
    lens = np.zeros( S, np.int64 )
    nxt = np.zeros( ( S, V, 3 ) )
    nlens = np.zeros( S, np.int64 )
    vals = np.zeros( V )
    count = 0
    for t in range( corner_vals.shape[0] ):
        for i in range( 3 ):
            for k in range( 3 ):
                polys[0, i, k] = 1.0 if i == k else 0.0
        lens[0] = 3
        n_p = 1
        for li in range( line_start[t], line_start[t] + line_count[t] ):
            a = line_attr[li]
            c0 = corner_vals[t, 0, a] - line_value[li]
            c1 = corner_vals[t, 1, a] - line_value[li]
            c2 = corner_vals[t, 2, a] - line_value[li]
            n_n = 0
            for p in range( n_p ):
                m = lens[p]
                lo, hi = 1e300, -1e300
                for i in range( m ):
                    x = polys[p, i, 0] * c0 + polys[p, i, 1] * c1 + polys[p, i, 2] * c2
                    vals[i] = x
                    lo = min( lo, x )
                    hi = max( hi, x )
                if lo >= 0.0 or hi <= 0.0 or n_n + 2 > S:
                    for i in range( m ):
                        for k in range( 3 ):
                            nxt[n_n, i, k] = polys[p, i, k]
                    nlens[n_n] = m
                    n_n += 1
                    continue
                cu, co = 0, 0
                for i in range( m ):
                    j = i + 1 if i + 1 < m else 0
                    sp, sq = vals[i], vals[j]
                    if sp <= 0.0 and cu < V:
                        for k in range( 3 ):
                            nxt[n_n, cu, k] = polys[p, i, k]
                        cu += 1
                    if sp >= 0.0 and co < V:
                        for k in range( 3 ):
                            nxt[n_n + 1, co, k] = polys[p, i, k]
                        co += 1
                    if ( sp < 0.0 < sq ) or ( sq < 0.0 < sp ):
                        f = sp / ( sp - sq )
                        for k in range( 3 ):
                            x = polys[p, i, k] + ( polys[p, j, k] - polys[p, i, k] ) * f
                            if cu < V:
                                nxt[n_n, cu, k] = x
                            if co < V:
                                nxt[n_n + 1, co, k] = x
                        cu = min( cu + 1, V )
                        co = min( co + 1, V )
                nlens[n_n] = cu
                nlens[n_n + 1] = co
                n_n += 2
            for p in range( n_n ):
                for i in range( nlens[p] ):
                    for k in range( 3 ):
                        polys[p, i, k] = nxt[p, i, k]
                lens[p] = nlens[p]
            n_p = n_n
        for p in range( n_p ):
            if lens[p] < 3:
                continue
            if count >= out_bary.shape[0]:
                return -1
            for i in range( lens[p] ):
                for k in range( 3 ):
                    out_bary[count, i, k] = polys[p, i, k]
            out_len[count] = lens[p]
            out_owner[count] = t
            count += 1
    return count


def cutter():
    if not _KERNEL:
        try:
            import numba
            _KERNEL.append( numba.njit( _cut_pieces ) )
        except Exception:
            _KERNEL.append( _cut_pieces )
    return _KERNEL[0]


def ground_lines( C, lo, hi, land, also=() ):
    """ ( triangle, attribute, value ) arrays of every line that crosses a triangle, by triangle: each field's 0 (the
    seabed's light only under the water, the rest only on the land), the also attributes' 0 on the land, and the crofts'
    dykes unless C is None. """
    ts, attrs, values = [], [], []

    def add( mask, a, value ):
        idx = np.flatnonzero( mask )
        if len( idx ):
            ts.append( idx )
            attrs.append( np.full( len( idx ), a, np.int64 ) )
            values.append( np.full( len( idx ), float( value ) ) )

    for name in FIELDS:
        a = FIELD[name]
        add( ( ~land if name == "light" else land ) & ( lo[:, a] < 0.0 ) & ( hi[:, a] > 0.0 ), a, 0.0 )
    for a in also:
        add( land & ( lo[:, a] < 0.0 ) & ( hi[:, a] > 0.0 ), a, 0.0 )
    if C is None:
        ts, attrs, values = ts or [ np.zeros( 0, np.int64 ) ], attrs or [ np.zeros( 0, np.int64 ) ], values or [ np.zeros( 0 ) ]
        t, a, v = np.concatenate( ts ), np.concatenate( attrs ), np.concatenate( values )
        order = np.argsort( t, kind="stable" )
        return t[order], a[order], v[order]
    u0, u1, v0, v1 = lo[:, A_U], hi[:, A_U], lo[:, A_V], hi[:, A_V]
    last = len( C.start ) - 1
    for k, edge in enumerate( C.edges ):
        near = [ j for j in ( k - 1, k ) if 0 <= j <= last ]
        low = min( C.start[j] for j in near )
        high = max( max( C.head[j], C.breaks[j][-1] ) for j in near )
        add( land & ( u0 < edge ) & ( u1 > edge ) & ( v1 > low ) & ( v0 < high ), A_U, edge )
    for j in range( last + 1 ):
        within = land & ( u1 > C.edges[j] ) & ( u0 < C.edges[j + 1] )
        for value in np.unique( np.append( C.breaks[j], C.head[j] ) ):
            add( within & ( v0 < value ) & ( v1 > value ), A_V, value )
    if not ts:
        return np.zeros( 0, np.int64 ), np.zeros( 0, np.int64 ), np.zeros( 0 )
    t, a, v = np.concatenate( ts ), np.concatenate( attrs ), np.concatenate( values )
    order = np.argsort( t, kind="stable" )
    return t[order], a[order], v[order]


def ground_pair():
    """ ( the land's ground, the seabed ), made once. """
    if not _GROUND:
        _GROUND.append( ground_models( world(), mesh() ) )
    return _GROUND[0]


def ground_models( W, M ):
    """ The land's and the seabed's models from the ground's mesh. """
    C = W.crofts
    P, T, N = M.xyz, M.tri, M.normal
    e, n, z = P[:, 0], P[:, 1], P[:, 2]
    u, v = croft_frame( W, e, n )
    dist, _, side = W.coast.query( e, n )
    d = dist * side
    f = far_side( W, e, n )
    attrs = np.concatenate( ( np.stack( ( e, n, z, u, v, d, N[:, 0], N[:, 1], N[:, 2] ), axis=1 ),
                              ground_fields( W, e, n, z, N[:, 2], d ), f[:, None] ), axis=1 )
    seam = attrs.shape[1] - 1
    # The far model takes over at far_side 0: the loch's bed by each triangle's middle (the far shore's skirt dips under
    # it), the land cut exactly along the line, so it meets the far land's own edge past the loch's heads
    centre = P[T].mean( axis=1 )
    land = attrs[T][:, :, A_Z].max( axis=1 ) >= SEA_Z - 25.0
    keep = ( far_side( W, centre[:, 0], centre[:, 1] ) <= 0.0 ) | ( land & ( f[T].min( axis=1 ) <= 0.0 ) )
    T, face, land = T[keep], M.face[keep], land[keep]
    corners = attrs[T]
    lo, hi = corners.min( axis=1 ), corners.max( axis=1 )
    models = ( K.Model(), K.Model() )

    def paint_of( a, is_land ):
        if not is_land:
            return seabed_paint( a )
        paint = land_paint( W, C, a )
        paint[a[:, seam] > 0.0] = "-"
        return paint

    cut_ground( corners, P[T], N[T], face, land, ground_lines( C, lo, hi, land, also=( seam, ) ), paint_of, models )
    return models


def cut_ground( corners, corner_xyz, corner_normal, face, land, lines, paint_of, models ):
    """ Triangles into models[ 0 ] (the land ones) and models[ 1 ] (the rest): each cut along the lines that cross it
    ( triangle, attribute, value, sorted by triangle ), every piece painted by its middle ( paint_of( attribute rows,
    is_land ); "-" leaves a piece out), and a cut triangle whose pieces all come out alike drawn whole. corners ( T, 3,
    A ) are the attributes at the triangles' corners; their positions, normals and faces come with them. UVs are the plan
    over each paint's tile. """
    T = np.arange( len( corners ) )
    lt, la, lv = lines
    counts = np.bincount( lt, minlength=len( T ) )
    starts = np.concatenate( ( [ 0 ], np.cumsum( counts )[:-1] ) )
    cut = np.flatnonzero( counts > 0 )
    room = 4 * len( cut ) + 1024
    while True:
        bary = np.zeros( ( room, 16, 3 ) )
        sizes = np.zeros( room, np.int64 )
        owner = np.zeros( room, np.int64 )
        got = cutter()( np.ascontiguousarray( corners[cut] ), starts[cut], counts[cut], la, lv, bary, sizes, owner )
        if got >= 0:
            break
        room *= 2
    bary, sizes, owner = bary[:got], sizes[:got], cut[owner[:got]]
    valid = np.arange( 16 )[None, :] < sizes[:, None]
    middle = ( bary * valid[..., None] ).sum( axis=1 ) / sizes[:, None]
    piece_attrs = np.einsum( "pk,pka->pa", middle, corners[owner] )
    # Paint the pieces, and the whole triangles
    whole = np.ones( len( T ), bool )
    whole[cut] = False
    paints = np.empty( len( T ), dtype=object )
    piece_paints = np.empty( got, dtype=object )
    for is_land in ( True, False ):
        rows = np.flatnonzero( whole & ( land == is_land ) )
        if len( rows ):
            paints[rows] = paint_of( corners[rows].mean( axis=1 ), is_land )
        rows = np.flatnonzero( land[owner] == is_land )
        if len( rows ):
            piece_paints[rows] = paint_of( piece_attrs[rows], is_land )
    # A cut triangle whose pieces all came out alike is drawn whole after all
    if got:
        names = { p: i for i, p in enumerate( sorted( set( piece_paints ) ) ) }
        code = np.array( [ names[p] for p in piece_paints ] )
        first = np.flatnonzero( np.r_[ True, owner[1:] != owner[:-1] ] )
        same = np.minimum.reduceat( code, first ) == np.maximum.reduceat( code, first )
        alike = owner[first][same]
        whole[alike] = True
        paints[alike] = piece_paints[first][same]
        drop = np.isin( owner, alike )
        bary, sizes, owner, piece_paints = bary[~drop], sizes[~drop], owner[~drop], piece_paints[~drop]
    # The polygons, straight into the models
    land_model, bed_model = models
    whole_ids = np.flatnonzero( whole )
    for paint in sorted( set( paints[whole_ids] ) | set( piece_paints ) ):
        if paint == "-":                # a piece left to another model
            continue
        tile = paint_tile( paint )
        for is_land, model in ( ( True, land_model ), ( False, bed_model ) ):
            ids = whole_ids[( paints[whole_ids] == paint ) & ( land[whole_ids] == is_land )]
            polys, uvs, normals, faces = [], [], [], []
            if len( ids ):
                pts = corner_xyz[ids]
                polys += pts.tolist()
                uvs += ( pts[:, :, :2] / tile ).tolist()
                nn = corner_normal[ids]
                normals += ( nn / np.linalg.norm( nn, axis=2, keepdims=True ) ).tolist()
                faces += face[ids].tolist()
            pick_ = np.flatnonzero( ( piece_paints == paint ) & ( land[owner] == is_land ) )
            for size in np.unique( sizes[pick_] ):
                group = pick_[sizes[pick_] == size]
                b = bary[group, :size]
                pts = np.einsum( "pvk,pka->pva", b, corner_xyz[owner[group]] )
                nn = np.einsum( "pvk,pka->pva", b, corner_normal[owner[group]] )
                polys += pts.tolist()
                uvs += ( pts[:, :, :2] / tile ).tolist()
                normals += ( nn / np.linalg.norm( nn, axis=2, keepdims=True ) ).tolist()
                faces += face[owner[group]].tolist()
            if not polys:
                continue
            base = len( model.polygons[paint] )
            model.polygons[paint].extend( zip( polys, faces ) )
            model.polygon_uvs.update( ( ( paint, base + i ), uv ) for i, uv in enumerate( uvs ) )
            model.polygon_normals.update( ( ( paint, base + i ), nv ) for i, nv in enumerate( normals ) )


# ---------------------------------------------------------------------------------------------------------------------
# The land's features: the crofts' dykes, the roads with their bridge and poles, and the lochan's dam

DYKE_BASE, DYKE_TOP = 13.0, 7.0     # a drystone dyke's half widths at its foot and its top: 0.65 m and 0.35 m across
DYKE_HEIGHT, DYKE_SINK = 46.0, 6.0  # 1.2 m over the ground, its foot sunk into it
DYKE_STEP = 110.0                   # the longest a stretch of dyke runs straight
POLE_STEP = ( 2000.0, 2300.0 )      # telegraph poles, 50-58 m apart
POLE_HEIGHT = 300.0                 # 7.6 m


def bulk( model, paint, polys ):
    """ Polygons ( k, m, 3 ) added at once, each facing the way its points wind. """
    polys = np.asarray( polys, float )
    if not len( polys ):
        return
    rel = polys[:, 1:] - polys[:, :1]
    normal = np.cross( rel[:, :-1], rel[:, 1:] ).sum( axis=1 )
    size = np.linalg.norm( normal, axis=1 )
    keep = size > 1e-9
    model.polygons[paint].extend( zip( [ list( p ) for p in polys[keep] ], list( normal[keep] / size[keep, None] ) ) )


def at_ground( M, p ):
    """ The ground's mesh height under plan points ( k, 2 ). """
    p = np.asarray( p, float ).reshape( -1, 2 )
    return drape( p[:, 0], p[:, 1], M )


def croft_point( W, u, v ):
    """ The plan points ( e, n ) at u along the croft line and v up from it. """
    u = np.atleast_1d( np.asarray( u, float ) )
    v = np.broadcast_to( np.asarray( v, float ), u.shape )
    return W.croft.at( u ) + v[:, None] * W.croft.left( u )


def keep_clear( W, p, reach=0.0 ):
    """ Which plan points ( k, 2 ) are clear of the roads, the burn, the lochan, the wood and the buildings (by reach). """
    e, n = p[:, 0], p[:, 1]
    ok = np.ones( len( p ), bool )
    for road in W.roads:
        near = road.route.near( e, n, road.half + 60.0 + reach )
        if near.any():
            dist, _, _ = road.route.query( e[near], n[near] )
            ok[np.flatnonzero( near )[dist < road.half + 30.0 + reach]] = False
    near = W.burn.near( e, n, 120.0 + reach )
    if near.any():
        dist, _, _ = W.burn.query( e[near], n[near] )
        ok[np.flatnonzero( near )[dist < 70.0 + reach]] = False
    ok &= ellipse_out( e, n, LOCHAN )[1] > 1.15
    ok &= inside_convex( e, n, PLANTATION ) < -40.0 - reach
    for b in W.buildings:
        if b["kind"] == "kirk":
            half = ( GRAVEYARD[0] / 2 + 30.0, GRAVEYARD[1] / 2 + 30.0 )
        else:
            half = ( b["width"] / 2 + 60.0, b["depth"] / 2 + 60.0 )
        ok &= rect_inside( e, n, b["centre"], b["axis"], half ) < -reach
    return ok


def runs( mask ):
    """ ( first, last ) index pairs of each run of True. """
    m = np.concatenate( ( [ 0 ], np.asarray( mask, np.int8 ), [ 0 ] ) )
    d = np.diff( m )
    return list( zip( np.flatnonzero( d == 1 ), np.flatnonzero( d == -1 ) - 1 ) )


def resample( pts, step ):
    """ A polyline's points ( k, 2 ) at most step apart, evenly along it, and its length. """
    pts = np.asarray( pts, float )
    s = np.concatenate( ( [ 0.0 ], np.cumsum( np.linalg.norm( np.diff( pts, axis=0 ), axis=1 ) ) ) )
    q = np.linspace( 0.0, s[-1], max( 2, int( math.ceil( s[-1] / step ) ) + 1 ) )
    return np.stack( ( np.interp( q, s, pts[:, 0] ), np.interp( q, s, pts[:, 1] ) ), axis=1 ), s[-1]


def dyke_polys( M, p, key, height=DYKE_HEIGHT, base=DYKE_BASE, top=DYKE_TOP ):
    """ A drystone dyke along plan points p ( k >= 2 ) on the ground's mesh: its battered faces, its top and its ends,
    as polygons ( m, 4, 3 ). """
    z = at_ground( M, p )
    t = np.gradient( p, axis=0 )
    t /= np.maximum( np.linalg.norm( t, axis=1 ), 1e-9 )[:, None]
    s = np.stack( ( -t[:, 1], t[:, 0] ), axis=1 )
    crown = z + height + 4.0 * vnoise( p[:, 0], p[:, 1], 900.0, key )
    foot = z - DYKE_SINK
    lf, rf = np.column_stack( ( p + s * base, foot ) ), np.column_stack( ( p - s * base, foot ) )
    lt, rt = np.column_stack( ( p + s * top, crown ) ), np.column_stack( ( p - s * top, crown ) )
    return np.concatenate( (
        np.stack( ( lf[1:], lf[:-1], lt[:-1], lt[1:] ), axis=1 ),
        np.stack( ( rf[:-1], rf[1:], rt[1:], rt[:-1] ), axis=1 ),
        np.stack( ( rt[:-1], rt[1:], lt[1:], lt[:-1] ), axis=1 ),
        np.stack( ( lf[:1], rf[:1], rt[:1], lt[:1] ), axis=1 ),
        np.stack( ( rf[-1:], lf[-1:], lt[-1:], rt[-1:] ), axis=1 ) ) )


def dyke_line( W, M, pts, key, out ):
    """ A dyke through plan points, broken where it would cross a road, the burn or a building; its polygons go on out. """
    p, length = resample( pts, DYKE_STEP )
    if length < 60.0:
        return
    for a, b in runs( keep_clear( W, p ) ):
        if b > a:
            out.append( dyke_polys( M, p[a:b + 1], ( *key, int( a ) ) ) )


def merge_spans( spans, slack=1.0 ):
    out = []
    for a, b in sorted( spans ):
        if b - a <= 1.0:
            continue
        if out and a <= out[-1][1] + slack:
            out[-1][1] = max( out[-1][1], b )
        else:
            out.append( [ a, b ] )
    return out


def croft_dykes( model, W, M ):
    """ The crofts' dykes: up each strip's sides, and across it at its foot, its head and between its fields. """
    C = W.crofts
    last = len( C.start ) - 1

    def fields( j ):
        return [ ( float( C.breaks[j][i] ), float( C.breaks[j][i + 1] ) ) for i, f in enumerate( C.fill[j] ) if f is not None ]

    out = []
    for k, edge in enumerate( C.edges ):
        for a, b in merge_spans( sum( ( fields( j ) for j in ( k - 1, k ) if 0 <= j <= last ), [] ) ):
            v = np.linspace( a, b, max( 2, int( math.ceil( ( b - a ) / 300.0 ) ) + 1 ) )
            dyke_line( W, M, croft_point( W, np.full( len( v ), edge ), v ), ( "edge", k ), out )
    for j in range( last + 1 ):
        lines = sorted( { round( x, 2 ) for ab in fields( j ) for x in ab } )
        u = np.linspace( C.edges[j], C.edges[j + 1], 9 )
        for v in lines:
            dyke_line( W, M, croft_point( W, u, np.full( len( u ), v ) ), ( "across", j, int( v ) ), out )
    if out:
        bulk( model, "sh_rubble", np.concatenate( out ) )


def road_ribbon( model, M, road, step=110.0 ):
    """ A road's surface on the ground: each edge at the higher of the ground's mesh and the road's own level, so it
    neither sinks where the mesh is coarse nor dips into the burn. Not in the play area's corner of the land. """
    s = np.append( np.arange( 0.0, road.route.length, step ), road.route.length )
    c, left = road.route.at( s ), road.route.left( s )
    level = np.interp( s, road.s, road.z )
    edge = []
    for side in ( 1.0, -1.0 ):
        p = c + left * road.half * side
        edge.append( np.column_stack( ( p, np.maximum( at_ground( M, p ), level ) + 4.0 ) ) )
    L, R = edge
    show = ~( ( np.abs( c[:, 0] ) < 2500.0 ) & ( c[:, 1] < 1850.0 ) )
    keep = show[:-1] | show[1:]
    bulk( model, road.paint, np.stack( ( R[:-1], R[1:], L[1:], L[:-1] ), axis=1 )[keep] )


def crossing( route, other, reach ):
    """ Where a route passes nearest another: ( its arc length there, the distance ), or ( None, inf ). """
    s = np.arange( 0.0, route.length, 10.0 )
    p = route.at( s )
    near = other.near( p[:, 0], p[:, 1], reach )
    if not near.any():
        return None, np.inf
    dist, _, _ = other.query( p[near, 0], p[near, 1] )
    k = int( np.argmin( dist ) )
    return float( s[near][k] ), float( dist[k] )


def bridge( model, W ):
    """ The shore road's bridge over the burn by the kirk: a rubble arch under the road between two parapets. """
    road = W.roads[0]
    s0, dist = crossing( road.route, W.burn, 400.0 )
    if s0 is None or dist > 60.0:
        return
    c0, a, l = road.route.at( s0 ), road.route.direction( s0 ), road.route.left( s0 )
    deck = float( np.interp( s0, road.s, road.z ) ) + 4.0
    _, along, _ = W.burn.query( np.array( [ c0[0] ] ), np.array( [ c0[1] ] ) )
    bed = float( np.interp( along[0], W.burn_s, W.burn_bed ) )
    flow = W.burn.direction( along[0] )
    span = 90.0 / max( abs( float( a[0] * flow[1] - a[1] * flow[0] ) ), 0.5 )
    rise = float( np.clip( deck - bed - 16.0, 14.0, 50.0 ) )
    spring, length, top = bed - 6.0, 190.0, deck + 30.0
    out = road.half + 17.0

    def P( x, y, z ):
        return np.array( ( *( c0 + a * x + l * y ), z ) )

    xs = np.linspace( -span / 2, span / 2, 9 )
    arch = spring + rise * ( 1.0 - ( xs / ( span / 2 ) ) ** 2 )
    for side in ( 1.0, -1.0 ):
        y, look = side * out, np.array( ( *( l * side ), 0.0 ) )
        for x0, x1 in ( ( -length, -span / 2 ), ( span / 2, length ) ):
            facing( model, "sh_rubble", [ P( x0, y, bed - 20.0 ), P( x1, y, bed - 20.0 ), P( x1, y, top ), P( x0, y, top ) ], look )
        for i in range( len( xs ) - 1 ):
            facing( model, "sh_rubble", [ P( xs[i], y, arch[i] ), P( xs[i + 1], y, arch[i + 1] ), P( xs[i + 1], y, top ),
                                          P( xs[i], y, top ) ], look )
        # The arch's voussoirs' faces, a band round the opening
        for i in range( len( xs ) - 1 ):
            facing( model, "sh_granite", [ P( xs[i], y + side * 0.6, arch[i] ), P( xs[i + 1], y + side * 0.6, arch[i + 1] ),
                                           P( xs[i + 1] * 1.12, y + side * 0.6, arch[i + 1] + 9.0 ),
                                           P( xs[i] * 1.12, y + side * 0.6, arch[i] + 9.0 ) ], look )
        # The parapet: its cope, the face towards the road and its ends
        inner = side * ( road.half + 1.0 )
        facing( model, "sh_granite", [ P( -length, inner, top ), P( length, inner, top ), P( length, y, top ),
                                       P( -length, y, top ) ], ( 0, 0, 1 ) )
        facing( model, "sh_rubble", [ P( -length, inner, deck - 3.0 ), P( length, inner, deck - 3.0 ), P( length, inner, top ),
                                      P( -length, inner, top ) ], -look )
        for x, t in ( ( -length, -1.0 ), ( length, 1.0 ) ):
            facing( model, "sh_rubble", [ P( x, inner, deck - 40.0 ), P( x, y, deck - 40.0 ), P( x, y, top ), P( x, inner, top ) ],
                    np.array( ( *( a * t ), 0.0 ) ) )
    for i in range( len( xs ) - 1 ):
        facing( model, "sh_rubble", [ P( xs[i], out, arch[i] ), P( xs[i + 1], out, arch[i + 1] ),
                                      P( xs[i + 1], -out, arch[i + 1] ), P( xs[i], -out, arch[i] ) ], ( 0, 0, -1 ) )


def telegraph_poles( model, W, M ):
    """ Poles up the hill road's east side, each with its cross arm and insulators. """
    road = W.roads[1]
    s, k = 500.0, 0
    while s < road.route.length - 300.0:
        side = road.route.left( s )
        side = side if side[0] > 0 else -side
        p = road.route.at( s ) + side * ( road.half + 55.0 + between( 0.0, 30.0, "pole", k ) )
        z = float( at_ground( M, p )[0] )
        lean = np.array( ( between( -0.012, 0.012, "pole", k, "e" ), between( -0.012, 0.012, "pole", k, "n" ), 0.0 ) )
        base, top = np.array( ( *p, z - 10.0 ) ), np.array( ( *p, z + POLE_HEIGHT ) ) + lean * POLE_HEIGHT
        ring = [ np.array( ( math.cos( t ), math.sin( t ), 0.0 ) ) for t in np.arange( 6 ) * math.pi / 3 ]
        for i in range( 6 ):
            d0, d1 = ring[i], ring[( i + 1 ) % 6]
            facing( model, "sh_timber_tar", [ base + d0 * 5.5, base + d1 * 5.5, top + d1 * 4.0, top + d0 * 4.0 ], d0 + d1 )
        model.polygon( "sh_timber_tar", [ top + d * 4.0 for d in ring ] )
        # The cross arm runs across the line of the wires, with an insulator at each wire
        arm = np.array( ( *side, 0.0 ) )
        mid = top - np.array( ( 0.0, 0.0, 16.0 ) )
        rod( model, mid - arm * 36.0, mid + arm * 36.0, 4.5, "sh_timber_tar" )
        for x in ( -30.0, -10.0, 10.0, 30.0 ):
            c = mid + arm * x
            lathe( model, c[:2], [ ( 1.8, c[2] + 2.0 ), ( 1.8, c[2] + 6.0 ), ( 0.6, c[2] + 7.5 ) ], "sh_paint_white", sides=4 )
        s += between( *POLE_STEP, "pole", k, "step" )
        k += 1


def dam( model, W, M ):
    """ The lochan's dam across its outlet: its crest 18 over the water and a spillway notch at the water's level where
    the burn leaves, its downstream face battered down to its toe 110 out. """
    level = W.lochan_level
    crest, lip = level + 18.0, level + 1.0
    burn_e = float( W.burn.at( W.burn.query( np.array( [ LOCHAN[0] ] ), np.array( [ DAM_N ] ) )[1] )[0][0] )
    e = np.arange( LOCHAN[0] - 1500.0, LOCHAN[0] + 1500.0 + 1.0, 50.0 )
    mid = at_ground( M, np.stack( ( e, np.full( len( e ), DAM_N - 12.0 ) ), axis=1 ) )
    stands = np.flatnonzero( mid < crest - 2.0 )
    if not len( stands ):
        return
    k = int( np.argmin( np.abs( e - burn_e ) ) )
    lo, hi = k, k
    while lo > 0 and mid[lo - 1] < crest - 2.0:
        lo -= 1
    while hi < len( e ) - 1 and mid[hi + 1] < crest - 2.0:
        hi += 1
    lo, hi = max( lo - 1, 0 ), min( hi + 1, len( e ) - 1 )
    xs = sorted( set( e[lo:hi + 1] ) | { burn_e - 50.0, burn_e + 50.0 } )
    xs = np.array( [ x for x in xs if e[lo] <= x <= e[hi] ] )
    tops = np.where( np.abs( xs - burn_e ) < 49.9, lip, crest )
    toe_n = DAM_N - 110.0
    toe = at_ground( M, np.stack( ( xs, np.full( len( xs ), toe_n ) ), axis=1 ) ) - 12.0
    heel = np.minimum( at_ground( M, np.stack( ( xs, np.full( len( xs ), DAM_N + 10.0 ) ), axis=1 ) ), level ) - 30.0
    for i in range( len( xs ) - 1 ):
        x0, x1 = xs[i], xs[i + 1]
        t0 = t1 = tops[i] if abs( ( x0 + x1 ) / 2 - burn_e ) < 50.0 else crest
        facing( model, "sh_granite", [ ( x0, DAM_N, heel[i] ), ( x1, DAM_N, heel[i + 1] ), ( x1, DAM_N, t1 ), ( x0, DAM_N, t0 ) ],
                ( 0, 1, 0 ) )
        facing( model, "sh_concrete", [ ( x0, DAM_N, t0 ), ( x1, DAM_N, t1 ), ( x1, DAM_N - 24.0, t1 ), ( x0, DAM_N - 24.0, t0 ) ], ( 0, 0, 1 ) )
        facing( model, "sh_granite", [ ( x0, DAM_N - 24.0, t0 ), ( x1, DAM_N - 24.0, t1 ), ( x1, toe_n, toe[i + 1] ),
                                       ( x0, toe_n, toe[i] ) ], ( 0, -1, 1 ) )
    for x, t in ( ( burn_e - 50.0, 1.0 ), ( burn_e + 50.0, -1.0 ) ):
        facing( model, "sh_granite", [ ( x, DAM_N, lip ), ( x, DAM_N, crest ), ( x, DAM_N - 24.0, crest ), ( x, DAM_N - 24.0, lip ) ],
                ( t, 0, 0 ) )
        g = float( at_ground( M, np.array( [ x, toe_n ] ) )[0] ) - 12.0
        facing( model, "sh_granite", [ ( x, DAM_N - 24.0, lip ), ( x, DAM_N - 24.0, crest ), ( x, toe_n, g + ( crest - lip ) ),
                                       ( x, toe_n, g ) ], ( t, 0, 0 ) )


# ---------------------------------------------------------------------------------------------------------------------
# The hill's things: the plantation, the peat banks, the rocks and the trees

PLANT_HEIGHT = 550.0            # Sitka spruce in their thirties: 14 m
PLANT_CELL = 150.0
PEAT_FACE = ( 30.0, 40.0 )      # a peat bank's cut face: 0.8-1 m
PEAT_BANKS = 12
HILL_ROCKS, SHORE_ROCKS = 40, 40


def land_at( W, M, p ):
    """ The land at plan points ( k, 2 ): ( its paint, its height on the mesh, its normal, its attribute rows ). """
    p = np.asarray( p, float ).reshape( -1, 2 )
    h = 40.0
    z = at_ground( M, p )
    ze, zn = at_ground( M, p + ( h, 0.0 ) ), at_ground( M, p + ( 0.0, h ) )
    normal = np.stack( ( -( ze - z ) / h, -( zn - z ) / h, np.ones( len( p ) ) ), axis=1 )
    normal /= np.linalg.norm( normal, axis=1, keepdims=True )
    u, v = croft_frame( W, p[:, 0], p[:, 1] )
    dist, _, side = W.coast.query( p[:, 0], p[:, 1] )
    d = dist * side
    rows = np.concatenate( ( np.stack( ( p[:, 0], p[:, 1], z, u, v, d, *normal.T ), axis=1 ),
                             ground_fields( W, p[:, 0], p[:, 1], z, normal[:, 2], d ) ), axis=1 )
    return land_paint( W, W.crofts, rows ), z, normal, rows


def spread( candidates, count, spacing, key ):
    """ Up to count of the candidate points ( k, 2 ), taken in an order set by key, none within spacing of another. """
    order = sorted( range( len( candidates ) ), key=lambda i: unit( key, i ) )
    chosen = []
    for i in order:
        if all( np.linalg.norm( candidates[i] - candidates[j] ) >= spacing for j in chosen ):
            chosen.append( i )
            if len( chosen ) == count:
                break
    return chosen


def jittered_grid( e0, e1, n0, n1, step, key ):
    e, n = np.meshgrid( np.arange( e0, e1, step ), np.arange( n0, n1, step ), indexing="ij" )
    e, n = e.ravel(), n.ravel()
    je = np.array( [ between( -0.4, 0.4, key, i, "e" ) for i in range( len( e ) ) ] ) * step
    jn = np.array( [ between( -0.4, 0.4, key, i, "n" ) for i in range( len( e ) ) ] ) * step
    return np.stack( ( e + je, n + jn ), axis=1 )


def bilinear( q, s, t ):
    s, t = np.asarray( s, float )[..., None], np.asarray( t, float )[..., None]
    return ( 1 - s ) * ( 1 - t ) * q[0] + s * ( 1 - t ) * q[1] + s * t * q[2] + ( 1 - s ) * t * q[3]


def canopy_z( M, p ):
    """ The plantation's canopy over plan points: an even-aged crop, so a steady height over the ground, lumpy where
    the crowns are. """
    return ( at_ground( M, p ) + PLANT_HEIGHT + 60.0 * vnoise( p[:, 0], p[:, 1], 1400.0, "plant" )
             + 22.0 * vnoise( p[:, 0], p[:, 1], 170.0, "crowns" ) )


def plantation( model, M ):
    """ The spruce plantation: its canopy over the hill, and round its edge the outer trees' dark wall with their
    pointed tops. """
    q = np.array( PLANTATION, float )
    ns = int( max( np.linalg.norm( q[1] - q[0] ), np.linalg.norm( q[2] - q[3] ) ) / PLANT_CELL )
    nt = int( max( np.linalg.norm( q[3] - q[0] ), np.linalg.norm( q[2] - q[1] ) ) / PLANT_CELL )
    s, t = np.meshgrid( np.linspace( 0, 1, ns + 1 ), np.linspace( 0, 1, nt + 1 ), indexing="ij" )
    p = bilinear( q, s, t )
    z = canopy_z( M, p.reshape( -1, 2 ) ).reshape( s.shape )
    P = np.concatenate( ( p, z[..., None] ), axis=2 )
    bulk( model, "sh_conifer", np.stack( ( P[:-1, :-1], P[1:, :-1], P[1:, 1:], P[:-1, 1:] ), axis=2 ).reshape( -1, 4, 3 ) )
    # The edge, anticlockwise from above, so its outside is on the right
    ring = []
    for a, b in ( ( 0, 1 ), ( 1, 2 ), ( 2, 3 ), ( 3, 0 ) ):
        count = max( 2, int( np.linalg.norm( q[b] - q[a] ) / 60.0 ) )
        f = np.arange( count ) / count
        ring.append( q[a] + f[:, None] * ( q[b] - q[a] ) )
    ring = np.concatenate( ring )
    ring = np.vstack( ( ring, ring[:1] ) )
    foot = at_ground( M, ring ) - 10.0
    top = canopy_z( M, ring ) + np.where( np.arange( len( ring ) ) % 2 == 0, 0.0, 50.0 )
    top[-1] = top[0]
    lo, hi = np.column_stack( ( ring, foot ) ), np.column_stack( ( ring, top ) )
    bulk( model, "sh_conifer", np.stack( ( lo[:-1], lo[1:], hi[1:], hi[:-1] ), axis=1 ) )


def peat_banks( model, W, M ):
    """ Peat banks cut into the moor near the hill road: each a dark cut face along the contour, the bare floor in
    front of it and the cut peats stacked to dry on it. """
    road = W.roads[1]
    banks, k = 0, 0
    while banks < PEAT_BANKS and k < 200:
        key = ( "peat", k )
        k += 1
        s = between( 0.2, 0.55, *key, "s" ) * road.route.length
        side = 1.0 if chance( 0.5, *key, "side" ) else -1.0
        c = road.route.at( s ) + road.route.left( s ) * side * between( 300.0, 1600.0, *key, "off" )
        paint, z, normal, rows = land_at( W, M, c )
        d = rows[0, A_D]
        if paint[0] not in ( "sh_heather", "sh_moor", "sh_hill_grass" ) or not 12000.0 <= d <= 25000.0:
            continue
        downhill = -normal[0, :2] / max( np.linalg.norm( normal[0, :2] ), 1e-6 )
        if np.linalg.norm( normal[0, :2] ) / normal[0, 2] > 0.25:
            continue
        along = np.array( ( -downhill[1], downhill[0] ) )
        length = between( 600.0, 1400.0, *key, "len" )
        x = np.linspace( -length / 2, length / 2, max( 3, int( length / 80.0 ) + 1 ) )
        wiggle = 40.0 * vnoise( x, np.zeros_like( x ), 500.0, key )
        line = c + x[:, None] * along + wiggle[:, None] * downhill
        if not keep_clear( W, line, 200.0 ).all():
            continue
        banks += 1
        g = at_ground( M, line )
        h = between( *PEAT_FACE, *key, "h" )
        face_lo, face_hi = np.column_stack( ( line, g - 6.0 ) ), np.column_stack( ( line, g + h ) )
        back = line - downhill * 220.0
        back = np.column_stack( ( back, at_ground( M, back ) + 1.0 ) )
        front = line + downhill * 150.0
        front = np.column_stack( ( front, at_ground( M, front ) + 2.0 ) )
        floor = np.column_stack( ( line + downhill * 4.0, g + 2.0 ) )
        top_paint = "sh_heather" if paint[0] == "sh_heather" else "sh_moor"
        # The face looks downhill: from the bank's line the right-hand side is along x x up
        flip = np.dot( np.cross( ( *along, 0.0 ), ( 0.0, 0.0, 1.0 ) )[:2], downhill ) > 0
        A, B = ( face_lo[:-1], face_lo[1:] ) if flip else ( face_lo[1:], face_lo[:-1] )
        C, D = ( face_hi[1:], face_hi[:-1] ) if flip else ( face_hi[:-1], face_hi[1:] )
        bulk( model, "sh_peat", np.stack( ( A, B, C, D ), axis=1 ) )
        for poly in np.stack( ( face_hi[:-1], face_hi[1:], back[1:], back[:-1] ), axis=1 ):
            facing( model, top_paint, poly, ( 0, 0, 1 ) )
        for poly in np.stack( ( floor[:-1], floor[1:], front[1:], front[:-1] ), axis=1 ):
            facing( model, "sh_peat", poly, ( 0, 0, 1 ) )
        for end, out in ( ( 0, -along ), ( -1, along ) ):
            facing( model, "sh_peat", [ face_lo[end], face_hi[end], back[end] ], ( *out, 0.0 ) )
        # The peats drying in small stacks along the floor
        for j in range( 0, len( line ) - 1 ):
            if not chance( 0.7, *key, "stack", j ):
                continue
            centre = ( line[j] + line[j + 1] ) / 2 + downhill * between( 50.0, 110.0, *key, "sd", j )
            gz = float( at_ground( M, centre )[0] ) + 1.0
            r, tip = between( 11.0, 15.0, *key, "sr", j ), between( 16.0, 24.0, *key, "sh", j )
            lathe( model, centre, [ ( r, gz ), ( r * 0.75, gz + tip * 0.55 ), ( 0.0, gz + tip ) ], "sh_peat", sides=4,
                   turn=between( 0, 1.5, *key, "st", j ) )


def hill_rocks( model, W, M ):
    """ Boulders and outcrops' blocks on the hill's crags. """
    pts = jittered_grid( -14000.0, 14000.0, 2500.0, 30000.0, 450.0, "hrock" )
    paint, z, normal, rows = land_at( W, M, pts )
    crag = rows[:, FIELD["crag"]]
    ok = ( paint == "sh_hill_rock" ) & ( crag > 0.12 ) & keep_clear( W, pts, 150.0 )
    candidates = pts[ok]
    for i in spread( candidates, HILL_ROCKS, 900.0, "hrock" ):
        p, key = candidates[i], ( "hrock", i )
        size = np.array( ( between( 70, 190, *key, "x" ), between( 60, 150, *key, "y" ), between( 45, 110, *key, "z" ) ) )
        g = float( at_ground( M, p )[0] )
        rock( model, ( p[0], p[1], g + size[2] * 0.12 ), size, key, collide=False, cap=40.0,
              paints={ "low": "sh_hill_rock", "high": "sh_hill_rock" }, turn=between( 0, 180, *key, "t" ),
              lean=( between( -0.1, 0.1, *key, "le" ), between( -0.1, 0.1, *key, "ln" ) ) )


def shore_rocks( model, W, M ):
    """ Rocks along the village shores, where the shingle meets the water. """
    s = np.arange( 0.0, W.coast.length, 120.0 )
    c = W.coast.at( s )
    ok = ( np.abs( c[:, 0] ) > 3200.0 ) & ( np.abs( c[:, 0] ) < 13500.0 )
    s, c = s[ok], c[ok]
    for i in spread( c, SHORE_ROCKS, 300.0, "srock" ):
        key = ( "srock", i )
        p = c[i] + W.coast.left( s[i] ) * between( -150.0, 220.0, *key, "off" )
        if not keep_clear( W, p[None, :], 60.0 )[0]:
            continue
        size = np.array( ( between( 50, 150, *key, "x" ), between( 40, 120, *key, "y" ), between( 30, 85, *key, "z" ) ) )
        g = float( at_ground( M, p )[0] )
        rock( model, ( p[0], p[1], g + size[2] * 0.1 ), size, key, collide=False, cap=30.0,
              paints={ "low": "sh_rock_weed", "high": "sh_rock" }, turn=between( 0, 180, *key, "t" ) )


def tree_spot( W, p, reach=80.0, own=None ):
    """ Whether a tree's trunk at plan point p stands clear of the roads, the burn, the shore and every building's walls
    (own, a building, may hold it: a graveyard's corner). """
    p = np.asarray( p, float ).reshape( 1, 2 )
    for road in W.roads:
        dist, _, _ = road.route.query( p[:, 0], p[:, 1] )
        if dist[0] < road.half + reach:
            return False
    dist, _, _ = W.burn.query( p[:, 0], p[:, 1] )
    if dist[0] < 100.0 + reach:
        return False
    dist, _, side = W.coast.query( p[:, 0], p[:, 1] )
    if dist[0] * side[0] < 350.0:
        return False
    for b in W.buildings:
        if b["kind"] == "yard":
            continue
        extra = OUTSHOT if b.get( "outshot" ) else 0.0
        centre = b["centre"] - b["out"] * extra / 2
        if rect_inside( p[:, 0], p[:, 1], centre, b["axis"], ( b["width"] / 2 + reach, ( b["depth"] + extra ) / 2 + reach ) )[0] > 0:
            return False
    return True


def garden_trees( model, W, M ):
    """ The few trees a Hebridean village has: sycamores in the graveyard, round the farm as its shelter belt and behind
    some of the houses and the inn, with a bush or two by the gables. """
    spots = []
    by_kind = {}
    for b in W.buildings:
        by_kind.setdefault( b["kind"], [] ).append( b )
    kirk = by_kind["kirk"][0]
    for side in ( -1, 1 ):
        spots.append( ( kirk["centre"] + kirk["axis"] * side * 440.0 - kirk["out"] * 300.0, OAK_BIG, 0.85, ( "kirk", side ) ) )
    farm = by_kind["farmhouse"][0]
    for j, along in enumerate( ( -420.0, -150.0, 140.0, 420.0 ) ):
        spots.append( ( farm["centre"] - farm["axis"] * 470.0 + farm["out"] * along, OAK, 1.15, ( "farm", j ) ) )
    for b in by_kind.get( "inn", [] ):
        spots.append( ( b["centre"] - b["out"] * ( b["depth"] / 2 + 260.0 ) + b["axis"] * 160.0, OAK, 1.1, ( "inn", ) ) )
    houses = by_kind.get( "house", [] )
    for i, b in enumerate( houses ):
        if not chance( 0.22, *b["key"], "tree" ):
            continue
        extra = OUTSHOT if b.get( "outshot" ) else 0.0
        spots.append( ( b["centre"] - b["out"] * ( b["depth"] / 2 + extra + 240.0 ) + b["axis"] * between( -120, 120, *b["key"], "tx" ),
                        OAK, between( 0.9, 1.2, *b["key"], "ts" ), b["key"] ) )
    for i, b in enumerate( houses ):
        if not chance( 0.3, *b["key"], "bush" ):
            continue
        side = 1.0 if chance( 0.5, *b["key"], "bush side" ) else -1.0
        spots.append( ( b["centre"] + b["axis"] * side * ( b["width"] / 2 + 70.0 ) + b["out"] * between( -60, 80, *b["key"], "bo" ),
                        BUSH, between( 0.9, 1.3, *b["key"], "bs" ), ( *b["key"], "bush" ) ) )
    placed = []
    for p, path, scale, key in spots:
        reach = 40.0 if path == BUSH else 80.0
        own = kirk if key[0] == "kirk" else None
        if own is None and not tree_spot( W, p, reach ):
            continue
        if any( np.linalg.norm( p - q ) < 250.0 for q in placed ):
            continue
        placed.append( p )
        z = float( at_ground( M, p )[0] ) - 4.0
        s = scale * between( 0.88, 1.12, *key, "scale" )
        name = "bush" if path == BUSH else "sycamore"
        model.props.append( dict( path=path, position=( float( p[0] ), float( p[1] ), z ), yaw=between( 0, 360, *key, "yaw" ),
                                  scale=( s, s, s ), name=f"{name}_{len( model.props )}" ) )


# ---------------------------------------------------------------------------------------------------------------------
# The villages: the houses in their rows along the shore road, the inn, the kirk, and the farm up the hill. They're
# drawn like the terraces' cottages (the same windows, doors, dormers and slates), a little plainer, and nothing of them
# collides.

STOREY_2 = 205.0                        # a two-storey house's eaves over its floor
UPPER_SILL, UPPER_HEAD = 124.0, 172.0   # its upper windows over the floor
LEAN_TO = math.tan( math.radians( 15.0 ) )


def heights( b ):
    """ A building's floor, eaves, ridge and wall foot, with its eaves set by its storeys. """
    floor = b["floor"]
    two = b["storeys"] >= 2.0
    eave = floor + ( STOREY_2 if two else EAVES ) + between( -5.0, 6.0, *b["key"], "eaves" )
    return dict( floor=floor, eave=eave, ridge=eave + b["depth"] / 2 * T47, bottom=b["level"] - 30.0, two=two )


def front_face( b ):
    """ The building's front wall as a Face: r along it from its middle, d out of it. """
    return Face( b["centre"] + b["out"] * b["depth"] / 2, b["out"] )


def gable_wall( model, face, r, depth, bottom, eave, ridge, towards, paint ):
    face.across( model, paint, r, [ ( 0.0, bottom ), ( 0.0, eave ), ( -depth / 2, ridge ), ( -depth, eave ), ( -depth, bottom ) ],
                 towards )


def raking_skews( model, face, r, depth, eave, towards, paint="sh_granite", over=5.0, pitch=T47 ):
    """ The copings up both raking edges of a gable at r (any depth), set out towards ( +-1 along R ). """
    ridge = eave + depth / 2 * pitch
    skew( model, face, r, ( over, eave - over * pitch ), ( -depth / 2, ridge ), paint, inset=towards * 1.5 )
    skew( model, face, r, ( -depth / 2, ridge ), ( -depth - over, eave - over * pitch ), paint, inset=towards * 1.5 )


def face_box( model, face, r0, r1, d0, d1, z0, z1, paints ):
    """ A box square to a face (paints by face, 'default' for the rest, a face painted None not drawn). """
    centre = face.p( ( r0 + r1 ) / 2, ( d0 + d1 ) / 2, ( z0 + z1 ) / 2 )
    if isinstance( paints, dict ):                          # R, -D, Z is right-handed, so +y is the face's -D
        paints = { { "+y": "-y", "-y": "+y" }.get( k, k ): v for k, v in paints.items() }
    model.oriented_box( centre, ( face.R, -face.D, face.Z ), ( abs( r1 - r0 ), abs( d1 - d0 ), abs( z1 - z0 ) ), paints )


def chimney( model, face, r_lo, r_hi, ridge_d, base, top, cans, key, harl ):
    """ A stack straddling the ridge at ridge_d, harled, with its cope and its clay cans. """
    face_box( model, face, r_lo, r_hi, ridge_d - 30.0, ridge_d + 30.0, base, top, { "default": harl, "-z": None } )
    face_box( model, face, r_lo - 2.5, r_hi + 2.5, ridge_d - 32.5, ridge_d + 32.5, top, top + 4.0, "sh_granite" )
    rm = ( r_lo + r_hi ) / 2
    for j in range( cans ):
        c = face.p( rm, ridge_d + ( j - ( cans - 1 ) / 2 ) * 15.0, top + 4.0 )
        h = between( 14.0, 22.0, *key, "can", j )
        lathe( model, c[:2], [ ( 5.4, c[2] ), ( 4.5, c[2] + h ) ], "clay_pot", sides=5, cap=False )
        model.polygon( "sh_tar_black", [ ( *( c[:2] + 4.3 * np.array( ( math.cos( a ), math.sin( a ) ) ) ), c[2] + h - 1.5 )
                                         for a in np.linspace( 0, 2 * math.pi, 6 )[:-1] ] )


def slots_for( width, key ):
    """ A house front's openings, left to right: windows (w) and the door (d). """
    if width < 330.0:
        return pick( ( "wd", "dw" ), *key, "slots" )
    if width < 390.0:
        return "wdw"
    return pick( ( "wdww", "wwdw", "wdw" ), *key, "slots" )


def small_window( model, face, rc, z0, z1, look, half=14.0 ):
    """ A plain window in a back or a gable wall (the face at d 0): a painted margin, a granite sill and dark glass in
    a shallow reveal. Returns its hole. """
    a, b = rc - half, rc + half
    face.quad( model, look["margin"], a - 4.0, a, z0, z1 + 4.0 )
    face.quad( model, look["margin"], b, b + 4.0, z0, z1 + 4.0 )
    face.quad( model, look["margin"], a, b, z1, z1 + 4.0 )
    face.quad( model, "sh_granite", a - 4.0, b + 4.0, z0 - 3.0, z0 )
    reveal( model, face, look["harl"], a, b, z0, z1, 8.0 )
    face.quad( model, "sh_window_dark", a, b, z0, z1, -8.0 )
    face.quad( model, "sh_paint_white", a, b, ( z0 + z1 ) / 2 - 1.2, ( z0 + z1 ) / 2 + 1.2, -7.5 )
    return ( a - 4.0, b + 4.0, z0 - 3.0, z1 + 4.0 )


def back_face( face, depth ):
    """ The face of the wall depth behind face, looking the other way (its r runs the other way). """
    return Face( face.p( 0.0, -depth, 0.0 )[:2], ( -face.D )[:2] )


def village_door( model, face, r0, r1, look, floor, ground ):
    """ A front door as the terraces' (front_door), without the panels' mouldings, which don't show from the play
    area: its margins, the reveal, a granite step, the leaf, the transom and the fanlight. """
    m, top = MARGIN, floor + DOOR_H + FAN
    face.quad( model, look["margin"], r0 - m, r0, ground - 4.0, top + m )
    face.quad( model, look["margin"], r1, r1 + m, ground - 4.0, top + m )
    face.quad( model, look["margin"], r0, r1, top, top + m )
    reveal( model, face, look["harl"], r0, r1, floor, top, 10.0, bottom=False )
    face.level( model, "sh_granite", r0, r1, -10.0, 0.0, floor )
    face.quad( model, "sh_granite", r0, r1, ground - 4.0, floor )
    face.quad( model, look["door"], r0, r1, floor, floor + DOOR_H, -10.0 )
    face.quad( model, "sh_paint_white", r0, r1, floor + DOOR_H, floor + DOOR_H + 2.0, -9.6 )
    face.quad( model, "sh_window_dark", r0, r1, floor + DOOR_H + 2.0, top, -10.0 )


def front_slope( model, face, r0, r1, eave, ridge, ridge_d, dormers, look, over=5.0 ):
    """ A front roof slope from r0 to r1, cut round wallhead dormers at dormers ( r ), with the dormers themselves, the
    rones under its eaves and the soffit. """
    hw, o = DORMER_HW, 4.0
    c = DORMER_RISE / T47
    de, dr = eave + DORMER_RISE, eave + DORMER_RISE + hw * T47
    eave_z = eave - over * T47
    up = face.D * T47 + face.Z
    x = r0
    for rc in dormers:
        face.slope( model, "sh_slate_roof", x, rc - hw - o, over, eave_z, ridge_d, ridge, 1.0 )
        x = rc + hw + o
        for sgn in ( -1.0, 1.0 ):
            xa, xb = rc + sgn * hw, rc + sgn * ( hw + o )
            facing( model, "sh_slate_roof", [ face.p( xb, o - c, de - o * T47 ), face.p( rc, -hw - c, dr ),
                                              face.p( rc, ridge_d, ridge ), face.p( xb, ridge_d, ridge ) ], up )
            facing( model, "sh_slate_roof", [ face.p( xa, over, eave_z ), face.p( xb, over, eave_z ),
                                              face.p( xb, o - c, de - o * T47 ), face.p( xa, -c, de ) ], up )
        dormer( model, face, rc, eave, look )
    face.slope( model, "sh_slate_roof", x, r1, over, eave_z, ridge_d, ridge, 1.0 )
    x, spans = r0, []
    for rc in dormers:
        spans.append( ( x, rc - hw ) )
        x = rc + hw
    spans.append( ( x, r1 ) )
    for a, b in spans:
        if b - a < 1.0:
            continue
        face.box( model, a, b, over - 1.0, over + 5.0, eave - 11.0, eave_z - 0.3, "sh_paint_black" )
        facing( model, "sh_tar_black", [ face.p( a, 0.0, eave - 0.6 ), face.p( b, 0.0, eave - 0.6 ),
                                         face.p( b, over, eave_z - 0.6 ), face.p( a, over, eave_z - 0.6 ) ], -face.Z )


def lean_to( model, face, b, h, oa, ob, look ):
    """ The outshot behind a house from oa to ob ( r ): a harled lean-to under slates or tin, with a small window. """
    depth, over = b["depth"], 4.0
    lz = min( h["eave"] - 12.0, h["floor"] + 120.0 )
    zb = lz - OUTSHOT * LEAN_TO
    d0, d1 = -depth, -depth - OUTSHOT
    roof = pick( ( "sh_slate_roof", "sh_slate_roof", "sh_corrugated_red", "sh_corrugated_green" ), *b["key"], "lean" )
    face.slope( model, roof, oa - over, ob + over, d0, lz, d1 - over, zb - over * LEAN_TO, -1.0 )
    bf = back_face( face, depth + OUTSHOT )
    rb = between( -ob + 30.0, -oa - 30.0, *b["key"], "lean window" )
    hole = small_window( model, bf, rb, h["floor"] + 36.0, h["floor"] + 60.0, look, half=11.0 )
    holed_wall( model, bf, look["harl"], -ob, -oa, h["bottom"], zb, [ hole ] )
    for r, towards in ( ( oa, -1.0 ), ( ob, 1.0 ) ):
        face.across( model, look["harl"], r, [ ( d0, h["bottom"] ), ( d0, lz ), ( d1, zb ), ( d1, h["bottom"] ) ], towards )


def village_house( model, b, h, left, right ):
    """ One house of a row, as the terraces' cottages: the front with its windows and door (and upper windows on two
    storeys), dormers or roof lights, the slated roof, the back with its windows and outshot, its gables where it ends
    the row or stands over its neighbour, with their skews, and its stacks. left and right are its neighbours' heights
    at its r0 and r1 ends (None at the row's ends). Returns its front face and its door's r. """
    face = front_face( b )
    look, key = b["look"], b["key"]
    w, depth = b["width"], b["depth"]
    r0, r1 = -w / 2, w / 2
    floor, eave, ridge, bottom, two = h["floor"], h["eave"], h["ridge"], h["bottom"], h["two"]
    ridge_d, ground, over = -depth / 2, b["level"], 5.0
    slots = slots_for( w, key )
    centres = [ r0 + w * ( j + 0.5 ) / len( slots ) for j in range( len( slots ) ) ]
    holes, wins, door = [], [], 0.0
    for rc, c in zip( centres, slots ):
        a = ( rc - WIN_W / 2, rc + WIN_W / 2 )
        if c == "w":
            wins.append( rc )
            holes.append( ( a[0] - MARGIN, a[1] + MARGIN, floor + WIN_SILL - MARGIN, floor + WIN_HEAD + MARGIN ) )
            sash_window( model, face, *a, floor + WIN_SILL, floor + WIN_HEAD, look )
        else:
            door = rc
            d0, d1 = rc - DOOR_W / 2, rc + DOOR_W / 2
            holes.append( ( d0 - MARGIN, d1 + MARGIN, ground - 4.0, floor + DOOR_H + FAN + MARGIN ) )
            village_door( model, face, d0, d1, look, floor, ground )
        if two:
            holes.append( ( a[0] - MARGIN, a[1] + MARGIN, floor + UPPER_SILL - MARGIN, floor + UPPER_HEAD + MARGIN ) )
            sash_window( model, face, *a, floor + UPPER_SILL, floor + UPPER_HEAD, look )
    chosen = sorted( wins if len( wins ) <= 2 else [ wins[0], wins[-1] ] )
    dormers = chosen if look["roof"] == "wallhead" and not two else []
    for rc in dormers:
        holes.append( ( rc - 19.0, rc + 19.0, eave - 19.0, eave + 33.0 ) )
    holed_wall( model, face, "sh_tar_black", r0, r1, bottom, floor + PLINTH, holes )
    holed_wall( model, face, look["harl"], r0, r1, floor + PLINTH, eave, holes )
    front_slope( model, face, r0, r1, eave, ridge, ridge_d, dormers, look, over )
    if look["roof"] == "lights":
        for rc in chosen:
            roof_light( model, face, rc, eave )
    # A downpipe at the end furthest from the openings, and the lead ridge
    rp = max( ( r0 + 9.0, r1 - 9.0 ), key=lambda r: min( min( abs( r - q[0] ), abs( r - q[1] ) ) for q in holes ) )
    rod( model, face.p( rp, 7.0, eave - 9.0 ), face.p( rp, 7.0, ground + 6.0 ), 3.0, "sh_paint_black" )
    rod( model, face.p( r0, ridge_d, ridge + 1.0 ), face.p( r1, ridge_d, ridge + 1.0 ), 4.0, "sh_lead" )
    # The back: its slope and rones, its windows, and the outshot across part of it
    eave_z = eave - over * T47
    face.slope( model, "sh_slate_roof", r0, r1, ridge_d, ridge, -depth - over, eave_z, -1.0 )
    face.box( model, r0, r1, -depth - over - 5.0, -depth - over + 1.0, eave - 11.0, eave_z - 0.3, "sh_paint_black" )
    bf = back_face( face, depth )
    span = None
    if b.get( "outshot" ):
        width = min( w - 40.0, between( 0.45, 0.7, *key, "outshot w" ) * w )
        span = ( r0, r0 + width ) if chance( 0.5, *key, "outshot side" ) else ( r1 - width, r1 )
        lean_to( model, face, b, h, *span, look )
    back_holes = []
    for j, rc in enumerate( ( r0 + w * 0.3, r1 - w * 0.3 ) ):
        if span and span[0] - 20.0 < rc < span[1] + 20.0:
            if two:
                back_holes.append( small_window( model, bf, -rc, floor + 134.0, floor + 166.0, look ) )
            continue
        if not chance( 0.75, *key, "back", j ):
            continue
        back_holes.append( small_window( model, bf, -rc, floor + 34.0, floor + 74.0, look ) )
        if two:
            back_holes.append( small_window( model, bf, -rc, floor + 134.0, floor + 166.0, look ) )
    holed_wall( model, bf, look["harl"], -r1, -r0, bottom, eave, back_holes )
    # Gables where it ends the row or stands over its neighbour, with skews where it stands well over; stacks on its
    # left party wall and at the row's ends
    for r, nb, towards in ( ( r0, left, -1.0 ), ( r1, right, 1.0 ) ):
        if nb is None or eave > nb["eave"] + 0.5:
            gable_wall( model, face, r, depth, bottom, eave, ridge, towards, look["harl"] )
            if nb is None or eave > nb["eave"] + 3.0:
                raking_skews( model, face, r, depth, eave, towards )
    for r, nb, inward in ( ( r0, left, 1.0 ), ( r1, right, -1.0 ) ):
        if nb is not None and inward < 0:
            continue
        lo, hi = ( min( ridge, nb["ridge"] ), max( ridge, nb["ridge"] ) ) if nb else ( ridge, ridge )
        a, c = ( r - 14.0, r + 14.0 ) if nb else sorted( ( r, r + inward * 28.0 ) )
        chimney( model, face, a, c, ridge_d, lo - 40.0, hi + 46.0, look["cans"], ( *key, "stack", inward ), look["harl"] )
    return face, door


def village_houses( model, W ):
    """ Every row of houses, each house drawn against its neighbours. """
    rows = {}
    for b in W.buildings:
        if b["kind"] == "house":
            rows.setdefault( b["key"][:3], [] ).append( b )
    for houses in rows.values():
        axis = houses[0]["axis"]
        houses.sort( key=lambda b: float( np.dot( b["centre"], axis ) ) )
        hs = [ heights( b ) for b in houses ]
        for i, b in enumerate( houses ):
            village_house( model, b, hs[i], hs[i - 1] if i else None, hs[i + 1] if i + 1 < len( houses ) else None )


KIRK_EAVES = 220.0                      # the kirk's walls: 5.6 m to the eaves
KIRK_WINDOWS = ( -270.0, -110.0, 110.0, 270.0 )
PORCH = ( 62.0, 110.0 )                 # the kirk's porch: half its width, and how far it stands out
HEADSTONES = 34


def arch( rc, spring, half, k=6 ):
    """ An opening's round head: points ( r, z ) from its left springing over its crown to its right one. """
    return [ ( rc - half * math.cos( math.pi * j / k ), spring + half * math.sin( math.pi * j / k ) ) for j in range( k + 1 ) ]


def round_opening( model, face, rc, z0, spring, half, look, fill, depth=14.0, margin=7.0, sill=True ):
    """ A round-headed window or door: dressed granite margins and arch, the reveal with its arched soffit, the fill
    (glass, or a door's leaf) deep in it, and the harl of the spandrels beside the arch. Returns the hole to leave in
    the wall round it. """
    inner, outer = arch( rc, spring, half ), arch( rc, spring, half + margin )
    crown, k = spring + half, len( inner ) - 1
    face.quad( model, "sh_granite", rc - half - margin, rc - half, z0, spring )
    face.quad( model, "sh_granite", rc + half, rc + half + margin, z0, spring )
    for ( ra, za ), ( rb, zb ), ( oa, pa ), ( ob, pb ) in zip( inner, inner[1:], outer, outer[1:] ):
        face.poly( model, "sh_granite", [ ( ra, za ), ( oa, pa ), ( ob, pb ), ( rb, zb ) ] )
    top = crown + margin
    face.poly( model, look["harl"], [ ( rc - half - margin, top ), *outer[: k // 2 + 1] ] )
    face.poly( model, look["harl"], [ ( rc + half + margin, top ), *outer[k // 2:][::-1] ] )
    reveal( model, face, look["harl"], rc - half, rc + half, z0, spring, depth, top=False, bottom=sill )
    for ( ra, za ), ( rb, zb ) in zip( inner, inner[1:] ):
        mid = np.array( ( ( ra + rb ) / 2 - rc, ( za + zb ) / 2 - spring ) )
        facing( model, look["harl"], [ face.p( ra, 0.0, za ), face.p( rb, 0.0, zb ), face.p( rb, -depth, zb ), face.p( ra, -depth, za ) ],
                -face.R * mid[0] - face.Z * mid[1] )
    face.poly( model, fill, [ ( rc - half, z0 ), ( rc + half, z0 ), *inner[::-1] ], d=-depth )
    base = z0
    if sill:
        face.box( model, rc - half - margin - 2.0, rc + half + margin + 2.0, 0.0, 2.5, z0 - 5.0, z0, "sh_granite" )
        base = z0 - 5.0
    return ( rc - half - margin, rc + half + margin, base, top )


def kirk_window( model, face, rc, sill, spring, half, look ):
    hole = round_opening( model, face, rc, sill, spring, half, look, "sh_window_dark" )
    d = -14.0 + 0.6
    face.quad( model, "sh_paint_white", rc - 1.0, rc + 1.0, sill, spring + half - 1.0, d )
    for t in ( 1 / 3, 2 / 3 ):
        z = sill + ( spring - sill ) * t
        face.quad( model, "sh_paint_white", rc - half, rc + half, z - 0.8, z + 0.8, d )
    return hole


def gable_face( face, r, towards ):
    """ The gable wall at r as a Face of its own, looking towards ( +-1 along R ), and how its r follows face's d. """
    g = Face( face.p( r, 0.0, 0.0 )[:2], ( face.R * towards )[:2] )
    return g, float( np.dot( face.D, g.R ) )


def bellcote( model, face, r, ridge_d, ridge ):
    """ The bellcote astride the west gable's apex: a dressed granite base, two piers with the bell hung between them,
    a moulded cap under its own little pitched roof, and a ball on top. """
    bc = r + 6.0
    face_box( model, face, bc - 11.0, bc + 11.0, ridge_d - 22.0, ridge_d + 22.0, ridge - 26.0, ridge + 18.0,
              { "default": "sh_granite", "-z": None } )
    for s in ( -1.0, 1.0 ):
        face_box( model, face, bc - 10.0, bc + 10.0, ridge_d + s * 12.0, ridge_d + s * 22.0, ridge + 18.0, ridge + 62.0,
                  { "default": "sh_granite", "-z": None, "+z": None } )
    c = face.p( bc, ridge_d, 0.0 )[:2]
    lathe( model, c, [ ( 9.0, ridge + 30.0 ), ( 7.6, ridge + 34.0 ), ( 5.6, ridge + 44.0 ), ( 4.6, ridge + 50.0 ),
                       ( 0.0, ridge + 52.0 ) ], "sh_copper_green", sides=8, cap=False )
    rod( model, face.p( bc, ridge_d, ridge + 52.0 ), face.p( bc, ridge_d, ridge + 62.0 ), 1.5, "sh_paint_black" )
    face_box( model, face, bc - 13.0, bc + 13.0, ridge_d - 25.0, ridge_d + 25.0, ridge + 62.0, ridge + 70.0, "sh_granite" )
    peak = ridge + 84.0
    for s in ( -1.0, 1.0 ):
        facing( model, "sh_granite", [ face.p( bc - 14.0, ridge_d + s * 27.0, ridge + 68.0 ), face.p( bc + 14.0, ridge_d + s * 27.0, ridge + 68.0 ),
                                       face.p( bc + 14.0, ridge_d, peak ), face.p( bc - 14.0, ridge_d, peak ) ], face.D * s + face.Z )
        face.across( model, "sh_granite", bc + s * 13.0, [ ( ridge_d - 25.0, ridge + 70.0 ), ( ridge_d + 25.0, ridge + 70.0 ),
                                                           ( ridge_d, peak - 1.0 ) ], s )
    lathe( model, c, [ ( 0.0, peak - 1.0 ), ( 3.0, peak + 1.0 ), ( 4.4, peak + 5.0 ), ( 3.0, peak + 9.0 ), ( 0.0, peak + 11.0 ) ],
           "sh_granite", sides=6, cap=False )


def kirk( model, b ):
    """ The parish kirk: a whitewashed preaching box with tall round-headed windows down both long walls, a gabled
    porch on the south, a window in the east gable, an oculus and the bellcote on the west gable, slates and skews. """
    face, look = front_face( b ), b["look"]
    w, depth = b["width"], b["depth"]
    r0, r1 = -w / 2, w / 2
    floor, bottom = b["floor"], b["level"] - 30.0
    eave = floor + KIRK_EAVES
    ridge_d, ridge, over = -depth / 2, floor + KIRK_EAVES + depth / 2 * T47, 6.0
    eave_z = eave - over * T47
    sill, spring, half = floor + 60.0, floor + 165.0, 20.0
    # The long walls, the porch in the south one
    for wall, porch in ( ( face, True ), ( back_face( face, depth ), False ) ):
        holes = [ kirk_window( model, wall, rc, sill, spring, half, look ) for rc in KIRK_WINDOWS ]
        if porch:
            holes.append( ( -PORCH[0], PORCH[0], bottom, floor + 118.0 ) )
        holed_wall( model, wall, "sh_granite", r0, r1, bottom, floor + 8.0, holes )
        holed_wall( model, wall, look["harl"], r0, r1, floor + 8.0, eave, holes )
    # The gables: the east with a tall window, the west with an oculus and the bellcote
    for r, towards in ( ( r0, -1.0 ), ( r1, 1.0 ) ):
        g, k = gable_face( face, r, towards )
        rm = k * ridge_d
        holes = [ kirk_window( model, g, rm, sill, spring + 6.0, 22.0, look ) ] if towards > 0 else []
        lo, hi = sorted( ( 0.0, k * -depth ) )
        holed_wall( model, g, "sh_granite", lo, hi, bottom, floor + 8.0, holes )
        holed_wall( model, g, look["harl"], lo, hi, floor + 8.0, eave, holes )
        face.across( model, look["harl"], r, [ ( 0.0, eave ), ( ridge_d, ridge ), ( -depth, eave ) ], towards )
        raking_skews( model, face, r, depth, eave, towards, over=over )
        if towards < 0:
            zc = eave + 62.0
            ring = [ ( rm + 17.0 * math.cos( a ), zc + 17.0 * math.sin( a ) ) for a in np.linspace( 0.0, 2 * math.pi, 9 )[:-1] ]
            glass = [ ( rm + 12.0 * math.cos( a ), zc + 12.0 * math.sin( a ) ) for a in np.linspace( 0.0, 2 * math.pi, 9 )[:-1] ]
            g.poly( model, "sh_granite", ring, d=0.6 )
            g.poly( model, "sh_window_dark", glass, d=1.0 )
            bellcote( model, face, r, ridge_d, ridge )
    # The roof: slates, the lead ridge, the rones and soffits
    face.slope( model, "sh_slate_roof", r0, r1, over, eave_z, ridge_d, ridge, 1.0 )
    face.slope( model, "sh_slate_roof", r0, r1, ridge_d, ridge, -depth - over, eave_z, -1.0 )
    rod( model, face.p( r0, ridge_d, ridge + 1.0 ), face.p( r1, ridge_d, ridge + 1.0 ), 4.0, "sh_lead" )
    for d0, d1, edge in ( ( over - 1.0, over + 5.0, 0.0 ), ( -depth - over - 5.0, -depth - over + 1.0, -depth ) ):
        face.box( model, r0, r1, d0, d1, eave - 11.0, eave_z - 0.3, "sh_paint_black" )
        tip = over if edge == 0.0 else -depth - over
        facing( model, "sh_tar_black", [ face.p( r0, edge, eave - 0.6 ), face.p( r1, edge, eave - 0.6 ),
                                         face.p( r1, tip, eave_z - 0.6 ), face.p( r0, tip, eave_z - 0.6 ) ], -face.Z )
    kirk_porch( model, face, b, floor, bottom, look )


def kirk_porch( model, face, b, floor, bottom, look ):
    """ The gabled porch on the kirk's south wall, its round-headed door facing the gate. """
    hw, out = PORCH
    eave = floor + 118.0
    ridge, o = eave + hw * T47, 5.0
    pf = Face( face.p( 0.0, out, 0.0 )[:2], face.D[:2] )
    door = round_opening( model, pf, 0.0, floor, floor + 80.0, 20.0, look, look["door"], depth=12.0, margin=6.0, sill=False )
    pf.level( model, "sh_granite", -20.0, 20.0, -12.0, 0.0, floor )
    pf.quad( model, "sh_granite", -26.0, 26.0, b["level"] - 4.0, floor )
    holed_wall( model, pf, look["harl"], -hw, hw, bottom, eave, [ ( door[0], door[1], b["level"] - 4.0, door[3] ) ] )
    pf.poly( model, look["harl"], [ ( -hw, eave ), ( hw, eave ), ( 0.0, ridge ) ] )
    for s in ( -1.0, 1.0 ):
        face.side( model, look["harl"], s * hw, 0.0, out, bottom, eave, s )
        facing( model, "sh_slate_roof", [ face.p( s * ( hw + o ), out + o, eave - o * T47 ), face.p( s * ( hw + o ), 0.0, eave - o * T47 ),
                                          face.p( 0.0, 0.0, ridge ), face.p( 0.0, out + o, ridge ) ], face.R * s * T47 + face.Z )
        rod( model, pf.p( s * ( hw + 2.0 ), 1.5, eave - 2.0 * T47 + 3.0 ), pf.p( 0.0, 1.5, ridge + 3.0 ), 6.0, "sh_granite" )
    rod( model, face.p( 0.0, 0.0, ridge + 1.0 ), face.p( 0.0, out + o, ridge + 1.0 ), 3.5, "sh_lead" )


def graveyard( model, M, b ):
    """ The kirk's walled graveyard: a mortared rubble wall with a granite cope, gate piers and an iron gate on the
    road side, and headstones in rows round the kirk. """
    c, ax, out = b["centre"], b["axis"], b["out"]
    hx, hy = GRAVEYARD[0] / 2, GRAVEYARD[1] / 2
    z = b["level"]
    gate, t, h = 24.0, 9.0, 44.0
    face = Face( c, out )                                   # r along the kirk, d out of the front
    for r0, r1, d0, d1 in ( ( -hx - t, -gate, hy - t, hy + t ), ( gate, hx + t, hy - t, hy + t ), ( -hx - t, hx + t, -hy - t, -hy + t ),
                            ( -hx - t, -hx + t, -hy, hy ), ( hx - t, hx + t, -hy, hy ) ):
        face_box( model, face, r0, r1, d0, d1, z - 8.0, z + h, { "default": "sh_rubble", "-z": None } )
        face_box( model, face, r0 - 1.5, r1 + 1.5, d0 - 1.5, d1 + 1.5, z + h, z + h + 4.0, { "default": "sh_granite", "-z": None } )
    for s in ( -1.0, 1.0 ):
        a, e = sorted( ( s * gate, s * ( gate + 16.0 ) ) )
        face_box( model, face, a, e, hy - 9.0, hy + 9.0, z - 8.0, z + 64.0, { "default": "sh_granite", "-z": None } )
        face_box( model, face, a - 2.0, e + 2.0, hy - 11.0, hy + 11.0, z + 64.0, z + 69.0, { "default": "sh_granite", "-z": None } )
    for zr in ( z + 6.0, z + 38.0 ):                        # the iron gate's two leaves: rails and bars
        for s in ( -1.0, 1.0 ):
            rod( model, face.p( s * 1.0, hy, zr ), face.p( s * ( gate - 1.0 ), hy, zr ), 1.6, "sh_paint_black" )
    for rb in np.arange( -gate + 3.0, gate - 1.0, 5.5 ):
        rod( model, face.p( rb, hy, z + 3.0 ), face.p( rb, hy, z + 42.0 + ( 4.0 if abs( rb ) > 3.0 else 0.0 ) ), 1.0,
             "sh_paint_black" )
    # Headstones in loose rows, clear of the kirk, the porch's path and the walls
    spots = []
    for i, d in enumerate( np.arange( -hy + 60.0, hy - 50.0, 72.0 ) ):
        for j, r in enumerate( np.arange( -hx + 55.0, hx - 50.0, 58.0 ) ):
            r += between( -14.0, 14.0, "stone r", i, j )
            dd = d + between( -10.0, 10.0, "stone d", i, j )
            if abs( r ) < b["width"] / 2 + 45.0 and abs( dd ) < b["depth"] / 2 + 45.0:
                continue
            if abs( r ) < 60.0 and dd > 0.0:
                continue
            spots.append( ( r, dd, i, j ) )
    rng = np.random.default_rng( zlib.crc32( b"headstones" ) )
    chosen = rng.choice( len( spots ), size=min( HEADSTONES, len( spots ) ), replace=False )
    for q in sorted( chosen ):
        r, d, i, j = spots[q]
        key = ( "stone", i, j )
        p = face.p( r, d, 0.0 )
        g = float( at_ground( M, p[:2] )[0] )
        yaw = math.atan2( out[1], out[0] ) + math.radians( between( -7.0, 7.0, *key, "yaw" ) )
        x = np.array( ( math.sin( yaw ), -math.cos( yaw ), 0.0 ) )   # x, y, z right-handed
        y = np.array( ( math.cos( yaw ), math.sin( yaw ), 0.0 ) )
        lean = math.radians( between( -5.0, 5.0, *key, "lean" ) )
        yl = y * math.cos( lean ) + np.array( ( 0.0, 0.0, 1.0 ) ) * math.sin( lean )
        zl = -y * math.sin( lean ) + np.array( ( 0.0, 0.0, 1.0 ) ) * math.cos( lean )
        width, thick, height = between( 18.0, 28.0, *key, "w" ), between( 3.5, 6.0, *key, "t" ), between( 24.0, 44.0, *key, "h" )
        centre = np.array( ( p[0], p[1], g - 4.0 ) ) + zl * ( height + 4.0 ) / 2
        model.oriented_box( centre, ( x, yl, zl ), ( width, thick, height + 4.0 ),
                            { "default": pick( ( "sh_granite", "sh_granite", "sh_rock" ), *key, "paint" ), "-z": None } )


def slit( model, face, rc, z0, z1, paint, depth=14.0 ):
    """ A slit vent in a rubble wall; returns its hole. """
    reveal( model, face, paint, rc - 3.0, rc + 3.0, z0, z1, depth )
    face.quad( model, "sh_window_dark", rc - 3.0, rc + 3.0, z0, z1, -depth )
    return ( rc - 3.0, rc + 3.0, z0, z1 )


def plank_door( model, face, r0, r1, ground, top, wall ):
    """ A tarred plank door under a timber lintel in a rubble wall; returns its hole. """
    face.box( model, r0 - 9.0, r1 + 9.0, -2.0, 2.0, top, top + 8.0, "sh_timber_tar" )
    reveal( model, face, wall, r0, r1, ground, top, 8.0, bottom=False )
    face.quad( model, "sh_timber_tar", r0, r1, ground - 4.0, top, -8.0 )
    if r1 - r0 > 60.0:
        face.quad( model, "sh_tar_black", ( r0 + r1 ) / 2 - 0.8, ( r0 + r1 ) / 2 + 0.8, ground, top, -7.6 )
    for zl in ( ground + 12.0, top - 18.0 ):
        face.box( model, r0 + 2.0, r1 - 2.0, -8.0, -6.5, zl, zl + 6.0, "sh_timber_tar" )
    return ( r0, r1, ground - 4.0, top )


def steading( model, b ):
    """ One range of the farm's steading: unharled rubble round the yard, its doors (a cart door in the middle of the
    longer ranges), slit vents, and a roof of slates or of tin on the old pitch. """
    face, look, key = front_face( b ), b["look"], b["key"]
    w, depth = b["width"], b["depth"]
    r0, r1 = -w / 2, w / 2
    floor, ground, bottom = b["floor"], b["level"], b["level"] - 30.0
    roof = look["roof"]
    tin = roof != "sh_slate_roof"
    pitch = math.tan( math.radians( 35.0 if tin else PITCH ) )
    eave = floor + 112.0 + between( -4.0, 4.0, *key, "eave" )
    ridge_d = -depth / 2
    ridge = eave + depth / 2 * pitch
    over, verge = 6.0, ( 8.0 if tin else 0.0 )
    eave_z = eave - over * pitch
    count = max( 3, int( w // 100 ) )
    holes = []
    for j in range( count ):
        rc = r0 + w * ( j + 0.5 ) / count
        if j == count // 2 and w >= 400.0:
            holes.append( plank_door( model, face, rc - 44.0, rc + 44.0, ground, ground + 98.0, "sh_rubble" ) )
        elif j % 2 == 1:
            holes.append( plank_door( model, face, rc - 18.0, rc + 18.0, ground, ground + 76.0, "sh_rubble" ) )
        else:
            holes.append( slit( model, face, rc, floor + 40.0, floor + 66.0, "sh_rubble" ) )
    holed_wall( model, face, "sh_rubble", r0, r1, bottom, eave, holes )
    bf = back_face( face, depth )
    back = [ slit( model, bf, rc, floor + 46.0, floor + 70.0, "sh_rubble" ) for rc in ( -w * 0.25, w * 0.25 ) ]
    holed_wall( model, bf, "sh_rubble", r0, r1, bottom, eave, back )
    for r, towards in ( ( r0, -1.0 ), ( r1, 1.0 ) ):
        gable_wall( model, face, r, depth, bottom, eave, ridge, towards, "sh_rubble" )
        if not tin:
            raking_skews( model, face, r, depth, eave, towards, over=over, pitch=pitch )
    face.slope( model, roof, r0 - verge, r1 + verge, over, eave_z, ridge_d, ridge, 1.0 )
    face.slope( model, roof, r0 - verge, r1 + verge, ridge_d, ridge, -depth - over, eave_z, -1.0 )
    rod( model, face.p( r0 - verge, ridge_d, ridge + 1.0 ), face.p( r1 + verge, ridge_d, ridge + 1.0 ), 4.0,
         "sh_lead" if not tin else roof )
    for edge, tip in ( ( 0.0, over ), ( -depth, -depth - over ) ):
        facing( model, "sh_timber_tar", [ face.p( r0, edge, eave - 0.6 ), face.p( r1, edge, eave - 0.6 ),
                                          face.p( r1, tip, eave_z - 0.6 ), face.p( r0, tip, eave_z - 0.6 ) ], -face.Z )


def hay_shed( model, b ):
    """ The steel hay shed by the steading: green sheeting rusting along its foot, two sliding doors on the yard side
    under their track, a shallow tin roof with clear roof lights, and gutters. """
    face, look = front_face( b ), b["look"]
    w, depth = b["width"], b["depth"]
    r0, r1 = -w / 2, w / 2
    floor, ground, bottom = b["floor"], b["level"], b["level"] - 20.0
    pitch = math.tan( math.radians( 12.0 ) )
    eave = floor + 210.0
    ridge_d, over = -depth / 2, 10.0
    ridge = eave + depth / 2 * pitch
    eave_z = eave - over * pitch
    wall, rust, roof = look["harl"], look["margin"], look["roof"]
    bf = back_face( face, depth )
    for f in ( face, bf ):
        f.quad( model, rust, r0, r1, bottom, floor + 14.0 )
        f.quad( model, wall, r0, r1, floor + 14.0, eave )
    for r, towards in ( ( r0, -1.0 ), ( r1, 1.0 ) ):
        face.side( model, rust, r, -depth, 0.0, bottom, floor + 14.0, towards )
        face.across( model, wall, r, [ ( 0.0, floor + 14.0 ), ( 0.0, eave ), ( ridge_d, ridge ), ( -depth, eave ),
                                       ( -depth, floor + 14.0 ) ], towards )
    for a in ( -w * 0.3, w * 0.02 ):
        face_box( model, face, a, a + w * 0.28, 0.0, 3.0, ground, ground + 180.0, { "default": wall, "-y": None } )
        face_box( model, face, a + 1.0, a + w * 0.28 - 1.0, 3.0, 3.6, ground, ground + 16.0, rust )
    rod( model, face.p( -w * 0.32, 4.0, ground + 186.0 ), face.p( w * 0.32, 4.0, ground + 186.0 ), 3.0, "sh_paint_black" )
    face.slope( model, roof, r0 - 8.0, r1 + 8.0, over, eave_z, ridge_d, ridge, 1.0 )
    face.slope( model, roof, r0 - 8.0, r1 + 8.0, ridge_d, ridge, -depth - over, eave_z, -1.0 )
    for t in ( 0.2, 0.5, 0.8 ):
        rc = r0 + w * t
        for d0, d1 in ( ( -40.0, -140.0 ), ( -depth + 40.0, -depth + 140.0 ) ):
            up = ( face.D * ( pitch if d0 > ridge_d else -pitch ) + face.Z )
            facing( model, "sh_glass_dirty", [ roof_at( face, rc - 22.0, d, eave, ridge_d, pitch, 0.6 ) for d in ( d0, d1 ) ] +
                    [ roof_at( face, rc + 22.0, d, eave, ridge_d, pitch, 0.6 ) for d in ( d1, d0 ) ], up )
    rod( model, face.p( r0 - 8.0, ridge_d, ridge + 1.5 ), face.p( r1 + 8.0, ridge_d, ridge + 1.5 ), 6.0, roof )
    for d in ( over + 2.0, -depth - over - 2.0 ):
        rod( model, face.p( r0 - 8.0, d, eave_z - 3.0 ), face.p( r1 + 8.0, d, eave_z - 3.0 ), 5.0, "sh_steel" )


def roof_at( face, r, d, eave, ridge_d, pitch, lift=0.0 ):
    """ A point on a two-slope roof whose eaves are at d 0 and -2 ridge_d, lifted off it. """
    z = eave + ( -d if d > ridge_d else d - 2 * ridge_d ) * pitch
    return face.p( r, d, z + lift )


def inn_front( model, b, face, door ):
    """ The inn's board between its floors, the name on it, and a lamp on a bracket beside the door. """
    floor = b["floor"]
    z0, z1 = floor + 101.0, floor + 117.0
    face_box( model, face, door - 62.0, door + 62.0, 0.0, 2.0, z0, z1, { "default": "sh_paint_black", "-y": None } )
    SM = materials()
    try:
        u0, v0, u1, v1 = SM.rect_uv( "sh_lettering", "camas_roin" )
        W, H, rects = SM.ATLASES["sh_lettering"]
        x0, y0, x1, y1 = rects["camas_roin"]
        aspect = ( x1 - x0 ) / ( y1 - y0 )
    except Exception:
        u0 = None
    if u0 is not None:
        hh = 13.0
        hw = min( 58.0, hh * aspect / 2 )
        zc = ( z0 + z1 ) / 2
        pts = [ face.p( door - hw, 2.3, zc - hh / 2 ), face.p( door + hw, 2.3, zc - hh / 2 ),
                face.p( door + hw, 2.3, zc + hh / 2 ), face.p( door - hw, 2.3, zc + hh / 2 ) ]
        facing( model, "sh_lettering", pts, face.D, uv=[ ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ] )
    lamp = door + 40.0
    rod( model, face.p( lamp, 0.0, floor + 92.0 ), face.p( lamp, 14.0, floor + 92.0 ), 1.6, "sh_paint_black" )
    face_box( model, face, lamp - 4.0, lamp + 4.0, 10.0, 18.0, floor + 78.0, floor + 90.0, "sh_lamp_warm" )
    face_box( model, face, lamp - 5.0, lamp + 5.0, 9.0, 19.0, floor + 90.0, floor + 93.0, "sh_paint_black" )


def village( model, W, M ):
    """ Every building of the villages and the farm, and the graveyard round the kirk. """
    village_houses( model, W )
    for b in W.buildings:
        kind = b["kind"]
        if kind in ( "inn", "farmhouse" ):
            face, door = village_house( model, b, heights( b ), None, None )
            if kind == "inn":
                inn_front( model, b, face, door )
        elif kind == "kirk":
            kirk( model, b )
            graveyard( model, M, b )
        elif kind == "range":
            steading( model, b )
        elif kind == "barn":
            hay_shed( model, b )


# ---------------------------------------------------------------------------------------------------------------------
# The water: the loch from the beach and the rocks out to REACH, and up the hill the lochan, the water going over its
# dam's spillway and the burn running down to the shore

# The loch's grid: quads no bigger than the gaps between these lines (both ways in e), clipped to REACH.
SEA_COLUMNS = ( 0.0, 2150.0, 4000.0, 6000.0, 9000.0, 13000.0, 19000.0, 28000.0, 42000.0, 62000.0, 95000.0 )
SEA_ROWS = ( -1740.0, -3000.0, -4500.0, -6500.0, -9000.0, -13000.0, -19000.0, -28000.0, -42000.0, -62000.0, -95000.0 )
SEA_BAND_N = -1300.0            # beside the beach the water runs on north under the rocky points and the village shores
SEA_SIDES = 64                  # the loch's edge out at REACH: a polygon of this many sides inside the circle
BURN_STEP = 90.0                # the burn's water, sampled this far apart along it
BURN_LIFT = 8.0                 # the burn's surface over its bed
BURN_BANK = 14.0                # each edge of the burn's water dips into its bank over this


def clip_convex( points, planes ):
    """ A plan polygon clipped by half planes ( a, c ), each keeping a . p <= c. """
    pts = [ np.asarray( p, float ) for p in points ]
    for a, c in planes:
        a = np.asarray( a, float )
        out = []
        for k in range( len( pts ) ):
            p, q = pts[k], pts[( k + 1 ) % len( pts )]
            sp, sq = float( np.dot( a, p ) - c ), float( np.dot( a, q ) - c )
            if sp <= 0.0:
                out.append( p )
            if sp * sq < 0.0:
                out.append( p + ( q - p ) * ( sp / ( sp - sq ) ) )
        pts = out
        if len( pts ) < 3:
            return []
    return pts


def reach_planes( radius=REACH, sides=SEA_SIDES ):
    """ The half planes of a polygon of sides sides inside a circle of radius about the play area's middle. """
    half = math.pi / sides
    return [ ( ( math.cos( 2 * half * k + half ), math.sin( 2 * half * k + half ) ), radius * math.cos( half ) )
             for k in range( sides ) ]


def sea_grid( model ):
    """ The loch's surface: the grid's quads, wound to face up, clipped to REACH. """
    es = sorted( { s * c for c in SEA_COLUMNS for s in ( -1.0, 1.0 ) } )
    planes = reach_planes()
    cells = [ ( e0, e1, n1, n0 ) for e0, e1 in zip( es, es[1:] ) for n0, n1 in zip( SEA_ROWS, SEA_ROWS[1:] ) ]
    cells += [ ( e0, e1, SEA_ROWS[0], SEA_BAND_N ) for e0, e1 in zip( es, es[1:] ) if min( abs( e0 ), abs( e1 ) ) >= FRONT ]
    for e0, e1, n0, n1 in cells:
        pts = clip_convex( [ ( e0, n0 ), ( e1, n0 ), ( e1, n1 ), ( e0, n1 ) ], planes )
        if pts:
            model.polygon( "sh_sea", [ ( round( float( p[0] ), 2 ), round( float( p[1] ), 2 ), SEA_Z ) for p in pts ],
                           normal=( 0.0, 0.0, 1.0 ) )


def lochan_water( model, W ):
    """ The lochan's surface, a little over its own outline so its edge lies under the shore, ending at the dam. """
    ce, cn, a, b = LOCHAN
    t = np.linspace( 0.0, 2 * math.pi, 48, endpoint=False )
    pts = clip_convex( np.stack( ( ce + 1.03 * a * np.cos( t ), cn + 1.03 * b * np.sin( t ) ), axis=1 ),
                       [ ( ( 0.0, -1.0 ), -( DAM_N + 2.0 ) ) ] )
    if pts:
        model.polygon( "sh_sea", [ ( float( p[0] ), float( p[1] ), W.lochan_level + 1.5 ) for p in pts ],
                       normal=( 0.0, 0.0, 1.0 ) )


def dam_notch( W, M ):
    """ The dam's spillway, as dam() builds it: ( the notch's e, the water's level, the lip, the toe's n and height ),
    or None where no dam stands. """
    level = W.lochan_level
    crest = level + 18.0
    burn_e = float( W.burn.at( W.burn.query( np.array( [ LOCHAN[0] ] ), np.array( [ DAM_N ] ) )[1] )[0][0] )
    e = np.arange( LOCHAN[0] - 1500.0, LOCHAN[0] + 1500.0 + 1.0, 50.0 )
    mid = at_ground( M, np.stack( ( e, np.full( len( e ), DAM_N - 12.0 ) ), axis=1 ) )
    if not ( mid < crest - 2.0 ).any():
        return None
    toe_n = DAM_N - 110.0
    toe = float( at_ground( M, np.array( [ burn_e, toe_n ] ) )[0] ) - 12.0
    return burn_e, level + 1.5, level + 1.0, toe_n, toe


def spillway_water( model, W, M ):
    """ The sheet of water going over the dam's lip and down its face to the burn. """
    notch = dam_notch( W, M )
    if notch is None:
        return
    burn_e, water, lip, toe_n, toe = notch
    profile = [ ( DAM_N + 2.0, water ), ( DAM_N, lip + 0.6 ), ( DAM_N - 24.0, lip + 0.4 ), ( toe_n, toe + 0.6 ) ]
    e0, e1 = burn_e - 49.0, burn_e + 49.0
    for ( na, za ), ( nb, zb ) in zip( profile, profile[1:] ):
        facing( model, "sh_sea", [ ( e0, na, za ), ( e1, na, za ), ( e1, nb, zb ), ( e0, nb, zb ) ], ( 0.0, -0.3, 1.0 ) )


def burn_water( model, W, M ):
    """ The burn's water from the dam's toe to where it meets the loch: a flat ribbon over its bed (or just over the
    ground's mesh where that's coarser than the channel), as wide as the channel's banks hold it, its edges dipping
    into the banks. """
    route = W.burn
    s0 = float( route.query( np.array( [ LOCHAN[0] ] ), np.array( [ DAM_N - 110.0 ] ) )[1][0] )
    s = np.append( np.arange( s0, route.length, BURN_STEP ), route.length )
    c, left = route.at( s ), route.left( s )
    bed = np.interp( s, W.burn_s, W.burn_bed )
    z = np.maximum( bed + BURN_LIFT, at_ground( M, c ) + 2.0 )
    wet = np.flatnonzero( z < SEA_Z + 1.0 )
    end = int( wet[0] ) if len( wet ) else len( s )
    if end < 2:
        return
    c, left, z, bed = c[:end], left[:end], z[:end], bed[:end]
    half = np.minimum( 30.0 + ( z - bed ) / 0.6, 60.0 )
    rows = []
    for k in ( 1.0, -1.0 ):
        inner = c + left * ( half * k )[:, None]
        outer = c + left * ( ( half + BURN_BANK ) * k )[:, None]
        rows.append( ( np.column_stack( ( inner, z ) ), np.column_stack( ( outer, at_ground( M, outer ) - 3.0 ) ) ) )
    ( li, lo ), ( ri, ro ) = rows
    strips = ( ( ro, ri ), ( ri, li ), ( li, lo ) )
    for i in range( end - 1 ):
        for a, b in strips:
            facing( model, "sh_sea", [ a[i], a[i + 1], b[i + 1], b[i] ], ( 0.0, 0.0, 1.0 ) )


def sea_model():
    """ The water: the loch, the lochan, the spillway and the burn. """
    W, M = world(), mesh()
    model = K.Model()
    sea_grid( model )
    lochan_water( model, W )
    spillway_water( model, W, M )
    burn_water( model, W, M )
    return model


# ---------------------------------------------------------------------------------------------------------------------
# The far shore: across the loch its low hills rising from the water, and behind them the mountains in forced
# perspective, on a polar mesh about the play area. Past the loch's heads the far land carries this shore's hills on
# beside a strath, meeting the land's own mesh exactly along far_side 0.

FAR_R0, FAR_R1 = 22000.0, 95000.0       # the far mesh's rings, from the loch's middle out to the far clip
FAR_RINGS = 50                          # spaced geometrically
FAR_SPLIT = 50000.0                     # inside this the mesh steps FAR_STEP degrees round, outside twice that
FAR_STEP = 0.4
FAR_A0, FAR_A1 = 135.0, 405.0           # its sweep, anticlockwise from the north-west round by the south to the north-east
FAR_SKIRT = 1000.0                      # the far land's skirt runs this far out under the loch
# Forced perspective: a point R from the middle stands for one D away, so it's drawn S = D / R times smaller. Inside
# 32000 everything is its real size.
FAR_R = ( 0.0, 32000.0, 42000.0, 55000.0, 70000.0, 95000.0 )
FAR_D = ( 0.0, 32000.0, 120000.0, 300000.0, 560000.0, 1100000.0 )
# The mountains' envelope: the tops' height (m) at each apparent distance (1.8 degrees up at 4 km, 3 at 15 km)
MOUNT_D = ( 0.0, 150000.0, 250000.0, 400000.0, 600000.0, 1100000.0 )
MOUNT_H = ( 0.0, 120.0, 250.0, 500.0, 800.0, 900.0 )
ISLAND_H = 60.0                         # the far island's top (m)
# The far mesh's attribute columns past the fields: where the far hills' paint takes over, far_side, the coast distance
FAR_COL, F_COL, D_COL = A_F + len( FIELDS ), A_F + len( FIELDS ) + 1, A_F + len( FIELDS ) + 2


def far_scale( R ):
    """ How many times smaller than its real size the far land R from the middle is drawn. """
    R = np.maximum( np.asarray( R, float ), 1.0 )
    return np.maximum( np.interp( R, FAR_R, FAR_D ) / R, 1.0 )


def far_island( e, n ):
    """ The far island's height where it stands out of the water, or -inf: a long low hump, its size in perspective. """
    out, r = ellipse_out( e, n, FAR_ISLAND )
    S = far_scale( np.hypot( e, n ) )
    hump = sstep( ( 1.0 - r ) / 0.45 ) * ( 0.75 + 0.25 * vfractal( e, n, 2400.0, "isle", 2 ) )
    return np.where( r < 1.0, -192.0 + ISLAND_H * 39.37 / S * hump, -np.inf ), out


def far_ground( W, e, n, island=False, parts=False ):
    """ ( z, f, d ) at plan points: the far land's height, how far into it each is ( f, far_side ) and how far from this
    shore ( d, + inland ). The far shore's low hills rise from its waterline; past the loch's heads this shore's hills
    run on, either side of the heads' straths; the mountains stand behind in forced perspective, and under the loch the
    far shore's skirt dips under the bed. parts adds how much of z is the mountains'. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    f = far_side( W, e, n )
    dist, _, side = W.coast.query( e, n )
    d = dist * side
    R = np.hypot( e, n )
    S = far_scale( R )
    sigma = np.minimum( f, -d )
    farshore = ( -192.0 + 42.0 * sstep( sigma / 200.0 )
                 + 1300.0 * sstep( ( sigma - 150.0 ) / 3500.0 ) * ( 0.5 + 0.5 * vfractal( e, n, 9000.0, "far_low", 3 ) )
                 + 120.0 * vfractal( e, n, 2500.0, "far_bumps", 2 ) * sstep( sigma / 600.0 ) )
    base = np.where( d >= 0.0, hills( e, n, d ), farshore )
    strath = -192.0 + 42.0 * sstep( f / 300.0 ) + 0.008 * np.maximum( f - 300.0, 0.0 )
    # The mountains: their shapes at their apparent places, so a far range has a far range's breadth
    ae, an = e * S, n * S
    massif = 0.5 + 0.5 * vfractal( ae, an, 300000.0, "massif", 2 )
    peaks = 1.0 - np.abs( vfractal( ae, an, 90000.0, "peaks", 3 ) )
    ridges = np.clip( 0.55 * massif + 0.45 * peaks ** 2, 0.0, 1.0 )
    mountain = np.interp( R * S, MOUNT_D, MOUNT_H ) * 39.37 * ( 0.35 + 0.65 * ridges ) / S
    strath_w = ( 1.0 - sstep( np.abs( d ) / 6000.0 - 0.3 ) ) * sstep( ( np.abs( e ) - 72000.0 ) / 4000.0 ) \
        * ( 1.0 - sstep( ( R - 86000.0 ) / 6000.0 ) )
    fade = sstep( ( f - 2000.0 ) / 8000.0 ) * ( 1.0 - sstep( ( d - 15000.0 ) / 12000.0 ) ) * ( 1.0 - strath_w )
    z = np.maximum( base, strath ) + mountain * fade
    skirt = -197.0 + ( shoal( -f ) - 80.0 + 197.0 ) * sstep( -f / 400.0 )
    z = np.where( ( f < 0.0 ) & ( d < 0.0 ), skirt, z )
    if island:
        top, out = far_island( e, n )
        rim = -197.0 + ( shoal( out ) - 80.0 + 197.0 ) * sstep( out / 400.0 )
        z = np.where( np.isfinite( top ), np.maximum( z, top ), np.where( out < 1500.0, np.maximum( z, rim ), z ) )
    if parts:
        return z, f, d, np.where( ( f < 0.0 ) & ( d < 0.0 ), 0.0, mountain * fade )
    return z, f, d


# Where a player's eye can be: the beach, the pier, the rocky points, the terraces' tops and the roofs' height
EYES = ( ( 0.0, -1940.0, 78.0 ), ( 0.0, -1500.0, 0.0 ), ( 2000.0, -1600.0, -26.0 ), ( -2000.0, -1600.0, -26.0 ),
         ( 1950.0, -1250.0, 78.0 ), ( -1950.0, -1250.0, 78.0 ), ( 0.0, 1850.0, 112.0 ), ( 1800.0, 1500.0, 112.0 ),
         ( -1800.0, 1500.0, 112.0 ), ( 0.0, 0.0, 600.0 ) )


def far_island_seen( W ):
    """ Whether the far island shows over the far land from anywhere a player stands. It lies out in the loch's mouth,
    which the far shore's west side hides from the bay. """
    ce, cn, a, b = FAR_ISLAND
    t = np.linspace( 0.0, 2 * math.pi, 24, endpoint=False )
    pts = np.concatenate( [ [ ( ce, cn ) ] ] + [ np.stack( ( ce + k * a * np.cos( t ), cn + k * b * np.sin( t ) ), axis=1 )
                                                 for k in ( 0.4, 0.7 ) ] )
    tops, _ = far_island( pts[:, 0], pts[:, 1] )
    targets = np.column_stack( ( pts, tops ) )
    eyes = np.array( EYES, float )
    s = np.linspace( 0.02, 0.98, 240 )
    lines = eyes[:, None, None, :] + s[None, None, :, None] * ( targets[None, :, None, :] - eyes[:, None, None, :] )
    flat_ = lines.reshape( -1, 3 )
    land, f, _ = far_ground( W, flat_[:, 0], flat_[:, 1] )
    clear = flat_[:, 2] > np.where( f > -FAR_SKIRT, land, SEA_Z )
    return bool( clear.reshape( len( eyes ), len( pts ), len( s ) ).all( axis=2 ).any() )


def far_rings():
    """ The rings' radii, and how many steps round each one takes. """
    radii = FAR_R0 * ( FAR_R1 / FAR_R0 ) ** ( np.arange( FAR_RINGS ) / ( FAR_RINGS - 1 ) )
    coarse = int( round( ( FAR_A1 - FAR_A0 ) / ( 2 * FAR_STEP ) ) )
    return radii, np.where( radii < FAR_SPLIT, 2 * coarse, coarse )


def far_mesh( W, island ):
    """ The far mesh: its plan points ( V, 2 ), heights, f and d, and its triangles ( T, 3 ) wound to face up, those
    over the far land and its skirt, over the far island if it shows, and short of LAND_CUT. """
    radii, counts = far_rings()
    plan, starts = [], []
    for R, count in zip( radii, counts ):
        a = np.radians( np.linspace( FAR_A0, FAR_A1, count + 1 ) )
        starts.append( sum( len( p ) for p in plan ) )
        plan.append( np.stack( ( R * np.cos( a ), R * np.sin( a ) ), axis=1 ) )
    plan = np.concatenate( plan )
    tris = []
    for k in range( len( radii ) - 1 ):
        a0, c0, a1, c1 = starts[k], counts[k], starts[k + 1], counts[k + 1]
        if c0 == c1:
            i = np.arange( c0 )
            tris += [ np.stack( ( a0 + i, a0 + i + 1, a1 + i + 1 ), 1 ), np.stack( ( a0 + i, a1 + i + 1, a1 + i ), 1 ) ]
        else:
            # Where the steps double: three triangles to each outer step
            j = np.arange( c1 )
            f0, f1, f2, g0, g1 = a0 + 2 * j, a0 + 2 * j + 1, a0 + 2 * j + 2, a1 + j, a1 + j + 1
            tris += [ np.stack( ( f0, f1, g0 ), 1 ), np.stack( ( f1, g1, g0 ), 1 ), np.stack( ( f1, f2, g1 ), 1 ) ]
    T = np.concatenate( tris ).astype( np.int64 )
    z, f, d, mf = far_ground( W, plan[:, 0], plan[:, 1], island, parts=True )
    keep = ( f[T].max( axis=1 ) > -FAR_SKIRT ) & ( d[T].min( axis=1 ) < LAND_CUT )
    if island:
        out, _ = ellipse_out( plan[:, 0], plan[:, 1], FAR_ISLAND )
        keep |= out[T].min( axis=1 ) < 1500.0
    T = T[keep]
    P = np.column_stack( ( plan, z ) )
    face = np.cross( P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]] )
    down = face[:, 2] < 0.0
    T[down] = T[down][:, ::-1]
    face[down] = -face[down]
    return P, f, d, mf, T, face / np.maximum( np.linalg.norm( face, axis=1, keepdims=True ), 1e-9 )


# ---------------------------------------------------------------------------------------------------------------------
# The far mesh's paints: this shore's (with no crofts) on the far shore's lower ground and past the loch's heads, the
# far hills' hazed paint on the mountains and on the far shore's land from FAR_HAZE out. Its edge on this shore's side
# of the heads is SEAM_BAND over the land's own, so no sliver of sky shows between them.

SEAM_BAND = 200.0
FAR_HAZE = 150000.0             # the far shore's land past this apparent distance (about 44000 out) is all far hills
MOUNT_PAINT = 250.0             # and so is ground the mountains lift more than this


def vertex_normals( P, T ):
    """ Each point's normal: its triangles' area-weighted normals summed (up where it has none). """
    face = np.cross( P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]] )
    N = np.zeros( ( len( P ), 3 ) )
    for k in range( 3 ):
        np.add.at( N, T[:, k], face )
    N[:, 2] += 1e-9
    return N / np.linalg.norm( N, axis=1, keepdims=True )


def far_rows( W, P, f, d, mf, N ):
    """ The far mesh's attribute rows: the land's ( e, n, z, u, v, d, normal ) with no croft frame and d the distance
    from the nearer shore, the fields, then FAR_COL ( >= 0 for the far hills' paint ), F_COL ( far_side plus SEAM_BAND )
    and D_COL ( the distance from this shore ). """
    e, n, z = P[:, 0], P[:, 1], P[:, 2]
    near = np.where( d >= 0.0, d, np.minimum( f, -d ) )
    big = np.full( len( e ), -1e9 )
    R = np.hypot( e, n )
    haze = ( mf - MOUNT_PAINT ) / 150.0 + 0.5 * vnoise( e, n, 6000.0, "far_haze" )
    shore = ( R * far_scale( R ) - FAR_HAZE ) / 30000.0 + vnoise( e, n, 9000.0, "far_haze_r" )
    haze = np.where( d < 0.0, np.maximum( haze, shore ), haze )
    return np.concatenate( ( np.stack( ( e, n, z, big, big, near, N[:, 0], N[:, 1], N[:, 2] ), axis=1 ),
                             ground_fields( W, e, n, z, N[:, 2], near, point=False ),
                             np.stack( ( haze, f + SEAM_BAND, d ), axis=1 ) ), axis=1 )


def far_paint( W, a, is_land ):
    """ The far mesh's paints at attribute rows: "-" where it's the land's, inside the seam band. """
    if not is_land:
        return seabed_paint( a )
    paint = land_paint( W, W.crofts, a )
    paint[a[:, FAR_COL] >= 0.0] = "sh_far_hills"
    paint[( a[:, D_COL] >= 0.0 ) & ( a[:, F_COL] < 0.0 )] = "-"
    return paint


def far_land( model, W ):
    """ The far shore, the land past the loch's heads and the mountains, cut along their paints' lines. Returns whether
    the far island was drawn. """
    island = far_island_seen( W )
    P, f, d, mf, T, face = far_mesh( W, island )
    rows = far_rows( W, P, f, d, mf, vertex_normals( P, T ) )
    corners = rows[T]
    land = corners[:, :, A_Z].max( axis=1 ) >= SEA_Z - 25.0
    lo, hi = corners.min( axis=1 ), corners.max( axis=1 )
    lines = ground_lines( None, lo, hi, land, also=( FAR_COL, F_COL, D_COL ) )
    cut_ground( corners, P[T], rows[:, A_NX:A_NZ + 1][T], face, land, lines,
                lambda a, is_land: far_paint( W, a, is_land ), ( model, model ) )
    return island


# ---------------------------------------------------------------------------------------------------------------------
# The islet off the south-east headland, 600 m out: a low hump of rock and turf, and on it a ruined tower house, its
# walls broken down to different heights, one breached, the barmkin's wall round its yard down to fragments

ISLET_TOP = 70.0                        # the islet's top over the sea's -195: 6.8 m
ISLET_WATER = 0.8                       # its waterline, as a share of the shoal's ellipse (ragged)
ISLET_RINGS = ( 0.0, 0.12, 0.24, 0.36, 0.48, 0.58, 0.66, 0.72, 0.77, 0.81, 0.85, 0.89, 0.94, 1.0, 1.1, 1.25 )
ISLET_SIDES = 56
TOWER = ( 394.0, 315.0 )                # the tower house: 10 by 8 m
TOWER_WALL = 80.0                       # its walls, 2 m thick
TOWER_OUT = ( -0.75, 0.66 )             # its long front looks across the loch to the bay
TOWER_SHIFT = ( -60.0, 40.0 )           # from the islet's middle, onto its top
TOWER_CORNERS = ( 470.0, 590.0, 520.0, 330.0 )  # what stands of its corners over the ground, round from the front left


def islet_ground( e, n ):
    """ The islet's height: a rocky shore rising from a ragged waterline to a rounded top, the foreshore going down to
    the shoal's edge, and outside the shoal's ellipse a skirt under the loch's bed. """
    e, n = np.asarray( e, float ), np.asarray( n, float )
    out, r = ellipse_out( e, n, ISLET )
    rr = r * ( 1.0 + 0.11 * vfractal( e, n, 520.0, "islet_rag", 2 ) )
    x = np.clip( ( ISLET_WATER - rr ) / ISLET_WATER, 0.0, 1.0 )
    top = SEA_Z + 5.0 + ( ISLET_TOP - SEA_Z - 5.0 ) * ( 1.0 - ( 1.0 - np.minimum( x / 0.5, 1.0 ) ) ** 2 )
    top += 22.0 * vfractal( e, n, 260.0, "islet_bumps", 2 ) * np.minimum( x / 0.25, 1.0 )
    fore = SEA_Z + 5.0 - 35.0 * sstep( ( rr - ISLET_WATER ) / ( 1.0 - ISLET_WATER ) ) - 20.0 * sstep( ( rr - 1.0 ) / 0.15 )
    z = np.where( rr < ISLET_WATER, top, fore )
    # Inside the ellipse the loch's bed dips under -235, outside it falls from -225: the islet keeps over the one and
    # under the other
    return np.where( r < 1.0, np.maximum( z, -232.0 ), np.minimum( z, shoal( out ) - 12.0 ) )


def islet_mesh():
    """ The islet's radial mesh: points ( V, 3 ) and triangles wound to face up. """
    ce, cn, a, b = ISLET
    t = np.linspace( 0.0, 2 * math.pi, ISLET_SIDES, endpoint=False )
    pts = [ ( ce, cn ) ]
    for r in ISLET_RINGS[1:]:
        pts += list( zip( ce + r * a * np.cos( t ), cn + r * b * np.sin( t ) ) )
    pts = np.array( pts )
    tris = [ ( 0, 1 + k, 1 + ( k + 1 ) % ISLET_SIDES ) for k in range( ISLET_SIDES ) ]
    for ring in range( len( ISLET_RINGS ) - 2 ):
        a0, a1 = 1 + ring * ISLET_SIDES, 1 + ( ring + 1 ) * ISLET_SIDES
        for k in range( ISLET_SIDES ):
            k1 = ( k + 1 ) % ISLET_SIDES
            tris += [ ( a0 + k, a1 + k, a1 + k1 ), ( a0 + k, a1 + k1, a0 + k1 ) ]
    T = np.array( tris, np.int64 )
    P = np.column_stack( ( pts, islet_ground( pts[:, 0], pts[:, 1] ) ) )
    face = np.cross( P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]] )
    down = face[:, 2] < 0.0
    T[down] = T[down][:, ::-1]
    return P, T


def islet( model ):
    """ The islet's ground: turf on its top, rock where it's steep or bare, wrack and weed between the tides, the light
    bed under the water; cut along the paints' lines. """
    P, T = islet_mesh()
    N = vertex_normals( P, T )
    e, n, z = P[:, 0], P[:, 1], P[:, 2]
    slope = slope_of( N[:, 2] )
    turf = np.minimum.reduce( [ vfractal( e, n, 300.0, "islet_turf", 2 ) + 0.3 - 1.6 * np.maximum( slope - 0.35, 0.0 ),
                                ( z - ( WEED_Z + 45.0 ) ) / 15.0 ] )
    # Attribute rows: e, n, z, then the lines' fields: over the weed, over the low water, turf
    rows = np.column_stack( ( e, n, z, z - WEED_Z, z - ( SEA_Z - 20.0 ), turf ) )
    corners = rows[T]
    lo, hi = corners.min( axis=1 ), corners.max( axis=1 )
    lt, la, lv = [], [], []
    for a in ( 3, 4, 5 ):
        idx = np.flatnonzero( ( lo[:, a] < 0.0 ) & ( hi[:, a] > 0.0 ) )
        lt.append( idx )
        la.append( np.full( len( idx ), a, np.int64 ) )
        lv.append( np.zeros( len( idx ) ) )
    lt, la, lv = np.concatenate( lt ), np.concatenate( la ), np.concatenate( lv )
    order = np.argsort( lt, kind="stable" )

    def paint_of( a, is_land ):
        paint = np.where( a[:, 5] >= 0.0, "sh_hill_grass", "sh_hill_rock" ).astype( object )
        paint[a[:, 3] < 0.0] = "sh_rock_weed"
        paint[a[:, 4] < 0.0] = "sh_seabed"
        return paint

    face = np.cross( P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]] )
    face /= np.maximum( np.linalg.norm( face, axis=1, keepdims=True ), 1e-9 )
    cut_ground( corners, P[T], N[T], face, np.ones( len( T ), bool ), ( lt[order], la[order], lv[order] ), paint_of,
                ( model, model ) )
    # Boulders along its shore
    ce, cn, a, b = ISLET
    for k in range( 9 ):
        t = 2 * math.pi * ( k + between( -0.3, 0.3, "islet_rock", k ) ) / 9
        r = between( 0.74, 0.9, "islet_rock", k, "r" )
        c = np.array( ( ce + r * a * math.cos( t ), cn + r * b * math.sin( t ) ) )
        size = np.array( ( between( 60, 150, "islet_rock", k, "x" ), between( 50, 120, "islet_rock", k, "y" ),
                           between( 40, 90, "islet_rock", k, "z" ) ) )
        ground = float( islet_ground( c[:1], c[1:] )[0] )
        rock( model, ( c[0], c[1], ground + size[2] * 0.2 ), size, ( "islet_rock", k ), collide=False,
              turn=between( 0, 180, "islet_rock", k, "turn" ), paints={ "high": "sh_hill_rock" } )


def ruin_wall( model, face, r0, r1, d0, d1, bottom, tops, paint, end_faces=( True, True ) ):
    """ A broken wall from r0 to r1 between d0 and d1 (its outer face at d1), in columns ( width ) whose tops step:
    tops ( k, ) over equal columns. Draws both faces, the tops and the steps between them, and its ends. """
    tops = np.asarray( tops, float )
    edges = np.linspace( r0, r1, len( tops ) + 1 )
    for k, top in enumerate( tops ):
        a, c = edges[k], edges[k + 1]
        face.quad( model, paint, a, c, bottom, top, d1 )
        face.quad( model, paint, a, c, bottom, top, d0, -1.0 )
        face.level( model, paint, a, c, d0, d1, top )
        if k + 1 < len( tops ) and tops[k + 1] < top - 0.5:
            face.side( model, paint, c, d0, d1, tops[k + 1], top, 1.0 )
        if k > 0 and tops[k - 1] < top - 0.5:
            face.side( model, paint, a, d0, d1, tops[k - 1], top, -1.0 )
    if end_faces[0]:
        face.side( model, paint, r0, d0, d1, bottom, tops[0], -1.0 )
    if end_faces[1]:
        face.side( model, paint, r1, d0, d1, bottom, tops[-1], 1.0 )


def ragged_tops( h0, h1, count, key, breach=None, base=0.0 ):
    """ The column tops along a broken wall from height h0 to h1, in courses, with an optional breach ( from, to as
    shares of its length, the height it's down to ). """
    t = ( np.arange( count ) + 0.5 ) / count
    tops = h0 + ( h1 - h0 ) * t + np.array( [ between( -45.0, 30.0, *key, k ) for k in range( count ) ] )
    if breach:
        b0, b1, low = breach
        dip = np.clip( np.minimum( ( t - b0 ) / 0.08, ( b1 - t ) / 0.08 ), 0.0, 1.0 )
        tops = tops - dip * ( tops - low - np.array( [ between( -20.0, 20.0, *key, "b", k ) for k in range( count ) ] ) )
    return base + np.maximum( np.round( tops / 18.0 ) * 18.0, 36.0 )


def tower_house( model ):
    """ The ruined tower house on the islet's top: four walls of rubble standing to different heights, the front's
    breach, windows and slits on its floors, a door, and the barmkin's broken wall round the yard behind. """
    ce, cn, _, _ = ISLET
    out = np.array( TOWER_OUT ) / np.linalg.norm( TOWER_OUT )
    axis = np.array( ( -out[1], out[0] ) )
    c = np.array( ( ce, cn ) ) + TOWER_SHIFT
    L, Dp = TOWER
    corners = np.array( [ c + axis * sa * L / 2 + out * so * Dp / 2 for sa in ( -1, 1 ) for so in ( -1, 1 ) ] )
    ground = islet_ground( corners[:, 0], corners[:, 1] )
    level, bottom = float( ground.mean() ), float( ground.min() ) - 30.0
    fl, fr, br, bl = TOWER_CORNERS      # front left, front right, back right, back left
    t = TOWER_WALL
    # The four walls as faces round the tower, each from its left corner to its right as seen from outside. The long
    # walls take the corners; the short ones stand between them.
    walls = (
        ( Face( c + out * Dp / 2, out ), -L / 2, L / 2, fl, fr, ( 0.12, 0.42, 150.0 ), True ),
        ( Face( c + axis * L / 2, axis ), -Dp / 2 + t, Dp / 2 - t, fr, br, None, False ),
        ( Face( c - out * Dp / 2, -out ), -L / 2, L / 2, br, bl, None, True ),
        ( Face( c - axis * L / 2, -axis ), -Dp / 2 + t, Dp / 2 - t, bl, fl, None, False ),
    )
    for k, ( face, r0, r1, h0, h1, breach, long ) in enumerate( walls ):
        count = 8 if long else 4
        tops = ragged_tops( h0, h1, count, ( "tower", k ), breach, level )
        ruin_wall( model, face, r0, r1, -t, 0.0, bottom, tops, "sh_rubble" )
        width = ( r1 - r0 ) / count
        # Its openings, where enough of the wall stands round them: slits low down, windows on the floors above
        floors = ( ( 60.0, 12.0, 52.0 ), ( 190.0, 34.0, 64.0 ), ( 320.0, 30.0, 58.0 ), ( 440.0, 24.0, 48.0 ) )
        for j, ( sill, w, h ) in enumerate( floors ):
            for rc in ( ( -0.28, 0.28 ) if long else ( 0.0, ) ):
                rc = rc * ( r1 - r0 ) + ( r0 + r1 ) / 2 + between( -20.0, 20.0, "tower", k, j, rc )
                col = int( np.clip( ( rc - r0 ) // width, 0, count - 1 ) )
                if tops[col] < level + sill + h + 30.0 or not chance( 0.8, "tower", k, j, rc ):
                    continue
                for d, way in ( ( 0.4, 1.0 ), ( -t - 0.4, -1.0 ) ):
                    face.quad( model, "sh_window_dark", rc - w / 2, rc + w / 2, level + sill, level + sill + h, d, way )
        if k == 2:
            face.quad( model, "sh_window_dark", -30.0, 30.0, level, level + 95.0, 0.4 )
    # The rubble fallen out of the breach, and the barmkin's broken wall round the yard behind
    front = walls[0][0]
    for j in range( 4 ):
        p = front.p( -L / 2 + L * between( 0.15, 0.4, "fall", j ), between( 20.0, 90.0, "fall", j, "d" ), 0.0 )
        g = float( islet_ground( p[:1], p[1:2] )[0] )
        rock( model, ( p[0], p[1], g ), ( between( 40, 80, "fall", j, "x" ), between( 30, 60, "fall", j, "y" ),
                                         between( 20, 40, "fall", j, "z" ) ), ( "fall", j ), collide=False,
              turn=between( 0, 180, "fall", j, "t" ), paints={ "low": "sh_rubble", "high": "sh_rubble" } )
    back = Face( c - out * Dp / 2, -out )
    for r0, r1, d1, h0, h1, key in ( ( -L / 2 - 120.0, -L / 2 + 40.0, 260.0, 150.0, 70.0, "b1" ),
                                     ( -L / 2 + 160.0, L / 2 - 20.0, 300.0, 60.0, 120.0, "b2" ) ):
        mid = back.p( ( r0 + r1 ) / 2, d1, 0.0 )
        g = float( islet_ground( mid[:1], mid[1:2] )[0] )
        tops = ragged_tops( h0, h1, 5, ( "barmkin", key ), None, g )
        ruin_wall( model, back, r0, r1, d1 - 36.0, d1, g - 40.0, tops, "sh_rubble" )
    side = Face( c + axis * L / 2, axis )
    mid = side.p( 0.0, 160.0, 0.0 )
    g = float( islet_ground( mid[:1], mid[1:2] )[0] )
    ruin_wall( model, side, -Dp / 2 - 300.0, -Dp / 2 - 80.0, 124.0, 160.0, g - 40.0,
               ragged_tops( 110.0, 40.0, 4, ( "barmkin", "b3" ), None, g ), "sh_rubble" )


# ---------------------------------------------------------------------------------------------------------------------
# The lighthouse on the west headland: a whitewashed round tower of the lighthouse board's sort, its gallery and trim
# ochre, a black lantern and dome, in its walled yard, with the keepers' cottages behind

LIGHT_SIDES = 16
LIGHT_FOOT, LIGHT_HEAD = 92.0, 70.0     # the tower's radius at its foot and under its gallery: 4.7 m across at the foot
LIGHT_HEIGHT = 472.0                    # from its floor to the gallery: 12 m
LANTERN_R, LANTERN_GLASS = 46.0, 80.0   # the lantern's radius and the height of its glazing
YARD_WALL = ( 236.0, 254.0, 66.0 )      # the yard wall round the tower: inner and outer radius, height (1.7 m)
YARD_GATE = 9.0                         # half the gate's angle (degrees)


def tower_radius( z, floor ):
    """ The tower's radius at height z, tapering from its foot to its head. """
    return float( np.interp( z, ( floor + 20.0, floor + LIGHT_HEIGHT - 30.0 ), ( LIGHT_FOOT, LIGHT_HEAD ) ) )


def tower_quad( model, paint, c, angle, floor, x0, x1, z0, z1, lift ):
    """ A quad flat on the tower's face whose middle is at angle (radians), x0..x1 across it, z0..z1 up it, lift off it. """
    u = np.array( ( math.cos( angle ), math.sin( angle ) ) )
    v = np.array( ( -u[1], u[0] ) )
    flatten = math.cos( math.pi / LIGHT_SIDES )
    pts = []
    for x, z in ( ( x0, z0 ), ( x1, z0 ), ( x1, z1 ), ( x0, z1 ) ):
        a = tower_radius( z, floor ) * flatten + lift
        pts.append( ( *( c + u * a + v * x ), z ) )
    facing( model, paint, pts, ( u[0], u[1], 0.0 ) )


def lighthouse( model, M, b ):
    """ The tower: a granite plinth, the tapering whitewashed shaft with its door and windows, the corbelled ochre
    gallery and its railing, the lantern's glazing and astragals round the lens, the dome and its ventilator; and the
    yard wall round it, open towards the track. """
    c = np.asarray( b["centre"], float )
    floor = b["floor"]
    top = floor + LIGHT_HEIGHT
    ring = np.array( [ c + ( LIGHT_FOOT + 10.0 ) * np.array( ( math.cos( a ), math.sin( a ) ) )
                       for a in np.linspace( 0.0, 2 * math.pi, 12, endpoint=False ) ] )
    bottom = min( float( at_ground( M, ring ).min() ), b["level"] ) - 30.0
    # The door looks towards the track's end; the tower's faces are turned so one is square to it
    gate = np.asarray( LIGHT_TRACK[-1], float ) - c
    door = math.atan2( gate[1], gate[0] )
    turn = door - math.pi / LIGHT_SIDES
    lathe( model, c, [ ( LIGHT_FOOT + 8.0, bottom ), ( LIGHT_FOOT + 8.0, floor + 20.0 ), ( LIGHT_FOOT, floor + 20.0 ) ],
           "sh_granite", sides=LIGHT_SIDES, turn=turn, cap=False )
    swell = ( LIGHT_FOOT + LIGHT_HEAD ) / 2 + 2.0
    lathe( model, c, [ ( LIGHT_FOOT, floor + 20.0 ), ( swell, floor + 240.0 ), ( LIGHT_HEAD, top - 30.0 ) ],
           "sh_whitewash", sides=LIGHT_SIDES, turn=turn, cap=False )
    lathe( model, c, [ ( LIGHT_HEAD, top - 30.0 ), ( LIGHT_HEAD + 16.0, top - 6.0 ), ( LIGHT_HEAD + 24.0, top - 6.0 ),
                       ( LIGHT_HEAD + 24.0, top ) ], "sh_paint_yellow", sides=LIGHT_SIDES, turn=turn )
    # The door, and three small windows up the stair, each on a face's middle
    face_step = 2 * math.pi / LIGHT_SIDES
    tower_quad( model, "sh_paint_yellow", c, door, floor, -18.0, 18.0, floor + 20.0, floor + 106.0, 0.3 )
    tower_quad( model, "sh_paint_black", c, door, floor, -14.0, 14.0, floor + 20.0, floor + 100.0, 0.6 )
    for k, ( turns, sill ) in enumerate( ( ( 5, 150.0 ), ( 9, 270.0 ), ( 13, 390.0 ) ) ):
        angle = door + turns * face_step
        tower_quad( model, "sh_paint_yellow", c, angle, floor, -11.0, 11.0, floor + sill - 4.0, floor + sill + 34.0, 0.3 )
        tower_quad( model, "sh_window_dark", c, angle, floor, -7.0, 7.0, floor + sill, floor + sill + 28.0, 0.6 )
    # The gallery's railing: posts round its edge, two rails
    rail_r = LIGHT_HEAD + 20.0
    posts = [ c + rail_r * np.array( ( math.cos( a ), math.sin( a ) ) )
              for a in turn + np.linspace( 0.0, 2 * math.pi, 12, endpoint=False ) ]
    for k, p in enumerate( posts ):
        q = posts[( k + 1 ) % len( posts )]
        rod( model, ( *p, top ), ( *p, top + 40.0 ), 2.6, "sh_paint_black" )
        for z in ( top + 20.0, top + 39.0 ):
            rod( model, ( *p, z ), ( *q, z ), 2.0, "sh_paint_black" )
    # The lantern: its black base, the glazing with its astragals, the lens on its pedestal inside
    glass0, glass1 = top + 30.0, top + 30.0 + LANTERN_GLASS
    lathe( model, c, [ ( LANTERN_R + 2.0, top ), ( LANTERN_R + 2.0, glass0 ) ], "sh_paint_black", sides=12, turn=turn )
    lathe( model, c, [ ( LANTERN_R, glass0 ), ( LANTERN_R, glass1 ) ], "sh_glass", sides=12, turn=turn, cap=False )
    corners = [ c + ( LANTERN_R + 0.6 ) * np.array( ( math.cos( a ), math.sin( a ) ) )
                for a in turn + np.linspace( 0.0, 2 * math.pi, 12, endpoint=False ) ]
    for k, p in enumerate( corners ):
        rod( model, ( *p, glass0 ), ( *p, glass1 ), 2.4, "sh_paint_black" )
        rod( model, ( *p, ( glass0 + glass1 ) / 2 ), ( *corners[( k + 1 ) % 12], ( glass0 + glass1 ) / 2 ), 1.6,
             "sh_paint_black" )
    lathe( model, c, [ ( 10.0, glass0 ), ( 8.0, glass0 + 16.0 ) ], "sh_copper", sides=6, cap=False )
    lathe( model, c, [ ( 17.0, glass0 + 16.0 ), ( 20.0, glass0 + 40.0 ), ( 17.0, glass0 + 64.0 ) ], "sh_glass_dirty",
           sides=8 )
    # The dome, its ventilator ball and the conductor
    lathe( model, c, [ ( LANTERN_R, glass1 ), ( LANTERN_R + 6.0, glass1 ), ( LANTERN_R + 6.0, glass1 + 3.0 ),
                       ( LANTERN_R - 2.0, glass1 + 18.0 ), ( 26.0, glass1 + 31.0 ), ( 0.0, glass1 + 37.0 ) ],
           "sh_paint_black", sides=12, turn=turn )
    vent = glass1 + 35.0
    lathe( model, c, [ ( 4.0, vent ), ( 4.0, vent + 7.0 ), ( 7.5, vent + 10.0 ), ( 7.5, vent + 17.0 ), ( 0.0, vent + 22.0 ) ],
           "sh_paint_black", sides=6 )
    rod( model, ( *c, vent + 21.0 ), ( *c, vent + 46.0 ), 1.4, "sh_paint_black" )
    yard_wall( model, M, c, b["level"], door )


def yard_wall( model, M, c, level, gate ):
    """ The whitewashed wall round the tower's yard, following the ground, with its gate's piers towards the track. """
    inner, outer, height = YARD_WALL
    half = math.radians( YARD_GATE )
    angles = gate + half + np.linspace( 0.0, 2 * math.pi - 2 * half, 47 )
    dirs = np.stack( ( np.cos( angles ), np.sin( angles ) ), axis=1 )
    ground = at_ground( M, c + dirs * ( ( inner + outer ) / 2 ) )
    tops, feet = ground + height, ground - 30.0
    rin, rout = c + dirs * inner, c + dirs * outer
    for k in range( len( angles ) - 1 ):
        i0, i1, o0, o1 = rin[k], rin[k + 1], rout[k], rout[k + 1]
        mid = ( dirs[k] + dirs[k + 1] ) / 2
        out = np.array( ( *mid, 0.0 ) )
        facing( model, "sh_whitewash", [ ( *o0, feet[k] ), ( *o1, feet[k + 1] ), ( *o1, tops[k + 1] ), ( *o0, tops[k] ) ], out )
        facing( model, "sh_whitewash", [ ( *i0, feet[k] ), ( *i1, feet[k + 1] ), ( *i1, tops[k + 1] ), ( *i0, tops[k] ) ], -out )
        facing( model, "sh_whitewash", [ ( *i0, tops[k] ), ( *o0, tops[k] ), ( *o1, tops[k + 1] ) ], ( 0.0, 0.0, 1.0 ) )
        facing( model, "sh_whitewash", [ ( *i0, tops[k] ), ( *o1, tops[k + 1] ), ( *i1, tops[k + 1] ) ], ( 0.0, 0.0, 1.0 ) )
    # The gate's piers, square, a little taller than the wall, each on its wall's end
    for k, way in ( ( 0, 1.0 ), ( len( angles ) - 1, -1.0 ) ):
        d = dirs[k]
        perp = np.array( ( -d[1], d[0] ) )
        centre = c + d * ( inner + outer ) / 2 + perp * way * 6.0
        model.oriented_box( ( *centre, ( feet[k] + tops[k] + 14.0 ) / 2 ), ( ( *d, 0.0 ), ( *perp, 0.0 ), ( 0.0, 0.0, 1.0 ) ),
                            ( 26.0, 26.0, tops[k] + 14.0 - feet[k] ), { "default": "sh_whitewash", "-z": None } )


# ---------------------------------------------------------------------------------------------------------------------
# The far shore's townships: crofthouses up from the water across the loch, some with a byre at the end, each sitting
# on the far mesh as its triangles lie there

CROFTHOUSES = 11
CROFT_UP = ( 600.0, 1800.0 )            # how far up from the far shore's waterline they stand
CROFT_OUT = 31500.0                     # and how far out at most: the far land is its real size inside 32000
CROFT_SPACING = 1600.0
CROFT_RISE = 120.0                      # the most the ground may rise across a crofthouse's footprint
TOWNSHIPS = ( ( -9500.0, -26000.0 ), ( 6500.0, -26500.0 ) )     # the far shore's two townships gather round these
CROFTHOUSE = ( 400.0, 220.0, 112.0 )    # a crofthouse's length, depth and eaves over its floor: 10 by 5.6 m
BYRE = ( 300.0, 180.0, 92.0 )
CROFT_HARLS = ( "sh_harl", "sh_harl", "sh_harl_cream", "sh_whitewash", "sh_harl_shade", "sh_whitewash", "sh_harl" )


def barycentric( p, a, b, c ):
    """ p's barycentric coordinates in the plan triangle a, b, c. """
    m = np.array( ( ( b[0] - a[0], c[0] - a[0] ), ( b[1] - a[1], c[1] - a[1] ) ) )
    s, t = np.linalg.solve( m, ( p[0] - a[0], p[1] - a[1] ) )
    return np.array( ( 1.0 - s - t, s, t ) )


def far_cell( radii, counts, e, n ):
    """ The far mesh's triangle under a plan point, as its corners ( 3, 2 ) and the point's barycentric coordinates in
    it, or None where the rings' steps change or the sweep ends. """
    k = int( np.searchsorted( radii, math.hypot( e, n ) ) ) - 1
    alpha = ( math.degrees( math.atan2( n, e ) ) - FAR_A0 ) % 360.0
    for kk in ( k, k - 1, k + 1 ):
        if kk < 0 or kk + 1 >= len( radii ) or counts[kk] != counts[kk + 1]:
            continue
        step = ( FAR_A1 - FAR_A0 ) / counts[kk]
        j = int( alpha // step )
        for jj in ( j, j - 1, j + 1 ):
            if not 0 <= jj < counts[kk]:
                continue
            a0, a1 = math.radians( FAR_A0 + jj * step ), math.radians( FAR_A0 + ( jj + 1 ) * step )
            corners = np.array( [ ( radii[ring] * math.cos( a ), radii[ring] * math.sin( a ) )
                                  for ring, a in ( ( kk, a0 ), ( kk, a1 ), ( kk + 1, a1 ), ( kk + 1, a0 ) ) ] )
            for tri in ( ( 0, 1, 2 ), ( 0, 2, 3 ) ):
                pts = corners[list( tri )]
                bary = barycentric( ( e, n ), *pts )
                if bary.min() >= -1e-7:
                    return pts, bary
    return None


def far_mesh_z( W, points ):
    """ The far mesh's height at plan points ( k, 2 ) as its triangles lie there (the far ground's own height where no
    triangle between rings of equal steps is found). """
    radii, counts = far_rings()
    corners, weights = [], []
    for e, n in np.asarray( points, float ).reshape( -1, 2 ):
        cell = far_cell( radii, counts, e, n )
        if cell is None:
            cell = ( np.array( [ ( e, n ) ] * 3 ), np.array( ( 1.0, 0.0, 0.0 ) ) )
        corners.append( cell[0] )
        weights.append( cell[1] )
    corners = np.concatenate( corners )
    z = far_ground( W, corners[:, 0], corners[:, 1] )[0].reshape( -1, 3 )
    return ( z * np.array( weights ) ).sum( axis=1 )


def croft_footprint( centre, out, size, along=( -1.0, 0.0, 1.0 ), across=( -1.0, 0.0, 1.0 ) ):
    """ Plan points over a building's footprint: its centre, its front facing out. """
    L, Dp = size[0], size[1]
    axis = np.array( ( -out[1], out[0] ) )
    return np.array( [ centre + axis * a * L / 2 + out * b * Dp / 2 for a in along for b in across ] )


def croft_sites( W ):
    """ The crofthouses' places on the far shore, ( centre, out ): the flattest spots up from its waterline near the
    townships, spaced apart, each looking out across the loch. """
    cands = []
    for route in ( W.far_west, W.far_east ):
        s = np.arange( 0.0, route.length, 200.0 )
        base, left = route.at( s ), route.left( s )
        for up in np.arange( CROFT_UP[0], CROFT_UP[1] + 1.0, 200.0 ):
            p = base - left * up
            keep = np.hypot( p[:, 0], p[:, 1] ) < CROFT_OUT
            cands += list( zip( p[keep], left[keep] ) )
    if not cands:
        return []
    centres = np.array( [ q for q, _ in cands ] )
    _, f, d = far_ground( W, centres[:, 0], centres[:, 1] )
    feet = np.concatenate( [ croft_footprint( q, o, CROFTHOUSE ) for q, o in cands ] )
    zf = far_ground( W, feet[:, 0], feet[:, 1] )[0].reshape( len( cands ), -1 )
    rise = zf.max( axis=1 ) - zf.min( axis=1 )
    town = np.min( [ np.hypot( centres[:, 0] - te, centres[:, 1] - tn ) for te, tn in TOWNSHIPS ], axis=0 )
    ok = ( d < -1500.0 ) & ( f > CROFT_UP[0] - 150.0 ) & ( f < CROFT_UP[1] + 150.0 ) & ( rise < CROFT_RISE )
    score = rise + 0.012 * town + np.array( [ 30.0 * unit( "croft site", round( q[0] ), round( q[1] ) ) for q in centres ] )
    chosen = []
    for k in np.argsort( np.where( ok, score, np.inf ) ):
        if not ok[k]:
            break
        q, o = cands[k]
        if all( np.linalg.norm( q - c ) >= CROFT_SPACING for c, _ in chosen ):
            turn = math.radians( between( -12.0, 12.0, "croft", round( q[0] ), round( q[1] ) ) )
            o = np.array( ( o[0] * math.cos( turn ) - o[1] * math.sin( turn ), o[0] * math.sin( turn ) + o[1] * math.cos( turn ) ) )
            chosen.append( ( q, o ) )
            if len( chosen ) == CROFTHOUSES:
                break
    return chosen


def croft_building( model, W, centre, out, size, key, byre=False ):
    """ A crofthouse (or its byre) on the far mesh: harled walls (a byre's rubble) down past the ground, gables, its
    slated or tin roof, the house's gable stacks, its door and windows. """
    L, Dp, eave_h = size
    out = np.asarray( out, float ) / np.linalg.norm( out )
    face = Face( np.asarray( centre, float ) + out * Dp / 2, out )
    z = far_mesh_z( W, croft_footprint( np.asarray( centre, float ), out, size, np.linspace( -1.0, 1.0, 5 ) ) )
    floor = float( z.max() - 0.4 * ( z.max() - z.min() ) ) + 4.0
    bottom = float( z.min() ) - 40.0
    eave = floor + eave_h + between( -8.0, 8.0, *key, "eave" )
    ridge = eave + Dp / 2 * T47
    wall = "sh_rubble" if byre else pick( CROFT_HARLS, *key, "harl" )
    face.quad( model, wall, -L / 2, L / 2, bottom, eave )
    face.quad( model, wall, -L / 2, L / 2, bottom, eave, -Dp, -1.0 )
    for r, towards in ( ( -L / 2, -1.0 ), ( L / 2, 1.0 ) ):
        face.across( model, wall, r, [ ( 0.0, bottom ), ( 0.0, eave ), ( -Dp / 2, ridge ), ( -Dp, eave ), ( -Dp, bottom ) ],
                     towards )
    roof = pick( ( "sh_corrugated_red", "sh_corrugated_green", "sh_slate_roof" ), *key, "roof" ) if byre else "sh_slate_roof"
    over = 8.0
    face.slope( model, roof, -L / 2 - 6.0, L / 2 + 6.0, over, eave - over * T47, -Dp / 2, ridge, 1.0 )
    face.slope( model, roof, -L / 2 - 6.0, L / 2 + 6.0, -Dp - over, eave - over * T47, -Dp / 2, ridge, -1.0 )
    if byre:
        door = between( -L / 4, L / 4, *key, "door" )
        face.quad( model, "sh_window_dark", door - 40.0, door + 40.0, floor, floor + 76.0, 0.5 )
        return
    for r in ( -L / 2 + 16.0, L / 2 - 16.0 ):
        face_box( model, face, r - 15.0, r + 15.0, -Dp / 2 - 28.0, -Dp / 2 + 28.0, ridge - 40.0, ridge + 34.0,
                  { "default": wall, "-z": None } )
    door = between( -30.0, 30.0, *key, "door" )
    face.quad( model, pick( HOUSE_DOORS, *key, "door paint" ), door - 16.0, door + 16.0, floor, floor + 80.0, 0.5 )
    margin = pick( HOUSE_MARGINS, *key, "margin" )
    for r in ( -L * 0.29, L * 0.29 ):
        face.quad( model, margin, r - 19.0, r + 19.0, floor + 30.0, floor + 82.0, 0.3 )
        face.quad( model, "sh_window_dark", r - 15.0, r + 15.0, floor + 34.0, floor + 78.0, 0.6 )


def crofthouses( model, W ):
    """ The townships: each crofthouse, most with a byre at one end, set back a little up the slope. """
    for k, ( q, o ) in enumerate( croft_sites( W ) ):
        key = ( "crofthouse", k )
        croft_building( model, W, q, o, CROFTHOUSE, key )
        if not chance( 0.65, *key, "byre" ):
            continue
        axis = np.array( ( -o[1], o[0] ) )
        way = 1.0 if chance( 0.5, *key, "byre side" ) else -1.0
        spot = q + axis * way * ( CROFTHOUSE[0] / 2 + BYRE[0] / 2 + between( 40.0, 160.0, *key, "byre gap" ) ) \
            - o * between( 0.0, 120.0, *key, "byre back" )
        _, f, _ = far_ground( W, np.array( [ spot[0] ] ), np.array( [ spot[1] ] ) )
        if f[0] > 350.0:
            croft_building( model, W, spot, o, BYRE, ( *key, "byre" ), byre=True )


# ---------------------------------------------------------------------------------------------------------------------
# The models

def land():
    """ The land round the play area: the ground's mesh with its fields, and on it the dykes, the roads, the bridge, the
    poles, the dam, the plantation, the peat banks, the rocks, the garden trees and the villages. Drawn only. """
    W, M = world(), mesh()
    model = K.Model()
    model.extend( ground_pair()[0] )
    croft_dykes( model, W, M )
    for road in W.roads:
        road_ribbon( model, M, road )
    bridge( model, W )
    telegraph_poles( model, W, M )
    dam( model, W, M )
    plantation( model, M )
    peat_banks( model, W, M )
    hill_rocks( model, W, M )
    shore_rocks( model, W, M )
    garden_trees( model, W, M )
    village( model, W, M )
    model.boxes, model.hulls = [], []
    return configure( model )


def seabed():
    """ The loch's bed from under the beach out to the far shore's skirt. Drawn only. """
    model = K.Model()
    model.extend( ground_pair()[1] )
    model.boxes, model.hulls = [], []
    return configure( model )


def sea():
    """ The water: the loch, the lochan, the dam's spillway and the burn. """
    return configure( sea_model() )


def far():
    """ Across the loch and beyond: the far shore and the mountains, the land past the loch's heads, the islet and its
    ruined tower house, the lighthouse and its keepers' cottages, and the far shore's townships. """
    W, M = world(), mesh()
    model = K.Model()
    W.far_island_shown = far_land( model, W )
    islet( model )
    tower_house( model )
    for b in W.buildings:
        if b["kind"] == "lighthouse":
            lighthouse( model, M, b )
        elif b["kind"] == "keepers":
            village_house( model, b, heights( b ), None, None )
    crofthouses( model, W )
    model.boxes, model.hulls = [], []
    return configure( model )


# ---------------------------------------------------------------------------------------------------------------------
# Previews

def greybox():
    """ The play area as plain blocks, for the previews only: the braes, yards, roads, beach and seawall at their levels
    and the distillery's buildings as boxes (DESIGN.md's footprints), both halves. """
    m = K.Model()
    g, w, b = "pv_ground", "pv_walk", "pv_block"
    steps = [ -1350, -1120, -1000, -860, -730, -600, 400, 520, 640, 760, 880, 1600 ]
    for s in ( -1, 1 ):
        e0, e1 = sorted( ( s * 1900, s * 2150 ) )
        for na, nb in zip( steps, steps[1:] ):
            m.polygon( g, [ ( e0, na, brae_z( na ) ), ( e1, na, brae_z( na ) ), ( e1, nb, brae_z( nb - 1e-6 ) ),
                            ( e0, nb, brae_z( nb - 1e-6 ) ) ] )
        m.box( ( min( s * 1900, s * 2150 ), 1550, 48 ), ( max( s * 1900, s * 2150 ), 1600, 84 ), "pv_block" )

        def area( ea, eb, n0, n1, z, paint=g ):
            flat( m, paint, min( s * ea, s * eb ), max( s * ea, s * eb ), n0, n1, z )

        def block( ea, eb, n0, n1, z0, z1 ):
            m.box( ( min( s * ea, s * eb ), n0, z0 ), ( max( s * ea, s * eb ), n1, z1 ), { "default": b, "+z": "pv_roof" } )

        area( 760, 1900, 1310, 1550, 48 )
        area( 420, 760, 1310, 1820, 48 )
        area( 0, 420, 1580, 1820, 48 )
        area( 0, 1900, 1820, 1900, 48 )
        block( 0, 420, 1820, 1850, 48, 90 )
        block( 1450, 1900, 1550, 1900, 48, 300 )
        block( 1000, 1450, 1550, 1900, 48, 260 )
        block( 760, 1000, 1550, 1900, 48, 280 )
        block( 880, 1900, 880, 1310, 48, 380 )
        area( 420, 880, 880, 1310, 48 )
        block( 0, 420, 1080, 1580, 48, 460 )
        block( 0, 420, 400, 1080, 48, 400 )
        block( 0, 420, -600, 400, 0, 480 )
        block( 0, 420, -900, -600, 0, 260 )
        block( 0, 420, -1350, -900, -50, 270 )
        area( 420, 1900, -600, 400, 0 )
        block( 420, 1900, 400, 880, 0, 330 )
        block( 420, 1900, -1120, -600, 0, 300 )
        area( 420, 1900, -1350, -1120, -50, w )
        block( 0, 2150, -1350, -1330, -150, -10 )
        e0, e1 = sorted( ( s * 150, s * 2150 ) )
        m.polygon( "pv_sand", [ ( e0, -1760, BEACH_FOOT ), ( e1, -1760, BEACH_FOOT ), ( e1, -1350, BEACH_TOP ),
                                ( e0, -1350, BEACH_TOP ) ] )
    m.box( ( -150, -1950, -80 ), ( 150, -1350, -50 ), { "default": "pv_block", "+z": "pv_walk" } )
    m.box( ( -394, -2170, -230 ), ( 394, -1950, -110 ), { "default": "pv_hull", "+z": "pv_walk" } )
    return m


def prop_shapes( models ):
    """ The props as blobs: a trunk and a crown for a tree, a mound for a bush. """
    m = K.Model()
    for model in models:
        for prop in model.props:
            e, n, z = prop["position"]
            s = prop["scale"]
            if prop["path"] == BUSH:
                lathe( m, ( e, n ), [ ( 72 * s[0], z + 19 * s[2] ), ( 60 * s[0], z + 55 * s[2] ), ( 0.0, z + 75 * s[2] ) ],
                       "pv_leaf", sides=7 )
                continue
            big = prop["path"] == OAK_BIG
            trunk, crown, mid, top = ( 22, 290, 430, 700 ) if big else ( 12, 150, 230, 390 )
            lathe( m, ( e, n ), [ ( trunk * s[0], z ), ( trunk * 0.8 * s[0], z + mid * 0.45 * s[2] ) ], "pv_bark", sides=5 )
            lathe( m, ( e, n ), [ ( crown * 0.3 * s[0], z + mid * 0.35 * s[2] ), ( crown * s[0], z + mid * s[2] ),
                                  ( crown * 0.55 * s[0], z + top * 0.92 * s[2] ), ( 0.0, z + top * s[2] ) ], "pv_leaf",
                   sides=8 )
    return m


def _raster():
    import numba

    @numba.njit
    def raster( image, depth, screen, nearness, colours ):
        height, width = depth.shape
        for t in range( screen.shape[0] ):
            ax, ay = screen[t, 0, 0], screen[t, 0, 1]
            bx, by = screen[t, 1, 0], screen[t, 1, 1]
            cx, cy = screen[t, 2, 0], screen[t, 2, 1]
            area = ( bx - ax ) * ( cy - ay ) - ( by - ay ) * ( cx - ax )
            if abs( area ) < 1e-9:
                continue
            x0 = max( int( math.floor( min( ax, bx, cx ) ) ), 0 )
            x1 = min( int( math.ceil( max( ax, bx, cx ) ) ), width - 1 )
            y0 = max( int( math.floor( min( ay, by, cy ) ) ), 0 )
            y1 = min( int( math.ceil( max( ay, by, cy ) ) ), height - 1 )
            za, zb, zc = nearness[t, 0], nearness[t, 1], nearness[t, 2]
            for y in range( y0, y1 + 1 ):
                py = y + 0.5
                for x in range( x0, x1 + 1 ):
                    px = x + 0.5
                    w0 = ( ( bx - px ) * ( cy - py ) - ( by - py ) * ( cx - px ) ) / area
                    w1 = ( ( cx - px ) * ( ay - py ) - ( cy - py ) * ( ax - px ) ) / area
                    w2 = 1.0 - w0 - w1
                    if w0 >= -1e-6 and w1 >= -1e-6 and w2 >= -1e-6:
                        z = w0 * za + w1 * zb + w2 * zc
                        if z > depth[y, x]:
                            depth[y, x] = z
                            image[y, x, 0] = colours[t, 0]
                            image[y, x, 1] = colours[t, 1]
                            image[y, x, 2] = colours[t, 2]
    return raster


def render( P, raster, opaque, glass, sea, eye, target, size=( 960, 540 ), fov=80.0, ss=2 ):
    """ stillhouse_preview.perspective with a compiled rasteriser, supersampled. """
    from PIL import Image
    width, height = size[0] * ss, size[1] * ss
    eye, target = np.asarray( eye, float ), np.asarray( target, float )
    forward = K.normalise( target - eye )
    right = K.normalise( np.cross( forward, ( 0.0, 0.0, 1.0 ) ) )
    up = np.cross( right, forward )
    focal = ( width / 2 ) / math.tan( math.radians( fov ) / 2 )
    xs = ( np.arange( width ) + 0.5 - width / 2 ) / focal
    ys = ( height / 2 - np.arange( height ) - 0.5 ) / focal
    rays = forward + xs[None, :, None] * right + ys[:, None, None] * up
    elevation = rays[..., 2] / np.linalg.norm( rays, axis=2 )
    t = np.clip( elevation * 2.5, 0.0, 1.0 )[..., None]
    image = np.ascontiguousarray( P.SKY[0] * ( 1 - t ) + P.SKY[1] * t )
    depth = np.zeros( ( height, width ) )

    def draw( data, img, dep, both=False ):
        s, z, c = P.project( data, eye, right, up, forward, focal, width, height, both_sides=both )
        raster( img, dep, np.ascontiguousarray( s ), np.ascontiguousarray( z ), np.ascontiguousarray( c ) )

    draw( opaque, image, depth )
    if sea is not None and len( sea[0] ):
        simage, sdepth = np.zeros_like( image ), np.zeros_like( depth )
        draw( sea, simage, sdepth, True )
        over = sdepth > depth
        behind = np.where( over, 1.0 / np.maximum( depth, 1e-9 ) - 1.0 / np.maximum( sdepth, 1e-9 ), 0.0 )
        alpha = np.clip( 0.35 + behind / 400.0, 0.35, 0.85 )[..., None]
        image = np.where( over[..., None], image * ( 1 - alpha ) + simage * alpha, image )
        depth = np.where( over, sdepth, depth )
    gimage, gdepth = np.zeros_like( image ), np.zeros_like( depth )
    draw( glass, gimage, gdepth, True )
    over = gdepth > depth
    image[over] = image[over] * 0.72 + gimage[over] * 0.28
    picture = Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )
    return picture.resize( size, Image.LANCZOS )


def plan( raster, opaque, sea, bounds, scale ):
    """ Straight down, sea tinted over what's under it. """
    from PIL import Image
    e0, e1, n0, n1 = bounds
    width, height = int( ( e1 - e0 ) / scale ), int( ( n1 - n0 ) / scale )
    image = np.tile( np.array( ( 0.12, 0.12, 0.14 ) ), ( height, width, 1 ) )
    depth = np.full( ( height, width ), -1e9 )
    for data, tint in ( ( opaque, None ), ( sea, ( 0.10, 0.22, 0.27 ) ) ):
        tris, normals, colours = data
        if not len( tris ):
            continue
        keep = ( np.abs( normals[:, 2] ) > 0.02 if tint else normals[:, 2] > 0.02 ) \
            & ( tris[:, :, 0].max( axis=1 ) > e0 ) & ( tris[:, :, 0].min( axis=1 ) < e1 ) \
            & ( tris[:, :, 1].max( axis=1 ) > n0 ) & ( tris[:, :, 1].min( axis=1 ) < n1 )
        t = tris[keep]
        cols = colours[keep] if tint is None else np.tile( tint, ( len( t ), 1 ) )
        screen = np.stack( ( ( t[:, :, 0] - e0 ) / scale, ( n1 - t[:, :, 1] ) / scale ), axis=-1 )
        raster( image, depth, np.ascontiguousarray( screen ), np.ascontiguousarray( t[:, :, 2] ), np.ascontiguousarray( cols ) )
    return Image.fromarray( ( np.clip( image, 0, 1 ) * 255 ).astype( np.uint8 ) )


# ( name, eye, target, horizontal field of view ), plan inches. The play area's own views (stillhouse_preview's) first.
VIEWS = [
    ( "brae", ( -2030, -1000, 64 ), ( -2030, 1400, 120 ), 80 ),
    ( "beach", ( -2050, -1600, -90 ), ( 0, -1450, -100 ), 80 ),
    ( "pier", ( 0, -1900, 14 ), ( 0, -1000, 120 ), 80 ),
    ( "road", ( -2030, 1430, 112 ), ( -400, 1650, 110 ), 80 ),
    ( "shore_walk", ( -1880, -1250, 14 ), ( -400, -1240, 30 ), 80 ),
    ( "sea_front", ( 0, -3200, 120 ), ( 0, -900, 160 ), 70 ),
    ( "aerial", ( -3600, -4400, 2600 ), ( 0, -100, 0 ), 70 ),
    ( "aerial_north", ( 2800, 3800, 2200 ), ( 0, -300, 100 ), 70 ),
    ( "brae_east", ( 2030, -1000, 64 ), ( 2030, 1400, 120 ), 80 ),
    ( "brae_east_down", ( 2030, 1500, 112 ), ( 2030, -1400, -20 ), 80 ),
    ( "brae_west_down", ( -2030, 1500, 112 ), ( -2030, -1400, -20 ), 80 ),
    ( "terrace_east", ( 1930, -300, 64 ), ( 2150, 250, 140 ), 80 ),
    ( "terrace_east_low", ( 1950, -1250, 14 ), ( 2150, -700, 110 ), 80 ),
    ( "terrace_west", ( -1930, 250, 64 ), ( -2150, -300, 140 ), 80 ),
    ( "terrace_west_up", ( -1940, 600, 112 ), ( -2150, 1300, 190 ), 80 ),
    ( "beach_east", ( 1500, -1560, -90 ), ( 2600, -1650, -70 ), 80 ),
    ( "beach_west", ( -1500, -1560, -90 ), ( -2600, -1500, -70 ), 80 ),
    ( "north_road", ( 0, 1700, 112 ), ( 400, 6000, 1100 ), 80 ),
    ( "north_road_east", ( 1800, 1750, 112 ), ( 5000, 4500, 500 ), 80 ),
    ( "north_road_west", ( -1800, 1750, 112 ), ( -5000, 4500, 500 ), 80 ),
    ( "pier_head_se", ( 0, -1940, 14 ), ( 4000, -6000, 0 ), 70 ),
    ( "pier_head_sw", ( 0, -1940, 14 ), ( -4000, -6000, 0 ), 70 ),
    ( "loch", ( 0, -1940, 14 ), ( 0, -20000, 300 ), 70 ),
    ( "puffer_east", ( 380, -2050, 40 ), ( 6000, -1200, 200 ), 80 ),
    ( "puffer_west", ( -380, -2050, 40 ), ( -6000, -1200, 200 ), 80 ),
    ( "aerial_east", ( 7000, -6000, 4500 ), ( 2500, 200, 0 ), 60 ),
    ( "aerial_west", ( -7000, -5000, 4000 ), ( -2500, 200, 0 ), 60 ),
    ( "village_wide", ( 0, -9000, 3000 ), ( 0, 3000, 200 ), 70 ),
    ( "hill_wide", ( 0, -3000, 5000 ), ( 0, 12000, 0 ), 70 ),
    # The far model: across the loch from the pier head, the mountains, the lighthouse, the islet, the townships
    ( "far_shore", ( 0, -1940, 14 ), ( 0, -25000, 300 ), 30 ),
    ( "far_tele_w", ( 0, -1940, 14 ), ( -9000, -25000, 200 ), 16 ),
    ( "far_tele_e", ( 0, -1940, 14 ), ( 6000, -25500, 200 ), 16 ),
    ( "mountains", ( 0, -1700, 300 ), ( 20000, -60000, 2500 ), 60 ),
    ( "light_tele", ( -1500, -1900, 14 ), ( -15700, -11750, 200 ), 8 ),
    ( "light_track", ( -14300, -10400, 260 ), ( -15700, -11750, 220 ), 45 ),
    ( "light_sea", ( -13000, -14500, -150 ), ( -15700, -11750, 150 ), 35 ),
    ( "light_air", ( -12500, -9000, 2500 ), ( -15700, -11750, 0 ), 50 ),
    ( "islet_tele", ( 1500, -1900, 14 ), ( 16700, -16700, 150 ), 10 ),
    ( "islet_close", ( 13000, -13500, 250 ), ( 16700, -16700, 150 ), 40 ),
    ( "crofts_close", ( 5600, -22000, 300 ), ( 6000, -25200, 50 ), 40 ),
    ( "far_air", ( 0, -8000, 12000 ), ( 0, -30000, 0 ), 70 ),
    ( "head_west_air", ( -40000, -30000, 20000 ), ( -75000, -6000, 0 ), 60 ),
    ( "head_east_air", ( 40000, -30000, 20000 ), ( 77000, -4000, 0 ), 60 ),
]


def preview( out_dir, names=None ):
    import stillhouse_preview as P
    out = Path( out_dir )
    out.mkdir( parents=True, exist_ok=True )
    started = time.time()
    built = models()
    print( f"built the backdrop in {time.time() - started:.1f} s" )
    west = edge_blocks( -1 )
    report( built, west )
    scene = list( built.values() ) + [ west, greybox(), prop_shapes( list( built.values() ) + [ west ] ) ]
    for paint, colour in ( ( "pv_leaf", ( 0.22, 0.30, 0.14 ) ), ( "pv_bark", ( 0.28, 0.22, 0.16 ) ),
                           ( "pv_ground", ( 0.52, 0.50, 0.46 ) ), ( "pv_walk", ( 0.46, 0.45, 0.43 ) ),
                           ( "pv_block", ( 0.66, 0.64, 0.60 ) ), ( "pv_roof", ( 0.34, 0.35, 0.38 ) ),
                           ( "pv_sand", ( 0.70, 0.64, 0.52 ) ), ( "pv_hull", ( 0.10, 0.20, 0.40 ) ) ):
        P._colours[paint] = np.array( colour )
    unknown = sorted( { p for m in scene for p in m.polygons if np.allclose( P.paint_colour( p ), ( 1, 0, 1 ) ) } )
    for paint in unknown:
        P._colours[paint] = np.array( ( 0.55, 0.55, 0.52 ) )
    if unknown:
        print( f"no preview colour (drawn grey): {unknown}" )
    opaque, glass, sea = P.triangles( scene ), P.triangles( scene, glass=True ), P.triangles( scene, sea=True )
    raster = _raster()
    print( f"{len( opaque[0] )} triangles to draw, {len( sea[0] )} of sea" )
    for name, eye, target, fov in VIEWS:
        if names and name not in names:
            continue
        started = time.time()
        render( P, raster, opaque, glass, sea, eye, target, fov=fov ).save( out / f"{name}.png" )
        print( f"wrote {name}.png ({time.time() - started:.1f} s)" )
    if not names or "top" in names:
        plan( raster, opaque, sea, ( -16000, 16000, -14000, 14000 ), 20 ).save( out / "top_wide.png" )
        plan( raster, opaque, sea, P.TOP_BOUNDS[:2] + ( -2400, 2400 ), 4 ).save( out / "top_close.png" )
        print( "wrote top_wide.png, top_close.png" )


BUDGETS = { "stillhouse_edge_east": 40000, "stillhouse_edge_west": 40000, "stillhouse_land": 250000,
            "stillhouse_seabed": 60000, "stillhouse_sea": 2000, "stillhouse_far": 60000 }


def solids( model ):
    """ The model's collision as ( F, 4 ) facet planes per solid ( inside: a x + b y + c z + d <= 0 ). """
    from scipy.spatial import ConvexHull
    out = []
    for centre, axes, size, _ in model.boxes:
        ax = np.asarray( axes, float ) * ( np.asarray( size, float ) / 2 )[:, None]
        corners = [ np.asarray( centre, float ) + i * ax[0] + j * ax[1] + k * ax[2]
                    for i in ( -1, 1 ) for j in ( -1, 1 ) for k in ( -1, 1 ) ]
        out.append( ConvexHull( np.array( corners ) ).equations )
    for points, _ in model.hulls:
        out.append( ConvexHull( np.array( points, float ) ).equations )
    return out


def line( planes, point, axis=2 ):
    """ The solid intervals along the axis through point (the other two coordinates), merged. """
    spans = []
    others = [ a for a in range( 3 ) if a != axis ]
    for eq in planes:
        val = eq[:, others[0]] * point[others[0]] + eq[:, others[1]] * point[others[1]] + eq[:, 3]
        c = eq[:, axis]
        flat_ = np.abs( c ) < 1e-9
        if ( val[flat_] > 1e-6 ).any():
            continue
        up, down = c > 1e-9, c < -1e-9
        high = ( -val[up] / c[up] ).min() if up.any() else 1e9
        low = ( -val[down] / c[down] ).max() if down.any() else -1e9
        if high > low:
            spans.append( ( low, high ) )
    spans.sort()
    merged = []
    for z0, z1 in spans:
        if merged and z0 <= merged[-1][1] + 0.5:
            merged[-1] = ( merged[-1][0], max( merged[-1][1], z1 ) )
        else:
            merged.append( ( z0, z1 ) )
    return merged


def column( planes, e, n ):
    """ The solid intervals ( z0, z1 ) on the vertical line through ( e, n ), merged. """
    return line( planes, ( e, n, 0.0 ), 2 )


def covered( spans, z0, z1 ):
    return any( a <= z0 + 0.5 and b >= z1 - 0.5 for a, b in spans )


def check_edge( model, side ):
    """ The edge's promises: the terrace's collision is unbroken from the rocks to the byre and stands over the eaves'
    height of the brae; the crag stands 90 over the seawall's parapet; the rocks shut the beach and the shallows off at
    |e| = FRONT, out of a mantle's reach; nothing collides west of the front, and nothing drawn sticks out more than a
    rone's depth below the eaves. Returns a list of problems. """
    s, problems = side, []
    planes = solids( model )
    for n in np.arange( TERRACE_N0 + 2, TERRACE_END - 2, 5.0 ):
        ground = brae_z( n ) if n < TERRACE_N1 else ROAD
        for depth, high in ( ( 2.0, 104.0 ), ( 250.0, 104.0 ), ( 340.0, 30.0 ) ):
            if not covered( column( planes, s * ( FRONT + depth ), n ), ground - 10, ground + high ):
                problems.append( f"terrace open at n {n:.0f}, {depth:.0f} behind the front" )
                break
    for n in np.arange( -1420.0, TERRACE_N0 - 2, 4.0 ):
        for e in ( FRONT + 40, FRONT + 80, FRONT + 120 ):
            spans = column( planes, s * e, n )
            if not spans or max( b for a, b in spans ) < 90:
                problems.append( f"crag under 90 at e {s * e:.0f}, n {n:.0f}" )
    worst = 1e9
    for n in np.arange( PLAY_N0 - 70, TERRACE_N0 - 2, 5.0 ):
        floor = seabed_floor( n )
        high = ( PARAPET if n > -1430 else floor ) + 97
        for z in np.arange( floor + 2, high, 6.0 ):
            spans = [ ( min( s * a, s * b ), max( s * a, s * b ) ) for a, b in line( planes, ( 0.0, n, z ), 0 ) ]
            if not any( a <= FRONT + 80 and b >= FRONT + 90 for a, b in spans ):
                problems.append( f"rocks open at n {n:.0f}, z {z:.0f} (floor {floor:.0f})" )
                break
        spans = column( planes, s * ( FRONT + 60 ), n )
        if spans:
            worst = min( worst, max( b for a, b in spans ) - floor )
    from scipy.spatial import ConvexHull
    for points, _ in model.hulls:
        pts = np.array( points, float )
        if ( s * pts[:, 0] ).min() > FRONT + 150 or pts[:, 1].min() > TERRACE_N0:
            continue
        hull = ConvexHull( pts )
        for simplex, eq in zip( hull.simplices, hull.equations ):
            if eq[2] < 0.7:
                continue
            for v in pts[simplex]:
                reach = ( PARAPET if v[1] > -1395 else max( seabed_floor( q ) for q in ( v[1] - 30, v[1] + 30 ) ) ) + 95
                if s * v[0] < FRONT + 120 and v[2] < reach and v[1] < TERRACE_N0:
                    problems.append( f"a ledge in reach at e {v[0]:.0f}, n {v[1]:.0f}, z {v[2]:.0f}" )
                    break
    for centre, axes, size, _ in model.boxes:
        ax = np.asarray( axes, float ) * ( np.asarray( size, float ) / 2 )[:, None]
        reach = s * centre[0] - np.abs( ax[:, 0] ).sum()
        if reach < FRONT - 0.01:
            problems.append( f"box reaches e {s * reach:.1f}" )
    for points, _ in model.hulls:
        for p in points:
            if s * p[0] < FRONT - 0.01 and ( p[1] >= TERRACE_N0 or p[2] > seabed_floor( p[1] ) + 1 ):
                problems.append( f"hull reaches e {p[0]:.1f} at n {p[1]:.0f}, z {p[2]:.0f}" )
                break
    out = 0.0
    for paint, items in model.polygons.items():
        for points, _ in items:
            for p in points:
                if p[1] > TERRACE_N0 and s * p[0] < FRONT - 12.5 and p[2] < ROAD + 104:
                    out = max( out, FRONT - s * p[0] )
                    if len( problems ) < 40:
                        problems.append( f"{paint} sticks out to e {p[0]:.1f} at n {p[1]:.0f}, z {p[2]:.0f}" )
    return problems, worst


def report( built, west=None ):
    print( f"{'model':26} {'triangles':>10} {'budget':>8} {'boxes':>6} {'hulls':>6} {'props':>6}  extents" )
    every = dict( built )
    if west is not None:
        every["stillhouse_edge_west"] = west
    for name, model in every.items():
        lo, hi = model.bounds() if model.polygons else ( ( 0, 0, 0 ), ( 0, 0, 0 ) )
        tris = model.triangle_count()
        flag = "  OVER" if tris > BUDGETS.get( name, 1e12 ) else ""
        print( f"{name:26} {tris:>10} {BUDGETS.get( name, 0 ):>8} {len( model.boxes ):>6} {len( model.hulls ):>6} "
               f"{len( model.props ):>6}  e {lo[0]:.0f}..{hi[0]:.0f}  n {lo[1]:.0f}..{hi[1]:.0f}  "
               f"z {lo[2]:.0f}..{hi[2]:.0f}{flag}" )
    for side, name in ( ( 1, "stillhouse_edge_east" ), ( -1, "stillhouse_edge_west" ) ):
        if name not in every:
            continue
        problems, worst = check_edge( every[name], side )
        print( f"{name}: {len( problems )} problems; the rocks stand at least {worst:.0f} over the floor 60 behind the front" )
        for problem in problems[:20]:
            print( "   ", problem )


def models():
    """ Every backdrop model by name. The west edge is edge_blocks( -1 ), built by the map script itself. """
    return { "stillhouse_edge_east": edge_blocks( 1 ), "stillhouse_land": land(), "stillhouse_seabed": seabed(),
             "stillhouse_sea": sea(), "stillhouse_far": far() }


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--preview" and len( args ) >= 2:
        preview( args[1], args[2:] or None )
    else:
        started = time.time()
        built = models()
        print( f"built in {time.time() - started:.1f} s" )
        report( built, edge_blocks( -1 ) )
