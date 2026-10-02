"""
Belltower's fronts: the pictures drawn once across a polygon (map_kit's decal paints) for the houses' shutters, windows,
doors and shop signs, and the cut-out cards for the iron railings, the plants and the painted lettering. Drawn with
numpy and PIL into Assets/materials/belltower/ beside Tools/belltower_finishes.py's plaster, in the project's own fonts.

    python Tools/belltower_fronts.py [name ...] [--out <dir>] [--sheet <jpg>]

Each picture is drawn in inches (its real size, below) and stretched across whatever polygon carries it, so it's
drawn for the size it's used at:
- louvre_<colour>: one leaf of a pair of louvred shutters (persiane), 22 x 72: stiles and rails round two panels of
  slats sloping out and down, the paint faded by the sun, chipped at the edges to the grey wood, dirt in the corners.
  louvre_pair_<colour> is a shut pair, 44 x 72.
- window_<a-d>: what's seen through a house's window, 44 x 72: a dark room behind lace half-curtains, a drawn sheer,
  heavy curtains held back, or a blind half down. Smooth, so the glass carries the sky's reflection.
- shopfront_<a-c>: a shop's window, 112 x 104: shelves of goods, a counter, warm light.
- door_<a-e>: a pair of panelled street doors, 48 x 94, painted or varnished, with a knob, a letter plate and wear.
- sign_<k>: a painted shop sign board, 120 x 22 (SIGNS: the west half's ten, then the east half's ten, which the east's
  mirror repaints them to).
- letters_<k>: the same name as cut-out lettering, for an awning's valance.
- railing: a wrought-iron balcony railing, cut out, one 36-inch bay of it across, 36 high (repeats along).
- geranium, ivy, bougainvillea: cut-out cards of planting.
- chalkboard_<a-b>, plaque_<k>, banner_<team>: a menu board, the street-name plaques and the town's banner.
- lantern_glass, lamp_bulb, lamp_reflector: the lamps' lit glass, bare bulbs and the dish lamps' enamel, self-lit
  (LAMP_GLOW): the town's lamps are on by day.
- insegna_<k>: the Inn's and the Tavern's hanging signs, 30 x 22, a name over an emblem (grapes, a tankard).

Only the town's names are written: generic Italian shop names and street names, nothing anyone owns.
"""
import argparse
import math
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import belltower_materials as M

FONTS = M.ROOT / "Assets/fonts"
SHEETS = {}


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

def font( name, size ):
    return ImageFont.truetype( str( FONTS / f"{name}.ttf" ), int( size ) )


def field( rng, shape, sigma ):
    """ Smooth noise, unit deviation; sigma in px (one, or ( rows, columns ) for grain). Wide blurs are done on fewer px
    and scaled up: a 300 px blur straight on a 2048 picture takes seconds. """
    sy, sx = ( sigma, sigma ) if np.isscalar( sigma ) else sigma
    fy, fx = max( sy / 3.0, 1.0 ), max( sx / 3.0, 1.0 )
    h, w = shape
    sh, sw = int( math.ceil( h / fy ) ) + 6, int( math.ceil( w / fx ) ) + 6
    f = ndimage.gaussian_filter( rng.standard_normal( ( sh, sw ) ), ( sy / fy, sx / fx ), mode="reflect" )[3:-3, 3:-3]
    if f.shape != ( h, w ):
        f = np.asarray( Image.fromarray( f.astype( np.float32 ), "F" ).resize( ( w, h ), Image.BICUBIC ) ).astype( float )
    return ( f - f.mean() ) / ( f.std() + 1e-9 )


def fbm( rng, shape, sigmas, weights=None ):
    weights = weights or [ 0.5 ** k for k in range( len( sigmas ) ) ]
    f = sum( w * field( rng, shape, s ) for s, w in zip( sigmas, weights ) )
    return f / f.std()


def grid( w, h, inches ):
    """ Each px's position in inches: x from the left, y up from the bottom, and the px per inch each way. """
    sx, sy = w / inches[0], h / inches[1]
    x = ( np.arange( w ) + 0.5 ) / sx
    y = ( h - 0.5 - np.arange( h ) ) / sy
    X, Y = np.meshgrid( x, y )
    return X, Y, sx, sy


def normals( height, sx, sy, strength=1.0 ):
    """ OpenGL tangent normals from a height field in inches, sx / sy px to the inch across / up. """
    gy, gx = np.gradient( height )
    hx = gx * sx * strength
    hy = -gy * sy * strength       # rows run down, y up
    n = np.stack( [ -hx, -hy, np.ones_like( height ) ], -1 )
    return n / np.linalg.norm( n, axis=-1, keepdims=True )


def occlusion( height, sx, radii=( 0.3, 1.0 ), weights=( 1.0, 0.5 ), strength=1.6 ):
    hollow = sum( w * np.maximum( ndimage.gaussian_filter( height, r * sx, mode="nearest" ) - height, 0 )
                  for r, w in zip( radii, weights ) )
    return np.clip( np.exp( -strength * hollow ), 0, 1 ), hollow


def mix( a, b, t ):
    """ M.lerp for grey and colour alike: t gains a channel axis only when a or b is a colour. """
    t = np.asarray( t, float )
    if t.ndim == 2 and ( np.ndim( a ) in ( 1, 3 ) or np.ndim( b ) in ( 1, 3 ) ):
        t = t[..., None]
    return a + ( np.asarray( b, float ) - a ) * t


def lin( rgb ):
    return M.to_linear( rgb )


def box_mask( X, Y, x0, x1, y0, y1, soft=0.04 ):
    return ( M.smoothstep( x0 - soft, x0 + soft, X ) * M.smoothstep( x1 + soft, x1 - soft, X )
             * M.smoothstep( y0 - soft, y0 + soft, Y ) * M.smoothstep( y1 + soft, y1 - soft, Y ) )


def inset_distance( X, Y, x0, x1, y0, y1 ):
    """ How far inside the rectangle each px is (negative outside), in inches. """
    return np.minimum( np.minimum( X - x0, x1 - X ), np.minimum( Y - y0, y1 - Y ) )


def span( X, Y, x0, x1, y0, y1, pad=0.1 ):
    """ The rows and columns a rectangle (inches) covers, to draw small things on a slice of the picture. """
    cols = np.nonzero( ( X[0] >= x0 - pad ) & ( X[0] <= x1 + pad ) )[0]
    rows = np.nonzero( ( Y[:, 0] >= y0 - pad ) & ( Y[:, 0] <= y1 + pad ) )[0]
    if len( cols ) == 0 or len( rows ) == 0:
        return None
    return slice( rows[0], rows[-1] + 1 ), slice( cols[0], cols[-1] + 1 )


def paint_rect( c, X, Y, x0, x1, y0, y1, colour, amount=1.0, soft=0.05 ):
    """ Paint a soft-edged rectangle onto c in place; colour is an RGB or a function of the slice's ( X, Y ). """
    s = span( X, Y, x0, x1, y0, y1, soft * 2 )
    if s is None:
        return None
    xs, ys = X[s], Y[s]
    m = box_mask( xs, ys, x0, x1, y0, y1, soft ) * amount
    col = colour( xs, ys ) if callable( colour ) else colour
    c[s] = mix( c[s], col, m )
    return s


def pot( n ):
    """ The power of two nearest n (in octaves). """
    return 1 << max( 0, int( round( math.log2( n ) ) ) )


def to_pot( a ):
    """ A map (HxW or HxWxC) resampled to power-of-two sides. The engine's mip filters for cut-outs (AlphaWeighted) and
    normal maps (HemiOctIsoRoughness) refuse anything else, and the material then fails to compile. A picture is
    stretched across its polygon by its UVs, so its px needn't be square. """
    a = np.asarray( a, float )
    if a.ndim < 2:
        return a
    h, w = a.shape[:2]
    H, W = pot( h ), pot( w )
    if ( H, W ) == ( h, w ):
        return a
    if a.ndim == 3:
        return np.stack( [ to_pot( a[..., k] ) for k in range( a.shape[2] ) ], -1 )
    return np.asarray( Image.fromarray( a.astype( np.float32 ), "F" ).resize( ( W, H ), Image.LANCZOS ) ).astype( float )


def write( name, colour, normal, rough, ao, alpha=None, cutout=True, backfaces=False, metal=0.0, illum=None,
           illum_mask=None ):
    """ The maps and .vmat of one material. colour: linear 0..1 (HxWx3). alpha: 0..1 (cut out at 0.5, or blended when
    cutout is False). illum: the brightness the colour glows at, where illum_mask (0..1) says, else by the colour map.
    Every map is written at power-of-two sides. """
    colour, rough, ao = to_pot( colour ), to_pot( rough ), to_pot( ao )
    normal = to_pot( normal )
    normal = normal / np.maximum( np.linalg.norm( normal, axis=-1, keepdims=True ), 1e-6 )
    if alpha is not None:
        alpha = to_pot( alpha )
    out = M.OUT_DIR
    M.save_rgb( out / f"{name}_color.png", M.to_srgb( np.clip( colour, 0, 1 ) ) )
    M.save_rgb( out / f"{name}_normal.png", ( normal * 0.5 + 0.5 ) * 255 )
    M.save_grey( out / f"{name}_rough.png", np.clip( rough, 0, 1 ) )
    M.save_grey( out / f"{name}_ao.png", np.clip( ao, 0, 1 ) )
    r = M.RESOURCE_DIR
    lines = [ "// Tools/belltower_fronts.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if alpha is not None:
        M.save_grey( out / f"{name}_alpha.png", np.clip( alpha, 0, 1 ) )
        if cutout:
            lines += [ '    F_ALPHA_TEST "1"', '    g_flAlphaTestReference "0.5"', '    g_flAntiAliasedEdgeStrength "1"' ]
        else:
            lines += [ '    F_TRANSLUCENT "1"' ]
        lines += [ f'    TextureTranslucency "{r}/{name}_alpha.png"' ]
    if backfaces:
        lines += [ '    F_RENDER_BACKFACES "1"' ]
    if illum:
        mask = f"{r}/{name}_color.png"
        if illum_mask is not None:
            M.save_grey( out / f"{name}_illum.png", np.clip( to_pot( illum_mask ), 0, 1 ) )
            mask = f"{r}/{name}_illum.png"
        lines += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{mask}"',
                   f'    g_flSelfIllumBrightness "{illum:.2f}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                   '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metal:.2f}"',
               f'    TextureColor "{r}/{name}_color.png"', f'    TextureNormal "{r}/{name}_normal.png"',
               f'    TextureRoughness "{r}/{name}_rough.png"', f'    TextureAmbientOcclusion "{r}/{name}_ao.png"',
               '    g_vColorTint "[1.0 1.0 1.0 1.0]"', '    g_flModelTintAmount "1.0"', "}", "" ]
    M.write_vmat( name, "\n".join( lines ) )
    SHEETS[name] = ( colour, normal, alpha )


def seed( name ):
    return zlib.crc32( name.encode() )


# ---------------------------------------------------------------------------------------------------------------------
# Paint on wood

WOOD_BARE = ( 150, 140, 124 )      # weathered softwood, silver-grey where the paint's gone


def wood_grain( rng, shape, along, sx, sy ):
    """ Grain running along 'x' or 'y': long streaks, unit deviation. """
    if along == "y":
        return fbm( rng, shape, [ ( 8 * sy, 0.3 * sx ), ( 2.5 * sy, 0.1 * sx ) ], [ 1.0, 0.5 ] )
    return fbm( rng, shape, [ ( 0.3 * sy, 8 * sx ), ( 0.1 * sy, 2.5 * sx ) ], [ 1.0, 0.5 ] )


def paint_weathering( rng, shape, paint, sx, sy, edge, grain, sun, chip_bias=0.0 ):
    """ The colour of old gloss paint on wood: faded and chalky where the sun gets it (sun 0..1), chipped back to the
    wood near edges (edge: inches to the nearest arris), grain showing through. Returns ( colour, rough, chipped ). """
    h, w = shape
    base = lin( paint )
    mottle = fbm( rng, shape, [ 6 * sx, 2 * sx ] )
    fade = np.clip( 0.18 + 0.32 * sun + 0.08 * mottle, 0, 0.8 )
    faded = base * 0.55 + lin( ( 196, 192, 180 ) ) * 0.45
    c = mix( base[None, None, :] * np.ones( ( h, w, 1 ) ), faded, fade )
    c = c * ( 1 + 0.06 * grain )[..., None]
    # Chips: where the paint's come away. Paint fails in patches (where the wood stayed wet longest, where the sun
    # cooks it), and in a patch first at the edges and along the grain; elsewhere it holds.
    patch = M.smoothstep( 0.4, 1.6, fbm( rng, shape, [ 7 * sx, 2.5 * sx ] ) + chip_bias )
    flakes = fbm( rng, shape, [ 0.5 * sx, 0.18 * sx ], [ 1.0, 0.6 ] ) + 0.5 * grain
    chip_field = flakes + 1.0 * np.exp( -np.maximum( edge, 0 ) / 0.3 ) + 2.2 * patch
    chipped = M.smoothstep( 2.75, 2.9, chip_field )
    bare = lin( WOOD_BARE ) * ( 1 + 0.18 * grain )[..., None]
    c = mix( c, bare, chipped )
    # The paint's lifted edge round each chip, a touch lighter.
    rim = np.clip( ndimage.gaussian_filter( chipped, 0.08 * sx ) - chipped, 0, 1 ) * 2.5
    c = mix( c, c * 1.25, np.clip( rim, 0, 1 ) * 0.5 )
    rough = 0.52 + 0.25 * fade + 0.04 * mottle
    rough = rough * ( 1 - chipped ) + 0.86 * chipped
    return c, rough, chipped


# ---------------------------------------------------------------------------------------------------------------------
# Louvred shutters

LOUVRE_PAINTS = {
    "green": ( 58, 96, 66 ),
    "brown": ( 96, 64, 42 ),
    "blue": ( 66, 98, 124 ),
    "red": ( 120, 48, 40 ),
}
LEAF = ( 22.0, 72.0 )


def louvre_leaf( paint, rng, w=512, h=1536 ):
    """ One leaf: height in inches, colour (linear), roughness, AO. """
    X, Y, sx, sy = grid( w, h, LEAF )
    stile, top, bottom, rail, rail_z = 2.3, 3.0, 4.6, 2.6, 31.0
    lw, lh = LEAF
    panels = [ ( bottom, rail_z - rail / 2 ), ( rail_z + rail / 2, lh - top ) ]
    in_panel = np.zeros( ( h, w ), bool )
    for y0, y1 in panels:
        in_panel |= ( X > stile ) & ( X < lw - stile ) & ( Y > y0 ) & ( Y < y1 )
    # The frame: flat, its arrises rounded over.
    frame_edge = np.full( ( h, w ), 99.0 )
    frame_edge = np.minimum( frame_edge, np.minimum( X, lw - X ) )
    frame_edge = np.minimum( frame_edge, np.minimum( Y, lh - Y ) )
    for y0, y1 in panels:
        d = -inset_distance( X, Y, stile, lw - stile, y0, y1 )
        frame_edge = np.where( in_panel, frame_edge, np.minimum( frame_edge, np.where( d > 0, d, 99 ) ) )
    height = np.where( in_panel, 0.0, -0.18 * np.exp( -np.maximum( frame_edge, 0 ) / 0.12 ) )
    # The slats: 1.55 apart, each sloping out and down, a dark slit over each where it meets the one above.
    pitch = 1.55
    slat_s = np.zeros( ( h, w ) )
    for y0, y1 in panels:
        inside = in_panel & ( Y > y0 ) & ( Y < y1 )
        s = ( ( y1 - Y ) % pitch ) / pitch
        slat_s = np.where( inside, s, slat_s )
    slat_h = -0.62 + 0.5 * slat_s - 0.08 * ( slat_s > 0.93 ) - 0.25 * np.exp( -slat_s / 0.03 )
    height = np.where( in_panel, slat_h, height )
    slit = in_panel & ( slat_s < 0.06 )

    edge = np.where( in_panel, np.minimum( slat_s, 1 - slat_s ) * pitch * 0.6, frame_edge )
    # The stiles run the leaf's height, the rails and slats across between them.
    grain = np.where( ( X < stile ) | ( X > lw - stile ),
                      wood_grain( rng, ( h, w ), "y", sx, sy ), wood_grain( rng, ( h, w ), "x", sx, sy ) )
    # The slats' sloping faces get the sun; the rails and stiles less so.
    sun = np.where( in_panel, 0.55 + 0.35 * slat_s, 0.35 ) + 0.15 * M.smoothstep( 20, 70, Y )
    c, rough, chipped = paint_weathering( rng, ( h, w ), paint, sx, sy, edge, grain, sun,
                                          chip_bias=0.5 * M.smoothstep( 8, 0, Y ) )
    height = height - 0.03 * chipped
    ao, hollow = occlusion( height, sx, ( 0.25, 0.9 ), ( 1.0, 0.5 ), 2.2 )
    c = c * ao[..., None]
    c = np.where( slit[..., None], lin( ( 14, 13, 12 ) ), c )
    # Dirt: splashed up the bottom rail, collected along the slats' backs.
    dirt = 0.35 * M.smoothstep( 6, 0, Y ) * ( 0.7 + 0.3 * fbm( rng, ( h, w ), [ 0.6 * sx ] ) )
    c = c * ( 1 - dirt )[..., None]
    rough = np.where( slit, 0.95, rough )
    return height, c, rough, ao


def louvres():
    for colour, paint in LOUVRE_PAINTS.items():
        rng = np.random.default_rng( seed( "louvre_" + colour ) )
        height, c, rough, ao = louvre_leaf( paint, rng )
        X, Y, sx, sy = grid( c.shape[1], c.shape[0], LEAF )
        write( f"louvre_{colour}", c, normals( height, sx, sy ), rough, ao )
        # A shut pair: two leaves, the meeting stiles rebated, an iron catch across them.
        leaves = [ louvre_leaf( paint, np.random.default_rng( seed( f"louvre_pair_{colour}_{k}" ) ) ) for k in ( 0, 1 ) ]
        height = np.concatenate( [ leaves[0][0], leaves[1][0] ], 1 )
        c = np.concatenate( [ leaves[0][1], leaves[1][1] ], 1 )
        rough = np.concatenate( [ leaves[0][2], leaves[1][2] ], 1 )
        ao = np.concatenate( [ leaves[0][3], leaves[1][3] ], 1 )
        X, Y, sx, sy = grid( c.shape[1], c.shape[0], ( 2 * LEAF[0], LEAF[1] ) )
        meet = np.abs( X - LEAF[0] ) < 0.06
        c = np.where( meet[..., None], lin( ( 16, 15, 14 ) ), c )
        catch = box_mask( X, Y, LEAF[0] - 1.6, LEAF[0] + 1.6, 33.0, 34.0 )
        height = height + 0.3 * catch
        c = mix( c, lin( ( 46, 42, 40 ) ), catch )
        rough = mix( rough, 0.5, catch )
        write( f"louvre_pair_{colour}", c, normals( height, sx, sy ), rough, ao )


# ---------------------------------------------------------------------------------------------------------------------
# Street doors

DOORS = {
    "a": ( "paint", ( 46, 78, 56 ) ),       # dark green
    "b": ( "varnish", ( 92, 56, 32 ) ),     # varnished walnut
    "c": ( "paint", ( 92, 36, 30 ) ),       # oxblood
    "d": ( "paint", ( 58, 74, 88 ) ),       # blue-grey
    "e": ( "varnish", ( 120, 80, 46 ) ),    # oak, the varnish weathered
}
DOOR = ( 48.0, 94.0 )


def door( kind, paint, rng, w=512, h=1024 ):
    X, Y, sx, sy = grid( w, h, DOOR )
    dw, dh = DOOR
    leaf = dw / 2
    lx = np.where( X < leaf, X, X - leaf )         # across each leaf
    stile, top, lock_lo, lock_hi, bottom = 4.0, 5.0, 36.0, 44.0, 9.0
    panels = [ ( stile, leaf - stile, bottom, lock_lo ), ( stile, leaf - stile, lock_hi, dh - top ) ]
    height = np.zeros( ( h, w ) )
    edge = np.minimum( np.minimum( lx, leaf - lx ), np.minimum( Y, dh - Y ) )
    in_any = np.zeros( ( h, w ), bool )
    for x0, x1, y0, y1 in panels:
        d = inset_distance( lx, Y, x0, x1, y0, y1 )
        inside = d > 0
        in_any |= inside
        # A sunk moulding round a raised field: a 0.45 deep quirk, a bead, then the field's bevel up 0.4 over 2.
        moulding = -0.45 * M.smoothstep( 0.0, 0.3, d ) + 0.18 * M.smoothstep( 0.5, 0.75, d ) * M.smoothstep( 1.3, 0.9, d )
        field_up = 0.4 * M.smoothstep( 1.3, 3.2, d )
        height = np.where( inside, moulding + field_up, height )
        edge = np.where( inside, np.minimum( np.abs( d - 0.75 ), np.abs( d - 3.2 ) + 0.3 ), np.minimum( edge, np.where( d > -0.5, -d + 0.2, 99 ) ) )
    # The leaves meet in a rebate.
    meet = np.abs( X - leaf ) < 0.07
    height = height - 0.3 * meet
    edge = np.minimum( edge, np.abs( X - leaf ) )
    grain_v = wood_grain( rng, ( h, w ), "y", sx, sy )
    grain_h = wood_grain( rng, ( h, w ), "x", sx, sy )
    rails = ~in_any & ( ( Y < bottom ) | ( Y > dh - top ) | ( ( Y > lock_lo ) & ( Y < lock_hi ) ) ) & ( lx > stile ) & ( lx < leaf - stile )
    grain = np.where( rails, grain_h, grain_v )
    sun = 0.3 + 0.4 * M.smoothstep( 30, 90, Y )
    if kind == "paint":
        c, rough, chipped = paint_weathering( rng, ( h, w ), paint, sx, sy, edge, grain, sun,
                                              chip_bias=0.7 * M.smoothstep( 10, 0, Y ) )
    else:
        base = lin( paint )
        figure = 0.18 * grain + 0.08 * fbm( rng, ( h, w ), [ ( 30 * sy, 3 * sx ) ] )
        c = base[None, None, :] * ( 1 + figure )[..., None]
        weather = np.clip( 0.25 * sun + 0.35 * M.smoothstep( 12, 0, Y ) + 0.1 * fbm( rng, ( h, w ), [ 4 * sx ] ), 0, 1 )
        c = mix( c, lin( ( 140, 118, 92 ) ) * ( 1 + 0.15 * grain )[..., None], 0.55 * weather )
        rough = 0.42 + 0.35 * weather
        chipped = np.zeros( ( h, w ) )
    # Ironmongery: a brass knob on the meeting stile, a letter plate, a keyhole escutcheon, iron studs low down.
    knob_d = np.hypot( ( X - ( leaf + 2.0 ) ) * 1.0, Y - 40.0 )
    knob = M.smoothstep( 1.25, 1.1, knob_d )
    height = height + 0.9 * np.sqrt( np.clip( 1 - ( knob_d / 1.25 ) ** 2, 0, 1 ) )
    plate = box_mask( X, Y, leaf - 9.5, leaf - 3.5, 39.2, 40.8, 0.05 )
    slot = box_mask( X, Y, leaf - 9.0, leaf - 4.0, 39.75, 40.25, 0.03 )
    escutcheon = M.smoothstep( 0.55, 0.45, np.hypot( ( X - ( leaf + 2.0 ) ) * 1.6, Y - 36.0 ) )
    height = height + 0.12 * plate - 0.2 * slot + 0.1 * escutcheon
    brass = lin( ( 150, 118, 62 ) ) * ( 1 + 0.15 * fbm( rng, ( h, w ), [ 0.4 * sx ] ) )[..., None]
    metal = np.clip( knob + plate + escutcheon, 0, 1 )
    c = mix( c, brass, metal )
    c = np.where( slot[..., None] > 0.5, lin( ( 20, 18, 16 ) ), c )
    rough = mix( rough, 0.3, metal )
    ao, hollow = occlusion( height, sx, ( 0.2, 0.8 ), ( 1.0, 0.5 ), 2.0 )
    c = c * ao[..., None]
    c = np.where( meet[..., None], lin( ( 14, 12, 11 ) ), c )
    # Scuffed and splashed at the foot, a dark band where hands push at the lock rail.
    c = c * ( 1 - 0.3 * M.smoothstep( 8, 0, Y ) * ( 0.6 + 0.4 * fbm( rng, ( h, w ), [ 0.5 * sx ] ) ) )[..., None]
    push = np.exp( -( ( Y - 42 ) / 6 ) ** 2 ) * np.exp( -( ( X - leaf ) / 7 ) ** 2 )
    c = c * ( 1 - 0.18 * push )[..., None]
    return height, c, rough, ao


PLANK_DOORS = {
    "f": ( 96, 68, 46 ),        # oiled softwood gone brown
    "g": ( 128, 118, 104 ),     # bare boards, silvered by the weather
}


def plank_door( wood, rng, w=512, h=1024 ):
    """ A boarded door: vertical boards of mixed widths with V-joints, nailed to battens behind (the rows of nail
    heads), two iron strap hinges with rust run down from them, a ring pull and a lock plate. """
    X, Y, sx, sy = grid( w, h, DOOR )
    dw, dh = DOOR
    edges = [ 0.0 ]
    while edges[-1] < dw - 0.01:
        edges.append( min( dw, edges[-1] + rng.uniform( 5.0, 7.5 ) ) )
    if len( edges ) > 2 and edges[-1] - edges[-2] < 3.0:
        edges.pop( -2 )
    edges = np.array( edges )
    board = np.clip( np.searchsorted( edges, X, side="right" ) - 1, 0, len( edges ) - 2 )
    left, right = edges[board], edges[board + 1]
    to_joint = np.minimum( X - left, right - X )
    across = ( X - left ) / ( right - left )
    height = -0.35 * np.exp( -np.maximum( to_joint, 0 ) / 0.1 ) - 0.06 * ( 2 * across - 1 ) ** 2     # V-joints, cupped
    grain = wood_grain( rng, ( h, w ), "y", sx, sy )
    tone = rng.uniform( 0.82, 1.12, len( edges ) )[board]
    base = lin( wood ) * tone[..., None] * ( 1 + 0.22 * grain )[..., None]
    # Weathering: the boards silver and open up where the rain gets them, from the foot up.
    weather = np.clip( 0.25 + 0.5 * M.smoothstep( 30, 0, Y ) + 0.15 * fbm( rng, ( h, w ), [ ( 12 * sy, 2 * sx ) ] ), 0, 1 )
    c = mix( base, lin( ( 136, 128, 116 ) ) * ( 1 + 0.25 * grain )[..., None], 0.5 * weather )
    height = height + 0.04 * grain * weather
    # The battens' nail heads, and the straps' own.
    nails = np.zeros( ( h, w ) )
    straps = np.zeros( ( h, w ) )
    for yc in ( 15.0, 47.0, 79.0 ):
        strap = yc != 47.0
        if strap:
            d_end = np.hypot( X - 33.0, ( Y - yc ) * 1.0 )
            s = np.clip( box_mask( X, Y, -1.0, 33.0, yc - 1.0, yc + 1.0, 0.04 ) + M.smoothstep( 1.65, 1.5, d_end ), 0, 1 )
            straps = np.maximum( straps, s )
        for xc in np.arange( 2.5, dw - 1.0, 4.0 if strap else 6.0 ):
            if strap and xc > 33.5:
                continue
            nails = np.maximum( nails, np.sqrt( np.clip( 1 - ( np.hypot( X - xc, Y - yc ) / 0.32 ) ** 2, 0, 1 ) ) )
    ring_d = np.hypot( X - 40.0, Y - 38.5 )
    ring = M.smoothstep( 0.3, 0.15, np.abs( ring_d - 1.9 ) ) * ( Y < 40.5 )
    boss = M.smoothstep( 0.75, 0.6, np.hypot( X - 40.0, Y - 40.5 ) )
    lock = box_mask( X, Y, 38.0, 42.0, 31.0, 36.0, 0.05 )
    keyhole = M.smoothstep( 0.3, 0.2, np.hypot( X - 40.0, Y - 34.2 ) ) + box_mask( X, Y, 39.85, 40.15, 32.6, 34.2, 0.02 )
    iron = np.clip( straps + nails + ring + boss + lock, 0, 1 )
    height = height + 0.22 * straps + 0.3 * nails + 0.35 * ring + 0.3 * boss + 0.12 * lock - 0.2 * keyhole
    rust = M.smoothstep( 0.2, 1.2, fbm( rng, ( h, w ), [ 0.6 * sx, 0.2 * sx ] ) )
    metal_c = mix( lin( ( 36, 34, 33 ) ), lin( ( 104, 56, 32 ) ), 0.7 * rust )
    c = mix( c, metal_c, iron )
    c = np.where( ( keyhole > 0.5 )[..., None], lin( ( 10, 9, 8 ) ), c )
    # Rust run down the boards from each strap and nail row.
    run = np.zeros( ( h, w ) )
    streak = M.smoothstep( 0.6, 1.8, fbm( rng, ( h, w ), [ ( 6 * sy, 0.25 * sx ) ] ) )
    for yc in ( 15.0, 47.0, 79.0 ):
        below = yc - 1.0 - Y
        run = np.maximum( run, np.where( below > 0, np.exp( -below / 7.0 ), 0 ) * streak * ( X < 34 if yc != 47.0 else 1 ) )
    stain = run * ( 1 - iron )
    c = c * ( 1 - 0.35 * stain )[..., None] * ( 1 + 0.25 * stain[..., None] * np.array( ( 0.5, 0.1, -0.2 ) ) )
    rough = 0.82 + 0.08 * weather - 0.2 * iron * ( 1 - rust )
    ao, _ = occlusion( height, sx, ( 0.2, 0.8 ), ( 1.0, 0.5 ), 2.0 )
    c = c * ao[..., None]
    c = c * ( 1 - 0.3 * M.smoothstep( 8, 0, Y ) * ( 0.6 + 0.4 * fbm( rng, ( h, w ), [ 0.5 * sx ] ) ) )[..., None]
    return height, c, rough, ao


def doors():
    for key, ( kind, paint ) in DOORS.items():
        rng = np.random.default_rng( seed( "door_" + key ) )
        height, c, rough, ao = door( kind, paint, rng )
        X, Y, sx, sy = grid( c.shape[1], c.shape[0], DOOR )
        write( f"door_{key}", c, normals( height, sx, sy ), rough, ao )
    for key, wood in PLANK_DOORS.items():
        rng = np.random.default_rng( seed( "door_" + key ) )
        height, c, rough, ao = plank_door( wood, rng )
        X, Y, sx, sy = grid( c.shape[1], c.shape[0], DOOR )
        write( f"door_{key}", c, normals( height, sx, sy ), rough, ao )


# ---------------------------------------------------------------------------------------------------------------------
# Windows: the room behind the glass

WINDOW = ( 44.0, 72.0 )


def lace( X, Y, rng, x0, x1, y0, y1 ):
    """ A lace curtain's coverage (0..1). From the street its fine net reads as an even veil; what shows is the
    flowers worked into it, a denser band over the hem, the hem's scallops and the folds. """
    u, v = X - x0, Y - y0
    cell = 3.2
    row = np.floor( v / cell )
    fu = ( ( u + cell / 2 * ( row % 2 ) ) % cell ) - cell / 2
    fv = ( v % cell ) - cell / 2
    r = np.hypot( fu, fv )
    petals = 0.5 + 0.5 * np.cos( 5 * np.arctan2( fv, fu ) )
    flower = M.smoothstep( 1.05, 0.8, r - 0.3 * petals ) * ( 1 - 0.7 * M.smoothstep( 0.3, 0.15, r ) )
    hem = y0 + 0.6 + 0.9 * np.abs( np.sin( math.pi * u / 2.4 ) )
    band = M.smoothstep( 4.5, 3.5, Y - hem )
    cover = 0.66 + 0.09 * flower + 0.18 * band + 0.03 * field( rng, X.shape, X.shape[1] / ( x1 - x0 ) * 0.6 )
    folds = 0.86 + 0.14 * np.cos( 2 * math.pi * u / 3.6 + 0.5 * np.sin( Y / 9 ) )
    inside = ( X > x0 ) & ( X < x1 ) & ( Y > hem ) & ( Y < y1 )
    return np.where( inside, np.clip( cover, 0, 1 ) * folds, 0.0 )


def room( rng, X, Y, sx, w, h, warm=1.0 ):
    """ A dim room: the ceiling lit by the window, furniture shapes darker below, a doorway. """
    wy = WINDOW[1]
    base = lin( ( 30, 27, 24 ) ) * 0.9
    c = np.ones( ( h, w, 3 ) ) * base
    ceiling = M.smoothstep( 46, 66, Y )
    c = c * ( 1 + 1.4 * ceiling )[..., None]
    c = c * ( 1 + 0.12 * fbm( rng, ( h, w ), [ 6 * sx, 2 * sx ] ) )[..., None]
    # A wardrobe or a dresser's dark shape, a picture frame, a doorway's slightly lighter rectangle beyond.
    x_door = rng.uniform( 6, 30 )
    doorway = box_mask( X, Y, x_door, x_door + 10, 6, 52, 0.3 )
    c = mix( c, c * 1.6 * np.array( ( 1.0, 0.96, 0.9 ) ), 0.6 * doorway )
    furniture = box_mask( X, Y, rng.uniform( 0, 20 ), rng.uniform( 26, 44 ), 0, rng.uniform( 18, 34 ), 0.4 )
    c = mix( c, c * 0.5, furniture )
    frame_x = rng.uniform( 4, 32 )
    picture = box_mask( X, Y, frame_x, frame_x + 8, 40, 48, 0.15 ) - box_mask( X, Y, frame_x + 0.8, frame_x + 7.2, 40.8, 47.2, 0.1 )
    c = mix( c, c * 2.2 * np.array( ( 1.0, 0.85, 0.6 ) ), 0.7 * np.clip( picture, 0, 1 ) )
    return c * warm


def window( key, rng, w=512, h=840 ):
    X, Y, sx, sy = grid( w, h, WINDOW )
    c = room( rng, X, Y, sx, w, h )
    ww, wh = WINDOW
    cloth = np.zeros( ( h, w ) )
    tint = lin( ( 232, 228, 214 ) )
    if key == "a":       # lace half-curtains on rods across each sash, the top half open to the room
        cloth = lace( X, Y, rng, 0, ww, 0, 36 )
        rod = box_mask( X, Y, 0, ww, 36.0, 36.5 )
        c = mix( c, lin( ( 120, 100, 70 ) ), rod )
    elif key == "b":     # a sheer drawn right across, gathered in soft folds
        phase = 1.2 * fbm( rng, ( h, w ), [ ( 24 * sy, 4 * sx ) ] )
        folds = 0.92 + 0.08 * np.cos( 2 * math.pi * X / 3.4 + phase )
        cloth = np.clip( 0.62 * folds + 0.03 * fbm( rng, ( h, w ), [ 0.5 * sx ] ), 0, 1 ) * M.smoothstep( 0, 2, Y )
        tint = lin( ( 226, 220, 200 ) )
    elif key == "c":     # heavy curtains tied back at each side, the room dark between them
        # Each hangs 11 wide from the rod, is drawn in to 7 at its tie, 30 up, and spreads to 12 at the sill.
        reach = np.where( Y > 30, 7 + 4 * ( Y - 30 ) / ( wh - 30 ), 7 + 5 * ( 30 - Y ) / 30 )
        gathered = np.where( Y > 30, 11 / reach, 12 / reach )
        for side in ( 0, 1 ):
            across = X if side == 0 else ww - X
            folds = 0.55 + 0.45 * np.cos( 2 * math.pi * across * gathered / 2.2 ) ** 2
            cloth = np.where( across < reach, folds * M.smoothstep( 0, 0.4, reach - across ), cloth )
        tint = lin( ( 120, 36, 34 ) ) if rng.random() < 0.5 else lin( ( 46, 78, 60 ) )
    else:                # a roller blind half down, the bottom half dark, a plant on the sill
        blind = M.smoothstep( 33.5, 34.0, Y )
        cloth = blind * ( 0.92 + 0.08 * fbm( rng, ( h, w ), [ ( 0.2 * sy, 30 * sx ) ] ) )
        tint = lin( ( 214, 200, 168 ) )
        pull = box_mask( X, Y, ww / 2 - 0.6, ww / 2 + 0.6, 30.5, 34.0, 0.05 )
        c = mix( c, lin( ( 60, 50, 40 ) ), pull )
        pot_x = rng.uniform( 10, 30 )
        pot = box_mask( X, Y, pot_x, pot_x + 5, 0, 4.5, 0.1 )
        leaves = M.smoothstep( 4.2, 3.6, np.hypot( ( X - pot_x - 2.5 ) * 0.8, Y - 7 ) ) * ( fbm( rng, ( h, w ), [ 0.3 * sx ] ) > -0.3 )
        c = mix( c, lin( ( 150, 70, 46 ) ), pot )
        c = mix( c, lin( ( 30, 52, 24 ) ), leaves )
    # The cloth is lit from the window side: brighter than the room, a little translucent.
    lit = tint * ( 0.36 + 0.1 * M.smoothstep( 0, 70, Y ) )[..., None]
    c = mix( c, lit, np.clip( cloth, 0, 1 ) )
    # The glass: dust towards the corners and the bottom, a faint film.
    dist = np.minimum( np.minimum( X, ww - X ), np.minimum( Y, wh - Y ) )
    dust = np.clip( 0.5 * M.smoothstep( 3, 0, dist ) + 0.25 * M.smoothstep( 10, 0, Y ) + 0.1 * fbm( rng, ( h, w ), [ 2 * sx ] ), 0, 1 )
    c = mix( c, lin( ( 110, 104, 92 ) ) * 0.4, 0.35 * dust )
    rough = 0.06 + 0.3 * dust + 0.03 * fbm( rng, ( h, w ), [ 4 * sx ] )
    height = np.zeros( ( h, w ) )
    write( f"window_{key}", c, normals( height, sx, sy ), rough, np.ones( ( h, w ) ) )


def windows():
    for key in "abcd":
        window( key, np.random.default_rng( seed( "window_" + key ) ) )


SHOPFRONT = ( 112.0, 104.0 )


def shopfront( key, rng, w=1024, h=952 ):
    """ Shelves behind the glass down both sides and across the back, goods on them, a counter, warm light from inside.
    The bottom 24 is behind the stall riser. """
    X, Y, sx, sy = grid( w, h, SHOPFRONT )
    sw, sh = SHOPFRONT
    c = np.ones( ( h, w, 3 ) ) * lin( ( 70, 58, 44 ) )
    c = c * ( 1 + 0.6 * M.smoothstep( 60, 100, Y ) )[..., None] * ( 1 + 0.15 * fbm( rng, ( h, w ), [ 8 * sx ] ) )[..., None]
    palettes = {
        "a": [ ( 170, 40, 30 ), ( 220, 190, 60 ), ( 60, 100, 50 ), ( 230, 220, 200 ), ( 160, 110, 50 ), ( 40, 70, 130 ) ],
        "b": [ ( 60, 90, 40 ), ( 120, 30, 30 ), ( 200, 160, 70 ), ( 70, 50, 30 ), ( 210, 200, 170 ) ],
        "c": [ ( 230, 220, 205 ), ( 200, 150, 90 ), ( 180, 60, 50 ), ( 110, 140, 160 ), ( 240, 200, 120 ) ],
    }[key]
    for shelf_z in ( 34, 50, 66, 82 ):
        paint_rect( c, X, Y, 6, sw - 6, shelf_z - 0.8, shelf_z, lin( ( 96, 66, 40 ) ) )
        x = 7.0
        while x < sw - 8:
            gw = rng.uniform( 1.6, 5.0 )
            gh = rng.uniform( 4.0, 13.0 )
            col = lin( palettes[int( rng.integers( 0, len( palettes ) ) )] ) * rng.uniform( 0.7, 1.1 )
            if rng.random() < 0.4:      # a bottle: a body, a neck and a gleam down its side
                paint_rect( c, X, Y, x, x + gw * 0.7, shelf_z, shelf_z + gh * 0.65, col * 0.5, soft=0.06 )
                paint_rect( c, X, Y, x + gw * 0.25, x + gw * 0.45, shelf_z, shelf_z + gh, col * 0.5 )
                paint_rect( c, X, Y, x + gw * 0.1, x + gw * 0.2, shelf_z + 1, shelf_z + gh * 0.6, col * 1.6 + 0.05, 0.6 )
            else:                       # a tin, a box or a jar, often a label across it
                paint_rect( c, X, Y, x, x + gw, shelf_z, shelf_z + gh * 0.7, col, soft=0.06 )
                if rng.random() < 0.6:
                    paint_rect( c, X, Y, x + 0.2, x + gw - 0.2, shelf_z + gh * 0.2, shelf_z + gh * 0.45,
                                lin( ( 230, 225, 210 ) ) * 0.8, 0.8, 0.04 )
            x += gw + rng.uniform( 0.2, 1.4 )
    # The counter across the back, lit from above; a lamp's glow.
    counter = box_mask( X, Y, 30, sw - 30, 24, 38, 0.1 )
    c = mix( c, lin( ( 120, 82, 50 ) ) * ( 1 + 0.2 * fbm( rng, ( h, w ), [ ( 2 * sy, 20 * sx ) ] ) )[..., None], 0.85 * counter )
    glow = np.exp( -( ( X - sw / 2 ) ** 2 + ( Y - 96 ) ** 2 ) / ( 2 * 22.0 ** 2 ) )
    c = c * ( 1 + 1.2 * glow )[..., None] * np.array( ( 1.0, 0.92, 0.78 ) )
    c = c * 0.55
    dist = np.minimum( np.minimum( X, sw - X ), np.minimum( Y - 24, sh - Y ) )
    dust = np.clip( 0.4 * M.smoothstep( 4, 0, dist ) + 0.1 * fbm( rng, ( h, w ), [ 3 * sx ] ), 0, 1 )
    c = mix( c, lin( ( 110, 104, 92 ) ) * 0.4, 0.3 * dust )
    rough = 0.05 + 0.25 * dust
    write( f"shopfront_{key}", c, normals( np.zeros( ( h, w ) ), sx, sy ), rough, np.ones( ( h, w ) ) )


def shopfronts():
    for key in "abc":
        shopfront( key, np.random.default_rng( seed( "shopfront_" + key ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Shop signs and lettering

# ( name, the line under it or None, board, letters ): the west half's ten, then the east half's ten.
SIGNS = [
    ( "TRATTORIA", "CUCINA CASALINGA", ( 34, 66, 48 ), ( 232, 222, 192 ) ),
    ( "ALIMENTARI", None, ( 226, 214, 184 ), ( 40, 60, 44 ) ),
    ( "PANETTERIA", "PANE E FOCACCIA", ( 104, 38, 32 ), ( 226, 196, 120 ) ),
    ( "FARMACIA", None, ( 34, 50, 74 ), ( 232, 226, 210 ) ),
    ( "MACELLERIA", None, ( 112, 34, 30 ), ( 236, 226, 204 ) ),
    ( "OSTERIA", "VINI E CUCINA", ( 52, 44, 36 ), ( 214, 182, 112 ) ),
    ( "FERRAMENTA", None, ( 40, 62, 76 ), ( 232, 220, 186 ) ),
    ( "TABACCHI", None, ( 30, 32, 36 ), ( 232, 226, 210 ) ),
    ( "DROGHERIA", "COLONIALI", ( 220, 206, 168 ), ( 104, 40, 32 ) ),
    ( "MERCERIA", None, ( 66, 84, 60 ), ( 236, 226, 200 ) ),
    ( "CAFFÈ", "BAR PASTICCERIA", ( 30, 46, 72 ), ( 232, 214, 168 ) ),
    ( "FRUTTA E VERDURA", None, ( 46, 78, 48 ), ( 236, 226, 196 ) ),
    ( "VINI E OLI", None, ( 92, 30, 36 ), ( 222, 192, 120 ) ),
    ( "PASTICCERIA", None, ( 226, 214, 190 ), ( 52, 66, 96 ) ),
    ( "LATTERIA", None, ( 52, 84, 112 ), ( 236, 232, 220 ) ),
    ( "BARBIERE", None, ( 34, 38, 46 ), ( 230, 222, 200 ) ),
    ( "LIBRERIA", "LIBRI E GIORNALI", ( 62, 52, 40 ), ( 226, 210, 170 ) ),
    ( "PESCHERIA", None, ( 40, 76, 96 ), ( 234, 230, 214 ) ),
    ( "GELATERIA", "GELATO ARTIGIANALE", ( 214, 196, 160 ), ( 70, 40, 60 ) ),
    ( "SALUMERIA", None, ( 74, 34, 28 ), ( 228, 206, 150 ) ),
]
SIGN = ( 120.0, 22.0 )


def text_mask( w, h, lines, fit=0.84 ):
    """ Coverage of the text (0..1), lines of ( text, font, height share ), centred, letter-spaced, at 3x then
    reduced. """
    k = 3
    W, H = w * k, h * k
    img = Image.new( "L", ( W, H ), 0 )
    d = ImageDraw.Draw( img )
    shares = sum( s for _, _, s in lines )
    y = H * 0.5 * ( 1 - shares )
    for text, face, share in lines:
        size = int( H * share * 1.15 )
        f = font( face, size )
        track = 0.1 * size
        widths = [ d.textlength( ch, font=f ) for ch in text ]
        total = sum( widths ) + track * ( len( text ) - 1 )
        if total > W * fit:
            size = int( size * W * fit / total )
            f = font( face, size )
            track = 0.1 * size
            widths = [ d.textlength( ch, font=f ) for ch in text ]
            total = sum( widths ) + track * ( len( text ) - 1 )
        x = ( W - total ) / 2
        # Capitals centred in the line's band: the baseline half a capital's height under the band's middle.
        cap = -f.getbbox( "H", anchor="ls" )[1]
        baseline = y + H * share / 2 + cap / 2
        for ch, cw in zip( text, widths ):
            d.text( ( x, baseline ), ch, font=f, fill=255, anchor="ls" )
            x += cw + track
        y += H * share
    return np.asarray( img.resize( ( w, h ), Image.LANCZOS ) ).astype( float ) / 255.0


def sign( k, rng, w=2048, h=376 ):
    name, sub, board, letters = SIGNS[k]
    X, Y, sx, sy = grid( w, h, SIGN )
    bw, bh = SIGN
    lines = [ ( name, "Dinish-Bold", 0.5 ) ] if sub is None else [ ( name, "Dinish-Bold", 0.44 ), ( sub, "Dinish-Regular", 0.17 ) ]
    text = text_mask( w, h, lines )
    border = np.clip( box_mask( X, Y, 1.1, bw - 1.1, 1.1, bh - 1.1, 0.03 ) - box_mask( X, Y, 1.55, bw - 1.55, 1.55, bh - 1.55, 0.03 ), 0, 1 )
    edge = np.minimum( np.minimum( X, bw - X ), np.minimum( Y, bh - Y ) )
    # Moulded edge round the board, the field flat: the board's planks show through as faint joints.
    height = -0.25 * M.smoothstep( 0.9, 0.4, edge ) - 0.05 * ( np.abs( ( Y % 7.3 ) - 3.65 ) > 3.6 )
    grain = wood_grain( rng, ( h, w ), "x", sx, sy )
    sun = 0.45 + 0.25 * M.smoothstep( 0, bh, Y )
    c, rough, chipped = paint_weathering( rng, ( h, w ), board, sx, sy, edge + 0.6, grain, sun, chip_bias=-0.3 )
    ink = lin( letters ) * ( 1 + 0.05 * fbm( rng, ( h, w ), [ 0.3 * sx ] ) )[..., None]
    paint = np.clip( text + border, 0, 1 ) * ( 1 - 0.6 * chipped )
    # The letters are signwriter's paint over the board: they fade and craze a little too.
    craze = M.smoothstep( 1.9, 2.3, fbm( rng, ( h, w ), [ 0.12 * sx, 0.05 * sx ] ) )
    c = mix( c, mix( ink, ink * 0.8 + lin( ( 180, 176, 166 ) ) * 0.2, 0.3 * craze ), paint * 0.94 )
    height = height + 0.02 * paint
    ao, _ = occlusion( height, sx, ( 0.3, 1.0 ), ( 1.0, 0.5 ), 1.6 )
    c = c * ao[..., None]
    c = c * ( 1 - 0.18 * M.smoothstep( 6, 0, Y ) * ( 0.5 + 0.5 * fbm( rng, ( h, w ), [ 1.5 * sx ] ) ) )[..., None]
    rough = mix( rough, 0.5, 0.5 * paint )
    write( f"sign_{k}", c, normals( height, sx, sy ), rough, ao )


def signs():
    for k in range( len( SIGNS ) ):
        sign( k, np.random.default_rng( seed( f"sign_{k}" ) ) )


def letters( k, rng, w=2048, h=160 ):
    """ The shop's name in cream cut-out letters for its awning's valance (10 high, about 130 long). """
    name = SIGNS[k][0]
    text = text_mask( w, h, [ ( name, "Dinish-Bold", 0.62 ) ], fit=0.7 )
    X, Y, sx, sy = grid( w, h, ( 130.0, 10.0 ) )
    c = np.ones( ( h, w, 3 ) ) * lin( ( 236, 228, 206 ) ) * ( 1 - 0.12 * M.smoothstep( 0.5, 2.0, fbm( rng, ( h, w ), [ 0.6 * sx ] ) ) )[..., None]
    write( f"letters_{k}", c, normals( np.zeros( ( h, w ) ), sx, sy ), np.full( ( h, w ), 0.8 ), np.ones( ( h, w ) ),
           alpha=text, backfaces=False )


def lettering():
    for k in range( len( SIGNS ) ):
        letters( k, np.random.default_rng( seed( f"letters_{k}" ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Cut-out cards

class Card:
    """ A cut-out picture painted back to front from small items, each over the slice of the picture it covers. The
    colour, height (inches: the normals, and the shade in the hollows between leaves) and roughness are kept
    premultiplied by the coverage, and divided out at the end. """

    def __init__( self, w, h, inches ):
        self.X, self.Y, self.sx, self.sy = grid( w, h, inches )
        self.inches = inches
        self.c = np.zeros( ( h, w, 3 ) )
        self.a = np.zeros( ( h, w ) )
        self.z = np.zeros( ( h, w ) )
        self.r = np.zeros( ( h, w ) )

    def put( self, x0, x1, y0, y1, draw ):
        """ draw( X, Y ) over the slice x0..x1, y0..y1 covers: ( coverage, colour, height, roughness ). """
        s = span( self.X, self.Y, x0, x1, y0, y1, 0.0 )
        if s is None:
            return
        m, col, z, r = draw( self.X[s], self.Y[s] )
        m = np.clip( m, 0, 1 )
        keep = 1 - m
        self.c[s] = self.c[s] * keep[..., None] + col * m[..., None]
        self.z[s] = self.z[s] * keep + z * m
        self.r[s] = self.r[s] * keep + r * m
        self.a[s] = self.a[s] * keep + m

    def finish( self, name, shade=1.5, radii=( 0.3, 1.2 ) ):
        a = np.maximum( self.a, 1e-4 )
        c, z, r = self.c / a[..., None], self.z / a, self.r / a
        drawn = self.a > 0.04
        # What's behind the card is far back, so a leaf's edge isn't shaded by the empty card round it.
        low = np.where( drawn, z, z[drawn].min() - 2.0 )
        ao, _ = occlusion( low, self.sx, radii, ( 1.0, 0.6 ), shade )
        # The cut-away px take the nearest drawn px's values, so the mips don't bleed black into the edges.
        idx = ndimage.distance_transform_edt( ~drawn, return_distances=False, return_indices=True )
        c, z, r, ao = c[idx[0], idx[1]], z[idx[0], idx[1]], r[idx[0], idx[1]], ao[idx[0], idx[1]]
        write( name, c * ao[..., None], normals( z, self.sx, self.sy, 0.7 ), r, ao, alpha=self.a )


def blade( card, cx, cy, length, angle, shape, colour, z0, squash=1.0, bulge=0.18, rise=0.25, rough=0.5, veins=(),
           vein_colour=None, vein_width=0.03, zone=None ):
    """ A leaf, petal or bract round its base at ( cx, cy ): shape( phi ) is its outline's radius as a share of length
    (phi 0 along angle), squash narrows it across (turned away), bulge domes it and rise lifts it towards the tip (both
    shares of its length). veins: the angles of its main veins from the base. zone: ( colour, amount ), a geranium's
    darker horseshoe. """
    ca, sa = math.cos( angle ), math.sin( angle )
    reach = length * 1.08

    def draw( X, Y ):
        dx, dy = X - cx, Y - cy
        u = dx * ca + dy * sa
        v = ( -dx * sa + dy * ca ) / squash
        rho = np.hypot( u, v ) / length
        phi = np.arctan2( v, u )
        edge = np.maximum( shape( phi ), 1e-3 )
        aa = 0.8 / ( length * card.sx )
        m = M.smoothstep( edge + aa, edge - aa, rho )
        t = np.clip( rho / edge, 0, 1 )
        z = z0 + bulge * length * ( 1 - t ** 2 ) + rise * u
        col = np.ones( X.shape + ( 3, ) ) * colour * ( 0.82 + 0.26 * t )[..., None]
        if zone is not None:
            band = M.smoothstep( 0.36, 0.48, t ) * M.smoothstep( 0.74, 0.6, t )
            col = mix( col, zone[0], zone[1] * band )
        if veins:
            vein = np.zeros( X.shape )
            for k in veins:
                off = phi - k
                d = rho * length * np.abs( np.sin( off ) )
                width = vein_width * ( 1.6 - t )
                vein = np.maximum( vein, np.exp( -( d / width ) ** 2 ) * ( np.cos( off ) > 0 ) )
            vein = vein * M.smoothstep( 0.97, 0.55, t )
            col = mix( col, vein_colour, 0.8 * vein )
            z = z - 0.04 * length * vein
        return m, col, z, np.full( X.shape, rough )

    card.put( cx - reach, cx + reach, cy - reach, cy + reach, draw )


def stroke( card, points, width, colour, z, rough=0.6 ):
    """ A stem through points (inches), width across, rounded. """
    for p, q in zip( points, points[1:] ):
        def draw( X, Y, p=p, q=q ):
            dx, dy = q[0] - p[0], q[1] - p[1]
            px, py = X - p[0], Y - p[1]
            t = np.clip( ( px * dx + py * dy ) / ( dx * dx + dy * dy + 1e-9 ), 0, 1 )
            d = np.hypot( px - t * dx, py - t * dy )
            aa = 0.8 / card.sx
            m = M.smoothstep( width / 2 + aa, width / 2 - aa, d )
            zz = z + 0.5 * width * np.sqrt( np.clip( 1 - ( 2 * d / width ) ** 2, 0, 1 ) )
            col = np.ones( X.shape + ( 3, ) ) * colour * ( 0.8 + 0.3 * np.clip( 1 - 2 * d / width, 0, 1 ) )[..., None]
            return m, col, zz, np.full( X.shape, rough )
        card.put( min( p[0], q[0] ) - width, max( p[0], q[0] ) + width, min( p[1], q[1] ) - width,
                  max( p[1], q[1] ) + width, draw )


def wander( rng, start, heading, step, count, turn, pull=0.0, towards=None ):
    """ A stem's path: count steps of step inches, turning at random, pulled back towards a heading by pull. """
    points = [ np.asarray( start, float ) ]
    a = heading
    for _ in range( count ):
        a += rng.normal( 0, turn )
        if towards is not None:
            a += pull * math.atan2( math.sin( towards - a ), math.cos( towards - a ) )
        points.append( points[-1] + step * np.array( ( math.cos( a ), math.sin( a ) ) ) )
    return points


def jitter( rng, rgb, spread=0.12 ):
    return lin( rgb ) * rng.uniform( 1 - spread, 1 + spread ) * rng.uniform( 1 - spread / 3, 1 + spread / 3, 3 )


def ivy_shape( phi ):
    """ An ivy leaf round its stalk: a long middle lobe, two side lobes and two small ones back by the stalk. """
    a = np.abs( phi )
    return ( 0.42 + 0.58 * np.exp( -( a / 0.42 ) ** 2 ) + 0.42 * np.exp( -( ( a - 1.2 ) / 0.36 ) ** 2 )
             + 0.26 * np.exp( -( ( a - 2.15 ) / 0.4 ) ** 2 ) - 0.3 * np.exp( -( ( a - math.pi ) / 0.35 ) ** 2 ) )


IVY_VEINS = ( 0.0, 1.2, -1.2, 2.15, -2.15 )


def geranium_shape( phi ):
    """ A zonal geranium's leaf round its middle: round, its edge scalloped, a notch where the stalk joins. """
    return 0.62 * ( 1 + 0.045 * np.cos( 13 * phi ) ) - 0.3 * np.exp( -( ( np.abs( phi ) - math.pi ) / 0.22 ) ** 2 )


def petal_shape( phi ):
    """ A five-petalled floret round its middle. """
    return 0.55 + 0.45 * np.abs( np.cos( 2.5 * phi ) ) ** 0.8


def bract_shape( phi ):
    """ A bougainvillea bract round its base: broad, heart-shaped, a short point at the tip. """
    return 0.85 * ( ( 1 + np.cos( phi ) ) / 2 ) ** 0.85 + 0.15 * np.exp( -( phi / 0.22 ) ** 2 )


def ovate_shape( phi ):
    """ A plain leaf round its stalk: oval, pointed. """
    c = np.clip( np.cos( phi ), 0, 1 )
    return 0.8 * c ** 1.1 * ( 1 + 0.25 * np.exp( -( phi / 0.2 ) ** 2 ) ) * ( 0.55 + 0.45 * c )


def disc_shape( phi ):
    return np.ones( np.shape( phi ) )


def umbel( card, rng, cx, cy, radius, colour, z0 ):
    """ A geranium's flower head: a ball of florets, the ones round its edge turned away. """
    florets = []
    for _ in range( int( 10 + 9 * radius * radius ) ):
        r = radius * math.sqrt( rng.random() )
        a = rng.uniform( 0, 2 * math.pi )
        florets.append( ( z0 + math.sqrt( max( radius * radius - r * r, 0 ) ), r, a ) )
    for z, r, a in sorted( florets ):
        x, y = cx + r * math.cos( a ), cy + 0.9 * r * math.sin( a )
        facing = math.sqrt( max( 1 - ( r / radius ) ** 2, 0.05 ) )
        col = colour * rng.uniform( 0.82, 1.12 )
        turn = rng.uniform( 0, 1.3 )
        blade( card, x, y, rng.uniform( 0.34, 0.46 ), a + math.pi / 2, lambda p, o=turn: petal_shape( p + o ),
               col, z, squash=0.45 + 0.55 * facing, bulge=0.1, rise=0.0, rough=0.55 )


PLANTER = ( 40.0, 16.0 )
TRAILING = ( 40.0, 20.0 )
IVY = ( 48.0, 96.0 )
BOUGAINVILLEA = ( 48.0, 48.0 )


GERANIUMS = {
    "red": [ ( 200, 26, 32 ), ( 214, 40, 34 ), ( 186, 20, 36 ) ],
    "pink": [ ( 226, 96, 84 ), ( 220, 100, 140 ), ( 232, 128, 160 ), ( 204, 30, 40 ) ],
}


def geranium_box( rng, key ):
    """ Zonal geraniums in a window box, seen from the street, 40 x 16: the box's rim hides the bottom 3. Two staggered
    rows of flower heads over a mound of leaves. """
    w, h = PLANTER
    card = Card( 1024, int( 1024 * h / w ), PLANTER )
    palette = GERANIUMS[key]
    heads = []
    for row, ( y_lo, y_hi, z ) in enumerate( ( ( 10.5, 13.6, 1.4 ), ( 7.8, 10.2, 2.6 ) ) ):
        x = rng.uniform( 1.5, 4.0 ) + row * 2.6
        while x < w - 1.5:
            heads.append( ( z, x + rng.uniform( -0.8, 0.8 ), rng.uniform( y_lo, y_hi ), rng.uniform( 1.5, 2.1 ),
                            lin( palette[int( rng.integers( 0, len( palette ) ) )] ) ) )
            x += rng.uniform( 4.6, 6.4 )

    def leaf( y_lo, y_hi, z_lo, z_hi, size=( 1.3, 2.0 ) ):
        old = rng.random() < 0.06
        colour = ( 128, 128, 52 ) if old else ( ( 70, 104, 44 ) if rng.random() < 0.7 else ( 84, 120, 50 ) )
        blade( card, rng.uniform( 0.0, w ), rng.uniform( y_lo, y_hi ), rng.uniform( *size ), rng.uniform( 0, 2 * math.pi ),
               geranium_shape, jitter( rng, colour ), rng.uniform( z_lo, z_hi ), squash=rng.uniform( 0.55, 1.0 ),
               bulge=0.14, rise=0.0, rough=0.62, veins=tuple( k * 2 * math.pi / 9 for k in range( 9 ) ),
               vein_colour=jitter( rng, ( 100, 130, 66 ) ), vein_width=0.022,
               zone=( lin( ( 54, 50, 28 ) ), 0.0 if old else rng.uniform( 0.2, 0.55 ) ) )

    for _ in range( 120 ):
        leaf( 2.5, 8.6, 0.0, 1.0 )
    for z, hx, hy, hr, _ in heads:
        stem = wander( rng, ( hx + rng.uniform( -1.2, 1.2 ), 6.0 ), math.pi / 2, ( hy - 6.0 ) / 4, 3, 0.1 )
        stroke( card, stem + [ np.array( ( hx, hy ) ) ], 0.17, lin( ( 84, 110, 52 ) ), z - 0.4 )
    for _ in range( 24 ):
        leaf( 6.0, 8.8, 1.2, 1.9, ( 1.1, 1.6 ) )
    for z, hx, hy, hr, colour in sorted( heads, key=lambda head: head[0] ):
        umbel( card, rng, hx, hy, hr, colour, z )
    for _ in range( 90 ):
        leaf( 0.0, 5.8, 2.6, 3.6 )
    card.finish( f"geranium_{key}" )


def trailing( rng ):
    """ Ivy-leaved geraniums and ivy hanging over a window box's front from its rim, 40 x 20: a mass of leaves over the
    rim, then the stems hanging down to different lengths. """
    w, h = TRAILING
    card = Card( 1024, int( 1024 * h / w ), TRAILING )
    pink = lin( ( 222, 92, 150 ) )

    def flowers( p, z ):
        for _ in range( int( rng.integers( 4, 8 ) ) ):
            q = p + rng.normal( 0, 0.55, 2 )
            turn = rng.uniform( 0, 1.3 )
            blade( card, q[0], q[1], rng.uniform( 0.42, 0.58 ), rng.uniform( 0, 6.3 ),
                   lambda f, o=turn: petal_shape( f + o ) * ( 0.8 + 0.2 * np.cos( f ) ), pink * rng.uniform( 0.85, 1.1 ),
                   z, squash=rng.uniform( 0.6, 1.0 ), rough=0.55, veins=( 0.0, 1.26, -1.26, 2.5, -2.5 ),
                   vein_colour=lin( ( 150, 30, 70 ) ), vein_width=0.03 )

    def leaf( p, size, angle, ivy, z ):
        if ivy:
            blade( card, p[0], p[1], size, angle, ivy_shape, jitter( rng, ( 44, 70, 32 ) ), z, squash=rng.uniform( 0.6, 1.0 ),
                   rough=0.38, veins=IVY_VEINS, vein_colour=lin( ( 110, 126, 86 ) ), vein_width=0.025 )
        else:
            blade( card, p[0], p[1], size * 0.9, angle, ivy_shape, jitter( rng, ( 74, 110, 46 ) ), z,
                   squash=rng.uniform( 0.6, 1.0 ), bulge=0.25, rough=0.42 )

    for k in range( 30 ):
        x = ( k + rng.uniform( 0.1, 0.9 ) ) * w / 30
        ivy = rng.random() < 0.4
        steps = int( rng.integers( 3, 13 ) )
        path = wander( rng, ( x, h + 0.5 ), -math.pi / 2 + rng.normal( 0, 0.35 ), 1.3, steps, 0.25, 0.25, -math.pi / 2 )
        stroke( card, path, 0.12, lin( ( 70, 60, 40 ) if ivy else ( 92, 100, 50 ) ), 0.2 )
        for i, p in enumerate( path[1:] ):
            side = 1 if i % 2 else -1
            angle = -math.pi / 2 + side * rng.uniform( 0.4, 1.4 )
            base = p + 0.3 * np.array( ( math.cos( angle ), math.sin( angle ) ) )
            leaf( base, rng.uniform( 0.9, 1.5 ) * ( 1 - 0.3 * i / steps ), angle, ivy, rng.uniform( 0.3, 1.0 ) )
            if not ivy and rng.random() < 0.5:
                flowers( p, 1.2 )
    # The mass over the rim.
    for _ in range( 70 ):
        p = np.array( ( rng.uniform( 0, w ), h - abs( rng.normal( 0, 2.2 ) ) ) )
        leaf( p, rng.uniform( 1.0, 1.6 ), rng.uniform( 0, 2 * math.pi ), rng.random() < 0.4, rng.uniform( 1.2, 2.2 ) )
        if rng.random() < 0.18:
            flowers( p, 2.4 )
    card.finish( "trailing" )


IVY_MARGIN = 5.0     # how far in from the card's free edges an ivy stem stops, so its leaves stay inside


def ivy( rng, name, hanging ):
    """ A patch of ivy on a wall, 48 x 96, every leaf inside the card but along its rooted edge, so a patch on its own
    has no straight sides. Climbing, it fans up from roots round the middle of its foot: a thick mat low down, thinning
    out up the wall and towards its sides, with a few runners along the foot. Hanging, it comes over a wall's top across
    its middle three quarters, thickest along the top, its stems trailing down, the longest in the middle. """
    w, h = IVY
    card = Card( 1024, 2048, IVY )
    leaves = []
    stems = []
    up = -1.0 if hanging else 1.0
    root = h + 1 if hanging else -1.0

    def inside( path ):
        """ The path as far as it stays IVY_MARGIN inside the card's free edges. """
        for i, p in enumerate( path ):
            far = p[1] < IVY_MARGIN if hanging else p[1] > h - IVY_MARGIN
            if i and ( p[0] < IVY_MARGIN or p[0] > w - IVY_MARGIN or far ):
                return path[:i]
        return path

    count = 18 if hanging else 16
    for k in range( count ):
        if hanging:
            x = w / 2 + ( ( k + rng.uniform( 0.2, 0.8 ) ) / count - 0.5 ) * w * 0.75
            middle = 1 - abs( x - w / 2 ) / ( w / 2 )
            steps = int( h * ( 0.2 + 0.62 * middle ** 1.4 ) * rng.uniform( 0.6, 1.1 ) / 2.0 )
            path = wander( rng, ( x, root ), -math.pi / 2 + rng.normal( 0, 0.12 ), 2.0, max( steps, 4 ), 0.18, 0.12,
                           -math.pi / 2 )
        else:
            x = float( np.clip( w / 2 + rng.normal( 0, w / 10 ), w * 0.3, w * 0.7 ) )
            lean = ( x - w / 2 ) / ( w / 2 ) * 1.6 + rng.normal( 0, 0.3 )
            path = wander( rng, ( x, root ), math.pi / 2 - lean, 2.0, int( rng.integers( 18, 48 ) ), 0.2, 0.05, math.pi / 2 )
        path = inside( path )
        if len( path ) < 3:
            continue
        stems.append( path )
        for _ in range( len( path ) // 4 ):
            i = int( rng.integers( 1, len( path ) - 1 ) )
            heading = up * math.pi / 2 + rng.choice( ( -1, 1 ) ) * rng.uniform( 0.6, 1.3 )
            branch = inside( wander( rng, path[i], heading, 1.8, int( rng.integers( 3, 10 ) ), 0.3 ) )
            if len( branch ) > 1:
                stems.append( branch )
    if not hanging:
        # Runners along the foot of the wall, either way from the roots.
        for side in ( -1, 1 ):
            for _ in range( 2 ):
                start = ( w / 2 + side * rng.uniform( 1, 5 ), rng.uniform( 0.5, 2.5 ) )
                runner = inside( wander( rng, start, ( 0.0 if side > 0 else math.pi ) + side * rng.uniform( 0.05, 0.35 ),
                                         1.8, int( rng.integers( 6, 11 ) ), 0.15 ) )
                if len( runner ) > 1:
                    stems.append( runner )
    for path in stems:
        for i, p in enumerate( path ):
            if i == 0:
                continue
            # Thick near where it started, thinning out towards the ends.
            share = i / len( path )
            for _ in range( 3 if share < 0.5 else ( 2 if share < 0.8 else 1 ) ):
                d = path[i] - path[i - 1]
                angle = math.atan2( d[1], d[0] ) + rng.choice( ( -1, 1 ) ) * rng.uniform( 0.5, 1.7 ) + rng.normal( 0, 0.3 )
                base = p + rng.uniform( 0.4, 1.6 ) * np.array( ( math.cos( angle ), math.sin( angle ) ) )
                size = rng.uniform( 1.5, 2.8 ) * ( 1.0 - 0.35 * share )
                pick = rng.random()
                colour = ( 86, 112, 48 ) if pick < 0.07 else ( ( 36, 58, 28 ) if pick < 0.65 else ( 48, 72, 32 ) )
                leaves.append( ( rng.uniform( 0, 1.5 ) + 0.4 * ( 1 - share ), base, size, angle + rng.normal( 0, 0.5 ), colour ) )
    for path in stems:
        stroke( card, path, 0.24, lin( ( 86, 70, 52 ) ), 0.0, rough=0.8 )
    for z, base, size, angle, colour in sorted( leaves, key=lambda l: l[0] ):
        blade( card, base[0], base[1], size, angle, ivy_shape, jitter( rng, colour ), z, squash=rng.uniform( 0.55, 1.0 ),
               bulge=0.12, rise=0.18, rough=rng.uniform( 0.3, 0.45 ), veins=IVY_VEINS,
               vein_colour=jitter( rng, ( 104, 118, 82 ), 0.08 ), vein_width=0.028 )
    card.finish( name, shade=1.8 )


def bougainvillea( rng ):
    """ Bougainvillea hanging over a balcony's rail from the top, 48 x 48: a mass of magenta bracts in threes among
    small leaves, thickest at the rail, branches trailing below. """
    w, h = BOUGAINVILLEA
    card = Card( 1024, 1024, BOUGAINVILLEA )
    items = []
    branches = []
    for k in range( 18 ):
        branches.append( wander( rng, ( ( k + rng.uniform( 0.1, 0.9 ) ) * w / 18, h + 1 ), -math.pi / 2 + rng.normal( 0, 0.5 ),
                                 1.6, int( rng.integers( 6, 24 ) ), 0.25, 0.1, -math.pi / 2 ) )
    for path in branches:
        stroke( card, path, 0.2, lin( ( 96, 82, 56 ) ), 0.0, rough=0.8 )
        for p in path[1:]:
            for _ in range( 4 ):
                items.append( ( "cluster" if rng.random() < 0.6 else "leaf", rng.uniform( 0.5, 2.0 ), p + rng.normal( 0, 1.3, 2 ) ) )
    # The mass along the rail.
    for _ in range( 520 ):
        q = np.array( ( rng.uniform( -1, w + 1 ), h - abs( rng.normal( 0, 8 ) ) ) )
        items.append( ( "cluster" if rng.random() < 0.62 else "leaf", rng.uniform( 0.4, 2.2 ), q ) )
    magenta = [ ( 196, 28, 120 ), ( 178, 22, 112 ), ( 206, 46, 140 ), ( 160, 36, 120 ) ]
    for kind, z, q in sorted( items, key=lambda i: i[1] ):
        if kind == "leaf":
            blade( card, q[0], q[1], rng.uniform( 1.4, 2.3 ), rng.uniform( 0, 2 * math.pi ), ovate_shape,
                   jitter( rng, ( 50, 82, 32 ) ), z, squash=rng.uniform( 0.5, 1.0 ), bulge=0.15, rise=0.1, rough=0.45,
                   veins=( 0.0, ), vein_colour=lin( ( 96, 124, 62 ) ), vein_width=0.03 )
            continue
        colour = lin( ( 150, 84, 100 ) ) if rng.random() < 0.08 else lin( magenta[int( rng.integers( 0, len( magenta ) ) )] )
        a0 = rng.uniform( 0, 2 * math.pi )
        for b in range( 3 ):
            blade( card, q[0], q[1], rng.uniform( 1.0, 1.35 ), a0 + b * 2 * math.pi / 3 + rng.normal( 0, 0.2 ), bract_shape,
                   colour * rng.uniform( 0.85, 1.1 ), z + 0.05 * b, squash=rng.uniform( 0.55, 1.0 ), bulge=0.1, rise=0.05,
                   rough=0.6, veins=( 0.0, 0.6, -0.6, 1.1, -1.1 ), vein_colour=colour * 0.78, vein_width=0.025 )
        if rng.random() < 0.5:
            fq = q + rng.normal( 0, 0.1, 2 )
            blade( card, fq[0], fq[1], 0.08, 0.0, disc_shape, lin( ( 226, 220, 190 ) ), z + 0.3, rough=0.6 )
    card.finish( "bougainvillea" )


def planting():
    for key in GERANIUMS:
        geranium_box( np.random.default_rng( seed( "geranium_" + key ) ), key )
    trailing( np.random.default_rng( seed( "trailing" ) ) )
    ivy( np.random.default_rng( seed( "ivy_climb" ) ), "ivy_climb", hanging=False )
    ivy( np.random.default_rng( seed( "ivy_hang" ) ), "ivy_hang", hanging=True )
    bougainvillea( np.random.default_rng( seed( "bougainvillea" ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Wrought iron

RAIL = ( 36.0, 36.0 )


def railing( rng, w=1024, h=1024 ):
    """ One 36-inch bay of a balcony's railing, cut out, repeating along: a flat bottom rail and a rounded top rail (the
    handrail goes over it), square bars every 4.5, rings between them in a band at the top and the bottom, and an oval
    with a ring in it in the middle. Old black paint, chalky where the rain sits, rusting at the joints and the bottom
    rail. """
    X, Y, sx, sy = grid( w, h, RAIL )
    rw, rh = RAIL
    state = { "cover": np.zeros( ( h, w ) ), "height": np.zeros( ( h, w ) ), "joint": np.zeros( ( h, w ) ) }

    def add( t, half, flat=False, inside=None ):
        aa = 0.8 / sx
        m = M.smoothstep( aa, -aa, t - half )
        if inside is not None:
            m = m * inside
        if flat:     # a square bar: a flat face, its arrises eased
            z = half * np.clip( ( half - t ) / ( 0.35 * half ), 0, 1 ) ** 0.5
        else:
            z = half * np.sqrt( np.clip( 1 - ( t / half ) ** 2, 0, 1 ) )
        state["joint"] = np.maximum( state["joint"], np.minimum( state["cover"], m ) )
        state["cover"] = np.maximum( state["cover"], m )
        state["height"] = np.maximum( state["height"], z * m )

    for yc, half, flat in ( ( 1.8, 0.6, True ), ( 6.0, 0.3, True ), ( 30.0, 0.4, True ), ( 34.3, 0.7, False ) ):
        add( np.abs( Y - yc ), half, flat )
    bars = box_mask( X, Y, -1, rw + 1, 1.8, 34.3, 0.02 )
    for k in range( 8 ):
        add( np.abs( X - ( 2.25 + 4.5 * k ) ), 0.32, True, bars )
    for k in range( 9 ):
        for yc, radius in ( ( 4.05, 1.45 ), ( 32.0, 1.4 ) ):
            add( np.abs( np.hypot( X - 4.5 * k, Y - yc ) - radius ), 0.2 )
    # The oval and the ring in it, joined by short bars.
    ex, ey = ( X - 18.0 ) / 1.75, ( Y - 16.0 ) / 5.0
    f = np.hypot( ex, ey )
    grad = np.hypot( ex / 1.75, ey / 5.0 ) / np.maximum( f, 1e-6 )
    add( np.abs( f - 1 ) / np.maximum( grad, 1e-6 ), 0.22 )
    add( np.abs( np.hypot( X - 18.0, Y - 16.0 ) - 0.85 ), 0.2 )
    stub = ( ( np.abs( Y - 16.0 ) > 0.85 ) & ( np.abs( Y - 16.0 ) < 5.0 ) ).astype( float )
    add( np.abs( X - 18.0 ), 0.16, True, stub )
    cover, height, joint = state["cover"], state["height"], state["joint"]
    # Old paint over the iron.
    c = np.ones( ( h, w, 3 ) ) * lin( ( 30, 29, 28 ) ) * ( 1 + 0.08 * fbm( rng, ( h, w ), [ 2 * sx, 0.5 * sx ] ) )[..., None]
    gy, gx = np.gradient( height )
    top = np.clip( gy * sy * 2, 0, 1 )      # faces turned up (rows run down), where the rain sits
    chalk = np.clip( 0.5 * top + 0.25 * fbm( rng, ( h, w ), [ 3 * sx ] ), 0, 1 )
    c = mix( c, lin( ( 70, 66, 62 ) ), 0.4 * chalk )
    rust_field = ( fbm( rng, ( h, w ), [ 1.2 * sx, 0.4 * sx, 0.12 * sx ], [ 1.0, 0.6, 0.4 ] )
                   + 1.4 * ndimage.gaussian_filter( joint, 0.3 * sx ) + 1.0 * M.smoothstep( 4, 1, Y ) + 0.5 * top )
    rust = M.smoothstep( 1.55, 2.2, rust_field )
    rust_colour = mix( lin( ( 76, 42, 26 ) ), lin( ( 112, 62, 34 ) ), M.smoothstep( 0, 1, fbm( rng, ( h, w ), [ 0.3 * sx ] ) ) )
    c = mix( c, rust_colour, rust )
    height = height + 0.03 * rust * fbm( rng, ( h, w ), [ 0.08 * sx ] )
    rough = 0.42 + 0.2 * chalk + 0.4 * rust
    drawn = cover > 0.04
    ao, _ = occlusion( np.where( drawn, height, -1.0 ), sx, ( 0.2, 0.6 ), ( 1.0, 0.5 ), 1.4 )
    idx = ndimage.distance_transform_edt( ~drawn, return_distances=False, return_indices=True )
    c, rough, height, ao = c[idx[0], idx[1]], rough[idx[0], idx[1]], height[idx[0], idx[1]], ao[idx[0], idx[1]]
    write( "railing", c * ao[..., None], normals( height, sx, sy ), rough, ao, alpha=cover )


def ironwork():
    railing( np.random.default_rng( seed( "railing" ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Awnings

# key: ( the canvas, the stripe (or None) ), sRGB. West green and red-and-cream; the east's mirror repaints them navy
# and blue-and-cream.
AWNINGS = {
    "green": ( ( 38, 82, 54 ), None ),
    "red": ( ( 152, 36, 32 ), ( 226, 214, 188 ) ),
    "navy": ( ( 34, 50, 82 ), None ),
    "blue": ( ( 40, 82, 128 ), ( 226, 220, 204 ) ),
}
AWNING = ( 48.0, 48.0 )
STRIPE = 6.0


def canvas( rng, X, Y, sx, sy, key, stripes=True ):
    """ Acrylic awning canvas: its colour (stripes 6 wide across x, unless stripes is False), weave, sun fading in
    blotches, tide marks where rain dried, grime streaked down y. Returns ( colour, height, rough ). """
    base, stripe = AWNINGS[key]
    shape = X.shape
    c = np.ones( shape + ( 3, ) ) * lin( base )
    if stripe is not None and stripes:
        s = M.smoothstep( 0.02, -0.02, np.abs( ( X % ( 2 * STRIPE ) ) - 1.5 * STRIPE ) - STRIPE / 2 )
        c = mix( c, lin( stripe ), s )
    weave = 0.5 * field( rng, shape, ( 0.03 * sy, 0.4 * sx ) ) + 0.5 * field( rng, shape, ( 0.4 * sy, 0.03 * sx ) )
    fade = np.clip( 0.15 + 0.045 * fbm( rng, shape, [ 10 * sx, 3 * sx ] ), 0, 0.5 )
    c = mix( c, c * 0.6 + lin( ( 206, 200, 188 ) ) * 0.4, fade )
    tide = np.exp( -( ( fbm( rng, shape, [ 5 * sx, 1.5 * sx ] ) % 0.9 ) - 0.45 ) ** 2 / 0.0012 )
    c = c * ( 1 - 0.07 * tide * ( fbm( rng, shape, [ 8 * sx ] ) > 0.3 ) )[..., None]
    grime = np.clip( 0.5 + 0.5 * fbm( rng, shape, [ ( 9 * sy, 0.4 * sx ), ( 3 * sy, 0.15 * sx ) ] ), 0, 1 )
    c = c * ( 1 - 0.12 * grime * M.smoothstep( 30, 0, Y ) )[..., None] * ( 1 + 0.04 * weave )[..., None]
    return c, 0.01 * weave, 0.82 + 0.06 * fade


def awning( key, rng, w=1024, h=1024 ):
    """ The canvas, one 48 x 48 tile: x along the shop's front, y up the slope (0 at the front edge). Seams where the
    widths of cloth are sewn together run up it. """
    X, Y, sx, sy = grid( w, h, AWNING )
    c, height, rough = canvas( rng, X, Y, sx, sy, key )
    across = np.minimum( X, AWNING[0] - X )
    seam = np.exp( -( across / 0.25 ) ** 2 )
    stitch = ( np.abs( across - 0.6 ) < 0.04 ) * ( ( Y % 0.4 ) < 0.25 )
    height = height + 0.05 * seam
    c = c * ( 1 - 0.25 * seam - 0.2 * stitch )[..., None]
    write( f"awning_{key}", c, normals( height, sx, sy ), rough, np.ones( ( h, w ) ) - 0.2 * seam )


def valance( key, rng, w=1024, h=256 ):
    """ The awning's flap, 48 x 12 repeating along: scalloped along its bottom 3 and edged with binding tape in the
    stripe's colour. It's plain, as a shop's flap is when its name is painted on it: cream letters wouldn't read across
    cream stripes. """
    X, Y, sx, sy = grid( w, h, ( 48.0, 12.0 ) )
    c, height, rough = canvas( rng, X, Y, sx, sy, key, stripes=False )
    xm = ( X % STRIPE ) - STRIPE / 2
    edge = 3.0 * ( 1 - np.sqrt( np.clip( 1 - ( xm / ( STRIPE / 2 ) ) ** 2, 0, 1 ) ) )
    aa = 0.8 / sy
    alpha = M.smoothstep( edge - aa, edge + aa, Y )
    tape = M.smoothstep( 0.75, 0.6, Y - edge ) * alpha
    c = mix( c, lin( AWNINGS[key][1] or ( 218, 206, 178 ) ) * 0.9, tape )
    height = height + 0.04 * tape
    c = c * ( 1 - 0.2 * M.smoothstep( 11.2, 11.6, Y ) )[..., None]
    drawn = alpha > 0.04
    idx = ndimage.distance_transform_edt( ~drawn, return_distances=False, return_indices=True )
    write( f"valance_{key}", c[idx[0], idx[1]], normals( height, sx, sy ), rough, np.ones( ( h, w ) ), alpha=alpha )


def awnings():
    for key in AWNINGS:
        awning( key, np.random.default_rng( seed( "awning_" + key ) ) )
        valance( key, np.random.default_rng( seed( "valance_" + key ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Chalkboards, street plaques, banners and old painted signs

def text_layer( w, h, inches, items ):
    """ Coverage of text placed in inches: ( text, font, cap height, x, baseline y, align 'l' / 'c' / 'r'[, widest] ),
    narrowed to the widest it may be. """
    k = 3
    img = Image.new( "L", ( w * k, h * k ), 0 )
    d = ImageDraw.Draw( img )
    ppi = w * k / inches[0]
    for text, face, cap, x, y, align, *limit in items:
        probe = font( face, 100 )
        cap_px = -probe.getbbox( "H", anchor="ls" )[1]
        size = 100 * cap * ppi / cap_px
        f = font( face, size )
        width = d.textlength( text, font=f )
        if limit and width > limit[0] * ppi:
            f = font( face, size * limit[0] * ppi / width )
            width = d.textlength( text, font=f )
        px = x * ppi - { "l": 0, "c": width / 2, "r": width }[align]
        d.text( ( px, ( inches[1] - y ) * ppi ), text, font=f, fill=255, anchor="ls" )
    return np.asarray( img.resize( ( w, h ), Image.LANCZOS ) ).astype( float ) / 255.0


CHALKBOARD = ( 24.0, 36.0 )
CHALKBOARDS = {
    "a": [ ( "Menù del giorno", 2.6, "y" ), ( "Pasta al ragù", 1.8, "w" ), ( "Risotto ai funghi", 1.8, "w" ),
           ( "Pesce del giorno", 1.8, "w" ), ( "Vino della casa", 1.8, "w" ), ( "Caffè", 1.8, "p" ) ],
    "b": [ ( "Oggi", 3.0, "p" ), ( "Pane fresco", 1.9, "w" ), ( "Focaccia", 1.9, "w" ), ( "Formaggi", 1.9, "w" ),
           ( "Salumi", 1.9, "w" ), ( "Olio d'oliva", 1.9, "y" ) ],
}
CHALKS = { "w": ( 226, 226, 216 ), "y": ( 236, 214, 120 ), "p": ( 232, 150, 170 ) }


def chalkboard( key, rng, w=768, h=1152 ):
    """ A shop's menu board, 24 x 36: a wooden frame round a slate-black board, chalk on it over old rubbed-out chalk. """
    X, Y, sx, sy = grid( w, h, CHALKBOARD )
    bw, bh = CHALKBOARD
    frame = 1.6
    inner = inset_distance( X, Y, frame, bw - frame, frame, bh - frame )
    on_board = M.smoothstep( -0.02, 0.02, inner )
    grain = np.where( ( X < frame ) | ( X > bw - frame ), wood_grain( rng, ( h, w ), "y", sx, sy ),
                      wood_grain( rng, ( h, w ), "x", sx, sy ) )
    edge = np.minimum( np.minimum( X, bw - X ), np.minimum( Y, bh - Y ) )
    wood, wood_rough, _ = paint_weathering( rng, ( h, w ), ( 96, 64, 40 ), sx, sy, np.minimum( edge, -inner ), grain,
                                            np.full( ( h, w ), 0.3 ), chip_bias=-0.6 )
    slate = lin( ( 38, 42, 40 ) ) * ( 1 + 0.06 * fbm( rng, ( h, w ), [ 2 * sx ] ) )[..., None]
    smear = np.clip( 0.5 + 0.6 * fbm( rng, ( h, w ), [ ( 1.2 * sy, 4 * sx ), ( 0.4 * sy, 1.5 * sx ) ] ), 0, 1 )
    slate = mix( slate, lin( ( 120, 122, 118 ) ), 0.16 * smear )
    c = mix( wood, slate, on_board )
    # Each line in its own chalk, dry and broken where the chalk skipped over the slate's grain.
    dry = M.smoothstep( -1.2, 0.4, field( rng, ( h, w ), 0.06 * sx ) )
    y = bh - frame - 3.4
    for k, ( text, cap, chalk ) in enumerate( CHALKBOARDS[key] ):
        cover = text_layer( w, h, CHALKBOARD, [ ( text, "Dinish-Italic", cap, bw / 2, y, "c", bw - 2 * frame - 2.5 ) ] )
        cover = cover * dry * on_board
        c = mix( c, lin( CHALKS[chalk] ), 0.9 * cover )
        y -= cap * 2.0 + ( 1.0 if k == 0 else 0.4 )
    swirl = text_layer( w, h, CHALKBOARD, [ ( "~ ~ ~", "Dinish-Italic", 0.8, bw / 2, frame + 1.4, "c" ) ] ) * dry
    c = mix( c, lin( CHALKS["w"] ), 0.7 * swirl * on_board )
    height = -0.25 * on_board + 0.06 * grain * ( 1 - on_board )
    ao, _ = occlusion( height, sx, ( 0.2, 0.8 ), ( 1.0, 0.5 ), 2.0 )
    write( f"chalkboard_{key}", c * ao[..., None], normals( height, sx, sy ), mix( wood_rough, 0.88, on_board ), ao )


PLAQUE = ( 24.0, 9.0 )
# The west half's own streets (West Street, the north alley by the Bakery, the south alley by the Inn), the east half's
# (belltower_map.EAST_PAINTS swaps them in), then the streets both halves share: Market Street, the spawn roads inside the
# walls, the terrace walk over the gardens and the square.
PLAQUES = [ ( "VIA DELLA TORRE", ), ( "VICOLO", "DEL FORNO" ), ( "VICOLO", "DELL'OSTERIA" ),
            ( "VIA DEL", "CAMPANILE" ), ( "VICOLO", "DEL LATTE" ), ( "VICOLO", "DELLA TAVERNA" ),
            ( "VIA DEL", "MERCATO" ), ( "VIA DELLE MURA", ), ( "VIA DEI", "GIARDINI" ), ( "PIAZZA", "DELLA FONTANA" ) ]


def plaque( k, rng, w=768, h=288 ):
    """ A street's name cut into a marble slab, 24 x 9, its letters painted black (PLAQUES[k]). """
    X, Y, sx, sy = grid( w, h, PLAQUE )
    pw, ph = PLAQUE
    lines = PLAQUES[k]
    if len( lines ) == 1:
        items = [ ( lines[0], "Dinish-Bold", 2.4, pw / 2, ph / 2 - 1.2, "c", pw - 4 ) ]
    else:
        items = [ ( lines[0], "Dinish-Bold", 1.5, pw / 2, 5.3, "c", pw - 4 ),
                  ( lines[1], "Dinish-Bold", 2.1, pw / 2, 1.9, "c", pw - 4 ) ]
    text = text_layer( w, h, PLAQUE, items )
    edge = np.minimum( np.minimum( X, pw - X ), np.minimum( Y, ph - Y ) )
    marble = lin( ( 222, 220, 212 ) ) * ( 1 + 0.04 * fbm( rng, ( h, w ), [ 1.5 * sx ] ) )[..., None]
    warp = fbm( rng, ( h, w ), [ 1.2 * sx, 0.4 * sx ] )
    vein = np.zeros( ( h, w ) )
    for width, amount, scale in ( ( 0.05, 0.55, ( 1.8, 7.0 ) ), ( 0.03, 0.3, ( 0.9, 3.5 ) ) ):
        f = fbm( rng, ( h, w ), [ ( scale[0] * sy, scale[1] * sx ) ] ) + 0.35 * warp
        fade = M.smoothstep( -0.6, 0.8, fbm( rng, ( h, w ), [ 4 * sx ] ) )
        vein = np.maximum( vein, amount * fade * np.exp( -( f / width ) ** 2 ) )
    marble = mix( marble, lin( ( 140, 142, 140 ) ), vein )
    marble = marble * ( 1 - 0.05 * M.smoothstep( 0.5, 2.0, warp ) )[..., None]
    weather = np.clip( 0.3 + 0.35 * fbm( rng, ( h, w ), [ 3 * sx, 0.8 * sx ] ) + 0.6 * M.smoothstep( 4, 0, Y )
                       + 0.4 * M.smoothstep( 1.2, 0, edge ), 0, 1 )
    marble = mix( marble, lin( ( 150, 140, 118 ) ), 0.45 * weather )
    streak = np.clip( fbm( rng, ( h, w ), [ ( 3 * sy, 0.15 * sx ) ] ), 0, None ) * M.smoothstep( 6, 0, Y )
    marble = marble * ( 1 - 0.12 * streak )[..., None]
    worn = M.smoothstep( 1.4, 2.0, fbm( rng, ( h, w ), [ 0.2 * sx, 0.06 * sx ] ) )
    c = mix( marble, lin( ( 22, 22, 24 ) ), text * ( 1 - 0.7 * worn ) )
    height = 0.2 * M.smoothstep( 0.0, 0.45, edge ) - 0.06 * text
    for x, y in ( ( 1.0, 1.0 ), ( pw - 1.0, 1.0 ), ( 1.0, ph - 1.0 ), ( pw - 1.0, ph - 1.0 ) ):
        r = np.hypot( X - x, Y - y )
        screw = M.smoothstep( 0.32, 0.26, r )
        height = height + 0.06 * screw * np.sqrt( np.clip( 1 - ( r / 0.3 ) ** 2, 0, 1 ) )
        c = mix( c, lin( ( 92, 62, 40 ) ), screw )
        run = M.smoothstep( 2.5, 0.2, y - Y ) * M.smoothstep( 0.6, 0.2, np.abs( X - x ) ) * ( Y < y )
        c = mix( c, lin( ( 120, 80, 50 ) ) * 0.9, 0.5 * run )
    ao, _ = occlusion( height, sx, ( 0.2, 0.6 ), ( 1.0, 0.5 ), 2.0 )
    write( f"plaque_{k}", c * ao[..., None], normals( height, sx, sy ), 0.35 + 0.3 * weather + 0.2 * text, ao )


BANNER = ( 36.0, 72.0 )
BANNERS = { "red": ( 150, 28, 30 ), "blue": ( 30, 62, 130 ) }


def banner( key, rng, w=768, h=1536 ):
    """ The town's banner, 36 x 72, hung from a pole: the side's colour, a gold border, a cream bell under two stars, a
    swallowtail. """
    X, Y, sx, sy = grid( w, h, BANNER )
    bw, bh = BANNER
    tail = 9.0 * ( 1 - np.abs( X - bw / 2 ) / ( bw / 2 ) )
    aa = 0.8 / sx
    alpha = M.smoothstep( tail - aa, tail + aa, Y )
    c = np.ones( ( h, w, 3 ) ) * lin( BANNERS[key] )
    gold = lin( ( 214, 168, 72 ) )
    border = 1 - M.smoothstep( 1.8, 2.2, np.minimum( np.minimum( X, bw - X ), bh - Y ) )
    border = np.maximum( border, M.smoothstep( 2.2, 1.8, Y - tail ) )
    c = mix( c, gold, border )
    # The bell: a loop and crown, a waist flaring to a lip, the clapper's ball under it.
    bx, by = bw / 2, 40.0
    u, v = np.abs( X - bx ), Y - by
    half = 4.0 + 3.0 * np.clip( 1 - v / 12.0, 0, 1 ) ** 2
    body = ( v > 0 ) & ( v < 12 ) & ( u < half )
    lip = ( v > -1.0 ) & ( v <= 0 ) & ( u < 7.6 )
    crown = np.hypot( X - bx, Y - ( by + 12.0 ) ) < 4.2
    loop = np.abs( np.hypot( X - bx, Y - ( by + 16.5 ) ) - 1.6 ) < 0.5
    ball = np.hypot( X - bx, Y - ( by - 2.4 ) ) < 1.6
    bell = ndimage.gaussian_filter( ( body | lip | crown | loop | ball ).astype( float ), 0.6 )
    c = mix( c, lin( ( 232, 220, 190 ) ), np.clip( bell * 1.4, 0, 1 ) )
    star = np.zeros( ( h, w ) )
    for j in ( -1, 1 ):
        r = np.hypot( X - ( bx + j * 9.0 ), Y - 60.0 )
        a = np.arctan2( Y - 60.0, X - ( bx + j * 9.0 ) )
        point = 0.9 + 0.9 * np.cos( 5 * ( a - math.pi / 2 ) )
        star = np.maximum( star, M.smoothstep( point + 0.3, point, r ) )
    c = mix( c, gold, star )
    # The cloth hangs in folds from its pole, deeper towards the tails, and the sun has faded its top.
    height = 0.5 * np.sin( 2 * math.pi * X / 9.0 + 0.6 * np.sin( Y / 11.0 ) ) * ( 0.3 + 0.7 * M.smoothstep( bh, 10, Y ) )
    c = c * ( 1 + 0.05 * fbm( rng, ( h, w ), [ 0.3 * sx ] ) )[..., None]
    c = mix( c, c * 0.7 + lin( ( 200, 190, 170 ) ) * 0.3, 0.3 * M.smoothstep( 30, bh, Y ) )
    drawn = alpha > 0.04
    idx = ndimage.distance_transform_edt( ~drawn, return_distances=False, return_indices=True )
    write( f"banner_{key}", c[idx[0], idx[1]], normals( height, sx, sy ), np.full( ( h, w ), 0.85 ), np.ones( ( h, w ) ),
           alpha=alpha, backfaces=True )


GHOST = ( 120.0, 30.0 )
# The Inn's and the Bakery's (west), then the Tavern's and the Dairy's (their mirrors: belltower_map.EAST_PAINTS).
GHOSTS = [ ( ( "BUON CIBO", "BUONA GENTE" ), ( 236, 226, 200 ) ), ( ( "PANE E PASTA", ), ( 50, 60, 84 ) ),
           ( ( "VINI E LIQUORI", ), ( 120, 38, 30 ) ), ( ( "LATTE E", "FORMAGGI" ), ( 40, 74, 56 ) ) ]


def ghost( k, rng, w=1536, h=384 ):
    """ An old sign painted straight on the render, 120 x 30, mostly weathered away: blended over the wall. """
    X, Y, sx, sy = grid( w, h, GHOST )
    lines, ink = GHOSTS[k]
    if len( lines ) == 1:
        items = [ ( lines[0], "Dinish-Bold", 9.0, GHOST[0] / 2, 10.5, "c" ) ]
    else:
        items = [ ( lines[0], "Dinish-Bold", 8.0, GHOST[0] / 2, 17.5, "c" ), ( lines[1], "Dinish-Bold", 8.0, GHOST[0] / 2, 4.5, "c" ) ]
    text = text_layer( w, h, GHOST, items )
    rule = box_mask( X, Y, 4, GHOST[0] - 4, 1.0, 1.8, 0.1 ) + box_mask( X, Y, 4, GHOST[0] - 4, 28.2, 29.0, 0.1 )
    paint = np.clip( text + rule, 0, 1 )
    loss = M.smoothstep( 0.2, 1.4, fbm( rng, ( h, w ), [ 4 * sx, 1 * sx, 0.25 * sx ], [ 1.0, 0.6, 0.5 ] ) )
    flake = M.smoothstep( 0.6, 1.2, fbm( rng, ( h, w ), [ 0.15 * sx ] ) )
    alpha = paint * 0.62 * ( 1 - 0.85 * loss ) * ( 1 - 0.6 * flake )
    c = np.ones( ( h, w, 3 ) ) * lin( ink ) * ( 1 + 0.08 * fbm( rng, ( h, w ), [ 1 * sx ] ) )[..., None]
    write( f"ghost_{k}", c, normals( np.zeros( ( h, w ) ), sx, sy ), np.full( ( h, w ), 0.9 ), np.ones( ( h, w ) ),
           alpha=alpha, cutout=False )


def boards():
    for key in CHALKBOARDS:
        chalkboard( key, np.random.default_rng( seed( "chalkboard_" + key ) ) )
    for k in range( len( PLAQUES ) ):
        plaque( k, np.random.default_rng( seed( f"plaque_{k}" ) ) )
    for key in BANNERS:
        banner( key, np.random.default_rng( seed( "banner_" + key ) ) )
    for k in range( len( GHOSTS ) ):
        ghost( k, np.random.default_rng( seed( f"ghost_{k}" ) ) )


# ---------------------------------------------------------------------------------------------------------------------
# Lamps and hanging signs

LANTERN = ( 8.0, 12.0 )
LAMP_GLOW = 5.0         # the lanterns' and bulbs' self-lit brightness: lit, as the town's lamps are by day


def lantern_glass( rng, w=256, h=384 ):
    """ One side of a lit lantern, 8 x 12: seeded glass between iron cames and a cross-bar, the bulb's glow behind it
    brightest 40% up and spreading through the glass, soot on the glass at the top. Self-lit through its own mask, so
    the iron stays dark. """
    X, Y, sx, sy = grid( w, h, LANTERN )
    lw, lh = LANTERN
    edge = np.minimum( np.minimum( X, lw - X ), np.minimum( Y, lh - Y ) )
    iron = 1 - M.smoothstep( 0.42, 0.5, edge )
    iron = np.maximum( iron, np.exp( -( ( Y - lh * 0.74 ) / 0.16 ) ** 2 ) )
    r = np.hypot( X - lw / 2, ( Y - lh * 0.4 ) * 0.8 )
    glow = 0.9 * np.exp( -( r / 1.5 ) ** 2 ) + 0.4 * np.exp( -( r / 4.2 ) ** 2 ) + 0.1
    # Seeded glass: a ripple that bends the glow, and small bubbles that catch it.
    ripple = fbm( rng, ( h, w ), [ ( 0.6 * sy, 2.5 * sx ), ( 0.2 * sy, 0.8 * sx ) ] )
    glow = glow * ( 1 + 0.14 * ripple ) + 0.12 * M.smoothstep( 2.3, 2.9, field( rng, ( h, w ), 0.05 * sx ) )
    soot = np.clip( M.smoothstep( lh * 0.62, lh, Y ) * ( 0.6 + 0.4 * fbm( rng, ( h, w ), [ 1.0 * sx ] ) ), 0, 1 )
    glow = np.clip( glow * ( 1 - 0.5 * soot ), 0, 1 ) * ( 1 - iron )
    glass = mix( lin( ( 96, 84, 66 ) ), lin( ( 255, 236, 196 ) ), np.sqrt( glow ) )
    rust = M.smoothstep( 1.0, 2.0, fbm( rng, ( h, w ), [ 0.3 * sx, 0.1 * sx ] ) )
    metal = mix( lin( ( 30, 28, 26 ) ), lin( ( 86, 52, 34 ) ), 0.5 * rust )
    c = mix( glass, metal, iron )
    height = 0.15 * iron + 0.01 * ripple * ( 1 - iron )
    ao, _ = occlusion( height, sx, ( 0.2, 0.5 ), ( 1.0, 0.5 ), 2.0 )
    write( "lantern_glass", c * ao[..., None], normals( height, sx, sy ), mix( 0.08, 0.6, iron ), ao, illum=LAMP_GLOW,
           illum_mask=glow )


def lamp_bulb( w=64, h=64 ):
    """ A bare bulb's glass, lit: warm white, brighter at its middle. """
    X, Y, sx, sy = grid( w, h, ( 2.0, 2.0 ) )
    r = np.hypot( X - 1.0, Y - 1.0 )
    glow = 0.75 + 0.25 * np.exp( -( r / 0.6 ) ** 2 )
    c = np.ones( ( h, w, 3 ) ) * lin( ( 255, 238, 204 ) ) * glow[..., None]
    write( "lamp_bulb", c, normals( np.zeros( ( h, w ) ), sx, sy ), np.full( ( h, w ), 0.15 ), np.ones( ( h, w ) ),
           illum=LAMP_GLOW * 1.6, illum_mask=np.ones( ( h, w ) ) )


def lamp_reflector( rng, w=128, h=128 ):
    """ The white enamel inside a street lamp's dish, lit by its bulb, a little dusty. """
    X, Y, sx, sy = grid( w, h, ( 8.0, 8.0 ) )
    dust = np.clip( 0.5 + 0.5 * fbm( rng, ( h, w ), [ 1.0 * sx ] ), 0, 1 )
    c = np.ones( ( h, w, 3 ) ) * lin( ( 240, 234, 220 ) ) * ( 1 - 0.1 * dust )[..., None]
    write( "lamp_reflector", c, normals( np.zeros( ( h, w ) ), sx, sy ), 0.2 + 0.2 * dust, np.ones( ( h, w ) ),
           illum=LAMP_GLOW * 0.3, illum_mask=np.ones( ( h, w ) ) )


INSEGNA = ( 30.0, 22.0 )
# ( name, emblem, board, letters ): the Inn's (west), then the Tavern's (east).
INSEGNE = [ ( "OSTERIA", "grapes", ( 92, 30, 34 ), ( 224, 192, 120 ) ),
            ( "TAVERNA", "tankard", ( 36, 66, 52 ), ( 226, 208, 152 ) ) ]


def grapes( rng, X, Y, cx, cy ):
    """ A painted bunch of grapes hanging from ( cx, cy ), with a vine leaf and its stalk: ( coverage, colour ). The
    berries sit a little out of line and vary in size, as a sign painter's do. """
    cover = np.zeros( X.shape )
    c = np.zeros( X.shape + ( 3, ) )
    leaf_r = np.hypot( X - ( cx - 3.2 ), Y - ( cy - 0.2 ) )
    phi = np.arctan2( Y - ( cy - 0.2 ), X - ( cx - 3.2 ) )
    leaf = M.smoothstep( 0.08, -0.08, leaf_r - 2.4 * ( 0.82 + 0.18 * np.cos( 5 * phi ) ) )
    vein = np.exp( -( ( ( phi * 5 / math.pi ) % 2 - 1 ) * leaf_r / 0.12 ) ** 2 ) * ( leaf_r < 2.0 )
    green = mix( lin( ( 70, 112, 52 ) ), lin( ( 40, 70, 34 ) ), 0.5 * vein )
    c = mix( c, green, leaf )
    cover = np.maximum( cover, leaf )
    stalk = np.exp( -( ( X - cx ) / 0.18 ) ** 2 ) * ( Y > cy - 0.5 ) * ( Y < cy + 2.4 )
    c = mix( c, lin( ( 86, 60, 36 ) ), stalk )
    cover = np.maximum( cover, stalk )
    for j, count in enumerate( ( 5, 4, 4, 3, 2, 1 ) ):
        for k in range( count ):
            x = cx + ( k - ( count - 1 ) / 2 ) * 1.9 + 0.25 * ( j % 2 ) + rng.uniform( -0.18, 0.18 )
            y = cy - 1.2 - j * 1.6 + rng.uniform( -0.15, 0.15 )
            size = rng.uniform( 0.88, 1.06 )
            d = np.hypot( X - x, Y - y ) / size
            berry = M.smoothstep( 1.08, 0.94, d )
            lit = np.clip( 1 - np.hypot( X - ( x - 0.35 ), Y - ( y + 0.35 ) ) / ( 1.1 * size ), 0, 1 )
            shade = mix( lin( ( 58, 26, 70 ) ), lin( ( 150, 96, 168 ) ), lit ** 1.5 )
            shade = mix( shade, lin( ( 34, 14, 40 ) ), M.smoothstep( 0.8, 1.05, d ) )
            c = mix( c, shade, berry )
            cover = np.maximum( cover, berry )
    return cover, c


def tankard( X, Y, cx, cy ):
    """ A painted pewter tankard standing on ( cx, cy ), its beer's head over the brim: ( coverage, colour ). """
    cover = np.zeros( X.shape )
    c = np.zeros( X.shape + ( 3, ) )
    u, v = X - cx, Y - cy
    half = 3.4 - 0.25 * v / 9.0
    body = M.smoothstep( 0.08, -0.08, np.abs( u ) - half ) * M.smoothstep( -0.08, 0.08, v ) * M.smoothstep( 9.08, 8.92, v )
    lit = np.clip( 0.5 + 0.5 * np.cos( ( u / half + 0.35 ) * 1.4 ), 0, 1 )
    pewter = mix( lin( ( 88, 92, 92 ) ), lin( ( 214, 214, 204 ) ), lit ** 2 )
    for b in ( 1.0, 7.8 ):
        pewter = mix( pewter, lin( ( 70, 72, 72 ) ), np.exp( -( ( v - b ) / 0.22 ) ** 2 ) )
    c = mix( c, pewter, body )
    cover = np.maximum( cover, body )
    ring = np.abs( np.hypot( ( u - half - 1.0 ) / 1.25, ( v - 4.6 ) / 2.3 ) - 1.0 ) * 1.4
    handle = M.smoothstep( 0.42, 0.3, ring ) * ( u > half - 0.2 )
    c = mix( c, mix( lin( ( 96, 98, 96 ) ), lin( ( 190, 190, 182 ) ), np.clip( ( v - 2.5 ) / 4.0, 0, 1 ) ), handle )
    cover = np.maximum( cover, handle )
    foam = np.zeros( X.shape )
    for k, x in enumerate( np.linspace( -3.1, 3.1, 6 ) ):
        foam = np.maximum( foam, M.smoothstep( 1.05, 0.9, np.hypot( u - x, v - ( 9.2 + 0.35 * ( k % 2 ) ) ) ) )
    foam = np.maximum( foam, M.smoothstep( 1.0, 0.85, np.hypot( u - 3.6, ( v - 7.6 ) / 1.6 ) ) * ( v > 6.5 ) )
    c = mix( c, mix( lin( ( 200, 190, 160 ) ), lin( ( 248, 244, 230 ) ), np.clip( ( v - 8.4 ) / 1.6, 0, 1 ) ), foam )
    cover = np.maximum( cover, foam )
    return cover, c


def insegna( k, rng, w=960, h=704 ):
    """ A hanging sign, 30 x 22, painted the same on both faces of its board: the house's name over its emblem in a
    lined border, the paint faded and chipped like the shop signs'. """
    name, emblem, board, letters = INSEGNE[k]
    X, Y, sx, sy = grid( w, h, INSEGNA )
    bw, bh = INSEGNA
    edge = np.minimum( np.minimum( X, bw - X ), np.minimum( Y, bh - Y ) )
    grain = wood_grain( rng, ( h, w ), "x", sx, sy )
    c, rough, chipped = paint_weathering( rng, ( h, w ), board, sx, sy, edge + 0.5, grain,
                                          0.4 + 0.3 * M.smoothstep( 0, bh, Y ), chip_bias=-0.9 )
    border = np.clip( box_mask( X, Y, 1.0, bw - 1.0, 1.0, bh - 1.0, 0.03 )
                      - box_mask( X, Y, 1.45, bw - 1.45, 1.45, bh - 1.45, 0.03 ), 0, 1 )
    text = text_layer( w, h, INSEGNA, [ ( name, "Dinish-Bold", 3.4, bw / 2, 16.4, "c", bw - 5.0 ) ] )
    rule = box_mask( X, Y, bw / 2 - 6, bw / 2 + 6, 14.6, 14.85, 0.03 )
    paint = np.clip( text + border + rule, 0, 1 ) * ( 1 - 0.6 * chipped )
    c = mix( c, lin( letters ), 0.94 * paint )
    cover, col = grapes( rng, X, Y, bw / 2 + 0.6, 12.0 ) if emblem == "grapes" else tankard( X, Y, bw / 2 - 0.6, 3.0 )
    cover = cover * ( 1 - 0.5 * chipped )
    c = mix( c, col, cover )
    height = -0.2 * M.smoothstep( 0.8, 0.3, edge ) + 0.02 * paint + 0.03 * cover + 0.04 * grain * chipped
    ao, _ = occlusion( height, sx, ( 0.3, 1.0 ), ( 1.0, 0.5 ), 1.6 )
    rough = mix( rough, 0.45, 0.5 * np.clip( paint + cover, 0, 1 ) )
    write( f"insegna_{k}", c * ao[..., None], normals( height, sx, sy ), rough, ao )


def lamps():
    lantern_glass( np.random.default_rng( seed( "lantern_glass" ) ) )
    lamp_bulb()
    lamp_reflector( np.random.default_rng( seed( "lamp_reflector" ) ) )
    for k in range( len( INSEGNE ) ):
        insegna( k, np.random.default_rng( seed( f"insegna_{k}" ) ) )


# ---------------------------------------------------------------------------------------------------------------------

MATERIALS = { "louvres": louvres, "doors": doors, "windows": windows, "shopfronts": shopfronts, "signs": signs,
              "lettering": lettering, "planting": planting, "ironwork": ironwork, "awnings": awnings, "boards": boards,
              "lamps": lamps }


def write_sheet( path ):
    """ Every picture lit from the top left on grey, each scaled to 300 high. """
    light = np.array( ( -0.45, 0.55, 0.7 ) )
    light /= np.linalg.norm( light )
    tiles = []
    for name, ( colour, normal, alpha ) in SHEETS.items():
        ndl = np.clip( np.sum( normal * light, -1 ), 0, 1 )
        shaded = M.to_srgb( np.clip( colour * ( 0.45 + 0.75 * ndl )[..., None], 0, 1 ) )
        if alpha is not None:
            shaded = shaded * alpha[..., None] + 90 * ( 1 - alpha[..., None] )
        img = Image.fromarray( shaded.astype( np.uint8 ) )
        scale = 300 / img.height
        if img.width * scale > 900:
            scale = 900 / img.width
        tiles.append( img.resize( ( max( 1, int( img.width * scale ) ), max( 1, int( img.height * scale ) ) ), Image.LANCZOS ) )
    if not tiles:
        return
    width = 1800
    rows, row, x = [], [], 0
    for t in tiles:
        if x + t.width > width and row:
            rows.append( row )
            row, x = [], 0
        row.append( t )
        x += t.width + 8
    rows.append( row )
    sheet = Image.new( "RGB", ( width, sum( max( t.height for t in r ) + 8 for r in rows ) ), ( 60, 60, 60 ) )
    y = 0
    for r in rows:
        x = 0
        for t in r:
            sheet.paste( t, ( x, y ) )
            x += t.width + 8
        y += max( t.height for t in r ) + 8
    sheet.save( path, quality=90 )
    print( f"wrote {path}" )


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "names", nargs="*", help=f"what to write (default all: {', '.join( MATERIALS )})" )
    parser.add_argument( "--out", help="write here instead of Assets/materials/belltower" )
    parser.add_argument( "--sheet", help="also write a lit picture of each here" )
    args = parser.parse_args()
    if args.out:
        M.OUT_DIR = Path( args.out )
    M.OUT_DIR.mkdir( parents=True, exist_ok=True )
    for name in args.names or list( MATERIALS ):
        MATERIALS[name]()
        print( f"{name}: done" )
    if args.sheet:
        write_sheet( args.sheet )


if __name__ == "__main__":
    main()
