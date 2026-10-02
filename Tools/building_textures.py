"""
Materials for Ridgeback's buildings, drawn from scratch with numpy and PIL like the ground's (Tools/terrain_textures.py,
whose tileable noise this borrows): lime render, whitewash, concrete, floorboards, quarry tiles, clay roof tiles,
painted wood, board shutters, brick and galvanised metal. Every map tiles.

Belltower (Tools/belltower_map.py) adds dressed stone, rubble walls, granite setts, flagstones, window glass, striped
awning canvas, sandbags, corrugated sheet, a roller shutter, painted iron, verdigris copper, raw planks, still water and a
clock face, more render colours, and the ground (gravel, soil, grass and rock) made from the terrain's own maps.

    python Tools/building_textures.py [name ...] [--sheet <png>]

- Writes Assets/materials/buildings/<texture>_normal.png and _rough.png, then a _color.png and a .vmat
  (shaders/complex.shader) for each of the texture's paints (PAINTS): the render comes in the walls' ochre and a pale
  trim colour, the painted wood in white, brown and green.
- A texture repeats every TILE_UNITS[texture] units. The buildings' UVs (Tools/ridgeback_buildings.py) are world-scale,
  so a brick is a brick's size on any wall.
- Normals are OpenGL style (green up the picture), as s&box's model shader reads them. Pictures run down the wall:
  row 0 is the top, so rain streaks and roof tile edges point the right way.
- Cavities (mortar, board gaps, the shadow under a roof tile's edge) are darkened in the colour itself, since the
  model shader gets no ambient occlusion map from these.
- The clock face is a decal (DECALS): drawn once over the picture and mapped whole onto its polygon.
- glass_clear is the Town House's see-through window glass, a decal mapped once across each pane, on glass.shader
  instead (SEE_THROUGH). Belltower's "glass" is opaque, for shut windows nobody sees into.
- --sheet writes each paint tiled 2x2 and lit from the top left, beside its height map, for checking.
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import terrain_textures as T

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/buildings"
RESOURCE_DIR = "materials/buildings"
DEFAULT_AO = "materials/default/default_ao.tga"

# Units (inches) each texture covers before it repeats.
TILE_UNITS = {
    "render": 256.0,
    "whitewash": 128.0,
    "concrete": 128.0,
    "floorboards": 128.0,
    "quarry_tiles": 64.0,
    "roof_tiles": 128.0,
    "painted_wood": 64.0,
    "shutter_boards": 64.0,
    "brick": 64.0,
    "metal": 32.0,
    # Belltower's
    "ashlar": 128.0,
    "rubble": 128.0,
    "setts": 64.0,
    "flagstones": 192.0,
    "glass": 64.0,
    "canvas": 64.0,
    "sandbags": 48.0,
    "corrugated": 64.0,
    "roller": 64.0,
    "iron": 32.0,
    "copper": 64.0,
    "planks": 96.0,
    "water": 128.0,
    "clock": 64.0,
    "gravel": 64.0,
    "soil": 128.0,
    "lawn": 96.0,
    "rock": 256.0,
    "hedge": 48.0,
    "slate": 96.0,
    # The Town House's window panes (a decal: one pane's size)
    "glass_clear": 16.0,
}


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

def unit( a ):
    return ( a - a.mean() ) / a.std()


def stretched( rng, n, beta, fmin, fmax, sigma ):
    """ Tileable noise blurred more one way than the other (sigma = rows, columns): grain, streaks. """
    return unit( ndimage.gaussian_filter( T.spectral( rng, n, beta, fmin, fmax ), sigma, mode="wrap" ) )


def paint( rgb, lum ):
    """ An sRGB colour lit by lum (linear), as an sRGB picture. """
    linear = T.srgb_to_linear( np.asarray( rgb, float ) )
    return T.linear_to_srgb( linear[None, None, :] * lum[..., None] )


def mix( a, b, t ):
    return a + ( b - a ) * t[..., None]


def per_cell( values, index ):
    """ values[index], broadcasting a colour or number per cell out to the picture. """
    return np.asarray( values )[index]


class Mask:
    """ Strokes and dots drawn at ss times the size on a canvas three tiles across, folded back into one tile so they
    wrap at the edges. Coordinates are tile pixels and may run a tile past either edge. """

    def __init__( self, n, ss=2 ):
        self.n, self.ss = n, ss
        self.image = Image.new( "L", ( 3 * n * ss, 3 * n * ss ), 0 )
        self.draw = ImageDraw.Draw( self.image )

    def _p( self, x, y ):
        return ( ( x + self.n ) * self.ss, ( y + self.n ) * self.ss )

    def line( self, points, width, value=1.0 ):
        self.draw.line( [ self._p( x, y ) for x, y in points ], fill=int( value * 255 ),
                        width=max( 1, int( round( width * self.ss ) ) ), joint="curve" )

    def ellipse( self, x, y, rx, ry, value=1.0 ):
        ( x0, y0 ), ( x1, y1 ) = self._p( x - rx, y - ry ), self._p( x + rx, y + ry )
        self.draw.ellipse( ( x0, y0, x1, y1 ), fill=int( value * 255 ) )

    def result( self ):
        n, s = self.n, self.ss
        a = np.asarray( self.image, float ) / 255.0
        folded = a.reshape( 3, n * s, 3, n * s ).max( axis=( 0, 2 ) )
        return folded.reshape( n, s, n, s ).mean( axis=( 1, 3 ) )


def cracks( rng, n, count, length, width, branch=0.35 ):
    """ Hairline cracks: wandering lines that now and then fork. """
    mask = Mask( n )
    todo = [ ( rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0, 2 * math.pi ), rng.uniform( *length ), width )
             for _ in range( count ) ]
    while todo:
        x, y, angle, remaining, w = todo.pop()
        points = [ ( x, y ) ]
        while remaining > 0:
            angle += rng.normal( 0, 0.18 )
            step = min( remaining, rng.uniform( 2.0, 5.0 ) )
            x, y = x + math.cos( angle ) * step, y + math.sin( angle ) * step
            points.append( ( x, y ) )
            remaining -= step
            if rng.random() < branch * step / 60.0 and w > 0.6:
                todo.append( ( x, y, angle + rng.choice( [ -1, 1 ] ) * rng.uniform( 0.5, 1.1 ), remaining * rng.uniform( 0.3, 0.6 ), w * 0.7 ) )
        mask.line( points, w )
    return mask.result()


def rounded_edges( distance, width ):
    """ 0 at an edge rising to 1 width px in: the bevel on a board, tile or brick. """
    return T.smoothstep( 0.0, width, distance )


def gl_normals( height, strength ):
    """ OpenGL-style tangent normals (green up the picture) from a height field. """
    normal = T.normal_map( height, strength )
    normal[..., 1] *= -1.0
    return normal


# ---------------------------------------------------------------------------------------------------------------------
# Textures. Each returns ( { paint: colour }, roughness, height, normal strength ); colours are sRGB 0..255.

def render( rng, n ):
    """ Lime render over the walls: sandy, trowelled, blotched by the weather, streaked where rain runs down, with the odd
    hairline crack and air hole. 4 px to the unit. """
    sand = T.spectral( rng, n, 0.8, n / 5, None )
    fine = T.spectral( rng, n, 2.0, 40, 300 )
    trowel = T.spectral( rng, n, 3.0, 3, 40 )
    blotch = T.spectral( rng, n, 3.2, 1, 10 )
    mottle = T.spectral( rng, n, 2.4, 6, 60 )
    runs = stretched( rng, n, 1.8, 2, 120, ( 90, 3.0 ) )
    streaks = T.smoothstep( 0.6, 2.6, runs ) * T.smoothstep( -0.9, 0.9, T.spectral( rng, n, 3.0, 1, 6 ) )
    holes = T.smoothstep( 2.6, 3.4, -T.spectral( rng, n, 0.4, n / 8, None ) )
    crack = cracks( rng, n, 6, ( 60, 240 ), 1.1 )

    height = 0.5 + 0.10 * trowel + 0.035 * fine + 0.03 * sand - 0.25 * holes - 0.3 * crack
    lum = ( 1.0 + 0.035 * blotch + 0.025 * mottle + 0.025 * sand - 0.08 * streaks - 0.4 * crack - 0.3 * holes )
    grime = 0.14 * T.smoothstep( 0.0, -2.5, blotch ) + 0.18 * streaks
    rough = np.clip( 0.9 + 0.03 * sand - 0.04 * streaks, 0.0, 1.0 )

    dirt = paint( ( 118, 114, 98 ), lum )
    colours = {
        "render_ochre": mix( paint( ( 204, 178, 134 ), lum ), dirt, grime ),
        "render_pale": mix( paint( ( 222, 215, 196 ), lum ), dirt, grime * 0.8 ),
        # Belltower's houses, each street's own colour to call by.
        "render_rose": mix( paint( ( 198, 152, 138 ), lum ), dirt, grime ),
        "render_blue": mix( paint( ( 160, 178, 188 ), lum ), dirt, grime ),
        "render_cream": mix( paint( ( 228, 212, 170 ), lum ), dirt, grime ),
        "render_sage": mix( paint( ( 170, 182, 150 ), lum ), dirt, grime ),
        "render_terracotta": mix( paint( ( 192, 124, 90 ), lum ), dirt, grime ),
        # Belltower's flowerpots: unglazed terracotta, its fine grain the render's.
        "clay_pot": mix( paint( ( 170, 96, 64 ), lum ), dirt, grime * 0.6 ),
    }
    return colours, rough, height, 2.5


def whitewash( rng, n ):
    """ Limewashed plaster inside: paler and smoother than the render, with scuffs and faded patches. """
    sand = T.spectral( rng, n, 0.8, n / 5, None )
    trowel = T.spectral( rng, n, 3.0, 2, 30 )
    blotch = T.spectral( rng, n, 3.0, 1, 12 )
    brush = stretched( rng, n, 1.5, 4, 200, ( 0.8, 9.0 ) )
    scuffs = T.smoothstep( 0.8, 2.8, T.spectral( rng, n, 3.0, 2, 20 ) ) * 0.18
    crack = cracks( rng, n, 3, ( 40, 140 ), 0.9 )

    height = 0.5 + 0.08 * trowel + 0.02 * sand + 0.012 * brush - 0.3 * crack
    lum = 1.0 + 0.035 * blotch + 0.015 * sand + 0.012 * brush - 0.12 * scuffs - 0.35 * crack
    colours = { "whitewash": mix( paint( ( 214, 211, 199 ), lum ), paint( ( 150, 144, 130 ), lum ), scuffs ) }
    rough = np.clip( 0.86 + 0.03 * sand, 0.0, 1.0 )
    return colours, rough, height, 2.0


def concrete( rng, n ):
    """ Cast concrete for the plinth, steps and sills: blotched, with sand and grit showing and small pores. """
    fine = T.spectral( rng, n, 1.0, n / 6, None )
    swell = T.spectral( rng, n, 2.6, 4, 60 )
    blotch = T.spectral( rng, n, 3.0, 1, 12 )
    grit = T.spectral( rng, n, 0.6, n / 6, None )
    light = T.smoothstep( 2.0, 2.8, grit )
    dark = T.smoothstep( 2.1, 2.9, -grit )
    pores = T.smoothstep( 2.5, 3.2, -T.spectral( rng, n, 0.5, n / 8, None ) )
    crack = cracks( rng, n, 3, ( 50, 160 ), 1.0 )

    height = 0.5 + 0.06 * swell + 0.03 * fine - 0.35 * pores - 0.3 * crack
    lum = 1.0 + 0.07 * blotch + 0.03 * fine + 0.12 * light - 0.15 * dark - 0.4 * pores - 0.4 * crack
    colours = { "concrete": paint( ( 150, 147, 140 ), lum ) }
    rough = np.clip( 0.86 + 0.04 * fine - 0.05 * light, 0.0, 1.0 )
    return colours, rough, height, 2.5


def floorboards( rng, n ):
    """ Old pine boards along the picture (u), 8 units wide and 4 to 11 feet long, butted end to end, nailed at the ends.
    8 px to the unit. """
    rows = 16
    width = n // rows
    y, x = np.mgrid[0:n, 0:n]
    row = y // width
    across = ( y % width + 0.5 ) / width

    board = np.zeros( ( n, n ), int )
    along = np.zeros( ( n, n ) )               # px from the board's start
    length = np.ones( ( n, n ) )
    count = 0
    for r in range( rows ):
        cuts = [ 0 ]
        while cuts[-1] < n:
            cuts.append( cuts[-1] + int( rng.uniform( 380, 900 ) ) )
        cuts[-1] = n
        if cuts[-1] - cuts[-2] < 250 and len( cuts ) > 2:
            cuts.pop( -2 )
        offset = int( rng.integers( 0, n ) )
        cuts = np.array( cuts )
        band = row == r
        xs = ( x[band] - offset ) % n
        k = np.searchsorted( cuts, xs, side="right" ) - 1
        board[band] = count + k
        along[band] = xs - cuts[k]
        length[band] = ( cuts[k + 1] - cuts[k] )
        count += len( cuts ) - 1

    palette = np.array( [ ( 150, 104, 66 ), ( 136, 94, 60 ), ( 160, 116, 76 ), ( 124, 88, 60 ), ( 142, 108, 80 ),
                          ( 118, 92, 72 ) ], float )
    tone = palette[rng.integers( 0, len( palette ), count )] * rng.uniform( 0.92, 1.06, ( count, 1 ) )
    tone = tone.mean( 0 ) + ( tone - tone.mean( 0 ) ) * 0.6
    board_rough = rng.uniform( 0.58, 0.76, count )

    grains = [ stretched( rng, n, 2.0, 3, 300, ( 0.9, 45.0 ) ) for _ in range( 4 ) ]
    grain = np.choose( board % 4, grains )
    rings = np.sin( 2 * math.pi * ( across * rng.uniform( 2.5, 4.5 ) + 0.35 * grain ) )
    fine = T.spectral( rng, n, 1.2, n / 6, None )
    wear = T.spectral( rng, n, 3.0, 2, 16 )

    # Knots: dark ellipses with rings round them, pulling the grain.
    knots = Mask( n )
    for _ in range( 14 ):
        kx, ky = rng.uniform( 0, n ), ( rng.integers( 0, rows ) + rng.uniform( 0.25, 0.75 ) ) * width
        rx = rng.uniform( 5, 11 )
        knots.ellipse( kx, ky, rx, rx * rng.uniform( 0.4, 0.6 ) )
    knot = ndimage.gaussian_filter( knots.result(), 1.2, mode="wrap" )

    edge_across = np.minimum( across, 1.0 - across ) * width
    edge_along = np.minimum( along, length - along )
    edge = np.minimum( edge_across, edge_along )
    nails = np.zeros( ( n, n ) )
    for spot in ( 14.0, ):
        near_end = np.minimum( np.abs( along - spot ), np.abs( length - along - spot ) )
        for side in ( 0.28, 0.72 ):
            nails = np.maximum( nails, T.smoothstep( 2.2, 1.2, np.hypot( near_end, ( across - side ) * width ) ) )

    bevel = rounded_edges( edge, 2.5 )
    gap = 1.0 - rounded_edges( edge, 1.0 )
    height = ( 0.55 + 0.035 * grain + 0.02 * rings + 0.01 * fine - 0.08 * knot ) * bevel + 0.05
    lum = ( 1.0 + 0.10 * grain + 0.05 * rings + 0.03 * fine + 0.05 * wear - 0.45 * knot - 0.55 * nails )
    lum *= 0.35 + 0.65 * bevel ** 0.5
    colour = T.linear_to_srgb( T.srgb_to_linear( tone[board] ) * lum[..., None] )
    rough = np.clip( board_rough[board] + 0.04 * grain - 0.04 * wear, 0.0, 1.0 ) * ( 1 - gap ) + gap
    return { "floorboards": colour }, rough, height, 4.0


def quarry_tiles( rng, n ):
    """ Terracotta quarry tiles, 8 units square, in a grey lime grout, some worn paler. 8 px to the unit. """
    tiles = 8
    size = n // tiles
    y, x = np.mgrid[0:n, 0:n]
    tx, ty = x // size, y // size
    u, v = x % size + 0.5, y % size + 0.5
    edge = np.minimum( np.minimum( u, size - u ), np.minimum( v, size - v ) )
    tile = ty * tiles + tx

    palette = np.array( [ ( 166, 84, 56 ), ( 150, 72, 50 ), ( 178, 98, 64 ), ( 140, 78, 60 ), ( 158, 90, 66 ) ], float )
    tone = palette[rng.integers( 0, len( palette ), tiles * tiles )] * rng.uniform( 0.9, 1.05, ( tiles * tiles, 1 ) )
    tone = tone.mean( 0 ) + ( tone - tone.mean( 0 ) ) * 0.55
    worn = rng.uniform( 0, 1, tiles * tiles ) < 0.2
    mottle = T.spectral( rng, n, 2.2, 8, 90 )
    fine = T.spectral( rng, n, 1.0, n / 6, None )
    scratches = cracks( rng, n, 10, ( 10, 40 ), 0.6, branch=0 )

    grout_half = 1.6
    inside = T.smoothstep( grout_half - 0.5, grout_half + 0.5, edge )
    dome = rounded_edges( edge - grout_half, 4.0 )
    centre = 1.0 - np.clip( np.hypot( u - size / 2, v - size / 2 ) / ( size * 0.6 ), 0, 1 )
    wear = np.where( worn[tile], centre * 0.25, 0.0 )

    height = 0.15 + inside * ( 0.45 + 0.25 * dome + 0.02 * mottle + 0.01 * fine - 0.06 * scratches )
    lum = ( 1.0 + 0.06 * mottle + 0.03 * fine + wear - 0.2 * scratches ) * ( 0.7 + 0.3 * dome )
    tile_colour = T.linear_to_srgb( T.srgb_to_linear( tone[tile] ) * lum[..., None] )
    grout = paint( ( 128, 120, 106 ), 1.0 + 0.05 * fine )
    colour = mix( grout * 0.8, tile_colour, inside )
    rough = np.clip( ( 0.62 + 0.05 * mottle - wear * 0.4 ) * inside + 0.95 * ( 1 - inside ), 0.0, 1.0 )
    return { "quarry_tiles": colour }, rough, height, 4.0


def roof_tiles( rng, n ):
    """ Clay tiles, 8 units to a course and 8 wide, each course broken joint with the one below. Each tile rises from
    its head (hidden under the course above) to its tail, which stands proud of the course below: the picture's rows run
    down the roof, so a course's edge is at its bottom. Weathered dark with lichen in places. 8 px to the unit. """
    course = n // 16
    y, x = np.mgrid[0:n, 0:n]
    row = y // course
    t = ( y % course + 0.5 ) / course                                # 0 at the head, 1 at the tail
    shifted = ( x + ( row % 2 ) * ( course // 2 ) ) % n
    col = shifted // course
    s = ( shifted % course + 0.5 ) / course
    tile = row * 16 + col

    palette = np.array( [ ( 146, 72, 50 ), ( 136, 66, 48 ), ( 156, 84, 58 ), ( 124, 62, 48 ), ( 142, 78, 60 ),
                          ( 116, 68, 56 ) ], float )
    count = 16 * 16
    tone = palette[rng.integers( 0, len( palette ), count )] * rng.uniform( 0.88, 1.06, ( count, 1 ) )
    tone = tone.mean( 0 ) + ( tone - tone.mean( 0 ) ) * 0.7
    dark = rng.uniform( 0, 1, count ) < 0.06
    tone[dark] *= 0.8

    side_gap = np.minimum( s, 1 - s ) * course
    camber = np.sin( math.pi * np.clip( s, 0, 1 ) )
    lip = rounded_edges( ( 1 - t ) * course, 2.0 )                  # the tail's rounded edge
    height = ( 0.18 + 0.6 * t + 0.08 * camber ) * lip * rounded_edges( side_gap, 1.3 )
    height = ndimage.gaussian_filter( height, 0.6, mode="wrap" )

    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    mottle = T.spectral( rng, n, 2.0, 12, 120 )
    fine = T.spectral( rng, n, 1.0, n / 6, None )
    lichen_zone = T.smoothstep( 0.6, 1.6, T.spectral( rng, n, 3.0, 2, 12 ) )
    lichen = T.smoothstep( 0.2, 1.6, T.spectral( rng, n, 2.2, 20, 200 ) ) * lichen_zone * 0.6

    shadow = 0.45 + 0.55 * T.smoothstep( 0.0, 0.4, t )             # under the tail of the course above
    lum = ( 1.0 + 0.08 * blotch + 0.05 * mottle + 0.03 * fine ) * shadow * ( 0.7 + 0.3 * rounded_edges( side_gap, 1.5 ) )
    clay = T.linear_to_srgb( T.srgb_to_linear( tone[tile] ) * lum[..., None] )
    weather = T.smoothstep( -0.5, -2.0, blotch ) * 0.35
    clay = mix( clay, paint( ( 78, 70, 62 ), lum ), weather )
    colour = mix( clay, paint( ( 170, 166, 128 ), lum ), lichen * 0.8 )
    rough = np.clip( 0.72 + 0.05 * mottle + 0.1 * lichen, 0.0, 1.0 )
    return { "roof_tiles": colour }, rough, height, 5.0


def wood_grain( rng, n ):
    """ Grain running down the picture. """
    return stretched( rng, n, 2.0, 3, 256, ( 30.0, 0.8 ) )


PAINT_COLOURS = { "white": ( 232, 228, 216 ), "brown": ( 88, 60, 42 ), "green": ( 66, 96, 70 ),
                  "blue": ( 64, 94, 124 ), "red": ( 124, 50, 42 ) }


def painted( rng, n, boards ):
    """ Painted wood with the grain showing through, the paint worn back to grey timber in patches. boards splits it
    into 8-unit boards with gaps between (shutters). 8 px to the unit. """
    grain = wood_grain( rng, n )
    fine = T.spectral( rng, n, 1.2, n / 6, None )
    wear = T.spectral( rng, n, 2.6, 3, 40 )
    flakes = T.smoothstep( 2.9, 3.3, ndimage.gaussian_filter( T.spectral( rng, n, 1.4, 20, None ), 0.8, mode="wrap" ) * 1.4 )
    bare = np.clip( T.smoothstep( 2.1, 2.5, wear + 0.4 * grain ) + flakes, 0.0, 1.0 )
    y, x = np.mgrid[0:n, 0:n]

    height = 0.6 + 0.015 * grain + 0.01 * fine - bare * ( 0.06 - 0.05 * grain )
    lum_paint = 1.0 + 0.025 * fine + 0.035 * grain
    lum_wood = 1.0 + 0.16 * grain + 0.05 * fine
    if boards:
        width = n // 8
        u = x % width + 0.5
        edge = np.minimum( u, width - u )
        bevel = rounded_edges( edge, 2.0 )
        board = x // width
        shade = rng.uniform( 0.94, 1.04, 8 )[board]
        height = height * bevel + 0.02
        lum_paint = lum_paint * shade * ( 0.35 + 0.65 * bevel )
        lum_wood = lum_wood * shade * ( 0.35 + 0.65 * bevel )

    wood = paint( ( 118, 104, 88 ), lum_wood )
    colours = { name: mix( paint( rgb, lum_paint ), wood, bare ) for name, rgb in PAINT_COLOURS.items() }
    rough = np.clip( 0.5 + 0.04 * fine + 0.35 * bare, 0.0, 1.0 )
    return colours, rough, height, 3.0


def painted_wood( rng, n ):
    colours, rough, height, strength = painted( rng, n, False )
    return { f"trim_{k}": v for k, v in colours.items() }, rough, height, strength


def shutter_boards( rng, n ):
    colours, rough, height, strength = painted( rng, n, True )
    return { f"shutter_{k}": v for k, v in colours.items() if k != "white" }, rough, height, strength


def brick( rng, n ):
    """ Soft red bricks, 8 units by 2 2/3 (three courses to 8 units) with 3/8 joints, in stretcher bond. """
    courses = 24
    per_row = 8
    course = n / courses
    length = n / per_row
    y, x = np.mgrid[0:n, 0:n] + 0.5
    row = ( y // course ).astype( int )
    v = y - row * course
    shifted = ( x + ( row % 2 ) * length / 2 ) % n
    col = ( shifted // length ).astype( int )
    u = shifted - col * length
    joint = 1.5
    edge = np.minimum( np.minimum( u, length - u ), np.minimum( v, course - v ) )
    brick_id = row * per_row + col

    palette = np.array( [ ( 150, 66, 46 ), ( 164, 80, 56 ), ( 128, 58, 44 ), ( 172, 96, 66 ), ( 116, 62, 50 ),
                          ( 140, 74, 58 ) ], float )
    count = courses * per_row
    tone = palette[rng.integers( 0, len( palette ), count )] * rng.uniform( 0.85, 1.1, ( count, 1 ) )
    chip = ndimage.gaussian_filter( T.spectral( rng, n, 2.0, 12, 120 ), 0.7, mode="wrap" )
    inside = T.smoothstep( joint - 0.6, joint + 0.6, edge + 0.45 * chip )
    face = rounded_edges( edge - joint, 2.0 )
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    mottle = T.spectral( rng, n, 2.2, 6, 80 )
    soot = T.smoothstep( 0.0, -2.2, T.spectral( rng, n, 3.4, 1, 5 ) ) * 0.6

    height = 0.15 + inside * ( 0.45 + 0.2 * face + 0.03 * fine + 0.02 * mottle )
    lum = ( 1.0 + 0.06 * mottle + 0.04 * fine ) * ( 0.75 + 0.25 * face )
    bricks = T.linear_to_srgb( T.srgb_to_linear( tone[brick_id] ) * lum[..., None] )
    mortar = paint( ( 150, 142, 128 ), 0.8 + 0.05 * fine )
    colour = mix( mix( mortar, bricks, inside ), paint( ( 60, 54, 50 ), lum ), soot * 0.45 )
    rough = np.clip( 0.8 * inside + 0.93 * ( 1 - inside ) + 0.03 * fine, 0.0, 1.0 )
    return { "brick": colour }, rough, height, 4.0


def metal( rng, n ):
    """ Galvanised sheet: grey, spangled, dulled in patches. """
    spangle = T.spectral( rng, n, 1.8, 8, 64 )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    dull = T.smoothstep( -0.2, 1.4, blotch )
    lum = 1.0 + 0.07 * spangle + 0.03 * fine - 0.12 * dull
    colours = { "metal": paint( ( 150, 153, 156 ), lum ) }
    rough = np.clip( 0.38 + 0.06 * spangle + 0.25 * dull, 0.0, 1.0 )
    height = 0.5 + 0.01 * fine
    return colours, rough, height, 1.0


# ---------------------------------------------------------------------------------------------------------------------
# Belltower's

def coursed( rng, n, rows_px, lengths_px ):
    """ Blocks laid in courses: rows of random heights (rows_px, a range), each cut into random lengths (lengths_px), every
    course starting at its own offset. Rows and cuts are stretched a little to fit the tile, so it wraps. Returns per px
    the block, u and v (px from its corner), its length and its row's height; then the row and the number of blocks. """
    heights = []
    while sum( heights ) < n:
        heights.append( rng.uniform( *rows_px ) )
    heights = np.array( heights ) * n / sum( heights )
    edges = np.concatenate( ( [ 0.0 ], np.cumsum( heights ) ) )
    y, x = np.mgrid[0:n, 0:n] + 0.5
    row = np.clip( np.searchsorted( edges, y, side="right" ) - 1, 0, len( heights ) - 1 )
    v = y - edges[row]
    block = np.zeros( ( n, n ), int )
    u = np.zeros( ( n, n ) )
    length = np.ones( ( n, n ) )
    count = 0
    for r in range( len( heights ) ):
        cuts = [ 0.0 ]
        while cuts[-1] < n:
            cuts.append( cuts[-1] + rng.uniform( *lengths_px ) )
        cuts = np.array( cuts ) * n / cuts[-1]
        band = row == r
        xs = ( x[band] - rng.uniform( 0, n ) ) % n
        k = np.clip( np.searchsorted( cuts, xs, side="right" ) - 1, 0, len( cuts ) - 2 )
        block[band] = count + k
        u[band] = xs - cuts[k]
        length[band] = cuts[k + 1] - cuts[k]
        count += len( cuts ) - 1
    return block, u, v, length, heights[row], row, count


def tones( rng, palette, count, spread, contrast=1.0 ):
    """ count colours from palette (sRGB), each shaded by up to spread, pulled towards their mean by contrast. """
    tone = np.array( palette, float )[rng.integers( 0, len( palette ), count )]
    tone = tone * rng.uniform( 1 - spread, 1 + spread, ( count, 1 ) )
    return tone.mean( 0 ) + ( tone - tone.mean( 0 ) ) * contrast


def shade( tone, lum ):
    """ Per-px sRGB colours lit by lum (linear). """
    return T.linear_to_srgb( T.srgb_to_linear( tone ) * lum[..., None] )


ASHLAR = {
    "ashlar": [ ( 200, 188, 162 ), ( 186, 174, 150 ), ( 210, 200, 176 ), ( 178, 166, 144 ), ( 194, 178, 150 ) ],
    "ashlar_grey": [ ( 152, 152, 148 ), ( 140, 141, 139 ), ( 162, 160, 154 ), ( 130, 132, 132 ), ( 146, 142, 136 ) ],
}


def ashlar( rng, n ):
    """ Dressed stone in courses 10 to 16 units high, blocks 16 to 40 long, in thin lime joints: each block its own
    shade, its face a little out of true, rain streaks down the wall and lichen in places. Limestone for the church and
    the town hall, and the same blocks in granite's greys. 8 px to the unit. """
    ppu = n / TILE_UNITS["ashlar"]
    block, u, v, length, course, row, count = coursed( rng, n, ( 10 * ppu, 16 * ppu ), ( 16 * ppu, 40 * ppu ) )
    edge = np.minimum( np.minimum( u, length - u ), np.minimum( v, course - v ) )
    chip = ndimage.gaussian_filter( T.spectral( rng, n, 2.0, 16, 160 ), 0.8, mode="wrap" )
    joint = 0.3 * ppu
    inside = T.smoothstep( joint - 0.7, joint + 0.7, edge + 0.8 * chip )
    face = rounded_edges( edge - joint, 1.0 * ppu )
    tilt = ( rng.uniform( -1, 1, count )[block] * ( u / length - 0.5 )
             + rng.uniform( -1, 1, count )[block] * ( v / course - 0.5 ) )
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    tooled = stretched( rng, n, 1.2, 20, n / 3, ( 0.5, 2.5 ) )
    blotch = T.spectral( rng, n, 3.0, 1, 10 )
    runs = stretched( rng, n, 1.8, 2, 120, ( 70, 2.5 ) )
    streaks = T.smoothstep( 0.8, 2.6, runs ) * T.smoothstep( -0.5, 1.0, T.spectral( rng, n, 3.0, 1, 6 ) )
    lichen = ( T.smoothstep( 1.0, 2.2, T.spectral( rng, n, 2.0, 8, 120 ) )
               * T.smoothstep( 0.4, 1.4, T.spectral( rng, n, 3.0, 2, 10 ) ) )

    height = 0.2 + inside * ( 0.55 + 0.12 * face + 0.04 * tilt + 0.02 * fine + 0.01 * tooled )
    lum = ( 1.0 + 0.04 * blotch + 0.03 * fine + 0.02 * tooled - 0.12 * streaks ) * ( 0.78 + 0.22 * face )
    mortar = paint( ( 170, 162, 146 ), 0.85 + 0.05 * fine )
    colours = {}
    for name, palette in ASHLAR.items():
        stone = shade( tones( rng, palette, count, 0.06, 0.8 )[block], lum )
        stone = mix( stone, paint( ( 92, 88, 80 ), lum ), streaks * 0.35 )
        stone = mix( stone, paint( ( 150, 152, 112 ), lum ), lichen * 0.5 )
        colours[name] = mix( mortar, stone, inside )
    rough = np.clip( 0.82 + 0.04 * fine - 0.04 * face + 0.1 * ( 1 - inside ), 0.0, 1.0 )
    return colours, rough, height, 4.0


def rubble( rng, n ):
    """ Random rubble walling: rough stones of every size, lying longer than they stand high, bedded in lime mortar
    weathered back between them. The garden walls, the terraces and the town wall. 4 px to the unit. """
    from scipy.spatial import cKDTree
    ppu = n / TILE_UNITS["rubble"]
    squash = 1.6                                         # stones this much longer than high
    spacing = 8.0 * ppu
    cols, rows = max( 2, round( n / spacing ) ), max( 2, round( n * squash / spacing ) )
    jj, ii = np.mgrid[0:rows, 0:cols]
    centres = np.stack( [ ( ii + rng.uniform( 0.15, 0.85, ii.shape ) ) * n / cols,
                          ( jj + rng.uniform( 0.15, 0.85, jj.shape ) ) * n / rows ], -1 ).reshape( -1, 2 )
    count = len( centres )
    grow = rng.uniform( 0.0, 0.45, count ) * spacing     # some stones crowd out their neighbours
    tiled = np.concatenate( [ centres + ( ox * n, oy * n ) for ox in ( -1, 0, 1 ) for oy in ( -1, 0, 1 ) ] )
    scale = np.array( ( 1.0, squash ) )
    tree = cKDTree( tiled * scale )
    y, x = np.mgrid[0:n, 0:n] + 0.5
    wander = 0.9 * ppu
    px = np.stack( [ ( x + T.spectral( rng, n, 2.5, 3, 30 ) * wander ).ravel(),
                     ( y + T.spectral( rng, n, 2.5, 3, 30 ) * wander ).ravel() ], -1 )
    dist, idx = tree.query( px * scale, k=8 )
    weighted = dist - grow[idx % count]
    order = np.argsort( weighted, axis=1 )
    d1 = np.take_along_axis( weighted, order[:, :1], 1 )[:, 0]
    d2 = np.take_along_axis( weighted, order[:, 1:2], 1 )[:, 0]
    stone = ( np.take_along_axis( idx, order[:, :1], 1 )[:, 0] % count ).reshape( n, n )
    border = ( ( d2 - d1 ) / 2 ).reshape( n, n )          # px (squashed) to the joint

    mortar_w = 0.7 * ppu * ( 1.0 + 0.4 * T.spectral( rng, n, 2.0, 8, 64 ) )
    inside = T.smoothstep( 0.0, 1.5, border - mortar_w )
    dome = rounded_edges( border - mortar_w, 2.5 * ppu )
    face = T.spectral( rng, n, 1.6, 20, n / 2 )
    fine = T.spectral( rng, n, 1.0, n / 4, None )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    lichen = ( T.smoothstep( 1.2, 2.2, T.spectral( rng, n, 2.0, 8, 100 ) )
               * T.smoothstep( 0.3, 1.3, T.spectral( rng, n, 3.0, 2, 10 ) ) )
    palette = [ ( 150, 144, 132 ), ( 128, 122, 112 ), ( 164, 150, 124 ), ( 140, 124, 104 ), ( 116, 112, 108 ),
                ( 170, 162, 146 ), ( 134, 110, 88 ) ]
    tone = tones( rng, palette, count, 0.08, 0.9 )

    height = 0.15 + inside * ( 0.4 + 0.35 * dome + 0.06 * face ) + 0.03 * fine
    lum = ( 1.0 + 0.06 * face + 0.04 * fine + 0.04 * blotch ) * ( 0.7 + 0.3 * dome )
    stones = shade( tone[stone], lum )
    mortar = paint( ( 158, 150, 134 ), 0.75 + 0.06 * fine )
    colour = mix( mix( mortar, stones, inside ), paint( ( 140, 146, 104 ), lum ), lichen * 0.5 )
    rough = np.clip( 0.85 + 0.05 * fine, 0.0, 1.0 )
    return { "rubble": colour }, rough, height, 5.0


def setts( rng, n ):
    """ Granite setts in courses 5 1/3 units wide, 6 to 10 long, their tops worn round and polished, with dark grit in
    the joints: the streets. 8 px to the unit. """
    ppu = n / TILE_UNITS["setts"]
    block, u, v, length, course, row, count = coursed( rng, n, ( 5.3 * ppu, 5.4 * ppu ), ( 6 * ppu, 10 * ppu ) )
    edge = np.minimum( np.minimum( u, length - u ), np.minimum( v, course - v ) )
    chip = ndimage.gaussian_filter( T.spectral( rng, n, 2.0, 24, 200 ), 0.7, mode="wrap" )
    joint = 0.45 * ppu
    inside = T.smoothstep( joint - 0.6, joint + 0.6, edge + 0.9 * chip )
    dome = rounded_edges( edge - joint, 1.8 * ppu )
    tilt = ( rng.uniform( -1, 1, count )[block] * ( u / length - 0.5 )
             + rng.uniform( -1, 1, count )[block] * ( v / course - 0.5 ) )
    grain = T.spectral( rng, n, 0.3, n / 4, None )
    dark_specks = T.smoothstep( 1.5, 2.2, grain )
    light_specks = T.smoothstep( 1.6, 2.4, -grain )
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    blotch = T.spectral( rng, n, 3.0, 1, 6 )
    palette = [ ( 124, 122, 120 ), ( 138, 134, 128 ), ( 108, 108, 110 ), ( 144, 126, 118 ), ( 116, 120, 128 ),
                ( 132, 128, 120 ) ]
    tone = tones( rng, palette, count, 0.07, 0.85 )

    height = 0.1 + inside * ( 0.5 + 0.3 * dome + 0.04 * tilt + 0.01 * fine )
    lum = ( 1.0 + 0.04 * fine + 0.05 * blotch - 0.35 * dark_specks + 0.25 * light_specks ) * ( 0.62 + 0.38 * dome )
    colour = mix( paint( ( 66, 60, 52 ), 0.9 + 0.1 * fine ), shade( tone[block], lum ), inside )
    rough = np.clip( ( 0.78 - 0.2 * dome ) * inside + 0.95 * ( 1 - inside ), 0.0, 1.0 )
    return { "setts": colour }, rough, height, 5.0


def flagstones( rng, n ):
    """ Sandstone flags for the square in random courses: rows 18 to 36 units wide, flags 20 to 48 long, each laid a
    touch out of level and worn, some cracked, with grit and moss in the joints. 5 1/3 px to the unit. """
    ppu = n / TILE_UNITS["flagstones"]
    block, u, v, length, course, row, count = coursed( rng, n, ( 18 * ppu, 36 * ppu ), ( 20 * ppu, 48 * ppu ) )
    edge = np.minimum( np.minimum( u, length - u ), np.minimum( v, course - v ) )
    chip = ndimage.gaussian_filter( T.spectral( rng, n, 2.0, 16, 200 ), 0.8, mode="wrap" )
    joint = 0.35 * ppu
    inside = T.smoothstep( joint - 0.6, joint + 0.6, edge + 0.8 * chip )
    face = rounded_edges( edge - joint, 0.8 * ppu )
    tilt = ( rng.uniform( -1, 1, count )[block] * ( u / length - 0.5 )
             + rng.uniform( -1, 1, count )[block] * ( v / course - 0.5 ) )
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    mottle = T.spectral( rng, n, 2.2, 6, 80 )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    crack = cracks( rng, n, 10, ( 40, 160 ), 1.0 )
    bedding = stretched( rng, n, 1.6, 4, 160, ( 1.0, 8.0 ) )         # the sandstone's bedding
    moss = T.smoothstep( 0.2, 1.5, T.spectral( rng, n, 2.4, 4, 40 ) )
    palette = [ ( 178, 160, 128 ), ( 160, 150, 132 ), ( 150, 128, 100 ), ( 190, 178, 150 ), ( 142, 136, 126 ),
                ( 170, 146, 116 ) ]
    tone = tones( rng, palette, count, 0.06, 0.75 )

    height = 0.15 + inside * ( 0.55 + 0.1 * face + 0.06 * tilt + 0.02 * mottle + 0.01 * fine - 0.25 * crack )
    lum = ( 1.0 + 0.05 * mottle + 0.03 * fine + 0.03 * bedding + 0.04 * blotch - 0.45 * crack ) * ( 0.8 + 0.2 * face )
    joints = mix( paint( ( 84, 76, 64 ), 0.9 + 0.1 * fine ), paint( ( 66, 78, 46 ), 0.9 + 0.1 * fine ), moss )
    colour = mix( joints, shade( tone[block], lum ), inside )
    rough = np.clip( 0.8 + 0.04 * fine + 0.1 * ( 1 - inside ), 0.0, 1.0 )
    return { "flagstones": colour }, rough, height, 3.5


def glass( rng, n ):
    """ Old window glass seen from outside: dark, a little wavy, grimy in blotches and streaked where rain ran. Opaque:
    it's for shut windows nobody sees into. """
    fine = T.spectral( rng, n, 1.5, 8, 200 )
    blotch = T.spectral( rng, n, 3.0, 1, 6 )
    runs = stretched( rng, n, 1.8, 2, 60, ( 40, 2.0 ) )
    grime = T.smoothstep( 0.6, 2.2, runs ) * 0.4 + T.smoothstep( 1.0, 2.5, blotch ) * 0.3
    lum = 1.0 + 0.05 * fine
    colour = mix( paint( ( 46, 56, 62 ), lum ), paint( ( 96, 92, 82 ), lum ), grime )
    rough = np.clip( 0.06 + 0.35 * grime + 0.02 * fine, 0.0, 1.0 )
    return { "glass": colour }, rough, 0.5 + 0.004 * fine, 1.0


def glass_clear( rng, n ):
    """ A clear window pane, drawn once across each pane (a decal: row 0 is its top) for the Town House's breakable
    windows. It's on glass.shader (SEE_THROUGH), which takes the colour as the light let through: nearly white, with float
    glass's faint green. The roughness says where it's dirty: the shader blurs what's behind by it, and with
    AlbedoAbsorption lets less through there and shows the dirt's own colour. Dirt lines the putty round the edge and
    gathers in the corners, dust settles along the bottom, and there are dried rain spots and faint wipe marks. Old
    glass is a little wavy across. """
    v, u = ( np.mgrid[0:n, 0:n] + 0.5 ) / n
    across = np.minimum( u, 1 - u )
    down = np.minimum( v, 1 - v )
    edge = np.minimum( across, down )
    corner = np.hypot( across, down )
    fine = T.spectral( rng, n, 1.6, 16, 256 )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )

    spots = Mask( n )
    for _ in range( 90 ):
        r = rng.uniform( 0.6, 2.2 )
        spots.ellipse( rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.7, 1.0 ), rng.uniform( 0.3, 0.8 ) )
    wipes = Mask( n )
    for _ in range( 5 ):
        cx, cy, radius = rng.uniform( 0.2, 0.8 ) * n, rng.uniform( 0.2, 0.8 ) * n, rng.uniform( 0.15, 0.4 ) * n
        start = rng.uniform( 0, 2 * math.pi )
        arc = [ ( cx + radius * math.cos( start + t ), cy + radius * math.sin( start + t ) )
                for t in np.linspace( 0, rng.uniform( 1.0, 2.5 ), 40 ) ]
        wipes.line( arc, rng.uniform( 6, 14 ), rng.uniform( 0.3, 0.7 ) )
    spot = ndimage.gaussian_filter( spots.result(), 0.8 )
    wipe = ndimage.gaussian_filter( wipes.result(), 3.0 )

    putty = T.smoothstep( 0.035, 0.004, edge + 0.004 * fine )
    corners = T.smoothstep( 0.13, 0.03, corner + 0.015 * blotch )
    dust = T.smoothstep( 0.78, 1.0, v ) * ( 0.55 + 0.25 * np.clip( blotch, -1.5, 1.5 ) )
    dirt = np.clip( 0.85 * putty + 0.6 * corners + 0.3 * dust + 0.35 * spot + 0.05 * T.smoothstep( 1.2, 2.8, blotch ), 0.0, 1.0 )

    clean = paint( ( 242, 248, 244 ), 1.0 + 0.004 * fine )
    colour = mix( clean, paint( ( 124, 116, 98 ), 1.0 + 0.1 * fine ), dirt )
    rough = np.clip( 0.025 + 0.6 * dirt + 0.08 * wipe + 0.006 * fine, 0.0, 1.0 )
    waves = stretched( rng, n, 2.2, 2, 24, ( 1.5, 40.0 ) )
    return { "glass_clear": colour }, rough, 0.5 + 0.02 * waves + 0.002 * fine, 0.35


CANVAS = { "canvas_red": ( 158, 46, 42 ), "canvas_green": ( 42, 100, 66 ), "canvas_blue": ( 40, 78, 132 ) }


def canvas( rng, n ):
    """ Awning canvas in 8-unit stripes down the slope (up the picture is up the awning), the weave showing, faded and
    dirtied by the weather. The plain paint is undyed duck. 8 px to the unit. """
    ppu = n / TILE_UNITS["canvas"]
    y, x = np.mgrid[0:n, 0:n] + 0.5
    s = ( x / ( 8 * ppu ) ) % 2.0
    band = np.clip( np.minimum( s, 1.0 - s ) * 8 * ppu + 0.5, 0.0, 1.0 )
    weave = 0.5 * ( stretched( rng, n, 0.6, n / 8, None, ( 0.4, 2.0 ) )
                    + stretched( rng, n, 0.6, n / 8, None, ( 2.0, 0.4 ) ) )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    fade = T.smoothstep( -1.0, 2.0, T.spectral( rng, n, 3.0, 1, 5 ) ) * 0.3
    dirt = T.smoothstep( 0.8, 2.4, stretched( rng, n, 1.8, 2, 100, ( 50, 3.0 ) ) ) * 0.3
    lum = 1.0 + 0.06 * weave + 0.04 * blotch
    cream = paint( ( 216, 206, 180 ), lum )
    grime = paint( ( 96, 88, 72 ), lum )
    colours = {}
    for name, rgb in CANVAS.items():
        dyed = mix( paint( rgb, lum ), cream, fade )
        colours[name] = mix( mix( cream, dyed, band ), grime, dirt )
    colours["canvas_plain"] = mix( paint( ( 186, 172, 138 ), lum ), grime, dirt )
    rough = np.clip( 0.9 + 0.03 * weave, 0.0, 1.0 )
    return colours, rough, 0.5 + 0.03 * weave, 1.5


def sandbags( rng, n ):
    """ Sandbags laid in bond, 24 units long and 8 high, plump and sagging, in faded khaki and olive hessian caked
    with dirt. 10 2/3 px to the unit. """
    rows, per_row = 6, 2
    h, length = n / rows, n / per_row
    y, x = np.mgrid[0:n, 0:n] + 0.5
    row = ( y // h ).astype( int )
    v = ( y - row * h ) / h
    shifted = ( x + rng.uniform( 0, length, rows )[row] ) % n
    col = ( shifted // length ).astype( int )
    uu = ( shifted - col * length ) / length
    bag = row * per_row + col
    count = rows * per_row
    squash = rng.uniform( 0.85, 1.0, count )[bag]
    bulge = ( np.clip( 1 - np.abs( 2 * uu - 1 ) ** 5, 0, 1 ) ** 0.5
              * np.clip( 1 - np.abs( 2 * v - 1 ) ** 2.2, 0, 1 ) ** 0.55 * squash )
    weave = 0.5 * ( stretched( rng, n, 0.6, n / 6, None, ( 0.4, 1.5 ) )
                    + stretched( rng, n, 0.6, n / 6, None, ( 1.5, 0.4 ) ) )
    creases = stretched( rng, n, 2.0, 8, 80, ( 2.0, 6.0 ) )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    dirt = T.smoothstep( 0.0, 2.2, T.spectral( rng, n, 1.8, 6, 80 ) ) * 0.3
    palette = [ ( 168, 150, 110 ), ( 128, 122, 84 ), ( 180, 162, 122 ), ( 150, 140, 108 ), ( 140, 128, 92 ) ]
    tone = tones( rng, palette, count, 0.05, 0.9 )

    height = 0.1 + 0.75 * bulge + 0.02 * weave + 0.03 * creases * bulge
    lum = ( 1.0 + 0.07 * weave + 0.04 * blotch + 0.05 * creases ) * ( 0.35 + 0.65 * bulge ** 0.5 )
    colour = mix( shade( tone[bag], lum ), paint( ( 92, 80, 62 ), lum ), dirt )
    rough = np.clip( 0.93 + 0.03 * weave, 0.0, 1.0 )
    return { "sandbags": colour }, rough, height, 6.0


def corrugated( rng, n ):
    """ Corrugated galvanised sheet, its ribs 2 2/3 units apart running up the picture (down a roof), rusting in
    patches, streaked below the rust. 8 px to the unit. """
    y, x = np.mgrid[0:n, 0:n] + 0.5
    phase = x / n * 24 * 2 * math.pi
    rust = 0.85 * T.smoothstep( 0.7, 2.0, T.blur( T.warp( rng, n, T.spectral( rng, n, 2.8, 2, 12 ), 20 ), 4.0 ) )
    streak = T.smoothstep( 0.8, 2.4, stretched( rng, n, 1.8, 2, 120, ( 60, 1.5 ) ) ) * 0.5
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    flake = T.spectral( rng, n, 1.5, 20, 200 )
    lum = 1.0 + 0.05 * fine
    galvanised = mix( paint( ( 150, 152, 150 ), lum ), paint( ( 110, 100, 88 ), lum ), streak )
    colour = mix( galvanised, paint( ( 118, 76, 50 ), 1.0 + 0.15 * flake ), rust )
    rough = np.clip( 0.4 + 0.45 * rust + 0.1 * streak, 0.0, 1.0 )
    return { "corrugated": colour }, rough, 0.5 + 0.4 * np.sin( phase ) + 0.01 * fine, 6.0


def roller( rng, n ):
    """ A shopfront's rolling shutter pulled down: slats 2 2/3 units high across the picture, painted, scuffed, the
    paint rusting through at the slats' edges. 8 px to the unit. """
    y, x = np.mgrid[0:n, 0:n] + 0.5
    t = ( y / n * 24 ) % 1.0
    profile = np.sin( math.pi * t ) ** 0.6
    lip = T.smoothstep( 0.12, 0.0, np.minimum( t, 1 - t ) )
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    scuffs = T.smoothstep( 1.2, 2.6, stretched( rng, n, 1.6, 4, 120, ( 1.0, 12.0 ) ) ) * 0.4
    rust = np.clip( lip * T.smoothstep( 0.4, 1.6, T.spectral( rng, n, 2.0, 4, 60 ) ) + scuffs * 0.3, 0.0, 1.0 )
    lum = ( 1.0 + 0.04 * fine + 0.05 * blotch ) * ( 0.6 + 0.4 * profile )
    brown = paint( ( 110, 70, 46 ), lum )
    colours = { "roller_grey": mix( paint( ( 128, 132, 134 ), lum ), brown, rust ),
                "roller_green": mix( paint( ( 70, 98, 82 ), lum ), brown, rust ) }
    rough = np.clip( 0.5 + 0.05 * fine + 0.3 * rust + 0.1 * scuffs, 0.0, 1.0 )
    return colours, rough, 0.3 + 0.4 * profile + 0.01 * fine, 3.0


def iron( rng, n ):
    """ Painted iron (railings, lamp posts, the balcony): gloss paint gone dull, chipped to rust here and there. """
    fine = T.spectral( rng, n, 1.2, n / 6, None )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    chips = T.smoothstep( 2.4, 2.9, ndimage.gaussian_filter( T.spectral( rng, n, 1.4, 16, None ), 0.7, mode="wrap" ) * 1.4 )
    lum = 1.0 + 0.04 * fine + 0.05 * blotch
    rust = paint( ( 104, 60, 38 ), lum )
    colours = { "iron_black": mix( paint( ( 36, 36, 36 ), lum ), rust, chips ),
                "iron_green": mix( paint( ( 38, 64, 48 ), lum ), rust, chips ) }
    rough = np.clip( 0.45 + 0.05 * fine + 0.1 * T.smoothstep( -1.0, 2.0, blotch ) + 0.4 * chips, 0.0, 1.0 )
    return colours, rough, 0.6 + 0.01 * fine - 0.08 * chips, 1.5


def copper( rng, n ):
    """ Copper sheet gone to verdigris on the tower's roof: pale blue-green, darker where rain runs off the standing
    seams (every 16 units, up the picture), the sheets lapped every 32, brown copper showing through in places.
    8 px to the unit. copper_brown is the same sheet as the houses' gutters and downpipes have it: copper's dark brown
    oxide, which the water running through them keeps from going green, with a little verdigris in the streaks. """
    ppu = n / TILE_UNITS["copper"]
    y, x = np.mgrid[0:n, 0:n] + 0.5
    bay = x / ( 16 * ppu )
    seam = T.smoothstep( 2.5, 0.8, np.abs( bay - np.round( bay ) ) * 16 * ppu )
    bays = int( round( n / ( 16 * ppu ) ) )
    lap = ( y / ( 32 * ppu ) + rng.uniform( 0, 1, bays )[np.floor( bay ).astype( int ) % bays] ) % 1.0
    cross = T.smoothstep( 1.2, 0.3, np.minimum( lap, 1 - lap ) * 32 * ppu )
    fine = T.spectral( rng, n, 1.2, n / 6, None )
    streak = T.smoothstep( 0.4, 2.2, stretched( rng, n, 1.8, 2, 120, ( 80, 2.0 ) ) )
    blotch = T.spectral( rng, n, 3.0, 1, 10 )
    bare = 0.6 * T.smoothstep( 1.6, 2.6, T.blur( T.warp( rng, n, T.spectral( rng, n, 2.8, 3, 16 ), 16 ), 3.0 ) )
    lum = 1.0 + 0.05 * fine + 0.06 * blotch - 0.12 * streak
    patina = mix( paint( ( 112, 170, 146 ), lum ), paint( ( 64, 104, 90 ), lum ), streak * 0.6 )
    colour = mix( patina, paint( ( 118, 78, 52 ), lum ), bare * 0.8 )
    brown = mix( mix( paint( ( 84, 56, 40 ), lum ), paint( ( 126, 84, 56 ), lum ), bare * 0.7 ),
                 paint( ( 80, 112, 94 ), lum ), streak * 0.35 )
    rough = np.clip( 0.7 + 0.05 * fine - 0.3 * bare, 0.0, 1.0 )
    return { "copper": colour, "copper_brown": brown }, rough, 0.4 + 0.45 * seam + 0.15 * cross + 0.01 * fine, 4.0


PLANKS = {
    "planks": [ ( 146, 136, 120 ), ( 132, 124, 110 ), ( 158, 146, 126 ), ( 120, 114, 104 ) ],
    "planks_dark": [ ( 92, 64, 44 ), ( 80, 56, 40 ), ( 102, 72, 50 ), ( 72, 52, 38 ) ],
}


def planks( rng, n ):
    """ Sawn boards across the picture, 8 units wide and 2 to 6 feet long, nailed at their ends: weathered silver-grey
    for the stalls, crates and sheds, or stained dark for pews, doors and the council table. 5 1/3 px to the unit. """
    ppu = n / TILE_UNITS["planks"]
    block, u, v, length, course, row, count = coursed( rng, n, ( 8 * ppu, 8.05 * ppu ), ( 24 * ppu, 72 * ppu ) )
    across = v / course
    edge = np.minimum( np.minimum( u, length - u ), np.minimum( v, course - v ) )
    grain = np.choose( block % 3, [ stretched( rng, n, 2.0, 3, 300, ( 0.9, 30.0 ) ) for _ in range( 3 ) ] )
    rings = np.sin( 2 * math.pi * ( across * rng.uniform( 2.0, 4.0 ) + 0.35 * grain ) )
    fine = T.spectral( rng, n, 1.2, n / 6, None )
    knots = Mask( n )
    for _ in range( 10 ):
        rx = rng.uniform( 1.0, 2.0 ) * ppu
        knots.ellipse( rng.uniform( 0, n ), rng.uniform( 0, n ), rx, rx * rng.uniform( 0.4, 0.6 ) )
    knot = ndimage.gaussian_filter( knots.result(), 1.0, mode="wrap" )
    end = np.minimum( u, length - u )
    nails = np.zeros( ( n, n ) )
    for side in ( 0.3, 0.7 ):
        nails = np.maximum( nails, T.smoothstep( 0.5 * ppu, 0.25 * ppu,
                                                 np.hypot( end - 1.5 * ppu, ( across - side ) * course ) ) )
    bevel = rounded_edges( edge, 0.8 * ppu )
    gap = 1.0 - rounded_edges( edge, 0.3 * ppu )

    height = ( 0.55 + 0.04 * grain + 0.02 * rings + 0.01 * fine - 0.06 * knot ) * bevel + 0.05
    lum = ( 1.0 + 0.12 * grain + 0.05 * rings + 0.03 * fine - 0.4 * knot - 0.5 * nails ) * ( 0.35 + 0.65 * bevel ** 0.5 )
    colours = { name: shade( tones( rng, palette, count, 0.05, 0.8 )[block], lum ) for name, palette in PLANKS.items() }
    rough = np.clip( 0.82 + 0.04 * grain, 0.0, 1.0 ) * ( 1 - gap ) + gap
    return colours, rough, height, 3.5


def water( rng, n ):
    """ Still water in the fountain's basin: dark green, with a faint ripple. """
    ripple = T.spectral( rng, n, 2.4, 3, 48 )
    fine = T.spectral( rng, n, 1.6, 16, 160 )
    colour = paint( ( 44, 64, 58 ), 1.0 + 0.04 * ripple )
    rough = np.clip( 0.05 + 0.02 * fine, 0.0, 1.0 )
    return { "water": colour }, rough, 0.5 + 0.03 * ripple + 0.005 * fine, 3.0


def clock( rng, n ):
    """ The tower's clock face, drawn once over the picture (a decal: map_kit maps it whole onto its polygon): a cream
    enamel dial in a gilt rim, a black chapter ring with hour and minute marks, the hands at ten past ten. """
    ss = 2
    big = n * ss
    c = big / 2
    dial, ink, gilt = ( 226, 218, 196 ), ( 28, 28, 30 ), ( 176, 146, 74 )
    rgb = Image.new( "RGB", ( big, big ), dial )
    hgt = Image.new( "L", ( big, big ), 110 )
    draw, draw_h = ImageDraw.Draw( rgb ), ImageDraw.Draw( hgt )

    def circle( r, h, fill=None, outline=None, width=1 ):
        box = ( c - r, c - r, c + r, c + r )
        draw.ellipse( box, fill=fill, outline=outline, width=width )
        draw_h.ellipse( box, fill=h if fill is not None else None, outline=h if outline is not None else None, width=width )

    def at( r, degrees ):
        a = math.radians( degrees )
        return ( c + r * math.sin( a ), c - r * math.cos( a ) )

    circle( 0.5 * big, 190, fill=gilt )
    circle( 0.465 * big, 110, fill=dial )
    for r in ( 0.44, 0.35 ):
        circle( r * big, 130, outline=ink, width=int( 0.007 * big ) )
    for k in range( 60 ):
        hour = k % 5 == 0
        line = [ at( ( 0.355 if hour else 0.41 ) * big, k * 6 ), at( 0.44 * big, k * 6 ) ]
        width = int( ( 0.024 if hour else 0.006 ) * big )
        draw.line( line, fill=ink, width=width )
        draw_h.line( line, fill=130, width=width )

    def hand( length, width, degrees ):
        tip, tail, mid = at( length * big, degrees ), at( -0.08 * big, degrees ), at( length * 0.7 * big, degrees )
        side = ( math.cos( math.radians( degrees ) ) * width * big / 2, math.sin( math.radians( degrees ) ) * width * big / 2 )
        shape = [ ( tail[0] - side[0], tail[1] - side[1] ), ( mid[0] - side[0] * 1.6, mid[1] - side[1] * 1.6 ), tip,
                  ( mid[0] + side[0] * 1.6, mid[1] + side[1] * 1.6 ), ( tail[0] + side[0], tail[1] + side[1] ) ]
        draw.polygon( shape, fill=ink )
        draw_h.polygon( shape, fill=170 )

    hand( 0.25, 0.024, ( 10 + 10 / 60 ) * 30 )
    hand( 0.39, 0.016, 10 * 6 )
    circle( 0.028 * big, 200, fill=gilt )

    colour = np.asarray( rgb.reduce( ss ), float )
    height = np.asarray( hgt.reduce( ss ), float ) / 255.0
    grime = T.smoothstep( 0.5, 2.0, T.spectral( rng, n, 2.6, 2, 16 ) ) * 0.25
    colour = mix( colour * ( 1.0 + 0.03 * T.spectral( rng, n, 1.2, 20, None ) )[..., None], np.full_like( colour, 110.0 ), grime )
    return { "clock": colour }, np.full( ( n, n ), 0.5 ), height, 2.0


def hedge( rng, n ):
    """ A clipped box hedge: small leaves packed thick in greens, darker deeper in. 10 2/3 px to the unit. """
    ppu = n / TILE_UNITS["hedge"]
    deep = T.spectral( rng, n, 2.0, 4, 60 )
    base = np.stack( [ value * ( 1.0 + 0.2 * deep ) for value in ( 26, 38, 26 ) ], -1 )
    strokes = T.Strokes( base, 0.1 + 0.05 * deep, ss=2 )
    palette = [ ( 3, ( 52, 82, 40 ) ), ( 3, ( 64, 96, 46 ) ), ( 2, ( 44, 70, 38 ) ), ( 1, ( 84, 110, 56 ) ),
                ( 1, ( 70, 88, 44 ) ) ]
    per_layer = int( n * n / 13 )
    for layer, bright in ( ( 0.35, 0.75 ), ( 0.55, 0.9 ), ( 0.75, 1.05 ) ):
        colours = T.pick( rng, palette, per_layer ) * bright * rng.uniform( 0.85, 1.15, ( per_layer, 1 ) )
        xs, ys = rng.uniform( 0, n, per_layer ), rng.uniform( 0, n, per_layer )
        rx = rng.uniform( 0.2, 0.4, per_layer ) * ppu
        ry = rx * rng.uniform( 0.45, 1.0, per_layer )
        swap = rng.uniform( 0, 1, per_layer ) < 0.5
        heights = layer + rng.uniform( -0.05, 0.05, per_layer )
        for k in range( per_layer ):
            a, b = ( ry[k], rx[k] ) if swap[k] else ( rx[k], ry[k] )
            strokes.dot( xs[k], ys[k], a, b, colours[k], heights[k] )
    colour, height, cover = strokes.result()
    height = T.blur( height, 0.5 )
    ao = T.cavity_ao( height, ( ( 2.0, 2.0 ), ( 6.0, 1.2 ) ), 1.0 )
    rough = np.clip( 0.75 - 0.15 * cover + 0.05 * deep, 0.0, 1.0 )
    return { "hedge": T.shaded( colour, ao, 0.5 ) }, rough, height, 4.0


def slate( rng, n ):
    """ Slates 6 units to a course and 9.6 wide, each course broken joint with the one below and lapping it: blue-grey,
    some purpler or greener, the tails catching the light, lichen here and there. The picture's rows run down the roof,
    as roof_tiles' do. 5 1/3 px to the unit. """
    ppu = n / TILE_UNITS["slate"]
    courses, per_row = 16, 10
    course, width = n / courses, n / per_row
    y, x = np.mgrid[0:n, 0:n] + 0.5
    row = ( y // course ).astype( int )
    t = ( y - row * course ) / course                                # 0 at the head, 1 at the tail
    shifted = ( x + ( row % 2 ) * width / 2 ) % n
    col = ( shifted // width ).astype( int )
    s = ( shifted - col * width ) / width
    tone = tones( rng, [ ( 84, 90, 98 ), ( 92, 96, 104 ), ( 76, 80, 90 ), ( 98, 90, 100 ), ( 86, 94, 90 ), ( 70, 74, 82 ) ],
                  courses * per_row, 0.06, 0.8 )
    side_gap = np.minimum( s, 1 - s ) * width
    lip = rounded_edges( ( 1 - t ) * course, 0.5 * ppu )
    fine = T.spectral( rng, n, 1.0, n / 5, None )
    cleave = stretched( rng, n, 1.6, 6, 200, ( 1.0, 6.0 ) )
    blotch = T.spectral( rng, n, 3.0, 1, 8 )
    lichen = ( T.smoothstep( 1.4, 2.2, T.spectral( rng, n, 1.8, 16, 200 ) )
               * T.smoothstep( 0.3, 1.2, T.spectral( rng, n, 3.0, 2, 10 ) ) )

    height = ( 0.2 + 0.3 * t ) * lip * rounded_edges( side_gap, 0.3 * ppu ) + 0.015 * cleave + 0.01 * fine
    shadow = 0.5 + 0.5 * T.smoothstep( 0.0, 0.25, t )
    lum = ( ( 1.0 + 0.05 * cleave + 0.03 * fine + 0.05 * blotch ) * shadow
            * ( 0.75 + 0.25 * rounded_edges( side_gap, 0.4 * ppu ) ) )
    colour = mix( shade( tone[row * per_row + col], lum ), paint( ( 168, 160, 110 ), lum ), lichen * 0.7 )
    rough = np.clip( 0.62 + 0.05 * cleave + 0.15 * lichen, 0.0, 1.0 )
    return { "slate": colour }, rough, height, 4.0


def from_terrain( draw, paint_name ):
    """ One of Tools/terrain_textures.py's grounds as a model material: the same maps, with this file's OpenGL normals. """
    def texture( rng, n ):
        colour, rough, height, ao, strength = draw( rng, n )
        return { paint_name: colour }, rough, height, strength
    return texture


TEXTURES = {
    # name: ( draw, size px, seed, metalness )
    "render": ( render, 1024, 11, 0.0 ),
    "whitewash": ( whitewash, 512, 12, 0.0 ),
    "concrete": ( concrete, 512, 13, 0.0 ),
    "floorboards": ( floorboards, 1024, 14, 0.0 ),
    "quarry_tiles": ( quarry_tiles, 512, 15, 0.0 ),
    "roof_tiles": ( roof_tiles, 1024, 16, 0.0 ),
    "painted_wood": ( painted_wood, 512, 17, 0.0 ),
    "shutter_boards": ( shutter_boards, 512, 18, 0.0 ),
    "brick": ( brick, 512, 19, 0.0 ),
    "metal": ( metal, 256, 20, 0.75 ),
    # Belltower's
    "ashlar": ( ashlar, 1024, 21, 0.0 ),
    "rubble": ( rubble, 512, 22, 0.0 ),
    "setts": ( setts, 512, 23, 0.0 ),
    "flagstones": ( flagstones, 1024, 24, 0.0 ),
    "glass": ( glass, 256, 25, 0.0 ),
    "canvas": ( canvas, 512, 26, 0.0 ),
    "sandbags": ( sandbags, 512, 27, 0.0 ),
    "corrugated": ( corrugated, 512, 28, 0.3 ),
    "roller": ( roller, 512, 29, 0.0 ),
    "iron": ( iron, 256, 30, 0.0 ),
    "copper": ( copper, 512, 31, 0.0 ),
    "planks": ( planks, 512, 32, 0.0 ),
    "water": ( water, 512, 33, 0.0 ),
    "clock": ( clock, 512, 34, 0.0 ),
    "hedge": ( hedge, 512, 35, 0.0 ),
    "slate": ( slate, 512, 36, 0.0 ),
    "gravel": ( from_terrain( T.gravel, "gravel" ), 512, 37, 0.0 ),
    "soil": ( from_terrain( T.dirt, "soil" ), 1024, 38, 0.0 ),
    "lawn": ( from_terrain( T.meadow, "lawn" ), 1024, 39, 0.0 ),
    "rock": ( from_terrain( T.rock, "rock" ), 1024, 41, 0.0 ),
    # The Town House's
    "glass_clear": ( glass_clear, 512, 40, 0.0 ),
}

# Each paint's texture, so the buildings' script can find a paint's tile size.
PAINTS = {
    "render_ochre": "render", "render_pale": "render", "whitewash": "whitewash", "concrete": "concrete",
    "floorboards": "floorboards", "quarry_tiles": "quarry_tiles", "roof_tiles": "roof_tiles",
    "trim_white": "painted_wood", "trim_brown": "painted_wood", "trim_green": "painted_wood",
    "shutter_brown": "shutter_boards", "shutter_green": "shutter_boards", "brick": "brick", "metal": "metal",
    # Belltower's
    "render_rose": "render", "render_blue": "render", "render_cream": "render", "render_sage": "render",
    "render_terracotta": "render", "clay_pot": "render", "trim_blue": "painted_wood", "trim_red": "painted_wood",
    "shutter_blue": "shutter_boards", "shutter_red": "shutter_boards", "ashlar": "ashlar", "ashlar_grey": "ashlar",
    "rubble": "rubble", "setts": "setts", "flagstones": "flagstones", "glass": "glass", "canvas_red": "canvas",
    "canvas_green": "canvas", "canvas_blue": "canvas", "canvas_plain": "canvas", "sandbags": "sandbags",
    "corrugated": "corrugated", "roller_grey": "roller", "roller_green": "roller", "iron_black": "iron",
    "iron_green": "iron", "copper": "copper", "copper_brown": "copper", "planks": "planks", "planks_dark": "planks", "water": "water",
    "clock": "clock", "hedge": "hedge", "slate": "slate", "gravel": "gravel", "soil": "soil", "lawn": "lawn",
    "rock": "rock",
    # The Town House's
    "glass_clear": "glass_clear",
}

# Paints drawn once over their polygon (map_kit maps their UVs 0..1 across it) instead of repeating at world scale.
DECALS = { "clock", "glass_clear" }

# See-through paints, on glass.shader instead of complex.shader, with the shader's AlbedoAbsorption: how opaque the
# rough (dirty) parts are.
SEE_THROUGH = { "glass_clear": 0.8 }


def material_path( paint_name ):
    return f"{RESOURCE_DIR}/{paint_name}.vmat"


def tile_units( paint_name ):
    return TILE_UNITS[PAINTS[paint_name]]


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def save_grey( path, a ):
    Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ).save( path, optimize=True )


def save_rgb( path, a ):
    Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( path, optimize=True )


def vmat( paint_name, texture, metalness ):
    if paint_name in SEE_THROUGH:
        return glass_vmat( paint_name, texture, SEE_THROUGH[paint_name] )
    return ( '// Tools/building_textures.py\n'
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/complex.shader"\n'
             '    F_SPECULAR "1"\n'
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metalness:.2f}"\n'
             f'    TextureColor "{RESOURCE_DIR}/{paint_name}_color.png"\n'
             f'    TextureNormal "{RESOURCE_DIR}/{texture}_normal.png"\n'
             f'    TextureRoughness "{RESOURCE_DIR}/{texture}_rough.png"\n'
             f'    TextureAmbientOcclusion "{DEFAULT_AO}"\n'
             '    g_vColorTint "[1.0 1.0 1.0 1.0]"\n'
             '    g_flModelTintAmount "1.0"\n'
             "}\n" )


def glass_vmat( paint_name, texture, absorption ):
    """ glass.shader's layered quality, which composites glass seen through glass (a pane behind a pane) properly.
    The colour is the light let through, and the roughness blurs what's behind (g_flBlurAmount). """
    return ( '// Tools/building_textures.py\n'
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/glass.shader"\n'
             '    F_GLASS_QUALITY "2"\n'
             '    g_bFogEnabled "1"\n'
             '    g_flBlurAmount "0.12"\n'
             '    g_flRefractionStrength "1.004"\n'
             f'    AlbedoAbsorption "{absorption:.2f}"\n'
             '    g_flTintColor "[1.000000 1.000000 1.000000 0.000000]"\n'
             f'    TextureColor "{RESOURCE_DIR}/{paint_name}_color.png"\n'
             f'    TextureNormal "{RESOURCE_DIR}/{texture}_normal.png"\n'
             f'    TextureRoughness "{RESOURCE_DIR}/{texture}_rough.png"\n'
             '    TextureMetalness "[0.000000 0.000000 0.000000 0.000000]"\n'
             '    TextureAmbientOcclusion "[1.000000 1.000000 1.000000 0.000000]"\n'
             '    TextureBlendMask "materials/default/default_blend.tga"\n'
             '    TextureTintMask "materials/default/default.tga"\n'
             '    TextureTranslucency "materials/default/default_trans.tga"\n'
             "}\n" )


def write_texture( name ):
    draw, size, seed, metalness = TEXTURES[name]
    rng = np.random.default_rng( seed )
    colours, rough, height, strength = draw( rng, size )
    normal = gl_normals( height, strength * size / 1024.0 )

    OUT_DIR.mkdir( parents=True, exist_ok=True )
    save_rgb( OUT_DIR / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( OUT_DIR / f"{name}_rough.png", rough )
    for paint_name, colour in colours.items():
        assert PAINTS[paint_name] == name, paint_name
        save_rgb( OUT_DIR / f"{paint_name}_color.png", colour )
        ( OUT_DIR / f"{paint_name}.vmat" ).write_text( vmat( paint_name, name, metalness ), encoding="utf-8", newline="\n" )
    units = TILE_UNITS[name]
    print( f"wrote {name}: {', '.join( colours )} ({units:g} units a tile, {size / units:g} px a unit)" )
    return colours, normal, height


def lit( colour, normal ):
    """ Lit from the top left: with OpenGL normals, green is up the picture. """
    light = np.array( ( -0.45, 0.55, 0.7 ) )
    light /= np.linalg.norm( light )
    ndl = np.clip( np.sum( normal * light, -1 ), 0.0, 1.0 )
    return np.clip( colour * ( 0.35 + 0.9 * ndl )[..., None], 0, 255 )


def write_sheet( results, path ):
    rows = []
    for name, ( colours, normal, height ) in results.items():
        for paint_name, colour in colours.items():
            shaded = lit( colour, normal )
            tiled = Image.fromarray( np.tile( shaded, ( 2, 2, 1 ) ).astype( np.uint8 ) ).resize( ( 512, 512 ), Image.LANCZOS )
            detail = Image.fromarray( shaded[: shaded.shape[0] // 4, : shaded.shape[1] // 4].astype( np.uint8 ) ).resize( ( 512, 512 ), Image.NEAREST )
            heights = Image.fromarray( np.clip( height * 255, 0, 255 ).astype( np.uint8 ) ).resize( ( 256, 256 ) ).convert( "RGB" )
            row = Image.new( "RGB", ( 512 * 2 + 256, 512 ), ( 20, 20, 20 ) )
            row.paste( tiled, ( 0, 0 ) )
            row.paste( detail, ( 512, 0 ) )
            row.paste( heights, ( 1024, 0 ) )
            ImageDraw.Draw( row ).text( ( 10, 10 ), f"{paint_name} ({TILE_UNITS[name] * 2:g} units across)", fill=( 255, 255, 255 ) )
            rows.append( row )
    sheet = Image.new( "RGB", ( rows[0].width, 512 * len( rows ) ) )
    for k, row in enumerate( rows ):
        sheet.paste( row, ( 0, 512 * k ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"textures to draw (default all: {', '.join( TEXTURES )})" )
    parser.add_argument( "--sheet", help="also write a lit contact sheet here" )
    parser.add_argument( "--out", help="write the maps here instead of Assets/materials/buildings (for trying things out)" )
    args = parser.parse_args()

    global OUT_DIR
    if args.out:
        OUT_DIR = Path( args.out )

    names = args.names or list( TEXTURES )
    results = { name: write_texture( name ) for name in names }
    if args.sheet:
        write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
