""" The buildings and trees on the land round Belltower: a hill town on the west ridge's summit (the one West Street
looks at through the west gate), a villa with its cypress avenue on the east ridge, a village on the south-west hill,
farms in the fields, chapels on knolls, and cypresses, round all of them, in rows and alone. Drawn only (no collision,
no shadows), as one model, `belltower_vista_props`, which Tools/belltower_map.py writes with the land.

Everything stands on the land as Tools/belltower_vista.py draws it (the mesh's own triangles, `Ground`, so nothing
floats over a hollow or sinks into a bump), at its real size over the forced perspective's scale where it stands
(belltower_vista.scale). A settlement is one rigid thing at its middle's scale, so its streets keep their shape.

Far off, a window is under a pixel, so the buildings are faces of flat colour from one atlas (vista_props: lime renders,
stone, brick, terracotta, ...) with each cell's weathering drawn in: rising damp, the shadow under the eaves, render
fallen off, the roofs' courses of coppi and their lichen. Where a window comes to WINDOW_PX pixels or more, seen from
the town at 1080p, the building gets its windows, shutters and door as faces just proud of its walls. Cypresses and
umbrella pines are smooth-shaded spindles and domes in a tiling foliage texture.

The painter (Tools/belltower_vista_paint.py) paints what they do to the ground (`World.paint_data`): the shadows of
every building and tree, the ground they stand on (yards: a town's paving and kitchen gardens, a farm's beaten earth, a
garden's lawn, a cemetery's gravel), and the white roads, out of the hill town's gate and down the villa's avenue, which
wind down the hills as a road builder lays them. It keeps its own painted trees off all of it.

    python Tools/belltower_vista_props.py [--textures-only]

writes the textures, the materials and the model. `python Tools/belltower_vista_paint.py --preview <dir>` renders
them over the painted land.
"""

import argparse
import io
import math
import time
from collections import defaultdict

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

import map_kit as K
import belltower_vista as V

M = 39.37                   # units a metre
NAME = "belltower_vista_props"
ATLAS, CYPRESS, PINE = "vista_props", "vista_cypress", "vista_pine"
ATLAS_SIZE, CELL, PAD = 512, 64, 6
INNER = CELL - 2 * PAD
PER_ROW = ATLAS_SIZE // CELL
FOLIAGE_SIZE = 512
FOLIAGE_TILE = 2.5          # metres of foliage one tile of its texture covers
PITCH = math.tan( math.radians( 22.0 ) )     # coppi roofs: a 40% slope
EAVE = 0.45                 # the roofs' overhang (m)
FLOOR = 3.3                 # a storey (m)
SINK = 0.6                  # walls and trunks go on this far (m) under the lowest ground beneath them
FOCAL = 960.0 / math.tan( math.radians( 40.0 ) )     # pixels for a unit seen a unit away: 1080p, an 80-degree view
WINDOW_PX = 1.5             # a window this many pixels wide, seen from the town, is drawn

# The atlas: name, what's drawn in the cell, and its colour (sRGB).
CELLS = (
    ( "render_ochre", "wall", ( 212, 170, 112 ) ),
    ( "render_yellow", "wall", ( 220, 192, 134 ) ),
    ( "render_cream", "wall", ( 224, 210, 180 ) ),
    ( "render_pink", "wall", ( 210, 160, 134 ) ),
    ( "render_rose", "wall", ( 194, 134, 110 ) ),
    ( "render_terra", "wall", ( 182, 112, 78 ) ),
    ( "render_umber", "wall", ( 162, 120, 84 ) ),
    ( "render_grey", "wall", ( 194, 186, 168 ) ),
    ( "stone_warm", "stone", ( 166, 146, 114 ) ),
    ( "stone_grey", "stone", ( 148, 142, 128 ) ),
    ( "stone_pale", "stone", ( 184, 172, 146 ) ),
    ( "white_stone", "ashlar", ( 216, 208, 190 ) ),
    ( "brick", "brick", ( 158, 92, 64 ) ),
    ( "roof_new", "roof", ( 174, 96, 64 ) ),
    ( "roof_old", "roof", ( 150, 92, 66 ) ),
    ( "roof_dark", "roof", ( 126, 84, 64 ) ),
    ( "roof_pale", "roof", ( 168, 114, 84 ) ),
    ( "roof_lichen", "roof", ( 138, 108, 80 ) ),
    ( "eave", "flat", ( 64, 52, 44 ) ),
    ( "window", "window", ( 36, 33, 31 ) ),
    ( "door", "door", ( 72, 54, 40 ) ),
    ( "shutter_green", "shutter", ( 72, 94, 64 ) ),
    ( "shutter_brown", "shutter", ( 102, 76, 52 ) ),
    ( "shutter_grey", "shutter", ( 126, 130, 114 ) ),
    ( "opening", "flat", ( 26, 24, 22 ) ),
    ( "wall_top", "flat", ( 172, 164, 146 ) ),
    ( "bark", "bark", ( 72, 60, 50 ) ),
)
CYPRESS_COLOUR = ( 44, 60, 36 )
PINE_COLOUR = ( 70, 88, 48 )

# The houses' colours and roofs, and how often each is picked.
RENDERS = ( ( "render_cream", 15 ), ( "render_ochre", 18 ), ( "render_yellow", 10 ), ( "render_pink", 12 ),
            ( "render_rose", 6 ), ( "render_terra", 6 ), ( "render_umber", 5 ), ( "render_grey", 8 ),
            ( "stone_warm", 12 ), ( "stone_grey", 5 ), ( "stone_pale", 3 ) )
ROOFS = ( ( "roof_new", 15 ), ( "roof_old", 35 ), ( "roof_dark", 15 ), ( "roof_pale", 15 ), ( "roof_lichen", 20 ) )
SHUTTERS = ( ( "shutter_green", 55 ), ( "shutter_brown", 30 ), ( "shutter_grey", 15 ) )

# Cypress (Cupressus sempervirens 'Stricta'): its outline up its height, as a share of its widest radius.
CYPRESS_PROFILE = np.array( [ ( 0.0, 0.32 ), ( 0.05, 0.62 ), ( 0.14, 0.86 ), ( 0.27, 1.0 ), ( 0.44, 0.93 ),
                              ( 0.62, 0.74 ), ( 0.78, 0.48 ), ( 0.9, 0.24 ), ( 1.0, 0.0 ) ] )
# Umbrella pine (Pinus pinea): its crown's top and underside, ( share of the radius, share of the crown's depth ).
PINE_TOP = np.array( [ ( 1.0, 0.0 ), ( 0.96, 0.3 ), ( 0.78, 0.66 ), ( 0.45, 0.9 ), ( 0.0, 1.0 ) ] )
PINE_UNDER = np.array( [ ( 0.0, -0.12 ), ( 0.55, -0.1 ), ( 1.0, 0.0 ) ] )

# The painter's tree kinds and their crowns' colours (belltower_vista_paint's TREES and TREE_COLOURS).
TREE_CYPRESS, TREE_PINE = 3, 6
# The ground the painter gives a yard (belltower_vista_paint.YARD_COLOURS): a town's paving and kitchen gardens, a
# farm's beaten earth, a garden's lawn, gravel.
YARD_TOWN, YARD_FARM, YARD_GARDEN, YARD_GRAVEL = range( 4 )
ROAD_HALF = 2.0             # the white roads' half-width (m)
TAKE_CELL = 400.0           # the cells World.free looks things up in (units)


def linear( srgb ):
    return ( np.asarray( srgb, float ) / 255.0 ) ** 2.2


def smoothstep( a, b, x ):
    t = np.clip( ( np.asarray( x, float ) - a ) / ( b - a ), 0.0, 1.0 )
    return t * t * ( 3.0 - 2.0 * t )


def pick( rng, table ):
    names = [ name for name, _ in table ]
    weights = np.array( [ w for _, w in table ], float )
    return names[rng.choice( len( names ), p=weights / weights.sum() )]


# ---------------------------------------------------------------------------------------------------------------------
# Textures

def tiling_noise( size, lo, hi, rng, beta=1.0 ):
    """ Noise that tiles, its energy between lo and hi cycles across, mostly within -1..1. """
    f = np.fft.fftfreq( size ) * size
    k = np.hypot( *np.meshgrid( f, f ) )
    amp = np.where( ( k >= lo ) & ( k <= hi ), 1.0 / np.maximum( k, 1.0 ) ** beta, 0.0 )
    phase = rng.standard_normal( ( size, size ) ) + 1j * rng.standard_normal( ( size, size ) )
    out = np.real( np.fft.ifft2( amp * phase ) )
    return out / max( 3.0 * out.std(), 1e-9 )


def draw_cell( kind, colour, rng ):
    """ One cell's picture, INNER square: colour (linear), height and roughness. Its top row is the top of the face
    it's drawn across (the eaves, the ridge). """
    n = INNER
    y, x = ( np.mgrid[0:n, 0:n] + 0.5 ) / n
    low, mid, fine = ( tiling_noise( n, lo, hi, rng ) for lo, hi in ( ( 1, 4 ), ( 4, 12 ), ( 12, 30 ) ) )
    base = linear( colour )
    shade = 1.0 + 0.06 * low + 0.04 * mid + 0.03 * fine
    height = 0.5 * mid + 0.3 * fine
    rough = np.full( ( n, n ), 0.9 )
    if kind == "wall":
        # Lime render: blotchy, fallen off here and there to the stone under it, shaded under the eaves and damp at
        # the foot.
        loss = smoothstep( 0.35, 0.6, tiling_noise( n, 2, 8, rng ) ) * 0.5
        col = base * shade[..., None] * ( 1 - loss[..., None] ) + linear( ( 150, 134, 108 ) ) * ( shade * loss )[..., None]
        col *= ( ( 0.5 + 0.5 * smoothstep( 0.0, 0.1, y ) ) * ( 0.78 + 0.22 * smoothstep( 0.0, 0.18, 1.0 - y + 0.03 * mid ) ) )[..., None]
        height -= loss
    elif kind == "roof":
        # Coppi: courses from the ridge (top) to the eaves, each lapping the one below, the rounded tiles catching the
        # light along their crowns, a few odd ones, and lichen.
        courses, tiles = 9, 11
        cy = y * courses
        row = np.floor( cy )
        ph = cy - row
        cx = x * tiles + 0.5 * ( row % 2 )
        px = cx - np.floor( cx )
        table = 1.0 + 0.09 * rng.standard_normal( ( courses + 1, tiles + 2 ) )
        odd = table[row.astype( int ), np.floor( cx ).astype( int ) % ( tiles + 2 )]
        crown = 0.86 + 0.18 * np.sin( np.pi * px )
        lap = 0.7 + 0.3 * smoothstep( 0.0, 0.3, ph )
        gutter = 0.75 + 0.25 * smoothstep( 0.0, 0.05, 1.0 - y )
        lichen = smoothstep( 0.3, 0.75, tiling_noise( n, 3, 10, rng ) ) * 0.4
        lit = shade * crown * lap
        col = base * ( lit * odd * gutter )[..., None] * ( 1 - lichen[..., None] ) + linear( ( 156, 148, 118 ) ) * ( lit * lichen )[..., None]
        height = 0.6 * np.sin( np.pi * px ) + 0.4 * ph
        rough[:] = 0.8
    elif kind in ( "stone", "ashlar", "brick" ):
        rows, width = { "stone": ( 8, 0.18 ), "ashlar": ( 6, 0.28 ), "brick": ( 16, 0.2 ) }[kind]
        cy = y * rows
        row = np.floor( cy ).astype( int )
        ph = cy - row
        stagger = rng.random( rows + 1 ) if kind == "stone" else 0.5 * ( np.arange( rows + 1 ) % 2 )
        cx = x / width + stagger[row]
        block = np.floor( cx ).astype( int )
        px = cx - block
        table = 1.0 + ( 0.05 if kind == "ashlar" else 0.12 ) * rng.standard_normal( ( rows + 1, int( 1 / width ) + 3 ) )
        tint = table[row, block % table.shape[1]]
        joint_w = 0.1 if kind == "brick" else 0.07
        joint = np.minimum( smoothstep( 0.0, joint_w, ph ) * smoothstep( 0.0, joint_w, 1 - ph ),
                            smoothstep( 0.0, joint_w * 0.5, px ) * smoothstep( 0.0, joint_w * 0.5, 1 - px ) )
        mortar = linear( ( 178, 166, 142 ) ) if kind == "brick" else base * 0.6
        col = base * ( shade * tint )[..., None] * joint[..., None] + mortar * ( shade * ( 1 - joint ) )[..., None]
        col *= ( 0.8 + 0.2 * smoothstep( 0.0, 0.15, 1.0 - y ) )[..., None]
        height = joint + 0.2 * fine
    elif kind == "window":
        # Dark glass in a painted frame, the upper panes catching a little of the sky.
        frame = ( x < 0.12 ) | ( x > 0.88 ) | ( y < 0.08 ) | ( y > 0.92 ) | ( np.abs( x - 0.5 ) < 0.04 ) | ( np.abs( y - 0.42 ) < 0.035 )
        col = base * ( shade * ( 1.0 + 0.8 * ( 1.0 - y ) ) )[..., None]
        col[frame] = linear( ( 190, 182, 162 ) ) * shade[frame][:, None]
        height = frame.astype( float )
        rough = np.where( frame, 0.8, 0.25 )
    elif kind == "door":
        col = base * ( shade * ( 0.82 + 0.18 * np.abs( np.sin( np.pi * x * 5 ) ) ) )[..., None]
        height = np.abs( np.sin( np.pi * x * 5 ) )
        rough[:] = 0.7
    elif kind == "shutter":
        # Louvred shutters: slats lit along their tops, in a frame.
        ph = ( y * 12 ) % 1.0
        slat = np.where( ph < 0.3, 1.1, np.where( ph > 0.8, 0.68, 0.95 ) )
        frame = ( x < 0.07 ) | ( x > 0.93 ) | ( y < 0.05 ) | ( y > 0.95 )
        col = base * ( shade * np.where( frame, 0.85, slat ) )[..., None]
        height = np.where( frame, 1.0, 1.0 - ph )
        rough[:] = 0.6
    elif kind == "bark":
        streak = tiling_noise( n, 3, 16, rng )[0][None, :] * 0.7 + 0.3 * fine
        col = base * ( shade * ( 0.8 + 0.35 * np.abs( streak ) ) )[..., None]
        height = np.abs( streak )
    else:
        col = base * shade[..., None]
    return np.clip( col, 0.0, 1.0 ), height, rough


def normal_map( height, strength ):
    """ OpenGL normals (green up the picture) of a height map, in pixels. """
    dy, dx = np.gradient( height )
    nrm = np.stack( ( -dx * strength, dy * strength, np.ones_like( height ) ), -1 )
    return nrm / np.linalg.norm( nrm, axis=-1, keepdims=True )


def encode( a ):
    return np.clip( np.rint( a * 255.0 ), 0, 255 ).astype( np.uint8 )


def srgb8( lin ):
    return encode( np.clip( lin, 0.0, 1.0 ) ** ( 1 / 2.2 ) )


class Atlas:
    """ The cells' places in the atlas and their mean colours, and the atlas's pictures. """

    def __init__( self ):
        self.index = { name: k for k, ( name, _, _ ) in enumerate( CELLS ) }
        rng = np.random.default_rng( 5 )
        self.colour = np.full( ( ATLAS_SIZE, ATLAS_SIZE, 3 ), 0.2 )
        self.normal = np.zeros( ( ATLAS_SIZE, ATLAS_SIZE, 3 ) )
        self.normal[..., 2] = 1.0
        self.rough = np.full( ( ATLAS_SIZE, ATLAS_SIZE ), 0.9 )
        self.mean = {}
        strengths = { "roof": 1.6, "stone": 1.2, "ashlar": 0.8, "brick": 1.0, "shutter": 1.0, "door": 0.8 }
        for k, ( name, kind, colour ) in enumerate( CELLS ):
            col, height, rough = draw_cell( kind, colour, rng )
            self.mean[name] = col.reshape( -1, 3 ).mean( axis=0 )
            r, c = divmod( k, PER_ROW )
            cells = np.s_[r * CELL:( r + 1 ) * CELL, c * CELL:( c + 1 ) * CELL]
            self.colour[cells] = np.pad( col, ( ( PAD, PAD ), ( PAD, PAD ), ( 0, 0 ) ), mode="edge" )
            self.normal[cells] = normal_map( np.pad( height, PAD, mode="edge" ), strengths.get( kind, 0.5 ) )
            self.rough[cells] = np.pad( rough, PAD, mode="edge" )

    def rect( self, name ):
        """ The cell's inner UVs ( u0, v0, u1, v1 ): v0 its bottom, v1 its top (OBJ's v runs up the picture). """
        r, c = divmod( self.index[name], PER_ROW )
        return ( ( c * CELL + PAD ) / ATLAS_SIZE, 1.0 - ( ( r + 1 ) * CELL - PAD ) / ATLAS_SIZE,
                 ( ( c + 1 ) * CELL - PAD ) / ATLAS_SIZE, 1.0 - ( r * CELL + PAD ) / ATLAS_SIZE )


def draw_foliage():
    """ The tiling foliage: sprays of scale leaves round dark gaps. ( height, light, dead ). """
    rng = np.random.default_rng( 9 )
    n = FOLIAGE_SIZE
    height = ( 0.55 * tiling_noise( n, 4, 12, rng ) + 0.35 * tiling_noise( n, 12, 40, rng )
               + 0.2 * tiling_noise( n, 40, 120, rng ) )
    light = 0.28 + 0.9 * smoothstep( -0.45, 0.35, height )
    dead = smoothstep( 0.55, 0.9, tiling_noise( n, 6, 20, rng ) ) * 0.25
    return height, light, dead


def foliage_colour( colour, light, dead ):
    lit = light[..., None]
    return np.clip( linear( colour ) * lit * ( 1 - dead[..., None] ) + linear( ( 96, 84, 56 ) ) * lit * dead[..., None], 0, 1 )


def save_png( path, array, mode ):
    """ Writes a PNG unless the file already holds the same picture (the editor recompiles what's rewritten). """
    buffer = io.BytesIO()
    Image.fromarray( array, mode ).save( buffer, "PNG", optimize=True )
    data = buffer.getvalue()
    if path.exists() and path.read_bytes() == data:
        return
    path.write_bytes( data )


def vmat_text( name, normal, rough ):
    return ( "// Tools/belltower_vista_props.py\n"
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/complex.shader"\n'
             '    F_SPECULAR "1"\n'
             '    g_flRoughnessScaleFactor "1"\n'
             '    g_flMetalness "0.00"\n'
             f'    TextureColor "{V.TEXTURE_RESOURCE}/{name}_color.png"\n'
             f'    TextureNormal "{V.TEXTURE_RESOURCE}/{normal}_normal.png"\n'
             f'    TextureRoughness "{V.TEXTURE_RESOURCE}/{rough}_rough.png"\n'
             '    g_vColorTint "[1.0 1.0 1.0 1.0]"\n'
             '    g_flModelTintAmount "1.0"\n'
             "}\n" )


def write_textures( atlas, out_dir=V.TEXTURE_DIR ):
    out_dir.mkdir( parents=True, exist_ok=True )
    save_png( out_dir / f"{ATLAS}_color.png", srgb8( atlas.colour ), "RGB" )
    save_png( out_dir / f"{ATLAS}_normal.png", encode( atlas.normal * 0.5 + 0.5 ), "RGB" )
    save_png( out_dir / f"{ATLAS}_rough.png", encode( atlas.rough ), "L" )
    height, light, dead = draw_foliage()
    save_png( out_dir / f"{CYPRESS}_color.png", srgb8( foliage_colour( CYPRESS_COLOUR, light, dead ) ), "RGB" )
    save_png( out_dir / f"{PINE}_color.png", srgb8( foliage_colour( PINE_COLOUR, light, dead ) ), "RGB" )
    save_png( out_dir / "vista_foliage_normal.png", encode( normal_map( height * 3.0, 6.0 ) * 0.5 + 0.5 ), "RGB" )
    save_png( out_dir / "vista_foliage_rough.png", encode( 0.82 + 0.1 * ( 1 - light / light.max() ) ), "L" )
    K.write_text( out_dir / f"{ATLAS}.vmat", vmat_text( ATLAS, ATLAS, ATLAS ) )
    K.write_text( out_dir / f"{CYPRESS}.vmat", vmat_text( CYPRESS, "vista_foliage", "vista_foliage" ) )
    K.write_text( out_dir / f"{PINE}.vmat", vmat_text( PINE, "vista_foliage", "vista_foliage" ) )


def foliage_mean( colour ):
    _, light, dead = draw_foliage()
    return foliage_colour( colour, light, dead ).reshape( -1, 3 ).mean( axis=0 )


# ---------------------------------------------------------------------------------------------------------------------
# The ground and the mesh

class Ground:
    """ The land's height as its model draws it: on the mesh's own triangles. """

    def __init__( self ):
        verts, _, tris, _ = V.land_mesh()
        self.verts, self.tris = verts, tris
        self.tree = cKDTree( verts[tris].mean( axis=1 )[:, :2] )

    def __call__( self, e, n ):
        e, n = np.broadcast_arrays( np.asarray( e, float ), np.asarray( n, float ) )
        q = np.column_stack( ( e.ravel(), n.ravel() ) )
        z = np.full( len( q ), np.nan )
        _, near = self.tree.query( q, k=12 )
        for k in range( near.shape[1] ):
            todo = np.nonzero( np.isnan( z ) )[0]
            if not len( todo ):
                break
            t = self.verts[self.tris[near[todo, k]]]
            a, b, c = t[:, 0], t[:, 1], t[:, 2]
            v0, v1, v2 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2], q[todo] - a[:, :2]
            den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
            wb = ( v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1] ) / den
            wc = ( v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1] ) / den
            wa = 1.0 - wb - wc
            inside = ( wa >= -1e-6 ) & ( wb >= -1e-6 ) & ( wc >= -1e-6 )
            z[todo[inside]] = ( wa * a[:, 2] + wb * b[:, 2] + wc * c[:, 2] )[inside]
        missed = np.isnan( z )
        if missed.any():
            z[missed] = V.land_height( q[missed, 0], q[missed, 1] )
        return z.reshape( e.shape )


class Mesh:
    """ Triangles by material, each corner with its own normal, UV and (for the previews) colour, in plan. """

    def __init__( self ):
        self.parts = defaultdict( lambda: ( [], [], [], [], [] ) )
        self.sizes = defaultdict( int )

    def add( self, material, points, normals, uvs, colours, triangles ):
        P, N, U, C, T = self.parts[material]
        points = np.asarray( points, float ).reshape( -1, 3 )
        P.append( points )
        N.append( np.asarray( normals, float ).reshape( -1, 3 ) )
        U.append( np.asarray( uvs, float ).reshape( -1, 2 ) )
        C.append( np.broadcast_to( np.asarray( colours, float ), ( len( points ), 3 ) ) )
        T.append( np.asarray( triangles, np.int64 ).reshape( -1, 3 ) + self.sizes[material] )
        self.sizes[material] += len( points )

    def face( self, material, points, uvs, colour, outward ):
        """ A flat convex polygon facing outward: its winding is put right if it's given the other way. """
        points, uvs = np.asarray( points, float ), np.asarray( uvs, float )
        normal = np.zeros( 3 )
        for k in range( 1, len( points ) - 1 ):
            normal += np.cross( points[k] - points[0], points[k + 1] - points[0] )
        size = np.linalg.norm( normal )
        if size < 1e-9:
            return
        normal /= size
        if np.dot( normal, outward ) < 0:
            points, uvs, normal = points[::-1], uvs[::-1], -normal
        self.add( material, points, np.repeat( normal[None], len( points ), 0 ), uvs, colour,
                  [ ( 0, k, k + 1 ) for k in range( 1, len( points ) - 1 ) ] )

    def grid( self, material, points, normals, uvs, colour ):
        """ Quads between a grid's neighbouring rows and columns, facing along its normals. Triangles with no area
        (where a row closes to a point) are left out. """
        rows, cols = points.shape[:2]
        idx = np.arange( rows * cols ).reshape( rows, cols )
        a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
        tris = np.concatenate( ( np.stack( ( a, b, c ), 1 ), np.stack( ( a, c, d ), 1 ) ) )
        P, N = points.reshape( -1, 3 ), normals.reshape( -1, 3 )
        cross = np.cross( P[tris[:, 1]] - P[tris[:, 0]], P[tris[:, 2]] - P[tris[:, 0]] )
        keep = np.linalg.norm( cross, axis=1 ) > 1e-6
        tris, cross = tris[keep], cross[keep]
        flip = ( cross * N[tris].mean( axis=1 ) ).sum( axis=1 ) < 0
        tris[flip] = tris[flip][:, ::-1]
        self.add( material, P, N, uvs.reshape( -1, 2 ), colour, tris )

    def arrays( self, material ):
        P, N, U, C, T = self.parts[material]
        return ( np.concatenate( P ), np.concatenate( N ), np.concatenate( U ), np.concatenate( C ),
                 np.concatenate( T ) )

    def triangles( self ):
        """ Every triangle's corners ( T, 3, 3 ), their normals and colours (the materials' means). """
        out = [ [], [], [] ]
        for material in sorted( self.parts ):
            P, N, _, C, T = self.arrays( material )
            for store, data in zip( out, ( P, N, C ) ):
                store.append( data[T] )
        return tuple( np.concatenate( x ) for x in out )

    def preview_triangles( self ):
        """ For the previews: every triangle's corners ( T, 3, 3 ), their normals, and ( u, v, the material's place in
        sorted order ) at each. """
        out = [ [], [], [] ]
        for m, material in enumerate( sorted( self.parts ) ):
            P, N, U, _, T = self.arrays( material )
            out[0].append( P[T] )
            out[1].append( N[T] )
            out[2].append( np.concatenate( ( U[T], np.full( ( len( T ), 3, 1 ), float( m ) ) ), axis=2 ) )
        return tuple( np.concatenate( x ) for x in out )

    def count( self ):
        return sum( len( self.arrays( m )[4] ) for m in self.parts )

    def write( self, out_dir, resource_dir, name ):
        """ <name>.obj/.mtl and .vmdl, drawn with the materials in materials/belltower/vista. Plan ( e, n, z ) is
        world ( n, -e, z ), and the OBJ is world ( y, z, x ): both keep the winding. """
        lines = [ "# Tools/belltower_vista_props.py", f"mtllib {name}.mtl", f"o {name}" ]
        verts, uvs, normals, faces = [], [], [], []
        base = 1
        for material in sorted( self.parts ):
            P, N, U, _, T = self.arrays( material )
            verts += [ f"v {-e:.2f} {z:.2f} {n:.2f}" for e, n, z in P ]
            uvs += [ f"vt {u:.5f} {v:.5f}" for u, v in U ]
            normals += [ f"vn {-a:.4f} {c:.4f} {b:.4f}" for a, b, c in N ]
            faces.append( f"usemtl {material}" )
            faces += [ f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}" for a, b, c in T + base ]
            base += len( P )
        out_dir.mkdir( parents=True, exist_ok=True )
        K.write_text( out_dir / f"{name}.obj", "\n".join( lines + verts + uvs + normals + faces ) + "\n" )
        K.write_text( out_dir / f"{name}.mtl", "".join( f"newmtl {m}\nKd 1 1 1\nd 1\n" for m in sorted( self.parts ) ) )
        holder = K.Model()
        for material in sorted( self.parts ):
            holder.polygons[material] = []
            holder.material_overrides[material] = f"{V.TEXTURE_RESOURCE}/{material}.vmat"
        K.write_vmdl( out_dir / f"{name}.vmdl", resource_dir, name, holder )


# ---------------------------------------------------------------------------------------------------------------------
# Building

def rect_corners( centre, yaw, length, width ):
    """ A length x width rectangle's corners, turned by yaw: anticlockwise seen from above, the first edge along its
    length on the -width side (its outward side faces yaw - 90 degrees). """
    c, s = math.cos( yaw ), math.sin( yaw )
    ax, ay = np.array( ( c, s ) ), np.array( ( -s, c ) )
    hl, hw = length / 2, width / 2
    centre = np.asarray( centre, float )
    return np.array( [ centre - ax * hl - ay * hw, centre + ax * hl - ay * hw, centre + ax * hl + ay * hw,
                       centre - ax * hl + ay * hw ] )


def facing( direction ):
    """ The yaw that turns a rectangle's first edge to face direction (radians, from east anticlockwise). """
    return direction + math.pi / 2


def outward( a, b ):
    """ The outward normal of edge a -> b of an anticlockwise outline: to its right. """
    d = np.asarray( b, float ) - np.asarray( a, float )
    return np.array( ( d[1], -d[0], 0.0 ) ) / max( math.hypot( d[0], d[1] ), 1e-9 )


class World:
    """ The props as they're built: the mesh, and for the painter the buildings' footprints and the trees' crowns,
    and where things stand, so nothing else is put there. """

    def __init__( self, ground ):
        self.ground = ground
        self.atlas = Atlas()
        self.mesh = Mesh()
        self.buildings = []         # ( corners ( 4, 2 ), base z, eave z, ridge z )
        self.trees = []             # ( e, n, ground z, crown radius, crown middle over the ground, half-height, kind )
        self.taken = defaultdict( list )    # cell -> ( e, n, radius ) of what stands in it
        self.yards = []             # ( kind, plan outline ( P, 2 ) ): the ground a settlement, yard or garden covers
        self.roads = []             # ( half-width (units), plan line ( P, 2 ) )
        self.cypress_colour = foliage_mean( CYPRESS_COLOUR )
        self.pine_colour = foliage_mean( PINE_COLOUR )

    # Where things stand ----------------------------------------------------------------------------------------

    @staticmethod
    def _cells( e, n, radius ):
        for i in range( int( ( e - radius ) // TAKE_CELL ), int( ( e + radius ) // TAKE_CELL ) + 1 ):
            for j in range( int( ( n - radius ) // TAKE_CELL ), int( ( n + radius ) // TAKE_CELL ) + 1 ):
                yield i, j

    def free( self, e, n, radius ):
        for cell in self._cells( e, n, radius ):
            for te, tn, tr in self.taken.get( cell, () ):
                if math.hypot( e - te, n - tn ) < radius + tr:
                    return False
        return True

    def take( self, e, n, radius ):
        entry = ( float( e ), float( n ), float( radius ) )
        for cell in self._cells( e, n, radius ):
            self.taken[cell].append( entry )

    def yard( self, kind, outline ):
        """ The ground of a yard's kind, inside a plan outline. """
        self.yards.append( ( kind, np.asarray( outline, float ) ) )

    def round_yard( self, kind, e, n, radius, sides=24 ):
        t = np.linspace( 0.0, 2 * math.pi, sides, endpoint=False )
        self.yard( kind, np.column_stack( ( e + np.cos( t ) * radius, n + np.sin( t ) * radius ) ) )

    def road( self, line, k, half=ROAD_HALF ):
        """ A white road along plan points, half metres either side of them, which nothing else is put on. """
        line = np.asarray( line, float )
        self.roads.append( ( half * k, line ) )
        for a, b in zip( line[:-1], line[1:] ):
            for t in np.linspace( 0.0, 1.0, max( 2, int( np.linalg.norm( b - a ) / ( 3.0 * k ) ) + 1 ) ):
                p = a + ( b - a ) * t
                self.take( p[0], p[1], ( half + 0.8 ) * k )

    @staticmethod
    def k_at( e, n ):
        """ Units a metre is drawn at, at plan point ( e, n ). """
        return M / float( V.scale( V.town_distance( e, n ) ) )

    @staticmethod
    def pixels( e, n, size ):
        """ How many pixels across size (units) at ( e, n ) is from the town's middle. """
        return size / max( math.hypot( e - V.CENTRE[0], n - V.CENTRE[1] ), 1.0 ) * FOCAL

    # Faces ------------------------------------------------------------------------------------------------------

    def quad( self, cell, a, b, c, d, out ):
        """ a, b along the bottom, c, d along the top (c above b): the cell's picture fills it. """
        u0, v0, u1, v1 = self.atlas.rect( cell )
        self.mesh.face( ATLAS, ( a, b, c, d ), ( ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ),
                        self.atlas.mean[cell], out )

    def walls( self, corners, base, top, cell ):
        for i in range( len( corners ) ):
            a, b = corners[i], corners[( i + 1 ) % len( corners )]
            self.quad( cell, ( *a, base ), ( *b, base ), ( *b, top ), ( *a, top ), outward( a, b ) )

    def roof( self, corners, top, k, cell, wall_cell, kind="hip", pitch=PITCH, overhang=EAVE ):
        """ A hip, gable or flat roof over a rectangle (corners as rect_corners gives them, its first edge the long
        one), from the walls' top. Returns the ridge's height. """
        c = np.asarray( corners, float )
        if kind == "flat":
            u0, v0, u1, v1 = self.atlas.rect( "wall_top" )
            self.mesh.face( ATLAS, [ ( *p, top ) for p in c ], ( ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ),
                            self.atlas.mean["wall_top"], ( 0, 0, 1 ) )
            return top
        ax, ay = c[1] - c[0], c[3] - c[0]
        length, width = np.linalg.norm( ax ), np.linalg.norm( ay )
        ax, ay = ax / length, ay / width
        middle = c.mean( axis=0 )
        o = overhang * k
        eaves = np.array( [ c[0] - ( ax + ay ) * o, c[1] + ( ax - ay ) * o, c[2] + ( ax + ay ) * o, c[3] - ( ax - ay ) * o ] )
        ze = top - o * pitch
        zr = top + width / 2 * pitch
        u0, v0, u1, v1 = self.atlas.rect( cell )
        colour = self.atlas.mean[cell]
        up = ( 0.0, 0.0, 1.0 )
        E = [ ( *p, ze ) for p in eaves ]
        if kind == "hip":
            half = max( length - width, 0.0 ) / 2
            r0, r1 = ( *( middle - ax * half ), zr ), ( *( middle + ax * half ), zr )
            mid = ( ( u0 + u1 ) / 2, v1 )
            if half < 0.01 * width:
                # Square: a pyramid.
                for i in range( 4 ):
                    self.mesh.face( ATLAS, ( E[i], E[( i + 1 ) % 4], r0 ), ( ( u0, v0 ), ( u1, v0 ), mid ), colour, up )
            else:
                share = half / ( length / 2 + o )
                um0, um1 = ( u0 + u1 ) / 2 - ( u1 - u0 ) / 2 * share, ( u0 + u1 ) / 2 + ( u1 - u0 ) / 2 * share
                self.mesh.face( ATLAS, ( E[0], E[1], r1, r0 ), ( ( u0, v0 ), ( u1, v0 ), ( um1, v1 ), ( um0, v1 ) ), colour, up )
                self.mesh.face( ATLAS, ( E[2], E[3], r0, r1 ), ( ( u0, v0 ), ( u1, v0 ), ( um1, v1 ), ( um0, v1 ) ), colour, up )
                self.mesh.face( ATLAS, ( E[1], E[2], r1 ), ( ( u0, v0 ), ( u1, v0 ), mid ), colour, up )
                self.mesh.face( ATLAS, ( E[3], E[0], r0 ), ( ( u0, v0 ), ( u1, v0 ), mid ), colour, up )
        else:
            r0 = ( *( middle - ax * ( length / 2 + o ) ), zr )
            r1 = ( *( middle + ax * ( length / 2 + o ) ), zr )
            self.mesh.face( ATLAS, ( E[0], E[1], r1, r0 ), ( ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ), colour, up )
            self.mesh.face( ATLAS, ( E[2], E[3], r0, r1 ), ( ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ), colour, up )
            # The gable ends, in the walls' render.
            g0, g1, g2, g3 = self.atlas.rect( wall_cell )
            for a, b, sign in ( ( c[1], c[2], 1 ), ( c[3], c[0], -1 ) ):
                apex = ( *( middle + ax * sign * length / 2 ), zr )
                self.mesh.face( ATLAS, ( ( *a, top ), ( *b, top ), apex ), ( ( g0, g1 ), ( g2, g1 ), ( ( g0 + g2 ) / 2, g3 ) ),
                                self.atlas.mean[wall_cell], outward( a, b ) )
        # Under the eaves: the rafters' ends in shade.
        a0, b0, a1, b1 = self.atlas.rect( "eave" )
        sides = range( 4 ) if kind == "hip" else ( 0, 2 )
        for i in sides:
            j = ( i + 1 ) % 4
            self.mesh.face( ATLAS, ( ( *c[i], top ), ( *c[j], top ), E[j], E[i] ),
                            ( ( a0, b1 ), ( a1, b1 ), ( a1, b0 ), ( a0, b0 ) ), self.atlas.mean["eave"],
                            outward( c[i], c[j] ) - np.array( ( 0.0, 0.0, 1.0 ) ) )
        return zr

    def openings( self, corners, foot, top, k, storeys, rng, shutter, door_side=0 ):
        """ Windows with their shutters (open or shut) and a door, just proud of the walls. """
        proud = max( 0.03 * k, 1.5 )
        for i in range( 4 ):
            a, b = np.asarray( corners[i] ), np.asarray( corners[( i + 1 ) % 4] )
            run = b - a
            length = float( np.linalg.norm( run ) )
            along = run / length
            out = outward( a, b )
            lift = out[:2] * proud
            bays = int( ( length / k - 1.6 ) // 3.4 )
            if bays < 1:
                continue
            floor0 = max( foot[i], foot[( i + 1 ) % 4] )
            for storey in range( storeys ):
                for j in range( bays ):
                    x = ( j + 0.5 ) / bays * length
                    door = storey == 0 and i == door_side and j == bays // 2
                    w, h = ( 1.2, 2.3 ) if door else ( 1.0, 1.45 )
                    z0 = floor0 + ( 0.05 if door else 0.95 + storey * FLOOR ) * k
                    z1 = z0 + h * k
                    if z1 > top - 0.35 * k:
                        continue
                    centre = a + along * x + lift
                    p0, p1 = centre - along * w / 2 * k, centre + along * w / 2 * k
                    shut = not door and rng.random() < 0.3
                    cell = "door" if door else ( shutter if shut else "window" )
                    self.quad( cell, ( *p0, z0 ), ( *p1, z0 ), ( *p1, z1 ), ( *p0, z1 ), out )
                    if not door and not shut:
                        for side in ( -1, 1 ):
                            q0 = centre + along * side * ( w / 2 ) * k
                            q1 = centre + along * side * ( w / 2 + 0.52 ) * k
                            lo, hi = ( q1, q0 ) if side < 0 else ( q0, q1 )
                            self.quad( shutter, ( *lo, z0 ), ( *hi, z0 ), ( *hi, z1 ), ( *lo, z1 ), out )

    def house( self, centre, yaw, length, width, storeys, k, rng, wall=None, roof=None, kind=None, near=None,
               dovecote=False, chimney=None, door_side=0, roof_lift=0.0, claim=True ):
        """ A house: length x width metres (length the longer), storeys of FLOOR over its highest ground. Returns
        its corners and the walls' top. claim: keep other things off its ground (a terraced row's houses don't, so
        they can stand side by side). """
        wall = wall or pick( rng, RENDERS )
        roof = roof or pick( rng, ROOFS )
        kind = kind or ( "hip" if rng.random() < 0.6 else "gable" )
        if width > length:
            length, width, yaw = width, length, yaw + math.pi / 2
            door_side = ( door_side + 3 ) % 4
        corners = rect_corners( centre, yaw, length * k, width * k )
        foot = self.ground( corners[:, 0], corners[:, 1] )
        base = float( foot.min() ) - SINK * k
        top = float( foot.max() ) + ( storeys * FLOOR + 0.5 + roof_lift ) * k
        self.walls( corners, base, top, wall )
        ridge = self.roof( corners, top, k, roof, wall, kind )
        if near is None:
            near = self.pixels( centre[0], centre[1], k ) >= WINDOW_PX
        if near:
            self.openings( corners, foot, top, k, storeys, rng, pick( rng, SHUTTERS ), door_side )
            if chimney is None:
                chimney = rng.random() < 0.7
        if chimney:
            ax = ( corners[1] - corners[0] ) / np.linalg.norm( corners[1] - corners[0] )
            spot = np.asarray( centre ) + ax * ( rng.uniform( -0.3, 0.3 ) * length * k )
            box = rect_corners( spot, yaw, 0.9 * k, 0.7 * k )
            self.walls( box, top, ridge + 1.0 * k, wall )
            self.roof( box, ridge + 1.0 * k, k, "wall_top", wall, "flat" )
        if dovecote:
            # The colombaia: a little tower over the middle of the roof, with its own hip roof.
            box = rect_corners( centre, yaw, 4.2 * k, 4.0 * k )
            dtop = ridge + 3.2 * k
            self.walls( box, top, dtop, wall )
            u = self.atlas.rect( "opening" )
            for i in range( 4 ):
                a, b = box[i], box[( i + 1 ) % 4]
                out = outward( a, b )
                m = ( a + b ) / 2 + out[:2] * max( 0.03 * k, 1.0 )
                along = ( b - a ) / np.linalg.norm( b - a )
                for dx in ( -0.8, 0.0, 0.8 ):
                    p0, p1 = m + along * ( dx - 0.18 ) * k, m + along * ( dx + 0.18 ) * k
                    z0 = dtop - 1.4 * k
                    self.quad( "opening", ( *p0, z0 ), ( *p1, z0 ), ( *p1, z0 + 0.5 * k ), ( *p0, z0 + 0.5 * k ), out )
            ridge = self.roof( box, dtop, k, roof, wall, "hip" )
        self.buildings.append( ( corners, base, top, ridge ) )
        if claim:
            self.take( centre[0], centre[1], 0.5 * math.hypot( length, width ) * k )
        return corners, top

    def tower( self, centre, yaw, width, height, k, wall, top="pyramid", roof=None, belfry=False, depth=None ):
        """ A square tower: width (and depth) metres, height metres over its highest ground. top: "pyramid" (a steep
        roof), "parapet" (a corbelled parapet round a flat top) or "flat". """
        depth = depth or width
        corners = rect_corners( centre, yaw, width * k, depth * k )
        foot = self.ground( corners[:, 0], corners[:, 1] )
        base = float( foot.min() ) - SINK * k
        crown = float( foot.max() ) + height * k
        if top == "parapet":
            shaft = crown - 2.4 * k
            self.walls( corners, base, shaft, wall )
            # The corbels and machicolations as a dark band, then the parapet stepped out over them.
            band = rect_corners( centre, yaw, ( width + 0.5 ) * k, ( depth + 0.5 ) * k )
            self.walls( band, shaft - 0.8 * k, shaft, "opening" )
            wide = rect_corners( centre, yaw, ( width + 0.9 ) * k, ( depth + 0.9 ) * k )
            self.walls( wide, shaft, crown, wall )
            self.roof( wide, crown - 0.9 * k, k, "wall_top", wall, "flat" )
            ridge = crown
        else:
            self.walls( corners, base, crown, wall )
            ridge = self.roof( corners, crown, k, roof or "roof_old", wall, "hip" if top == "pyramid" else "flat",
                               pitch=math.tan( math.radians( 32.0 ) ), overhang=0.35 ) if top != "flat" else crown
            if top == "flat":
                self.roof( corners, crown, k, "wall_top", wall, "flat" )
        if belfry:
            # The bell openings, two a side, under the roof.
            for i in range( 4 ):
                a, b = corners[i], corners[( i + 1 ) % 4]
                out = outward( a, b )
                along = ( b - a ) / np.linalg.norm( b - a )
                m = ( a + b ) / 2 + out[:2] * max( 0.03 * k, 1.0 )
                z0 = crown - 5.0 * k
                for dx in ( -0.28, 0.28 ):
                    p0 = m + along * ( dx * width - 0.5 ) * k
                    p1 = m + along * ( dx * width + 0.5 ) * k
                    self.quad( "opening", ( *p0, z0 ), ( *p1, z0 ), ( *p1, z0 + 2.6 * k ), ( *p0, z0 + 2.6 * k ), out )
        self.buildings.append( ( corners, base, crown, ridge ) )
        self.take( centre[0], centre[1], 0.6 * math.hypot( width, depth ) * k )
        return corners, crown

    def wall_run( self, points, k, height, thickness, cell, closed=False ):
        """ A wall along plan points (anticlockwise if closed), height metres over the ground under each point. """
        pts = np.asarray( points, float )
        if closed:
            pts = np.vstack( ( pts, pts[:1] ) )
        z = self.ground( pts[:, 0], pts[:, 1] )
        for i in range( len( pts ) - 1 ):
            a, b = pts[i], pts[i + 1]
            out = outward( a, b )
            off = out[:2] * thickness / 2 * k
            za, zb = z[i] + height * k, z[i + 1] + height * k
            ba, bb = min( z[i], z[i + 1] ) - SINK * k, min( z[i], z[i + 1] ) - SINK * k
            self.quad( cell, ( *( a + off ), ba ), ( *( b + off ), bb ), ( *( b + off ), zb ), ( *( a + off ), za ), out )
            self.quad( cell, ( *( b - off ), bb ), ( *( a - off ), ba ), ( *( a - off ), za ), ( *( b - off ), zb ), -out )
            u0, v0, u1, v1 = self.atlas.rect( "wall_top" )
            self.mesh.face( ATLAS, ( ( *( a - off ), za ), ( *( b - off ), zb ), ( *( b + off ), zb ), ( *( a + off ), za ) ),
                            ( ( u0, v0 ), ( u1, v0 ), ( u1, v1 ), ( u0, v1 ) ), self.atlas.mean["wall_top"], ( 0, 0, 1 ) )
            self.buildings.append( ( np.array( [ a + off, b + off, b - off, a - off ] ), min( ba, bb ), max( za, zb ),
                                     max( za, zb ) ) )

    def church( self, centre, front, k, rng, length=28.0, width=12.0, eaves=12.0, tower_side=1, tower_height=34.0 ):
        """ A church: its front (a pale stone gable) facing direction front, the nave behind it, a lower apse at the
        far end, and a campanile at one front corner. """
        yaw = front + math.pi / 2       # its length runs along front: the front is the gable end
        ax = np.array( ( math.cos( front ), math.sin( front ) ) )
        side = np.array( ( -ax[1], ax[0] ) )
        centre = np.asarray( centre, float )
        corners = rect_corners( centre, front, length * k, width * k )
        foot = self.ground( corners[:, 0], corners[:, 1] )
        base = float( foot.min() ) - SINK * k
        top = float( foot.max() ) + eaves * k
        self.walls( corners, base, top, "stone_pale" )
        ridge = self.roof( corners, top, k, "roof_old", "white_stone", "gable", overhang=0.3 )
        # The front: a pale stone face just proud of the gable end, with its door and rose window.
        a, b = corners[1], corners[2]
        out = outward( a, b )
        lift = out[:2] * max( 0.04 * k, 1.5 )
        apex = ( *( ( a + b ) / 2 + lift ), ridge )
        self.quad( "white_stone", ( *( a + lift ), base ), ( *( b + lift ), base ), ( *( b + lift ), top ), ( *( a + lift ), top ), out )
        g0, g1, g2, g3 = self.atlas.rect( "white_stone" )
        self.mesh.face( ATLAS, ( ( *( a + lift ), top ), ( *( b + lift ), top ), apex ), ( ( g0, g1 ), ( g2, g1 ), ( ( g0 + g2 ) / 2, g3 ) ),
                        self.atlas.mean["white_stone"], out )
        m = ( a + b ) / 2 + lift * 2
        along = ( b - a ) / np.linalg.norm( b - a )
        z0 = float( max( foot[1], foot[2] ) )
        self.quad( "opening", ( *( m - along * 1.3 * k ), z0 ), ( *( m + along * 1.3 * k ), z0 ),
                   ( *( m + along * 1.3 * k ), z0 + 4.2 * k ), ( *( m - along * 1.3 * k ), z0 + 4.2 * k ), out )
        rose = [ ( *( m + along * math.cos( t ) * 1.6 * k ), z0 + 8.0 * k + math.sin( t ) * 1.6 * k )
                 for t in np.linspace( 0, 2 * math.pi, 9 )[:-1] ]
        self.mesh.face( ATLAS, rose, [ self._mid( "opening" ) ] * len( rose ), self.atlas.mean["opening"], out )
        self.buildings.append( ( corners, base, top, ridge ) )
        # The apse.
        back = centre - ax * ( length / 2 + 3.5 ) * k
        self.house( back, front + math.pi / 2, width * 0.75, 7.0, 0, k, rng, wall="stone_pale", roof="roof_old",
                    kind="hip", near=False, chimney=False, roof_lift=( eaves - 4.0 ) * 0.7 )
        # The campanile.
        spot = centre + ax * ( length / 2 - 3.0 ) * k + side * tower_side * ( width / 2 + 3.2 ) * k
        self.tower( spot, front, 5.5, tower_height, k, "stone_warm", top="pyramid", roof="roof_old", belfry=True )
        self.take( centre[0], centre[1], 0.55 * math.hypot( length, width ) * k )

    def _mid( self, cell ):
        u0, v0, u1, v1 = self.atlas.rect( cell )
        return ( ( u0 + u1 ) / 2, ( v0 + v1 ) / 2 )

    # Trees ------------------------------------------------------------------------------------------------------

    def cypress( self, e, n, height, rng, k=None, radius=None ):
        """ A cypress height metres tall (12-22 for grown ones), its widest radius about a fourteenth of that. """
        k = k or self.k_at( e, n )
        radius = radius or height * rng.uniform( 0.062, 0.078 )
        z = float( self.ground( e, n ) )
        px = self.pixels( e, n, height * k )
        sides = 8 if px > 60 else ( 6 if px > 18 else 5 )
        rows = CYPRESS_PROFILE if sides == 8 else CYPRESS_PROFILE[[ 0, 2, 3, 5, 6, 7, 8 ]] if sides == 6 else \
            CYPRESS_PROFILE[[ 0, 3, 5, 7, 8 ]]
        t, r = rows[:, 0], rows[:, 1] * ( 1.0 + 0.06 * rng.standard_normal( len( rows ) ) )
        r[-1] = 0.0
        H, R = height * k, radius * k
        lean = rng.normal( 0.0, 0.012, 2 ) * H
        theta = np.linspace( 0.0, 2 * math.pi, sides + 1 ) + rng.uniform( 0, 2 * math.pi )
        dr = np.gradient( r * R, t * H )
        P = np.zeros( ( len( t ), sides + 1, 3 ) )
        N = np.zeros_like( P )
        UV = np.zeros( ( len( t ), sides + 1, 2 ) )
        for i in range( len( t ) ):
            P[i, :, 0] = e + np.cos( theta ) * r[i] * R + lean[0] * t[i] ** 2
            P[i, :, 1] = n + np.sin( theta ) * r[i] * R + lean[1] * t[i] ** 2
            P[i, :, 2] = z - SINK * k + t[i] * ( H + SINK * k )
            N[i, :, 0], N[i, :, 1], N[i, :, 2] = np.cos( theta ), np.sin( theta ), -dr[i]
            UV[i, :, 0] = np.linspace( 0, 2 * math.pi * radius / FOLIAGE_TILE, sides + 1 )
            UV[i, :, 1] = t[i] * height / FOLIAGE_TILE
        N /= np.linalg.norm( N, axis=-1, keepdims=True )
        self.mesh.grid( CYPRESS, P, N, UV, self.cypress_colour )
        self.trees.append( ( e, n, z, R, 0.47 * H, 0.5 * H, TREE_CYPRESS ) )
        self.take( e, n, R * 1.2 )

    def pine( self, e, n, height, rng, k=None ):
        """ An umbrella pine height metres tall: a bare trunk, often leaning, under a flat crown. """
        k = k or self.k_at( e, n )
        z = float( self.ground( e, n ) )
        H = height * k
        R = height * rng.uniform( 0.38, 0.48 ) * k
        depth = height * 0.28 * k
        lean = rng.normal( 0.0, 0.08, 2 ) * H
        top = np.array( ( e + lean[0], n + lean[1], z + H - depth ) )
        # The trunk.
        sides = 5
        theta = np.linspace( 0, 2 * math.pi, sides + 1 )
        P = np.zeros( ( 2, sides + 1, 3 ) )
        for i, ( p, rad ) in enumerate( ( ( np.array( ( e, n, z - SINK * k ) ), 0.32 * k ), ( top, 0.18 * k ) ) ):
            P[i, :, 0], P[i, :, 1], P[i, :, 2] = p[0] + np.cos( theta ) * rad, p[1] + np.sin( theta ) * rad, p[2]
        N = np.stack( ( np.cos( theta ), np.sin( theta ), np.zeros_like( theta ) ), -1 )[None].repeat( 2, 0 )
        u0, v0, u1, v1 = self.atlas.rect( "bark" )
        UV = np.stack( np.meshgrid( np.linspace( u0, u1, sides + 1 ), ( v0, v1 ) ), -1 )
        self.mesh.grid( ATLAS, P, N, UV, self.atlas.mean["bark"] )
        # The crown: its top and its underside.
        sides = 12 if self.pixels( e, n, R ) > 30 else 8
        theta = np.linspace( 0, 2 * math.pi, sides + 1 ) + rng.uniform( 0, 2 * math.pi )
        for profile in ( PINE_TOP, PINE_UNDER ):
            rr = profile[:, 0] * R * ( 1.0 + 0.05 * rng.standard_normal( len( profile ) ) )
            zz = profile[:, 1] * depth
            P = np.zeros( ( len( profile ), sides + 1, 3 ) )
            P[..., 0] = top[0] + rr[:, None] * np.cos( theta )
            P[..., 1] = top[1] + rr[:, None] * np.sin( theta )
            P[..., 2] = top[2] + zz[:, None]
            dz = np.gradient( zz, rr ) if profile is PINE_UNDER else np.gradient( zz, -rr )
            slope = np.nan_to_num( dz, nan=0.0, posinf=0.0, neginf=0.0 )
            if profile is PINE_TOP:
                N = np.stack( ( np.cos( theta )[None] * np.abs( slope )[:, None], np.sin( theta )[None] * np.abs( slope )[:, None],
                                np.ones( ( len( profile ), sides + 1 ) ) ), -1 )
                N[0, :, :2] = np.stack( ( np.cos( theta ), np.sin( theta ) ), -1 )
                N[0, :, 2] = 0.3
            else:
                N = np.zeros( ( len( profile ), sides + 1, 3 ) )
                N[..., 2] = -1.0
            N /= np.linalg.norm( N, axis=-1, keepdims=True )
            UV = np.stack( ( P[..., 0] / ( FOLIAGE_TILE * 2 * k ), P[..., 1] / ( FOLIAGE_TILE * 2 * k ) ), -1 )
            self.mesh.grid( PINE, P, N, UV, self.pine_colour )
        self.trees.append( ( top[0], top[1], z, R, top[2] + depth * 0.4 - z, depth * 0.5, TREE_PINE ) )
        self.take( e, n, R * 0.8 )

    def preview_textures( self ):
        """ Each material's colour map (linear), in the mesh's sorted order (Mesh.preview_triangles). """
        _, light, dead = draw_foliage()
        maps = { ATLAS: self.atlas.colour, CYPRESS: foliage_colour( CYPRESS_COLOUR, light, dead ),
                 PINE: foliage_colour( PINE_COLOUR, light, dead ) }
        return [ maps[m] for m in sorted( self.mesh.parts ) ]

    def paint_data( self ):
        """ What the painter needs: the buildings ( count, 11: their corners' e and n, the base, the eaves and the
        ridge ), the trees as crowns, the yards and the roads. """
        boxes = np.array( [ ( *np.asarray( c, float ).ravel(), base, top, ridge )
                            for c, base, top, ridge in self.buildings ] ).reshape( -1, 11 )
        return boxes, self.crowns(), self.yards, self.roads

    def crowns( self ):
        """ The trees as the painter's crowns (belltower_vista_paint.CROWN_FIELDS): their shadows, with no tops
        (the colour is -1: their models draw them). """
        import belltower_vista_paint as P
        out = np.full( ( len( self.trees ), P.CROWN_FIELDS ), -1.0 )
        for i, ( e, n, z, radius, middle, half, kind ) in enumerate( self.trees ):
            out[i, :7] = ( e, n, z, radius, middle, half, kind )
            out[i, 10] = P.TREES[kind, 3]
            out[i, 11] = i * 7.31 % 1000.0
        return out


# ---------------------------------------------------------------------------------------------------------------------
# The places

class Frame:
    """ A settlement's own plan: metres along `right` and `forward` from its middle, at its middle's scale. """

    def __init__( self, e, n, front=0.0 ):
        self.e, self.n = float( e ), float( n )
        self.k = World.k_at( e, n )
        self.forward = np.array( ( math.cos( front ), math.sin( front ) ) )
        self.right = np.array( ( self.forward[1], -self.forward[0] ) )
        self.front = front

    def __call__( self, x, y ):
        """ Plan point x metres right and y forward of the middle. """
        return np.array( ( self.e, self.n ) ) + ( self.right * x + self.forward * y ) * self.k

    def polar( self, r, theta ):
        """ Plan point r metres out from the middle at plan angle theta. """
        return np.array( ( self.e + math.cos( theta ) * r * self.k, self.n + math.sin( theta ) * r * self.k ) )


TOWN_EYE = ( 250.0, 125.0, 128.0 )   # an eye in Belltower's streets, for what the town sees


def seen_share( world, points, eye=TOWN_EYE, samples=240 ):
    """ The share of plan points ( P, 2 ) whose ground the town's eye sees over the land between. """
    seen = 0
    for e, n in points:
        ts = np.linspace( 0.05, 0.995, samples )
        E, N = eye[0] + ( e - eye[0] ) * ts, eye[1] + ( n - eye[1] ) * ts
        Z = world.ground( np.append( E, e ), np.append( N, n ) )
        D = np.hypot( np.append( E, e ) - eye[0], np.append( N, n ) - eye[1] )
        angles = ( Z - eye[2] ) / D
        seen += angles[-1] + 2.0 * world.k_at( e, n ) / D[-1] >= angles[:-1].max()
    return seen / max( len( points ), 1 )


def contour_radii( world, frame, thetas, drop ):
    """ How far out (m) from the frame's middle, at each plan angle, the ground is drop metres under the middle's. """
    rs = np.arange( 0.0, 420.0, 1.0 )
    E = frame.e + np.outer( np.cos( thetas ), rs ) * frame.k
    N = frame.n + np.outer( np.sin( thetas ), rs ) * frame.k
    Z = world.ground( E, N )
    level = float( world.ground( frame.e, frame.n ) ) - drop * frame.k
    below = Z < level
    first = np.where( below.any( axis=1 ), np.argmax( below, axis=1 ), len( rs ) - 1 )
    i0 = np.maximum( first - 1, 0 )
    za, zb = Z[np.arange( len( thetas ) ), i0], Z[np.arange( len( thetas ) ), first]
    r = rs[i0] + np.clip( ( za - level ) / np.maximum( za - zb, 1e-6 ), 0, 1 ) * ( rs[first] - rs[i0] )
    # Smoothed round the circle: the mesh's facets wiggle a contour that the streets wouldn't.
    pad = np.concatenate( ( r[-4:], r, r[:4] ) )
    return np.convolve( pad, np.ones( 9 ) / 9, mode="same" )[4:-4]


class Lots:
    """ A settlement's houses so far, so that one row's don't run into another's. """

    def __init__( self, k ):
        self.k, self.size, self.cells = k, 14.0 * k, defaultdict( list )

    def clear( self, e, n, half, row ):
        ci, cj = int( e // self.size ), int( n // self.size )
        for di in ( -1, 0, 1 ):
            for dj in ( -1, 0, 1 ):
                for pe, pn, ph, pr in self.cells[( ci + di, cj + dj )]:
                    if pr != row and math.hypot( e - pe, n - pn ) < 0.85 * ( half + ph ) * self.k:
                        return False
        return True

    def add( self, e, n, half, row ):
        self.cells[( int( e // self.size ), int( n // self.size ) )].append( ( e, n, half, row ) )


def ring_of_houses( world, frame, rng, thetas, radii, side, depth, arc, storeys, lots, row ):
    """ A terraced row of houses along one side of a street that follows a contour (radii at thetas): side -1 is the
    uphill side, +1 downhill. arc ( start, end ) in radians. A house goes where nothing claimed stands (a church, a
    tower, a square) and no other row's house does (lots). """
    k = frame.k
    theta = arc[0] + rng.uniform( 0, 0.02 )
    while theta < arc[1]:
        r = float( np.interp( theta, thetas, radii, period=2 * math.pi ) )
        width = rng.uniform( 6.0, 12.5 )
        d = rng.uniform( *depth )
        step = width / max( r, 10.0 )
        mid = theta + step / 2
        rm = float( np.interp( mid, thetas, radii, period=2 * math.pi ) ) + side * ( d / 2 + 2.0 )
        a = frame.polar( float( np.interp( theta, thetas, radii, period=2 * math.pi ) ), theta )
        b = frame.polar( float( np.interp( theta + step, thetas, radii, period=2 * math.pi ) ), theta + step )
        centre = frame.polar( rm, mid )
        yaw = math.atan2( b[1] - a[1], b[0] - a[0] )
        half = min( width, d ) / 2
        if world.free( centre[0], centre[1], half * k ) and lots.clear( centre[0], centre[1], half, row ):
            # The street is on the house's inner side (edge 2) for the downhill row, its outer side (edge 0) uphill.
            world.house( centre, yaw, width, d, int( rng.choice( storeys ) ), k, rng,
                         door_side=2 if side > 0 else 0, near=False, claim=False )
            lots.add( centre[0], centre[1], half, row )
        gap = 0.0 if rng.random() < 0.78 else ( rng.uniform( 2.5, 4.5 ) if rng.random() < 0.8 else rng.uniform( 9, 16 ) )
        theta += step + gap / max( r, 10.0 )


def winding_road( world, start, heading, k, steps, step=10.0, grade=0.07 ):
    """ A road from start that winds down the hill as a road builder lays it, falling about grade, step metres at a
    time and turning at most 20 degrees a step, round what's already there. It stops on the level. """
    p = np.asarray( start, float )
    line = [ p.copy() ]
    level = 0
    for _ in range( steps ):
        z = float( world.ground( p[0], p[1] ) )
        best = None
        for turn in np.radians( np.arange( -20.0, 21.0, 5.0 ) ):
            h = heading + turn
            q = p + np.array( ( math.cos( h ), math.sin( h ) ) ) * step * k
            fall = ( z - float( world.ground( q[0], q[1] ) ) ) / ( step * k )
            cost = abs( fall - grade ) + 0.03 * abs( turn ) + ( 0.0 if world.free( q[0], q[1], ROAD_HALF * k ) else 1.0 )
            if best is None or cost < best[0]:
                best = ( cost, h, q, fall )
        _, heading, p, fall = best
        line.append( p.copy() )
        level = level + 1 if abs( fall ) < 0.015 else 0
        if level >= 6:
            break
    return np.array( line )


def hill_town( world ):
    """ The hill town on the west ridge's summit, facing Belltower: the castle on the top, then streets along the
    contours, houses both sides, down its east face, a church and a few tower houses among them, the town walls with
    their towers and a gate towards Belltower, and the cemetery and cypresses outside. """
    rng = np.random.default_rng( 31 )
    frame = Frame( -28500.0, 5000.0 )
    k = frame.k
    thetas = np.radians( np.arange( 0.0, 360.0, 2.0 ) )
    # Each street's contour: as far down as the ground is at these distances east of the top.
    streets = [ 52.0, 76.0, 100.0, 124.0, 148.0, 172.0 ]
    east = np.array( [ frame.polar( r, 0.0 ) for r in np.array( streets + [ 196.0 ] ) ] )
    drops = ( float( world.ground( frame.e, frame.n ) ) - world.ground( east[:, 0], east[:, 1] ) ) / k
    rings = [ contour_radii( world, frame, thetas, d ) for d in drops ]
    arc = ( math.radians( -128.0 ), math.radians( 128.0 ) )

    # The castle: a curtain wall round the top with towers at its corners, the keep and the lord's house.
    corners = [ frame.polar( 36.0 + rng.uniform( -4, 4 ), t ) for t in np.radians( np.arange( 0, 360, 60 ) + 15 ) ]
    world.wall_run( corners, k, 11.0, 2.2, "stone_grey", closed=True )
    for c in corners:
        world.tower( c, rng.uniform( 0, math.pi ), 6.5, 16.0, k, "stone_grey", top="parapet" )
    world.tower( frame( 6.0, -9.0 ), 0.3, 13.0, 36.0, k, "stone_warm", top="parapet" )
    world.house( frame( -4.0, 12.0 ), 0.15, 22.0, 12.0, 3, k, rng, wall="stone_warm", roof="roof_old", kind="hip",
                 near=False )
    world.take( frame.e, frame.n, 40.0 * k )

    # The church on the second street, its front to the east, and the civic tower across its square.
    church_at = math.radians( 18.0 )
    church_r = float( np.interp( church_at, thetas, rings[1] ) ) + 14.0
    church = frame.polar( church_r, church_at )
    world.church( church, church_at, k, rng, tower_side=-1 )
    square = frame.polar( church_r + 26.0, church_at - 0.12 )
    world.take( square[0], square[1], 16.0 * k )
    world.tower( frame.polar( church_r + 30.0, church_at - 0.32 ), church_at, 6.5, 42.0, k, "stone_warm",
                 top="parapet" )
    # Tower houses: the old families' towers, here and there on the inner streets.
    for t, r, h in ( ( -0.55, 64.0, 30.0 ), ( 0.62, 58.0, 26.0 ), ( -1.2, 90.0, 24.0 ), ( 1.05, 86.0, 28.0 ),
                     ( -0.18, 112.0, 22.0 ) ):
        world.tower( frame.polar( r, t ), t + rng.uniform( -0.2, 0.2 ), 7.0, h, k, pick( rng, ( ( "stone_warm", 2 ), ( "stone_grey", 1 ) ) ),
                     top="parapet" if rng.random() < 0.6 else "flat" )

    # The road up from the gate keeps clear, straight up the east side to the castle.
    gate_at = math.radians( -6.0 )
    for r in np.arange( 40.0, 260.0, 4.0 ):
        world.take( *frame.polar( r, gate_at ), 3.0 * k )

    lots = Lots( k )
    for i in range( len( streets ) ):
        storeys = ( 3, 3, 4 ) if i < 2 else ( ( 2, 3, 3 ) if i < 4 else ( 2, 2, 3 ) )
        if i:
            ring_of_houses( world, frame, rng, thetas, rings[i], -1, ( 7.0, 10.0 ), arc, storeys, lots, 2 * i )
        ring_of_houses( world, frame, rng, thetas, rings[i], 1, ( 7.0, 10.0 ), arc, storeys, lots, 2 * i + 1 )

    # The town walls, out past the last street, all the way round; towers on them, and the gate.
    walls = np.array( [ frame.polar( r + 14.0, t ) for r, t in zip( rings[-1], thetas ) ][::3] )
    world.wall_run( walls, k, 9.0, 2.0, "stone_warm", closed=True )
    for t in np.radians( np.arange( -150, 180, 30 ) ):
        r = float( np.interp( t, thetas, rings[-1], period=2 * math.pi ) ) + 14.0
        world.tower( frame.polar( r, t ), t, 7.0, 14.0, k, "stone_warm", top="parapet" if t % 2 else "flat" )
    gate_r = float( np.interp( gate_at, thetas, rings[-1], period=2 * math.pi ) ) + 14.0
    gate = frame.polar( gate_r, gate_at )
    corners, top = world.tower( gate, gate_at, 10.0, 17.0, k, "stone_warm", top="parapet", depth=12.0 )
    a, b = corners[1], corners[2]
    out = outward( a, b )
    m = ( a + b ) / 2 + out[:2] * max( 0.04 * k, 1.5 )
    along = ( b - a ) / np.linalg.norm( b - a )
    z0 = float( world.ground( m[0], m[1] ) )
    world.quad( "opening", ( *( m - along * 2.2 * k ), z0 - SINK * k ), ( *( m + along * 2.2 * k ), z0 - SINK * k ),
                ( *( m + along * 2.2 * k ), z0 + 5.5 * k ), ( *( m - along * 2.2 * k ), z0 + 5.5 * k ), out )
    world.yard( YARD_TOWN, walls )

    # Outside: cypresses along the road down from the gate, the cemetery, and a few by the walls.
    for j in range( 15 ):
        r = gate_r + 14.0 + j * 10.0
        for side in ( -1, 1 ):
            p = frame.polar( r, gate_at ) + np.array( ( -math.sin( gate_at ), math.cos( gate_at ) ) ) * side * 6.0 * k
            if world.free( p[0], p[1], 1.0 * k ):
                world.cypress( p[0], p[1], rng.uniform( 14, 20 ), rng, k )
    cemetery( world, frame, rng, math.radians( -38.0 ),
              float( np.interp( math.radians( -38.0 ), thetas, rings[-1], period=2 * math.pi ) ) + 70.0 )
    # The road: out of the gate between the cypresses, then down the hill.
    straight = np.array( [ frame.polar( gate_r + r, gate_at ) for r in ( 4.0, 60.0, 120.0, 165.0 ) ] )
    world.road( np.vstack( ( straight, winding_road( world, straight[-1], gate_at, k, 90 )[1:] ) ), k )
    for _ in range( 24 ):
        t = rng.uniform( *arc )
        r = float( np.interp( t, thetas, rings[-1], period=2 * math.pi ) ) + rng.uniform( 24, 70 )
        p = frame.polar( r, t )
        for c in range( rng.integers( 1, 4 ) ):
            q = p + rng.normal( 0, 4.0, 2 ) * k
            if world.free( q[0], q[1], 1.5 * k ):
                world.cypress( q[0], q[1], rng.uniform( 13, 21 ), rng, k )
    # Nothing else inside the walls.
    world.take( frame.e, frame.n, ( float( rings[-1].max() ) + 16.0 ) * k )


def cemetery( world, frame, rng, at, r ):
    """ A walled cemetery out of town: white walls, cypresses along them inside and down the middle, and its
    chapel at the far end. """
    k = frame.k
    centre = frame.polar( r, at )
    length, width = 44.0, 30.0
    corners = rect_corners( centre, at, length * k, width * k )
    world.wall_run( corners, k, 2.8, 0.6, "render_cream", closed=True )
    ax = ( corners[1] - corners[0] ) / np.linalg.norm( corners[1] - corners[0] )
    ay = ( corners[3] - corners[0] ) / np.linalg.norm( corners[3] - corners[0] )
    for j in range( 7 ):
        x = ( -length / 2 + 4.0 + j * ( length - 8.0 ) / 6 )
        for y in ( -width / 2 + 3.0, width / 2 - 3.0, 0.0 ):
            if y == 0.0 and j % 2:
                continue
            p = centre + ( ax * x + ay * y ) * k
            world.cypress( p[0], p[1], rng.uniform( 13, 19 ), rng, k )
    world.yard( YARD_GRAVEL, corners )
    chapel = centre - ax * ( length / 2 - 4.5 ) * k
    world.house( chapel, at + math.pi / 2, 7.0, 5.0, 1, k, rng, wall="render_cream", roof="roof_old", kind="gable",
                 near=False, chimney=False, roof_lift=1.5 )
    world.take( centre[0], centre[1], 0.5 * math.hypot( length, width ) * k )


def villa( world ):
    """ The villa on the east ridge, facing Belltower down the long avenue of cypresses that climbs to it: the house
    with its belvedere, the lemon house and the farm's buildings behind, a walled garden in front, umbrella pines. """
    rng = np.random.default_rng( 47 )
    front = math.pi     # it faces west
    f = Frame( 27800.0, 300.0, front )
    k = f.k
    world.house( f( 0, 0 ), facing( front ), 30.0, 15.0, 3, k, rng, wall="render_ochre", roof="roof_old", kind="hip",
                 dovecote=True, chimney=True )
    world.house( f( -24, -14 ), facing( front ) + math.pi / 2, 18.0, 8.0, 1, k, rng, wall="render_yellow",
                 roof="roof_pale", kind="gable" )
    world.house( f( 26, -18 ), facing( front ), 26.0, 11.0, 2, k, rng, wall="stone_warm", roof="roof_lichen",
                 kind="gable" )
    world.house( f( 34, 6 ), facing( front ) + math.pi / 2, 14.0, 9.0, 2, k, rng, wall="brick", roof="roof_dark",
                 kind="gable" )
    world.house( f( -30, 12 ), facing( front ), 9.0, 6.0, 1, k, rng, wall="render_cream", roof="roof_old",
                 kind="gable", roof_lift=2.0 )
    world.round_yard( YARD_FARM, *f( 4, -4 ), 46.0 * k )
    # The garden: walled, the avenue's gate in the middle of its far wall.
    garden = [ f( -26, 12 ), f( 26, 12 ), f( 26, 56 ), f( -26, 56 ) ]
    world.yard( YARD_GARDEN, garden )
    world.wall_run( garden, k, 2.4, 0.6, "render_cream", closed=True )
    world.take( *f( 0, 34 ), 30.0 * k )
    for x in ( -22.0, 22.0 ):
        for y in range( 18, 56, 8 ):
            p = f( x, y )
            world.cypress( p[0], p[1], rng.uniform( 9, 12 ), rng, k )
    # The avenue: pairs of cypresses down the slope from the garden gate, slanting across the slope the town sees
    # (pointed at the town, its two rows would line up into two spikes).
    gate = f( 0, 60 )
    best = None
    for turn in ( -0.95, -0.7, 0.7, 0.95 ):
        way = np.array( ( math.cos( front + turn ), math.sin( front + turn ) ) )
        line = gate + np.outer( np.arange( 0, 46 ) * 9.0, way ) * k
        score = seen_share( world, line ) - 2.0 * float( np.mean( np.diff( world.ground( line[:, 0], line[:, 1] ) ) > 0 ) )
        if best is None or score > best[0]:
            best = ( score, way, line )
    _, way, line = best
    across = np.array( ( -way[1], way[0] ) )
    for p0 in line:
        for x in ( -6.0, 6.0 ):
            p = p0 + across * ( x + rng.normal( 0, 0.15 ) ) * k
            world.cypress( p[0], p[1], rng.uniform( 15, 21 ), rng, k )
    # Its white road, on down the hill past the last pair.
    world.road( np.vstack( ( line[[ 0, -1 ]], winding_road( world, line[-1], math.atan2( way[1], way[0] ), k, 50 )[1:] ) ), k )
    for x, y in ( ( -40, -6 ), ( 44, -30 ), ( -14, -34 ), ( 50, 20 ), ( -48, 30 ) ):
        p = f( x, y )
        world.pine( p[0], p[1], rng.uniform( 14, 19 ), rng, k )


def village( world ):
    """ The village on the south-west hill: houses round its top, the church at the top, its cemetery outside. """
    rng = np.random.default_rng( 53 )
    frame = Frame( -19500.0, -48000.0 )
    k = frame.k
    thetas = np.radians( np.arange( 0.0, 360.0, 2.0 ) )
    streets = [ 30.0, 52.0, 74.0 ]
    towards = math.atan2( V.CENTRE[1] - frame.n, V.CENTRE[0] - frame.e )
    east = np.array( [ frame.polar( r, towards ) for r in streets ] )
    drops = ( float( world.ground( frame.e, frame.n ) ) - world.ground( east[:, 0], east[:, 1] ) ) / k
    rings = [ contour_radii( world, frame, thetas, max( d, 1.0 ) ) for d in drops ]
    world.church( ( frame.e, frame.n ), towards, k, rng, length=24.0, width=10.0, eaves=10.0, tower_height=28.0 )
    arc = ( towards - math.radians( 115.0 ), towards + math.radians( 115.0 ) )

    lots = Lots( k )
    for i in range( len( streets ) ):
        ring_of_houses( world, frame, rng, thetas, rings[i], 1, ( 7.0, 10.0 ), arc, ( 2, 2, 3 ), lots, 2 * i + 1 )
        if i:
            ring_of_houses( world, frame, rng, thetas, rings[i], -1, ( 7.0, 10.0 ), arc, ( 2, 3 ), lots, 2 * i )
    rim = [ frame.polar( float( np.interp( t, thetas, rings[-1], period=2 * math.pi ) ) + 8.0, t )
            for t in np.linspace( arc[0], arc[1], 40 ) ]
    world.yard( YARD_TOWN, [ frame.polar( 14.0, towards + math.pi ) ] + rim )
    cemetery( world, frame, rng, towards + 0.9, float( np.interp( towards + 0.9, thetas, rings[-1], period=2 * math.pi ) ) + 40.0 )
    world.take( frame.e, frame.n, ( float( rings[-1].max() ) + 14.0 ) * k )


def land_use( e, n ):
    """ ( the ground's kind, whether it's woods, its slope ) at a plan point, as the painter decides it. """
    import belltower_vista_paint as P
    s, z, res = P._decide( float( e ), float( n ), V._GRADIENTS )
    t0, n0 = int( res[5] ), float( res[6] )
    woods = t0 in ( P.OAK, P.HOLM, P.BEECH, P.PINE ) and n0 * float( P.LAYER_CELL[0] ) ** 2 > 0.25
    return float( res[3] ), woods


def slope_at( world, e, n, k ):
    """ The ground's slope at ( e, n ) and the way up it (radians). """
    h = 6.0 * k
    zs = world.ground( np.array( ( e + h, e - h, e, e ) ), np.array( ( n, n, n + h, n - h ) ) )
    return math.hypot( zs[0] - zs[1], zs[2] - zs[3] ) / ( 2 * h ), math.atan2( zs[2] - zs[3], zs[0] - zs[1] )


def open_ground( world, e, n, k, radius, max_slope ):
    """ Whether ( e, n ) is open, gentle ground, off the river's bed and away from everything already built. """
    if not world.free( e, n, radius * k ):
        return False
    slope, _ = slope_at( world, e, n, k )
    if slope > max_slope:
        return False
    kind, woods = land_use( e, n )
    return kind < 2.5 and not woods and abs( n - float( V.river_line( e ) ) ) > 3 * V.RIVER_BED


def sample_sites( world, rng, count, d_range, test, spacing ):
    """ Up to count plan points spread evenly over the land as it's seen (its apparent places), between d_range out
    from the walls, passing test, at least spacing metres apart where they stand. """
    sites = []
    r0, r1 = d_range
    R0, R1 = ( ( 2380.0 + r ) * float( V.scale( r ) ) for r in ( r0, r1 ) )
    for _ in range( count * 40 ):
        if len( sites ) >= count:
            break
        t = rng.uniform( 0, 2 * math.pi )
        R = math.sqrt( R0 * R0 + rng.random() * ( R1 * R1 - R0 * R0 ) )
        e, n = ( float( x ) for x in V.real_place( V.CENTRE[0] + math.cos( t ) * R, V.CENTRE[1] + math.sin( t ) * R ) )
        dd = float( V.town_distance( e, n ) )
        if dd < r0 or dd > r1:
            continue
        k = World.k_at( e, n )
        if any( math.hypot( e - se, n - sn ) < spacing * k for se, sn in sites ):
            continue
        if test( e, n, k ):
            sites.append( ( e, n ) )
    return sites


def farm( world, e, n, rng ):
    """ A podere: the farmhouse (often with its dovecote tower), its barn and shed, and its cypresses. """
    k = World.k_at( e, n )
    _, uphill = slope_at( world, e, n, k )
    front = uphill + math.pi        # the house faces down the slope
    f = Frame( e, n, front )
    world.round_yard( YARD_FARM, *f( 0, -4 ), 24.0 * k )
    stone = rng.random() < 0.38
    wall = pick( rng, ( ( "stone_warm", 3 ), ( "stone_pale", 1 ), ( "stone_grey", 1 ) ) ) if stone else \
        pick( rng, RENDERS[:8] )
    roof = pick( rng, ROOFS )
    world.house( f( 0, 0 ), facing( front ), rng.uniform( 13, 17 ), rng.uniform( 9, 11 ), 2, k, rng, wall=wall,
                 roof=roof, kind="hip", dovecote=rng.random() < 0.45 )
    side = rng.choice( ( -1, 1 ) )
    if rng.random() < 0.8:
        world.house( f( side * rng.uniform( 15, 19 ), rng.uniform( -10, -4 ) ), facing( front ) + rng.choice( ( 0, math.pi / 2 ) ),
                     rng.uniform( 10, 14 ), rng.uniform( 7, 9 ), 1, k, rng,
                     wall="brick" if rng.random() < 0.5 else wall, roof=pick( rng, ROOFS ), kind="gable", roof_lift=1.6 )
    if rng.random() < 0.4:
        world.house( f( -side * rng.uniform( 12, 15 ), rng.uniform( -6, 2 ) ), facing( front ), 5.0, 4.0, 1, k, rng,
                     wall=wall, roof=pick( rng, ROOFS ), kind="gable", chimney=False )
    style = rng.choice( ( "avenue", "group", "row", "pair" ), p=( 0.3, 0.3, 0.2, 0.2 ) )
    if style == "avenue":
        for j in range( rng.integers( 5, 10 ) ):
            for x in ( -4.5, 4.5 ):
                p = f( x, 16.0 + j * 9.0 )
                if open_ground( world, p[0], p[1], k, 1.2, 0.45 ):
                    world.cypress( p[0], p[1], rng.uniform( 13, 19 ), rng, k )
    elif style == "group":
        spot = f( -side * rng.uniform( 14, 22 ), rng.uniform( 4, 14 ) )
        for _ in range( rng.integers( 3, 7 ) ):
            p = spot + rng.normal( 0, 3.0, 2 ) * k
            if world.free( p[0], p[1], 1.2 * k ):
                world.cypress( p[0], p[1], rng.uniform( 12, 20 ), rng, k )
    elif style == "row":
        x0 = side * rng.uniform( 12, 18 )
        for j in range( rng.integers( 5, 10 ) ):
            p = f( x0, -12.0 + j * 7.0 )
            if world.free( p[0], p[1], 1.2 * k ):
                world.cypress( p[0], p[1], rng.uniform( 13, 19 ), rng, k )
    else:
        for x in ( -7.0, 7.0 ):
            p = f( x, 9.0 )
            if world.free( p[0], p[1], 1.2 * k ):
                world.cypress( p[0], p[1], rng.uniform( 14, 20 ), rng, k )
    if rng.random() < 0.3:
        p = f( side * rng.uniform( -14, 14 ), rng.uniform( 10, 20 ) )
        if world.free( p[0], p[1], 5.0 * k ):
            world.pine( p[0], p[1], rng.uniform( 12, 17 ), rng, k )


def farms( world ):
    rng = np.random.default_rng( 61 )
    sites = sample_sites( world, rng, 44, ( 1800.0, 44000.0 ),
                          lambda e, n, k: open_ground( world, e, n, k, 40.0, 0.17 ), 420.0 )
    for e, n in sites:
        farm( world, e, n, rng )
    return len( sites )


def knolls( world, rng, count, d_range ):
    """ Hilltops: points higher than the ground round them, gentle on top. """
    best = []
    for _ in range( 3000 ):
        t = rng.uniform( 0, 2 * math.pi )
        d = rng.uniform( *d_range )
        e = V.CENTRE[0] + math.cos( t ) * ( 2380.0 + d )
        n = V.CENTRE[1] + math.sin( t ) * ( 2380.0 + d )
        k = World.k_at( e, n )
        ring = np.linspace( 0, 2 * math.pi, 8, endpoint=False )
        zs = world.ground( e + np.cos( ring ) * 60 * k, n + np.sin( ring ) * 60 * k )
        z = float( world.ground( e, n ) )
        rise = ( z - zs.mean() ) / k
        if rise > 4.0 and slope_at( world, e, n, k )[0] < 0.12:
            best.append( ( rise, e, n ) )
    best.sort( reverse=True )
    out = []
    for _, e, n in best:
        k = World.k_at( e, n )
        if len( out ) < count and all( math.hypot( e - a, n - b ) > 300 * k for a, b in out ) and \
                open_ground( world, e, n, k, 30.0, 0.15 ):
            out.append( ( e, n ) )
    return out


def chapels( world ):
    """ Wayside chapels on knolls, each with its cypresses. """
    rng = np.random.default_rng( 67 )
    spots = knolls( world, rng, 6, ( 3000.0, 30000.0 ) )
    for e, n in spots:
        k = World.k_at( e, n )
        front = math.atan2( V.CENTRE[1] - n, V.CENTRE[0] - e ) + rng.uniform( -0.6, 0.6 )
        f = Frame( e, n, front )
        world.round_yard( YARD_GRAVEL, *f( 0, 1 ), 9.0 * k )
        world.house( f( 0, 0 ), facing( front ) + math.pi / 2, 8.0, 5.5, 1, k, rng, wall=pick( rng, ( ( "render_cream", 2 ), ( "stone_pale", 1 ) ) ),
                     roof="roof_old", kind="gable", chimney=False, roof_lift=1.8 )
        for x, y in ( ( -4.5, 6.0 ), ( 4.5, 6.0 ), ( -5.5, -3.0 ), ( 5.5, -3.0 ) )[:rng.integers( 2, 5 )]:
            p = f( x, y )
            world.cypress( p[0], p[1], rng.uniform( 14, 20 ), rng, k )
    return len( spots )


def lone_cypresses( world ):
    """ Cypresses on their own in the fields, in rows along their edges, and in small clumps. """
    rng = np.random.default_rng( 71 )
    count = 0
    for e, n in sample_sites( world, rng, 70, ( 1500.0, 38000.0 ),
                              lambda e, n, k: open_ground( world, e, n, k, 8.0, 0.3 ), 60.0 ):
        world.cypress( e, n, rng.uniform( 13, 21 ), rng )
        count += 1
    for e, n in sample_sites( world, rng, 24, ( 1500.0, 34000.0 ),
                              lambda e, n, k: open_ground( world, e, n, k, 50.0, 0.2 ), 200.0 ):
        k = World.k_at( e, n )
        _, uphill = slope_at( world, e, n, k )
        along = uphill + math.pi / 2 + rng.uniform( -0.4, 0.4 )
        for j in range( rng.integers( 5, 12 ) ):
            p = np.array( ( e, n ) ) + np.array( ( math.cos( along ), math.sin( along ) ) ) * j * 6.5 * k
            if open_ground( world, p[0], p[1], k, 1.2, 0.35 ):
                world.cypress( p[0], p[1], rng.uniform( 13, 20 ), rng, k )
                count += 1
    for e, n in sample_sites( world, rng, 26, ( 1500.0, 34000.0 ),
                              lambda e, n, k: open_ground( world, e, n, k, 20.0, 0.3 ), 150.0 ):
        k = World.k_at( e, n )
        for _ in range( rng.integers( 3, 8 ) ):
            p = np.array( ( e, n ) ) + rng.normal( 0, 3.5, 2 ) * k
            if world.free( p[0], p[1], 1.2 * k ):
                world.cypress( p[0], p[1], rng.uniform( 12, 20 ), rng, k )
                count += 1
    return count


def build( ground=None ):
    """ Every prop, in a World. """
    t0 = time.time()
    world = World( ground or Ground() )
    hill_town( world )
    villa( world )
    village( world )
    n_farms = farms( world )
    n_chapels = chapels( world )
    n_lone = lone_cypresses( world )
    trees = np.array( [ t[6] for t in world.trees ] )
    print( f"props: {len( world.buildings )} buildings and walls, {n_farms} farms, {n_chapels} chapels, "
           f"{int( ( trees == TREE_CYPRESS ).sum() )} cypresses ({n_lone} in the fields), "
           f"{int( ( trees == TREE_PINE ).sum() )} pines, {len( world.yards )} yards, "
           f"{sum( len( line ) for _, line in world.roads )} road points, {world.mesh.count()} triangles "
           f"in {time.time() - t0:.1f} s" )
    return world


def write( out_dir=V.MODEL_DIR, resource_dir=V.MODEL_RESOURCE, world=None ):
    """ The textures, materials and model. Returns the triangle count. """
    world = world or build()
    write_textures( world.atlas )
    world.mesh.write( out_dir, resource_dir, NAME )
    return world.mesh.count()


def main():
    parser = argparse.ArgumentParser( description=__doc__.split( "\n\n" )[0] )
    parser.add_argument( "--textures-only", action="store_true" )
    args = parser.parse_args()
    if args.textures_only:
        write_textures( Atlas() )
        return
    print( f"{NAME}: {write()} triangles" )


if __name__ == "__main__":
    main()
