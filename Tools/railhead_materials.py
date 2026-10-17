"""
Railhead's materials (Tools/railhead_map.py, railhead_props.py and railhead_backdrop.py): Hohenwald Hauptbahnhof, a
Gründerzeit through station of sandstone and riveted iron, its platforms, tracks, trains and goods yard, and the town's
façades round it. Drawn from scratch with numpy and PIL like Reef Hall's and Belltower's: concrete paving slabs, tactile
strips, platform coping, ballast, sleepers, rails, asphalt, granite kerbs, formwork concrete, terrazzo, sandstone ashlar,
riveted and modern steel, lattice girders, the town's rendered façades, glass, the trains' and wagons' paint, containers,
lamps and signals, and the atlases: wayfinding signs, platform displays and the departures board, timetables and
posters, shop signs, graffiti, the cast bronze lettering, the platform clock and the snack machine's goods and
controls.

The close stone, timber and concrete surfaces also use curated CC0 scans through railhead_scanned.py; source channels
and provenance are recorded in railhead_scanned_sources.json.

    python Tools/railhead_materials.py [name ...] [--out <dir>] [--sheet <png>]

- Writes Assets/materials/railhead/<texture>_normal.png and _rough.png per texture (with _trans.png for the
  alpha-tested ones (lattice, graffiti, lettering) and _illum.png for the self-lit masks of the signs, displays
  and shop signs), and per paint <paint>_color.png and <paint>.vmat.
  Most are on shaders/complex.shader; rw_glass and rw_glass_roof are on shaders/glass.shader. The car paints, the
  signals' unlit lenses, the lanterns' opal glass and the kiosk's counter, shelves, plant and bottles (PAINTED) are
  flat colours with no texture of their own, so they get a vmat only. The kiosk's atlas, rw_kiosk, is
  railhead_kiosk_art.py's (OWN_SCRIPT), drawn without numpy.
- Every texture tiles over its tile units (paints(); map_kit's world-scale UVs read them through the model's
  tile_overrides), except the decal (DECALS: the clock, 0..1 across its polygon), the lattice (one panel per 1.0 of u)
  and the atlases (ATLASES), which the map scripts place by rect_uv().
- Heights are drawn in inches and the normal strength is 1024 / tile units, so the relief is the real thing's size.
- ANCHORED paints (the façades) start their picture's bottom edge at z 0: each tile is two storeys of two bays,
  138 in a storey and a bay. GRAIN paints run their picture's v along the polygon's longest edge (wood grain, rails,
  the coping's and kerbs' joints across it).
- Normals are OpenGL style (green up the picture), as s&box's model shader reads them.
- Nothing here names a real railway, operator or brand: the signs, displays and posters are the town's own, in the
  project's fonts (Dinish, Chakra Petch, Mina).
"""
import argparse
import functools
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree

import terrain_textures as T
import building_textures as BT
import railhead_kiosk_art as KIOSK

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/railhead"
RESOURCE_DIR = "materials/railhead"
DEFAULT_AO = "materials/default/default_ao.tga"
FONT_DIR = ROOT / "Assets/fonts"
SS = 2                                              # atlases are drawn at twice their size, then shrunk

spectral, smoothstep, gl_normals = T.spectral, T.smoothstep, BT.gl_normals


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

def unit( a ):
    return ( a - a.mean() ) / ( a.std() + 1e-9 )


def noise( rng, n, beta, fmin, fmax=None ):
    return unit( spectral( rng, n, beta, fmin, fmax ) )


def streaks( rng, n, beta, fmin, fmax, rows, cols=0.5 ):
    """ Noise smeared down the picture (rows px of blur along y): rain runs, grain, scuffs along v. """
    return BT.stretched( rng, n, beta, fmin, fmax, ( rows, cols ) )


def coords( n ):
    y, x = np.mgrid[0:n, 0:n] + 0.5
    return x, y


def lin( c ):
    return T.srgb_to_linear( np.asarray( c, float ) )


def srgb( c ):
    return T.linear_to_srgb( c )


def lum_paint( rgb, lum ):
    """ An sRGB colour lit by lum (linear) as an sRGB picture. """
    return BT.paint( rgb, np.asarray( lum, float ) )


def mix( a, b, t ):
    """ Two sRGB pictures (or a picture and a colour) mixed by t per px. """
    a = np.asarray( a, float )
    b = np.asarray( b, float )
    t = np.asarray( t, float )
    return a + ( b - a ) * ( t[..., None] if t.ndim else t )


def tinted( colour, rgb, amount ):
    """ A picture moved towards rgb by amount (per px or one number), keeping its own light and dark. """
    linear = lin( colour )
    lum = linear @ np.array( ( 0.2126, 0.7152, 0.0722 ) )
    rel = lum / max( lum.mean(), 1e-6 )
    target = lin( rgb )[None, None, :] * rel[..., None]
    amount = np.asarray( amount, float )
    return srgb( linear + ( target - linear ) * ( amount[..., None] if amount.ndim else amount ) )


def darken( colour, factor ):
    """ A picture times factor (per px) in linear light. """
    return srgb( lin( colour ) * np.asarray( factor, float )[..., None] )


def stamp( field, x, y, rx, ry, value, angle=0.0, soft=1.0, profile="flat", mode="max" ):
    """ An ellipse rx x ry px at ( x, y ) into field, wrapping at the edges. profile "flat" is a disc with a soft edge
    (soft px), "dome" a rivet head or a blob of gum, "cone" falls off straight. mode max keeps the higher, add adds. """
    n = field.shape[0]
    r = int( math.ceil( max( rx, ry ) + soft ) ) + 1
    xs = np.arange( int( x ) - r, int( x ) + r + 1 )
    ys = np.arange( int( y ) - r, int( y ) + r + 1 )
    u0 = xs[None, :] + 0.5 - x
    v0 = ys[:, None] + 0.5 - y
    c, s = math.cos( angle ), math.sin( angle )
    u = ( u0 * c + v0 * s ) / rx
    v = ( -u0 * s + v0 * c ) / ry
    d = np.hypot( u, v )
    if profile == "dome":
        w = np.sqrt( np.clip( 1.0 - d * d, 0.0, 1.0 ) )
    elif profile == "cone":
        w = np.clip( 1.0 - d, 0.0, 1.0 )
    else:
        w = np.clip( ( 1.0 - d ) * max( rx, ry ) / soft + 0.5, 0.0, 1.0 )
    rows, cols = np.ix_( ys % n, xs % n )
    if mode == "add":
        np.add.at( field, ( rows, cols ), w * value )
    elif mode == "min":
        field[rows, cols] = np.minimum( field[rows, cols], 1.0 - w * ( 1.0 - value ) )
    else:
        field[rows, cols] = np.maximum( field[rows, cols], w * value )
    return w


def _fold( a, t, m, axis ):
    a = np.moveaxis( a, axis, 0 )
    out = a[m:m + t].copy()
    if m:
        out[t - m:] = np.maximum( out[t - m:], a[:m] )
        out[:m] = np.maximum( out[:m], a[m + t:] )
    return np.moveaxis( out, 0, axis )


class Canvas:
    """ Lines and shapes drawn at ss times the size on the tile plus a margin, folded back so they wrap. Points are
    tile px. A shape's first point is moved into the tile and the rest with it, so a shape may cross any edge as long
    as it stays within the margin. """

    def __init__( self, n, ss=2, margin=None ):
        self.n, self.ss = n, ss
        self.m = int( min( n, margin if margin is not None else n // 4 ) )
        size = ( n + 2 * self.m ) * ss
        self.image = Image.new( "L", ( size, size ), 0 )
        self.draw = ImageDraw.Draw( self.image )

    def _shift( self, points ):
        x0, y0 = points[0]
        dx, dy = ( x0 % self.n ) - x0, ( y0 % self.n ) - y0
        return [ ( ( x + dx + self.m ) * self.ss, ( y + dy + self.m ) * self.ss ) for x, y in points ]

    def line( self, points, width, value=1.0 ):
        self.draw.line( self._shift( points ), fill=int( value * 255 ), width=max( 1, int( round( width * self.ss ) ) ),
                        joint="curve" )

    def polygon( self, points, value=1.0 ):
        self.draw.polygon( self._shift( points ), fill=int( value * 255 ) )

    def ellipse( self, x, y, rx, ry, value=1.0 ):
        ( px, py ), = self._shift( [ ( x, y ) ] )
        s = self.ss
        self.draw.ellipse( ( px - rx * s, py - ry * s, px + rx * s, py + ry * s ), fill=int( value * 255 ) )

    def result( self ):
        n, s = self.n, self.ss
        a = np.asarray( self.image )
        a = _fold( _fold( a, n * s, self.m * s, 0 ), n * s, self.m * s, 1 )
        return a.reshape( n, s, n, s ).mean( axis=( 1, 3 ) ) / 255.0


def crack_lines( rng, n, count, length, width, branch=0.35, margin=None ):
    """ Hairline cracks, as BT.cracks draws them, on a Canvas (no 3x3 tile canvas at 2048). """
    canvas = Canvas( n, 2, margin if margin is not None else min( n, int( length[1] ) + 8 ) )
    todo = [ ( rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0, 2 * math.pi ), rng.uniform( *length ), width )
             for _ in range( count ) ]
    while todo:
        x, y, angle, remaining, w = todo.pop()
        points = [ ( x, y ) ]
        while remaining > 0:
            angle += rng.normal( 0, 0.18 )
            step = min( remaining, rng.uniform( 2.0, 5.0 ) * n / 1024 )
            x, y = x + math.cos( angle ) * step, y + math.sin( angle ) * step
            points.append( ( x, y ) )
            remaining -= step
            if rng.random() < branch * step / 60.0 and w > 0.6:
                todo.append( ( x, y, angle + rng.choice( [ -1, 1 ] ) * rng.uniform( 0.5, 1.1 ),
                               remaining * rng.uniform( 0.3, 0.6 ), w * 0.7 ) )
        canvas.line( points, w )
    return canvas.result()


def blotches( rng, n, beta, fmin, fmax, cover, soft=0.25 ):
    """ Patches covering about cover of the tile, with soft edges: stains, rust, grime. """
    field = noise( rng, n, beta, fmin, fmax )
    edge = np.quantile( field, 1.0 - cover )
    return smoothstep( edge - soft, edge + soft, field )


def run_down( source, length, fall=0.4, rng=None, n=None ):
    """ Streaks running down the picture from source (0..1): rust and dirt washed down a wall by rain. length px. """
    out = source.copy()
    for k in range( 1, int( length ), 2 ):
        out = np.maximum( out, np.roll( source, k, axis=0 ) * math.exp( -k * fall / length * 3.0 ) )
    if rng is not None:
        out *= np.clip( 0.6 + 0.6 * streaks( rng, source.shape[0], 1.5, 4, 120, 30, 0.6 ), 0.0, 1.0 )
    return out


def cast_shadow( height, slope, reach, dx=0.6, soft=0.25 ):
    """ How much of a sun from the upper left falls on each px (1 lit, 0 in shade), from height (inches): slope is how
    far the light rises a px. Wraps like the tile. """
    shade = np.zeros_like( height )
    for k in range( 1, int( reach ) ):
        above = np.roll( np.roll( height, k, axis=0 ), int( round( k * dx ) ), axis=1 )
        shade = np.maximum( shade, above - height - k * slope )
    return 1.0 - smoothstep( 0.0, soft, shade )


# ---------------------------------------------------------------------------------------------------------------------
# Text

@functools.lru_cache( None )
def font( name, px ):
    return ImageFont.truetype( str( FONT_DIR / f"{name}.ttf" ), max( 4, int( round( px ) ) ) )


@functools.lru_cache( None )
def cap_ratio( name ):
    return -font( name, 1000 ).getbbox( "H", anchor="ls" )[1] / 1000.0


def sized( name, cap ):
    """ The font whose capitals stand cap px high. """
    return font( name, cap / cap_ratio( name ) )


def text_width( s, f, tracking=0.0 ):
    return f.getlength( s ) + tracking * max( 0, len( s ) - 1 )


def fitted( name, s, cap, width, tracking=0.0 ):
    """ sized( name, cap ), smaller if s would run wider than width (tracking is a share of cap). """
    f = sized( name, cap )
    w = text_width( s, f, tracking * cap )
    if w > width:
        cap *= width / w
        f = sized( name, cap )
    return f, cap


def put( draw, xy, s, f, fill, anchor="ls", tracking=0.0 ):
    """ Text at xy; tracking (px) spaces the letters out, drawn one at a time. """
    if not tracking:
        draw.text( xy, s, font=f, fill=fill, anchor=anchor )
        return
    x, y = xy
    w = text_width( s, f, tracking )
    x -= { "l": 0.0, "m": w / 2, "r": w }[anchor[0]]
    for ch in s:
        draw.text( ( x, y ), ch, font=f, fill=fill, anchor="l" + anchor[1] )
        x += f.getlength( ch ) + tracking


def rotated( points, angle, cx=0.0, cy=0.0, scale=1.0 ):
    c, s = math.cos( angle ), math.sin( angle )
    return [ ( cx + scale * ( x * c - y * s ), cy + scale * ( x * s + y * c ) ) for x, y in points ]


# ---------------------------------------------------------------------------------------------------------------------
# Tiling textures. Each returns ( { paint: sRGB colour }, roughness, height (inches), normal strength[, extra maps] ).

PAVING_TILE = 240.0                                 # inches a paving tile: 10 x 15 slabs, so a 60 m platform doesn't repeat


def paving( rng, n ):
    """ Concrete paving slabs (Betonwerkstein) on the platforms and the forecourt: 10 x 15 to a 240 in tile, each 24 x 16 in
    (61 x 40.6 cm: a 60 x 40 slab with its 5 mm joint), laid in third bond so the odd row count still wraps. Mid grey
    with fine aggregate, each slab a shade of its own (6 %), one in ten a little cooler or warmer from another batch,
    a few newer ones, lipped and tilted a hair. The arrises carry a 0.3 in chamfer, so the joints read as a dark line
    a long way off; they hold dark sand, and stains spread out of them. Walking lanes a metre or so wide, darker and
    smoother from shoes, flattened chewing gum (black where it's newer, pale and crazed when years old), two or three
    cracked slabs and a cut-in replacement. Paints: rw_paving grey, rw_paving_warm buff, rw_paving_dark anthracite. """
    tile = PAVING_TILE
    p = n / tile
    x, y = coords( n )
    cols, rows = 10, 15
    sw, sh = n / cols, n / rows
    row = np.minimum( ( y // sh ).astype( int ), rows - 1 )
    xo = ( x + ( row % 3 ) * sw / 3 ) % n
    col = np.minimum( ( xo // sw ).astype( int ), cols - 1 )
    slab = row * cols + col
    u, v = xo - col * sw, y - row * sh
    edge = np.minimum( np.minimum( u, sw - u ), np.minimum( v, sh - v ) ) / p          # inches to the slab's edge
    count = rows * cols
    # Round 2: in the engine every slab read the same and the joints were hairlines. 10 % spread, and one in eight
    # clearly newer (lighter) or older (darker and stained).
    tone = rng.normal( 1.0, 0.10, count )
    age_roll = rng.random( count )
    newer = age_roll < 0.0625
    older = ( age_roll >= 0.0625 ) & ( age_roll < 0.125 )
    tone[newer] *= 1.12
    tone[older] *= 0.88
    # One slab in ten from another batch: a cooler or a warmer cement.
    hue = np.ones( ( count, 3 ) )
    batch = rng.random( count )
    hue[batch < 0.05] = ( 0.975, 0.995, 1.03 )
    hue[( batch >= 0.05 ) & ( batch < 0.10 )] = ( 1.035, 1.0, 0.95 )
    # Two or three cracked slabs, and one cut in later (sharper, cleaner, a shade off).
    cracked = np.zeros( count, bool )
    cracked[rng.choice( count, 3, replace=False )] = True
    replaced = np.zeros( count, bool )
    replaced[rng.choice( np.flatnonzero( ~cracked ), 2, replace=False )] = True
    tone[replaced] = rng.uniform( 1.04, 1.1, replaced.sum() )
    hue[replaced] = ( 1.0, 1.0, 0.98 )
    lip = rng.normal( 0.0, 0.03, count )
    lip[cracked] += 0.03
    gx, gy = rng.normal( 0.0, 0.0015, ( 2, count ) )                                  # inches an inch
    fine = noise( rng, n, 1.0, n / 6 )
    mottle = noise( rng, n, 2.4, 6, 160 )
    speck = noise( rng, n, 0.6, n / 4 )
    joint = 0.1                                                                       # half a 5 mm joint
    chamfer = smoothstep( joint, joint + 0.5, edge )
    chipn = noise( rng, n, 1.5, 40, 500 )
    chip = smoothstep( 2.1, 2.6, chipn ) * ( edge < 0.8 ) * ( edge > joint ) * ( 1.0 - replaced[slab] )
    surface = lip[slab] + gx[slab] * ( u - sw / 2 ) / p + gy[slab] * ( v - sh / 2 ) / p
    on_slab = edge > joint

    # A crack across each cracked slab: a wandering line from one side to the other, one half a hair lower.
    crack = np.zeros( ( n, n ) )
    split = np.zeros( ( n, n ) )
    for s in np.flatnonzero( cracked ):
        r_, c_ = divmod( s, cols )
        x0 = ( c_ * sw - ( r_ % 3 ) * sw / 3 ) % n
        y0 = r_ * sh
        across = rng.random() < 0.5
        canvas = Canvas( n, 2, int( sw ) + 8 )
        pts = []
        t0, t1 = rng.uniform( 0.2, 0.8, 2 )
        for k in range( 13 ):
            t = k / 12.0
            jitter = rng.normal( 0, 0.03 )
            if across:
                pts.append( ( x0 + sw * t, y0 + sh * ( t0 + ( t1 - t0 ) * t + jitter ) ) )
            else:
                pts.append( ( x0 + sw * ( t0 + ( t1 - t0 ) * t + jitter ), y0 + sh * t ) )
        canvas.line( pts, 0.9 * n / 2048, 1.0 )
        line = canvas.result() * ( slab == s )
        crack = np.maximum( crack, line )
        # Which side of the crack is lower: the side away from the slab's first corner.
        side = ( ( v / sh if across else u / sw ) > ( t0 + t1 ) / 2 ) & ( slab == s )
        split = np.maximum( split, side * 1.0 )
    height = np.where( on_slab, surface + 0.012 * fine + 0.006 * mottle - 0.15 * ( 1.0 - chamfer ) - 0.14 * chip
                       - 0.035 * split - 0.08 * crack, -0.2 + 0.03 * fine )

    # Chewing gum, trodden flat: black when new-ish (it collects dirt), pale grey and crazed when years old.
    gum = np.zeros( ( n, n ) )
    gum_age = np.zeros( ( n, n ) )
    gum_h = np.zeros( ( n, n ) )
    for _ in range( int( 170 * ( n / 2048 ) ** 2 * ( tile / 160.0 ) ** 2 ) ):
        gx_, gy_ = rng.uniform( 0, n, 2 )
        r = rng.uniform( 0.22, 0.5 ) * p
        aspect = rng.uniform( 0.75, 1.0 )
        age = rng.uniform() ** 0.7
        stamp( gum, gx_, gy_, r, r * aspect, 1.0, rng.uniform( 0, 3.2 ), soft=0.6 )
        stamp( gum_age, gx_, gy_, r, r * aspect, age, rng.uniform( 0, 3.2 ), soft=0.6 )
        stamp( gum_h, gx_, gy_, r, r * aspect, 0.03, profile="dome" )
    height = height + gum_h * on_slab
    hair = crack_lines( rng, n, 4, ( 40 * n / 2048, 160 * n / 2048 ), 0.7 * n / 2048 ) * on_slab
    height -= 0.04 * hair
    # Stains: spreading out of the joints (dirty water standing in them) and a few spills on the slabs.
    near_joint = 1.0 - smoothstep( 0.2, 3.5, edge + 1.2 * noise( rng, n, 1.6, 20, 300 ) )
    seep = near_joint * smoothstep( -0.6, 1.4, noise( rng, n, 2.2, 3, 80 ) )
    stains = np.maximum( T.warp( rng, n, blotches( rng, n, 2.6, 3, 60, 0.035, 0.6 ), 0.8 * p ), 0.6 * seep )
    # Walking lanes: one big beta-3 field a tile, darker and smoother where the crowds walk.
    lanes = smoothstep( -0.2, 1.6, noise( rng, n, 3.0, 1, 6 ) )
    broad = noise( rng, n, 3.0, 1.5, 3 )                                          # a 2-4 m dirt cloud, +-6 %
    stains = np.maximum( stains, 0.5 * older[slab] * smoothstep( -0.8, 1.2, noise( rng, n, 2.2, 6, 60 ) ) )
    ao = T.cavity_ao( height, ( ( 1.5, 3.0 ), ( 5.0, 1.2 ) ), 1.0 )

    lum = ( tone[slab] * ( 1.0 + 0.03 * mottle + 0.035 * fine ) * ( 1.0 - 0.15 * lanes ) * ( 1.0 - 0.14 * stains )
            * ( 1.0 + 0.06 * broad ) )
    lum *= 1.0 - 0.16 * smoothstep( 1.9, 2.7, speck ) + 0.1 * smoothstep( 2.0, 2.8, -speck )
    lum *= ( 1.0 - 0.45 * crack ) * ( 1.0 - 0.2 * hair )
    # The joint and its shadowed chamfer: dark sand in the gap, the arris darkening over its 0.35 in.
    joint_mix = 1.0 - smoothstep( joint - 0.03, joint + 0.04, edge )
    arris = ( 1.0 - smoothstep( joint, joint + 0.55, edge ) ) * ( 1.0 - joint_mix )
    dirt = lum_paint( ( 50, 46, 42 ), 1.0 + 0.12 * fine )
    gum_colour = mix( np.array( ( 50, 50, 50 ), float ), np.array( ( 146, 146, 141 ), float ), gum_age )
    colours = {}
    for name, base in ( ( "rw_paving", ( 138, 140, 136 ) ), ( "rw_paving_warm", ( 146, 134, 110 ) ),
                        ( "rw_paving_dark", ( 72, 74, 76 ) ) ):
        c = srgb( lin( lum_paint( base, lum ) ) * hue[slab] )
        c = mix( c, srgb( lin( c ) * 0.72 + lin( ( 82, 72, 58 ) ) * 0.28 ), 0.4 * stains )
        c = darken( c, 1.0 - 0.4 * arris )
        c = mix( c, dirt, joint_mix )
        c = mix( c, gum_colour * ( 1.0 + 0.06 * fine )[..., None], gum * on_slab )
        colours[name] = T.shaded( c, ao, 0.5 )
    rough = np.clip( 0.88 + 0.03 * fine - 0.12 * lanes + 0.03 * newer[slab] - 0.04 * replaced[slab], 0, 1 )
    rough = np.where( joint_mix > 0.5, 0.95, rough )
    rough = rough + ( 0.5 - rough ) * gum * on_slab
    return colours, rough, height, 1024 / tile


def tactile( rng, n ):
    """ The platforms' guidance strip (Leitstreifen): white concrete plates 12 in (30 cm) square, four ribs on each running
    along v, 1 in wide on top and 1.5 at their foot, 0.2 in high (DIN 32984's 4-5 mm), stopping 0.6 in short of the
    plate's edge. Dirt gathers between the ribs, the tops are scuffed grey with the odd rubber mark. """
    p = n / 24.0
    x, y = coords( n )
    pu, pv = ( x / p ) % 12.0, ( y / p ) % 12.0
    a = np.abs( pu % 3.0 - 1.5 )
    across = np.clip( ( 0.75 - a ) / 0.25, 0.0, 1.0 )
    along = np.clip( ( np.minimum( pv, 12.0 - pv ) - 0.6 ) / 0.25, 0.0, 1.0 )
    rib = smoothstep( 0.0, 1.0, np.minimum( across, along ) )
    plate_edge = np.minimum( np.minimum( pu, 12.0 - pu ), np.minimum( pv, 12.0 - pv ) )
    groove = 1.0 - smoothstep( 0.03, 0.14, plate_edge )
    return _plates( rng, n, rib, groove, "rw_tactile", 1024 / 24.0 )


def tactile_dots( rng, n ):
    """ The warning field at the stairs and the platform ends (Aufmerksamkeitsfeld): the same plates with truncated cone
    studs 2.4 in apart, 0.9 in across on top, 1.35 at their foot and 0.2 in high. """
    p = n / 24.0
    x, y = coords( n )
    du, dv = ( x / p ) % 2.4 - 1.2, ( y / p ) % 2.4 - 1.2
    r = np.hypot( du, dv )
    rib = smoothstep( 0.0, 1.0, np.clip( ( 0.68 - r ) / 0.23, 0.0, 1.0 ) )
    pu, pv = ( x / p ) % 12.0, ( y / p ) % 12.0
    plate_edge = np.minimum( np.minimum( pu, 12.0 - pu ), np.minimum( pv, 12.0 - pv ) )
    groove = 1.0 - smoothstep( 0.03, 0.14, plate_edge )
    return _plates( rng, n, rib, groove, "rw_tactile_dots", 1024 / 24.0 )


def _plates( rng, n, rib, groove, paint_name, strength ):
    fine = noise( rng, n, 1.0, n / 6 )
    mottle = noise( rng, n, 2.4, 3, 60 )
    grime_n = noise( rng, n, 2.6, 2, 60 )
    height = 0.2 * rib - 0.06 * groove + 0.006 * fine
    low = 1.0 - rib
    grime = np.clip( 0.2 * low * smoothstep( -1.0, 1.5, grime_n ) + 0.5 * groove, 0.0, 1.0 )
    scuff = blotches( rng, n, 2.0, 8, 160, 0.06 ) * rib
    rubber = blotches( rng, n, 1.8, 10, 200, 0.012, 0.15 ) * rib
    lum = ( 1.0 + 0.03 * mottle + 0.03 * fine ) * ( 1.0 - 0.3 * grime ) * ( 1.0 - 0.12 * scuff ) * ( 1.0 - 0.55 * rubber )
    colour = lum_paint( ( 232, 232, 226 ), lum )
    colour = mix( colour, lum_paint( ( 92, 84, 72 ), 1.0 + 0.1 * fine ), 0.3 * grime )
    ao = T.cavity_ao( height, ( ( 2.0, 2.0 ), ( 8.0, 1.0 ) ), 1.0 )
    rough = np.clip( 0.68 + 0.04 * fine + 0.1 * grime - 0.08 * scuff, 0, 1 )
    return { paint_name: T.shaded( colour, ao, 0.4 ) }, rough, height, strength


def coping( rng, n ):
    """ The platform edge's coping: precast concrete blocks 1 m long, one to a tile of 39.4 in. GRAIN runs v along the
    platform edge, so the block joint is across the picture at its top and bottom edge. Light grey, the arrises chipped
    at the block ends, spalled here and there, and brown with brake dust. """
    p = n / 39.37
    x, y = coords( n )
    dj = np.minimum( y, n - y ) / p                       # inches to the joint
    joint = 0.2
    bevel = smoothstep( joint, joint + 0.3, dj )
    fine = noise( rng, n, 1.0, n / 6 )
    mottle = noise( rng, n, 2.4, 3, 60 )
    speck = noise( rng, n, 0.0, n / 3 )
    spall = np.zeros( ( n, n ) )
    for _ in range( 7 ):                                  # chips at the block ends
        stamp( spall, rng.uniform( 0, n ), rng.uniform( -0.3, 0.3 ) * p,
               rng.uniform( 0.6, 1.6 ) * p, rng.uniform( 0.4, 0.9 ) * p, 1.0, rng.uniform( -0.4, 0.4 ), soft=2.0 )
    for _ in range( 5 ):
        stamp( spall, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.4, 1.4 ) * p, rng.uniform( 0.3, 0.9 ) * p,
               1.0, rng.uniform( 0, 3.2 ), soft=2.0 )
    spall = T.warp( rng, n, spall, 0.4 * p ) * smoothstep( -0.5, 0.5, noise( rng, n, 1.5, 20, 200 ) + 0.6 )
    height = np.where( dj > joint, -0.15 * ( 1.0 - bevel ), -0.3 ) + 0.01 * fine - 0.18 * spall
    dust = T.blur( blotches( rng, n, 2.8, 1, 16, 0.35, 1.2 ), 3.0 * p )
    scuff = smoothstep( 0.0, 2.0, streaks( rng, n, 1.5, 2, 100, 20, 0.5 ) )
    lum = ( 1.0 + 0.03 * mottle + 0.04 * fine ) * ( 1.0 - 0.2 * smoothstep( 2.0, 2.7, speck ) ) * ( 1.0 - 0.06 * scuff )
    lum *= 1.0 - 0.12 * spall
    colour = lum_paint( ( 172, 172, 168 ), lum )
    colour = tinted( colour, ( 132, 104, 82 ), 0.25 * dust )
    joint_mix = 1.0 - smoothstep( joint - 0.05, joint + 0.05, dj )
    colour = mix( colour, lum_paint( ( 70, 66, 60 ), 1.0 + 0.1 * fine ), joint_mix )
    ao = T.cavity_ao( height, ( ( 2.0, 2.0 ), ( 6.0, 1.0 ) ), 1.0 )
    rough = np.clip( 0.8 + 0.04 * fine + 0.08 * spall, 0, 1 )
    return { "rw_coping": T.shaded( colour, ao, 0.45 ) }, rough, height, 1024 / 39.37


def lines( rng, n ):
    """ Painted markings, road paint 1 mm (0.04 in) thick over grey concrete, worn through in patches and specks:
    rw_line_white (the platform's safety line), rw_line_yellow and rw_hazard (yellow and black stripes at 45 degrees,
    3.8 in (96 mm) each, three of each across a tile). """
    x, y = coords( n )
    fine = noise( rng, n, 1.0, n / 6 )
    mottle = noise( rng, n, 2.4, 3, 60 )
    patches = noise( rng, n, 2.6, 2, 40 )
    speck = noise( rng, n, 0.6, n / 6 )
    worn = smoothstep( 1.25, 1.85, 0.75 * patches + 0.55 * speck )
    worn = np.maximum( worn, smoothstep( 2.4, 2.8, speck ) )
    paint_ = 1.0 - worn
    concrete = lum_paint( ( 138, 138, 134 ), ( 1.0 + 0.05 * mottle + 0.05 * fine ) )
    dirt = 1.0 - 0.08 * smoothstep( -0.5, 2.0, noise( rng, n, 2.6, 2, 30 ) )
    g = ( x + y ) / ( n / 3.0 )
    tri = np.abs( ( g % 1.0 ) - 0.5 )
    yellow = np.clip( 0.5 + ( tri - 0.25 ) * ( n / 3.0 ) / math.sqrt( 2.0 ), 0.0, 1.0 )
    colours = {}
    for name, base in ( ( "rw_line_white", ( 234, 234, 228 ) ), ( "rw_line_yellow", ( 228, 178, 28 ) ) ):
        colours[name] = mix( concrete, lum_paint( base, dirt * ( 1.0 + 0.02 * fine ) ), paint_ )
    stripes = mix( lum_paint( ( 32, 32, 32 ), dirt * ( 1.0 + 0.04 * fine ) ),
                   lum_paint( ( 232, 184, 20 ), dirt * ( 1.0 + 0.02 * fine ) ), yellow )
    colours["rw_hazard"] = mix( concrete, stripes, paint_ )
    height = 0.04 * smoothstep( 0.3, 0.7, paint_ ) + 0.008 * fine
    rough = np.clip( 0.55 + 0.03 * fine + 0.3 * worn, 0, 1 )
    return colours, rough, height, 1024 / 32.0


def ballast( rng, n ):
    """ Track ballast: crushed granite of the railway grading (31.5-63 mm), angular stones piled loose over grit and
    fines, light grey with pinkish, dark and pale ones, dusted pale on top. rw_ballast is a clean bed; rw_ballast_rusty
    is the brown of brake dust and rust between the rails; rw_ballast_old is a siding's, its gaps silted up with soil and
    its stones mossy. """
    p = n / 160.0
    fines = noise( rng, n, 1.0, n / 8 )
    colour = lum_paint( ( 30, 30, 30 ), 1.0 + 0.12 * fines )      # the shadowed voids and grit between the stones
    ground = T.Ground( colour, -1.6 + 0.1 * fines, 0.95 + 0.0 * fines, noise( rng, n, 1.2, 40, n / 2 ) )
    # Dark grey basalt and granite (sRGB 95-115), a quarter of the stones pale, pinkish or darker.
    palette = [ ( 8, ( 98, 100, 102 ) ), ( 6, ( 90, 92, 94 ) ), ( 5, ( 106, 106, 106 ) ), ( 2, ( 134, 132, 128 ) ),
                ( 2, ( 126, 110, 102 ) ), ( 2, ( 72, 74, 76 ) ), ( 1, ( 144, 140, 134 ) ), ( 1, ( 114, 98, 90 ) ) ]
    count = int( 76000 * ( n / 2048 ) ** 2 )
    radii = T.sizes( rng, count, 0.7 * p, 1.35 * p, 1.4 )
    # Round 2: in the engine's sun the bed read pale and flat; real ballast is dark (sRGB 70-100) with deep shadows.
    palette = [ ( w, tuple( c * 0.85 for c in rgb ) ) for w, rgb in palette ]
    stones = T.stone_colours( rng, count, palette, 0.08 )
    for k in np.argsort( -radii ):                    # big ones first, small ones settle between
        r = radii[k]
        x_, y_ = rng.uniform( 0, n, 2 )
        ground.press( rng, x_, y_, r, stones[k], rng.uniform( 0.72, 0.9 ), top=r / p * rng.uniform( 0.85, 1.3 ),
                      sink=r / p * rng.uniform( 0.0, 0.6 ), aspect=rng.uniform( 1.0, 1.6 ), angular=True, tilt=0.3 )
    height = T.blur( ground.height, 0.6 * p / 12.8 )
    grain = noise( rng, n, 0.3, n / 4 )
    on_stone = ground.stone
    base = ground.colour * ( 1.0 + 0.07 * grain * on_stone )[..., None]
    ao = T.cavity_ao( height, ( ( 2.5 * p / 12.8, 0.8 ), ( 8.0 * p / 12.8, 0.75 ) ), 1.0 )
    tops = smoothstep( -0.3, 0.5, height ) * on_stone
    dust = blotches( rng, n, 2.2, 2, 60, 0.6, 1.0 )
    colours = {}
    c = mix( base, np.array( ( 138, 136, 132 ), float ), 0.06 * tops * dust )
    colours["rw_ballast"] = T.shaded( c, ao, 0.75 )
    # Between and beside the rails: brake dust and rust on the stones' tops, the voids darker with it.
    rust = np.clip( 0.45 + 0.2 * noise( rng, n, 2.4, 2, 40 ), 0.0, 0.8 ) * ( 0.35 + 0.65 * tops ) * 0.75
    c = darken( tinted( base, ( 100, 72, 52 ), rust ), 0.8 )
    colours["rw_ballast_rusty"] = T.shaded( c, ao, 0.75 )
    soil = 1.0 - smoothstep( -0.95, -0.25, height + 0.25 * noise( rng, n, 2.0, 8, 200 ) )
    moss = blotches( rng, n, 2.4, 3, 80, 0.25, 0.8 ) * smoothstep( -0.4, 0.2, height ) * on_stone
    c = darken( base, 0.9 + 0.0 * soil )
    c = mix( c, lum_paint( ( 90, 78, 60 ), 1.0 + 0.15 * fines ), 0.9 * soil )
    c = mix( c, lum_paint( ( 78, 92, 50 ), 1.0 + 0.2 * grain ), 0.55 * moss )
    colours["rw_ballast_old"] = T.shaded( c, ao, 0.7 )
    return colours, ground.rough, height, 1024 / 160.0, { "ao": ao }


def sleeper( rng, n ):
    """ Prestressed concrete sleepers: smooth cast grey with bug holes, brown with dust off the rails and brakes, and
    dark with grease and oil dripped from the trains. """
    p = n / 48.0
    fine = noise( rng, n, 1.0, n / 6 )
    mottle = noise( rng, n, 2.4, 3, 60 )
    pits = np.zeros( ( n, n ) )
    for _ in range( int( 700 * ( n / 1024 ) ** 2 ) ):
        r = rng.uniform( 0.03, 0.11 ) * p
        stamp( pits, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.7, 1 ), 1.0, profile="dome" )
    dust = blotches( rng, n, 2.8, 1, 24, 0.55, 2.0 )
    # Oil and grease dripped from standing trains: big soaked patches with darker cores and drips round them.
    # Capped at 0.45 darker: the tops stay a concrete grey (sRGB 145-150), only the soak darkens them, and the oil
    # proper lies in the four-foot's ballast (rw_ballast_rusty). The sleepers' UVs are planar in world space, so the
    # soak can't be held to their middles: it's kept to scattered patches.
    soak = T.warp( rng, n, blotches( rng, n, 2.6, 1, 16, 0.14, 1.0 ), 1.2 * p )
    grease = np.maximum( soak * ( 0.55 + 0.45 * blotches( rng, n, 2.2, 4, 60, 0.4, 0.8 ) ),
                         T.warp( rng, n, blotches( rng, n, 2.6, 2, 40, 0.05, 1.0 ), 0.6 * p ) )
    grease = 0.45 / 0.7 * grease
    rust = np.zeros( ( n, n ) )
    for _ in range( int( 40 * ( n / 1024 ) ** 2 ) ):                 # rust stains round the fastenings' steel
        r = rng.uniform( 0.6, 2.2 ) * p
        stamp( rust, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.5, 1.0 ), rng.uniform( 0.4, 0.9 ),
               rng.uniform( 0, 3.2 ), soft=0.6 * p )
    rust = rust * smoothstep( -1.0, 1.0, noise( rng, n, 1.4, 20, 300 ) )
    lum = ( 1.0 + 0.04 * mottle + 0.04 * fine ) * ( 1.0 - 0.45 * pits )
    colour = lum_paint( ( 150, 148, 142 ), lum )
    colour = tinted( colour, ( 120, 90, 66 ), 0.25 * dust )
    colour = tinted( colour, ( 122, 70, 40 ), 0.6 * rust )
    colour = darken( colour, 1.0 - 0.7 * grease )
    height = 0.01 * fine + 0.004 * mottle - 0.08 * pits
    rough = np.clip( 0.84 + 0.04 * fine - 0.5 * grease, 0, 1 )
    return { "rw_sleeper": colour }, rough, height, 1024 / 48.0


def sleeper_wood( rng, n ):
    """ Oak sleepers soaked in creosote (GRAIN: the grain runs along v, the sleeper's length): near black-brown where
    it is fresh, weathered to a grey-brown on top, with tar oozing out in glossy spots and checks split along the
    grain. """
    p = n / 48.0
    grain = streaks( rng, n, 1.2, 8, n / 2, 40, 0.6 )
    fibre = streaks( rng, n, 0.5, 60, n / 2, 14, 0.3 )
    weather = smoothstep( -1.2, 1.8, 0.6 * noise( rng, n, 3.0, 1, 12 ) + 0.5 * streaks( rng, n, 2.0, 2, 60, 60, 2.0 )
                          + 0.25 * grain )
    canvas = Canvas( n, 2, int( 16 * p ) )
    for _ in range( int( 26 * ( n / 1024 ) ** 2 ) ):
        x_, y_ = rng.uniform( 0, n, 2 )
        length = rng.uniform( 3, 14 ) * p
        pts = [ ( x_, y_ ) ]
        for k in range( 12 ):
            pts.append( ( pts[-1][0] + rng.normal( 0, 0.06 * p ), pts[-1][1] + length / 12 ) )
        canvas.line( pts, rng.uniform( 0.05, 0.16 ) * p )
    checks = canvas.result()
    tar = T.warp( rng, n, blotches( rng, n, 2.4, 3, 60, 0.03, 0.6 ), 0.5 * p ) * ( 1.0 - weather )
    lum = ( 1.0 + 0.1 * grain + 0.06 * fibre ) * ( 1.0 - 0.5 * checks )
    colour = mix( lum_paint( ( 56, 42, 30 ), lum ), lum_paint( ( 96, 86, 74 ), lum ), 0.85 * weather )
    colour = mix( colour, lum_paint( ( 30, 24, 20 ), 1.0 + 0.1 * fibre ), 0.9 * tar )
    height = 0.04 * grain + 0.015 * fibre - 0.25 * checks + 0.03 * tar
    rough = np.clip( 0.84 - 0.12 * ( 1.0 - weather ) - 0.5 * tar + 0.03 * fibre, 0, 1 )
    return { "rw_sleeper_wood": colour }, rough, height, 1024 / 48.0


def rail( rng, n ):
    """ The rails' web and foot (GRAIN: v along the rail): rolled steel under rust, orange-brown where it is fresh and
    dark brown where it is old, streaked along the rail by the rain and the passing trains, with flaking scale. """
    fine = noise( rng, n, 0.8, n / 6 )
    st = streaks( rng, n, 1.2, 4, n / 2, 30, 0.6 )
    blot = noise( rng, n, 2.0, 3, 80 )
    t = smoothstep( -1.5, 1.5, 0.6 * blot + 0.5 * st )
    colour = mix( lum_paint( ( 78, 48, 32 ), 1.0 + 0.08 * fine ), lum_paint( ( 122, 70, 44 ), 1.0 + 0.08 * fine ), t )
    fresh = blotches( rng, n, 2.0, 4, 100, 0.12, 0.6 )
    colour = mix( colour, lum_paint( ( 150, 92, 52 ), 1.0 + 0.1 * fine ), 0.6 * fresh )
    scale = smoothstep( 1.8, 2.4, noise( rng, n, 1.0, 30, n / 3 ) )
    colour = darken( colour, 1.0 - 0.3 * scale )
    height = 0.01 * fine + 0.006 * blot - 0.02 * scale
    rough = np.clip( 0.85 + 0.04 * fine - 0.06 * scale, 0, 1 )
    return { "rw_rail": colour }, rough, height, 1024 / 32.0


def rail_head( rng, n ):
    """ The rails' running surface (GRAIN: v along the rail): steel polished bright by the wheels, finely streaked along
    the rail, with a few dull flecks of oxide. Metal. """
    st = streaks( rng, n, 0.8, 8, n / 2, 80, 0.4 )
    fine = noise( rng, n, 0.6, n / 6 )
    oxide = smoothstep( 1.6, 2.6, streaks( rng, n, 1.2, 6, 240, 12, 0.5 ) ) * blotches( rng, n, 2.2, 2, 40, 0.3, 1.0 )
    colour = lum_paint( ( 172, 170, 166 ), 1.0 + 0.06 * st + 0.02 * fine )
    colour = mix( colour, lum_paint( ( 96, 66, 48 ), 1.0 + 0.1 * fine ), 0.7 * oxide )
    rough = np.clip( 0.22 + 0.06 * st + 0.45 * oxide, 0.05, 1 )
    height = 0.003 * st + 0.01 * oxide
    return { "rw_rail_head": colour }, rough, height, 1024 / 32.0


def _rect_wrap( x, y, x0, y0, w, h, n ):
    """ Inside a w x h rectangle at ( x0, y0 ) that wraps round the tile, and the px to its edge (inside or out). """
    u, v = ( x - x0 ) % n, ( y - y0 ) % n
    inside = ( u < w ) & ( v < h )
    du = np.where( u < w, np.minimum( u, w - u ), -np.minimum( u - w, n - u ) )
    dv = np.where( v < h, np.minimum( v, h - v ), -np.minimum( v - h, n - v ) )
    edge = np.where( inside, np.minimum( du, dv ), np.where( ( du < 0 ) & ( dv < 0 ), -np.hypot( du, dv ), np.minimum( du, dv ) ) )
    return inside, edge


SEALED_CRACKS = 0


ASPHALT_WHEEL_PATHS = ( 38.0, 99.0 )                 # inches across a 192 in tile: one car's two wheel paths, 61 in apart


def asphalt( rng, n ):
    """ Weathered stone mastic asphalt, 2048 px over a 192 in tile (u across the road, v along it, as map_kit lays a
    floor out): a dark binder (about sRGB 80) oxidised lighter and greyer where no tyre runs, its 8-11 mm chippings
    showing through, and two faint straight wheel paths 0.7 m wide down the tile 1.55 m apart (a car's track), where the
    binder is worn off the chippings: at most 4 % darker with a slight sheen (round 2: the wandering 15 % darker paths
    read as 4-6 smears across the cab road in sun). The lanes' own wear follows the lanes in the dressing's overlays
    (railhead_map), one owner, so a lane never gets four tracks.
    Fine crazing in the oxidised binder. Large repairs, sealed cracks, gutters and oil are placed by the dressing
    (railhead_map.road_wear): baked into a 4.9 m tile they repeat as a pattern down the road. """
    p = n / 192.0
    x, y = coords( n )
    fine = noise( rng, n, 0.0, n / 3 )
    chipn = noise( rng, n, 0.6, n / 10 )
    chips = smoothstep( 0.9, 1.6, chipn + 0.35 * fine )
    age = smoothstep( -1.0, 1.6, noise( rng, n, 2.6, 1, 16 ) )
    tone = noise( rng, n, 1.4, 8, n / 4 )
    broad = noise( rng, n, 3.0, 1, 2 )                              # one cycle a tile: +-6 %
    # The wheel paths: bands along v, their edges wandering 3-4 in, their wear stronger in some stretches.
    wander = 0.0
    strength = 1.0
    wheel = np.zeros( ( n, n ) )
    for k, u0 in enumerate( ASPHALT_WHEEL_PATHS ):
        d = np.abs( ( ( x - u0 * p - wander * ( 1 if k else 0.8 ) + n / 2 ) % n ) - n / 2 ) / p
        wheel = np.maximum( wheel, 1.0 - smoothstep( 6.0, 19.0, d + 0.6 * noise( rng, n, 2.4, 2, 12 ) ) )
    wheel *= strength
    # Oxidised binder between the wheel paths, darker worn binder and bared chippings in them.
    binder = mix( lum_paint( ( 76, 77, 76 ), 1.0 + 0.04 * tone ), lum_paint( ( 94, 94, 91 ), 1.0 + 0.04 * tone ),
                  ( 0.35 + 0.65 * age ) * ( 1.0 - 0.15 * wheel ) )
    stone = lum_paint( ( 140, 138, 132 ), 1.0 + 0.16 * noise( rng, n, 0.2, n / 5 ) )
    colour = mix( binder, stone, ( 0.5 + 0.03 * wheel ) * chips )
    colour = darken( colour, ( 1.0 + 0.06 * broad ) * ( 1.0 - 0.01 * wheel ) )
    # Crazing in the oxidised binder, not in the wheel paths, where the traffic kneads it shut.
    craze = crack_lines( rng, n, 34, ( 4 * p, 14 * p ), 0.6 * n / 2048, 0.6 ) * ( 1.0 - 0.8 * wheel ) * ( 0.4 + 0.6 * age )
    canvas = Canvas( n, 2, int( 120 * p ) )
    for _ in range( SEALED_CRACKS ):
        x_, y_ = rng.uniform( 0, n, 2 )
        angle = rng.uniform( 0, 2 * math.pi )
        pts = [ ( x_, y_ ) ]
        for _k in range( int( rng.uniform( 50, 110 ) / 2.5 ) ):
            angle += rng.normal( 0, 0.09 )
            pts.append( ( pts[-1][0] + math.cos( angle ) * 2.5 * p, pts[-1][1] + math.sin( angle ) * 2.5 * p ) )
        canvas.line( pts, 1.5 * p * rng.uniform( 0.8, 1.2 ) )
    sealed = smoothstep( 0.15, 0.6, T.blur( canvas.result(), 0.25 * p ) )
    colour = darken( colour, 1.0 - 0.3 * craze )
    colour = mix( colour, lum_paint( ( 30, 30, 30 ), 1.0 + 0.05 * fine ), 0.92 * sealed )
    height = 0.1 * chips + 0.02 * fine - 0.04 * craze + 0.02 * sealed
    rough = np.clip( 0.88 + 0.04 * fine - 0.07 * chips, 0, 1 )
    rough = rough - 0.04 * age * ( 1.0 - wheel ) - 0.05 * wheel
    rough = rough + ( 0.35 - rough ) * sealed
    ao = T.cavity_ao( height, ( ( 1.5, 4.0 ), ), 1.0 )
    return { "rw_asphalt": T.shaded( colour, ao, 0.5 ) }, np.clip( rough, 0, 1 ), height, 1024 / 192.0


KERB_TILE = 96.0


def kerb( rng, n ):
    """ Granite kerbs (GRAIN: v along the kerb), one 1.22 m stone to a 48 in tile with its mortar joint at the tile's top
    and bottom: grey salt-and-pepper granite, black mica and pale feldspar in grey quartz, flamed rough, scuffed dark by
    tyres along its length. """
    p = n / KERB_TILE
    x, y = coords( n )
    half = n / 2.0                                                   # two 1.22 m stones to a tile
    stone_ = ( y // half ).astype( int ) % 2
    dj = np.minimum( y % half, half - y % half ) / p
    a = noise( rng, n, 0.0, n / 3 )
    b = noise( rng, n, 0.4, n / 6 )
    c = noise( rng, n, 1.6, 20, n / 4 )
    mica = smoothstep( 1.2, 1.8, a )
    feldspar = smoothstep( 1.0, 1.7, b ) * ( 1.0 - mica )
    tone = 1.0 + rng.normal( 0, 0.06, 2 )
    colour = lum_paint( ( 132, 131, 129 ), tone[stone_] * ( 1.0 + 0.05 * c ) )
    colour = mix( colour, np.array( ( 44, 44, 46 ), float ), 0.85 * mica )
    colour = mix( colour, lum_paint( ( 186, 182, 176 ), 1.0 + 0.03 * c ), 0.6 * feldspar )
    # Tyre scuffs: black rubber smeared along the kerb, heavy in places.
    scuff = smoothstep( 0.1, 2.0, streaks( rng, n, 1.4, 2, 120, 60, 0.6 ) ) * blotches( rng, n, 2.0, 2, 30, 0.55, 1.0 )
    # Black rubber smeared along the kerb by tyres (u is across the kerb's face): heavy bands on some stretches.
    rubber = smoothstep( 0.6, 1.6, streaks( rng, n, 1.0, 3, 60, 200, 0.4 ) ) * blotches( rng, n, 2.4, 1, 6, 0.4, 0.8 )
    colour = darken( colour, ( 1.0 - 0.55 * scuff ) * ( 1.0 - 0.3 * rubber ) )
    colour = tinted( colour, ( 60, 58, 56 ), 0.25 * rubber )
    grime = smoothstep( -0.5, 2.0, noise( rng, n, 2.6, 1, 8 ) )
    colour = darken( colour, 1.0 - 0.12 * grime )
    joint = 1.0 - smoothstep( 0.18, 0.24, dj )                        # a 1 cm mortar joint, dark with dirt
    colour = mix( colour, lum_paint( ( 70, 66, 60 ), 1.0 + 0.08 * c ), joint )
    bevel = smoothstep( 0.2, 1.0, dj )                                # a 2 cm chamfer at the stones' ends
    colour = darken( colour, 1.0 - 0.15 * ( 1.0 - bevel ) * ( 1.0 - joint ) )
    height = 0.008 * a + 0.012 * c - 0.3 * ( 1.0 - bevel ) - 0.1 * joint
    rough = np.clip( 0.72 + 0.02 * a - 0.12 * scuff + 0.15 * joint, 0, 1 )
    rough = rough + ( 0.4 - rough ) * 0.8 * rubber
    return { "rw_kerb": colour }, rough, height, 1024 / KERB_TILE


SETTS_TILE = 128.0


def setts( rng, n ):
    """ Granite setts (Kleinpflaster laid in rows, as in old goods yards and station forecourts), 2048 px over a 128 in
    tile: tops about 8 x 4 in (20 x 10 cm) in rows 4.3 in apart, each stone its own granite from near-black to pale
    pink-grey (a tenth red-grey), the tops flamed and worn flat-crowned by a century of iron tyres, 0.7 in (1.8 cm)
    joints of dark grit sunk 0.5 in, oil and rust stains, and two or three broad darker, smoother wheel tracks. Round 2:
    the old 0.18 in dome rim-lit every edge and the 1 cm joints vanished in the mips, a grid of bathroom tiles. """
    p = n / SETTS_TILE
    block, u, v, length, rowh, row, count = BT.coursed( rng, n, ( 4.4 * p, 5.2 * p ), ( 5.2 * p, 7.8 * p ) )
    # Hand-set stones aren't sawn bricks: rounded, knocked corners, wobbling edges and joints of their own width.
    du = np.minimum( u, length - u ) / p
    dv = np.minimum( v, rowh - v ) / p
    r = rng.uniform( 0.5, 1.3, count )[block]
    d = np.where( ( du < r ) & ( dv < r ), r - np.hypot( r - du, r - dv ), np.minimum( du, dv ) )
    d = d + 0.15 * noise( rng, n, 2.4, 8, 70 ) + 0.025 * noise( rng, n, 1.2, 60, 400 )
    joint = rng.uniform( 0.26, 0.5, count )[block]
    pu, pv = ( u / length - 0.5 ) * 2.0, ( v / rowh - 0.5 ) * 2.0
    dome = np.clip( 1.0 - np.maximum( np.abs( pu ) ** 3, np.abs( pv ) ** 3 ), 0.0, 1.0 )
    lift = rng.normal( 0, 0.06, count )
    tilt_u, tilt_v = rng.normal( 0, 0.01, ( 2, count ) )
    fine = noise( rng, n, 0.2, n / 3 )
    flame = noise( rng, n, 1.2, 30, n / 3 )
    on = d > joint
    face = lift[block] + tilt_u[block] * ( u - length / 2 ) / p + tilt_v[block] * ( v - rowh / 2 ) / p + 0.08 * dome
    height = np.where( on, face + 0.06 * flame + 0.012 * fine - 0.12 * ( 1.0 - smoothstep( joint, joint + 0.5, d ) ),
                       -0.5 + 0.05 * fine )
    height = T.blur( height, 0.6 )
    tone = BT.tones( rng, [ ( 84, 84, 86 ), ( 104, 103, 102 ), ( 124, 122, 120 ), ( 138, 134, 128 ), ( 150, 144, 136 ),
                            ( 160, 152, 142 ), ( 116, 114, 112 ) ], count, 0.14 )
    red = rng.random( count ) < 0.08                                   # a few red-grey granite
    tone[red] = np.array( ( 132, 114, 104 ), float ) * rng.uniform( 0.88, 1.08, ( red.sum(), 1 ) )
    mica = smoothstep( 1.3, 1.9, noise( rng, n, 0.0, n / 3 ) )
    felds = smoothstep( 1.2, 1.8, noise( rng, n, 0.3, n / 5 ) ) * ( 1.0 - mica )
    lum = 1.0 + 0.04 * flame + 0.03 * fine
    colour = BT.shade( tone[block], lum )
    colour = mix( colour, np.array( ( 52, 52, 54 ), float ), 0.6 * mica )
    colour = mix( colour, lum_paint( ( 190, 184, 176 ), 1.0 + 0.02 * fine ), 0.5 * felds )
    x_, y_ = coords( n )
    lanes = 0.0
    for k, u0 in enumerate( rng.uniform( 0, n, 3 ) ):                  # two or three broad wheel tracks down the tile
        dl = np.abs( ( ( x_ - u0 - 0.03 * n * noise( rng, n, 2.6, 1, 3 ) + n / 2 ) % n ) - n / 2 ) / p
        lanes = np.maximum( lanes, ( 1.0 - smoothstep( 6.0, 16.0, dl ) ) * ( 0.6 + 0.4 * ( k < 2 ) ) )
    track = np.clip( lanes * ( 0.7 + 0.3 * smoothstep( -1.0, 1.0, noise( rng, n, 2.4, 2, 10 ) ) ), 0, 1 )
    oil = blotches( rng, n, 2.4, 2, 40, 0.06, 0.8 )
    rust = blotches( rng, n, 2.6, 3, 60, 0.04, 0.8 )
    colour = darken( colour, ( 1.0 - 0.35 * oil ) * ( 1.0 - 0.15 * track ) )
    colour = tinted( colour, ( 120, 80, 54 ), 0.4 * rust )
    in_joint = 1.0 - smoothstep( joint - 0.05, joint + 0.08, d )
    grit = mix( lum_paint( ( 60, 56, 50 ), 1.0 + 0.15 * fine ), lum_paint( ( 104, 96, 82 ), 1.0 + 0.1 * fine ),
                0.45 * smoothstep( -0.4, 1.4, noise( rng, n, 1.8, 10, 200 ) ) )
    colour = mix( colour, grit, in_joint )
    ao = T.cavity_ao( height, ( ( 0.6 * p, 0.6 ), ( 2.0 * p, 0.3 ) ), 1.0 )
    rough = np.clip( 0.78 + 0.05 * flame - 0.2 * track * dome - 0.25 * oil + 0.12 * in_joint, 0.4, 0.97 )
    return { "rw_setts": T.shaded( colour, ao, 0.6 ) }, rough, height, 1024 / SETTS_TILE


def concrete( rng, n ):
    """ Fair-faced concrete (the underpass, the retaining walls, the goods shed's plinth): cast against framed formwork
    panels 51 x 85 in, five across and three up a 256 in tile, their joints leaving thin fins, with rows of tie holes
    plugged with mortar, bug holes and each panel a shade of its own. rw_concrete is clean; rw_concrete_dark is the
    railway's, streaked with soot and brake dust, white efflorescence weeping from the tie holes. """
    p = n / 256.0
    x, y = coords( n )
    pw, ph = n / 5.0, n / 3.0
    col = np.minimum( ( x // pw ).astype( int ), 4 )
    row = np.minimum( ( y // ph ).astype( int ), 2 )
    panel = row * 5 + col
    u, v = x - col * pw, y - row * ph
    de = np.minimum( np.minimum( u, pw - u ), np.minimum( v, ph - v ) ) / p
    tone = rng.normal( 1.0, 0.03, 15 )
    offset = rng.normal( 0.0, 0.03, 15 )
    fin = 1.0 - smoothstep( 0.03, 0.14, de )
    tie = np.zeros( ( n, n ) )
    cone = np.zeros( ( n, n ) )
    for c in range( 5 ):
        for r in range( 3 ):
            for fu in ( 0.25, 0.75 ):
                for fv in ( 0.18, 0.5, 0.82 ):
                    cx, cy = ( c + fu ) * pw, ( r + fv ) * ph
                    stamp( tie, cx, cy, 0.55 * p, 0.55 * p, 1.0, soft=1.0 )
                    stamp( cone, cx, cy, 0.95 * p, 0.95 * p, 1.0, profile="cone" )
    pits = np.zeros( ( n, n ) )
    for _ in range( int( 2400 * ( n / 2048 ) ** 2 ) ):
        r = rng.uniform( 0.04, 0.2 ) * p
        stamp( pits, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.6, 1.0 ), 1.0, profile="dome" )
    fine = noise( rng, n, 1.0, n / 6 )
    mottle = noise( rng, n, 2.4, 4, 120 )
    lifts = BT.stretched( rng, n, 1.6, 3, 60, ( 2.0, 60.0 ) )
    height = offset[panel] + 0.05 * fin + 0.006 * fine - 0.05 * cone - 0.25 * tie - 0.1 * pits
    lum = tone[panel] * ( 1.0 + 0.04 * mottle + 0.035 * fine + 0.025 * lifts ) * ( 1.0 - 0.5 * pits )
    plug = lum_paint( ( 128, 126, 120 ), 1.0 + 0.05 * fine )
    colours = {}
    c = lum_paint( ( 150, 148, 142 ), lum )
    c = mix( c, plug, tie )
    colours["rw_concrete"] = c
    soot = smoothstep( 0.0, 2.2, 0.7 * streaks( rng, n, 1.6, 2, 80, 90, 2.0 ) + 0.5 * noise( rng, n, 2.8, 1, 10 ) )
    soot *= np.clip( 0.75 + 0.35 * streaks( rng, n, 1.0, 20, 400, 24, 0.6 ), 0.0, 1.2 )
    dust = blotches( rng, n, 2.6, 1, 20, 0.5, 1.5 )
    weep = run_down( tie, 10 * p, 0.5, rng )
    c = lum_paint( ( 132, 130, 124 ), lum )
    c = tinted( c, ( 120, 96, 76 ), 0.3 * dust )
    c = darken( c, 1.0 - 0.55 * soot )
    c = mix( c, plug, tie )
    c = mix( c, lum_paint( ( 204, 202, 194 ), 1.0 + 0.05 * fine ), 0.45 * weep * ( 1.0 - tie ) )
    colours["rw_concrete_dark"] = c
    ao = T.cavity_ao( height, ( ( 2.0, 1.5 ), ), 1.0 )
    colours = { k: T.shaded( v, ao, 0.4 ) for k, v in colours.items() }
    rough = np.clip( 0.86 + 0.04 * fine - 0.04 * fin, 0, 1 )
    return colours, rough, height, 1024 / 256.0


def _chips( rng, n, spacing, gap, matrix_share ):
    """ A tiling Voronoi of stone chips spacing px apart, each shrunk from its cell's edge by its own gap (px), and some
    left out (matrix_share). Returns the chip mask, each px's chip and its distance to the cell's edge. """
    count = int( ( n / spacing ) ** 2 )
    pts = rng.uniform( 0, n, ( count, 2 ) )
    tiled = np.concatenate( [ pts + ( dx * n, dy * n ) for dx in ( -1, 0, 1 ) for dy in ( -1, 0, 1 ) ] )
    x, y = coords( n )
    d, i = cKDTree( tiled ).query( np.stack( [ x.ravel(), y.ravel() ], -1 ), k=2, workers=-1 )
    cell = ( i[:, 0] % count ).reshape( n, n )
    border = ( ( d[:, 1] - d[:, 0] ) * 0.5 ).reshape( n, n )
    g = rng.uniform( gap * 0.5, gap * 1.6, count )
    keep = rng.random( count ) > matrix_share
    chip = smoothstep( g[cell] - 0.6, g[cell] + 0.6, border ) * keep[cell]
    return chip, cell, count


# Round 3: in the engine the round 2 mix (a quarter dark chips at full colour on a darker matrix) read as gravel from
# 3 m on, in the concourse and the booking hall. A station's terrazzo is mostly light marble, the dark and red chips a
# scattering, and grinding leaves the chips little brighter than the matrix round them (TERRAZZO_GROUND).
TERRAZZO_CHIPS = [ ( 6, ( 226, 224, 218 ) ), ( 5, ( 204, 200, 192 ) ), ( 4, ( 176, 174, 170 ) ), ( 3, ( 214, 202, 182 ) ),
                   ( 1.2, ( 118, 116, 114 ) ), ( 0.5, ( 70, 70, 72 ) ), ( 1.0, ( 162, 120, 100 ) ), ( 1, ( 192, 172, 136 ) ) ]
TERRAZZO_MATRIX = ( 174, 168, 154 )
TERRAZZO_GROUND = ( 0.3, 0.38 )                     # how far the big and small chips' colours sit towards the matrix
TERRAZZO_BRASS = ( 150, 120, 70 )


def terrazzo( rng, n ):
    """ The concourse's terrazzo as laid about 1900 (Venetian): marble chips 8-20 mm at full colour with finer 4-8 mm
    ones between, three in four white or grey and a quarter dark grey, black or red, in a slightly darker grey-beige
    cement matrix (round 2: the 0.36 in chips mipped to a salt-and-pepper speckle, like vinyl tile), 4096 px over the
    192 in tile since the hall is walked at 1-3 m; cast in panels 48 in
    wide and 38.4 in deep (four by five to a 192 in tile) divided by 0.25 in brass strips. Ground flat and polished
    (roughness 0.24-0.3), dulled matte in broad walking lanes and scratched. rw_terrazzo has the warm grey matrix;
    rw_terrazzo_border an anthracite one, for the bands and borders. """
    p = n / 192.0
    x, y = coords( n )
    big, big_cell, big_count = _chips( rng, n, 0.8 * p, 0.08 * p, 0.2 )
    small, small_cell, small_count = _chips( rng, n, 0.35 * p, 0.04 * p, 0.45 )
    small = small * ( 1.0 - big )
    big_colour = T.stone_colours( rng, big_count, TERRAZZO_CHIPS, 0.06 )
    small_colour = T.stone_colours( rng, small_count, TERRAZZO_CHIPS, 0.06 )
    vein = noise( rng, n, 1.2, 30, n / 3 )
    fine = noise( rng, n, 0.6, n / 6 )
    chips = big_colour[big_cell] * ( 1.0 + 0.05 * vein )[..., None]
    chips_s = small_colour[small_cell] * ( 1.0 + 0.04 * fine )[..., None]
    pw, ph = n / 4.0, n / 5.0
    su, sv = x % pw, y % ph
    de = np.minimum( np.minimum( su, pw - su ), np.minimum( sv, ph - sv ) ) / p
    joint = 1.0 - smoothstep( 0.105, 0.155, de )                                    # the brass strip, 0.25 in
    lane = smoothstep( -0.8, 1.4, noise( rng, n, 2.6, 1, 4 ) )
    walked = np.clip( lane * ( 0.7 + 0.3 * smoothstep( -1.0, 1.0, noise( rng, n, 2.0, 6, 40 ) ) ), 0, 1 )
    canvas = Canvas( n, 2, int( 8 * p ) )
    for _ in range( int( 500 * ( n / 2048 ) ** 2 ) ):
        x_, y_ = rng.uniform( 0, n, 2 )
        a = rng.uniform( 0, 2 * math.pi )
        length = rng.uniform( 1.0, 7.0 ) * p
        bend = rng.normal( 0, 0.15 )
        pts = [ ( x_ + math.cos( a + bend * t ) * length * t, y_ + math.sin( a + bend * t ) * length * t )
                for t in np.linspace( 0, 1, 6 ) ]
        canvas.line( pts, rng.uniform( 0.3, 0.7 ), rng.uniform( 0.4, 1.0 ) )
    scratches = canvas.result()
    stone = big + small
    tarnish = smoothstep( -1.0, 1.5, noise( rng, n, 2.0, 4, 80 ) )
    brass = lum_paint( TERRAZZO_BRASS, 1.0 + 0.08 * fine - 0.25 * tarnish )
    colours = {}
    for name, matrix in ( ( "rw_terrazzo", TERRAZZO_MATRIX ), ( "rw_terrazzo_border", ( 70, 72, 74 ) ) ):
        m = lum_paint( matrix, 1.0 + 0.03 * fine + 0.02 * vein )
        # Ground flat, the chips' colours sit part of the way to the matrix's.
        c = mix( m, mix( chips, m, TERRAZZO_GROUND[0] ), big )
        c = mix( c, mix( chips_s, m, TERRAZZO_GROUND[1] ), small )
        c = darken( c, 1.0 - 0.05 * walked )
        haze = 0.05 * walked + 0.08 * scratches
        c = srgb( lin( c ) * ( 1.0 - haze[..., None] ) + lin( ( 170, 166, 158 ) ) * haze[..., None] )
        c = mix( c, brass, joint )
        colours[name] = c
    rough = 0.28 - 0.04 * stone + 0.008 * fine
    rough = rough + 0.2 * walked + 0.22 * scratches
    rough = rough + ( 0.35 - rough ) * joint
    height = 0.003 * stone + 0.002 * fine + 0.01 * joint - 0.004 * scratches
    return colours, np.clip( rough, 0.1, 1 ), height, 1024 / 192.0


SANDSTONE = [ ( 198, 176, 138 ), ( 190, 168, 128 ), ( 204, 184, 150 ), ( 182, 160, 124 ), ( 196, 170, 140 ), ( 176, 166, 140 ) ]
# Main sandstone ashlar in the sun, warm yellow-grey: the blocks' colours, the odd greyer or yellower one from another
# bed of the quarry, and the lime mortar of the flush joints.
ASHLAR = [ ( 188, 172, 138 ), ( 182, 166, 132 ), ( 193, 177, 143 ), ( 179, 167, 140 ), ( 190, 171, 133 ), ( 185, 169, 142 ),
           ( 176, 162, 131 ) ]
ASHLAR_ODD = [ ( 176, 168, 150 ), ( 194, 175, 134 ), ( 186, 166, 140 ) ]
ASHLAR_MORTAR = ( 180, 172, 154 )
SANDSTONE_TILE = 192.0


def ashlar( rng, n ):
    """ The station's walls, outside and in the shed: Main sandstone ashlar of about 1900, 4096 px over a 192 in tile
    (21 px an inch). Courses 14-20 in (35-50 cm), blocks 24-40 in, each block dressed with a smooth drafted margin an
    inch wide round a finely tooled (scharriert) field, its face a hair out of plane with its neighbours', so each
    catches the light its own way. Flush lime joints 0.2 in wide, set back 0.1 in, their arrises softly rounded and
    chipped here and there. Warm yellow-grey, each block a shade of its own and the odd one from another bed, with
    bedding laminations, iron spots and the odd brown Liesegang band; the scan's pores and grains (railhead_scanned's
    sandstone_grain) inside each block, from its own place in the scan. rw_sandstone is the lower walls, grimy in the
    joints and faintly washed; rw_sandstone_soot the upper courses, under a century's black gypsum crust (0.6) except
    where the rain washes it in pale streaks. """
    import railhead_scanned
    tile = SANDSTONE_TILE
    p = n / tile
    x, y = coords( n )
    block, u, v, length, rowh, row, count = BT.coursed( rng, n, ( 14 * p, 20 * p ), ( 24 * p, 40 * p ) )
    d = np.minimum( np.minimum( u, length - u ), np.minimum( v, rowh - v ) ) / p          # inches to the block's edge
    joint = 0.1                                                                         # half a 0.2 in joint
    arris = smoothstep( joint, joint + 0.28, d )
    margin = smoothstep( 0.85, 1.15, d )                                                # the drafted margin's inner edge
    # The tooled field: fine parallel strokes 0.18 in apart, upright or slanting a little, block by block.
    slant = rng.uniform( -0.25, 0.25, count )
    phase = rng.uniform( 0, 2 * math.pi, count )
    tool = np.sin( 2 * math.pi * ( u + slant[block] * v ) / ( 0.18 * p ) + phase[block]
                   + 0.8 * noise( rng, n, 2.0, 16, 400 ) )
    tool *= 0.5 + 0.5 * smoothstep( -1.0, 1.0, noise( rng, n, 1.6, 20, 300 ) )
    # Each face a little out of plane: a tilt and a faint pillow.
    tu, tv = rng.normal( 0, 0.0012, ( 2, count ) )                                      # inches an inch
    plane = rng.normal( 0, 0.02, count )
    pu, pv = ( u / length - 0.5 ) * 2.0, ( v / rowh - 0.5 ) * 2.0
    pillow = ( 1.0 - pu ** 4 ) * ( 1.0 - pv ** 4 )
    # Chipped arrises: small spalls along the edges, more at the corners.
    chipn = noise( rng, n, 1.4, 30, 600 )
    corner = np.minimum( np.minimum( u, length - u ), 9 * p ) + np.minimum( np.minimum( v, rowh - v ), 9 * p )
    chip = smoothstep( 2.15, 2.55, chipn + 0.9 * ( 1.0 - smoothstep( 0, 10 * p, corner ) ) ) * ( d < 1.0 ) * ( d > joint )
    on_block = d > joint
    face = ( plane[block] + tu[block] * ( u - length / 2 ) / p + tv[block] * ( v - rowh / 2 ) / p + 0.02 * pillow
             + 0.008 * tool * margin )
    height = np.where( on_block, face - 0.05 * ( 1.0 - arris ) - 0.06 * chip, -0.1 )
    grain, detail, grain_rough = railhead_scanned.sandstone_grain( block, u, v, length, rowh, count, rng, amount=0.2 )
    height = height + 0.006 * ( grain - 1.0 ) * on_block
    height = T.blur( height, 0.5 )

    # Colour: the block's tone, its bedding, iron and the scan's grain.
    # Round 2: at 30 m a 6 % spread block to block read as a light/dark checkerboard; 4 %, with the hues kept, and the
    # blocks grouped into washed and crusted zones by a 3-5 m patina cloud (zone, below).
    tone = BT.tones( rng, ASHLAR, count, 0.04, 1.0 )
    odd = rng.random( count ) < 0.05
    tone[odd] = np.array( ASHLAR_ODD, float )[rng.integers( 0, len( ASHLAR_ODD ), odd.sum() )]
    lam = BT.stretched( rng, n, 1.6, 6, 400, ( 1.0, 60.0 ) )
    lam2 = BT.stretched( rng, n, 1.4, 10, 600, ( 0.6, 24.0 ) )
    bedded = rng.uniform( 0.3, 1.0, count )
    mottle = noise( rng, n, 2.6, 4, 160 )
    fine = noise( rng, n, 0.6, n / 4 )
    # Each block weathers on its own: a cloud of darker and paler patina, water held along its upper bed joint and
    # drying out paler towards its foot.
    patina = noise( rng, n, 2.2, 3, 40 )
    wet = 1.0 - smoothstep( 0.0, 0.35, v / rowh + 0.08 * noise( rng, n, 1.6, 10, 200 ) )
    lum = ( ( 1.0 + bedded[block] * ( 0.05 * lam + 0.02 * lam2 ) + 0.05 * mottle + 0.035 * patina + 0.012 * fine )
            * ( 1.0 - 0.06 * wet ) * grain )
    colour = BT.shade( tone[block], lum )
    # Iron: freckles in some blocks, a brown Liesegang band in a few.
    freckled = rng.random( count ) < 0.35
    spots = np.zeros( ( n, n ) )
    for _ in range( int( 2600 * ( n / 4096 ) ** 2 ) ):
        r = rng.uniform( 0.03, 0.12 ) * p
        stamp( spots, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.6, 1.0 ), rng.uniform( 0.4, 1.0 ),
               rng.uniform( 0, 3.2 ), soft=0.8 )
    spots *= freckled[block]
    banded = rng.random( count ) < 0.05
    band_phase = rng.uniform( 0, 2 * math.pi, count )
    band = smoothstep( 0.82, 0.97, np.sin( 2 * math.pi * ( v + 0.3 * u ) / ( 3.4 * p ) + band_phase[block]
                                          + 1.4 * noise( rng, n, 2.4, 3, 60 ) ) ) * banded[block]
    colour = tinted( colour, ( 150, 98, 58 ), np.clip( 0.5 * spots + 0.2 * band, 0, 1 ) )
    mortar = 1.0 - smoothstep( joint - 0.02, joint + 0.03, d )
    colour = mix( colour, lum_paint( ASHLAR_MORTAR, 1.0 + 0.06 * fine + 0.03 * mottle ), mortar )
    ao = T.cavity_ao( height, ( ( 0.6 * p, 0.5 ), ( 2.5 * p, 0.25 ) ), 1.0 )

    # Weathering.
    joint_dirt = ( 1.0 - smoothstep( joint, joint + 0.6, d ) ) * smoothstep( -0.8, 1.2, noise( rng, n, 2.0, 6, 200 ) )
    washed = smoothstep( 0.6, 2.2, streaks( rng, n, 2.0, 3, 64, 700, 3.0 ) )
    grime = smoothstep( -0.5, 2.2, 0.6 * noise( rng, n, 3.0, 1, 8 ) + 0.6 * streaks( rng, n, 1.6, 2, 80, 100, 2.0 ) )
    colours = {}
    broad = noise( rng, n, 3.0, 1, 3 )                                                # +-8 % across the wall
    zone = smoothstep( -1.2, 1.2, noise( rng, n, 3.4, 1, 1.6 ) )                        # washed (1) and crusted (0) zones
    c = darken( colour, ( 1.0 - 0.22 * joint_dirt ) * ( 1.0 - 0.1 * grime ) * ( 1.0 + 0.04 * washed ) * ( 1.0 + 0.08 * broad )
                * ( 0.94 + 0.08 * zone ) )
    c = tinted( c, ( 120, 114, 104 ), 0.12 * ( 1.0 - zone ) )
    colours["rw_sandstone"] = T.shaded( c, ao, 0.5 )
    per_block = rng.uniform( 0.0, 1.0, count ) ** 0.8
    crust = np.clip( 0.55 + 0.18 * per_block[block] + 0.15 * smoothstep( -1.0, 1.6, noise( rng, n, 3.0, 1, 8 ) )
                     + 0.05 * noise( rng, n, 2.2, 6, 120 ) - 0.05, 0.0, 1.0 )
    crust = crust * ( 1.0 - 0.65 * washed )
    crust = np.clip( crust + 0.4 * ( 1.0 - arris ) + 0.25 * joint_dirt, 0.0, 1.0 )
    soot = lum_paint( ( 62, 58, 52 ), 1.0 + 0.12 * fine + 0.06 * mottle ) * grain[..., None] ** 0.5
    c = mix( colour, soot, 0.82 * smoothstep( 0.05, 0.9, crust ) )
    c = srgb( lin( c ) * ( 1.0 + 0.1 * washed * ( 1.0 - crust ) )[..., None] )
    colours["rw_sandstone_soot"] = T.shaded( c, ao, 0.5 )
    rough = np.clip( 0.86 + 0.04 * fine + 0.06 * ( grain_rough - 0.5 ) - 0.03 * crust + 0.06 * mortar, 0.72, 0.97 )
    return colours, rough, height, 1024 / tile, { "detail_normal": ( detail, 0.45 ) }


def sandstone( rng, n ):
    """ The station's walls: buff sandstone ashlar in courses 18-26 in high, blocks 32-62 in long, their joints cut as a
    V an inch deep (rusticated) round a thin line of lime mortar; each block a shade of its own, faintly pillowed, with
    bedding laminations, iron spots, a black crust of a century's soot where the rain doesn't reach, and paler streaks
    where it washes down. """
    p = n / 192.0
    block, u, v, length, rowh, row, count = BT.coursed( rng, n, ( 18 * p, 26 * p ), ( 32 * p, 62 * p ) )
    d = np.minimum( np.minimum( u, length - u ), np.minimum( v, rowh - v ) ) / p
    chamfer = smoothstep( 0.18, 1.1, d )
    pu, pv = ( u / length - 0.5 ) * 2.0, ( v / rowh - 0.5 ) * 2.0
    pillow = ( 1.0 - pu ** 4 ) * ( 1.0 - pv ** 4 )
    tool = noise( rng, n, 1.4, 20, n / 3 )
    fine = noise( rng, n, 0.6, n / 4 )
    height = -1.0 + chamfer * ( 1.0 + 0.15 * pillow + 0.02 * tool ) + 0.004 * fine
    tone = BT.tones( rng, SANDSTONE, count, 0.035, 0.7 )
    lam = BT.stretched( rng, n, 1.6, 6, 240, ( 1.2, 40.0 ) )
    mottle = noise( rng, n, 2.6, 4, 120 )
    iron = blotches( rng, n, 1.6, 30, 400, 0.025, 0.6 )
    lum = ( 1.0 + 0.05 * lam + 0.04 * mottle + 0.04 * fine + 0.02 * tool )
    colour = BT.shade( tone[block], lum )
    colour = tinted( colour, ( 156, 104, 62 ), 0.5 * iron )
    mortar = 1.0 - smoothstep( 0.12, 0.22, d )
    colour = mix( colour, lum_paint( ( 176, 170, 158 ), 1.0 + 0.05 * fine ), mortar )
    washed = smoothstep( 0.2, 1.8, streaks( rng, n, 1.8, 2, 120, 120, 3.0 ) )
    per_block = rng.uniform( 0.0, 1.0, count ) ** 1.6
    within = noise( rng, n, 2.2, 3, 60 )
    crust = np.clip( 0.55 * per_block[block] + 0.45 * smoothstep( -1.0, 1.6, noise( rng, n, 3.0, 1, 6 ) )
                     + 0.12 * within - 0.15, 0.0, 1.0 ) * ( 1.0 - 0.75 * washed )
    crust = np.clip( crust + 0.35 * ( 1.0 - chamfer ) * smoothstep( 0.1, 0.5, crust ), 0.0, 1.0 )
    colour = mix( colour, lum_paint( ( 58, 54, 48 ), 1.0 + 0.1 * fine ), 0.7 * smoothstep( 0.05, 0.95, crust ) )
    colour = srgb( lin( colour ) * ( 1.0 + 0.12 * washed * ( 1.0 - crust ) )[..., None] )
    ao = T.cavity_ao( height, ( ( 1.5 * p, 0.35 ), ( 4.0 * p, 0.2 ) ), 1.0 )
    rough = np.clip( 0.88 + 0.03 * fine - 0.04 * crust, 0, 1 )
    return { "rw_sandstone": T.shaded( colour, ao, 0.5 ) }, rough, height, 1024 / 192.0


DRESSED_BEDS = [ ( 180, 160, 120 ), ( 168, 158, 136 ), ( 184, 156, 110 ), ( 192, 178, 148 ), ( 172, 154, 122 ),
                 ( 176, 164, 132 ) ]
DRESSED_RED_BEDS = [ ( 148, 98, 82 ), ( 138, 96, 84 ), ( 156, 106, 84 ), ( 132, 88, 76 ), ( 152, 112, 94 ), ( 142, 94, 76 ) ]
DRESSED_MORTAR = ( 138, 130, 116 )


def dressed( rng, n ):
    """ Dressed stone for the booking hall's piers, pilasters, arches, cornices and balustrade, the plinths, quoins and
    sills: smooth tooled blocks in courses 20-28 in high, 36-64 in long. Main sandstone of about 1900: each block a bed
    of its own (DRESSED_BEDS: yellow-buff, grey-buff, ochre, pale, a 12 % spread), one in twelve crossed by a red-brown
    Liesegang band, bedding laminations, iron blotches over 1-2 % of the face, and the scan's pores and grains from each
    block's own place in it (railhead_scanned.sandstone_grain). The faces are droved (parallel chisel strokes 0.22 in
    apart, 0.02 in deep) so raking lamp light shows the tooling at 2-5 m. Lime joints 0.3 in wide set back 0.25 in in a
    darker mortar, dirt held at the arrises and in streaks below them, so the courses read at 10 m. It sits darker than
    the painted plaster, as the stone frame of a real hall does. rw_dressed_red is the red Main sandstone. """
    import railhead_scanned
    p = n / 96.0
    x, y = coords( n )
    block, u, v, length, rowh, row, count = BT.coursed( rng, n, ( 20 * p, 28 * p ), ( 36 * p, 64 * p ) )
    d = np.minimum( np.minimum( u, length - u ), np.minimum( v, rowh - v ) ) / p
    phase = rng.uniform( 0, 2 * math.pi, count )
    slant = rng.uniform( -0.12, 0.12, count )
    pitch = 0.22 * p
    drove = np.sin( 2 * math.pi * ( x + slant[block] * y ) / pitch + phase[block] + 0.6 * noise( rng, n, 2.0, 8, 200 ) )
    drove *= 0.55 + 0.45 * noise( rng, n, 1.6, 10, 200 )
    fine = noise( rng, n, 0.6, n / 4 )
    mottle = noise( rng, n, 2.6, 3, 80 )
    bedding = BT.stretched( rng, n, 1.6, 6, 300, ( 1.0, 40.0 ) )
    bedding2 = BT.stretched( rng, n, 1.4, 10, 500, ( 0.6, 18.0 ) )
    bedded = rng.uniform( 0.3, 1.0, count )
    joint = 0.15                                                        # half a 0.3 in joint
    bevel = smoothstep( joint, joint + 0.35, d )
    chipn = noise( rng, n, 1.4, 30, 600 )
    corner = np.minimum( np.minimum( u, length - u ), 6 * p ) + np.minimum( np.minimum( v, rowh - v ), 6 * p )
    chip = smoothstep( 2.1, 2.5, chipn + 0.7 * ( 1.0 - smoothstep( 0, 7 * p, corner ) ) ) * ( d < 0.9 ) * ( d > joint )
    grain, detail, grain_rough = railhead_scanned.sandstone_grain( block, u, v, length, rowh, count, rng, amount=0.08 )
    tu, tv = rng.normal( 0, 0.0008, ( 2, count ) )                      # each face a hair out of plane
    face = tu[block] * ( u - length / 2 ) / p + tv[block] * ( v - rowh / 2 ) / p
    height = np.where( d > joint, face - 0.2 * ( 1.0 - bevel ) + 0.02 * drove * bevel - 0.1 * chip, -0.25 )
    height = height + 0.002 * fine + 0.004 * ( grain - 1.0 ) / 0.08
    height = T.blur( height, 0.5 )
    mortar = 1.0 - smoothstep( joint - 0.02, joint + 0.04, d )
    arris = ( 1.0 - bevel ) * ( 1.0 - mortar )
    near_joint = 1.0 - smoothstep( joint, joint + 1.2, d )
    # Dirt: held at the arrises and in the joints, and in streaks running down from the bed joints (rain on the
    # outside, cleaners' water and dust inside), with a broad cloud across the wall.
    bed_top = ( 1.0 - smoothstep( 0.0, 1.5, v / p ) ) * ( d > joint )
    held = run_down( bed_top, 6 * p, fall=0.8 ) * smoothstep( -0.6, 1.4, streaks( rng, n, 1.6, 3, 90, 60, 1.6 ) )
    dirt = smoothstep( 0.0, 2.0, streaks( rng, n, 1.8, 2, 80, 60, 2.0 ) + 0.5 * noise( rng, n, 2.8, 1, 12 ) )
    broad = noise( rng, n, 3.0, 1, 4 )
    iron = blotches( rng, n, 1.6, 30, 400, 0.015, 0.6 )
    banded = rng.random( count ) < 1.0 / 12.0
    band_phase = rng.uniform( 0, 2 * math.pi, count )
    # Liesegang bands: soft, broad wavy rings of iron, not lines.
    band = smoothstep( 0.35, 0.95, np.sin( 2 * math.pi * ( v + 0.3 * u ) / ( 7.0 * p ) + band_phase[block]
                                          + 1.8 * noise( rng, n, 3.0, 2, 16 ) ) ) * banded[block]
    band = T.blur( band, 0.3 * p )
    freckled = rng.random( count ) < 0.3
    spots = np.zeros( ( n, n ) )
    for _ in range( int( 900 * ( n / 2048 ) ** 2 ) ):
        r = rng.uniform( 0.03, 0.1 ) * p
        stamp( spots, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.6, 1.0 ), rng.uniform( 0.4, 1.0 ),
               rng.uniform( 0, 3.2 ), soft=0.8 )
    spots *= freckled[block]
    ao = T.cavity_ao( height, ( ( 0.5 * p, 0.7 ), ( 2.0 * p, 0.3 ) ), 1.0 )
    colours = {}
    for name, beds in ( ( "rw_dressed", DRESSED_BEDS ), ( "rw_dressed_red", DRESSED_RED_BEDS ) ):
        tone = BT.tones( rng, beds, count, 0.12, 0.85 )
        lum = ( 1.0 + bedded[block] * ( 0.05 * bedding + 0.02 * bedding2 ) + 0.02 * drove * bevel + 0.03 * mottle
                + 0.01 * fine + 0.05 * broad ) * grain
        c = BT.shade( tone[block], lum )
        c = tinted( c, ( 156, 104, 62 ), np.clip( 0.5 * iron + 0.45 * spots + 0.3 * band, 0, 1 ) )
        c = darken( c, ( 1.0 - 0.2 * arris - 0.12 * chip ) * ( 1.0 - 0.1 * near_joint ) * ( 1.0 - 0.12 * held ) )
        c = mix( c, lum_paint( DRESSED_MORTAR, 1.0 + 0.05 * fine + 0.03 * mottle ), mortar )
        c = darken( c, 1.0 - 0.1 * dirt )
        colours[name] = T.shaded( c, ao, 0.55 )
    rough = np.clip( 0.8 + 0.03 * fine + 0.05 * drove * bevel + 0.1 * mortar + 0.06 * ( grain_rough - 0.5 ), 0.7, 0.98 )
    return colours, rough, height, 1024 / 96.0, { "detail_normal": ( detail, 0.3 ) }


STEEL_GREEN = ( 70, 80, 75 )


def _old_paint( rng, n, p, base, height, hot, wear=None, drips=False ):
    """ Old paint on riveted iron: base, chipped down to red lead and then rust where hot (0..1, the rivets' and edges'
    nearness) says it wears first, rust bleeding out and running down, soot over it. wear (per px, about -1..1) moves
    the chipping up or down by area; drips adds the runs and sags of many hand-brushed coats. Returns colour and
    roughness. """
    fine = noise( rng, n, 0.8, n / 6 )
    mottle = noise( rng, n, 2.4, 3, 80 )
    chipn = noise( rng, n, 1.4, 12, n / 3 )
    if wear is not None:
        chipn = chipn + 0.45 * wear
    chip = smoothstep( 2.05, 2.25, chipn + 1.1 * hot )
    deep = smoothstep( 2.45, 2.65, chipn + 1.1 * hot )
    colour = lum_paint( base, ( 1.0 + 0.05 * mottle + 0.025 * fine ) )
    if drips:
        # Sags under the rivet rows and edges where the coats ran: a hair darker and glossier.
        runs = run_down( np.clip( hot * smoothstep( 0.8, 2.2, noise( rng, n, 1.0, 40, n / 3 ) ), 0, 1 ), 3.0 * p, 0.8 )
        colour = darken( colour, 1.0 - 0.06 * runs )
    colour = mix( colour, lum_paint( ( 156, 72, 48 ), 1.0 + 0.08 * fine ), chip )
    colour = mix( colour, lum_paint( ( 104, 58, 38 ), 1.0 + 0.12 * fine ), deep )
    bleed = run_down( np.clip( 0.6 * deep + 0.35 * smoothstep( 0.4, 0.9, hot ) * smoothstep( 0.5, 2.0, chipn ), 0, 1 ),
                      14 * p, 0.6, rng )
    colour = mix( colour, lum_paint( ( 120, 70, 44 ), 1.0 + 0.1 * fine ), 0.45 * bleed * ( 1.0 - chip ) )
    soot = smoothstep( -0.4, 2.6, 0.35 * noise( rng, n, 3.0, 1, 5 ) + 0.9 * streaks( rng, n, 1.6, 2, 60, 80, 1.5 ) )
    colour = darken( colour, 1.0 - 0.28 * soot )
    rough = np.clip( 0.55 + 0.05 * fine + 0.1 * soot + 0.25 * chip + 0.1 * deep + 0.1 * bleed, 0, 1 )
    return colour, rough


def _weather_iron( rng, n, p, colour, rivets, bleed_in=( 2.0, 4.0 ) ):
    """ The wear old riveted ironwork shows in diffuse light, in its colour: the top coat chalked paler in broad blotches,
    rust bleeding 2-4 in down from about a third of the rivet heads (where the paint cracked round them), soot darkening
    some areas by a fifth, and darker drip tracks where the coats ran. rivets is the rivets' height field. """
    fine = noise( rng, n, 0.8, n / 6 )
    chalk = smoothstep( -0.8, 1.8, noise( rng, n, 3.0, 1, 10 ) + 0.25 * noise( rng, n, 1.8, 10, 60 ) )
    c = srgb( lin( colour ) * ( 1.0 + 0.16 * chalk )[..., None] )
    c = tinted( c, ( 132, 138, 130 ), 0.15 * chalk )
    heads = smoothstep( 0.02, 0.15, rivets )
    which = blotches( rng, n, 1.0, n / ( 14 * p ), n / ( 5 * p ), 0.3, 0.15 )   # about a third of the heads
    src = T.blur( heads * which, 0.35 * p )
    bleed = np.clip( run_down( src, bleed_in[1] * p, 0.7, rng ) * 1.6, 0, 1 )
    bleed = bleed * ( 0.6 + 0.4 * smoothstep( -1.0, 1.0, noise( rng, n, 1.4, 20, n / 4 ) ) )
    c = mix( c, lum_paint( ( 120, 70, 40 ), 1.0 + 0.12 * fine ), 0.85 * bleed )
    soot = blotches( rng, n, 2.8, 1, 5, 0.4, 0.9 ) * ( 0.7 + 0.3 * smoothstep( -1.0, 2.0, streaks( rng, n, 1.6, 2, 60, 80, 1.5 ) ) )
    c = darken( c, 1.0 - 0.22 * soot )
    drips = smoothstep( 0.8, 2.4, streaks( rng, n, 1.2, 6, 200, 60, 0.5 ) ) * blotches( rng, n, 2.0, 2, 20, 0.5, 0.8 )
    c = darken( c, 1.0 - 0.12 * drips )
    return c, bleed, soot


STEEL_TILE = 128.0


def steel( rng, n ):
    """ The train shed's riveted wrought iron, the footbridge and the old girders, 2048 px over a 128 in tile (16 px an
    inch): plates painted dark grey-green, a lap seam along u at the tile's edge with two staggered rows of 28 mm snap
    heads on each side (3.5 in pitch), and one cover strap 5 in wide down the tile off its centre with its own two rows.
    Many coats of brushed lead paint, brush marks along v and sags under the rivets, chipped to red lead and rust round
    the rivets and edges (more in some parts of the tile than others), rust bleeding and running down, dulled with
    soot. rw_steel is the iron within reach; rw_steel_soot the ironwork high in the shed, under a crust of soot. """
    p = n / STEEL_TILE
    x, y = coords( n )
    pitch = 3.5 * p
    head = 0.55 * p                                              # 28 mm heads
    # The lap seam along u at the tile's edge (y = 0): the upper plate 0.3 in proud above it.
    dy = np.minimum( y, n - y )
    # One cover strap down the tile, off its centre.
    sx0 = 0.37 * n
    sxd = np.abs( x - sx0 )
    strap = smoothstep( 2.6 * p, 2.45 * p, sxd )
    rivets = np.zeros( ( n, n ) )
    count = int( round( n / pitch ) )
    step = n / count
    for k in range( count ):
        for ry, shift in ( ( 1.6 * p, 0.0 ), ( 3.6 * p, 0.5 ), ( n - 1.6 * p, 0.0 ), ( n - 3.6 * p, 0.5 ) ):
            rx = ( k + 0.25 + shift ) * step
            if abs( rx - sx0 ) > 3.0 * p:
                stamp( rivets, rx, ry, head, head, 0.4, profile="dome" )
        for cx, shift in ( ( sx0 - 1.2 * p, 0.0 ), ( sx0 + 1.2 * p, 0.5 ) ):
            ry = ( k + 0.6 + shift ) * step
            if min( ry, n - ry ) > 5.0 * p:
                stamp( rivets, cx, ry, head, head, 0.4, profile="dome" )
    fine = noise( rng, n, 0.8, n / 6 )
    brush = streaks( rng, n, 0.6, 30, n / 2, 40, 0.4 )            # brush marks along v
    # The plates' butt joint along u at the tile's edge, under a cover plate 5.4 in wide (0.3 in proud) carrying the
    # two staggered rows each side.
    cover = smoothstep( 5.4 * p, 5.2 * p, dy )
    height = 0.3 * np.maximum( strap, cover ) + rivets + 0.004 * fine + 0.0025 * brush
    height = T.blur( height, 0.6 )
    rim = ndimage.maximum_filter( ( rivets > 0.02 ).astype( float ), size=int( 0.5 * p ) * 2 + 1, mode="wrap" )
    edge = np.maximum( smoothstep( 2.8 * p, 2.6 * p, sxd ) * ( 1.0 - smoothstep( 2.4 * p, 2.2 * p, sxd ) ),
                       smoothstep( 0.4 * p, 0.0, np.abs( dy - 5.3 * p ) ) )
    hot = T.blur( np.maximum( rim * 0.8, edge ), 0.6 * p )
    # Chipping varies by area: one quarter of the tile worn more, one less.
    qx, qy = ( x // ( n / 2 ) ).astype( int ), ( y // ( n / 2 ) ).astype( int )
    quad = rng.uniform( -1.0, 1.0, ( 2, 2 ) )
    wear = T.blur( quad[qy, qx], 6 * p ) + 0.5 * noise( rng, n, 2.4, 1, 6 )
    colour, rough = _old_paint( rng, n, p, STEEL_GREEN, height, hot, wear=wear, drips=True )
    colour, bleed, soot_w = _weather_iron( rng, n, p, colour, rivets )
    rough = np.clip( 0.45 + 0.25 * ( rough - 0.55 ) / 0.45 + 0.12 * bleed + 0.08 * soot_w, 0.42, 0.78 )
    ao = T.cavity_ao( height, ( ( 0.4 * p, 0.6 ), ( 1.5 * p, 0.3 ) ), 1.0 )
    colours = { "rw_steel": T.shaded( colour, ao, 0.45 ) }
    # High up: a soot crust half covering it, a third darker, matt.
    crust = np.clip( 0.5 + 0.3 * noise( rng, n, 2.6, 1, 10 ) + 0.25 * streaks( rng, n, 1.6, 2, 60, 80, 1.5 )
                     + 0.25 * ( 1.0 - smoothstep( 0.0, 0.6, hot ) ) - 0.2, 0, 1 )
    soot = lum_paint( ( 40, 40, 38 ), 1.0 + 0.1 * fine )
    c = darken( colour, 0.7 )
    c = mix( c, soot, 0.55 * crust )
    colours["rw_steel_soot"] = T.shaded( c, ao, 0.5 )
    return colours, rough, height, 1024 / STEEL_TILE


STEEL_MODERN_TILE = 128.0


def steel_modern( rng, n ):
    """ Modern powder-coated steel (the platform canopies' columns, the footbridge's posts and railings, signal posts,
    cabinets), 2048 px over a 128 in tile: satin (roughness about 0.4) with a fine orange peel, chalked a little, worn
    glossier and grimy where hands go, scratched lighter through the coat, the ghosts of two or three peeled-off
    stickers (a cleaner, glossier rectangle with a ring of glue grime). Round 2 (it read as an even fine-speckle
    hammer finish with round rust blobs): the orange peel is faint, the sheen shifts broadly over 1-3 m (roughness
    +-0.1), dust settles in a soft gradient down the tile, and the rust gathers along a plate seam and its bolt row and
    runs down from them. rw_steel_dark is RAL 7016 anthracite, rw_steel_grey RAL 7035 light grey. """
    p = n / STEEL_MODERN_TILE
    x, y = coords( n )
    peel = noise( rng, n, 1.0, n / 14 )
    mottle = noise( rng, n, 2.6, 2, 40 )
    chalk = smoothstep( -0.6, 1.8, noise( rng, n, 2.8, 1, 8 ) )
    canvas = Canvas( n, 2, int( 10 * p ) )
    for _ in range( 140 ):
        x_, y_ = rng.uniform( 0, n, 2 )
        a = rng.uniform( 0, 2 * math.pi )
        length = rng.uniform( 0.4, 5.0 ) * p
        bend = rng.normal( 0, 0.1 )
        pts = [ ( x_ + math.cos( a + bend * t ) * length * t, y_ + math.sin( a + bend * t ) * length * t ) for t in np.linspace( 0, 1, 5 ) ]
        canvas.line( pts, rng.uniform( 0.5, 1.4 ), rng.uniform( 0.3, 1.0 ) )
    scratches = canvas.result()
    scuff = blotches( rng, n, 2.2, 3, 60, 0.08, 0.8 )
    grime = smoothstep( 0.0, 2.2, streaks( rng, n, 1.6, 2, 60, 50, 1.5 ) )
    hands = smoothstep( -0.2, 1.8, noise( rng, n, 2.6, 1, 6 ) )
    # Sticker ghosts: rectangles 3-8 in, cleaner and glossier, with a grey ring of old glue.
    ghost = np.zeros( ( n, n ) )
    ring = np.zeros( ( n, n ) )
    for _ in range( 3 ):
        x0, y0 = rng.uniform( 0, n, 2 )
        w, h = rng.uniform( 3, 8 ) * p, rng.uniform( 2, 6 ) * p
        inside, edge = _rect_wrap( x, y, x0, y0, w, h, n )
        ghost = np.maximum( ghost, inside * smoothstep( 0.0, 0.3 * p, edge ) * rng.uniform( 0.5, 1.0 ) )
        ring = np.maximum( ring, ( 1.0 - smoothstep( 0.0, 0.25 * p, np.abs( edge ) ) ) * rng.uniform( 0.5, 1.0 ) )
    ghost = ghost * smoothstep( -1.0, 0.8, noise( rng, n, 1.6, 8, 80 ) )
    # A plate seam across the tile with its row of bolts (every 4 in), and a short upright one: the rust gathers
    # there (water stands in a seam) and at a few of the bolts, and runs down.
    bolts = np.zeros( ( n, n ) )
    rusty = np.zeros( ( n, n ) )
    seam_y = rng.uniform( 0.2, 0.8 ) * n
    seam = 1.0 - smoothstep( 0.04 * p, 0.12 * p, np.abs( ( ( y - seam_y + n / 2 ) % n ) - n / 2 ) )
    seam_x = rng.uniform( 0, n )
    vseam = ( 1.0 - smoothstep( 0.04 * p, 0.12 * p, np.abs( ( ( x - seam_x + n / 2 ) % n ) - n / 2 ) ) ) \
        * ( ( ( y - seam_y ) % n ) < 0.45 * n )
    seam = np.maximum( seam, vseam )
    for k in range( int( STEEL_MODERN_TILE / 4 ) ):
        bx, by = ( k + 0.5 ) * 4 * p, seam_y - 1.2 * p
        stamp( bolts, bx, by, 0.35 * p, 0.35 * p, 0.1, profile="dome" )
        if rng.random() < 0.12:
            stamp( rusty, bx, by + 0.25 * p, 0.4 * p, 0.4 * p, rng.uniform( 0.4, 0.9 ), soft=0.3 * p )
    along = smoothstep( 0.8, 2.0, noise( rng, n, 2.2, 2, 30 ) )
    rusty = np.maximum( rusty, seam * along * 0.6 )
    bleed = run_down( rusty, 22 * p, 0.55, rng )
    sheen = noise( rng, n, 3.0, 1, 3 )                                  # broad 1-3 m shifts in the coat's sheen
    dust = np.clip( 0.5 + 0.5 * smoothstep( -1.5, 1.5, streaks( rng, n, 2.6, 1, 4, 200, 3.0 ) ) * ( y / n ), 0, 1 )
    colours = {}
    for name, base, rust_amount in ( ( "rw_steel_dark", ( 66, 70, 74 ), 0.35 ), ( "rw_steel_grey", ( 172, 174, 172 ), 0.6 ) ):
        c = lum_paint( base, 1.0 + 0.03 * mottle + 0.004 * peel + 0.03 * sheen )
        c = mix( c, lum_paint( ( 150, 144, 132 ), np.ones( ( n, n ) ) ), ( 0.08 if base[0] < 100 else 0.04 ) * dust )
        c = mix( c, lum_paint( ( 196, 196, 192 ), np.ones( ( n, n ) ) ), 0.07 * chalk if base[0] < 100 else 0.04 * chalk )
        c = mix( c, lum_paint( ( 188, 190, 188 ) if base[0] < 100 else ( 120, 120, 118 ), 1.0 + 0.05 * peel ), 0.7 * scratches )
        c = darken( c, ( 1.0 - 0.06 * scuff - 0.08 * grime - ( 0.1 if base[0] > 100 else 0.03 ) * hands )
                    * ( 1.0 + 0.06 * ghost ) * ( 1.0 - 0.2 * ring ) )
        c = mix( c, lum_paint( ( 110, 62, 36 ), 1.0 + 0.1 * mottle ), rust_amount * np.clip( bleed, 0, 1 ) )
        c = darken( c, 1.0 - 0.25 * seam )
        c = mix( c, lum_paint( ( 120, 122, 124 ), 1.0 + 0.0 * peel ), smoothstep( 0.02, 0.06, bolts ) * 0.5 )
        colours[name] = c
    rough = np.clip( 0.42 + 0.012 * peel + 0.1 * sheen + 0.08 * chalk + 0.1 * scuff + 0.18 * scratches + 0.1 * grime
                     - 0.06 * hands - 0.07 * ghost + 0.15 * ring + 0.25 * bleed + 0.06 * dust, 0.28, 0.72 )
    height = 0.0015 * peel - 0.008 * scratches + bolts + 0.004 * ghost - 0.03 * seam
    return colours, rough, height, 1024 / STEEL_MODERN_TILE


def lattice( rng, n ):
    """ A lattice girder's web, alpha-tested: one square panel per 1.0 of u, v from chord to chord. An X of riveted flat
    bars from corner to corner (9% of the panel wide, one over the other where they cross), the chords' flanges as a
    strip 6.5% deep along the top and bottom with a rivet every eighth, a gusset plate at each corner and rivets at the
    bars' ends and their crossing. Painted like rw_steel. The relief is drawn for a 36 in panel. """
    p = n / 36.0
    x, y = coords( n )
    s, t = x / n, y / n
    d1 = np.abs( ( ( s - t + 0.5 ) % 1.0 ) - 0.5 ) / math.sqrt( 2.0 ) * n
    d2 = np.abs( ( ( s + t - 1.0 + 0.5 ) % 1.0 ) - 0.5 ) / math.sqrt( 2.0 ) * n
    hw = 0.045 * n
    bar1 = np.clip( 0.5 + ( hw - d1 ), 0.0, 1.0 )
    bar2 = np.clip( 0.5 + ( hw - d2 ), 0.0, 1.0 )
    tt = np.minimum( t, 1.0 - t )
    chord = np.clip( 0.5 + ( 0.065 * n - tt * n ), 0.0, 1.0 )
    sw = np.abs( ( ( s + 0.5 ) % 1.0 ) - 0.5 )
    gusset = np.clip( 0.5 + ( ( 0.16 - 0.9 * np.maximum( tt - 0.065, 0.0 ) ) - sw ) * n, 0.0, 1.0 )
    rivets = np.zeros( ( n, n ) )
    r = 0.016 * n
    for k in range( 10 ):                              # 3.6 in pitch on a 36 in panel, as the plates' rivets
        for cy in ( 0.032 * n, ( 1 - 0.032 ) * n ):
            stamp( rivets, ( k + 0.5 ) * n / 10, cy, r, r, 0.3, profile="dome" )
    for tv in ( 0.1, 0.15 ):
        for cy, sign in ( ( tv, 1 ), ( 1 - tv, -1 ) ):
            for cx in ( tv, -tv ):
                stamp( rivets, ( cx % 1.0 ) * n, cy * n, r, r, 0.3, profile="dome" )
    stamp( rivets, 0.5 * n, 0.5 * n, r, r, 0.3, profile="dome" )
    for c in ( 0.47, 0.53 ):
        stamp( rivets, c * n, c * n, r * 0.9, r * 0.9, 0.3, profile="dome" )
        stamp( rivets, c * n, ( 1 - c ) * n, r * 0.9, r * 0.9, 0.3, profile="dome" )
    rivets *= np.maximum.reduce( [ bar1, bar2, chord, gusset ] ) > 0.5
    solid = np.maximum.reduce( [ bar1, bar2, chord, gusset ] )
    height = 0.375 * np.maximum( bar1, gusset ) + 0.375 * bar2 + 0.5 * chord + rivets
    height = T.blur( height, 0.6 )
    hot = T.blur( np.maximum( ( rivets > 0.02 ) * 1.0, 1.0 - smoothstep( 0.0, 3.0, np.minimum( np.abs( d1 - hw ), np.abs( d2 - hw ) ) ) ), 4.0 )
    wear = noise( rng, n, 2.4, 1, 4 )
    colour, rough = _old_paint( rng, n, p, STEEL_GREEN, height, hot, wear=wear, drips=True )
    colour, bleed, soot_w = _weather_iron( rng, n, p, colour, rivets, bleed_in=( 1.5, 3.0 ) )
    rough = np.clip( 0.45 + 0.25 * ( rough - 0.55 ) / 0.45 + 0.12 * bleed + 0.08 * soot_w, 0.42, 0.78 )
    ao = T.cavity_ao( height, ( ( 0.4 * p, 0.6 ), ), 1.0 )
    return { "rw_lattice": T.shaded( colour, ao, 0.45 ) }, rough, height, 1024 / 36.0, { "trans": solid }


def window_dark( rng, n ):
    """ Dark window glass seen from outside (the backdrop's and the yards' buildings): near black-blue, glossy, with a
    faint film of dirt and rain streaks. """
    film = smoothstep( -0.5, 2.0, noise( rng, n, 2.6, 1, 16 ) )
    st = smoothstep( 0.5, 2.5, streaks( rng, n, 1.6, 2, 60, 40, 1.0 ) )
    colour = lum_paint( ( 34, 42, 48 ), 1.0 + 0.1 * film + 0.15 * st )
    rough = np.clip( 0.06 + 0.16 * film + 0.12 * st, 0, 1 )
    height = 0.002 * noise( rng, n, 2.0, 2, 60 )
    return { "rw_window_dark": colour }, rough, height, 1024 / 96.0


GLASS_ROOF_TILE = 192.0


def glass_roof( rng, n ):
    """ The train shed's roof glazing, 2048 px over a 192 in tile: cast (rolled, wired) glass panes 24 x 64 in, eight
    across and three up the slope (v), each with its own film of soot and pigeon dirt (0.2-0.8 of the way to a brown
    grey) thickest at its lower end and streaked down the slope; one in twenty limewashed near opaque against the summer
    sun, one in twenty a newer, cleaner replacement. Its colour is the light it lets through, milky white-grey where
    clean (rolled glass diffuses), so the sky reads grey through it; the roughness (0.5-0.85) is how much it blurs what's
    behind. The wire mesh is left out: at this scale it would only alias. On shaders/glass.shader. """
    p = n / GLASS_ROOF_TILE
    x, y = coords( n )
    cols, rows = 8, 3
    pw, ph = n / cols, n / rows
    col = np.minimum( ( x // pw ).astype( int ), cols - 1 )
    row = np.minimum( ( y // ph ).astype( int ), rows - 1 )
    pane = row * cols + col
    count = cols * rows
    u, v = x - col * pw, y - row * ph
    edge = np.minimum( np.minimum( u, pw - u ), np.minimum( v, ph - v ) ) / p
    film = rng.uniform( 0.2, 0.8, count )
    kind = rng.random( count )
    lime = kind < 0.05
    clean = ( kind >= 0.05 ) & ( kind < 0.10 )
    if not lime.any():
        lime[rng.integers( count )] = True
    film[clean] = rng.uniform( 0.03, 0.12, clean.sum() )
    low = v / ph                                                   # 0 at the pane's top, 1 at its lower lap
    # Round 2: every pane's dark patch sat at the same spot, a stamp along a span. Each pane's film now centres on its
    # own place (a soft patch of its own size), and one in six has a run off to one side.
    cu, cv = rng.uniform( 0.2, 0.8, count ), rng.uniform( 0.45, 0.95, count )
    ru, rv = rng.uniform( 0.25, 0.6, count ), rng.uniform( 0.25, 0.55, count )
    blob = np.exp( -( ( u / pw - cu[pane] ) / ru[pane] ) ** 2 - ( ( v / ph - cv[pane] ) / rv[pane] ) ** 2 )
    lean = rng.uniform( 0.4, 1.0, count )                          # how much the film thickens towards the lap
    dirt = film[pane] * ( 0.6 + 0.3 * lean[pane] * low + 0.45 * blob ) + 0.12 * noise( rng, n, 2.4, 2, 24 ) \
        + 0.08 * noise( rng, n, 1.6, 8, 160 )
    side = rng.random( count ) < 1.0 / 6.0
    su = rng.choice( ( 0.12, 0.25, 0.75, 0.88 ), count )
    sw = rng.uniform( 0.05, 0.1, count )
    side_run = side[pane] * np.exp( -( ( u / pw - su[pane] ) / sw[pane] ) ** 2 ) * smoothstep( 0.1, 0.9, low )
    side_run = side_run * ( 0.7 + 0.3 * smoothstep( -1.0, 1.0, noise( rng, n, 1.6, 8, 120 ) ) )
    dirt = dirt + 0.35 * side_run
    dirt = dirt + 0.3 * smoothstep( -0.2, 2.2, streaks( rng, n, 1.6, 2, 80, 90, 2.0 ) ) * film[pane]
    # Soot gathered along the putty and the glazing bars' edges.
    dirt = dirt + 0.35 * ( 1.0 - smoothstep( 0.2, 1.5, edge ) )
    # Two scales within each pane, so a row of panes isn't a row of even stripes: a broad drift across the roof (the
    # wind's lee, the smoke's track) and patches a pane wide where rain did or didn't wash.
    drift = noise( rng, n, 3.0, 1, 3 )
    patches = noise( rng, n, 2.2, 6, 24 )
    dirt = dirt * ( 1.0 + 0.3 * drift + 0.22 * patches ) * ( 1.0 - 0.6 * clean[pane] )
    # Soot run down the slope from the laps and the purlins' drips: a few heavy brown tracks a tile.
    runs_src = np.zeros( ( n, n ) )
    for _ in range( int( rng.integers( 2, 4 ) ) ):
        x0 = rng.uniform( 0, n )
        y0 = rng.uniform( 0, n )
        w = rng.uniform( 2.5, 6.0 ) * p
        stamp( runs_src, x0, y0, w, 2.0 * p, 1.0, soft=1.5 * p )
    runs = np.clip( run_down( runs_src, rng.uniform( 40, 64 ) * p, 0.2, rng ) * 1.3, 0, 1 )
    runs = T.warp( rng, n, runs, 1.0 * p )
    dirt = np.clip( dirt + 0.35 * runs, 0.0, 1.0 )
    clear = lum_paint( ( 214, 216, 210 ), 1.0 + 0.025 * noise( rng, n, 1.0, 20, n / 4 ) )
    dirty = lum_paint( ( 150, 142, 126 ), 1.0 + 0.08 * noise( rng, n, 1.0, 20, n / 4 ) )
    colour = mix( clear, dirty, dirt )
    colour = mix( colour, lum_paint( ( 120, 110, 95 ), 1.0 + 0.08 * noise( rng, n, 1.0, 20, n / 4 ) ), 0.5 * runs )
    wash = lime[pane] * smoothstep( -1.2, 0.6, noise( rng, n, 1.8, 6, 120 ) + 1.2 )
    colour = mix( colour, lum_paint( ( 205, 205, 195 ), 1.0 + 0.04 * noise( rng, n, 1.2, 30, n / 3 ) ), 0.9 * wash )
    putty = 1.0 - smoothstep( 0.1, 0.25, edge )
    colour = mix( colour, np.array( ( 96, 92, 84 ), float ), 0.3 * putty )
    # Rolled glass diffuses even when clean; dirt makes it a milky film (glass.shader: roughness x absorption is the
    # share lit as a film, the rest the view through).
    rough = np.clip( 0.5 + 0.35 * dirt, 0.5, 0.85 )
    rough = rough + ( 0.9 - rough ) * wash
    height = 0.012 * noise( rng, n, 2.6, 4, 80 ) + 0.004 * noise( rng, n, 1.0, 40, n / 3 ) - 0.03 * putty
    return { "rw_glass_roof": colour }, rough, height, 1024 / GLASS_ROOF_TILE


def train( rng, n ):
    """ Trains' bodies: glossy enamel over the body shell, a faint panel seam down the tile's middle, and dirt in soft
    streaks running down from the roof and the windows. Six plain colours (rw_train_red, _blue, _white, _grey, _dark and
    _yellow): the town's own fleet, no operator's livery. """
    p = n / 96.0
    x, y = coords( n )
    seam = 1.0 - smoothstep( 0.04 * p, 0.1 * p, np.abs( x - n / 2 ) )
    peel = noise( rng, n, 1.0, n / 10 )
    mottle = noise( rng, n, 2.6, 2, 40 )
    st = smoothstep( 0.4, 2.4, streaks( rng, n, 1.6, 2, 120, 100, 1.5 ) )
    grime = 0.08 + 0.3 * st + 0.08 * smoothstep( -1, 2, mottle )
    colours = {}
    for name, base in ( ( "rw_train_red", ( 156, 28, 36 ) ), ( "rw_train_blue", ( 22, 56, 118 ) ),
                        ( "rw_train_white", ( 220, 222, 220 ) ), ( "rw_train_grey", ( 118, 122, 124 ) ),
                        ( "rw_train_dark", ( 36, 38, 40 ) ), ( "rw_train_yellow", ( 228, 180, 30 ) ) ):
        c = lum_paint( base, 1.0 + 0.015 * peel + 0.02 * mottle )
        c = mix( c, lum_paint( ( 92, 84, 74 ), 1.0 + 0.1 * mottle ), 0.6 * grime )
        c = darken( c, 1.0 - 0.45 * seam )
        colours[name] = c
    rough = np.clip( 0.24 + 0.3 * grime + 0.02 * peel + 0.2 * seam, 0, 1 )
    height = 0.002 * peel - 0.04 * seam
    return colours, rough, height, 1024 / 96.0


def bogie( rng, n ):
    """ Bogies, underframes, buffers and couplers: black-painted steel under grime and brake dust, rusty where it's
    chipped, oily round the axle boxes. """
    p = n / 64.0
    fine = noise( rng, n, 0.8, n / 6 )
    mottle = noise( rng, n, 2.4, 2, 60 )
    dust = np.clip( 0.45 + 0.12 * noise( rng, n, 2.6, 1, 16 ) + 0.25 * smoothstep( -0.5, 2.5, streaks( rng, n, 1.6, 2, 60, 50, 1.5 ) ),
                    0.0, 1.0 )
    rust = blotches( rng, n, 1.6, 10, 200, 0.06, 0.4 )
    oil = 0.6 * blotches( rng, n, 2.4, 2, 40, 0.06, 1.0 )
    colour = lum_paint( ( 46, 40, 36 ), 1.0 + 0.08 * fine + 0.06 * mottle )
    colour = mix( colour, lum_paint( ( 104, 76, 56 ), 1.0 + 0.1 * fine ), 0.55 * dust )
    colour = mix( colour, lum_paint( ( 110, 64, 40 ), 1.0 + 0.12 * fine ), 0.7 * rust )
    colour = darken( colour, 1.0 - 0.5 * oil )
    rough = np.clip( 0.72 + 0.05 * fine + 0.1 * dust - 0.4 * oil, 0, 1 )
    height = 0.01 * fine + 0.02 * rust
    return { "rw_bogie": colour }, rough, height, 1024 / 64.0


def rubber( rng, n ):
    """ Rubber: the gangways' bellows, door seals, cables and hoses. Near black with a dusty bloom. """
    fine = noise( rng, n, 0.6, n / 6 )
    dust = smoothstep( -0.5, 2.0, noise( rng, n, 2.6, 1, 12 ) )
    colour = lum_paint( ( 30, 30, 30 ), 1.0 + 0.05 * fine + 0.35 * dust )
    rough = np.clip( 0.85 + 0.04 * fine + 0.06 * dust, 0, 1 )
    return { "rw_rubber": colour }, rough, 0.004 * fine, 1024 / 32.0


def wagon( rng, n ):
    """ Freight wagons' steel bodies: rw_wagon_rust in a faded oxide red-brown, rw_wagon_grey in grey, both with welded
    seams every 48 in, chalky fading, patches of fresher overpaint, chips and rust running down. """
    p = n / 96.0
    x, y = coords( n )
    seam_d = np.minimum( x % ( n / 2 ), n / 2 - x % ( n / 2 ) ) / p
    bead = smoothstep( 0.25, 0.1, seam_d )
    fine = noise( rng, n, 0.8, n / 6 )
    mottle = noise( rng, n, 2.4, 2, 60 )
    fade = smoothstep( -1.6, 2.2, 0.4 * noise( rng, n, 2.8, 1, 8 ) + 0.9 * streaks( rng, n, 1.6, 2, 60, 90, 1.5 ) )
    over = np.zeros( ( n, n ) )
    for _ in range( 3 ):
        inside, edge = _rect_wrap( x, y, *rng.uniform( 0, n, 2 ), rng.uniform( 8, 30 ) * p, rng.uniform( 6, 24 ) * p, n )
        over = np.maximum( over, np.clip( 0.5 + edge / 1.5, 0.0, 1.0 ) )
    hot = T.blur( bead, 0.4 * p )
    chipn = noise( rng, n, 1.4, 12, n / 3 )
    chip = smoothstep( 2.0, 2.3, chipn + 0.8 * hot )
    bleed = run_down( chip, 20 * p, 0.5, rng )
    colours = {}
    for name, base, faded in ( ( "rw_wagon_rust", ( 112, 54, 40 ), ( 140, 98, 84 ) ),
                               ( "rw_wagon_grey", ( 120, 124, 124 ), ( 150, 152, 150 ) ) ):
        c = mix( lum_paint( base, 1.0 + 0.04 * mottle + 0.03 * fine ), lum_paint( faded, 1.0 + 0.04 * fine ), 0.6 * fade )
        c = mix( c, lum_paint( base, 0.9 + 0.02 * fine ), over )
        c = mix( c, lum_paint( ( 104, 58, 38 ), 1.0 + 0.12 * fine ), chip )
        c = mix( c, lum_paint( ( 122, 72, 44 ), 1.0 + 0.1 * fine ), 0.4 * bleed * ( 1.0 - chip ) )
        colours[name] = c
    rough = np.clip( 0.62 + 0.15 * fade - 0.15 * over + 0.2 * chip + 0.04 * fine, 0, 1 )
    height = 0.12 * bead + 0.004 * fine - 0.01 * chip + 0.004 * over
    return colours, rough, height, 1024 / 96.0


CONTAINER_COLOURS = ( ( "blue", ( 34, 74, 130 ) ), ( "red", ( 148, 44, 36 ) ), ( "green", ( 42, 92, 62 ) ),
                      ( "orange", ( 206, 110, 42 ) ), ( "grey", ( 140, 144, 146 ) ) )
CONTAINER_HEIGHT = 102.0                    # inches up a tile: a standard box's height, so each wall gets one band set
CONTAINER_WIDTH = 48.0                      # inches across a tile (the models' UVs)


def container( rng, n ):
    """ A working 20 or 40 ft box's painted steel (railhead_props builds the corrugation as geometry, 278 mm pitch, so
    no ribs here). The picture is 48 in across by 102 in up (a box's height): the vmat scales v by 48/102
    (TEXCOORD_SCALE) and the wall paints are ANCHORED, so its bottom rows are z 0, the box's bottom rail, as they stand
    in the yards (one stacked on another lines up too). A grime band over the bottom 6 in rail and splashed up the
    lowest foot, rust running down from the top rail's weld, the upper half sun-faded and chalky, broad grime runs,
    bare-metal scrapes with rust halos, dents. Roughness: fresh paint 0.45, faded 0.75, rust 0.8. rw_container_<colour>
    is the walls; rw_container_<colour>_roof the same paint without the height bands, for the roofs (where the bands
    would lie in stripes across). Five plain colours, with no owner's marks. """
    pu = n / CONTAINER_WIDTH                                            # px an inch across
    pv = n / CONTAINER_HEIGHT                                           # px an inch up
    x, y = coords( n )
    z = ( n - y ) / pv                                                  # inches up from the box's foot
    dents = noise( rng, n, 3.0, 1, 8 )
    fine = noise( rng, n, 0.8, n / 6 )
    height = 0.12 * dents + 0.004 * noise( rng, n, 0.6, n / 6 )
    canvas = Canvas( n, 2, int( 32 * pu ) )
    cores = Canvas( n, 2, int( 32 * pu ) )
    for _ in range( 12 ):
        x_ = rng.uniform( 0, n )
        z_ = rng.uniform( 8, 70 ) if rng.random() < 0.8 else rng.uniform( 70, 92 )
        y_ = n - z_ * pv
        length = rng.uniform( 6, 30 ) * pu
        slope = rng.normal( 0, 0.06 )
        pts = [ ( x_ + length * k / 8, y_ + length * k / 8 * slope + rng.normal( 0, 0.08 * pv ) ) for k in range( 9 ) ]
        w = rng.uniform( 0.08, 0.3 ) * pv
        canvas.line( pts, w * 2.2, rng.uniform( 0.4, 0.8 ) )
        cores.line( pts, w * 0.8, rng.uniform( 0.6, 1.0 ) )
    halo = np.clip( canvas.result(), 0, 1 )
    core = np.clip( cores.result(), 0, 1 )
    scrape = np.maximum( halo, core )
    height = height - 0.03 * scrape
    # Rust: along the top rail's weld (z 92-100), at the scrapes' halos and in a few pitted patches; it runs down.
    weld = ( smoothstep( 92.0, 95.0, z ) * ( 1.0 - smoothstep( 99.5, 101.5, z ) )
             * smoothstep( 0.4, 1.6, noise( rng, n, 1.6, 6, 120 ) ) )
    pits = blotches( rng, n, 1.6, 12, 240, 0.025, 0.4 ) * blotches( rng, n, 2.6, 1, 6, 0.25, 0.6 ) * ( z > 10 )
    rust = np.clip( np.maximum( np.maximum( 0.75 * weld, 0.6 * halo * ( 1.0 - core ) ), pits ), 0, 1 )
    bleed = run_down( rust * ( z > 12 ), 40 * pv, 0.45, rng )
    bleed = T.blur( bleed, 0.8 * pu ) * ( z > 4 )
    # Sun fade and chalk on the upper half, grime washed down and splashed up from the yard.
    upper = smoothstep( 30.0, 90.0, z + 8.0 * noise( rng, n, 2.2, 2, 12 ) )
    fade = np.clip( upper * ( 0.6 + 0.4 * smoothstep( -1.6, 1.6, noise( rng, n, 2.8, 1, 6 ) ) ), 0, 1 )
    chalky = noise( rng, n, 0.6, n / 8 )
    chalk = smoothstep( 0.4, 2.0, chalky + 0.8 * upper ) * ( 0.3 + 0.7 * fade )
    runs = streaks( rng, n, 2.2, 2, 24, 160, 4.0 )
    grime = smoothstep( 0.6, 2.4, runs ) * ( 0.5 + 0.5 * ( 1.0 - upper ) )
    foot = 1.0 - smoothstep( 6.0, 16.0, z + 3.0 * noise( rng, n, 1.8, 6, 80 ) )
    rail = 1.0 - smoothstep( 5.4, 6.2, z )                             # the bottom rail, its 6 in band
    roof_fade = 0.6 + 0.4 * smoothstep( -1.6, 1.6, noise( rng, n, 2.8, 1, 6 ) )
    roof_chalk = smoothstep( 0.4, 2.0, chalky + 0.8 )
    colours = {}
    roofs = {}
    for name, base in CONTAINER_COLOURS:
        faded = srgb( lin( base ) * 0.62 + lin( ( 182, 180, 174 ) ) * 0.38 )
        c = mix( lum_paint( base, 1.0 + 0.03 * fine ), lum_paint( faded, 1.0 + 0.03 * fine ), 0.05 + 0.4 * fade )
        c = mix( c, lum_paint( ( 140, 136, 128 ), 1.0 + 0.1 * fine ), 0.5 * halo * ( 1.0 - core ) )
        c = mix( c, lum_paint( ( 160, 156, 150 ), 1.0 + 0.1 * fine ), 0.75 * core )
        c = mix( c, lum_paint( ( 112, 62, 38 ), 1.0 + 0.12 * fine ), 0.7 * rust * ( 1.0 - core ) )
        c = mix( c, lum_paint( ( 118, 74, 46 ), 1.0 + 0.1 * fine ), 0.35 * bleed * ( 1.0 - rust ) )
        c = darken( c, 1.0 - 0.3 * grime )
        c = mix( c, lum_paint( ( 204, 200, 192 ), 1.0 + 0.0 * fine ), 0.22 * chalk )
        c = darken( c, ( 1.0 - 0.4 * rail ) * ( 1.0 - 0.25 * foot ) )
        c = tinted( c, ( 90, 76, 60 ), 0.3 * foot + 0.2 * rail )
        colours[f"rw_container_{name}"] = c
        # The roof: no height bands, the upper half's weather all over, pitted rust and grime runs.
        r = mix( lum_paint( base, 1.0 + 0.03 * fine ), lum_paint( faded, 1.0 + 0.03 * fine ), 0.1 + 0.4 * roof_fade )
        r = mix( r, lum_paint( ( 112, 62, 38 ), 1.0 + 0.12 * fine ), 0.7 * pits )
        r = darken( r, 1.0 - 0.25 * grime )
        r = mix( r, lum_paint( ( 204, 200, 192 ), 1.0 + 0.0 * fine ), 0.2 * roof_chalk )
        roofs[f"rw_container_{name}_roof"] = r
    colours.update( roofs )
    rough = 0.45 + 0.3 * fade + 0.04 * fine
    rough = rough + ( 0.8 - rough ) * np.clip( rust + 0.6 * bleed, 0, 1 )
    rough = rough + ( 0.35 - rough ) * 0.6 * core + 0.06 * chalk + 0.1 * rail
    return colours, np.clip( rough, 0.3, 0.95 ), height, 1024 / CONTAINER_WIDTH


def plain( rng, n ):
    """ Plain satin paints for small things (railings, bollards, signal arms, buffer stops, fire points): rw_black,
    rw_white_paint, rw_yellow_paint and rw_red_paint, faintly mottled, with a few scuffs. """
    fine = noise( rng, n, 0.8, n / 6 )
    mottle = noise( rng, n, 2.4, 2, 40 )
    scuff = blotches( rng, n, 2.2, 3, 60, 0.06, 0.8 )
    colours = {}
    for name, base in ( ( "rw_black", ( 24, 24, 24 ) ), ( "rw_white_paint", ( 226, 226, 222 ) ),
                        ( "rw_yellow_paint", ( 230, 170, 24 ) ), ( "rw_red_paint", ( 186, 32, 28 ) ) ):
        c = lum_paint( base, 1.0 + 0.02 * fine + 0.03 * mottle )
        c = mix( c, lum_paint( ( 110, 104, 96 ), 1.0 + 0.05 * fine ), 0.25 * scuff )
        colours[name] = c
    rough = np.clip( 0.45 + 0.03 * fine + 0.2 * scuff, 0, 1 )
    return colours, rough, 0.003 * fine, 1024 / 64.0


def lamps( rng, n ):
    """ Self-lit: lamp glass and LED panels (rw_lamp_warm, rw_lamp_cool) and signal lenses (rw_signal_red, _green and
    _yellow). Their colour is the light they give; ILLUM sets how bright. """
    fine = noise( rng, n, 1.0, n / 8 )
    colours = { name: lum_paint( base, 1.0 + 0.015 * fine ) for name, base in (
        ( "rw_lamp_warm", ( 255, 222, 170 ) ), ( "rw_lamp_cool", ( 226, 236, 255 ) ), ( "rw_signal_red", ( 255, 38, 22 ) ),
        ( "rw_signal_green", ( 40, 230, 170 ) ), ( "rw_signal_yellow", ( 255, 176, 24 ) ) ) }
    return colours, 0.12 + 0.01 * fine, 0.0, 1024 / 32.0


def wood( rng, n ):
    """ Varnished hardwood (GRAIN: along v): the benches' slats, the waiting room's doors and panelling. Oak-brown, its
    grain and figure running along the piece, open pores, the varnish worn dull where hands and seats rub it. """
    p = n / 32.0
    x, y = coords( n )
    grain = streaks( rng, n, 1.4, 6, n / 2, 60, 0.8 )
    pores = streaks( rng, n, 0.2, n / 8, n / 2, 6, 0.3 )
    warp = noise( rng, n, 2.6, 1, 6 ) * 0.9 * p
    rings = np.sin( 2 * math.pi * ( x + warp ) / ( 0.35 * p ) + 0.3 * grain )
    figure = smoothstep( 0.4, 1.0, rings ) * smoothstep( -0.5, 1.5, noise( rng, n, 2.0, 2, 30 ) )
    worn = blotches( rng, n, 2.6, 1, 16, 0.25, 1.5 )
    lum = 1.0 + 0.1 * grain - 0.18 * figure - 0.12 * smoothstep( 1.5, 2.5, pores )
    colour = lum_paint( ( 148, 96, 56 ), lum )
    colour = mix( colour, lum_paint( ( 162, 120, 84 ), lum ), 0.4 * worn )
    rough = np.clip( 0.35 + 0.25 * worn + 0.03 * grain, 0, 1 )
    height = 0.006 * grain - 0.01 * smoothstep( 1.5, 2.5, pores ) - 0.004 * figure
    return { "rw_wood": colour }, rough, height, 1024 / 32.0


FACADES = {                                       # wall render, trim (surrounds, string courses, sills)
    "rw_facade_cream": ( ( 224, 208, 172 ), ( 240, 234, 216 ) ),
    "rw_facade_ochre": ( ( 206, 160, 88 ), ( 234, 222, 192 ) ),
    "rw_facade_grey": ( ( 166, 164, 156 ), ( 214, 212, 204 ) ),
    "rw_facade_rose": ( ( 202, 152, 140 ), ( 238, 226, 212 ) ),
}
STOREY = 138.0


def _box( ax, lz, p, hw, z0, z1 ):
    """ 1 inside |dx| < hw and z0 <= lz < z1 (inches), anti-aliased over a px. """
    return ( np.clip( 0.5 + ( hw - ax ) * p, 0.0, 1.0 ) * np.clip( 0.5 + ( lz - z0 ) * p, 0.0, 1.0 )
             * np.clip( 0.5 + ( z1 - lz ) * p, 0.0, 1.0 ) )


def facade( rng, n ):
    """ A Gründerzeit tenement's rendered front for the city round the station, seen from the platforms: two storeys of
    11.5 ft (138 in) and two window bays of 138 in to a 276 in tile, anchored at z 0 so storeys line up with the floor.
    Each storey stands on a string course 9 in deep; each window is 46 x 80 in (1.17 x 2.03 m) in a plastered surround
    6 in wide with ears at its head, over a projecting sill on two consoles and a framed parapet panel. The lower
    storey's windows have straight cornices, the upper ones' triangular pediments, as such fronts alternate them.
    White-painted casement windows with a transom light, 3.6 in back from the wall face, and the glass behind them
    shows what each flat has: net curtains, a roller blind half down, drapes, or a dark room, under a faint reflection
    of the sky. The render is mottled and patched, and dirt runs down from the sills and cornices. Four colourways:
    cream, ochre, grey and rose, each with a paler trim. """
    p = n / 276.0
    x, y = coords( n )
    X, Z = x / p, ( n - y ) / p
    k = np.minimum( ( Z // STOREY ).astype( int ), 1 )
    lz = Z - STOREY * k
    b = np.minimum( ( X // STOREY ).astype( int ), 1 )
    dx = X - ( STOREY / 2 + STOREY * b )
    ax = np.abs( dx )
    box = functools.partial( _box, ax, lz, p )
    upper = k == 1

    # Relief, in inches out of the wall face.
    zl = 36.5                                                     # the glass's bottom and top (local)
    zt = 111.5
    string = np.clip( 0.5 + lz * p, 0, 1 ) * np.clip( 0.5 + ( 9.0 - lz ) * p, 0, 1 )
    string_h = 2.5 * smoothstep( 0.0, 1.2, lz ) * smoothstep( 9.0, 7.4, lz ) - 0.5 * ( np.abs( lz - 4.5 ) < 0.45 )
    panel = box( 26, 12, 30 )
    field = box( 22.5, 15.5, 26.5 )
    sill = box( 33, 30, 34 )
    sill_h = 2.4 + 0.8 * smoothstep( 30.0, 31.5, lz )
    consoles = ( box( 32, 22, 30 ) - box( 27, 22, 30 ) ).clip( 0, 1 )
    console_h = 1.0 + 1.6 * ( lz - 22.0 ) / 8.0
    head_top = np.where( upper, 120.0, 124.0 )
    surround = np.clip( box( 29, 34, 124 ) * np.where( upper, box( 29, 34, 120 ), 1.0 ), 0, 1 )
    ears = box( 32, 108, 120 )
    cornice = box( 34, 124, 128 ) * ( 1 - upper )
    cornice_h = 1.6 + 1.6 * ( lz - 124.0 ) / 4.0
    base = box( 35, 120, 124 ) * upper
    slope_d = ( 124.0 + 11.0 * ( 1.0 - ax / 36.0 ) ) - lz           # inches under the pediment's slope
    pediment = ( np.clip( 0.5 + slope_d * p * 0.95, 0, 1 ) * np.clip( 0.5 + ( lz - 124.0 ) * p, 0, 1 )
                 * np.clip( 0.5 + ( 36.0 - ax ) * p, 0, 1 ) * upper )
    pediment_h = np.where( slope_d < 2.2, 2.6, 0.9 )
    opening = box( 23, 34, 114 )
    glass = box( 20.5, zl, zt ) * ( 1.0 - box( 1.25, zl, zt ) ) * ( 1.0 - box( 21, 88, 91 ) )
    glass = np.clip( glass * ( 1.0 - box( 21, 61.5, 63.0 ) ), 0, 1 )   # a glazing bar across each casement
    frame = np.clip( opening - glass, 0, 1 )

    trim = np.maximum.reduce( [ string, panel * ( 1.0 - field ), sill, consoles, surround, ears, cornice, base, pediment ] )
    raised = np.maximum.reduce( [ string * string_h, panel * 0.8 + field * -0.6, sill * sill_h, consoles * console_h,
                                  surround * 1.2, ears * 1.2, cornice * cornice_h, base * 3.0, pediment * pediment_h ] )
    fine = noise( rng, n, 1.0, n / 6 )
    plaster = noise( rng, n, 1.8, 16, n / 4 )
    height = raised * ( 1.0 - opening ) + opening * ( -3.6 * frame - 4.6 * glass ) + 0.03 * plaster + 0.01 * fine
    height = T.blur( height, 0.5 )

    # Weathering: mottled render, a few patched repairs, dirt running down from what sticks out.
    mottle = noise( rng, n, 2.6, 2, 60 )
    patch = T.warp( rng, n, blotches( rng, n, 2.2, 3, 40, 0.07, 0.3 ), 3 * p )
    drip_src = np.zeros( ( n, n ) )
    for zb, hw in ( ( 30.0, 33 ), ( 22.0, 32 ), ( 124.0, 34 ), ( 120.0, 35 ), ( 0.0, 999 ) ):
        under = np.clip( 1.0 - np.abs( lz - zb ) * p / 1.5, 0, 1 ) * np.clip( 0.5 + ( hw - ax ) * p, 0, 1 )
        drip_src = np.maximum( drip_src, under )
    drip_src *= smoothstep( 0.2, 1.6, noise( rng, n, 1.2, 30, 400 ) )
    drips = np.clip( run_down( drip_src, 30 * p, 0.5, rng ) * 1.3, 0, 1 )
    drips = T.blur( drips, 0.8 * p ) * ( 1.0 - opening )
    grime = smoothstep( -0.5, 2.5, streaks( rng, n, 1.6, 2, 60, 90, 2.0 ) )
    ao = T.cavity_ao( height, ( ( 1.5 * p, 1.0 ), ( 5.0 * p, 0.8 ) ), 1.0 )
    lit = cast_shadow( height, 1.0 / p, 7 * p, dx=0.0, soft=0.4 )

    # The glass: what's behind it, under a reflection of the sky that's brighter towards the top.
    gz = np.clip( ( lz - zl ) / ( zt - zl ), 0, 1 )
    interior = lum_paint( ( 30, 32, 34 ), 1.0 + 0.15 * noise( rng, n, 2.0, 2, 30 ) )
    kinds = rng.permutation( [ "lace", "blind", "drapes", "dark" ] )
    win = 2 * k + b
    folds = 0.5 + 0.5 * np.sin( 2 * math.pi * ( dx / 2.4 + 0.3 * noise( rng, n, 2.0, 4, 40 ) ) )
    lace_c = lum_paint( ( 214, 212, 204 ), 0.8 + 0.3 * folds + 0.05 * fine )
    behind = interior.copy()
    for w, kind in enumerate( kinds ):
        here = ( win == w )[..., None]
        if kind == "lace":
            c = mix( interior, lace_c, 0.82 )
        elif kind == "blind":
            down = rng.uniform( 0.35, 0.6 )
            blind = smoothstep( 1.0 - down - 0.004, 1.0 - down + 0.004, gz )
            c = mix( mix( interior, lace_c, 0.5 * ( gz < 0.7 ) ), lum_paint( ( 200, 184, 152 ), 1.0 + 0.04 * fine ), blind )
        elif kind == "drapes":
            fabric = lum_paint( ( 118, 46, 40 ), 0.75 + 0.4 * folds )
            side = smoothstep( 11.0, 12.0, ax )
            c = mix( mix( interior, lace_c, 0.6 ), fabric, side )
        else:
            c = interior
        behind = np.where( here, c, behind )
    sky = lum_paint( ( 150, 166, 184 ), 0.7 + 0.5 * gz )
    glass_c = mix( behind, sky, 0.1 + 0.2 * gz )
    frame_c = lum_paint( ( 234, 232, 226 ), 1.0 + 0.02 * fine )

    # Two patched repairs a tile: newer render, a shade off the old, with a crisp edge that catches the light.
    repair = np.zeros( ( n, n ) )
    repair_edge = np.zeros( ( n, n ) )
    for _ in range( 2 ):
        x0, y0 = rng.uniform( 0, n, 2 )
        w, h = rng.uniform( 20, 60 ) * p, rng.uniform( 14, 40 ) * p
        inside, edge = _rect_wrap( x, y, x0, y0, w, h, n )
        wob = T.warp( rng, n, inside * 1.0, 2.0 * p )
        repair = np.maximum( repair, smoothstep( 0.4, 0.6, wob ) )
        repair_edge = np.maximum( repair_edge, 1.0 - smoothstep( 0.0, 0.18, np.abs( wob - 0.5 ) ) )
    repair *= 1.0 - opening
    repair_edge *= 1.0 - opening
    height = height + 0.06 * repair + 0.03 * repair_edge
    # Splash and grime at the foot of each storey's wall (heaviest over the string course), and soot in the
    # render's texture over the whole front.
    foot = ( 1.0 - smoothstep( 9.0, 40.0, lz + 6.0 * noise( rng, n, 1.8, 8, 120 ) ) ) * ( 1.0 - trim ) * ( 1.0 - opening )
    broad = noise( rng, n, 4.0, 1, 1.5 )                          # one gentle shift a tile, so a front isn't one flat colour
    colours = {}
    for name, ( wall_rgb, trim_rgb ) in FACADES.items():
        lum = ( 1.0 + 0.035 * mottle + 0.02 * fine + 0.02 * plaster ) * ( 1.0 + 0.04 * patch ) * ( 1.0 + 0.12 * broad )
        c = mix( lum_paint( wall_rgb, lum ), lum_paint( trim_rgb, lum ), trim )
        c = mix( c, lum_paint( tuple( min( 255, k * 1.06 ) for k in wall_rgb ), 1.0 + 0.02 * fine ), 0.85 * repair * ( 1.0 - trim ) )
        c = darken( c, ( 1.0 - 0.14 * repair_edge ) * ( 1.0 - 0.22 * foot ) )
        c = mix( c, lum_paint( ( 96, 88, 76 ), 1.0 + 0.1 * fine ), 0.8 * drips + 0.15 * grime )
        c = mix( c, frame_c, frame )
        c = mix( c, glass_c, glass )
        c = darken( c, 1.0 - 0.3 * ( 1.0 - lit ) * ( 1.0 - glass ) )
        colours[name] = T.shaded( c, ao, 0.5 )
    rough = 0.9 - 0.04 * trim + 0.04 * drips
    rough = rough + ( 0.45 - rough ) * frame
    rough = np.clip( rough + ( 0.06 - rough ) * glass + 0.02 * fine, 0, 1 )
    return colours, rough, height, 1024 / 276.0


def clock( rng, n ):
    """ The platform clock's face, a decal across its polygon (0..1 both ways, the face's circle touching the edges):
    a white dial under glass with black bars, 12 thick ones for the hours and 48 thin ones between, and plain black bar
    hands, as German railway clocks have, at 14:03. There's no second hand. Round the dial a black bezel; the corners
    are the dark grey housing. """
    x, y = coords( n )
    c = n / 2.0
    dx, dy = ( x - c ) / c, ( y - c ) / c
    r = np.hypot( dx, dy )
    ang = np.arctan2( dx, -dy )                                  # clockwise from 12
    aa = 1.5 / c
    face = np.clip( ( 0.9 - r ) / aa + 0.5, 0, 1 )
    bezel = np.clip( ( 0.985 - r ) / aa + 0.5, 0, 1 )

    def bar( angle, r0, r1, half ):
        """ A bar from radius r0 to r1 along angle, half wide (in face radii), sharp-edged. """
        ux, uy = math.sin( angle ), -math.cos( angle )
        along = dx * ux + dy * uy
        across = np.abs( dx * uy - dy * ux )
        ends = np.minimum( along - r0, r1 - along )
        return np.clip( ( half - across ) / aa + 0.5, 0, 1 ) * np.clip( ends / aa + 0.5, 0, 1 )

    marks = np.zeros( ( n, n ) )
    for m in range( 60 ):
        a = m * math.pi / 30
        if m % 5 == 0:
            marks = np.maximum( marks, bar( a, 0.62, 0.84, 0.032 ) )
        else:
            marks = np.maximum( marks, bar( a, 0.77, 0.84, 0.011 ) )
    hour = bar( math.radians( ( 2 + 3 / 60 ) * 30 ), -0.12, 0.56, 0.042 )
    minute = bar( math.radians( 3 * 6 ), -0.16, 0.82, 0.032 )
    hub = np.clip( ( 0.05 - r ) / aa + 0.5, 0, 1 )
    hands = np.maximum.reduce( [ hour, minute, hub ] )
    shadow = np.maximum( bar( math.radians( 61.5 ), -0.12, 0.56, 0.05 ), bar( math.radians( 18 ), -0.16, 0.82, 0.04 ) )
    shadow = T.blur( np.roll( np.roll( shadow, int( 0.012 * c ), 0 ), int( 0.006 * c ), 1 ), 0.01 * c )
    fine = noise( rng, n, 1.0, n / 8 )
    dial = lum_paint( ( 238, 238, 234 ), ( 1.0 + 0.008 * fine ) * ( 1.0 - 0.1 * r ** 4 ) * ( 1.0 - 0.18 * shadow ) )
    colour = mix( dial, np.array( ( 18, 18, 18 ), float ), np.maximum( marks, hands ) )
    rim = lum_paint( ( 34, 34, 36 ), 1.0 + 0.25 * smoothstep( 0.93, 0.96, r ) * smoothstep( 0.99, 0.96, r )
                     * ( 0.5 + 0.5 * np.cos( ang + 0.8 ) ) )
    housing = lum_paint( ( 58, 60, 62 ), 1.0 + 0.04 * fine )
    colour = mix( housing, mix( rim, colour, face ), bezel )
    glare = 0.08 * smoothstep( 0.5, 0.0, np.hypot( dx + 0.35, dy + 0.45 ) ) * face
    colour = srgb( lin( colour ) + glare[..., None] )
    rough = np.where( bezel > 0.5, 0.12, 0.5 )
    height = 0.6 * bezel - 0.4 * face + 0.06 * hands * face
    return { "rw_clock": colour }, rough, height, 1024 / 16.0


# ---------------------------------------------------------------------------------------------------------------------
# Atlases. Each is drawn at SS times its size in PIL layers (colour, roughness, height, alpha, self-illumination), with
# every piece in its own rectangle of ATLASES; the gutters between them carry on the piece's background, so mips don't
# bleed. Coordinates are the atlas's px, top left first.

class Sheet:
    def __init__( self, w, h, rects, background, rough=0.5, height=0.0, alpha=1.0, light=0.0 ):
        self.w, self.h, self.rects = w, h, rects
        size = ( w * SS, h * SS )
        self.colour = Image.new( "RGB", size, tuple( int( v ) for v in background ) )
        self.layers = { "rough": Image.new( "L", size, int( rough * 255 ) ), "height": Image.new( "L", size, int( height * 255 ) ),
                        "alpha": Image.new( "L", size, int( alpha * 255 ) ), "light": Image.new( "L", size, int( light * 255 ) ) }
        self.draws = { "colour": ImageDraw.Draw( self.colour ) }
        self.draws.update( { k: ImageDraw.Draw( v ) for k, v in self.layers.items() } )

    def box( self, name ):
        return self.rects[name]

    def _each( self, fill, layers ):
        if fill is not None:
            yield self.draws["colour"], tuple( int( round( v ) ) for v in fill )
        for k, v in ( layers or {} ).items():
            yield self.draws[k], int( round( np.clip( v, 0, 1 ) * 255 ) )

    @staticmethod
    def _s( points ):
        return [ ( px * SS, py * SS ) for px, py in points ]

    def rectangle( self, xy, fill=None, layers=None, radius=0.0, outline=None, width=0.0 ):
        x0, y0, x1, y1 = ( v * SS for v in xy )
        for d, f in self._each( fill, layers ):
            d.rounded_rectangle( ( x0, y0, x1 - 1, y1 - 1 ), radius=radius * SS, fill=f )
        if outline is not None:
            for d, f in self._each( outline, layers ):
                d.rounded_rectangle( ( x0, y0, x1 - 1, y1 - 1 ), radius=radius * SS, outline=f, width=max( 1, int( round( width * SS ) ) ) )

    def polygon( self, points, fill, layers=None ):
        for d, f in self._each( fill, layers ):
            d.polygon( self._s( points ), fill=f )

    def ellipse( self, xy, fill=None, layers=None, outline=None, width=0.0 ):
        box = tuple( v * SS for v in xy )
        if fill is not None or ( layers and outline is None ):
            for d, f in self._each( fill, layers ):
                d.ellipse( box, fill=f )
        if outline is not None:
            for d, f in self._each( outline, layers ):
                d.ellipse( box, outline=f, width=max( 1, int( round( width * SS ) ) ) )

    def line( self, points, fill, width, layers=None, joint="curve" ):
        for d, f in self._each( fill, layers ):
            d.line( self._s( points ), fill=f, width=max( 1, int( round( width * SS ) ) ), joint=joint )

    def dot( self, x, y, r, fill, layers=None ):
        self.ellipse( ( x - r, y - r, x + r, y + r ), fill, layers )

    def text( self, xy, s, face, cap, fill, layers=None, anchor="ls", tracking=0.0, width=None ):
        """ s with capitals cap px high (shrunk to width if given); tracking is a share of cap. Returns its width. """
        if width is not None:
            f, cap = fitted( face, s, cap * SS, width * SS, tracking )
        else:
            f, cap = sized( face, cap * SS ), cap * SS
        for d, fl in self._each( fill, layers ):
            put( d, ( xy[0] * SS, xy[1] * SS ), s, f, fl, anchor, tracking * cap )
        return text_width( s, f, tracking * cap ) / SS

    def measure( self, s, face, cap, tracking=0.0 ):
        f = sized( face, cap * SS )
        return text_width( s, f, tracking * cap * SS ) / SS

    def arrays( self ):
        colour = np.asarray( self.colour.reduce( SS ), float )
        return colour, { k: np.asarray( v.reduce( SS ), float ) / 255.0 for k, v in self.layers.items() }


def arrow( angle, cx, cy, s ):
    """ A wayfinding arrow s px long pointing at angle (0 right, pi/2 down) round ( cx, cy ). """
    hl, L = 0.44 * s, s
    shape = [ ( -L / 2, -0.11 * s ), ( L / 2 - hl, -0.11 * s ), ( L / 2 - hl, -0.36 * s ), ( L / 2, 0 ),
              ( L / 2 - hl, 0.36 * s ), ( L / 2 - hl, 0.11 * s ), ( -L / 2, 0.11 * s ) ]
    return rotated( shape, angle, cx, cy )


SIGN_BLUE = ( 20, 44, 98 )
SIGN_WHITE = ( 244, 246, 246 )
SIGN_GREEN = ( 0, 128, 70 )

SIGNS_RECTS = {}
for _k, _name in enumerate( [ f"gleis_{i}" for i in range( 1, 7 ) ] + [ "info", "wc", "aufzug" ]
                            + [ f"sector_{c}" for c in "abcdef" ] ):
    SIGNS_RECTS[_name] = ( 8 + 200 * ( _k % 10 ), 8 + 200 * ( _k // 10 ), 200 + 200 * ( _k % 10 ), 200 + 200 * ( _k // 10 ) )
SIGNS_RECTS.update( {
    "warn_gleise": ( 1000, 208, 1576, 400 ), "notausgang": ( 1584, 208, 1968, 400 ),
    "station_name": ( 8, 408, 1160, 600 ), "gleis_1_2": ( 1168, 408, 1936, 600 ),
    "gueterbahnhof": ( 8, 608, 1160, 800 ), "gleis_3_4": ( 1168, 608, 1936, 800 ),
    "to_gleis_left": ( 8, 808, 968, 1000 ), "to_gleis_right": ( 976, 808, 1936, 1000 ),
    "ausgang_left": ( 8, 1008, 968, 1200 ), "ausgang_right": ( 976, 1008, 1936, 1200 ),
    "ausgang_west": ( 8, 1208, 968, 1400 ), "ausgang_ost": ( 976, 1208, 1936, 1400 ),
    "gleis_5_6": ( 8, 1408, 776, 1600 ), "fahrkarten": ( 784, 1408, 1552, 1600 ), "taxi": ( 1560, 1408, 1944, 1600 ),
    "reisezentrum": ( 8, 1608, 968, 1800 ), "schliessfaecher": ( 976, 1608, 1936, 1800 ),
    "gleis_ahead": ( 8, 1808, 968, 2000 ), "ausgang_ahead": ( 976, 1808, 1936, 2000 ),
} )


def _face( sh, name, colour=SIGN_BLUE, rule=SIGN_WHITE, light=1.0 ):
    """ A sign's face: the colour, a thin rule inset round it, and the light it gives (backlit). Returns its box and
    unit (a sixth of its height). """
    x0, y0, x1, y1 = sh.box( name )
    h = y1 - y0
    sh.rectangle( ( x0, y0, x1, y1 ), colour, { "light": light, "rough": 0.28 } )
    inset = 0.055 * h
    sh.rectangle( ( x0 + inset, y0 + inset, x1 - inset, y1 - inset ), None, { "light": light },
                  radius=0.04 * h, outline=rule, width=max( 2.0, 0.016 * h ) )
    return ( x0, y0, x1, y1 ), h / 6.0


def _ticket( sh, cx, cy, s, fg, bg ):
    """ A ticket pictogram s px wide. """
    w, h = s, 0.56 * s
    sh.rectangle( ( cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2 ), fg, { "light": 1 }, radius=0.06 * s )
    for side in ( -1, 1 ):
        sh.dot( cx + side * w / 2, cy, 0.09 * s, bg )
    for k in range( 5 ):
        yy = cy - h / 2 + ( k + 0.7 ) * h / 5.4
        sh.rectangle( ( cx - 0.24 * s - 0.018 * s, yy, cx - 0.24 * s + 0.018 * s, yy + 0.09 * s ), bg )
    sh.rectangle( ( cx - 0.12 * s, cy - 0.12 * s, cx + 0.36 * s, cy - 0.06 * s ), bg )
    sh.rectangle( ( cx - 0.12 * s, cy + 0.02 * s, cx + 0.26 * s, cy + 0.08 * s ), bg )


def _taxi( sh, cx, cy, s, fg, bg ):
    """ A car seen from the side with a roof sign, s px wide. """
    body = [ ( -0.5, 0.12 ), ( -0.48, -0.06 ), ( -0.3, -0.1 ), ( -0.18, -0.3 ), ( 0.2, -0.3 ), ( 0.32, -0.1 ),
             ( 0.48, -0.06 ), ( 0.5, 0.12 ) ]
    sh.polygon( [ ( cx + s * u, cy + s * v ) for u, v in body ], fg, { "light": 1 } )
    sh.polygon( [ ( cx + s * u, cy + s * v ) for u, v in ( ( -0.14, -0.12 ), ( -0.08, -0.25 ), ( 0.0, -0.25 ),
                                                            ( 0.0, -0.12 ) ) ], bg )
    sh.polygon( [ ( cx + s * u, cy + s * v ) for u, v in ( ( 0.04, -0.12 ), ( 0.04, -0.25 ), ( 0.16, -0.25 ),
                                                            ( 0.24, -0.12 ) ) ], bg )
    sh.rectangle( ( cx - 0.08 * s, cy - 0.4 * s, cx + 0.1 * s, cy - 0.33 * s ), fg, { "light": 1 } )
    for u in ( -0.29, 0.29 ):
        sh.dot( cx + u * s, cy + 0.13 * s, 0.12 * s, bg )
        sh.dot( cx + u * s, cy + 0.13 * s, 0.085 * s, fg, { "light": 1 } )
        sh.dot( cx + u * s, cy + 0.13 * s, 0.035 * s, bg )


def _lift( sh, cx, cy, s, fg, bg ):
    """ A lift: the car with a person in it, and up and down arrowheads beside it. """
    w, h = 0.5 * s, 0.8 * s
    x0 = cx - 0.42 * s
    sh.rectangle( ( x0, cy - h / 2, x0 + w, cy + h / 2 ), None, { "light": 1 }, outline=fg, width=0.06 * s )
    px = x0 + w / 2
    sh.dot( px, cy - 0.2 * s, 0.07 * s, fg, { "light": 1 } )
    sh.rectangle( ( px - 0.09 * s, cy - 0.11 * s, px + 0.09 * s, cy + 0.12 * s ), fg, { "light": 1 }, radius=0.03 * s )
    sh.rectangle( ( px - 0.075 * s, cy + 0.1 * s, px - 0.01 * s, cy + 0.32 * s ), fg, { "light": 1 } )
    sh.rectangle( ( px + 0.01 * s, cy + 0.1 * s, px + 0.075 * s, cy + 0.32 * s ), fg, { "light": 1 } )
    ax = cx + 0.3 * s
    sh.polygon( [ ( ax - 0.13 * s, cy - 0.06 * s ), ( ax + 0.13 * s, cy - 0.06 * s ), ( ax, cy - 0.3 * s ) ], fg, { "light": 1 } )
    sh.polygon( [ ( ax - 0.13 * s, cy + 0.06 * s ), ( ax + 0.13 * s, cy + 0.06 * s ), ( ax, cy + 0.3 * s ) ], fg, { "light": 1 } )


def _lockers( sh, cx, cy, s, fg, bg ):
    """ Luggage lockers: a block of six doors, one with a key. """
    w, h = 0.66 * s, 0.84 * s
    x0, y0 = cx - w / 2, cy - h / 2
    for i in range( 2 ):
        for j in range( 3 ):
            gx, gy = x0 + i * w / 2, y0 + j * h / 3
            sh.rectangle( ( gx + 0.025 * s, gy + 0.025 * s, gx + w / 2 - 0.025 * s, gy + h / 3 - 0.025 * s ), fg, { "light": 1 },
                          radius=0.02 * s )
            sh.rectangle( ( gx + w / 2 - 0.1 * s, gy + h / 6 - 0.025 * s, gx + w / 2 - 0.07 * s, gy + h / 6 + 0.025 * s ), bg )


def _running_man( sh, cx, cy, s, fg ):
    """ The emergency exit's running figure (after ISO 7010 E001's pose), s px tall, running right. """
    w = 0.13 * s
    pts = lambda seq: [ ( cx + s * u, cy + s * v ) for u, v in seq ]
    sh.dot( cx + 0.1 * s, cy - 0.38 * s, 0.085 * s, fg, { "light": 1 } )
    sh.line( pts( [ ( 0.04, -0.22 ), ( -0.06, 0.08 ) ] ), fg, w * 1.15, { "light": 1 } )
    sh.line( pts( [ ( 0.02, -0.18 ), ( 0.2, -0.08 ), ( 0.32, -0.16 ) ] ), fg, w * 0.75, { "light": 1 } )
    sh.line( pts( [ ( 0.02, -0.18 ), ( -0.16, -0.12 ), ( -0.24, 0.0 ) ] ), fg, w * 0.75, { "light": 1 } )
    sh.line( pts( [ ( -0.06, 0.08 ), ( 0.14, 0.2 ), ( 0.1, 0.42 ) ] ), fg, w * 0.9, { "light": 1 } )
    sh.line( pts( [ ( -0.06, 0.08 ), ( -0.16, 0.3 ), ( -0.36, 0.34 ) ] ), fg, w * 0.9, { "light": 1 } )


def _warning( sh, cx, cy, s ):
    """ The yellow warning triangle with its black border and exclamation mark, s px wide. """
    tri = lambda k: [ ( cx, cy - 0.5 * k * s ), ( cx + 0.55 * k * s, cy + 0.45 * k * s ), ( cx - 0.55 * k * s, cy + 0.45 * k * s ) ]
    sh.polygon( tri( 1.0 ), ( 20, 20, 20 ) )
    sh.polygon( [ ( x_, y_ + 0.02 * s ) for x_, y_ in tri( 0.76 ) ], ( 248, 196, 0 ) )
    sh.polygon( [ ( cx - 0.045 * s, cy - 0.2 * s ), ( cx + 0.045 * s, cy - 0.2 * s ), ( cx + 0.025 * s, cy + 0.14 * s ),
                  ( cx - 0.025 * s, cy + 0.14 * s ) ], ( 20, 20, 20 ) )
    sh.dot( cx, cy + 0.25 * s, 0.045 * s, ( 20, 20, 20 ) )


def signs( rng, n ):
    """ Backlit wayfinding signs (rw_signs): white lettering in a DIN typeface on dark blue, a thin white rule inset round
    each face, as German stations sign their platforms, exits and services. Arrows and pictograms are drawn as shapes.
    The emergency exit sign is green (after ISO 7010's E001 with an arrow), and the track warning a black-on-white
    plate with a yellow triangle, not lit. The self-illumination mask is written as signs_illum.png. """
    W, B = SIGN_WHITE, SIGN_BLUE
    sh = Sheet( n, n, SIGNS_RECTS, B, rough=0.28, light=0.0 )
    L = { "light": 1 }
    for i in range( 1, 7 ):
        ( x0, y0, x1, y1 ), u = _face( sh, f"gleis_{i}" )
        sh.text( ( ( x0 + x1 ) / 2, ( y0 + y1 ) / 2 + 1.9 * u ), str( i ), "Dinish-Bold", 3.8 * u, W, L, anchor="ms" )
    for c in "abcdef":
        ( x0, y0, x1, y1 ), u = _face( sh, f"sector_{c}" )
        sh.text( ( ( x0 + x1 ) / 2, ( y0 + y1 ) / 2 + 1.8 * u ), c.upper(), "Dinish-Bold", 3.6 * u, W, L, anchor="ms" )
    ( x0, y0, x1, y1 ), u = _face( sh, "info" )
    cx, cy = ( x0 + x1 ) / 2, ( y0 + y1 ) / 2
    sh.dot( cx, cy, 2.05 * u, W, L )
    sh.text( ( cx, cy + 1.3 * u ), "i", "Dinish-Bold", 2.6 * u, B, anchor="ms" )
    ( x0, y0, x1, y1 ), u = _face( sh, "wc" )
    sh.text( ( ( x0 + x1 ) / 2, ( y0 + y1 ) / 2 + 1.25 * u ), "WC", "Dinish-Bold", 2.5 * u, W, L, anchor="ms",
             width=x1 - x0 - 1.8 * u )
    ( x0, y0, x1, y1 ), u = _face( sh, "aufzug" )
    _lift( sh, ( x0 + x1 ) / 2, ( y0 + y1 ) / 2, 4.2 * u, W, B )

    # The platforms' double numbers: "Gleis" and each number on a white square.
    for name, nums in ( ( "gleis_1_2", "12" ), ( "gleis_3_4", "34" ), ( "gleis_5_6", "56" ) ):
        ( x0, y0, x1, y1 ), u = _face( sh, name )
        cy = ( y0 + y1 ) / 2
        sh.text( ( x0 + 1.2 * u, cy + 1.25 * u ), "Gleis", "Dinish-Regular", 2.5 * u, W, L )
        for k, num in enumerate( nums ):
            bx = x1 - 1.0 * u - ( 2 - k ) * 4.4 * u
            sh.rectangle( ( bx, cy - 2.0 * u, bx + 4.0 * u, cy + 2.0 * u ), W, L, radius=0.3 * u )
            sh.text( ( bx + 2.0 * u, cy + 1.4 * u ), num, "Dinish-Bold", 2.8 * u, B, anchor="ms" )

    for name, s_ in ( ( "station_name", "Hohenwald Hbf" ), ( "gueterbahnhof", "Güterbahnhof" ) ):
        ( x0, y0, x1, y1 ), u = _face( sh, name )
        sh.text( ( ( x0 + x1 ) / 2, ( y0 + y1 ) / 2 + 1.35 * u ), s_, "Dinish-Regular", 2.7 * u, W, L, anchor="ms",
                 width=x1 - x0 - 3 * u )

    # Directions: the arrow on the side it points to.
    for name, words, side in ( ( "to_gleis_left", "Gleise 1–6", -1 ), ( "to_gleis_right", "Gleise 1–6", 1 ),
                               ( "ausgang_left", "Ausgang", -1 ), ( "ausgang_right", "Ausgang", 1 ),
                               ( "gleis_ahead", "Gleise 1–6", 0 ), ( "ausgang_ahead", "Ausgang", 0 ) ):
        ( x0, y0, x1, y1 ), u = _face( sh, name )
        cy = ( y0 + y1 ) / 2
        angle = { -1: math.pi, 1: 0.0, 0: -math.pi / 2 }[side]
        ax_ = x1 - 3.2 * u if side == 1 else x0 + 3.2 * u
        sh.polygon( arrow( angle, ax_, cy, 3.6 * u ), W, L )
        tx = x0 + 6.2 * u if side != 1 else x0 + 1.4 * u
        sh.text( ( tx, cy + 1.25 * u ), words, "Dinish-Regular", 2.5 * u, W, L )
    for name, words in ( ( "ausgang_west", "Ausgang West · Taxi" ), ( "ausgang_ost", "Ausgang Ost · Bus" ) ):
        ( x0, y0, x1, y1 ), u = _face( sh, name )
        sh.text( ( x0 + 1.4 * u, ( y0 + y1 ) / 2 + 1.25 * u ), words, "Dinish-Regular", 2.5 * u, W, L,
                 width=x1 - x0 - 2.8 * u )

    for name, words, picto in ( ( "fahrkarten", "Fahrkarten", _ticket ), ( "reisezentrum", "Reisezentrum", _ticket ),
                                ( "schliessfaecher", "Schließfächer", _lockers ), ( "taxi", "Taxi", _taxi ) ):
        ( x0, y0, x1, y1 ), u = _face( sh, name )
        cy = ( y0 + y1 ) / 2
        picto( sh, x0 + 3.4 * u, cy, 3.9 * u, W, B )
        sh.text( ( x0 + 6.4 * u, cy + 1.25 * u ), words, "Dinish-Regular", 2.5 * u, W, L, width=x1 - x0 - 7.6 * u )

    # The emergency exit: white on green, the running figure at a door and an arrow.
    ( x0, y0, x1, y1 ), u = _face( sh, "notausgang", SIGN_GREEN, SIGN_WHITE )
    cy = ( y0 + y1 ) / 2
    dx0 = x0 + 4.6 * u
    sh.rectangle( ( dx0, cy - 2.3 * u, dx0 + 2.4 * u, cy + 2.3 * u ), SIGN_WHITE, L )
    sh.rectangle( ( dx0 + 0.35 * u, cy - 1.95 * u, dx0 + 2.4 * u, cy + 2.3 * u ), SIGN_GREEN )
    _running_man( sh, x0 + 3.0 * u, cy + 0.1 * u, 4.4 * u, SIGN_WHITE )
    sh.polygon( arrow( 0.0, x1 - 3.4 * u, cy, 4.0 * u ), SIGN_WHITE, L )

    # The track warning: a white enamel plate with a black border, not lit.
    x0, y0, x1, y1 = sh.box( "warn_gleise" )
    u = ( y1 - y0 ) / 6
    sh.rectangle( ( x0, y0, x1, y1 ), ( 244, 244, 236 ), { "light": 0, "rough": 0.35 } )
    sh.rectangle( ( x0 + 0.25 * u, y0 + 0.25 * u, x1 - 0.25 * u, y1 - 0.25 * u ), None, outline=( 20, 20, 20 ), width=0.22 * u,
                  radius=0.2 * u )
    _warning( sh, x0 + 2.7 * u, ( y0 + y1 ) / 2, 3.6 * u )
    sh.text( ( x0 + 5.0 * u, y0 + 2.75 * u ), "Achtung! Gleisbereich", "Dinish-Bold", 1.25 * u, ( 20, 20, 20 ),
             width=x1 - x0 - 5.7 * u )
    sh.text( ( x0 + 5.0 * u, y0 + 4.55 * u ), "Betreten verboten", "Dinish-Regular", 1.25 * u, ( 20, 20, 20 ),
             width=x1 - x0 - 5.7 * u )

    colour, layers = sh.arrays()
    # Backlighting falls off a little towards each face's edges; a faint sheen of dust on the faces.
    x, y = coords( n )
    fall = np.ones( ( n, n ) )
    for name, ( x0, y0, x1, y1 ) in SIGNS_RECTS.items():
        if name == "warn_gleise":
            continue
        sl = ( slice( y0, y1 ), slice( x0, x1 ) )
        ex = np.minimum( x[sl] - x0, x1 - x[sl] ) / ( y1 - y0 )
        ey = np.minimum( y[sl] - y0, y1 - y[sl] ) / ( y1 - y0 )
        fall[sl] = 0.9 + 0.1 * smoothstep( 0.0, 0.35, np.minimum( ex, ey ) )
    dust = smoothstep( -0.5, 2.5, noise( rng, n, 2.6, 2, 40 ) )
    colour = darken( colour, fall * ( 1.0 - 0.05 * dust ) )
    rough = np.clip( layers["rough"] + 0.15 * dust, 0, 1 )
    height = 0.004 * noise( rng, n, 1.0, n / 6 )
    return { "rw_signs": colour }, rough, height, 8.0, { "illum": layers["light"] }


DISPLAY_BLUE = ( 8, 34, 104 )
DISPLAY_WHITE = ( 236, 240, 250 )
DISPLAY_YELLOW = ( 255, 214, 40 )
DISPLAY_DIM = ( 150, 172, 220 )

# The board at 14:03 (the design doc's table): time, train, destination, via, platform, note.
DEPARTURES = [
    ( "14:05", "RE 4712", "München Hbf", "Augsburg Hbf", "3", "" ),
    ( "14:08", "RE 4721", "Nürnberg Hbf", "Ansbach", "4", "" ),
    ( "14:12", "IC 2216", "Berlin Hbf", "Leipzig Hbf", "1", "" ),
    ( "14:20", "EC 113", "Wien Hbf", "Salzburg Hbf", "6", "+5" ),
    ( "14:24", "RB 58", "Neustadt", "Hohenwald-Süd", "2", "" ),
    ( "14:31", "S 3", "Hohenwald-Ost", "Stadtmitte", "5", "" ),
    ( "14:40", "IC 2091", "Hamburg-Altona", "Hannover Hbf", "1", "" ),
    ( "14:52", "IC 119", "Zürich HB", "Stuttgart Hbf", "5", "" ),
    ( "15:05", "RE 4714", "München Hbf", "Augsburg Hbf", "3", "" ),
]
# The arrivals over the same hour: time, train, from, via, platform, note.
ARRIVALS = [
    ( "14:11", "RB 57", "Neustadt", "Hohenwald-Süd", "2", "" ),
    ( "14:15", "S 3", "Hohenwald-Ost", "Stadtmitte", "5", "" ),
    ( "14:18", "RE 4709", "Nürnberg Hbf", "Ansbach", "4", "" ),
    ( "14:26", "IC 2090", "Hamburg-Altona", "Hannover Hbf", "1", "" ),
    ( "14:33", "EC 112", "Wien Hbf", "Salzburg Hbf", "6", "+10" ),
    ( "14:47", "IC 118", "Zürich HB", "Stuttgart Hbf", "5", "" ),
]

DISPLAYS_RECTS = { "departures": ( 8, 8, 2040, 854 ), "ticket_screen": ( 8, 1524, 648, 2004 ),
                   "arrivals": ( 664, 1524, 1816, 2004 ) }
for _i in range( 6 ):
    _x, _y = 8 + 1022 * ( _i % 2 ), 870 + 218 * ( _i // 2 )
    DISPLAYS_RECTS[f"gleis_{_i + 1}_display"] = ( _x, _y, _x + 1010, _y + 202 )


def _board( sh, name, title, subtitle, columns, rows, header_h, row_h, cap ):
    """ A departures or arrivals board: the title, the clock, the column heads and the rows. columns: ( head, x share,
    face, anchor ) per column. """
    x0, y0, x1, y1 = sh.box( name )
    w = x1 - x0
    L = { "light": 1.0 }
    sh.rectangle( ( x0, y0, x1, y1 ), DISPLAY_BLUE, L )
    sh.text( ( x0 + 0.015 * w, y0 + 0.62 * header_h ), title, "Dinish-Bold", 0.42 * header_h, DISPLAY_WHITE, L )
    tw = sh.measure( title, "Dinish-Bold", 0.42 * header_h )
    sh.text( ( x0 + 0.015 * w + tw + 0.3 * header_h, y0 + 0.62 * header_h ), subtitle, "Dinish-Italic", 0.26 * header_h,
             DISPLAY_DIM, L )
    sh.text( ( x1 - 0.015 * w, y0 + 0.62 * header_h ), "14:03", "Dinish-Bold", 0.42 * header_h, DISPLAY_WHITE, L,
             anchor="rs" )
    hy = y0 + header_h
    for head, share, face, anchor in columns:
        sh.text( ( x0 + share * w, hy + 0.62 * row_h * 0.75 ), head, "Dinish-Regular", 0.55 * cap, DISPLAY_DIM, L,
                 anchor=anchor )
    top = hy + 0.75 * row_h
    sh.rectangle( ( x0 + 0.01 * w, top - 2, x1 - 0.01 * w, top ), DISPLAY_DIM, L )
    for r, row in enumerate( rows ):
        ry = top + r * row_h
        if r % 2:
            sh.rectangle( ( x0 + 0.01 * w, ry, x1 - 0.01 * w, ry + row_h ), ( 14, 46, 128 ), L )
        for ( head, share, face, anchor ), value in zip( columns, row ):
            colour = DISPLAY_YELLOW if value.startswith( "+" ) else DISPLAY_WHITE
            sh.text( ( x0 + share * w, ry + 0.5 * row_h + 0.5 * cap ), value, face, cap, colour, L, anchor=anchor )


def _platform_display( sh, name, row ):
    """ A platform's display: the next train's time and number at the left, its destination large with the stations it
    calls at above, the platform's number at the right, a delay in yellow. """
    time_, train, dest, via, track, note = row
    x0, y0, x1, y1 = sh.box( name )
    h = y1 - y0
    L = { "light": 1.0 }
    sh.rectangle( ( x0, y0, x1, y1 ), DISPLAY_BLUE, L )
    sh.text( ( x0 + 0.12 * h, y0 + 0.4 * h ), time_, "Dinish-Bold", 0.24 * h, DISPLAY_WHITE, L )
    sh.text( ( x0 + 0.12 * h, y0 + 0.78 * h ), train, "Dinish-Regular", 0.17 * h, DISPLAY_WHITE, L )
    mx = x0 + 1.55 * h
    sh.rectangle( ( mx - 0.08 * h, y0 + 0.12 * h, mx - 0.07 * h, y1 - 0.12 * h ), DISPLAY_DIM, L )
    if note:                                              # the delay takes the line the stations it calls at had
        words = f"ca. {note[1:]} Minuten später"
        tw = sh.measure( words, "Dinish-Bold", 0.14 * h )
        sh.rectangle( ( mx, y0 + 0.1 * h, mx + tw + 0.14 * h, y0 + 0.34 * h ), DISPLAY_YELLOW, L )
        sh.text( ( mx + 0.07 * h, y0 + 0.29 * h ), words, "Dinish-Bold", 0.14 * h, DISPLAY_BLUE, L )
    else:
        sh.text( ( mx, y0 + 0.3 * h ), f"über {via}", "Dinish-Regular", 0.15 * h, DISPLAY_WHITE, L )
    sh.text( ( mx, y0 + 0.78 * h ), dest, "Dinish-Bold", 0.34 * h, DISPLAY_WHITE, L, width=x1 - 1.15 * h - mx )
    sh.rectangle( ( x1 - 0.95 * h, y0 + 0.12 * h, x1 - 0.94 * h, y1 - 0.12 * h ), DISPLAY_DIM, L )
    sh.text( ( x1 - 0.47 * h, y0 + 0.66 * h ), "Gleis", "Dinish-Regular", 0.1 * h, DISPLAY_DIM, L, anchor="ms" )
    sh.text( ( x1 - 0.47 * h, y0 + 0.5 * h ), track, "Dinish-Bold", 0.36 * h, DISPLAY_WHITE, L, anchor="ms" )


def _ticket_screen( sh, name ):
    """ A ticket machine's touch screen on its first page: where to, the usual destinations, and the other tickets. """
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    L = { "light": 0.55 }
    ink, blue = ( 30, 36, 48 ), ( 26, 76, 168 )
    sh.rectangle( ( x0, y0, x1, y1 ), ( 234, 238, 244 ), L )
    sh.rectangle( ( x0, y0, x1, y0 + 0.12 * h ), ( 14, 42, 110 ), L )
    sh.text( ( x0 + 0.04 * w, y0 + 0.085 * h ), "Fahrkarten", "Dinish-Bold", 0.05 * h, ( 255, 255, 255 ), L )
    sh.text( ( x1 - 0.04 * w, y0 + 0.085 * h ), "14:03", "Dinish-Regular", 0.05 * h, ( 255, 255, 255 ), L, anchor="rs" )
    sh.text( ( x0 + 0.05 * w, y0 + 0.22 * h ), "Wohin möchten Sie fahren?", "Dinish-Bold", 0.045 * h, ink, L )
    sh.rectangle( ( x0 + 0.05 * w, y0 + 0.26 * h, x1 - 0.05 * w, y0 + 0.36 * h ), ( 255, 255, 255 ), L, radius=0.01 * h,
                  outline=( 150, 160, 176 ), width=2 )
    sh.text( ( x0 + 0.08 * w, y0 + 0.33 * h ), "Zielbahnhof eingeben", "Dinish-Regular", 0.038 * h, ( 140, 146, 156 ), L )
    gx, gy = x1 - 0.1 * w, y0 + 0.305 * h
    sh.ellipse( ( gx - 0.022 * h, gy - 0.022 * h, gx + 0.022 * h, gy + 0.022 * h ), None, L, outline=ink, width=3 )
    sh.line( [ ( gx + 0.015 * h, gy + 0.015 * h ), ( gx + 0.04 * h, gy + 0.04 * h ) ], ink, 4, L )
    sh.text( ( x0 + 0.05 * w, y0 + 0.44 * h ), "Häufige Ziele", "Dinish-Regular", 0.036 * h, ( 90, 98, 112 ), L )
    places = [ "München Hbf", "Nürnberg Hbf", "Augsburg Hbf", "Berlin Hbf", "Wien Hbf", "Hohenwald-Süd" ]
    bw, bh = 0.43 * w, 0.085 * h
    for k, place in enumerate( places ):
        bx = x0 + 0.05 * w + ( k % 2 ) * ( bw + 0.04 * w )
        by = y0 + 0.47 * h + ( k // 2 ) * ( bh + 0.025 * h )
        sh.rectangle( ( bx, by, bx + bw, by + bh ), blue, L, radius=0.012 * h )
        sh.text( ( bx + 0.04 * w, by + 0.62 * bh ), place, "Dinish-Regular", 0.036 * h, ( 255, 255, 255 ), L )
    for k, ( label, colour ) in enumerate( ( ( "Tageskarte", ( 220, 226, 236 ) ), ( "Gruppenkarte", ( 220, 226, 236 ) ),
                                             ( "Abbrechen", ( 196, 52, 44 ) ) ) ):
        bx = x0 + 0.05 * w + k * 0.31 * w
        sh.rectangle( ( bx, y0 + 0.84 * h, bx + 0.28 * w, y0 + 0.94 * h ), colour, L, radius=0.012 * h,
                      outline=( 170, 178, 192 ) if k < 2 else None, width=2 )
        sh.text( ( bx + 0.14 * w, y0 + 0.905 * h ), label, "Dinish-Regular", 0.036 * h,
                 ink if k < 2 else ( 255, 255, 255 ), L, anchor="ms" )


def displays( rng, n ):
    """ The self-lit displays (rw_displays): the concourse's departures board and its arrivals board, one display per
    platform, and a ticket machine's screen. LCD panels: white lettering on deep blue, notes in yellow, at 14:03 by the
    clock. The board's rows are the design doc's table; each platform's display shows its next train from it. The
    self-illumination mask (displays_illum.png) dims the ticket screen's light pages. """
    sh = Sheet( n, n, DISPLAYS_RECTS, DISPLAY_BLUE, rough=0.18, light=0.0 )
    dep_cols = [ ( "Zeit", 0.015, "Dinish-Bold", "ls" ), ( "Zug", 0.1, "Dinish-Regular", "ls" ),
                 ( "Ziel", 0.23, "Dinish-Bold", "ls" ), ( "über", 0.48, "Dinish-Regular", "ls" ),
                 ( "Gleis", 0.815, "Dinish-Bold", "ms" ), ( "Hinweis", 0.875, "Dinish-Bold", "ls" ) ]
    _board( sh, "departures", "Abfahrt", "Departure", dep_cols, DEPARTURES, 112, 74, 34 )
    arr_cols = [ ( "Zeit", 0.015, "Dinish-Bold", "ls" ), ( "Zug", 0.1, "Dinish-Regular", "ls" ),
                 ( "von", 0.23, "Dinish-Bold", "ls" ), ( "über", 0.5, "Dinish-Regular", "ls" ),
                 ( "Gleis", 0.8, "Dinish-Bold", "ms" ), ( "Hinweis", 0.87, "Dinish-Bold", "ls" ) ]
    _board( sh, "arrivals", "Ankunft", "Arrival", arr_cols, ARRIVALS, 76, 54, 23 )
    for track in range( 1, 7 ):
        row = next( r for r in DEPARTURES if r[4] == str( track ) )
        _platform_display( sh, f"gleis_{track}_display", row )
    _ticket_screen( sh, "ticket_screen" )
    colour, layers = sh.arrays()
    smear = smoothstep( 0.5, 2.5, noise( rng, n, 2.4, 2, 40 ) )
    rough = np.clip( layers["rough"] + 0.12 * smear, 0, 1 )
    return { "rw_displays": colour }, rough, 0.0, 8.0, { "illum": layers["light"] }


POSTERS_RECTS = {
    "timetable_dep": ( 8, 8, 600, 845 ), "timetable_arr": ( 616, 8, 1208, 845 ), "network_map": ( 1224, 8, 2040, 585 ),
    "stellwerk_hf": ( 1224, 601, 1824, 801 ), "poster_alps": ( 8, 861, 504, 1562 ), "poster_sea": ( 520, 861, 1016, 1562 ),
    "poster_city": ( 1032, 861, 1528, 1562 ), "poster_bike": ( 1544, 861, 2040, 1562 ),
    "station_enamel": ( 8, 1578, 1208, 1778 ), "notice_a4": ( 1224, 1578, 1524, 2002 ),
}
INK = ( 24, 24, 26 )

# The day's trains at Hohenwald, for the printed timetables, matching the displays at 14:03 (DEPARTURES, ARRIVALS):
# minute past the hour, category, the train's number in the 14 o'clock hour (or the nearest run) and how much it goes up
# each run, every how many hours it runs, its first and last hour, its platform, and its other stations in the order
# it calls at them, with their minutes from Hohenwald.
DEPARTING = [
    ( 5, "RE", 4712, 2, 1, 5, 22, "3", [ ( "Augsburg Hbf", 43 ), ( "München Hbf", 83 ) ] ),
    ( 8, "RE", 4721, 2, 1, 5, 22, "4", [ ( "Ansbach", 38 ), ( "Nürnberg Hbf", 71 ) ] ),
    ( 12, "IC", 2216, 2, 2, 6, 20, "1", [ ( "Leipzig Hbf", 130 ), ( "Berlin Hbf", 205 ) ] ),
    ( 20, "EC", 113, 2, 2, 6, 20, "6", [ ( "Salzburg Hbf", 125 ), ( "Wien Hbf", 270 ) ] ),
    ( 24, "RB", 58, 0, 1, 5, 23, "2", [ ( "Hohenwald-Süd", 9 ), ( "Neustadt", 27 ) ] ),
    ( 31, "S", 3, 0, 1, 5, 23, "5", [ ( "Stadtmitte", 4 ), ( "Hohenwald-Ost", 11 ) ] ),
    ( 40, "IC", 2091, 2, 2, 6, 20, "1", [ ( "Hannover Hbf", 185 ), ( "Hamburg-Altona", 260 ) ] ),
    ( 52, "IC", 119, 2, 2, 6, 20, "5", [ ( "Stuttgart Hbf", 130 ), ( "Zürich HB", 305 ) ] ),
]
ARRIVING = [
    ( 11, "RB", 57, 0, 1, 5, 23, "2", [ ( "Neustadt", 27 ), ( "Hohenwald-Süd", 9 ) ] ),
    ( 15, "S", 3, 0, 1, 5, 23, "5", [ ( "Hohenwald-Ost", 11 ), ( "Stadtmitte", 4 ) ] ),
    ( 18, "RE", 4709, 2, 1, 5, 22, "4", [ ( "Nürnberg Hbf", 71 ), ( "Ansbach", 38 ) ] ),
    ( 26, "IC", 2090, 2, 2, 6, 20, "1", [ ( "Hamburg-Altona", 260 ), ( "Hannover Hbf", 185 ) ] ),
    ( 33, "EC", 112, 2, 2, 6, 20, "6", [ ( "Wien Hbf", 270 ), ( "Salzburg Hbf", 125 ) ] ),
    ( 45, "IC", 2215, 2, 2, 7, 21, "1", [ ( "Berlin Hbf", 205 ), ( "Leipzig Hbf", 130 ) ] ),
    ( 47, "IC", 118, 2, 2, 6, 20, "5", [ ( "Zürich HB", 305 ), ( "Stuttgart Hbf", 130 ) ] ),
    ( 52, "RE", 4711, 2, 1, 5, 22, "3", [ ( "München Hbf", 83 ), ( "Augsburg Hbf", 43 ) ] ),
]


def _clock( minutes ):
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _timetable_rows( arrivals ):
    """ ( hour, time, train, route, platform ) for every train in the day, departures or arrivals, in time order. The
    route lists the other stations with the train's time there. """
    rows = []
    for minute, cat, number, step, every, first, last, track, stops in ARRIVING if arrivals else DEPARTING:
        for hour in range( first, last + 1, every ):
            t = hour * 60 + minute
            sign = -1 if arrivals else 1
            route = " – ".join( f"{s} {_clock( t + sign * m )}" for s, m in stops )
            rows.append( ( hour, _clock( t ), f"{cat} {number + step * ( ( hour - 14 ) // every )}", route, track ) )
    rows.sort( key=lambda r: r[1] )
    return rows


def _timetable( sh, name, title, sub, paper, arrivals ):
    """ A printed station timetable, as German stations post them: yellow for departures, white for arrivals, the day's
    trains in two columns hour by hour, each with its number, the stations it calls at with their times, and its
    platform. """
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0, y0, x1, y1 ), paper, { "rough": 0.86 } )
    sh.text( ( x0 + 0.05 * w, y0 + 0.075 * h ), title, "Dinish-Bold", 0.045 * h, INK )
    sh.text( ( x0 + 0.05 * w + sh.measure( title, "Dinish-Bold", 0.045 * h ) + 12, y0 + 0.075 * h ), sub, "Dinish-Regular",
             0.02 * h, INK )
    sh.text( ( x1 - 0.05 * w, y0 + 0.075 * h ), "Hohenwald Hbf", "Dinish-Bold", 0.03 * h, INK, anchor="rs" )
    sh.rectangle( ( x0 + 0.05 * w, y0 + 0.09 * h, x1 - 0.05 * w, y0 + 0.093 * h ), INK )
    sh.text( ( x0 + 0.05 * w, y0 + 0.112 * h ), "Gültig vom 13. Dezember bis 12. Juni · Zeit, Zug, Halte, Gleis",
             "Dinish-Regular", 0.0085 * h, INK )
    rows = _timetable_rows( arrivals )
    line = 0.0098 * h
    cap = 0.0062 * h
    col_w = 0.44 * w
    top = y0 + 0.135 * h
    bottom = y1 - 0.04 * h
    col, yy, hour = 0, top, None
    for hr, time_, train, route, track in rows:
        if hr != hour:
            if yy + 2.6 * line > bottom:
                col, yy = col + 1, top
            if col > 1:
                break
            hour = hr
            cx = x0 + 0.05 * w + col * ( col_w + 0.02 * w )
            yy += 0.6 * line
            sh.rectangle( ( cx, yy - 0.2 * line, cx + col_w, yy - 0.2 * line + 1 ), INK )
            sh.text( ( cx, yy + 1.5 * line ), f"{hr:d}", "Dinish-Bold", 1.25 * line, INK )
        cx = x0 + 0.05 * w + col * ( col_w + 0.02 * w )
        yy += line
        sh.text( ( cx + 0.07 * w, yy ), time_, "Dinish-Bold", cap, INK )
        sh.text( ( cx + 0.14 * w, yy ), train, "Dinish-Regular", cap, INK )
        sh.text( ( cx + 0.225 * w, yy ), route, "Dinish-Regular", cap * 0.92, INK, width=0.19 * w )
        sh.text( ( cx + col_w, yy ), track, "Dinish-Bold", cap, INK, anchor="rs" )
        if yy + line > bottom:
            col, yy = col + 1, top
            if col > 1:
                break
    sh.text( ( x0 + 0.05 * w, y1 - 0.018 * h ), "Änderungen vorbehalten. Auskunft im Reisezentrum.", "Dinish-Regular",
             0.008 * h, INK )


def _network_map( sh, name ):
    """ The local network: Hohenwald Hbf in the middle and its lines out, each in its own colour, as a schematic with
    45 degree bends. """
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0, y0, x1, y1 ), ( 246, 246, 242 ), { "rough": 0.8 } )
    sh.text( ( x0 + 0.04 * w, y0 + 0.08 * h ), "Liniennetz", "Dinish-Bold", 0.05 * h, INK )
    sh.text( ( x0 + 0.04 * w, y0 + 0.13 * h ), "Hohenwald und Umgebung", "Dinish-Regular", 0.028 * h, INK )
    cx, cy = x0 + 0.5 * w, y0 + 0.52 * h
    sh.polygon( [ ( cx - 0.05 * w, cy - 0.3 * h ), ( cx + 0.22 * w, cy - 0.26 * h ), ( cx + 0.3 * w, cy + 0.05 * h ),
                  ( cx + 0.08 * w, cy + 0.3 * h ), ( cx - 0.25 * w, cy + 0.22 * h ), ( cx - 0.3 * w, cy - 0.12 * h ) ],
                ( 232, 238, 226 ) )
    u = 0.1 * h
    # Each line's points from the hub, and its stations' labels: r(ight), l(eft), a(bove) or b(elow) the stop. The EC
    # and the S share the corridor east, side by side.
    lines_ = [
        ( ( 196, 34, 38 ), [ ( 0, 0 ), ( 1.2, 1.2 ), ( 3.2, 1.2 ) ], [ ( "Augsburg Hbf", "b" ), ( "München Hbf", "r" ) ] ),
        ( ( 232, 120, 20 ), [ ( 0, 0 ), ( 1.4, -1.4 ), ( 3.4, -1.4 ) ], [ ( "Ansbach", "a" ), ( "Nürnberg Hbf", "r" ) ] ),
        ( ( 60, 60, 64 ), [ ( 0, 0 ), ( 0, -2.0 ), ( 0.9, -2.9 ) ], [ ( "Leipzig Hbf", "l" ), ( "Berlin Hbf", "r" ) ] ),
        ( ( 60, 60, 64 ), [ ( 0, -0.07 ), ( 3.2, -0.07 ), ( 4.4, -0.07 ) ], [ ( "Salzburg Hbf", "a" ), ( "Wien Hbf", "r" ) ] ),
        ( ( 60, 60, 64 ), [ ( 0, 0 ), ( -1.4, -1.4 ), ( -3.4, -1.4 ) ], [ ( "Hannover Hbf", "a" ), ( "Hamburg-Altona", "l" ) ] ),
        ( ( 60, 60, 64 ), [ ( 0, 0 ), ( -1.4, 1.4 ), ( -3.6, 1.4 ) ], [ ( "Stuttgart Hbf", "b" ), ( "Zürich HB", "l" ) ] ),
        ( ( 30, 90, 180 ), [ ( 0, 0 ), ( 0, 1.8 ), ( 0, 3.0 ) ], [ ( "Hohenwald-Süd", "r" ), ( "Neustadt", "r" ) ] ),
        ( ( 20, 140, 70 ), [ ( 0, 0.07 ), ( 1.0, 0.07 ), ( 2.6, 0.07 ) ], [ ( "Stadtmitte", "b" ), ( "Hohenwald-Ost", "b" ) ] ),
    ]
    for colour, pts, names in lines_:
        sh.line( [ ( cx + px * u, cy + py * u ) for px, py in pts ], colour, 0.075 * u )
    cap = 0.16 * u
    for colour, pts, names in lines_:
        for ( px, py ), ( label, side ) in zip( pts[1:], names ):
            sx, sy = cx + px * u, cy + py * u
            sh.dot( sx, sy, 0.11 * u, ( 255, 255, 255 ) )
            sh.ellipse( ( sx - 0.11 * u, sy - 0.11 * u, sx + 0.11 * u, sy + 0.11 * u ), outline=INK, width=0.03 * u )
            at, anchor = { "r": ( ( sx + 0.2 * u, sy + cap / 2 ), "ls" ), "l": ( ( sx - 0.2 * u, sy + cap / 2 ), "rs" ),
                           "a": ( ( sx, sy - 0.2 * u ), "ms" ), "b": ( ( sx, sy + 0.2 * u + cap ), "ms" ) }[side]
            sh.text( at, label, "Dinish-Regular", cap, INK, anchor=anchor )
    sh.rectangle( ( cx - 0.3 * u, cy - 0.22 * u, cx + 0.3 * u, cy + 0.22 * u ), ( 255, 255, 255 ), radius=0.1 * u,
                  outline=INK, width=0.04 * u )
    sh.text( ( cx - 0.42 * u, cy + 0.07 * u ), "Hohenwald Hbf", "Dinish-Bold", 0.2 * u, INK, anchor="rs" )
    for k, ( colour, label ) in enumerate( ( ( ( 196, 34, 38 ), "RE" ), ( ( 30, 90, 180 ), "RB" ), ( ( 20, 140, 70 ), "S" ),
                                             ( ( 60, 60, 64 ), "IC / EC" ) ) ):
        lx = x0 + 0.04 * w + k * 0.13 * w
        sh.rectangle( ( lx, y1 - 0.075 * h, lx + 0.04 * w, y1 - 0.06 * h ), colour )
        sh.text( ( lx + 0.05 * w, y1 - 0.057 * h ), label, "Dinish-Regular", 0.022 * h, INK )


def _enamel( sh, name, words, rng ):
    """ A vitreous enamel name board: black capitals on white, a black border, four bolt holes, the enamel chipped to
    the steel at the edges and round the bolts. """
    x0, y0, x1, y1 = sh.box( name )
    h = y1 - y0
    sh.rectangle( ( x0, y0, x1, y1 ), ( 238, 238, 230 ), { "rough": 0.14, "height": 0.6 }, radius=0.06 * h )
    sh.rectangle( ( x0 + 0.07 * h, y0 + 0.07 * h, x1 - 0.07 * h, y1 - 0.07 * h ), None, outline=INK, width=0.05 * h,
                  radius=0.04 * h )
    sh.text( ( ( x0 + x1 ) / 2, y0 + 0.73 * h ), words, "Dinish-Bold", 0.5 * h, INK, anchor="ms", width=x1 - x0 - 0.6 * h )
    for bx in ( x0 + 0.16 * h, x1 - 0.16 * h ):
        for by in ( y0 + 0.16 * h, y1 - 0.16 * h ):
            r = rng.uniform( 0.035, 0.05 ) * h                          # the enamel chipped round the bolt
            sh.dot( bx + rng.normal( 0, 0.005 * h ), by + rng.normal( 0, 0.005 * h ), r, ( 70, 58, 50 ),
                    { "rough": 0.7, "height": 0.45 } )
            sh.dot( bx, by, 0.022 * h, ( 30, 30, 32 ), { "rough": 0.5, "height": 0.7 } )   # the bolt's head
    for _ in range( 6 ):                                                # chips along the rim, inside the plate
        side = rng.integers( 4 )
        t = rng.uniform( 0.08, 0.92 )
        r = rng.uniform( 0.008, 0.02 ) * h
        px = x0 + t * ( x1 - x0 ) if side < 2 else ( x0 + r + 2 if side == 2 else x1 - r - 2 )
        py = ( y0 + r + 2 if side == 0 else y1 - r - 2 ) if side < 2 else y0 + t * h
        sh.dot( px, py, r, ( 70, 58, 50 ), { "rough": 0.75, "height": 0.45 } )


def _ridge( rng, x0, x1, base, rough, count=7 ):
    """ A mountain ridge's points from x0 to x1 round base, by midpoint displacement. """
    pts = [ ( x0, base + rng.normal( 0, rough ) ), ( x1, base + rng.normal( 0, rough ) ) ]
    amp = rough
    for _ in range( count ):
        out = []
        for ( ax_, ay ), ( bx, by ) in zip( pts[:-1], pts[1:] ):
            out += [ ( ax_, ay ), ( ( ax_ + bx ) / 2, ( ay + by ) / 2 + rng.normal( 0, amp ) ) ]
        pts = out + [ pts[-1] ]
        amp *= 0.55
    return pts


def _sky( sh, box, top, bottom ):
    x0, y0, x1, y1 = box
    rows = int( ( y1 - y0 ) * 2 )
    for k in range( rows ):
        t = k / max( 1, rows - 1 )
        c = tuple( a + ( b - a ) * t for a, b in zip( top, bottom ) )
        sh.rectangle( ( x0, y0 + k / 2, x1, y0 + ( k + 1 ) / 2 + 0.5 ), c )


def _poster_frame( sh, box, title, tag, band, ink ):
    """ The poster's title band at the bottom. """
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0, y1 - 0.2 * h, x1, y1 ), band )
    sh.text( ( x0 + 0.07 * w, y1 - 0.105 * h ), title, "Dinish-Bold", 0.06 * h, ink, width=0.86 * w, tracking=0.04 )
    sh.text( ( x0 + 0.07 * w, y1 - 0.05 * h ), tag, "Dinish-Regular", 0.025 * h, ink, width=0.86 * w )


def _poster_alps( sh, rng ):
    x0, y0, x1, y1 = sh.box( "poster_alps" )
    w, h = x1 - x0, y1 - y0
    art = ( x0, y0, x1, y1 - 0.2 * h )
    _sky( sh, art, ( 120, 172, 214 ), ( 236, 226, 196 ) )
    sh.dot( x0 + 0.74 * w, y0 + 0.16 * h, 0.07 * w, ( 252, 236, 170 ) )
    for base, rough, colour, snow in ( ( 0.36, 0.09, ( 150, 168, 196 ), ( 232, 238, 246 ) ),
                                       ( 0.46, 0.07, ( 96, 118, 150 ), ( 214, 224, 238 ) ),
                                       ( 0.58, 0.035, ( 46, 92, 66 ), None ) ):
        pts = _ridge( rng, x0, x1, y0 + base * h, rough * h )
        sh.polygon( pts + [ ( x1, y0 + 0.8 * h ), ( x0, y0 + 0.8 * h ) ], colour )
        if snow:
            for k in range( 1, len( pts ) - 1 ):
                if pts[k][1] < pts[k - 1][1] and pts[k][1] < pts[k + 1][1] and pts[k][1] < y0 + ( base - 0.02 ) * h:
                    px, py = pts[k]
                    sh.polygon( [ ( px, py ), ( px + 0.07 * w, py + 0.06 * h ), ( px + 0.02 * w, py + 0.05 * h ),
                                  ( px - 0.01 * w, py + 0.065 * h ), ( px - 0.06 * w, py + 0.05 * h ) ], snow )
    sh.rectangle( ( x0, y0 + 0.66 * h, x1, y0 + 0.8 * h ), ( 58, 140, 158 ) )
    for k in range( 6 ):
        yy = y0 + ( 0.68 + 0.02 * k ) * h
        sh.rectangle( ( x0 + rng.uniform( 0.05, 0.4 ) * w, yy, x0 + rng.uniform( 0.5, 0.95 ) * w, yy + 2 ), ( 120, 190, 200 ) )
    # A train on a viaduct across the valley.
    vy = y0 + 0.62 * h
    sh.rectangle( ( x0, vy, x1, vy + 0.012 * h ), ( 214, 204, 184 ) )
    for k in range( 7 ):
        ax_ = x0 + ( 0.04 + 0.145 * k ) * w
        sh.rectangle( ( ax_, vy, ax_ + 0.025 * w, y0 + 0.67 * h ), ( 214, 204, 184 ) )
    for k in range( 4 ):
        cx = x0 + ( 0.18 + 0.14 * k ) * w
        sh.rectangle( ( cx, vy - 0.035 * h, cx + 0.13 * w, vy - 0.002 * h ), ( 196, 40, 42 ), radius=0.006 * h )
        sh.rectangle( ( cx + 0.01 * w, vy - 0.03 * h, cx + 0.12 * w, vy - 0.022 * h ), ( 240, 236, 226 ) )
    _poster_frame( sh, ( x0, y0, x1, y1 ), "DIE ALPEN", "Mit dem Zug in die Berge", ( 28, 52, 92 ), ( 244, 238, 220 ) )


def _poster_sea( sh, rng ):
    x0, y0, x1, y1 = sh.box( "poster_sea" )
    w, h = x1 - x0, y1 - y0
    _sky( sh, ( x0, y0, x1, y0 + 0.45 * h ), ( 250, 214, 150 ), ( 252, 238, 206 ) )
    sh.dot( x0 + 0.3 * w, y0 + 0.3 * h, 0.1 * w, ( 248, 168, 82 ) )
    _sky( sh, ( x0, y0 + 0.45 * h, x1, y0 + 0.8 * h ), ( 40, 110, 160 ), ( 20, 70, 120 ) )
    for k in range( 18 ):
        yy = y0 + ( 0.47 + 0.018 * k ) * h
        xa = x0 + rng.uniform( 0.0, 0.6 ) * w
        sh.rectangle( ( xa, yy, xa + rng.uniform( 0.1, 0.35 ) * w, yy + 2 ), ( 120, 180, 210 ) )
    sh.polygon( [ ( x0 + 0.5 * w, y0 + 0.8 * h ), ( x0 + 0.62 * w, y0 + 0.66 * h ), ( x1, y0 + 0.62 * h ), ( x1, y0 + 0.8 * h ) ],
                ( 226, 200, 150 ) )
    sh.polygon( [ ( x0 + 0.66 * w, y0 + 0.66 * h ), ( x0 + 0.72 * w, y0 + 0.6 * h ), ( x0 + 0.92 * w, y0 + 0.6 * h ),
                  ( x1, y0 + 0.63 * h ) ], ( 120, 110, 100 ) )
    lx = x0 + 0.8 * w
    for k in range( 6 ):
        ya, yb = y0 + ( 0.33 + 0.045 * k ) * h, y0 + ( 0.33 + 0.045 * ( k + 1 ) ) * h
        sh.polygon( [ ( lx - ( 0.035 + 0.006 * k ) * w, ya ), ( lx + ( 0.035 + 0.006 * k ) * w, ya ),
                      ( lx + ( 0.041 + 0.006 * k ) * w, yb ), ( lx - ( 0.041 + 0.006 * k ) * w, yb ) ],
                    ( 200, 40, 40 ) if k % 2 == 0 else ( 246, 244, 236 ) )
    sh.rectangle( ( lx - 0.045 * w, y0 + 0.285 * h, lx + 0.045 * w, y0 + 0.33 * h ), ( 40, 44, 50 ) )
    sh.polygon( [ ( lx - 0.05 * w, y0 + 0.285 * h ), ( lx, y0 + 0.25 * h ), ( lx + 0.05 * w, y0 + 0.285 * h ) ], ( 200, 40, 40 ) )
    bx, by = x0 + 0.24 * w, y0 + 0.6 * h
    sh.polygon( [ ( bx - 0.1 * w, by ), ( bx + 0.12 * w, by ), ( bx + 0.08 * w, by + 0.03 * h ), ( bx - 0.07 * w, by + 0.03 * h ) ],
                ( 60, 40, 30 ) )
    sh.polygon( [ ( bx, by - 0.005 * h ), ( bx, by - 0.2 * h ), ( bx + 0.1 * w, by - 0.005 * h ) ], ( 248, 246, 238 ) )
    sh.polygon( [ ( bx - 0.01 * w, by - 0.005 * h ), ( bx - 0.01 * w, by - 0.15 * h ), ( bx - 0.08 * w, by - 0.005 * h ) ],
                ( 230, 226, 214 ) )
    for k in range( 4 ):
        gx, gy = x0 + rng.uniform( 0.45, 0.7 ) * w, y0 + rng.uniform( 0.08, 0.22 ) * h
        sh.line( [ ( gx - 0.03 * w, gy ), ( gx, gy + 0.01 * h ), ( gx + 0.03 * w, gy ) ], ( 60, 60, 70 ), 2.0 )
    _poster_frame( sh, ( x0, y0, x1, y1 ), "AN DIE SEE", "Sommer an der Ostsee – bequem mit der Bahn", ( 236, 226, 200 ),
                   ( 24, 64, 110 ) )


def _poster_city( sh, rng ):
    x0, y0, x1, y1 = sh.box( "poster_city" )
    w, h = x1 - x0, y1 - y0
    _sky( sh, ( x0, y0, x1, y0 + 0.8 * h ), ( 70, 56, 120 ), ( 244, 150, 90 ) )
    ground = y0 + 0.8 * h
    xs = x0
    while xs < x1:
        bw = rng.uniform( 0.07, 0.14 ) * w
        bh = rng.uniform( 0.12, 0.3 ) * h
        colour = ( 52, 40, 70 )
        sh.rectangle( ( xs, ground - bh, xs + bw, ground ), colour )
        sh.polygon( [ ( xs, ground - bh ), ( xs + bw / 2, ground - bh - 0.04 * h ), ( xs + bw, ground - bh ) ], colour )
        for wy in np.arange( ground - bh + 0.03 * h, ground - 0.02 * h, 0.035 * h ):
            for wx in np.arange( xs + 0.012 * w, xs + bw - 0.02 * w, 0.03 * w ):
                if rng.random() < 0.45:
                    sh.rectangle( ( wx, wy, wx + 0.012 * w, wy + 0.016 * h ), ( 252, 206, 110 ) )
        xs += bw + rng.uniform( 0.0, 0.02 ) * w
    # The minster's two spires and the station's arched hall in front.
    for sx in ( 0.36, 0.48 ):
        cx = x0 + sx * w
        sh.rectangle( ( cx - 0.035 * w, ground - 0.42 * h, cx + 0.035 * w, ground ), ( 36, 28, 52 ) )
        sh.polygon( [ ( cx - 0.035 * w, ground - 0.42 * h ), ( cx, ground - 0.6 * h ), ( cx + 0.035 * w, ground - 0.42 * h ) ],
                    ( 36, 28, 52 ) )
    hx0, hx1 = x0 + 0.15 * w, x0 + 0.85 * w
    pts = [ ( hx0 + ( hx1 - hx0 ) * t, ground - 0.08 * h - 0.12 * h * math.sin( math.pi * t ) ) for t in np.linspace( 0, 1, 40 ) ]
    sh.polygon( pts + [ ( hx1, ground ), ( hx0, ground ) ], ( 30, 24, 44 ) )
    inner = [ ( ( hx0 + 0.04 * w ) + ( hx1 - hx0 - 0.08 * w ) * t, ground - 0.07 * h - 0.09 * h * math.sin( math.pi * t ) )
              for t in np.linspace( 0, 1, 40 ) ]
    sh.polygon( inner + [ ( hx1 - 0.04 * w, ground - 0.05 * h ), ( hx0 + 0.04 * w, ground - 0.05 * h ) ], ( 252, 214, 140 ) )
    for k in range( 1, 8 ):
        tx = hx0 + 0.04 * w + ( hx1 - hx0 - 0.08 * w ) * k / 8
        sh.rectangle( ( tx - 1.5, ground - 0.2 * h, tx + 1.5, ground - 0.05 * h ), ( 30, 24, 44 ) )
    sh.rectangle( ( x0, ground, x1, y1 ), ( 30, 24, 44 ) )
    _poster_frame( sh, ( x0, y0, x1, y1 ), "HOHENWALD", "Die Stadt entdecken – Führungen ab dem Hauptbahnhof",
                   ( 246, 196, 92 ), ( 30, 24, 44 ) )


def _poster_bike( sh, rng ):
    x0, y0, x1, y1 = sh.box( "poster_bike" )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0, y0, x1, y1 ), ( 240, 232, 210 ) )
    sh.rectangle( ( x0, y0 + 0.46 * h, x1, y0 + 0.56 * h ), ( 32, 104, 92 ) )
    for k in range( 3 ):
        cx = x0 + ( 0.02 + 0.33 * k ) * w
        sh.rectangle( ( cx, y0 + 0.47 * h, cx + 0.31 * w, y0 + 0.54 * h ), ( 214, 70, 52 ), radius=0.01 * h )
        for j in range( 4 ):
            wx = cx + ( 0.02 + 0.075 * j ) * w
            sh.rectangle( ( wx, y0 + 0.48 * h, wx + 0.05 * w, y0 + 0.505 * h ), ( 236, 232, 222 ) )
    green = ( 22, 70, 62 )
    r = 0.15 * w
    cyw = y0 + 0.78 * h
    rx, fx = x0 + 0.27 * w, x0 + 0.73 * w
    for wx in ( rx, fx ):
        sh.ellipse( ( wx - r, cyw - r, wx + r, cyw + r ), outline=green, width=0.022 * w )
        for k in range( 12 ):
            a = k * math.pi / 6
            sh.line( [ ( wx, cyw ), ( wx + r * math.cos( a ), cyw + r * math.sin( a ) ) ], green, 1.2 )
    crank = ( x0 + 0.47 * w, cyw )
    seat = ( x0 + 0.42 * w, cyw - 0.2 * h )
    head = ( x0 + 0.67 * w, cyw - 0.2 * h )
    for a_, b_ in ( ( ( rx, cyw ), crank ), ( crank, seat ), ( seat, ( rx, cyw ) ), ( seat, head ), ( crank, head ),
                    ( head, ( fx, cyw ) ) ):
        sh.line( [ a_, b_ ], ( 214, 70, 52 ), 0.02 * w )
    sh.line( [ ( seat[0] - 0.04 * w, seat[1] - 0.02 * h ), ( seat[0] + 0.04 * w, seat[1] - 0.02 * h ) ], INK, 0.02 * w )
    sh.line( [ ( head[0], head[1] ), ( head[0] - 0.02 * w, head[1] - 0.04 * h ), ( head[0] + 0.05 * w, head[1] - 0.05 * h ) ],
             INK, 0.016 * w )
    sh.dot( crank[0], crank[1], 0.03 * w, INK )
    sh.text( ( x0 + 0.07 * w, y0 + 0.16 * h ), "FAHRRAD", "Dinish-Bold", 0.08 * h, green, tracking=0.04 )
    sh.text( ( x0 + 0.07 * w, y0 + 0.27 * h ), "& BAHN", "Dinish-Bold", 0.08 * h, ( 214, 70, 52 ), tracking=0.04 )
    sh.text( ( x0 + 0.07 * w, y0 + 0.34 * h ), "Ihr Rad fährt mit. Stellplätze in jedem Regionalzug.", "Dinish-Regular",
             0.022 * h, INK, width=0.86 * w )


def _notice( sh, name ):
    """ An A4 notice of engineering work, pinned up: a heading, a few paragraphs and a replacement bus timetable. """
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0, y0, x1, y1 ), ( 248, 248, 244 ), { "rough": 0.9 } )
    sh.rectangle( ( x0 + 0.08 * w, y0 + 0.06 * h, x0 + 0.92 * w, y0 + 0.13 * h ), ( 196, 30, 36 ) )
    sh.text( ( x0 + 0.11 * w, y0 + 0.112 * h ), "Bauarbeiten", "Dinish-Bold", 0.04 * h, ( 255, 255, 255 ) )
    sh.text( ( x0 + 0.08 * w, y0 + 0.18 * h ), "Hohenwald Hbf – Neustadt", "Dinish-Bold", 0.026 * h, INK )
    body = [ "Wegen Gleiserneuerung zwischen Hohenwald Hbf",
             "und Neustadt fallen die Züge der Linie RB 58 vom",
             "12. bis 26. Oktober aus. Zwischen Hohenwald Hbf",
             "(Ausgang West) und Neustadt fahren Busse.",
             "", "Bitte beachten Sie die geänderten Fahrzeiten.",
             "Fahrräder können nicht befördert werden." ]
    for k, s_ in enumerate( body ):
        sh.text( ( x0 + 0.08 * w, y0 + ( 0.24 + 0.032 * k ) * h ), s_, "Dinish-Regular", 0.016 * h, INK, width=0.84 * w )
    sh.text( ( x0 + 0.08 * w, y0 + 0.5 * h ), "Ersatzverkehr (Bus)", "Dinish-Bold", 0.018 * h, INK )
    columns = ( ( 0.08, "ls", "Hohenwald Hbf", 14 ), ( 0.5, "ms", "Hohenwald-Süd", 31 ), ( 0.92, "rs", "Neustadt", 44 ) )
    for cx_, anchor, stop, _ in columns:
        sh.text( ( x0 + cx_ * w, y0 + 0.54 * h ), stop, "Dinish-Bold", 0.014 * h, INK, anchor=anchor )
    for k in range( 9 ):
        yy = y0 + ( 0.58 + 0.033 * k ) * h
        sh.rectangle( ( x0 + 0.08 * w, yy + 0.008 * h, x0 + 0.92 * w, yy + 0.008 * h + 1 ), ( 180, 180, 176 ) )
        for cx_, anchor, stop, minute in columns:
            sh.text( ( x0 + cx_ * w, yy ), f"{6 + 2 * k:02d}:{minute:02d}", "Dinish-Regular", 0.016 * h, INK, anchor=anchor )
    sh.text( ( x0 + 0.08 * w, y1 - 0.05 * h ), "Wir bitten um Ihr Verständnis.", "Dinish-Italic", 0.016 * h, INK )


def posters( rng, n ):
    """ Paper and enamel (rw_posters): the station's yellow departure and white arrival timetables, a map of the local
    network, four travel posters (original flat-colour illustrations with German titles, no operator named), the signal
    box's enamel name board "Hf", an enamel "Hohenwald" station board and an A4 notice of engineering work. Paper is
    matt, faded a little and creased; the enamel is glossy, chipped to the steel at its edges and bolts. """
    sh = Sheet( n, n, POSTERS_RECTS, ( 206, 202, 192 ), rough=0.85, height=0.5 )
    _timetable( sh, "timetable_dep", "Abfahrt", "Departure", ( 250, 214, 46 ), False )
    _timetable( sh, "timetable_arr", "Ankunft", "Arrival", ( 248, 248, 244 ), True )
    _network_map( sh, "network_map" )
    _poster_alps( sh, rng )
    _poster_sea( sh, rng )
    _poster_city( sh, rng )
    _poster_bike( sh, rng )
    _notice( sh, "notice_a4" )
    _enamel( sh, "stellwerk_hf", "Hf", rng )
    _enamel( sh, "station_enamel", "Hohenwald", rng )
    colour, layers = sh.arrays()
    x, y = coords( n )
    fibre = noise( rng, n, 0.6, n / 4 )
    grime = smoothstep( -0.5, 2.5, noise( rng, n, 2.6, 2, 30 ) )
    creases = np.zeros( ( n, n ) )
    fade = np.zeros( ( n, n ) )
    for name, ( x0, y0, x1, y1 ) in POSTERS_RECTS.items():
        sl = ( slice( y0, y1 ), slice( x0, x1 ) )
        if name in ( "stellwerk_hf", "station_enamel" ):
            continue
        u = ( x[sl] - x0 ) / ( x1 - x0 )
        v = ( y[sl] - y0 ) / ( y1 - y0 )
        fade[sl] = 1.0 - 0.5 * smoothstep( 0.0, 1.0, v )                  # the sun from above fades the top more
        edge = np.minimum( np.minimum( u, 1 - u ), np.minimum( v, 1 - v ) )
        fade[sl] *= 1.0 - 0.6 * smoothstep( 0.0, 0.04, edge )
        if name.startswith( "poster" ):                                   # folded for posting
            creases[sl] = np.maximum( np.exp( -( ( u - 0.5 ) * ( x1 - x0 ) / 0.8 ) ** 2 ),
                                      np.exp( -( ( v - 0.5 ) * ( y1 - y0 ) / 0.8 ) ** 2 ) )
    paper = layers["rough"] > 0.5
    light = 1.0 + paper * ( 0.025 * fibre - 0.06 * grime - 0.05 * creases )
    colour = darken( colour, light )
    faded = srgb( lin( colour ) * 0.82 + lin( ( 236, 230, 214 ) ) * 0.18 )
    colour = mix( colour, faded, 0.35 * fade * paper )
    rough = np.clip( layers["rough"] + 0.04 * fibre * paper, 0, 1 )
    height = 0.08 * layers["height"] + 0.004 * fibre * paper - 0.01 * creases
    return { "rw_posters": colour }, rough, height, 16.0


SHOPSIGNS = [
    # name, style ("box": a backlit printed face; "letters": lit letters on an unlit panel), face, ink, face font,
    # main text, the line under it (or None), icon (or None).
    ( "baeckerei", "box", ( 238, 222, 178 ), ( 112, 64, 32 ), "Mina-Bold", "Bäckerei Brandl", "Brot · Brötchen · Kuchen",
      "pretzel" ),
    ( "apotheke", "box", ( 246, 248, 246 ), ( 0, 122, 72 ), "Dinish-Bold", "Bahnhof-Apotheke", None, "cross" ),
    ( "imbiss", "box", ( 250, 202, 44 ), ( 186, 30, 30 ), "ChakraPetch-Bold", "Imbiss am Gleis",
      "Currywurst · Pommes · Getränke", None ),
    ( "reisebuero", "box", ( 248, 248, 246 ), ( 22, 72, 152 ), "Dinish-Bold", "Reisebüro Fernweh",
      "Urlaub · Flüge · Bahnreisen", "plane" ),
    ( "hotel", "letters", ( 24, 54, 42 ), ( 236, 200, 116 ), "Dinish-Regular", "HOTEL KAISERHOF", None, "stars" ),
    ( "cafe", "letters", ( 54, 36, 28 ), ( 252, 236, 204 ), "Mina-Bold", "Café am Bahnhof", None, "cup" ),
    ( "friseur", "letters", ( 26, 26, 28 ), ( 246, 246, 246 ), "Dinish-Bold", "Salon Elke", "Friseur · Damen & Herren",
      "scissors" ),
    ( "kiosk", "box", ( 200, 38, 38 ), ( 252, 252, 250 ), "ChakraPetch-Bold", "Kiosk", "Zeitschriften · Getränke · Snacks",
      None ),
    ( "buchhandlung", "letters", ( 26, 42, 72 ), ( 244, 244, 240 ), "Dinish-Regular", "Bahnhofsbuchhandlung",
      "Bücher · Zeitschriften · Karten", "book" ),
    ( "blumen", "box", ( 64, 122, 64 ), ( 252, 252, 248 ), "Mina-Bold", "Blumen Lindner", "Sträuße · Pflanzen · Gestecke",
      "flower" ),
    ( "optik", "box", ( 246, 246, 244 ), ( 40, 42, 46 ), "Dinish-Regular", "Optik Weiß", "Brillen · Kontaktlinsen",
      "glasses" ),
    ( "pension", "box", ( 244, 242, 232 ), ( 36, 62, 40 ), "Dinish-Regular", "Pension Lindenhof", None, "zimmer" ),
    ( "metzgerei", "box", ( 176, 28, 32 ), ( 252, 250, 246 ), "Dinish-Bold", "Metzgerei Huber", "Fleisch- und Wurstwaren",
      None ),
    ( "pizzeria", "letters", ( 22, 22, 24 ), ( 252, 248, 240 ), "ChakraPetch-BoldItalic", "Pizzeria Napoli", None, "flag" ),
    ( "schuhmacher", "box", ( 232, 228, 216 ), ( 58, 44, 34 ), "Dinish-Bold", "Schuhmacherei Wolf", "Reparaturen · Pflege",
      "shoe" ),
    ( "schluesseldienst", "box", ( 250, 208, 52 ), ( 24, 24, 26 ), "ChakraPetch-Bold", "Schlüsseldienst", "Tag und Nacht",
      "key" ),
    ( "getraenke", "box", ( 20, 92, 172 ), ( 252, 252, 250 ), "Dinish-Bold", "Getränkemarkt", "Bier · Wasser · Säfte",
      "bottle" ),
    ( "tabak", "box", ( 116, 26, 30 ), ( 250, 236, 200 ), "Dinish-Bold", "Tabakwaren", "Zeitungen · Zeitschriften", None ),
]
SHOPSIGNS_RECTS = { name: ( 8 + 1022 * ( k % 2 ), 8 + 218 * ( k // 2 ), 1018 + 1022 * ( k % 2 ), 210 + 218 * ( k // 2 ) )
                    for k, ( name, *_ ) in enumerate( SHOPSIGNS ) }
FRAME_GREY = ( 132, 134, 136 )


def _smooth( points, steps=10, closed=False ):
    """ A Catmull-Rom curve through points. """
    P = list( points ) + ( list( points[:3] ) if closed else [] )
    if not closed:
        P = [ P[0] ] + P + [ P[-1] ]
    out = []
    for i in range( 1, len( P ) - 2 ):
        p0, p1, p2, p3 = ( np.array( P[j], float ) for j in ( i - 1, i, i + 1, i + 2 ) )
        for t in np.linspace( 0, 1, steps, endpoint=False ):
            out.append( tuple( 0.5 * ( 2 * p1 + ( p2 - p0 ) * t + ( 2 * p0 - 5 * p1 + 4 * p2 - p3 ) * t * t
                                       + ( 3 * p1 - p0 - 3 * p2 + p3 ) * t ** 3 ) ) )
    out.append( tuple( P[-2] ) )
    return out


def _stroke( sh, points, fill, width, layers=None ):
    """ A round-ended line of width px along points, as overlapping dots (PIL's wide polylines notch at short
    segments). """
    step = max( 0.5, 0.2 * width )
    for ( ax_, ay ), ( bx, by ) in zip( points[:-1], points[1:] ):
        k = max( 1, int( math.hypot( bx - ax_, by - ay ) / step ) )
        for t in np.linspace( 0, 1, k, endpoint=False ):
            sh.dot( ax_ + ( bx - ax_ ) * t, ay + ( by - ay ) * t, width / 2, fill, layers )
    sh.dot( points[-1][0], points[-1][1], width / 2, fill, layers )


def _star( cx, cy, r ):
    return [ ( cx + ( r if k % 2 == 0 else 0.4 * r ) * math.sin( k * math.pi / 5 ),
               cy - ( r if k % 2 == 0 else 0.4 * r ) * math.cos( k * math.pi / 5 ) ) for k in range( 10 ) ]


def _icon( sh, kind, cx, cy, s, ink, face, L ):
    """ The shop's emblem in an s px square round ( cx, cy ), in ink on face. """
    P = lambda pts: [ ( cx + px * s, cy + py * s ) for px, py in pts ]
    if kind == "pretzel":                             # the bakers' Brezel: a fat belly, the arms twisted at the top
        path = [ ( -0.3, 0.3 ), ( -0.14, 0.12 ), ( 0.0, -0.04 ), ( 0.16, -0.2 ), ( 0.3, -0.34 ), ( 0.46, -0.24 ),
                 ( 0.48, 0.0 ), ( 0.38, 0.24 ), ( 0.18, 0.38 ), ( 0.0, 0.4 ), ( -0.18, 0.38 ), ( -0.38, 0.24 ),
                 ( -0.48, 0.0 ), ( -0.46, -0.24 ), ( -0.3, -0.34 ), ( -0.16, -0.2 ), ( 0.0, -0.04 ), ( 0.14, 0.12 ),
                 ( 0.3, 0.3 ) ]
        _stroke( sh, P( _smooth( path ) ), ink, 0.09 * s, L )
        _stroke( sh, P( _smooth( path[7:12] ) ), ink, 0.16 * s, L )     # the fat belly
        for end in ( path[0], path[-1] ):
            sh.dot( cx + end[0] * s, cy + end[1] * s, 0.06 * s, ink, L )
    elif kind == "cross":                             # a pharmacy's green cross, white edged
        for grow, colour in ( ( 0.05, ( 255, 255, 255 ) ), ( 0.0, ink ) ):
            a, b = 0.15 + grow, 0.44 + grow
            sh.polygon( P( [ ( -a, -b ), ( a, -b ), ( a, -a ), ( b, -a ), ( b, a ), ( a, a ), ( a, b ), ( -a, b ), ( -a, a ),
                             ( -b, a ), ( -b, -a ), ( -a, -a ) ] ), colour, L )
    elif kind == "plane":
        sh.polygon( P( rotated( [ ( 0.46, 0 ), ( 0.38, -0.05 ), ( 0.06, -0.05 ), ( -0.16, -0.42 ), ( -0.26, -0.42 ),
                                  ( -0.12, -0.05 ), ( -0.34, -0.05 ), ( -0.42, -0.18 ), ( -0.48, -0.18 ), ( -0.44, 0 ),
                                  ( -0.48, 0.18 ), ( -0.42, 0.18 ), ( -0.34, 0.05 ), ( -0.12, 0.05 ), ( -0.26, 0.42 ),
                                  ( -0.16, 0.42 ), ( 0.06, 0.05 ), ( 0.38, 0.05 ) ], -0.5 ) ), ink, L )
    elif kind == "cup":
        sh.polygon( P( [ ( -0.3, -0.12 ), ( 0.22, -0.12 ), ( 0.18, 0.2 ), ( 0.1, 0.28 ), ( -0.18, 0.28 ), ( -0.26, 0.2 ) ] ),
                    ink, L )
        sh.ellipse( ( cx + 0.14 * s, cy - 0.06 * s, cx + 0.38 * s, cy + 0.16 * s ), outline=ink, width=0.06 * s, layers=L )
        sh.rectangle( ( cx - 0.42 * s, cy + 0.32 * s, cx + 0.34 * s, cy + 0.37 * s ), ink, L, radius=0.025 * s )
        for k in range( 3 ):
            x_ = -0.16 + 0.12 * k
            sh.line( P( _smooth( [ ( x_, -0.2 ), ( x_ + 0.04, -0.28 ), ( x_ - 0.03, -0.36 ), ( x_ + 0.02, -0.44 ) ] ) ),
                     ink, 0.035 * s, L )
    elif kind == "scissors":
        for side in ( -1, 1 ):
            sh.ellipse( ( cx - 0.38 * s, cy + side * 0.2 * s - 0.11 * s, cx - 0.16 * s, cy + side * 0.2 * s + 0.11 * s ),
                        outline=ink, width=0.05 * s, layers=L )
            sh.polygon( P( [ ( -0.17, side * 0.15 ), ( 0.46, -side * 0.06 ), ( 0.46, -side * 0.02 ), ( -0.12, side * 0.21 ) ] ),
                        ink, L )
        sh.dot( cx + 0.05 * s, cy, 0.035 * s, face )
    elif kind == "book":
        for side in ( -1, 1 ):
            sh.polygon( P( [ ( 0, -0.22 ), ( side * 0.2, -0.3 ), ( side * 0.46, -0.26 ), ( side * 0.46, 0.26 ),
                             ( side * 0.2, 0.22 ), ( 0, 0.3 ) ] ), ink, L )
            for k in range( 4 ):
                yy = -0.14 + 0.1 * k
                sh.line( P( [ ( side * 0.08, yy ), ( side * 0.38, yy - 0.03 ) ] ), face, 0.02 * s )
    elif kind == "flower":
        sh.line( P( _smooth( [ ( 0, 0.05 ), ( 0.04, 0.25 ), ( 0.0, 0.46 ) ] ) ), ink, 0.05 * s, L )
        sh.polygon( P( [ ( 0.02, 0.3 ), ( 0.22, 0.18 ), ( 0.3, 0.24 ), ( 0.1, 0.34 ) ] ), ink, L )
        for k in range( 5 ):
            a = k * 2 * math.pi / 5
            px, py = 0.15 * math.sin( a ), -0.13 - 0.15 * math.cos( a )
            sh.dot( cx + px * s, cy + py * s, 0.12 * s, ( 236, 120, 150 ), L )
        sh.dot( cx, cy - 0.13 * s, 0.07 * s, ( 252, 210, 60 ), L )
    elif kind == "glasses":
        for side in ( -1, 1 ):
            sh.ellipse( ( cx + side * 0.25 * s - 0.19 * s, cy - 0.15 * s, cx + side * 0.25 * s + 0.19 * s, cy + 0.15 * s ),
                        outline=ink, width=0.055 * s, layers=L )
            sh.line( P( [ ( side * 0.43, -0.04 ), ( side * 0.5, -0.1 ) ] ), ink, 0.05 * s, L )
        sh.line( P( _smooth( [ ( -0.07, -0.02 ), ( 0, -0.07 ), ( 0.07, -0.02 ) ] ) ), ink, 0.05 * s, L )
    elif kind == "shoe":
        sh.polygon( P( _smooth( [ ( -0.44, 0.22 ), ( -0.44, -0.24 ), ( -0.26, -0.24 ), ( -0.2, -0.08 ), ( 0.1, 0.0 ),
                                  ( 0.4, 0.08 ), ( 0.46, 0.2 ), ( 0.44, 0.24 ) ] ) ), ink, L )
        sh.rectangle( ( cx - 0.46 * s, cy + 0.22 * s, cx + 0.46 * s, cy + 0.3 * s ), ink, L, radius=0.03 * s )
    elif kind == "key":
        sh.ellipse( ( cx - 0.46 * s, cy - 0.17 * s, cx - 0.12 * s, cy + 0.17 * s ), outline=ink, width=0.08 * s, layers=L )
        sh.rectangle( ( cx - 0.14 * s, cy - 0.045 * s, cx + 0.46 * s, cy + 0.045 * s ), ink, L )
        for x_, d in ( ( 0.26, 0.18 ), ( 0.38, 0.13 ) ):
            sh.rectangle( ( cx + x_ * s, cy, cx + ( x_ + 0.07 ) * s, cy + d * s ), ink, L )
    elif kind == "bottle":
        for k, dx in enumerate( ( -0.2, 0.0, 0.2 ) ):
            top = -0.42 + 0.06 * ( k % 2 )
            sh.polygon( P( [ ( dx - 0.03, top ), ( dx + 0.03, top ), ( dx + 0.03, top + 0.18 ), ( dx + 0.08, top + 0.3 ),
                             ( dx + 0.08, 0.42 ), ( dx - 0.08, 0.42 ), ( dx - 0.08, top + 0.3 ), ( dx - 0.03, top + 0.18 ) ] ),
                        ink, L )
            sh.rectangle( ( cx + ( dx - 0.08 ) * s, cy + 0.08 * s, cx + ( dx + 0.08 ) * s, cy + 0.22 * s ), face )


def shopsigns( rng, n ):
    """ Backlit shop fascias (rw_shopsigns, 5:1, a 2.5 x 0.5 m sign reads at real size) for the concourse's shops and the
    town's ground floors, every shop made up: a bakery with the bakers' pretzel, a pharmacy's green cross (not the
    German pharmacists' trademark "A"), a snack bar, a travel agency, a hotel, a café, a hairdresser, a kiosk, a
    bookshop, a florist, an optician, a guesthouse with "Zimmer frei", a butcher, a pizzeria, a cobbler, a locksmith,
    a drinks shop and a tobacconist. Each sits in an aluminium frame. Printed lightboxes glow all over (a little brighter
    over the tubes behind); channel letters glow on an unlit panel. Returns the glow as the self-illumination mask. """
    sh = Sheet( n, n, SHOPSIGNS_RECTS, ( 60, 60, 62 ), rough=0.5, height=0.5 )
    for name, style, face, ink, face_font, main, sub, icon in SHOPSIGNS:
        x0, y0, x1, y1 = sh.box( name )
        h = y1 - y0
        f = 0.055 * h                                                  # the frame's width
        sh.rectangle( ( x0, y0, x1, y1 ), FRAME_GREY, { "rough": 0.38, "height": 0.75, "light": 0.0 } )
        sh.rectangle( ( x0 + f * 0.35, y0 + f * 0.35, x1 - f * 0.35, y1 - f * 0.35 ), darken_rgb( FRAME_GREY, 0.8 ) )
        lit_face = 1.0 if style == "box" else 0.0
        sh.rectangle( ( x0 + f, y0 + f, x1 - f, y1 - f ), face,
                      { "rough": 0.3 if style == "box" else 0.55, "height": 0.5, "light": lit_face } )
        L = { "light": 1.0, "height": 0.62 if style == "letters" else 0.5, "rough": 0.3 }
        inner = ( x0 + f, y0 + f, x1 - f, y1 - f )
        ih = inner[3] - inner[1]
        tx0, tx1 = inner[0] + 0.3 * ih, inner[2] - 0.3 * ih
        if icon in ( "pretzel", "cross", "plane", "cup", "scissors", "book", "flower", "glasses", "shoe", "key", "bottle" ):
            s = 0.78 * ih
            _icon( sh, icon, inner[0] + 0.25 * ih + s / 2, ( inner[1] + inner[3] ) / 2, s, ink, face, L )
            tx0 = inner[0] + 0.45 * ih + s
        elif icon == "flag":                                           # an Italian tricolour, lit
            for k, colour in enumerate( ( ( 0, 140, 70 ), ( 250, 250, 248 ), ( 206, 40, 44 ) ) ):
                fx = inner[0] + 0.3 * ih + 0.16 * ih * k
                sh.rectangle( ( fx, inner[1] + 0.25 * ih, fx + 0.16 * ih, inner[3] - 0.25 * ih ), colour, L )
            tx0 = inner[0] + 1.05 * ih
        elif icon == "zimmer":                                         # "Zimmer frei" in its own green box
            zx0 = inner[2] - 2.3 * ih
            sh.rectangle( ( zx0, inner[1] + 0.16 * ih, inner[2] - 0.16 * ih, inner[3] - 0.16 * ih ), ( 0, 112, 62 ), L,
                          radius=0.06 * ih )
            sh.text( ( ( zx0 + inner[2] - 0.16 * ih ) / 2, inner[1] + 0.63 * ih ), "Zimmer frei", "Dinish-Bold", 0.26 * ih,
                     ( 252, 252, 250 ), L, anchor="ms", width=1.8 * ih )
            tx1 = zx0 - 0.25 * ih
        tracking = 0.14 if main.isupper() else 0.0
        if sub:
            sh.text( ( tx0, inner[1] + 0.56 * ih ), main, face_font, 0.36 * ih, ink, L, tracking=tracking,
                     width=tx1 - tx0 )
            sh.text( ( tx0, inner[1] + 0.84 * ih ), sub, "Dinish-Regular", 0.14 * ih, ink, L, width=tx1 - tx0 )
        else:
            centred = icon in ( None, "stars" )
            cap = 0.4 * ih if icon != "stars" else 0.32 * ih
            base = inner[1] + ( 0.7 if icon != "stars" else 0.56 ) * ih
            at = ( ( tx0 + tx1 ) / 2 if centred else tx0, base )
            w = sh.text( at, main, face_font, cap, ink, L, anchor="ms" if centred else "ls", tracking=tracking,
                         width=tx1 - tx0 )
            if icon == "stars":
                for k in range( 3 ):
                    sx = ( tx0 + tx1 ) / 2 + ( k - 1 ) * 0.24 * ih
                    sh.polygon( _star( sx, inner[1] + 0.79 * ih, 0.09 * ih ), ink, L )
    colour, layers = sh.arrays()
    x, y = coords( n )
    light = layers["light"].copy()
    for name, style, *_ in SHOPSIGNS:
        x0, y0, x1, y1 = SHOPSIGNS_RECTS[name]
        sl = ( slice( y0, y1 ), slice( x0, x1 ) )
        v = ( y[sl] - y0 ) / ( y1 - y0 )
        ex = np.minimum( x[sl] - x0, x1 - x[sl] ) / ( y1 - y0 )
        ey = np.minimum( y[sl] - y0, y1 - y[sl] ) / ( y1 - y0 )
        edge = 0.86 + 0.14 * smoothstep( 0.0, 0.3, np.minimum( ex, ey ) )
        if style == "box":                                             # two tubes behind the face
            tubes = 0.92 + 0.08 * np.cos( 2 * math.pi * 2 * ( v - 0.25 ) ) ** 2
            light[sl] *= edge * tubes
        else:
            light[sl] *= edge
    dust = smoothstep( -0.5, 2.5, noise( rng, n, 2.6, 2, 40 ) )
    grime = smoothstep( 0.0, 2.5, streaks( rng, n, 1.6, 2, 60, 60, 2.0 ) )
    colour = darken( colour, 1.0 - 0.05 * dust - 0.06 * grime * ( 1.0 - layers["light"] ) )
    rough = np.clip( layers["rough"] + 0.12 * dust, 0, 1 )
    height = 0.25 * layers["height"] + 0.004 * noise( rng, n, 1.0, n / 6 )
    return { "rw_shopsigns": colour }, rough, height, 8.0, { "illum": light }


def darken_rgb( rgb, factor ):
    return tuple( float( v ) for v in srgb( lin( rgb ) * factor ) )


GRAFFITI_RECTS = {
    "tag_1": ( 8, 8, 968, 328 ), "tag_2": ( 984, 8, 1944, 328 ), "tag_3": ( 8, 344, 1288, 664 ),
    "tag_4": ( 1304, 344, 1944, 664 ), "tag_5": ( 8, 680, 648, 1000 ), "tag_6": ( 664, 680, 1944, 1000 ),
    "tag_7": ( 8, 1016, 808, 1336 ), "tag_8": ( 824, 1016, 1944, 1336 ), "tag_9": ( 8, 1352, 968, 1672 ),
    "tag_10": ( 984, 1352, 1944, 1672 ), "tag_11": ( 8, 1688, 808, 2008 ), "tag_12": ( 824, 1688, 1784, 2008 ),
}
# Every word is made up. kind: "piece" (filled letters, outlined, with a 3D block and a border), "throwup" (fat rounded
# letters, one fill and an outline) or "tag" (a hand style signature in one colour).
GRAFFITI = {
    "tag_1": dict( kind="piece", word="KRYL", face="Dinish-Bold", fill=( ( 252, 214, 40 ), ( 240, 96, 24 ) ),
                   line=( 58, 22, 70 ), block=( 34, 14, 44 ), border=( 248, 248, 244 ), cloud=( 120, 196, 232 ),
                   warp=0.06, shine=True, drips=5, stars=2 ),
    "tag_2": dict( kind="piece", word="VONZA", face="ChakraPetch-Bold", fill=( ( 180, 236, 60 ), ( 30, 150, 70 ) ),
                   line=( 16, 18, 16 ), block=( 18, 60, 30 ), border=( 240, 240, 236 ), split=( 250, 250, 210 ),
                   warp=0.04, shine=True, drips=3, stars=3 ),
    "tag_3": dict( kind="throwup", word="ZEPO", face="Mina-Bold", fill=( ( 236, 238, 240 ), ( 150, 154, 160 ) ),
                   line=( 14, 14, 16 ), warp=0.03, drips=4 ),
    "tag_4": dict( kind="piece", word="MURQ", face="Dinish-Bold", fill=( ( 250, 120, 160 ), ( 200, 24, 50 ) ),
                   line=( 250, 250, 248 ), block=( 90, 10, 24 ), border=( 16, 16, 18 ), bubbles=( 255, 200, 220 ),
                   warp=0.07, shine=False, drips=3, stars=1 ),
    "tag_5": dict( kind="piece", word="OKRU", face="Mina-Bold", fill=( ( 110, 200, 250 ), ( 20, 70, 180 ) ),
                   line=( 250, 210, 40 ), block=( 14, 26, 70 ), border=( 20, 20, 22 ), cloud=( 240, 130, 40 ),
                   warp=0.05, shine=True, drips=2, stars=2 ),
    "tag_6": dict( kind="piece", word="FENZ", face="ChakraPetch-Bold", fill=( ( 220, 90, 230 ), ( 110, 30, 150 ) ),
                   line=( 70, 230, 230 ), block=( 40, 10, 60 ), border=( 12, 12, 14 ), split=( 250, 170, 250 ),
                   warp=0.09, shine=True, drips=4, stars=2 ),
    "tag_7": dict( kind="tag", word="Dyko", face="Dinish-Italic", fill=( ( 16, 16, 18 ), ( 16, 16, 18 ) ), drips=4 ),
    "tag_8": dict( kind="piece", word="TRAZ", face="Dinish-Bold", fill=( ( 90, 220, 200 ), ( 10, 120, 120 ) ),
                   line=( 12, 12, 14 ), block=( 90, 92, 96 ), border=( 246, 246, 240 ), warp=0.05, shine=True, drips=3,
                   stars=1 ),
    "tag_9": dict( kind="tag", word="skeo", face="ChakraPetch-MediumItalic", fill=( ( 200, 30, 36 ), ( 200, 30, 36 ) ),
                   drips=3 ),
    "tag_10": dict( kind="throwup", word="WEMA", face="Mina-Bold", fill=( ( 20, 20, 22 ), ( 40, 40, 44 ) ),
                    line=( 244, 244, 240 ), warp=0.04, drips=2 ),
    "tag_11": dict( kind="tag", word="Nokt", face="ChakraPetch-Italic", fill=( ( 196, 198, 204 ), ( 196, 198, 204 ) ),
                    drips=1 ),
    "tag_12": dict( kind="piece", word="ZURA", face="Mina-Bold", fill=( ( 255, 236, 120 ), ( 250, 150, 20 ) ),
                    line=( 20, 16, 14 ), block=( 120, 40, 10 ), border=( 250, 250, 246 ), bubbles=( 255, 250, 210 ),
                    warp=0.05, shine=True, drips=3, stars=2 ),
}


def _grow( mask, r ):
    """ mask (0..1) grown by r px, anti-aliased. """
    if r <= 0:
        return mask
    return np.maximum( mask, np.clip( r + 0.5 - ndimage.distance_transform_edt( mask < 0.5 ), 0, 1 ) )


def _shifted( mask, dx, dy ):
    return ndimage.shift( mask, ( dy, dx ), order=1, mode="constant" )


def _letters( word, face, W, H, rng, rounded ):
    """ Each letter's mask on a W x H canvas: the word laid out at a jaunty angle, each letter turned, raised or lowered
    and scaled a little and overlapping the last, the whole fitted inside the canvas. """
    cap = 0.36 * H                                            # room round it on the canvas
    f = sized( face, cap )
    advs = [ f.getlength( ch ) for ch in word ]
    overlap = 0.9 if rounded else 0.84
    total = sum( a * overlap for a in advs[:-1] ) + advs[-1]
    scale = min( 1.0, 0.78 * W / total )
    cap *= scale
    f = sized( face, cap )
    advs = [ a * scale for a in advs ]
    total *= scale
    x = ( W - total ) / 2
    masks = []
    for k, ch in enumerate( word ):
        size = int( 2.2 * cap + 8 )
        g = Image.new( "L", ( size, size ), 0 )
        ImageDraw.Draw( g ).text( ( size / 2, size / 2 + cap / 2 ), ch, font=f, fill=255, anchor="ms" )
        g = g.resize( ( int( size * rng.uniform( 0.94, 1.1 ) ), int( size * rng.uniform( 0.96, 1.14 ) ) ), Image.BICUBIC )
        g = g.rotate( rng.uniform( -9, 9 ), resample=Image.BICUBIC, expand=False )
        canvas = Image.new( "L", ( W, H ), 0 )
        cx = x + advs[k] / 2
        cy = H / 2 + rng.uniform( -0.06, 0.06 ) * H
        canvas.paste( g, ( int( cx - g.width / 2 ), int( cy - g.height / 2 ) ) )
        masks.append( np.asarray( canvas, float ) / 255.0 )
        x += advs[k] * overlap
    return masks, cap


def _warped( masks, W, H, amount, rng ):
    """ The letters bent by a smooth displacement field (amount of the height), the same for all of them. """
    if not amount:
        return masks
    yy, xx = np.mgrid[0:H, 0:W].astype( float )
    dx = np.zeros( ( H, W ) )
    dy = np.zeros( ( H, W ) )
    for _ in range( 3 ):
        kx, ky = rng.uniform( 0.5, 2.0, 2 ) * 2 * math.pi
        ph = rng.uniform( 0, 2 * math.pi, 2 )
        dx += amount * H * np.sin( kx * xx / H + ph[0] ) * np.cos( ky * yy / H )
        dy += amount * H * np.sin( ky * yy / H + ph[1] ) * np.cos( kx * xx / H )
    return [ ndimage.map_coordinates( m, ( yy + dy, xx + dx ), order=1, mode="constant" ) for m in masks ]


def _paint( C, A, mask, colour ):
    m = mask[..., None]
    C[:] = C * ( 1 - m ) + np.asarray( colour, float ) * m
    A[:] = np.maximum( A, mask )


def _piece( spec, W, H, rng ):
    """ One piece on a W x H canvas (supersampled): colour and coverage. """
    kind = spec["kind"]
    C = np.zeros( ( H, W, 3 ) )
    A = np.zeros( ( H, W ) )
    yy, xx = np.mgrid[0:H, 0:W].astype( float )
    if kind == "tag":
        return _hand_tag( spec, W, H, rng )
    masks, cap = _letters( spec["word"], spec["face"], W, H, rng, kind == "throwup" )
    masks = _warped( masks, W, H, spec.get( "warp", 0.0 ), rng )
    if kind == "throwup":                                     # fat, rounded letters
        masks = [ _grow( T.blur( m, 0.04 * cap ), 0.09 * cap ) for m in masks ]
    union = np.maximum.reduce( masks )
    o = 0.07 * cap                                            # the outline's width
    outlined = _grow( union, o )
    t = np.clip( ( yy - ( H / 2 - 0.55 * cap ) ) / ( 1.1 * cap ), 0, 1 )   # the fill's gradient, top to bottom
    fill = mix( np.asarray( spec["fill"][0], float ), np.asarray( spec["fill"][1], float ), t )
    if kind == "piece":
        if spec.get( "cloud" ):                               # a cloud of round blobs behind the letters
            img = Image.new( "L", ( W, H ), 0 )
            ys, xs = np.nonzero( union > 0.5 )
            for _ in range( 26 ):
                i = rng.integers( len( xs ) )
                r = rng.uniform( 0.25, 0.45 ) * cap
                ImageDraw.Draw( img ).ellipse( ( xs[i] - r, ys[i] - r, xs[i] + r, ys[i] + r ), fill=255 )
            cloud = np.asarray( img, float ) / 255.0
            cloud = _grow( cloud, 0.08 * cap )
            _paint( C, A, _grow( cloud, 0.04 * cap ), spec["line"] )
            _paint( C, A, cloud, spec["cloud"] )
        d = 0.16 * cap                                        # the 3D block, down and to the right
        block = np.zeros( ( H, W ) )
        steps = int( d )
        for k in range( 1, steps + 1 ):
            block = np.maximum( block, _shifted( outlined, 0.7 * k, k ) ) if k % 2 == 0 or k == steps else block
        border = _grow( np.maximum( outlined, block ), 0.06 * cap )
        _paint( C, A, border, spec["border"] )
        shade = 0.8 + 0.35 * yy / H                           # the block lighter towards its foot
        _paint( C, A, block, np.asarray( spec["block"], float )[None, None, :] * shade[..., None] )
    for m in masks:                                           # each letter outlined over the ones before
        _paint( C, A, _grow( m, o ), spec["line"] )
        letter = np.clip( m, 0, 1 )
        f = fill.copy()
        if spec.get( "split" ):                               # a diagonal band of a second colour
            band = np.abs( ( xx * 0.5 - yy ) % ( 1.2 * cap ) - 0.6 * cap ) < 0.12 * cap
            f = mix( f, np.asarray( spec["split"], float ), T.blur( band.astype( float ), 1.5 ) )
        if spec.get( "bubbles" ):
            img = Image.new( "L", ( W, H ), 0 )
            for _ in range( 40 ):
                bx, by = rng.uniform( 0, W ), rng.uniform( H / 2 - 0.5 * cap, H / 2 + 0.5 * cap )
                r = rng.uniform( 0.03, 0.09 ) * cap
                ImageDraw.Draw( img ).ellipse( ( bx - r, by - r, bx + r, by + r ), fill=255 )
            b = T.blur( np.asarray( img, float ) / 255.0, 0.8 )
            f = mix( f, np.asarray( spec["bubbles"], float ), b * 0.9 )
        _paint( C, A, letter, f if f.ndim == 3 else np.broadcast_to( f, C.shape ) )
        if spec.get( "shine" ):                               # white shines along each letter's top left edge
            edge = np.clip( letter - _shifted( letter, 0.05 * cap, 0.05 * cap ), 0, 1 )
            edge *= ( np.sin( xx / ( 0.3 * cap ) + rng.uniform( 0, 6 ) ) > 0.2 )
            C[:] = mix( C, ( 255, 255, 255 ), np.clip( edge * letter, 0, 1 ) * 0.95 )
    # Drips from the letters' bottoms, in the outline's colour.
    for _ in range( spec.get( "drips", 0 ) ):
        cols = np.nonzero( outlined.max( 0 ) > 0.5 )[0]
        cx_ = cols[rng.integers( len( cols ) )]
        rows = np.nonzero( outlined[:, cx_] > 0.5 )[0]
        y0 = rows.max() - 2
        length = rng.uniform( 0.1, 0.45 ) * cap
        w = rng.uniform( 0.02, 0.035 ) * cap
        drip = np.clip( w - np.abs( xx - cx_ ), 0, 1 ) * ( yy >= y0 ) * ( yy <= y0 + length )
        drip = np.maximum( drip, np.clip( 1.5 * w - np.hypot( xx - cx_, yy - y0 - length ), 0, 1 ) )
        drip = np.minimum( drip, ( yy < H - 4 ).astype( float ) )
        _paint( C, A, drip, spec.get( "line" ) if kind != "throwup" else spec["fill"][1] )
    for _ in range( spec.get( "stars", 0 ) ):                 # sparkles
        cols = np.nonzero( outlined.max( 0 ) > 0.5 )[0]                # on the letters' top edge
        sx = cols[rng.integers( len( cols ) )]
        sy = np.nonzero( outlined[:, sx] > 0.5 )[0].min() + 0.05 * cap
        r = rng.uniform( 0.08, 0.14 ) * cap
        star = np.clip( 1.0 - ( np.abs( xx - sx ) * np.abs( yy - sy ) ) ** 0.5 / ( 0.06 * r ) - np.hypot( xx - sx, yy - sy ) / r,
                        0, 1 )
        _paint( C, A, np.clip( star * 3, 0, 1 ), ( 255, 255, 255 ) )
    return C, A


def _hand_tag( spec, W, H, rng ):
    """ A signature in one colour of spray: the word in an italic face drawn with a stroke, leaned and wobbled, with a
    swoosh under it. """
    face, word = spec["face"], spec["word"]
    cap = 0.42 * H
    f = sized( face, cap )
    width = f.getlength( word )
    scale = min( 1.0, 0.8 * W / width )
    cap *= scale
    f = sized( face, cap )
    img = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( img )
    stroke = max( 1, int( 0.05 * cap ) )
    x0 = ( W - f.getlength( word ) ) / 2
    d.text( ( x0, H * 0.58 ), word, font=f, fill=255, anchor="ls", stroke_width=stroke, stroke_fill=255 )
    pts = [ ( x0 - 0.1 * cap + t * ( f.getlength( word ) + 0.3 * cap ),
              H * 0.7 + 0.12 * cap * math.sin( math.pi * t ) - 0.15 * cap * t ) for t in np.linspace( 0, 1, 40 ) ]
    d.line( pts, fill=255, width=max( 1, int( 0.07 * cap ) ), joint="curve" )
    m = np.asarray( img, float ) / 255.0
    m = _warped( [ m ], W, H, 0.025, rng )[0]
    # Lean it: a shear about the middle.
    yy, xx = np.mgrid[0:H, 0:W].astype( float )
    m = ndimage.map_coordinates( m, ( yy, xx + 0.18 * ( yy - H / 2 ) ), order=1, mode="constant" )
    C = np.zeros( ( H, W, 3 ) ) + np.asarray( spec["fill"][0], float )
    A = np.clip( m, 0, 1 )
    for _ in range( spec.get( "drips", 0 ) ):
        cols = np.nonzero( A.max( 0 ) > 0.5 )[0]
        cx_ = cols[rng.integers( len( cols ) )]
        y0 = np.nonzero( A[:, cx_] > 0.5 )[0].max() - 1
        length = rng.uniform( 0.15, 0.5 ) * cap
        w = 0.025 * cap
        drip = np.clip( w - np.abs( xx - cx_ ), 0, 1 ) * ( yy >= y0 ) * ( yy <= y0 + length )
        drip = np.maximum( drip, np.clip( 1.6 * w - np.hypot( xx - cx_, yy - y0 - length ), 0, 1 ) )
        A = np.maximum( A, np.minimum( drip, ( yy < H - 4 ).astype( float ) ) )
    return C, A


def _fitted( C, A, W, H, margin ):
    """ The painted part of C, A (its bounds) scaled to fit W x H less margin, centred. """
    ys, xs = np.nonzero( A > 0.01 )
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    k = min( ( W - 2 * margin ) / ( x1 - x0 ), ( H - 2 * margin ) / ( y1 - y0 ) )
    w, h = max( 1, int( ( x1 - x0 ) * k ) ), max( 1, int( ( y1 - y0 ) * k ) )
    def scaled( a ):
        return np.asarray( Image.fromarray( a[y0:y1, x0:x1].astype( np.float32 ), "F" ).resize( ( w, h ), Image.BILINEAR ) )
    Cs = np.stack( [ scaled( C[..., c] * A ) for c in range( 3 ) ], -1 )
    As = scaled( A )
    Cs = Cs / np.maximum( As, 1e-6 )[..., None]
    outC = np.zeros( ( H, W, 3 ) )
    outA = np.zeros( ( H, W ) )
    ox, oy = ( W - w ) // 2, ( H - h ) // 2
    outC[oy:oy + h, ox:ox + w] = Cs
    outA[oy:oy + h, ox:ox + w] = np.clip( As, 0, 1 )
    return outC, outA


def _push_pull( colour, weight ):
    """ colour where weight is 1, and elsewhere the nearest colours carried out over it (a mip pyramid of the weighted
    colour, filled from coarse to fine). n must be a power of two. """
    levels = [ ( colour * weight[..., None], weight ) ]
    while levels[-1][1].shape[0] > 1:
        c, w = levels[-1]
        h = c.shape[0] // 2
        levels.append( ( c.reshape( h, 2, h, 2, 3 ).sum( ( 1, 3 ) ), w.reshape( h, 2, h, 2 ).sum( ( 1, 3 ) ) ) )
    out = levels[-1][0] / max( float( levels[-1][1].max() ), 1e-9 )
    for c, w in reversed( levels[:-1] ):
        up = np.repeat( np.repeat( out, 2, 0 ), 2, 1 )
        own = c / np.maximum( w, 1e-9 )[..., None]
        a = np.clip( w, 0, 1 )[..., None]
        out = own * a + up * ( 1 - a )
    return out


def graffiti( rng, n ):
    """ Graffiti for the yard's walls, the wagons and under the bridges (rw_graffiti, alpha-tested): twelve original
    made-up pieces (no real writer's or crew's name): letter pieces with gradient fills, splits and bubbles, outlines,
    a 3D block and a border round them, white shines, sparkles and drips; two chrome and black-and-white throw-ups;
    and three hand style tags. The alpha is the paint's own edge (the overspray haze isn't kept, as alpha testing would
    turn it to noise); round each piece its colours carry on outwards so the mips don't fringe. Spray paint on a wall
    is a little rough and speckled. """
    colour = np.zeros( ( n, n, 3 ) )
    alpha = np.zeros( ( n, n ) )
    for name, ( x0, y0, x1, y1 ) in GRAFFITI_RECTS.items():
        spec = GRAFFITI[name]
        W, H = ( x1 - x0 ) * SS, ( y1 - y0 ) * SS
        # Drawn on a bigger canvas, then fitted into the rect with a margin, so nothing is cut off.
        C, A = _piece( spec, int( 1.4 * W ), int( 1.4 * H ), np.random.default_rng( rng.integers( 1 << 30 ) ) )
        C, A = _fitted( C, A, W, H, 0.05 * H )
        # Spray: the edge roughened a little, the paint speckled.
        speck = rng.normal( 0, 1, ( H, W ) )
        A = np.clip( ( A - 0.5 ) * 1.2 + 0.5 + 0.08 * T.blur( speck, 0.7 ), 0, 1 )
        C = C * ( 1.0 + 0.03 * T.blur( speck, 1.0 ) )[..., None]
        C = ( C * A[..., None] ).reshape( H // SS, SS, W // SS, SS, 3 ).sum( ( 1, 3 ) )
        A = A.reshape( H // SS, SS, W // SS, SS ).mean( ( 1, 3 ) )
        C = C / np.maximum( A * SS * SS, 1e-6 )[..., None]
        colour[y0:y1, x0:x1] = C
        alpha[y0:y1, x0:x1] = A
    # Carry the colours out past the paint's edges (a push-pull fill), so a mip's average isn't dragged to black.
    colour = _push_pull( colour, ( alpha > 0.02 ).astype( float ) )
    rough = np.clip( 0.72 + 0.06 * noise( rng, n, 1.0, n / 6 ), 0, 1 )
    height = 0.002 * noise( rng, n, 1.0, n / 8 )
    return { "rw_graffiti": np.clip( colour, 0, 255 ) }, rough, height, 8.0, { "trans": alpha }




# ---------------------------------------------------------------------------------------------------------------------
# Cast bronze lettering (rw_lettering)

# Every rect is 1 / 0.6 of its capitals' height: the capitals stand from 0.2 to 0.8 of the rect's height (the baseline at
# 0.8 from its top), with room above for an umlaut's dots, and 0.2 of the capitals' height clear either side of the
# word. The capitals are LETTER_CAP px high in every rect but the year's, which is twice that, so the words that go up
# side by side (hohenwald and hbf_word, the two halves of hauptbahnhof inside the shed) have the same letters.
LETTER_CAP = 93
LETTER_FACE = "Dinish-Bold"
LETTER_TRACKING = 0.12                                  # of the cap height, between letters
LETTERING_WORDS = {
    "hauptbahnhof": "HOHENWALD HAUPTBAHNHOF", "hohenwald": "HOHENWALD", "hbf_word": "HAUPTBAHNHOF",
    "gueterabfertigung": "GÜTERABFERTIGUNG", "eingang": "EINGANG", "wartesaal": "WARTESAAL",
    "fahrkarten": "FAHRKARTEN", "abfahrt": "ABFAHRT", "ankunft": "ANKUNFT", "ausgang": "AUSGANG",
    "restaurant": "RESTAURANT", "bahnpost": "BAHNPOST", "gepaeck": "GEPÄCK", "year": "1913",
}
LETTERING_RECTS = {
    "hauptbahnhof": ( 8, 8, 2004, 163 ),
    "hohenwald": ( 8, 171, 879, 326 ), "hbf_word": ( 887, 171, 1998, 326 ),
    "gueterabfertigung": ( 8, 334, 1408, 489 ), "eingang": ( 1416, 334, 2038, 489 ),
    "wartesaal": ( 8, 497, 852, 652 ), "fahrkarten": ( 860, 497, 1780, 652 ),
    "abfahrt": ( 8, 660, 656, 815 ), "ankunft": ( 664, 660, 1322, 815 ), "ausgang": ( 1330, 660, 1999, 815 ),
    "restaurant": ( 8, 823, 915, 978 ), "bahnpost": ( 923, 823, 1664, 978 ),
    "gepaeck": ( 8, 986, 573, 1141 ), "year": ( 581, 986, 1185, 1296 ),
}
LETTER_INCHES = 28.0                                    # the capitals' real height the bevel is drawn for (71 cm)


def _letter_mask( text, W, H, cap ):
    """ The word's capitals at SS times W x H px, 0..1, centred across by their ink, the baseline at 0.8 H. """
    img = Image.new( "L", ( W * SS, H * SS ), 0 )
    f = sized( LETTER_FACE, cap * SS )
    put( ImageDraw.Draw( img ), ( W * SS / 2, 0.8 * H * SS ), text, f, 255, anchor="ms",
         tracking=LETTER_TRACKING * cap * SS )
    m = np.asarray( img, float ) / 255.0
    cols = np.nonzero( m.max( 0 ) > 0.1 )[0]
    shift = int( round( ( W * SS - ( cols[0] + cols[-1] + 1 ) ) / 2 ) )
    return np.roll( m, shift, axis=1 ).reshape( H, SS, W, SS ).mean( ( 1, 3 ) )


def _run_lengths( inside, reverse ):
    """ Per px inside, how many px down the column to its stroke's top edge (or, reversed, its bottom edge). """
    out = np.zeros( inside.shape )
    rows = range( inside.shape[0] - 1, -1, -1 ) if reverse else range( inside.shape[0] )
    last = np.zeros( inside.shape[1] )
    for y in rows:
        last = inside[y] * ( last + 1 )
        out[y] = last
    return out


def lettering( rng, n ):
    """ Cast bronze capitals for the head building's letter band and its doors (rw_lettering, alpha-tested): sand-cast
    letters in a plain grotesque, flat-faced with a rounded bevel 0.08 of their height wide, as station names were cast
    and bolted up from the 1900s. A century outdoors under the cornice has turned them a dark chocolate patina, mottled,
    with black where they're sheltered (the strokes' undersides) and pale green verdigris along their top edges and in
    runs down the faces where rain has washed them. LETTER_INCHES sets the bevel's depth against the letters' size. """
    s = n / 2048.0
    alpha = np.zeros( ( n, n ) )
    capmap = np.full( ( n, n ), LETTER_CAP * s )
    for name, ( x0, y0, x1, y1 ) in LETTERING_RECTS.items():
        X0, Y0, X1, Y1 = ( int( round( v * s ) ) for v in ( x0, y0, x1, y1 ) )
        cap = 0.6 * ( Y1 - Y0 )
        alpha[Y0:Y1, X0:X1] = _letter_mask( LETTERING_WORDS[name], X1 - X0, Y1 - Y0, cap )
        capmap[Y0:Y1, X0:X1] = cap
    inside = alpha > 0.5
    d_in = ndimage.distance_transform_edt( inside )
    d_top = _run_lengths( inside, False )                 # px down from the stroke's top edge
    d_bottom = _run_lengths( inside, True )               # px up from its bottom edge
    k = capmap / ( LETTER_CAP * s )                       # the year's letters are twice the size
    # The bevel and the cast face: the height in inches for letters LETTER_INCHES tall, scaled with the rect's capitals
    # so every word's bevel has the same slope.
    bevel = np.sin( 0.5 * np.pi * np.clip( d_in / ( 0.08 * capmap ), 0, 1 ) )
    grain = noise( rng, n, 0.6, n / 8 )
    height = k * ( 0.55 * bevel + 0.006 * grain * bevel )
    # The patina.
    mottle = noise( rng, n, 1.8, 6, n / 12 )
    fine = noise( rng, n, 1.1, n / 24 )
    runs = streaks( rng, n, 1.5, 6, 260, 40 * s, 0.6 )
    colour = mix( ( 104, 80, 56 ), ( 68, 52, 38 ), smoothstep( -1.4, 1.4, mottle ) )
    colour = darken( colour, 1.0 + 0.04 * fine )
    sheltered = np.exp( -d_bottom / ( 0.07 * capmap ) ) * ( 1 - bevel * 0.4 )
    colour = mix( colour, ( 38, 31, 25 ), 0.6 * sheltered )
    top = np.exp( -d_top / ( 0.05 * capmap ) )
    washed = smoothstep( 0.7, 1.8, runs ) * np.exp( -d_top / ( 0.55 * capmap ) )
    green = np.clip( 0.85 * top * smoothstep( -0.8, 0.8, mottle + 0.4 * fine ) + 0.75 * washed, 0, 1 )
    green *= smoothstep( -1.5, 0.5, noise( rng, n, 1.4, 3, n / 6 ) )        # some letters greener than others
    verdigris = mix( ( 84, 128, 104 ), ( 122, 156, 128 ), smoothstep( -1, 1, fine ) )
    colour = mix( colour, verdigris, green )
    rough = np.clip( 0.5 + 0.05 * mottle + 0.04 * fine + 0.12 * sheltered + 0.26 * green, 0.3, 0.9 )
    # Carry the colours out past the letters' edges so the mips don't fringe.
    colour = _push_pull( colour, ( alpha > 0.02 ).astype( float ) )
    rough = np.where( alpha > 0.02, rough, 0.6 )
    strength = 1024.0 * ( LETTER_CAP / LETTER_INCHES ) / 2048.0
    return { "rw_lettering": np.clip( colour, 0, 255 ) }, rough, height, strength, { "trans": alpha }


# ---------------------------------------------------------------------------------------------------------------------
# The snack machine (rw_vending): its goods' packets, cans and bottle, its touch screen, keys, card reader, pick-up
# flap, the steel panel round its controls and the shelves' label rails. Every brand is made up.

# The goods, by atlas entry: ( kind, brand, flavour, background top, background bottom, brand ink, brand outline,
# picture ). Bags are pillow packs (crimped seals top and bottom); cans' labels wrap round them, their front in the
# middle of the picture; the bottle's label is a band round its middle.
VENDING_GOODS = {
    "snack_solbite": ( "bag", "SolBite", "BBQ WAVE", ( 222, 36, 30 ), ( 150, 14, 16 ), ( 255, 214, 44 ),
                       ( 110, 8, 10 ), "wave_chips" ),
    "snack_cloudos": ( "bag", "Cloudos", "SEA SALT", ( 46, 122, 226 ), ( 18, 62, 160 ), ( 255, 255, 255 ),
                       ( 12, 40, 110 ), "salted_chips" ),
    "snack_zestix": ( "bag", "Zestix", "CHEESE BLAST", ( 250, 132, 24 ), ( 206, 72, 10 ), ( 255, 255, 255 ),
                      ( 120, 36, 6 ), "nachos" ),
    "snack_ridgerun": ( "bag", "RidgeRun", "SOUR CREAM & HERB", ( 44, 160, 64 ), ( 18, 98, 40 ), ( 255, 255, 255 ),
                        ( 10, 62, 24 ), "ridged_chips" ),
    "snack_novabar": ( "bag", "NovaBar", "CARAMEL", ( 124, 52, 186 ), ( 70, 22, 122 ), ( 255, 255, 255 ),
                       ( 40, 10, 76 ), "caramel_bar" ),
    "snack_chunko": ( "bag", "Chunko", "NUT CRUNCH", ( 132, 78, 44 ), ( 78, 40, 20 ), ( 252, 228, 180 ),
                      ( 46, 22, 10 ), "nut_chunks" ),
    "snack_meltz": ( "bag", "Meltz", "MILK CHOC", ( 214, 34, 44 ), ( 140, 14, 26 ), ( 255, 255, 255 ),
                     ( 96, 8, 16 ), "choc_squares" ),
    "snack_frost": ( "bag", "Frost", "COOKIE CREAM", ( 36, 146, 230 ), ( 14, 82, 172 ), ( 255, 255, 255 ),
                     ( 8, 46, 110 ), "cream_cookies" ),
    "snack_crumbly": ( "bag", "Crumbly", "CHOC CHIP", ( 244, 228, 196 ), ( 214, 186, 140 ), ( 120, 64, 30 ),
                       ( 255, 248, 232 ), "chip_cookies" ),
    "snack_jellyjoy": ( "bag", "JellyJoy", "FRUIT GUMS", ( 236, 60, 160 ), ( 170, 22, 112 ), ( 255, 255, 255 ),
                        ( 110, 8, 70 ), "gummies" ),
    "snack_polar": ( "bag", "Polar", "PEPPERMINT MINTS", ( 52, 152, 236 ), ( 18, 92, 194 ), ( 255, 255, 255 ),
                     ( 10, 56, 130 ), "mints" ),
    "snack_knotties": ( "bag", "Knotties", "HONEY PRETZELS", ( 252, 206, 48 ), ( 230, 156, 18 ), ( 176, 44, 22 ),
                        ( 255, 246, 214 ), "pretzels" ),
    "snack_mintle": ( "bag", "Mintle", "FRESH MINT", ( 22, 170, 156 ), ( 8, 108, 108 ), ( 255, 255, 255 ),
                      ( 4, 70, 70 ), "mint_leaves" ),
    "snack_bubblez": ( "bag", "Bubblez", "BUBBLE GUM", ( 246, 120, 186 ), ( 206, 62, 144 ), ( 255, 255, 255 ),
                       ( 132, 20, 92 ), "gum_balls" ),
    "snack_chocobitz": ( "bag", "ChocoBitz", "COOKIE BITES", ( 44, 98, 206 ), ( 20, 52, 142 ), ( 255, 255, 255 ),
                         ( 10, 30, 90 ), "cookie_bites" ),
    "drink_fizzup": ( "can", "FizzUp", "COLA", ( 214, 26, 34 ), ( 150, 12, 20 ), ( 255, 255, 255 ), ( 100, 6, 12 ),
                      "cola" ),
    "drink_citraze": ( "can", "Citraze", "ORANGE", ( 250, 150, 24 ), ( 226, 96, 10 ), ( 255, 255, 255 ),
                       ( 150, 52, 4 ), "orange" ),
    "drink_sparkleaf": ( "can", "SparkLeaf", "LEMON LIME", ( 40, 164, 66 ), ( 16, 104, 42 ), ( 255, 255, 255 ),
                         ( 8, 64, 24 ), "lime" ),
    "drink_groove": ( "can", "Groove", "GRAPE", ( 120, 52, 178 ), ( 68, 22, 118 ), ( 255, 255, 255 ),
                      ( 40, 8, 74 ), "grapes" ),
    "drink_hydro": ( "bottle", "Hydro+", "STILL WATER", ( 250, 252, 255 ), ( 204, 228, 248 ), ( 22, 102, 206 ),
                     None, "water" ),
}
# The bags' sizes in inches ( width, height ), by the row they stand on (A at the top); cans and the bottle are round.
VENDING_BAGS = { "A": ( 5.0, 8.2 ), "B": ( 5.0, 7.2 ), "C": ( 5.0, 7.2 ), "E": ( 5.0, 6.9 ) }
VENDING_ROWS = "ABCDE"
VENDING_COLUMNS = ( 0.14, 0.38, 0.62, 0.86 )            # the slots' centres across the shelves, a share of their width

VENDING_RECTS = {}
_bags = [ name for name, g in VENDING_GOODS.items() if g[0] == "bag" ]
for _k, _name in enumerate( _bags ):
    _row = "ABCE"[min( _k // 4, 3 )]
    _w, _h = VENDING_BAGS[_row]
    _x, _y = 8 + 248 * ( _k % 8 ), 8 + 408 * ( _k // 8 )
    VENDING_RECTS[_name] = ( _x, _y, _x + 240, _y + int( round( 240 * _h / _w ) ) )
for _k, _name in enumerate( name for name, g in VENDING_GOODS.items() if g[0] == "can" ):
    VENDING_RECTS[_name] = ( 8 + 408 * _k, 824, 408 + 408 * _k, 1054 )
VENDING_RECTS.update( {
    "panel": ( 1744, 416, 1920, 1192 ), "screen": ( 8, 1062, 252, 1538 ), "reader": ( 260, 1062, 484, 1278 ),
    "flap": ( 1028, 1062, 1628, 1268 ), "drink_hydro": ( 260, 1286, 682, 1411 ),
    "cavity_side": ( 1448, 1420, 1704, 1932 ),
} )
for _k, _name in enumerate( ( "bottle_plastic", "bottle_cap", "can_lid", "cavity_back" ) ):
    VENDING_RECTS[_name] = ( 690 + 72 * _k, 1286, 754 + 72 * _k, 1350 )
for _k, _name in enumerate( ( "1", "2", "3", "4", "5", "6", "7", "8", "9", "x", "0", "ok" ) ):
    VENDING_RECTS[f"key_{_name}"] = ( 492 + 88 * ( _k % 6 ), 1062 + 88 * ( _k // 6 ), 572 + 88 * ( _k % 6 ),
                                      1142 + 88 * ( _k // 6 ) )
for _k, _row in enumerate( VENDING_ROWS ):
    VENDING_RECTS[f"rail_{_row.lower()}"] = ( 260, 1420 + 58 * _k, 1440, 1474 + 58 * _k )

# Self-illumination (the illum mask) by kind of entry: the machine's LEDs light its goods and shelves from inside.
VENDING_GLOW = { "goods": 0.2, "rail": 0.28, "cavity": 0.32, "screen": 0.9, "symbol": 0.35 }


def _ss_grid( box ):
    """ The px box at SS times its size, and u, v across it (0..1, v down). """
    x0, y0, x1, y1 = ( int( round( v * SS ) ) for v in box )
    v, u = np.mgrid[0:y1 - y0, 0:x1 - x0] + 0.5
    return ( x0, y0, x1, y1 ), u / ( x1 - x0 ), v / ( y1 - y0 )


def _paste_rgb( sh, box, rgb, mask=None ):
    """ An sRGB picture (SS times box's size) into the sheet's colour, over mask (0..1) if given. """
    ( x0, y0, x1, y1 ), _, _ = _ss_grid( box )
    img = Image.fromarray( np.clip( np.rint( rgb ), 0, 255 ).astype( np.uint8 ), "RGB" )
    m = None if mask is None else Image.fromarray( np.clip( np.rint( mask * 255 ), 0, 255 ).astype( np.uint8 ), "L" )
    sh.colour.paste( img, ( x0, y0 ), m )


def _gradient( sh, box, top, bottom, glow=None, glow_at=( 0.5, 0.25 ), glow_r=0.45 ):
    """ box filled from top to bottom, with a soft round glow ( colour ) behind glow_at. """
    _, u, v = _ss_grid( box )
    w = ( box[2] - box[0] ) / ( box[3] - box[1] )
    c = mix( np.array( top, float ), np.array( bottom, float ), smoothstep( 0.0, 1.0, v ) )
    if glow is not None:
        d = np.hypot( ( u - glow_at[0] ) * w, v - glow_at[1] ) / glow_r
        c = mix( c, np.array( glow, float ), 0.85 * np.exp( -2.2 * d * d ) )
    _paste_rgb( sh, box, c )


def _brand( sh, cx, cy, s, face, cap, fill, outline=None, outline_w=0.0, angle=0.0, width=None, shadow=None,
            layers=None ):
    """ s centred on ( cx, cy ), outlined outline_w px, turned angle degrees anticlockwise, straight into the colour
    (and layers, as Sheet.text's). A shadow ( dx, dy, colour ) goes under it. """
    f, cap = fitted( face, s, cap * SS, width * SS ) if width is not None else ( sized( face, cap * SS ), cap * SS )
    sw = int( round( outline_w * SS ) )
    l, t, r, b = f.getbbox( s, anchor="mm", stroke_width=sw )
    pad = sw + 6
    W, H = r - l + 2 * pad, b - t + 2 * pad
    ink = Image.new( "RGBA", ( W, H ), ( 0, 0, 0, 0 ) )
    ImageDraw.Draw( ink ).text( ( pad - l, pad - t ), s, font=f, anchor="mm", fill=tuple( int( v ) for v in fill ) + ( 255, ),
                                stroke_width=sw, stroke_fill=tuple( int( v ) for v in ( outline or fill ) ) + ( 255, ) )
    if angle:
        ink = ink.rotate( angle, resample=Image.BICUBIC, expand=True )
    at = ( int( round( cx * SS - ink.width / 2 ) ), int( round( cy * SS - ink.height / 2 ) ) )
    alpha = ink.getchannel( "A" )
    if shadow is not None:
        dx, dy, colour = shadow
        sh.colour.paste( Image.new( "RGB", ink.size, tuple( int( v ) for v in colour ) ),
                         ( at[0] + int( dx * SS ), at[1] + int( dy * SS ) ), alpha )
    sh.colour.paste( ink.convert( "RGB" ), at, alpha )
    for k, value in ( layers or {} ).items():
        sh.layers[k].paste( Image.new( "L", ink.size, int( round( np.clip( value, 0, 1 ) * 255 ) ) ), at, alpha )


def _blob( cx, cy, rx, ry, angle=0.0, wobble=0.0, rng=None, k=28 ):
    """ An ellipse's outline as points (rx, ry across and along angle, radians), roughened by wobble. """
    out = []
    phase = rng.uniform( 0, 2 * math.pi, 3 ) if rng is not None else ( 0.0, 0.0, 0.0 )
    for j in range( k ):
        t = 2 * math.pi * j / k
        r = 1.0 + wobble * ( 0.5 * math.sin( 3 * t + phase[0] ) + 0.3 * math.sin( 5 * t + phase[1] )
                             + 0.2 * math.sin( 7 * t + phase[2] ) )
        x, y = rx * r * math.cos( t ), ry * r * math.sin( t )
        out.append( ( cx + x * math.cos( angle ) - y * math.sin( angle ), cy + x * math.sin( angle ) + y * math.cos( angle ) ) )
    return out


def _shade( rgb, factor ):
    return darken_rgb( rgb, factor )


def _chip( sh, rng, cx, cy, r, angle, base=( 236, 182, 72 ), wave=False, ridges=False, spice=None ):
    """ A crisp seen at a slant: a golden curl with a darker rim, its waves or ridges, browned spots, and spice. """
    sh.polygon( _blob( cx, cy + 0.06 * r, 1.04 * r, 0.7 * r, angle, 0.08, rng ), _shade( base, 0.45 ) )
    sh.polygon( _blob( cx, cy, r, 0.66 * r, angle, 0.08, rng ), base )
    sh.polygon( _blob( cx - 0.12 * r, cy - 0.1 * r, 0.62 * r, 0.36 * r, angle, 0.1, rng ), _shade( base, 1.25 ) )
    if wave or ridges:
        for j in range( -3, 4 ):
            off = j * 0.24 * r
            pts = []
            for t in np.linspace( -0.85, 0.85, 9 ):
                x = t * r
                y = off * 0.66 + ( 0.07 * r * math.sin( 6 * t ) if wave else 0.0 )
                if ( x / r ) ** 2 + ( y / ( 0.66 * r ) ) ** 2 > 0.8:
                    continue
                pts.append( ( cx + x * math.cos( angle ) - y * math.sin( angle ),
                              cy + x * math.sin( angle ) + y * math.cos( angle ) ) )
            if len( pts ) > 1:
                sh.line( pts, _shade( base, 0.72 ), max( 1.0, 0.07 * r ) )
    for _ in range( 4 ):
        a, d = rng.uniform( 0, 2 * math.pi ), rng.uniform( 0.1, 0.6 ) * r
        sh.dot( cx + d * math.cos( a ), cy + 0.6 * d * math.sin( a ), 0.06 * r, _shade( base, 0.6 ) )
    if spice is not None:
        for _ in range( 14 ):
            a, d = rng.uniform( 0, 2 * math.pi ), rng.uniform( 0.0, 0.75 ) * r
            sh.dot( cx + d * math.cos( a ), cy + 0.6 * d * math.sin( a ), rng.uniform( 0.03, 0.06 ) * r, spice )


def _chocolate( sh, x0, y0, x1, y1, cols, rows, base=( 98, 52, 28 ) ):
    """ A slab of chocolate: squares with lit top edges and shadowed grooves. """
    sh.rectangle( ( x0, y0, x1, y1 ), _shade( base, 0.7 ), radius=0.04 * ( x1 - x0 ) )
    gw, gh = ( x1 - x0 ) / cols, ( y1 - y0 ) / rows
    for i in range( cols ):
        for j in range( rows ):
            a, b = x0 + i * gw, y0 + j * gh
            sh.rectangle( ( a + 0.08 * gw, b + 0.08 * gh, a + 0.92 * gw, b + 0.92 * gh ), base, radius=0.1 * gw )
            sh.rectangle( ( a + 0.2 * gw, b + 0.18 * gh, a + 0.8 * gw, b + 0.72 * gh ), _shade( base, 1.2 ),
                          radius=0.1 * gw )


def _cookie( sh, rng, cx, cy, r, base=( 214, 160, 92 ), chips=( 70, 38, 20 ), count=7 ):
    sh.ellipse( ( cx - r, cy - 0.8 * r + 0.08 * r, cx + r, cy + 0.8 * r + 0.08 * r ), _shade( base, 0.6 ) )
    sh.polygon( _blob( cx, cy, r, 0.8 * r, 0.0, 0.05, rng ), base )
    sh.polygon( _blob( cx - 0.15 * r, cy - 0.15 * r, 0.55 * r, 0.4 * r, 0.0, 0.12, rng ), _shade( base, 1.15 ) )
    for _ in range( count ):
        a, d = rng.uniform( 0, 2 * math.pi ), rng.uniform( 0.0, 0.72 ) * r
        s = rng.uniform( 0.08, 0.14 ) * r
        sh.polygon( _blob( cx + d * math.cos( a ), cy + 0.8 * d * math.sin( a ), s, 0.8 * s, a, 0.2, rng ), chips )


def _sandwich( sh, cx, cy, r, tilt=0.35 ):
    """ A cream sandwich biscuit at a slant: two dark discs with the white filling between. """
    dark, rim = ( 40, 26, 22 ), ( 24, 16, 14 )
    for dy, colour in ( ( 0.3 * r, rim ), ( 0.22 * r, dark ) ):
        sh.ellipse( ( cx - r, cy + dy - tilt * r, cx + r, cy + dy + tilt * r ), colour )
    sh.rectangle( ( cx - 0.96 * r, cy + 0.02 * r, cx + 0.96 * r, cy + 0.16 * r ), ( 246, 244, 236 ) )
    sh.ellipse( ( cx - 0.96 * r, cy + 0.16 * r - tilt * r, cx + 0.96 * r, cy + 0.16 * r + tilt * r ), ( 246, 244, 236 ) )
    sh.ellipse( ( cx - r, cy - tilt * r, cx + r, cy + tilt * r ), dark )
    sh.ellipse( ( cx - 0.72 * r, cy - 0.72 * tilt * r, cx + 0.72 * r, cy + 0.72 * tilt * r ), None,
                outline=( 70, 50, 42 ), width=0.05 * r )
    for k in range( 8 ):
        a = k * math.pi / 4
        sh.dot( cx + 0.45 * r * math.cos( a ), cy + 0.45 * tilt * r * math.sin( a ), 0.05 * r, ( 64, 44, 36 ) )


def _pretzel( sh, cx, cy, s, base=( 150, 78, 26 ) ):
    path = [ ( -0.3, 0.3 ), ( -0.14, 0.12 ), ( 0.0, -0.04 ), ( 0.16, -0.2 ), ( 0.3, -0.34 ), ( 0.46, -0.24 ),
             ( 0.48, 0.0 ), ( 0.38, 0.24 ), ( 0.18, 0.38 ), ( 0.0, 0.4 ), ( -0.18, 0.38 ), ( -0.38, 0.24 ),
             ( -0.48, 0.0 ), ( -0.46, -0.24 ), ( -0.3, -0.34 ), ( -0.16, -0.2 ), ( 0.0, -0.04 ), ( 0.14, 0.12 ),
             ( 0.3, 0.3 ) ]
    P = lambda pts, dy=0.0: [ ( cx + px * s, cy + ( py + dy ) * s ) for px, py in pts ]
    _stroke( sh, P( _smooth( path ), 0.03 ), _shade( base, 0.55 ), 0.15 * s )
    _stroke( sh, P( _smooth( path ) ), base, 0.13 * s )
    _stroke( sh, P( _smooth( path ), -0.02 ), _shade( base, 1.35 ), 0.05 * s )
    for k in range( 0, len( path ), 3 ):
        sh.dot( cx + path[k][0] * s, cy + path[k][1] * s - 0.03 * s, 0.018 * s, ( 250, 250, 246 ) )


def _leaf( sh, cx, cy, s, angle, colour=( 40, 170, 70 ) ):
    pts = [ ( 0.0, -0.5 ), ( 0.22, -0.3 ), ( 0.26, 0.0 ), ( 0.16, 0.3 ), ( 0.0, 0.5 ), ( -0.16, 0.3 ), ( -0.26, 0.0 ),
            ( -0.22, -0.3 ) ]
    sh.polygon( rotated( _smooth( pts, 6, closed=True ), angle, cx, cy, s ), colour )
    sh.line( rotated( [ ( 0.0, -0.45 ), ( 0.0, 0.45 ) ], angle, cx, cy, s ), _shade( colour, 0.6 ), 0.025 * s )
    for t in ( -0.2, 0.0, 0.2 ):
        for side in ( -1, 1 ):
            sh.line( rotated( [ ( 0.0, t ), ( side * 0.16, t - 0.12 ) ], angle, cx, cy, s ), _shade( colour, 0.7 ),
                     0.015 * s )


def _glossy_ball( sh, cx, cy, r, colour ):
    sh.dot( cx + 0.06 * r, cy + 0.08 * r, r, _shade( colour, 0.55 ) )
    sh.dot( cx, cy, 0.96 * r, colour )
    sh.dot( cx - 0.2 * r, cy - 0.2 * r, 0.55 * r, _shade( colour, 1.25 ) )
    sh.dot( cx - 0.35 * r, cy - 0.38 * r, 0.18 * r, ( 255, 255, 255 ) )


def _picture( sh, rng, kind, x0, y0, x1, y1 ):
    """ The packet's picture of what's inside, in the box ( x0, y0, x1, y1 ). """
    w, h = x1 - x0, y1 - y0
    cx, cy = ( x0 + x1 ) / 2, ( y0 + y1 ) / 2
    if kind in ( "wave_chips", "salted_chips", "ridged_chips" ):
        spots = [ ( -0.24, 0.12, 0.3, -0.3 ), ( 0.22, 0.18, 0.28, 0.4 ), ( -0.02, -0.1, 0.3, 0.1 ), ( 0.02, 0.32, 0.26, -0.1 ),
                  ( -0.3, -0.22, 0.2, 0.6 ), ( 0.3, -0.18, 0.2, -0.6 ) ]
        if kind == "ridged_chips":                            # a scoop of the dip, with herbs
            sh.polygon( _blob( cx + 0.2 * w, cy - 0.18 * h, 0.22 * w, 0.14 * w, 0.2, 0.15, rng ), ( 214, 214, 206 ) )
            sh.polygon( _blob( cx + 0.18 * w, cy - 0.2 * h, 0.2 * w, 0.12 * w, 0.2, 0.15, rng ), ( 250, 250, 244 ) )
            for _ in range( 16 ):
                sh.dot( cx + 0.2 * w + rng.uniform( -0.15, 0.15 ) * w, cy - 0.2 * h + rng.uniform( -0.08, 0.08 ) * w,
                        rng.uniform( 0.008, 0.016 ) * w, ( 40, 120, 40 ) )
            spots = spots[:4]
        for dx, dy, r, a in sorted( spots, key=lambda q: q[1] ):
            spice = { "wave_chips": ( 170, 52, 20 ), "salted_chips": ( 250, 250, 250 ),
                      "ridged_chips": ( 60, 130, 50 ) }[kind]
            _chip( sh, rng, cx + dx * w, cy + dy * h, r * w, a, wave=kind == "wave_chips", ridges=kind == "ridged_chips",
                   spice=spice )
    elif kind == "nachos":
        for dx, dy, a in ( ( -0.24, -0.12, 0.4 ), ( 0.2, -0.16, -0.3 ), ( -0.02, 0.0, 1.2 ), ( 0.26, 0.08, 0.9 ),
                           ( -0.28, 0.16, -0.6 ), ( 0.04, 0.26, 0.2 ), ( 0.3, 0.32, -1.0 ), ( -0.18, 0.36, 2.0 ) ):
            tri = rotated( _smooth( [ ( 0.0, -0.2 ), ( 0.18, 0.12 ), ( -0.18, 0.12 ) ], 5, closed=True ), a, cx + dx * w,
                           cy + dy * h, w )
            sh.polygon( [ ( x + 0.015 * w, y + 0.02 * w ) for x, y in tri ], ( 150, 66, 12 ) )
            sh.polygon( tri, ( 250, 166, 40 ) )
            for _ in range( 6 ):
                px, py = tri[rng.integers( len( tri ) )]
                qx, qy = cx + dx * w, cy + dy * h
                t_ = rng.uniform( 0.2, 0.8 )
                sh.dot( qx + ( px - qx ) * t_, qy + ( py - qy ) * t_, 0.01 * w, ( 214, 90, 16 ) )
        sh.polygon( _blob( cx + 0.02 * w, cy - 0.3 * h, 0.22 * w, 0.07 * w, 0.0, 0.25, rng ), ( 255, 196, 40 ) )  # cheese
        for k in range( 3 ):
            sh.polygon( _blob( cx + ( k - 1 ) * 0.12 * w, cy - 0.26 * h, 0.025 * w, 0.06 * w, 0.0, 0.1, rng ),
                        ( 255, 196, 40 ) )
    elif kind in ( "caramel_bar", "nut_chunks", "choc_squares" ):
        if kind == "caramel_bar":
            _chocolate( sh, cx - 0.42 * w, cy - 0.02 * h, cx + 0.12 * w, cy + 0.34 * h, 3, 2 )
            # A broken piece showing the caramel through its middle, a string of it running off.
            bx0, by0, bx1, by1 = cx + 0.02 * w, cy - 0.26 * h, cx + 0.42 * w, cy + 0.06 * h
            sh.rectangle( ( bx0, by0, bx1, by1 ), ( 74, 38, 20 ), radius=0.03 * w )
            sh.rectangle( ( bx0 + 0.02 * w, by0 + 0.1 * ( by1 - by0 ), bx1 - 0.02 * w, by0 + 0.34 * ( by1 - by0 ) ),
                          ( 110, 60, 32 ), radius=0.02 * w )
            sh.rectangle( ( bx0, by0 + 0.45 * ( by1 - by0 ), bx1, by0 + 0.66 * ( by1 - by0 ) ), ( 232, 150, 44 ) )
            sh.rectangle( ( bx0, by0 + 0.45 * ( by1 - by0 ), bx1, by0 + 0.5 * ( by1 - by0 ) ), ( 250, 196, 96 ) )
            sh.polygon( _smooth( [ ( bx0 + 0.05 * w, by0 + 0.6 * ( by1 - by0 ) ), ( bx0 - 0.04 * w, by1 + 0.02 * h ),
                                   ( bx0 - 0.1 * w, cy + 0.0 * h ), ( bx0 - 0.07 * w, by1 + 0.04 * h ),
                                   ( bx0 + 0.02 * w, by0 + 0.7 * ( by1 - by0 ) ) ], 6, closed=True ), ( 232, 150, 44 ) )
        elif kind == "nut_chunks":
            for dx, dy, s in ( ( -0.2, 0.0, 0.3 ), ( 0.18, 0.1, 0.28 ), ( -0.05, 0.28, 0.3 ) ):
                sh.polygon( _blob( cx + dx * w, cy + dy * h + 0.02 * w, s * w, 0.7 * s * w, 0.3, 0.25, rng ), ( 52, 26, 14 ) )
                sh.polygon( _blob( cx + dx * w, cy + dy * h, s * w, 0.7 * s * w, 0.3, 0.25, rng ), ( 104, 56, 30 ) )
                sh.polygon( _blob( cx + dx * w - 0.05 * w, cy + dy * h - 0.05 * w, 0.5 * s * w, 0.3 * s * w, 0.3, 0.3, rng ),
                            ( 130, 74, 40 ) )
            for _ in range( 7 ):
                nx, ny = cx + rng.uniform( -0.35, 0.35 ) * w, cy + rng.uniform( -0.15, 0.35 ) * h
                sh.ellipse( ( nx - 0.06 * w, ny - 0.045 * w, nx + 0.06 * w, ny + 0.045 * w ), ( 200, 150, 90 ) )
                sh.ellipse( ( nx - 0.035 * w, ny - 0.03 * w, nx + 0.02 * w, ny + 0.0 * w ), ( 226, 184, 124 ) )
        else:
            _chocolate( sh, cx - 0.42 * w, cy - 0.12 * h, cx + 0.2 * w, cy + 0.32 * h, 3, 3 )
            tri = [ ( cx + 0.08 * w, cy - 0.22 * h ), ( cx + 0.44 * w, cy - 0.1 * h ), ( cx + 0.3 * w, cy + 0.14 * h ) ]
            sh.polygon( tri, ( 120, 64, 34 ) )
            sh.polygon( _blob( cx - 0.1 * w, cy - 0.28 * h, 0.22 * w, 0.06 * w, -0.1, 0.2, rng ), ( 246, 240, 226 ) )  # milk
    elif kind == "cream_cookies":
        for dx, dy, r in ( ( -0.2, -0.12, 0.26 ), ( 0.2, -0.04, 0.26 ), ( -0.02, 0.22, 0.3 ) ):
            _sandwich( sh, cx + dx * w, cy + dy * h, r * w )
    elif kind == "chip_cookies":
        for dx, dy, r in ( ( -0.22, -0.1, 0.26 ), ( 0.22, -0.02, 0.26 ), ( 0.0, 0.24, 0.3 ) ):
            _cookie( sh, rng, cx + dx * w, cy + dy * h, r * w )
    elif kind == "gummies":
        colours = [ ( 230, 30, 40 ), ( 255, 200, 20 ), ( 60, 190, 60 ), ( 255, 120, 20 ), ( 170, 40, 200 ), ( 230, 30, 40 ),
                    ( 60, 190, 60 ), ( 255, 200, 20 ) ]
        for k, colour in enumerate( colours ):
            gx = cx + ( ( k % 4 ) - 1.5 ) * 0.22 * w + ( 0.06 * w if k // 4 else 0.0 )
            gy = cy + ( -0.1 + 0.26 * ( k // 4 ) ) * h
            body = _blob( gx, gy, 0.1 * w, 0.13 * w, rng.uniform( -0.4, 0.4 ), 0.06, rng )
            sh.polygon( [ ( x + 0.015 * w, y + 0.02 * w ) for x, y in body ], _shade( colour, 0.5 ) )
            sh.polygon( body, colour )
            sh.dot( gx - 0.03 * w, gy - 0.05 * w, 0.025 * w, ( 255, 255, 255 ) )
    elif kind == "mints":
        for k in range( 6 ):
            mx = cx + ( ( k % 3 ) - 1 ) * 0.27 * w + ( 0.1 * w if k // 3 else -0.03 * w )
            my = cy + ( -0.08 + 0.26 * ( k // 3 ) ) * h
            r = 0.12 * w
            sh.ellipse( ( mx - r, my - 0.7 * r + 0.1 * r, mx + r, my + 0.7 * r + 0.1 * r ), ( 150, 190, 220 ) )
            sh.ellipse( ( mx - r, my - 0.7 * r, mx + r, my + 0.7 * r ), ( 248, 250, 252 ) )
            sh.ellipse( ( mx - 0.5 * r, my - 0.35 * r, mx + 0.5 * r, my + 0.35 * r ), None, outline=( 200, 220, 236 ),
                        width=0.08 * r )
        for k in range( 3 ):                                             # a snowflake
            a = k * math.pi / 3
            sh.line( [ ( cx + 0.3 * w + 0.1 * w * math.cos( a ), cy - 0.33 * h + 0.1 * w * math.sin( a ) ),
                       ( cx + 0.3 * w - 0.1 * w * math.cos( a ), cy - 0.33 * h - 0.1 * w * math.sin( a ) ) ],
                     ( 255, 255, 255 ), 0.02 * w )
    elif kind == "pretzels":
        for dx, dy, s in ( ( -0.18, -0.08, 0.42 ), ( 0.2, 0.0, 0.4 ), ( 0.0, 0.26, 0.46 ) ):
            _pretzel( sh, cx + dx * w, cy + dy * h, s * w )
        sh.polygon( _blob( cx + 0.28 * w, cy - 0.3 * h, 0.12 * w, 0.06 * w, 0.0, 0.1, rng ), ( 250, 180, 30 ) )  # honey
    elif kind == "mint_leaves":
        for dx, dy, s, a in ( ( -0.18, -0.02, 0.42, -0.6 ), ( 0.16, 0.04, 0.44, 0.5 ), ( 0.0, 0.26, 0.4, 0.05 ) ):
            _leaf( sh, cx + dx * w, cy + dy * h, s * w, a, ( 60, 200, 90 ) )
        for k in range( 5 ):
            sh.dot( cx + ( k - 2 ) * 0.17 * w, cy - 0.3 * h, 0.035 * w, ( 230, 255, 250 ) )
    elif kind == "gum_balls":
        for dx, dy, r, colour in ( ( -0.22, 0.0, 0.14, ( 255, 150, 200 ) ), ( 0.2, -0.04, 0.13, ( 250, 110, 180 ) ),
                                   ( 0.0, 0.22, 0.15, ( 255, 170, 210 ) ), ( -0.28, 0.3, 0.1, ( 240, 90, 160 ) ),
                                   ( 0.3, 0.28, 0.11, ( 255, 190, 220 ) ) ):
            _glossy_ball( sh, cx + dx * w, cy + dy * h, r * w, colour )
        sh.ellipse( ( cx - 0.12 * w, cy - 0.42 * h, cx + 0.32 * w, cy - 0.12 * h ), ( 255, 196, 226 ),
                    outline=( 255, 255, 255 ), width=0.015 * w )            # a bubble
    elif kind == "cookie_bites":
        for k in range( 7 ):
            bx = cx + ( ( k % 4 ) - 1.5 ) * 0.22 * w + ( 0.1 * w if k >= 4 else 0.0 )
            by = cy + ( -0.06 + 0.26 * ( k // 4 ) ) * h
            _cookie( sh, rng, bx, by, 0.11 * w, base=( 150, 90, 46 ), chips=( 40, 20, 10 ), count=4 )


def _fruit( sh, rng, kind, cx, cy, s ):
    """ A can's fruit, s px across, round ( cx, cy ). """
    if kind == "cola":
        for dx, dy in ( ( -0.18, 0.08 ), ( 0.16, 0.12 ) ):
            sh.line( _smooth( [ ( cx + dx * s, cy + dy * s ), ( cx + 0.02 * s, cy - 0.2 * s ), ( cx + 0.08 * s, cy - 0.32 * s ) ] ),
                     ( 70, 110, 30 ), 0.03 * s )
            _glossy_ball( sh, cx + dx * s, cy + dy * s + 0.1 * s, 0.17 * s, ( 170, 10, 30 ) )
        for _ in range( 12 ):
            bx, by = cx + rng.uniform( -0.5, 0.5 ) * s, cy + rng.uniform( -0.4, 0.5 ) * s
            r = rng.uniform( 0.02, 0.05 ) * s
            sh.ellipse( ( bx - r, by - r, bx + r, by + r ), None, outline=( 255, 210, 210 ), width=0.012 * s )
    elif kind in ( "orange", "lime" ):
        peel, flesh, pith = ( ( 240, 120, 10 ), ( 255, 170, 40 ), ( 255, 236, 190 ) ) if kind == "orange" else \
            ( ( 40, 140, 30 ), ( 170, 220, 60 ), ( 236, 250, 200 ) )
        if kind == "lime":
            _leaf( sh, cx + 0.28 * s, cy - 0.2 * s, 0.5 * s, 0.9, ( 30, 120, 40 ) )
        r = 0.36 * s
        sh.dot( cx, cy, r, peel )
        sh.dot( cx, cy, 0.9 * r, pith )
        sh.dot( cx, cy, 0.82 * r, flesh )
        for k in range( 10 ):
            a = k * 2 * math.pi / 10
            sh.line( [ ( cx, cy ), ( cx + 0.82 * r * math.cos( a ), cy + 0.82 * r * math.sin( a ) ) ], pith, 0.04 * r )
        sh.dot( cx, cy, 0.1 * r, pith )
    elif kind == "grapes":
        sh.line( [ ( cx, cy - 0.42 * s ), ( cx + 0.06 * s, cy - 0.3 * s ) ], ( 90, 70, 30 ), 0.03 * s )
        _leaf( sh, cx + 0.16 * s, cy - 0.34 * s, 0.34 * s, 1.2, ( 60, 150, 50 ) )
        for row, count in enumerate( ( 4, 3, 2, 1 ) ):
            for k in range( count ):
                gx = cx + ( k - ( count - 1 ) / 2 ) * 0.17 * s
                gy = cy - 0.2 * s + row * 0.15 * s
                _glossy_ball( sh, gx, gy, 0.09 * s, ( 130, 50, 170 ) )


def _bag( sh, rng, name ):
    """ A pillow pack's front: crimped seals at both ends, the brand big over a soft glow, the flavour on a ribbon and
    the picture of what's inside. """
    kind, brand, flavour, top, bottom, ink, outline, picture = VENDING_GOODS[name]
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    seal = 0.065 * h
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), top, { "rough": 0.3, "light": VENDING_GLOW["goods"] } )
    glow = tuple( min( 255, c * 1.25 + 30 ) for c in top )
    _gradient( sh, ( x0, y0, x1, y1 ), top, bottom, glow, ( 0.5, 0.25 ), 0.32 )
    for y_, s in ( ( y0, 1 ), ( y1 - seal, -1 ) ):                  # the seals: crimped ridges
        sh.rectangle( ( x0, y_, x1, y_ + seal ), _shade( top, 0.9 ) )
        for k in range( int( w / 6 ) ):
            sx = x0 + 3 + 6 * k
            sh.rectangle( ( sx, y_ + 2, sx + 2.4, y_ + seal - 2 ), _shade( top, 1.18 ), { "height": 0.8 } )
        sh.rectangle( ( x0, y_ + ( seal - 3 if s > 0 else 0 ), x1, y_ + ( seal if s > 0 else 3 ) ), _shade( top, 0.7 ) )
    face = "Mina-Bold" if len( brand ) <= 7 else "ChakraPetch-BoldItalic"
    _brand( sh, x0 + 0.5 * w, y0 + 0.24 * h, brand, face, 0.17 * w, ink, outline, 0.025 * w, angle=7.0, width=0.86 * w,
            shadow=( 0.012 * w, 0.02 * w, _shade( bottom, 0.5 ) ) )
    rb = y0 + 0.335 * h
    tw = sh.measure( flavour, "Dinish-Bold", 0.05 * w, 0.08 )
    rw_ = min( 0.86 * w, tw + 0.12 * w )
    sh.rectangle( ( x0 + 0.5 * w - rw_ / 2, rb, x0 + 0.5 * w + rw_ / 2, rb + 0.085 * w ), _shade( bottom, 0.6 ),
                  radius=0.02 * w )
    sh.text( ( x0 + 0.5 * w, rb + 0.066 * w ), flavour, "Dinish-Bold", 0.05 * w, ( 255, 255, 255 ), anchor="ms",
             tracking=0.08, width=0.8 * w )
    _picture( sh, rng, picture, x0 + 0.04 * w, y0 + 0.43 * h, x1 - 0.04 * w, y1 - seal - 0.02 * h )
    sh.text( ( x1 - 0.06 * w, y1 - seal - 0.012 * h ), "80 g", "Dinish-Regular", 0.032 * w, ( 255, 255, 255 ), anchor="rs" )


def _can_label( sh, rng, name ):
    """ A can's printed wrap: its front (the brand, the flavour and the fruit) in the middle, a band of colour round
    the back with the brand small, 500 ml. """
    kind, brand, flavour, top, bottom, ink, outline, picture = VENDING_GOODS[name]
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), top, { "rough": 0.24, "light": VENDING_GLOW["goods"] } )
    glow = tuple( min( 255, c * 1.3 + 30 ) for c in top )
    _gradient( sh, ( x0, y0, x1, y1 ), top, bottom, glow, ( 0.5, 0.3 ), 0.4 )
    cx = x0 + 0.5 * w
    for k in range( 3 ):                                          # swooshes round the can
        yy = y0 + ( 0.7 + 0.07 * k ) * h
        pts = [ ( x0 + t * w, yy + 0.05 * h * math.sin( 2 * math.pi * 2 * t + k ) ) for t in np.linspace( 0, 1, 40 ) ]
        sh.line( pts, _shade( top, 1.3 + 0.1 * k ), 0.012 * h )
    long_name = len( brand ) > 7
    _brand( sh, cx, y0 + 0.26 * h, brand, "ChakraPetch-BoldItalic" if long_name else "Mina-Bold", 0.2 * h, ink, outline,
            0.012 * w, angle=8.0, width=( 0.3 if long_name else 0.34 ) * w,
            shadow=( 0.004 * w, 0.012 * h, _shade( bottom, 0.45 ) ) )
    sh.text( ( cx, y0 + 0.46 * h ), flavour, "Dinish-Bold", 0.065 * h, ( 255, 255, 255 ), anchor="ms", tracking=0.1,
             width=0.3 * w )
    _fruit( sh, rng, picture, cx, y0 + 0.71 * h, 0.5 * h )
    for bx in ( x0 + 0.04 * w, x1 - 0.04 * w ):                  # the back
        sh.text( ( bx, y0 + 0.5 * h ), brand, "Mina-Bold", 0.07 * h, ink, anchor="ls" if bx < cx else "rs" )
    sh.text( ( x0 + 0.28 * w, y1 - 0.06 * h ), "500 ml", "Dinish-Regular", 0.045 * h, ( 255, 255, 255 ), anchor="ms" )


def _bottle_label( sh, name ):
    """ The water's label, a band round the bottle: the brand over a drop on its front, waves round its foot. """
    kind, brand, flavour, top, bottom, ink, outline, picture = VENDING_GOODS[name]
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), top, { "rough": 0.3, "light": VENDING_GLOW["goods"] } )
    _gradient( sh, ( x0, y0, x1, y1 ), top, bottom )
    for k in range( 2 ):
        yy = y0 + ( 0.8 + 0.1 * k ) * h
        sh.line( [ ( x0 + t * w, yy + 0.04 * h * math.sin( 2 * math.pi * 4 * t + k ) ) for t in np.linspace( 0, 1, 60 ) ],
                 ( 120, 180, 236 ) if k else ( 60, 140, 220 ), 0.05 * h )
    cx = x0 + 0.5 * w
    _brand( sh, cx, y0 + 0.3 * h, brand, "Mina-Bold", 0.26 * h, ink, ( 255, 255, 255 ), 0.01 * h, width=0.24 * w )
    sh.text( ( cx, y0 + 0.53 * h ), "NATURAL MINERAL WATER", "Dinish-Bold", 0.06 * h, ( 40, 90, 160 ), anchor="ms",
             width=0.22 * w )
    drop = [ ( 0.0, -0.5 ), ( 0.24, -0.08 ), ( 0.3, 0.14 ), ( 0.2, 0.36 ), ( 0.0, 0.46 ), ( -0.2, 0.36 ), ( -0.3, 0.14 ),
             ( -0.24, -0.08 ) ]
    sh.polygon( rotated( _smooth( drop, 6, closed=True ), 0.0, cx, y0 + 0.67 * h, 0.2 * h ), ( 40, 140, 230 ) )
    for bx in ( x0 + 0.12 * w, x1 - 0.12 * w ):                  # the back: the brand small, 0,5 L
        sh.text( ( bx, y0 + 0.45 * h ), brand, "Mina-Bold", 0.14 * h, ink, anchor="ms" )
        sh.text( ( bx, y0 + 0.62 * h ), "0,5 L", "Dinish-Bold", 0.08 * h, ( 40, 90, 160 ), anchor="ms" )


def _hand( sh, cx, cy, s, ink, L ):
    """ A hand tapping with its forefinger, in outline, s px tall: the touch screens' "tap here". """
    finger = [ ( -0.07, 0.05 ), ( -0.07, -0.38 ), ( -0.06, -0.43 ), ( 0.0, -0.46 ), ( 0.06, -0.43 ), ( 0.07, -0.38 ),
               ( 0.07, -0.04 ) ]
    knuckles = [ ( 0.07, -0.04 ), ( 0.08, -0.1 ), ( 0.13, -0.12 ), ( 0.18, -0.1 ), ( 0.19, -0.03 ), ( 0.2, -0.08 ),
                 ( 0.25, -0.09 ), ( 0.3, -0.06 ), ( 0.31, 0.0 ), ( 0.32, -0.03 ), ( 0.36, -0.03 ), ( 0.4, 0.0 ),
                 ( 0.41, 0.06 ), ( 0.4, 0.22 ), ( 0.34, 0.36 ), ( 0.26, 0.44 ), ( 0.26, 0.5 ) ]
    palm = [ ( -0.12, 0.5 ), ( -0.12, 0.44 ), ( -0.22, 0.34 ), ( -0.32, 0.2 ), ( -0.36, 0.1 ), ( -0.34, 0.05 ),
             ( -0.28, 0.06 ), ( -0.2, 0.14 ), ( -0.07, 0.24 ), ( -0.07, 0.05 ) ]
    outline = finger + knuckles[1:] + [ ( 0.26, 0.5 ) ] + palm
    pts = [ ( cx + x * s, cy + y * s ) for x, y in outline ]
    sh.line( pts + pts[:1], ink, 0.035 * s, L )
    for x_ in ( 0.13, 0.25 ):                                     # the curled fingers' tips
        sh.line( [ ( cx + x_ * s, cy - 0.08 * s ), ( cx + x_ * s, cy + 0.02 * s ) ], ink, 0.025 * s, L )
    sh.line( [ ( cx - 0.12 * s, cy + 0.5 * s ), ( cx + 0.26 * s, cy + 0.5 * s ) ], ink, 0.035 * s, L )
    for k, r in enumerate( ( 0.12, 0.2 ) ):                      # the tap's ripples round the fingertip
        box = ( cx - r * s, cy - 0.46 * s - r * s, cx + r * s, cy - 0.46 * s + r * s )
        for d, f in sh._each( ink, L ):
            d.arc( tuple( v * SS for v in box ), 200, 340, fill=f, width=max( 1, int( 0.025 * s * SS ) ) )


def _screen( sh ):
    x0, y0, x1, y1 = sh.box( "screen" )
    w, h = x1 - x0, y1 - y0
    L = { "light": VENDING_GLOW["screen"] }
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), ( 12, 16, 26 ), { "rough": 0.08, "light": VENDING_GLOW["screen"] } )
    _gradient( sh, ( x0, y0, x1, y1 ), ( 18, 26, 44 ), ( 8, 10, 18 ), ( 28, 40, 66 ), ( 0.5, 0.45 ), 0.5 )
    white = ( 244, 246, 250 )
    sh.text( ( x0 + 0.5 * w, y0 + 0.2 * h ), "SELECT", "Dinish-Bold", 0.062 * h, white, L, anchor="ms", tracking=0.06 )
    sh.text( ( x0 + 0.5 * w, y0 + 0.3 * h ), "YOUR ITEM", "Dinish-Bold", 0.062 * h, white, L, anchor="ms", tracking=0.06,
             width=0.86 * w )
    _hand( sh, x0 + 0.5 * w, y0 + 0.62 * h, 0.4 * h, white, L )


def _key( sh, name, label ):
    x0, y0, x1, y1 = sh.box( name )
    s = x1 - x0
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), ( 30, 31, 34 ), { "rough": 0.45, "light": 0.0, "height": 0.5 } )
    sh.rectangle( ( x0, y0, x1, y1 ), ( 70, 72, 78 ), radius=0.12 * s )
    sh.rectangle( ( x0 + 0.06 * s, y0 + 0.1 * s, x1 - 0.04 * s, y1 - 0.02 * s ), ( 22, 23, 26 ), radius=0.1 * s )
    sh.rectangle( ( x0 + 0.06 * s, y0 + 0.06 * s, x1 - 0.06 * s, y1 - 0.08 * s ), ( 44, 46, 50 ), radius=0.1 * s )
    cx, cy = ( x0 + x1 ) / 2, ( y0 + y1 ) / 2 - 0.01 * s
    if label == "x":
        for a in ( 1, -1 ):
            sh.line( [ ( cx - 0.2 * s, cy - a * 0.2 * s ), ( cx + 0.2 * s, cy + a * 0.2 * s ) ], ( 236, 44, 44 ), 0.09 * s )
    elif label == "ok":
        sh.line( [ ( cx - 0.22 * s, cy + 0.0 * s ), ( cx - 0.06 * s, cy + 0.17 * s ), ( cx + 0.24 * s, cy - 0.19 * s ) ],
                 ( 70, 200, 90 ), 0.09 * s )
    else:
        sh.text( ( cx, cy + 0.2 * s ), label, "Dinish-Bold", 0.42 * s, ( 246, 246, 246 ), anchor="ms" )


def _reader( sh ):
    x0, y0, x1, y1 = sh.box( "reader" )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), ( 14, 14, 16 ), { "rough": 0.35, "light": 0.0 } )
    sh.rectangle( ( x0, y0, x1, y1 ), ( 28, 29, 32 ), radius=0.08 * w )
    sh.rectangle( ( x0 + 0.05 * w, y0 + 0.05 * h, x1 - 0.05 * w, y1 - 0.05 * h ), ( 16, 16, 18 ), radius=0.06 * w )
    cx, cy = x0 + 0.5 * w, y0 + 0.6 * h
    grey = ( 176, 180, 186 )
    L = { "light": VENDING_GLOW["symbol"] }
    sh.dot( cx, cy, 0.035 * w, grey, L )
    for r in ( 0.13, 0.22 ):
        box = tuple( v * SS for v in ( cx - r * w, cy - r * w, cx + r * w, cy + r * w ) )
        for start, end in ( ( -50, 50 ), ( 130, 230 ) ):
            for d, f in sh._each( grey, L ):
                d.arc( box, start, end, fill=f, width=max( 1, int( 0.03 * w * SS ) ) )


def _flap( sh ):
    x0, y0, x1, y1 = sh.box( "flap" )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), ( 34, 35, 38 ), { "rough": 0.42, "light": 0.0 } )
    _gradient( sh, ( x0, y0, x1, y1 ), ( 24, 25, 28 ), ( 44, 46, 50 ) )
    sh.text( ( x0 + 0.5 * w, y0 + 0.6 * h ), "PUSH", "Dinish-Bold", 0.2 * h, ( 96, 98, 104 ), { "height": 0.65 },
             anchor="ms", tracking=0.35 )


def _rail( sh, row ):
    """ A shelf's front: a dark label strip under a bright metal edge, each slot's code in white under its slot. """
    name = f"rail_{row.lower()}"
    x0, y0, x1, y1 = sh.box( name )
    w, h = x1 - x0, y1 - y0
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), ( 34, 36, 40 ), { "light": 0.05, "rough": 0.4 } )
    sh.rectangle( ( x0, y0, x1, y0 + 0.16 * h ), ( 214, 218, 224 ), { "light": VENDING_GLOW["rail"] } )
    sh.rectangle( ( x0, y0 + 0.16 * h, x1, y0 + 0.22 * h ), ( 110, 114, 120 ) )
    sh.rectangle( ( x0, y1 - 0.1 * h, x1, y1 ), ( 70, 72, 78 ) )
    for k, share in enumerate( VENDING_COLUMNS ):
        sh.text( ( x0 + share * w, y0 + 0.86 * h ), f"{row}{k + 1}", "Dinish-Bold", 0.56 * h, ( 244, 246, 248 ),
                 { "light": 0.5 }, anchor="ms" )


def vending_missing( out=OUT_DIR ):
    """ Whether any of the snack machine's pictures isn't there. They aren't in the repository (the session that drew
    them couldn't upload to its LFS store), so railhead_map draws them then. """
    names = ( "rw_vending_color", "vending_normal", "vending_rough", "vending_illum" )
    return any( not ( Path( out ) / f"{name}.png" ).exists() for name in names )


def vending( rng, n ):
    """ The snack machine (rw_vending): the goods' packets, cans and bottle in their makers' colours (all made up),
    the touch screen's "select your item" page, the keypad's keys, the card reader's face, the pick-up flap, the
    brushed steel panel round the controls, the shelves' label rails and the lit cavity's walls. The goods, rails and
    cavity glow a little (the machine's LEDs light them from inside), the screen fully. """
    sh = Sheet( n, n, VENDING_RECTS, ( 20, 21, 24 ), rough=0.4, height=0.5, light=0.0 )
    for name, ( kind, *_ ) in VENDING_GOODS.items():
        if kind == "bag":
            _bag( sh, rng, name )
        elif kind == "can":
            _can_label( sh, rng, name )
        else:
            _bottle_label( sh, name )
    _screen( sh )
    for key in ( "1", "2", "3", "4", "5", "6", "7", "8", "9", "x", "0", "ok" ):
        _key( sh, f"key_{key}", key )
    _reader( sh )
    _flap( sh )
    for row in VENDING_ROWS:
        _rail( sh, row )
    for name, colour, rough, light in ( ( "bottle_plastic", ( 214, 230, 244 ), 0.15, VENDING_GLOW["goods"] ),
                                        ( "bottle_cap", ( 26, 104, 214 ), 0.35, VENDING_GLOW["goods"] ),
                                        ( "can_lid", ( 196, 198, 202 ), 0.3, VENDING_GLOW["goods"] ),
                                        ( "cavity_back", ( 26, 27, 30 ), 0.5, 0.06 ) ):
        x0, y0, x1, y1 = sh.box( name )
        sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), colour, { "rough": rough, "light": light } )
    x0, y0, x1, y1 = sh.box( "cavity_side" )                       # lit from the LED strip along its top
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), ( 120, 124, 130 ), { "rough": 0.35, "light": VENDING_GLOW["cavity"] } )
    _gradient( sh, ( x0, y0, x1, y1 ), ( 196, 200, 208 ), ( 58, 60, 66 ) )
    x0, y0, x1, y1 = sh.box( "panel" )                             # brushed stainless, satin
    sh.rectangle( ( x0 - 4, y0 - 4, x1 + 4, y1 + 4 ), ( 150, 153, 158 ), { "rough": 0.32, "light": 0.0 } )
    _, u, v = _ss_grid( ( x0, y0, x1, y1 ) )
    hx, hy = u.shape[1], u.shape[0]
    brush = np.cumsum( rng.standard_normal( ( 1, hx ) ), axis=1 )
    brush = ( brush - brush.mean() ) / ( brush.std() + 1e-9 )
    fine = rng.standard_normal( ( 1, hx ) )
    sheen = 1.0 + 0.12 * np.exp( -( ( u - 0.32 ) / 0.22 ) ** 2 ) * ( 1.0 - 0.5 * v ) - 0.08 * v
    lum = sheen * ( 1.0 + 0.025 * brush + 0.02 * fine ) + 0.006 * rng.standard_normal( ( hy, hx ) )
    _paste_rgb( sh, ( x0, y0, x1, y1 ), lum_paint( ( 152, 155, 160 ), lum ) )
    colour, layers = sh.arrays()
    # The packets' foil: darker towards their crimped edges, a soft gloss down one side and fine crinkles.
    x, y = coords( n )
    shade = np.ones( ( n, n ) )
    gloss = np.zeros( ( n, n ) )
    crinkle = noise( rng, n, 1.2, n / 16, n / 3 )
    for name, ( kind, *_ ) in VENDING_GOODS.items():
        if kind != "bag":
            continue
        x0, y0, x1, y1 = VENDING_RECTS[name]
        sl = ( slice( y0, y1 ), slice( x0, x1 ) )
        u = ( x[sl] - x0 ) / ( x1 - x0 )
        v = ( y[sl] - y0 ) / ( y1 - y0 )
        body = smoothstep( 0.05, 0.1, v ) * smoothstep( 0.95, 0.9, v )
        shade[sl] = ( 0.78 + 0.22 * np.sin( math.pi * u ) ** 0.6 ) * ( 1.0 + 0.04 * crinkle[sl] * body )
        gloss[sl] = 0.1 * np.exp( -( ( u - 0.3 ) / 0.1 ) ** 2 ) * body * ( 1.0 - 0.4 * v )
    colour = srgb( lin( colour ) * shade[..., None] + gloss[..., None] )
    rough = np.clip( layers["rough"] - 0.15 * gloss, 0, 1 )
    height = 0.03 * ( layers["height"] - 0.5 )
    return { "rw_vending": colour }, rough, height, 24.0, { "illum": layers["light"] }


# ---------------------------------------------------------------------------------------------------------------------
# Tables

# name: ( draw, size, seed, metalness, tile units ). The atlases, the clock and the lattice are placed by explicit UVs
# (rect_uv(), the clock's 0..1, the lattice's one panel per 1.0 of u), so their tile units are 1.
TEXTURES = {
    "paving": ( paving, 2048, 1, 0.0, PAVING_TILE ),
    "tactile": ( tactile, 1024, 2, 0.0, 24.0 ),
    "tactile_dots": ( tactile_dots, 1024, 3, 0.0, 24.0 ),
    "coping": ( coping, 1024, 4, 0.0, 39.37 ),
    "lines": ( lines, 512, 5, 0.0, 32.0 ),
    "ballast": ( ballast, 2048, 6, 0.0, 160.0 ),
    "sleeper": ( sleeper, 1024, 7, 0.0, 48.0 ),
    "sleeper_wood": ( sleeper_wood, 1024, 8, 0.0, 48.0 ),
    "rail": ( rail, 512, 9, 0.1, 32.0 ),
    "rail_head": ( rail_head, 512, 10, 1.0, 32.0 ),
    "asphalt": ( asphalt, 2048, 11, 0.0, 192.0 ),
    "kerb": ( kerb, 1024, 12, 0.0, KERB_TILE ),
    "setts": ( setts, 2048, 41, 0.0, SETTS_TILE ),
    "concrete": ( concrete, 2048, 13, 0.0, 256.0 ),
    "terrazzo": ( terrazzo, 4096, 14, 0.0, 192.0 ),
    "sandstone": ( ashlar, 4096, 15, 0.0, SANDSTONE_TILE ),
    "dressed": ( dressed, 2048, 16, 0.0, 96.0 ),
    "steel": ( steel, 2048, 17, 0.0, STEEL_TILE ),
    "steel_modern": ( steel_modern, 2048, 18, 0.0, STEEL_MODERN_TILE ),
    "lattice": ( lattice, 1024, 19, 0.0, 1.0 ),
    "window_dark": ( window_dark, 512, 20, 0.0, 96.0 ),
    "glass_roof": ( glass_roof, 2048, 21, 0.0, GLASS_ROOF_TILE ),
    "train": ( train, 1024, 22, 0.0, 96.0 ),
    "bogie": ( bogie, 1024, 23, 0.05, 64.0 ),
    "rubber": ( rubber, 512, 24, 0.0, 32.0 ),
    "wagon": ( wagon, 1024, 25, 0.0, 96.0 ),
    "container": ( container, 1024, 26, 0.0, 48.0 ),
    "plain": ( plain, 512, 27, 0.0, 64.0 ),
    "lamps": ( lamps, 256, 28, 0.0, 32.0 ),
    "wood": ( wood, 1024, 29, 0.0, 32.0 ),
    "facade": ( facade, 2048, 30, 0.0, 276.0 ),
    "clock": ( clock, 1024, 31, 0.0, 1.0 ),
    "signs": ( signs, 2048, 32, 0.0, 1.0 ),
    "displays": ( displays, 2048, 33, 0.0, 1.0 ),
    "posters": ( posters, 2048, 34, 0.0, 1.0 ),
    "shopsigns": ( shopsigns, 2048, 35, 0.0, 1.0 ),
    "graffiti": ( graffiti, 2048, 36, 0.0, 1.0 ),
    "lettering": ( lettering, 2048, 37, 0.5, 1.0 ),
    "vending": ( vending, 2048, 38, 0.0, 1.0 ),
}

# The paints each texture draws, so paints() needn't run them (write_texture checks them).
TEXTURE_PAINTS = {
    "paving": [ "rw_paving", "rw_paving_warm", "rw_paving_dark" ], "tactile": [ "rw_tactile" ],
    "tactile_dots": [ "rw_tactile_dots" ], "coping": [ "rw_coping" ],
    "lines": [ "rw_line_white", "rw_line_yellow", "rw_hazard" ],
    "ballast": [ "rw_ballast", "rw_ballast_rusty", "rw_ballast_old" ], "sleeper": [ "rw_sleeper" ],
    "sleeper_wood": [ "rw_sleeper_wood" ], "rail": [ "rw_rail" ], "rail_head": [ "rw_rail_head" ],
    "asphalt": [ "rw_asphalt" ], "kerb": [ "rw_kerb" ], "setts": [ "rw_setts" ], "concrete": [ "rw_concrete", "rw_concrete_dark" ],
    "terrazzo": [ "rw_terrazzo", "rw_terrazzo_border" ], "sandstone": [ "rw_sandstone", "rw_sandstone_soot" ],
    "dressed": [ "rw_dressed", "rw_dressed_red" ], "steel": [ "rw_steel", "rw_steel_soot" ],
    "steel_modern": [ "rw_steel_dark", "rw_steel_grey" ], "lattice": [ "rw_lattice" ],
    "window_dark": [ "rw_window_dark" ], "glass_roof": [ "rw_glass_roof" ],
    "train": [ "rw_train_red", "rw_train_blue", "rw_train_white", "rw_train_grey", "rw_train_dark", "rw_train_yellow" ],
    "bogie": [ "rw_bogie" ], "rubber": [ "rw_rubber" ], "wagon": [ "rw_wagon_rust", "rw_wagon_grey" ],
    "container": [ "rw_container_blue", "rw_container_red", "rw_container_green", "rw_container_orange",
                   "rw_container_grey", "rw_container_blue_roof", "rw_container_red_roof", "rw_container_green_roof",
                   "rw_container_orange_roof", "rw_container_grey_roof" ],
    "plain": [ "rw_black", "rw_white_paint", "rw_yellow_paint", "rw_red_paint" ],
    "lamps": [ "rw_lamp_warm", "rw_lamp_cool", "rw_signal_red", "rw_signal_green", "rw_signal_yellow" ],
    "wood": [ "rw_wood" ], "facade": [ "rw_facade_cream", "rw_facade_ochre", "rw_facade_grey", "rw_facade_rose" ],
    "clock": [ "rw_clock" ], "signs": [ "rw_signs" ], "displays": [ "rw_displays" ], "posters": [ "rw_posters" ],
    "shopsigns": [ "rw_shopsigns" ], "graffiti": [ "rw_graffiti" ], "lettering": [ "rw_lettering" ],
    "vending": [ "rw_vending" ],
}

DECALS = { "rw_clock" }
# Self-lit paints: brightness. Where the texture draws an illum mask (<texture>_illum.png: the signs' faces, the
# displays' LEDs, the shop signs' lit letters and boxes) only that glows; otherwise the whole paint does, its colour the
# light it gives.
ILLUM = { "rw_signs": 1.4, "rw_displays": 2.4, "rw_shopsigns": 1.6, "rw_vending": 2.4, "rw_lamp_warm": 6.0, "rw_lamp_cool": 6.0,
          "rw_signal_red": 8.0, "rw_signal_green": 8.0, "rw_signal_yellow": 8.0 }
# Metalness per paint where it differs from its texture's.
METALNESS = { "rw_rail_head": 1.0, "rw_lettering": 0.5 }
# A paint sharing its texture's roughness but rougher or glossier: g_flRoughnessScaleFactor is an exponent on it
# (under 1 rougher), so a soot crust can be matt on the same map as the clean paint.
ROUGH_EXP = { "rw_steel_soot": 0.5, "rw_sandstone_soot": 0.8 }
ALPHA_TESTED = { "rw_lattice", "rw_graffiti", "rw_lettering" }
# Clear glass on shaders/glass.shader: ( tint, absorption ).
GLASS = { "rw_glass": ( ( 0.92, 0.95, 0.94 ), 0.15 ),
          # The platform canopies' laminated safety glass (railhead_canopy), faintly green at its edges, a little dusty.
          "rw_canopy_glass": ( ( 0.86, 0.91, 0.89 ), 0.25 ) }
# Car paint, with no texture of its own: white (materials/default/default_color.tga) tinted to the colour through
# g_vColorTint, flat normals and one roughness all over, a clear coat's. paint: ( sRGB colour, metalness, roughness ).
# The trains' paints have their grime and panel seams, and every other texture its dirt, which read wrong on a car.
# The signals' dark lenses and the lamps' opal glass are flat colours the same way.
PAINTED = { "rw_car_grey": ( ( 74, 78, 83 ), 0.4, 0.3 ),            # a metallic graphite grey
            "rw_car_silver": ( ( 160, 164, 168 ), 0.6, 0.3 ),
            "rw_car_white": ( ( 226, 228, 228 ), 0.0, 0.28 ),
            "rw_car_black": ( ( 20, 21, 23 ), 0.2, 0.25 ),
            "rw_car_ivory": ( ( 228, 214, 172 ), 0.0, 0.28 ),         # taxi light ivory, RAL 1015
            "rw_car_red": ( ( 140, 16, 22 ), 0.3, 0.28 ),
            "rw_car_blue": ( ( 22, 44, 90 ), 0.4, 0.28 ),
            # A traffic signal's lenses while they're dark: tinted glass over a black reflector, glossy.
            "rw_lens_red": ( ( 82, 14, 12 ), 0.0, 0.12 ),
            "rw_lens_amber": ( ( 92, 58, 10 ), 0.0, 0.12 ),
            "rw_lens_green": ( ( 10, 50, 40 ), 0.0, 0.12 ),
            # Opal (milk) glass, the street lamps' and lanterns' by day, with the lamps off.
            "rw_opal_glass": ( ( 214, 214, 206 ), 0.0, 0.3 ),
            # The kiosk's: its solid-surface stone counter, the shelves' warm white backs and trays, the pothos and
            # its glazed pot, and the bottled drinks, the colour of what's in them through the clear PET.
            "rw_kiosk_stone": ( ( 216, 210, 199 ), 0.0, 0.32 ),
            "rw_kiosk_shelf": ( ( 232, 226, 214 ), 0.0, 0.6 ),
            "rw_pot": ( ( 230, 228, 222 ), 0.0, 0.22 ),
            "rw_soil": ( ( 46, 34, 26 ), 0.0, 0.95 ),
            "rw_leaf": ( ( 46, 104, 40 ), 0.0, 0.42 ),
            "rw_leaf_light": ( ( 104, 150, 58 ), 0.0, 0.42 ),
            "rw_bottle_water": ( ( 178, 206, 218 ), 0.0, 0.08 ),
            "rw_bottle_apple": ( ( 204, 148, 44 ), 0.0, 0.1 ),
            "rw_bottle_orange": ( ( 236, 126, 26 ), 0.0, 0.1 ),
            "rw_bottle_cola": ( ( 38, 20, 14 ), 0.0, 0.08 ),
            "rw_bottle_lemon": ( ( 226, 212, 116 ), 0.0, 0.1 ),
            "rw_bottle_tea": ( ( 146, 76, 28 ), 0.0, 0.1 ),
            # The snack machine's black powder coat, satin.
            "rw_satin_black": ( ( 17, 17, 19 ), 0.0, 0.34 ),
            # The Rotunde's (railhead_backdrop.rotunda): its glazing, which the sky lights from a distance, its iron
            # frames and the frieze's panels in a dark green-grey, and the zinc of its cornice and roof.
            "rw_rotunda_glass": ( ( 118, 138, 158 ), 0.0, 0.08 ),
            "rw_rotunda_iron": ( ( 58, 66, 70 ), 0.25, 0.45 ),
            "rw_rotunda_panel": ( ( 80, 88, 94 ), 0.25, 0.5 ),
            "rw_zinc": ( ( 150, 155, 158 ), 0.35, 0.42 ) }
# Textured glass on shaders/glass.shader (its texture's colour, normal and roughness): paint: absorption.
TEXTURED_GLASS = { "rw_glass_roof": 0.85 }
# How much each textured glass blurs what is behind it (glass.shader's g_flBlurAmount): rolled glass diffuses.
GLASS_BLUR = { "rw_glass_roof": 0.5 }
# Paints whose picture's bottom edge stands at z 0 (two storeys a tile).
ANCHORED = { "rw_facade_cream", "rw_facade_ochre", "rw_facade_grey", "rw_facade_rose", "rw_lime_dado",
             "rw_container_blue", "rw_container_red", "rw_container_green", "rw_container_orange", "rw_container_grey" }
# Textures whose files go in a folder of their own under materials/railhead: Railhead's containers are anchored and
# 48 x 102 in (round 2), and Lowtide's dressing still points at the old square materials/railhead/rw_container_*.vmat,
# so Railhead's live in materials/railhead/containers and the old ones stay as they are for Lowtide.
TEXTURE_SUBDIR = { "container": "containers" }
# Paints whose picture isn't square in the world: g_vTexCoordScale ( u, v ). The containers' walls are 48 in across by
# 102 in (a box's height) up the picture.
TEXCOORD_SCALE = { f"rw_container_{c}": ( 1.0, CONTAINER_WIDTH / CONTAINER_HEIGHT ) for c, _ in CONTAINER_COLOURS }
# railhead_finish's paints, under materials/railhead/finish.
FINISH_PAINTS = { "rw_lime", "rw_lime_dark", "rw_lime_dado", "rw_brick", "rw_brick_dark" }
# Paints whose picture's v runs along the polygon's longest edge.
GRAIN = { "rw_sleeper_wood", "rw_wood", "rw_rail", "rw_rail_head", "rw_coping", "rw_kerb" }
# Atlases: paint: ( width, height, { name: ( x0, y0, x1, y1 ) } ), px with the origin at the top left.
ATLASES = {
    "rw_signs": ( 2048, 2048, SIGNS_RECTS ),
    "rw_displays": ( 2048, 2048, DISPLAYS_RECTS ),
    "rw_posters": ( 2048, 2048, POSTERS_RECTS ),
    "rw_shopsigns": ( 2048, 2048, SHOPSIGNS_RECTS ),
    "rw_graffiti": ( 2048, 2048, GRAFFITI_RECTS ),
    "rw_lettering": ( 2048, 2048, LETTERING_RECTS ),
    "rw_kiosk": ( KIOSK.W, KIOSK.H, KIOSK.RECTS ),
    "rw_vending": ( 2048, 2048, VENDING_RECTS ),
}
# Paints whose textures another script draws, placed by their atlases' explicit UVs: paint: the script.
OWN_SCRIPT = { "rw_kiosk": "Tools/railhead_kiosk_art.py" }


def paints():
    """ paint -> ( texture, tile units ) for every paint, without drawing anything. Atlases, the clock and the lattice
    have 1.0 (explicit UVs); the glass, 64. """
    out = { p: ( tex, TEXTURES[tex][4] ) for tex, ps in TEXTURE_PAINTS.items() for p in ps }
    import railhead_buffer
    out.update( { p: ( "buffer", tile ) for p, tile in railhead_buffer.PAINTS.items() } )
    # The kiosk terminal authors its own atlas and the silver/plastic variants.
    out.update({"rw_card_reader": ("card_reader", 1.0), "rw_card_reader_metal": ("card_reader", 1.0),
                "rw_card_reader_screen": ("card_reader", 1.0)})
    out.update({"rw_ticket_machine": ("ticket_machine", 1.0), "rw_ticket_machine_metal": ("ticket_machine", 1.0),
                "rw_ticket_machine_display": ("ticket_machine", 1.0)})
    out.update({"rw_luggage_body": ("luggage", 1.0), "rw_luggage_markings": ("luggage", 1.0)})
    import railhead_train as EMU
    out.update({paint: ("emu", 96.0 if paint in (EMU.RED, EMU.BLUE) else 1.0) for paint in EMU.PAINTS})
    import railhead_signal_box as SIGNAL_BOX
    out.update({paint: ("signal_box", tile) for paint, tile in SIGNAL_BOX.PAINTS.items()})
    for g in GLASS:
        out[g] = ( "glass", 64.0 )
    for p in PAINTED:
        out[p] = ( "painted", 96.0 )
    for p in OWN_SCRIPT:
        out[p] = ( p, 1.0 )
    # railhead_finish's lime plaster and brick (materials/railhead/finish, material_path()).
    import railhead_finish
    out.update( railhead_finish.PAINTS )
    return out


def tile_units( paint_name ):
    return paints()[paint_name][1]


def material_path( paint_name ):
    if paint_name in ("rw_luggage_body", "rw_luggage_markings"):
        return f"{RESOURCE_DIR}/luggage/{paint_name}.vmat"
    if paint_name in FINISH_PAINTS:
        return f"{RESOURCE_DIR}/finish/{paint_name}.vmat"
    for texture, sub in TEXTURE_SUBDIR.items():
        if paint_name in TEXTURE_PAINTS.get( texture, () ):
            return f"{RESOURCE_DIR}/{sub}/{paint_name}.vmat"
    return f"{RESOURCE_DIR}/{paint_name}.vmat"


def rect_uv( atlas, name ):
    """ An atlas entry's ( u0, v0, u1, v1 ), v up from the picture's bottom edge. """
    W, H, rects = ATLASES[atlas]
    x0, y0, x1, y1 = rects[name]
    return ( x0 / W, 1.0 - y1 / H, x1 / W, 1.0 - y0 / H )


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def save_image( image, path ):
    """ Saves through a temporary file beside the picture, renamed over it once complete (map_kit.write_text's way): the
    open editor compiles a changed picture straight away and holds it while it does, so writing it in place can fail
    (OSError 22) or leave the editor half a file. A failed rename is tried again for up to 10 s. """
    path = Path( path )
    # Not named as a picture, so the editor's asset system doesn't take the temporary file up (it gave one a .meta).
    temp = path.with_name( path.name + ".writing" )
    image.save( temp, format={ ".jpg": "JPEG", ".jpeg": "JPEG" }.get( path.suffix.lower(), "PNG" ), optimize=True )
    for attempt in range( 20 ):
        try:
            temp.replace( path )
            return
        except OSError:
            if attempt == 19:
                raise
            time.sleep( 0.5 )


def save_grey( path, a ):
    save_image( Image.fromarray( np.clip( np.rint( np.asarray( a, float ) * 255 ), 0, 255 ).astype( np.uint8 ), "L" ), path )


def save_rgb( path, a ):
    save_image( Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" ), path )


def vmat( paint_name, texture, metalness, extra, resource=RESOURCE_DIR ):
    ao_path = f"{resource}/{texture}_ao.png" if "ao" in extra else DEFAULT_AO
    lines_ = [ "// Tools/railhead_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if paint_name in ALPHA_TESTED:
        lines_ += [ '    F_ALPHA_TEST "1"', '    F_RENDER_BACKFACES "1"',
                    f'    TextureTranslucency "{resource}/{texture}_trans.png"',
                    '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"' ]
    if paint_name in ILLUM:
        mask = f"{resource}/{texture}_illum.png" if "illum" in extra else "[1.000000 1.000000 1.000000 0.000000]"
        lines_ += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{mask}"',
                    f'    g_flSelfIllumBrightness "{ILLUM[paint_name]:.2f}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                    '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    if paint_name in TEXCOORD_SCALE:
        su, sv = TEXCOORD_SCALE[paint_name]
        lines_.append( f'    g_vTexCoordScale "[{su:.7f} {sv:.7f}]"' )
        if paint_name in ANCHORED and abs( sv - 1.0 ) > 1e-6:
            # The engine flips v on import (1 - v) before the scale, so an anchored picture scaled by sv starts sv up
            # its height instead of at its foot: the containers showed their rail band at z 48. This puts it back.
            lines_.append( f'    g_vTexCoordOffset "[0.0000000 {-sv:.7f}]"' )
    lines_ += [ f'    g_flRoughnessScaleFactor "{ROUGH_EXP.get( paint_name, 1.0 ):g}"', f'    g_flMetalness "{METALNESS.get( paint_name, metalness ):.2f}"',
                f'    TextureColor "{resource}/{paint_name}_color.png"',
                f'    TextureNormal "{resource}/{texture}_normal.png"',
                f'    TextureRoughness "{resource}/{texture}_rough.png"',
                f'    TextureAmbientOcclusion "{ao_path}"',
                '    g_vColorTint "[1.0 1.0 1.0 1.0]"',
                '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines_ ) + "\n"


def glass_vmat( paint_name, tint, absorption ):
    """ Clear glass, its colour the light it lets through. """
    r, g, b = tint
    return ( '// Tools/railhead_materials.py\n'
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/glass.shader"\n'
             '    F_GLASS_QUALITY "2"\n'
             '    g_bFogEnabled "1"\n'
             '    g_flBlurAmount "0.02"\n'
             '    g_flRefractionStrength "1.006"\n'
             f'    AlbedoAbsorption "{absorption:.2f}"\n'
             '    g_flTintColor "[1.000000 1.000000 1.000000 0.000000]"\n'
             f'    TextureColor "[{r:.6f} {g:.6f} {b:.6f} 0.000000]"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             '    TextureRoughness "[0.040000 0.040000 0.040000 0.000000]"\n'
             '    TextureMetalness "[0.000000 0.000000 0.000000 0.000000]"\n'
             '    TextureAmbientOcclusion "[1.000000 1.000000 1.000000 0.000000]"\n'
             '    TextureBlendMask "materials/default/default_blend.tga"\n'
             '    TextureTintMask "materials/default/default.tga"\n'
             '    TextureTranslucency "materials/default/default_trans.tga"\n'
             "}\n" )


def painted_vmat( paint_name, colour, metalness, roughness ):
    """ A PAINTED paint: a flat colour, flat normals, one roughness. """
    r, g, b = ( c / 255.0 for c in colour )
    return ( '// Tools/railhead_materials.py\n'
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/complex.shader"\n'
             '    F_SPECULAR "1"\n'
             '    g_flRoughnessScaleFactor "1"\n'
             f'    g_flMetalness "{metalness:.2f}"\n'
             '    TextureColor "materials/default/default_color.tga"\n'
             '    TextureNormal "materials/default/default_normal.tga"\n'
             f'    TextureRoughness "[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]"\n'
             f'    TextureAmbientOcclusion "{DEFAULT_AO}"\n'
             f'    g_vColorTint "[{r:.6f} {g:.6f} {b:.6f} 1.000000]"\n'
             '    g_flModelTintAmount "1.0"\n'
             "}\n" )


def textured_glass_vmat( paint_name, texture, absorption ):
    """ Glass with a picture (the wired, dirty roof glazing), as building_textures' glass_vmat: the colour is the light
    let through, and the roughness blurs what's behind. """
    return ( '// Tools/railhead_materials.py\n'
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/glass.shader"\n'
             '    F_GLASS_QUALITY "2"\n'
             '    g_bFogEnabled "1"\n'
             f'    g_flBlurAmount "{GLASS_BLUR.get( paint_name, 0.12 ):.2f}"\n'
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


def write_texture( name, out_dir ):
    import railhead_scanned
    scanned = railhead_scanned.write_surface( name, out_dir )
    if scanned is not None:
        return scanned
    draw, size, seed, metalness, units = TEXTURES[name]
    rng = np.random.default_rng( seed )
    result = draw( rng, size )
    colours, rough, height, strength = result[:4]
    extra = result[4] if len( result ) > 4 else {}
    assert list( colours ) == TEXTURE_PAINTS[name], ( name, list( colours ) )
    height = np.asarray( height, float ) * np.ones( ( size, size ) )
    rough = np.asarray( rough, float ) * np.ones( ( size, size ) )
    normal = gl_normals( height, strength * size / 1024.0 )
    if name == "concrete":
        colours, rough, normal = railhead_scanned.concrete_detail( colours, rough, normal )
    # dressed() takes the scan's grain block by block itself (railhead_scanned.sandstone_grain): dressed_detail's one
    # stretched patch faded out at every tile edge, a grid on long cornices.
    if "detail_normal" in extra:
        # A finer detail normal (0..1, OpenGL) over the drawn relief, at its strength.
        detail, amount = extra.pop( "detail_normal" )
        normal = railhead_scanned.combine_normals( normal * 0.5 + 0.5, detail, amount ) * 2 - 1
    resource = RESOURCE_DIR
    if name in TEXTURE_SUBDIR:
        out_dir = Path( out_dir ) / TEXTURE_SUBDIR[name]
        resource = f"{RESOURCE_DIR}/{TEXTURE_SUBDIR[name]}"
    out_dir.mkdir( parents=True, exist_ok=True )
    save_rgb( out_dir / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( out_dir / f"{name}_rough.png", np.clip( rough, 0, 1 ) )
    if "ao" in extra:
        save_grey( out_dir / f"{name}_ao.png", np.clip( extra["ao"], 0, 1 ) )
    if "trans" in extra:
        save_grey( out_dir / f"{name}_trans.png", np.clip( extra["trans"], 0, 1 ) )
    if "illum" in extra:
        save_grey( out_dir / f"{name}_illum.png", np.clip( extra["illum"], 0, 1 ) )
    for paint_name, colour in colours.items():
        save_rgb( out_dir / f"{paint_name}_color.png", colour )
        if paint_name in TEXTURED_GLASS:
            text = textured_glass_vmat( paint_name, name, TEXTURED_GLASS[paint_name] )
        else:
            text = vmat( paint_name, name, metalness, extra, resource )
        ( out_dir / f"{paint_name}.vmat" ).write_text( text, encoding="utf-8", newline="\n" )
    scale = f"{units:g} units a tile, {size / units:.1f} px an inch" if units > 1 else "explicit UVs"
    print( f"wrote {name}: {', '.join( colours )} ({size} px, {scale})", flush=True )
    return colours, normal, extra


def write_glass( out_dir ):
    out_dir.mkdir( parents=True, exist_ok=True )
    for paint_name, ( tint, absorption ) in GLASS.items():
        ( out_dir / f"{paint_name}.vmat" ).write_text( glass_vmat( paint_name, tint, absorption ), encoding="utf-8",
                                                       newline="\n" )
    print( f"wrote glass: {', '.join( GLASS )}" )


def write_painted( out_dir ):
    out_dir.mkdir( parents=True, exist_ok=True )
    for paint_name, ( colour, metalness, rough ) in PAINTED.items():
        ( out_dir / f"{paint_name}.vmat" ).write_text( painted_vmat( paint_name, colour, metalness, rough ),
                                                       encoding="utf-8", newline="\n" )
    print( f"wrote paints: {', '.join( PAINTED )}" )


def lit( colour, normal, alpha=None ):
    light = np.array( ( -0.45, 0.55, 0.7 ) )
    light /= np.linalg.norm( light )
    ndl = np.clip( np.sum( normal * light, -1 ), 0.0, 1.0 )
    out = np.clip( colour * ( 0.35 + 0.9 * ndl )[..., None], 0, 255 )
    if alpha is not None:                               # alpha-tested: a grey checker shows through
        x, y = coords( out.shape[0] )
        check = np.where( ( ( x // 32 ) + ( y // 32 ) ) % 2 > 0, 70.0, 100.0 )
        a = ( alpha > 0.5 )[..., None]
        out = np.where( a, out, check[..., None] )
    return out


def write_sheet( results, path ):
    tiles = []
    for name, ( colours, normal, extra ) in results.items():
        for paint_name, colour in colours.items():
            img = Image.fromarray( lit( colour, normal, extra.get( "trans" ) ).astype( np.uint8 ) )
            img = img.resize( ( 384, 384 ), Image.LANCZOS )
            ImageDraw.Draw( img ).text( ( 6, 6 ), paint_name, fill=( 255, 255, 255 ) )
            tiles.append( img )
    cols = 8
    rows = ( len( tiles ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( 384 * cols, 384 * rows ), ( 16, 16, 16 ) )
    for k, t in enumerate( tiles ):
        sheet.paste( t, ( 384 * ( k % cols ), 384 * ( k // cols ) ) )
    sheet.save( path )
    print( f"wrote sheet {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"textures to draw (default all: {', '.join( TEXTURES )})" )
    parser.add_argument( "--out", help="write somewhere else (for trying things out)" )
    parser.add_argument( "--sheet", help="also write a lit contact sheet here" )
    args = parser.parse_args()
    out_dir = Path( args.out ) if args.out else OUT_DIR
    names = args.names or list( TEXTURES )
    for name in names:
        if name not in TEXTURES:
            parser.error( f"unknown texture {name}" )
    results = { name: write_texture( name, out_dir ) for name in names }
    write_glass( out_dir )
    write_painted( out_dir )
    if args.sheet:
        write_sheet( results, args.sheet )


if __name__ == "__main__":
    main()
