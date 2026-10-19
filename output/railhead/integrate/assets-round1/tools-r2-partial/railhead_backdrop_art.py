"""
Railhead backdrop's own textures: what the tenements along the cab roads need that no other script draws.

    python Tools/railhead_backdrop_art.py <output root>        (a folder laid out as Assets; writes RES under it)

ensure_materials( root ) writes every texture and vmat under root / RES (materials/railhead/backdrop), and nothing
anywhere else; railhead_backdrop.configure() points the "bd_" paints at them (PAINTS). Pictures have their origin at the
top left; rect_uv gives ( u0, v0, u1, v1 ) with v up from the bottom, as railhead_materials' atlases do.

- bd_windows: the upper floors' glass, 16 variants (8 x 2 cells of 256 x 512 px, a 1.2 x 2.2 m casement): an empty dark
  room, net curtains, a roller blind part down, drawn curtains, a lit room, plants on the sill, Venetian blinds. Glossy,
  so the glass reflects the sky over the street (Fresnel does the rest).
- bd_shop_glass: clear plate glass (glass.shader), so the shops' rooms behind it show.
- bd_interiors: a shop's back wall at 512 x 512 px per 140 x 140 in: shelves of goods by trade (bakery, pharmacy, books,
  flowers, optician, drinks, clothes, cafe), lit as a shop is by day (a little self-illumination).
- bd_light: a lit opal ceiling panel.
- bd_awning: four striped canvas colourways (rows of 1024 x 256 px), its stripes 4 in apart, u repeating.
- bd_plaques: 32 enamel house numbers (blue, white rim and figures), 128 x 128 px each.
- bd_shutter: a galvanised roller shutter's slats at 2.4 in, grimed at the foot, a few tags on some.
- bd_soot_<render>: the renders darkened by a century of soot, for the attic storeys (the buildings' own textures,
  tinted), and bd_plinth_grime: the grey ashlar plinth splashed dark.
- Pass 2 (2026-10-16): the windows mirror the sky's blue-grey over a dark room (lit rooms self-lit through
  bd_windows_illum); bd_goods (64 packaging fronts, no real brands), bd_crust (loaves), bd_clock and bd_menu for the
  shops' fittings, bd_room_* / bd_shelf_* (self-lit a little, as a shop is by day); bd_granite, bd_dressed_dark,
  bd_tile_green, bd_burgundy and bd_paint_* (clean joinery paint) for the shopfronts; bd_tile_aged / bd_tile_dark for
  the roofs; bd_field_dry / bd_field_stubble and the canopy (bd_canopy, bd_woods, bd_woods_dark, bd_tree) for the
  country; bd_rotunda_card, the Rotunde's impostor shown mostly as baked.
"""
import math
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path( __file__ ).resolve().parent.parent
RES = "materials/railhead/backdrop"
FONT_DIR = ROOT / "Assets/fonts"

WINDOWS = ( 2048, 1024, 8, 2 )          # atlas w, h, columns, rows
INTERIORS = ( 2048, 1024, 4, 2 )
PLAQUES = ( 1024, 512, 8, 4 )
AWNINGS = ( "green", "red", "blue", "grey" )
INTERIOR_KINDS = ( "bakery", "pharmacy", "books", "flowers", "optician", "drinks", "clothes", "cafe" )
SOOTED = ( "render_cream", "render_ochre", "render_pale", "render_rose", "render_sage", "render_blue", "render_terracotta" )

PAINTS = {
    "bd_windows": 1.0, "bd_shop_glass": 128.0, "bd_interiors": 1.0, "bd_light": 64.0, "bd_awning": 1.0,
    "bd_plaques": 1.0, "bd_shutter": 1.0, "bd_plinth_grime": 64.0, "bd_rotunda_glass": 64.0,
    **{ f"bd_soot_{r[7:]}": 128.0 for r in SOOTED }, "bd_render_rose": 128.0, "bd_render_terracotta": 128.0,
    "bd_woods": 512.0, "bd_woods_dark": 512.0, "bd_tree": 384.0,
    # Pass 2: the shops' fittings and goods, stall risers and frames, the far city's roofs, the hills' fields
    "bd_light_soft": 64.0, "bd_goods": 1.0, "bd_crust": 16.0, "bd_granite": 96.0, "bd_dressed_dark": 96.0,
    "bd_tile_green": 24.0, "bd_burgundy": 64.0, "bd_tile_aged": 160.0, "bd_tile_dark": 160.0, "bd_field_dry": 480.0,
    "bd_field_stubble": 480.0, "bd_clock": 1.0, "bd_menu": 1.0, "bd_steel_white": 64.0,
    **{ f"bd_paint_{c}": 64.0 for c in ( "white", "brown", "green", "blue", "red" ) },
    # A shop's room behind the glass, lit as shops are by day (~800 lux against the street's shade): its walls, ceiling
    # and fittings self-lit a little, so they read through the glass as the old back-wall picture did
    **{ f"bd_room_{c}": 128.0 for c in ( "pale", "cream", "ochre", "sage" ) },
    "bd_shelf_white": 64.0, "bd_shelf_oak": 96.0, "bd_shelf_dark": 96.0, "bd_rotunda_card": 1.0,
    # Round 2: the rooms' ceilings and back walls (a warm pool under the lamps falling off to the floor), the pendant
    # lamps and their glow on the ceiling, the vinyl and frosted band on the shop glass, bread baskets, a shutter's poster
    "bd_room_ceiling": 128.0, **{ f"bd_room_{c}_back": 128.0 for c in ( "pale", "cream", "ochre", "sage" ) },
    "bd_lamp": 16.0, "bd_enamel_dark": 32.0, "bd_light_halo": 1.0, "bd_vinyl": 1.0, "bd_frost": 64.0, "bd_wicker": 12.0,
    "bd_poster": 1.0, "bd_zinc": 96.0,
}
# Joinery paint as a kept-up city has it: clean satin colours (building_textures' trim_ paints are flaking, too worn
# for front doors and window frames a few metres from the pavement)
JOINERY = { "white": ( 0.84, 0.83, 0.8 ), "brown": ( 0.25, 0.155, 0.1 ), "green": ( 0.12, 0.215, 0.155 ),
            "blue": ( 0.13, 0.19, 0.29 ), "red": ( 0.36, 0.1, 0.09 ) }
GOODS = ( 1024, 1024, 8, 8 )            # packaging fronts: 64 cells of 128 px
GOODS_KINDS = { "box": range( 0, 24 ), "can": range( 24, 32 ), "spine": range( 32, 48 ), "jar": range( 48, 56 ),
                "magazine": range( 56, 64 ) }
# Round 2: the rooms' emulsion colours, warm (a Baeckerei's cream, an ochre cafe, a sage florist, a pale chemist)
ROOM_TINTS = { "cream": ( 0.82, 0.75, 0.62 ), "ochre": ( 0.8, 0.66, 0.46 ), "sage": ( 0.62, 0.68, 0.58 ),
               "pale": ( 0.8, 0.78, 0.72 ) }
WINDOW_LIT = ( 4, 12 )                  # the lit rooms' cells, self-lit
WINDOW_BRIGHT = 9                       # the brightest variant (a net curtain in the sky's light): Kipp sashes take it


def material_path( paint ):
    return f"{RES}/{paint}.vmat"


def cell_uv( atlas, k ):
    """ Cell k's ( u0, v0, u1, v1 ) in an atlas ( w, h, cols, rows ), v up from the bottom; a half-texel inset. """
    w, h, cols, rows = atlas
    c, r = k % cols, ( k // cols ) % rows
    cw, ch = w / cols, h / rows
    x0, y0, x1, y1 = c * cw + 1, r * ch + 1, ( c + 1 ) * cw - 1, ( r + 1 ) * ch - 1
    return ( x0 / w, 1.0 - y1 / h, x1 / w, 1.0 - y0 / h )


def awning_v( colourway ):
    """ The v band of an awning colourway's row ( v0, v1 ). """
    k = AWNINGS.index( colourway ) if colourway in AWNINGS else 0
    return ( 1.0 - ( k + 1 ) / 4 + 0.004, 1.0 - k / 4 - 0.004 )


# ---------------------------------------------------------------------------------------------------------------------
# Helpers

def rng_of( *key ):
    return np.random.default_rng( zlib.crc32( "/".join( map( str, key ) ).encode() ) )


def noise( h, w, cell, rng, octaves=3 ):
    """ Value noise in 0..1, roughly cell px per feature. """
    out = np.zeros( ( h, w ) )
    amp, total = 1.0, 0.0
    for o in range( octaves ):
        c = max( 2, int( cell / ( 2 ** o ) ) )
        small = rng.random( ( h // c + 2, w // c + 2 ) )
        img = Image.fromarray( ( small * 255 ).astype( np.uint8 ) ).resize( ( ( w // c + 2 ) * c, ( h // c + 2 ) * c ),
                                                                           Image.BICUBIC )
        out += amp * np.asarray( img, float )[:h, :w] / 255.0
        total += amp
        amp *= 0.5
    return out / total


def save( path, arr ):
    path.parent.mkdir( parents=True, exist_ok=True )
    a = np.clip( arr, 0, 255 ).astype( np.uint8 )
    Image.fromarray( a ).save( path )


def font( name, px ):
    try:
        return ImageFont.truetype( str( FONT_DIR / f"{name}.ttf" ), int( px ) )
    except OSError:
        return ImageFont.load_default( int( px ) )


def vmat( path, colour, normal="materials/default/default_normal.tga", rough="[0.700000 0.700000 0.700000 0.000000]",
          tint=( 1.0, 1.0, 1.0 ), metal=0.0, illum=None, illum_mask="[1.000000 1.000000 1.000000 0.000000]" ):
    lines = [ "// Tools/railhead_backdrop_art.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_SPECULAR "1"' ]
    if illum:
        lines += [ '    F_SELF_ILLUM "1"', f'    TextureSelfIllumMask "{illum_mask}"', f'    g_flSelfIllumBrightness "{illum:.2f}"',
                   '    g_flSelfIllumAlbedoFactor "1.0"', '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"' ]
    lines += [ '    g_flRoughnessScaleFactor "1"', f'    g_flMetalness "{metal:.2f}"', f'    TextureColor "{colour}"',
               f'    TextureNormal "{normal}"', f'    TextureRoughness "{rough}"',
               '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
               f'    g_vColorTint "[{tint[0]:.3f} {tint[1]:.3f} {tint[2]:.3f} 1.0]"', '    g_flModelTintAmount "1.0"', "}", "" ]
    path.parent.mkdir( parents=True, exist_ok=True )
    path.write_text( "\n".join( lines ) )


def normal_from_height( height, strength ):
    gy, gx = np.gradient( height )
    n = np.dstack( ( -gx * strength, gy * strength, np.ones_like( height ) ) )
    n /= np.linalg.norm( n, axis=2, keepdims=True )
    return ( n * 0.5 + 0.5 ) * 255


# ---------------------------------------------------------------------------------------------------------------------
# The upper floors' windows: what's behind the glass, seen from the street

def window_cell( k ):
    """ A 256 x 512 window picture ( RGB float 0..255 ) and its roughness ( 0..255 ). """
    W, H = 256, 512
    rng = rng_of( "win", k )
    kind = ( "dark", "net", "blind", "drapes", "lit", "plants", "venetian", "net_blind" )[k % 8]
    alt = k >= 8
    y = np.linspace( 0, 1, H )[:, None]
    x = np.linspace( 0, 1, W )[None, :]
    # The room: dark, a little lighter towards the ceiling's light from the window; a ceiling line, a wall, furniture
    base = np.array( ( 30, 32, 36 ) if not alt else ( 34, 31, 30 ), float )
    room = np.ones( ( H, W, 3 ) ) * base
    room *= ( 0.75 + 0.5 * ( 1 - y ) )[..., None] * ( 0.85 + 0.3 * x )[..., None] / 1.1
    img = Image.fromarray( np.clip( room, 0, 255 ).astype( np.uint8 ) )
    d = ImageDraw.Draw( img )
    ceil = int( H * between( rng, 0.08, 0.16 ) )
    d.rectangle( ( 0, 0, W, ceil ), fill=( 44, 44, 46 ) )
    # A wardrobe or shelf, a picture, a lamp shade
    fx = int( W * between( rng, 0.05, 0.55 ) )
    d.rectangle( ( fx, int( H * 0.35 ), fx + int( W * 0.35 ), H ), fill=( 18, 17, 18 ) )
    px = int( W * between( rng, 0.1, 0.7 ) )
    d.rectangle( ( px, int( H * 0.25 ), px + 46, int( H * 0.25 ) + 36 ), fill=( 52, 48, 42 ) )
    lx = int( W * between( rng, 0.3, 0.7 ) )
    d.polygon( [ ( lx - 22, ceil + 40 ), ( lx + 22, ceil + 40 ), ( lx + 14, ceil + 14 ), ( lx - 14, ceil + 14 ) ],
               fill=( 70, 66, 58 ) )
    d.line( ( lx, 0, lx, ceil + 14 ), fill=( 20, 20, 20 ), width=2 )
    if kind == "lit":
        glow = np.array( img, float )
        warm = np.array( ( 255, 214, 160 ) if not alt else ( 236, 232, 222 ), float )
        g = np.exp( -( ( x - lx / W ) ** 2 * 6 + ( y - 0.2 ) ** 2 * 4 ) )
        glow = glow * ( 1.6 + 2.2 * g[..., None] ) + warm * 0.25 * g[..., None]
        img = Image.fromarray( np.clip( glow, 0, 255 ).astype( np.uint8 ) )
        d = ImageDraw.Draw( img )
        d.ellipse( ( lx - 16, ceil + 18, lx + 16, ceil + 46 ), fill=( 255, 240, 210 ) )
    img = img.filter( ImageFilter.GaussianBlur( 2.5 ) )      # out of focus behind the glass
    a = np.asarray( img, float )
    # What hangs in the window
    if kind in ( "net", "net_blind" ):
        lace = 0.5 + 0.5 * np.sin( x * math.pi * between( rng, 22, 34 ) + 0.6 * np.sin( y * 9 ) )
        pattern = noise( H, W, 6, rng, 2 )
        white = np.array( ( 226, 224, 214 ) if not alt else ( 232, 226, 206 ), float )
        cover = ( 0.55 + 0.25 * lace + 0.15 * pattern )[..., None]
        top = int( H * ( 0.0 if kind == "net" else 0.38 ) )
        mask = np.zeros( ( H, 1, 1 ) )
        mask[top:] = 1
        a = a * ( 1 - cover * mask ) + white * cover * mask * ( 0.7 + 0.3 * lace[..., None] )
    if kind in ( "blind", "net_blind" ):
        drop = int( H * ( between( rng, 0.25, 0.6 ) if kind == "blind" else 0.36 ) )
        cloth = np.array( ( 214, 202, 176 ) if not alt else ( 196, 200, 196 ), float )
        weave = 0.92 + 0.08 * noise( H, W, 4, rng, 2 )
        a[:drop] = cloth * weave[:drop, :, None] * ( 0.9 + 0.1 * x[..., None] )
        a[drop:drop + 10] = ( 120, 116, 104 )
        a[drop + 10:drop + 14] *= 0.4
    if kind == "drapes":
        colours = ( ( 112, 40, 36 ), ( 70, 82, 52 ), ( 140, 120, 86 ), ( 54, 64, 96 ) )
        c = np.array( colours[int( rng.integers( 4 ) )], float )
        for side in ( 0, 1 ):
            w = int( W * between( rng, 0.18, 0.3 ) )
            xs = slice( 0, w ) if side == 0 else slice( W - w, W )
            fold = 0.65 + 0.35 * np.sin( np.linspace( 0, 1, w )[None, :] * math.pi * 7 + side )
            a[:, xs] = c * fold[..., None] * ( 0.8 + 0.2 * ( 1 - y ) )[..., None]
    if kind == "venetian":
        slat = ( ( np.arange( H ) // 7 ) % 2 ).astype( float )[:, None, None]
        grey = np.array( ( 196, 196, 190 ), float )
        a = a * 0.15 + grey * ( 0.75 + 0.2 * slat ) * ( 0.85 + 0.15 * x[..., None] )
    if kind == "plants" or ( alt and kind == "dark" ):
        img = Image.fromarray( np.clip( a, 0, 255 ).astype( np.uint8 ) )
        d = ImageDraw.Draw( img )
        for p in range( int( rng.integers( 2, 4 ) ) ):
            cx = int( W * between( rng, 0.15, 0.85 ) )
            d.rectangle( ( cx - 16, H - 50, cx + 16, H - 8 ), fill=( 150, 82, 50 ) )
            for leaf in range( 18 ):
                lx_, ly_ = cx + rng.normal( 0, 18 ), H - 60 - abs( rng.normal( 0, 40 ) )
                r = between( rng, 7, 15 )
                g = int( between( rng, 60, 110 ) )
                d.ellipse( ( lx_ - r, ly_ - r * 0.6, lx_ + r, ly_ + r * 0.6 ), fill=( 30, g, 34 ) )
        a = np.asarray( img, float )
    # Seen from the street on a sunny afternoon the glass mirrors the sky over the street and the houses opposite: a
    # blue-grey gradient (paler at the top, ~0.45, ~0.25 at the sill) over the darker room, strongest where the room is
    # dark, with a soft band of a sunlit cornice opposite. Nets and blinds keep their own light; lit rooms barely mirror.
    mirror = { "lit": 0.12, "net": 0.3, "venetian": 0.3 }.get( kind, 0.62 )
    sky = np.array( ( 122.0, 132.0, 146.0 ) ) * ( 1 - y[..., None] ) + np.array( ( 64.0, 70.0, 78.0 ) ) * y[..., None]
    band = np.exp( -( ( x * 0.6 + y * 0.8 - between( rng, 0.35, 0.8 ) ) ** 2 ) / 0.004 )
    sky = sky + np.array( ( 52.0, 46.0, 36.0 ) ) * band[..., None] * between( rng, 0.3, 1.0 )
    lum = a.mean( axis=2, keepdims=True ) / 255.0
    w = mirror * np.clip( 1.15 - lum * 1.6, 0.25, 1.0 )
    a = a * ( 1 - w ) + sky * w
    # Dust and grime gather in the glass's corners; a faint film of dirt over it all
    edge = np.minimum( np.minimum( x, 1 - x ) * W, np.minimum( y, 1 - y ) * H )
    a = a * ( 0.82 + 0.18 * np.clip( edge / 30, 0, 1 ) )[..., None]
    a = a * 0.92 + 14 * noise( H, W, 40, rng, 2 )[..., None]
    rough = 20 + 26 * noise( H, W, 24, rng, 2 ) + ( 30 * ( 1 - np.clip( edge / 18, 0, 1 ) ) )
    return a, rough


def between( rng, lo, hi ):
    return lo + ( hi - lo ) * float( rng.random() )


def draw_windows( out ):
    w, h, cols, rows = WINDOWS
    colour, rough = np.zeros( ( h, w, 3 ) ), np.zeros( ( h, w ) )
    for k in range( cols * rows ):
        c, r = k % cols, k // cols
        a, ro = window_cell( k )
        colour[r * 512:( r + 1 ) * 512, c * 256:( c + 1 ) * 256] = a
        rough[r * 512:( r + 1 ) * 512, c * 256:( c + 1 ) * 256] = ro
    save( out / "bd_windows_color.png", colour )
    save( out / "bd_windows_rough.png", rough )
    # The lit rooms glow a little (a lamp on by day): a self-illumination mask over their cells only
    mask = np.zeros( ( h, w ) )
    for k in WINDOW_LIT:
        c, r = k % cols, k // cols
        cell = colour[r * 512:( r + 1 ) * 512, c * 256:( c + 1 ) * 256].mean( axis=2 )
        mask[r * 512:( r + 1 ) * 512, c * 256:( c + 1 ) * 256] = np.clip( ( cell - 40 ) * 1.6, 0, 255 )
    save( out / "bd_windows_illum.png", mask )
    vmat( out / "bd_windows.vmat", f"{RES}/bd_windows_color.png", rough=f"{RES}/bd_windows_rough.png", illum=1.4,
          illum_mask=f"{RES}/bd_windows_illum.png" )


# ---------------------------------------------------------------------------------------------------------------------
# The shops' back walls

def interior_cell( kind ):
    S = 512
    rng = rng_of( "shop", kind )
    walls = { "bakery": ( 232, 220, 196 ), "pharmacy": ( 236, 240, 238 ), "books": ( 214, 200, 176 ),
              "flowers": ( 222, 228, 214 ), "optician": ( 240, 240, 236 ), "drinks": ( 212, 214, 216 ),
              "clothes": ( 228, 222, 214 ), "cafe": ( 120, 84, 60 ) }
    img = Image.new( "RGB", ( S, S ), walls[kind] )
    d = ImageDraw.Draw( img )
    wood = ( 132, 92, 58 ) if kind in ( "bakery", "books", "cafe", "flowers" ) else ( 238, 238, 236 )
    if kind in ( "clothes", ):
        for rail in ( 70, 290 ):
            d.rectangle( ( 0, rail, S, rail + 6 ), fill=( 150, 150, 152 ) )
            x = 10
            while x < S - 30:
                w = int( rng.integers( 26, 40 ) )
                c = ( ( 46, 52, 70 ), ( 120, 112, 100 ), ( 180, 172, 160 ), ( 70, 40, 44 ), ( 40, 40, 42 ), ( 150, 120, 90 ),
                      ( 90, 100, 84 ), ( 200, 196, 190 ) )[int( rng.integers( 8 ) )]
                length = int( rng.integers( 110, 170 ) ) if rail == 70 else int( rng.integers( 90, 150 ) )
                d.line( ( x + w // 2, rail, x + w // 2, rail + 10 ), fill=( 110, 110, 110 ), width=2 )
                d.polygon( [ ( x + 4, rail + 12 ), ( x + w - 4, rail + 12 ), ( x + w, rail + 22 ), ( x + w - 1, rail + length ),
                             ( x + 1, rail + length ), ( x, rail + 22 ) ], fill=c )
                d.line( ( x + w // 2, rail + 14, x + w // 2, rail + length ), fill=tuple( int( v * 0.7 ) for v in c ), width=1 )
                x += w - int( rng.integers( 6, 14 ) )
        d.rectangle( ( 0, 470, S, S ), fill=( 200, 192, 180 ) )
    elif kind == "flowers":
        for row, z in enumerate( ( 250, 380, 500 ) ):
            d.rectangle( ( 0, z, S, z + 12 ), fill=wood )
            for k in range( 9 ):
                x = 28 + k * 56 + row * 10
                d.rectangle( ( x - 18, z - 50, x + 18, z ), fill=( 70, 74, 80 ) )
                for f in range( 14 ):
                    fx, fy = x + rng.normal( 0, 14 ), z - 60 - abs( rng.normal( 0, 30 ) )
                    d.line( ( x, z - 48, fx, fy ), fill=( 52, 104, 50 ), width=2 )
                    c = ( ( 220, 40, 60 ), ( 250, 210, 60 ), ( 240, 240, 236 ), ( 200, 90, 160 ), ( 240, 130, 40 ) )[
                        int( rng.integers( 5 ) )]
                    d.ellipse( ( fx - 6, fy - 6, fx + 6, fy + 6 ), fill=c )
    elif kind == "cafe":
        d.rectangle( ( 40, 60, 260, 230 ), fill=( 28, 30, 28 ) )                 # a chalk menu board
        for k in range( 9 ):
            d.line( ( 60, 84 + k * 16, 60 + int( rng.integers( 80, 180 ) ), 84 + k * 16 ), fill=( 220, 220, 210 ), width=3 )
        d.rectangle( ( 300, 150, 500, 160 ), fill=wood )
        d.rectangle( ( 300, 250, 500, 260 ), fill=wood )
        for k in range( 12 ):
            x = 310 + k * 16
            d.rectangle( ( x, 120, x + 10, 150 ), fill=( 236, 236, 230 ) )
            d.rectangle( ( x, 226, x + 12, 250 ), fill=( 60 + int( rng.integers( 0, 80 ) ), 40, 30 ) )
        d.rectangle( ( 300, 300, 470, 420 ), fill=( 170, 170, 172 ) )            # the espresso machine
        d.rectangle( ( 314, 320, 456, 360 ), fill=( 40, 40, 42 ) )
        for k in range( 3 ):
            d.ellipse( ( 330 + k * 44, 372, 348 + k * 44, 390 ), fill=( 30, 30, 30 ) )
    else:
        shelves = ( 110, 210, 310, 410 )
        for z in shelves:
            d.rectangle( ( 10, z, S - 10, z + 9 ), fill=wood )
            d.rectangle( ( 10, z + 9, S - 10, z + 13 ), fill=tuple( int( v * 0.6 ) for v in wood ) )
            x = 16
            while x < S - 24:
                if kind == "books":
                    w_, h_ = int( rng.integers( 7, 16 ) ), int( rng.integers( 60, 88 ) )
                    c = tuple( int( v ) for v in rng.integers( 30, 200, 3 ) )
                elif kind == "bakery":
                    w_, h_ = int( rng.integers( 30, 52 ) ), int( rng.integers( 18, 36 ) )
                    c = ( int( rng.integers( 150, 200 ) ), int( rng.integers( 90, 130 ) ), int( rng.integers( 40, 70 ) ) )
                elif kind == "drinks":
                    w_, h_ = 12, int( rng.integers( 60, 76 ) )
                    c = ( ( 40, 110, 50 ), ( 140, 70, 30 ), ( 210, 210, 220 ), ( 60, 60, 70 ), ( 180, 40, 40 ) )[
                        int( rng.integers( 5 ) )]
                elif kind == "optician":
                    w_, h_ = 40, 14
                    c = ( ( 30, 30, 30 ), ( 120, 70, 40 ), ( 150, 150, 160 ), ( 40, 60, 120 ) )[int( rng.integers( 4 ) )]
                else:       # pharmacy: small boxes
                    w_, h_ = int( rng.integers( 10, 20 ) ), int( rng.integers( 22, 40 ) )
                    c = ( ( 240, 240, 240 ), ( 40, 120, 180 ), ( 220, 60, 60 ), ( 60, 160, 90 ), ( 250, 200, 60 ) )[
                        int( rng.integers( 5 ) )]
                if rng.random() < 0.08:
                    x += w_ + 6
                    continue
                if kind == "optician":
                    d.ellipse( ( x, z - 30, x + 16, z - 18 ), outline=c, width=3 )
                    d.ellipse( ( x + 20, z - 30, x + 36, z - 18 ), outline=c, width=3 )
                elif kind == "bakery":
                    d.ellipse( ( x, z - h_, x + w_, z + 4 ), fill=c )
                    d.arc( ( x + 4, z - h_ + 4, x + w_ - 4, z ), 200, 340, fill=( 220, 180, 120 ), width=2 )
                elif kind == "drinks":
                    d.rectangle( ( x, z - h_ + 18, x + w_, z ), fill=c )
                    d.rectangle( ( x + 4, z - h_, x + w_ - 4, z - h_ + 18 ), fill=c )
                    d.rectangle( ( x, z - 34, x + w_, z - 22 ), fill=( 236, 230, 210 ) )
                else:
                    d.rectangle( ( x, z - h_, x + w_, z ), fill=c )
                    if kind == "books":
                        d.line( ( x + 2, z - h_ + 10, x + w_ - 2, z - h_ + 10 ), fill=( 220, 200, 120 ), width=2 )
                x += w_ + int( rng.integers( 1, 5 ) )
        if kind in ( "pharmacy", "optician" ):
            d.rectangle( ( 0, 440, S, S ), fill=( 220, 222, 220 ) )
    a = np.asarray( img.filter( ImageFilter.GaussianBlur( 1.0 ) ), float )
    a = a * 0.8 + a.mean( axis=2, keepdims=True ) * 0.2         # printed packaging fades under shop lights
    yy = np.linspace( 0, 1, S )[:, None, None]
    a *= 0.9 + 0.15 * ( 1 - yy )                     # lit from the ceiling
    return a


def draw_interiors( out ):
    w, h, cols, rows = INTERIORS
    colour = np.zeros( ( h, w, 3 ) )
    for k, kind in enumerate( INTERIOR_KINDS ):
        c, r = k % cols, k // cols
        colour[r * 512:( r + 1 ) * 512, c * 512:( c + 1 ) * 512] = interior_cell( kind )
    save( out / "bd_interiors_color.png", colour )
    # Lit a little, as the rooms' walls are now (round 2): a far shop is a warm room, not a light box
    vmat( out / "bd_interiors.vmat", f"{RES}/bd_interiors_color.png", rough="[0.650000 0.650000 0.650000 0.000000]",
          illum=0.18, tint=( 0.9, 0.84, 0.74 ) )


# ---------------------------------------------------------------------------------------------------------------------
# Canvas awnings, house numbers, roller shutters

def draw_awnings( out ):
    S = 1024
    ways = { "green": ( ( 52, 106, 70 ), ( 232, 226, 204 ) ), "red": ( ( 164, 52, 46 ), ( 236, 230, 214 ) ),
             "blue": ( ( 44, 80, 128 ), ( 238, 238, 232 ) ), "grey": ( ( 110, 112, 112 ), ( 214, 210, 198 ) ) }
    colour = np.zeros( ( S, S, 3 ) )
    rng = rng_of( "awning" )
    weave = 0.9 + 0.1 * noise( S, S, 3, rng, 2 )
    stain = noise( S, S, 120, rng, 3 )
    xs = np.arange( S )
    stripe = ( ( xs // 64 ) % 2 ).astype( float )          # 64 px = 4 in at 256 px per 16 in
    for k, name in enumerate( AWNINGS ):
        a, b = ( np.array( c, float ) for c in ways[name] )
        rows = slice( k * 256, ( k + 1 ) * 256 )
        band = a[None, :] * ( 1 - stripe[:, None] ) + b[None, :] * stripe[:, None]
        yy = np.linspace( 0, 1, 256 )[:, None, None]
        c = band[None, :, :] * weave[rows, :, None] * ( 0.86 + 0.14 * ( 1 - yy ) )
        c *= ( 0.85 + 0.15 * stain[rows, :, None] )        # weathered, sun-faded towards the hem
        colour[rows] = c
    save( out / "bd_awning_color.png", colour )
    height = noise( S, S, 3, rng, 1 )
    save( out / "bd_awning_normal.png", normal_from_height( height, 2.0 ) )
    vmat( out / "bd_awning.vmat", f"{RES}/bd_awning_color.png", normal=f"{RES}/bd_awning_normal.png",
          rough="[0.850000 0.850000 0.850000 0.000000]" )


def draw_plaques( out ):
    w, h, cols, rows = PLAQUES
    img = Image.new( "RGB", ( w, h ), ( 30, 52, 112 ) )
    d = ImageDraw.Draw( img )
    f = font( "Dinish-Bold", 80 ) if ( FONT_DIR / "Dinish-Bold.ttf" ).is_file() else font( "ChakraPetch-Bold", 80 )
    for k in range( cols * rows ):
        x0, y0 = ( k % cols ) * 128, ( k // cols ) * 128
        d.rounded_rectangle( ( x0 + 4, y0 + 4, x0 + 124, y0 + 124 ), 14, fill=( 26, 48, 108 ), outline=( 240, 240, 236 ),
                             width=6 )
        text = str( k + 1 )
        bb = d.textbbox( ( 0, 0 ), text, font=f )
        d.text( ( x0 + 64 - ( bb[2] + bb[0] ) / 2, y0 + 64 - ( bb[3] + bb[1] ) / 2 ), text, font=f, fill=( 244, 244, 240 ) )
    save( out / "bd_plaques_color.png", np.asarray( img, float ) )
    vmat( out / "bd_plaques.vmat", f"{RES}/bd_plaques_color.png", rough="[0.250000 0.250000 0.250000 0.000000]" )


def draw_shutter( out ):
    W, H = 512, 1024                    # 64 x 128 in: slats 2.4 in (19 px) apart
    rng = rng_of( "shutter" )
    y = np.arange( H )[:, None].astype( float )
    phase = ( y % 19.2 ) / 19.2
    height = np.sin( phase * math.pi ) ** 0.6 + 0 * np.arange( W )[None, :]
    groove = ( phase < 0.08 ).astype( float )
    base = np.array( ( 196, 198, 196 ), float )          # light grey powder-coat, as most German shop shutters
    zinc = 0.9 + 0.1 * noise( H, W, 30, rng, 3 )
    # Perforated slats: a row of 0.12 x 0.6 in slots across each slat's middle, 1.2 in apart (dark: the shop behind)
    xs = np.arange( W )[None, :].astype( float )
    slot = ( ( np.abs( phase - 0.5 ) < 0.13 ) & ( ( xs % 9.6 ) < 4.8 ) ).astype( float )
    colour = base * zinc[..., None] * ( 0.8 + 0.2 * height[..., None] ) * ( 1 - 0.35 * groove[..., None] )
    colour *= ( 1 - 0.72 * slot[..., None] )
    yy = y / H
    grime = np.clip( ( yy - 0.7 ) / 0.3, 0, 1 ) * ( 0.5 + 0.5 * noise( H, W, 20, rng, 2 ) )
    streak = noise( H, W, 6, rng, 1 )
    colour *= ( 1 - 0.45 * grime[..., None] ) * ( 1 - 0.08 * streak[..., None] )
    # Tags: a few spray-painted scrawls low down
    img = Image.fromarray( np.clip( colour, 0, 255 ).astype( np.uint8 ) )
    d = ImageDraw.Draw( img )
    for t in range( 1 ):
        cx, cy = between( rng, 60, 450 ), between( rng, 700, 940 )
        col = ( ( 30, 30, 34 ), ( 40, 70, 160 ), ( 170, 40, 60 ), ( 240, 240, 240 ) )[int( rng.integers( 4 ) )]
        pts = [ ( cx + between( rng, -70, 70 ), cy + between( rng, -30, 30 ) ) for _ in range( 7 ) ]
        d.line( pts, fill=col, width=int( between( rng, 4, 8 ) ), joint="curve" )
    colour = np.asarray( img.filter( ImageFilter.GaussianBlur( 0.7 ) ), float )
    save( out / "bd_shutter_color.png", colour )
    save( out / "bd_shutter_normal.png", normal_from_height( height * 6 + 0.3 * streak - 2.0 * slot, 1.0 ) )
    save( out / "bd_shutter_rough.png", 110 + 70 * grime + 30 * streak + 60 * slot )
    vmat( out / "bd_shutter.vmat", f"{RES}/bd_shutter_color.png", normal=f"{RES}/bd_shutter_normal.png",
          rough=f"{RES}/bd_shutter_rough.png", metal=0.3 )


# ---------------------------------------------------------------------------------------------------------------------
# Pass 2: the shops' goods, bread crust, the hills' canopy, a shop clock and a chalk menu

def goods_cell( k ):
    """ A 128 x 128 packaging front ( RGB 0..255 ): boxes, cans, book spines, jars, magazines (no real brands). """
    S = 128
    rng = rng_of( "goods", k )
    kind = next( name for name, cells in GOODS_KINDS.items() if k in cells )
    palette = ( ( 236, 234, 228 ), ( 196, 52, 46 ), ( 40, 92, 160 ), ( 56, 132, 76 ), ( 238, 196, 60 ), ( 30, 44, 84 ),
                ( 226, 124, 48 ), ( 120, 60, 110 ), ( 200, 200, 196 ), ( 70, 70, 74 ) )
    bg = palette[int( rng.integers( len( palette ) ) )]
    img = Image.new( "RGB", ( S, S ), bg )
    d = ImageDraw.Draw( img )
    ink = ( 30, 30, 34 ) if sum( bg ) > 420 else ( 244, 242, 236 )
    accent = palette[int( rng.integers( len( palette ) ) )]
    if kind == "box":
        y = int( between( rng, 20, 70 ) )
        d.rectangle( ( 0, y, S, y + int( between( rng, 14, 34 ) ) ), fill=accent )
        for j in range( int( rng.integers( 2, 5 ) ) ):
            yy = 10 + j * 9
            d.rectangle( ( 10, yy, 10 + int( between( rng, 30, 100 ) ), yy + 4 ), fill=ink )
        if rng.random() < 0.6:
            cx, cy = int( between( rng, 30, 98 ) ), int( between( rng, 80, 110 ) )
            d.ellipse( ( cx - 12, cy - 12, cx + 12, cy + 12 ), fill=accent, outline=ink, width=2 )
    elif kind == "can":
        for x in range( S ):             # a cylinder's shading across its label
            t = x / S
            shade = 0.55 + 0.6 * math.sin( t * math.pi ) ** 0.7
            d.line( ( x, 0, x, S ), fill=tuple( int( c * shade ) for c in bg ) )
        d.rectangle( ( 0, 44, S, 74 ), fill=accent )
        d.rectangle( ( 20, 54, 108, 62 ), fill=ink )
        d.rectangle( ( 0, 0, S, 8 ), fill=( 180, 182, 184 ) )
        d.rectangle( ( 0, S - 8, S, S ), fill=( 170, 172, 174 ) )
    elif kind == "spine":
        d.rectangle( ( 0, 6, S, 12 ), fill=( 206, 176, 96 ) )
        d.rectangle( ( 0, S - 12, S, S - 6 ), fill=( 206, 176, 96 ) )
        for j in range( int( rng.integers( 3, 7 ) ) ):
            yy = 22 + j * 12
            d.rectangle( ( int( between( rng, 30, 50 ) ), yy, int( between( rng, 70, 100 ) ), yy + 5 ), fill=ink )
    elif kind == "jar":
        glass = ( 60, 64, 58 )
        d.rectangle( ( 0, 0, S, S ), fill=glass )
        d.rectangle( ( 0, 0, S, 22 ), fill=accent )
        d.rectangle( ( 10, 40, S - 10, 100 ), fill=( 236, 230, 214 ) )
        d.rectangle( ( 22, 58, 106, 66 ), fill=( 60, 50, 40 ) )
        d.rectangle( ( 14, 24, 22, 120 ), fill=( 150, 156, 150 ) )                       # a highlight on the glass
    else:                                # a magazine's cover: a photo block and its title
        photo = tuple( int( c ) for c in rng.integers( 40, 200, 3 ) )
        d.rectangle( ( 0, 30, S, S ), fill=photo )
        d.ellipse( ( 30, 50, 100, 130 ), fill=tuple( min( 255, c + 50 ) for c in photo ) )
        d.rectangle( ( 6, 6, int( between( rng, 70, 120 ) ), 24 ), fill=ink )
        for j in range( 3 ):
            d.rectangle( ( 8, 84 + j * 10, int( between( rng, 30, 60 ) ), 88 + j * 10 ), fill=( 250, 250, 246 ) )
    a = np.asarray( img.filter( ImageFilter.GaussianBlur( 0.6 ) ), float )
    return a * 0.88 + a.mean( axis=2, keepdims=True ) * 0.12


def draw_goods( out ):
    w, h, cols, rows = GOODS
    colour = np.zeros( ( h, w, 3 ) )
    for k in range( cols * rows ):
        c, r = k % cols, k // cols
        colour[r * 128:( r + 1 ) * 128, c * 128:( c + 1 ) * 128] = goods_cell( k )
    save( out / "bd_goods_color.png", colour )
    vmat( out / "bd_goods.vmat", f"{RES}/bd_goods_color.png", rough="[0.450000 0.450000 0.450000 0.000000]" )


def draw_crust( out ):
    """ A loaf's crust: baked golden brown, darker where it rose, flour dusted, at 256 px per 16 in. """
    S = 256
    rng = rng_of( "crust" )
    n = noise( S, S, 24, rng, 3 )
    fine = noise( S, S, 4, rng, 2 )
    dark, gold = np.array( ( 96, 54, 26 ), float ), np.array( ( 196, 138, 70 ), float )
    t = np.clip( n * 1.3 - 0.15, 0, 1 )[..., None]
    a = dark * ( 1 - t ) + gold * t
    flour = ( fine > 0.72 ).astype( float )[..., None] * 0.6
    a = a * ( 1 - flour ) + np.array( ( 228, 214, 190 ) ) * flour
    save( out / "bd_crust_color.png", a )
    save( out / "bd_crust_normal.png", normal_from_height( n * 3 + fine, 1.5 ) )
    vmat( out / "bd_crust.vmat", f"{RES}/bd_crust_color.png", normal=f"{RES}/bd_crust_normal.png",
          rough="[0.750000 0.750000 0.750000 0.000000]" )


def blur_wrap( a, radius ):
    """ A Gaussian blur of a tiling picture, wrapped at its edges (through the FFT, which is periodic). """
    h, w = a.shape
    fy, fx = np.fft.fftfreq( h )[:, None], np.fft.fftfreq( w )[None, :]
    kernel = np.exp( -2 * ( math.pi * radius ) ** 2 * ( fx * fx + fy * fy ) )
    return np.real( np.fft.ifft2( np.fft.fft2( a ) * kernel ) )


def draw_canopy( out ):
    """ A wood's canopy, tiling (1024 px over 512 in): heaped clusters of leaves at three sizes, lit from the sun's side
    and dark in the hollows between them, a blue-green summer leaf turning in places in early October. """
    S = 1024
    rng = rng_of( "canopy" )
    height = np.zeros( ( S, S ) )
    for count, radius, weight in ( ( 90, 34.0, 1.0 ), ( 700, 11.0, 0.55 ), ( 5000, 3.5, 0.3 ) ):
        imp = np.zeros( ( S, S ) )
        ys, xs = rng.integers( 0, S, count ), rng.integers( 0, S, count )
        imp[ys, xs] = rng.uniform( 0.5, 1.0, count )
        layer = blur_wrap( imp, radius )
        height += weight * layer / max( layer.max(), 1e-6 )
    height /= height.max()
    gy, gx = np.gradient( height * 60 )
    light = np.clip( 0.6 + 0.9 * ( -gx * 0.55 - gy * 0.7 ) / np.sqrt( 1 + gx * gx + gy * gy ), 0.1, 1.4 )
    hollow = np.clip( ( height - 0.08 ) / 0.35, 0, 1 ) ** 0.7                # the shade down between the clusters
    shade = light * ( 0.25 + 0.75 * hollow )
    base = np.array( ( 30.0, 50.0, 30.0 ) )
    turn = np.clip( noise( S, S, 140, rng, 2 ) * 2 - 1, 0, 1 )[..., None]  # a few crowns turning yellow-brown
    autumn = np.array( ( 70.0, 66.0, 30.0 ) )
    colour = ( base * ( 1 - 0.45 * turn ) + autumn * 0.45 * turn ) * shade[..., None] * 3.2     # ~0.05-0.08 albedo
    save( out / "bd_canopy_color.png", colour )
    save( out / "bd_canopy_normal.png", normal_from_height( height * 40, 1.0 ) )


def draw_clock_menu( out ):
    """ A shop's wall clock (256 px) and a chalk menu board. """
    img = Image.new( "RGB", ( 256, 256 ), ( 238, 236, 228 ) )
    d = ImageDraw.Draw( img )
    d.ellipse( ( 4, 4, 252, 252 ), fill=( 244, 242, 236 ), outline=( 30, 30, 30 ), width=10 )
    for k in range( 12 ):
        a = 2 * math.pi * k / 12
        r0, r1 = ( 92, 112 ) if k % 3 else ( 80, 112 )
        d.line( ( 128 + r0 * math.sin( a ), 128 - r0 * math.cos( a ), 128 + r1 * math.sin( a ), 128 - r1 * math.cos( a ) ),
                fill=( 20, 20, 20 ), width=6 if k % 3 == 0 else 3 )
    for a, r, wd in ( ( 2 * math.pi * 2.05 / 12, 56, 9 ), ( 2 * math.pi * 0.05, 88, 6 ) ):     # 14:03
        d.line( ( 128, 128, 128 + r * math.sin( a ), 128 - r * math.cos( a ) ), fill=( 16, 16, 16 ), width=wd )
    save( out / "bd_clock_color.png", np.asarray( img, float ) )
    vmat( out / "bd_clock.vmat", f"{RES}/bd_clock_color.png", rough="[0.300000 0.300000 0.300000 0.000000]" )
    rng = rng_of( "menu" )
    img = Image.new( "RGB", ( 256, 256 ), ( 120, 86, 56 ) )
    d = ImageDraw.Draw( img )
    d.rectangle( ( 10, 10, 246, 246 ), fill=( 34, 38, 36 ) )
    for k in range( 12 ):
        y = 26 + k * 18
        d.line( ( 24, y, 24 + int( between( rng, 60, 150 ) ), y ), fill=( 226, 224, 214 ), width=3 )
        d.line( ( 200, y, 230, y ), fill=( 236, 210, 120 ), width=3 )
    a = np.asarray( img.filter( ImageFilter.GaussianBlur( 0.8 ) ), float )
    save( out / "bd_menu_color.png", a )
    vmat( out / "bd_menu.vmat", f"{RES}/bd_menu_color.png", rough="[0.850000 0.850000 0.850000 0.000000]" )


def write_pass2( out ):
    """ Pass 2's tinted and flat materials: stall risers, frames, enamel, far roofs, fields, woods, the soft ceiling
    lights. """
    B = "materials/buildings"
    vmat( out / "bd_granite.vmat", f"{B}/ashlar_grey_color.png", normal=f"{B}/ashlar_normal.png",
          rough="[0.220000 0.220000 0.220000 0.000000]", tint=( 0.30, 0.29, 0.29 ) )
    vmat( out / "bd_dressed_dark.vmat", "materials/railhead/rw_dressed_color.png",
          normal="materials/railhead/dressed_normal.png", rough="materials/railhead/dressed_rough.png",
          tint=( 0.6, 0.56, 0.52 ) )
    vmat( out / "bd_tile_green.vmat", "[0.150000 0.290000 0.215000 0.000000]", normal=f"{B}/quarry_tiles_normal.png",
          rough="[0.180000 0.180000 0.180000 0.000000]" )
    vmat( out / "bd_burgundy.vmat", "[0.330000 0.090000 0.100000 0.000000]", normal="materials/railhead/plain_normal.png",
          rough="[0.380000 0.380000 0.380000 0.000000]" )
    vmat( out / "bd_steel_white.vmat", "[0.860000 0.860000 0.840000 0.000000]", normal="materials/railhead/plain_normal.png",
          rough="[0.320000 0.320000 0.320000 0.000000]" )
    for name, tint in ( ( "bd_tile_aged", ( 0.74, 0.68, 0.7 ) ), ( "bd_tile_dark", ( 0.54, 0.5, 0.52 ) ) ):
        vmat( out / f"{name}.vmat", f"{B}/roof_tiles_color.png", normal=f"{B}/roof_tiles_normal.png",
              rough=f"{B}/roof_tiles_rough.png", tint=tint )
    vmat( out / "bd_field_dry.vmat", f"{B}/lawn_color.png", normal=f"{B}/lawn_normal.png", rough=f"{B}/lawn_rough.png",
          tint=( 1.4, 1.25, 1.12 ) )
    vmat( out / "bd_field_stubble.vmat", f"{B}/soil_color.png", normal=f"{B}/soil_normal.png", rough=f"{B}/soil_rough.png",
          tint=( 1.0, 0.95, 0.72 ) )
    for name, tint in ( ( "bd_woods", ( 1.0, 1.0, 1.05 ) ), ( "bd_woods_dark", ( 0.8, 0.85, 0.92 ) ),
                        ( "bd_tree", ( 1.18, 1.24, 1.02 ) ) ):
        vmat( out / f"{name}.vmat", f"{RES}/bd_canopy_color.png", normal=f"{RES}/bd_canopy_normal.png",
              rough="[0.850000 0.850000 0.850000 0.000000]", tint=tint )
    for c, rgb in JOINERY.items():
        vmat( out / f"bd_paint_{c}.vmat", "[%.6f %.6f %.6f 0.000000]" % rgb, normal="materials/railhead/plain_normal.png",
              rough="materials/railhead/plain_rough.png" )
    # A shop's room by day: warm emulsion walls lit from above, only a little self-light (the lamps' pool is the back
    # wall's own, bright under the ceiling and gone 30 in over the floor), so it reads darker than the sunlit street
    for c in ( "pale", "cream", "ochre", "sage" ):
        vmat( out / f"bd_room_{c}.vmat", f"{B}/render_{c}_color.png", normal=f"{B}/render_normal.png",
              rough=f"{B}/render_rough.png", illum=0.15, tint=ROOM_TINTS[c] )
        vmat( out / f"bd_room_{c}_back.vmat", f"{B}/render_{c}_color.png", normal=f"{B}/render_normal.png",
              rough=f"{B}/render_rough.png", illum=0.42, tint=ROOM_TINTS[c], illum_mask=f"{RES}/bd_room_fall_mask.png" )
    vmat( out / "bd_room_ceiling.vmat", f"{B}/render_pale_color.png", normal=f"{B}/render_normal.png",
          rough=f"{B}/render_rough.png", illum=0.2, tint=ROOM_TINTS["pale"] )
    vmat( out / "bd_shelf_white.vmat", "[0.880000 0.880000 0.860000 0.000000]", normal="materials/railhead/plain_normal.png",
          rough="[0.350000 0.350000 0.350000 0.000000]", illum=0.12 )
    for name, wood, tint in ( ( "bd_shelf_oak", "planks", ( 0.78, 0.6, 0.42 ) ), ( "bd_shelf_dark", "planks_dark", ( 1.0, 1.0, 1.0 ) ) ):
        vmat( out / f"{name}.vmat", f"{B}/{wood}_color.png", normal=f"{B}/planks_normal.png", rough=f"{B}/planks_rough.png",
              illum=0.12, tint=tint )
    # The Rotunde's roof: zinc weathered to its blue-grey patina, darker than new sheet, a little sheen
    vmat( out / "bd_zinc.vmat", "[0.420000 0.445000 0.465000 0.000000]", normal="materials/railhead/plain_normal.png",
          rough="[0.480000 0.480000 0.480000 0.000000]", metal=0.35 )
    # The pendant lamps: an opal underside, dark green-black enamel shades
    vmat( out / "bd_lamp.vmat", "[0.990000 0.930000 0.820000 0.000000]", rough="[0.400000 0.400000 0.400000 0.000000]",
          illum=2.0 )
    vmat( out / "bd_enamel_dark.vmat", "[0.060000 0.075000 0.065000 0.000000]", normal="materials/railhead/plain_normal.png",
          rough="[0.250000 0.250000 0.250000 0.000000]" )
    # The Rotunde's distant card: its bake carries the sun's and the sky's light, so it shows mostly as baked (self-lit)
    # with only a little of the scene's light on it, which would light its shaded face a second time
    ( out / "bd_rotunda_card.vmat" ).write_text( "\n".join( [
        "// Tools/railhead_backdrop_art.py", '"Layer0"', "{", '    shader "shaders/complex.shader"', '    F_ALPHA_TEST "1"',
        '    F_SELF_ILLUM "1"', '    TextureColor "materials/railhead/rotunda_impostor.png"',
        '    TextureTranslucency "materials/railhead/rotunda_impostor_alpha.png"',
        '    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"',
        '    TextureNormal "materials/default/default_normal.tga"', '    TextureRoughness "[0.850000 0.850000 0.850000 0.000000]"',
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"', '    g_flAlphaTestReference "0.7"',
        '    g_flSelfIllumBrightness "1.0"', '    g_flSelfIllumAlbedoFactor "1"',
        '    g_vColorTint "[1.000000 0.960000 0.900000 1.0]"', "}", "" ] ) )
    vmat( out / "bd_light_soft.vmat", "[0.960000 0.950000 0.910000 0.000000]", rough="[0.400000 0.400000 0.400000 0.000000]",
          illum=1.4 )


def write_tinted( out ):
    """ The sooted renders and the plinth's grime: the buildings' own textures, tinted. """
    for r in SOOTED:
        tint = ( 0.62, 0.6, 0.58 ) if r != "render_pale" else ( 0.66, 0.64, 0.62 )
        vmat( out / f"bd_soot_{r[7:]}.vmat", f"materials/buildings/{r}_color.png",
              normal="materials/buildings/render_normal.png", rough="materials/buildings/render_rough.png", tint=tint )
    # The rose and terracotta renders, weathered paler and less pink: limewash colours fade in a few summers
    for r, tint in ( ( "render_rose", ( 0.9, 0.93, 0.95 ) ), ( "render_terracotta", ( 0.8, 0.72, 0.74 ) ) ):
        vmat( out / f"bd_{r}.vmat", f"materials/buildings/{r}_color.png", normal="materials/buildings/render_normal.png",
              rough="materials/buildings/render_rough.png", tint=tint )
    vmat( out / "bd_plinth_grime.vmat", "materials/buildings/ashlar_grey_color.png",
          normal="materials/buildings/ashlar_normal.png", rough="materials/buildings/ashlar_rough.png",
          tint=( 0.58, 0.56, 0.53 ) )


def write_glass( out ):
    ( out / "bd_shop_glass.vmat" ).write_text( "\n".join( [
        "// Tools/railhead_backdrop_art.py", '"Layer0"', "{", '    shader "shaders/glass.shader"', '    F_GLASS_QUALITY "2"',
        '    g_bFogEnabled "1"', '    g_flBlurAmount "0.0"', '    g_flRefractionStrength "1.002"', '    AlbedoAbsorption "0.22"',
        '    g_flTintColor "[1.000000 1.000000 1.000000 0.000000]"', '    TextureColor "[0.830000 0.860000 0.860000 0.000000]"',
        '    TextureNormal "materials/default/default_normal.tga"',
        f'    TextureRoughness "{RES}/bd_glass_rough.png"',
        '    TextureMetalness "[0.000000 0.000000 0.000000 0.000000]"',
        '    TextureAmbientOcclusion "[1.000000 1.000000 1.000000 0.000000]"',
        '    TextureBlendMask "materials/default/default_blend.tga"', '    TextureTintMask "materials/default/default.tga"',
        '    TextureTranslucency "materials/default/default_trans.tga"', "}", "" ] ) )
    vmat( out / "bd_light.vmat", "[0.980000 0.960000 0.920000 0.000000]", rough="[0.400000 0.400000 0.400000 0.000000]",
          illum=5.0 )
    # The Rotunde's plate glass seen from outside: the dark hall behind it, the sky in it (Fresnel)
    # (sky-grey: the pale sky over the park in it, as plate glass seen from outside on a bright day)
    vmat( out / "bd_rotunda_glass.vmat", "[0.240000 0.270000 0.310000 0.000000]",
          rough="[0.120000 0.120000 0.120000 0.000000]" )


# ---------------------------------------------------------------------------------------------------------------------
# Round 2: the shops' fall-off and lamps, the glass's smears and lettering, bread baskets, a poster on a shutter

def draw_round2( out ):
    """ bd_room_fall_mask (a back wall's self-light: full under the ceiling, gone 30 in over the floor, over one tile of
    v from the floor to the ceiling), bd_light_halo (a lamp's glow on the ceiling, radial), bd_glass_rough (a shop
    window's smears and handprints, 128 in square), bd_vinyl (the opening hours in white vinyl), bd_wicker and
    bd_poster. """
    rng = rng_of( "round2" )
    # The fall-off: v = 0 at the floor (the image's foot) to 1 at the ceiling (its top); 0 below 30 in of ~128 (v 0.23)
    H = 256
    v = 1.0 - ( np.arange( H ) + 0.5 ) / H
    t = np.clip( ( v - 0.23 ) / 0.77, 0, 1 )
    fall = ( t * t * ( 3 - 2 * t ) ) ** 1.3
    save( out / "bd_room_fall_mask.png", np.repeat( ( fall * 255 )[:, None, None], 16, axis=1 ).repeat( 3, axis=2 ) )
    # The halo: warm light, its alpha falling off as a lamp's pool on a ceiling does ( 1 / ( 1 + ( r / r0 )^2 )^2 )
    S = 256
    y, x = np.mgrid[0:S, 0:S].astype( float )
    r = np.hypot( x - S / 2 + 0.5, y - S / 2 + 0.5 ) / ( S / 2 )
    a = np.clip( ( 1.0 / ( 1 + ( r / 0.35 ) ** 2 ) ** 2 - 0.06 ) / 0.94, 0, 1 ) * ( r < 1 )
    save( out / "bd_light_halo_color.png", np.dstack( [ np.full( ( S, S ), c, float ) for c in ( 255, 228, 186 ) ] ) )
    save( out / "bd_light_halo_trans.png", np.repeat( ( a * 255 )[..., None], 3, axis=2 ) )
    # The glass's roughness (0..255 = 0..1): clean 0.07, wiped arcs over head height, handprints and smudges 30-60 in
    # up (v 0.23-0.47 of a 128 in tile from the pavement), a little dust low down
    G = 512
    rough = np.full( ( G, G ), 0.07 )
    yy, xx = np.mgrid[0:G, 0:G].astype( float )
    zin = ( 1.0 - ( yy + 0.5 ) / G ) * 128.0                            # inches up the tile
    for k in range( 3 ):                                                # wipe arcs: a squeegee's swing
        cx, cy, rad = between( rng, 80, 430 ), between( rng, 60, 200 ), between( rng, 120, 220 )
        d = np.abs( np.hypot( xx - cx, yy - cy ) - rad )
        band = np.clip( 1 - d / between( rng, 6, 14 ), 0, 1 ) * ( yy > cy )
        rough += 0.1 * band * between( rng, 0.5, 1.0 )
    for k in range( 9 ):                                                # handprints and finger smears
        cz = between( rng, 32, 60 )
        cx, cy = between( rng, 20, 490 ), ( 1.0 - cz / 128.0 ) * G
        rough += 0.16 * np.exp( -( ( ( xx - cx ) / 11 ) ** 2 + ( ( yy - cy ) / 13 ) ** 2 ) )
        for f in range( 4 ):
            fx, fy = cx - 12 + 8 * f, cy - 22 - 4 * abs( f - 1.5 )
            rough += 0.13 * np.exp( -( ( ( xx - fx ) / 3 ) ** 2 + ( ( yy - fy ) / 9 ) ** 2 ) )
    rough += 0.06 * np.clip( ( 28 - zin ) / 20, 0, 1 ) * noise( G, G, 24, rng, 2 )
    rough += 0.025 * noise( G, G, 40, rng, 3 )
    save( out / "bd_glass_rough.png", np.repeat( ( np.clip( rough, 0, 1 ) * 255 )[..., None], 3, axis=2 ) )
    # Opening hours in white vinyl, 10 x 14 in (256 x 358 px of 256 x 384), alpha tested
    img = Image.new( "L", ( 256, 384 ), 0 )
    d = ImageDraw.Draw( img )
    head, body = font( "Dinish-Bold", 30 ), font( "Dinish-Regular", 22 )
    d.text( ( 20, 18 ), "Öffnungszeiten", font=head, fill=255 )
    d.line( ( 20, 60, 236, 60 ), fill=255, width=3 )
    for k, ( day, hours ) in enumerate( ( ( "Mo – Fr", "6:30 – 18:30" ), ( "Sa", "7:00 – 14:00" ), ( "So", "8:00 – 11:00" ),
                                          ( "Feiertags", "geschlossen" ) ) ):
        d.text( ( 20, 82 + 44 * k ), day, font=body, fill=255 )
        d.text( ( 236, 82 + 44 * k ), hours, font=body, fill=255, anchor="ra" )
    d.text( ( 20, 290 ), "Kartenzahlung", font=body, fill=255 )
    d.text( ( 20, 322 ), "willkommen", font=body, fill=255 )
    alpha = np.asarray( img, float )
    save( out / "bd_vinyl_color.png", np.full( ( 384, 256, 3 ), 242.0 ) )
    save( out / "bd_vinyl_trans.png", np.repeat( alpha[..., None], 3, axis=2 ) )
    # Wicker: a basket weave at 256 px per 12 in, the willow rods woven round upright stakes
    W = 256
    yy, xx = np.mgrid[0:W, 0:W].astype( float )
    row = ( yy // 10 ).astype( int )
    over = np.sin( ( xx / 21.3 + 0.5 * ( row % 2 ) ) * math.pi )
    rods = np.sin( ( yy % 10 ) / 10 * math.pi ) ** 0.5
    height = rods * ( 0.55 + 0.45 * over )
    base = np.array( ( 150.0, 110.0, 62.0 ) )
    colour = base * ( 0.45 + 0.6 * height[..., None] ) * ( 0.9 + 0.2 * noise( W, W, 8, rng, 2 )[..., None] )
    save( out / "bd_wicker_color.png", colour )
    save( out / "bd_wicker_normal.png", normal_from_height( height * 4, 1.0 ) )
    # Two small posters for a shutter, side by side (a flea market, a lost cat; no real names)
    img = Image.new( "RGB", ( 512, 384 ), ( 236, 232, 220 ) )
    d = ImageDraw.Draw( img )
    d.rectangle( ( 0, 0, 255, 383 ), fill=( 244, 206, 70 ) )
    d.text( ( 128, 40 ), "FLOHMARKT", font=font( "Dinish-Bold", 40 ), fill=( 30, 30, 30 ), anchor="ma" )
    d.text( ( 128, 110 ), "Samstag", font=font( "Dinish-Bold", 34 ), fill=( 160, 30, 30 ), anchor="ma" )
    d.text( ( 128, 160 ), "10 – 16 Uhr", font=font( "Dinish-Regular", 30 ), fill=( 30, 30, 30 ), anchor="ma" )
    d.text( ( 128, 220 ), "Hof Nr. 12", font=font( "Dinish-Regular", 26 ), fill=( 30, 30, 30 ), anchor="ma" )
    for k in range( 8 ):
        d.rectangle( ( 8 + 31 * k, 320, 30 + 31 * k, 376 ), fill=( 250, 250, 246 ) )        # tear-off strips
    d.text( ( 384, 30 ), "VERMISST", font=font( "Dinish-Bold", 44 ), fill=( 20, 20, 20 ), anchor="ma" )
    d.rectangle( ( 300, 90, 468, 240 ), fill=( 120, 118, 112 ) )
    d.ellipse( ( 340, 120, 430, 220 ), fill=( 60, 56, 52 ) )
    d.text( ( 384, 262 ), "grau getigert", font=font( "Dinish-Regular", 26 ), fill=( 20, 20, 20 ), anchor="ma" )
    d.text( ( 384, 300 ), "hört auf Mila", font=font( "Dinish-Regular", 26 ), fill=( 20, 20, 20 ), anchor="ma" )
    save( out / "bd_poster_color.png", np.asarray( img.filter( ImageFilter.GaussianBlur( 0.6 ) ), float ) )


def write_round2( out ):
    """ Round 2's vmats: the halo (translucent, self-lit), the vinyl (alpha tested), the frosted band (translucent),
    wicker and the poster. """
    def tr( name ):
        return f"{RES}/{name}"
    for name, colour, extra in (
            ( "bd_light_halo", tr( "bd_light_halo_color.png" ), [ '    F_TRANSLUCENT "1"', '    F_SELF_ILLUM "1"',
              f'    TextureTranslucency "{tr( "bd_light_halo_trans.png" )}"',
              '    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"', '    g_flSelfIllumBrightness "0.60"',
              '    g_flSelfIllumAlbedoFactor "1.0"' ] ),
            ( "bd_vinyl", tr( "bd_vinyl_color.png" ), [ '    F_ALPHA_TEST "1"',
              f'    TextureTranslucency "{tr( "bd_vinyl_trans.png" )}"', '    g_flAlphaTestReference "0.5"' ] ),
            ( "bd_frost", "[0.900000 0.910000 0.900000 0.000000]", [ '    F_TRANSLUCENT "1"',
              '    TextureTranslucency "[0.600000 0.600000 0.600000 0.000000]"' ] ) ):
        ( out / f"{name}.vmat" ).write_text( "\n".join( [ "// Tools/railhead_backdrop_art.py", '"Layer0"', "{",
            '    shader "shaders/complex.shader"', *extra, f'    TextureColor "{colour}"',
            '    TextureNormal "materials/default/default_normal.tga"',
            '    TextureRoughness "[0.600000 0.600000 0.600000 0.000000]"',
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"', '    g_flMetalness "0.00"',
            '    g_vColorTint "[1.000000 1.000000 1.000000 1.0]"', "}", "" ] ) )
    vmat( out / "bd_wicker.vmat", tr( "bd_wicker_color.png" ), normal=tr( "bd_wicker_normal.png" ),
          rough="[0.800000 0.800000 0.800000 0.000000]" )
    vmat( out / "bd_poster.vmat", tr( "bd_poster_color.png" ), rough="[0.650000 0.650000 0.650000 0.000000]" )


def ensure_materials( root, force=False ):
    """ Writes every bd_ texture and vmat under root / RES (root laid out as Assets). Drawn only when missing (or force). """
    out = Path( root ) / RES
    out.mkdir( parents=True, exist_ok=True )
    steps = ( ( "bd_windows_color.png", draw_windows ), ( "bd_interiors_color.png", draw_interiors ),
              ( "bd_awning_color.png", draw_awnings ), ( "bd_plaques_color.png", draw_plaques ),
              ( "bd_shutter_color.png", draw_shutter ), ( "bd_goods_color.png", draw_goods ),
              ( "bd_crust_color.png", draw_crust ), ( "bd_canopy_color.png", draw_canopy ),
              ( "bd_clock_color.png", draw_clock_menu ), ( "bd_glass_rough.png", draw_round2 ) )
    for name, step in steps:
        if force or not ( out / name ).is_file():
            step( out )
    write_tinted( out )
    write_glass( out )
    write_pass2( out )
    write_round2( out )
    return out


if __name__ == "__main__":
    if len( sys.argv ) < 2:
        print( __doc__ )
        sys.exit( 1 )
    print( f"wrote {ensure_materials( sys.argv[1], force='--force' in sys.argv )}" )
