"""
Ground materials for terrain, drawn from scratch with numpy and PIL: tileable colour, roughness, normal, height and
ambient occlusion maps, and the .tmat that points the terrain at them. Ridgeback uses them (Tools/ridgeback_map.py
paints where each one goes).

    python Tools/terrain_textures.py [name ...] [--size 1024] [--sheet <png>]

- Writes Assets/materials/terrain/<name>_color.png, _rough.png, _normal.png, _height.png, _ao.png and <name>.tmat
  (the editor packs the maps into the terrain's two textures when it compiles the .tmat).
- A material repeats every 32 * UVScale units: the terrain shader tiles by TERRAIN_SPLAT_TILE_UNITS (32) and the engine
  hands it 1 / UVScale. REPEAT below is that size in units, and the .tmat's UVScale is REPEAT / 32.
- Normals are DirectX style (green is the slope down the picture): the terrain turns the map's y to +Y local, and the
  picture's rows run along +Y.
- The height map drives height blending between materials (Terrain_HeightBlendWeight), so each material's highs are
  what should show through its neighbour: stones out of dirt, grass over soil.
- Ground that grass clumps grow on (meadow, dry meadow) is painted to the clumps' own colour, from
  Tools/ridgeback_grass.py's ground_colour, so where the clumps stop the field still reads as grass instead of turning
  dark. Run this again after changing the grass's colours.
- --sheet writes each material tiled 2x2, lit from the top left, with its height map, for checking.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/terrain"
RESOURCE_DIR = "materials/terrain"
TILE_UNITS = 32.0


# ---------------------------------------------------------------------------------------------------------------------
# Tileable fields. Everything wraps at the picture's edges.

def spectral( rng, n, beta, fmin, fmax=None ):
    """ Periodic fractal noise, unit deviation: white noise shaped to a 1/f^beta spectrum. f is cycles per tile, so
    whole numbers of waves fit across it and it tiles. """
    white = rng.standard_normal( ( n, n ) )
    spectrum = np.fft.rfft2( white )
    fy = np.fft.fftfreq( n )[:, None] * n
    fx = np.fft.rfftfreq( n )[None, :] * n
    f = np.sqrt( fx * fx + fy * fy )
    f[0, 0] = 1.0
    amp = f ** ( -beta / 2.0 )
    amp *= np.clip( ( f - fmin * 0.5 ) / ( fmin * 0.5 ), 0.0, 1.0 )
    if fmax:
        amp *= np.clip( 2.0 - f / fmax, 0.0, 1.0 )
    out = np.fft.irfft2( spectrum * amp, s=( n, n ) )
    return ( out - out.mean() ) / out.std()


def blur( a, sigma ):
    return ndimage.gaussian_filter( a, sigma, mode="wrap" )


def smoothstep( e0, e1, x ):
    t = np.clip( ( x - e0 ) / ( e1 - e0 ), 0.0, 1.0 )
    return t * t * ( 3.0 - 2.0 * t )


def warp( rng, n, field, amount, fmin=3, fmax=24 ):
    """ The field pushed around by noise, amount px at most, so blobs and veins aren't round. """
    dx = spectral( rng, n, 2.5, fmin, fmax ) * amount
    dy = spectral( rng, n, 2.5, fmin, fmax ) * amount
    yy, xx = np.mgrid[0:n, 0:n].astype( float )
    return ndimage.map_coordinates( field, [ yy + dy, xx + dx ], order=1, mode="grid-wrap" )


class Strokes:
    """ Lines drawn at ss times the size and box-filtered down, wrapping at the edges. Draws colour, height and coverage
    together, each stroke over the ones before it. """

    def __init__( self, colour, height, ss=3 ):
        n = colour.shape[0]
        self.n, self.ss = n, ss
        big = n * ss
        self.rgb = Image.fromarray( np.clip( colour, 0, 255 ).astype( np.uint8 ) ).resize( ( big, big ), Image.BILINEAR )
        self.height = Image.fromarray( np.clip( height * 255, 0, 255 ).astype( np.uint8 ) ).resize( ( big, big ), Image.BILINEAR )
        self.cover = Image.new( "L", ( big, big ), 0 )
        self.draw_rgb = ImageDraw.Draw( self.rgb )
        self.draw_height = ImageDraw.Draw( self.height )
        self.draw_cover = ImageDraw.Draw( self.cover )

    def _copies( self, xs, ys, pad ):
        """ The offsets a shape spanning xs, ys (big px) needs to wrap round the tile. """
        big = self.n * self.ss
        offsets = []
        for ox in ( -big, 0, big ):
            if min( xs ) + ox > big + pad or max( xs ) + ox < -pad:
                continue
            for oy in ( -big, 0, big ):
                if min( ys ) + oy > big + pad or max( ys ) + oy < -pad:
                    continue
                offsets.append( ( ox, oy ) )
        return offsets

    def blade( self, points, widths, colours, heights ):
        """ A polyline of segments, each with its own width (px), colour and height (0..1). Points in tile px. """
        s = self.ss
        pts = [ ( x * s, y * s ) for x, y in points ]
        xs, ys = [ p[0] for p in pts ], [ p[1] for p in pts ]
        for ox, oy in self._copies( xs, ys, max( widths ) * s ):
            for k in range( len( pts ) - 1 ):
                seg = [ ( pts[k][0] + ox, pts[k][1] + oy ), ( pts[k + 1][0] + ox, pts[k + 1][1] + oy ) ]
                w = max( 1, int( round( widths[k] * s ) ) )
                self.draw_rgb.line( seg, fill=tuple( int( c ) for c in colours[k] ), width=w )
                self.draw_height.line( seg, fill=int( heights[k] * 255 ), width=w )
                self.draw_cover.line( seg, fill=255, width=w )

    def dot( self, x, y, rx, ry, colour, height ):
        s = self.ss
        cx, cy = x * s, y * s
        for ox, oy in self._copies( [ cx - rx * s, cx + rx * s ], [ cy - ry * s, cy + ry * s ], 0 ):
            box = [ cx - rx * s + ox, cy - ry * s + oy, cx + rx * s + ox, cy + ry * s + oy ]
            self.draw_rgb.ellipse( box, fill=tuple( int( c ) for c in colour ) )
            self.draw_height.ellipse( box, fill=int( height * 255 ) )
            self.draw_cover.ellipse( box, fill=255 )

    def result( self ):
        s = self.ss
        rgb = np.asarray( self.rgb.reduce( s ), float )
        height = np.asarray( self.height.reduce( s ), float ) / 255.0
        cover = np.asarray( self.cover.reduce( s ), float ) / 255.0
        return rgb, height, cover


def pick( rng, palette, count ):
    """ count colours from [ ( weight, ( r, g, b ) ), ... ]. """
    weights = np.array( [ w for w, _ in palette ], float )
    idx = rng.choice( len( palette ), size=count, p=weights / weights.sum() )
    return np.array( [ palette[i][1] for i in idx ], float )


def curve_points( x, y, angle, length, bend, segments ):
    """ A blade seen from above: a curve from (x, y) that turns by bend radians over its length. """
    points = [ ( x, y ) ]
    step = length / segments
    for k in range( segments ):
        a = angle + bend * ( k + 0.5 ) / segments
        x += math.cos( a ) * step
        y += math.sin( a ) * step
        points.append( ( x, y ) )
    return points


# ---------------------------------------------------------------------------------------------------------------------
# Maps from a height field

def normal_map( height, strength ):
    """ DirectX-style tangent normals from a height field (0..1 per px, scaled by strength). """
    dx = ( np.roll( height, -1, 1 ) - np.roll( height, 1, 1 ) ) * 0.5 * strength
    dy = ( np.roll( height, -1, 0 ) - np.roll( height, 1, 0 ) ) * 0.5 * strength
    n = np.stack( [ -dx, -dy, np.ones_like( height ) ], -1 )
    n /= np.linalg.norm( n, axis=-1, keepdims=True )
    return n


def srgb_to_linear( c ):
    c = np.clip( c / 255.0, 0.0, 1.0 )
    return np.where( c <= 0.04045, c / 12.92, ( ( c + 0.055 ) / 1.055 ) ** 2.4 )


def linear_to_srgb( c ):
    c = np.clip( c, 0.0, 1.0 )
    return 255.0 * np.where( c <= 0.0031308, c * 12.92, 1.055 * c ** ( 1 / 2.4 ) - 0.055 )


# How much of a grass ground's own light and dark it keeps when it's painted to the grass's colour, so its brightest
# blades don't outshine the clumps standing on it.
GRASS_CONTRAST = 0.85


def match_grass( name, colour ):
    """ A grass ground's colour map moved to the grass clumps' mean colour (Tools/ridgeback_grass.py, beside this). """
    import ridgeback_grass
    target = ridgeback_grass.ground_colour( name )
    if target is None:
        return colour
    linear = srgb_to_linear( colour )
    mean = linear.reshape( -1, 3 ).mean( 0 )
    linear = ( mean + ( linear - mean ) * GRASS_CONTRAST ) * ( target / mean )
    print( f"{name}: mean colour {np.round( mean, 4 )} -> {np.round( target, 4 )} (linear)" )
    return linear_to_srgb( linear )


def shaded( colour, ao, amount=0.4 ):
    """ Some of the cavity shadow in the colour itself, so gaps still read far off, where the normals no longer do. """
    return colour * ( 1.0 - amount + amount * ao )[..., None]


def cavity_ao( height, radii, strength ):
    """ Darker where the ground sits below its surroundings: the gaps between blades, stones and plates. """
    ao = np.ones_like( height )
    for radius, weight in radii:
        ao -= np.maximum( 0.0, blur( height, radius ) - height ) * weight * strength
    return np.clip( ao, 0.0, 1.0 )


# ---------------------------------------------------------------------------------------------------------------------
# Materials. Each returns colour (0..255 sRGB), roughness, height, ao (0..1) and the normal strength.

def grass_field( rng, n, *, soil, thatch, blades, clover, flowers, blade_count, thatch_count, lengths, widths,
                 patch=0.035, root_dark=0.55 ):
    """ Grass seen from above: soil under a layer of dead thatch, then blades leaning every way, each darker at its
    root where the others shade it. The later a blade is drawn the higher it sits. """
    base = np.empty( ( n, n, 3 ) )
    grain = spectral( rng, n, 1.6, 40, n / 2 )
    lumps = spectral( rng, n, 2.6, 6, 40 )
    for c in range( 3 ):
        base[..., c] = soil[c] * ( 1.0 + 0.10 * grain + 0.12 * lumps )
    strokes = Strokes( base, 0.12 + 0.05 * lumps, ss=3 )

    def draw( count, palette, length_range, width_range, height_range, segments, bend, dark ):
        colours = pick( rng, palette, count )
        colours *= rng.uniform( 0.85, 1.15, ( count, 1 ) )
        lo, hi = np.log( length_range[0] ), np.log( length_range[1] )
        for k in range( count ):
            x, y = rng.uniform( 0, n, 2 )
            angle = rng.uniform( 0, 2 * math.pi )
            length = math.exp( rng.uniform( lo, hi ) )
            points = curve_points( x, y, angle, length, rng.normal( 0, bend ), segments )
            w0 = rng.uniform( *width_range )
            layer = height_range[0] + ( height_range[1] - height_range[0] ) * k / count
            ts = [ ( i + 0.5 ) / segments for i in range( segments ) ]
            strokes.blade( points,
                           [ w0 * ( 1.0 - 0.6 * t ) for t in ts ],
                           [ colours[k] * ( dark + ( 1.1 - dark ) * t ) for t in ts ],
                           [ min( 1.0, layer + 0.12 * t ) for t in ts ] )

    draw( thatch_count, thatch, ( lengths[0] * 1.2, lengths[1] * 1.4 ), ( widths[0] * 0.7, widths[1] * 0.8 ), ( 0.25, 0.4 ), 3, 0.6, 0.8 )

    # Clover and small weeds among the grass, drawn part-way through so blades cover some of them.
    blade_colours = blades
    drawn = 0
    for share in ( 0.45, 0.55 ):
        count = int( blade_count * share )
        draw( count, blade_colours, lengths, widths, ( 0.42 + 0.45 * drawn / blade_count, 0.42 + 0.45 * ( drawn + count ) / blade_count ), 4, 0.5, root_dark )
        drawn += count
        if clover and share == 0.45:
            for _ in range( clover[0] ):
                x, y = rng.uniform( 0, n, 2 )
                colour = np.array( clover[1] ) * rng.uniform( 0.85, 1.15 )
                for _ in range( 3 ):
                    a = rng.uniform( 0, 2 * math.pi )
                    r = rng.uniform( 1.2, 2.2 )
                    strokes.dot( x + math.cos( a ) * r, y + math.sin( a ) * r, r, r, colour, 0.62 )

    for _ in range( flowers[0] ):
        x, y = rng.uniform( 0, n, 2 )
        colour = np.array( flowers[1][rng.integers( len( flowers[1] ) )] ) * rng.uniform( 0.9, 1.05 )
        r = rng.uniform( 0.8, 1.6 )
        strokes.dot( x, y, r, r, colour, 0.95 )

    colour, height, cover = strokes.result()

    # Broad patches, weak: the tile is a couple of metres, so anything big would show as a grid from afar.
    patches = 1.0 + patch * spectral( rng, n, 3.0, 3, 10 )
    colour *= patches[..., None]
    height = blur( height, 0.6 )
    rough = 0.93 - 0.2 * cover + 0.04 * spectral( rng, n, 1.0, 64, n / 2 )
    ao = cavity_ao( height, ( ( 2.0, 2.5 ), ( 8.0, 1.5 ) ), 1.0 )
    return colour, rough, height, ao, 3.5


def meadow( rng, n ):
    return grass_field(
        rng, n,
        soil=( 60, 50, 36 ),
        thatch=[ ( 3, ( 104, 90, 58 ) ), ( 2, ( 124, 108, 70 ) ), ( 2, ( 86, 76, 50 ) ) ],
        blades=[ ( 22, ( 54, 76, 30 ) ), ( 30, ( 70, 94, 36 ) ), ( 26, ( 88, 110, 42 ) ), ( 12, ( 108, 118, 50 ) ),
                 ( 6, ( 122, 116, 66 ) ), ( 4, ( 46, 66, 30 ) ) ],
        clover=( 700, ( 50, 80, 36 ) ),
        flowers=( 50, [ ( 232, 228, 206 ), ( 226, 204, 74 ) ] ),
        blade_count=52000, thatch_count=9000, lengths=( 7.0, 30.0 ), widths=( 1.3, 2.6 ),
    )


def meadow_dry( rng, n ):
    return grass_field(
        rng, n,
        soil=( 96, 82, 60 ),
        thatch=[ ( 3, ( 150, 130, 88 ) ), ( 2, ( 126, 106, 72 ) ), ( 2, ( 170, 152, 106 ) ) ],
        blades=[ ( 18, ( 168, 150, 98 ) ), ( 10, ( 186, 170, 122 ) ), ( 20, ( 146, 126, 80 ) ), ( 20, ( 122, 114, 62 ) ),
                 ( 18, ( 100, 102, 50 ) ), ( 10, ( 78, 92, 38 ) ) ],
        clover=None,
        flowers=( 25, [ ( 226, 204, 74 ), ( 214, 214, 196 ) ] ),
        blade_count=38000, thatch_count=16000, lengths=( 6.0, 28.0 ), widths=( 1.0, 2.1 ),
        root_dark=0.62,
    )


def stone_colours( rng, count, palette, spread=0.1 ):
    colours = pick( rng, palette, count )
    return colours * rng.uniform( 1.0 - spread, 1.0 + spread, ( count, 1 ) )


class Ground:
    """ Colour, height and roughness that stones are pressed into one at a time. A stone only shows where it stands
    higher than what's there (a height buffer), so later ones pile against earlier ones and sink into the soil. """

    def __init__( self, colour, height, rough, speckle ):
        self.n = height.shape[0]
        self.colour, self.height, self.rough = colour.copy(), height.copy(), rough.copy()
        self.speckle = speckle
        self.stone = np.zeros_like( height )

    def press( self, rng, x, y, radius, colour, rough, *, top=1.0, sink=0.0, aspect=1.0, angular=False, tilt=0.0 ):
        """ One stone at (x, y), radius px. Rounded ones are lumpy domes; angular ones have a few straight sides,
        a flat top tipped by tilt, and bevelled edges. sink is how far its base sits under height 0. """
        n = self.n
        reach = int( math.ceil( radius * max( aspect, 1.0 ) * 1.3 ) ) + 1
        xs = np.arange( int( x ) - reach, int( x ) + reach + 1 )
        ys = np.arange( int( y ) - reach, int( y ) + reach + 1 )
        u0 = xs[None, :] + 0.5 - x
        v0 = ys[:, None] + 0.5 - y
        angle = rng.uniform( 0, 2 * math.pi )
        c, s = math.cos( angle ), math.sin( angle )
        u = ( u0 * c + v0 * s ) / ( radius * aspect )
        v = ( -u0 * s + v0 * c ) / radius
        if angular:
            # Faces spread all round (random angles could leave a gap over half a turn, and the stone open on that side)
            sides = rng.integers( 5, 8 )
            dirs = ( np.arange( sides ) + rng.uniform( -0.35, 0.35, sides ) ) * 2 * math.pi / sides
            reach_k = rng.uniform( 0.7, 1.0, sides )
            r = np.max( [ ( u * math.cos( a ) + v * math.sin( a ) ) / k for a, k in zip( dirs, reach_k ) ], axis=0 )
            bevel = rng.uniform( 0.18, 0.35 )
            profile = np.clip( ( 1.0 - r ) / bevel, 0.0, 1.0 ) ** 0.7
            gx, gy = rng.normal( 0, tilt, 2 )
            profile = profile * ( 1.0 + gx * u + gy * v ) * ( r < 1.0 )
        else:
            theta = np.arctan2( v, u )
            lump = sum( rng.normal( 0, 0.06 ) * np.cos( k * theta + rng.uniform( 0, 6.3 ) ) for k in ( 2, 3, 5 ) )
            r = np.hypot( u, v ) * ( 1.0 + lump )
            profile = np.sqrt( np.clip( 1.0 - r * r, 0.0, 1.0 ) )
        z = top * profile - sink
        rows, cols = np.ix_( ys % n, xs % n )
        higher = ( profile > 0 ) & ( z > self.height[rows, cols] )
        if not higher.any():
            return
        edge = np.clip( profile / 0.25, 0.0, 1.0 )[..., None]
        shade = ( 0.72 + 0.36 * profile )[..., None] * ( 1.0 + 0.05 * self.speckle[rows, cols] )[..., None]
        mixed = self.colour[rows, cols] * ( 1 - edge ) + np.asarray( colour ) * shade * edge
        self.colour[rows, cols] = np.where( higher[..., None], mixed, self.colour[rows, cols] )
        self.height[rows, cols] = np.where( higher, z, self.height[rows, cols] )
        self.rough[rows, cols] = np.where( higher, rough, self.rough[rows, cols] )
        self.stone[rows, cols] = np.where( higher, np.maximum( self.stone[rows, cols], edge[..., 0] ), self.stone[rows, cols] )


def sizes( rng, count, smallest, largest, power=2.2 ):
    """ Radii with many small and few large, as sieved stone comes (a power law between the two). """
    u = rng.uniform( 0, 1, count )
    a, b = smallest ** ( 1 - power ), largest ** ( 1 - power )
    return ( a + u * ( b - a ) ) ** ( 1 / ( 1 - power ) )


EARTH = [ ( 4, ( 138, 132, 122 ) ), ( 3, ( 156, 146, 126 ) ), ( 2, ( 106, 98, 88 ) ), ( 1, ( 172, 166, 154 ) ),
          ( 1, ( 128, 106, 84 ) ) ]


def dirt( rng, n ):
    """ Packed dry earth: brown with faint dusty and damp patches, crumbs and clods, half-buried pebbles, bits of straw. """
    broad = spectral( rng, n, 2.8, 3, 20 )
    medium = spectral( rng, n, 2.0, 14, 120 )
    grain = spectral( rng, n, 1.0, 120, n / 2 )
    dusty = 0.5 * smoothstep( 0.4, 1.8, warp( rng, n, spectral( rng, n, 2.6, 6, 32 ), 24 ) )

    base = np.array( ( 106, 87, 66 ), float )
    dust = np.array( ( 126, 110, 90 ), float )
    colour = base * ( 1 - dusty[..., None] ) + dust * dusty[..., None]
    colour *= ( 1.0 + 0.04 * broad + 0.05 * medium + 0.06 * grain )[..., None]
    height = 0.22 + 0.04 * broad + 0.04 * medium + 0.02 * grain
    ground = Ground( colour, height, 0.95 + 0.0 * height, spectral( rng, n, 1.2, 40, n / 2 ) )

    # Clods and crumbs of the same earth, then pebbles, most of them sunk in it.
    crumbs = sizes( rng, 3500, 1.2, 7.0, 2.6 )
    for r in crumbs:
        x, y = rng.uniform( 0, n, 2 )
        tone = base * rng.uniform( 0.85, 1.12 ) * ( 1.0 + 0.08 * dusty[int( y ), int( x )] )
        ground.press( rng, x, y, r, tone, 0.95, top=0.22 + 0.1 * rng.uniform(), sink=-0.18, aspect=rng.uniform( 1.0, 1.6 ),
                      angular=True, tilt=0.15 )
    pebbles = stone_colours( rng, 1400, EARTH, 0.08 )
    for k, r in enumerate( sizes( rng, 1400, 1.5, 9.0, 2.4 ) ):
        x, y = rng.uniform( 0, n, 2 )
        ground.press( rng, x, y, r, pebbles[k], rng.uniform( 0.65, 0.85 ), top=0.75, sink=rng.uniform( 0.25, 0.6 ) - 0.3,
                      aspect=rng.uniform( 1.0, 1.5 ), angular=rng.uniform() < 0.4, tilt=0.1 )

    # Straw and twigs lying on it.
    strokes = Strokes( ground.colour, np.clip( ground.height, 0, 1 ), ss=3 )
    straw = pick( rng, [ ( 3, ( 150, 132, 90 ) ), ( 2, ( 118, 98, 66 ) ), ( 1, ( 84, 70, 52 ) ) ], 260 )
    for k in range( 260 ):
        x, y = rng.uniform( 0, n, 2 )
        points = curve_points( x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 6, 20 ), rng.normal( 0, 0.4 ), 3 )
        w = rng.uniform( 0.8, 1.4 )
        strokes.blade( points, [ w ] * 3, [ straw[k] * f for f in ( 0.9, 1.0, 1.05 ) ], [ 0.6 ] * 3 )
    colour, height, cover = strokes.result()

    height = blur( height, 0.5 )
    rough = np.where( cover > 0.5, 0.9, ground.rough )
    ao = cavity_ao( height, ( ( 2.0, 2.0 ), ( 10.0, 1.2 ) ), 1.0 )
    return shaded( colour, ao ), rough, height, ao, 5.0


def gravel( rng, n ):
    """ Loose rounded gravel, as on a track or a dry river bed: packed pebbles of greys and fawns over dark grit. """
    grit = spectral( rng, n, 1.0, 100, n / 2 )
    colour = np.array( ( 88, 80, 68 ), float ) * ( 1.0 + 0.15 * grit )[..., None]
    height = 0.05 + 0.03 * grit
    ground = Ground( colour, height, 0.96 + 0.0 * grit, spectral( rng, n, 1.2, 40, n / 2 ) )
    palette = [ ( 6, ( 122, 116, 106 ) ), ( 4, ( 138, 130, 116 ) ), ( 3, ( 98, 94, 88 ) ), ( 3, ( 136, 120, 96 ) ),
                ( 2, ( 114, 98, 78 ) ), ( 1, ( 160, 152, 138 ) ), ( 1, ( 82, 80, 76 ) ) ]
    count = int( 9000 * ( n / 1024 ) ** 2 )
    radii = sizes( rng, count, 2.0, 13.0, 2.0 ) * n / 1024
    colours = stone_colours( rng, count, palette, 0.08 )
    for k in np.argsort( -radii ):                    # big ones first, small ones settle between
        x, y = rng.uniform( 0, n, 2 )
        ground.press( rng, x, y, radii[k], colours[k], rng.uniform( 0.5, 0.78 ), top=0.55 + 0.45 * rng.uniform(),
                      sink=rng.uniform( 0.0, 0.3 ), aspect=rng.uniform( 1.0, 1.7 ), angular=rng.uniform() < 0.15, tilt=0.1 )

    height = blur( np.clip( ground.height, 0, 1 ), 0.5 )
    ao = cavity_ao( height, ( ( 1.5, 2.5 ), ( 6.0, 1.5 ) ), 1.0 )
    return shaded( ground.colour, ao ), ground.rough, height, ao, 7.0


def rock( rng, n ):
    """ Weathered rock: rounded lumps and ridges, a few fractures, lighter where it stands out, dirt in the hollows,
    iron stains and lichen. No closed polygons: joints wander and fade out. """
    def ridges( fmin, fmax, amount ):
        return ( 1.0 - np.abs( warp( rng, n, spectral( rng, n, 2.4, fmin, fmax ), amount ) ) / 2.5 ).clip( 0, 1 ) ** 2

    lumps = spectral( rng, n, 2.8, 2, 24 )
    ridged = 0.55 * ridges( 3, 24, 30 ) + 0.3 * ridges( 8, 64, 14 ) + 0.15 * ridges( 24, 160, 6 )
    fine = spectral( rng, n, 1.3, 60, n / 2 )
    # Joints: long warped lines that come and go.
    joint = 1.0 - smoothstep( 0.0, 0.06, np.abs( warp( rng, n, spectral( rng, n, 2.4, 3, 18 ), 50 ) ) )
    joint *= smoothstep( -0.1, 0.8, spectral( rng, n, 2.0, 3, 12 ) )
    joint2 = 1.0 - smoothstep( 0.0, 0.05, np.abs( warp( rng, n, spectral( rng, n, 2.2, 6, 30 ), 25 ) ) )
    joint2 *= smoothstep( 0.2, 1.0, spectral( rng, n, 2.0, 4, 16 ) )
    height = 0.45 * lumps / 3 + 0.45 * ridged + 0.04 * fine - 0.22 * joint - 0.12 * joint2
    height = ( height - height.min() ) / ( height.max() - height.min() )

    relief = height - blur( height, 12 )
    base = np.array( ( 122, 119, 112 ), float )
    colour = base * ( 1.0 + 0.9 * relief + 0.05 * lumps / 3 + 0.05 * fine )[..., None]
    stain = 0.25 * smoothstep( 0.9, 2.0, warp( rng, n, spectral( rng, n, 2.6, 5, 32 ), 30 ) )
    colour = colour * ( 1 - stain[..., None] ) + np.array( ( 142, 114, 84 ) ) * stain[..., None]
    low = smoothstep( 0.02, 0.12, blur( height, 5 ) - height ) + 0.35 * np.maximum( joint, joint2 )
    low = np.clip( low, 0, 1 )
    colour = colour * ( 1 - 0.55 * low[..., None] ) + np.array( ( 72, 64, 54 ) ) * 0.55 * low[..., None]
    lichen_mask = smoothstep( 1.2, 1.9, spectral( rng, n, 1.4, 16, 256 ) ) * smoothstep( 0.0, 0.8, spectral( rng, n, 2.5, 3, 20 ) )
    lichen_mask *= smoothstep( 0.45, 0.7, height ) * 0.85
    tint = np.where( ( spectral( rng, n, 2.0, 8, 64 ) > 0 )[..., None], np.array( ( 150, 148, 104 ) ), np.array( ( 160, 166, 150 ) ) )
    colour = colour * ( 1 - lichen_mask[..., None] ) + tint * lichen_mask[..., None]

    rough = 0.86 - 0.08 * relief * 4 + 0.05 * low
    ao = cavity_ao( height, ( ( 3.0, 1.5 ), ( 16.0, 1.2 ) ), 1.0 )
    return shaded( colour, ao ), np.clip( rough, 0.6, 1.0 ), height, ao, 9.0


def scree( rng, n ):
    """ Stony ground on steep slopes and high up: broken rock of every size, half sunk in grey-brown soil. """
    broad = spectral( rng, n, 2.8, 3, 20 )
    grain = spectral( rng, n, 1.0, 120, n / 2 )
    colour = np.array( ( 114, 104, 90 ), float ) * ( 1.0 + 0.05 * broad + 0.07 * grain )[..., None]
    height = 0.2 + 0.03 * broad + 0.02 * grain
    ground = Ground( colour, height, 0.95 + 0.0 * grain, spectral( rng, n, 1.2, 40, n / 2 ) )
    palette = [ ( 5, ( 128, 125, 118 ) ), ( 3, ( 110, 107, 101 ) ), ( 3, ( 148, 144, 136 ) ), ( 2, ( 134, 118, 98 ) ),
                ( 1, ( 94, 92, 88 ) ) ]
    count = 5200
    radii = sizes( rng, count, 2.0, 26.0, 2.3 )
    colours = stone_colours( rng, count, palette, 0.07 )
    bury = warp( rng, n, spectral( rng, n, 2.4, 3, 30 ), 25 )           # where the soil covers the stones
    for k in np.argsort( -radii ):
        x, y = rng.uniform( 0, n, 2 )
        sink = 0.15 + 0.25 * np.clip( bury[int( y ), int( x )], -1, 1.5 ) + rng.uniform( 0, 0.2 )
        ground.press( rng, x, y, radii[k], colours[k], rng.uniform( 0.75, 0.9 ), top=0.8, sink=sink - 0.2,
                      aspect=rng.uniform( 1.0, 1.8 ), angular=True, tilt=0.2 )

    height = blur( np.clip( ground.height, 0, 1 ), 0.6 )
    ao = cavity_ao( height, ( ( 2.0, 2.0 ), ( 10.0, 1.2 ) ), 1.0 )
    return shaded( ground.colour, ao ), ground.rough, height, ao, 6.0


# ---------------------------------------------------------------------------------------------------------------------
# name: ( draw, repeat in units, surface, seed )

MATERIALS = {
    "meadow": ( meadow, 96, "surfaces/grass.surface", 11 ),
    "meadow_dry": ( meadow_dry, 96, "surfaces/grass.surface", 12 ),
    "dirt": ( dirt, 128, "surfaces/dirt.surface", 13 ),
    "gravel": ( gravel, 64, "surfaces/dirt.surface", 14 ),
    "rock": ( rock, 256, "surfaces/default.surface", 15 ),
    "scree": ( scree, 160, "surfaces/dirt.surface", 16 ),
}


def save_grey( path, a ):
    Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" ).save( path, optimize=True )


def write_material( name, size ):
    draw, repeat, surface, seed = MATERIALS[name]
    rng = np.random.default_rng( seed )
    colour, rough, height, ao, strength = draw( rng, size )
    colour = match_grass( name, colour )
    normal = normal_map( height, strength * size / 1024.0 )

    OUT_DIR.mkdir( parents=True, exist_ok=True )
    Image.fromarray( np.clip( np.rint( colour ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( OUT_DIR / f"{name}_color.png", optimize=True )
    save_grey( OUT_DIR / f"{name}_rough.png", rough )
    save_grey( OUT_DIR / f"{name}_height.png", height )
    save_grey( OUT_DIR / f"{name}_ao.png", ao )
    Image.fromarray( np.clip( np.rint( ( normal * 0.5 + 0.5 ) * 255 ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( OUT_DIR / f"{name}_normal.png", optimize=True )

    tmat = {
        "AlbedoImage": f"{RESOURCE_DIR}/{name}_color.png",
        "RoughnessImage": f"{RESOURCE_DIR}/{name}_rough.png",
        "NormalImage": f"{RESOURCE_DIR}/{name}_normal.png",
        "HeightImage": f"{RESOURCE_DIR}/{name}_height.png",
        "AOImage": f"{RESOURCE_DIR}/{name}_ao.png",
        "UVScale": repeat / TILE_UNITS,
        "Metalness": 0,
        "NormalStrength": 1,
        "HeightBlendStrength": 1,
        "DisplacementScale": 0,
        "NoTiling": False,
        "Surface": surface,
        "__references": [],
        "__version": 0,
    }
    ( OUT_DIR / f"{name}.tmat" ).write_text( json.dumps( tmat, indent=2 ), encoding="utf-8" )
    print( f"wrote {name}: {repeat} units a tile ({repeat * 2.54 / 100:.2f} m), {size}px" )
    return colour, normal, height


def lit( colour, normal ):
    light = np.array( ( -0.45, -0.55, 0.7 ) )                 # from the top left (DirectX y is down the picture)
    light /= np.linalg.norm( light )
    ndl = np.clip( np.sum( normal * light, -1 ), 0.0, 1.0 )
    return np.clip( colour * ( 0.35 + 0.9 * ndl )[..., None], 0, 255 )


def write_sheet( results, path ):
    tiles = []
    for name, ( colour, normal, height ) in results.items():
        shaded = lit( colour, normal )
        tiled = np.tile( shaded, ( 2, 2, 1 ) )
        small = Image.fromarray( tiled.astype( np.uint8 ) ).resize( ( 768, 768 ), Image.LANCZOS )
        detail = Image.fromarray( shaded[:384, :384].astype( np.uint8 ) ).resize( ( 768, 768 ), Image.NEAREST )
        heights = Image.fromarray( np.clip( np.tile( height, ( 2, 2 ) ) * 255, 0, 255 ).astype( np.uint8 ) ).resize( ( 384, 384 ) ).convert( "RGB" )
        row = Image.new( "RGB", ( 768 * 2 + 384, 768 ), ( 20, 20, 20 ) )
        row.paste( small, ( 0, 0 ) )
        row.paste( detail, ( 768, 0 ) )
        row.paste( heights, ( 768 * 2, 0 ) )
        ImageDraw.Draw( row ).text( ( 10, 10 ), name, fill=( 255, 255, 255 ) )
        tiles.append( row )
    sheet = Image.new( "RGB", ( tiles[0].width, 768 * len( tiles ) ) )
    for k, row in enumerate( tiles ):
        sheet.paste( row, ( 0, 768 * k ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"materials to draw (default all: {', '.join( MATERIALS )})" )
    parser.add_argument( "--size", type=int, default=1024 )
    parser.add_argument( "--sheet", help="also write a lit contact sheet here" )
    parser.add_argument( "--out", help="write the maps here instead of Assets/materials/terrain (for trying things out)" )
    args = parser.parse_args()

    global OUT_DIR
    if args.out:
        OUT_DIR = Path( args.out )

    names = args.names or list( MATERIALS )
    results = { name: write_material( name, args.size ) for name in names }
    if args.sheet:
        write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
