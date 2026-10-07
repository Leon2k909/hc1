"""
Stillhouse's materials (Tools/stillhouse_map.py, stillhouse_props.py and stillhouse_backdrop.py): Camas Ròin, a
whitewashed Scottish island distillery of 1824 on its bay, with its pier, beach, warehouses and the hills behind, on a
bright October afternoon. Drawn from scratch with numpy and PIL like Railhead's and Belltower's: lime harl and
limewash over rubble, tarred plinths, dressed granite (and the same under the tide line, weeded and barnacled), Ballachulish
-style slates, lead, corrugated iron, granite setts, tarmac, concrete, quarry tiles, pine floorboards, the dunnage
warehouses' earth floors, grating and chequer plate, the beach (shingle, shell sand, wet sand, the wrack line), grass,
the seabed, shore rock; the stills' copper (polished, working and verdigris), brass, painted steel, rust and stainless;
pine, cask oak and hoops, tarred and silvered boards, a boat's deck; paints and hulls; peat, malt, sacks, rope, net,
fish boxes, rubber, wall tiles, dark windows, tarpaulin; a lantern's glass and the kiln's embers; dirty glass; the
hills' grazing, heather, bracken, moor, rock, fields, conifers and the far hills; and three atlases: the black lettering
painted on the white walls (with the boats' white names), the plates and signs, and the casks' stencilled heads.

    python Tools/stillhouse_materials.py [name ...] [--out <dir>] [--sheet <png>]

- Writes Assets/materials/stillhouse/<texture>_normal.png and _rough.png per texture (with _trans.png for the
  alpha-tested ones (the net, the lettering) and _illum.png for a self-lit mask (the embers)), and per paint
  <paint>_color.png and <paint>.vmat. Most are on shaders/complex.shader; sh_glass and sh_glass_dirty are on
  shaders/glass.shader, and sh_sea on shaders/ridgeback_river.shader (with the engine's water normals, no texture of
  its own).
- Every texture tiles over its tile units (paints(); map_kit's world-scale UVs read them through the model's
  tile_overrides), except the atlases (ATLASES: sh_lettering, sh_signs, sh_cask_head), which the map scripts place by
  rect_uv() and whose pixel rectangles are LETTERING_RECTS, SIGNS_RECTS and CASK_HEAD_RECTS. A lettering entry's
  capitals are LETTERING_CAP px high on its LETTERING_BASELINE (LETTERING_CAP_SHARE of its rectangle's height), and
  its harl and paint are drawn for capitals LETTERING_CAP_INCHES tall, so place each word at that size; the signs
  are drawn at SIGN_PPI px an inch and the heads at CASK_HEAD_PPI.
- Heights are drawn in inches and the normal strength is 1024 / tile units, so the relief is the real thing's size.
- GRAIN paints run their picture's v along the polygon's longest edge (boards, staves, rope): their grain runs up and
  down the picture. Nothing is ANCHORED (the floors are at several levels) and there are no DECALS.
- Each tiling paint's mean colour is pinned to MEANS (the previews draw every paint flat in its mean colour, so the
  colours must read right at a glance); the pictures are drawn first and then shifted to it, which the script prints.
- Normals are OpenGL style (green up the picture), as s&box's model shader reads them.
- Nothing here names a real distillery, brand, boat or office: the lettering and signs are the design's own, in the
  project's fonts (Dinish, Chakra Petch).
- Deterministic: every texture has its own seed, so a rerun writes the same files.
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

ROOT = Path( __file__ ).resolve().parent.parent
OUT_DIR = ROOT / "Assets/materials/stillhouse"
RESOURCE_DIR = "materials/stillhouse"
DEFAULT_AO = "materials/default/default_ao.tga"
FONT_DIR = ROOT / "Assets/fonts"
SS = 2                                              # atlases are drawn at twice their size, then shrunk

spectral, smoothstep, gl_normals = T.spectral, T.smoothstep, BT.gl_normals


# ---------------------------------------------------------------------------------------------------------------------
# Helpers (Railhead's)

def unit( a ):
    return ( a - a.mean() ) / ( a.std() + 1e-9 )


def noise( rng, n, beta, fmin, fmax=None ):
    """ Tiling noise with unit spread, f in cycles a tile. """
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
    """ rgb (one sRGB colour, or one per px) lit by lum (linear, per px). """
    rgb = np.asarray( rgb, float )
    if rgb.ndim > 1:
        return BT.shade( rgb, np.asarray( lum, float ) )
    return BT.paint( rgb, np.asarray( lum, float ) )


def mix( a, b, t ):
    a = np.asarray( a, float )
    b = np.asarray( b, float )
    t = np.asarray( t, float )
    return a + ( b - a ) * ( t[..., None] if t.ndim else t )


def tinted( colour, rgb, amount ):
    """ colour pulled towards rgb at its own brightness (amount 0..1, per px or one). """
    linear = lin( colour )
    lum = linear @ np.array( ( 0.2126, 0.7152, 0.0722 ) )
    rel = lum / max( lum.mean(), 1e-6 )
    target = lin( rgb )[None, None, :] * rel[..., None]
    amount = np.asarray( amount, float )
    return srgb( linear + ( target - linear ) * ( amount[..., None] if amount.ndim else amount ) )


def darken( colour, factor ):
    """ colour times factor in linear light (per px). """
    return srgb( lin( colour ) * np.asarray( factor, float )[..., None] )


def stamp( field, x, y, rx, ry, value, angle=0.0, soft=1.0, profile="flat", mode="max" ):
    """ An ellipse into field (wrapping): flat with a soft edge, a dome or a cone; max, add or min. """
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
    """ An antialiased greyscale canvas that wraps: drawn ss times over with a margin, folded back into the tile. """

    def __init__( self, n, ss=2, margin=None ):
        self.n, self.s = n, ss
        self.m = int( min( n, margin if margin is not None else n // 4 ) )
        size = ( n + 2 * self.m ) * ss
        self.img = Image.new( "L", ( size, size ), 0 )
        self.draw = ImageDraw.Draw( self.img )

    def _shift( self, points ):
        x0, y0 = points[0]
        dx = ( x0 % self.n ) - x0
        dy = ( y0 % self.n ) - y0
        return [ ( ( x + dx + self.m ) * self.s, ( y + dy + self.m ) * self.s ) for x, y in points ]

    def line( self, points, width, value=1.0 ):
        self.draw.line( self._shift( points ), fill=int( value * 255 ), width=max( 1, int( round( width * self.s ) ) ),
                        joint="curve" )

    def polygon( self, points, value=1.0 ):
        self.draw.polygon( self._shift( points ), fill=int( value * 255 ) )

    def ellipse( self, x, y, rx, ry, value=1.0 ):
        ( cx, cy ), = self._shift( [ ( x, y ) ] )
        self.draw.ellipse( ( cx - rx * self.s, cy - ry * self.s, cx + rx * self.s, cy + ry * self.s ),
                           fill=int( value * 255 ) )

    def result( self ):
        a = np.asarray( self.img, float )
        t = self.n * self.s
        m = self.m * self.s
        a = _fold( _fold( a, t, m, 0 ), t, m, 1 )
        return a.reshape( self.n, self.s, self.n, self.s ).mean( ( 1, 3 ) ) / 255.0


class Layers:
    """ Flat shapes drawn at ss times the size and box-filtered down, wrapping at the tile's edges, each over the ones
    before it: colour, height (0..1), cover and an extra channel (0..1, a roughness). Straps are drawn as polygons
    between their cross-sections, so wide curved ones have no notches at their bends. """

    def __init__( self, colour, height, aux=0.0, ss=2 ):
        n = colour.shape[0]
        self.n, self.ss = n, ss
        big = n * ss

        def up_f( a ):
            a = np.ascontiguousarray( np.clip( np.broadcast_to( np.asarray( a, float ), ( n, n ) ), 0, 1 ), np.float32 )
            return Image.fromarray( a, "F" ).resize( ( big, big ), Image.BILINEAR )

        self.rgb = Image.fromarray( np.clip( colour, 0, 255 ).astype( np.uint8 ) ).resize( ( big, big ), Image.BILINEAR )
        self.height = up_f( height )
        self.aux = up_f( aux )
        self.cover = Image.new( "L", ( big, big ), 0 )
        self.draws = [ ImageDraw.Draw( im ) for im in ( self.rgb, self.height, self.cover, self.aux ) ]

    def _copies( self, xs, ys, pad ):
        big = self.n * self.ss
        out = []
        for ox in ( -big, 0, big ):
            if min( xs ) + ox > big + pad or max( xs ) + ox < -pad:
                continue
            for oy in ( -big, 0, big ):
                if min( ys ) + oy > big + pad or max( ys ) + oy < -pad:
                    continue
                out.append( ( ox, oy ) )
        return out

    def _fill( self, shapes, colours, heights, aux ):
        """ shapes: polygons in big px, each with its colour, height and aux; drawn with every wrapped copy. """
        xs = [ x for poly in shapes for x, _ in poly ]
        ys = [ y for poly in shapes for _, y in poly ]
        d_rgb, d_h, d_c, d_a = self.draws
        for ox, oy in self._copies( xs, ys, 4 ):
            for poly, c, h, a in zip( shapes, colours, heights, aux ):
                q = [ ( x + ox, y + oy ) for x, y in poly ]
                d_rgb.polygon( q, fill=( int( c[0] ), int( c[1] ), int( c[2] ) ) )
                d_h.polygon( q, fill=float( min( max( h, 0.0 ), 1.0 ) ) )
                d_c.polygon( q, fill=255 )
                d_a.polygon( q, fill=float( min( max( a, 0.0 ), 1.0 ) ) )

    def ribbon( self, points, widths, colours, heights, aux=0.5 ):
        """ A strap along points (tile px) with a width per point (px), and a colour, height and aux per segment
        (or one for all). """
        s = self.ss
        pts = np.asarray( points, float ) * s
        m = len( pts )
        if m < 2:
            return
        d = np.gradient( pts, axis=0 )
        d /= np.linalg.norm( d, axis=1, keepdims=True ) + 1e-9
        half = np.maximum( np.asarray( widths, float ), 0.35 )[:, None] * s / 2
        nrm = np.stack( [ -d[:, 1], d[:, 0] ], -1 ) * half
        left, right = pts + nrm, pts - nrm
        shapes = [ [ tuple( left[k] ), tuple( left[k + 1] ), tuple( right[k + 1] ), tuple( right[k] ) ] for k in range( m - 1 ) ]
        cols = colours if isinstance( colours, list ) else [ colours ] * ( m - 1 )
        hs = heights if isinstance( heights, list ) else [ heights ] * ( m - 1 )
        aux_s = aux if isinstance( aux, list ) else [ aux ] * ( m - 1 )
        self._fill( shapes, cols, hs, aux_s )

    def ellipse( self, x, y, rx, ry, angle, colour, height, aux=0.5, sides=14 ):
        s = self.ss
        ca, sa = math.cos( angle ), math.sin( angle )
        poly = []
        for k in range( sides ):
            t = 2 * math.pi * k / sides
            u, v = rx * math.cos( t ), ry * math.sin( t )
            poly.append( ( ( x + u * ca - v * sa ) * s, ( y + u * sa + v * ca ) * s ) )
        self._fill( [ poly ], [ colour ], [ height ], [ aux ] )

    def result( self ):
        s = self.ss
        rgb = np.asarray( self.rgb.reduce( s ), float )
        height = np.asarray( self.height.reduce( s ), float )
        cover = np.asarray( self.cover.reduce( s ), float ) / 255.0
        aux = np.asarray( self.aux.reduce( s ), float )
        return rgb, height, cover, aux


class Pile:
    """ Weed and flotsam piled over a surface strap by strap: Layers for the colour, the height above the surface (0..1
    over span inches) and the roughness (starting from rough), and a coarse map (cells cell px across) of how high the
    pile already stands, so each new strap lies on whatever is under it rather than at a level of its own. dt is one
    strap's thickness, layer inches, in 0..1. """

    def __init__( self, colour, rough, span, layer=0.08, cell=4 ):
        n = colour.shape[0]
        self.n, self.span, self.cell = n, span, max( 1, int( cell ) )
        self.dt = layer / span
        self.layers = Layers( colour, np.zeros( ( n, n ) ), rough )
        self.m = max( 1, n // self.cell )
        self.top = np.zeros( ( self.m, self.m ) )
        self._ring = np.array( [ ( dx, dy ) for dx in ( -1, 0, 1 ) for dy in ( -1, 0, 1 ) ] )

    def _cells( self, pts ):
        return np.floor( np.asarray( pts, float ).reshape( -1, 2 ) / self.cell ).astype( int )

    def under( self, pts ):
        """ How high (0..1) the pile stands under and right round each point. """
        i = self._cells( pts )
        ix = ( i[:, None, 0] + self._ring[None, :, 0] ) % self.m
        iy = ( i[:, None, 1] + self._ring[None, :, 1] ) % self.m
        return self.top[iy, ix].max( 1 )

    def lay( self, pts, levels ):
        """ Records points (px) as lying at levels (0..1). """
        i = self._cells( pts ) % self.m
        lv = np.broadcast_to( np.asarray( levels, float ).ravel(), ( len( i ), ) )
        np.maximum.at( self.top, ( i[:, 1], i[:, 0] ), lv )

    def rest( self, pts, lift ):
        """ The level (0..1) each point of a new strap lies at: on whatever is under it plus lift, smoothed along the
        strap so it drapes over what it crosses rather than stepping. """
        under = self.under( pts )
        r = under + lift
        if len( r ) > 4:
            s = np.convolve( np.pad( r, 2, mode="edge" ), np.array( [ 1, 2, 3, 2, 1 ] ) / 9.0, mode="valid" )
            r = np.maximum( s, under + 0.5 * lift )
        return np.clip( r, 0.0, 0.97 )

    def result( self ):
        """ ( colour, the pile's height over the surface in inches, cover, roughness ). """
        rgb, rel, cover, aux = self.layers.result()
        return rgb, rel * self.span, cover, aux


def settle( ground, lift, cover, p ):
    """ The height (inches) of a pile (lift, cover from Pile.result) lying on ground: it bridges the ground's hollows
    narrower than about an inch (p px), lying over its high points. """
    size = max( 3, int( round( p ) ) | 1 )
    base = T.blur( ndimage.maximum_filter( ground, size=size, mode="wrap" ), 0.35 * p )
    return np.maximum( ground, ground + cover * np.maximum( base - ground, 0.0 ) + lift )


def crack_lines( rng, n, count, length, width, branch=0.35, margin=None, turn=0.18, pull=0.0 ):
    """ Hairline cracks: wandering polylines with the odd branch, 0..1. turn is how much they wander at each step;
    pull draws each back towards the way it set out, so long ones run on instead of curling up. """
    canvas = Canvas( n, 2, margin if margin is not None else min( n, int( length[1] ) + 8 ) )
    for _ in range( count ):
        x, y = rng.uniform( 0, n, 2 )
        angle = rng.uniform( 0, 2 * math.pi )
        todo = [ ( x, y, angle, rng.uniform( *length ), width ) ]
        while todo:
            x, y, angle, left, w = todo.pop()
            heading = angle
            points = [ ( x, y ) ]
            while left > 0:
                step = rng.uniform( 2, 5 ) * n / 1024
                angle += rng.normal( 0, turn ) + pull * ( heading - angle )
                x += math.cos( angle ) * step
                y += math.sin( angle ) * step
                points.append( ( x, y ) )
                left -= step
                if rng.random() < branch * step / 60 and w > 0.6:
                    todo.append( ( x, y, angle + rng.choice( ( -1, 1 ) ) * rng.uniform( 0.5, 1.1 ),
                                   left * rng.uniform( 0.3, 0.6 ), w * 0.7 ) )
            if len( points ) > 1:
                canvas.line( points, w )
    return canvas.result()


def blotches( rng, n, beta, fmin, fmax, cover, soft=0.25 ):
    """ Soft patches covering about cover of the tile. """
    field = noise( rng, n, beta, fmin, fmax )
    edge = np.quantile( field, 1.0 - cover )
    return smoothstep( edge - soft, edge + soft, field )


def run_down( source, length, fall=0.4, rng=None, n=None ):
    """ source washed down the picture (rain runs) for length px, fading. """
    out = source.copy()
    for k in range( 1, int( length ), 2 ):
        out = np.maximum( out, np.roll( source, k, axis=0 ) * math.exp( -k * fall / length * 3.0 ) )
    if rng is not None:
        out *= np.clip( 0.6 + 0.6 * streaks( rng, source.shape[0], 1.5, 4, 120, 30, 0.6 ), 0.0, 1.0 )
    return out


def cast_shadow( height, slope, reach, dx=0.6, soft=0.25 ):
    """ 1 lit, 0 shadowed: what stands over each px up the picture (and dx across) by more than slope a px. """
    shade = np.zeros_like( height )
    for k in range( 1, int( reach ) ):
        above = np.roll( np.roll( height, k, axis=0 ), int( round( k * dx ) ), axis=1 )
        shade = np.maximum( shade, above - height - k * slope )
    return 1.0 - smoothstep( 0.0, soft, shade )


def _rect_wrap( x, y, x0, y0, w, h, n ):
    """ ( inside, signed distance to the edge ) of a w x h rectangle at x0, y0 that wraps round the tile. """
    u, v = ( x - x0 ) % n, ( y - y0 ) % n
    inside = ( u < w ) & ( v < h )
    du = np.where( u < w, np.minimum( u, w - u ), -np.minimum( u - w, n - u ) )
    dv = np.where( v < h, np.minimum( v, h - v ), -np.minimum( v - h, n - v ) )
    edge = np.where( inside, np.minimum( du, dv ),
                     np.where( ( du < 0 ) & ( dv < 0 ), -np.hypot( du, dv ), np.minimum( du, dv ) ) )
    return inside, edge


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


# ---------------------------------------------------------------------------------------------------------------------
# Helpers (Stillhouse's)

def cells( rng, n, centres, squash=1.0, grow=None, wander=0.0, wander_f=( 3, 30 ), k=6, round_px=0.0 ):
    """ A power diagram over the tile (wrapping): ( the cell of each px, its distance in px in from the cell's border,
    its offset from the cell's centre ( n, n, 2 ) ). squash > 1 flattens the cells (rows of stones), grow adds to a
    cell's reach (big stones), wander bends the borders, round_px rounds the cells' corners (a soft minimum of the
    distances to the neighbours, so a corner sits about 0.7 round_px further in than its sides). """
    centres = np.asarray( centres, float )
    count = len( centres )
    tiled = np.concatenate( [ centres + ( ox * n, oy * n ) for ox in ( -1, 0, 1 ) for oy in ( -1, 0, 1 ) ] )
    scale = np.array( ( 1.0, squash ) )
    tree = cKDTree( tiled * scale )
    x, y = coords( n )
    if wander:
        x = x + noise( rng, n, 2.5, *wander_f ) * wander
        y = y + noise( rng, n, 2.5, *wander_f ) * wander
    q = np.stack( [ x.ravel(), y.ravel() * squash ], -1 )
    dist, idx = tree.query( q, k=k, workers=-1 )
    g = np.zeros( count ) if grow is None else np.asarray( grow, float )
    pd = dist ** 2 - g[idx % count] ** 2
    order = np.argsort( pd, axis=1 )
    pd = np.take_along_axis( pd, order, 1 )
    idx = np.take_along_axis( idx, order, 1 )
    p1 = tiled[idx[:, 0]] * scale
    sides = np.empty( ( len( q ), k - 1 ) )
    for j in range( 1, k ):
        pj = tiled[idx[:, j]] * scale
        sep = np.linalg.norm( pj - p1, axis=1 )
        sides[:, j - 1] = ( pd[:, j] - pd[:, 0] ) / ( 2 * np.maximum( sep, 1e-6 ) )
    border = sides.min( 1 )
    if round_px:
        border = border - round_px * np.log( np.exp( -( sides - border[:, None] ) / round_px ).sum( 1 ) )
    cell = ( idx[:, 0] % count ).reshape( n, n )
    off = ( q - p1 ).reshape( n, n, 2 ) / scale
    return cell, border.reshape( n, n ), off


def jittered( rng, n, spacing, jitter=0.45 ):
    """ Points about spacing px apart over the tile: a jittered grid. """
    k = max( 1, int( round( n / spacing ) ) )
    step = n / k
    gy, gx = np.mgrid[0:k, 0:k]
    pts = np.stack( [ ( gx + 0.5 ) * step, ( gy + 0.5 ) * step ], -1 ).reshape( -1, 2 )
    pts += rng.uniform( -jitter, jitter, pts.shape ) * step
    return pts % n


def match_mean( colour, target, iterations=6 ):
    """ colour scaled in linear light so its mean (as saved, in sRGB) is target. """
    linear = lin( colour )
    target = np.asarray( target, float )
    for _ in range( iterations ):
        out = np.clip( np.rint( srgb( linear ) ), 0, 255 )
        mean = out.reshape( -1, 3 ).mean( 0 )
        linear = linear * ( lin( target ) / np.maximum( lin( mean ), 1e-6 ) )
    return srgb( linear )


def flat( n, rgb ):
    return np.broadcast_to( np.asarray( rgb, float ), ( n, n, 3 ) ).copy()


def shade_by( colour, height, amount, sigma=2.0 ):
    """ Cavity shading: darker where the height is below its blurred self. """
    cav = np.clip( T.blur( height, sigma ) - height, 0, None )
    return darken( colour, np.exp( -amount * cav ) )


# The draw functions, by texture name (@texture( name ) registers one).
DRAWS = {}


def texture( name ):
    def register( fn ):
        DRAWS[name] = fn
        return fn
    return register


def _stub( paint_names, extra=None ):
    """ A flat picture in each paint's mean colour, while a texture is still to be drawn. """
    def draw( rng, n ):
        colours = { p: flat( n, MEANS.get( p, ( 128, 128, 128 ) ) ) for p in paint_names }
        if extra:
            return colours, 0.8, 0.0, 1.0, { k: np.full( ( n, n ), v ) for k, v in extra.items() }
        return colours, 0.8, 0.0, 1.0
    return draw


# ---------------------------------------------------------------------------------------------------------------------
# Atlases' rectangles (2048 x 2048 px each). The map scripts place them by rect_uv().

# sh_lettering: black painted capitals (Dinish Bold) on a transparent ground, for the white walls, and the boats' white
# names. The capitals are LETTERING_CAP px high in every rect, the baseline LETTERING_BASELINE[name] px under the rect's
# top, so every word on the walls has the same letters; camas_roin has room above for its Ò's accent.
LETTERING_FACE = "Dinish-Bold"
LETTERING_CAP = 120
LETTERING_TRACKING = 0.06                               # of the cap height, between letters
LETTERING_WORDS = {
    "camas_roin": "CAMAS RÒIN", "distillery": "DISTILLERY", "warehouse_1": "WAREHOUSE No. 1",
    "warehouse_2": "WAREHOUSE No. 2", "date_1824": "1824", "still_house": "STILL HOUSE", "tun_room": "TUN ROOM",
    "mash_house": "MASH HOUSE", "kiln": "KILN", "filling_store": "FILLING STORE", "pier_store": "PIER STORE",
    "boiler_house": "BOILER HOUSE", "spirit_store": "SPIRIT STORE", "cooperage": "COOPERAGE",
    "malt_barn": "MALT BARN", "sea_warehouse": "SEA WAREHOUSE", "peat_shed": "PEAT SHED", "office": "OFFICE",
    "boat_mairi_ros": "MAIRI ROS", "boat_cr47": "CR 47", "boat_cr112": "CR 112",
}
LETTERING_WHITE = ( "boat_mairi_ros", "boat_cr47", "boat_cr112" )
LETTERING_RECTS = {
    "camas_roin": ( 8, 8, 1028, 200 ), "distillery": ( 1040, 8, 1970, 162 ),
    "warehouse_1": ( 8, 212, 1455, 366 ), "boat_cr112": ( 1467, 212, 1975, 366 ),
    "warehouse_2": ( 8, 378, 1483, 532 ), "boat_cr47": ( 1495, 378, 1962, 532 ),
    "sea_warehouse": ( 8, 544, 1399, 698 ), "office": ( 1411, 544, 1995, 698 ),
    "filling_store": ( 8, 710, 1204, 864 ), "date_1824": ( 1216, 710, 1589, 864 ), "kiln": ( 1601, 710, 1986, 864 ),
    "boiler_house": ( 8, 876, 1185, 1030 ), "boat_mairi_ros": ( 1197, 876, 2039, 1030 ),
    "spirit_store": ( 8, 1042, 1101, 1196 ), "tun_room": ( 1113, 1042, 1968, 1196 ),
    "mash_house": ( 8, 1208, 1069, 1362 ), "peat_shed": ( 1081, 1208, 1972, 1362 ),
    "still_house": ( 8, 1374, 1051, 1528 ), "malt_barn": ( 1063, 1374, 2006, 1528 ),
    "cooperage": ( 8, 1540, 995, 1694 ), "pier_store": ( 1007, 1540, 1948, 1694 ),
}
LETTERING_BASELINE = { name: ( 175 if name == "camas_roin" else 137 ) for name in LETTERING_RECTS }
LETTERING_CAP_SHARE = { name: LETTERING_CAP / ( r[3] - r[1] ) for name, r in LETTERING_RECTS.items() }
# Each entry's capitals' real height in inches, which its harl and paint are drawn to (the map
# scripts size the words by these): the building names over the doors 14 in, CAMAS RÒIN and
# DISTILLERY on the Spirit Stores' sea faces 40 in, WAREHOUSE No. 1 and 2 27 in, the Pier Store's
# 1824 24 in, and the boats' names and numbers as stillhouse_props paints them on the bows.
LETTERING_NAME_INCHES = 14.0
LETTERING_CAP_INCHES = { name: LETTERING_NAME_INCHES for name in LETTERING_RECTS }
LETTERING_CAP_INCHES.update( { "camas_roin": 40.0, "distillery": 40.0, "warehouse_1": 27.0,
                               "warehouse_2": 27.0, "date_1824": 24.0, "boat_mairi_ros": 10.9,
                               "boat_cr47": 9.8, "boat_cr112": 9.8 } )
# px an inch the atlas's heights are drawn at (each entry's own scale is folded into them).
LETTERING_PPI = 4.0

# sh_signs: plates and signs, each its own entry, drawn at about 24 px an inch.
SIGNS_RECTS = {
    "datestone": ( 8, 8, 675, 408 ), "no_smoking": ( 683, 8, 950, 408 ), "flammable": ( 958, 8, 1358, 408 ),
    "danger_deep_water": ( 1366, 8, 1966, 408 ),
    "visitors": ( 8, 416, 728, 704 ), "fire_point": ( 736, 416, 1168, 704 ), "dead_slow": ( 1176, 416, 1752, 704 ),
    "private_pier": ( 8, 712, 728, 952 ), "bonded_warehouse": ( 736, 712, 1696, 952 ),
    "weighbridge": ( 8, 960, 872, 1176 ), "exit": ( 880, 960, 1312, 1176 ),
    "no_naked_lights": ( 8, 1184, 584, 1376 ), "keep_clear": ( 592, 1184, 1168, 1376 ),
    "wash_charger": ( 1176, 1184, 1752, 1376 ),
    "low_wines": ( 8, 1384, 584, 1576 ), "feints": ( 592, 1384, 1168, 1576 ),
    "spirit_receiver": ( 1176, 1384, 1752, 1576 ),
    "intermediate": ( 8, 1584, 584, 1776 ),
}
SIGN_PPI = 24.0                                         # px an inch

# sh_cask_head: cask ends, each square round its disc (the head's edge touches the square).
CASK_HEAD_NAMES = [ f"head_{k}" for k in range( 8 ) ] + [ "head_plain" ]
CASK_HEAD_RECTS = { name: ( 2 + 682 * ( k % 3 ), 2 + 682 * ( k // 3 ), 682 + 682 * ( k % 3 ), 682 + 682 * ( k // 3 ) )
                    for k, name in enumerate( CASK_HEAD_NAMES ) }
CASK_HEAD_PPI = 28.0                                    # px an inch, about


# ---------------------------------------------------------------------------------------------------------------------
# Mean colours (sRGB): each tiling paint's picture is shifted to its mean, which is what the previews draw.

MEANS = {
    # Walls and roofs
    "sh_harl": ( 219, 219, 212 ), "sh_harl_shade": ( 189, 189, 181 ), "sh_harl_cream": ( 219, 209, 179 ),
    "sh_harl_mould": ( 158, 158, 153 ), "sh_whitewash": ( 204, 204, 196 ), "sh_tar_black": ( 38, 38, 37 ),
    "sh_rubble": ( 115, 110, 102 ), "sh_granite": ( 148, 140, 135 ), "sh_granite_weed": ( 56, 61, 43 ),
    "sh_slate_roof": ( 64, 69, 77 ), "sh_lead": ( 107, 112, 117 ), "sh_corrugated_red": ( 115, 43, 31 ),
    "sh_corrugated_green": ( 51, 82, 66 ),
    # Ground and floors
    "sh_setts": ( 107, 105, 102 ), "sh_tarmac": ( 61, 61, 64 ), "sh_concrete": ( 148, 145, 138 ),
    "sh_floor_tiles": ( 140, 64, 46 ), "sh_floorboards": ( 128, 97, 64 ), "sh_dunnage": ( 51, 46, 41 ),
    "sh_grating": ( 62, 64, 64 ), "sh_chequer": ( 128, 130, 130 ), "sh_shingle": ( 128, 122, 115 ),
    "sh_sand": ( 194, 179, 148 ), "sh_sand_wet": ( 122, 107, 87 ), "sh_wrack": ( 66, 56, 34 ),
    "sh_grass": ( 87, 107, 51 ), "sh_seabed": ( 71, 69, 56 ), "sh_seabed_deep": ( 20, 26, 23 ),
    "sh_kerb": ( 158, 153, 148 ), "sh_rock": ( 92, 89, 83 ), "sh_rock_weed": ( 56, 54, 38 ),
    # Metals
    "sh_copper_bright": ( 204, 115, 71 ), "sh_copper": ( 140, 77, 46 ), "sh_copper_green": ( 82, 133, 112 ),
    "sh_brass": ( 184, 148, 77 ), "sh_steel": ( 140, 143, 145 ), "sh_steel_green": ( 36, 77, 66 ),
    "sh_rust": ( 102, 56, 31 ), "sh_stainless": ( 179, 181, 184 ),
    # Wood
    "sh_pine": ( 158, 107, 61 ), "sh_cask_oak": ( 117, 84, 54 ), "sh_cask_dark": ( 77, 54, 36 ),
    "sh_hoop": ( 46, 46, 48 ), "sh_timber_tar": ( 36, 33, 30 ), "sh_planks_grey": ( 133, 128, 117 ),
    "sh_deck": ( 122, 102, 77 ),
    # Paints and hulls
    "sh_paint_door": ( 18, 64, 61 ), "sh_paint_white": ( 230, 230, 224 ), "sh_paint_black": ( 34, 34, 34 ),
    "sh_paint_red": ( 158, 26, 20 ), "sh_paint_yellow": ( 224, 179, 31 ), "sh_paint_orange": ( 230, 102, 20 ),
    "sh_paint_blue": ( 31, 61, 117 ),
    "sh_hull_blue": ( 26, 51, 102 ), "sh_hull_red": ( 128, 31, 23 ), "sh_hull_white": ( 217, 217, 209 ),
    "sh_hull_black": ( 40, 40, 40 ),
    # Goods
    "sh_peat": ( 51, 33, 20 ), "sh_malt": ( 184, 148, 87 ), "sh_sack": ( 140, 115, 77 ), "sh_rope": ( 158, 140, 102 ),
    "sh_net": ( 77, 115, 89 ), "sh_fishbox_blue": ( 38, 82, 158 ), "sh_fishbox_orange": ( 224, 107, 26 ),
    "sh_rubber": ( 36, 36, 37 ), "sh_tile_white": ( 224, 227, 222 ), "sh_window_dark": ( 26, 31, 36 ),
    "sh_canvas": ( 92, 102, 92 ),
    # Lights and glass
    "sh_lamp_warm": ( 255, 219, 158 ), "sh_fire": ( 181, 89, 39 ), "sh_glass_dirty": ( 128, 133, 122 ),
    # The land
    "sh_hill_grass": ( 92, 107, 56 ), "sh_heather": ( 77, 61, 56 ), "sh_bracken": ( 140, 89, 41 ),
    "sh_moor": ( 82, 74, 51 ), "sh_hill_rock": ( 102, 99, 94 ), "sh_field": ( 97, 128, 56 ),
    "sh_far_hills": ( 92, 97, 107 ), "sh_conifer": ( 31, 46, 31 ),
}


# ---------------------------------------------------------------------------------------------------------------------
# Tables

# name: ( draw, size px, seed, metalness, tile units )
TEXTURE_PAINTS = {
    # Walls and roofs
    "harl": [ "sh_harl", "sh_harl_shade", "sh_harl_cream", "sh_harl_mould" ],
    "rubble": [ "sh_rubble", "sh_whitewash" ],
    "tar_black": [ "sh_tar_black" ],
    "granite": [ "sh_granite" ],
    "granite_weed": [ "sh_granite_weed" ],
    "slate": [ "sh_slate_roof" ],
    "lead": [ "sh_lead" ],
    "corrugated": [ "sh_corrugated_red", "sh_corrugated_green" ],
    # Ground and floors
    "setts": [ "sh_setts" ],
    "tarmac": [ "sh_tarmac" ],
    "concrete": [ "sh_concrete" ],
    "floor_tiles": [ "sh_floor_tiles" ],
    "floorboards": [ "sh_floorboards" ],
    "dunnage": [ "sh_dunnage" ],
    "grating": [ "sh_grating" ],
    "chequer": [ "sh_chequer" ],
    "shingle": [ "sh_shingle" ],
    "sand": [ "sh_sand" ],
    "sand_wet": [ "sh_sand_wet" ],
    "wrack": [ "sh_wrack" ],
    "grass": [ "sh_grass" ],
    "seabed": [ "sh_seabed" ],
    "seabed_deep": [ "sh_seabed_deep" ],
    "kerb": [ "sh_kerb" ],
    "rock": [ "sh_rock" ],
    "rock_weed": [ "sh_rock_weed" ],
    # Metals
    "copper_bright": [ "sh_copper_bright" ],
    "copper": [ "sh_copper" ],
    "copper_green": [ "sh_copper_green" ],
    "brass": [ "sh_brass" ],
    "steel_paint": [ "sh_steel", "sh_steel_green" ],
    "rust": [ "sh_rust" ],
    "stainless": [ "sh_stainless" ],
    # Wood
    "pine": [ "sh_pine" ],
    "cask": [ "sh_cask_oak", "sh_cask_dark" ],
    "hoop": [ "sh_hoop" ],
    "timber_tar": [ "sh_timber_tar" ],
    "planks_grey": [ "sh_planks_grey" ],
    "deck": [ "sh_deck" ],
    # Paints and hulls
    "paint": [ "sh_paint_door", "sh_paint_white", "sh_paint_black", "sh_paint_red", "sh_paint_yellow",
               "sh_paint_orange", "sh_paint_blue" ],
    "hull": [ "sh_hull_blue", "sh_hull_red", "sh_hull_white", "sh_hull_black" ],
    # Goods
    "peat": [ "sh_peat" ],
    "malt": [ "sh_malt" ],
    "sack": [ "sh_sack" ],
    "rope": [ "sh_rope" ],
    "net": [ "sh_net" ],
    "fishbox": [ "sh_fishbox_blue", "sh_fishbox_orange" ],
    "rubber": [ "sh_rubber" ],
    "tile_white": [ "sh_tile_white" ],
    "window_dark": [ "sh_window_dark" ],
    "canvas": [ "sh_canvas" ],
    # Lights and glass
    "lamp": [ "sh_lamp_warm" ],
    "fire": [ "sh_fire" ],
    "glass_dirty": [ "sh_glass_dirty" ],
    # The land
    "hill_grass": [ "sh_hill_grass" ],
    "heather": [ "sh_heather" ],
    "bracken": [ "sh_bracken" ],
    "moor": [ "sh_moor" ],
    "hill_rock": [ "sh_hill_rock" ],
    "field": [ "sh_field" ],
    "conifer": [ "sh_conifer" ],
    "far_hills": [ "sh_far_hills" ],
    # Atlases
    "lettering": [ "sh_lettering" ],
    "signs": [ "sh_signs" ],
    "cask_head": [ "sh_cask_head" ],
}

_SPEC = {
    # name: ( size, seed, metalness, tile units )
    "harl": ( 1024, 101, 0.0, 256 ), "rubble": ( 1024, 102, 0.0, 192 ), "tar_black": ( 512, 103, 0.0, 128 ),
    "granite": ( 1024, 104, 0.0, 160 ), "granite_weed": ( 1024, 105, 0.0, 160 ), "slate": ( 1024, 106, 0.0, 128 ),
    "lead": ( 512, 107, 0.25, 96 ), "corrugated": ( 1024, 108, 0.0, 64 ),
    "setts": ( 1024, 201, 0.0, 96 ), "tarmac": ( 1024, 202, 0.0, 256 ), "concrete": ( 1024, 203, 0.0, 192 ),
    "floor_tiles": ( 512, 204, 0.0, 64 ), "floorboards": ( 1024, 205, 0.0, 128 ), "dunnage": ( 1024, 206, 0.0, 192 ),
    "grating": ( 512, 207, 0.5, 48 ), "chequer": ( 512, 208, 0.7, 48 ), "shingle": ( 1024, 209, 0.0, 128 ),
    "sand": ( 1024, 210, 0.0, 192 ), "sand_wet": ( 1024, 211, 0.0, 192 ), "wrack": ( 1024, 212, 0.0, 128 ),
    "grass": ( 1024, 213, 0.0, 192 ), "seabed": ( 512, 214, 0.0, 256 ), "seabed_deep": ( 512, 215, 0.0, 512 ),
    "kerb": ( 512, 216, 0.0, 64 ), "rock": ( 1024, 217, 0.0, 256 ), "rock_weed": ( 1024, 218, 0.0, 256 ),
    "copper_bright": ( 512, 301, 1.0, 64 ), "copper": ( 1024, 302, 0.9, 96 ), "copper_green": ( 512, 303, 0.1, 96 ),
    "brass": ( 512, 304, 1.0, 48 ), "steel_paint": ( 1024, 305, 0.0, 96 ), "rust": ( 512, 306, 0.0, 96 ),
    "stainless": ( 512, 307, 1.0, 128 ),
    "pine": ( 1024, 401, 0.0, 128 ), "cask": ( 512, 402, 0.0, 64 ), "hoop": ( 512, 403, 0.4, 32 ),
    "timber_tar": ( 512, 404, 0.0, 128 ), "planks_grey": ( 1024, 405, 0.0, 128 ), "deck": ( 1024, 406, 0.0, 128 ),
    "paint": ( 512, 501, 0.0, 64 ), "hull": ( 512, 502, 0.0, 128 ),
    "peat": ( 512, 601, 0.0, 48 ), "malt": ( 1024, 602, 0.0, 64 ), "sack": ( 1024, 603, 0.0, 64 ),
    "rope": ( 512, 604, 0.0, 16 ), "net": ( 512, 605, 0.0, 64 ), "fishbox": ( 512, 606, 0.0, 32 ),
    "rubber": ( 512, 607, 0.0, 64 ), "tile_white": ( 512, 608, 0.0, 48 ), "window_dark": ( 512, 609, 0.0, 64 ),
    "canvas": ( 512, 610, 0.0, 64 ),
    "lamp": ( 256, 701, 0.0, 32 ), "fire": ( 512, 702, 0.0, 48 ), "glass_dirty": ( 512, 703, 0.0, 64 ),
    "hill_grass": ( 512, 801, 0.0, 512 ), "heather": ( 512, 802, 0.0, 512 ), "bracken": ( 512, 803, 0.0, 512 ),
    "moor": ( 512, 804, 0.0, 512 ), "hill_rock": ( 512, 805, 0.0, 512 ), "field": ( 512, 806, 0.0, 512 ),
    "conifer": ( 512, 807, 0.0, 512 ), "far_hills": ( 512, 808, 0.0, 2048 ),
    "lettering": ( 2048, 901, 0.0, 64 ), "signs": ( 2048, 902, 0.0, 64 ), "cask_head": ( 2048, 903, 0.0, 64 ),
}

ATLAS_TEXTURES = ( "lettering", "signs", "cask_head" )

# Self-lit paints and their brightness.
ILLUM = { "sh_lamp_warm": 6.0, "sh_fire": 3.5 }
# Metalness per paint where it differs from its texture's.
METALNESS = {}
ALPHA_TESTED = { "sh_net", "sh_lettering" }
# Clear glass: ( the light let through, absorption ).
GLASS = { "sh_glass": ( ( 0.93, 0.96, 0.95 ), 0.12 ) }
# Glass with a picture (on the glass shader): absorption.
TEXTURED_GLASS = { "sh_glass_dirty": 0.35 }
GRAIN = { "sh_floorboards", "sh_pine", "sh_cask_oak", "sh_cask_dark", "sh_timber_tar", "sh_planks_grey", "sh_deck",
          "sh_rope" }
ANCHORED = ()
DECALS = ()
SEA = { "sh_sea": 768.0 }

ATLASES = {
    "sh_lettering": ( 2048, 2048, LETTERING_RECTS ),
    "sh_signs": ( 2048, 2048, SIGNS_RECTS ),
    "sh_cask_head": ( 2048, 2048, CASK_HEAD_RECTS ),
}

def _texture_table():
    out = {}
    for name, ( size, seed, metalness, units ) in _SPEC.items():
        draw = DRAWS.get( name )
        if draw is None:
            draw = _stub( TEXTURE_PAINTS[name], { "trans": 1.0 } if name in ( "net", "lettering" ) else None )
        out[name] = ( draw, size, seed, metalness, units )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Shared pieces

def grain_field( rng, n, sigma=0.6, power=5.0 ):
    """ Sparse bumps a px or two across, unit spread: grit, aggregate, crystals. """
    return unit( T.blur( rng.random( ( n, n ) ) ** power, sigma ) )


def wash_down( source, length, spread=0.7, rng=None, keep=1.0 ):
    """ source carried down the picture for about length px, fading as it goes (rain runs, rust), as a wrapping FFT
    convolution with a one-sided exponential, scaled back to source's peak. keep is how much of each run's start
    survives where the runs are broken up (rng given). """
    n = source.shape[0]
    k = np.zeros( ( n, n ) )
    rows = np.arange( min( n, int( 4 * length ) ) )
    k[rows, 0] = np.exp( -rows / length )
    if spread:
        k = ndimage.gaussian_filter1d( k, spread, axis=1, mode="wrap" )
    out = np.clip( np.real( np.fft.ifft2( np.fft.fft2( source ) * np.fft.fft2( k ) ) ), 0, None )
    out *= source.max() / max( out.max(), 1e-9 )
    if rng is not None:
        out *= np.clip( 0.5 + 0.6 * streaks( rng, n, 1.5, 4, 160, 30, 0.6 ), 0.0, 1.0 ) * keep
    return np.clip( np.maximum( out, source ), 0, 1 )


def dots( rng, n, count, radius, profile="dome", soft=0.8 ):
    """ count round dots (radius px, a range) scattered over the tile, 0..1 (max where they overlap). """
    field = np.zeros( ( n, n ) )
    for _ in range( count ):
        r = rng.uniform( *radius )
        stamp( field, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.75, 1.0 ), 1.0,
               angle=rng.uniform( 0, math.pi ), soft=soft, profile=profile )
    return field


def packed( rng, n, points, radius ):
    """ Round things packed over the tile (pebbles, barnacles, grains), each the nearest to its px: ( index of each
    px's thing, distance from its centre over its radius, offset from its centre ( n, n, 2 ) ). points ( k, 2 ) px,
    radius ( k, ) px. Nearest by distance over radius, so big ones take more room. """
    points = np.asarray( points, float ) % n
    radius = np.asarray( radius, float )
    tree = cKDTree( points, boxsize=n )
    x, y = coords( n )
    q = np.stack( [ x.ravel(), y.ravel() ], -1 )
    dist, idx = tree.query( q, k=4, workers=-1 )
    idx = np.where( np.isfinite( dist ), idx, 0 )
    rel = dist / radius[idx]
    best = np.argmin( rel, 1 )
    pick = idx[np.arange( len( q ) ), best]
    d = rel[np.arange( len( q ) ), best]
    off = ( q - points[pick] + n / 2 ) % n - n / 2
    return pick.reshape( n, n ), d.reshape( n, n ), off.reshape( n, n, 2 )


def cavities( height, sigma ):
    """ How far each px lies below its surroundings (and above them), in the height's units. """
    smooth = T.blur( height, sigma )
    return np.clip( smooth - height, 0, None ), np.clip( height - smooth, 0, None )


def jag_1d( rng, n, amp, fmin, fmax, beta=1.5 ):
    """ A wrapping 1-D noise along the tile, unit spread times amp. """
    f = np.fft.rfftfreq( n, 1.0 / n )
    spec = np.zeros( len( f ), complex )
    band = ( f >= fmin ) & ( f <= fmax )
    spec[band] = ( rng.normal( size=band.sum() ) + 1j * rng.normal( size=band.sum() ) ) / np.maximum( f[band], 1 ) ** ( beta / 2 )
    out = np.fft.irfft( spec, n )
    return amp * ( out - out.mean() ) / ( out.std() + 1e-9 )


# ---------------------------------------------------------------------------------------------------------------------
# Walls and roofs

def _harl_relief( rng, n, tile ):
    """ Wet-dash harl's relief in inches: the wall's undulation over the rubble behind it, the lumps of the thrown
    dashes and the aggregate standing in the lime. Returns ( height, grit ). """
    undulate = 0.24 * noise( rng, n, 3.2, tile / 128, tile / 16 )
    dashes = 0.055 * noise( rng, n, 1.7, tile / 18, tile / 1.4 )
    grit = grain_field( rng, n, 0.55, 5.0 )
    return undulate + dashes + 0.035 * grit, grit


@texture( "harl" )
def harl( rng, n ):
    """ Harl: wet-dash lime roughcast thrown on over the rubble and limewashed, 4 px an inch. The wall undulates over
    the stones behind it, the dashes leave lumps an inch or two across and the grit stands in the lime. Weathering:
    dirt in the hollows, faint rain streaks, green algae where the wall stays damp (speckled at its edges), rust run
    down from old iron pins, hairline cracks and spots where the limewash has flaked off the grey harl. Paints: sh_harl
    white, sh_harl_shade greyer and dirtier, sh_harl_cream ochre-tinted limewash, sh_harl_mould the white blackened in
    patches by Baudoinia, the whisky fungus that grows on bonded warehouses' walls. """
    p = n / 256.0
    height, grit = _harl_relief( rng, n, 256 )
    cav, tops = cavities( height, 1.6 )
    mottle = noise( rng, n, 2.4, 2, 40 )
    fine = noise( rng, n, 1.0, n / 6 )
    # Rain washes dirt down the wall in faint streaks, heavier in broad bands.
    rain = smoothstep( 0.3, 2.4, streaks( rng, n, 1.3, 6, 260, 40 * p, 0.5 ) )
    rain *= smoothstep( -1.0, 1.2, noise( rng, n, 2.5, 1, 5 ) )
    # Algae where the wall stays damp: soft patches, speckled at their edges.
    damp = noise( rng, n, 2.4, 1, 24 ) + 0.45 * noise( rng, n, 1.2, 40, n / 3 )
    algae = smoothstep( 1.25, 2.1, damp )
    algae_core = smoothstep( 1.9, 2.7, damp )
    # Iron pins and stays bleeding rust down the wall, in soft runs.
    pins = np.zeros( ( n, n ) )
    for _ in range( 4 ):
        stamp( pins, rng.uniform( 0, n ), rng.uniform( 0, n ), 1.6 * p, 1.2 * p, 1.0, soft=1.5 )
    rust = 0.7 * T.blur( wash_down( pins, 16 * p, 2.5, rng ), 1.2 )
    # Hairline cracks, and flakes where the limewash has come off the harl under it.
    crack = crack_lines( rng, n, 6, ( 40 * p, 150 * p ), 0.9 )
    flake = smoothstep( 2.5, 2.8, noise( rng, n, 1.5, 24, n / 4 ) + 0.5 * mottle )
    height = height - 0.03 * crack - 0.035 * flake
    grit_bare = smoothstep( 1.8, 3.0, grit ) * smoothstep( -0.5, 1.5, noise( rng, n, 2.0, 3, 30 ) )

    def weathered( base, dirt, algae_amount, rain_amount ):
        lum = 1.0 + 0.022 * mottle + 0.018 * fine
        c = lum_paint( base, lum )
        c = darken( c, np.exp( -5.5 * cav ) * ( 1 + 0.6 * tops ) )
        c = mix( c, ( 150, 146, 136 ), 0.45 * grit_bare )
        c = mix( c, dirt, rain_amount * rain )
        c = mix( c, ( 140, 148, 122 ), algae_amount * algae )
        c = mix( c, ( 104, 116, 84 ), 0.3 * algae_amount * algae_core )
        c = mix( c, ( 168, 124, 86 ), 0.45 * rust )
        c = mix( c, ( 176, 174, 166 ), 0.85 * flake )
        return darken( c, 1.0 - 0.38 * crack )

    white = weathered( ( 228, 228, 221 ), ( 152, 152, 140 ), 0.4, 0.2 )
    shade = weathered( ( 212, 212, 204 ), ( 138, 138, 126 ), 0.55, 0.38 )
    shade = mix( shade, ( 150, 150, 138 ), 0.18 * smoothstep( -0.4, 1.6, mottle ) )
    cream = weathered( ( 234, 222, 188 ), ( 156, 148, 128 ), 0.35, 0.2 )
    # Baudoinia: a sooty black-grey film over the wall's texture, in broad blotches of every size with ragged edges,
    # run down the wall below the worst of them where the damp carries it, thinned where the rain washes it, and
    # freckled with its colonies (dots a quarter to half an inch across) where it hasn't closed up yet, more of them
    # the denser the film.
    blot = noise( rng, n, 3.0, 1, 10 ) + 0.4 * noise( rng, n, 2.2, 10, 48 ) + 0.18 * noise( rng, n, 1.6, 48, 160 )
    heavy = smoothstep( 0.6, 1.6, blot )
    drips = wash_down( heavy * smoothstep( 0.0, 1.0, noise( rng, n, 1.2, 20, 120 ) ), 22 * p, 1.2, rng )
    runs = unit( BT.stretched( rng, n, 1.5, 6, 60, ( 18 * p, 1.2 * p ) ) )
    film_f = blot + 0.9 * drips + 0.22 * runs * smoothstep( -0.5, 0.8, blot )
    film = smoothstep( -1.5, 2.1, film_f ) ** 1.3
    washed = smoothstep( 0.5, 2.4, BT.stretched( rng, n, 1.4, 3, 30, ( 14 * p, 4 * p ) ) )
    film = film * ( 1.0 - 0.3 * washed )
    specks = unit( T.blur( rng.random( ( n, n ) ), 1.1 ) ) + 0.6 * noise( rng, n, 1.4, 20, 90 )
    freck = smoothstep( -0.15, 0.15, specks - ( 2.4 - 3.2 * film ) )
    sooty = np.clip( 0.1 + 0.85 * film + 0.5 * freck * ( 1 - film ), 0, 1 )
    mould_colour = mix( ( 116, 114, 108 ), ( 46, 45, 42 ), smoothstep( 0.2, 0.95, film ) )
    mould_colour = darken( mould_colour, np.exp( -3.0 * cav ) )
    blackened = mix( white, mould_colour, 0.92 * sooty )
    rough = np.clip( 0.88 + 0.025 * fine + 1.2 * cav + 0.04 * algae - 0.04 * rust + 0.04 * crack, 0.0, 1.0 )
    return { "sh_harl": white, "sh_harl_shade": shade, "sh_harl_cream": cream, "sh_harl_mould": blackened }, \
        rough, height, 1024 / 256


@texture( "rubble" )
def rubble( rng, n ):
    """ Unharled rubble walling (dykes, gable ends), 5.3 px an inch: the island's grey quartzite, buff sandstone and
    dark slaty phyllite in rough courses, stones 6 to 20 inches across with the odd pinning stone, bedded and pointed
    in lime that has weathered back from their faces. The stones are lumpy, each tilted its own way, the phyllite
    banded along its bedding and the quartzite sugary, some stained with iron; grey-green and yellow crustose lichen
    on their faces. sh_whitewash is the same wall limewashed: thick in the joints and hollows, thinner on the stones'
    high points, so their shapes show through, flaked off here and there. """
    p = n / 192.0
    nx, ny = 13, 22                                     # stones about 15 in long and 9 high, before their sizes vary
    gx, gy = np.meshgrid( np.arange( nx ), np.arange( ny ) )
    jx = rng.uniform( -0.4, 0.4, gx.shape )
    jy = rng.uniform( -0.28, 0.28, gy.shape )
    pts = np.stack( [ ( gx + 0.5 + jx + 0.5 * ( gy % 2 ) ) * n / nx, ( gy + 0.5 + jy ) * n / ny ], -1 ).reshape( -1, 2 ) % n
    count = len( pts )
    grow = 0.38 * ( n / nx ) * rng.random( count ) ** 1.5
    cell, border, off = cells( rng, n, pts, squash=ny / nx, grow=grow, wander=1.3 * p, wander_f=( 3, 22 ),
                               round_px=1.2 * p )
    # Rounded stones bedded in lime joints about an inch wide.
    mw = ( 0.45 + 0.12 * noise( rng, n, 1.5, 6, 60 ) ) * p
    inner = np.clip( border - mw, 0, None )
    stone = smoothstep( -0.7, 0.7, border - mw )
    dome = 1.0 - np.exp( -inner / ( 1.5 * p ) )
    tilt = rng.normal( 0, 0.014, ( count, 2 ) )
    lumps = noise( rng, n, 2.3, 10, 120 )
    stone_h = dome * ( 0.5 + 0.14 * lumps + ( off * tilt[cell] ).sum( -1 ) ) + 0.02 * noise( rng, n, 1.0, n / 4 )
    mortar_h = -0.3 + 0.05 * noise( rng, n, 1.2, 30, n / 3 ) + 0.03 * grain_field( rng, n, 0.6, 4.0 )
    height = mortar_h * ( 1 - stone ) + stone * np.maximum( stone_h, mortar_h + 0.04 )
    cav, tops = cavities( height, 3.0 )
    # The stones.
    kinds = rng.choice( 4, size=count, p=( 0.38, 0.12, 0.42, 0.08 ) )     # quartzite, sandstone, phyllite, ironstained
    palettes = [ [ ( 160, 158, 152 ), ( 170, 166, 158 ), ( 150, 149, 145 ) ], [ ( 156, 146, 128 ), ( 146, 138, 122 ) ],
                 [ ( 106, 110, 108 ), ( 96, 100, 100 ), ( 112, 112, 108 ), ( 100, 100, 96 ) ],
                 [ ( 132, 118, 102 ), ( 138, 124, 106 ) ] ]
    tone = np.array( [ palettes[k][rng.integers( len( palettes[k] ) )] for k in kinds ], float )
    tone *= rng.uniform( 0.9, 1.1, ( count, 1 ) )
    kind = kinds[cell]
    mottle = noise( rng, n, 1.8, 10, 140 )
    bedding = BT.stretched( rng, n, 1.3, 8, 260, ( 0.6, 14 ) )
    sugar = noise( rng, n, 0.8, n / 5 )
    lum = 1.0 + 0.07 * mottle + np.where( kind == 2, 0.11, 0.035 ) * bedding + np.where( kind == 0, 0.05, 0.02 ) * sugar
    col = BT.shade( tone[cell], lum )
    stain = smoothstep( 0.4, 1.6, noise( rng, n, 2.0, 6, 60 ) ) * ( ( kind == 3 ) * 0.6 + ( kind == 0 ) * 0.2 )
    col = mix( col, ( 136, 104, 76 ), 0.4 * stain )
    veins = crack_lines( rng, n, 22, ( 8 * p, 30 * p ), 0.9, branch=0.1 ) * ( kind == 2 )
    col = mix( col, ( 190, 188, 180 ), 0.6 * veins )
    has_lichen = rng.random( count ) < 0.6
    lichen_f = noise( rng, n, 1.9, 18, 220 ) + 0.4 * noise( rng, n, 0.8, n / 4 )
    lichen = smoothstep( 1.35, 1.75, lichen_f ) * has_lichen[cell] * smoothstep( 0.5, 1.5, inner / p )
    yellow = smoothstep( 2.2, 2.5, lichen_f + 0.6 * noise( rng, n, 1.5, 20, 200 ) ) * has_lichen[cell]
    col = mix( col, ( 160, 164, 146 ), 0.55 * lichen )
    col = mix( col, ( 170, 152, 84 ), 0.5 * yellow * stone )
    # The lime mortar, weathered back and dirty.
    mortar = lum_paint( ( 178, 172, 156 ), 1.0 + 0.07 * noise( rng, n, 1.5, 20, n / 2 ) - 0.04 * grain_field( rng, n, 0.6, 6.0 ) )
    mortar = mix( mortar, ( 116, 112, 100 ), 0.35 * smoothstep( -0.5, 1.5, noise( rng, n, 2.0, 4, 40 ) ) )
    wall = mix( mortar, col, stone )
    ao = np.exp( -0.8 * cav )
    rough_wall = np.clip( np.where( stone > 0.5, 0.76 + 0.06 * mottle, 0.9 ) + 0.1 * lichen + 0.6 * cav, 0, 1 )
    rubble_colour = darken( wall, ao )
    # Limewashed: the lime lies thick in the joints and hollows and thin on the stones' high points.
    thin = smoothstep( 0.2, 0.6, stone_h ) * stone
    flake = blotches( rng, n, 1.8, 6, 90, 0.06, soft=0.06 ) * stone
    cover = np.clip( 0.93 - 0.2 * thin, 0, 1 ) * ( 1 - flake )
    lime = lum_paint( ( 226, 226, 218 ), 1.0 + 0.02 * mottle + 0.02 * sugar )
    washed = mix( wall, lime, cover )
    rain = smoothstep( 0.4, 2.4, streaks( rng, n, 1.3, 6, 200, 30 * p, 0.5 ) ) * smoothstep( -1, 1, noise( rng, n, 2.4, 1, 6 ) )
    washed = mix( washed, ( 150, 150, 138 ), 0.22 * rain )
    damp = smoothstep( 1.2, 2.0, noise( rng, n, 2.4, 1, 20 ) + 0.4 * noise( rng, n, 1.2, 30, n / 3 ) )
    washed = mix( washed, ( 124, 136, 98 ), 0.45 * damp )
    whitewash = darken( washed, np.exp( -0.9 * cav ) )
    return { "sh_rubble": rubble_colour, "sh_whitewash": whitewash }, rough_wall, height, 1024 / 192


@texture( "tar_black" )
def tar_black( rng, n ):
    """ The black-painted plinth band and the surrounds of the doors and windows: bitumen paint over the harl, 4 px an
    inch, filling its texture a little. Weathered to a dull brown-grey chalky bloom in places, scuffed and chipped back
    to the white harl, dust in the hollows. """
    p = n / 128.0
    height, grit = _harl_relief( rng, n, 128 )
    height = T.blur( height, 0.8 ) * 0.85
    cav, tops = cavities( height, 1.6 )
    mottle = noise( rng, n, 2.2, 2, 30 )
    fine = noise( rng, n, 1.0, n / 6 )
    bloom = smoothstep( -0.2, 1.8, mottle + 0.5 * noise( rng, n, 1.6, 10, 80 ) ) * ( 0.55 + 0.45 * smoothstep( 0, 0.03, tops ) )
    chips = smoothstep( 3.1, 3.3, noise( rng, n, 1.8, 6, 60 ) + 0.15 * fine )
    scuff = smoothstep( 1.6, 2.6, BT.stretched( rng, n, 1.2, 10, 200, ( 0.6, 6 ) ) ) * smoothstep( 0.0, 1.2, noise( rng, n, 2, 2, 12 ) )
    c = lum_paint( ( 30, 30, 29 ), 1.0 + 0.1 * fine + 0.12 * mottle )
    c = mix( c, ( 74, 70, 62 ), 0.5 * bloom )
    c = mix( c, ( 66, 64, 60 ), 0.35 * scuff )
    c = mix( c, ( 64, 60, 54 ), np.clip( 18 * cav, 0, 0.5 ) )               # dust settled in the hollows
    c = mix( c, ( 168, 166, 158 ), chips )
    height = height - 0.02 * chips
    rough = np.clip( 0.56 + 0.22 * bloom + 0.12 * scuff + 0.3 * chips + 0.03 * fine, 0, 1 )
    return { "sh_tar_black": c }, rough, height, 1024 / 128


@functools.lru_cache( None )
def _ashlar_layout( n ):
    """ The granite's courses (shared by sh_granite and sh_granite_weed, so the two meet block for block): courses 12
    to 20 inches, blocks 20 to 48 long, over a 160 in tile. """
    rng = np.random.default_rng( 1600 )
    p = n / 160.0
    block, u, v, length, rowh, row, count = BT.coursed( rng, n, ( 12 * p, 20 * p ), ( 20 * p, 48 * p ) )
    du = np.minimum( u, length - u )
    dv = np.minimum( v, rowh - v )
    return block, u, v, length, rowh, np.minimum( du, dv ), count


def _ashlar_relief( rng, n ):
    """ The dressed granite's height (inches) and pieces: a margin draft round each block's face, the face picked
    (stippled) and a little proud and lumpy, the arrises chipped, the joints of cement set back. """
    p = n / 160.0
    block, u, v, length, rowh, edge, count = _ashlar_layout( n )
    joint = 0.22 * p
    draft = 1.3 * p
    face = smoothstep( draft - 0.6, draft + 0.6, edge )
    inblock = smoothstep( joint - 0.5, joint + 0.5, edge )
    bulge = rng.uniform( 0.05, 0.22, count )[block] * np.sin( np.pi * np.clip( u / length, 0, 1 ) ) * np.sin( np.pi * np.clip( v / rowh, 0, 1 ) )
    lumps = 0.05 * noise( rng, n, 2.0, 16, 160 )
    picks = T.blur( ( rng.random( ( n, n ) ) < 0.08 ).astype( float ), 0.5 )
    chip_f = noise( rng, n, 1.6, 30, 220 )
    chips = smoothstep( 1.5, 2.1, chip_f ) * ( 1 - smoothstep( 0.0, 3.2 * p, edge ) )
    h_block = 0.02 + face * ( 0.06 + bulge + lumps - 0.05 * picks ) + 0.012 * noise( rng, n, 1.0, n / 4 )
    h_block -= 0.25 * chips
    height = np.where( inblock > 0, -0.28 + inblock * ( 0.28 + h_block ), -0.28 ) + 0.02 * noise( rng, n, 1.2, 40, n / 2 ) * ( 1 - inblock )
    return height, block, count, inblock, face, chips, edge


def _granite_crystals( rng, n ):
    """ Salt-and-pepper grains: ( black biotite, white quartz and feldspar, pink feldspar ), each 0..1. """
    coarse = T.blur( rng.random( ( n, n ) ), 1.0 )
    fine = T.blur( rng.random( ( n, n ) ), 0.5 )
    c = unit( unit( coarse ) * 0.6 + unit( fine ) )
    black = smoothstep( 1.25, 1.45, -c )                    # about 9% of the stone
    white = smoothstep( 0.65, 0.85, c )                     # about 23%
    pink = smoothstep( 0.35, 0.5, unit( T.blur( rng.random( ( n, n ) ), 1.2 ) ) ) * ( 1 - white ) * ( 1 - black )
    return black, white, pink


@texture( "granite" )
def granite( rng, n ):
    """ Dressed grey granite (the quoins, the pier's sides, the seawall, the steps, the gate arch), 6.4 px an inch:
    blocks in courses 12-20 in high and 20-48 long with half-inch cement joints. Each block has a tooled margin draft
    round a picked face that stands a little proud; the arrises are chipped. Salt-and-pepper grains (black mica, white
    quartz and feldspar, pinkish feldspar in some blocks), every block its own shade; grey-white crustose lichen, a
    little green where it stays damp, and rust run down from old iron. """
    p = n / 160.0
    height, block, count, inblock, face, chips, edge = _ashlar_relief( rng, n )
    cav, tops = cavities( height, 2.0 )
    black, white, pink = _granite_crystals( rng, n )
    tone = BT.tones( rng, [ ( 150, 145, 141 ), ( 158, 151, 145 ), ( 144, 141, 139 ), ( 162, 152, 144 ), ( 140, 138, 136 ) ],
                     count, 0.05 )
    pinkness = rng.uniform( 0.0, 1.0, count ) ** 2
    mottle = noise( rng, n, 1.8, 6, 120 )
    c = BT.shade( tone[block], 1.0 + 0.05 * mottle )
    c = mix( c, ( 178, 152, 140 ), 0.5 * pink * pinkness[block] )
    c = mix( c, ( 206, 202, 196 ), 0.75 * white )
    c = mix( c, ( 42, 42, 44 ), 0.85 * black )
    c = mix( c, ( 196, 192, 184 ), 0.6 * chips )                              # fresh stone in the chips
    lich_f = noise( rng, n, 1.8, 14, 240 ) + 0.5 * noise( rng, n, 0.7, n / 5 )
    lichen = smoothstep( 1.45, 1.75, lich_f ) * inblock
    c = mix( c, ( 182, 184, 172 ), 0.7 * lichen )
    c = mix( c, ( 52, 54, 50 ), 0.5 * smoothstep( 2.2, 2.4, lich_f + 0.8 * noise( rng, n, 1.0, 40, n / 2 ) ) * inblock )
    green = smoothstep( 0.6, 2.0, noise( rng, n, 2.6, 1, 10 ) ) * smoothstep( -0.5, 1.0, noise( rng, n, 1.5, 10, 80 ) )
    c = mix( c, ( 112, 122, 90 ), 0.35 * green )
    pins = np.zeros( ( n, n ) )
    for _ in range( 3 ):
        stamp( pins, rng.uniform( 0, n ), rng.uniform( 0, n ), 1.4 * p, 1.4 * p, 1.0 )
    rust = wash_down( pins, 30 * p, 1.4, rng )
    c = mix( c, ( 150, 98, 60 ), 0.5 * rust )
    cement = lum_paint( ( 138, 136, 130 ), 1.0 + 0.08 * noise( rng, n, 1.2, 30, n / 2 ) )
    cement = mix( cement, ( 96, 94, 88 ), 0.3 * smoothstep( -0.5, 1.5, mottle ) )
    c = mix( cement, c, inblock )
    c = darken( c, np.exp( -1.6 * cav ) )
    rough = np.clip( 0.64 + 0.04 * mottle - 0.04 * face + 0.25 * ( 1 - inblock ) + 0.2 * lichen + 0.5 * cav, 0, 1 )
    return { "sh_granite": c }, rough, height, 1024 / 160


@texture( "granite_weed" )
def granite_weed( rng, n ):
    """ The same granite below the high-water line, block for block with sh_granite (the courses are shared): wet and
    dark, crusted with black tar lichen, streaked with green weed where water seeps out, crowded with acorn barnacles
    (each a little grey-white cone with its dark opening), a few limpets, and bladderwrack and knotted wrack hanging
    down the blocks in curtains, the fronds lying flat against the stone side by side. """
    p = n / 160.0
    height, block, count, inblock, face, chips, edge = _ashlar_relief( rng, n )
    black, white, pink = _granite_crystals( rng, n )
    tone = BT.tones( rng, [ ( 84, 82, 78 ), ( 90, 86, 80 ), ( 78, 78, 76 ) ], count, 0.06 )
    c = BT.shade( tone[block], 1.0 + 0.05 * noise( rng, n, 1.8, 6, 120 ) )
    c = mix( c, ( 112, 110, 104 ), 0.5 * white )
    c = mix( c, ( 30, 30, 30 ), 0.6 * black )
    cement = lum_paint( ( 76, 74, 70 ), 1.0 + 0.08 * noise( rng, n, 1.2, 30, n / 2 ) )
    c = mix( cement, c, 0.6 + 0.4 * inblock )
    flow = math.pi / 2 + 0.1 * noise( rng, n, 3.0, 1, 4 )
    tones = [ ( 3, ( 72, 60, 28 ) ), ( 2, ( 63, 52, 25 ) ), ( 2, ( 80, 68, 31 ) ), ( 1, ( 54, 44, 22 ) ),
              ( 1, ( 88, 78, 35 ) ) ]
    c, height, rough = _shore_life( rng, n, p, c, height, tar=0.3, green=0.12, barnacles=0.18, weed=0.36, flow=flow,
                                    tones=tones, plants=0, size=1.0, hanging=True, strand=0.75, length=22.0 )
    return { "sh_granite_weed": c }, rough, height, 1024 / 160


def _shore_life( rng, n, p, colour, height, tar, green, barnacles, weed, flow, tones, plants, size=1.0, hanging=False,
                 strand=0.45, length=10.0 ):
    """ What grows on stone between the tides, over colour and height (inches): black tar lichen (Verrucaria maura)
    over about tar of it, a crust like spilt tar with lacy, speckled edges; green weed (Ulva) over about green of it (on
    a wall in streaks run down from seeps); acorn barnacles crowded in colonies over about barnacles of it (each a
    grey-white cone a third of an inch across with its dark opening, thinning out at the colonies' edges); a few
    limpets; and wrack over about weed of it: a mat of it combed along flow (headings, n x n) in tones, its fronds
    strand inches wide and length long, with plants of it laid over the mat's edges. Everything's wet. Returns
    ( colour, height, roughness ). """
    c = darken( colour, 0.8 )
    tar_f = noise( rng, n, 2.4, 2, 24 ) + 0.75 * noise( rng, n, 1.0, 40, n / 2.5 )
    tar_m = smoothstep( -0.06, 0.06, tar_f - np.quantile( tar_f, 1 - tar ) )
    c = mix( c, ( 24, 27, 26 ), 0.85 * tar_m )
    cav = cavities( height, 3.0 )[0]
    if hanging:
        seeps = np.zeros( ( n, n ) )
        for _ in range( 10 ):
            stamp( seeps, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 1.5, 4 ) * p, rng.uniform( 0.5, 1.2 ) * p,
                   1.0, soft=2.0 )
        green_f = wash_down( seeps, 36 * p, 1.2, rng ) + 0.25 * noise( rng, n, 1.6, 10, 80 ) \
            + 0.15 * streaks( rng, n, 1.5, 2, 40, 60, 0.5 )
    else:
        green_f = noise( rng, n, 2.3, 2, 40 ) + 0.5 * noise( rng, n, 1.2, 40, n / 3 ) + 4.0 * cav
    green_m = smoothstep( -0.1, 0.15, green_f - np.quantile( green_f, 1 - green ) )
    greens = mix( ( 46, 66, 30 ), ( 66, 88, 38 ), smoothstep( -1, 1, noise( rng, n, 1.5, 10, 100 ) ) )
    c = mix( c, greens, 0.8 * green_m )
    # Barnacles: each one there with the colony's density, so the colonies thin out at their edges.
    col_f = noise( rng, n, 2.0, 2, 24 ) + 0.45 * noise( rng, n, 1.4, 24, 120 ) - 1.2 * green_m
    dens = smoothstep( -0.5, 0.6, col_f - np.quantile( col_f, 1 - barnacles ) )
    pts = jittered( rng, n, 0.34 * p, 0.45 )
    pts = pts[rng.random( len( pts ) ) < 0.95 * dens[pts[:, 1].astype( int ) % n, pts[:, 0].astype( int ) % n]]
    shell = np.zeros( ( n, n ) )
    if len( pts ):
        radius = rng.uniform( 0.12, 0.22, len( pts ) ) * p
        who, d, _ = packed( rng, n, pts, radius )
        cone = np.clip( 1.0 - d, 0, 1 )
        shell = smoothstep( 1.05, 0.85, d )
        pale = rng.uniform( 0.8, 1.06, len( pts ) )[who]
        shell_c = lum_paint( ( 140, 137, 128 ), pale * ( 0.86 + 0.16 * cone ) )
        c = mix( c, shell_c, shell * 0.88 )
        c = mix( c, ( 62, 60, 54 ), shell * smoothstep( 0.62, 0.86, cone ) * 0.6 )
        height = height + 0.12 * np.sqrt( cone ) * shell
    limpets_h = np.zeros( ( n, n ) )
    for _ in range( int( 30 * ( n / p ) ** 2 / 160 ** 2 ) ):
        r = rng.uniform( 0.5, 0.85 ) * p
        stamp( limpets_h, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.8, 0.92 ), 1.0,
               angle=rng.uniform( 0, 3.2 ), profile="cone" )
    limpet = smoothstep( 0.0, 0.08, limpets_h )
    c = mix( c, mix( ( 140, 128, 104 ), ( 104, 96, 80 ), 0.5 + 0.5 * np.sin( limpets_h * 22 ) ), limpet )
    height = height + 0.5 * limpets_h
    rough = np.clip( 0.34 + 0.12 * tar_m - 0.12 * green_m + 0.28 * shell + 0.2 * limpet, 0, 1 )
    c = darken( c, np.exp( -1.2 * cavities( height, 2.0 )[0] ) )
    # The wrack: a combed mat in clumps, then plants laid over its edges.
    cf = noise( rng, n, 2.4, 2, 12 ) + 0.4 * noise( rng, n, 1.6, 12, 60 ) - 1.0 * green_m
    cov = smoothstep( -0.3, 0.3, cf - np.quantile( cf, 1 - weed ) )
    mat_c, thick, mat, mat_r = _weed_mat( rng, n, p, flow, cov, tones, strand=strand, length=length, hang=hanging )
    c = mix( c, mat_c, mat )
    rough = rough + ( mat_r - rough ) * mat
    height = settle( height, thick, mat, p )
    pile = Pile( c, rough, 2.0, layer=0.08, cell=0.5 * p )
    edge = smoothstep( 0.1, 0.35, cov ) * smoothstep( 0.75, 0.45, cov )
    placed = 0
    for _ in range( 30 * plants ):
        if placed >= plants:
            break
        x, y = rng.uniform( 0, n, 2 )
        if rng.random() > edge[int( y ) % n, int( x ) % n]:
            continue
        tone = T.pick( rng, tones, 1 )[0] * rng.uniform( 0.92, 1.08 )
        a = float( flow[int( y ) % n, int( x ) % n] ) + rng.normal( 0, 0.2 )
        s = size * rng.uniform( 0.8, 1.2 )
        if tone.sum() > 190:
            _knotted( pile, rng, x, y, a, p, s, tone, flow=flow, pull=0.25 )
        else:
            _fucus( pile, rng, x, y, a, p, s, tone, flow=flow, pull=0.25, fork=( 0.04, 0.1 ), seg=( 2.6, 4.2 ),
                    width=0.8 )
        placed += 1
    rgb, lift, cover, rough = pile.result()
    top = T.blur( lift, 0.7 * p )
    c = darken( rgb, np.exp( -2.0 * np.clip( top - lift, 0, None ) ) )
    weedy = np.maximum( mat, cover )
    shadow = np.clip( T.blur( np.roll( np.roll( weedy, int( 0.4 * p ), 0 ), int( 0.2 * p ), 1 ), 0.6 * p ) - weedy, 0, 1 )
    c = darken( c, 1.0 - 0.5 * shadow )
    c = darken( c, 1.0 - 0.25 * mat * smoothstep( 0.9, 0.2, thick ) )
    height = settle( height, lift, cover, p )
    return c, height, rough


def _slates( rng, n, p ):
    """ Random-width slating: courses of 4.5-6.5 in exposure, slates 7-14 in wide, each course's joints offset from
    the last; each slate's tail cut a little out of square and dressed, so the tails waver. Returns per px the slate,
    px from its exposed top (under the course above) and from its tail, from its sides, and the count. """
    heights = []
    while sum( heights ) < n:
        heights.append( rng.uniform( 4.5 * p, 6.5 * p ) )
    heights = np.array( heights ) * n / sum( heights )
    edges = np.concatenate( ( [ 0.0 ], np.cumsum( heights ) ) )
    rows = len( heights )
    xs = np.arange( n ) + 0.5
    slate_of = np.zeros( ( rows, n ), int )
    u_of = np.zeros( ( rows, n ) )
    len_of = np.zeros( ( rows, n ) )
    count = 0
    tails = np.zeros( ( rows, n ) )
    for r in range( rows ):
        cuts = [ 0.0 ]
        while cuts[-1] < n:
            cuts.append( cuts[-1] + rng.uniform( 7 * p, 14 * p ) )
        cuts = np.array( cuts ) * n / cuts[-1]
        shift = rng.uniform( 0, n )
        xx = ( xs - shift ) % n
        k = np.clip( np.searchsorted( cuts, xx, side="right" ) - 1, 0, len( cuts ) - 2 )
        slate_of[r] = count + k
        u_of[r] = xx - cuts[k]
        len_of[r] = cuts[k + 1] - cuts[k]
        tilt = rng.normal( 0, 0.025, len( cuts ) - 1 )[k]
        tails[r] = tilt * ( u_of[r] - len_of[r] / 2 ) + jag_1d( rng, n, 0.06 * p, 20, 300 )
        count += len( cuts ) - 1
    # The top of course r's exposed face is course r - 1's tail. ext runs from the course above the tile's first one
    # (the last, wrapped round) to the one below its last (the first), so every px finds its course's two lines.
    bounds = [ edges[r] + tails[( r - 1 ) % rows] for r in range( rows + 1 ) ]
    ext = np.stack( [ bounds[rows - 1] - n ] + bounds + [ bounds[1] + n ] )
    y = np.arange( n )[:, None] + 0.5
    k = ( y[None] >= ext[:, None, :] ).sum( 0 ) - 1
    course = ( k - 1 ) % rows
    cols = np.arange( n )[None, :]
    top = ext[k, cols]
    bottom = ext[k + 1, cols]
    slate = slate_of[course, cols]
    u = u_of[course, cols]
    length = len_of[course, cols]
    return slate, y - top, bottom - y, np.minimum( u, length - u ), count


@texture( "slate" )
def slate( rng, n ):
    """ Graded grey-blue Scottish slates, 8 px an inch: random widths 7-14 in, courses of 4.5-6.5 in, each slate tilted
    its own way, its exposed face rising a quarter inch to its tail, which drops onto the course below; the tails are
    dressed (bevelled and nicked) and a little out of square. Each slate its own shade (blue-grey, green-grey,
    purple-grey), its cleavage faintly streaked along its length, with the odd pyrite crystal rusted out. Grey-green
    and orange lichen and a little moss where the tails hold water. """
    p = n / 128.0
    slate_id, from_top, to_tail, from_side, count = _slates( rng, n, p )
    span = np.maximum( from_top + to_tail, 1.0 )
    rise = 0.22 * np.clip( from_top / span, 0, 1 )
    bevel_w = ( 0.14 + 0.06 * noise( rng, n, 1.2, 40, 400 ) ) * p
    bevel = 1.0 - smoothstep( 0.0, np.maximum( bevel_w, 0.4 ), to_tail )
    nicks = smoothstep( 1.9, 2.4, noise( rng, n, 1.2, 60, n / 2 ) ) * ( 1 - smoothstep( 0, 0.5 * p, to_tail ) )
    gap = 1.0 - smoothstep( 0.2, 1.1, from_side )
    warp = rng.normal( 0, 0.03, count )[slate_id] * noise( rng, n, 2.6, 2, 20 )
    cleave = BT.stretched( rng, n, 1.4, 10, 300, ( 6, 0.6 ) )
    height = rise + warp + 0.012 * cleave + 0.004 * noise( rng, n, 1.0, n / 4 ) - 0.07 * bevel - 0.06 * nicks - 0.12 * gap
    cav, tops = cavities( height, 2.5 )
    tone = BT.tones( rng, [ ( 74, 80, 88 ), ( 68, 74, 82 ), ( 76, 82, 84 ), ( 78, 77, 85 ), ( 62, 66, 74 ), ( 72, 78, 84 ) ],
                     count, 0.05 )
    c = BT.shade( tone[slate_id], 1.0 + 0.05 * cleave + 0.03 * noise( rng, n, 1.8, 6, 80 ) )
    c = mix( c, ( 104, 110, 116 ), 0.3 * bevel )                                 # the dressed edge catches the light
    pyrite = dots( rng, n, 40, ( 0.4, 0.9 ) )
    c = mix( c, ( 120, 84, 56 ), 0.6 * wash_down( pyrite, 2.5 * p, 0.6 ) )
    lich_f = noise( rng, n, 2.0, 6, 160 ) + 0.5 * noise( rng, n, 0.8, n / 4 )
    lichen = smoothstep( 1.55, 1.85, lich_f )
    c = mix( c, ( 132, 136, 120 ), 0.55 * lichen )
    orange = smoothstep( 2.35, 2.55, lich_f + 0.5 * noise( rng, n, 1.5, 20, 200 ) )
    c = mix( c, ( 160, 126, 64 ), 0.5 * orange )
    moss = smoothstep( 1.4, 2.2, noise( rng, n, 2.0, 4, 60 ) + 1.4 * ( 1 - smoothstep( 0, 1.2 * p, to_tail ) ) - 0.9 ) * smoothstep( 0.0, 1.2, noise( rng, n, 1.5, 20, 160 ) )
    c = mix( c, ( 64, 76, 38 ), 0.7 * moss )
    height = height + 0.05 * moss + 0.01 * lichen
    c = darken( c, np.exp( -3.0 * cav ) * ( 1 - 0.6 * gap ) )
    rough = np.clip( 0.58 + 0.05 * cleave * 0.5 + 0.3 * lichen + 0.35 * moss + 0.25 * orange + 0.6 * cav, 0, 1 )
    return { "sh_slate_roof": c }, rough, height, 1024 / 128


@texture( "lead" )
def lead( rng, n ):
    """ Lead flashings and ridge rolls, 5.3 px an inch: sheet dressed down over the slates and stone, so it undulates,
    with crisp creases, the dents of the dressing and old knocks. Blue-grey with the white bloom of its carbonate
    patina in patches and washed down in runs, darker where water stands. """
    p = n / 96.0
    height = 0.05 * noise( rng, n, 2.6, 2, 24 ) + 0.006 * noise( rng, n, 1.8, 30, 120 )
    creases = Canvas( n, 2, n // 3 )
    for _ in range( 7 ):
        x, y = rng.uniform( 0, n, 2 )
        a = rng.choice( ( 0.0, math.pi / 2 ) ) + rng.normal( 0, 0.12 )
        L = rng.uniform( 20, 70 ) * p
        creases.line( [ ( x, y ), ( x + math.cos( a ) * L, y + math.sin( a ) * L ) ], rng.uniform( 1.0, 2.0 ) )
    crease = T.blur( creases.result(), 1.0 )
    height += 0.04 * crease
    dents = dots( rng, n, 40, ( 0.6 * p, 2.0 * p ), profile="dome" )
    height -= 0.05 * dents
    mottle = noise( rng, n, 2.2, 2, 40 )
    bloom = smoothstep( 0.0, 1.6, mottle + 0.4 * noise( rng, n, 1.2, 20, 120 ) )
    spots = dots( rng, n, 30, ( 0.5 * p, 1.5 * p ) )
    runs = wash_down( np.clip( spots + smoothstep( 1.6, 2.0, mottle ), 0, 1 ), 14 * p, 1.2, rng )
    c = lum_paint( ( 110, 116, 122 ), 1.0 + 0.03 * noise( rng, n, 1.0, n / 6 ) + 0.03 * mottle )
    c = mix( c, ( 140, 145, 146 ), 0.42 * bloom )
    c = mix( c, ( 184, 186, 184 ), 0.32 * runs )
    c = mix( c, ( 84, 88, 94 ), 0.3 * smoothstep( 0.6, 2.0, -mottle ) )
    c = mix( c, ( 150, 154, 158 ), 0.3 * crease )
    rough = np.clip( 0.58 + 0.12 * bloom + 0.1 * runs - 0.06 * crease, 0, 1 )
    return { "sh_lead": c }, rough, height, 1024 / 96


@texture( "corrugated" )
def corrugated( rng, n ):
    """ Painted corrugated iron (the sheds), 16 px an inch: 3-inch corrugations three-quarters of an inch deep running up
    the picture, 21 to the tile; sheets lapped one and a half corrugations at the sides every seven, and one end lap
    across the tile where the upper sheet comes down over the lower. Nailed through the crests with lead-washered
    nails at the laps and rails, each bleeding rust. The paint chalked and faded on the crests, worn back to
    galvanising in patches, rusting at the laps, the nail holes and the sheets' edges, with a few dents. Paints:
    sh_corrugated_red (red oxide) and sh_corrugated_green. """
    p = n / 64.0
    x, y = coords( n )
    ribs = 21
    pitch = n / ribs
    phase = 2 * np.pi * x / pitch
    profile = 0.375 * np.sin( phase )
    crest = smoothstep( 0.2, 1.0, np.sin( phase ) )
    # Side laps every seven corrugations, the end lap once across the tile.
    lap_x = [ k * 7 * pitch + 0.25 * pitch for k in range( 3 ) ]
    side = np.zeros( ( n, n ) )
    side_edge = np.zeros( ( n, n ) )
    for lx in lap_x:
        d = ( x - lx ) % n
        side = np.maximum( side, ( d < 1.5 * pitch ).astype( float ) )
        side_edge = np.maximum( side_edge, np.exp( -( ( d - 1.5 * pitch + 0.5 ) ** 2 ) / 2.0 ) )
    lap_y = 0.62 * n
    dy = ( y - lap_y ) % n
    over = ( dy > n - 6 * p ).astype( float )                         # the upper sheet's last 6 in, over the lower one
    end_edge = np.exp( -( ( ( y - lap_y + n / 2 ) % n - n / 2 ) ** 2 ) / 2.0 )
    height = profile + 0.035 * ( side + over ) - 0.01 * side_edge - 0.02 * end_edge
    dents = np.zeros( ( n, n ) )
    for _ in range( 5 ):
        r = rng.uniform( 2, 6 ) * p
        stamp( dents, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 0.5, 1.0 ), rng.uniform( 0.3, 1.0 ),
               angle=rng.uniform( 0, 3.2 ), profile="dome" )
    height -= 0.25 * dents
    height += 0.004 * noise( rng, n, 1.2, 40, n / 3 )
    # Nails: through the crests every second corrugation, at the end lap and at a rail half a tile up.
    nails = np.zeros( ( n, n ) )
    washers = np.zeros( ( n, n ) )
    for row_y in ( lap_y - 3 * p, lap_y - 35 * p ):
        for k in range( 0, ribs, 2 ):
            cx = ( k + 0.25 ) * pitch + rng.normal( 0, 0.3 )
            cy = row_y + rng.normal( 0, 0.5 * p )
            stamp( washers, cx, cy, 0.42 * p, 0.42 * p, 1.0, soft=0.8 )
            stamp( nails, cx, cy, 0.2 * p, 0.2 * p, 1.0, profile="dome" )
    height += 0.06 * washers + 0.08 * nails
    mottle = noise( rng, n, 2.2, 2, 30 )
    fine = noise( rng, n, 1.0, n / 6 )
    wear = noise( rng, n, 2.4, 2, 40 ) + 0.4 * noise( rng, n, 1.4, 40, n / 3 )
    bare = smoothstep( 2.05, 2.25, wear + 0.5 * crest )
    rusty = smoothstep( 1.75, 2.0, wear + 0.3 * crest ) * smoothstep( 0.0, 1.0, noise( rng, n, 1.5, 8, 80 ) )
    rust_src = np.clip( 0.9 * side_edge * smoothstep( 0.5, 1.5, noise( rng, n, 1.6, 3, 40 ) ) + end_edge * 0.9 + washers * 0.8
                        + 0.8 * rusty, 0, 1 )
    rust = wash_down( rust_src, 9 * p, 1.5, rng )
    pitting = smoothstep( 1.4, 2.4, noise( rng, n, 1.2, 40, n / 2 ) ) * rust
    height -= 0.01 * pitting
    chalk = smoothstep( -0.6, 1.4, mottle ) * ( 0.5 + 0.5 * crest )

    def painted( base, faded ):
        c = lum_paint( base, 1.0 + 0.04 * fine + 0.05 * mottle )
        c = mix( c, faded, 0.65 * chalk )
        c = mix( c, ( 152, 152, 148 ), 0.9 * bare )
        c = mix( c, mix( ( 112, 62, 38 ), ( 84, 46, 30 ), smoothstep( -1, 1, fine ) ), 0.85 * rust )
        c = mix( c, ( 58, 58, 60 ), 0.9 * washers * ( 1 - nails ) )
        c = mix( c, ( 92, 58, 40 ), nails )
        return darken( c, np.exp( -1.5 * cavities( height, 3.0 )[0] ) )

    red = painted( ( 134, 46, 34 ), ( 160, 96, 84 ) )
    green = painted( ( 52, 90, 70 ), ( 100, 122, 106 ) )
    rough = np.clip( 0.62 + 0.12 * chalk - 0.12 * bare + 0.28 * rust + 0.03 * fine, 0, 1 )
    return { "sh_corrugated_red": red, "sh_corrugated_green": green }, rough, height, 1024 / 64


# ---------------------------------------------------------------------------------------------------------------------
# Ground and floors

@texture( "setts" )
def setts( rng, n ):
    """ Granite setts in the yards, 10.7 px an inch: courses 4.2-5.2 in wide across the way, setts 6-9.5 in long, each
    course breaking joint on the last, joints of grit and sand half an inch wide. A century of iron tyres and boots has
    worn their tops into smooth low domes and rounded their arrises over an inch; the odd one has sunk or rocked out of
    level. The grain (black mica, white quartz, some pinkish feldspar) shows dull through grime and polish. The joints
    stay damp: dark and glossy, with moss in some, and the damp creeps onto the setts' edges. """
    p = n / 96.0
    block, u, v, length, rowh, row, count = BT.coursed( rng, n, ( 4.2 * p, 5.2 * p ), ( 6 * p, 9.5 * p ) )
    du = np.minimum( u, length - u )
    dv = np.minimum( v, rowh - v )
    r = 0.7 * p
    edge = -r * np.log( np.exp( -du / r ) + np.exp( -dv / r ) )                  # rounded corners
    jw = ( 0.24 + 0.07 * noise( rng, n, 1.5, 8, 80 ) ) * p
    inside = smoothstep( jw - 0.7, jw + 0.7, edge )
    into = np.clip( edge - jw, 0, None )
    dome = 1.0 - np.exp( -into / ( 1.1 * p ) )
    sink = rng.normal( 0, 0.07, count )[block]
    tilt = rng.normal( 0, 0.012, ( count, 2 ) ) / p
    lumps = 0.022 * noise( rng, n, 2.2, 20, 200 )
    grain = 0.008 * grain_field( rng, n, 0.6, 3.0 )
    top = sink + tilt[block, 0] * ( u - length / 2 ) + tilt[block, 1] * ( v - rowh / 2 ) + 0.3 * ( dome - 1 ) + lumps + grain
    joint_h = -0.55 + 0.06 * noise( rng, n, 1.2, 30, n / 3 ) + 0.05 * grain_field( rng, n, 0.7, 4.0 )
    height = joint_h * ( 1 - inside ) + inside * np.maximum( top, joint_h + 0.05 )
    black, white, pink = _granite_crystals( rng, n )
    tone = BT.tones( rng, [ ( 122, 118, 114 ), ( 130, 124, 118 ), ( 112, 110, 108 ), ( 136, 126, 118 ), ( 102, 102, 102 ),
                            ( 118, 116, 110 ) ], count, 0.07 )
    pinkish = rng.random( count ) ** 2
    mottle = noise( rng, n, 1.8, 6, 120 )
    c = BT.shade( tone[block], 1.0 + 0.05 * mottle )
    c = mix( c, ( 166, 160, 152 ), 0.35 * white )
    c = mix( c, ( 52, 50, 50 ), 0.45 * black )
    c = mix( c, ( 150, 126, 114 ), 0.3 * pink * pinkish[block] )
    # Polished where the wheels and boots go; grime towards the arrises; oil and dirt in patches.
    polish = smoothstep( 0.35, 0.95, dome ) * smoothstep( -0.6, 1.0, noise( rng, n, 2.0, 2, 16 ) )
    c = mix( c, ( 142, 138, 132 ), 0.16 * polish )
    grime = ( 1 - dome ) * inside
    c = mix( c, ( 70, 66, 60 ), 0.4 * grime )
    c = mix( c, ( 58, 56, 54 ), 0.3 * smoothstep( 0.8, 2.2, noise( rng, n, 2.2, 3, 40 ) ) )
    # The joints: wet grit and sand, moss in some.
    jc = lum_paint( ( 66, 62, 54 ), 1.0 + 0.15 * noise( rng, n, 1.0, n / 6 ) + 0.1 * noise( rng, n, 1.6, 20, 120 ) )
    moss = smoothstep( 0.6, 1.6, noise( rng, n, 2.0, 4, 60 ) ) * smoothstep( -0.5, 1.5, noise( rng, n, 1.2, 40, n / 2 ) )
    jc = mix( jc, ( 60, 80, 34 ), 0.75 * moss )
    c = mix( jc, c, inside )
    cav, tops = cavities( height, 2.5 )
    c = darken( c, np.exp( -1.2 * cav ) )
    damp = ( 1 - inside ) + 0.6 * smoothstep( 0.6 * p, 0.0, into ) * inside
    c = darken( c, 1.0 - 0.25 * damp )
    rough = np.clip( ( 0.66 - 0.16 * polish + 0.1 * grime + 0.02 * mottle ) * ( 1 - 0.35 * damp * inside ), 0, 1 ) * inside \
        + ( 0.4 + 0.25 * moss ) * ( 1 - inside )
    return { "sh_setts": c }, rough, height, 1024 / 96


@texture( "tarmac" )
def tarmac( rng, n ):
    """ Worn road tarmac, 4 px an inch: the black binder weathered dull grey and worn off the chippings' tops, so the grey
    and pinkish stone shows through in a fine speckle, greyest in broad patches; two dug-out-and-filled repairs of
    darker, newer tarmac, their saw-cut edges sealed under a band of bitumen worn through in places; cracks, some
    sealed the same way, some with grass in them; oil drips; pale silt where the puddles stand. """
    p = n / 256.0
    x, y = coords( n )
    fine = noise( rng, n, 1.0, n / 6 )
    undulate = noise( rng, n, 3.0, 1, 12 )
    # The chippings, a fifth to half an inch, standing in the binder.
    grit = unit( T.blur( rng.random( ( n, n ) ), 0.7 ) )
    chips = smoothstep( 0.2, 1.0, grit + 0.35 * fine )
    age = smoothstep( -1.8, 1.8, 0.8 * noise( rng, n, 2.4, 1, 10 ) + 0.35 * noise( rng, n, 1.5, 10, 60 ) )
    stone = mix( ( 112, 110, 106 ), ( 146, 134, 124 ),
                 smoothstep( -0.8, 1.4, unit( T.blur( rng.random( ( n, n ) ), 1.2 ) ) ) )
    binder = mix( ( 44, 44, 46 ), ( 66, 66, 67 ), age )
    c = mix( binder, stone, chips * ( 0.42 + 0.33 * age ) )
    c = mix( c, ( 92, 88, 82 ), 0.12 * smoothstep( -0.5, 1.5, noise( rng, n, 1.8, 6, 80 ) ) )        # dust
    height = 0.12 * undulate + 0.03 * chips + 0.006 * fine
    # Repairs: newer tarmac in saw-cut rectangles, a little proud, the cut sealed with a band of bitumen.
    patch = np.zeros( ( n, n ) )
    seal = np.zeros( ( n, n ) )
    jag = 0.5 * p * noise( rng, n, 1.8, 20, 200 )
    worn_band = 0.55 + 0.45 * smoothstep( -0.6, 0.8, noise( rng, n, 1.4, 4, 40 ) )
    for _ in range( 2 ):
        w, h = rng.uniform( 40, 90 ) * p, rng.uniform( 30, 70 ) * p
        _, edge = _rect_wrap( x, y, rng.uniform( 0, n ), rng.uniform( 0, n ), w, h, n )
        e = edge + jag
        patch = np.maximum( patch, smoothstep( -0.6, 0.6, e ) )
        seal = np.maximum( seal, smoothstep( 1.3 * p, 0.8 * p, np.abs( e - 0.2 * p ) ) * worn_band )
    newer = mix( ( 40, 40, 42 ), stone, 0.22 * chips )
    newer = mix( newer, ( 58, 58, 59 ), 0.35 * smoothstep( -1.0, 1.5, noise( rng, n, 2.0, 2, 30 ) ) )
    c = mix( c, newer, patch )
    height += 0.05 * patch
    # Cracks running across the road: open ones with dirt and grass, and sealed ones under a band of bitumen.
    open_c = crack_lines( rng, n, 7, ( 60 * p, 180 * p ), 0.9, branch=0.5, turn=0.1, pull=0.06 ) * ( 1 - patch )
    sealed_line = crack_lines( rng, n, 4, ( 60 * p, 180 * p ), 1.0, branch=0.3, turn=0.1, pull=0.06 )
    seal = np.maximum( seal, smoothstep( 0.03, 0.07, T.blur( sealed_line, 1.0 * p ) ) * worn_band )
    grass = open_c * smoothstep( 0.7, 1.5, noise( rng, n, 1.6, 6, 60 ) )
    tufts = smoothstep( 0.02, 0.06, T.blur( grass, 1.4 * p ) ) * smoothstep( -0.4, 0.9, noise( rng, n, 0.8, n / 8 ) )
    c = mix( c, ( 34, 32, 30 ), 0.75 * open_c )
    c = mix( c, mix( ( 58, 80, 32 ), ( 92, 112, 50 ), smoothstep( -1, 1, noise( rng, n, 0.9, n / 6 ) ) ), 0.85 * tufts )
    height -= 0.12 * open_c
    height += 0.12 * tufts
    c = mix( c, mix( ( 26, 26, 27 ), ( 36, 36, 37 ), smoothstep( -1, 1, fine ) ), 0.88 * seal )
    height += 0.03 * seal
    # Oil drips and the silt left where puddles dried.
    oil = blotches( rng, n, 2.4, 2, 30, 0.03, soft=0.7 ) * smoothstep( -0.6, 1.0, noise( rng, n, 1.5, 10, 80 ) )
    c = darken( c, 1.0 - 0.35 * oil )
    silt = smoothstep( 0.9, 1.7, -undulate ) * smoothstep( -0.8, 1.0, noise( rng, n, 1.6, 8, 80 ) ) * ( 1 - seal )
    c = mix( c, ( 116, 110, 98 ), 0.3 * silt )
    c = darken( c, np.exp( -2.0 * cavities( height, 1.5 )[0] ) )
    rough = np.clip( 0.86 + 0.04 * fine - 0.12 * age * chips - 0.35 * seal - 0.25 * oil - 0.06 * patch + 0.05 * silt
                     + 0.05 * tufts, 0, 1 )
    return { "sh_tarmac": c }, rough, height, 1024 / 256


@texture( "concrete" )
def concrete( rng, n ):
    """ Cast concrete aprons and floors, 5.3 px an inch: bays sixteen feet square (the tile) between sawn joints, a
    wood-floated finish worn in places to the sand and fine aggregate, the pour's light and dark clouds, pop-outs,
    hairline cracks, rust stains under old ironwork, an oil stain or two, dirt in the joints and hollows, a little green
    where it stays damp, and a faint white bloom of lime where water has seeped from the cracks. """
    p = n / 192.0
    x, y = coords( n )
    jd = np.minimum( np.minimum( x, n - x ), np.minimum( y, n - y ) )
    joint = smoothstep( 0.18 * p + 0.6, 0.18 * p - 0.6, jd )
    spall = smoothstep( 1.8, 2.3, noise( rng, n, 1.5, 20, 200 ) ) * smoothstep( 1.4 * p, 0.2 * p, jd )
    fine = noise( rng, n, 1.0, n / 6 )
    clouds = noise( rng, n, 2.2, 1, 16 )
    float_marks = BT.stretched( rng, n, 1.5, 6, 120, ( 1.5 * p, 6 * p ) )
    wear = smoothstep( -0.2, 1.6, noise( rng, n, 2.4, 1, 10 ) )
    agg = smoothstep( 1.0, 1.6, unit( T.blur( rng.random( ( n, n ) ), 0.8 ) ) ) * wear
    pops = dots( rng, n, 30, ( 0.3 * p, 0.7 * p ) )
    cracks = crack_lines( rng, n, 6, ( 40 * p, 120 * p ), 0.8, branch=0.4, turn=0.1, pull=0.06 )
    height = 0.06 * noise( rng, n, 2.6, 1, 20 ) + 0.006 * fine + 0.004 * float_marks + 0.02 * agg - 0.08 * pops \
        - 0.06 * cracks - 0.35 * joint - 0.15 * spall
    c = lum_paint( ( 152, 149, 142 ), 1.0 + 0.06 * clouds + 0.02 * fine + 0.012 * float_marks )
    c = mix( c, mix( ( 120, 114, 104 ), ( 160, 154, 144 ), smoothstep( -1, 1, unit( T.blur( rng.random( ( n, n ) ), 1.0 ) ) ) ),
             0.6 * agg )
    c = mix( c, ( 96, 92, 86 ), 0.7 * pops )
    # Stains: rust under ironwork, oil, dirt in the hollows, green damp, lime bloom.
    rust_src = np.zeros( ( n, n ) )
    for _ in range( 3 ):
        stamp( rust_src, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 2, 6 ) * p, rng.uniform( 1, 3 ) * p, 1.0,
               angle=rng.uniform( 0, 3.2 ), soft=3 * p )
    rust = np.clip( T.blur( rust_src, 2.5 * p ) * 1.4, 0, 1 ) * smoothstep( -1.0, 1.0, noise( rng, n, 1.6, 10, 80 ) )
    c = mix( c, ( 150, 96, 58 ), 0.5 * rust )
    oil = blotches( rng, n, 2.6, 1, 20, 0.025, soft=0.8 ) * smoothstep( -0.5, 1.0, noise( rng, n, 1.5, 8, 60 ) )
    c = darken( c, 1.0 - 0.3 * oil )
    dirt = smoothstep( 0.4, 1.8, -noise( rng, n, 2.6, 1, 20 ) )
    c = mix( c, ( 110, 104, 94 ), 0.3 * dirt )
    damp = smoothstep( 1.0, 2.2, noise( rng, n, 2.4, 1, 16 ) + 1.2 * smoothstep( 6 * p, 0, jd ) )
    c = mix( c, ( 116, 124, 98 ), 0.3 * damp )
    bloom = smoothstep( 0.01, 0.05, T.blur( cracks + joint, 1.5 * p ) ) * smoothstep( 0.0, 1.4, noise( rng, n, 1.6, 6, 80 ) )
    c = mix( c, ( 196, 194, 186 ), 0.15 * bloom )
    c = mix( c, ( 66, 62, 56 ), 0.85 * joint )
    c = mix( c, ( 120, 116, 108 ), 0.5 * spall )
    c = mix( c, ( 64, 60, 56 ), 0.6 * cracks )
    c = darken( c, np.exp( -3.0 * cavities( height, 2.0 )[0] ) )
    rough = np.clip( 0.86 + 0.03 * fine - 0.08 * wear - 0.25 * oil + 0.03 * bloom - 0.06 * damp, 0, 1 )
    return { "sh_concrete": c }, rough, height, 1024 / 192


@texture( "floor_tiles" )
def floor_tiles( rng, n ):
    """ Red quarry tiles (the Still House floor), 8 px an inch: tiles six inches and a bit (ten to the tile) set square
    in grey-brown cement joints a quarter of an inch wide, each tile its own shade of fired red, darker where the kiln
    flashed it; their faces waxed and polished by boots along the walkways and dull elsewhere, chipped at the edges to
    the paler body, a few cracked; pores, dirt in the joints and a dark spill or two. """
    p = n / 64.0
    x, y = coords( n )
    k = 10
    s = n / k
    tx, ty = np.floor( x / s ).astype( int ), np.floor( y / s ).astype( int )
    tid = ty * k + tx
    u, v = x - tx * s, y - ty * s
    edge = np.minimum( np.minimum( u, s - u ), np.minimum( v, s - v ) )
    jw = 0.13 * p
    inside = smoothstep( jw - 0.5, jw + 0.5, edge )
    bevel = smoothstep( jw, jw + 0.3 * p, edge )
    count = k * k
    tone = BT.tones( rng, [ ( 150, 62, 42 ), ( 140, 58, 40 ), ( 158, 70, 46 ), ( 132, 56, 40 ), ( 146, 66, 48 ),
                            ( 124, 52, 38 ) ], count, 0.05 )
    mottle = noise( rng, n, 1.8, 4, 120 )
    flash = smoothstep( 0.3, 1.8, noise( rng, n, 2.0, 4, 60 ) ) * ( rng.random( count ) ** 1.5 )[tid]
    c = BT.shade( tone[tid], 1.0 + 0.07 * mottle + 0.03 * noise( rng, n, 1.0, n / 4 ) )
    c = mix( c, ( 88, 36, 28 ), 0.5 * flash )
    pores = smoothstep( 2.3, 2.8, unit( T.blur( rng.random( ( n, n ) ), 0.6 ) ) )
    c = mix( c, ( 92, 40, 30 ), 0.6 * pores )
    walk = smoothstep( -0.4, 1.2, noise( rng, n, 2.4, 1, 6 ) )
    c = mix( c, ( 120, 50, 36 ), 0.18 * walk )                                 # waxed and polished: deeper red
    dull = ( 1 - walk ) * smoothstep( -0.5, 1.5, noise( rng, n, 1.8, 6, 60 ) )
    c = mix( c, ( 156, 104, 90 ), 0.18 * dull )                                # dried bloom on the unwalked tiles
    chips = smoothstep( 1.7, 2.1, noise( rng, n, 1.4, 20, 200 ) ) * smoothstep( 0.7 * p, 0.1 * p, edge ) * inside
    c = mix( c, ( 186, 120, 96 ), 0.8 * chips )
    # A few tiles cracked right across, edge to edge.
    canvas = Canvas( n, 2, 0 )
    for t in np.flatnonzero( rng.random( count ) < 0.07 ):
        x0, y0 = ( t % k ) * s, ( t // k ) * s
        sides = rng.choice( 4, 2, replace=False )
        ends = []
        for side in sides:
            a = rng.uniform( 0.2, 0.8 ) * s
            ends.append( ( ( a, 0.0 ), ( s, a ), ( a, s ), ( 0.0, a ) )[side] )
        pts = [ ( x0 + ends[0][0] + ( ends[1][0] - ends[0][0] ) * f + rng.normal( 0, 0.06 * s ) * ( 0 < f < 1 ),
                  y0 + ends[0][1] + ( ends[1][1] - ends[0][1] ) * f + rng.normal( 0, 0.06 * s ) * ( 0 < f < 1 ) )
                for f in np.linspace( 0, 1, 7 ) ]
        canvas.line( pts, 0.8 )
    crack = canvas.result() * inside
    c = mix( c, ( 50, 26, 22 ), 0.8 * crack )
    spill = blotches( rng, n, 2.0, 3, 40, 0.04, soft=0.4 )
    c = darken( c, 1.0 - 0.35 * spill )
    joint_c = lum_paint( ( 104, 96, 86 ), 1.0 + 0.12 * noise( rng, n, 1.0, n / 6 ) )
    joint_c = mix( joint_c, ( 62, 54, 46 ), 0.4 * smoothstep( -0.5, 1.5, noise( rng, n, 1.8, 6, 60 ) ) )
    c = mix( joint_c, c, inside )
    c = darken( c, 0.82 + 0.18 * bevel )
    height = -0.18 * ( 1 - inside ) + inside * ( -0.07 * ( 1 - bevel ) - 0.025 * pores - 0.06 * chips - 0.03 * crack
                                                + 0.004 * mottle )
    rough = np.clip( ( 0.62 - 0.22 * walk + 0.12 * dull + 0.2 * chips - 0.2 * spill ) * inside + 0.88 * ( 1 - inside ), 0, 1 )
    return { "sh_floor_tiles": c }, rough, height, 1024 / 64


@texture( "floorboards" )
def floorboards( rng, n ):
    """ Pine floorboards, 8 px an inch, running up the picture (GRAIN): boards 5.5-7 in wide, each in lengths with butt
    joints, the grain of each length its own (flat-sawn cathedral figures and straight rift), a few knots, pairs of cut
    nails over the joists every sixteen inches. Old varnish worn grey-brown along the walkways, dirt in the gaps, the
    boards a little cupped. """
    p = n / 128.0
    x, y = coords( n )
    widths = []
    while sum( widths ) < n:
        widths.append( rng.uniform( 5.5 * p, 7.0 * p ) )
    widths = np.array( widths ) * n / sum( widths )
    edges = np.concatenate( ( [ 0.0 ], np.cumsum( widths ) ) )
    board = np.clip( np.searchsorted( edges, x, side="right" ) - 1, 0, len( widths ) - 1 )
    u = x - edges[board]
    w = widths[board]
    piece = np.zeros( ( n, n ), int )
    dy = np.full( ( n, n ), float( n ) )
    count = 0
    for b in range( len( widths ) ):
        cols = slice( int( round( edges[b] ) ), int( round( edges[b + 1] ) ) )
        joints = np.sort( rng.uniform( 0, n, int( rng.integers( 1, 3 ) ) ) )
        yy = y[:, cols]
        k = np.searchsorted( joints, yy ) % len( joints )
        piece[:, cols] = count + k
        d = np.min( [ np.abs( ( yy - j + n / 2 ) % n - n / 2 ) for j in joints ], axis=0 )
        dy[:, cols] = d
        count += len( joints )
    # Each length's grain: rings cut by the board's face, r = sqrt( ( u - c )^2 + ( depth + wave )^2 ).
    c0 = rng.uniform( -0.4, 1.4, count )[piece] * w
    depth = rng.uniform( 1.5, 7.0, count )[piece] * p
    amp = rng.uniform( 0.5, 3.0, count )[piece] * p
    m = rng.integers( 1, 3, count )[piece]
    phi = rng.uniform( 0, 2 * math.pi, count )[piece]
    spacing = rng.uniform( 0.22, 0.4, count )[piece] * p
    warp = 0.6 * p * noise( rng, n, 2.6, 2, 30 )
    rr = np.sqrt( ( u - c0 ) ** 2 + ( depth + amp * np.sin( 2 * np.pi * m * y / n + phi ) ) ** 2 ) + warp
    phase = rr / spacing
    ring = phase % 1.0
    late = smoothstep( 0.62, 0.8, ring ) * ( 1 - smoothstep( 0.9, 1.0, ring ) )
    # Where the rings crowd closer than the pixels can show (rift-sawn), they fade to their average.
    gy, gx = np.gradient( phase )
    crowd = smoothstep( 0.42, 0.22, np.hypot( gx, gy ) )
    late = late * crowd + 0.26 * ( 1 - crowd )
    # Knots.
    knots = np.zeros( ( n, n ) )
    for _ in range( 6 ):
        r = rng.uniform( 0.35, 0.7 ) * p
        stamp( knots, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 1.1, 1.6 ), 1.0, soft=0.6 * p )
    halo = np.clip( T.blur( knots, 1.2 * p ) * 1.5, 0, 1 ) - knots
    late = np.clip( late + 0.6 * halo, 0, 1 )
    tone = rng.uniform( 0.86, 1.12, count )[piece]
    c = BT.shade( np.broadcast_to( np.array( ( 150, 112, 70 ), float ), ( n, n, 3 ) ), tone * ( 1.0 + 0.02 * noise( rng, n, 1.0, n / 4 ) ) )
    c = mix( c, ( 104, 70, 40 ), 0.55 * late )
    c = mix( c, ( 70, 44, 26 ), 0.9 * knots )
    # Nails over the joists.
    nails = np.zeros( ( n, n ) )
    for jy in ( np.arange( 8 ) + 0.5 ) * 16 * p:
        for b in range( len( widths ) ):
            for side in ( 0.8 * p, widths[b] - 0.8 * p ):
                stamp( nails, edges[b] + side + rng.normal( 0, 0.1 * p ), jy + rng.normal( 0, 0.15 * p ), 0.11 * p,
                       0.09 * p, 1.0, soft=0.5 )
    stain = np.clip( T.blur( nails, 0.5 * p ) * 2.5, 0, 1 )
    c = mix( c, ( 64, 52, 42 ), 0.4 * stain )
    c = mix( c, ( 34, 30, 28 ), nails )
    # Wear: the varnish worn off greyer along the walkways; grime along the gaps.
    walk = smoothstep( -0.5, 1.4, noise( rng, n, 2.4, 1, 8 ) )
    c = mix( c, ( 132, 112, 88 ), 0.3 * walk )
    near_gap = np.exp( -np.minimum( u, w - u ) / ( 0.5 * p ) ) + np.exp( -dy / ( 0.5 * p ) )
    c = mix( c, ( 60, 44, 30 ), 0.3 * np.clip( near_gap, 0, 1 ) )
    gap = smoothstep( 0.1 * p, 0.0, np.minimum( u, w - u ) ) + smoothstep( 0.08 * p, 0.0, dy )
    gap = np.clip( gap, 0, 1 )
    c = mix( c, ( 26, 20, 16 ), 0.9 * gap )
    cup = 0.025 * ( ( u - w / 2 ) / ( w / 2 ) ) ** 2
    height = cup - 0.008 * ( 1 - late ) * walk - 0.2 * gap - 0.02 * knots + 0.015 * nails
    rough = np.clip( 0.6 + 0.12 * walk + 0.15 * late * walk - 0.1 * ( 1 - walk ) + 0.3 * gap, 0, 1 )
    return { "sh_floorboards": c }, rough, height, 1024 / 128


@texture( "dunnage" )
def dunnage( rng, n ):
    """ A dunnage warehouse's floor, 5.3 px an inch: earth and cinders trodden hard over a century, dark and damp (the
    warehouses are kept cool and humid): clinker and ash in a dark brown-black matrix, small stones, flakes of rust and
    bits of oak and wicker from the casks, grey ash where it's dry; pressed smooth, darker and a little glossy along
    the two lanes up the picture where the casks are rolled, and where it's walked. """
    p = n / 192.0
    x, y = coords( n )
    lumps = noise( rng, n, 2.4, 2, 40 )
    worn = smoothstep( -0.4, 1.4, noise( rng, n, 2.6, 1, 8 ) )
    # The rolling lanes: the casks' chimes run in two pairs of ruts about a cask's length apart.
    lane = np.zeros( ( n, n ) )
    wobble = 2.5 * p * noise( rng, n, 2.5, 1, 6 )
    for x0 in rng.uniform( 0, n, 1 ) + np.array( ( 0.0, n / 2 ) ):
        for side in ( -11.0, 11.0 ):
            dx = np.abs( ( x - x0 - side * p + wobble + n / 2 ) % n - n / 2 )
            lane = np.maximum( lane, smoothstep( 4.0 * p, 1.5 * p, dx ) )
    lane *= 0.75 + 0.25 * smoothstep( -0.8, 0.8, noise( rng, n, 1.5, 4, 40 ) )
    worn = np.maximum( worn, lane )
    height = ( 0.12 - 0.07 * worn ) * lumps + 0.03 * noise( rng, n, 1.6, 40, 200 ) - 0.15 * lane
    # Clinker: porous lumps of slag, a quarter to three-quarters of an inch.
    pts = jittered( rng, n, 0.85 * p, 0.45 )
    pts = pts[rng.random( len( pts ) ) < 0.5]
    rad = rng.uniform( 0.14, 0.4, len( pts ) ) * p
    who, d, _ = packed( rng, n, pts, rad )
    clinker = smoothstep( 1.0, 0.75, d ) * ( 1 - 0.6 * worn )
    dome = np.sqrt( np.clip( 1 - d * d, 0, 1 ) )
    kinds = T.pick( rng, [ ( 4, ( 50, 48, 48 ) ), ( 3, ( 68, 64, 60 ) ), ( 3, ( 38, 36, 36 ) ), ( 1, ( 92, 68, 50 ) ),
                           ( 2, ( 92, 90, 86 ) ) ], len( pts ) )
    pore = smoothstep( 0.8, 1.4, unit( T.blur( rng.random( ( n, n ) ), 0.6 ) ) )
    clinker_c = BT.shade( kinds[who], ( 0.85 + 0.25 * dome ) * ( 1 - 0.45 * pore ) )
    height = height + clinker * ( 0.06 + 0.1 * dome * rad[who] / p )
    # Small stones.
    pts2 = jittered( rng, n, 2.2 * p, 0.5 )
    pts2 = pts2[rng.random( len( pts2 ) ) < 0.35]
    rad2 = rng.uniform( 0.2, 0.5, len( pts2 ) ) * p
    who2, d2, _ = packed( rng, n, pts2, rad2 )
    pebble = smoothstep( 1.0, 0.8, d2 ) * ( 1 - 0.5 * lane )
    dome2 = np.sqrt( np.clip( 1 - d2 * d2, 0, 1 ) )
    pebble_c = BT.shade( BT.tones( rng, [ ( 104, 98, 90 ), ( 88, 84, 80 ), ( 118, 108, 96 ) ], len( pts2 ), 0.1 )[who2],
                         0.8 + 0.3 * dome2 )
    height = height + pebble * 0.25 * dome2 * ( 1 - 0.6 * lane )
    # The earth matrix, ash grey where it's dry, damp and dark in others.
    earth = lum_paint( ( 56, 48, 40 ), 1.0 + 0.12 * noise( rng, n, 1.8, 4, 100 ) + 0.06 * noise( rng, n, 1.0, n / 4 ) )
    ash = smoothstep( 0.4, 1.6, noise( rng, n, 2.2, 2, 30 ) ) * ( 1 - lane )
    earth = mix( earth, ( 96, 92, 86 ), 0.45 * ash )
    c = mix( earth, clinker_c, clinker )
    c = mix( c, pebble_c, pebble )
    # Bits from the casks: slivers of oak and wicker, flakes of rust.
    bits = np.zeros( ( n, n ) )
    bits_rust = np.zeros( ( n, n ) )
    for _ in range( 160 ):
        stamp( bits, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.5, 1.6 ) * p, rng.uniform( 0.14, 0.24 ) * p,
               1.0, angle=rng.uniform( 0, 3.2 ), soft=0.6 )
    for _ in range( 90 ):
        stamp( bits_rust, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.15, 0.4 ) * p,
               rng.uniform( 0.1, 0.3 ) * p, 1.0, angle=rng.uniform( 0, 3.2 ), soft=0.6 )
    bits *= 1 - 0.7 * lane
    c = mix( c, mix( ( 112, 86, 60 ), ( 84, 62, 42 ), smoothstep( -1, 1, noise( rng, n, 1.0, n / 6 ) ) ), 0.8 * bits )
    c = mix( c, ( 96, 56, 34 ), 0.8 * bits_rust )
    height = height + 0.04 * bits + 0.02 * bits_rust
    damp = smoothstep( -0.2, 1.6, noise( rng, n, 2.6, 1, 12 ) ) * ( 1 - 0.6 * ash )
    c = darken( c, ( 1.0 - 0.3 * damp ) * ( 1.0 - 0.15 * worn ) * ( 1.0 - 0.15 * lane ) )
    c = darken( c, np.exp( -2.0 * cavities( height, 2.0 )[0] ) )
    rough = np.clip( 0.84 - 0.2 * damp - 0.16 * worn - 0.12 * lane + 0.06 * clinker + 0.06 * ash, 0, 1 )
    return { "sh_dunnage": c }, rough, height, 1024 / 192


@texture( "grating" )
def grating( rng, n ):
    """ Open steel floor grating (the galleries), 10.7 px an inch, drawn opaque: galvanised bearing bars three-
    sixteenths of an inch thick on edge at 1.2-inch centres, running up the picture, twisted cross rods at 4-inch
    centres, and between them the dark of the floor below, with a little of the bars' sides lit. The bars' tops worn
    bright by boots, the zinc dull and spangled between, rust where it's worn through, dirt packed at the joints. """
    p = n / 48.0
    x, y = coords( n )
    pb, pc = n / 40.0, n / 12.0
    db = np.abs( ( x % pb ) - pb / 2 )
    dc = np.abs( ( y % pc ) - pc / 2 )
    tb, tc = 0.094 * p, 0.13 * p
    bar = smoothstep( tb + 0.5, tb - 0.5, db )
    rod = smoothstep( tc + 0.5, tc - 0.5, dc ) * ( 1 - bar )
    side = np.exp( -np.clip( db - tb, 0, None ) / ( 0.1 * p ) ) * ( 1 - bar ) * ( 1 - rod )
    twist = 0.5 + 0.5 * np.sin( 2 * np.pi * x / ( pb / 3 ) )
    junction = bar * smoothstep( tc + 0.6 * p, tc, dc )
    spangle = noise( rng, n, 0.8, n / 8 ) + 0.5 * noise( rng, n, 1.6, 10, 80 )
    zinc = lum_paint( ( 150, 152, 150 ), 1.0 + 0.06 * spangle )
    worn = smoothstep( -0.8, 1.2, noise( rng, n, 2.2, 1, 12 ) )
    top = mix( zinc, ( 178, 180, 178 ), 0.5 * worn )
    rust = smoothstep( 1.2, 1.9, noise( rng, n, 1.8, 3, 40 ) )
    top = mix( top, ( 120, 72, 44 ), 0.6 * rust )
    rod_c = BT.shade( np.broadcast_to( np.array( ( 132, 134, 132 ), float ), ( n, n, 3 ) ), 0.8 + 0.35 * twist )
    rod_c = mix( rod_c, ( 112, 70, 44 ), 0.5 * rust )
    below = lum_paint( ( 24, 24, 24 ), 1.0 + 0.25 * noise( rng, n, 2.0, 2, 30 ) )
    c = mix( below, ( 70, 72, 72 ), 0.55 * side )
    c = mix( c, rod_c, rod )
    c = mix( c, top, bar )
    c = mix( c, ( 66, 60, 52 ), 0.5 * junction * smoothstep( -0.5, 1.0, noise( rng, n, 1.5, 10, 100 ) ) )
    height = -1.5 * ( 1 - np.maximum( bar, rod ) ) - 0.12 * rod + 0.004 * spangle * bar
    rough = np.clip( ( 0.42 - 0.12 * worn + 0.4 * rust ) * bar + ( 0.55 + 0.3 * rust ) * rod + 0.95 * ( 1 - bar - rod ), 0, 1 )
    return { "sh_grating": c }, rough, height, 1024 / 48


@texture( "chequer" )
def chequer( rng, n ):
    """ Steel chequer plate (the stillmen's platforms, covers and steps), 10.7 px an inch: raised lugs an inch long on a
    1.2-inch grid, each at right angles to its neighbours. Grey mill-scaled steel, the lugs' tops worn bright and
    smooth, dirt in the flats, a little brown rust where water stands, scuffs. """
    p = n / 48.0
    x, y = coords( n )
    k = 40
    s = n / k
    i, j = np.floor( x / s ), np.floor( y / s )
    cx, cy = x - ( i + 0.5 ) * s, y - ( j + 0.5 ) * s
    sign = np.where( ( i + j ) % 2 == 0, 1.0, -1.0 )
    cs, sn = math.cos( math.pi / 4 ), math.sin( math.pi / 4 )
    lu = cx * cs + cy * sn * sign
    lv = -cx * sn * sign + cy * cs
    half, wid = 0.45 * p, 0.11 * p
    d = np.hypot( np.clip( np.abs( lu ) - ( half - wid ), 0, None ), lv ) - wid
    lug = smoothstep( 0.6, -0.6, d )
    lug_h = 0.07 * np.sqrt( np.clip( -d / wid, 0, 1 ) )
    mottle = noise( rng, n, 2.2, 2, 30 )
    fine = noise( rng, n, 1.0, n / 6 )
    scale = smoothstep( -0.2, 1.4, noise( rng, n, 1.8, 4, 60 ) )
    plate = lum_paint( ( 122, 124, 126 ), 1.0 + 0.05 * mottle + 0.03 * fine )
    plate = mix( plate, ( 100, 102, 104 ), 0.35 * scale )
    worn = smoothstep( -0.6, 1.4, noise( rng, n, 2.4, 1, 10 ) )
    tops = mix( plate, ( 176, 178, 178 ), lug * ( 0.35 + 0.5 * worn ) * smoothstep( 0.0, 0.05, lug_h ) )
    dirt = smoothstep( -0.2, 1.6, noise( rng, n, 2.0, 2, 30 ) ) * ( 1 - lug )
    c = mix( tops, ( 84, 80, 74 ), 0.45 * dirt )
    rust = smoothstep( 1.5, 2.3, noise( rng, n, 2.0, 2, 40 ) + 0.3 * fine ) * ( 1 - 0.8 * lug * worn )
    c = mix( c, mix( ( 110, 70, 44 ), ( 84, 52, 34 ), smoothstep( -1, 1, fine ) ), 0.6 * rust )
    scuffs = smoothstep( 1.8, 2.6, BT.stretched( rng, n, 1.2, 8, 160, ( 0.5, 8 ) ) )
    c = mix( c, ( 150, 152, 152 ), 0.25 * scuffs * ( 1 - rust ) )
    height = lug_h * lug + 0.004 * mottle - 0.01 * rust * fine
    c = darken( c, np.exp( -4.0 * cavities( height, 1.5 )[0] ) )
    rough = np.clip( 0.5 - 0.18 * lug * worn + 0.12 * dirt + 0.35 * rust + 0.05 * scale, 0, 1 )
    return { "sh_chequer": c }, rough, height, 1024 / 48


def _stones( n, pts, rx, ry, ang, lift, thick, k=10 ):
    """ Flattened round stones lying over each other: ellipses rx x ry px turned by ang, each lift + thick x a flat
    dome inches high, every px showing the highest stone over it. Returns per px ( the stone (-1 where none), its
    elliptical distance from the stone's centre (1 at its edge, 9 where none), the offset along and across the stone
    over its radii, the height (-inf where none) ). """
    pts = np.asarray( pts, float ) % n
    tree = cKDTree( pts, boxsize=n )
    x, y = coords( n )
    q = np.stack( [ x.ravel(), y.ravel() ], -1 )
    _, idx = tree.query( q, k=k, workers=-1 )
    best_h = np.full( len( q ), -np.inf )
    best = np.full( len( q ), -1 )
    best_e = np.full( len( q ), 9.0 )
    best_u = np.zeros( len( q ) )
    best_v = np.zeros( len( q ) )
    ca, sa = np.cos( ang ), np.sin( ang )
    for j in range( k ):
        i = idx[:, j]
        off = ( q - pts[i] + n / 2 ) % n - n / 2
        eu = ( off[:, 0] * ca[i] + off[:, 1] * sa[i] ) / rx[i]
        ev = ( -off[:, 0] * sa[i] + off[:, 1] * ca[i] ) / ry[i]
        e = np.hypot( eu, ev )
        h = np.where( e < 1, lift[i] + thick[i] * np.clip( 1 - np.clip( e, 0, 1 ) ** 3, 0, 1 ) ** ( 1 / 3 ), -np.inf )
        better = h > best_h
        best_h = np.where( better, h, best_h )
        best = np.where( better, i, best )
        best_e = np.where( better, e, best_e )
        best_u = np.where( better, eu, best_u )
        best_v = np.where( better, ev, best_v )
    shape = ( n, n )
    return ( best.reshape( shape ), best_e.reshape( shape ), best_u.reshape( shape ), best_v.reshape( shape ),
             best_h.reshape( shape ) )


@texture( "shingle" )
def shingle( rng, n ):
    """ Beach shingle, 8 px an inch: pebbles an inch to four across, rounded and flattened by the sea, packed on smaller
    gravel and grit. Grey quartzite, white quartz, dark dolerite, green-grey schist, pink granite, brown sandstone and
    banded gneiss, some with quartz veins; dry and dull, darker and damp in the hollows between. """
    p = n / 128.0
    # The gravel bed under them.
    g_pts = jittered( rng, n, 0.7 * p, 0.5 )
    g_rad = rng.uniform( 0.25, 0.45, len( g_pts ) ) * p
    g_who, g_d, _ = packed( rng, n, g_pts, g_rad )
    g_in = smoothstep( 1.0, 0.85, g_d )
    g_dome = np.sqrt( np.clip( 1 - g_d * g_d, 0, 1 ) )
    g_tone = BT.tones( rng, [ ( 120, 116, 110 ), ( 96, 94, 90 ), ( 140, 132, 122 ), ( 110, 104, 96 ) ], len( g_pts ), 0.12 )
    grit = lum_paint( ( 84, 78, 70 ), 1.0 + 0.2 * noise( rng, n, 1.0, n / 6 ) )
    g_col = mix( grit, BT.shade( g_tone[g_who], 0.75 + 0.35 * g_dome ), g_in )
    g_h = -0.6 + g_in * 0.3 * g_dome
    # The pebbles: flattened ellipses of lognormal sizes, each turned its own way, lying over each other.
    pts = jittered( rng, n, 2.1 * p, 0.5 )
    m = len( pts )
    size = np.exp( rng.normal( 0, 0.33, m ) )
    rx = 1.0 * p * size * rng.uniform( 1.0, 1.45, m )
    ry = rx * rng.uniform( 0.55, 0.9, m )
    ang = rng.uniform( 0, math.pi, m )
    thick = rng.uniform( 0.35, 0.6, m ) * np.sqrt( rx * ry ) / p
    lift = rng.uniform( -0.25, 0.2, m )
    who, e, eu, ev, h_peb = _stones( n, pts, rx, ry, ang, lift, thick )
    who = np.maximum( who, 0 )
    peb = smoothstep( 1.0, 0.92, e )
    dome = np.clip( 1 - np.clip( e, 0, 1 ) ** 3, 0, 1 ) ** ( 1 / 3 )
    kind = rng.choice( 7, size=m, p=( 0.28, 0.1, 0.15, 0.12, 0.1, 0.1, 0.15 ) )
    base_c = np.array( [ ( 150, 148, 142 ), ( 206, 204, 196 ), ( 76, 76, 76 ), ( 118, 122, 112 ), ( 164, 142, 128 ),
                         ( 146, 124, 98 ), ( 132, 130, 126 ) ], float )
    tone = base_c[kind] * rng.uniform( 0.88, 1.1, ( m, 1 ) )
    kk = kind[who]
    lum = 0.78 + 0.3 * dome + 0.03 * noise( rng, n, 1.2, 20, n / 3 )
    col = BT.shade( tone[who], lum )
    black, white, pink = _granite_crystals( rng, n )
    col = mix( col, ( 60, 56, 56 ), 0.5 * black * ( kk == 4 ) )
    col = mix( col, ( 214, 206, 196 ), 0.4 * white * ( ( kk == 4 ) | ( kk == 0 ) ) )
    phi = rng.uniform( 0, math.pi, m )[who]
    freq = rng.uniform( 2.5, 6.0, m )[who]
    stripes = np.sin( 2 * np.pi * freq * ( eu * np.cos( phi ) + ev * np.sin( phi ) ) + 3 * noise( rng, n, 2.0, 10, 80 ) * 0.3 )
    col = mix( col, ( 70, 70, 72 ), 0.45 * smoothstep( 0.3, 0.8, stripes ) * ( kk == 6 ) )
    veined = ( rng.random( m ) < 0.18 )[who]
    vein_pos = rng.uniform( -0.5, 0.5, m )[who]
    vein = smoothstep( 0.09, 0.03, np.abs( eu * np.cos( phi + 1.1 ) + ev * np.sin( phi + 1.1 ) - vein_pos ) ) * veined
    col = mix( col, ( 222, 220, 212 ), 0.85 * vein )
    c = mix( g_col, col, peb )
    height = np.maximum( g_h, np.where( np.isfinite( h_peb ), h_peb, g_h ) )
    cav, tops = cavities( height, 3.0 )
    c = darken( c, np.exp( -1.4 * cav ) * ( 1 - 0.35 * ( 1 - peb ) ) )
    rough = np.clip( 0.66 + 0.04 * ( kk == 2 ) - 0.12 * ( kk == 1 ) * peb + 0.15 * ( 1 - peb ), 0, 1 )
    return { "sh_shingle": c }, rough, height, 1024 / 128


def _ripples( rng, n, count, spread, wobble, sharp ):
    """ Ripple marks across the picture: a narrow band of wave vectors round count crests a tile (so they wrap), spread
    in wavelength and wobble in direction (radians), turned into crests by the band's analytic signal: each crest is a
    line of one phase of it, so the crests bend, fork and end the way real ones do. Asymmetric, a gentle stoss side
    and a steeper lee (sharp). Returns height -1..1 and the crest-ness 0..1. """
    f = np.fft.fftfreq( n, 1.0 / n )
    FX, FY = np.meshgrid( f, f )
    r = np.hypot( FX, FY )
    band = np.exp( -0.5 * ( ( r - count ) / ( spread * count ) ) ** 2 ) \
        * np.exp( -0.5 * ( np.arctan2( FX, FY ) / wobble ) ** 2 ) * ( FY > 0 )
    z = np.fft.ifft2( band * ( rng.normal( size=( n, n ) ) + 1j * rng.normal( size=( n, n ) ) ) )
    phase = ( np.angle( z ) / ( 2 * np.pi ) ) % 1.0
    amp = np.abs( z ) / np.abs( z ).mean()
    h = np.where( phase < sharp, phase / sharp, ( 1 - phase ) / ( 1 - sharp ) )
    h = ( smoothstep( 0, 1, h ) * 2 - 1 ) * smoothstep( 0.03, 0.4, amp ) * ( 0.75 + 0.25 * smoothstep( 0.3, 1.5, amp ) )
    return h, smoothstep( 0.5, 1.0, h )


@texture( "sand" )
def sand( rng, n ):
    """ Pale dry shell sand, 5.3 px an inch: cream-white, mostly broken shell, with darker mineral grains; small wind
    ripples three or four inches apart, their crests a little darker, fading out where the sand's been scuffed; bits of
    shell (white, pink and blue mussel), dry curls of weed and the odd pebble; drier and damper patches. """
    p = n / 192.0
    rip, crest = _ripples( rng, n, 52, 0.1, 0.12, 0.7 )
    keep = smoothstep( -0.6, 0.8, noise( rng, n, 2.4, 1, 8 ) )
    fine = noise( rng, n, 0.8, n / 5 )
    lumps = noise( rng, n, 2.6, 2, 40 )
    height = 0.1 * rip * keep + 0.12 * lumps + 0.006 * fine
    c = lum_paint( ( 204, 190, 160 ), 1.0 + 0.035 * fine + 0.03 * noise( rng, n, 2.0, 2, 40 ) )
    c = mix( c, ( 168, 154, 126 ), 0.2 * crest * keep )
    grains = smoothstep( 1.8, 2.6, unit( T.blur( rng.random( ( n, n ) ), 0.5 ) ) )
    c = mix( c, ( 120, 110, 96 ), 0.4 * grains )
    shells = Canvas( n, 2, 8 )
    pink_s, blue_s = Canvas( n, 2, 8 ), Canvas( n, 2, 8 )
    for _ in range( 500 ):
        cx, cy = rng.uniform( 0, n, 2 )
        r = rng.uniform( 0.12, 0.35 ) * p
        target = ( shells, shells, shells, pink_s, blue_s )[int( rng.integers( 5 ) )]
        target.ellipse( cx, cy, r, r * rng.uniform( 0.5, 1.0 ) )
    sh, pk, bl = shells.result(), pink_s.result(), blue_s.result()
    c = mix( c, ( 240, 236, 226 ), 0.8 * sh )
    c = mix( c, ( 214, 178, 170 ), 0.8 * pk )
    c = mix( c, ( 74, 80, 96 ), 0.8 * bl )
    weed = crack_lines( rng, n, 40, ( 2 * p, 6 * p ), 0.9, branch=0.3 )
    c = mix( c, ( 52, 44, 30 ), 0.75 * weed )
    pebbles = dots( rng, n, 30, ( 0.3 * p, 0.8 * p ) )
    c = mix( c, ( 128, 124, 116 ), 0.9 * smoothstep( 0, 0.2, pebbles ) )
    height = height + 0.03 * ( sh + pk + bl ) + 0.02 * weed + 0.25 * pebbles
    damp = smoothstep( 0.6, 1.8, noise( rng, n, 2.6, 1, 10 ) )
    c = darken( c, 1.0 - 0.12 * damp )
    c = darken( c, np.exp( -1.5 * cavities( height, 2.0 )[0] ) )
    rough = np.clip( 0.9 - 0.08 * damp - 0.1 * smoothstep( 0, 0.2, pebbles ), 0, 1 )
    return { "sh_sand": c }, rough, height, 1024 / 192


@texture( "sand_wet" )
def sand_wet( rng, n ):
    """ Wet sand at the water's edge, 5.3 px an inch: darker and smoother, with sinuous current ripples three to five
    inches apart, water left standing in their troughs (glossy, showing the sky), lugworm casts and their blow holes,
    bits of cockle and razor shell, scraps of green and brown weed. """
    p = n / 192.0
    rip, crest = _ripples( rng, n, 46, 0.12, 0.2, 0.62 )
    keep = smoothstep( -1.0, 0.6, noise( rng, n, 2.4, 1, 8 ) )
    fine = noise( rng, n, 0.8, n / 5 )
    height = 0.22 * rip * keep + 0.08 * noise( rng, n, 2.6, 1, 20 ) + 0.004 * fine
    c = lum_paint( ( 126, 110, 90 ), 1.0 + 0.03 * fine + 0.04 * noise( rng, n, 2.0, 2, 30 ) )
    c = mix( c, ( 150, 134, 108 ), 0.25 * crest * keep )                     # the crests drain and pale first
    pool = smoothstep( -0.55, -0.8, rip ) * keep * smoothstep( -0.6, 0.6, noise( rng, n, 2.0, 2, 24 ) )
    c = mix( c, mix( darken( c, 0.78 ), ( 118, 122, 126 ), 0.22 ), pool )
    # Lugworm casts: coils of sand beside their blow holes.
    casts = T.Strokes( c, np.clip( ( height + 1 ) / 2, 0, 1 ), ss=2 )
    holes = np.zeros( ( n, n ) )
    for _ in range( 14 ):
        cx, cy = rng.uniform( 0, n, 2 )
        a = rng.uniform( 0, 2 * math.pi )
        for _ in range( int( rng.integers( 2, 4 ) ) ):
            pts = T.curve_points( cx, cy, a, rng.uniform( 2.0, 3.5 ) * p, rng.choice( ( -1, 1 ) ) * rng.uniform( 4, 7 ), 12 )
            shade_c = np.array( ( 136, 120, 98 ) ) * rng.uniform( 0.95, 1.08 )
            casts.blade( pts, [ 0.28 * p ] * 12, [ shade_c * ( 0.9 + 0.02 * k ) for k in range( 12 ) ],
                         [ min( 0.99, ( 1.3 + 0.03 * k ) / 2 ) for k in range( 12 ) ] )
            cx, cy = pts[-1]
            a += rng.uniform( 1.5, 3.0 )
        stamp( holes, cx + rng.uniform( 4, 8 ) * p, cy + rng.uniform( -3, 3 ) * p, 0.5 * p, 0.5 * p, 1.0, profile="cone" )
    rgb, h, cover = casts.result()
    c = mix( c, rgb, cover )
    height = np.where( cover > 0.05, np.maximum( h * 2 - 1, height ), height ) - 0.25 * holes
    c = darken( c, 1.0 - 0.3 * holes )
    shells = dots( rng, n, 80, ( 0.15 * p, 0.4 * p ) )
    razor = np.zeros( ( n, n ) )
    for _ in range( 8 ):
        stamp( razor, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 2.0, 2.8 ) * p, 0.32 * p, 1.0,
               angle=rng.uniform( 0, math.pi ), soft=0.8 )
    c = mix( c, ( 220, 214, 200 ), 0.8 * smoothstep( 0, 0.3, shells ) )
    c = mix( c, ( 196, 190, 176 ), 0.7 * razor )
    green = blotches( rng, n, 2.0, 10, 120, 0.012, soft=0.15 )
    c = mix( c, ( 64, 110, 40 ), 0.8 * green )
    height = height + 0.05 * shells + 0.03 * razor + 0.02 * green
    c = darken( c, np.exp( -1.0 * cavities( height, 2.0 )[0] ) )
    rough = np.clip( 0.42 - 0.34 * pool + 0.08 * crest * keep - 0.1 * green + 0.25 * cover, 0.04, 1 )
    return { "sh_sand_wet": c }, rough, height, 1024 / 192


@texture( "wrack" )
def wrack( rng, n ):
    """ The strand line, 8 px an inch: a drift of cast-up weed on damp sand, heaped up in places and thin in others.
    Oarweed at the bottom (pale stipes with their holdfasts, dark strap blades), bladderwrack and knotted wrack heaped
    over it, wet and glossy, the pieces on top drying black and crisp; bootlace weed, eelgrass, a bit of twine,
    driftwood sticks, shells (mussels, cockles, limpets, whelks) and a gull's feather or two; the sand showing between
    with sandhopper holes. """
    p = n / 128.0
    sand_h = 0.12 * noise( rng, n, 2.6, 1, 20 ) + 0.01 * noise( rng, n, 0.8, n / 5 )
    sand_c = lum_paint( ( 146, 130, 104 ), 1.0 + 0.05 * noise( rng, n, 1.0, n / 5 ) + 0.05 * noise( rng, n, 2.0, 2, 30 ) )
    sand_c = mix( sand_c, ( 116, 102, 82 ), 0.45 * smoothstep( -0.5, 1.5, noise( rng, n, 2.2, 2, 16 ) ) )
    sand_c = mix( sand_c, ( 94, 86, 74 ), 0.4 * smoothstep( 1.8, 2.6, unit( T.blur( rng.random( ( n, n ) ), 0.5 ) ) ) )
    holes = np.zeros( ( n, n ) )
    for _ in range( 60 ):
        stamp( holes, rng.uniform( 0, n ), rng.uniform( 0, n ), 0.12 * p, 0.12 * p, 1.0, profile="cone" )
    sand_c = darken( sand_c, 1.0 - 0.5 * holes )
    sand_h = sand_h - 0.1 * holes
    pile = Pile( sand_c, np.full( ( n, n ), 0.82 ), 3.0, layer=0.1, cell=0.5 * p )
    heap = smoothstep( -0.9, 1.3, noise( rng, n, 2.4, 1, 6 ) + 0.4 * noise( rng, n, 2.0, 6, 20 ) )

    def spot():
        while True:
            x, y = rng.uniform( 0, n, 2 )
            if rng.random() < 0.2 + 0.8 * heap[int( y ) % n, int( x ) % n]:
                return x, y

    for _ in range( 14 ):
        x, y = spot()
        _oarweed( pile, rng, x, y, rng.uniform( 0, 2 * math.pi ), p, rng.uniform( 0.8, 1.15 ),
                  dry=0.4 if rng.random() < 0.2 else 0.0 )
    for _ in range( 4 ):
        _twig( pile, rng, *spot(), p )
    tones = [ ( 3, ( 74, 60, 26 ) ), ( 3, ( 66, 54, 24 ) ), ( 2, ( 84, 70, 30 ) ), ( 2, ( 58, 48, 22 ) ),
              ( 1, ( 96, 82, 36 ) ) ]
    count = 520
    for k in range( count ):
        x, y = spot()
        share = k / count
        dry = float( np.clip( rng.normal( 0.7, 0.3 ), 0, 1 ) ) if rng.random() < 0.06 + 0.4 * share ** 2 else 0.0
        if rng.random() < 0.14:
            _knotted( pile, rng, x, y, rng.uniform( 0, 2 * math.pi ), p, rng.uniform( 0.8, 1.2 ),
                      np.array( ( 84, 74, 32 ) ) * rng.uniform( 0.9, 1.1 ), dry=dry, bladder=1.02 )
        else:
            tone = T.pick( rng, tones, 1 )[0] * rng.uniform( 0.9, 1.1 )
            start = 0 if rng.random() < 0.45 else int( rng.integers( 1, 3 ) )
            _fucus( pile, rng, x, y, rng.uniform( 0, 2 * math.pi ), p, rng.uniform( 0.8, 1.2 ), tone, dry=dry,
                    start=start, fork=( 0.15, 0.4 ), seg=( 1.3, 2.6 ), fruit=0.05, width=0.75, bladder=1.0 )
        if k % 30 == 15:
            _strand( pile, rng, *spot(), p, ( "bootlace", "eelgrass", "bootlace", "twine" )[( k // 30 ) % 4] )
    for _ in range( 26 ):
        _shell( pile, rng, *rng.uniform( 0, n, 2 ), p )
    for _ in range( 3 ):
        _feather( pile, rng, *spot(), p )
    rgb, lift, cover, rough = pile.result()
    top = T.blur( lift, 0.7 * p )
    c = darken( rgb, np.exp( -1.4 * np.clip( top - lift, 0, None ) ) )
    shadow = np.clip( T.blur( np.roll( np.roll( cover, int( 0.5 * p ), 0 ), int( 0.25 * p ), 1 ), 0.8 * p ) - cover, 0, 1 )
    c = darken( c, 1.0 - 0.4 * shadow )
    height = settle( sand_h, lift, cover, p )
    c = darken( c, np.exp( -0.45 * cavities( height, 2.5 )[0] ) )
    return { "sh_wrack": c }, rough, height, 1024 / 128


@texture( "grass" )
def grass( rng, n ):
    """ Short verge grass, 5.3 px an inch, seen from above: tussocks of blades two to four inches long and blades lying
    every way between them over thatch and soil. Its greens vary in patches (blue-green rye grass, yellower bents,
    pale grey-green tufts of Yorkshire fog, dry straw-coloured blades), with clover in patches, a few clusters of
    daisies, the odd plantain and dandelion rosette, and moss where it's damp. """
    p = n / 192.0
    s2 = ( n / 1024 ) ** 2
    patch = noise( rng, n, 2.3, 1, 10 )
    patch2 = noise( rng, n, 1.8, 8, 60 )
    vigour = smoothstep( -1.4, 1.2, noise( rng, n, 2.4, 1, 12 ) + 0.3 * patch2 )
    damp = smoothstep( 0.8, 1.8, noise( rng, n, 2.4, 1, 10 ) )
    soil = lum_paint( ( 66, 60, 38 ), 1.0 + 0.1 * noise( rng, n, 1.0, n / 5 ) + 0.1 * noise( rng, n, 2.0, 2, 40 ) )
    soil = mix( soil, ( 58, 74, 30 ), 0.6 * damp )
    height = 0.1 * noise( rng, n, 2.6, 1, 20 )
    strokes = T.Strokes( soil, np.zeros( ( n, n ) ), ss=2 )

    def colour_at( x, y ):
        i, j = int( y ) % n, int( x ) % n
        t = smoothstep( -0.9, 0.9, patch[i, j] )
        col = mix( np.array( ( 60, 92, 42 ) ), np.array( ( 102, 118, 48 ) ), t )
        if patch2[i, j] > 1.1:
            col = mix( col, np.array( ( 112, 124, 86 ) ), 0.6 )
        return col * ( 0.86 + 0.24 * vigour[i, j] )

    # Thatch: dead blades lying flat under the sward.
    for _ in range( int( 16000 * s2 ) ):
        x, y = rng.uniform( 0, n, 2 )
        pts = T.curve_points( x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 1.5, 3.5 ) * p, rng.normal( 0, 0.3 ), 2 )
        col = np.array( ( 118, 104, 66 ) ) * rng.uniform( 0.8, 1.1 )
        strokes.blade( pts, [ 0.8, 0.6 ], [ col * 0.9, col ], [ 0.05, 0.05 ] )
    # Tussocks: blades springing from a crown and arching out every way.
    blades = []
    for cx, cy in jittered( rng, n, 3.4 * p, 0.5 ):
        v = vigour[int( cy ) % n, int( cx ) % n]
        R = rng.uniform( 0.3, 0.8 ) * p
        for _ in range( int( 10 + 26 * v ) ):
            ox, oy = rng.normal( 0, R, 2 )
            a = math.atan2( oy, ox ) + rng.normal( 0, 0.5 )
            blades.append( ( cx + ox, cy + oy, a, rng.uniform( 1.5, 3.8 ) * p ) )
    # Loose blades between them.
    for _ in range( int( 30000 * s2 ) ):
        x, y = rng.uniform( 0, n, 2 )
        if rng.random() < 0.3 + 0.7 * vigour[int( y ) % n, int( x ) % n]:
            blades.append( ( x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 1.4, 3.4 ) * p ) )
    order = rng.permutation( len( blades ) )
    total = len( blades )
    for rank, k in enumerate( order ):
        x, y, a, length = blades[k]
        col = colour_at( x, y ) * rng.uniform( 0.84, 1.14 )
        if rng.random() < 0.06:
            col = np.array( ( 150, 136, 86 ) ) * rng.uniform( 0.85, 1.1 )
        pts = T.curve_points( x, y, a, length, rng.normal( 0, 0.45 ), 3 )
        hh = 0.12 + 0.8 * rank / total
        strokes.blade( pts, [ 1.0, 0.85, 0.6 ], [ col * 0.8, col * 0.98, col * 1.1 ], [ hh, hh, hh ] )
    # Moss in the damp patches.
    for _ in range( int( 9000 * s2 ) ):
        x, y = rng.uniform( 0, n, 2 )
        if rng.random() < damp[int( y ) % n, int( x ) % n]:
            r = rng.uniform( 0.08, 0.16 ) * p
            strokes.dot( x, y, r, r, np.array( ( 78, 100, 34 ) ) * rng.uniform( 0.8, 1.15 ), 0.5 )
    # Clover in patches.
    clover = smoothstep( 1.0, 1.8, noise( rng, n, 2.2, 2, 24 ) )
    for _ in range( int( 3000 * s2 ) ):
        x, y = rng.uniform( 0, n, 2 )
        if rng.random() > clover[int( y ) % n, int( x ) % n]:
            continue
        a = rng.uniform( 0, 2 * math.pi )
        r = rng.uniform( 0.2, 0.28 ) * p
        col = np.array( ( 54, 90, 48 ) ) * rng.uniform( 0.9, 1.1 )
        for k in range( 3 ):
            b = a + k * 2 * math.pi / 3
            strokes.dot( x + math.cos( b ) * r, y + math.sin( b ) * r, r, r, col, 0.96 )
    # Plantain and dandelion rosettes.
    for _ in range( int( 10 * s2 ) + 1 ):
        x, y = rng.uniform( 0, n, 2 )
        dandelion = rng.random() < 0.4
        col = np.array( ( 70, 100, 44 ) if dandelion else ( 58, 86, 40 ) ) * rng.uniform( 0.9, 1.1 )
        for k in range( int( rng.integers( 5, 9 ) ) ):
            a = rng.uniform( 0, 2 * math.pi )
            pts = T.curve_points( x, y, a, rng.uniform( 2.5, 4.5 ) * p, rng.normal( 0, 0.2 ), 3 )
            w = rng.uniform( 0.5, 0.8 ) * p
            strokes.blade( pts, [ 0.5 * w, w, 0.6 * w ], [ col * 0.9, col, col * 1.05 ], [ 0.97 ] * 3 )
    # Daisies, a few clusters of them.
    for _ in range( int( 5 * s2 ) + 1 ):
        cx, cy = rng.uniform( 0, n, 2 )
        for _ in range( int( rng.integers( 3, 12 ) ) ):
            x, y = cx + rng.normal( 0, 2.5 * p ), cy + rng.normal( 0, 2.5 * p )
            r = rng.uniform( 0.24, 0.34 ) * p
            strokes.dot( x, y, r, r, np.array( ( 232, 230, 220 ) if rng.random() < 0.8 else ( 228, 206, 210 ) ), 0.98 )
            strokes.dot( x, y, r * 0.36, r * 0.36, ( 222, 180, 40 ), 0.99 )
    rgb, h, cover = strokes.result()
    height = height + 0.3 * h
    c = darken( rgb, np.exp( -2.0 * cavities( height, 1.5 )[0] ) )
    rough = np.clip( 0.8 + 0.05 * noise( rng, n, 1.0, n / 6 ) - 0.05 * vigour, 0, 1 )
    return { "sh_grass": c }, rough, height, 1024 / 192


@texture( "seabed" )
def seabed( rng, n ):
    """ The seabed under a little water, 2 px an inch: rippled sand, pebbles and stones, patches of weed and green
    algae, all a little blue-green and muted by the water over them. """
    p = n / 256.0
    rip, crest = _ripples( rng, n, 50, 0.12, 0.18, 0.6 )
    keep = smoothstep( -0.8, 0.8, noise( rng, n, 2.4, 1, 8 ) )
    height = 0.3 * rip * keep + 0.4 * noise( rng, n, 2.6, 1, 20 )
    c = lum_paint( ( 124, 116, 94 ), 1.0 + 0.06 * noise( rng, n, 1.5, 4, n / 4 ) )
    c = mix( c, ( 140, 132, 108 ), 0.25 * crest * keep )
    pts = jittered( rng, n, 3.0 * p, 0.5 )
    stony = smoothstep( -0.5, 1.0, noise( rng, n, 2.0, 2, 16 ) )
    pts = pts[rng.random( len( pts ) ) < stony[pts[:, 1].astype( int ) % n, pts[:, 0].astype( int ) % n]]
    rad = rng.uniform( 0.7, 2.4, len( pts ) ) * p
    who, d, _ = packed( rng, n, pts, rad )
    stone = smoothstep( 1.0, 0.8, d )
    dome = np.sqrt( np.clip( 1 - d * d, 0, 1 ) )
    tone = BT.tones( rng, [ ( 110, 108, 100 ), ( 84, 84, 80 ), ( 136, 130, 120 ), ( 98, 92, 82 ) ], len( pts ), 0.1 )
    c = mix( c, BT.shade( tone[who], 0.75 + 0.35 * dome ), stone )
    height = height + stone * 1.2 * dome * rad[who] / p * 0.5
    weed_m = smoothstep( 0.6, 1.4, noise( rng, n, 2.2, 2, 24 ) + 0.5 * stone )
    strands = smoothstep( -0.2, 1.2, BT.stretched( rng, n, 1.2, 10, 200, ( 2, 0.6 ) ) + 0.5 * noise( rng, n, 1.0, n / 4 ) )
    c = mix( c, mix( ( 50, 46, 26 ), ( 72, 64, 34 ), strands ), 0.85 * weed_m )
    green = smoothstep( 1.2, 1.8, noise( rng, n, 2.0, 4, 40 ) ) * ( 1 - weed_m )
    c = mix( c, ( 70, 104, 46 ), 0.6 * green )
    c = tinted( c, ( 70, 96, 92 ), 0.25 )
    c = darken( c, np.exp( -0.8 * cavities( height, 2.0 )[0] ) )
    rough = np.clip( 0.6 - 0.2 * weed_m, 0, 1 )
    return { "sh_seabed": c }, rough, height, 1024 / 256


@texture( "seabed_deep" )
def seabed_deep( rng, n ):
    """ The deep seabed, an inch a px, seen down through the water: muddy sand in long low ripples, boulders in
    clusters, crusted pink with coralline algae, and kelp growing on them, its fingers lying downstream with the
    current in dark swathes that spill over the sand; the odd starfish; all dim and blue-green. """
    p = n / 512.0
    current = rng.uniform( 0, 2 * math.pi )
    rip, crest = _ripples( rng, n, 22, 0.15, 0.3, 0.55 )
    height = 0.8 * rip + 1.2 * noise( rng, n, 2.6, 1, 30 )
    c = lum_paint( ( 96, 92, 76 ), 1.0 + 0.1 * noise( rng, n, 1.8, 2, n / 4 ) + 0.05 * noise( rng, n, 1.0, n / 3 ) )
    c = mix( c, ( 112, 108, 90 ), 0.3 * crest )
    c = mix( c, ( 68, 64, 52 ), 0.35 * smoothstep( 0.0, 1.6, noise( rng, n, 2.2, 2, 20 ) ) )
    pebbles = dots( rng, n, 300, ( 0.6 * p, 2.0 * p ) )
    c = mix( c, ( 120, 116, 104 ), 0.6 * smoothstep( 0, 0.3, pebbles ) )
    height = height + 1.0 * pebbles
    field = smoothstep( -0.2, 1.0, noise( rng, n, 2.4, 1, 6 ) )
    pts = jittered( rng, n, 36 * p, 0.5 )
    pts = pts[rng.random( len( pts ) ) < 0.9 * field[pts[:, 1].astype( int ) % n, pts[:, 0].astype( int ) % n]]
    m = len( pts )
    rx = np.exp( rng.normal( 0, 0.4, m ) ) * 16 * p
    ry = rx * rng.uniform( 0.6, 0.95, m )
    thick = rng.uniform( 0.4, 0.7, m ) * np.sqrt( rx * ry ) / p
    who, e, eu, ev, h = _stones( n, pts, rx, ry, rng.uniform( 0, math.pi, m ), rng.uniform( -6, 0, m ), thick )
    rock = smoothstep( 1.0, 0.9, e + 0.06 * noise( rng, n, 2.0, 8, 40 ) ) * ( who >= 0 )
    rock_h = np.where( np.isfinite( h ), h, -10.0 ) + 0.8 * noise( rng, n, 2.0, 20, 120 )
    height = height + ( np.maximum( height, rock_h ) - height ) * rock
    shade = 0.75 + 0.3 * np.clip( 1 - np.clip( e, 0, 1 ) ** 2, 0, 1 )
    rock_c = lum_paint( ( 92, 90, 84 ), shade + 0.08 * noise( rng, n, 1.5, 20, 160 ) )
    rock_c = mix( rock_c, ( 150, 106, 112 ), 0.55 * smoothstep( 0.2, 1.2, noise( rng, n, 1.8, 6, 60 ) ) )
    rock_c = mix( rock_c, ( 70, 52, 34 ), 0.4 * smoothstep( 0.0, 1.4, noise( rng, n, 1.8, 10, 100 ) ) )
    c = mix( c, rock_c, rock )
    c = darken( c, 1.0 - 0.35 * np.clip( T.blur( np.roll( rock, 3, 0 ), 3 ) - rock, 0, 1 ) )
    pile = Pile( c, np.clip( 0.75 - 0.1 * rock, 0, 1 ), 8.0, layer=0.3, cell=2 * p )
    for k in range( m ):
        for _ in range( int( rng.integers( 2, 7 ) ) ):
            ox, oy = rng.normal( 0, 0.4, 2 ) * ( rx[k], ry[k] )
            _kelp_plant( pile, rng, pts[k][0] + ox, pts[k][1] + oy, current, p, rng.uniform( 0.8, 1.2 ) )
    for _ in range( 7 ):
        _starfish( pile, rng, *rng.uniform( 0, n, 2 ), p )
    rgb, lift, cover, rough = pile.result()
    top = ndimage.maximum_filter( lift, size=5, mode="wrap" )
    c = darken( rgb, np.exp( -0.3 * np.clip( top - lift, 0, None ) ) )
    shadow = np.clip( T.blur( np.roll( cover, 3, 0 ), 2.0 ) - cover, 0, 1 )
    c = darken( c, 1.0 - 0.4 * shadow )
    height = settle( height, lift, cover, 2 * p )
    c = darken( c, np.exp( -0.12 * cavities( height, 3.0 )[0] ) )
    c = tinted( c, ( 40, 72, 68 ), 0.35 )
    return { "sh_seabed_deep": c }, rough, height, 1024 / 512


@texture( "kerb" )
def kerb( rng, n ):
    """ Granite kerbstones, 8 px an inch: blocks three to four feet long, fine-axed so faint parallel tool lines cross
    them, the grain salt-and-pepper grey; the arrises worn round, the joints set back and dirty, black smudges where
    tyres have rubbed, a little lichen. """
    p = n / 64.0
    block, u, v, length, rowh, row, count = BT.coursed( rng, n, ( 30 * p, 34 * p ), ( 36 * p, 48 * p ) )
    edge = np.minimum( np.minimum( u, length - u ), np.minimum( v, rowh - v ) )
    jw = 0.15 * p
    inside = smoothstep( jw - 0.5, jw + 0.5, edge )
    round_ = 1.0 - np.exp( -np.clip( edge - jw, 0, None ) / ( 0.5 * p ) )
    axe = BT.stretched( rng, n, 1.0, 40, n / 2, ( 0.4, 3 * p ) )
    height = -0.25 * ( 1 - inside ) + inside * ( 0.12 * ( round_ - 1 ) + 0.006 * axe + 0.01 * noise( rng, n, 2.0, 8, 80 ) )
    black, white, pink = _granite_crystals( rng, n )
    tone = BT.tones( rng, [ ( 162, 158, 152 ), ( 154, 148, 142 ), ( 168, 162, 156 ) ], count, 0.04 )
    c = BT.shade( tone[block], 1.0 + 0.04 * noise( rng, n, 1.8, 4, 80 ) + 0.03 * axe )
    c = mix( c, ( 206, 202, 196 ), 0.6 * white )
    c = mix( c, ( 50, 48, 48 ), 0.7 * black )
    c = mix( c, ( 176, 160, 150 ), 0.3 * pink )
    smudge = smoothstep( 1.0, 2.2, BT.stretched( rng, n, 1.6, 2, 40, ( 1.5 * p, 10 * p ) ) ) * smoothstep( -0.5, 1.0, noise( rng, n, 2.0, 2, 20 ) )
    c = mix( c, ( 52, 50, 50 ), 0.4 * smudge )
    grime = smoothstep( -0.2, 1.6, noise( rng, n, 2.2, 1, 20 ) )
    c = mix( c, ( 116, 110, 102 ), 0.25 * grime )
    lichen = smoothstep( 2.0, 2.3, noise( rng, n, 1.6, 10, 120 ) + 0.4 * noise( rng, n, 0.8, n / 4 ) )
    c = mix( c, ( 196, 196, 186 ), 0.6 * lichen )
    c = mix( lum_paint( ( 90, 86, 80 ), 1.0 + 0.1 * noise( rng, n, 1.0, n / 6 ) ), c, inside )
    c = darken( c, np.exp( -2.0 * cavities( height, 2.0 )[0] ) )
    rough = np.clip( 0.7 - 0.06 * ( 1 - grime ) + 0.1 * lichen + 0.2 * ( 1 - inside ) - 0.1 * smudge, 0, 1 )
    return { "sh_kerb": c }, rough, height, 1024 / 64


def _rock_relief( rng, n, p ):
    """ An outcrop's face in inches. Master joints run right across it (one set of gently bent lines, wrapping round
    the tile); cross joints run square to them from one master joint to the next, each stretch at its own offset (so
    they meet the masters in T-junctions, as real ones do) and some missing, so the blocks between are irregular. Each
    block sits at its own level with its own tilt, its edges weathered round, and the joints are open by varying widths.
    A third set shows only as short partial joints; bumps and hollows at every scale, hairline fractures, and the
    foliation's banding as a field. Returns ( height, block, count, bands, fractures, joint ). """
    x, y = coords( n )
    a, b = 2, 5
    ab = math.hypot( a, b )
    ph_a = ( a * x + b * y ) / n + 0.09 * noise( rng, n, 3.0, 1, 3 ) + 0.01 * noise( rng, n, 2.0, 3, 10 )
    d_a = np.abs( ph_a - np.round( ph_a ) ) * n / ab
    # Each px's point on its strip's centre line between two master joints (moving square to them), where the cross
    # joints' offsets are read: waves whose crests run nearly along the strip, so they change slowly along it but
    # differ from one lap of it to the next.
    shift = ( np.floor( ph_a ) + 0.5 - ph_a ) * n / ab ** 2
    cx, cy = x + shift * a, y + shift * b
    off = np.zeros( ( n, n ) )
    for fx, fy in ( ( 1, 2 ), ( 1, 3 ), ( 0, 1 ), ( 3, 8 ) ):
        off += rng.uniform( 0.25, 0.45 ) * np.cos( 2 * np.pi * ( fx * cx + fy * cy ) / n + rng.uniform( 0, 2 * np.pi ) )
    c_, d_ = 5, -2
    cd = math.hypot( c_, d_ )
    ph_b = ( c_ * x + d_ * y ) / n + off + 0.01 * noise( rng, n, 2.0, 3, 12 )
    d_b = np.abs( ph_b - np.round( ph_b ) ) * n / cd
    # Each stretch of cross joint between two masters is there or not.
    stretch = ( d_b < 2.0 ) & ( d_a > 2.5 )
    seg, segs = _wrap_label( stretch )
    keep = rng.random( max( segs, 1 ) ) < 0.7
    rows, cols = nearest_wrap( stretch, 96 )
    present = keep[seg[rows, cols]]
    barrier = ( d_a < 1.0 ) | ( ( d_b < 1.0 ) & present )
    block, count = _blocks( barrier )
    # Joint widths: the masters wider, everything varying along its length.
    width_a = ( 0.6 + 1.0 * smoothstep( -1, 1, noise( rng, n, 2.0, 3, 24 ) ) ) * p
    width_b = ( 0.35 + 0.6 * smoothstep( -1, 1, noise( rng, n, 2.0, 3, 24 ) ) ) * p
    d_b_open = np.where( present, d_b, 1e9 )
    third = _joint_set( rng, n, 3, 3, 0.04 )
    open_c = smoothstep( 0.2, 0.7, noise( rng, n, 2.2, 3, 16 ) )
    d_c = third + ( 1 - open_c ) * 40 * p
    joint = np.maximum.reduce( [ smoothstep( width_a, 0.0, d_a ), smoothstep( width_b, 0.0, d_b_open ),
                                 0.7 * smoothstep( 0.5 * p, 0.0, d_c ) ] )
    d_edge = np.minimum.reduce( [ d_a / ( 1.2 * width_a / p ), d_b_open / ( 1.2 * width_b / p ), d_c / 0.6 ] )
    rounded = 1.0 - np.exp( -d_edge / ( 3.0 * p ) )
    # Each block's level and tilt about its centre (found round the torus).
    lab = block.ravel()
    ang_x, ang_y = 2 * np.pi * x.ravel() / n, 2 * np.pi * y.ravel() / n
    mx = np.angle( np.bincount( lab, np.cos( ang_x ), count ) + 1j * np.bincount( lab, np.sin( ang_x ), count ) )
    my = np.angle( np.bincount( lab, np.cos( ang_y ), count ) + 1j * np.bincount( lab, np.sin( ang_y ), count ) )
    bx, by = ( mx / ( 2 * np.pi ) * n ) % n, ( my / ( 2 * np.pi ) * n ) % n
    dx = ( x - bx[block] + n / 2 ) % n - n / 2
    dy = ( y - by[block] + n / 2 ) % n - n / 2
    level = rng.normal( 0, 1.0, count )
    tilt = rng.normal( 0, 0.05 / p, ( count, 2 ) )
    planes = level[block] + tilt[block, 0] * dx + tilt[block, 1] * dy
    bands = np.sin( 2 * np.pi * ( 20 * x + 46 * y ) / n + 2.2 * noise( rng, n, 2.6, 1, 8 ) ) \
        + 0.5 * np.sin( 2 * np.pi * ( 53 * x + 117 * y ) / n + 1.8 * noise( rng, n, 2.2, 2, 20 ) )
    fractures = crack_lines( rng, n, 10, ( 20 * p, 70 * p ), 0.6, branch=0.3, turn=0.05, pull=0.5 )
    height = planes + 0.9 * noise( rng, n, 2.6, 1, 24 ) + 0.3 * noise( rng, n, 2.0, 20, 120 ) \
        + 0.05 * noise( rng, n, 1.4, 100, n / 3 ) + 0.06 * bands + 2.2 * ( rounded - 1 ) - 1.4 * joint \
        - 0.12 * fractures
    return height, block, count, bands, fractures, joint


@texture( "rock" )
def rock( rng, n ):
    """ Grey rock outcrops (Lewisian gneiss), 4 px an inch: blocks between joints, weathered round, banded along the
    foliation (pale pinkish bands and dark ones, folded), with the odd white quartz vein and iron staining run down from
    the cracks. Lichens: grey-white crusts spread in big merging patches, yellow-green map lichen with its black rims,
    grey-green leafy rosettes, black spots, and yellow Xanthoria and orange Caloplaca clustered on the tops where the
    birds perch; moss in the joints. """
    p = n / 256.0
    height, block, count, bands, fractures, joint = _rock_relief( rng, n, p )
    cav, tops = cavities( height, 4.0 )
    tone = BT.tones( rng, [ ( 128, 126, 120 ), ( 120, 119, 115 ), ( 132, 127, 120 ), ( 116, 116, 113 ) ], count, 0.04 )
    mottle = noise( rng, n, 1.8, 4, 120 )
    fine = noise( rng, n, 1.0, n / 5 )
    grain = grain_field( rng, n, 0.6, 4.0 )
    c = BT.shade( tone[block], 1.0 + 0.06 * mottle + 0.1 * bands + 0.04 * fine )
    c = mix( c, ( 156, 138, 130 ), 0.35 * smoothstep( 0.5, 1.3, bands ) )
    c = mix( c, ( 74, 78, 74 ), 0.4 * smoothstep( -0.5, -1.3, bands ) )
    c = mix( c, ( 52, 52, 50 ), 0.35 * smoothstep( 1.4, 2.4, grain ) )
    veins = crack_lines( rng, n, 5, ( 40 * p, 140 * p ), 2.0, branch=0.1, turn=0.04, pull=0.6 )
    veins = veins * smoothstep( -0.4, 0.5, noise( rng, n, 2.0, 4, 30 ) )
    c = mix( c, ( 200, 198, 190 ), 0.6 * veins )
    stain = wash_down( np.clip( fractures + joint, 0, 1 ) * smoothstep( 0.6, 1.6, noise( rng, n, 1.6, 4, 40 ) ), 12 * p,
                       1.0, rng )
    c = mix( c, ( 128, 96, 66 ), 0.3 * stain )
    c = darken( c, 1.0 - 0.3 * fractures )
    open_ground = 1 - smoothstep( 0.15, 0.5, joint )
    tex = noise( rng, n, 1.2, 20, n / 3 )
    patches = smoothstep( -0.6, 0.9, noise( rng, n, 2.4, 1, 6 ) + 0.35 * noise( rng, n, 2.0, 6, 30 ) ) * open_ground
    c, grey = _lichen( c, rng, n, 520, ( 1.6 * p, 7 * p ), patches, ( 172, 172, 162 ), 0.62, texture=tex )
    c, _ = _lichen( c, rng, n, 60, ( 2 * p, 6 * p ), 0.5 * open_ground, ( 134, 142, 122 ), 0.8, texture=tex,
                    lobes=0.28 )
    tops_f = smoothstep( -0.3, 1.2, tops * 2 + 0.3 * noise( rng, n, 2.0, 2, 20 ) ) * open_ground
    c, mapl = _lichen( c, rng, n, 90, ( 0.8 * p, 3.5 * p ), 0.6 * tops_f, ( 176, 176, 86 ), 0.85, rim=0.8,
                       texture=tex, lobes=0.1 )
    c, _ = _lichen( c, rng, n, 160, ( 0.35 * p, 1.2 * p ), 0.5 * open_ground, ( 54, 54, 50 ), 0.8, lobes=0.08 )
    perch = smoothstep( 0.9, 1.8, noise( rng, n, 2.2, 1, 10 ) ) * tops_f
    c, yel = _lichen( c, rng, n, 260, ( 0.35 * p, 1.6 * p ), perch, ( 212, 162, 50 ), 0.88, spread=0.08, texture=tex,
                      lobes=0.24 )
    c, ora = _lichen( c, rng, n, 140, ( 0.3 * p, 1.0 * p ), perch, ( 204, 112, 42 ), 0.85, spread=0.08, lobes=0.2 )
    moss = joint * smoothstep( -0.4, 1.0, noise( rng, n, 1.8, 6, 80 ) )
    c = mix( c, mix( ( 60, 80, 32 ), ( 92, 104, 44 ), smoothstep( -1, 1, fine ) ), 0.85 * moss )
    height = height + 0.03 * grey + 0.05 * ( mapl + yel + ora ) + 0.4 * moss
    c = darken( c, np.exp( -0.8 * cav ) )
    rough = np.clip( 0.74 + 0.04 * mottle + 0.1 * grey + 0.12 * ( yel + ora ) - 0.1 * veins + 0.12 * moss, 0, 1 )
    return { "sh_rock": c }, rough, height, 1024 / 256


@texture( "rock_weed" )
def rock_weed( rng, n ):
    """ Shore rock between the tides, 4 px an inch: the same jointed rock, wet and dark, under black tar lichen,
    crowds of barnacles, a few limpets, green weed in the hollows and a mat of knotted wrack and bladderwrack laid over
    it in clumps, combed one way by the ebb. """
    p = n / 256.0
    height, block, count, bands, fractures, joint = _rock_relief( rng, n, p )
    tone = BT.tones( rng, [ ( 86, 84, 80 ), ( 78, 78, 76 ), ( 92, 88, 82 ) ], count, 0.06 )
    c = BT.shade( tone[block], 1.0 + 0.05 * noise( rng, n, 1.8, 4, 120 ) + 0.05 * bands )
    flow = rng.uniform( 0, 2 * math.pi ) + 1.1 * noise( rng, n, 3.0, 1, 4 )
    tones = [ ( 3, ( 80, 66, 30 ) ), ( 2, ( 70, 58, 27 ) ), ( 2, ( 60, 50, 24 ) ), ( 1, ( 92, 80, 36 ) ),
              ( 1, ( 52, 42, 21 ) ) ]
    c, height, rough = _shore_life( rng, n, p, c, height, tar=0.3, green=0.05, barnacles=0.3, weed=0.55, flow=flow,
                                    tones=tones, plants=40, size=1.1, strand=0.85, length=14.0 )
    return { "sh_rock_weed": c }, rough, height, 1024 / 256


def _frond_path( rng, x, y, angle, length, step, curl, toward=None, pull=0.0 ):
    """ Points ( x, y ) along a frond lying loose from x, y, about step px apart: its heading wanders (the turn each
    step a smoothed random walk of curl radians), and with toward (a heading, or a field of them n x n) it's drawn back
    to that heading by pull of the difference a step (fronds hanging down a wall, or combed one way by the ebb).
    Returns ( points, the heading at its end ). """
    k = max( 2, int( math.ceil( length / step ) ) )
    step = length / k
    pts = [ ( x, y ) ]
    turn = rng.normal( 0, curl )
    field = isinstance( toward, np.ndarray )
    n = toward.shape[0] if field else 0
    for _ in range( k ):
        turn = 0.75 * turn + rng.normal( 0, curl )
        angle += turn
        if toward is not None:
            goal = float( toward[int( y ) % n, int( x ) % n] ) if field else toward
            angle += pull * math.atan2( math.sin( goal - angle ), math.cos( goal - angle ) )
        x += math.cos( angle ) * step
        y += math.sin( angle ) * step
        pts.append( ( x, y ) )
    return pts, angle


def _strap( pile, pts, widths, colours, lift=1.0, aux=0.25 ):
    """ One strap laid on the pile: it rests on whatever lies under it, lift straps' thickness over it, drawn with a
    colour and an aux (roughness) per segment or one for all, and recorded at its level across its width. Returns its
    level at each point. """
    a = np.asarray( pts, float )
    lv = pile.rest( a, lift * pile.dt )
    pile.layers.ribbon( pts, widths, colours, list( 0.5 * ( lv[:-1] + lv[1:] ) ), aux )
    d = np.gradient( a, axis=0 )
    d /= np.linalg.norm( d, axis=1, keepdims=True ) + 1e-9
    nrm = np.stack( [ -d[:, 1], d[:, 0] ], -1 ) * np.asarray( widths, float )[:, None]
    for s in ( -0.35, 0.0, 0.35 ):
        pile.lay( a + s * nrm, lv )
    return lv


def _dried( colour, dry ):
    """ A weed's colour dried towards crisp black-brown by dry (0..1). """
    return np.asarray( colour, float ) * ( 1 - dry ) + np.array( ( 33, 30, 23 ) ) * dry


def _fucus( pile, rng, x, y, angle, p, size, tone, flow=None, pull=0.15, dry=0.0, start=0, depth_max=5,
            fork=( 0.2, 0.5 ), seg=( 2.0, 3.6 ), fruit=0.15, width=0.6, bladder=1.1 ):
    """ A plant (or, from start > 0, a broken piece) of bladderwrack, Fucus vesiculosus, laid on the pile from x, y: a
    short stipe, then flat fronds width inches wide with a midrib, forking every seg inches (each half a little
    narrower, turning off by fork radians), with a pair of air bladders just past most forks and, at fruit of the
    tips, a swollen receptacle (few are left by October). flow: a heading or a field of them the fronds are drawn to
    by pull a step (hanging down a wall, or combed one way by the ebb); without it they sprawl every way. tone: the
    plant's olive-brown, lighter towards the tips; dry 0..1 how far it has dried black; bladder the bladders' colour
    against the frond's. """
    dt = pile.dt
    aux = 0.2 + 0.5 * dry
    todo = [ ( x, y, angle, start ) ]
    while todo:
        x, y, a, depth = todo.pop()
        length = ( rng.uniform( 0.8, 1.6 ) if depth == 0 else rng.uniform( *seg ) ) * p * size
        tip = depth >= depth_max or ( depth >= 3 and rng.random() < 0.25 )
        if flow is not None:
            pts, a_end = _frond_path( rng, x, y, a, length, 0.6 * p, 0.05, toward=flow, pull=pull )
        else:
            pts, a_end = _frond_path( rng, x, y, a, length, 0.6 * p, 0.09 )
        m = len( pts )
        if depth == 0:
            w = [ ( 0.16 + 0.06 * k / ( m - 1 ) ) * p * size for k in range( m ) ]
        else:
            w0 = width * p * size * 0.93 ** ( depth - 1 ) * rng.uniform( 0.9, 1.1 )
            w = [ w0 * min( 1.0, 0.72 + 0.28 * k ) for k in range( m ) ]
            if tip:
                w[-1] *= 0.45
                w[-2] *= 0.85
        cols = [ np.clip( _dried( tone * ( 0.86 + 0.05 * min( depth + k / ( m - 1 ), 5 ) ) * rng.uniform( 0.96, 1.04 ),
                                  dry ), 0, 255 ) for k in range( m - 1 ) ]
        lv = _strap( pile, pts, w, cols, 1.0, aux )
        if depth > 0:
            mid = list( 0.5 * ( lv[:-1] + lv[1:] ) + 0.35 * dt )
            pile.layers.ribbon( pts, [ 0.14 * wk for wk in w ], [ c * 0.8 for c in cols ], mid, aux )
            if m > 3 and rng.random() < 0.6:
                k = int( rng.integers( 1, min( 3, m - 2 ) + 1 ) )
                bx, by = pts[k]
                ang = math.atan2( pts[k + 1][1] - pts[k - 1][1], pts[k + 1][0] - pts[k - 1][0] )
                r = 0.2 * p * size * rng.uniform( 0.8, 1.2 )
                ox, oy = -math.sin( ang ) * 0.28 * w[k], math.cos( ang ) * 0.28 * w[k]
                for side in ( -1, 1 ):
                    pile.layers.ellipse( bx + side * ox, by + side * oy, r * 1.3, r, ang,
                                         np.clip( cols[min( k, m - 2 )] * bladder, 0, 255 ), float( lv[k] ) + 1.4 * dt,
                                         aux * 0.8 )
        if tip:
            if depth >= 3 and rng.random() < fruit:
                ex, ey = pts[-1]
                L = rng.uniform( 0.45, 0.75 ) * p * size
                rc = np.clip( _dried( np.array( ( 94, 84, 40 ) ) * rng.uniform( 0.85, 1.1 ), dry ), 0, 255 )
                pile.layers.ellipse( ex - math.cos( a_end ) * 0.3 * L, ey - math.sin( a_end ) * 0.3 * L, L,
                                     0.36 * p * size, a_end, rc, float( lv[-1] ) + 1.2 * dt, aux )
            continue
        for side in ( -1, 1 ):
            todo.append( ( pts[-1][0], pts[-1][1], a_end + side * rng.uniform( *fork ), depth + 1 ) )


def _knotted( pile, rng, x, y, angle, p, size, tone, dry=0.0, flow=None, pull=0.15, bladder=1.1 ):
    """ Knotted wrack, Ascophyllum nodosum: long narrow strap-like fronds a third of an inch wide with no midrib,
    single egg-shaped bladders swelling them every few inches, and the odd side shoot; yellow-olive. flow and pull as
    for _fucus, bladder the bladders' colour against the frond's. """
    aux = 0.22 + 0.5 * dry
    shoots = [ ( x, y, angle, rng.uniform( 14, 30 ) * p * size, 0.32 ) ]
    first = True
    while shoots:
        x, y, a, length, width = shoots.pop()
        if flow is not None:
            pts, _ = _frond_path( rng, x, y, a, length, 0.6 * p, 0.05, toward=flow, pull=pull )
        else:
            pts, _ = _frond_path( rng, x, y, a, length, 0.6 * p, 0.07 )
        m = len( pts )
        w = [ width * p * size * ( 1 - 0.3 * k / m ) for k in range( m ) ]
        w[-1] *= 0.5
        cols = [ np.clip( _dried( tone * rng.uniform( 0.95, 1.05 ) * ( 0.9 + 0.15 * k / m ), dry ), 0, 255 )
                 for k in range( m - 1 ) ]
        lv = _strap( pile, pts, w, cols, 1.0, aux )
        k = int( rng.integers( 2, 6 ) )
        while k < m - 2:
            ang = math.atan2( pts[k + 1][1] - pts[k - 1][1], pts[k + 1][0] - pts[k - 1][0] )
            L = rng.uniform( 0.35, 0.55 ) * p * size
            pile.layers.ellipse( pts[k][0], pts[k][1], L, 0.55 * L, ang, np.clip( cols[k] * bladder, 0, 255 ),
                                 float( lv[k] ) + 1.8 * pile.dt, aux * 0.8 )
            k += int( rng.integers( 6, 11 ) )
        if first and m > 6:
            first = False
            for _ in range( int( rng.integers( 0, 3 ) ) ):
                j = int( rng.integers( 2, m - 3 ) )
                ang = math.atan2( pts[j + 1][1] - pts[j][1], pts[j + 1][0] - pts[j][0] )
                shoots.append( ( pts[j][0], pts[j][1], ang + rng.choice( ( -1, 1 ) ) * rng.uniform( 0.3, 0.7 ),
                                 rng.uniform( 3, 8 ) * p * size, 0.26 ) )


def _oarweed( pile, rng, x, y, angle, p, size, dry=0.0 ):
    """ Oarweed (Laminaria) torn off and cast up: a holdfast of branching root-like haptera, a round stipe a foot or
    two long tapering from an inch thick, rough and pale brown, then the blade: a dark brown leathery palm split into
    straps an inch to three wide, overlapping, glossy. """
    hold = np.array( ( 86, 66, 40 ) ) * rng.uniform( 0.9, 1.1 )
    for _ in range( int( rng.integers( 5, 9 ) ) ):
        pts, _ = _frond_path( rng, x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 1.0, 2.5 ) * p * size, 0.4 * p, 0.25 )
        _strap( pile, pts, [ 0.22 * p * size ] * len( pts ), hold, 1.5, 0.6 )
    pts, a_end = _frond_path( rng, x, y, angle, rng.uniform( 12, 26 ) * p * size, 0.8 * p, 0.04 )
    m = len( pts )
    w = [ ( 0.95 - 0.45 * k / ( m - 1 ) ) * p * size for k in range( m ) ]
    stipe = np.array( ( 114, 90, 58 ) ) * rng.uniform( 0.9, 1.1 )
    cols = [ stipe * rng.uniform( 0.93, 1.07 ) for _ in range( m - 1 ) ]
    lv = _strap( pile, pts, w, cols, 2.5 * size, 0.55 )
    pile.layers.ribbon( pts, [ 0.35 * wk for wk in w ], [ np.clip( c * 1.15, 0, 255 ) for c in cols ],
                        list( 0.5 * ( lv[:-1] + lv[1:] ) + 0.8 * pile.dt ), 0.5 )
    ex, ey = pts[-1]
    blade = np.array( ( 58, 42, 20 ) ) * rng.uniform( 0.85, 1.15 )
    for _ in range( int( rng.integers( 4, 8 ) ) ):
        pts2, _ = _frond_path( rng, ex + rng.normal( 0, 0.6 * p ), ey + rng.normal( 0, 0.6 * p ),
                               a_end + rng.normal( 0, 0.35 ), rng.uniform( 12, 28 ) * p * size, 0.9 * p, 0.06 )
        mm = len( pts2 )
        wd = rng.uniform( 1.0, 2.6 ) * p * size
        ws = [ wd * min( 1.0, 0.45 + 0.4 * k ) * ( 1 - 0.3 * k / mm ) for k in range( mm ) ]
        ws[-1] *= 0.5
        cs = [ np.clip( _dried( blade * ( 0.92 + 0.16 * k / mm ) * rng.uniform( 0.96, 1.04 ), dry ), 0, 255 )
               for k in range( mm - 1 ) ]
        _strap( pile, pts2, ws, cs, 1.4, 0.18 + 0.5 * dry )


def _strand( pile, rng, x, y, p, kind ):
    """ The thin things in a strand line: bootlace weed (a dark glossy cord a few feet long), eelgrass (narrow flat
    green-brown blades, several together) or a bit of blue or orange polypropylene twine, kinked. """
    a = rng.uniform( 0, 2 * math.pi )
    if kind == "bootlace":
        pts, _ = _frond_path( rng, x, y, a, rng.uniform( 20, 50 ) * p, 0.8 * p, 0.12 )
        w = rng.uniform( 0.12, 0.2 ) * p
        _strap( pile, pts, [ w ] * len( pts ), np.array( ( 54, 44, 22 ) ) * rng.uniform( 0.85, 1.1 ), 0.8, 0.2 )
    elif kind == "eelgrass":
        col = np.array( ( 72, 74, 38 ) ) * rng.uniform( 0.85, 1.1 )
        for _ in range( int( rng.integers( 3, 7 ) ) ):
            pts, _ = _frond_path( rng, x + rng.normal( 0, 0.3 * p ), y + rng.normal( 0, 0.3 * p ),
                                  a + rng.normal( 0, 0.3 ), rng.uniform( 10, 24 ) * p, 0.7 * p, 0.06 )
            _strap( pile, pts, [ 0.22 * p ] * len( pts ), col * rng.uniform( 0.9, 1.1 ), 0.6, 0.3 )
    else:
        col = np.array( ( 40, 92, 168 ) if rng.random() < 0.6 else ( 214, 104, 34 ) ) * rng.uniform( 0.85, 1.05 )
        pts, _ = _frond_path( rng, x, y, a, rng.uniform( 6, 18 ) * p, 0.5 * p, 0.35 )
        _strap( pile, pts, [ 0.09 * p ] * len( pts ), col, 0.8, 0.6 )


def _twig( pile, rng, x, y, p ):
    """ A stick of driftwood: bark gone and bleached silver-grey, or still brown, rounded (a lighter line along its
    top). """
    pts, _ = _frond_path( rng, x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 6, 20 ) * p, 0.8 * p, 0.04 )
    m = len( pts )
    w0 = rng.uniform( 0.4, 1.0 ) * p
    w = [ w0 * ( 1 - 0.35 * k / m ) for k in range( m ) ]
    col = np.array( ( 150, 142, 128 ) if rng.random() < 0.7 else ( 98, 74, 52 ) ) * rng.uniform( 0.9, 1.1 )
    cols = [ col * rng.uniform( 0.94, 1.06 ) for _ in range( m - 1 ) ]
    lv = _strap( pile, pts, w, cols, ( w0 / p ) / ( pile.dt * pile.span ), 0.75 )
    pile.layers.ribbon( pts, [ 0.4 * wk for wk in w ], [ np.clip( c * 1.12, 0, 255 ) for c in cols ],
                        list( 0.5 * ( lv[:-1] + lv[1:] ) + 0.3 * pile.dt ), 0.72 )


def _shell( pile, rng, x, y, p ):
    """ A shell lying on the pile or the sand: a blue-black mussel (some open, the nacre showing), a ribbed buff
    cockle, a limpet or a whelk. """
    level = float( pile.under( [ ( x, y ) ] )[0] )
    ang = rng.uniform( 0, math.pi )
    kind = rng.choice( 4, p=( 0.45, 0.3, 0.15, 0.1 ) )
    if kind == 0:
        L = rng.uniform( 0.9, 1.3 ) * p
        col = np.array( ( 40, 44, 56 ) ) * rng.uniform( 0.85, 1.15 )
        pile.layers.ellipse( x, y, L, 0.45 * L, ang, col, level + 4 * pile.dt, 0.35 )
        if rng.random() < 0.3:
            pile.layers.ellipse( x, y, 0.8 * L, 0.32 * L, ang, ( 150, 160, 178 ), level + 4.5 * pile.dt, 0.2 )
        else:
            pile.layers.ellipse( x + 0.1 * L * math.cos( ang ), y + 0.1 * L * math.sin( ang ), 0.6 * L, 0.18 * L, ang,
                                 np.clip( col * 1.6, 0, 255 ), level + 4.6 * pile.dt, 0.3 )
    elif kind == 1:
        r = rng.uniform( 0.45, 0.6 ) * p
        col = np.array( ( 210, 196, 172 ) ) * rng.uniform( 0.9, 1.05 )
        pile.layers.ellipse( x, y, r, 0.9 * r, ang, col * 0.85, level + 4 * pile.dt, 0.6 )
        pile.layers.ellipse( x, y - 0.1 * r, 0.7 * r, 0.62 * r, ang, col, level + 5 * pile.dt, 0.6 )
    elif kind == 2:
        r = rng.uniform( 0.5, 0.7 ) * p
        col = np.array( ( 148, 134, 110 ) ) * rng.uniform( 0.9, 1.1 )
        pile.layers.ellipse( x, y, r, 0.85 * r, ang, col * 0.85, level + 4 * pile.dt, 0.7 )
        pile.layers.ellipse( x, y, 0.55 * r, 0.47 * r, ang, col, level + 6 * pile.dt, 0.7 )
        pile.layers.ellipse( x, y, 0.15 * r, 0.13 * r, ang, col * 1.2, level + 7 * pile.dt, 0.7 )
    else:
        L = rng.uniform( 0.7, 1.0 ) * p
        col = np.array( ( 184, 168, 142 ) ) * rng.uniform( 0.9, 1.05 )
        pile.layers.ellipse( x, y, L, 0.55 * L, ang, col * 0.85, level + 4 * pile.dt, 0.6 )
        pile.layers.ellipse( x - 0.3 * L * math.cos( ang ), y - 0.3 * L * math.sin( ang ), 0.5 * L, 0.38 * L, ang, col,
                             level + 6 * pile.dt, 0.6 )


def _feather( pile, rng, x, y, p ):
    """ A gull's feather: a white or grey vane either side of its quill. """
    a = rng.uniform( 0, 2 * math.pi )
    L = rng.uniform( 3, 6 ) * p
    pts, _ = _frond_path( rng, x, y, a, L, 0.4 * p, 0.03 )
    m = len( pts )
    col = np.array( ( 222, 222, 216 ) if rng.random() < 0.6 else ( 150, 152, 150 ) ) * rng.uniform( 0.95, 1.03 )
    w = [ 0.5 * p * math.sin( math.pi * min( 0.95, 0.1 + k / ( m - 1 ) ) ) + 0.1 * p for k in range( m ) ]
    lv = _strap( pile, pts, w, col, 0.8, 0.8 )
    pile.layers.ribbon( pts, [ 0.08 * p ] * m, np.clip( col * 1.05, 0, 255 ), list( 0.5 * ( lv[:-1] + lv[1:] ) + 0.4 * pile.dt ),
                        0.6 )


def _joint_set( rng, n, a, b, wobble ):
    """ The distance in px to the nearest joint of a set: the lines where ( a x + b y ) / n is a whole number (so they
    wrap), bent gently and unevenly spaced by low-frequency noise (wobble, a share of their spacing). """
    x, y = coords( n )
    phase = ( a * x + b * y ) / n + wobble * ( noise( rng, n, 3.0, 1, 3 ) + 0.12 * noise( rng, n, 2.0, 3, 10 ) )
    return np.abs( phase - np.round( phase ) ) * n / math.hypot( a, b )


def _blocks( barrier ):
    """ The regions between barriers (bool), joined round the tile's edges: ( each px's region 0..count-1, the count ).
    A barrier px takes its nearest region. """
    lab, count = _wrap_label( ~barrier )
    idx = ndimage.distance_transform_edt( lab < 0, return_distances=False, return_indices=True )
    return lab[idx[0], idx[1]], count


def _colonies( rng, n, count, radius, density=None, lobes=0.16, soft=1.0 ):
    """ Lichen colonies: round patches with lobed edges, radius px drawn log-uniformly from the range, placed where
    density (0..1) is high, each over the ones before. Returns ( cover 0..1, the share of the way out from its centre
    0..1, the colony each px is in (-1 none) ). """
    cover = np.zeros( ( n, n ) )
    inner = np.ones( ( n, n ) )
    who = np.full( ( n, n ), -1 )
    placed = 0
    for _ in range( count * 40 ):
        if placed >= count:
            break
        x, y = rng.uniform( 0, n, 2 )
        if density is not None and rng.random() > density[int( y ) % n, int( x ) % n]:
            continue
        r = math.exp( rng.uniform( math.log( radius[0] ), math.log( radius[1] ) ) )
        R = int( math.ceil( r * ( 1 + 3 * lobes ) + soft ) ) + 1
        xs = np.arange( int( x ) - R, int( x ) + R + 1 )
        ys = np.arange( int( y ) - R, int( y ) + R + 1 )
        u = xs[None, :] + 0.5 - x
        v = ys[:, None] + 0.5 - y
        th = np.arctan2( v, u )
        rr = np.full( th.shape, r )
        for k in rng.integers( 3, 9, 3 ):
            rr = rr + r * lobes * rng.uniform( 0.3, 1.0 ) * np.sin( k * th + rng.uniform( 0, 2 * math.pi ) )
        d = np.hypot( u, v ) / rr
        w = np.clip( ( 1.0 - d ) * r / soft + 0.5, 0, 1 )
        rows, cols = np.ix_( ys % n, xs % n )
        win = w > 0.5
        who[rows, cols] = np.where( win, placed, who[rows, cols] )
        inner[rows, cols] = np.where( win, np.clip( d, 0, 1 ), inner[rows, cols] )
        cover[rows, cols] = np.maximum( cover[rows, cols], w )
        placed += 1
    return cover, inner, who


def _lichen( c, rng, n, count, radius, density, colour, alpha, spread=0.06, rim=0.0, rim_colour=( 40, 40, 38 ),
             lobes=0.16, texture=None ):
    """ One kind of lichen over colour c: count colonies (see _colonies), each its own shade of colour (spread), mixed
    in at alpha, mottled by texture (a unit field), with a rim (rim 0..1: how strongly its edge goes to rim_colour; a
    map lichen's black prothallus). Returns ( colour, cover ). """
    cov, inner, who = _colonies( rng, n, count, radius, density, lobes )
    shades = np.asarray( colour, float ) * rng.uniform( 1 - spread, 1 + spread, ( count, 1 ) )
    lc = shades[np.maximum( who, 0 )]
    lum = 1.0 + ( 0.07 * texture if texture is not None else 0.0 ) - 0.05 * smoothstep( 0.6, 0.0, inner )
    lc = BT.shade( lc, lum )
    if rim:
        lc = mix( lc, rim_colour, rim * smoothstep( 0.8, 0.95, inner ) )
    return mix( c, lc, alpha * cov ), cov


def _kelp_plant( pile, rng, x, y, current, p, size ):
    """ A kelp plant (Laminaria) on the seabed seen from above: a short stipe from its holdfast, then its blade split
    into fingers lying downstream with the current, dark olive-brown, lighter and greener at their tips, glossy. """
    a = current + rng.normal( 0, 0.45 )
    pts, a_end = _frond_path( rng, x, y, a, rng.uniform( 6, 14 ) * p * size, 1.0 * p, 0.03 )
    stipe = np.array( ( 108, 86, 54 ) ) * rng.uniform( 0.9, 1.1 )
    _strap( pile, pts, [ 1.6 * p * size ] * len( pts ), stipe, 2.0, 0.5 )
    bx, by = pts[-1]
    blade = np.array( ( 66, 52, 24 ) ) * rng.uniform( 0.85, 1.15 )
    fingers = int( rng.integers( 4, 9 ) )
    for k in range( fingers ):
        fa = a_end + ( k - ( fingers - 1 ) / 2 ) * rng.uniform( 0.06, 0.14 ) + rng.normal( 0, 0.05 )
        L = rng.uniform( 22, 48 ) * p * size
        fp, _ = _frond_path( rng, bx, by, fa, L, 1.2 * p, 0.02 )
        m = len( fp )
        wd = rng.uniform( 2.5, 5.5 ) * p * size
        ws = [ wd * min( 1.0, 0.5 + 0.25 * j ) * ( 1 - 0.4 * j / m ) for j in range( m ) ]
        ws[-1] *= 0.5
        cs = [ np.clip( blade * ( 0.9 + 0.3 * j / m ) * rng.uniform( 0.96, 1.04 ), 0, 255 ) for j in range( m - 1 ) ]
        _strap( pile, fp, ws, cs, 1.0, 0.25 )


def _starfish( pile, rng, x, y, p ):
    """ A common starfish, five arms. """
    level = float( pile.under( [ ( x, y ) ] )[0] )
    a0 = rng.uniform( 0, 2 * math.pi )
    L = rng.uniform( 3, 5 ) * p
    col = np.array( ( 176, 104, 58 ) ) * rng.uniform( 0.85, 1.1 )
    for k in range( 5 ):
        a = a0 + 2 * math.pi * k / 5 + rng.normal( 0, 0.1 )
        pts = [ ( x, y ), ( x + math.cos( a ) * L * 0.5, y + math.sin( a ) * L * 0.5 ), ( x + math.cos( a ) * L, y + math.sin( a ) * L ) ]
        pile.layers.ribbon( pts, [ 1.2 * p, 0.9 * p, 0.35 * p ], col, level + 3 * pile.dt, 0.7 )


def sample_wrap( field, x, y ):
    """ field (n x n, tiling) read at px positions x, y (any shape), bilinearly, wrapping round the tile. """
    return ndimage.map_coordinates( field, [ np.asarray( y ) - 0.5, np.asarray( x ) - 0.5 ], order=1,
                                    mode="grid-wrap" )


def _wrap_label( mask ):
    """ The connected regions of mask (bool), joined round the tile's edges: ( each px's region 0.., -1 outside the
    mask; the count ). """
    lab, count = ndimage.label( mask )
    parent = np.arange( count + 1 )

    def find( i ):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in zip( np.concatenate( [ lab[0, :], lab[:, 0] ] ), np.concatenate( [ lab[-1, :], lab[:, -1] ] ) ):
        if a and b:
            ra, rb = find( a ), find( b )
            if ra != rb:
                parent[max( ra, rb )] = min( ra, rb )
    roots = np.array( [ find( i ) for i in range( count + 1 ) ] )
    _, compact = np.unique( roots, return_inverse=True )
    lab = compact.reshape( -1 )[lab]
    return lab - 1, int( lab.max() )


def nearest_wrap( mask, margin ):
    """ For each px, ( row, col ) of the nearest px of mask (bool), looking round the tile's edges up to margin px. """
    n = mask.shape[0]
    big = np.pad( mask, margin, mode="wrap" )
    idx = ndimage.distance_transform_edt( ~big, return_distances=False, return_indices=True )
    rows = ( idx[0][margin:margin + n, margin:margin + n] - margin ) % n
    cols = ( idx[1][margin:margin + n, margin:margin + n] - margin ) % n
    return rows, cols


def _smear( fields, flow, length, step, signs=( 1.0, -1.0 ) ):
    """ Each of fields (n x n) smeared along the headings flow (n x n, radians) out to length px (both ways, or only
    the signs given), weighted by a tent: line integral convolution, which turns noise into strands lying along the
    flow. """
    n = flow.shape[0]
    fx, fy = np.cos( flow ), np.sin( flow )
    steps = max( 1, int( round( length / step ) ) )
    out = [ np.array( f, float ) for f in fields ]
    total = 1.0
    for sign in signs:
        x, y = coords( n )
        for k in range( 1, steps + 1 ):
            hx, hy = sample_wrap( fx, x, y ), sample_wrap( fy, x, y )
            x = x + sign * step * hx
            y = y + sign * step * hy
            w = 1.0 - k / ( steps + 1.0 )
            for o, f in zip( out, fields ):
                o += w * sample_wrap( f, x, y )
            total += w
    return [ o / total for o in out ]


def _weed_mat( rng, n, p, flow, cover, tones, strand=0.45, length=10.0, bladders=0.12, hang=False ):
    """ Wrack lying in a mat combed along flow (n x n headings, radians) where cover (0..1) is high, its edges drawn out
    into trailing fronds: noise smeared along the flow into fronds about strand inches wide and length inches long
    (with finer ones a third as wide among them), each its own tone from tones ( ( weight, rgb ), ... ), lying over one
    another, with egg-shaped bladders (bladders an square inch of mat) swelling some. If hang, the mat hangs from
    where cover is: it runs on down the flow from there, its tips ragged. Returns ( colour, thickness in inches, cover
    0..1, roughness ). """
    seed = unit( T.blur( rng.random( ( n, n ) ) - 0.5, 0.3 * strand * p ) ) \
        + 0.35 * unit( T.blur( rng.random( ( n, n ) ) - 0.5, max( 0.5, 0.1 * strand * p ) ) )
    tone_seed = T.blur( rng.random( ( n, n ) ) - 0.5, 0.45 * strand * p )
    s, t, c = _smear( [ seed, tone_seed, cover ], flow, 0.5 * length * p, max( 1.0, 0.35 * p ) )
    if hang:
        c = _smear( [ cover ], flow, length * p, max( 1.0, 0.35 * p ), signs=( -1.0, ) )[0]
    s, t = unit( s ), unit( t )
    mat = smoothstep( 0.4, 0.6, c + 0.1 * s )
    weights = np.array( [ w for w, _ in tones ], float )
    cuts = np.quantile( t, np.cumsum( weights / weights.sum() )[:-1] )
    rgb = np.array( [ col for _, col in tones ], float )[np.searchsorted( cuts, t )]
    # Each frond rounded across: dark in the gaps between, fullest along its middle.
    rope = smoothstep( -1.4, 0.9, s )
    lum = ( 0.66 + 0.4 * np.sqrt( rope ) ) * ( 0.85 + 0.15 * smoothstep( 0.4, 0.8, c ) )
    colour = BT.shade( rgb, lum )
    thick = mat * ( 0.3 + 0.5 * smoothstep( 0.45, 0.9, c ) ) + 0.14 * ( np.sqrt( rope ) - 0.5 ) * mat
    # Bladders: eggs along the fronds, lighter and catching the light.
    blad = np.zeros( ( n, n ) )
    count = int( bladders * float( mat.sum() ) / p ** 2 )
    placed = 0
    for _ in range( 4 * count ):
        if placed >= count:
            break
        x, y = rng.uniform( 0, n, 2 )
        i, j = int( y ) % n, int( x ) % n
        if mat[i, j] < 0.6 or s[i, j] < 0.2:
            continue
        L = rng.uniform( 0.25, 0.45 ) * p
        stamp( blad, x, y, L, 0.6 * L, 1.0, angle=float( flow[i, j] ), profile="dome" )
        placed += 1
    colour = BT.shade( colour, 1.0 + 0.3 * blad )
    colour = mix( colour, colour * np.array( [ 1.06, 1.08, 1.0 ] ), 0.5 * blad )
    thick = thick + 0.25 * blad * mat
    rough = 0.2 + 0.06 * smoothstep( -1, 1, s ) - 0.05 * blad
    return colour, thick, mat, rough


def _facets( rng, n, spacing, radius, depth, jitter=0.45 ):
    """ Planishing: a hand-beaten sheet's shallow round facets, one hammer blow each, spacing px apart and about
    radius px across: ( height in inches, a dish depth deep each, ridged where they meet; each px's facet; its distance
    from the facet's centre over its radius ). """
    pts = jittered( rng, n, spacing, jitter )
    rad = rng.uniform( 0.8, 1.2, len( pts ) ) * radius
    who, d, _ = packed( rng, n, pts, rad )
    height = depth * ( np.minimum( d, 1.4 ) ** 2 - 0.6 )
    return height, who, d


def _ring( field, x, y, r, width, fill=0.25 ):
    """ A dried drop's ring into field (wrapping): 1 on its rim, about width px wide, fill inside. """
    n = field.shape[0]
    reach = int( math.ceil( r + width + 1 ) ) + 1
    xs = np.arange( int( x ) - reach, int( x ) + reach + 1 )
    ys = np.arange( int( y ) - reach, int( y ) + reach + 1 )
    d = np.hypot( xs[None, :] + 0.5 - x, ys[:, None] + 0.5 - y )
    w = np.maximum( np.clip( 1.0 - np.abs( d - r ) / max( width, 0.5 ), 0, 1 ), fill * np.clip( r - d, 0, 1 ) )
    rows, cols = np.ix_( ys % n, xs % n )
    field[rows, cols] = np.maximum( field[rows, cols], w )


def _water_spots( rng, n, count, radius, width ):
    """ count dried drops (radius px, a range), 0..1: a ring each, faintly filled, some in little clusters. """
    field = np.zeros( ( n, n ) )
    k = 0
    while k < count:
        cx, cy = rng.uniform( 0, n, 2 )
        for _ in range( int( rng.integers( 1, 5 ) ) ):
            r = rng.uniform( *radius )
            _ring( field, cx + rng.normal( 0, 3 * radius[1] ), cy + rng.normal( 0, 3 * radius[1] ), r, width )
            k += 1
    return field


def _hand_marks( rng, n, count, p ):
    """ count greasy hand marks (p px an inch), 0..1: a palm's smear with four finger pads in an arc beyond it, each
    soft-edged, at every angle. """
    field = np.zeros( ( n, n ) )
    for _ in range( count ):
        x, y = rng.uniform( 0, n, 2 )
        a = rng.uniform( 0, 2 * math.pi )
        s = rng.uniform( 0.85, 1.15 )
        strength = rng.uniform( 0.4, 1.0 )
        if rng.random() < 0.6:
            stamp( field, x, y, 1.3 * p * s, 1.0 * p * s, 0.6 * strength, angle=a, soft=0.8 * p )
        for k, off in enumerate( ( -0.45, -0.15, 0.15, 0.42 ) ):
            reach = ( 2.4 + ( 0.3 if 0 < k < 3 else 0.0 ) ) * p * s
            fa = a + off
            stamp( field, x + math.cos( fa ) * reach, y + math.sin( fa ) * reach, 0.42 * p * s, 0.3 * p * s,
                   strength * rng.uniform( 0.6, 1.0 ), angle=fa, soft=0.3 * p )
    return field


@texture( "copper_bright" )
def copper_bright( rng, n ):
    """ Polished copper, 8 px an inch: the bands round a still and the necks kept bright. A hand-beaten sheet (the
    hammer's shallow facets an inch across), buffed along the band so fine scratches run across the picture, a soft
    tarnish coming back where the cloth misses, greasy hand marks and dried water spots. """
    p = n / 64.0
    height, who, d = _facets( rng, n, 1.0 * p, 0.62 * p, 0.01 )
    fine = BT.stretched( rng, n, 0.6, n / 8, n / 2, ( 0.3, 10 * p ) )
    coarse = BT.stretched( rng, n, 1.2, 8, n / 8, ( 0.6, 24 * p ) )
    tarnish = smoothstep( 0.2, 2.2, noise( rng, n, 2.8, 1, 10 ) + 0.35 * noise( rng, n, 2.0, 10, 40 ) )
    hands = _hand_marks( rng, n, 5, p )
    spots = _water_spots( rng, n, 30, ( 0.08 * p, 0.25 * p ), 0.05 * p )
    facet_tone = rng.normal( 0, 0.02, who.max() + 1 )[who]
    c = lum_paint( ( 236, 140, 98 ), 1.0 + 0.04 * fine + 0.03 * coarse + facet_tone
                   + 0.03 * noise( rng, n, 2.5, 1, 20 ) )
    c = mix( c, ( 190, 110, 78 ), 0.45 * tarnish )
    c = mix( c, ( 176, 100, 72 ), 0.18 * hands )
    c = mix( c, ( 216, 160, 130 ), 0.22 * spots )
    height = height + 0.0008 * fine + 0.0006 * coarse
    rough = np.clip( 0.12 + 0.03 * smoothstep( -2, 2, fine ) + 0.1 * tarnish + 0.14 * hands + 0.1 * spots, 0, 1 )
    return { "sh_copper_bright": c }, rough, height, 1024 / 64


@texture( "copper" )
def copper( rng, n ):
    """ A still's working copper, 10.7 px an inch: the hand-beaten sheet (the hammer's facets an inch or so across,
    each catching the light its own way, and the odd dent) gone a dull brown with years of heat: mottled with darker
    oxide that runs down the picture in streaks, rubbed brighter where hands and cloths reach, tinted by the heat in
    soft bands (rose, gold) and marked by condensation runs. """
    p = n / 96.0
    height, who, d = _facets( rng, n, 1.3 * p, 0.8 * p, 0.014 )
    dents = dots( rng, n, 10, ( 0.8 * p, 2.0 * p ), profile="dome", soft=1.0 )
    height = height - 0.05 * dents
    mottle = noise( rng, n, 2.4, 2, 60 )
    runs = unit( BT.stretched( rng, n, 1.4, 3, 80, ( 26 * p, 1.2 * p ) ) )
    dark = smoothstep( -0.3, 1.9, noise( rng, n, 2.7, 1, 16 ) + 0.45 * runs )
    rub = smoothstep( 1.0, 2.4, noise( rng, n, 2.8, 1, 10 ) + 0.3 * noise( rng, n, 2.0, 10, 30 ) ) * ( 1 - 0.6 * dark )
    x, y = coords( n )
    band = np.sin( 2 * np.pi * ( 2 * y / n + 0.25 * noise( rng, n, 2.5, 1, 6 ) ) )
    drips = np.zeros( ( n, n ) )
    for _ in range( 40 ):
        stamp( drips, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.2, 0.5 ) * p, 0.3 * p, 1.0, soft=0.5 )
    wet = wash_down( drips, 30 * p, 0.8, rng, keep=0.8 )
    facet_tone = rng.normal( 0, 0.035, who.max() + 1 )[who]
    c = lum_paint( ( 158, 90, 56 ), 1.0 + 0.07 * mottle + facet_tone + 0.03 * runs )
    c = mix( c, ( 96, 56, 38 ), 0.6 * dark )
    c = mix( c, ( 124, 72, 72 ), 0.16 * smoothstep( 0.3, 1.0, band ) )
    c = mix( c, ( 176, 120, 62 ), 0.12 * smoothstep( 0.3, 1.0, -band ) )
    c = mix( c, ( 204, 124, 84 ), 0.6 * rub )
    c = mix( c, ( 82, 52, 40 ), 0.3 * wet )
    c = mix( c, ( 112, 66, 46 ), 0.35 * dents )
    rough = np.clip( 0.44 + 0.03 * mottle + 0.1 * dark - 0.2 * rub + 0.08 * wet, 0.2, 0.8 )
    return { "sh_copper": c }, rough, height, 1024 / 96


@texture( "copper_green" )
def copper_green( rng, n ):
    """ Copper left out in the weather, 5.3 px an inch: a crust of verdigris, chalky green-blue, mottled and streaked
    down the picture by the rain (paler where it runs off, darker where dirt settles), with the brown copper showing
    through here and there, dirt washed down from it; powdery and matt. """
    p = n / 96.0
    base = noise( rng, n, 2.4, 2, 40 )
    streak = unit( BT.stretched( rng, n, 1.2, 4, 120, ( 16 * p, 0.8 * p ) ) )
    powder = grain_field( rng, n, 0.6, 3.0 )
    tone = smoothstep( -1.6, 1.6, 0.6 * base + 0.7 * streak )
    c = mix( ( 66, 112, 94 ), ( 124, 174, 154 ), tone )
    c = lum_paint( c, 1.0 + 0.04 * powder + 0.03 * noise( rng, n, 1.5, 20, n / 3 ) )
    bare_f = noise( rng, n, 2.2, 3, 50 ) + 0.25 * noise( rng, n, 1.4, 50, 200 )
    bare = smoothstep( 1.45, 1.9, bare_f )
    halo = smoothstep( 0.9, 1.45, bare_f ) * ( 1 - bare )
    under = mix( ( 104, 72, 50 ), ( 50, 42, 36 ), smoothstep( -1, 1, noise( rng, n, 2.0, 4, 40 ) ) )
    c = mix( c, ( 58, 92, 76 ), 0.5 * halo )
    c = mix( c, under, bare )
    dirt = wash_down( bare, 22 * p, 0.8, rng, keep=0.6 ) * ( 1 - bare )
    c = mix( c, ( 58, 70, 60 ), 0.35 * dirt )
    height = 0.015 * smoothstep( -1, 1, base ) + 0.006 * powder * ( 1 - bare ) - 0.012 * bare \
        + 0.004 * streak
    rough = np.clip( 0.8 + 0.04 * powder / 2 - 0.3 * bare - 0.05 * dirt, 0, 1 )
    return { "sh_copper_green": c }, rough, height, 1024 / 96


@texture( "brass" )
def brass( rng, n ):
    """ Brass, 10.7 px an inch: the spirit safe's frame, valves and plates, polished by hand for years: fine buffing
    scratches in long swirls, gone a soft brown where the polish doesn't reach, with hand marks, water spots and a few
    tiny dents. """
    p = n / 48.0
    flow = 2.2 * noise( rng, n, 3.0, 1, 4 )
    seed = T.blur( rng.random( ( n, n ) ) - 0.5, 0.4 )
    swirl = unit( _smear( [ seed ], flow, 4 * p, 1.0 )[0] )
    tarnish = smoothstep( 0.0, 2.2, noise( rng, n, 2.8, 1, 10 ) + 0.35 * noise( rng, n, 2.0, 10, 40 ) )
    hands = _hand_marks( rng, n, 3, p )
    spots = _water_spots( rng, n, 16, ( 0.06 * p, 0.2 * p ), 0.04 * p )
    dents = dots( rng, n, 14, ( 0.05 * p, 0.15 * p ), profile="dome", soft=0.6 )
    wave = 0.006 * noise( rng, n, 3.0, 1, 8 )
    c = lum_paint( ( 212, 170, 92 ), 1.0 + 0.045 * swirl + 0.03 * noise( rng, n, 2.0, 2, 30 ) )
    c = mix( c, ( 156, 118, 62 ), 0.5 * tarnish )
    c = mix( c, ( 142, 108, 62 ), 0.18 * hands )
    c = mix( c, ( 202, 178, 132 ), 0.22 * spots )
    height = wave + 0.0006 * swirl - 0.01 * dents
    rough = np.clip( 0.16 + 0.04 * smoothstep( -2, 2, swirl ) + 0.14 * tarnish + 0.14 * hands + 0.1 * spots, 0, 1 )
    return { "sh_brass": c }, rough, height, 1024 / 48


@texture( "steel_paint" )
def steel_paint( rng, n ):
    """ Painted steel plate, 10.7 px an inch (sh_steel grey, sh_steel_green the green of pipes, stands and
    railings): gloss gone semi-matt in the salt air, chalkier in patches, a faint orange peel and the odd sag; knocks
    have chipped flakes off it, down to the red-oxide primer round their edges and to the steel in their middles,
    which has rusted; rust blisters swell under the paint, and rust bleeds down the plate from both; grime streaks;
    fine scratches. """
    p = n / 96.0
    peel = noise( rng, n, 1.0, n / 14, n / 3 )
    chalk = smoothstep( 0.4, 2.2, noise( rng, n, 2.6, 1, 14 ) + 0.3 * noise( rng, n, 2.0, 14, 50 ) )
    # Chips: irregular flakes of every size, in clusters where things knock it.
    dens = noise( rng, n, 2.6, 1, 10 )
    flake = noise( rng, n, 2.0, 12, 140 ) + 0.18 * noise( rng, n, 1.0, 140, n / 3 ) + 0.75 * dens
    q_primer, q_chip = np.quantile( flake, 0.972 ), np.quantile( flake, 0.986 )
    primer = smoothstep( q_primer - 0.02, q_primer + 0.02, flake )
    chip = smoothstep( q_chip - 0.03, q_chip + 0.03, flake )
    # Rust blisters under the paint.
    blister = np.zeros( ( n, n ) )
    for _ in range( 30 ):
        cx, cy = rng.uniform( 0, n, 2 )
        for _ in range( int( rng.integers( 1, 5 ) ) ):
            r = rng.uniform( 0.12, 0.45 ) * p
            stamp( blister, cx + rng.normal( 0, 0.8 * p ), cy + rng.normal( 0, 0.8 * p ), r,
                   r * rng.uniform( 0.7, 1.0 ), 1.0, angle=rng.uniform( 0, 3.2 ), profile="dome" )
    rust_src = np.maximum( blister, chip )
    bleed = wash_down( rust_src * 0.8, 12 * p, 0.8, rng, keep=0.6 ) * ( 1 - rust_src )
    grime = smoothstep( 0.6, 2.2, unit( BT.stretched( rng, n, 1.3, 3, 60, ( 30 * p, 1.5 * p ) ) ) )
    scratches = crack_lines( rng, n, 18, ( 3 * p, 14 * p ), 0.5, branch=0.0, turn=0.03 )
    sags = np.zeros( ( n, n ) )
    for _ in range( 5 ):
        stamp( sags, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.3, 0.7 ) * p, rng.uniform( 1.0, 2.5 ) * p,
               1.0, profile="dome" )
    rust_c = mix( ( 116, 62, 32 ), ( 72, 44, 30 ), smoothstep( -1, 1, noise( rng, n, 1.5, 20, 120 ) ) )

    def painted( base, chalky, grimy ):
        c = lum_paint( base, 1.0 + 0.012 * peel + 0.025 * noise( rng, n, 2.4, 1, 30 ) )
        c = mix( c, chalky, 0.4 * chalk )
        c = mix( c, grimy, 0.25 * grime )
        c = mix( c, ( 132, 62, 42 ), primer )
        c = mix( c, rust_c, chip )
        c = mix( c, rust_c, 0.9 * smoothstep( 0.2, 0.6, blister ) )
        c = mix( c, ( 122, 74, 44 ), 0.4 * bleed )
        c = mix( c, ( 96, 94, 92 ), 0.45 * scratches * ( 1 - primer ) )
        return c

    grey = painted( ( 146, 150, 152 ), ( 170, 172, 170 ), ( 112, 112, 106 ) )
    green = painted( ( 38, 82, 70 ), ( 72, 100, 90 ), ( 34, 52, 44 ) )
    height = 0.0012 * peel + 0.004 * sags - 0.006 * primer - 0.004 * chip + 0.02 * blister - 0.002 * scratches
    rough = np.clip( 0.42 + 0.02 * peel + 0.16 * chalk + 0.06 * grime + 0.2 * primer + 0.2 * chip + 0.35 * blister
                     + 0.12 * bleed + 0.1 * scratches, 0, 1 )
    return { "sh_steel": grey, "sh_steel_green": green }, rough, height, 1024 / 96


@texture( "rust" )
def rust( rng, n ):
    """ Steel left to rust, 5.3 px an inch: plate gone to a crust of rust, orange-brown mottled with dark scale,
    flaking in layers (each flake's edge lifting and catching the light), pitted, powdery yellow-orange where it's
    freshest and darker where it stays wet, with a patch or two of the old paint left. """
    p = n / 96.0
    cell, border, off = cells( rng, n, jittered( rng, n, 2.6 * p, 0.45 ), wander=0.9 * p, wander_f=( 6, 60 ) )
    count = cell.max() + 1
    lifted = rng.random( count ) < 0.45
    lev = rng.normal( 0, 0.012, count )
    tilt = rng.normal( 0, 0.004 / p, ( count, 2 ) )
    edge_lift = smoothstep( 0.8 * p, 0.0, border ) * lifted[cell]
    pits = dots( rng, n, 260, ( 0.08 * p, 0.3 * p ), profile="dome", soft=0.5 )
    mottle = noise( rng, n, 2.4, 2, 40 )
    fine = noise( rng, n, 1.0, n / 6 )
    height = lev[cell] + tilt[cell, 0] * off[..., 0] + tilt[cell, 1] * off[..., 1] + 0.02 * edge_lift \
        - 0.015 * smoothstep( 0.3 * p, 0.0, border ) - 0.03 * pits + 0.004 * fine + 0.02 * noise( rng, n, 2.6, 2, 30 )
    tone = rng.uniform( 0.85, 1.15, count )[cell]
    c = lum_paint( ( 124, 64, 32 ), tone * ( 1.0 + 0.08 * mottle + 0.05 * fine ) )
    scale = smoothstep( 0.4, 1.4, noise( rng, n, 2.2, 3, 30 ) ) * ( rng.random( count ) < 0.4 )[cell]
    c = mix( c, ( 60, 40, 30 ), 0.75 * scale )
    powder = smoothstep( 0.8, 2.0, noise( rng, n, 1.8, 6, 60 ) + 1.5 * pits )
    c = mix( c, ( 170, 100, 46 ), 0.5 * powder )
    wet = smoothstep( 0.5, 2.0, unit( BT.stretched( rng, n, 1.5, 3, 40, ( 20 * p, 1.5 * p ) ) ) )
    c = mix( c, ( 66, 40, 28 ), 0.45 * wet )
    c = darken( c, np.exp( -12.0 * cavities( height, 1.5 * p )[0] ) )
    c = mix( c, ( 150, 92, 52 ), 0.5 * edge_lift * smoothstep( 0.2 * p, 0.6 * p, border ) )
    paint = smoothstep( 2.0, 2.2, noise( rng, n, 2.2, 4, 40 ) + 0.4 * noise( rng, n, 1.2, 40, 160 ) )
    c = mix( c, ( 74, 94, 84 ), 0.85 * paint )
    height = height + 0.008 * paint
    rough = np.clip( 0.88 + 0.04 * fine / 2 - 0.12 * wet - 0.25 * paint, 0, 1 )
    return { "sh_rust": c }, rough, height, 1024 / 96


@texture( "stainless" )
def stainless( rng, n ):
    """ Brushed stainless steel, 4 px an inch: the brushing's fine lines across the picture, the sheet a little wavy,
    with hand smudges, dried water spots and a few light scratches. """
    p = n / 128.0
    brush = BT.stretched( rng, n, 0.5, n / 8, n / 2, ( 0.3, 30 * p ) )
    broad = BT.stretched( rng, n, 1.2, 6, n / 8, ( 0.8, 60 * p ) )
    wave = noise( rng, n, 3.2, 1, 6 )
    hands = _hand_marks( rng, n, 8, p )
    spots = _water_spots( rng, n, 40, ( 0.1 * p, 0.35 * p ), 0.08 * p )
    scratches = crack_lines( rng, n, 10, ( 4 * p, 18 * p ), 0.4, branch=0.0, turn=0.02 )
    c = lum_paint( ( 188, 190, 193 ), 1.0 + 0.04 * brush + 0.03 * broad + 0.02 * wave )
    c = mix( c, ( 150, 152, 154 ), 0.2 * hands )
    c = mix( c, ( 210, 210, 206 ), 0.25 * spots )
    c = mix( c, ( 214, 216, 218 ), 0.35 * scratches )
    height = 0.03 * wave + 0.0008 * brush + 0.0006 * broad - 0.001 * scratches
    rough = np.clip( 0.3 + 0.04 * smoothstep( -2, 2, brush ) + 0.03 * broad / 2 + 0.12 * hands + 0.08 * spots
                     - 0.05 * scratches, 0, 1 )
    return { "sh_stainless": c }, rough, height, 1024 / 128


def _boards( rng, n, width, joints=( 1, 2 ) ):
    """ Boards running up the picture (GRAIN), each width px wide (a range), cut into lengths at butt joints (a range
    a board, 0 for none, so the board runs the tile's length): ( each px's board, u px from the board's left edge, the
    board's width w, its piece, dy px to the nearest joint (n where none), the count of pieces, the boards' edges ). """
    x, y = coords( n )
    widths = []
    while sum( widths ) < n:
        widths.append( rng.uniform( *width ) )
    widths = np.array( widths ) * n / sum( widths )
    edges = np.concatenate( ( [ 0.0 ], np.cumsum( widths ) ) )
    board = np.clip( np.searchsorted( edges, x, side="right" ) - 1, 0, len( widths ) - 1 )
    u = x - edges[board]
    w = widths[board]
    piece = np.zeros( ( n, n ), int )
    dy = np.full( ( n, n ), float( n ) )
    count = 0
    for b in range( len( widths ) ):
        cols = slice( int( round( edges[b] ) ), int( round( edges[b + 1] ) ) )
        k_j = int( rng.integers( joints[0], joints[1] + 1 ) )
        if k_j == 0:
            piece[:, cols] = count
            count += 1
            continue
        # Spread round the tile, so no length is a stub.
        steps = rng.uniform( 0.7, 1.3, k_j )
        js = np.sort( ( rng.uniform( 0, n ) + np.cumsum( steps / steps.sum() * n ) ) % n )
        yy = y[:, cols]
        piece[:, cols] = count + np.searchsorted( js, yy ) % k_j
        dy[:, cols] = np.min( [ np.abs( ( yy - j + n / 2 ) % n - n / 2 ) for j in js ], axis=0 )
        count += k_j
    return board, u, w, piece, dy, count, edges


def _rings( rng, n, piece, count, u, w, y, spacing, centre=( -0.4, 1.4 ), depth=( 12.0, 56.0 ), amp=( 4.0, 24.0 ),
            waves=( 1, 2 ), warp=4.8 ):
    """ Each piece's annual rings where its face cuts them: r = sqrt( ( u - c )^2 + ( depth + wave )^2 ), c the pith's
    place across the board (a share of its width: inside it, flat-sawn cathedral figures; far outside, rift-sawn
    straight lines), depth its depth under the face and the wave a slow bend along the board (px); spacing px between
    rings (a range). ( Latewood 0..1, faded to its average where the rings crowd closer than the px can show; the ring
    phase ). """
    c0 = rng.uniform( *centre, count )[piece] * w
    dep = rng.uniform( *depth, count )[piece]
    am = rng.uniform( *amp, count )[piece]
    m = rng.integers( waves[0], waves[1] + 1, count )[piece]
    phi = rng.uniform( 0, 2 * math.pi, count )[piece]
    sp = rng.uniform( *spacing, count )[piece]
    wp = warp * ( noise( rng, n, 3.0, 1, 6 ) + 0.15 * noise( rng, n, 2.0, 6, 40 ) )
    rr = np.sqrt( ( u - c0 ) ** 2 + ( dep + am * np.sin( 2 * np.pi * m * y / n + phi ) ) ** 2 ) + wp
    phase = rr / sp
    ring = phase % 1.0
    late = smoothstep( 0.62, 0.8, ring ) * ( 1 - smoothstep( 0.9, 1.0, ring ) )
    gy, gx = np.gradient( phase )
    crowd = smoothstep( 0.42, 0.22, np.hypot( gx, gy ) )
    return late * crowd + 0.26 * ( 1 - crowd ), phase


def _knots( rng, n, count, radius ):
    """ count knots (radius px, a range), each a little longer than wide: ( the knots 0..1, the swirl of grain round
    them 0..1 ). """
    knots = np.zeros( ( n, n ) )
    for _ in range( count ):
        r = rng.uniform( *radius )
        stamp( knots, rng.uniform( 0, n ), rng.uniform( 0, n ), r, r * rng.uniform( 1.1, 1.6 ), 1.0, soft=0.6 * r )
    halo = np.clip( T.blur( knots, 2.0 * radius[1] ) * 1.5, 0, 1 ) - knots
    return knots, np.clip( halo, 0, 1 )


def _checks( rng, n, count, length, width ):
    """ count checks (drying cracks) running up the picture, length and width px (ranges), tapering at both ends, 0..1. """
    field = np.zeros( ( n, n ) )
    for _ in range( count ):
        stamp( field, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( *width ), rng.uniform( *length ), 1.0,
               angle=rng.normal( 0, 0.01 ), soft=0.5, profile="cone" )
    return np.clip( field * 1.6, 0, 1 )


def _seams( u, w, dy, half, joint_half=None ):
    """ 0..1 in the gaps between boards (half px each side of an edge) and at their butt joints. """
    side = np.minimum( u, w - u )
    gap = smoothstep( half + 0.5, half - 0.5, side )
    jh = half if joint_half is None else joint_half
    return np.clip( np.maximum( gap, smoothstep( jh + 0.5, jh - 0.5, dy ) ), 0, 1 )


@texture( "pine" )
def pine( rng, n ):
    """ Oregon pine, 8 px an inch, running up the picture (GRAIN): the washbacks' staves, vertical-grained and clear,
    4.5-6 in wide and running the whole height, a few flat-sawn with cathedral figures; the latewood's reddish lines
    strong against the pale earlywood, as Douglas fir's are. Oiled long ago and darkened unevenly, with wash run down the
    staves in streaks, a pin knot or two, and the joints between the staves tight dark lines. """
    p = n / 128.0
    x, y = coords( n )
    board, u, w, piece, dy, count, edges = _boards( rng, n, ( 4.5 * p, 6.0 * p ), joints=( 0, 0 ) )
    flat_sawn = rng.random( count ) < 0.1
    late_r, _ = _rings( rng, n, piece, count, u, w, y, ( 0.28 * p, 0.45 * p ), centre=( -9.0, -3.0 ),
                        depth=( 1.0 * p, 3.0 * p ), amp=( 0.2 * p, 0.8 * p ) )
    late_f, _ = _rings( rng, n, piece, count, u, w, y, ( 0.3 * p, 0.5 * p ), centre=( 0.1, 0.9 ),
                        depth=( 2.0 * p, 6.0 * p ), amp=( 1.0 * p, 3.0 * p ) )
    late = np.where( flat_sawn[piece], late_f, late_r )
    fibre = BT.stretched( rng, n, 0.8, n / 8, n / 2, ( 10 * p, 0.3 ) )
    knots, halo = _knots( rng, n, 3, ( 0.12 * p, 0.25 * p ) )
    late = np.clip( late + 0.5 * halo, 0, 1 )
    tone = rng.uniform( 0.88, 1.1, count )[piece]
    c = lum_paint( ( 188, 130, 76 ), tone * ( 1.0 + 0.03 * fibre + 0.04 * noise( rng, n, 2.4, 1, 20 ) ) )
    c = mix( c, ( 132, 72, 40 ), 0.62 * late )
    c = mix( c, ( 92, 52, 30 ), 0.9 * knots )
    # Oil darkened unevenly; wash spilt from the top running down the staves.
    dark = smoothstep( -0.4, 1.8, noise( rng, n, 2.6, 1, 12 ) )
    c = mix( c, ( 120, 76, 44 ), 0.35 * dark )
    spill = np.zeros( ( n, n ) )
    for _ in range( 14 ):
        stamp( spill, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.3, 1.2 ) * p, 0.5 * p, 1.0, soft=0.4 * p )
    runs = wash_down( spill, 60 * p, 0.6, rng, keep=0.7 )
    runs = runs * smoothstep( -1.0, 1.0, streaks( rng, n, 1.4, 3, 80, 24 * p, 0.4 * p ) )
    c = mix( c, ( 96, 62, 36 ), 0.45 * np.clip( runs, 0, 1 ) )
    seam = _seams( u, w, dy, 0.08 * p )
    c = mix( c, ( 52, 32, 20 ), 0.7 * seam )
    side = np.minimum( u, w - u )
    bevel = 0.04 * smoothstep( 0.0, 0.6 * p, side )
    height = bevel + 0.004 * late + 0.002 * fibre - 0.02 * knots - 0.05 * seam \
        - 0.006 * ( ( u - w / 2 ) / ( w / 2 ) ) ** 2
    rough = np.clip( 0.52 + 0.06 * late + 0.06 * dark + 0.1 * runs + 0.3 * seam, 0, 1 )
    return { "sh_pine": c }, rough, height, 1024 / 128


@texture( "cask" )
def cask( rng, n ):
    """ Cask staves, 8 px an inch, running up the picture (GRAIN): white oak, riven and quarter-sawn, 3-4.2 in wide,
    each running the cask's length. The ring-porous oak's fine dark lines along the stave and its ray flecks across
    them, each stave a little crowned and shaved by the cooper's knife in shallow scallops, weathered its own shade.
    Warehouse dirt and the black of the angels' share fungus in specks; spirit seeping darker from the joints. sh_cask_oak
    is a weathered ex-bourbon cask, sh_cask_dark a wet one, or a sherry butt. """
    p = n / 64.0
    x, y = coords( n )
    board, u, w, piece, dy, count, edges = _boards( rng, n, ( 3.0 * p, 4.2 * p ), joints=( 0, 0 ) )
    late, _ = _rings( rng, n, piece, count, u, w, y, ( 0.2 * p, 0.34 * p ), centre=( -14.0, -5.0 ),
                      depth=( 0.5 * p, 2.0 * p ), amp=( 0.1 * p, 0.4 * p ) )
    fibre = BT.stretched( rng, n, 0.7, n / 8, n / 2, ( 8 * p, 0.3 ) )
    pores = smoothstep( 1.2, 2.4, BT.stretched( rng, n, 0.6, n / 6, n / 2, ( 3 * p, 0.25 ) ) )
    # Ray flecks: lens-shaped ribbons crossing the grain at a slant.
    fleck = np.zeros( ( n, n ) )
    for _ in range( int( 3.2 * ( n / p ) ** 2 / 16 ) ):
        stamp( fleck, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.04, 0.09 ) * p,
               rng.uniform( 0.2, 0.7 ) * p, rng.uniform( 0.4, 1.0 ), angle=rng.normal( 0, 0.35 ), soft=0.4,
               profile="dome" )
    # The cooper's knife: shallow scallops across each stave.
    scallop = np.sin( 2 * np.pi * ( y / ( rng.uniform( 1.4, 2.2, count )[piece] * p ) + rng.uniform( 0, 1, count )[piece] )
                      + 0.8 * noise( rng, n, 2.0, 2, 16 ) )
    tone = rng.uniform( 0.84, 1.12, count )[piece]
    grey = rng.uniform( 0.0, 0.6, count )[piece]
    weather = smoothstep( -0.6, 1.6, noise( rng, n, 2.6, 1, 10 ) )
    dirt = smoothstep( 0.2, 2.2, noise( rng, n, 2.4, 1, 14 ) + 0.4 * noise( rng, n, 1.6, 14, 60 ) )
    specks = smoothstep( 2.5, 3.2, grain_field( rng, n, 0.7, 4.0 ) + 1.4 * smoothstep( 0.8, 2.0, noise( rng, n, 2.4, 2, 16 ) ) )
    side = np.minimum( u, w - u )
    seam = smoothstep( 0.9, 0.1, side )
    seep = wash_down( smoothstep( 0.9 * p, 0.0, side ) * smoothstep( 1.0, 2.2, noise( rng, n, 2.0, 2, 30 ) ), 12 * p, 0.7,
                      rng, keep=0.8 )

    def stave( base, late_c, grey_c, dirt_c, wet_c ):
        c = lum_paint( base, tone * ( 1.0 + 0.04 * fibre + 0.03 * scallop ) )
        c = mix( c, late_c, 0.45 * late + 0.35 * pores )
        c = mix( c, grey_c, ( 0.25 + 0.45 * weather ) * grey )
        c = mix( c, tuple( v * 1.12 for v in base ), 0.35 * fleck )
        c = mix( c, dirt_c, 0.35 * dirt )
        c = mix( c, wet_c, 0.6 * np.clip( seep, 0, 1 ) )
        c = mix( c, ( 30, 26, 22 ), 0.6 * specks )
        return mix( c, ( 40, 28, 20 ), 0.75 * seam )

    oak = stave( ( 150, 110, 72 ), ( 98, 68, 44 ), ( 138, 128, 112 ), ( 86, 70, 54 ), ( 92, 62, 40 ) )
    dark = stave( ( 104, 70, 46 ), ( 62, 40, 28 ), ( 96, 80, 66 ), ( 52, 40, 32 ), ( 58, 34, 24 ) )
    crown = -0.05 * ( ( u - w / 2 ) / ( w / 2 ) ) ** 2
    height = crown + 0.004 * scallop + 0.003 * fibre - 0.004 * pores + 0.003 * fleck - 0.06 * seam - 0.004 * late
    rough = np.clip( 0.72 + 0.06 * weather * grey + 0.04 * dirt - 0.18 * np.clip( seep, 0, 1 ) + 0.2 * seam, 0, 1 )
    return { "sh_cask_oak": oak, "sh_cask_dark": dark }, rough, height, 1024 / 64


@texture( "hoop" )
def hoop( rng, n ):
    """ Cask hoops, 16 px an inch: galvanised mild steel gone dark grey, its zinc worn through to rust in patches and
    pits (rust brown, flaking), white zinc salts in spots, black warehouse grime, and bright scrapes where the casks are
    rolled and the hoops driven. """
    p = n / 32.0
    zinc = noise( rng, n, 2.4, 2, 40 )
    spangle_cells = cells( rng, n, jittered( rng, n, 0.5 * p, 0.45 ), wander=0.1 * p )[0]
    spangle = rng.normal( 0, 0.04, spangle_cells.max() + 1 )[spangle_cells]
    grime = smoothstep( -0.6, 1.6, noise( rng, n, 2.4, 1, 16 ) )
    rust_f = noise( rng, n, 2.3, 2, 40 ) + 0.35 * noise( rng, n, 1.4, 40, 200 )
    rust_m = smoothstep( 0.9, 1.5, rust_f )
    pits = dots( rng, n, 300, ( 0.04 * p, 0.12 * p ), profile="dome", soft=0.5 )
    rust_m = np.clip( rust_m + 0.8 * pits, 0, 1 )
    salts = smoothstep( 2.0, 2.6, noise( rng, n, 1.8, 6, 80 ) + 0.5 * grain_field( rng, n, 0.8, 3.0 ) ) * ( 1 - rust_m )
    scrape = crack_lines( rng, n, 16, ( 1.0 * p, 5.0 * p ), 0.6, branch=0.0, turn=0.02 ) * ( 1 - rust_m )
    c = lum_paint( ( 92, 94, 96 ), 1.0 + 0.08 * zinc + spangle )
    c = mix( c, ( 34, 33, 32 ), 0.6 * grime )
    rust_c = mix( ( 112, 60, 30 ), ( 60, 38, 26 ), smoothstep( -1, 1, noise( rng, n, 1.6, 10, 100 ) ) )
    c = mix( c, rust_c, rust_m )
    c = mix( c, ( 150, 150, 142 ), 0.6 * salts )
    c = mix( c, ( 150, 152, 154 ), 0.6 * scrape )
    height = 0.004 * zinc + 0.012 * rust_m * smoothstep( -1, 1, rust_f ) - 0.01 * pits + 0.004 * salts - 0.002 * scrape
    rough = np.clip( 0.5 + 0.12 * grime + 0.38 * rust_m + 0.3 * salts - 0.2 * scrape, 0, 1 )
    return { "sh_hoop": c }, rough, height, 1024 / 32


@texture( "timber_tar" )
def timber_tar( rng, n ):
    """ Tarred boarding, 4 px an inch, running up the picture (GRAIN): shiplap boards 6-9 in wide, a shadowed rebate
    where each laps the next, coated black with tar. Fresh coats glossy, old ones gone matt and brown-grey in the
    weather, the grain standing up through them, runs and drips where it was laid on thick. """
    p = n / 128.0
    x, y = coords( n )
    board, u, w, piece, dy, count, edges = _boards( rng, n, ( 6.0 * p, 9.0 * p ), joints=( 0, 1 ) )
    late, _ = _rings( rng, n, piece, count, u, w, y, ( 0.3 * p, 0.6 * p ), centre=( -0.2, 1.2 ), depth=( 2 * p, 7 * p ),
                      amp=( 1 * p, 4 * p ), warp=0.4 * p )
    fibre = BT.stretched( rng, n, 0.9, n / 8, n / 2, ( 6 * p, 0.3 ) )
    coat = rng.uniform( 0, 1, count )[piece]
    worn = smoothstep( -0.8, 1.4, 0.5 * noise( rng, n, 2.6, 1, 10 ) + 0.7 * streaks( rng, n, 1.6, 2, 60, 20 * p, 0.6 * p )
                       + 1.6 * ( coat - 0.5 ) )
    blooms = smoothstep( 0.8, 2.2, noise( rng, n, 2.2, 2, 30 ) ) * worn
    drips = np.zeros( ( n, n ) )
    for _ in range( 60 ):
        stamp( drips, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.15, 0.4 ) * p, 0.3 * p, 1.0, soft=0.4 )
    runs = np.clip( wash_down( drips, 14 * p, 0.6, rng, keep=0.6 ), 0, 1 ) * ( 1 - 0.5 * worn )
    c = lum_paint( ( 28, 26, 24 ), 1.0 + 0.1 * fibre + 0.06 * noise( rng, n, 2.0, 2, 30 ) )
    weathered = mix( ( 66, 62, 56 ), ( 82, 70, 56 ), smoothstep( -1, 1, noise( rng, n, 2.4, 1, 20 ) ) )
    weathered = lum_paint( weathered, 1.0 + 0.25 * ( late - 0.3 ) + 0.06 * fibre )
    c = mix( c, weathered, 0.75 * worn )
    c = mix( c, ( 92, 84, 72 ), 0.35 * blooms )
    c = mix( c, ( 20, 19, 18 ), 0.7 * runs )
    # The rebate: a shadowed step at each board's left edge, a fine line at its right.
    lap = smoothstep( 0.9 * p, 0.2 * p, u )
    c = darken( c, 1.0 - 0.6 * lap )
    c = mix( c, ( 12, 11, 10 ), 0.8 * smoothstep( 0.8, 0.0, w - u ) )
    joint = smoothstep( 0.8, 0.0, dy )
    c = mix( c, ( 12, 11, 10 ), 0.8 * joint )
    height = 0.12 * smoothstep( 0.0, 0.6 * p, u ) + 0.012 * late * worn + 0.004 * fibre + 0.01 * runs \
        - 0.08 * joint
    rough = np.clip( 0.42 + 0.42 * worn + 0.08 * blooms - 0.15 * runs + 0.2 * lap, 0, 1 )
    return { "sh_timber_tar": c }, rough, height, 1024 / 128


@texture( "planks_grey" )
def planks_grey( rng, n ):
    """ Weathered planks, 8 px an inch, running up the picture (GRAIN): sawn softwood 4-6 in wide, in lengths of a few
    feet, gone silver-grey in the salt air. The soft earlywood worn back so the latewood stands up in ridges, drying
    checks along the grain, a few knots, rusted nails at the ends of each length bleeding dark down the grain, a little
    brown left in the sheltered boards, and lichen beginning. """
    p = n / 128.0
    x, y = coords( n )
    board, u, w, piece, dy, count, edges = _boards( rng, n, ( 4.0 * p, 6.0 * p ), joints=( 2, 3 ) )
    late, _ = _rings( rng, n, piece, count, u, w, y, ( 0.3 * p, 0.55 * p ), centre=( -2.0, 3.0 ),
                      depth=( 1.5 * p, 7 * p ), amp=( 0.5 * p, 2.5 * p ), warp=0.25 * p )
    fibre = BT.stretched( rng, n, 0.8, n / 8, n / 2, ( 10 * p, 0.3 ) )
    late = late * ( 0.75 + 0.25 * smoothstep( -1.5, 1.5, streaks( rng, n, 1.0, 8, 200, 12 * p, 0.4 ) ) )
    knots, halo = _knots( rng, n, 8, ( 0.3 * p, 0.6 * p ) )
    late = np.clip( late + 0.6 * halo, 0, 1 )
    checks = _checks( rng, n, 40, ( 2 * p, 9 * p ), ( 0.05 * p, 0.12 * p ) )
    brown = rng.uniform( 0, 1, count )[piece] ** 2
    tone = rng.uniform( 0.86, 1.12, count )[piece]
    c = lum_paint( ( 160, 156, 146 ), tone * ( 1.0 + 0.08 * fibre + 0.04 * noise( rng, n, 2.4, 1, 20 ) ) )
    c = mix( c, ( 140, 118, 92 ), 0.6 * brown * smoothstep( -1.0, 1.0, noise( rng, n, 2.6, 1, 10 ) ) )
    c = mix( c, ( 108, 102, 92 ), 0.3 * late )
    c = mix( c, ( 62, 54, 46 ), 0.9 * knots )
    c = mix( c, ( 42, 38, 34 ), 0.85 * checks )
    # Nails near each length's ends, two to a board, bleeding rust down the grain.
    nails = np.zeros( ( n, n ) )
    for b in range( len( edges ) - 1 ):
        cols = ( edges[b], edges[b + 1] )
        bx = 0.5 * ( cols[0] + cols[1] )
        cut_rows = np.where( np.abs( np.diff( piece[:, int( bx ) % n] ) ) > 0 )[0]
        for j in cut_rows:
            for side in ( -1, 1 ):
                for off in ( -0.28, 0.28 ):
                    stamp( nails, bx + off * ( cols[1] - cols[0] ) + rng.normal( 0, 0.1 * p ),
                           j + side * ( 0.9 * p + rng.normal( 0, 0.1 * p ) ), 0.12 * p, 0.12 * p, 1.0, soft=0.5 )
    bleed = np.clip( wash_down( nails, 10 * p, 0.5, rng, keep=0.9 ), 0, 1 ) * ( 1 - nails )
    c = mix( c, ( 74, 60, 50 ), 0.5 * bleed )
    c = mix( c, ( 40, 34, 30 ), nails )
    lichen = smoothstep( 1.9, 2.5, noise( rng, n, 1.8, 6, 80 ) + 0.6 * grain_field( rng, n, 0.8, 3.0 ) )
    c = mix( c, ( 150, 158, 128 ), 0.6 * lichen )
    seam = _seams( u, w, dy, 0.25 * p, 0.15 * p )
    c = mix( c, ( 30, 28, 26 ), 0.9 * seam )
    side = np.minimum( u, w - u )
    height = 0.02 * smoothstep( 0.0, 0.5 * p, side ) + 0.02 * late + 0.005 * fibre - 0.03 * checks - 0.02 * knots \
        - 0.2 * seam + 0.004 * lichen + 0.003 * nails + 0.01 * ( ( u - w / 2 ) / ( w / 2 ) ) ** 2
    rough = np.clip( 0.84 + 0.04 * late - 0.08 * nails + 0.1 * seam, 0, 1 )
    return { "sh_planks_grey": c }, rough, height, 1024 / 128


@texture( "deck" )
def deck( rng, n ):
    """ A boat's deck, 8 px an inch, running up the picture (GRAIN): larch planks 3-4 in wide in long staggered
    lengths, the seams between them paid with black pitch, wooden plugs over the fastenings in pairs at every frame,
    scrubbed and worn grey-brown along the working side, darker where the oil and the fish have been. """
    p = n / 128.0
    x, y = coords( n )
    board, u, w, piece, dy, count, edges = _boards( rng, n, ( 3.0 * p, 4.0 * p ), joints=( 0, 1 ) )
    late, _ = _rings( rng, n, piece, count, u, w, y, ( 0.25 * p, 0.45 * p ), centre=( -3.0, 4.0 ),
                      depth=( 1.0 * p, 5.0 * p ), amp=( 0.5 * p, 2.0 * p ), warp=0.3 * p )
    fibre = BT.stretched( rng, n, 0.8, n / 8, n / 2, ( 10 * p, 0.3 ) )
    tone = rng.uniform( 0.86, 1.12, count )[piece]
    worn = smoothstep( -0.8, 1.6, noise( rng, n, 2.6, 1, 8 ) )
    c = lum_paint( ( 150, 122, 88 ), tone * ( 1.0 + 0.04 * fibre + 0.04 * noise( rng, n, 2.4, 1, 20 ) ) )
    c = mix( c, ( 104, 78, 52 ), 0.38 * late )
    c = mix( c, ( 152, 144, 130 ), 0.45 * worn )
    # Plugs over the fastenings: pairs on every plank at each frame, 18 in apart across the picture's rows.
    plugs = np.zeros( ( n, n ) )
    rim = np.zeros( ( n, n ) )
    frame_rows = ( np.arange( int( round( n / ( 18 * p ) ) ) ) + 0.5 ) * n / int( round( n / ( 18 * p ) ) )
    for b in range( len( edges ) - 1 ):
        bw = edges[b + 1] - edges[b]
        for fy in frame_rows:
            for off in ( 0.3, 0.7 ):
                px_ = edges[b] + off * bw + rng.normal( 0, 0.05 * p )
                py_ = fy + rng.normal( 0, 0.1 * p )
                stamp( plugs, px_, py_, 0.22 * p, 0.22 * p, 1.0, soft=0.5 )
                stamp( rim, px_, py_, 0.3 * p, 0.3 * p, 1.0, soft=0.5 )
    rim = np.clip( rim - plugs, 0, 1 )
    plug_tone = lum_paint( ( 160, 132, 96 ), 1.0 + 0.05 * fibre )
    c = mix( c, plug_tone, 0.7 * plugs )
    c = mix( c, ( 70, 54, 38 ), 0.6 * rim )
    stain = smoothstep( 1.4, 2.8, noise( rng, n, 2.8, 1, 16 ) + 0.25 * noise( rng, n, 1.5, 16, 60 ) )
    c = mix( c, ( 66, 54, 42 ), 0.4 * stain )
    side = np.minimum( u, w - u )
    paid = smoothstep( 1.4, 0.6, side )
    c = mix( c, ( 18, 16, 15 ), 0.92 * paid )
    joint = smoothstep( 1.2, 0.4, dy )
    c = mix( c, ( 18, 16, 15 ), 0.92 * joint )
    height = 0.006 * late * worn + 0.003 * fibre - 0.04 * paid - 0.04 * joint + 0.004 * plugs - 0.006 * rim \
        + 0.012 * smoothstep( 1.0, 3.0, side )
    rough = np.clip( 0.7 + 0.12 * worn - 0.15 * stain - 0.25 * paid - 0.2 * joint, 0, 1 )
    return { "sh_deck": c }, rough, height, 1024 / 128


def _chips( rng, n, cover, deep, fmin=10, fmax=120, cluster=0.8 ):
    """ Paint knocked off in flakes: ( the paint gone to the coat under it, 0..1; gone to the bare surface; the ring
    round each chip where the paint's edge stands ). cover and deep are the shares of the tile. Flakes of every size,
    clustered where things knock it. """
    flake = noise( rng, n, 2.0, fmin, fmax ) + 0.2 * noise( rng, n, 1.0, fmax, n / 3 ) \
        + cluster * noise( rng, n, 2.6, 1, 8 )
    q_under, q_bare = np.quantile( flake, 1.0 - cover ), np.quantile( flake, 1.0 - deep )
    under = smoothstep( q_under - 0.015, q_under + 0.015, flake )
    bare = smoothstep( q_bare - 0.02, q_bare + 0.02, flake )
    edge = smoothstep( q_under - 0.12, q_under - 0.015, flake ) * ( 1 - under )
    return under, bare, edge


@texture( "paint" )
def paint( rng, n ):
    """ Gloss paint on woodwork and steel, 8 px an inch, a few years old: the brush marks laid off up the picture, a
    faint orange peel, chalkier where the sun and salt get at it, grime settled in patches; small chips down to the
    undercoat and, in their middles, to the bare wood, the odd scratch and a sag or two. Seven colours share it. """
    PAINT_COLOURS = {
        # paint: ( colour, faded, undercoat )
        "sh_paint_door": ( ( 22, 72, 68 ), ( 70, 104, 98 ), ( 176, 172, 160 ) ),
        "sh_paint_white": ( ( 236, 236, 230 ), ( 222, 220, 210 ), ( 150, 148, 140 ) ),
        "sh_paint_black": ( ( 34, 34, 34 ), ( 70, 70, 68 ), ( 140, 138, 132 ) ),
        "sh_paint_red": ( ( 162, 28, 22 ), ( 176, 82, 70 ), ( 170, 166, 156 ) ),
        "sh_paint_yellow": ( ( 228, 182, 32 ), ( 226, 200, 112 ), ( 160, 156, 146 ) ),
        "sh_paint_orange": ( ( 232, 104, 22 ), ( 222, 142, 88 ), ( 160, 156, 146 ) ),
        "sh_paint_blue": ( ( 32, 62, 120 ), ( 86, 106, 140 ), ( 172, 168, 158 ) ),
    }
    p = n / 64.0
    brush = streaks( rng, n, 1.0, 8, n / 2, 6 * p, 0.3 )
    peel = noise( rng, n, 1.0, n / 12, n / 3 )
    fade = smoothstep( -0.4, 2.0, noise( rng, n, 2.6, 1, 10 ) + 0.3 * noise( rng, n, 2.0, 10, 40 ) )
    grime = smoothstep( 0.6, 2.4, noise( rng, n, 2.4, 1, 12 ) + 0.4 * streaks( rng, n, 1.4, 3, 60, 18 * p, 0.6 * p ) )
    under, bare, edge = _chips( rng, n, 0.018, 0.007, fmin=12, fmax=160 )
    scratches = crack_lines( rng, n, 10, ( 1.5 * p, 6 * p ), 0.5, branch=0.0, turn=0.04 )
    sags = np.zeros( ( n, n ) )
    for _ in range( 3 ):
        stamp( sags, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.2, 0.4 ) * p, rng.uniform( 0.6, 1.4 ) * p,
               1.0, profile="dome" )
    wood = mix( ( 132, 104, 72 ), ( 96, 72, 50 ), smoothstep( -1, 1, streaks( rng, n, 1.0, 8, 200, 8 * p, 0.3 ) ) )
    colours = {}
    for name, ( base, faded, undercoat ) in PAINT_COLOURS.items():
        c = lum_paint( base, 1.0 + 0.025 * brush + 0.01 * peel + 0.02 * noise( rng, n, 2.0, 2, 30 ) )
        c = mix( c, faded, 0.35 * fade )
        c = mix( c, darken( base, 0.55 ) if name != "sh_paint_black" else ( 52, 50, 46 ), 0.22 * grime )
        c = mix( c, undercoat, under )
        c = mix( c, wood, bare )
        c = mix( c, mix( base, undercoat, 0.5 ), 0.4 * scratches * ( 1 - under ) )
        colours[name] = c
    height = 0.0015 * brush + 0.0008 * peel + 0.004 * sags - 0.006 * under - 0.004 * bare + 0.002 * edge \
        - 0.002 * scratches
    rough = np.clip( 0.34 + 0.02 * brush / 2 + 0.22 * fade + 0.12 * grime + 0.3 * under + 0.4 * bare
                     + 0.15 * scratches, 0, 1 )
    return colours, rough, height, 1024 / 64


@texture( "hull" )
def hull( rng, n ):
    """ A working boat's painted hull, 4 px an inch: the strakes' seams faint across the picture, the paint chalky
    and faded, scraped along by fenders and quay walls back through the coats (an older colour under this one, then the
    red primer, then bare wood or rust), rust weeping down from the fastenings in streaks, salt dried in patches, dents
    and the odd patch painted over in a fresher coat. Four colours share it. """
    HULL_COLOURS = {
        # paint: ( colour, faded, the older coat under it, the primer )
        "sh_hull_blue": ( ( 28, 56, 112 ), ( 78, 100, 134 ), ( 214, 212, 204 ), ( 140, 70, 48 ) ),
        "sh_hull_red": ( ( 134, 32, 24 ), ( 150, 84, 72 ), ( 34, 62, 104 ), ( 140, 70, 48 ) ),
        "sh_hull_white": ( ( 226, 226, 218 ), ( 208, 206, 196 ), ( 40, 70, 112 ), ( 140, 70, 48 ) ),
        "sh_hull_black": ( ( 40, 40, 40 ), ( 76, 76, 74 ), ( 150, 40, 30 ), ( 140, 70, 48 ) ),
    }
    p = n / 128.0
    x, y = coords( n )
    # The strakes, 7-9 in deep, each its own slight bulge.
    rows = []
    while sum( rows ) < n:
        rows.append( rng.uniform( 7 * p, 9 * p ) )
    rows = np.array( rows ) * n / sum( rows )
    edges = np.concatenate( ( [ 0.0 ], np.cumsum( rows ) ) )
    strake = np.clip( np.searchsorted( edges, y, side="right" ) - 1, 0, len( rows ) - 1 )
    v = y - edges[strake]
    h = rows[strake]
    seam_d = np.minimum( v, h - v )
    seam = smoothstep( 1.0, 0.0, seam_d ) * ( 0.3 + 0.7 * smoothstep( -0.5, 1.5, noise( rng, n, 2.0, 2, 20 ) ) )
    swell = 0.06 * ( 1 - ( ( v - h / 2 ) / ( h / 2 ) ) ** 2 )
    fade = smoothstep( -0.6, 1.8, noise( rng, n, 2.6, 1, 10 ) + 0.4 * streaks( rng, n, 1.4, 2, 40, 16 * p, 1.0 * p ) )
    # Scrapes along the hull: wear stretched across the picture.
    # Each coat wears through on its own ragged line, so the coats under it show in streaks, not rings.
    scrape_f = unit( BT.stretched( rng, n, 1.6, 4, 160, ( 0.8 * p, 14 * p ) ) ) + 0.9 * noise( rng, n, 2.6, 1, 6 )
    rag = [ unit( BT.stretched( rng, n, 1.2, 20, n / 2, ( 0.4, 3 * p ) ) ) for _ in range( 3 ) ]
    layers = []
    for share, r in zip( ( 0.955, 0.978, 0.992 ), rag ):
        f = scrape_f + 0.45 * r
        q = np.quantile( f, share )
        layers.append( smoothstep( q - 0.04, q + 0.04, f ) )
    old, primer, bare = layers
    primer = primer * old
    bare = bare * primer
    under, deep, edge = _chips( rng, n, 0.02, 0.008, fmin=8, fmax=100 )
    old = np.maximum( old, under )
    primer = np.maximum( primer, 0.6 * deep )
    bare = np.maximum( bare, deep * 0.8 )
    # Fastenings along the seams, rust weeping down from some.
    bolts = np.zeros( ( n, n ) )
    for k in range( len( rows ) ):
        for bx in np.arange( rng.uniform( 0, 16 * p ), n, rng.uniform( 14, 20 ) * p ):
            if rng.random() < 0.35:
                stamp( bolts, bx + rng.normal( 0, 0.3 * p ), edges[k] + rng.uniform( 1.2, 2.2 ) * p,
                       0.35 * p, 0.35 * p, 1.0, soft=0.4 )
    weep_src = np.maximum( bolts, bare ) * smoothstep( 0.0, 1.0, noise( rng, n, 1.5, 8, 60 ) + 0.5 )
    weep = np.clip( wash_down( weep_src, 40 * p, 0.6, rng, keep=0.6 ), 0, 1 ) * ( 1 - bare )
    salt = smoothstep( 1.2, 2.4, noise( rng, n, 2.0, 2, 40 ) + 0.5 * grain_field( rng, n, 0.8, 3.0 ) )
    patch = smoothstep( 1.6, 1.8, noise( rng, n, 3.0, 1, 6 ) )
    dents = T.blur( dots( rng, n, 14, ( 1.5 * p, 4.0 * p ), profile="dome", soft=1.0 ), 1.0 * p )
    rust_c = mix( ( 120, 64, 34 ), ( 70, 44, 30 ), smoothstep( -1, 1, noise( rng, n, 1.6, 10, 80 ) ) )
    colours = {}
    for name, ( base, faded, older, red ) in HULL_COLOURS.items():
        c = lum_paint( base, 1.0 + 0.03 * noise( rng, n, 2.2, 1, 30 ) + 0.015 * noise( rng, n, 1.0, 40, n / 3 ) )
        c = mix( c, faded, 0.45 * fade * ( 1 - patch ) )
        c = mix( c, darken( base, 0.6 ), 0.35 * seam )
        c = mix( c, older, old )
        c = mix( c, red, primer )
        c = mix( c, rust_c, bare )
        c = mix( c, rust_c, 0.55 * weep )
        c = mix( c, rust_c, 0.8 * bolts )
        c = mix( c, ( 214, 212, 200 ), 0.35 * salt * ( 1 - bare ) )
        colours[name] = c
    height = swell - 0.06 * seam - 0.01 * old - 0.014 * primer - 0.02 * bare + 0.004 * edge - 0.06 * dents \
        + 0.01 * bolts + 0.004 * salt
    rough = np.clip( 0.42 + 0.3 * fade * ( 1 - patch ) + 0.15 * old + 0.25 * primer + 0.4 * bare + 0.2 * weep
                     + 0.15 * salt, 0, 1 )
    return colours, rough, height, 1024 / 128


def _courses( rng, n, low, high, wander ):
    """ Rows across the tile low..high px high, their borders wandering up and down by wander px: ( the row of each px,
    its height, the px's distance down from the row's top, the row borders ). """
    x, y = coords( n )
    rows = []
    while sum( rows ) < n:
        rows.append( rng.uniform( low, high ) )
    rows = np.array( rows ) * n / sum( rows )
    edges = np.concatenate( ( [ 0.0 ], np.cumsum( rows ) ) )
    yw = ( y + wander * noise( rng, n, 2.2, 1, 8 ) ) % n
    row = np.clip( np.searchsorted( edges, yw, side="right" ) - 1, 0, len( rows ) - 1 )
    return row, rows[row], yw - edges[row], rows


def _bricks_in_rows( rng, n, row, count, lengths, wander ):
    """ Each row cut into blocks lengths px long (a list of ( low, high, weight ) choices), from its own start: ( the
    block of each px, numbered over the tile, the px's distance along it, its length, how many blocks ). """
    x, _ = coords( n )
    xw = x + wander * noise( rng, n, 2.0, 2, 12 )
    block = np.zeros( ( n, n ), int )
    along = np.zeros( ( n, n ) )
    size = np.zeros( ( n, n ) )
    first = 0
    weights = np.array( [ w for _, _, w in lengths ], float )
    for r in range( count ):
        sizes = []
        while sum( sizes ) < n:
            lo, hi, _ = lengths[rng.choice( len( lengths ), p=weights / weights.sum() )]
            sizes.append( rng.uniform( lo, hi ) )
        sizes = np.array( sizes ) * n / sum( sizes )
        edges = np.concatenate( ( [ 0.0 ], np.cumsum( sizes ) ) )
        here = row == r
        xs = ( xw[here] + rng.uniform( 0, n ) ) % n
        k = np.clip( np.searchsorted( edges, xs, side="right" ) - 1, 0, len( sizes ) - 1 )
        block[here] = first + k
        along[here] = xs - edges[k]
        size[here] = sizes[k]
        first += len( sizes )
    return block, along, size, first


@texture( "peat" )
def peat( rng, n ):
    """ A stack of dried peats in the peat shed, 10 2/3 px an inch: bricks cut with the peat iron, about 9 x 3 1/2 x 2 1/2
    in once dry, laid loose in rough courses with dark gaps between, some showing their sides and some their ends,
    each set a little askew. Each is fibrous dark brown with the bank's layers in it, its outside dried to a dusty
    grey-brown skin, cracked as it shrank, with pale root fibres and crumbs. """
    p = n / 48.0
    row, row_h, down, rows = _courses( rng, n, 2.6 * p, 3.8 * p, 0.45 * p )
    block, along, length, count = _bricks_in_rows( rng, n, row, len( rows ),
                                                   [ ( 7.5 * p, 10.0 * p, 0.55 ), ( 3.0 * p, 4.2 * p, 0.45 ) ], 0.3 * p )
    # Each brick a little smaller than its place, off centre in it and turned a few degrees.
    gap_u = rng.uniform( 0.12, 0.45, count )[block] * p
    gap_v = rng.uniform( 0.1, 0.35, count )[block] * p
    shift_u = rng.normal( 0, 0.12, count )[block] * p
    shift_v = rng.normal( 0, 0.08, count )[block] * p
    turn = rng.normal( 0, 0.035, count )[block]
    u0 = along - length / 2 - shift_u
    v0 = down - row_h / 2 - shift_v
    u1 = u0 * np.cos( turn ) + v0 * np.sin( turn )
    v1 = -u0 * np.sin( turn ) + v0 * np.cos( turn )
    U = u1 / np.maximum( length / 2 - gap_u, 1.0 )
    V = v1 / np.maximum( row_h / 2 - gap_v, 1.0 )
    crumble = 0.05 * noise( rng, n, 1.6, 12, 80 ) + 0.04 * noise( rng, n, 2.2, 4, 20 )
    D = ( np.abs( U ) ** 5 + np.abs( V ) ** 5 ) ** 0.2 + crumble
    proud = rng.normal( 0, 0.3, count )[block]
    tip = rng.normal( 0, 0.2, count )[block]
    body = np.clip( 1.0 - np.clip( D, 0, 1 ) ** 6, 0.0, 1.0 ) ** 0.4
    inside = smoothstep( 1.03, 0.95, D )
    # The peat itself: the bank's layers along the brick (or across it, for the ones on their end), fibres, cracks.
    on_end = ( length < 5.0 * p ) & ( rng.random( count ) < 0.6 )[block]
    layers = np.where( on_end, BT.stretched( rng, n, 1.2, 10, n / 2, ( 4.0, 0.5 ) ),
                       BT.stretched( rng, n, 1.2, 10, n / 2, ( 0.5, 4.0 ) ) )
    fibre = np.where( on_end, BT.stretched( rng, n, 0.8, 60, None, ( 0.7, 0.2 ) ),
                      BT.stretched( rng, n, 0.8, 60, None, ( 0.2, 0.7 ) ) )
    crumbly = noise( rng, n, 1.2, 24, None )
    pits = smoothstep( 1.0, 3.5, grain_field( rng, n, 0.7, 3.0 ) )
    cracks = crack_lines( rng, n, 90, ( 0.6 * p, 2.6 * p ), 0.9, branch=0.5, turn=0.25 ) * inside
    roots = crack_lines( rng, n, 110, ( 0.3 * p, 1.2 * p ), 0.5, branch=0.1, turn=0.12, pull=0.3 ) * inside
    dryness = rng.uniform( 0.2, 1.0, count )[block]
    skin = smoothstep( -0.6, 1.0, noise( rng, n, 2.0, 4, 40 ) + 1.6 * dryness - 0.8 ) * inside
    tone = rng.uniform( 0.75, 1.2, count )[block]
    red = rng.uniform( 0.0, 1.0, count )[block]
    lum = tone * ( 1.0 + 0.1 * layers + 0.04 * fibre + 0.1 * crumbly ) * ( 1.0 - 0.45 * pits ) * ( 0.5 + 0.5 * body )
    dark = mix( ( 44, 29, 19 ), ( 70, 40, 24 ), 0.6 * red )
    c = lum_paint( dark, lum )
    c = mix( c, lum_paint( ( 96, 76, 58 ), ( 0.85 + 0.06 * fibre + 0.08 * layers + 0.1 * crumbly ) * ( 1.0 - 0.4 * pits )
                               * ( 0.6 + 0.4 * body ) ), 0.7 * skin )
    c = mix( c, ( 20, 14, 10 ), 0.85 * cracks )
    c = mix( c, ( 126, 100, 70 ), 0.5 * roots * ( 1 - cracks ) )
    # The gaps: deep and dark, with crumbs and dust lying in them.
    crumbs = dots( rng, n, 1100, ( 0.15 * p, 0.45 * p ), profile="dome", soft=0.6 )
    gap = 1 - inside
    c = mix( c, mix( flat( n, ( 12, 9, 7 ) ), ( 70, 52, 38 ), 0.6 * crumbs ), gap )
    height = inside * ( 0.9 * body + proud + tip * U + 0.04 * layers + 0.01 * fibre + 0.02 * crumbly - 0.04 * pits
                        - 0.12 * cracks + 0.015 * roots ) - 1.1 * gap + gap * 0.3 * crumbs
    rough = np.clip( 0.86 + 0.06 * skin - 0.05 * ( 1 - dryness ) * inside + 0.02 * fibre, 0, 1 )
    return { "sh_peat": c }, rough, height, 1024 / 48


def _spindles( rng, n, points, length, width, angle, depth, thick, k=10, rows=128 ):
    """ Long grains lying every way over each other (malt): for each px the topmost grain whose outline holds it.
    points ( m, 2 ) px; length and width ( m, ) px, full; angle ( m, ); depth ( m, ) the height (in) each lies at;
    thick the grains' thickness (in). Returns ( the grain at each px, -1 in a gap; the surface's height there; u along
    the grain -1..1; v across it -1..1, as a share of its width there ). """
    points = np.asarray( points, float ) % n
    tree = cKDTree( points, boxsize=n )
    x, y = coords( n )
    grain = np.full( ( n, n ), -1, int )
    top = np.full( ( n, n ), -1.0 )
    uu = np.zeros( ( n, n ) )
    vv = np.zeros( ( n, n ) )
    ca, sa = np.cos( angle ), np.sin( angle )
    for r0 in range( 0, n, rows ):
        q = np.stack( [ x[r0:r0 + rows].ravel(), y[r0:r0 + rows].ravel() ], -1 )
        _, idx = tree.query( q, k=k, workers=-1 )
        off = ( q[:, None, :] - points[idx] + n / 2 ) % n - n / 2
        u = ( off[..., 0] * ca[idx] + off[..., 1] * sa[idx] ) / ( 0.5 * length[idx] )
        v = ( -off[..., 0] * sa[idx] + off[..., 1] * ca[idx] ) / ( 0.5 * width[idx] )
        w = np.clip( 1.0 - u * u, 0.0, 1.0 ) ** 0.55
        rel = v / np.maximum( w, 1e-6 )
        inside = ( np.abs( u ) < 1.0 ) & ( np.abs( rel ) < 1.0 )
        dome = np.sqrt( np.clip( 1.0 - rel * rel, 0.0, 1.0 ) ) * np.sqrt( w )
        h = np.where( inside, depth[idx] + thick * dome, -1e9 )
        best = np.argmax( h, 1 )
        at = np.arange( len( q ) )
        hit = h[at, best] > -1e8
        sl = slice( r0, r0 + rows )
        grain[sl] = np.where( hit, idx[at, best], -1 ).reshape( -1, n )
        top[sl] = np.where( hit, h[at, best], -1.0 ).reshape( -1, n )
        uu[sl] = np.where( hit, u[at, best], 0.0 ).reshape( -1, n )
        vv[sl] = np.where( hit, rel[at, best], 0.0 ).reshape( -1, n )
    return grain, top, uu, vv


@texture( "malt" )
def malt( rng, n ):
    """ Malted barley, as it lies on the malting floor and in the kiln, 16 px an inch: grains about 3/8 in long lying
    every way over each other, each a pale gold husk drawn to a point at both ends with fine ridges along it, the
    crease down its belly on the ones lying face up, a brown spot where the rootlets came off; a little darker and
    browner here and there (a hotter part of the kiln), dark between them where the grains below show. """
    p = n / 64.0
    pts = jittered( rng, n, 2.3, 0.5 )
    m = len( pts )
    length = rng.uniform( 0.33, 0.42, m ) * p
    width = length * rng.uniform( 0.36, 0.44, m )
    angle = rng.uniform( 0, math.pi, m )
    depth = rng.uniform( 0.0, 0.16, m )
    grain, top, u, v = _spindles( rng, n, pts, length, width, angle, depth, 0.09 )
    gap = grain < 0
    g = np.maximum( grain, 0 )
    palette = np.array( [ ( 214, 180, 116 ), ( 202, 166, 102 ), ( 224, 194, 132 ), ( 190, 152, 92 ), ( 208, 176, 120 ) ],
                        float )
    base = palette[rng.integers( 0, len( palette ), m )] * rng.uniform( 0.92, 1.06, ( m, 1 ) )
    kilned = smoothstep( 0.6, 2.2, noise( rng, n, 2.6, 1, 8 ) )
    tone = mix( base[g], ( 168, 118, 66 ), 0.45 * kilned )
    belly = ( rng.random( m ) < 0.5 )[g]
    flip = np.where( rng.random( m ) < 0.5, 1.0, -1.0 )[g]
    ridges = np.cos( v * math.pi * 2.5 ) * np.sqrt( np.clip( 1 - v * v, 0, 1 ) )
    crease = np.exp( -( v / 0.16 ) ** 2 ) * belly * np.clip( 1 - u * u, 0, 1 )
    germ = smoothstep( 0.62, 0.9, u * flip )
    dome = np.sqrt( np.clip( 1 - v * v, 0, 1 ) )
    lum = ( 0.58 + 0.42 * dome ) * ( 1.0 + 0.05 * ridges ) * ( 1.0 - 0.35 * crease )
    c = lum_paint( tone, lum )
    c = mix( c, ( 120, 84, 46 ), 0.55 * germ )
    # Husk flakes and rootlets (the culms) lying loose over them.
    culms = crack_lines( rng, n, 260, ( 0.08 * p, 0.3 * p ), 0.6, branch=0.2, turn=0.5 )
    flakes = dots( rng, n, 300, ( 0.04 * p, 0.09 * p ), profile="flat", soft=0.6 )
    loose = np.maximum( culms, flakes )
    height = np.where( gap, -0.05, top ) + 0.004 * ridges * ( 1 - gap ) - 0.012 * crease + 0.01 * loose
    # The grains under the top ones are in the shade: the deeper the darker.
    below, _ = cavities( height, 1.6 )
    gap_c = mix( flat( n, ( 52, 38, 22 ) ), ( 96, 72, 42 ), 0.4 * smoothstep( -1, 1, noise( rng, n, 1.0, 40, n / 3 ) ) )
    c = np.where( gap[..., None], gap_c, c )
    c = darken( c, ( 0.72 + 0.28 * smoothstep( -0.05, 0.2, height ) ) * np.exp( -6.0 * below ) )
    c = mix( c, ( 214, 196, 150 ), 0.7 * loose )
    rough = np.clip( np.where( gap, 0.92, 0.6 + 0.08 * kilned + 0.06 * crease ) + 0.04 * noise( rng, n, 1.0, 40, None ),
                     0, 1 )
    return { "sh_malt": c }, rough, height, 1024 / 64


@texture( "sack" )
def sack( rng, n ):
    """ Jute hessian, the sacks' cloth, 16 px an inch: a coarse plain weave of 5 threads an inch each way, the threads
    uneven (slubs, thick and thin along them), hairy and wandering a little, the dark of the sack's inside showing
    through the holes between them; the cloth creased and bagged, floury with malt dust in patches and stained where it
    stood in the wet. Drawn twice over and shrunk. """
    s = 2
    N = n * s
    count = n * 5 // 16                      # threads a tile each way (even, so the weave wraps)
    P = N / count
    x, y = coords( N )
    gx = ( x + 0.22 * P * noise( rng, N, 2.0, 2, 30 ) ) / P
    gy = ( y + 0.22 * P * noise( rng, N, 2.0, 2, 30 ) ) / P
    i = np.floor( gx )
    j = np.floor( gy )
    fu = gx - i - 0.5
    fv = gy - j - 0.5
    rows_i = np.arange( N )
    # Each thread's slubs: thick and thin along it, the same right across it.
    slub_w = BT.stretched( rng, N, 1.2, 6, N / 2, ( 10.0, 0.0 ) )[rows_i[:, None], ( ( i + 0.5 ) * P ).astype( int ) % N]
    slub_f = BT.stretched( rng, N, 1.2, 6, N / 2, ( 0.0, 10.0 ) )[( ( j + 0.5 ) * P ).astype( int ) % N, rows_i[None, :]]
    hw = np.clip( 0.37 + 0.08 * slub_w, 0.24, 0.5 )
    hf = np.clip( 0.37 + 0.08 * slub_f, 0.24, 0.5 )
    sw = np.where( i % 2 == 0, 1.0, -1.0 )
    sf = np.where( j % 2 == 0, 1.0, -1.0 )
    z_warp = np.cos( np.pi * ( gy - 0.5 ) ) * sw
    z_weft = -np.cos( np.pi * ( gx - 0.5 ) ) * sf
    prof_w = np.sqrt( np.clip( 1 - ( fu / hw ) ** 2, 0, 1 ) )
    prof_f = np.sqrt( np.clip( 1 - ( fv / hf ) ** 2, 0, 1 ) )
    r, amp = 0.045, 0.028
    top_w = np.where( np.abs( fu ) < hw, amp * z_warp + r * prof_w, -1.0 )
    top_f = np.where( np.abs( fv ) < hf, amp * z_weft + r * prof_f, -1.0 )
    warp_on = top_w >= top_f
    surface = np.maximum( top_w, top_f )
    hole = surface < -0.5
    hair_w = BT.stretched( rng, N, 0.8, 60, None, ( 2.5, 0.3 ) )
    hair_f = BT.stretched( rng, N, 0.8, 60, None, ( 0.3, 2.5 ) )
    tone_w = rng.uniform( 0.86, 1.12, count )[i.astype( int ) % count]
    tone_f = rng.uniform( 0.86, 1.12, count )[j.astype( int ) % count]
    z = np.where( warp_on, z_warp, z_weft )
    prof = np.where( warp_on, prof_w, prof_f )
    hair = np.where( warp_on, hair_w, hair_f )
    lum = np.where( warp_on, tone_w, tone_f ) * ( 1 + 0.12 * hair ) * ( 0.62 + 0.38 * ( 0.5 + 0.5 * z ) ) \
        * ( 0.55 + 0.45 * prof ** 0.6 )
    c = np.where( hole[..., None], flat( N, ( 34, 26, 18 ) ), lum_paint( ( 182, 150, 100 ), lum ) )
    height = np.where( hole, -0.07, surface ) + 0.006 * hair * ( ~hole )
    c = c.reshape( n, s, n, s, 3 ).mean( ( 1, 3 ) )
    height = height.reshape( n, s, n, s ).mean( ( 1, 3 ) )
    hole_n = hole.reshape( n, s, n, s ).mean( ( 1, 3 ) )
    # The sack's shape on the cloth: bagging and creases.
    p = n / 64.0
    bag = 0.22 * noise( rng, n, 3.0, 1, 8 )
    folds = T.blur( crack_lines( rng, n, 14, ( 6 * p, 20 * p ), 4.0, branch=0.0, turn=0.03, pull=0.4 ), 2.0 * p )
    folds = folds / max( folds.max(), 1e-6 )
    height = height + bag - 0.18 * folds
    # Malt dust caught in the weave, damp stains with their tide marks, and grime.
    dust = smoothstep( 0.3, 2.0, noise( rng, n, 2.5, 1, 12 ) + 0.4 * noise( rng, n, 1.5, 12, 80 ) ) \
        * ( 0.6 + 0.4 * hole_n )
    damp_f = noise( rng, n, 2.6, 1, 10 ) + 0.25 * noise( rng, n, 1.8, 10, 60 )
    damp = smoothstep( 0.8, 2.2, damp_f )
    grime = smoothstep( 0.4, 2.2, streaks( rng, n, 1.6, 2, 60, 10 * p, 0.8 * p ) )
    c = darken( c, 1.0 - 0.25 * folds )
    c = mix( c, ( 206, 192, 162 ), 0.45 * dust )
    c = darken( c, 1.0 - 0.3 * damp )
    c = mix( c, ( 96, 82, 60 ), 0.25 * grime )
    rough = np.clip( 0.9 + 0.05 * hole_n - 0.06 * damp + 0.03 * dust, 0, 1 )
    return { "sh_sack": c }, rough, height, 1024 / 64


@texture( "rope" )
def rope( rng, n ):
    """ Three-strand laid manila, 32 px an inch, its length up the picture: the strands spiral up to the right (a
    right-hand lay), 1.8 in apart along the rope and 37 degrees off it, each a rounded bundle of yarns lying nearly along
    the rope, hairy with loose fibres; weathered grey in patches, greener and dirtier down in the grooves. """
    p = n / 16.0
    x, y = coords( n )
    phase = ( 12 * x + 9 * y ) / n
    t = phase - np.floor( phase )
    strand = np.floor( phase ).astype( int ) % 3
    ridge = np.sin( np.pi * t ) ** 0.55
    groove = 1 - np.sin( np.pi * t ) ** 0.25
    phase2 = ( -64 * x + 9 * y ) / n + 0.37 * strand
    yarn = np.sin( np.pi * ( phase2 - np.floor( phase2 ) ) ) ** 0.7
    fibre = streaks( rng, n, 0.9, 24, n / 2, 5, 0.3 )
    fuzz = Canvas( n, 2, 24 )
    for _ in range( 900 ):
        x0, y0 = rng.uniform( 0, n, 2 )
        a = math.pi / 2 + rng.normal( 0, 0.5 )
        ln = rng.uniform( 0.15, 0.5 ) * p
        bend = rng.normal( 0, 0.4 )
        pts = [ ( x0 + math.cos( a + bend * k / 4 ) * ln * k / 4, y0 + math.sin( a + bend * k / 4 ) * ln * k / 4 )
                for k in range( 5 ) ]
        fuzz.line( pts, 0.6, rng.uniform( 0.5, 1.0 ) )
    fuzz = fuzz.result()
    tone = np.array( [ 1.0, 0.95, 1.04 ] )[strand]
    lum = tone * ( 0.36 + 0.64 * ridge ** 0.8 ) * ( 0.86 + 0.14 * yarn ) * ( 1 + 0.07 * fibre )
    c = lum_paint( ( 190, 164, 116 ), lum )
    weather = smoothstep( -0.2, 1.8, noise( rng, n, 2.5, 1, 8 ) + 0.3 * noise( rng, n, 1.5, 8, 40 ) )
    c = mix( c, lum_paint( ( 150, 146, 132 ), lum ), 0.5 * weather )
    algae = smoothstep( -0.5, 1.5, noise( rng, n, 2.4, 1, 10 ) ) * groove
    c = mix( c, ( 78, 78, 52 ), 0.5 * algae )
    c = mix( c, ( 214, 196, 156 ), 0.55 * fuzz )
    stains = smoothstep( 1.0, 2.6, noise( rng, n, 2.6, 1, 12 ) ) * ( 0.5 + 0.5 * groove )
    c = darken( c, 1.0 - 0.3 * stains )
    height = 0.3 * ridge + 0.035 * yarn * ridge + 0.006 * fibre + 0.012 * fuzz
    rough = np.clip( 0.86 + 0.05 * groove + 0.04 * weather - 0.1 * stains, 0, 1 )
    return { "sh_rope": c }, rough, height, 1024 / 16


@texture( "net" )
def net( rng, n ):
    """ Green nylon fishing net, 8 px an inch: knotted diamond meshes about 4 3/4 in stretched, hung so they're taller
    than wide, the twine sagging a little out of true; faded and dirty here and there, mended in two places with
    orange and blue twine. Alpha-tested: only the twine and the knots are there. """
    p = n / 64.0
    x, y = coords( n )
    xd = x + 2.2 * noise( rng, n, 2.6, 1, 6 )
    yd = y + 2.8 * noise( rng, n, 2.6, 1, 6 )
    A, B = 24, 16
    k = math.hypot( A, B ) / n
    ph1 = ( A * xd + B * yd ) / n
    ph2 = ( A * xd - B * yd ) / n
    dp, dq = ph1 - np.round( ph1 ), ph2 - np.round( ph2 )
    d1 = np.abs( dp ) / k
    d2 = np.abs( dq ) / k
    dk = np.hypot( n * ( dp + dq ) / ( 2 * A ), n * ( dp - dq ) / ( 2 * B ) )
    half = 1.15 + 0.15 * noise( rng, n, 1.5, 8, 60 )
    alpha = np.maximum( np.maximum( np.clip( half + 0.5 - d1, 0, 1 ), np.clip( half + 0.5 - d2, 0, 1 ) ),
                        np.clip( 2.3 + 0.5 - dk, 0, 1 ) )
    knot = np.clip( 2.7 - dk, 0, 1 )
    tube = np.maximum( np.maximum( np.sqrt( np.clip( 1 - ( d1 / ( half + 0.4 ) ) ** 2, 0, 1 ) ),
                                   np.sqrt( np.clip( 1 - ( d2 / ( half + 0.4 ) ) ** 2, 0, 1 ) ) ),
                       1.4 * np.sqrt( np.clip( 1 - ( dk / 2.7 ) ** 2, 0, 1 ) ) )
    fade = smoothstep( -0.8, 1.6, noise( rng, n, 2.6, 1, 8 ) )
    dirt = smoothstep( 0.6, 2.2, noise( rng, n, 2.2, 2, 20 ) )
    lum = ( 0.55 + 0.45 * np.clip( tube, 0, 1 ) ) * ( 1 + 0.06 * noise( rng, n, 1.0, 30, n / 2 ) )
    c = lum_paint( ( 66, 118, 84 ), lum )
    c = mix( c, lum_paint( ( 118, 146, 120 ), lum ), 0.45 * fade )
    c = mix( c, lum_paint( ( 74, 70, 52 ), lum ), 0.4 * dirt )
    c = darken( c, 1.0 - 0.25 * knot )
    # Mends: patches of meshes knotted again in other twine.
    for rgb in ( ( 212, 100, 36 ), ( 46, 84, 150 ) ):
        m = np.zeros( ( n, n ) )
        stamp( m, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 4, 7 ) * p, rng.uniform( 3, 5 ) * p, 1.0,
               angle=rng.uniform( 0, math.pi ), soft=0.5 * p )
        c = mix( c, lum_paint( rgb, lum ), m )
    c = _push_pull( c, ( alpha > 0.5 ).astype( float ) )
    height = 0.07 * np.clip( tube, 0, 1.4 )
    rough = np.clip( 0.62 + 0.15 * fade + 0.15 * dirt, 0, 1 )
    return { "sh_net": c }, rough, height, 1024 / 64, { "trans": alpha }


def _scratches( rng, n, count, length, width, angle, spread ):
    """ Straight-ish scratches, mostly at angle (rad) give or take spread, 0..1. """
    canvas = Canvas( n, 2, int( length[1] ) + 8 )
    for _ in range( count ):
        x0, y0 = rng.uniform( 0, n, 2 )
        a = angle + rng.normal( 0, spread )
        ln = rng.uniform( *length )
        bend = rng.normal( 0, 0.05 )
        pts = [ ( x0 + math.cos( a + bend * k / 6 ) * ln * k / 6, y0 + math.sin( a + bend * k / 6 ) * ln * k / 6 )
                for k in range( 7 ) ]
        canvas.line( pts, rng.uniform( 0.6, 1.0 ) * width, rng.uniform( 0.4, 1.0 ) )
    return canvas.result()


@texture( "fishbox" )
def fishbox( rng, n ):
    """ Moulded polyethylene fish boxes, 16 px an inch: the walls' stiffening ribs up the picture every 4 in, a fine
    moulded stipple, chalky where the sun has faded them; scuffed and scraped along (the plastic goes whitish where
    it's scratched), grimy in the ribs' corners, with dried salt and the odd fish scale stuck to them. Blue and
    orange share it. """
    p = n / 32.0
    x, y = coords( n )
    period = n / 8
    t = np.abs( ( x % period ) - period / 2 )
    rib = np.clip( 1 - ( t / ( 0.3 * p ) ) ** 2, 0, 1 ) ** 0.5
    fillet = np.exp( -( ( t - 0.3 * p ) / ( 0.12 * p ) ) ** 2 ) * ( t > 0.3 * p )
    stipple = noise( rng, n, 0.6, n / 6, None )
    wave = noise( rng, n, 2.8, 1, 8 )
    height = 0.12 * rib + 0.0015 * stipple + 0.01 * wave
    scratches = _scratches( rng, n, 140, ( 0.5 * p, 4.0 * p ), 0.7, 0.0, 0.15 )
    scuff = smoothstep( 0.6, 2.0, noise( rng, n, 2.4, 2, 12 ) ) \
        * smoothstep( -0.2, 1.2, BT.stretched( rng, n, 1.0, 10, n / 2, ( 0.3, 6.0 ) ) )
    fade = smoothstep( -0.6, 1.6, noise( rng, n, 2.6, 1, 6 ) )
    below, _ = cavities( height, 0.4 * p )
    grime = np.clip( 40 * below, 0, 1 ) * ( 0.5 + 0.5 * smoothstep( -1, 1, noise( rng, n, 2.0, 2, 20 ) ) ) \
        + 0.6 * fillet * smoothstep( -0.5, 1.5, noise( rng, n, 2.0, 2, 16 ) )
    grime = np.clip( grime + 0.4 * smoothstep( 0.8, 2.4, noise( rng, n, 2.4, 1, 10 ) ), 0, 1 )
    salt = smoothstep( 1.4, 3.2, noise( rng, n, 2.0, 2, 30 ) + 0.8 * grain_field( rng, n, 0.6, 3.0 ) )
    scales = dots( rng, n, 30, ( 0.08 * p, 0.16 * p ), profile="flat", soft=0.5 )
    colours = {}
    for name, ( base, faded ) in { "sh_fishbox_blue": ( ( 36, 84, 166 ), ( 92, 128, 180 ) ),
                                   "sh_fishbox_orange": ( ( 232, 108, 26 ), ( 232, 156, 102 ) ) }.items():
        c = lum_paint( base, 1.0 + 0.02 * stipple + 0.03 * wave - 0.12 * fillet )
        c = mix( c, faded, 0.4 * fade )
        c = mix( c, mix( base, ( 236, 236, 230 ), 0.5 ), 0.55 * scratches + 0.2 * scuff )
        c = mix( c, ( 70, 66, 56 ), 0.45 * grime )
        c = mix( c, ( 226, 226, 220 ), 0.25 * salt )
        c = mix( c, ( 214, 220, 222 ), 0.8 * scales )
        colours[name] = c
    rough = np.clip( 0.42 + 0.03 * stipple + 0.2 * fade + 0.2 * scuff + 0.2 * scratches + 0.25 * grime + 0.2 * salt
                     - 0.2 * scales, 0, 1 )
    height = height - 0.004 * scratches - 0.002 * scuff + 0.004 * salt
    return colours, rough, height, 1024 / 32


@texture( "rubber" )
def rubber( rng, n ):
    """ Old black rubber (the pier's tyre fenders, a boat's rubbing strake), 8 px an inch: matt, with the soft brownish
    grey bloom of age over it, rubbed back to a darker sheen where it bears on the quay, crazed by the weather into
    short cracks across the stretch, scuffed grey by the stone, with a film of dried salt and splashed mud. """
    p = n / 64.0
    fine = noise( rng, n, 0.8, n / 6, None )
    broad = noise( rng, n, 2.8, 1, 8 )
    bloom = smoothstep( -1.6, 2.2, noise( rng, n, 2.4, 1, 12 ) + 0.35 * noise( rng, n, 1.6, 12, 60 ) )
    rubbed = smoothstep( 0.2, 2.4, noise( rng, n, 2.8, 1, 6 ) + 0.6 * BT.stretched( rng, n, 1.4, 4, 80, ( 1.0, 12.0 ) ) )
    crazed = smoothstep( -0.4, 1.6, noise( rng, n, 2.4, 1, 8 ) ) * ( 1 - 0.7 * rubbed )
    cracks = _scratches( rng, n, 1600, ( 0.2 * p, 0.8 * p ), 0.7, 0.0, 0.3 ) * crazed
    scuffs = _scratches( rng, n, 60, ( 1.0 * p, 5.0 * p ), 1.1, 0.0, 0.2 ) * ( 1 - rubbed )
    salt = smoothstep( 0.6, 3.2, grain_field( rng, n, 0.7, 3.0 ) + 0.5 * noise( rng, n, 2.2, 1, 10 ) )
    mud = smoothstep( 0.6, 2.6, noise( rng, n, 2.6, 1, 6 ) + 0.4 * noise( rng, n, 1.6, 6, 40 ) )
    flecks = smoothstep( 1.5, 3.5, grain_field( rng, n, 0.8, 3.0 ) ) * mud
    c = lum_paint( ( 30, 30, 31 ), 1.0 + 0.05 * fine + 0.05 * broad )
    c = mix( c, ( 66, 62, 57 ), 0.5 * bloom * ( 1 - rubbed ) )
    c = mix( c, ( 24, 24, 25 ), 0.6 * rubbed )
    c = mix( c, ( 13, 13, 13 ), 0.65 * cracks )
    c = mix( c, ( 84, 82, 78 ), 0.4 * scuffs )
    c = mix( c, ( 130, 128, 120 ), 0.22 * salt * ( 1 - rubbed ) )
    c = mix( c, ( 70, 60, 46 ), 0.3 * mud * ( 1 - rubbed ) )
    c = mix( c, ( 86, 72, 52 ), 0.6 * flecks )
    height = 0.004 * fine - 0.015 * cracks - 0.006 * scuffs + 0.008 * flecks + 0.02 * broad
    rough = np.clip( 0.8 + 0.08 * bloom - 0.38 * rubbed + 0.05 * cracks + 0.04 * salt + 0.05 * mud, 0, 1 )
    return { "sh_rubber": c }, rough, height, 1024 / 64


@texture( "tile_white" )
def tile_white( rng, n ):
    """ White glazed wall tiles, 6 in square, 10 2/3 px an inch: off-white glaze cushioned at the edges and a little
    wavy, each tile set a touch out of true; thin grey grout, dirtier in places; crazing in the glaze of some (a net of
    hairline cracks, picked out by dirt), the odd chipped edge or corner showing the buff body, and rust and dirt run
    down from above. """
    p = n / 48.0
    x, y = coords( n )
    size = n / 8
    iu, iv = ( x // size ).astype( int ), ( y // size ).astype( int )
    tile = ( iv % 8 ) * 8 + ( iu % 8 )
    u, v = x - iu * size, y - iv * size
    edge = np.minimum( np.minimum( u, size - u ), np.minimum( v, size - v ) )
    grout_half = 0.08 * p
    grout = smoothstep( grout_half + 0.5, grout_half - 0.5, edge )
    cushion = smoothstep( 0.0, 0.45 * p, edge - grout_half ) ** 0.6
    tilt_u = rng.normal( 0, 0.0012, 64 )[tile]
    tilt_v = rng.normal( 0, 0.0012, 64 )[tile]
    proud = rng.normal( 0, 0.012, 64 )[tile]
    glaze_wave = noise( rng, n, 2.4, 4, 30 )
    height = ( 0.05 * cushion + proud + tilt_u * ( u - size / 2 ) + tilt_v * ( v - size / 2 ) + 0.002 * glaze_wave ) \
        * ( 1 - grout ) - 0.05 * grout
    shade = rng.uniform( -1, 1, 64 )[tile]
    warm = ( rng.random( 64 ) < 0.12 )[tile]
    white = mix( flat( n, ( 238, 240, 235 ) ), ( 232, 230, 216 ), 0.6 * warm )
    c = lum_paint( white, 1.0 + 0.012 * shade + 0.006 * glaze_wave )
    # Crazing: a net of hairline cracks over part of some tiles, some of its lines broken off.
    _, border, _ = cells( rng, n, jittered( rng, n, 0.75 * p, 0.5 ), wander=0.6, wander_f=( 20, 120 ) )
    net_lines = smoothstep( 0.7, 0.0, border ) * smoothstep( -0.3, 0.6, noise( rng, n, 1.5, 30, 160 ) )
    crazed_tiles = ( rng.random( 64 ) < 0.35 )[tile]
    crazing = net_lines * crazed_tiles * smoothstep( -0.6, 0.8, noise( rng, n, 2.4, 4, 24 ) ) * ( 1 - grout )
    dirt_f = smoothstep( 0.0, 2.2, noise( rng, n, 2.4, 1, 10 ) )
    c = mix( c, ( 156, 148, 130 ), 0.5 * crazing * ( 0.35 + 0.65 * dirt_f ) )
    # Chips: bites out of the glaze at edges and corners, into the tile.
    chips = np.zeros( ( n, n ) )
    for _ in range( 22 ):
        tx, ty = rng.integers( 0, 8, 2 )
        side = rng.integers( 0, 4 )
        r = rng.uniform( 0.12, 0.35 ) * p
        along_ = rng.uniform( 0.05, 0.95 ) * size if rng.random() < 0.6 else rng.choice( ( 0.0, size ) )
        inward = 0.5 * r + grout_half
        if side < 2:
            cx = tx * size + along_
            cy = ty * size + ( inward if side == 0 else size - inward )
        else:
            cx = tx * size + ( inward if side == 2 else size - inward )
            cy = ty * size + along_
        stamp( chips, cx, cy, r * rng.uniform( 1.0, 1.8 ), r, 1.0, angle=rng.uniform( 0, math.pi ), soft=0.6 )
    chips *= 1 - grout
    grout_c = mix( flat( n, ( 178, 176, 166 ) ), ( 120, 112, 98 ), smoothstep( -0.5, 1.8, noise( rng, n, 2.2, 2, 20 ) ) )
    c = mix( c, ( 206, 192, 162 ), chips )
    c = mix( c, grout_c, grout )
    # Rust and dirt run down from above.
    src = np.zeros( ( n, n ) )
    for _ in range( 5 ):
        stamp( src, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0.3, 1.0 ) * p, 0.3 * p, 1.0, soft=0.5 * p )
    runs = wash_down( src, 18 * p, 0.8, rng, keep=0.7 )
    c = mix( c, ( 168, 120, 78 ), 0.35 * runs )
    c = mix( c, ( 190, 184, 168 ), 0.2 * dirt_f * smoothstep( 0, 3 * p, grout_half + 1.5 * p - edge ) )
    height = height - 0.03 * chips - 0.002 * crazing
    rough = np.clip( 0.08 + 0.02 * dirt_f + 0.75 * grout + 0.7 * chips + 0.2 * runs + 0.08 * crazing, 0, 1 )
    return { "sh_tile_white": c }, rough, height, 1024 / 48


@texture( "window_dark" )
def window_dark( rng, n ):
    """ A window's glass seen from outside, 8 px an inch: dark behind it, the sky and its clouds faintly in it, drawn
    across by the waves of old drawn glass; dusty and filmed with salt, cleaner where the rain has run down it, spotted
    where it dried. """
    p = n / 64.0
    x, y = coords( n )
    ripple = BT.stretched( rng, n, 2.0, 2, 30, ( 0.6, 14.0 ) )
    clouds = noise( rng, n, 2.8, 1, 8 ) + 0.4 * noise( rng, n, 2.0, 8, 30 )
    sky = smoothstep( -0.4, 1.8, ndimage.map_coordinates( clouds, [ y - 0.5 + 3.0 * ripple, x - 0.5 ], order=1,
                                                          mode="grid-wrap" ) )
    inside = smoothstep( 0.4, 2.0, noise( rng, n, 2.6, 1, 6 ) )
    c = lum_paint( ( 16, 19, 24 ), 1.0 + 0.1 * inside )
    c = mix( c, ( 58, 70, 86 ), 0.42 * sky )
    c = mix( c, ( 30, 30, 30 ), 0.3 * inside )
    dust_f = noise( rng, n, 2.6, 1, 8 ) + 0.3 * noise( rng, n, 1.6, 8, 60 )
    runs = smoothstep( 0.4, 1.6, streaks( rng, n, 1.2, 4, 120, 24 * p, 0.6 * p ) )
    dust = smoothstep( -0.4, 1.8, dust_f ) * ( 1 - 0.7 * runs )
    spots = _water_spots( rng, n, 160, ( 0.1 * p, 0.4 * p ), 0.6 )
    c = mix( c, ( 74, 72, 66 ), 0.35 * dust )
    c = mix( c, ( 96, 96, 92 ), 0.3 * spots )
    height = 0.004 * ripple + 0.001 * spots
    rough = np.clip( 0.06 + 0.3 * dust + 0.15 * spots, 0, 1 )
    return { "sh_window_dark": c }, rough, height, 1024 / 64


@texture( "canvas" )
def canvas( rng, n ):
    """ A weathered green-grey tarpaulin of proofed cotton duck, 8 px an inch: the weave faintly, the fold lines from
    being stored folded and the wrinkles of lying draped, a stitched lap seam across it; bleached paler where the sun
    gets it, darker where it stays damp, freckled with mildew, streaked with dirt, a bird's mess or two. """
    p = n / 64.0
    x, y = coords( n )
    weave = 0.5 * ( BT.stretched( rng, n, 0.6, n / 8, None, ( 0.4, 1.6 ) )
                    + BT.stretched( rng, n, 0.6, n / 8, None, ( 1.6, 0.4 ) ) )
    # Fold lines: a rough grid from being stored folded, and wrinkles.
    folds = np.zeros( ( n, n ) )
    for axis in ( 0, 1 ):
        for f in rng.uniform( 0, n, 2 ):
            pos = ( y if axis == 0 else x ) - f - 2.0 * p * noise( rng, n, 2.0, 1, 4 )
            d = ( pos + n / 2 ) % n - n / 2
            folds += np.exp( -( d / ( 0.5 * p ) ) ** 2 ) - 0.5 * np.exp( -( ( np.abs( d ) - 1.0 * p ) / ( 0.6 * p ) ) ** 2 )
    wrinkles = T.blur( crack_lines( rng, n, 30, ( 4 * p, 14 * p ), 2.0, branch=0.3, turn=0.06, pull=0.3 ), 0.8 * p )
    wrinkles /= max( wrinkles.max(), 1e-6 )
    drape = noise( rng, n, 3.0, 1, 8 )
    # A lap seam across, two rows of stitches.
    sy = rng.uniform( 0.2, 0.8 ) * n
    d = ( y - sy + n / 2 ) % n - n / 2
    lap = smoothstep( 0.8 * p + 0.5, 0.8 * p - 0.5, np.abs( d ) )
    stitch = np.zeros( ( n, n ) )
    for off in ( -0.5 * p, 0.5 * p ):
        row = np.exp( -( ( d - off ) / 0.45 ) ** 2 )
        stitch = np.maximum( stitch, row * ( 0.55 + 0.45 * np.cos( 2 * math.pi * x / ( 0.45 * p ) ) ) )
    height = 0.08 * drape - 0.05 * folds - 0.08 * wrinkles + 0.03 * lap + 0.004 * weave + 0.006 * stitch
    fade = smoothstep( -0.4, 1.8, noise( rng, n, 2.6, 1, 6 ) + 0.4 * noise( rng, n, 1.6, 6, 40 ) )
    damp = smoothstep( 0.6, 2.2, noise( rng, n, 2.6, 1, 8 ) )
    mildew = smoothstep( 0.4, 1.0, dots( rng, n, 1800, ( 0.08 * p, 0.3 * p ), profile="dome", soft=0.5 ) ) \
        * smoothstep( 0.2, 1.6, noise( rng, n, 2.4, 1, 10 ) )
    grime = smoothstep( 0.5, 2.2, streaks( rng, n, 1.6, 2, 60, 12 * p, 0.8 * p ) )
    droppings = np.zeros( ( n, n ) )
    for _ in range( 3 ):
        cx, cy = rng.uniform( 0, n, 2 )
        for _ in range( 6 ):
            r = rng.uniform( 0.1, 0.45 ) * p
            stamp( droppings, cx + rng.normal( 0, 0.5 * p ), cy + rng.normal( 0, 0.5 * p ), r, r * 0.8, 1.0, soft=0.5 )
    lum = 1.0 + 0.06 * weave + 0.04 * drape - 0.06 * folds
    c = lum_paint( ( 94, 108, 92 ), lum )
    c = mix( c, lum_paint( ( 140, 144, 128 ), lum ), 0.45 * fade )
    c = darken( c, 1.0 - 0.28 * damp )
    c = mix( c, ( 66, 70, 60 ), 0.25 * lap )
    c = mix( c, ( 160, 160, 140 ), 0.5 * stitch )
    c = mix( c, ( 38, 42, 36 ), 0.6 * mildew )
    c = mix( c, ( 82, 76, 60 ), 0.25 * grime )
    c = mix( c, ( 222, 220, 210 ), 0.85 * droppings )
    rough = np.clip( 0.86 + 0.02 * weave + 0.05 * fade - 0.08 * damp, 0, 1 )
    return { "sh_canvas": c }, rough, height, 1024 / 64


def _palette( t, stops ):
    """ t (0..1) through a list of ( t, sRGB ) stops, in sRGB. """
    t = np.clip( t, 0.0, 1.0 )
    ts = [ s for s, _ in stops ]
    return np.stack( [ np.interp( t, ts, [ c[k] for _, c in stops ] ) for k in range( 3 ) ], -1 )


@texture( "lamp" )
def lamp( rng, n ):
    """ A lantern's glass lit from inside, 8 px an inch: pressed glass with prism ribs across it every half inch, each
    rib's crown bright and yellow-white with the flame behind it and its valleys a deeper orange; the glow swelling
    and fading over the pane, seed bubbles catching the light, and dust and a breath of soot dimming it. The self-lit
    mask carries the brightness. """
    p = n / 32.0
    x, y = coords( n )
    period = 0.5 * p
    yy = y + 0.08 * p * noise( rng, n, 2.6, 1, 4 )
    crown = 0.5 + 0.5 * np.cos( 2 * np.pi * yy / period )
    glow = noise( rng, n, 2.6, 1, 5 )
    flicker = noise( rng, n, 1.6, 6, 40 )
    bubbles = dots( rng, n, 70, ( 0.35, 0.9 ), profile="dome", soft=0.6 )
    soot = smoothstep( 0.4, 2.6, noise( rng, n, 2.6, 1, 6 ) )
    dust = smoothstep( 0.5, 2.5, grain_field( rng, n, 0.7, 3.0 ) + 0.5 * noise( rng, n, 2.0, 2, 16 ) )
    hot, warm, deep = ( 255, 238, 200 ), ( 255, 210, 140 ), ( 244, 168, 92 )
    heat = np.clip( 0.55 + 0.3 * crown + 0.12 * glow + 0.04 * flicker, 0, 1 )
    c = mix( mix( flat( n, deep ), warm, smoothstep( 0.3, 0.7, heat ) ), hot, smoothstep( 0.7, 1.0, heat ) )
    c = mix( c, ( 255, 246, 222 ), 0.7 * bubbles )
    c = mix( c, ( 120, 92, 62 ), 0.35 * soot )
    c = mix( c, ( 200, 170, 128 ), 0.25 * dust )
    illum = np.clip( 0.72 + 0.2 * crown + 0.06 * glow + 0.1 * bubbles - 0.3 * soot - 0.08 * dust, 0, 1 )
    height = 0.02 * crown + 0.002 * flicker
    rough = np.clip( 0.08 + 0.35 * soot + 0.25 * dust, 0, 1 )
    return { "sh_lamp_warm": c }, rough, height, 1024 / 32, { "illum": illum }


@texture( "fire" )
def fire( rng, n ):
    """ The malt kiln's furnace: a bed of burning peat and coke on the grate, 10 2/3 px an inch. Lumps of 1.5-3.5 in,
    each at its own heat: a crust crazed into plates a half inch across, glowing through the seams between them and
    brighter round the lump's rim, where the gaps heat it; pale ash on the plates of the cooler ones. Deep in the gaps
    between the lumps it's white-hot where the draught comes up through the bars and black where it doesn't; the odd
    black lump just thrown on, glowing only in its seams. Its self-lit mask follows the heat. """
    p = n / 48.0
    spacing = 2.4 * p
    pts = jittered( rng, n, spacing, 0.42 )
    k = len( pts )
    radius = spacing * rng.uniform( 0.42, 0.75, k )
    lump, d, off = packed( rng, n, pts, radius )
    # Broken, angular lumps: each squashed along its own axis, its outline bitten.
    turn = rng.uniform( 0, np.pi, k )[lump]
    squash = rng.uniform( 1.0, 1.5, k )[lump]
    along_ = ( off[..., 0] * np.cos( turn ) + off[..., 1] * np.sin( turn ) ) / radius[lump]
    across = ( -off[..., 0] * np.sin( turn ) + off[..., 1] * np.cos( turn ) ) / radius[lump]
    d = np.minimum( d, np.hypot( along_ / squash ** 0.5, across * squash ** 0.5 ) )
    d = d + 0.11 * noise( rng, n, 2.0, 4, 30 ) + 0.05 * noise( rng, n, 1.5, 30, 100 )
    inside = smoothstep( 1.0, 0.9, d )
    gap = 1 - inside
    rim = smoothstep( 0.55, 0.93, d ) * inside
    plate, plate_b, _ = cells( rng, n, jittered( rng, n, 0.55 * p, 0.5 ), wander=0.15 * p, wander_f=( 20, 120 ) )
    seams = smoothstep( 0.9, 0.0, plate_b ) * smoothstep( 0.97, 0.85, d )
    plate_r = rng.random( plate.max() + 1 )[plate]
    swirl = noise( rng, n, 2.0, 6, 40 )
    fresh = ( rng.random( k ) < 0.05 )[lump].astype( float )
    t_k = np.clip( rng.normal( 0.47, 0.13, k ), 0.15, 0.78 )[lump]
    t_lump = t_k - 0.08 * plate_r + 0.26 * seams + 0.24 * rim + 0.05 * swirl
    t_fresh = 0.06 + 0.35 * seams * rim + 0.16 * seams + 0.4 * rim ** 2
    t_lump = t_lump * ( 1 - fresh ) + t_fresh * fresh
    draught = smoothstep( -0.6, 1.0, noise( rng, n, 2.0, 2, 16 ) )
    t_gap = 0.1 + 0.85 * draught
    t = np.clip( t_lump * inside + t_gap * gap, 0, 1 )
    ash_k = np.clip( rng.normal( 0.0, 0.5, k ), -0.6, 0.9 )[lump]
    ash = smoothstep( 0.35, 0.75, ash_k + 0.5 * plate_r + 0.25 * noise( rng, n, 1.8, 8, 60 ) - 0.9 * rim
                      - 0.4 * ( t_k - 0.47 ) ) * ( 1 - fresh ) * inside * ( 1 - 0.8 * seams )
    stops = [ ( 0.0, ( 18, 7, 4 ) ), ( 0.15, ( 48, 12, 5 ) ), ( 0.3, ( 104, 20, 6 ) ), ( 0.45, ( 172, 38, 8 ) ),
              ( 0.6, ( 226, 80, 12 ) ), ( 0.74, ( 252, 134, 30 ) ), ( 0.87, ( 255, 192, 82 ) ),
              ( 1.0, ( 255, 238, 178 ) ) ]
    c = _palette( t, stops )
    ash_c = mix( lum_paint( ( 170, 160, 150 ), 1.0 + 0.1 * noise( rng, n, 1.2, 20, None ) ), ( 212, 206, 198 ),
                 smoothstep( 1.0, 2.5, grain_field( rng, n, 0.7, 3.0 ) ) )
    ash_c = mix( ash_c, c, 0.2 + 0.3 * seams )
    c = mix( c, ash_c, 0.9 * ash )
    char = fresh * ( 1 - smoothstep( 0.2, 0.55, t ) ) * inside
    c = mix( c, lum_paint( ( 30, 26, 23 ), 1.0 + 0.2 * noise( rng, n, 1.2, 20, None ) ), char )
    illum = np.clip( t, 0, 1 ) ** 1.6 * ( 1 - 0.75 * ash ) * ( 1 - 0.9 * char )
    dome = np.sqrt( np.clip( 1 - np.minimum( d, 1 ) ** 2, 0, 1 ) )
    height = ( radius[lump] / p ) * 0.5 * dome + 0.03 * swirl - 0.05 * seams + 0.02 * ash
    rough = np.clip( 0.72 + 0.22 * ash - 0.1 * gap, 0, 1 )
    return { "sh_fire": c }, rough, height, 1024 / 48, { "illum": illum }


@texture( "glass_dirty" )
def glass_dirty( rng, n ):
    """ Old window glass seen against the light, 8 px an inch: the light it lets through. A film of dust over it,
    thicker in drifts, and the pale green of the clean glass where the rain has run down it in narrow wandering trails
    (each edged with the dirt it pushed aside); brown grime washed down from the glazing bars; dried drops, fly specks,
    and the slow waves of drawn sheet glass across it. The roughness blurs what's behind it where it's dusty. """
    p = n / 64.0
    film = noise( rng, n, 2.6, 1, 10 )
    drift = smoothstep( -2.0, 2.0, film + 0.15 * noise( rng, n, 1.6, 10, 80 ) )
    trails = Canvas( n, 2, int( 24 * p ) )
    edges = Canvas( n, 2, int( 24 * p ) )
    for _ in range( 46 ):
        x0, y0 = rng.uniform( 0, n, 2 )
        length = rng.uniform( 3, 16 ) * p
        width = rng.uniform( 0.12, 0.35 ) * p
        steps = 14
        pts, x = [], x0
        for j in range( steps + 1 ):
            pts.append( ( x, y0 + length * j / steps ) )
            x += rng.normal( 0, 0.12 * p )
        trails.line( pts, width, 1.0 )
        edges.line( pts, width + 0.25 * p, 1.0 )
    washed = trails.result()
    rim = np.clip( edges.result() - washed, 0, 1 )
    dust = np.clip( 0.45 + 0.55 * drift, 0, 1 ) * ( 1 - 0.85 * washed )
    src = np.zeros( ( n, n ) )
    for _ in range( 6 ):
        stamp( src, rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 1.0, 4.0 ) * p, 0.15 * p, 1.0, soft=0.3 * p )
    grime = np.clip( wash_down( src, 16 * p, 0.8, rng, keep=0.6 ) - 0.9 * src, 0, 1 ) * ( 1 - 0.6 * washed )
    spots = _water_spots( rng, n, 60, ( 0.4 * p, 1.2 * p ), 0.6 )
    specks = smoothstep( 2.0, 4.0, grain_field( rng, n, 0.6, 4.0 ) )
    c = mix( flat( n, ( 210, 225, 215 ) ), ( 150, 150, 140 ), dust )
    c = mix( c, ( 132, 128, 116 ), 0.5 * rim )
    c = mix( c, ( 110, 106, 94 ), 0.8 * grime )
    c = mix( c, ( 128, 124, 112 ), 0.45 * spots )
    c = mix( c, ( 60, 55, 45 ), 0.8 * specks )
    waves = BT.stretched( rng, n, 2.0, 2, 40, ( 0.6 * p, 10 * p ) )
    height = 0.006 * unit( waves ) + 0.001 * spots + 0.002 * grime
    rough = np.clip( 0.05 + 0.5 * dust + 0.3 * grime + 0.2 * spots + 0.3 * specks + 0.1 * rim, 0, 1 )
    return { "sh_glass_dirty": c }, rough, height, 1024 / 64


@texture( "hill_grass" )
def hill_grass( rng, n ):
    """ Rough hill grazing in October, 1 px an inch (a tile 43 ft across). A fine sward of bents and fescues that the
    sheep keep short, green over straw-coloured thatch and moss, with the odd pale patch of mat-grass; in it, tussocks
    of purple moor-grass 1-2 ft across, gone tawny and straw at their tips and still green at their crowns, their
    leaves flopped over (a little more one way, the wind's), thick in some places and scattered in others; dark clumps
    of soft rush where it's wet, a few small stones, the odd bare scrape. Its broad patches are kept weak so the tile
    doesn't show from afar. """
    p = n / 512.0
    clump = noise( rng, n, 2.2, 3, 12 )
    tawny = noise( rng, n, 2.2, 3, 12 )
    wet = smoothstep( 1.1, 2.1, noise( rng, n, 2.4, 2, 8 ) )
    pale = smoothstep( 1.0, 2.0, noise( rng, n, 2.4, 3, 14 ) )
    colour, rough, height, ao, _ = T.grass_field(
        rng, n,
        soil=( 56, 62, 36 ),
        thatch=[ ( 3, ( 124, 116, 76 ) ), ( 2, ( 140, 130, 88 ) ), ( 2, ( 100, 94, 62 ) ) ],
        blades=[ ( 26, ( 66, 106, 36 ) ), ( 26, ( 80, 120, 40 ) ), ( 16, ( 96, 128, 48 ) ), ( 10, ( 58, 94, 32 ) ),
                 ( 10, ( 112, 124, 62 ) ), ( 6, ( 136, 132, 84 ) ) ],
        clover=None,
        flowers=( 0, [ ( 0, 0, 0 ) ] ),
        blade_count=int( 0.22 * n * n ), thatch_count=int( 0.025 * n * n ), lengths=( 2.5 * p, 6 * p ),
        widths=( 0.8, 1.3 ), patch=0.02, root_dark=0.68 )
    colour = darken( colour, 0.85 + 0.15 * ao )
    moss = smoothstep( 0.5, 1.6, noise( rng, n, 2.0, 8, 60 ) )
    colour = tinted( colour, ( 118, 128, 52 ), 0.35 * moss )
    colour = mix( colour, tinted( colour, ( 150, 148, 112 ), 1.0 ), 0.3 * pale )
    strokes = T.Strokes( colour, 0.3 * height, ss=3 )
    # Purple moor-grass: tussocks, thick where clump is high.
    pts = jittered( rng, n, 17 * p, 0.5 )
    ix, iy = pts[:, 0].astype( int ) % n, pts[:, 1].astype( int ) % n
    keep = rng.random( len( pts ) ) < 0.2 + 0.6 * smoothstep( -1.0, 1.0, clump[iy, ix] )
    keep &= wet[iy, ix] < 0.5
    pts, ix, iy = pts[keep], ix[keep], iy[keep]
    radii = np.exp( rng.uniform( np.log( 6 ), np.log( 13 ), len( pts ) ) ) * p
    straw = np.clip( 0.3 + 0.35 * smoothstep( -1.5, 1.5, tawny[iy, ix] ) + rng.normal( 0, 0.15, len( pts ) ), 0.1, 1 )
    tips = np.array( [ ( 176, 160, 104 ), ( 164, 140, 90 ), ( 186, 172, 122 ), ( 112, 122, 62 ) ], float )
    lean = ( 0.25, 0.1 )
    for i in rng.permutation( len( pts ) ):
        tip = tips[rng.integers( 0, len( tips ) )] * rng.uniform( 0.92, 1.06 )
        _tussock( strokes, rng, pts[i, 0], pts[i, 1], radii[i], np.array( ( 70, 106, 38 ) ) * rng.uniform( 0.88, 1.1 ),
                  tip, straw[i], heights=( 0.35, 0.95 ), density=1.6, width=( 0.45, 0.85 ), bend=0.7,
                  reach=( 0.7, 1.2 ), crown=0.35,
                  lean=( lean[0] + rng.normal( 0, 0.12 ), lean[1] + rng.normal( 0, 0.12 ) ),
                  squash=rng.uniform( 0.8, 1.25 ), turn=rng.uniform( 0, math.pi ), dead_share=0.18 )
    # Soft rush where it's wet: dense dark clumps of stems splaying out, a few dead and brown.
    for cx, cy in jittered( rng, n, 26 * p, 0.5 ):
        if wet[int( cy ) % n, int( cx ) % n] < 0.3 or rng.random() < 0.3:
            continue
        r = rng.uniform( 6, 10 ) * p
        _tussock( strokes, rng, cx, cy, r, ( 40, 60, 28 ), ( 64, 86, 38 ), 0.8, heights=( 0.5, 1.0 ), density=1.6,
                  squash=rng.uniform( 0.85, 1.15 ), turn=rng.uniform( 0, math.pi ), width=( 0.5, 0.8 ),
                  dead=( 122, 100, 64 ), dead_share=0.15, reach=( 0.8, 1.1 ), crown=0.2, bend=0.15, segments=2 )
    colour, h, cover = strokes.result()
    h = T.blur( h, 0.7 )
    occ = T.cavity_ao( h, ( ( 2.0, 2.0 ), ( 6.0, 1.5 ) ), 1.0 )
    colour = darken( colour, 0.65 + 0.35 * occ )
    stones = dots( rng, n, 4, ( 1.5 * p, 2.5 * p ), profile="dome", soft=0.8 ) * ( 1 - cover * smoothstep( 0.3, 0.6, h ) )
    colour = mix( colour, lum_paint( ( 128, 126, 118 ), 0.85 + 0.25 * stones ), smoothstep( 0.1, 0.3, stones ) )
    scrapes = smoothstep( 1.8, 2.8, noise( rng, n, 2.4, 3, 24 ) + 0.5 * noise( rng, n, 1.5, 24, 100 ) )
    colour = mix( colour, lum_paint( ( 88, 72, 52 ), 1.0 + 0.2 * noise( rng, n, 1.2, 30, None ) ), 0.8 * scrapes )
    h_in = 10.0 * h + 1.5 * stones - 1.0 * scrapes
    rough = np.clip( 0.9 - 0.06 * cover * h - 0.08 * stones + 0.03 * noise( rng, n, 1.0, 40, None ), 0, 1 )
    return { "sh_hill_grass": colour }, rough, h_in, 1024 / 512


def _tussock( strokes, rng, cx, cy, r, base, tip, straw, heights=( 0.35, 0.95 ), density=1.2, lean=( 0.0, 0.0 ),
              squash=1.0, turn=0.0, width=( 0.6, 1.1 ), dead=( 150, 138, 96 ), dead_share=0.2, reach=( 0.75, 1.15 ),
              crown=0.3, bend=0.45, segments=4 ):
    """ One tussock from above, r px: its leaves spring from a crown crown x r across and arch out and over every way.
    The old outer ones go first, lowest, longest and dullest, some of them dead (dead_share); the young middle ones
    last, highest and brightest at their tips (straw: how far the tips have turned from base to tip). Its outline is
    an ellipse (squash, turn), and lean (a share of r, in the picture) pushes the leaves' ends one way, as the wind
    combs them. """
    count = int( density * r * r ) + 10
    cu, su = math.cos( turn ), math.sin( turn )
    base, tip, dead = np.asarray( base, float ), np.asarray( tip, float ), np.asarray( dead, float )
    h0, h1 = heights
    for k in range( count ):
        tier = k / count
        a = rng.uniform( 0, 2 * math.pi )
        start = r * crown * math.sqrt( rng.random() )
        length = r * ( 1.2 - 0.5 * tier ) * rng.uniform( *reach )
        curl = rng.normal( 0, bend )
        heading = a + rng.normal( 0, 0.35 )
        ox, oy = math.cos( a ) * start, math.sin( a ) * start
        pts = []
        for j in range( segments + 1 ):
            t = j / segments
            ang = heading + curl * t
            u = ( ox + math.cos( ang ) * length * t ) * squash
            v = ( oy + math.sin( ang ) * length * t ) / squash
            x = cx + u * cu - v * su + lean[0] * r * t * t * ( 1.2 - tier )
            y = cy + u * su + v * cu + lean[1] * r * t * t * ( 1.2 - tier )
            pts.append( ( x, y ) )
        shade = ( 0.7 + 0.35 * tier ) * rng.uniform( 0.86, 1.12 )
        s = float( np.clip( straw + rng.normal( 0, 0.2 ), 0, 1 ) )
        is_dead = rng.random() < dead_share * ( 1.2 - tier )
        w = rng.uniform( *width )
        cols, ws, hs = [], [], []
        for j in range( segments ):
            t = ( j + 0.5 ) / segments
            c = dead * rng.uniform( 0.9, 1.06 ) if is_dead else mix( base, tip, s * t ** 0.5 )
            cols.append( np.clip( c * shade * ( 0.88 + 0.16 * t ), 0, 255 ) )
            ws.append( w * ( 1.0 - 0.5 * t ) )
            hs.append( float( np.clip( h0 + ( h1 - h0 ) * ( 0.35 + 0.65 * tier ) * ( 1 - 0.6 * t ** 1.5 ), 0, 1 ) ) )
        strokes.blade( pts, ws, cols, hs )


@texture( "field" )
def field( rng, n ):
    """ An in-bye field of improved pasture in October, 1 px an inch: rye-grass and white clover grazed short and dense,
    bright green, with patches of clover; a few cow pats, old and crusted or fresh, each in a ring of the darker, ranker
    grass the cattle leave round it; a couple of docks and thistle rosettes. Its broad patches are kept weak. """
    p = n / 512.0
    colour, rough, height, ao, _ = T.grass_field(
        rng, n,
        soil=( 54, 66, 34 ),
        thatch=[ ( 3, ( 112, 108, 64 ) ), ( 2, ( 128, 120, 74 ) ), ( 2, ( 94, 92, 54 ) ) ],
        blades=[ ( 26, ( 64, 110, 36 ) ), ( 30, ( 80, 124, 42 ) ), ( 22, ( 96, 136, 48 ) ), ( 10, ( 112, 142, 58 ) ),
                 ( 8, ( 54, 94, 32 ) ), ( 4, ( 122, 128, 68 ) ) ],
        clover=( int( 1400 * p * p ), ( 62, 104, 46 ) ),
        flowers=( int( 3 * p * p ), [ ( 226, 224, 210 ) ] ),
        blade_count=int( 0.24 * n * n ), thatch_count=int( 0.015 * n * n ), lengths=( 2.0 * p, 5.0 * p ),
        widths=( 0.9, 1.4 ), patch=0.02, root_dark=0.7 )
    colour = darken( colour, 0.85 + 0.15 * ao )
    trodden = smoothstep( 0.6, 2.0, noise( rng, n, 2.0, 6, 30 ) )
    colour = tinted( colour, ( 120, 130, 66 ), 0.12 * trodden )
    strokes = T.Strokes( colour, 0.4 * height, ss=3 )
    pats = np.zeros( ( n, n ) )
    for _ in range( 5 ):
        x, y = rng.uniform( 0, n, 2 )
        r = rng.uniform( 5.0, 7.0 ) * p
        # The rank grass round it, longer and darker.
        for _ in range( int( 70 * r / p ) ):
            a = rng.uniform( 0, 2 * math.pi )
            d = r * ( 1.0 + 2.2 * rng.random() ** 0.8 )
            x0, y0 = x + math.cos( a ) * d, y + math.sin( a ) * d
            col = np.array( ( 52, 92, 32 ) ) * rng.uniform( 0.8, 1.2 )
            pts = T.curve_points( x0, y0, rng.uniform( 0, 2 * math.pi ), rng.uniform( 3, 7 ) * p, rng.normal( 0, 0.5 ), 3 )
            w = rng.uniform( 0.9, 1.4 )
            strokes.blade( pts, [ w, 0.8 * w, 0.5 * w ], [ col * 0.75, col, col * 1.1 ], [ 0.6, 0.65, 0.6 ] )
        if rng.random() < 0.8:
            old = rng.random() < 0.6
            body = np.array( ( 90, 90, 70 ) if old else ( 58, 56, 36 ) )
            for _ in range( 7 ):
                ox, oy = rng.normal( 0, 0.25 * r, 2 )
                rr = r * rng.uniform( 0.7, 1.0 )
                strokes.dot( x + ox, y + oy, rr, rr * rng.uniform( 0.7, 1.0 ), body * rng.uniform( 0.9, 1.08 ), 0.5 )
            for _ in range( 12 ):
                ox, oy = rng.normal( 0, 0.3 * r, 2 )
                rr = rng.uniform( 0.6, 1.4 ) * p
                strokes.dot( x + ox, y + oy, rr, rr, body * rng.uniform( 0.8, 1.2 ), 0.52 )
            stamp( pats, x, y, r * 0.9, r * 0.9, 0.5 if old else 1.0, soft=1.0 )
    # Docks: broad leaves, dark green with a pale midrib; thistles: narrow spiny grey-green leaves.
    for _ in range( 3 ):
        x, y = rng.uniform( 0, n, 2 )
        dock = rng.random() < 0.5
        for _ in range( int( rng.integers( 5, 8 ) if dock else rng.integers( 8, 13 ) ) ):
            a = rng.uniform( 0, 2 * math.pi )
            length = rng.uniform( 6, 10 ) * p if dock else rng.uniform( 4, 7 ) * p
            w = rng.uniform( 2.5, 3.5 ) * p if dock else rng.uniform( 1.2, 1.8 ) * p
            col = np.array( ( 50, 84, 34 ) if dock else ( 92, 110, 68 ) ) * rng.uniform( 0.9, 1.1 )
            pts = T.curve_points( x, y, a, length, rng.normal( 0, 0.2 ), 3 )
            strokes.blade( pts, [ 0.5 * w, w, 0.5 * w ], [ col * 0.85, col, col * 1.08 ], [ 0.8, 0.85, 0.8 ] )
            rib = np.array( ( 96, 106, 66 ) if dock else ( 118, 128, 92 ) )
            strokes.blade( pts[:3], [ 0.5, 0.4 ], [ rib, rib ], [ 0.86, 0.86 ] )
    colour, h, cover = strokes.result()
    h = T.blur( h, 0.6 )
    h_in = 4.0 * h + 1.0 * pats
    rough = np.clip( 0.88 - 0.05 * ( h > 0.75 ) - 0.25 * pats + 0.03 * noise( rng, n, 1.0, 40, None ), 0, 1 )
    return { "sh_field": colour }, rough, h_in, 1024 / 512


@texture( "moor" )
def moor( rng, n ):
    """ Wet blanket bog in October, 1 px an inch: dark peat under a carpet of bog moss (red on the hummocks, ochre and
    green on the lawns, bright green round the pools); tufts of deer-grass gone orange-tawny all over it, a few pale
    tussocks of cotton-grass, the orange stems of bog asphodel, sprigs of heather on the drier hummocks, and black
    pools of peaty water, glossy, in the hollows. """
    p = n / 512.0
    hum = noise( rng, n, 2.4, 2, 24 ) + 0.35 * noise( rng, n, 1.8, 24, 90 )
    pools = smoothstep( -1.85, -2.3, hum )
    edge = smoothstep( -1.3, -1.85, hum ) * ( 1 - pools )
    dry = smoothstep( 0.4, 1.4, hum )
    kind = noise( rng, n, 2.2, 3, 30 )
    fine = noise( rng, n, 1.0, 60, None )
    moss = mix( flat( n, ( 92, 98, 54 ) ), ( 138, 118, 70 ), smoothstep( -0.8, 0.4, kind ) )
    moss = mix( moss, ( 122, 72, 56 ), smoothstep( 0.3, 1.2, kind ) * ( 0.4 + 0.6 * dry ) )
    moss = mix( moss, ( 96, 108, 52 ), edge )
    moss = lum_paint( moss, 1.0 + 0.22 * fine + 0.1 * noise( rng, n, 1.6, 10, 60 ) )
    peat = lum_paint( ( 48, 38, 28 ), 1.0 + 0.15 * fine )
    cover = smoothstep( -0.6, 0.6, noise( rng, n, 2.0, 4, 40 ) + 1.0 )
    base = mix( peat, moss, cover * ( 1 - pools ) )
    water = lum_paint( ( 26, 22, 17 ), 1.0 + 0.08 * noise( rng, n, 2.0, 2, 30 ) )
    base = mix( base, water, pools )
    strokes = T.Strokes( base, np.clip( 0.25 + 0.06 * hum, 0, 1 ), ss=3 )
    # Bog asphodel's stems, orange-brown, over the lawns.
    for _ in range( int( 900 * p * p ) ):
        x, y = rng.uniform( 0, n, 2 )
        if pools[int( y ) % n, int( x ) % n] > 0.1:
            continue
        col = np.array( ( 168, 98, 44 ) ) * rng.uniform( 0.8, 1.15 )
        pts = T.curve_points( x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 2, 4 ) * p, rng.normal( 0, 0.3 ), 2 )
        strokes.blade( pts, [ 0.6, 0.5 ], [ col * 0.85, col ], [ 0.45, 0.5 ] )
    # Deer-grass: small dense tufts, orange-tawny.
    pts = jittered( rng, n, 9 * p, 0.5 )
    ix, iy = pts[:, 0].astype( int ) % n, pts[:, 1].astype( int ) % n
    keep = ( pools[iy, ix] < 0.2 ) & ( rng.random( len( pts ) ) < 0.85 * ( 1 - dry[iy, ix] ) * ( 1 - 0.6 * edge[iy, ix] ) )
    tips = np.array( [ ( 164, 120, 72 ), ( 172, 138, 90 ), ( 150, 108, 66 ), ( 160, 134, 96 ) ], float )
    for cx, cy in pts[keep]:
        _tussock( strokes, rng, cx, cy, rng.uniform( 2.5, 5.0 ) * p, np.array( ( 86, 88, 52 ) ) * rng.uniform( 0.9, 1.1 ),
                  tips[rng.integers( 0, len( tips ) )] * rng.uniform( 0.9, 1.06 ), rng.uniform( 0.55, 0.95 ),
                  heights=( 0.4, 0.85 ), density=2.5, width=( 0.4, 0.7 ), segments=3, dead=( 146, 126, 94 ),
                  reach=( 0.6, 1.0 ), bend=0.6,
                  dead_share=0.15, squash=rng.uniform( 0.85, 1.15 ), turn=rng.uniform( 0, math.pi ) )
    # Cotton-grass: fewer, bigger and paler tussocks.
    wetness = smoothstep( 0.0, -1.6, hum )
    for cx, cy in jittered( rng, n, 22 * p, 0.5 ):
        if pools[int( cy ) % n, int( cx ) % n] > 0.1 or rng.random() > 0.15 + 0.7 * wetness[int( cy ) % n, int( cx ) % n]:
            continue
        tip = np.array( ( 176, 166, 128 ) if rng.random() < 0.6 else ( 162, 150, 110 ) )
        _tussock( strokes, rng, cx, cy, rng.uniform( 5, 9 ) * p, np.array( ( 92, 100, 58 ) ) * rng.uniform( 0.9, 1.1 ),
                  tip, 0.7, heights=( 0.45, 0.95 ), density=1.4, width=( 0.5, 0.9 ), bend=0.6,
                  squash=rng.uniform( 0.85, 1.15 ), turn=rng.uniform( 0, math.pi ) )
    # Heather on the drier hummocks: low sprigs, brown-purple with a little dark green.
    for cx, cy in jittered( rng, n, 9 * p, 0.5 ):
        if rng.random() > 1.2 * dry[int( cy ) % n, int( cx ) % n] - 0.1:
            continue
        r = rng.uniform( 4, 7 ) * p
        for _ in range( int( 3.0 * r * r / p / p ) ):
            a = rng.uniform( 0, 2 * math.pi )
            rr = r * math.sqrt( rng.random() )
            x0, y0 = cx + math.cos( a ) * rr, cy + math.sin( a ) * rr
            pick = rng.random()
            col = np.array( ( 70, 54, 46 ) if pick < 0.6 else ( 58, 64, 42 ) if pick < 0.85 else ( 104, 72, 78 ) )
            pts_h = T.curve_points( x0, y0, rng.uniform( 0, 2 * math.pi ), rng.uniform( 1.2, 2.5 ) * p, 0.3, 2 )
            strokes.blade( pts_h, [ 0.8, 0.6 ], [ col * rng.uniform( 0.8, 1.1 ), col * rng.uniform( 0.9, 1.2 ) ],
                           [ 0.7, 0.75 ] )
    colour, h, cover = strokes.result()
    h = T.blur( h, 0.9 )
    occ = T.cavity_ao( h, ( ( 2.0, 2.0 ), ( 6.0, 1.2 ) ), 1.0 )
    colour = darken( colour, ( 0.8 + 0.2 * occ ) * ( 1 - pools ) + pools )
    ground = 2.5 * T.blur( h, 0.5 ) + 5.0 * hum
    h_in = ground + ( -8.5 - ground ) * pools
    rough = np.clip( 0.82 - 0.3 * edge - 0.76 * pools + 0.05 * cover * ( 1 - pools )
                     + 0.03 * noise( rng, n, 1.0, 40, None ), 0.04, 1 )
    return { "sh_moor": colour }, rough, h_in, 1024 / 512


def _segments( strokes, x0, y0, x1, y1, width, colour, height ):
    """ Many straight strokes into a T.Strokes at once, drawn in order, each its own width (px), colour and height
    (0..1), wrapping round the tile: Strokes.blade's drawing without its per-call overhead. """
    s = strokes.ss
    big = strokes.n * s
    x0, y0, x1, y1 = ( np.asarray( v, float ) * s for v in ( x0, y0, x1, y1 ) )
    count = len( x0 )
    sx, sy = np.floor( x0 / big ) * big, np.floor( y0 / big ) * big
    x0, x1, y0, y1 = x0 - sx, x1 - sx, y0 - sy, y1 - sy
    w = np.maximum( 1, np.rint( np.asarray( width, float ) * s ) ).astype( int ) * np.ones( count, int )
    pad = w + 2
    near = ( np.minimum( x0, x1 ) - pad < 0 ) | ( np.maximum( x0, x1 ) + pad > big ) \
        | ( np.minimum( y0, y1 ) - pad < 0 ) | ( np.maximum( y0, y1 ) + pad > big )
    cols = [ tuple( c ) for c in np.clip( np.rint( colour ), 0, 255 ).astype( int ).tolist() ]
    hs = np.clip( np.rint( np.asarray( height, float ) * 255 ), 0, 255 ).astype( int ) * np.ones( count, int )
    line_rgb, line_h, line_c = strokes.draw_rgb.line, strokes.draw_height.line, strokes.draw_cover.line
    shifts = [ ( ox, oy ) for ox in ( -big, 0, big ) for oy in ( -big, 0, big ) ]
    for a, b, c, d, wi, ci, hi, ni in zip( x0.tolist(), y0.tolist(), x1.tolist(), y1.tolist(), w.tolist(), cols,
                                           hs.tolist(), near.tolist() ):
        for ox, oy in ( shifts if ni else ( ( 0, 0 ), ) ):
            seg = [ ( a + ox, b + oy ), ( c + ox, d + oy ) ]
            line_rgb( seg, fill=ci, width=wi )
            line_h( seg, fill=hi, width=wi )
            line_c( seg, fill=255, width=wi )


@texture( "heather" )
def heather( rng, n ):
    """ Heather moor in October, 1 px an inch (a tile 43 ft across): ling, bush against bush in a dense, lumpy canopy
    a foot or so deep. Each bush is a dome of wiry shoots splaying out from its middle, their tips carrying the
    summer's flower spikes, faded now to rust and dull mauve, over dark green and bronze foliage, with grey-brown woody
    stems showing lower down; between the bushes, dark gaps over peat and moss with grey-green cushions of Cladonia,
    and a few pale stems of grass poking up through. Old stands are leggier and woodier, young ones lower and greener;
    those broad patches are kept weak. """
    p = n / 512.0
    age = smoothstep( -1.3, 1.3, noise( rng, n, 2.4, 2, 10 ) )
    damp = smoothstep( -0.2, 1.2, noise( rng, n, 2.0, 6, 50 ) )
    ground = mix( lum_paint( ( 36, 30, 24 ), 1.0 + 0.2 * noise( rng, n, 1.4, 20, None ) ),
                  lum_paint( ( 66, 70, 40 ), 1.0 + 0.2 * noise( rng, n, 1.4, 20, None ) ), 0.55 * damp )
    strokes = T.Strokes( ground, np.full( ( n, n ), 0.03 ), ss=3 )
    # Cladonia and grass low down among the stems: only the gaps show them.
    lichen = np.array( ( 150, 156, 136 ) )
    for _ in range( int( 300 * p * p ) ):
        x, y = rng.uniform( 0, n, 2 )
        r = rng.uniform( 0.6, 1.4 ) * p
        strokes.dot( x, y, r, r * rng.uniform( 0.7, 1.0 ), lichen * rng.uniform( 0.8, 1.1 ), 0.1 )
    count = int( 0.012 * n * n )
    a = rng.uniform( 0, 2 * np.pi, count )
    length = rng.uniform( 3, 7, count ) * p
    x0, y0 = rng.uniform( 0, n, ( 2, count ) )
    straw = mix( ( 112, 104, 66 ), ( 150, 132, 90 ), rng.random( count ) )
    _segments( strokes, x0, y0, x0 + np.cos( a ) * length, y0 + np.sin( a ) * length, rng.uniform( 0.5, 0.8, count ) * p,
               straw * rng.uniform( 0.6, 0.9, ( count, 1 ) ), rng.uniform( 0.05, 0.15, count ) )
    # The bushes.
    pts = jittered( rng, n, 15 * p, 0.5 )
    k = len( pts )
    ix, iy = pts[:, 0].astype( int ) % n, pts[:, 1].astype( int ) % n
    old = age[iy, ix]
    radius = rng.uniform( 7, 13, k ) * p * ( 0.88 + 0.24 * old )
    top = rng.uniform( 0.62, 0.95, k ) * ( 0.85 + 0.15 * old )
    purple = np.clip( rng.normal( 0.3, 0.3, k ), 0, 1 )
    green = np.clip( rng.normal( 0.25, 0.2, k ) + 0.3 * ( 1 - old ), 0, 1 )
    bright = rng.uniform( 0.76, 1.2, k )
    flowered = np.clip( rng.normal( 0.6, 0.25, k ) + 0.25 * old, 0.15, 1.2 )
    ph = rng.uniform( 0, 2 * np.pi, ( k, 2 ) )
    counts = np.maximum( 8, 2.3 * radius ** 2 ).astype( int )
    bush = np.repeat( np.arange( k ), counts )
    m = len( bush )
    u = np.sqrt( rng.random( m ) )
    ang = rng.uniform( 0, 2 * np.pi, m )
    lobe = 1.0 + 0.16 * np.sin( 3 * ang + ph[bush, 0] ) + 0.09 * np.sin( 5 * ang + ph[bush, 1] )
    rr = u * radius[bush] * lobe
    x0 = pts[bush, 0] + np.cos( ang ) * rr
    y0 = pts[bush, 1] + np.sin( ang ) * rr
    depth = np.sqrt( np.clip( 1 - u * u, 0, 1 ) ) ** 0.8 * ( 0.8 + 0.2 * rng.random( m ) )
    h = 0.08 + ( top[bush] - 0.08 ) * depth
    heading = ang + rng.normal( 0, 0.7, m )
    length = rng.uniform( 1.4, 3.0, m ) * p * ( 0.45 + 0.55 * u )
    x1 = x0 + np.cos( heading ) * length
    y1 = y0 + np.sin( heading ) * length
    width = rng.uniform( 0.7, 1.1, m ) * p
    woody, foliage, bronze = np.array( ( 80, 70, 66 ) ), np.array( ( 52, 60, 40 ) ), np.array( ( 74, 60, 58 ) )
    rust, mauve, faded = np.array( ( 128, 84, 62 ) ), np.array( ( 112, 76, 94 ) ), np.array( ( 142, 120, 102 ) )
    spike = rng.random( m ) < ( 0.12 + 0.6 * depth ** 1.6 ) * flowered[bush]
    wood = ~spike & ( rng.random( m ) < 0.45 * ( 1 - depth ) ** 1.5 + 0.15 * old[bush] * ( 1 - depth ) )
    pick = rng.random( m )
    spikes = np.where( ( pick < purple[bush] )[:, None], mauve, np.where( ( pick > 0.9 )[:, None], faded, rust ) )
    leaves = mix( bronze, foliage, green[bush] )
    col = np.where( spike[:, None], spikes, np.where( wood[:, None], woody, leaves ) )
    col = col * ( ( 0.5 + 0.55 * depth ) * rng.uniform( 0.85, 1.15, m ) * bright[bush] )[:, None]
    order = np.argsort( h, kind="stable" )
    _segments( strokes, x0[order], y0[order], x1[order], y1[order], width[order], col[order], h[order] )
    # A few long stems of grass up through it all.
    for _ in range( int( 420 * p * p ) ):
        x, y = rng.uniform( 0, n, 2 )
        pts_g = T.curve_points( x, y, rng.uniform( 0, 2 * math.pi ), rng.uniform( 4, 9 ) * p, rng.normal( 0, 0.4 ), 3 )
        c = np.array( ( 168, 150, 104 ) ) * rng.uniform( 0.8, 1.05 )
        strokes.blade( pts_g, [ 0.7 * p, 0.6 * p, 0.5 * p ], [ c * 0.85, c, c * 1.04 ], [ 0.9, 0.95, 0.92 ] )
    colour, h, cover = strokes.result()
    h = T.blur( h, 0.6 )
    occ = T.cavity_ao( h, ( ( 2.0, 2.0 ), ( 6.0, 1.4 ), ( 14.0, 0.8 ) ), 1.0 )
    colour = darken( colour, 0.62 + 0.38 * occ )
    rough = np.clip( 0.88 + 0.03 * noise( rng, n, 1.0, 40, None ) - 0.04 * h, 0, 1 )
    return { "sh_heather": colour }, rough, 10.0 * h, 1024 / 512


@texture( "bracken" )
def bracken( rng, n ):
    """ A bracken bed in October, 1 px an inch (a tile 43 ft across): the fronds gone russet, copper and orange, a few
    still yellowish or bleached, held out flat 2-4 ft up in overlapping layers. Each frond is a broad triangle of
    pinnae either side of its pale stem, angled towards its tip, the lowest pair the longest; the lower layers are
    older, darker and collapsing, and between them are glimpses of last year's litter, dark brown, with dead stems
    lying every way. """
    p = n / 512.0
    ground = lum_paint( ( 58, 40, 26 ), 1.0 + 0.2 * noise( rng, n, 1.6, 10, None ) )
    strokes = T.Strokes( ground, np.full( ( n, n ), 0.02 ), ss=3 )
    count = int( 0.004 * n * n )
    a = rng.uniform( 0, 2 * np.pi, count )
    length = rng.uniform( 6, 20, count ) * p
    x0, y0 = rng.uniform( 0, n, ( 2, count ) )
    litter = mix( ( 92, 62, 38 ), ( 124, 94, 60 ), rng.random( count ) ) * rng.uniform( 0.6, 1.0, ( count, 1 ) )
    _segments( strokes, x0, y0, x0 + np.cos( a ) * length, y0 + np.sin( a ) * length, rng.uniform( 0.8, 1.6, count ) * p,
               litter, rng.uniform( 0.04, 0.14, count ) )
    palette = [ ( 4, ( 168, 100, 44 ) ), ( 4, ( 150, 86, 40 ) ), ( 2, ( 176, 116, 52 ) ), ( 2, ( 156, 118, 68 ) ),
                ( 0.5, ( 132, 114, 62 ) ), ( 1, ( 120, 72, 38 ) ), ( 0.6, ( 162, 128, 86 ) ) ]
    old_palette = [ ( 3, ( 120, 72, 38 ) ), ( 3, ( 134, 80, 40 ) ), ( 2, ( 108, 74, 46 ) ), ( 1, ( 150, 86, 40 ) ) ]
    xs0, ys0, xs1, ys1, ws, cs, hs = [], [], [], [], [], [], []

    def add( x0, y0, x1, y1, w, c, h ):
        xs0.append( x0 ), ys0.append( y0 ), xs1.append( x1 ), ys1.append( y1 )
        ws.append( w ), cs.append( c ), hs.append( h )

    def frond( x, y, theta, L, colour, h0, midribs ):
        bend = rng.normal( 0, 0.25 )
        ts = np.linspace( 0, 1, 9 )
        steps = theta + bend * ( ts[:-1] + 1 / 16 )
        rx = x + np.concatenate( [ [ 0.0 ], np.cumsum( np.cos( steps ) * L / 8 ) ] )
        ry = y + np.concatenate( [ [ 0.0 ], np.cumsum( np.sin( steps ) * L / 8 ) ] )
        m = int( rng.integers( 11, 15 ) )
        tj = 0.06 + 0.9 * np.arange( m ) / m
        bx, by = np.interp( tj, ts, rx ), np.interp( tj, ts, ry )
        lj = L * ( 0.04 + 0.4 * ( 1 - tj ) ** 0.9 ) * rng.uniform( 0.85, 1.12, m )
        w0 = np.clip( 0.26 * lj, 0.8 * p, 4.2 * p )
        for side in ( -1, 1 ):
            a0 = theta + bend * tj + side * np.radians( rng.uniform( 50, 62, m ) )
            curl = -side * np.radians( rng.uniform( 5, 20, m ) )
            shade = rng.uniform( 0.88, 1.1, m ) * ( 0.94 + 0.12 * tj )
            px, py = bx.copy(), by.copy()
            rib = []
            for q, lobe in enumerate( ( 1.0, 0.8, 0.9, 0.6 ) ):
                t = ( q + 0.5 ) / 4
                ang = a0 + curl * t
                nx, ny = px + np.cos( ang ) * lj / 4, py + np.sin( ang ) * lj / 4
                add( px, py, nx, ny, w0 * lobe * ( 1 - 0.6 * t ), colour * ( shade * ( 1 + 0.08 * t ) )[:, None],
                     np.full( m, h0 + 0.06 * ( 1 - t ) ) )
                rib.append( ( px, py, nx, ny ) )
                px, py = nx, ny
            if midribs:
                for q, ( ax, ay, cx_, cy_ ) in enumerate( rib[:3] ):
                    add( ax, ay, cx_, cy_, np.full( m, 0.45 * p ), colour * ( shade * 1.14 )[:, None],
                         np.full( m, h0 + 0.065 ) )
        add( rx[:-1], ry[:-1], rx[1:], ry[1:], np.linspace( 1.2, 0.6, 8 ) * p,
             np.tile( np.array( ( 150, 112, 64 ) ) * ( colour.mean() / 120.0 ), ( 8, 1 ) ), np.full( 8, h0 + 0.07 ) )

    total = int( 0.0105 * n * n )
    for share, h0, shade_range, size, pal, midribs in ( ( 0.35, 0.18, ( 0.5, 0.66 ), ( 16, 30 ), old_palette, False ),
                                                        ( 0.35, 0.5, ( 0.72, 0.88 ), ( 20, 34 ), palette, False ),
                                                        ( 0.30, 0.82, ( 0.92, 1.1 ), ( 22, 36 ), palette, True ) ):
        cnt = int( total * share )
        colours = T.pick( rng, pal, cnt ) * rng.uniform( *shade_range, ( cnt, 1 ) )
        for i in range( cnt ):
            frond( rng.uniform( 0, n ), rng.uniform( 0, n ), rng.uniform( 0, 2 * math.pi ),
                   rng.uniform( *size ) * p, colours[i], h0 + rng.uniform( 0, 0.1 ), midribs )
    _segments( strokes, np.concatenate( xs0 ), np.concatenate( ys0 ), np.concatenate( xs1 ), np.concatenate( ys1 ),
               np.concatenate( ws ), np.concatenate( cs ), np.concatenate( hs ) )
    colour, h, cover = strokes.result()
    h = T.blur( h, 0.6 )
    occ = T.cavity_ao( h, ( ( 2.0, 2.0 ), ( 6.0, 1.2 ) ), 1.0 )
    colour = darken( colour, 0.72 + 0.28 * occ )
    rough = np.clip( 0.86 + 0.03 * noise( rng, n, 1.0, 40, None ) + 0.04 * ( 1 - cover ), 0, 1 )
    return { "sh_bracken": colour }, rough, 10.0 * h, 1024 / 512


@texture( "hill_rock" )
def hill_rock( rng, n ):
    """ Grey crags and slabs on the hills (gneiss), 1 px an inch (a tile 43 ft across): blocks between joints a few
    feet apart, weathered round, banded, and nearly all grown over with lichens (grey-white crusts merging into big
    pale patches, grey-green leafy rosettes, yellow-green map lichen with its black rims, black spots), which is what
    makes hill rock pale from afar; dark streaks where water seeps from the joints. Peaty soil gathers in the wider
    joints and on ledges, under moss, tawny grass and heather. """
    p = n / 384.0
    height, block, count, bands, fractures, joint = _rock_relief( rng, n, p )
    height = 2.4 * height
    cav, tops = cavities( height, 3.0 * p )
    hollow, _ = cavities( height, 12.0 * p )
    tone = BT.tones( rng, [ ( 124, 124, 121 ), ( 116, 117, 116 ), ( 130, 127, 122 ), ( 110, 112, 112 ),
                            ( 98, 100, 100 ) ], count, 0.06 )
    mottle = noise( rng, n, 1.8, 4, 120 )
    fine = noise( rng, n, 1.0, n / 5 )
    grain = grain_field( rng, n, 0.5, 4.0 )
    c = BT.shade( tone[block], 1.0 + 0.08 * mottle + 0.07 * bands + 0.06 * fine )
    c = mix( c, ( 148, 138, 130 ), 0.25 * smoothstep( 0.5, 1.3, bands ) )
    c = mix( c, ( 76, 78, 76 ), 0.35 * smoothstep( -0.5, -1.3, bands ) )
    c = mix( c, ( 52, 52, 50 ), 0.3 * smoothstep( 1.4, 2.4, grain ) )
    veins = crack_lines( rng, n, 3, ( 40 * p, 120 * p ), 1.5 * p, branch=0.1, turn=0.04, pull=0.6 )
    veins = veins * smoothstep( -0.4, 0.5, noise( rng, n, 2.0, 4, 30 ) )
    c = mix( c, ( 196, 194, 186 ), 0.5 * veins )
    open_rock = 1 - smoothstep( 0.15, 0.5, joint )
    tex = noise( rng, n, 1.2, 20, n / 3 )
    patches = smoothstep( -1.0, 0.6, noise( rng, n, 2.4, 1, 6 ) + 0.35 * noise( rng, n, 2.0, 6, 30 ) ) * open_rock
    c, grey = _lichen( c, rng, n, 1700, ( 1.5 * p, 8 * p ), patches, ( 172, 174, 168 ), 0.7, texture=tex )
    c, _ = _lichen( c, rng, n, 240, ( 1.5 * p, 4.5 * p ), 0.5 * open_rock, ( 136, 146, 128 ), 0.8, texture=tex,
                    lobes=0.28 )
    tops_f = smoothstep( -0.3, 1.2, tops * 2 / 2.4 + 0.3 * noise( rng, n, 2.0, 2, 20 ) ) * open_rock
    c, mapl = _lichen( c, rng, n, 260, ( 0.7 * p, 3.0 * p ), 0.6 * tops_f, ( 168, 174, 96 ), 0.8, rim=0.8,
                       texture=tex, lobes=0.1 )
    c, _ = _lichen( c, rng, n, 500, ( 0.3 * p, 1.0 * p ), 0.5 * open_rock, ( 54, 54, 50 ), 0.8, lobes=0.08 )
    seeps = wash_down( np.clip( fractures + joint, 0, 1 ) * smoothstep( 0.3, 1.3, noise( rng, n, 1.6, 4, 40 ) ),
                       18 * p, 1.0, rng )
    c = mix( c, ( 56, 58, 56 ), 0.3 * seeps * open_rock )
    c = darken( c, ( 1.0 - 0.3 * fractures ) * np.exp( -0.25 * cav - 0.15 * hollow ) )
    # Soil in the wider joints and on ledges: moss and bare peat, then grass and heather over it.
    jw = T.blur( joint, 2.0 * p )
    jw = jw / max( jw.max(), 1e-6 )
    along = smoothstep( -1.0, 1.0, noise( rng, n, 2.0, 3, 24 ) )
    in_joints = smoothstep( 0.2, 0.5, jw * ( 0.45 + 0.9 * along ) )
    ledges = smoothstep( 1.2, 1.8, noise( rng, n, 2.4, 2, 12 ) + 1.0 * jw + 0.3 * noise( rng, n, 1.6, 12, 60 ) )
    soil = np.maximum( in_joints, ledges )
    kind = noise( rng, n, 2.0, 4, 40 )
    tawny = noise( rng, n, 2.0, 3, 20 )
    ground = mix( lum_paint( ( 44, 38, 30 ), 1.0 + 0.2 * fine ),
                  mix( flat( n, ( 54, 64, 34 ) ), ( 80, 88, 46 ), smoothstep( -1, 1, fine ) ),
                  smoothstep( -0.8, 0.4, -kind + 0.3 * mottle ) )
    c = mix( c, ground, smoothstep( 0.15, 0.5, soil ) )
    strokes = T.Strokes( c, np.clip( 0.3 + 0.25 * soil, 0, 1 ), ss=3 )
    m = int( 1.8 * soil.sum() )
    at = rng.choice( n * n, size=m, p=( soil / soil.sum() ).ravel() )
    yy, xx = np.divmod( at, n )
    x0, y0 = xx + rng.random( m ), yy + rng.random( m )
    s_at, k_at, t_at = soil.ravel()[at], kind.ravel()[at], tawny.ravel()[at]
    is_heather = rng.random( m ) < 0.15 + 0.75 * smoothstep( -0.6, 0.8, k_at )
    grass_cols = np.array( [ ( 76, 92, 44 ), ( 96, 100, 56 ), ( 132, 118, 80 ), ( 146, 134, 96 ), ( 112, 98, 70 ) ],
                           float )
    g_pick = np.clip( ( rng.random( m ) * 3 + 2.0 * smoothstep( -1.0, 1.0, t_at ) ).astype( int ), 0, 4 )
    heather_cols = np.array( [ ( 76, 60, 54 ), ( 96, 70, 74 ), ( 60, 64, 42 ), ( 118, 84, 64 ) ], float )
    h_pick = np.searchsorted( np.cumsum( [ 0.45, 0.25, 0.2, 0.1 ] ), rng.random( m ) )
    col = np.where( is_heather[:, None], heather_cols[np.minimum( h_pick, 3 )], grass_cols[g_pick] )
    col = col * rng.uniform( 0.78, 1.14, ( m, 1 ) )
    length = np.where( is_heather, rng.uniform( 1.2, 2.5, m ), rng.uniform( 2.0, 5.0, m ) ) * p
    ang = rng.uniform( 0, 2 * np.pi, m )
    lift = np.where( is_heather, 0.6 + 0.3 * rng.random( m ), 0.4 + 0.45 * rng.random( m ) ) * ( 0.6 + 0.4 * s_at )
    order = np.argsort( lift )
    _segments( strokes, x0[order], y0[order], ( x0 + np.cos( ang ) * length )[order],
               ( y0 + np.sin( ang ) * length )[order], np.where( is_heather, 0.9 * p, 0.7 * p )[order],
               col[order], lift[order] )
    c, h_s, cov_s = strokes.result()
    occ = T.cavity_ao( h_s, ( ( 2.0, 2.0 ), ( 6.0, 1.2 ) ), 1.0 )
    plants = cov_s * smoothstep( 0.1, 0.5, soil )
    c = darken( c, 1.0 - plants * ( 0.3 - 0.3 * occ ) )
    sm = smoothstep( 0.15, 0.5, soil )
    turf = T.blur( height, 6.0 * p ) + 0.5 + 4.0 * h_s
    height = height * ( 1 - sm ) + np.maximum( height, turf ) * sm
    rough = np.clip( 0.8 + 0.04 * mottle + 0.08 * grey - 0.1 * veins - 0.08 * seeps + 0.12 * sm, 0, 1 )
    return { "sh_hill_rock": c }, rough, height, 1024 / 512


@texture( "conifer" )
def conifer( rng, n ):
    """ A Sitka spruce plantation's canopy, 1 px an inch (a tile 43 ft across: six rows of trees about 7 ft apart, as
    planted, a few gone in the thinning, their neighbours' crowns spread into the gaps). Each crown is a steep cone of
    drooping branches in whorls, a different number in each, blue-green and lit at the shoots' tips, with its leader at
    the top; it darkens down its sides, to near black where the crowns meet. For the plantations on the hills behind,
    seen from afar, so the shading is all in the colour and the cones' slopes, with no sun of its own. """
    k = 6
    step = n / k
    gy, gx = np.mgrid[0:k, 0:k]
    centres = np.stack( [ ( gx + 0.5 ) * step, ( gy + 0.5 ) * step ], -1 ).reshape( -1, 2 ).astype( float )
    centres[:, 0] += rng.normal( 0, 0.2 * step, len( centres ) )
    centres[:, 1] += rng.normal( 0, 0.1 * step, len( centres ) ) + 0.12 * step * np.sin( 2 * np.pi * centres[:, 0] / n
                                                                                        + rng.uniform( 0, 6.3 ) )
    centres = centres[rng.random( len( centres ) ) > 0.12] % n
    count = len( centres )
    tree = cKDTree( centres, boxsize=n )
    near_d, _ = tree.query( centres, k=4 )
    room = np.clip( near_d[:, 1:].mean( 1 ) / step, 0.8, 1.5 )
    R = step * rng.uniform( 0.6, 0.78, count ) * room
    top = rng.uniform( 0.8, 1.0, count ) * ( 0.9 + 0.1 * room )
    x, y = coords( n )
    q = np.stack( [ x.ravel(), y.ravel() ], -1 )
    dist, idx = tree.query( q, k=6, workers=-1 )
    cone = top[idx] - dist / R[idx]
    rows = np.arange( len( q ) )
    best = np.argmax( cone, 1 )
    t = idx[rows, best].reshape( n, n )
    canopy = cone[rows, best].reshape( n, n )
    second = np.sort( cone, 1 )[:, -2].reshape( n, n )
    d = dist[rows, best].reshape( n, n ) / R[t]
    off = ( q - centres[idx[rows, best]] + n / 2 ) % n - n / 2
    theta = np.arctan2( off[:, 1], off[:, 0] ).reshape( n, n )
    # Whorls: rings out from the top, each with its own number of branches at its own turn.
    nt = 7
    tier_f = d * nt + 0.15 * noise( rng, n, 2.0, 8, 60 )
    ti = np.clip( np.floor( tier_f ), 0, nt + 4 ).astype( int )
    frac = tier_f - np.floor( tier_f )
    branches = rng.integers( 5, 9, ( count, nt + 5 ) )
    turn = rng.uniform( 0, 2 * np.pi, ( count, nt + 5 ) )
    spoke = np.cos( branches[t, ti] * theta - turn[t, ti] )
    shoots = noise( rng, n, 1.3, 30, n / 3 )
    needles = noise( rng, n, 1.0, n / 6 )
    width = 0.55 - 0.45 * np.clip( d, 0, 1 )
    branch = smoothstep( width - 0.35, width + 0.25, spoke + 0.35 * shoots ) * smoothstep( 0.0, 0.1, d )
    # The tips of each whorl's branches stand out over the whorl below: lit there, dark under the next whorl up.
    lit = branch * smoothstep( 0.05, 0.9, frac )
    light = smoothstep( -0.25, 0.85, canopy ) * ( 0.55 + 0.45 * smoothstep( 0.0, 0.3, canopy - second ) )
    dark, mid, sunlit, tips = ( 12, 18, 13 ), ( 30, 48, 32 ), ( 56, 80, 52 ), ( 70, 92, 78 )
    c = mix( flat( n, dark ), mid, light * ( 0.45 + 0.55 * branch ) )
    c = mix( c, sunlit, lit * light )
    c = mix( c, tips, 0.6 * smoothstep( 0.75, 1.0, frac ) * branch * light )
    c = mix( c, ( 62, 84, 60 ), 0.7 * smoothstep( 0.08, 0.02, d ) )
    tone = rng.uniform( 0.86, 1.14, count )
    blue = np.clip( rng.normal( 0, 0.5, count ), 0, 1 )
    c = lum_paint( c, tone[t] * ( 1.0 + 0.2 * needles * branch + 0.06 * shoots ) )
    c = tinted( c, ( 40, 62, 60 ), 0.15 * blue[t] )
    h = canopy + 0.04 * lit - 0.03 * ( 1 - branch )
    h_in = 30.0 * h + 0.6 * needles * branch
    rough = np.clip( 0.84 + 0.06 * ( 1 - branch ) + 0.03 * needles, 0, 1 )
    return { "sh_conifer": c }, rough, h_in, 1024 / 512


@texture( "far_hills" )
def far_hills( rng, n ):
    """ The far hills, 4 in a px (a tile 171 ft across), seen through miles of autumn air: a soft mosaic of heather,
    grazing, bracken and wet moor, with grey crags and screes, its colours hazed towards the sky's blue-grey. Nothing
    runs one way (no gullies or streaks), so it reads the same however it's laid; the broad patches are kept weak, so
    the tile doesn't show as a grid from afar, and most of its variation is in patches a few yards across. The relief
    is gentle: from that far off the normals should only just break the light up. """
    def field( beta, fmin, fmax ):
        return noise( rng, n, beta, fmin, fmax )
    def weight( bias, gain ):
        return np.exp( gain * ( 0.35 * field( 2.0, 2, 6 ) + field( 2.2, 6, 30 ) + bias ) )
    w = [ weight( 0.3, 1.6 ), weight( 0.0, 1.6 ), weight( -0.3, 1.6 ), weight( -1.0, 2.2 ) ]
    total = sum( w )
    speck = field( 1.3, 30, None )
    clumps = field( 2.0, 10, 80 )
    lands = [ ( ( 74, 58, 54 ), 0.18 ), ( ( 92, 104, 58 ), 0.1 ), ( ( 96, 86, 60 ), 0.12 ), ( ( 132, 84, 44 ), 0.12 ) ]
    c = sum( lum_paint( rgb, 1.0 + amount * speck + 0.08 * clumps ) * ( wk / total )[..., None]
             for ( rgb, amount ), wk in zip( lands, w ) )
    # Crags and screes: small grey patches, pale with lichen, dark in their clefts.
    crag_f = field( 2.2, 6, 40 ) + 0.4 * field( 1.6, 30, 120 )
    crag = smoothstep( 1.8, 2.4, crag_f )
    scree = smoothstep( 1.4, 2.0, crag_f ) * ( 1 - crag ) * smoothstep( 0.0, 1.0, field( 2.0, 4, 30 ) )
    c = mix( c, lum_paint( ( 124, 124, 120 ), 1.0 + 0.2 * speck + 0.12 * field( 1.6, 20, 120 ) ), 0.85 * crag )
    c = mix( c, lum_paint( ( 106, 106, 102 ), 1.0 + 0.25 * speck ), 0.5 * scree )
    cleft = smoothstep( 0.6, 1.6, field( 1.4, 30, 160 ) ) * crag
    c = darken( c, 1.0 - 0.4 * cleft )
    # The air between: the far hills take the sky's colour.
    c = mix( c, ( 120, 130, 154 ), 0.5 )
    h_in = 2.0 * clumps + 0.7 * speck * ( 1 - crag ) + 8.0 * crag + 3.0 * scree
    rough = np.clip( 0.9 - 0.08 * crag + 0.03 * speck, 0, 1 )
    return { "sh_far_hills": c }, rough, h_in, 1024 / 2048


# ---------------------------------------------------------------------------------------------------------------------
# The atlases' pictures

class Sheet:
    """ A picture drawn ss times over and shrunk, so its shapes' edges come out antialiased: an RGB colour and float
    layers (masks), each shape setting the colour and whichever layers it names. PIL draws on float layers without
    antialiasing (text too), so the shrink is what smooths their edges. Coordinates are the picture's px. """

    def __init__( self, w, h, background, ss=4, **layers ):
        self.w, self.h, self.ss = w, h, ss
        size = ( w * ss, h * ss )
        self.colour = Image.new( "RGB", size, tuple( int( round( v ) ) for v in background ) )
        self.layers = { k: Image.new( "F", size, float( v ) ) for k, v in layers.items() }
        self.draws = { "colour": ImageDraw.Draw( self.colour ) }
        self.draws.update( { k: ImageDraw.Draw( im ) for k, im in self.layers.items() } )

    def _each( self, fill, layers ):
        if fill is not None:
            yield self.draws["colour"], tuple( int( round( v ) ) for v in fill )
        for k, v in ( layers or {} ).items():
            yield self.draws[k], float( v )

    def _s( self, points ):
        return [ ( x * self.ss, y * self.ss ) for x, y in points ]

    def _w( self, width ):
        return max( 1, int( round( width * self.ss ) ) )

    def rectangle( self, xy, fill=None, layers=None, radius=0.0, outline=None, width=0.0 ):
        """ A (rounded) rectangle, filled, or with outline only its border, width px wide. """
        s = self.ss
        box = ( xy[0] * s, xy[1] * s, xy[2] * s - 1, xy[3] * s - 1 )
        if outline is None:
            for d, f in self._each( fill, layers ):
                d.rounded_rectangle( box, radius=radius * s, fill=f )
        else:
            for d, f in self._each( outline, layers ):
                d.rounded_rectangle( box, radius=radius * s, outline=f, width=self._w( width ) )

    def polygon( self, points, fill=None, layers=None ):
        for d, f in self._each( fill, layers ):
            d.polygon( self._s( points ), fill=f )

    def ellipse( self, xy, fill=None, layers=None, outline=None, width=0.0 ):
        box = tuple( v * self.ss for v in xy )
        if outline is None:
            for d, f in self._each( fill, layers ):
                d.ellipse( box, fill=f )
        else:
            for d, f in self._each( outline, layers ):
                d.ellipse( box, outline=f, width=self._w( width ) )

    def dot( self, x, y, r, fill=None, layers=None ):
        self.ellipse( ( x - r, y - r, x + r, y + r ), fill, layers )

    def line( self, points, fill=None, width=1.0, layers=None, joint="curve", round_caps=False ):
        for d, f in self._each( fill, layers ):
            d.line( self._s( points ), fill=f, width=self._w( width ), joint=joint )
        if round_caps:
            for x, y in ( points[0], points[-1] ):
                self.dot( x, y, width / 2, fill, layers )

    def text( self, xy, s, face, cap, fill=None, layers=None, anchor="ls", tracking=0.0, width=None, middle=False ):
        """ s with capitals cap px high (smaller if it would run wider than width); tracking is a share of the cap
        height; with middle, xy's y is the middle of the capitals as drawn rather than their baseline. Returns its
        width in px. """
        k = self.ss
        if width is not None:
            f, c = fitted( face, s, cap * k, width * k, tracking )
        else:
            f, c = sized( face, cap * k ), cap * k
        y = xy[1] * k + ( c / 2 if middle else 0.0 )
        for d, fl in self._each( fill, layers ):
            put( d, ( xy[0] * k, y ), s, f, fl, anchor, tracking * c )
        return text_width( s, f, tracking * c ) / k

    def arrays( self ):
        colour = np.asarray( self.colour.reduce( self.ss ), float )
        return colour, { k: np.asarray( im.reduce( self.ss ), float ) for k, im in self.layers.items() }


class _Fields:
    """ Noise for a picture up to 1024 px across, cut from 1024 px tiles (f in cycles a tile). """
    N = 1024

    def __init__( self, rng, w, h ):
        self.rng, self.w, self.h = rng, w, h

    def noise( self, beta, fmin, fmax=None ):
        return noise( self.rng, self.N, beta, fmin, fmax )[:self.h, :self.w]

    def down( self, beta, fmin, fmax, rows, cols=0.5 ):
        """ Streaks down the picture (runs). """
        return streaks( self.rng, self.N, beta, fmin, fmax, rows, cols )[:self.h, :self.w]

    def across( self, beta, fmin, fmax, cols, rows=0.5 ):
        """ Streaks across the picture (grain, brush strokes along a board). """
        return streaks( self.rng, self.N, beta, fmin, fmax, cols, rows ).T[:self.h, :self.w]

    def grit( self, sigma=0.6, power=5.0 ):
        return grain_field( self.rng, self.N, sigma, power )[:self.h, :self.w]

    def spots( self, count, radius, profile="dome", soft=0.8 ):
        """ count dots (radius px, a range) over the whole 1024 px tile, so about count * w * h / 1024^2 here. """
        return dots( self.rng, self.N, count, radius, profile, soft )[:self.h, :self.w]


def _soft( a, sigma ):
    """ A blur that doesn't wrap, for pictures that don't tile. """
    return ndimage.gaussian_filter( a, sigma, mode="nearest" )


def _trickle( src, length ):
    """ src run down the picture, fading by e every length px: each px the most of itself and the px above it, decayed,
    so every spot leaves its own run (none add up). Doesn't wrap. """
    a = math.exp( -1.0 / max( length, 1e-3 ) )
    out = np.array( src, float )
    for r in range( 1, out.shape[0] ):
        np.maximum( out[r], a * out[r - 1], out=out[r] )
    return out


def _warp( arrays, dx, dy ):
    """ Each array (2-D, or with colour channels last) resampled at ( x + dx, y + dy ): edges that waver, as a brush
    leaves them. """
    h, w = dx.shape
    yy, xx = np.mgrid[0:h, 0:w].astype( float )
    at = [ yy + dy, xx + dx ]
    out = []
    for a in arrays:
        if a.ndim == 3:
            out.append( np.stack( [ ndimage.map_coordinates( a[..., k], at, order=1, mode="nearest" )
                                    for k in range( a.shape[2] ) ], -1 ) )
        else:
            out.append( ndimage.map_coordinates( a, at, order=1, mode="nearest" ) )
    return out


def _inside( mask ):
    """ px from each px of mask (over 0.5) to its edge, 0 outside it. """
    return ndimage.distance_transform_edt( mask > 0.5 )


def _smooth_closed( points, steps=8 ):
    """ A closed Catmull-Rom curve through points. """
    p = np.asarray( points, float )
    m = len( p )
    out = []
    for i in range( m ):
        p0, p1, p2, p3 = p[( i - 1 ) % m], p[i], p[( i + 1 ) % m], p[( i + 2 ) % m]
        for t in np.linspace( 0.0, 1.0, steps, endpoint=False ):
            out.append( 0.5 * ( 2 * p1 + ( p2 - p0 ) * t + ( 2 * p0 - 5 * p1 + 4 * p2 - p3 ) * t * t
                                + ( 3 * p1 - p0 - 3 * p2 + p3 ) * t * t * t ) )
    return [ ( float( q[0] ), float( q[1] ) ) for q in out ]


def _closed( mask, r ):
    """ mask closed by a disc of radius r px (its inside corners filled round), by distance transforms. """
    grown = ndimage.distance_transform_edt( ~mask ) <= r
    return ndimage.distance_transform_edt( grown ) > r


def _padded( rough, height, weight ):
    """ rough and height carried out over where weight is 0 (the atlas's gutters), so their mips and the normals at
    an entry's edge don't take in the gutter. """
    out = _push_pull( np.stack( [ rough, height, np.zeros_like( height ) ], -1 ), weight )
    return out[..., 0], out[..., 1]


def _rects_mask( n, rects ):
    m = np.zeros( ( n, n ) )
    for x0, y0, x1, y1 in rects.values():
        m[y0:y1, x0:x1] = 1.0
    return m


# ---------------------------------------------------------------------------------------------------------------------
# sh_lettering

def _word_distance( name, k=4 ):
    """ A lettering entry's signed distance to its letters' edges (px, positive inside) over its rectangle: its word in
    LETTERING_FACE, capitals LETTERING_CAP px high on its baseline, drawn k times over and centred across the
    rectangle by its ink. """
    x0, y0, x1, y1 = LETTERING_RECTS[name]
    w, h = x1 - x0, y1 - y0
    img = Image.new( "L", ( w * k, h * k ), 0 )
    put( ImageDraw.Draw( img ), ( w * k / 2, LETTERING_BASELINE[name] * k ), LETTERING_WORDS[name],
         sized( LETTERING_FACE, LETTERING_CAP * k ), 255, "ms", LETTERING_TRACKING * LETTERING_CAP * k )
    ink = np.asarray( img ) >= 128
    cols = np.nonzero( ink.any( 0 ) )[0]
    ink = np.roll( ink, int( round( ( w * k - cols[0] - cols[-1] - 1 ) / 2 ) ), axis=1 )
    rows, cols = np.nonzero( ink.any( 1 ) )[0], np.nonzero( ink.any( 0 ) )[0]
    assert cols[0] >= 6 * k and cols[-1] < ( w - 6 ) * k and rows[0] >= 3 * k and rows[-1] < ( h - 3 ) * k, \
        ( name, rows[0] / k, rows[-1] / k, cols[0] / k, cols[-1] / k )
    sd = np.where( ink, ndimage.distance_transform_edt( ink ) - 0.5, 0.5 - ndimage.distance_transform_edt( ~ink ) )
    return sd.reshape( h, k, w, k ).mean( ( 1, 3 ) ) / k


@texture( "lettering" )
def lettering( rng, n ):
    """ sh_lettering: the names painted on the walls in black and the boats' names and numbers in white, each in its
    LETTERING_RECTS entry on a transparent ground (alpha tested).

    The walls' are a sign-writer's black masonry paint over the harl. Their edges are ragged where the brush caught
    the harl's grit and skipped its pits, and the paint lies in the harl's relief, drawn to each entry's size
    (LETTERING_CAP_INCHES). Each letter is a little different where it was touched up; the paint is faded chalky in
    broad patches and worn grey on the harl's tops, with the odd pit the brush missed (the wall shows through) and
    faint runs of limewash from above.

    The boats' are white gloss over the hull, brushed along the letters, chipped at their edges where the hull shows
    through, with grime along their feet and, on MAIRI ROS, rust run down from the fittings above. """
    colour = np.zeros( ( n, n, 3 ) )
    alpha = np.zeros( ( n, n ) )
    rough = np.full( ( n, n ), 0.75 )
    height = np.zeros( ( n, n ) )
    fine = noise( rng, n, 1.0, n / 10 )
    mottle = noise( rng, n, 2.4, 4, 80 )
    patches = noise( rng, n, 3.0, 2, 24 )
    lime_runs = smoothstep( 1.7, 3.0, streaks( rng, n, 1.3, 6, 300, 30, 0.5 ) )
    brush = streaks( rng, n, 1.0, 20, 600, 14, 0.4 ).T
    chip_f = noise( rng, n, 1.6, 40, 420 )
    rust_breaks = streaks( rng, n, 1.5, 4, 160, 30, 0.6 )
    reliefs = {}
    for name, ( x0, y0, x1, y1 ) in LETTERING_RECTS.items():
        sl = np.s_[y0:y1, x0:x1]
        hh, ww = y1 - y0, x1 - x0
        sd = _word_distance( name )
        p = LETTERING_CAP / LETTERING_CAP_INCHES[name]          # px an inch
        scale = p / LETTERING_PPI                                # an inch of relief, as drawn
        if name not in LETTERING_WHITE:
            if p not in reliefs:
                # The harl's grit comes a px across; blurred to its real size (as the harl's 4 px an inch draws it),
                # so the bigger the px an inch, the coarser it is in px.
                relief, grit = _harl_relief( rng, n, n / p )
                coarse = T.blur( grit, 0.3 * p / 4.0 )
                relief = relief + 0.035 * ( unit( coarse ) * grit.std() - grit )
                cav, tops = cavities( relief, 0.4 * p )
                edge = unit( 0.6 * unit( tops - cav ) + 0.4 * unit( T.blur( fine, 0.15 * p ) ) )
                reliefs[p] = ( relief, cav / ( cav.std() + 1e-9 ), tops / ( tops.std() + 1e-9 ), edge )
            relief, cav, tops, edge = ( a[sl] for a in reliefs[p] )
            # The brush cut in along the letters' edges: ragged by a millimetre or two where it caught the harl's
            # stones or skipped its hollows, not more.
            amp = 0.3 + 0.05 * p
            cov = np.clip( sd + amp * edge + 0.5, 0, 1 )
            # Pits the brush skipped show the wall.
            deep = np.quantile( cav[sd > 0], 0.985 )
            cov *= 1 - smoothstep( deep, deep * 1.25, cav ) * ( fine[sl] > -0.3 )
            lab, count = ndimage.label( sd > -1.0 )
            per = rng.random( ( count + 1, 2 ) )
            base = mix( ( 21, 22, 24 ), ( 33, 33, 33 ), per[lab, 0] )
            fade = np.clip( 0.16 * per[lab, 1] + 0.42 * smoothstep( 0.4, 2.0, patches[sl] + 0.35 * mottle[sl] ), 0, 0.6 )
            c = mix( base, ( 80, 82, 84 ), fade )
            worn = smoothstep( 0.9, 2.6, tops ) * ( 0.3 + 0.7 * smoothstep( -0.5, 1.5, mottle[sl] ) )
            c = mix( c, ( 116, 116, 112 ), 0.42 * worn )
            c = darken( c, np.exp( -0.3 * cav ) )
            c = mix( c, ( 178, 178, 170 ), 0.3 * lime_runs[sl] )
            r = np.clip( 0.66 + 0.12 * fade + 0.12 * worn + 0.03 * fine[sl] + 0.1 * lime_runs[sl], 0, 1 )
            h = relief * scale
        else:
            cov = np.clip( sd + 0.25 * fine[sl] + 0.5, 0, 1 )
            # Chips, mostly at the edges, where the hull's paint shows.
            edge = smoothstep( 4.0, 0.5, sd ) * ( sd > -1.0 )
            chips = smoothstep( 2.25, 2.45, chip_f[sl] + 1.25 * edge )
            cov *= 1 - chips
            yy = np.arange( hh )[:, None] + np.zeros( ( 1, ww ) )
            base = LETTERING_BASELINE[name]
            feet = smoothstep( base - 40, base + 4, yy ) * smoothstep( -0.6, 1.4, mottle[sl] )
            c = lum_paint( ( 236, 236, 230 ), 1.0 + 0.016 * brush[sl] + 0.01 * fine[sl] )
            c = mix( c, ( 180, 178, 166 ), 0.32 * feet )
            if name == "boat_mairi_ros":
                # Rust from the fittings above, run down over the letters in soft streaks, each as wide as the
                # bolt head or cleat it came from.
                src = np.zeros( ( hh, ww ) )
                xs = np.arange( ww ) + 0.5
                for _ in range( int( rng.integers( 4, 6 ) ) ):
                    xr, half = rng.uniform( 40, ww - 40 ), rng.uniform( 3.0, 7.0 )
                    rows = int( rng.uniform( 4, 14 ) )
                    prof = np.clip( 1 - np.abs( xs - xr ) / half, 0, 1 ) ** 0.7 * rng.uniform( 0.5, 1.0 )
                    src[:rows] = np.maximum( src[:rows], prof[None, :] )
                runs = _soft( _trickle( src, rng.uniform( 50, 80 ) ), 2.0 )
                runs *= np.clip( 0.45 + 0.6 * rust_breaks[sl], 0, 1 )
                c = mix( c, ( 150, 92, 54 ), 0.45 * np.clip( runs, 0, 1 ) )
            r = np.clip( 0.34 + 0.08 * feet + 0.02 * brush[sl], 0, 1 )
            h = ( 0.004 * cov + 0.0006 * brush[sl] ) * scale
        colour[sl], alpha[sl], rough[sl], height[sl] = c, cov, r, h
    colour = _push_pull( colour, np.clip( alpha * 2.0, 0, 1 ) )
    return { "sh_lettering": colour }, rough, height, LETTERING_PPI * 1024 / n, { "trans": alpha }


# ---------------------------------------------------------------------------------------------------------------------
# sh_signs

SIGN_FACE = "Dinish-Bold"
SIGN_WHITE, SIGN_BLACK = ( 238, 238, 232 ), ( 24, 24, 26 )
SIGN_RED, SIGN_GREEN, SIGN_YELLOW = ( 200, 30, 40 ), ( 0, 128, 80 ), ( 246, 194, 0 )
SIGN_TEAL, SIGN_CREAM = ( 24, 70, 64 ), ( 232, 222, 190 )
SIGN_SIGNAL_RED = ( 186, 34, 34 )                        # sign-writer's red, on the boards
INK, RED, CLEAR = { "ink": 1.0, "red": 0.0 }, { "ink": 1.0, "red": 1.0 }, { "ink": 0.0, "red": 0.0 }
# The still house's vessels' labels: ( name, a tuple for two lines ), detail.
VESSEL_LABELS = {
    "wash_charger": ( "WASH CHARGER", "No. 1      CAPACITY 20,000 LITRES" ),
    "low_wines": ( "LOW WINES RECEIVER", "No. 1      CAPACITY 12,000 LITRES" ),
    "feints": ( "FEINTS RECEIVER", "No. 1      CAPACITY 10,000 LITRES" ),
    "spirit_receiver": ( "SPIRIT RECEIVER", "No. 1      CAPACITY 8,000 LITRES" ),
    "intermediate": ( ( "INTERMEDIATE", "SPIRIT RECEIVER" ), "No. 1      CAPACITY 6,000 LITRES" ),
}
# px an inch where a sign isn't at SIGN_PPI: the flammable label is a 250 mm diamond on stillhouse_props' 13.9 in quad.
SIGN_OWN_PPI = { "flammable": 400 / 13.9 }
# The flame of the flammable label (x right, y up, its base at 0, about 1.2 tall).
FLAME = [ ( 0.0, 0.0 ), ( 0.22, 0.02 ), ( 0.36, 0.1 ), ( 0.44, 0.24 ), ( 0.46, 0.4 ), ( 0.42, 0.56 ), ( 0.34, 0.7 ),
          ( 0.36, 0.84 ), ( 0.3, 0.98 ), ( 0.26, 0.86 ), ( 0.2, 0.76 ), ( 0.18, 0.92 ), ( 0.1, 1.08 ), ( 0.02, 1.22 ),
          ( -0.04, 1.08 ), ( -0.1, 0.94 ), ( -0.16, 0.8 ), ( -0.22, 0.9 ), ( -0.3, 0.98 ), ( -0.36, 0.86 ),
          ( -0.42, 0.7 ), ( -0.46, 0.52 ), ( -0.46, 0.34 ), ( -0.42, 0.18 ), ( -0.32, 0.07 ), ( -0.18, 0.01 ) ]


def _corners( w, h, inset ):
    return [ ( inset, inset ), ( w - inset, inset ), ( inset, h - inset ), ( w - inset, h - inset ) ]


def _arrow( angle, cx, cy, s ):
    """ An arrow s px long pointing at angle (0 right) round ( cx, cy ). """
    hl = 0.44 * s
    shape = [ ( -s / 2, -0.11 * s ), ( s / 2 - hl, -0.11 * s ), ( s / 2 - hl, -0.36 * s ), ( s / 2, 0 ),
              ( s / 2 - hl, 0.36 * s ), ( s / 2 - hl, 0.11 * s ), ( -s / 2, 0.11 * s ) ]
    return rotated( shape, angle, cx, cy )


def _running_man( sh, cx, cy, s, fg, layers ):
    """ The emergency exit's running figure, s px tall, running right. """
    w = 0.13 * s
    pts = lambda seq: [ ( cx + s * u, cy + s * v ) for u, v in seq ]  # noqa: E731
    sh.dot( cx + 0.1 * s, cy - 0.38 * s, 0.085 * s, fg, layers )
    sh.line( pts( [ ( 0.04, -0.22 ), ( -0.06, 0.08 ) ] ), fg, w * 1.15, layers, round_caps=True )
    sh.line( pts( [ ( 0.02, -0.18 ), ( 0.2, -0.08 ), ( 0.32, -0.16 ) ] ), fg, w * 0.75, layers, round_caps=True )
    sh.line( pts( [ ( 0.02, -0.18 ), ( -0.16, -0.12 ), ( -0.24, 0.0 ) ] ), fg, w * 0.75, layers, round_caps=True )
    sh.line( pts( [ ( -0.06, 0.08 ), ( 0.14, 0.2 ), ( 0.1, 0.42 ) ] ), fg, w * 0.9, layers, round_caps=True )
    sh.line( pts( [ ( -0.06, 0.08 ), ( -0.16, 0.3 ), ( -0.36, 0.34 ) ] ), fg, w * 0.9, layers, round_caps=True )


def _warning( sh, cx, cy, s ):
    """ The yellow warning triangle with its black border and exclamation mark, about s px wide. """
    tri = lambda k: [ ( cx, cy - 0.5 * k * s ), ( cx + 0.55 * k * s, cy + 0.45 * k * s ),  # noqa: E731
                      ( cx - 0.55 * k * s, cy + 0.45 * k * s ) ]
    sh.polygon( tri( 1.0 ), SIGN_BLACK, INK )
    sh.polygon( [ ( x_, y_ + 0.02 * s ) for x_, y_ in tri( 0.76 ) ], SIGN_YELLOW, INK )
    sh.polygon( [ ( cx - 0.045 * s, cy - 0.2 * s ), ( cx + 0.045 * s, cy - 0.2 * s ), ( cx + 0.025 * s, cy + 0.14 * s ),
                  ( cx - 0.025 * s, cy + 0.14 * s ) ], SIGN_BLACK, INK )
    sh.dot( cx, cy + 0.25 * s, 0.045 * s, SIGN_BLACK, INK )


def _sign_no_smoking( sh ):
    """ A printed plate: the prohibition sign (a red ring and bar, 0.1 and 0.08 of its diameter, over a black
    cigarette with its smoke) over NO SMOKING. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 1, 1, w - 1, h - 1 ), SIGN_WHITE, { "plate": 1 }, radius=10 )
    d = 0.84 * w
    cx, cy = w / 2, 0.36 * h
    sh.rectangle( ( cx - 0.27 * d, cy + 0.03 * d, cx + 0.21 * d, cy + 0.13 * d ), SIGN_BLACK, INK )
    sh.rectangle( ( cx - 0.37 * d, cy + 0.03 * d, cx - 0.3 * d, cy + 0.13 * d ), SIGN_BLACK, INK )
    for x_, a_ in ( ( 0.12, 0.0 ), ( 0.18, 1.7 ) ):
        sh.line( [ ( cx + ( x_ + 0.022 * math.sin( 2.6 * t + a_ ) ) * d, cy - 0.065 * t * d )
                   for t in np.linspace( 0.0, 3.3, 24 ) ], SIGN_BLACK, 0.026 * d, INK, round_caps=True )
    sh.ellipse( ( cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2 ), None, RED, outline=SIGN_RED, width=0.1 * d )
    u, b, ln = ( math.sqrt( 0.5 ), math.sqrt( 0.5 ) ), 0.04 * d, 0.43 * d
    v = ( -u[1], u[0] )
    sh.polygon( [ ( cx + sa * u[0] * ln + sb * v[0] * b, cy + sa * u[1] * ln + sb * v[1] * b )
                  for sa, sb in ( ( -1, 1 ), ( 1, 1 ), ( 1, -1 ), ( -1, -1 ) ) ], SIGN_RED, RED )
    sh.text( ( cx, 0.785 * h ), "NO", SIGN_FACE, 40, SIGN_BLACK, INK, "ms", 0.04, width=0.84 * w )
    sh.text( ( cx, 0.93 * h ), "SMOKING", SIGN_FACE, 40, SIGN_BLACK, INK, "ms", 0.04, width=0.84 * w )
    return { "kind": "printed", "screws": _corners( w, h, 13 ) }


def _sign_flammable( sh ):
    """ The flammable-liquids hazard label (class 3): a red diamond 250 mm on its side, its corners at the entry's
    edges' middles, with its line 12.5 mm in, the flame over its base line and the 3 in its bottom corner, all black;
    a vinyl label on the tanker's stainless steel, which shows in the entry's corners. """
    w, h = sh.w, sh.h
    cx, cy = w / 2, h / 2
    sh.polygon( [ ( cx, 0.5 ), ( w - 0.5, cy ), ( cx, h - 0.5 ), ( 0.5, cy ) ], ( 204, 30, 42 ),
                { "plate": 1, "ink": 1, "red": 1 } )
    inset = 14 * math.sqrt( 2.0 )
    line = [ ( cx, inset ), ( w - inset, cy ), ( cx, h - inset ), ( inset, cy ) ]
    sh.line( line + line[:2], SIGN_BLACK, 2.4, INK )
    scale, base = 92.0, 0.53 * h
    sh.polygon( _smooth_closed( [ ( cx + scale * x_, base - scale * y_ ) for x_, y_ in FLAME ] ), SIGN_BLACK, INK )
    sh.rectangle( ( cx - 0.5 * scale, base + 0.04 * scale, cx + 0.5 * scale, base + 0.12 * scale ), SIGN_BLACK, INK )
    sh.text( ( cx, 0.86 * h ), "3", SIGN_FACE, 58, SIGN_BLACK, INK, "ms" )
    return { "kind": "label" }


def _sign_danger_deep_water( sh ):
    """ A printed plate: DANGER in white on its red header, the warning triangle and DEEP WATER in black below. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 1, 1, w - 1, h - 1 ), SIGN_WHITE, { "plate": 1 }, radius=8 )
    sh.rectangle( ( 14, 14, w - 14, 0.33 * h ), SIGN_RED, RED, radius=6 )
    sh.text( ( w / 2, ( 14 + 0.33 * h ) / 2 ), "DANGER", SIGN_FACE, 76, SIGN_WHITE, CLEAR, "ms", 0.06, width=w - 80,
             middle=True )
    _warning( sh, 118, 0.665 * h, 150 )
    sh.text( ( 228, 0.625 * h ), "DEEP", SIGN_FACE, 78, SIGN_BLACK, INK, "ls", 0.05, width=w - 260 )
    sh.text( ( 228, 0.88 * h ), "WATER", SIGN_FACE, 78, SIGN_BLACK, INK, "ls", 0.05, width=w - 260 )
    return { "kind": "printed", "screws": _corners( w, h, 16 ), "seaside": True }


def _sign_visitors( sh ):
    """ A sign-writer's board in the distillery's green, cream letters and a lined border inside a moulded frame, made
    of two boards joined across its middle. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 0, 0, w, h ), SIGN_TEAL, { "plate": 1 } )
    sh.rectangle( ( 0, 0, w, h ), None, { "frame": 1 }, outline=SIGN_TEAL, width=15 )
    sh.rectangle( ( 27, 27, w - 27, h - 27 ), None, INK, radius=4, outline=SIGN_CREAM, width=3 )
    sh.text( ( w / 2, 136 ), "VISITORS", SIGN_FACE, 82, SIGN_CREAM, INK, "ms", 0.1, width=w - 130 )
    sh.text( ( w / 2, 222 ), "PLEASE REPORT TO THE OFFICE", SIGN_FACE, 34, SIGN_CREAM, INK, "ms", 0.06, width=w - 112 )
    return { "kind": "painted", "joints": [ 160 ], "screws": [ ( 7.5, h / 2 ), ( w - 7.5, h / 2 ) ] }


def _sign_fire_point( sh ):
    """ A printed plate: FIRE POINT in white on red, with a white line inset. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 1, 1, w - 1, h - 1 ), SIGN_RED, { "plate": 1, "ink": 1, "red": 1 }, radius=8 )
    sh.rectangle( ( 12, 12, w - 12, h - 12 ), None, CLEAR, radius=6, outline=SIGN_WHITE, width=4 )
    sh.text( ( w / 2, 131 ), "FIRE", SIGN_FACE, 84, SIGN_WHITE, CLEAR, "ms", 0.08, width=w - 80 )
    sh.text( ( w / 2, 241 ), "POINT", SIGN_FACE, 84, SIGN_WHITE, CLEAR, "ms", 0.08, width=w - 80 )
    return { "kind": "printed", "screws": _corners( w, h, 26 ) }


def _sign_dead_slow( sh ):
    """ A harbour board: DEAD SLOW in red on white, a red border. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 0, 0, w, h ), ( 232, 230, 220 ), { "plate": 1 } )
    sh.rectangle( ( 14, 14, w - 14, h - 14 ), None, RED, radius=10, outline=SIGN_SIGNAL_RED, width=8 )
    sh.text( ( w / 2, 130 ), "DEAD", SIGN_FACE, 90, SIGN_SIGNAL_RED, RED, "ms", 0.08, width=w - 90 )
    sh.text( ( w / 2, 246 ), "SLOW", SIGN_FACE, 90, SIGN_SIGNAL_RED, RED, "ms", 0.08, width=w - 90 )
    return { "kind": "painted", "seaside": True, "screws": [ ( w / 2, 7 ), ( w / 2, h - 7 ) ] }


def _sign_private_pier( sh ):
    """ A printed plate: PRIVATE PIER in black, NO UNAUTHORISED ACCESS in red, a black border. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 1, 1, w - 1, h - 1 ), SIGN_WHITE, { "plate": 1 }, radius=8 )
    sh.rectangle( ( 12, 12, w - 12, h - 12 ), None, INK, radius=6, outline=SIGN_BLACK, width=5 )
    sh.text( ( w / 2, 128 ), "PRIVATE PIER", SIGN_FACE, 80, SIGN_BLACK, INK, "ms", 0.06, width=w - 90 )
    sh.text( ( w / 2, 196 ), "NO UNAUTHORISED ACCESS", SIGN_FACE, 30, SIGN_RED, RED, "ms", 0.08, width=w - 140 )
    return { "kind": "printed", "screws": _corners( w, h, 30 ), "seaside": True }


def _sign_bonded_warehouse( sh ):
    """ A cast-iron plate: BONDED WAREHOUSE and a beaded border standing out of it, bolted at its ends. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 0, 0, w, h ), None, { "plate": 1 } )
    sh.rectangle( ( 16, 16, w - 16, h - 16 ), None, { "relief": 1 }, radius=14, outline=( 226, 224, 214 ), width=9 )
    sh.text( ( w / 2, 166 ), "BONDED WAREHOUSE", SIGN_FACE, 92, ( 226, 224, 214 ), { "relief": 1 }, "ms", 0.06,
             width=w - 160 )
    return { "kind": "cast", "bolts": [ ( 50, h / 2 ), ( w - 50, h / 2 ) ] }


def _sign_weighbridge( sh ):
    """ A sign-writer's board: WEIGHBRIDGE in black on white, a black lined border. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 0, 0, w, h ), ( 234, 232, 222 ), { "plate": 1 } )
    sh.rectangle( ( 14, 14, w - 14, h - 14 ), None, INK, radius=8, outline=SIGN_BLACK, width=6 )
    sh.text( ( w / 2, 156 ), "WEIGHBRIDGE", SIGN_FACE, 96, SIGN_BLACK, INK, "ms", 0.08, width=w - 110 )
    return { "kind": "painted", "screws": [ ( 7, h / 2 ), ( w - 7, h / 2 ) ] }


def _sign_exit( sh ):
    """ A printed exit sign: white on green, the running figure at a doorway, EXIT and an arrow to the right. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 1, 1, w - 1, h - 1 ), SIGN_GREEN, { "plate": 1, "ink": 1 }, radius=8 )
    sh.rectangle( ( 114, 38, 166, 178 ), None, CLEAR, outline=SIGN_WHITE, width=7 )
    _running_man( sh, 70, 112, 130, SIGN_WHITE, CLEAR )
    sh.text( ( 184, 141 ), "EXIT", SIGN_FACE, 66, SIGN_WHITE, CLEAR, "ls", 0.06, width=148 )
    sh.polygon( _arrow( 0.0, 382, 108, 72 ), SIGN_WHITE, CLEAR )
    return { "kind": "printed", "screws": _corners( w, h, 12 ) }


def _sign_no_naked_lights( sh ):
    """ A vitreous enamel sign: NO NAKED LIGHTS in red on white, a red border, screwed through its corners. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 0, 0, w, h ), ( 240, 240, 234 ), { "plate": 1 } )
    sh.rectangle( ( 13, 13, w - 13, h - 13 ), None, RED, radius=6, outline=( 190, 28, 36 ), width=6 )
    sh.text( ( w / 2, h / 2 ), "NO NAKED LIGHTS", SIGN_FACE, 62, ( 190, 28, 36 ), RED, "ms", 0.06, width=w - 84,
             middle=True )
    return { "kind": "enamel", "screws": _corners( w, h, 9 ) }


def _sign_keep_clear( sh ):
    """ A printed plate: KEEP CLEAR in black on yellow, a black border. """
    w, h = sh.w, sh.h
    sh.rectangle( ( 1, 1, w - 1, h - 1 ), SIGN_YELLOW, { "plate": 1, "ink": 1 }, radius=8 )
    sh.rectangle( ( 10, 10, w - 10, h - 10 ), None, INK, radius=6, outline=SIGN_BLACK, width=5 )
    sh.text( ( w / 2, 131 ), "KEEP CLEAR", SIGN_FACE, 70, SIGN_BLACK, INK, "ms", 0.08, width=w - 90 )
    return { "kind": "printed", "screws": _corners( w, h, 26 ) }


def _sign_vessel( title, detail ):
    def draw( sh ):
        """ A still house vessel's label: white laminate over a black core, its name and number engraved through to
        the black, its edge bevelled to the black too, screwed at its ends. """
        w, h = sh.w, sh.h
        cut = { "ink": 1, "relief": 1 }
        sh.rectangle( ( 0, 0, w, h ), SIGN_BLACK, { "plate": 1 }, radius=10 )
        sh.rectangle( ( 3, 3, w - 3, h - 3 ), ( 238, 236, 226 ), None, radius=8 )
        if isinstance( title, tuple ):
            sh.text( ( w / 2, 74 ), title[0], SIGN_FACE, 42, SIGN_BLACK, cut, "ms", 0.06, width=w - 84 )
            sh.text( ( w / 2, 128 ), title[1], SIGN_FACE, 42, SIGN_BLACK, cut, "ms", 0.06, width=w - 84 )
            sh.text( ( w / 2, 166 ), detail, SIGN_FACE, 22, SIGN_BLACK, cut, "ms", 0.08, width=w - 120 )
        else:
            sh.text( ( w / 2, 98 ), title, SIGN_FACE, 52, SIGN_BLACK, cut, "ms", 0.06, width=w - 84 )
            sh.text( ( w / 2, 154 ), detail, SIGN_FACE, 26, SIGN_BLACK, cut, "ms", 0.08, width=w - 120 )
        return { "kind": "engraved", "screws": [ ( 22, h / 2 ), ( w - 22, h / 2 ) ] }
    return draw


SIGN_DRAWS = {
    "no_smoking": _sign_no_smoking, "flammable": _sign_flammable, "danger_deep_water": _sign_danger_deep_water,
    "visitors": _sign_visitors, "fire_point": _sign_fire_point, "dead_slow": _sign_dead_slow,
    "private_pier": _sign_private_pier, "bonded_warehouse": _sign_bonded_warehouse, "weighbridge": _sign_weighbridge,
    "exit": _sign_exit, "no_naked_lights": _sign_no_naked_lights, "keep_clear": _sign_keep_clear,
}
SIGN_DRAWS.update( { name: _sign_vessel( *text ) for name, text in VESSEL_LABELS.items() } )
SIGN_BACKGROUNDS = { "flammable": ( 179, 181, 184 ), "bonded_warehouse": ( 30, 30, 30 ) }


def _screw( c, hgt, r, x, y, rad, rng, slot=True ):
    """ A round-headed screw at ( x, y ), rad px across its head's radius (a bolt's dome without its slot), into the
    colour, height and roughness (in place): zinc plating gone dull, rusting round its rim. Returns where its rust
    starts to run, under it. """
    hh, ww = hgt.shape
    x0, x1 = max( 0, int( x - rad - 2 ) ), min( ww, int( x + rad + 3 ) )
    y0, y1 = max( 0, int( y - rad - 2 ) ), min( hh, int( y + rad + 3 ) )
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    d = np.hypot( xx - x, yy - y ) / rad
    disc = np.clip( ( 1.0 - d ) * rad / 0.9 + 0.5, 0.0, 1.0 )
    dome = np.sqrt( np.clip( 1.0 - d * d, 0.0, 1.0 ) )
    rusty = rng.uniform( 0.1, 0.8 )
    col = mix( ( 150, 150, 146 ), ( 116, 72, 42 ), rusty * smoothstep( 0.45, 1.0, d ) )
    hs = 0.07 * dome
    if slot:
        a = rng.uniform( 0, math.pi )
        v = -( xx - x ) * math.sin( a ) + ( yy - y ) * math.cos( a )
        cut = np.clip( 1.0 - np.abs( v ) / 0.75, 0, 1 ) * ( d < 0.82 )
        col = mix( col, ( 44, 40, 36 ), 0.85 * cut )
        hs = hs - 0.035 * cut
    sl = np.s_[y0:y1, x0:x1]
    c[sl] = mix( c[sl], col, disc )
    hgt[sl] = hgt[sl] + disc * hs
    r[sl] = r[sl] * ( 1 - disc ) + 0.5 * disc
    spot = np.zeros( ( hh, ww ) )
    sy = int( min( hh - 1, y + rad ) )
    spot[sy:sy + 2, max( 0, int( x - rad * 0.6 ) ):int( x + rad * 0.6 ) + 1] = rusty
    return spot


def _screws( c, hgt, r, at, rad, rng, slot=True ):
    spots = np.zeros( hgt.shape )
    for x, y in at:
        spots = np.maximum( spots, _screw( c, hgt, r, x, y, rad, rng, slot ) )
    return spots


def _rust_runs( f, c, spots, length=34.0, amount=0.4 ):
    """ Rust run down from spots, broken into streaks. """
    if not spots.any():
        return c
    runs = _trickle( _soft( spots, 0.8 ), length )
    runs *= np.clip( 0.45 + 0.7 * f.down( 1.5, 4, 160, 24, 0.6 ), 0, 1 )
    return mix( c, ( 128, 74, 40 ), amount * np.clip( runs, 0, 1 ) )


def _grime( f, h, w ):
    """ Dirt washed down from the top edge in streaks and gathered along the foot: ( 0..1, the foot's share ). """
    y = np.arange( h )[:, None] + np.zeros( ( 1, w ) )
    top = smoothstep( 0.4, 2.2, f.down( 1.3, 4, 200, 26, 0.6 ) ) * np.exp( -y / ( 0.45 * h ) )
    foot = np.exp( -( h - 1 - y ) / ( 0.07 * h ) )
    grime = 0.5 * top + 0.6 * foot * smoothstep( -1.0, 1.0, f.noise( 2.0, 4, 60 ) ) \
        + 0.12 * smoothstep( 0.0, 2.0, f.noise( 2.4, 2, 30 ) )
    return np.clip( grime, 0, 1 ), foot


def _faded( c, amount ):
    """ Inks faded by the sun: paler and greyer. """
    lum = c.mean( -1, keepdims=True )
    pale = 0.5 * c + 0.5 * ( lum + 34.0 )
    return mix( c, pale, amount )


def _finish_printed( rng, f, c, L, ex ):
    """ A printed plastic or aluminium plate outdoors: its inks faded by the sun (the red most), the white gone a
    little yellow, grime run down from its top and gathered along its foot, salt haze and a little green at the foot
    by the sea, fine scratches, its edge rounded; its screws rusting down it. """
    h, w = c.shape[:2]
    ink, red = np.clip( L["ink"], 0, 1 ), np.clip( L["red"], 0, 1 )
    fade = smoothstep( -1.2, 1.5, f.noise( 2.6, 1, 12 ) )
    c = _faded( c, fade * ( 0.1 + 0.22 * red + 0.08 * ink ) )
    c = mix( c, ( 232, 226, 204 ), 0.14 * fade * ( 1 - ink ) )
    grime, foot = _grime( f, h, w )
    c = mix( c, ( 118, 112, 98 ), 0.26 * grime )
    if ex.get( "seaside" ):
        c = mix( c, ( 216, 218, 214 ), 0.14 * smoothstep( 0.3, 2.0, f.noise( 2.2, 2, 40 ) ) )
        c = mix( c, ( 92, 106, 66 ), 0.4 * foot * smoothstep( -0.3, 1.2, f.noise( 2.2, 4, 80 ) ) )
    scr = _scratches( rng, f.N, 40, ( 8, 60 ), 0.8, rng.uniform( 0, math.pi ), 1.2 )[:h, :w]
    c = mix( c, ( 196, 196, 192 ), 0.25 * scr )
    edge = _inside( L["plate"] )
    hgt = -0.03 * ( 1 - smoothstep( 0.0, 3.0, edge ) ) + 0.0015 * f.noise( 1.5, 30, 500 ) - 0.002 * scr
    r = np.clip( 0.34 + 0.22 * grime + 0.2 * scr + 0.03 * f.noise( 1.0, 100 ), 0, 1 )
    spots = _screws( c, hgt, r, ex.get( "screws", () ), 5.0, rng )
    return _rust_runs( f, c, spots, 30, 0.35 ), r, hgt


def _finish_enamel( rng, f, c, L, ex ):
    """ Vitreous enamel on sheet steel: glassy, the sheet a little domed and its edge rolled (the enamel thin and dark
    there); chipped at the edges and round the screw holes, through the white to the blue-black ground coat and, in the
    bigger chips, to the steel, rusted, which bleeds down the face; a few hairline crazes. """
    h, w = c.shape[:2]
    y = np.arange( h )[:, None] + np.zeros( ( 1, w ) )
    x = np.arange( w )[None, :] + np.zeros( ( h, 1 ) )
    edge = np.minimum( np.minimum( x, w - 1 - x ), np.minimum( y, h - 1 - y ) ) + 0.5
    zone = np.exp( -edge / 7.0 )
    for sx, sy in ex.get( "screws", () ):
        zone = np.maximum( zone, np.exp( -np.maximum( np.hypot( x - sx, y - sy ) - 5.0, 0 ) / 6.0 ) )
    chip_f = f.noise( 1.8, 30, 420 ) + 2.0 * zone + 0.4 * f.noise( 2.4, 1, 8 )
    chipped = smoothstep( 2.55, 2.65, chip_f )
    steel = smoothstep( 3.0, 3.1, chip_f )
    craze = crack_lines( rng, f.N, 8, ( 40, 160 ), 0.6 )[:h, :w]
    c = mix( c, ( 176, 176, 168 ), 0.35 * craze * ( 1 - L["red"] ) )
    grime, foot = _grime( f, h, w )
    c = mix( c, ( 120, 114, 100 ), 0.2 * grime )
    rim = 1 - smoothstep( 1.5, 3.0, edge )
    c = mix( c, ( 34, 40, 58 ), 0.85 * rim )
    c = mix( c, ( 34, 38, 54 ), chipped )
    rust_c = mix( ( 108, 60, 32 ), ( 70, 42, 26 ), smoothstep( -1, 1, f.noise( 1.4, 60, 400 ) ) )
    c = mix( c, rust_c, steel )
    runs = _trickle( _soft( steel, 0.7 ), 26 ) * np.clip( 0.4 + 0.7 * f.down( 1.5, 4, 160, 20, 0.6 ), 0, 1 )
    c = mix( c, ( 150, 86, 46 ), 0.45 * runs * ( 1 - chipped ) )
    hgt = 0.05 * np.sin( np.pi * ( x + 0.5 ) / w ) * np.sin( np.pi * ( y + 0.5 ) / h ) \
        - 0.07 * ( 1 - smoothstep( 0.0, 6.0, edge ) ) ** 2 - 0.012 * chipped - 0.006 * steel
    r = np.clip( 0.1 + 0.1 * grime + 0.2 * chipped + 0.5 * steel + 0.15 * runs * ( 1 - chipped ), 0, 1 )
    spots = _screws( c, hgt, r, ex.get( "screws", () ), 4.5, rng )
    return _rust_runs( f, c, spots, 30, 0.45 ), r, hgt


def _finish_painted( rng, f, c, L, ex ):
    """ A sign-writer's board: oil paint on timber, its grain (along the board) showing through as fine ridges,
    brushed along; the letters' edges wavering a little, by hand. Years outdoors: dirty, flaking along its foot and
    its joints down to the silvered wood, green along its foot by the sea. A moulded frame stands round some. """
    h, w = c.shape[:2]
    y = np.arange( h )[:, None] + np.zeros( ( 1, w ) )
    dx, dy = 0.5 * f.noise( 1.5, 40, 260 ), 0.5 * f.noise( 1.5, 40, 260 )
    c, ink = _warp( [ c, L["ink"] ], dx, dy )
    wav = 9.0 * f.noise( 3.0, 1, 10 ) + 2.5 * f.across( 1.4, 2, 40, 40 )
    ring = ( ( y + wav ) / 6.5 ) % 1.0
    late = smoothstep( 0.62, 0.82, ring ) * ( 1 - smoothstep( 0.88, 1.0, ring ) )
    fibre = f.across( 0.8, 60, 500, 30, 0.3 )
    brush = f.across( 1.0, 20, 600, 14, 0.4 )
    joint = np.zeros( ( h, w ) )
    near = np.zeros( ( h, w ) )
    for jy in ex.get( "joints", () ):
        dist = np.abs( y + 0.6 * f.noise( 2.0, 4, 60 ) - jy )
        joint = np.maximum( joint, smoothstep( 1.8, 0.5, dist ) )
        near = np.maximum( near, np.exp( -dist / 10.0 ) )
    foot = np.exp( -( h - 1 - y ) / ( 0.1 * h ) )
    flake_f = f.noise( 2.0, 16, 300 ) + 0.5 * f.noise( 2.6, 1, 6 ) + 2.0 * foot + 1.3 * near
    bare = smoothstep( 2.62, 2.7, flake_f )
    rim = smoothstep( 2.4, 2.62, flake_f ) * ( 1 - bare )
    c = darken( c, 1.0 + 0.02 * brush + 0.012 * fibre )
    wood = lum_paint( ( 142, 138, 126 ), 1.0 + 0.12 * fibre - 0.3 * late )
    c = mix( c, wood, bare )
    c = mix( c, ( 40, 36, 32 ), 0.65 * joint )
    grime, _ = _grime( f, h, w )
    c = mix( c, ( 112, 106, 92 ), 0.26 * grime )
    if ex.get( "seaside" ):
        c = mix( c, ( 92, 106, 66 ), 0.45 * foot * smoothstep( -0.3, 1.2, f.noise( 2.2, 4, 80 ) ) )
    hgt = 0.012 * late + 0.003 * fibre + 0.0015 * brush + 0.002 * ink - 0.05 * joint - 0.01 * bare + 0.004 * rim
    if L["frame"].max() > 0.5:
        hgt = hgt + 0.18 * smoothstep( 0.0, 5.0, _inside( L["frame"] ) )
    r = np.clip( 0.58 + 0.08 * grime + 0.27 * bare + 0.2 * joint, 0, 1 )
    spots = _screws( c, hgt, r, ex.get( "screws", () ), 5.0, rng )
    return _rust_runs( f, c, spots, 40, 0.4 ), r, hgt


def _finish_cast( rng, f, c, L, ex ):
    """ A cast-iron plate: its letters and beaded border stand out 0.15 in, cast in sand (the face a fine grit, with
    blow holes), painted black with the letters' and bead's faces picked out in white. The white worn off the faces'
    edges, the black worn through to the iron on the edges and corners, rusting, and rust weeping from the bolts. """
    h, w = c.shape[:2]
    y = np.arange( h )[:, None] + np.zeros( ( 1, w ) )
    x = np.arange( w )[None, :] + np.zeros( ( h, 1 ) )
    inner = _inside( L["relief"] )
    raised = ndimage.gaussian_filter( 0.15 * smoothstep( 0.0, 3.0, inner ), 0.8, mode="nearest" )
    face = smoothstep( 1.6, 3.2, inner )
    border = np.minimum( np.minimum( x, w - 1 - x ), np.minimum( y, h - 1 - y ) ) + 0.5
    holes = f.spots( 900, ( 0.6, 1.8 ), "cone" ) * ( 1 - face )
    sand = 0.004 * f.grit( 0.6, 4.0 ) + 0.006 * f.noise( 1.6, 30, 300 ) - 0.02 * holes
    wear_w = smoothstep( 1.5, 2.3, f.noise( 1.8, 30, 300 ) + 1.6 * ( 1 - smoothstep( 1.6, 5.0, inner ) ) )
    black = lum_paint( ( 30, 30, 30 ), 1.0 + 0.08 * f.noise( 2.0, 4, 80 ) )
    out = mix( black, ( 228, 226, 216 ), face * ( 1 - wear_w ) )
    rim = ( inner > 0.5 ) * smoothstep( 3.0, 0.8, np.abs( inner - 1.6 ) )
    iron_f = f.noise( 1.8, 30, 300 ) + 1.3 * rim + 1.5 * np.exp( -border / 4.0 )
    iron = smoothstep( 2.3, 2.7, iron_f )
    out = mix( out, ( 92, 88, 82 ), iron )
    rust = smoothstep( 2.7, 3.1, iron_f ) \
        + smoothstep( 2.9, 3.3, f.noise( 2.2, 16, 200 ) + 0.8 * f.noise( 2.6, 1, 8 ) ) * ( 1 - face )
    rust = np.clip( rust, 0, 1 )
    out = mix( out, ( 104, 58, 32 ), rust )
    runs = _trickle( _soft( rust, 0.8 ), 22 ) * np.clip( 0.4 + 0.7 * f.down( 1.5, 4, 160, 20, 0.6 ), 0, 1 )
    out = mix( out, ( 96, 56, 34 ), 0.45 * runs * ( 1 - face ) )
    out = mix( out, ( 20, 20, 20 ), 0.25 * holes )
    hgt = raised + sand - 0.004 * iron
    r = np.clip( 0.5 + 0.05 * face - 0.05 * iron + 0.35 * rust + 0.2 * runs, 0, 1 )
    spots = _screws( out, hgt, r, ex.get( "bolts", () ), 10.0, rng, slot=False )
    return _rust_runs( f, out, spots, 50, 0.5 ), r, hgt


def _finish_engraved( rng, f, c, L, ex ):
    """ An engraved laminate plate: the letters cut through the white into the black core with a round-nosed cutter,
    the edge bevelled to the black; the white gone cream with age and the still house's warmth, smudged by hands, a
    few scratches. """
    h, w = c.shape[:2]
    groove = -0.03 * smoothstep( 0.0, 1.6, _inside( L["relief"] ) )
    bevel = -0.04 * ( 1 - smoothstep( 0.0, 3.5, _inside( L["plate"] ) ) )
    ink = np.clip( L["ink"], 0, 1 )
    cream = smoothstep( -1.0, 1.4, f.noise( 2.4, 1, 10 ) )
    c = mix( c, c * np.array( ( 0.98, 0.95, 0.86 ) ), ( 0.35 + 0.4 * cream ) * ( 1 - ink ) )
    smudge = smoothstep( 0.6, 2.0, f.noise( 2.2, 6, 80 ) ) * ( 1 - ink )
    c = mix( c, ( 176, 170, 152 ), 0.16 * smudge )
    scr = _scratches( rng, f.N, 24, ( 10, 50 ), 0.7, rng.uniform( 0, math.pi ), 1.4 )[:h, :w]
    c = mix( c, ( 150, 148, 140 ), 0.2 * scr * ( 1 - ink ) )
    hgt = groove + bevel - 0.002 * scr
    r = np.clip( 0.28 + 0.4 * ink + 0.12 * smudge + 0.2 * scr, 0, 1 )
    _screws( c, hgt, r, ex.get( "screws", () ), 4.5, rng )
    return c, r, hgt


def _finish_label( rng, f, c, L, ex ):
    """ The vinyl hazard label on the tanker's stainless steel: its red faded towards pink in places, its edge a step
    above the steel, its left corner lifting, with grime caught under its edge there; the steel round it brushed. """
    h, w = c.shape[:2]
    y = np.arange( h )[:, None] + np.zeros( ( 1, w ) )
    x = np.arange( w )[None, :] + np.zeros( ( h, 1 ) )
    plate = np.clip( L["plate"], 0, 1 )
    brushed = f.across( 1.0, 30, 800, 30, 0.3 )
    steel = lum_paint( ( 179, 181, 184 ), 1.0 + 0.03 * brushed + 0.02 * f.noise( 2.0, 2, 30 ) )
    fade = smoothstep( -1.0, 1.4, f.noise( 2.6, 1, 10 ) )
    c = _faded( c, ( 0.12 + 0.25 * fade ) * L["red"] + 0.08 * fade * np.clip( L["ink"] - L["red"], 0, 1 ) )
    zone = smoothstep( 50.0, 22.0, x + np.abs( y - h / 2 ) )
    lift = zone * plate
    c = mix( c, ( 236, 214, 210 ), 0.22 * lift )
    edge_in = 1 - smoothstep( 0.0, 3.0, _inside( plate ) )
    c = mix( c, ( 70, 58, 50 ), 0.6 * edge_in * zone )
    out_d = ndimage.distance_transform_edt( plate < 0.5 )
    shadow = zone * ( 1 - plate ) * np.exp( -out_d / 3.0 )
    grime, _ = _grime( f, h, w )
    out = mix( steel, c, plate )
    out = mix( out, ( 60, 54, 48 ), 0.5 * shadow )
    out = mix( out, ( 116, 110, 100 ), 0.22 * grime )
    hgt = 0.006 * smoothstep( 0.2, 0.8, plate ) + 0.03 * lift + 0.0006 * brushed
    r = np.clip( 0.3 + 0.12 * plate + 0.2 * grime + 0.02 * brushed + 0.2 * edge_in * zone, 0, 1 )
    return out, r, hgt


SIGN_FINISHES = { "printed": _finish_printed, "enamel": _finish_enamel, "painted": _finish_painted,
                  "cast": _finish_cast, "engraved": _finish_engraved, "label": _finish_label }


def _arc( cx, cy, rx, ry, a0, a1, steps=28 ):
    """ Points round an ellipse from a0 to a1 (degrees, anticlockwise from the right, y up). """
    return [ ( cx + rx * math.cos( math.radians( t ) ), cy - ry * math.sin( math.radians( t ) ) )
             for t in np.linspace( a0, a1, steps ) ]


def _roman( ch ):
    """ A carved capital's strokes ( polylines in cap heights, x right, y down ) and its advance: Roman letters as a
    broad nib draws them, with serifs. """
    if ch == "C":
        return 0.84, [ _arc( 0.46, 0.5, 0.4, 0.5, 48, 312, 40 ), [ ( 0.728, 0.128 ), ( 0.74, 0.27 ) ],
                       [ ( 0.728, 0.872 ), ( 0.745, 0.74 ) ] ]
    if ch == "R":
        bowl = [ ( 0.14, 0.0 ), ( 0.44, 0.0 ) ] + _arc( 0.44, 0.255, 0.255, 0.255, 90, -90 ) + [ ( 0.14, 0.51 ) ]
        return 0.88, [ [ ( 0.14, 0.0 ), ( 0.14, 1.0 ) ], bowl, [ ( 0.38, 0.51 ), ( 0.78, 1.0 ) ],
                       [ ( 0.0, 0.0 ), ( 0.28, 0.0 ) ], [ ( 0.0, 1.0 ), ( 0.3, 1.0 ) ], [ ( 0.66, 1.0 ), ( 0.9, 1.0 ) ] ]
    if ch == "1":
        return 0.56, [ [ ( 0.26, 0.0 ), ( 0.26, 1.0 ) ], [ ( 0.26, 0.0 ), ( 0.08, 0.16 ) ],
                       [ ( 0.06, 1.0 ), ( 0.46, 1.0 ) ] ]
    if ch == "8":
        return 0.74, [ _arc( 0.36, 0.25, 0.21, 0.245, 0, 360, 44 ), _arc( 0.36, 0.735, 0.27, 0.265, 0, 360, 48 ) ]
    if ch == "2":
        return 0.76, [ _arc( 0.34, 0.27, 0.27, 0.26, 165, -32 ) + [ ( 0.04, 1.0 ), ( 0.7, 1.0 ), ( 0.71, 0.86 ) ] ]
    if ch == "4":
        return 0.8, [ [ ( 0.54, 0.0 ), ( 0.02, 0.7 ), ( 0.76, 0.7 ) ], [ ( 0.54, 0.0 ), ( 0.54, 1.0 ) ],
                      [ ( 0.4, 1.0 ), ( 0.7, 1.0 ) ] ]
    raise ValueError( ch )


def _carved( lines, w, h, k=4, nib=0.14, angle=30.0, spacing=0.12 ):
    """ Lines ( text, cap px, top px ) cut in Roman capitals, centred across w: the letters' mask, k times over. Each
    stroke is a broad nib's sweep (nib cap heights wide, held at angle degrees), so its stems are thick and its
    hairlines thin, never under 0.3 of the nib; the inside corners filled round, as a carver brackets the serifs. """
    img = Image.new( "L", ( w * k, h * k ), 0 )
    d = ImageDraw.Draw( img )
    for s, cap, top in lines:
        total = sum( _roman( ch )[0] for ch in s ) + spacing * ( len( s ) - 1 )
        x = w / 2 - total * cap / 2
        a = math.radians( angle )
        nx, ny = 0.5 * nib * cap * math.cos( a ), -0.5 * nib * cap * math.sin( a )
        for ch in s:
            adv, strokes = _roman( ch )
            for pts in strokes:
                p = [ ( x + cap * u, top + cap * v ) for u, v in pts ]
                for ( x0, y0 ), ( x1, y1 ) in zip( p, p[1:] ):
                    d.polygon( [ ( ( x0 + nx ) * k, ( y0 + ny ) * k ), ( ( x1 + nx ) * k, ( y1 + ny ) * k ),
                                 ( ( x1 - nx ) * k, ( y1 - ny ) * k ), ( ( x0 - nx ) * k, ( y0 - ny ) * k ) ], fill=255 )
                d.line( [ ( px * k, py * k ) for px, py in p ], fill=255, width=max( 1, int( 0.3 * nib * cap * k ) ),
                        joint="curve" )
            x += ( adv + spacing ) * cap
    return _closed( np.asarray( img ) >= 128, 0.045 * lines[0][1] * k )


def _datestone( rng, w, h ):
    """ The gate's datestone at 24 px an inch: a block of buff sandstone, a drafted margin round its face (tooled in
    fine batter lines square to each edge, mitred at the corners) and the field rubbed smooth, a little proud; its
    arrises worn round and bitten. CR over 1824 V-cut into the field in Roman capitals, with the black paint that was
    put in them left in the bottoms. Iron-stained bands and bedding in the stone; grime and lichen (grey-green, and
    orange near the top) from the weather. """
    f = _Fields( rng, w, h )
    y = np.arange( h )[:, None] + np.zeros( ( 1, w ) )
    x = np.arange( w )[None, :] + np.zeros( ( h, 1 ) )
    lr, tb = np.minimum( x, w - 1 - x ) + 0.5, np.minimum( y, h - 1 - y ) + 0.5
    border = np.minimum( lr, tb )
    margin = 48.0
    along = np.where( tb < lr, x, y )
    batter = 0.5 + 0.5 * np.sin( 2 * np.pi * ( along + 1.4 * f.noise( 2.0, 4, 60 ) ) / 3.6 )
    batter *= 0.6 + 0.4 * smoothstep( -1.0, 1.0, f.noise( 1.6, 20, 200 ) )
    field = smoothstep( margin - 1.5, margin + 1.5, border )
    k = 4
    cut = _carved( [ ( "CR", 100, 74 ), ( "1824", 100, 222 ) ], w, h, k )
    letters = cut.reshape( h, k, w, k ).mean( ( 1, 3 ) )
    depth = 0.9 * ndimage.distance_transform_edt( cut ).reshape( h, k, w, k ).mean( ( 1, 3 ) ) / ( k * SIGN_PPI )
    pits = f.spots( 9000, ( 1.0, 2.6 ), "cone" ) * field * ( 1 - letters )
    stone = 0.02 * field + ( 1 - field ) * 0.008 * batter + 0.005 * f.noise( 2.2, 6, 80 ) \
        + 0.003 * f.grit( 0.6, 4.0 ) - 0.012 * pits
    bite = smoothstep( 1.3, 2.2, f.noise( 1.8, 10, 200 ) )
    stone -= 0.14 * ( 1 - smoothstep( 0.0, 10.0 + 10.0 * bite, border ) ) ** 2
    hgt = stone - depth
    lum = 1 + 0.05 * f.noise( 2.2, 2, 40 ) + 0.03 * f.noise( 1.2, 60, 400 )
    c = lum_paint( ( 184, 162, 124 ), lum )
    bands = smoothstep( 0.55, 0.95, 0.5 + 0.5 * np.sin( 2 * np.pi * ( y + 14 * f.noise( 3.0, 1, 6 ) ) / 70 + 1.3 ) )
    c = mix( c, ( 166, 128, 92 ), 0.35 * bands * smoothstep( -1.0, 1.0, f.noise( 2.4, 1, 10 ) ) )
    bedding = smoothstep( 0.93, 0.99, np.cos( 2 * np.pi * ( y + 6 * f.noise( 3.0, 1, 8 ) ) / 31 ) )
    c = mix( c, ( 140, 124, 100 ), 0.3 * bedding )
    cav = np.clip( ndimage.gaussian_filter( hgt, 2.0, mode="nearest" ) - hgt, 0, None )
    c = darken( c, np.exp( -9.0 * cav ) )
    c = darken( c, 1.0 - 0.3 * smoothstep( 0.0, 0.12, depth ) )
    paint = letters * smoothstep( -0.2, 0.4, f.noise( 1.8, 20, 300 ) + 0.5 ) * smoothstep( 0.02, 0.08, depth )
    c = mix( c, ( 34, 34, 34 ), 0.9 * paint )
    grime = smoothstep( 0.3, 2.2, f.down( 1.3, 4, 220, 24, 0.6 ) ) * np.exp( -y / ( 0.5 * h ) )
    c = mix( c, ( 104, 98, 86 ), 0.45 * grime )
    lichen = smoothstep( 1.3, 2.0, f.noise( 2.6, 2, 30 ) + 0.4 * f.noise( 1.4, 30, 200 ) + 0.8 * ( 1 - y / h ) - 0.6 )
    c = mix( c, ( 130, 138, 118 ), 0.4 * lichen * ( 1 - letters ) )
    xan = np.zeros( ( f.N, f.N ) )
    for _ in range( 46 ):
        r_ = rng.uniform( 1.5, 5.5 )
        stamp( xan, rng.uniform( 0, w ), abs( rng.normal( 0, 0.16 * h ) ), r_, r_ * rng.uniform( 0.7, 1.0 ), 1.0,
               soft=1.0 )
    c = mix( c, ( 204, 142, 44 ), 0.75 * xan[:h, :w] * ( 1 - letters ) )
    r = np.clip( 0.86 + 0.03 * f.noise( 1.0, 100 ) - 0.24 * paint + 0.04 * lichen, 0, 1 )
    return c, r, hgt


def _sign( rng, name, w, h ):
    """ One sign's colour, roughness, height (drawn at SIGN_PPI) and how much of it is the sign itself (for the
    gutters' fill). """
    if name == "datestone":
        c, r, hgt = _datestone( rng, w, h )
        return c, r, hgt, np.ones( ( h, w ) )
    sh = Sheet( w, h, SIGN_BACKGROUNDS.get( name, SIGN_WHITE ), 4, plate=0.0, ink=0.0, red=0.0, relief=0.0, frame=0.0 )
    ex = SIGN_DRAWS[name]( sh )
    colour, L = sh.arrays()
    c, r, hgt = SIGN_FINISHES[ex["kind"]]( rng, _Fields( rng, w, h ), colour, L, ex )
    weight = np.ones( ( h, w ) ) if ex["kind"] == "label" else smoothstep( 0.3, 0.7, L["plate"] )
    return c, r, hgt * SIGN_OWN_PPI.get( name, SIGN_PPI ) / SIGN_PPI, weight


@texture( "signs" )
def signs( rng, n ):
    """ sh_signs: the plates and signs, each in its SIGNS_RECTS entry, at about 24 px an inch (the flammable label at
    28.8, so its diamond is the real 250 mm on stillhouse_props' 13.9 in quad). Printed plastic and aluminium safety
    signs, faded and grimed; sign-writers' boards, flaking; a cast-iron plate, worn and rusting; an enamel sign,
    chipped; engraved laminate labels on the still house's vessels; the vinyl hazard label on the tanker's steel; and
    the gate's carved datestone. Their wording is generic: no maker, office or real place. """
    colour = np.zeros( ( n, n, 3 ) )
    rough = np.full( ( n, n ), 0.5 )
    height = np.zeros( ( n, n ) )
    weight = np.zeros( ( n, n ) )
    for name, ( x0, y0, x1, y1 ) in SIGNS_RECTS.items():
        sl = np.s_[y0:y1, x0:x1]
        colour[sl], rough[sl], height[sl], weight[sl] = _sign( rng, name, x1 - x0, y1 - y0 )
    colour = _push_pull( colour, weight )
    rough, height = _padded( rough, height, _rects_mask( n, SIGNS_RECTS ) )
    return { "sh_signs": colour }, rough, height, SIGN_PPI * 1024 / n


# ---------------------------------------------------------------------------------------------------------------------
# sh_cask_head

# Each head: its fill (R a refill ex-bourbon cask, S a sherry butt), the year it was filled, its stencilled lines
# ( text, cap px, red ), and the ghost of the fill before it ( text, cap px ) or None.
CASK_HEADS = {
    "head_0": ( "S", 2009, [ ( "CR", 84, False ), ( "2009", 64, False ), ( "0472", 54, False ), ( "S", 70, False ) ],
                None ),
    "head_1": ( "R", 2011, [ ( "CR 2011", 72, False ), ( "1188 R", 64, False ) ], [ ( "1996", 60 ) ] ),
    "head_2": ( "R", 2014, [ ( "CR", 84, False ), ( "2014", 64, False ), ( "2251 R", 54, False ) ],
                [ ( "CR 1998", 56 ), ( "2207", 50 ) ] ),
    "head_3": ( "S", 2010, [ ( "CR", 84, False ), ( "2010", 64, False ), ( "0903", 54, False ), ( "S", 70, False ) ],
                None ),
    "head_4": ( "R", 2016, [ ( "CR 2016", 72, False ), ( "3076", 64, False ), ( "R", 70, True ) ], [ ( "4471", 54 ) ] ),
    "head_5": ( "R", 2019, [ ( "CR", 84, False ), ( "2019", 64, False ), ( "4410 R", 54, False ) ], [ ( "3341", 56 ) ] ),
    "head_6": ( "R", 2012, [ ( "CR", 84, True ), ( "2012", 64, False ), ( "1634 R", 54, False ) ],
                [ ( "CR", 70 ), ( "2004", 56 ) ] ),
    "head_7": ( "S", 2017, [ ( "CR 2017", 72, False ), ( "3502 S", 64, False ) ], None ),
    "head_plain": ( "R", None, [], None ),
}
# The heads with a chalk mark ( strokes in the head's 1024 px tile ) and those with a plug in them.
CASK_HEAD_CHALK = {
    "head_3": [ [ ( 612, 704 ), ( 634, 736 ), ( 694, 650 ) ] ],
    "head_5": [ [ ( 318, 330 ), ( 372, 324 ), ( 338, 410 ) ], [ ( 330, 368 ), ( 366, 366 ) ] ],
}
CASK_HEAD_PLUG = ( "head_0", "head_4" )
# Oak: ( face, latewood, weathered grey, dirt, wet, the bevel's fresh cut ).
CASK_OAK = {
    "R": ( ( 150, 110, 72 ), ( 98, 68, 44 ), ( 136, 126, 110 ), ( 86, 70, 54 ), ( 90, 60, 38 ), ( 172, 138, 100 ) ),
    "S": ( ( 106, 68, 48 ), ( 64, 40, 30 ), ( 98, 80, 68 ), ( 54, 40, 32 ), ( 58, 32, 26 ), ( 128, 90, 64 ) ),
}


def _stencil_line( s, cap, k=4, bridge=0.085, tracking=0.08 ):
    """ A line of stencilled capitals, k times over: LETTERING_FACE's letters with each counter tied to the outside by
    a bridge, a cut bridge * cap wide through the ink straight above and below it, as a stencil plate's ties hold its
    islands. A box 1.5 cap high with the baseline 1.25 cap down. """
    f = sized( LETTERING_FACE, cap * k )
    wpx = int( text_width( s, f, tracking * cap * k ) ) + 8 * k
    hpx = int( 1.5 * cap * k )
    img = Image.new( "L", ( wpx, hpx ), 0 )
    put( ImageDraw.Draw( img ), ( 4 * k, 1.25 * cap * k ), s, f, 255, "ls", tracking * cap * k )
    ink = np.asarray( img ) >= 128
    holes, count = ndimage.label( ndimage.binary_fill_holes( ink ) & ~ink )
    half = max( 1, int( round( bridge * cap * k / 2 ) ) )
    for lab in range( 1, count + 1 ):
        rows, cols = np.nonzero( holes == lab )
        if len( rows ) < 8:
            continue
        mid = int( round( cols.mean() ) )
        for col in range( mid - half, mid + half + 1 ):
            r_hole = rows[cols == col]
            if not len( r_hole ):
                continue
            column = ink[:, col]
            r = r_hole.min() - 1
            while r >= 0 and column[r]:
                column[r] = False
                r -= 1
            r = r_hole.max() + 1
            while r < hpx and column[r]:
                column[r] = False
                r += 1
    return ink


def _stencil_block( lines, n, centre, angle, k=4 ):
    """ Stencilled lines ( text, cap px ), each centred across centre (px in an n px tile) and stacked down it with
    gaps of 0.42 of the smaller cap, the block turned by angle degrees: a mask per line, 0..1. """
    gaps = [ 0.42 * min( a[1], b[1] ) for a, b in zip( lines, lines[1:] ) ]
    top = centre[1] - ( sum( cap for _, cap in lines ) + sum( gaps ) ) / 2
    out = []
    for i, ( s, cap ) in enumerate( lines ):
        if i:
            top += gaps[i - 1]
        ink = _stencil_line( s, cap, k )
        cols = np.nonzero( ink.any( 0 ) )[0]
        if not len( cols ):
            out.append( np.zeros( ( n, n ) ) )
            top += cap
            continue
        x0 = int( round( centre[0] * k - ( cols[0] + cols[-1] ) / 2 ) )
        y0 = int( round( ( top - 0.25 * cap ) * k ) )
        big = np.zeros( ( n * k, n * k ), np.uint8 )
        hh, ww = ink.shape
        big[y0:y0 + hh, x0:x0 + ww] = ink * 255
        img = Image.fromarray( big ).rotate( angle, resample=Image.BILINEAR, center=( centre[0] * k, centre[1] * k ) )
        out.append( np.asarray( img.reduce( k ), float ) / 255.0 )
        top += cap
    return out


def _sprayed( rng, n, mask, grain, fade ):
    """ A stencil's spray paint: the mask's edge softened by the paint creeping under the plate, a faint overspray
    round it, uneven where the can was passed over, thinner on the oak's hard latewood, weathered by fade. """
    soft = T.blur( mask, 0.6 )
    halo = T.blur( mask, 3.5 ) * 0.22 * smoothstep( -0.5, 1.5, noise( rng, n, 1.0, n / 6 ) )
    density = 0.82 + 0.18 * smoothstep( -1.2, 1.2, noise( rng, n, 2.2, 3, 40 ) )
    density *= 1.0 - 0.25 * grain
    return np.clip( ( soft * density + halo * ( 1 - soft ) ) * ( 1.0 - fade ), 0, 1 )


def _cask_head( rng, name, size ):
    """ One head, size px across its disc, drawn in a 1024 px tile: ( colour, roughness, height, the disc ) cut to its
    square. """
    N = 1024
    fill, year, lines, ghost = CASK_HEADS[name]
    sherry = fill == "S"
    base_c, late_c, grey_c, dirt_c, wet_c, cut_c = CASK_OAK[fill]
    R = size / 2.0
    cx = cy = N / 2.0
    x, y = coords( N )
    dx, dy = x - cx, y - cy
    rho = np.hypot( dx, dy )
    # The head's boards, 4-6 of them, the middle ones widest, their joints within 8 degrees of upright.
    phi = math.radians( rng.uniform( -8, 8 ) )
    gg = dx * math.sin( phi ) + dy * math.cos( phi )
    tt = dx * math.cos( phi ) - dy * math.sin( phi )
    nb = int( rng.integers( 4, 7 ) )
    widths = rng.uniform( 0.8, 1.2, nb ) * ( 1.0 + 0.25 * np.cos( np.pi * ( np.arange( nb ) - ( nb - 1 ) / 2 ) / nb ) )
    widths *= ( 2 * R + 6 ) / widths.sum()
    edges = -( R + 3 ) + np.concatenate( ( [ 0.0 ], np.cumsum( widths ) ) )
    board = np.clip( np.searchsorted( edges, tt, side="right" ) - 1, 0, nb - 1 )
    u = tt - edges[board]
    w = widths[board]
    side = np.minimum( u, w - u )
    side = np.where( ( ( board == 0 ) & ( u < w / 2 ) ) | ( ( board == nb - 1 ) & ( u > w / 2 ) ), 99.0, side )
    seam = smoothstep( 1.3, 0.35, side )
    rows = ( gg + cy + rng.uniform( 0, N, nb )[board] ) % N
    cols = ( tt + cx ) % N

    def along( field ):
        """ A field whose grain runs down its rows, laid along the boards. """
        return ndimage.map_coordinates( field, [ rows, cols ], order=1, mode="grid-wrap" )

    # Quarter-sawn white oak. Its rings are fine lines along each board, 6-11 an inch, their spacing changing as the
    # tree grew faster or slower from year to year and each year's line darker or fainter: the earlywood's band of
    # big pores, broken along the grain, with the dense latewood between. Ray flecks cross them, pale and glossy;
    # streaks of lighter and darker wood run along the boards, and each board is its own shade.
    sp = rng.uniform( 2.6, 4.6, nb )[board]
    wander = along( 2.0 * noise( rng, N, 3.0, 1, 10 ) ) + rng.uniform( 0, 10, nb )[board]
    growth = along( BT.stretched( rng, N, 1.0, 5, 20, ( 200, 0.1 ) ) )
    phase = ( u + wander ) / sp + 1.8 * growth
    ring = phase % 1.0
    year_k = rng.uniform( 0.3, 1.0, 4096 )[( np.floor( phase ).astype( int ) + 613 * board ) % 4096]
    gy_, gx_ = np.gradient( phase )
    crowd = smoothstep( 0.5, 0.3, np.hypot( gx_, gy_ ) )
    pores = smoothstep( 0.9, 2.2, along( BT.stretched( rng, N, 0.6, N / 6, N / 2, ( 6, 0.3 ) ) ) )
    band = smoothstep( 0.0, 0.12, ring ) * ( 1 - smoothstep( 0.3, 0.46, ring ) )
    late = ( band * year_k * ( 0.55 + 0.45 * pores ) ) * crowd + 0.25 * ( 1 - crowd )
    fibre = along( BT.stretched( rng, N, 0.7, N / 8, N / 2, ( 40, 0.4 ) ) )
    streak = along( BT.stretched( rng, N, 1.2, 6, 120, ( 70, 0.8 ) ) )
    fl = np.zeros( ( N, N ) )
    for _ in range( 340 ):
        stamp( fl, rng.uniform( 0, N ), rng.uniform( 0, N ), rng.uniform( 6, 22 ), rng.uniform( 1.6, 5.0 ),
               rng.uniform( 0.4, 1.0 ), angle=rng.normal( 0, 0.45 ), soft=0.6, profile="dome" )
    fleck = along( fl )
    tone = rng.uniform( 0.8, 1.16, nb )[board]
    hue = rng.uniform( -1.0, 1.0, nb )[board]
    # The cooper's plane leaves shallow ridges across each board.
    plane = np.sin( 2 * np.pi * ( gg / rng.uniform( 40, 60, nb )[board] + rng.uniform( 0, 1, nb )[board] )
                    + 0.8 * noise( rng, N, 2.0, 2, 16 ) )
    weather = smoothstep( -0.6, 1.6, noise( rng, N, 2.6, 1, 10 ) )
    greyness = rng.uniform( 0.05, 0.25 ) if sherry else rng.uniform( 0.25, 0.65 )
    # Lying in the warehouse, a head is dirtiest low down, near the floor, where the fungus grows thickest too.
    low = smoothstep( -0.3 * R, 0.95 * R, dy )
    dirt = smoothstep( 0.2, 2.2, noise( rng, N, 2.4, 1, 14 ) + 0.4 * noise( rng, N, 1.6, 14, 60 ) )
    soot = smoothstep( 0.9, 2.3, noise( rng, N, 2.4, 2, 24 ) + 0.5 * noise( rng, N, 1.4, 24, 120 ) ) \
        * ( 0.3 + 0.7 * low )
    specks = smoothstep( 2.4, 3.1, grain_field( rng, N, 0.7, 4.0 )
                         + 1.6 * smoothstep( 0.6, 2.0, noise( rng, N, 2.4, 2, 16 ) ) + 0.8 * soot )
    seep = wash_down( seam * smoothstep( 1.0, 2.2, noise( rng, N, 2.0, 2, 30 ) ), 40, 0.8, rng, keep=0.8 )
    c = lum_paint( base_c, tone * ( 1.0 + 0.04 * fibre + 0.07 * streak + 0.015 * plane ) )
    c = c * np.stack( [ 1.0 + 0.045 * hue, np.ones_like( hue ), 1.0 - 0.07 * hue ], -1 )
    c = mix( c, late_c, 0.6 * late + 0.15 * pores * ( 1 - band ) )
    c = mix( c, tuple( min( 255.0, v * 1.22 ) for v in base_c ), 0.55 * fleck )
    c = mix( c, grey_c, ( 0.2 + 0.5 * weather ) * greyness )
    c = mix( c, dirt_c, ( 0.18 + 0.3 * low ) * dirt + 0.1 * low )
    if sherry:
        stain = np.clip( 0.5 * smoothstep( 0.8, 2.0, noise( rng, N, 2.6, 2, 20 ) ) + 0.6 * seep, 0, 1 )
        c = mix( c, ( 74, 30, 34 ), 0.5 * stain )
    c = mix( c, wet_c, 0.55 * np.clip( seep, 0, 1 ) )
    c = mix( c, ( 38, 34, 30 ), 0.35 * soot )
    c = mix( c, ( 28, 24, 20 ), 0.65 * specks )
    c = mix( c, ( 36, 26, 20 ), 0.8 * seam )
    paint = np.zeros( ( N, N ) )
    grain = np.clip( 0.6 * late + 0.6 * pores, 0, 1 )
    if ghost:
        masks = _stencil_block( ghost, N, ( cx + rng.uniform( -60, 60 ), cy + rng.uniform( -60, 60 ) ),
                                rng.uniform( -12, 12 ) )
        c = mix( c, ( 40, 36, 32 ), 0.2 * _sprayed( rng, N, np.clip( sum( masks ), 0, 1 ), grain, 0.3 ) )
    if lines:
        masks = _stencil_block( [ ( s, cap ) for s, cap, _ in lines ], N,
                                ( cx + rng.uniform( -30, 30 ), cy + rng.uniform( -20, 20 ) ), rng.uniform( -5, 5 ) )
        fade = float( np.clip( ( 2019 - year ) / 10 * 0.4, 0.0, 0.45 ) )
        for red in ( False, True ):
            mine = [ m for m, ( _, _, rd ) in zip( masks, lines ) if rd == red ]
            if not mine:
                continue
            p = _sprayed( rng, N, np.clip( sum( mine ), 0, 1 ), grain, fade )
            c = mix( c, ( 150, 34, 30 ) if red else ( 26, 24, 22 ), p )
            paint = np.maximum( paint, p )
    for strokes in CASK_HEAD_CHALK.get( name, () ):
        img = Image.new( "L", ( N * 4, N * 4 ), 0 )
        ImageDraw.Draw( img ).line( [ ( ( px + rng.normal( 0, 0.6 ) ) * 4, ( py + rng.normal( 0, 0.6 ) ) * 4 )
                                      for px, py in strokes ], fill=255, width=14, joint="curve" )
        chalk = np.asarray( img.reduce( 4 ), float ) / 255.0
        chalk *= smoothstep( -0.4, 0.9, grain_field( rng, N, 0.8, 3.0 ) + 0.6 * noise( rng, N, 1.0, N / 8 )
                             + 0.6 * late )
        c = mix( c, ( 226, 224, 214 ), 0.85 * chalk )
        paint = np.maximum( paint, 0.5 * chalk )
    plug = np.zeros( ( N, N ) )
    if name in CASK_HEAD_PLUG:
        px, py = cx + rng.uniform( -40, 40 ), cy + 0.62 * R
        d = np.hypot( x - px, y - py )
        plug = np.clip( 16.5 - d, 0, 1 )
        c = mix( c, mix( late_c, base_c, 0.4 ), plug )
        c = mix( c, ( 30, 22, 16 ), 0.8 * np.clip( 1.0 - np.abs( d - 16.0 ) / 1.2, 0, 1 ) )
    bev = np.clip( ( rho - ( R - 38 ) ) / 38, 0, 1 )
    on_bev = smoothstep( R - 39, R - 36, rho )
    c = mix( c, cut_c, 0.22 * on_bev )
    croze = smoothstep( R - 5, R - 2.5, rho )
    c = mix( c, ( 24, 19, 15 ), 0.85 * croze )
    step = rng.uniform( -0.015, 0.015, nb )[board]
    # The weather wears the soft earlywood down, so the latewood stands up a little.
    hgt = step - 0.006 * late * ( 0.4 + 0.6 * weather ) - 0.004 * pores + 0.002 * fibre + 0.003 * fleck \
        + 0.003 * plane - 0.03 * seam - 0.25 * bev - 0.3 * croze - 0.012 * plug
    r = 0.75 + 0.05 * weather * greyness + 0.04 * dirt + 0.04 * soot - 0.15 * np.clip( seep, 0, 1 ) - 0.08 * fleck \
        + 0.08 * on_bev + 0.15 * seam
    r = np.clip( r * ( 1 - paint ) + 0.68 * paint, 0, 1 )
    lo = int( cx - R )
    crop = np.s_[lo:lo + size, lo:lo + size]
    return c[crop], r[crop], hgt[crop], ( rho < R - 1 )[crop].astype( float )


@texture( "cask_head" )
def cask_head( rng, n ):
    """ sh_cask_head: cask ends, each in its CASK_HEAD_RECTS square, the head's edge touching the square, upright as
    stillhouse_props lays them (down the picture is down a lying cask's head). Quarter-sawn white oak boards, their
    joints near upright: the rings' fine lines along them, the pores, the ray flecks across; bevelled round the edge
    and meeting the staves at the croze. Refills (ex-bourbon) grey and dusty, sherry butts dark and stained red; black
    specks of the warehouse fungus; spirit seeping darker from the joints. head_0..7 stencilled in spray paint: CR, the
    year filled, the cask number and R or S, with bridges in the letters, a little askew, the older fainter, some over
    the ghost of an older fill; a couple chalked, two with a plug. head_plain is bare. About 28 px an inch. """
    colour = np.zeros( ( n, n, 3 ) )
    rough = np.full( ( n, n ), 0.8 )
    height = np.zeros( ( n, n ) )
    weight = np.zeros( ( n, n ) )
    for name, ( x0, y0, x1, y1 ) in CASK_HEAD_RECTS.items():
        sl = np.s_[y0:y1, x0:x1]
        colour[sl], rough[sl], height[sl], weight[sl] = _cask_head( rng, name, x1 - x0 )
    colour = _push_pull( colour, weight )
    rough, height = _padded( rough, height, _rects_mask( n, CASK_HEAD_RECTS ) )
    return { "sh_cask_head": colour }, rough, height, CASK_HEAD_PPI * 1024 / n


# ---------------------------------------------------------------------------------------------------------------------
# The interface

def paints():
    """ { paint: ( texture, tile units ) } for every sh_ paint: the glass at 64, the sea at 768, the atlases at 64. """
    out = { p: ( tex, float( _SPEC[tex][3] ) ) for tex, ps in TEXTURE_PAINTS.items() for p in ps }
    for g in GLASS:
        out[g] = ( "glass", 64.0 )
    for s, tile in SEA.items():
        out[s] = ( "sea", tile )
    return out


def tile_units( paint_name ):
    return paints()[paint_name][1]


def material_path( paint_name ):
    return f"{RESOURCE_DIR}/{paint_name}.vmat"


def rect_uv( atlas, name ):
    """ An atlas entry's ( u0, v0, u1, v1 ), v up from the picture's bottom. """
    W, H, rects = ATLASES[atlas]
    x0, y0, x1, y1 = rects[name]
    return ( x0 / W, 1.0 - y1 / H, x1 / W, 1.0 - y0 / H )


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def save_grey( path, a ):
    Image.fromarray( np.clip( np.rint( np.asarray( a, float ) * 255 ), 0, 255 ).astype( np.uint8 ), "L" ).save(
        path, optimize=True )


def save_rgb( path, a ):
    Image.fromarray( np.clip( np.rint( a ), 0, 255 ).astype( np.uint8 ), "RGB" ).save( path, optimize=True )


def vmat( paint_name, texture, metalness, extra ):
    lines_ = [ "// Tools/stillhouse_materials.py", '"Layer0"', "{", '    shader "shaders/complex.shader"',
               '    F_SPECULAR "1"' ]
    if paint_name in ALPHA_TESTED:
        lines_ += [ '    F_ALPHA_TEST "1"', '    F_RENDER_BACKFACES "1"',
                    f'    TextureTranslucency "{RESOURCE_DIR}/{texture}_trans.png"',
                    '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"' ]
    if paint_name in ILLUM:
        mask = f"{RESOURCE_DIR}/{texture}_illum.png" if "illum" in extra else "[1.000000 1.000000 1.000000 0.000000]"
        lines_ += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{mask}"',
                    f'    g_flSelfIllumBrightness "{ILLUM[paint_name]:.2f}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                    '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines_ += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{METALNESS.get( paint_name, metalness ):.2f}"',
                f'    TextureColor "{RESOURCE_DIR}/{paint_name}_color.png"',
                f'    TextureNormal "{RESOURCE_DIR}/{texture}_normal.png"',
                f'    TextureRoughness "{RESOURCE_DIR}/{texture}_rough.png"',
                f'    TextureAmbientOcclusion "{DEFAULT_AO}"', '    g_vColorTint "[1.0 1.0 1.0 1.0]"',
                '    g_flModelTintAmount "1.0"', "}" ]
    return "\n".join( lines_ ) + "\n"


def glass_vmat( paint_name, tint, absorption ):
    """ Clear glass, its colour the light it lets through. """
    r, g, b = tint
    return ( '// Tools/stillhouse_materials.py\n'
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


def textured_glass_vmat( paint_name, texture, absorption ):
    """ Glass with a picture (the dusty windows): the colour is the light let through, and the roughness blurs what's
    behind. """
    return ( '// Tools/stillhouse_materials.py\n'
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


def sea_vmat():
    """ The sea's surface, on Ridgeback's river shader with the engine's water normals (no picture of its own). """
    return ( '// Tools/stillhouse_materials.py\n'
             '"Layer0"\n'
             "{\n"
             '    shader "shaders/ridgeback_river.shader"\n'
             '    NormalA "materials/water/water1_normal.jpg"\n'
             '    NormalB "materials/water/water2_normal.jpg"\n'
             '    g_vWaterColor "[0.035 0.075 0.085]"\n'
             '    g_flFlowSpeed "0.012"\n'
             "}\n" )


def write_texture( name, out_dir ):
    draw, size, seed, metalness, units = TEXTURES[name]
    rng = np.random.default_rng( seed )
    start = time.perf_counter()
    result = draw( rng, size )
    colours, rough, height, strength = result[:4]
    extra = result[4] if len( result ) > 4 else {}
    assert list( colours ) == TEXTURE_PAINTS[name], ( name, list( colours ) )
    height = np.asarray( height, float ) * np.ones( ( size, size ) )
    rough = np.asarray( rough, float ) * np.ones( ( size, size ) )
    normal = gl_normals( height, strength * size / 1024.0 )
    out_dir.mkdir( parents=True, exist_ok=True )
    save_rgb( out_dir / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    save_grey( out_dir / f"{name}_rough.png", np.clip( rough, 0, 1 ) )
    if "trans" in extra:
        save_grey( out_dir / f"{name}_trans.png", np.clip( extra["trans"], 0, 1 ) )
    if "illum" in extra:
        save_grey( out_dir / f"{name}_illum.png", np.clip( extra["illum"], 0, 1 ) )
    shifts = []
    for paint_name, colour in colours.items():
        colour = np.clip( np.asarray( colour, float ), 0, 255 )
        if paint_name in MEANS:
            drawn = colour.reshape( -1, 3 ).mean( 0 )
            colour = match_mean( colour, MEANS[paint_name] )
            shifts.append( f"{paint_name} {tuple( int( round( v ) ) for v in drawn )}" )
            colours[paint_name] = colour
        save_rgb( out_dir / f"{paint_name}_color.png", colour )
        if paint_name in TEXTURED_GLASS:
            text = textured_glass_vmat( paint_name, name, TEXTURED_GLASS[paint_name] )
        else:
            text = vmat( paint_name, name, metalness, extra )
        ( out_dir / f"{paint_name}.vmat" ).write_text( text, encoding="utf-8", newline="\n" )
    scale = "explicit UVs" if name in ATLAS_TEXTURES else f"{units:g} units a tile, {size / units:.1f} px an inch"
    drawn = f"; drawn means {', '.join( shifts )}" if shifts else ""
    print( f"wrote {name}: {', '.join( colours )} ({size} px, {scale}, {time.perf_counter() - start:.1f} s{drawn})",
           flush=True )
    return colours, normal, extra


def write_glass( out_dir ):
    out_dir.mkdir( parents=True, exist_ok=True )
    for paint_name, ( tint, absorption ) in GLASS.items():
        ( out_dir / f"{paint_name}.vmat" ).write_text( glass_vmat( paint_name, tint, absorption ), encoding="utf-8",
                                                       newline="\n" )
    for paint_name in SEA:
        ( out_dir / f"{paint_name}.vmat" ).write_text( sea_vmat(), encoding="utf-8", newline="\n" )
    print( f"wrote glass and sea: {', '.join( list( GLASS ) + list( SEA ) )}" )


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


def write_sheet( results, path, tile=384, cols=8 ):
    tiles = []
    for name, ( colours, normal, extra ) in results.items():
        for paint_name, colour in colours.items():
            img = Image.fromarray( lit( colour, normal, extra.get( "trans" ) ).astype( np.uint8 ) )
            img = img.resize( ( tile, tile ), Image.LANCZOS )
            d = ImageDraw.Draw( img )
            d.text( ( 7, 7 ), paint_name, fill=( 0, 0, 0 ) )
            d.text( ( 6, 6 ), paint_name, fill=( 255, 255, 255 ) )
            tiles.append( img )
    cols = min( cols, max( 1, len( tiles ) ) )
    rows = ( len( tiles ) + cols - 1 ) // cols
    sheet = Image.new( "RGB", ( tile * cols, tile * rows ), ( 16, 16, 16 ) )
    for k, t in enumerate( tiles ):
        sheet.paste( t, ( tile * ( k % cols ), tile * ( k // cols ) ) )
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
    start = time.perf_counter()
    results = { name: write_texture( name, out_dir ) for name in names }
    write_glass( out_dir )
    print( f"done in {time.perf_counter() - start:.0f} s" )
    if args.sheet:
        write_sheet( results, args.sheet )


TEXTURES = _texture_table()

if __name__ == "__main__":
    main()
