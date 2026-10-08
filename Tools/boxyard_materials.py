"""
Boxyard's materials, drawn with numpy into Assets/materials/boxyard/: the shipping containers' paint, the yard's
concrete, the perimeter wall's precast panels, the floor markings and the small props' finishes.

    python Tools/boxyard_materials.py [names ...] [--out <dir>] [--sheet <png>]

Boxyard is the project's own container yard on Shipment's layout (Tools/boxyard_map.py builds it). Shipment's dev
textures were flat colours, so everything here is drawn at its real size from what the real thing looks like.

The containers are ISO 1CC (20 ft x 8 ft x 8 ft 6 in) dry boxes. Their side walls' trapezoidal corrugation is geometry
(boxyard_map builds it from the constants below), so the paint here knows where every bend is: knocks chip the outer
bends, rain runs down the inner flats and the inner corners hold a little dirt. One atlas per colour and variant
(`bx_container_<colour>_<variant>`, 4096 x 2048):

    side A  u 0.00-0.50  v 0.5-1     the -y side, seen from outside, the door end on the right
    side B  u 0.50-1.00  v 0.5-1     the +y side, the door end on the left
    doors   u 0.00-0.25  v 0.0-0.5   the +x end
    front   u 0.25-0.50  v 0.0-0.5   the -x end, the blank front wall
    roof    u 0.50-1.00  v 0.0-0.5   u along the length (-x to +x), v across (-y to +y)

Each region spans its face edge to edge (sides 238.6 x 102, ends 96 x 102, roof 238.6 x 96 inches), so boxyard_map
maps a point's place on the box straight to the atlas. The paint is a ship container's marine paint: weathered, chalked
by the sun on top, rusting at the bottom rails, the castings and wherever it's been knocked through, streaked with rust
and grime below. The markings are ISO 6346's: an owner code (made-up, each ending U), a serial and its real check digit,
and the 22G1 size and type code, plus the weights on the left door and its CSC plate. No real owner, lessor or logo.

The inside (`bx_container_inside`, 4096 x 2048) is one atlas for every open container: side wall, plywood floor,
ceiling, the front wall's inside and the doors' insides.

The rest tile at their real size:
    bx_concrete     the yard's slabs (16 ft square, sawn joints, cracks, oil, rust and tyre marks), 768 in a tile
    bx_wall_panel   one precast wall panel, 1 x 1 across the panel (boxyard_map maps each panel onto it)
    bx_line_yellow, bx_line_white   worn floor paint, alpha tested, 192 x 4 in
    bx_galv         galvanised steel: posts, wire, locking bars
    bx_rust         rusty steel: the pipe stacks
    bx_drum_blue, bx_drum_red, bx_skip_green   painted steel: drums and the skip
    bx_hdpe         an IBC's white plastic tank
and flat paints (PAINTED): cones, bins, rubber.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert( 0, str( Path( __file__ ).resolve().parent ) )
import terrain_textures as T  # noqa: E402

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/boxyard"
RESOURCE_DIR = "materials/boxyard"
DEFAULT_AO = "materials/default/default_ao.tga"
FONT = ROOT / "Assets/fonts/Dinish-Bold.ttf"
CAP = 0.69          # Dinish Bold's cap height over its em
CAP_TOP = 0.34      # and where a capital's top sits below the em's

# ---------------------------------------------------------------------------------------------------------------------
# The 20 ft container (ISO 668 1CC), in inches. boxyard_map builds it from these.

LENGTH = 238.6              # 6058 mm
WIDTH = 96.0                # 2438 mm
HEIGHT = 102.0              # 2591 mm
POST = 7.0                  # corner posts, along the length and across
BOTTOM_RAIL = 6.0           # the bottom side rail's height
TOP_RAIL = 97.0             # the top side rail's underside
CASTING = ( 7.0, 6.4, 4.6 ) # corner castings (ISO 1161): along, across, high
PITCH = 10.94               # the side walls' corrugation: one pitch...
DEPTH = 1.42                # ...its depth...
OUTER_FLAT = 2.83           # ...and its outer flat, slopes (each, along the wall) and inner flat
SLOPE = 2.72
INNER_FLAT = 2.68
PITCHES = 20                # pitches along each side, centred between the posts
SKIN = 0.25                 # the outer flats sit this far inside the rails' faces
POCKETS = ( -40.35, 40.35 ) # forklift pockets in the bottom side rails (centres, along the length)
POCKET = ( 14.0, 4.5 )      # and their openings
DOOR_HEADER = 95.0          # the door end: the header's underside...
DOOR_SILL = 6.5             # ...the sill's top...
DOOR_POST = 41.0            # ...and the posts' inner faces, across
BARS = ( 10.5, 30.5 )       # each leaf's two locking bars, out from the middle
INSIDE_HEIGHT = 94.0        # inside: the floor's top to the ceiling
FLOOR = 6.0                 # the floor's top

COLOURS = { "red": ( 132, 40, 33 ), "blue": ( 34, 62, 106 ), "green": ( 44, 92, 66 ), "orange": ( 198, 94, 32 ),
            "grey": ( 122, 126, 128 ) }
# colour, variant -> owner code, serial, seed, how sun-bleached, how old (rust and grime), roof code
CONTAINERS = {
    ( "red", "a" ): ( "BXYU", "482107", 11, 0.55, 0.7, False ),
    ( "red", "b" ): ( "QZLU", "715093", 12, 0.35, 1.0, True ),
    ( "blue", "a" ): ( "HCXU", "203318", 13, 0.45, 0.6, False ),
    ( "blue", "b" ): ( "XKWU", "569241", 14, 0.65, 0.9, True ),
    ( "green", "a" ): ( "ZJRU", "330872", 15, 0.5, 0.8, False ),
    ( "green", "b" ): ( "BXYU", "618455", 16, 0.3, 0.55, True ),
    ( "orange", "a" ): ( "VQXU", "904126", 17, 0.6, 0.75, False ),
    ( "grey", "a" ): ( "KZQU", "127764", 18, 0.4, 0.85, True ),
}
ATLAS = ( 4096, 2048 )
REGIONS = { "side_a": ( 0, 0, 2048, 1024 ), "side_b": ( 2048, 0, 2048, 1024 ), "doors": ( 0, 1024, 1024, 1024 ),
            "front": ( 1024, 1024, 1024, 1024 ), "roof": ( 2048, 1024, 2048, 1024 ) }
# The inside's atlas: side wall, ceiling, floor, the front wall's inside, the doors' insides (pixels: x, y, w, h).
INSIDE = { "wall": ( 0, 0, 2048, 1024 ), "ceiling": ( 2048, 0, 2048, 1024 ), "floor": ( 0, 1024, 2048, 1024 ),
           "front": ( 2048, 1024, 1024, 1024 ), "doors": ( 3072, 1024, 1024, 1024 ) }


SCALE = 1.0                 # --scale draws everything smaller, for previews


def px( n ):
    return max( 8, int( round( n * SCALE ) ) )


def set_scale( scale ):
    """ Draws at scale times the size: the atlases' layout keeps its shares. """
    global SCALE, ATLAS
    SCALE = scale
    ATLAS = ( px( 4096 ), px( 2048 ) )
    for table in ( REGIONS, INSIDE ):
        for key, ( x, y, w, h ) in list( table.items() ):
            table[key] = ( px( x ) if x else 0, px( y ) if y else 0, px( w ), px( h ) )


def region_uv( name, s, t, regions=None ):
    """ ( u, v ) in an atlas (REGIONS', or INSIDE's) for ( s, t ) 0..1 across a region (s to the right, t up), v up
    from the picture's foot. """
    regions = regions or REGIONS
    size = ATLAS
    x, y, w, h = regions[name]
    return ( x + s * w ) / size[0], 1.0 - ( y + ( 1.0 - t ) * h ) / size[1]


# ---------------------------------------------------------------------------------------------------------------------
# Helpers. Fields are float32, in inches where they're heights.

def unit( a ):
    return ( ( a - a.mean() ) / ( a.std() + 1e-9 ) ).astype( np.float32 )


def noise( rng, shape, ppi, beta, longest, shortest=None ):
    """ Periodic fractal noise (unit deviation) with wavelengths from longest to shortest inches, on a picture of
    ppi = ( across, up ) pixels to the inch, which may differ. """
    h, w = shape
    white = rng.standard_normal( ( h, w ), dtype=np.float32 )
    spectrum = np.fft.rfft2( white )
    fy = ( np.fft.fftfreq( h ) * ppi[1] )[:, None]
    fx = ( np.fft.rfftfreq( w ) * ppi[0] )[None, :]
    f = np.sqrt( fx * fx + fy * fy )
    f[0, 0] = 1.0
    fmin = 1.0 / longest
    amp = f ** ( -beta / 2.0 ) * np.clip( ( f - fmin * 0.5 ) / ( fmin * 0.5 ), 0.0, 1.0 )
    if shortest:
        amp *= np.clip( 2.0 - f * shortest, 0.0, 1.0 )
    amp[0, 0] = 0.0
    return unit( np.fft.irfft2( spectrum * amp, s=( h, w ) ) )


smoothstep = T.smoothstep


def lin( rgb ):
    return T.srgb_to_linear( np.asarray( rgb, np.float32 ) ).astype( np.float32 )


def mix( a, b, t ):
    t = np.asarray( t, np.float32 )
    if t.ndim == 2 and np.ndim( a ) == 3:
        t = t[..., None]
    return a + ( b - a ) * t


def normals( height, ppi ):
    """ OpenGL tangent normals (green up the picture) from heights in inches. """
    gy, gx = np.gradient( height )
    n = np.stack( [ -gx * ppi[0], gy * ppi[1], np.ones_like( height ) ], -1 )
    return n / np.linalg.norm( n, axis=-1, keepdims=True )


class Canvas:
    """ Strokes, shapes and lettering drawn at ss times the size, in inches from a region's corner (x right, z up),
    read back as 0..1 coverage. Lettering is drawn square and stretched to the region's pixels. """

    def __init__( self, shape, ppi, origin=( 0.0, 0.0 ), top=None, ss=3 ):
        self.h, self.w = shape
        self.ppi, self.ss, self.origin = ppi, ss, origin
        self.top = top if top is not None else origin[1] + self.h / ppi[1]
        self.image = Image.new( "L", ( self.w * ss, self.h * ss ), 0 )
        self.draw = ImageDraw.Draw( self.image )

    def p( self, x, z ):
        return ( ( x - self.origin[0] ) * self.ppi[0] * self.ss, ( self.top - z ) * self.ppi[1] * self.ss )

    def line( self, points, width, value=1.0 ):
        self.draw.line( [ self.p( x, z ) for x, z in points ], fill=int( value * 255 ),
                        width=max( 1, int( round( width * self.ppi[1] * self.ss ) ) ), joint="curve" )

    def ellipse( self, x, z, rx, rz, value=1.0 ):
        ( x0, y0 ), ( x1, y1 ) = self.p( x - rx, z + rz ), self.p( x + rx, z - rz )
        self.draw.ellipse( ( x0, y0, x1, y1 ), fill=int( value * 255 ) )

    def rect( self, x0, z0, x1, z1, value=1.0, outline=None, width=0.0 ):
        ( a, b ), ( c, d ) = self.p( x0, z1 ), self.p( x1, z0 )
        if outline is None:
            self.draw.rectangle( ( a, b, c, d ), fill=int( value * 255 ) )
        else:
            self.draw.rectangle( ( a, b, c, d ), outline=int( value * 255 ),
                                 width=max( 1, int( round( width * self.ppi[1] * self.ss ) ) ) )

    def polygon( self, points, value=1.0 ):
        self.draw.polygon( [ self.p( x, z ) for x, z in points ], fill=int( value * 255 ) )

    def text( self, x, z, text, cap, align="left", spacing=0.12 ):
        """ Lettering cap inches high, its capitals' top-left (or top-right, align="right") at x, z. Returns its width. """
        scale = self.ppi[1] * self.ss
        font = ImageFont.truetype( str( FONT ), max( 6, int( round( cap / CAP * scale ) ) ) )
        gap = spacing * cap * scale
        widths = [ font.getlength( ch ) for ch in text ]
        total = sum( widths ) + gap * ( len( text ) - 1 )
        size = font.size
        sheet = Image.new( "L", ( int( total ) + 4, int( size * 1.2 ) + 4 ), 0 )
        d = ImageDraw.Draw( sheet )
        cx = 2.0
        for ch, cw in zip( text, widths ):
            d.text( ( cx, 2 ), ch, font=font, fill=255 )
            cx += cw + gap
        stretch = self.ppi[0] / self.ppi[1]
        sheet = sheet.resize( ( max( 1, int( round( sheet.width * stretch ) ) ), sheet.height ), Image.LANCZOS )
        width_in = sheet.width / ( self.ppi[0] * self.ss )
        left = x - width_in if align == "right" else x
        px, py = self.p( left, z )
        py -= CAP_TOP * size + 2
        self.image.paste( 255, ( int( px ), int( py ) ), sheet )
        return width_in

    def result( self ):
        a = np.asarray( self.image, np.float32 ) / 255.0
        s = self.ss
        return a.reshape( self.h, s, self.w, s ).mean( axis=( 1, 3 ) )


class Region:
    """ A face's picture: x across (inches, left to right), z up, its paint (linear), roughness and height. """

    def __init__( self, rng, shape, xr, zr ):
        self.rng, self.shape = rng, shape
        h, w = shape
        self.xr, self.zr = xr, zr
        self.ppi = ( w / ( xr[1] - xr[0] ), h / ( zr[1] - zr[0] ) )
        self.x = ( xr[0] + ( np.arange( w, dtype=np.float32 ) + 0.5 ) / self.ppi[0] )[None, :]
        self.z = ( zr[1] - ( np.arange( h, dtype=np.float32 ) + 0.5 ) / self.ppi[1] )[:, None]
        self.colour = np.zeros( ( h, w, 3 ), np.float32 )
        self.rough = np.full( shape, 0.5, np.float32 )
        self.height = np.zeros( shape, np.float32 )

    def noise( self, beta, longest, shortest=None ):
        return noise( self.rng, self.shape, self.ppi, beta, longest, shortest )

    def canvas( self ):
        return Canvas( self.shape, self.ppi, ( self.xr[0], self.zr[0] ), self.zr[1] )

    def full( self, a ):
        return np.broadcast_to( a, self.shape ).astype( np.float32 )

    def lay( self, colour, amount, rough=None, height=None, rough_amount=None ):
        """ colour (linear rgb, or a picture) over the paint by amount, with its roughness and a height offset. """
        amount = self.full( amount )
        self.colour = mix( self.colour, np.asarray( colour, np.float32 ), amount )
        if rough is not None:
            self.rough = mix( self.rough, rough, amount if rough_amount is None else rough_amount )
        if height is not None:
            self.height += height * amount

    def streaks( self, runs, sharp=1.0 ):
        """ Stains running down from points: ( x, top z, length, width, strength ) each, in inches. """
        field = np.zeros( self.shape, np.float32 )
        h, w = self.shape
        px, pz = self.ppi
        for x0, z0, length, width, strength in runs:
            r0 = int( max( 0, ( self.zr[1] - z0 ) * pz ) )
            r1 = int( min( h, ( self.zr[1] - z0 + length ) * pz ) )
            if r1 <= r0 + 1:
                continue
            sigma = max( 0.6, width * 0.5 * px )
            c = ( x0 - self.xr[0] ) * px
            c0, c1 = int( max( 0, c - 6 * sigma - 8 ) ), int( min( w, c + 6 * sigma + 8 ) )
            if c1 <= c0:
                continue
            rows = np.arange( r0, r1, dtype=np.float32 )[:, None]
            cols = np.arange( c0, c1, dtype=np.float32 )[None, :]
            t = ( rows - r0 ) / ( r1 - r0 )
            drift = np.cumsum( self.rng.normal( 0, 0.04 * px, r1 - r0 ) ).astype( np.float32 )[:, None]
            spread = sigma * ( 1.0 + 0.9 * t )
            across = np.exp( -0.5 * ( ( cols - c - drift ) / spread ) ** 2 )
            along = ( 1.0 - t ) ** ( 1.2 * sharp ) * ( 0.65 + 0.35 * np.cos( t * self.rng.uniform( 6, 18 ) + self.rng.uniform( 0, 6 ) ) )
            part = strength * across * along
            field[r0:r1, c0:c1] = 1.0 - ( 1.0 - field[r0:r1, c0:c1] ) * ( 1.0 - part )
        return field

    def dents( self, count, radius, depth, region=None ):
        """ Soft dents: count of them, radius and depth ranges in inches, inside region ( x0, x1, z0, z1 ). """
        x0, x1, z0, z1 = region or ( self.xr[0], self.xr[1], self.zr[0], self.zr[1] )
        for _ in range( count ):
            cx, cz = self.rng.uniform( x0, x1 ), self.rng.uniform( z0, z1 )
            r = self.rng.uniform( *radius )
            sx, sz = r * self.rng.uniform( 0.6, 1.5 ), r * self.rng.uniform( 0.6, 1.5 )
            d = self.rng.uniform( *depth )
            self.height -= d * np.exp( -0.5 * ( ( ( self.x - cx ) / sx ) ** 2 + ( ( self.z - cz ) / sz ) ** 2 ) )

    def scrapes( self, groups, region, length=( 20, 90 ), slope=0.06, lines=( 2, 7 ) ):
        """ Scrapes from cargo and forks: bunches of near-parallel strokes. Returns ( scuffs, gouges ). """
        light, deep = self.canvas(), self.canvas()
        x0, x1, z0, z1 = region
        for _ in range( groups ):
            sx, sz = self.rng.uniform( x0, x1 ), self.rng.uniform( z0, z1 )
            run = self.rng.uniform( *length ) * self.rng.choice( [ -1, 1 ] )
            tilt = self.rng.normal( 0, slope )
            for _ in range( self.rng.integers( *lines ) ):
                off = self.rng.normal( 0, 0.5 )
                start = self.rng.uniform( 0, 0.3 ) * run
                end = run * self.rng.uniform( 0.5, 1.0 )
                pts = [ ( sx + start + k * ( end - start ) / 6, sz + off + tilt * ( start + k * ( end - start ) / 6 )
                          + self.rng.normal( 0, 0.05 ) ) for k in range( 7 ) ]
                if self.rng.random() < 0.4:
                    deep.line( pts, self.rng.uniform( 0.06, 0.22 ) )
                else:
                    light.line( pts, self.rng.uniform( 0.1, 0.5 ), self.rng.uniform( 0.4, 1.0 ) )
        return light.result(), deep.result()

    def maps( self ):
        return self.colour, np.clip( self.rough, 0.04, 1.0 ), self.height


# Weathering colours (sRGB): rust fresh and dark, a rust stain running down paint, primer, bare steel, road grime.
RUST = lin( ( 142, 66, 30 ) )
RUST_DARK = lin( ( 72, 40, 24 ) )
RUST_STAIN = lin( ( 118, 60, 30 ) )
PRIMER = lin( ( 118, 112, 102 ) )
BARE = lin( ( 128, 128, 126 ) )
GRIME = lin( ( 58, 52, 44 ) )
STENCIL = lin( ( 228, 228, 222 ) )


def chalked( colour, amount ):
    """ Paint the sun has faded: lighter, greyer, chalky. """
    grey = colour.mean( -1, keepdims=True )
    return mix( colour, grey * 1.18 + 0.018, amount )


# ---------------------------------------------------------------------------------------------------------------------
# The container's faces

def corrugation( x ):
    """ The side wall's profile at x inches along the box: depth 0 (outer flat) to 1 (inner), the distance to the
    nearest outer bend and to the nearest inner bend, and the middle of the inner flats (1 there). """
    start = -PITCHES * PITCH / 2
    t = x - start
    k = np.floor( t / PITCH )
    local = t - k * PITCH
    inside = ( k >= 0 ) & ( k < PITCHES )
    a = OUTER_FLAT / 2
    b, c, d = a + SLOPE, a + SLOPE + INNER_FLAT, a + 2 * SLOPE + INNER_FLAT
    depth = np.where( local < a, 0.0, np.where( local < b, ( local - a ) / SLOPE, np.where( local < c, 1.0,
                      np.where( local < d, 1.0 - ( local - c ) / SLOPE, 0.0 ) ) ) )
    outer = np.minimum( np.abs( local - a ), np.abs( local - d ) )
    inner = np.minimum( np.abs( local - b ), np.abs( local - c ) )
    channel = np.clip( 1.0 - np.abs( local - ( b + c ) / 2 ) / ( INNER_FLAT / 2 ), 0.0, 1.0 )
    big = np.float32( 99.0 )
    return ( np.where( inside, depth, 0.0 ).astype( np.float32 ), np.where( inside, outer, big ).astype( np.float32 ),
             np.where( inside, inner, big ).astype( np.float32 ), np.where( inside, channel, 0.0 ).astype( np.float32 ) )


def check_digit( code ):
    """ ISO 6346's check digit for an owner code and serial ("BXYU482107"). """
    values, v = {}, 10
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if v % 11 == 0:
            v += 1
        values[ch] = v
        v += 1
    total = sum( ( values[ch] if ch.isalpha() else int( ch ) ) * 2 ** i for i, ch in enumerate( code ) )
    return total % 11 % 10


def base_paint( r, colour, bleach, top_bias=0.65 ):
    """ The box's paint: mottled, a little uneven in hue, chalked by the sun (more higher up), with repaint patches. """
    c0 = lin( colour )
    mottle = r.noise( 2.6, 80, 6 )
    fine = r.noise( 1.0, 1.5, 0.12 )
    drift = r.noise( 3.0, 140, 24 )
    lum = 1.0 + 0.055 * mottle + 0.018 * fine
    r.colour = c0[None, None, :] * lum[..., None] * ( 1.0 + 0.03 * drift[..., None] * np.array( [ 1.0, 0.1, -0.8 ], np.float32 ) )
    sun = bleach * ( 1.0 - top_bias + top_bias * smoothstep( 8.0, r.zr[1], r.z ) ) * ( 0.75 + 0.25 * smoothstep( -1.5, 1.5, r.noise( 2.4, 60, 8 ) ) )
    r.colour = mix( r.colour, chalked( r.colour, 1.0 ), r.full( sun ) * 0.75 )
    r.rough = r.full( 0.46 + 0.2 * sun + 0.03 * mottle )
    return c0


def repaint( r, c0, count, region, bleach=0.5 ):
    """ Patches of later paint, rolled over damage or old markings: a slightly different shade, faded less, crisper. """
    x0, x1, z0, z1 = region
    roller = r.noise( 1.6, 3.0, 0.3 )
    c0 = chalked( c0[None, None, :], bleach * 0.45 )[0, 0]
    for _ in range( count ):
        w_, h_ = r.rng.uniform( 6, 40 ), r.rng.uniform( 5, 30 )
        cx, cz = r.rng.uniform( x0, x1 ), r.rng.uniform( z0, z1 )
        inside = np.minimum( w_ / 2 - np.abs( r.x - cx ), h_ / 2 - np.abs( r.z - cz ) )
        mask = smoothstep( -0.3, 0.3, inside )
        shade = c0 * r.rng.uniform( 0.9, 1.02 ) * ( 1.0 + r.rng.normal( 0, 0.03, 3 ).astype( np.float32 ) )
        r.lay( shade[None, None, :] * ( 1.0 + 0.025 * roller[..., None] ), mask, rough=0.36, height=0.01 )


def markings( r, draw ):
    """ Stencilled white paint, worn: draw( canvas ) letters it. Returns the coverage. """
    cv = r.canvas()
    draw( cv )
    cover = cv.result()
    wear = smoothstep( 0.6, 2.4, r.noise( 1.8, 6, 0.2 ) ) * 0.9 + smoothstep( 1.5, 3.0, r.noise( 1.0, 1.0, 0.1 ) )
    cover = cover * ( 1.0 - np.clip( wear, 0.0, 1.0 ) )
    r.lay( STENCIL * ( 0.92 + 0.05 * r.noise( 1.2, 3, 0.2 )[..., None] ), cover, rough=0.5, height=0.012 )
    return cover


def grime_and_rust( r, age, bottom=28.0, wall=None, sources=None ):
    """ Grime splashed up from the ground, rust breaking through low down and at knocks, and stains running down. """
    low = smoothstep( bottom, 0.0, r.z ) * ( 0.55 + 0.45 * smoothstep( -1.0, 1.5, r.noise( 2.0, 30, 2 ) ) )
    r.lay( GRIME * ( 1.0 + 0.2 * r.noise( 1.5, 4, 0.3 )[..., None] ), low * 0.55 * age, rough=0.75, rough_amount=low * 0.4 )
    blister = r.noise( 1.4, 6, 0.25 )
    spots = smoothstep( 2.6 - 0.4 * age, 3.4, r.noise( 1.3, 10, 0.4 ) + 1.1 * smoothstep( 16.0, 0.0, r.z ) * age )
    if wall is not None:
        spots *= wall
    rust_colour = mix( RUST_DARK[None, None, :] * np.ones( ( 1, 1, 3 ), np.float32 ), RUST, smoothstep( -1.0, 1.0, blister ) )
    r.lay( rust_colour, spots, rough=0.88, height=0.03 * ( 0.5 + 0.5 * blister ) )
    runs = list( sources or [] )
    ys, xs = np.nonzero( spots[:: 8, :: 8] > 0.5 )
    for k in r.rng.choice( len( xs ), size=min( len( xs ), 140 ), replace=False ) if len( xs ) else []:
        x = r.xr[0] + ( xs[k] * 8 + 4 ) / r.ppi[0]
        z = r.zr[1] - ( ys[k] * 8 + 4 ) / r.ppi[1]
        runs.append( ( x, z, r.rng.uniform( 4, 30 ) * age, r.rng.uniform( 0.4, 1.4 ), r.rng.uniform( 0.25, 0.6 ) ) )
    stain = r.streaks( runs ) * smoothstep( -2.0, 1.0, r.noise( 1.6, 8, 0.6 ) )
    r.lay( RUST_STAIN, np.clip( stain, 0.0, 0.85 ), rough=0.7, rough_amount=stain * 0.3 )
    return spots


def wear_through( r, scuff, gouge, chips, age ):
    """ Paint worn through: scuffs lighten it, gouges and chips show primer, bare steel or rust (chips mostly rust:
    they're old). """
    r.lay( chalked( r.colour, 0.6 ) * 1.1, scuff * 0.5, rough=0.4, rough_amount=scuff * 0.4 )
    old = smoothstep( -0.8, 0.8, r.noise( 1.5, 8, 0.4 ) + 1.2 * ( age - 0.6 ) + 1.5 * chips )
    under = mix( mix( PRIMER[None, None, :] * np.ones( ( 1, 1, 3 ), np.float32 ), BARE, smoothstep( 0.5, 1.5, r.noise( 1.2, 3, 0.3 ) ) ),
                 RUST, old )
    hole = np.clip( gouge + chips, 0.0, 1.0 )
    r.lay( under, hole, rough=0.6, height=-0.03 )


def container_side( rng, shape, colour, code, bleach, age, door_right ):
    r = Region( rng, shape, ( -LENGTH / 2, LENGTH / 2 ), ( 0.0, HEIGHT ) )
    c0 = base_paint( r, colour, bleach )
    depth, outer, inner, channel = corrugation( r.x )
    post = np.abs( r.x ) > LENGTH / 2 - POST
    wall = ( ( r.z > BOTTOM_RAIL ) & ( r.z < TOP_RAIL ) & ~post ).astype( np.float32 )
    rails = 1.0 - wall
    # The inner corners hold a little shade and dirt; the rails and posts are heavier steel, painted the same.
    r.colour *= ( 1.0 - 0.06 * np.exp( -inner / 0.35 ) * wall )[..., None]
    repaint( r, c0, rng.integers( 0, 4 ), ( -LENGTH / 2 + 15, LENGTH / 2 - 15, 12, 92 ), bleach )
    # Weld seams between the wall's sheets, at inner flats.
    for k in range( 0, PITCHES, 4 ):
        seam_x = -PITCHES * PITCH / 2 + k * PITCH + OUTER_FLAT / 2 + SLOPE + INNER_FLAT / 2
        if k == 0:
            continue
        bead = np.exp( -0.5 * ( ( r.x - seam_x ) / 0.18 ) ** 2 ) * wall
        r.height += 0.06 * bead
        r.colour *= ( 1.0 - 0.12 * bead )[..., None]
    # Markings near the door end's top corner: owner code, serial and check digit, then the size and type code.
    digit = check_digit( code[0] + code[1] )
    edge = LENGTH / 2 - 16.0
    label = f"{code[0]} {code[1]}"

    def letter( cv ):
        if door_right:
            right = edge - 5.6                            # the boxed digit ends at the edge
            left = right - cv.text( right, 92.0, label, 4.2, align="right" )
        else:
            left = -edge
            right = left + cv.text( left, 92.0, label, 4.2 )
        box = right + 1.0
        cv.text( box + 0.9, 92.0, str( digit ), 4.2 )
        cv.rect( box, 87.0, box + 4.4, 93.0, outline=True, width=0.4 )
        cv.text( left + 0.2, 85.0, "22G1", 3.4 )

    markings( r, letter )
    # Knocks: chips along the outer bends, scrapes, dents.
    chip = smoothstep( 2.6, 3.4, r.noise( 1.2, 3, 0.15 ) + 1.3 * np.exp( -outer / 0.25 ) + 0.4 * age ) * ( 0.3 + 0.7 * wall )
    scuff, gouge = r.scrapes( rng.integers( 5, 11 ), ( -LENGTH / 2, LENGTH / 2, 8, 70 ) )
    wear_through( r, scuff, gouge, chip, age )
    r.dents( rng.integers( 3, 8 ), ( 4, 16 ), ( 0.08, 0.4 ), ( -LENGTH / 2 + 10, LENGTH / 2 - 10, 10, 90 ) )
    # Forklift pockets: openings in the bottom rail, dark and rusty inside.
    for px_ in POCKETS:
        open_ = smoothstep( 0.0, 0.15, np.minimum( POCKET[0] / 2 - np.abs( r.x - px_ ), POCKET[1] / 2 - np.abs( r.z - 3.0 ) ) )
        r.lay( RUST_DARK * 0.25, open_, rough=0.9, height=-1.6 )
    # Corner castings, with their side apertures.
    for sx in ( -1, 1 ):
        for cz in ( CASTING[2] / 2, HEIGHT - CASTING[2] / 2 ):
            cx = sx * ( LENGTH / 2 - CASTING[0] / 2 )
            cast = smoothstep( 0.0, 0.1, np.minimum( CASTING[0] / 2 - np.abs( r.x - cx ), CASTING[2] / 2 - np.abs( r.z - cz ) ) )
            r.lay( mix( RUST_DARK[None, None, :] * 1.3, r.colour, 0.45 ), cast * 0.8, rough=0.8 )
            hole = smoothstep( 0.0, 0.1, 1.0 - np.sqrt( ( ( r.x - cx ) / 1.9 ) ** 2 + ( ( r.z - cz ) / 1.25 ) ** 2 ) )
            r.lay( RUST_DARK * 0.15, hole, rough=0.9, height=-1.2 )
    # Grime from the top rail down the inner flats, rust low down and its stains.
    grime_runs = [ ( float( -PITCHES * PITCH / 2 + ( k + 0.5 ) * PITCH ) + rng.normal( 0, 0.4 ), TOP_RAIL, rng.uniform( 25, 95 ),
                     rng.uniform( 1.2, 2.6 ), rng.uniform( 0.25, 0.6 ) * age ) for k in range( PITCHES ) if rng.random() < 0.8 ]
    dark = r.streaks( grime_runs, sharp=0.5 )
    r.lay( GRIME, np.clip( dark, 0, 0.7 ) * wall )
    under_rail = smoothstep( TOP_RAIL - 14.0, TOP_RAIL, r.z ) * wall * ( 0.6 + 0.4 * smoothstep( -1, 1, r.noise( 2, 30, 3 ) ) )
    r.lay( GRIME, under_rail * 0.35 * age )
    rust_runs = [ ( rng.uniform( -LENGTH / 2, LENGTH / 2 ), TOP_RAIL + rng.uniform( -1, 2 ), rng.uniform( 10, 55 ) * age,
                    rng.uniform( 0.5, 1.8 ), rng.uniform( 0.4, 0.8 ) ) for _ in range( int( 14 * age ) + 4 ) ]
    for sx in ( -1, 1 ):
        for cz in ( HEIGHT - CASTING[2], ):
            rust_runs.append( ( sx * ( LENGTH / 2 - 3.5 ), cz, rng.uniform( 10, 50 ), 2.0, 0.6 ) )
    grime_and_rust( r, age, wall=None, sources=rust_runs )
    rust_rail = smoothstep( 0.3, 1.8, r.noise( 1.6, 12, 0.3 ) + 1.5 * age ) * smoothstep( BOTTOM_RAIL + 1, 0, r.z ) * rails
    r.lay( RUST, rust_rail * 0.8, rough=0.9, height=0.02 )
    return r.maps()


def door_end( rng, shape, colour, code, bleach, age ):
    r = Region( rng, shape, ( -WIDTH / 2, WIDTH / 2 ), ( 0.0, HEIGHT ) )
    c0 = base_paint( r, colour, bleach, top_bias=0.4 )
    leaf = ( np.abs( r.x ) > 0.2 ) & ( np.abs( r.x ) < DOOR_POST - 0.4 ) & ( r.z > DOOR_SILL ) & ( r.z < DOOR_HEADER )
    leaf = leaf.astype( np.float32 )
    # Each leaf's panel: a frame round five raised horizontal ribs.
    frame = 2.6
    lx = np.abs( r.x )
    inner_panel = ( ( lx > 0.2 + frame ) & ( lx < DOOR_POST - 0.4 - frame ) & ( r.z > DOOR_SILL + frame ) & ( r.z < DOOR_HEADER - frame ) ).astype( np.float32 )
    span = ( DOOR_HEADER - frame ) - ( DOOR_SILL + frame )
    phase = ( r.z - DOOR_SILL - frame ) / span * 5.0
    rib = smoothstep( 0.12, 0.3, phase % 1.0 ) * smoothstep( 0.88, 0.7, phase % 1.0 )
    r.height += ( 0.8 * rib - 0.3 ) * inner_panel
    r.colour *= ( 1.0 - 0.05 * ( 1 - rib ) * inner_panel )[..., None]
    # The gaps: between the leaves, and each leaf and its post; the gaskets in black rubber.
    gap = np.exp( -0.5 * ( r.x / 0.22 ) ** 2 ) + np.exp( -0.5 * ( ( lx - ( DOOR_POST - 0.2 ) ) / 0.2 ) ** 2 )
    gap = np.clip( gap, 0, 1 ) * ( ( r.z > DOOR_SILL - 0.3 ) & ( r.z < DOOR_HEADER + 0.3 ) )
    gasket = np.clip( np.exp( -0.5 * ( r.x / 0.7 ) ** 2 ) - gap, 0, 1 ) * leaf
    r.lay( lin( ( 22, 22, 22 ) ), gasket * 0.9, rough=0.8 )
    r.lay( lin( ( 6, 6, 6 ) ), gap, rough=0.9, height=-0.8 )
    edge = np.clip( np.exp( -0.5 * ( ( r.z - DOOR_HEADER ) / 0.25 ) ** 2 ) + np.exp( -0.5 * ( ( r.z - DOOR_SILL ) / 0.25 ) ** 2 ), 0, 1 ) * ( lx < DOOR_POST )
    r.lay( lin( ( 10, 10, 10 ) ), edge * 0.85, height=-0.5 )
    repaint( r, c0, rng.integers( 0, 3 ), ( -36, 36, 15, 85 ), bleach )
    # Markings: the code on the right leaf, the weights on the left, and the CSC plate.
    digit = check_digit( code[0] + code[1] )
    weights = [ ( "MAX. GROSS", "30,480 KG", "67,200 LB" ), ( "TARE", "2,230 KG", "4,920 LB" ),
                ( "MAX. PAYLOAD", "28,250 KG", "62,280 LB" ), ( "CU. CAP.", "33.2 CU.M", "1,172 CU.FT" ) ]

    def letter( cv ):
        # The right leaf: owner code over the serial and its boxed digit, then the size and type code.
        cv.text( 5.5, 88.0, code[0], 3.6 )
        box = 5.5 + cv.text( 5.5, 82.5, code[1], 3.6 ) + 0.9
        cv.text( box + 0.75, 82.5, str( digit ), 3.6 )
        cv.rect( box, 78.2, box + 3.8, 83.4, outline=True, width=0.35 )
        cv.text( 5.7, 76.0, "22G1", 3.0 )
        # The left leaf: the weights and capacity.
        for k, ( name, a, b ) in enumerate( weights ):
            z = 80.0 - k * 2.4
            cv.text( -38.0, z, name, 1.2 )
            cv.text( -13.5, z, a, 1.2, align="right" )
            cv.text( -1.5, z, b, 1.2, align="right" )

    markings( r, letter )
    plate = r.canvas()
    plate.rect( -37.0, 26.0, -29.0, 31.0 )
    plate.rect( -27.5, 26.6, -21.5, 30.4 )
    pm = plate.result()
    r.lay( lin( ( 168, 170, 166 ) ) * ( 1.0 + 0.06 * r.noise( 1.2, 2, 0.1 )[..., None] ), pm, rough=0.42, height=0.08 )
    lines_ = r.canvas()
    for k in range( 8 ):
        lines_.line( [ ( -36.3, 30.2 - k * 0.5 ), ( -36.3 + rng.uniform( 3.5, 6.8 ), 30.2 - k * 0.5 ) ], 0.14 )
    for k in range( 5 ):
        lines_.line( [ ( -27.0, 29.8 - k * 0.6 ), ( -27.0 + rng.uniform( 2.5, 5.0 ), 29.8 - k * 0.6 ) ], 0.14 )
    for cx, cz in ( ( -36.6, 26.4 ), ( -29.4, 26.4 ), ( -36.6, 30.6 ), ( -29.4, 30.6 ) ):
        lines_.ellipse( cx, cz, 0.18, 0.18 )
    r.lay( lin( ( 60, 62, 62 ) ), lines_.result() * pm * 0.8 )
    # Rust under the bar brackets and hinges, grime low down, knocks round the handles.
    runs = []
    for sx in ( -1, 1 ):
        for bx in BARS:
            for bz in ( 15.0, 46.0, 78.0 ):
                runs.append( ( sx * bx + rng.normal( 0, 0.4 ), bz, rng.uniform( 6, 26 ) * age, rng.uniform( 0.8, 1.6 ), 0.55 ) )
        for hz in ( 12.0, 33.0, 64.0, 85.0 ):
            runs.append( ( sx * ( DOOR_POST - 1.2 ), hz, rng.uniform( 8, 30 ) * age, 1.4, 0.6 ) )
    chip = smoothstep( 2.2, 3.0, r.noise( 1.2, 3, 0.15 ) + 0.6 * age + 1.4 * sum(
        np.exp( -0.5 * ( ( lx - b ) / 2.0 ) ** 2 ) * np.exp( -0.5 * ( ( r.z - 46.0 ) / 5.0 ) ** 2 ) for b in BARS ) )
    scuff, gouge = r.scrapes( rng.integers( 3, 7 ), ( -40, 40, 8, 60 ), length=( 8, 40 ), slope=0.3 )
    wear_through( r, scuff, gouge, chip, age )
    r.dents( rng.integers( 2, 5 ), ( 3, 10 ), ( 0.05, 0.25 ), ( -38, 38, 10, 90 ) )
    grime_and_rust( r, age, bottom=22.0, sources=runs )
    post = ( lx > DOOR_POST ).astype( np.float32 )
    rust_post = smoothstep( 0.8, 2.2, r.noise( 1.6, 10, 0.3 ) + 1.2 * age ) * ( post + smoothstep( DOOR_SILL + 1, 0, r.z ) )
    r.lay( RUST, np.clip( rust_post, 0, 1 ) * 0.7, rough=0.9, height=0.02 )
    return r.maps()


def front_end( rng, shape, colour, bleach, age ):
    r = Region( rng, shape, ( -WIDTH / 2, WIDTH / 2 ), ( 0.0, HEIGHT ) )
    c0 = base_paint( r, colour, bleach, top_bias=0.4 )
    lx = np.abs( r.x )
    wall = ( ( lx < DOOR_POST ) & ( r.z > BOTTOM_RAIL ) & ( r.z < TOP_RAIL ) ).astype( np.float32 )
    # The front wall's five vertical corrugations, 1.4 in deep.
    ribs = 5
    t = ( r.x + DOOR_POST ) / ( 2 * DOOR_POST ) * ribs
    f = t % 1.0
    prof = smoothstep( 0.1, 0.32, f ) * smoothstep( 0.9, 0.68, f )
    r.height += 1.4 * prof * wall
    r.colour *= ( 1.0 - 0.07 * np.exp( -np.minimum( np.abs( f - 0.1 ), np.abs( f - 0.9 ) ) * ( 2 * DOOR_POST / ribs ) / 0.4 ) * wall )[..., None]
    repaint( r, c0, rng.integers( 0, 2 ), ( -36, 36, 15, 85 ), bleach )
    runs = [ ( ( k + 0.5 ) / ribs * 2 * DOOR_POST - DOOR_POST, TOP_RAIL, rng.uniform( 20, 80 ), 1.6, 0.3 * age ) for k in range( ribs ) ]
    dark = r.streaks( runs, sharp=0.6 )
    r.lay( GRIME, np.clip( dark, 0, 0.6 ) * wall )
    chip = smoothstep( 2.2, 3.0, r.noise( 1.2, 3, 0.15 ) + 0.6 * age + 1.2 * np.exp( -np.minimum( np.abs( f - 0.32 ), np.abs( f - 0.68 ) ) * 25 ) * wall )
    scuff, gouge = r.scrapes( rng.integers( 2, 5 ), ( -40, 40, 8, 60 ), length=( 8, 40 ), slope=0.2 )
    wear_through( r, scuff, gouge, chip, age )
    r.dents( rng.integers( 1, 4 ), ( 4, 12 ), ( 0.05, 0.3 ), ( -38, 38, 10, 90 ) )
    sources = [ ( sx * ( DOOR_POST + 3.5 ), HEIGHT - CASTING[2], rng.uniform( 10, 40 ), 2.0, 0.6 ) for sx in ( -1, 1 ) ]
    grime_and_rust( r, age, bottom=22.0, sources=sources )
    post = ( ( lx > DOOR_POST ) | ( r.z < BOTTOM_RAIL ) | ( r.z > TOP_RAIL ) ).astype( np.float32 )
    rust_post = smoothstep( 0.8, 2.2, r.noise( 1.6, 10, 0.3 ) + 1.2 * age ) * post
    r.lay( RUST, rust_post * 0.7, rough=0.9, height=0.02 )
    for sx in ( -1, 1 ):
        for cz in ( CASTING[2] / 2, HEIGHT - CASTING[2] / 2 ):
            cx = sx * ( WIDTH / 2 - CASTING[1] / 2 )
            hole = smoothstep( 0.0, 0.1, 1.0 - np.sqrt( ( ( r.x - cx ) / 1.4 ) ** 2 + ( ( r.z - cz ) / 1.25 ) ** 2 ) )
            r.lay( RUST_DARK * 0.15, hole, rough=0.9, height=-1.2 )
    return r.maps()


def roof( rng, shape, colour, code, bleach, age, show_code ):
    r = Region( rng, shape, ( -LENGTH / 2, LENGTH / 2 ), ( -WIDTH / 2, WIDTH / 2 ) )
    c0 = lin( colour )
    mottle = r.noise( 2.4, 60, 4 )
    r.colour = chalked( c0[None, None, :] * ( 1.0 + 0.07 * mottle[..., None] ), min( 0.6, bleach * 0.8 + 0.15 ) )
    r.rough = r.full( 0.62 + 0.06 * mottle )
    sheet = ( ( np.abs( r.z ) < WIDTH / 2 - 2.2 ) & ( np.abs( r.x ) < LENGTH / 2 - POST ) ).astype( np.float32 )
    # Shallow ribs across the roof, every 9 in, 0.6 in deep.
    f = ( ( r.x + LENGTH / 2 ) / 9.0 ) % 1.0
    rib = smoothstep( 0.2, 0.42, f ) * smoothstep( 0.8, 0.58, f )
    r.height -= 0.6 * rib * sheet * smoothstep( WIDTH / 2 - 2.2, WIDTH / 2 - 6.0, np.abs( r.z ) )
    # Water stands in the ribs' troughs and along the sides: rings of dirt and rust where it dried.
    pond = smoothstep( 0.4, 1.8, r.noise( 2.6, 50, 6 ) + 1.0 * rib ) * sheet
    r.lay( GRIME * 1.4, pond * 0.45 * age, rough=0.8 )
    ring = np.clip( np.abs( np.gradient( ndimage.gaussian_filter( pond, 2.0 ) )[0] ) * 18, 0, 1 )
    r.lay( RUST_STAIN, ring * 0.5 * age )
    if show_code:
        digit = check_digit( code[0] + code[1] )
        markings( r, lambda cv: cv.text( -LENGTH / 2 + 18.0, 14.0, f"{code[0]} {code[1]} {digit}", 7.5 ) )
    rust = smoothstep( 2.4 - 0.6 * age, 3.2, r.noise( 1.5, 20, 0.4 ) + 0.9 * pond ) * sheet
    r.lay( mix( RUST_DARK[None, None, :] * np.ones( ( 1, 1, 3 ), np.float32 ), RUST, smoothstep( -1, 1, r.noise( 1.4, 5, 0.3 ) ) ),
           rust, rough=0.9, height=0.03 )
    scuff, gouge = r.scrapes( rng.integers( 3, 8 ), ( -LENGTH / 2, LENGTH / 2, -40, 40 ), length=( 10, 60 ), slope=0.5 )
    wear_through( r, scuff, gouge, 0.0, age )
    r.dents( rng.integers( 4, 10 ), ( 3, 14 ), ( 0.1, 0.5 ), ( -LENGTH / 2 + 10, LENGTH / 2 - 10, -40, 40 ) )
    edges = 1.0 - sheet
    r.lay( RUST, smoothstep( 0.6, 2.0, r.noise( 1.6, 8, 0.3 ) + age ) * edges * 0.8, rough=0.9 )
    for sx in ( -1, 1 ):
        for sz in ( -1, 1 ):
            cx, cz = sx * ( LENGTH / 2 - CASTING[0] / 2 ), sz * ( WIDTH / 2 - CASTING[1] / 2 )
            cast = smoothstep( 0.0, 0.1, np.minimum( CASTING[0] / 2 - np.abs( r.x - cx ), CASTING[1] / 2 - np.abs( r.z - cz ) ) )
            r.lay( RUST_DARK * 1.4, cast * 0.85, rough=0.85 )
            hole = smoothstep( 0.0, 0.1, 1.0 - np.sqrt( ( ( r.x - cx ) / 2.45 ) ** 2 + ( ( r.z - cz ) / 1.25 ) ** 2 ) )
            r.lay( RUST_DARK * 0.12, hole, rough=0.9, height=-1.5 )
    return r.maps()


def container_atlas( colour_name, variant ):
    code_letters, serial, seed, bleach, age, roof_code = CONTAINERS[( colour_name, variant )]
    colour = COLOURS[colour_name]
    code = ( code_letters, serial )
    rng = np.random.default_rng( seed )
    W, H = ATLAS
    colour_map = np.zeros( ( H, W, 3 ), np.float32 )
    rough = np.zeros( ( H, W ), np.float32 )
    normal = np.zeros( ( H, W, 3 ), np.float32 )
    parts = {
        "side_a": lambda shape: container_side( rng, shape, colour, code, bleach, age, True ),
        "side_b": lambda shape: container_side( rng, shape, colour, code, bleach, age, False ),
        "doors": lambda shape: door_end( rng, shape, colour, code, bleach, age ),
        "front": lambda shape: front_end( rng, shape, colour, bleach, age ),
        "roof": lambda shape: roof( rng, shape, colour, code, bleach, age, roof_code ),
    }
    for name, draw in parts.items():
        x, y, w, h = REGIONS[name]
        c, ro, he = draw( ( h, w ) )
        ppi = ( w / ( WIDTH if name in ( "doors", "front" ) else LENGTH ),
                h / ( WIDTH if name == "roof" else HEIGHT ) )
        colour_map[y:y + h, x:x + w] = c
        rough[y:y + h, x:x + w] = ro
        normal[y:y + h, x:x + w] = normals( he, ppi )
    return T.linear_to_srgb( colour_map ), rough, normal


# ---------------------------------------------------------------------------------------------------------------------
# The inside of an open container

def inside_atlas():
    rng = np.random.default_rng( 31 )
    W, H = ATLAS
    colour_map = np.zeros( ( H, W, 3 ), np.float32 )
    rough = np.zeros( ( H, W ), np.float32 )
    normal = np.zeros( ( H, W, 3 ), np.float32 )
    paint = lin( ( 186, 184, 174 ) )
    inside_len = LENGTH - 2 * 3.5

    def size( name ):
        return INSIDE[name][3], INSIDE[name][2]

    def wall( shape, xr, ribs_along=True, corrugated=True ):
        r = Region( rng, shape, xr, ( 0.0, INSIDE_HEIGHT ) )
        r.colour = paint[None, None, :] * ( 1.0 + 0.05 * r.noise( 2.4, 50, 4 )[..., None] + 0.015 * r.noise( 1.0, 1, 0.12 )[..., None] )
        r.rough = r.full( 0.55 )
        if corrugated:
            depth, outer, inner, channel = corrugation( r.x )
            r.height += DEPTH * ( 1.0 - depth )           # seen from inside, the inner flats are nearest
            r.colour *= ( 1.0 - 0.05 * np.exp( -outer / 0.4 ) )[..., None]
        scuff, gouge = r.scrapes( rng.integers( 8, 16 ), ( xr[0], xr[1], 4, 60 ), length=( 10, 70 ), slope=0.05 )
        r.lay( lin( ( 70, 66, 60 ) ), scuff * 0.45, rough=0.6 )
        wear_through( r, 0.0, gouge, 0.0, 0.8 )
        low = smoothstep( 14.0, 0.0, r.z ) * ( 0.6 + 0.4 * smoothstep( -1, 1.5, r.noise( 2, 20, 2 ) ) )
        r.lay( GRIME * 1.3, low * 0.6, rough=0.8 )
        runs = [ ( rng.uniform( *xr ), INSIDE_HEIGHT, rng.uniform( 10, 60 ), rng.uniform( 1, 3 ), rng.uniform( 0.15, 0.35 ) ) for _ in range( 10 ) ]
        r.lay( lin( ( 120, 96, 66 ) ), np.clip( r.streaks( runs, 0.5 ), 0, 0.5 ) )
        r.dents( rng.integers( 3, 8 ), ( 3, 12 ), ( 0.05, 0.3 ) )
        return r

    def floor( shape ):
        r = Region( rng, shape, ( -inside_len / 2, inside_len / 2 ), ( -46.0, 46.0 ) )
        grain = noise( rng, shape, r.ppi, 1.5, 30, 0.2 )
        streak = ndimage.gaussian_filter( r.noise( 1.0, 2, 0.15 ), ( 0.5, 0 ) )
        board = np.floor( ( r.x + inside_len / 2 ) / 45.7 ).astype( np.int32 )
        tone = rng.uniform( 0.82, 1.12, 8 ).astype( np.float32 )[np.broadcast_to( board, shape ) % 8]
        wood = lin( ( 128, 90, 58 ) )
        r.colour = wood[None, None, :] * ( tone * ( 1.0 + 0.08 * grain + 0.06 * streak ) )[..., None]
        r.rough = r.full( 0.78 )
        seam = np.exp( -0.5 * ( ( ( r.x + inside_len / 2 ) % 45.7 - 0.0 ) / 0.15 ) ** 2 )
        seam = np.maximum( seam, np.exp( -0.5 * ( ( ( r.x + inside_len / 2 ) % 45.7 - 45.7 ) / 0.15 ) ** 2 ) )
        r.lay( lin( ( 30, 22, 16 ) ), seam, height=-0.12 )
        # Bolts into the cross members, every 12 in along, 7 across.
        bolts = r.canvas()
        for k in range( int( inside_len // 12 ) ):
            bx = -inside_len / 2 + 6 + k * 12
            for j in range( 7 ):
                bolts.ellipse( bx, -39 + j * 13, 0.35, 0.35 )
        b = bolts.result()
        r.lay( lin( ( 70, 66, 60 ) ), b, rough=0.5, height=-0.04 )
        stains = smoothstep( 1.2, 3.0, r.noise( 2.6, 30, 3 ) )
        r.lay( lin( ( 52, 38, 26 ) ), stains * 0.45, rough=0.6 )
        tyres = r.canvas()
        for _ in range( 6 ):
            z0 = rng.uniform( -36, 36 )
            pts = [ ( x_, z0 + 6 * math.sin( x_ / rng.uniform( 30, 80 ) + rng.uniform( 0, 6 ) ) ) for x_ in np.linspace( -inside_len / 2, inside_len / 2, 30 ) ]
            tyres.line( pts, rng.uniform( 3, 6 ), rng.uniform( 0.3, 0.7 ) )
        r.lay( lin( ( 34, 30, 28 ) ), tyres.result() * 0.45 * smoothstep( -1, 1, r.noise( 1.5, 10, 0.5 ) ) )
        scuff, gouge = r.scrapes( 20, ( -inside_len / 2, inside_len / 2, -44, 44 ), length=( 6, 40 ), slope=0.6 )
        r.lay( lin( ( 150, 118, 84 ) ), np.clip( scuff + gouge, 0, 1 ) * 0.3, rough=0.85, height=-0.03 )
        return r

    regions = {
        "wall": wall( size( "wall" ), ( -inside_len / 2, inside_len / 2 ) ),
        "ceiling": wall( size( "ceiling" ), ( -inside_len / 2, inside_len / 2 ) ),
        "floor": floor( size( "floor" ) ),
        "front": wall( size( "front" ), ( -WIDTH / 2 + 3, WIDTH / 2 - 3 ), corrugated=False ),
        "doors": wall( size( "doors" ), ( -WIDTH / 2 + 3, WIDTH / 2 - 3 ), corrugated=False ),
    }
    # The ceiling's dirt isn't at its edge: even it out. The front wall's ribs and the doors' frames.
    c = regions["ceiling"]
    c.colour = paint[None, None, :] * ( 1.0 + 0.05 * c.noise( 2.4, 50, 4 )[..., None] ) * ( 1.0 - 0.04 * np.exp( -corrugation( c.x )[1] / 0.4 ) )[..., None]
    c.height = DEPTH * 0.4 * ( 1.0 - corrugation( c.x )[0] ) * np.ones( c.shape, np.float32 )
    f = regions["front"]
    t = ( ( f.x + DOOR_POST ) / ( 2 * DOOR_POST ) * 5 ) % 1.0
    f.height += 1.4 * ( 1.0 - smoothstep( 0.1, 0.32, t ) * smoothstep( 0.9, 0.68, t ) )
    # The doors' inner faces (an open container's leaves): the back of door_end's panel, so its five ribs are channels
    # here, inside the leaf's box-section frame, and the black rubber gasket round the leaf's edge.
    d = regions["doors"]
    lx = np.abs( d.x )
    zl = d.z + FLOOR                                  # the region's z is from the floor's top; door_end's from the ground
    rim = 2.6
    panel = ( ( lx > 0.2 + rim ) & ( lx < DOOR_POST - 0.4 - rim ) & ( zl > DOOR_SILL + rim ) & ( zl < DOOR_HEADER - rim ) ).astype( np.float32 )
    phase = ( zl - DOOR_SILL - rim ) / ( ( DOOR_HEADER - rim ) - ( DOOR_SILL + rim ) ) * 5.0
    rib = smoothstep( 0.12, 0.3, phase % 1.0 ) * smoothstep( 0.88, 0.7, phase % 1.0 )
    # How far in from the leaf's edge. The door frame round the opening samples this region too, outside the leaves.
    edge = np.minimum( np.minimum( lx - 0.4, DOOR_POST - lx ), np.minimum( zl - DOOR_SILL, DOOR_HEADER - zl ) )
    on_leaf = ( edge > 0.0 ).astype( np.float32 )
    d.height += 0.6 * ( 1.0 - panel ) * on_leaf - 0.8 * rib * panel
    d.colour *= ( 1.0 - 0.07 * rib * panel )[..., None]
    gasket = smoothstep( 1.5, 1.1, edge ).astype( np.float32 ) * on_leaf
    d.lay( lin( ( 20, 20, 20 ) ), gasket * 0.92, rough=0.85, height=0.3 )
    for name, r in regions.items():
        x, y, w, h = INSIDE[name]
        c_, ro, he = r.maps()
        colour_map[y:y + h, x:x + w] = c_
        rough[y:y + h, x:x + w] = ro
        normal[y:y + h, x:x + w] = normals( he, r.ppi )
    return T.linear_to_srgb( colour_map ), rough, normal


# ---------------------------------------------------------------------------------------------------------------------
# The yard

CONCRETE_TILE = 768.0       # inches a tile
SLAB = 192.0                # 16 ft slabs


def concrete( n=None ):
    """ The yard's slabs: brushed concrete, sawn joints every 16 ft with their sealant, hairline cracks, oil and rust
    stains, tyre marks from the straddle carriers and forklifts, patches, and darker damp where water stood. """
    rng = np.random.default_rng( 41 )
    n = n or px( 4096 )
    ppi = n / CONCRETE_TILE
    shape = ( n, n )

    def nz( beta, longest, shortest=None ):
        return noise( rng, shape, ( ppi, ppi ), beta, longest, shortest )

    y, x = np.mgrid[0:n, 0:n].astype( np.float32 ) / ppi
    base = lin( ( 142, 140, 134 ) )
    cure = nz( 2.8, 400, 30 )
    mid = nz( 2.0, 40, 3 )
    grit = nz( 0.6, 0.6, 0.19 )
    colour = base[None, None, :] * ( 1.0 + 0.07 * cure + 0.035 * mid + 0.05 * grit )[..., None]
    colour *= ( 1.0 + 0.025 * nz( 3.0, 300, 60 )[..., None] * np.array( [ 1.0, 0.3, -0.6 ], np.float32 ) )
    rough = 0.86 + 0.04 * mid
    # A broom finish across each slab, its direction alternating slab to slab.
    slab_i = ( np.floor( x / SLAB ) + np.floor( y / SLAB ) ) % 2
    broom_a = ndimage.gaussian_filter( nz( 0.8, 2, 0.19 ), ( 0, 6 ), mode="wrap" )
    broom_b = ndimage.gaussian_filter( nz( 0.8, 2, 0.19 ), ( 6, 0 ), mode="wrap" )
    broom = np.where( slab_i == 0, broom_a, broom_b )
    height = 0.02 * broom + 0.03 * grit + 0.04 * mid      # a power-floated slab: flat to a few mm over a metre
    # Worn: the paste gone and the aggregate showing, where the traffic runs.
    worn = smoothstep( 0.2, 1.6, nz( 2.4, 200, 20 ) )
    aggregate = smoothstep( 0.3, 1.2, nz( 0.8, 1.2, 0.19 ) )
    stones = mix( lin( ( 118, 114, 106 ) )[None, None, :] * np.ones( ( 1, 1, 3 ), np.float32 ), lin( ( 160, 154, 142 ) ), aggregate )
    colour = mix( colour, stones, worn * 0.6 )
    height += worn * 0.06 * aggregate
    rough = mix( rough, 0.92, worn * 0.5 )
    # Sawn joints, spalled in places, the sealant black.
    jx = np.minimum( x % SLAB, SLAB - x % SLAB )
    jy = np.minimum( y % SLAB, SLAB - y % SLAB )
    joint = np.minimum( jx, jy )
    spall = smoothstep( 1.2, 2.6, nz( 1.4, 12, 0.4 ) ) * 1.4
    groove = smoothstep( 0.22 + spall, 0.1, joint )
    lip = np.exp( -joint / 1.2 ) * 0.4
    colour = mix( colour, lin( ( 20, 20, 20 ) ), groove * 0.9 )
    colour *= ( 1.0 - 0.18 * lip )[..., None]
    height -= 0.5 * groove
    rough = mix( rough, 0.95, groove )
    # Hairline cracks: meandering, forking, a few running off the joints' corners.
    cv = Canvas( shape, ( ppi, ppi ), ( 0.0, 0.0 ), CONCRETE_TILE, ss=2 )
    todo = [ ( rng.uniform( 0, CONCRETE_TILE ), rng.uniform( 0, CONCRETE_TILE ), rng.uniform( 0, 2 * math.pi ), rng.uniform( 30, 140 ), 0.16 ) for _ in range( 26 ) ]
    for i in range( 0, 4 ):
        for j in range( 0, 4 ):
            if rng.random() < 0.35:
                todo.append( ( i * SLAB, j * SLAB, rng.uniform( 0, 2 * math.pi ), rng.uniform( 20, 80 ), 0.18 ) )
    while todo:
        cx, cy, angle, remaining, w = todo.pop()
        pts = [ ( cx, cy ) ]
        while remaining > 0:
            angle += rng.normal( 0, 0.25 )
            step = min( remaining, rng.uniform( 1.0, 3.0 ) )
            cx, cy = cx + math.cos( angle ) * step, cy + math.sin( angle ) * step
            pts.append( ( cx, cy ) )
            remaining -= step
            if rng.random() < 0.02 and w > 0.1:
                todo.append( ( cx, cy, angle + rng.choice( [ -1, 1 ] ) * rng.uniform( 0.5, 1.2 ), remaining * rng.uniform( 0.3, 0.6 ), w * 0.75 ) )
        for ox in ( -CONCRETE_TILE, 0.0, CONCRETE_TILE ):
            for oy in ( -CONCRETE_TILE, 0.0, CONCRETE_TILE ):
                cv.line( [ ( px + ox, CONCRETE_TILE - ( py + oy ) ) for px, py in pts ], w )
    crack = cv.result()
    colour = mix( colour, lin( ( 34, 34, 32 ) ), crack * 0.9 )
    colour *= ( 1.0 - 0.12 * ndimage.gaussian_filter( crack, 3, mode="wrap" ) * 2 )[..., None]
    height -= 0.25 * crack
    # Oil: dark soft blots with darker middles, oil glossier.
    oil = np.zeros( shape, np.float32 )
    for _ in range( 22 ):
        cx, cy = rng.uniform( 0, CONCRETE_TILE, 2 )
        r_ = rng.uniform( 4, 26 )
        dx = ( x - cx + CONCRETE_TILE / 2 ) % CONCRETE_TILE - CONCRETE_TILE / 2
        dy = ( y - cy + CONCRETE_TILE / 2 ) % CONCRETE_TILE - CONCRETE_TILE / 2
        d = np.sqrt( ( dx / rng.uniform( 0.6, 1.4 ) ) ** 2 + dy ** 2 ) / r_
        oil = np.maximum( oil, np.clip( 1.0 - d, 0, 1 ) ** 0.7 * rng.uniform( 0.35, 0.8 ) )
    oil = ndimage.map_coordinates( oil, [ ( y + 6 * nz( 2, 20, 2 ) ) * ppi, ( x + 6 * nz( 2, 20, 2 ) ) * ppi ], order=1, mode="grid-wrap" ).astype( np.float32 )
    colour = mix( colour, lin( ( 44, 42, 40 ) ), oil * 0.85 )
    rough = mix( rough, 0.42, oil * 0.8 )
    # Rust: blooms where steel lay on the slab, and the castings' marks.
    rust = smoothstep( 1.9, 3.0, nz( 2.0, 30, 1 ) ) * 0.6
    for _ in range( 30 ):
        cx, cy = rng.uniform( 0, CONCRETE_TILE, 2 )
        d = np.maximum( np.abs( ( x - cx + CONCRETE_TILE / 2 ) % CONCRETE_TILE - CONCRETE_TILE / 2 ) - 3.5,
                        np.abs( ( y - cy + CONCRETE_TILE / 2 ) % CONCRETE_TILE - CONCRETE_TILE / 2 ) - 3.2 )
        rust = np.maximum( rust, smoothstep( 2.0, -0.5, d ) * rng.uniform( 0.3, 0.7 ) )
    rust *= smoothstep( -1.2, 1.0, nz( 1.6, 6, 0.3 ) )
    colour = mix( colour, lin( ( 132, 82, 48 ) ), rust * 0.75 )
    # Tyre marks: pairs of curving dark bands.
    tyres = Canvas( shape, ( ppi, ppi ), ( 0.0, 0.0 ), CONCRETE_TILE, ss=1 )
    for _ in range( 14 ):
        cx, cy = rng.uniform( 0, CONCRETE_TILE, 2 )
        heading = rng.uniform( 0, 2 * math.pi )
        bend = rng.normal( 0, 0.004 )
        track = rng.uniform( 40, 70 )
        length = rng.uniform( 150, 500 )
        width = rng.uniform( 4, 9 )
        value = rng.uniform( 0.25, 0.6 )
        for side in ( -0.5, 0.5 ):
            pts = []
            hx, hy, hd = cx, cy, heading
            for s in np.linspace( 0, length, 60 ):
                pts.append( ( hx - math.sin( hd ) * side * track, hy + math.cos( hd ) * side * track ) )
                hd += bend * length / 60
                hx += math.cos( hd ) * length / 60
                hy += math.sin( hd ) * length / 60
            for ox in ( -CONCRETE_TILE, 0.0, CONCRETE_TILE ):
                for oy in ( -CONCRETE_TILE, 0.0, CONCRETE_TILE ):
                    tyres.line( [ ( px + ox, CONCRETE_TILE - ( py + oy ) ) for px, py in pts ], width, value )
    tyre = ndimage.gaussian_filter( tyres.result(), 1.5, mode="wrap" ) * smoothstep( -1.5, 1.0, nz( 1.5, 20, 1 ) )
    colour = mix( colour, lin( ( 40, 40, 40 ) ), tyre * 0.6 )
    rough = mix( rough, 0.7, tyre * 0.5 )
    # Patches: newer concrete set into a cut, darker and smoother, its edges sawn.
    for _ in range( 3 ):
        cx, cy = rng.uniform( 0, CONCRETE_TILE, 2 )
        hw, hh = rng.uniform( 12, 40, 2 )
        dx = np.abs( ( x - cx + CONCRETE_TILE / 2 ) % CONCRETE_TILE - CONCRETE_TILE / 2 ) - hw
        dy = np.abs( ( y - cy + CONCRETE_TILE / 2 ) % CONCRETE_TILE - CONCRETE_TILE / 2 ) - hh
        inside = smoothstep( 0.2, -0.2, np.maximum( dx, dy ) )
        border = np.exp( -np.abs( np.maximum( dx, dy ) ) / 0.3 )
        colour = mix( colour, lin( ( 118, 118, 114 ) )[None, None, :] * ( 1.0 + 0.05 * mid[..., None] ), inside * 0.85 )
        colour = mix( colour, lin( ( 30, 30, 30 ) ), border * 0.7 )
        rough = mix( rough, 0.8, inside )
        height -= 0.1 * border
    # Damp where water stood: darker, glossier, soft-edged.
    damp = smoothstep( 1.0, 2.4, nz( 3.0, 160, 12 ) )
    colour *= ( 1.0 - 0.22 * damp )[..., None]
    rough = mix( rough, 0.5, damp * 0.7 )
    return T.linear_to_srgb( colour ), np.clip( rough, 0, 1 ), normals( height, ( ppi, ppi ) )


PANEL = ( 228.6, 128.0 )    # one precast wall panel: wide, high


def wall_panel( shape=None ):
    """ A precast concrete wall panel: smooth form face with blowholes, two rebated reveals, chamfered edges, lifting
    anchors in its top; rain streaks below the top and the reveals, efflorescence, algae and splash low down, rust
    stains from the posts' brackets at its ends. """
    rng = np.random.default_rng( 51 )
    shape = shape or ( px( 1024 ), px( 2048 ) )
    r = Region( rng, shape, ( 0.0, PANEL[0] ), ( 0.0, PANEL[1] ) )
    base = lin( ( 160, 158, 150 ) )
    r.colour = base[None, None, :] * ( 1.0 + 0.06 * r.noise( 2.6, 120, 8 ) + 0.03 * r.noise( 1.6, 8, 0.5 ) + 0.03 * r.noise( 0.6, 0.5, 0.12 ) )[..., None]
    r.rough = r.full( 0.8 )
    r.height += 0.02 * r.noise( 1.2, 2, 0.12 )
    # Faint pours: the form face's lifts.
    r.colour *= ( 1.0 + 0.025 * np.sin( r.z / PANEL[1] * 2 * math.pi * 3 + r.noise( 2, 40, 5 ) * 0.4 ) )[..., None]
    holes = smoothstep( 2.4, 3.4, r.noise( 0.9, 0.8, 0.12 ) )
    r.lay( lin( ( 70, 68, 64 ) ), holes, height=-0.12 )
    # Chamfers at the panel's ends and top, the reveals across it.
    edge = np.minimum( np.minimum( r.x, PANEL[0] - r.x ), PANEL[1] - r.z )
    chamfer = smoothstep( 0.9, 0.0, edge )
    r.height -= 0.6 * chamfer
    r.colour *= ( 1.0 - 0.15 * chamfer )[..., None]
    for rz in ( 42.0, 86.0 ):
        d = np.abs( r.z - rz )
        rebate = smoothstep( 0.9, 0.6, d )
        r.height -= 0.6 * rebate
        r.colour *= ( 1.0 - 0.2 * smoothstep( 0.9, 0.5, d ) )[..., None]
    for ax in ( 0.25, 0.75 ):
        a = smoothstep( 1.3, 1.0, np.sqrt( ( r.x - ax * PANEL[0] ) ** 2 + ( ( r.z - ( PANEL[1] - 3.0 ) ) * 1.6 ) ** 2 ) )
        r.lay( lin( ( 80, 78, 72 ) ), a, height=-0.4 )
    # Rain: dark streaks down from the top and under each reveal; efflorescence in places.
    runs = [ ( rng.uniform( 0, PANEL[0] ), PANEL[1], rng.uniform( 20, 110 ), rng.uniform( 1.5, 6 ), rng.uniform( 0.15, 0.4 ) ) for _ in range( 30 ) ]
    runs += [ ( rng.uniform( 0, PANEL[0] ), rz - 0.8, rng.uniform( 8, 30 ), rng.uniform( 1, 4 ), rng.uniform( 0.15, 0.35 ) ) for rz in ( 42.0, 86.0 ) for _ in range( 12 ) ]
    r.lay( lin( ( 76, 74, 70 ) ), np.clip( r.streaks( runs, 0.5 ), 0, 0.6 ) )
    white = [ ( rng.uniform( 0, PANEL[0] ), rz - 0.8, rng.uniform( 6, 18 ), rng.uniform( 0.6, 2 ), rng.uniform( 0.2, 0.45 ) ) for rz in ( 42.0, 86.0 ) for _ in range( 6 ) ]
    r.lay( lin( ( 214, 212, 204 ) ), np.clip( r.streaks( white, 1.4 ), 0, 0.5 ) )
    # Algae and splash low down.
    low = smoothstep( 16.0, 0.0, r.z + 4 * r.noise( 2, 30, 2 ) )
    r.lay( lin( ( 54, 62, 44 ) ), low * 0.65 * smoothstep( -1, 1.5, r.noise( 2, 20, 1 ) ), rough=0.9 )
    r.lay( GRIME * 1.4, smoothstep( 8.0, 0.0, r.z ) * 0.5 )
    # Rust from the posts' brackets at each end.
    rust = [ ( ex + rng.normal( 0, 1 ), z0, rng.uniform( 10, 40 ), rng.uniform( 1, 3 ), 0.45 ) for ex in ( 2.5, PANEL[0] - 2.5 ) for z0 in ( 30.0, 100.0 ) ]
    r.lay( RUST_STAIN, np.clip( r.streaks( rust ), 0, 0.7 ) )
    return r


# ---------------------------------------------------------------------------------------------------------------------
# Small tiling finishes

def floor_line( shape=( 64, 2048 ), length=192.0, width=4.0 ):
    """ A painted floor line, worn: coverage (the alpha test), its brightness and roughness. Tiles along its length. """
    rng = np.random.default_rng( 61 )
    ppi = ( shape[1] / length, shape[0] / width )
    big = noise( rng, shape, ppi, 2.2, 60, 2 )
    fine = noise( rng, shape, ppi, 1.0, 1.5, 0.08 )
    v = ( np.arange( shape[0], dtype=np.float32 ) + 0.5 ) / shape[0]
    edge = np.minimum( v, 1.0 - v )[:, None] * width
    ragged = smoothstep( 0.0, 0.12, edge + 0.05 * fine )
    paint = smoothstep( -1.6, -0.6, big + 0.5 * fine ) * ragged
    wheel = smoothstep( 1.2, 2.2, noise( rng, shape, ppi, 2.4, 40, 4 ) )
    paint *= 1.0 - wheel * smoothstep( -0.5, 0.8, fine )
    lum = 0.9 + 0.06 * fine - 0.25 * smoothstep( 0.0, 2.0, big ) * 0.5 - 0.2 * wheel
    rough = 0.55 + 0.1 * fine + 0.2 * wheel
    height = 0.02 * paint
    return paint, lum, rough, normals( height, ppi )


def painted_steel( colour, seed, rust_amount=0.5, n=None, tile=48.0 ):
    rng = np.random.default_rng( seed )
    n = n or px( 1024 )
    r = Region( rng, ( n, n ), ( 0.0, tile ), ( 0.0, tile ) )
    c0 = lin( colour )
    r.colour = c0[None, None, :] * ( 1.0 + 0.06 * r.noise( 2.4, 24, 2 ) + 0.02 * r.noise( 1, 0.6, 0.1 ) )[..., None]
    r.rough = r.full( 0.45 )
    r.colour = mix( r.colour, chalked( r.colour, 1.0 ), 0.12 + 0.1 * smoothstep( -1, 2, r.noise( 2.2, 10, 1 ) ) )
    scuff, gouge = r.scrapes( 10, ( 0, tile, 0, tile ), length=( 3, 16 ), slope=0.8 )
    chips = smoothstep( 2.3, 3.0, r.noise( 1.2, 1.5, 0.1 ) )
    wear_through( r, scuff, gouge, chips, rust_amount )
    rust = smoothstep( 2.4 - rust_amount, 3.2, r.noise( 1.4, 6, 0.3 ) )
    r.lay( RUST, rust, rough=0.9, height=0.02 )
    runs = [ ( rng.uniform( 0, tile ), rng.uniform( 10, tile ), rng.uniform( 4, 16 ), rng.uniform( 0.3, 0.8 ), 0.4 * rust_amount ) for _ in range( 12 ) ]
    r.lay( RUST_STAIN, np.clip( r.streaks( runs ), 0, 0.6 ) )
    r.dents( 6, ( 1, 4 ), ( 0.03, 0.15 ) )
    return r


def galvanised( seed=71, n=None, tile=32.0 ):
    rng = np.random.default_rng( seed )
    n = n or px( 1024 )
    r = Region( rng, ( n, n ), ( 0.0, tile ), ( 0.0, tile ) )
    spangle = r.noise( 1.8, 1.5, 0.15 )
    blotch = r.noise( 3.0, 16, 2 )
    dull = smoothstep( -0.2, 1.4, blotch )
    r.colour = lin( ( 150, 153, 155 ) )[None, None, :] * ( 1.0 + 0.07 * spangle - 0.12 * dull )[..., None]
    r.rough = r.full( 0.38 ) + 0.06 * spangle + 0.25 * dull
    white = smoothstep( 1.4, 2.6, r.noise( 2.0, 6, 0.3 ) )
    r.lay( lin( ( 190, 192, 188 ) ), white * 0.5, rough=0.8 )
    rust = smoothstep( 2.2, 3.0, r.noise( 1.5, 3, 0.2 ) )
    r.lay( RUST, rust * 0.8, rough=0.9 )
    return r


def rusty_steel( seed=81, n=None, tile=48.0 ):
    rng = np.random.default_rng( seed )
    n = n or px( 1024 )
    r = Region( rng, ( n, n ), ( 0.0, tile ), ( 0.0, tile ) )
    flake = r.noise( 1.4, 4, 0.12 )
    r.colour = mix( RUST_DARK[None, None, :] * np.ones( ( 1, 1, 3 ), np.float32 ), RUST, smoothstep( -1.2, 1.2, flake + 0.6 * r.noise( 2.2, 20, 2 ) ) )
    mill = smoothstep( 0.8, 2.0, r.noise( 2.4, 16, 1 ) )
    r.lay( lin( ( 62, 62, 64 ) ), mill * 0.6, rough=0.6 )
    r.rough = r.full( 0.85 ) - 0.2 * mill
    r.height += 0.03 * flake
    return r


def hdpe( seed=91, n=None, tile=48.0 ):
    rng = np.random.default_rng( seed )
    n = n or px( 1024 )
    r = Region( rng, ( n, n ), ( 0.0, tile ), ( 0.0, tile ) )
    r.colour = lin( ( 214, 212, 200 ) )[None, None, :] * ( 1.0 + 0.04 * r.noise( 2.2, 20, 2 ) )[..., None]
    r.rough = r.full( 0.55 )
    runs = [ ( rng.uniform( 0, tile ), rng.uniform( 20, tile ), rng.uniform( 6, 30 ), rng.uniform( 0.5, 2 ), rng.uniform( 0.2, 0.5 ) ) for _ in range( 16 ) ]
    r.lay( lin( ( 120, 108, 80 ) ), np.clip( r.streaks( runs, 0.6 ), 0, 0.6 ) )
    r.lay( GRIME * 2.2, smoothstep( 0.5, 3.0, r.noise( 2.6, 20, 2 ) ) * 0.25 )
    scuff, _ = r.scrapes( 8, ( 0, tile, 0, tile ), length=( 2, 10 ), slope=1.0 )
    r.lay( lin( ( 230, 228, 220 ) ), scuff * 0.5, rough=0.4 )
    return r


# ---------------------------------------------------------------------------------------------------------------------
# Writing

# Flat paints: colour (sRGB), metalness, roughness.
PAINTED = {
    "bx_cone_orange": ( ( 232, 86, 22 ), 0.0, 0.55 ),
    "bx_reflective": ( ( 232, 232, 226 ), 0.0, 0.3 ),
    "bx_bin_green": ( ( 38, 84, 52 ), 0.0, 0.6 ),
    "bx_bin_grey": ( ( 82, 86, 90 ), 0.0, 0.6 ),
    "bx_bin_blue": ( ( 30, 64, 120 ), 0.0, 0.6 ),
    "bx_black_plastic": ( ( 26, 26, 28 ), 0.0, 0.65 ),
    "bx_rubber": ( ( 20, 20, 20 ), 0.0, 0.85 ),
    "bx_dark": ( ( 18, 17, 16 ), 0.0, 0.9 ),
    "bx_crane_yellow": ( ( 214, 168, 30 ), 0.2, 0.5 ),
    "bx_crane_white": ( ( 210, 212, 210 ), 0.2, 0.5 ),
    "bx_crane_red": ( ( 150, 38, 30 ), 0.2, 0.5 ),
    "bx_cab_glass": ( ( 40, 52, 60 ), 0.0, 0.1 ),
    "bx_lamp_off": ( ( 200, 200, 192 ), 0.0, 0.2 ),
    "bx_steel_dark": ( ( 52, 54, 56 ), 0.4, 0.5 ),
}


def save_grey( path, a, size=None ):
    img = Image.fromarray( np.clip( np.rint( a * 255 ), 0, 255 ).astype( np.uint8 ), "L" )
    if size:
        img = img.resize( size, Image.LANCZOS )
    img.save( path, optimize=True )


def save_rgb( path, a, quality=92 ):
    img = Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" )
    if str( path ).endswith( ".jpg" ):
        img.save( path, quality=quality, subsampling=0 )
    else:
        img.save( path, optimize=True )


def save_normal( path, n ):
    save_rgb( path, ( n * 0.5 + 0.5 ) * 255, quality=94 )


def vmat( name, colour, normal, rough, metalness=0.0, alpha=None ):
    lines_ = [ "// Tools/boxyard_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if alpha:
        lines_ += [ '    F_ALPHA_TEST "1"', f'    TextureTranslucency "{RESOURCE_DIR}/{alpha}"', '    g_flAlphaTestReference "0.5"',
                    '    g_flAntiAliasedEdgeStrength "1"' ]
    lines_ += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metalness:.2f}"',
                f'    TextureColor "{RESOURCE_DIR}/{colour}"', f'    TextureNormal "{RESOURCE_DIR}/{normal}"',
                f'    TextureRoughness "{RESOURCE_DIR}/{rough}"', f'    TextureAmbientOcclusion "{DEFAULT_AO}"',
                '    g_vColorTint "[1.0 1.0 1.0 1.0]"', '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines_ ) + "\n"


def painted_vmat( colour, metalness, roughness ):
    r, g, b = ( c / 255.0 for c in colour )
    return ( '// Tools/boxyard_materials.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metalness:.2f}"\n'
             '    TextureColor "materials/default/default_color.tga"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"\n'
             f'    TextureAmbientOcclusion "{DEFAULT_AO}"\n'
             f'    g_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"\n'
             '    g_flModelTintAmount "1.0"\n}\n' )


def write( out, name, colour, rough, normal, metalness=0.0, rough_size=None, alpha=None ):
    save_rgb( out / f"{name}_color.jpg", colour )
    save_normal( out / f"{name}_normal.jpg", normal )
    save_grey( out / f"{name}_rough.png", rough, rough_size )
    ( out / f"{name}.vmat" ).write_text( vmat( name, f"{name}_color.jpg", f"{name}_normal.jpg", f"{name}_rough.png", metalness, alpha ),
                                         encoding="utf-8", newline="\n" )
    print( f"wrote {name}" )
    return colour, normal


def region_maps( r ):
    c, ro, he = r.maps()
    return T.linear_to_srgb( c ), ro, normals( he, r.ppi )


def build( name, out ):
    """ Draws one texture (or a group: 'containers', 'tiles'); returns { name: ( colour, normal ) } for the sheet. """
    done = {}
    if name.startswith( "bx_container_" ) and name != "bx_container_inside":
        colour_name, variant = name[len( "bx_container_" ):].split( "_" )
        c, ro, n = container_atlas( colour_name, variant )
        done[name] = write( out, name, c, ro, n, rough_size=( px( 2048 ), px( 1024 ) ) )
    elif name == "bx_container_inside":
        c, ro, n = inside_atlas()
        done[name] = write( out, name, c, ro, n, rough_size=( px( 2048 ), px( 1024 ) ) )
    elif name == "bx_concrete":
        c, ro, n = concrete()
        done[name] = write( out, name, c, ro, n, rough_size=( px( 2048 ), px( 2048 ) ) )
    elif name == "bx_wall_panel":
        c, ro, n = region_maps( wall_panel() )
        done[name] = write( out, name, c, ro, n )
    elif name == "bx_line":
        paint, lum, rough, n = floor_line()
        save_grey( out / "bx_line_trans.png", paint )
        save_normal( out / "bx_line_normal.jpg", n )
        save_grey( out / "bx_line_rough.png", rough )
        for colour_name, rgb in ( ( "yellow", ( 222, 178, 30 ) ), ( "white", ( 226, 226, 220 ) ) ):
            c = T.linear_to_srgb( lin( rgb )[None, None, :] * lum[..., None] )
            save_rgb( out / f"bx_line_{colour_name}_color.jpg", c )
            ( out / f"bx_line_{colour_name}.vmat" ).write_text(
                vmat( f"bx_line_{colour_name}", f"bx_line_{colour_name}_color.jpg", "bx_line_normal.jpg", "bx_line_rough.png", 0.0, "bx_line_trans.png" ),
                encoding="utf-8", newline="\n" )
            done[f"bx_line_{colour_name}"] = ( c * paint[..., None], n )
            print( f"wrote bx_line_{colour_name}" )
    elif name in SMALL:
        draw, metalness = SMALL[name]
        c, ro, n = region_maps( draw() )
        done[name] = write( out, name, c, ro, n, metalness )
    elif name == "painted":
        for p, ( rgb, metal, rough ) in PAINTED.items():
            ( out / f"{p}.vmat" ).write_text( painted_vmat( rgb, metal, rough ), encoding="utf-8", newline="\n" )
        print( f"wrote {len( PAINTED )} flat paints" )
    else:
        raise SystemExit( f"unknown texture {name}" )
    return done


SMALL = {
    "bx_galv": ( galvanised, 0.6 ),
    "bx_rust": ( rusty_steel, 0.0 ),
    "bx_drum_blue": ( lambda: painted_steel( ( 30, 70, 140 ), 101, 0.5 ), 0.0 ),
    "bx_drum_red": ( lambda: painted_steel( ( 150, 34, 28 ), 102, 0.7 ), 0.0 ),
    "bx_skip_green": ( lambda: painted_steel( ( 40, 78, 52 ), 103, 0.9 ), 0.0 ),
    "bx_hdpe": ( hdpe, 0.0 ),
}
NAMES = ( [ f"bx_container_{c}_{v}" for c, v in CONTAINERS ] + [ "bx_container_inside", "bx_concrete", "bx_wall_panel", "bx_line" ]
          + list( SMALL ) + [ "painted" ] )


def all_paints():
    """ Every paint name these materials give boxyard_map. """
    names = [ n for n in NAMES if n not in ( "bx_line", "painted" ) ] + [ "bx_line_yellow", "bx_line_white" ] + list( PAINTED )
    return names


def lit( colour, normal ):
    light = np.array( ( -0.45, 0.55, 0.7 ), np.float32 )
    light /= np.linalg.norm( light )
    ndl = np.clip( np.sum( normal * light, -1 ), 0.0, 1.0 )
    return np.clip( colour * ( 0.35 + 0.9 * ndl )[..., None], 0, 255 )


def write_sheet( results, path ):
    tiles = []
    for name, ( colour, normal ) in results.items():
        img = Image.fromarray( lit( colour, normal ).astype( np.uint8 ) )
        img.thumbnail( ( 1024, 512 ), Image.LANCZOS )
        canvas = Image.new( "RGB", ( 1024, 512 ), ( 16, 16, 16 ) )
        canvas.paste( img, ( 0, 0 ) )
        ImageDraw.Draw( canvas ).text( ( 6, 6 ), name, fill=( 255, 255, 255 ) )
        tiles.append( canvas )
    cols = 2
    rows = ( len( tiles ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( 1024 * cols, 512 * rows ), ( 16, 16, 16 ) )
    for k, t in enumerate( tiles ):
        sheet.paste( t, ( 1024 * ( k % cols ), 512 * ( k // cols ) ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"what to draw (default all: {', '.join( NAMES )})" )
    parser.add_argument( "--out", help="write somewhere else (for trying things out)" )
    parser.add_argument( "--sheet", help="also write a lit contact sheet here" )
    parser.add_argument( "--scale", type=float, default=1.0, help="draw at this share of the size (previews)" )
    args = parser.parse_args()
    if args.scale != 1.0:
        set_scale( args.scale )
    out = Path( args.out ) if args.out else OUT_DIR
    out.mkdir( parents=True, exist_ok=True )
    results = {}
    for name in args.names or NAMES:
        results.update( build( name, out ) )
    if args.sheet and results:
        write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
